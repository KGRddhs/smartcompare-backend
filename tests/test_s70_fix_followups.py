"""Session 71 OAI_OBS fix round: pins for the adversary findings the fix
agent applied. The four test_s70_* RED files stay frozen; these pins sit in
their own file.

1. ``exc_summary`` runs the R-W18 URL scrub BEFORE the Sentry key patterns.
   With the key patterns first, a key-shape replacement glued to a URL
   (``Bearer https://u:p@h``, a JWT or a 32+ hex run directly before
   ``https://`` or ``://``) swallowed the URL scheme. The URL scrub then never
   saw ``scheme://`` and the userinfo stayed in the log line (measured by the
   correctness adversary, 4 of 4 adjacency shapes).
2. ``exc_summary`` collapses a line break in the TYPE name, and drops leading
   whitespace before the 200-character cut so whitespace cannot use up the
   budget and hide the text after it.
3. R2.5: ``_verdict_model_downgraded`` is reset at the START of every run on
   both orchestrator paths. The reset is observable on a run that ends before
   the verdict; the L1 content-safety refusal is that run here. Without these
   pins, replacing either reset with ``pass`` survived every test (adversary
   mutants M2f / M2g).

Nothing this unit creates is imported at module top (the C3 hygiene of the
RED files). No network: the L1 refusal returns before any provider call, and
the audit write is replaced by an AsyncMock. This file is ASCII-only and
carries no credential-shaped literal (secret-shaped strings are concatenated).
"""
import asyncio
from unittest.mock import AsyncMock

import pytest

import app.services.structured_comparison_service as scs

_PW = "fixpw" + "12345"
_JWT = ("ey" + "J" + "hbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" + "." + "ey" + "J"
        + "zdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4ifQ" + "." + "sig")

# raw exception text -> the exact exc_summary output
_GLUED = {
    "bearer_glued_url": (
        "Authorization: Bearer https://usr:" + _PW + "@h.test/p",
        "RuntimeError: Authorization: Bearer [REDACTED]://h.test/p",
    ),
    "hex32_glued_scheme": (
        "a" * 32 + "://usr:" + _PW + "@h.test/p",
        "RuntimeError: [TOKEN_REDACTED]://h.test/p",
    ),
    "jwt_glued_url": (
        _JWT + "https://usr:" + _PW + "@h.test/p",
        "RuntimeError: [JWT_REDACTED]://h.test/p",
    ),
    "long_hex_letter_scheme": (
        "b" * 40 + "://usr:" + _PW + "@h.test/p",
        "RuntimeError: [TOKEN_REDACTED]://h.test/p",
    ),
}


@pytest.mark.parametrize("raw,expected", list(_GLUED.values()), ids=list(_GLUED))
def test_exc_summary_url_userinfo_scrubbed_when_glued_to_a_key_shape(raw, expected):
    """The userinfo of a URL glued to a key shape is removed, and the key shape
    is still redacted: the URL scrub runs first, then the key patterns."""
    from app.services.log_scrub import exc_summary

    out = exc_summary(RuntimeError(raw))
    assert _PW not in out and "usr:" not in out, out
    assert out == expected, out


def test_exc_summary_space_separated_control_unchanged():
    """Control: with a space between the key shape and the URL, both scrubs
    applied in either order already gave this output."""
    from app.services.log_scrub import exc_summary

    out = exc_summary(RuntimeError("Bearer abc.def " + "https://usr:" + _PW + "@h.test/p"))
    assert out == "RuntimeError: Bearer [REDACTED] https://h.test/p", out


def test_exc_summary_type_name_is_one_line():
    from app.services.log_scrub import exc_summary

    weird = type("Weird\nName", (Exception,), {})
    assert exc_summary(weird("x")) == "Weird Name: x"
    assert exc_summary(weird("")) == "Weird Name"

    def _boom(self):
        raise RuntimeError("broken __str__")

    broken = type("Bad\r\nStr", (Exception,), {"__str__": _boom})
    assert exc_summary(broken()) == "<unprintable Bad Str>"


def test_exc_summary_leading_whitespace_does_not_use_up_the_budget():
    from app.services.log_scrub import exc_summary

    assert exc_summary(ValueError(" " * 250 + "detail")) == "ValueError: detail"
    assert exc_summary(ValueError("\n\n  bad")) == "ValueError: bad"
    assert exc_summary(ValueError(" \n\t ")) == "ValueError"
    # the cut still applies to the text that remains
    out = exc_summary(ValueError(" " * 50 + "x" * 500))
    assert out == "ValueError: " + "x" * 200, out


# ===========================================================================
# R2.5 -- the per-run reset of _verdict_model_downgraded
# ===========================================================================

_BLOCKED = "glock 19 vs ar-15"  # refused by the L1 query prefilter


@pytest.fixture
def _l1_refusal_env(monkeypatch):
    from app.services import audit_service

    spy = AsyncMock()
    monkeypatch.setattr(audit_service, "log_content_blocked", spy)
    monkeypatch.delenv("ENABLE_LLM_PREFLIGHT_BREAKER", raising=False)
    monkeypatch.delenv("ENABLE_BLOCKLIST_PRECISION_V2", raising=False)
    return spy


@pytest.mark.asyncio
async def test_verdict_marker_reset_at_run_start_sync(_l1_refusal_env):
    svc = scs.StructuredComparisonService()
    svc._verdict_model_downgraded = True  # a previous run's value on a reused instance
    out = await svc.compare_from_text(_BLOCKED)
    await asyncio.sleep(0)
    assert out.get("code") == "CONTENT_UNAVAILABLE", out
    assert out.get("layer") == "query_prefilter", out
    assert svc._verdict_model_downgraded is False


@pytest.mark.asyncio
async def test_verdict_marker_reset_at_run_start_streaming(_l1_refusal_env):
    svc = scs.StructuredComparisonService()
    svc._verdict_model_downgraded = True  # a previous run's value on a reused instance
    events = [ev async for ev in svc.compare_from_text_streaming(_BLOCKED)]
    await asyncio.sleep(0)
    assert events, events
    kind, payload = events[-1]
    assert kind == "error" and payload.get("code") == "CONTENT_UNAVAILABLE", events
    assert svc._verdict_model_downgraded is False
