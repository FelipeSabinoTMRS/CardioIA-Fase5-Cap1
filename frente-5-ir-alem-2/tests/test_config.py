"""Testes da leitura de configuração (.env / variáveis de ambiente)."""

from pathlib import Path

import config

VARIAVEIS = ("SQLITE_PATH", "MONGO_URI", "MONGO_DB", "SKILL_WATSON_PATH")


def test_valores_padrao_apontam_para_a_pasta_da_frente(monkeypatch):
    for nome in VARIAVEIS:
        monkeypatch.delenv(nome, raising=False)

    cfg = config.Config.carregar(arquivo_env=None)

    assert cfg.sqlite_path == config.PASTA / "dados" / "cardioia_rpa.db"
    assert cfg.mongo_uri.startswith("mongodb://")
    assert cfg.mongo_db == "cardioia_rpa"
    assert cfg.skill_watson == (config.PASTA.parent / "frente-1-watson" / "cardioia-skill.json").resolve()
    assert cfg.skill_watson.exists()


def test_variaveis_de_ambiente_sobrescrevem_o_padrao(monkeypatch, tmp_path):
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "outro.db"))
    monkeypatch.setenv("MONGO_URI", "mongodb://usuario:senha@servidor:27017/")
    monkeypatch.setenv("MONGO_DB", "cardioia_teste")

    cfg = config.Config.carregar(arquivo_env=None)

    assert cfg.sqlite_path == tmp_path / "outro.db"
    assert cfg.mongo_uri == "mongodb://usuario:senha@servidor:27017/"
    assert cfg.mongo_db == "cardioia_teste"


def test_caminho_relativo_e_resolvido_a_partir_da_pasta_da_frente(monkeypatch):
    monkeypatch.setenv("SQLITE_PATH", "saida/teste.db")
    cfg = config.Config.carregar(arquivo_env=None)
    assert cfg.sqlite_path == (config.PASTA / "saida" / "teste.db").resolve()


def test_uri_sem_senha_para_exibir_no_terminal():
    assert config.ocultar_senha("mongodb://admin:segredo@localhost:27017/?authSource=admin") == \
        "mongodb://admin:***@localhost:27017/?authSource=admin"
    assert config.ocultar_senha("mongodb://localhost:27017/") == "mongodb://localhost:27017/"


def test_env_example_lista_as_variaveis_usadas():
    exemplo = (Path(config.PASTA) / ".env.example").read_text(encoding="utf-8")
    for nome in VARIAVEIS:
        assert f"{nome}=" in exemplo
