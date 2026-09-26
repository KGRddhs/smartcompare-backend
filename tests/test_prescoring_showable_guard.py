"""W4-3 (PO-RECORDED-MEASURED-04) — score the price you are willing to show.

ENABLE_PRESCORING_SHOWABLE_GUARD (default OFF, read PER CALL). The correctness
predicate that decides what the user may SEE (`is_price_showable(...,
enforce_correctness=True)`) runs today only at the response chokepoint
(response_builder.build_comparison_response) — i.e. AFTER compute_scores has picked
winner_index / dimension_winners / win_margin from the raw amount and AFTER the GPT
verdict was handed the raw product_data. So the payload ships `price: pending`
beside a 24.6-point win decided by that hidden price.

The unit (spec .qa-w4/W4_3_UNIT_SPEC.md + its binding FABLE REVIEW RULINGS) adds:
  * price_service.prescoring_showable_guard_enabled()   — per-call flag reader
  * price_service.apply_prescoring_showable_guard(pd)   — pure in-place pass that
    pends every non-showable price and stashes the reason on the PRODUCT as
    `_prescoring_showable_rejected` (falls back to "not_showable" — R6)
  * both orchestrator twins call it after reconcile_pair_fairness and BEFORE
    apply_region_currency_guard (R4: showable-then-region is the load-bearing
    order), before the `specs`/`prices` yields and compute_scores
  * response_builder harvests the stash before its `unavailable` early-continue,
    and under the flag the chokepoint's own guard_rejected append becomes
    idempotent on (product_index, reason) (R3)

Labels: every test is either RED (the behaviour is absent at b63a8368) or a PIN
(green at b63a8368, guards a regression). PINs that CALL the new helper carry a
flag-ON positive control in the same test, so a do-nothing stub
(`apply_prescoring_showable_guard = lambda pd: False`) still reddens them on an
assertion rather than only on the missing symbol (R8).

Fixtures are stated in full so every number reproduces (R8): electronics amounts
100.0 / 200.0 BHD, `local_bhd`, rating 4.5 / review_count 1000; the fragrance pair
40.0 / 60.0 BHD, rating 4.6 / 500; the one-sided spec-poor pair uses rating
4.5/1200 vs 4.4/900. All with ENABLE_EXACT_PRICE_GATE at its shipped default (ON) —
the whole correctness backstop is gated on it.

Zero network: the unit half is pure; the orchestrator halves reuse the fully mocked
harnesses (`_mock_to_verdict` for the stream twin, the explicit-pair mocked fetch +
patched generate_comparison for the sync twin).
"""
import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

import asyncio  # noqa: E402
import copy  # noqa: E402

import pytest  # noqa: E402

import app.services.structured_comparison_service as scs  # noqa: E402
from app.services import price_service  # noqa: E402
from app.services.price_service import is_price_showable, make_pending_price  # noqa: E402
from app.services.scoring_service import get_scoring_service  # noqa: E402

from tests.test_m13_04_full_stream_deadline import _mock_to_verdict  # noqa: E402
from tests.test_m18_region_guard_prescoring import (  # noqa: E402
    _collect_until,
    _event_type,
    _payload,
)

FLAG = "ENABLE_PRESCORING_SHOWABLE_GUARD"

GOOG0 = "https://www.google.com/search?ibp=oshop&q=Sony+WH-1000XM5"
GOOG1 = "https://www.google.com/search?ibp=oshop&q=Bose+QC+Ultra"
PDP0 = "https://bolo.bh/products/sony-wh-1000xm5"
PDP1 = "https://bolo.bh/products/bose-qc-ultra"

# Electronics specs WITH numerically scored fields (value dim reads the spec signal).
E0 = {"battery_life": "30 hours", "ram": "8 GB", "storage": "256 GB",
      "screen_size": "6.1 inch", "weight": "250 g"}
E1 = {"battery_life": "24 hours", "ram": "6 GB", "storage": "128 GB",
      "screen_size": "6.1 inch", "weight": "254 g"}
# Spec-poor variant: `_score_specs` -> None, so `_spec_missing` is set too.
NOSPEC = {"battery_life": "30 hours", "weight": "250 g", "warranty": "1 year"}
# The one-sided (winner-flip) spec-poor pair, exactly as measured (probe2).
SPEC0 = {"battery_life": "30 hours", "weight": "250 g", "warranty": "1 year",
         "connectivity": "Bluetooth 5.2", "noise_cancellation": "Yes"}
SPEC1 = {"battery_life": "24 hours", "weight": "254 g", "warranty": "1 year",
         "connectivity": "Bluetooth 5.3", "noise_cancellation": "Yes"}

SONY = "Sony WH-1000XM5"
BOSE = "Bose QuietComfort Ultra"


# --------------------------------------------------------------------- helpers

_LOCAL_HOSTS = ("127.0.0.1", "::1", "localhost", b"127.0.0.1", b"::1", b"localhost",
                "", None)


@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    """Zero-network guard. Resolution / connection to any non-loopback host is
    refused AND recorded, and the test fails at teardown if anything tried — so a
    fail-open call path (e.g. the L3 moderation tail) cannot silently reach the
    network and swallow the refusal. Loopback stays allowed: the Windows asyncio
    loop builds its self-pipe with a local socketpair."""
    import socket

    attempts = []
    real_getaddrinfo = socket.getaddrinfo
    real_connect = socket.socket.connect

    def _gai(host, *a, **k):
        if host not in _LOCAL_HOSTS:
            attempts.append(("getaddrinfo", host))
            raise OSError(f"W4-3 tests: network blocked (getaddrinfo {host!r})")
        return real_getaddrinfo(host, *a, **k)

    def _connect(self, address):
        host = address[0] if isinstance(address, tuple) else address
        if host not in _LOCAL_HOSTS:
            attempts.append(("connect", host))
            raise OSError(f"W4-3 tests: network blocked (connect {host!r})")
        return real_connect(self, address)

    monkeypatch.setattr(socket, "getaddrinfo", _gai)
    monkeypatch.setattr(socket.socket, "connect", _connect)
    yield
    assert attempts == [], f"a W4-3 test attempted network access: {attempts}"


def _guard():
    """Resolve the helper at CALL time so an absent symbol fails the individual
    test (AttributeError), never the whole module's collection."""
    return price_service.apply_prescoring_showable_guard


def _reader():
    return price_service.prescoring_showable_guard_enabled


def _flag(monkeypatch, value):
    if value is None:
        monkeypatch.delenv(FLAG, raising=False)
    else:
        monkeypatch.setenv(FLAG, value)


def _mk(name, brand, amount, url, specs, rating=4.5, rc=1000, cat="electronics",
        method="local_bhd"):
    return {
        "name": name, "full_name": name, "brand": brand, "category": cat,
        "price": {"amount": amount, "currency": "BHD", "source_method": method,
                  "url": url, "title": name, "in_stock": True, "retailer": "Best Buy"},
        "best_price": amount, "retailer": "Best Buy", "specs": specs,
        "rating": rating, "review_count": rc,
    }


def _both_google_numeric():
    return [_mk(SONY, "Sony", 100.0, GOOG0, E0), _mk(BOSE, "Bose", 200.0, GOOG1, E1)]


def _google_control():
    """A row the guard MUST pend (flag ON). Mixed into the PIN tests so a no-op stub
    reddens them on an assertion."""
    return _mk(SONY, "Sony", 100.0, GOOG0, E0)


def _assert_pended_control(row):
    assert row["price"]["amount"] is None, row["price"]
    assert row["price"]["unavailable"] is True, row["price"]
    assert row["_prescoring_showable_rejected"] == "non_pdp_url", row


_COMPARISON = {"winner": {"name": SONY, "reason": "Better value overall.",
                          "key_tradeoff": "Battery vs comfort"}}


def _build(pd, scoring_result):
    from app.services.response_builder import build_comparison_response
    return build_comparison_response(
        product_data=pd, comparison=copy.deepcopy(_COMPARISON),
        scoring_result=scoring_result, product_names=[SONY, BOSE],
        query="q", region="bahrain", category_used="electronics",
    )


def _value(res, i, dim="value_score"):
    return res["scores"][f"product_{i}"]["breakdown"][dim]


def _missing(res, i):
    return res["scores"][f"product_{i}"].get("missing_data") or []


# ------------------------------------------------ 1-7: the pure pass (unit half)


def test_01_red_headline_both_google_numeric_specs(monkeypatch):
    """RED. Both prices behind a google search link (`non_pdp_url`), numeric specs.
    Today compute_scores reads the raw amount: value 89.5 / 40.5, dimension winner
    "Sony WH-1000XM5" by 49.0, win_margin 24.6 — on two prices the payload then
    ships as `unavailable: true`. Guarded: value falls back to the spec signal
    (85.0 / 45.0), the value dimension has no winner, win_margin 22.8, and — R8 —
    `value_score` enters missing_data (it is NOT there raw for this numeric shape)."""
    _flag(monkeypatch, "true")
    pd = _both_google_numeric()
    raw = get_scoring_service().compute_scores(copy.deepcopy(pd))
    assert "value_score" not in _missing(raw, 0)  # discriminator: absent raw

    assert _guard()(pd) is True
    res = get_scoring_service().compute_scores(copy.deepcopy(pd))
    assert _value(res, 0) == 85.0, res["scores"]
    assert _value(res, 1) == 45.0, res["scores"]
    assert "value_score" in _missing(res, 0), _missing(res, 0)
    assert "value_score" in _missing(res, 1), _missing(res, 1)
    assert res["dimension_winners"]["value_score"]["winner"] == "N/A"
    assert res["dimension_winners"]["value_score"]["margin"] is None
    assert res["win_margin"] == 22.8


def test_02_red_review_literal_missing_score(monkeypatch):
    """RED. The review's literal claim, on the spec-poor shape: value 100.0 / 30.0
    and win_margin 14.0 raw -> MISSING_SCORE (50) for BOTH and 0.0 guarded.

    missing_data is deliberately NOT asserted here: on this shape `value_score` is
    already in missing_data in BOTH states (driven by `_spec_missing`, not by the
    price) — the wave plan's verifier caveat, confirmed by measurement."""
    _flag(monkeypatch, "true")
    pd = [_mk(SONY, "Sony", 100.0, GOOG0, NOSPEC), _mk(BOSE, "Bose", 200.0, GOOG1, NOSPEC)]
    assert _guard()(pd) is True
    res = get_scoring_service().compute_scores(copy.deepcopy(pd))
    assert _value(res, 0) == 50
    assert _value(res, 1) == 50
    assert res["win_margin"] == 0.0


def test_03_red_fragrance_missing_data_pins_something(monkeypatch):
    """RED. Fragrance (value dim `wear_value_score`, spec signal present): raw 76.0,
    NOT in missing_data, dimension winner "Dior Sauvage EDP 100ml" by 22.0,
    win_margin 2.8. Guarded: 65.7, in missing_data, no winner, win_margin 0.6."""
    _flag(monkeypatch, "true")
    f0 = _mk("Dior Sauvage EDP 100ml", "Dior", 40.0, GOOG0,
             {"concentration": "EDP", "size": "100ml", "longevity": "8 hours"},
             rating=4.6, rc=500, cat="fragrance")
    f1 = _mk("Chanel Bleu EDP 100ml", "Chanel", 60.0, GOOG1,
             {"concentration": "EDP", "size": "100ml", "longevity": "7 hours"},
             rating=4.6, rc=500, cat="fragrance")
    pd = [f0, f1]
    assert _guard()(pd) is True
    res = get_scoring_service().compute_scores(copy.deepcopy(pd))
    assert "wear_value_score" in _missing(res, 0), _missing(res, 0)
    assert _value(res, 0, "wear_value_score") == 65.7
    assert res["dimension_winners"]["wear_value_score"] == {"winner": "N/A", "margin": None}
    assert res["win_margin"] == 0.6


def test_04_red_winner_flips_one_sided(monkeypatch):
    """RED. product_0 behind a google link, product_1 on a real PDP (showable).
    Raw: winner_index 0, evidence "Sony WH-1000XM5 leads on the overall picture".
    Guarded: winner_index 1 and the honest deterministic evidence line."""
    _flag(monkeypatch, "true")
    pd = [_mk(SONY, "Sony", 100.0, GOOG0, SPEC0, rating=4.5, rc=1200),
          _mk(BOSE, "Bose", 200.0, PDP1, SPEC1, rating=4.4, rc=900)]
    assert _guard()(pd) is True
    assert pd[1]["price"]["amount"] == 200.0  # the showable side is untouched
    res = get_scoring_service().compute_scores(copy.deepcopy(pd))
    assert res["winner_index"] == 1
    assert res["winner_evidence"] == [
        "Bose QuietComfort Ultra has a confirmed Bahrain price while the other "
        "relies on an indicative figure"
    ]


def test_05_red_metadata_guard_rejected_survives_the_prescoring_pend(monkeypatch):
    """RED. Once the pre-scoring pass has pended the prices, the chokepoint's
    `unavailable is True` early-continue returns BEFORE its guard_rejected append —
    measured: the list is [] with the guard applied and no harvest. The harvest
    (response_builder, before the early-continue) is what keeps the canary honest."""
    _flag(monkeypatch, "true")
    pd = _both_google_numeric()
    assert _guard()(pd) is True
    resp = _build(pd, get_scoring_service().compute_scores(copy.deepcopy(pd)))
    assert resp["metadata"]["guard_rejected"] == [
        {"product_index": 0, "reason": "non_pdp_url"},
        {"product_index": 1, "reason": "non_pdp_url"},
    ]


@pytest.mark.parametrize("method", [
    "converted_usd", "local_bhd", "page_scrape_jsonld", "shopify_json", "official_brand",
])
def test_06_red_guard_delegates_to_is_price_showable(monkeypatch, method):
    """RED (W4-1 composition pin). The guard must not carry a source-method test of
    its own: a showable method on a REAL PDP with an exact title is never blanked —
    the `converted_usd` row is the specific W4-1 pin (W4-1 relabels shopping rows
    to converted_usd; a legitimately showable converted price must survive) — while
    the SAME method behind a google search url is pended with `non_pdp_url`.
    Both rows go through ONE call so a no-op stub reddens the PDP half too (R8)."""
    _flag(monkeypatch, "true")
    pdp = _mk(SONY, "Sony", 100.0, PDP0, E0, method=method)
    goog = _mk(SONY, "Sony", 100.0, GOOG0, E0, method=method)
    pdp_before = copy.deepcopy(pdp)
    pd = [pdp, goog]
    assert _guard()(pd) is True
    assert pd[0] == pdp_before
    assert "_prescoring_showable_rejected" not in pd[0]
    assert pd[1]["price"]["amount"] is None
    assert pd[1]["price"]["unavailable"] is True
    assert pd[1]["price"]["reason"] == "pending_genuine"
    assert pd[1]["_prescoring_showable_rejected"] == "non_pdp_url"


_PDP_OK = "https://bolo.bh/products/sony-wh-1000xm5"


@pytest.mark.parametrize("expected,name,category,price", [
    ("non_pdp_url", SONY, "electronics",
     {"amount": 100.0, "currency": "BHD", "source_method": "local_bhd",
      "url": GOOG0, "title": SONY, "in_stock": True}),
    ("out_of_stock", SONY, "electronics",
     {"amount": 100.0, "currency": "BHD", "source_method": "local_bhd",
      "url": _PDP_OK, "title": SONY, "in_stock": False}),
    ("no_identity", SONY, "electronics",
     {"amount": 100.0, "currency": "BHD", "source_method": "local_bhd"}),
    ("not_exact", "Dior Sauvage EDT", "fragrance",
     {"amount": 40.0, "currency": "BHD", "source_method": "local_bhd",
      "url": "https://bolo.bh/products/dior-sauvage-parfum",
      "title": "Dior Sauvage Parfum", "in_stock": True}),
    # R6 — `estimated` returns False BEFORE any stamp (guard_rejected is None), so
    # the helper's `or "not_showable"` fallback is what is asserted.
    ("not_showable", SONY, "electronics",
     {"amount": 100.0, "currency": "BHD", "source_method": "estimated",
      "url": _PDP_OK, "title": SONY, "in_stock": True}),
], ids=["non_pdp_url", "out_of_stock", "no_identity", "not_exact", "not_showable"])
def test_07_red_reason_vocabulary(monkeypatch, expected, name, category, price):
    """RED. The stashed reason per rejection class, flag ON, one product per row."""
    _flag(monkeypatch, "true")
    pd = [{"name": name, "full_name": name, "brand": name.split()[0],
           "category": category, "price": copy.deepcopy(price),
           "best_price": price["amount"], "retailer": "X"}]
    assert _guard()(pd) is True
    assert pd[0]["_prescoring_showable_rejected"] == expected
    assert pd[0]["price"]["amount"] is None
    assert pd[0]["best_price"] is None
    assert pd[0]["retailer"] is None


def test_r5_red_category_is_derived_from_the_query_when_absent(monkeypatch):
    """RED (R5 — the discriminating fixture for the category derivation). The row
    carries NO `category`; `_infer_category_from_query("Apple iPhone 15")` resolves
    `electronics`, under which `Apple iPhone 15 Pro` is `not_exact` — with category
    None the SAME price is showable (asserted as the control), so a guard that used
    `pd.get("category")` alone would leave it unpended."""
    _flag(monkeypatch, "true")
    price = {"amount": 300.0, "currency": "BHD", "source_method": "local_bhd",
             "url": "https://bolo.bh/products/apple-iphone-15-pro",
             "title": "Apple iPhone 15 Pro", "in_stock": True}
    # Control: the derivation is what decides this row.
    assert is_price_showable("Apple iPhone 15", copy.deepcopy(price), None,
                             enforce_correctness=True) is True
    assert is_price_showable("Apple iPhone 15", copy.deepcopy(price), "electronics",
                             enforce_correctness=True) is False

    pd = [{"name": "Apple iPhone 15", "full_name": "Apple iPhone 15", "brand": "Apple",
           "price": copy.deepcopy(price), "best_price": 300.0, "retailer": "X"}]
    assert "category" not in pd[0]
    assert _guard()(pd) is True
    assert pd[0]["_prescoring_showable_rejected"] == "not_exact"
    assert pd[0]["price"]["amount"] is None


def test_r5b_red_name_is_full_name_first(monkeypatch):
    """RED (mirror fidelity with the chokepoint's `full_name or name`). Real
    orchestrator rows carry a brand-prefixed `full_name` beside a brand-less `name`.
    Here that difference decides the verdict: `_infer_category_from_query("Dior
    Sauvage")` is fragrance, under which the `Parfum` title is `not_exact`; the bare
    `name` "Sauvage" infers NO category and the SAME price is showable (asserted as
    the control). A guard that read `name` first would leave a price the chokepoint
    then pends feeding the scorer."""
    _flag(monkeypatch, "true")
    price = {"amount": 120.0, "currency": "BHD", "source_method": "local_bhd",
             "url": "https://bolo.bh/products/dior-sauvage-parfum",
             "title": "Dior Sauvage Parfum", "in_stock": True}
    # Control: the name choice is what decides this row.
    assert is_price_showable("Sauvage", copy.deepcopy(price),
                             price_service._infer_category_from_query("Sauvage"),
                             enforce_correctness=True) is True
    pd = [{"name": "Sauvage", "full_name": "Dior Sauvage", "brand": "Dior",
           "price": copy.deepcopy(price), "best_price": 120.0, "retailer": "X"}]
    assert _guard()(pd) is True
    assert pd[0]["_prescoring_showable_rejected"] == "not_exact"
    assert pd[0]["price"]["amount"] is None


def test_17_pin_pended_price_keeps_its_own_currency_and_size(monkeypatch):
    """PIN (make_pending_price kwarg fidelity). A non-SHOWABLE price keeps its own
    currency and size when pended pre-scoring — identical to what the chokepoint
    itself ships for the same row (measured through build_comparison_response with
    the flag OFF: `{"amount": None, "currency": "SAR", "unavailable": True,
    "reason": "pending_genuine", "size": "100ml"}`). Fixture is SAR (not BHD) so a
    hardcoded `currency="BHD"` reddens, and carries a size so `size=None` reddens.
    The google control in the same call must be pended."""
    _flag(monkeypatch, "true")
    row = {"name": "Dior Sauvage EDT 100ml", "full_name": "Dior Sauvage EDT 100ml",
           "brand": "Dior", "category": "fragrance",
           "price": {"amount": 450.0, "currency": "SAR", "source_method": "local_bhd",
                     "url": "https://www.google.com/search?ibp=oshop&q=Dior+Sauvage",
                     "title": "Dior Sauvage EDT 100ml", "in_stock": True,
                     "size": "100ml"},
           "best_price": 450.0, "retailer": "X"}
    pd = [copy.deepcopy(row), _google_control()]
    assert _guard()(pd) is True
    expected = {"amount": None, "currency": "SAR", "unavailable": True,
                "reason": "pending_genuine", "size": "100ml"}
    assert pd[0]["price"] == expected
    assert pd[0]["_prescoring_showable_rejected"] == "non_pdp_url"
    _assert_pended_control(pd[1])

    # The chokepoint's own pend of the same row (flag OFF, no guard) is identical.
    monkeypatch.delenv(FLAG, raising=False)
    from app.services.response_builder import build_comparison_response
    resp = build_comparison_response(product_data=[copy.deepcopy(row)], region="bahrain")
    assert resp["overview"]["products"][0]["price"] == expected


def test_18_pin_stash_key_reaches_only_the_bc_products_alias_under_the_flag(monkeypatch):
    """PIN of CURRENT behaviour (disclosed, not endorsed). The legacy BC `products`
    alias ships the raw product dicts wholesale (response_builder assigns
    `result["products"] = product_data`), so with the flag ON the product-level stash
    reaches `/products[i]/_prescoring_showable_rejected` — the same pre-existing leak
    #113's `_region_guard_rejected` has. The rendered surface
    (`overview.products[i]`, an explicit key set) never carries it, and with the flag
    OFF the key is never set at all. The value is redundant with
    metadata.guard_rejected and the 97b5f15 client ignores it. Follow-up (recorded in
    the PR): scrub both `_`-stash keys from the BC alias — when that lands, the
    flag-ON half of this pin is expected to change."""
    for state, expect_bc in ((None, False), ("true", True)):
        _flag(monkeypatch, state)
        pd = _both_google_numeric()
        _guard()(pd)
        resp = _build(pd, get_scoring_service().compute_scores(copy.deepcopy(pd)))
        for i in (0, 1):
            assert "_prescoring_showable_rejected" not in resp["overview"]["products"][i]
            assert ("_prescoring_showable_rejected" in resp["products"][i]) is expect_bc, state
            if expect_bc:
                assert resp["products"][i]["_prescoring_showable_rejected"] == "non_pdp_url"


def test_r6_red_not_showable_reason_reaches_metadata(monkeypatch):
    """RED (R6). The `not_showable` fallback is a NEW metadata.guard_rejected
    reason: an estimated-method row is pended pre-scoring (scoring must agree with
    display) and the harvest surfaces it. Today the chokepoint pends such a row
    without any stamp, so the canary cannot count it at all."""
    _flag(monkeypatch, "true")
    est = _mk(SONY, "Sony", 100.0, PDP0, E0, method="estimated")
    ok = _mk(BOSE, "Bose", 200.0, PDP1, E1)
    pd = [est, ok]
    assert _guard()(pd) is True
    assert pd[0]["_prescoring_showable_rejected"] == "not_showable"
    resp = _build(pd, get_scoring_service().compute_scores(copy.deepcopy(pd)))
    assert resp["metadata"]["guard_rejected"] == [
        {"product_index": 0, "reason": "not_showable"},
    ]


def test_r7b_pin_current_manufactured_cross_tier(monkeypatch):
    """PIN of CURRENT behaviour (R7b), red today only because the helper is absent.

    Both prices are `luxury` electronics (900 / 1800 BHD) raw, so is_cross_tier is
    False. Pending product_0 makes scoring default its tier to `mid`, which
    MANUFACTURES is_cross_tier and cuts the honest, SHOWABLE product_1's value
    score 40.5 -> 15.6, while `dimension_winners.value_score` crowns product_1 at
    the LOWER score (15.6 < 85.0). This is a scoring_service hazard shared with #113
    and outside this unit's must-not-touch list; it is pinned so it is visible.
    Follow-up PO-RECORDED-MEASURED-04b (exclude a missing-price tier from
    is_cross_tier) is sequenced BEFORE this flag flips — when it lands this pin
    is expected to change."""
    _flag(monkeypatch, "true")
    pd = [_mk(SONY, "Sony", 900.0, GOOG0, E0), _mk(BOSE, "Bose", 1800.0, PDP1, E1)]
    raw = get_scoring_service().compute_scores(copy.deepcopy(pd))
    assert raw["is_cross_tier"] is False
    assert _value(raw, 1) == 40.5

    assert _guard()(pd) is True
    res = get_scoring_service().compute_scores(copy.deepcopy(pd))
    assert res["price_tiers_by_index"] == {"product_0": "mid", "product_1": "luxury"}
    assert res["is_cross_tier"] is True
    assert _value(res, 0) == 85.0
    assert _value(res, 1) == 15.6
    assert res["dimension_winners"]["value_score"]["winner"] == "Bose QuietComfort Ultra"


# ------------------------------------------------------ PINs on the pure pass


@pytest.mark.parametrize("value", [None, "false"], ids=["unset", "false"])
def test_10a_pin_flag_off_helper_is_a_noop(monkeypatch, value):
    """PIN (rollback). Flag unset / "false": the helper returns False and the
    product_data is `==` its pre-call deepcopy — no `_prescoring_showable_rejected`
    key. Positive control: the SAME data with the flag ON is pended, so the OFF
    result is the flag's doing (and a no-op stub reddens this test)."""
    _flag(monkeypatch, value)
    pd = _both_google_numeric()
    before = copy.deepcopy(pd)
    assert _guard()(pd) is False
    assert pd == before

    monkeypatch.setenv(FLAG, "true")
    on = _both_google_numeric()
    assert _guard()(on) is True
    _assert_pended_control(on[0])


@pytest.mark.parametrize("value", [None, "false"], ids=["unset", "false"])
def test_10b_pin_flag_off_end_to_end_numbers_hold(monkeypatch, value):
    """PIN (green at b63a8368). Flag OFF the response builder must reproduce the
    spec's section-1.2 HEAD numbers exactly: value 89.5, overview.winner.margin 24.6,
    the Sony value-dimension win by 49.0, and the chokepoint's two `non_pdp_url`
    rows. This is the flag-OFF rollback pin the corpus byte-identity harness cannot
    see (it never reaches is_price_showable / compute_scores / the builder).

    The helper is called first, exactly where the orchestrator calls it (after
    fairness, before compute_scores), so a reader that ignores the env (e.g. a
    `return True` left behind) pends both prices and reddens every number below —
    this is the end-to-end half of the default-OFF contract, not only the
    chokepoint's."""
    _flag(monkeypatch, value)
    pd = _both_google_numeric()
    assert _guard()(pd) is False
    assert "_prescoring_showable_rejected" not in pd[0]
    res = get_scoring_service().compute_scores(copy.deepcopy(pd))
    assert _value(res, 0) == 89.5
    assert res["win_margin"] == 24.6
    resp = _build(pd, res)
    assert resp["overview"]["winner"]["margin"] == 24.6
    assert resp["scoring"]["scores"]["product_0"]["breakdown"]["value_score"] == 89.5
    assert resp["scoring"]["dimension_winners"]["value_score"] == {
        "winner": "Sony WH-1000XM5", "margin": 49.0,
    }
    assert resp["metadata"]["guard_rejected"] == [
        {"product_index": 0, "reason": "non_pdp_url"},
        {"product_index": 1, "reason": "non_pdp_url"},
    ]


def test_10c_pin_harvest_is_flag_gated(monkeypatch):
    """PIN (green at b63a8368). A product carrying the stash with the flag OFF is
    NOT harvested: metadata.guard_rejected stays exactly what the chokepoint alone
    produces (here [] — the price is already pending). Keeps flag-OFF
    byte-identical for any product_data that happens to carry the key."""
    monkeypatch.delenv(FLAG, raising=False)
    pd = [{"name": SONY, "full_name": SONY, "category": "electronics",
           "price": make_pending_price(currency="BHD", reason="pending_genuine"),
           "best_price": None, "retailer": None,
           "_prescoring_showable_rejected": "non_pdp_url"}]
    from app.services.response_builder import build_comparison_response
    resp = build_comparison_response(product_data=pd, region="bahrain")
    assert resp["metadata"].get("guard_rejected", []) == []


def test_11_pin_showable_price_untouched_flag_on(monkeypatch):
    """PIN (over-rejection guard). Real PDP, exact title, in stock, flag ON: the
    row is `==` its deepcopy (price, best_price, retailer) and carries no stash.
    The google control in the same call must be pended."""
    _flag(monkeypatch, "true")
    ok = _mk(SONY, "Sony", 100.0, PDP0, E0)
    before = copy.deepcopy(ok)
    pd = [ok, _google_control()]
    assert _guard()(pd) is True
    assert pd[0] == before
    assert pd[0]["best_price"] == 100.0 and pd[0]["retailer"] == "Best Buy"
    assert "_prescoring_showable_rejected" not in pd[0]
    _assert_pended_control(pd[1])


def test_12_pin_already_pending_keeps_its_own_reason(monkeypatch):
    """PIN. An upstream `size_mismatch` pend (size 50ml) is not clobbered to
    pending_genuine and gets no stash. The google control must be pended."""
    _flag(monkeypatch, "true")
    sz = _mk(SONY, "Sony", 100.0, PDP0, E0)
    sz["price"] = make_pending_price(currency="BHD", reason="size_mismatch", size="50ml")
    before = copy.deepcopy(sz)
    pd = [sz, _google_control()]
    assert _guard()(pd) is True
    assert pd[0] == before
    assert pd[0]["price"]["reason"] == "size_mismatch"
    assert pd[0]["price"]["size"] == "50ml"
    assert "_prescoring_showable_rejected" not in pd[0]
    _assert_pended_control(pd[1])


def test_13_pin_non_dict_price_is_left_to_the_chokepoint(monkeypatch):
    """PIN. `price is None` is the chokepoint's SIB-5 branch: skipped, no crash, no
    coercion. The google control must be pended."""
    _flag(monkeypatch, "true")
    nd = {"name": "Alpha", "full_name": "Alpha", "price": None}
    pd = [nd, _google_control()]
    assert _guard()(pd) is True
    assert pd[0]["price"] is None
    assert "_prescoring_showable_rejected" not in pd[0]
    _assert_pended_control(pd[1])


def test_14_pin_chokepoint_backstop_still_fires_for_a_direct_caller(monkeypatch):
    """PIN (regression). Flag ON, raw google-linked product_data, NO guard run
    (the hard-cap-partial shape): the chokepoint still pends both prices and still
    reports both `non_pdp_url` rows. Reddens if the implementer MOVES the check
    instead of adding a pass."""
    _flag(monkeypatch, "true")
    pd = _both_google_numeric()
    resp = _build(pd, get_scoring_service().compute_scores(copy.deepcopy(pd)))
    for p in resp["overview"]["products"]:
        assert p["price"]["amount"] is None, p["price"]
        assert p["price"]["unavailable"] is True, p["price"]
    assert resp["metadata"]["guard_rejected"] == [
        {"product_index": 0, "reason": "non_pdp_url"},
        {"product_index": 1, "reason": "non_pdp_url"},
    ]


def test_15_pin_stash_plus_unpended_price_counts_once(monkeypatch):
    """PIN (R3). The in-call de-dup the spec body specified is dead code
    (`_guard_rejected_diag` is fresh per call) and is dropped. The real duplicate
    shape: a product carrying the pre-scoring stash AND a price that is NOT yet
    pended — the harvest appends it, then the chokepoint's own append fires again
    (measured: two `non_pdp_url` rows for one product). Under the flag the
    chokepoint append is idempotent on (product_index, reason): exactly one entry
    per product. Green at b63a8368 (no harvest exists yet)."""
    _flag(monkeypatch, "true")
    pd = _both_google_numeric()
    pd[0]["_prescoring_showable_rejected"] = "non_pdp_url"
    resp = _build(pd, get_scoring_service().compute_scores(copy.deepcopy(pd)))
    assert resp["metadata"]["guard_rejected"] == [
        {"product_index": 0, "reason": "non_pdp_url"},
        {"product_index": 1, "reason": "non_pdp_url"},
    ]


@pytest.mark.parametrize("value,expected", [
    ("true", True), ("1", True), ("yes", True), ("on", True), ("  TRUE  ", True),
    ("false", False), ("0", False), ("no", False), ("off", False), ("", False),
])
def test_16_red_flag_reader_values(monkeypatch, value, expected):
    """RED (absent reader). The `region_currency_guard_enabled` idiom verbatim.
    Each case first asserts the canonical "true" reads True (control), so a
    constant-False stub reddens the falsy cases too."""
    monkeypatch.setenv(FLAG, "true")
    assert _reader()() is True
    monkeypatch.setenv(FLAG, value)
    assert _reader()() is expected


def test_16_red_flag_reader_unset_and_per_call(monkeypatch):
    """RED (absent reader). Unset -> False; a setenv AFTER import flips the very
    next call (read per call, never memoised at import)."""
    monkeypatch.delenv(FLAG, raising=False)
    assert _reader()() is False
    monkeypatch.setenv(FLAG, "true")
    assert _reader()() is True
    monkeypatch.setenv(FLAG, "off")
    assert _reader()() is False


# ------------------------------------------- orchestrator twins (8, 9, R1, R4, R7e)


def _goog_stream_fetch(monkeypatch, service):
    """The mirror's `_showable_bhd_fetch`, identical except `url` is a google search
    link — so the ONLY pre-scoring pass that can pend it is this guard."""

    async def _fake_fetch(product, region, include_specs, include_reviews, nocache,
                          partial_slot=0, **kw):
        _name = f"{product.get('brand', 'X')} {product.get('name', 'Y')}".strip()
        return {
            "brand": product.get("brand", "X"),
            "name": product.get("name", "Y"),
            "full_name": _name,
            "specs": {"k": "v"},
            "price": {
                "amount": 10.0, "currency": "BHD", "estimated": False,
                "source_method": "local_bhd", "retailer": "noon",
                "url": GOOG0, "title": _name, "in_stock": True,
            },
            "best_price": 10.0,
            "retailer": "noon",
            "reviews": {"highlights": []},
            "fact_check": {"overall_confidence": "medium"},
            "image_url": None,
        }

    monkeypatch.setattr(service, "_fetch_product_data", _fake_fetch)


@pytest.mark.asyncio
@pytest.mark.parametrize("flag_on,expected", [(True, None), (False, 10.0)])
async def test_08_red_streaming_compute_scores_receives_guarded_product_data(
    monkeypatch, flag_on, expected
):
    """RED on the ON half (stream twin). compute_scores must be handed the pended
    price, not the raw 10.0 behind the google link. Flag OFF: the raw amount."""
    _flag(monkeypatch, "true" if flag_on else None)
    service = scs.get_comparison_service()
    _mock_to_verdict(monkeypatch, service)
    _goog_stream_fetch(monkeypatch, service)
    scoring = scs.get_scoring_service()

    gen = service.compare_from_text_streaming(query="A vs B", region="bahrain")
    events = await _collect_until(gen, "scores")

    assert scoring.compute_scores.call_args is not None, [_event_type(e) for e in events]
    scored_pd = scoring.compute_scores.call_args[0][0]
    assert scored_pd[0]["price"]["amount"] == expected, scored_pd[0]["price"]
    if flag_on:
        assert scored_pd[0]["_prescoring_showable_rejected"] == "non_pdp_url"
        assert scored_pd[1]["price"]["amount"] is None


@pytest.mark.asyncio
async def test_09_pin_sse_prices_event_identical_in_both_flag_states(monkeypatch):
    """PIN (regression, green at b63a8368). The `prices` projection already pends a
    non-showable price on a COPY, so moving the pend earlier must not change the
    streamed payload: pending in both states, and the ON payload `==` the OFF one
    (spec section 3: measured IDENTICAL)."""
    payloads = {}
    for state in (None, "true"):
        _flag(monkeypatch, state)
        service = scs.get_comparison_service()
        _mock_to_verdict(monkeypatch, service)
        _goog_stream_fetch(monkeypatch, service)
        gen = service.compare_from_text_streaming(query="A vs B", region="bahrain")
        events = await _collect_until(gen, "prices")
        payload = _payload(events, "prices")
        assert payload is not None, [_event_type(e) for e in events]
        assert payload["product_0"]["price"]["amount"] is None, payload
        assert payload["product_0"]["price"]["unavailable"] is True, payload
        payloads[state] = payload
    assert payloads["true"] == payloads[None]


class _StopAfterScoring(RuntimeError):
    pass


def _run_sync(monkeypatch, *, url, region="bahrain", stop_at_scoring=True):
    """Drive the SYNC twin (`compare_from_text`) fully mocked: explicit pair, mocked
    `_fetch_product_data`, fairness patched to a no-op (exactly as `_mock_to_verdict`
    does for the stream twin), patched `generate_comparison`. compute_scores records
    a deepcopy of its product input and — for the R1 pin — raises so nothing
    downstream runs. Returns (response, holder)."""
    from unittest.mock import AsyncMock

    from app.services import scoring_service as _ss

    service = scs.get_comparison_service()
    monkeypatch.setattr(scs, "reconcile_pair_fairness", lambda *a, **k: None)

    async def _fake_fetch(product, region, include_specs, include_reviews, nocache=False,
                          partial_slot=0, **kw):
        _name = f"{product.get('brand') or ''} {product.get('name') or ''}".strip() or "X Y"
        return {
            "brand": product.get("brand") or "X",
            "name": product.get("name") or "Y",
            "full_name": _name, "category": "electronics",
            "specs": {"battery_mah": 4000, "storage_gb": 128},
            "price": {"amount": 120.0, "currency": "BHD", "estimated": False,
                      "source_method": "local_bhd", "retailer": "Best Buy",
                      "url": url, "title": _name, "in_stock": True},
            "best_price": 120.0, "retailer": "Best Buy",
            "reviews": {"highlights": []},
            "fact_check": {"overall_confidence": "medium"},
            "image_url": None,
        }

    monkeypatch.setattr(service, "_fetch_product_data", _fake_fetch)

    # A PRIVATE instance, never the singleton (#186): monkeypatch.setattr on an
    # INSTANCE undoes by setting the bound method it read, which then shadows
    # ScoringService.compute_scores on that instance for the rest of the process.
    real_service = _ss.ScoringService()
    real_compute = real_service.compute_scores
    holder = {}

    def _spy(products_data, *a, **k):
        holder["scored_pd"] = copy.deepcopy(products_data)
        if stop_at_scoring:
            raise _StopAfterScoring("W4-3 sync pin: compute_scores input recorded")
        return real_compute(products_data, *a, **k)

    monkeypatch.setattr(real_service, "compute_scores", _spy)
    monkeypatch.setattr(scs, "get_scoring_service", lambda: real_service)

    async def _record_verdict_input_and_stop(product1, product2, *a, **k):
        # Record a DEEPCOPY at call time: the orchestrator later hands the SAME
        # dicts to build_comparison_response, whose chokepoint mutates them, so a
        # stored reference would show post-chokepoint state. Then stop, so the
        # post-verdict tail (L3 moderation = a real OpenAI call) never runs.
        holder["verdict_input"] = (copy.deepcopy(product1), copy.deepcopy(product2))
        raise _StopAfterScoring("W4-3 sync pin: verdict input recorded")

    gen_mock = AsyncMock(side_effect=_record_verdict_input_and_stop)
    monkeypatch.setattr(scs, "generate_comparison", gen_mock)
    holder["generate_comparison"] = gen_mock

    response = asyncio.run(service.compare_from_text(
        query="Samsung Galaxy S24 vs Apple iPhone 15", region=region,
        explicit_pair=("Samsung Galaxy S24", "Apple iPhone 15"),
        selected_category="electronics", user_id=None, nocache=True,
    ))
    return response, holder


@pytest.mark.parametrize("flag_on,expected", [(True, None), (False, 120.0)])
def test_r1_red_sync_compute_scores_receives_guarded_product_data(
    monkeypatch, flag_on, expected
):
    """RED on the ON half (R1 — the SYNC twin must be pinned; before this, deleting
    the sync call site reddened nothing). compute_scores' recorded input carries the
    pended price for a google-url row. Flag OFF: the raw 120.0."""
    _flag(monkeypatch, "true" if flag_on else None)
    _resp, holder = _run_sync(monkeypatch, url=GOOG0)
    scored = holder.get("scored_pd")
    assert scored is not None, "compute_scores never ran on the sync path"
    assert scored[0]["price"]["amount"] == expected, scored[0]["price"]
    assert scored[1]["price"]["amount"] == expected, scored[1]["price"]
    if flag_on:
        assert scored[0]["price"]["unavailable"] is True
        assert scored[0]["_prescoring_showable_rejected"] == "non_pdp_url"


def test_r7e_red_sync_verdict_payload_carries_no_best_price(monkeypatch):
    """RED (R7e). The verdict's remaining raw-price channel is `best_price` (the
    `price` itself is already scrubbed by `_verdict_safe_product` at HEAD). With the
    flag ON the guard nulls it before generate_comparison, so the dumped verdict
    payload carries no amount at all. (Flag OFF still leaks it — the unflagged
    follow-up in `_verdict_safe_product` is queued separately, not pinned here.)"""
    from app.services.extraction_service import _verdict_safe_product

    _flag(monkeypatch, "true")
    _resp, holder = _run_sync(monkeypatch, url=GOOG0, stop_at_scoring=False)
    assert "verdict_input" in holder, "generate_comparison never ran on the sync path"
    for p in holder["verdict_input"]:
        assert p["best_price"] is None, p.get("best_price")
        dumped = _verdict_safe_product(p, "electronics")
        assert dumped["best_price"] is None
        assert dumped["price"]["amount"] is None


def _both_flags_on(monkeypatch):
    monkeypatch.setenv("ENABLE_REGION_CURRENCY_GUARD", "true")
    monkeypatch.setenv(FLAG, "true")


def _assert_showable_then_region(pd0):
    """R4 — the load-bearing order. Showable first: the google-linked BHD price is
    pended in its OWN currency with stash `non_pdp_url`; the region guard then hits
    its `unavailable` early-continue. Region first would give currency SAR and
    `_region_guard_rejected = region_currency_mismatch` (measured)."""
    assert pd0["price"]["amount"] is None, pd0["price"]
    assert pd0["price"]["currency"] == "BHD", pd0["price"]
    assert pd0["_prescoring_showable_rejected"] == "non_pdp_url", pd0
    assert "_region_guard_rejected" not in pd0, pd0


def test_r4_red_order_showable_then_region_sync(monkeypatch):
    """RED (R4, sync twin). Both flags ON, region saudi_arabia, a BHD price behind a
    google url."""
    _both_flags_on(monkeypatch)
    _resp, holder = _run_sync(monkeypatch, url=GOOG0, region="saudi_arabia")
    scored = holder.get("scored_pd")
    assert scored is not None, "compute_scores never ran on the sync path"
    _assert_showable_then_region(scored[0])


@pytest.mark.asyncio
async def test_r4_red_order_showable_then_region_stream(monkeypatch):
    """RED (R4, stream twin). Same as the sync case through compare_from_text_streaming."""
    _both_flags_on(monkeypatch)
    service = scs.get_comparison_service()
    _mock_to_verdict(monkeypatch, service)
    _goog_stream_fetch(monkeypatch, service)
    scoring = scs.get_scoring_service()
    gen = service.compare_from_text_streaming(query="A vs B", region="saudi_arabia")
    events = await _collect_until(gen, "scores")
    assert scoring.compute_scores.call_args is not None, [_event_type(e) for e in events]
    _assert_showable_then_region(scoring.compute_scores.call_args[0][0][0])
