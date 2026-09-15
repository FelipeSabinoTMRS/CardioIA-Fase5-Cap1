"""ExtraÃ§Ã£o acadÃªmica de informaÃ§Ãµes clÃ­nicas fictÃ­cias com IA generativa."""

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
    "ExtraÃ§Ã£o acadÃªmica. NÃ£o substitui avaliaÃ§Ã£o mÃ©dica ou atendimento de emergÃªncia."
)


class SinaisVitais(BaseModel):
    """Sinais vitais escritos explicitamente no texto."""

    model_config = ConfigDict(extra="forbid")
    pressao_arterial: str | None = Field(
        default=None, description="PressÃ£o arterial exatamente como informada."
    )
    frequencia_cardiaca: str | None = Field(
        default=None, description="FrequÃªncia cardÃ­aca exatamente como informada."
    )
    saturacao: str | None = Field(
        default=None, description="SaturaÃ§Ã£o de oxigÃªnio exatamente como informada."
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
VocÃª Ã© um extrator de informaÃ§Ãµes para uma demonstraÃ§Ã£o acadÃªmica.
Sua Ãºnica tarefa Ã© estruturar o conteÃºdo explicitamente presente no texto.

Regras obrigatÃ³rias:
1. NÃ£o diagnostique, recomende tratamento ou avalie prognÃ³stico.
2. NÃ£o complete lacunas e nÃ£o use conhecimento externo para inferir dados.
3. Mantenha listas vazias e valores null quando a informaÃ§Ã£o estiver ausente.
4. Preserve nÃºmeros e unidades dos sinais vitais como aparecem no texto.
5. Uma informaÃ§Ã£o negada deve aparecer apenas em informacoes_negadas, nunca como
   sintoma ou alerta afirmado.
6. Registre em alertas somente sinais explicitamente afirmados no texto, como dor
   no peito, falta de ar intensa ou desmaio.
7. Use fonte igual a texto_simulado e mantenha a observacao acadÃªmica definida no schema.
8. Responda exclusivamente de acordo com o schema JSON fornecido.
""".strip()


# Schema enviado ao Gemini. Ele Ã© declarado separadamente porque alguns endpoints
# nÃ£o aceitam `additionalProperties`, gerado pelo `extra="forbid"` do Pydantic.
# A validaÃ§Ã£o rigorosa continua sendo feita por ExtracaoClinica apÃ³s a resposta.
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
    """Envia o texto Ã  API e devolve apenas uma estrutura jÃ¡ validada."""
    if not texto.strip():
        raise ValueError("O texto clÃ­nico nÃ£o pode estar vazio.")

    chave = os.getenv("GEMINI_API_KEY")
    if not chave:
        raise RuntimeError(
            "GEMINI_API_KEY nÃ£o encontrada. Copie .env.example para .env e informe a chave."
        )

    cliente = genai.Client(api_key=chave)
    resposta = cliente.models.generate_content(
        model=modelo,
        contents=f"Texto clÃ­nico fictÃ­cio para extraÃ§Ã£o:\n\n{texto.strip()}",
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
        raise RuntimeError("A API nÃ£o retornou conteÃºdo para validaÃ§Ã£o.")
    return ExtracaoClinica.model_validate_json(resposta.text)


def carregar_texto(texto: str | None, arquivo: Path | None) -> str:
    """ObtÃ©m a entrada por uma das duas formas aceitas pela linha de comando."""
    if texto is not None:
        return texto
    if arquivo is not None:
        return arquivo.read_text(encoding="utf-8")
    raise ValueError("Informe --texto ou --arquivo.")


def criar_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Extrai informaÃ§Ãµes de um texto clÃ­nico fictÃ­cio para JSON."
    )
    entrada = parser.add_mutually_exclusive_group(required=True)
    entrada.add_argument("--texto", help="Texto clÃ­nico fictÃ­cio digitado entre aspas.")
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
