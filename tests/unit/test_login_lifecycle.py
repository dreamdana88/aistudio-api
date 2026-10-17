import asyncio
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from aistudio_api.api.dependencies import get_account_service, get_runtime_state
from aistudio_api.api.routes_accounts import router
from aistudio_api.application.account_service import AccountService
from aistudio_api.domain.errors import LoginInProgressError
from aistudio_api.infrastructure.account.account_store import AccountStore
from aistudio_api.infrastructure.account.login_service import (
    LOGIN_DONE_HOSTS,
    LoginService,
    LoginSession,
    LoginStatus,
)


class FakeRuntime:
    def __init__(self):
        self.client = SimpleNamespace(_session=None)
        self.snapshot_cache = SimpleNamespace(clear=lambda: None)
        self.busy_lock = None


@pytest.fixture
def login_api(tmp_path, monkeypatch):
    store = AccountStore(tmp_path / "accounts")
    service = AccountService(store, LoginService())

    async def hang_worker(self, session_id, account_store, name, *, headless, ui_locale):
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            session = self._sessions[session_id]
            if session.status == LoginStatus.PENDING:
                session.status = LoginStatus.CANCELLED
                session.error = "已取消"
            raise
        finally:
            self._tasks.pop(session_id, None)

    monkeypatch.setattr(LoginService, "_login_worker", hang_worker)
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_account_service] = lambda: service
    app.dependency_overrides[get_runtime_state] = lambda: FakeRuntime()
    return TestClient(app), service, store


def test_start_returns_remote_display_url(login_api, monkeypatch):
    from aistudio_api.config import settings

    monkeypatch.setattr(settings, "novnc_public_url", None)
    client, service, store = login_api
    first = client.post("/accounts/login/start", json={})
    assert first.status_code == 200
    body = first.json()
    assert body["session_id"]
    assert body["display_via"] == "ssh_tunnel"
    assert body["display_url"] == "http://127.0.0.1:6080/vnc.html?autoconnect=1&resize=scale"
    assert body["instruction"]
    assert store.list_accounts() == []


def test_start_uses_public_novnc_url(login_api, monkeypatch):
    from aistudio_api.config import settings

    monkeypatch.setattr(settings, "novnc_public_url", "https://LOGIN_DOMAIN:8443/")
    client, service, store = login_api
    started = client.post("/accounts/login/start", json={})
    assert started.status_code == 200
    body = started.json()
    assert body["display_via"] == "public"
    assert body["display_url"] == "https://LOGIN_DOMAIN:8443/vnc.html?autoconnect=1&resize=scale"
    assert "Google" in body["instruction"]
    assert store.list_accounts() == []


def test_second_start_is_rejected_while_pending(login_api):
    client, service, store = login_api
    service._login._sessions["login_old"] = LoginSession(session_id="login_old")
    second = client.post("/accounts/login/start", json={})
    assert second.status_code == 409
    assert store.list_accounts() == []


def test_cancel_recycles_session_and_does_not_save(login_api):
    client, service, store = login_api
    session = LoginSession(session_id="login_manual")
    service._login._sessions[session.session_id] = session
    cancelled = client.post(f"/accounts/login/cancel/{session.session_id}")
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    status = client.get(f"/accounts/login/status/{session.session_id}")
    assert status.json()["status"] == "cancelled"
    assert status.json()["account_id"] is None
    assert store.list_accounts() == []
    third = client.post("/accounts/login/start", json={})
    assert third.status_code == 200


def test_failed_status_is_not_completed():
    session = LoginSession(session_id="login_x", status=LoginStatus.FAILED, error="登录超时（30 秒）")
    assert session.status != LoginStatus.COMPLETED
    assert session.account_id is None


def test_login_completes_only_on_aistudio_host():
    assert LOGIN_DONE_HOSTS == {"aistudio.google.com"}


def test_start_login_raises_when_pending(monkeypatch):
    service = LoginService()
    service._sessions["login_old"] = LoginSession(session_id="login_old")

    async def boom(*args, **kwargs):
        raise AssertionError("should not start another worker")

    monkeypatch.setattr(LoginService, "_login_worker", boom)
    with pytest.raises(LoginInProgressError):
        asyncio.run(service.start_login(SimpleNamespace(), None))
