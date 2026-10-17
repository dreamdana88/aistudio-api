"""Generation concurrency is the existing semaphore, not a second scheduler."""

import asyncio
import threading
import time

import pytest
from fastapi import HTTPException

from aistudio_api.api.state import runtime_state
from aistudio_api.application.api_service_common import require_busy_lock
from aistudio_api.infrastructure.gateway.session import BrowserSession


def test_semaphore_admits_three_and_rejects_the_fourth():
    previous = runtime_state.busy_lock
    runtime_state.busy_lock = asyncio.Semaphore(3)
    try:
        asyncio.run(_admit_three())
    finally:
        runtime_state.busy_lock = previous


async def _admit_three():
    semaphore = runtime_state.busy_lock
    entered = asyncio.Event()
    release = asyncio.Event()
    active = 0

    async def hold():
        nonlocal active
        async with semaphore:
            active += 1
            if active == 1:
                assert require_busy_lock() is semaphore
            if active == 3:
                entered.set()
            await release.wait()

    tasks = [asyncio.create_task(hold()) for _ in range(3)]
    await entered.wait()
    assert semaphore.locked()
    with pytest.raises(HTTPException) as exc_info:
        require_busy_lock()
    assert exc_info.value.status_code == 429
    release.set()
    await asyncio.gather(*tasks)
    assert not semaphore.locked()
    assert require_busy_lock() is semaphore


def test_browser_streaming_workers_do_not_overlap():
    session = BrowserSession(9222)
    state = {"active": 0, "max_active": 0}
    lock = threading.Lock()

    def fake_send(body, timeout_ms, queue, loop, cancel_event):
        del body, timeout_ms, cancel_event
        with lock:
            state["active"] += 1
            state["max_active"] = max(state["max_active"], state["active"])
        time.sleep(0.15)
        with lock:
            state["active"] -= 1
        loop.call_soon_threadsafe(queue.put_nowait, None)

    session._send_streaming_request_sync = fake_send

    async def consume():
        async for _event in session.send_streaming_request(body="{}", timeout_ms=1000):
            pass

    async def main():
        await asyncio.gather(consume(), consume(), consume())

    try:
        asyncio.run(main())
    finally:
        session._executor.shutdown(wait=True, cancel_futures=True)

    assert state["max_active"] == 1
    assert session._executor._max_workers == 1
