"""S81-12d OPENAI-EGRESS-STOP: the frozen RED file A (spec S81-12d section 5 as
amended by RULINGS_S81_12D C to K: D-2, D-6, G-3, I-1..I-6, J-5 / J-11 (S12D-21,
S12D-22, the no-subclass census) and K-2 / K-3 (MON1's contract inside this
unit: rows MC-1..MC-4)). Amended on the replay onto main c6ebbd2e: the census
row (RULINGS_REPLAY_S81_12D RP-2) and the autouse fixture's spend-breaker
reset (RP-7).

ENABLE_OPENAI_EGRESS_STOP (default OFF, read per call): ON, every call that would
go to OpenAI fails LOCALLY with api_budget_service.OpenAIEgressStoppedError (an
LLMUnavailableError) before any network activity: in guarded_llm_create after the
store=False prologue and before the spend admit (H1), in
content_safety_service.moderate_output after the Claude branch (H2), and in the
two operator scripts (H3 / H4). OFF: byte-identical (one getenv per dispatch).

RED = fails at base 445f8de3 on an AssertionError only (every new symbol is read
with getattr and asserted). PIN = green at base, FULL configuration (ruling B1 as
amended by D-2) plus the transport and call recorders. Hermetic: the pinned SDK
(openai 3.3.1 over httpx2) talks only to a class-level recorder on
httpx2.AsyncClient.send that answers an OpenAI request with a synthetic 401; every
other host is refused; no .env, no real credential (every synthetic value is
built at run time). Every ENABLE_* / ANTHROPIC_* / LLM_SPEND_* / OPENAI_* knob a
row depends on is deleted first and set explicitly per row. Pure ASCII.
"""

import app.main  # noqa: F401  (first: the dotenv guard, tests/_env_safety)

import ast
import asyncio
import json
import logging
import os
import pathlib
import types

import pytest

from app.services import api_budget_service as abs_
from app.services import content_safety_service as css
from app.services import extraction_service as es
from app.services import image_service as imgsvc
from app.services import llm_router
from app.services import llm_spend_breaker as sb
from app.services import model_config
from app.services import openai_service as osvc
from app.services import url_extraction_service as urlsvc
from app.services.llm_provider import STOCK_OPENAI_BASE_URL, provider_base_url

ROOT = pathlib.Path(__file__).resolve().parents[1]

FLAG = "ENABLE_OPENAI_EGRESS_STOP"
ON_VALUES = ("true", "1", "yes", "on", " TRUE ", "On\n")
OFF_VALUES = (None, "", "false", "0", "no", "off", "truthy", "2")
SURFACES = ("chat_completions", "moderations", "script")
BANNED_WORDS = ("429", "rate", "quota", "rate limit", "ratelimit")
OPENAI_HOST = "api.openai.com"
STOP_TAG = "[OPENAI_EGRESS]"

SYN_OPENAI = "test" + "-" + "z" * 24
SYN_ANTH = "syn" + "thetic" + "-anthropic-" + "s12d"
# The synthetic 401 the recorder answers with: no word the verdict fallback
# matcher keys on (extraction_service.py:2718-2722) and none of the shadow
# matcher's words (shadow_experiments.py:1001-1004).
SYN_401_MESSAGE = "s12d synthetic key refused"

ROLE_FLAGS = (
    "ENABLE_ANTHROPIC_TEXT",
    "ENABLE_ANTHROPIC_VISION",
    "ENABLE_ANTHROPIC_VERDICT",
    "ENABLE_ANTHROPIC_CRITIC",
    "ENABLE_ANTHROPIC_MODERATION",
)
# The FULL configuration (spec section 5 + ruling D-2): every knob at a
# non-default value; the role flags OFF (production) unless a row says otherwise.
FULL = {
    "ENABLE_LLM_SPEND_BREAKER": "true",
    "ENABLE_LLM_LEDGER_V2": "true",
    "ENABLE_PAID_ROUTE_METERING": "true",
    "ENABLE_COMPARE_AUTH_REQUIRED": "true",
    "ENABLE_CAMERA_FAILURE_ENVELOPE": "true",
    "OPENAI_MAX_RETRIES": "1",
    "OPENAI_FALLBACK_MAX_RETRIES": "0",
    "LLM_BREAKER_CACHE_TTL": "7.5",
    "LLM_SPEND_CAP_LIVE_USD": "41.5",
    "LLM_SPEND_CAP_ESCALATION_USD": "3.5",
    "LLM_SPEND_CAP_SEARCH_USD": "2.5",
    "LLM_SPEND_CAP_OFFCLOCK_USD": "9.5",
    "LLM_SPEND_MEMO_SECONDS": "4.5",
    "LLM_SPEND_REDIS_TIMEOUT_SECONDS": "0.75",
    "LLM_SPEND_ENTRY_RESERVE_USD": "0.25",
    "LLM_SPEND_CHOKEPOINT_LANE": "live",
    "ANTHROPIC_API_KEY": SYN_ANTH,
}
WATCHED = (
    "app.services.api_budget_service",
    "app.services.content_safety_service",
    "app.services.extraction_service",
    "app.services.url_extraction_service",
    "app.services.openai_service",
    "app.services.image_service",
    "app.services.llm_spend_breaker",
    "app.services.llm_router",
    "app.api.image_routes",
    "app.services.llm_credential_health",
    "app.services.llm_credential_probe",
    "seed_spec_spine",
    "scripts.shadow_experiments",
)
ZERO = {"prompt_tokens": 0, "completion_tokens": 0}

_MISSING = type("_Missing", (Exception,), {})


def new_symbol(name):
    """A new S81-12d symbol, or None at base (asserted by the caller)."""
    return getattr(abs_, name, None)


def stop_class():
    """OpenAIEgressStoppedError, or a private class nothing raises (base)."""
    cls = new_symbol("OpenAIEgressStoppedError")
    return cls if isinstance(cls, type) else _MISSING


def stop_message():
    return new_symbol("OPENAI_EGRESS_STOP_MESSAGE")


# ---------------------------------------------------------------------------
# the transport recorder (spec 2.8)
# ---------------------------------------------------------------------------
class Wire:
    def __init__(self):
        self.requests = []  # (host, path, body)
        self.other = []

    def paths(self):
        return [r[1] for r in self.requests]

    def count(self, path=None):
        return len([r for r in self.requests if path is None or r[1] == path])


def _body(request):
    try:
        raw = request.content
    except Exception:  # noqa: BLE001
        return None
    try:
        return json.loads(raw.decode("utf-8")) if raw else None
    except Exception:  # noqa: BLE001
        return None


def _err_json():
    return {
        "error": {
            "message": SYN_401_MESSAGE,
            "type": "invalid_request_error",
            "code": "invalid_api_key",
        }
    }


LOCAL_HOSTS = ("testserver",)  # the in-process ASGI TestClient only


def install_wire(mp):
    """Every OpenAI request is recorded and answered 401; the TestClient's
    in-process 'testserver' passes through; every other host is refused."""
    import httpx
    import httpx2

    wire = Wire()
    real2 = httpx2.AsyncClient.send
    real2_sync = httpx2.Client.send
    real1 = httpx.AsyncClient.send
    real1_sync = httpx.Client.send

    def _record(mod, request):
        host = request.url.host
        if host == OPENAI_HOST:
            wire.requests.append((host, request.url.path, _body(request)))
            return mod.Response(401, json=_err_json(), request=request)
        wire.other.append((host, request.url.path))
        raise mod.ConnectError("s12d hermetic: host refused", request=request)

    async def _send2(self, request, *a, **k):
        if request.url.host in LOCAL_HOSTS:
            return await real2(self, request, *a, **k)
        return _record(httpx2, request)

    def _send2_sync(self, request, *a, **k):
        if request.url.host in LOCAL_HOSTS:
            return real2_sync(self, request, *a, **k)
        return _record(httpx2, request)

    async def _send1(self, request, *a, **k):
        if request.url.host in LOCAL_HOSTS:
            return await real1(self, request, *a, **k)
        return _record(httpx, request)

    def _send1_sync(self, request, *a, **k):
        if request.url.host in LOCAL_HOSTS:
            return real1_sync(self, request, *a, **k)
        return _record(httpx, request)

    mp.setattr(httpx2.AsyncClient, "send", _send2)
    mp.setattr(httpx2.Client, "send", _send2_sync)
    mp.setattr(httpx.AsyncClient, "send", _send1)
    mp.setattr(httpx.Client, "send", _send1_sync)
    return wire


def real_client(**kw):
    """A real AsyncOpenAI under the synthetic key, as the sites build theirs."""
    from openai import AsyncOpenAI

    return AsyncOpenAI(
        api_key=SYN_OPENAI,
        base_url=provider_base_url(),
        max_retries=model_config.openai_max_retries(),
        **kw,
    )


def reset_clients(mp):
    """The production client memo slots, reset; the module singleton rebuilt."""
    mp.setattr(es, "_client", None)
    mp.setattr(urlsvc, "_client", None)
    mp.setattr(osvc, "_client_cache", {})
    mp.setattr(osvc, "client", real_client())


# ---------------------------------------------------------------------------
# recorders
# ---------------------------------------------------------------------------
class Calls:
    def __init__(self):
        self.names = []

    def n(self, name):
        return self.names.count(name)


def install_call_recorders(mp):
    """spend read (forwarding), spend admit (recorder, returns no ticket), the
    W1-3 admission (recorder, admits), the three W1-3 records, both response
    records, the moderation client / model readers (forwarding)."""
    calls = Calls()
    real_sbe = sb.spend_breaker_enabled

    def _sbe():
        calls.names.append("spend_breaker_enabled")
        return real_sbe()

    async def _admit(*_a, **_k):
        calls.names.append("admit_openai_dispatch")
        return None

    def _soon(*_a, **_k):
        calls.names.append("record_openai_response_soon")

    real_pre = abs_.llm_preflight_breaker_enabled

    def _pre():
        calls.names.append("llm_preflight_breaker_enabled")
        return real_pre()

    def _adm():
        calls.names.append("_openai_dispatch_admission")
        return True, False, False

    def _mk(name):
        def _f(*_a, **_k):
            calls.names.append(name)

        return _f

    real_rec = abs_.record_openai_response

    def _rec(*a, **k):
        calls.names.append("record_openai_response")
        return real_rec(*a, **k)

    real_gc = osvc.get_client

    def _gc(*a, **k):
        calls.names.append("openai_service.get_client")
        return real_gc(*a, **k)

    real_mm = model_config.moderation_model

    def _mm(*a, **k):
        calls.names.append("moderation_model")
        return real_mm(*a, **k)

    mp.setattr(sb, "spend_breaker_enabled", _sbe)
    mp.setattr(sb, "admit_openai_dispatch", _admit)
    mp.setattr(sb, "record_openai_response_soon", _soon)
    mp.setattr(abs_, "llm_preflight_breaker_enabled", _pre)
    mp.setattr(abs_, "_openai_dispatch_admission", _adm)
    for name in (
        "openai_record_failure",
        "openai_record_success",
        "openai_release_half_open_probe",
    ):
        mp.setattr(abs_, name, _mk(name))
    mp.setattr(abs_, "record_openai_response", _rec)
    mp.setattr(osvc, "get_client", _gc)
    mp.setattr(model_config, "moderation_model", _mm)
    return calls


R5_NAMES = (
    "spend_breaker_enabled",
    "admit_openai_dispatch",
    "llm_preflight_breaker_enabled",
    "_openai_dispatch_admission",
    "openai_record_failure",
    "openai_record_success",
    "openai_release_half_open_probe",
    "record_openai_response",
    "record_openai_response_soon",
)


_REAL_STOP = getattr(abs_, "stop_openai_egress_if_enabled", None)


class StopCounter:
    def __init__(self):
        self.surfaces = []


def install_stop_counter(mp):
    """A forwarding wrapper on stop_openai_egress_if_enabled that counts the
    calls that STOPPED (raised); a flag-OFF call returns None and is not
    counted (absent at base: nothing calls it there, the counter stays empty)."""
    counter = StopCounter()
    real = _REAL_STOP

    def _wrap(surface, *a, **k):
        if real is None:
            return None
        try:
            return real(surface, *a, **k)
        except BaseException:
            counter.surfaces.append(surface)
            raise

    mp.setattr(abs_, "stop_openai_egress_if_enabled", _wrap, raising=False)
    return counter


class _Rec(logging.Handler):
    def __init__(self):
        super().__init__(level=logging.DEBUG)
        self.records = []

    def emit(self, record):
        self.records.append(record)


@pytest.fixture
def logs():
    handler = _Rec()
    root_handler = _Rec()
    root_handler.setLevel(logging.ERROR)
    prev = {}
    for name in WATCHED:
        lg = logging.getLogger(name)
        prev[name] = (lg.level, lg.disabled)
        lg.disabled = False
        lg.setLevel(logging.DEBUG)
        lg.addHandler(handler)
    logging.getLogger().addHandler(root_handler)
    ns = types.SimpleNamespace(handler=handler, root=root_handler)
    yield ns
    for name in WATCHED:
        lg = logging.getLogger(name)
        lg.removeHandler(handler)
        lg.setLevel(prev[name][0])
        lg.disabled = prev[name][1]
    logging.getLogger().removeHandler(root_handler)


def stop_records(ns):
    return [r for r in ns.handler.records if STOP_TAG in str(r.msg)]


def error_records(ns):
    seen = list(ns.handler.records) + list(ns.root.records)
    return [r for r in seen if r.levelno >= logging.ERROR]


@pytest.fixture(autouse=True)
def _s12d_env(monkeypatch):
    for k in list(os.environ):
        if (
            k.startswith("ENABLE_")
            or k.startswith("ANTHROPIC_")
            or k.startswith("LLM_SPEND_")
            or k.startswith("OPENAI_")
            or k.startswith("LLM_BREAKER_")
        ):
            monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", SYN_OPENAI)
    reset = new_symbol("_reset_openai_egress_stop_state")
    if reset is not None:
        reset()
    if hasattr(llm_router, "_reset_router_state"):
        llm_router._reset_router_state()
    monkeypatch.setattr(abs_, "_openai_breaker_cache", None)
    # RP-7 (RULINGS_REPLAY_S81_12D): the FULL configuration runs the spend breaker;
    # its process state (the latch behind /health's llm_spend keys) is dropped
    # before and after every row, as tests/test_s81_s04_spend_breaker.py does, so
    # no later file of one CI process sees it.
    reset_spend = getattr(sb, "_reset_spend_breaker_state", None)
    if callable(reset_spend):
        reset_spend()
    yield
    if reset is not None:
        reset()
    if hasattr(llm_router, "_reset_router_state"):
        llm_router._reset_router_state()
    if callable(reset_spend):
        reset_spend()


def full_config(mp, stop=None, preflight=False, base_url=False):
    for k, v in FULL.items():
        mp.setenv(k, v)
    for name in ROLE_FLAGS:
        mp.delenv(name, raising=False)
    if preflight:
        mp.setenv("ENABLE_LLM_PREFLIGHT_BREAKER", "true")
    else:
        mp.delenv("ENABLE_LLM_PREFLIGHT_BREAKER", raising=False)
    if base_url:
        mp.setenv("OPENAI_BASE_URL", STOCK_OPENAI_BASE_URL)
    else:
        mp.delenv("OPENAI_BASE_URL", raising=False)
    if stop is None:
        mp.delenv(FLAG, raising=False)
    else:
        mp.setenv(FLAG, stop)


def set_consent(mp, value):
    from app.utils import request_context as rc

    mp.setattr(rc, "consent_version", lambda: value)


def _run(coro):
    return asyncio.run(coro)


async def _capture(coro):
    """('ok', value) or ('raised', exc): a RED never escapes as an error."""
    try:
        return "ok", await coro
    except Exception as e:  # noqa: BLE001
        return "raised", e


def chat_kwargs():
    return {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": "synthetic s12d text"}],
        "max_tokens": 5,
    }


def guarded(client=None, **extra):
    kw = chat_kwargs()
    kw.update(extra)
    return _run(_capture(abs_.guarded_llm_create(client or real_client(), **kw)))


def moderate(text="synthetic shopping text"):
    return _run(_capture(css.ContentSafetyService().moderate_output(text)))


# ---------------------------------------------------------------------------
# S12D-01 .. S12D-02: the reader, the class and the message
# ---------------------------------------------------------------------------
def test_s12d_01_reader_per_call_house_idiom(monkeypatch):
    """RED: the reader exists; ON for the house idiom's four words (padded,
    upper case); OFF otherwise; read per call."""
    reader = new_symbol("openai_egress_stop_enabled")
    assert callable(reader), "openai_egress_stop_enabled missing"
    for v in ON_VALUES:
        monkeypatch.setenv(FLAG, v)
        assert reader() is True, repr(v)
    for v in OFF_VALUES:
        if v is None:
            monkeypatch.delenv(FLAG, raising=False)
        else:
            monkeypatch.setenv(FLAG, v)
        assert reader() is False, repr(v)
    monkeypatch.setenv(FLAG, "true")
    assert reader() is True
    monkeypatch.delenv(FLAG, raising=False)
    assert reader() is False


def test_s12d_02_class_message_and_surfaces():
    """RED: OpenAIEgressStoppedError is an LLMUnavailableError; the message is a
    constant free of the fallback matchers' words; the closed surface set."""
    cls = new_symbol("OpenAIEgressStoppedError")
    msg = stop_message()
    assert isinstance(cls, type), "OpenAIEgressStoppedError missing"
    assert issubclass(cls, abs_.LLMUnavailableError), cls.__mro__
    assert isinstance(msg, str) and msg, msg
    assert str(cls(msg)) == msg
    low = msg.lower()
    for w in BANNED_WORDS:
        assert w not in low, (w, msg)
    assert new_symbol("OPENAI_EGRESS_SURFACES") == SURFACES
    for name in (
        "OPENAI_EGRESS_STOP_MESSAGE",
        "OPENAI_EGRESS_STOP_LOG",
        "_OPENAI_EGRESS_STOP_FLAG",
    ):
        value = new_symbol(name)
        assert isinstance(value, str) and value.isascii(), (name, value)
    assert new_symbol("_OPENAI_EGRESS_STOP_FLAG") == FLAG


# ---------------------------------------------------------------------------
# S12D-03 .. S12D-05: the chokepoint
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("preflight", (False, True), ids=("preflight_off", "preflight_on"))
def test_s12d_03_chokepoint_on_sends_no_byte(monkeypatch, logs, preflight):
    """RED (base: one 401 request, AuthenticationError): ON, guarded_llm_create
    raises exactly OpenAIEgressStoppedError; zero requests; zero calls of every
    R-12D-5 recorder."""
    full_config(monkeypatch, stop="true", preflight=preflight)
    wire = install_wire(monkeypatch)
    calls = install_call_recorders(monkeypatch)
    st, out = guarded()
    assert wire.requests == [], wire.paths()
    assert st == "raised" and type(out) is stop_class(), (st, type(out).__name__)
    for name in R5_NAMES:
        assert calls.n(name) == 0, (name, calls.names)


def test_s12d_04_stop_after_prologue_before_spend(monkeypatch, logs):
    """RED: ON, the stop line is emitted, the stop sees the prologue's writes
    (store False, an extra_body store False) and the spend reader is never read."""
    full_config(monkeypatch, stop="true")
    wire = install_wire(monkeypatch)
    calls = install_call_recorders(monkeypatch)
    seen = []
    real = _REAL_STOP

    def _spy(surface):
        import inspect

        frame = inspect.currentframe().f_back
        kw = dict(frame.f_locals.get("kwargs") or {})
        seen.append((surface, kw.get("store"), dict(kw.get("extra_body") or {})))
        if real is not None:
            return real(surface)
        return None

    monkeypatch.setattr(abs_, "stop_openai_egress_if_enabled", _spy, raising=False)
    st, out = guarded(store=True, extra_body={"store": True, "s12d_keep": 1})
    assert seen == [("chat_completions", False, {"store": False, "s12d_keep": 1})], seen
    assert calls.n("spend_breaker_enabled") == 0, calls.names
    assert wire.requests == [], wire.paths()
    assert len(stop_records(logs)) == 1, [r.getMessage() for r in logs.handler.records]
    assert st == "raised" and type(out) is stop_class()


def _function(path, name):
    tree = ast.parse((ROOT / path).read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node
    raise AssertionError((path, name))


def _callee_name(call):
    f = call.func
    if isinstance(f, ast.Name):
        return f.id
    if isinstance(f, ast.Attribute):
        return f.attr
    return None


def _stop_calls(node):
    return [
        n
        for n in ast.walk(node)
        if isinstance(n, ast.Call) and _callee_name(n) == "stop_openai_egress_if_enabled"
    ]


def test_s12d_05_ast_placement_in_guarded_llm_create():
    """RED: statement 1 stays the store write; exactly ONE top-level
    stop_openai_egress_if_enabled("chat_completions") after the extra_body if and
    before `spend_ticket = None`; it names no kwargs."""
    fn = _function("app/services/api_budget_service.py", "guarded_llm_create")
    body = list(fn.body)
    if (
        body
        and isinstance(body[0], ast.Expr)
        and isinstance(getattr(body[0], "value", None), ast.Constant)
        and isinstance(body[0].value.value, str)
    ):
        body = body[1:]
    first = ast.unparse(body[0])
    assert first == "kwargs['store'] = False", first
    calls = _stop_calls(fn)
    assert len(calls) == 1, [ast.unparse(c) for c in calls]
    call = calls[0]
    assert [type(a).__name__ for a in call.args] == ["Constant"], ast.unparse(call)
    assert call.args[0].value == "chat_completions" and not call.keywords
    idx = [
        i
        for i, s in enumerate(body)
        if isinstance(s, ast.Expr) and s.value is call
    ]
    assert len(idx) == 1, "the stop is not a top-level statement"
    i_stop = idx[0]
    i_if = [
        i
        for i, s in enumerate(body)
        if isinstance(s, ast.If) and "extra_body" in ast.unparse(s)
    ]
    i_ticket = [
        i for i, s in enumerate(body) if ast.unparse(s) == "spend_ticket = None"
    ]
    assert i_if and i_ticket, (i_if, i_ticket)
    assert i_if[0] < i_stop < i_ticket[0], (i_if, i_stop, i_ticket)
    names = {n.id for n in ast.walk(body[i_stop]) if isinstance(n, ast.Name)}
    assert "kwargs" not in names, names


# ---------------------------------------------------------------------------
# S12D-06 .. S12D-09: moderation and the router
# ---------------------------------------------------------------------------
def test_s12d_06_moderation_on_fails_open_with_no_byte(monkeypatch, logs):
    """RED: ON, moderate_output answers allowed True with zero requests; neither
    the OpenAI client nor the moderation model is read; ONE fail-open WARNING
    carrying the constant; no ERROR."""
    full_config(monkeypatch, stop="true")
    wire = install_wire(monkeypatch)
    reset_clients(monkeypatch)
    calls = install_call_recorders(monkeypatch)
    st, out = moderate()
    assert wire.requests == [], wire.paths()
    assert st == "ok" and out.allowed is True and out.reason is None, (st, out)
    assert calls.n("openai_service.get_client") == 0, calls.names
    assert calls.n("moderation_model") == 0, calls.names
    fail_open = [
        r
        for r in logs.handler.records
        if r.name == "app.services.content_safety_service"
        and r.getMessage().startswith("[content_safety] L3 moderation API failed")
    ]
    assert [(r.levelname, r.getMessage()) for r in fail_open] == [
        (
            "WARNING",
            "[content_safety] L3 moderation API failed (fail-open): " + str(stop_message()),
        )
    ], [r.getMessage() for r in fail_open]
    assert error_records(logs) == []


def test_s12d_07_claude_moderation_untouched(monkeypatch, logs):
    """PIN: the moderation role ON, consent 3, the stop ON: the Claude branch
    runs (stubbed) exactly once; zero OpenAI requests; no stop line."""
    full_config(monkeypatch, stop="true")
    monkeypatch.setenv("ENABLE_ANTHROPIC_MODERATION", "true")
    set_consent(monkeypatch, 3)
    wire = install_wire(monkeypatch)
    reset_clients(monkeypatch)
    seen = []

    async def _claude(text):
        seen.append(text)
        return True, None

    monkeypatch.setattr(llm_router, "moderate_with_claude", _claude)
    st, out = moderate()
    assert st == "ok" and out.allowed is True, (st, out)
    assert seen == ["synthetic shopping text"], seen
    assert wire.requests == [], wire.paths()
    assert stop_records(logs) == []


def test_s12d_08_anthropic_routed_site_untouched(monkeypatch, logs):
    """PIN: the text role ON, consent 3, the stop ON: route('parse', ...) returns
    the stubbed Claude result; the OpenAI dispatch is never called; zero
    requests; no stop line."""
    full_config(monkeypatch, stop="true")
    monkeypatch.setenv("ENABLE_ANTHROPIC_TEXT", "true")
    set_consent(monkeypatch, 3)
    wire = install_wire(monkeypatch)
    sentinel = llm_router.ClaudeChatResult(
        '{"products": []}', "stop", {}, model_config.anthropic_model("text"), "end_turn"
    )
    claude_calls = []

    async def _claude(site, spec, request, lane):
        claude_calls.append(site)
        return sentinel

    dispatched = []

    async def _dispatch(client, **kw):
        dispatched.append(kw.get("model"))
        return await abs_.guarded_llm_create(client, **kw)

    monkeypatch.setattr(llm_router, "_dispatch_claude", _claude)
    st, out = _run(
        _capture(
            llm_router.route(
                "parse",
                _dispatch,
                real_client(),
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "synthetic system"},
                    {"role": "user", "content": "synthetic s12d text"},
                ],
                max_tokens=64,
            )
        )
    )
    assert (st, out) == ("ok", sentinel), (st, out)
    assert claude_calls == ["parse"] and dispatched == [], (claude_calls, dispatched)
    assert wire.requests == [], wire.paths()
    assert stop_records(logs) == []


def test_s12d_09_pre_v3_decision_lands_on_the_stop(monkeypatch, logs):
    """RED (base: one 401 request): the text role ON, no consent, pre-v3 ON, the
    stop ON: route('parse', guarded_llm_create, ...) raises the stop class with
    zero requests."""
    full_config(monkeypatch, stop="true")
    monkeypatch.setenv("ENABLE_ANTHROPIC_TEXT", "true")
    monkeypatch.setenv("ENABLE_OPENAI_PRE_V3", "true")
    set_consent(monkeypatch, None)
    wire = install_wire(monkeypatch)
    st, out = _run(
        _capture(
            llm_router.route("parse", abs_.guarded_llm_create, real_client(), **chat_kwargs())
        )
    )
    assert wire.requests == [], wire.paths()
    assert st == "raised" and type(out) is stop_class(), (st, type(out).__name__)


# ---------------------------------------------------------------------------
# S12D-10 .. S12D-11: the log line, no ERROR, no Sentry
# ---------------------------------------------------------------------------
def test_s12d_10_one_line_per_process_per_surface(monkeypatch, logs):
    """RED: three chat stops and two moderation stops log exactly two WARNING
    records (args ('chat_completions',), ('moderations',)); after the test seam
    one more chat stop logs again."""
    full_config(monkeypatch, stop="true")
    wire = install_wire(monkeypatch)
    reset_clients(monkeypatch)
    for _ in range(3):
        guarded()
    for _ in range(2):
        moderate()
    recs = stop_records(logs)
    assert [(r.levelname, r.args) for r in recs] == [
        ("WARNING", ("chat_completions",)),
        ("WARNING", ("moderations",)),
    ], [(r.levelname, r.args) for r in recs]
    reset = new_symbol("_reset_openai_egress_stop_state")
    assert callable(reset)
    reset()
    guarded()
    recs = stop_records(logs)
    assert len(recs) == 3 and recs[-1].args == ("chat_completions",), [r.args for r in recs]
    assert wire.requests == [], wire.paths()


def test_s12d_11_no_sentry_event_no_error_record(monkeypatch, logs):
    """RED: across a chat and a moderation stop no capture_message /
    capture_exception call and no record at ERROR or above; and the stop
    happened (zero requests)."""
    import sentry_sdk

    full_config(monkeypatch, stop="true")
    wire = install_wire(monkeypatch)
    reset_clients(monkeypatch)
    captured = []
    monkeypatch.setattr(sentry_sdk, "capture_message", lambda *a, **k: captured.append(a))
    monkeypatch.setattr(sentry_sdk, "capture_exception", lambda *a, **k: captured.append(a))
    st, out = guarded()
    mst, mout = moderate()
    assert wire.requests == [], wire.paths()
    assert type(out) is stop_class(), type(out).__name__
    assert mst == "ok" and mout.allowed is True
    assert captured == []
    assert error_records(logs) == []


# ---------------------------------------------------------------------------
# S12D-12 .. S12D-13: flag-OFF identity (PIN, FULL configuration + recorders)
# ---------------------------------------------------------------------------
OFF_CASES = [
    (stop, pre, False)
    for stop in (None, "false", "garbage")
    for pre in (False, True)
] + [(None, False, True), ("false", True, True)]


@pytest.mark.parametrize("stop,preflight,base_url", OFF_CASES)
def test_s12d_12_chokepoint_flag_off_identity(monkeypatch, logs, stop, preflight, base_url):
    """PIN: OFF, the SDK's AuthenticationError propagates after exactly ONE
    request to /v1/chat/completions with store false (no SDK retry at
    OPENAI_MAX_RETRIES=1); the spend read + admit once each; preflight ON one
    admission and no W1-3 record (a 401 = the server answered); no stop line."""
    import openai

    full_config(monkeypatch, stop=stop, preflight=preflight, base_url=base_url)
    wire = install_wire(monkeypatch)
    calls = install_call_recorders(monkeypatch)
    st, out = guarded()
    assert st == "raised" and type(out) is openai.AuthenticationError, (st, out)
    assert wire.paths() == ["/v1/chat/completions"], wire.paths()
    assert wire.requests[0][2].get("store") is False, wire.requests[0][2]
    assert calls.n("spend_breaker_enabled") == 1, calls.names
    assert calls.n("admit_openai_dispatch") == 1, calls.names
    assert calls.n("llm_preflight_breaker_enabled") == 1, calls.names
    assert calls.n("_openai_dispatch_admission") == (1 if preflight else 0), calls.names
    for name in (
        "openai_record_failure",
        "openai_record_success",
        "openai_release_half_open_probe",
        "record_openai_response",
        "record_openai_response_soon",
    ):
        assert calls.n(name) == 0, (name, calls.names)
    assert stop_records(logs) == []


@pytest.mark.parametrize("stop", (None, "false", "garbage"))
def test_s12d_13_moderation_flag_off_identity(monkeypatch, logs, stop):
    """PIN: OFF, ONE request to /v1/moderations; allowed True; the fail-open
    WARNING carries the SDK's 401 text; no stop line."""
    full_config(monkeypatch, stop=stop)
    wire = install_wire(monkeypatch)
    reset_clients(monkeypatch)
    st, out = moderate()
    assert st == "ok" and out.allowed is True and out.reason is None, (st, out)
    assert wire.paths() == ["/v1/moderations"], wire.paths()
    fail_open = [
        r.getMessage()
        for r in logs.handler.records
        if r.name == "app.services.content_safety_service"
        and r.levelname == "WARNING"
        and r.getMessage().startswith("[content_safety] L3 moderation API failed (fail-open): ")
    ]
    assert len(fail_open) == 1 and "401" in fail_open[0], fail_open
    assert SYN_401_MESSAGE in fail_open[0], fail_open
    assert stop_records(logs) == []


# ---------------------------------------------------------------------------
# S12D-14 .. S12D-17: every site, the verdict fallback, the S81-04c arms
# ---------------------------------------------------------------------------
P1 = {
    "name": "Aventus 100ml",
    "brand": "Creed",
    "category": "fragrances",
    "specs": {"concentration": "Eau de Parfum"},
    "reviews": {"average_rating": 4.5},
}
P2 = {
    "name": "Layton 125ml",
    "brand": "Parfums de Marly",
    "category": "fragrances",
    "specs": {"concentration": "Eau de Parfum"},
    "reviews": {"average_rating": 4.4},
}
HTML = (
    "<html><head><title>Creed Aventus 100ml</title></head><body>"
    "<h1>Creed Aventus</h1><p>An aromatic fragrance.</p></body></html>"
)
JPEG = b"\xff\xd8" + b"\x00" * 64


def _pin_verdict_models(mp, model):
    from app.services.model_router_service import model_router

    async def _gm(*_a, **_k):
        return model

    async def _ru(*_a, **_k):
        return None

    mp.setattr(model_router, "get_model", _gm)
    mp.setattr(model_router, "record_usage", _ru)


async def _site(site, mp):
    """Drive the REAL site function (the real route, the real chokepoint, the
    site's own client from a reset memo)."""
    if site == "classify":
        return await es.classify_category_llm(["Creed Aventus", "Layton"])
    if site == "parse":
        return await es.parse_product_query("Creed Aventus vs Parfums de Marly Layton")
    if site == "specs":
        return await es.extract_specs(
            "Creed", "Aventus", "100ml", "fragrances", "[snippet_1] Eau de Parfum"
        )
    if site == "price":
        return await es.extract_price(
            "Creed", "Aventus", "100ml", "bahrain", "[snippet_1] 125.000 BHD"
        )
    if site == "price_training":
        return await es.extract_price_from_training_data("Creed", "Aventus", "100ml", "bahrain")
    if site == "reviews":
        return await es.extract_reviews("Creed", "Aventus", "100ml", "[snippet_1] lovely")
    if site == "verdict":
        _pin_verdict_models(mp, model_config.standard_model())
        return await es.generate_comparison(P1, P2, "bahrain", category="fragrances")
    if site == "verdict_fallback":
        # The fallback dispatch fires only on a rate-limited primary; its real
        # route + chokepoint with the re-wrapped client the site passes.
        return await llm_router.route(
            "verdict_fallback",
            abs_.guarded_llm_create,
            es.get_client().with_options(max_retries=model_config.openai_fallback_max_retries()),
            model=model_config.standard_model(),
            messages=[
                {"role": "system", "content": "synthetic system"},
                {"role": "user", "content": "synthetic user"},
            ],
            max_tokens=32,
            response_format={"type": "json_object"},
        )
    if site == "image_tier3":
        return await imgsvc.extract_image_via_gpt(
            "Creed Aventus", [{"link": "https://shop.example.test/a", "snippet": "Aventus"}]
        )
    if site == "vision_v1":
        return await osvc.identify_products([{"bytes": JPEG, "mime_type": "image/jpeg"}])
    if site == "vision_v2":
        mp.setenv("ENABLE_VISION_IDENTITY_V2", "true")
        return await osvc.identify_products([{"bytes": JPEG, "mime_type": "image/jpeg"}])
    if site == "specs_targeted":
        return await osvc.extract_specs_targeted(
            "Creed", "Aventus", "100ml", "fragrances", ["concentration"], "[snippet_1] EDP"
        )
    if site == "specs_synthesized":
        return await osvc.extract_specs_synthesized(
            "Creed", "Aventus", "100ml", "fragrances", ["concentration"]
        )
    if site == "disambiguate":
        return await osvc.disambiguate_variant_line(
            "fragrances", "Creed Aventus", "Creed Aventus for Her", "gender"
        )
    if site == "url_extract":
        return await urlsvc.extract_with_ai(
            "https://shop.example.test/p/aventus", HTML, {"key": "generic", "name": "Example"}
        )
    if site == "moderation":
        return await css.ContentSafetyService().moderate_output("synthetic shopping text")
    raise AssertionError(site)  # pragma: no cover


SITES = (
    "classify",
    "parse",
    "specs",
    "price",
    "price_training",
    "reviews",
    "verdict",
    "verdict_fallback",
    "image_tier3",
    "vision_v1",
    "vision_v2",
    "specs_targeted",
    "specs_synthesized",
    "disambiguate",
    "url_extract",
    "moderation",
)
# Sites with no catching arm of their own: the dispatch error propagates to
# the caller (vision: image_routes; verdict_fallback: driven here through its
# route call directly). Both states raise; the class differs by design.
RAISING_SITES = ("vision_v1", "vision_v2", "verdict_fallback")
SITE_PATH = {s: "/v1/chat/completions" for s in SITES}
SITE_PATH["moderation"] = "/v1/moderations"


def _norm(value, texts):
    s = json.dumps(value, sort_keys=True, default=repr)
    for t in texts:
        if t:
            s = s.replace(json.dumps(t)[1:-1], "<ERR>")
    return s


def _run_site(site, mp, stop):
    full_config(mp, stop=stop)
    wire = install_wire(mp)
    reset_clients(mp)
    counter = install_stop_counter(mp)
    st, out = _run(_capture(_site(site, mp)))
    return wire, counter, st, out


@pytest.mark.parametrize("site", SITES)
def test_s12d_14_per_site_pair(monkeypatch, logs, site):
    """RED (ON half: requests > 0 at base): OFF the site sends N_off requests to
    its path and returns V_off; ON it sends ZERO, the stop runs exactly N_off
    times and V_on == V_off once the two error texts are replaced by one token
    (the RAISING_SITES raise in both states: AuthenticationError OFF, the stop
    class ON)."""
    import openai

    w_off, c_off, st_off, v_off = _run_site(site, monkeypatch, None)
    n_off = w_off.count(SITE_PATH[site])
    assert n_off >= 1 and w_off.count() == n_off, (site, w_off.paths())
    assert c_off.surfaces == [], c_off.surfaces
    off_text = str(v_off) if st_off == "raised" else None
    reset = new_symbol("_reset_openai_egress_stop_state")
    if reset is not None:
        reset()
    monkeypatch.setattr(abs_, "_openai_breaker_cache", None)
    w_on, c_on, st_on, v_on = _run_site(site, monkeypatch, "true")
    assert w_on.requests == [], (site, w_on.paths())
    surface = "moderations" if site == "moderation" else "chat_completions"
    assert c_on.surfaces == [surface] * n_off, (site, c_on.surfaces, n_off)
    if site in RAISING_SITES:
        assert st_off == "raised" and type(v_off) is openai.AuthenticationError, v_off
        assert st_on == "raised" and type(v_on) is stop_class(), type(v_on).__name__
        return
    assert st_off == st_on, (st_off, st_on, v_off, v_on)
    msg = stop_message()
    auth_texts = [off_text] if off_text else []
    auth_texts += _sdk_texts()
    assert _norm(v_on, [msg] + auth_texts) == _norm(v_off, [msg] + auth_texts), (v_off, v_on)


def _sdk_texts():
    """The SDK's str() for the recorder's 401, measured once per process."""
    if _SDK_TEXT:
        return list(_SDK_TEXT)
    import httpx2
    import openai

    req = httpx2.Request("POST", "https://" + OPENAI_HOST + "/v1/chat/completions")
    resp = httpx2.Response(401, json=_err_json(), request=req)
    try:
        client = real_client()
        err = client._make_status_error_from_response(resp)
    except Exception:  # noqa: BLE001
        err = openai.AuthenticationError(
            "Error code: 401 - " + str(_err_json()), response=resp, body=_err_json()
        )
    _SDK_TEXT.extend([str(err), repr(err), type(err).__name__ + ": " + str(err)])
    return list(_SDK_TEXT)


_SDK_TEXT = []


def test_s12d_15_verdict_fallback_not_attempted(monkeypatch, logs):
    """RED: the verdict model differs from the standard model, the stop ON:
    generate_comparison stops exactly ONCE, the router never sees
    'verdict_fallback', the result is the base failure dict."""
    full_config(monkeypatch, stop="true")
    wire = install_wire(monkeypatch)
    reset_clients(monkeypatch)
    counter = install_stop_counter(monkeypatch)
    _pin_verdict_models(monkeypatch, "gpt-4o")
    assert model_config.standard_model() != "gpt-4o"
    keys = []
    real_route = llm_router.route

    async def _route(site, *a, **k):
        keys.append(site)
        return await real_route(site, *a, **k)

    monkeypatch.setattr(llm_router, "route", _route)
    st, out = _run(_capture(es.generate_comparison(P1, P2, "bahrain", category="fragrances")))
    assert wire.requests == [], wire.paths()
    assert counter.surfaces == ["chat_completions"], counter.surfaces
    assert keys == ["verdict"], keys
    assert (st, out) == (
        "ok",
        ({"winner_index": 0, "error": "verdict generation unavailable"}, ZERO),
    ), (st, out)


ARMS = (
    "parse",
    "specs",
    "price",
    "price_training",
    "reviews",
    "verdict",
    "url_extract",
)
PREFIX = {
    "parse": "Product parsing error",
    "specs": "Specs extraction error",
    "price": "Price extraction error",
    "price_training": "Price fallback error",
    "reviews": "Reviews extraction error",
    "verdict": "Comparison generation error",
    "url_extract": "AI extraction error",
    "camera": "[IMAGE] Vision call failed",
}
LOGGER = {a: "app.services.extraction_service" for a in ARMS}
LOGGER["url_extract"] = "app.services.url_extraction_service"
LOGGER["camera"] = "app.api.image_routes"


def _delivery(arm, msg):
    """The S81-04c W13_DELIVERY shapes with the class text = the stop message."""
    return {
        "parse": ({"products": [], "error": "product parsing unavailable"}, ZERO),
        "specs": ({"brand": "Creed", "model": "Aventus", "error": msg}, ZERO),
        "price": ({"amount": None, "currency": "BHD", "error": msg}, ZERO),
        "price_training": ({"amount": None, "currency": "BHD", "error": msg}, ZERO),
        "reviews": ({"average_rating": None, "error": "reviews extraction unavailable"}, ZERO),
        "verdict": ({"winner_index": 0, "error": "verdict generation unavailable"}, ZERO),
        "url_extract": {"error": msg},
    }[arm]


def _camera(mp):
    import hashlib  # noqa: F401
    from fastapi.testclient import TestClient

    from app.api import image_routes
    from app.api.auth_routes import get_optional_user
    from app.main import app as fastapi_app
    from app.middleware.rate_limiter import limiter
    from app.services import usage_service

    mp.setattr(limiter, "enabled", False)
    led = types.SimpleNamespace(consumes=[], refunds=[], labels=[])

    def _consume(user_id, *_a, **_k):
        led.consumes.append(user_id)

        async def _r():
            return {
                "allowed": True,
                "reason": None,
                "tier": "free",
                "consumed": True,
                "consumed_keys": None,
                "remaining": {"daily": 2, "monthly": 9, "lifetime_free": 2},
            }

        return _r()

    def _refund(user_id, consumed_keys=None, *_a, **_k):
        led.refunds.append((user_id, consumed_keys))

        async def _r():
            return None

        return _r()

    for mod in (usage_service, image_routes):
        mp.setattr(mod, "consume_comparison_credit", _consume, raising=False)
        mp.setattr(mod, "refund_comparison_credit", _refund, raising=False)
    real_ff = image_routes.fire_and_forget

    def _ff(coro, *a, **kw):
        led.labels.append(kw.get("label"))
        return real_ff(coro, *a, **kw)

    mp.setattr(image_routes, "fire_and_forget", _ff)
    fastapi_app.dependency_overrides[get_optional_user] = lambda: {
        "id": "s12d-camera-user",
        "email": "s12d@example.test",
        "access_token": "s12d-" + "bearer",
    }
    try:
        client = TestClient(fastapi_app, raise_server_exceptions=False)
        files = [("images", ("p%d.jpg" % i, JPEG, "image/jpeg")) for i in range(2)]
        resp = client.post("/api/v1/image/identify", files=files)
    finally:
        fastapi_app.dependency_overrides.pop(get_optional_user, None)
    return resp, led


def _fields(resp):
    try:
        body = resp.json()
    except ValueError:
        return {}
    if isinstance(body, dict) and isinstance(body.get("detail"), dict):
        return body["detail"]
    return body if isinstance(body, dict) else {}


@pytest.mark.parametrize("arm", ARMS + ("camera",))
def test_s12d_16_the_eight_s04c_arms_warn_by_type(monkeypatch, logs, arm):
    """RED: the stop ON, role flags OFF: each S81-04c arm logs exactly ONE WARNING
    '<prefix>: OpenAIEgressStoppedError' and no ERROR; the delivered value is the
    base failure value of that arm (camera: the coded 503, one consume, one
    refund under the vision_exception label)."""
    full_config(monkeypatch, stop="true")
    wire = install_wire(monkeypatch)
    reset_clients(monkeypatch)
    if arm == "camera":
        resp, led = _camera(monkeypatch)
        body = _fields(resp)
        assert wire.requests == [], wire.paths()
        assert resp.status_code == 503, (resp.status_code, body)
        assert body.get("code") == "LLM_UNAVAILABLE" and body.get("success") is False, body
        assert led.consumes == ["s12d-camera-user"], led.consumes
        assert led.refunds == [("s12d-camera-user", None)], led.refunds
        assert led.labels == ["usage_refund.image.vision_exception"], led.labels
    else:
        if arm == "verdict":
            _pin_verdict_models(monkeypatch, model_config.standard_model())
        st, out = _run(_capture(_arm(arm)))
        assert wire.requests == [], wire.paths()
        assert (st, out) == ("ok", _delivery(arm, stop_message())), (st, out)
    mine = [
        (r.levelname, bool(r.exc_info), r.getMessage())
        for r in logs.handler.records
        if r.name == LOGGER[arm] and r.getMessage().startswith(PREFIX[arm])
    ]
    assert mine == [("WARNING", False, PREFIX[arm] + ": OpenAIEgressStoppedError")], mine
    assert error_records(logs) == [], [r.getMessage() for r in error_records(logs)]


async def _arm(arm):
    if arm == "url_extract":
        return await urlsvc.extract_with_ai(
            "https://shop.example.test/p/aventus", HTML, {"key": "generic", "name": "Example"}
        )
    if arm == "parse":
        return await es.parse_product_query("Creed Aventus vs Parfums de Marly Layton")
    if arm == "specs":
        return await es.extract_specs(
            "Creed", "Aventus", "100ml", "fragrances", "[snippet_1] Eau de Parfum"
        )
    if arm == "price":
        return await es.extract_price(
            "Creed", "Aventus", "100ml", "bahrain", "[snippet_1] 125.000 BHD"
        )
    if arm == "price_training":
        return await es.extract_price_from_training_data("Creed", "Aventus", "100ml", "bahrain")
    if arm == "reviews":
        return await es.extract_reviews("Creed", "Aventus", "100ml", "[snippet_1] lovely")
    if arm == "verdict":
        return await es.generate_comparison(P1, P2, "bahrain", category="fragrances")
    raise AssertionError(arm)  # pragma: no cover


def test_s12d_17_flag_read_per_call_in_one_process(monkeypatch, logs):
    """RED: the stop ON, then the variable deleted between two calls: the first
    raises the stop class with zero requests, the second sends ONE request."""
    import openai

    full_config(monkeypatch, stop="true")
    wire = install_wire(monkeypatch)
    client = real_client()
    st1, out1 = guarded(client)
    n1 = wire.count()
    monkeypatch.delenv(FLAG, raising=False)
    st2, out2 = guarded(client)
    assert n1 == 0 and type(out1) is stop_class(), (n1, type(out1).__name__)
    assert wire.count() == 1 and type(out2) is openai.AuthenticationError, (wire.paths(), out2)


# ---------------------------------------------------------------------------
# S12D-18 .. S12D-19: the operator scripts (part B, ruling C-1)
# ---------------------------------------------------------------------------
PAGES = [{"host": "shop.example.test", "text": "Top notes: bergamot. Eau de Parfum."}]


def _scripts(mp):
    from scripts import seed_spec_spine as seed
    from scripts import shadow_experiments as shadow

    sleeps = []

    async def _sleep(*a, **k):
        sleeps.append(a)

    mp.setattr(shadow.asyncio, "sleep", _sleep)
    return seed, shadow, sleeps


def test_s12d_18_scripts_on_send_no_byte(monkeypatch, logs):
    """RED: ON, extract_spine_specs returns {} with zero requests and its WARNING
    carries the constant; _create_with_retry raises the stop class with zero
    requests and zero sleeps."""
    full_config(monkeypatch, stop="true")
    wire = install_wire(monkeypatch)
    reset_clients(monkeypatch)
    seed, shadow, sleeps = _scripts(monkeypatch)
    st, out = _run(_capture(seed.extract_spine_specs("Creed", "Aventus", PAGES)))
    assert (st, out) == ("ok", {}), (st, out)
    assert wire.requests == [], wire.paths()
    warn = [
        r.getMessage()
        for r in logs.handler.records
        if r.name == "seed_spec_spine" and r.levelname == "WARNING"
    ]
    assert warn == ["seed extraction failed for Creed Aventus: " + str(stop_message())], warn
    st, out = _run(_capture(shadow._create_with_retry(real_client(), **chat_kwargs())))
    assert wire.requests == [], wire.paths()
    assert st == "raised" and type(out) is stop_class(), (st, type(out).__name__)
    assert sleeps == [], sleeps


@pytest.mark.parametrize("stop", (None, "false", "garbage"))
def test_s12d_19_scripts_flag_off_identity(monkeypatch, logs, stop):
    """PIN: OFF, ONE request each with store false; C4 returns {} after the 401;
    C5 re-raises the AuthenticationError with no retry and no sleep."""
    import openai

    full_config(monkeypatch, stop=stop)
    wire = install_wire(monkeypatch)
    reset_clients(monkeypatch)
    seed, shadow, sleeps = _scripts(monkeypatch)
    st, out = _run(_capture(seed.extract_spine_specs("Creed", "Aventus", PAGES)))
    assert (st, out) == ("ok", {}), (st, out)
    assert wire.paths() == ["/v1/chat/completions"], wire.paths()
    assert wire.requests[0][2].get("store") is False
    st, out = _run(_capture(shadow._create_with_retry(real_client(), **chat_kwargs())))
    assert st == "raised" and type(out) is openai.AuthenticationError, (st, out)
    assert wire.paths() == ["/v1/chat/completions"] * 2, wire.paths()
    assert wire.requests[1][2].get("store") is False
    assert sleeps == [], sleeps
    assert stop_records(logs) == []


# ---------------------------------------------------------------------------
# S12D-20: THE CENSUS (rulings D-6 and G-3)
# ---------------------------------------------------------------------------
DISPATCH_SUFFIXES = (
    ("chat", "completions", "create"),
    ("moderations", "create"),
    ("embeddings", "create"),
    ("responses", "create"),
    ("images", "generate"),
    ("files", "create"),
    ("batches", "create"),
    ("models", "list"),
    ("models", "retrieve"),
)
EXPECTED_DISPATCH = {
    ("app/services/api_budget_service.py", "guarded_llm_create"): 2,
    ("app/services/content_safety_service.py", "moderate_output"): 1,
    ("scripts/seed_spec_spine.py", "extract_spine_specs"): 1,
    ("scripts/shadow_experiments.py", "_create_with_retry"): 1,
    # MON1 (on the base since 445f8de3): the active check's metadata call, one
    # models.retrieve per provider (openai and anthropic; the chain rule of D-6
    # cannot tell them apart). Its OpenAI leg is gated by the in-use rule
    # (ruling K-2 (3.11)), not by a stop statement: asserted below.
    ("app/services/llm_credential_probe.py", "_metadata_call"): 2,
    # RP-2 (RULINGS_REPLAY_S81_12D, the replay onto main c6ebbd2e, which carries
    # S81-07): the measurement harness's capability check on its OWN Anthropic
    # client (models.retrieve; the chain rule of D-6 cannot tell the SDKs apart).
    # NOT an OpenAI dispatch: its file builds exactly one SDK client, anthropic's
    # AsyncAnthropic, and names no openai module (asserted below); no stop.
    ("scripts/meas_claude_gate.py", "_attempt"): 1,
}
GATED_BY_IN_USE = {("app/services/llm_credential_probe.py", "_metadata_call")}
NOT_OPENAI_SDK = {("scripts/meas_claude_gate.py", "_attempt")}
CLIENT_CTORS = ("OpenAI", "AsyncOpenAI", "AzureOpenAI", "AsyncAzureOpenAI", "Anthropic", "AsyncAnthropic")
EXPECTED_SURFACE = {
    ("app/services/api_budget_service.py", "guarded_llm_create"): "chat_completions",
    ("app/services/content_safety_service.py", "moderate_output"): "moderations",
    ("scripts/seed_spec_spine.py", "extract_spine_specs"): "script",
    ("scripts/shadow_experiments.py", "_create_with_retry"): "script",
}
IN_TRY = {
    ("app/services/content_safety_service.py", "moderate_output"),
    ("scripts/seed_spec_spine.py", "extract_spine_specs"),
}
URL_ALLOWED = {"app/services/llm_provider.py", "app/services/sentry_service.py"}


def _chain(node):
    """The attribute segments of a callee, through calls: get_client().chat.x ->
    ['get_client', 'chat', 'x']."""
    out = []
    while True:
        if isinstance(node, ast.Attribute):
            out.append(node.attr)
            node = node.value
        elif isinstance(node, ast.Call):
            node = node.func
        elif isinstance(node, ast.Name):
            out.append(node.id)
            break
        else:
            break
    return list(reversed(out))


def _is_dispatch(chain):
    if "messages" in chain:  # the anthropic SDK (ruling D-6): by the callee chain
        return False
    for suf in DISPATCH_SUFFIXES:
        if tuple(chain[-len(suf):]) == suf and len(chain) > len(suf):
            return True
    if len(chain) >= 3 and chain[-1] == "create" and "audio" in chain[:-1]:
        return True
    return False


def _py_files():
    for top in ("app", "scripts"):
        for p in sorted((ROOT / top).rglob("*.py")):
            yield p.relative_to(ROOT).as_posix(), p


def _parents(tree):
    parents = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parents[child] = node
    return parents


def _enclosing(node, parents, kinds):
    cur = parents.get(node)
    while cur is not None and not isinstance(cur, kinds):
        cur = parents.get(cur)
    return cur


def test_s12d_20_the_egress_census():
    """RED: the OpenAI SDK dispatch calls under app/ and scripts/ are EXACTLY the
    five of the census; in each such function a stop with its surface literal
    precedes every dispatch (inside the same try where the arm must catch it);
    no other function calls the stop; no app module imports tiktoken; no
    api.openai.com URL literal outside llm_provider.py and sentry_service.py.
    RP-2 (the replay onto c6ebbd2e): the S81-07 harness's models.retrieve on its
    own Anthropic client is counted by the chain rule and exempted by name; its
    file is proven to build no OpenAI client."""
    found = {}
    stops = {}
    tiktoken = []
    urls = []
    subclasses = []
    ctors = {}
    openai_mods = {}
    not_openai_files = {k[0] for k in NOT_OPENAI_SDK}
    for rel, path in _py_files():
        try:
            src = path.read_text(encoding="utf-8-sig")
            tree = ast.parse(src)
        except (SyntaxError, UnicodeDecodeError):
            continue
        parents = _parents(tree)
        fn_kinds = (ast.FunctionDef, ast.AsyncFunctionDef)
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for b in node.bases:
                    if _chain(b)[-1:] == ["OpenAIEgressStoppedError"]:
                        subclasses.append((rel, node.name))
            if isinstance(node, (ast.Import, ast.ImportFrom)) and rel.startswith("app/"):
                names = [a.name for a in node.names]
                mod = getattr(node, "module", None) or ""
                if mod.split(".")[0] == "tiktoken" or any(
                    n.split(".")[0] == "tiktoken" for n in names
                ):
                    tiktoken.append((rel, node.lineno))
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if OPENAI_HOST in node.value and rel not in URL_ALLOWED:
                    fn = _enclosing(node, parents, fn_kinds)
                    is_doc = (
                        isinstance(parents.get(node), ast.Expr)
                        and fn is not None
                        and fn.body
                        and fn.body[0] is parents.get(node)
                    ) or (
                        isinstance(parents.get(node), ast.Expr)
                        and isinstance(parents.get(parents.get(node)), ast.Module)
                    )
                    if not is_doc:
                        urls.append((rel, node.lineno))
            if rel in not_openai_files:
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    mods = [a.name for a in node.names] + [getattr(node, "module", None) or ""]
                    if any(m.split(".")[0] == "openai" for m in mods):
                        openai_mods.setdefault(rel, []).append(node.lineno)
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    if node.value == "openai" or node.value.startswith("openai."):
                        openai_mods.setdefault(rel, []).append(node.lineno)
            if not isinstance(node, ast.Call):
                continue
            chain = _chain(node.func)
            if rel in not_openai_files and chain and chain[-1] in CLIENT_CTORS:
                ctors.setdefault(rel, []).append(chain[-1])
            fn = _enclosing(node, parents, fn_kinds)
            key = (rel, fn.name if fn is not None else "<module>")
            if _is_dispatch(chain):
                found.setdefault(key, []).append(node)
            if chain and chain[-1] == "stop_openai_egress_if_enabled":
                stops.setdefault(key, []).append((node, parents))
    got = {k: len(v) for k, v in found.items()}
    assert got == EXPECTED_DISPATCH, got
    assert tiktoken == [], tiktoken
    assert urls == [], urls
    # J-11 (b): the stop class has no subclass, by source and at run time.
    assert subclasses == [], subclasses
    cls = new_symbol("OpenAIEgressStoppedError")
    assert isinstance(cls, type), "OpenAIEgressStoppedError missing"
    assert cls.__subclasses__() == [], cls.__subclasses__()
    # RP-2: each NOT_OPENAI_SDK file builds exactly one SDK client, anthropic's, and
    # names no openai module (an import or an importlib string).
    for rel in sorted(not_openai_files):
        assert ctors.get(rel) == ["AsyncAnthropic"], (rel, ctors.get(rel))
        assert openai_mods.get(rel, []) == [], (rel, openai_mods.get(rel))
    assert set(stops) == set(EXPECTED_DISPATCH) - GATED_BY_IN_USE - NOT_OPENAI_SDK, sorted(stops)
    # K-2 (3.11): providers_in_use reads the stop predicate by module attribute.
    fn = _function("app/services/llm_credential_health.py", "providers_in_use")
    reads = [
        _chain(n.func)
        for n in ast.walk(fn)
        if isinstance(n, ast.Call) and _chain(n.func)[-1:] == ["openai_egress_stop_enabled"]
    ]
    assert len(reads) == 1 and len(reads[0]) == 2, reads
    for key, dispatches in found.items():
        if key in GATED_BY_IN_USE or key in NOT_OPENAI_SDK:
            continue
        calls = stops[key]
        assert len(calls) == 1, (key, len(calls))
        call, parents = calls[0]
        assert len(call.args) == 1 and isinstance(call.args[0], ast.Constant), key
        assert call.args[0].value == EXPECTED_SURFACE[key], (key, call.args[0].value)
        assert call.args[0].value in SURFACES
        for d in dispatches:
            assert call.lineno < d.lineno, (key, call.lineno, d.lineno)
        if key in IN_TRY:
            t_stop = _enclosing(call, parents, (ast.Try,))
            for d in dispatches:
                assert t_stop is not None and _enclosing(d, parents, (ast.Try,)) is t_stop, key
        else:
            stmt = parents.get(call)
            fn = _enclosing(call, parents, (ast.FunctionDef, ast.AsyncFunctionDef))
            assert isinstance(stmt, ast.Expr) and stmt in fn.body, key


# ---------------------------------------------------------------------------
# S12D-21 .. S12D-22: the two re-raising arms exempt exactly the stop class
# (ruling J-3 / J-5 / J-11)
# ---------------------------------------------------------------------------
# A role flag whose role covers neither the verdict site nor url_extract:
# any_role_enabled() is True while both sites still dispatch to OpenAI.
ROLE_ON_ELSEWHERE = ("ENABLE_ANTHROPIC_CRITIC", "ENABLE_ANTHROPIC_VISION")


def _reraising_arm(arm):
    if arm == "verdict":
        return es.generate_comparison(P1, P2, "bahrain", category="fragrances")
    return urlsvc.extract_with_ai(
        "https://shop.example.test/p/aventus", HTML, {"key": "generic", "name": "Example"}
    )


@pytest.mark.parametrize("role", ROLE_ON_ELSEWHERE)
@pytest.mark.parametrize("arm", ("verdict", "url_extract"))
def test_s12d_21_role_on_stop_takes_the_base_return(monkeypatch, logs, arm, role):
    """RED (base: one 401 request; an AuthenticationError logs ERROR): a role
    flag ON, the stop ON: the arm does NOT re-raise the stop class; it returns
    its base failure value and logs exactly ONE WARNING '<prefix>:
    OpenAIEgressStoppedError'; zero requests; no ERROR."""
    full_config(monkeypatch, stop="true")
    monkeypatch.setenv(role, "true")
    assert llm_router.any_role_enabled() is True
    wire = install_wire(monkeypatch)
    reset_clients(monkeypatch)
    if arm == "verdict":
        _pin_verdict_models(monkeypatch, model_config.standard_model())
    st, out = _run(_capture(_reraising_arm(arm)))
    assert wire.requests == [], wire.paths()
    assert (st, out) == ("ok", _delivery(arm, stop_message())), (st, out)
    mine = [
        (r.levelname, bool(r.exc_info), r.getMessage())
        for r in logs.handler.records
        if r.name == LOGGER[arm] and r.getMessage().startswith(PREFIX[arm])
    ]
    assert mine == [("WARNING", False, PREFIX[arm] + ": OpenAIEgressStoppedError")], mine
    assert error_records(logs) == [], [r.getMessage() for r in error_records(logs)]


def _class_source(mp, kind):
    """Install the source of one OTHER member of the LLMUnavailableError class
    at the chokepoint; returns the class the arm must re-raise."""
    if kind == "consent":
        async def _raise(client, **kw):
            raise llm_router.ConsentUpdateRequiredError()

        mp.setattr(abs_, "guarded_llm_create", _raise)
        return llm_router.ConsentUpdateRequiredError
    if kind == "anthropic":
        async def _raise(client, **kw):
            raise llm_router.AnthropicDispatchError("APIStatusError", 529, True)

        mp.setattr(abs_, "guarded_llm_create", _raise)
        return llm_router.AnthropicDispatchError
    if kind == "admission":
        mp.setenv("ENABLE_LLM_PREFLIGHT_BREAKER", "true")
        mp.setattr(abs_, "_openai_dispatch_admission", lambda: (False, False, False))
        return abs_.LLMUnavailableError
    if kind == "spend":
        mp.setenv("ENABLE_LLM_SPEND_BREAKER", "true")

        async def _admit(*_a, **_k):
            sb._refuse_dispatch("live", 1.0, 0.1)

        mp.setattr(sb, "admit_openai_dispatch", _admit)
        return abs_.LLMUnavailableError
    raise AssertionError(kind)  # pragma: no cover


@pytest.mark.parametrize("kind", ("consent", "anthropic", "admission", "spend"))
@pytest.mark.parametrize("arm", ("verdict", "url_extract"))
def test_s12d_22_role_on_other_members_still_reraised(monkeypatch, logs, arm, kind):
    """PIN (green at base): with a role flag ON (and the stop OFF, so the
    admission / spend denials are reached) every OTHER member of the class (the
    consent refusal, an Anthropic dispatch failure, the bare
    LLMUnavailableError of a W1-3 admission denial and of a spend denial) is
    still re-raised at both arms, with its WARNING by type; zero requests."""
    full_config(monkeypatch, stop=None)
    monkeypatch.setenv("ENABLE_ANTHROPIC_CRITIC", "true")
    wire = install_wire(monkeypatch)
    reset_clients(monkeypatch)
    if arm == "verdict":
        _pin_verdict_models(monkeypatch, model_config.standard_model())
    want = _class_source(monkeypatch, kind)
    st, out = _run(_capture(_reraising_arm(arm)))
    assert st == "raised" and type(out) is want, (st, type(out).__name__)
    assert type(out) is not stop_class()
    assert wire.requests == [], wire.paths()
    mine = [
        (r.levelname, r.getMessage())
        for r in logs.handler.records
        if r.name == LOGGER[arm] and r.getMessage().startswith(PREFIX[arm])
    ]
    assert mine == [("WARNING", PREFIX[arm] + ": " + want.__name__)], mine


# ---------------------------------------------------------------------------
# MC-1 .. MC-4: MON1's contract inside this unit (ruling K-2 / K-3)
# ---------------------------------------------------------------------------
from app.services import llm_credential_health as cred  # noqa: E402

PROBE_FLAG = "ENABLE_LLM_CREDENTIAL_PROBE"


def _alerts(mp):
    from app.services import sentry_service

    sent = []

    def _send(kind, provider, state, status):
        sent.append((kind, provider, state, status))

    mp.setattr(sentry_service, "capture_credential_alert", _send)
    return sent


def _auth401():
    """A real openai.AuthenticationError as the pinned SDK builds it for the
    recorder's 401 (structured code invalid_api_key)."""
    import httpx2

    req = httpx2.Request("POST", "https://" + OPENAI_HOST + "/v1/chat/completions")
    resp = httpx2.Response(401, json=_err_json(), request=req)
    return real_client()._make_status_error_from_response(resp)


def test_mc_1_classifier_ignores_the_stop_class(monkeypatch):
    """RED (the class is absent at base): MON1's classify returns None for the
    stop class from every source, and note_failure with it writes no state and
    sends no alert."""
    sent = _alerts(monkeypatch)
    cls = new_symbol("OpenAIEgressStoppedError")
    assert isinstance(cls, type), "OpenAIEgressStoppedError missing"
    exc = cls(stop_message())
    for source in cred.SOURCES:
        assert cred.classify("openai", exc, source) is None, source
        cred.note_failure("openai", exc, source)
    assert cred.health_snapshot() == {}, cred.health_snapshot()
    assert sent == []


@pytest.mark.parametrize("stop", ("true", None), ids=("stop_on", "stop_off_pin_half"))
def test_mc_2_probe_pass_never_calls_openai_while_stopped(monkeypatch, logs, stop):
    """RED (stop_on) + PIN half (stop_off): one probe tick with
    ENABLE_LLM_CREDENTIAL_PROBE on. Stop ON: ZERO OpenAI requests, no record,
    openai not probed. Stop OFF: its one models request (401 invalid_api_key)
    and the rejected record, as at base."""
    from app.services import llm_credential_probe as probe

    full_config(monkeypatch, stop=stop)
    monkeypatch.setenv(PROBE_FLAG, "true")
    sent = _alerts(monkeypatch)
    wire = install_wire(monkeypatch)
    reset_clients(monkeypatch)
    st, out = _run(_capture(probe.tick()))
    assert st == "ok", (st, out)
    if stop is None:
        std = model_config.standard_model()
        assert wire.paths() == ["/v1/models/" + std], wire.paths()
        assert out == {"openai": "rejected"}, out
        snap = cred.health_snapshot()["llm_credential"]["openai"]
        assert (snap["state"], snap["source"], snap["last_status"]) == (
            "rejected",
            "probe",
            401,
        ), snap
        assert [s[1:3] for s in sent] == [("openai", "rejected")], sent
        return
    assert wire.requests == [], wire.paths()
    assert out == {}, out
    assert cred.health_snapshot() == {}, cred.health_snapshot()
    assert sent == []


@pytest.mark.parametrize("stop", ("true", None), ids=("stop_on", "stop_off_pin_half"))
def test_mc_3_openai_not_in_use_while_stopped(monkeypatch, stop):
    """RED (stop_on) + PIN half (stop_off): a stale rejected openai state is
    recorded. Stop ON: providers_in_use() has no openai, the monitor view
    answers 200 ok, and the /health entry still shows the last state (never
    erased). Stop OFF: openai in use, 503 LLM_CREDENTIAL_UNUSABLE, as at base."""
    full_config(monkeypatch, stop=None)
    _alerts(monkeypatch)
    cred.note_failure("openai", _auth401(), "dispatch")
    stale = cred.health_snapshot()["llm_credential"]["openai"]
    assert stale["state"] == "rejected", stale
    if stop is not None:
        monkeypatch.setenv(FLAG, stop)
    in_use = cred.providers_in_use()
    code, body = cred.monitor_view()
    after = cred.health_snapshot()["llm_credential"]["openai"]
    assert after == stale, (after, stale)
    if stop is None:
        assert in_use == ("openai",), in_use
        assert (code, body.get("code")) == (503, "LLM_CREDENTIAL_UNUSABLE"), (code, body)
        return
    assert "openai" not in in_use, in_use
    assert code == 200 and body.get("status") == "ok", (code, body)
    assert "openai" not in body.get("providers", {}), body


def test_mc_4_stopped_calls_leave_the_health_state_untouched(monkeypatch, logs):
    """RED (base: the chat call's 401 records rejected and sends an alert): the
    stop ON, one stopped chat call at the chokepoint on each breaker branch and
    one stopped moderation call: the health snapshot is unchanged ({}) and no
    alert event is sent; zero requests."""
    full_config(monkeypatch, stop="true")
    sent = _alerts(monkeypatch)
    wire = install_wire(monkeypatch)
    reset_clients(monkeypatch)
    before = cred.health_snapshot()
    st, out = guarded()
    monkeypatch.setenv("ENABLE_LLM_PREFLIGHT_BREAKER", "true")
    monkeypatch.setattr(abs_, "_openai_dispatch_admission", lambda: (True, True, False))
    st2, out2 = guarded()
    mst, mout = moderate()
    assert wire.requests == [], wire.paths()
    assert cred.health_snapshot() == before == {}, cred.health_snapshot()
    assert sent == [], sent
    assert type(out) is stop_class() and type(out2) is stop_class(), (out, out2)
    assert mst == "ok" and mout.allowed is True
