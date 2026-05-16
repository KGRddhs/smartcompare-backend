"""Backend-owned unit tests for reengagement_service + cron internals.

Contract tests (test-referral lane) patch the DB-side helpers, so the
real implementations stay un-covered. This file exercises them with
mock Supabase clients to lift coverage above the 80% gate.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.reengagement_service import ReengagementService


@pytest.fixture(autouse=True)
def _enable_reengagement_flag(monkeypatch):
    """Bundle E (2026-05-16): both evaluate() and cron.main() are now gated
    by ENABLE_REENGAGEMENT_PUSHES. Default the flag on for legacy internal
    tests that exercise post-gate code paths."""
    monkeypatch.setenv("ENABLE_REENGAGEMENT_PUSHES", "true")
    yield


# ============================================
# 7-day cap helper internals
# ============================================


class TestRecentPushQuery:
    @pytest.mark.asyncio
    async def test_recent_push_with_zero_count_returns_false(self):
        client = MagicMock()
        client.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = MagicMock(
            count=0
        )
        with patch(
            "app.services.reengagement_service.get_admin_supabase_client",
            return_value=client,
        ):
            svc = ReengagementService()
            assert await svc._recent_push({"id": "u1"}) is False

    @pytest.mark.asyncio
    async def test_recent_push_with_nonzero_count_returns_true(self):
        client = MagicMock()
        client.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = MagicMock(
            count=1
        )
        with patch(
            "app.services.reengagement_service.get_admin_supabase_client",
            return_value=client,
        ):
            svc = ReengagementService()
            assert await svc._recent_push({"id": "u1"}) is True

    @pytest.mark.asyncio
    async def test_recent_push_db_error_fails_closed(self):
        """Transient DB error must NOT spam the user — fail closed (skip push)."""
        client = MagicMock()
        client.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.side_effect = RuntimeError(
            "supabase down"
        )
        with patch(
            "app.services.reengagement_service.get_admin_supabase_client",
            return_value=client,
        ):
            svc = ReengagementService()
            assert await svc._recent_push({"id": "u1"}) is True


# ============================================
# Sentiment lookup
# ============================================


class TestComputeCurrentSentiment:
    @pytest.mark.asyncio
    async def test_returns_score_when_row_exists(self):
        client = MagicMock()
        client.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{"sentiment_score": 0.72}]
        )
        with patch(
            "app.services.reengagement_service.get_admin_supabase_client",
            return_value=client,
        ):
            svc = ReengagementService()
            assert await svc._compute_current_sentiment("p1") == 0.72

    @pytest.mark.asyncio
    async def test_returns_none_when_no_rows(self):
        client = MagicMock()
        client.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[]
        )
        with patch(
            "app.services.reengagement_service.get_admin_supabase_client",
            return_value=client,
        ):
            svc = ReengagementService()
            assert await svc._compute_current_sentiment("p-missing") is None

    @pytest.mark.asyncio
    async def test_returns_none_on_db_error(self):
        client = MagicMock()
        client.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.side_effect = RuntimeError(
            "x"
        )
        with patch(
            "app.services.reengagement_service.get_admin_supabase_client",
            return_value=client,
        ):
            svc = ReengagementService()
            assert await svc._compute_current_sentiment("p1") is None


# ============================================
# Top-100 cache lookup
# ============================================


class TestTop100Cache:
    @pytest.mark.asyncio
    async def test_parses_json_payload_when_cached(self):
        with patch(
            "app.services.cache_service._redis_get",
            return_value='["iphone-15", "galaxy-s24"]',
        ), patch(
            "app.services.reengagement_service.get_admin_supabase_client",
            return_value=MagicMock(),
        ):
            svc = ReengagementService()
            result = await svc._get_top_100_saved_globally()
            assert result == {"iphone-15", "galaxy-s24"}

    @pytest.mark.asyncio
    async def test_returns_empty_set_when_uncached(self):
        with patch(
            "app.services.cache_service._redis_get", return_value=None
        ), patch(
            "app.services.reengagement_service.get_admin_supabase_client",
            return_value=MagicMock(),
        ):
            svc = ReengagementService()
            assert await svc._get_top_100_saved_globally() == set()

    @pytest.mark.asyncio
    async def test_returns_empty_set_on_redis_error(self):
        with patch(
            "app.services.cache_service._redis_get", side_effect=RuntimeError("redis")
        ), patch(
            "app.services.reengagement_service.get_admin_supabase_client",
            return_value=MagicMock(),
        ):
            svc = ReengagementService()
            assert await svc._get_top_100_saved_globally() == set()


# ============================================
# 14-day retrospective lookup
# ============================================


class TestRetroLookup:
    @pytest.mark.asyncio
    async def test_returns_comparison_when_no_prior_retro(self):
        client = MagicMock()
        # comparisons query returns one row
        client.table.return_value.select.return_value.eq.return_value.gte.return_value.lte.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{"id": "c14", "full_response": {}, "created_at": "x"}]
        )
        # re_engagement_events query returns 0 prior retro pushes
        client.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            count=0
        )

        with patch(
            "app.services.reengagement_service.get_admin_supabase_client",
            return_value=client,
        ):
            svc = ReengagementService()
            result = await svc._find_14d_comparison_no_retrospective({"id": "u"})
        assert result is not None and result["id"] == "c14"

    @pytest.mark.asyncio
    async def test_returns_none_when_retro_already_sent(self):
        client = MagicMock()
        client.table.return_value.select.return_value.eq.return_value.gte.return_value.lte.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{"id": "c14", "full_response": {}, "created_at": "x"}]
        )
        client.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            count=1
        )
        with patch(
            "app.services.reengagement_service.get_admin_supabase_client",
            return_value=client,
        ):
            svc = ReengagementService()
            assert await svc._find_14d_comparison_no_retrospective({"id": "u"}) is None

    @pytest.mark.asyncio
    async def test_returns_none_when_no_comparison_in_window(self):
        client = MagicMock()
        client.table.return_value.select.return_value.eq.return_value.gte.return_value.lte.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[]
        )
        with patch(
            "app.services.reengagement_service.get_admin_supabase_client",
            return_value=client,
        ):
            svc = ReengagementService()
            assert await svc._find_14d_comparison_no_retrospective({"id": "u"}) is None

    @pytest.mark.asyncio
    async def test_returns_none_on_db_error(self):
        client = MagicMock()
        client.table.return_value.select.return_value.eq.return_value.gte.return_value.lte.return_value.order.return_value.limit.return_value.execute.side_effect = RuntimeError(
            "x"
        )
        with patch(
            "app.services.reengagement_service.get_admin_supabase_client",
            return_value=client,
        ):
            svc = ReengagementService()
            assert await svc._find_14d_comparison_no_retrospective({"id": "u"}) is None


# ============================================
# Payload builders + Arabic localisation
# ============================================


class TestPayloadCopy:
    def test_insight_arabic_user_gets_arabic_title(self):
        with patch(
            "app.services.reengagement_service.get_admin_supabase_client",
            return_value=MagicMock(),
        ):
            svc = ReengagementService()
            payload = svc._build_insight_payload(
                user={"preferences": {"language": "Arabic"}},
                product={"id": "p", "name": "iPhone"},
                current=0.7,
                previous=0.5,
            )
        text = payload["title"] + payload["body"]
        assert any(0x0600 <= ord(c) <= 0x06FF for c in text)

    def test_cohort_english_user_default(self):
        with patch(
            "app.services.reengagement_service.get_admin_supabase_client",
            return_value=MagicMock(),
        ):
            svc = ReengagementService()
            payload = svc._build_cohort_payload(
                user={}, n_users=7, governorate="Capital"
            )
        assert "7" in payload["title"]
        assert "Capital" not in payload["title"]  # English title omits governorate name

    def test_retrospective_falls_back_when_winner_missing(self):
        with patch(
            "app.services.reengagement_service.get_admin_supabase_client",
            return_value=MagicMock(),
        ):
            svc = ReengagementService()
            payload = svc._build_retrospective_payload(
                user={}, comparison={"id": "c", "full_response": {}}
            )
        assert "your decision" in payload["body"]


# ============================================
# cron_reengagement internals
# ============================================


class TestCronInternals:
    @pytest.mark.asyncio
    async def test_fetch_eligible_users_returns_data_on_success(self):
        from scripts.cron_reengagement import _fetch_eligible_users

        client = MagicMock()
        client.table.return_value.select.return_value.eq.return_value.gte.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{"id": "u1"}, {"id": "u2"}]
        )
        users = await _fetch_eligible_users(client)
        assert len(users) == 2

    @pytest.mark.asyncio
    async def test_fetch_eligible_users_empty_on_db_error(self):
        from scripts.cron_reengagement import _fetch_eligible_users

        client = MagicMock()
        client.table.return_value.select.return_value.eq.return_value.gte.return_value.limit.return_value.execute.side_effect = RuntimeError(
            "x"
        )
        assert await _fetch_eligible_users(client) == []

    @pytest.mark.asyncio
    async def test_record_event_returns_id_on_success(self):
        from scripts.cron_reengagement import _record_event

        client = MagicMock()
        client.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": "evt-1"}]
        )
        rid = await _record_event(
            client,
            user_id="u",
            payload={"event_type": "decision_insight", "comparison_id": "c"},
        )
        assert rid == "evt-1"

    @pytest.mark.asyncio
    async def test_record_event_none_on_error(self):
        from scripts.cron_reengagement import _record_event

        client = MagicMock()
        client.table.return_value.insert.return_value.execute.side_effect = RuntimeError("x")
        rid = await _record_event(client, user_id="u", payload={"event_type": "x"})
        assert rid is None

    @pytest.mark.asyncio
    async def test_dispatch_push_handles_missing_user_id(self):
        from scripts.cron_reengagement import _dispatch_push

        # Should not raise and not call send_reengagement_push
        with patch(
            "scripts.cron_reengagement.send_reengagement_push", new_callable=AsyncMock
        ) as mock_send:
            await _dispatch_push(user={}, payload={"event_type": "x"})
            mock_send.assert_not_called()

    @pytest.mark.asyncio
    async def test_dispatch_push_swallows_send_error(self):
        from scripts.cron_reengagement import _dispatch_push

        with patch(
            "scripts.cron_reengagement.send_reengagement_push",
            new_callable=AsyncMock,
            side_effect=RuntimeError("network"),
        ):
            # Should NOT raise
            await _dispatch_push(
                user={"id": "u"},
                payload={
                    "event_type": "decision_insight",
                    "title": "T",
                    "body": "B",
                    "deep_link_url": "x",
                },
            )

    @pytest.mark.asyncio
    async def test_main_handles_no_eligible_users(self):
        from scripts import cron_reengagement

        with patch(
            "scripts.cron_reengagement._fetch_eligible_users",
            new_callable=AsyncMock,
            return_value=[],
        ), patch(
            "scripts.cron_reengagement.ReengagementService"
        ) as MockSvc, patch(
            "scripts.cron_reengagement._dispatch_push", new_callable=AsyncMock
        ) as mock_dispatch:
            await cron_reengagement.main()
            MockSvc.return_value.evaluate.assert_not_called() if hasattr(
                MockSvc.return_value.evaluate, "assert_not_called"
            ) else None
            mock_dispatch.assert_not_called()

    @pytest.mark.asyncio
    async def test_main_swallows_evaluate_exceptions(self):
        from scripts import cron_reengagement

        users = [{"id": "u1"}, {"id": "u2"}]
        with patch(
            "scripts.cron_reengagement._fetch_eligible_users",
            new_callable=AsyncMock,
            return_value=users,
        ), patch(
            "scripts.cron_reengagement.ReengagementService"
        ) as MockSvc, patch(
            "scripts.cron_reengagement._dispatch_push", new_callable=AsyncMock
        ) as mock_dispatch:
            # First user raises, second user returns None — both must be handled.
            MockSvc.return_value.evaluate = AsyncMock(side_effect=[RuntimeError("x"), None])
            await cron_reengagement.main()
            # Neither should have triggered a dispatch
            mock_dispatch.assert_not_called()

    @pytest.mark.asyncio
    async def test_main_dispatches_when_payload_returned(self):
        from scripts import cron_reengagement

        users = [{"id": "u1"}]
        payload = {
            "event_type": "decision_insight",
            "title": "T",
            "body": "B",
            "deep_link_url": "qaren://x",
        }
        with patch(
            "scripts.cron_reengagement._fetch_eligible_users",
            new_callable=AsyncMock,
            return_value=users,
        ), patch(
            "scripts.cron_reengagement.ReengagementService"
        ) as MockSvc, patch(
            "scripts.cron_reengagement._record_event",
            new_callable=AsyncMock,
            return_value="evt-1",
        ), patch(
            "scripts.cron_reengagement._dispatch_push", new_callable=AsyncMock
        ) as mock_dispatch:
            MockSvc.return_value.evaluate = AsyncMock(return_value=payload)
            await cron_reengagement.main()
            mock_dispatch.assert_called_once()
