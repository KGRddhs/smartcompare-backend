"""One-shot generator for tests/fixtures/spec_field_norm_flag_off_golden.json.

Issue #100 gate: `scripts/verify_flag_byte_identity.py` does NOT apply (that
script exercises `price_service.extract_price_from_html` only, and #100 is
downstream of price extraction and touches no extractor). This golden is the
mandatory equivalent: it pins `ScoringService.compute_scores` output with
ENABLE_SPEC_FIELD_NORM UNSET (flag OFF) across all 9 keys of
CATEGORY_DIMENSIONS.

The fixture is deliberately the WORST case for the flag: the two products
differ by spec NOTATION (`5000mAh` vs `Up to 29 hours video playback`), by raw
magnitude (12/256 vs 8/128) and by COVERAGE (B omits two fields), so every
branch the flag adds is exercised — and the golden proves none of it moves the
flag-OFF numbers.

Captured at dd4c849 (base of feature/m20-w2-truth-and-leaks) + the #101
exclude-and-renormalize edit already applied in this worktree. #101's own flag
(ENABLE_MISSING_DIM_RENORM) is popped below so both flags are OFF here, which
is code-identical to the review base 593ec1e for this fixture.

Run from the repo root:

    python tests/fixtures/_gen_spec_field_norm_flag_off_golden.py

Kept in the tree so the golden can be regenerated deliberately (and so the
capture conditions are auditable), never run by pytest.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

os.environ.pop("ENABLE_SPEC_FIELD_NORM", None)
os.environ.pop("ENABLE_MISSING_DIM_RENORM", None)

from app.services.scoring_service import ScoringService, CATEGORY_DIMENSIONS  # noqa: E402

# One spec dict wide enough to populate several fields of EVERY category
# schema in app/services/extraction_service.py:CATEGORY_SPEC_SCHEMAS.
SPECS_A = {
    "display": "6.7-inch OLED", "processor": "Snapdragon 8 Gen 3",
    "ram": "12GB", "storage": "256GB", "battery": "5000mAh",
    "rear_camera": "50MP", "front_camera": "12MP",
    "count": "60 capsules", "size": "500 g", "nutrition_protein": "20 g",
    "nutrition_calories": "150 kcal", "dosage": "1000 mg",
    "serving_size": "2 capsules",
    "spf": "50", "volume": "100 ml", "shade_range": "40 shades",
    "longevity": "8 hours", "sillage": "moderate",
    "concentration": "eau de parfum",
    "material": "100% cotton", "weight": "180 g", "color": "black",
}

# Same product family, different NOTATION + lower magnitudes + 2 fields absent.
SPECS_B = dict(SPECS_A)
SPECS_B["battery"] = "Up to 29 hours video playback"
SPECS_B["ram"] = "8GB"
SPECS_B["storage"] = "128GB"
SPECS_B["volume"] = "50 ml"
SPECS_B["longevity"] = "6 hours"
del SPECS_B["color"]
del SPECS_B["sillage"]


def products(category):
    return [
        {
            "brand": "Alpha", "name": "One", "category": category,
            "specs": dict(SPECS_A),
            "price": {"amount": 300, "currency": "BHD", "source_method": "local_bhd"},
            "rating": 4.5, "review_count": 800,
            "fact_check": {"specs_verified": 3},
        },
        {
            "brand": "Beta", "name": "Two", "category": category,
            "specs": dict(SPECS_B),
            "price": {"amount": 300, "currency": "BHD", "source_method": "local_bhd"},
            "rating": 4.7, "review_count": 1500,
            "fact_check": {"specs_verified": 3},
        },
    ]


def capture(category):
    service = ScoringService()
    result = service.compute_scores(products(category))
    return {
        "winner_index": result["winner_index"],
        "win_margin": result["win_margin"],
        "scores": result["scores"],
    }


def main():
    golden = {category: capture(category) for category in sorted(CATEGORY_DIMENSIONS)}
    out = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "spec_field_norm_flag_off_golden.json",
    )
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(golden, fh, indent=2, sort_keys=True)
        fh.write("\n")
    print("wrote", out)


if __name__ == "__main__":
    main()
