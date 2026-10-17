"""Generation concurrency: three upstream XHRs, one Playwright thread."""

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


class FakeStreamPage:
    """Page double whose XHRs progress outside the browser thread."""

    def __init__(self, *, hold_after_first: bool = False, silent: bool = False):
        self.hold_after_first = hold_after_first
        self.silent = silent
        self.lock = threading.Lock()
        self.streams: dict[str, dict] = {}
        self.starts: list[str] = []
        self.aborts: list[str] = []
        self.in_flight = 0
        self.completed = 0
        self.saw_three_before_any_finished = False
        self.started_all = threading.Event()
        self.release_rest = threading.Event()
        self.by_body: dict[str, str] = {}
        self.chunks_pushed = 0

    def evaluate(self, script, arg):
        if isinstance(arg, dict):
            return self._start(arg)
        if "__stream_abort" in script:
            return self._abort(arg)
        if "__stream_poll" in script:
            return self._poll(arg)
        raise AssertionError(script)

    def _start(self, arg):
        rid = arg["rid"]
        body = arg["body"]
        with self.lock:
            self.streams[rid] = {"body": body, "events": []}
            self.starts.append(body)
            self.by_body[body] = rid
            self.in_flight += 1
            if len(self.starts) == 3 and self.completed == 0 and self.in_flight == 3:
                self.saw_three_before_any_finished = True
            if len(self.starts) >= 3:
                self.started_all.set()
        if not self.silent:
            threading.Thread(target=self._produce, args=(rid, body), daemon=True).start()
        return None

    def _produce(self, rid, body):
        if not self.started_all.wait(2):
            return
        self._push(rid, {"type": "status", "status": 200})
        self._push(rid, {"type": "chunk", "text": f"{body}-1"})
        if self.hold_after_first:
            if not self.release_rest.wait(2):
                return
        self._push(rid, {"type": "chunk", "text": f"{body}-2"})
        with self.lock:
            stream = self.streams.get(rid)
            if stream is None:
                return
            stream["events"].append({"type": "done"})
            self.completed += 1
            self.in_flight -= 1

    def _push(self, rid, event):
        with self.lock:
            stream = self.streams.get(rid)
            if stream is not None:
                stream["events"].append(event)
                if event.get("type") == "chunk":
                    self.chunks_pushed += 1

    def _poll(self, rid):
        with self.lock:
            stream = self.streams.get(rid)
            if stream is None:
                return {"type": "missing"}
            if stream["events"]:
                return stream["events"].pop(0)
            return {"type": "idle"}

    def _abort(self, rid):
        with self.lock:
            self.aborts.append(rid)
            stream = self.streams.pop(rid, None)
            if stream is not None:
                self.in_flight -= 1
        return None


def _bind_page(session: BrowserSession, page: FakeStreamPage) -> None:
    session._prepare_streaming_sync = lambda: (
        page,
        "https://example.test/generate",
        {"Content-Type": "application/json"},
    )


async def _collect(
    session: BrowserSession,
    body: str,
    timeout_ms: int = 2000,
    *,
    stop_after_first_chunk: bool = False,
):
    chunks: list[str] = []
    async for kind, payload in session.send_streaming_request(body=body, timeout_ms=timeout_ms):
        if kind == "chunk":
            chunks.append(payload.decode())
            if stop_after_first_chunk:
                break
    return chunks


def test_three_streams_start_upstream_before_any_finishes_and_do_not_cross():
    session = BrowserSession(9222)
    page = FakeStreamPage()
    _bind_page(session, page)

    async def main():
        return await asyncio.wait_for(
            asyncio.gather(_collect(session, "A"), _collect(session, "B"), _collect(session, "C")),
            timeout=3,
        )

    try:
        results = asyncio.run(main())
    finally:
        session._executor.shutdown(wait=True, cancel_futures=True)

    assert session._executor._max_workers == 1
    assert page.saw_three_before_any_finished
    assert sorted(results) == [["A-1", "A-2"], ["B-1", "B-2"], ["C-1", "C-2"]]


def test_cancel_one_stream_leaves_the_other_two_running():
    session = BrowserSession(9222)
    page = FakeStreamPage(hold_after_first=True)
    _bind_page(session, page)

    async def consume(body: str) -> list[str]:
        chunks: list[str] = []
        async for kind, payload in session.send_streaming_request(body=body, timeout_ms=2000):
            if kind == "chunk":
                chunks.append(payload.decode())
        return chunks

    async def main():
        task_b = asyncio.create_task(consume("B"))
        task_a = asyncio.create_task(consume("A"))
        task_c = asyncio.create_task(consume("C"))
        for _ in range(100):
            if page.saw_three_before_any_finished and page.chunks_pushed >= 3:
                break
            await asyncio.sleep(0.01)
        else:
            raise AssertionError("the three upstream requests did not emit their first chunks")
        await asyncio.sleep(0.08)
        task_b.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task_b
        for _ in range(50):
            if page.by_body["B"] in page.aborts:
                break
            await asyncio.sleep(0.01)
        assert page.by_body["B"] in page.aborts
        assert page.by_body["A"] not in page.aborts
        assert page.by_body["C"] not in page.aborts
        assert page.in_flight == 2
        page.release_rest.set()
        return await asyncio.wait_for(asyncio.gather(task_a, task_c), timeout=3)

    try:
        chunks_a, chunks_c = asyncio.run(main())
    finally:
        session._executor.shutdown(wait=True, cancel_futures=True)

    assert chunks_a == ["A-1", "A-2"]
    assert chunks_c == ["C-1", "C-2"]


def test_stream_timeout_releases_the_concurrency_slot():
    session = BrowserSession(9222)
    page = FakeStreamPage(silent=True)
    _bind_page(session, page)
    semaphore = asyncio.Semaphore(1)

    async def main():
        async with semaphore:
            with pytest.raises(RuntimeError, match="no response status"):
                async for _event in session.send_streaming_request(body="hang", timeout_ms=200):
                    pass
        assert not semaphore.locked()
        await asyncio.wait_for(semaphore.acquire(), timeout=0.2)

    try:
        asyncio.run(main())
    finally:
        session._executor.shutdown(wait=True, cancel_futures=True)

    assert page.by_body["hang"] in page.aborts
