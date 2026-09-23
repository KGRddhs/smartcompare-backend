"""W3-14 B1 -- ``PUT /api/v1/auth/preference-toggles``: a privacy opt-out a
user WITHOUT priorities can actually exercise.

Findings ``MB-NETWORK-CONTRACT-05/-06`` (backend half). The defect, measured
at b63a8368:

* ``UserPreferencesRequest.priorities`` is ``Field(..., min_length=1)``
  (``auth_routes.py:183-184``), so there is NO body a no-priorities user can
  send to flip ``ai_sharing_enabled`` / ``notifications_enabled``:
  ``PUT /preferences`` with ``priorities: []`` -> 422, with only
  ``{"ai_sharing_enabled": false}`` -> 422 "Field required".
* No single-purpose route exists: ``PUT /api/v1/auth/preference-toggles``
  -> Starlette's bare ``404 {"detail": "Not Found"}``.
* The client's answer (``dbf152d9``, F-S1.5i surface C) was to disable the
  toggles -- which makes the privacy control unreachable.

Fix contract (spec section 4 + FABLE rulings R-2, R-11, R-17, R-19): ONE
additive, UNFLAGGED route, ``10/minute``, shaped like the
``PUT /reengagement-subs`` precedent (``228ff63``): user-scoped client,
read-modify-write of ``users.preferences`` touching ONLY the provided
key(s) -- never ``preferences_completed``, ``_sources``, ``priorities`` or
``notification_types`` -- and never via ``save_user_preferences``.
``PUT /preferences`` and ``min_length=1`` stay exactly as they are.

Discipline (ruling R-19): local pydantic is 2.7.0 vs 2.13.4 pinned, fastapi
0.115.0 vs 0.141.1, slowapi 0.1.9 vs 0.1.10, starlette 0.38.6 vs 1.6.0.
Every assertion is on status codes, ``body["code"]``, integer ranges and the
recorded ``update()`` payload -- never on a Pydantic sentence.

Written against ``app.main.app`` (ruling R-11): a hand-built app would lose
``rate_limit_handler`` and the 429 envelope would pass for the wrong reason.

Free tier: no network. Supabase clients are MagicMocks; conftest's autouse
``_reset_rate_limiter`` gives every test a clean limiter window.
"""
from __future__ import annotations

import copy
import ipaddress
import socket
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.api.auth_routes import get_current_user
from app.main import app

_ROUTE = "/api/v1/auth/preference-toggles"
_USER = {"id": "u-w314", "email": "w314@example.com", "access_token": "tok"}
_LIMIT_AMOUNT = 10
_WINDOW_SECONDS = 60


def _is_loopback(host) -> bool:
    if host in (None, "", "localhost"):
        return True
    try:
        return ipaddress.ip_address(str(host).split("%")[0]).is_loopback
    except ValueError:
        return False


@pytest.fixture(autouse=True)
def _zero_network(monkeypatch):
    """Every test in this file is network-free: a non-loopback resolve or
    connect raises AND fails the test at teardown (the route's broad
    ``except`` would otherwise swallow the raise into a 500)."""
    attempts = []
    real_getaddrinfo = socket.getaddrinfo
    real_connect = socket.socket.connect

    def guarded_getaddrinfo(host, *args, **kwargs):
        if not _is_loopback(host):
            attempts.append(f"getaddrinfo({host!r})")
            raise OSError(f"network blocked in test: getaddrinfo({host!r})")
        return real_getaddrinfo(host, *args, **kwargs)

    def guarded_connect(self, address, *args, **kwargs):
        host = address[0] if isinstance(address, tuple) and address else None
        if isinstance(address, tuple) and not _is_loopback(host):
            attempts.append(f"connect({address!r})")
            raise OSError(f"network blocked in test: connect({address!r})")
        return real_connect(self, address, *args, **kwargs)

    monkeypatch.setattr(socket, "getaddrinfo", guarded_getaddrinfo)
    monkeypatch.setattr(socket.socket, "connect", guarded_connect)
    yield
    if attempts:
        pytest.fail(f"network attempted: {attempts}")


def _user_client(existing_preferences, captured_updates, *, raise_on_execute=None):
    """A user-scoped Supabase MagicMock: SELECT returns ``existing_preferences``;
    UPDATE payloads are recorded in ``captured_updates``."""
    client = MagicMock()
    select_chain = (
        client.table.return_value.select.return_value.eq.return_value.single.return_value
    )
    if raise_on_execute is not None:
        select_chain.execute.side_effect = raise_on_execute
    else:
        select_chain.execute.return_value = MagicMock(
            data={"preferences": existing_preferences}
        )

    def capture_update(payload):
        captured_updates.append(copy.deepcopy(payload))
        inner = MagicMock()
        inner.eq.return_value.execute.return_value = MagicMock(data=[{}])
        return inner

    client.table.return_value.update.side_effect = capture_update
    return client


@pytest.fixture()
def authed():
    """TestClient on the REAL app with ``get_current_user`` overridden."""
    app.dependency_overrides[get_current_user] = lambda: dict(_USER)
    try:
        with TestClient(app) as tc:
            yield tc
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def _put(tc, body, existing=None, *, raise_on_execute=None):
    """PUT the route with both Supabase factories and the full-save service
    patched. Returns (response, captured_updates, user_client, admin_client, save_mock)."""
    captured = []
    user_client = _user_client(
        {} if existing is None else copy.deepcopy(existing),
        captured,
        raise_on_execute=raise_on_execute,
    )
    admin_client = MagicMock()
    with patch(
        "app.api.auth_routes.get_user_supabase_client", return_value=user_client
    ), patch(
        "app.api.auth_routes.get_admin_supabase_client", return_value=admin_client
    ), patch(
        "app.api.auth_routes.save_user_preferences",
        new_callable=AsyncMock,
        return_value={"success": True},
    ) as save_mock:
        resp = tc.put(_ROUTE, json=body, headers={"Authorization": "Bearer tok"})
    return resp, captured, user_client, admin_client, save_mock


class TestPreferenceTogglesWrites:
    def test_ai_sharing_off_on_empty_preferences_row(self, authed):
        """A user with NO priorities (empty prefs row) can opt out of AI sharing."""
        resp, captured, user_client, admin_client, save_mock = _put(
            authed, {"ai_sharing_enabled": False}, existing={}
        )
        assert resp.status_code == 200, resp.text
        assert resp.json() == {
            "success": True,
            "ai_sharing_enabled": False,
            "notifications_enabled": None,
        }
        assert captured == [{"preferences": {"ai_sharing_enabled": False}}]
        # Onboarding's completion signal is never touched by a toggle write.
        assert "preferences_completed" not in captured[0]
        assert "preferences_completed" not in captured[0]["preferences"]
        # RLS path: the user-scoped client, not the admin one; not the full saver.
        assert user_client.table.called
        assert not admin_client.table.called
        assert save_mock.await_count == 0

    def test_notifications_off_preserves_every_other_key(self, authed):
        """Read-modify-write flips ONLY the provided key; everything else is
        written back byte-for-byte (priorities, budget, _sources, notification_types...)."""
        existing = {
            "priorities": ["price", "quality"],
            "budget": "premium",
            "lifestyle": ["gamer"],
            "brand_attitude": "function_first",
            "_sources": {"budget": "user_stated", "lifestyle": "cohort_inferred"},
            "notification_types": {
                "decision_insight": True,
                "cohort_curiosity": False,
                "decision_retrospective": True,
            },
            "ai_sharing_enabled": True,
            "notifications_enabled": True,
        }
        resp, captured, _u, _a, save_mock = _put(
            authed, {"notifications_enabled": False}, existing=existing
        )
        assert resp.status_code == 200, resp.text
        assert resp.json() == {
            "success": True,
            "ai_sharing_enabled": True,
            "notifications_enabled": False,
        }
        expected = copy.deepcopy(existing)
        expected["notifications_enabled"] = False
        assert captured == [{"preferences": expected}]
        assert save_mock.await_count == 0

    def test_both_keys_in_one_body(self, authed):
        resp, captured, _u, _a, _s = _put(
            authed,
            {"ai_sharing_enabled": True, "notifications_enabled": False},
            existing={"budget": "mid"},
        )
        assert resp.status_code == 200, resp.text
        assert captured == [
            {
                "preferences": {
                    "budget": "mid",
                    "ai_sharing_enabled": True,
                    "notifications_enabled": False,
                }
            }
        ]

    def test_null_preferences_column_is_treated_as_empty(self, authed):
        """``users.preferences`` NULL (fresh signup) -> the write creates the key."""
        captured = []
        user_client = MagicMock()
        user_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={"preferences": None}
        )

        def capture_update(payload):
            captured.append(copy.deepcopy(payload))
            inner = MagicMock()
            inner.eq.return_value.execute.return_value = MagicMock(data=[{}])
            return inner

        user_client.table.return_value.update.side_effect = capture_update
        admin_client = MagicMock()
        with patch(
            "app.api.auth_routes.get_user_supabase_client", return_value=user_client
        ), patch(
            "app.api.auth_routes.get_admin_supabase_client", return_value=admin_client
        ):
            resp = authed.put(
                _ROUTE,
                json={"ai_sharing_enabled": False},
                headers={"Authorization": "Bearer tok"},
            )
        assert resp.status_code == 200, resp.text
        assert captured == [{"preferences": {"ai_sharing_enabled": False}}]
        assert user_client.table.called
        assert not admin_client.table.called


class TestPreferenceTogglesValidation:
    @pytest.mark.parametrize(
        "body",
        [
            {},
            {"ai_sharing_enabled": None},
            {"ai_sharing_enabled": None, "notifications_enabled": None},
            {"ai_sharing_enabled": "banana"},
            {"ai_sharing_enabled": 1.5},
            {"notifications_enabled": "banana"},
        ],
        ids=["empty", "ai-null", "both-null", "ai-banana", "ai-1.5", "notifs-banana"],
    )
    def test_rejected_bodies_are_422_validation_error_and_write_nothing(self, authed, body):
        resp, captured, _u, _a, save_mock = _put(authed, body, existing={"budget": "mid"})
        assert resp.status_code == 422, resp.text
        assert resp.json()["code"] == "VALIDATION_ERROR"
        assert captured == []
        assert save_mock.await_count == 0

    @pytest.mark.parametrize("value", ["yes", "on", 1])
    def test_documented_lax_coercions_write_true(self, authed, value):
        """DOCUMENTATION row (ruling R-2): pydantic v2 lax mode coerces
        ``"yes"`` / ``"on"`` / ``1`` to ``True`` (measured on 2.7.0). The route is
        deliberately NOT ``strict=True``; the OTA'd client only sends JSON booleans."""
        resp, captured, _u, _a, _s = _put(authed, {"ai_sharing_enabled": value}, existing={})
        assert resp.status_code == 200, resp.text
        assert captured == [{"preferences": {"ai_sharing_enabled": True}}]


class TestPreferenceTogglesFailureModes:
    def test_eleventh_call_in_the_window_is_the_w19_429_envelope(self, authed):
        oks = 0
        first_429 = None
        for _ in range(_LIMIT_AMOUNT + 3):
            resp, _c, _u, _a, _s = _put(authed, {"ai_sharing_enabled": False}, existing={})
            if resp.status_code == 429:
                first_429 = resp
                break
            assert resp.status_code == 200, resp.text
            oks += 1
        assert oks == _LIMIT_AMOUNT
        assert first_429 is not None
        body = first_429.json()
        assert body["code"] == "RATE_LIMITED"
        v = body.get("retry_after_seconds")
        # slowapi's own formula carries a +1 guard (test_429_contract.py docstring).
        assert isinstance(v, int) and not isinstance(v, bool)
        assert 0 < v <= _WINDOW_SECONDS + 1
        assert int(first_429.headers["Retry-After"]) == v

    def test_supabase_failure_is_500_internal_error(self, authed):
        resp, captured, _u, _a, _s = _put(
            authed,
            {"ai_sharing_enabled": False},
            raise_on_execute=RuntimeError("db down: secret-ish detail"),
        )
        assert resp.status_code == 500, resp.text
        assert resp.json()["code"] == "INTERNAL_ERROR"
        assert "secret-ish" not in resp.text
        assert captured == []

    def test_unauthenticated_is_401_auth_required(self):
        app.dependency_overrides.pop(get_current_user, None)
        with TestClient(app) as tc:
            resp = tc.put(_ROUTE, json={"ai_sharing_enabled": False})
        assert resp.status_code == 401, resp.text
        assert resp.json()["code"] == "AUTH_REQUIRED"


class TestPutPreferencesUnchanged:
    """Regression pin -- ALREADY GREEN at b63a8368 (probe B1) and must stay so:
    this unit does NOT relax ``PUT /preferences`` or ``min_length=1``."""

    def test_empty_priorities_still_422_and_nothing_saved(self, authed):
        with patch(
            "app.api.auth_routes.get_user_preferences",
            new_callable=AsyncMock,
            return_value={"success": True, "preferences": {}, "preferences_completed": False},
        ), patch(
            "app.api.auth_routes.save_user_preferences",
            new_callable=AsyncMock,
            return_value={"success": True, "message": "Preferences saved"},
        ) as save_mock:
            resp = authed.put(
                "/api/v1/auth/preferences",
                json={
                    "priorities": [],
                    "budget": "mid",
                    "lifestyle": [],
                    "brand_attitude": "best_of_both",
                    "ai_sharing_enabled": False,
                },
                headers={"Authorization": "Bearer tok"},
            )
        assert resp.status_code == 422, resp.text
        assert resp.json()["code"] == "VALIDATION_ERROR"
        assert save_mock.await_count == 0

    def test_toggle_only_body_still_422_on_the_full_route(self, authed):
        with patch(
            "app.api.auth_routes.save_user_preferences",
            new_callable=AsyncMock,
            return_value={"success": True},
        ) as save_mock:
            resp = authed.put(
                "/api/v1/auth/preferences",
                json={"ai_sharing_enabled": False},
                headers={"Authorization": "Bearer tok"},
            )
        assert resp.status_code == 422, resp.text
        assert resp.json()["code"] == "VALIDATION_ERROR"
        assert save_mock.await_count == 0
