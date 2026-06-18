import json
import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from aistudio_api.infrastructure.cache.snapshot_cache import SnapshotCache
from aistudio_api.infrastructure.gateway import wire_codec
from aistudio_api.infrastructure.gateway.capture import RequestCaptureService
from aistudio_api.infrastructure.gateway.client import AIStudioClient
from aistudio_api.infrastructure.gateway.model_defaults import ModelDefaults
from aistudio_api.infrastructure.gateway.session import BrowserSession


class DummyCaptureSession:
    async def capture_template(self, model: str):
        return {
            "url": "https://example.test/GenerateContent",
            "headers": {},
            "body": json.dumps(
                [
                    "models/gemma-4-31b-it",
                    [[[[None, "old"]], "user"]],
                    None,
                    [None] * 27,
                    "!old-snapshot",
                    None,
                    None,
                ]
            ),
        }

    async def generate_snapshot(self, contents):
        return "!new-snapshot"


@pytest.mark.asyncio
async def test_capture_uses_requested_model_over_template_model(monkeypatch):
    monkeypatch.setattr(wire_codec, "resolve_model_defaults", lambda _model: ModelDefaults())
    service = RequestCaptureService(DummyCaptureSession(), SnapshotCache())

    captured = await service.capture(
        prompt="hello",
        model="models/gemini-3.5-flash",
        force_refresh=True,
    )

    assert captured is not None
    assert json.loads(captured.body)[0] == "models/gemini-3.5-flash"


class ClickFailButton:
    def click(self, timeout=None):
        raise TimeoutError(f"blocked after {timeout}")


class FakeTextarea:
    def __init__(self):
        self.clicked = False

    def click(self):
        self.clicked = True


class FakeKeyboard:
    def __init__(self):
        self.pressed: list[str] = []

    def press(self, key: str):
        self.pressed.append(key)


class FakeRunPage:
    def __init__(self):
        self.textarea = FakeTextarea()
        self.keyboard = FakeKeyboard()

    def query_selector(self, selector: str):
        if selector == "button:has-text('Run')":
            return ClickFailButton()
        if selector == "textarea":
            return self.textarea
        return None


def test_click_run_button_uses_ctrl_enter_fallback_when_button_is_blocked():
    session = BrowserSession.__new__(BrowserSession)
    page = FakeRunPage()

    assert session._click_run_button_sync(page) is True
    assert page.textarea.clicked is True
    assert page.keyboard.pressed == ["Control+Enter"]


class FakeStartupTextarea:
    def __init__(self):
        self.value = ""

    def fill(self, value):
        self.value = value


class FakeStartupRequest:
    url = "https://example.test/GenerateContent"
    post_data = "[" + ("0," * 60) + "0]"
    headers = {"content-type": "application/json+protobuf"}


class FakeStartupResponse:
    url = "https://example.test/GenerateContent"

    def __init__(self, status):
        self.status = status

    def text(self):
        return "[]"


class FakeStartupPage:
    def __init__(self, status):
        self.status = status
        self.textarea = FakeStartupTextarea()
        self.listeners = {"request": [], "response": []}

    def evaluate(self, _script):
        return None

    def on(self, event, callback):
        self.listeners[event].append(callback)

    def remove_listener(self, event, callback):
        self.listeners[event].remove(callback)

    def query_selector(self, selector):
        return self.textarea if selector == "textarea" else None

    def wait_for_timeout(self, _ms):
        return None

    def emit_generate_content(self):
        request = FakeStartupRequest()
        response = FakeStartupResponse(self.status)
        for callback in list(self.listeners["request"]):
            callback(request)
        for callback in list(self.listeners["response"]):
            callback(response)


def _page_prompt_session(status):
    session = BrowserSession.__new__(BrowserSession)
    session._templates = {}
    session._bootstrap_template = None
    page = FakeStartupPage(status)
    session._ensure_hook_page_sync = Mock(return_value=page)
    session._wait_until_idle_sync = Mock()

    def click_run_button(_page):
        page.emit_generate_content()
        return True

    session._click_run_button_sync = Mock(side_effect=click_run_button)
    return session


def test_send_page_prompt_caches_template_after_200():
    session = _page_prompt_session(status=200)

    status, _raw = session._send_page_prompt_sync("say 'ok'", "gemma-4-31b-it", 1000)

    assert status == 200
    assert session._bootstrap_template is not None
    assert "gemma-4-31b-it" in session._templates


def test_send_page_prompt_caches_template_after_403():
    session = _page_prompt_session(status=403)

    status, _raw = session._send_page_prompt_sync("say 'ok'", "gemma-4-31b-it", 1000)

    assert status == 403
    assert session._bootstrap_template is not None
    assert "gemma-4-31b-it" in session._templates


def _startup_client(send_page_prompt, show_hook_page=None):
    client = AIStudioClient.__new__(AIStudioClient)
    client.clear_snapshot_cache = Mock()
    client._session = SimpleNamespace(
        send_page_prompt=AsyncMock(side_effect=send_page_prompt),
        show_hook_page=AsyncMock(side_effect=show_hook_page),
    )
    client._build_user_content = Mock(return_value=object())
    return client


@pytest.mark.asyncio
async def test_startup_self_test_does_not_show_browser_on_success():
    client = _startup_client(send_page_prompt=[(200, b"[]")])

    assert await AIStudioClient.startup_self_test(client) is True
    client._session.send_page_prompt.assert_awaited_once()
    assert client._session.send_page_prompt.await_args.kwargs["prompt"] == "say 'ok'"
    client._session.show_hook_page.assert_not_awaited()
    client.clear_snapshot_cache.assert_not_called()


@pytest.mark.asyncio
async def test_startup_self_test_shows_browser_only_on_failure():
    client = _startup_client(send_page_prompt=[RuntimeError("cold 403"), RuntimeError("visible 403")])

    assert await AIStudioClient.startup_self_test(client) is False
    client.clear_snapshot_cache.assert_called_once()
    client._session.show_hook_page.assert_awaited_once()
    assert client._session.send_page_prompt.await_count == 2


@pytest.mark.asyncio
async def test_startup_self_test_treats_page_403_as_failure():
    client = _startup_client(
        send_page_prompt=[
            (403, b'[,[7,"The caller does not have permission"]]'),
            (403, b'[,[7,"The caller does not have permission"]]'),
        ]
    )

    assert await AIStudioClient.startup_self_test(client) is False
    client.clear_snapshot_cache.assert_called_once()
    client._session.show_hook_page.assert_awaited_once()
    assert client._session.send_page_prompt.await_count == 2


@pytest.mark.asyncio
async def test_startup_self_test_retries_on_visible_page_after_cold_failure():
    events = []
    send_count = 0

    async def send_page_prompt(**_kwargs):
        nonlocal send_count
        send_count += 1
        events.append(f"send{send_count}")
        if send_count == 1:
            raise RuntimeError("cold 403")
        return 200, b"[]"

    async def show_hook_page():
        events.append("show")

    client = _startup_client(
        send_page_prompt=send_page_prompt,
        show_hook_page=show_hook_page,
    )

    assert await AIStudioClient.startup_self_test(client) is True
    client.clear_snapshot_cache.assert_called_once()
    client._session.show_hook_page.assert_awaited_once()
    assert client._session.send_page_prompt.await_count == 2
    assert events == ["send1", "show", "send2"]


@pytest.mark.asyncio
async def test_startup_self_test_logs_failure_before_showing_browser(caplog):
    client = _startup_client(send_page_prompt=[RuntimeError("cold 403"), RuntimeError("visible 403")])

    async def show_hook_page():
        assert any("启动自检未通过" in record.message for record in caplog.records)

    client._session.show_hook_page = AsyncMock(side_effect=show_hook_page)

    with caplog.at_level(logging.WARNING, logger="aistudio"):
        assert await AIStudioClient.startup_self_test(client) is False

    assert any("即将打开可见 AI Studio 页面" in record.message for record in caplog.records)
