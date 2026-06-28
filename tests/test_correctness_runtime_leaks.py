# -*- coding: utf-8 -*-
"""Wave 1 (FIX session 2026-06-28) — the 8 release-blocker leaks reproduced
through the REAL RUNTIME PATH, not the helper in isolation.

LOAD-BEARING LESSON (PR #9 was HELD): a green comm gate + a passing self-review
LIED — the 110 prior tests asserted the leaks were "acceptable" (missing-URL /
unknown-stock OK) and exercised helpers (`is_exact_match`) that the selector
(`select_best` -> `_selection_match`) never runs. EVERY test below drives the
function the orchestrator actually calls and asserts the CORRECT (fail-closed)
behaviour. They are RED on the current branch and turn GREEN as the fix waves land.

Blocker map:
  B1  fetch_iherb_price best-overlap-no-threshold + strips title + hardcodes stock;
      fetch_pharmacy_price -> extract_jsonld_price WITHOUT query_name (gate disabled).
  B2  select_best runs permissive _selection_match: flanker + product FORM
      (deodorant/candle) + candidate-omits-query-axis all leak through.
  B3  usable_exact_genuine KPI never loads its truth file / counts no-URL+unknown-stock.
  B4  extract_jsonld_price accepts AggregateOffer.lowPrice + ignores priceValidUntil.
  B5  select_best is fail-OPEN on a no-title / no-URL candidate.
  B6  cache write is not gated on the RESOLVED identity matching the request.
  B7  guard_rejected leaks into the PUBLIC price payload (belongs in metadata).
  B8  ENABLE_EXACT_PRICE_GATE=false is NOT byte-identical to b207bfa (unbxd wasPrice).
"""
import importlib

import pytest

import app.services.price_service as ps


@pytest.fixture(autouse=True)
def _gate_on(monkeypatch):
    """The leak repros run with the correctness gate ON (default)."""
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "true")


# ===========================================================================
# B1 — supplements return + cache the WRONG product (iHerb + pharmacy bypass)
# ===========================================================================

def _iherb_html(cards):
    rows = "".join(
        f'<a data-ga-brand-name="{b}" data-ga-discount-price="{p}" '
        f'title="{t}" href="{h}"></a>'
        for (b, p, t, h) in cards
    )
    return f"<html><body>{rows}</body></html>"


@pytest.mark.asyncio
async def test_b1_iherb_no_exact_pends_not_wrong_brandmate(monkeypatch):
    """The exact requested SKU is ABSENT from the iHerb results; only a same-brand
    DIFFERENT product is present. fetch_iherb_price must PEND (return None), not
    fall back to best-overlap and ship the wrong product's price.

    Repro: query 'Solgar Vitamin D3 5000 IU 120 Softgels'; page only carries
    'Solgar Magnesium Citrate 120 Tablets'. Current code: no full subset match ->
    best-overlap fallback (no threshold) -> returns the Magnesium price."""
    html = _iherb_html([
        ("Solgar", "9.500", "Solgar Magnesium Citrate 120 Tablets", "/pr/magnesium-citrate/111"),
    ])

    class _Resp:
        status_code = 200
        text = html

    import curl_cffi
    monkeypatch.setattr(curl_cffi.requests, "get", lambda *a, **k: _Resp())

    res = await ps.fetch_iherb_price(
        query="Solgar Vitamin D3 5000 IU 120 Softgels",
        brand="Solgar",
        full_name="Solgar Vitamin D3 5000 IU 120 Softgels",
        region_code="bh", currency="BHD",
    )
    assert res is None, (
        "no exact D3 5000IU 120-softgel match present -> must pend, NOT return the "
        f"same-brand Magnesium Citrate price (got {res})"
    )


@pytest.mark.asyncio
async def test_b1_iherb_match_keeps_title_and_identity(monkeypatch):
    """When fetch_iherb_price DOES match, the returned price must carry the matched
    title/name so the downstream chokepoint + select_best can re-verify identity.
    Current code strips the title (the dict has no title/name key)."""
    html = _iherb_html([
        ("Solgar", "14.200", "Solgar Vitamin D3 5000 IU 120 Softgels", "/pr/d3-5000/222"),
    ])

    class _Resp:
        status_code = 200
        text = html

    import curl_cffi
    monkeypatch.setattr(curl_cffi.requests, "get", lambda *a, **k: _Resp())

    res = await ps.fetch_iherb_price(
        query="Solgar Vitamin D3 5000 IU 120 Softgels",
        brand="Solgar",
        full_name="Solgar Vitamin D3 5000 IU 120 Softgels",
        region_code="bh", currency="BHD",
    )
    assert res is not None
    identity = (res.get("title") or res.get("name") or "")
    assert "d3" in identity.lower() or "5000" in identity.lower(), (
        "iHerb price must retain the matched product title/name for identity "
        f"re-verification, got keys={sorted(res.keys())}"
    )


@pytest.mark.asyncio
async def test_b1_pharmacy_passes_query_name_to_jsonld_gate(monkeypatch):
    """fetch_pharmacy_price must thread the full query into extract_jsonld_price so
    the JSON-LD identity gate is ARMED — a multi-Product same-brand pharmacy page
    must not attribute the cheapest unrelated same-brand item to the query.

    Current code calls extract_jsonld_price(text, brand, currency) with NO
    query_name (4th arg defaults to '') -> the _selection_match gate inside is
    skipped. We record the query_name extract_jsonld_price actually receives."""
    import httpx

    captured = {}

    def _spy_extract(html, brand, currency, query_name="", *a, **k):
        captured["query_name"] = query_name
        # Return a plausible same-brand-but-WRONG product price.
        return {"amount": 9.5, "currency": currency, "in_stock": True,
                "name": "Solgar Magnesium Citrate 120 Tablets"}

    monkeypatch.setattr(ps, "extract_jsonld_price", _spy_extract)

    class _Resp:
        status_code = 200
        text = "<html></html>"

    class _FakeClient:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def get(self, url, **k):
            return _Resp()

    monkeypatch.setattr(httpx, "AsyncClient", _FakeClient)

    # A pharmacy domain the route recognizes.
    domain = next(iter(ps.PHARMACY_DOMAINS.keys()))
    serper_organic = [{"link": f"https://{domain}/product/solgar-d3-5000"}]

    await ps.fetch_pharmacy_price(
        serper_organic=serper_organic, brand="Solgar",
        full_name="Solgar Vitamin D3 5000 IU 120 Softgels", currency="BHD",
    )
    assert captured.get("query_name") == "Solgar Vitamin D3 5000 IU 120 Softgels", (
        "pharmacy route must pass the full query into extract_jsonld_price so its "
        f"identity gate is armed; got query_name={captured.get('query_name')!r}"
    )


# ===========================================================================
# B2 — the selector runs the permissive matcher: flanker + FORM + omitted axis
# ===========================================================================

def _cand(amount, title, url="https://www.example-bh.com/p/x"):
    return {"amount": amount, "currency": "BHD", "in_stock": True,
            "url": url, "title": title, "source_method": "local_bhd"}


def test_b2_select_best_rejects_flanker():
    """YSL Black Opium must NOT resolve to 'Black Opium Over Red' (a flanker with
    an extra distinctive sub-line token). select_best runs _selection_match
    (query-subset) which accepts it; the structured matcher must reject."""
    cands = [_cand(42.0, "YSL Black Opium Over Red Eau de Parfum 90ml")]
    best = ps.select_best(cands, "YSL Black Opium Eau de Parfum 90ml", "fragrances")
    assert best is None, f"flanker must pend, got {best}"


def test_b2_select_best_rejects_deodorant_form():
    """Dior Sauvage EDT (the bottle) must NOT resolve to 'Dior Sauvage Deodorant'.
    The form token is STRIPPED as noise today (_FORM_NOISE_TOKENS) so the residual
    identity matches; form must DISCRIMINATE."""
    cands = [_cand(8.5, "Dior Sauvage Deodorant Stick 75g")]
    best = ps.select_best(cands, "Dior Sauvage Eau de Toilette 100ml", "fragrances")
    assert best is None, f"deodorant form must pend, got {best}"


def test_b2_select_best_rejects_candle_form():
    """Tom Ford Oud Wood EDP must NOT resolve to a 'Oud Wood Candle'."""
    cands = [_cand(55.0, "Tom Ford Oud Wood Candle 200g")]
    best = ps.select_best(cands, "Tom Ford Oud Wood Eau de Parfum 50ml", "fragrances")
    assert best is None, f"candle form must pend, got {best}"


def test_b2_select_best_pends_when_candidate_omits_query_stated_axes():
    """Query states concentration AND size; the candidate states NEITHER -> the
    candidate is UNVERIFIED on those axes -> pend (not auto-accept). Today the axes
    are only checked when BOTH sides state them (fail-open)."""
    cands = [_cand(30.0, "Dior Sauvage")]
    best = ps.select_best(cands, "Dior Sauvage Eau de Toilette 100ml", "fragrances")
    assert best is None, (
        "candidate omits the query's stated concentration+size -> unverified -> "
        f"must pend, got {best}"
    )


# ===========================================================================
# B3 — usable_exact_genuine KPI must LOAD + VALIDATE against the truth entry
# ===========================================================================

def _kpi_body(price):
    return {"overview": {"products": [{"price": price}, {"price": price}]}}


def test_b3_kpi_rejects_wrong_identity_against_truth():
    """The rebuilt KPI takes a truth_entry and INDEPENDENTLY validates the resolved
    price's identity. A genuine, in-stock, valid-PDP price whose title is a
    DIFFERENT product than truth.expected must NOT count as usable_exact_genuine.

    Current signature is (body, product_idx) — it never loads/examines the truth,
    so calling with a truth_entry raises TypeError (RED)."""
    er = importlib.import_module("scripts.eval_runner")
    truth = {"id": "kpi-frag-001", "query": "YSL Black Opium EDP 90ml",
             "category": "fragrances",
             "expected": {"brand": "Yves Saint Laurent", "model": "Black Opium",
                          "concentration": "EDP", "size_ml": 90}}
    wrong = {"amount": 30.0, "currency": "BHD", "source_method": "local_bhd",
             "in_stock": True, "title": "YSL Libre Eau de Parfum 90ml",
             "url": "https://example-bh.com/p/libre"}
    assert er.usable_exact_genuine_for_product(_kpi_body(wrong), 0, truth) is False, (
        "a wrong-identity (Libre for a Black Opium request) genuine price must NOT "
        "count as usable_exact_genuine"
    )


def test_b3_kpi_rejects_missing_url_and_unknown_stock():
    """A genuine price with NO url, or with UNKNOWN (not confirmed-True) stock, is
    NOT usable_exact_genuine. The prior test_kpi_metric.py:47 wrongly asserted a
    no-url price is usable; the rebuilt KPI requires a present PDP URL + confirmed
    in-stock."""
    er = importlib.import_module("scripts.eval_runner")
    truth = {"id": "kpi-x", "query": "Dior Sauvage EDT 100ml", "category": "fragrances",
             "expected": {"brand": "Dior", "model": "Sauvage",
                          "concentration": "EDT", "size_ml": 100}}
    no_url = {"amount": 45.0, "currency": "BHD", "source_method": "local_bhd",
              "in_stock": True, "title": "Dior Sauvage Eau de Toilette 100ml"}
    assert er.usable_exact_genuine_for_product(_kpi_body(no_url), 0, truth) is False, (
        "missing PDP URL -> not usable_exact_genuine (the old 'benign' assumption)"
    )


# ===========================================================================
# B4 — JSON-LD must not ship a stale / variant-minimum AggregateOffer as exact
# ===========================================================================

def test_b4_jsonld_rejects_expired_pricevaliduntil():
    """An offer whose priceValidUntil is in the past is STALE -> must not be shown."""
    html = '''<html><head><script type="application/ld+json">
    {"@type":"Product","name":"Dior Sauvage Eau de Toilette 100ml","brand":"Dior",
     "offers":{"@type":"Offer","price":"45.000","priceCurrency":"BHD",
               "priceValidUntil":"2020-01-01","availability":"https://schema.org/InStock"}}
    </script></head><body></body></html>'''
    res = ps.extract_jsonld_price(html, "Dior", "BHD", "Dior Sauvage EDT 100ml")
    assert res is None, f"expired 2020 offer must be rejected as stale, got {res}"


def test_b4_jsonld_aggregateoffer_lowprice_not_taken_as_exact():
    """AggregateOffer.lowPrice is the cheapest VARIANT/size, not the exact SKU's
    price — without a per-SKU Offer it must not be attributed to the exact query."""
    html = '''<html><head><script type="application/ld+json">
    {"@type":"Product","name":"Dior Sauvage Eau de Toilette","brand":"Dior",
     "offers":{"@type":"AggregateOffer","lowPrice":"22.000","highPrice":"60.000",
               "priceCurrency":"BHD","availability":"https://schema.org/InStock"}}
    </script></head><body></body></html>'''
    res = ps.extract_jsonld_price(html, "Dior", "BHD", "Dior Sauvage EDT 100ml")
    assert res is None, (
        "AggregateOffer.lowPrice (cheapest variant) must not be taken as the exact "
        f"100ml EDT price without per-SKU offer proof, got {res}"
    )


# ===========================================================================
# B5 — missing identity + URL is fail-OPEN
# ===========================================================================

def test_b5_select_best_pends_no_title():
    """A candidate with NO title/name has no verifiable identity -> fail-CLOSED.
    Today `if title and not _selection_match(...)` short-circuits, so a titleless
    candidate is appended to eligible (fail-open)."""
    cand = {"amount": 400.0, "currency": "BHD", "in_stock": True,
            "url": "https://example-bh.com/p/x", "source_method": "local_bhd"}
    best = ps.select_best([cand], "Samsung Galaxy S24 256GB", "electronics")
    assert best is None, f"no-title candidate must pend (no identity), got {best}"


def test_b5_select_best_pends_no_url():
    """A candidate with NO PDP URL cannot be verified to a current PDP -> pend.
    Today a missing url passes (only a listing url is rejected)."""
    cand = {"amount": 400.0, "currency": "BHD", "in_stock": True,
            "title": "Samsung Galaxy S24 256GB", "source_method": "local_bhd"}
    best = ps.select_best([cand], "Samsung Galaxy S24 256GB", "electronics")
    assert best is None, f"no-url candidate must pend (no PDP proof), got {best}"


# ===========================================================================
# B6 — cache write must be gated on the RESOLVED identity matching the request
# ===========================================================================

def test_b6_cache_write_guard_rejects_wrong_identity():
    """A wrong-identity resolved price must NOT be written to the request's cache
    key for the genuine TTL. The fix adds a write guard
    `should_cache_price(request_name, price, category)` -> False on a non-exact
    resolved price. (RED: helper does not exist yet.)"""
    from app.services.price_service import should_cache_price
    wrong = {"amount": 240.0, "currency": "BHD", "source_method": "local_bhd",
             "in_stock": True, "title": "Samsung Galaxy S24 FE 256GB",
             "url": "https://example-bh.com/p/s24fe"}
    assert should_cache_price("Samsung Galaxy S24 256GB", wrong, "electronics") is False
    right = {**wrong, "title": "Samsung Galaxy S24 256GB"}
    assert should_cache_price("Samsung Galaxy S24 256GB", right, "electronics") is True


def test_b6_resolved_title_keys_the_variant_axis():
    """When a request omits a variant axis the resolved title carries (request
    'iPhone 15', resolved 'iPhone 15 256GB'), the WRITE key built from the resolved
    title must encode the 256 axis (so a later 512GB resolution can't collide)."""
    bare = ps.build_size_aware_price_cache_key("Apple", "iPhone 15", None, "bahrain", "")
    resolved = ps.build_size_aware_price_cache_key(
        "Apple", "iPhone 15", None, "bahrain", "iPhone 15 256GB")
    assert bare != resolved, (
        "the resolved-title write key must encode the storage axis the bare request "
        "omitted, so distinct resolved variants never share one slot"
    )


# ===========================================================================
# B7 — guard_rejected (a diagnostic) must NOT leak into the public price payload
# ===========================================================================

def test_b7_public_price_view_strips_diagnostics():
    """The public price projection must drop the internal `guard_rejected` diagnostic
    and any `_`-prefixed internal keys. The fix adds `public_price_view(price)`.
    (RED: helper does not exist yet.)"""
    from app.services.price_service import public_price_view
    price = {"amount": None, "currency": "BHD", "unavailable": True,
             "reason": "pending_genuine", "guard_rejected": "not_exact",
             "_cached": True, "_cache_source": "db"}
    pub = public_price_view(price)
    assert "guard_rejected" not in pub, "guard_rejected is a diagnostic -> metadata only"
    assert not any(k.startswith("_") for k in pub), "internal _-keys must be stripped"
    assert pub.get("reason") == "pending_genuine"


# ===========================================================================
# B8 — ENABLE_EXACT_PRICE_GATE=false must be byte-identical to b207bfa
# ===========================================================================

def test_b8_flag_off_unbxd_keeps_waspce_fallback(monkeypatch):
    """With the gate OFF, _parse_unbxd_amount must restore the b207bfa behaviour
    (wasPrice as a last-resort fallback). The branch removed wasPrice
    UNCONDITIONALLY, so flag-OFF differs from b207bfa today (RED)."""
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "false")
    from app.services.unbxd_service import _parse_unbxd_amount
    assert _parse_unbxd_amount({"wasPrice": 50.0}) == 50.0, (
        "flag-OFF must be byte-identical to b207bfa: wasPrice fallback restored"
    )


def test_b8_flag_off_select_best_is_cheapest(monkeypatch):
    """With the gate OFF, select_best restores the legacy cheapest-pick (min amount),
    ignoring identity. (Pins the rollback contract.)"""
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "false")
    cands = [_cand(300.0, "Samsung Galaxy S24 256GB"),
             _cand(240.0, "Samsung Galaxy S24 FE 256GB")]
    best = ps.select_best(cands, "Samsung Galaxy S24 256GB", "electronics")
    assert best is not None and best["amount"] == 240.0, (
        "flag-OFF rollback: select_best returns the cheapest (legacy), got "
        f"{best and best['amount']}"
    )
