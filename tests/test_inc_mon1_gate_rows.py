"""MON1 LLM-CREDENTIAL-HEALTH: the gate rows G1-G4 of GATE_MON1 GC-10 (written at GREEN).

- G1 (GC-5): the alert helper's fail-safe. With the private scope attribute the
  no-request-region recipe needs made unavailable, exactly ONE event is still sent
  (from the current scope), one constant WARNING is logged and nothing raises.
- G2 (GC-6): a transition suppressed by the cool-down logs the named WARNING
  `[LLM_CREDENTIAL] alert suppressed provider=%s state=%s cooldown_s=%d` once.
- G3 (GC-7): the manual trigger state `test` is sent at level error with the same
  alert tag (the owner's rule fires on it as on a real rejection).
- G4 (addendum A2-3): per-provider independence. OpenAI held in `rejected` across
  repeated failures emits no further event, while an Anthropic rejection in the same
  process (same instant) emits exactly one event tagged for Anthropic and an
  Anthropic recovery emits one recovery event; the OpenAI state is untouched.

Hermetic: no DSN, no network; sentry_sdk's entry points are replaced by recorders.
"""

import contextlib
import logging
import re

import sentry_sdk

from tests.test_inc_mon1_credential_health import (  # noqa: F401 -- fixtures re-used
    _alerts,
    _leaf,
    _mon1_env,
    _need,
    _sentry,
    _state,
    alert_rec,
    an_err,
    auth401,
)

SUPPRESSED_RE = re.compile(
    r"\[LLM_CREDENTIAL\] alert suppressed provider=(openai|anthropic|serper)"
    r" state=(ok|rejected|quota|exhausted) cooldown_s=\d+"
)
FALLBACK_TEXT = (
    "[LLM_CREDENTIAL] alert scope recipe unavailable; sent from the current scope"
)


def _capture_recorder(monkeypatch):
    calls = []

    def _capture(message, *args, **kwargs):
        calls.append((message, args, kwargs))
        return None

    monkeypatch.setattr(sentry_sdk, "capture_message", _capture)
    return calls


class _ScopeWithoutProcessors:
    """A scope stand-in whose private processor list is not there (an SDK change)."""

    def clear(self):
        return None


@contextlib.contextmanager
def _stub_scope():
    yield _ScopeWithoutProcessors()


def test_g1_fail_safe_sends_exactly_one_event(monkeypatch, caplog):
    fn = _need(_sentry(), "capture_credential_alert")
    calls = _capture_recorder(monkeypatch)
    monkeypatch.setattr(sentry_sdk, "isolation_scope", _stub_scope)
    monkeypatch.setattr(sentry_sdk, "new_scope", _stub_scope)
    with caplog.at_level(logging.INFO):
        assert fn("llm_credential", "openai", "rejected", 401) is None
    assert len(calls) == 1, calls
    message, _args, kwargs = calls[0]
    assert message == "credential_state"
    assert kwargs.get("level") == "error"
    assert kwargs.get("tags") == {
        "alert": "llm_credential",
        "provider": "openai",
        "state": "rejected",
        "status": "401",
    }
    assert kwargs.get("fingerprint") == ["llm_credential", "openai", "rejected"]
    warn = [r for r in caplog.records if r.getMessage() == FALLBACK_TEXT]
    assert len(warn) == 1 and warn[0].levelno == logging.WARNING


def test_g1_control_recipe_path_sends_one_event_and_no_warning(monkeypatch, caplog):
    fn = _need(_sentry(), "capture_credential_alert")
    calls = _capture_recorder(monkeypatch)
    with caplog.at_level(logging.INFO):
        assert fn("llm_credential", "openai", "rejected", 401) is None
    assert len(calls) == 1, calls
    assert not [r for r in caplog.records if r.getMessage() == FALLBACK_TEXT]


def test_g2_suppressed_transition_line(
    monkeypatch, caplog, alert_rec  # noqa: F811 -- the imported fixture
):
    leaf = _leaf()
    t = [30000.0]
    _need(leaf, "_monotonic")
    monkeypatch.setattr(leaf, "_monotonic", lambda: t[0])
    with caplog.at_level(logging.INFO):
        leaf.note_failure("openai", auth401(), "dispatch")
        t[0] += 5
        leaf.note_success("openai", "dispatch")
        t[0] += 5
        leaf.note_failure("openai", auth401(), "dispatch")
    lines = [r for r in caplog.records if SUPPRESSED_RE.fullmatch(r.getMessage())]
    assert len(lines) == 1, [r.getMessage() for r in caplog.records]
    assert lines[0].levelno == logging.WARNING
    got = SUPPRESSED_RE.fullmatch(lines[0].getMessage())
    assert (got.group(1), got.group(2)) == ("openai", "rejected")
    assert [c[2] for c in _alerts(alert_rec)] == ["rejected", "ok"]


def test_g3_manual_trigger_level_error(monkeypatch):
    fn = _need(_sentry(), "capture_credential_alert")
    calls = _capture_recorder(monkeypatch)
    fn("llm_credential", "openai", "test", None)
    fn("llm_credential", "openai", "ok", None)
    assert [c[2].get("level") for c in calls] == ["error", "info"]
    assert calls[0][2].get("tags") == {
        "alert": "llm_credential",
        "provider": "openai",
        "state": "test",
        "status": "none",
    }


def test_g4_per_provider_independence(
    monkeypatch, alert_rec  # noqa: F811 -- the imported fixture
):
    leaf = _leaf()
    _need(leaf, "_monotonic")
    monkeypatch.setattr(leaf, "_monotonic", lambda: 40000.0)
    for _ in range(5):
        leaf.note_failure("openai", auth401(), "dispatch")
    assert _alerts(alert_rec) == [("llm_credential", "openai", "rejected", 401)]
    leaf.note_failure(
        "anthropic",
        an_err("AuthenticationError", 401, "authentication_error"),
        "dispatch",
    )
    leaf.note_success("anthropic", "dispatch")
    assert _alerts(alert_rec) == [
        ("llm_credential", "openai", "rejected", 401),
        ("llm_credential", "anthropic", "rejected", 401),
        ("llm_credential", "anthropic", "ok", None),
    ]
    st = _state("openai")
    assert st["state"] == "rejected" and st["count"] == 5
    assert _state("anthropic")["state"] == "ok"
