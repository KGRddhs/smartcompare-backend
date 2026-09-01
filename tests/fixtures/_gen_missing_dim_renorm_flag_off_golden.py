"""One-shot generator for tests/fixtures/missing_dim_renorm_flag_off_golden.json.

Issue #101 gate: `scripts/verify_flag_byte_identity.py` does NOT apply (that
script exercises the price-EXTRACTION path only, and #101 touches none of it).
This golden is the mandatory equivalent: it pins `ScoringService.compute_scores`
output with ENABLE_MISSING_DIM_RENORM UNSET (flag OFF) across all 9 keys of
CATEGORY_DIMENSIONS, on a fixture that carries a ONE-SIDED missing gap (product
B has no rating / no review_count / no fact_check) so the flag-ON code path is
the one being held still.

Captured at dd4c849 (base of feature/m20-w2-truth-and-leaks), which is
code-identical to the review base 593ec1e for scoring_service.py.

Run from the repo root:

    python tests/fixtures/_gen_missing_dim_renorm_flag_off_golden.py

Kept in the tree so the golden can be regenerated deliberately (and so the
capture conditions are auditable), never run by pytest.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

os.environ.pop("ENABLE_MISSING_DIM_RENORM", None)

from app.services.scoring_service import ScoringService, CATEGORY_DIMENSIONS  # noqa: E402


def products(category):
    """A = fully measured, B = no rating / no review_count / no fact_check.

    Specs and price are IDENTICAL so the only difference between the two
    products is the presence of the review / popularity / reliability signals.
    """
    common_specs = {
        "ram": "8GB", "storage": "256GB", "longevity": "8 hours",
        "volume": "100 ml", "material": "cotton", "protein": "20 g",
    }
    return [
        {
            "brand": "Alpha", "name": "One", "category": category,
            "specs": dict(common_specs),
            "price": {"amount": 300, "currency": "BHD", "source_method": "local_bhd"},
            "rating": 2.0, "review_count": 300,
            "fact_check": {"specs_verified": 3},
        },
        {
            "brand": "Beta", "name": "Two", "category": category,
            "specs": dict(common_specs),
            "price": {"amount": 300, "currency": "BHD", "source_method": "local_bhd"},
            "rating": None, "review_count": None,
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
        "missing_dim_renorm_flag_off_golden.json",
    )
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(golden, fh, indent=2, sort_keys=True)
        fh.write("\n")
    print("wrote", out)


if __name__ == "__main__":
    main()
