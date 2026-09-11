"""W3-3 — MB-NETWORK-CONTRACT-03, backend half.

THE DEFECT (measured at ed75dc70 / b63a8368)
``POST /api/v1/auth/social-login`` (``app/api/auth_routes.py:849-856``) accepts
``request`` only because slowapi needs it and never reads it.
``grep -c device_fingerprint app/services/auth_service.py`` = 0, and
``sign_in_with_social`` inserts only ``{id, email, auth_provider,
subscription_tier}`` for a new user, so the ONLY writer of
``users.device_fingerprint_hash`` in the codebase is the register block at
``auth_routes.py:444-472``. Every user who arrived through Google or Apple has
``device_fingerprint_hash = NULL``, and both consumers fail OPEN on that NULL:
``referral_service._referrer_device_lifetime_count`` (``if not fp: return 0`` →
the 3-per-device LIFETIME cap is never reached for social referrers) and
``abuse_detection_service.evaluate_invite`` (``is_same_device`` False).

THE FIX this file pins is gated: ``ENABLE_SOCIAL_DEVICE_FINGERPRINT``, default
OFF, read per call (the ``strict_optional_auth_enabled`` idiom at
``auth_routes.py:317-349``).

RED here: B1, B2.
PINS (green today AND after the fix, each with a named mutation): B3, B4, B5,
B6, B7. B8 (the register regression) is NOT re-implemented here — it is the two
EXISTING tests
``tests/test_auth_routes_invite_fingerprint.py::test_register_with_fingerprint_inherits_lifetime_counter``
and ``::test_register_without_fingerprint_does_not_update_user``, which encode
the exact chain order the helper extraction must preserve and must stay green
UNCHANGED; re-asserting them here would be decoration.

Harness per RULING R3: ``admin.table`` pops SEPARATE ``MagicMock`` chains from a
list, because the single-shared-chain idiom of
``test_auth_routes_invite_fingerprint.py:170-215`` cannot tell the own-row SELECT
from the device-max SELECT. This file is NOT in
``tests/conftest.py::_RATE_LIMITER_BYPASS_TEST_FILES``, so it carries its own
autouse limiter fixture (copied from ``tests/test_social_login_smoke.py:23-30``).
"""
import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app

FLAG = "ENABLE_SOCIAL_DEVICE_FINGERPRINT"
FP = "a" * 64
UID = "00000000-0000-0000-0000-000000000001"

SUCCESS = {
    "success": True,
    "user": {
        "id": UID,
        "email": "u@gmail.com",
        "preferences_completed": False,
    },
    "session": {
        "access_token": "supabase-access-token",
        "refresh_token": "supabase-refresh-token",
        "expires_at": 1234567890,
    },
    "message": "Signed in with google",
}

GOOGLE_BODY = {"provider": "google", "id_token": "header.payload.signature"}


# Bypass slowapi rate limit (10/min on /social-login).
@pytest.fixture(autouse=True)
def _disable_limiter():
    from app.middleware.rate_limiter import limiter

    prior = limiter.enabled
    limiter.enabled = False
    yield
    limiter.enabled = prior


@pytest.fixture(autouse=True)
def _clean_flag(monkeypatch):
    """Every test states its own flag value; never inherit the ambient env."""
    monkeypatch.delenv(FLAG, raising=False)
    yield


def _select_chain(rows):
    """A chain whose select/eq/order/limit all return itself, execute -> rows."""
    chain = MagicMock()
    for method in ("select", "eq", "order", "limit"):
        getattr(chain, method).return_value = chain
    chain.execute.return_value = MagicMock(data=rows)
    return chain


def _update_chain():
    """A chain that RECORDS the dict handed to .update()."""
    chain = MagicMock()
    captured = {}

    def _update(data):
        captured.update(data)
        return chain

    chain.update = MagicMock(side_effect=_update)
    chain.eq.return_value = chain
    chain.execute.return_value = MagicMock(data=[{"id": UID}])
    return chain, captured


class _Admin:
    """Records every table() name and hands out the next prepared chain."""

    def __init__(self, chains):
        self.tables = []
        self._chains = list(chains)
        self.client = MagicMock()
        self.client.table.side_effect = self._table

    def _table(self, name):
        self.tables.append(name)
        if not self._chains:
            raise AssertionError(
                f"unexpected extra table({name!r}) call; tables so far={self.tables}"
            )
        return self._chains.pop(0)


def _post(headers=None, service_result=None):
    """Drive POST /auth/social-login with sign_in_with_social patched."""
    with patch(
        "app.api.auth_routes.sign_in_with_social",
        new=AsyncMock(return_value=service_result if service_result is not None else SUCCESS),
    ):
        return TestClient(app).post(
            "/api/v1/auth/social-login",
            json=GOOGLE_BODY,
            headers=headers or {},
        )


# ---------------------------------------------------------------- RED -------


def test_b1_flag_on_writes_hash_and_inherits_device_counter(monkeypatch):
    """B1 (RED at base): flag ON + valid header + NULL own hash -> the route
    binds the device and inherits the device maximum.

    Measured at base: get_admin_supabase_client calls=0, tables=[],
    update_called=False. Mutation that reddens this after the fix: remove the
    gated ``_apply_social_device_fingerprint`` call in ``social_login``.
    """
    monkeypatch.setenv(FLAG, "true")
    own = _select_chain([{"device_fingerprint_hash": None, "lifetime_comparisons_used": 0}])
    device = _select_chain([{"lifetime_comparisons_used": 3}])
    upd, captured = _update_chain()
    admin = _Admin([own, device, upd])

    with patch(
        "app.api.auth_routes.get_admin_supabase_client", return_value=admin.client
    ) as get_admin:
        resp = _post(headers={"X-Device-Fingerprint": FP})

    assert resp.status_code == 200, resp.text
    assert resp.json() == SUCCESS, "the response body must not change in either flag state"
    assert get_admin.call_count == 1
    assert admin.tables == ["users", "users", "users"]
    assert upd.update.called, "social-login never wrote device_fingerprint_hash"
    assert captured == {"device_fingerprint_hash": FP, "lifetime_comparisons_used": 3}
    upd.eq.assert_called_once_with("id", UID)


def test_b2_flag_on_never_lowers_an_existing_counter(monkeypatch):
    """B2 (RED at base): own=5, device max=3 -> writes 5, not 3.

    HAZARD H1. Reusing the register block verbatim would compute ``inherited``
    ONLY from OTHER rows carrying this fp (the caller's own row has a NULL hash
    so it can never match) and then OVERWRITE ``lifetime_comparisons_used`` with
    it -- handing a returning social user with used=5 a fresh free quota on
    every login, the exact opposite of the finding. ``max(own, device-max)`` is
    monotone and is identical to register's semantics for a NEW row (own=0).

    Mutation that reddens this after the fix: reuse the register block verbatim
    (it writes 3).
    """
    monkeypatch.setenv(FLAG, "true")
    own = _select_chain([{"device_fingerprint_hash": None, "lifetime_comparisons_used": 5}])
    device = _select_chain([{"lifetime_comparisons_used": 3}])
    upd, captured = _update_chain()
    admin = _Admin([own, device, upd])

    with patch("app.api.auth_routes.get_admin_supabase_client", return_value=admin.client):
        resp = _post(headers={"X-Device-Fingerprint": FP})

    assert resp.status_code == 200, resp.text
    assert captured.get("device_fingerprint_hash") == FP
    assert captured.get("lifetime_comparisons_used") == 5


# --------------------------------------------------------------- PINS -------


def test_b3_pin_never_rebinds_a_row_that_already_has_a_hash(monkeypatch):
    """B3 (pin): first-device binding is permanent (RULING R7).

    Always-overwriting would let a referrer move its hash off a saturated device
    by reinstalling (the nonce resets on uninstall), defeating both
    ``_referrer_device_lifetime_count`` and SAME_DEVICE. Exactly ONE table()
    call: the own-row SELECT, then return.

    Mutation that reddens this: drop the NULL check (the device SELECT + the
    UPDATE then run, taking table() to 3).

    Bound, not equality, deliberately: RULING R3 says this case makes exactly
    ONE table() call after the fix, but the base makes ZERO (nothing reads the
    header at all) and 5/7/R14 all require B3 to be green BEFORE and after.
    ``<= 1`` is the strongest assertion true in both states, and it is what the
    named mutation trips. Tighten to ``== 1`` in the green phase.
    """
    monkeypatch.setenv(FLAG, "true")
    own = _select_chain(
        [{"device_fingerprint_hash": "f" * 64, "lifetime_comparisons_used": 2}]
    )
    admin = _Admin([own])

    with patch("app.api.auth_routes.get_admin_supabase_client", return_value=admin.client):
        resp = _post(headers={"X-Device-Fingerprint": FP})

    assert resp.status_code == 200, resp.text
    assert resp.json() == SUCCESS
    assert admin.client.table.call_count <= 1, admin.tables
    assert not own.update.called


@pytest.mark.parametrize("bad_fp", ["z" * 64, "a" * 63, "A" * 64, ""])
def test_b4_pin_malformed_fingerprint_never_touches_the_database(monkeypatch, bad_fp):
    """B4 (pin): the social path applies ``_DEVICE_FINGERPRINT_RE`` exactly as
    register does, so a forged/garbage header cannot poison the Migration 021
    counter -- and costs zero DB work.

    Mutation that reddens this: skip ``_DEVICE_FINGERPRINT_RE`` on the social
    path.
    """
    monkeypatch.setenv(FLAG, "true")
    admin = _Admin([])

    with patch(
        "app.api.auth_routes.get_admin_supabase_client", return_value=admin.client
    ) as get_admin:
        resp = _post(headers={"X-Device-Fingerprint": bad_fp})

    assert resp.status_code == 200, resp.text
    assert get_admin.call_count == 0
    assert admin.tables == []


@pytest.mark.parametrize("flag_value", [None, "false"])
def test_b5_pin_flag_off_is_byte_identical(monkeypatch, flag_value):
    """B5 (byte-identity pin): with the flag UNSET or "false" the route executes
    exactly today's four statements -- no admin client, no DB call, and the
    response body is the mocked payload verbatim (no ``is_new_user``-style key
    creeps in).

    "request.headers never consulted" is not observable through TestClient; the
    real invariant is the admin-call count (RULING R5).

    Mutation that reddens this: drop the flag check.
    """
    if flag_value is None:
        monkeypatch.delenv(FLAG, raising=False)
    else:
        monkeypatch.setenv(FLAG, flag_value)
    admin = _Admin([])

    with patch(
        "app.api.auth_routes.get_admin_supabase_client", return_value=admin.client
    ) as get_admin:
        resp = _post(headers={"X-Device-Fingerprint": FP})

    assert resp.status_code == 200, resp.text
    assert resp.json() == SUCCESS
    assert get_admin.call_count == 0
    assert admin.tables == []


def test_b6_pin_a_database_failure_never_breaks_sign_in(monkeypatch):
    """B6a (pin): the apply leg is best-effort -- it never raises and never
    touches the response body.

    Mutation that reddens this: remove the try/except (the RuntimeError then
    escapes the route and the client sees 500 instead of 200).
    """
    monkeypatch.setenv(FLAG, "true")

    with patch(
        "app.api.auth_routes.get_admin_supabase_client",
        side_effect=RuntimeError("supabase down"),
    ):
        resp = _post(headers={"X-Device-Fingerprint": FP})

    assert resp.status_code == 200, resp.text
    assert resp.json() == SUCCESS


def test_b6_failure_is_reported_at_warning(monkeypatch, caplog):
    """B6b (RED at base): a swallowed failure must still be VISIBLE.

    Split out of B6 deliberately. 5 labels B6 "pin, green today (trivially)",
    but only its 200/body half is trivially green: the log line
    ``device-fp social apply failed`` describes behaviour that does not exist at
    base (``get_admin_supabase_client`` is never called from ``social_login``,
    so caplog.records is empty), which makes THIS half a red test, not a pin.

    Mutation that reddens this after the fix: swallow the exception silently
    (``except Exception: pass``).
    """
    monkeypatch.setenv(FLAG, "true")

    with caplog.at_level(logging.WARNING, logger="app.api.auth_routes"):
        with patch(
            "app.api.auth_routes.get_admin_supabase_client",
            side_effect=RuntimeError("supabase down"),
        ):
            resp = _post(headers={"X-Device-Fingerprint": FP})

    assert resp.status_code == 200, resp.text
    assert any(
        "device-fp social apply failed" in record.getMessage()
        for record in caplog.records
    ), [r.getMessage() for r in caplog.records]


def test_b7_pin_a_rejected_login_never_reaches_the_database(monkeypatch):
    """B7 (pin): the apply call sits AFTER the 401 raise, so a failed social
    login costs no DB work and still returns 401.

    Mutation that reddens this: apply before the success check.
    """
    monkeypatch.setenv(FLAG, "true")
    admin = _Admin([])

    with patch(
        "app.api.auth_routes.get_admin_supabase_client", return_value=admin.client
    ) as get_admin:
        resp = _post(
            headers={"X-Device-Fingerprint": FP},
            service_result={"success": False, "error": "x"},
        )

    assert resp.status_code == 401, resp.text
    assert get_admin.call_count == 0
    assert admin.tables == []
