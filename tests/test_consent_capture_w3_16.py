"""W3-16 — consent capture (ToS acceptance + 13+ attestation), backend half.

Spec: .qa-w3b/W3_16_UNIT_SPEC.md §5-B (tests B.1-B.13) + FABLE rulings.

Contract under test:
  * `RegisterRequest` / `SocialLoginRequest` accept three OPTIONAL fields
    (`terms_accepted`, `terms_version`, `age_attested`); phones on 97b5f15
    send none of them and must keep working.
  * `ENABLE_CONSENT_REQUIRED` (default OFF, read PER CALL) rejects an account
    creation that carries no complete acceptance with
    400 {"success": false, "code": "TERMS_ACCEPTANCE_REQUIRED"} — on /register
    BEFORE any Supabase account exists, and on /social-login only for a NEW
    account (existing accounts are never gated).
  * `ENABLE_CONSENT_PERSIST` (default OFF, read PER CALL) writes
    `terms_accepted_at` / `terms_version` / `age_attested_at` into the
    `users` insert. OFF = the insert dict is byte-identical to today's.
  * Migration 038 adds the three nullable columns, with a rollback file.

House idiom (ruling 6): every import of the NEW module
`app.services.consent_service` lives INSIDE the test that needs it, so the
file always collects and the flag-OFF pins (B.4, B.8) run before AND after.

Every test starts with BOTH flags unset (autouse `_clean_consent_flags`).
"""
import re
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app

REPO_ROOT = Path(__file__).resolve().parents[1]

PERSIST_FLAG = "ENABLE_CONSENT_PERSIST"
REQUIRED_FLAG = "ENABLE_CONSENT_REQUIRED"
TERMS_VERSION = "2026-03-26"
REJECTION_CODE = "TERMS_ACCEPTANCE_REQUIRED"

BARE_REGISTER = {"email": "u@example.com", "password": "ValidP@ss123"}
FULL_CONSENT_FIELDS = {
    "terms_accepted": True,
    "terms_version": TERMS_VERSION,
    "age_attested": True,
}
CONSENT_COLUMNS = {"terms_accepted_at", "terms_version", "age_attested_at"}

# A consent record in the shape consent_from_fields() returns (§4.3). Built
# literally here so the service-level tests red on the missing `consent`
# keyword, not on the missing consent_service module.
CONSENT_RECORD = {
    "terms_accepted_at": "2026-09-11T00:00:00+00:00",
    "terms_version": TERMS_VERSION,
    "age_attested_at": "2026-09-11T00:00:00+00:00",
}


# ---------------------------------------------------------------------------
# fixtures + harness (tests/test_auth_routes_invite_fingerprint.py:17-41,
# tests/test_auth_interceptor.py:422 / :1024)
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _disable_limiter():
    """/register is 3/minute, /social-login 10/minute; this file posts more."""
    from app.middleware.rate_limiter import limiter

    prior = limiter.enabled
    limiter.enabled = False
    yield
    limiter.enabled = prior


@pytest.fixture(autouse=True)
def _clean_consent_flags(monkeypatch):
    """Every test states its own flag values; never inherit the ambient env."""
    monkeypatch.delenv(PERSIST_FLAG, raising=False)
    monkeypatch.delenv(REQUIRED_FLAG, raising=False)
    yield


def _register_success_mock() -> AsyncMock:
    return AsyncMock(
        return_value={
            "success": True,
            "user": {"id": "00000000-0000-0000-0000-000000000001", "email": "u@example.com"},
            "session": {"access_token": "tok", "refresh_token": "ref"},
            "message": "ok",
        }
    )


def _register_service_mocks():
    """MagicMock auth + admin clients for register_user (test_auth_interceptor:422)."""
    mock_user = MagicMock()
    mock_user.id = "new-id"
    mock_user.email = "new@test.com"

    mock_session = MagicMock()
    mock_session.access_token = "access-tok"
    mock_session.refresh_token = "refresh-tok"
    mock_session.expires_at = 1234567890

    mock_response = MagicMock()
    mock_response.user = mock_user
    mock_response.session = mock_session

    mock_client = MagicMock()
    mock_client.auth.sign_up.return_value = mock_response

    mock_admin_table = MagicMock()
    mock_admin_table.insert.return_value.execute.return_value = MagicMock()
    mock_admin = MagicMock()
    mock_admin.table.return_value = mock_admin_table
    return mock_client, mock_admin, mock_admin_table


def _social_service_mocks(existing_rows):
    """MagicMock auth + admin clients for sign_in_with_social (test_auth_interceptor:1024)."""
    mock_user = MagicMock()
    mock_user.id = "new-id"
    mock_user.email = "new@test.com"

    mock_session = MagicMock()
    mock_session.access_token = "social-tok"
    mock_session.refresh_token = "social-ref"
    mock_session.expires_at = 9999

    mock_response = MagicMock()
    mock_response.user = mock_user
    mock_response.session = mock_session

    mock_auth_client = MagicMock()
    mock_auth_client.auth.sign_in_with_id_token.return_value = mock_response

    mock_admin_client = MagicMock()
    mock_admin_client.table.return_value.select.return_value.eq.return_value.execute.return_value = (
        MagicMock(data=existing_rows)
    )
    return mock_auth_client, mock_admin_client


def _iso(value) -> datetime:
    assert isinstance(value, str) and value, value
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


# ---------------------------------------------------------------------------
# B.1 — /register threads the parsed consent into register_user (flags OFF)
# ---------------------------------------------------------------------------


def test_b1_register_route_threads_parsed_consent_to_register_user():
    mock = _register_success_mock()
    with patch("app.api.auth_routes.register_user", new=mock):
        client = TestClient(app)

        resp = client.post("/api/v1/auth/register", json={**BARE_REGISTER, **FULL_CONSENT_FIELDS})
        assert resp.status_code == 200, resp.text
        consent = mock.call_args.kwargs["consent"]
        assert isinstance(consent, dict), consent
        assert consent["terms_version"] == TERMS_VERSION
        _iso(consent["terms_accepted_at"])
        _iso(consent["age_attested_at"])

        mock.reset_mock()
        resp = client.post("/api/v1/auth/register", json=BARE_REGISTER)
        assert resp.status_code == 200, resp.text
        assert mock.call_args.kwargs["consent"] is None


# ---------------------------------------------------------------------------
# B.1bis — the version is recorded AS SENT (what the user saw), never coerced
# to the server's TERMS_VERSION. After a bump, a phone on an older OTA must
# record the OLD version it accepted, or the row is false legal evidence.
# ---------------------------------------------------------------------------


def test_b1bis_terms_version_is_recorded_as_sent_not_coerced():
    from app.services.consent_service import TERMS_VERSION as SERVER_VERSION
    from app.services.consent_service import consent_from_fields

    sent_version = "2025-01-01"
    assert sent_version != SERVER_VERSION

    record = consent_from_fields(True, sent_version, True)
    assert record is not None
    assert record["terms_version"] == sent_version

    mock = _register_success_mock()
    with patch("app.api.auth_routes.register_user", new=mock):
        resp = TestClient(app).post(
            "/api/v1/auth/register",
            json={**BARE_REGISTER, **FULL_CONSENT_FIELDS, "terms_version": sent_version},
        )
    assert resp.status_code == 200, resp.text
    assert mock.call_args.kwargs["consent"]["terms_version"] == sent_version


# ---------------------------------------------------------------------------
# B.2 — REQUIRED ON rejects a bare register BEFORE any account exists
# ---------------------------------------------------------------------------


def test_b2_required_on_rejects_bare_register_before_register_user(monkeypatch):
    monkeypatch.setenv(REQUIRED_FLAG, "true")
    mock = _register_success_mock()
    with patch("app.api.auth_routes.register_user", new=mock):
        resp = TestClient(app).post("/api/v1/auth/register", json=BARE_REGISTER)

    assert resp.status_code == 400, resp.text
    body = resp.json()
    assert body["success"] is False
    assert body["code"] == REJECTION_CODE
    mock.assert_not_called()


# ---------------------------------------------------------------------------
# B.3 — BOTH attestations are required
# ---------------------------------------------------------------------------


def test_b3_required_on_needs_both_terms_and_age_attestation(monkeypatch):
    monkeypatch.setenv(REQUIRED_FLAG, "true")
    mock = _register_success_mock()
    with patch("app.api.auth_routes.register_user", new=mock):
        client = TestClient(app)

        no_age = client.post(
            "/api/v1/auth/register",
            json={**BARE_REGISTER, "terms_accepted": True, "terms_version": TERMS_VERSION},
        )
        assert no_age.status_code == 400, no_age.text
        assert no_age.json()["code"] == REJECTION_CODE

        no_terms = client.post(
            "/api/v1/auth/register",
            json={**BARE_REGISTER, "age_attested": True, "terms_version": TERMS_VERSION},
        )
        assert no_terms.status_code == 400, no_terms.text
        assert no_terms.json()["code"] == REJECTION_CODE

        # §4.3 "a NON-EMPTY terms_version": a missing or empty version is not
        # an acceptance, or PERSIST would record NULL / "" as legal evidence.
        no_version = client.post(
            "/api/v1/auth/register",
            json={**BARE_REGISTER, "terms_accepted": True, "age_attested": True},
        )
        assert no_version.status_code == 400, no_version.text
        assert no_version.json()["code"] == REJECTION_CODE

        empty_version = client.post(
            "/api/v1/auth/register",
            json={**BARE_REGISTER, "terms_accepted": True, "terms_version": "", "age_attested": True},
        )
        assert empty_version.status_code == 400, empty_version.text
        assert empty_version.json()["code"] == REJECTION_CODE

        mock.assert_not_called()

        full = client.post("/api/v1/auth/register", json={**BARE_REGISTER, **FULL_CONSENT_FIELDS})
        assert full.status_code == 200, full.text
        mock.assert_called_once()


# ---------------------------------------------------------------------------
# B.4 — PRESERVE PIN: flags unset, bare register -> 200 (phones on 97b5f15)
# ---------------------------------------------------------------------------


def test_b4_required_off_bare_register_still_200():
    mock = _register_success_mock()
    with patch("app.api.auth_routes.register_user", new=mock):
        resp = TestClient(app).post("/api/v1/auth/register", json=BARE_REGISTER)

    assert resp.status_code == 200, resp.text
    assert resp.json()["success"] is True
    mock.assert_called_once()


# ---------------------------------------------------------------------------
# B.5 / B.6 — register_user insert dict, PERSIST ON vs OFF
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_b5_persist_on_register_user_writes_consent_columns(monkeypatch):
    from app.services.auth_service import register_user

    monkeypatch.setenv(PERSIST_FLAG, "true")
    mock_client, mock_admin, mock_admin_table = _register_service_mocks()
    with patch("app.services.auth_service.get_auth_client", return_value=mock_client), patch(
        "app.services.auth_service.get_admin_client", return_value=mock_admin
    ):
        result = await register_user("new@test.com", "pw", consent=dict(CONSENT_RECORD))

    assert result["success"] is True
    inserted = mock_admin_table.insert.call_args.args[0]
    assert set(inserted) == {"id", "email", "subscription_tier"} | CONSENT_COLUMNS
    assert inserted == {
        "id": "new-id",
        "email": "new@test.com",
        "subscription_tier": "free",
        **CONSENT_RECORD,
    }


@pytest.mark.asyncio
async def test_b6_persist_off_register_user_insert_is_byte_identical_even_with_consent():
    from app.services.auth_service import register_user

    mock_client, mock_admin, mock_admin_table = _register_service_mocks()
    with patch("app.services.auth_service.get_auth_client", return_value=mock_client), patch(
        "app.services.auth_service.get_admin_client", return_value=mock_admin
    ):
        result = await register_user("new@test.com", "pw", consent=dict(CONSENT_RECORD))

    assert result["success"] is True
    assert mock_admin_table.insert.call_args.args[0] == {
        "id": "new-id",
        "email": "new@test.com",
        "subscription_tier": "free",
    }


# ---------------------------------------------------------------------------
# B.7 / B.8 / B.9 — sign_in_with_social at the `if not existing.data` branch
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_b7_social_new_account_required_on_without_consent_is_refused_no_row(monkeypatch):
    from app.services.auth_service import sign_in_with_social

    monkeypatch.setenv(REQUIRED_FLAG, "true")
    mock_auth_client, mock_admin_client = _social_service_mocks(existing_rows=[])
    with patch("app.services.auth_service.get_auth_client", return_value=mock_auth_client), patch(
        "app.services.auth_service.get_admin_client", return_value=mock_admin_client
    ):
        result = await sign_in_with_social("google", "a.b.c")

    assert result["success"] is False, result
    assert result["code"] == REJECTION_CODE
    assert isinstance(result.get("error"), str) and result["error"]
    mock_admin_client.table.return_value.insert.assert_not_called()


@pytest.mark.asyncio
async def test_b7bis_social_new_account_required_on_with_consent_signs_in(monkeypatch):
    """REQUIRED ON is the state updated phones run in: a NEW Google/Apple account
    that DOES carry consent must be created, not refused. (Fixer addition — the
    `consent is None` half of the B.7 gate; B.7 alone survives a gate that
    refuses every new social account.)"""
    from app.services.auth_service import sign_in_with_social

    monkeypatch.setenv(REQUIRED_FLAG, "true")
    mock_auth_client, mock_admin_client = _social_service_mocks(existing_rows=[])
    with patch("app.services.auth_service.get_auth_client", return_value=mock_auth_client), patch(
        "app.services.auth_service.get_admin_client", return_value=mock_admin_client
    ):
        result = await sign_in_with_social("google", "a.b.c", consent=dict(CONSENT_RECORD))

    assert result["success"] is True, result
    insert = mock_admin_client.table.return_value.insert
    insert.assert_called_once()
    # PERSIST is OFF here: the row is created, with today's exact four keys.
    assert insert.call_args.args[0] == {
        "id": "new-id",
        "email": "new@test.com",
        "auth_provider": "google",
        "subscription_tier": "free",
    }


@pytest.mark.asyncio
async def test_b8_social_existing_account_required_on_without_consent_signs_in(monkeypatch):
    """PRESERVE PIN: the gate never touches an account that already exists."""
    from app.services.auth_service import sign_in_with_social

    monkeypatch.setenv(REQUIRED_FLAG, "true")
    mock_auth_client, mock_admin_client = _social_service_mocks(existing_rows=[{"id": "x"}])
    with patch("app.services.auth_service.get_auth_client", return_value=mock_auth_client), patch(
        "app.services.auth_service.get_admin_client", return_value=mock_admin_client
    ):
        result = await sign_in_with_social("google", "a.b.c")

    assert result["success"] is True, result
    mock_admin_client.table.return_value.insert.assert_not_called()


@pytest.mark.asyncio
async def test_b9_social_new_account_persist_on_with_consent_writes_columns(monkeypatch):
    from app.services.auth_service import sign_in_with_social

    monkeypatch.setenv(PERSIST_FLAG, "true")
    mock_auth_client, mock_admin_client = _social_service_mocks(existing_rows=[])
    with patch("app.services.auth_service.get_auth_client", return_value=mock_auth_client), patch(
        "app.services.auth_service.get_admin_client", return_value=mock_admin_client
    ):
        result = await sign_in_with_social("google", "a.b.c", consent=dict(CONSENT_RECORD))

    assert result["success"] is True, result
    insert = mock_admin_client.table.return_value.insert
    insert.assert_called_once()
    inserted = insert.call_args.args[0]
    assert set(inserted) == {"id", "email", "auth_provider", "subscription_tier"} | CONSENT_COLUMNS
    assert inserted == {
        "id": "new-id",
        "email": "new@test.com",
        "auth_provider": "google",
        "subscription_tier": "free",
        **CONSENT_RECORD,
    }


# ---------------------------------------------------------------------------
# B.10 — /social-login maps the consent code to 400; other failures stay 401
# ---------------------------------------------------------------------------


def test_b10_social_login_route_maps_consent_code_to_400_other_failures_401():
    client = TestClient(app)
    body = {"provider": "google", "id_token": "a.b.c"}

    refused = {"success": False, "code": REJECTION_CODE, "error": "x"}
    with patch("app.api.auth_routes.sign_in_with_social", new=AsyncMock(return_value=refused)):
        resp = client.post("/api/v1/auth/social-login", json=body)
    assert resp.status_code == 400, resp.text
    assert resp.json()["success"] is False
    assert resp.json()["code"] == REJECTION_CODE

    invalid = {"success": False, "error": "Invalid token"}
    with patch("app.api.auth_routes.sign_in_with_social", new=AsyncMock(return_value=invalid)):
        resp = client.post("/api/v1/auth/social-login", json=body)
    assert resp.status_code == 401, resp.text


# ---------------------------------------------------------------------------
# B.10-bis (ADDED by the red phase — NOT in spec §5-B; see report): the
# /social-login route must thread the parsed consent to sign_in_with_social as
# a KEYWORD (spec §4.3). Without this, every service-level test (B.7/B.9) can
# pass while the route silently drops what the client sent, and REQUIRED ON
# would then refuse every new social account.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("required_on", [False, True], ids=["required_off", "required_on"])
def test_b10bis_social_login_route_threads_parsed_consent_as_keyword(monkeypatch, required_on):
    # Run in BOTH flag states: REQUIRED ON is the state in which dropping the
    # consent at the route would refuse every new social account (fixer
    # addition — the flags-OFF run alone survives a route that drops consent
    # only when REQUIRED is on).
    if required_on:
        monkeypatch.setenv(REQUIRED_FLAG, "true")
    ok = {"success": True, "user": {"id": "u"}, "session": {"access_token": "t"}}
    mock = AsyncMock(return_value=ok)
    with patch("app.api.auth_routes.sign_in_with_social", new=mock):
        client = TestClient(app)

        resp = client.post(
            "/api/v1/auth/social-login",
            json={"provider": "google", "id_token": "a.b.c", **FULL_CONSENT_FIELDS},
        )
        assert resp.status_code == 200, resp.text
        consent = mock.call_args.kwargs["consent"]
        assert isinstance(consent, dict), consent
        assert consent["terms_version"] == TERMS_VERSION
        _iso(consent["terms_accepted_at"])
        _iso(consent["age_attested_at"])

        mock.reset_mock()
        resp = client.post("/api/v1/auth/social-login", json={"provider": "google", "id_token": "a.b.c"})
        assert resp.status_code == 200, resp.text
        assert mock.call_args.kwargs["consent"] is None


# ---------------------------------------------------------------------------
# B.11 — per-call reads, independent flags
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_b11_flags_are_read_per_call_and_independent(monkeypatch):
    mock = _register_success_mock()
    with patch("app.api.auth_routes.register_user", new=mock):
        client = TestClient(app)

        # REQUIRED flips without a reload, both directions.
        monkeypatch.setenv(REQUIRED_FLAG, "true")
        resp = client.post("/api/v1/auth/register", json=BARE_REGISTER)
        assert resp.status_code == 400, resp.text
        assert resp.json()["code"] == REJECTION_CODE

        monkeypatch.delenv(REQUIRED_FLAG, raising=False)
        resp = client.post("/api/v1/auth/register", json=BARE_REGISTER)
        assert resp.status_code == 200, resp.text

        # PERSIST ON + REQUIRED OFF: a bare body is accepted and carries no
        # consent — PERSIST does not imply REQUIRED.
        monkeypatch.setenv(PERSIST_FLAG, "true")
        mock.reset_mock()
        resp = client.post("/api/v1/auth/register", json=BARE_REGISTER)
        assert resp.status_code == 200, resp.text
        assert mock.call_args.kwargs["consent"] is None

    # ... and with no consent the PERSIST-ON insert writes nothing extra.
    from app.services.auth_service import register_user

    mock_client, mock_admin, mock_admin_table = _register_service_mocks()
    with patch("app.services.auth_service.get_auth_client", return_value=mock_client), patch(
        "app.services.auth_service.get_admin_client", return_value=mock_admin
    ):
        result = await register_user("new@test.com", "pw", consent=None)
    assert result["success"] is True
    assert mock_admin_table.insert.call_args.args[0] == {
        "id": "new-id",
        "email": "new@test.com",
        "subscription_tier": "free",
    }


# ---------------------------------------------------------------------------
# B.12 — cross-language TERMS_VERSION parity (reads SmartCompareApp/)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_b12_terms_version_parity_backend_legal_route_and_client():
    from app.api import legal_routes
    from app.services import consent_service

    served = (await legal_routes.get_terms_of_service())["last_updated"]

    client_src = (REPO_ROOT / "SmartCompareApp" / "src" / "services" / "consent.ts").read_text(
        encoding="utf-8"
    )
    m = re.search(r"export\s+const\s+TERMS_VERSION\s*=\s*['\"]([^'\"]+)['\"]", client_src)
    assert m, "TERMS_VERSION literal not found in SmartCompareApp/src/services/consent.ts"

    assert consent_service.TERMS_VERSION == TERMS_VERSION
    assert consent_service.TERMS_VERSION == served
    assert m.group(1) == consent_service.TERMS_VERSION


# ---------------------------------------------------------------------------
# B.13 — migration 038 is additive and reversible (static)
# ---------------------------------------------------------------------------


def _strip_sql_comments(sql: str) -> str:
    return "\n".join(line.split("--", 1)[0] for line in sql.splitlines())


def test_b13_migration_038_is_additive_nullable_and_has_a_rollback():
    forward_path = REPO_ROOT / "migrations" / "038_users_consent_capture.sql"
    rollback_path = REPO_ROOT / "migrations" / "rollback" / "038_users_consent_capture.sql"
    assert forward_path.is_file(), f"missing {forward_path}"
    assert rollback_path.is_file(), f"missing {rollback_path}"

    forward_raw = forward_path.read_text(encoding="utf-8")
    forward = _strip_sql_comments(forward_raw)

    assert re.search(r"ALTER\s+TABLE\s+(public\.)?users\b", forward, re.I)
    added = re.findall(r"ADD\s+COLUMN\s+IF\s+NOT\s+EXISTS\s+([a-z_]+)", forward, re.I)
    assert sorted(a.lower() for a in added) == sorted(CONSENT_COLUMNS), added
    assert not re.search(r"NOT\s+NULL", forward, re.I), "consent columns must be nullable"
    assert not re.search(r"\bDROP\b", forward, re.I), "forward migration must not drop anything"
    assert "rollback/038_users_consent_capture.sql" in forward_raw, "header must name its rollback"

    rollback = _strip_sql_comments(rollback_path.read_text(encoding="utf-8"))
    dropped = re.findall(r"DROP\s+COLUMN\s+IF\s+EXISTS\s+([a-z_]+)", rollback, re.I)
    assert sorted(d.lower() for d in dropped) == sorted(CONSENT_COLUMNS), dropped
