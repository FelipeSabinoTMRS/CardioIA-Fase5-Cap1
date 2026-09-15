"""Extração acadêmica de informações clínicas fictícias com IA generativa."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel, ConfigDict, Field, field_validator


OBSERVACAO_PADRAO = (
    "Extração acadêmica. Não substitui avaliação médica ou atendimento de emergência."
)


class SinaisVitais(BaseModel):
    """Sinais vitais escritos explicitamente no texto."""

    model_config = ConfigDict(extra="forbid")
    pressao_arterial: str | None = Field(
        default=None, description="Pressão arterial exatamente como informada."
    )
    frequencia_cardiaca: str | None = Field(
        default=None, description="Frequência cardíaca exatamente como informada."
    )
    saturacao: str | None = Field(
        default=None, description="Saturação de oxigênio exatamente como informada."
    )


class ExtracaoClinica(BaseModel):
    """Contrato validado da resposta produzida pelo modelo generativo."""

    model_config = ConfigDict(extra="forbid")
    sintomas: list[str] = Field(default_factory=list)
    fatores_risco: list[str] = Field(default_factory=list)
    medicamentos: list[str] = Field(default_factory=list)
    sinais_vitais: SinaisVitais = Field(default_factory=SinaisVitais)
    alertas: list[str] = Field(default_factory=list)
    informacoes_negadas: list[str] = Field(default_factory=list)
    fonte: Literal["texto_simulado"] = "texto_simulado"
    observacao: str = OBSERVACAO_PADRAO

    @field_validator(
        "sintomas",
        "fatores_risco",
        "medicamentos",
        "alertas",
        "informacoes_negadas",
    )
    @classmethod
    def limpar_listas(cls, valores: list[str]) -> list[str]:
        """Remove itens vazios e duplicados, preservando a ordem."""
        resultado: list[str] = []
        vistos: set[str] = set()
        for valor in valores:
            item = valor.strip()
            chave = item.casefold()
            if item and chave not in vistos:
                vistos.add(chave)
                resultado.append(item)
        return resultado


INSTRUCAO_SISTEMA = """
Você é um extrator de informações para uma demonstração acadêmica.
Sua única tarefa é estruturar o conteúdo explicitamente presente no texto.

Regras obrigatórias:
1. Não diagnostique, recomende tratamento ou avalie prognóstico.
2. Não complete lacunas e não use conhecimento externo para inferir dados.
3. Mantenha listas vazias e valores null quando a informação estiver ausente.
4. Preserve números e unidades dos sinais vitais como aparecem no texto.
5. Uma informação negada deve aparecer apenas em informacoes_negadas, nunca como
   sintoma ou alerta afirmado.
6. Registre em alertas somente sinais explicitamente afirmados no texto, como dor
   no peito, falta de ar intensa ou desmaio.
7. Use fonte igual a texto_simulado e mantenha a observacao acadêmica definida no schema.
8. Responda exclusivamente de acordo com o schema JSON fornecido.
""".strip()


# Schema enviado ao Gemini. Ele é declarado separadamente porque alguns endpoints
# não aceitam `additionalProperties`, gerado pelo `extra="forbid"` do Pydantic.
# A validação rigorosa continua sendo feita por ExtracaoClinica após a resposta.
SCHEMA_GEMINI = {
    "type": "OBJECT",
    "properties": {
        "sintomas": {"type": "ARRAY", "items": {"type": "STRING"}},
        "fatores_risco": {"type": "ARRAY", "items": {"type": "STRING"}},
        "medicamentos": {"type": "ARRAY", "items": {"type": "STRING"}},
        "sinais_vitais": {
            "type": "OBJECT",
            "properties": {
                "pressao_arterial": {"type": "STRING", "nullable": True},
                "frequencia_cardiaca": {"type": "STRING", "nullable": True},
                "saturacao": {"type": "STRING", "nullable": True},
            },
            "required": [
                "pressao_arterial",
                "frequencia_cardiaca",
                "saturacao",
            ],
        },
        "alertas": {"type": "ARRAY", "items": {"type": "STRING"}},
        "informacoes_negadas": {
            "type": "ARRAY",
            "items": {"type": "STRING"},
        },
        "fonte": {"type": "STRING", "enum": ["texto_simulado"]},
        "observacao": {"type": "STRING"},
    },
    "required": [
        "sintomas",
        "fatores_risco",
        "medicamentos",
        "sinais_vitais",
        "alertas",
        "informacoes_negadas",
        "fonte",
        "observacao",
    ],
}


def extrair_informacoes(texto: str, modelo: str) -> ExtracaoClinica:
    """Envia o texto à API e devolve apenas uma estrutura já validada."""
    if not texto.strip():
        raise ValueError("O texto clínico não pode estar vazio.")

    chave = os.getenv("GEMINI_API_KEY")
    if not chave:
        raise RuntimeError(
            "GEMINI_API_KEY não encontrada. Copie .env.example para .env e informe a chave."
        )

    cliente = genai.Client(api_key=chave)
    resposta = cliente.models.generate_content(
        model=modelo,
        contents=f"Texto clínico fictício para extração:\n\n{texto.strip()}",
        config=types.GenerateContentConfig(
            system_instruction=INSTRUCAO_SISTEMA,
            response_mime_type="application/json",
            response_schema=SCHEMA_GEMINI,
            temperature=0,
        ),
    )

    if resposta.parsed is not None:
        return ExtracaoClinica.model_validate(resposta.parsed)
    if not resposta.text:
        raise RuntimeError("A API não retornou conteúdo para validação.")
    return ExtracaoClinica.model_validate_json(resposta.text)


def carregar_texto(texto: str | None, arquivo: Path | None) -> str:
    """Obtém a entrada por uma das duas formas aceitas pela linha de comando."""
    if texto is not None:
        return texto
    if arquivo is not None:
        return arquivo.read_text(encoding="utf-8")
    raise ValueError("Informe --texto ou --arquivo.")


def criar_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Extrai informações de um texto clínico fictício para JSON."
    )
    entrada = parser.add_mutually_exclusive_group(required=True)
    entrada.add_argument("--texto", help="Texto clínico fictício digitado entre aspas.")
    entrada.add_argument("--arquivo", type=Path, help="Caminho de um arquivo TXT.")
    parser.add_argument("--saida", type=Path, help="Arquivo JSON opcional para salvar.")
    return parser


def main() -> None:
    load_dotenv()
    argumentos = criar_parser().parse_args()
    modelo = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")

    try:
        texto = carregar_texto(argumentos.texto, argumentos.arquivo)
        extracao = extrair_informacoes(texto, modelo)
        conteudo = extracao.model_dump_json(indent=2)
        print(conteudo)

        if argumentos.saida:
            argumentos.saida.parent.mkdir(parents=True, exist_ok=True)
            argumentos.saida.write_text(conteudo + "\n", encoding="utf-8")
            print(f"\nResultado salvo em: {argumentos.saida}")
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as erro:
        raise SystemExit(f"Erro: {erro}") from erro


if __name__ == "__main__":
    main()
