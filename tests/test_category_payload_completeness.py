"""Phase 3.2 Task #4 — category_profile payload completeness (Contract 1).

Each product emits `category_profile = {category, fields: [{key, label, value}]}`
— ordered per CATEGORY_SPEC_SCHEMAS, cleaned (no N/A/null/object), with a
copy-policy-safe English label. SYMMETRY: both products built from the same
ordered key set; a product omits a field it lacks (no blank second product).
Hidden (fields == []) when nothing populates.

Grounded in the real Phase-0 prod fixtures (fragrances/electronics/fashion).
"""

import json
import os

import pytest

from app.services.extraction_service import (
    build_category_profile,
    CATEGORY_SPEC_SCHEMAS,
    canonicalize_category,
)

_FIXTURE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "..", "smartcompare", ".qa-bias-rerun", "_discovery", "prod",
)


def _load_fixture(name):
    path = os.path.join(_FIXTURE_DIR, f"{name}.json")
    if not os.path.exists(path):
        pytest.skip(f"prod fixture {name}.json not present")
    with open(path, encoding="utf-8") as f:
        return json.load(f)["body"]


# ------------------------------------------------------- shape + cleaning ---

class TestCategoryProfileShape:
    def test_shape_keys(self):
        specs = {"scent_family": "Amber", "notes_top": "Bergamot", "longevity": "8 hours"}
        prof = build_category_profile("fragrances", specs)
        assert prof["category"] == "fragrances"
        assert isinstance(prof["fields"], list)
        for f in prof["fields"]:
            assert set(f.keys()) == {"key", "label", "value"}

    def test_na_values_filtered(self):
        specs = {"scent_family": "N/A", "notes_top": "Bergamot", "longevity": "none",
                 "sillage": "", "season": None}
        prof = build_category_profile("fragrances", specs)
        keys = [f["key"] for f in prof["fields"]]
        assert "notes_top" in keys
        assert "scent_family" not in keys  # N/A filtered
        assert "longevity" not in keys     # "none" filtered
        assert "sillage" not in keys       # "" filtered
        assert "season" not in keys        # None filtered

    def test_internal_fields_filtered(self):
        specs = {"notes_top": "Bergamot", "_field_confidence": {"notes_top": "snippet"}}
        prof = build_category_profile("fragrances", specs)
        keys = [f["key"] for f in prof["fields"]]
        assert "notes_top" in keys
        assert "_field_confidence" not in keys

    def test_object_values_filtered(self):
        specs = {"notes_top": "Bergamot", "weird": {"nested": 1}}
        prof = build_category_profile("electronics", specs)
        keys = [f["key"] for f in prof["fields"]]
        assert "weird" not in keys

    def test_empty_specs_empty_fields(self):
        assert build_category_profile("fragrances", {})["fields"] == []
        assert build_category_profile("fragrances", None)["fields"] == []

    def test_ordered_per_schema(self):
        # Fields come back in CATEGORY_SPEC_SCHEMAS declared order, not dict order.
        specs = {"longevity": "8h", "scent_family": "Amber", "notes_top": "Bergamot"}
        prof = build_category_profile("fragrances", specs)
        keys = [f["key"] for f in prof["fields"]]
        # schema order: scent_family, notes_top, ..., longevity
        assert keys.index("scent_family") < keys.index("notes_top") < keys.index("longevity")


# ------------------------------------------------------------- i18n labels ---

class TestLabels:
    def test_humanized_default(self):
        prof = build_category_profile("fragrances", {"scent_family": "Amber"})
        label = prof["fields"][0]["label"]
        assert label == "Scent family"

    def test_override_special_cases(self):
        # ram -> RAM, os -> OS, notes_top -> Top notes
        e = build_category_profile("electronics", {"ram": "8 GB", "os": "Android 14"})
        labels = {f["key"]: f["label"] for f in e["fields"]}
        assert labels["ram"] == "RAM"
        assert labels["os"] == "OS"
        f = build_category_profile("fragrances", {"notes_top": "Bergamot"})
        assert f["fields"][0]["label"] == "Top notes"

    def test_labels_copy_policy_safe(self):
        # No banned vocab in any emitted label across all categories.
        banned = ["best for", "winner", "beats", "excellent", "best pick", "we recommend"]
        for cat, schema in CATEGORY_SPEC_SCHEMAS.items():
            specs = {k: "x" for k in schema}
            prof = build_category_profile(cat, specs)
            for fobj in prof["fields"]:
                low = fobj["label"].lower()
                for b in banned:
                    assert b not in low, f"{cat}.{fobj['key']} label '{fobj['label']}' has banned '{b}'"


# ----------------------------------------------- canonicalization keystone ---

class TestCanonicalization:
    def test_capital_category_routes_correctly(self):
        # "Fragrances" (capital — the LLM form) must route to the fragrance schema
        # (the keystone bug: it fell to "other" → wrong fields).
        prof = build_category_profile("Fragrances", {"scent_family": "Amber", "notes_top": "Bergamot"})
        assert prof["category"] == "fragrances"
        keys = [f["key"] for f in prof["fields"]]
        assert "scent_family" in keys and "notes_top" in keys


# ----------------------------------------------- real prod fixture symmetry ---

class TestProdFixtureSymmetry:
    def test_fragrance_both_products_populate(self):
        body = _load_fixture("fragrances")
        category = canonicalize_category(body.get("category"))
        profiles = [
            build_category_profile(category, p.get("specs"))
            for p in body["specs"]["products"]
        ]
        # Both products produce a non-empty category_profile (no blank 2nd product).
        for prof in profiles:
            assert len(prof["fields"]) >= 3
        # No raw "N/A" leaks into any value.
        for prof in profiles:
            for f in prof["fields"]:
                assert f["value"].lower() not in ("n/a", "na", "none", "")

    def test_electronics_both_products_populate(self):
        body = _load_fixture("electronics")
        category = canonicalize_category(body.get("category"))
        for p in body["specs"]["products"]:
            prof = build_category_profile(category, p.get("specs"))
            assert len(prof["fields"]) >= 4

    def test_fashion_no_blank_second_product(self):
        # F3.1 — the asymmetric-field case. Each product renders its OWN populated
        # subset; neither comes back empty (no blank second product).
        body = _load_fixture("fashion")
        category = canonicalize_category(body.get("category"))
        profiles = [
            build_category_profile(category, p.get("specs"))
            for p in body["specs"]["products"]
        ]
        for prof in profiles:
            assert len(prof["fields"]) >= 1  # neither product is blank


class TestCategoryProfileInResponse:
    def test_category_profile_on_products(self):
        from app.services.response_builder import build_comparison_response
        product_data = [
            {
                "brand": "Tom Ford", "name": "Ombre Leather", "category": "fragrances",
                "price": {"amount": 100.0, "currency": "BHD", "source_method": "page_scrape_jsonld"},
                "specs": {"scent_family": "Leather", "notes_top": "Cardamom", "longevity": "6 hours"},
                "reviews": {},
            },
            {
                "brand": "Tom Ford", "name": "Tobacco Vanille", "category": "fragrances",
                "price": {"amount": 118.0, "currency": "BHD", "source_method": "page_scrape_jsonld"},
                "specs": {"scent_family": "Oriental", "notes_top": "Tobacco", "longevity": "all day"},
                "reviews": {},
            },
        ]
        comparison = {"winner_index": 0, "winner_declaration": "Ombre Leather",
                      "winner_reason": "x", "specs_comparison": {}}
        resp = build_comparison_response(
            query="Ombre Leather vs Tobacco Vanille",
            product_data=product_data, comparison=comparison,
            scoring_result={}, category_used="fragrances", region="bahrain",
            elapsed_seconds=1.0, api_calls=0, total_cost=0.0, gpt_calls=0, serper_calls=0,
        )
        for p in resp["products"]:
            assert "category_profile" in p
            cp = p["category_profile"]
            assert cp["category"] == "fragrances"
            assert len(cp["fields"]) >= 3
            keys = [f["key"] for f in cp["fields"]]
            assert "scent_family" in keys and "notes_top" in keys

    def test_category_profile_falls_back_to_category_used(self):
        # A product missing its own `category` uses the response-level
        # category_used so both products key the same schema (symmetry).
        from app.services.response_builder import build_comparison_response
        product_data = [
            {"brand": "A", "name": "X",
             "price": {"amount": 100.0, "currency": "BHD", "source_method": "page_scrape_jsonld"},
             "specs": {"scent_family": "Amber", "notes_top": "Bergamot"}, "reviews": {}},
            {"brand": "B", "name": "Y",
             "price": {"amount": 90.0, "currency": "BHD", "source_method": "page_scrape_jsonld"},
             "specs": {"scent_family": "Woody", "notes_top": "Cedar"}, "reviews": {}},
        ]
        comparison = {"winner_index": 0, "winner_declaration": "X", "winner_reason": "x", "specs_comparison": {}}
        resp = build_comparison_response(
            query="X vs Y", product_data=product_data, comparison=comparison,
            scoring_result={}, category_used="fragrances", region="bahrain",
            elapsed_seconds=1.0, api_calls=0, total_cost=0.0, gpt_calls=0, serper_calls=0,
        )
        for p in resp["products"]:
            assert p["category_profile"]["category"] == "fragrances"
