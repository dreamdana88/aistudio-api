"""Browser lifecycle management for Camoufox and Chromium backends."""

from __future__ import annotations

import json
import logging
import socket
import subprocess
import sys
import time
import importlib.util
from pathlib import Path
from typing import Any, Optional

from aistudio_api.config import settings
from aistudio_api.infrastructure.browser.browser_engine import (
    async_maximize_page_window,
    build_browser_context_options,
    describe_browser_backend,
    is_camoufox_engine,
)

logger = logging.getLogger("aistudio.camoufox")
LAUNCHER_PATH = Path(__file__).with_name("camoufox_launcher.py")


def _pick_free_local_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        sock.listen(1)
        return int(sock.getsockname()[1])


class CamoufoxManager:
    def __init__(
        self,
        port: int = 9222,
        auth_profile: Optional[str] = None,
        headless: bool = True,
    ):
        self.port = port
        self.auth_profile = auth_profile
        self.headless = headless
        self._process: Optional[subprocess.Popen] = None
        self._ws_endpoint: Optional[str] = None
        self._browser = None
        self._context = None
        self._page = None
        self._playwright = None
        self.python_executable = settings.browser_python or sys.executable

    async def start(self) -> str | None:
        if self._ws_endpoint:
            return self._ws_endpoint
        if not is_camoufox_engine():
            logger.info("Using %s backend", describe_browser_backend())
            return None

        existing_data = None
        try:
            import urllib.request

            resp = urllib.request.urlopen(f"http://127.0.0.1:{self.port}/json", timeout=2)
            existing_data = json.loads(resp.read())
        except Exception:
            existing_data = None

        if existing_data is not None:
            old_port = self.port
            self.port = _pick_free_local_port()
            logger.info("Port %s already has a browser, switching login flow to free port %s", old_port, self.port)

        logger.info("Starting Camoufox on port %s...", self.port)
        cmd = [
            self.python_executable,
            str(LAUNCHER_PATH),
            "--port",
            str(self.port),
        ]
        if self.headless:
            cmd.append("--headless")

        self._process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        for _ in range(30):
            time.sleep(1)
            if self._process and self._process.poll() is not None:
                output = ""
                if self._process.stdout:
                    try:
                        output = self._process.stdout.read()
                    except Exception:
                        output = ""
                hint = self._build_failure_hint(output)
                raise RuntimeError(
                    "Camoufox exited before startup. "
                    f"Command: {' '.join(cmd)}. "
                    f"Output: {output.strip() or '<no output>'}. "
                    f"{hint}"
                )
            try:
                import urllib.request

                resp = urllib.request.urlopen(f"http://127.0.0.1:{self.port}/json", timeout=2)
                data = json.loads(resp.read())
                if "wsEndpointPath" in data:
                    self._ws_endpoint = f"ws://127.0.0.1:{self.port}{data['wsEndpointPath']}"
                    logger.info("Camoufox started: %s", self._ws_endpoint)
                    return self._ws_endpoint
            except Exception:
                continue

        output = ""
        if self._process and self._process.stdout:
            try:
                output = self._process.stdout.read()
            except Exception:
                output = ""
        hint = self._build_failure_hint(output)
        raise RuntimeError(
            "Camoufox failed to start within 30s. "
            f"Command: {' '.join(cmd)}. "
            f"Output: {output.strip() or '<no output>'}. "
            f"{hint}"
        )

    def _build_failure_hint(self, output: str) -> str:
        if settings.browser_python:
            return (
                f"Check whether AISTUDIO_BROWSER_PYTHON={settings.browser_python} "
                "has camoufox installed and can run `-m camoufox.server`."
            )

        current_has_camoufox = importlib.util.find_spec("camoufox.server") is not None
        if not current_has_camoufox:
            return (
                "Current server interpreter does not appear to have camoufox installed. "
                "Run the server with the environment that has camoufox, or set "
                "AISTUDIO_BROWSER_PYTHON to that Python executable."
            )

        if not output.strip():
            return (
                "Camoufox produced no output. Try launching it manually with the same command "
                "to inspect runtime dependencies."
            )

        return "Inspect the command output above for startup failures."

    async def launch_browser(self, playwright):
        if self._browser and self._browser.is_connected():
            return self._browser

        if is_camoufox_engine():
            if not self._ws_endpoint:
                await self.start()
            self._browser = await playwright.firefox.connect(self._ws_endpoint)
            return self._browser
        from aistudio_api.infrastructure.browser.browser_engine import async_launch_browser

        self._browser = await async_launch_browser(headless=self.headless)
        logger.info("Started %s", describe_browser_backend())
        return self._browser

    async def get_page(self):
        if self._page and not self._page.is_closed():
            return self._page

        if is_camoufox_engine():
            from playwright.async_api import async_playwright

            if self._playwright is None:
                self._playwright = await async_playwright().start()
            if self._browser is None or not self._browser.is_connected():
                self._browser = await self.launch_browser(self._playwright)
        else:
            if self._browser is None or not self._browser.is_connected():
                self._browser = await self.launch_browser(None)

        if is_camoufox_engine():
            ctx = self._browser.contexts[0]
        else:
            self._context = self._context or await self._browser.new_context(**build_browser_context_options(headless=self.headless))
            ctx = self._context

        self._page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        await async_maximize_page_window(self._page, headless=self.headless)
        return self._page

    async def evaluate(self, js_code: str, timeout: int = 30000) -> Any:
        page = await self.get_page()
        return await page.evaluate(js_code)

    async def navigate(self, url: str):
        page = await self.get_page()
        await page.goto(url, wait_until="networkidle")

    async def fetch_in_browser(
        self,
        url: str,
        method: str = "POST",
        headers: Optional[dict[str, str]] = None,
        body: Optional[str] = None,
    ) -> dict[str, Any]:
        headers_js = json.dumps(headers or {})
        body_js = json.dumps(body) if body else "undefined"

        js_code = f"""(async () => {{
            try {{
                const resp = await fetch({json.dumps(url)}, {{
                    method: {json.dumps(method)},
                    headers: {headers_js},
                    body: {body_js},
                    credentials: 'include',
                }});
                const text = await resp.text();
                return {{status: resp.status, text: text}};
            }} catch(e) {{
                return {{error: e.message}};
            }}
        }})()"""

        return await self.evaluate(js_code, timeout=60000)

    async def stop(self):
        if self._page:
            try:
                await self._page.close()
            except Exception:
                pass
        if self._context:
            try:
                await self._context.close()
            except Exception:
                pass
        if self._browser:
            try:
                await self._browser.close()
            except Exception:
                pass
        if self._playwright:
            try:
                await self._playwright.stop()
            except Exception:
                pass
        if self._process:
            try:
                self._process.terminate()
            except Exception:
                pass
        self._ws_endpoint = None
        self._browser = None
        self._context = None
        self._page = None
        self._playwright = None
