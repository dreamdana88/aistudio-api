"""账号管理应用服务，协调 account_store 和 login_service。"""

from __future__ import annotations

import asyncio
from contextlib import AsyncExitStack
import logging
from typing import Any

from aistudio_api.infrastructure.account.account_store import AccountStore, AccountMeta
from aistudio_api.infrastructure.account.login_service import LoginService, LoginSession

logger = logging.getLogger("aistudio.account")


class AccountService:
    """账号管理服务。"""

    def __init__(
        self,
        account_store: AccountStore,
        login_service: LoginService,
    ) -> None:
        self._store = account_store
        self._login = login_service
        self._delete_lock = asyncio.Lock()

    def list_accounts(self) -> list[AccountMeta]:
        """列出所有账号。"""
        return self._store.list_accounts()

    def get_account(self, account_id: str) -> AccountMeta | None:
        """获取单个账号。"""
        return self._store.get_account(account_id)

    def get_active_account(self) -> AccountMeta | None:
        """获取当前活跃账号。"""
        return self._store.get_active_account()

    async def start_login(
        self,
        name: str | None = None,
        *,
        headless: bool = False,
        ui_locale: str | None = None,
    ) -> str:
        """启动登录流程，返回 session_id。"""
        return await self._login.start_login(
            self._store,
            name,
            headless=headless,
            ui_locale=ui_locale,
        )

    def get_login_status(self, session_id: str) -> LoginSession | None:
        """获取登录状态。"""
        return self._login.get_status(session_id)

    async def cancel_login(self, session_id: str) -> LoginSession | None:
        """取消进行中的登录并回收临时浏览器。"""
        return await self._login.cancel_login(session_id)

    async def activate_account(
        self,
        account_id: str,
        browser_session: Any,
        snapshot_cache: Any,
        busy_lock: Any = None,  # None = skip lock (caller already holds it)
        keep_snapshot_cache: bool = False,
    ) -> AccountMeta | None:
        """切换到指定账号。"""
        account = self._store.get_account(account_id)
        if account is None:
            return None

        async def _do_switch():
            auth_path = self._store.get_auth_path_optional(account_id, require_exists=False)
            if auth_path is None:
                logger.error("账号 %s 的账号目录不存在", account_id)
                return None

            await browser_session.switch_auth(str(auth_path))
            await browser_session.ensure_context()

            if not keep_snapshot_cache and snapshot_cache is not None:
                snapshot_cache.clear()
                logger.info("已清除 snapshot 缓存")

            self._store.set_active_account(account_id)
            logger.info("已切换到账号: %s (%s)", account_id, account.name)
            return account

        if busy_lock is not None:
            async with busy_lock:
                return await _do_switch()
        return await _do_switch()

    async def delete_account(
        self, account_id: str, browser_session: Any, snapshot_cache: Any,
        busy_lock: Any, concurrency: int,
    ) -> bool:
        """Drain requests, detach credentials, delete files, then select remaining auth."""
        async with self._delete_lock, AsyncExitStack() as stack:
            if busy_lock is not None:
                for _ in range(max(1, concurrency)):
                    await stack.enter_async_context(busy_lock)
            if self._store.get_account(account_id) is None:
                return False
            if browser_session is not None:
                await browser_session.switch_auth(None)
            if snapshot_cache is not None:
                snapshot_cache.clear()
            try:
                return self._store.delete_account(account_id)
            finally:
                active = self._store.get_active_account()
                auth = self._store.get_auth_path(active.id) if active else None
                if browser_session is not None:
                    await browser_session.switch_auth(str(auth) if auth else None)

    def update_account(self, account_id: str, name: str) -> AccountMeta | None:
        """更新账号名称。"""
        return self._store.update_account(account_id, name)
