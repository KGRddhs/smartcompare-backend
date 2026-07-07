"""Budget Arabic/Gulf-house fragrance floor bypass (source-aware).

The designer low-price floor (is_implausible_low_fragrance_price, 25 BHD/100ml)
wrongly pended the genuine cheap price of budget Arabic houses (Lattafa/Rasasi/
Al Haramain/Ajmal — whose real full 100ml EDP is ~8-25 BHD). The fix does NOT
change the floor function itself (it still protects the LOOSE Serper-shopping
path); instead the DISPLAY chokepoint (is_price_showable) BYPASSES the floor for a
TRUSTWORTHY genuine direct-adapter exact-PDP budget-house price — the store's
authoritative listed price for the exact SKU. Flag ENABLE_BUDGET_FRAGRANCE_FLOOR
(default ON; OFF -> the floor applies, byte-identical).

Coverage-driven, BOTH directions + the review-surfaced hazards:
  A. trusted budget direct-adapter prices now SHOW
  B. the floor FUNCTION is unchanged (loose-path protection intact)
  C. non-trusted budget prices STAY floored: loose listing-URL, estimate,
     converted, and the houses' expensive dehn-al-oud/attar OIL lines
  D. designer/premium unaffected + no generic-token collision ("my perfumes")
  E. flag OFF == legacy (floor applies to budget houses again)
"""
import pytest

import app.services.price_service as ps

_PDP = "https://alibaksh.com/product/x-100ml"
_ALHAJIS = "https://alhajisbahrain.com/products/lattafa-khamrah-edp-100ml"
_LISTING = "https://www.google.com/search?ibp=oshop&q=x&prds=localAnnotations"


def _price(amount, source_method="woo_store_api", url=_PDP, title="", in_stock=True):
    return {"amount": amount, "currency": "BHD", "source_method": source_method,
            "in_stock": in_stock, "url": url, "title": title}


def _show(q, p):
    return ps.is_price_showable(q, p, "fragrances", enforce_correctness=True)


@pytest.fixture(autouse=True)
def _flag_on(monkeypatch):
    monkeypatch.setenv("ENABLE_BUDGET_FRAGRANCE_FLOOR", "true")


# --- A. trusted budget direct-adapter prices SHOW -------------------------
@pytest.mark.parametrize("query,amount,title,url,method", [
    ("Lattafa Khamrah", 12.0, "Lattafa Khamrah Edp 100Ml", _ALHAJIS, "shopify_json"),
    ("Lattafa Asad", 8.0, "Lattafa Asad Bourbon 100ml", _PDP, "woo_store_api"),
    ("Rasasi Hawas For Him", 14.0, "Rasasi Hawas For Him EDP 100ml", _PDP, "woo_store_api"),
    ("Al Haramain Amber Oud Gold Edition", 22.0, "Al Haramain Amber Oud Gold Edition (U) Edp 100ml", _PDP, "woo_store_api"),
    ("Ajmal Aristocrat", 18.0, "Ajmal Aristocrat For Him EDP 75ml", _PDP, "local_bhd"),
])
def test_trusted_budget_price_is_showable(query, amount, title, url, method):
    assert _show(query, _price(amount, method, url, title)) is True


# --- B. the floor FUNCTION itself is UNCHANGED (loose-path protection) -----
@pytest.mark.parametrize("query,amount,title,expect", [
    ("Lattafa Khamrah", 12.0, "Lattafa Khamrah 100ml", True),     # budget house STILL floored by the fn
    ("Rasasi Hawas For Him", 14.0, "Rasasi Hawas 100ml", True),
    ("Dior Sauvage", 12.0, "Dior Sauvage 100ml", True),
    ("Tom Ford Tobacco Vanille", 28.2, "Tom Ford Tobacco Vanille 100ml", True),
])
def test_floor_function_unchanged(query, amount, title, expect):
    # is_implausible_low_fragrance_price is reverted to the legacy designer floor —
    # it is the LOOSE-path guard and must be byte-identical to before.
    assert ps.is_implausible_low_fragrance_price(query, amount, title=title) is expect


# --- C. non-trusted budget prices STAY floored (not showable) -------------
def test_listing_url_budget_price_stays_floored():
    assert _show("Lattafa Khamrah", _price(12.0, "local_bhd", _LISTING, "Lattafa Khamrah")) is False


def test_estimated_budget_price_stays_floored():
    assert _show("Lattafa Khamrah", _price(12.0, "estimated", None, "Lattafa Khamrah")) is False


def test_converted_budget_price_stays_floored():
    assert _show("Lattafa Khamrah", _price(12.0, "converted_usd", _PDP, "Lattafa Khamrah")) is False


@pytest.mark.parametrize("query,title", [
    ("Ajmal Dahn Al Oudh", "Ajmal Dahn Al Oudh 100ml"),
    ("Ajmal Dahn Al Oudh Moattaq", "Ajmal Dahn Al Oudh Moattaq"),
    ("Rasasi Mukhallat", "Rasasi Mukhallat Oud Perfume Oil"),
    ("Lattafa Oud Mood Perfume Oil", "Lattafa Oud Mood Elixir Perfume Oil"),
    # alternate transliterations the round-2 review surfaced (must ALSO stay floored)
    ("Ajmal Dhan Al Oudh Moattaq", "Ajmal Dhan Al Oudh Moattaq 100ml"),
    ("Rasasi Muhallat Oud", "Rasasi Muhallat Oud Oil"),
    ("Al Haramain Ittar Al Kaaba", "Al Haramain Ittar Al Kaaba"),
    ("Ajmal Concentrated Oil CPO", "Ajmal Concentrated Perfume Oil CPO"),
])
def test_expensive_oil_line_stays_floored(query, title):
    # the houses' concentrated dehn-al-oud/mukhallat/oil lines keep the designer
    # floor even from a direct adapter, so a wrong-cheap oil scrape is still caught.
    assert _show(query, _price(8.0, "woo_store_api", _PDP, title)) is False


@pytest.mark.parametrize("amount", [0.1, 1.9, 3.0, 4.99])
def test_sub_artifact_floor_budget_price_stays_pended(amount):
    # ABSOLUTE artifact floor — even a TRUSTED genuine-PDP budget price below 5 BHD
    # is a scrape/fils-parse glitch (the exact-gate checks identity, not amount) and
    # must stay pended. The bypass lowers the floor 25 -> 5, never to 0.
    assert _show("Rasasi Hawas", _price(amount, "scrapedo_rendered", _PDP, "Rasasi Hawas EDP")) is False


def test_cheap_amber_oud_edp_still_shows():
    # "Amber Oud" is a cheap mainstream EDP spray, NOT a concentrated-oil line — a
    # bare "oud" token must NOT over-floor it (it is a hero SKU).
    assert _show("Al Haramain Amber Oud Gold Edition",
                 _price(22.0, "woo_store_api", _PDP, "Al Haramain Amber Oud Gold Edition (U) Edp 100ml")) is True


# --- D. designer/premium unaffected + collision token removed -------------
@pytest.mark.parametrize("query,title", [
    ("Chanel No 5", "Chanel No 5 EDP 100ml"),
    ("Dior Sauvage", "Dior Sauvage EDP 100ml"),
    ("Tom Ford Ombre Leather", "Tom Ford Ombre Leather 100ml"),
    ("Chanel my perfumes No 5", "Chanel No 5"),   # "my perfumes" must NOT trust a Chanel query
])
def test_designer_price_stays_floored(query, title):
    assert _show(query, _price(12.0, "shopify_json", _PDP, title)) is False


def test_my_perfumes_not_in_budget_set():
    assert "my perfumes" not in ps.BUDGET_FRAGRANCE_BRAND_KEYWORDS
    assert "myperfumes" not in ps.BUDGET_FRAGRANCE_BRAND_KEYWORDS


# --- E. flag OFF == legacy: budget houses floored again --------------------
def test_flag_off_floors_trusted_budget_price(monkeypatch):
    monkeypatch.setenv("ENABLE_BUDGET_FRAGRANCE_FLOOR", "false")
    assert _show("Lattafa Khamrah", _price(12.0, "shopify_json", _ALHAJIS, "Lattafa Khamrah Edp 100Ml")) is False
    assert _show("Rasasi Hawas For Him", _price(14.0, "woo_store_api", _PDP, "Rasasi Hawas 100ml")) is False


# --- helper contract -------------------------------------------------------
def test_trusted_helper_requires_all_conditions():
    # genuine + PDP + budget + not oil -> trusted
    assert ps._budget_house_trusted_price("Lattafa Khamrah", _price(12.0, "woo_store_api", _PDP, "Lattafa Khamrah 100ml")) is True
    # missing url -> not trusted
    assert ps._budget_house_trusted_price("Lattafa Khamrah", _price(12.0, "woo_store_api", None, "Lattafa Khamrah")) is False
    # non-budget brand -> not trusted
    assert ps._budget_house_trusted_price("Dior Sauvage", _price(12.0, "woo_store_api", _PDP, "Dior Sauvage")) is False
