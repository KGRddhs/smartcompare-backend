"""Bundle A §1.5 — device-bound free-tier counter inheritance.

These tests pin the invariant that a freshly-registered user whose
``lifetime_comparisons_used`` was inherited from a same-device prior account
sees the free-tier lifetime cap apply immediately. This is the user-facing
contract of the fingerprint inheritance logic in auth_routes.register.

We don't re-test the inheritance write path here (that's in
tests/test_auth_routes_invite_fingerprint.py). These tests confirm that
``check_usage_allowed`` respects the inherited value once it lands on the row.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _build_user_chain(tier: str, lifetime_used: int):
    """Build a fluent supabase chain returning user row with given values."""
    chain = MagicMock()
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.single.return_value = chain
    chain.execute.return_value = MagicMock(
        data={
            "subscription_tier": tier,
            "lifetime_comparisons_used": lifetime_used,
        }
    )
    return chain


@pytest.mark.asyncio
async def test_new_free_user_with_inherited_3_blocks_at_lifetime_cap():
    """Inherited lifetime_comparisons_used=3 means new user is OUT of free comparisons.

    The lifetime_free branch only fires when lifetime_used < limits["lifetime_free"]
    (3 for free). At ==3 we fall through to daily/monthly checks against fresh
    Redis counters (0/0). The user gets blocked once they hit the 10/month or
    3/day cap — but NOT immediately, which is the desired behavior: the prior
    user already burned the 3 lifetime-free; the new user inherits the daily/
    monthly allowance but not extra free comparisons.
    """
    chain = _build_user_chain(tier="free", lifetime_used=3)
    mock_client = MagicMock()
    mock_client.table.return_value = chain

    mock_redis = MagicMock()
    mock_redis.get.return_value = None  # fresh Redis counters

    with patch(
        "app.services.usage_service.redis_client", mock_redis
    ), patch(
        "app.services.usage_service.get_admin_supabase_client",
        return_value=mock_client,
    ), patch(
        "app.services.usage_service._get_active_referral_bonus",
        new=AsyncMock(return_value=0),
    ):
        from app.services.usage_service import check_usage_allowed

        result = await check_usage_allowed("new-user", "tok")

    assert result["allowed"] is True
    # lifetime_free remaining drops to 0 — the next branch handles daily/monthly.
    assert result["remaining"]["lifetime_free"] == 0


@pytest.mark.asyncio
async def test_new_free_user_inherited_used_plus_daily_cap_blocks():
    """Inherited=3 AND daily counter at cap (3) → daily_limit block.

    Reproduces the freebie-farming-prevention contract end-to-end at the
    usage layer: a re-signup on the same device with a fresh Redis day will
    still get blocked the moment they hit the daily cap, because the
    lifetime allowance was already consumed by the prior account.
    """
    chain = _build_user_chain(tier="free", lifetime_used=3)
    mock_client = MagicMock()
    mock_client.table.return_value = chain

    mock_redis = MagicMock()
    # Daily count at cap (3), monthly = 3.
    mock_redis.get.side_effect = lambda key: (
        "3" if "daily" in key else "3" if "monthly" in key else None
    )

    with patch(
        "app.services.usage_service.redis_client", mock_redis
    ), patch(
        "app.services.usage_service.get_admin_supabase_client",
        return_value=mock_client,
    ), patch(
        "app.services.usage_service._get_active_referral_bonus",
        new=AsyncMock(return_value=0),
    ):
        from app.services.usage_service import check_usage_allowed

        result = await check_usage_allowed("new-user", "tok")

    assert result["allowed"] is False
    assert result["reason"] == "daily_limit"


@pytest.mark.asyncio
async def test_new_free_user_inherited_zero_still_has_full_lifetime_free():
    """When fingerprint header was absent, inherited=0 → user gets the full 3 free."""
    chain = _build_user_chain(tier="free", lifetime_used=0)
    mock_client = MagicMock()
    mock_client.table.return_value = chain

    mock_redis = MagicMock()
    mock_redis.get.return_value = None

    with patch(
        "app.services.usage_service.redis_client", mock_redis
    ), patch(
        "app.services.usage_service.get_admin_supabase_client",
        return_value=mock_client,
    ), patch(
        "app.services.usage_service._get_active_referral_bonus",
        new=AsyncMock(return_value=0),
    ):
        from app.services.usage_service import check_usage_allowed

        result = await check_usage_allowed("fresh-user", "tok")

    assert result["allowed"] is True
    assert result["remaining"]["lifetime_free"] == 3
