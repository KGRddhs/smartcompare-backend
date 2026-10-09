"""FANOUT-STARVE (session 75, 2026-10-09) -- flag-OFF compare identity against main 4c0f3c99.

Ruling FY25 (post-adversary, closes FY5): the runtime-truth adversary's ident_probe.py, made a
repo test. Seven flag-OFF scenarios (REST q full, REST pair full, REST partial at gather,
stream q / pair full, stream partial at gather, the parse-failure shape) plus the injected
private-marks scenario (FY3: an LLM JSON carrying `_parse_presplit` / `_parse_fallback`) run
through the REAL compare entries and the REAL `_fetch_product_data`, with every network leaf
faked (the LLM parse and verdict, the unified search, specs / price / reviews / rating, the
refill tiers, the image). Each scenario's observable result -- the response bytes (or the
stream's event list), the cost counters, the searches issued, the products fetched and the
category-resolution calls -- is normalised (the clock fields dropped) and hashed; the
digests must equal the ones recorded at main 4c0f3c99 in
tests/fixtures/s75_fanout_identity_digests.json (re-record: run this file as a script at the
base sha, `python -m tests.test_s75_fanout_identity <out.json>`). Flag-ON nodes pin the
success-path stamps the partial-path nodes cannot reach (FY5): metadata.parse_presplit and
metadata.phase2_skipped on the REST success body and on the stream `complete` payload.

Hygiene: pure ASCII, LF; bounded runner only; netguard on (no host is ever resolved: every
leaf is faked); the sentinel key is built by concatenation.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import sys
from pathlib import Path

if __name__ == "__main__":  # pragma: no cover - the recorder runs outside pytest's guards
    import socket

    import dotenv
    import dotenv.main

    dotenv.load_dotenv = lambda *a, **k: False  # never read a developer .env
    dotenv.main.load_dotenv = lambda *a, **k: False
    for _name in ("REDIS_URL", "UPSTASH_REDIS_URL", "UPSTASH_REDIS_TOKEN",
                  "UPSTASH_REDIS_REST_URL", "SUPABASE_URL", "SENTRY_DSN"):
        os.environ.pop(_name, None)
    _LOCAL = ("127.0.0.1", "::1", "localhost", "", None)
    _real_gai = socket.getaddrinfo

    def _gai(host, *args, **kwargs):
        if host not in _LOCAL:
            raise OSError("identity recorder: network blocked")
        return _real_gai(host, *args, **kwargs)

    socket.getaddrinfo = _gai
    os.environ["OPENAI_API_KEY"] = "sk" + "-test-dummy"

os.environ.setdefault("OPENAI_API_KEY", "sk" + "-test-dummy")

import app.services.structured_comparison_service as scs  # noqa: E402
from app.services import scoring_service as _ss  # noqa: E402

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "s75_fanout_identity_digests.json"
QUERY = "iPhone 15 vs Galaxy S24"
PAIR = ("iPhone 15", "Galaxy S24")
UNIT_ENV = ("ENABLE_PARSE_PRESPLIT", "ENABLE_PARSE_BUDGET", "PARSE_TIMEOUT_SECONDS",
            "ENABLE_UNIFIED_SEARCH_BOUND", "UNIFIED_SEARCH_TIMEOUT_SECONDS",
            "ENABLE_PHASE2_RESIDUAL_GUARD", "PHASE2_MIN_RESIDUAL_SECONDS",
            "DEBUG_STAGE_TIMINGS", "ENABLE_FULL_STREAM_DEADLINE")
# The clock fields: they differ between two runs of the SAME tree (measured: ident_probe
# base x2 / head x2, 2026-10-09), so they are dropped before hashing.
VOLATILE = frozenset({"elapsed_ms", "elapsed_seconds", "timestamp", "generated_at",
                      "created_at", "started_at", "cached_at", "fetched_at", "at",
                      "stage_timings_ms", "orchestrator_timings_ms", "request_id"})
LLM_PARSED = {"products": [
    {"brand": "Apple", "name": "iPhone 15", "variant": None, "category": "electronics",
     "search_query": "Apple iPhone 15"},
    {"brand": "Samsung", "name": "Galaxy S24", "variant": None, "category": "electronics",
     "search_query": "Samsung Galaxy S24"}], "comparison_type": "value"}
USAGE = {"prompt_tokens": 100, "completion_tokens": 50}


class _Patcher:
    """monkeypatch's setattr/undo, usable outside pytest (the base recorder)."""

    def __init__(self):
        self._undo = []

    def setattr(self, obj, name, value):
        self._undo.append((obj, name, getattr(obj, name)))
        setattr(obj, name, value)

    def undo(self):
        while self._undo:
            obj, name, value = self._undo.pop()
            setattr(obj, name, value)


def _install(p, svc, state, slow=False):
    async def _parse(query):
        state["parse_calls"] += 1
        if state["parse_delay"]:
            await asyncio.sleep(state["parse_delay"])
        out = json.loads(json.dumps(LLM_PARSED))
        out.update(state["parse_extra"] or {})
        return out, dict(USAGE)

    async def _gen(*_a, **_k):
        if state["gen_delay"]:
            await asyncio.sleep(state["gen_delay"])
        return ({"winner_index": 0, "winner_declaration": "iPhone wins",
                 "winner_reason": "battery", "verdict": "v", "pros": {}, "cons": {}},
                {"prompt_tokens": 7, "completion_tokens": 3})

    async def _cat_llm(*_a, **_k):
        return "electronics"

    real_resolve = scs._resolve_pair_category

    async def _resolve(products, selected_category, parser_path=False):
        state["resolve"].append([[dict(x) for x in products], parser_path])
        return await real_resolve(products, selected_category, parser_path=parser_path)

    real_track = svc._track_gpt_cost

    def _track(usage):
        state["track_gpt"] += 1
        return real_track(usage)

    async def _search(query, num_results=10, **kwargs):
        state["searches"].append([query, num_results, sorted(kwargs)])
        return {"organic": [{"title": "T " + query[:20], "link": "https://example.com/a",
                             "snippet": "spec sheet battery 4000 mAh"}]}

    async def _specs(*_a, **_k):
        return {"battery_mah": 4000, "storage_gb": 128, "display_size_in": 6.1}

    async def _price(*_a, **_k):
        return {"amount": 120.0, "currency": "BHD", "estimated": False,
                "source_method": "local_bhd", "retailer": "Best Buy",
                "url": "https://www.bestbuy.com/site/x/1.p", "title": "x", "in_stock": True}

    async def _reviews(*_a, **_k):
        return {"highlights": ["good"], "summary": "ok"}

    async def _rating(*_a, **_k):
        return {"rating": 4.5, "review_count": 10, "rating_verified": True,
                "rating_source": {"name": "example", "url": "https://example.com/r"}}

    async def _empty(*_a, **_k):
        return {}

    async def _none(*_a, **_k):
        return None

    from app.services import content_safety_service as _cs

    async def _moderate(_self, _text):
        return _cs.SafetyResult(allowed=True)  # the L3 moderation call, faked (no network)

    p.setattr(_cs.ContentSafetyService, "moderate_output", _moderate)
    p.setattr(scs, "parse_product_query", _parse)
    p.setattr(scs, "generate_comparison", _gen)
    p.setattr(scs, "reconcile_pair_fairness", lambda *a, **k: None)
    p.setattr(scs, "classify_category_llm", _cat_llm)
    p.setattr(scs, "get_scoring_service", lambda: _ss.ScoringService())
    p.setattr(scs, "_resolve_pair_category", _resolve)
    p.setattr(scs, "search_web", _search)
    p.setattr(scs, "tier2_fill_non_negotiables", _empty)
    p.setattr(scs, "tier3_synthesize_non_negotiables", _empty)
    p.setattr(scs, "collect_retailer_ratings", lambda *a, **k: [])
    p.setattr(scs, "get_product_image_url", _none)
    svc._track_gpt_cost = _track
    svc._get_specs = _specs
    svc._get_price = _price
    svc._get_reviews = _reviews
    svc._get_verified_rating = _rating
    svc._smart_fallback_extract = _empty
    real_fetch = svc._fetch_product_data

    async def _slow_fetch(product_info, region, include_specs, include_reviews, nocache=False,
                          partial_slot=None):
        if partial_slot is not None and isinstance(svc._early_specs_buffer, list):
            svc._early_specs_buffer[partial_slot] = {
                "brand": "", "name": product_info["name"], "full_name": product_info["name"],
                "category": "electronics", "specs": {"display": "6.1 in"}, "price": None}
        await asyncio.sleep(30)

    async def _fetch(product_info, *args, **kwargs):
        state["fetch_products"].append(dict(product_info))
        return await (_slow_fetch if slow else real_fetch)(product_info, *args, **kwargs)

    svc._fetch_product_data = _fetch


def _new_state():
    return {"parse_calls": 0, "parse_extra": None, "parse_delay": 0.0, "gen_delay": 0.0,
            "fetch_products": [], "resolve": [], "track_gpt": 0, "searches": []}


async def _scenario(kind, query, *, cap=30.0, explicit_pair=None, slow=False, parse_extra=None,
                    env=None):
    """One compare (kind "rest" or "stream") on the faked pipeline; returns the snapshot."""
    p = _Patcher()
    saved = {name: os.environ.get(name) for name in UNIT_ENV}
    for name in UNIT_ENV:
        os.environ.pop(name, None)
    os.environ.update(env or {})
    state = _new_state()
    state["parse_extra"] = parse_extra
    try:
        p.setattr(scs, "STREAM_HARD_CAP_SECONDS", cap)
        svc = scs.StructuredComparisonService()
        _install(p, svc, state, slow=slow)
        kwargs = {"explicit_pair": explicit_pair} if explicit_pair else {}
        if kind == "rest":
            payload = await asyncio.wait_for(
                svc.compare_from_text(query, region="bahrain", nocache=True, **kwargs), 60)
        else:
            payload = []

            async def _drain():
                async for event in svc.compare_from_text_streaming(
                        query, region="bahrain", nocache=True, **kwargs):
                    payload.append(list(event))
            await asyncio.wait_for(_drain(), 60)
        return {"payload": payload, "parse_calls": state["parse_calls"],
                "track_gpt": state["track_gpt"], "fetch_products": state["fetch_products"],
                "resolve": state["resolve"], "searches": state["searches"],
                "cost": [svc.total_cost, svc.api_calls, svc.gpt_calls, svc.serper_calls]}
    finally:
        p.undo()
        for name, value in saved.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


MARKS = {"_parse_presplit": True, "_parse_fallback": True}
SCENARIOS = {
    "rest_q_full": ("rest", QUERY, {}),
    "rest_pair_full": ("rest", QUERY, {"explicit_pair": PAIR}),
    "rest_q_partial_gather": ("rest", QUERY, {"cap": 0.5, "slow": True}),
    "stream_q_full": ("stream", QUERY, {}),
    "stream_pair_full": ("stream", QUERY, {"explicit_pair": PAIR}),
    "stream_q_partial_gather": ("stream", QUERY, {"cap": 0.5, "slow": True}),
    "rest_q_parse_fail_shape": ("rest", "just one thing", {}),
    "rest_q_full_llm_json_carries_private_marks": ("rest", QUERY, {"parse_extra": MARKS}),
    "stream_q_full_llm_json_carries_private_marks": ("stream", QUERY, {"parse_extra": MARKS}),
}


def _normalize(obj):
    if isinstance(obj, dict):
        return {str(k): _normalize(v) for k, v in obj.items() if k not in VOLATILE}
    if isinstance(obj, (list, tuple)):
        return [_normalize(v) for v in obj]
    if isinstance(obj, float):
        return repr(obj)
    return obj


def _digest(snapshot):
    blob = json.dumps(_normalize(snapshot), sort_keys=True, default=repr, ensure_ascii=True)
    return hashlib.sha256(blob.encode("ascii")).hexdigest()


async def _all_digests():
    out = {}
    for name, (kind, query, kwargs) in SCENARIOS.items():
        out[name] = _digest(await _scenario(kind, query, **kwargs))
    return out


def test_FY25_flag_off_compare_identity_matches_main():
    """FY25 / FY5: with every unit flag OFF the nine scenarios' normalised digests equal the
    ones recorded at main 4c0f3c99 (the injected-marks scenarios included: an LLM JSON
    carrying a private mark moves no byte, FY3)."""
    want = json.loads(FIXTURE.read_text(encoding="ascii"))["digests"]
    got = asyncio.run(_all_digests())
    moved = sorted(name for name in SCENARIOS if got.get(name) != want.get(name))
    assert moved == [], "FY25: flag-OFF scenarios moved against main 4c0f3c99: %r" % (moved,)


def _complete(events):
    for kind, payload in events:
        if kind == "complete":
            return payload
    raise AssertionError("no complete event: %r" % ([e[0] for e in events],))


def test_FY25_presplit_marks_the_rest_success_and_stream_complete():
    """FY5 (X4 / X5): ENABLE_PARSE_PRESPLIT on, full pipeline -> the REST success body and
    the stream `complete` payload carry metadata.parse_presplit (the success-path call sites
    of _stamp_unit_metadata), with zero LLM parse calls."""
    env = {"ENABLE_PARSE_PRESPLIT": "true"}
    rest = asyncio.run(_scenario("rest", QUERY, env=env))
    assert rest["payload"].get("success") is True, rest["payload"]
    metadata = rest["payload"].get("metadata") or {}
    assert metadata.get("partial") is not True, metadata
    assert metadata.get("parse_presplit") is True, metadata
    assert rest["parse_calls"] == 0, rest["parse_calls"]
    stream = asyncio.run(_scenario("stream", QUERY, env=env))
    complete = _complete(stream["payload"])
    assert (complete.get("metadata") or {}).get("parse_presplit") is True, complete.get("metadata")


def test_FY25_phase2_skip_marks_the_rest_success_and_stream_complete():
    """FY5: ENABLE_PHASE2_RESIDUAL_GUARD on with a knob above the cap -> Phase 2 skipped on
    both products and metadata.phase2_skipped on the REST success body and the stream
    `complete` payload."""
    env = {"ENABLE_PHASE2_RESIDUAL_GUARD": "true", "PHASE2_MIN_RESIDUAL_SECONDS": "1000"}
    rest = asyncio.run(_scenario("rest", QUERY, env=env))
    metadata = rest["payload"].get("metadata") or {}
    assert metadata.get("partial") is not True, metadata
    assert metadata.get("phase2_skipped") is True, metadata
    stream = asyncio.run(_scenario("stream", QUERY, env=env))
    complete = _complete(stream["payload"])
    assert (complete.get("metadata") or {}).get("phase2_skipped") is True, complete.get("metadata")


if __name__ == "__main__":  # pragma: no cover - the recorder (run at the base sha)
    digests = asyncio.run(_all_digests())
    with open(sys.argv[1], "w", encoding="ascii", newline="\n") as handle:
        json.dump({"base": "4c0f3c99", "digests": digests}, handle, indent=1, sort_keys=True)
        handle.write("\n")
    print("wrote", sys.argv[1], len(digests))
