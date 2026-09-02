"""M18 usage-symmetry pins (CD-interactions-05, CD-interactions-07,
CD-wave-diffs-09, LS-event-loop-03) - property-tests for the consume/refund pair
in app/services/usage_service.py.

Three defects pinned here:
1. ANON TOCTOU (CD-interactions-05): check_anon_usage_allowed READ the
   anon:{fp} counters and record_anon_comparison INCREMENTED them later
   fire-and-forget, so N parallel same-fingerprint requests all passed - the
   exact race M13-37 closed for authenticated users via _atomic_consume in the
   SAME file. The gate must consume atomically.
2. REFUND WINDOW ASYMMETRY (CD-interactions-07 / CD-wave-diffs-09): the daily/
   monthly keys embed the CURRENT UTC date at call time, and the refund
   recomputed them AT REFUND TIME - a consume just before UTC midnight refunded
   just after decremented the NEW day's key to -1 (no TTL until a later
   INCRBY returns exactly 1), leaving the burned credit in the old window and
   minting a phantom credit (and a leaked key) in the new one. A refund must
   credit back the SAME window the consume debited, and must never drive a
   counter negative.
3. REDUNDANT SERIAL ROUND TRIPS (LS-event-loop-03): the gate re-READ both
   counters after the atomic consume even though the INCRBY return values ARE
   those counts, and fetched the two independent Supabase reads (tier info,
   referral bonus) strictly serially.

No `hypothesis` in the dev lock, so the property test is a seeded random walk
(deterministic, parametrized over seeds) instead of a Hypothesis strategy.
"""
import asyncio
import random
from datetime import datetime, timedelta, timezone

import pytest

from app.services import usage_service as us


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class FakeRedis:
    """Single-threaded atomic counter fake (mirrors tests/test_m13_37).

    Additionally counts get() calls (LS-event-loop-03: the redundant
    remaining-count GETs must be gone) and records expire() TTLs (the stray-key
    leak in CD-wave-diffs-09 must not recur without a TTL).
    """

    def __init__(self, raise_on_incr_keys=()):
        self.store = {}
        self.ttls = {}
        self.get_calls = 0
        self.raise_on_incr_keys = set(raise_on_incr_keys)

    def incrby(self, key, n):
        if key in self.raise_on_incr_keys:
            raise ConnectionError(f"injected incrby failure for {key}")
        self.store[key] = int(self.store.get(key, 0)) + n
        return self.store[key]

    # record_anon_comparison historically used incr(); route through incrby.
    def incr(self, key):
        return self.incrby(key, 1)

    def decrby(self, key, n):
        self.store[key] = int(self.store.get(key, 0)) - n
        return self.store[key]

    def expire(self, key, ttl):
        self.ttls[key] = ttl
        return True

    def get(self, key):
        self.get_calls += 1
        v = self.store.get(key)
        return str(v) if v is not None else None


class FakeDatetime:
    """Stands in for usage_service.datetime - controllable now()."""

    current = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)

    @classmethod
    def now(cls, tz=None):
        return cls.current


def _freeze(monkeypatch, dt):
    FakeDatetime.current = dt
    monkeypatch.setattr(us, "datetime", FakeDatetime)


def _stub_tier(monkeypatch, tier="free", lifetime_used=99, bonus=0):
    async def _tier(uid):
        return {"subscription_tier": tier, "lifetime_comparisons_used": lifetime_used}

    async def _bonus(uid):
        return bonus

    monkeypatch.setattr(us, "_get_user_tier_info", _tier)
    monkeypatch.setattr(us, "_get_active_referral_bonus", _bonus)


# ---------------------------------------------------------------------------
# 1. CD-interactions-05 - the anonymous gate must consume atomically
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_anon_gate_six_parallel_consume_exactly_one(monkeypatch):
    """Six parallel same-fingerprint requests with ONE remaining daily credit:
    exactly one may pass. Today all six pass (the gate only READS)."""
    fake = FakeRedis()
    fp = "a" * 64
    anon_id = f"anon:{fp}"
    daily_key = us._daily_key(anon_id)
    fake.store[daily_key] = 2  # 2 of 3 used -> exactly one remaining

    monkeypatch.setattr(us, "redis_client", fake)

    results = await asyncio.gather(
        *[us.check_anon_usage_allowed(fp) for _ in range(6)]
    )

    allowed = [r for r in results if r["allowed"]]
    rejected = [r for r in results if not r["allowed"]]
    assert len(allowed) == 1, f"expected exactly 1 allowed, got {len(allowed)}"
    assert len(rejected) == 5
    assert all(r["reason"] == "daily_limit" for r in rejected)
    # The gate itself debited the credit - counter reflects the consume.
    assert int(fake.store[daily_key]) == 3


@pytest.mark.asyncio
async def test_anon_record_after_gate_does_not_double_count(monkeypatch):
    """With the gate consuming atomically, the legacy fire-and-forget
    record_anon_comparison must NOT debit a second credit."""
    fake = FakeRedis()
    fp = "b" * 64
    anon_id = f"anon:{fp}"
    daily_key = us._daily_key(anon_id)
    monthly_key = us._monthly_key(anon_id)
    fake.store[daily_key] = 2
    fake.store[monthly_key] = 2
    monkeypatch.setattr(us, "redis_client", fake)

    res = await us.check_anon_usage_allowed(fp)
    assert res["allowed"] is True
    # The gate consumed the credit synchronously (TOCTOU closed).
    assert int(fake.store[daily_key]) == 3
    assert int(fake.store[monthly_key]) == 3

    # The route still fire-and-forgets this on success - must be a no-op now.
    await us.record_anon_comparison(fp)
    assert int(fake.store[daily_key]) == 3
    assert int(fake.store[monthly_key]) == 3


# ---------------------------------------------------------------------------
# 2. CD-interactions-07 / CD-wave-diffs-09 - refund credits the debited window
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "consume_at,refund_at",
    [
        (  # UTC midnight straddle
            datetime(2026, 9, 1, 23, 59, 0, tzinfo=timezone.utc),
            datetime(2026, 9, 2, 0, 0, 30, tzinfo=timezone.utc),
        ),
        (  # month rollover straddle
            datetime(2026, 9, 30, 23, 59, 0, tzinfo=timezone.utc),
            datetime(2026, 10, 1, 0, 0, 30, tzinfo=timezone.utc),
        ),
    ],
)
async def test_refund_credits_the_window_the_consume_debited(
    monkeypatch, consume_at, refund_at
):
    """A consume just before a UTC window boundary refunded just after must
    credit back the OLD window - not decrement the NEW window to -1."""
    fake = FakeRedis()
    monkeypatch.setattr(us, "redis_client", fake)
    _stub_tier(monkeypatch)
    _freeze(monkeypatch, consume_at)

    old_daily = us._daily_key("u1")
    old_monthly = us._monthly_key("u1")

    res = await us.consume_comparison_credit("u1", "tok")
    assert res["allowed"] and res["consumed"]
    assert int(fake.store[old_daily]) == 1
    assert int(fake.store[old_monthly]) == 1

    # The comparison work fails after the boundary; refund fires (legacy
    # signature - exactly what text_routes calls today).
    _freeze(monkeypatch, refund_at)
    new_daily = us._daily_key("u1")
    new_monthly = us._monthly_key("u1")
    await us.refund_comparison_credit("u1")

    # The debited (old) window was credited back...
    assert int(fake.store[old_daily]) == 0, "old day's burned credit not refunded"
    assert int(fake.store[old_monthly]) == 0, "old month's burned credit not refunded"
    # ...and the new window was NOT driven negative (no phantom credit).
    assert int(fake.store.get(new_daily, 0)) >= 0
    assert int(fake.store.get(new_monthly, 0)) >= 0


@pytest.mark.asyncio
async def test_refund_never_mints_negative_counters(monkeypatch):
    """Refund against an empty store (nothing consumed - e.g. redis restarted)
    must not create -1 keys, and any key it does touch into existence must
    carry a TTL so it cannot leak forever."""
    fake = FakeRedis()
    monkeypatch.setattr(us, "redis_client", fake)

    await us.refund_comparison_credit("u-empty")

    for key, val in fake.store.items():
        assert int(val) >= 0, f"refund minted a negative counter at {key}"
        assert key in fake.ttls, f"refund left a TTL-less key {key}"


@pytest.mark.asyncio
async def test_consume_returns_keys_and_refund_honors_them(monkeypatch):
    """Deterministic symmetry: consume returns the exact keys it debited and
    refund(consumed_keys=...) credits exactly those, even across midnight."""
    fake = FakeRedis()
    monkeypatch.setattr(us, "redis_client", fake)
    _stub_tier(monkeypatch)
    _freeze(monkeypatch, datetime(2026, 9, 1, 23, 59, 0, tzinfo=timezone.utc))

    res = await us.consume_comparison_credit("u2", "tok")
    assert res["allowed"] and res["consumed"]
    keys = res["consumed_keys"]
    assert keys["daily"] == us._daily_key("u2")
    assert keys["monthly"] == us._monthly_key("u2")
    assert int(fake.store[keys["daily"]]) == 1
    assert int(fake.store[keys["monthly"]]) == 1

    _freeze(monkeypatch, datetime(2026, 9, 2, 0, 0, 30, tzinfo=timezone.utc))
    await us.refund_comparison_credit("u2", consumed_keys=keys)

    assert int(fake.store[keys["daily"]]) == 0
    assert int(fake.store[keys["monthly"]]) == 0
    # Nothing else was touched into existence.
    for key, val in fake.store.items():
        assert int(val) >= 0


@pytest.mark.asyncio
async def test_partial_failure_refund_does_not_drive_monthly_negative(monkeypatch):
    """The fail-open exception path can return consumed:True after only the
    daily INCRBY succeeded (monthly incrby raised). The paired refund must not
    drive the never-incremented monthly counter negative."""
    monthly_key = us._monthly_key("u3")
    fake = FakeRedis(raise_on_incr_keys={monthly_key})
    monkeypatch.setattr(us, "redis_client", fake)
    _stub_tier(monkeypatch)

    res = await us.consume_comparison_credit("u3", "tok")
    assert res["allowed"] is True  # fail-open
    daily_key = us._daily_key("u3")
    assert int(fake.store[daily_key]) == 1
    assert monthly_key not in fake.store

    await us.refund_comparison_credit("u3")

    assert int(fake.store[daily_key]) == 0
    assert int(fake.store.get(monthly_key, 0)) >= 0, (
        "refund drove the never-incremented monthly counter negative"
    )


# ---------------------------------------------------------------------------
# 3. LS-event-loop-03 - drop the redundant reads, parallelize the DB reads
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_success_path_issues_zero_remaining_count_gets(monkeypatch):
    """The INCRBY return values ARE the post-consume counts - the success path
    must not re-GET either counter, and the remaining math must still be right."""
    fake = FakeRedis()
    daily_key = us._daily_key("u4")
    monthly_key = us._monthly_key("u4")
    fake.store[daily_key] = 1
    fake.store[monthly_key] = 4
    monkeypatch.setattr(us, "redis_client", fake)
    _stub_tier(monkeypatch)

    res = await us.consume_comparison_credit("u4", "tok")

    assert res["allowed"] and res["consumed"]
    assert fake.get_calls == 0, (
        f"success path still re-reads counters ({fake.get_calls} GETs) whose "
        "values the incrby already returned"
    )
    # free tier: daily 3, monthly 10. Post-consume: daily 2, monthly 5.
    assert res["remaining"]["daily"] == 1
    assert res["remaining"]["monthly"] == 5


@pytest.mark.asyncio
async def test_anon_success_path_issues_zero_remaining_count_gets(monkeypatch):
    fake = FakeRedis()
    fp = "c" * 64
    monkeypatch.setattr(us, "redis_client", fake)

    res = await us.check_anon_usage_allowed(fp)

    assert res["allowed"] is True
    assert fake.get_calls == 0, (
        f"anon gate still issues {fake.get_calls} read round trips the "
        "atomic consume makes redundant"
    )
    # Post-consume: 1 of 3 daily, 1 of 10 monthly.
    assert res["remaining"]["daily"] == 2
    assert res["remaining"]["monthly"] == 9


@pytest.mark.asyncio
async def test_tier_and_bonus_fetched_concurrently(monkeypatch):
    """The two independent Supabase reads must overlap. The tier stub blocks
    until the bonus stub has started: serial execution (tier fully awaited
    before bonus starts) deadlocks and trips the wait_for timeout."""
    fake = FakeRedis()
    monkeypatch.setattr(us, "redis_client", fake)

    bonus_started = asyncio.Event()

    async def _tier(uid):
        await asyncio.wait_for(bonus_started.wait(), timeout=2)
        return {"subscription_tier": "free", "lifetime_comparisons_used": 99}

    async def _bonus(uid):
        bonus_started.set()
        return 0

    monkeypatch.setattr(us, "_get_user_tier_info", _tier)
    monkeypatch.setattr(us, "_get_active_referral_bonus", _bonus)

    res = await asyncio.wait_for(us.consume_comparison_credit("u5", "tok"), timeout=4)
    assert res["allowed"] is True


# ---------------------------------------------------------------------------
# 4. Property test - seeded random walk over the consume/refund pair
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("seed", [1, 7, 42])
async def test_property_consume_refund_symmetry_random_walk(monkeypatch, seed):
    """Random interleaving of consumes, key-carrying refunds and clock advances
    (including boundary straddles). Invariants after EVERY operation:
      - no window counter is ever negative;
      - every window counter equals the model (debits minus paired refunds
        credited to the SAME window the consume debited).
    """
    rng = random.Random(seed)
    fake = FakeRedis()
    monkeypatch.setattr(us, "redis_client", fake)
    # Large caps so the walk exercises the consume/refund pair, not rejections
    # (rejections are pinned separately above and in test_m13_37).
    _stub_tier(monkeypatch, tier="premium", bonus=0)

    now = datetime(2026, 9, 1, 22, 0, 0, tzinfo=timezone.utc)
    _freeze(monkeypatch, now)

    expected = {}  # key -> net count
    pending = []  # consumed_keys dicts not yet refunded

    def check_invariants():
        for key, val in fake.store.items():
            assert int(val) >= 0, f"negative counter {key}={val} (seed {seed})"
        for key, val in expected.items():
            assert int(fake.store.get(key, 0)) == val, (
                f"window {key}: store={fake.store.get(key, 0)} model={val} "
                f"(seed {seed})"
            )

    for _ in range(200):
        op = rng.random()
        if op < 0.45:
            res = await us.consume_comparison_credit("pu", "tok")
            if res["allowed"] and res.get("consumed"):
                keys = res["consumed_keys"]
                expected[keys["daily"]] = expected.get(keys["daily"], 0) + 1
                expected[keys["monthly"]] = expected.get(keys["monthly"], 0) + 1
                pending.append(keys)
        elif op < 0.75 and pending:
            keys = pending.pop(rng.randrange(len(pending)))
            await us.refund_comparison_credit("pu", consumed_keys=keys)
            expected[keys["daily"]] -= 1
            expected[keys["monthly"]] -= 1
        else:
            # Advance the clock 1 minute .. 26 hours (crosses day and, over
            # the walk, month boundaries).
            now = now + timedelta(minutes=rng.randint(1, 1560))
            _freeze(monkeypatch, now)
        check_invariants()
