# Design: Bahrain Drug Database + Integration Tests

**Date:** 2026-02-21
**Status:** Approved

## Overview

Two parallel workstreams to make SmartCompare smarter for supplement comparisons and more reliable overall:

1. **WS1: Bahrain Drug Database** — Import 960 approved health products from official Bahrain registry into Supabase. Use as GPT context injection during spec extraction for supplements.
2. **WS2: Integration Tests** — Real API tests across all 4 product categories (electronics, supplements, grocery, general) hitting the live Railway endpoint.

## Agent Team Structure (3 Opus Agents)

| Agent | Primary Task | QAs |
|-------|-------------|-----|
| Agent A | Drug database (Supabase + service + GPT injection) | Agent B's tests |
| Agent B | Integration tests (all categories, live endpoint) | Agent C's work |
| Agent C | TDD unit tests for drug DB, then QA Agent A's code | Agent A's code |

### Workflow Phases

1. **Phase 1 (Parallel):** Agent A builds drug DB feature. Agent B writes integration tests for current API. Agent C writes failing unit tests first (TDD).
2. **Phase 2 (QA):** Agent C QAs Agent A's code. Agent A QAs Agent B's tests. Agent B QAs Agent C's tests.
3. **Phase 3 (Rework):** Rejected work sent back to original agent. Idle agents write more tests toward 80% coverage.
4. **Phase 4 (Verification):** All agents verify: all tests pass, feature complete, no gaps. Team dissolves only when 100% complete.

### Conflict Prevention

Zero file overlap between workstreams:
- WS1 touches: `app/services/drug_database_service.py` (new), `app/services/extraction_service.py` (modify), `app/services/structured_comparison_service.py` (modify), Supabase migration
- WS2 touches: `tests/test_integration.py` (new), `tests/test_drug_database_service.py` (new)
- Sequential deploy: WS1 deploys first, WS2 tests run after deploy confirmed healthy

## WS1: Bahrain Drug Database

### Data Source

Excel file: `PPR_LISTS_Approved Health Product List_20181227.xlsx`
- 960 rows of approved health products
- Key columns: Trade Name, API name & strength (ingredients), Form, Pack Size, Method of sale, Applicant/Agent name (Bahrain pharmacy), Manufacturer, Country

### Supabase Table Schema

```sql
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
  applicant_name TEXT,
  search_vector TSVECTOR
);

CREATE INDEX idx_drugs_search ON bahrain_approved_drugs USING GIN (search_vector);

ALTER TABLE bahrain_approved_drugs ENABLE ROW LEVEL SECURITY;
```

### Data Import

- Parse Excel (openpyxl), skip empty rows and None-only columns
- Insert 960 rows into Supabase
- Generate `search_vector` from `to_tsvector('english', trade_name || ' ' || coalesce(api_name, ''))` via trigger or on insert

### New Service: `app/services/drug_database_service.py`

```python
class DrugDatabaseService:
    async def find_matching_drugs(self, query: str, limit: int = 5) -> list[dict]:
        """Full-text search against bahrain_approved_drugs.

        Returns top matches with trade_name, api_name, form,
        pack_size, applicant_name.
        """
```

### Integration: GPT Context Injection

In `extraction_service.py` → `extract_specs()`, when category is supplements:

1. Call `drug_database_service.find_matching_drugs(product_name)`
2. If matches found, append to GPT prompt:

```
## Official Bahrain Drug Registration Data
The following registered health products may be relevant:
- Trade Name: KORDEL'S OMEGA 3 FISH OIL 1500MG PLUS VITAMIN D
  Ingredients: Fish oil 1500mg, EPA 270mg, DHA 180mg, Vitamin D3 142 IU
  Form: Capsules, Pack Size: 90
  Sold at: Wael Pharmacy

Use this data as ground truth for dosage, form, and ingredient details.
```

3. GPT extracts specs with higher accuracy from verified reference data

### Pipeline Integration

In `structured_comparison_service.py` → `_get_specs()`:
- After detecting supplement category, call drug DB lookup
- Pass results to `extract_specs()` as additional context parameter
- Lookup runs in parallel with existing web search (no added latency on critical path)

### Cost Impact

- Supabase query: Free (within existing plan)
- Latency: ~50-100ms added per supplement comparison
- No additional external API calls

### Safety

- Migration is purely additive (new table, no existing table modifications)
- No foreign keys to existing tables
- `service_role` access only (backend reads, no public access)
- PostgreSQL transactions ensure atomic create-or-nothing

## WS2: Integration Tests

### File: `tests/test_integration.py`

Tests call the live Railway production endpoint with `nocache=true`.

### Reference Comparisons

| Category | Query | Key Validations |
|----------|-------|-----------------|
| Electronics | `iPhone 15 vs Samsung Galaxy S24` | Specs: display_size, processor, battery. Price in BHD, realistic range. Rating 1-5. |
| Electronics | `MacBook Air M3 vs Dell XPS 15` | Laptop specs: RAM, storage, weight. Price ranges realistic. |
| Supplements | `NOW Vitamin D3 5000 IU vs Nature Made D3 2000 IU` | Dosage in specs, iHerb prices populated, form = softgels/capsules. |
| Supplements | `HealthAid Vitamin C vs Vitabiotics Wellman` | Non-iHerb brands, pharmacy pricing path, BHD currency. |
| Grocery | `Coca Cola vs Pepsi` | Basic specs present, prices realistic, comparison generated. |
| General | `Nike Air Max vs Adidas Ultraboost` | General product specs, price comparison works. |

### Validation Pattern

Each test validates:
- HTTP 200 response
- 2 products in response
- Each product has: name, non-empty specs, price (BHD, realistic amount), rating (1-5 or null)
- Comparison has: winner, recommendation
- Cost within budget (≤ $0.015)

### Test Configuration

- `BASE_URL`: Railway production URL (hardcoded constant)
- Timeout: 120 seconds
- Marker: `@pytest.mark.integration`
- Cost per full suite run: ~$0.06-0.08

## WS1 QA: Unit Tests (Agent C — TDD)

### File: `tests/test_drug_database_service.py`

Written BEFORE Agent A's implementation (red-green TDD):

- `test_find_matching_drugs_exact_trade_name` — exact match returns correct product
- `test_find_matching_drugs_partial_match` — "Omega 3" matches full trade names
- `test_find_matching_drugs_ingredient_search` — "Vitamin D3" matches api_name
- `test_find_matching_drugs_no_match_returns_empty` — "iPhone 15" returns []
- `test_find_matching_drugs_limit` — results capped at limit
- `test_context_injection_format` — injected context has correct structure

### Coverage Target: 80%

Across all test files:
- `tests/test_drug_database_service.py` (new)
- `tests/test_integration.py` (new)
- `tests/test_pharmacy_jsonld.py` (existing, 12 tests)
- `tests/test_url_extraction.py` (existing, 8 tests)
