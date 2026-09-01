"""One-shot generator for tests/fixtures/behavioral_flag_off_golden.json.

Captures `weights_used` + `scoring_method` from ScoringService.compute_scores
for the fixed profile+prefs fixture across all 9 categories, with
ENABLE_BEHAVIORAL_DIM_TRANSLATION unset (flag OFF). Run from the repo root:

    python tests/fixtures/_gen_behavioral_flag_off_golden.py

Kept in the tree so the golden can be regenerated deliberately (and so the
capture conditions are auditable), never run by pytest.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

os.environ.pop("ENABLE_BEHAVIORAL_DIM_TRANSLATION", None)

from app.services.scoring_service import ScoringService, CATEGORY_DIMENSIONS  # noqa: E402

PROFILE = {"dimension_sensitivity": {"spec_score": 0.7, "review_score": 0.2, "price_score": 0.1}}
PREFERENCES = {"priorities": ["quality"], "budget": "mid"}


def _products(category):
    return [
        {
            "brand": "Alpha", "name": "One", "category": category,
            "specs": {"ram": "6GB", "storage": "128GB"},
            "price": {"amount": 299, "currency": "BHD", "retailer": "Amazon", "estimated": False},
            "reviews": {"average_rating": 4.5, "total_reviews": 1200},
            "rating": 4.5, "review_count": 1200, "rating_verified": True,
            "rating_source": {"name": "Amazon"}, "fact_check": {},
        },
        {
            "brand": "Beta", "name": "Two", "category": category,
            "specs": {"ram": "8GB", "storage": "256GB"},
            "price": {"amount": 279, "currency": "BHD", "retailer": "Noon", "estimated": False},
            "reviews": {"average_rating": 4.3, "total_reviews": 800},
            "rating": 4.3, "review_count": 800, "rating_verified": True,
            "rating_source": {"name": "Noon"}, "fact_check": {},
        },
    ]


def main():
    service = ScoringService()
    golden = {}
    for category in sorted(CATEGORY_DIMENSIONS):
        result = service.compute_scores(
            _products(category),
            preferences=PREFERENCES,
            behavior_profile=PROFILE,
        )
        golden[category] = {
            "scoring_method": result["scoring_method"],
            "weights_used": result["scores"]["product_0"]["weights_used"],
        }
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "behavioral_flag_off_golden.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(golden, fh, indent=2, sort_keys=True)
        fh.write("\n")
    print("wrote", out)


if __name__ == "__main__":
    main()
