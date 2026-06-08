"""Tests for scripts/research_goldtruth_seed.py pure helpers.

Plan: docs/plans/2026-06-08-backend-comparison-overhaul-plan.md § L4.3 (idle-time path b)

Network helpers (search_web) are exercised at runtime against Serper.
This file covers the pure helpers: extraction regex, range inference,
product split, BHD conversion.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "research_goldtruth_seed.py"


def _load():
    spec = importlib.util.spec_from_file_location("research_goldtruth_seed", SCRIPT_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["research_goldtruth_seed"] = mod
    spec.loader.exec_module(mod)
    return mod


mod = _load()


# ---------------------------------------------------------------------------
# Currency extraction
# ---------------------------------------------------------------------------

def test_extract_bhd_with_prefix():
    out = mod._extract_prices_from_text("Price BHD 24.500")
    assert any(abs(v - 24.5) < 0.01 for v, _ in out)


def test_extract_bhd_with_suffix():
    out = mod._extract_prices_from_text("24.500 BHD shipping included")
    assert any(abs(v - 24.5) < 0.01 for v, _ in out)


def test_extract_bd_short_form():
    out = mod._extract_prices_from_text("BD 12.5 only")
    assert any(abs(v - 12.5) < 0.01 for v, _ in out)


def test_extract_usd_converts_to_bhd():
    out = mod._extract_prices_from_text("Now only $10 on iHerb")
    # $10 * 0.377 = 3.77 BHD
    assert any(abs(v - 3.77) < 0.05 for v, _ in out)


def test_extract_aed_converts_to_bhd():
    out = mod._extract_prices_from_text("AED 100")
    # 100 * 0.103 = 10.30
    assert any(abs(v - 10.30) < 0.5 for v, _ in out)


def test_extract_sar_converts_to_bhd():
    out = mod._extract_prices_from_text("SAR 200")
    # 200 * 0.100 = 20.0
    assert any(abs(v - 20.0) < 0.5 for v, _ in out)


def test_extract_ignores_implausibly_large():
    out = mod._extract_prices_from_text("Reference: 999999 BHD")
    assert all(v < 10000 for v, _ in out)


def test_extract_ignores_trivial_small():
    out = mod._extract_prices_from_text("0.01 BHD")
    assert not out


def test_extract_no_match_returns_empty():
    assert mod._extract_prices_from_text("no prices here at all") == []


def test_extract_multiple_currencies():
    out = mod._extract_prices_from_text("Was $20, now BHD 7.50")
    bhd_values = [v for v, _ in out]
    # Both should be near 7.54 (USD→BHD) and 7.50 (direct BHD)
    assert any(abs(v - 7.5) < 0.5 for v in bhd_values)


# ---------------------------------------------------------------------------
# Range inference
# ---------------------------------------------------------------------------

def test_infer_range_empty_returns_none():
    assert mod._infer_range_from_prices([]) is None


def test_infer_range_single_value():
    r = mod._infer_range_from_prices([10.0])
    # 10 ± 10% pad
    assert r["min"] == 9.0
    assert r["max"] == 11.0
    assert r["currency"] == "BHD"


def test_infer_range_multiple_prices():
    r = mod._infer_range_from_prices([10, 12, 14, 16])
    # Range padded: min=10*0.9=9, max=16*1.1=17.6
    assert r["min"] == 9.0
    assert abs(r["max"] - 17.6) < 0.01


def test_infer_range_trims_outliers_when_n_ge_5():
    # n=10, trim=1: drops bottom 1, top 1
    prices = [1, 10, 11, 12, 13, 14, 15, 16, 17, 100]
    r = mod._infer_range_from_prices(prices)
    # After trim: [10..17]; pad: 9..18.7
    assert r["min"] == 9.0
    assert abs(r["max"] - 18.7) < 0.01


def test_infer_range_degenerate_zero_range_padded():
    # Same value twice → degenerate → fallback to ±15% midpoint pad
    r = mod._infer_range_from_prices([5.0, 5.0])
    assert r["max"] > r["min"]
    assert r["max"] - r["min"] >= 0.5


# ---------------------------------------------------------------------------
# Product split
# ---------------------------------------------------------------------------

def test_extract_two_products_basic():
    a, b = mod._extract_two_products("iPhone 15 vs Galaxy S24")
    assert a == "iPhone 15"
    assert b == "Galaxy S24"


def test_extract_two_products_case_insensitive():
    a, b = mod._extract_two_products("NOW Foods D3 VS Solgar D3")
    assert a == "NOW Foods D3"
    assert b == "Solgar D3"


def test_extract_two_products_strips_whitespace():
    a, b = mod._extract_two_products("  Tom Ford Black Orchid   vs   Creed Aventus  ")
    assert a == "Tom Ford Black Orchid"
    assert b == "Creed Aventus"


def test_extract_two_products_no_vs_returns_self():
    a, b = mod._extract_two_products("just one product")
    assert a == "just one product"
    assert b == "just one product"


def test_extract_two_products_first_vs_only():
    """Multi-vs queries split on the FIRST vs (rare but possible)."""
    a, b = mod._extract_two_products("A vs B vs C")
    assert a == "A"
    assert b == "B vs C"


# ---------------------------------------------------------------------------
# Currency conversion to BHD
# ---------------------------------------------------------------------------

def test_to_bhd_bhd_passthrough():
    assert mod._to_bhd(10.0, "BHD") == 10.0


def test_to_bhd_usd():
    assert mod._to_bhd(10.0, "USD") == pytest.approx(3.77, abs=0.01)


def test_to_bhd_aed():
    assert mod._to_bhd(100.0, "AED") == pytest.approx(10.3, abs=0.01)


def test_to_bhd_sar():
    assert mod._to_bhd(100.0, "SAR") == pytest.approx(10.0, abs=0.01)


def test_to_bhd_unknown_currency_passthrough():
    assert mod._to_bhd(10.0, "KWD") == 10.0


# ---------------------------------------------------------------------------
# RETAILER_QUERIES + EXTRA_RETAILERS_BY_CAT shape
# ---------------------------------------------------------------------------

def test_retailer_queries_have_lulu_sharaf_carrefour():
    retailers = {r for r, _ in mod.RETAILER_QUERIES}
    assert "lulu.com.bh" in retailers
    assert "sharafdg.com" in retailers
    assert "carrefourbh" in retailers


def test_extra_retailers_supplement_has_iherb_boots():
    retailers = {r for r, _ in mod.EXTRA_RETAILERS_BY_CAT["supplements"]}
    assert "bn.boots.com" in retailers
    assert "iherb.com" in retailers


def test_extra_retailers_skincare_has_boots():
    retailers = {r for r, _ in mod.EXTRA_RETAILERS_BY_CAT["skincare"]}
    assert "bn.boots.com" in retailers


def test_extra_retailers_unknown_category_handled_at_call_site():
    """The runner uses .get(category, []) — explicit None mapping not
    required; absence just means no extras."""
    assert mod.EXTRA_RETAILERS_BY_CAT.get("unknown_category", []) == []


# ---------------------------------------------------------------------------
# Safety: SERPER_API_KEY required for non-dry-run
# ---------------------------------------------------------------------------

def test_require_serper_key_raises_systemexit(monkeypatch):
    monkeypatch.delenv("SERPER_API_KEY", raising=False)
    with pytest.raises(SystemExit) as exc:
        mod._require_serper_key()
    assert exc.value.code == 3


def test_require_serper_key_passes_when_set(monkeypatch):
    monkeypatch.setenv("SERPER_API_KEY", "anything")
    # Should not raise
    mod._require_serper_key()
