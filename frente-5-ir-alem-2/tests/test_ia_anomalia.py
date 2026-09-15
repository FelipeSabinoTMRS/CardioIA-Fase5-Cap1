"""Testes da detecção de anomalias com Isolation Forest (Cap. 2 de AIRPA, seção 5)."""

from datetime import date, datetime, timedelta, timezone

import numpy as np
import pandas as pd
import pytest

from ia_anomalia import FEATURES, DetectorAnomalias, descrever_anomalia, doses_na_janela_7d, preparar_features

INICIO = datetime(2026, 9, 1, 8, 0, tzinfo=timezone.utc)


def montar_leituras(bases, n_por_paciente=60, semente=7):
    """Leituras a cada 12 h com ruído pequeno em torno da base de cada paciente."""
    rng = np.random.default_rng(semente)
    linhas = []
    proximo_id = 1
    for paciente_id, (sistolica, diastolica, fc) in bases.items():
        for i in range(n_por_paciente):
            linhas.append({
                "id": proximo_id,
                "paciente_id": paciente_id,
                "medido_em": (INICIO + timedelta(hours=12 * i)).isoformat(),
                "pressao_sistolica": int(round(sistolica + rng.normal(0, 4))),
                "pressao_diastolica": int(round(diastolica + rng.normal(0, 3))),
                "frequencia_cardiaca": int(round(fc + rng.normal(0, 3))),
            })
            proximo_id += 1
    return pd.DataFrame(linhas)


def acrescentar(leituras, id_, paciente_id, sistolica, diastolica, fc, medido_em=INICIO):
    nova = pd.DataFrame([{
        "id": id_, "paciente_id": paciente_id, "medido_em": medido_em.isoformat(),
        "pressao_sistolica": sistolica, "pressao_diastolica": diastolica, "frequencia_cardiaca": fc,
    }])
    return pd.concat([leituras, nova], ignore_index=True)


def adesao_vazia():
    return pd.DataFrame(columns=["paciente_id", "data", "doses_prescritas", "doses_tomadas"])


def test_pressao_de_pulso_e_desvio_em_relacao_a_mediana_do_paciente():
    leituras = montar_leituras({1: (120, 80, 70), 2: (140, 90, 80)})
    features = preparar_features(leituras, adesao_vazia())
    linha = features[features["id"] == 5].iloc[0]
    do_paciente = leituras[leituras["paciente_id"] == 1]

    assert linha["pressao_pulso"] == linha["pressao_sistolica"] - linha["pressao_diastolica"]
    assert linha["desvio_sistolica"] == linha["pressao_sistolica"] - do_paciente["pressao_sistolica"].median()
    assert linha["desvio_fc"] == linha["frequencia_cardiaca"] - do_paciente["frequencia_cardiaca"].median()


def test_adesao_7d_considera_a_propria_data_e_os_6_dias_anteriores():
    dia = date(2026, 9, 20)
    registros = [{"paciente_id": 1, "data": (dia - timedelta(days=7)).isoformat(),
                  "doses_prescritas": 2, "doses_tomadas": 0}]
    registros += [{"paciente_id": 1, "data": (dia - timedelta(days=k)).isoformat(),
                   "doses_prescritas": 2, "doses_tomadas": 1} for k in range(7)]
    leituras = acrescentar(montar_leituras({1: (120, 80, 70)}, n_por_paciente=5), 99, 1, 120, 80, 70,
                           medido_em=datetime(2026, 9, 20, 20, 0, tzinfo=timezone.utc))

    features = preparar_features(leituras, pd.DataFrame(registros))

    assert features.loc[features["id"] == 99, "adesao_7d"].iloc[0] == pytest.approx(0.5)


def test_doses_na_janela_de_7_dias_para_a_regra_de_adesao():
    registros = pd.DataFrame([
        {"paciente_id": 1, "data": "2026-09-13", "doses_prescritas": 2, "doses_tomadas": 0},  # fora da janela
        {"paciente_id": 1, "data": "2026-09-14", "doses_prescritas": 2, "doses_tomadas": 1},
        {"paciente_id": 1, "data": "2026-09-20", "doses_prescritas": 2, "doses_tomadas": 2},
        {"paciente_id": 2, "data": "2026-09-20", "doses_prescritas": 1, "doses_tomadas": 0},  # outro paciente
    ])
    assert doses_na_janela_7d(registros, paciente_id=1, dia=date(2026, 9, 20)) == (3, 4)
    assert doses_na_janela_7d(registros, paciente_id=3, dia=date(2026, 9, 20)) == (0, 0)


def test_parametros_do_detector_para_registro_da_execucao():
    parametros = DetectorAnomalias(contaminacao=0.07, minimo_amostras=30).parametros()
    assert parametros["algoritmo"] == "IsolationForest"
    assert parametros["contaminacao"] == 0.07
    assert parametros["minimo_amostras"] == 30
    assert parametros["features"] == FEATURES


def test_sem_registro_de_adesao_assume_adesao_completa():
    features = preparar_features(montar_leituras({1: (120, 80, 70)}, n_por_paciente=3), adesao_vazia())
    assert (features["adesao_7d"] == 1.0).all()


def test_detector_marca_outlier_evidente_e_mantem_leitura_tipica():
    leituras = montar_leituras({1: (120, 80, 70), 2: (130, 85, 75)})
    leituras = acrescentar(leituras, 900, 1, 120, 80, 70)
    leituras = acrescentar(leituras, 999, 1, 195, 125, 140)
    features = preparar_features(leituras, adesao_vazia())

    resultado = DetectorAnomalias().avaliar(features, ids_para_pontuar=[900, 999])

    assert resultado.treinado
    assert resultado.pontuacoes[999].anomalia
    assert resultado.pontuacoes[999].score < 0
    assert not resultado.pontuacoes[900].anomalia


def test_detector_percebe_desvio_do_padrao_do_paciente_sem_cruzar_limiar():
    # A leitura 138/88 com FC 96 é normal para o paciente 2, mas atípica para o paciente 1.
    leituras = montar_leituras({1: (110, 70, 60), 2: (138, 88, 95)})
    leituras = acrescentar(leituras, 777, 1, 138, 88, 96)
    features = preparar_features(leituras, adesao_vazia())

    resultado = DetectorAnomalias().avaliar(features, ids_para_pontuar=[777])

    assert resultado.pontuacoes[777].anomalia


def test_historico_insuficiente_nao_treina_o_modelo():
    features = preparar_features(montar_leituras({1: (120, 80, 70)}, n_por_paciente=10), adesao_vazia())

    resultado = DetectorAnomalias(minimo_amostras=50).avaliar(features, ids_para_pontuar=[1])

    assert not resultado.treinado
    assert resultado.pontuacoes == {}
    assert "insuficiente" in resultado.metadados["motivo"]


def test_metadados_permitem_reproduzir_o_modelo():
    features = preparar_features(montar_leituras({1: (120, 80, 70), 2: (130, 85, 75)}), adesao_vazia())
    ids = features["id"].tolist()

    primeiro = DetectorAnomalias().avaliar(features, ids_para_pontuar=ids)
    segundo = DetectorAnomalias().avaliar(features, ids_para_pontuar=ids)

    meta = primeiro.metadados
    assert meta["algoritmo"] == "IsolationForest"
    assert meta["features"] == FEATURES
    assert meta["n_amostras"] == len(features)
    assert {"contaminacao", "n_estimadores", "semente", "versao_scikit_learn"} <= meta.keys()
    assert len(meta["hash_dataset"]) == 64
    assert meta["hash_dataset"] == segundo.metadados["hash_dataset"]
    assert primeiro.pontuacoes == segundo.pontuacoes


def test_descricao_da_anomalia_compara_com_a_mediana_do_paciente():
    leituras = acrescentar(montar_leituras({1: (110, 70, 60)}), 777, 1, 138, 88, 96)
    linha = preparar_features(leituras, adesao_vazia()).set_index("id").loc[777]

    texto = descrever_anomalia(linha, score=-0.081)

    assert "138/88 mmHg" in texto
    assert "96 bpm" in texto
    assert "mediana do paciente" in texto
    assert "-0.081" in texto
