"""Testes do cliente do Watson sem acesso à rede (SDK substituído por dublês)."""

import pytest
from ibm_watson import ApiException

import watson_client
from watson_client import (
    WatsonAssistantClient,
    WatsonConfigError,
    WatsonSessionExpired,
    parse_response,
)

SAMPLE_RESPONSE = {
    "output": {
        "intents": [{"intent": "sintomas", "confidence": 0.93}],
        "entities": [{"entity": "sintoma", "value": "falta de ar", "confidence": 1.0}],
        "generic": [
            {"response_type": "text", "text": "Entendi que você está com falta de ar."},
            {"response_type": "text", "text": "Há quanto tempo isso acontece?"},
        ],
    }
}


def test_parse_response_extracts_text_intent_and_entities():
    parsed = parse_response(SAMPLE_RESPONSE)
    assert parsed.reply == "Entendi que você está com falta de ar. Há quanto tempo isso acontece?"
    assert parsed.intent == "sintomas"
    assert parsed.confidence == 0.93
    assert parsed.entities == [{"entity": "sintoma", "value": "falta de ar", "confidence": 1.0}]


def test_parse_response_handles_empty_output():
    parsed = parse_response({"output": {}})
    assert parsed.reply == ""
    assert parsed.intent is None
    assert parsed.entities == []


def test_missing_credentials_raises_config_error():
    with pytest.raises(WatsonConfigError):
        WatsonAssistantClient(api_key="", url="", assistant_id="")


class FakeDetailedResponse:
    def __init__(self, result):
        self._result = result

    def get_result(self):
        return self._result


class FakeAssistantV2:
    """Imita AssistantV2 do SDK: guarda as chamadas e devolve respostas prontas."""

    def __init__(self, version, authenticator=None):
        self.version = version
        self.calls = []
        self.fail_message_with = None

    def set_service_url(self, url):
        self.url = url

    def create_session(self, assistant_id, environment_id):
        self.calls.append(("create_session", assistant_id, environment_id))
        return FakeDetailedResponse({"session_id": "sess-123"})

    def message(self, assistant_id, environment_id, session_id, input=None, user_id=None):
        self.calls.append(("message", assistant_id, environment_id, session_id, input, user_id))
        if self.fail_message_with:
            raise ApiException(self.fail_message_with, message="Invalid Session")
        return FakeDetailedResponse(SAMPLE_RESPONSE)

    def delete_session(self, assistant_id, environment_id, session_id):
        self.calls.append(("delete_session", assistant_id, environment_id, session_id))
        return FakeDetailedResponse({})

    # rota antiga
    def prepare_request(self, method, url, headers=None, params=None, data=None):
        self.calls.append(("prepare_request", method, url, params, data))
        return {"method": method, "url": url}

    def send(self, request):
        if request["method"] == "POST" and request["url"].endswith("/sessions"):
            return FakeDetailedResponse({"session_id": "legacy-1"})
        if request["url"].endswith("/message"):
            return FakeDetailedResponse(SAMPLE_RESPONSE)
        return FakeDetailedResponse({})


@pytest.fixture
def fake_sdk(monkeypatch):
    monkeypatch.setattr(watson_client, "AssistantV2", FakeAssistantV2)
    monkeypatch.setattr(watson_client, "IAMAuthenticator", lambda key: object())


def test_client_with_environment_id_uses_sdk_methods(fake_sdk):
    client = WatsonAssistantClient("key", "https://wa.example", "asst-1", environment_id="env-1")
    session_id = client.create_session()
    reply = client.send_message(session_id, "Estou com falta de ar")

    assert session_id == "sess-123"
    assert reply.intent == "sintomas"
    sdk = client.assistant
    assert sdk.calls[0] == ("create_session", "asst-1", "env-1")
    assert sdk.calls[1][:4] == ("message", "asst-1", "env-1", "sess-123")
    assert sdk.calls[1][4] == {"message_type": "text", "text": "Estou com falta de ar"}
    assert sdk.calls[1][5] == "session:sess-123"


def test_client_without_environment_id_uses_legacy_route(fake_sdk):
    client = WatsonAssistantClient("key", "https://wa.example", "asst-1")
    session_id = client.create_session()
    reply = client.send_message(session_id, "Oi")

    assert session_id == "legacy-1"
    assert reply.reply.startswith("Entendi")
    urls = [c[2] for c in client.assistant.calls if c[0] == "prepare_request"]
    assert urls == [
        "/v2/assistants/asst-1/sessions",
        "/v2/assistants/asst-1/sessions/legacy-1/message",
    ]


def test_404_on_message_becomes_session_expired(fake_sdk):
    client = WatsonAssistantClient("key", "https://wa.example", "asst-1", environment_id="env-1")
    client.assistant.fail_message_with = 404
    with pytest.raises(WatsonSessionExpired):
        client.send_message("old-session", "Oi")


def test_other_api_errors_propagate(fake_sdk):
    client = WatsonAssistantClient("key", "https://wa.example", "asst-1", environment_id="env-1")
    client.assistant.fail_message_with = 401
    with pytest.raises(ApiException):
        client.send_message("sess", "Oi")
