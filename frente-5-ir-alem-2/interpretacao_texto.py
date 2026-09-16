"""Interpretação das mensagens textuais dos pacientes (Frente 5).

O robô não cria um vocabulário novo: lê as entidades ``@sinal_alerta``,
``@sintoma`` e ``@medicamento`` direto do JSON da skill Watson da Frente 1 e
aplica a mesma ideia de entidade com sinônimos vista em PCV. Assim, o que o
chatbot reconhece na conversa é o mesmo que o robô reconhece no histórico.

Técnica: normalização (minúsculas, sem acento), casamento de termo inteiro
(o mais longo primeiro) e uma regra simples de negação ("sem", "não" até três
palavras antes do termo). Não há fuzzy match como no Watson: erro de digitação
não é reconhecido. Essa limitação está no relatório técnico.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

from regras_clinicas import AlertaRegra

ENTIDADES = ("sinal_alerta", "sintoma", "medicamento")
PALAVRAS_NEGACAO = {"nao", "sem", "nunca", "nem", "nenhum", "nenhuma"}
JANELA_NEGACAO = 3


@dataclass(frozen=True)
class Vocabulario:
    """Termos normalizados da skill: (entidade, valor canônico, termo)."""

    termos: tuple[tuple[str, str, str], ...]
    hash_skill: str


@dataclass
class Interpretacao:
    """Valores canônicos encontrados em uma mensagem."""

    sinais_alerta: list[str] = field(default_factory=list)
    sintomas: list[str] = field(default_factory=list)
    medicamentos: list[str] = field(default_factory=list)
    negados: list[str] = field(default_factory=list)


def normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto)
    sem_acento = "".join(c for c in sem_acento if not unicodedata.combining(c))
    return sem_acento.lower()


def carregar_vocabulario(caminho_skill: str | Path) -> Vocabulario:
    """Lê as entidades clínicas do JSON exportado da skill Watson."""
    conteudo = Path(caminho_skill).read_bytes()
    skill = json.loads(conteudo.decode("utf-8"))
    termos: set[tuple[str, str, str]] = set()
    for entidade in skill["entities"]:
        if entidade["entity"] not in ENTIDADES:
            continue
        for valor in entidade["values"]:
            for termo in [valor["value"], *valor.get("synonyms", [])]:
                termos.add((entidade["entity"], valor["value"], normalizar(termo)))
    ordenados = tuple(sorted(termos, key=lambda t: (-len(t[2]), t)))
    return Vocabulario(termos=ordenados, hash_skill=hashlib.sha256(conteudo).hexdigest()[:12])


def _negado(texto_normalizado: str, inicio: int) -> bool:
    # A negação vale só dentro da mesma oração: "Não, estou com dor no peito" é relato.
    trecho = re.split(r"[.,;:!?]", texto_normalizado[:inicio])[-1]
    anteriores = re.findall(r"[a-z0-9]+", trecho)[-JANELA_NEGACAO:]
    return any(palavra in PALAVRAS_NEGACAO for palavra in anteriores)


def interpretar_mensagem(texto: str, vocabulario: Vocabulario) -> Interpretacao:
    """Encontra sinais de alerta, sintomas e medicamentos citados na mensagem."""
    normalizado = normalizar(texto)
    ocupados: list[tuple[int, int]] = []
    resultado = Interpretacao()
    destino = {
        "sinal_alerta": resultado.sinais_alerta,
        "sintoma": resultado.sintomas,
        "medicamento": resultado.medicamentos,
    }

    for entidade, canonico, termo in vocabulario.termos:
        padrao = r"(?<![a-z0-9])" + r"\s+".join(map(re.escape, termo.split())) + r"(?![a-z0-9])"
        for achado in re.finditer(padrao, normalizado):
            inicio, fim = achado.span()
            if any(inicio < f and fim > i for i, f in ocupados):
                continue
            ocupados.append((inicio, fim))
            lista = resultado.negados if _negado(normalizado, inicio) else destino[entidade]
            if canonico not in lista:
                lista.append(canonico)

    return resultado


def alerta_da_interpretacao(interpretacao: Interpretacao) -> AlertaRegra | None:
    """Sinal de alerta vira alerta crítico; sintoma relatado vira alerta moderado."""
    if interpretacao.sinais_alerta:
        citados = ", ".join(interpretacao.sinais_alerta)
        return AlertaRegra(
            "sinal_alerta_relatado", "critica",
            f"Mensagem do paciente cita sinal de alerta: {citados}. "
            "Contato imediato e orientação para ligar 192 (SAMU).",
        )
    if interpretacao.sintomas:
        return AlertaRegra(
            "sintoma_relatado", "moderada",
            f"Mensagem do paciente relata: {', '.join(interpretacao.sintomas)}.",
        )
    return None
