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


# ---------------------------------------------------------------------------
# Fix round 1 (RULINGS_FIX1_MON1 F1-6): G5-G9 pin behaviour the GREEN bytes have;
# G10 pins the fixed cool-down window (F1-2); G11-G12 the pending rule (F1-1);
# G13-G14 the moderation rule (F1-3).
# ---------------------------------------------------------------------------
import asyncio  # noqa: E402
import sys  # noqa: E402
import types  # noqa: E402

from tests.test_inc_mon1_credential_health import (  # noqa: E402,F401
    LEAF,
    _client,
    _main,
    oa_err,
    quota_err,
)

MONITOR_FALLBACK = {"status": "ok", "providers": {}}


def test_g5_monitor_path_fails_open(monkeypatch):
    """GC-13 named check: the monitor path is never a bare 503. The leaf's view
    raising, or the leaf absent, answers the documented 200 fallback."""
    leaf = _leaf()

    def boom():
        raise RuntimeError("view")

    monkeypatch.setattr(leaf, "monitor_view", boom)
    r = _client().get("/health/llm")
    assert r.status_code == 200, r.status_code
    assert r.json() == MONITOR_FALLBACK
    monkeypatch.setitem(sys.modules, LEAF, None)
    r = _client().get("/health/llm")
    assert r.status_code == 200, r.status_code
    assert r.json() == MONITOR_FALLBACK


def test_g6_shutdown_cancels_and_awaits_the_probe_task(monkeypatch):
    """GC-13 named check: after the shutdown handler returns, the probe task is
    done AND cancelled (the handler awaited it) and the pointer is cleared."""
    main = _main()
    _need(main, "_stop_llm_credential_probe")
    seen = {}

    async def scenario():
        task = asyncio.ensure_future(asyncio.sleep(3600))
        await asyncio.sleep(0)
        monkeypatch.setattr(main, "_llm_probe_task", task)
        await main._stop_llm_credential_probe()
        seen["done"] = task.done()
        seen["cancelled"] = task.cancelled()
        seen["pointer"] = main._llm_probe_task
        if not task.done():
            task.cancel()

    asyncio.run(scenario())
    assert seen == {"done": True, "cancelled": True, "pointer": None}, seen


class _ScopeWithProcessors:
    def __init__(self):
        self._event_processors = [lambda event, hint: event]

    def clear(self):
        return None


@contextlib.contextmanager
def _scope_ok():
    yield _ScopeWithProcessors()


@contextlib.contextmanager
def _scope_exit_raises():
    yield _ScopeWithProcessors()
    raise RuntimeError("scope exit")


def test_g7_scope_exit_raising_after_the_send_is_one_event(monkeypatch, caplog):
    """GC-5: a scope exit that raises AFTER the send still yields exactly ONE event
    (the fail-safe never resends) and no fallback WARNING."""
    fn = _need(_sentry(), "capture_credential_alert")
    calls = _capture_recorder(monkeypatch)
    monkeypatch.setattr(sentry_sdk, "isolation_scope", _scope_ok)
    monkeypatch.setattr(sentry_sdk, "new_scope", _scope_exit_raises)
    with caplog.at_level(logging.INFO):
        assert fn("llm_credential", "openai", "rejected", 401) is None
    assert len(calls) == 1, calls
    assert not [r for r in caplog.records if r.getMessage() == FALLBACK_TEXT]


def test_g8_closed_set_guard_sends_nothing(monkeypatch):
    """GREEN deviation 5: a kind, provider or state outside the closed sets sends
    nothing."""
    fn = _need(_sentry(), "capture_credential_alert")
    calls = _capture_recorder(monkeypatch)
    for args in (
        ("other_kind", "openai", "rejected", 401),
        ("llm_credential", "other_provider", "rejected", 401),
        ("llm_credential", "openai", "other_state", 401),
    ):
        assert fn(*args) is None
    assert calls == []


def test_g9_health_snapshot_returns_copies(alert_rec):  # noqa: F811
    """A caller mutating the /health snapshot never changes the recorder."""
    leaf = _leaf()
    leaf.note_failure("openai", auth401(), "dispatch")
    snap = leaf.health_snapshot()
    snap["llm_credential"]["openai"]["state"] = "ok"
    snap["llm_credential"]["openai"]["count"] = 99
    snap["llm_credential"]["anthropic"] = {"state": "ok"}
    again = leaf.health_snapshot()["llm_credential"]
    assert set(again) == {"openai"}
    assert again["openai"]["state"] == "rejected" and again["openai"]["count"] == 1


def _clocked(monkeypatch, start):
    leaf = _leaf()
    _need(leaf, "_monotonic")
    t = [start]
    monkeypatch.setattr(leaf, "_monotonic", lambda: t[0])
    return leaf, t


def _states(rec):
    return [c[2] for c in _alerts(rec)]


def test_g10_cooldown_is_a_fixed_window(monkeypatch, alert_rec):  # noqa: F811
    """F1-2: the cool-down runs from the last event actually EMITTED for that
    (kind, provider, state); a suppressed transition does not extend it."""
    leaf, t = _clocked(monkeypatch, 50000.0)
    leaf.note_failure("openai", auth401(), "dispatch")  # t=0 rejected emitted
    t[0] += 5
    leaf.note_success("openai", "dispatch")  # t=5 ok emitted
    t[0] += 595
    leaf.note_failure("openai", auth401(), "dispatch")  # t=600 suppressed
    t[0] += 5
    leaf.note_success("openai", "dispatch")  # t=605 suppressed
    assert _states(alert_rec) == ["rejected", "ok"]
    t[0] = 50000.0 + 950
    leaf.note_failure("openai", auth401(), "dispatch")  # t=950: 950 s after t=0
    assert _states(alert_rec) == ["rejected", "ok", "rejected"]


def test_g11_a_suppressed_rejection_is_never_lost(monkeypatch, alert_rec):  # noqa: F811
    """F1-1: rejected, ok, rejected inside the cool-down (suppressed), then hours of
    failures: the held rejection is emitted ONCE by the first confirming failure
    after the cool-down, never before it, never twice."""
    leaf, t = _clocked(monkeypatch, 60000.0)
    leaf.note_failure("openai", auth401(), "dispatch")  # t=0 emitted
    t[0] += 5
    leaf.note_success("openai", "dispatch")  # t=5 emitted
    t[0] += 5
    leaf.note_failure("openai", auth401(), "dispatch")  # t=10 suppressed, pending
    t[0] += 90
    leaf.note_failure("openai", auth401(), "dispatch")  # t=100 inside: nothing
    assert _states(alert_rec) == ["rejected", "ok"]
    t[0] = 60000.0 + 950
    leaf.note_failure("openai", auth401(), "dispatch")  # t=950 cooled: emitted once
    assert _alerts(alert_rec)[-1] == ("llm_credential", "openai", "rejected", 401)
    for _ in range(10):
        t[0] += 3600
        leaf.note_failure("openai", auth401(), "dispatch")
    assert _states(alert_rec) == ["rejected", "ok", "rejected"]
    assert _state()["state"] == "rejected"


def test_g11_a_transition_out_clears_the_pending_mark(
    monkeypatch, alert_rec  # noqa: F811
):
    """F1-1: a transition out of the held state clears its pending mark without
    emitting; a later return to that state emits normally, and the cleared mark
    never fires a second event."""
    leaf, t = _clocked(monkeypatch, 70000.0)
    leaf.note_failure("openai", auth401(), "dispatch")  # t=0 rejected emitted
    t[0] += 5
    leaf.note_success("openai", "dispatch")  # t=5 ok emitted
    t[0] += 5
    leaf.note_failure("openai", auth401(), "dispatch")  # t=10 suppressed, pending
    t[0] += 10
    leaf.note_success("openai", "dispatch")  # t=20 out of rejected: mark cleared
    assert _states(alert_rec) == ["rejected", "ok"]
    t[0] = 70000.0 + 950
    leaf.note_failure("openai", auth401(), "dispatch")  # t=950 a new transition
    assert _states(alert_rec) == ["rejected", "ok", "rejected"]
    t[0] += 1900
    leaf.note_failure("openai", auth401(), "dispatch")  # a confirming failure
    assert _states(alert_rec) == ["rejected", "ok", "rejected"]


def test_g12_a_suppressed_recovery_is_never_lost(monkeypatch, alert_rec):  # noqa: F811
    """F1-1: a recovery suppressed by the ok cool-down is emitted once by the first
    served call after that cool-down, so the newest event agrees with `ok`."""
    leaf, t = _clocked(monkeypatch, 80000.0)
    leaf.note_failure("openai", auth401(), "dispatch")  # t=0 rejected emitted
    t[0] += 5
    leaf.note_success("openai", "dispatch")  # t=5 ok emitted
    t[0] += 5
    leaf.note_failure("openai", quota_err(), "dispatch")  # t=10 quota emitted
    t[0] += 5
    leaf.note_success("openai", "dispatch")  # t=15 ok suppressed, pending
    t[0] += 85
    leaf.note_success("openai", "dispatch")  # t=100 inside: nothing
    assert _states(alert_rec) == ["rejected", "ok", "quota"]
    t[0] = 80000.0 + 910
    leaf.note_success("openai", "dispatch")  # t=910 cooled: emitted once
    t[0] += 5000
    leaf.note_success("openai", "dispatch")
    assert _alerts(alert_rec) == [
        ("llm_credential", "openai", "rejected", 401),
        ("llm_credential", "openai", "ok", None),
        ("llm_credential", "openai", "quota", 429),
        ("llm_credential", "openai", "ok", None),
    ]
    assert _state()["state"] == "ok"


def test_g13_moderation_success_never_clears_quota_or_dispatch_403(
    monkeypatch, alert_rec  # noqa: F811
):
    """F1-3: a moderation success proves authentication only: it never clears a
    quota state (dispatch- or moderation-sourced) or a dispatch-sourced 403, and
    emits no recovery event while one is held. A served dispatch clears either."""
    leaf, t = _clocked(monkeypatch, 90000.0)
    leaf.note_failure("openai", quota_err(), "dispatch")
    leaf.note_success("openai", "moderation")
    st = _state()
    assert st["state"] == "quota" and st["source"] == "dispatch" and st["count"] == 1
    assert _states(alert_rec) == ["quota"]
    leaf.note_success("openai", "dispatch")
    assert _state()["state"] == "ok"
    t[0] += 1000
    leaf.note_failure("openai", oa_err("PermissionDeniedError", 403), "dispatch")
    leaf.note_success("openai", "moderation")
    st = _state()
    assert st["state"] == "rejected" and st["last_status"] == 403
    assert st["source"] == "dispatch"
    assert _states(alert_rec) == ["quota", "ok", "rejected"]
    leaf._reset_credential_health_state()
    leaf.note_failure("openai", quota_err(), "moderation")
    leaf.note_success("openai", "moderation")
    assert _state()["state"] == "quota"


def test_g14_moderation_success_clears_a_401_and_only_after_the_call(
    monkeypatch, alert_rec  # noqa: F811
):
    """F1-3: through the content-safety call site, a moderation call that RAISES
    from a held dispatch 401 emits no recovery event (note_success stays after the
    awaited call); a moderation success then clears the 401 with one recovery
    event."""
    from app.services import content_safety_service as css
    from app.services import openai_service

    leaf, t = _clocked(monkeypatch, 95000.0)
    leaf.note_failure("openai", auth401(), "dispatch")
    outcomes = [
        auth401(),
        types.SimpleNamespace(results=[types.SimpleNamespace(flagged=False)]),
    ]

    async def mod_create(**kw):
        item = outcomes.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item

    fake = types.SimpleNamespace(moderations=types.SimpleNamespace(create=mod_create))
    monkeypatch.setattr(openai_service, "get_client", lambda: fake)
    svc = css.ContentSafetyService()
    res = asyncio.run(svc.moderate_output("a plain sentence"))
    assert res.allowed is True
    assert _states(alert_rec) == ["rejected"]
    assert _state()["state"] == "rejected"
    res = asyncio.run(svc.moderate_output("a plain sentence"))
    assert res.allowed is True
    st = _state()
    assert st["state"] == "ok" and st["source"] == "moderation"
    assert _states(alert_rec) == ["rejected", "ok"]


# ---------------------------------------------------------------------------
# Final round (RULINGS_REBASE_MON1 RB-MON1F-3): G15 pins the stamp of a late
# (pending) event (the re-verifier's surviving mutant RV9); G16 pins that the
# test reset clears the pending marks (the surviving mutant RV12).
# ---------------------------------------------------------------------------


def test_g15_a_late_event_stamps_the_cooldown(
    monkeypatch, caplog, alert_rec  # noqa: F811
):
    """F1-1 / F1-2: the late (pending) event is an emitted event, so it stamps the
    fixed window of its (kind, provider, state). A flap back into the same state
    inside ALERT_COOLDOWN_SECONDS after the late event sends NO second event (the
    suppressed WARNING is logged instead)."""
    leaf, t = _clocked(monkeypatch, 110000.0)
    leaf.note_failure("openai", auth401(), "dispatch")  # t=0 rejected emitted
    t[0] += 5
    leaf.note_success("openai", "dispatch")  # t=5 ok emitted
    t[0] += 5
    leaf.note_failure("openai", auth401(), "dispatch")  # t=10 suppressed, pending
    t[0] = 110000.0 + 950
    leaf.note_failure("openai", auth401(), "dispatch")  # t=950 late rejected sent
    assert _states(alert_rec) == ["rejected", "ok", "rejected"]
    t[0] += 5
    leaf.note_success("openai", "dispatch")  # t=955 ok: 950 s after t=5, emitted
    assert _states(alert_rec) == ["rejected", "ok", "rejected", "ok"]
    t[0] += 5
    caplog.clear()  # the t=10 suppression logged its own line
    with caplog.at_level(logging.INFO):
        # t=960: 10 s after the late event, 960 s after the first rejected event.
        leaf.note_failure("openai", auth401(), "dispatch")
    assert _states(alert_rec) == ["rejected", "ok", "rejected", "ok"]
    lines = [r for r in caplog.records if SUPPRESSED_RE.fullmatch(r.getMessage())]
    assert len(lines) == 1, [r.getMessage() for r in caplog.records]
    got = SUPPRESSED_RE.fullmatch(lines[0].getMessage())
    assert (got.group(1), got.group(2)) == ("openai", "rejected")
    assert _state()["state"] == "rejected"


def test_g16_the_test_reset_clears_the_pending_marks(
    monkeypatch, alert_rec  # noqa: F811
):
    """The conftest reset seam clears the pending marks with the state and the
    cool-down stamps, so no held event leaks from one test into the next."""
    leaf, t = _clocked(monkeypatch, 120000.0)
    pending = _need(leaf, "_PENDING")
    leaf.note_failure("openai", auth401(), "dispatch")  # t=0 rejected emitted
    t[0] += 5
    leaf.note_success("openai", "dispatch")  # t=5 ok emitted
    t[0] += 5
    leaf.note_failure("openai", auth401(), "dispatch")  # t=10 suppressed, pending
    assert ("openai", "rejected") in pending, dict(pending)
    leaf._reset_credential_health_state()
    assert dict(pending) == {}
    assert leaf.health_snapshot() == {}
