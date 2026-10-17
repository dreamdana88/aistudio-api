"""Pinned browser packages still match the calls this project makes."""

import inspect
from importlib.metadata import version

import cloakbrowser.config as cloak_config
from cloakbrowser import launch, launch_async, launch_persistent_context
from playwright.async_api import BrowserType


def test_pinned_browser_versions():
    assert version("cloakbrowser") == "0.6.3"
    assert version("playwright") == "1.64.0"
    assert version("curl-cffi") == "0.16.3"


def test_launch_calls_match_cloakbrowser_0_6_3():
    assert "stealth_args" in inspect.signature(launch).parameters
    assert "headless" in inspect.signature(launch_async).parameters
    assert inspect.signature(launch_async).parameters["kwargs"].kind is inspect.Parameter.VAR_KEYWORD
    assert "user_data_dir" in inspect.signature(launch_persistent_context).parameters
    assert "chromium_sandbox" in inspect.signature(BrowserType.launch).parameters


def test_linux_arm64_binary_cache_contract(monkeypatch):
    monkeypatch.setattr(cloak_config.platform, "system", lambda: "Linux")
    monkeypatch.setattr(cloak_config.platform, "machine", lambda: "aarch64")
    monkeypatch.delenv("CLOAKBROWSER_CACHE_DIR", raising=False)
    monkeypatch.setattr(cloak_config.Path, "home", lambda: cloak_config.Path("/root"))

    assert cloak_config.get_platform_tag() == "linux-arm64"
    assert cloak_config.get_archive_name() == "cloakbrowser-linux-arm64.tar.gz"
    assert cloak_config.get_cache_dir() == cloak_config.Path("/root/.cloakbrowser")
    assert cloak_config.get_binary_path().as_posix().endswith(
        f"chromium-{cloak_config.get_chromium_version()}/chrome"
    )
    assert cloak_config.PLATFORM_CHROMIUM_VERSIONS["linux-arm64"]
    assert cloak_config.PLATFORM_CHROMIUM_VERSIONS["linux-x64"]
