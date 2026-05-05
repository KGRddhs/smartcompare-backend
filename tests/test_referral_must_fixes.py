"""Tests for team-lead must-fix items (parallel work, 2026-05-05).

Three must-fix red tests, each covering a backend gap that blocks P7 disband:

#1. Feature flag enforcement: when ENABLE_REFERRAL_SYSTEM is unset/false,
    every /api/v1/referrals/* endpoint must return 503 FEATURE_DISABLED
    (no leaky fall-through to auth/route logic).

#2. Invite linking on signup: POST /api/v1/auth/register with `invite_id`
    must update the corresponding referral_invites row's
    `redeemed_by_user_id` to the new user's id.

#3. Privacy toggles persisted: POST /api/v1/referrals/share must accept
    `show_name`, `show_result`, `show_reasons` privacy toggle fields per
    design Section 3.3, and the resulting referral_invites row must store
    them. `show_budget` must NEVER be settable (locked OFF per PDF #8).

All tests are paired with `monkeypatch.setenv("ENABLE_REFERRAL_SYSTEM", "true")`
where appropriate so the flag check itself doesn't short-circuit valid scenarios.
"""
from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


# ============================================
# MUST-FIX #1 — Feature flag enforcement
# ============================================


class TestFeatureFlagEnforcement:
    """When ENABLE_REFERRAL_SYSTEM is OFF/missing, all /referrals/* return 503."""

    @pytest.mark.parametrize(
        "method,path,body",
        [
            ("POST", "/api/v1/referrals/share", {"comparison_id": "c", "share_target": "whatsapp"}),
            ("GET", "/api/v1/referrals/status", None),
            ("GET", "/api/v1/referrals/invite/aaaaaaaaaaaaaaaaaaaa?ref=QR-AAAAAA", None),
            ("POST", "/api/v1/referrals/invite/aaaaaaaaaaaaaaaaaaaa/quiz",
                {"priority": "best_price", "budget": "mid", "brand_attitude": "function_first"}),
        ],
    )
    def test_endpoint_returns_503_when_flag_off(self, monkeypatch, method, path, body):
        """Default OFF: all referral endpoints return 503 FEATURE_DISABLED.

        Tests that the dependency injection of `_require_referral_enabled`
        runs BEFORE auth dependency or pydantic validation.
        """
        monkeypatch.delenv("ENABLE_REFERRAL_SYSTEM", raising=False)

        if method == "GET":
            resp = client.get(path)
        else:
            resp = client.post(path, json=body)

        assert resp.status_code == 503, (
            f"{method} {path} must return 503 when flag off, got {resp.status_code}: {resp.text}"
        )
        # Body shape per design — unified error format with code
        body_json = resp.json()
        # Either top-level code or detail.code (FastAPI default wrapping)
        code = (
            body_json.get("code")
            or (body_json.get("detail") or {}).get("code")
            or body_json.get("error")
        )
        assert code in ("FEATURE_DISABLED", "FeatureDisabled"), (
            f"expected FEATURE_DISABLED code, got body: {body_json}"
        )

    def test_endpoint_returns_503_when_flag_explicit_false(self, monkeypatch):
        monkeypatch.setenv("ENABLE_REFERRAL_SYSTEM", "false")

        resp = client.get("/api/v1/referrals/status")
        assert resp.status_code == 503, f"got {resp.status_code}: {resp.text}"

    def test_endpoint_works_when_flag_true(self, monkeypatch):
        """Sanity check: with flag ON, endpoints don't 503 — they hit auth/route layer."""
        monkeypatch.setenv("ENABLE_REFERRAL_SYSTEM", "true")

        # Anon GET /status — should be 401/403/422 (auth-required), NOT 503
        resp = client.get("/api/v1/referrals/status")
        assert resp.status_code != 503, (
            f"flag ON but endpoint returned 503 — flag check incorrectly fires; "
            f"got {resp.status_code}: {resp.text}"
        )

    def test_share_target_validation_is_after_flag_check(self, monkeypatch):
        """When flag OFF + invalid body: still 503 (flag check runs first)."""
        monkeypatch.delenv("ENABLE_REFERRAL_SYSTEM", raising=False)

        resp = client.post(
            "/api/v1/referrals/share",
            json={"comparison_id": "c1", "share_target": "FACEBOOK_NOT_ALLOWED"},
        )
        # Must be 503, not 422 — flag check should short-circuit before validation
        assert resp.status_code == 503, (
            f"flag check must run before pydantic validation; got {resp.status_code}: {resp.text}"
        )


# ============================================
# MUST-FIX #2 — POST /register links invite_id
# ============================================


class TestRegisterLinksInvite:
    """POST /api/v1/auth/register with invite_id updates referral_invites row."""

    @pytest.mark.asyncio
    async def test_register_with_invite_id_calls_link_function(self):
        """When invite_id is in the register payload, backend must call a
        function that updates referral_invites.redeemed_by_user_id.

        We verify by patching the link function (wherever it lives) and
        checking it was called with the new user's id.
        """
        from app.api.auth_routes import register

        # Mock register_user to return a successful new user
        with patch("app.api.auth_routes.register_user", new_callable=AsyncMock) as mock_register:
            mock_register.return_value = {
                "success": True,
                "user": {"id": "new-user-id", "email": "x@example.com"},
                "session": {"access_token": "tok"},
                "message": "Registered",
            }

            # The link function is wherever the backend chose to put it.
            # Most likely location: app.services.referral_service.link_invite_to_user
            # Patch defensively at multiple plausible locations.
            with patch(
                "app.services.referral_service.link_invite_to_user",
                new_callable=AsyncMock,
                create=True,
            ) as mock_link_a, patch(
                "app.api.auth_routes.link_invite_to_user",
                new_callable=AsyncMock,
                create=True,
            ) as mock_link_b:

                from app.api.auth_routes import RegisterRequest
                req = RegisterRequest(
                    email="x@example.com",
                    password="ValidPass123!",
                    invite_id="00000000-0000-0000-0000-000000000000",
                )

                # Call the route function directly (avoids HTTP/auth complexity)
                request = MagicMock()
                request.headers = {}

                try:
                    result = await register(request, req)
                except TypeError:
                    # Some implementations use different sig; try without request
                    result = await register(req)

                # Either of the two patched paths must have been hit
                assert mock_link_a.called or mock_link_b.called, (
                    "register endpoint must call link_invite_to_user when invite_id present "
                    "(must-fix #2 — see plan B3.5/B4.2)"
                )

    @pytest.mark.asyncio
    async def test_register_without_invite_id_does_not_link(self):
        """Backward compat: organic signup (no invite_id) doesn't trigger linking."""
        from app.api.auth_routes import register, RegisterRequest

        with patch("app.api.auth_routes.register_user", new_callable=AsyncMock) as mock_register:
            mock_register.return_value = {
                "success": True,
                "user": {"id": "organic-user", "email": "x@example.com"},
                "session": {"access_token": "tok"},
            }

            with patch(
                "app.services.referral_service.link_invite_to_user",
                new_callable=AsyncMock,
                create=True,
            ) as mock_link_a, patch(
                "app.api.auth_routes.link_invite_to_user",
                new_callable=AsyncMock,
                create=True,
            ) as mock_link_b:

                req = RegisterRequest(email="x@example.com", password="ValidPass123!")
                request = MagicMock()
                request.headers = {}

                try:
                    await register(request, req)
                except TypeError:
                    await register(req)

                mock_link_a.assert_not_called()
                mock_link_b.assert_not_called()


# ============================================
# MUST-FIX #4 — Privacy toggles on share
# ============================================


class TestSharePrivacyToggles:
    """ShareRequest must accept name/result/reasons toggles, NOT budget."""

    def test_share_request_accepts_privacy_toggle_fields(self):
        """Pydantic model should accept the 3 optional toggles."""
        from app.api.referral_routes import ShareRequest

        try:
            req = ShareRequest(
                comparison_id="c1",
                share_target="whatsapp",
                show_name=True,
                show_result=True,
                show_reasons=False,
            )
            assert hasattr(req, "show_name")
            assert hasattr(req, "show_result")
            assert hasattr(req, "show_reasons")
        except (TypeError, ValueError) as e:
            pytest.fail(
                f"ShareRequest must accept show_name/show_result/show_reasons "
                f"per design 3.3 (must-fix #4): {e}"
            )

    def test_share_request_defaults_match_design(self):
        """Per design 3.3: name=ON, result=ON, reasons=ON by default."""
        from app.api.referral_routes import ShareRequest

        try:
            req = ShareRequest(comparison_id="c1", share_target="whatsapp")
        except Exception as e:
            pytest.skip(f"ShareRequest constructor changed: {e}")

        # Defaults — only check if fields exist (they should after must-fix #4)
        if hasattr(req, "show_name"):
            assert req.show_name is True, "show_name default must be ON per design 3.3"
        if hasattr(req, "show_result"):
            assert req.show_result is True, "show_result default must be ON per design 3.3"
        if hasattr(req, "show_reasons"):
            assert req.show_reasons is True, "show_reasons default must be ON per design 3.3"

    def test_share_request_does_NOT_accept_show_budget(self):
        """show_budget is locked OFF per PDF #8 — must NOT be a settable field.

        If the model accepts it, that's a leak: a malicious client could send
        show_budget=true and the field would silently propagate.
        """
        from app.api.referral_routes import ShareRequest

        try:
            req = ShareRequest(
                comparison_id="c1",
                share_target="whatsapp",
                show_budget=True,  # Should be REJECTED or IGNORED
            )
            # Pydantic v2 with ConfigDict(extra="forbid") raises ValidationError
            # If it accepts the field, ensure it's not stored True
            stored = getattr(req, "show_budget", None)
            assert stored in (None, False), (
                f"show_budget must NEVER be settable to True per PDF #8, got {stored!r}"
            )
        except (TypeError, ValueError):
            # Pydantic forbids the field — correct behavior
            pass

    @pytest.mark.asyncio
    async def test_create_invite_persists_privacy_toggles_to_row(self, monkeypatch):
        """The persisted referral_invites row must include the toggle fields.

        Backend may store them as separate columns or as a JSONB
        privacy_settings column. Either is acceptable — we just verify the
        toggle values reach the DB write call.
        """
        monkeypatch.setenv("ENABLE_REFERRAL_SYSTEM", "true")

        from app.services.referral_service import ReferralService

        client_db = MagicMock()

        weekly_count = MagicMock(count=0)
        existing_user = MagicMock(data={"referral_code": "QR-PRIVY1"})
        comp = MagicMock(data={"id": "c1", "user_id": "u1", "share_token": "tok-x" * 4 + "aaa"})
        invite_row = MagicMock(data=[{"id": "invite-1"}])

        captured_invite_inserts = []

        def table_side_effect(name):
            t = MagicMock()
            if name == "referral_invites":
                t.select.return_value.eq.return_value.gte.return_value.execute.return_value = weekly_count

                def capture_insert(payload):
                    captured_invite_inserts.append(payload)
                    inner = MagicMock()
                    inner.execute.return_value = invite_row
                    return inner

                t.insert.side_effect = capture_insert
            elif name == "users":
                t.select.return_value.eq.return_value.single.return_value.execute.return_value = existing_user
            elif name == "comparisons":
                t.select.return_value.eq.return_value.single.return_value.execute.return_value = comp
            elif name == "deep_review_credits":
                t.insert.return_value.execute.return_value = MagicMock(data=[{}])
            return t

        client_db.table.side_effect = table_side_effect

        with patch("app.services.referral_service.get_admin_supabase_client", return_value=client_db):
            svc = ReferralService()

            # Call create_invite with privacy toggles. Backend may add a
            # privacy kwarg or accept toggles via separate args — try both.
            try:
                await svc.create_invite(
                    referrer_user_id="u1",
                    comparison_id="c1",
                    share_target="whatsapp",
                    show_name=False,
                    show_result=True,
                    show_reasons=True,
                )
            except TypeError as e:
                pytest.fail(
                    f"create_invite must accept show_name/show_result/show_reasons kwargs "
                    f"(must-fix #4): {e}"
                )

            assert len(captured_invite_inserts) == 1
            insert_payload = captured_invite_inserts[0]

            # Privacy toggles must reach the row — either as columns or
            # nested under a privacy_settings JSONB
            settings_keys = {"show_name", "show_result", "show_reasons"}
            row_keys = set(insert_payload.keys())

            has_columns = settings_keys & row_keys
            has_nested = "privacy_settings" in insert_payload and isinstance(
                insert_payload["privacy_settings"], dict
            )

            assert has_columns or has_nested, (
                f"privacy toggles must be stored on referral_invites row, "
                f"got payload keys: {sorted(row_keys)}"
            )
