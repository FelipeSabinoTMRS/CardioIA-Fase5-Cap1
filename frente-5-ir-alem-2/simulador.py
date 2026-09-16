"""Gerador de dados clínicos simulados para o robô da Frente 5.

Faz o papel do dispositivo de monitoramento da Fase 3: pacientes fictícios
medem pressão e frequência cardíaca duas vezes ao dia e registram as doses
tomadas. O ruído é aleatório com semente fixa (mesma semente, mesmos dados),
como no gerador do pipeline do Cap. 2 de AIRPA, e alguns cenários de atenção
são colocados de propósito para que regras e IA tenham o que encontrar.

Nenhum dado aqui é real. Os pacientes têm apenas código e nome fictício.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone

from banco_relacional import iso_utc

# Medições às 8h e às 20h (UTC) de dias completos: o histórico sai igual a qualquer hora do preparo.
HORARIOS = (time(8, 0), time(20, 0))


@dataclass(frozen=True)
class PerfilPaciente:
    codigo: str
    idade: int
    condicao_base: str
    medicamento: str
    doses_dia: int
    sistolica: int
    diastolica: int
    fc: int
    adesao: float


PERFIS = (
    PerfilPaciente("PAC-001", 58, "hipertensão controlada", "losartana", 1, 128, 82, 72, 0.97),
    PerfilPaciente("PAC-002", 64, "hipertensão", "losartana", 2, 132, 84, 76, 0.95),
    PerfilPaciente("PAC-003", 47, "palpitações em investigação", "atenolol", 1, 122, 78, 66, 0.92),
    PerfilPaciente("PAC-004", 71, "pós-infarto", "AAS", 1, 118, 76, 68, 0.96),
    PerfilPaciente("PAC-005", 69, "insuficiência cardíaca", "hidroclorotiazida", 1, 112, 70, 74, 0.90),
    PerfilPaciente("PAC-006", 55, "dislipidemia", "sinvastatina", 1, 124, 80, 70, 0.93),
    PerfilPaciente("PAC-007", 52, "hipertensão", "enalapril", 2, 110, 70, 60, 0.94),
    PerfilPaciente("PAC-008", 60, "bradicardia em acompanhamento", "atenolol", 1, 126, 80, 64, 0.95),
)

# (código, dias antes de ontem, turno 0 = 8h / 1 = 20h) -> leitura (sistólica, diastólica, FC) do cenário.
EVENTOS = {
    ("PAC-003", 18, 1): (126, 80, 128),   # taquicardia
    ("PAC-003", 6, 1): (130, 82, 138),    # taquicardia acentuada
    ("PAC-004", 5, 0): (188, 112, 92),    # crise hipertensiva
    ("PAC-005", 12, 0): (84, 54, 88),     # pressão baixa
    ("PAC-007", 3, 1): (138, 88, 96),     # atípico para o paciente, sem cruzar limiar
    ("PAC-007", 2, 0): (136, 86, 94),
    ("PAC-008", 15, 0): (118, 76, 44),    # bradicardia
}

# PAC-002 para de tomar o remédio nos últimos 10 dias e a pressão sobe aos poucos.
PACIENTE_BAIXA_ADESAO = "PAC-002"
DIAS_BAIXA_ADESAO = 10


@dataclass
class DadosSimulados:
    pacientes: list[dict]
    leituras: list[dict]
    adesao: list[dict]


def _medir(rng: random.Random, sistolica: float, diastolica: float, fc: float) -> tuple[int, int, int]:
    s = round(rng.gauss(sistolica, 5))
    d = round(rng.gauss(diastolica, 3.5))
    f = round(rng.gauss(fc, 3))
    s = min(max(s, 60), 290)
    d = min(max(d, 35), s - 10)
    f = min(max(f, 25), 240)
    return s, d, f


def _registro_leitura(codigo: str, medido_em: datetime, valores: tuple[int, int, int]) -> dict:
    sistolica, diastolica, fc = valores
    return {
        "paciente_codigo": codigo,
        "medido_em": iso_utc(medido_em),
        "pressao_sistolica": sistolica,
        "pressao_diastolica": diastolica,
        "frequencia_cardiaca": fc,
        "origem": "simulador",
    }


def gerar_historico(agora: datetime, dias: int = 30, semente: int = 42) -> DadosSimulados:
    """Pacientes, duas leituras por dia e adesão diária dos ``dias`` dias completos até ontem."""
    rng = random.Random(semente)
    ontem = agora.astimezone(timezone.utc).date() - timedelta(days=1)
    criado_em = iso_utc(datetime.combine(ontem - timedelta(days=dias - 1), time(0), tzinfo=timezone.utc))
    pacientes, leituras, adesao = [], [], []

    for numero, perfil in enumerate(PERFIS, start=1):
        pacientes.append({
            "codigo": perfil.codigo,
            "nome_ficticio": f"Paciente Fictício {numero:02d}",
            "idade": perfil.idade,
            "condicao_base": perfil.condicao_base,
            "medicamento_continuo": perfil.medicamento,
            "criado_em": criado_em,
        })
        for dias_atras in range(dias - 1, -1, -1):
            dia = ontem - timedelta(days=dias_atras)
            probabilidade = perfil.adesao
            sistolica, diastolica = perfil.sistolica, perfil.diastolica
            if perfil.codigo == PACIENTE_BAIXA_ADESAO and dias_atras < DIAS_BAIXA_ADESAO:
                probabilidade = 0.35
                fator = (DIAS_BAIXA_ADESAO - dias_atras) / DIAS_BAIXA_ADESAO
                sistolica += 18 * fator
                diastolica += 10 * fator

            tomadas = sum(rng.random() < probabilidade for _ in range(perfil.doses_dia))
            adesao.append({
                "paciente_codigo": perfil.codigo,
                "data": dia.isoformat(),
                "doses_prescritas": perfil.doses_dia,
                "doses_tomadas": tomadas,
            })

            for turno, horario in enumerate(HORARIOS):
                medido_em = datetime.combine(dia, horario, tzinfo=timezone.utc)
                valores = EVENTOS.get((perfil.codigo, dias_atras, turno)) or _medir(
                    rng, sistolica, diastolica, perfil.fc
                )
                leituras.append(_registro_leitura(perfil.codigo, medido_em, valores))

    return DadosSimulados(pacientes=pacientes, leituras=leituras, adesao=adesao)


def gerar_novas_leituras(agora: datetime, quantidade: int, semente: int | None = None) -> list[dict]:
    """Leituras que chegam durante a demonstração do robô, com chance de anomalia."""
    rng = random.Random(semente)
    novas = []
    for _ in range(quantidade):
        perfil = rng.choice(PERFIS)
        sorteio = rng.random()
        if sorteio < 0.08:
            valores = _medir(rng, perfil.sistolica + 58, perfil.diastolica + 32, perfil.fc + 12)
        elif sorteio < 0.16:
            valores = _medir(rng, perfil.sistolica, perfil.diastolica, perfil.fc + 48)
        elif sorteio < 0.24:
            valores = _medir(rng, perfil.sistolica + 26, perfil.diastolica + 16, perfil.fc + 34)
        else:
            valores = _medir(rng, perfil.sistolica, perfil.diastolica, perfil.fc)
        novas.append(_registro_leitura(perfil.codigo, agora, valores))
    return novas


def com_ids(registros: list[dict], ids_por_codigo: dict[str, int]) -> list[dict]:
    """Troca ``paciente_codigo`` pelo ``paciente_id`` gerado no SQLite."""
    convertidos = []
    for registro in registros:
        copia = dict(registro)
        copia = {"paciente_id": ids_por_codigo[copia.pop("paciente_codigo")], **copia}
        convertidos.append(copia)
    return convertidos


def mensagens_iniciais(agora: datetime) -> list[dict]:
    """Mensagens textuais que pacientes enviaram pelo app de monitoramento."""
    textos = [
        ("PAC-004", 3, "Ontem à noite senti um aperto no peito e fiquei suando frio."),
        ("PAC-002", 20, "Acabou a losartana e fiquei uns dias sem tomar."),
        ("PAC-003", 9, "Coração disparado de novo depois do café."),
        ("PAC-001", 30, "Hoje estou bem, sem dor no peito e sem falta de ar."),
        ("PAC-005", 6, "Fiquei tonta quando levantei da cama."),
        ("PAC-007", 2, "Queria confirmar o horário da consulta."),
        ("PAC-099", 1, "Oi, recebi o aparelho de pressão, como começo?"),
    ]
    return [
        {
            "paciente_codigo": codigo,
            "texto": texto,
            "recebida_em": agora - timedelta(hours=horas_antes),
            "canal": "app_monitoramento",
            "origem": "simulador",
        }
        for codigo, horas_antes, texto in textos
    ]
