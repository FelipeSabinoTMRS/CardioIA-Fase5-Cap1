"""Gráficos Seaborn das análises do robô (Cap. 2 de AIRPA, seção 5; Cap. 7, visualização governada).

Os gráficos repetem a ideia do pipeline do material: dispersão com as leituras
típicas e atípicas e barras com a contagem de alertas. As linhas tracejadas
mostram os limiares das regras, para separar o que a regra pega do que só a IA pega.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.ticker import MaxNLocator  # noqa: E402
import pandas as pd  # noqa: E402
import seaborn as sns  # noqa: E402

import banco_relacional as br  # noqa: E402

CORES = {"Típica": "royalblue", "Atípica (IA)": "red", "Sem pontuação": "gray"}
MARCADORES = {"Típica": "o", "Atípica (IA)": "X", "Sem pontuação": "s"}
CORES_ORIGEM = {"regra": "#4C72B0", "regra+ia": "#8172B3", "ia": "#C44E52", "texto": "#55A868"}


def gerar(con, pasta: Path) -> list[Path]:
    pasta.mkdir(parents=True, exist_ok=True)
    return [
        dispersao_anomalias(br.leituras_analisadas(con), pasta / "dispersao_anomalias.png"),
        alertas_por_tipo(br.contagem_alertas(con), pasta / "alertas_por_tipo.png"),
    ]


def dispersao_anomalias(leituras: pd.DataFrame, destino: Path) -> Path:
    sns.set_theme(style="whitegrid")
    classificacao = np.select(
        [leituras["anomalia_ia"] == 1, leituras["anomalia_ia"] == 0],
        ["Atípica (IA)", "Típica"],
        default="Sem pontuação",
    )
    dados = leituras.assign(classificacao=classificacao)
    presentes = [c for c in CORES if c in set(classificacao)]

    fig, ax = plt.subplots(figsize=(10, 6))
    sns.scatterplot(
        data=dados, x="pressao_sistolica", y="frequencia_cardiaca",
        hue="classificacao", style="classificacao", hue_order=presentes, style_order=presentes,
        palette={c: CORES[c] for c in presentes}, markers={c: MARCADORES[c] for c in presentes},
        s=70, alpha=0.8, ax=ax,
    )
    for x, rotulo in ((140, "140 mmHg"), (180, "180 mmHg")):
        ax.axvline(x, color="gray", linestyle="--", linewidth=1)
        ax.text(x + 1, ax.get_ylim()[1] * 0.98, rotulo, color="gray", va="top", fontsize=9)
    for y in (50, 100):
        ax.axhline(y, color="gray", linestyle=":", linewidth=1)
    ax.set_title("Leituras analisadas pelo robô: Isolation Forest", fontsize=14, weight="bold")
    ax.set_xlabel("Pressão sistólica (mmHg)")
    ax.set_ylabel("Frequência cardíaca (bpm)")
    ax.legend(title="Classificação")
    fig.tight_layout()
    fig.savefig(destino, dpi=120)
    plt.close(fig)
    return destino


def alertas_por_tipo(contagem: pd.DataFrame, destino: Path) -> Path:
    sns.set_theme(style="whitegrid")
    fig, ax = plt.subplots(figsize=(10, 6))
    if contagem.empty:
        ax.text(0.5, 0.5, "Nenhum alerta gerado", ha="center", va="center", fontsize=14)
        ax.set_axis_off()
    else:
        tabela = contagem.pivot_table(index="tipo", columns="origem_deteccao", values="total",
                                      aggfunc="sum", fill_value=0)
        tabela = tabela[[origem for origem in CORES_ORIGEM if origem in tabela.columns]]
        tabela = tabela.loc[tabela.sum(axis=1).sort_values().index]
        tabela.plot(kind="barh", stacked=True, ax=ax, width=0.7,
                    color=[CORES_ORIGEM[origem] for origem in tabela.columns])
        ax.xaxis.set_major_locator(MaxNLocator(integer=True))
        ax.set_xlabel("Quantidade de alertas")
        ax.set_ylabel("Tipo de alerta")
        ax.legend(title="Origem da detecção")
    ax.set_title("Alertas gerados por tipo e origem", fontsize=14, weight="bold")
    fig.tight_layout()
    fig.savefig(destino, dpi=120)
    plt.close(fig)
    return destino
