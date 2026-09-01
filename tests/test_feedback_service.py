"""#116 — the save side of the home:savings cache-bust contract.

`/home/savings` is busted on write so a lengthened TTL cannot serve a stale
banner: history delete busts it (tests in test_history_routes.py) and a
successful `save_comparison_and_track_cohort` busts it here — ONLY when the
save actually produced a comparison_id (mirroring the delete-side invariant
that a failed mutation never busts a valid cache).
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services import feedback_service as fs


def _full_response():
    return {"metadata": {}, "products": []}


@pytest.mark.asyncio
async def test_successful_save_busts_home_savings_cache(monkeypatch):
    monkeypatch.setattr(
        fs, "save_comparison", AsyncMock(return_value={"id": "comp-1"})
    )
    monkeypatch.setattr(fs, "track_event", AsyncMock(return_value={"success": True}))
    monkeypatch.setattr(fs, "_persist_verdict_critique", AsyncMock())

    fake_referral = MagicMock()
    fake_referral.return_value.try_trigger_loop2 = AsyncMock()
    busted = []
    monkeypatch.setattr(fs, "delete_cached", lambda key: busted.append(key) or True)

    with patch("app.services.referral_service.ReferralService", fake_referral):
        await fs.save_comparison_and_track_cohort(
            full_response=_full_response(),
            query="a vs b",
            input_type="text",
            user_id="user-42",
        )

    assert "home:savings:user-42" in busted, (
        f"successful save must bust the savings cache; busted={busted}"
    )


@pytest.mark.asyncio
async def test_failed_save_does_not_bust_home_savings(monkeypatch):
    monkeypatch.setattr(fs, "save_comparison", AsyncMock(return_value=None))
    monkeypatch.setattr(fs, "track_event", AsyncMock(return_value={"success": True}))

    busted = []
    monkeypatch.setattr(fs, "delete_cached", lambda key: busted.append(key) or True)

    await fs.save_comparison_and_track_cohort(
        full_response=_full_response(),
        query="a vs b",
        input_type="text",
        user_id="user-42",
    )

    assert busted == [], f"failed save must not bust any cache; busted={busted}"
