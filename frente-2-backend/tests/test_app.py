"""Testes das rotas Flask com um cliente do Watson falso (sem rede)."""

import pytest
from ibm_watson import ApiException

from app import create_app
from watson_client import WatsonReply, WatsonSessionExpired


class FakeWatsonClient:
    def __init__(self):
        self.sessions_created = 0
        self.expire_once = False
        self.raise_api_error = None

    def create_session(self):
        self.sessions_created += 1
        return f"sess-{self.sessions_created}"

    def send_message(self, session_id, text):
        if self.raise_api_error:
            raise ApiException(self.raise_api_error, message="Unauthorized")
        if self.expire_once:
            self.expire_once = False
            raise WatsonSessionExpired("Invalid Session")
        if "dor no peito" in text.lower():
            return WatsonReply(
                reply="Procure emergência agora.",
                intent="emergencia",
                confidence=0.98,
                entities=[{"entity": "sintoma", "value": "dor no peito", "confidence": 1.0}],
            )
        return WatsonReply(reply=f"Você disse: {text}", intent="saudacao", confidence=0.8)


@pytest.fixture
def fake_client():
    return FakeWatsonClient()


@pytest.fixture
def client(fake_client):
    app = create_app(client=fake_client)
    app.config["TESTING"] = True
    return app.test_client()


def test_health_reports_configured_client(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.get_json() == {
        "status": "ok",
        "service": "cardioia-backend",
        "watson_configured": True,
    }


def test_health_without_client_and_without_env(monkeypatch):
    for name in ("WA_API_KEY", "WA_URL", "WA_ASSISTANT_ID"):
        monkeypatch.delenv(name, raising=False)
    app = create_app(client=None)
    res = app.test_client().get("/api/health")
    assert res.get_json()["watson_configured"] is False


def test_index_renders_test_page(client):
    res = client.get("/")
    assert res.status_code == 200
    assert "Simulação acadêmica".encode("utf-8") in res.data


def test_chat_creates_session_and_returns_material_contract(client, fake_client):
    res = client.post("/api/chat", json={"message": "Olá"})
    body = res.get_json()
    assert res.status_code == 200
    assert body["response"] == "Você disse: Olá"  # contrato do Cap. 10
    assert body["reply"] == body["response"]  # contrato do README da frente
    assert body["session_id"] == "sess-1"
    assert body["intent"] == "saudacao"
    assert fake_client.sessions_created == 1


def test_chat_reuses_session_id(client, fake_client):
    first = client.post("/api/chat", json={"message": "Olá"}).get_json()
    second = client.post(
        "/api/chat", json={"message": "Estou com dor no peito", "session_id": first["session_id"]}
    ).get_json()
    assert second["session_id"] == first["session_id"]
    assert second["intent"] == "emergencia"
    assert second["entities"][0]["value"] == "dor no peito"
    assert fake_client.sessions_created == 1


def test_chat_recreates_session_when_expired(client, fake_client):
    fake_client.expire_once = True
    res = client.post("/api/chat", json={"message": "Oi", "session_id": "sess-antiga"})
    body = res.get_json()
    assert res.status_code == 200
    assert body["session_id"] == "sess-1"
    assert fake_client.sessions_created == 1


def test_chat_rejects_empty_message(client):
    res = client.post("/api/chat", json={"message": "   "})
    assert res.status_code == 400
    assert "message" in res.get_json()["error"]


def test_chat_returns_503_when_not_configured(monkeypatch):
    for name in ("WA_API_KEY", "WA_URL", "WA_ASSISTANT_ID"):
        monkeypatch.delenv(name, raising=False)
    app = create_app(client=None)
    res = app.test_client().post("/api/chat", json={"message": "Oi"})
    assert res.status_code == 503
    assert "WA_API_KEY" in res.get_json()["error"]


def test_chat_returns_502_on_watson_api_error(client, fake_client):
    fake_client.raise_api_error = 401
    res = client.post("/api/chat", json={"message": "Oi"})
    assert res.status_code == 502
    assert res.get_json()["detail"] == "Unauthorized"
