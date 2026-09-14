"""Cliente do IBM watsonx Assistant (API v2) para o CardioIA.

Segue o padrão do material da disciplina PCV (Cap. 10, Código-fonte 10):
``IAMAuthenticator`` + ``AssistantV2`` + ``set_service_url``, com uma sessão
criada via ``create_session`` e mensagens enviadas via ``message``.

O SDK ``ibm-watson`` 11.x passou a exigir ``environment_id`` nas rotas de
sessão. Quando a variável ``WA_ENVIRONMENT_ID`` não está definida, o cliente
usa a rota antiga ``/v2/assistants/{assistant_id}/sessions``, que é a mesma
usada pelo código do material (só ``assistant_id``).
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
from ibm_watson import ApiException, AssistantV2

DEFAULT_VERSION = "2021-06-14"


class WatsonConfigError(RuntimeError):
    """Credenciais do Watson ausentes ou incompletas."""


class WatsonSessionExpired(RuntimeError):
    """A sessão informada não existe mais no Watson (timeout por inatividade)."""


@dataclass
class WatsonReply:
    """Resposta já interpretada do Watson, no formato usado pelas rotas Flask."""

    reply: str
    intent: str | None = None
    confidence: float | None = None
    entities: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "reply": self.reply,
            "intent": self.intent,
            "confidence": self.confidence,
            "entities": self.entities,
        }


def parse_response(wa_response: dict) -> WatsonReply:
    """Extrai texto, intenção principal e entidades de ``output`` (como no Cap. 10)."""
    output = wa_response.get("output", {}) or {}
    intents = output.get("intents", []) or []
    entities = output.get("entities", []) or []
    generic = output.get("generic", []) or []

    texts = [item.get("text", "") for item in generic if item.get("response_type", "text") == "text"]
    reply = " ".join(t for t in texts if t).strip()

    top_intent = None
    confidence = None
    if intents:
        top_intent = intents[0].get("intent")
        confidence = intents[0].get("confidence")

    parsed_entities = [
        {"entity": e.get("entity"), "value": e.get("value"), "confidence": e.get("confidence")}
        for e in entities
    ]
    return WatsonReply(reply=reply, intent=top_intent, confidence=confidence, entities=parsed_entities)


class WatsonAssistantClient:
    """Encapsula sessão e envio de mensagens ao watsonx Assistant."""

    def __init__(
        self,
        api_key: str,
        url: str,
        assistant_id: str,
        environment_id: str | None = None,
        version: str = DEFAULT_VERSION,
    ) -> None:
        if not api_key or not url or not assistant_id:
            raise WatsonConfigError(
                "Defina WA_API_KEY, WA_URL e WA_ASSISTANT_ID no arquivo .env."
            )
        self.assistant_id = assistant_id
        self.environment_id = environment_id or None
        authenticator = IAMAuthenticator(api_key)
        self.assistant = AssistantV2(version=version, authenticator=authenticator)
        self.assistant.set_service_url(url)

    @classmethod
    def from_env(cls) -> "WatsonAssistantClient":
        """Cria o cliente a partir das variáveis de ambiente do material (WA_*)."""
        return cls(
            api_key=os.getenv("WA_API_KEY", ""),
            url=os.getenv("WA_URL", ""),
            assistant_id=os.getenv("WA_ASSISTANT_ID", ""),
            environment_id=os.getenv("WA_ENVIRONMENT_ID") or None,
            version=os.getenv("WA_VERSION") or DEFAULT_VERSION,
        )

    @staticmethod
    def is_configured() -> bool:
        return all(os.getenv(name) for name in ("WA_API_KEY", "WA_URL", "WA_ASSISTANT_ID"))

    # ----- sessão ---------------------------------------------------------

    def create_session(self) -> str:
        if self.environment_id:
            result = self.assistant.create_session(
                assistant_id=self.assistant_id, environment_id=self.environment_id
            ).get_result()
        else:
            result = self._legacy_request("POST", f"/v2/assistants/{self.assistant_id}/sessions")
        return result["session_id"]

    def delete_session(self, session_id: str) -> None:
        try:
            if self.environment_id:
                self.assistant.delete_session(
                    assistant_id=self.assistant_id,
                    environment_id=self.environment_id,
                    session_id=session_id,
                )
            else:
                self._legacy_request(
                    "DELETE", f"/v2/assistants/{self.assistant_id}/sessions/{session_id}"
                )
        except ApiException as exc:
            if exc.status_code != 404:
                raise

    # ----- mensagem -------------------------------------------------------

    def send_message(self, session_id: str, text: str) -> WatsonReply:
        """Envia ``text`` na sessão e devolve a resposta interpretada.

        Levanta ``WatsonSessionExpired`` quando o Watson responde 404 para a
        sessão, para que o chamador crie outra e reenvie.
        """
        message_input = {"message_type": "text", "text": text}
        try:
            if self.environment_id:
                raw = self.assistant.message(
                    assistant_id=self.assistant_id,
                    environment_id=self.environment_id,
                    session_id=session_id,
                    input=message_input,
                ).get_result()
            else:
                raw = self._legacy_request(
                    "POST",
                    f"/v2/assistants/{self.assistant_id}/sessions/{session_id}/message",
                    data={"input": message_input},
                )
        except ApiException as exc:
            if exc.status_code == 404:
                raise WatsonSessionExpired(str(exc.message)) from exc
            raise
        return parse_response(raw)

    # ----- rota antiga (só assistant_id) ----------------------------------

    def _legacy_request(self, method: str, url: str, data: dict | None = None) -> dict:
        headers = {"content-type": "application/json"}
        request = self.assistant.prepare_request(
            method=method,
            url=url,
            headers=headers,
            params={"version": self.assistant.version},
            data=json.dumps(data) if data is not None else None,
        )
        response = self.assistant.send(request)
        return response.get_result() or {}
