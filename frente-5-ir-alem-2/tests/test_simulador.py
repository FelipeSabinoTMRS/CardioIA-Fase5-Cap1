"""Testes do gerador de dados clínicos simulados."""

from datetime import datetime, timedelta, timezone

import simulador

AGORA = datetime(2026, 9, 15, 12, 0, tzinfo=timezone.utc)


def por_paciente(registros, codigo):
    return [r for r in registros if r["paciente_codigo"] == codigo]


def adesao_ultimos_7_dias(adesao, codigo):
    limite = (AGORA.date() - timedelta(days=6)).isoformat()
    janela = [r for r in por_paciente(adesao, codigo) if r["data"] >= limite]
    return sum(r["doses_tomadas"] for r in janela) / sum(r["doses_prescritas"] for r in janela)


def test_mesma_semente_gera_os_mesmos_dados():
    assert simulador.gerar_historico(AGORA, dias=30, semente=42) == simulador.gerar_historico(AGORA, dias=30, semente=42)


def test_historico_nao_depende_da_hora_em_que_o_ambiente_foi_preparado():
    madrugada = datetime(2026, 9, 15, 1, 5, tzinfo=timezone.utc)
    noite = datetime(2026, 9, 15, 23, 50, tzinfo=timezone.utc)
    assert simulador.gerar_historico(madrugada) == simulador.gerar_historico(noite)


def test_historico_cobre_dias_completos_ate_ontem_as_8h_e_20h_utc():
    dados = simulador.gerar_historico(AGORA, dias=30)
    ontem = AGORA.date() - timedelta(days=1)

    assert {datetime.fromisoformat(r["medido_em"]).strftime("%H:%M") for r in dados.leituras} == {"08:00", "20:00"}
    assert max(r["data"] for r in dados.adesao) == ontem.isoformat()
    assert min(r["data"] for r in dados.adesao) == (ontem - timedelta(days=29)).isoformat()


def test_historico_tem_duas_leituras_por_dia_e_uma_linha_de_adesao_por_dia():
    dados = simulador.gerar_historico(AGORA, dias=30)
    codigos = [p["codigo"] for p in dados.pacientes]

    assert len(codigos) == len(set(codigos)) == 8
    assert len(dados.leituras) == 8 * 2 * 30
    assert len(dados.adesao) == 8 * 30


def test_leituras_respeitam_as_restricoes_do_schema_e_ficam_no_passado():
    dados = simulador.gerar_historico(AGORA, dias=30)
    for r in dados.leituras:
        assert 50 <= r["pressao_sistolica"] <= 300
        assert 30 <= r["pressao_diastolica"] <= 200
        assert 20 <= r["frequencia_cardiaca"] <= 250
        assert r["pressao_sistolica"] > r["pressao_diastolica"]
        assert datetime.fromisoformat(r["medido_em"]) < AGORA
    for r in dados.adesao:
        assert 0 <= r["doses_tomadas"] <= r["doses_prescritas"]


def test_cenarios_de_atencao_estao_no_historico():
    dados = simulador.gerar_historico(AGORA, dias=30)

    assert any(r["pressao_sistolica"] >= 180 for r in por_paciente(dados.leituras, "PAC-004"))
    assert any(r["frequencia_cardiaca"] > 120 for r in por_paciente(dados.leituras, "PAC-003"))
    assert any(r["frequencia_cardiaca"] < 50 for r in por_paciente(dados.leituras, "PAC-008"))
    assert adesao_ultimos_7_dias(dados.adesao, "PAC-002") < 0.8
    assert adesao_ultimos_7_dias(dados.adesao, "PAC-001") >= 0.8
    atipicas = [r for r in por_paciente(dados.leituras, "PAC-007") if r["frequencia_cardiaca"] >= 90]
    assert atipicas and all(r["pressao_sistolica"] < 140 for r in atipicas)


def test_com_ids_troca_codigo_por_id_do_banco():
    registros = [{"paciente_codigo": "PAC-001", "valor": 1}]
    assert simulador.com_ids(registros, {"PAC-001": 7}) == [{"paciente_id": 7, "valor": 1}]


def test_novas_leituras_chegam_no_instante_informado():
    novas = simulador.gerar_novas_leituras(AGORA, quantidade=5, semente=1)

    assert len(novas) == 5
    assert all(r["medido_em"] == AGORA.isoformat() for r in novas)
    assert all(r["pressao_sistolica"] > r["pressao_diastolica"] for r in novas)
    assert simulador.gerar_novas_leituras(AGORA, quantidade=5, semente=1) == novas


def test_mensagens_iniciais_trazem_alerta_negacao_e_paciente_fora_do_cadastro():
    mensagens = simulador.mensagens_iniciais(AGORA)
    textos = " | ".join(m["texto"].lower() for m in mensagens)
    codigos = {p["codigo"] for p in simulador.gerar_historico(AGORA).pacientes}

    assert "aperto no peito" in textos
    assert "sem dor no peito" in textos
    assert any(m["paciente_codigo"] not in codigos for m in mensagens)
    assert all(m["recebida_em"] < AGORA for m in mensagens)
