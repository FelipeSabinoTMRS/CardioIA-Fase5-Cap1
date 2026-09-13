"""Conversa real com o Watson pelo terminal, usando as credenciais do .env.

Uso (dentro de frente-2-backend/, com o venv ativo):

    python scripts/smoke_chat.py
    python scripts/smoke_chat.py "Olá" "Estou com dor no peito" "qual o placar do jogo"

Sem argumentos, entra em modo interativo (Ctrl+C para sair). Serve para validar
a integração ponta a ponta antes de ligar a interface da Frente 3.
"""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from watson_client import WatsonAssistantClient, WatsonSessionExpired  # noqa: E402


def main(messages: list[str]) -> int:
    client = WatsonAssistantClient.from_env()
    mode = "environment_id" if client.environment_id else "rota antiga (só assistant_id)"
    print(f"Modo: {mode}")
    session_id = client.create_session()
    print(f"Sessão criada: {session_id}\n")

    def ask(text: str) -> None:
        nonlocal session_id
        try:
            reply = client.send_message(session_id, text)
        except WatsonSessionExpired:
            session_id = client.create_session()
            reply = client.send_message(session_id, text)
        print(f"Você: {text}")
        print(f"CardioIA: {reply.reply or '(sem texto)'}")
        print(f"  intent={reply.intent} confidence={reply.confidence} entities={reply.entities}\n")

    try:
        if messages:
            for text in messages:
                ask(text)
        else:
            while True:
                ask(input("Você: ").strip() or "oi")
    except (KeyboardInterrupt, EOFError):
        print()
    finally:
        client.delete_session(session_id)
        print("Sessão encerrada.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
