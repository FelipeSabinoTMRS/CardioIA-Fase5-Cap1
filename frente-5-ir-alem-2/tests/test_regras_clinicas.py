"""Testes das regras clínicas determinísticas (limiares alinhados à Frente 1)."""

from regras_clinicas import LIMIARES, avaliar_adesao, avaliar_sinais


def tipos(alertas):
    return sorted(a.tipo for a in alertas)


def test_leitura_na_referencia_nao_gera_alerta():
    assert avaliar_sinais(120, 80, 72) == []


def test_sistolica_a_partir_de_180_e_crise_hipertensiva_critica():
    alertas = avaliar_sinais(185, 100, 80)
    assert tipos(alertas) == ["crise_hipertensiva"]
    assert alertas[0].severidade == "critica"
    assert "185/100" in alertas[0].descricao


def test_diastolica_a_partir_de_120_tambem_e_crise():
    assert tipos(avaliar_sinais(130, 122, 80)) == ["crise_hipertensiva"]


def test_pressao_elevada_pela_sistolica_ou_pela_diastolica():
    assert tipos(avaliar_sinais(145, 85, 80)) == ["pressao_elevada"]
    assert tipos(avaliar_sinais(135, 92, 80)) == ["pressao_elevada"]
    assert avaliar_sinais(145, 85, 80)[0].severidade == "moderada"


def test_limite_exato_de_140_por_90_ja_e_elevada():
    assert tipos(avaliar_sinais(140, 80, 70)) == ["pressao_elevada"]
    assert tipos(avaliar_sinais(139, 89, 70)) == []


def test_pressao_baixa_e_alta_severidade():
    alertas = avaliar_sinais(85, 58, 70)
    assert tipos(alertas) == ["pressao_baixa"]
    assert alertas[0].severidade == "alta"


def test_taquicardia_moderada_acima_de_100_e_alta_a_partir_de_130():
    moderada = avaliar_sinais(120, 80, 110)
    alta = avaliar_sinais(120, 80, 135)
    assert tipos(moderada) == ["taquicardia"] and moderada[0].severidade == "moderada"
    assert tipos(alta) == ["taquicardia"] and alta[0].severidade == "alta"
    assert avaliar_sinais(120, 80, 100) == []


def test_bradicardia_abaixo_de_50():
    alertas = avaliar_sinais(120, 80, 45)
    assert tipos(alertas) == ["bradicardia"]
    assert "45 bpm" in alertas[0].descricao
    assert avaliar_sinais(120, 80, 50) == []


def test_eventos_diferentes_na_mesma_leitura_geram_um_alerta_cada():
    assert tipos(avaliar_sinais(190, 110, 130)) == ["crise_hipertensiva", "taquicardia"]


def test_adesao_abaixo_de_80_por_cento_gera_alerta_moderado():
    alerta = avaliar_adesao(doses_tomadas=8, doses_prescritas=14)
    assert alerta.tipo == "baixa_adesao"
    assert alerta.severidade == "moderada"
    assert "57%" in alerta.descricao
    assert "8 de 14" in alerta.descricao


def test_adesao_no_limiar_ou_acima_nao_gera_alerta():
    assert avaliar_adesao(doses_tomadas=12, doses_prescritas=14) is None
    assert avaliar_adesao(doses_tomadas=8, doses_prescritas=10) is None


def test_adesao_sem_doses_prescritas_nao_gera_alerta():
    assert avaliar_adesao(doses_tomadas=0, doses_prescritas=0) is None


def test_limiares_expostos_sao_os_usados_pelas_regras():
    assert LIMIARES["crise_sistolica"] == 180
    assert LIMIARES["elevada_sistolica"] == 140
    assert LIMIARES["adesao_minima"] == 0.8
