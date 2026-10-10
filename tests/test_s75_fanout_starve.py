"""FANOUT-STARVE (session 75, 2026-10-09) -- RED file: fan-out code truth, observability
and the q-form parity levers.

Spec set (authoritative, the later wins): scratchpad/specs/FANOUT_STARVE_SPEC.md (section 5
test rows T1-T16), FANOUT_STARVE_REVIEW.md (B1, M1-M8, m1-m9) and
FABLE_RULINGS_FANOUT_STARVE.md (FS-R1..R20, BINDING; section D is the final list). D3 is
DEFERRED (FS-R2), so T7-T10 are not written. T20/T21 live in their own files
(tests/test_shutdown_drain.py, tests/test_retro_w0_4_efg.py) and T22/T23 are appended to
tests/test_be_harness.py. Every file:line below is at main 4c0f3c99.

RED at main unless a node says PIN or GUARD. A RED node fails on an AttributeError (a helper
the unit adds) or on the pinned defect's assertion message; PIN nodes are green at main and
must stay green; a GUARD pins today's flag-OFF behaviour (green at main by construction).

Contract this file fixes for GREEN (names the spec leaves open; the rest is the spec's):
  * app.utils.executor: `_DEFAULT_MAX_WORKERS == 96`; `install_default_executor` records the
    installed pool in a module global that `executor_snapshot()` and /health read (FS-R7).
  * app.main startup: one INFO `[loop] class=<cls> uvloop=<bool> UV_THREADPOOL_SIZE=<value|unset>`.
  * app.services.brightdata_service: `_AUTH_ERROR_SEEN: set` (spec D6) and the snapshot state
    reset by `_reset_brightdata_auth_state()` (preferred) or by clearing `_AUTH_ERROR_SEEN`
    and setting `_AUTH_LAST = None`; `brightdata_auth_snapshot()` feeds /health.
  * structured_comparison_service (scs): `StructuredComparisonService._parse_with_budget(query)`
    is the ONE Step-1 seam both entries call (:3848 and :4462): it applies the pre-split
    (ENABLE_PARSE_PRESPLIT, FS-R3 i) and then the stall guard (ENABLE_PARSE_BUDGET, FS-R3 ii),
    returns `(parsed, usage)` exactly like parse_product_query, marks `parsed["_parse_presplit"]`
    / `parsed["_parse_fallback"]` True on those paths (the orchestrator maps them onto
    metadata.parse_presplit / parse_fallback), and emits the ONE INFO
    `[STAGE] parse done elapsed_ms=%d mode=llm|presplit|fallback`. Knob readers:
    `scs._parse_timeout_seconds()` (8.0), `scs._unified_search_timeout_seconds()` (12.0),
    `scs._phase2_min_residual_seconds()` (8.0), float hygiene: non-finite / <= 0 / garbage /
    unset -> the default. The compare deadline both entries record (FS-R4) is the instance
    attribute `_compare_deadline`, a `time.monotonic()` instant (the clock of :4325).
    `_build_partial_response` writes `metadata.phase2_skipped` / `parse_presplit` /
    `parse_fallback` (flag ON only, FS-R3 m9 / FS-R4).

Hygiene: pure ASCII, LF; bounded runner only; netguard on (loopback and numeric hosts only);
every sentinel is built at runtime by concatenation; every "env unset" row delenvs (FS-R13 m3).
"""
from __future__ import annotations

import asyncio
import inspect
import json
import logging
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
import pytest

os.environ.setdefault("OPENAI_API_KEY", "sk" + "-test-dummy")

# FY2 / FY11 (post-adversary rulings, 2026-10-09): app.main is imported at MODULE scope, after
# the setdefault above, so configure_logging() (whose root_logger.handlers.clear() would drop
# caplog's handler) and main.py's load_dotenv + the conftest dotenv guard run at COLLECTION,
# before any node's fixture sets a variable (T6 and T13 were order-dependent otherwise).
import app.main  # noqa: E402,F401
import app.services.structured_comparison_service as scs  # noqa: E402
from app.services.extraction_service import classify_category_from_text  # noqa: E402
from app.utils.prompt_sanitizer import sanitize_prompt_input  # noqa: E402

# FY1: the REAL httpx.AsyncClient, captured ONCE at import; _bd_client's factory builds on it
# (re-reading the attribute per call wrapped the previous factory, which ignored the new
# transport, so T12's 403 / 402 legs were answered 401).
_REAL_ASYNC_CLIENT = httpx.AsyncClient

REPO_ROOT = Path(__file__).resolve().parent.parent
RAILWAY_JSON = REPO_ROOT / "railway.json"
PROCFILE = REPO_ROOT / "Procfile"
UV_TOKEN = 'UV_THREADPOOL_SIZE="${UV_THREADPOOL_SIZE:-64}"'
EXECUTOR_ENV = "ADAPTER_EXECUTOR_MAX_WORKERS"
SCS_LOGGER = "app.services.structured_comparison_service"
BD_LOGGER = "app.services.brightdata_service"
# Runtime-built sentinels (no credential shape anywhere in this file).
BD_KEY_SENTINEL = "bd" + "-sentinel-" + "k9q"
BD_ZONE = "zone_x7q"
BD_QUERY = "probe query x7q"
BD_BODY = "Token expired"
ISO_UTC = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|\+00:00)$")
STAGE_RE = re.compile(r"^\[STAGE\] parse done elapsed_ms=\d+ mode=(llm|presplit|fallback)\b")
GARBAGE = [None, "", "abc", "0", "-1", "nan", "inf"]
GARBAGE_IDS = ["unset", "empty", "abc", "zero", "negative", "nan", "inf"]

LLM_PARSED = {
    "products": [
        {"brand": "Apple", "name": "iPhone 15", "variant": None, "category": "electronics",
         "search_query": "Apple iPhone 15"},
        {"brand": "Samsung", "name": "Galaxy S24", "variant": None, "category": "electronics",
         "search_query": "Samsung Galaxy S24"},
    ],
    "comparison_type": "value",
}
LLM_USAGE = {"prompt_tokens": 10, "completion_tokens": 5}
PRODUCT = {"brand": "", "name": "Ajmal Aristocrat", "variant": None, "category": "fragrances",
           "search_query": "Ajmal Aristocrat", "_explicit": True}


# ===========================================================================
# helpers
# ===========================================================================
class _RecordingExecutor(ThreadPoolExecutor):
    """A default executor that records every submit (the T5 / T19 recorder)."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.submits = []

    def submit(self, fn, /, *args, **kwargs):
        self.submits.append(getattr(fn, "__name__", repr(fn)))
        return super().submit(fn, *args, **kwargs)


def _run_with_default_executor(coro_factory, executor):
    """Run coro_factory(loop) on a fresh loop whose default executor is `executor`."""
    loop = asyncio.new_event_loop()
    try:
        loop.set_default_executor(executor)
        return loop.run_until_complete(coro_factory(loop))
    finally:
        executor.shutdown(wait=True)
        loop.close()


def _railway_command() -> str:
    data = json.loads(RAILWAY_JSON.read_text(encoding="utf-8"))
    return str(data["deploy"]["startCommand"]).strip()


def _procfile_command() -> str:
    for raw in PROCFILE.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.startswith("web:"):
            return line.split(":", 1)[1].strip()
    pytest.fail("Procfile declares no 'web:' process type")


def _set_or_del(monkeypatch, name, raw):
    if raw is None:
        monkeypatch.delenv(name, raising=False)
    else:
        monkeypatch.setenv(name, raw)


def _slow_parse(delay, result):
    """A parse_product_query stand-in that records its calls and sleeps `delay`."""
    calls = []

    async def stub(query):
        calls.append(query)
        await asyncio.sleep(delay)
        return result

    stub.calls = calls
    return stub


def _cost(svc):
    return (svc.gpt_calls, svc.api_calls, svc.total_cost)


def _explicit_half(raw):
    return sanitize_prompt_input(raw, max_length=80)


def _assert_explicit_shape(products, halves):
    """The explicit-pair shape of scs:3829-3845 (brand "", sanitized name, keyword category)."""
    assert isinstance(products, list) and len(products) == 2, products
    for product, raw in zip(products, halves):
        safe = _explicit_half(raw)
        assert product.get("brand") == "", product
        assert product.get("name") == safe, product
        assert product.get("search_query") == safe, product
        assert product.get("variant") is None, product
        assert product.get("_explicit") is True, product
        assert product.get("category") == classify_category_from_text(safe), product


def _reset_bd_auth_state(bd):
    reset = getattr(bd, "_reset_brightdata_auth_state", None)
    if callable(reset):
        reset()
        return
    seen = getattr(bd, "_AUTH_ERROR_SEEN", None)
    if isinstance(seen, set):
        seen.clear()
    if hasattr(bd, "_AUTH_LAST"):
        bd._AUTH_LAST = None


def _bd_client(monkeypatch, bd, status, text):
    """Replace httpx.AsyncClient (the brightdata_service.py:120 construction) with one whose
    transport is an httpx.MockTransport answering `status`/`text` (zero network). FY1: the
    factory builds on the module-import capture `_REAL_ASYNC_CLIENT`, never on the attribute
    a previous call of this helper replaced."""
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(status, text=text)

    def factory(*args, **kwargs):
        return _REAL_ASYNC_CLIENT(transport=httpx.MockTransport(handler),
                                  timeout=kwargs.get("timeout"))

    monkeypatch.setattr(bd.httpx, "AsyncClient", factory)
    return calls


def _records(caplog, level=None, prefix=None):
    out = []
    for record in caplog.records:
        if level is not None and record.levelno != level:
            continue
        message = record.getMessage()
        if prefix is not None and not message.startswith(prefix):
            continue
        out.append(message)
    return out


class _NoRead:
    """A deadline stand-in that fails the test if the flag-OFF Phase-2 path reads it."""

    def _boom(self, *_a, **_k):
        raise AssertionError("FS-R4: the flag-OFF Phase-2 path read _compare_deadline")

    __sub__ = __rsub__ = __lt__ = __le__ = __gt__ = __ge__ = __float__ = _boom


@contextmanager
def _phase_mocks(svc, *, search_web_impl, specs_seen, ratings):
    """Patch ONLY the inner phase-1 / phase-2 machinery so the REAL _fetch_product_data runs
    to its return (the tests/test_partial_specs_stash_on_price_timeout.py:46 pattern, extended
    over Phase 2). Every network touch is mocked; the specs stub records the
    `search_results` payload it was handed and the rating stub records each call."""

    async def _specs(*_a, **kwargs):
        specs_seen.append(kwargs.get("search_results", "<missing>"))
        return {"concentration": "EDP", "volume_ml": 100, "scent_family": "woody"}

    async def _price(*_a, **_k):
        return None

    async def _reviews(*_a, **_k):
        return None

    async def _rating(*_a, **_k):
        ratings.append(time.monotonic())
        return {"rating": None, "review_count": None, "rating_verified": False,
                "rating_source": None}

    async def _empty(*_a, **_k):
        return {}

    with patch.object(svc, "_get_specs", side_effect=_specs), \
            patch.object(svc, "_get_price", side_effect=_price), \
            patch.object(svc, "_get_reviews", side_effect=_reviews), \
            patch.object(svc, "_get_verified_rating", side_effect=_rating), \
            patch.object(svc, "_smart_fallback_extract", side_effect=_empty), \
            patch.object(svc, "_track_serper_cost", lambda *a, **k: None), \
            patch.object(scs, "search_web", search_web_impl), \
            patch.object(scs, "tier2_fill_non_negotiables", side_effect=_empty), \
            patch.object(scs, "tier3_synthesize_non_negotiables", side_effect=_empty), \
            patch.object(scs, "collect_retailer_ratings", lambda *a, **k: []), \
            patch.object(scs, "get_product_image_url", AsyncMock(return_value=None)):
        yield


@pytest.fixture
def svc():
    return scs.StructuredComparisonService()


@pytest.fixture
def parse_flags_off(monkeypatch):
    monkeypatch.delenv("ENABLE_PARSE_BUDGET", raising=False)
    monkeypatch.delenv("ENABLE_PARSE_PRESPLIT", raising=False)
    monkeypatch.delenv("PARSE_TIMEOUT_SECONDS", raising=False)


@pytest.fixture
def bd_env(monkeypatch):
    """FS-R13 m4: the Bright Data module state is reset before AND after the node; the budget
    gate is delenv'd (else _bd_record reaches api_budget_service -> Redis) and the fallback is
    set like tests/test_brightdata_fallback.py:92-101."""
    from app.services import brightdata_service as bd
    monkeypatch.delenv("ENABLE_BRIGHTDATA_BUDGET_GATE", raising=False)
    monkeypatch.setenv("ENABLE_BRIGHTDATA_FALLBACK", "true")
    monkeypatch.setenv("BRIGHTDATA_API_KEY", BD_KEY_SENTINEL)
    monkeypatch.setenv("BRIGHTDATA_ZONE", BD_ZONE)
    _reset_bd_auth_state(bd)
    yield bd
    _reset_bd_auth_state(bd)


# ===========================================================================
# T1 / T2 -- D1 executor default as code truth
# ===========================================================================
@pytest.mark.parametrize("raw", GARBAGE[:5] + ["96.0"],
                         ids=GARBAGE_IDS[:5] + ["float"])
def test_T1_executor_default_is_96(monkeypatch, raw):
    """T1 (spec 5 / D1; FS-R13 m3 delenv): env unset, "", "abc", "0", "-1", "96.0" -> 96.
    RED at main: _DEFAULT_MAX_WORKERS is 40 (executor.py:30)."""
    from app.utils import executor
    _set_or_del(monkeypatch, EXECUTOR_ENV, raw)
    assert executor._DEFAULT_MAX_WORKERS == 96, (
        "D1: executor._DEFAULT_MAX_WORKERS is %r, want 96" % (executor._DEFAULT_MAX_WORKERS,))
    assert executor.default_executor_size() == 96, (
        "D1: default_executor_size() with %s=%r is %r, want 96"
        % (EXECUTOR_ENV, raw, executor.default_executor_size()))


def test_T1_pin_executor_env_override_wins(monkeypatch):
    """T1 PIN (green at main, stays green): ADAPTER_EXECUTOR_MAX_WORKERS="7" -> 7
    (executor.py:33-37 precedence unchanged by D1)."""
    from app.utils import executor
    monkeypatch.setenv(EXECUTOR_ENV, "7")
    assert executor.default_executor_size() == 7


def test_T2_install_log_names_96(monkeypatch, caplog):
    """T2 (spec 5 / D1): with the env unset the boot line (executor.py:56) reads
    `max_workers=96`. RED at main: max_workers=40."""
    from app.utils import executor
    monkeypatch.delenv(EXECUTOR_ENV, raising=False)
    caplog.set_level(logging.INFO, logger="app.utils.executor")
    loop = asyncio.new_event_loop()
    pool = None
    try:
        pool = executor.install_default_executor(loop)
    finally:
        if pool is not None:
            pool.shutdown(wait=False)
        loop.close()
    lines = [r.getMessage() for r in caplog.records
             if r.name == "app.utils.executor" and "installed" in r.getMessage()]
    assert lines, "no `[executor] default ThreadPoolExecutor installed` line was logged"
    assert any("max_workers=96" in line for line in lines), (
        "D1: the install line reads %r, want max_workers=96" % (lines,))


# ===========================================================================
# T3 -- D2 start command carries the UV_THREADPOOL_SIZE env prefix
# ===========================================================================
@pytest.mark.parametrize("source, reader",
                         [("railway.json", _railway_command), ("Procfile", _procfile_command)])
def test_T3_start_command_carries_the_uv_threadpool_env_prefix(source, reader):
    """T3 (spec 5 / D2; FS-R6): whitespace tokens of both start commands contain `env` and
    UV_THREADPOOL_SIZE="${UV_THREADPOOL_SIZE:-64}" BEFORE the `uvicorn` token, with `exec`
    first. RED at main: neither token is present (railway.json:7, Procfile:1)."""
    tokens = reader().split()
    assert tokens and tokens[0] == "exec", tokens
    assert "uvicorn" in tokens, tokens
    before_uvicorn = tokens[:tokens.index("uvicorn")]
    assert "env" in before_uvicorn, (
        "D2: %s start command has no `env` token before `uvicorn`: %r" % (source, tokens))
    assert UV_TOKEN in before_uvicorn, (
        "D2: %s start command has no %s token before `uvicorn`: %r" % (source, UV_TOKEN, tokens))
    assert tokens.index("env") < tokens.index(UV_TOKEN) < tokens.index("uvicorn"), tokens


def test_T3_pin_start_commands_are_byte_identical():
    """T3 PIN (tests/test_start_command.py:208 mirror, green at main, stays green): Railway
    boots from railway.json, so the two strings must never drift."""
    assert _railway_command() == _procfile_command()


# ===========================================================================
# T4 / T5 -- PINs of the library mechanism and the F2 trap
# ===========================================================================
def test_T4_pin_anyio_getaddrinfo_runs_on_the_loop():
    """T4 PIN (spec 5; anyio 4.14.2 measured): anyio's asyncio backend resolves through
    `get_running_loop().getaddrinfo`, i.e. libuv's threadpool under uvloop and the loop's
    default executor under asyncio. An anyio upgrade that moves DNS elsewhere must be noticed."""
    import anyio._backends._asyncio as backend
    source = inspect.getsource(backend.AsyncIOBackend.getaddrinfo)
    assert "get_running_loop().getaddrinfo" in source, source


def test_T5_pin_asyncio_getaddrinfo_submits_to_the_default_executor():
    """T5 PIN (spec 5 / D2, the F2 trap): under plain asyncio `loop.getaddrinfo` is ONE submit
    to the loop's DEFAULT executor -- the qaren-worker pool once main.py:179-182 installed it --
    so `--loop asyncio` would queue DNS behind the ~30 curl fetches. Numeric host, no network
    (tests/_netguard.py:14-15 allows IP literals)."""
    recorder = _RecordingExecutor(max_workers=2, thread_name_prefix="t5-recorder")

    async def go(loop):
        return await loop.getaddrinfo("127.0.0.1", 80)

    infos = _run_with_default_executor(go, recorder)
    assert infos, "getaddrinfo returned nothing for the loopback literal"
    assert len(recorder.submits) == 1, (
        "F2: expected exactly one default-executor submit for loop.getaddrinfo, saw %r"
        % (recorder.submits,))


# ===========================================================================
# T6 -- D2 boot truth line
# ===========================================================================
def test_T6_boot_line_reports_loop_class_and_uv_threadpool(monkeypatch, caplog):
    """T6 (spec 5 / D2; FS-R13 m3): the app's startup handlers (driven through the REAL ASGI
    lifespan, the tests/test_health_loop_lag.py:304 pattern) log ONE INFO
    `[loop] class=<cls> uvloop=False UV_THREADPOOL_SIZE=unset` when the variable is unset
    (uvloop is absent on the pinned venv). RED at main: no `[loop]` line exists."""
    from fastapi.testclient import TestClient
    import app.main as app_main
    monkeypatch.delenv("UV_THREADPOOL_SIZE", raising=False)
    caplog.set_level(logging.INFO)
    with TestClient(app_main.app):
        pass
    lines = _records(caplog, prefix="[loop] ")
    assert lines, (
        "D2: no `[loop] class=... uvloop=... UV_THREADPOOL_SIZE=...` INFO line at startup; "
        "INFO lines seen: %r" % (_records(caplog, level=logging.INFO)[:12],))
    assert len(lines) == 1, lines
    line = lines[0]
    assert re.search(r"\bclass=\S+", line), line
    assert "uvloop=False" in line, line
    assert "UV_THREADPOOL_SIZE=unset" in line, line


# ===========================================================================
# T11 -- D4 Serper connect default
# ===========================================================================
@pytest.fixture
def serper_fail_fast(monkeypatch):
    for name in ("SERPER_READ_TIMEOUT", "SERPER_CONNECT_TIMEOUT"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("ENABLE_SERPER_FAIL_FAST", "true")
    from app.services import serper_service
    return serper_service


def test_T11_serper_connect_default_is_8(serper_fail_fast):
    """T11 (spec 5 / D4; FS-R13 m3): fail-fast ON, SERPER_CONNECT_TIMEOUT unset -> connect 8.0,
    read 10.0 unchanged. RED at main: serper_service.py:397 reads 3.0. The companion one-liner
    is tests/test_serper_fail_fast.py:127 (3.0 -> 8.0)."""
    timeout = serper_fail_fast._serper_timeout()
    assert isinstance(timeout, httpx.Timeout), timeout
    assert timeout.read == 10.0, timeout
    assert timeout.connect == 8.0, (
        "D4: fail-fast connect default is %r, want 8.0 (serper_service.py:397)" % (timeout.connect,))


def test_T11_pin_serper_connect_env_override_wins(serper_fail_fast, monkeypatch):
    """T11 PIN (green at main, stays green): SERPER_CONNECT_TIMEOUT="2" -> 2.0 per call."""
    monkeypatch.setenv("SERPER_CONNECT_TIMEOUT", "2")
    assert serper_fail_fast._serper_timeout().connect == 2.0


# ===========================================================================
# T12 / T13 -- D6 Bright Data 401 observability and /health
# ===========================================================================
@pytest.mark.asyncio
async def test_T12_brightdata_401_is_one_error_event_without_secrets(bd_env, monkeypatch, caplog):
    """T12 (spec 5 / D6; FS-R13 m4, m8): a 401 with body "Token expired" and a runtime-built
    key sentinel in the env -> EXACTLY one ERROR record (the Sentry event under
    LoggingIntegration(ERROR), sentry_service.py:651) whose message contains "status=401"
    and names BRIGHTDATA_API_KEY, and carries neither the query, the body, the zone nor the
    key; the existing WARNING (brightdata_service.py:130-133) stays but drops the response
    text for 401; a second 401 in the process adds no ERROR; a 403 is its own once-per-status
    ERROR; a 402 keeps today's WARNING and adds no ERROR. RED at main: no ERROR is logged and
    the 401 WARNING carries the body."""
    bd = bd_env
    caplog.set_level(logging.DEBUG, logger=BD_LOGGER)
    _bd_client(monkeypatch, bd, 401, BD_BODY)
    out = await bd.bd_search_web(BD_QUERY)
    assert out.get("organic") == [] and out.get("error") == "brightdata_unavailable", out
    errors = _records(caplog, level=logging.ERROR)
    assert len(errors) == 1, (
        "D6 (F3): want exactly one ERROR record after a Bright Data 401, got %d: %r"
        % (len(errors), errors))
    message = errors[0]
    assert "[brightdata]" in message and "status=401" in message, message
    assert "BRIGHTDATA_API_KEY" in message, message
    for forbidden in (BD_QUERY, BD_BODY, BD_ZONE, BD_KEY_SENTINEL):
        assert forbidden not in message, (forbidden, message)
    warnings = _records(caplog, level=logging.WARNING)
    assert warnings, "the 401 WARNING of brightdata_service.py:130 must stay"
    assert not any(BD_BODY in line for line in warnings), (
        "D6: the 401 WARNING must not carry the response text: %r" % (warnings,))
    assert not any(BD_KEY_SENTINEL in line for line in _records(caplog)), "the key reached a log"
    # a second 401 in the same process: no second ERROR
    await bd.bd_search_web(BD_QUERY + " again")
    assert len(_records(caplog, level=logging.ERROR)) == 1, _records(caplog, level=logging.ERROR)
    # a 403 is a distinct status: one more ERROR, once
    _bd_client(monkeypatch, bd, 403, "Forbidden zone")
    await bd.bd_search_web(BD_QUERY)
    await bd.bd_search_web(BD_QUERY)
    errors = _records(caplog, level=logging.ERROR)
    assert len(errors) == 2 and "status=403" in errors[1], errors
    assert "Forbidden zone" not in errors[1], errors[1]
    # 402: no ERROR, the WARNING as today (brightdata_service.py:130-133)
    caplog.clear()
    _bd_client(monkeypatch, bd, 402, "Payment required q7")
    await bd.bd_search_web(BD_QUERY)
    assert _records(caplog, level=logging.ERROR) == []
    assert any("HTTP 402" in line for line in _records(caplog, level=logging.WARNING)), (
        _records(caplog, level=logging.WARNING))


def test_T13_health_carries_adapter_executor_and_brightdata_auth_after_a_401(bd_env, monkeypatch):
    """T13 (spec 5 / D1 + D6; FS-R7, FS-R13 m3, n6): through the real lifespan (startup installs
    the pool, main.py:179-182) /health carries `adapter_executor` {workers ==
    default_executor_size(), queued >= 0} and lacks `brightdata_auth` before any 401; after a
    401 it carries {"last_status": 401, "at": <iso-utc>} and nothing else under that key;
    status/message are unchanged (tests/test_retro_w1_7_w1_10.py:192 stays green).
    RED at main: /health has no adapter_executor key (main.py:548-553)."""
    from fastapi.testclient import TestClient
    import app.main as app_main
    from app.utils import executor
    bd = bd_env
    monkeypatch.delenv(EXECUTOR_ENV, raising=False)
    with TestClient(app_main.app) as client:
        before = client.get("/health")
        assert before.status_code == 200, before.status_code
        body = before.json()
        assert body["status"] == "healthy" and body["message"] == "MYEZ API is running", body
        assert "brightdata_auth" not in body, sorted(body)
        assert "adapter_executor" in body, (
            "D1 (FS-R7): /health lacks `adapter_executor` after install_default_executor ran at "
            "startup; keys %r" % (sorted(body),))
        snapshot = body["adapter_executor"]
        assert snapshot.get("workers") == executor.default_executor_size(), snapshot
        assert isinstance(snapshot.get("queued"), int) and snapshot["queued"] >= 0, snapshot
        _bd_client(monkeypatch, bd, 401, BD_BODY)
        asyncio.run(bd.bd_search_web(BD_QUERY))
        after = client.get("/health")
        assert after.status_code == 200
        body = after.json()
        assert "brightdata_auth" in body, sorted(body)
        auth = body["brightdata_auth"]
        assert set(auth) == {"last_status", "at"}, auth
        assert auth["last_status"] == 401, auth
        assert isinstance(auth["at"], str) and ISO_UTC.match(auth["at"]), auth
        assert body["status"] == "healthy" and body["message"] == "MYEZ API is running", body
        assert "adapter_executor" in body, sorted(body)


# ===========================================================================
# T14 / T15 -- FS-R3(ii) the parse stall guard and the [STAGE] line
# ===========================================================================
@pytest.mark.asyncio
async def test_T14_stall_guard_off_awaits_the_parse_to_completion(svc, monkeypatch, parse_flags_off):
    """T14 (FS-R3 ii, flag OFF): a parse stub sleeping 0.2 s is awaited to completion and the
    result is the stub's tuple, with the knob set to 0.05 (OFF must not read it).
    RED at main: StructuredComparisonService has no _parse_with_budget (AttributeError)."""
    monkeypatch.setenv("PARSE_TIMEOUT_SECONDS", "0.05")
    stub = _slow_parse(0.2, (LLM_PARSED, LLM_USAGE))
    monkeypatch.setattr(scs, "parse_product_query", stub)
    started = time.monotonic()
    parsed, usage = await svc._parse_with_budget("iPhone 15 vs Galaxy S24")
    assert time.monotonic() - started >= 0.18, "OFF must await the parse to completion"
    assert (parsed, usage) == (LLM_PARSED, LLM_USAGE), (parsed, usage)
    assert stub.calls == ["iPhone 15 vs Galaxy S24"], stub.calls


@pytest.mark.asyncio
async def test_T14_stall_guard_on_falls_back_to_the_explicit_shape(svc, monkeypatch, parse_flags_off,
                                                                   caplog):
    """T14 (FS-R3 ii, flag ON): PARSE_TIMEOUT_SECONDS=0.05 and a parse that stalls -> the
    deterministic split on the FIRST case-insensitive " vs " built exactly like scs:3829-3845
    (brand "", sanitized name, keyword category, _explicit True), `_parse_fallback` True,
    comparison_type "value", NO usage and the cost counters unchanged (n5), the `[STAGE]`
    line in mode=fallback. RED at main: AttributeError."""
    monkeypatch.setenv("ENABLE_PARSE_BUDGET", "true")
    monkeypatch.setenv("PARSE_TIMEOUT_SECONDS", "0.05")
    caplog.set_level(logging.INFO, logger=SCS_LOGGER)
    stub = _slow_parse(5.0, (LLM_PARSED, LLM_USAGE))
    monkeypatch.setattr(scs, "parse_product_query", stub)
    before = _cost(svc)
    started = time.monotonic()
    parsed, usage = await svc._parse_with_budget("iPhone 15 VS Galaxy S24")
    assert time.monotonic() - started < 2.0, "the stall guard did not cut the parse"
    assert stub.calls == ["iPhone 15 VS Galaxy S24"], stub.calls
    _assert_explicit_shape(parsed.get("products"), ("iPhone 15", "Galaxy S24"))
    assert parsed.get("_parse_fallback") is True, parsed
    assert parsed.get("comparison_type") == "value", parsed
    assert not usage, usage
    assert _cost(svc) == before, (before, _cost(svc))
    stage = _records(caplog, prefix="[STAGE] parse done")
    assert len(stage) == 1 and stage[0].rstrip().endswith("mode=fallback"), stage


@pytest.mark.asyncio
async def test_T14_stall_guard_on_without_vs_keeps_the_parse_failure_shape(svc, monkeypatch,
                                                                           parse_flags_off):
    """T14 (FS-R3 ii): a stalled parse on a query WITHOUT " vs " returns a `parsed` that fails
    the :3850 condition (fewer than two products) so the orchestrator ships today's
    parse-failure body; no usage, cost counters unchanged. RED at main: AttributeError."""
    monkeypatch.setenv("ENABLE_PARSE_BUDGET", "true")
    monkeypatch.setenv("PARSE_TIMEOUT_SECONDS", "0.05")
    monkeypatch.setattr(scs, "parse_product_query", _slow_parse(5.0, (LLM_PARSED, LLM_USAGE)))
    before = _cost(svc)
    parsed, usage = await svc._parse_with_budget("iPhone 15 and Galaxy S24")
    assert isinstance(parsed, dict), parsed
    assert len(parsed.get("products") or []) < 2, parsed
    assert not usage, usage
    assert _cost(svc) == before


@pytest.mark.parametrize("raw, want", list(zip(GARBAGE, [8.0] * len(GARBAGE))) + [("3.5", 3.5)],
                         ids=GARBAGE_IDS + ["3.5"])
def test_T14_parse_timeout_knob_hygiene(monkeypatch, raw, want):
    """T14 (FS-R3 ii knob hygiene): PARSE_TIMEOUT_SECONDS unset / "" / "abc" / "0" / "-1" /
    "nan" / "inf" -> 8.0; "3.5" -> 3.5; read per call. RED at main: scs has no
    _parse_timeout_seconds (AttributeError)."""
    _set_or_del(monkeypatch, "PARSE_TIMEOUT_SECONDS", raw)
    assert scs._parse_timeout_seconds() == want


@pytest.mark.asyncio
@pytest.mark.parametrize("flag", ["off", "on"])
async def test_T15_stage_parse_line_in_both_flag_states(svc, monkeypatch, parse_flags_off, caplog,
                                                        flag):
    """T15 (spec 5; FS-R3): ONE INFO `[STAGE] parse done elapsed_ms=<int> mode=llm` on the LLM
    path in BOTH flag states, free of the query text. RED at main: AttributeError."""
    if flag == "on":
        monkeypatch.setenv("ENABLE_PARSE_BUDGET", "true")
        monkeypatch.setenv("PARSE_TIMEOUT_SECONDS", "5")
    caplog.set_level(logging.INFO, logger=SCS_LOGGER)
    monkeypatch.setattr(scs, "parse_product_query", _slow_parse(0.01, (LLM_PARSED, LLM_USAGE)))
    query = "Zorblax Q17 vs Fimbulwinter R3"
    await svc._parse_with_budget(query)
    stage = _records(caplog, prefix="[STAGE] parse done")
    assert len(stage) == 1, "want ONE [STAGE] parse done line, got %r" % (stage,)
    assert STAGE_RE.match(stage[0]), stage[0]
    assert stage[0].rstrip().endswith("mode=llm"), stage[0]
    assert "Zorblax" not in stage[0] and "Fimbulwinter" not in stage[0], stage[0]


# ===========================================================================
# T16 -- D5 / FS-R8 unified-search bound
# ===========================================================================
@pytest.mark.asyncio
async def test_T16_unified_bound_off_awaits_search_web_bare(svc, monkeypatch, caplog):
    """T16 GUARD (D5 flag OFF; green at main by construction, must stay green): with the knob
    at 0.05 and the flag unset, a 0.3 s search_web is awaited to completion ONCE and its
    payload object is handed to _get_specs unchanged; no `[L2.6] unified search timeout`."""
    monkeypatch.delenv("ENABLE_UNIFIED_SEARCH_BOUND", raising=False)
    monkeypatch.setenv("UNIFIED_SEARCH_TIMEOUT_SECONDS", "0.05")
    payload = {"organic": [{"title": "t", "link": "http://127.0.0.1/p", "snippet": "s"}],
               "shopping": []}
    calls, specs_seen, ratings = [], [], []

    async def _search(*args, **kwargs):
        calls.append(args)
        await asyncio.sleep(0.3)
        return payload

    caplog.set_level(logging.WARNING, logger=SCS_LOGGER)
    with _phase_mocks(svc, search_web_impl=_search, specs_seen=specs_seen, ratings=ratings):
        result = await asyncio.wait_for(
            svc._fetch_product_data(dict(PRODUCT), "bahrain", True, True, nocache=True),
            timeout=20.0)
    assert len(calls) == 1, calls
    assert len(specs_seen) == 1 and specs_seen[0] is payload, specs_seen
    assert not any("unified search timeout" in line for line in _records(caplog)), _records(caplog)
    assert result.get("specs"), result


@pytest.mark.asyncio
async def test_T16_unified_bound_on_hands_the_empty_payload_once(svc, monkeypatch, caplog):
    """T16 (D5; FS-R8): flag ON, UNIFIED_SEARCH_TIMEOUT_SECONDS=0.05, a hanging search_web ->
    the specs task receives the explicit EMPTY payload {"organic": []} (so neither specs nor
    reviews re-searches: search_web is called ONCE), and ONE WARNING
    `[L2.6] unified search timeout (limit <s>s)`. RED at main: scs:5393 has no bound, the hang
    is awaited past the 3 s test bound."""
    monkeypatch.setenv("ENABLE_UNIFIED_SEARCH_BOUND", "true")
    monkeypatch.setenv("UNIFIED_SEARCH_TIMEOUT_SECONDS", "0.05")
    calls, specs_seen, ratings = [], [], []

    async def _hang(*args, **kwargs):
        calls.append(args)
        await asyncio.sleep(30)
        return {"organic": [{"title": "late"}]}

    caplog.set_level(logging.WARNING, logger=SCS_LOGGER)
    with _phase_mocks(svc, search_web_impl=_hang, specs_seen=specs_seen, ratings=ratings):
        try:
            result = await asyncio.wait_for(
                svc._fetch_product_data(dict(PRODUCT), "bahrain", True, True, nocache=True),
                timeout=3.0)
        except asyncio.TimeoutError:
            pytest.fail("D5: the unified search at scs:5393 is not bounded -- a hanging "
                        "search_web was awaited past 3 s with the flag ON")
    assert len(calls) == 1, "FS-R8: search_web must be called ONCE, saw %d" % len(calls)
    # FY19 (post-adversary ruling, 2026-10-09) amends this one assertion: the empty payload
    # carries the `_unified_timeout` mark so _get_specs / _get_reviews skip every cache write.
    assert specs_seen == [{"organic": [], "_unified_timeout": True}], specs_seen
    warnings = [line for line in _records(caplog, level=logging.WARNING)
                if line.startswith("[L2.6] unified search timeout")]
    assert len(warnings) == 1 and "(limit " in warnings[0], _records(caplog, level=logging.WARNING)
    assert result.get("specs"), result


@pytest.mark.parametrize("raw, want", list(zip(GARBAGE, [12.0] * len(GARBAGE))) + [("4", 4.0)],
                         ids=GARBAGE_IDS + ["4"])
def test_T16_unified_timeout_knob_hygiene(monkeypatch, raw, want):
    """T16 (D5 knob hygiene): UNIFIED_SEARCH_TIMEOUT_SECONDS garbage / unset -> 12.0; "4" -> 4.0.
    RED at main: scs has no _unified_search_timeout_seconds (AttributeError)."""
    _set_or_del(monkeypatch, "UNIFIED_SEARCH_TIMEOUT_SECONDS", raw)
    assert scs._unified_search_timeout_seconds() == want


# ===========================================================================
# T17 -- FS-R3(i) the pre-split
# ===========================================================================
@pytest.mark.asyncio
async def test_T17_presplit_on_builds_the_explicit_shape_without_the_llm(svc, monkeypatch,
                                                                         parse_flags_off, caplog):
    """T17 (FS-R3 i): ENABLE_PARSE_PRESPLIT on and a clean " vs " split -> the explicit-pair
    shape of scs:3829-3845, `_parse_presplit` True, comparison_type "value", ZERO LLM calls,
    no usage, cost counters unchanged, the `[STAGE]` line in mode=presplit.
    RED at main: AttributeError."""
    monkeypatch.setenv("ENABLE_PARSE_PRESPLIT", "true")
    caplog.set_level(logging.INFO, logger=SCS_LOGGER)
    stub = _slow_parse(0.01, (LLM_PARSED, LLM_USAGE))
    monkeypatch.setattr(scs, "parse_product_query", stub)
    before = _cost(svc)
    parsed, usage = await svc._parse_with_budget("iPhone 15 vs Galaxy S24")
    assert stub.calls == [], "FS-R3: the pre-split must make zero LLM calls, saw %r" % (stub.calls,)
    _assert_explicit_shape(parsed.get("products"), ("iPhone 15", "Galaxy S24"))
    assert parsed.get("_parse_presplit") is True, parsed
    assert parsed.get("comparison_type") == "value", parsed
    assert not usage, usage
    assert _cost(svc) == before
    stage = _records(caplog, prefix="[STAGE] parse done")
    assert len(stage) == 1 and stage[0].rstrip().endswith("mode=presplit"), stage


@pytest.mark.asyncio
@pytest.mark.parametrize("flag, query", [("on", "iPhone 15 and Galaxy S24"),
                                         ("on", " vs Galaxy S24"),
                                         ("off", "iPhone 15 vs Galaxy S24")],
                         ids=["on_no_vs", "on_empty_half", "off"])
async def test_T17_presplit_falls_through_to_the_llm_parse(svc, monkeypatch, parse_flags_off, flag,
                                                           query):
    """T17 (FS-R3 i): a query without " vs " (or with an empty half) under the flag, and ANY
    query with the flag OFF, take today's LLM parse: one parse_product_query call, the stub's
    tuple returned unchanged (no presplit key). RED at main: AttributeError."""
    if flag == "on":
        monkeypatch.setenv("ENABLE_PARSE_PRESPLIT", "true")
    stub = _slow_parse(0.01, (LLM_PARSED, LLM_USAGE))
    monkeypatch.setattr(scs, "parse_product_query", stub)
    parsed, usage = await svc._parse_with_budget(query)
    assert stub.calls == [query], stub.calls
    assert (parsed, usage) == (LLM_PARSED, LLM_USAGE), (parsed, usage)


def _install_presplit_pipeline(svc, monkeypatch):
    """The REST / stream Step-1 driver: the LLM parse is a recorder, _resolve_pair_category
    records its products and parser_path, _fetch_product_data seeds the early buffer and
    hangs so the 0.5 s cap (scs:3641) builds a partial from the early buffer."""
    monkeypatch.setattr(scs, "STREAM_HARD_CAP_SECONDS", 0.5)
    llm = _slow_parse(0.01, (LLM_PARSED, LLM_USAGE))
    monkeypatch.setattr(scs, "parse_product_query", llm)
    resolved = []

    async def _resolve(products, selected_category, parser_path=False):
        resolved.append(([dict(p) for p in products], parser_path))
        return ("electronics", False, None)

    monkeypatch.setattr(scs, "_resolve_pair_category", _resolve)

    async def _fetch(product_info, region, include_specs, include_reviews, nocache=False,
                     partial_slot=None):
        if partial_slot is not None and isinstance(svc._early_specs_buffer, list):
            svc._early_specs_buffer[partial_slot] = {
                "brand": "", "name": product_info["name"], "full_name": product_info["name"],
                "category": "electronics", "specs": {"display": "6.1 in"}, "price": None,
            }
        await asyncio.sleep(30)

    monkeypatch.setattr(svc, "_fetch_product_data", _fetch)
    return llm, resolved


@pytest.mark.asyncio
async def test_T17_presplit_rest_entry_parser_path_false_and_metadata(svc, monkeypatch,
                                                                      parse_flags_off):
    """T17 (FS-R3 i, m1, m9) through compare_from_text: the pre-split path hands
    _resolve_pair_category the explicit-shaped products with parser_path=False (so A2b may
    escalate exactly as on the app path, scs:485), makes zero LLM calls, and the partial
    built at the cap carries metadata.parse_presplit True. RED at main: the orchestrator
    calls parse_product_query (:3848) and passes parser_path=True (:3866)."""
    monkeypatch.setenv("ENABLE_PARSE_PRESPLIT", "true")
    llm, resolved = _install_presplit_pipeline(svc, monkeypatch)
    body = await svc.compare_from_text("iPhone 15 vs Galaxy S24", nocache=True)
    assert llm.calls == [], (
        "FS-R3: presplit ON must make zero LLM calls; parse_product_query saw %r" % (llm.calls,))
    assert len(resolved) == 1, resolved
    products, parser_path = resolved[0]
    assert parser_path is False, "m1: parser_path must be False on the pre-split path"
    _assert_explicit_shape(products, ("iPhone 15", "Galaxy S24"))
    assert body.get("success") is True, body
    metadata = body.get("metadata") or {}
    assert metadata.get("partial") is True, metadata
    assert metadata.get("parse_presplit") is True, (
        "m9: metadata.parse_presplit missing on the partial: %r" % (metadata,))


@pytest.mark.asyncio
async def test_T17_presplit_stream_entry_takes_the_same_path(svc, monkeypatch, parse_flags_off):
    """T17 (FS-R3 i, n4) through compare_from_text_streaming: the stream entry (:4462) takes
    the same pre-split path -- zero LLM calls, parser_path False, the explicit shape.
    RED at main: the stream calls parse_product_query and passes parser_path=True."""
    monkeypatch.setenv("ENABLE_PARSE_PRESPLIT", "true")
    llm, resolved = _install_presplit_pipeline(svc, monkeypatch)
    gen = svc.compare_from_text_streaming("iPhone 15 vs Galaxy S24", nocache=True)
    events = []
    try:
        async for event in gen:
            events.append(event)
            if resolved or len(events) > 40:
                break
    finally:
        await gen.aclose()
    assert llm.calls == [], (
        "FS-R3: the stream pre-split must make zero LLM calls; saw %r" % (llm.calls,))
    assert len(resolved) == 1, (resolved, [e[0] for e in events])
    products, parser_path = resolved[0]
    assert parser_path is False
    _assert_explicit_shape(products, ("iPhone 15", "Galaxy S24"))


# ===========================================================================
# T18 -- FS-R4 the Phase-2 residual guard
# ===========================================================================
def _seed_partial(svc, result):
    svc._partial_build_ctx = {"query": "A vs B", "region": "bahrain", "from_cache": False,
                              "user_preferences": None, "category_used": "fragrances",
                              "category_switched": False, "original_category": None}
    svc._partial_product_data = [result, dict(result, name="Rasasi Hawas",
                                              full_name="Rasasi Hawas")]
    svc._partial_scoring_result = None
    svc._partial_comparison = None
    svc._partial_product_names = None
    svc._shopping_items_cache = {}


@pytest.mark.asyncio
@pytest.mark.parametrize("state", ["skip", "runs", "off"])
async def test_T18_phase2_residual_guard(svc, monkeypatch, caplog, state):
    """T18 (FS-R4): the guard reads the compare deadline the entries record on the instance
    (`_compare_deadline`, a time.monotonic() instant like :4325). Flag ON, knob 8.0:
    residual 2.0 s -> Phase 2 (scs:5652-5740, the verified rating + the refill) is SKIPPED,
    ONE INFO `[L2.6] phase 2 skipped residual=<s>s product=<n>` and the partial builder
    writes metadata.phase2_skipped True; residual 100 s -> Phase 2 runs, no line, no key.
    Flag OFF -> Phase 2 runs and the deadline is never read (a reading stand-in raises).
    The residual is set relative to the real clock with wide margins instead of a fake
    clock. RED at main: Phase 2 always runs (the rating stub is called)."""
    ratings, specs_seen = [], []
    if state == "off":
        monkeypatch.delenv("ENABLE_PHASE2_RESIDUAL_GUARD", raising=False)
        monkeypatch.setenv("PHASE2_MIN_RESIDUAL_SECONDS", "8")
        svc._compare_deadline = _NoRead()
    else:
        monkeypatch.setenv("ENABLE_PHASE2_RESIDUAL_GUARD", "true")
        monkeypatch.setenv("PHASE2_MIN_RESIDUAL_SECONDS", "8")
        svc._compare_deadline = time.monotonic() + (2.0 if state == "skip" else 100.0)

    async def _search(*args, **kwargs):
        return {"organic": [], "shopping": []}

    caplog.set_level(logging.INFO, logger=SCS_LOGGER)
    with _phase_mocks(svc, search_web_impl=_search, specs_seen=specs_seen, ratings=ratings):
        result = await asyncio.wait_for(
            svc._fetch_product_data(dict(PRODUCT), "bahrain", True, True, nocache=True),
            timeout=20.0)
    skipped = _records(caplog, prefix="[L2.6] phase 2 skipped")
    _seed_partial(svc, result)
    response = svc._build_partial_response(elapsed_seconds=1.0)
    metadata = response.get("metadata") or {}
    if state == "skip":
        assert ratings == [], (
            "FS-R4: Phase 2 ran (the rating was fetched) with a 2.0 s residual below the 8.0 s "
            "knob and the flag ON")
        assert len(skipped) == 1, skipped
        assert re.match(r"^\[L2\.6\] phase 2 skipped residual=-?\d+\.\ds product=\d+", skipped[0]), (
            skipped[0])
        assert metadata.get("phase2_skipped") is True, metadata
    else:
        assert len(ratings) == 1, ratings
        assert skipped == [], skipped
        assert metadata.get("phase2_skipped") is not True, metadata
        if state == "off":
            assert "phase2_skipped" not in metadata, metadata


@pytest.mark.parametrize("raw, want", list(zip(GARBAGE, [8.0] * len(GARBAGE))) + [("3.5", 3.5)],
                         ids=GARBAGE_IDS + ["3.5"])
def test_T18_phase2_residual_knob_hygiene(monkeypatch, raw, want):
    """T18 (FS-R4 knob hygiene): PHASE2_MIN_RESIDUAL_SECONDS garbage / unset -> 8.0; "3.5" ->
    3.5. RED at main: scs has no _phase2_min_residual_seconds (AttributeError)."""
    _set_or_del(monkeypatch, "PHASE2_MIN_RESIDUAL_SECONDS", raw)
    assert scs._phase2_min_residual_seconds() == want


# ===========================================================================
# T19 -- FS-R10 the third resolver path (PINs, green at main)
# ===========================================================================
def test_T19_pin_ssrf_guard_off_never_submits_to_the_default_executor(monkeypatch):
    """T19 PIN (FS-R10 / M6): with ENABLE_OFFLOOP_DNS_RESOLVE unset,
    _validate_url_offloop_or_sync (url_validator.py:526-537) resolves synchronously ON THE LOOP
    -- never through the loop's default executor (the qaren-worker pool), never through libuv.
    Loopback literal, no network."""
    from app.utils import url_validator
    monkeypatch.delenv("ENABLE_OFFLOOP_DNS_RESOLVE", raising=False)
    recorder = _RecordingExecutor(max_workers=2, thread_name_prefix="t19-recorder")

    async def go(loop):
        return await url_validator._validate_url_offloop_or_sync("http://127.0.0.9/p")

    verdict = _run_with_default_executor(go, recorder)
    assert verdict is False, "a loopback literal must stay blocked by the SSRF guard"
    assert recorder.submits == [], (
        "FS-R10: the flag-OFF resolve must not touch the default executor: %r" % (recorder.submits,))


def test_T19_pin_ssrf_guard_on_submits_to_the_dns_pool_only(monkeypatch):
    """T19 PIN (FS-R10 / M6): with the flag ON the resolve is ONE submit to the dedicated
    url_validator._DNS_POOL (the `dns-resolve` pool) and none to the default executor."""
    from app.utils import url_validator
    monkeypatch.setenv("ENABLE_OFFLOOP_DNS_RESOLVE", "true")
    url_validator._DNS_MEMO.clear()
    pool = url_validator._dns_pool()
    real_submit = pool.submit
    pool_submits = []

    def recording_submit(fn, *args, **kwargs):
        pool_submits.append(getattr(fn, "__name__", repr(fn)))
        return real_submit(fn, *args, **kwargs)

    monkeypatch.setattr(pool, "submit", recording_submit)
    recorder = _RecordingExecutor(max_workers=2, thread_name_prefix="t19-recorder")

    async def go(loop):
        return await url_validator._validate_url_offloop_or_sync("http://127.0.0.9/p")

    verdict = _run_with_default_executor(go, recorder)
    url_validator._DNS_MEMO.clear()
    assert verdict is False
    assert recorder.submits == [], recorder.submits
    assert len(pool_submits) == 1, pool_submits
    assert url_validator._DNS_POOL is pool


# ===========================================================================
# FIX ROUND (post-adversary rulings FY1-FY25, 2026-10-09). Every node below is new; each
# names the ruling it serves and the mutant it kills. Promoted probe nodes keep the
# adversary's / GREEN's body with the notes-folder `t.` prefix dropped.
# ===========================================================================
UNIT_KEYS = ("parse_presplit", "parse_fallback", "phase2_skipped")
FLAG_NAMES = ("ENABLE_PARSE_PRESPLIT", "ENABLE_PARSE_BUDGET", "ENABLE_PHASE2_RESIDUAL_GUARD",
              "ENABLE_UNIFIED_SEARCH_BOUND")


def _flags_off(monkeypatch):
    for name in FLAG_NAMES:
        monkeypatch.delenv(name, raising=False)


def _hostile(mark):
    parsed = dict(LLM_PARSED)
    if mark is not None:
        parsed[mark] = True
    return parsed


async def _stream_to_complete(gen, limit=60):
    """Drive a compare stream to its terminal `complete` event (or give up after `limit`)."""
    terminal = None
    events = 0
    try:
        async for kind, payload in gen:
            events += 1
            if kind == "complete" or events > limit:
                terminal = (kind, payload)
                break
    finally:
        await gen.aclose()
    return terminal


# --- FY3: the `_parse_*` marks are the seam's own, never the LLM's ---------------------------
@pytest.mark.asyncio
@pytest.mark.parametrize("mark", ["_parse_presplit", "_parse_fallback"])
@pytest.mark.parametrize("branch", ["bare", "budget"])
async def test_FY3_seam_strips_an_llm_supplied_parse_mark(svc, monkeypatch, parse_flags_off,
                                                         branch, mark):
    """FY3 (strip): an LLM parse whose JSON carries a `_parse_*` key returns WITHOUT it, on the
    bare await (every flag OFF) and on the stall guard's wait_for branch (ENABLE_PARSE_BUDGET
    on, the parse inside its budget). Kills the strip-removed mutant on either branch.
    RED on the GREEN bytes: the dict passed through unchanged."""
    if branch == "budget":
        monkeypatch.setenv("ENABLE_PARSE_BUDGET", "true")
        monkeypatch.setenv("PARSE_TIMEOUT_SECONDS", "5")
    stub = _slow_parse(0.01, (_hostile(mark), LLM_USAGE))
    monkeypatch.setattr(scs, "parse_product_query", stub)
    parsed, usage = await svc._parse_with_budget("Zorblax Q17 and Fimbulwinter R3")
    assert stub.calls == ["Zorblax Q17 and Fimbulwinter R3"], stub.calls
    leaked = sorted(k for k in parsed if str(k).startswith("_parse_"))
    assert leaked == [], "FY3: the seam returned the LLM's own mark(s) %r" % (leaked,)
    assert parsed == LLM_PARSED and usage == LLM_USAGE, (parsed, usage)


@pytest.mark.parametrize("mark, flag, other", [
    ("_parse_presplit", "ENABLE_PARSE_PRESPLIT", "ENABLE_PARSE_BUDGET"),
    ("_parse_fallback", "ENABLE_PARSE_BUDGET", "ENABLE_PARSE_PRESPLIT"),
], ids=["presplit", "fallback"])
def test_FY3_parse_marks_honour_a_mark_only_under_its_own_flag(monkeypatch, mark, flag, other):
    """FY3 (belt and braces): `_parse_marks` honours `_parse_presplit` only while
    ENABLE_PARSE_PRESPLIT is on and `_parse_fallback` only while ENABLE_PARSE_BUDGET is on,
    both read per call; the OTHER flag never opens it. Kills the flag-gate-removed mutant.
    RED on the GREEN bytes: the mark was honoured with every flag OFF."""
    _flags_off(monkeypatch)
    key = mark[1:]
    assert scs._parse_marks({mark: True}) == {}, "FY3: a mark honoured with every flag OFF"
    monkeypatch.setenv(other, "true")
    assert scs._parse_marks({mark: True}) == {}, "FY3: a mark honoured under the OTHER flag"
    monkeypatch.setenv(flag, "true")
    assert scs._parse_marks({mark: True}) == {key: True}
    assert scs._parse_marks({mark: "true"}) == {}, "only the literal True is a mark"


# --- FY3 + FY12: flag-OFF compare bytes carry none of the unit keys (REST and stream) ---------
@pytest.mark.asyncio
@pytest.mark.parametrize("mark", [None, "_parse_presplit", "_parse_fallback"],
                         ids=["honest", "llm_presplit_mark", "llm_fallback_mark"])
@pytest.mark.parametrize("entry", ["rest", "stream"])
async def test_FY12_flags_off_partial_has_no_unit_keys(svc, monkeypatch, parse_flags_off, entry,
                                                       mark):
    """FY12 (ENG-M3) + FY3 (a)/(b), REST and stream: with every flag OFF the partial built at
    the cap carries NONE of parse_presplit / parse_fallback / phase2_skipped, parser_path is
    True and the parse cost is tracked -- also when the LLM's own JSON carries a mark.
    `honest` kills C09 (the stamp writing `ctx.get(key) is True`, i.e. False keys on every
    response); the mark rows were RED on the GREEN bytes (adv_defects.py / ident_probe.py)."""
    _flags_off(monkeypatch)
    _llm, resolved = _install_presplit_pipeline(svc, monkeypatch)
    stub = _slow_parse(0.01, (_hostile(mark), LLM_USAGE))
    monkeypatch.setattr(scs, "parse_product_query", stub)
    before = _cost(svc)
    if entry == "rest":
        body = await svc.compare_from_text("iPhone 15 vs Galaxy S24", nocache=True)
    else:
        terminal = await _stream_to_complete(
            svc.compare_from_text_streaming("iPhone 15 vs Galaxy S24", nocache=True))
        assert terminal is not None and terminal[0] == "complete", terminal
        body = terminal[1]
    metadata = body.get("metadata") or {}
    assert metadata.get("partial") is True, metadata
    present = sorted(k for k in UNIT_KEYS if k in metadata)
    assert present == [], "flag-OFF response carries %r" % (present,)
    assert resolved and resolved[0][1] is True, "parser_path flipped with every flag OFF"
    assert _cost(svc)[0] == before[0] + 1, "FY3: the LLM parse cost was not tracked"


@pytest.mark.asyncio
@pytest.mark.parametrize("entry", ["rest", "stream"])
async def test_FY3_presplit_on_llm_mark_on_an_unsplit_query_is_not_honoured(
        svc, monkeypatch, parse_flags_off, entry):
    """FY3, flag ON: ENABLE_PARSE_PRESPLIT on, a query the pre-split leaves to the LLM, and an
    LLM JSON carrying `_parse_presplit` -> no metadata.parse_presplit, parser_path True, the
    parse cost tracked (the flag gate alone would let it through: kills the strip mutant at
    the entry)."""
    _flags_off(monkeypatch)
    monkeypatch.setenv("ENABLE_PARSE_PRESPLIT", "true")
    _llm, resolved = _install_presplit_pipeline(svc, monkeypatch)
    stub = _slow_parse(0.01, (_hostile("_parse_presplit"), LLM_USAGE))
    monkeypatch.setattr(scs, "parse_product_query", stub)
    before = _cost(svc)
    query = "iPhone 15 and Galaxy S24"
    if entry == "rest":
        body = await svc.compare_from_text(query, nocache=True)
    else:
        terminal = await _stream_to_complete(svc.compare_from_text_streaming(query, nocache=True))
        assert terminal is not None and terminal[0] == "complete", terminal
        body = terminal[1]
    assert stub.calls == [query], stub.calls
    metadata = body.get("metadata") or {}
    assert "parse_presplit" not in metadata, metadata
    assert resolved and resolved[0][1] is True, resolved
    assert _cost(svc)[0] == before[0] + 1


# --- FY4 (GREEN probe_entries.py, promoted) ---------------------------------------------------
def _wrap_fetch(s, monkeypatch):
    inner = s._fetch_product_data
    seen = []

    async def _fetch(*args, **kwargs):
        deadline = s._compare_deadline
        seen.append((None if deadline is None else deadline - time.monotonic(), _cost(s)))
        return await inner(*args, **kwargs)

    monkeypatch.setattr(s, "_fetch_product_data", _fetch)
    return seen


@pytest.mark.asyncio
@pytest.mark.parametrize("presplit", ["on", "off"])
async def test_FY4_rest_entry_records_the_deadline_and_skips_the_presplit_cost(
        svc, monkeypatch, parse_flags_off, presplit):
    """FY4 (M33b REST deadline, M32b REST call-site cost skip): the REST entry records
    `_compare_deadline` on the monotonic clock before any product fetch, and the pre-split
    path tracks NO GPT cost at the call site (the LLM path tracks one)."""
    if presplit == "on":
        monkeypatch.setenv("ENABLE_PARSE_PRESPLIT", "true")
    llm, _resolved = _install_presplit_pipeline(svc, monkeypatch)
    seen = _wrap_fetch(svc, monkeypatch)
    before = _cost(svc)
    await svc.compare_from_text("iPhone 15 vs Galaxy S24", nocache=True)
    assert seen, "no product fetch was reached"
    residual, cost_at_fetch = seen[0]
    assert residual is not None and 0.0 < residual <= 0.5, residual
    if presplit == "on":
        assert llm.calls == [] and cost_at_fetch == before, (before, cost_at_fetch)
    else:
        assert len(llm.calls) == 1 and cost_at_fetch[0] == before[0] + 1, (before, cost_at_fetch)


@pytest.mark.asyncio
async def test_FY4_rest_entry_resets_phase2_skipped(svc, monkeypatch, parse_flags_off):
    """FY4 (M35): a stale `_phase2_skipped` from an earlier run of the instance never reaches
    the REST partial: the entry resets it per run."""
    _install_presplit_pipeline(svc, monkeypatch)
    svc._phase2_skipped = True
    body = await svc.compare_from_text("iPhone 15 vs Galaxy S24", nocache=True)
    metadata = body.get("metadata") or {}
    assert metadata.get("partial") is True, metadata
    assert "phase2_skipped" not in metadata, metadata


@pytest.mark.asyncio
async def test_FY4_stream_partial_carries_the_presplit_mark_and_resets_phase2(
        svc, monkeypatch, parse_flags_off):
    """FY4 (M36 stream ctx marks + the stream per-run reset): the stream partial carries
    metadata.parse_presplit under the flag and never a stale phase2_skipped."""
    monkeypatch.setenv("ENABLE_PARSE_PRESPLIT", "true")
    _install_presplit_pipeline(svc, monkeypatch)
    svc._phase2_skipped = True
    terminal = await _stream_to_complete(
        svc.compare_from_text_streaming("iPhone 15 vs Galaxy S24", nocache=True))
    assert terminal is not None and terminal[0] == "complete", terminal
    metadata = terminal[1].get("metadata") or {}
    assert metadata.get("partial") is True, metadata
    assert metadata.get("parse_presplit") is True, metadata
    assert "phase2_skipped" not in metadata, metadata


@pytest.mark.asyncio
@pytest.mark.parametrize("presplit", ["on", "off"])
async def test_FY4_stream_entry_records_the_deadline_and_skips_the_presplit_cost(
        svc, monkeypatch, parse_flags_off, presplit):
    """FY4 (stream deadline + the stream call-site cost skip)."""
    if presplit == "on":
        monkeypatch.setenv("ENABLE_PARSE_PRESPLIT", "true")
    llm, _resolved = _install_presplit_pipeline(svc, monkeypatch)
    seen = _wrap_fetch(svc, monkeypatch)
    before = _cost(svc)
    gen = svc.compare_from_text_streaming("iPhone 15 vs Galaxy S24", nocache=True)
    events = 0
    try:
        async for _event in gen:
            events += 1
            if seen or events > 40:
                break
    finally:
        await gen.aclose()
    assert seen, "no product fetch was reached on the stream"
    residual, cost_at_fetch = seen[0]
    assert residual is not None and 0.0 < residual <= 0.5, residual
    if presplit == "on":
        assert llm.calls == [] and cost_at_fetch == before, (before, cost_at_fetch)
    else:
        assert len(llm.calls) == 1 and cost_at_fetch[0] == before[0] + 1, (before, cost_at_fetch)


def test_FY4_boot_line_reports_the_uv_threadpool_value_when_set(monkeypatch, caplog):
    """FY4 (M47, GREEN probe_t6_t12.py promoted): the value branch of the `[loop]` line --
    UV_THREADPOOL_SIZE=64 in the env -> the line ends `UV_THREADPOOL_SIZE=64`."""
    from fastapi.testclient import TestClient
    monkeypatch.setenv("UV_THREADPOOL_SIZE", "64")
    caplog.set_level(logging.INFO)
    with TestClient(app.main.app):
        pass
    lines = _records(caplog, prefix="[loop] ")
    assert len(lines) == 1 and lines[0].endswith("UV_THREADPOOL_SIZE=64"), lines


# --- FY13 (ENG-M4): the stall-guard fallback at the REST entry, the REST deadline clock -------
@pytest.mark.asyncio
async def test_FY13_fallback_rest_entry_parser_path_false_and_metadata(svc, monkeypatch,
                                                                       parse_flags_off):
    """FY13 (C05): ENABLE_PARSE_BUDGET on, the LLM parse stalls past the knob -> the REST
    entry hands _resolve_pair_category the explicit shape with parser_path False, the partial
    carries metadata.parse_fallback (and no parse_presplit), and no parse cost is tracked."""
    monkeypatch.setenv("ENABLE_PARSE_BUDGET", "true")
    monkeypatch.setenv("PARSE_TIMEOUT_SECONDS", "0.05")
    _llm, resolved = _install_presplit_pipeline(svc, monkeypatch)
    slow = _slow_parse(5.0, (LLM_PARSED, LLM_USAGE))
    monkeypatch.setattr(scs, "parse_product_query", slow)
    before = _cost(svc)
    body = await svc.compare_from_text("iPhone 15 vs Galaxy S24", nocache=True)
    assert len(slow.calls) == 1, slow.calls
    assert len(resolved) == 1, resolved
    products, parser_path = resolved[0]
    assert parser_path is False, "the stall-guard fallback must take the explicit path"
    _assert_explicit_shape(products, ("iPhone 15", "Galaxy S24"))
    metadata = body.get("metadata") or {}
    assert metadata.get("partial") is True, metadata
    assert metadata.get("parse_fallback") is True, metadata
    assert "parse_presplit" not in metadata, metadata
    assert _cost(svc)[0] == before[0], (before, _cost(svc))


@pytest.mark.asyncio
async def test_FY13_rest_deadline_on_the_monotonic_clock(svc, monkeypatch, parse_flags_off):
    """FY13 (C08b): the REST entry records `_compare_deadline` on time.monotonic() (a
    time.time() deadline would sit ~1.7e9 s away and the residual guard could never fire)."""
    _install_presplit_pipeline(svc, monkeypatch)
    inner = svc._fetch_product_data
    seen = []

    async def _fetch(*args, **kwargs):
        seen.append(svc._compare_deadline - time.monotonic())
        return await inner(*args, **kwargs)

    monkeypatch.setattr(svc, "_fetch_product_data", _fetch)
    await svc.compare_from_text("iPhone 15 vs Galaxy S24", nocache=True)
    assert seen and 0.0 < seen[0] <= 0.5, seen


# --- FY14 (ENG-m1) + FY20: the pre-split edges --------------------------------------------------
@pytest.mark.asyncio
@pytest.mark.parametrize("query", ["Canvas Tote and Leather Bag", "iPhone15vsGalaxyS24",
                                   "Tote vs.Leather Bag"], ids=["canvas", "nospace", "vsdot"])
async def test_FY14_presplit_needs_a_spaced_vs(svc, monkeypatch, parse_flags_off, query):
    """FY14 (C03): only a spaced " vs " splits; anything else takes the LLM parse."""
    monkeypatch.setenv("ENABLE_PARSE_PRESPLIT", "true")
    stub = _slow_parse(0.01, (LLM_PARSED, LLM_USAGE))
    monkeypatch.setattr(scs, "parse_product_query", stub)
    parsed, usage = await svc._parse_with_budget(query)
    assert stub.calls == [query], stub.calls
    assert (parsed, usage) == (LLM_PARSED, LLM_USAGE)


@pytest.mark.asyncio
async def test_FY14_presplit_half_that_sanitizes_to_empty_falls_through(svc, monkeypatch,
                                                                        parse_flags_off):
    """FY14 (C04): a half that sanitize_prompt_input empties never splits."""
    monkeypatch.setenv("ENABLE_PARSE_PRESPLIT", "true")
    stub = _slow_parse(0.01, (LLM_PARSED, LLM_USAGE))
    monkeypatch.setattr(scs, "parse_product_query", stub)
    query = chr(1) + chr(2) + " vs Galaxy S24"
    parsed, usage = await svc._parse_with_budget(query)
    assert stub.calls == [query], stub.calls
    assert (parsed, usage) == (LLM_PARSED, LLM_USAGE)


@pytest.mark.asyncio
@pytest.mark.parametrize("query", ["Alpha One vs Beta Two vs Gamma Three",
                                   "Alpha One VS Beta Two vs Gamma Three",
                                   "Alpha One vs Beta Two VS Gamma Three"],  # AF-m1: the SECOND separator upper-case
                         ids=["lower", "mixed_case", "upper_second"])
async def test_FY20_three_way_query_goes_to_the_llm(svc, monkeypatch, parse_flags_off, query):
    """FY20 (runtime-truth m1): a query whose halves would still contain " vs "
    (case-insensitive) is not pre-split -- three-way strings go to the LLM parse.
    RED on the GREEN bytes: ("Alpha One", "Beta Two vs Gamma Three") was pre-split."""
    monkeypatch.setenv("ENABLE_PARSE_PRESPLIT", "true")
    stub = _slow_parse(0.01, (LLM_PARSED, LLM_USAGE))
    monkeypatch.setattr(scs, "parse_product_query", stub)
    parsed, usage = await svc._parse_with_budget(query)
    assert stub.calls == [query], "FY20: a three-way query was pre-split: %r" % (parsed,)
    assert (parsed, usage) == (LLM_PARSED, LLM_USAGE)


@pytest.mark.asyncio
async def test_FY20_three_way_query_under_the_stall_guard_keeps_the_failure_shape(
        svc, monkeypatch, parse_flags_off):
    """FY20, stall-guard side: a stalled parse of a three-way query never builds a two-product
    fallback from "A" and "B vs C"; the products-less parse-failure shape ships instead."""
    monkeypatch.setenv("ENABLE_PARSE_BUDGET", "true")
    monkeypatch.setenv("PARSE_TIMEOUT_SECONDS", "0.05")
    monkeypatch.setattr(scs, "parse_product_query", _slow_parse(5.0, (LLM_PARSED, LLM_USAGE)))
    parsed, usage = await svc._parse_with_budget("Alpha One vs Beta Two vs Gamma Three")
    assert len(parsed.get("products") or []) < 2, parsed
    assert not usage, usage


# --- ENG-n1 (FY15): the stall guard catches the timeout only ----------------------------------
@pytest.mark.asyncio
async def test_FY15_stall_guard_lets_a_non_timeout_error_through(svc, monkeypatch,
                                                                 parse_flags_off):
    """ENG-n1 (C06): the stall guard turns a TIMEOUT into the fallback and nothing else."""
    monkeypatch.setenv("ENABLE_PARSE_BUDGET", "true")

    async def boom(query):
        raise RuntimeError("parse exploded")

    monkeypatch.setattr(scs, "parse_product_query", boom)
    with pytest.raises(RuntimeError):
        await svc._parse_with_budget("iPhone 15 vs Galaxy S24")


# --- FY14 (ENG-m2): the executor snapshot follows the LATEST install --------------------------
def test_FY14_executor_second_install_updates_the_snapshot(monkeypatch):
    """FY14 (A01): a second install_default_executor (another loop, another size) moves the
    snapshot to the NEW pool; the module global never points at a stale pool."""
    from app.utils import executor
    monkeypatch.setattr(executor, "_INSTALLED_POOL", None)
    pools = []
    for size in ("7", "9"):
        monkeypatch.setenv(EXECUTOR_ENV, size)
        loop = asyncio.new_event_loop()
        try:
            pools.append(executor.install_default_executor(loop))
        finally:
            loop.close()
    snap = executor.executor_snapshot()
    for pool in pools:
        pool.shutdown(wait=False)
    assert snap.get("adapter_executor", {}).get("workers") == 9, snap


# --- FY10: Bright Data once per status, the snapshot follows the latest rejection ------------
@pytest.mark.asyncio
async def test_FY10_bd_one_error_per_status(bd_env, monkeypatch, caplog):
    """FY10 (B01): 401, 401, 403, 403 -> exactly two ERROR records, status=401 then
    status=403, each naming BRIGHTDATA_API_KEY."""
    bd = bd_env
    caplog.set_level(logging.DEBUG, logger=BD_LOGGER)
    _bd_client(monkeypatch, bd, 401, BD_BODY)
    await bd.bd_search_web(BD_QUERY)
    await bd.bd_search_web(BD_QUERY)
    _bd_client(monkeypatch, bd, 403, "Forbidden zone")
    await bd.bd_search_web(BD_QUERY)
    await bd.bd_search_web(BD_QUERY)
    errors = _records(caplog, level=logging.ERROR)
    assert len(errors) == 2, errors
    assert "status=401" in errors[0] and "status=403" in errors[1], errors
    assert all("BRIGHTDATA_API_KEY" in e for e in errors), errors


@pytest.mark.asyncio
async def test_FY10_bd_snapshot_tracks_the_latest_auth_status(bd_env, monkeypatch):
    """FY10 (B02, B03): /health's brightdata_auth follows the LATEST 401/403 (after the ERROR
    latch too); a 402 is not an auth rejection and leaves it alone."""
    bd = bd_env
    seen = []
    for status in (401, 403, 401, 402):
        _bd_client(monkeypatch, bd, status, "x")
        await bd.bd_search_web(BD_QUERY)
        seen.append(bd.brightdata_auth_snapshot().get("brightdata_auth", {}).get("last_status"))
    assert seen == [401, 403, 401, 401], seen


# --- FY19: a D5 timeout caches nothing; the honest Serper failure is today's ------------------
@contextmanager
def _d5_cache_mocks(svc, monkeypatch, search_impl):
    """The REAL _fetch_product_data -> the REAL _get_specs and the REAL
    review_service.get_reviews, with nocache False and every storage / network leaf recorded:
    `writes` collects (kind, key) for the specs L1 / L2 and reviews L1 / L2 writes."""
    from app.services import product_data_service as pds
    from app.services import review_service as rs
    writes = []

    async def _none(*_a, **_k):
        return None

    async def _empty(*_a, **_k):
        return {}

    async def _cache_set(key, value, ttl):
        writes.append(("l1", key))

    def _rec(kind):
        def _save(*args, **_k):
            writes.append((kind, args[0] if args else None))
            return _none()
        return _save

    def _set_cached(key, value, ttl=None):
        writes.append(("l1", key))

    async def _extract_specs(brand, name, variant, category, search_context, **_k):
        return {"concentration": "N/A", "volume_ml": 100}, dict(LLM_USAGE)

    async def _extract_reviews(*_a, **_k):
        return {"summary": "steady", "pros": ["lasts"], "cons": ["price"]}, dict(LLM_USAGE)

    async def _tier2(**_k):
        return {"concentration": "EDP"}

    async def _rating(*_a, **_k):
        return {"rating": None, "review_count": None, "rating_verified": False,
                "rating_source": None}

    for name in ("ENABLE_SPEC_CONFIDENCE_CACHE", "ENABLE_SPEC_SPINE",
                 "ENABLE_REVIEW_SOURCE_CONSULT"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(scs, "_cache_get_async", _none)
    monkeypatch.setattr(scs, "_cache_set_async", _cache_set)
    monkeypatch.setattr(scs, "extract_specs", _extract_specs)
    monkeypatch.setattr(scs, "_spine_specs_or_empty", _empty)
    monkeypatch.setattr(scs, "search_web", search_impl)
    monkeypatch.setattr(scs, "tier2_fill_non_negotiables", _tier2)
    monkeypatch.setattr(scs, "tier3_synthesize_non_negotiables", _empty)
    monkeypatch.setattr(scs, "collect_retailer_ratings", lambda *a, **k: [])
    monkeypatch.setattr(scs, "get_product_image_url", AsyncMock(return_value=None))
    monkeypatch.setattr(pds, "get_cached_specs", _none)
    monkeypatch.setattr(pds, "save_specs", _rec("specs_l2"))
    monkeypatch.setattr(pds, "get_cached_reviews", _none)
    monkeypatch.setattr(pds, "save_reviews", _rec("reviews_l2"))
    monkeypatch.setattr(rs, "get_cached", lambda *a, **k: None)
    monkeypatch.setattr(rs, "set_cached", _set_cached)
    monkeypatch.setattr(rs, "extract_reviews", _extract_reviews)
    monkeypatch.setattr(rs, "search_web", search_impl)
    monkeypatch.setattr(rs, "consult_review_sources", AsyncMock(return_value=[]))
    monkeypatch.setattr(rs, "consult_youtube_source", AsyncMock(return_value=None))
    with patch.object(svc, "_get_price", side_effect=_none), \
            patch.object(svc, "_get_verified_rating", side_effect=_rating), \
            patch.object(svc, "_smart_fallback_extract", side_effect=_empty), \
            patch.object(svc, "_track_serper_cost", lambda *a, **k: None):
        yield writes


def _d5_keys():
    specs_key = scs.get_specs_cache_key(PRODUCT["brand"], PRODUCT["name"], PRODUCT["variant"])
    reviews_key = scs.get_reviews_cache_key(PRODUCT["brand"], PRODUCT["name"], PRODUCT["variant"])
    return specs_key, reviews_key


@pytest.mark.asyncio
async def test_FY19_unified_timeout_writes_no_specs_or_reviews_cache(svc, monkeypatch, caplog):
    """FY19 (runtime-truth M1): ENABLE_UNIFIED_SEARCH_BOUND on, a hanging unified search ->
    the timeout payload carries the `_unified_timeout` mark and NO specs L1 / L2 (incl. the
    enriched re-cache) and NO reviews L1 / L2 entry is written, so a rollback (unset) leaves no
    empty-context row behind; the mark reaches neither the response nor a stored row.
    RED on the GREEN bytes: specs L1 (7 d) + save_specs + the reviews writes happened."""
    monkeypatch.setenv("ENABLE_UNIFIED_SEARCH_BOUND", "true")
    monkeypatch.setenv("UNIFIED_SEARCH_TIMEOUT_SECONDS", "0.05")
    searches = []

    async def _hang(*args, **kwargs):
        searches.append(args)
        await asyncio.sleep(30)
        return {"organic": [{"title": "late"}]}

    specs_key, reviews_key = _d5_keys()
    with _d5_cache_mocks(svc, monkeypatch, _hang) as writes:
        result = await asyncio.wait_for(
            svc._fetch_product_data(dict(PRODUCT), "bahrain", True, True, nocache=False),
            timeout=10.0)
        await asyncio.sleep(0.05)
    assert len(searches) == 1, searches
    unit_writes = [w for w in writes if w[1] in (specs_key, reviews_key)]
    assert unit_writes == [], (
        "FY19: a D5 timeout wrote empty-context cache rows %r" % (unit_writes,))
    assert result.get("specs"), result
    assert "_unified_timeout" not in json.dumps(result, default=str), "the mark leaked"


@pytest.mark.asyncio
@pytest.mark.parametrize("flag", ["on", "off"])
async def test_FY19_honest_serper_failure_payload_still_caches(svc, monkeypatch, flag):
    """FY19 GUARD: today's honest Serper-failure payload ({"organic": [], "error": ...},
    answered at once) is untouched in both flag states -- the specs L1 / L2 (and the enriched
    re-cache) and the reviews L1 / L2 writes all happen as today. Kills a skip keyed on an
    empty organic list instead of the mark."""
    if flag == "on":
        monkeypatch.setenv("ENABLE_UNIFIED_SEARCH_BOUND", "true")
        monkeypatch.setenv("UNIFIED_SEARCH_TIMEOUT_SECONDS", "5")
    else:
        monkeypatch.delenv("ENABLE_UNIFIED_SEARCH_BOUND", raising=False)

    async def _failed(*args, **kwargs):
        return {"organic": [], "error": "serper_unavailable"}

    specs_key, reviews_key = _d5_keys()
    with _d5_cache_mocks(svc, monkeypatch, _failed) as writes:
        await asyncio.wait_for(
            svc._fetch_product_data(dict(PRODUCT), "bahrain", True, True, nocache=False),
            timeout=10.0)
        await asyncio.sleep(0.05)
    kinds = sorted(set((w[0], "specs" if w[1] == specs_key else "reviews")
                       for w in writes if w[1] in (specs_key, reviews_key)))
    assert kinds == [("l1", "reviews"), ("l1", "specs"), ("reviews_l2", "reviews"),
                     ("specs_l2", "specs")], kinds
    specs_l1 = [w for w in writes if w == ("l1", specs_key)]
    assert len(specs_l1) == 2, "want the _get_specs write AND the enriched re-cache: %r" % (
        writes,)
