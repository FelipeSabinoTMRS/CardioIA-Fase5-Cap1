"""Testes contra o MongoDB real do docker-compose. São pulados se o banco não estiver no ar.

Cada execução usa um banco descartável (``cardioia_rpa_teste_<hash>``), apagado no final.
"""

import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest

import banco_relacional as br
import simulador
from banco_nosql import MAP_ALERTAS, REDUCE_ALERTAS, MongoIndisponivel, RegistroNoSQL
from ciclo_robo import executar_ciclo
from config import Config
from interpretacao_texto import carregar_vocabulario

pytestmark = pytest.mark.integracao

AGORA = datetime(2026, 9, 15, 12, 0, tzinfo=timezone.utc)


@pytest.fixture(scope="module")
def mongo_uri():
    cfg = Config.carregar()
    try:
        RegistroNoSQL.conectar(cfg.mongo_uri, "admin", timeout_ms=1500).db.client.close()
    except MongoIndisponivel:
        pytest.skip("MongoDB não está rodando (docker compose up -d)")
    return cfg.mongo_uri


@pytest.fixture
def registro_real(mongo_uri):
    nome = f"cardioia_rpa_teste_{uuid.uuid4().hex[:8]}"
    registro = RegistroNoSQL.conectar(mongo_uri, nome)
    yield registro
    registro.db.client.drop_database(nome)
    registro.db.client.close()


def test_map_reduce_roda_no_servidor_e_conta_alertas_por_tipo(registro_real):
    registro_real.registrar_eventos("exec-integracao", "alerta_gerado", [
        {"tipo_alerta": "crise_hipertensiva"}, {"tipo_alerta": "crise_hipertensiva"}, {"tipo_alerta": "taquicardia"},
    ], AGORA)
    registro_real.registrar_evento("exec-integracao", "leituras_lidas", {"quantidade": 3}, AGORA)

    resposta = registro_real.db.command(
        "mapReduce", "eventos", map=MAP_ALERTAS, reduce=REDUCE_ALERTAS,
        query={"tipo": "alerta_gerado"}, out={"inline": 1},
    )

    assert {item["_id"]: item["value"] for item in resposta["results"]} == {"crise_hipertensiva": 2, "taquicardia": 1}
    assert registro_real.resumo_alertas_por_tipo() == {"crise_hipertensiva": 2, "taquicardia": 1}
    assert registro_real.resumo_alertas_por_tipo(usar_map_reduce=False) == {"crise_hipertensiva": 2, "taquicardia": 1}


def test_datas_voltam_do_servidor_com_fuso_utc(registro_real):
    registro_real.iniciar_execucao("exec-fuso", AGORA)
    assert registro_real.buscar_execucao("exec-fuso")["inicio"] == AGORA


def test_ciclo_completo_com_sqlite_e_mongodb_reais(registro_real, tmp_path):
    con = br.conectar(tmp_path / "integracao.db")
    br.criar_schema(con)
    dados = simulador.gerar_historico(AGORA)
    ids = br.inserir_pacientes(con, dados.pacientes)
    br.inserir_leituras(con, simulador.com_ids(dados.leituras, ids))
    br.inserir_adesao(con, simulador.com_ids(dados.adesao, ids))
    registro_real.inserir_mensagens(simulador.mensagens_iniciais(AGORA))
    vocabulario = carregar_vocabulario(Path(__file__).resolve().parents[2] / "frente-1-watson" / "cardioia-skill.json")

    resumo = executar_ciclo(con, registro_real, vocabulario, agora=AGORA)

    execucao = registro_real.buscar_execucao(resumo.execucao_id)
    assert execucao["status"] == "concluida"
    assert execucao["metricas"]["alertas_gerados"] == resumo.alertas_gerados
    eventos = registro_real.eventos_da_execucao(resumo.execucao_id)
    assert sum(e["tipo"] == "alerta_gerado" for e in eventos) == resumo.alertas_gerados
    assert registro_real.resumo_alertas_por_tipo() == resumo.alertas_por_tipo
    assert registro_real.buscar_mensagens_pendentes(limite=100) == []
    con.close()
