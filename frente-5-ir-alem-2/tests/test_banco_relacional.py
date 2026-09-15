"""Testes da camada relacional (SQLite) com banco temporário em disco."""

import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

import banco_relacional as br
from banco_relacional import AnaliseLeitura, NovoAlerta

AGORA = "2026-09-15T12:00:00+00:00"


@pytest.fixture
def con(tmp_path):
    conexao = br.conectar(tmp_path / "dados" / "teste.db")
    br.criar_schema(conexao)
    yield conexao
    conexao.close()


@pytest.fixture
def paciente_id(con):
    ids = br.inserir_pacientes(con, [{
        "codigo": "PAC-001", "nome_ficticio": "Paciente Teste", "idade": 60,
        "condicao_base": "hipertensão", "medicamento_continuo": "losartana", "criado_em": AGORA,
    }])
    return ids["PAC-001"]


def leitura(paciente_id, medido_em="2026-09-15T08:00:00+00:00", sistolica=120, diastolica=80, fc=70):
    return {"paciente_id": paciente_id, "medido_em": medido_em, "pressao_sistolica": sistolica,
            "pressao_diastolica": diastolica, "frequencia_cardiaca": fc, "origem": "teste"}


def analise(leitura_id, execucao_id="exec-1"):
    return AnaliseLeitura(leitura_id=leitura_id, execucao_id=execucao_id, analisado_em=AGORA,
                          adesao_7d=1.0, score_anomalia=0.12, anomalia_ia=False)


def alerta(paciente_id, leitura_id=None, severidade="critica", tipo="crise_hipertensiva"):
    return NovoAlerta(paciente_id=paciente_id, execucao_id="exec-1", tipo=tipo, severidade=severidade,
                      origem_deteccao="regra", descricao="PA 185/100 mmHg", criado_em=AGORA,
                      leitura_id=leitura_id)


def ids_das_leituras(con):
    return [r[0] for r in con.execute("SELECT id FROM leituras_sinais ORDER BY id")]


def test_conectar_cria_a_pasta_e_ativa_wal_e_chaves_estrangeiras(tmp_path):
    conexao = br.conectar(tmp_path / "nova_pasta" / "banco.db")
    try:
        assert conexao.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
        assert conexao.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    finally:
        conexao.close()


def test_criar_schema_cria_as_tabelas_e_pode_rodar_de_novo(con):
    br.criar_schema(con)
    tabelas = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    assert {"pacientes", "leituras_sinais", "adesao_tratamento", "analises_leitura", "alertas"} <= tabelas


def test_leitura_de_paciente_inexistente_e_recusada(con):
    with pytest.raises(sqlite3.IntegrityError):
        br.inserir_leituras(con, [leitura(paciente_id=999)])


def test_valor_fisiologicamente_impossivel_e_recusado(con, paciente_id):
    with pytest.raises(sqlite3.IntegrityError):
        br.inserir_leituras(con, [leitura(paciente_id, sistolica=400)])


def test_leituras_pendentes_ignoram_as_analisadas_e_seguem_a_ordem_de_medicao(con, paciente_id):
    br.inserir_leituras(con, [
        leitura(paciente_id, "2026-09-15T10:00:00+00:00"),
        leitura(paciente_id, "2026-09-15T08:00:00+00:00"),
        leitura(paciente_id, "2026-09-15T12:00:00+00:00"),
    ])
    id_10h, id_8h, id_12h = ids_das_leituras(con)
    br.registrar_resultados(con, [analise(id_8h)], [])

    pendentes = br.buscar_leituras_pendentes(con, limite=10)

    assert pendentes["id"].tolist() == [id_10h, id_12h]
    assert pendentes["paciente_codigo"].tolist() == ["PAC-001", "PAC-001"]
    assert br.buscar_leituras_pendentes(con, limite=1)["id"].tolist() == [id_10h]


def test_leituras_do_modelo_trazem_a_janela_e_as_pendentes_antigas(con, paciente_id):
    br.inserir_leituras(con, [
        leitura(paciente_id, "2026-07-01T08:00:00+00:00"),  # antiga e analisada: fica fora
        leitura(paciente_id, "2026-07-02T08:00:00+00:00"),  # antiga e pendente: entra
        leitura(paciente_id, "2026-09-10T08:00:00+00:00"),  # dentro da janela: entra
    ])
    antiga_analisada, antiga_pendente, recente = ids_das_leituras(con)
    br.registrar_resultados(con, [analise(antiga_analisada)], [])

    janela = br.buscar_leituras_modelo(con, desde="2026-08-16T12:00:00+00:00")

    assert janela["id"].tolist() == [antiga_pendente, recente]


def test_registrar_resultados_grava_analises_e_alertas(con, paciente_id):
    br.inserir_leituras(con, [leitura(paciente_id, sistolica=185, diastolica=100)])
    (leitura_id,) = ids_das_leituras(con)

    ids = br.registrar_resultados(con, [analise(leitura_id)], [alerta(paciente_id, leitura_id)])

    assert len(ids) == 1 and isinstance(ids[0], int)
    assert con.execute("SELECT COUNT(*) FROM analises_leitura").fetchone()[0] == 1
    linha = con.execute("SELECT tipo, execucao_id, status FROM alertas WHERE id = ?", (ids[0],)).fetchone()
    assert tuple(linha) == ("crise_hipertensiva", "exec-1", "aberto")


def test_falha_em_um_alerta_desfaz_as_analises_do_mesmo_ciclo(con, paciente_id):
    br.inserir_leituras(con, [leitura(paciente_id)])
    (leitura_id,) = ids_das_leituras(con)

    with pytest.raises(sqlite3.IntegrityError):
        br.registrar_resultados(con, [analise(leitura_id)], [alerta(paciente_id, leitura_id, severidade="grave")])

    assert con.execute("SELECT COUNT(*) FROM analises_leitura").fetchone()[0] == 0


def test_reprocessar_o_mesmo_resultado_nao_duplica(con, paciente_id):
    br.inserir_leituras(con, [leitura(paciente_id, sistolica=185, diastolica=100)])
    (leitura_id,) = ids_das_leituras(con)
    br.registrar_resultados(con, [analise(leitura_id)], [alerta(paciente_id, leitura_id)])

    ids = br.registrar_resultados(con, [analise(leitura_id, "exec-2")], [alerta(paciente_id, leitura_id)])

    assert ids == [None]
    assert con.execute("SELECT COUNT(*) FROM alertas").fetchone()[0] == 1
    assert con.execute("SELECT execucao_id FROM analises_leitura").fetchone()[0] == "exec-1"


def test_existe_alerta_recente_filtra_paciente_tipo_e_data(con, paciente_id):
    br.registrar_resultados(con, [], [alerta(paciente_id, tipo="baixa_adesao", severidade="moderada")])

    assert br.existe_alerta_recente(con, paciente_id, "baixa_adesao", desde="2026-09-14T12:00:00+00:00")
    assert not br.existe_alerta_recente(con, paciente_id, "baixa_adesao", desde="2026-09-15T13:00:00+00:00")
    assert not br.existe_alerta_recente(con, paciente_id, "crise_hipertensiva", desde="2026-09-14T12:00:00+00:00")


def test_adesao_e_filtrada_a_partir_da_data(con, paciente_id):
    br.inserir_adesao(con, [
        {"paciente_id": paciente_id, "data": "2026-09-01", "doses_prescritas": 2, "doses_tomadas": 2},
        {"paciente_id": paciente_id, "data": "2026-09-10", "doses_prescritas": 2, "doses_tomadas": 1},
    ])
    adesao = br.buscar_adesao(con, desde="2026-09-05")
    assert adesao["data"].tolist() == ["2026-09-10"]
    assert adesao["doses_tomadas"].tolist() == [1]


def test_rastrear_alerta_junta_paciente_leitura_e_analise(con, paciente_id):
    br.inserir_leituras(con, [leitura(paciente_id, sistolica=185, diastolica=100)])
    (leitura_id,) = ids_das_leituras(con)
    (alerta_id,) = br.registrar_resultados(con, [analise(leitura_id)], [alerta(paciente_id, leitura_id)])

    rastro = br.rastrear_alerta(con, alerta_id)

    assert rastro["alerta"]["execucao_id"] == "exec-1"
    assert rastro["paciente"]["codigo"] == "PAC-001"
    assert rastro["leitura"]["pressao_sistolica"] == 185
    assert rastro["analise"]["score_anomalia"] == 0.12
    assert br.rastrear_alerta(con, 12345) is None


def test_mapa_de_codigos_de_paciente(con, paciente_id):
    assert br.ids_por_codigo(con) == {"PAC-001": paciente_id}


def test_alertas_da_execucao_vem_do_mais_grave_para_o_menos_grave(con, paciente_id):
    br.registrar_resultados(con, [], [
        alerta(paciente_id, tipo="pressao_elevada", severidade="moderada"),
        alerta(paciente_id, tipo="crise_hipertensiva", severidade="critica"),
    ])

    alertas = br.alertas_da_execucao(con, "exec-1")

    assert [a["tipo"] for a in alertas] == ["crise_hipertensiva", "pressao_elevada"]
    assert alertas[0]["paciente_codigo"] == "PAC-001"
    assert br.alertas_da_execucao(con, "exec-inexistente") == []


def test_resumo_de_alertas_abertos_por_paciente_e_severidade(con, paciente_id):
    br.registrar_resultados(con, [], [
        alerta(paciente_id, tipo="crise_hipertensiva", severidade="critica"),
        alerta(paciente_id, tipo="crise_hipertensiva", severidade="critica"),
        alerta(paciente_id, tipo="pressao_elevada", severidade="moderada"),
    ])

    resumo = br.resumo_alertas_abertos(con)

    linha = resumo.iloc[0]
    assert linha["paciente_codigo"] == "PAC-001"
    assert (linha["critica"], linha["alta"], linha["moderada"], linha["total"]) == (2, 0, 1, 3)


def test_dados_dos_graficos_juntam_leitura_analise_e_alertas(con, paciente_id):
    br.inserir_leituras(con, [leitura(paciente_id, sistolica=185, diastolica=100), leitura(paciente_id)])
    critica, normal = ids_das_leituras(con)
    br.registrar_resultados(con, [analise(critica), analise(normal)], [alerta(paciente_id, critica)])

    leituras = br.leituras_analisadas(con)
    contagem = br.contagem_alertas(con)

    assert set(leituras.columns) >= {"paciente_codigo", "pressao_sistolica", "frequencia_cardiaca",
                                     "score_anomalia", "anomalia_ia"}
    assert len(leituras) == 2
    assert contagem.to_dict("records") == [{"tipo": "crise_hipertensiva", "origem_deteccao": "regra", "total": 1}]


def test_iso_utc_padroniza_datas_em_utc_e_sem_microssegundos():
    horario_de_brasilia = datetime(2026, 9, 15, 9, 30, 15, 123456, tzinfo=timezone(timedelta(hours=-3)))
    assert br.iso_utc(horario_de_brasilia) == "2026-09-15T12:30:15+00:00"
