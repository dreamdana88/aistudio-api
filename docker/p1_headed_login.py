#!/usr/bin/env python3
"""P1 temporary headed login browser.

Opens Google's login page on the container Xvfb display so a human can
complete sign-in over noVNC. This session is experimental: it does not
write accounts, auth.json, or storage_state into the account store.
"""

from __future__ import annotations

import asyncio
import json
import os
import signal
import sys
import time
from pathlib import Path
from urllib.parse import urlencode, urlparse

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

STATUS_PATH = Path(os.environ.get("AISTUDIO_P1_STATUS_FILE", "/tmp/p1-login-session.json"))
TIMEOUT_SEC = int(os.environ.get("AISTUDIO_P1_TIMEOUT", "2400"))
SUCCESS_HOSTS = {"aistudio.google.com"}


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def write_status(**kwargs) -> None:
    payload = {
        "experimental": True,
        "not_an_account": True,
        "updated_at": _now(),
        **kwargs,
    }
    STATUS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def build_login_url() -> str:
    query = {
        "continue": "https://aistudio.google.com",
        "hl": os.environ.get("AISTUDIO_P1_HL", "en-US"),
    }
    return f"https://accounts.google.com/ServiceLogin?{urlencode(query)}"


async def main() -> int:
    display = os.environ.get("AISTUDIO_LOGIN_DISPLAY") or os.environ.get("DISPLAY") or ":99"
    os.environ["DISPLAY"] = display
    login_url = build_login_url()
    write_status(
        status="starting",
        display=display,
        login_url=login_url,
        note="P1 experimental session; will not save an account",
    )

    from aistudio_api.config import build_browser_proxy, settings
    from aistudio_api.infrastructure.browser.browser_engine import (
        _build_cloakbrowser_args,
        async_maximize_page_window,
        build_browser_context_options,
        describe_browser_backend,
    )
    from cloakbrowser import launch_async

    print(f"P1 headed login: display={display} backend={describe_browser_backend()}", flush=True)
    browser = await launch_async(
        headless=False,
        proxy=build_browser_proxy(settings.proxy_url),
        stealth_args=False,
        chromium_sandbox=False,
        args=_build_cloakbrowser_args(
            headless=False,
            extra_args=["--disable-dev-shm-usage"],
        ),
    )
    context = await browser.new_context(**build_browser_context_options(headless=False))
    page = await context.new_page()
    await async_maximize_page_window(page, headless=False)

    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, stop.set)

    try:
        print(f"P1 headed login: opening {login_url}", flush=True)
        await page.goto(login_url, wait_until="domcontentloaded", timeout=60000)
        write_status(
            status="google_login_visible",
            display=display,
            url=page.url,
            title=await page.title(),
            login_url=login_url,
        )
        print(f"P1 headed login: page url={page.url!r} title={await page.title()!r}", flush=True)

        deadline = time.monotonic() + TIMEOUT_SEC
        reached = False
        while not stop.is_set() and time.monotonic() < deadline:
            url = page.url or ""
            host = urlparse(url).hostname or ""
            title = ""
            try:
                title = await page.title()
            except Exception:
                pass
            status = "reached_aistudio" if host in SUCCESS_HOSTS else "waiting_user"
            if host in SUCCESS_HOSTS:
                reached = True
            write_status(
                status=status,
                display=display,
                url=url,
                host=host,
                title=title,
                login_url=login_url,
            )
            if reached:
                print(f"P1 headed login: reached AI Studio at {url}", flush=True)
                # Keep the page up so the operator can look around; still not an account save.
                while not stop.is_set() and time.monotonic() < deadline:
                    await asyncio.sleep(2)
                break
            try:
                await asyncio.wait_for(stop.wait(), timeout=3)
            except asyncio.TimeoutError:
                pass

        if not reached and not stop.is_set():
            write_status(
                status="timeout",
                display=display,
                url=page.url,
                login_url=login_url,
            )
            print("P1 headed login: timed out waiting for AI Studio", flush=True)
            return 2
        write_status(
            status="stopped" if stop.is_set() and not reached else "reached_aistudio",
            display=display,
            url=page.url,
            login_url=login_url,
        )
        return 0
    except Exception as exc:
        write_status(status="failed", error=str(exc), display=display, login_url=login_url)
        print(f"P1 headed login failed: {exc}", flush=True)
        raise
    finally:
        try:
            await browser.close()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
