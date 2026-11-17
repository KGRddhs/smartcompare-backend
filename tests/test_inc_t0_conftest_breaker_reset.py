"""INC-T0 CONFTEST-BREAKER-RESET (S96-FIX incident lane, ruling H2R-14): tests/conftest.py
resets the process latches of the LLM spend breaker (llm_spend_breaker._STATE["ran"], read by
/health `llm_spend*`) and of the Anthropic router (llm_router._STATE["ran"], read by /health
`anthropic_breaker`) after EVERY test, so a test that trips either latch cannot leak the keys
into a later test's /health body in CI's one alphabetical process (the #418 CI red, P2R-39;
the link lane's #417 leak).

The rows run in file order (the runner passes -p no:randomly): each pair sets a latch in its
first test and reads /health in the next test of this file. RED at the base 7f672cfe (no
conftest reset: the latch leaks into the next test); green once the autouse fixture exists.
The second row of a pair run ALONE is vacuous (nothing set the latch); the pair is the row.
Hermetic: no network, no Redis command (the latches are set through the modules' own seams).
Pure ASCII, LF.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app  # noqa: E402  (first: the dotenv guard)
from app.services import llm_router, llm_spend_breaker  # noqa: E402

SPEND_KEYS = ("llm_spend", "llm_spend_fail_open", "llm_spend_late_records")
ROUTER_KEY = "anthropic_breaker"


def _health() -> dict:
    resp = TestClient(app).get("/health")
    assert resp.status_code == 200
    return resp.json()


# ---- pair 1: the spend-breaker latch -------------------------------------------------
def test_t0_1a_spend_breaker_latch_is_visible_on_health():
    """Set the spend breaker's 'ran' latch through its fail-open seam (a fail-open counts as
    a run, GC-5) and see the llm_spend keys on /health inside this test."""
    llm_spend_breaker._fail_open("RuntimeError")
    body = _health()
    assert "llm_spend" in body and body["llm_spend_fail_open"] >= 1, sorted(body)


def test_t0_1b_spend_breaker_latch_does_not_leak_into_the_next_test():
    """RED at base: the latch set by the previous test is still on, so /health still
    carries the llm_spend keys; the conftest reset after each test clears it."""
    body = _health()
    leaked = [k for k in SPEND_KEYS if k in body]
    assert leaked == [], "T0-1: the spend-breaker latch leaked across tests: %s" % leaked


# ---- pair 2: the router latch ---------------------------------------------------------
def test_t0_2a_router_latch_is_visible_on_health(monkeypatch):
    """Walk one role flag ON and decide: the router's 'ran' latch is set and /health carries
    anthropic_breaker inside this test."""
    monkeypatch.setenv("ENABLE_ANTHROPIC_VERDICT", "true")
    llm_router.decide("verdict")
    body = _health()
    assert ROUTER_KEY in body, sorted(body)


def test_t0_2b_router_latch_does_not_leak_into_the_next_test():
    """RED at base: the router latch set by the previous test survives the env restore, so
    /health still carries anthropic_breaker; the conftest reset after each test clears it."""
    body = _health()
    assert ROUTER_KEY not in body, "T0-2: the router latch leaked across tests"
