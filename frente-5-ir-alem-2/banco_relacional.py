"""Camada relacional do robô (SQLite via ``sqlite3``), no padrão do Cap. 2 de AIRPA.

- Conexão com ``PRAGMA journal_mode=WAL`` e ``synchronous=NORMAL`` (seção 6.2 do
  material): o robô escreve enquanto consultas analíticas leem.
- DDL em ``schema_relacional.sql`` e DML com parâmetros ``?``/``:nome``, nunca
  com f-string, para evitar injeção de SQL.
- ``registrar_resultados`` grava análises e alertas de um ciclo em uma única
  transação: ou entra tudo, ou nada.
"""

from __future__ import annotations

import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

SCHEMA = Path(__file__).resolve().parent / "schema_relacional.sql"


def iso_utc(momento: datetime) -> str:
    """Formato único de data do banco: ISO 8601 em UTC, com segundos (compara como texto)."""
    return momento.astimezone(timezone.utc).isoformat(timespec="seconds")


@dataclass(frozen=True)
class AnaliseLeitura:
    leitura_id: int
    execucao_id: str
    analisado_em: str
    adesao_7d: float | None
    score_anomalia: float | None
    anomalia_ia: bool | None


@dataclass(frozen=True)
class NovoAlerta:
    paciente_id: int
    execucao_id: str
    tipo: str
    severidade: str
    origem_deteccao: str
    descricao: str
    criado_em: str
    leitura_id: int | None = None
    mensagem_id: str | None = None
    score_anomalia: float | None = None


def conectar(caminho: str | Path) -> sqlite3.Connection:
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(caminho)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.execute("PRAGMA journal_mode = WAL")
    con.execute("PRAGMA synchronous = NORMAL")
    return con


def criar_schema(con: sqlite3.Connection) -> None:
    con.executescript(SCHEMA.read_text(encoding="utf-8"))


def inserir_pacientes(con: sqlite3.Connection, pacientes: list[dict]) -> dict[str, int]:
    with con:
        con.executemany(
            """INSERT INTO pacientes (codigo, nome_ficticio, idade, condicao_base, medicamento_continuo, criado_em)
               VALUES (:codigo, :nome_ficticio, :idade, :condicao_base, :medicamento_continuo, :criado_em)""",
            pacientes,
        )
    return ids_por_codigo(con)


def inserir_leituras(con: sqlite3.Connection, leituras: list[dict]) -> int:
    with con:
        cursor = con.executemany(
            """INSERT INTO leituras_sinais
                   (paciente_id, medido_em, pressao_sistolica, pressao_diastolica, frequencia_cardiaca, origem)
               VALUES (:paciente_id, :medido_em, :pressao_sistolica, :pressao_diastolica,
                       :frequencia_cardiaca, :origem)""",
            leituras,
        )
    return cursor.rowcount


def inserir_adesao(con: sqlite3.Connection, registros: list[dict]) -> int:
    with con:
        cursor = con.executemany(
            """INSERT INTO adesao_tratamento (paciente_id, data, doses_prescritas, doses_tomadas)
               VALUES (:paciente_id, :data, :doses_prescritas, :doses_tomadas)""",
            registros,
        )
    return cursor.rowcount


def ids_por_codigo(con: sqlite3.Connection) -> dict[str, int]:
    return {r["codigo"]: r["id"] for r in con.execute("SELECT id, codigo FROM pacientes")}


def buscar_leituras_pendentes(con: sqlite3.Connection, limite: int) -> pd.DataFrame:
    """Leituras que ainda não têm linha em ``analises_leitura``, da mais antiga para a mais nova."""
    return pd.read_sql_query(
        """SELECT l.id, l.paciente_id, p.codigo AS paciente_codigo, l.medido_em,
                  l.pressao_sistolica, l.pressao_diastolica, l.frequencia_cardiaca
           FROM leituras_sinais l
           JOIN pacientes p ON p.id = l.paciente_id
           LEFT JOIN analises_leitura a ON a.leitura_id = l.id
           WHERE a.leitura_id IS NULL
           ORDER BY l.medido_em, l.id
           LIMIT ?""",
        con,
        params=(limite,),
    )


def buscar_leituras_modelo(con: sqlite3.Connection, desde: str) -> pd.DataFrame:
    """Base de treino: leituras da janela e as pendentes, mesmo que antigas."""
    return pd.read_sql_query(
        """SELECT l.id, l.paciente_id, l.medido_em,
                  l.pressao_sistolica, l.pressao_diastolica, l.frequencia_cardiaca
           FROM leituras_sinais l
           LEFT JOIN analises_leitura a ON a.leitura_id = l.id
           WHERE l.medido_em >= ? OR a.leitura_id IS NULL
           ORDER BY l.medido_em, l.id""",
        con,
        params=(desde,),
    )


def buscar_adesao(con: sqlite3.Connection, desde: str) -> pd.DataFrame:
    return pd.read_sql_query(
        """SELECT paciente_id, data, doses_prescritas, doses_tomadas
           FROM adesao_tratamento WHERE data >= ? ORDER BY paciente_id, data""",
        con,
        params=(desde,),
    )


def existe_alerta_recente(con: sqlite3.Connection, paciente_id: int, tipo: str, desde: str) -> bool:
    linha = con.execute(
        "SELECT 1 FROM alertas WHERE paciente_id = ? AND tipo = ? AND criado_em >= ? LIMIT 1",
        (paciente_id, tipo, desde),
    ).fetchone()
    return linha is not None


def registrar_resultados(con: sqlite3.Connection, analises: list[AnaliseLeitura],
                         alertas: list[NovoAlerta]) -> list[int | None]:
    """Grava o ciclo em uma transação. Devolve o id de cada alerta (``None`` se já existia).

    ``ON CONFLICT DO NOTHING`` só trata duplicidade (reprocessamento). Violação de
    CHECK ou de chave estrangeira continua gerando erro e desfaz o ciclo inteiro.
    """
    ids: list[int | None] = []
    with con:
        con.executemany(
            """INSERT INTO analises_leitura
                   (leitura_id, execucao_id, analisado_em, adesao_7d, score_anomalia, anomalia_ia)
               VALUES (:leitura_id, :execucao_id, :analisado_em, :adesao_7d, :score_anomalia, :anomalia_ia)
               ON CONFLICT DO NOTHING""",
            [asdict(a) for a in analises],
        )
        for alerta in alertas:
            cursor = con.execute(
                """INSERT INTO alertas
                       (paciente_id, leitura_id, mensagem_id, execucao_id, tipo, severidade,
                        origem_deteccao, descricao, score_anomalia, criado_em)
                   VALUES (:paciente_id, :leitura_id, :mensagem_id, :execucao_id, :tipo, :severidade,
                           :origem_deteccao, :descricao, :score_anomalia, :criado_em)
                   ON CONFLICT DO NOTHING""",
                asdict(alerta),
            )
            ids.append(cursor.lastrowid if cursor.rowcount == 1 else None)
    return ids


def alertas_da_execucao(con: sqlite3.Connection, execucao_id: str) -> list[dict]:
    linhas = con.execute(
        """SELECT a.id, p.codigo AS paciente_codigo, a.tipo, a.severidade, a.origem_deteccao, a.descricao
           FROM alertas a JOIN pacientes p ON p.id = a.paciente_id
           WHERE a.execucao_id = ?
           ORDER BY CASE a.severidade WHEN 'critica' THEN 0 WHEN 'alta' THEN 1 ELSE 2 END, a.id""",
        (execucao_id,),
    )
    return [dict(linha) for linha in linhas]


def resumo_alertas_abertos(con: sqlite3.Connection) -> pd.DataFrame:
    return pd.read_sql_query(
        """SELECT p.codigo AS paciente_codigo,
                  SUM(a.severidade = 'critica') AS critica,
                  SUM(a.severidade = 'alta') AS alta,
                  SUM(a.severidade = 'moderada') AS moderada,
                  COUNT(*) AS total
           FROM alertas a JOIN pacientes p ON p.id = a.paciente_id
           WHERE a.status = 'aberto'
           GROUP BY p.codigo
           ORDER BY critica DESC, alta DESC, total DESC, p.codigo""",
        con,
    )


def leituras_analisadas(con: sqlite3.Connection) -> pd.DataFrame:
    return pd.read_sql_query(
        """SELECT l.id, p.codigo AS paciente_codigo, l.medido_em, l.pressao_sistolica, l.pressao_diastolica,
                  l.frequencia_cardiaca, an.adesao_7d, an.score_anomalia, an.anomalia_ia
           FROM analises_leitura an
           JOIN leituras_sinais l ON l.id = an.leitura_id
           JOIN pacientes p ON p.id = l.paciente_id
           ORDER BY l.medido_em""",
        con,
    )


def contagem_alertas(con: sqlite3.Connection) -> pd.DataFrame:
    return pd.read_sql_query(
        """SELECT tipo, origem_deteccao, COUNT(*) AS total
           FROM alertas GROUP BY tipo, origem_deteccao ORDER BY total DESC, tipo""",
        con,
    )


def rastrear_alerta(con: sqlite3.Connection, alerta_id: int) -> dict | None:
    """Monta o rastro relacional de um alerta: alerta, paciente, leitura de origem e análise."""
    alerta = con.execute("SELECT * FROM alertas WHERE id = ?", (alerta_id,)).fetchone()
    if alerta is None:
        return None

    def uma(sql: str, parametro) -> dict | None:
        if parametro is None:
            return None
        linha = con.execute(sql, (parametro,)).fetchone()
        return dict(linha) if linha else None

    return {
        "alerta": dict(alerta),
        "paciente": uma("SELECT codigo, nome_ficticio, idade, condicao_base, medicamento_continuo "
                        "FROM pacientes WHERE id = ?", alerta["paciente_id"]),
        "leitura": uma("SELECT * FROM leituras_sinais WHERE id = ?", alerta["leitura_id"]),
        "analise": uma("SELECT * FROM analises_leitura WHERE leitura_id = ?", alerta["leitura_id"]),
    }
