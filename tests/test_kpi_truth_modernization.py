"""KPI truth-set modernization (2026-07-02) — precision pins for the REPLACED
electronics SKUs, all through the REAL runtime matchers.

The 2026-06-27 electronics truth set was 4/6 stale at BH retail (iPad Air M2 /
MacBook Air M3 / Switch OLED discontinued; S24 base+Ultra carried but zero
in-stock+priced BH PDPs — live-probed sharafdg Algolia + extra Unbxd + noon).
Replacements: S25 / S25 Ultra / iPad Air 11 M3 / MacBook Air M5 512GB (the M5
line has no 256GB config; M4 256GB is OOS at both stores) / Switch 2. Fashion
queries were aligned to GCC listing names (GCC titles never carry the US
marketing names "Classic" / "Classic Fit" / "Flag Logo").

Every ACCEPT/REJECT below was reproduced through _selection_match /
strict_title_match against LIVE retailer titles (recon 2026-07-02). Correct
titles the CURRENT matcher over-rejects are pinned xfail — Wave B owns matcher
work; weakening the matcher here would reopen the PR#9 leak classes.
"""
import io
import json

import pytest

from app.services.price_service import _selection_match, strict_title_match

_TRUTH = "data/usable_exact_genuine_truth.json"


@pytest.fixture(autouse=True)
def _gate_on(monkeypatch):
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "true")


def _sel(query, title, candidate_brand=""):
    return _selection_match(query, title, "electronics", candidate_brand=candidate_brand)


# ---------------------------------------------------------------------------
# Truth-file content — guards an accidental revert to the retired SKUs
# ---------------------------------------------------------------------------

def test_truth_file_carries_the_modernized_queries():
    data = json.load(io.open(_TRUTH, encoding="utf-8"))
    queries = {p["id"]: p["query"] for p in data["products"]}
    assert queries["kpi-elec-001"] == "iPhone 15 256GB"  # unchanged (still sold)
    assert queries["kpi-elec-002"] == "Samsung Galaxy S25 256GB"
    assert queries["kpi-elec-003"] == "Samsung Galaxy S25 Ultra 256GB"
    assert queries["kpi-elec-004"] == "Apple iPad Air 11-inch M3 128GB"
    assert queries["kpi-elec-005"] == "MacBook Air 13 M5 512GB"
    assert queries["kpi-elec-006"] == "Nintendo Switch 2"
    assert queries["kpi-fash-004"] == "Ray-Ban Aviator RB3025"
    assert queries["kpi-fash-005"] == "Lacoste L1212 Polo"
    assert queries["kpi-fash-006"] == "Tommy Hilfiger Essential Flag T-Shirt"


# ---------------------------------------------------------------------------
# (a) Switch 2 — games/bundles rank ABOVE the console at sharafdg/noon and
# "game" is NOT in ACCESSORY_KEYWORDS (the genuine console title contains
# "Gaming"); correctness rests on the _selection_match token-add rejection.
# ---------------------------------------------------------------------------

def test_switch2_rejects_games_and_bundle():
    assert _sel("Nintendo Switch 2", "Nintendo Switch 2 NBA 2K26 Game") is False
    assert _sel("Nintendo Switch 2",
                "Nintendo Switch 2 Mario Kart World Racing Game") is False
    assert _sel("Nintendo Switch 2",
                "Nintendo Switch 2 + Mario Kart World Bundle") is False


def test_switch2_accepts_sharafdg_console_title():
    # live sharafdg title, 225 BHD in_stock=1
    assert _sel("Nintendo Switch 2", "Nintendo Switch 2 Gaming Console 256GB Black") is True


@pytest.mark.xfail(
    reason="matcher over-rejection (Wave B): 'Light' in extra.com's colourway "
    "'Light Blue and Light Red' reads as a variant qualifier (Switch-Lite "
    "class) instead of a colour modifier — bisect-proven: 'Nintendo Switch 2 "
    "Blue' passes, '... Light' alone fails. Do NOT fix by weakening the "
    "variant-add guard (it is what rejects the games/bundle above).",
    strict=True,
)
def test_switch2_accepts_extra_console_title():
    # live extra.com title, 209.99 BHD inStockFlag=true
    assert _sel("Nintendo Switch 2", "Nintendo Switch 2, Light Blue and Light Red") is True


def test_switch2_truth_query_must_not_carry_console_token():
    """WHY the truth query is 'Nintendo Switch 2' with no 'Console': extra's
    genuine title has no console token, so a Console-carrying query fails the
    query-subset gate against it (both matchers agree)."""
    extra_title = "Nintendo Switch 2, Light Blue and Light Red"
    assert _sel("Nintendo Switch 2 Console", extra_title) is False
    assert strict_title_match("Nintendo Switch 2 Console", extra_title) is False


# ---------------------------------------------------------------------------
# (b) Galaxy S25 flankers — both directions
# ---------------------------------------------------------------------------

def test_s25_rejects_fe_and_ultra_flankers():
    assert _sel("Samsung Galaxy S25 256GB", "Samsung Galaxy S25 FE 256GB") is False
    assert _sel("Samsung Galaxy S25 256GB", "Samsung Galaxy S25 Ultra 256GB") is False


def test_s25_ultra_rejects_base_model_title():
    # reverse direction: the Ultra query must not take a base-model PDP
    assert _sel("Samsung Galaxy S25 Ultra 256GB",
                "Samsung Galaxy S25 5G 256GB 12GB RAM") is False


def test_s25_accepts_descriptive_bh_title():
    # 5G/RAM adds are padding — guards that the flanker rejects above are not
    # a matcher that rejects everything
    assert _sel("Samsung Galaxy S25 256GB",
                "Samsung Galaxy S25 5G 256GB 12GB RAM") is True


@pytest.mark.xfail(
    reason="matcher over-rejection (Wave B): the live sharafdg title fails on "
    "the concatenated colourway 'Icyblue' + marketing token 'AI' (bisect-"
    "proven: '... 5G 256GB 12GB RAM' passes; '... Icyblue' or '... AI "
    "Smartphone' alone fail) — neither is in the electronics padding vocab.",
    strict=True,
)
def test_s25_accepts_live_sharafdg_title():
    # live sharafdg title, 359.99 BHD in_stock=1
    assert _sel(
        "Samsung Galaxy S25 256GB",
        "Samsung Galaxy S25 5G 256GB 12GB RAM Icyblue AI Smartphone Middle East Version",
    ) is True


# ---------------------------------------------------------------------------
# (c) iPad Air 11 M3 — brand-omitted BH titles need candidate_brand
# ---------------------------------------------------------------------------

def test_ipad_m3_accepts_brand_omitted_descriptive_title():
    assert _sel("Apple iPad Air 11-inch M3 128GB",
                "iPad Air 11-inch M3 Wi-Fi 128GB Space Grey",
                candidate_brand="Apple") is True


@pytest.mark.xfail(
    reason="matcher over-rejection (Wave B): the live sharafdg title fails on "
    "the model-year token '(2025)' — an added numeric the query does not "
    "state (bisect-proven: identical title without '(2025)' passes).",
    strict=True,
)
def test_ipad_m3_accepts_live_sharafdg_title():
    # live sharafdg title, 240.99 BHD in_stock=1
    assert _sel(
        "Apple iPad Air 11-inch M3 128GB",
        "iPad Air 11-inch M3 (2025) Wi-Fi 128GB - Space Grey Middle East Version with FaceTime",
        candidate_brand="Apple",
    ) is True


def test_ipad_m3_rejects_the_m2_predecessor():
    # chip axis, not the year token: the clean M2 title also rejects
    assert _sel(
        "Apple iPad Air 11-inch M3 128GB",
        "iPad Air 11-inch M2 (2024) Wi-Fi 128GB - Space Grey Middle East Version with FaceTime",
        candidate_brand="Apple",
    ) is False
    assert _sel("Apple iPad Air 11-inch M3 128GB",
                "iPad Air 11-inch M2 Wi-Fi 128GB Space Grey",
                candidate_brand="Apple") is False


# ---------------------------------------------------------------------------
# (d) MacBook Air M5 — chip-tier discrimination
# ---------------------------------------------------------------------------

@pytest.mark.xfail(
    reason="matcher over-rejection (Wave B): the live extra.com title fails on "
    "the spelled screen unit 'Inch' — the query's bare '13' parses no inch "
    "axis, so '13 Inch' reads as an added axis (bisect-proven: 'APPLE MacBook "
    "Air M5 512GB 13' passes, '... 13 Inch' fails).",
    strict=True,
)
def test_mba_m5_accepts_live_extra_title():
    # live extra.com title, 609.99 BHD inStockFlag=true
    assert _sel(
        "MacBook Air 13 M5 512GB",
        "APPLE MacBook Air, M5, 16GB, 512GB SSD, 13 Inch IPS, 8 Core GPU, Silver",
        candidate_brand="Apple",
    ) is True


def test_mba_m5_rejects_m4_on_chip_axis():
    # M4 title WITHOUT the Inch token — rejects on the chip axis alone
    assert _sel("MacBook Air 13 M5 512GB",
                "APPLE MacBook Air M4 512GB 13", candidate_brand="Apple") is False
    # the same clean shape with M5 passes, so the reject above IS the chip
    assert _sel("MacBook Air 13 M5 512GB",
                "APPLE MacBook Air M5 512GB 13", candidate_brand="Apple") is True
