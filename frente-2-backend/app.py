"""Backend Flask do Assistente Cardiológico CardioIA (Frente 2).

Recebe a mensagem do usuário, envia ao IBM watsonx Assistant e devolve a
resposta para a interface (Frente 3). Estrutura baseada no exemplo Flask do
material da disciplina PCV (Cap. 10): rota ``/`` com ``index.html`` e rota
``POST /api/chat`` que recebe ``{"message": ...}`` e responde ``{"response": ...}``.

Diferenças em relação ao material, pedidas no README da frente:
- ``session_id`` é devolvido e pode ser reenviado para manter o contexto;
- a resposta traz também ``intent``, ``confidence`` e ``entities``;
- ``GET /api/health`` informa se o backend está no ar e configurado.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from ibm_watson import ApiException

from watson_client import (
    WatsonAssistantClient,
    WatsonConfigError,
    WatsonSessionExpired,
)

load_dotenv()

DISCLAIMER = (
    "Simulação acadêmica (FIAP, CardioIA Fase 5). Não substitui avaliação médica. "
    "Em caso de dor no peito, falta de ar intensa ou desmaio, procure emergência."
)


def create_app(client: WatsonAssistantClient | None = None) -> Flask:
    """Cria a aplicação. ``client`` pode ser injetado nos testes."""
    app = Flask(__name__)
    app.config["WATSON_CLIENT"] = client

    def get_client() -> WatsonAssistantClient:
        if app.config["WATSON_CLIENT"] is None:
            app.config["WATSON_CLIENT"] = WatsonAssistantClient.from_env()
        return app.config["WATSON_CLIENT"]

    @app.route("/")
    def index():
        return render_template("index.html", disclaimer=DISCLAIMER)

    @app.route("/api/health", methods=["GET"])
    def health():
        configured = app.config["WATSON_CLIENT"] is not None or WatsonAssistantClient.is_configured()
        return jsonify({"status": "ok", "service": "cardioia-backend", "watson_configured": configured})

    @app.route("/api/chat", methods=["POST"])
    def chat():
        payload = request.get_json(silent=True) or {}
        user_msg = (payload.get("message") or "").strip()
        session_id = payload.get("session_id") or None

        if not user_msg:
            return jsonify({"error": "Envie um texto no campo 'message'."}), 400

        try:
            client = get_client()
        except WatsonConfigError as exc:
            return jsonify({"error": str(exc)}), 503

        try:
            if session_id is None:
                session_id = client.create_session()
            try:
                reply = client.send_message(session_id, user_msg)
            except WatsonSessionExpired:
                # Sessão expirou por inatividade: cria outra e reenvia uma vez.
                session_id = client.create_session()
                reply = client.send_message(session_id, user_msg)
        except ApiException as exc:
            app.logger.error("Erro na API do Watson: status=%s", exc.status_code)
            return (
                jsonify({"error": "Falha ao falar com o Watson Assistant.", "detail": exc.message}),
                502,
            )

        body = {"response": reply.reply, "session_id": session_id, **reply.to_dict()}
        return jsonify(body)

    return app


app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("FLASK_PORT", "5050"))
    app.run(host="127.0.0.1", port=port, debug=True)
