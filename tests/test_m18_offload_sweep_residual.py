"""Issue #115 (M18 offload sweep) -- the request-path blocking calls W3 left inline.

With ENABLE_SYNC_DB_OFFLOAD on, every request-path Supabase .execute() in the
sweep's residual set must run OFF the asyncio event loop (asyncio.to_thread via
app.utils.db_offload.run_db); with ENABLE_ASYNC_REDIS_OFFLOAD on, the residual
request-path Upstash commands (_is_token_revoked GET, usage counters) must too.
Both flags OFF must stay inline (thread identity == main) -- that is the
byte-identity substitute gate for this unit (the price-extraction corpus gate
does not cover these modules).

Assertion style copied from tests/test_m13_05_sync_db_offload.py: a monkeypatched
fake records threading.current_thread() inside the blocking primitive and the
test asserts thread identity, proving the property rather than spying on a call.

Sites covered (issue #115 table, restricted to this lane's files):
  1  auth_service.get_user_preferences                       (Supabase)
  2  scs._fetch_behavior_profile                             (Supabase)
  3  scs._update_behavior_profile                            (4x Supabase)
  4  scs._update_behavior_profile comparison_feedback bound  (.limit)
  5  database_service.log_search                             (Supabase)
  6  feedback_service.track_event                            (Supabase)
  8  product_data_service (static scan: no raw .execute())   (Supabase x6)
  9  auth_service._is_token_revoked (via verify_token)       (Redis)
  10 usage_service consume path (_atomic_consume + reads)    (Redis)
  14 all of the above inline when both flags are off

NOT covered here (out of this lane's file ownership -- see unit report):
  7  referral Loop 2 (blocking calls live in referral_service.py)
  11/12/13 review_service / api_budget_service sites.
"""
import threading
import types
from datetime import datetime, timezone
from pathlib import Path

import pytest

MAIN = threading.current_thread()

SYNC_FLAG = "ENABLE_SYNC_DB_OFFLOAD"
REDIS_FLAG = "ENABLE_ASYNC_REDIS_OFFLOAD"


def _del_flags(monkeypatch):
    monkeypatch.delenv(SYNC_FLAG, raising=False)
    monkeypatch.delenv(REDIS_FLAG, raising=False)


class _Resp:
    def __init__(self, data):
        self.data = data


class _RecordingQuery:
    """One chained Supabase query-builder stub; .execute() records the thread."""

    def __init__(self, table_name, seen, data):
        self._table = table_name
        self._seen = seen
        self._data = data

    def select(self, *a, **k):
        return self

    def insert(self, *a, **k):
        return self

    def upsert(self, *a, **k):
        return self

    def update(self, *a, **k):
        return self

    def eq(self, *a, **k):
        return self

    def order(self, *a, **k):
        return self

    def single(self):
        return self

    def limit(self, n):
        self._seen.setdefault("limits", {})[self._table] = n
        return self

    def execute(self):
        self._seen["calls"] += 1
        self._seen["threads"].append(threading.current_thread())
        self._seen.setdefault("tables", []).append(self._table)
        return _Resp(self._data.get(self._table))


class _RecordingClient:
    def __init__(self, seen, data):
        self._seen = seen
        self._data = data

    def table(self, name):
        return _RecordingQuery(name, self._seen, self._data)


def _seen():
    return {"calls": 0, "threads": []}


# ---------------------------------------------------------------------------
# Scenario runners -- each stubs the blocking primitive, drives the PUBLIC
# entry point, sanity-checks the result, and returns the recorded threads.
# Reused by the per-site flag-ON tests AND the parametrized flags-OFF gate.
# ---------------------------------------------------------------------------

async def _run_get_user_preferences(monkeypatch):
    from app.services import auth_service

    seen = _seen()
    data = {"users": {"preferences": {"budget": "mid"}, "preferences_completed": True}}
    monkeypatch.setattr(
        auth_service, "get_admin_client", lambda: _RecordingClient(seen, data)
    )
    result = await auth_service.get_user_preferences("u1")
    assert result["success"] is True
    assert result["preferences"] == {"budget": "mid"}
    seen["expected_calls"] = 1
    return seen


async def _run_fetch_behavior_profile(monkeypatch):
    from app.services import database_service
    from app.services.structured_comparison_service import get_comparison_service

    seen = _seen()
    data = {"users": {"behavior_profile": {"category_affinity": {}}}}
    monkeypatch.setattr(
        database_service, "get_supabase_client", lambda: _RecordingClient(seen, data)
    )
    svc = get_comparison_service()
    result = await svc._fetch_behavior_profile("u1")
    assert result == {"category_affinity": {}}
    seen["expected_calls"] = 1
    return seen


async def _run_update_behavior_profile(monkeypatch):
    from app.services import behavior_service, database_service
    from app.services.structured_comparison_service import get_comparison_service

    seen = _seen()
    data = {"comparisons": [], "comparison_feedback": [], "user_events": [], "users": []}
    monkeypatch.setattr(
        database_service, "get_supabase_client", lambda: _RecordingClient(seen, data)
    )

    class _FakeBehavior:
        async def build_behavior_profile(self, comparisons, feedback, events):
            return {"built": True}

    monkeypatch.setattr(
        behavior_service, "get_behavior_service", lambda: _FakeBehavior()
    )
    svc = get_comparison_service()
    await svc._update_behavior_profile("u1")
    assert seen["calls"] == 4, (
        f"expected the 3 selects + 1 update = 4 round trips, saw {seen['calls']} "
        f"on tables {seen.get('tables')}"
    )
    seen["expected_calls"] = 4
    return seen


async def _run_log_search(monkeypatch):
    from app.services import database_service

    seen = _seen()
    data = {"search_logs": [{"id": 1}]}
    monkeypatch.setattr(
        database_service, "get_supabase_client", lambda: _RecordingClient(seen, data)
    )
    await database_service.log_search(query="a vs b", input_type="text", user_id="u1")
    seen["expected_calls"] = 1
    return seen


async def _run_track_event(monkeypatch):
    from app.services import feedback_service

    seen = _seen()
    data = {"user_events": [{"id": "ev1"}]}
    monkeypatch.setattr(
        feedback_service, "get_supabase_client", lambda: _RecordingClient(seen, data)
    )
    result = await feedback_service.track_event(
        user_id="u1", event_type="comparison_completed", event_data={"k": 1},
    )
    assert result["success"] is True
    seen["expected_calls"] = 1
    return seen


async def _run_product_data_read(monkeypatch):
    from app.services import product_data_service as pds

    seen = _seen()
    data = {
        "product_specs": {
            "specs": {"size": "100ml"},
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }
    }
    monkeypatch.setattr(
        pds, "get_admin_supabase_client", lambda: _RecordingClient(seen, data)
    )
    result = await pds.get_cached_specs("key1")
    assert result == {"size": "100ml"}
    seen["expected_calls"] = 1
    return seen


async def _run_product_data_write(monkeypatch):
    from app.services import product_data_service as pds

    seen = _seen()
    data = {"product_prices": [{"id": 1}]}
    monkeypatch.setattr(
        pds, "get_admin_supabase_client", lambda: _RecordingClient(seen, data)
    )
    await pds.save_price(
        "key1", "Brand", "Name", None, "bahrain",
        {"amount": 1.0, "currency": "BHD", "retailer": "r", "url": "u",
         "source_method": "local_bhd", "estimated": False},
    )
    seen["expected_calls"] = 1
    return seen


async def _run_token_revocation(monkeypatch):
    from app.services import auth_service

    seen = _seen()

    def fake_revoked(token):
        seen["calls"] += 1
        seen["threads"].append(threading.current_thread())
        return False

    monkeypatch.setattr(auth_service, "_is_token_revoked", fake_revoked)

    class _Auth:
        @staticmethod
        def get_user(tok):
            return types.SimpleNamespace(
                user=types.SimpleNamespace(id="u1", email="e@x.com")
            )

    monkeypatch.setattr(
        auth_service, "get_auth_client",
        lambda: types.SimpleNamespace(auth=_Auth()),
    )
    result = await auth_service.verify_token("tok")
    assert result is not None and result["id"] == "u1"
    seen["expected_calls"] = 1
    return seen


async def _run_usage_consume(monkeypatch):
    from app.services import usage_service

    seen = _seen()

    async def fake_tier(user_id):
        return {
            "subscription_tier": "free",
            "lifetime_comparisons_used": 10,
            "referral_bonus_comparisons_this_month": 0,
        }

    async def fake_bonus(user_id):
        return 0

    def fake_atomic(user_id, daily_limit, monthly_cap):
        seen["calls"] += 1
        seen["threads"].append(threading.current_thread())
        return None  # consumed OK

    def fake_count(key):
        seen["calls"] += 1
        seen["threads"].append(threading.current_thread())
        return 0

    monkeypatch.setattr(usage_service, "_get_user_tier_info", fake_tier)
    monkeypatch.setattr(usage_service, "_get_active_referral_bonus", fake_bonus)
    monkeypatch.setattr(usage_service, "_atomic_consume", fake_atomic)
    monkeypatch.setattr(usage_service, "_get_redis_count", fake_count)

    result = await usage_service.consume_comparison_credit("u1", "tok")
    assert result["allowed"] is True and result["consumed"] is True
    # 1 atomic consume + 2 remaining-count reads on the success shape
    seen["expected_calls"] = 3
    return seen


SCENARIOS = {
    "get_user_preferences": (_run_get_user_preferences, SYNC_FLAG),
    "fetch_behavior_profile": (_run_fetch_behavior_profile, SYNC_FLAG),
    "update_behavior_profile": (_run_update_behavior_profile, SYNC_FLAG),
    "log_search": (_run_log_search, SYNC_FLAG),
    "track_event": (_run_track_event, SYNC_FLAG),
    "product_data_read": (_run_product_data_read, SYNC_FLAG),
    "product_data_write": (_run_product_data_write, SYNC_FLAG),
    "token_revocation": (_run_token_revocation, REDIS_FLAG),
    "usage_consume": (_run_usage_consume, REDIS_FLAG),
}


# ---------------------------------------------------------------------------
# Flag ON -- every site runs its blocking primitive OFF the main thread.
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.parametrize("name", list(SCENARIOS))
async def test_site_offloads_when_flag_on(name, monkeypatch):
    runner, flag = SCENARIOS[name]
    _del_flags(monkeypatch)
    monkeypatch.setenv(flag, "true")
    seen = await runner(monkeypatch)
    assert seen["calls"] == seen["expected_calls"]
    offenders = [t.name for t in seen["threads"] if t is MAIN]
    assert not offenders, (
        f"{name}: {len(offenders)} blocking call(s) ran ON the event-loop thread "
        f"with {flag}=true -- the offload is missing"
    )


# ---------------------------------------------------------------------------
# Test 14 -- the OFF-branch identity pin: both flags deleted, every site runs
# inline on the main thread, blocking stub called exactly the expected count.
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.parametrize("name", list(SCENARIOS))
async def test_all_new_sites_inline_when_flags_off(name, monkeypatch):
    runner, _flag = SCENARIOS[name]
    _del_flags(monkeypatch)
    seen = await runner(monkeypatch)
    assert seen["calls"] == seen["expected_calls"]
    off_main = [t.name for t in seen["threads"] if t is not MAIN]
    assert not off_main, (
        f"{name}: flag OFF must run inline on the event-loop thread "
        f"(byte-identical to base), but ran on {off_main}"
    )


# ---------------------------------------------------------------------------
# Test 4 -- the behaviour-profile comparison_feedback select is bounded.
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_behavior_profile_feedback_select_is_bounded(monkeypatch):
    _del_flags(monkeypatch)
    seen = await _run_update_behavior_profile(monkeypatch)
    limit = seen.get("limits", {}).get("comparison_feedback")
    assert isinstance(limit, int) and limit > 0, (
        "the comparison_feedback select must carry a positive .limit() like its "
        f"comparisons(50)/user_events(200) siblings -- saw {limit!r}"
    )


# ---------------------------------------------------------------------------
# Test 8 -- static scan: product_data_service has no raw .execute() left.
# Style precedent: tests/test_migration_index_predicate_immutability.py.
# ---------------------------------------------------------------------------

def test_product_data_service_has_no_raw_execute_on_request_path():
    path = Path(__file__).resolve().parents[1] / "app" / "services" / "product_data_service.py"
    src = path.read_text(encoding="utf-8")
    unwrapped = [
        f"line {i}: {line.strip()}"
        for i, line in enumerate(src.splitlines(), start=1)
        if ".execute()" in line and "run_db(" not in line
    ]
    assert unwrapped == [], (
        "raw blocking .execute() call(s) outside run_db() in product_data_service:\n"
        + "\n".join(unwrapped)
    )


# ---------------------------------------------------------------------------
# Test 9b -- fail-open invariant: Redis down never blocks auth, either flag
# state. Must be GREEN before AND after this unit.
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.parametrize("flag_on", [False, True])
async def test_is_token_revoked_still_fail_open_on_redis_error(flag_on, monkeypatch):
    from app.services import auth_service, cache_service

    _del_flags(monkeypatch)
    if flag_on:
        monkeypatch.setenv(REDIS_FLAG, "true")

    class _BadRedis:
        def get(self, key):
            raise RuntimeError("redis down")

    monkeypatch.setattr(cache_service, "redis_client", _BadRedis())

    class _Auth:
        @staticmethod
        def get_user(tok):
            return types.SimpleNamespace(
                user=types.SimpleNamespace(id="u1", email="e@x.com")
            )

    monkeypatch.setattr(
        auth_service, "get_auth_client",
        lambda: types.SimpleNamespace(auth=_Auth()),
    )
    result = await auth_service.verify_token("tok")
    assert result is not None and result["id"] == "u1", (
        "a Redis failure in the revocation check must FAIL OPEN (token accepted)"
    )


# ---------------------------------------------------------------------------
# Test 10b -- _atomic_consume rollback ordering unchanged: on a monthly
# overflow the decrements are monthly THEN daily. Must stay GREEN throughout.
# ---------------------------------------------------------------------------

def test_atomic_consume_rollback_order_unchanged(monkeypatch):
    from app.services import usage_service

    class _FakeRedis:
        def __init__(self):
            self.ops = []

        def incrby(self, key, n):
            self.ops.append(("incrby", key))
            return 100 if ":monthly:" in key else 2

        def decrby(self, key, n):
            self.ops.append(("decrby", key))

        def expire(self, key, ttl):
            pass

    fake = _FakeRedis()
    monkeypatch.setattr(usage_service, "redis_client", fake)
    reason = usage_service._atomic_consume("u1", daily_limit=10, monthly_cap=50)
    assert reason == "monthly_limit"
    decrs = [key for op, key in fake.ops if op == "decrby"]
    assert len(decrs) == 2
    assert ":monthly:" in decrs[0], "monthly rollback must come FIRST"
    assert ":daily:" in decrs[1], "daily rollback must come SECOND"
