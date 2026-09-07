"""B2 (mobile checkup 2026-09-06) — an EXPIRED Bearer token must not be
indistinguishable from an ABSENT one.

Failure scenario being pinned: a phone that has been backgrounded past the
access-token lifetime resumes holding a stale JWT. `get_optional_user` catches
the rejection and returns `None`, exactly as it does for a request that carried
no `Authorization` header at all, so `POST /api/v1/text/compare` runs the compare
ANONYMOUSLY and returns HTTP 200:

  * `consume_comparison_credit` is skipped     -> the compare is UNMETERED
  * `save_comparison_and_track_cohort` skipped -> NO history row, no cohort
  * `record_lifetime_comparison` skipped       -> lifetime counter never moves
  * user preferences skipped                   -> no personalization

and because no 401 is ever emitted, the mobile client's 401 -> refresh -> retry
interceptor (`SmartCompareApp/src/services/api.ts`) can never fire. The user sits
in a logged-in UI while their decision is silently discarded.

`ENABLE_STRICT_OPTIONAL_AUTH` (NEW, default OFF) splits the two cases apart:
ABSENT still means anonymous; PRESENTED-BUT-REJECTED raises the standard 401
`AUTH_REQUIRED` envelope so the interceptor refreshes and re-drives the original
request, which then meters + persists exactly once.

Scope note: this file exercises the TEXT compare route's EXISTING usage bracket
only. The camera (`image_routes`) and URL (`url_routes`) metering unit is owned
by a separate workstream under its own flag and is deliberately not touched here.
"""
import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")
os.environ.setdefault("ADMIN_API_KEY", "test-admin-key")

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from app.api import auth_routes


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

STRICT_FLAG = "ENABLE_STRICT_OPTIONAL_AUTH"

EXPIRED_TOKEN = "expired.jwt.token"
FRESH_TOKEN = "fresh.jwt.token"
FRESH_USER = {
    "id": "user-b2",
    "email": "b2@example.com",
    "access_token": FRESH_TOKEN,
}


@pytest.fixture(autouse=True)
def _clean_strict_flag(monkeypatch):
    """Every test states its own flag value; never inherit the ambient env."""
    monkeypatch.delenv(STRICT_FLAG, raising=False)
    yield


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """slowapi caps /text/compare at 10/minute per IP; this file issues several
    compares from the TestClient's single fake IP. Mirror of
    tests/test_text_routes_error_mapping.py."""
    from app.middleware.rate_limiter import limiter

    try:
        limiter.reset()
    except Exception:  # noqa: BLE001
        pass
    yield


def _verify_token_stub():
    """Supabase behaviour, reproduced: an expired/revoked JWT resolves to None
    (auth_service.verify_token swallows the AuthApiError), a live one resolves
    to the user dict."""

    async def _verify(token):
        if token == FRESH_TOKEN:
            return dict(FRESH_USER)
        return None

    return _verify


# --------------------------------------------------------------------------
# 1. the dependency itself — ABSENT vs PRESENTED-BUT-REJECTED
# --------------------------------------------------------------------------


class TestFlagDefault:
    def test_flag_is_off_when_unset(self):
        assert auth_routes.strict_optional_auth_enabled() is False

    @pytest.mark.parametrize("value", ["true", "True", "1", " yes ", "ON"])
    def test_flag_on_values(self, monkeypatch, value):
        monkeypatch.setenv(STRICT_FLAG, value)
        assert auth_routes.strict_optional_auth_enabled() is True

    @pytest.mark.parametrize("value", ["false", "0", "no", "off", "", "maybe"])
    def test_flag_off_values(self, monkeypatch, value):
        monkeypatch.setenv(STRICT_FLAG, value)
        assert auth_routes.strict_optional_auth_enabled() is False

    def test_flag_is_read_per_call_not_cached(self, monkeypatch):
        """Railway must be able to flip it without a restart (the
        price_service.exact_gate_enabled idiom)."""
        assert auth_routes.strict_optional_auth_enabled() is False
        monkeypatch.setenv(STRICT_FLAG, "true")
        assert auth_routes.strict_optional_auth_enabled() is True
        monkeypatch.setenv(STRICT_FLAG, "false")
        assert auth_routes.strict_optional_auth_enabled() is False


class TestGetOptionalUserFlagOff:
    """Flag OFF must be byte-identical to the pre-change behaviour: every
    rejection shape still degrades silently to None."""

    @pytest.mark.asyncio
    async def test_absent_header_is_none(self):
        assert await auth_routes.get_optional_user(authorization=None) is None

    @pytest.mark.asyncio
    async def test_rejected_token_is_none(self):
        with patch.object(
            auth_routes, "verify_token", new=AsyncMock(return_value=None)
        ):
            result = await auth_routes.get_optional_user(
                authorization=f"Bearer {EXPIRED_TOKEN}"
            )
        assert result is None

    @pytest.mark.asyncio
    async def test_verify_token_raising_is_none(self):
        with patch.object(
            auth_routes,
            "verify_token",
            new=AsyncMock(side_effect=Exception("Token expired")),
        ):
            result = await auth_routes.get_optional_user(
                authorization=f"Bearer {EXPIRED_TOKEN}"
            )
        assert result is None

    @pytest.mark.asyncio
    async def test_malformed_header_is_none(self):
        assert (
            await auth_routes.get_optional_user(authorization="NotBearer abc") is None
        )
        assert await auth_routes.get_optional_user(authorization="Bearer") is None

    @pytest.mark.asyncio
    async def test_valid_token_returns_user(self):
        with patch.object(
            auth_routes, "verify_token", new=AsyncMock(side_effect=_verify_token_stub())
        ):
            result = await auth_routes.get_optional_user(
                authorization=f"Bearer {FRESH_TOKEN}"
            )
        assert result == FRESH_USER


class TestGetOptionalUserFlagOn:
    @pytest.fixture(autouse=True)
    def _on(self, monkeypatch):
        monkeypatch.setenv(STRICT_FLAG, "true")

    @pytest.mark.asyncio
    async def test_absent_header_still_anonymous(self):
        """ABSENT is NOT an error — anonymous compares must keep working."""
        assert await auth_routes.get_optional_user(authorization=None) is None

    @pytest.mark.asyncio
    async def test_rejected_token_raises_401_auth_required(self):
        with patch.object(
            auth_routes, "verify_token", new=AsyncMock(return_value=None)
        ):
            with pytest.raises(HTTPException) as exc:
                await auth_routes.get_optional_user(
                    authorization=f"Bearer {EXPIRED_TOKEN}"
                )
        assert exc.value.status_code == 401
        assert exc.value.detail["code"] == "AUTH_REQUIRED"

    @pytest.mark.asyncio
    async def test_verify_token_raising_raises_401(self):
        """The legacy blanket `except Exception` must not swallow the 401 it
        now has to raise — HTTPException is itself an Exception."""
        with patch.object(
            auth_routes,
            "verify_token",
            new=AsyncMock(side_effect=Exception("Token expired")),
        ):
            with pytest.raises(HTTPException) as exc:
                await auth_routes.get_optional_user(
                    authorization=f"Bearer {EXPIRED_TOKEN}"
                )
        assert exc.value.status_code == 401
        assert exc.value.detail["code"] == "AUTH_REQUIRED"

    @pytest.mark.asyncio
    async def test_malformed_header_raises_401_naming_the_format(self):
        """The header-shape rejection keeps its OWN message. Without the
        `except HTTPException: raise` re-entry guard the blanket
        `except Exception` below re-runs the rejection and relabels a
        malformed header as an expired token."""
        with pytest.raises(HTTPException) as exc:
            await auth_routes.get_optional_user(authorization="NotBearer abc")
        assert exc.value.status_code == 401
        assert exc.value.detail["code"] == "AUTH_REQUIRED"
        assert "Bearer <token>" in exc.value.detail["error"]

    @pytest.mark.asyncio
    async def test_bearer_with_no_token_raises_401(self):
        with pytest.raises(HTTPException) as exc:
            await auth_routes.get_optional_user(authorization="Bearer")
        assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_valid_token_still_returns_user(self):
        with patch.object(
            auth_routes, "verify_token", new=AsyncMock(side_effect=_verify_token_stub())
        ):
            result = await auth_routes.get_optional_user(
                authorization=f"Bearer {FRESH_TOKEN}"
            )
        assert result == FRESH_USER


# --------------------------------------------------------------------------
# 2. the whole point — the TEXT compare route's usage bracket
# --------------------------------------------------------------------------


class _CompareHarness:
    """Drives POST /api/v1/text/compare with every side effect recorded.

    Patches only what the usage bracket touches, so the assertions are about
    metering/persistence and nothing else.
    """

    def __init__(self):
        self.consume_calls = []
        self.refund_calls = []
        self.ff_labels = []

    def __enter__(self):
        from fastapi.testclient import TestClient
        from app.main import app

        result = {
            "success": True,
            "products": [{"brand": "A", "name": "1"}, {"brand": "B", "name": "2"}],
            "metadata": {"total_cost": 0.0},
        }

        async def _consume(user_id, access_token=""):
            self.consume_calls.append((user_id, access_token))
            return {"allowed": True, "consumed": True, "tier": "free", "remaining": 2}

        async def _refund(user_id):
            self.refund_calls.append(user_id)

        def _fire_and_forget(coro, label):
            self.ff_labels.append(label)
            # Nothing is scheduled: close the coroutine so the event loop never
            # sees an un-awaited DB write.
            close = getattr(coro, "close", None)
            if close:
                close()
            return None

        async def _prefs(user_id):
            return {"success": True, "preferences_completed": False}

        self._stack = [
            patch("app.api.text_routes.get_comparison_service"),
            patch("app.api.text_routes.consume_comparison_credit", new=_consume),
            patch("app.api.text_routes.refund_comparison_credit", new=_refund),
            patch("app.api.text_routes.fire_and_forget", new=_fire_and_forget),
            patch("app.api.text_routes.get_user_preferences", new=_prefs),
            patch.object(
                auth_routes, "verify_token", new=AsyncMock(side_effect=_verify_token_stub())
            ),
        ]
        entered = [cm.__enter__() for cm in self._stack]
        entered[0].return_value.compare_from_text = AsyncMock(return_value=result)
        self.client = TestClient(app)
        return self

    def __exit__(self, *exc):
        for cm in reversed(self._stack):
            cm.__exit__(*exc)
        return False

    def compare(self, token=None):
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        return self.client.post(
            "/api/v1/text/compare",
            json={"query": "iPhone 15 vs Galaxy S24"},
            headers=headers,
        )


class TestCompareRouteFlagOff:
    """Documents the live defect AND proves flag-OFF byte-identity."""

    def test_expired_token_silently_runs_an_anonymous_unmetered_compare(
        self, monkeypatch
    ):
        monkeypatch.setenv(STRICT_FLAG, "false")
        with _CompareHarness() as h:
            resp = h.compare(EXPIRED_TOKEN)

        assert resp.status_code == 200
        assert resp.json()["success"] is True
        # The defect, stated as an assertion: an authenticated user's compare
        # is neither metered nor persisted.
        assert h.consume_calls == []
        assert "save_comparison.text.post" not in h.ff_labels
        assert "record_lifetime.text.post" not in h.ff_labels

    def test_fresh_token_is_metered_and_persisted(self, monkeypatch):
        monkeypatch.setenv(STRICT_FLAG, "false")
        with _CompareHarness() as h:
            resp = h.compare(FRESH_TOKEN)

        assert resp.status_code == 200
        assert [c[0] for c in h.consume_calls] == ["user-b2"]
        assert h.ff_labels.count("save_comparison.text.post") == 1
        assert h.ff_labels.count("record_lifetime.text.post") == 1


class TestCompareRouteFlagOn:
    @pytest.fixture(autouse=True)
    def _on(self, monkeypatch):
        monkeypatch.setenv(STRICT_FLAG, "true")

    def test_expired_token_gets_401_auth_required_and_burns_nothing(self):
        with _CompareHarness() as h:
            resp = h.compare(EXPIRED_TOKEN)

        assert resp.status_code == 401
        body = resp.json()
        assert body["success"] is False
        assert body["code"] == "AUTH_REQUIRED"
        # The dependency rejects BEFORE the handler body, so no credit is
        # reserved and nothing needs refunding.
        assert h.consume_calls == []
        assert h.refund_calls == []
        assert h.ff_labels == []

    def test_absent_header_still_serves_an_anonymous_compare(self):
        with _CompareHarness() as h:
            resp = h.compare(None)

        assert resp.status_code == 200
        assert resp.json()["success"] is True
        assert h.consume_calls == []

    def test_401_then_refreshed_retry_meters_and_persists_exactly_once(self):
        """The whole contract, end to end: the phone's stale token is refused,
        the client's interceptor refreshes, and the RE-DRIVEN request carries
        the new Bearer -> metered once, history row written once."""
        with _CompareHarness() as h:
            first = h.compare(EXPIRED_TOKEN)
            assert first.status_code == 401

            # ...client refreshes (api.ts performRefresh) and replays the same
            # compare with the new access token.
            retried = h.compare(FRESH_TOKEN)

        assert retried.status_code == 200
        assert retried.json()["success"] is True
        # Exactly once across BOTH requests — the rejected attempt contributed
        # nothing, the retry contributed one of each.
        assert [c[0] for c in h.consume_calls] == ["user-b2"]
        assert h.consume_calls[0][1] == FRESH_TOKEN
        assert h.ff_labels.count("save_comparison.text.post") == 1
        assert h.ff_labels.count("record_lifetime.text.post") == 1
