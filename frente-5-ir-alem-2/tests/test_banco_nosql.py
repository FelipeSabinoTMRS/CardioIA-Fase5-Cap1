"""Testes da camada não relacional com mongomock (MongoDB em memória, sem Docker)."""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import mongomock
import pytest

from banco_nosql import COLECOES, MongoIndisponivel, RegistroNoSQL

INICIO = datetime(2026, 9, 15, 12, 0, tzinfo=timezone.utc)


@pytest.fixture
def registro():
    return RegistroNoSQL(mongomock.MongoClient()["cardioia_rpa_teste"])


def test_execucao_concluida_guarda_parametros_metricas_e_duracao(registro):
    registro.iniciar_execucao("exec-1", INICIO, parametros={"lote": 500}, versao_robo="1.0.0")
    assert registro.buscar_execucao("exec-1")["status"] == "em_execucao"

    registro.concluir_execucao("exec-1", INICIO + timedelta(seconds=2), 2.0, metricas={"alertas_gerados": 3})

    execucao = registro.buscar_execucao("exec-1")
    assert execucao["status"] == "concluida"
    assert execucao["parametros"] == {"lote": 500}
    assert execucao["versao_robo"] == "1.0.0"
    assert execucao["metricas"] == {"alertas_gerados": 3}
    assert execucao["duracao_s"] == 2.0


def test_execucao_com_erro_guarda_tipo_mensagem_e_evento(registro):
    registro.iniciar_execucao("exec-1", INICIO)

    registro.falhar_execucao("exec-1", ValueError("banco travado"), INICIO + timedelta(seconds=1), 1.0)

    execucao = registro.buscar_execucao("exec-1")
    assert execucao["status"] == "erro"
    assert execucao["erro"] == {"tipo": "ValueError", "mensagem": "banco travado"}
    assert [e["tipo"] for e in registro.eventos_da_execucao("exec-1")] == ["erro"]


def test_execucao_aberta_de_rodada_anterior_vira_interrompida(registro):
    registro.iniciar_execucao("exec-antiga", INICIO)
    registro.iniciar_execucao("exec-ok", INICIO)
    registro.concluir_execucao("exec-ok", INICIO, 0.1)

    quantidade = registro.marcar_execucoes_interrompidas(INICIO + timedelta(hours=1))

    assert quantidade == 1
    assert registro.buscar_execucao("exec-antiga")["status"] == "interrompida"
    assert registro.buscar_execucao("exec-ok")["status"] == "concluida"


def test_eventos_ficam_ligados_a_execucao_na_ordem_em_que_ocorreram(registro):
    registro.registrar_evento("exec-1", "leituras_lidas", {"quantidade": 3}, INICIO)
    registro.registrar_eventos("exec-1", "alerta_gerado",
                               [{"tipo_alerta": "crise_hipertensiva"}, {"tipo_alerta": "taquicardia"}],
                               INICIO + timedelta(seconds=1))
    registro.registrar_evento("exec-2", "leituras_lidas", {"quantidade": 0}, INICIO)

    eventos = registro.eventos_da_execucao("exec-1")

    assert [e["tipo"] for e in eventos] == ["leituras_lidas", "alerta_gerado", "alerta_gerado"]
    assert eventos[1]["detalhes"] == {"tipo_alerta": "crise_hipertensiva"}


def test_registrar_lista_vazia_de_eventos_nao_falha(registro):
    registro.registrar_eventos("exec-1", "alerta_gerado", [], INICIO)
    assert registro.eventos_da_execucao("exec-1") == []


def test_mensagem_nova_entra_pendente_e_sai_da_fila_quando_processada(registro):
    ids = registro.inserir_mensagens([
        {"paciente_codigo": "PAC-002", "texto": "segunda", "recebida_em": INICIO + timedelta(minutes=5)},
        {"paciente_codigo": "PAC-001", "texto": "primeira", "recebida_em": INICIO},
    ])

    pendentes = registro.buscar_mensagens_pendentes(limite=10)
    assert [m["texto"] for m in pendentes] == ["primeira", "segunda"]
    assert all(m["status"] == "pendente" for m in pendentes)

    registro.concluir_mensagem(ids[1], "processada", "exec-1", INICIO,
                               interpretacao={"sintomas": ["tontura"]}, alerta_id=7)

    assert [m["texto"] for m in registro.buscar_mensagens_pendentes(limite=10)] == ["segunda"]
    mensagem = registro.buscar_mensagem(ids[1])
    assert mensagem["status"] == "processada"
    assert mensagem["execucao_id"] == "exec-1"
    assert mensagem["interpretacao"] == {"sintomas": ["tontura"]}
    assert mensagem["alerta_id"] == 7


def test_resumo_de_alertas_por_tipo_pela_agregacao(registro):
    registro.registrar_eventos("exec-1", "alerta_gerado", [
        {"tipo_alerta": "crise_hipertensiva"}, {"tipo_alerta": "crise_hipertensiva"}, {"tipo_alerta": "taquicardia"},
    ], INICIO)
    registro.registrar_evento("exec-1", "leituras_lidas", {"quantidade": 3}, INICIO)

    assert registro.resumo_alertas_por_tipo(usar_map_reduce=False) == {"crise_hipertensiva": 2, "taquicardia": 1}


def test_indices_das_consultas_do_robo(registro):
    registro.criar_indices()
    chaves_eventos = [info["key"] for info in registro.db.eventos.index_information().values()]
    chaves_mensagens = [info["key"] for info in registro.db.mensagens_pacientes.index_information().values()]
    assert [("execucao_id", 1), ("registrado_em", 1)] in chaves_eventos
    assert [("status", 1), ("recebida_em", 1)] in chaves_mensagens


def test_estrutura_documentada_bate_com_colecoes_e_indices_do_codigo(registro):
    estrutura = json.loads((Path(__file__).resolve().parents[1] / "estrutura_nosql.json").read_text(encoding="utf-8"))
    registro.criar_indices()

    assert set(estrutura["colecoes"]) == set(COLECOES)
    for nome, descricao in estrutura["colecoes"].items():
        criados = sorted(info["key"] for info in registro.db[nome].index_information().values() if info["key"] != [("_id", 1)])
        documentados = sorted([tuple(par) for par in indice] for indice in descricao["indices"])
        assert documentados == [[tuple(par) for par in chave] for chave in criados], nome
        assert descricao["exemplos"], nome


def test_apagar_tudo_limpa_as_colecoes_do_robo(registro):
    registro.iniciar_execucao("exec-1", INICIO)
    registro.inserir_mensagens([{"paciente_codigo": "PAC-001", "texto": "oi", "recebida_em": INICIO}])

    registro.apagar_tudo()

    assert registro.buscar_execucao("exec-1") is None
    assert registro.buscar_mensagens_pendentes(limite=10) == []


def test_servidor_fora_do_ar_gera_erro_com_instrucao_para_subir_o_mongo():
    with pytest.raises(MongoIndisponivel, match="docker compose up -d"):
        RegistroNoSQL.conectar("mongodb://127.0.0.1:1/", "cardioia_rpa", timeout_ms=300)
