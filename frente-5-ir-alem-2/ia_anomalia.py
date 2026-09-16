"""Detecção de anomalias nos sinais vitais com Isolation Forest (Frente 5).

Segue o pipeline do Cap. 2 de AIRPA (seção 5): dados lidos do SQLite com
pandas, engenharia de atributos e ``IsolationForest`` do scikit-learn, sem
rótulos prévios. O modelo aprende o perfil típico das leituras e isola as que
fogem dele.

Atributos usados:
- pressão sistólica, diastólica e frequência cardíaca, como vieram do banco;
- pressão de pulso (sistólica - diastólica), razão clínica simples;
- adesão ao tratamento nos 7 dias até a leitura;
- desvio de cada sinal em relação à mediana do próprio paciente. É a
  normalização que o material recomenda: 138/88 pode ser normal para um
  paciente e atípico para outro.

Parâmetros: 200 árvores (faixa de 100 a 300 do material) e semente fixa. A
contaminação começou em 5%, como o material sugere, e foi ajustada para 2,5%
depois de inspecionar os alertas na base simulada: com 5% a IA sozinha apontava
quatro leituras sem nada clínico (score entre -0,05 e 0); com 3% ainda sobrava
uma (score -0,0035); com 2,5% ficam só as duas leituras atípicas planejadas, com
folga. O material recomenda esse ajuste quando há falso positivo demais.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import date, timedelta

import pandas as pd
import sklearn
from sklearn.ensemble import IsolationForest

FEATURES = [
    "pressao_sistolica",
    "pressao_diastolica",
    "frequencia_cardiaca",
    "pressao_pulso",
    "adesao_7d",
    "desvio_sistolica",
    "desvio_diastolica",
    "desvio_fc",
]

CONTAMINACAO = 0.025
N_ESTIMADORES = 200
SEMENTE = 42
MINIMO_AMOSTRAS = 50


@dataclass(frozen=True)
class Pontuacao:
    """Score do Isolation Forest (negativo = atípico) e o rótulo derivado."""

    score: float
    anomalia: bool


@dataclass
class ResultadoDeteccao:
    treinado: bool
    pontuacoes: dict[int, Pontuacao] = field(default_factory=dict)
    metadados: dict = field(default_factory=dict)


def _indice_doses(adesao: pd.DataFrame) -> dict[tuple[int, str], tuple[int, int]]:
    return {
        (int(r.paciente_id), str(r.data)): (int(r.doses_tomadas), int(r.doses_prescritas))
        for r in adesao.itertuples(index=False)
    }


def _doses_na_janela(indice: dict, paciente_id: int, dia: date) -> tuple[int, int]:
    tomadas = prescritas = 0
    for k in range(7):
        t, p = indice.get((paciente_id, (dia - timedelta(days=k)).isoformat()), (0, 0))
        tomadas += t
        prescritas += p
    return tomadas, prescritas


def doses_na_janela_7d(adesao: pd.DataFrame, paciente_id: int, dia: date) -> tuple[int, int]:
    """Doses tomadas e prescritas do paciente no dia informado e nos 6 anteriores."""
    return _doses_na_janela(_indice_doses(adesao), paciente_id, dia)


def preparar_features(leituras: pd.DataFrame, adesao: pd.DataFrame) -> pd.DataFrame:
    """Monta os atributos do modelo a partir das tabelas de leituras e de adesão."""
    df = leituras.copy()
    df["pressao_pulso"] = df["pressao_sistolica"] - df["pressao_diastolica"]

    por_paciente = df.groupby("paciente_id")
    for coluna, sufixo in [("pressao_sistolica", "sistolica"), ("pressao_diastolica", "diastolica"),
                           ("frequencia_cardiaca", "fc")]:
        df[f"mediana_{sufixo}"] = por_paciente[coluna].transform("median")
        df[f"desvio_{sufixo}"] = df[coluna] - df[f"mediana_{sufixo}"]

    indice = _indice_doses(adesao)
    valores = []
    for paciente_id, medido_em in zip(df["paciente_id"], df["medido_em"]):
        tomadas, prescritas = _doses_na_janela(indice, int(paciente_id), date.fromisoformat(str(medido_em)[:10]))
        # Sem registro de dose na janela, não há evidência de baixa adesão.
        valores.append(tomadas / prescritas if prescritas else 1.0)
    df["adesao_7d"] = valores
    return df


class DetectorAnomalias:
    """Treina o Isolation Forest na janela de leituras e pontua as leituras novas."""

    def __init__(self, contaminacao: float = CONTAMINACAO, n_estimadores: int = N_ESTIMADORES,
                 semente: int = SEMENTE, minimo_amostras: int = MINIMO_AMOSTRAS):
        self.contaminacao = contaminacao
        self.n_estimadores = n_estimadores
        self.semente = semente
        self.minimo_amostras = minimo_amostras

    def parametros(self) -> dict:
        return {
            "algoritmo": "IsolationForest",
            "features": FEATURES,
            "contaminacao": self.contaminacao,
            "n_estimadores": self.n_estimadores,
            "semente": self.semente,
            "minimo_amostras": self.minimo_amostras,
        }

    def avaliar(self, features: pd.DataFrame, ids_para_pontuar) -> ResultadoDeteccao:
        metadados = {
            **self.parametros(),
            "n_amostras": len(features),
            "versao_scikit_learn": sklearn.__version__,
        }
        if len(features) < self.minimo_amostras:
            metadados["motivo"] = (
                f"histórico insuficiente: {len(features)} leituras (mínimo {self.minimo_amostras})"
            )
            return ResultadoDeteccao(treinado=False, metadados=metadados)

        matriz = features[FEATURES].astype(float)
        metadados["hash_dataset"] = hashlib.sha256(
            pd.util.hash_pandas_object(matriz, index=False).to_numpy().tobytes()
        ).hexdigest()

        modelo = IsolationForest(
            n_estimators=self.n_estimadores,
            contamination=self.contaminacao,
            random_state=self.semente,
        ).fit(matriz)

        alvo = features["id"].isin(list(ids_para_pontuar))
        scores = modelo.decision_function(matriz[alvo])
        rotulos = modelo.predict(matriz[alvo])
        pontuacoes = {
            int(leitura_id): Pontuacao(score=round(float(score), 4), anomalia=bool(rotulo == -1))
            for leitura_id, score, rotulo in zip(features.loc[alvo, "id"], scores, rotulos)
        }
        return ResultadoDeteccao(treinado=True, pontuacoes=pontuacoes, metadados=metadados)


def descrever_anomalia(linha: pd.Series, score: float) -> str:
    """Texto do alerta de padrão atípico, comparando a leitura com a mediana do paciente."""
    return (
        f"Padrão atípico para o paciente (Isolation Forest, score {score:.3f}): "
        f"PA {int(linha['pressao_sistolica'])}/{int(linha['pressao_diastolica'])} mmHg "
        f"(mediana do paciente {linha['mediana_sistolica']:.0f}/{linha['mediana_diastolica']:.0f}), "
        f"FC {int(linha['frequencia_cardiaca'])} bpm (mediana {linha['mediana_fc']:.0f}), "
        f"adesão em 7 dias {linha['adesao_7d']:.0%}."
    )
