"""S69 U7 T4 (spec R4) -- an LLM outage on the camera route is an LLM outage.

Base (d792f00e): `/api/v1/image/identify` wraps `identify_products` in a bare
`except Exception` (app/api/image_routes.py, the "vision_exception" exit) and
raises HTTPException(500, "Image analysis failed. Please try again."), which
error_handler turns into a code SERVER_ERROR envelope. So a prod OpenAI 429
(`insufficient_quota` is a RateLimitError), a connection drop, or the preflight
breaker's LLMUnavailableError all look to the client like a generic server
crash, and ResultsScreen routes them into the "Still gathering prices / Tap to
retry" loop.

Target: the SAME `{success: false, code: "LLM_UNAVAILABLE"}` 503 envelope the
text route ships (app/api/text_routes.py `_surface_comparison_failure`,
detail = {"code": "LLM_UNAVAILABLE", "error": LLM_UNAVAILABLE_FRIENDLY_MESSAGE})
when the failure is one the breaker itself calls transient
(api_budget_service._openai_failure_is_transient) or is LLMUnavailableError.
Anything else keeps today's 500 literal (pinned elsewhere:
test_paid_route_metering.py vision_raised_500, test_security_regression.py).

Hermetic: the OpenAI client object `openai_service.client` is replaced with a
fake whose `chat.completions.create` raises a locally built SDK exception --
the REAL `identify_products` and the REAL `guarded_llm_create` run, no socket
is opened. The breaker-denied case patches `_openai_dispatch_admission` (no
Redis). Harness pattern follows tests/test_paid_route_metering.py.
"""
from __future__ import annotations

import httpx
import openai
import pytest
from fastapi.testclient import TestClient

from app.api import image_routes
from app.api.auth_routes import get_optional_user
from app.main import app
from app.middleware.rate_limiter import limiter
from app.services import api_budget_service, openai_service, usage_service
from app.services.structured_comparison_service import (
    LLM_UNAVAILABLE_FRIENDLY_MESSAGE,
)

JPEG = b"\xff\xd8" + b"\x00" * 64
VISION_500_LITERAL = "Image analysis failed. Please try again."
_OPENAI_URL = "https://api.openai.invalid/v1/chat/completions"


# ---------------------------------------------------------------------------
# harness
# ---------------------------------------------------------------------------
class _Ledger:
    """consume/refund stand-ins recording at CALL time (the refund site is
    fire_and_forget(refund_comparison_credit(uid)), which may never be awaited
    before TestClient returns) -- same reasoning as test_paid_route_metering."""

    def __init__(self) -> None:
        self.consumes: list[str] = []
        self.refunds: list[str] = []

    def consume(self, user_id, access_token="", *_a, **_kw):
        self.consumes.append(user_id)

        async def _r():
            return {
                "allowed": True,
                "reason": None,
                "tier": "free",
                "consumed": True,
                "consumed_keys": {"daily": f"usage:daily:{user_id}"},
                "remaining": {"daily": 2, "monthly": 9, "lifetime_free": 2},
            }

        return _r()

    def refund(self, user_id, consumed_keys=None, *_a, **_kw):
        self.refunds.append(user_id)

        async def _r():
            return None

        return _r()


class _RaisingCompletions:
    def __init__(self, exc_factory) -> None:
        self._exc_factory = exc_factory
        self.calls = 0

    async def create(self, **_kwargs):
        self.calls += 1
        raise self._exc_factory()


class _FakeOpenAIClient:
    def __init__(self, exc_factory) -> None:
        self.completions = _RaisingCompletions(exc_factory)
        self.chat = type("_Chat", (), {"completions": self.completions})()


def _rate_limit_error() -> openai.RateLimitError:
    # Prod's shape on 2026-09 : a 429 whose body code is insufficient_quota.
    req = httpx.Request("POST", _OPENAI_URL)
    resp = httpx.Response(
        429,
        request=req,
        json={"error": {"code": "insufficient_quota",
                        "message": "You exceeded your current quota"}},
    )
    return openai.RateLimitError(
        "Error code: 429 - insufficient_quota sk-proj-...XXXX",
        response=resp,
        body={"error": {"code": "insufficient_quota"}},
    )


def _connection_error() -> openai.APIConnectionError:
    return openai.APIConnectionError(request=httpx.Request("POST", _OPENAI_URL))


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture(autouse=True)
def _hermetic(monkeypatch):
    # Several requests per test: keep the process-wide 10/min bucket out of it.
    monkeypatch.setattr(limiter, "enabled", False)
    monkeypatch.delenv("ENABLE_ANON_USAGE_GATE", raising=False)
    monkeypatch.delenv("ENABLE_LLM_PREFLIGHT_BREAKER", raising=False)
    monkeypatch.setenv("ENABLE_PAID_ROUTE_METERING", "true")
    yield


@pytest.fixture
def authed(request):
    user = {
        "id": f"s69-u7-{request.node.name}"[:120],
        "email": "s69-u7@example.test",
        "access_token": "s69-u7-token",
    }
    app.dependency_overrides[get_optional_user] = lambda: user
    try:
        yield user
    finally:
        app.dependency_overrides.pop(get_optional_user, None)


@pytest.fixture
def ledger(monkeypatch):
    led = _Ledger()
    for mod in (usage_service, image_routes):
        monkeypatch.setattr(mod, "consume_comparison_credit", led.consume, raising=False)
        monkeypatch.setattr(mod, "refund_comparison_credit", led.refund, raising=False)
    return led


def _install_client(monkeypatch, exc_factory) -> _FakeOpenAIClient:
    fake = _FakeOpenAIClient(exc_factory)
    monkeypatch.setattr(openai_service, "client", fake)
    return fake


def _post_identify(client):
    files = [("images", (f"p{i}.jpg", JPEG, "image/jpeg")) for i in range(2)]
    return client.post("/api/v1/image/identify", files=files)


def _assert_llm_unavailable_envelope(resp, label: str) -> dict:
    assert resp.status_code == 503, (
        f"{label}: /image/identify must return 503 LLM_UNAVAILABLE like the text "
        f"route, got {resp.status_code} body={resp.text[:300]}"
    )
    body = resp.json()
    assert body.get("success") is False, f"{label}: envelope success must be False, got {body!r}"
    assert body.get("code") == "LLM_UNAVAILABLE", (
        f"{label}: envelope code must be LLM_UNAVAILABLE, got {body!r}"
    )
    assert body.get("error") == LLM_UNAVAILABLE_FRIENDLY_MESSAGE, (
        f"{label}: error must be the text route's constant, got {body.get('error')!r}"
    )
    # str(e) of the SDK error must never reach the wire.
    for leak in ("insufficient_quota", "sk-proj", "quota", "Error code"):
        assert leak not in resp.text, f"{label}: SDK detail {leak!r} leaked: {resp.text[:300]}"
    return body


# ---------------------------------------------------------------------------
# tests
# ---------------------------------------------------------------------------
def test_rate_limit_error_from_openai_returns_503_llm_unavailable_and_refunds_once(
    monkeypatch, client, authed, ledger
):
    """RED at base: status 500 / code SERVER_ERROR. The refund half is already
    true at base (exit 1 refunds) -- kept here as a pin on the new branch."""
    fake = _install_client(monkeypatch, _rate_limit_error)

    resp = _post_identify(client)

    assert fake.completions.calls == 1, (
        "harness: the real identify_products must have dispatched through the "
        f"patched client exactly once, got {fake.completions.calls}"
    )
    _assert_llm_unavailable_envelope(resp, "RateLimitError")
    assert ledger.consumes == [authed["id"]], f"one consume at the gate, got {ledger.consumes!r}"
    assert ledger.refunds == [authed["id"]], (
        f"the credit must be refunded exactly once like the text route, got {ledger.refunds!r}"
    )

    # Control (same request shape, non-LLM failure): a plain RuntimeError keeps
    # today's 500 literal -- the seam is class-specific, not a blanket 503.
    _install_client(monkeypatch, lambda: RuntimeError("s69 probe: not an LLM outage"))
    resp2 = _post_identify(client)
    assert resp2.status_code == 500, (
        f"a non-transient failure must stay 500, got {resp2.status_code} {resp2.text[:200]}"
    )
    assert resp2.json().get("code") != "LLM_UNAVAILABLE"
    assert VISION_500_LITERAL in resp2.text


def test_connection_error_from_openai_returns_503_llm_unavailable(
    monkeypatch, client, authed, ledger
):
    """RED at base: 500 SERVER_ERROR. APIConnectionError (and its subclass
    APITimeoutError) is transient per the breaker's own classifier."""
    _install_client(monkeypatch, _connection_error)

    resp = _post_identify(client)

    _assert_llm_unavailable_envelope(resp, "APIConnectionError")
    assert ledger.refunds == [authed["id"]], f"refund once, got {ledger.refunds!r}"


def test_breaker_denied_llm_unavailable_error_returns_503_llm_unavailable(
    monkeypatch, client, authed, ledger
):
    """RED at base: 500 SERVER_ERROR. With ENABLE_LLM_PREFLIGHT_BREAKER ON and
    the breaker open, guarded_llm_create raises LLMUnavailableError WITHOUT
    dispatching -- the camera route must say so with the same code."""
    monkeypatch.setenv("ENABLE_LLM_PREFLIGHT_BREAKER", "true")
    monkeypatch.setattr(
        api_budget_service, "_openai_dispatch_admission", lambda: (False, False, False)
    )
    fake = _install_client(monkeypatch, lambda: AssertionError("must not dispatch"))

    resp = _post_identify(client)

    assert fake.completions.calls == 0, "harness: a denied admission must not dispatch"
    _assert_llm_unavailable_envelope(resp, "LLMUnavailableError")
    assert ledger.refunds == [authed["id"]], f"refund once, got {ledger.refunds!r}"
