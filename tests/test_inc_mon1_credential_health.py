"""MON1 LLM-CREDENTIAL-HEALTH: the frozen RED file (recorder, hooks, alert, /health, monitor).

Spec: .qa-s80/MON1_UNIT_SPEC.md, amended by the review MON1_SPEC_REVIEW.md and the
orchestrator rulings R-MON1-16..30 (RULINGS_INC_BATCH1.md, section MON1). The passive
part is UNFLAGGED (R-MON1-1); the dark probe has its own file (test_inc_mon1_probe.py).

Every RED row fails at base on an AssertionError only: a missing module or symbol is
read through find_spec / getattr helpers and asserted, never imported bare. PIN rows
(G01, G02, G03, HE02, S04, S05, T01) are green at base and run with the FULL unit
configuration plus call recorders (the B1 rule). Hermetic: no network, no .env, no real
credential; every credential-shaped sentinel is built at run time.

Seam names this file freezes beyond the spec text (rulings R-MON1-21 / R-MON1-22 name
the behaviour, not the seam): llm_credential_health.ALERT_COOLDOWN_SECONDS (900.0),
llm_credential_health._monotonic (the clock the cool-down and the uptime read) and
llm_credential_health._STARTED_AT (the monotonic start mark of the process).
"""

import asyncio
import ast
import base64
import hashlib
import importlib
import importlib.util
import json
import logging
import os
import re
import subprocess
import sys
import types
import uuid
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEAF = "app.services.llm_credential_health"

# Run-time sentinels (never a provider-shaped literal).
SDK_SENTINEL = "SDK" + "MSG" + "SENTINEL" + "m1"
KEY_SENTINEL = "syn" + "thetic" + "-mon1-" + "c4d5"
ISO_Z = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
L1_RE = re.compile(
    r"\[LLM_CREDENTIAL\] provider=(openai|anthropic) state=(ok|rejected|quota)"
    r" status=(\d{3}|none) source=(dispatch|probe|moderation)"
)
OPENAI_QUOTA_CODES = (
    "credit_balance_exhausted",
    "insufficient_quota",
    "organization_spend_limit_exceeded",
    "project_spend_limit_exceeded",
    "organization_usage_limit_exceeded",
)
ROLE_FLAGS = (
    "ENABLE_ANTHROPIC_TEXT",
    "ENABLE_ANTHROPIC_VISION",
    "ENABLE_ANTHROPIC_VERDICT",
    "ENABLE_ANTHROPIC_CRITIC",
    "ENABLE_ANTHROPIC_MODERATION",
)
SPEND_KNOBS = {
    "LLM_SPEND_CAP_LIVE_USD": "7.5",
    "LLM_SPEND_CAP_ESCALATION_USD": "2.5",
    "LLM_SPEND_CAP_SEARCH_USD": "1.5",
    "LLM_SPEND_CAP_OFFCLOCK_USD": "3.5",
    "LLM_SPEND_CHOKEPOINT_LANE": "live",
    "LLM_SPEND_ENTRY_RESERVE_USD": "0.05",
    "LLM_SPEND_FALLBACK_OUTPUT_TOKENS": "512",
    "LLM_SPEND_MEMO_SECONDS": "5",
    "LLM_SPEND_REDIS_TIMEOUT_SECONDS": "0.5",
}

# G01: sha256 of ast.dump(include_attributes=False) of the gating functions, measured
# AT BASE a74caba7 by the RED agent (base64; the name carries no scanner keyword).
GATING_AST_B64 = {
    (
        "api_budget_service",
        "_openai_server_answered",
    ): "+1v5ZolWlgQU7ClwOwMv+Qw9p2NR9WRIBR+Uc9X9gYk=",
    (
        "api_budget_service",
        "_openai_failure_is_transient",
    ): "S81+Ie8U4xYp5pFxAcPS6H21Z8Febi4oA2mqiI6HyD8=",
    (
        "api_budget_service",
        "openai_record_failure",
    ): "/lR3b+SPgxSz4ii8SJfCV/JIF3PLcr7WcaXWlLGV7oQ=",
    (
        "api_budget_service",
        "openai_record_success",
    ): "D6O1mufWV2WZ1bpFAECq5IvYszZoVQ/IfzzpXzYNXeQ=",
    (
        "api_budget_service",
        "openai_release_half_open_probe",
    ): "q0jxr1u7kORWVDAqYKtZONAxmT+DT4dCaxROtqZhwjI=",
    (
        "api_budget_service",
        "_openai_dispatch_admission",
    ): "KIsKoDsZFBNsulYV0psdgmgJNWpp3LNEEZN9HgA9Mz0=",
    ("llm_router", "_classify"): "KdEArRT1JUoS9RDZTF9Q5XmtbXoScCilpkLmn06NZK0=",
    ("llm_router", "route"): "3KbEVkq0XFTnKlDABtL3WrxETdqMs+jLq83wEfuWr+I=",
    ("llm_router", "_moderate_step"): "afvq34JenJAeIZH1w90STQjcQsW6RV503jRKVL+G1zI=",
    (
        "llm_router",
        "moderate_with_claude",
    ): "Y5HyAS5q2TXH/BZE/pa7frns2Ixbl6v71twRLMt5KDA=",
}
# Y01: sha256 of repr(sorted(tests/_env_safety.CREDENTIALS_UNSET)) (base64); re-pinned by S81-07 (E1: MEAS_ANTHROPIC_TEST_KEY joined the list; RULINGS_MERGE_S81_07 M-10).
ENV_SAFETY_UNSET_B64 = "KuyarpanjcDiW1QGpvl+SLg0lN7zqgAm1DCpdi9efgM="


# ---------------------------------------------------------------------------
# Helpers (a missing module or symbol is an AssertionError, never an ImportError)
# ---------------------------------------------------------------------------
def _leaf():
    try:
        spec = importlib.util.find_spec(LEAF)
    except (ImportError, ValueError):
        spec = None
    assert (
        spec is not None
    ), "app/services/llm_credential_health.py is absent (MON1 3.1)"
    return importlib.import_module(LEAF)


def _need(mod, name):
    assert hasattr(
        mod, name
    ), f"{getattr(mod, '__name__', mod)}.{name} is missing (MON1)"
    return getattr(mod, name)


def _main():
    import app.main as app_main

    return app_main


def _abs():
    from app.services import api_budget_service

    return api_budget_service


def _router():
    from app.services import llm_router

    return llm_router


def _serper():
    from app.services import serper_service

    return serper_service


def _sentry():
    from app.services import sentry_service

    return sentry_service


def _snapshot():
    return _need(_leaf(), "health_snapshot")()


def _client():
    from fastapi.testclient import TestClient

    return TestClient(_main().app)


async def _capture(coro):
    try:
        return "ok", await coro
    except BaseException as exc:  # noqa: BLE001
        if isinstance(exc, (KeyboardInterrupt, SystemExit)):
            raise
        return "raised", exc


def _run(coro):
    return asyncio.run(_capture(coro))


# Real SDK exception objects, built from the pinned classes.
def _httpx2():
    return importlib.import_module("httpx2")


def _oa():
    return importlib.import_module("openai")


def _anth():
    return importlib.import_module("anthropic")


def _resp(status):
    h = _httpx2()
    req = h.Request("POST", "https://example.invalid/v1/x")
    return h.Response(status, request=req, json={"error": {"message": SDK_SENTINEL}})


def oa_err(cls_name, status, body=None, message=None):
    cls = getattr(_oa(), cls_name)
    return cls(message or SDK_SENTINEL, response=_resp(status), body=body)


def oa_timeout():
    h = _httpx2()
    return _oa().APITimeoutError(
        request=h.Request("POST", "https://example.invalid/v1/x")
    )


def oa_connection():
    h = _httpx2()
    return _oa().APIConnectionError(
        request=h.Request("POST", "https://example.invalid/v1/x")
    )


def an_err(cls_name, status, err_type=None, message=None):
    """An anthropic SDK exception from whatever `anthropic` module is loaded (the real
    pinned SDK, or the S81-06 fake hierarchy when a sibling suite installed it)."""
    sdk = _anth()
    cls = getattr(sdk, cls_name)
    body = (
        {"type": "error", "error": {"type": err_type, "message": SDK_SENTINEL}}
        if err_type
        else None
    )
    exc = cls(message or SDK_SENTINEL, response=_resp(status), body=body)
    if getattr(exc, "status_code", None) != status:
        exc.status_code = status
    if err_type and getattr(exc, "type", None) != err_type:
        exc.type = err_type
    return exc


def quota_err(code="insufficient_quota", err_type="insufficient_quota"):
    body = {"message": SDK_SENTINEL, "code": code, "type": err_type}
    return oa_err("RateLimitError", 429, body=body)


def auth401(code="invalid_api_key"):
    return oa_err(
        "AuthenticationError",
        401,
        body={"message": SDK_SENTINEL, "code": code, "type": "invalid_request_error"},
    )


class _Rec:
    """An ordered call recorder shared by every patched function of one test."""

    def __init__(self):
        self.calls = []

    def fn(self, name, ret=None):
        def _f(*a, **k):
            self.calls.append((name, a, k))
            return ret

        return _f

    def afn(self, name, ret=None):
        async def _f(*a, **k):
            self.calls.append((name, a, k))
            return ret

        return _f

    def names(self):
        return [c[0] for c in self.calls]

    def count(self, name):
        return self.names().count(name)


def _alerts(rec):
    return [c[1] for c in rec.calls if c[0] == "capture_credential_alert"]


@pytest.fixture(autouse=True)
def _mon1_env(monkeypatch):
    """app.main first (the dotenv guard), then every flag this file depends on set or
    deleted explicitly, and the MON1 state seams reset when they exist."""
    _main()
    for name in ROLE_FLAGS + (
        "ENABLE_LLM_CREDENTIAL_PROBE",
        "LLM_CREDENTIAL_PROBE_INTERVAL_SECONDS",
        "ENABLE_LLM_PREFLIGHT_BREAKER",
        "ENABLE_LLM_SPEND_BREAKER",
        "ENABLE_SERPER_KEY_STATE_MEMO",
        "SERPER_API_KEYS",
        "ANTHROPIC_API_KEY",
        "ENABLE_SONNET_ESCALATION",
        "ENABLE_OPENAI_PRE_V3",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", KEY_SENTINEL + "-oa")
    leaf = sys.modules.get(LEAF)
    if leaf is not None and hasattr(leaf, "_reset_credential_health_state"):
        leaf._reset_credential_health_state()
    ss = _serper()
    if hasattr(ss, "_reset_serper_keys_state"):
        ss._reset_serper_keys_state()
    yield
    leaf = sys.modules.get(LEAF)
    if leaf is not None and hasattr(leaf, "_reset_credential_health_state"):
        leaf._reset_credential_health_state()
    if hasattr(ss, "_reset_serper_keys_state"):
        ss._reset_serper_keys_state()


@pytest.fixture
def alert_rec(monkeypatch):
    rec = _Rec()
    monkeypatch.setattr(
        _sentry(),
        "capture_credential_alert",
        rec.fn("capture_credential_alert"),
        raising=False,
    )
    return rec


def _full_config(monkeypatch, preflight=False, spend=False):
    """The FULL unit configuration (B1 rule): every flag in the row's state, every knob
    and credential name set to a synthetic value."""
    monkeypatch.setenv("ENABLE_LLM_PREFLIGHT_BREAKER", "true" if preflight else "false")
    monkeypatch.setenv("ENABLE_LLM_SPEND_BREAKER", "true" if spend else "false")
    for k, v in SPEND_KNOBS.items():
        monkeypatch.setenv(k, v)
    monkeypatch.setenv("ENABLE_ANTHROPIC_TEXT", "true")
    monkeypatch.setenv("ENABLE_ANTHROPIC_MODERATION", "true")
    monkeypatch.setenv("ANTHROPIC_API_KEY", KEY_SENTINEL + "-an")
    monkeypatch.setenv(
        "SERPER_API_KEYS", uuid.uuid4().hex[:8] + "-s1," + uuid.uuid4().hex[:8] + "-s2"
    )
    monkeypatch.setenv("ENABLE_LLM_CREDENTIAL_PROBE", "false")
    monkeypatch.setenv("LLM_CREDENTIAL_PROBE_INTERVAL_SECONDS", "600")


def _openai_recorders(monkeypatch, rec):
    a = _abs()
    from app.services import llm_spend_breaker as sb

    monkeypatch.setattr(a, "openai_record_failure", rec.fn("openai_record_failure"))
    monkeypatch.setattr(a, "openai_record_success", rec.fn("openai_record_success"))
    monkeypatch.setattr(
        a, "openai_release_half_open_probe", rec.fn("openai_release_half_open_probe")
    )
    monkeypatch.setattr(a, "record_openai_response", rec.fn("record_openai_response"))
    monkeypatch.setattr(a, "record_failure", rec.fn("abs.record_failure"))
    monkeypatch.setattr(a, "record_success", rec.fn("abs.record_success"))
    monkeypatch.setattr(
        sb, "admit_openai_dispatch", rec.afn("admit_openai_dispatch", ret=object())
    )
    monkeypatch.setattr(
        sb, "record_openai_response_soon", rec.fn("record_openai_response_soon")
    )
    monkeypatch.setattr(sb, "admit_async", rec.afn("admit_async"))
    monkeypatch.setattr(sb, "record_soon", rec.fn("record_soon"))


def _fake_openai_client(rec, outcome):
    async def create(**kw):
        rec.calls.append(("create", (), {}))
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome

    return types.SimpleNamespace(
        chat=types.SimpleNamespace(completions=types.SimpleNamespace(create=create))
    )


def _kw():
    from app.services import model_config

    return {
        "model": model_config.standard_model(),
        "messages": [{"role": "user", "content": "x"}],
        "max_tokens": 5,
    }


def _state(provider="openai"):
    snap = _snapshot()
    return (snap.get("llm_credential") or {}).get(provider)


# ---------------------------------------------------------------------------
# L: the recorder leaf
# ---------------------------------------------------------------------------
def test_l01_leaf_exists_and_import_rule():
    leaf = _leaf()
    tree = ast.parse(Path(leaf.__file__).read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".")[0] in sys.stdlib_module_names, alias.name
        if isinstance(node, ast.ImportFrom):
            assert (
                node.module and node.module.split(".")[0] in sys.stdlib_module_names
            ), node.module
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            assert "://" not in node.value, "URL literal in the leaf"
            for frag in ("gpt-", "claude-", "omni-moderation"):
                assert frag not in node.value, "model-id literal in the leaf"
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            assert node.func.attr not in (
                "error",
                "exception",
                "critical",
            ), "an ERROR-level log call in the leaf"


L02_CASES = [
    ("AuthenticationError", 401, None, None, ("rejected", 401)),
    ("PermissionDeniedError", 403, None, None, ("rejected", 403)),
    ("APIStatusError", 401, None, None, ("rejected", 401)),
    ("APIStatusError", 403, None, None, ("rejected", 403)),
    (
        "RateLimitError",
        429,
        {"code": "rate_limit_exceeded", "type": "requests"},
        None,
        None,
    ),
    (
        "RateLimitError",
        429,
        {"code": "slow_down", "type": "rate_limit_error"},
        None,
        None,
    ),
    ("RateLimitError", 429, None, None, None),
    ("BadRequestError", 400, None, "invalid_api_key 401 " + SDK_SENTINEL, None),
    ("NotFoundError", 404, None, None, None),
    ("InternalServerError", 500, None, None, None),
    ("ConflictError", 409, None, None, None),
    ("UnprocessableEntityError", 422, None, None, None),
]


@pytest.mark.parametrize("cls_name,status,body,message,expected", L02_CASES)
def test_l02_openai_classify_real_classes(cls_name, status, body, message, expected):
    classify = _need(_leaf(), "classify")
    exc = oa_err(cls_name, status, body=body, message=message)
    assert classify("openai", exc) == expected


@pytest.mark.parametrize("code", OPENAI_QUOTA_CODES)
def test_l02_openai_quota_codes(code):
    """R-MON1-16: every structured out-of-credit code on a 429 is quota."""
    classify = _need(_leaf(), "classify")
    assert classify("openai", quota_err(code=code, err_type="requests")) == (
        "quota",
        429,
    )


def test_l02_openai_quota_type_only():
    """R-MON1-16: the structured type insufficient_quota alone is quota."""
    classify = _need(_leaf(), "classify")
    assert classify("openai", quota_err(code=None, err_type="insufficient_quota")) == (
        "quota",
        429,
    )


@pytest.mark.parametrize(
    "make",
    [
        oa_timeout,
        oa_connection,
        lambda: asyncio.TimeoutError(),
        lambda: ValueError(SDK_SENTINEL),
    ],
)
def test_l02_openai_non_sdk_and_transport(make):
    classify = _need(_leaf(), "classify")
    assert classify("openai", make()) is None


L03_CASES = [
    ("AuthenticationError", 401, None, None, ("rejected", 401)),
    ("PermissionDeniedError", 403, None, None, ("rejected", 403)),
    ("APIStatusError", 402, "billing_error", None, ("quota", 402)),
    ("RateLimitError", 429, "rate_limit_error", None, None),
    ("OverloadedError", 529, "overloaded_error", None, None),
    (
        "BadRequestError",
        400,
        "invalid_request_error",
        "credit balance is too low " + SDK_SENTINEL,
        None,
    ),
    ("InternalServerError", 500, "api_error", None, None),
]


@pytest.mark.parametrize("cls_name,status,err_type,message,expected", L03_CASES)
def test_l03_anthropic_classify(cls_name, status, err_type, message, expected):
    classify = _need(_leaf(), "classify")
    exc = an_err(cls_name, status, err_type=err_type, message=message)
    assert classify("anthropic", exc) == expected


def test_l04_record_shape_repeat_and_change():
    leaf = _leaf()
    _need(leaf, "note_failure")("openai", auth401(), "dispatch")
    snap = _snapshot()
    assert set(snap) == {"llm_credential"}
    rec = snap["llm_credential"]["openai"]
    assert set(rec) == {"state", "last_status", "at", "source", "count"}
    assert (
        rec["state"] == "rejected"
        and rec["last_status"] == 401
        and rec["source"] == "dispatch"
    )
    assert rec["count"] == 1 and ISO_Z.match(rec["at"])
    leaf.note_failure("openai", auth401(), "dispatch")
    assert _state()["count"] == 2
    _need(leaf, "note_success")("openai", "dispatch")
    assert _state()["state"] == "ok" and _state()["count"] == 1


def test_l05_recovery():
    leaf = _leaf()
    _need(leaf, "note_failure")("openai", auth401(), "dispatch")
    _need(leaf, "note_success")("openai", "dispatch")
    assert _state()["state"] == "ok" and _state()["last_status"] is None


def test_l06_empty_and_reset():
    leaf = _leaf()
    assert _snapshot() == {}
    _need(leaf, "note_failure")("openai", auth401(), "dispatch")
    assert _snapshot() != {}
    _need(leaf, "_reset_credential_health_state")()
    assert _snapshot() == {}


def _no_raise(fn, *args):
    """Call fn; an escaping exception is reported as an AssertionError."""
    try:
        return fn(*args)
    except Exception as exc:  # noqa: BLE001
        raise AssertionError("raised " + type(exc).__name__) from None


def test_l07_never_raises(monkeypatch, alert_rec):
    leaf = _leaf()
    note_failure = _need(leaf, "note_failure")
    note_success = _need(leaf, "note_success")

    class Weird(Exception):
        @property
        def status_code(self):
            raise RuntimeError("boom")

        @property
        def code(self):
            raise RuntimeError("boom")

    assert _no_raise(note_failure, "openai", Weird(), "dispatch") is None
    assert _no_raise(note_failure, "x", auth401(), "dispatch") is None
    assert _no_raise(note_failure, "openai", auth401(), "y") is None
    assert _no_raise(note_success, "x", "dispatch") is None
    assert _no_raise(note_success, "openai", "y") is None
    assert _snapshot() == {}

    def boom(*a, **k):
        raise RuntimeError("emit")

    monkeypatch.setattr(_sentry(), "capture_credential_alert", boom, raising=False)
    assert _no_raise(note_failure, "openai", auth401(), "dispatch") is None
    assert _state()["state"] == "rejected"
    _need(leaf, "_transition")
    monkeypatch.setattr(leaf, "_transition", boom)
    assert _no_raise(note_success, "openai", "dispatch") is None
    assert _no_raise(note_failure, "openai", auth401(), "dispatch") is None


def test_l08_event_rule_same_instant(alert_rec):
    """R-MON1-21 re-pin: every transition emits, subject to the 900 s cool-down per
    (provider, state); all at one instant: rejected, ok, (rejected cooled), quota, (ok cooled).
    """
    leaf = _leaf()
    for _ in range(3):
        _need(leaf, "note_failure")("openai", auth401(), "dispatch")
    leaf.note_success("openai", "dispatch")
    leaf.note_failure("openai", auth401(), "dispatch")
    leaf.note_failure("openai", quota_err(), "dispatch")
    leaf.note_success("openai", "dispatch")
    assert _alerts(alert_rec) == [
        ("llm_credential", "openai", "rejected", 401),
        ("llm_credential", "openai", "ok", None),
        ("llm_credential", "openai", "quota", 429),
    ]


def test_l09_no_event_on_a_first_ok(alert_rec):
    _need(_leaf(), "note_success")("openai", "dispatch")
    assert _state()["state"] == "ok"
    assert _alerts(alert_rec) == []


def test_l10_l1_line(caplog, alert_rec):
    leaf = _leaf()
    with caplog.at_level(logging.INFO):
        _need(leaf, "note_failure")("openai", auth401(), "dispatch")
        leaf.note_failure("openai", auth401(), "dispatch")
        leaf.note_success("openai", "dispatch")
        leaf.note_failure("openai", quota_err(), "moderation")
    l1 = [r for r in caplog.records if L1_RE.fullmatch(r.getMessage())]
    assert [r.levelno for r in l1] == [logging.WARNING] * 3
    assert [L1_RE.fullmatch(r.getMessage()).group(2) for r in l1] == [
        "rejected",
        "ok",
        "quota",
    ]
    for r in caplog.records:
        text = r.getMessage() + repr(r.args)
        assert SDK_SENTINEL not in text and KEY_SENTINEL not in text


def _clock(monkeypatch, leaf, t):
    _need(leaf, "_monotonic")
    monkeypatch.setattr(leaf, "_monotonic", lambda: t[0])


def test_l11_second_outage_after_the_cooldown_emits_again(monkeypatch, alert_rec):
    """R-MON1-21: rejected, ok, rejected again AFTER the interval -> two alert events."""
    leaf = _leaf()
    assert _need(leaf, "ALERT_COOLDOWN_SECONDS") == 900.0
    t = [10000.0]
    _clock(monkeypatch, leaf, t)
    leaf.note_failure("openai", auth401(), "dispatch")
    t[0] += 10
    leaf.note_success("openai", "dispatch")
    t[0] += 1000
    leaf.note_failure("openai", auth401(), "dispatch")
    states = [c[2] for c in _alerts(alert_rec)]
    assert states == ["rejected", "ok", "rejected"]


def test_l12_inside_the_cooldown_one_event_and_one_warning(
    monkeypatch, caplog, alert_rec
):
    """R-MON1-21: inside the interval -> ONE alert event; the suppressed transition logs
    one WARNING and /health still updates."""
    leaf = _leaf()
    t = [20000.0]
    _clock(monkeypatch, leaf, t)
    with caplog.at_level(logging.INFO):
        leaf.note_failure("openai", auth401(), "dispatch")
        t[0] += 10
        leaf.note_success("openai", "dispatch")
        t[0] += 10
        leaf.note_failure("openai", auth401(), "dispatch")
    assert [c[2] for c in _alerts(alert_rec)] == ["rejected", "ok"]
    warn = [
        r for r in caplog.records if r.name == LEAF and r.levelno == logging.WARNING
    ]
    l1 = [r for r in warn if L1_RE.fullmatch(r.getMessage())]
    assert len(l1) == 3 and len(warn) == 4, [r.getMessage() for r in warn]
    assert _state()["state"] == "rejected"


# ---------------------------------------------------------------------------
# H: the hooks at the dispatch chokepoints
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("spend", [False, True])
def test_h01_flag_off_401(monkeypatch, alert_rec, spend):
    _full_config(monkeypatch, preflight=False, spend=spend)
    rec = _Rec()
    _openai_recorders(monkeypatch, rec)
    exc = auth401()
    kind, got = _run(_abs().guarded_llm_create(_fake_openai_client(rec, exc), **_kw()))
    assert kind == "raised" and got is exc
    for n in (
        "openai_record_failure",
        "openai_record_success",
        "openai_release_half_open_probe",
        "record_openai_response",
        "record_openai_response_soon",
    ):
        assert rec.count(n) == 0, n
    st = _state()
    assert (
        st
        and st["state"] == "rejected"
        and st["last_status"] == 401
        and st["source"] == "dispatch"
    )


@pytest.mark.parametrize("spend", [False, True])
def test_h02_flag_off_success(monkeypatch, alert_rec, spend):
    _full_config(monkeypatch, preflight=False, spend=spend)
    rec = _Rec()
    _openai_recorders(monkeypatch, rec)
    resp = types.SimpleNamespace(choices=[], usage=None)
    kind, got = _run(_abs().guarded_llm_create(_fake_openai_client(rec, resp), **_kw()))
    assert kind == "ok" and got is resp
    names = rec.names()
    assert names.count("record_openai_response") == 1
    assert names.index("record_openai_response") > names.index("create")
    assert names.count("record_openai_response_soon") == (1 if spend else 0)
    for n in (
        "openai_record_failure",
        "openai_record_success",
        "openai_release_half_open_probe",
    ):
        assert rec.count(n) == 0, n
    st = _state()
    assert st and st["state"] == "ok" and st["source"] == "dispatch"


@pytest.mark.parametrize("probe", [False, True])
def test_h03_flag_on_401(monkeypatch, alert_rec, probe):
    _full_config(monkeypatch, preflight=True, spend=True)
    rec = _Rec()
    _openai_recorders(monkeypatch, rec)
    monkeypatch.setattr(
        _abs(), "_openai_dispatch_admission", lambda: (True, True, probe)
    )
    exc = auth401()
    kind, got = _run(_abs().guarded_llm_create(_fake_openai_client(rec, exc), **_kw()))
    assert kind == "raised" and got is exc
    assert rec.count("openai_record_failure") == 0
    assert rec.count("openai_release_half_open_probe") == 0
    assert rec.count("openai_record_success") == (1 if probe else 0)
    st = _state()
    assert st and st["state"] == "rejected" and st["source"] == "dispatch"


@pytest.mark.parametrize("outcome_matters", [False, True])
def test_h04_flag_on_success(monkeypatch, alert_rec, outcome_matters):
    _full_config(monkeypatch, preflight=True, spend=False)
    rec = _Rec()
    _openai_recorders(monkeypatch, rec)
    monkeypatch.setattr(
        _abs(), "_openai_dispatch_admission", lambda: (True, outcome_matters, False)
    )
    resp = types.SimpleNamespace(choices=[], usage=None)
    kind, got = _run(_abs().guarded_llm_create(_fake_openai_client(rec, resp), **_kw()))
    assert kind == "ok" and got is resp
    assert rec.count("openai_record_success") == (1 if outcome_matters else 0)
    st = _state()
    assert st and st["state"] == "ok"


@pytest.mark.parametrize("preflight", [False, True])
@pytest.mark.parametrize(
    "make",
    [
        lambda: oa_err("RateLimitError", 429),
        oa_timeout,
        lambda: oa_err("InternalServerError", 500),
    ],
    ids=["ratelimit", "timeout", "5xx"],
)
def test_h05_transient_leaves_state(monkeypatch, alert_rec, preflight, make):
    _full_config(monkeypatch, preflight=preflight, spend=False)
    rec = _Rec()
    _openai_recorders(monkeypatch, rec)
    monkeypatch.setattr(
        _abs(), "_openai_dispatch_admission", lambda: (True, False, False)
    )
    exc = make()
    kind, got = _run(_abs().guarded_llm_create(_fake_openai_client(rec, exc), **_kw()))
    assert kind == "raised" and got is exc
    assert _snapshot() == {}
    assert rec.count("openai_record_failure") == (1 if preflight else 0)


@pytest.mark.parametrize(
    "preflight,probe", [(False, False), (True, False), (True, True)]
)
def test_h06_cancelled_leaves_state(monkeypatch, alert_rec, preflight, probe):
    _full_config(monkeypatch, preflight=preflight, spend=False)
    rec = _Rec()
    _openai_recorders(monkeypatch, rec)
    monkeypatch.setattr(
        _abs(), "_openai_dispatch_admission", lambda: (True, False, probe)
    )
    kind, got = _run(
        _abs().guarded_llm_create(
            _fake_openai_client(rec, asyncio.CancelledError()), **_kw()
        )
    )
    assert kind == "raised" and isinstance(got, asyncio.CancelledError)
    assert _snapshot() == {}
    assert rec.count("openai_release_half_open_probe") == (1 if probe else 0)


def _anthropic_call(monkeypatch, rec, outcome, site="extract"):
    r = _router()
    _full_config(monkeypatch, preflight=False, spend=False)
    _openai_recorders(monkeypatch, rec)

    async def admission():
        return False, False

    async def create(**kw):
        rec.calls.append(("messages.create", (), {}))
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome

    client = types.SimpleNamespace(messages=types.SimpleNamespace(create=create))
    monkeypatch.setattr(r, "_anthropic_dispatch_admission", admission)
    monkeypatch.setattr(r, "_client_for", lambda key: client)
    from app.services import model_config

    return _run(
        r.guarded_anthropic_create(
            site=site,
            role="text",
            lane="live",
            model=model_config.anthropic_model("text"),
            system=None,
            messages=[{"role": "user", "content": "x"}],
            max_tokens=5,
            thinking={"type": "disabled"},
            output_config={},
        )
    )


def _claude_msg():
    usage = types.SimpleNamespace(
        input_tokens=3,
        output_tokens=2,
        cache_read_input_tokens=0,
        cache_creation_input_tokens=0,
        cache_creation=None,
        server_tool_use=None,
    )
    return types.SimpleNamespace(
        id="msg_mon1",
        type="message",
        role="assistant",
        model="m",
        content=[types.SimpleNamespace(type="text", text="{}")],
        stop_reason="end_turn",
        usage=usage,
    )


def test_h07_anthropic_401(monkeypatch, alert_rec):
    rec = _Rec()
    kind, got = _anthropic_call(
        monkeypatch, rec, an_err("AuthenticationError", 401, "authentication_error")
    )
    r = _router()
    assert kind == "raised" and isinstance(got, r.AnthropicDispatchError)
    assert (got.error_class, got.status, got.transient) == (
        "AuthenticationError",
        401,
        False,
    )
    assert rec.count("abs.record_failure") == 0
    st = _state("anthropic")
    assert (
        st
        and st["state"] == "rejected"
        and st["last_status"] == 401
        and st["source"] == "dispatch"
    )


def test_h08_moderation_site_403_then_success(monkeypatch, alert_rec):
    rec = _Rec()
    kind, _ = _anthropic_call(
        monkeypatch,
        rec,
        an_err("PermissionDeniedError", 403, "permission_error"),
        site="moderation",
    )
    assert kind == "raised"
    st = _state("anthropic")
    assert st and st["state"] == "rejected" and st["source"] == "moderation"
    kind, _ = _anthropic_call(monkeypatch, rec, _claude_msg(), site="moderation")
    assert kind == "ok"
    st = _state("anthropic")
    assert st["state"] == "ok" and st["source"] == "moderation"


def test_h09_anthropic_billing_quota(monkeypatch, alert_rec):
    rec = _Rec()
    kind, _ = _anthropic_call(
        monkeypatch, rec, an_err("APIStatusError", 402, "billing_error")
    )
    assert kind == "raised"
    st = _state("anthropic")
    assert st and st["state"] == "quota" and st["last_status"] == 402


def test_h10_content_safety_moderation(monkeypatch, alert_rec):
    from app.services import content_safety_service as css
    from app.services import openai_service

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
    kind, res = _run(svc.moderate_output("a plain sentence"))
    assert kind == "ok" and res.allowed is True
    st = _state()
    assert st and st["state"] == "rejected" and st["source"] == "moderation"
    kind, res = _run(svc.moderate_output("a plain sentence"))
    assert kind == "ok" and res.allowed is True
    assert _state()["state"] == "ok" and _state()["source"] == "moderation"


# ---------------------------------------------------------------------------
# G: gating unchanged (PIN)
# ---------------------------------------------------------------------------
def _fn_digest(path, name):
    tree = ast.parse(Path(path).read_text(encoding="utf-8"))
    for node in tree.body:
        if (
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == name
        ):
            raw = hashlib.sha256(
                ast.dump(node, include_attributes=False).encode("utf-8")
            ).digest()
            return base64.b64encode(raw).decode("ascii")
    return None


def test_g01_gating_code_untouched():
    for (mod, name), want in GATING_AST_B64.items():
        assert _fn_digest(ROOT / "app" / "services" / (mod + ".py"), name) == want, (
            mod,
            name,
        )


def test_g02_a_401_never_gates(monkeypatch, alert_rec):
    """PIN (FULL config, preflight ON, spend ON, the dict Redis): ten 401 dispatches are
    each admitted; the breaker never opens; no failure is counted."""
    from tests.test_openai_breaker import (
        _breaker_blob,
        _dict_breaker_redis,
        _patch_breaker_redis,
        _reset_breaker_memo,
    )
    from app.services import llm_spend_breaker as sb

    _full_config(monkeypatch, preflight=True, spend=True)
    rec = _Rec()
    monkeypatch.setattr(
        sb, "admit_openai_dispatch", rec.afn("admit_openai_dispatch", ret=object())
    )
    monkeypatch.setattr(
        sb, "record_openai_response_soon", rec.fn("record_openai_response_soon")
    )
    _reset_breaker_memo()
    store, ops, get, set_, incr, expire = _dict_breaker_redis()
    p = _patch_breaker_redis(get, set_, incr, expire)
    with p[0], p[1], p[2], p[3]:
        for _ in range(10):
            kind, got = _run(
                _abs().guarded_llm_create(_fake_openai_client(rec, auth401()), **_kw())
            )
            assert kind == "raised" and isinstance(got, _oa().AuthenticationError)
            blob = _breaker_blob(store)
            assert blob is None or (
                blob.get("state") != _abs().CB_OPEN
                and int(blob.get("failure_count", 0)) == 0
            )
    _reset_breaker_memo()
    assert rec.count("create") == 10


def _mark_both_and_select(monkeypatch):
    ss = _serper()
    store, ops = _serper_redis(monkeypatch)
    k1, k2 = _unique_key(), _unique_key()
    monkeypatch.setenv("SERPER_API_KEYS", k1 + "," + k2)
    ss._mark_serper_key_exhausted(k1)
    ss._mark_serper_key_exhausted(k2)
    return ss._active_serper_key(), (k1, k2), ops


def test_g03_health_status_unchanged_with_every_state_set(monkeypatch, alert_rec):
    _full_config(monkeypatch, preflight=False, spend=False)
    rec = _Rec()
    _openai_recorders(monkeypatch, rec)
    _run(_abs().guarded_llm_create(_fake_openai_client(rec, auth401()), **_kw()))
    got, _keys, _ops = _mark_both_and_select(monkeypatch)
    assert got is None
    r = _client().get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "healthy" and body["message"] == "MYEZ API is running"


# ---------------------------------------------------------------------------
# HE: /health entries
# ---------------------------------------------------------------------------
def test_he01_health_entry():
    leaf = _leaf()
    base = _client().get("/health").json()
    _need(leaf, "note_failure")("openai", auth401(), "dispatch")
    body = _client().get("/health").json()
    assert set(body) - set(base) == {"llm_credential"}
    assert body["llm_credential"] == _snapshot()["llm_credential"]


def test_he02_absent_after_reset():
    """PIN: with the reset seams applied (when present) /health carries neither key."""
    body = _client().get("/health").json()
    assert "llm_credential" not in body and "serper_keys" not in body
    assert body["status"] == "healthy"


def test_he03_raising_snapshot(monkeypatch):
    app_main = _main()
    _need(app_main, "llm_credential_health_snapshot")
    leaf = _leaf()
    leaf.note_failure("openai", auth401(), "dispatch")

    def boom():
        raise RuntimeError("x")

    monkeypatch.setattr(leaf, "health_snapshot", boom)
    r = _client().get("/health")
    assert r.status_code == 200 and "llm_credential" not in r.json()


def test_he04_health_purity(monkeypatch):
    import inspect

    from app.services import cache_service

    app_main = _main()
    src = inspect.getsource(app_main.health_check)
    assert (
        "llm_credential_health_snapshot()" in src
        and "serper_keys_health_snapshot()" in src
    )
    assert "await " not in src
    rec = _Rec()
    monkeypatch.setattr(cache_service, "_redis_get", rec.fn("redis_get"))
    monkeypatch.setattr(cache_service, "_redis_set", rec.fn("redis_set"))
    from app.services import openai_service

    monkeypatch.setattr(openai_service, "get_client", rec.fn("get_client"))
    _leaf().note_failure("openai", auth401(), "dispatch")
    assert _client().get("/health").status_code == 200
    assert rec.calls == []


def _unique_key():
    return uuid.uuid4().hex[:8] + "-mon1-" + "k" * 6


def _serper_redis(monkeypatch):
    from app.services import cache_service

    store = {}
    ops = {"get": 0, "set": 0}

    def _get(key):
        ops["get"] += 1
        return store.get(key)

    def _set(key, value, ex=None):
        ops["set"] += 1
        store[key] = value
        return True

    monkeypatch.setattr(cache_service, "_redis_get", _get)
    monkeypatch.setattr(cache_service, "_redis_set", _set)
    monkeypatch.delenv("ENABLE_SERPER_KEY_STATE_MEMO", raising=False)
    _serper()._reset_serper_key_state_memo()
    return store, ops


def test_he05_serper_counts_only(monkeypatch, alert_rec):
    ss = _serper()
    _need(ss, "serper_keys_snapshot")
    _serper_redis(monkeypatch)
    k1, k2 = _unique_key(), _unique_key()
    monkeypatch.setenv("SERPER_API_KEYS", k1 + "," + k2)
    ss._mark_serper_key_exhausted(k1)
    assert ss._active_serper_key() == k2
    r = _client().get("/health")
    body = r.json()
    sk = body.get("serper_keys")
    assert sk is not None and set(sk) == {
        "configured",
        "marked_exhausted",
        "none_left",
        "at",
    }
    assert (
        sk["configured"] == 2
        and sk["marked_exhausted"] == 1
        and sk["none_left"] is False
    )
    assert ISO_Z.match(sk["at"])
    text = r.text
    for k in (k1, k2):
        assert k not in text and k[:8] not in text


# ---------------------------------------------------------------------------
# S: the Serper key state
# ---------------------------------------------------------------------------
def test_s01_all_exhausted(monkeypatch, caplog, alert_rec):
    ss = _serper()
    with caplog.at_level(logging.INFO):
        got, _keys, _ops = _mark_both_and_select(monkeypatch)
        assert got is None
        assert ss._active_serper_key() is None
    snap = _need(ss, "serper_keys_snapshot")()
    assert snap["serper_keys"]["none_left"] is True
    assert _alerts(alert_rec) == [("serper_keys", "serper", "exhausted", None)]
    l2 = [
        r
        for r in caplog.records
        if r.getMessage().startswith("[SERPER_KEYS] no healthy key left")
    ]
    assert len(l2) == 1 and l2[0].levelno == logging.WARNING


def test_s02_exclude_is_not_exhaustion(monkeypatch, alert_rec):
    ss = _serper()
    _serper_redis(monkeypatch)
    k1, k2 = _unique_key(), _unique_key()
    monkeypatch.setenv("SERPER_API_KEYS", k1 + "," + k2)
    ss._mark_serper_key_exhausted(k2)
    assert ss._active_serper_key(exclude={k1}) is None
    snap = _need(ss, "serper_keys_snapshot")()
    assert snap["serper_keys"]["none_left"] is False
    assert _alerts(alert_rec) == []


def test_s03_single_key_inert(monkeypatch, alert_rec):
    ss = _serper()
    snapshot = _need(ss, "serper_keys_snapshot")
    store, ops = _serper_redis(monkeypatch)
    monkeypatch.setenv("SERPER_API_KEYS", _unique_key())
    assert ss._active_serper_key() is not None
    assert ops["get"] == 0
    assert snapshot() == {}


def test_s04_redis_command_count_unchanged(monkeypatch):
    """PIN (literals measured at base): two keys, first healthy -> 1 GET; first
    exhausted -> 2 GETs."""
    ss = _serper()
    _full_config(monkeypatch)
    store, ops = _serper_redis(monkeypatch)
    k1, k2 = _unique_key(), _unique_key()
    monkeypatch.setenv("SERPER_API_KEYS", k1 + "," + k2)
    assert ss._active_serper_key() == k1
    assert ops["get"] == 1
    ss._mark_serper_key_exhausted(k1)
    ops["get"] = 0
    assert ss._active_serper_key() == k2
    assert ops["get"] == 2


def test_s05_serper_key_exhausted_warning_unchanged(monkeypatch, caplog):
    """PIN: two marks of one key -> one WARNING, the base template."""
    ss = _serper()
    _full_config(monkeypatch)
    _serper_redis(monkeypatch)
    k = _unique_key()
    with caplog.at_level(logging.INFO):
        ss._mark_serper_key_exhausted(k)
        ss._mark_serper_key_exhausted(k)
    lines = [
        r
        for r in caplog.records
        if r.getMessage().startswith("SERPER_KEY_EXHAUSTED key=")
    ]
    assert len(lines) == 1 and lines[0].levelno == logging.WARNING
    assert lines[0].msg.endswith("marked exhausted (ttl=%ss); rotating to next key")


# ---------------------------------------------------------------------------
# M: the monitor path GET /health/llm
# ---------------------------------------------------------------------------
def test_m01_monitor_ok_unknown():
    r = _client().get("/health/llm")
    assert r.status_code == 200, r.status_code
    assert r.json() == {"status": "ok", "providers": {"openai": "unknown"}}


def test_m02_monitor_rejected(alert_rec):
    leaf = _leaf()
    leaf.note_failure("openai", auth401(), "dispatch")
    r = _client().get("/health/llm")
    assert r.status_code == 503
    body = r.json()
    assert (
        body.get("status") == "degraded"
        and body.get("code") == "LLM_CREDENTIAL_UNUSABLE"
    ), body
    assert body.get("providers") == {"openai": "rejected"}
    assert r.headers["content-type"].startswith("application/json")


def test_m03_monitor_quota(alert_rec):
    _leaf().note_failure("openai", quota_err(), "dispatch")
    r = _client().get("/health/llm")
    assert r.status_code == 503
    assert r.json().get("providers") == {"openai": "quota"}


def test_m04_not_in_use(monkeypatch, alert_rec):
    monkeypatch.setenv("ANTHROPIC_API_KEY", KEY_SENTINEL + "-an")
    leaf = _leaf()
    leaf.note_failure(
        "anthropic",
        an_err("AuthenticationError", 401, "authentication_error"),
        "dispatch",
    )
    assert _state("anthropic")["state"] == "rejected"
    r = _client().get("/health/llm")
    assert r.status_code == 200
    assert "anthropic" not in r.json().get("providers", {})


def test_m05_route_properties(monkeypatch):
    import inspect

    from slowapi.middleware import _should_exempt

    app = _main().app
    pairs = {
        (m, getattr(rt, "path", None))
        for rt in app.routes
        for m in (getattr(rt, "methods", None) or ())
    }
    assert ("GET", "/health/llm") in pairs
    assert "/health/llm" not in app.openapi().get("paths", {})
    reach = {
        rt.path
        for rt in app.routes
        if hasattr(rt, "endpoint")
        and not _should_exempt(app.state.limiter, rt.endpoint)
    }
    assert "/health/llm" not in reach
    assert {"/health", "/", "/favicon.ico"} <= reach
    handler = [
        rt.endpoint for rt in app.routes if getattr(rt, "path", None) == "/health/llm"
    ][0]
    assert "await " not in inspect.getsource(handler)


def test_m06_no_sentry_event_on_the_503(alert_rec):
    _leaf().note_failure("openai", auth401(), "dispatch")
    setup = len(alert_rec.calls)
    assert setup == 1
    for _ in range(5):
        assert _client().get("/health/llm").status_code == 503
    assert len(alert_rec.calls) == setup


@pytest.mark.parametrize(
    "probe_on,uptime,status,code",
    [
        ("true", 200.0, 503, "LLM_CREDENTIAL_UNKNOWN"),
        ("true", 60.0, 200, None),
        ("false", 200.0, 200, None),
    ],
)
def test_m07_unknown_with_the_probe_on(monkeypatch, probe_on, uptime, status, code):
    """R-MON1-22: probe ON + no outcome + up more than 120 s -> 503 LLM_CREDENTIAL_UNKNOWN;
    otherwise 200 with the provider unknown."""
    leaf = _leaf()
    _need(leaf, "_monotonic")
    _need(leaf, "_STARTED_AT")
    monkeypatch.setenv("ENABLE_LLM_CREDENTIAL_PROBE", probe_on)
    monkeypatch.setattr(leaf, "_STARTED_AT", 50000.0)
    monkeypatch.setattr(leaf, "_monotonic", lambda: 50000.0 + uptime)
    r = _client().get("/health/llm")
    assert r.status_code == status
    body = r.json()
    assert body.get("providers") == {"openai": "unknown"}
    if code:
        assert body.get("code") == code and body.get("status") == "degraded"
    else:
        assert body.get("status") == "ok"


# ---------------------------------------------------------------------------
# SE: the alert event (a child process with a live client and an in-memory transport)
# ---------------------------------------------------------------------------
_CHILD = r"""
import json, os, sys
sys.path.insert(0, os.getcwd())
mode = sys.argv[1]
out = {"events": [], "error": None}
try:
    import importlib, importlib.util
    import sentry_sdk
    import app.main as app_main
    from app.services import sentry_service
    client = sentry_sdk.get_client()
    out["active"] = bool(client.is_active())
    class _T(sentry_sdk.transport.Transport):
        def capture_envelope(self, envelope):
            for item in envelope.items:
                if item.type == "event":
                    ev = item.payload.json
                    out["events"].append({
                        "message": ev.get("message") or (ev.get("logentry") or {}).get("message"),
                        "level": ev.get("level"), "tags": ev.get("tags"),
                        "fingerprint": ev.get("fingerprint"), "has_request": "request" in ev,
                        "has_exception": "exception" in ev, "transaction": ev.get("transaction"),
                        "text": json.dumps(ev, default=str),
                    })
    client.transport = _T(client.options)
    fn = getattr(sentry_service, "capture_credential_alert", None)
    if fn is None:
        out["error"] = "capture_credential_alert missing"
    elif mode == "se01":
        fn("llm_credential", "openai", "rejected", 401)
    elif mode == "se05":
        fn("llm_credential", "openai", "test", None)
    else:
        if importlib.util.find_spec("app.services.llm_credential_health") is None:
            out["error"] = "leaf missing"
        else:
            leaf = importlib.import_module("app.services.llm_credential_health")
            import httpx2, openai
            req = httpx2.Request("POST", "https://example.invalid/v1/x")
            def _exc():
                return openai.AuthenticationError(os.environ["MON1_SDK_SENTINEL"], response=httpx2.Response(401, request=req), body={"code": "invalid_api_key"})
            if mode == "se03":
                import logging
                leaf.note_failure("openai", _exc(), "dispatch")
            elif mode == "se04":
                from fastapi.testclient import TestClient
                async def _probe_route():
                    sentry_sdk.set_tag("comparison_renderable", "yes")
                    leaf.note_failure("openai", _exc(), "dispatch")
                    return {"ok": True}
                app_main.app.add_api_route("/__mon1_se04", _probe_route, methods=["GET"])
                r = TestClient(app_main.app).get("/__mon1_se04?q=" + os.environ["MON1_SDK_SENTINEL"])
                out["route_status"] = r.status_code
    sentry_sdk.flush(2)
except Exception as exc:
    out["error"] = type(exc).__name__ + ": " + str(exc)[:200]
print("MON1JSON" + json.dumps(out))
"""


def _sentry_child(mode, dsn=True):
    env = {k: v for k, v in os.environ.items() if not k.startswith("ENABLE_")}
    env["PYTHONIOENCODING"] = "utf-8"
    env["MON1_SDK_SENTINEL"] = SDK_SENTINEL
    env.pop("SENTRY_DSN", None)
    if dsn:
        env["SENTRY_DSN"] = "https" + "://" + "public" + "@" + "example.invalid/1"
    proc = subprocess.run(
        [sys.executable, "-c", _CHILD, mode],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=180,
    )
    lines = [ln for ln in proc.stdout.splitlines() if ln.startswith("MON1JSON")]
    assert lines, (proc.returncode, proc.stderr[-2000:])
    return json.loads(lines[-1][len("MON1JSON") :])


def _cred_events(out):
    return [e for e in out["events"] if e["message"] == "credential_state"]


def test_se01_one_tagged_event():
    out = _sentry_child("se01")
    assert out["error"] is None, out["error"]
    assert out["active"] is True
    evs = _cred_events(out)
    assert len(evs) == 1 and len(out["events"]) == 1, out["events"]
    ev = evs[0]
    assert ev["level"] == "error"
    assert ev["tags"] == {
        "alert": "llm_credential",
        "provider": "openai",
        "state": "rejected",
        "status": "401",
    }
    assert ev["fingerprint"] == ["llm_credential", "openai", "rejected"]
    assert ev["has_exception"] is False and ev["has_request"] is False


def test_se02_no_dsn():
    fn = _need(_sentry(), "capture_credential_alert")
    assert fn("llm_credential", "openai", "rejected", 401) is None


def test_se03_one_event_not_two():
    out = _sentry_child("se03")
    assert out["error"] is None, out["error"]
    assert len(out["events"]) == 1 and len(_cred_events(out)) == 1, out["events"]
    assert SDK_SENTINEL not in out["events"][0]["text"]


def test_se04_no_request_region_inside_a_request():
    """R-MON1-20: inside a real request the alert event carries no request key, no
    transaction name and none of the request-scoped tags."""
    out = _sentry_child("se04")
    assert out["error"] is None, out["error"]
    assert out.get("route_status") == 200
    evs = _cred_events(out)
    assert len(evs) == 1, out["events"]
    ev = evs[0]
    assert ev["has_request"] is False
    assert not ev["transaction"], ev["transaction"]
    assert "comparison_renderable" not in (ev["tags"] or {})
    assert SDK_SENTINEL not in ev["text"]


def test_se05_manual_trigger_state_test():
    """R-MON1-26: the closed-set state `test` is accepted and tagged."""
    out = _sentry_child("se05")
    assert out["error"] is None, out["error"]
    evs = _cred_events(out)
    assert (
        len(evs) == 1
        and evs[0]["tags"].get("state") == "test"
        and evs[0]["tags"].get("alert") == "llm_credential"
    )


def test_t01_no_app_path_passes_the_test_state():
    """PIN (R-MON1-26): no application code path passes the state `test` to the sender."""
    pat = re.compile(
        r"(capture_credential_alert|emit_alert)\s*\([^)]*['\"]test['\"]", re.S
    )
    for path in (ROOT / "app").rglob("*.py"):
        assert not pat.search(path.read_text(encoding="utf-8")), path


# ---------------------------------------------------------------------------
# Y: env names and the env-safety tuple
# ---------------------------------------------------------------------------
Y01_ALLOWED = {
    "ENABLE_LLM_CREDENTIAL_PROBE",
    "LLM_CREDENTIAL_PROBE_INTERVAL_SECONDS",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
}


def _env_names(path):
    tree = ast.parse(Path(path).read_text(encoding="utf-8"))
    consts = {}
    for node in tree.body:
        if (
            isinstance(node, ast.Assign)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        ):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    consts[t.id] = node.value.value
    names = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not node.args:
            continue
        f = node.func
        txt = ast.unparse(f)
        if txt in ("os.getenv", "os.environ.get", "getenv", "environ.get"):
            a = node.args[0]
            if isinstance(a, ast.Constant):
                names.add(a.value)
            elif isinstance(a, ast.Name):
                names.add(consts.get(a.id, "<unresolved:" + a.id + ">"))
            else:
                names.add("<dynamic>")
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript) and ast.unparse(node.value) in (
            "os.environ",
            "environ",
        ):
            names.add("<subscript>")
    return names


def test_y01_env_names_and_env_safety():
    for mod in (LEAF, "app.services.llm_credential_probe"):
        try:
            spec = importlib.util.find_spec(mod)
        except (ImportError, ValueError):
            spec = None
        assert spec is not None and spec.origin, mod + " is absent"
        names = _env_names(spec.origin)
        assert names <= Y01_ALLOWED, (mod, names - Y01_ALLOWED)
    from tests import _env_safety

    raw = hashlib.sha256(
        repr(sorted(_env_safety.CREDENTIALS_UNSET)).encode("utf-8")
    ).digest()
    assert base64.b64encode(raw).decode("ascii") == ENV_SAFETY_UNSET_B64
