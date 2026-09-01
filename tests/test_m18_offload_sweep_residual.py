"""#115 (M18 LS-event-loop-02) — finish the W3 offload sweep for the request-path
blocking calls M13-05/M13-06 deferred.

Every test copies the M13-05/M13-06 assertion style: capture
`threading.current_thread()` inside a monkeypatched fake and assert thread
identity — `is not main` when the flag is ON, `is main` when OFF. That proves
the *property* (the blocking call left the event loop) rather than spying on
`asyncio.to_thread`.

Flags reused (NOT new): ENABLE_SYNC_DB_OFFLOAD for Supabase `.execute()`,
ENABLE_ASYNC_REDIS_OFFLOAD for Upstash commands. Both default OFF; the OFF
branches here are the byte-identity pins for this unit (the corpus byte-identity
gate does not apply — none of the touched modules is on the CLAUDE.md:357
extraction-path list).

All tests are free-tier: no network, no credentials, no live services.
"""
from __future__ import annotations

import re
import threading
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

SENTINEL = object()


class _Resp:
    def __init__(self, data=None, count=None):
        self.data = data
        self.count = count


class _RecordingQuery:
    """Chainable supabase query stub: every builder method returns self;
    `.execute()` records the calling thread (and the method trail)."""

    def __init__(self, record: dict, key: str, data=None, count=None):
        self._record = record
        self._key = key
        self._data = data
        self._count = count
        self.calls: list = []

    def __getattr__(self, name):
        def _method(*args, **kwargs):
            self.calls.append((name, args))
            self._record.setdefault("methods", []).append((self._key, name, args))
            return self

        return _method

    def execute(self):
        self._record.setdefault("threads", []).append(
            (self._key, threading.current_thread())
        )
        return _Resp(data=self._data, count=self._count)


class _RecordingClient:
    def __init__(self, record: dict, table_data: dict | None = None):
        self._record = record
        self._table_data = table_data or {}

    def table(self, name):
        return _RecordingQuery(self._record, name, data=self._table_data.get(name))


def _threads(record: dict) -> list:
    return [t for _, t in record.get("threads", [])]


# ---------------------------------------------------------------------------
# 1. auth_service.get_user_preferences — 1x Supabase on all three compare routes
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("flag_on", [True, False])
async def test_get_user_preferences_offload_dispatch(monkeypatch, flag_on):
    from app.services import auth_service as au

    if flag_on:
        monkeypatch.setenv("ENABLE_SYNC_DB_OFFLOAD", "true")
    else:
        monkeypatch.delenv("ENABLE_SYNC_DB_OFFLOAD", raising=False)
    main = threading.current_thread()

    record: dict = {}
    client = _RecordingClient(
        record, {"users": {"preferences": {"a": 1}, "preferences_completed": True}}
    )
    monkeypatch.setattr(au, "get_admin_client", lambda: client)

    result = await au.get_user_preferences("u1")
    assert result["success"] is True
    assert result["preferences"] == {"a": 1}
    threads = _threads(record)
    assert len(threads) == 1
    if flag_on:
        assert threads[0] is not main, "flag ON must offload the users SELECT"
    else:
        assert threads[0] is main, "flag OFF must stay inline (byte-identical)"


# ---------------------------------------------------------------------------
# 2/3/4. structured_comparison_service behaviour-profile chain
# ---------------------------------------------------------------------------


def _make_scs():
    from app.services.structured_comparison_service import StructuredComparisonService

    return StructuredComparisonService()


@pytest.mark.asyncio
@pytest.mark.parametrize("flag_on", [True, False])
async def test_fetch_behavior_profile_offload_dispatch(monkeypatch, flag_on):
    from app.services import database_service as ds

    if flag_on:
        monkeypatch.setenv("ENABLE_SYNC_DB_OFFLOAD", "true")
    else:
        monkeypatch.delenv("ENABLE_SYNC_DB_OFFLOAD", raising=False)
    main = threading.current_thread()

    record: dict = {}
    client = _RecordingClient(record, {"users": {"behavior_profile": {"x": 1}}})
    monkeypatch.setattr(ds, "get_supabase_client", lambda: client)

    svc = _make_scs()
    profile = await svc._fetch_behavior_profile("u1")
    assert profile == {"x": 1}
    threads = _threads(record)
    assert len(threads) == 1
    if flag_on:
        assert threads[0] is not main
    else:
        assert threads[0] is main


@pytest.mark.asyncio
async def test_update_behavior_profile_offloads_all_four_executes(monkeypatch):
    from app.services import database_service as ds
    from app.services import behavior_service as bs

    monkeypatch.setenv("ENABLE_SYNC_DB_OFFLOAD", "true")
    main = threading.current_thread()

    record: dict = {}
    client = _RecordingClient(record, {})

    class _FakeBehavior:
        async def build_behavior_profile(self, comparisons, feedback, events):
            return {"built": True}

    monkeypatch.setattr(ds, "get_supabase_client", lambda: client)
    monkeypatch.setattr(bs, "get_behavior_service", lambda: _FakeBehavior())

    svc = _make_scs()
    await svc._update_behavior_profile("u1")

    threads = _threads(record)
    assert len(threads) == 4, (
        f"expected 4 .execute() round trips (comparisons/feedback/events/update), "
        f"got {len(threads)}: {[k for k, _ in record.get('threads', [])]}"
    )
    for key, t in record["threads"]:
        assert t is not main, f"{key} .execute() ran on the event-loop thread"


@pytest.mark.asyncio
async def test_update_behavior_profile_feedback_select_is_bounded(monkeypatch):
    """The comparison_feedback select must carry a positive .limit() like its
    50/200-limited siblings — it was the one unbounded read in the chain."""
    from app.services import database_service as ds
    from app.services import behavior_service as bs

    monkeypatch.delenv("ENABLE_SYNC_DB_OFFLOAD", raising=False)

    record: dict = {}
    client = _RecordingClient(record, {})

    class _FakeBehavior:
        async def build_behavior_profile(self, comparisons, feedback, events):
            return {}

    monkeypatch.setattr(ds, "get_supabase_client", lambda: client)
    monkeypatch.setattr(bs, "get_behavior_service", lambda: _FakeBehavior())

    svc = _make_scs()
    await svc._update_behavior_profile("u1")

    feedback_limits = [
        args
        for key, name, args in record.get("methods", [])
        if key == "comparison_feedback" and name == "limit"
    ]
    assert feedback_limits, "comparison_feedback select has no .limit() — unbounded"
    assert isinstance(feedback_limits[0][0], int) and feedback_limits[0][0] > 0


# ---------------------------------------------------------------------------
# _persist_genuine_price — the Redis set_cached write W3 deferred
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("flag_on", [True, False])
async def test_persist_genuine_price_cache_write_offload_dispatch(monkeypatch, flag_on):
    import app.services.structured_comparison_service as scs

    if flag_on:
        monkeypatch.setenv("ENABLE_ASYNC_REDIS_OFFLOAD", "true")
    else:
        monkeypatch.delenv("ENABLE_ASYNC_REDIS_OFFLOAD", raising=False)
    main = threading.current_thread()
    seen = {}

    def fake_set_cached(key, value, ttl):
        seen["thread"] = threading.current_thread()
        return True

    monkeypatch.setattr(scs, "set_cached", fake_set_cached)
    monkeypatch.setattr(scs, "should_cache_price", lambda *a, **k: True)

    svc = _make_scs()
    monkeypatch.setattr(svc, "_save_price_to_db", lambda *a, **k: None)

    await svc._persist_genuine_price(
        "k", {"amount": 1.0, "currency": "BHD"}, "b", "n", None, "bahrain", "b n", "other"
    )
    assert "thread" in seen, "set_cached was never called"
    if flag_on:
        assert seen["thread"] is not main
    else:
        assert seen["thread"] is main


# ---------------------------------------------------------------------------
# 5. database_service.log_search — highest-frequency request-path write #1
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("flag_on", [True, False])
async def test_log_search_offload_dispatch(monkeypatch, flag_on):
    from app.services import database_service as ds

    if flag_on:
        monkeypatch.setenv("ENABLE_SYNC_DB_OFFLOAD", "true")
    else:
        monkeypatch.delenv("ENABLE_SYNC_DB_OFFLOAD", raising=False)
    main = threading.current_thread()

    record: dict = {}
    client = _RecordingClient(record, {})
    monkeypatch.setattr(ds, "get_supabase_client", lambda: client)

    await ds.log_search(query="q", user_id="u1")
    threads = _threads(record)
    assert len(threads) == 1
    if flag_on:
        assert threads[0] is not main
    else:
        assert threads[0] is main


# ---------------------------------------------------------------------------
# 6. feedback_service.track_event — highest-frequency request-path write #2
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("flag_on", [True, False])
async def test_track_event_offload_dispatch(monkeypatch, flag_on):
    from app.services import feedback_service as fs

    if flag_on:
        monkeypatch.setenv("ENABLE_SYNC_DB_OFFLOAD", "true")
    else:
        monkeypatch.delenv("ENABLE_SYNC_DB_OFFLOAD", raising=False)
    main = threading.current_thread()

    record: dict = {}
    client = _RecordingClient(record, {"user_events": [{"id": "e1"}]})
    monkeypatch.setattr(fs, "get_supabase_client", lambda: client)

    result = await fs.track_event(user_id="u1", event_type="t", event_data={})
    assert result["success"] is True
    threads = _threads(record)
    assert len(threads) == 1
    if flag_on:
        assert threads[0] is not main
    else:
        assert threads[0] is main


# ---------------------------------------------------------------------------
# 7. referral Loop 2 entry queries (fire inside save_comparison_and_track_cohort)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("flag_on", [True, False])
async def test_loop2_entry_queries_offload_dispatch(monkeypatch, flag_on):
    from app.services import referral_service as rs

    if flag_on:
        monkeypatch.setenv("ENABLE_SYNC_DB_OFFLOAD", "true")
    else:
        monkeypatch.delenv("ENABLE_SYNC_DB_OFFLOAD", raising=False)
    main = threading.current_thread()

    record: dict = {}
    client = _RecordingClient(record, {"referral_invites": [], "comparisons": []})
    monkeypatch.setattr(rs, "get_admin_supabase_client", lambda: client)

    svc = rs.ReferralService()
    invite = await svc._find_unredeemed_invite_for_invitee("u1")
    assert invite is None
    count = await svc._count_user_comparisons("u1")
    assert count == 0

    threads = _threads(record)
    assert len(threads) == 2
    for key, t in record["threads"]:
        if flag_on:
            assert t is not main, f"{key} query ran on the event-loop thread"
        else:
            assert t is main, f"{key} query left the loop with the flag OFF"


# ---------------------------------------------------------------------------
# 8. product_data_service — static scan: zero raw .execute() outside run_db
# ---------------------------------------------------------------------------


def test_product_data_service_has_no_raw_execute_on_request_path():
    src = (REPO_ROOT / "app" / "services" / "product_data_service.py").read_text(
        encoding="utf-8"
    )
    execute_count = src.count(".execute()")
    wrapped_count = len(re.findall(r"run_db\(\s*lambda", src))
    assert execute_count > 0, "sanity: the L2 cache should still call .execute()"
    assert wrapped_count == execute_count, (
        f"product_data_service has {execute_count - wrapped_count} raw .execute() "
        f"call(s) not routed through run_db ({execute_count} total, "
        f"{wrapped_count} wrapped)"
    )


# ---------------------------------------------------------------------------
# 9. auth_service._is_token_revoked — Redis GET on every authed request
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("flag_on", [True, False])
async def test_is_token_revoked_async_dispatch(monkeypatch, flag_on):
    from app.services import auth_service as au

    if flag_on:
        monkeypatch.setenv("ENABLE_ASYNC_REDIS_OFFLOAD", "true")
    else:
        monkeypatch.delenv("ENABLE_ASYNC_REDIS_OFFLOAD", raising=False)
    main = threading.current_thread()
    seen = {}

    def fake_revoked(token):
        seen["thread"] = threading.current_thread()
        return False

    monkeypatch.setattr(au, "_is_token_revoked", fake_revoked)

    result = await au._is_token_revoked_async("tok")
    assert result is False
    if flag_on:
        assert seen["thread"] is not main
    else:
        assert seen["thread"] is main


@pytest.mark.asyncio
async def test_is_token_revoked_still_fail_open_on_redis_error(monkeypatch):
    """Must stay GREEN throughout: Redis down => False (fail-open), no raise."""
    import app.services.cache_service as cache_service
    from app.services import auth_service as au

    monkeypatch.setenv("ENABLE_ASYNC_REDIS_OFFLOAD", "true")
    broken = MagicMock()
    broken.get.side_effect = RuntimeError("redis down")
    monkeypatch.setattr(cache_service, "redis_client", broken)

    assert await au._is_token_revoked_async("tok") is False


def test_verify_token_routes_through_async_revocation_dispatch():
    """Wiring pin: verify_token must await the dispatch, not call the sync
    helper inline on the loop."""
    src = (REPO_ROOT / "app" / "services" / "auth_service.py").read_text(
        encoding="utf-8"
    )
    m = re.search(r"async def verify_token.*?(?=\nasync def |\ndef )", src, re.S)
    assert m, "verify_token not found"
    body = m.group(0)
    assert "_is_token_revoked_async(" in body
    assert not re.search(r"(?<!def )(?<!async )\b_is_token_revoked\(", body), (
        "verify_token still calls the sync _is_token_revoked inline"
    )


# ---------------------------------------------------------------------------
# 10. usage_service — atomic consume + remaining-count reads
# ---------------------------------------------------------------------------


def _stub_usage_tier(monkeypatch, us):
    monkeypatch.setattr(
        us,
        "_get_user_tier_info",
        AsyncMock(
            return_value={
                "subscription_tier": "free",
                "lifetime_comparisons_used": 99,
                "referral_bonus_comparisons_this_month": 0,
            }
        ),
    )
    monkeypatch.setattr(us, "_get_active_referral_bonus", AsyncMock(return_value=0))


@pytest.mark.asyncio
@pytest.mark.parametrize("flag_on", [True, False])
async def test_usage_atomic_consume_and_counts_offload_dispatch(monkeypatch, flag_on):
    from app.services import usage_service as us

    if flag_on:
        monkeypatch.setenv("ENABLE_ASYNC_REDIS_OFFLOAD", "true")
    else:
        monkeypatch.delenv("ENABLE_ASYNC_REDIS_OFFLOAD", raising=False)
    main = threading.current_thread()
    _stub_usage_tier(monkeypatch, us)

    consume_seen = {}
    count_threads = []

    def fake_atomic_consume(user_id, daily, monthly):
        consume_seen["thread"] = threading.current_thread()
        return None

    def fake_get_redis_count(key):
        count_threads.append(threading.current_thread())
        return 0

    monkeypatch.setattr(us, "_atomic_consume", fake_atomic_consume)
    monkeypatch.setattr(us, "_get_redis_count", fake_get_redis_count)

    result = await us.consume_comparison_credit("u1", "tok")
    assert result["allowed"] is True
    assert result["consumed"] is True
    assert "thread" in consume_seen
    assert count_threads, "remaining-count reads never ran"
    if flag_on:
        assert consume_seen["thread"] is not main
        for t in count_threads:
            assert t is not main
    else:
        assert consume_seen["thread"] is main
        for t in count_threads:
            assert t is main


@pytest.mark.asyncio
async def test_atomic_consume_rollback_order_unchanged(monkeypatch):
    """Must stay GREEN: monthly overflow rolls back monthly THEN daily."""
    from app.services import usage_service as us

    monkeypatch.delenv("ENABLE_ASYNC_REDIS_OFFLOAD", raising=False)
    decrs = []

    fake = MagicMock()
    fake.incrby.side_effect = [1, 100]  # daily ok (1), monthly overflow (100)
    fake.decrby.side_effect = lambda key, n: decrs.append(key)
    fake.expire.return_value = True
    monkeypatch.setattr(us, "redis_client", fake)

    reason = us._atomic_consume("u1", daily_limit=3, monthly_cap=10)
    assert reason == "monthly_limit"
    assert len(decrs) == 2
    assert decrs[0] == us._monthly_key("u1"), "monthly must be rolled back first"
    assert decrs[1] == us._daily_key("u1"), "daily must be rolled back second"


# ---------------------------------------------------------------------------
# 11. review_service.has_budget — 2x Redis on the reviews path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("flag_on", [True, False])
async def test_review_has_budget_async_dispatch(monkeypatch, flag_on):
    from app.services import review_service as rv

    if flag_on:
        monkeypatch.setenv("ENABLE_ASYNC_REDIS_OFFLOAD", "true")
    else:
        monkeypatch.delenv("ENABLE_ASYNC_REDIS_OFFLOAD", raising=False)
    main = threading.current_thread()
    seen = {}

    def fake_has_budget(provider):
        seen["thread"] = threading.current_thread()
        return False

    monkeypatch.setattr(rv, "has_budget", fake_has_budget)

    result = await rv._has_budget_async("serper")
    assert result is False
    if flag_on:
        assert seen["thread"] is not main
    else:
        assert seen["thread"] is main


def test_review_service_call_sites_use_async_dispatch():
    src = (REPO_ROOT / "app" / "services" / "review_service.py").read_text(
        encoding="utf-8"
    )
    raw_calls = re.findall(r"(?m)^\s*if not has_budget\(", src)
    assert raw_calls == [], (
        f"review_service still has {len(raw_calls)} inline has_budget() gate(s)"
    )
    assert src.count("_has_budget_async(") >= 3  # def + 2 call sites


# ---------------------------------------------------------------------------
# 12. serper record_usage — 1x Redis per Serper 200, inline in async fns
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("flag_on", [True, False])
async def test_serper_record_usage_async_dispatch(monkeypatch, flag_on):
    from app.services import serper_service as sp

    if flag_on:
        monkeypatch.setenv("ENABLE_ASYNC_REDIS_OFFLOAD", "true")
    else:
        monkeypatch.delenv("ENABLE_ASYNC_REDIS_OFFLOAD", raising=False)
    main = threading.current_thread()
    seen = {}

    def fake_record_usage(provider):
        seen["thread"] = threading.current_thread()
        seen["provider"] = provider

    monkeypatch.setattr(sp, "record_usage", fake_record_usage)

    await sp._record_usage_async("serper")
    assert seen["provider"] == "serper"
    if flag_on:
        assert seen["thread"] is not main
    else:
        assert seen["thread"] is main


def test_serper_service_has_no_inline_record_usage_calls():
    src = (REPO_ROOT / "app" / "services" / "serper_service.py").read_text(
        encoding="utf-8"
    )
    inline = re.findall(r'(?m)^\s*record_usage\("serper"\)', src)
    assert inline == [], (
        f"{len(inline)} inline record_usage() call(s) still block the loop"
    )
    assert "await _record_usage_async(" in src


# ---------------------------------------------------------------------------
# usage_service._maybe_reset_referral_bonus — deferred by W3, named in CLAUDE.md
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("flag_on", [True, False])
async def test_maybe_reset_referral_bonus_offload_dispatch(monkeypatch, flag_on):
    from app.services import usage_service as us

    if flag_on:
        monkeypatch.setenv("ENABLE_SYNC_DB_OFFLOAD", "true")
    else:
        monkeypatch.delenv("ENABLE_SYNC_DB_OFFLOAD", raising=False)
    main = threading.current_thread()

    record: dict = {}
    client = _RecordingClient(
        record,
        {
            "users": {
                "subscription_tier": "free",
                "lifetime_comparisons_used": 0,
                "referral_bonus_comparisons_this_month": 5,
                "referral_bonus_reset_at": "2020-01-01T00:00:00+00:00",
            }
        },
    )
    monkeypatch.setattr(us, "get_admin_supabase_client", lambda: client)

    info = await us._get_user_tier_info("u1")
    assert info["referral_bonus_comparisons_this_month"] == 0

    # Two executes: the tier SELECT (already W3-wrapped) + the lazy-reset UPDATE.
    threads = _threads(record)
    assert len(threads) == 2, f"expected SELECT + reset UPDATE, got {len(threads)}"
    for key, t in record["threads"]:
        if flag_on:
            assert t is not main, f"{key} .execute() ran on the event-loop thread"
        else:
            assert t is main
