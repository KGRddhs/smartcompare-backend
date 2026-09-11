"""W3-6 — a password reset that can actually be completed.

Finding ``MB-FLOWS-STATE-02``: "Password reset cannot be completed by any
email/password user (no recovery route, no ``redirect_to``)".

Two halves, both pinned here.

**The email link goes nowhere.** ``auth_service.request_password_reset``
calls ``client.auth.reset_password_email(email)`` with no options, so the
``POST /auth/v1/recover`` it produces carries **no** ``redirect_to`` and
GoTrue sends the user to the project's Site URL after verifying the link —
which is not the app.  MEASURED at base (probe A/B, re-run this session on the
INSTALLED ``supabase-auth`` 2.28.0; ``requirements.txt:158`` pins 2.31.0, so
the wire pin below is written version-agnostically and CI settles it on the
pinned build)::

    A. reset_password_email call args: call('user@test.com')
    B. POST /recover redirect_to=None   body={'email': ..., 'gotrue_meta_security': {...}}
    B. POST /recover redirect_to='qaren://reset-password'  (with options)

The change is gated by ``ENABLE_PASSWORD_RESET_DEEP_LINK`` (default OFF, read
PER CALL) because GoTrue honours ``redirect_to`` only when the value is on the
project's Redirect-URL allow-list — a Supabase dashboard step.  Flag OFF must
stay the byte-identical one-positional call that
``tests/test_auth_interceptor.py:684`` already pins.

**Nothing can spend the token.** ``PUT /auth/password`` requires
``Depends(get_current_user)`` AND the current password, which a user who has
forgotten their password does not have.  The new unauthenticated
``POST /api/v1/auth/password-recovery`` completes the flow: the recovery access
token IS the credential.

Security shape of the new route, each pinned below:

* the token is checked against the LOCAL revocation blacklist FIRST, so a
  spent recovery token cannot be replayed against this route for the rest of
  its upstream lifetime;
* it is then verified UPSTREAM by ``client.auth.get_user(token)``;
* an **AMR gate, fail-closed**, requires ``amr`` to contain a ``recovery``
  method — without it any live session bearer would become a
  "change the password without knowing the current one" door, which is exactly
  what ``PUT /auth/password`` exists to prevent;
* the write reuses the admin call ``change_user_password`` already makes;
* the token is blacklisted the moment it is spent;
* a bad token maps to **400**, never 401 — the client's response interceptor
  (``api.ts:207-209``) starts a refresh on 401, and on an unauthenticated
  device that would emit ``sessionInvalid`` for nothing;
* nothing ever logs the token (``UserDoesntExist(access_token)``'s ``str()``
  IS the bearer on this SDK — the W1-4 lesson).

Free tier: no network.  Every Supabase client is a mock, every env read goes
through ``monkeypatch``.
"""
import base64
import inspect
import json
import logging
import os
import re
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")
os.environ.setdefault("ADMIN_API_KEY", "test-admin-key")

from app.services import auth_service  # noqa: E402

FLAG = "ENABLE_PASSWORD_RESET_DEEP_LINK"
KNOB = "PASSWORD_RESET_REDIRECT_URL"
DEFAULT_REDIRECT = "qaren://reset-password"

ROUTE = "/api/v1/auth/password-recovery"
STRONG = "NewPassw0rd!x"


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def _jwt(payload: dict) -> str:
    """A 3-segment token whose payload segment is UNPADDED base64url.

    GoTrue strips the ``=`` padding, so the decoder has to restore it.  The
    fixtures below assert that at least one segment genuinely needs padding,
    otherwise a padding bug would sail through this file.
    """
    seg = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=")
    return "hdr." + seg.decode() + ".sig"


RECOVERY_TOKEN = _jwt({"sub": "u1", "amr": [{"method": "recovery", "timestamp": 1}]})
PASSWORD_TOKEN = _jwt({"sub": "u1", "amr": [{"method": "password", "timestamp": 1}]})
NO_AMR_TOKEN = _jwt({"sub": "u1"})


def _payload_segment(token: str) -> str:
    return token.split(".")[1]


def _auth_client_returning_user(uid: str = "u1") -> MagicMock:
    client = MagicMock()
    user_response = MagicMock()
    user_response.user.id = uid
    client.auth.get_user.return_value = user_response
    return client


# --------------------------------------------------------------------------
# 1-3 — the redirect_to option, and the flag-OFF byte-identity pin
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_flag_on_sends_the_default_app_redirect(monkeypatch):
    """FLAG ON, knob unset -> the SDK is told to send the user back to the app."""
    monkeypatch.setenv(FLAG, "true")
    monkeypatch.delenv(KNOB, raising=False)

    mock_client = MagicMock()
    with patch.object(auth_service, "get_auth_client", return_value=mock_client):
        result = await auth_service.request_password_reset("u@t.com")

    assert result["success"] is True
    mock_client.auth.reset_password_email.assert_called_once_with(
        "u@t.com", {"redirect_to": DEFAULT_REDIRECT}
    )


@pytest.mark.asyncio
async def test_flag_on_honours_the_redirect_knob(monkeypatch):
    """The knob is what will switch to the universal link with no code change."""
    monkeypatch.setenv(FLAG, "true")
    monkeypatch.setenv(KNOB, "https://qaren.app/reset-password")

    mock_client = MagicMock()
    with patch.object(auth_service, "get_auth_client", return_value=mock_client):
        await auth_service.request_password_reset("u@t.com")

    mock_client.auth.reset_password_email.assert_called_once_with(
        "u@t.com", {"redirect_to": "https://qaren.app/reset-password"}
    )


@pytest.mark.parametrize("value", [None, "false", "0", "no", "off", "garbage", ""])
@pytest.mark.asyncio
async def test_flag_off_is_the_byte_identical_one_positional_call(monkeypatch, value):
    """PRESERVE (green today): flag OFF must call the SDK exactly as base does.

    Duplicates ``tests/test_auth_interceptor.py::test_request_password_reset_success``
    under an EXPLICIT env pop, so a future "always pass options" refactor cannot
    slip through on an environment that happens to have the flag set.
    """
    if value is None:
        monkeypatch.delenv(FLAG, raising=False)
    else:
        monkeypatch.setenv(FLAG, value)
    monkeypatch.delenv(KNOB, raising=False)

    mock_client = MagicMock()
    with patch.object(auth_service, "get_auth_client", return_value=mock_client):
        result = await auth_service.request_password_reset("u@t.com")

    assert result["success"] is True
    mock_client.auth.reset_password_email.assert_called_once_with("u@t.com")


# --------------------------------------------------------------------------
# 4 — library contract pin (green today, version-agnostic)
# --------------------------------------------------------------------------

def test_redirect_to_option_becomes_the_recover_query_param():
    """PIN on the SDK, not on our code: the option name matches the INSTALLED
    supabase-auth, whatever version is present (2.28.0 locally, 2.31.0 in CI).

    Also guards the flow: ``reset_password_for_email`` must send NO PKCE
    ``code_challenge``.  If it ever does, GoTrue redirects with ``?code=`` and
    the implicit-flow fragment this unit's client parser reads never arrives —
    a red here is a STOP-and-re-spec, never a loosened assertion.
    """
    from supabase_auth._sync.gotrue_client import SyncGoTrueClient

    recorded = []

    def _fake_request(self, method, path, **kwargs):
        recorded.append((method, path, kwargs.get("redirect_to"), kwargs.get("body")))
        return MagicMock()

    with patch.object(SyncGoTrueClient, "_request", _fake_request):
        client = SyncGoTrueClient(url="https://example.invalid/auth/v1", headers={})
        client.reset_password_email("u@t.com", {"redirect_to": DEFAULT_REDIRECT})

    assert len(recorded) == 1, recorded
    method, path, redirect_to, body = recorded[0]
    assert (method, path, redirect_to) == ("POST", "recover", DEFAULT_REDIRECT)
    assert not (body or {}).get("code_challenge"), (
        "the recover link became a PKCE link -- the client parser reads an "
        "implicit-flow fragment and cannot complete a ?code= flow"
    )


# --------------------------------------------------------------------------
# 5-9 — the new route
# --------------------------------------------------------------------------

def _post(json_body):
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as client:
        return client.post(ROUTE, json=json_body)


def test_route_accepts_a_recovery_completion_and_returns_success():
    with patch(
        "app.api.auth_routes.complete_password_recovery",
        new=AsyncMock(return_value={"success": True, "message": "Password updated"}),
    ):
        response = _post({"access_token": "x" * 32, "new_password": STRONG})

    assert response.status_code == 200, response.text
    assert response.json()["success"] is True


def test_a_bad_recovery_token_is_400_with_a_TOP_LEVEL_code():
    """400, not 401 (the client's 401 interceptor would start a refresh on an
    unauthenticated device), and the code must survive the unified envelope --
    ``body["code"]``, never ``body["detail"]["code"]``.
    """
    with patch(
        "app.api.auth_routes.complete_password_recovery",
        new=AsyncMock(
            return_value={
                "success": False,
                "code": "RECOVERY_TOKEN_INVALID",
                "error": "This reset link is no longer valid.",
            }
        ),
    ):
        response = _post({"access_token": "x" * 32, "new_password": STRONG})

    assert response.status_code == 400, response.text
    body = response.json()
    assert body["code"] == "RECOVERY_TOKEN_INVALID", body
    assert body["error"] == "This reset link is no longer valid."


@pytest.mark.parametrize(
    "payload",
    [
        {"access_token": "x" * 32, "new_password": "short1"},
        {"access_token": "x" * 32, "new_password": "nouppercase1234"},
        {"access_token": "x" * 32, "new_password": "NOLOWERCASE1234"},
        {"access_token": "x" * 32, "new_password": "NoDigitsAtAllHere"},
        {"new_password": STRONG},
        {"access_token": "x" * 32},
    ],
)
def test_weak_or_missing_fields_are_rejected_before_any_service_call(payload):
    """The password rule is the ONE shared ``_validate_password_strength``
    (``auth_routes.py:66``) that Register and ChangePassword already use."""
    service = AsyncMock(return_value={"success": True, "message": "Password updated"})
    with patch("app.api.auth_routes.complete_password_recovery", new=service):
        response = _post(payload)

    assert response.status_code == 422, response.text
    service.assert_not_called()


def test_route_table_has_password_recovery_and_still_no_reset_password():
    from app.api.auth_routes import router

    paths = [route.path for route in router.routes]
    # PRESERVE (green today): test_auth_interceptor.py:1626 pins this absence.
    assert "/api/v1/auth/reset-password" not in paths
    assert ROUTE in paths, paths


def test_password_recovery_is_rate_limited_at_the_put_password_tier():
    source = Path("app/api/auth_routes.py").read_text(encoding="utf-8")
    lines = source.splitlines()
    indexes = [i for i, line in enumerate(lines) if line.startswith("async def password_recovery(")]
    assert indexes, "no `async def password_recovery(` in app/api/auth_routes.py"

    preceding = lines[max(0, indexes[0] - 3): indexes[0]]
    assert any('@limiter.limit("5/minute")' in line for line in preceding), preceding


# --------------------------------------------------------------------------
# 10 — the service happy path
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_complete_password_recovery_verifies_then_writes_then_burns(monkeypatch):
    auth_client = _auth_client_returning_user("u1")
    admin_client = MagicMock()

    manager = Mock()
    manager.attach_mock(auth_client.auth.get_user, "get_user")
    manager.attach_mock(admin_client.auth.admin.update_user_by_id, "update_user_by_id")

    revoke = Mock()
    monkeypatch.setattr(auth_service, "get_auth_client", lambda: auth_client)
    monkeypatch.setattr(auth_service, "get_admin_client", lambda: admin_client)
    monkeypatch.setattr(auth_service, "_revoke_token", revoke)
    monkeypatch.setattr(auth_service, "_is_token_revoked", lambda _t: False)

    result = await auth_service.complete_password_recovery(RECOVERY_TOKEN, STRONG)

    assert result["success"] is True, result
    auth_client.auth.get_user.assert_called_once_with(RECOVERY_TOKEN)
    admin_client.auth.admin.update_user_by_id.assert_called_once_with(
        "u1", {"password": STRONG}
    )
    revoke.assert_called_once_with(RECOVERY_TOKEN)

    ordered = [name for name, _args, _kwargs in manager.mock_calls]
    assert ordered == ["get_user", "update_user_by_id"], (
        "the password must never be written before the token is verified upstream"
    )


def test_the_amr_fixture_really_needs_base64_padding_restored():
    """Guards the guard: if every fixture happened to be 4-byte aligned, a
    decoder that forgot to re-pad would still pass the AMR tests."""
    unaligned = [
        t for t in (RECOVERY_TOKEN, PASSWORD_TOKEN, NO_AMR_TOKEN)
        if len(_payload_segment(t)) % 4 != 0
    ]
    assert unaligned, "no fixture exercises unpadded base64url"


# --------------------------------------------------------------------------
# 11-13, 16 — every rejection path, fail-closed
# --------------------------------------------------------------------------

def _patched_service(monkeypatch, auth_client, admin_client, revoked=False):
    revoke = Mock()
    monkeypatch.setattr(auth_service, "get_auth_client", lambda: auth_client)
    monkeypatch.setattr(auth_service, "get_admin_client", lambda: admin_client)
    monkeypatch.setattr(auth_service, "_revoke_token", revoke)
    monkeypatch.setattr(auth_service, "_is_token_revoked", lambda _t: revoked)
    return revoke


@pytest.mark.asyncio
async def test_a_locally_revoked_token_is_refused_before_any_upstream_call(monkeypatch):
    """The route must consult the blacklist ITSELF.

    ``_revoke_token`` only protects ``verify_token`` callers, so without this
    check the SAME recovery token could be replayed against this route for its
    whole upstream lifetime -- and whether GoTrue invalidates it on use is
    UNMEASURED (no network).  Fail-closed here costs nothing.
    """
    auth_client = _auth_client_returning_user()
    admin_client = MagicMock()
    _patched_service(monkeypatch, auth_client, admin_client, revoked=True)

    result = await auth_service.complete_password_recovery(RECOVERY_TOKEN, STRONG)

    assert result["success"] is False
    assert result["code"] == "RECOVERY_TOKEN_INVALID"
    auth_client.auth.get_user.assert_not_called()
    admin_client.auth.admin.update_user_by_id.assert_not_called()


@pytest.mark.asyncio
async def test_an_invalid_token_raising_upstream_is_refused(monkeypatch):
    auth_client = MagicMock()
    auth_client.auth.get_user.side_effect = Exception("invalid JWT")
    admin_client = MagicMock()
    revoke = _patched_service(monkeypatch, auth_client, admin_client)

    result = await auth_service.complete_password_recovery(RECOVERY_TOKEN, STRONG)

    assert result["success"] is False
    assert result["code"] == "RECOVERY_TOKEN_INVALID", result
    admin_client.auth.admin.update_user_by_id.assert_not_called()
    revoke.assert_not_called()


@pytest.mark.asyncio
async def test_a_token_with_no_user_upstream_is_refused(monkeypatch):
    auth_client = MagicMock()
    auth_client.auth.get_user.return_value = None
    admin_client = MagicMock()
    revoke = _patched_service(monkeypatch, auth_client, admin_client)

    result = await auth_service.complete_password_recovery(RECOVERY_TOKEN, STRONG)

    assert result["success"] is False
    assert result["code"] == "RECOVERY_TOKEN_INVALID", result
    admin_client.auth.admin.update_user_by_id.assert_not_called()
    revoke.assert_not_called()


@pytest.mark.parametrize(
    "token,label",
    [
        (PASSWORD_TOKEN, "an ordinary password session"),
        (NO_AMR_TOKEN, "a token with no amr claim at all"),
        ("not-a-jwt", "a non-JWT string"),
        ("hdr.!!!not-base64!!!.sig", "an undecodable payload segment"),
    ],
)
@pytest.mark.asyncio
async def test_the_amr_gate_fails_closed(monkeypatch, token, label):
    """Only a session minted from a RECOVERY link may rotate the password.

    ``PUT /auth/password`` exists precisely so a stolen bearer cannot change a
    password without the current one; a recovery endpoint that accepted ANY
    live session token would re-open that door.
    """
    auth_client = _auth_client_returning_user()
    admin_client = MagicMock()
    revoke = _patched_service(monkeypatch, auth_client, admin_client)

    result = await auth_service.complete_password_recovery(token, STRONG)

    assert result["success"] is False, label
    assert result["code"] == "RECOVERY_TOKEN_INVALID", (label, result)
    admin_client.auth.admin.update_user_by_id.assert_not_called()
    revoke.assert_not_called()


@pytest.mark.asyncio
async def test_the_amr_rejection_logs_the_method_names_and_never_the_token(
    monkeypatch, caplog
):
    """The first canary reset is the measurement for the ``amr`` claim shape,
    so the rejection has to say what it actually saw -- method names only."""
    auth_client = _auth_client_returning_user()
    admin_client = MagicMock()
    _patched_service(monkeypatch, auth_client, admin_client)

    with caplog.at_level(logging.WARNING, logger="app.services.auth_service"):
        await auth_service.complete_password_recovery(PASSWORD_TOKEN, STRONG)

    emitted = "\n".join(record.getMessage() for record in caplog.records)
    assert "amr=" in emitted, emitted
    assert "password" in emitted, emitted
    assert PASSWORD_TOKEN not in emitted, "THE RECOVERY TOKEN LEAKED INTO THE LOGS"
    assert _payload_segment(PASSWORD_TOKEN) not in emitted


@pytest.mark.asyncio
async def test_the_token_is_scrubbed_out_of_an_exception_message(monkeypatch, caplog):
    """``UserDoesntExist(access_token)``'s ``str()`` IS the bearer on this SDK
    (W1-4).  Anything derived from ``str(e)`` must be scrubbed before it is
    logged."""
    auth_client = MagicMock()
    auth_client.auth.get_user.side_effect = Exception(RECOVERY_TOKEN)
    admin_client = MagicMock()
    _patched_service(monkeypatch, auth_client, admin_client)

    with caplog.at_level(logging.DEBUG, logger="app.services.auth_service"):
        result = await auth_service.complete_password_recovery(RECOVERY_TOKEN, STRONG)

    assert result["success"] is False
    assert RECOVERY_TOKEN not in caplog.text, (
        "THE RECOVERY TOKEN LEAKED INTO THE LOGS: " + caplog.text[:300]
    )
    assert _payload_segment(RECOVERY_TOKEN) not in caplog.text


# --------------------------------------------------------------------------
# 15 — both predicates are read PER CALL
# --------------------------------------------------------------------------

def test_both_predicates_are_read_per_call_never_cached_at_import(monkeypatch):
    """Railway must be able to flip these without a restart (the
    ``price_service.exact_gate_enabled`` idiom).  No ``importlib.reload`` here
    -- the W0-3 lesson: reloading a real module rebinds it under every
    ``from X import y`` importer."""
    monkeypatch.setenv(FLAG, "true")
    assert auth_service.password_reset_deep_link_enabled() is True

    monkeypatch.setenv(FLAG, "false")
    assert auth_service.password_reset_deep_link_enabled() is False

    monkeypatch.delenv(FLAG, raising=False)
    assert auth_service.password_reset_deep_link_enabled() is False

    monkeypatch.delenv(KNOB, raising=False)
    assert auth_service.password_reset_redirect_url() == DEFAULT_REDIRECT

    monkeypatch.setenv(KNOB, "https://qaren.app/reset-password")
    assert auth_service.password_reset_redirect_url() == "https://qaren.app/reset-password"

    monkeypatch.setenv(KNOB, "   ")
    assert auth_service.password_reset_redirect_url() == DEFAULT_REDIRECT


def test_neither_predicate_captures_the_env_at_module_scope():
    """Source-level guard: an ``os.getenv`` at module scope would make the flag
    un-flippable, and the unit test above could still pass on a fresh import."""
    source = inspect.getsource(auth_service)
    for name in ("password_reset_deep_link_enabled", "password_reset_redirect_url"):
        assert re.search(r"^def %s\(" % name, source, re.M), f"{name} is not defined"
        body = source.split("def %s(" % name, 1)[1].split("\ndef ", 1)[0]
        assert "os.getenv" in body, f"{name} does not read the env per call"
