"""B1 RESULT-STATUS + TELEMETRY (S80, ENABLE_RESULT_STATUS_METADATA) -- RED and PIN rows.

Spec .qa-s80/B1_UNIT_SPEC.md section 5.1 as amended by the review (C1-C11) and the batch
rulings B1-R1..B1-R12 / G-1..G-4. Base 81df2b64. Every RED row fails at base on an
AssertionError only: the unit's symbols are resolved with find_spec / getattr inside the test
body and ASSERTED, never imported at module top. Every PIN row is green at base and runs with
the FULL unit configuration (flag OFF, DEBUG_STAGE_TIMINGS=true with the memo reset, the
capture_message recorder installed, product_categories passed whenever the builder accepts it)
so a "not gated" mutant is killed. Hermetic: every network leaf is faked (the FY25 harness),
Supabase is stubbed, no .env, no credential; the synthetic Sentry DSN is built at run time.
Pure ASCII, LF.

Measured at base (probe in a detached scratch worktree, 2026-10-20): the builder's chokepoint
pends every lane1 / w412 price that lacks the exact-gate identity stamp (the google search url
is a listing url), so lane1 bodies reach data_coverage 3 (ratings, specs, dims) unstamped and 4
(grocery / now_vs_solgar / iphone15) with the stamp; the FY25 fakes give coverage 3 (price,
ratings, specs; every dim ties); rows 12-14 give coverage 0 / literal 1; rows 15-19 coverage
1-2 with brand ''; row 24 coverage 1 (the reliability dim 65 / 90); the gather partial coverage
1 (the stash's one real spec row on both sides); classify_category_from_text: 'Samsung Galaxy
S24 phone' -> electronics, 'Dior Sauvage eau de parfum' -> fragrances, 'Casio G-Shock watch' ->
other.
"""
from __future__ import annotations

import asyncio
import copy
import hashlib
import importlib
import importlib.util
import inspect
import json
import logging
import re
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import sentry_sdk
from fastapi.testclient import TestClient

from app.api import image_routes, text_routes, url_routes
from app.api.auth_routes import get_current_user
from app.main import app
from app.services import response_builder as rb
from app.services import sentry_service as ss
import app.services.structured_comparison_service as scs
from tests import test_s75_fanout_identity as fy

FLAG = "ENABLE_RESULT_STATUS_METADATA"
RG = "app.services.result_gate"
FIX = Path(__file__).resolve().parent / "fixtures"
CLEAR = (
    FLAG, "DEBUG_STAGE_TIMINGS", "ENABLE_HONEST_PARTIAL_SCORING", "ENABLE_SINGLE_VERDICT_MARGIN",
    "ENABLE_CONFIDENCE_SINGLE_COMPUTATION", "ENABLE_PRESCORING_SHOWABLE_GUARD",
    "ENABLE_REGION_CURRENCY_GUARD", "ENABLE_COMPARISON_ID_ECHO", "ENABLE_SEARCH_LOG_TRUTH",
    "ENABLE_SEARCH_LOG_SYNTHETIC_MARKER", "ENABLE_PAID_ROUTE_METERING",
    "ENABLE_CAMERA_FAILURE_ENVELOPE", "ENABLE_ANON_USAGE_GATE", "ENABLE_COMPARE_AUTH_REQUIRED",
    "ENABLE_PREVERDICT_DISCONNECT_ABORT", "ENABLE_FULL_STREAM_DEADLINE",
    "ENABLE_ARABIC_VERDICT_OUTPUT", "ENABLE_SMART_PICK_VERDICT_CAPTION",
    "ENABLE_HOME_SAVINGS_AGGREGATE",
)
TAG_GRAMMAR = re.compile("^[a-z0-9_,]+$")
TAG_KEYS = {"input_type", "result_status", "identity_confidence", "reasons", "unknown_product_count",
            "winner_emitted", "image_present_a", "image_present_b", "price_showable_a",
            "price_showable_b", "partial_stage", "data_coverage", "data_coverage_literal",
            "vision_ms", "compare_ms"}
STAMPED_MD = ("result_status", "identity_confidence", "data_coverage", "data_coverage_literal",
              "section_status", "product_categories", "winner_index")
WINNER_KEYS = {"product_index", "name", "declaration", "reason", "key_tradeoff", "margin"}
STATUSES = ("supported_result", "partial_no_winner", "needs_identification",
            "unsupported_category", "failed")
COMPARE_PATHS = ("/api/v1/text/compare", "/api/v1/text/compare/stream", "/api/v1/image/identify",
                 "/api/v1/url/compare")
OTHER_PATHS = ("/api/v1/health", "/api/v1/comparisons/history")
PRODUCT_TOKENS = ("iphone", "galaxy", "apple", "samsung")
JPEG = bytes([255, 216]) + bytes(64)
# P1 base digests (sorted-key JSON of the built body with FY25's VOLATILE keys dropped), recorded
# at 81df2b64 twice each (stable) in the RED probe.
P1_BASE = {
    "w412_12": "31c07498f43887417ee34976a43d8c730e4ab96275e840fa3a85e3be5d5e29f4",
    "w412_15": "c505b6783b568d36a987ee1287722c53cd7f814f0157ac40f6adfc74d61f7be8",
    "w412_24": "abaa208c612926cb0fdb29c6b74c31a14ba0f34b101cc259a90825a76ca8b8fc",
    "lane1_grocery": "a96f6cf33d8c2124e8bf67ab4c0b25ba9c20b3ed9b54aaa929619a275feb970f",
}
BASE_MD_KEYS = {
    "w412_12": {"api_calls", "budget_mismatch", "cache_hit", "cached", "comparison_quality",
                "elapsed_ms", "elapsed_seconds", "fact_check", "genuine_from_cache", "gpt_calls",
                "guard_rejected", "missing_dim_cells", "query", "region", "serper_calls", "timestamp",
                "total_cost", "verdict_validation"},
}


# ---------------------------------------------------------------- helpers

def _done(value=None):
    async def _r():
        return value
    return _r()


class _Rec:
    """Records sentry_sdk.capture_message(message, level=..., tags=..., extras=...) at call time."""

    def __init__(self):
        self.calls = []

    def __call__(self, message, level=None, **kw):
        self.calls.append((message, level, dict(kw.get("tags") or {}), dict(kw.get("extras") or {})))


def _rg():
    if importlib.util.find_spec(RG) is None:
        return None
    return importlib.import_module(RG)


def _need_rg():
    mod = _rg()
    assert mod is not None, "app.services.result_gate is absent (RED at base)"
    return mod


def _fn(mod, name):
    f = getattr(mod, name, None)
    assert callable(f), "missing callable %s" % name
    return f


def _w412(n):
    rows = json.loads((FIX / "w412_corpus_min.json").read_text(encoding="utf-8"))
    return rows[n]["full_response"]


def _lane1(name):
    return json.loads((FIX / "lane1" / (name + "_response.json")).read_text(encoding="utf-8"))


def _builder_accepts_product_categories():
    return "product_categories" in inspect.signature(rb.build_comparison_response).parameters


def _build(products, comparison, scoring, winner_index, category, query, *, product_categories=None,
           metadata=None):
    """The builder, driven exactly as the orchestrator drives it; product_categories is passed
    only when the signature accepts it (absent at base, so PIN rows stay green there)."""
    sr = copy.deepcopy(scoring) or {}
    sr["winner_index"] = winner_index
    kw = {}
    if product_categories is not None and _builder_accepts_product_categories():
        kw["product_categories"] = product_categories
    return rb.build_comparison_response(
        product_data=copy.deepcopy(products), comparison=copy.deepcopy(comparison or {}),
        scoring_result=sr, product_names=[p.get("name", "") for p in products],
        query=query, category_used=category or "", metadata=metadata, **kw)


def _build_row(resp, *, product_categories=None, metadata=None, products=None):
    cat = resp.get("category_used") or resp.get("category") or ""
    return _build(products if products is not None else resp["products"], resp.get("comparison"),
                  resp.get("scoring"), resp.get("winner_index", 0), cat,
                  resp.get("query") or "a vs b", product_categories=product_categories,
                  metadata=metadata)


def _stamp_prices(products):
    out = copy.deepcopy(products)
    for p in out:
        if isinstance(p.get("price"), dict):
            p["price"]["name"] = p.get("name")
            p["price"]["brand"] = p.get("brand")
            p["price"]["url"] = "https://shop.example/" + re.sub("[^a-z0-9]+", "-", str(p.get("name")).lower())
            p["price"]["in_stock"] = True
    return out


def _digest(body):
    blob = json.dumps(fy._normalize(body), sort_keys=True, default=repr, ensure_ascii=True)
    return hashlib.sha256(blob.encode("ascii")).hexdigest()


def _strip_stamps(body):
    out = copy.deepcopy(body)
    md = out.get("metadata") or {}
    for k in STAMPED_MD:
        md.pop(k, None)
    ((out.get("overview") or {}).get("winner") or {}).pop("supported", None)
    return fy._normalize(out)


def _quiet(monkeypatch, module):
    labels = []

    def _ff(coro, label=None, **_k):
        labels.append(label)
        try:
            coro.close()
        except Exception:  # noqa: BLE001
            pass

    monkeypatch.setattr(module, "fire_and_forget", _ff)
    monkeypatch.setattr(module, "log_search", lambda **_kw: _done(), raising=False)
    return labels


def _check_tags(tags, extras):
    for k, v in tags.items():
        assert isinstance(v, str) and TAG_GRAMMAR.match(v), (k, v)
        for tok in PRODUCT_TOKENS:
            assert tok not in v.lower(), (k, v)
        assert "vs" not in v.split(","), (k, v)
    assert set(tags) <= TAG_KEYS, sorted(tags)
    assert set(extras) <= {"vision_ms", "compare_ms"}, sorted(extras)
    for k, v in extras.items():
        assert isinstance(v, int) and not isinstance(v, bool) and v >= 0, (k, v)


def _text(chunk):
    return chunk.decode("utf-8", "replace") if isinstance(chunk, bytes) else str(chunk)


class _FakeReq:
    def __init__(self, disconnect_after=10 ** 6):
        self.calls = 0
        self.disconnect_after = disconnect_after
        self.headers = {}

    async def is_disconnected(self):
        self.calls += 1
        return self.calls > self.disconnect_after


class _StreamSvc:
    def __init__(self, events):
        self.events = events

    async def compare_from_text_streaming(self, *_a, **_kw):
        for ev in self.events:
            yield copy.deepcopy(ev)


# ---------------------------------------------------------------- fixtures

@pytest.fixture(autouse=True)
def rec(monkeypatch):
    for name in CLEAR:
        monkeypatch.delenv(name, raising=False)
    scs._DEBUG_STAGE_TIMINGS = None
    from app.middleware.rate_limiter import limiter

    prior = limiter.enabled
    limiter.enabled = False
    recorder = _Rec()
    monkeypatch.setattr(sentry_sdk, "capture_message", recorder)
    saved = dict(app.dependency_overrides)
    try:
        yield recorder
    finally:
        limiter.enabled = prior
        scs._DEBUG_STAGE_TIMINGS = None
        app.dependency_overrides.clear()
        app.dependency_overrides.update(saved)


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def fy_text(monkeypatch):
    """text_routes.get_comparison_service -> a fresh FY25-installed service per call."""
    p = fy._Patcher()
    state = fy._new_state()

    def _factory():
        svc = scs.StructuredComparisonService()
        fy._install(p, svc, state)
        return svc

    monkeypatch.setattr(text_routes, "get_comparison_service", _factory)
    _quiet(monkeypatch, text_routes)
    try:
        yield state
    finally:
        p.undo()


def _camera(monkeypatch, client, body, *, vision_n=2):
    from tests.test_retro_w2_1 import Ledger, _stub_camera, _vision

    ledger = Ledger()
    _stub_camera(monkeypatch, ledger, vision=_vision(vision_n), compare_result=body)
    _quiet(monkeypatch, image_routes)
    files = [("images", ("p%d.jpg" % i, JPEG, "image/jpeg")) for i in range(2)]
    return client.post("/api/v1/image/identify", files=files)


def _url(monkeypatch, client):
    from tests.test_paid_route_metering import _post_compare, _stub_url_leaves

    _stub_url_leaves(monkeypatch)
    _quiet(monkeypatch, url_routes)
    return _post_compare(client)


async def _stream_direct(monkeypatch, factory, *, disconnect_after=10 ** 6):
    monkeypatch.setattr(text_routes, "get_comparison_service", factory)
    _quiet(monkeypatch, text_routes)
    resp = await text_routes.text_compare_stream(
        request=_FakeReq(disconnect_after), q=fy.QUERY, product_a=None, product_b=None,
        region="bahrain", specs=True, reviews=True, pros_cons=True, nocache=True,
        selected_category=None, lang=None, user=None)
    chunks = []
    async for c in resp.body_iterator:
        chunks.append(c)
    return chunks


def _fy_rest(query=fy.QUERY, **kw):
    return asyncio.run(fy._scenario("rest", query, **kw))["payload"]


def _fy_stream_complete(**kw):
    return fy._complete(asyncio.run(fy._scenario("stream", fy.QUERY, **kw))["payload"])


def _savings(client, rows):
    from tests.test_home_routes import _fake_user, _patch_supabase_comparisons

    app.dependency_overrides[get_current_user] = _fake_user()
    supabase = MagicMock()
    _patch_supabase_comparisons(supabase, rows)
    with patch("app.api.home_routes.get_user_supabase_client", return_value=supabase), \
            patch("app.api.home_routes._redis_get", return_value=None), \
            patch("app.api.home_routes._redis_set", return_value=True):
        resp = client.get("/api/v1/home/savings", headers={"Authorization": "Bearer fake"})
    assert resp.status_code == 200, resp.text[:300]
    return resp.json()


def _smart_pick(client, rows):
    from tests.test_home_routes import _fake_user

    app.dependency_overrides[get_current_user] = _fake_user()
    supabase = MagicMock()
    user_resp = MagicMock()
    user_resp.data = {"preferences": {}}
    comp_resp = MagicMock()
    comp_resp.data = rows

    def _dispatch(name):
        m = MagicMock()
        if name == "users":
            m.select.return_value.eq.return_value.single.return_value.execute.return_value = user_resp
        else:
            m.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = comp_resp
        return m

    supabase.table.side_effect = _dispatch
    with patch("app.api.home_routes.get_user_supabase_client", return_value=supabase), \
            patch("app.api.home_routes._redis_get", return_value=None), \
            patch("app.api.home_routes._redis_set", return_value=True):
        resp = client.get("/api/v1/home/smart-pick", headers={"Authorization": "Bearer fake"})
    assert resp.status_code == 200, resp.text[:300]
    return resp.json()


def _home_row(winner_idx, p0_price, p1_price, id_, *, metadata=None, winner_declaration=None):
    from tests.test_home_routes import _comparison_row

    row = _comparison_row(winner_idx=winner_idx, p0_price=p0_price, p1_price=p1_price, id_=id_,
                          winner_declaration=winner_declaration)
    if metadata is not None:
        row["full_response"]["metadata"] = metadata
    return row


def _recorded_init_kwargs(monkeypatch):
    from sentry_sdk.integrations.logging import LoggingIntegration

    calls = []
    monkeypatch.setattr(sentry_sdk, "init", lambda *a, **kw: calls.append(kw))
    monkeypatch.setattr(LoggingIntegration, "capture_sentry_logs", LoggingIntegration.capture_sentry_logs)
    monkeypatch.setenv("SENTRY_DSN", "https://public" + "@" + "o0.ingest.example.invalid/1")
    ss.init_sentry()
    assert len(calls) == 1, calls
    return calls[0]


def _ctx(path, ps):
    ctx = {"transaction_context": {"name": path, "op": "http.server"}, "parent_sampled": ps}
    if path is not None:
        ctx["asgi_scope"] = {"path": path, "method": "GET", "type": "http"}
    return ctx


# ================================================================ R1-R7: the pure module

@pytest.mark.parametrize("value, want", [
    (None, False), ("", False), ("false", False), ("0", False), ("no", False), ("off", False),
    ("true", True), ("1", True), ("yes", True), ("on", True), (" TRUE ", True)])
def test_b1_r1_flag_reader_per_call(monkeypatch, value, want):
    rg = _need_rg()
    reader = _fn(rg, "result_status_metadata_enabled")
    if value is None:
        monkeypatch.delenv(FLAG, raising=False)
    else:
        monkeypatch.setenv(FLAG, value)
    assert reader() is want, (value, want)
    # per call: flipping the env after import flips the answer
    monkeypatch.setenv(FLAG, "false" if want else "true")
    assert reader() is (not want)


@pytest.mark.parametrize("brand, name, want", [
    ("Unknown", "Unknown Product", True), ("", "Unknown Product", True), ("Unknown", "", True),
    ("Unknown", "Unknown", True), ("", "", True), ("", "n/a", True), ("Acme", "This product", True),
    ("", "PRODUCT", True), ("Rasasi", "Hawas", False), ("", "Iphone 17", False),
    ("Unknown", "Hawas", False)])
def test_b1_r2_placeholder_identity(brand, name, want):
    rg = _need_rg()
    assert _fn(rg, "product_is_placeholder")({"brand": brand, "name": name}) is want, (brand, name)
    assert _fn(rg, "is_placeholder_identity")("Store Title", site_title="store title") is True
    assert _fn(rg, "is_placeholder_identity")("Hawas", site_title="store title") is False
    assert _fn(rg, "product_is_placeholder")(None) is True


@pytest.mark.parametrize("p0, p1, want", [
    ({"brand": "GUESS", "name": "GUESS!"}, {"brand": "GUESS", "name": "GUESS!"}, True),
    ({"brand": "Guess", "name": "GUESS !"}, {"brand": "GUESS", "name": "GUESS!"}, True),
    ({"brand": "GUESS", "name": "GUESS Logo Tee"}, {"brand": "GUESS", "name": "GUESS Denim Shirt"}, False),
    ({"brand": "Bertolli", "name": "Extra Virgin Olive Oil"},
     {"brand": "Carbonell", "name": "Extra Virgin Olive Oil"}, False),
    ({"brand": "NOW Foods", "name": "Vitamin D3"}, {"brand": "Solgar", "name": "Vitamin D3"}, False),
    ({"brand": "TOM FORD", "name": "TOM FORD OUD VOYAGER 100 ML"},
     {"brand": "TOM FORD", "name": "TOM FORD OUD WOOD 100 ML"}, False),
    ({"brand": "Dior", "name": "Sauvage", "variant": "100ml"},
     {"brand": "Dior", "name": "Sauvage", "variant": "50ml"}, False),
    ({"brand": "Dior", "name": "Sauvage", "variant": None},
     {"brand": "Dior", "name": "Sauvage", "variant": "50ml"}, True),
    ({"brand": "", "name": "Unknown Product"}, {"brand": "Unknown", "name": "Unknown Product"}, True)])
def test_b1_r3_same_identity(p0, p1, want):
    rg = _need_rg()
    assert _fn(rg, "same_identity")(p0, p1) is want, (p0, p1)
    jac = _fn(rg, "token_jaccard")
    assert abs(jac("TOM FORD OUD VOYAGER 100 ML", "TOM FORD OUD WOOD 100 ML") - 5.0 / 7.0) < 1e-9
    assert jac("", "") == 1.0


@pytest.mark.parametrize("cats, want", [
    (["electronics", "fragrances"], False), (["other", "fragrances"], True),
    (["electronics", "electronics"], True), ([None, "grocery"], True),
    (["Electronics ", "electronics"], True), (None, True), (["beauty", "fragrances"], True),
    (["electronics", "fragrances", "other"], True), ("electronics", True)])
def test_b1_r4_identity_coherence(cats, want):
    rg = _need_rg()
    assert _fn(rg, "identity_coherence")(cats, "other") is want, cats
    assert _fn(rg, "identity_coherence")(cats) is want, cats


@pytest.mark.parametrize("price, showable, literal", [
    ({"amount": 2.25, "source_method": "estimated", "estimated": True}, False, False),
    ({"amount": 1.26, "source_method": "local_bhd"}, True, True),
    ({"amount": 2.07, "source_method": None}, False, True),
    ({"amount": None, "unavailable": True}, False, False),
    ({"amount": True}, False, False),
    (None, False, False),
    ({"amount": 0, "source_method": "local_bhd"}, False, True),
    ({"amount": 3.5, "source_method": "converted_usd", "unavailable": True}, False, False)])
def test_b1_r5_price_facts(price, showable, literal):
    rg = _need_rg()
    assert _fn(rg, "price_is_showable")(price) is showable, price
    assert _fn(rg, "price_is_present_literal")(price) is literal, price


def test_b1_r6_real_spec_rows_excludes_na_and_tier3():
    rg = _need_rg()
    rows = _fn(rg, "real_spec_rows")
    manama = {k: "N/A" for k in ("color", "origin", "weight", "features", "material", "warranty", "dimensions")}
    assert rows(manama, dict(manama)) == 0
    assert rows({"color": "red", "_field_confidence": {"color": "tier3_synthesis"}}, {"color": "blue"}) == 0
    assert rows({"color": "red", "weight": "N/A"}, {"color": "blue", "weight": "1 kg"}) == 1
    # B1-R2: NA through strip().lower(), never through norm()
    for na in ("N/A", " n/a ", "NA", "-", "None", "", "unknown", None):
        assert rows({"x": na, "y": "1"}, {"x": "real", "y": "2"}) == 1, repr(na)
    assert rows({"x": "n a"}, {"x": "n a"}) == 1  # 'n a' is NOT an NA token
    assert rows({"x": 5}, {"x": 7}) == 1
    assert rows(None, {"x": 1}) == 0
    assert _fn(rg, "real_spec_rows_one_side")({"a": "N/A", "b": "", "c": None, "d": "1 kg", "_fc": {}}) == 1
    assert _fn(rg, "literal_spec_items")({"product_0_advantages": ["x"], "similar": []}) == 1
    assert _fn(rg, "literal_spec_items")({"rows": [1, 2, 3]}) == 0
    # the base behaviour this fact deliberately does not follow (documented): 7 N/A rows are emitted
    row12 = _w412(12)
    emitted = rb._build_specs_rows(copy.deepcopy(row12["products"]), row12.get("category_used") or "other") \
        if "category" in inspect.signature(rb._build_specs_rows).parameters \
        else rb._build_specs_rows(copy.deepcopy(row12["products"]))
    assert len(emitted) == 7, emitted


@pytest.mark.parametrize("a, b, conf, cap, key, missing, literal, strict", [
    (85, 85, "high", None, "price", [], False, False),
    (85, 75, "high", None, "price", [], True, True),
    (75, 75, "low", "limited_data", "price", [], False, False),
    (65.0, 50, "medium", None, "function", [], True, False),
    (88, 82, "low", None, "reviews", [], True, False),
    (88, 84, "high", None, "review", ["review_score"], True, False),
    (88, 84, "high", None, "review", ["review"], True, False),
    (90, 86, "medium", None, "build", ["other_score"], True, True),
    (True, 50, "high", None, "x", [], False, False),
    (80, 76, "medium", "limited_data", "x", [], False, False)])
def test_b1_r7_dim_facts(a, b, conf, cap, key, missing, literal, strict):
    rg = _need_rg()
    dim = {"key": key, "score_a": a, "score_b": b, "confidence": conf}
    if cap is not None:
        dim["caption_key"] = cap
    f = _fn(rg, "dim_is_discriminating")
    assert f(dim, set(missing), strict=False) is literal, dim
    assert f(dim, set(missing), strict=True) is strict, dim
    assert f(None, set(), strict=True) is False


# ================================================================ R8-R14: the builder stamp

@pytest.mark.parametrize("n", [12, 13, 14])
def test_b1_r8_builder_stamps_manama_partial_no_winner(monkeypatch, n):
    monkeypatch.setenv(FLAG, "true")
    body = _build_row(_w412(n), product_categories=["other", "other"])
    md = body["metadata"]
    assert md.get("result_status") == "partial_no_winner", md.get("result_status")
    assert "no_evidence" in (md.get("reasons") or ["no_evidence"])  # reasons ride telemetry, not metadata
    assert md.get("data_coverage") == 0
    assert md.get("data_coverage_literal", 0) >= 1
    assert md.get("identity_confidence") == "medium"
    assert md.get("section_status") == {"specs": "unavailable", "reviews": "available",
                                        "pros_cons": "available", "price": "unavailable"}
    assert body["overview"]["winner"].get("supported") is False
    assert "winner_index" in md and md["winner_index"] is None
    assert body["winner_index"] == 0 and body["overview"]["winner"]["product_index"] == 0
    assert md.get("product_categories") == ["other", "other"]


LANE1_PRICE_SECTION = {"grocery": "unavailable", "now_vs_solgar": "partial",
                       "tomford_vs_creed": "unavailable", "iphone15_vs_galaxys24": "unavailable"}


@pytest.mark.parametrize("name", sorted(LANE1_PRICE_SECTION))
def test_b1_r9_builder_stamps_lane1_supported(monkeypatch, name):
    monkeypatch.setenv(FLAG, "true")
    resp = _lane1(name)
    cat = resp.get("category_used") or "other"
    body = _build_row(resp, product_categories=[cat, cat])
    md = body["metadata"]
    assert md.get("result_status") == "supported_result", md.get("result_status")
    assert md.get("data_coverage", 0) >= 3, md.get("data_coverage")
    assert md.get("identity_confidence") == "high"
    assert body["overview"]["winner"].get("supported") is True
    assert "winner_index" not in md
    sec = md.get("section_status") or {}
    assert (sec.get("specs"), sec.get("reviews"), sec.get("pros_cons")) == ("available", "available", "available"), sec
    assert sec.get("price") == LANE1_PRICE_SECTION[name], sec
    assert md.get("product_categories") == [cat, cat]


@pytest.mark.parametrize("name", ["grocery", "now_vs_solgar", "iphone15_vs_galaxys24"])
def test_b1_r9b_builder_lane1_stamped_prices_reach_coverage_4(monkeypatch, name):
    """B1-R5 second row / B1-R3: the price dicts carry the exact-gate identity -> price available,
    data_coverage 4 (the dims differ on these three lane1 pairs)."""
    monkeypatch.setenv(FLAG, "true")
    resp = _lane1(name)
    cat = resp.get("category_used") or "other"
    body = _build_row(resp, product_categories=[cat, cat], products=_stamp_prices(resp["products"]))
    md = body["metadata"]
    assert md.get("result_status") == "supported_result"
    assert md.get("data_coverage") == 4, md.get("data_coverage")
    assert md.get("data_coverage_literal") == 4, md.get("data_coverage_literal")
    assert (md.get("section_status") or {}).get("price") == "available", md.get("section_status")


@pytest.mark.parametrize("brands", [("", ""), ("Unknown", "Unknown")])
def test_b1_r10_builder_unknown_product_pair_needs_identification(monkeypatch, brands):
    monkeypatch.setenv(FLAG, "true")
    resp = _lane1("grocery")
    prods = copy.deepcopy(resp["products"])
    for p, b in zip(prods, brands):
        p["brand"], p["name"] = b, "Unknown Product"
    body = _build_row(resp, product_categories=["grocery", "grocery"], products=prods)
    md = body["metadata"]
    assert md.get("result_status") == "needs_identification", md.get("result_status")
    assert md.get("identity_confidence") == "unresolved"
    assert "winner_index" in md and md["winner_index"] is None
    assert body["overview"]["winner"].get("supported") is False
    assert body["winner_index"] == 0  # B1 never refuses
    rg = _need_rg()
    a = _fn(rg, "assess_result")(body)
    assert a["reasons"][0] == "placeholder_identity", a["reasons"]
    assert a["unknown_product_count"] == 2


def test_b1_r10b_v09_shape_reasons_exact(monkeypatch):
    """B1-R9 (a): V09 = two Unknown Products with no evidence -> every reason, in REASONS order."""
    monkeypatch.setenv(FLAG, "true")
    resp = _w412(12)
    prods = copy.deepcopy(resp["products"])
    for p in prods:
        p["brand"], p["name"] = "", "Unknown Product"
    body = _build_row(resp, product_categories=["other", "other"], products=prods)
    rg = _need_rg()
    a = _fn(rg, "assess_result")(body, product_categories=["other", "other"])
    assert a["reasons"] == ["placeholder_identity", "same_identity", "no_evidence"], a["reasons"]
    assert a["status"] == "needs_identification"
    assert body["metadata"].get("result_status") == "needs_identification"
    tags = _fn(rg, "telemetry_tags")(body, "camera", assessment=a)
    assert tags["reasons"] == "placeholder_identity,same_identity,no_evidence"


def test_b1_r11_builder_same_identity_pair(monkeypatch):
    monkeypatch.setenv(FLAG, "true")
    resp = _lane1("grocery")
    prods = copy.deepcopy(resp["products"])
    for p in prods:
        p["brand"], p["name"] = "GUESS", "GUESS!"
    body = _build_row(resp, product_categories=["fashion", "fashion"], products=prods)
    md = body["metadata"]
    assert md.get("result_status") == "needs_identification", md.get("result_status")
    assert md.get("identity_confidence") == "low"
    rg = _need_rg()
    a = _fn(rg, "assess_result")(body)
    assert a["reasons"][0] == "same_identity", a["reasons"]
    # B1-R7: a spec-derived display variant (colour) does not break the identity
    prods2 = copy.deepcopy(prods)
    prods2[0]["specs"] = {"color": "red"}
    prods2[1]["specs"] = {"color": "blue"}
    for p in prods2:
        p["variant"] = None
    body2 = _build_row(resp, product_categories=["fashion", "fashion"], products=prods2)
    assert body2["metadata"].get("result_status") == "needs_identification"
    assert _fn(rg, "same_identity")(body2["products"][0], body2["products"][1]) is True


def test_b1_r12_builder_category_conflict(monkeypatch):
    monkeypatch.setenv(FLAG, "true")
    resp = _lane1("grocery")
    body = _build_row(resp, product_categories=["electronics", "fragrances"])
    md = body["metadata"]
    assert md.get("result_status") == "unsupported_category", md.get("result_status")
    assert md.get("identity_confidence") == "low"
    assert md.get("product_categories") == ["electronics", "fragrances"]
    rg = _need_rg()
    a = _fn(rg, "assess_result")(body, product_categories=["electronics", "fragrances"])
    assert a["reasons"] == ["category_conflict"], a["reasons"]
    body2 = _build_row(resp, product_categories=["other", "fragrances"])
    assert body2["metadata"].get("result_status") == "supported_result"
    assert body2["metadata"].get("product_categories") == ["other", "fragrances"]


@pytest.mark.parametrize("n", [15, 16, 17, 18, 19])
def test_b1_r13_builder_june_rows_brand_empty_supported(monkeypatch, n):
    monkeypatch.setenv(FLAG, "true")
    body = _build_row(_w412(n), product_categories=["electronics", "electronics"])
    md = body["metadata"]
    assert md.get("result_status") == "supported_result", (n, md.get("result_status"))
    assert md.get("identity_confidence") == "medium", (n, md.get("identity_confidence"))
    assert md.get("data_coverage", 0) >= 1, (n, md.get("data_coverage"))
    assert "winner_index" not in md


def test_b1_r14_builder_partial_rows(monkeypatch):
    monkeypatch.setenv(FLAG, "true")
    partial = {"partial": True, "partial_stage": "post_gather"}
    b24 = _build_row(_w412(24), product_categories=["fragrances", "fragrances"], metadata=dict(partial))
    md = b24["metadata"]
    assert md.get("data_coverage") == 1, md.get("data_coverage")
    assert md.get("result_status") == "supported_result"
    assert b24["overview"]["winner"].get("supported") is True
    assert md.get("partial") is True and md.get("partial_stage") == "post_gather"
    rg = _need_rg()
    assert _fn(rg, "telemetry_tags")(b24, "camera")["partial_stage"] == "post_gather"
    b26 = _build_row(_w412(26), product_categories=["fragrances", "fragrances"], metadata=dict(partial))
    assert b26["metadata"].get("data_coverage", 0) >= 1
    assert b26["metadata"].get("result_status") == "supported_result"


# ================================================================ R15-R16: the orchestrator

def test_b1_r15_orchestrator_rest_and_stream_stamp(monkeypatch):
    monkeypatch.setenv(FLAG, "true")
    env = {FLAG: "true"}
    # measured on the prototype: the parser path carries the LLM per-product category (electronics),
    # the explicit pair carries the keyword stubs (brand-only names -> other; L2 / B1-R4)
    for label, body, conf, cats in (("rest_q", _fy_rest(env=env), "high", ["electronics", "electronics"]),
                                    ("rest_pair", _fy_rest(explicit_pair=fy.PAIR, env=env), "medium", ["other", "other"]),
                                    ("stream", _fy_stream_complete(env=env), "high", ["electronics", "electronics"])):
        md = body.get("metadata") or {}
        assert md.get("result_status") == "supported_result", (label, md.get("result_status"))
        assert md.get("data_coverage") == 3, (label, md.get("data_coverage"))  # B1-R3: the dims tie
        assert md.get("identity_confidence") == conf, (label, md.get("identity_confidence"))
        assert md.get("product_categories") == cats, (label, md.get("product_categories"))
        assert body["overview"]["winner"].get("supported") is True, label
        assert "winner_index" not in md, label
    part = _fy_rest(cap=0.5, slow=True, env=env)
    md = part.get("metadata") or {}
    assert md.get("partial") is True and md.get("partial_stage") == "gather", md
    # measured at base: the stash carries one real spec row on both sides -> coverage 1 -> supported
    assert md.get("data_coverage") == 1, md.get("data_coverage")
    assert md.get("result_status") == "supported_result", md.get("result_status")
    assert "winner_index" not in md
    assert md.get("product_categories") == ["electronics", "electronics"], md.get("product_categories")


def _vision_compare(monkeypatch, pair):
    p = fy._Patcher()
    state = fy._new_state()
    try:
        svc = scs.StructuredComparisonService()
        fy._install(p, svc, state)
        return asyncio.run(asyncio.wait_for(
            svc.compare_from_text(fy.QUERY, region="bahrain", nocache=True, vision_products=pair), 60))
    finally:
        p.undo()


def test_b1_r16_orchestrator_vision_pair_product_categories(monkeypatch):
    monkeypatch.setenv(FLAG, "true")
    body = _vision_compare(monkeypatch, [{"brand": "Samsung", "name": "Galaxy S24 phone"},
                                         {"brand": "Dior", "name": "Sauvage eau de parfum"}])
    md = body.get("metadata") or {}
    assert md.get("product_categories") == ["electronics", "fragrances"], md.get("product_categories")
    cu = body.get("category_used")
    assert [p.get("category") for p in body["products"]] == [cu, cu]
    assert md.get("result_status") == "unsupported_category", md.get("result_status")
    rg = _need_rg()
    assert _fn(rg, "assess_result")(body, product_categories=md.get("product_categories"))["reasons"] == ["category_conflict"]
    # the measured negative (B1-R4): a brand-only name is 'other', which never conflicts
    body2 = _vision_compare(monkeypatch, [{"brand": "Casio", "name": "G-Shock watch"},
                                          {"brand": "Dior", "name": "Sauvage eau de parfum"}])
    md2 = body2.get("metadata") or {}
    assert md2.get("product_categories") == ["other", "fragrances"], md2.get("product_categories")
    assert md2.get("result_status") == "supported_result", md2.get("result_status")


# ================================================================ R17-R19: telemetry

def test_b1_r17_telemetry_text_post_get_stream(monkeypatch, client, rec, fy_text):
    monkeypatch.setenv(FLAG, "true")
    r = client.post("/api/v1/text/compare", json={"query": fy.QUERY, "nocache": True})
    assert r.status_code == 200, r.text[:300]
    assert len(rec.calls) == 1, rec.calls
    r = client.get("/api/v1/text/compare", params={"q": fy.QUERY, "nocache": "true"})
    assert r.status_code == 200, r.text[:300]
    assert len(rec.calls) == 2, rec.calls
    chunks = asyncio.run(_stream_direct(monkeypatch, text_routes.get_comparison_service))
    assert any("complete" in _text(c) for c in chunks), chunks[-1:]
    assert len(rec.calls) == 3, rec.calls
    for (message, level, tags, extras), input_type in zip(rec.calls, ("text", "text", "text_stream")):
        assert message == "comparison_result_status" and level == "info", (message, level)
        _check_tags(tags, extras)
        assert set(tags) == TAG_KEYS - {"vision_ms"}, sorted(tags)
        assert tags["input_type"] == input_type
        assert tags["result_status"] == "supported_result"
        assert tags["winner_emitted"] == "true"
        assert tags["unknown_product_count"] == "0"
        assert tags["image_present_a"] == "false"
        assert tags["price_showable_a"] == "true"
        assert tags["partial_stage"] == "none"
        assert tags["data_coverage"] == "3"  # B1-R3
        assert tags["compare_ms"].isdigit() and int(tags["compare_ms"]) % 5000 == 0  # B1-R10 bucket
        assert "vision_ms" not in tags and "vision_ms" not in extras
        assert isinstance(extras.get("compare_ms"), int)  # B1-R10 raw int rides extras


def test_b1_r17b_telemetry_non_supported_body_tags(monkeypatch):
    """B1-R9 (b): a non-supported body -> winner_emitted false, unknown_product_count 2."""
    rg = _need_rg()
    resp = _w412(12)
    prods = copy.deepcopy(resp["products"])
    for p in prods:
        p["brand"], p["name"] = "Unknown", "Unknown Product"
    body = _build_row(resp, products=prods)
    tags = _fn(rg, "telemetry_tags")(body, "camera", vision_ms=1234, compare_ms=5678)
    _check_tags(tags, _fn(rg, "telemetry_extras")(vision_ms=1234, compare_ms=5678))
    assert tags["winner_emitted"] == "false" and tags["unknown_product_count"] == "2"
    assert tags["result_status"] == "needs_identification"
    assert tags["vision_ms"] == "1000" and tags["compare_ms"] == "5000"
    assert _fn(rg, "telemetry_extras")(vision_ms=1234, compare_ms=5678) == {"vision_ms": 1234, "compare_ms": 5678}
    assert _fn(rg, "telemetry_extras")() == {}


def test_b1_r18_telemetry_camera_and_url(monkeypatch, client, rec):
    monkeypatch.setenv(FLAG, "true")
    body = _build_row(_lane1("grocery"), product_categories=["grocery", "grocery"])
    r = _camera(monkeypatch, client, body)
    assert r.status_code == 200, r.text[:300]
    assert r.json().get("action") == "comparison"
    assert len(rec.calls) == 1, rec.calls
    message, level, tags, extras = rec.calls[0]
    assert message == "comparison_result_status" and level == "info"
    _check_tags(tags, extras)
    assert tags["input_type"] == "camera"
    assert tags["vision_ms"].isdigit() and tags["compare_ms"].isdigit()
    assert set(extras) == {"vision_ms", "compare_ms"}
    rec.calls.clear()
    r = _url(monkeypatch, client)
    assert r.status_code == 200, r.text[:300]
    assert len(rec.calls) == 1, rec.calls
    message, level, tags, extras = rec.calls[0]
    _check_tags(tags, extras)
    assert tags["input_type"] == "url"
    assert tags["result_status"] in STATUSES
    assert tags["price_showable_a"] == "false"
    assert "vision_ms" not in tags and "compare_ms" in tags
    assert "metadata" not in r.json()  # P12: the URL body is never stamped (R0-1)


@pytest.mark.parametrize("meter, envelope", [("true", "true"), (None, None), ("true", None)])
def test_b1_r18b_telemetry_camera_unsuccessful_emits_nothing(monkeypatch, client, rec, meter, envelope):
    """B1-R6: the camera emitter fires only when result.success is True (metering ON or OFF,
    envelope ON or OFF); the :580 body is unchanged with both OFF."""
    monkeypatch.setenv(FLAG, "true")
    if meter:
        monkeypatch.setenv("ENABLE_PAID_ROUTE_METERING", meter)
    if envelope:
        monkeypatch.setenv("ENABLE_CAMERA_FAILURE_ENVELOPE", envelope)
    failed = {"success": False, "code": "TIMEOUT", "error": "slow", "products": [],
              "metadata": {"total_cost": 0.0}}
    r = _camera(monkeypatch, client, failed)
    assert r.status_code == 200, r.text[:300]
    assert rec.calls == [], rec.calls
    body = r.json()
    if not meter and not envelope:
        assert body.get("success") is False and body.get("action") == "comparison" and body.get("code") == "TIMEOUT"
        assert "result_status" not in (body.get("metadata") or {})


def test_b1_r19_telemetry_stream_client_gone_emits_nothing(monkeypatch, rec):
    monkeypatch.setenv(FLAG, "true")
    delivered = _build_row(_lane1("grocery"))
    events = [("status", {}), ("specs", {}), ("prices", {}), ("verdict", {}),
              ("settle_complete", delivered), ("complete", delivered)]
    asyncio.run(_stream_direct(monkeypatch, lambda: _StreamSvc(events), disconnect_after=0))
    assert rec.calls == [], rec.calls
    # the same events with the client present -> exactly one message
    asyncio.run(_stream_direct(monkeypatch, lambda: _StreamSvc(events)))
    assert len(rec.calls) == 1, rec.calls
    assert rec.calls[0][2]["input_type"] == "text_stream"


# ================================================================ R20 / P3: camera timings

@pytest.mark.parametrize("shape", ["dict", "absent", "notdict"])
def test_b1_r20_camera_timings_written_only_into_existing_dict(monkeypatch, client, shape):
    monkeypatch.setenv(FLAG, "true")
    monkeypatch.setenv("DEBUG_STAGE_TIMINGS", "true")
    scs._DEBUG_STAGE_TIMINGS = None
    body = _build_row(_w412(12))
    if shape == "dict":
        body["metadata"]["stage_timings_ms"] = {"total_ms": 1.0}
    elif shape == "notdict":
        body["metadata"]["stage_timings_ms"] = 7
    before = set(body["metadata"])
    r = _camera(monkeypatch, client, body)
    assert r.status_code == 200, r.text[:300]
    md = r.json()["metadata"]
    if shape == "dict":
        st = md["stage_timings_ms"]
        assert set(st) == {"total_ms", "vision_ms", "vision_moderation_ms", "compare_ms"}, st
        assert st["total_ms"] == 1.0
        for k in ("vision_ms", "vision_moderation_ms", "compare_ms"):
            assert isinstance(st[k], int) and st[k] >= 0, (k, st[k])
    elif shape == "absent":
        assert "stage_timings_ms" not in md
    else:
        assert md["stage_timings_ms"] == 7
    extra = set(md) - before - {"input_method", "vision_cost", "total_cost", "identified_products", "openai"}
    assert extra <= set(STAMPED_MD), extra


def test_b1_r20b_stamp_camera_stage_timings_skips_none(monkeypatch):
    """B1-R9 (f): vision_moderation_ms None -> that key skipped, the other two written."""
    monkeypatch.setenv(FLAG, "true")
    rg = _need_rg()
    stamp = _fn(rg, "stamp_camera_stage_timings")
    result = {"metadata": {"stage_timings_ms": {"total_ms": 2.0}}}
    assert stamp(result, vision_ms=10, vision_moderation_ms=None, compare_ms=20) is True
    assert result["metadata"]["stage_timings_ms"] == {"total_ms": 2.0, "vision_ms": 10, "compare_ms": 20}
    bare = {"metadata": {}}
    assert stamp(bare, vision_ms=1, vision_moderation_ms=1, compare_ms=1) is False
    assert bare == {"metadata": {}}
    monkeypatch.delenv(FLAG, raising=False)
    result2 = {"metadata": {"stage_timings_ms": {"total_ms": 2.0}}}
    assert stamp(result2, vision_ms=10, vision_moderation_ms=5, compare_ms=20) is False
    assert result2["metadata"]["stage_timings_ms"] == {"total_ms": 2.0}


@pytest.mark.parametrize("flag_value", [None, "false"])
def test_b1_p3_flag_off_camera_timings_untouched(monkeypatch, client, rec, flag_value):
    if flag_value is not None:
        monkeypatch.setenv(FLAG, flag_value)
    monkeypatch.setenv("DEBUG_STAGE_TIMINGS", "true")
    scs._DEBUG_STAGE_TIMINGS = None
    body = _build_row(_w412(12))
    body["metadata"]["stage_timings_ms"] = {"total_ms": 1.0}
    before = set(body["metadata"])
    r = _camera(monkeypatch, client, body)
    assert r.status_code == 200, r.text[:300]
    md = r.json()["metadata"]
    assert md["stage_timings_ms"] == {"total_ms": 1.0}
    assert set(md) == before | {"input_method", "vision_cost", "total_cost", "identified_products"}, sorted(md)
    assert rec.calls == []


# ================================================================ R21 / P5: the sampler

@pytest.mark.parametrize("path", COMPARE_PATHS + OTHER_PATHS + (None,))
@pytest.mark.parametrize("ps", [None, True, False])
def test_b1_r21_sampler_flag_on_compare_paths(monkeypatch, path, ps):
    monkeypatch.setenv(FLAG, "true")
    sampler = getattr(ss, "compare_traces_sampler", None)
    assert callable(sampler), "compare_traces_sampler absent (RED at base)"
    got = sampler(_ctx(path, ps))
    if path in COMPARE_PATHS:
        assert got == 1.0, (path, ps, got)
    else:
        assert got == (ps if ps is not None else 0.1), (path, ps, got)


def test_b1_r21b_init_sentry_installs_the_sampler(monkeypatch):
    kw = _recorded_init_kwargs(monkeypatch)
    assert kw.get("traces_sample_rate") == 0.1
    sampler = kw.get("traces_sampler")
    assert callable(sampler) and getattr(sampler, "__name__", "") == "compare_traces_sampler", sampler


@pytest.mark.parametrize("path", COMPARE_PATHS + OTHER_PATHS + (None,))
@pytest.mark.parametrize("ps", [None, True, False])
@pytest.mark.parametrize("flag_value", [None, "false"])
def test_b1_p5_flag_off_sampler_is_the_sdk_rule(monkeypatch, path, ps, flag_value):
    if flag_value is not None:
        monkeypatch.setenv(FLAG, flag_value)
    sampler = getattr(ss, "compare_traces_sampler", None)
    assert callable(sampler), "compare_traces_sampler absent (RED at base)"
    assert sampler(_ctx(path, ps)) == (ps if ps is not None else 0.1), (path, ps)


@pytest.mark.parametrize("flag_value", [None, "false", "true"])
def test_b1_p5b_sampler_off_branch_reads_the_live_client_option(monkeypatch, flag_value):
    """B1-R1: parent_sampled when not None, else the LIVE client traces_sample_rate (a harness that
    forces 1.0 is honoured), never a module constant; 0.1 only when the client has no rate."""
    if flag_value is not None:
        monkeypatch.setenv(FLAG, flag_value)
    sampler = getattr(ss, "compare_traces_sampler", None)
    assert callable(sampler), "compare_traces_sampler absent (RED at base)"

    class _Client:
        def __init__(self, rate):
            self.options = {"traces_sample_rate": rate}

    monkeypatch.setattr(sentry_sdk, "get_client", lambda: _Client(1.0))
    assert sampler(_ctx("/api/v1/health", None)) == 1.0
    assert sampler(_ctx("/api/v1/health", False)) is False
    monkeypatch.setattr(sentry_sdk, "get_client", lambda: _Client(0.25))
    assert sampler(_ctx("/api/v1/comparisons/history", None)) == 0.25
    monkeypatch.setattr(sentry_sdk, "get_client", lambda: _Client(None))
    assert sampler(_ctx("/api/v1/health", None)) == 0.1
    assert sampler("not a dict") == 0.1


def test_b1_p5a_init_sentry_kwargs_kept(monkeypatch):
    kw = _recorded_init_kwargs(monkeypatch)
    assert (kw["send_default_pii"], kw["include_local_variables"], kw["traces_sample_rate"]) == (False, False, 0.1)
    assert (kw["before_send"].__name__, kw["before_send_transaction"].__name__, kw["before_breadcrumb"].__name__) == (
        ss._before_send.__name__, ss._before_send_transaction.__name__, ss._strip_tokens_from_breadcrumb.__name__)
    assert kw.get("max_request_body_size") == "never" and kw.get("trace_propagation_targets") == []


# ================================================================ R22 / R23 / P8 / P7: readers

def test_b1_r22_home_savings_skips_stamped_non_supported_rows(client):
    rows = [
        _home_row(0, 100, 150, "a"),                                                      # 50 saved
        _home_row(0, 200, 220, "b", metadata={"result_status": "partial_no_winner"}),     # skipped
        _home_row(1, 400, 300, "c", metadata={"result_status": "supported_result"}),      # 100 saved
        _home_row(1, 80, 75, "d", metadata={"result_status": "needs_identification"}),    # skipped
    ]
    body = _savings(client, rows)
    assert body["decisions_count"] == 2, body
    assert body["savings_bhd"] == 150.0, body
    # never via winner_index: a row carrying metadata.winner_index None but NO result_status counts
    rows2 = [_home_row(0, 100, 150, "e", metadata={"winner_index": None})]
    body2 = _savings(client, rows2)
    assert body2["decisions_count"] == 1 and body2["savings_bhd"] == 50.0, body2


def test_b1_p8_home_savings_unstamped_rows_count_as_today(client):
    rows = [_home_row(0, 100, 150, "a"), _home_row(0, 200, 220, "b"), _home_row(1, 400, 300, "c"),
            _home_row(1, 80, 75, "d", metadata={"cached": False}),
            ]
    body = _savings(client, rows)
    assert body["decisions_count"] == 4 and body["savings_bhd"] == 175.0, body
    rows2 = [_home_row(0, 100, 150, "a", metadata="garbage"), _home_row(0, 200, 220, "b", metadata={})]
    body2 = _savings(client, rows2)
    assert body2["decisions_count"] == 2 and body2["savings_bhd"] == 70.0, body2


def test_b1_r23_home_smart_pick_skips_stamped_non_supported_rows(client):
    newest = _home_row(0, 100, 150, "new", metadata={"result_status": "partial_no_winner"},
                       winner_declaration="Newest wins")
    older = _home_row(1, 400, 300, "old", metadata={"result_status": "supported_result"},
                      winner_declaration="Older wins")
    older["full_response"]["products"][1]["name"] = "OlderWinner"
    body = _smart_pick(client, [newest, older])
    assert body.get("empty_state") is False, body
    pick = body["smart_pick"]
    assert "OlderWinner" in json.dumps(pick), pick
    assert "Newest" not in json.dumps(pick), pick
    # every row stamped non-supported -> the empty state
    body2 = _smart_pick(client, [newest])
    assert body2.get("smart_pick") is None, body2


def test_b1_p7_history_list_null_neutral_for_stamped_row():
    from tests.test_history_routes import _cleanup_overrides, _get_client_with_user

    rows = [
        {"id": "11111111-1111-1111-1111-111111111111", "query": "a vs b", "product_names": ["a", "b"],
         "input_type": "camera", "user_id": "user-123", "created_at": "2026-10-18T10:00:00Z",
         "full_response": {"metadata": {"winner_index": None, "result_status": "partial_no_winner"},
                           "comparison": {"winner_index": 0},
                           "products": [{"name": "a", "image_url": "https://x.invalid/a.jpg"},
                                        {"name": "b", "image_url": "https://x.invalid/b.jpg"}]}},
        {"id": "22222222-2222-2222-2222-222222222222", "query": "c vs d", "product_names": ["c", "d"],
         "input_type": "text", "user_id": "user-123", "created_at": "2026-10-17T10:00:00Z",
         "full_response": {"metadata": {}, "comparison": {"winner_index": 0},
                           "products": [{"name": "c", "image_url": "https://x.invalid/c.jpg"},
                                        {"name": "d", "image_url": "https://x.invalid/d.jpg"}]}},
    ]
    client = _get_client_with_user()
    try:
        with patch("app.api.history_routes.get_user_comparison_count", new_callable=AsyncMock, return_value=2), \
                patch("app.api.history_routes.get_user_comparisons", new_callable=AsyncMock, return_value=rows):
            resp = client.get("/api/v1/comparisons/history")
        assert resp.status_code == 200, resp.text[:300]
        out = resp.json()["comparisons"]
        assert (out[0]["winner_index"], out[0]["winner_image_url"], out[0]["runner_up_image_url"]) == (None, None, None)
        assert (out[1]["winner_index"], out[1]["winner_image_url"], out[1]["runner_up_image_url"]) == (
            0, "https://x.invalid/c.jpg", "https://x.invalid/d.jpg")
    finally:
        _cleanup_overrides()


# ================================================================ P1 / P2 / P4 / P6: flag-OFF identity

@pytest.mark.parametrize("flag_value", [None, "false", "0", "", "off"])
def test_b1_p1_flag_off_builder_bodies_identical(monkeypatch, rec, flag_value):
    if flag_value is not None:
        monkeypatch.setenv(FLAG, flag_value)
    monkeypatch.setenv("DEBUG_STAGE_TIMINGS", "true")
    scs._DEBUG_STAGE_TIMINGS = None
    bodies = {
        "w412_12": _build_row(_w412(12), product_categories=["other", "other"]),
        "w412_15": _build_row(_w412(15), product_categories=["electronics", "electronics"]),
        "w412_24": _build_row(_w412(24), product_categories=["fragrances", "fragrances"],
                              metadata={"partial": True, "partial_stage": "post_gather"}),
        "lane1_grocery": _build_row(_lane1("grocery"), product_categories=["grocery", "grocery"]),
    }
    for label, body in bodies.items():
        assert _digest(body) == P1_BASE[label], (label, flag_value)
        md = body["metadata"]
        assert not any(k in md for k in STAMPED_MD), (label, sorted(md))
        assert set(body["overview"]["winner"]) == WINNER_KEYS, (label, sorted(body["overview"]["winner"]))
    assert set(bodies["w412_12"]["metadata"]) == BASE_MD_KEYS["w412_12"]
    assert rec.calls == []


@pytest.mark.parametrize("flag_value", [None, "false"])
def test_b1_p2_flag_off_orchestrator_digests_unchanged(monkeypatch, flag_value):
    if flag_value is not None:
        monkeypatch.setenv(FLAG, flag_value)
    want = json.loads(fy.FIXTURE.read_text(encoding="ascii"))["digests"]
    env = {FLAG: flag_value} if flag_value is not None else None
    got = {}
    for name, (kind, query, kwargs) in fy.SCENARIOS.items():
        kw = dict(kwargs)
        if env:
            kw["env"] = env
        got[name] = fy._digest(asyncio.run(fy._scenario(kind, query, **kw)))
    moved = sorted(name for name in fy.SCENARIOS if got.get(name) != want.get(name))
    assert moved == [], moved


@pytest.mark.parametrize("flag_value", [None, "0"])
def test_b1_p4_flag_off_no_message_on_any_exit(monkeypatch, client, rec, fy_text, flag_value):
    if flag_value is not None:
        monkeypatch.setenv(FLAG, flag_value)
    monkeypatch.setenv("DEBUG_STAGE_TIMINGS", "true")
    scs._DEBUG_STAGE_TIMINGS = None
    r = client.post("/api/v1/text/compare", json={"query": fy.QUERY, "nocache": True})
    assert r.status_code == 200 and "result_status" not in r.json()["metadata"], r.text[:300]
    r = client.get("/api/v1/text/compare", params={"q": fy.QUERY, "nocache": "true"})
    assert r.status_code == 200 and "result_status" not in r.json()["metadata"], r.text[:300]
    chunks = asyncio.run(_stream_direct(monkeypatch, text_routes.get_comparison_service))
    assert any("complete" in _text(c) for c in chunks)
    body = _build_row(_lane1("grocery"))
    r = _camera(monkeypatch, client, body)
    assert r.status_code == 200 and "result_status" not in r.json()["metadata"], r.text[:300]
    r = _url(monkeypatch, client)
    assert r.status_code == 200 and "metadata" not in r.json(), r.text[:300]
    assert rec.calls == [], rec.calls


def test_b1_p6_builder_flag_on_does_not_move_the_crown(monkeypatch):
    cases = [
        (_w412(12), ["other", "other"], None),
        (_lane1("grocery"), ["grocery", "grocery"], None),
        (_lane1("grocery"), ["electronics", "fragrances"], None),
        (_w412(24), ["fragrances", "fragrances"], {"partial": True, "partial_stage": "post_gather"}),
    ]
    for resp, cats, md in cases:
        monkeypatch.delenv(FLAG, raising=False)
        off = _build_row(resp, product_categories=cats, metadata=copy.deepcopy(md))
        monkeypatch.setenv(FLAG, "true")
        on = _build_row(resp, product_categories=cats, metadata=copy.deepcopy(md))
        assert _strip_stamps(on) == _strip_stamps(off), cats
        for key in ("winner_index", "recommendation", "specs", "reviews", "products"):
            assert fy._normalize(on.get(key)) == fy._normalize(off.get(key)), key
        assert fy._normalize(on["scoring_v2"]) == fy._normalize(off["scoring_v2"])
        assert on["overview"]["winner"]["product_index"] == off["overview"]["winner"]["product_index"]
        assert on["comparison"]["winner_index"] == off["comparison"]["winner_index"]


# ================================================================ P10-P13 and the C9 rows

def test_b1_p10_canonical_categories_and_na_tokens_match_the_sources():
    rg = _need_rg()
    from app.services import extraction_service as es
    from app.services import scoring_service as sv

    assert set(getattr(rg, "CANONICAL_CATEGORIES", set())) == set(es.CATEGORY_SPEC_SCHEMAS.keys())
    assert set(rb._SPEC_NA_TOKENS) <= set(getattr(rg, "NA_VALUES", set()))
    assert getattr(rg, "SENTINEL_SCORE", None) == sv.MISSING_SCORE
    assert tuple(getattr(rg, "STATUSES", ())) == STATUSES
    assert tuple(getattr(rg, "CONFIDENCE_LEVELS", ())) == ("high", "medium", "low", "unresolved")
    assert tuple(getattr(rg, "REASONS", ())) == ("not_success", "placeholder_identity", "same_identity",
                                                  "unsupported_category", "category_conflict", "no_evidence")


def test_b1_p11_result_gate_is_pure():
    spec = importlib.util.find_spec(RG)
    assert spec is not None and spec.origin, "result_gate absent (RED at base)"
    src = Path(spec.origin).read_text(encoding="utf-8")
    assert all(ord(ch) < 128 for ch in src), "non-ASCII byte in result_gate.py"
    imports = re.findall(r"^(?:from|import)\s+([A-Za-z_][\w.]*)", src, flags=re.M)
    allowed = {"os", "re", "typing", "__future__", "app.services.text_sanitize"}
    assert set(imports) <= allowed, sorted(set(imports) - allowed)
    for banned in ("sentry_sdk", "structured_comparison_service", "response_builder", "price_service",
                   "extraction_service", "httpx", "asyncio", "socket", "logging"):
        assert banned not in src, banned
    assert "async def" not in src


def test_b1_p12_url_body_never_stamped(monkeypatch, client, rec):
    monkeypatch.setenv(FLAG, "true")
    r = _url(monkeypatch, client)
    assert r.status_code == 200, r.text[:300]
    body = r.json()
    assert "metadata" not in body, sorted(body)
    assert body.get("success") is True
    assert len(rec.calls) == 1 and rec.calls[0][2]["input_type"] == "url", rec.calls


def test_b1_p13_stamp_failure_degrades_to_flag_off(monkeypatch, caplog):
    assert getattr(rb, "assess_result", None) is not None, "response_builder.assess_result absent (RED at base)"
    resp = _lane1("grocery")
    monkeypatch.delenv(FLAG, raising=False)
    off = _build_row(resp, product_categories=["grocery", "grocery"])
    monkeypatch.setenv(FLAG, "true")

    def _boom(*_a, **_k):
        raise ValueError("probe")

    monkeypatch.setattr(rb, "assess_result", _boom)
    with caplog.at_level(logging.WARNING, logger="app.services.response_builder"):
        on = _build_row(resp, product_categories=["grocery", "grocery"])
    assert fy._normalize(on) == fy._normalize(off)
    lines = [r for r in caplog.records if r.levelno == logging.WARNING and "[RESULT_STATUS] assess failed" in r.getMessage()]
    assert len(lines) == 1, [r.getMessage() for r in caplog.records]
    assert lines[0].getMessage() == "[RESULT_STATUS] assess failed: ValueError"
    assert "probe" not in lines[0].getMessage()


def test_b1_c9c_assess_result_not_success_is_failed():
    """B1-R9 (c): `failed` is reachable only through a direct call (every B1 exit is success-only)."""
    rg = _need_rg()
    a = _fn(rg, "assess_result")({"success": False, "products": []})
    assert a["status"] == "failed" and a["reasons"][0] == "not_success", a
    a2 = _fn(rg, "assess_result")({})
    assert a2["status"] == "failed", a2
    a3 = _fn(rg, "assess_result")(None)
    assert a3["status"] == "failed" and a3["data_coverage"] == 0, a3


@pytest.mark.parametrize("cats", [["a", "b", "c"], None, "electronics", []])
def test_b1_c9d_product_categories_not_a_pair_key_omitted(monkeypatch, cats):
    monkeypatch.setenv(FLAG, "true")
    body = _build_row(_lane1("grocery"), product_categories=cats)
    md = body["metadata"]
    assert md.get("result_status") == "supported_result", md.get("result_status")
    assert "product_categories" not in md, md.get("product_categories")
    rg = _need_rg()
    assert _fn(rg, "assess_result")(body, product_categories=cats)["coherent"] is True


def test_b1_c9e_section_status_partial_when_one_side_empty(monkeypatch):
    monkeypatch.setenv(FLAG, "true")
    resp = _lane1("grocery")
    prods = copy.deepcopy(resp["products"])
    prods[1]["specs"] = {}
    body = _build_row(resp, product_categories=["grocery", "grocery"], products=prods)
    sec = body["metadata"].get("section_status") or {}
    assert sec.get("specs") == "partial", sec
    prods[1]["pros_cons"] = {"pros": [], "cons": []}
    prods[1]["pros"], prods[1]["cons"] = [], []
    body2 = _build_row(resp, product_categories=["grocery", "grocery"], products=prods)
    assert (body2["metadata"].get("section_status") or {}).get("pros_cons") == "partial"


# ================================================================ fix round 1 (RULINGS_FIX1_B1 F1-1..F1-6)
# Appended by the fix round on the GREEN bytes 2bbd58a9. Every row below fails there on an
# AssertionError only (a call that raised at 2bbd58a9 is turned into a value first).

CONFLICT_PAIR = ("Samsung Galaxy S24 phone", "Dior Sauvage eau de parfum")
CONFLICT_CATS = ["electronics", "fragrances"]
_ABSENT = object()


def _call_total(fn, *args, **kwargs):
    """fn(*args, **kwargs) with an exception turned into a value, so the row fails on an
    AssertionError and never on the exception itself."""
    try:
        return fn(*args, **kwargs)
    except Exception as exc:  # noqa: BLE001
        return "raised " + type(exc).__name__


def _assert_tags_equal_stamp(body, tags, label):
    """F1-1: on a category-conflict body the message tags equal the stamped body."""
    md = body.get("metadata") or {}
    assert md.get("product_categories") == CONFLICT_CATS, (label, md.get("product_categories"))
    assert md.get("result_status") == "unsupported_category", (label, md.get("result_status"))
    assert md.get("identity_confidence") == "low", (label, md.get("identity_confidence"))
    assert body["overview"]["winner"].get("supported") is False, label
    rg = _need_rg()
    stamp = _fn(rg, "assess_result")(body, product_categories=md["product_categories"])
    assert stamp["status"] == md["result_status"], (label, stamp["status"])
    assert stamp["identity_confidence"] == md["identity_confidence"], (label, stamp["identity_confidence"])
    assert "category_conflict" in stamp["reasons"], (label, stamp["reasons"])
    assert tags.get("result_status") == md["result_status"], (label, tags.get("result_status"))
    assert tags.get("identity_confidence") == md["identity_confidence"], (label, tags.get("identity_confidence"))
    assert tags.get("reasons") == ",".join(stamp["reasons"]), (label, tags.get("reasons"))
    assert tags.get("winner_emitted") == "false", (label, tags.get("winner_emitted"))


def _sse_complete(chunks):
    for chunk in chunks:
        text = _text(chunk)
        if text.startswith("event: complete\n"):
            return json.loads(text.split("data: ", 1)[1])
    raise AssertionError("no complete event: %r" % ([_text(c)[:24] for c in chunks],))


async def _stream_pair(monkeypatch, factory, pair):
    monkeypatch.setattr(text_routes, "get_comparison_service", factory)
    _quiet(monkeypatch, text_routes)
    resp = await text_routes.text_compare_stream(
        request=_FakeReq(), q=None, product_a=pair[0], product_b=pair[1],
        region="bahrain", specs=True, reviews=True, pros_cons=True, nocache=True,
        selected_category=None, lang=None, user=None)
    chunks = []
    async for c in resp.body_iterator:
        chunks.append(c)
    return chunks


def test_b1_f1_1a_emitter_tags_equal_the_stamp_on_a_conflict_body(monkeypatch, rec):
    """F1-1 (MAJ-1 / MAJ-E1): the emitter's assessment uses the STAMPED product_categories, so
    `unsupported_category` / `category_conflict` reach the message; one reader decides."""
    monkeypatch.setenv(FLAG, "true")
    body = _build_row(_lane1("grocery"), product_categories=list(CONFLICT_CATS))
    ss.capture_result_status(body, "camera", vision_ms=1234, compare_ms=5678)
    assert len(rec.calls) == 1, rec.calls
    message, level, tags, extras = rec.calls[0]
    assert message == "comparison_result_status" and level == "info", (message, level)
    _check_tags(tags, extras)
    _assert_tags_equal_stamp(body, tags, "emitter")
    rg = _need_rg()
    # the tag helper's own fallback (no assessment passed) reads the same stamp
    assert _fn(rg, "telemetry_tags")(body, "camera")["result_status"] == "unsupported_category"
    reader = getattr(rg, "stamped_product_categories", None)
    assert callable(reader), "result_gate.stamped_product_categories absent"
    assert reader(body) == CONFLICT_CATS
    for md, want in ((_ABSENT, None), ("garbage", None), ({}, None), ({"product_categories": None}, None),
                     ({"product_categories": "electronics"}, None),
                     ({"product_categories": ["a", "b", "c"]}, None),
                     ({"product_categories": [5, "fragrances"]}, [None, "fragrances"])):
        probe = {"success": True} if md is _ABSENT else {"success": True, "metadata": md}
        assert reader(probe) == want, (md, want)
    assert reader(None) is None and reader("x") is None
    # an unstamped body (flag OFF at the build) keeps today's tags: no category read
    monkeypatch.delenv(FLAG, raising=False)
    plain = _build_row(_lane1("grocery"), product_categories=list(CONFLICT_CATS))
    assert "product_categories" not in plain["metadata"]
    assert _fn(rg, "telemetry_tags")(plain, "camera")["result_status"] == "supported_result"


def test_b1_f1_1b_telemetry_equals_stamp_text_post_and_get_conflict_pair(monkeypatch, client, rec, fy_text):
    monkeypatch.setenv(FLAG, "true")
    r = client.post("/api/v1/text/compare", json={"product_a": CONFLICT_PAIR[0], "product_b": CONFLICT_PAIR[1]})
    assert r.status_code == 200, r.text[:300]
    assert len(rec.calls) == 1, rec.calls
    tags, extras = rec.calls[0][2], rec.calls[0][3]
    _check_tags(tags, extras)
    assert tags["input_type"] == "text"
    _assert_tags_equal_stamp(r.json(), tags, "text_post")
    r = client.get("/api/v1/text/compare", params={"product_a": CONFLICT_PAIR[0], "product_b": CONFLICT_PAIR[1],
                                                   "nocache": "true"})
    assert r.status_code == 200, r.text[:300]
    assert len(rec.calls) == 2, rec.calls
    _assert_tags_equal_stamp(r.json(), rec.calls[1][2], "text_get")


def test_b1_f1_1c_telemetry_equals_stamp_camera_conflict_body(monkeypatch, client, rec):
    monkeypatch.setenv(FLAG, "true")
    body = _build_row(_lane1("grocery"), product_categories=list(CONFLICT_CATS))
    r = _camera(monkeypatch, client, body)
    assert r.status_code == 200 and r.json().get("action") == "comparison", r.text[:300]
    assert len(rec.calls) == 1, rec.calls
    tags, extras = rec.calls[0][2], rec.calls[0][3]
    _check_tags(tags, extras)
    assert tags["input_type"] == "camera"
    _assert_tags_equal_stamp(r.json(), tags, "camera")


def test_b1_f1_1d_telemetry_equals_stamp_stream_conflict_pair(monkeypatch, rec, fy_text):
    monkeypatch.setenv(FLAG, "true")
    chunks = asyncio.run(_stream_pair(monkeypatch, text_routes.get_comparison_service, CONFLICT_PAIR))
    body = _sse_complete(chunks)
    assert len(rec.calls) == 1, rec.calls
    tags, extras = rec.calls[0][2], rec.calls[0][3]
    _check_tags(tags, extras)
    assert tags["input_type"] == "text_stream"
    _assert_tags_equal_stamp(body, tags, "stream")


def test_b1_f1_4_stream_twin_captures_categories_before_the_write_back(monkeypatch, rec):
    """F1-4 (X18s): a cross-category pair through the STREAM orchestrator twin keeps the per-product
    categories captured before the pair write-back (the FY25 pair is same-category); its message
    then equals the stamp (F1-1)."""
    monkeypatch.setenv(FLAG, "true")
    events = asyncio.run(fy._scenario("stream", fy.QUERY, explicit_pair=CONFLICT_PAIR, env={FLAG: "true"}))["payload"]
    body = fy._complete(events)
    md = body.get("metadata") or {}
    cu = body.get("category_used")
    assert [p.get("category") for p in body["products"]] == [cu, cu], [p.get("category") for p in body["products"]]
    assert md.get("product_categories") == CONFLICT_CATS, md.get("product_categories")
    assert md.get("result_status") == "unsupported_category", md.get("result_status")
    ss.capture_result_status(body, "text_stream")
    assert len(rec.calls) == 1, rec.calls
    _assert_tags_equal_stamp(body, rec.calls[0][2], "stream_twin")


PROFILE_SITES = ("prices", "names", "images")
PROFILE_WANT = {"prices": (100.0, 150.0), "names": ("Acme Alpha", "Beta Bravo"),
                "images": ("https://x.invalid/a.jpg", "https://x.invalid/b.jpg")}


def _profile_full(metadata=_ABSENT):
    full = {"winner_index": 0, "products": [
        {"brand": "Acme", "name": "Alpha", "price": {"amount": 100.0, "currency": "BHD"},
         "image_url": "https://x.invalid/a.jpg"},
        {"brand": "Beta", "name": "Bravo", "price": {"amount": 150.0, "currency": "BHD"},
         "image_url": "https://x.invalid/b.jpg"}]}
    if metadata is not _ABSENT:
        full["metadata"] = metadata
    return full


@pytest.mark.parametrize("site", PROFILE_SITES)
def test_b1_f1_2_profile_site_skips_stamped_non_supported_rows(site):
    """F1-2 (MAJ-2 / MAJ-E2, B1-R11 Q7): the three profile readers skip a row stamped with a
    non-supported status through home_routes._result_status_supported; an unstamped row and a
    stamped supported row count exactly as today (P8-style)."""
    from app.api import home_routes, profile_routes

    fn = {"prices": profile_routes._extract_winner_loser_prices,
          "names": profile_routes._extract_product_names,
          "images": profile_routes._extract_product_image_urls}[site]
    for md in (_ABSENT, "garbage", {}, {"cached": False}, {"winner_index": None},
               {"result_status": "supported_result"}):
        assert fn(_profile_full(md)) == PROFILE_WANT[site], (site, md)
    for status in ("partial_no_winner", "needs_identification", "unsupported_category", "failed"):
        assert fn(_profile_full({"result_status": status, "winner_index": None})) == (None, None), (site, status)
    assert getattr(profile_routes, "_result_status_supported", None) is home_routes._result_status_supported


def test_b1_f1_2b_profile_routes_skip_stamped_non_supported_rows(client):
    from tests.test_home_routes import _fake_user
    from tests.test_profile_routes import TestMonthlyStats, _comparison_row

    app.dependency_overrides[get_current_user] = _fake_user()
    rows = [_comparison_row(winner_idx=0, p0_price=100, p1_price=150, id_="a"),      # 50, unstamped
            _comparison_row(winner_idx=1, p0_price=300, p1_price=200, id_="b"),      # 100, stamped supported
            _comparison_row(winner_idx=0, p0_price=80, p1_price=120, id_="c")]       # stamped partial: skipped
    rows[1]["full_response"]["metadata"] = {"result_status": "supported_result"}
    rows[2]["full_response"]["metadata"] = {"result_status": "partial_no_winner", "winner_index": None}
    supabase = TestMonthlyStats()._patch_supabase(rows, [])
    with patch("app.api.profile_routes.get_user_supabase_client", return_value=supabase), \
            patch("app.api.profile_routes._redis_get", return_value=None), \
            patch("app.api.profile_routes._redis_set", return_value=True):
        resp = client.get("/api/v1/profile/monthly-stats", headers={"Authorization": "Bearer fake"})
    assert resp.status_code == 200, resp.text[:300]
    assert (resp.json()["decisions_count"], resp.json()["savings_bhd"]) == (2, 150.0), resp.json()
    supabase2 = MagicMock()
    comp_resp = MagicMock()
    comp_resp.data = rows
    supabase2.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value \
        .limit.return_value.execute.return_value = comp_resp
    with patch("app.api.profile_routes.get_user_supabase_client", return_value=supabase2), \
            patch("app.api.profile_routes._redis_get", return_value=None), \
            patch("app.api.profile_routes._redis_set", return_value=True):
        resp2 = client.get("/api/v1/profile/recent-decisions", headers={"Authorization": "Bearer fake"})
    assert resp2.status_code == 200, resp2.text[:300]
    assert [e["comparison_id"] for e in resp2.json()["recent"]] == ["a", "b"], resp2.json()


def test_b1_f1_3_training_data_fields_are_not_auditable_evidence(monkeypatch):
    """F1-3 (R-A4: model knowledge is not evidence): a `training_data` field is excluded from the
    AUDITABLE spec fact like a tier-3 synthesis; retrieved markers keep counting; the LITERAL
    reading is untouched."""
    rg = _need_rg()
    rows = _fn(rg, "real_spec_rows")
    assert rows({"color": "red", "_field_confidence": {"color": "training_data"}}, {"color": "blue"}) == 0
    assert rows({"color": "red"}, {"color": "blue", "_field_confidence": {"color": "training_data"}}) == 0
    assert rows({"color": "red", "weight": "1 kg", "_field_confidence": {"color": "training_data"}},
                {"color": "blue", "weight": "2 kg"}) == 1
    for retrieved in ("smart_fallback", "tier2_fallback", "snippet", "db"):
        assert rows({"color": "red", "_field_confidence": {"color": retrieved}}, {"color": "blue"}) == 1, retrieved
    monkeypatch.setenv(FLAG, "true")
    resp = _lane1("grocery")
    bodies = {}
    for marker in ("smart_fallback", "training_data"):
        prods = copy.deepcopy(resp["products"])
        prods[0]["specs"] = {"weight": "1 kg", "_field_confidence": {"weight": marker}}
        prods[1]["specs"] = {"weight": "2 kg"}
        bodies[marker] = _build_row(resp, product_categories=["grocery", "grocery"], products=prods)
    kept, model = bodies["smart_fallback"]["metadata"], bodies["training_data"]["metadata"]
    a_kept = _fn(rg, "assess_result")(bodies["smart_fallback"])
    a_model = _fn(rg, "assess_result")(bodies["training_data"])
    assert a_kept["facts"]["specs"] is True, a_kept["facts"]
    assert a_model["facts"]["specs"] is False, a_model["facts"]
    assert model.get("data_coverage") == kept.get("data_coverage") - 1, (model.get("data_coverage"), kept.get("data_coverage"))
    assert model.get("data_coverage_literal") == kept.get("data_coverage_literal"), (model, kept)
    assert a_model["facts_literal"] == a_kept["facts_literal"]


def test_b1_f1_5_wall_helpers_are_total_on_non_finite_and_non_int_walls(monkeypatch, rec, caplog):
    """F1-5: inf, -inf, nan, bool and str walls are absent (never raise) in telemetry_tags (its
    bucket), telemetry_extras, stamp_camera_stage_timings and the emitter's elapsed_ms fallback."""
    rg = _need_rg()
    extras_fn, tags_fn = _fn(rg, "telemetry_extras"), _fn(rg, "telemetry_tags")
    stamp = _fn(rg, "stamp_camera_stage_timings")
    assert _call_total(extras_fn, vision_ms=float("inf"), compare_ms=float("nan")) == {}
    body = _build_row(_w412(12))
    for bad in (float("inf"), float("-inf"), float("nan"), True, False, "1234"):
        got = _call_total(extras_fn, vision_ms=bad, compare_ms=bad)
        assert got == {}, (bad, got)
        tags = _call_total(tags_fn, body, "camera", vision_ms=bad, compare_ms=bad)
        assert isinstance(tags, dict), (bad, tags)
        assert "vision_ms" not in tags and "compare_ms" not in tags, (bad, sorted(tags))
    monkeypatch.setenv(FLAG, "true")
    for bad in (float("inf"), float("nan"), True, "1234"):
        result = {"metadata": {"stage_timings_ms": {"total_ms": 1.0}}}
        wrote = _call_total(stamp, result, vision_ms=bad, vision_moderation_ms=bad, compare_ms=bad)
        assert wrote is False, (bad, wrote)
        assert result["metadata"]["stage_timings_ms"] == {"total_ms": 1.0}, (bad, result)
    # the emitter: a non-finite metadata.elapsed_ms is an absent wall, and the message still goes out
    with caplog.at_level(logging.WARNING, logger="app.services.sentry_service"):
        for i, bad in enumerate((float("inf"), float("nan"))):
            probe = copy.deepcopy(body)
            probe["metadata"]["elapsed_ms"] = bad
            ss.capture_result_status(probe, "text")
            assert len(rec.calls) == i + 1, (bad, rec.calls)
            assert "compare_ms" not in rec.calls[i][2] and rec.calls[i][3] == {}, (bad, rec.calls[i])
    skipped = [r.getMessage() for r in caplog.records if "[RESULT_STATUS]" in r.getMessage()]
    assert skipped == [], skipped


def test_b1_f1_6_partial_stage_tag_is_whitelisted_to_the_server_constants():
    """F1-6: the `partial_stage` tag carries only a stage the server stamps (the return values of
    StructuredComparisonService._partial_stage, read from the source); an unknown value omits it."""
    import ast

    rg = _need_rg()
    tree = ast.parse(Path(inspect.getsourcefile(scs)).read_text(encoding="utf-8"))
    stages = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "_partial_stage":
            for sub in ast.walk(node):
                if isinstance(sub, ast.Return) and isinstance(sub.value, ast.Constant) \
                        and isinstance(sub.value.value, str):
                    stages.add(sub.value.value)
    assert stages == {"gather", "post_gather", "scoring", "verdict"}, stages
    assert set(getattr(rg, "PARTIAL_STAGES", None) or ()) == stages, getattr(rg, "PARTIAL_STAGES", None)
    tags_fn = _fn(rg, "telemetry_tags")
    base = _build_row(_w412(24), metadata={"partial": True, "partial_stage": "post_gather"})
    for stage in sorted(stages):
        probe = copy.deepcopy(base)
        probe["metadata"]["partial_stage"] = stage
        assert tags_fn(probe, "camera")["partial_stage"] == stage, stage
    for unknown in ("Gather", "warmup", "post gather", "", "x" * 40):
        probe = copy.deepcopy(base)
        probe["metadata"]["partial_stage"] = unknown
        tags = tags_fn(probe, "camera")
        assert "partial_stage" not in tags, (unknown, tags.get("partial_stage"))
    probe = copy.deepcopy(base)
    probe["metadata"]["partial"] = False
    assert tags_fn(probe, "camera")["partial_stage"] == "none"
    probe["metadata"]["partial"] = True
    probe["metadata"]["partial_stage"] = None
    assert tags_fn(probe, "camera")["partial_stage"] == "none"
