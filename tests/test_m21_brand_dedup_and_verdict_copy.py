# tests/test_m21_brand_dedup_and_verdict_copy.py
"""M21 W3 quality unit `brand-dedup` (M18 findings PO-verdict-text-05,
PO-recorded-13, PO-verdict-text-04, PO-verdict-text-12).

Three defect families:
  A. Doubled brand in user-facing copy ("TOM FORD TOM FORD OUD WOOD 100 ML")
     from un-deduped `f"{brand} {name}"` concatenation. ONE shared helper
     (text_sanitize.dedup_brand_name) applied at the display-name sites:
     scoring_service._product_name_for_evidence (winner_evidence lines),
     structured_comparison_service product_names (sync + streaming, via
     _display_product_names) and the per-product full_name/display_name
     assembly (_product_display_identity).
  B. Fact-check INTERNALS leaking into user-facing cons ("Price deviation of
     53.9% from expected") -- the text_sanitize scrub provably missed them
     (M18 probe: has_score_internals() == False for the shipped strings), and
     the verdict prompt dumped the whole product dict incl. fact_check.
  C. Verdict calibration coverage: 4 of 9 categories injected NO exemplar or
     anti-pattern at all, and no anti-pattern targeted the dominant recorded
     failure mode (score-margin cited as the "why").
"""
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent


# ===========================================================================
# A. The shared dedup helper -- snapshot tests
# ===========================================================================

DEDUP_CASES = [
    # (brand, name, expected)
    ("Apple", "iPhone 15 Pro", "Apple iPhone 15 Pro"),          # plain concat
    ("Apple", "Apple iPhone 15 Pro", "Apple iPhone 15 Pro"),    # name already branded
    ("TOM FORD", "TOM FORD OUD WOOD 100 ML", "TOM FORD OUD WOOD 100 ML"),
    # Case-insensitive match keeps the NAME's own casing untouched.
    ("Tom Ford", "TOM FORD OUD WOOD", "TOM FORD OUD WOOD"),
    # Token boundary: "Applesauce" is NOT the brand "Apple".
    ("Apple", "Applesauce Maker", "Apple Applesauce Maker"),
    # Internal repeat collapses to a single brand occurrence.
    ("HealthAid", "HealthAid HealthAid Vitamin D3 1000 IU",
     "HealthAid Vitamin D3 1000 IU"),
    ("Louis Vuitton", "Louis Vuitton LV Vers Mesh Cap",
     "Louis Vuitton LV Vers Mesh Cap"),
    ("", "iPhone 15", "iPhone 15"),                             # no brand
    ("Apple", "", "Apple"),                                     # no name
    ("", "", ""),                                               # nothing
    ("Apple", "apple", "apple"),                                # name == brand
    (None, "iPhone 15", "iPhone 15"),                           # None-tolerant
    ("Apple", None, "Apple"),
]


@pytest.mark.parametrize("brand,name,expected", DEDUP_CASES)
def test_dedup_brand_name_snapshot(brand, name, expected):
    from app.services.text_sanitize import dedup_brand_name
    assert dedup_brand_name(brand, name) == expected


# ===========================================================================
# A. Site 1 -- scoring_service winner_evidence lines
# ===========================================================================

def test_product_name_for_evidence_dedups_brand():
    from app.services import scoring_service as ss
    got = ss._product_name_for_evidence(
        {"brand": "TOM FORD", "name": "TOM FORD OUD WOOD 100 ML"}
    )
    assert got == "TOM FORD OUD WOOD 100 ML"


def test_product_name_for_evidence_keeps_fallback():
    from app.services import scoring_service as ss
    assert ss._product_name_for_evidence({}) == "the winning option"
    assert ss._product_name_for_evidence(
        {"brand": "Apple", "name": "iPhone 15"}
    ) == "Apple iPhone 15"


def test_winner_evidence_line_carries_single_brand():
    """End-to-end through build_winner_evidence -- the exact recorded shape
    ('TOM FORD TOM FORD OUD WOOD 100 ML leads on the overall picture')."""
    from app.services import scoring_service as ss
    win = {
        "brand": "TOM FORD", "name": "TOM FORD OUD WOOD 100 ML",
        "price": {"amount": 100.0, "currency": "BHD", "source_method": "local_bhd"},
    }
    run = {
        "brand": "Other", "name": "Thing",
        "price": {"amount": 90.0, "currency": "BHD", "source_method": "estimated"},
    }
    ev = ss.build_winner_evidence([win, run], {}, 0, "fragrances")
    assert ev, "expected at least one evidence line (real price vs estimate)"
    assert ev[0].startswith("TOM FORD OUD WOOD 100 ML "), ev[0]
    assert "TOM FORD TOM FORD" not in ev[0]


# ===========================================================================
# A. Sites 2+3 -- product_names in both orchestrator paths
# ===========================================================================

def test_display_product_names_dedup():
    from app.services.structured_comparison_service import _display_product_names
    pd = [
        {"brand": "TOM FORD", "name": "TOM FORD SOLEIL NEIGE 100ML"},
        {"brand": "Apple", "name": "iPhone 15"},
    ]
    assert _display_product_names(pd) == [
        "TOM FORD SOLEIL NEIGE 100ML", "Apple iPhone 15",
    ]


def test_both_orchestrator_paths_use_display_product_names():
    """Wiring pin: the sync AND streaming product_names constructions both go
    through the shared helper (the raw doubled comprehension is gone)."""
    src = (REPO / "app" / "services" / "structured_comparison_service.py").read_text(
        encoding="utf-8"
    )
    assert src.count("_display_product_names(product_data)") >= 2, (
        "both product_names sites must call _display_product_names"
    )


# ===========================================================================
# A. Site 4 -- per-product full_name / display_name (vision doubling root)
# ===========================================================================

def test_product_display_identity_vision_dedups():
    """Vision products previously got full_name = display_name = search_query
    (= '{brand} {name}' with a camera-model name that already starts with the
    brand) -- the deterministic 'TOM FORD TOM FORD ...' constructor."""
    from app.services.structured_comparison_service import _product_display_identity
    full, disp = _product_display_identity(
        brand="TOM FORD", name="TOM FORD OUD WOOD 100 ML", variant=None,
        search_query="TOM FORD TOM FORD OUD WOOD 100 ML", is_vision=True,
    )
    assert full == "TOM FORD OUD WOOD 100 ML"
    assert disp == "TOM FORD OUD WOOD 100 ML"


def test_product_display_identity_text_path_shape_preserved():
    from app.services.structured_comparison_service import _product_display_identity
    full, disp = _product_display_identity(
        brand="Apple", name="iPhone 15", variant="256GB",
        search_query="Apple iPhone 15 256GB", is_vision=False,
    )
    assert full == "Apple iPhone 15 256GB"
    assert disp == "iPhone 15"


def test_product_display_identity_text_path_dedups_branded_name():
    """The recorded 'HealthAid HealthAid Vitamin D3 1000 IU' shape: the text
    parser CAN emit a brand-prefixed name; full_name must not double it."""
    from app.services.structured_comparison_service import _product_display_identity
    full, _disp = _product_display_identity(
        brand="HealthAid", name="HealthAid Vitamin D3", variant="1000 IU",
        search_query="", is_vision=False,
    )
    assert full == "HealthAid Vitamin D3 1000 IU"


def test_fetch_product_data_wired_to_identity_helper():
    src = (REPO / "app" / "services" / "structured_comparison_service.py").read_text(
        encoding="utf-8"
    )
    assert "_product_display_identity(" in src.replace(
        "def _product_display_identity(", ""
    ), "identity assembly site must call _product_display_identity"


# ===========================================================================
# B. Fact-check internals -- scrub patterns (the M18 probe strings verbatim)
# ===========================================================================

@pytest.mark.parametrize("leak", [
    "Price deviation of 53.9% from expected.",
    "Price deviation of 44% from verified sources.",
    "Soleil Neige scores 73.8 overall.",
])
def test_fact_check_internals_now_detected(leak):
    from app.services.text_sanitize import has_score_internals, strip_score_internals
    assert has_score_internals(leak), leak
    assert strip_score_internals(leak) == ""


@pytest.mark.parametrize("clean", [
    "Longer-lasting on skin with a warmer drydown.",
    "It scores well with reviewers.",          # no digit -> not an internal
    "Rated 4.5 stars by verified buyers.",
    "Ships in a 100 ml bottle.",
])
def test_clean_facts_still_pass(clean):
    from app.services.text_sanitize import has_score_internals, strip_score_internals
    assert not has_score_internals(clean), clean
    assert strip_score_internals(clean) == clean


# ===========================================================================
# B. Root cause -- the verdict prompt must not dump fact_check / _-diag keys
# ===========================================================================

def test_verdict_safe_product_strips_fact_check_and_diag_keys():
    from app.services.extraction_service import _verdict_safe_product
    p = {
        "name": "Soleil Neige",
        "full_name": "TOM FORD SOLEIL NEIGE 100ML",
        "specs": {"concentration": "EDP"},
        "fact_check": {"price_deviation_pct": 53.9, "specs_verified": 2},
        "_search_snippets": ["snippet"],
        "_cached": True,
    }
    out = _verdict_safe_product(p, "fragrances")
    assert "fact_check" not in out
    assert not any(k.startswith("_") for k in out), sorted(out)
    # Retained content untouched; original dict NOT mutated (copy-on-write).
    assert out["specs"] == {"concentration": "EDP"}
    assert p["fact_check"] == {"price_deviation_pct": 53.9, "specs_verified": 2}
    assert "_search_snippets" in p


def test_verdict_safe_product_identity_preserved_when_nothing_to_strip():
    """No fact_check / _-keys and a showable-or-absent price -> the SAME object
    comes back (pre-existing copy-on-write contract stays intact)."""
    from app.services.extraction_service import _verdict_safe_product
    p = {"name": "X", "full_name": "B X", "specs": {"a": 1}}
    assert _verdict_safe_product(p, "fragrances") is p


# ===========================================================================
# C. Verdict calibration coverage (data/verdict_exemplars.json)
# ===========================================================================

ALL_CATEGORIES = [
    "electronics", "grocery", "supplements", "makeup", "skincare",
    "haircare", "fragrances", "fashion", "other",
]


@pytest.fixture(autouse=True)
def _reset_exemplar_cache():
    from app.services import verdict_exemplar_loader as vel
    vel.reset_cache()
    yield
    vel.reset_cache()


def _exemplar_data():
    return json.loads(
        (REPO / "data" / "verdict_exemplars.json").read_text(encoding="utf-8")
    )


@pytest.mark.parametrize("category", ALL_CATEGORIES)
def test_no_category_injects_zero_calibration(category):
    """PO-verdict-text-12: build_exemplar_block must never return '' for a live
    category (supplements/haircare/fashion/other previously got 0 chars)."""
    from app.services import verdict_exemplar_loader as vel
    data = _exemplar_data()
    assert data[category].get("anti_patterns"), f"{category}: no anti_patterns"
    block = vel.build_exemplar_block(category)
    assert block != "", f"{category}: empty calibration block"
    assert "ANTI-PATTERN" in block


@pytest.mark.parametrize("category", ALL_CATEGORIES)
def test_margin_is_not_a_reason_anti_pattern_everywhere(category):
    """The dominant recorded failure mode (winner_reason built from internal
    margins: 'wins with a 24.4 point higher score') gets a named anti-pattern
    in EVERY category."""
    data = _exemplar_data()
    names = " ".join(
        ap.get("name", "").lower()
        for ap in data[category].get("anti_patterns", [])
    )
    assert "margin" in names, f"{category}: no margin anti-pattern"


def test_new_anti_patterns_carry_no_forbidden_vocab():
    """Mirror of the S2 I2.6 audit for the NEW rows: no scary copy, no
    'estimated', and every AP has name+rule."""
    forbidden = ["estimated", "reference price", "couldn't", "try again",
                 "failed to", "unable to"]
    data = _exemplar_data()
    for cat in ALL_CATEGORIES:
        for ap in data[cat].get("anti_patterns", []):
            assert ap.get("name") and ap.get("rule"), (cat, ap)
            low = f"{ap['name']} {ap['rule']}".lower()
            for bad in forbidden:
                assert bad not in low, (cat, ap["name"], bad)
