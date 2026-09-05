import json
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from aistudio_api.api.dependencies import get_account_service
from aistudio_api.api.routes_accounts import router
from aistudio_api.application.account_service import AccountService
from aistudio_api.infrastructure.account.account_store import AccountStore
from aistudio_api.infrastructure.account.login_service import LoginService


@pytest.fixture
def account_api(tmp_path):
    store = AccountStore(tmp_path / "accounts")
    account = store.save_account("账号备注", "signed-in@example.org", {"cookies": [], "origins": []})
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_account_service] = lambda: AccountService(store, LoginService())
    return TestClient(app), store, account


def test_account_email_is_read_only(account_api):
    client, store, account = account_api
    auth = store.get_auth_path(account.id)
    before = auth.read_bytes()
    response = client.put(
        "/accounts/" + account.id,
        json={"name": "账号备注", "email": "someone-else@example.org"},
    )
    assert response.status_code == 422
    assert store.get_account(account.id).email == "signed-in@example.org"
    assert auth.read_bytes() == before


def test_renaming_does_not_change_bound_identity(account_api):
    client, store, account = account_api
    response = client.put("/accounts/" + account.id, json={"name": "新备注"})
    assert response.status_code == 200
    assert response.json()["email"] == "signed-in@example.org"
    auth = store.get_auth_path(account.id)
    fresh = AccountStore(auth.parent.parent)
    assert fresh.get_account(account.id).email == "signed-in@example.org"
    assert json.loads(auth.with_name("meta.json").read_text(encoding="utf8"))["email"] == "signed-in@example.org"


def test_import_rejects_user_supplied_email(account_api):
    client, store, _ = account_api
    response = client.post(
        "/accounts/import-cookies",
        json={"cookies": "SID=test", "email": "fake@example.org"},
    )
    assert response.status_code == 422
    assert len(store.list_accounts()) == 1


def test_import_without_verified_identity_stays_unknown(account_api):
    client, store, _ = account_api
    response = client.post("/accounts/import-cookies", json={"cookies": "SID=test"})
    assert response.status_code == 200
    imported = store.get_account(response.json()["account_id"])
    assert imported.email is None


def test_ui_has_no_email_editor():
    static = Path(__file__).resolve().parents[2] / "src/aistudio_api/static"
    html = (static / "index.html").read_text(encoding="utf8")
    js = (static / "app.js").read_text(encoding="utf8")
    assert "编辑邮箱" not in html
    assert "邮箱未识别" in html
    assert "cookieModal.email" not in html + js
