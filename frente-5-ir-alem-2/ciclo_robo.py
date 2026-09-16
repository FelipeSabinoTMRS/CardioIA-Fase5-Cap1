"""Um ciclo do robô de monitoramento do CardioIA (Frente 5).

Cada ciclo é uma execução rastreável com ``execucao_id`` próprio:

1. abre a execução no MongoDB com parâmetros, limiares e versões do ambiente;
2. lê no SQLite as leituras que ainda não foram analisadas;
3. treina o Isolation Forest na janela de 30 dias e pontua as leituras novas;
4. aplica as regras clínicas. Evento agudo (crise, taquicardia, bradicardia,
   pressão baixa, padrão atípico) gera um alerta por leitura. Estado
   persistente (pressão elevada recorrente, baixa adesão) gera no máximo um
   alerta por paciente a cada 24 h, para não afogar a equipe em repetição;
5. interpreta as mensagens pendentes com o vocabulário da skill Watson;
6. grava análises e alertas no SQLite em uma transação;
7. registra no MongoDB um evento por alerta e fecha a execução com métricas.

Se algo falhar, a transação do SQLite não é confirmada e a execução fica com
status ``erro`` no MongoDB. As leituras continuam pendentes para o próximo ciclo.
"""

from __future__ import annotations

import platform
import sqlite3
import time
import uuid
from collections import Counter
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timedelta, timezone

import pandas as pd
import pymongo
import sklearn

import banco_relacional as br
from banco_nosql import RegistroNoSQL
from ia_anomalia import DetectorAnomalias, descrever_anomalia, doses_na_janela_7d, preparar_features
from interpretacao_texto import ENTIDADES, Vocabulario, alerta_da_interpretacao, interpretar_mensagem
from regras_clinicas import LIMIARES, VERSAO_REGRAS, AlertaRegra, avaliar_adesao, avaliar_sinais

NOME_ROBO = "robo-monitoramento-cardioia"
VERSAO_ROBO = "1.0.0"
LOTE_LEITURAS = 500
LOTE_MENSAGENS = 100
JANELA_TREINO_DIAS = 30
JANELA_ALERTA_ESTADO_HORAS = 24
TIPOS_ESTADO = ("pressao_elevada", "baixa_adesao")


@dataclass
class ResumoCiclo:
    execucao_id: str
    status: str = "concluida"
    leituras_analisadas: int = 0
    anomalias_ia: int = 0
    modelo_treinado: bool = False
    mensagens_processadas: int = 0
    mensagens_rejeitadas: int = 0
    alertas_gerados: int = 0
    alertas_por_tipo: dict[str, int] = field(default_factory=dict)
    duracao_s: float = 0.0


@dataclass(frozen=True)
class _Candidato:
    alerta: br.NovoAlerta
    paciente_codigo: str


def executar_ciclo(con: sqlite3.Connection, registro: RegistroNoSQL, vocabulario: Vocabulario,
                   detector: DetectorAnomalias | None = None, agora: datetime | None = None,
                   lote_leituras: int = LOTE_LEITURAS) -> ResumoCiclo:
    detector = detector or DetectorAnomalias()
    agora = (agora or datetime.now(timezone.utc)).astimezone(timezone.utc).replace(microsecond=0)
    resumo = ResumoCiclo(execucao_id=str(uuid.uuid4()))
    inicio = time.perf_counter()

    registro.iniciar_execucao(
        resumo.execucao_id, agora,
        robo=NOME_ROBO, versao_robo=VERSAO_ROBO,
        parametros=_parametros(detector, vocabulario, lote_leituras),
        ambiente=_ambiente(),
    )
    try:
        codigos = {paciente_id: codigo for codigo, paciente_id in br.ids_por_codigo(con).items()}
        analises, candidatos, modelo = _analisar_leituras(
            con, registro, detector, resumo, agora, lote_leituras, codigos
        )
        resumo.leituras_analisadas = len(analises)
        mensagens = _interpretar_mensagens(registro, vocabulario, resumo, agora, codigos, candidatos)

        ids = br.registrar_resultados(con, analises, [c.alerta for c in candidatos])

        _registrar_alertas(registro, resumo, candidatos, ids, agora)
        _concluir_mensagens(registro, resumo, mensagens, candidatos, ids, agora)
        resumo.duracao_s = round(time.perf_counter() - inicio, 3)
        metricas = {k: v for k, v in asdict(resumo).items() if k not in ("execucao_id", "status", "duracao_s")}
        registro.concluir_execucao(
            resumo.execucao_id, agora + timedelta(seconds=resumo.duracao_s), resumo.duracao_s,
            metricas=metricas, modelo=modelo,
        )
    except Exception as exc:
        resumo.status = "erro"
        resumo.duracao_s = round(time.perf_counter() - inicio, 3)
        registro.falhar_execucao(resumo.execucao_id, exc, agora + timedelta(seconds=resumo.duracao_s),
                                 resumo.duracao_s)
        raise
    return resumo


def _parametros(detector, vocabulario: Vocabulario, lote_leituras: int) -> dict:
    return {
        "lote_leituras": lote_leituras,
        "lote_mensagens": LOTE_MENSAGENS,
        "janela_treino_dias": JANELA_TREINO_DIAS,
        "janela_alerta_estado_horas": JANELA_ALERTA_ESTADO_HORAS,
        "tipos_estado": list(TIPOS_ESTADO),
        "versao_regras": VERSAO_REGRAS,
        "limiares": dict(LIMIARES),
        "modelo": detector.parametros(),
        "vocabulario": {
            "fonte": "frente-1-watson/cardioia-skill.json",
            "hash_skill": vocabulario.hash_skill,
            "entidades": list(ENTIDADES),
        },
    }


def _ambiente() -> dict:
    return {
        "python": platform.python_version(),
        "sqlite": sqlite3.sqlite_version,
        "pandas": pd.__version__,
        "scikit_learn": sklearn.__version__,
        "pymongo": pymongo.version,
    }


def _candidato(regra: AlertaRegra, origem: str, paciente_id: int, codigos: dict[int, str], execucao_id: str,
               agora: datetime, leitura_id: int | None = None, mensagem_id: str | None = None,
               score: float | None = None) -> _Candidato:
    alerta = br.NovoAlerta(
        paciente_id=paciente_id, execucao_id=execucao_id, tipo=regra.tipo, severidade=regra.severidade,
        origem_deteccao=origem, descricao=regra.descricao, criado_em=br.iso_utc(agora),
        leitura_id=leitura_id, mensagem_id=mensagem_id, score_anomalia=score,
    )
    return _Candidato(alerta=alerta, paciente_codigo=codigos[paciente_id])


def _analisar_leituras(con, registro, detector, resumo, agora, lote_leituras, codigos):
    pendentes = br.buscar_leituras_pendentes(con, lote_leituras)
    registro.registrar_evento(resumo.execucao_id, "leituras_lidas", {
        "quantidade": len(pendentes),
        "primeira_leitura_id": int(pendentes["id"].min()) if len(pendentes) else None,
        "ultima_leitura_id": int(pendentes["id"].max()) if len(pendentes) else None,
    }, agora)
    if pendentes.empty:
        return [], [], None

    base = br.buscar_leituras_modelo(con, desde=br.iso_utc(agora - timedelta(days=JANELA_TREINO_DIAS)))
    primeiro_dia = datetime.fromisoformat(base["medido_em"].min()).date() - timedelta(days=6)
    adesao = br.buscar_adesao(con, desde=primeiro_dia.isoformat())
    features = preparar_features(base, adesao).set_index("id", drop=False)

    resultado = detector.avaliar(features, pendentes["id"].tolist())
    resumo.modelo_treinado = resultado.treinado
    tipo_evento = "modelo_treinado" if resultado.treinado else "modelo_nao_treinado"
    registro.registrar_evento(resumo.execucao_id, tipo_evento, resultado.metadados, agora)

    analises, candidatos = [], []
    estados: dict[tuple[int, str], list[_Candidato]] = {}
    for leitura in pendentes.itertuples(index=False):
        leitura_id, paciente_id = int(leitura.id), int(leitura.paciente_id)
        linha = features.loc[leitura_id]
        pontuacao = resultado.pontuacoes.get(leitura_id)
        score = pontuacao.score if pontuacao else None
        ia_marcou = bool(pontuacao and pontuacao.anomalia)
        resumo.anomalias_ia += int(ia_marcou)

        analises.append(br.AnaliseLeitura(
            leitura_id=leitura_id, execucao_id=resumo.execucao_id, analisado_em=br.iso_utc(agora),
            adesao_7d=round(float(linha["adesao_7d"]), 4), score_anomalia=score,
            anomalia_ia=pontuacao.anomalia if pontuacao else None,
        ))

        regras = avaliar_sinais(int(leitura.pressao_sistolica), int(leitura.pressao_diastolica),
                                int(leitura.frequencia_cardiaca))
        for regra in regras:
            candidato = _candidato(regra, "regra+ia" if ia_marcou else "regra", paciente_id, codigos,
                                   resumo.execucao_id, agora, leitura_id=leitura_id, score=score)
            if regra.tipo in TIPOS_ESTADO:
                estados.setdefault((paciente_id, regra.tipo), []).append(candidato)
            else:
                candidatos.append(candidato)
        if ia_marcou and not regras:
            regra_ia = AlertaRegra("padrao_atipico", "moderada", descrever_anomalia(linha, score))
            candidatos.append(_candidato(regra_ia, "ia", paciente_id, codigos, resumo.execucao_id, agora,
                                         leitura_id=leitura_id, score=score))

    desde = br.iso_utc(agora - timedelta(hours=JANELA_ALERTA_ESTADO_HORAS))
    for (paciente_id, tipo), grupo in sorted(estados.items()):
        if not br.existe_alerta_recente(con, paciente_id, tipo, desde):
            candidatos.append(_consolidar_estado(grupo))

    for paciente_id in sorted({int(p) for p in pendentes["paciente_id"]}):
        tomadas, prescritas = doses_na_janela_7d(adesao, paciente_id, agora.date())
        regra = avaliar_adesao(tomadas, prescritas)
        if regra and not br.existe_alerta_recente(con, paciente_id, regra.tipo, desde):
            candidatos.append(_candidato(regra, "regra", paciente_id, codigos, resumo.execucao_id, agora))

    return analises, candidatos, resultado.metadados


def _consolidar_estado(grupo: list[_Candidato]) -> _Candidato:
    """Um alerta pela leitura mais recente do grupo, dizendo quantas leituras repetiram o achado."""
    ultimo = grupo[-1]
    if len(grupo) == 1:
        return ultimo
    descricao = f"{ultimo.alerta.descricao} {len(grupo)} leituras acima da referência neste ciclo; esta é a mais recente."
    return replace(ultimo, alerta=replace(ultimo.alerta, descricao=descricao))


def _interpretar_mensagens(registro, vocabulario, resumo, agora, codigos, candidatos):
    ids_por_codigo = {codigo: paciente_id for paciente_id, codigo in codigos.items()}
    processadas = []
    for mensagem in registro.buscar_mensagens_pendentes(LOTE_MENSAGENS):
        mensagem_id = str(mensagem["_id"])
        codigo = mensagem.get("paciente_codigo")
        texto = mensagem.get("texto")
        paciente_id = ids_por_codigo.get(codigo)

        # Documento mal formado não pode travar a fila: vira rejeitado e sai da fila.
        motivo = None
        if paciente_id is None:
            motivo = f"paciente {codigo} fora do cadastro relacional"
        elif not isinstance(texto, str) or not texto.strip():
            motivo = "mensagem sem texto"
        if motivo:
            registro.concluir_mensagem(mensagem_id, "rejeitada", resumo.execucao_id, agora, motivo=motivo)
            registro.registrar_evento(resumo.execucao_id, "mensagem_rejeitada",
                                      {"mensagem_id": mensagem_id, "motivo": motivo}, agora)
            resumo.mensagens_rejeitadas += 1
            continue

        interpretacao = interpretar_mensagem(texto, vocabulario)
        regra = alerta_da_interpretacao(interpretacao)
        if regra:
            candidatos.append(_candidato(regra, "texto", paciente_id, codigos, resumo.execucao_id, agora,
                                         mensagem_id=mensagem_id))
        processadas.append((mensagem_id, codigo, interpretacao))
    return processadas


def _registrar_alertas(registro, resumo, candidatos, ids, agora):
    detalhes = []
    for candidato, alerta_id in zip(candidatos, ids):
        if alerta_id is None:  # já existia: reprocessamento não duplica alerta nem evento
            continue
        alerta = candidato.alerta
        detalhes.append({
            "alerta_id": alerta_id,
            "tipo_alerta": alerta.tipo,
            "severidade": alerta.severidade,
            "origem_deteccao": alerta.origem_deteccao,
            "paciente_codigo": candidato.paciente_codigo,
            "leitura_id": alerta.leitura_id,
            "mensagem_id": alerta.mensagem_id,
            "score_anomalia": alerta.score_anomalia,
        })
    registro.registrar_eventos(resumo.execucao_id, "alerta_gerado", detalhes, agora)
    resumo.alertas_gerados = len(detalhes)
    resumo.alertas_por_tipo = dict(Counter(d["tipo_alerta"] for d in detalhes))


def _concluir_mensagens(registro, resumo, mensagens, candidatos, ids, agora):
    alerta_da_mensagem = {c.alerta.mensagem_id: i for c, i in zip(candidatos, ids) if c.alerta.mensagem_id}
    for mensagem_id, codigo, interpretacao in mensagens:
        alerta_id = alerta_da_mensagem.get(mensagem_id)
        registro.concluir_mensagem(mensagem_id, "processada", resumo.execucao_id, agora,
                                   interpretacao=asdict(interpretacao), alerta_id=alerta_id)
        registro.registrar_evento(resumo.execucao_id, "mensagem_interpretada", {
            "mensagem_id": mensagem_id, "paciente_codigo": codigo, **asdict(interpretacao), "alerta_id": alerta_id,
        }, agora)
    resumo.mensagens_processadas = len(mensagens)
