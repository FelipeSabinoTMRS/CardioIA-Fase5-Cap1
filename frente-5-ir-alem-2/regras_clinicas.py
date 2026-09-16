"""Regras clínicas determinísticas do robô de monitoramento (Frente 5).

As faixas seguem as mesmas referências que o assistente da Frente 1 usa com o
paciente (pressão abaixo de 14 por 9, frequência cardíaca entre 50 e 100 bpm e
pressão muito elevada a partir de 18). As regras são a camada explicável da
detecção: cada alerta diz qual limiar foi cruzado. O Isolation Forest
(``ia_anomalia.py``) complementa com o que foge do padrão sem cruzar limiar.

Simulação acadêmica: os limiares não substituem protocolo clínico real.
"""

from __future__ import annotations

from dataclasses import dataclass

VERSAO_REGRAS = "1.0.0"

LIMIARES = {
    "crise_sistolica": 180,
    "crise_diastolica": 120,
    "elevada_sistolica": 140,
    "elevada_diastolica": 90,
    "baixa_sistolica": 90,
    "baixa_diastolica": 60,
    "fc_alta": 100,
    "fc_muito_alta": 130,
    "fc_baixa": 50,
    "adesao_minima": 0.8,
}


@dataclass(frozen=True)
class AlertaRegra:
    """Alerta produzido por uma regra: tipo, severidade e descrição legível."""

    tipo: str
    severidade: str
    descricao: str


def avaliar_sinais(sistolica: int, diastolica: int, frequencia_cardiaca: int) -> list[AlertaRegra]:
    """Aplica as regras de pressão e frequência cardíaca a uma leitura."""
    alertas: list[AlertaRegra] = []
    pa = f"{sistolica}/{diastolica} mmHg"

    if sistolica >= LIMIARES["crise_sistolica"] or diastolica >= LIMIARES["crise_diastolica"]:
        alertas.append(AlertaRegra(
            "crise_hipertensiva", "critica",
            f"PA {pa} na faixa de crise hipertensiva (a partir de 180/120). Contato imediato com o paciente.",
        ))
    elif sistolica >= LIMIARES["elevada_sistolica"] or diastolica >= LIMIARES["elevada_diastolica"]:
        alertas.append(AlertaRegra(
            "pressao_elevada", "moderada",
            f"PA {pa} acima da referência de 140/90.",
        ))
    elif sistolica < LIMIARES["baixa_sistolica"] or diastolica < LIMIARES["baixa_diastolica"]:
        alertas.append(AlertaRegra(
            "pressao_baixa", "alta",
            f"PA {pa} abaixo de 90/60. Verificar tontura, desmaio ou desidratação.",
        ))

    if frequencia_cardiaca > LIMIARES["fc_alta"]:
        severidade = "alta" if frequencia_cardiaca >= LIMIARES["fc_muito_alta"] else "moderada"
        alertas.append(AlertaRegra(
            "taquicardia", severidade,
            f"FC de {frequencia_cardiaca} bpm acima de 100 bpm em repouso.",
        ))
    elif frequencia_cardiaca < LIMIARES["fc_baixa"]:
        alertas.append(AlertaRegra(
            "bradicardia", "alta",
            f"FC de {frequencia_cardiaca} bpm abaixo de 50 bpm em repouso.",
        ))

    return alertas


def avaliar_adesao(doses_tomadas: int, doses_prescritas: int) -> AlertaRegra | None:
    """Gera alerta quando a adesão ao tratamento fica abaixo do mínimo (80%)."""
    if doses_prescritas <= 0:
        return None
    adesao = doses_tomadas / doses_prescritas
    if adesao >= LIMIARES["adesao_minima"]:
        return None
    return AlertaRegra(
        "baixa_adesao", "moderada",
        f"Adesão de {adesao:.0%} nos últimos 7 dias ({doses_tomadas} de {doses_prescritas} doses).",
    )
