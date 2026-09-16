"""Testes dos comandos de terminal com SQLite temporário e MongoDB em memória."""

import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from types import SimpleNamespace

import mongomock
import pytest

import preparar_ambiente
import resumo_execucoes
import robot
from banco_nosql import MongoIndisponivel, RegistroNoSQL


@pytest.fixture
def cli(tmp_path, monkeypatch):
    sqlite_path = tmp_path / "cli.db"
    monkeypatch.setenv("SQLITE_PATH", str(sqlite_path))
    registro = RegistroNoSQL(mongomock.MongoClient()["cardioia_rpa_cli"])
    monkeypatch.setattr(RegistroNoSQL, "conectar", classmethod(lambda cls, *args, **kwargs: registro))
    # mongomock não implementa mapReduce; o caminho com Map/Reduce é testado contra o MongoDB real.
    original = RegistroNoSQL.resumo_alertas_por_tipo
    monkeypatch.setattr(RegistroNoSQL, "resumo_alertas_por_tipo",
                        lambda self, usar_map_reduce=True: original(self, usar_map_reduce=False))
    return SimpleNamespace(sqlite=sqlite_path, registro=registro)


def contar(caminho, tabela):
    with closing(sqlite3.connect(caminho)) as con:
        return con.execute(f"SELECT COUNT(*) FROM {tabela}").fetchone()[0]


def test_preparar_ambiente_cria_os_dois_bancos_com_dados_simulados(cli, capsys):
    assert preparar_ambiente.main([]) == 0

    assert contar(cli.sqlite, "pacientes") == 8
    assert contar(cli.sqlite, "leituras_sinais") == 480
    assert len(cli.registro.buscar_mensagens_pendentes(limite=100)) == 7
    assert "480 leituras" in capsys.readouterr().out


def test_preparar_ambiente_so_recria_com_reset(cli, capsys):
    preparar_ambiente.main([])

    assert preparar_ambiente.main([]) == 1
    assert "--reset" in capsys.readouterr().out

    assert preparar_ambiente.main(["--reset"]) == 0
    assert contar(cli.sqlite, "leituras_sinais") == 480
    assert len(cli.registro.buscar_mensagens_pendentes(limite=100)) == 7


def test_preparar_ambiente_avisa_quando_o_banco_esta_aberto_em_outro_processo(cli, capsys):
    preparar_ambiente.main([])
    capsys.readouterr()
    aberto = sqlite3.connect(cli.sqlite)  # no Windows, arquivo aberto não pode ser apagado

    try:
        codigo = preparar_ambiente.main(["--reset"])
    finally:
        aberto.close()

    assert codigo == 3
    saida = capsys.readouterr().out
    assert "em uso" in saida
    assert contar(cli.sqlite, "leituras_sinais") == 480  # nada foi perdido


def test_robot_roda_os_ciclos_pedidos_e_simula_chegada_de_leituras(cli, capsys):
    preparar_ambiente.main([])

    assert robot.main(["--ciclos", "2", "--intervalo", "0", "--simular-chegada", "3"]) == 0

    assert [e["status"] for e in cli.registro.ultimas_execucoes(limite=10)] == ["concluida", "concluida"]
    assert contar(cli.sqlite, "analises_leitura") == 486
    saida = capsys.readouterr().out
    assert "Ciclo 1" in saida and "Ciclo 2" in saida
    assert "[CRITICA] PAC-004" in saida
    assert "6 interpretada(s), 1 rejeitada(s)" in saida


def test_robot_sem_leituras_novas_diz_que_nao_havia_o_que_analisar(cli, capsys):
    preparar_ambiente.main([])

    robot.main(["--ciclos", "2", "--intervalo", "0"])

    segundo_ciclo = capsys.readouterr().out.split("Ciclo 2")[1]
    assert "sem leituras novas" in segundo_ciclo
    assert "modelo treinado" not in segundo_ciclo


def test_robot_sem_banco_preparado_orienta_rodar_o_preparo(cli, capsys):
    assert robot.main(["--ciclos", "1"]) == 1
    assert "preparar_ambiente.py" in capsys.readouterr().out


def test_robot_sem_mongodb_orienta_subir_o_container(cli, monkeypatch, capsys):
    preparar_ambiente.main([])

    def indisponivel(cls, *args, **kwargs):
        raise MongoIndisponivel("MongoDB indisponível. Suba o banco com `docker compose up -d`.")

    monkeypatch.setattr(RegistroNoSQL, "conectar", classmethod(indisponivel))

    assert robot.main(["--ciclos", "1"]) == 2
    assert "docker compose up -d" in capsys.readouterr().out


def test_robot_fecha_execucao_abandonada_da_rodada_anterior(cli, capsys):
    preparar_ambiente.main([])
    cli.registro.iniciar_execucao("exec-abandonada", datetime.now(timezone.utc))

    robot.main(["--ciclos", "1", "--intervalo", "0"])

    assert cli.registro.buscar_execucao("exec-abandonada")["status"] == "interrompida"
    assert "interrompida" in capsys.readouterr().out


def test_robot_segue_para_o_proximo_ciclo_depois_de_um_erro(cli, monkeypatch, capsys):
    preparar_ambiente.main([])
    chamadas = []
    original = robot.executar_ciclo

    def instavel(*args, **kwargs):
        chamadas.append(1)
        if len(chamadas) == 1:
            raise RuntimeError("falha simulada")
        return original(*args, **kwargs)

    monkeypatch.setattr(robot, "executar_ciclo", instavel)

    assert robot.main(["--ciclos", "2", "--intervalo", "0"]) == 1
    assert len(chamadas) == 2
    assert "falha simulada" in capsys.readouterr().out


def test_resumo_mostra_execucoes_alertas_e_rastro_de_um_alerta(cli, capsys):
    preparar_ambiente.main([])
    robot.main(["--ciclos", "1", "--intervalo", "0"])
    with closing(sqlite3.connect(cli.sqlite)) as con:
        alerta_id, execucao_id = con.execute(
            "SELECT id, execucao_id FROM alertas WHERE tipo = 'crise_hipertensiva'"
        ).fetchone()
        (alerta_texto_id,) = con.execute("SELECT id FROM alertas WHERE tipo = 'sinal_alerta_relatado'").fetchone()
    capsys.readouterr()

    assert resumo_execucoes.main([]) == 0
    saida = capsys.readouterr().out
    assert "Execuções recentes" in saida
    assert "crise_hipertensiva" in saida
    assert "PAC-004" in saida

    assert resumo_execucoes.main(["--alerta", str(alerta_id)]) == 0
    rastro = capsys.readouterr().out
    assert execucao_id in rastro
    assert "alerta_gerado" in rastro
    assert "PAC-004" in rastro
    assert "mensagem_interpretada" not in rastro  # eventos de outras origens não poluem o rastro

    assert resumo_execucoes.main(["--alerta", str(alerta_texto_id)]) == 0
    rastro_texto = capsys.readouterr().out
    assert "aperto no peito" in rastro_texto
    assert rastro_texto.count("mensagem_interpretada") == 1
    assert "PAC-003" not in rastro_texto

    assert resumo_execucoes.main(["--alerta", "99999"]) == 1


def test_resumo_gera_os_graficos(cli, tmp_path):
    preparar_ambiente.main([])
    robot.main(["--ciclos", "1", "--intervalo", "0"])
    pasta = tmp_path / "graficos"

    assert resumo_execucoes.main(["--graficos", str(pasta)]) == 0

    assert (pasta / "dispersao_anomalias.png").stat().st_size > 0
    assert (pasta / "alertas_por_tipo.png").stat().st_size > 0
