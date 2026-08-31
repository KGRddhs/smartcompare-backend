"""M13-05 pin — ENABLE_SYNC_DB_OFFLOAD moves the request-path hot set of blocking
Supabase calls off the event loop; flag OFF runs them inline (byte-identical).

Failure scenario: the sync supabase client blocks the single-worker event loop for
a full RTT inside async def, so one user's DB round trip stalls every other
coroutine and converts directly into wall-clock hard-cap timeouts for unrelated
requests. run_db offloads via asyncio.to_thread when the flag is ON.
"""
import threading

import pytest

from app.utils import db_offload
from app.utils.db_offload import run_db


@pytest.mark.asyncio
async def test_run_db_offloads_off_the_loop_when_flag_on(monkeypatch):
    monkeypatch.setenv("ENABLE_SYNC_DB_OFFLOAD", "true")
    main = threading.current_thread()
    seen = {}

    def call():
        seen["thread"] = threading.current_thread()
        return "RESULT"

    result = await run_db(call)
    assert result == "RESULT"
    assert seen["thread"] is not main, "flag ON must run the blocking call off-loop"


@pytest.mark.asyncio
async def test_run_db_inline_when_flag_off(monkeypatch):
    monkeypatch.delenv("ENABLE_SYNC_DB_OFFLOAD", raising=False)
    main = threading.current_thread()
    seen = {}

    def call():
        seen["thread"] = threading.current_thread()
        return "RESULT"

    result = await run_db(call)
    assert result == "RESULT"
    assert seen["thread"] is main, "flag OFF must run inline (byte-identical to today)"


@pytest.mark.asyncio
async def test_get_user_by_id_uses_to_thread_when_flag_on(monkeypatch):
    """A named hot-set function routes its .execute() through asyncio.to_thread."""
    monkeypatch.setenv("ENABLE_SYNC_DB_OFFLOAD", "true")

    from app.services import database_service as ds

    class _Resp:
        data = {"id": "u1"}

    class _Q:
        def select(self, *a, **k): return self
        def eq(self, *a, **k): return self
        def single(self): return self
        def execute(self): return _Resp()

    class _Client:
        def table(self, *a, **k): return _Q()

    monkeypatch.setattr(ds, "get_supabase_client", lambda: _Client())

    to_thread_calls = {"n": 0}
    real_to_thread = db_offload.asyncio.to_thread

    async def spy_to_thread(fn, *a, **k):
        to_thread_calls["n"] += 1
        return await real_to_thread(fn, *a, **k)
    monkeypatch.setattr(db_offload.asyncio, "to_thread", spy_to_thread)

    result = await ds.get_user_by_id("u1")
    assert result == {"id": "u1"}
    assert to_thread_calls["n"] == 1, "get_user_by_id did not offload via to_thread"


@pytest.mark.asyncio
async def test_get_user_by_id_no_to_thread_when_flag_off(monkeypatch):
    monkeypatch.delenv("ENABLE_SYNC_DB_OFFLOAD", raising=False)

    from app.services import database_service as ds

    class _Resp:
        data = {"id": "u1"}

    class _Q:
        def select(self, *a, **k): return self
        def eq(self, *a, **k): return self
        def single(self): return self
        def execute(self): return _Resp()

    class _Client:
        def table(self, *a, **k): return _Q()

    monkeypatch.setattr(ds, "get_supabase_client", lambda: _Client())

    to_thread_calls = {"n": 0}
    real_to_thread = db_offload.asyncio.to_thread

    async def spy_to_thread(fn, *a, **k):
        to_thread_calls["n"] += 1
        return await real_to_thread(fn, *a, **k)
    monkeypatch.setattr(db_offload.asyncio, "to_thread", spy_to_thread)

    result = await ds.get_user_by_id("u1")
    assert result == {"id": "u1"}
    assert to_thread_calls["n"] == 0, "flag OFF must call inline, not via to_thread"
