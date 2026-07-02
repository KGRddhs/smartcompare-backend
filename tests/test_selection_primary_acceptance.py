"""R2 SELECTION-PRIMARY adapter acceptance (genuine-price KPI Wave B4).

strict_title_match tokenizes RAW (word-substring presence), so a CORRECT
retrieved row is rejected on pure alias/spacing variance the keystone
_selection_match already collapses via _identity_tokens_ps:
  * size spacing   "90ml" (query) vs "90 ml" (live perfumesclub title)
  * brand alias    "YSL" (query) vs "Yves Saint Laurent" (spelled title,
                   via candidate_brand + _BRAND_ALIAS_GROUPS)
  * concentration  "Eau de Parfum" vs "EDP" (strict ALSO collapses this one)
recon_cascade 2026-07-02 (R2): the live 48.000-BHD in-stock exact SKU
"YSL Black Opium (W) EDP 90 ml" @ theperfumesclub was retrieved by the R1
ladder and then thrown away by the strict pre-gate in every adapter chain.

THE CHANGE (flag ENABLE_ADAPTER_SELECTION_PRIMARY, default ON, and ONLY
active while ENABLE_EXACT_PRICE_GATE is on): in the 5 adapter chains that run
_selection_match ALONGSIDE strict (woo / magento _best_match / salla /
rest_json / occ), a strict PASS stays the fast-accept path and a strict FAIL
falls through to the remaining chain — the candidate must still pass
numbers_match AND NOT variant_mismatch AND NOT counterfeit AND NOT
accessory-mismatch AND _selection_match (plus each chain's existing overlap /
stock gates). The bolo-sitemap strict gate (price_service.py ~:7095) has NO
_selection_match alongside and is deliberately NOT touched (the PR#13
lesson — strict is the only protection there).

Both directions pinned per [[feedback-coverage-driven-review]]:
  ACCEPT — the recon-proven exact SKU + concentration-abbrev + brand-omitting
           candidate_brand rows;
  REJECT — flankers (EDP Extreme / Le Parfum), wrong brand, accessory,
           counterfeit ("Inspired by" luxodor class), and the 4 truth-
           modernization titles that fail _selection_match ITSELF (strict=True,
           selection=False — selection-primary must NOT unlock those; they are
           the Wave-B matcher / Wave-2 VariantDescriptor scope pinned xfail in
           tests/test_kpi_truth_modernization.py — flip together).
  FLAGS  — sibling-flag OFF and exact-gate OFF each restore the exact
           pre-change hard strict gate (no new flag-OFF acceptance).
"""
import asyncio
import json

import pytest

import app.services.woocommerce_service as woo
import app.services.salla_service as salla
import app.services.magento_graphql_service as mg
import app.services.rest_json_service as rj
import app.services.occ_service as occ
from app.services.price_service import (
    adapter_selection_primary_enabled,
    build_adapter_search_terms,
)


def _run(coro):
    return asyncio.run(coro)


@pytest.fixture(autouse=True)
def _flags(monkeypatch):
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "true")
    monkeypatch.delenv("ENABLE_ADAPTER_SELECTION_PRIMARY", raising=False)
    monkeypatch.delenv("ENABLE_ADAPTER_QUERY_LADDER", raising=False)
    monkeypatch.setattr(woo, "ENABLE_PAGE_SCRAPE", True, raising=False)


# The kpi-frag-001 TRUTH query (data/usable_exact_genuine_truth.json) — the
# form prod actually sends. NB the SPELLED-brand query form ("Yves Saint
# Laurent Black Opium ...") still rejects at the no-candidate_brand chains:
# _identity_tokens_ps folds the ysl<->spelled alias ONLY via candidate_brand,
# and Woo Store API rows carry no brand field — a documented fail-closed
# residual (Wave-2 VariantDescriptor scope), NOT pinned as accept here.
Q_KPI = "YSL Black Opium Eau de Parfum 90ml"

T_EXACT = "YSL Black Opium (W) EDP 90 ml"           # live row, 48.000 BHD in-stock
T_EXTREME = "YSL Black Opium (W) EDP Extreme 90ml"  # flanker sibling (same price!)
T_LEPARFUM = "YSL Black Opium (W) Le Parfum 90 ml"  # flanker sibling
T_WRONGBRAND = "Lancome La Vie Est Belle (W) EDP 90 ml"


def _woo_row(name, slug="row", price="48000", cc="BHD", minor=3):
    return {
        "name": name,
        "permalink": f"https://theperfumesclub.com/product/{slug}/",
        "is_in_stock": True,
        "prices": {"price": price, "currency_code": cc,
                   "currency_minor_unit": minor},
    }


WOO_ROWS = [
    _woo_row(T_EXTREME, "edp-extreme"),
    _woo_row(T_EXACT, "edp-90"),
    _woo_row(T_LEPARFUM, "le-parfum"),
]


# ---------------------------------------------------------------------------
# flag helper semantics
# ---------------------------------------------------------------------------

def test_flag_default_on():
    assert adapter_selection_primary_enabled() is True


def test_flag_off_values(monkeypatch):
    for v in ("false", "0", "no", "off", ""):
        monkeypatch.setenv("ENABLE_ADAPTER_SELECTION_PRIMARY", v)
        assert adapter_selection_primary_enabled() is False


def test_flag_hard_requires_exact_gate(monkeypatch):
    """_selection_match is a no-op True when ENABLE_EXACT_PRICE_GATE is off —
    selection-primary MUST disable itself then, or the rollback state would
    accept candidates gated only by numbers/variant/counterfeit/accessory."""
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "false")
    monkeypatch.setenv("ENABLE_ADAPTER_SELECTION_PRIMARY", "true")
    assert adapter_selection_primary_enabled() is False


# ---------------------------------------------------------------------------
# WOO — the recon-proven case (theperfumesclub, kpi-frag-001)
# ---------------------------------------------------------------------------

def test_woo_accepts_recon_exact_sku_over_flankers():
    """The exact SKU is picked out of the flanker siblings (same price, so the
    selector cannot be leaning on amount)."""
    res = woo._match_woo_product(WOO_ROWS, Q_KPI, "BHD",
                                 resolved_category="fragrances")
    assert res is not None
    assert res["title"] == T_EXACT
    assert res["amount"] == pytest.approx(48.0)
    assert res["currency"] == "BHD"
    assert res["source_method"] == "woo_store_api"
    assert res["in_stock"] is True
    assert res["url"].endswith("/edp-90/")


def test_woo_strict_pass_fast_accept_path_unchanged():
    """The strict=True query form accepted BEFORE the change keeps working."""
    res = woo._match_woo_product(WOO_ROWS, "YSL Black Opium EDP 90 ml", "BHD",
                                 resolved_category="fragrances")
    assert res is not None
    assert res["title"] == T_EXACT


def test_woo_flankers_only_rejected():
    res = woo._match_woo_product(
        [_woo_row(T_EXTREME, "edp-extreme"), _woo_row(T_LEPARFUM, "le-parfum")],
        Q_KPI, "BHD", resolved_category="fragrances")
    assert res is None


def test_woo_wrong_brand_rejected():
    res = woo._match_woo_product([_woo_row(T_WRONGBRAND, "lvb")], Q_KPI, "BHD",
                                 resolved_category="fragrances")
    assert res is None


def test_woo_accessory_rejected():
    res = woo._match_woo_product(
        [_woo_row("AirPods Pro 2 Case", "case", price="4900")],
        "Apple AirPods Pro 2", "BHD", resolved_category="electronics")
    assert res is None


def test_woo_counterfeit_rejected():
    """The luxodor class from the live Google evidence — 'Inspired by ...'."""
    res = woo._match_woo_product(
        [_woo_row("Inspired by Tom Ford Oud Wood Eau de Parfum 100ml", "insp")],
        "Tom Ford Oud Wood Eau de Parfum 100ml", "BHD",
        resolved_category="fragrances")
    assert res is None


def test_woo_sibling_flag_off_restores_strict_hard_gate(monkeypatch):
    monkeypatch.setenv("ENABLE_ADAPTER_SELECTION_PRIMARY", "false")
    res = woo._match_woo_product(WOO_ROWS, Q_KPI, "BHD",
                                 resolved_category="fragrances")
    assert res is None


def test_woo_exact_gate_off_alias_row_stays_rejected(monkeypatch):
    """Rollback coherence: with the exact gate OFF, selection-primary disables
    itself, so strict stays hard and the alias-variant row alone -> None — B4
    must add ZERO new flag-OFF acceptance."""
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "false")
    res = woo._match_woo_product([_woo_row(T_EXACT, "edp-90")], Q_KPI, "BHD",
                                 resolved_category="fragrances")
    assert res is None


def test_woo_exact_gate_off_is_the_prechange_chain(monkeypatch):
    """Byte-identical pre-change rollback behaviour, PINNED: with the exact
    gate OFF, _selection_match is a no-op True, so the strict-PASSING flanker
    (T_EXTREME — strict=True because the query words are a raw subset) is what
    the b207bfa chain accepted for this row set. That leak class is the
    DOCUMENTED, pre-existing rollback trade (PR#9 flag contract) — this pin
    proves B4 changed nothing flag-OFF (it would be T_EXACT if selection-
    primary leaked through)."""
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "false")
    res = woo._match_woo_product(WOO_ROWS, Q_KPI, "BHD",
                                 resolved_category="fragrances")
    assert res is not None
    assert res["title"] == T_EXTREME


def test_woo_exact_gate_off_strict_pass_still_accepts(monkeypatch):
    """...while a strict-passing exact row keeps the legacy accept (flag-OFF
    is the pre-change chain, not a shutdown)."""
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "false")
    res = woo._match_woo_product([_woo_row(T_EXACT, "edp-90")],
                                 "YSL Black Opium EDP 90 ml", "BHD",
                                 resolved_category="fragrances")
    assert res is not None
    assert res["title"] == T_EXACT


# ---------------------------------------------------------------------------
# WOO end-to-end — R1 retrieval ladder + R2 selection-primary compose
# ---------------------------------------------------------------------------

class _FakeResp:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code
        self.text = json.dumps(payload)

    def json(self):
        return self._payload


def test_woo_e2e_ladder_retrieves_and_selection_primary_accepts(monkeypatch):
    """The full kpi-frag-001 recovery: full-name search -> 0 rows, core-term
    'Black Opium' -> the real perfumesclub rows, exact SKU accepted."""
    assert build_adapter_search_terms(Q_KPI, "fragrances") == [Q_KPI, "Black Opium"]
    calls = []

    def fake_do_get(url, params, headers):
        term = (params or {}).get("search")
        calls.append(term)
        return _FakeResp({Q_KPI: [], "Black Opium": WOO_ROWS}.get(term, []))

    monkeypatch.setattr(woo, "_do_get", fake_do_get)
    res = _run(woo.fetch_woocommerce_store_api_price(
        "theperfumesclub.com", Q_KPI, resolved_category="fragrances"))
    assert calls == [Q_KPI, "Black Opium"]
    assert res is not None
    assert res["title"] == T_EXACT
    assert res["amount"] == pytest.approx(48.0)
    assert res["source_method"] == "woo_store_api"
    assert res["retailer"] == "theperfumesclub.com"


# ---------------------------------------------------------------------------
# MAGENTO _best_match
# ---------------------------------------------------------------------------

def _mg_node(name, brand="", value=39.38):
    return {"name": name, "value": value, "currency": "BHD",
            "url_key": "x", "brand": brand}


def test_magento_accepts_concentration_size_alias():
    """kpi-frag-004 shape: 'EDP 100 ML' vs the 'Eau de Parfum 100ml' query —
    strict fails ONLY on the '100ml' vs '100 ML' spacing."""
    node = _mg_node("Lancome La Vie Est Belle EDP 100 ML")
    best = mg._best_match([node], "Lancome La Vie Est Belle Eau de Parfum 100ml",
                          "fragrances")
    assert best is not None
    assert best["name"] == "Lancome La Vie Est Belle EDP 100 ML"


def test_magento_accepts_brand_omitting_title_via_candidate_brand():
    """The klinq class (A4's sibling): a brand-omitting title whose node
    carries the spelled brand — the ysl<->spelled alias folds ONLY inside
    _selection_match(candidate_brand=), so strict cannot pass it."""
    node = _mg_node("Black Opium Eau De Parfum 90 ml", brand="Yves Saint Laurent")
    best = mg._best_match([node], Q_KPI, "fragrances")
    assert best is not None
    assert best["name"] == "Black Opium Eau De Parfum 90 ml"


def test_magento_rejects_flanker():
    node = _mg_node("Black Opium EDP Extreme 90 ml", brand="Yves Saint Laurent")
    assert mg._best_match([node], Q_KPI, "fragrances") is None


def test_magento_sibling_flag_off_restores_strict_hard_gate(monkeypatch):
    monkeypatch.setenv("ENABLE_ADAPTER_SELECTION_PRIMARY", "false")
    node = _mg_node("Lancome La Vie Est Belle EDP 100 ML")
    assert mg._best_match([node], "Lancome La Vie Est Belle Eau de Parfum 100ml",
                          "fragrances") is None


# ---------------------------------------------------------------------------
# SALLA _select_candidate
# ---------------------------------------------------------------------------

def test_salla_accepts_exact_and_skips_flanker():
    items = [{"name": T_EXTREME, "price": 48.0}, {"name": T_EXACT, "price": 48.0}]
    got = salla._select_candidate(items, Q_KPI, "fragrances")
    assert got is not None
    assert got["name"] == T_EXACT


def test_salla_flanker_only_rejected():
    assert salla._select_candidate([{"name": T_EXTREME, "price": 48.0}],
                                   Q_KPI, "fragrances") is None


def test_salla_sibling_flag_off_restores_strict_hard_gate(monkeypatch):
    monkeypatch.setenv("ENABLE_ADAPTER_SELECTION_PRIMARY", "false")
    assert salla._select_candidate([{"name": T_EXACT, "price": 48.0}],
                                   Q_KPI, "fragrances") is None


# ---------------------------------------------------------------------------
# REST_JSON _title_matches
# ---------------------------------------------------------------------------

def test_rest_json_accepts_alias_variant_title():
    assert rj._title_matches(Q_KPI, T_EXACT, "fragrances") is True


def test_rest_json_rejects_flanker():
    assert rj._title_matches(Q_KPI, T_EXTREME, "fragrances") is False


def test_rest_json_sibling_flag_off_restores_strict_hard_gate(monkeypatch):
    monkeypatch.setenv("ENABLE_ADAPTER_SELECTION_PRIMARY", "false")
    assert rj._title_matches(Q_KPI, T_EXACT, "fragrances") is False


# ---------------------------------------------------------------------------
# OCC _select_product
# ---------------------------------------------------------------------------

def _occ_node(name, manufacturer="", value=39.38, ccy="BHD", stock="inStock"):
    return {"name": name, "manufacturer": manufacturer,
            "price": {"value": value, "currencyIso": ccy},
            "stock": {"stockLevelStatus": stock}, "url": "/p/x"}


def test_occ_accepts_brand_omitting_bhd_node():
    got = occ._select_product(
        {"products": [_occ_node("Black Opium Eau De Parfum 90 ml",
                                "Yves Saint Laurent")]},
        Q_KPI, "fragrances")
    assert got is not None
    assert got["name"] == "Black Opium Eau De Parfum 90 ml"


def test_occ_rejects_flanker():
    got = occ._select_product(
        {"products": [_occ_node("Black Opium EDP Extreme 90 ml",
                                "Yves Saint Laurent")]},
        Q_KPI, "fragrances")
    assert got is None


def test_occ_brand_omitted_model_line_accepted_without_manufacturer():
    """The BH model-line listing class ("iPad Air M2 128GB", no "Apple") is now
    recovered even when the OCC node carries NO manufacturer field — the
    keystone treats a one-sided MANUFACTURER word as padding. (This updates
    the item-2 pin in tests/test_kpi_session_fixes.py; the legacy reject is
    preserved there under the sibling flag OFF.)"""
    got = occ._select_product(
        {"products": [_occ_node("iPad Air M2 11-inch 128GB Blue")]},
        "Apple iPad Air M2 128GB", "electronics")
    assert got is not None
    assert got["name"] == "iPad Air M2 11-inch 128GB Blue"


@pytest.mark.parametrize("title", [
    "Samsung Galaxy Tab A9 128GB",     # wrong brand+model
    "Tablet Air M2 128GB Android",     # knockoff-generic (no 'ipad' token)
    "iPad Air M2 128GB Case",          # accessory
    "iPad Air M2 128GB Renewed",       # condition axis
    "iPad Air M4 11-inch 128GB Blue",  # successor chip
    "iPad Air M2 11-inch 256GB Blue",  # wrong storage
    "iPad Pro M2 11-inch 128GB",       # pro flanker
])
def test_occ_brand_omitted_adversarial_directions_still_reject(title):
    """Both-directions sweep of the brand-omitted acceptance above — every
    adversarial neighbour of the exact SKU stays rejected (probed through
    _select_product 2026-07-02)."""
    got = occ._select_product(
        {"products": [_occ_node(title)]},
        "Apple iPad Air M2 128GB", "electronics")
    assert got is None


def test_occ_sibling_flag_off_restores_strict_hard_gate(monkeypatch):
    monkeypatch.setenv("ENABLE_ADAPTER_SELECTION_PRIMARY", "false")
    got = occ._select_product(
        {"products": [_occ_node("Black Opium Eau De Parfum 90 ml",
                                "Yves Saint Laurent")]},
        Q_KPI, "fragrances")
    assert got is None


# ---------------------------------------------------------------------------
# The 4 truth-modernization titles — selection-primary must NOT unlock them.
# They fail _selection_match ITSELF (strict=True, selection=False: variant-add
# on 'Light' / 'Icyblue'+'AI' / '(2025)' / '13 Inch') — the exact class the
# strict=True xfails in tests/test_kpi_truth_modernization.py pin at matcher
# level. Adapter-chain REJECT pinned here so the strict demotion is proven not
# to widen the variant-add direction; when the matcher work lands, flip these
# WITH the xfails.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("query,title,manufacturer", [
    ("Nintendo Switch 2",
     "Nintendo Switch 2, Light Blue and Light Red", ""),
    ("Samsung Galaxy S25 256GB",
     "Samsung Galaxy S25 5G 256GB 12GB RAM Icyblue AI Smartphone Middle East Version",
     ""),
    ("Apple iPad Air 11-inch M3 128GB",
     "iPad Air 11-inch M3 (2025) Wi-Fi 128GB - Space Grey Middle East Version with FaceTime",
     "Apple"),
    ("MacBook Air 13 M5 512GB",
     "APPLE MacBook Air, M5, 16GB, 512GB SSD, 13 Inch IPS, 8 Core GPU, Silver",
     "Apple"),
])
def test_selection_level_rejections_stay_rejected(query, title, manufacturer):
    got = occ._select_product(
        {"products": [_occ_node(title, manufacturer, 199.9)]},
        query, "electronics")
    assert got is None


# ===========================================================================
# Wave B-FIX BF1 — the WRONG-BRAND FENCE on the strict-FAIL fallthrough
# (coverage leak sweep L1 CRITICAL + L2 HIGH, waveb_leak.json) and the unbxd
# selection-primary wiring (over-rejection sweep OR-1 partial).
#
# The B4 strict demotion dropped strict's brand requirement, and for a
# PADDING-BRAND query ("Adidas"/"Puma" are _FASHION_PADDING; manufacturers
# are _ELECTRONICS_PADDING) _selection_match strips the query's brand from
# q_core — so a same-model-word CROSS-BRAND row sailed through the
# fallthrough on every demoted chain. selection_primary_admits now requires
# BRAND EVIDENCE on the fallthrough:
#   (a) a non-empty candidate_brand must alias-equal a query token
#       (a stated CONTRADICTING brand hard-rejects);
#   (b) with NO candidate-brand signal, a FASHION padding-brand query
#       requires its brand token folded in the title (electronics keeps the
#       B4 brand-omitted unlock — model-line tokens are brand-unique, the
#       leak sweep probed that space rejected).
# Both directions pinned per [[feedback-coverage-driven-review]].
# ===========================================================================

import app.services.unbxd_service as ub
from app.services.price_service import selection_primary_admits


# --- L1 (CRITICAL): brand-stamped chains reject the cross-brand row ---------

_L1_CASES = [
    # the two sweep repros (probe_wrong_brand_class.py, reproduced 2026-07-02)
    ("Adidas Superstar White", "Golden Goose Superstar White Sneakers", "Golden Goose"),
    ("Puma Suede Classic", "Vans Suede Classic Sneakers", "Vans"),
]


@pytest.mark.parametrize("query,title,brand", _L1_CASES)
def test_fence_magento_rejects_wrong_brand_stamped_fashion_row(query, title, brand):
    node = _mg_node(title, brand=brand, value=45.0)
    assert mg._best_match([node], query, "fashion") is None


@pytest.mark.parametrize("query,title,brand", _L1_CASES)
def test_fence_occ_rejects_wrong_brand_stamped_fashion_row(query, title, brand):
    got = occ._select_product(
        {"products": [_occ_node(title, brand, 45.0)]}, query, "fashion")
    assert got is None


def test_fence_wrong_brand_stamp_rejects_at_admits_level_electronics():
    """(a) generalizes to electronics: a stated CONTRADICTING brand is
    definitive wrong-brand evidence (the chain also rejects via residual
    model tokens — this pins the fence as defense-in-depth)."""
    assert selection_primary_admits(
        "Apple Watch Ultra 2", "Galaxy Watch Ultra LTE",
        candidate_brand="Samsung", category="electronics") is False


# --- L2 (HIGH): brandless chains reject the brand-omitted cross-brand row ---

L2_Q = "Adidas Superstar White"
L2_T = "Superstar White Sneakers"  # a Golden Goose row listed brand-omitted


def test_fence_woo_brandless_wrong_brand_fashion_row_rejected():
    rows = [_woo_row(L2_T, "superstar", price="45000")]
    assert woo._match_woo_product(rows, L2_Q, "BHD",
                                  resolved_category="fashion") is None


def test_fence_salla_brandless_wrong_brand_fashion_row_rejected():
    assert salla._select_candidate([{"name": L2_T, "price": 45.0}],
                                   L2_Q, "fashion") is None


def test_fence_rest_json_brandless_wrong_brand_fashion_row_rejected():
    assert rj._title_matches(L2_Q, L2_T, "fashion") is False


# --- BOTH sanctioned unlocks still pass (the fence's own over-rejection is
#     the next blind spot — pinned) ------------------------------------------

def test_fence_correct_brand_stamp_brand_omitted_fashion_row_still_accepted():
    """A brand-OMITTED fashion title whose node carries the MATCHING brand
    (the klinq-class stamp, fashion edition) keeps the B4 unlock."""
    node = _mg_node("Superstar White Sneakers", brand="Adidas", value=45.0)
    best = mg._best_match([node], "Adidas Superstar White", "fashion")
    assert best is not None
    assert best["name"] == "Superstar White Sneakers"


def test_fence_admits_fashion_brandless_title_carrying_the_brand():
    """(b) sanctioned unlock: a brandless-chain fashion row whose TITLE carries
    the query's brand keeps the fallthrough (spaced-unit/alias titles that
    strict alone rejects)."""
    assert selection_primary_admits(
        "Adidas Superstar White", "adidas Superstar Cloud White Sneakers EU 42",
        category="fashion") is True


def test_fence_admits_electronics_brand_omitted_brandless_row():
    """(b) electronics keeps the B4 brand-omitted unlock (BH model-line
    listings: 'iPad Air M2 128GB', no 'Apple') — the sweep probed the
    cross-brand electronics space naturally rejected by model tokens."""
    assert selection_primary_admits(
        "Apple iPad Air M2 128GB", "iPad Air M2 11-inch 128GB Blue",
        category="electronics") is True


def test_fence_admits_klinq_alias_stamp_unaffected():
    """The klinq unlock (brand-omitted title + spelled-brand stamp) is
    untouched: fragrance brand words are NOT padding, so the fence is inert
    ('YSL' query vs 'Yves Saint Laurent' stamp still admitted)."""
    assert selection_primary_admits(
        Q_KPI, "Black Opium Eau De Parfum 90 ml",
        candidate_brand="Yves Saint Laurent", category="fragrances") is True


def test_fence_admits_non_padding_brand_query_untouched():
    """A query whose brand is NOT padding-strippable passes the fence — the
    keystone's own subset check keeps that brand required downstream."""
    assert selection_primary_admits(
        "Lattafa Khamrah Eau de Parfum 100ml", "Khamrah EDP 100 ml",
        category="fragrances") is True


def test_fence_pure_digit_brand_label_is_no_signal_not_contradiction():
    """A numeric option-id leaking into the brand field ('743') asserts no
    brand — it must fall to the brandless path (electronics admit), never
    hard-reject as a contradiction."""
    assert selection_primary_admits(
        "Apple iPad Air M2 128GB", "iPad Air M2 11-inch 128GB Blue",
        candidate_brand="743", category="electronics") is True


def test_fence_flag_off_admits_nothing(monkeypatch):
    monkeypatch.setenv("ENABLE_ADAPTER_SELECTION_PRIMARY", "false")
    assert selection_primary_admits(
        "Adidas Superstar White", "adidas Superstar Cloud White Sneakers",
        category="fashion") is False


# --- OR-1 (partial): unbxd wired into the SAME selection-primary + fence ----

EXTRA_Q = "Samsung Galaxy S25 Ultra 256GB"
EXTRA_TITLE = "SAMSUNG Galaxy S25 Ultra, 5G, 256 GB, Titanium Black"  # real extra.com row


def _ub_product(title, price=358.0, in_stock="true", url="https://www.extra.com/en-bh/p/123"):
    return {"title": title, "sellingPrice": price, "inStockFlag": in_stock,
            "productUrl": url}


def test_unbxd_selection_primary_accepts_extra_spaced_unit_title():
    """The real extra.com S25 Ultra title fails strict ONLY on the spaced
    '256 GB' (query '256GB' not a raw substring) while _selection_match
    accepts — the exact class the B4 demotion exists for (OR-1)."""
    got = ub._match_unbxd_product([_ub_product(EXTRA_TITLE)], EXTRA_Q,
                                  resolved_category="electronics")
    assert got is not None
    assert got["title"] == EXTRA_TITLE


def test_unbxd_e2e_ships_local_bhd_for_spaced_unit_title(monkeypatch):
    async def fake_search(store, query):
        return [_ub_product(EXTRA_TITLE)]

    monkeypatch.setattr(ub, "_unbxd_search", fake_search)
    monkeypatch.setattr(ub, "is_circuit_closed", lambda *_a, **_k: True)
    res = _run(ub.fetch_unbxd_price("extra.com", EXTRA_Q,
                                    resolved_category="electronics"))
    assert res is not None
    assert res["amount"] == pytest.approx(358.0)
    assert res["source_method"] == "local_bhd"
    assert res["title"] == EXTRA_TITLE
    assert res["in_stock"] is True


@pytest.mark.parametrize("title", [
    # variant flanker: base query must not take the Ultra's sibling
    "SAMSUNG Galaxy S25 Plus, 5G, 256 GB, Navy",
    # wrong storage (axis)
    "SAMSUNG Galaxy S25 Ultra, 5G, 512 GB, Titanium Black",
    # wrong brand+model (electronics natural fence via model tokens)
    "APPLE iPhone 17 Pro, 256 GB, Silver",
    # accessory
    "SAMSUNG Galaxy S25 Ultra Clear Case",
    # the pinned truth-modernization xfail class stays REJECTED at unbxd too
    # (selection-level '13 Inch' added-axis — flip with the matcher xfails)
    ])
def test_unbxd_selection_primary_wrong_skus_still_reject(title):
    got = ub._match_unbxd_product([_ub_product(title)], EXTRA_Q,
                                  resolved_category="electronics")
    assert got is None


def test_unbxd_macbook_added_inch_axis_stays_rejected():
    """OR-2's class: '13 Inch' added-axis rejects at _selection_match ITSELF —
    wiring selection-primary must NOT unlock it (flip with the
    test_kpi_truth_modernization xfails when the matcher work lands)."""
    got = ub._match_unbxd_product(
        [_ub_product("APPLE MacBook Air, M5, 16GB, 512GB SSD, 13 Inch IPS, 8 Core GPU, Silver",
                     price=499.9)],
        "MacBook Air 13 M5 512GB", resolved_category="electronics")
    assert got is None


def test_unbxd_sibling_flag_off_restores_strict_hard_gate(monkeypatch):
    monkeypatch.setenv("ENABLE_ADAPTER_SELECTION_PRIMARY", "false")
    got = ub._match_unbxd_product([_ub_product(EXTRA_TITLE)], EXTRA_Q,
                                  resolved_category="electronics")
    assert got is None


def test_unbxd_exact_gate_off_restores_strict_hard_gate(monkeypatch):
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "false")
    monkeypatch.setenv("ENABLE_ADAPTER_SELECTION_PRIMARY", "true")
    got = ub._match_unbxd_product([_ub_product(EXTRA_TITLE)], EXTRA_Q,
                                  resolved_category="electronics")
    assert got is None
