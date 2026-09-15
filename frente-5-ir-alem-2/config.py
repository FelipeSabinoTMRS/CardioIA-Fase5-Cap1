"""Configuração da Frente 5 lida do ``.env`` (credenciais nunca vão para o código)."""

from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PASTA = Path(__file__).resolve().parent

PADRAO_SQLITE = "dados/cardioia_rpa.db"
PADRAO_MONGO_URI = "mongodb://admin:admin@localhost:27017/?authSource=admin"
PADRAO_MONGO_DB = "cardioia_rpa"
PADRAO_SKILL = "../frente-1-watson/cardioia-skill.json"


def _caminho(valor: str) -> Path:
    caminho = Path(valor)
    return caminho if caminho.is_absolute() else (PASTA / caminho).resolve()


def configurar_saida_utf8() -> None:
    """Acentos legíveis no terminal do Windows (PowerShell e Git Bash)."""
    for fluxo in (sys.stdout, sys.stderr):
        if hasattr(fluxo, "reconfigure"):
            fluxo.reconfigure(encoding="utf-8")


def ocultar_senha(uri: str) -> str:
    """Mostra a URI no terminal sem expor a senha."""
    return re.sub(r"(mongodb(?:\+srv)?://[^:/@]+:)[^@]+@", r"\1***@", uri)


@dataclass(frozen=True)
class Config:
    sqlite_path: Path
    mongo_uri: str
    mongo_db: str
    skill_watson: Path

    @classmethod
    def carregar(cls, arquivo_env: Path | None = PASTA / ".env") -> Config:
        if arquivo_env is not None:
            load_dotenv(arquivo_env)
        return cls(
            sqlite_path=_caminho(os.getenv("SQLITE_PATH", PADRAO_SQLITE)),
            mongo_uri=os.getenv("MONGO_URI", PADRAO_MONGO_URI),
            mongo_db=os.getenv("MONGO_DB", PADRAO_MONGO_DB),
            skill_watson=_caminho(os.getenv("SKILL_WATSON_PATH", PADRAO_SKILL)),
        )
