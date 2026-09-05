import asyncio
from types import SimpleNamespace

import pytest

from aistudio_api.application.account_service import AccountService
from aistudio_api.infrastructure.account.account_store import AccountStore
from aistudio_api.infrastructure.account.login_service import LoginService


class Session:
    def __init__(self):
        self.auth_changes = []

    async def switch_auth(self, path):
        self.auth_changes.append(path)


def make_store(tmp_path, count=1):
    store = AccountStore(tmp_path / "accounts")
    accounts = [
        store.save_account(f"Test {i}", None, {"cookies": [], "origins": []})
        for i in range(count)
    ]
    for account in accounts:
        profile = store.get_profile_path(account.id)
        profile.mkdir()
        (profile / "test-profile.txt").write_text("test-only")
    return store, accounts


@pytest.mark.parametrize("deleted_index", [0, 1])
def test_delete_one_account_removes_profile_and_keeps_other(tmp_path, deleted_index):
    store, accounts = make_store(tmp_path, 2)
    removed, kept = accounts[deleted_index], accounts[1 - deleted_index]
    removed_dir = store.get_auth_path(removed.id).parent
    kept_path = store.get_auth_path(kept.id)
    kept_bytes = kept_path.read_bytes()
    session = Session()
    cleared = []
    service = AccountService(store, LoginService())
    assert asyncio.run(
        service.delete_account(
            removed.id,
            session,
            SimpleNamespace(clear=lambda: cleared.append(True)),
            asyncio.Semaphore(1),
            1,
        )
    )
    assert not removed_dir.exists()
    assert kept_path.read_bytes() == kept_bytes
    assert store.get_active_account().id == kept.id
    assert AccountStore(tmp_path / "accounts").get_account(removed.id) is None
    assert session.auth_changes[-1] == str(kept_path)
    assert cleared == [True]


def test_delete_last_account_clears_active_auth(tmp_path):
    store, accounts = make_store(tmp_path)
    session = Session()
    assert asyncio.run(
        AccountService(store, LoginService()).delete_account(
            accounts[0].id, session, None, None, 1
        )
    )
    assert store.list_accounts() == []
    assert store.get_active_account() is None
    assert session.auth_changes[-1] is None
