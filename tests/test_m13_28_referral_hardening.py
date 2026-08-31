"""M13-28 — the referral invite endpoints were unauthenticated, unrate-limited
and their share_token/ref params unvalidated, so with ENABLE_REFERRAL_SYSTEM on
an anonymous client could hammer POST /invite/<anything>/quiz and push unbounded
strings into the PostgREST filter values.

Harden (correction — the router is already flag-gated by ENABLE_REFERRAL_SYSTEM,
flipped on in Railway and on in the test conftest):
  * limiter decorators (20/min on GET invite, 10/min on the quiz POST),
  * Path/Query patterns using the existing invite-code alphabet,
  * both handlers gain the request: Request slowapi requires.

Pins: invalid code -> 422; over-limit -> 429; valid params still reach the
service (the request: Request addition did not break the signature).
"""
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import app

_VALID_TOKEN = "sometoken123456789"   # url-safe base64 shape
_VALID_REF = "QR-ABCDEF"              # QR- + 6 unambiguous-alphabet chars


@pytest.fixture()
def client():
    return TestClient(app)


@pytest.fixture()
def mock_referral_service(monkeypatch):
    """Patch ReferralService so no test touches Supabase; resolve/quiz default
    to None (-> 404) unless a test overrides them."""
    svc = MagicMock()
    svc.resolve_invite = AsyncMock(return_value=None)
    svc.run_invitee_quiz = AsyncMock(return_value=None)
    monkeypatch.setattr("app.api.referral_routes.ReferralService", lambda *a, **k: svc)
    return svc


_QUIZ_BODY = {
    "priority": "best_price",
    "budget": "mid",
    "brand_attitude": "function_first",
    "non_negotiable": "size",
}


# ---- invalid params -> 422 (before the service is ever called) --------------

def test_invalid_share_token_is_422(client, mock_referral_service):
    resp = client.get(f"/api/v1/referrals/invite/{'a' * 65}", params={"ref": _VALID_REF})
    assert resp.status_code == 422, resp.text
    mock_referral_service.resolve_invite.assert_not_awaited()


def test_share_token_with_bad_char_is_422(client, mock_referral_service):
    resp = client.get("/api/v1/referrals/invite/bad.token", params={"ref": _VALID_REF})
    assert resp.status_code == 422, resp.text


def test_invalid_ref_is_422(client, mock_referral_service):
    resp = client.get(
        f"/api/v1/referrals/invite/{_VALID_TOKEN}", params={"ref": "not-a-code"}
    )
    assert resp.status_code == 422, resp.text
    mock_referral_service.resolve_invite.assert_not_awaited()


def test_quiz_invalid_share_token_is_422(client, mock_referral_service):
    resp = client.post(
        f"/api/v1/referrals/invite/{'a' * 65}/quiz", json=_QUIZ_BODY
    )
    assert resp.status_code == 422, resp.text
    mock_referral_service.run_invitee_quiz.assert_not_awaited()


# ---- valid params still work (request:Request did not break the signature) --

def test_valid_invite_params_reach_service(client, monkeypatch):
    svc = MagicMock()
    svc.resolve_invite = AsyncMock(return_value={
        "referrer_display_name": "Ahmed",
        "comparison": {"products": [], "winner": None},
        "cohort_match": None,
        "invite_id": "i-1",
    })
    monkeypatch.setattr("app.api.referral_routes.ReferralService", lambda *a, **k: svc)

    resp = client.get(f"/api/v1/referrals/invite/{_VALID_TOKEN}", params={"ref": _VALID_REF})
    assert resp.status_code == 200, resp.text
    svc.resolve_invite.assert_awaited_once()


def test_valid_quiz_params_reach_service(client, monkeypatch):
    svc = MagicMock()
    svc.run_invitee_quiz = AsyncMock(return_value={
        "products": [], "winner": None,
        "scoring": {"scoring_method": "invitee_quiz"},
    })
    monkeypatch.setattr("app.api.referral_routes.ReferralService", lambda *a, **k: svc)

    resp = client.post(f"/api/v1/referrals/invite/{_VALID_TOKEN}/quiz", json=_QUIZ_BODY)
    assert resp.status_code == 200, resp.text
    svc.run_invitee_quiz.assert_awaited_once()


# ---- over-limit -> 429 ------------------------------------------------------

def test_invite_get_over_limit_429(client, mock_referral_service):
    """20/min on GET invite -> the 21st valid call within the window is 429."""
    statuses = [
        client.get(f"/api/v1/referrals/invite/{_VALID_TOKEN}", params={"ref": _VALID_REF}).status_code
        for _ in range(25)
    ]
    assert 429 in statuses, statuses
    assert statuses.index(429) >= 20, f"429 fired too early: {statuses}"


def test_quiz_post_over_limit_429(client, mock_referral_service):
    """10/min on the quiz POST -> the 11th valid call within the window is 429."""
    statuses = [
        client.post(f"/api/v1/referrals/invite/{_VALID_TOKEN}/quiz", json=_QUIZ_BODY).status_code
        for _ in range(15)
    ]
    assert 429 in statuses, statuses
    assert statuses.index(429) >= 10, f"429 fired too early: {statuses}"
