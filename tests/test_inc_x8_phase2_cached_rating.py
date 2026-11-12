"""INC-X8 PHASE2-CACHED-RATING (G-INC-1, the S92-FIX incident lane) RED rows.

Spec: .qa-s80/G-INC-1_UNIT_SPEC.md section "Unit INC-X8" (X8.5), as amended by the batch
ruling R-G1-10 (the mutant that drops `not _kb_full` must be KILLED by a row that seeds a
KB full hit with the S81-18 test helpers: P8-6 below, the helpers COPIED from
tests/test_s81_s18_kb_first_serve.py, never imported).

Flag ENABLE_PHASE2_CACHED_RATING (default OFF, read per call as the FIRST conjunct of the new
block's condition). It acts only when ENABLE_PHASE2_RESIDUAL_GUARD skipped Phase 2 for the
product and the product is not a KB full hit: the product then gets the rating its in-memory
shopping rows hold (the free tier of get_verified_rating: extract_rating_from_shopping + the
not-low acceptance), with one INFO `[L2.6] phase 2 cached rating outcome=<hit|miss|error:T>
product=<n>`. RED rows fail at base on an AssertionError only; PIN rows are green at base,
with the FULL configuration (both flags, the knob, a deadline, the rows present) and call
recorders on `_get_verified_rating` and `scs.extract_rating_from_shopping`.

Driver: the s75 `_phase_mocks` pattern (tests/test_s75_fanout_starve.py:235-271, `_NoRead`
:226-232) re-implemented here, except that the `_get_price` stub writes the synthetic shopping
rows into `svc._shopping_items_cache` as `_get_price` does and extract_rating_from_shopping
is NOT patched (a wrapping recorder delegates to the real function). Hermetic: no network,
no LLM. Pure ASCII, LF.
"""
from __future__ import annotations

import asyncio
import copy
import importlib
import json
import logging
import os
import time
import types
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest

os.environ.setdefault("OPENAI_API_KEY", "sk" + "-test-dummy")

import app.main  # noqa: E402,F401  (FIRST: the dotenv-override hazard; caplog-safe at collection)
import app.services.structured_comparison_service as scs  # noqa: E402
from app.services import rating_service as rs  # noqa: E402

FLAG = "ENABLE_PHASE2_CACHED_RATING"
GUARD = "ENABLE_PHASE2_RESIDUAL_GUARD"
KNOB = "PHASE2_MIN_RESIDUAL_SECONDS"
FCKEY = "ENABLE_FACTCHECK_SHOPPING_KEY"
SCS_LOGGER = "app.services.structured_comparison_service"
LINE = "[L2.6] phase 2 cached rating outcome="
SKIP_LINE = "[L2.6] phase 2 skipped"
PRODUCT = {"brand": "Ajmal", "name": "Ajmal Aristocrat", "variant": None, "category": "fragrances",
           "search_query": "Ajmal Aristocrat", "_explicit": True}
OFF_SPELLINGS = [None, "false", " FALSE ", "0", "garbage"]
OFF_IDS = ["unset", "false", "padFALSE", "zero", "garbage"]
CLEARED_ENV = (FLAG, GUARD, KNOB, FCKEY, "ENABLE_KB_FIRST_SERVE", "ENABLE_VERDICT_CACHE_LOG",
               "ENABLE_JSONLD_RATING", "ENABLE_DATA_GUARDS_V2", "ENABLE_TIER_FILL_RESIDUAL_GUARD",
               "ENABLE_KB_INGEST", "ENABLE_FIELD_STATUS_METADATA", "ENABLE_RESULT_GATE",
               "ENABLE_SYNC_DB_OFFLOAD", "KB_FIRST_SERVE_TIMEOUT_SECONDS", "KB_FIRST_SERVE_MAX_ASOF_DAYS",
               "ENABLE_FRAGRANCE_ONLY_GATE", "ENABLE_LIVE_ROBOTS_REGISTRY", "ENABLE_UNIFIED_SEARCH_BOUND",
               "ENABLE_PARSE_PRESPLIT", "ENABLE_PARSE_BUDGET", "ENABLE_ARABIC_VERDICT_OUTPUT",
               "ENABLE_ANTHROPIC_TEXT", "ENABLE_ANTHROPIC_VERDICT", "ENABLE_ANTHROPIC_MODERATION",
               "ENABLE_LLM_SPEND_BREAKER", "ENABLE_FULL_STREAM_DEADLINE", "ENABLE_ALL_TIMEOUT_CAP_AS_TIMEOUT")


def _full_name():
    return scs._product_display_identity(PRODUCT["brand"], PRODUCT["name"], PRODUCT["variant"],
                                         PRODUCT["search_query"], False)[0]


def _fc_key():
    return scs._shopping_cache_key_or(PRODUCT["brand"], PRODUCT["name"], PRODUCT["variant"], _full_name())


def _rows(sources, rating=4.6, count=1200):
    name = _full_name()
    return [{"title": name + " Eau de Parfum", "source": s, "rating": rating, "ratingCount": count,
             "link": "https://" + "store-" + str(i) + ".example.com/p/aristocrat", "price": "BHD 30.000"}
            for i, s in enumerate(sources)]


ROWS = _rows(["Amazon.com", "Noon", "Sephora"])
TIER3_ROWS = _rows(["eBay"], rating=4.2, count=5000)
EMPTY_RATING = {"rating": None, "review_count": None, "rating_verified": False, "rating_source": None}


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    for name in CLEARED_ENV:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.delenv("SERPER_API_KEY", raising=False)
    monkeypatch.setattr(rs, "SERPER_API_KEY", None)
    yield


def _set(mp, name, value):
    if value is None:
        mp.delenv(name, raising=False)
    else:
        mp.setenv(name, value)


def _records(caplog, prefix):
    return [r.getMessage() for r in caplog.records if r.getMessage().startswith(prefix)]


class _NoRead:
    """A deadline stand-in that fails the test if a path reads it."""

    def _boom(self, *_a, **_k):
        raise AssertionError("the guard-OFF path read _compare_deadline")

    __sub__ = __rsub__ = __lt__ = __le__ = __gt__ = __ge__ = __float__ = _boom


@contextmanager
def _phase_mocks(svc, *, rows, rows_key, phase2_rating=None, rec=None, extract_raises=None):
    rec = rec if rec is not None else {}
    rec.setdefault("rating", [])
    rec.setdefault("fallback", [])
    rec.setdefault("extract", [])
    real_extract = scs.extract_rating_from_shopping

    async def _specs(*_a, **_k):
        return {"concentration": "EDP"}

    async def _price(*_a, **_k):
        svc._shopping_items_cache[rows_key] = copy.deepcopy(rows)
        return None

    async def _reviews(*_a, **_k):
        return None

    async def _rating(*a, **k):
        rec["rating"].append((a, k))
        if phase2_rating is not None:
            return dict(phase2_rating)
        return dict(EMPTY_RATING)

    async def _fallback(*a, **_k):
        rec["fallback"].append(a)
        return {}

    async def _empty(*_a, **_k):
        return {}

    async def _search(*_a, **_k):
        return {"organic": [], "shopping": []}

    def _extract(*a, **k):
        rec["extract"].append(a)
        if extract_raises is not None:
            raise extract_raises
        return real_extract(*a, **k)

    with patch.object(svc, "_get_specs", side_effect=_specs), \
            patch.object(svc, "_get_price", side_effect=_price), \
            patch.object(svc, "_get_reviews", side_effect=_reviews), \
            patch.object(svc, "_get_verified_rating", side_effect=_rating), \
            patch.object(svc, "_smart_fallback_extract", side_effect=_fallback), \
            patch.object(svc, "_track_serper_cost", lambda *a, **k: None), \
            patch.object(scs, "search_web", _search), \
            patch.object(scs, "extract_rating_from_shopping", _extract), \
            patch.object(scs, "tier2_fill_non_negotiables", side_effect=_empty), \
            patch.object(scs, "tier3_synthesize_non_negotiables", side_effect=_empty), \
            patch.object(scs, "collect_retailer_ratings", lambda *a, **k: []), \
            patch.object(scs, "get_product_image_url", AsyncMock(return_value=None)):
        yield rec


def _configure(mp, *, flag, residual, guard="true"):
    _set(mp, FLAG, flag)
    _set(mp, GUARD, guard)
    mp.setenv(KNOB, "8")


def _run(svc, mp, caplog, *, flag, residual=2.0, rows=ROWS, rows_key=None, guard="true", **kw):
    _configure(mp, flag=flag, residual=residual, guard=guard)
    if residual is None:
        svc._compare_deadline = _NoRead()
    else:
        svc._compare_deadline = time.monotonic() + residual
    caplog.set_level(logging.INFO, logger=SCS_LOGGER)
    with _phase_mocks(svc, rows=rows, rows_key=rows_key or _full_name(), **kw) as rec:
        result = asyncio.run(asyncio.wait_for(
            svc._fetch_product_data(dict(PRODUCT), "bahrain", True, True, nocache=True), 20.0))
    return result, rec


@pytest.fixture
def svc():
    return scs.StructuredComparisonService()


# ---------------------------------------------------------------------------
# PIN P8-0: the fixture is a tier-0 hit
# ---------------------------------------------------------------------------

def test_p8_0_fixture_is_a_tier0_hit():
    """P8-0: ROWS give 4.6 / 1200 / high / google_shopping; TIER3_ROWS give confidence low;
    the W4-7 key differs from full_name (so R8-5 can tell the views apart)."""
    hit = rs.extract_rating_from_shopping(_full_name(), copy.deepcopy(ROWS))
    assert hit["rating"] == 4.6 and hit["review_count"] == 1200, hit
    assert hit["rating_verified"] is True
    assert hit["rating_source"]["confidence"] == "high"
    assert hit["rating_source"]["extract_method"] == "google_shopping"
    low = rs.extract_rating_from_shopping(_full_name(), copy.deepcopy(TIER3_ROWS))
    assert low["rating_source"]["confidence"] == "low", low
    assert _fc_key() != _full_name(), (_fc_key(), _full_name())


# ---------------------------------------------------------------------------
# RED rows
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("value", ["true", " TRUE "], ids=["true", "padTRUE"])
def test_r8_1_skipped_product_gets_the_in_memory_rating(svc, monkeypatch, caplog, value):
    """R8-1 / R8-2: guard ON, knob 8, residual 2 s, X8 ON: rating 4.6 / 1200 verified from
    the in-memory rows; Phase 2's rating never called; one skip line and one hit line."""
    result, rec = _run(svc, monkeypatch, caplog, flag=value)
    assert result["rating"] == 4.6, result.get("rating")
    assert result["review_count"] == 1200
    assert result["rating_verified"] is True
    assert result["rating_source"]["extract_method"] == "google_shopping"
    assert result["rating_source"]["confidence"] == "high"
    assert rec["rating"] == []
    assert len(_records(caplog, SKIP_LINE)) == 1
    hits = _records(caplog, LINE)
    assert len(hits) == 1 and hits[0].startswith(LINE + "hit product="), hits


def test_r8_3_tier3_rows_give_no_rating_and_a_miss_line(svc, monkeypatch, caplog):
    result, rec = _run(svc, monkeypatch, caplog, flag="true", rows=TIER3_ROWS)
    assert result["rating"] is None and result["rating_verified"] is False
    lines = _records(caplog, LINE)
    assert len(lines) == 1 and lines[0].startswith(LINE + "miss product="), lines


def test_r8_4_extractor_error_is_contained(svc, monkeypatch, caplog):
    try:
        result, rec = _run(svc, monkeypatch, caplog, flag="true", extract_raises=RuntimeError("probe"))
    except RuntimeError as exc:  # the extractor error escaped _fetch_product_data
        raise AssertionError("the extractor error escaped _fetch_product_data: %r" % (exc,))
    assert result["rating"] is None
    lines = _records(caplog, LINE)
    assert len(lines) == 1 and lines[0].startswith(LINE + "error:RuntimeError product="), lines


def test_r8_5_factcheck_view_is_used(svc, monkeypatch, caplog):
    """R8-5: ENABLE_FACTCHECK_SHOPPING_KEY ON, rows only under the W4-7 key: still a 4.6 hit."""
    monkeypatch.setenv(FCKEY, "true")
    result, rec = _run(svc, monkeypatch, caplog, flag="true", rows_key=_fc_key())
    assert result["rating"] == 4.6, result.get("rating")
    assert result["rating_verified"] is True


def test_p8_5_no_new_keys(monkeypatch, caplog):
    """P8-5 (RED by its skip half): the X8 hit and a normal Phase-2 tier-0 hit from the REAL
    get_verified_rating over the same rows carry the same key set and the same rating fields
    (rating_source minus retrieved_at)."""
    assert not rs.SERPER_API_KEY
    normal_svc = scs.StructuredComparisonService()
    _set(monkeypatch, FLAG, "true")
    _set(monkeypatch, GUARD, None)
    normal_svc._compare_deadline = time.monotonic() + 100.0
    real_rating = scs.StructuredComparisonService._get_verified_rating

    @contextmanager
    def _mocks_real_rating():
        with _phase_mocks(normal_svc, rows=ROWS, rows_key=_full_name()) as rec:
            async def _real(*a, **k):
                return await real_rating(normal_svc, *a, **k)
            with patch.object(normal_svc, "_get_verified_rating", side_effect=_real):
                yield rec
    with _mocks_real_rating():
        normal = asyncio.run(asyncio.wait_for(
            normal_svc._fetch_product_data(dict(PRODUCT), "bahrain", True, True, nocache=True), 20.0))
    assert normal["rating"] == 4.6, normal.get("rating")
    skip_svc = scs.StructuredComparisonService()
    skipped, _rec = _run(skip_svc, monkeypatch, caplog, flag="true")
    assert set(skipped) == set(normal), sorted(set(skipped) ^ set(normal))
    for key in ("rating", "review_count", "rating_verified"):
        assert skipped[key] == normal[key], key
    a = dict(skipped["rating_source"] or {})
    b = dict(normal["rating_source"] or {})
    a.pop("retrieved_at", None)
    b.pop("retrieved_at", None)
    assert a == b and a, (a, b)


# ---------------------------------------------------------------------------
# PIN rows
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("value", OFF_SPELLINGS, ids=OFF_IDS)
def test_p8_1_flag_off_identity_full_config(svc, monkeypatch, caplog, value):
    """P8-1: X8 OFF over five spellings, guard ON, knob 8, residual 2 s, ROWS present: rating
    None, no rating call, no extract call, no cached-rating line, exactly one skip line."""
    result, rec = _run(svc, monkeypatch, caplog, flag=value)
    assert result["rating"] is None
    assert result["rating_verified"] is False and result["rating_source"] is None
    assert rec["rating"] == [] and rec["extract"] == []
    assert _records(caplog, LINE) == []
    assert len(_records(caplog, SKIP_LINE)) == 1


def test_p8_2_not_skipped_runs_phase2_as_today(svc, monkeypatch, caplog):
    """P8-2: X8 ON, residual 100 s (no skip): the Phase-2 stub's 3.9 / 77 stands."""
    p2 = {"rating": 3.9, "review_count": 77, "rating_verified": True,
          "rating_source": {"name": "stub", "url": "https://" + "example.com/r", "confidence": "high"}}
    result, rec = _run(svc, monkeypatch, caplog, flag="true", residual=100.0, phase2_rating=p2)
    assert result["rating"] == 3.9 and result["review_count"] == 77
    assert len(rec["rating"]) == 1 and rec["extract"] == []
    assert _records(caplog, LINE) == []


def test_p8_3_guard_off_never_reads(svc, monkeypatch, caplog):
    """P8-3: X8 ON, guard unset, a deadline that raises on any read: Phase 2 runs."""
    result, rec = _run(svc, monkeypatch, caplog, flag="true", residual=None, guard=None)
    assert len(rec["rating"]) == 1
    assert _records(caplog, LINE) == []


def test_p8_4_refill_stays_skipped(svc, monkeypatch, caplog):
    """P8-4: X8 ON and a skip: the smart-fallback refill is never called (specs miss the
    critical fragrance fields: the specs stub returns only a concentration)."""
    result, rec = _run(svc, monkeypatch, caplog, flag="true")
    assert rec["fallback"] == []
    assert len(_records(caplog, SKIP_LINE)) == 1


# ---------------------------------------------------------------------------
# P8-6 (R-G1-10): a KB full hit with the guard skipping Phase 2 -> the X8 block stays out
# (the S81-18 helpers, COPIED from tests/test_s81_s18_kb_first_serve.py)
# ---------------------------------------------------------------------------

NOW = datetime(2026, 11, 2, 6, 0, tzinfo=timezone.utc)
HOST_A = "store-a.example.com"
HOST_B = "store-b.example.com"
P0 = ("Acme", "Nimbus Noir Eau de Parfum")
P1 = ("Zephyra", "Velvet Dusk Eau de Toilette")
QUERY = "Acme Nimbus Noir Eau de Parfum vs Zephyra Velvet Dusk Eau de Toilette"
LLM_PARSED = {"products": [
    {"brand": P0[0], "name": P0[1], "variant": None, "category": "fragrances", "search_query": " ".join(P0)},
    {"brand": P1[0], "name": P1[1], "variant": None, "category": "fragrances", "search_query": " ".join(P1)},
], "comparison_type": "value"}


def _kb():
    from app.services import kb_service as kb
    return kb


def _pid(pair):
    return _kb().kb_product_id(pair[0], pair[1])


def _vid(pid, ml):
    kb = _kb()
    conc = pid.split("|")[3]
    conc = conc if conc in kb.kb_concentrations() else None
    return kb.kb_variant_key(pid, conc, ml)


def _iso(moment):
    return moment.strftime("%Y-%m-%dT%H:%M:%S+00:00")


def _card(pair, host, slug):
    pid = _pid(pair)
    conc = pid.split("|")[3]
    url = "https://" + host + "/products/" + slug
    offers = [{"variant_id": _vid(pid, 100), "merchant_id": host, "market": "BH", "observed_currency": "BHD",
               "amount": 42.5, "canonical_url": url, "last_seen": _iso(NOW - timedelta(days=2)),
               "captured_at": _iso(NOW - timedelta(days=5)), "first_seen": _iso(NOW - timedelta(days=5)),
               "in_stock": True, "list_vs_sale": "unknown", "evidence_rung": "page_evidence", "size_ml": 100}]
    specs = {"concentration": "Eau de Parfum", "scent_family": "woody", "season": "winter"}
    variants = sorted({o["variant_id"] for o in offers})
    return {
        "product": {"id": pid, "brand": pair[0], "name": pair[1], "concentration": conc, "line": None,
                    "audience": None, "identity_confidence": "high", "updated_at": "2026-10-30T00:00:00+00:00"},
        "variants": [{"id": v, "product_id": pid, "concentration": conc,
                      "size_ml": int(v.rsplit("|", 1)[1]) if v.rsplit("|", 1)[1].isdigit() else None,
                      "gtin": None, "sku": None} for v in variants],
        "offers": offers,
        "images": [{"url": "https://" + host + "/img/" + slug + ".jpg", "provenance_host": host,
                    "source": "retailer_jsonld", "captured_at": _iso(NOW - timedelta(days=4))}],
        "specs": [{"field": f, "value": v, "lang": "en", "cited": True, "source_url": url,
                   "extractor": "retailer_jsonld"} for f, v in specs.items()],
        "rating": {"sources": 1, "review_count": 31, "rating": 4.6},
    }


class _CardClient:
    def __init__(self, cards):
        self.cards = dict(cards)

    def rpc(self, name, params=None, *args, **kwargs):
        client = self
        params = dict(params or {})

        class _B:
            def execute(self_inner):
                return types.SimpleNamespace(data=copy.deepcopy(client.cards.get(params.get("p_product_id"))))
        return _B()

    def table(self, name):
        raise AssertionError("never reads a table: " + name)


def _install_kb(mp, client):
    kbs = importlib.import_module("app.services.kb_serve")
    mp.setattr(kbs, "_admin_client", lambda: client, raising=False)
    mp.setattr(kbs, "_now", lambda: NOW, raising=False)
    from app.utils import db_offload

    async def _run_db(call):
        return call()
    mp.setattr(db_offload, "run_db", _run_db)


def _install_compare(mp, svc, rec):
    from app.services import audit_service as _audit
    from app.services import content_safety_service as _cs
    from app.services import scoring_service as _ss

    async def _parse(query):
        return json.loads(json.dumps(LLM_PARSED)), {"prompt_tokens": 1, "completion_tokens": 1}

    async def _gen(*_a, **_k):
        return ({"winner_index": 0, "winner_declaration": "Acme wins", "winner_reason": "longevity",
                 "verdict": "v", "pros": {}, "cons": {}}, {"prompt_tokens": 7, "completion_tokens": 3})

    async def _leg(*a, **_k):
        rec.setdefault("legs", []).append(a[:1])
        return None

    async def _rating(*a, **_k):
        rec.setdefault("rating", []).append(a)
        return dict(EMPTY_RATING)

    async def _empty(*_a, **_k):
        return {}

    async def _search(*_a, **_k):
        rec.setdefault("legs", []).append(("search",))
        return {"organic": []}

    async def _moderate(_self, _text):
        return _cs.SafetyResult(allowed=True)

    async def _none(*_a, **_k):
        return None

    async def _cat(*_a, **_k):
        return "fragrances"

    mp.setattr(_audit, "log_content_blocked", _none)
    mp.setattr(_cs.ContentSafetyService, "moderate_output", _moderate)
    mp.setattr(scs, "parse_product_query", _parse)
    mp.setattr(scs, "generate_comparison", _gen)
    mp.setattr(scs, "reconcile_pair_fairness", lambda *a, **k: None)
    mp.setattr(scs, "classify_category_llm", _cat)
    mp.setattr(scs, "get_scoring_service", lambda: _ss.ScoringService())
    mp.setattr(scs, "search_web", _search)
    mp.setattr(scs, "tier2_fill_non_negotiables", _empty)
    mp.setattr(scs, "tier3_synthesize_non_negotiables", _empty)
    mp.setattr(scs, "collect_retailer_ratings", lambda *a, **k: [])
    mp.setattr(scs, "get_product_image_url", _none)
    mp.setattr(scs, "get_user_demographics", _none)
    svc._get_specs = _leg
    svc._get_price = _leg
    svc._get_reviews = _leg
    svc._get_verified_rating = _rating
    svc._smart_fallback_extract = _empty
    svc._fetch_behavior_profile = _none


def test_p8_6_kb_full_hit_keeps_the_card_rating(monkeypatch, caplog):
    """P8-6 (R-G1-10): ENABLE_KB_FIRST_SERVE ON with two full cards, the guard ON with a knob
    above the whole cap (every product's Phase 2 skipped) and X8 ON: the X8 block never runs
    (no cached-rating line), the card rating 4.6 / 31 stands, no live leg ran."""
    _install_kb(monkeypatch, _CardClient({_pid(P0): _card(P0, HOST_A, "nimbus-noir"),
                                          _pid(P1): _card(P1, HOST_B, "velvet-dusk")}))
    monkeypatch.setenv("ENABLE_KB_FIRST_SERVE", "true")
    monkeypatch.setenv("KB_FIRST_SERVE_TIMEOUT_SECONDS", "1.5")
    monkeypatch.setenv("KB_FIRST_SERVE_MAX_ASOF_DAYS", "30")
    monkeypatch.setenv(GUARD, "true")
    monkeypatch.setenv(KNOB, "100")
    monkeypatch.setenv(FLAG, "true")
    monkeypatch.setattr(scs, "STREAM_HARD_CAP_SECONDS", 30.0)
    caplog.set_level(logging.INFO, logger=SCS_LOGGER)
    svc = scs.StructuredComparisonService()
    rec = {}
    _install_compare(monkeypatch, svc, rec)
    body = asyncio.run(asyncio.wait_for(svc.compare_from_text(QUERY, region="bahrain", nocache=True), 60))
    assert body.get("success") is True, str(body)[:300]
    assert (body.get("metadata") or {}).get("kb_hit") == ["full", "full"], body.get("metadata")
    assert len(_records(caplog, SKIP_LINE)) == 2, _records(caplog, SKIP_LINE)
    assert rec.get("legs", []) == [] and rec.get("rating", []) == [], rec
    assert _records(caplog, LINE) == []
    for p in body["products"]:
        assert p.get("rating") == 4.6 and p.get("review_count") == 31, (p.get("rating"), p.get("review_count"))
