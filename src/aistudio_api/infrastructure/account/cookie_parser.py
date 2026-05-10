"""解析浏览器 cookie 字符串，转换为 Playwright storage state 格式。"""

from __future__ import annotations

import time
from typing import Any

_DOMAIN_OVERRIDES: dict[str, list[str]] = {
    "OSID": [".youtube.com"],
    "__Secure-OSID": [".youtube.com"],
    "__Secure-BUCKET": ["aistudio.google.com"],
    "OTZ": ["accounts.google.com"],
    "__Host-GAPS": ["accounts.google.com"],
}

# 需要复制到多个 Google 域名的核心认证 cookie
_MULTI_DOMAIN_COOKIES = {
    "SID", "__Secure-1PSID", "__Secure-3PSID",
    "HSID", "SSID",
    "APISID", "SAPISID", "__Secure-1PAPISID", "__Secure-3PAPISID",
    "NID",
}

# YouTube 域名列表（用于复制核心 cookie）
_GOOGLE_DOMAINS = [
    ".google.com",
    ".youtube.com",
    ".google.com.tw",
]


def parse_cookie_string(raw: str) -> dict[str, Any]:
    """将 `key=value; key=value` 格式的 cookie 字符串解析为 Playwright storage state。

    Args:
        raw: 浏览器开发者工具或扩展导出的 cookie 字符串

    Returns:
        Playwright storage state dict，包含 cookies 和 origins 字段
    """
    pairs: list[tuple[str, str]] = []
    for part in raw.split(";"):
        part = part.strip()
        if not part or "=" not in part:
            continue
        name, _, value = part.partition("=")
        name = name.strip()
        value = value.strip()
        if name:
            pairs.append((name, value))

    now = int(time.time())
    default_expires = now + 86400 * 180  # 180 天后过期

    seen: set[tuple[str, str]] = set()  # (name, domain) 去重
    cookies: list[dict[str, Any]] = []

    def _add_cookie(name: str, value: str, domain: str) -> None:
        key = (name, domain)
        if key in seen:
            return
        seen.add(key)
        cookies.append({
            "name": name,
            "value": value,
            "domain": domain,
            "path": "/",
            "secure": True,
            "httpOnly": False,
            "sameSite": "None",
            "expires": default_expires,
        })

    for name, value in pairs:
        # 有域名覆盖的 cookie
        if name in _DOMAIN_OVERRIDES:
            for domain in _DOMAIN_OVERRIDES[name]:
                _add_cookie(name, value, domain)
            continue

        # 核心认证 cookie → 复制到多个域名
        if name in _MULTI_DOMAIN_COOKIES:
            for domain in _GOOGLE_DOMAINS:
                _add_cookie(name, value, domain)
            continue

        # 其余 cookie → .google.com
        _add_cookie(name, value, ".google.com")

    return {
        "cookies": cookies,
        "origins": [],
    }


def parse_and_filter_google_cookies(raw: str) -> list[dict[str, Any]]:
    state = parse_cookie_string(raw)
    return [c for c in state["cookies"] if "google" in c.get("domain", "")]
