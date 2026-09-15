"""Prepara os bancos da Frente 5 com dados simulados.

Cria o schema do SQLite, grava pacientes fictícios, 30 dias de leituras e de
adesão e coloca no MongoDB as mensagens que os pacientes enviaram pelo app.

Uso:
    python preparar_ambiente.py            # primeira vez
    python preparar_ambiente.py --reset    # apaga os dados do robô e recria
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

import banco_relacional as br
import simulador
from banco_nosql import MongoIndisponivel, RegistroNoSQL
from config import Config, configurar_saida_utf8, ocultar_senha


def main(argv: list[str] | None = None) -> int:
    configurar_saida_utf8()
    parser = argparse.ArgumentParser(description="Cria o SQLite e o MongoDB da Frente 5 com dados simulados.")
    parser.add_argument("--reset", action="store_true", help="apaga os dados atuais do robô antes de recriar")
    parser.add_argument("--dias", type=int, default=30, help="dias de histórico simulado (padrão: 30)")
    parser.add_argument("--semente", type=int, default=42, help="semente do gerador de dados (padrão: 42)")
    args = parser.parse_args(argv)
    cfg = Config.carregar()

    if cfg.sqlite_path.exists() and not args.reset:
        print(f"O banco {cfg.sqlite_path} já existe. Use --reset para apagar e recriar os dados simulados.")
        return 1

    try:
        registro = RegistroNoSQL.conectar(cfg.mongo_uri, cfg.mongo_db)
    except MongoIndisponivel as exc:
        print(exc)
        return 2

    if args.reset:
        try:
            _apagar_sqlite(cfg.sqlite_path)
        except OSError:
            print(f"O arquivo {cfg.sqlite_path} está em uso por outro processo. "
                  "Pare o robô (Ctrl+C) e rode de novo. Nada foi apagado.")
            return 3
        registro.apagar_tudo()
        registro.criar_indices()

    agora = datetime.now(timezone.utc).replace(microsecond=0)
    dados = simulador.gerar_historico(agora, dias=args.dias, semente=args.semente)
    con = br.conectar(cfg.sqlite_path)
    try:
        br.criar_schema(con)
        ids = br.inserir_pacientes(con, dados.pacientes)
        leituras = br.inserir_leituras(con, simulador.com_ids(dados.leituras, ids))
        adesao = br.inserir_adesao(con, simulador.com_ids(dados.adesao, ids))
    finally:
        con.close()
    mensagens = registro.inserir_mensagens(simulador.mensagens_iniciais(agora))

    print("Ambiente da Frente 5 pronto (dados 100% simulados).")
    print(f"  SQLite  {cfg.sqlite_path}")
    print(f"          {len(ids)} pacientes, {leituras} leituras, {adesao} registros de adesão")
    print(f"  MongoDB {ocultar_senha(cfg.mongo_uri)} (banco {cfg.mongo_db})")
    print(f"          {len(mensagens)} mensagens de pacientes pendentes")
    print("Próximo passo: python robot.py --ciclos 3 --intervalo 10 --simular-chegada 4")
    return 0


def _apagar_sqlite(caminho: Path) -> None:
    for sufixo in ("", "-wal", "-shm"):
        caminho.with_name(caminho.name + sufixo).unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
