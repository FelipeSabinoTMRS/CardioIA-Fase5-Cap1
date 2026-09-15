"""Testes da interpretação de mensagens com o vocabulário da skill Watson (Frente 1)."""

from pathlib import Path

import pytest

from interpretacao_texto import alerta_da_interpretacao, carregar_vocabulario, interpretar_mensagem

SKILL_WATSON = Path(__file__).resolve().parents[2] / "frente-1-watson" / "cardioia-skill.json"


@pytest.fixture(scope="module")
def vocabulario():
    return carregar_vocabulario(SKILL_WATSON)


def test_vocabulario_usa_as_entidades_clinicas_da_skill(vocabulario):
    entidades = {entidade for entidade, _, _ in vocabulario.termos}
    assert entidades == {"sinal_alerta", "sintoma", "medicamento"}
    assert len(vocabulario.hash_skill) == 12


def test_sinonimo_da_skill_vira_valor_canonico(vocabulario):
    r = interpretar_mensagem("Ontem à noite senti um aperto no peito e fiquei suando", vocabulario)
    assert r.sinais_alerta == ["dor no peito"]


def test_acentos_e_maiusculas_nao_atrapalham(vocabulario):
    r = interpretar_mensagem("DOR TORACICA desde cedo", vocabulario)
    assert r.sinais_alerta == ["dor no peito"]


def test_negacao_antes_do_termo_nao_conta_como_relato(vocabulario):
    r = interpretar_mensagem("Hoje estou bem, sem dor no peito e não tenho falta de ar", vocabulario)
    assert r.sinais_alerta == []
    assert r.sintomas == []
    assert sorted(r.negados) == ["dor no peito", "falta de ar"]


def test_negacao_nao_atravessa_pontuacao(vocabulario):
    r = interpretar_mensagem("Não, estou com dor no peito agora", vocabulario)
    assert r.sinais_alerta == ["dor no peito"]
    assert r.negados == []


def test_negacao_que_faz_parte_do_sinonimo_continua_valendo(vocabulario):
    r = interpretar_mensagem("Socorro, não consigo respirar", vocabulario)
    assert r.sinais_alerta == ["falta de ar intensa"]


def test_termo_mais_longo_prevalece_sobre_termo_contido_nele(vocabulario):
    r = interpretar_mensagem("Estou com muita falta de ar", vocabulario)
    assert r.sinais_alerta == ["falta de ar intensa"]
    assert r.sintomas == []


def test_extrai_sintoma_e_medicamento(vocabulario):
    r = interpretar_mensagem("Fiquei tonta e esqueci de tomar a losartana", vocabulario)
    assert r.sintomas == ["tontura"]
    assert r.medicamentos == ["losartana"]
    assert r.sinais_alerta == []


def test_termo_dentro_de_outra_palavra_nao_casa(vocabulario):
    r = interpretar_mensagem("A dieta foi um fracasso", vocabulario)
    assert r.sintomas == []


def test_valor_repetido_aparece_uma_vez(vocabulario):
    r = interpretar_mensagem("Tontura de manhã e tontura à noite", vocabulario)
    assert r.sintomas == ["tontura"]


def test_sinal_de_alerta_gera_alerta_critico(vocabulario):
    r = interpretar_mensagem("Meu braço dormente e a boca torta", vocabulario)
    alerta = alerta_da_interpretacao(r)
    assert alerta.tipo == "sinal_alerta_relatado"
    assert alerta.severidade == "critica"
    assert "sinais de AVC" in alerta.descricao
    assert "192" in alerta.descricao


def test_sintoma_sem_sinal_de_alerta_gera_alerta_moderado(vocabulario):
    alerta = alerta_da_interpretacao(interpretar_mensagem("Coração disparado depois do café", vocabulario))
    assert alerta.tipo == "sintoma_relatado"
    assert alerta.severidade == "moderada"
    assert "palpitação" in alerta.descricao


def test_mensagem_sem_termo_clinico_nao_gera_alerta(vocabulario):
    r = interpretar_mensagem("Queria confirmar o horário da consulta", vocabulario)
    assert alerta_da_interpretacao(r) is None


def test_medicamento_sozinho_nao_gera_alerta(vocabulario):
    assert alerta_da_interpretacao(interpretar_mensagem("Tomei o atenolol", vocabulario)) is None
