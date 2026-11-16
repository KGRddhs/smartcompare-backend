"""INC-P2 PRICE-NOT-LOST (S96-FIX incident lane) RED rows: the pure PS / RB rows.

Spec: .qa-s80/INC-P2_UNIT_SPEC.md section 5.1, as amended by RULINGS_INC_P2.md (P2R-1..P2R-28,
binding; section G = the relay's ruling ORCH-P2-A: the both-shown display of a different-size
side is gated on the request token `price_size` in X-Client-Capabilities; without it the side
stays pending (size_mismatch, as flag OFF) and its listing travels in `price.offsize_listing`;
section H = ORCH-P2-B, which supersedes G where they differ: RULE 1 a side with a TYPED size
whose listing is at that typed size is shown in every capability cell, and a typed side's
off-size listing stays pending in every cell; RULE 2 the token gate applies ONLY to a side with
NO typed size whose listing size differs from the other side's; RULE 3 a mixed pair applies
rule 1 to the typed side and rule 2 to the untyped side; RULE 4 no side flag OFF shows loses
its price because the token is absent) and the brief's ADDENDA 1-2 (P2-17..P2-23). This file
is the single RED amendment of P2R-27 (agent B's frozen set, amended; agent A's unique rows
ported onto B's prototype seams).

Flag ENABLE_PRICE_NOT_LOST (default OFF, read per call). Every pair row names its
ENABLE_FRAGRANCE_SIZE_RECONCILE_FIX cell ("fix0" / "fix1") and its ENABLE_PRODUCT_RESOLVER
cell ("res0" / "res1": the Step-1 shapes of spec 1.2); every both-shown row runs in the two
capability cells ("cap1" token present / "cap0" token absent, P2R-21).

RED rows fail at the base on an AssertionError only (a missing symbol is read with getattr
and asserted); PIN rows are green at the base and run with the FULL production
configuration (H12 c + H13 c) set explicitly in every row.

Hermetic: pure functions and build_comparison_response over synthetic dicts; hosts are
*.example.com except the public marketplace names under test; public perfume names and the
logged prices of P2-14 only. Pure ASCII, LF.
"""
from __future__ import annotations

import asyncio
import base64
import contextvars
import copy
import hashlib
import json
import logging
import os
import re

import pytest

os.environ.setdefault("OPENAI_API_KEY", "sk" + "-test-dummy")

import app.main  # noqa: F401,E402  (FIRST: the dotenv guard)
from app.services import price_service as ps  # noqa: E402
from app.services import response_builder as rb  # noqa: E402

FLAG = "ENABLE_PRICE_NOT_LOST"
FIX = "ENABLE_FRAGRANCE_SIZE_RECONCILE_FIX"
RES = "ENABLE_PRODUCT_RESOLVER"
FRAG = "fragrances"
PROD_ON = (
    "ENABLE_LLM_LEDGER_V2", "ENABLE_LLM_SPEND_BREAKER", "ENABLE_REQUEST_CONTEXT_HEADERS",
    "ENABLE_OPENAI_EGRESS_STOP", "ENABLE_OPENAI_PRE_V3", "ENABLE_ANTHROPIC_TEXT",
    "ENABLE_ANTHROPIC_VERDICT", "ENABLE_LEGACY_FINGERPRINT_READER", "ENABLE_CONSENT_PERSIST",
    "ENABLE_COMPARE_AUTH_REQUIRED", "ENABLE_OFFLOOP_DNS_RESOLVE", "ENABLE_PRICE_PARSE_OFFLOAD",
    "ENABLE_EXACT_PRICE_GATE",
)
PROD_OFF = (
    "ENABLE_ANTHROPIC_MODERATION", "ENABLE_ANTHROPIC_VISION", "ENABLE_KB_INGEST",
    "ENABLE_KB_FIRST_SERVE", "ENABLE_FIELD_STATUS_METADATA", "ENABLE_RESULT_STATUS_METADATA",
    "ENABLE_FRAGRANCE_ONLY_GATE", "ENABLE_DATA_GUARDS_V2", "ENABLE_ASYNC_REDIS_OFFLOAD",
    "ENABLE_COMPARE_RUN_LEDGER", "ENABLE_GENUINE_PRICE_PRIORITY", "ENABLE_LISTING_MATCH_GUARD",
    "ENABLE_REGION_CURRENCY_GUARD", "ENABLE_PRESCORING_SHOWABLE_GUARD", "WARMER_CONTEXT",
    "ENABLE_CONFIDENCE_SINGLE_COMPUTATION", "ENABLE_L2_PROMOTION_REMAINING_TTL",
)
OFFSIZE_KEYS = ["amount", "currency", "size_ml", "per_ml", "retailer", "url", "title",
                "source_method"]
OUTCOME_FIELDS = ("slot", "product", "shown", "amount", "currency", "size_ml", "method",
                  "retailer", "marketplace", "origin", "race", "reconcile", "pend_reason",
                  "display_rule", "miss", "miss_host", "miss_status", "miss_rule", "fam",
                  "rejected", "cache_write", "cap")


# --------------------------------------------------------------------------- helpers
def need(name, mod=ps):
    """A symbol of this unit: asserted (never an AttributeError at the base)."""
    obj = getattr(mod, name, None)
    assert obj is not None, "%s.%s is missing" % (mod.__name__, name)
    return obj


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    for name in PROD_ON:
        monkeypatch.setenv(name, "true")
    for name in PROD_OFF:
        monkeypatch.delenv(name, raising=False)
    for name in (FLAG, FIX, RES):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "syn" + "thetic-" + "p2")
    yield


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


def cand(price, rank=0):
    return {"value": price["amount"], "raw_data": dict(price), "source_method": price["source_method"],
            "retailer": price["retailer"], "title": price["title"],
            "size": (sorted(ps.extract_sizes_ml(price["title"]))[0] + "ml")
            if ps.extract_sizes_ml(price["title"]) else None,
            "in_stock": price.get("in_stock", True), "variant_rank": rank}


RESOLVED = {
    "Ted Baker M 30ml": ("Ted Baker", "M", "30ml"),
    "Dior Sauvage 100 ML Edp": ("Dior", "Sauvage", "EDP 100ml"),
}


def prod(typed, price, res=False, category=FRAG):
    """The product dict the orchestrator hands the reconcile (spec 1.2): resolver OFF:
    brand '', name = full_name = the typed half; ON: the apply_resolution shape through
    _product_display_identity."""
    if res and typed in RESOLVED:
        brand, line, variant = RESOLVED[typed]
        import app.services.structured_comparison_service as scs
        full, display = scs._product_display_identity(brand, line, variant, line, False)
        d = {"brand": brand, "name": display, "full_name": full, "variant": variant}
    else:
        d = {"brand": "", "name": typed, "full_name": typed, "variant": None}
    d.update({"category": category, "price": copy.deepcopy(price),
              "best_price": price.get("amount") if isinstance(price, dict) else None,
              "retailer": price.get("retailer") if isinstance(price, dict) else None,
              "specs": {}, "reviews": None, "rating": 4.2, "rating_source": None,
              "review_count": 5, "fact_check": {}})
    return d


def scoring():
    return {"winner_index": 0,
            "scores": {"product_0": {"overall": 60.0}, "product_1": {"overall": 50.0}},
            "tradeoff_pairs": [], "value_badges": [], "comparison_quality": "normal",
            "personalization": {"applied_shifts": []}, "price_tiers": {},
            "comparison_pair": ["product_a", "product_b"], "verdict_text": "Test.",
            "key_differences": []}


def in_ctx(fn, cap=False, strict=True):
    """Run fn in a copied context (no ContextVar leaks across rows); bind the capability
    token there (cap=True asserts the binder exists on a RED row; strict=False = a PIN row:
    bind only when it exists, so the row is green at the base)."""
    def _body():
        binder = getattr(ps, "price_size_cap_bind", None)
        if cap:
            assert binder is not None or not strict, "price_service.price_size_cap_bind is missing"
            if binder is not None:
                binder(True)
        return fn()
    return contextvars.copy_context().run(_body)


def build(pd, query="A vs B", category=FRAG):
    return rb.build_comparison_response(
        query=query, product_data=pd, scoring_result=scoring(), comparison=None,
        region="bahrain", api_calls=0, elapsed_seconds=0.0, total_cost=0.0, gpt_calls=0,
        serper_calls=0, from_cache=False, verdict_validation={}, category_used=category)


def run_pair(a, b, query=None, cands=None, cap=False, category=FRAG, strict=True):
    """reconcile_pair_fairness then build_comparison_response, in one copied context.
    Returns (body, product_data_after_reconcile_snapshot)."""
    q = query or "%s vs %s" % (a["name"], b["name"])
    pd = [a, b]

    def _go():
        ps.reconcile_pair_fairness(pd, q, category, candidates_by_name=cands or {})
        snap = copy.deepcopy(pd)
        return build(pd, q, category), snap
    return in_ctx(_go, cap, strict)


def ov(body):
    return [p.get("price") for p in body["overview"]["products"]]


def legacy(body):
    return [p.get("price") for p in body["products"]]


def dims(body):
    return {d["key"]: d for d in body["scoring_v2"]["dimensions"]}


def shown(price):
    return isinstance(price, dict) and price.get("unavailable") is not True and isinstance(
        price.get("amount"), (int, float))


def pending(price, reason=None):
    ok = isinstance(price, dict) and price.get("unavailable") is True and price.get("amount") is None
    return ok and (reason is None or price.get("reason") == reason)


def underscore_or_p2(obj, out):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if str(k).startswith("_p2"):
                out.append(k)
            underscore_or_p2(v, out)
    elif isinstance(obj, list):
        for v in obj:
            underscore_or_p2(v, out)
    return out


# Fixtures (P2-14): public names, the logged prices, synthetic hosts.
TED_P = P(9.5, "Ted Baker M Eau De Toilette 30ml", "store-a", "p/ted-m-30")
DIOR_P = P(58.11, "Dior Sauvage EDP 100ml", "store-b", "p/sauvage-100")
DIOR_50 = P(40.0, "Dior Sauvage EDP 50ml", "store-b", "p/sauvage-50")
DIOR_30 = P(30.0, "Dior Sauvage EDP 30ml", "store-b", "p/sauvage-30")
YSL_P = P(39.0, "YSL Libre Eau de Parfum 90ml", "store-a", "p/libre-90")
LVEB_P = P(34.0, "Lancome La Vie Est Belle Eau de Parfum 100ml", "store-a", "p/lveb-100")
BR_P = P(129.28, "Maison Francis Kurkdjian Baccarat Rouge 540 EDP 70ml", "store-b", "p/br540-70")
BLEU_150 = P(70.0, "Bleu de Chanel EDP 150ml", "store-a", "p/bleu-150")
BLEU_100 = P(91.78, "Bleu de Chanel EDP 100ml", "store-b", "p/bleu-100")
SAUV_100 = P(58.11, "Sauvage EDP 100ml", "store-b", "p/sv-100")
TED_Q = "Ted Baker M 30ml vs Dior Sauvage 100 ML Edp"

FIXCELLS = [pytest.param(None, id="fix0"), pytest.param("true", id="fix1")]
RESCELLS = [pytest.param(False, id="res0"), pytest.param(True, id="res1")]
CAPCELLS = [pytest.param(True, id="cap1"), pytest.param(False, id="cap0")]


def flag_off_pend(a, b, query, cands=None):
    """Flag OFF's own wire price per side for the same inputs (computed, not assumed)."""
    os.environ.pop(FLAG, None)
    body, _ = run_pair(copy.deepcopy(a), copy.deepcopy(b), query, cands)
    return ov(body)


def assert_offsize(price, src, size_ml):
    off = price.get("offsize_listing")
    assert isinstance(off, dict), ("offsize_listing missing", price)
    assert sorted(off) == sorted(OFFSIZE_KEYS), sorted(off)
    assert off["amount"] == src["amount"] and off["currency"] == src["currency"]
    assert off["size_ml"] == size_ml
    if size_ml:
        assert off["per_ml"] == round(float(src["amount"]) / size_ml, 4)
    else:
        assert off["per_ml"] is None
    assert off["retailer"] == src["retailer"] and off["url"] == src["url"]
    assert off["title"] == src["title"][:120] and off["source_method"] == src["source_method"]


def check_both_shown_cells(mp, cap, body, flag_off_wire, held_idx, shown_src, sizes):
    """P2R-18 / P2R-19: cap1 -> the held side carries its found amount with size_ml /
    per_ml and no offsize_listing; cap0 -> the held side equals flag OFF's pending dict
    plus offsize_listing."""
    wire = ov(body)
    for i in range(2):
        if i in held_idx:
            src = shown_src[i]
            if cap:
                assert shown(wire[i]) and wire[i]["amount"] == src["amount"], wire[i]
                assert wire[i].get("size_ml") == sizes[i], wire[i]
                if sizes[i]:
                    assert wire[i].get("per_ml") == round(float(src["amount"]) / sizes[i], 4)
                assert "offsize_listing" not in wire[i]
                assert legacy(body)[i]["amount"] == src["amount"]
            else:
                rest = {k: v for k, v in wire[i].items() if k != "offsize_listing"}
                assert rest == flag_off_wire[i], (rest, flag_off_wire[i])
                assert_offsize(wire[i], src, sizes[i])
                assert legacy(body)[i].get("offsize_listing") == wire[i]["offsize_listing"]
    assert underscore_or_p2(body, []) == []


def assert_open(body, i, src, size_ml):
    """ORCH-P2-B rule 1 / rule 4: side i is shown with its found amount in EVERY capability
    cell (size_ml / per_ml when the listing carries one strict size), never with an
    offsize_listing, and the legacy alias carries the same amount."""
    w = ov(body)[i]
    assert shown(w) and w["amount"] == src["amount"], w
    if size_ml:
        assert w.get("size_ml") == size_ml, w
        assert w.get("per_ml") == round(float(src["amount"]) / size_ml, 4), w
    else:
        assert "size_ml" not in w and "per_ml" not in w, w
    assert "offsize_listing" not in w, w
    assert legacy(body)[i].get("amount") == src["amount"], legacy(body)[i]
    assert underscore_or_p2(body, []) == []


def shown_idx(wire):
    return {i for i, p in enumerate(wire) if shown(p)}


# --------------------------------------------------------------------------- A01-A03
@pytest.mark.parametrize("val,exp", [(None, False), ("false", False), ("0", False),
                                     ("maybe", False), ("TRUE", True), (" on ", True),
                                     ("1", True), ("yes", True)])
def test_a01_flag_reader(monkeypatch, val, exp):
    """A01 RED: the house idiom, read per call."""
    fn = need("price_not_lost_enabled")
    setflags(monkeypatch, flag=val)
    assert fn() is exp
    monkeypatch.setenv(FLAG, "false" if exp else "true")
    assert fn() is (not exp)


@pytest.mark.parametrize("res", RESCELLS)
def test_a02_typed_size_both_modes(res):
    """A02 RED: each side's OWN typed size, equal with the resolver ON and OFF (Q1)."""
    fn = need("typed_size_ml")
    assert fn(prod("Ted Baker M 30ml", TED_P, res)) == 30
    assert fn(prod("Dior Sauvage 100 ML Edp", DIOR_P, res)) == 100
    assert fn({"name": "Sauvage 3.4 oz", "full_name": "Sauvage 3.4 oz"}) == 100
    assert fn({"name": "Sauvage", "full_name": "Sauvage", "price": {"title": "x 90ml"}}) is None
    assert fn(None) is None


def test_a03_listing_size_strict():
    """A03 RED: X1-R7's strict parser, exactly one distinct token."""
    fn = need("listing_size_ml")
    assert fn({"title": "Libre EDP 90ml"}) == 90
    assert fn({"title": "50ml / 100ml"}) is None
    assert fn({"title": "7.5ml"}) is None
    assert fn({"title": "EDP100ml"}) == 100
    assert fn({"size": "100ml"}) == 100
    assert fn({"title": "100ml 100 ml"}) == 100
    assert fn({"title": "Sauvage 3.4 oz"}) is None
    assert fn(None) is None


# --------------------------------------------------------------------------- A04-A05 (T3-01)
@pytest.mark.parametrize("cap", CAPCELLS)
@pytest.mark.parametrize("res", RESCELLS)
@pytest.mark.parametrize("fix", FIXCELLS)
def test_a04_a05_ted_dior_own_typed_sizes(monkeypatch, fix, res, cap):
    """A04 (res0) / A05 (res1) RED, REWRITTEN by ORCH-P2-B rule 1 (P2R-23, the T3-01 pair):
    two typed sizes, each listing at its own typed size: BOTH amounts are shown in BOTH
    capability cells (the token changes nothing), each with its typed size_ml / per_ml and
    no offsize_listing; flag OFF pends Dior (the incident)."""
    setflags(monkeypatch, fix=fix, res="true" if res else None)
    t, d = prod("Ted Baker M 30ml", TED_P, res), prod("Dior Sauvage 100 ML Edp", DIOR_P, res)
    off = flag_off_pend(t, d, TED_Q)
    assert shown(off[0]) and pending(off[1], "size_mismatch"), off
    monkeypatch.setenv(FLAG, "true")
    body, _ = run_pair(t, d, TED_Q, cap=cap)
    assert_open(body, 0, TED_P, 30)
    assert_open(body, 1, DIOR_P, 100)
    assert body["metadata"].get("pair_price_sizes") == {"mode": "different_sizes",
                                                         "sizes_ml": [30, 100]}


@pytest.mark.parametrize("fix", FIXCELLS)
def test_a06_own_typed_size_reselection(monkeypatch, fix):
    """A06 RED: Dior's found price is a 50 ml listing; a genuine 100 ml candidate exists:
    the shown (stashed) Dior price is the 100 ml candidate and the side is marked."""
    setflags(monkeypatch, flag="true", fix=fix)
    t, d = prod("Ted Baker M 30ml", TED_P), prod("Dior Sauvage 100 ML Edp", DIOR_50)
    c100 = P(61.0, "Dior Sauvage EDP 100ml", "store-c", "p/sv-100", sm="shopify_json")
    _, snap = run_pair(t, d, TED_Q, {"Dior Sauvage 100 ML Edp": [cand(c100)]})
    held = snap[1].get("_p2_shown_price") or snap[1]["price"]
    assert held.get("amount") == 61.0, snap[1]
    assert snap[1].get("_p2_reselected") is True


@pytest.mark.parametrize("cap", CAPCELLS)
@pytest.mark.parametrize("fix", FIXCELLS)
def test_a07_one_side_typed(monkeypatch, fix, cap):
    """A07 RED: Dior typed 100 vs an untyped Bleu at 150 ml with a 100 ml candidate: Bleu
    is re-selected to 100; same_size; no projection (the price dim is not limited)."""
    setflags(monkeypatch, flag="true", fix=fix)
    d, b = prod("Dior Sauvage 100 ML Edp", DIOR_P), prod("Bleu de Chanel EDP", BLEU_150)
    body, snap = run_pair(d, b, None, {"Bleu de Chanel EDP": [cand(BLEU_100)]}, cap=cap)
    wire = ov(body)
    assert wire[1]["amount"] == 91.78 and wire[1].get("size_ml") == 100, wire[1]
    assert snap[1].get("_p2_reselected") is True
    assert body["metadata"].get("pair_price_sizes") == {"mode": "same_size", "sizes_ml": [100, 100]}
    assert dims(body)["price"].get("caption_key") != "limited_data"


@pytest.mark.parametrize("gate", [None, "false"], ids=["gate_prod", "gate_off"])
@pytest.mark.parametrize("cap", CAPCELLS)
@pytest.mark.parametrize("fix", FIXCELLS)
def test_a08_typed_off_size_listing_stays_pending(monkeypatch, fix, cap, gate):
    """A08 PIN (rewritten, P2R-3; gate cells added by the amendment, P2R-23 second
    sentence): a typed 100 side whose only listing is 50 ml stays pending in both capability
    cells; never a 50 ml amount on the wire, never an offsize_listing. gate_prod = the C1
    not_exact chokepoint refuses it; gate_off (ENABLE_EXACT_PRICE_GATE false, a state the
    chokepoint does not cover) = the unit itself must keep it pending."""
    if gate:
        monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", gate)
    setflags(monkeypatch, flag="true", fix=fix)
    t, d = prod("Ted Baker M 30ml", TED_P), prod("Dior Sauvage 100 ML Edp", DIOR_50)
    body, _ = run_pair(t, d, TED_Q, cap=cap, strict=False)
    assert pending(ov(body)[1]) and pending(legacy(body)[1]), ov(body)[1]
    assert ov(body)[1].get("reason") in ("size_mismatch", "pending_genuine")
    assert "40.0" not in json.dumps(ov(body)[1]) and "offsize_listing" not in ov(body)[1]


@pytest.mark.parametrize("cap", CAPCELLS)
@pytest.mark.parametrize("fix", FIXCELLS)
def test_a09_ysl_lancome_different_sizes(monkeypatch, fix, cap):
    """A09 RED (T3-02): no typed size, no candidate: never pended for size by the flag."""
    setflags(monkeypatch, fix=fix)
    y, l = prod("YSL Libre EDP", YSL_P), prod("Lancome La Vie Est Belle EDP", LVEB_P)
    q = "YSL Libre EDP vs Lancome La Vie Est Belle EDP"
    off = flag_off_pend(y, l, q)
    held = {i for i in (0, 1) if pending(off[i], "size_mismatch")}
    assert held, off
    monkeypatch.setenv(FLAG, "true")
    body, _ = run_pair(y, l, q, cap=cap)
    check_both_shown_cells(monkeypatch, cap, body, off, held, {0: YSL_P, 1: LVEB_P}, {0: 90, 1: 100})
    assert body["metadata"].get("pair_price_sizes") == {"mode": "different_sizes", "sizes_ml": [90, 100]}


@pytest.mark.parametrize("cap", CAPCELLS)
@pytest.mark.parametrize("fix", FIXCELLS)
def test_a10_baccarat_70(monkeypatch, fix, cap):
    """A10 RED: Baccarat Rouge 540 at 70 ml vs a 100 ml partner."""
    setflags(monkeypatch, fix=fix)
    a, b = prod("Baccarat Rouge 540", BR_P), prod("Bleu de Chanel EDP", BLEU_100)
    q = "Baccarat Rouge 540 vs Bleu de Chanel EDP"
    off = flag_off_pend(a, b, q)
    held = {i for i in (0, 1) if pending(off[i], "size_mismatch")}
    assert 0 in held, off
    monkeypatch.setenv(FLAG, "true")
    body, _ = run_pair(a, b, q, cap=cap)
    check_both_shown_cells(monkeypatch, cap, body, off, held, {0: BR_P, 1: BLEU_100}, {0: 70, 1: 100})
    if cap:
        assert ov(body)[0]["per_ml"] == round(129.28 / 70, 4)


@pytest.mark.parametrize("fix", [pytest.param(None, id="fix0-RED"), pytest.param("true", id="fix1-PIN")])
def test_a11_common_100_kept(monkeypatch, fix):
    """A11: Sauvage EDP vs Bleu de Chanel EDP with the noon 100 ml candidate: Bleu is
    re-selected to 91.780, no pend. fix1 = today (PIN); fix0 base pends both (RED, P2R-8)."""
    setflags(monkeypatch, flag="true", fix=fix)
    s, b = prod("Sauvage EDP", SAUV_100), prod("Bleu de Chanel EDP", BLEU_150)
    body, _ = run_pair(s, b, None, {"Bleu de Chanel EDP": [cand(BLEU_100)]})
    w = ov(body)
    assert shown(w[0]) and w[0]["amount"] == 58.11, w
    assert shown(w[1]) and w[1]["amount"] == 91.78, w


@pytest.mark.parametrize("fix", FIXCELLS)
def test_a12_common_50(monkeypatch, fix):
    """A12 RED: both reach 50 only: both re-selected to 50."""
    setflags(monkeypatch, flag="true", fix=fix)
    s = prod("Sauvage EDP", P(70.0, "Sauvage EDP 75ml", "store-a", "p/sv-75"))
    b = prod("Bleu de Chanel EDP", P(95.0, "Bleu de Chanel EDP 125ml", "store-a", "p/bl-125"))
    c = {"Sauvage EDP": [cand(P(45.0, "Sauvage EDP 50ml", "store-b", "p/sv-50"))],
         "Bleu de Chanel EDP": [cand(P(55.0, "Bleu de Chanel EDP 50ml", "store-b", "p/bl-50"))]}
    body, _ = run_pair(s, b, None, c)
    assert [p.get("amount") for p in ov(body)] == [45.0, 55.0], ov(body)


@pytest.mark.parametrize("fix", [pytest.param(None, id="fix0-RED"), pytest.param("true", id="fix1")])
def test_a13_100_preferred(monkeypatch, fix):
    """A13: both reach 100 and 125: target 100."""
    setflags(monkeypatch, flag="true", fix=fix)
    s = prod("Sauvage EDP", P(70.0, "Sauvage EDP 75ml", "store-a", "p/sv-75"))
    b = prod("Bleu de Chanel EDP", BLEU_150)
    c = {"Sauvage EDP": [cand(P(80.0, "Sauvage EDP 100ml", "store-b", "p/sv-100")),
                         cand(P(99.0, "Sauvage EDP 125ml", "store-b", "p/sv-125"))],
         "Bleu de Chanel EDP": [cand(BLEU_100), cand(P(110.0, "Bleu de Chanel EDP 125ml", "store-b", "p/bl-125"))]}
    body, _ = run_pair(s, b, None, c)
    assert [p.get("amount") for p in ov(body)] == [80.0, 91.78], ov(body)


@pytest.mark.parametrize("flag", [None, "true"])
@pytest.mark.parametrize("fix", FIXCELLS)
def test_a14_unknown_keeps_flagship_default(monkeypatch, fix, flag):
    """A14 PIN: one side without any size (a designer name), the other 100 ml: no swap,
    no projection, both amounts shown, never size_mismatch (both flag values)."""
    setflags(monkeypatch, flag=flag, fix=fix)
    d = prod("Dior Sauvage EDP", P(58.11, "Dior Sauvage EDP 100ml", "store-b", "p/s"))
    b = prod("Bleu de Chanel EDP", P(80.0, "Bleu de Chanel Eau de Parfum", "store-a", "p/b"))
    body, _ = run_pair(d, b)
    w = ov(body)
    assert shown(w[0]) and shown(w[1]), w
    assert "size_mismatch" not in json.dumps(w)


@pytest.mark.parametrize("cap", CAPCELLS)
def test_a15_legacy_branch_both_shown(monkeypatch, cap):
    """A15 RED (fix0): two non-designer houses at 50 / 100: flag OFF pends both (today);
    flag ON holds or shows both by the capability."""
    setflags(monkeypatch, fix=None)
    a = prod("Ted Baker M", P(12.0, "Ted Baker M EDT 50ml", "store-a", "p/t50"))
    b = prod("Zara Red Vanilla", P(9.0, "Zara Red Vanilla EDT 100ml", "store-a", "p/z100"))
    q = "Ted Baker M vs Zara Red Vanilla"
    src = {0: copy.deepcopy(a["price"]), 1: copy.deepcopy(b["price"])}
    off = flag_off_pend(a, b, q)
    assert pending(off[0], "size_mismatch") and pending(off[1], "size_mismatch"), off
    monkeypatch.setenv(FLAG, "true")
    body, _ = run_pair(a, b, q, cap=cap)
    check_both_shown_cells(monkeypatch, cap, body, off, {0, 1}, src, {0: 50, 1: 100})


@pytest.mark.parametrize("flag", [None, "true"])
@pytest.mark.parametrize("fix", FIXCELLS)
def test_a16_other_pends_unchanged(monkeypatch, fix, flag):
    """A16 PIN: an estimate side is a no-op; a pending_genuine side is untouched; an
    out-of-stock candidate is never re-selected (both flag values, full config)."""
    setflags(monkeypatch, flag=flag, fix=fix)
    est = prod("Dior Sauvage EDP", P(50.0, "Dior Sauvage EDP 100ml", sm="estimated", estimated=True))
    other = prod("Bleu de Chanel EDP", BLEU_150)
    pd = [est, other]
    before = copy.deepcopy(pd)
    assert in_ctx(lambda: ps.reconcile_pair_fairness(pd, None, FRAG, candidates_by_name={})) is False
    assert pd == before
    pg = ps.make_pending_price("BHD", "pending_genuine")
    pd2 = [prod("Dior Sauvage EDP", P(58.11, "Dior Sauvage EDP 100ml")), prod("Bleu de Chanel EDP", BLEU_150)]
    pd2[1]["price"] = dict(pg)
    in_ctx(lambda: ps.reconcile_pair_fairness(pd2, None, FRAG, candidates_by_name={}))
    assert pd2[1]["price"] == pg
    oos = cand(P(91.78, "Bleu de Chanel EDP 100ml", in_stock=False))
    pd3 = [prod("Dior Sauvage EDP", P(58.11, "Dior Sauvage EDP 100ml")), prod("Bleu de Chanel EDP", BLEU_150)]
    in_ctx(lambda: ps.reconcile_pair_fairness(pd3, None, FRAG, candidates_by_name={"Bleu de Chanel EDP": [oos]}))
    assert pd3[1].get("price", {}).get("amount") != 91.78
    assert (pd3[1].get("_p2_shown_price") or {}).get("amount") != 91.78


@pytest.mark.parametrize("fix", FIXCELLS)
def test_a17_projection_equals_flag_off_inputs(monkeypatch, fix):
    """A17 RED: after the reconcile every index flag OFF pends carries flag OFF's own
    pending dict (equal and byte-equal); the found price rides _p2_shown_price."""
    setflags(monkeypatch, fix=fix)
    pd_off = [prod("Ted Baker M 30ml", TED_P), prod("Dior Sauvage 100 ML Edp", DIOR_P)]
    in_ctx(lambda: ps.reconcile_pair_fairness(pd_off, TED_Q, FRAG, candidates_by_name={}))
    monkeypatch.setenv(FLAG, "true")
    pd_on = [prod("Ted Baker M 30ml", TED_P), prod("Dior Sauvage 100 ML Edp", DIOR_P)]
    in_ctx(lambda: ps.reconcile_pair_fairness(pd_on, TED_Q, FRAG, candidates_by_name={}))
    assert pd_on[1]["price"] == pd_off[1]["price"]
    assert json.dumps(pd_on[1]["price"]) == json.dumps(pd_off[1]["price"])
    assert (pd_on[1].get("_p2_shown_price") or {}).get("amount") == 58.11, pd_on[1]
    assert pd_on[0]["price"] == pd_off[0]["price"]


@pytest.mark.parametrize("cap", CAPCELLS)
@pytest.mark.parametrize("fix", FIXCELLS)
def test_a18_consumers_see_no_comparison(monkeypatch, fix, cap):
    """A18 RED: the price and value dims stay limited_data in both capability cells while
    cap1 shows both amounts (P2-4 unchanged, P2R-20)."""
    setflags(monkeypatch, flag="true", fix=fix)
    body, _ = run_pair(prod("Ted Baker M 30ml", TED_P), prod("Dior Sauvage 100 ML Edp", DIOR_P), TED_Q, cap=cap)
    dm = dims(body)
    assert dm["price"].get("caption_key") == "limited_data" and dm["value"].get("caption_key") == "limited_data"
    assert "less" not in (dm["price"].get("delta_text") or "").lower()
    assert "offsize_listing" in ov(body)[1] or shown(ov(body)[1])
    if cap:
        assert all(shown(p) for p in ov(body)), ov(body)


@pytest.mark.parametrize("cap", CAPCELLS)
@pytest.mark.parametrize("fix", FIXCELLS)
def test_a19_both_projected_when_today_pends_nothing(monkeypatch, fix, cap):
    """A19 RED: typed 30 / 100 and Dior holds a 30 ml candidate (today re-selects Dior to
    30); the flag keeps Dior at its typed 100, so BOTH sides are projected (P2-4, unchanged).
    The wire is REWRITTEN by ORCH-P2-B rule 1 (P2R-23; it supersedes D2): both typed sides
    are at their own typed sizes, so both amounts are shown in BOTH capability cells."""
    setflags(monkeypatch, flag="true", fix=fix)
    c = {"Dior Sauvage 100 ML Edp": [cand(DIOR_30)]}
    pd = [prod("Ted Baker M 30ml", TED_P), prod("Dior Sauvage 100 ML Edp", DIOR_P)]
    _, snap = run_pair(pd[0], pd[1], TED_Q, c, cap=cap)
    for i in (0, 1):
        assert pending(snap[i]["price"], "size_mismatch"), snap[i]["price"]
        assert isinstance(snap[i].get("_p2_shown_price"), dict)
    pd = [prod("Ted Baker M 30ml", TED_P), prod("Dior Sauvage 100 ML Edp", DIOR_P)]
    body, _ = run_pair(pd[0], pd[1], TED_Q, c, cap=cap)
    assert_open(body, 0, TED_P, 30)
    assert_open(body, 1, DIOR_P, 100)


def test_a20_marker_modes(monkeypatch):
    """A20 RED: same_size, different_sizes, unknown, and null for a side with no token."""
    setflags(monkeypatch, flag="true", fix="true")
    b1, _ = run_pair(prod("Dior Sauvage EDP", P(58.11, "Dior Sauvage EDP 100ml")),
                     prod("Bleu de Chanel EDP", BLEU_100), cap=True)
    assert b1["metadata"].get("pair_price_sizes") == {"mode": "same_size", "sizes_ml": [100, 100]}
    b2, _ = run_pair(prod("Dior Sauvage EDP", P(58.11, "Dior Sauvage EDP 100ml")),
                     prod("Bleu de Chanel EDP", P(80.0, "Bleu de Chanel Eau de Parfum")), cap=True)
    assert b2["metadata"].get("pair_price_sizes") == {"mode": "unknown", "sizes_ml": [100, None]}
    b3, _ = run_pair(prod("YSL Libre EDP", YSL_P), prod("Lancome La Vie Est Belle EDP", LVEB_P), cap=False)
    assert b3["metadata"].get("pair_price_sizes") == {"mode": "different_sizes", "sizes_ml": [90, 100]}


def test_a21_size_and_per_ml_stamp(monkeypatch):
    """A21 RED: one strict token -> size_ml + per_ml (4 places); two tokens / oz only /
    electronics / a pending side -> neither key (and no marker for electronics)."""
    setflags(monkeypatch, flag="true", fix="true")
    b, _ = run_pair(prod("Dior Sauvage EDP", P(58.11, "Dior Sauvage EDP 100ml")),
                    prod("Bleu de Chanel EDP", BLEU_100), cap=True)
    assert ov(b)[0].get("size_ml") == 100 and ov(b)[0].get("per_ml") == 0.5811
    b, _ = run_pair(prod("YSL Libre EDP", YSL_P), prod("Lancome La Vie Est Belle EDP", LVEB_P), cap=True)
    assert ov(b)[0].get("per_ml") == 0.4333 and ov(b)[0].get("size_ml") == 90
    b, _ = run_pair(prod("Dior Sauvage EDP", P(58.11, "Dior Sauvage EDP 3.4 oz")),
                    prod("Bleu de Chanel EDP", P(80.0, "Bleu de Chanel EDP 50ml / 100ml")), cap=True)
    for p in ov(b):
        assert "size_ml" not in p and "per_ml" not in p, p
    e, _ = run_pair(prod("iPhone 15", P(300.0, "Apple iPhone 15 128GB"), category="electronics"),
                    prod("Galaxy S24", P(280.0, "Samsung Galaxy S24 128GB"), category="electronics"),
                    category="electronics", cap=True)
    for p in ov(e):
        assert "size_ml" not in p and "per_ml" not in p, p
    assert "pair_price_sizes" not in e["metadata"]
    est = prod("Dior Sauvage EDP", P(50.0, "Dior Sauvage EDP 100ml", sm="estimated", estimated=True))
    b, _ = run_pair(est, prod("Bleu de Chanel EDP", BLEU_100), cap=True)
    assert pending(ov(b)[0]) and "size_ml" not in ov(b)[0]
    assert ov(b)[1].get("size_ml") == 100


@pytest.mark.parametrize("cap", CAPCELLS)
@pytest.mark.parametrize("bad", [{"in_stock": False}, {"url": "https://store-a.example.com/search?q=libre"}],
                         ids=["oos", "listing_url"])
def test_a22_restore_runs_chokepoint_checks(monkeypatch, cap, bad):
    """A22 PIN: a projected side whose found price the chokepoint refuses ships today's
    pending dict, no amount and no offsize_listing, in both capability cells."""
    setflags(monkeypatch, flag="true", fix="true")
    y = prod("YSL Libre EDP", dict(YSL_P, **bad))
    body, _ = run_pair(y, prod("Lancome La Vie Est Belle EDP", LVEB_P), cap=cap, strict=False)
    assert pending(ov(body)[0]) and "offsize_listing" not in ov(body)[0], ov(body)[0]


# --------------------------------------------------------------------------- P2R-2 rows
@pytest.mark.parametrize("cap", CAPCELLS)
@pytest.mark.parametrize("fix", FIXCELLS)
def test_a35_typed_30_sizeless_listing_vs_100(monkeypatch, fix, cap):
    """A35 RED (P2R-2): Ted typed 30 with a size-less listing vs Dior 100: the typed size
    decides comparability, so the consumers stay limited_data (never a 'less' delta).
    The wire is REWRITTEN by ORCH-P2-B: Dior (typed 100, listing 100) is shown in BOTH
    cells (rule 1); Ted, shown flag OFF, stays shown in both (rule 4), with no size_ml."""
    setflags(monkeypatch, fix=fix)
    t = prod("Ted Baker M 30ml", P(9.5, "Ted Baker M Eau De Toilette", "store-a", "p/ted"))
    d = prod("Dior Sauvage 100 ML Edp", DIOR_P)
    tsrc = copy.deepcopy(t["price"])
    off = flag_off_pend(t, d, TED_Q)
    assert shown(off[0]) and pending(off[1], "size_mismatch"), off
    monkeypatch.setenv(FLAG, "true")
    body, _ = run_pair(t, d, TED_Q, cap=cap)
    dm = dims(body)
    assert dm["price"].get("caption_key") == "limited_data", dm["price"]
    assert "less" not in (dm["price"].get("delta_text") or "").lower()
    assert_open(body, 0, tsrc, None)
    assert_open(body, 1, DIOR_P, 100)


@pytest.mark.parametrize("cap", CAPCELLS)
def test_a36_two_size_listing_vs_100(monkeypatch, cap):
    """A36 RED (P2R-2): a '50ml / 100ml' listing vs a 100 ml partner with no common size
    is NOT comparable (the effective size decides): limited_data."""
    setflags(monkeypatch, fix="true")
    a = prod("Dior Sauvage EDP", P(58.11, "Dior Sauvage EDP 50ml / 100ml", "store-b", "p/sv-x"))
    b = prod("Bleu de Chanel EDP", BLEU_100)
    src = {0: copy.deepcopy(a["price"])}
    off = flag_off_pend(a, b, None)
    monkeypatch.setenv(FLAG, "true")
    body, _ = run_pair(a, b, cap=cap)
    assert dims(body)["price"].get("caption_key") == "limited_data"
    held = {i for i in (0, 1) if pending(off[i], "size_mismatch")}
    assert held == {0}, off
    check_both_shown_cells(monkeypatch, cap, body, off, held, src, {0: None})


# --------------------------------------------------------------------------- ORCH-P2-B rules 1-4 (P2R-23..P2R-26)
TED_50 = P(12.0, "Ted Baker M EDT 50ml", "store-a", "p/t50")
DIOR_NOSIZE = P(58.11, "Dior Sauvage Eau de Parfum", "store-b", "p/sv")
SAUV_60 = P(48.0, "Sauvage EDP 60ml", "store-a", "p/sv-60")


@pytest.mark.parametrize("cap", CAPCELLS)
@pytest.mark.parametrize("fix", FIXCELLS)
def test_r1b_typed_off_size_listing_pending_partner_shown(monkeypatch, fix, cap):
    """R1b RED (rule 1, P2R-23 with P2R-3): Ted typed 30 whose only listing is 50 ml stays
    pending in BOTH cells (never the 12.000 amount, never an offsize_listing); Dior typed 100
    at 100 ml is shown in BOTH cells whatever the other side's state."""
    setflags(monkeypatch, fix=fix)
    t, d = prod("Ted Baker M 30ml", TED_50), prod("Dior Sauvage 100 ML Edp", DIOR_P)
    off = flag_off_pend(t, d, TED_Q)
    assert not shown(off[0]) and pending(off[1], "size_mismatch"), off
    monkeypatch.setenv(FLAG, "true")
    body, _ = run_pair(t, d, TED_Q, cap=cap)
    w = ov(body)
    assert pending(w[0]) and pending(legacy(body)[0]), w[0]
    assert "offsize_listing" not in w[0] and "12.0" not in json.dumps(w[0]), w[0]
    assert_open(body, 1, DIOR_P, 100)


@pytest.mark.parametrize("cap", CAPCELLS)
@pytest.mark.parametrize("fix", FIXCELLS)
def test_r1c_typed_side_with_a_size_less_listing(monkeypatch, fix, cap):
    """R1c RED (rule 1 read through the P2R-2 comparability reader: a size-less listing under
    a typed size reads as that typed size): Dior typed 100 with a size-less listing, pended
    by flag OFF against Ted 30, is shown in BOTH cells with no size_ml (no strict token);
    Ted at its typed 30 is shown in both cells too."""
    setflags(monkeypatch, fix=fix)
    q = "Dior Sauvage 100 ML Edp vs Ted Baker M 30ml"
    d, t = prod("Dior Sauvage 100 ML Edp", DIOR_NOSIZE), prod("Ted Baker M 30ml", TED_P)
    off = flag_off_pend(d, t, q)
    assert pending(off[0], "size_mismatch") and shown(off[1]), off
    monkeypatch.setenv(FLAG, "true")
    body, _ = run_pair(d, t, q, cap=cap)
    assert_open(body, 0, DIOR_NOSIZE, None)
    assert_open(body, 1, TED_P, 30)


@pytest.mark.parametrize("cap", CAPCELLS)
@pytest.mark.parametrize("fix", FIXCELLS)
def test_r2_untyped_off_size_side_gated(monkeypatch, fix, cap):
    """R2 RED (rule 2, P2R-24): two UNTYPED sides, Sauvage at 60 ml vs Bleu at 100 ml, no
    common size: each side flag OFF pends is held without the token (flag OFF's own dict +
    offsize_listing with size_ml 60 / per_ml) and shown with size_ml / per_ml with it; a side
    flag OFF shows stays shown in both cells (rule 4)."""
    setflags(monkeypatch, fix=fix)
    s, b = prod("Sauvage EDP", SAUV_60), prod("Bleu de Chanel EDP", BLEU_100)
    off = flag_off_pend(s, b, None)
    held = {i for i in (0, 1) if pending(off[i], "size_mismatch")}
    assert 0 in held, off
    monkeypatch.setenv(FLAG, "true")
    body, _ = run_pair(s, b, cap=cap)
    src, sizes = {0: SAUV_60, 1: BLEU_100}, {0: 60, 1: 100}
    check_both_shown_cells(monkeypatch, cap, body, off, held, src, sizes)
    for i in {0, 1} - held:
        assert_open(body, i, src[i], sizes[i])


@pytest.mark.parametrize("cap", CAPCELLS)
@pytest.mark.parametrize("fix", FIXCELLS)
@pytest.mark.parametrize("order", ["typed_first", "typed_second"])
def test_r3_mixed_pair(monkeypatch, order, fix, cap):
    """R3 RED (rule 3, P2R-25): in a mixed pair the typed side is shown at its typed size in
    BOTH cells (rule 1) and the untyped side, whose listing size differs from the typed
    side's, is gated by the token (rule 2): held as flag OFF + offsize_listing in cap0,
    shown with size_ml / per_ml in cap1. Both orders."""
    setflags(monkeypatch, fix=fix)
    if order == "typed_first":
        a, b = prod("Ted Baker M 30ml", TED_P), prod("Dior Sauvage EDP", DIOR_P)
        q, ti, ui, tsrc, usrc, tsz, usz = "Ted Baker M 30ml vs Dior Sauvage EDP", 0, 1, TED_P, DIOR_P, 30, 100
    else:
        a, b = prod("Ted Baker M", TED_P), prod("Dior Sauvage 100 ML Edp", DIOR_P)
        q, ti, ui, tsrc, usrc, tsz, usz = "Ted Baker M vs Dior Sauvage 100 ML Edp", 1, 0, DIOR_P, TED_P, 100, 30
    off = flag_off_pend(a, b, q)
    assert shown(off[ti]) and pending(off[ui], "size_mismatch"), off
    monkeypatch.setenv(FLAG, "true")
    body, _ = run_pair(a, b, q, cap=cap)
    assert_open(body, ti, tsrc, tsz)
    check_both_shown_cells(monkeypatch, cap, body, off, {ui}, {ui: usrc}, {ui: usz})


@pytest.mark.parametrize("cap", CAPCELLS)
@pytest.mark.parametrize("fix", FIXCELLS)
def test_r3b_mixed_pair_untyped_at_the_typed_size(monkeypatch, fix, cap):
    """R3b RED (rule 3): an untyped side whose listing size EQUALS the typed side's size is
    never gated: both shown in both cells with size_ml 100, same_size marker, the price dim
    not limited_data, no offsize_listing."""
    setflags(monkeypatch, flag="true", fix=fix)
    d, b = prod("Dior Sauvage 100 ML Edp", DIOR_P), prod("Bleu de Chanel EDP", BLEU_100)
    body, _ = run_pair(d, b, "Dior Sauvage 100 ML Edp vs Bleu de Chanel EDP", cap=cap)
    assert_open(body, 0, DIOR_P, 100)
    assert_open(body, 1, BLEU_100, 100)
    assert body["metadata"].get("pair_price_sizes") == {"mode": "same_size", "sizes_ml": [100, 100]}
    assert dims(body)["price"].get("caption_key") != "limited_data"


_STRICT_ML = re.compile(r"(?<![0-9.,])([0-9]{1,4})[ -]?ml\b", re.I)


def _one_strict_ml(title):
    toks = {int(t) for t in _STRICT_ML.findall(title or "")}
    return next(iter(toks)) if len(toks) == 1 else None


_FLOOR_WORDS = re.compile(r"\b(?:travel|miniature|mini|atomiser|atomizer)\b", re.I)


def _fails_floor(price, product):
    """The P2R-12 floor, read by the test (not by the unit): under 30 ml or a floor word,
    unless the side's own typed size equals the listing's size."""
    title = str((price or {}).get("title") or "")
    n = _one_strict_ml(title)
    typed = ps.extract_size_ml_any(product.get("full_name") or product.get("name") or "")
    if typed is not None and n is not None and int(typed) == n:
        return False
    return (n is not None and n < 30) or bool(_FLOOR_WORDS.search(title))


def _wm(amount, title, host="store-a", path="p/x", sm="local_bhd", retailer=None, url=None, **kw):
    out = P(amount, title, host, path, sm, **kw)
    if retailer:
        out.update(retailer=retailer, url=url)
    return out


# Every pair fixture of this file (rows A04-A48, F*, R*, the ported rows): a builder per id
# returning fresh (side a, side b, query, candidates). Rule 4 walks all of them.
WALK = {
    "a04_ted_dior": lambda: (prod("Ted Baker M 30ml", TED_P), prod("Dior Sauvage 100 ML Edp", DIOR_P), TED_Q, {}),
    "a05_ted_dior_res1": lambda: (prod("Ted Baker M 30ml", TED_P, True),
                                  prod("Dior Sauvage 100 ML Edp", DIOR_P, True), TED_Q, {}),
    "a06_dior50_c100": lambda: (prod("Ted Baker M 30ml", TED_P), prod("Dior Sauvage 100 ML Edp", DIOR_50), TED_Q,
                                {"Dior Sauvage 100 ML Edp": [cand(P(61.0, "Dior Sauvage EDP 100ml", "store-c",
                                                                   "p/sv-100", sm="shopify_json"))]}),
    "a07_dior_bleu150_c100": lambda: (prod("Dior Sauvage 100 ML Edp", DIOR_P), prod("Bleu de Chanel EDP", BLEU_150),
                                      None, {"Bleu de Chanel EDP": [cand(BLEU_100)]}),
    "a08_ted_dior50": lambda: (prod("Ted Baker M 30ml", TED_P), prod("Dior Sauvage 100 ML Edp", DIOR_50), TED_Q, {}),
    "a09_ysl_lveb": lambda: (prod("YSL Libre EDP", YSL_P), prod("Lancome La Vie Est Belle EDP", LVEB_P), None, {}),
    "a10_br_bleu100": lambda: (prod("Baccarat Rouge 540", BR_P), prod("Bleu de Chanel EDP", BLEU_100), None, {}),
    "a11_sauv_bleu150_c100": lambda: (prod("Sauvage EDP", SAUV_100), prod("Bleu de Chanel EDP", BLEU_150), None,
                                      {"Bleu de Chanel EDP": [cand(BLEU_100)]}),
    "a12_common50": lambda: (prod("Sauvage EDP", P(70.0, "Sauvage EDP 75ml", "store-a", "p/sv-75")),
                             prod("Bleu de Chanel EDP", P(95.0, "Bleu de Chanel EDP 125ml", "store-a", "p/bl-125")),
                             None, {"Sauvage EDP": [cand(P(45.0, "Sauvage EDP 50ml", "store-b", "p/sv-50"))],
                                    "Bleu de Chanel EDP": [cand(P(55.0, "Bleu de Chanel EDP 50ml", "store-b",
                                                                  "p/bl-50"))]}),
    "a13_100_preferred": lambda: (prod("Sauvage EDP", P(70.0, "Sauvage EDP 75ml", "store-a", "p/sv-75")),
                                  prod("Bleu de Chanel EDP", BLEU_150), None,
                                  {"Sauvage EDP": [cand(P(80.0, "Sauvage EDP 100ml", "store-b", "p/sv-100")),
                                                   cand(P(99.0, "Sauvage EDP 125ml", "store-b", "p/sv-125"))],
                                   "Bleu de Chanel EDP": [cand(BLEU_100), cand(P(110.0, "Bleu de Chanel EDP 125ml",
                                                                                 "store-b", "p/bl-125"))]}),
    "a14_one_size_less": lambda: (prod("Dior Sauvage EDP", P(58.11, "Dior Sauvage EDP 100ml", "store-b", "p/s")),
                                  prod("Bleu de Chanel EDP", P(80.0, "Bleu de Chanel Eau de Parfum", "store-a", "p/b")),
                                  None, {}),
    "a15_ted50_zara100": lambda: (prod("Ted Baker M", P(12.0, "Ted Baker M EDT 50ml", "store-a", "p/t50")),
                                  prod("Zara Red Vanilla", P(9.0, "Zara Red Vanilla EDT 100ml", "store-a", "p/z100")),
                                  None, {}),
    "a16_estimate": lambda: (prod("Dior Sauvage EDP", P(50.0, "Dior Sauvage EDP 100ml", sm="estimated", estimated=True)),
                             prod("Bleu de Chanel EDP", BLEU_150), None, {}),
    "a16_oos_cand": lambda: (prod("Dior Sauvage EDP", P(58.11, "Dior Sauvage EDP 100ml")),
                             prod("Bleu de Chanel EDP", BLEU_150), None,
                             {"Bleu de Chanel EDP": [cand(P(91.78, "Bleu de Chanel EDP 100ml", in_stock=False))]}),
    "a19_ted_dior_c30": lambda: (prod("Ted Baker M 30ml", TED_P), prod("Dior Sauvage 100 ML Edp", DIOR_P), TED_Q,
                                 {"Dior Sauvage 100 ML Edp": [cand(DIOR_30)]}),
    "a20_dior_bleu100": lambda: (prod("Dior Sauvage EDP", P(58.11, "Dior Sauvage EDP 100ml")),
                                 prod("Bleu de Chanel EDP", BLEU_100), None, {}),
    "a21_oz_two_size": lambda: (prod("Dior Sauvage EDP", P(58.11, "Dior Sauvage EDP 3.4 oz")),
                                prod("Bleu de Chanel EDP", P(80.0, "Bleu de Chanel EDP 50ml / 100ml")), None, {}),
    "a21_estimate_bleu100": lambda: (prod("Dior Sauvage EDP", P(50.0, "Dior Sauvage EDP 100ml", sm="estimated",
                                                                estimated=True)),
                                     prod("Bleu de Chanel EDP", BLEU_100), None, {}),
    "a22_oos": lambda: (prod("YSL Libre EDP", dict(YSL_P, in_stock=False)),
                        prod("Lancome La Vie Est Belle EDP", LVEB_P), None, {}),
    "a22_listing_url": lambda: (prod("YSL Libre EDP", dict(YSL_P, url="https://store-a.example.com/search?q=libre")),
                                prod("Lancome La Vie Est Belle EDP", LVEB_P), None, {}),
    "a30_whatnot_cand": lambda: (prod("Dior Sauvage EDP", P(70.0, "Dior Sauvage EDP 75ml", "store-a", "p/sv-75")),
                                 prod("Bleu de Chanel EDP", BLEU_100), None,
                                 {"Dior Sauvage EDP": [cand(_wm(50.76, "Dior Sauvage EDP 100ml", sm="converted_usd",
                                                               retailer="Whatnot",
                                                               url="https://www.whatnot.com/listing/x"))]}),
    "a35_ted_size_less": lambda: (prod("Ted Baker M 30ml", P(9.5, "Ted Baker M Eau De Toilette", "store-a", "p/ted")),
                                  prod("Dior Sauvage 100 ML Edp", DIOR_P), TED_Q, {}),
    "a36_two_size": lambda: (prod("Dior Sauvage EDP", P(58.11, "Dior Sauvage EDP 50ml / 100ml", "store-b", "p/sv-x")),
                             prod("Bleu de Chanel EDP", BLEU_100), None, {}),
    "a42_kb_side": lambda: (prod("Sauvage EDP", P(70.0, "Sauvage EDP 75ml", "store-a", "p/sv-75", _cached=True,
                                                  _cache_source="kb")),
                            prod("Bleu de Chanel EDP", BLEU_150), None,
                            {"Sauvage EDP": [cand(P(80.0, "Sauvage EDP 100ml", "store-b", "p/sv-100"))],
                             "Bleu de Chanel EDP": [cand(BLEU_100)]}),
    "a43_long_title": lambda: (prod("YSL Libre EDP", P(39.0, "YSL Libre Eau de Parfum 90ml " + "Z" * 150, "store-a",
                                                       "p/libre-90")),
                               prod("Lancome La Vie Est Belle EDP", LVEB_P), None, {}),
    "a44_whatnot_price": lambda: (prod("Dior Sauvage EDP", _wm(50.76, "Dior Sauvage EDP 100ml", sm="converted_usd",
                                                               retailer="Whatnot",
                                                               url="https://www.whatnot.com/listing/x")),
                                  prod("Bleu de Chanel EDP", BLEU_100), None, {}),
    "a45_dior_bleu150": lambda: (prod("Dior Sauvage 100 ML Edp", DIOR_P), prod("Bleu de Chanel EDP", BLEU_150),
                                 "Dior Sauvage 100 ML Edp vs Bleu de Chanel EDP", {}),
    "a46_common125": lambda: (prod("Sauvage EDP", P(70.0, "Sauvage EDP 75ml", "store-a", "p/sv-75")),
                              prod("Bleu de Chanel EDP", BLEU_150), None,
                              {"Sauvage EDP": [cand(P(45.0, "Sauvage EDP 50ml", "store-b", "p/sv-50")),
                                               cand(P(99.0, "Sauvage EDP 125ml", "store-b", "p/sv-125"))],
                               "Bleu de Chanel EDP": [cand(P(55.0, "Bleu de Chanel EDP 50ml", "store-b", "p/bl-50")),
                                                      cand(P(110.0, "Bleu de Chanel EDP 125ml", "store-b",
                                                             "p/bl-125"))]}),
    "a48_ted_size_less_zara30": lambda: (prod("Ted Baker M 30ml", P(9.5, "Ted Baker M Eau De Toilette", "store-a",
                                                                    "p/ted")),
                                         prod("Zara Red Vanilla", P(9.0, "Zara Red Vanilla EDT 30ml", "store-a",
                                                                    "p/z30")),
                                         "Ted Baker M 30ml vs Zara Red Vanilla", {}),
    "f2_travel_c100": lambda: (prod("Dior Sauvage EDP", P(10.0, "Dior Sauvage EDP Travel Spray 10ml", "store-a", "p/tr")),
                               prod("Bleu de Chanel EDP", BLEU_100), None,
                               {"Dior Sauvage EDP": [cand(P(58.11, "Dior Sauvage EDP 100ml", "store-b", "p/sv"))]}),
    "f2_travel": lambda: (prod("Dior Sauvage EDP", P(10.0, "Dior Sauvage EDP Travel Spray 10ml", "store-a", "p/tr")),
                          prod("Bleu de Chanel EDP", BLEU_100), None, {}),
    "f3_typed_10ml": lambda: (prod("Dior Sauvage 10ml", P(8.0, "Dior Sauvage EDP Travel Spray 10ml", "store-a", "p/tr")),
                              prod("Bleu de Chanel EDP", BLEU_100), "Dior Sauvage 10ml vs Bleu de Chanel EDP", {}),
    "f4_mini_common": lambda: (prod("Sauvage EDP", P(70.0, "Sauvage EDP 75ml", "store-a", "p/sv-75")),
                               prod("Bleu de Chanel EDP", P(95.0, "Bleu de Chanel EDP 125ml", "store-a", "p/bl-125")),
                               None, {"Sauvage EDP": [cand(P(20.0, "Sauvage EDP Mini 50ml", "store-b", "p/sv-50"))],
                                      "Bleu de Chanel EDP": [cand(P(22.0, "Bleu de Chanel EDP Mini 50ml", "store-b",
                                                                    "p/bl-50"))]}),
    "r1b_ted50_dior100": lambda: (prod("Ted Baker M 30ml", TED_50), prod("Dior Sauvage 100 ML Edp", DIOR_P), TED_Q, {}),
    "r1c_dior_size_less_ted30": lambda: (prod("Dior Sauvage 100 ML Edp", DIOR_NOSIZE), prod("Ted Baker M 30ml", TED_P),
                                         "Dior Sauvage 100 ML Edp vs Ted Baker M 30ml", {}),
    "r2_sauv60_bleu100": lambda: (prod("Sauvage EDP", SAUV_60), prod("Bleu de Chanel EDP", BLEU_100), None, {}),
    "r3_typed_first": lambda: (prod("Ted Baker M 30ml", TED_P), prod("Dior Sauvage EDP", DIOR_P),
                               "Ted Baker M 30ml vs Dior Sauvage EDP", {}),
    "r3_typed_second": lambda: (prod("Ted Baker M", TED_P), prod("Dior Sauvage 100 ML Edp", DIOR_P),
                                "Ted Baker M vs Dior Sauvage 100 ML Edp", {}),
    "r3b_dior100_bleu100": lambda: (prod("Dior Sauvage 100 ML Edp", DIOR_P), prod("Bleu de Chanel EDP", BLEU_100),
                                    "Dior Sauvage 100 ML Edp vs Bleu de Chanel EDP", {}),
    "f01_two_travel_sprays": lambda: (prod("Dior Sauvage EDP", P(10.0, "Dior Sauvage EDP Travel Spray 10ml", "store-a",
                                                                 "p/tr")),
                                      prod("Bleu de Chanel EDP", P(11.0, "Bleu de Chanel EDP Travel Spray 10ml",
                                                                   "store-b", "p/btr")), None, {}),
    "f03_atomizer_vs_ysl": lambda: (prod("Dior Sauvage EDP", P(10.0, "Dior Sauvage EDP Atomizer 10ml", "store-a",
                                                               "p/at")),
                                    prod("YSL Libre EDP", YSL_P), None, {}),
    "f06_plain_15ml": lambda: (prod("Dior Sauvage EDP", P(12.0, "Dior Sauvage EDP 15ml", "store-a", "p/sv-15")),
                               prod("YSL Libre EDP", YSL_P), None, {}),
    "f05_minimalist": lambda: (prod("Dominique Minimalist EDP", P(45.0, "Dominique Minimalist EDP 100ml", "store-a",
                                                                  "p/dm")),
                               prod("Lancome La Vie Est Belle EDP", LVEB_P), None, {}),
    "b14k_kb_ysl": lambda: (prod("YSL Libre EDP", dict(YSL_P, _cached=True, _cache_source="kb")),
                            prod("Lancome La Vie Est Belle EDP", LVEB_P), None, {}),
}


@pytest.mark.parametrize("cap", CAPCELLS)
@pytest.mark.parametrize("fix", FIXCELLS)
@pytest.mark.parametrize("fx", sorted(WALK))
def test_r4_no_side_shown_flag_off_is_lost(monkeypatch, fx, fix, cap):
    """R4 RED (rule 4, P2R-26): walk EVERY pair fixture of this file, both fix cells, both
    capability cells (cap0 = the token absent, the cell the rule is about): every side flag
    OFF shows is shown with the flag ON, and carries the flag's size stamp (size_ml) when its
    shown listing has exactly one strict ml size. The one stated exemption: a side whose flag
    OFF price fails the P2R-12 floor (under 30 ml or a travel / mini word, not at its own
    typed size) is removed by the floor in EVERY cell, never because the token is absent."""
    need("price_not_lost_enabled")
    setflags(monkeypatch, fix=fix)
    a, b, q, c = WALK[fx]()
    off_body, _ = run_pair(copy.deepcopy(a), copy.deepcopy(b), q, copy.deepcopy(c))
    was = shown_idx(ov(off_body))
    exempt = {i for i in was if _fails_floor(ov(off_body)[i], (a, b)[i])}
    monkeypatch.setenv(FLAG, "true")
    body, _ = run_pair(copy.deepcopy(a), copy.deepcopy(b), q, copy.deepcopy(c), cap=cap)
    w = ov(body)
    assert (was - exempt) <= shown_idx(w), (fx, ov(off_body), w)
    for i in was - exempt:
        n = _one_strict_ml(w[i].get("title"))
        if n:
            assert w[i].get("size_ml") == n, (fx, i, w[i])


# --------------------------------------------------------------------------- floor (P2R-12)
TRAVEL = "Dior Sauvage EDP Travel Spray 10ml"


@pytest.mark.parametrize("amount", [8.0, 10.0, 12.0])
def test_f1_travel_spray_passes_today(monkeypatch, amount):
    """F1 PIN (the measured gap, P2R-12): a 10 ml travel spray at 8 / 10 / 12 BHD passes
    the plausibility floor at the base (both correctness modes)."""
    p = P(amount, TRAVEL, "store-a", "p/tr")
    assert ps.is_price_showable("Dior Sauvage EDP", copy.deepcopy(p), FRAG) is True
    assert ps.is_price_showable("Dior Sauvage EDP", copy.deepcopy(p), FRAG, enforce_correctness=True) is True


@pytest.mark.parametrize("cap", CAPCELLS)
@pytest.mark.parametrize("amount", [8.0, 10.0, 12.0])
def test_f2_floor_reselects_or_pends(monkeypatch, amount, cap):
    """F2 RED: an untyped side whose price is a 10 ml travel spray is re-selected to a
    floor-passing candidate when one exists, else pended pending_genuine (never shown,
    never an offsize_listing)."""
    setflags(monkeypatch, flag="true", fix="true")
    s = prod("Dior Sauvage EDP", P(amount, TRAVEL, "store-a", "p/tr"))
    body, _ = run_pair(s, prod("Bleu de Chanel EDP", BLEU_100),
                       cands={"Dior Sauvage EDP": [cand(P(58.11, "Dior Sauvage EDP 100ml", "store-b", "p/sv"))]}, cap=cap)
    assert ov(body)[0].get("amount") == 58.11, ov(body)[0]
    s = prod("Dior Sauvage EDP", P(amount, TRAVEL, "store-a", "p/tr"))
    body, _ = run_pair(s, prod("Bleu de Chanel EDP", BLEU_100), cap=cap)
    assert pending(ov(body)[0], "pending_genuine") and "offsize_listing" not in ov(body)[0], ov(body)[0]
    assert str(amount) not in json.dumps(ov(body)[0])


@pytest.mark.parametrize("flag", [None, "true"])
def test_f3_typed_10ml_keeps_10ml(monkeypatch, flag):
    """F3 PIN: a typed '10ml' side keeps its 10 ml price (both flag values)."""
    setflags(monkeypatch, flag=flag, fix="true")
    s = prod("Dior Sauvage 10ml", P(8.0, TRAVEL, "store-a", "p/tr"))
    body, _ = run_pair(s, prod("Bleu de Chanel EDP", BLEU_100), "Dior Sauvage 10ml vs Bleu de Chanel EDP", cap=True,
                       strict=False)
    assert ov(body)[0].get("amount") == 8.0, ov(body)[0]


@pytest.mark.parametrize("word", ["Travel Spray", "Miniature", "Mini", "Atomiser", "Atomizer"])
def test_f4_floor_words_and_common_size(monkeypatch, word):
    """F4 RED: the common-size re-selection never lands on a sub-30 ml or travel-worded
    candidate; both keep their found prices (cap1 shows both)."""
    setflags(monkeypatch, flag="true", fix="true")
    s = prod("Sauvage EDP", P(70.0, "Sauvage EDP 75ml", "store-a", "p/sv-75"))
    b = prod("Bleu de Chanel EDP", P(95.0, "Bleu de Chanel EDP 125ml", "store-a", "p/bl-125"))
    c = {"Sauvage EDP": [cand(P(20.0, "Sauvage EDP %s 50ml" % word, "store-b", "p/sv-50"))],
         "Bleu de Chanel EDP": [cand(P(22.0, "Bleu de Chanel EDP %s 50ml" % word, "store-b", "p/bl-50"))]}
    body, _ = run_pair(s, b, None, c, cap=True)
    assert [p.get("amount") for p in ov(body)] == [70.0, 95.0], ov(body)


@pytest.mark.parametrize("cap", CAPCELLS)
@pytest.mark.parametrize("amount", [8.0, 10.0, 12.0])
@pytest.mark.parametrize("fix", FIXCELLS)
def test_f01_two_travel_sprays_never_shown(monkeypatch, fix, amount, cap):
    """F01 RED (ported from agent A's f01, P2R-12): BOTH sides are 10 ml travel sprays with
    no floor-passing candidate: neither is ever shown, in either capability cell (both
    pending_genuine, no offsize_listing, no amount on the wire)."""
    setflags(monkeypatch, flag="true", fix=fix)
    a = prod("Dior Sauvage EDP", P(amount, TRAVEL, "store-a", "p/tr"))
    b = prod("Bleu de Chanel EDP", P(amount + 1, "Bleu de Chanel EDP Travel Spray 10ml", "store-b", "p/btr"))
    body, _ = run_pair(a, b, cap=cap)
    for i, p in enumerate(ov(body)):
        assert pending(p, "pending_genuine") and "offsize_listing" not in p, (i, p)
        assert pending(legacy(body)[i]), legacy(body)[i]


@pytest.mark.parametrize("cap", CAPCELLS)
@pytest.mark.parametrize("fix", FIXCELLS)
def test_f03_floor_on_the_both_shown_path(monkeypatch, fix, cap):
    """F03 RED (ported from agent A's f03, P2R-12 'the both-shown path'): an untyped 10 ml
    atomizer side against an untyped YSL 90 ml side: the floor pends the atomizer
    (pending_genuine, never shown, never an offsize_listing) in both cells and YSL keeps its
    39.000 with size_ml 90 in both cells (no other shown price to differ from)."""
    setflags(monkeypatch, flag="true", fix=fix)
    a = prod("Dior Sauvage EDP", P(10.0, "Dior Sauvage EDP Atomizer 10ml", "store-a", "p/at"))
    body, _ = run_pair(a, prod("YSL Libre EDP", YSL_P), cap=cap)
    p0 = ov(body)[0]
    assert pending(p0, "pending_genuine") and "offsize_listing" not in p0, p0
    assert_open(body, 1, YSL_P, 90)


@pytest.mark.parametrize("cap", CAPCELLS)
@pytest.mark.parametrize("fix", FIXCELLS)
def test_f06_a_plain_15ml_listing_is_under_the_floor(monkeypatch, fix, cap):
    """F06 RED (ported from agent A's f06, P2R-12 'under 30 ml'): a plain 15 ml listing with
    NO floor word is under the floor too: pending_genuine in both cells, never shown, never an
    offsize_listing; YSL keeps its 39.000 (size_ml 90) in both cells."""
    setflags(monkeypatch, flag="true", fix=fix)
    a = prod("Dior Sauvage EDP", P(12.0, "Dior Sauvage EDP 15ml", "store-a", "p/sv-15"))
    body, _ = run_pair(a, prod("YSL Libre EDP", YSL_P), cap=cap)
    p0 = ov(body)[0]
    assert pending(p0, "pending_genuine") and "offsize_listing" not in p0, p0
    assert_open(body, 1, YSL_P, 90)


@pytest.mark.parametrize("flag", [None, "true"])
@pytest.mark.parametrize("fix", FIXCELLS)
def test_f05_floor_word_match_is_whole_word_pin(monkeypatch, fix, flag):
    """F05 PIN (ported from agent A's f05; P2R-12 'Mini inside a line name', D4): no line in
    data/fragrance_lines.json or the lexicon carries the word (measured); the floor's word
    rule is whole-word, so 'Dominique Minimalist' 100 ml keeps its price (both flag values)."""
    setflags(monkeypatch, flag=flag, fix=fix)
    a = prod("Dominique Minimalist EDP", P(45.0, "Dominique Minimalist EDP 100ml", "store-a", "p/dm"))
    body, _ = run_pair(a, prod("Lancome La Vie Est Belle EDP", LVEB_P), cap=False, strict=False)
    w = ov(body)
    assert shown(w[0]) and w[0]["amount"] == 45.0, w[0]
    assert shown(w[1]) and w[1]["amount"] == 34.0, w[1]
    assert "size_mismatch" not in json.dumps(w) and "pending_genuine" not in json.dumps(w)


@pytest.mark.parametrize("cap", CAPCELLS)
def test_b14k_kb_served_cell(monkeypatch, cap):
    """B14k RED (ported from agent A's b14k; it replaces the KB pipeline cell B's report
    dropped): with ENABLE_KB_FIRST_SERVE on, a KB-served YSL price (_cache_source kb) follows
    the same rules as a live one: the side flag OFF pends is held + offsize_listing in cap0
    and shown with size_ml in cap1; it is never marked for the cache write (P2R-5)."""
    setflags(monkeypatch, fix="true")
    monkeypatch.setenv("ENABLE_KB_FIRST_SERVE", "true")
    kb = dict(YSL_P, _cached=True, _cache_source="kb")
    y, l = prod("YSL Libre EDP", kb), prod("Lancome La Vie Est Belle EDP", LVEB_P)
    off = flag_off_pend(y, l, None)
    held = {i for i in (0, 1) if pending(off[i], "size_mismatch")}
    assert held == {0}, off
    monkeypatch.setenv(FLAG, "true")
    body, snap = run_pair(y, l, cap=cap)
    check_both_shown_cells(monkeypatch, cap, body, off, held, {0: YSL_P}, {0: 90})
    assert_open(body, 1, LVEB_P, 100)
    assert all(s.get("_p2_reselected") is not True for s in snap)


# --------------------------------------------------------------------------- numbers_match (P2-8)
def test_a23_numbers_match_size_tokens(monkeypatch):
    """A23 RED: flag ON, product-side ml / oz numbers are ignored."""
    setflags(monkeypatch, flag="true")
    for t in ("Sauvage EDP 100ml", "Dior Sauvage EDP 100ml/3.4oz", "DIOR Sauvage Eau de Parfum Spray"):
        assert ps.numbers_match("Dior Sauvage 100 ML Edp", t) is True, t
    assert ps.numbers_match("Sauvage 100 ML 3.4 FL OZ", "Sauvage EDT") is True


def test_a24_numbers_match_other_numbers_kept(monkeypatch):
    """A24 PIN: flag ON, every other number still has to appear."""
    setflags(monkeypatch, flag="true")
    rows = [("iPhone 16 256GB", "Apple iPhone 15 256GB"), ("NOW D-3 360 Softgels", "NOW D-3 120 Softgels"),
            ("Baccarat Rouge 540 70 ML", "Baccarat Rouge Extrait 70ml"),
            ("Le Labo Santal 33 100 ML", "Le Labo Another 13 EDP 100ml"),
            ("Creed Aventus 100 ML 2024", "Creed Aventus EDP 100ml")]
    for a, b in rows:
        assert ps.numbers_match(a, b) is False, (a, b)


def test_a25_numbers_match_flag_off(monkeypatch):
    """A25 PIN (full configuration): flag OFF, today's rejections."""
    setflags(monkeypatch, flag=None)
    for t in ("Sauvage EDP 100ml", "Dior Sauvage EDP 100ml/3.4oz", "DIOR Sauvage Eau de Parfum Spray"):
        assert ps.numbers_match("Dior Sauvage 100 ML Edp", t) is False, t


def test_a26_every_caller_follows(monkeypatch):
    """A26 RED: SCS's static wrapper and the Shopping picker follow the function."""
    import app.services.structured_comparison_service as scs
    name, title = "Dior Sauvage 100 ML Edp", "Sauvage EDP 100ml"
    setflags(monkeypatch, flag=None)
    assert scs.StructuredComparisonService._numbers_match(name, title) is False
    setflags(monkeypatch, flag="true")
    assert scs.StructuredComparisonService._numbers_match(name, title) is True


# --------------------------------------------------------------------------- marketplaces (P2-10)
def test_a27_marketplace_predicate():
    """A27 RED (+ C-7): whole tokens of the seller name or the host label."""
    fn = need("is_auction_marketplace_seller")
    for r, u in (("Whatnot", None), (None, "https://www.whatnot.com/x"), ("eBay - seller", None),
                 (None, "https://www.ebay.co.uk/itm/1"), ("Back Market", None), ("eBay.com", None),
                 ("Whatnot.com", None), ("The RealReal", None)):
        assert fn(r, u) is True, (r, u)
    for r, u in (("Wishlist Perfumes", None), ("Jomashop.com", "https://www.jomashop.com/x"),
                 (None, None), (5, object())):
        assert fn(r, u) is False, (r, u)


def shop_items():
    return [{"title": "Dior Sauvage Eau de Parfum 100ml", "price": "BHD 50.760", "source": "Whatnot",
             "link": "https://www.whatnot.com/listing/x"},
            {"title": "Dior Sauvage Eau de Parfum 100ml", "price": "BHD 57.500", "source": "Jomashop.com",
             "link": "https://www.jomashop.com/dior-sauvage-edp-100.html"}]


@pytest.mark.parametrize("dg", [None, "true"])
def test_a28_tier1_pick_skips_whatnot(monkeypatch, dg):
    """A28 RED: flag ON the Tier-1 pick never comes from an auction seller."""
    setflags(monkeypatch, flag="true")
    if dg:
        monkeypatch.setenv("ENABLE_DATA_GUARDS_V2", dg)
    pick = ps.extract_price_from_shopping("Dior Sauvage EDP 100ml", shop_items(), "BHD", category=FRAG)
    assert pick is not None and pick.get("retailer") == "Jomashop.com", pick
    assert ps.extract_price_from_shopping("Dior Sauvage EDP 100ml", shop_items()[:1], "BHD", category=FRAG) is None


def test_a29_tier1_pick_flag_off(monkeypatch):
    """A29 PIN: flag OFF, today's pick (Whatnot alone is picked)."""
    setflags(monkeypatch, flag=None)
    pick = ps.extract_price_from_shopping("Dior Sauvage EDP 100ml", shop_items()[:1], "BHD", category=FRAG)
    assert pick is not None and pick.get("retailer") == "Whatnot", pick


def test_a30_reselection_skips_marketplaces(monkeypatch):
    """A30 RED: the only target-size candidate is a Whatnot row: never re-selected."""
    setflags(monkeypatch, flag="true", fix="true")
    s = prod("Dior Sauvage EDP", P(70.0, "Dior Sauvage EDP 75ml", "store-a", "p/sv-75"))
    w = P(50.76, "Dior Sauvage EDP 100ml", sm="converted_usd")
    w.update(retailer="Whatnot", url="https://www.whatnot.com/listing/x")
    body, snap = run_pair(s, prod("Bleu de Chanel EDP", BLEU_100), cands={"Dior Sauvage EDP": [cand(w)]}, cap=True)
    assert "whatnot" not in json.dumps(ov(body)).lower()
    assert ov(body)[0].get("amount") == 70.0, ov(body)[0]


def test_a37_filter_marketplace_rows(monkeypatch):
    """A37 RED (C-5 a): the adapter converted-park filter drops marketplace rows flag ON
    and returns the SAME list object flag OFF."""
    fn = need("p2_filter_marketplace_rows")
    rows = [{"retailer": "Whatnot", "url": "https://www.whatnot.com/x", "amount": 1.0},
            {"retailer": "store-b.example.com", "url": "https://store-b.example.com/p", "amount": 2.0}]
    setflags(monkeypatch, flag=None)
    assert fn(rows) is rows
    setflags(monkeypatch, flag="true")
    assert [r["amount"] for r in fn(rows)] == [2.0]


# --------------------------------------------------------------------------- the header (P2R-18/21)
class Req:
    def __init__(self, value):
        self.headers = {} if value is None else {"x-client-capabilities": value}


@pytest.mark.parametrize("value,exp", [(None, False), ("price_asof", False), ("price_asof, other", False),
                                       (" Price_Size ", True), ("price_asof, price_size", True),
                                       ("PRICE_SIZE,x", True), ("price_size" + "," * 600, False)],
                         ids=["absent", "other", "others", "mixed_case_spaces", "list", "upper", "too_long"])
def test_h1_header_reader(monkeypatch, value, exp):
    """H1 RED: the token reader, comma separated, stripped, case-insensitive; never
    dependent on ENABLE_KB_FIRST_SERVE (unset here)."""
    fn = need("client_price_size")
    setflags(monkeypatch, flag="true")
    assert fn(Req(value)) is exp


def test_h2_header_reader_switch_off(monkeypatch):
    """H2 RED: flag OFF reads no header (the token present -> False); flag ON with the KB
    flag ON or OFF -> True."""
    fn = need("client_price_size")
    setflags(monkeypatch, flag=None)
    assert fn(Req("price_size")) is False
    setflags(monkeypatch, flag="true")
    monkeypatch.setenv("ENABLE_KB_FIRST_SERVE", "true")
    assert fn(Req("price_size")) is True
    assert fn(object()) is False


def test_h3_capability_contextvar():
    """H3 RED: the request-scoped capability: False by default, True once bound, never
    leaking out of its context."""
    bind = need("price_size_cap_bind")
    get = need("price_size_cap")
    assert get() is False

    def _in():
        bind(True)
        return get()
    assert contextvars.copy_context().run(_in) is True
    assert get() is False


@pytest.mark.parametrize("fix", FIXCELLS)
def test_h4_flag_off_with_token_pin(monkeypatch, fix):
    """H4 PIN (P2R-21): flag OFF with the token present: today's body (Dior pending, no
    offsize_listing, no size keys, no marker)."""
    setflags(monkeypatch, flag=None, fix=fix)
    t, d = prod("Ted Baker M 30ml", TED_P), prod("Dior Sauvage 100 ML Edp", DIOR_P)

    def _go():
        b = getattr(ps, "price_size_cap_bind", None)
        if b is not None:
            b(True)
        pd = [t, d]
        ps.reconcile_pair_fairness(pd, TED_Q, FRAG, candidates_by_name={})
        return build(pd, TED_Q)
    body = contextvars.copy_context().run(_go)
    w = ov(body)
    assert shown(w[0]) and pending(w[1], "size_mismatch")
    for p in w:
        assert not ({"size_ml", "per_ml", "offsize_listing"} & set(p)), p
    assert "pair_price_sizes" not in body["metadata"]


# --------------------------------------------------------------------------- the log lines
def outcome_records(caplog):
    return [r for r in caplog.records if r.getMessage().startswith("PRICE_OUTCOME")]


def fields(msg):
    return dict(m.groups() for m in re.finditer(r"(\w+)=(\S*)", msg))


@pytest.mark.parametrize("fix", FIXCELLS)
def test_a31_price_outcome_flag_off(monkeypatch, caplog, fix):
    """A31 RED: flag OFF, one PRICE_OUTCOME per product with the P2R-11 / P2R-7 / P2R-21
    fields; the size-pended side says reconcile=pend pend_reason=size_mismatch."""
    setflags(monkeypatch, flag=None, fix=fix)
    caplog.set_level(logging.INFO)
    run_pair(prod("Ted Baker M 30ml", TED_P), prod("Dior Sauvage 100 ML Edp", DIOR_P), TED_Q)
    recs = outcome_records(caplog)
    assert len(recs) == 2, [r.getMessage() for r in recs]
    f = [fields(r.getMessage()) for r in recs]
    for one in f:
        assert set(OUTCOME_FIELDS) <= set(one), sorted(one)
        assert one["cap"] == "none"
    assert f[1]["reconcile"] == "pend" and f[1]["pend_reason"] == "size_mismatch"
    assert f[0]["shown"] == "yes" and f[0]["size_ml"] == "30" and f[0]["marketplace"] == "0"


def test_a32_price_outcome_no_path_no_personal(monkeypatch, caplog):
    """A32 RED (P2-19): the retailer host only, never the path or query; no user id,
    device id, IP or header field; product cut to 60."""
    setflags(monkeypatch, flag=None, fix="true")
    caplog.set_level(logging.INFO)
    long = "Dior Sauvage EDP " + "X" * 80
    a = prod(long, P(58.11, "Dior Sauvage EDP 100ml", "store-a", "p/x?ref=y"))
    run_pair(a, prod("Bleu de Chanel EDP", BLEU_100))
    recs = outcome_records(caplog)
    assert recs, "no PRICE_OUTCOME"
    msg = recs[0].getMessage()
    assert "/p/x" not in msg and "ref=y" not in msg
    for bad in ("user", "device", "ip=", "header", "email", "token"):
        assert bad not in msg.lower().replace("price_size", ""), (bad, msg)
    assert len(fields(msg)["product"]) <= 60


@pytest.mark.parametrize("cap", CAPCELLS)
def test_a38_price_outcome_cap_and_reconcile(monkeypatch, caplog, cap):
    """A38 RED (P2R-21), REWRITTEN by ORCH-P2-B: the T3-01 Dior side (typed, at its typed
    size) logs reconcile=both_shown in BOTH cells (rule 1); an untyped off-size side (Bleu
    150 against a typed Dior 100) logs both_shown under cap=price_size and offsize_held
    under cap=none (rule 3); cap= names the cell on every line."""
    setflags(monkeypatch, flag="true", fix="true")
    caplog.set_level(logging.INFO)
    run_pair(prod("Ted Baker M 30ml", TED_P), prod("Dior Sauvage 100 ML Edp", DIOR_P), TED_Q, cap=cap)
    f = [fields(r.getMessage()) for r in outcome_records(caplog)]
    assert len(f) == 2, f
    assert f[1]["cap"] == ("price_size" if cap else "none")
    assert f[1]["reconcile"] == "both_shown" and f[1]["shown"] == "yes", f[1]
    assert f[1]["size_ml"] == "100"
    caplog.clear()
    run_pair(prod("Dior Sauvage 100 ML Edp", DIOR_P), prod("Bleu de Chanel EDP", BLEU_150),
             "Dior Sauvage 100 ML Edp vs Bleu de Chanel EDP", cap=cap)
    f = [fields(r.getMessage()) for r in outcome_records(caplog)]
    assert len(f) == 2, f
    assert f[0]["shown"] == "yes" and f[0]["cap"] == f[1]["cap"] == ("price_size" if cap else "none")
    assert f[1]["reconcile"] == ("both_shown" if cap else "offsize_held"), f[1]
    assert f[1]["size_ml"] == "150"


class _Boom(Exception):
    pass


def test_a39_price_outcome_raising_logger(monkeypatch):
    """A39 RED (P2R-10): a logger that raises on PRICE_OUTCOME changes nothing in the
    body, and the line was attempted (one attempt per product)."""
    setflags(monkeypatch, flag=None, fix="true")
    normal, _ = run_pair(prod("Ted Baker M 30ml", TED_P), prod("Dior Sauvage 100 ML Edp", DIOR_P), TED_Q)
    attempts = []
    real = rb.logger.info

    def _info(msg, *a, **k):
        if str(msg).startswith("PRICE_OUTCOME"):
            attempts.append(1)
            raise _Boom("logger down")
        return real(msg, *a, **k)
    monkeypatch.setattr(rb.logger, "info", _info)
    body, _ = run_pair(prod("Ted Baker M 30ml", TED_P), prod("Dior Sauvage 100 ML Edp", DIOR_P), TED_Q)
    assert len(attempts) == 2
    strip = lambda b: json.dumps({k: v for k, v in b.items() if k != "metadata"}, sort_keys=True, default=str)
    assert strip(body) == strip(normal)


def test_a40_price_outcome_raising_formatter(monkeypatch):
    """A40 RED (P2R-10): a field builder that raises (listing_size_ml) never fails the
    build flag OFF; the line is skipped."""
    need("listing_size_ml")
    setflags(monkeypatch, flag=None, fix="true")
    normal, _ = run_pair(prod("YSL Libre EDP", YSL_P), prod("Lancome La Vie Est Belle EDP", LVEB_P))

    def _raise(*_a, **_k):
        raise _Boom("formatter down")
    monkeypatch.setattr(ps, "listing_size_ml", _raise)
    body, _ = run_pair(prod("YSL Libre EDP", YSL_P), prod("Lancome La Vie Est Belle EDP", LVEB_P))
    assert ov(body) == ov(normal)


def test_a41_trace_note_raising(monkeypatch, caplog):
    """A41 RED (P2R-10, C-6): the unflagged trace note in the fragrance branch raising
    never fails the reconcile (no exception, prices as without the fault)."""
    need("price_trace_note")
    setflags(monkeypatch, flag=None, fix="true")
    pd_ok = [prod("Ted Baker M 30ml", TED_P), prod("Dior Sauvage 100 ML Edp", DIOR_P)]
    in_ctx(lambda: ps.reconcile_pair_fairness(pd_ok, TED_Q, FRAG, candidates_by_name={}))

    def _raise(*_a, **_k):
        raise _Boom("trace down")
    monkeypatch.setattr(ps, "price_trace_note", _raise)
    pd = [prod("Ted Baker M 30ml", TED_P), prod("Dior Sauvage 100 ML Edp", DIOR_P)]
    in_ctx(lambda: ps.reconcile_pair_fairness(pd, TED_Q, FRAG, candidates_by_name={}))
    assert [p["price"] for p in pd] == [p["price"] for p in pd_ok]


# --------------------------------------------------------------------------- the miss ledger (P2R-11)
def test_l1_closest_to_success_wins():
    """L1 RED: rejected > no_price_parsed > refused > not_found > timed_out; host, status,
    rule, family counts."""
    bind, note, summ = need("price_trace_bind"), need("price_miss_note"), need("price_miss_summary")

    def _go():
        bind()
        n = "Dior Sauvage EDP"
        note(n, "timed_out", family="race")
        assert summ(n)["miss"] == "timed_out"
        note(n, "not_found", family="woo")
        assert summ(n)["miss"] == "not_found"
        note(n, "refused", family="shopify", host="store-c.example.com", status=403)
        s = summ(n)
        assert (s["miss"], s["miss_host"], s["miss_status"]) == ("refused", "store-c.example.com", "403")
        note(n, "no_price_parsed", family="fanout_curl", host="store-d.example.com")
        assert summ(n)["miss"] == "no_price_parsed"
        note(n, "rejected", family="shopping", rule="numbers_match", title="T" * 90)
        note(n, "rejected", family="shopping", rule="numbers_match", title="U" * 10)
        note(n, "rejected", family="shopping", rule="numbers_match", title="V" * 10)
        s = summ(n)
        assert s["miss"] == "rejected" and s["miss_rule"] == "numbers_match"
        assert s["rejected"]["numbers_match"] == 3
        assert s["examples"]["numbers_match"] == ["T" * 60, "U" * 10]
        assert "shopify" in s["fam"] and "shopping" in s["fam"]
        assert summ("other product")["miss"] == "none"
    contextvars.copy_context().run(_go)


def test_l2_unbound_never_raises():
    """L2 RED: with no trace bound every helper is a no-op and never raises."""
    note, summ = need("price_miss_note"), need("price_miss_summary")

    def _go():
        note("x", "rejected", rule="floor")
        assert summ("x")["miss"] in ("none", "unknown")
    contextvars.copy_context().run(_go)


def test_l3_ledger_survives_cancel():
    """L3 RED: a note made inside a task that is then cancelled stays in the ledger the
    request bound before the task started."""
    bind, note, summ = need("price_trace_bind"), need("price_miss_note"), need("price_miss_summary")

    async def _main():
        bind()

        async def _price_task():
            note("Dior Sauvage EDP", "refused", family="shopify", host="store-c.example.com", status=403)
            await asyncio.sleep(10)
        t = asyncio.ensure_future(_price_task())
        await asyncio.sleep(0.01)
        t.cancel()
        try:
            await t
        except asyncio.CancelledError:
            pass
        return summ("Dior Sauvage EDP")
    s = contextvars.copy_context().run(lambda: asyncio.run(_main()))
    assert s["miss"] == "refused" and s["miss_status"] == "403"


def test_l4_shopping_filters_recorded(monkeypatch):
    """L4 RED: extract_price_from_shopping records its rejections for the product the
    task is pricing (numbers_match unflagged; marketplace under the flag)."""
    bind, prod_bind, summ = need("price_trace_bind"), need("price_trace_product"), need("price_miss_summary")
    setflags(monkeypatch, flag="true")
    items = [{"title": "Dior Sauvage Eau de Parfum 50ml Limited 2019", "price": "BHD 40.000",
              "source": "store-e.example.com", "link": "https://store-e.example.com/p/a"},
             shop_items()[0]]

    def _go():
        bind()
        prod_bind("Dior Sauvage EDP 2024")
        ps.extract_price_from_shopping("Dior Sauvage EDP 2024", items, "BHD", category=FRAG)
        return summ("Dior Sauvage EDP 2024")
    s = contextvars.copy_context().run(_go)
    assert s["miss"] == "rejected", s
    assert s["rejected"].get("numbers_match", 0) >= 1, s


@pytest.mark.parametrize("cap", CAPCELLS)
def test_l5_floor_pend_is_recorded(monkeypatch, caplog, cap):
    """L5 RED: a floor pend carries miss=rejected miss_rule=floor on its PRICE_OUTCOME."""
    setflags(monkeypatch, flag="true", fix="true")
    caplog.set_level(logging.INFO)

    def _go():
        need("price_trace_bind")()
        s = prod("Dior Sauvage EDP", P(10.0, TRAVEL, "store-a", "p/tr"))
        pd = [s, prod("Bleu de Chanel EDP", BLEU_100)]
        ps.reconcile_pair_fairness(pd, None, FRAG, candidates_by_name={})
        return build(pd)
    in_ctx(_go, cap)
    f = [fields(r.getMessage()) for r in outcome_records(caplog)]
    assert f and f[0]["miss"] == "rejected" and f[0]["miss_rule"] == "floor", f


def test_l05_outcome_reads_the_ledger_and_the_body_does_not(monkeypatch, caplog):
    """L05 RED (ported from agent A's l05; P2R-11 'nothing in a response body reads them'):
    flag OFF, a ledger note for Dior changes Dior's PRICE_OUTCOME line (miss=rejected
    miss_rule=numbers_match rejected=numbers_match=1) and never the body."""
    bind, note = need("price_trace_bind"), need("price_miss_note")
    setflags(monkeypatch, flag=None, fix="true")
    pend = ps.make_pending_price("BHD", "pending_genuine")

    def mk():
        d = prod("Dior Sauvage 100 ML Edp", DIOR_P)
        d.update(price=dict(pend), best_price=None, retailer=None)
        return [prod("Ted Baker M 30ml", TED_P), d]

    def _plain():
        bind()
        return build(mk(), TED_Q)

    def _noted():
        bind()
        note("Dior Sauvage 100 ML Edp", "rejected", family="shopping", rule="numbers_match",
             title="Sauvage EDP 100ml")
        return build(mk(), TED_Q)
    plain = contextvars.copy_context().run(_plain)
    caplog.set_level(logging.INFO)
    caplog.clear()
    noted = contextvars.copy_context().run(_noted)
    f = [fields(r.getMessage()) for r in outcome_records(caplog)]
    assert len(f) == 2, f
    assert f[1]["miss"] == "rejected" and f[1]["miss_rule"] == "numbers_match", f[1]
    assert f[1]["rejected"] == "numbers_match=1", f[1]
    strip = lambda b: json.dumps({k: v for k, v in b.items() if k != "metadata"}, sort_keys=True, default=str)
    assert strip(noted) == strip(plain)


# --------------------------------------------------------------------------- the cache gate (A33)
def cache_rows():
    good = P(91.78, "Bleu de Chanel EDP 100ml", "store-b", "p/bleu-100")
    return [
        ("not_dict", "Bleu de Chanel EDP", None, False),
        ("no_title", "Bleu de Chanel EDP", dict(good, title=""), False),
        ("no_url", "Bleu de Chanel EDP", dict(good, url=None), False),
        ("listing_url", "Bleu de Chanel EDP", dict(good, url="https://store-b.example.com/search?q=bleu"), False),
        ("out_of_stock", "Bleu de Chanel EDP", dict(good, in_stock=False), False),
        ("identity", "Bleu de Chanel EDP", dict(good, title="Chanel Coco Mademoiselle EDP 100ml"), False),
        (None, "Bleu de Chanel EDP", good, True),
        (None, "", good, True),
    ]


@pytest.mark.parametrize("gate", [None, "false"])
def test_a33_pin_should_cache_truth_table(monkeypatch, gate):
    """A33 PIN: should_cache_price keeps today's values (exact gate ON and OFF)."""
    if gate:
        monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", gate)
    for _reason, name, price, exp in cache_rows():
        got = ps.should_cache_price(name, copy.deepcopy(price), FRAG)
        assert got is (True if gate else exp), (_reason, got)


def test_a33_red_refusal_reason(monkeypatch):
    """A33 RED: the log-only reason names the first failing check, None on a pass."""
    fn = need("price_cache_refusal_reason")
    for reason, name, price, _exp in cache_rows():
        assert fn(name, copy.deepcopy(price), FRAG) == reason, reason


def test_a33d_exact_gate_off_has_no_reason(monkeypatch):
    """A33d RED (ported from agent A's a33 exact-gate-OFF row): with ENABLE_EXACT_PRICE_GATE
    false should_cache_price allows every row, so the log-only reason is None for every row
    (never a PRICE_CACHE_SKIP reason the gate did not apply)."""
    fn = need("price_cache_refusal_reason")
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "false")
    for reason, name, price, _exp in cache_rows():
        assert ps.should_cache_price(name, copy.deepcopy(price), FRAG) is True, reason
        assert fn(name, copy.deepcopy(price), FRAG) is None, reason


# --------------------------------------------------------------------------- gender row (P2R-13)
def test_g1_rasasi_hawas_row(monkeypatch):
    """G1 RED: under the flag (and the X10 guard) a gender-free 'Rasasi Hawas' query
    rejects a 'for Her' listing and keeps a 'for Him' one."""
    monkeypatch.setenv("ENABLE_LISTING_MATCH_GUARD", "true")
    monkeypatch.setenv("ENABLE_VARIANT_DESCRIPTOR_AXES", "true")
    setflags(monkeypatch, flag="true")
    sel = lambda t: ps._selection_match("Rasasi Hawas", t, FRAG, candidate_brand="Rasasi")
    assert sel("Rasasi Hawas for Her Eau de Parfum 100ml") is False
    assert sel("Rasasi Hawas for Him Eau de Parfum 100ml") is True


def test_g2_rasasi_hawas_flag_off(monkeypatch):
    """G2 PIN: flag OFF the table is today's (the 'for Her' listing is not rejected by
    the gender-line rule)."""
    monkeypatch.setenv("ENABLE_LISTING_MATCH_GUARD", "true")
    monkeypatch.setenv("ENABLE_VARIANT_DESCRIPTOR_AXES", "true")
    setflags(monkeypatch, flag=None)
    assert ps._selection_match("Rasasi Hawas", "Rasasi Hawas for Her Eau de Parfum 100ml", FRAG,
                               candidate_brand="Rasasi") is True


# --------------------------------------------------------------------------- flag-OFF identity (A34)
def _norm_digest(body):
    from tests import test_s75_fanout_identity as fy
    raw = json.dumps(fy._normalize(body), sort_keys=True, default=str).encode("utf-8")
    return base64.b64encode(hashlib.sha256(raw).digest()).decode("ascii")


A34_BASE = {
    "sauv_bleu|0": "Tii1ODOhbNLkQnOs+TT8eqbbfNb20IHn7/FBP1xqSd8=",
    "sauv_bleu|true": "AeS0pQ0djdwrY0n1+HBd8Yl3u2kFdI73ZI4wew3GX9k=",
    "ted_dior|0": "xoPoWmM1TUnQVPKnqaNFK3gy/hX65LhguOkc42b0LrQ=",
    "ted_dior|true": "xoPoWmM1TUnQVPKnqaNFK3gy/hX65LhguOkc42b0LrQ=",
    "ysl_lveb|0": "ttBPBgmEHPUr+wMiySrDVFuB31pw6O1i6FiSopf6+HQ=",
    "ysl_lveb|true": "ttBPBgmEHPUr+wMiySrDVFuB31pw6O1i6FiSopf6+HQ=",
}  # filled from the base run (see the RED report); base64 sha256 of the normalized body


A34_PAIRS = {
    "ted_dior": (("Ted Baker M 30ml", TED_P), ("Dior Sauvage 100 ML Edp", DIOR_P), TED_Q, {}),
    "ysl_lveb": (("YSL Libre EDP", YSL_P), ("Lancome La Vie Est Belle EDP", LVEB_P), None, {}),
    "sauv_bleu": (("Sauvage EDP", SAUV_100), ("Bleu de Chanel EDP", BLEU_150), None,
                  {"Bleu de Chanel EDP": [cand(BLEU_100)]}),
}


@pytest.mark.parametrize("cap", [False, True], ids=["cap0", "cap1"])
@pytest.mark.parametrize("fix", FIXCELLS)
@pytest.mark.parametrize("pair", sorted(A34_PAIRS))
def test_a34_flag_off_identity_pure(monkeypatch, pair, fix, cap):
    """A34 PIN: flag OFF with the full configuration (token present or absent): the body
    digest equals the base record; no _p2_ key anywhere."""
    setflags(monkeypatch, flag=None, fix=fix)
    (na, pa), (nb, pb), q, c = A34_PAIRS[pair]

    def _go():
        b = getattr(ps, "price_size_cap_bind", None)
        if cap and b is not None:
            b(True)
        pd = [prod(na, pa), prod(nb, pb)]
        ps.reconcile_pair_fairness(pd, q or "%s vs %s" % (na, nb), FRAG, candidates_by_name=copy.deepcopy(c))
        return build(pd, q or "%s vs %s" % (na, nb))
    body = contextvars.copy_context().run(_go)
    key = "%s|%s" % (pair, fix or "0")
    assert underscore_or_p2(body, []) == []
    assert key in A34_BASE, "base record missing for %s" % key
    assert _norm_digest(body) == A34_BASE[key], key


# --------------------------------------------------------------------------- C-5 gap rows (added by the RED)
@pytest.mark.parametrize("fix", FIXCELLS)
def test_a17b_projection_keeps_the_size_annotation(monkeypatch, fix):
    """A17b RED (M12): with a price.size annotation the projected dict is flag OFF's own
    dict byte for byte (the size carried), not a fresh pending dict."""
    setflags(monkeypatch, fix=fix)
    dsz = dict(DIOR_P, size="100ml")
    pd_off = [prod("Ted Baker M 30ml", TED_P), prod("Dior Sauvage 100 ML Edp", dsz)]
    in_ctx(lambda: ps.reconcile_pair_fairness(pd_off, TED_Q, FRAG, candidates_by_name={}))
    assert pd_off[1]["price"].get("size") == "100ml"
    monkeypatch.setenv(FLAG, "true")
    pd_on = [prod("Ted Baker M 30ml", TED_P), prod("Dior Sauvage 100 ML Edp", dsz)]
    in_ctx(lambda: ps.reconcile_pair_fairness(pd_on, TED_Q, FRAG, candidates_by_name={}))
    assert json.dumps(pd_on[1]["price"]) == json.dumps(pd_off[1]["price"])
    assert isinstance(pd_on[1].get("_p2_shown_price"), dict)


def test_a42_kb_reselection_not_marked(monkeypatch):
    """A42 RED (M31, P2R-5): a side whose replaced price was KB-served is re-selected but
    never marked for the cache write; a live side is marked."""
    setflags(monkeypatch, flag="true", fix="true")
    kb = P(70.0, "Sauvage EDP 75ml", "store-a", "p/sv-75", _cached=True, _cache_source="kb")
    s, b = prod("Sauvage EDP", kb), prod("Bleu de Chanel EDP", BLEU_150)
    c = {"Sauvage EDP": [cand(P(80.0, "Sauvage EDP 100ml", "store-b", "p/sv-100"))],
         "Bleu de Chanel EDP": [cand(BLEU_100)]}
    _, snap = run_pair(s, b, None, c)
    assert snap[0]["price"].get("amount") == 80.0 and snap[1]["price"].get("amount") == 91.78, snap
    assert snap[0].get("_p2_reselected") is not True
    assert snap[1].get("_p2_reselected") is True


def test_a43_offsize_title_cut(monkeypatch):
    """A43 RED (P2R-19, M48): the offsize_listing title is cut to 120 characters."""
    setflags(monkeypatch, flag="true", fix="true")
    longt = "YSL Libre Eau de Parfum 90ml " + "Z" * 150
    y = prod("YSL Libre EDP", P(39.0, longt, "store-a", "p/libre-90"))
    body, _ = run_pair(y, prod("Lancome La Vie Est Belle EDP", LVEB_P), cap=False)
    off = ov(body)[0].get("offsize_listing") or {}
    assert off.get("title") == longt[:120], off


def test_a44_price_outcome_marketplace_field(monkeypatch, caplog):
    """A44 RED (P2R-7, M54): a shown price sold by an auction seller logs marketplace=1
    and the seller name (spaces folded, cut to 30)."""
    setflags(monkeypatch, flag=None, fix="true")
    caplog.set_level(logging.INFO)
    w = P(50.76, "Dior Sauvage EDP 100ml", sm="converted_usd")
    w.update(retailer="Whatnot", url="https://www.whatnot.com/listing/x")
    run_pair(prod("Dior Sauvage EDP", w), prod("Bleu de Chanel EDP", BLEU_100))
    f = [fields(r.getMessage()) for r in outcome_records(caplog)]
    assert f and f[0]["marketplace"] == "1" and f[0]["retailer"] == "Whatnot", f


@pytest.mark.parametrize("cap", CAPCELLS)
@pytest.mark.parametrize("fix", FIXCELLS)
def test_a45_untyped_side_without_typed_size_candidate(monkeypatch, fix, cap):
    """A45 RED (mutant M05 gap): Dior typed 100 vs an untyped Bleu at 150 ml with NO 100 ml
    candidate: Bleu is never pended for size by the flag; cap1 shows both, cap0 holds Bleu
    exactly as flag OFF plus its offsize_listing."""
    setflags(monkeypatch, fix=fix)
    d, b = prod("Dior Sauvage 100 ML Edp", DIOR_P), prod("Bleu de Chanel EDP", BLEU_150)
    q = "Dior Sauvage 100 ML Edp vs Bleu de Chanel EDP"
    off = flag_off_pend(d, b, q)
    assert shown(off[0]) and pending(off[1], "size_mismatch"), off
    monkeypatch.setenv(FLAG, "true")
    body, _ = run_pair(d, b, q, cap=cap)
    check_both_shown_cells(monkeypatch, cap, body, off, {1}, {1: BLEU_150}, {1: 150})


@pytest.mark.parametrize("fix", FIXCELLS)
def test_a46_largest_common_without_100(monkeypatch, fix):
    """A46 RED (mutant M08 gap): both reach 50 and 125 but not 100: the largest common
    size (125) is the target."""
    setflags(monkeypatch, flag="true", fix=fix)
    s = prod("Sauvage EDP", P(70.0, "Sauvage EDP 75ml", "store-a", "p/sv-75"))
    b = prod("Bleu de Chanel EDP", BLEU_150)
    c = {"Sauvage EDP": [cand(P(45.0, "Sauvage EDP 50ml", "store-b", "p/sv-50")),
                         cand(P(99.0, "Sauvage EDP 125ml", "store-b", "p/sv-125"))],
         "Bleu de Chanel EDP": [cand(P(55.0, "Bleu de Chanel EDP 50ml", "store-b", "p/bl-50")),
                                cand(P(110.0, "Bleu de Chanel EDP 125ml", "store-b", "p/bl-125"))]}
    body, _ = run_pair(s, b, None, c)
    assert [p.get("amount") for p in ov(body)] == [99.0, 110.0], ov(body)


def test_a47_numbers_match_fl_oz_two_digits(monkeypatch):
    """A47 RED (mutant M22 gap): a two-digit fl oz size number on the product side is
    ignored flag ON (it blocks today)."""
    setflags(monkeypatch, flag=None)
    assert ps.numbers_match("Fine Mist Body Spray 16.9 fl oz", "Fine Mist Body Spray 500ml") is False
    setflags(monkeypatch, flag="true")
    assert ps.numbers_match("Fine Mist Body Spray 16.9 fl oz", "Fine Mist Body Spray 500ml") is True
    assert ps.numbers_match("Fine Mist Body Spray 16.9 FL. OZ", "Fine Mist Body Spray") is True


def test_a33c_refusal_reason_order(monkeypatch):
    """A33c RED (mutant M35 gap): with neither a title nor a url the FIRST failing check
    of should_cache_price's order is named: no_title."""
    fn = need("price_cache_refusal_reason")
    p = P(91.78, "", "store-b", "p/bleu-100")
    p["url"] = None
    assert fn("Bleu de Chanel EDP", p, FRAG) == "no_title"
    assert ps.should_cache_price("Bleu de Chanel EDP", copy.deepcopy(p), FRAG) is False


@pytest.mark.parametrize("flag", [None, "true"])
@pytest.mark.parametrize("fix", FIXCELLS)
def test_a48_typed_size_makes_a_sizeless_listing_comparable(monkeypatch, fix, flag):
    """A48 PIN (mutant M42 gap, P2R-2): Ted typed 30 with a size-less listing vs a 30 ml
    partner is COMPARABLE through the typed size: no projection, both amounts shown in the
    token-absent cell, the price dim not limited_data, no offsize_listing (both flag values)."""
    setflags(monkeypatch, flag=flag, fix=fix)
    t = prod("Ted Baker M 30ml", P(9.5, "Ted Baker M Eau De Toilette", "store-a", "p/ted"))
    z = prod("Zara Red Vanilla", P(9.0, "Zara Red Vanilla EDT 30ml", "store-a", "p/z30"))
    body, _ = run_pair(t, z, "Ted Baker M 30ml vs Zara Red Vanilla", cap=False, strict=False)
    w = ov(body)
    assert shown(w[0]) and shown(w[1]), w
    assert all("offsize_listing" not in p for p in w)
    assert dims(body)["price"].get("caption_key") != "limited_data"
