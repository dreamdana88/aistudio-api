from aistudio_api.infrastructure.account.cookie_parser import (
    build_google_cookie_list,
    parse_cookie_string,
)
from aistudio_api.infrastructure.account.cookie_refresher import load_cookies_from_string
from aistudio_api.infrastructure.gateway.session import BrowserSession


def test_parse_cookie_string_skips_host_only_cookies_in_storage_state():
    state = parse_cookie_string("__Host-GAPS=abc; SID=sid123")

    assert state["origins"] == []
    assert {cookie["name"] for cookie in state["cookies"]} == {"SID"}
    assert state["cookies"][0]["domain"] == ".google.com"


def test_build_google_cookie_list_uses_url_for_host_targets_when_injecting():
    cookies = build_google_cookie_list(
        [("__Host-GAPS", "abc"), ("LSID", "lsid123"), ("SID", "sid123")],
        allow_url_targets=True,
    )

    by_name = {cookie["name"]: cookie for cookie in cookies}
    assert by_name["__Host-GAPS"]["url"] == "https://accounts.google.com/"
    assert "domain" not in by_name["__Host-GAPS"]
    assert by_name["LSID"]["url"] == "https://accounts.google.com/"
    assert by_name["SID"]["domain"] == ".google.com"


def test_load_cookies_from_string_builds_playwright_safe_cookies(monkeypatch):
    def fake_refresh(_: dict[str, str]) -> dict[str, str]:
        return {
            "__Host-GAPS": "abc",
            "LSID": "lsid123",
            "SID": "sid123",
        }

    monkeypatch.setattr(
        "aistudio_api.infrastructure.account.cookie_refresher._refresh_session_cookies",
        fake_refresh,
    )

    cookies = load_cookies_from_string("SID=sid123")
    by_name = {cookie["name"]: cookie for cookie in cookies}

    assert by_name["LSID"]["domain"] == ".google.com"
    assert by_name["SID"]["domain"] == ".google.com"
    assert "__Host-GAPS" not in by_name


def test_load_cookies_from_string_keeps_accounts_cookies_from_raw_string(monkeypatch):
    def fake_refresh(_: dict[str, str]) -> dict[str, str]:
        return {
            "SID": "sid_from_refresh",
            "__Host-GAPS": "gaps_from_refresh",
        }

    monkeypatch.setattr(
        "aistudio_api.infrastructure.account.cookie_refresher._refresh_session_cookies",
        fake_refresh,
    )

    cookies = load_cookies_from_string(
        "SID=sid_from_raw; LSID=lsid_raw; __Host-1PLSID=one_raw; ACCOUNT_CHOOSER=chooser_raw"
    )
    by_name = {cookie["name"]: cookie for cookie in cookies}

    assert by_name["SID"]["value"] == "sid_from_refresh"
    assert by_name["LSID"]["domain"] == ".google.com"
    assert by_name["ACCOUNT_CHOOSER"]["domain"] == ".google.com"
    assert "__Host-1PLSID" not in by_name


class _FakeContext:
    def __init__(self, cookies):
        self._cookies = cookies

    def cookies(self):
        return self._cookies


class _FakePage:
    url = "https://aistudio.google.com/prompts/new_chat"


def test_replace_account_cookies_rebuilds_profile_and_verifies(tmp_path, monkeypatch):
    account_dir = tmp_path / "acc_test"
    profile_dir = account_dir / "profile"
    profile_dir.mkdir(parents=True)
    (profile_dir / "stale-cookie-db").write_text("stale", encoding="utf-8")
    auth_file = account_dir / "auth.json"
    auth_file.write_text('{"cookies":[]}', encoding="utf-8")

    cookies = [{"name": "SID", "value": "new", "domain": ".google.com"}]
    monkeypatch.setattr(
        "aistudio_api.infrastructure.account.cookie_refresher.load_cookies_from_string",
        lambda raw: cookies,
    )

    session = BrowserSession.__new__(BrowserSession)
    session._auth_file = str(auth_file)
    session._profile_dir = str(profile_dir)
    session._hook_page = _FakePage()
    session._ctx = None
    session._close_sync = lambda: None
    session._derive_profile_dir = lambda _: str(profile_dir)
    session._switch_auth_sync = lambda value: setattr(session, "_auth_file", value)
    saved = []
    session._save_cookies_sync = lambda **kwargs: saved.append(kwargs.get("cookies"))

    context = _FakeContext(cookies)

    def ensure_browser():
        session._hook_page = _FakePage()
        return context

    session._ensure_browser_sync = ensure_browser

    count = session._replace_account_cookies_sync("SID=new", str(auth_file))

    assert count == 1
    assert not (profile_dir / "stale-cookie-db").exists()
    assert saved[0] == cookies
    assert saved[-1] is None


def test_replace_account_cookies_removes_partial_profile_on_failure(tmp_path, monkeypatch):
    account_dir = tmp_path / "acc_test"
    profile_dir = account_dir / "profile"
    profile_dir.mkdir(parents=True)
    auth_file = account_dir / "auth.json"
    auth_file.write_text('{"cookies":[]}', encoding="utf-8")

    cookies = [{"name": "SID", "value": "bad", "domain": ".google.com"}]
    monkeypatch.setattr(
        "aistudio_api.infrastructure.account.cookie_refresher.load_cookies_from_string",
        lambda raw: cookies,
    )

    session = BrowserSession.__new__(BrowserSession)
    session._auth_file = str(auth_file)
    session._profile_dir = str(profile_dir)
    session._hook_page = None
    session._ctx = None
    session._close_sync = lambda: None
    session._derive_profile_dir = lambda _: str(profile_dir)
    session._switch_auth_sync = lambda value: setattr(session, "_auth_file", value)
    session._save_cookies_sync = lambda **kwargs: None

    def fail_browser():
        profile_dir.mkdir(parents=True, exist_ok=True)
        (profile_dir / "partial").write_text("partial", encoding="utf-8")
        raise RuntimeError("login failed")

    session._ensure_browser_sync = fail_browser

    import pytest

    with pytest.raises(RuntimeError, match="login failed"):
        session._replace_account_cookies_sync("SID=bad", str(auth_file))

    assert not profile_dir.exists()
