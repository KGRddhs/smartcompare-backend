# Bahrain Drug Database + Integration Tests — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Import 960 approved Bahrain health products into Supabase for GPT context injection during supplement spec extraction, and build real API integration tests across all product categories.

**Architecture:** Two independent workstreams. WS1 creates a new Supabase table, a lookup service, and injects matched drug data into GPT prompts. WS2 creates integration tests that hit the live Railway endpoint and validate data quality. Zero file overlap between workstreams.

**Tech Stack:** Python 3.12, FastAPI, Supabase (PostgreSQL + full-text search), OpenAI GPT-4o-mini, pytest, httpx, openpyxl

**Supabase Project ID:** `qulajmyxdbdkchvecmvc` (currently INACTIVE — must be restored before migrations)

**Railway Production URL:** `https://smartcompare-backend-production.up.railway.app`

---

## Agent Team Assignment

| Agent | Tasks | Files Owned |
|-------|-------|-------------|
| **Agent A** | Tasks 1-5 (drug database feature) | `app/services/drug_database_service.py`, `app/services/extraction_service.py`, `app/services/structured_comparison_service.py`, Supabase migration |
| **Agent B** | Tasks 6-9 (integration tests) | `tests/test_integration.py` |
| **Agent C** | Tasks 10-12 (TDD unit tests + QA) | `tests/test_drug_database_service.py` |

**Conflict rules:** No agent touches another agent's files. Sequential deploy: Agent A pushes first, Agent B runs tests after deploy is healthy.

---

## WS1: Bahrain Drug Database (Agent A)

### Task 1: Create Supabase table for approved drugs

**Files:**
- Supabase migration (via MCP tool `apply_migration`)

**Step 1: Restore the Supabase project**

The project `qulajmyxdbdkchvecmvc` is currently paused/INACTIVE. Restore it first:

```
Use MCP tool: restore_project(project_id="qulajmyxdbdkchvecmvc")
```

Wait for status to become `ACTIVE_HEALTHY` (check with `get_project`). This may take 1-2 minutes.

**Step 2: Apply the migration**

```
Use MCP tool: apply_migration(
  project_id="qulajmyxdbdkchvecmvc",
  name="create_bahrain_approved_drugs",
  query=<see below>
)
```

Migration SQL:

```sql
-- Create table for Bahrain approved health products
CREATE TABLE bahrain_approved_drugs (
  id SERIAL PRIMARY KEY,
  trade_name TEXT NOT NULL,
  registration_no TEXT,
  api_name TEXT,
  form TEXT,
  pack_size TEXT,
  method_of_sale TEXT,
  manufacturer TEXT,
  country TEXT,
  applicant_name TEXT
);

-- Add full-text search column with auto-update trigger
ALTER TABLE bahrain_approved_drugs ADD COLUMN search_vector TSVECTOR
  GENERATED ALWAYS AS (
    to_tsvector('english', coalesce(trade_name, '') || ' ' || coalesce(api_name, ''))
  ) STORED;

CREATE INDEX idx_drugs_search ON bahrain_approved_drugs USING GIN (search_vector);

-- RLS: service_role bypasses RLS by default, but enable for defense-in-depth
ALTER TABLE bahrain_approved_drugs ENABLE ROW LEVEL SECURITY;
```

**Step 3: Verify the table exists**

```
Use MCP tool: list_tables(project_id="qulajmyxdbdkchvecmvc", schemas=["public"])
```

Expected: `bahrain_approved_drugs` appears in the list alongside existing tables.

**Step 4: Commit** (nothing to commit yet — migration is in Supabase, not in git)

---

### Task 2: Import Excel data into Supabase

**Files:**
- Read: `C:\Users\SynAckITPC\Downloads\PPR_LISTS_Approved Health Product List_20181227.xlsx`
- Supabase insert (via MCP tool `execute_sql`)

**Step 1: Parse the Excel and generate INSERT statements**

The Excel file has 960 data rows (row 0 is header). Columns (0-indexed):
- 0: S.No (skip)
- 1: HP Registration No. → `registration_no`
- 2: Reg'n. Date (skip)
- 3: Next Renewal Date (skip)
- 4: Trade Name → `trade_name`
- 5: API name & strength → `api_name`
- 6: Form → `form`
- 7: Pack Size → `pack_size` (can be int or string)
- 8: Method of sale → `method_of_sale`
- 9: Shelf Life (skip)
- 10: Applicant/Agent name → `applicant_name`
- 11: Manufacturer → `manufacturer`
- 12: Country → `country`
- 13: Storage Condition (skip)
- 14+: all None (skip)

Write a Python script to read the Excel and generate SQL:

```python
import openpyxl

wb = openpyxl.load_workbook(
    r'C:\Users\SynAckITPC\Downloads\PPR_LISTS_Approved Health Product List_20181227.xlsx',
    read_only=True
)
ws = wb['Drug Price List']

rows = []
for i, row in enumerate(ws.iter_rows(values_only=True)):
    if i == 0:  # skip header
        continue
    trade_name = row[4]
    if not trade_name:  # skip empty rows
        continue

    def esc(val):
        if val is None:
            return "NULL"
        s = str(val).replace("'", "''").strip()
        return f"'{s}'"

    rows.append(
        f"({esc(trade_name)}, {esc(row[1])}, {esc(row[5])}, {esc(row[6])}, "
        f"{esc(str(row[7]) if row[7] is not None else None)}, {esc(row[8])}, "
        f"{esc(row[11])}, {esc(row[12])}, {esc(row[10])})"
    )

wb.close()

# Split into batches of 100 for Supabase SQL limits
for batch_start in range(0, len(rows), 100):
    batch = rows[batch_start:batch_start+100]
    sql = (
        "INSERT INTO bahrain_approved_drugs "
        "(trade_name, registration_no, api_name, form, pack_size, method_of_sale, "
        "manufacturer, country, applicant_name) VALUES\n"
        + ",\n".join(batch) + ";"
    )
    print(f"--- BATCH {batch_start // 100 + 1} ({len(batch)} rows) ---")
    print(sql)
    print()
```

Run this script locally to generate the INSERT batches.

**Step 2: Execute each batch via Supabase MCP**

For each batch of ~100 rows:

```
Use MCP tool: execute_sql(
  project_id="qulajmyxdbdkchvecmvc",
  query=<INSERT batch SQL>
)
```

**Step 3: Verify row count**

```
Use MCP tool: execute_sql(
  project_id="qulajmyxdbdkchvecmvc",
  query="SELECT COUNT(*) as total FROM bahrain_approved_drugs;"
)
```

Expected: `total` close to 960 (exact count depends on empty rows skipped).

**Step 4: Verify full-text search works**

```
Use MCP tool: execute_sql(
  project_id="qulajmyxdbdkchvecmvc",
  query="SELECT trade_name, api_name, applicant_name FROM bahrain_approved_drugs WHERE search_vector @@ plainto_tsquery('english', 'vitamin d') LIMIT 5;"
)
```

Expected: Returns products containing "vitamin" and/or "D" in trade_name or api_name.

---

### Task 3: Create the drug database service

**Files:**
- Create: `app/services/drug_database_service.py`

**Step 1: Write the service**

```python
"""
Drug Database Service - Queries Bahrain approved health products from Supabase.

Used to inject official drug registration data into GPT prompts for
more accurate supplement spec extraction.
"""
import logging
from typing import List, Dict, Optional
from app.services.database_service import get_supabase_client

logger = logging.getLogger(__name__)


async def find_matching_drugs(query: str, limit: int = 5) -> List[Dict]:
    """Full-text search against bahrain_approved_drugs table.

    Args:
        query: Product name or ingredient to search for (e.g. "Omega 3", "Vitamin D3")
        limit: Maximum number of results to return

    Returns:
        List of matching drug records with trade_name, api_name, form,
        pack_size, applicant_name, manufacturer, country.
        Empty list if no matches or on error.
    """
    try:
        client = get_supabase_client()
        # Use PostgreSQL full-text search via Supabase RPC or raw query
        # plainto_tsquery handles multi-word queries naturally
        response = client.table("bahrain_approved_drugs").select(
            "trade_name, api_name, form, pack_size, applicant_name, manufacturer, country"
        ).text_search(
            "search_vector", query, type="plain"
        ).limit(limit).execute()

        return response.data if response.data else []

    except Exception as e:
        logger.warning(f"Drug database lookup failed for '{query}': {e}")
        return []


def format_drug_context(drugs: List[Dict]) -> str:
    """Format matched drugs into a string for GPT prompt injection.

    Args:
        drugs: List of drug records from find_matching_drugs()

    Returns:
        Formatted string to append to GPT prompt, or empty string if no drugs.
    """
    if not drugs:
        return ""

    lines = [
        "\n## Official Bahrain Drug Registration Data",
        "The following registered health products may be relevant. "
        "Use this as ground truth for dosage, form, and ingredient details:"
    ]

    for drug in drugs:
        entry = f"- Trade Name: {drug.get('trade_name', 'N/A')}"
        if drug.get('api_name'):
            entry += f"\n  Ingredients: {drug['api_name']}"
        if drug.get('form'):
            entry += f"\n  Form: {drug['form']}"
        if drug.get('pack_size'):
            entry += f"\n  Pack Size: {drug['pack_size']}"
        if drug.get('applicant_name'):
            entry += f"\n  Sold at: {drug['applicant_name']}"
        if drug.get('manufacturer'):
            entry += f"\n  Manufacturer: {drug['manufacturer']}"
        if drug.get('country'):
            entry += f"\n  Country: {drug['country']}"
        lines.append(entry)

    return "\n".join(lines)
```

**Step 2: Verify syntax**

Run: `python -m py_compile app/services/drug_database_service.py`
Expected: No output (clean compile)

**Step 3: Commit**

```bash
git add app/services/drug_database_service.py
git commit -m "feat: add drug database service for Bahrain approved drugs lookup"
```

---

### Task 4: Inject drug context into GPT spec extraction prompt

**Files:**
- Modify: `app/services/extraction_service.py` (lines 95 and 332)

**Step 1: Add `drug_context` parameter to `_build_specs_prompt()`**

In `app/services/extraction_service.py`, modify line 95:

Change:
```python
def _build_specs_prompt(brand: str, name: str, variant: str, category: str, search_context: str) -> str:
```

To:
```python
def _build_specs_prompt(brand: str, name: str, variant: str, category: str, search_context: str, drug_context: str = "") -> str:
```

Then in the prompt template, insert the drug context after the search results block. Change lines 108-109:

```python
Search results for context:
{search_context}
```

To:
```python
Search results for context:
{search_context}
{drug_context}
```

**Step 2: Add `drug_context` parameter to `extract_specs()`**

Modify the function signature at line 332:

Change:
```python
async def extract_specs(
    brand: str,
    name: str,
    variant: Optional[str],
    category: str,
    search_context: str
) -> Dict[str, Any]:
```

To:
```python
async def extract_specs(
    brand: str,
    name: str,
    variant: Optional[str],
    category: str,
    search_context: str,
    drug_context: str = ""
) -> Dict[str, Any]:
```

Then modify the `_build_specs_prompt` call at line 342:

Change:
```python
        prompt = _build_specs_prompt(
            brand, name, variant or "", category,
            search_context[:3000]
        )
```

To:
```python
        prompt = _build_specs_prompt(
            brand, name, variant or "", category,
            search_context[:3000],
            drug_context
        )
```

**Step 3: Verify syntax**

Run: `python -m py_compile app/services/extraction_service.py`
Expected: No output (clean compile)

**Step 4: Commit**

```bash
git add app/services/extraction_service.py
git commit -m "feat: accept drug_context in spec extraction prompt"
```

---

### Task 5: Wire drug lookup into the comparison pipeline

**Files:**
- Modify: `app/services/structured_comparison_service.py` (lines 332 and 434)

**Step 1: Add import at top of file**

Add after the existing imports from extraction_service (find the line with `from app.services.extraction_service import`):

```python
from app.services.drug_database_service import find_matching_drugs, format_drug_context
```

**Step 2: Add `drug_context` parameter to `_get_specs()`**

Modify the function signature at line 434:

Change:
```python
    async def _get_specs(
        self,
        brand: str,
        name: str,
        variant: Optional[str],
        category: str,
        search_query: str,
        nocache: bool = False,
        search_results: Optional[Dict] = None
    ) -> Dict[str, Any]:
```

To:
```python
    async def _get_specs(
        self,
        brand: str,
        name: str,
        variant: Optional[str],
        category: str,
        search_query: str,
        nocache: bool = False,
        search_results: Optional[Dict] = None,
        drug_context: str = ""
    ) -> Dict[str, Any]:
```

**Step 3: Pass `drug_context` to `extract_specs()`**

Modify line 463:

Change:
```python
        specs = await extract_specs(brand, name, variant, category, search_context)
```

To:
```python
        specs = await extract_specs(brand, name, variant, category, search_context, drug_context=drug_context)
```

**Step 4: Add drug lookup before `_get_specs()` call**

In `_fetch_product_data()`, find the block around line 331-332 where `_get_specs` is called:

```python
        if include_specs:
            phase1_tasks.append(self._get_specs(brand, name, variant, category, search_query, nocache, search_results=unified_search))
            phase1_keys.append("specs")
```

Change to:

```python
        if include_specs:
            # For supplements, look up official Bahrain drug registration data
            drug_ctx = ""
            if category == "supplements" or self._is_supplement_query(f"{brand} {name}"):
                try:
                    matching_drugs = await find_matching_drugs(f"{brand} {name}")
                    drug_ctx = format_drug_context(matching_drugs)
                    if drug_ctx:
                        logger.info(f"Found {len(matching_drugs)} Bahrain drug matches for {brand} {name}")
                except Exception as e:
                    logger.warning(f"Drug database lookup failed: {e}")

            phase1_tasks.append(self._get_specs(brand, name, variant, category, search_query, nocache, search_results=unified_search, drug_context=drug_ctx))
            phase1_keys.append("specs")
```

**Step 5: Verify syntax**

Run: `python -m py_compile app/services/structured_comparison_service.py`
Expected: No output (clean compile)

**Step 6: Commit**

```bash
git add app/services/structured_comparison_service.py
git commit -m "feat: inject Bahrain drug context into supplement spec extraction"
```

**Step 7: Push to deploy**

```bash
git push origin main
```

Wait ~90 seconds for Railway to deploy, then verify:

```bash
curl https://smartcompare-backend-production.up.railway.app/health
```

Expected: `{"status": "ok"}` or similar healthy response.

---

## WS2: Integration Tests (Agent B)

### Task 6: Create integration test infrastructure

**Files:**
- Create: `tests/test_integration.py`

**Step 1: Write the test file with shared helpers and configuration**

```python
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
    rating = product.get("rating", {})
    if rating and rating.get("score") is not None:
        score = rating["score"]
        assert 1.0 <= score <= 5.0, f"Rating must be 1-5, got {score}"


def assert_valid_comparison(data: dict):
    """Validate the comparison structure."""
    assert "products" in data, "Response must have 'products'"
    assert len(data["products"]) == 2, f"Expected 2 products, got {len(data['products'])}"

    # Comparison section
    comparison = data.get("comparison", {})
    assert comparison.get("recommendation"), "Comparison must have a recommendation"

    # Cost tracking
    metadata = data.get("metadata", {})
    cost = metadata.get("cost", {})
    if cost.get("current_cost"):
        assert cost["current_cost"] <= 0.020, f"Cost ${cost['current_cost']:.4f} exceeds $0.020 budget"
```

**Step 2: Verify syntax**

Run: `python -m py_compile tests/test_integration.py`
Expected: No output (clean compile)

**Step 3: Commit**

```bash
git add tests/test_integration.py
git commit -m "test: add integration test infrastructure for live API validation"
```

---

### Task 7: Write electronics integration tests

**Files:**
- Modify: `tests/test_integration.py`

**Step 1: Add electronics tests**

Append to `tests/test_integration.py`:

```python
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
        # Phones must have these core specs
        assert specs.get("display_size") and specs["display_size"] != "N/A", \
            f"Phone must have display_size, got: {specs.get('display_size')}"
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
```

**Step 2: Run the tests**

Run: `python -m pytest tests/test_integration.py::test_electronics_phones tests/test_integration.py::test_electronics_laptops -v --timeout=180`
Expected: Both tests PASS with real data from the live API. Each test takes 30-90 seconds.

**Step 3: Commit**

```bash
git add tests/test_integration.py
git commit -m "test: add electronics integration tests (phones + laptops)"
```

---

### Task 8: Write supplement and grocery integration tests

**Files:**
- Modify: `tests/test_integration.py`

**Step 1: Add supplement tests**

Append to `tests/test_integration.py`:

```python
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
```

**Step 2: Run the supplement and grocery tests**

Run: `python -m pytest tests/test_integration.py::test_supplements_iherb tests/test_integration.py::test_supplements_pharmacy tests/test_integration.py::test_grocery -v --timeout=180`
Expected: All 3 tests PASS. Supplement tests may take longer due to iHerb scraping.

**Step 3: Commit**

```bash
git add tests/test_integration.py
git commit -m "test: add supplement and grocery integration tests"
```

---

### Task 9: Write general product test and run full suite

**Files:**
- Modify: `tests/test_integration.py`

**Step 1: Add general product test**

Append to `tests/test_integration.py`:

```python
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

    # Shoe prices (10-100 BHD range)
    for product in data["products"]:
        amount = product["price"]["amount"]
        assert 5 <= amount <= 150, f"Shoe price {amount} BHD seems unrealistic"
```

**Step 2: Run the full integration test suite**

Run: `python -m pytest tests/test_integration.py -v --timeout=180`
Expected: All 6 tests PASS. Total runtime: 3-8 minutes. Total cost: ~$0.06.

**Step 3: Commit**

```bash
git add tests/test_integration.py
git commit -m "test: add general product test, complete integration test suite"
```

---

## WS1 QA: Unit Tests + TDD (Agent C)

### Task 10: Write failing unit tests for drug database service (TDD — red phase)

**Files:**
- Create: `tests/test_drug_database_service.py`

**Important:** These tests are written BEFORE Agent A's implementation code exists (or at least before it's finalized). They define the expected behavior.

**Step 1: Write the test file**

```python
"""
Unit tests for drug database service.

Tests the Bahrain approved drugs lookup and GPT context formatting.
These tests require the Supabase bahrain_approved_drugs table to be populated.
"""
import pytest
import asyncio
from unittest.mock import patch, MagicMock


def run_async(coro):
    """Helper to run async functions in sync tests."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class TestFindMatchingDrugs:
    """Tests for find_matching_drugs() full-text search."""

    def test_exact_trade_name_match(self):
        """Searching for an exact trade name returns that product."""
        from app.services.drug_database_service import find_matching_drugs

        results = run_async(find_matching_drugs("TIGER BALM SOFT"))
        assert len(results) >= 1
        trade_names = [r["trade_name"].upper() for r in results]
        assert any("TIGER BALM" in tn for tn in trade_names)

    def test_partial_ingredient_match(self):
        """Searching 'Omega 3' matches products with omega-3 ingredients."""
        from app.services.drug_database_service import find_matching_drugs

        results = run_async(find_matching_drugs("Omega 3"))
        assert len(results) >= 1
        # At least one result should mention omega in trade_name or api_name
        found_omega = any(
            "omega" in (r.get("trade_name", "") + " " + r.get("api_name", "")).lower()
            for r in results
        )
        assert found_omega, f"Expected omega-related product, got: {[r['trade_name'] for r in results]}"

    def test_vitamin_d_search(self):
        """Searching 'Vitamin D' matches vitamin D products."""
        from app.services.drug_database_service import find_matching_drugs

        results = run_async(find_matching_drugs("Vitamin D"))
        assert len(results) >= 1

    def test_no_match_returns_empty(self):
        """Searching for a non-drug product returns empty list."""
        from app.services.drug_database_service import find_matching_drugs

        results = run_async(find_matching_drugs("iPhone 15 Pro Max"))
        assert results == []

    def test_limit_parameter(self):
        """Results are capped at the limit parameter."""
        from app.services.drug_database_service import find_matching_drugs

        results = run_async(find_matching_drugs("vitamin", limit=3))
        assert len(results) <= 3

    def test_result_fields(self):
        """Each result has the expected fields."""
        from app.services.drug_database_service import find_matching_drugs

        results = run_async(find_matching_drugs("cod liver oil"))
        assert len(results) >= 1
        result = results[0]
        assert "trade_name" in result
        assert "api_name" in result
        assert "form" in result
        assert "pack_size" in result
        assert "applicant_name" in result

    def test_error_returns_empty_list(self):
        """If Supabase fails, returns empty list instead of raising."""
        from app.services.drug_database_service import find_matching_drugs

        with patch("app.services.drug_database_service.get_supabase_client") as mock:
            mock.side_effect = Exception("Connection refused")
            results = run_async(find_matching_drugs("anything"))
            assert results == []


class TestFormatDrugContext:
    """Tests for format_drug_context() prompt formatting."""

    def test_empty_list_returns_empty_string(self):
        """No drugs = no context to inject."""
        from app.services.drug_database_service import format_drug_context

        assert format_drug_context([]) == ""

    def test_single_drug_format(self):
        """Single drug formatted correctly for GPT prompt."""
        from app.services.drug_database_service import format_drug_context

        drugs = [{
            "trade_name": "NORWEGIAN COD LIVER OIL",
            "api_name": "Vitamin A 1250 IU, Vitamin D 135 IU",
            "form": "Soft Gel Capsules",
            "pack_size": "110",
            "applicant_name": "BAHRAIN PHARMACY (MAIN)",
            "manufacturer": "21st Century Healthcare Inc",
            "country": "USA",
        }]

        result = format_drug_context(drugs)
        assert "Official Bahrain Drug Registration Data" in result
        assert "NORWEGIAN COD LIVER OIL" in result
        assert "Vitamin A 1250 IU" in result
        assert "Soft Gel Capsules" in result
        assert "BAHRAIN PHARMACY (MAIN)" in result
        assert "21st Century Healthcare Inc" in result

    def test_multiple_drugs_all_included(self):
        """Multiple drugs all appear in output."""
        from app.services.drug_database_service import format_drug_context

        drugs = [
            {"trade_name": "Product A", "api_name": "Ingredient A"},
            {"trade_name": "Product B", "api_name": "Ingredient B"},
        ]

        result = format_drug_context(drugs)
        assert "Product A" in result
        assert "Product B" in result

    def test_missing_fields_handled(self):
        """Drugs with missing optional fields don't crash."""
        from app.services.drug_database_service import format_drug_context

        drugs = [{"trade_name": "Minimal Drug"}]
        result = format_drug_context(drugs)
        assert "Minimal Drug" in result
```

**Step 2: Run tests to verify they fail (red phase)**

Run: `python -m pytest tests/test_drug_database_service.py -v`
Expected: `TestFormatDrugContext` tests may pass (if Agent A's code exists), `TestFindMatchingDrugs` tests may fail with import errors or connection errors. This is correct — they define expected behavior.

**Step 3: Commit**

```bash
git add tests/test_drug_database_service.py
git commit -m "test: add TDD unit tests for drug database service (red phase)"
```

---

### Task 11: QA Agent A's code

**This task runs AFTER Agent A completes Tasks 1-5.**

**Step 1: Review `app/services/drug_database_service.py`**

Check for:
- [ ] SQL injection: Is the query properly parameterized? (Supabase client handles this via `.text_search()`, but verify)
- [ ] Error handling: Does `find_matching_drugs()` catch all exceptions and return `[]`?
- [ ] Logging: Are failures logged with enough context to debug?
- [ ] No new env vars required (reuses existing `SUPABASE_SERVICE_KEY`)

**Step 2: Review changes to `app/services/extraction_service.py`**

Check for:
- [ ] `drug_context` parameter has default `""` (backward compatible)
- [ ] Drug context is inserted in the right position in the prompt
- [ ] No change to the JSON schema enforcement logic
- [ ] `search_context[:3000]` truncation still applies (drug context is separate)

**Step 3: Review changes to `app/services/structured_comparison_service.py`**

Check for:
- [ ] Drug lookup only runs for supplements (not electronics/grocery)
- [ ] Drug lookup failure doesn't block spec extraction (wrapped in try/except)
- [ ] `drug_context` parameter has default `""` (backward compatible for non-supplement calls)
- [ ] Import statement added at top of file
- [ ] No changes to cost tracking or cache logic

**Step 4: Run ALL unit tests**

Run: `python -m pytest tests/test_drug_database_service.py tests/test_pharmacy_jsonld.py tests/test_url_extraction.py -v`
Expected: All tests PASS (green phase). If any fail, send back to Agent A with specific failure details.

**Step 5: Verify syntax of all modified files**

Run:
```bash
python -m py_compile app/services/drug_database_service.py
python -m py_compile app/services/extraction_service.py
python -m py_compile app/services/structured_comparison_service.py
```

Expected: No output (all clean).

---

### Task 12: QA Agent B's tests + write additional coverage

**This task runs AFTER Agent B completes Tasks 6-9.**

**Step 1: Review `tests/test_integration.py`**

Check for:
- [ ] All tests use `nocache=true` (tests real pipeline, not stale cache)
- [ ] Timeout is sufficient (≥120 seconds)
- [ ] Price range assertions are realistic (not too tight to cause flaky failures)
- [ ] Error messages are descriptive enough to debug failures
- [ ] No hardcoded product-specific values that could change (e.g., exact price amounts)
- [ ] `assert_valid_product()` checks all required fields

**Step 2: Run the full integration test suite**

Run: `python -m pytest tests/test_integration.py -v --timeout=180`
Expected: All 6 tests PASS.

**Step 3: If any tests fail, send back to Agent B with:**
- Exact failure output
- Which assertion failed and why
- Suggested fix (e.g., "widen price range" or "add timeout")

**Step 4: Write additional tests if coverage is below 80%**

If idle, add more edge case tests to existing test files. Ideas:
- Test that the health endpoint returns 200: `test_health_endpoint()`
- Test that an empty query returns an error: `test_empty_query()`
- Test that a single-product query is handled: `test_single_product_query()`

---

## Phase 4: Final Verification (All Agents)

### Task 13: End-to-end verification

**All agents verify together before team dissolves.**

**Step 1: Run ALL tests**

```bash
python -m pytest tests/ -v --timeout=180
```

Expected: All tests pass (unit + integration).

**Step 2: Verify deployed feature works**

Test a supplement comparison with drug context:

```bash
curl "https://smartcompare-backend-production.up.railway.app/api/v1/text/compare?q=Norwegian+Cod+Liver+Oil+vs+Kordel+Omega+3&nocache=true"
```

Check the response:
- Specs should reflect accurate dosages from the drug database
- Prices should be in BHD
- Cost should be within budget (≤$0.015)

**Step 3: Verify non-supplement comparisons are unaffected**

```bash
curl "https://smartcompare-backend-production.up.railway.app/api/v1/text/compare?q=iPhone+15+vs+Galaxy+S24&nocache=true"
```

Check: Electronics comparison should work exactly as before (no drug context injected).

**Step 4: Final commit with all tests passing**

```bash
git add -A
git status  # Review what's being committed
git commit -m "feat: complete Bahrain drug database integration + full test suite"
git push origin main
```

**Step 5: Team dissolves only when:**
- [ ] All tests pass
- [ ] Drug context injection works for supplements
- [ ] Non-supplement comparisons are unaffected
- [ ] Cost is within budget
- [ ] Code has been cross-QA'd by another agent
