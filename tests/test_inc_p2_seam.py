"""INC-P2 PRICE-NOT-LOST (S96-FIX incident lane) RED rows: the seams (the REAL orchestrator
with stubbed fetches, the route, the stream, the partial build, the price cache).

Spec: .qa-s80/INC-P2_UNIT_SPEC.md section 5.2, as amended by RULINGS_INC_P2.md P2R-1..P2R-28
(section G: the capability token `price_size` in X-Client-Capabilities gates the both-shown
display; the route passes it down as compare_from_text(..., price_size_cap=True), bound for
the request by price_service.price_size_cap_bind; section H = ORCH-P2-B, superseding G where
they differ: a typed side at its own typed size is shown in every cell (the T3-01 pair shows
both prices on every app), the token gates ONLY an untyped side whose listing size differs
from the other side's, and no side flag OFF shows is lost because the token is absent) and
the brief's ADDENDA 1-2. The single RED amendment of P2R-27: agent B's frozen set, amended,
with agent A's unique seam rows ported onto B's seams.

Harness: tests/test_s75_fanout_identity.py (FY25: every LLM / network leaf faked) with the
REAL reconcile_pair_fairness restored, classify_category_llm answering fragrances and a fake
_get_price per typed half; resolver-ON cells replace _resolve_explicit_pair with the
apply_resolution Step-1 shape (no LLM). The route rows use the tests/test_retro_w2_1.py route
ledger through tests/test_inc_r1_seam.py's helper. Every row sets or deletes each flag it
depends on; the production configuration (H12 c + H13 c) is set in every row.

RED rows fail at the base on an AssertionError only; PIN rows are green at the base. Pure
ASCII, LF.
"""
from __future__ import annotations

import asyncio
import base64
import copy
import datetime as dt
import hashlib
import inspect
import json
import logging
import os
import re
import time

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("OPENAI_API_KEY", "sk" + "-test-dummy")

import app.main  # noqa: F401,E402  (FIRST: the dotenv guard)
from app.api import text_routes  # noqa: E402
from app.api.auth_routes import get_current_user, get_optional_user  # noqa: E402
from app.main import app as fastapi_app  # noqa: E402
from app.services import price_service as ps  # noqa: E402
from app.services import response_builder as rb  # noqa: E402
import app.services.structured_comparison_service as scs  # noqa: E402
from tests import test_s75_fanout_identity as fy  # noqa: E402
from tests import test_inc_r1_seam as r1  # noqa: E402

FLAG = "ENABLE_PRICE_NOT_LOST"
FIX = "ENABLE_FRAGRANCE_SIZE_RECONCILE_FIX"
RES = "ENABLE_PRODUCT_RESOLVER"
FRAG = "fragrances"
PROD_ON = (
    "ENABLE_LLM_LEDGER_V2", "ENABLE_LLM_SPEND_BREAKER", "ENABLE_REQUEST_CONTEXT_HEADERS",
    "ENABLE_OPENAI_EGRESS_STOP", "ENABLE_LEGACY_FINGERPRINT_READER", "ENABLE_CONSENT_PERSIST",
    "ENABLE_COMPARE_AUTH_REQUIRED", "ENABLE_OFFLOOP_DNS_RESOLVE", "ENABLE_PRICE_PARSE_OFFLOAD",
    "ENABLE_EXACT_PRICE_GATE",
)
PROD_OFF = (
    "ENABLE_ANTHROPIC_MODERATION", "ENABLE_ANTHROPIC_VISION", "ENABLE_KB_INGEST",
    "ENABLE_KB_FIRST_SERVE", "ENABLE_FIELD_STATUS_METADATA", "ENABLE_RESULT_STATUS_METADATA",
    "ENABLE_FRAGRANCE_ONLY_GATE", "ENABLE_DATA_GUARDS_V2", "ENABLE_ASYNC_REDIS_OFFLOAD",
    "ENABLE_COMPARE_RUN_LEDGER", "ENABLE_GENUINE_PRICE_PRIORITY", "ENABLE_LISTING_MATCH_GUARD",
    "ENABLE_REGION_CURRENCY_GUARD", "ENABLE_PRESCORING_SHOWABLE_GUARD", "WARMER_CONTEXT",
    "ENABLE_L2_PROMOTION_REMAINING_TTL", "ENABLE_FULL_STREAM_DEADLINE", "ENABLE_RESULT_GATE",
    "ENABLE_PARSE_PRESPLIT", "ENABLE_PARSE_BUDGET", "ENABLE_ANTHROPIC_TEXT", "ENABLE_ANTHROPIC_VERDICT",
    "ENABLE_OPENAI_PRE_V3", "ENABLE_NEGCACHE_GENUINE_INVALIDATION", "ENABLE_TITLE_PERSIST",
)
# The FY harness fakes generate_comparison at the module seam, so the two Claude role flags
# (ON on web) would only change which (faked) client is asked; they are walked ON in the
# pure file and in B17's prod cell below.
PROD_ROLE = ("ENABLE_ANTHROPIC_TEXT", "ENABLE_ANTHROPIC_VERDICT", "ENABLE_OPENAI_PRE_V3")


def need(name, mod=ps):
    obj = getattr(mod, name, None)
    assert obj is not None, "%s.%s is missing" % (mod.__name__, name)
    return obj


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    for name in PROD_OFF:
        monkeypatch.delenv(name, raising=False)
    for name in PROD_ON:
        monkeypatch.setenv(name, "true")
    for name in (FLAG, FIX, RES):
        monkeypatch.delenv(name, raising=False)
    for name in list(os.environ):
        if name.startswith("PRODUCT_RESOLVER_"):
            monkeypatch.delenv(name, raising=False)
    scs._DEBUG_STAGE_TIMINGS = None
    yield
    scs._DEBUG_STAGE_TIMINGS = None


def setflags(mp, flag=None, fix=None, res=None):
    for name, val in ((FLAG, flag), (FIX, fix), (RES, res)):
        if val is None:
            mp.delenv(name, raising=False)
        else:
            mp.setenv(name, val)


def P(amount, title, host="store-a", path="p/x", sm="local_bhd", **kw):
    out = {"amount": amount, "currency": "BHD", "estimated": False, "source_method": sm,
           "retailer": host + ".example.com", "url": "https://%s.example.com/%s" % (host, path),
           "title": title, "in_stock": True}
    out.update(kw)
    return out


TED_P = P(9.5, "Ted Baker M Eau De Toilette 30ml", "store-a", "p/ted-m-30")
DIOR_P = P(58.11, "Dior Sauvage EDP 100ml", "store-b", "p/sauvage-100")
YSL_P = P(39.0, "YSL Libre Eau de Parfum 90ml", "store-a", "p/libre-90")
LVEB_P = P(34.0, "Lancome La Vie Est Belle Eau de Parfum 100ml", "store-a", "p/lveb-100")
SAUV_100 = P(58.11, "Sauvage EDP 100ml", "store-b", "p/sv-100")
BLEU_150 = P(70.0, "Bleu de Chanel EDP 150ml", "store-a", "p/bleu-150", sm="local_bhd")
BLEU_100 = P(91.78, "Bleu de Chanel EDP 100ml", "store-b", "p/bleu-100", sm="page_scrape_jsonld")
TED_DIOR = ("Ted Baker M 30ml", "Dior Sauvage 100 ML Edp")
YSL_LVEB = ("YSL Libre EDP", "Lancome La Vie Est Belle EDP")
SAUV_BLEU = ("Sauvage EDP", "Bleu de Chanel EDP")
PRICES = {"Ted Baker M 30ml": TED_P, "Dior Sauvage 100 ML Edp": DIOR_P, "YSL Libre EDP": YSL_P,
          "Lancome La Vie Est Belle EDP": LVEB_P, "Sauvage EDP": SAUV_100, "Bleu de Chanel EDP": BLEU_150}
CANDS = {"Bleu de Chanel EDP": [BLEU_100]}
RESOLVED = {"Ted Baker M 30ml": ("Ted Baker", "M", "30ml", "Ted Baker M"),
            "Dior Sauvage 100 ML Edp": ("Dior", "Sauvage", "EDP 100ml", "Dior Sauvage EDP"),
            "Sauvage EDP": ("Dior", "Sauvage", "EDP", "Dior Sauvage EDP"),
            "Bleu de Chanel EDP": ("Chanel", "Bleu de Chanel", "EDP", "Chanel Bleu de Chanel EDP"),
            "YSL Libre EDP": ("YSL", "Libre", "EDP", "YSL Libre EDP"),
            "Lancome La Vie Est Belle EDP": ("Lancome", "La Vie Est Belle", "EDP", "Lancome La Vie Est Belle EDP")}


class Rec:
    def __init__(self):
        self.sets, self.db, self.gen, self.scores, self.price_calls = [], [], [], [], []


def install(p, svc, state, rec, *, prices=None, cands=None, res=False, l1=None):
    fy._install(p, svc, state)
    p.setattr(scs, "reconcile_pair_fairness", ps.reconcile_pair_fairness)

    async def _cat(*_a, **_k):
        return FRAG
    p.setattr(scs, "classify_category_llm", _cat)
    p.setattr(scs, "set_cached", lambda key, value, ttl: rec.sets.append((key, copy.deepcopy(value), ttl)) or True)
    p.setattr(scs, "get_cached", l1 or (lambda key: None))
    svc._save_price_to_db = lambda *a, **k: rec.db.append(a)
    prices = PRICES if prices is None else prices
    cands = CANDS if cands is None else cands
    by_query = {}
    for typed in prices:
        by_query[typed] = typed
        if typed in RESOLVED:
            by_query[RESOLVED[typed][3]] = typed

    async def _price(brand, name, variant, region, search_query, nocache=False, category="other"):
        typed = by_query.get(search_query) or by_query.get(name)
        rec.price_calls.append({"brand": brand, "name": name, "variant": variant, "region": region,
                                "search_query": search_query, "category": category, "typed": typed})
        fn = scs._shopping_cache_key(brand, name, variant)
        if cands.get(typed):
            svc._seed_shortcircuit_candidates(fn, kind="price_dicts", currency="BHD",
                                              price_dicts=copy.deepcopy(cands[typed]))
        return copy.deepcopy(prices[typed])
    svc._get_price = _price
    real_gen = scs.generate_comparison

    async def _gen(*a, **k):
        rec.gen.append(copy.deepcopy([a[0], a[1]]))
        return await real_gen(*a, **k)
    p.setattr(scs, "generate_comparison", _gen)
    real_ss = scs.get_scoring_service

    class _SS:
        def __init__(self):
            self._real = real_ss()

        def compute_scores(self, product_data, *a, **k):
            rec.scores.append(copy.deepcopy(product_data))
            return self._real.compute_scores(product_data, *a, **k)

        def __getattr__(self, n):
            return getattr(self._real, n)
    p.setattr(scs, "get_scoring_service", lambda: _SS())
    if res:
        async def _resolve(products, selected_category, start_time):
            for prod in products:
                r = RESOLVED.get(prod["name"])
                if r:
                    prod.update(brand=r[0], name=r[1], variant=r[2], search_query=r[3], category=FRAG)
            return None, True
        svc._resolve_explicit_pair = _resolve


def run(kind, pair, *, cap=False, prices=None, cands=None, res=False, rec=None, after=None, l1=None,
        hard_cap=30.0, gen_delay=0.0):
    """One compare on the faked pipeline; returns (payload, rec, svc). hard_cap / gen_delay
    drive the hard-cap and stream-tail partials (FY25's slow verdict leaf)."""
    rec = rec or Rec()
    p = fy._Patcher()
    state = fy._new_state()
    state["gen_delay"] = gen_delay
    try:
        p.setattr(scs, "STREAM_HARD_CAP_SECONDS", hard_cap)
        svc = scs.StructuredComparisonService()
        install(p, svc, state, rec, prices=prices, cands=cands, res=res, l1=l1)
        kw = {"explicit_pair": tuple(pair)}
        if cap:
            kw["price_size_cap"] = True
        q = "%s vs %s" % tuple(pair)
        if kind == "rest":
            payload = asyncio.run(asyncio.wait_for(svc.compare_from_text(q, region="bahrain", nocache=True, **kw), 60))
        else:
            payload = []

            async def _drain():
                async for ev in svc.compare_from_text_streaming(q, region="bahrain", nocache=True, **kw):
                    payload.append(list(ev))
            asyncio.run(asyncio.wait_for(_drain(), 60))
        if after is not None:
            after(svc, payload)
        return payload, rec, svc
    finally:
        p.undo()


def has_cap_kwarg():
    sig = inspect.signature(scs.StructuredComparisonService.compare_from_text)
    assert "price_size_cap" in sig.parameters, "compare_from_text(price_size_cap=...) is missing"


def complete(events):
    for k, d in events:
        if k == "complete":
            return d
    raise AssertionError("no complete event")


def event(events, kind):
    for k, d in events:
        if k == kind:
            return d
    raise AssertionError("no %s event" % kind)


def ov(body):
    return [p.get("price") for p in body["overview"]["products"]]


def shown(price):
    return isinstance(price, dict) and price.get("unavailable") is not True and isinstance(
        price.get("amount"), (int, float))


def pending(price, reason=None):
    ok = isinstance(price, dict) and price.get("unavailable") is True and price.get("amount") is None
    return ok and (reason is None or price.get("reason") == reason)


def p2_keys(obj, out):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if str(k).startswith("_p2"):
                out.append(k)
            p2_keys(v, out)
    elif isinstance(obj, list):
        for v in obj:
            p2_keys(v, out)
    return out


def digest(obj):
    raw = json.dumps(fy._normalize(obj), sort_keys=True, default=str).encode("utf-8")
    return base64.b64encode(hashlib.sha256(raw).digest()).decode("ascii")


FIXCELLS = [pytest.param(None, id="fix0"), pytest.param("true", id="fix1")]
RESCELLS = [pytest.param(False, id="res0"), pytest.param(True, id="res1")]
CAPCELLS = [pytest.param(True, id="cap1"), pytest.param(False, id="cap0")]


# --------------------------------------------------------------------------- B01-B02 the service seam
@pytest.mark.parametrize("cap", CAPCELLS)
@pytest.mark.parametrize("res", RESCELLS)
@pytest.mark.parametrize("fix", FIXCELLS)
def test_b01_rest_ted_dior(monkeypatch, fix, res, cap):
    """B01 RED (service), REWRITTEN by ORCH-P2-B rule 1 (P2R-23): the T3-01 pair through the
    real orchestrator: BOTH capability cells show Ted 9.500 (size_ml 30) and Dior 58.110
    (size_ml 100) on the overview and the legacy alias, never an offsize_listing, never a
    _p2_ key (the token changes nothing for two typed sides at their typed sizes)."""
    has_cap_kwarg()
    setflags(monkeypatch, flag="true", fix=fix, res="true" if res else None)
    body, _, _ = run("rest", TED_DIOR, cap=cap, res=res)
    w, lg = ov(body), [p.get("price") for p in body["products"]]
    assert shown(w[0]) and w[0]["amount"] == 9.5 and w[0].get("size_ml") == 30, w[0]
    assert shown(w[1]) and w[1]["amount"] == 58.11 and w[1].get("size_ml") == 100, w[1]
    assert lg[0]["amount"] == 9.5 and lg[1]["amount"] == 58.11, lg
    assert "offsize_listing" not in w[0] and "offsize_listing" not in w[1]
    assert p2_keys(body, []) == []


@pytest.mark.parametrize("cap", CAPCELLS)
@pytest.mark.parametrize("fix", FIXCELLS)
@pytest.mark.parametrize("pair", ["ted_dior", "ysl_lveb"])
def test_b02_stream_complete_and_prices(monkeypatch, pair, fix, cap):
    """B02 RED, REWRITTEN by ORCH-P2-B: the stream. ted_dior (rule 1): the complete event and
    the SSE prices event show Dior 58.110 with size_ml 100 in BOTH cells. ysl_lveb (rule 2,
    two untyped sides): YSL is shown with size_ml 90 under cap1 and held (pending
    size_mismatch + offsize_listing 39.000) under cap0, on the complete and prices events."""
    has_cap_kwarg()
    setflags(monkeypatch, flag="true", fix=fix)
    if pair == "ted_dior":
        events, _, _ = run("stream", TED_DIOR, cap=cap)
        w = ov(complete(events))
        pr = event(events, "prices")["product_1"]
        assert w[1]["amount"] == 58.11 and pr["price"].get("amount") == 58.11, (w[1], pr)
        assert pr["price"].get("size_ml") == 100 and pr["best_price"] == 58.11
        assert "offsize_listing" not in pr["price"] and "offsize_listing" not in w[1]
    else:
        events, _, _ = run("stream", YSL_LVEB, cap=cap)
        w = ov(complete(events))
        pr = event(events, "prices")["product_0"]
        if cap:
            assert w[0]["amount"] == 39.0 and pr["price"].get("amount") == 39.0, (w[0], pr)
            assert pr["price"].get("size_ml") == 90 and pr["best_price"] == 39.0
        else:
            assert pending(w[0], "size_mismatch") and pending(pr["price"], "size_mismatch"), (w[0], pr)
            assert (pr["price"].get("offsize_listing") or {}).get("amount") == 39.0
            assert (w[0].get("offsize_listing") or {}).get("amount") == 39.0
        assert shown(w[1]) and w[1]["amount"] == 34.0
    assert p2_keys(events, []) == []


@pytest.mark.parametrize("cap", CAPCELLS)
def test_b03_partial_build_equals_full(monkeypatch, caplog, cap):
    """B03 RED (X1-R1): a partial built AFTER the full build on the same reconciled dicts
    carries exactly the full build's prices and marker; its price dim is still
    limited_data (the restore never mutated the dicts); it prints PRICE_OUTCOME too."""
    has_cap_kwarg()
    setflags(monkeypatch, flag="true", fix="true")
    caplog.set_level(logging.INFO)
    got = {}

    def _after(svc, payload):
        import contextvars

        def _p():
            need("price_size_cap_bind")(cap)
            return svc._build_partial_response(elapsed_seconds=1.0)
        caplog.clear()
        got["partial"] = contextvars.copy_context().run(_p)
        got["lines"] = [r.getMessage() for r in caplog.records if r.getMessage().startswith("PRICE_OUTCOME")]
    body, _, _ = run("rest", TED_DIOR, cap=cap, after=_after)
    part = got["partial"]
    assert ov(part) == ov(body)
    assert part["metadata"].get("pair_price_sizes") == body["metadata"].get("pair_price_sizes") is not None
    dm = {d["key"]: d for d in part["scoring_v2"]["dimensions"]}
    assert dm["price"].get("caption_key") == "limited_data"
    assert len(got["lines"]) == 2


@pytest.mark.parametrize("fix", FIXCELLS)
def test_b00_harness_is_the_fragrance_path_pin(monkeypatch, fix):
    """B00 PIN (ported from agent A's b00): the faked pipeline is a fragrance pair and pends
    Dior for size today (flag OFF, the full configuration): the harness reaches the reconcile
    every seam row of this file relies on."""
    setflags(monkeypatch, flag=None, fix=fix)
    body, rec, _ = run("rest", TED_DIOR)
    assert body.get("success") is not False, str(body)[:300]
    assert {c["category"] for c in rec.price_calls} == {FRAG}, rec.price_calls
    w = ov(body)
    assert shown(w[0]) and w[0]["amount"] == 9.5, w[0]
    assert pending(w[1], "size_mismatch"), w[1]


@pytest.mark.parametrize("cap", CAPCELLS)
def test_b03s_stream_tail_partial_stamps_the_size(monkeypatch, cap):
    """B03s RED (ported from agent A's b03s; it narrows D8: the stream's gather-stage tail
    partial IS drivable on this harness): ENABLE_FULL_STREAM_DEADLINE on, a 1.5 s hard cap and
    a 5 s verdict leaf: the complete event is the tail partial (metadata.partial true), and
    under the flag both T3-01 sides are shown with their size_ml (30 / 100) in both cells,
    with the pair marker, never a _p2_ key."""
    has_cap_kwarg()
    setflags(monkeypatch, flag="true", fix="true")
    monkeypatch.setenv("ENABLE_FULL_STREAM_DEADLINE", "true")
    events, _, _ = run("stream", TED_DIOR, cap=cap, hard_cap=1.5, gen_delay=5.0)
    body = complete(events)
    assert (body.get("metadata") or {}).get("partial") is True, (body.get("metadata") or {})
    w = ov(body)
    assert [p.get("amount") for p in w] == [9.5, 58.11], w
    assert [p.get("size_ml") for p in w] == [30, 100], w
    assert body["metadata"].get("pair_price_sizes") == {"mode": "different_sizes", "sizes_ml": [30, 100]}
    assert p2_keys(events, []) == []


# --------------------------------------------------------------------------- the route (P2R-18)
@pytest.fixture
def client():
    return TestClient(fastapi_app, raise_server_exceptions=False)


@pytest.fixture
def authed(request):
    user = {"id": ("inc-p2-" + request.node.name)[:120], "email": "inc-p2@example.test",
            "access_token": "inc-p2-synthetic"}
    saved = dict(fastapi_app.dependency_overrides)
    fastapi_app.dependency_overrides[get_optional_user] = lambda: user
    fastapi_app.dependency_overrides[get_current_user] = lambda: user
    from app.middleware.rate_limiter import limiter
    prior = limiter.enabled
    limiter.enabled = False
    yield user
    limiter.enabled = prior
    fastapi_app.dependency_overrides.clear()
    fastapi_app.dependency_overrides.update(saved)


@pytest.fixture
def svc_factory(monkeypatch):
    p = fy._Patcher()
    state = fy._new_state()
    rec = Rec()

    async def _none(*_a, **_k):
        return None

    def _factory():
        svc = scs.StructuredComparisonService()
        install(p, svc, state, rec)
        svc._fetch_behavior_profile = _none
        p.setattr(scs, "get_user_demographics", _none)
        return svc
    monkeypatch.setattr(text_routes, "get_comparison_service", _factory)
    try:
        yield rec
    finally:
        p.undo()


def route_env(mp):
    mp.setenv("ENABLE_PAID_ROUTE_METERING", "true")
    mp.setenv("ENABLE_CAMERA_FAILURE_ENVELOPE", "true")
    r1._ledger(mp)


@pytest.mark.parametrize("header", [None, "price_asof", " Price_Size ", "price_asof, price_size"],
                         ids=["absent", "other", "mixed", "list"])
def test_r01_get_route_header(monkeypatch, client, authed, svc_factory, header):
    """R01 RED (P2R-18/21; REWRITTEN onto the untyped YSL / Lancome pair by ORCH-P2-B rule 2,
    since the T3-01 pair no longer depends on the token): GET /api/v1/text/compare (the
    phone's route): the token shows YSL's 39.000 with size_ml 90; without it YSL is held
    (pending size_mismatch) with its offsize_listing; Lancome is shown in every cell."""
    setflags(monkeypatch, flag="true", fix="true")
    route_env(monkeypatch)
    h = {} if header is None else {"X-Client-Capabilities": header}
    resp = client.get("/api/v1/text/compare", params={"product_a": YSL_LVEB[0], "product_b": YSL_LVEB[1]}, headers=h)
    assert resp.status_code == 200, resp.text[:300]
    w = ov(resp.json())
    if header and "price_size" in header.lower():
        assert shown(w[0]) and w[0]["amount"] == 39.0 and w[0].get("size_ml") == 90, w[0]
    else:
        assert pending(w[0], "size_mismatch") and (w[0].get("offsize_listing") or {}).get("amount") == 39.0, w[0]
    assert shown(w[1]) and w[1]["amount"] == 34.0, w[1]


def test_r02_post_route_header(monkeypatch, client, authed, svc_factory):
    """R02 RED (REWRITTEN onto the untyped pair, as R01): POST /api/v1/text/compare with the
    token shows YSL's amount with size_ml 90."""
    setflags(monkeypatch, flag="true", fix="true")
    route_env(monkeypatch)
    resp = client.post("/api/v1/text/compare", json={"product_a": YSL_LVEB[0], "product_b": YSL_LVEB[1]},
                       headers={"X-Client-Capabilities": "price_size"})
    assert resp.status_code == 200, resp.text[:300]
    w = ov(resp.json())
    assert w[0].get("amount") == 39.0 and w[0].get("size_ml") == 90, w[0]


@pytest.mark.parametrize("header", [None, "price_asof", "price_size"], ids=["absent", "other", "token"])
def test_r04_get_route_t3_01_every_app(monkeypatch, client, authed, svc_factory, header):
    """R04 RED (ORCH-P2-B rule 1, P2R-23 'the T3-01 pair shows both prices on every app'):
    GET /api/v1/text/compare for 'Ted Baker M 30ml' vs 'Dior Sauvage 100 ML Edp' shows both
    amounts whatever X-Client-Capabilities carries (today's phones send none)."""
    setflags(monkeypatch, flag="true", fix="true")
    route_env(monkeypatch)
    h = {} if header is None else {"X-Client-Capabilities": header}
    resp = client.get("/api/v1/text/compare", params={"product_a": TED_DIOR[0], "product_b": TED_DIOR[1]}, headers=h)
    assert resp.status_code == 200, resp.text[:300]
    w = ov(resp.json())
    assert shown(w[0]) and w[0]["amount"] == 9.5, w[0]
    assert shown(w[1]) and w[1]["amount"] == 58.11 and w[1].get("size_ml") == 100, w[1]
    assert "offsize_listing" not in w[1]


def test_r03_route_flag_off_with_token(monkeypatch, client, authed, svc_factory):
    """R03 PIN: flag OFF with the token: today's body (Dior pending, no new key)."""
    setflags(monkeypatch, flag=None, fix="true")
    route_env(monkeypatch)
    resp = client.get("/api/v1/text/compare", params={"product_a": TED_DIOR[0], "product_b": TED_DIOR[1]},
                      headers={"X-Client-Capabilities": "price_size"})
    assert resp.status_code == 200, resp.text[:300]
    w = ov(resp.json())
    assert pending(w[1], "size_mismatch") and not ({"offsize_listing", "size_ml"} & set(w[1])), w[1]


# --------------------------------------------------------------------------- cache what is shown (P2-7)
@pytest.mark.parametrize("res", RESCELLS)
def test_b04_b05_cache_reselected_and_read_back(monkeypatch, caplog, res):
    """B04 (res0) / B05 (res1) RED: run 1 re-selects Bleu to 91.780 and writes it under the
    key _get_price reads for Bleu's Step-1 dict, at price_cache_ttl, with _seen_at; run 2
    reads it back from L1 and logs PRICE_CACHE_HIT layer=l1."""
    setflags(monkeypatch, flag="true", fix="true", res="true" if res else None)
    caplog.set_level(logging.INFO)
    body, rec, _ = run("rest", SAUV_BLEU, res=res)
    assert ov(body)[1]["amount"] == 91.78
    call = [c for c in rec.price_calls if c["typed"] == "Bleu de Chanel EDP"][0]
    key = ps.build_size_aware_price_cache_key(call["brand"], call["name"], call["variant"], call["region"],
                                              call["search_query"], category=call["category"])
    writes = [w for w in rec.sets if w[0] == key]
    assert len(writes) == 1, [w[0] for w in rec.sets]
    _, value, ttl = writes[0]
    assert value["amount"] == 91.78 and ttl == ps.price_cache_ttl(value)
    seen = value.get("_seen_at")
    assert isinstance(seen, str) and dt.datetime.fromisoformat(seen.replace("Z", "+00:00")).tzinfo is not None
    p = fy._Patcher()
    try:
        p.setattr(scs, "get_cached", lambda k: copy.deepcopy(value) if k == key else None)
        svc = scs.StructuredComparisonService()
        caplog.clear()
        got = asyncio.run(svc._get_price(call["brand"], call["name"], call["variant"], call["region"],
                                         call["search_query"], nocache=False, category=call["category"]))
    finally:
        p.undo()
    assert got["amount"] == 91.78
    assert any(r.getMessage().startswith("PRICE_CACHE_HIT layer=l1") for r in caplog.records)


def test_b06_never_cache_refused_or_converted_over_genuine(monkeypatch, caplog):
    """B06 RED (P2R-5): a re-selected price should_cache_price refuses is not written and
    PRICE_CACHE_SKIP names the reason; a converted re-selection never overwrites a genuine
    entry already under the key."""
    setflags(monkeypatch, flag="true", fix="true")
    caplog.set_level(logging.INFO)
    bad = dict(BLEU_100, url=None)
    body, rec, _ = run("rest", SAUV_BLEU, cands={"Bleu de Chanel EDP": [bad]})
    assert ov(body)[1].get("amount") == 91.78, ov(body)[1]
    assert rec.sets == [], rec.sets
    assert any(re.match(r"PRICE_CACHE_SKIP reason=no_url", r.getMessage()) for r in caplog.records), \
        [r.getMessage() for r in caplog.records if "PRICE_CACHE" in r.getMessage()]
    conv = dict(BLEU_100, source_method="converted_usd")
    reads = []

    def _l1(k):
        reads.append(k)
        return dict(BLEU_100)
    caplog.clear()
    body2, rec2, _ = run("rest", SAUV_BLEU, cands={"Bleu de Chanel EDP": [conv]}, l1=_l1)
    assert ov(body2)[1].get("amount") == 91.78 and ov(body2)[1].get("source_method") == "converted_usd"
    assert reads, "the key was not read before a converted write"
    assert [w for w in rec2.sets if w[1].get("source_method") == "converted_usd"] == []


def _cache_reselected_call(monkeypatch, set_fn):
    """Drive SCS._p2_cache_reselected directly with one re-selected, shown Bleu 100 ml side."""
    fn = need("_p2_cache_reselected", scs.StructuredComparisonService)

    async def _get_none(_k):
        return None
    monkeypatch.setattr(scs, "_cache_set_async", set_fn)
    monkeypatch.setattr(scs, "_cache_get_async", _get_none)
    svc = scs.StructuredComparisonService()
    svc._save_price_to_db = lambda *a, **k: None
    products = [{"brand": "", "name": n, "variant": None, "category": FRAG, "search_query": n} for n in SAUV_BLEU]
    pd = [{"full_name": SAUV_BLEU[0], "name": SAUV_BLEU[0], "price": dict(SAUV_100)},
          {"full_name": SAUV_BLEU[1], "name": SAUV_BLEU[1], "price": dict(BLEU_100), "_p2_reselected": True}]
    return asyncio.run(fn(svc, products, pd, "bahrain"))


@pytest.mark.parametrize("mode", ["slow", "raising"])
def test_b06d_cache_write_is_bounded_and_swallowed(monkeypatch, caplog, mode):
    """B06d RED (ported from agent A's b06d; P2R-5): the P2-7 write is inline and bounded by
    asyncio.wait_for of 1.0 s: a cache write that hangs (5 s) returns within 2.5 s, and a
    write that raises never raises out; either failure is swallowed with ONE WARNING."""
    setflags(monkeypatch, flag="true", fix="true")
    caplog.set_level(logging.WARNING)

    async def _slow(*_a, **_k):
        await asyncio.sleep(5)

    async def _raise(*_a, **_k):
        raise RuntimeError("cache down")
    t0 = time.monotonic()
    _cache_reselected_call(monkeypatch, _slow if mode == "slow" else _raise)
    assert time.monotonic() - t0 < 2.5
    warns = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warns) == 1, [r.getMessage() for r in warns]


@pytest.mark.parametrize("fix", FIXCELLS)
def test_b07_flag_off_cache_identity(monkeypatch, fix):
    """B07 PIN (full configuration + recorders): flag OFF, run 1 writes nothing to L1 or L2
    (the base writes on this faked pipeline)."""
    setflags(monkeypatch, flag=None, fix=fix)
    _, rec, _ = run("rest", SAUV_BLEU)
    assert rec.sets == [] and rec.db == []


@pytest.mark.parametrize("age,exp", [(120, "120"), (None, "unknown")])
def test_b08_cache_hit_l2(monkeypatch, caplog, age, exp):
    """B08 RED (+ C-2): an L2 hit logs PRICE_CACHE_HIT layer=l2 age_s=<age or unknown>."""
    caplog.set_level(logging.INFO)
    from app.services import product_data_service as pds
    row = dict(BLEU_100)
    if age is not None:
        row["_l2_age_seconds"] = age

    async def _l2(key, region):
        return dict(row)
    p = fy._Patcher()
    try:
        p.setattr(scs, "get_cached", lambda k: None)
        p.setattr(scs, "set_cached", lambda *a, **k: True)
        p.setattr(pds, "get_cached_price", _l2)
        svc = scs.StructuredComparisonService()
        got = asyncio.run(svc._get_price("", "Bleu de Chanel EDP", None, "bahrain", "Bleu de Chanel EDP",
                                         nocache=False, category=FRAG))
    finally:
        p.undo()
    assert got["amount"] == 91.78
    msgs = [r.getMessage() for r in caplog.records if r.getMessage().startswith("PRICE_CACHE_HIT")]
    assert msgs and msgs[0].startswith("PRICE_CACHE_HIT layer=l2 age_s=%s" % exp), msgs


def test_b19_cache_hit_logger_raising(monkeypatch):
    """B19 RED (P2R-10): a logger raising on PRICE_CACHE_HIT inside the price task never
    loses the cached price (the line was attempted)."""
    attempts = []
    real = scs.logger.info

    def _info(msg, *a, **k):
        if str(msg).startswith("PRICE_CACHE_HIT"):
            attempts.append(1)
            raise RuntimeError("logger down")
        return real(msg, *a, **k)
    p = fy._Patcher()
    try:
        p.setattr(scs.logger, "info", _info)
        p.setattr(scs, "get_cached", lambda k: dict(BLEU_100))
        svc = scs.StructuredComparisonService()
        got = asyncio.run(svc._get_price("", "Bleu de Chanel EDP", None, "bahrain", "Bleu de Chanel EDP",
                                         nocache=False, category=FRAG))
    finally:
        p.undo()
    assert got["amount"] == 91.78 and attempts == [1]


def test_b20_cache_skip_persist_and_raising(monkeypatch, caplog):
    """B20 RED (C-5 b, P2R-4, P2R-10): _persist_genuine_price keeps should_cache_price as
    the gate (a patched gate still decides), logs PRICE_CACHE_SKIP with the reason on a
    refusal, and a raising logger there never raises out."""
    caplog.set_level(logging.INFO)
    svc = scs.StructuredComparisonService()
    rec = Rec()
    p = fy._Patcher()
    try:
        p.setattr(scs, "set_cached", lambda k, v, t: rec.sets.append((k, v, t)) or True)
        svc._save_price_to_db = lambda *a, **k: rec.db.append(a)
        asyncio.run(svc._persist_genuine_price("k1", dict(BLEU_100, url=None), "", "Bleu de Chanel EDP", None,
                                               "bahrain", "Bleu de Chanel EDP", FRAG))
        assert rec.sets == []
        assert any(r.getMessage().startswith("PRICE_CACHE_SKIP reason=no_url") for r in caplog.records)
        p.setattr(scs, "should_cache_price", lambda *a, **k: True)
        asyncio.run(svc._persist_genuine_price("k2", {"amount": 1.0, "currency": "BHD"}, "", "x", None,
                                               "bahrain", "x", FRAG))
        assert [s[0] for s in rec.sets] == ["k2"]
        p.setattr(scs, "should_cache_price", lambda *a, **k: False)
        real = scs.logger.info

        def _info(msg, *a, **k):
            if str(msg).startswith("PRICE_CACHE_SKIP"):
                raise RuntimeError("logger down")
            return real(msg, *a, **k)
        p.setattr(scs.logger, "info", _info)
        asyncio.run(svc._persist_genuine_price("k3", dict(BLEU_100), "", "Bleu de Chanel EDP", None,
                                               "bahrain", "Bleu de Chanel EDP", FRAG))
    finally:
        p.undo()
    assert [s[0] for s in rec.sets] == ["k2"]


def test_b21_direct_hit_site_uses_skip_line():
    """B21 RED (C-5 b): the adapter direct-hit write keeps `if should_cache_price(` as its
    gate and logs PRICE_CACHE_SKIP with site=direct_hit on a refusal (source read)."""
    src = inspect.getsource(scs.StructuredComparisonService._get_price)
    i = src.find("bypass site 2 of 5")
    assert i > 0
    window = src[max(0, i - 600): i + 900]
    assert "if should_cache_price(full_name, best, category):" in window
    assert "direct_hit" in window


@pytest.mark.parametrize("flag", [None, "true"])
def test_b22_seen_at(monkeypatch, flag):
    """B22 RED / PIN (P2R-6): flag ON a persisted price carries _seen_at (ISO-8601 UTC), an
    existing _seen_at is kept; flag OFF the written value equals the input (PIN)."""
    setflags(monkeypatch, flag=flag)
    svc = scs.StructuredComparisonService()
    rec = Rec()
    p = fy._Patcher()
    try:
        p.setattr(scs, "set_cached", lambda k, v, t: rec.sets.append((k, copy.deepcopy(v), t)) or True)
        svc._save_price_to_db = lambda *a, **k: rec.db.append(a)
        asyncio.run(svc._persist_genuine_price("k1", dict(BLEU_100), "", "Bleu de Chanel EDP", None,
                                               "bahrain", "Bleu de Chanel EDP", FRAG))
        asyncio.run(svc._persist_genuine_price("k2", dict(BLEU_100, _seen_at="2026-11-01T00:00:00+00:00"), "",
                                               "Bleu de Chanel EDP", None, "bahrain", "Bleu de Chanel EDP", FRAG))
    finally:
        p.undo()
    v1, v2 = rec.sets[0][1], rec.sets[1][1]
    if flag:
        assert isinstance(v1.get("_seen_at"), str), v1
        assert dt.datetime.fromisoformat(v1["_seen_at"]).utcoffset() == dt.timedelta(0)
        assert v2["_seen_at"] == "2026-11-01T00:00:00+00:00"
    else:
        assert v1 == BLEU_100


def test_b23_seen_at_l2_promotion(monkeypatch):
    """B23 RED (P2R-6): flag ON an L2 -> L1 promotion carries _seen_at = now - the row
    age when the age is known."""
    setflags(monkeypatch, flag="true")
    monkeypatch.setenv("ENABLE_L2_PROMOTION_REMAINING_TTL", "true")
    from app.services import product_data_service as pds
    sets = []

    async def _l2(key, region):
        return dict(BLEU_100, _l2_age_seconds=3600)
    p = fy._Patcher()
    try:
        p.setattr(scs, "get_cached", lambda k: None)
        p.setattr(scs, "set_cached", lambda k, v, t: sets.append(copy.deepcopy(v)) or True)
        p.setattr(pds, "get_cached_price", _l2)
        svc = scs.StructuredComparisonService()
        asyncio.run(svc._get_price("", "Bleu de Chanel EDP", None, "bahrain", "Bleu de Chanel EDP",
                                   nocache=False, category=FRAG))
    finally:
        p.undo()
    assert sets, "no promotion"
    assert isinstance(sets[0].get("_seen_at"), str), sets[0]
    seen = dt.datetime.fromisoformat(sets[0]["_seen_at"])
    age = (dt.datetime.now(dt.timezone.utc) - seen).total_seconds()
    assert 3500 < age < 3700, age


# --------------------------------------------------------------------------- reseller park (P2-9)
SHOP_BEST = P(55.0, "Dior Sauvage EDP 100ml", "reseller-c", "p/sv-100", sm="shopify_json")
CONV_PARK = P(50.76, "Dior Sauvage EDP 100ml", "store-us", "p/sv", sm="converted_usd")


@pytest.mark.parametrize("prio", [None, "true"])
def test_b09_reseller_parked_and_served(monkeypatch, prio):
    """B09 RED: flag ON the Shopify reseller hit replaces a converted park, is seeded as a
    candidate, and a race miss serves it (priority off and on)."""
    fn = need("_p2_park_reseller", scs.StructuredComparisonService)
    setflags(monkeypatch, flag="true")
    if prio:
        monkeypatch.setenv("ENABLE_GENUINE_PRICE_PRIORITY", prio)
    svc = scs.StructuredComparisonService()
    full = "Dior Sauvage EDP"
    svc._parked_price[full] = dict(CONV_PARK)
    fn(svc, full, dict(SHOP_BEST), [dict(SHOP_BEST)], "BHD")
    assert svc._parked_price[full]["source_method"] == "shopify_json"
    assert any((c.get("raw_data") or {}).get("amount") == 55.0 for c in svc._price_candidates.get(full, []))
    got = svc._price_fallback_on_miss("price", full, FRAG)
    assert got and got["amount"] == 55.0


def test_b10_genuine_park_kept(monkeypatch):
    """B10 RED: a genuine park already present is never replaced; the hit is still seeded;
    a park _is_listing_url marks IS replaced (P2R-9)."""
    fn = need("_p2_park_reseller", scs.StructuredComparisonService)
    setflags(monkeypatch, flag="true")
    svc = scs.StructuredComparisonService()
    full = "Dior Sauvage EDP"
    genuine = P(60.0, "Dior Sauvage EDP 100ml", "store-b", "p/sv", sm="noon")
    svc._parked_price[full] = dict(genuine)
    fn(svc, full, dict(SHOP_BEST), [dict(SHOP_BEST)], "BHD")
    assert svc._parked_price[full]["amount"] == 60.0
    assert any((c.get("raw_data") or {}).get("amount") == 55.0 for c in svc._price_candidates.get(full, []))
    svc._parked_price[full] = dict(genuine, url="https://store-b.example.com/search?q=sauvage")
    fn(svc, full, dict(SHOP_BEST), [dict(SHOP_BEST)], "BHD")
    assert svc._parked_price[full]["amount"] == 55.0


def test_b11_reseller_flag_off(monkeypatch):
    """B11 PIN (full configuration): flag OFF the park and candidates are unchanged, and
    the reseller call site exists only beside the local fallback (source read)."""
    setflags(monkeypatch, flag=None)
    svc = scs.StructuredComparisonService()
    full = "Dior Sauvage EDP"
    svc._parked_price[full] = dict(CONV_PARK)
    fn = getattr(scs.StructuredComparisonService, "_p2_park_reseller", None)
    if fn is not None:
        fn(svc, full, dict(SHOP_BEST), [dict(SHOP_BEST)], "BHD")
    assert svc._parked_price[full] == CONV_PARK and svc._price_candidates.get(full, []) == []


def test_b11b_reseller_call_site():
    """B11b RED: the reseller branch calls the park helper right after the local fallback."""
    src = inspect.getsource(scs.StructuredComparisonService._get_price)
    i = src.find("shopify_fallback = shop_best")
    assert i > 0 and "self._p2_park_reseller(" in src[i: i + 600]


def test_b12_adapter_converted_park_filtered():
    """B12 RED (C-5 a; B13 folded in): the adapter converted park passes its rows through
    p2_filter_marketplace_rows (source read; the predicate is A37)."""
    src = inspect.getsource(scs.StructuredComparisonService._get_price)
    i = src.find("_conv_best = select_best(")
    assert i > 0 and "p2_filter_marketplace_rows(" in src[i: i + 400]


# --------------------------------------------------------------------------- matrix, consumers, logs
@pytest.mark.parametrize("cap", CAPCELLS)
@pytest.mark.parametrize("res", RESCELLS)
@pytest.mark.parametrize("fix", FIXCELLS)
@pytest.mark.parametrize("pair", ["ted_dior", "ysl_lveb"])
def test_b14_matrix_flag_on(monkeypatch, pair, fix, res, cap):
    """B14 RED (ON cells), REWRITTEN by ORCH-P2-B: ted_dior (two typed sides at their typed
    sizes, rule 1) shows both prices in BOTH cells with no offsize_listing; ysl_lveb (two
    untyped sides, rule 2) shows both under cap1 and holds the off-size side (pending +
    offsize_listing) under cap0, the other side shown (rule 4)."""
    has_cap_kwarg()
    setflags(monkeypatch, flag="true", fix=fix, res="true" if res else None)
    pr = TED_DIOR if pair == "ted_dior" else YSL_LVEB
    body, _, _ = run("rest", pr, cap=cap, res=res)
    w = ov(body)
    if cap or pair == "ted_dior":
        assert all(shown(p) for p in w), w
        assert all("offsize_listing" not in p for p in w), w
    else:
        held = [p for p in w if not shown(p)]
        assert len(held) == 1 and isinstance(held[0].get("offsize_listing"), dict), w


def test_b14_exact_gate_off(monkeypatch):
    """B14 RED (exact gate OFF cell): the restore copies never leak a _p2_ key."""
    has_cap_kwarg()
    setflags(monkeypatch, flag="true", fix="true")
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "false")
    body, _, _ = run("rest", TED_DIOR, cap=True)
    assert p2_keys(body, []) == [] and ov(body)[1]["amount"] == 58.11


@pytest.mark.parametrize("cap", CAPCELLS)
def test_b15_consumers_recorded(monkeypatch, cap):
    """B15 RED: the verdict call sees Dior projected (amount None, size_mismatch) and the
    scoring call's product list equals flag OFF's, in both capability cells."""
    has_cap_kwarg()
    setflags(monkeypatch, flag=None, fix="true")
    _, off, _ = run("rest", TED_DIOR)
    setflags(monkeypatch, flag="true", fix="true")
    body, on, _ = run("rest", TED_DIOR, cap=cap)
    assert pending(on.gen[0][1]["price"], "size_mismatch")
    strip = lambda pdl: [{k: v for k, v in d.items() if not str(k).startswith("_p2")} for d in pdl]
    assert json.dumps(strip(on.scores[0]), sort_keys=True, default=str) == json.dumps(strip(off.scores[0]), sort_keys=True, default=str)
    assert "offsize_listing" in ov(body)[1] or shown(ov(body)[1])


@pytest.mark.parametrize("flag", [None, "true"])
@pytest.mark.parametrize("kind", ["rest", "stream"])
def test_b16_price_outcome_both_routes(monkeypatch, caplog, kind, flag):
    """B16 RED: two PRICE_OUTCOME lines per build, sync and stream, both flag values;
    flag ON + cap1 says reconcile=both_shown size_ml=100 cap=price_size for Dior."""
    if flag:
        has_cap_kwarg()
    setflags(monkeypatch, flag=flag, fix="true")
    caplog.set_level(logging.INFO)
    run(kind, TED_DIOR, cap=bool(flag))
    lines = [r.getMessage() for r in caplog.records if r.getMessage().startswith("PRICE_OUTCOME")]
    assert len(lines) == 2, lines
    if flag:
        assert "reconcile=both_shown" in lines[1] and "size_ml=100" in lines[1] and "cap=price_size" in lines[1]


B17_BASE = {
    "sauv_bleu|0|rest": "auTdV/NVLIABrAijys4QEhwrdBTiVFAWUWTGGEJPqLA=",
    "sauv_bleu|0|stream": "pH0BXhDERPPwhqpMWiEwUtyW6BcuTTuc1isX4OrV+aA=",
    "sauv_bleu|true|rest": "1N2Lo524EmFR8AHrWdhRactn1zxvmGvI/X1SwzbhFiw=",
    "sauv_bleu|true|stream": "EqPrDpz68jyh5M5o/Mun0kPG6mN80QCWGdqT132R4hk=",
    "ted_dior|0|rest": "fS4xNO1ll5bI8mQb9djvf1skWjQESAVpy4zTlOzUDj8=",
    "ted_dior|0|stream": "78nwJMcGX7HXEBxWzvWi2MdYkCe84mcz8j0iSSPkZ+8=",
    "ted_dior|true|rest": "fS4xNO1ll5bI8mQb9djvf1skWjQESAVpy4zTlOzUDj8=",
    "ted_dior|true|stream": "78nwJMcGX7HXEBxWzvWi2MdYkCe84mcz8j0iSSPkZ+8=",
    "ysl_lveb|0|rest": "EOpTTMx1njLnb5c9grbqq7X99NzromackcSipw4jKb0=",
    "ysl_lveb|0|stream": "wI6Fp0YG1qn5qSlrVBYCQQ6mkZqXj4YrPYHDBObLqJA=",
    "ysl_lveb|true|rest": "EOpTTMx1njLnb5c9grbqq7X99NzromackcSipw4jKb0=",
    "ysl_lveb|true|stream": "wI6Fp0YG1qn5qSlrVBYCQQ6mkZqXj4YrPYHDBObLqJA=",
}  # base64 sha256 of the normalized payload per cell, recorded at the base (RED report)


@pytest.mark.parametrize("cap", [False, True], ids=["cap0", "cap1"])
@pytest.mark.parametrize("kind", ["rest", "stream"])
@pytest.mark.parametrize("fix", FIXCELLS)
@pytest.mark.parametrize("pair", ["ted_dior", "ysl_lveb", "sauv_bleu"])
def test_b17_flag_off_body_identity(monkeypatch, caplog, pair, fix, kind, cap):
    """B17 PIN (full configuration + recorders): flag OFF (the token present or absent:
    compare_from_text is called with the token only when it accepts it): the payload
    digest equals the base record; no cache write; the only PRICE_* records are the three
    P2-11 kinds."""
    setflags(monkeypatch, flag=None, fix=fix)
    caplog.set_level(logging.INFO)
    pr = {"ted_dior": TED_DIOR, "ysl_lveb": YSL_LVEB, "sauv_bleu": SAUV_BLEU}[pair]
    accepts = "price_size_cap" in inspect.signature(scs.StructuredComparisonService.compare_from_text).parameters
    payload, rec, _ = run(kind, pr, cap=cap and accepts)
    assert rec.sets == [] and rec.db == []
    for r in caplog.records:
        m = r.getMessage()
        if m.startswith("PRICE_"):
            assert m.split(" ", 1)[0] in ("PRICE_OUTCOME", "PRICE_CACHE_HIT", "PRICE_CACHE_SKIP"), m
    key = "%s|%s|%s" % (pair, fix or "0", kind)
    assert key in B17_BASE, "base record missing for %s" % key
    assert digest(payload) == B17_BASE[key], key


def test_b18_wire_failure_ships_flag_off_body(monkeypatch, caplog):
    """B18 RED: p2_wire_price raising -> 200-equivalent body equal to the projected
    (flag-OFF shaped) wire and ONE WARNING by type."""
    has_cap_kwarg()
    setflags(monkeypatch, flag="true", fix="true")
    caplog.set_level(logging.WARNING)

    def _raise(*_a, **_k):
        raise RuntimeError("wire down")
    monkeypatch.setattr(ps, "p2_wire_price", _raise, raising=False)
    body, _, _ = run("rest", TED_DIOR, cap=True)
    assert pending(ov(body)[1], "size_mismatch") and "offsize_listing" not in ov(body)[1]
    warns = [r for r in caplog.records if r.levelno == logging.WARNING and "RuntimeError" in r.getMessage()
             and "p2" in r.getMessage().lower()]
    assert len(warns) == 1, [r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING]


def test_b24_race_miss_notes_timed_out(monkeypatch):
    """B24 RED (P2R-11): a race miss records timed_out for the product in the ledger the
    request bound (and a parked price is noted as parked)."""
    bind, summ = need("price_trace_bind"), need("price_miss_summary")
    import contextvars

    def _go():
        bind()
        svc = scs.StructuredComparisonService()
        got = svc._price_fallback_on_miss("price", "Dior Sauvage EDP", FRAG)
        return got, summ("Dior Sauvage EDP")
    got, s = contextvars.copy_context().run(_go)
    assert got is None and s["miss"] == "timed_out", s


def test_b16t_timed_out_and_parked_origin(monkeypatch, caplog):
    """B16t RED (ported from agent A's b16t; P2R-11 race / origin): flag OFF (the ledger and
    the line are unflagged), a race miss with nothing parked records timed_out; a race miss
    that serves a parked price makes that side's PRICE_OUTCOME say origin=parked_on_timeout
    with miss=timed_out, and the side with no price says miss=timed_out shown=no."""
    bind, summ = need("price_trace_bind"), need("price_miss_summary")
    setflags(monkeypatch, flag=None, fix="true")
    caplog.set_level(logging.INFO)
    import contextvars
    from tests import test_inc_p2_price_not_lost as pure

    def _go():
        bind()
        svc = scs.StructuredComparisonService()
        full = "Dior Sauvage EDP"
        assert svc._price_fallback_on_miss("price", full, FRAG) is None
        first = summ(full)
        svc._parked_price["Bleu de Chanel EDP"] = dict(BLEU_100)
        got = svc._price_fallback_on_miss("price", "Bleu de Chanel EDP", FRAG)
        a = pure.prod(full, ps.make_pending_price("BHD", "pending_genuine"))
        b = pure.prod("Bleu de Chanel EDP", BLEU_100)
        b["price"] = got  # the very object the race served (its identity carries the parked note)
        pure.build([a, b], "Dior Sauvage EDP vs Bleu de Chanel EDP")
        return first, got
    first, got = contextvars.copy_context().run(_go)
    assert first["miss"] == "timed_out", first
    assert got and got["amount"] == 91.78
    f = [dict(m.groups() for m in re.finditer(r"(\w+)=(\S*)", r.getMessage()))
         for r in caplog.records if r.getMessage().startswith("PRICE_OUTCOME")]
    assert len(f) == 2, f
    assert f[0]["miss"] == "timed_out" and f[0]["shown"] == "no", f[0]
    assert f[1]["origin"] == "parked_on_timeout" and f[1]["miss"] == "timed_out", f[1]


def test_s03_flag_off_promotion_carries_no_seen_at_pin(monkeypatch):
    """S03 PIN (ported from agent A's s03, its L2-promotion half; the persist half is B22's
    flag-OFF cell): flag OFF an L2 -> L1 promotion writes the row without any _seen_at key
    (the remaining-TTL flag on, the row age known)."""
    setflags(monkeypatch, flag=None)
    monkeypatch.setenv("ENABLE_L2_PROMOTION_REMAINING_TTL", "true")
    from app.services import product_data_service as pds
    sets = []

    async def _l2(key, region):
        return dict(BLEU_100, _l2_age_seconds=3600)
    p = fy._Patcher()
    try:
        p.setattr(scs, "get_cached", lambda k: None)
        p.setattr(scs, "set_cached", lambda k, v, t: sets.append(copy.deepcopy(v)) or True)
        p.setattr(pds, "get_cached_price", _l2)
        svc = scs.StructuredComparisonService()
        got = asyncio.run(svc._get_price("", "Bleu de Chanel EDP", None, "bahrain", "Bleu de Chanel EDP",
                                         nocache=False, category=FRAG))
    finally:
        p.undo()
    assert got and got["amount"] == 91.78
    assert sets, "no promotion"
    assert all("_seen_at" not in v for v in sets), sets


@pytest.fixture(autouse=True)
def _p2_reset_spend_breaker_after_each_test():
    """Test hygiene (P2R-39): this file walks ENABLE_LLM_SPEND_BREAKER on, so the breaker's
    process state ("ran", the fail-open counter), like the router's latch, would leak the llm_spend keys into a later
    file's /health body in CI's one alphabetical process. Reset it after every test; the
    rows themselves are unchanged."""
    yield
    from app.services import llm_router as _lr
    from app.services import llm_spend_breaker as _lsb
    _lsb._reset_spend_breaker_state()
    _lr._reset_router_state()  # the anthropic_breaker latch (the link lane's #417 leak)
