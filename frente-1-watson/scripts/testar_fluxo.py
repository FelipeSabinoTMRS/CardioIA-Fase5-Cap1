"""Roda conversas-roteiro contra a skill publicada, usando o cliente da Frente 2.

Pré-requisitos: dependências de ``frente-2-backend/requirements.txt`` instaladas
e ``frente-2-backend/.env`` preenchido (WA_API_KEY, WA_URL, WA_ASSISTANT_ID).

Cada roteiro abre uma sessão nova e confere a intent reconhecida e um trecho
esperado da resposta em cada turno.

Uso (a partir de frente-1-watson/):
    python scripts/testar_fluxo.py
"""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2] / "frente-2-backend"
sys.path.insert(0, str(BACKEND))

from dotenv import load_dotenv  # noqa: E402

from watson_client import WatsonAssistantClient  # noqa: E402

# (mensagem, intent esperada ou None para não conferir, trecho esperado na resposta)
ROTEIROS: dict[str, list[tuple[str, str | None, str]]] = {
    "saudação e ajuda": [
        ("Olá", "saudacao", "CardioIA"),
        ("o que você faz?", "ajuda", "Posso ajudar"),
    ],
    "emergência": [
        ("Estou com dor forte no peito", "emergencia", "192"),
    ],
    "triagem de sintomas": [
        ("estou com tontura", "sintomas", "Desde quando"),
        ("desde ontem", None, "intensidade"),
        ("forte", None, "Resumo do que você relatou"),
    ],
    "sintoma sem nome, depois resposta inválida": [
        ("não estou me sentindo bem", "sintomas", "Qual sintoma"),
        ("sei lá", None, "Não reconheci"),
        ("cansaço", None, "Desde quando"),
        ("mais de um mês", None, "intensidade"),
        ("leve", None, "marcar uma consulta"),
    ],
    "urgência no meio da triagem": [
        ("tenho sentido palpitação", "sintomas", "Desde quando"),
        ("agora estou com aperto no peito", None, "192"),
    ],
    "sinais vitais": [
        ("minha pressão deu 15 por 9", "sinais_vitais", "acima da referência"),
        ("minha pressão deu 12 por 8", "sinais_vitais", "dentro da faixa"),
        ("pressão 19 por 12", None, "muito elevado"),
        ("meus batimentos estão em 120", "sinais_vitais", "fora da faixa"),
        ("qual a pressão ideal?", "sinais_vitais", "Referências gerais"),
    ],
    "medicamentos e exames": [
        ("esqueci de tomar a losartana", "medicamentos", "losartana"),
        ("o que é um ecocardiograma?", "exames", "ultrassom do coração"),
    ],
    "agendamento": [
        ("quero marcar consulta com cardiologista", "agendamento", "Para qual dia"),
        ("amanhã", None, "manhã, tarde ou noite"),
        ("à tarde", None, "simulação"),
    ],
    "cancelar agendamento": [
        ("preciso agendar uma consulta", "agendamento", "especialidade"),
        ("deixa pra lá", None, "cancelei"),
    ],
    "exceções": [
        ("qual o placar do jogo?", "fora_de_escopo", "fora do que eu sei"),
        ("asdfgh qwerty", None, "não entendi"),
        ("obrigado, era só isso", "despedida", ""),
    ],
}


def main() -> int:
    load_dotenv(BACKEND / ".env")
    cliente = WatsonAssistantClient.from_env()
    falhas = 0
    for nome, turnos in ROTEIROS.items():
        print(f"\n== {nome}")
        sessao = cliente.create_session()
        try:
            for mensagem, intent_esperada, trecho in turnos:
                r = cliente.send_message(sessao, mensagem)
                ok_intent = intent_esperada is None or r.intent == intent_esperada
                ok_texto = trecho.lower() in r.reply.lower()
                status = "ok " if ok_intent and ok_texto else "FALHOU"
                falhas += 0 if ok_intent and ok_texto else 1
                print(f"[{status}] > {mensagem}")
                print(f"         #{r.intent} ({r.confidence}) {[e['entity'] + ':' + str(e['value']) for e in r.entities]}")
                print(f"         < {r.reply}")
        finally:
            cliente.delete_session(sessao)
    print(f"\n{falhas} turno(s) com falha")
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
