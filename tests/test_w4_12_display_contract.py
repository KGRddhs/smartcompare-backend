"""W4-12 - display contract: one spelling, one margin, one verdict.

Findings PO-VERDICT-TRUTH-03/-04/-06/-07/-08/-09/-14. Spec
`.qa-s68/specs/W4_12_UNIT_SPEC.md` AS AMENDED by its "ADVERSARIAL SPEC REVIEW
(2026-09-26, session 68)" section and by `W4_12_FABLE_RULINGS.md` (binding).

UNFLAGGED (live on deploy):
  * A - the SSE `verdict` frame is scrubbed with the SAME score-internals scrub the
        `complete` payload gets (`response_builder.scrub_verdict_prose`, called in
        `compare_from_text_streaming` right after `reconcile_winner_prose`).
  * B - the BC `products[i].reviews.review_summary` alias ships the scrubbed copy
        (a NEW dict, placed after the alias `review_praise` build), and
        `review_praise` is built from the scrubbed summary on BOTH surfaces (F2).
        `retailer_quotes` stay verbatim (third-party snippets, pin B4).
  * C - `/home/smart-pick` and `/profile/recent-decisions` names go through
        `dedup_brand_name` (`home_routes.py:456` priority_match is NOT touched).
  * D - loser-only `verdict_short` guard (K10: mask the LONGER name first).
  * E - `metadata.verdict_scrubbed` (present only when True) + ONE
        `[VERDICT_SCRUB]` WARNING per request.

FLAGGED (both default OFF, read per call):
  * `ENABLE_SMART_PICK_VERDICT_CAPTION` - caption source factual_verdict.line1 ->
    strip_score_internals(overview.winner.reason) -> None, tautology guard.
  * `ENABLE_SINGLE_VERDICT_MARGIN` - the PRE-nudge calibrated gap in
    `overview.winner.margin`, `scoring_v2.win_margin` and the SSE verdict margin
    (ties -> 0), read ONCE per streaming request (K12).

Every docstring says RED (absent at HEAD ac887e2d, fails on an assertion naming the
absent behaviour), PIN (green at HEAD, must stay green) or PIN/KILL (green at HEAD
and red under the named mutant). New symbols are looked up INSIDE test bodies via
getattr so the file always collects (K5). Every SSE frame is snapshotted with
json.dumps AT YIELD (the verdict payload's `comparison` is the same dict the builder
later mutates in place, so inspecting the live object is vacuous - spec 1a).
"""
from __future__ import annotations

import copy
import json
import logging
import socket
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.api import home_routes, profile_routes
from app.main import app
from app.services import response_builder as rb
from app.services.response_builder import _build_scoring_v2, build_comparison_response
from app.services.text_sanitize import (
    dedup_brand_name,
    has_score_internals,
    scrub_review_summary,
    strip_score_internals,
)

MARGIN_FLAG = "ENABLE_SINGLE_VERDICT_MARGIN"
CAPTION_FLAG = "ENABLE_SMART_PICK_VERDICT_CAPTION"
SCRUB_TAG = "[VERDICT_SCRUB]"
RECENT = "home.smart_pick.reason.recent_winner"
PRIORITY = "home.smart_pick.reason.priority_match"

client = TestClient(app)


# ---------------------------------------------------------------------------
# Guards: zero network (incl. libcurl's entry point), flag/env reset
# ---------------------------------------------------------------------------
_LOOPBACK = ("127.0.0.1", "::1", "localhost")


def _host_of(address):
    if isinstance(address, tuple) and address:
        return address[0]
    return address


@pytest.fixture(autouse=True)
def _zero_network(monkeypatch):
    """Block every non-loopback connect / getaddrinfo and curl_cffi.requests.get;
    fail the test at teardown if anything tried."""
    attempts = []
    real_connect = socket.socket.connect
    real_connect_ex = socket.socket.connect_ex
    real_getaddrinfo = socket.getaddrinfo

    def guard_connect(self, address, *a, **k):
        host = _host_of(address)
        if isinstance(host, bytes):
            host = host.decode("ascii", "replace")
        if host not in _LOOPBACK:
            attempts.append(("connect", host))
            raise OSError("W4-12 zero-network guard: blocked connect to %r" % (host,))
        return real_connect(self, address, *a, **k)

    def guard_connect_ex(self, address, *a, **k):
        host = _host_of(address)
        if isinstance(host, bytes):
            host = host.decode("ascii", "replace")
        if host not in _LOOPBACK:
            attempts.append(("connect_ex", host))
            raise OSError("W4-12 zero-network guard: blocked connect_ex to %r" % (host,))
        return real_connect_ex(self, address, *a, **k)

    def guard_getaddrinfo(host, *a, **k):
        name = host.decode("ascii", "replace") if isinstance(host, bytes) else host
        if name is not None and name not in _LOOPBACK:
            attempts.append(("getaddrinfo", name))
            raise socket.gaierror("W4-12 zero-network guard: blocked getaddrinfo(%r)" % (name,))
        return real_getaddrinfo(host, *a, **k)

    monkeypatch.setattr(socket.socket, "connect", guard_connect)
    monkeypatch.setattr(socket.socket, "connect_ex", guard_connect_ex)
    monkeypatch.setattr(socket, "getaddrinfo", guard_getaddrinfo)

    import curl_cffi.requests as curl_requests

    def curl_guard(*a, **k):
        attempts.append(("curl_cffi.get", a[:1]))
        raise RuntimeError("W4-12 zero-network guard: blocked curl_cffi.requests.get")

    monkeypatch.setattr(curl_requests, "get", curl_guard)
    yield
    assert not attempts, "W4-12 zero-network guard: the test attempted network I/O: %r" % (attempts,)


@pytest.fixture(autouse=True)
def _w412_env(monkeypatch):
    """Both new flags start UNSET; every flag that moves the asserted fields is
    pinned to its shipped default (OFF)."""
    for name in (
        MARGIN_FLAG,
        CAPTION_FLAG,
        "ENABLE_HONEST_PARTIAL_SCORING",
        "ENABLE_WINNER_PROSE_RECONCILE",
        "ENABLE_GPT_WINNER",
        "ENABLE_YOUTUBE_SOURCE",
        "EVAL_CAPTURE_DEBUG",
    ):
        monkeypatch.delenv(name, raising=False)
    yield
    app.dependency_overrides.clear()


def _set(monkeypatch, name, value):
    if value is None:
        monkeypatch.delenv(name, raising=False)
    else:
        monkeypatch.setenv(name, value)


# ---------------------------------------------------------------------------
# SSE harness (copied from tests/test_winner_prose_reconciliation.py:284-327,
# every frame snapshotted with json.dumps AT YIELD)
# ---------------------------------------------------------------------------
LEAKY = {
    "winner_index": 0,
    "winner_declaration": "Apple iPhone 15 with a presentation score of 100",
    "winner_reason": "Apple iPhone 15 scores 73.8 overall. It has the sharper camera.",
    "key_tradeoff": "Galaxy S24 trails by 12 points on value.",
    "value_context": {"product_0": "Scores 81 on value.", "product_1": "Solid value for money."},
    "best_for": {"product_0": "camera lovers", "product_1": "+5 pts battery fans"},
    "personalized_insights": [{"insight": "Matches you: overall score higher."}],
    "product_0_pros": ["Great camera"], "product_0_cons": ["Higher price"],
    "product_1_pros": ["Better value"], "product_1_cons": ["Shorter updates"],
    "specs_comparison": {"product_0_advantages": ["10.7-point higher camera", "Faster chip"],
                         "product_1_advantages": ["More RAM"], "similar": []},
}

# single-spaced, present strings (K6 / A5)
CLEAN = {
    "winner_index": 0,
    "winner_declaration": "Apple iPhone 15",
    "winner_reason": "Sharper camera and a faster chip.",
    "key_tradeoff": "Galaxy S24 has more RAM.",
    "value_context": {"product_0": "Fair for a flagship.", "product_1": "Solid value."},
    "best_for": {"product_0": "camera lovers", "product_1": "multitaskers"},
    "personalized_insights": [],
    "product_0_pros": ["Great camera"], "product_0_cons": ["Higher price"],
    "product_1_pros": ["Better value"], "product_1_cons": ["Shorter updates"],
    "specs_comparison": {"product_0_advantages": [], "product_1_advantages": [], "similar": []},
}


SSE_PAIRS = [("Apple", "iPhone 15"), ("Samsung", "Galaxy S24")]


def _sse_products(pairs=None):
    """The two SSE products; `pairs` [(brand, name), (brand, name)] renames them
    (brand/name/full_name/query) and keeps every other field."""
    out = _sse_products_default()
    for p, (b, n) in zip(out, pairs or []):
        p.update({"brand": b, "name": n, "full_name": "%s %s" % (b, n), "query": "%s %s" % (b, n)})
    return out


def _sse_products_default():
    base = {"variant": "128GB", "category": "electronics", "rating_verified": True,
            "data_freshness": "fresh"}
    return [
        {**base, "brand": "Apple", "name": "iPhone 15", "full_name": "Apple iPhone 15",
         "query": "Apple iPhone 15", "specs": {"ram": "6GB", "storage": "128GB"},
         "price": {"amount": 299, "currency": "BHD", "retailer": "Amazon", "url": None, "estimated": False},
         "best_price": 299, "currency": "BHD", "retailer": "Amazon",
         "reviews": {"average_rating": 4.5, "total_reviews": 1200,
                     "review_summary": {"overall_sentiment": "positive", "consensus": "Great phone.",
                                        "highlights": [], "review_volume": "high",
                                        "agreement_level": "strong"}},
         "rating": 4.5, "review_count": 1200, "rating_source": {"name": "Amazon", "url": None},
         "fact_check": {}},
        {**base, "brand": "Samsung", "name": "Galaxy S24", "full_name": "Samsung Galaxy S24",
         "query": "Samsung Galaxy S24", "specs": {"ram": "8GB", "storage": "128GB"},
         "price": {"amount": 279, "currency": "BHD", "retailer": "Noon", "url": None, "estimated": False},
         "best_price": 279, "currency": "BHD", "retailer": "Noon",
         "reviews": {"average_rating": 4.3, "total_reviews": 800,
                     "review_summary": {"overall_sentiment": "positive", "consensus": "Good Android phone.",
                                        "highlights": [], "review_volume": "high",
                                        "agreement_level": "moderate"}},
         "rating": 4.3, "review_count": 800, "rating_source": {"name": "Noon", "url": None},
         "fact_check": {}},
    ]


def _sse_scoring(winner_index=0, overall=(78, 72), win_margin=6):
    return {
        "scores": {
            "product_0": {"overall": overall[0],
                          "breakdown": {"price_score": 70, "spec_score": 80, "value_score": 65}},
            "product_1": {"overall": overall[1],
                          "breakdown": {"price_score": 85, "spec_score": 65, "value_score": 58}},
        },
        "winner_index": winner_index, "win_margin": win_margin, "scoring_method": "category_weighted",
        "dimension_winners": {"price_score": {"winner": "Samsung Galaxy S24", "margin": 15.0}},
        "price_tiers": {"Apple iPhone 15": "mid", "Samsung Galaxy S24": "mid"},
        "is_cross_tier": False, "category_weights": {"price_score": 0.2, "spec_score": 0.25},
    }


async def _stream(comparison, scoring, on_frame=None, pairs=None):
    """Drive the REAL compare_from_text_streaming; return [(event, wire_snapshot)].
    `on_frame(event_type)` runs after each frame is snapshotted (before the
    generator resumes). `pairs` renames the two products (default SSE_PAIRS)."""
    pairs = pairs or SSE_PAIRS
    from app.services.content_safety_service import ContentSafetyService, SafetyResult
    from app.services.structured_comparison_service import StructuredComparisonService

    service = StructuredComparisonService()
    frames = []
    with patch.object(service, "_fetch_product_data", new_callable=AsyncMock) as mock_fetch, \
         patch("app.services.structured_comparison_service.parse_product_query",
               new_callable=AsyncMock) as mock_parse, \
         patch("app.services.structured_comparison_service.generate_comparison",
               new_callable=AsyncMock) as mock_gen, \
         patch("app.services.structured_comparison_service.get_scoring_service") as mock_scoring, \
         patch.object(ContentSafetyService, "moderate_output",
                      new=AsyncMock(return_value=SafetyResult(allowed=True))):
        mock_parse.return_value = ({
            "products": [
                {"brand": b, "name": n, "category": "electronics", "search_query": "%s %s" % (b, n)}
                for b, n in pairs
            ],
            "comparison_type": "value",
        }, {"prompt_tokens": 0, "completion_tokens": 0})
        mock_fetch.side_effect = _sse_products(pairs)
        mock_gen.return_value = (copy.deepcopy(comparison), {"prompt_tokens": 0, "completion_tokens": 0})
        svc = MagicMock()
        svc.compute_scores.return_value = scoring
        svc.build_scores_summary.return_value = "summary"
        svc.compute_value_badge.return_value = "fair_price"
        svc.compute_tradeoff_pairs.return_value = []
        svc.compute_confidence.return_value = {"overall": "high"}
        mock_scoring.return_value = svc
        async for event_type, data in service.compare_from_text_streaming(
                "%s vs %s" % (pairs[0][1], pairs[1][1])):
            # the wire form: text_routes json.dumps(data, default=str) at yield
            frames.append((event_type, json.loads(json.dumps(data, default=str))))
            if on_frame is not None:
                on_frame(event_type)
    return frames


def _frame(frames, name):
    hits = [d for e, d in frames if e == name]
    assert hits, "no %r frame in %r" % (name, [e for e, _ in frames])
    return hits[-1]


def _shared_fields(verdict, complete):
    """The 10 shared fields of spec 1a: verdict value vs complete value."""
    vw = verdict["winner"]
    cw = complete["overview"]["winner"]
    cc = complete.get("comparison") or {}
    return {
        "winner.name": (vw.get("name"), cw.get("name")),
        "winner.reason": (vw.get("reason"), cw.get("reason")),
        "winner.key_tradeoff": (vw.get("key_tradeoff"), cw.get("key_tradeoff")),
        "winner.margin": (vw.get("margin"), cw.get("margin")),
        "winner.product_index": (vw.get("product_index"), cw.get("product_index")),
        "recommendation": (verdict.get("recommendation"), complete.get("recommendation")),
        "value_context": (verdict.get("value_context"), cc.get("value_context")),
        "best_for": (verdict.get("best_for"), cc.get("best_for")),
        "personalized_insights": (verdict.get("personalized_insights"),
                                  complete.get("personalized_insights")),
        "comparison": (verdict.get("comparison"), cc),
    }


def _scrub_records(caplog):
    return [r for r in caplog.records
            if r.levelno == logging.WARNING and SCRUB_TAG in r.getMessage()]


# ===========================================================================
# A - SSE verdict parity (UNFLAGGED)
# ===========================================================================

@pytest.mark.asyncio
async def test_sse_verdict_frame_carries_no_score_internals():
    """A1 RED - at HEAD the `verdict` frame ships the RAW GPT dict: 8 fields leak
    score internals (spec 1a). The pre-verdict `scrub_verdict_prose` call is absent."""
    frames = await _stream(LEAKY, _sse_scoring(0))
    v = _frame(frames, "verdict")
    alias = v.get("comparison") or {}
    checked = {
        "winner.name": v["winner"].get("name"),
        "winner.reason": v["winner"].get("reason"),
        "winner.key_tradeoff": v["winner"].get("key_tradeoff"),
        "recommendation": v.get("recommendation"),
        "alias.winner_reason": alias.get("winner_reason"),
        "alias.key_tradeoff": alias.get("key_tradeoff"),
        "alias.winner_declaration": alias.get("winner_declaration"),
    }
    for k, val in (v.get("value_context") or {}).items():
        checked["value_context." + k] = val
    for k, val in (v.get("best_for") or {}).items():
        checked["best_for." + k] = val
    for i, item in enumerate(v.get("personalized_insights") or []):
        checked["insight[%d]" % i] = item.get("insight")
    for k, lst in (alias.get("specs_comparison") or {}).items():
        for i, s in enumerate(lst or []):
            checked["specs_comparison.%s[%d]" % (k, i)] = s
    leaking = sorted(k for k, val in checked.items() if has_score_internals(val))
    assert leaking == [], (
        "RED: the SSE verdict frame is not scrubbed before the yield; leaking fields: %r" % leaking
    )


@pytest.mark.asyncio
async def test_sse_verdict_frame_equals_complete_on_shared_fields():
    """A2 RED - GPT and scoring agree (index 0). At HEAD only margin and
    product_index agree; 8 of the 10 shared fields differ (spec 1a)."""
    frames = await _stream(LEAKY, _sse_scoring(0))
    pairs = _shared_fields(_frame(frames, "verdict"), _frame(frames, "complete"))
    differing = sorted(k for k, (a, b) in pairs.items() if a != b)
    assert differing == [], "RED: verdict frame != complete payload on %r" % differing


@pytest.mark.asyncio
async def test_sse_verdict_frame_equals_complete_on_mismatch():
    """A3 RED - GPT index 1 / scoring index 0. The reconcile already repairs
    name/reason/key_tradeoff; value_context, best_for, personalized_insights and
    the comparison alias still differ at HEAD."""
    comp = copy.deepcopy(LEAKY)
    comp["winner_index"] = 1
    frames = await _stream(comp, _sse_scoring(0))
    pairs = _shared_fields(_frame(frames, "verdict"), _frame(frames, "complete"))
    differing = sorted(k for k, (a, b) in pairs.items() if a != b)
    assert differing == [], "RED: verdict frame != complete payload on the mismatch path: %r" % differing


@pytest.mark.asyncio
async def test_sse_complete_payload_values_unchanged():
    """A4 PIN/KILL - the leaky run's `complete` carries exactly today's measured
    values (the pre-scrub must not move the terminal payload).
    KILL: drop the SIB-4 value_context strip in build_comparison_response."""
    frames = await _stream(LEAKY, _sse_scoring(0))
    c = _frame(frames, "complete")
    assert c["overview"]["winner"] == {
        "product_index": 0, "name": "Apple iPhone 15", "declaration": "",
        "reason": "It has the sharper camera.", "key_tradeoff": "", "margin": 6,
    }
    assert c["recommendation"] == "It has the sharper camera."
    assert c["comparison"]["value_context"] == {"product_0": "", "product_1": "Solid value for money."}
    assert c["comparison"]["best_for"] == {"product_0": "camera lovers", "product_1": ""}
    assert c["personalized_insights"] == [{"insight": ""}]
    assert c["comparison"]["specs_comparison"]["product_0_advantages"] == ["Faster chip"]
    assert c["comparison"]["specs_comparison"]["product_1_advantages"] == ["More RAM"]
    assert [p["spec_advantages"] for p in c["specs"]["products"]] == [["Faster chip"], ["More RAM"]]
    assert _frame(frames, "settle_complete")["overview"]["winner"] == c["overview"]["winner"]


@pytest.mark.asyncio
async def test_sse_clean_verdict_frame_unchanged():
    """A5 PIN - clean, single-spaced, present strings: the verdict frame's winner
    name/reason/key_tradeoff, value_context and best_for equal the INPUT strings."""
    frames = await _stream(CLEAN, _sse_scoring(0))
    v = _frame(frames, "verdict")
    assert v["winner"]["name"] == CLEAN["winner_declaration"]
    assert v["winner"]["reason"] == CLEAN["winner_reason"]
    assert v["winner"]["key_tradeoff"] == CLEAN["key_tradeoff"]
    assert v["recommendation"] == CLEAN["winner_reason"]
    assert v["value_context"] == CLEAN["value_context"]
    assert v["best_for"] == CLEAN["best_for"]


@pytest.mark.asyncio
async def test_sse_double_spaced_clean_reason_verdict_equals_complete():
    """A5b RED (K6 lists it as a PIN; MEASURED RED at HEAD) - a clean reason with a
    double space after a full stop: `strip_score_internals` normalises whitespace in
    the builder, so `complete` ships "Sharper camera. Faster chip." while the HEAD
    verdict frame ships the raw double-spaced input. Parity is the property: the
    pre-verdict scrub must make verdict reason == complete reason."""
    comp = copy.deepcopy(CLEAN)
    comp["winner_reason"] = "Sharper camera.  Faster chip."
    frames = await _stream(comp, _sse_scoring(0))
    v, c = _frame(frames, "verdict"), _frame(frames, "complete")
    assert c["overview"]["winner"]["reason"] == "Sharper camera. Faster chip."
    assert v["winner"]["reason"] == c["overview"]["winner"]["reason"], (
        "RED: verdict reason %r != complete reason %r (no pre-verdict normalisation)"
        % (v["winner"]["reason"], c["overview"]["winner"]["reason"])
    )
    assert v["recommendation"] == c["recommendation"]


@pytest.mark.asyncio
async def test_sse_scrub_sets_metadata_and_logs_once(caplog):
    """A6 RED - leaky run whose winner_reason the strip EMPTIES (spec 4.1 counts
    only a full-empty; LEAKY's own reason keeps "It has the sharper camera." so it
    is NOT counted - see E4): `complete.metadata.verdict_scrubbed is True` (and on
    `settle_complete`), exactly ONE `[VERDICT_SCRUB]` WARNING for the request
    (scs and the builder both call the scrub; only the first can fire).
    RED at HEAD: no key, no log."""
    caplog.set_level(logging.WARNING)
    comp = copy.deepcopy(LEAKY)
    comp["winner_reason"] = "Apple iPhone 15 scores 73.8 overall."
    frames = await _stream(comp, _sse_scoring(0))
    c, s = _frame(frames, "complete"), _frame(frames, "settle_complete")
    assert c["metadata"].get("verdict_scrubbed") is True, (
        "RED: complete.metadata.verdict_scrubbed absent (scrub telemetry missing)"
    )
    assert s["metadata"].get("verdict_scrubbed") is True
    recs = _scrub_records(caplog)
    assert len(recs) == 1, "RED: expected exactly one %s WARNING, got %d" % (SCRUB_TAG, len(recs))


# ===========================================================================
# B - reviews alias + review_praise (UNFLAGGED)
# ===========================================================================

def _leaky_summary():
    return {
        "overall_sentiment": "positive",
        "consensus": "Alpha scores 73.8 overall. Loved for its longevity.",
        "highlights": [
            {"point": "Presentation score of 100.", "sentiment": "positive"},
            {"point": "Lasts all day on skin.", "sentiment": "positive"},
        ],
        "review_volume": "high",
        "agreement_level": "strong",
    }


def _consensus_only_summary():
    return {
        "overall_sentiment": "positive",
        "consensus": "Alpha scores 73.8 overall. Loved for its longevity.",
        "highlights": [{"point": "Presentation score of 100.", "sentiment": "positive"}],
        "review_volume": "high",
        "agreement_level": "strong",
    }


_QUOTES = [
    {"retailer": "amazon.com", "text": "I would give it a score of 100, lasts all day on skin.",
     "rating": 4.5},
    {"retailer": "sephora.com", "text": "Lovely sillage and a great bottle design overall.",
     "rating": 4.0},
]


def _review_pd(name, brand, reviews):
    return {
        "brand": brand, "name": name, "category": "fragrances",
        "price": {"amount": 50.0, "currency": "BHD", "source_method": "local_bhd", "retailer": "X"},
        "rating": 4.4, "review_count": 300,
        "reviews": reviews,
    }


def _review_build(reviews0, reviews1=None):
    if reviews1 is None:
        reviews1 = copy.deepcopy(reviews0)
    return build_comparison_response(
        product_data=[_review_pd("Alpha EDP", "Brand A", reviews0),
                      _review_pd("Beta EDT", "Brand B", reviews1)],
        comparison={"winner_index": 0, "winner_reason": "Alpha lasts longer."},
        scoring_result={"scores": {"product_0": {"overall": 70}, "product_1": {"overall": 60}},
                        "winner_index": 0, "win_margin": 10.0},
        category_used="fragrances",
    )


def test_products_alias_review_summary_is_scrubbed():
    """B1 RED - the BC `products[i].reviews.review_summary` alias re-ships the RAW
    summary at HEAD while the canonical projection is scrubbed (spec 1b)."""
    res = _review_build({"review_summary": _leaky_summary(), "retailer_quotes": copy.deepcopy(_QUOTES)})
    canon = res["reviews"]["products"][0]["review_summary"]
    alias = res["products"][0]["reviews"]["review_summary"]
    assert canon["consensus"] == "Loved for its longevity."
    assert [h["point"] for h in canon["highlights"]] == ["Lasts all day on skin."]
    assert alias["consensus"] == "Loved for its longevity.", (
        "RED: the products alias ships the raw review_summary consensus %r" % alias["consensus"]
    )
    assert [h["point"] for h in alias["highlights"]] == ["Lasts all day on skin."]
    assert alias == canon


def test_products_alias_reviews_input_dict_not_mutated():
    """B2 PIN - the caller's `reviews` object (possibly cache-owned) keeps its raw
    review_summary after the build: the alias gets a COPY, never an in-place edit."""
    reviews = {"review_summary": _leaky_summary(), "retailer_quotes": copy.deepcopy(_QUOTES)}
    raw = copy.deepcopy(reviews)
    _review_build(reviews)
    assert reviews["review_summary"]["consensus"] == raw["review_summary"]["consensus"]
    assert reviews["review_summary"] == raw["review_summary"]


def test_products_alias_reviews_without_summary_untouched():
    """B3 PIN - a `reviews` dict without `review_summary` gets no key injected on
    the alias (the default dict is the canonical projection's only)."""
    res = _review_build({"retailer_quotes": copy.deepcopy(_QUOTES)})
    alias = res["products"][0]["reviews"]
    assert "review_summary" not in alias
    assert alias["retailer_quotes"] == _QUOTES


def test_retailer_quotes_ship_verbatim_on_both_surfaces():
    """B4 PIN/KILL (F2) - verbatim third-party snippets are NOT scrubbed; the key is
    `text`. KILL: filter canonical retailer_quotes on has_score_internals(q['text'])."""
    res = _review_build({"review_summary": _leaky_summary(), "retailer_quotes": copy.deepcopy(_QUOTES)})
    canon = res["reviews"]["products"][0]["retailer_quotes"]
    alias = res["products"][0]["reviews"]["retailer_quotes"]
    assert canon == _QUOTES
    assert alias == _QUOTES
    assert has_score_internals(canon[0]["text"]) is True
    assert sorted(canon[0].keys()) == ["rating", "retailer", "text"]


@pytest.mark.parametrize("reviews", [
    None,
    {"review_summary": "Alpha scores 73.8 overall.", "retailer_quotes": []},
    {"review_summary": None, "retailer_quotes": []},
], ids=["reviews_none", "summary_str", "summary_none"])
def test_products_alias_non_dict_reviews_pass_through(reviews):
    """B5 PIN/KILL (K7) - `reviews=None`, or a `review_summary` that is a string or
    None, passes through untouched with no exception (the PYTHON-FASTAPI-J shape).
    KILL: drop the `(pd.get("reviews") or {})` coalesce at the canonical projection."""
    original = copy.deepcopy(reviews)
    res = _review_build(copy.deepcopy(reviews), copy.deepcopy(reviews))
    alias = res["products"][0]["reviews"]
    assert alias == original
    assert res["products"][0]["review_praise"] is None
    assert res["reviews"]["products"][0]["review_praise"] is None


def test_products_alias_review_praise_equals_canonical():
    """B6 PIN/KILL (K7) - alias `products[i].review_praise` == canonical
    `reviews.products[i].review_praise` on the leaky input.
    KILL: drop the alias `pd["review_praise"] = _safe_review_praise(pd)` line."""
    for summary in (_leaky_summary(), _consensus_only_summary()):
        res = _review_build({"review_summary": summary, "retailer_quotes": copy.deepcopy(_QUOTES)})
        for i in (0, 1):
            assert res["products"][i]["review_praise"] is not None
            assert res["products"][i]["review_praise"] == res["reviews"]["products"][i]["review_praise"]


@pytest.mark.parametrize("summary_fn", [_leaky_summary, _consensus_only_summary],
                         ids=["highlight_leak", "consensus_leak"])
def test_review_praise_built_from_scrubbed_summary(summary_fn):
    """B7 RED (F2 fold-in) - `review_praise` is RENDERED (ResultsAccordion) and at
    HEAD is built from the RAW review_summary on both surfaces, so a leaked internal
    score reaches the praise line. It must equal build_review_praise over the
    scrub_review_summary copy, on the canonical AND the alias surface."""
    from app.services.review_service import build_review_praise

    summary = summary_fn()
    res = _review_build({"review_summary": copy.deepcopy(summary), "retailer_quotes": copy.deepcopy(_QUOTES)})
    expected = build_review_praise({"review_summary": scrub_review_summary(summary)})
    assert expected is not None and not has_score_internals(expected)
    canon = res["reviews"]["products"][0]["review_praise"]
    alias = res["products"][0]["review_praise"]
    assert not has_score_internals(canon), "RED: canonical review_praise leaks: %r" % canon
    assert not has_score_internals(alias), "RED: alias review_praise leaks: %r" % alias
    assert canon == expected
    assert alias == expected


# ===========================================================================
# C - display names (UNFLAGGED)
# ===========================================================================

_DOUBLED_PAIRS = [
    ("HealthAid", "HealthAid Vitamin D3 1000 IU"),
    ("Apple", "Apple iPhone 14"),
    ("Samsung", "Samsung Galaxy S25 Ultra 256GB"),
    ("TOM FORD", "TOM FORD SOLEIL NEIGE 100ML"),
    ("Manama Pickles", "Manama Pickles Achbara Sauce"),
]


def _pick_row(winner, loser, *, winner_idx=0, declaration=None, line1=None, reason=None,
              dim_winners=None, id_="comp-1"):
    wb, wn = winner
    lb, ln = loser
    w = {"brand": wb, "name": wn, "price": {"amount": 329.0, "currency": "BHD"}}
    lo = {"brand": lb, "name": ln, "price": {"amount": 299.0, "currency": "BHD"}}
    products = [w, lo] if winner_idx == 0 else [lo, w]
    full = {
        "winner_index": winner_idx,
        "products": products,
        "scoring": {"dimension_winners": dim_winners or {}},
    }
    ov_winner = {}
    if declaration is not None:
        ov_winner["declaration"] = declaration
    if reason is not None:
        ov_winner["reason"] = reason
    if ov_winner:
        full["overview"] = {"winner": ov_winner}
    if line1 is not None:
        full["scoring_v2"] = {"factual_verdict": {"line1": line1, "line2": ""}}
    return {"id": id_, "created_at": "2026-09-01T00:00:00Z", "full_response": full}


def _smart_pick_route(rows, priorities=None):
    from app.api.auth_routes import get_current_user

    async def _user():
        return {"id": "w412-user", "email": "w412@example.invalid", "access_token": "fake-token"}

    app.dependency_overrides[get_current_user] = _user
    user_resp = MagicMock()
    user_resp.data = {"preferences": {"priorities": priorities or []}}
    comp_resp = MagicMock()
    comp_resp.data = rows

    def _table(name):
        m = MagicMock()
        if name == "users":
            m.select.return_value.eq.return_value.single.return_value.execute.return_value = user_resp
        else:
            m.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value \
                .execute.return_value = comp_resp
        return m

    supabase = MagicMock()
    supabase.table.side_effect = _table
    with patch("app.api.home_routes.get_user_supabase_client", return_value=supabase), \
         patch("app.api.home_routes._redis_get", return_value=None), \
         patch("app.api.home_routes._redis_set", return_value=True):
        resp = client.get("/api/v1/home/smart-pick", headers={"Authorization": "Bearer fake"})
    assert resp.status_code == 200, resp.text
    return resp.json()["smart_pick"]


def _recent_route(rows):
    from app.api.auth_routes import get_current_user

    async def _user():
        return {"id": "w412-user", "email": "w412@example.invalid", "access_token": "fake-token"}

    app.dependency_overrides[get_current_user] = _user
    supabase = MagicMock()
    comp_resp = MagicMock()
    comp_resp.data = rows
    supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value \
        .limit.return_value.execute.return_value = comp_resp
    with patch("app.api.profile_routes.get_user_supabase_client", return_value=supabase), \
         patch("app.api.profile_routes._redis_get", return_value=None), \
         patch("app.api.profile_routes._redis_set", return_value=True):
        resp = client.get("/api/v1/profile/recent-decisions", headers={"Authorization": "Bearer fake"})
    assert resp.status_code == 200, resp.text
    return resp.json()["recent"]


@pytest.mark.parametrize("i", range(len(_DOUBLED_PAIRS)),
                         ids=[p[0].replace(" ", "_") for p in _DOUBLED_PAIRS])
def test_smart_pick_names_are_deduped(i):
    """C1 RED - `_select_smart_pick` ships `f"{brand} {name}"` at home_routes:527/:528,
    doubling the brand whenever the name already carries it (12/22 eligible corpus
    rows). Both the pure function and GET /api/v1/home/smart-pick."""
    winner = _DOUBLED_PAIRS[i]
    loser = _DOUBLED_PAIRS[(i + 1) % len(_DOUBLED_PAIRS)]
    want_w = dedup_brand_name(*winner)
    want_l = dedup_brand_name(*loser)
    assert want_w == winner[1] and want_l == loser[1]
    pick = home_routes._select_smart_pick(["camera"], [_pick_row(winner, loser)])
    assert pick["winner_name"] == want_w, "RED: smart-pick winner_name doubled: %r" % pick["winner_name"]
    assert pick["runner_up_name"] == want_l, "RED: smart-pick runner_up_name doubled: %r" % pick["runner_up_name"]
    body = _smart_pick_route([_pick_row(winner, loser)], priorities=["camera"])
    assert body["winner_name"] == want_w
    assert body["runner_up_name"] == want_l


@pytest.mark.parametrize("i", range(len(_DOUBLED_PAIRS)),
                         ids=[p[0].replace(" ", "_") for p in _DOUBLED_PAIRS])
def test_recent_decisions_names_are_deduped(i):
    """C2 RED - `_extract_product_names` concatenates at profile_routes:102/:103
    (16/26 corpus rows doubled). Both the pure function and
    GET /api/v1/profile/recent-decisions."""
    winner = _DOUBLED_PAIRS[i]
    loser = _DOUBLED_PAIRS[(i + 1) % len(_DOUBLED_PAIRS)]
    row = _pick_row(winner, loser, winner_idx=1)
    w, lo = profile_routes._extract_product_names(row["full_response"])
    assert w == winner[1], "RED: recent-decisions winner_name doubled: %r" % w
    assert lo == loser[1], "RED: recent-decisions runner_up_name doubled: %r" % lo
    recent = _recent_route([row])
    assert len(recent) == 1
    assert recent[0]["winner_name"] == winner[1]
    assert recent[0]["runner_up_name"] == loser[1]


@pytest.mark.parametrize("winner,expected", [
    (("Apple", "iPhone 15"), "Apple iPhone 15"),
    (("Apple", "Applesauce"), "Apple Applesauce"),
    ((None, "iPhone 15"), "iPhone 15"),
    (("", "iPhone 15"), "iPhone 15"),
    (("Apple", None), "Apple"),
    ((" Apple ", " iPhone 15 "), "Apple iPhone 15"),
], ids=["no_brand_in_name", "applesauce", "brand_none", "brand_empty", "name_none", "padded"])
def test_names_unchanged_when_name_lacks_brand(winner, expected):
    """C3 PIN - every name that does not repeat its brand ships byte-identical to
    today's concat on both routes (the dedup is a no-op there)."""
    loser = ("Samsung", "Galaxy S24")
    pick = home_routes._select_smart_pick(["camera"], [_pick_row(winner, loser)])
    assert pick["winner_name"] == expected
    assert pick["runner_up_name"] == "Samsung Galaxy S24"
    w, lo = profile_routes._extract_product_names(_pick_row(winner, loser)["full_response"])
    assert w == expected
    assert lo == "Samsung Galaxy S24"


@pytest.mark.parametrize("winner,dim_winners,expected", [
    (("Apple", "iPhone 15"), {"camera_quality_score": "Apple iPhone 15"}, PRIORITY),
    (("Apple", "iPhone 15"), {"camera_quality_score": {"winner": "Apple iPhone 15", "margin": 5.0}}, RECENT),
    (("TOM FORD", "TOM FORD OUD WOOD"), {"camera_quality_score": "TOM FORD OUD WOOD"}, RECENT),
    (("TOM FORD", "TOM FORD OUD WOOD"),
     {"camera_quality_score": {"winner": "TOM FORD OUD WOOD", "margin": 5.0}}, RECENT),
], ids=["string_shape", "dict_shape", "string_brand_repeat", "dict_brand_repeat"])
def test_priority_match_semantics_unchanged(winner, dim_winners, expected):
    """C4 PIN/KILL (K4) - home_routes:456 compares the dim winner to the RAW concat;
    the production dict shape never matches (dead branch, W4-12c owns it) and a
    brand-repeating string label does not match the doubled concat.
    KILL: apply dedup_brand_name at home_routes:456 too (string_brand_repeat flips
    to priority_match)."""
    row = _pick_row(winner, ("Samsung", "Galaxy S24"), dim_winners=dim_winners)
    pick = home_routes._select_smart_pick(["camera_quality"], [row])
    assert pick["reason_key"] == expected


# ===========================================================================
# D - verdict_short (loser guard UNFLAGGED, caption source FLAGGED)
# ===========================================================================

_ROW12_W = ("Manama Pickles", "Achbara Sauce")
_ROW12_L = ("Manama Pickles", "Maabooch Kuwaiti Red 250g")


@pytest.mark.parametrize("flag", [None, "true"], ids=["caption_unset", "caption_on"])
def test_verdict_short_never_names_only_the_loser(monkeypatch, flag):
    """D1 RED - row-12 shape: the stored declaration names the LOSER and not the
    winner, and (for the flag-ON half, K3) so do factual_verdict.line1 and the
    reason. verdict_short must be None and the card falls back to the
    recent_winner copy. RED at HEAD: the loser's name ships as the caption."""
    _set(monkeypatch, CAPTION_FLAG, flag)
    row = _pick_row(
        _ROW12_W, _ROW12_L,
        declaration="Manama Pickles Maabooch Kuwaiti Red 250g",
        line1="Maabooch Kuwaiti Red 250g is the pick for heat.",
        reason="Maabooch Kuwaiti Red 250g brings more heat.",
    )
    pick = home_routes._select_smart_pick(["camera"], [row])
    assert pick["verdict_short"] is None, (
        "RED: verdict_short names only the loser: %r" % pick["verdict_short"]
    )
    assert pick["reason_key"] == RECENT


@pytest.mark.parametrize("flag", [None, "false"], ids=["caption_unset", "caption_false"])
def test_verdict_short_flag_off_keeps_declaration(monkeypatch, flag):
    """D2 PIN/KILL - caption flag OFF: the declaration (== the winner name here) is
    today's caption, even when the row carries a factual_verdict.line1.
    KILL: verdict_short sourced from anything but the declaration (at the fix:
    `smart_pick_verdict_caption_enabled()` forced True)."""
    _set(monkeypatch, CAPTION_FLAG, flag)
    row = _pick_row(("Apple", "iPhone 15"), ("Samsung", "Galaxy S24"),
                    declaration="Apple iPhone 15", line1="Sharper photos and a faster chip.",
                    reason="Longer software support.")
    pick = home_routes._select_smart_pick(["camera"], [row])
    assert pick["verdict_short"] == "Apple iPhone 15"


@pytest.mark.parametrize("winner,loser,declaration", [
    (("Apple", "iPhone 15 Pro"), ("Apple", "iPhone 15"), "iPhone 15 Pro edges the iPhone 15"),
    (("Apple", "iPhone 15"), ("Apple", "iPhone 15 Pro"), "iPhone 15 edges the iPhone 15 Pro"),
    (("Samsung", "Galaxy S25 Ultra"), ("Samsung", "Galaxy S25"), "Galaxy S25 Ultra"),
], ids=["winner_superset_both_named", "loser_superset_both_named", "winner_superset_winner_only"])
def test_loser_guard_keeps_captions_naming_both(winner, loser, declaration):
    """D3 PIN (K10) - a caption naming BOTH products, or only the winner whose name
    CONTAINS the loser's, is kept.
    KILL (at the fix): the loser guard without its "and not the winner" clause."""
    pick = home_routes._select_smart_pick(["camera"], [_pick_row(winner, loser, declaration=declaration)])
    assert pick["verdict_short"] == declaration


def test_loser_guard_masks_the_longer_name_first():
    """D3b RED (K10) - winner `Galaxy S25`, loser `Galaxy S25 Ultra`, caption
    "Galaxy S25 Ultra": the winner's name is a substring of the loser's, so plain
    containment keeps a caption naming ONLY the loser. Longest-first masking drops
    it. RED at HEAD (no guard at all)."""
    row = _pick_row(("Samsung", "Galaxy S25"), ("Samsung", "Galaxy S25 Ultra"),
                    declaration="Galaxy S25 Ultra")
    pick = home_routes._select_smart_pick(["camera"], [row])
    assert pick["verdict_short"] is None, (
        "RED: a caption naming only the (superset-named) loser shipped: %r" % pick["verdict_short"]
    )
    assert pick["reason_key"] == RECENT


def test_caption_flag_on_prefers_factual_verdict_line1(monkeypatch):
    """D4 RED (K3) - caption flag ON, the row carries BOTH a factual_verdict.line1
    and a clean reason: line1 wins. RED at HEAD (the declaration ships)."""
    monkeypatch.setenv(CAPTION_FLAG, "true")
    row = _pick_row(("Apple", "iPhone 15"), ("Samsung", "Galaxy S24"),
                    declaration="Apple iPhone 15", line1="Sharper photos and a faster chip.",
                    reason="Longer software support.")
    pick = home_routes._select_smart_pick(["camera"], [row])
    assert pick["verdict_short"] == "Sharper photos and a faster chip.", (
        "RED: caption flag ON does not source factual_verdict.line1 (got %r)" % pick["verdict_short"]
    )


def test_caption_flag_on_falls_back_to_scrubbed_reason(monkeypatch):
    """D5 RED - caption flag ON, no factual_verdict: the reason goes through
    strip_score_internals ("X scores 73.8 overall." is dropped). RED at HEAD."""
    monkeypatch.setenv(CAPTION_FLAG, "true")
    row = _pick_row(("Apple", "iPhone 15"), ("Samsung", "Galaxy S24"),
                    declaration="Apple iPhone 15",
                    reason="X scores 73.8 overall. Lasts longer on skin.")
    pick = home_routes._select_smart_pick(["camera"], [row])
    assert pick["verdict_short"] == "Lasts longer on skin.", (
        "RED: caption flag ON does not fall back to the scrubbed reason (got %r)" % pick["verdict_short"]
    )


@pytest.mark.parametrize("line1,reason", [
    ("iPhone 15", None),
    (None, "apple  iPhone 15"),
], ids=["line1_is_bare_name", "reason_is_display_name"])
def test_caption_flag_on_tautology_is_none(monkeypatch, line1, reason):
    """D6 RED (K3) - caption flag ON: a line1 (or, separately, a stripped reason)
    whose normalised text equals the winner's bare or display name is a tautology
    -> None. RED at HEAD (the declaration "Apple iPhone 15" ships)."""
    monkeypatch.setenv(CAPTION_FLAG, "true")
    row = _pick_row(("Apple", "iPhone 15"), ("Samsung", "Galaxy S24"),
                    declaration="Apple iPhone 15", line1=line1, reason=reason)
    pick = home_routes._select_smart_pick(["camera"], [row])
    assert pick["verdict_short"] is None, (
        "RED: tautological caption shipped: %r" % pick["verdict_short"]
    )


_READER_TABLE = [
    ("TRUE", True), (" true ", True), ("on", True), ("1", True), ("yes", True),
    (None, False), ("false", False), ("0", False), ("", False),
]


def test_caption_flag_reader(monkeypatch):
    """D7 RED (K5 relabel: new API) - `home_routes.smart_pick_verdict_caption_enabled`
    reads ENABLE_SMART_PICK_VERDICT_CAPTION per call with the
    `.strip().lower() in ("1","true","yes","on")` idiom. Absent at HEAD."""
    reader = getattr(home_routes, "smart_pick_verdict_caption_enabled", None)
    assert callable(reader), "RED: home_routes.smart_pick_verdict_caption_enabled is absent"
    for raw, want in _READER_TABLE:
        _set(monkeypatch, CAPTION_FLAG, raw)
        assert reader() is want, (raw, want)


# ===========================================================================
# E - scrub observability on the sync builder (UNFLAGGED)
# ===========================================================================

def _ab_build(comparison, winner_index=0):
    return build_comparison_response(
        product_data=[{"name": "Alpha", "brand": "A"}, {"name": "Beta", "brand": "B"}],
        comparison=comparison,
        scoring_result={"scores": {"product_0": {"overall": 70}, "product_1": {"overall": 60}},
                        "winner_index": winner_index, "win_margin": 10.0},
        product_names=["Alpha", "Beta"],
        category_used="electronics",
    )


def test_scrubbed_reason_sets_metadata_flag_and_logs(caplog):
    """E1 RED - a winner_reason the strip empties sets metadata.verdict_scrubbed and
    logs ONE `[VERDICT_SCRUB]` WARNING. RED at HEAD (silent)."""
    caplog.set_level(logging.WARNING)
    res = _ab_build({"winner_index": 0, "winner_reason": "Alpha scores 73.8 overall."})
    assert res["overview"]["winner"]["reason"] == "Alpha is the stronger overall pick."
    assert res["metadata"].get("verdict_scrubbed") is True, "RED: metadata.verdict_scrubbed absent"
    assert len(_scrub_records(caplog)) == 1, "RED: no %s WARNING" % SCRUB_TAG


def test_clean_reason_has_no_metadata_key_and_no_log(caplog):
    """E2 PIN - a clean reason: the key is ABSENT (never False) and nothing logs."""
    caplog.set_level(logging.WARNING)
    res = _ab_build({"winner_index": 0, "winner_reason": "Alpha lasts longer."})
    assert res["overview"]["winner"]["reason"] == "Alpha lasts longer."
    assert "verdict_scrubbed" not in res["metadata"]
    assert _scrub_records(caplog) == []


def test_reconcile_dropped_reason_is_not_counted(caplog):
    """E3 PIN (K11) - GPT 1 / scoring 0 with a SCORE-LEAKING winner_reason: the
    reconcile replaces it with the qualitative fallback before the scrub sees it,
    so it is not counted as a scrub (key absent, no `[VERDICT_SCRUB]`)."""
    caplog.set_level(logging.WARNING)
    res = _ab_build({"winner_index": 1, "winner_reason": "Beta scores 73.8 overall."}, winner_index=0)
    assert res["overview"]["winner"]["product_index"] == 0
    assert res["overview"]["winner"]["reason"] == "Alpha is the stronger overall pick."
    assert "verdict_scrubbed" not in res["metadata"]
    assert _scrub_records(caplog) == []


@pytest.mark.asyncio
async def test_partially_stripped_reason_is_not_counted(caplog):
    """E4 PIN (spec 4.1: True iff the strip EMPTIED the reason) - a reason that
    keeps a clean sentence ("It has the sharper camera.") is not counted, on the
    sync builder and on the SSE path (LEAKY). Kills "helper returns True
    unconditionally" beside E2/E3."""
    caplog.set_level(logging.WARNING)
    res = _ab_build({"winner_index": 0, "winner_reason": "Alpha scores 73.8 overall. Lasts longer."})
    assert res["overview"]["winner"]["reason"] == "Lasts longer."
    assert "verdict_scrubbed" not in res["metadata"]
    frames = await _stream(LEAKY, _sse_scoring(0))
    assert "verdict_scrubbed" not in _frame(frames, "complete")["metadata"]
    assert _scrub_records(caplog) == []


# ===========================================================================
# F - ENABLE_SINGLE_VERDICT_MARGIN (default OFF)
# ===========================================================================

def _margin_build(overall, winner_index=0, win_margin=None, n=2, **kw):
    products = [{"name": "A", "brand": "X"}, {"name": "B", "brand": "Y"}][:n]
    if win_margin is None:
        win_margin = round(abs(overall[0] - overall[1]), 1)
    return build_comparison_response(
        product_data=products,
        comparison={"winner_index": winner_index},
        scoring_result={"scores": {"product_0": {"overall": overall[0]},
                                   "product_1": {"overall": overall[1]}},
                        "winner_index": winner_index, "win_margin": win_margin},
        category_used="electronics",
        **kw,
    )


def test_single_margin_overview_equals_scoring_v2(monkeypatch):
    """F1 RED (margin ON) - raw 83.0/49.6: overview.winner.margin and
    scoring_v2.win_margin are both the calibrated gap 16 (86 - 70).
    RED at HEAD: 33.4 vs 16."""
    monkeypatch.setenv(MARGIN_FLAG, "true")
    res = _margin_build((83.0, 49.6))
    assert res["scoring_v2"]["win_margin"] == 16
    assert res["overview"]["winner"]["margin"] == 16, (
        "RED: overview.winner.margin %r != scoring_v2.win_margin 16" % res["overview"]["winner"]["margin"]
    )


@pytest.mark.parametrize("wi", [0, 1])
def test_single_margin_exact_tie_is_zero_everywhere(monkeypatch, wi):
    """F2 RED (margin ON) - raw 57.3/57.3: the PRE-nudge calibrated gap is 0 in both
    margins; the nudged overall_score stays 74/73 (wi 0) / 73/74 (wi 1) - the phones
    need it (W4-12b owns the tie scores). RED at HEAD: scoring_v2.win_margin 1."""
    monkeypatch.setenv(MARGIN_FLAG, "true")
    res = _margin_build((57.3, 57.3), winner_index=wi, win_margin=0.0)
    ov = res["scoring_v2"]["overall_score"]
    assert (ov["product_a"], ov["product_b"]) == ((74, 73) if wi == 0 else (73, 74))
    assert res["overview"]["winner"]["margin"] == 0
    assert res["scoring_v2"]["win_margin"] == 0, (
        "RED: scoring_v2.win_margin is the post-nudge %r, not the honest 0" % res["scoring_v2"]["win_margin"]
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("overall,raw_margin,want", [
    ((78, 72), 6, 3),
    ((57.3, 57.3), 0.0, 0),
], ids=["78_72", "tie_57_3"])
async def test_single_margin_sse_verdict_equals_complete(monkeypatch, overall, raw_margin, want):
    """F3 RED (margin ON, + K8 tie case) - verdict margin == complete
    overview.winner.margin == complete scoring_v2.win_margin == the pre-nudge
    calibrated gap. RED at HEAD: verdict/overview raw (6 / 0.0), scoring_v2 3 / 1."""
    monkeypatch.setenv(MARGIN_FLAG, "true")
    frames = await _stream(CLEAN, _sse_scoring(0, overall=overall, win_margin=raw_margin))
    v, c = _frame(frames, "verdict"), _frame(frames, "complete")
    got = (v["winner"]["margin"], c["overview"]["winner"]["margin"], c["scoring_v2"]["win_margin"])
    assert got == (want, want, want), "RED: (verdict, overview, scoring_v2) margins = %r" % (got,)


@pytest.mark.asyncio
@pytest.mark.parametrize("flag", [None, "false"], ids=["margin_unset", "margin_false"])
async def test_margin_flag_off_is_today(monkeypatch, flag):
    """F4 PIN/KILL (margin OFF) - today's two margins: 33.4 & 16; tie 0.0 & 1 with
    74/73; SSE verdict 6 (complete overview 6, scoring_v2 3).
    KILL: overview.winner.margin := scoring_v2.win_margin unconditionally (at the
    fix: `single_verdict_margin_enabled()` forced True)."""
    _set(monkeypatch, MARGIN_FLAG, flag)
    res = _margin_build((83.0, 49.6))
    assert (res["overview"]["winner"]["margin"], res["scoring_v2"]["win_margin"]) == (33.4, 16)
    tie = _margin_build((57.3, 57.3), win_margin=0.0)
    assert (tie["overview"]["winner"]["margin"], tie["scoring_v2"]["win_margin"]) == (0.0, 1)
    assert tie["scoring_v2"]["overall_score"]["product_a"] == 74
    assert tie["scoring_v2"]["overall_score"]["product_b"] == 73
    frames = await _stream(CLEAN, _sse_scoring(0))
    v, c = _frame(frames, "verdict"), _frame(frames, "complete")
    assert (v["winner"]["margin"], c["overview"]["winner"]["margin"], c["scoring_v2"]["win_margin"]) == (6, 6, 3)


def test_single_margin_leaves_partial_and_short_payloads_alone(monkeypatch):
    """F5 PIN (margin ON) - no second margin to disagree with: len(product_data) < 2
    -> scoring_v2 == {} and the overview margin stays raw; an honest partial
    (ENABLE_HONEST_PARTIAL_SCORING + metadata.partial + scoring_result={}) ->
    scoring_v2 None and the overview margin stays today's value."""
    monkeypatch.setenv(MARGIN_FLAG, "true")
    short = _margin_build((83.0, 49.6), win_margin=12.5, n=1)
    assert short["scoring_v2"] == {}
    assert short["overview"]["winner"]["margin"] == 12.5
    monkeypatch.setenv("ENABLE_HONEST_PARTIAL_SCORING", "true")
    partial = build_comparison_response(
        product_data=[{"name": "A", "brand": "X"}, {"name": "B", "brand": "Y"}],
        comparison={"winner_index": 0},
        scoring_result={},
        category_used="electronics",
        metadata={"partial": True},
    )
    assert partial["scoring_v2"] is None
    assert partial["overview"]["winner"]["margin"] == 0


@pytest.mark.asyncio
async def test_scores_event_keeps_raw_win_margin(monkeypatch):
    """F6 PIN/KILL (margin ON) - the `scores` SSE event keeps the RAW win_margin
    beside the RAW scores it ships.
    KILL: route the calibrated gap into the scores event."""
    monkeypatch.setenv(MARGIN_FLAG, "true")
    frames = await _stream(CLEAN, _sse_scoring(0))
    assert _frame(frames, "scores")["win_margin"] == 6


def test_single_margin_reader(monkeypatch):
    """F7 RED (K5 relabel: new API) - `response_builder.single_verdict_margin_enabled`
    reads ENABLE_SINGLE_VERDICT_MARGIN per call (the idiom); and `_build_scoring_v2`
    called WITHOUT the new keyword keeps the post-nudge value under the flag ON (the
    keyword, not the env, decides inside the helper). Reader absent at HEAD."""
    monkeypatch.setenv(MARGIN_FLAG, "true")
    direct = _build_scoring_v2(
        [{"name": "A"}, {"name": "B"}],
        {"scores": {"product_0": {"overall": 57.3}, "product_1": {"overall": 57.3}},
         "winner_index": 0, "win_margin": 0.0},
        "electronics", 0,
    )
    assert direct["win_margin"] == 1
    reader = getattr(rb, "single_verdict_margin_enabled", None)
    assert callable(reader), "RED: response_builder.single_verdict_margin_enabled is absent"
    for raw, want in _READER_TABLE:
        _set(monkeypatch, MARGIN_FLAG, raw)
        assert reader() is want, (raw, want)


@pytest.mark.asyncio
async def test_single_margin_read_once_per_stream(monkeypatch):
    """F8 RED (K12) - the margin flag is read ONCE per streaming request and routed
    into the builder: flipping the env OFF between the `verdict` frame and the
    builder call must not split verdict from complete. RED at HEAD (no flag: the
    verdict/overview margins are raw 6, scoring_v2 3)."""
    monkeypatch.setenv(MARGIN_FLAG, "true")

    def _flip(event_type):
        if event_type == "verdict":
            monkeypatch.delenv(MARGIN_FLAG, raising=False)

    frames = await _stream(CLEAN, _sse_scoring(0), on_frame=_flip)
    v, c = _frame(frames, "verdict"), _frame(frames, "complete")
    got = (v["winner"]["margin"], c["overview"]["winner"]["margin"], c["scoring_v2"]["win_margin"])
    assert got == (3, 3, 3), "RED: margins split across one request: %r" % (got,)


# ===========================================================================
# R-idempotence (ruling) - the double application (scs, then builder) is byte-safe
# only because strip_score_internals is idempotent
# ===========================================================================

def _unit_strings():
    out = []

    def walk(x):
        if isinstance(x, str):
            out.append(x)
        elif isinstance(x, dict):
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)

    for fx in (LEAKY, CLEAN, _leaky_summary(), _consensus_only_summary(), _QUOTES):
        walk(fx)
    out += [
        "Sharper camera.  Faster chip.",
        "A.\nB.",
        "  Lasts longer on skin.  ",
        "X scores 73.8 overall. Lasts longer on skin.",
        "Alpha scores 73.8 overall. Beta trails by 12 points. Lasts longer.",
        "Alpha scores 73.8 overall.",
        "Maabooch Kuwaiti Red 250g brings more heat.",
        "",
    ]
    return out


def test_strip_score_internals_is_idempotent_over_unit_fixtures():
    """R-idempotence PIN/KILL - strip(strip(x)) == strip(x) over every string this
    unit feeds the scrub. KILL: a strip that drops only the FIRST leaking sentence
    per call (the two-leak fixture then changes on the second pass)."""
    bad = [x for x in _unit_strings()
           if strip_score_internals(strip_score_internals(x)) != strip_score_internals(x)]
    assert bad == []


# ===========================================================================
# Fix round (post-adversary Fable rulings R8-R11, 2026-09-26). Every test here is
# a PIN/KILL: green on the fix-round bytes, red under the named mutant.
# ===========================================================================

# A winner whose display name itself trips the score-internals strip
# ("5-Point" matches the "N-point" pattern), so the qualitative fallback that
# names it is emptied too - the adversary's probe shape. Pre-existing false
# positive, follow-up W4-12g.
GRACO_PAIRS = [("Graco", "4Ever 5-Point Harness Seat"), ("Chicco", "Fit")]
GRACO = "Graco 4Ever 5-Point Harness Seat"
GRACO_FALLBACK = GRACO + " is the stronger overall pick."


def _assert_graco_premise():
    assert strip_score_internals(GRACO_FALLBACK) == "", (
        "fixture premise changed (W4-12g fixed?): the Graco fallback no longer trips the strip, "
        "so the R8 pins below no longer exercise our-own-text exclusion"
    )


def _graco_build(comparison, scoring_winner):
    return build_comparison_response(
        product_data=[{"name": "4Ever 5-Point Harness Seat", "brand": "Graco"},
                      {"name": "Fit", "brand": "Chicco"}],
        comparison=comparison,
        scoring_result={"scores": {"product_0": {"overall": 70 if scoring_winner == 0 else 60},
                                   "product_1": {"overall": 60 if scoring_winner == 0 else 70}},
                        "winner_index": scoring_winner, "win_margin": 10.0},
        product_names=[GRACO, "Chicco Fit"],
        category_used="electronics",
    )


@pytest.mark.parametrize("reconcile", [None, "true"], ids=["reconcile_off", "reconcile_on"])
def test_r8_sync_mismatch_clean_reason_not_counted(monkeypatch, caplog, reconcile):
    """R8 p1 PIN/KILL - sync path, GPT 1 / scoring 0 with a CLEAN reason: the
    reconcile replaces it (qualitative fallback, or with ENABLE_WINNER_PROSE_RECONCILE
    the deterministic "edges ahead" reason) before the scrub; the strip then empties
    OUR text because the winner's name trips it. Our own text is never counted:
    no metadata key, no `[VERDICT_SCRUB]` line. The payload text is unchanged.
    KILL: drop the own-text exclusion in scrub_verdict_prose."""
    _assert_graco_premise()
    _set(monkeypatch, "ENABLE_WINNER_PROSE_RECONCILE", reconcile)
    caplog.set_level(logging.WARNING)
    res = _graco_build({"winner_index": 1, "winner_reason": "Chicco Fit is lighter."}, 0)
    assert res["overview"]["winner"]["product_index"] == 0
    assert res["overview"]["winner"]["reason"] == GRACO_FALLBACK
    assert "verdict_scrubbed" not in res["metadata"], "our own fallback was counted as a GPT scrub"
    assert _scrub_records(caplog) == []


@pytest.mark.asyncio
async def test_r8_sse_agree_fully_leaking_reason_counted_once(caplog):
    """R8 p2 PIN/KILL - SSE, GPT and scoring agree, the GPT reason fully leaks: the
    scs call counts it and logs it ONCE (the dropped text is GPT's); the builder's
    second call sees our fallback write-back and counts nothing, even though the
    strip empties that fallback too. Exactly one `[VERDICT_SCRUB]` line per request.
    KILL: drop the own-text exclusion (the builder logs a second line)."""
    _assert_graco_premise()
    caplog.set_level(logging.WARNING)
    comp = {"winner_index": 0, "winner_reason": "It scores 73.8 overall.",
            "winner_declaration": "Graco 4Ever", "key_tradeoff": ""}
    frames = await _stream(comp, _sse_scoring(0), pairs=GRACO_PAIRS)
    v, c = _frame(frames, "verdict"), _frame(frames, "complete")
    assert v["winner"]["reason"] == c["overview"]["winner"]["reason"] == GRACO_FALLBACK
    assert c["metadata"].get("verdict_scrubbed") is True
    recs = _scrub_records(caplog)
    assert len(recs) == 1, "expected exactly one %s line, got %d" % (SCRUB_TAG, len(recs))
    assert "It scores 73.8 overall." in recs[0].getMessage()
    assert "stronger overall pick" not in recs[0].getMessage().split("dropped=", 1)[1]


@pytest.mark.asyncio
async def test_r8_sse_mismatch_fully_leaking_reason_not_counted(caplog):
    """R8 p3 PIN/KILL (E3's SSE twin) - SSE, GPT 1 / scoring 0 with a FULLY leaking
    reason: the reconcile replaces it BEFORE the scrub, so it is not counted (no
    metadata key, 0 `[VERDICT_SCRUB]` lines) - also with a winner whose fallback
    trips the strip. Pins the scs call ORDER.
    KILL: N4 - scs calls scrub_verdict_prose BEFORE reconcile_winner_prose."""
    _assert_graco_premise()
    caplog.set_level(logging.WARNING)
    comp = {"winner_index": 1, "winner_reason": "Chicco Fit scores 81 overall.",
            "winner_declaration": "Chicco Fit", "key_tradeoff": "Graco trails on weight."}
    frames = await _stream(comp, _sse_scoring(0), pairs=GRACO_PAIRS)
    v, c = _frame(frames, "verdict"), _frame(frames, "complete")
    assert v["winner"]["product_index"] == 0
    assert v["winner"]["reason"] == c["overview"]["winner"]["reason"] == GRACO_FALLBACK
    assert "verdict_scrubbed" not in c["metadata"], "a reconcile-replaced reason was counted"
    assert "verdict_scrubbed" not in _frame(frames, "settle_complete")["metadata"]
    assert _scrub_records(caplog) == []


def test_r9_sync_fallback_names_the_reconciled_winner(caplog):
    """R9 PIN/KILL (#99 class) - winner_index 1 with a fully leaking reason: the
    qualitative fallback in overview.winner.reason, recommendation and the BC
    comparison.winner_reason names PRODUCT 1, never product 0.
    KILL: N5 - the helper takes its fallback name from product_names[0]."""
    caplog.set_level(logging.WARNING)
    res = _ab_build({"winner_index": 1, "winner_reason": "Beta scores 73.8 overall."}, winner_index=1)
    want = "Beta is the stronger overall pick."
    got = (res["overview"]["winner"]["reason"], res["recommendation"], res["comparison"]["winner_reason"])
    assert got == (want, want, want), "fallback does not name the reconciled winner: %r" % (got,)
    assert not any("Alpha" in s for s in got)
    assert res["overview"]["winner"]["product_index"] == 1
    assert res["metadata"].get("verdict_scrubbed") is True
    assert len(_scrub_records(caplog)) == 1


@pytest.mark.asyncio
async def test_r9_sse_fallback_names_the_reconciled_winner():
    """R9 PIN/KILL - the same on the SSE verdict frame (and its complete twin):
    scoring and GPT both pick product 1, its reason fully leaks; every fallback
    string names "Samsung Galaxy S24", never "Apple iPhone 15".
    KILL: N5 (fallback from product_names[0])."""
    comp = {"winner_index": 1, "winner_reason": "Galaxy S24 scores 78 overall.",
            "winner_declaration": "", "key_tradeoff": ""}
    frames = await _stream(comp, _sse_scoring(1, overall=(72, 78)))
    v, c = _frame(frames, "verdict"), _frame(frames, "complete")
    want = "Samsung Galaxy S24 is the stronger overall pick."
    got = (v["winner"]["reason"], v["recommendation"], (v.get("comparison") or {}).get("winner_reason"),
           c["overview"]["winner"]["reason"], c["recommendation"], c["comparison"]["winner_reason"])
    assert got == (want,) * 6, "fallback does not name the reconciled winner: %r" % (got,)
    assert not any("iPhone" in s for s in got)
    assert v["winner"]["product_index"] == 1


def test_r10_absent_keys_stay_absent():
    """R10 PIN/KILL (spec 4.1 key-present rule) - a comparison WITHOUT
    key_tradeoff / winner_declaration: the scrub never creates either key on the
    BC comparison alias. KILL: N2 (key_tradeoff written unconditionally) /
    N3 (winner_declaration written unconditionally)."""
    res = _ab_build({"winner_index": 0, "winner_reason": "Alpha lasts longer."})
    assert "key_tradeoff" not in res["comparison"]
    assert "winner_declaration" not in res["comparison"]


@pytest.mark.asyncio
async def test_r10_absent_keys_stay_absent_on_the_verdict_frame():
    """R10 PIN/KILL - the same on the SSE verdict frame's comparison alias and the
    complete comparison. KILL: N2 / N3."""
    comp = copy.deepcopy(CLEAN)
    del comp["key_tradeoff"]
    del comp["winner_declaration"]
    frames = await _stream(comp, _sse_scoring(0))
    for name in ("verdict", "complete"):
        fr = _frame(frames, name)
        alias = fr.get("comparison") or {}
        assert "key_tradeoff" not in alias, name
        assert "winner_declaration" not in alias, name


def test_r10_present_leaking_keys_are_rewritten():
    """R10 PIN - both keys present and leaking: key_tradeoff (fully leaking) is
    emptied and winner_declaration (partly leaking) keeps only its clean sentence."""
    res = _ab_build({"winner_index": 0, "winner_reason": "Alpha lasts longer.",
                     "key_tradeoff": "Beta trails by 12 points.",
                     "winner_declaration": "Alpha is sharper. Presentation score of 100."})
    assert res["comparison"]["key_tradeoff"] == ""
    assert res["comparison"]["winner_declaration"] == "Alpha is sharper."
    assert res["overview"]["winner"]["key_tradeoff"] == ""
    assert res["overview"]["winner"]["name"] == "Alpha is sharper."


@pytest.mark.parametrize("winner,loser,declaration", [
    (("Nike", "Air Max 90"), ("Nike", "Air"), "Airy cushioning wins"),
    (("Samsung", "Galaxy S25+"), ("Samsung", "Galaxy S25"), "Galaxy S25 Plus"),
    (("Samsung", "Galaxy S25+"), ("Samsung", "Galaxy S25"), "Samsung Galaxy S25+ 256GB"),
    (("Dior", "Sauvage Elixir"), ("Dior", "Sauvage"), "Sauvage Elixir 60ml"),
], ids=["airy_not_a_token_match", "galaxy_shared_form", "galaxy_display", "elixir_ml"])
def test_r11_loser_guard_keeps_captions_that_do_not_name_only_the_loser(winner, loser, declaration):
    """R11 PIN/KILL - the unflagged loser guard matches names on whole TOKENS
    ("air" is not in "Airy") and keeps any caption that names the winner. Since
    R13 "+" is the token "plus", so winner "Galaxy S25+" tokenises to
    "galaxy s25 plus" (no longer a form shared with loser "Galaxy S25"): the
    longer winner form masks "Galaxy S25 Plus" first and the caption is kept.
    KILL: plain substring matching (airy row red). The both-match clause is now
    pinned by test_r13_identical_names_keep_the_caption."""
    pick = home_routes._select_smart_pick(["camera"], [_pick_row(winner, loser, declaration=declaration)])
    assert pick["verdict_short"] == declaration


def test_r11_conservative_drop_is_documented():
    """R11 PIN (documented conservative drop) - winner "Sauvage Elixir", loser
    "Sauvage", caption "The Elixir concentration of Sauvage": the caption names only
    the loser as a whole name (the winner's name is not contiguous in it), so it is
    dropped and the card renders the reason_key copy, like measured rows 12 and 13."""
    row = _pick_row(("Dior", "Sauvage Elixir"), ("Dior", "Sauvage"),
                    declaration="The Elixir concentration of Sauvage")
    pick = home_routes._select_smart_pick(["camera"], [row])
    assert pick["verdict_short"] is None
    assert pick["reason_key"] == RECENT


# ===========================================================================
# Fix round 2 (Fable rulings R13-R14, 2026-09-26). PIN/KILL: green on the
# fix-round-2 bytes, red under the named mutant.
# ===========================================================================

_GALAXY = ("Samsung", "Galaxy S25")
_GALAXY_PLUS = ("Samsung", "Galaxy S25+")
_GALAXY_FW_PLUS = ("Samsung", "Galaxy S25\uff0b")  # fullwidth plus sign (escaped: the file stays ASCII, R18)


def _verdict_short_of(winner, loser, declaration):
    pick = home_routes._select_smart_pick(["camera"], [_pick_row(winner, loser, declaration=declaration)])
    return pick["verdict_short"], pick["reason_key"]


def test_r13_plus_is_its_own_token():
    """R13 PIN/KILL - a "+" or fullwidth plus glued to the name (R17) becomes the
    token "plus" before the punctuation drop, so "Galaxy S25+" and "Galaxy S25"
    never share a token form.
    KILL: drop the + -> plus mapping."""
    assert home_routes._name_tokens("Galaxy S25+") == "galaxy s25 plus"
    assert home_routes._name_tokens("Galaxy S25\uff0b") == "galaxy s25 plus"
    assert home_routes._name_tokens("Galaxy S25") == "galaxy s25"
    assert not (home_routes._product_name_token_forms({"brand": "Samsung", "name": "Galaxy S25+"})
                & home_routes._product_name_token_forms({"brand": "Samsung", "name": "Galaxy S25"}))


@pytest.mark.parametrize("winner,loser,declaration,kept", [
    (_GALAXY_PLUS, _GALAXY, "Galaxy S25 Plus", True),
    (_GALAXY_PLUS, _GALAXY, "Galaxy S25", False),
    (_GALAXY, _GALAXY_PLUS, "Galaxy S25+", False),
    (_GALAXY, _GALAXY_PLUS, "Samsung Galaxy S25+ wins", False),
    (_GALAXY_FW_PLUS, _GALAXY, "Galaxy S25 Plus", True),
    (_GALAXY, _GALAXY_FW_PLUS, "Galaxy S25+", False),
], ids=["w_plus_caption_plus_kept", "w_plus_caption_loser_dropped",
        "l_plus_caption_loser_dropped", "l_plus_display_caption_dropped",
        "w_fullwidth_plus_kept", "l_fullwidth_plus_dropped"])
def test_r13_plus_variants_stay_distinct(winner, loser, declaration, kept):
    """R13 PIN/KILL (#99 class on the S2x / S2x+ pair) - the four ruled Galaxy
    cases (plus two fullwidth-plus twins) resolve by R11's rules once "+" is a
    token: a caption naming only the loser's exact name is DROPPED in both
    directions (the card renders the recent_winner copy), "Galaxy S25 Plus" on the
    S25+ winner's tile is KEPT (the longer winner form masks it).
    KILL: drop the + -> plus mapping (w_plus_caption_plus_kept red: the
    punctuation-kept fallback then reads "Galaxy S25 Plus" as the loser)."""
    got, reason_key = _verdict_short_of(winner, loser, declaration)
    if kept:
        assert got == declaration
    else:
        assert got is None, "a caption naming only the loser shipped: %r" % (got,)
        assert reason_key == RECENT


_WH_W = ("Sony", "WH-1000XM5")
_WH_L = ("Sony", "WH 1000XM5")


@pytest.mark.parametrize("declaration,kept", [
    ("WH 1000XM5", False),
    ("Sony WH 1000XM5 is lighter", False),
    ("WH-1000XM5", True),
], ids=["loser_exact_dropped", "loser_display_dropped", "winner_exact_kept"])
def test_r13_token_collision_falls_back_to_whitespace_normalised_names(declaration, kept):
    """R13 PIN/KILL (safety net, synthetic collision) - "WH-1000XM5" and
    "WH 1000XM5" are two display names whose token forms still collide
    ("wh 1000xm5"). The guard then compares the whitespace-normalised names, so a
    caption naming only the loser is still dropped instead of the collision
    silently turning the guard off.
    KILL: drop the collision fallback (both loser rows red)."""
    assert (home_routes._product_name_token_forms({"brand": _WH_W[0], "name": _WH_W[1]})
            & home_routes._product_name_token_forms({"brand": _WH_L[0], "name": _WH_L[1]})), (
        "fixture premise changed: the two names no longer collide in token form")
    got, reason_key = _verdict_short_of(_WH_W, _WH_L, declaration)
    if kept:
        assert got == declaration
    else:
        assert got is None, "a collision turned the loser guard off: %r" % (got,)
        assert reason_key == RECENT


def test_r13_identical_names_keep_the_caption():
    """R11/R13/R19 PIN/KILL - two products with the SAME name in every form: every
    form is shared, so no form is evidence for either side (R19) and the caption is
    kept (the guard cannot tell them apart).
    KILL: a shared form credited to the loser only (red: the caption is dropped)."""
    got, _ = _verdict_short_of(_GALAXY, _GALAXY, "Galaxy S25")
    assert got == "Galaxy S25"


@pytest.mark.parametrize("reconcile", [None, "true"], ids=["reconcile_off", "reconcile_on"])
def test_r14_own_text_exclusion_is_keyed_on_the_reconciled_winner(monkeypatch, caplog, reconcile):
    """R14 PIN/KILL - R8's p1 shape with the Graco pair REVERSED: Graco is product
    1 and the reconciled (scoring) winner, GPT picked product 0 with a clean
    reason. The reconcile replaces it with GRACO's text (the qualitative fallback,
    or with ENABLE_WINNER_PROSE_RECONCILE the deterministic reason), the strip
    empties it because Graco's name trips it, and that is OUR text for the
    reconciled winner: no metadata key, no `[VERDICT_SCRUB]` line, the served
    reason is Graco's fallback.
    KILL: X1 - `_own_texts` built from product_names[0] (Chicco) instead of the
    reconciled winner."""
    _assert_graco_premise()
    _set(monkeypatch, "ENABLE_WINNER_PROSE_RECONCILE", reconcile)
    caplog.set_level(logging.WARNING)
    res = build_comparison_response(
        product_data=[{"name": "Fit", "brand": "Chicco"},
                      {"name": "4Ever 5-Point Harness Seat", "brand": "Graco"}],
        comparison={"winner_index": 0, "winner_reason": "Chicco Fit is lighter."},
        scoring_result={"scores": {"product_0": {"overall": 60}, "product_1": {"overall": 70}},
                        "winner_index": 1, "win_margin": 10.0},
        product_names=["Chicco Fit", GRACO],
        category_used="electronics",
    )
    assert res["overview"]["winner"]["product_index"] == 1
    assert res["overview"]["winner"]["reason"] == GRACO_FALLBACK
    assert "verdict_scrubbed" not in res["metadata"], "the reconciled winner's own fallback was counted"
    assert _scrub_records(caplog) == []


# ===========================================================================
# Fix round 3 (Fable rulings R16-R17, 2026-09-26). PIN/KILL: green on the
# fix-round-3 bytes, red under the named mutant.
# ===========================================================================

_NINJA = ("Ninja", "Air Fryer")
_PHILIPS = ("Philips", "Air Fryer")


def _prod(pair):
    return {"brand": pair[0], "name": pair[1]}


def test_r19_safety_net_premise():
    """R19 PIN (replaces the R16 `_names_collide` premise pin; R19 folds the
    trigger into "no distinguishing form remains"). "WH-1000XM5" / "WH 1000XM5"
    share EVERY token form, so no distinguishing token form remains and the guard
    falls back to the punctuation-kept forms. Ninja / Philips "Air Fryer" share
    only the bare-name token form, so each keeps a distinguishing display form and
    the guard stays on the token path."""
    wh_w = home_routes._product_name_token_forms(_prod(_WH_W))
    wh_l = home_routes._product_name_token_forms(_prod(_WH_L))
    assert wh_w and wh_w == wh_l, "fixture premise changed: the WH pair is no longer token-identical"
    ninja = home_routes._product_name_token_forms(_prod(_NINJA))
    philips = home_routes._product_name_token_forms(_prod(_PHILIPS))
    assert ninja & philips == {"air fryer"}
    assert ninja - philips == {"ninja air fryer"} and philips - ninja == {"philips air fryer"}


@pytest.mark.parametrize("declaration", [
    "Philips' Air Fryer is quieter",
    "Philips\u2122 Air Fryer",
    "Philips-Air Fryer wins",
], ids=["apostrophe", "trademark_sign", "hyphen"])
def test_r16_shared_name_form_stays_on_the_token_path(declaration):
    """R16 PIN/KILL - winner Ninja "Air Fryer" / loser Philips "Air Fryer": a shared
    bare name is not a collision, so the guard stays on R11's token path, where
    the loser's display name "Philips Air Fryer" masks first and nothing of the
    winner remains. Each caption names only the loser -> DROPPED (as fix round 1
    had them). The trademark sign is written as an escape (R18). Under R19 the
    shared "air fryer" is evidence for neither side and each keeps its display form.
    KILL: the broad `loser_forms & winner_forms` fallback trigger (all three rows
    red: the punctuation-kept fallback misses the punctuated loser display name)."""
    got, reason_key = _verdict_short_of(_NINJA, _PHILIPS, declaration)
    assert got is None, "a caption naming only the loser shipped: %r" % (got,)
    assert reason_key == RECENT


def test_r17_free_standing_plus_is_prose():
    """R17 PIN/KILL - the plus token is a NAME plus: only a "+" glued to the
    preceding letter or digit becomes "plus". Winner "iPad" / loser "iPad Plus" /
    caption "iPad + keyboard bundle wins": the free-standing " + " stays
    punctuation, the caption names the winner only -> KEPT.
    KILL: map every "+" to "plus" (red: the caption then reads "ipad plus ...",
    which names only the loser)."""
    got, _ = _verdict_short_of(("Apple", "iPad"), ("Apple", "iPad Plus"), "iPad + keyboard bundle wins")
    assert got == "iPad + keyboard bundle wins"
    assert home_routes._name_tokens("iPad + keyboard bundle wins") == "ipad keyboard bundle wins"
    assert home_routes._name_tokens("S25 \uff0b case") == "s25 case"


def test_r17_leading_whole_token_boundary():
    """R17 PIN/KILL (the LEADING whole-token boundary) - loser "Air" / winner
    "Air Max 90" / caption "Repair kit wins the day": "air" at the tail of
    "repair" is not a token match, so the caption does not name the loser -> KEPT.
    KILL: A2 - the lookbehind removed from the whole-token needle."""
    got, _ = _verdict_short_of(("Nike", "Air Max 90"), ("Nike", "Air"), "Repair kit wins the day")
    assert got == "Repair kit wins the day"


# ===========================================================================
# Fix round 4 (Fable ruling R19, 2026-09-26). Shared forms are evidence for
# NEITHER side. PIN/KILL: green on the fix-round-4 bytes, red under the named
# mutant.
# ===========================================================================

_PHILIPS_HYPHEN = ("Philips", "Air-Fryer")


@pytest.mark.parametrize("winner,loser,declaration", [
    (_NINJA, _PHILIPS_HYPHEN, "Philips Air Fryer wins"),
    (_PHILIPS_HYPHEN, _NINJA, "Ninja Air Fryer wins"),
], ids=["w_ninja_l_philips_hyphen", "w_philips_hyphen_l_ninja"])
def test_r19_shared_stem_is_not_winner_evidence(winner, loser, declaration):
    """R19 (a) PIN/KILL - a cross-brand pair whose bare names differ only by
    punctuation ("Air Fryer" / "Air-Fryer"): the stem "air fryer" is SHARED and is
    evidence for neither side, so a caption naming the loser's display name is a
    loser-only caption -> DROPPED, in both directions.
    KILL: today's (round-3) behaviour, the shared stem credited to the winner via
    the collision trigger (first row red)."""
    got, reason_key = _verdict_short_of(winner, loser, declaration)
    assert got is None, "a caption naming only the loser shipped: %r" % (got,)
    assert reason_key == RECENT


def test_r19_shared_stem_beside_the_loser_name_is_not_winner_evidence():
    """R19 (a2) PIN/KILL - the token-path half of (a): the caption names the
    loser's display name AND repeats the shared stem on its own. The stem is
    evidence for neither side, so the caption still names only the loser ->
    DROPPED.
    KILL: shared forms credited to the winner on the token path (red: the lone
    stem then reads as the winner)."""
    got, reason_key = _verdict_short_of(_NINJA, _PHILIPS_HYPHEN,
                                        "Philips Air Fryer beats every other air fryer")
    assert got is None, "a caption naming only the loser shipped: %r" % (got,)
    assert reason_key == RECENT


def test_r19_shared_stem_alone_is_no_evidence():
    """R19 (b) PIN/KILL - the same pair with a caption naming only the shared stem
    (neither distinguishing form): no evidence -> KEPT.
    KILL: shared forms credited to the loser only (red: the caption is dropped)."""
    got, _ = _verdict_short_of(_NINJA, _PHILIPS_HYPHEN, "Air Fryer wins on crisp")
    assert got == "Air Fryer wins on crisp"


def test_r19_punctuation_only_names_keep_the_guard_off():
    """R19 (c) PIN/KILL (the adversary's O2 probe) - winner "!!!", loser "???":
    neither name has a token form, so neither is ever evidence and the guard stays
    OFF: the caption "??? wins" is KEPT.
    KILL: the punctuation-kept fallback also counting forms whose token form is
    empty (red: the caption is dropped)."""
    got, _ = _verdict_short_of(("", "!!!"), ("", "???"), "??? wins")
    assert got == "??? wins"


# ===========================================================================
# Fix round 5 (Fable rulings R21-R22, 2026-09-27). R21: shared forms are MASKED
# in the longest-first pass and credit no one. R22: both halves of the
# `loser_only or winner_only` fallback trigger are pinned. PIN/KILL unless a
# docstring says RED (red on the fix-round-4 bytes).
# ===========================================================================

_XL_NO_BRAND = ("", "Philips Air Fryer XL")
_XL_BRANDED = ("Philips", "Air Fryer XL")
_TF_FULL = ("Tom Ford", "Tom Ford Soleil Neige")
_TF_BARE = ("Tom Ford", "Soleil Neige")


@pytest.mark.parametrize("winner,loser,declaration", [
    (_XL_NO_BRAND, _XL_BRANDED, "Philips Air Fryer XL wins"),
    (_XL_BRANDED, _XL_NO_BRAND, "Philips Air Fryer XL wins"),
    (_TF_FULL, _TF_BARE, "Tom Ford Soleil Neige"),
    (_TF_BARE, _TF_FULL, "Tom Ford Soleil Neige"),
], ids=["xl_w_nobrand_l_branded", "xl_w_branded_l_nobrand",
        "tomford_w_full_l_bare", "tomford_w_bare_l_full"])
def test_r21_identical_display_names_keep_the_caption(winner, loser, declaration):
    """R21 (the round-4 adversary's two identical-display-name cases, both pair
    directions). Both products DISPLAY the same name, split differently between
    brand and name, and the caption names exactly that shared display name. The
    shared form is masked first (it is the longest) and credits no one, so the
    one product's shorter distinguishing bare name, nested inside it, is not
    evidence -> KEPT.
    RED (rows xl_w_nobrand_l_branded and tomford_w_full_l_bare) on the round-4
    bytes, where shared forms were left out of the masking pass and the loser's
    bare name matched inside the unmasked display name; the two mirror rows are
    PIN (kept on the round-4 bytes too, through the winner's bare name).
    KILL: shared forms excluded from the masking pass (whole-file swap to the
    round-4 home_routes fcb4ff6d)."""
    w_forms = home_routes._product_name_token_forms(_prod(winner))
    l_forms = home_routes._product_name_token_forms(_prod(loser))
    shared = w_forms & l_forms
    assert len(shared) == 1 and next(iter(shared)) in home_routes._name_tokens(declaration), (
        "fixture premise changed: the caption no longer names the one shared display name")
    got, _ = _verdict_short_of(winner, loser, declaration)
    assert got == declaration, "a caption naming only the shared display name was dropped"


_AIR_NO_BRAND = ("", "Air Fryer")


def test_r22_winner_without_distinguishing_form_drops_a_loser_caption():
    """R22 (i) PIN/KILL (the round-4 adversary's case) - winner brand '' "Air
    Fryer" / loser Philips "Air-Fryer": the winner has NO distinguishing token form
    (its only form "air fryer" is shared), the loser keeps "philips air fryer".
    The guard must stay on the token path, where the caption "Philips Air Fryer
    wins" names only the loser -> DROPPED.
    KILL: `if loser_only and winner_only:` and `if winner_only:` (red: both send
    the pair to the punctuation-kept fallback, where the caption's "air fryer"
    reads as the winner's raw name and the caption is kept)."""
    w_forms = home_routes._product_name_token_forms(_prod(_AIR_NO_BRAND))
    l_forms = home_routes._product_name_token_forms(_prod(_PHILIPS_HYPHEN))
    assert not (w_forms - l_forms) and (l_forms - w_forms) == {"philips air fryer"}, (
        "fixture premise changed: winner_only must be empty and loser_only non-empty")
    got, reason_key = _verdict_short_of(_AIR_NO_BRAND, _PHILIPS_HYPHEN, "Philips Air Fryer wins")
    assert got is None, "a caption naming only the loser shipped: %r" % (got,)
    assert reason_key == RECENT


@pytest.mark.parametrize("declaration", [
    "Philips Air Fryer wins",
    "Air Fryer wins on crisp",
], ids=["names_the_winner_only", "names_neither"])
def test_r22_loser_without_distinguishing_form_keeps_the_caption(declaration):
    """R22 (ii) PIN/KILL - the mirror pair: winner Philips "Air-Fryer" / loser
    brand '' "Air Fryer". The loser has NO distinguishing token form, the winner
    keeps "philips air fryer". A caption naming only the winner's distinguishing
    form, and a caption naming neither distinguishing form, are both KEPT on the
    token path.
    KILL: `if loser_only:` and `if loser_only and winner_only:` (red: both send the
    pair to the punctuation-kept fallback, where "air fryer" is the loser's raw
    name and matches, while the winner's raw forms keep their hyphen and do not,
    so the caption is dropped).
    (iii) - both sides empty -> the punctuation-kept fallback - is pinned by the
    WH-1000XM5 rows (test_r13_token_collision_falls_back_to_whitespace_normalised_names)."""
    w_forms = home_routes._product_name_token_forms(_prod(_PHILIPS_HYPHEN))
    l_forms = home_routes._product_name_token_forms(_prod(_AIR_NO_BRAND))
    assert not (l_forms - w_forms) and (w_forms - l_forms) == {"philips air fryer"}, (
        "fixture premise changed: loser_only must be empty and winner_only non-empty")
    got, _ = _verdict_short_of(_PHILIPS_HYPHEN, _AIR_NO_BRAND, declaration)
    assert got == declaration
