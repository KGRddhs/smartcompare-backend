"""MON1 LLM-CREDENTIAL-HEALTH: the frozen RED file of the DARK active check (rows P).

Spec .qa-s80/MON1_UNIT_SPEC.md section 2.9, amended by the review and the rulings
R-MON1-17 (a probe success proves authentication only), R-MON1-18 (a probe-sourced
rejection needs the structured invalid-credential signal) and R-MON1-19 (`tick()` reads
the flag as its FIRST statement). Every RED row fails at base on an AssertionError only.
Hermetic: the provider clients are fakes; no network, no .env, no real credential.
"""

import ast
import asyncio
import importlib
import importlib.util
import logging
import re
import types
from pathlib import Path

import pytest

from tests.test_inc_mon1_credential_health import (  # noqa: F401 -- fixtures re-used
    KEY_SENTINEL,
    SDK_SENTINEL,
    _alerts,
    _client,
    _full_config,
    _leaf,
    _main,
    _mon1_env,
    _need,
    _Rec,
    _snapshot,
    _state,
    alert_rec,
    an_err,
    auth401,
    oa_err,
    quota_err,
)

PROBE = "app.services.llm_credential_probe"
FLAG = "ENABLE_LLM_CREDENTIAL_PROBE"
KNOB = "LLM_CREDENTIAL_PROBE_INTERVAL_SECONDS"
L4_RE = re.compile(
    r"\[LLM_PROBE\] provider=(openai|anthropic) outcome=(ok|rejected|quota|inconclusive|unavailable)"
    r" class=([A-Za-z_][A-Za-z0-9_]*|none) ms=\d+"
)


def _probe():
    try:
        spec = importlib.util.find_spec(PROBE)
    except (ImportError, ValueError):
        spec = None
    assert spec is not None, "app/services/llm_credential_probe.py is absent (MON1 3.8)"
    return importlib.import_module(PROBE)


async def _cap(coro):
    try:
        return "ok", await coro
    except BaseException as exc:  # noqa: BLE001
        if isinstance(exc, (KeyboardInterrupt, SystemExit)):
            raise
        return "raised", exc


def _tick():
    return asyncio.run(_cap(_need(_probe(), "tick")()))


class _FakeProviderClient:
    """A fake AsyncOpenAI / AsyncAnthropic: with_options(...) records the options and
    returns an object whose models.retrieve records the model and returns / raises."""

    def __init__(self, rec, name, outcome):
        self.rec, self.name, self.outcome = rec, name, outcome

    def with_options(self, **opts):
        self.rec.calls.append((self.name + ".with_options", (), dict(opts)))
        outer = self

        async def retrieve(model, **kw):
            outer.rec.calls.append((outer.name + ".retrieve", (model,), dict(kw)))
            item = outer.outcome
            if callable(item) and not isinstance(item, BaseException):
                return await item()
            if isinstance(item, BaseException):
                raise item
            return item

        return types.SimpleNamespace(models=types.SimpleNamespace(retrieve=retrieve))


def _install_clients(monkeypatch, rec, openai_outcome=None, anthropic_outcome=None):
    from app.services import llm_router, openai_service

    ok = types.SimpleNamespace(id="model-meta", object="model")
    oa = _FakeProviderClient(
        rec, "openai", ok if openai_outcome is None else openai_outcome
    )
    an = _FakeProviderClient(
        rec, "anthropic", ok if anthropic_outcome is None else anthropic_outcome
    )

    def get_client():
        rec.calls.append(("get_client", (), {}))
        return oa

    def client_for(key):
        rec.calls.append(("_client_for", (), {}))
        return an

    monkeypatch.setattr(openai_service, "get_client", get_client)
    monkeypatch.setattr(llm_router, "_client_for", client_for)


def _probe_on(monkeypatch, anthropic=False):
    monkeypatch.setenv(FLAG, "true")
    if anthropic:
        monkeypatch.setenv("ENABLE_ANTHROPIC_TEXT", "true")
        monkeypatch.setenv("ANTHROPIC_API_KEY", KEY_SENTINEL + "-an")


def _retrieves(rec, name):
    return [c for c in rec.calls if c[0] == name + ".retrieve"]


# ---------------------------------------------------------------------------
def test_p01_flag_off_full_config_tick_makes_no_call(monkeypatch, alert_rec):
    """PIN-class (RED at base: the module is absent): flag OFF with the FULL config
    (both keys, every role flag ON, the interval set) -> tick() builds no client."""
    _full_config(monkeypatch)
    for f in (
        "ENABLE_ANTHROPIC_VISION",
        "ENABLE_ANTHROPIC_VERDICT",
        "ENABLE_ANTHROPIC_CRITIC",
    ):
        monkeypatch.setenv(f, "true")
    monkeypatch.setenv(FLAG, "false")
    rec = _Rec()
    _install_clients(monkeypatch, rec)
    kind, _ = _tick()
    assert kind == "ok"
    assert rec.calls == []
    assert _snapshot() == {}


@pytest.mark.parametrize(
    "value,on",
    [
        ("true", True),
        ("1", True),
        ("yes", True),
        ("on", True),
        (" TRUE ", True),
        (None, False),
        ("", False),
        ("false", False),
        ("0", False),
        ("off", False),
        ("maybe", False),
    ],
)
def test_p02_flag_reader(monkeypatch, value, on):
    reader = _need(_probe(), "probe_enabled")
    if value is None:
        monkeypatch.delenv(FLAG, raising=False)
    else:
        monkeypatch.setenv(FLAG, value)
    assert reader() is on


@pytest.mark.parametrize(
    "value,want",
    [
        (None, 900.0),
        ("600", 600.0),
        ("60", 300.0),
        ("0", 900.0),
        ("-5", 900.0),
        ("inf", 900.0),
        ("nan", 900.0),
        ("abc", 900.0),
        ("300", 300.0),
        (" 1200 ", 1200.0),
    ],
)
def test_p03_interval_knob(monkeypatch, value, want):
    reader = _need(_probe(), "probe_interval")
    if value is None:
        monkeypatch.delenv(KNOB, raising=False)
    else:
        monkeypatch.setenv(KNOB, value)
    assert reader() == want


def test_p04_on_openai_only(monkeypatch, alert_rec):
    from app.services import model_config

    _probe_on(monkeypatch)
    rec = _Rec()
    _install_clients(monkeypatch, rec)
    kind, out = _tick()
    assert kind == "ok"
    calls = _retrieves(rec, "openai")
    assert len(calls) == 1 and calls[0][1] == (model_config.standard_model(),)
    opts = [c[2] for c in rec.calls if c[0] == "openai.with_options"]
    assert (
        len(opts) == 1
        and opts[0].get("max_retries") == 0
        and opts[0].get("timeout") == 5.0
    )
    assert _retrieves(rec, "anthropic") == []
    st = _state()
    assert st and st["state"] == "ok" and st["source"] == "probe"
    assert out == {"openai": "ok"}


def test_p05_on_invalid_api_key_401(monkeypatch, alert_rec):
    """R-MON1-18: openai 401 + structured code invalid_api_key -> rejected (probe)."""
    _probe_on(monkeypatch)
    rec = _Rec()
    _install_clients(monkeypatch, rec, openai_outcome=auth401("invalid_api_key"))
    kind, out = _tick()
    assert kind == "ok"
    st = _state()
    assert (
        st
        and st["state"] == "rejected"
        and st["source"] == "probe"
        and st["last_status"] == 401
    )
    assert out == {"openai": "rejected"}


def test_p06_hang_is_bounded(monkeypatch, alert_rec):
    probe = _probe()
    _need(probe, "CALL_TIMEOUT_SECONDS")
    monkeypatch.setattr(probe, "CALL_TIMEOUT_SECONDS", 0.05)
    _probe_on(monkeypatch)
    rec = _Rec()

    async def hang():
        await asyncio.sleep(30)

    _install_clients(monkeypatch, rec, openai_outcome=hang)
    kind, out = _tick()
    assert kind == "ok"
    assert len(_retrieves(rec, "openai")) == 1
    assert _snapshot() == {}
    assert out == {"openai": "inconclusive"}


def test_p07_anthropic_in_use_and_not(monkeypatch, alert_rec):
    from app.services import model_config

    _probe_on(monkeypatch, anthropic=True)
    rec = _Rec()
    _install_clients(monkeypatch, rec)
    kind, _ = _tick()
    assert kind == "ok"
    calls = _retrieves(rec, "anthropic")
    assert len(calls) == 1 and calls[0][1] == (model_config.anthropic_model("text"),)
    opts = [c[2] for c in rec.calls if c[0] == "anthropic.with_options"]
    assert (
        len(opts) == 1
        and opts[0].get("max_retries") == 0
        and opts[0].get("timeout") == 5.0
    )
    assert _state("anthropic")["source"] == "probe"
    monkeypatch.delenv("ENABLE_ANTHROPIC_TEXT")
    rec2 = _Rec()
    _install_clients(monkeypatch, rec2)
    _tick()
    assert _retrieves(rec2, "anthropic") == [] and len(_retrieves(rec2, "openai")) == 1


def test_p08_no_spend_or_ledger(monkeypatch, alert_rec):
    from app.services import api_budget_service as a
    from app.services import llm_pricing, llm_router
    from app.services import llm_spend_breaker as sb

    _probe_on(monkeypatch, anthropic=True)
    rec = _Rec()
    _install_clients(monkeypatch, rec)
    spy = _Rec()
    for mod, name in ((sb, "admit_openai_dispatch"), (sb, "admit_async")):
        monkeypatch.setattr(mod, name, spy.afn(name))
    for mod, name in (
        (sb, "record_soon"),
        (sb, "record_openai_response_soon"),
        (llm_pricing, "record_llm_call"),
        (a, "record_openai_response"),
        (a, "_openai_dispatch_admission"),
    ):
        monkeypatch.setattr(mod, name, spy.fn(name))
    monkeypatch.setattr(
        llm_router, "_anthropic_dispatch_admission", spy.afn("anthropic_admission")
    )
    kind, _ = _tick()
    assert kind == "ok"
    assert (
        len(_retrieves(rec, "openai")) == 1 and len(_retrieves(rec, "anthropic")) == 1
    )
    assert spy.calls == []


def test_p09_run_forever_timing_and_cancel(monkeypatch):
    probe = _probe()
    _need(probe, "run_forever")
    first = _need(probe, "FIRST_DELAY_SECONDS")
    assert 0 < first <= 30
    monkeypatch.setenv(KNOB, "600")
    real_sleep = asyncio.sleep
    delays = []
    ticks = []

    async def fake_sleep(d, *a, **k):
        delays.append(d)
        if len(delays) >= 3:
            await asyncio.Event().wait()
        await real_sleep(0)

    async def fake_tick():
        ticks.append(1)
        return {}

    monkeypatch.setattr(probe.asyncio, "sleep", fake_sleep)
    monkeypatch.setattr(probe, "tick", fake_tick)

    async def main():
        task = asyncio.ensure_future(probe.run_forever())
        for _ in range(200):
            if len(delays) >= 3:
                break
            await real_sleep(0)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        return task

    task = asyncio.run(main())
    assert task.cancelled()
    assert delays[0] == first and delays[1] == 600.0
    assert len(ticks) >= 1


def _shutdown_names(app_main):
    handlers = getattr(app_main.app.router, "on_shutdown", None)
    if handlers:
        return [getattr(f, "__name__", repr(f)) for f in handlers]
    source = Path(app_main.__file__).read_text(encoding="utf-8")
    names = []
    lines = source.splitlines()
    for index, line in enumerate(lines):
        if 'on_event("shutdown")' not in line and "on_event('shutdown')" not in line:
            continue
        for following in lines[index + 1 : index + 5]:
            stripped = following.strip()
            if stripped.startswith("async def ") or stripped.startswith("def "):
                names.append(stripped.split("def ", 1)[1].split("(", 1)[0].strip())
                break
    return names


def test_p10_lifespan(monkeypatch):
    from fastapi.testclient import TestClient

    app_main = _main()
    _need(app_main, "_llm_probe_task")
    names = _shutdown_names(app_main)
    assert "_stop_llm_credential_probe" in names, names
    assert (
        names.index("_stop_loop_lag_heartbeat")
        < names.index("_stop_llm_credential_probe")
        < names.index("_drain_background_tasks")
    )
    with TestClient(app_main.app):
        task = app_main._llm_probe_task
        assert isinstance(task, asyncio.Task)
    assert app_main._llm_probe_task is None


def test_p11_l4_line(monkeypatch, caplog, alert_rec):
    _probe_on(monkeypatch, anthropic=True)
    rec = _Rec()
    _install_clients(
        monkeypatch,
        rec,
        anthropic_outcome=an_err("InternalServerError", 500, "api_error"),
    )
    with caplog.at_level(logging.INFO):
        kind, _ = _tick()
    assert kind == "ok"
    l4 = [r for r in caplog.records if L4_RE.fullmatch(r.getMessage())]
    assert sorted(L4_RE.fullmatch(r.getMessage()).group(1) for r in l4) == [
        "anthropic",
        "openai",
    ]
    assert all(r.levelno == logging.INFO for r in l4)
    for r in caplog.records:
        text = r.getMessage() + repr(r.args)
        assert SDK_SENTINEL not in text and KEY_SENTINEL not in text


def test_p12_probe_module_hygiene():
    probe = _probe()
    tree = ast.parse(Path(probe.__file__).read_text(encoding="utf-8"))
    for node in tree.body:
        if (
            isinstance(node, ast.ImportFrom)
            and node.module
            and node.module.startswith("app.")
        ):
            names = {a.name for a in node.names}
            assert node.module == "app.services" and names == {
                "llm_credential_health"
            }, (node.module, names)
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not alias.name.startswith("app."), alias.name
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            assert "://" not in node.value
            for frag in ("gpt-", "claude-", "omni-moderation"):
                assert frag not in node.value
        if isinstance(node, ast.Call):
            fn = node.func
            name = (
                fn.id
                if isinstance(fn, ast.Name)
                else (fn.attr if isinstance(fn, ast.Attribute) else "")
            )
            assert name not in (
                "AsyncOpenAI",
                "AsyncAnthropic",
                "OpenAI",
                "Anthropic",
                "create",
            )
            assert name not in ("error", "exception", "critical")
        if isinstance(node, ast.Attribute):
            assert node.attr != "messages"


@pytest.mark.parametrize("held", ["quota", "dispatch403", "probe_quota"])
def test_p13_probe_success_never_clears_quota_or_dispatch_403(
    monkeypatch, alert_rec, held
):
    """R-MON1-17: a dispatch quota (or a dispatch 403) survives a probe 2xx; no recovery
    event; /health/llm stays 503."""
    leaf = _leaf()
    exc = quota_err() if held != "dispatch403" else oa_err("PermissionDeniedError", 403)
    leaf.note_failure("openai", exc, "probe" if held == "probe_quota" else "dispatch")
    want = "rejected" if held == "dispatch403" else "quota"
    before = len(alert_rec.calls)
    _probe_on(monkeypatch)
    rec = _Rec()
    _install_clients(monkeypatch, rec)
    kind, _ = _tick()
    assert kind == "ok" and len(_retrieves(rec, "openai")) == 1
    assert _state()["state"] == want
    assert [c for c in _alerts(alert_rec)[before:] if c[2] == "ok"] == []
    assert _client().get("/health/llm").status_code == 503


def test_p14_probe_success_clears_a_dispatch_401(monkeypatch, alert_rec):
    """R-MON1-17: a dispatch 401 then a probe 2xx -> ok + one recovery event."""
    leaf = _leaf()
    leaf.note_failure("openai", auth401(), "dispatch")
    _probe_on(monkeypatch)
    rec = _Rec()
    _install_clients(monkeypatch, rec)
    kind, _ = _tick()
    assert kind == "ok"
    st = _state()
    assert st["state"] == "ok" and st["source"] == "probe"
    assert [c[2] for c in _alerts(alert_rec)] == ["rejected", "ok"]


@pytest.mark.parametrize(
    "provider,make",
    [
        ("openai", lambda: oa_err("AuthenticationError", 401)),
        ("openai", lambda: auth401("invalid_organization")),
        ("openai", lambda: oa_err("PermissionDeniedError", 403)),
        ("anthropic", lambda: an_err("PermissionDeniedError", 403, "permission_error")),
        ("anthropic", lambda: an_err("AuthenticationError", 401)),
    ],
    ids=["oa401-nocode", "oa401-othercode", "oa403", "an403", "an401-notype"],
)
def test_p15_probe_unstructured_401_403_is_inconclusive(
    monkeypatch, alert_rec, provider, make
):
    """R-MON1-18: a probe 401 / 403 without the structured invalid-credential signal is
    inconclusive: no state change, no event."""
    anthropic = provider == "anthropic"
    _probe_on(monkeypatch, anthropic=anthropic)
    rec = _Rec()
    if anthropic:
        _install_clients(monkeypatch, rec, anthropic_outcome=make())
    else:
        _install_clients(monkeypatch, rec, openai_outcome=make())
    kind, out = _tick()
    assert kind == "ok"
    assert out.get(provider) == "inconclusive", out
    assert (_snapshot().get("llm_credential") or {}).get(provider) is None
    assert [c for c in _alerts(alert_rec) if c[1] == provider] == []


def test_p16_anthropic_structured_401_rejects(monkeypatch, alert_rec):
    """R-MON1-18: anthropic 401 + type authentication_error -> rejected (probe)."""
    _probe_on(monkeypatch, anthropic=True)
    rec = _Rec()
    _install_clients(
        monkeypatch,
        rec,
        anthropic_outcome=an_err("AuthenticationError", 401, "authentication_error"),
    )
    kind, out = _tick()
    assert kind == "ok" and out.get("anthropic") == "rejected"
    st = _state("anthropic")
    assert st["state"] == "rejected" and st["source"] == "probe"
