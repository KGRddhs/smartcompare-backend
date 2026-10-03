"""Session 70 OAI_OBS item 4 -- ``_GatheringFuture exception was never retrieved``
(Sentry PYTHON-FASTAPI-1K / 1J / Y / 1N / 17).

Mechanism (CPython 3.12.9 ``asyncio.tasks.gather._done_callback``, read from the
venv): when the OUTER ``_GatheringFuture`` had ``cancel()`` requested, the last
child's completion runs ``outer.set_exception(fut._make_cancelled_error())`` --
regardless of ``return_exceptions=True``. The outer future therefore ends
FINISHED-with-exception, not cancelled; when nothing calls ``.result()`` /
``.exception()`` on it, ``Future.__del__`` reports ``"_GatheringFuture exception
was never retrieved"`` through ``loop.call_exception_handler`` (an ERROR on the
``asyncio`` logger = the Sentry event).

The leak site is ``structured_comparison_service._get_price``'s
``_cancel_prefetched_direct``: it cancels every speculative prefetch gather
(``asyncio.ensure_future(asyncio.gather(..., return_exceptions=True))`` --
shopify / algolia / sitemap / jsonapi / one per new-adapter family incl. occ)
and then ``_prefetched_direct.clear()`` drops the last reference, so the
exception is never retrieved. It runs on the genuine Tier-1 short-circuit and,
through the M13-30 ``finally``, on EVERY exit incl. an outer cancel.

Requirements pinned here (OAI_OBS_SPEC.md R4.1-R4.3 + review corrections C3,
C4, C11 + orchestrator rulings OR7, OR10): a module-level done-callback
``_retrieve_prefetch_outcome`` marks the outcome retrieved for EVERY entry in
``_cancel_prefetched_direct``, awaiting nothing; which futures are cancelled,
and when, is unchanged.

BASE = 4bd5a09f (OR14; app/ and tests/ are byte-identical to 94c097cd).
RED at BASE: the three ``*_no_unretrieved_gather`` tests (3 captured reports
each -- the occ, sitemap and jsonapi gathers), the helper-contract test (the
helper is absent) and the R4.2 source-shape test (no callback is attached).
PIN (green at BASE): the pure-asyncio mechanism test and
test_prefetch_children_still_cancelled.

C3: nothing this unit creates is imported at module top (the helper is looked
up inside the test body).
C4: every LLM leg ``_get_price`` could reach (extract_price,
extract_price_from_training_data, extraction_service.get_client) is stubbed
and asserted unreached; ``search_web`` HANGS (a raising mock in a discovery
prefetch Task produces an unrelated "Task exception was never retrieved").
C11: the capture helper installs the loop exception handler BEFORE the
scenario, the scenario drops every reference it held (it returns None), and the
full sleep / ``gc.collect()`` sequence runs INSIDE the handler scope; the
handler stores strings only (holding the future would resurrect it inside its
own ``__del__``).
OR7: assertions read ONLY ``context["message"]`` (the attached CancelledError
can be fresh, with no traceback) -- never frames, never the future's repr.
"""
import ast
import asyncio
import gc
import pathlib
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import app.services.extraction_service as es
import app.services.structured_comparison_service as scs

_NEVER_RETRIEVED = "never retrieved"
_CALLBACK_ERROR = "Exception in callback"
_GET_PRICE_ARGS = dict(
    brand="elf", name="SuperHydrate Moisturizer", variant=None,
    region="bahrain", search_query="elf SuperHydrate Moisturizer",
    nocache=True, category="makeup",
)


# ---------------------------------------------------------------------------
# the C11-safe capture helper
# ---------------------------------------------------------------------------

async def _capture_unretrieved(scenario):
    """Run ``await scenario()`` with the loop exception handler capturing every
    context MESSAGE, then settle (20x sleep(0), gc.collect(), 5x sleep(0),
    gc.collect()) while the handler is STILL installed, restore the previous
    handler in ``finally`` and return the captured message strings.

    ``scenario`` must return None and hold no reference to any prefetch future
    once it returns (C11): a leftover reference defers ``__del__`` past the
    restore and the report escapes to stderr, reading as clean."""
    loop = asyncio.get_running_loop()
    previous = loop.get_exception_handler()
    captured = []

    def _handler(_loop, context):
        captured.append(str(context.get("message")))

    loop.set_exception_handler(_handler)
    try:
        await scenario()
        for _ in range(20):
            await asyncio.sleep(0)
        gc.collect()
        for _ in range(5):
            await asyncio.sleep(0)
        gc.collect()
    finally:
        loop.set_exception_handler(previous)
    return captured


def _leaks(captured):
    return [m for m in captured if _NEVER_RETRIEVED in m]


def _callback_errors(captured):
    return [m for m in captured if _CALLBACK_ERROR in m]


# ---------------------------------------------------------------------------
# the mechanism R4 relies on (pure asyncio, no app code)
# ---------------------------------------------------------------------------

async def _child():
    await asyncio.sleep(30)


@pytest.mark.asyncio
async def test_mechanism_cancelled_gather_reports_unretrieved():
    """PIN (pure asyncio, CPython 3.12): a cancel()-requested gather ends
    FINISHED (not cancelled) even with return_exceptions=True, asyncio reports
    it as never retrieved at GC when nothing reads it, and the R4 callback
    shape (``f.cancelled() or f.exception()``) is enough to silence the report.
    Green at base and HEAD."""
    states = {}

    async def _leaky():
        outer = asyncio.ensure_future(asyncio.gather(_child(), return_exceptions=True))
        await asyncio.sleep(0)  # the child starts
        outer.cancel()
        for _ in range(5):
            await asyncio.sleep(0)  # the child ends cancelled -> outer.set_exception(...)
        states["leaky"] = (outer.done(), outer.cancelled())
        # return without retrieving: the only reference dies here

    captured = await _capture_unretrieved(_leaky)
    assert states["leaky"] == (True, False), states
    leaks = _leaks(captured)
    assert leaks, captured
    assert all(m.startswith("_GatheringFuture ") for m in leaks), leaks

    async def _retrieved():
        outer = asyncio.ensure_future(asyncio.gather(_child(), return_exceptions=True))
        outer.add_done_callback(lambda f: f.cancelled() or f.exception())
        await asyncio.sleep(0)
        outer.cancel()
        for _ in range(5):
            await asyncio.sleep(0)
        states["retrieved"] = (outer.done(), outer.cancelled())

    captured = await _capture_unretrieved(_retrieved)
    assert states["retrieved"] == (True, False), states
    assert not _leaks(captured), captured
    assert not _callback_errors(captured), captured


# ---------------------------------------------------------------------------
# R4.1 -- the helper's contract
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_retrieve_prefetch_outcome_helper_contract():
    """RED at base (the helper is absent). R4.1: a module-level, synchronous
    done-callback that marks a cancel()-requested gather's outcome retrieved,
    never raises (a CANCELLED future is skipped -- ``.exception()`` would raise
    CancelledError on it), awaits nothing and changes no outcome."""
    helper = getattr(scs, "_retrieve_prefetch_outcome", None)
    assert callable(helper), (
        "structured_comparison_service._retrieve_prefetch_outcome is absent (R4.1)")
    assert not asyncio.iscoroutinefunction(helper), "R4.2: the callback awaits nothing"

    loop = asyncio.get_running_loop()
    cancelled = loop.create_future()
    cancelled.cancel()
    assert helper(cancelled) is None
    assert cancelled.cancelled()

    with_result = loop.create_future()
    with_result.set_result([None, None])
    assert helper(with_result) is None
    assert with_result.result() == [None, None]

    with_exc = loop.create_future()
    boom = RuntimeError("boom")
    with_exc.set_exception(boom)
    assert helper(with_exc) is None
    assert with_exc.exception() is boom  # outcome unchanged

    async def _attached():
        outer = asyncio.ensure_future(asyncio.gather(_child(), return_exceptions=True))
        outer.add_done_callback(helper)
        await asyncio.sleep(0)
        outer.cancel()
        for _ in range(5):
            await asyncio.sleep(0)
        assert outer.done() and not outer.cancelled()

    captured = await _capture_unretrieved(_attached)
    assert not _leaks(captured), captured
    assert not _callback_errors(captured), captured

    # a later awaiter still receives the CancelledError (outcome unchanged)
    outer = asyncio.ensure_future(asyncio.gather(_child(), return_exceptions=True))
    outer.add_done_callback(helper)
    await asyncio.sleep(0)
    outer.cancel()
    with pytest.raises(asyncio.CancelledError):
        await outer


def _cancel_prefetched_direct_defs():
    tree = ast.parse(pathlib.Path(scs.__file__).read_text(encoding="utf-8"))
    return [n for n in ast.walk(tree)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
            and n.name == "_cancel_prefetched_direct"]


def _is_call(node, obj_name, attr, args=None):
    if not (isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)):
        return False
    func = node.value.func
    if not (isinstance(func, ast.Attribute) and func.attr == attr
            and isinstance(func.value, ast.Name) and func.value.id == obj_name):
        return False
    if args is None:
        return True
    return [a.id for a in node.value.args if isinstance(a, ast.Name)] == args


def test_cancel_prefetched_direct_attaches_callback_to_every_entry():
    """RED at base (no callback is attached). R4.2, source shape: inside
    ``_cancel_prefetched_direct`` the loop over ``_prefetched_direct.values()``
    keeps ``if not t.done(): t.cancel()`` exactly, attaches
    ``t.add_done_callback(_retrieve_prefetch_outcome)`` for EVERY entry (a
    statement of the loop body, not of the ``if``), and the dict is still
    cleared after the loop; the function stays synchronous (awaits nothing).
    Behaviourally, "every entry" cannot be told apart from "every pending
    entry" (a done, unconsumed prefetch gather holds a result, not an
    exception), so the requirement is pinned on the source."""
    defs = _cancel_prefetched_direct_defs()
    assert len(defs) == 1, len(defs)
    fn = defs[0]
    assert isinstance(fn, ast.FunctionDef), "R4.2: nothing is awaited"
    loops = [s for s in fn.body if isinstance(s, ast.For)
             and isinstance(s.iter, ast.Call) and isinstance(s.iter.func, ast.Attribute)
             and s.iter.func.attr == "values"
             and isinstance(s.iter.func.value, ast.Name)
             and s.iter.func.value.id == "_prefetched_direct"]
    assert len(loops) == 1, ast.dump(fn)[:400]
    loop = loops[0]
    assert isinstance(loop.target, ast.Name), ast.dump(loop.target)
    t = loop.target.id
    cancel_ifs = [s for s in loop.body if isinstance(s, ast.If)
                  and isinstance(s.test, ast.UnaryOp) and isinstance(s.test.op, ast.Not)
                  and isinstance(s.test.operand, ast.Call)
                  and isinstance(s.test.operand.func, ast.Attribute)
                  and s.test.operand.func.attr == "done"
                  and any(_is_call(b, t, "cancel") for b in s.body)]
    assert len(cancel_ifs) == 1, "the `if not t.done(): t.cancel()` guard is unchanged"
    attached = [s for s in loop.body
                if _is_call(s, t, "add_done_callback", ["_retrieve_prefetch_outcome"])]
    assert len(attached) == 1, (
        "R4.2: t.add_done_callback(_retrieve_prefetch_outcome) must be a statement of "
        "the loop body (every entry), not absent and not inside the `if`")
    after = fn.body[fn.body.index(loop) + 1:]
    assert any(_is_call(s, "_prefetched_direct", "clear") for s in after), \
        "_prefetched_direct.clear() still follows the loop"


# ---------------------------------------------------------------------------
# the real _get_price, with its cascade stubbed (no network, no LLM leg)
# ---------------------------------------------------------------------------

def _stub_cascade(monkeypatch, svc, *, shopping_delay=0.0, hang_shopping=False):
    """``_stub_common`` (tests/test_adapter_prefetch_hook.py, copied) plus:
    exactly the three prefetch gathers the Sentry issues name (sitemap/bolo,
    jsonapi/nasser, occ) with SLEEPING adapters, a HANGING discovery
    ``search_web``, a Tier-1 shopping stub that wins (optionally after a
    delay, so the children are in flight) or hangs (the outer-cancel path),
    and every LLM leg stubbed + recorded (C4). A ``_timeout_none`` spy counts
    the adapters the prefetch actually wrapped, so a run in which nothing was
    prefetched cannot pass vacuously."""
    rec = {"wrapped": 0, "bolo_started": 0, "nasser_started": 0,
           "occ_started": 0, "occ_cancelled": 0, "llm": []}

    # --- _stub_common: no cache / DB / negative-cache so the live cascade runs
    monkeypatch.setattr(scs, "get_cached", lambda *a, **k: None)
    monkeypatch.setattr(scs, "get_negative_cache", lambda *a, **k: None)
    monkeypatch.setattr(scs, "set_cached", lambda *a, **k: None)
    monkeypatch.setattr(scs, "validate_price_query", lambda *a, **k: True)

    async def _no_db_price(*a, **k):
        return None
    monkeypatch.setattr(
        "app.services.product_data_service.get_cached_price", _no_db_price,
        raising=False,
    )
    monkeypatch.setattr(svc, "_save_price_to_db", lambda *a, **k: None, raising=False)

    # --- the prefetch slot: makeup, no shopify/algolia, escalation OFF
    monkeypatch.setattr(scs, "ENABLE_PAGE_SCRAPE", True, raising=False)
    monkeypatch.setattr(scs, "_should_escalate_price_scrape", lambda *a, **k: False)
    monkeypatch.setattr(scs, "get_shopify_sources_for_category", lambda c: [])
    monkeypatch.setattr(scs, "get_algolia_sources_for_category", lambda c: [])
    monkeypatch.setattr(scs, "get_sitemap_sources_for_category",
                        lambda c: [SimpleNamespace(domain="bolo.bh")])
    monkeypatch.setattr(scs, "get_jsonapi_sources_for_category",
                        lambda c: [SimpleNamespace(domain="nasserpharmacy.com")])
    monkeypatch.setattr(scs, "get_occ_sources_for_category",
                        lambda c: [SimpleNamespace(domain="occ.test")])
    for name in ("get_woo_sources_for_category", "get_salla_sources_for_category",
                 "get_magento_gql_sources_for_category", "get_unbxd_sources_for_category",
                 "get_restjson_sources_for_category", "get_noon_sources_for_category",
                 "get_gcc_shopify_pagescrape_sources_for_category"):
        monkeypatch.setattr(scs, name, lambda c: [])

    real_timeout_none = scs._timeout_none

    def _spy_timeout_none(make_coro, timeout=scs._ADAPTER_TIMEOUT, **kwargs):
        rec["wrapped"] += 1
        return real_timeout_none(make_coro, timeout, **kwargs)
    monkeypatch.setattr(scs, "_timeout_none", _spy_timeout_none)

    # --- sleeping adapters (bolo via _sitemap_fetch_coro, nasser, occ)
    async def _sleep_bolo(product_name, currency="BHD"):
        rec["bolo_started"] += 1
        await asyncio.sleep(30)
        return None

    async def _sleep_nasser(product_name, currency="BHD"):
        rec["nasser_started"] += 1
        await asyncio.sleep(30)
        return None

    async def _sleep_occ(domain, product_name, currency, resolved_category=None):
        rec["occ_started"] += 1
        try:
            await asyncio.sleep(30)
        except asyncio.CancelledError:
            rec["occ_cancelled"] += 1
            raise
        return None
    monkeypatch.setattr(scs, "fetch_bolo_price", _sleep_bolo, raising=False)
    monkeypatch.setattr(scs, "fetch_nasser_price", _sleep_nasser, raising=False)
    monkeypatch.setattr(scs, "fetch_occ_rest_price", _sleep_occ)

    # --- discovery HANGS (never raises: a raising mock in a discovery prefetch
    #     Task produces an unrelated "Task exception was never retrieved")
    async def _hang_search_web(*a, **k):
        await asyncio.sleep(3600)
        return {"organic": []}
    monkeypatch.setattr(scs, "search_web", _hang_search_web)

    async def _no_organic(*a, **k):
        return {"organic": [], "knowledge_graph": None}
    monkeypatch.setattr(scs, "search_price_organic", _no_organic, raising=False)

    # --- Tier-1 Serper shopping
    if hang_shopping:
        async def _shopping(*a, **k):
            await asyncio.sleep(3600)
            return {"shopping": [], "organic": [], "shopping_region": "bahrain"}
    else:
        async def _shopping(*a, **k):
            if shopping_delay:
                await asyncio.sleep(shopping_delay)
            return {
                "shopping": [{
                    "title": "elf SuperHydrate Moisturizer",
                    "price": "BHD 8.50", "source": "bolo.bh",
                    "link": "https://www.bolo.bh/p",
                }],
                "organic": [], "shopping_region": "bahrain",
            }
    monkeypatch.setattr(scs, "search_product_prices", _shopping)

    # --- C4: no LLM leg may be reached (record instead of raising, so a wrong
    #     path shows up as an assertion, never as orphan-task noise)
    async def _llm_price(*a, **k):
        rec["llm"].append("extract_price")
        return {"amount": None, "currency": "BHD"}, {"prompt_tokens": 0, "completion_tokens": 0}

    async def _llm_fallback(*a, **k):
        rec["llm"].append("extract_price_from_training_data")
        return {"amount": None, "currency": "BHD"}, {"prompt_tokens": 0, "completion_tokens": 0}

    def _no_client():
        rec["llm"].append("get_client")
        return MagicMock()
    monkeypatch.setattr(scs, "extract_price", _llm_price)
    monkeypatch.setattr(scs, "extract_price_from_training_data", _llm_fallback)
    monkeypatch.setattr(es, "get_client", _no_client)
    return rec


async def _tier1_short_circuit(monkeypatch, box, shopping_delay):
    """Genuine Tier-1 short-circuit: Serper Shopping returns a genuine BHD price
    with escalation OFF, so the speculative prefetch gathers are cancelled
    unconsumed (``_cancel_prefetched_discovery`` -> ``_cancel_prefetched_direct``).
    Holds no reference past its return (C11)."""
    svc = scs.get_comparison_service()
    box.append(_stub_cascade(monkeypatch, svc, shopping_delay=shopping_delay))
    price = await svc._get_price(**_GET_PRICE_ARGS)
    assert price is not None and price.get("amount"), price  # the Tier-1 price won


async def _outer_cancel(monkeypatch, box):
    """The M13-30 path: an outer ``task.cancel()`` while ``_get_price`` is parked
    at the Tier-1 shopping await with the prefetch children in flight; the
    ``finally`` converges on the same cleanup. Holds no reference past its
    return (C11)."""
    svc = scs.get_comparison_service()
    box.append(_stub_cascade(monkeypatch, svc, hang_shopping=True))
    task = asyncio.ensure_future(svc._get_price(**_GET_PRICE_ARGS))
    for _ in range(20):
        await asyncio.sleep(0)
    await asyncio.sleep(0.05)
    assert not task.done(), "expected _get_price parked at the shopping await"
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    else:  # pragma: no cover - the cancel must propagate
        raise AssertionError("_get_price swallowed the outer cancel")
    assert task.cancelled()
    del task


def _assert_prefetch_fired(rec):
    assert rec["wrapped"] >= 3, (
        f"the prefetch wrapped {rec['wrapped']} adapter(s) in _timeout_none; "
        "expected the sitemap (bolo), jsonapi (nasser) and occ gathers")
    assert not rec["llm"], f"C4: an LLM leg was reached: {rec['llm']}"


# ---------------------------------------------------------------------------
# R4 -- no unretrieved prefetch gather on any _cancel_prefetched_direct path
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_price_tier1_short_circuit_prerun_no_unretrieved_gather(monkeypatch):
    """RED at base (3 reports -- occ, sitemap, jsonapi). The gathers are
    cancelled BEFORE their children ran (the shopping stub never yields)."""
    box = []
    captured = await _capture_unretrieved(
        lambda: _tier1_short_circuit(monkeypatch, box, 0.0))
    rec = box[0]
    _assert_prefetch_fired(rec)
    assert rec["occ_started"] == 0, rec  # cancelled pre-run: the factory never ran
    assert not _callback_errors(captured), captured
    leaks = _leaks(captured)
    assert not leaks, (
        f"{len(leaks)} prefetch gather(s) finished with an unretrieved "
        f"CancelledError on the Tier-1 short-circuit (pre-run): {leaks}")


@pytest.mark.asyncio
async def test_get_price_tier1_short_circuit_inflight_no_unretrieved_gather(monkeypatch):
    """RED at base (3 reports). The shopping stub sleeps 0.05 s so the children
    are IN FLIGHT when the gathers are cancelled (the occ child started exactly
    once)."""
    box = []
    captured = await _capture_unretrieved(
        lambda: _tier1_short_circuit(monkeypatch, box, 0.05))
    rec = box[0]
    _assert_prefetch_fired(rec)
    assert rec["occ_started"] == 1, rec
    assert not _callback_errors(captured), captured
    leaks = _leaks(captured)
    assert not leaks, (
        f"{len(leaks)} prefetch gather(s) finished with an unretrieved "
        f"CancelledError on the Tier-1 short-circuit (in flight): {leaks}")


@pytest.mark.asyncio
async def test_get_price_outer_cancel_no_unretrieved_gather(monkeypatch):
    """RED at base (3 reports). The M13-30 ``finally`` path: an outer cancel
    while parked at the shopping await, the occ child in flight."""
    box = []
    captured = await _capture_unretrieved(lambda: _outer_cancel(monkeypatch, box))
    rec = box[0]
    _assert_prefetch_fired(rec)
    assert rec["occ_started"] == 1, rec
    assert not _callback_errors(captured), captured
    leaks = _leaks(captured)
    assert not leaks, (
        f"{len(leaks)} prefetch gather(s) finished with an unretrieved "
        f"CancelledError on the outer-cancel (finally) path: {leaks}")


# ---------------------------------------------------------------------------
# R4.2 -- the cancellation semantics are unchanged
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_prefetch_children_still_cancelled(monkeypatch):
    """PIN (green at base): in the in-flight scenario the occ child receives
    CancelledError -- the fix retrieves the outcome, it never changes which
    futures are cancelled or when."""
    box = []
    await _capture_unretrieved(lambda: _tier1_short_circuit(monkeypatch, box, 0.05))
    rec = box[0]
    _assert_prefetch_fired(rec)
    assert rec["occ_started"] == 1, rec
    assert rec["occ_cancelled"] == 1, rec
