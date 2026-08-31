"""M13-37 pin — the freemium gate consumes atomically: N parallel requests from a
user with 1 remaining daily credit consume exactly ONE.

Failure scenario: check_usage_allowed READ the counters before the work and
record_comparison INCREMENTED them fire-and-forget after, so a free user at 2 of 3
daily could fire 6 parallel /text/compare (the limiter allows 10/min); all six read
daily_used=2, all six passed, all six ran — 6 comparisons against a 3/day cap.
consume_comparison_credit reserves the credit synchronously via an atomic
INCRBY + cap check + DECRBY rollback.
"""
import asyncio

import pytest

from app.services import usage_service as us


class _FakeRedis:
    """Single-threaded atomic counter — each incrby/decrby is indivisible, exactly
    like Upstash INCRBY, so 'parallel' asyncio callers cannot interleave mid-op."""
    def __init__(self):
        self.store = {}

    def incrby(self, key, n):
        self.store[key] = int(self.store.get(key, 0)) + n
        return self.store[key]

    def decrby(self, key, n):
        self.store[key] = int(self.store.get(key, 0)) - n
        return self.store[key]

    def expire(self, key, ttl):
        return True

    def get(self, key):
        v = self.store.get(key)
        return str(v) if v is not None else None


@pytest.mark.asyncio
async def test_six_parallel_consume_exactly_one_daily_credit(monkeypatch):
    fake = _FakeRedis()
    daily_key = us._daily_key("u1")
    fake.store[daily_key] = 2  # 2 of 3 used -> exactly one remaining

    monkeypatch.setattr(us, "redis_client", fake)

    async def _tier(uid):
        # Past the 3 lifetime-free comparisons -> the daily/monthly gate applies.
        return {"subscription_tier": "free", "lifetime_comparisons_used": 3}
    monkeypatch.setattr(us, "_get_user_tier_info", _tier)

    async def _bonus(uid):
        return 0
    monkeypatch.setattr(us, "_get_active_referral_bonus", _bonus)

    results = await asyncio.gather(
        *[us.consume_comparison_credit("u1", "tok") for _ in range(6)]
    )

    allowed = [r for r in results if r["allowed"]]
    rejected = [r for r in results if not r["allowed"]]
    assert len(allowed) == 1, f"expected exactly 1 allowed, got {len(allowed)}"
    assert len(rejected) == 5
    assert all(r["reason"] == "daily_limit" for r in rejected)
    # The counter reflects exactly the consumed credit, not the attempts.
    assert int(fake.store[daily_key]) == 3


@pytest.mark.asyncio
async def test_refund_restores_the_daily_credit(monkeypatch):
    fake = _FakeRedis()
    daily_key = us._daily_key("u2")
    monthly_key = us._monthly_key("u2")
    fake.store[daily_key] = 2
    fake.store[monthly_key] = 2
    monkeypatch.setattr(us, "redis_client", fake)

    async def _tier(uid):
        return {"subscription_tier": "free", "lifetime_comparisons_used": 3}
    monkeypatch.setattr(us, "_get_user_tier_info", _tier)

    async def _bonus(uid):
        return 0
    monkeypatch.setattr(us, "_get_active_referral_bonus", _bonus)

    res = await us.consume_comparison_credit("u2", "tok")
    assert res["allowed"] and res["consumed"]
    assert int(fake.store[daily_key]) == 3

    # A later work failure refunds the reserved credit.
    await us.refund_comparison_credit("u2")
    assert int(fake.store[daily_key]) == 2
    assert int(fake.store[monthly_key]) == 2


@pytest.mark.asyncio
async def test_monthly_cap_rejects_and_rolls_back_daily(monkeypatch):
    fake = _FakeRedis()
    daily_key = us._daily_key("u3")
    monthly_key = us._monthly_key("u3")
    fake.store[daily_key] = 0        # daily has room
    fake.store[monthly_key] = 10     # monthly at cap (free base = 10)
    monkeypatch.setattr(us, "redis_client", fake)

    async def _tier(uid):
        return {"subscription_tier": "free", "lifetime_comparisons_used": 3}
    monkeypatch.setattr(us, "_get_user_tier_info", _tier)

    async def _bonus(uid):
        return 0
    monkeypatch.setattr(us, "_get_active_referral_bonus", _bonus)

    res = await us.consume_comparison_credit("u3", "tok")
    assert not res["allowed"]
    assert res["reason"] == "monthly_limit"
    # The daily incr taken before the monthly check was rolled back.
    assert int(fake.store[daily_key]) == 0
    assert int(fake.store[monthly_key]) == 10
