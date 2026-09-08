"""W1-3 — an OpenAI preflight breaker, so a dead LLM stops costing money.

Findings ``LS-FAILURE-MODES-COST-02`` / ``-03``. Flag
``ENABLE_LLM_PREFLIGHT_BREAKER``, default OFF; flag OFF must be byte-identical.

WHY THIS UNIT EXISTS (measured, not modelled)
---------------------------------------------
Serper is dead by configuration on ``web`` (``SERPER_LIFETIME_LIMIT=0``), so
every search leg routes to Bright Data, which is armed with no budget gate and
no breaker. Meanwhile OpenAI answers 429. The app's only compare shape
(``explicit_pair``) never checks LLM health before dispatching, so every compare
pays the full scrape/render cascade and then fails at the LLM. Money out,
nothing back.

THE CONTRACT THESE TESTS PIN
----------------------------
The template is the Serper breaker at ``serper_service.py:284-320``
(``ENABLE_SERPER_BREAKER``), which already solved the two hard parts. The OpenAI
breaker must mirror it exactly:

  * ``api_budget_service.PROVIDER_CONFIGS`` gains an ``"openai"`` entry — a
    budget row for FUTURE metering, explicitly not part of the breaker mechanism.
  * The breaker state is MEMOISED and the success path costs NOTHING when the
    breaker is closed and clean, so the hot path takes no blocking Redis round
    trip — the event-loop hazard W0 spent four units removing.
  * FAIL-OPEN on any error. If the breaker state cannot be read, DISPATCH. A
    Redis blip must never become "the app refuses every compare".
  * The short-circuit sits at BOTH COMPARE ENTRIES, before the provider fan-out
    — ``compare_from_text`` AND ``compare_from_text_streaming``, which is the
    entry the mobile client actually drives. Placing it at the OpenAI call sites
    saves the LLM call and still pays for all the scraping, which is the entire
    cost being attacked.
  * The compare-entry preflight is READ-ONLY. ``is_circuit_closed`` is not: its
    half-open branch spends the single ``CB_HALF_OPEN_MAX_CALLS`` probe, so
    using it at an entry that may never dispatch an LLM call would leave the
    breaker half-open with its budget spent and NOTHING to record an outcome —
    denying every later compare forever. Pinned by
    ``test_half_open_preflight_never_locks_the_breaker_open``.
  * Flag OFF: no breaker read, no record, every call dispatches, both entries
    reach the fan-out.

The breaker uses the EXISTING abstraction (``api_budget_service.record_failure``
/ ``record_success`` / ``is_circuit_closed``) under the provider key ``openai``.
No new breaker is introduced.

SURFACE ASSUMPTIONS (stated so a reviewer can move them deliberately)
---------------------------------------------------------------------
Behavioural tests go through real call paths (``openai_service`` for the record
half, ``compare_from_text`` / ``compare_from_text_streaming`` for the preflight
half) rather than private helpers, so a RED failure is "the behaviour is absent",
never "the name is absent". The one exception is the MINOR-5 timeout pin, which
drives ``guarded_llm_create`` directly because that IS the named chokepoint.
Fail-open is exercised by making the underlying Redis GET raise, not by patching
a named breaker helper, so the test cannot be satisfied by a rename. Two names
ARE pinned outright because the spec names them: the flag
``ENABLE_LLM_PREFLIGHT_BREAKER`` and the provider key ``"openai"``.

Zero-network: the circuit-breaker Redis is dict-stubbed, every OpenAI client is
a mock, and the Serper / Bright Data / Firecrawl entry points are counting stubs.
"""
import asyncio
import json
import time

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import openai as openai_sdk
from fastapi import HTTPException

from app.api import text_routes as text_routes_mod
from app.services import api_budget_service as abs_mod
from app.services import brightdata_service as bd_mod
from app.services import extraction_service as extraction_mod
from app.services import firecrawl_service as fc_mod
from app.services import openai_service as oai
from app.services import serper_service as ss
from app.services import structured_comparison_service as scs
from app.services import url_extraction_service as url_extraction_mod
from app.services import verdict_critique_service as vc_mod


FLAG = "ENABLE_LLM_PREFLIGHT_BREAKER"
TTL_ENV = "LLM_BREAKER_CACHE_TTL"
PROVIDER = "openai"

# An L1-blocklisted query (app/data/content_blocklist.json, `weapons`). It makes
# a compare return BEFORE any LLM call is dispatched, which is the exact shape
# that turned the half-open probe into a permanent lockout.
L1_BLOCKED_QUERY = "handgun holster vs rifle case"


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------
def _dict_breaker_redis(seed=None):
    """A dict standing in for the circuit-breaker Redis. Returns the store, an
    op counter, and the four cache_service helpers api_budget_service calls.

    The counter is what makes the hot-path cost assertable: every entry in it is
    one BLOCKING Upstash round trip on the async event loop."""
    store = dict(seed or {})
    ops = {"get": 0, "set": 0, "incr": 0, "expire": 0}

    def _get(key):
        ops["get"] += 1
        return store.get(key)

    def _set(key, value, ex=None):
        ops["set"] += 1
        store[key] = value
        return True

    def _incr(key):
        ops["incr"] += 1
        store[key] = str(int(store.get(key, "0")) + 1)
        return int(store[key])

    def _expire(key, ttl):
        ops["expire"] += 1
        return True

    return store, ops, _get, _set, _incr, _expire


def _patch_breaker_redis(get, set_, incr, expire):
    """Context managers for the four api_budget_service Redis helpers."""
    return (
        patch.object(abs_mod, "_redis_get", side_effect=get),
        patch.object(abs_mod, "_redis_set", side_effect=set_),
        patch.object(abs_mod, "_redis_incr", side_effect=incr),
        patch.object(abs_mod, "_redis_expire", side_effect=expire),
    )


def _open_breaker_seed(provider=PROVIDER, tripped_ago=0.0):
    """A breaker blob that reads as OPEN. `tripped_ago=0` is inside the cooldown
    (deny); anything past CB_RECOVERY_TIMEOUT is recovery-eligible."""
    return {
        abs_mod._circuit_key(provider): json.dumps({
            "state": abs_mod.CB_OPEN,
            "failure_count": abs_mod.CB_FAILURE_THRESHOLD,
            "tripped_at": time.time() - tripped_ago,
        })
    }


def _half_open_breaker_seed(provider=PROVIDER):
    """A breaker blob already transitioned to half-open with its probe UNSPENT."""
    return {
        abs_mod._circuit_key(provider): json.dumps({
            "state": abs_mod.CB_HALF_OPEN,
            "failure_count": abs_mod.CB_FAILURE_THRESHOLD,
            "tripped_at": time.time() - (abs_mod.CB_RECOVERY_TIMEOUT + 5),
            "half_open_calls": 0,
        })
    }


def _probe_key_for(store, provider=PROVIDER):
    """The half-open probe counter key for the blob currently in `store`."""
    state = json.loads(store[abs_mod._circuit_key(provider)])
    return abs_mod._half_open_probe_key(provider, state)


def _breaker_blob(store, provider=PROVIDER):
    raw = store.get(abs_mod._circuit_key(provider))
    return json.loads(raw) if raw else None


def _rate_limit_error():
    """A genuine SDK 429 — what a credit-exhausted OpenAI project returns."""
    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    response = httpx.Response(429, request=request)
    return openai_sdk.RateLimitError(
        "rate limit / credit balance exhausted", response=response, body=None
    )


def _mock_openai_client(raises=None, content='{"f": "v"}'):
    """A stand-in AsyncOpenAI whose chat.completions.create is countable."""
    client = MagicMock()
    if raises is not None:
        client.chat.completions.create = AsyncMock(side_effect=raises)
    else:
        message = MagicMock()
        message.content = content
        choice = MagicMock()
        choice.message = message
        resp = MagicMock()
        resp.choices = [choice]
        resp.usage = None
        client.chat.completions.create = AsyncMock(return_value=resp)
    # content_safety L3 goes through client.moderations.create; give it an async
    # stand-in so the compare path never falls back to its fail-open exception
    # branch for a reason unrelated to this unit.
    _flagged = MagicMock()
    _flagged.flagged = False
    _mod_resp = MagicMock()
    _mod_resp.results = [_flagged]
    client.moderations.create = AsyncMock(return_value=_mod_resp)
    return client


def _reset_breaker_memo():
    """Drop the breaker memo between tests. Defensive: the hook does not exist in
    the RED state, and its absence must not be what a behavioural test reports."""
    for module in (oai, scs, abs_mod):
        for name in (
            "_reset_openai_breaker_cache",
            "_reset_llm_breaker_cache",
            "_reset_openai_gate_cache",
        ):
            hook = getattr(module, name, None)
            if callable(hook):
                hook()


@pytest.fixture(autouse=True)
def _clean_breaker_state(monkeypatch):
    monkeypatch.delenv(FLAG, raising=False)
    monkeypatch.delenv(TTL_ENV, raising=False)
    _reset_breaker_memo()
    yield
    _reset_breaker_memo()


def _arm_prod_search_config(monkeypatch):
    """Reproduce the measured prod config from the finding: Serper dead by
    configuration (``SERPER_LIFETIME_LIMIT=0``, no key) so every search leg routes
    to the Bright Data fallback, which is armed with no budget gate. This is what
    makes ``bd_search_web`` genuinely REACHABLE in this harness rather than a
    counter that can only ever read zero."""
    monkeypatch.delenv("SERPER_API_KEY", raising=False)
    monkeypatch.delenv("SERPER_API_KEYS", raising=False)
    monkeypatch.setenv("SERPER_LIFETIME_LIMIT", "0")
    monkeypatch.setenv("ENABLE_BRIGHTDATA_FALLBACK", "true")
    monkeypatch.setenv("BRIGHTDATA_API_KEY", "bd-test-dummy")
    monkeypatch.setenv("BRIGHTDATA_ZONE", "serp_api1")
    monkeypatch.delenv("ENABLE_BRIGHTDATA_BUDGET_GATE", raising=False)


class _FanOutCounters:
    """Counting stubs for every PAID provider entry point a compare can reach
    before the LLM: Serper, the Bright Data fallback Serper's dead config routes
    everything to, and Firecrawl."""

    def __init__(self):
        self.calls = {"search_web": 0, "bd_search_web": 0, "firecrawl": 0}

    async def search_web(self, *args, **kwargs):
        self.calls["search_web"] += 1
        return {"organic": [], "shopping": []}

    async def bd_search_web(self, *args, **kwargs):
        self.calls["bd_search_web"] += 1
        return {"organic": []}

    async def firecrawl(self, *args, **kwargs):
        self.calls["firecrawl"] += 1
        return None

    async def firecrawl_with_status(self, *args, **kwargs):
        self.calls["firecrawl"] += 1
        return None, 0

    def patches(self, llm_client):
        return (
            patch.object(ss, "search_web", side_effect=self.search_web),
            patch.object(scs, "search_web", side_effect=self.search_web),
            patch.object(bd_mod, "bd_search_web", side_effect=self.bd_search_web),
            patch.object(fc_mod, "scrape_page", side_effect=self.firecrawl),
            patch.object(fc_mod, "scrape_page_with_status",
                         side_effect=self.firecrawl_with_status),
            patch.object(oai, "get_client", return_value=llm_client),
            patch.object(extraction_mod, "get_client", return_value=llm_client),
            patch.object(url_extraction_mod, "get_client", return_value=llm_client),
        )

    @property
    def total(self):
        return sum(self.calls.values())


import contextlib  # noqa: E402 — used only by the helper below


@contextlib.contextmanager
def _all(*context_managers):
    """Enter a flat tuple of context managers (keeps the `with` blocks readable
    now that there are ten of them per test)."""
    with contextlib.ExitStack() as stack:
        for cm in context_managers:
            stack.enter_context(cm)
        yield


async def _call_llm():
    """One real LLM call path (``openai_service.extract_specs_targeted``). It
    builds its client through ``get_client()`` and swallows exceptions, so the
    observable is the dispatch count on the mocked client, not the return value."""
    return await oai.extract_specs_targeted(
        brand="Acme",
        name="Widget",
        variant=None,
        category="electronics",
        fields=["weight"],
        context="snippets",
    )


async def _run_compare(query="Acme Widget vs Globex Gadget"):
    service = scs.get_comparison_service()
    return await service.compare_from_text(
        query=query,
        region="bahrain",
        explicit_pair=("Acme Widget", "Globex Gadget"),
    )


async def _run_stream(query="Acme Widget vs Globex Gadget"):
    """Drive the SSE entry the mobile client actually uses and collect its
    events."""
    service = scs.get_comparison_service()
    events = []
    async for event_type, data in service.compare_from_text_streaming(
        query=query,
        region="bahrain",
        explicit_pair=("Acme Widget", "Globex Gadget"),
    ):
        events.append((event_type, data))
    return events


# ---------------------------------------------------------------------------
# Fix 1 — the missing budget row (a CONFIGURATION pin, not a behavioural one)
# ---------------------------------------------------------------------------
def test_openai_has_a_provider_budget_row():
    """CONFIGURATION PIN — deliberately labelled as such (adversarial review
    MINOR 7). It asserts the row EXISTS and is well-formed; it asserts nothing
    about behaviour, because the row has none: the breaker keys off
    `circuit:openai` via `_circuit_key`, which never consults PROVIDER_CONFIGS.
    The row is the budget row the finding asks for, for future metering."""
    assert PROVIDER in abs_mod.PROVIDER_CONFIGS, (
        "no 'openai' entry in PROVIDER_CONFIGS — the provider that gates every "
        "compare's usefulness is the only one with no budget row"
    )
    entry = abs_mod.PROVIDER_CONFIGS[PROVIDER]
    assert isinstance(entry.get("monthly_limit"), int) and entry["monthly_limit"] > 0
    assert isinstance(entry.get("warn_at"), int) and entry["warn_at"] > 0
    assert entry["warn_at"] < entry["monthly_limit"]
    assert isinstance(entry.get("is_lifetime"), bool)


# ---------------------------------------------------------------------------
# Test 1 — three consecutive 429s ⇒ the 4th call short-circuits
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_three_429s_then_fourth_call_short_circuits(monkeypatch):
    """RED: it dispatches. Today nothing records an OpenAI outcome and nothing
    reads a breaker, so a 429 storm dispatches forever."""
    monkeypatch.setenv(FLAG, "true")
    store, ops, _get, _set, _incr, _expire = _dict_breaker_redis()
    client = _mock_openai_client(raises=_rate_limit_error())

    with _all(*_patch_breaker_redis(_get, _set, _incr, _expire),
              patch.object(oai, "get_client", return_value=client)):
        for _ in range(abs_mod.CB_FAILURE_THRESHOLD):
            await _call_llm()
        assert client.chat.completions.create.await_count == abs_mod.CB_FAILURE_THRESHOLD

        await _call_llm()

    assert client.chat.completions.create.await_count == abs_mod.CB_FAILURE_THRESHOLD, (
        "the 4th call dispatched despite three consecutive 429s — no failure was "
        "recorded against the 'openai' breaker, or the breaker is never read"
    )
    assert abs_mod._circuit_key(PROVIDER) in store, (
        "no circuit state was ever written for 'openai'"
    )
    assert _breaker_blob(store)["state"] == abs_mod.CB_OPEN


# ---------------------------------------------------------------------------
# Test 2 — THE LOAD-BEARING ONE: short-circuit BEFORE the provider fan-out
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_explicit_pair_compare_returns_before_provider_fanout(monkeypatch):
    """The whole point of the unit. With the OpenAI breaker OPEN, an explicit-pair
    compare must return the LLM_UNAVAILABLE-class envelope BEFORE any paid
    provider is touched — Serper, the Bright Data fallback that Serper's dead
    config routes everything to, and Firecrawl all record ZERO calls.

    RED: > 0. Today the compare pays the full scrape/render cascade and only then
    fails at the LLM. Flag OFF the identical harness reaches the fan-out 24 times
    (see test_flag_off_compare_never_short_circuits), which is what makes the
    zero here evidence rather than a tautology.
    """
    monkeypatch.setenv(FLAG, "true")
    _arm_prod_search_config(monkeypatch)
    store, ops, _get, _set, _incr, _expire = _dict_breaker_redis(seed=_open_breaker_seed())
    fan = _FanOutCounters()
    llm_client = _mock_openai_client()

    with _all(*_patch_breaker_redis(_get, _set, _incr, _expire),
              *fan.patches(llm_client)):
        result = await _run_compare()

    # THE assertion this unit exists for — asserted FIRST, because "the compare
    # returned an error envelope" is worth nothing if it already paid for the
    # scrape/render cascade to get there.
    assert fan.calls == {"search_web": 0, "bd_search_web": 0, "firecrawl": 0}, (
        f"the compare paid the provider fan-out before failing at the LLM: {fan.calls}"
    )
    assert llm_client.chat.completions.create.await_count == 0

    # The envelope: the existing error SHAPE, carrying an LLM-unavailable code.
    assert isinstance(result, dict)
    assert result.get("success") is False, (
        f"compare returned success={result.get('success')!r} with the OpenAI "
        f"breaker OPEN (code={result.get('code')!r})"
    )
    assert result.get("code") == "LLM_UNAVAILABLE", (
        f"expected an LLM_UNAVAILABLE-class envelope, got code={result.get('code')!r}"
    )
    assert isinstance(result.get("error"), str) and result["error"].strip()

    # The preflight is READ-ONLY: one GET for the state, never a write, never an
    # INCR of the half-open probe counter.
    assert ops["set"] == 0 and ops["incr"] == 0, f"the preflight mutated Redis: {ops}"


# ---------------------------------------------------------------------------
# Test 2b — BLOCKING 1: the SAME pin on the STREAMING entry the app actually uses
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_streaming_explicit_pair_returns_before_provider_fanout(monkeypatch):
    """``GET /api/v1/text/compare/stream`` is the entry the mobile client drives
    (``streamComparison()``); POST /compare is only its fallback. A preflight on
    the non-streaming entry alone would leave the PRIMARY user path paying the
    full Serper / Bright Data / Firecrawl cascade before failing at the LLM — the
    unit's headline saving would not reach the traffic it was written for.

    Same assertion as test 2, on the other entry: zeroed fan-out counters plus
    the LLM_UNAVAILABLE-class error event.
    """
    monkeypatch.setenv(FLAG, "true")
    _arm_prod_search_config(monkeypatch)
    store, ops, _get, _set, _incr, _expire = _dict_breaker_redis(seed=_open_breaker_seed())
    fan = _FanOutCounters()
    llm_client = _mock_openai_client()

    with _all(*_patch_breaker_redis(_get, _set, _incr, _expire),
              *fan.patches(llm_client)):
        events = await _run_stream()

    assert fan.calls == {"search_web": 0, "bd_search_web": 0, "firecrawl": 0}, (
        f"the STREAMING compare paid the provider fan-out before failing at the "
        f"LLM: {fan.calls}"
    )
    assert llm_client.chat.completions.create.await_count == 0

    assert [e for e, _ in events] == ["error"], (
        f"expected exactly one error event before any work, got {[e for e, _ in events]}"
    )
    body = events[0][1]
    assert body.get("success") is False
    assert body.get("code") == "LLM_UNAVAILABLE", (
        f"expected an LLM_UNAVAILABLE-class error event, got code={body.get('code')!r}"
    )
    assert isinstance(body.get("error"), str) and body["error"].strip()
    assert ops["set"] == 0 and ops["incr"] == 0, f"the preflight mutated Redis: {ops}"


# ---------------------------------------------------------------------------
# Test 2c — BLOCKING 2: the permanent-lockout pin
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_half_open_preflight_never_locks_the_breaker_open(monkeypatch):
    """``is_circuit_closed`` is NOT read-only — its half-open branch INCRs the
    probe counter and ``CB_HALF_OPEN_MAX_CALLS`` is 1. A compare-entry preflight
    built on it SPENDS that single probe on a compare that may never dispatch an
    LLM call at all (here: blocked by the L1 content-safety prefilter), after
    which NOTHING records an outcome — so the breaker stays half-open with its
    budget spent and denies every subsequent compare indefinitely. That is
    strictly worse than the problem this unit exists to solve, and it would fire
    the first time anyone flipped the flag.

    The memo is disabled (``LLM_BREAKER_CACHE_TTL=0``) on purpose: with it on,
    the second compare would reuse the first compare's cached verdict and the
    defect would hide behind the cache rather than being pinned.
    """
    monkeypatch.setenv(FLAG, "true")
    monkeypatch.setenv(TTL_ENV, "0")
    _arm_prod_search_config(monkeypatch)
    store, ops, _get, _set, _incr, _expire = _dict_breaker_redis(
        seed=_half_open_breaker_seed()
    )
    probe_key = _probe_key_for(store)
    fan = _FanOutCounters()
    llm_client = _mock_openai_client()

    with _all(*_patch_breaker_redis(_get, _set, _incr, _expire),
              *fan.patches(llm_client)):
        # 1. A compare that returns BEFORE any LLM dispatch.
        blocked = await _run_compare(query=L1_BLOCKED_QUERY)
        assert blocked.get("code") == "CONTENT_UNAVAILABLE", (
            f"the harness did not produce a dispatch-free compare: {blocked!r}"
        )
        assert llm_client.chat.completions.create.await_count == 0
        assert store.get(probe_key) is None, (
            "the compare-entry preflight SPENT the single half-open probe on a "
            f"compare that never dispatched an LLM call (probe={store.get(probe_key)!r})"
        )

        # 2. The very next compare must still be admitted.
        result = await _run_compare()

    assert result.get("code") != "LLM_UNAVAILABLE", (
        "the breaker locked out every later compare after a half-open probe was "
        "spent by a compare that recorded no outcome — permanent lockout"
    )
    assert fan.total > 0, "the second compare never reached the provider fan-out"
    # And the probe was spent where an outcome IS recorded, closing the breaker.
    assert llm_client.chat.completions.create.await_count > 0
    assert store.get(probe_key) == "1", (
        f"expected exactly one probe, spent at the dispatch chokepoint: "
        f"{store.get(probe_key)!r}"
    )
    assert _breaker_blob(store)["state"] == abs_mod.CB_CLOSED, (
        "the successful probe dispatch did not close the breaker"
    )


@pytest.mark.asyncio
async def test_preflight_admits_once_the_open_cooldown_expires(monkeypatch):
    """The other half of the same lockout, and a correction to the ruling's
    letter: ``get_breaker_state`` returns the PERSISTED state and does NOT apply
    the ``CB_RECOVERY_TIMEOUT`` transition — only ``is_circuit_closed`` writes
    that. Verified: a blob tripped long past the cooldown still reads "open"
    forever. So a preflight that denied on a bare ``state == CB_OPEN`` would deny
    forever: it blocks the compare, nothing on the compare path then calls
    ``is_circuit_closed``, the blob is never transitioned, and the preflight
    keeps reading "open". A cooldown-expired OPEN must PROCEED, handing the probe
    to the dispatch chokepoint that transitions and records it."""
    monkeypatch.setenv(FLAG, "true")
    monkeypatch.setenv(TTL_ENV, "0")
    _arm_prod_search_config(monkeypatch)
    store, ops, _get, _set, _incr, _expire = _dict_breaker_redis(
        seed=_open_breaker_seed(tripped_ago=abs_mod.CB_RECOVERY_TIMEOUT + 5)
    )
    fan = _FanOutCounters()
    llm_client = _mock_openai_client()

    # The state string alone still says OPEN — that is the trap being pinned.
    with _all(*_patch_breaker_redis(_get, _set, _incr, _expire)):
        assert abs_mod.get_breaker_state(PROVIDER) == abs_mod.CB_OPEN

    with _all(*_patch_breaker_redis(_get, _set, _incr, _expire),
              *fan.patches(llm_client)):
        result = await _run_compare()

    assert result.get("code") != "LLM_UNAVAILABLE", (
        "a breaker whose cooldown has expired denied the compare — nothing else "
        "on the compare path can transition it, so this denies forever"
    )
    assert fan.total > 0
    assert _breaker_blob(store)["state"] == abs_mod.CB_CLOSED, (
        "the recovery probe never reached a dispatch that could record an outcome"
    )


# ---------------------------------------------------------------------------
# Test 3 — FAIL-OPEN pins (exercised through an unreadable Redis, not a
# patched-out helper name)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_breaker_read_raising_still_dispatches(monkeypatch):
    """A Redis blip must never become 'the app refuses every compare'. If the
    breaker state cannot be read, DISPATCH."""
    monkeypatch.setenv(FLAG, "true")
    store, ops, _get, _set, _incr, _expire = _dict_breaker_redis()
    client = _mock_openai_client()

    def _boom(key):
        raise RuntimeError("upstash unreachable")

    with _all(*_patch_breaker_redis(_boom, _set, _incr, _expire),
              patch.object(oai, "get_client", return_value=client)):
        await _call_llm()

    assert client.chat.completions.create.await_count == 1, (
        "an unreadable breaker blocked the call — the breaker must FAIL OPEN"
    )
    assert store == {}, f"an unreadable breaker still wrote state: {store}"


@pytest.mark.asyncio
async def test_breaker_read_raising_still_runs_the_compare(monkeypatch):
    """Fail-open at the compare entry too. Asserts the compare actually SUCCEEDED
    and actually reached the fan-out — `code != LLM_UNAVAILABLE` alone would pass
    on a compare that failed for any unrelated reason (adversarial review)."""
    monkeypatch.setenv(FLAG, "true")
    _arm_prod_search_config(monkeypatch)
    store, ops, _get, _set, _incr, _expire = _dict_breaker_redis(seed=_open_breaker_seed())
    fan = _FanOutCounters()
    llm_client = _mock_openai_client()

    def _boom(key):
        raise RuntimeError("upstash unreachable")

    with _all(*_patch_breaker_redis(_boom, _set, _incr, _expire),
              *fan.patches(llm_client)):
        result = await _run_compare()

    assert result.get("success") is True, (
        f"an unreadable breaker degraded the compare (code={result.get('code')!r}) "
        "— it must FAIL OPEN and behave exactly as it does with no breaker at all"
    )
    assert result.get("code") != "LLM_UNAVAILABLE"
    assert fan.total > 0, "the compare never reached the provider fan-out"
    assert llm_client.chat.completions.create.await_count > 0


@pytest.mark.asyncio
async def test_streaming_breaker_read_raising_still_runs_the_compare(monkeypatch):
    """Same fail-open pin on the streaming entry: an unreadable breaker must not
    turn the primary user path into an error event."""
    monkeypatch.setenv(FLAG, "true")
    _arm_prod_search_config(monkeypatch)
    store, ops, _get, _set, _incr, _expire = _dict_breaker_redis(seed=_open_breaker_seed())
    fan = _FanOutCounters()
    llm_client = _mock_openai_client()

    def _boom(key):
        raise RuntimeError("upstash unreachable")

    with _all(*_patch_breaker_redis(_boom, _set, _incr, _expire),
              *fan.patches(llm_client)):
        events = await _run_stream()

    codes = [d.get("code") for e, d in events if e == "error"]
    assert "LLM_UNAVAILABLE" not in codes, (
        "an unreadable breaker short-circuited the stream — it must FAIL OPEN"
    )
    assert fan.total > 0, "the stream never reached the provider fan-out"


# ---------------------------------------------------------------------------
# Test 4 — the hot path costs (almost) nothing: MEMOISED READ *and* no
# un-memoised success writes
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_flag_on_hot_path_adds_no_per_call_redis_round_trips(monkeypatch):
    """"No per-call blocking Redis round trip on the async hot path" was named
    non-negotiable in the spec, and the first implementation only memoised the
    READ: `record_success` still fired un-memoised on every successful dispatch,
    which measured 12 -> 24 blocking GETs on one identical compare (adversarial
    review MAJOR 3). This counts ALL FOUR Redis verbs, not just the read.

    A closed breaker learning it is still closed is not information."""
    monkeypatch.setenv(FLAG, "true")
    store, ops, _get, _set, _incr, _expire = _dict_breaker_redis()
    ok_client = _mock_openai_client()

    with _all(*_patch_breaker_redis(_get, _set, _incr, _expire),
              patch.object(oai, "get_client", return_value=ok_client)):
        # A. Five successful dispatches in one memo window == ONE Redis op total.
        for _ in range(5):
            await _call_llm()
        assert ops == {"get": 1, "set": 0, "incr": 0, "expire": 0}, (
            f"5 successful dispatches cost {ops} blocking Redis round trips on "
            "the event loop; the contract is one memoised read and no writes"
        )

        # B. A recorded FAILURE must both write and drop the memo.
        failing_client = _mock_openai_client(raises=_rate_limit_error())
        with patch.object(oai, "get_client", return_value=failing_client):
            await _call_llm()
        assert ops["set"] == 1, "the failure was not recorded"
        after_failure = dict(ops)

        # C. The next call re-reads (memo dropped) and, because a failure streak
        #    now stands, its success IS recorded — that is what resets the streak.
        await _call_llm()
        assert ops["get"] == after_failure["get"] + 2, (
            "a recorded failure did not invalidate the breaker memo — a trip "
            f"would not engage until the memo window expired (ops={ops})"
        )
        assert ops["set"] == after_failure["set"] + 1, (
            "the success that follows a failure streak was not recorded, so the "
            "streak would never reset and unrelated failures would trip the breaker"
        )
        assert json.loads(store[abs_mod._circuit_key(PROVIDER)])["failure_count"] == 0
        settled = dict(ops)

        # D. Back on the quiet path: free again.
        for _ in range(4):
            await _call_llm()
        assert ops == settled, (
            f"the hot path started paying Redis again after recovery: {ops} vs {settled}"
        )


# ---------------------------------------------------------------------------
# Test 5 — flag OFF is byte-identical
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_flag_off_never_reads_or_records_and_always_dispatches(monkeypatch):
    """Flag OFF: no breaker read, no record, every call dispatches."""
    monkeypatch.delenv(FLAG, raising=False)
    store, ops, _get, _set, _incr, _expire = _dict_breaker_redis()
    client = _mock_openai_client(raises=_rate_limit_error())

    seen = {"closed": 0, "fail": 0, "success": 0}

    def _closed(provider):
        if provider == PROVIDER:
            seen["closed"] += 1
        return True

    def _fail(provider):
        if provider == PROVIDER:
            seen["fail"] += 1

    def _success(provider):
        if provider == PROVIDER:
            seen["success"] += 1

    with _all(*_patch_breaker_redis(_get, _set, _incr, _expire),
              patch.object(abs_mod, "is_circuit_closed", side_effect=_closed),
              patch.object(abs_mod, "record_failure", side_effect=_fail),
              patch.object(abs_mod, "record_success", side_effect=_success),
              patch.object(oai, "get_client", return_value=client)):
        for _ in range(5):
            await _call_llm()

    assert client.chat.completions.create.await_count == 5, (
        "flag OFF must dispatch every call"
    )
    assert seen == {"closed": 0, "fail": 0, "success": 0}, (
        f"flag OFF touched the breaker: {seen}"
    )
    assert ops == {"get": 0, "set": 0, "incr": 0, "expire": 0}, (
        f"flag OFF made Redis round trips: {ops}"
    )
    assert store == {}, f"flag OFF wrote circuit state: {store}"


@pytest.mark.asyncio
async def test_flag_off_compare_never_short_circuits(monkeypatch):
    """Flag OFF at the compare entry: an OPEN breaker is invisible and the
    compare runs exactly as it does today — which means it REACHES THE FAN-OUT.
    The counter is asserted, not merely built (adversarial review): without it
    the docstring's claim was unchecked and the test would pass on a compare
    that short-circuited for some other reason. Measured here: 22 Serper
    `search_web` calls + 2 Bright Data `bd_search_web` calls, which is exactly
    the spend test 2 proves the flag ON avoids."""
    monkeypatch.delenv(FLAG, raising=False)
    _arm_prod_search_config(monkeypatch)
    store, ops, _get, _set, _incr, _expire = _dict_breaker_redis(seed=_open_breaker_seed())
    fan = _FanOutCounters()
    llm_client = _mock_openai_client()

    with _all(*_patch_breaker_redis(_get, _set, _incr, _expire),
              *fan.patches(llm_client)):
        result = await _run_compare()

    assert result.get("code") != "LLM_UNAVAILABLE", (
        "flag OFF short-circuited the compare — flag OFF must be byte-identical"
    )
    assert fan.calls["search_web"] > 0 and fan.calls["bd_search_web"] > 0, (
        f"flag OFF did not reach the paid provider fan-out: {fan.calls} — the "
        "zero-fan-out assertion in test 2 would then prove nothing"
    )
    assert llm_client.chat.completions.create.await_count > 0


@pytest.mark.asyncio
async def test_flag_off_streaming_never_short_circuits(monkeypatch):
    """Flag OFF on the streaming entry too: an OPEN breaker is invisible and the
    stream reaches the fan-out."""
    monkeypatch.delenv(FLAG, raising=False)
    _arm_prod_search_config(monkeypatch)
    store, ops, _get, _set, _incr, _expire = _dict_breaker_redis(seed=_open_breaker_seed())
    fan = _FanOutCounters()
    llm_client = _mock_openai_client()

    with _all(*_patch_breaker_redis(_get, _set, _incr, _expire),
              *fan.patches(llm_client)):
        events = await _run_stream()

    codes = [d.get("code") for e, d in events if e == "error"]
    assert "LLM_UNAVAILABLE" not in codes, (
        "flag OFF short-circuited the stream — flag OFF must be byte-identical"
    )
    assert fan.calls["search_web"] > 0 and fan.calls["bd_search_web"] > 0, (
        f"flag OFF did not reach the paid provider fan-out: {fan.calls}"
    )
    # NOTE deliberately NOT asserted here: `ops == 0`. A flag-OFF compare already
    # makes 12 breaker GETs — the PRE-EXISTING firecrawl/scrapedo render-gate
    # `is_circuit_closed` reads, which have nothing to do with this unit. The
    # "flag OFF never touches the openai breaker" pin lives in
    # test_flag_off_never_reads_or_records_and_always_dispatches, where the only
    # breaker traffic possible is this unit's.
    assert llm_client.chat.completions.create.await_count > 0


# ---------------------------------------------------------------------------
# MINOR 5 — a wait_for timeout must be RECORDED, and never swallowed
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_wait_for_timeout_around_the_guard_records_a_failure(monkeypatch):
    """`asyncio.CancelledError` is a BaseException, so an `except Exception`
    never saw it: an `asyncio.wait_for` deadline around a guarded dispatch
    cancelled the call and the breaker recorded NOTHING (measured
    {'fail': 0, 'succ': 0}). Most compare-path LLM calls are wrapped in exactly
    such a wait_for, so this was the timeout class the breaker most needed to
    see. The cancellation must still propagate — the guard records, it does not
    swallow."""
    monkeypatch.setenv(FLAG, "true")
    store, ops, _get, _set, _incr, _expire = _dict_breaker_redis()

    client = MagicMock()

    async def _never_returns(**kwargs):
        await asyncio.sleep(30)

    client.chat.completions.create = _never_returns

    with _all(*_patch_breaker_redis(_get, _set, _incr, _expire)):
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(
                abs_mod.guarded_llm_create(client, model="gpt-4o-mini"),
                timeout=0.05,
            )

    blob = _breaker_blob(store)
    assert blob is not None, (
        "a wait_for timeout around the dispatch chokepoint recorded nothing — "
        "the cancellation escaped the guard's `except Exception`"
    )
    assert blob["failure_count"] == 1, f"expected one recorded failure, got {blob}"


# ---------------------------------------------------------------------------
# MAJOR 4 — a server-side LLM outage is a 503, not a 400
# ---------------------------------------------------------------------------
def test_llm_unavailable_surfaces_as_503():
    """`_surface_comparison_failure` fell through to the generic arm, so a
    SERVER-side LLM outage was reported to the client as a client error."""
    with pytest.raises(HTTPException) as excinfo:
        text_routes_mod._surface_comparison_failure({
            "success": False,
            "code": "LLM_UNAVAILABLE",
            "error": scs.LLM_UNAVAILABLE_FRIENDLY_MESSAGE,
        })
    assert excinfo.value.status_code == 503, (
        f"LLM_UNAVAILABLE surfaced as HTTP {excinfo.value.status_code}; an "
        "upstream outage belongs with the other 503s, not with BAD_REQUEST"
    )
    assert excinfo.value.detail["code"] == "LLM_UNAVAILABLE"
    # The client has no i18n key for this code yet, so it renders `error`
    # verbatim — it must therefore obey the no-scary-copy contract.
    msg = excinfo.value.detail["error"].lower()
    assert "failed" not in msg and "couldn't" not in msg and "try again" not in msg


def test_timeout_still_surfaces_as_503():
    """Guard the MAJOR-4 edit: widening the 503 arm must not move TIMEOUT."""
    with pytest.raises(HTTPException) as excinfo:
        text_routes_mod._surface_comparison_failure({"code": "TIMEOUT", "error": "x"})
    assert excinfo.value.status_code == 503
    assert excinfo.value.detail["code"] == "TIMEOUT"


def test_insufficient_data_still_surfaces_as_400():
    """...and must not move anything else onto 503 either."""
    with pytest.raises(HTTPException) as excinfo:
        text_routes_mod._surface_comparison_failure(
            {"code": "INSUFFICIENT_DATA", "error": "x"}
        )
    assert excinfo.value.status_code == 400


# ---------------------------------------------------------------------------
# MINOR 6 — the compare-path caller that was left unwired
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_verdict_critique_dispatch_feeds_the_breaker(monkeypatch):
    """`verdict_critique_service.critique_verdict` IS on the compare path
    (`_apply_self_critique`, gated by ENABLE_SELF_CRITIQUE) and was not wired to
    the breaker. With the breaker OPEN it must not dispatch; the function's own
    contract (serve the original verdict on any failure) is preserved."""
    monkeypatch.setenv(FLAG, "true")
    store, ops, _get, _set, _incr, _expire = _dict_breaker_redis(seed=_open_breaker_seed())
    client = _mock_openai_client()

    with _all(*_patch_breaker_redis(_get, _set, _incr, _expire),
              patch.object(vc_mod, "get_client", return_value=client)):
        result = await vc_mod.critique_verdict(
            comparison={"winner_index": 0, "winner_reason": "cheaper"},
            product_names=["Acme Widget", "Globex Gadget"],
        )

    assert client.chat.completions.create.await_count == 0, (
        "the self-critique pass dispatched to OpenAI with the breaker OPEN — it "
        "is on the compare path and must feed the breaker like the others"
    )
    assert result is None, "critique_verdict must degrade to the original verdict"
