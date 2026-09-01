"""MB-contract-05 — referral landing + invitee quiz must read comparisons.full_response.

The comparisons table has NO ``response_data`` column: migration
001_update_comparisons.sql defines ``full_response JSONB`` and the only
writer of comparison payloads (database_service.save_comparison, :215)
persists under ``full_response``.  ``grep -rn response_data migrations/``
returns nothing.  referral_service previously selected and read a
``response_data`` column at four sites (resolve_invite + run_invitee_quiz),
so with ENABLE_REFERRAL_SYSTEM ON every invite landing / invitee quiz
either PostgREST-errored (42703) or rendered an empty comparison.

These tests mock the comparison row AS THE DATABASE ACTUALLY RETURNS IT
(``full_response`` key, no ``response_data`` key) and assert the payload
reaches the invitee.  At the broken base they fail because the service
reads the nonexistent key and degrades to ``{}``.
"""

from unittest.mock import MagicMock, patch

import pytest

# The row shape the real DB serves: full_response only.
_REAL_ROW_PAYLOAD = {
    "products": [{"name": "iPhone 15"}, {"name": "Galaxy S24"}],
    "winner": {"name": "iPhone 15"},
    "winner_index": 0,
    "scoring": {"scoring_method": "category_weighted"},
    "preferences": {"priorities": ["best_price"]},  # must be stripped
    "personalization": {"user_id": "ref-1"},  # must be stripped
}


def _make_resolve_client(select_columns_sink=None):
    """Mock supabase client serving a REAL-shaped comparisons row."""
    client = MagicMock()
    client.rpc.return_value.execute.return_value = MagicMock(
        data=[{"referrer_user_id": "ref-1", "display_name": "Ahmed"}]
    )

    comp = MagicMock(
        data={
            "id": "cmp-1",
            "user_id": "ref-1",
            "share_token": "tok-aaaaaaaaaaaaaaaaaa",
            "full_response": dict(_REAL_ROW_PAYLOAD),
        }
    )
    invite_resp = MagicMock(data=[{"id": "invite-1", "first_viewed_at": "2026-05-04T00:00:00Z"}])

    def table_side_effect(name):
        t = MagicMock()
        if name == "comparisons":
            def capture_select(*cols):
                if select_columns_sink is not None:
                    select_columns_sink.append(", ".join(cols))
                inner = MagicMock()
                inner.eq.return_value.single.return_value.execute.return_value = comp
                return inner

            t.select.side_effect = capture_select
        elif name == "referral_invites":
            chain = (
                t.select.return_value.eq.return_value.eq.return_value
                .order.return_value.limit.return_value
            )
            chain.execute.return_value = invite_resp
        return t

    client.table.side_effect = table_side_effect
    return client


class TestResolveInviteReadsFullResponse:
    @pytest.mark.asyncio
    async def test_landing_comparison_carries_products_from_full_response(self):
        from app.services.referral_service import ReferralService

        client = _make_resolve_client()
        with patch(
            "app.services.referral_service.get_admin_supabase_client", return_value=client
        ):
            svc = ReferralService()
            result = await svc.resolve_invite(
                share_token="tok-aaaaaaaaaaaaaaaaaa", ref_code="QR-AHMED1"
            )

        assert result is not None
        comparison = result["comparison"]
        # The invitee landing must actually receive the referrer's products —
        # a service reading the nonexistent response_data column yields {}.
        assert comparison.get("products") == [
            {"name": "iPhone 15"},
            {"name": "Galaxy S24"},
        ]
        assert comparison.get("winner") == {"name": "iPhone 15"}
        # Privacy invariants still hold on the real column
        assert "preferences" not in comparison
        assert "personalization" not in comparison

    @pytest.mark.asyncio
    async def test_resolve_invite_selects_full_response_column(self):
        """The SELECT must name the column that exists — response_data 42703s."""
        from app.services.referral_service import ReferralService

        sink: list[str] = []
        client = _make_resolve_client(select_columns_sink=sink)
        with patch(
            "app.services.referral_service.get_admin_supabase_client", return_value=client
        ):
            svc = ReferralService()
            await svc.resolve_invite(
                share_token="tok-aaaaaaaaaaaaaaaaaa", ref_code="QR-AHMED1"
            )

        assert sink, "comparisons.select was never called"
        assert "full_response" in sink[0]
        assert "response_data" not in sink[0]


class TestRunInviteeQuizReadsFullResponse:
    @pytest.mark.asyncio
    async def test_quiz_rescores_the_full_response_payload(self):
        from app.services.referral_service import ReferralService

        client = MagicMock()
        select_sink: list[str] = []
        comp = MagicMock(
            data={"id": "cmp-1", "full_response": dict(_REAL_ROW_PAYLOAD)}
        )

        def table_side_effect(name):
            t = MagicMock()
            if name == "comparisons":
                def capture_select(*cols):
                    select_sink.append(", ".join(cols))
                    inner = MagicMock()
                    inner.eq.return_value.single.return_value.execute.return_value = comp
                    return inner

                t.select.side_effect = capture_select
            return t

        client.table.side_effect = table_side_effect

        with patch(
            "app.services.referral_service.get_admin_supabase_client", return_value=client
        ):
            svc = ReferralService()
            result = await svc.run_invitee_quiz(
                share_token="tok-aaaaaaaaaaaaaaaaaa",
                priority="best_price",
                budget="mid",
                brand_attitude="function_first",
            )

        assert result is not None
        # The quiz result must carry the referrer's actual products, not {}.
        assert result.get("products") == [
            {"name": "iPhone 15"},
            {"name": "Galaxy S24"},
        ]
        assert result["scoring"]["scoring_method"] == "invitee_quiz"
        assert "preferences" not in result

        assert select_sink, "comparisons.select was never called"
        assert "full_response" in select_sink[0]
        assert "response_data" not in select_sink[0]
