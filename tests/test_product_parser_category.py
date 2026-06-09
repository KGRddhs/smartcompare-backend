"""B0-A BUG #1 regression — appliance/electronics category drift.

Symptom: "Carrier 1.5T AC vs LG 1.5T AC" was routing to category="other"
instead of "electronics", giving GCC users (huge AC market) generic dims
(function/build/reliability) instead of the proper electronics dims
(performance/value/build_quality/feature/ecosystem/futureproof).

Fix: PRODUCT_PARSER_PROMPT electronics enum now explicitly lists home
appliances (AC, refrigerator, washing machine, dryer, vacuum) so the
gpt-4o-mini parser routes them correctly.

Two layers of test:
  * Static (free) — prompt string contains the appliance keywords.
  * live_unit — parametrized over 8 product types asserting each parses
    as "electronics" via the real OpenAI gpt-4o-mini call.
"""
import pytest

from app.services.extraction_service import PRODUCT_PARSER_PROMPT, parse_product_query


# ---------- Static prompt-content guards (free, no API) ----------

APPLIANCE_KEYWORDS = [
    "air conditioner",  # AC
    "refrigerator",     # fridge / freezer
    "washing machine",
    "dryer",
    "vacuum",
]


@pytest.mark.parametrize("keyword", APPLIANCE_KEYWORDS)
def test_parser_prompt_includes_appliance_keyword(keyword):
    """Static guard — every appliance keyword listed under electronics."""
    assert keyword.lower() in PRODUCT_PARSER_PROMPT.lower(), (
        f"PRODUCT_PARSER_PROMPT missing '{keyword}' — appliance category drift "
        "regression. See B0-A BUG #1."
    )


def test_parser_prompt_appliance_keywords_appear_in_electronics_block():
    """Drift-guard — appliances must be on the SAME LINE as the electronics enum,
    not orphaned in some other category bullet (which would mis-route them)."""
    lines = PRODUCT_PARSER_PROMPT.split("\n")
    electronics_lines = [ln for ln in lines if "electronics:" in ln.lower()]
    assert electronics_lines, "PRODUCT_PARSER_PROMPT has no electronics: line"
    # Concatenate any electronics-tagged lines and verify each appliance keyword
    # is present within that block (so the parser sees them as electronics).
    electronics_block = " ".join(electronics_lines).lower()
    for keyword in APPLIANCE_KEYWORDS:
        assert keyword.lower() in electronics_block, (
            f"'{keyword}' not on electronics enum line — drift regression"
        )


# ---------- Live unit (real OpenAI gpt-4o-mini, ~$0.001/test) ----------

LIVE_PARSER_CASES = [
    # (query, expected_category, note)
    ("iPhone 16 vs Galaxy S25", "electronics", "phone — baseline sanity"),
    ("Samsung 65 inch QLED TV vs LG OLED 65 inch", "electronics", "TV"),
    ("MacBook Pro M4 vs Dell XPS 15", "electronics", "laptop"),
    ("Carrier 1.5T AC vs LG 1.5T AC", "electronics", "BUG #1 root case — AC"),
    ("LG 8kg washing machine vs Samsung 8kg front load washer", "electronics", "washer"),
    ("Samsung 500L refrigerator vs LG 500L fridge", "electronics", "refrigerator"),
    ("Sony WH-1000XM5 vs Bose QuietComfort Ultra", "electronics", "headphones"),
    ("Dyson V15 vacuum vs iRobot Roomba j7", "electronics", "vacuum / robot vacuum"),
]


@pytest.mark.live_unit
@pytest.mark.asyncio
@pytest.mark.parametrize(("query", "expected_category", "note"), LIVE_PARSER_CASES)
async def test_parse_product_query_routes_to_electronics_live(
    query: str, expected_category: str, note: str
) -> None:
    """Live OpenAI test — every product type parses as electronics, NOT other."""
    result, _usage = await parse_product_query(query)
    assert "error" not in result, f"parser failed [{note}]: {result.get('error')}"
    products = result.get("products", [])
    assert len(products) >= 1, f"parser returned no products for [{note}]: {result}"
    for product in products:
        actual_category = product.get("category")
        assert actual_category == expected_category, (
            f"[{note}] '{product.get('name')}' (brand={product.get('brand')}) "
            f"parsed as {actual_category!r}, expected {expected_category!r}. "
            f"Full query: {query!r}"
        )
