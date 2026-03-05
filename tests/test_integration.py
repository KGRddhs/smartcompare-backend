"""
Integration tests for SmartCompare API.

These tests call the LIVE Railway production endpoint and validate
real responses for data quality and structural correctness.

Cost: ~$0.01 per test (real API calls). Full suite: ~$0.06-0.08.
Run with: pytest tests/test_integration.py -v --timeout=180
"""
import pytest
import httpx

BASE_URL = "https://smartcompare-backend-production.up.railway.app"
TIMEOUT = 150.0  # seconds — API can take up to 120s for complex queries


def fetch_comparison(query: str) -> dict:
    """Call the compare endpoint and return parsed JSON."""
    response = httpx.get(
        f"{BASE_URL}/api/v1/text/compare",
        params={"q": query, "nocache": "true"},
        timeout=TIMEOUT,
    )
    assert response.status_code == 200, f"HTTP {response.status_code}: {response.text[:500]}"
    return response.json()


def assert_valid_product(product: dict, category: str = None):
    """Validate a product has all required fields with sensible values."""
    # Name present
    assert product.get("name"), "Product must have a name"

    # Specs present and non-empty
    specs = product.get("specs", {})
    assert specs, "Product must have specs"
    # Filter out meta keys to check real spec content
    real_specs = {k: v for k, v in specs.items() if k not in ("brand", "model", "variant", "category", "_cached", "error")}
    assert len(real_specs) >= 3, f"Product should have at least 3 spec fields, got {len(real_specs)}: {list(real_specs.keys())}"

    # Price present with correct currency
    price = product.get("price")
    assert price, "Product must have a price"
    assert price.get("currency") == "BHD", f"Currency should be BHD, got {price.get('currency')}"
    amount = price.get("amount")
    assert amount is not None, "Price amount must not be None"
    assert isinstance(amount, (int, float)), f"Price amount must be a number, got {type(amount)}"
    assert amount > 0, f"Price amount must be positive, got {amount}"

    # Rating valid (can be null but if present must be 1-5)
    # Backend returns rating as a raw float, not a dict
    rating = product.get("rating")
    if rating is not None:
        assert isinstance(rating, (int, float)), f"Rating must be a number, got {type(rating)}"
        assert 1.0 <= rating <= 5.0, f"Rating must be 1-5, got {rating}"


def assert_valid_comparison(data: dict):
    """Validate the comparison structure."""
    assert "products" in data, "Response must have 'products'"
    assert len(data["products"]) == 2, f"Expected 2 products, got {len(data['products'])}"

    # Comparison section
    comparison = data.get("comparison", {})
    assert comparison.get("recommendation"), "Comparison must have a recommendation"

    # Cost tracking — metadata.total_cost is a flat float
    metadata = data.get("metadata", {})
    total_cost = metadata.get("total_cost")
    if total_cost is not None:
        assert total_cost <= 0.020, f"Cost ${total_cost:.4f} exceeds $0.020 budget"


# ============================================
# Electronics Tests
# ============================================

@pytest.mark.integration
def test_electronics_phones():
    """iPhone vs Samsung: flagship phone comparison."""
    data = fetch_comparison("iPhone 15 vs Samsung Galaxy S24")
    assert_valid_comparison(data)

    for product in data["products"]:
        assert_valid_product(product, category="electronics")
        specs = product["specs"]
        # Phones must have these core specs (key may be "display" or "display_size")
        display = specs.get("display") or specs.get("display_size")
        assert display and display != "N/A", \
            f"Phone must have display, got: {display}"
        assert specs.get("processor") and specs["processor"] != "N/A", \
            f"Phone must have processor, got: {specs.get('processor')}"
        assert specs.get("battery") and specs["battery"] != "N/A", \
            f"Phone must have battery, got: {specs.get('battery')}"

    # Price should be in a realistic range for phones (50-600 BHD)
    for product in data["products"]:
        amount = product["price"]["amount"]
        assert 50 <= amount <= 600, f"Phone price {amount} BHD seems unrealistic"


@pytest.mark.integration
def test_electronics_laptops():
    """MacBook vs Dell: laptop comparison."""
    data = fetch_comparison("MacBook Air M3 vs Dell XPS 15")
    assert_valid_comparison(data)

    for product in data["products"]:
        assert_valid_product(product, category="electronics")
        specs = product["specs"]
        # Laptops must have RAM and storage
        assert specs.get("ram") and specs["ram"] != "N/A", \
            f"Laptop must have RAM, got: {specs.get('ram')}"
        assert specs.get("storage") and specs["storage"] != "N/A", \
            f"Laptop must have storage, got: {specs.get('storage')}"

    # Price should be in a realistic range for laptops (150-1200 BHD)
    for product in data["products"]:
        amount = product["price"]["amount"]
        assert 150 <= amount <= 1200, f"Laptop price {amount} BHD seems unrealistic"


# ============================================
# Supplement Tests
# ============================================

@pytest.mark.integration
def test_supplements_iherb():
    """NOW D3 vs Nature Made D3: iHerb-sourced supplements."""
    data = fetch_comparison("NOW Vitamin D3 5000 IU vs Nature Made D3 2000 IU")
    assert_valid_comparison(data)

    for product in data["products"]:
        assert_valid_product(product, category="supplements")
        specs = product["specs"]
        # Supplements must have dosage and form
        assert specs.get("dosage") and specs["dosage"] != "N/A", \
            f"Supplement must have dosage, got: {specs.get('dosage')}"
        assert specs.get("form") and specs["form"] != "N/A", \
            f"Supplement must have form, got: {specs.get('form')}"

    # Supplement prices are typically low (0.5-30 BHD)
    for product in data["products"]:
        amount = product["price"]["amount"]
        assert 0.5 <= amount <= 30, f"Supplement price {amount} BHD seems unrealistic"


@pytest.mark.integration
def test_supplements_pharmacy():
    """HealthAid vs Vitabiotics: non-iHerb brands, pharmacy pricing path."""
    data = fetch_comparison("HealthAid Vitamin C 1000mg vs Vitabiotics Wellman Original")
    assert_valid_comparison(data)

    for product in data["products"]:
        assert_valid_product(product, category="supplements")
        # These brands should still get BHD prices (via pharmacy or fallback)
        assert product["price"]["currency"] == "BHD"


# ============================================
# Grocery Tests
# ============================================

@pytest.mark.integration
def test_grocery():
    """Coca Cola vs Pepsi: basic grocery comparison."""
    data = fetch_comparison("Coca Cola vs Pepsi")
    assert_valid_comparison(data)

    for product in data["products"]:
        assert_valid_product(product, category="grocery")

    # Grocery prices are very low (0.1-5 BHD typically)
    for product in data["products"]:
        amount = product["price"]["amount"]
        assert 0.1 <= amount <= 10, f"Grocery price {amount} BHD seems unrealistic"


# ============================================
# General Product Tests
# ============================================

@pytest.mark.integration
def test_general_product():
    """Nike vs Adidas: general product comparison."""
    data = fetch_comparison("Nike Air Max 90 vs Adidas Ultraboost")
    assert_valid_comparison(data)

    for product in data["products"]:
        assert_valid_product(product, category="other")

    # Shoe prices (5-400 BHD range — premium sneakers can be expensive)
    for product in data["products"]:
        amount = product["price"]["amount"]
        assert 5 <= amount <= 400, f"Shoe price {amount} BHD seems unrealistic"


# ============================================
# Category Selection Tests
# ============================================

def fetch_comparison_with_category(query: str, selected_category: str = None) -> dict:
    """Call compare endpoint with optional selected_category param."""
    params = {"q": query, "nocache": "true"}
    if selected_category:
        params["selected_category"] = selected_category
    response = httpx.get(
        f"{BASE_URL}/api/v1/text/compare",
        params=params,
        timeout=TIMEOUT,
    )
    assert response.status_code == 200, f"HTTP {response.status_code}: {response.text[:500]}"
    return response.json()


@pytest.mark.integration
def test_category_selection_electronics_match():
    """E2E: Select electronics, query electronics, verify no switch."""
    data = fetch_comparison_with_category(
        "iPhone 15 vs Samsung Galaxy S24",
        selected_category="electronics"
    )
    assert data["success"] is True
    assert data["category_used"] == "electronics"
    assert data["category_switched"] is False
    assert data.get("original_category") is None


@pytest.mark.integration
def test_category_selection_mismatch():
    """E2E: Select electronics, query makeup, verify switch to makeup."""
    data = fetch_comparison_with_category(
        "MAC Ruby Woo vs Dior 999 lipstick",
        selected_category="electronics"
    )
    assert data["success"] is True
    assert data["category_used"] == "makeup"
    assert data["category_switched"] is True
    assert data["original_category"] == "electronics"

    # Verify makeup specs were extracted
    if data.get("products"):
        product = data["products"][0]
        specs = product.get("specs", {})
        makeup_fields = ["finish", "shade_range", "coverage", "skin_type",
                         "cruelty_free", "waterproof", "volume"]
        has_makeup_field = any(f in specs for f in makeup_fields)
        assert has_makeup_field, \
            f"No makeup fields found in specs: {list(specs.keys())}"


@pytest.mark.integration
def test_backward_compat_no_category():
    """E2E: API works without selected_category param (backward compat)."""
    data = fetch_comparison_with_category(
        "iPhone 15 vs Samsung Galaxy S24",
        selected_category=None  # No category selected
    )
    assert data["success"] is True
    assert "category_used" in data
    assert data["category_switched"] is False


@pytest.mark.integration
def test_category_skincare_match():
    """E2E: Skincare products with matching category."""
    data = fetch_comparison_with_category(
        "CeraVe Moisturizing Cream vs Cetaphil Daily Hydrating Lotion",
        selected_category="skincare"
    )
    assert data["success"] is True
    # AI should detect skincare
    assert data["category_used"] in ("skincare", "other")

    if data.get("products"):
        product = data["products"][0]
        specs = product.get("specs", {})
        skincare_fields = ["skin_type", "skin_concern", "active_ingredient",
                           "fragrance_free", "volume"]
        if data["category_used"] == "skincare":
            has_skincare_field = any(f in specs for f in skincare_fields)
            assert has_skincare_field, \
                f"No skincare fields in specs: {list(specs.keys())}"
