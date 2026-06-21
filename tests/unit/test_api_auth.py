from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from aistudio_api.api.app import app as application
from aistudio_api.api.dependencies import require_api_key
from aistudio_api.config import settings


def _build_client() -> TestClient:
    app = FastAPI()

    @app.get("/protected", dependencies=[Depends(require_api_key)])
    async def protected():
        return {"ok": True}

    return TestClient(app)


def test_auth_is_disabled_when_no_api_key_is_configured(monkeypatch):
    monkeypatch.setattr(settings, "api_keys", frozenset())
    client = _build_client()

    response = client.get("/protected")

    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_bearer_token_is_accepted(monkeypatch):
    monkeypatch.setattr(settings, "api_keys", frozenset({"secret-token"}))
    client = _build_client()

    response = client.get("/protected", headers={"Authorization": "Bearer secret-token"})

    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_x_api_key_is_accepted(monkeypatch):
    monkeypatch.setattr(settings, "api_keys", frozenset({"secret-token"}))
    client = _build_client()

    response = client.get("/protected", headers={"X-API-Key": "secret-token"})

    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_missing_or_invalid_api_key_returns_401(monkeypatch):
    monkeypatch.setattr(settings, "api_keys", frozenset({"secret-token"}))
    client = _build_client()

    response = client.get("/protected")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.json()["detail"]["type"] == "authentication_error"

    invalid_response = client.get(
        "/protected",
        headers={"Authorization": "Bearer wrong-token"},
    )
    assert invalid_response.status_code == 401


def test_health_is_public_but_auth_verify_is_protected(monkeypatch):
    monkeypatch.setattr(settings, "api_keys", frozenset({"secret-token"}))
    client = TestClient(application)

    health_response = client.get("/health")
    missing_response = client.get("/auth/verify")
    valid_response = client.get(
        "/auth/verify",
        headers={"Authorization": "Bearer secret-token"},
    )

    assert health_response.status_code == 200
    assert health_response.json()["status"] == "ok"
    assert missing_response.status_code == 401
    assert valid_response.status_code == 200
    assert valid_response.json() == {"ok": True}
