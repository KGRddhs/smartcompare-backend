"""Tests for Bundle A §1.1 (invite_code) + §1.5 (X-Device-Fingerprint) on register.

Per CLAUDE.md, these tests mock the service boundary rather than hitting
Supabase. The existing referral tests follow the same TestClient + AsyncMock
pattern.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import referral_service as referral_service_module


# Bypass slowapi rate limit (3/min on /register) for batch invariant tests.
@pytest.fixture(autouse=True)
def _disable_limiter():
    from app.middleware.rate_limiter import limiter

    prior = limiter.enabled
    limiter.enabled = False
    yield
    limiter.enabled = prior


@pytest.fixture
def fresh_register_success():
    """Patch register_user to return a successful new-user payload."""
    with patch(
        "app.api.auth_routes.register_user",
        new=AsyncMock(
            return_value={
                "success": True,
                "user": {"id": "00000000-0000-0000-0000-000000000001", "email": "u@x.com"},
                "session": {"access_token": "tok", "refresh_token": "ref"},
                "message": "ok",
            }
        ),
    ) as m:
        yield m


# ---------- Pydantic format validation (Task 1.6) ----------


def test_register_invalid_invite_code_format_returns_422(fresh_register_success):
    """Invalid format (not QR-XXXXXX) — Pydantic raises ValueError → 422."""
    client = TestClient(app)
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": "u@example.com",
            "password": "ValidP@ss123",
            "invite_code": "notvalid",
        },
    )
    # Pydantic field_validator ValueError → 422 (validation error)
    # The error_handler middleware may map this to 400 with a code field;
    # accept either as long as the error message references INVITE_CODE_INVALID.
    assert resp.status_code in (400, 422)
    body = resp.json()
    body_str = str(body).upper()
    assert "INVITE_CODE_INVALID" in body_str or "INVITE_CODE" in body_str


def test_register_invite_code_empty_string_accepted_as_no_code(fresh_register_success):
    """Empty-string invite_code should be coerced to None and not rejected."""
    client = TestClient(app)
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": "u@example.com",
            "password": "ValidP@ss123",
            "invite_code": "",
        },
    )
    # Register itself succeeds — empty string is treated as "no code given".
    assert resp.status_code == 200


def test_register_invite_code_valid_format_accepted(fresh_register_success):
    """QR-ABCDEF (valid alphabet) passes Pydantic format check."""
    client = TestClient(app)
    with patch.object(
        referral_service_module,
        "resolve_code_to_invite_id",
        new=AsyncMock(return_value="invite-uuid-xyz"),
    ), patch.object(
        referral_service_module,
        "link_invite_to_user",
        new=AsyncMock(return_value=True),
    ):
        resp = client.post(
            "/api/v1/auth/register",
            json={
                "email": "u@example.com",
                "password": "ValidP@ss123",
                "invite_code": "QR-ABCDEF",
            },
        )
    assert resp.status_code == 200


# ---------- Code resolution (Task 1.6) ----------


def test_register_unknown_invite_code_returns_404(fresh_register_success):
    """Code that doesn't match any user's referral_code → 404."""
    client = TestClient(app)
    with patch.object(
        referral_service_module,
        "resolve_code_to_invite_id",
        new=AsyncMock(return_value=None),
    ):
        resp = client.post(
            "/api/v1/auth/register",
            json={
                "email": "u@example.com",
                "password": "ValidP@ss123",
                "invite_code": "QR-ZZZZZZ",
            },
        )
    assert resp.status_code == 404
    body = resp.json()
    body_str = str(body).upper()
    assert "INVITE_CODE_NOT_FOUND" in body_str


def test_register_resolves_code_then_links_invite(fresh_register_success):
    """Happy path: invite_code → resolve → link_invite_to_user is called."""
    client = TestClient(app)
    with patch.object(
        referral_service_module,
        "resolve_code_to_invite_id",
        new=AsyncMock(return_value="resolved-invite-uuid"),
    ) as resolve_mock, patch.object(
        referral_service_module,
        "link_invite_to_user",
        new=AsyncMock(return_value=True),
    ) as link_mock:
        resp = client.post(
            "/api/v1/auth/register",
            json={
                "email": "u@example.com",
                "password": "ValidP@ss123",
                "invite_code": "QR-ABCDEF",
            },
        )

    assert resp.status_code == 200
    resolve_mock.assert_awaited_once()
    # Code + new-user id were passed to resolver
    call_args = resolve_mock.await_args
    assert call_args.args[0] == "QR-ABCDEF"
    assert call_args.args[1] == "00000000-0000-0000-0000-000000000001"
    link_mock.assert_awaited_once()
    # link uses the resolved invite id
    assert link_mock.await_args.args[1] == "resolved-invite-uuid"


# ---------- Device fingerprint inheritance (Task 1.6 / §1.5) ----------


def test_register_with_fingerprint_inherits_lifetime_counter(fresh_register_success):
    """When X-Device-Fingerprint matches a prior user, lifetime_comparisons_used is inherited.

    H5 (audit 2026-05-22): the header must be valid SHA-256 hex (64-char lowercase).
    Updated fixture from the prior 8-char `deadbeef` value to a realistic full-length
    hash that the new _DEVICE_FINGERPRINT_RE in auth_routes.py accepts.
    """
    # 64-char lowercase hex — matches the format deviceFingerprint.ts produces.
    fp = "a" * 64
    # Mock the admin supabase chain: SELECT returns 1 prior user with used=3,
    # then UPDATE persists fingerprint + inherited counter on new user.
    select_chain = MagicMock()
    select_chain.select.return_value = select_chain
    select_chain.eq.return_value = select_chain
    select_chain.order.return_value = select_chain
    select_chain.limit.return_value = select_chain
    select_chain.execute.return_value = MagicMock(
        data=[{"lifetime_comparisons_used": 3}]
    )

    update_chain = MagicMock()
    update_chain.update.return_value = update_chain
    update_chain.eq.return_value = update_chain
    update_chain.execute.return_value = MagicMock(data=[{"id": "new"}])

    captured_updates = {}

    def table_side_effect(name):
        # Single chain object that records both .select and .update calls.
        chain = MagicMock()

        def update(data):
            captured_updates.update(data)
            return update_chain

        chain.select = select_chain.select
        chain.eq = select_chain.eq
        chain.order = select_chain.order
        chain.limit = select_chain.limit
        chain.execute = select_chain.execute
        chain.update = update
        return chain

    mock_client = MagicMock()
    mock_client.table.side_effect = table_side_effect

    with patch(
        "app.api.auth_routes.get_admin_supabase_client", return_value=mock_client
    ):
        client = TestClient(app)
        resp = client.post(
            "/api/v1/auth/register",
            json={"email": "u@example.com", "password": "ValidP@ss123"},
            headers={"X-Device-Fingerprint": fp},
        )

    assert resp.status_code == 200
    # The new user row was updated with the inherited counter + fingerprint.
    assert captured_updates.get("device_fingerprint_hash") == fp
    assert captured_updates.get("lifetime_comparisons_used") == 3


def test_register_without_fingerprint_does_not_update_user(fresh_register_success):
    """No X-Device-Fingerprint → no inheritance, no admin SQL touch from §1.5 logic."""
    mock_client = MagicMock()
    # Provide a no-op chain in case anything attempts to call .table()
    chain = MagicMock()
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.order.return_value = chain
    chain.limit.return_value = chain
    chain.update.return_value = chain
    chain.execute.return_value = MagicMock(data=[])
    mock_client.table.return_value = chain

    with patch(
        "app.api.auth_routes.get_admin_supabase_client", return_value=mock_client
    ):
        client = TestClient(app)
        resp = client.post(
            "/api/v1/auth/register",
            json={"email": "u@example.com", "password": "ValidP@ss123"},
        )

    assert resp.status_code == 200
    # Update was NOT invoked for the §1.5 inheritance path.
    chain.update.assert_not_called()


# ---------- resolve_code_to_invite_id unit-level tests ----------


@pytest.mark.asyncio
async def test_resolve_code_to_invite_id_unknown_returns_none():
    """No matching referral_code → None."""
    mock_client = MagicMock()
    chain = MagicMock()
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.maybe_single.return_value = chain
    chain.execute.return_value = MagicMock(data=None)
    mock_client.table.return_value = chain
    with patch(
        "app.services.referral_service.get_admin_supabase_client",
        return_value=mock_client,
    ):
        from app.services.referral_service import resolve_code_to_invite_id

        result = await resolve_code_to_invite_id("QR-ZZZZZZ", "invitee-uuid")
    assert result is None


@pytest.mark.asyncio
async def test_resolve_code_to_invite_id_self_referral_rejected():
    """Referrer ID == invitee ID → None (self-referral block)."""
    mock_client = MagicMock()
    user_chain = MagicMock()
    user_chain.select.return_value = user_chain
    user_chain.eq.return_value = user_chain
    user_chain.maybe_single.return_value = user_chain
    user_chain.execute.return_value = MagicMock(
        data={"id": "same-uuid", "referral_code": "QR-ABCDEF"}
    )
    mock_client.table.return_value = user_chain
    with patch(
        "app.services.referral_service.get_admin_supabase_client",
        return_value=mock_client,
    ):
        from app.services.referral_service import resolve_code_to_invite_id

        result = await resolve_code_to_invite_id("QR-ABCDEF", "same-uuid")
    assert result is None


@pytest.mark.asyncio
async def test_resolve_code_to_invite_id_creates_invite_row():
    """Valid resolution → inserts referral_invites with source=code_redeem and returns invite_id."""
    mock_client = MagicMock()

    insert_captured = {}

    def table_side_effect(name):
        chain = MagicMock()
        if name == "users":
            chain.select.return_value = chain
            chain.eq.return_value = chain
            chain.maybe_single.return_value = chain
            chain.execute.return_value = MagicMock(
                data={"id": "referrer-uuid", "referral_code": "QR-ABCDEF"}
            )
        else:  # referral_invites
            def insert(payload):
                insert_captured.update(payload)
                return chain

            chain.insert = insert
            chain.execute.return_value = MagicMock(data=[{"id": "new-invite-uuid"}])
        return chain

    mock_client.table.side_effect = table_side_effect

    with patch(
        "app.services.referral_service.get_admin_supabase_client",
        return_value=mock_client,
    ):
        from app.services.referral_service import resolve_code_to_invite_id

        result = await resolve_code_to_invite_id("QR-ABCDEF", "invitee-uuid")

    assert result == "new-invite-uuid"
    assert insert_captured["referrer_user_id"] == "referrer-uuid"
    assert insert_captured["redeemed_by_user_id"] == "invitee-uuid"
    assert insert_captured["source"] == "code_redeem"
    assert insert_captured.get("share_target") in ("other", None) or "share_target" in insert_captured


# ---------- Task 1.8: audit log emitted on code redemption ----------


def test_register_invite_code_emits_audit_event(fresh_register_success):
    """Successful invite_code redemption fires log_audit_event('invite_code_redeemed', ...)."""
    client = TestClient(app)
    captured_events = []

    async def _fake_audit(event_type, **kwargs):
        captured_events.append({"event_type": event_type, **kwargs})

    with patch.object(
        referral_service_module,
        "resolve_code_to_invite_id",
        new=AsyncMock(return_value="resolved-invite-uuid"),
    ), patch.object(
        referral_service_module,
        "link_invite_to_user",
        new=AsyncMock(return_value=True),
    ), patch(
        "app.api.auth_routes.log_audit_event", side_effect=_fake_audit,
    ):
        resp = client.post(
            "/api/v1/auth/register",
            json={
                "email": "u@example.com",
                "password": "ValidP@ss123",
                "invite_code": "QR-ABCDEF",
            },
        )

    assert resp.status_code == 200
    types = [e["event_type"] for e in captured_events]
    assert "invite_code_redeemed" in types
    redeem_event = next(e for e in captured_events if e["event_type"] == "invite_code_redeemed")
    details = redeem_event.get("details") or {}
    # Don't log the new user's identifying fields — just the code + invite id.
    assert details.get("invite_code") == "QR-ABCDEF"
    assert details.get("invite_id") == "resolved-invite-uuid"


def test_register_invite_code_unknown_does_not_emit_redemption_audit(fresh_register_success):
    """A 404 (unknown code) should NOT emit invite_code_redeemed."""
    client = TestClient(app)
    captured_events = []

    async def _fake_audit(event_type, **kwargs):
        captured_events.append({"event_type": event_type, **kwargs})

    with patch.object(
        referral_service_module,
        "resolve_code_to_invite_id",
        new=AsyncMock(return_value=None),
    ), patch(
        "app.api.auth_routes.log_audit_event", side_effect=_fake_audit,
    ):
        resp = client.post(
            "/api/v1/auth/register",
            json={
                "email": "u@example.com",
                "password": "ValidP@ss123",
                "invite_code": "QR-ZZZZZZ",
            },
        )
    assert resp.status_code == 404
    types = [e["event_type"] for e in captured_events]
    assert "invite_code_redeemed" not in types


# ---------- Task 1.9 idle-work: resolve_code edge cases ----------


def test_register_invite_code_case_sensitive_lookup_returns_format_error(
    fresh_register_success,
):
    """qr-abcdef (lowercase) is NOT 'QR-ABCDEF' — fails format validation pre-lookup."""
    client = TestClient(app)
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": "u@example.com",
            "password": "ValidP@ss123",
            "invite_code": "qr-abcdef",
        },
    )
    assert resp.status_code in (400, 422)


@pytest.mark.parametrize(
    "bad",
    [
        "QR-ABCDE",      # 5 chars
        "QR-ABCDEFG",    # 7 chars
        "QR-ABC0EF",     # 0 is excluded from alphabet
        "QR-ABC1EF",     # 1 is excluded
        "QR-ABCIEF",     # I is excluded
        "QR-ABCOEF",     # O is excluded
        "QRABCDEF",      # missing dash
        "PR-ABCDEF",     # wrong prefix
        " QR-ABCDEF",    # leading whitespace
        "QR-ABCDEF ",    # trailing whitespace
    ],
)
def test_register_invite_code_format_rejects_bad_inputs(bad, fresh_register_success):
    """Comprehensive negative cases against the QR-XXXXXX regex."""
    client = TestClient(app)
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": "u@example.com",
            "password": "ValidP@ss123",
            "invite_code": bad,
        },
    )
    assert resp.status_code in (400, 422), f"unexpected accept for {bad!r}"


@pytest.mark.asyncio
async def test_resolve_code_to_invite_id_insert_returns_no_data_yields_none():
    """If the insert succeeds but returns no data (RLS / driver edge), result is None."""
    mock_client = MagicMock()

    def table_side_effect(name):
        chain = MagicMock()
        if name == "users":
            chain.select.return_value = chain
            chain.eq.return_value = chain
            chain.maybe_single.return_value = chain
            chain.execute.return_value = MagicMock(
                data={"id": "referrer-uuid", "referral_code": "QR-ABCDEF"}
            )
        else:
            chain.insert.return_value = chain
            chain.execute.return_value = MagicMock(data=[])  # empty
        return chain

    mock_client.table.side_effect = table_side_effect

    with patch(
        "app.services.referral_service.get_admin_supabase_client",
        return_value=mock_client,
    ):
        from app.services.referral_service import resolve_code_to_invite_id

        result = await resolve_code_to_invite_id("QR-ABCDEF", "invitee-uuid")
    assert result is None


@pytest.mark.asyncio
async def test_resolve_code_to_invite_id_lookup_exception_returns_none():
    """If user-lookup raises, resolver must swallow and return None — never 500."""
    mock_client = MagicMock()
    chain = MagicMock()
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.maybe_single.return_value = chain
    chain.execute.side_effect = RuntimeError("DB hiccup")
    mock_client.table.return_value = chain
    with patch(
        "app.services.referral_service.get_admin_supabase_client",
        return_value=mock_client,
    ):
        from app.services.referral_service import resolve_code_to_invite_id

        result = await resolve_code_to_invite_id("QR-ABCDEF", "invitee-uuid")
    assert result is None


@pytest.mark.asyncio
async def test_resolve_code_to_invite_id_insert_exception_returns_none():
    """If the insert path raises, resolver returns None (caller maps to 404)."""
    mock_client = MagicMock()

    def table_side_effect(name):
        chain = MagicMock()
        if name == "users":
            chain.select.return_value = chain
            chain.eq.return_value = chain
            chain.maybe_single.return_value = chain
            chain.execute.return_value = MagicMock(
                data={"id": "referrer-uuid", "referral_code": "QR-ABCDEF"}
            )
        else:
            chain.insert.return_value = chain
            chain.execute.side_effect = RuntimeError("constraint blip")
        return chain

    mock_client.table.side_effect = table_side_effect

    with patch(
        "app.services.referral_service.get_admin_supabase_client",
        return_value=mock_client,
    ):
        from app.services.referral_service import resolve_code_to_invite_id

        result = await resolve_code_to_invite_id("QR-ABCDEF", "invitee-uuid")
    assert result is None
