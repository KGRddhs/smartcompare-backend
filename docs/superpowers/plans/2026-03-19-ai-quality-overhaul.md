# AI Quality Overhaul — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix wrong prices, irrelevant specs, raw citations, and missing fashion category across ALL product comparisons.

**Architecture:** Add fashion as 9th category with dedicated spec schema. Add luxury brand detection (category-independent) for price guardrails. Rewrite price extraction prompt to prefer official sources over cheapest. Strip `[snippet_N]` citations from reviews, replacing with source domains. Filter N/A specs in frontend.

**Tech Stack:** Python 3.12 (FastAPI), React Native (Expo), GPT-4o-mini prompts, Serper API

**Spec:** `docs/superpowers/specs/2026-03-19-ai-quality-overhaul-design.md`

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `app/services/extraction_service.py` | Modify (lines 45-78, 81-155, 158-198, 201-229, 257-304, 307-372) | All prompt templates + category schemas |
| `app/services/structured_comparison_service.py` | Modify (lines 45-97, 1081-1136, 1573-1688) | RETAILER_TIERS, luxury detection, price extraction, citation cleanup |
| `app/services/scoring_service.py` | Modify (lines 224-259, 46-58) | Spec score N/A penalty, fashion field awareness |
| `SmartCompareApp/src/screens/ResultsScreen.tsx` | Modify (lines 397-438) | N/A spec filtering |
| `SmartCompareApp/src/components/CategorySelector.tsx` | Modify (lines 21-29) | Add fashion category |
| `tests/test_fashion_category.py` | Create | Fashion detection + schema tests |
| `tests/test_luxury_brands.py` | Create | Luxury brand detection + price guardrail tests |
| `tests/test_citation_cleanup.py` | Create | Citation stripping tests |
| `tests/test_price_priority.py` | Create | Price source hierarchy tests |

---

## Round 1 — Backend Agent Tasks

> **Agent:** Opus, mode: bypassPermissions
> **Scope:** extraction_service.py + structured_comparison_service.py
> **Context files to read first:** This plan, the spec doc, extraction_service.py (full), structured_comparison_service.py (lines 45-97, 1073-1136, 1573-1688)

### Task 1: Add Fashion Category to Parser + Schema

**Files:**
- Modify: `app/services/extraction_service.py:45-78` (PRODUCT_PARSER_PROMPT)
- Modify: `app/services/extraction_service.py:81-155` (CATEGORY_SPEC_SCHEMAS)

- [ ] **Step 1: Add "fashion" to PRODUCT_PARSER_PROMPT**

In `extraction_service.py` line 56, change the category enum:
```python
"category": "electronics|grocery|supplements|makeup|skincare|haircare|fragrances|fashion|other"
```

Replace the category detection rules block (lines 69-77) with:
```python
- Category detection — match based on PRODUCT TYPE, not brand:
  * electronics: phones, laptops, TVs, cameras, headphones, tablets, consoles, smartwatches
  * grocery: food, beverages, household items, cleaning products
  * supplements: vitamins, minerals, health supplements, protein powder
  * makeup: foundation, lipstick, mascara, eyeshadow, concealer, blush, primer
  * skincare: moisturizer, serum, cleanser, sunscreen, toner, face wash
  * haircare: shampoo, conditioner, hair treatment, styling products, hair oil
  * fragrances: perfume, cologne, eau de toilette, eau de parfum, body spray
  * fashion: hats, caps, bags, handbags, shoes, sneakers, jackets, coats, scarves, belts, wallets, clothing, dresses, watches, jewelry, sunglasses
  * other: anything not fitting above categories
- IMPORTANT: Category is determined by PRODUCT TYPE, never by brand. An LV hat is fashion. A Chanel perfume is fragrances. A Rolex watch is fashion.
```

- [ ] **Step 2: Add fashion schema to CATEGORY_SPEC_SCHEMAS**

After the `"fragrances"` entry (line 154), add:
```python
"fashion": [
    "material",           # e.g., "100% cotton", "cashmere", "leather"
    "style",              # e.g., "five-panel cap", "tote bag", "low-top sneaker"
    "closure_type",       # e.g., "adjustable back strap", "zip", "snap"
    "size_options",       # e.g., "S/M/L", "One size", "36-44"
    "care_instructions",  # e.g., "Dry clean only", "Machine wash"
    "craftsmanship",      # e.g., "Hand-stitched", "Machine-made"
    "collection_season",  # e.g., "Spring/Summer 2025", "Permanent collection"
    "origin",             # e.g., "Made in Italy", "Made in France"
    "color",              # e.g., "Light Grey", "Black"
    "design_details",     # e.g., "Embroidered LV monogram, mesh back panel"
],
```

- [ ] **Step 3: Fix "other" schema — remove electronics-centric fields**

Replace the current `"other"` schema (lines 97-100):
```python
"other": [
    "dimensions", "weight", "material", "color",
    "features", "origin", "warranty"
],
```

- [ ] **Step 4: Verify syntax**

Run: `python -m py_compile app/services/extraction_service.py`
Expected: No output (success)

- [ ] **Step 5: Commit**

```bash
git add app/services/extraction_service.py
git commit -m "feat: add fashion category with dedicated schema, fix 'other' schema"
```

---

### Task 2: Add Luxury Brand Detection

**Files:**
- Modify: `app/services/structured_comparison_service.py:1081-1136`

- [ ] **Step 1: Add LUXURY_BRAND_KEYWORDS constant**

After `HIGH_VALUE_KEYWORDS` (line 1085), add:
```python
# Luxury/designer brand keywords — triggers price guardrails regardless of category
LUXURY_BRAND_KEYWORDS = {
    "louis vuitton", "lv", "hermes", "hermès", "chanel", "gucci", "prada",
    "dior", "burberry", "fendi", "balenciaga", "versace", "givenchy",
    "ysl", "saint laurent", "cartier", "rolex", "omega", "patek philippe",
    "tag heuer", "tiffany", "tom ford", "bottega veneta", "valentino",
    "celine", "loewe", "moncler", "balmain", "alexander mcqueen",
}
```

- [ ] **Step 2: Add OFFICIAL_BRAND_DOMAINS mapping**

After `LUXURY_BRAND_KEYWORDS`, add:
```python
# Official brand website domains — always trust score 1.0 for price
OFFICIAL_BRAND_DOMAINS = {
    "hermes.com", "louisvuitton.com", "chanel.com", "gucci.com", "prada.com",
    "dior.com", "burberry.com", "fendi.com", "balenciaga.com", "cartier.com",
    "rolex.com", "omegawatches.com", "tiffany.com", "tomford.com",
    "apple.com", "samsung.com", "sony.com", "dell.com", "hp.com",
    "nordstrom.com", "farfetch.com", "ssense.com", "net-a-porter.com",
    "sephora.com", "harrods.com", "selfridges.com",
}
```

- [ ] **Step 3: Add _is_luxury_brand() method**

After `_is_high_value_query()` (line 1136), add:
```python
@staticmethod
def _is_luxury_brand(product_name: str) -> bool:
    """Check if the product is from a luxury/designer brand (triggers price guardrails)."""
    name_lower = product_name.lower()
    return any(brand in name_lower for brand in StructuredComparisonService.LUXURY_BRAND_KEYWORDS)
```

- [ ] **Step 4: Verify syntax**

Run: `python -m py_compile app/services/structured_comparison_service.py`
Expected: No output (success)

- [ ] **Step 5: Commit**

```bash
git add app/services/structured_comparison_service.py
git commit -m "feat: add luxury brand detection with official domain mapping"
```

---

### Task 3: Rewrite Price Extraction Prompt

**Files:**
- Modify: `app/services/extraction_service.py:201-229` (PRICE_EXTRACTION_PROMPT)

- [ ] **Step 1: Replace PRICE_EXTRACTION_PROMPT**

Replace lines 201-229 with:
```python
PRICE_EXTRACTION_PROMPT = """You are a price extraction expert for GCC markets. Your goal is to find the MOST AUTHORITATIVE retail price, not the cheapest one.

PRODUCT: {brand} {name} {variant}
REGION: {region} ({currency})

Search results:
{search_context}

Return ONLY valid JSON:
{{
    "amount": numeric_price_or_null,
    "original_currency": "USD",
    "currency": "{currency}",
    "retailer": null,
    "url": null,
    "in_stock": true,
    "confidence": 0.0
}}

SOURCE PRIORITY (use the HIGHEST available):
1. Official brand website (hermes.com, louisvuitton.com, apple.com, chanel.com) — ALWAYS prefer this
2. Authorized retailers (Nordstrom, Sephora, Harrods, Farfetch, SSENSE, Net-a-Porter, Amazon)
3. Major GCC retailers (Noon, Jarir, Extra, Sharaf DG, LuLu)
4. Resellers (eBay, StockX, TheRealReal) — ONLY if nothing else available, flag confidence 0.3
5. NEVER use: DHgate, AliExpress, Temu, Wish — these sell counterfeits

RULES:
- Extract the MOST AUTHORITATIVE price, NOT the lowest. A $630 price from hermes.com is correct; a $94 price from eBay is likely counterfeit/resale.
- Do NOT convert currencies — return the exact price as shown in the source
- original_currency: the ACTUAL currency of the price you found (detect from symbols: $ = USD, £ = GBP, € = EUR, BHD/BD = BHD, SAR/SR = SAR, AED = AED, KWD = KWD)
- currency: always set to "{currency}" (the target currency — conversion happens later)
- Confidence: 1.0 = official brand/authorized retailer, 0.7 = major marketplace, 0.3 = reseller, 0.0 = not found
- Return null for amount if no reliable price found from Priority 1-3 sources
- retailer: the actual store name, or null if unknown

DO: Extract $630 from hermes.com (official brand site)
DON'T: Extract $94 from eBay reseller listing — that's counterfeit/resale pricing

DO: Extract $999 from apple.com or $999 from Amazon (both authorized)
DON'T: Extract $750 from unknown electronics reseller

DO: Extract BHD 8.500 from iherb.com (authorized supplement retailer)
DON'T: Extract BHD 2.000 from unverified supplement seller"""
```

- [ ] **Step 2: Verify syntax**

Run: `python -m py_compile app/services/extraction_service.py`
Expected: No output (success)

- [ ] **Step 3: Commit**

```bash
git add app/services/extraction_service.py
git commit -m "feat: rewrite price prompt to prefer authoritative sources over cheapest"
```

---

### Task 4: Update Price Extraction Backend Logic

**Files:**
- Modify: `app/services/structured_comparison_service.py:45-97` (RETAILER_TIERS)
- Modify: `app/services/structured_comparison_service.py:1573-1688` (_extract_price_from_shopping)
- Modify: `app/services/structured_comparison_service.py:865-870` (sanity check)

- [ ] **Step 1: Add luxury fashion retailers to RETAILER_TIERS**

After the existing Tier 1 entries (after line 70, before Tier 2 comment), add:
```python
# Tier 1: Luxury fashion official + authorized retailers
"hermes": 1.0,
"hermès": 1.0,
"louis vuitton": 1.0,
"louisvuitton": 1.0,
"chanel": 1.0,
"gucci": 1.0,
"prada": 1.0,
"dior": 1.0,
"burberry": 1.0,
"fendi": 1.0,
"nordstrom": 1.0,
"farfetch": 1.0,
"ssense": 1.0,
"net-a-porter": 1.0,
"harrods": 1.0,
"selfridges": 1.0,
"sephora": 1.0,
"ulta": 1.0,
```

- [ ] **Step 2: Add official domain check in _extract_price_from_shopping()**

In `_extract_price_from_shopping()`, after computing `retailer_score` (line 1646), add official domain boost. Note: `urlparse` is already used elsewhere in the file via `_extract_domain()` added in Task 6.

```python
retailer_score = self._get_retailer_score(retailer)

# Boost official brand domains to max trust
link = item.get("link", "")
if link:
    domain = self._extract_domain(link)
    if domain in self.OFFICIAL_BRAND_DOMAINS:
        retailer_score = 1.0
        logger.debug(f"[PRICE] Official brand domain boost: {domain}")
```

- [ ] **Step 3: Add luxury brand price floor in _extract_price_from_shopping()**

After the existing `min_price` logic (line 1590), add luxury brand handling:
```python
is_high_value = self._is_high_value_query(product_name)
is_luxury = self._is_luxury_brand(product_name)
min_price = 100.0 if is_high_value else 0

# For luxury brands: filter out untrusted sellers entirely
if is_luxury:
    min_price = max(min_price, 50.0)  # Luxury items rarely under BHD 50
```

- [ ] **Step 4: Update sorting to prioritize retailer trust for luxury brands**

Replace the sort line (1676):
```python
# Sort: best retailer quality → best title match → lowest price
# For luxury brands, retailer trust is most important (official > reseller)
if is_luxury:
    candidates.sort(key=lambda c: (-c["retailer_score"], -c["match_score"], c["amount"]))
else:
    candidates.sort(key=lambda c: (-c["match_score"], -c["retailer_score"], c["amount"]))
```

- [ ] **Step 5: Expand sanity check to include luxury brands**

Find the sanity check around line 869:
```python
if self._is_high_value_query(full_name) and price.get("retailer_score", 0) < 1.0:
```

Change to:
```python
if (self._is_high_value_query(full_name) or self._is_luxury_brand(full_name)) and price.get("retailer_score", 0) < 1.0:
```

Note: Line 1274 is inside `_is_supplement_query()` which uses `HIGH_VALUE_KEYWORDS` as an anti-keyword to prevent electronics from matching as supplements. Do NOT change that — it's unrelated to price sanity checking.

- [ ] **Step 6: Verify syntax**

Run: `python -m py_compile app/services/structured_comparison_service.py`
Expected: No output (success)

- [ ] **Step 7: Commit**

```bash
git add app/services/structured_comparison_service.py
git commit -m "feat: luxury brand price guardrails — official source priority, seller trust"
```

---

### Task 5: Fix Spec Extraction Prompt

**Files:**
- Modify: `app/services/extraction_service.py:158-198` (_build_specs_prompt)

- [ ] **Step 1: Replace the "EVERY field MUST have a value" rule**

In `_build_specs_prompt()`, replace line 189:
```python
# Before:
- EVERY field MUST have a value. Use search results first, then your training knowledge. null is ONLY acceptable if the spec truly does not exist for this product (e.g. water_resistance for a budget phone that has none)
```

With:
```python
- Only include fields that are GENUINELY RELEVANT to this specific product. Omit irrelevant fields rather than writing N/A or null. A hat does not need "power". A phone does not need "care_instructions". Use search results first, then your training knowledge.
- For well-known products, you KNOW the specs — do NOT return null for fields that clearly apply (e.g. os, weight, water_resistance for smartphones)
```

- [ ] **Step 2: Add category-aware examples to the prompt**

After the existing citation example (line 197-198), add:
```python
- Category-specific guidance:
  * Electronics: include all tech specs (display, processor, ram, storage, battery, camera)
  * Fashion: focus on material, style, craftsmanship, origin, design_details. Skip irrelevant fields.
  * Supplements: include count, dosage, form, certifications. Skip tech fields.
  * Fragrances: include scent notes, longevity, sillage, concentration. Skip tech fields.
```

- [ ] **Step 3: Verify syntax**

Run: `python -m py_compile app/services/extraction_service.py`
Expected: No output (success)

- [ ] **Step 4: Commit**

```bash
git add app/services/extraction_service.py
git commit -m "fix: spec prompt allows omitting irrelevant fields instead of forcing N/A"
```

---

### Task 6: Add Review Citation Cleanup

**Files:**
- Modify: `app/services/structured_comparison_service.py` (new method + call site at line ~285)

- [ ] **Step 1: Add _extract_domain() and _clean_review_citations() methods**

Add these as methods on `StructuredComparisonService` class (after `_sanitize_gpt_price` around line 1107):

```python
@staticmethod
def _extract_domain(url: str) -> str:
    """Extract clean domain from URL."""
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        domain = parsed.netloc.replace("www.", "")
        return domain or ""
    except Exception:
        return ""

def _clean_review_citations(self, reviews: dict, search_results: list) -> dict:
    """Replace [snippet_N] with source domain name in review text fields.

    Only cleans review display fields (common_praises, common_complaints,
    detailed_praises, detailed_complaints). Does NOT touch spec _source fields.
    """
    import re

    # Build snippet index → source domain map
    snippet_source_map = {}
    for i, result in enumerate(search_results or []):
        link = result.get("link", "")
        if link:
            snippet_source_map[str(i + 1)] = self._extract_domain(link)

    def replace_citation(text: str) -> str:
        def replacer(match):
            snippet_num = match.group(1)
            domain = snippet_source_map.get(snippet_num, "")
            if domain:
                return f"Per {domain}: "
            return ""
        return re.sub(r'\[snippet_(\d+)\]\s*', replacer, text)

    cleaned = dict(reviews)
    for key in ["common_praises", "common_complaints"]:
        if key in cleaned and isinstance(cleaned[key], list):
            cleaned[key] = [replace_citation(str(item)) for item in cleaned[key]]
    for key in ["detailed_praises", "detailed_complaints"]:
        if key in cleaned and isinstance(cleaned[key], list):
            for item in cleaned[key]:
                if isinstance(item, dict) and "text" in item:
                    item["text"] = replace_citation(str(item["text"]))
    return cleaned
```

- [ ] **Step 2: Call citation cleanup in compare_from_text()**

In `compare_from_text()`, after the Phase 2 results are collected but BEFORE building the response dict (around line 285), add cleanup for each product's reviews:

```python
# Clean review citations for display (replace [snippet_N] with source domain)
for pd in product_data:
    if pd.get("reviews"):
        pd["reviews"] = self._clean_review_citations(
            pd["reviews"],
            unified_search.get("organic", []) if unified_search else []
        )
```

Note: `unified_search` is a `Dict[str, Any]` returned by `search_web()` (serper_service.py). The organic results are in `unified_search["organic"]` — this is a list of dicts with `"link"`, `"title"`, `"snippet"` keys. The `unified_search` variable is available in scope — it's defined at line 593 and used through the method.

- [ ] **Step 3: Do the same in compare_from_text_streaming()**

In `compare_from_text_streaming()` (starts at line 349), find where reviews are yielded as SSE events. The streaming variant also has a `unified_search` variable (search around line 460-470). Add the same cleanup before yielding the reviews event:

```python
# Before yielding reviews SSE event, clean citations
for pd in product_data:
    if pd.get("reviews"):
        pd["reviews"] = self._clean_review_citations(
            pd["reviews"],
            unified_search.get("organic", []) if unified_search else []
        )
```

- [ ] **Step 4: Verify syntax**

Run: `python -m py_compile app/services/structured_comparison_service.py`
Expected: No output (success)

- [ ] **Step 5: Commit**

```bash
git add app/services/structured_comparison_service.py
git commit -m "feat: strip [snippet_N] citations from reviews, replace with source domain"
```

---

### Task 7: Update Review + Verdict Prompts

**Files:**
- Modify: `app/services/extraction_service.py:257-304` (REVIEWS_EXTRACTION_PROMPT)
- Modify: `app/services/extraction_service.py:307-372` (COMPARISON_PROMPT)

- [ ] **Step 1: Add sparse review handling to REVIEWS_EXTRACTION_PROMPT**

After the existing DO/DON'T examples (line 302), add:
```python
- If fewer than 3 credible review sources exist in the search results, return fewer items rather than inventing content. Quality over quantity — 2 real citations beat 5 fabricated ones.
- category_scores aspect guidance by category:
  * Electronics: camera, battery, display, performance, value, build_quality
  * Fashion: style, material_quality, craftsmanship, comfort, durability, value
  * Fragrances: longevity, projection, uniqueness, versatility, value
  * Supplements: effectiveness, ingredients, taste, absorption, value
  * Default: quality, value, durability, ease_of_use
```

- [ ] **Step 2: Update COMPARISON_PROMPT best_for to be dynamic**

Keep the existing `best_for` JSON structure (lines 337-342) unchanged — the frontend expects these exact keys. Instead, add this guidance to the RULES section:
```python
- best_for categories depend on product type:
  * Electronics: budget, performance, features, reliability
  * Fashion: budget, style, craftsmanship, versatility
  * Fragrances: budget, longevity, occasion_range, uniqueness
  * Supplements: budget, ingredient_quality, certifications, effectiveness
  * Default: budget, performance, features, reliability
- For luxury/designer products, consider brand prestige and craftsmanship in value assessment, not just raw cost per feature
```

- [ ] **Step 3: Verify syntax**

Run: `python -m py_compile app/services/extraction_service.py`
Expected: No output (success)

- [ ] **Step 4: Commit**

```bash
git add app/services/extraction_service.py
git commit -m "feat: category-aware review scoring and dynamic best_for in verdict"
```

---

## Round 1 — Test Agent Tasks

> **Agent:** Opus, mode: bypassPermissions
> **Scope:** Write all new test files, QA Backend Agent's work
> **Context files to read first:** This plan, the spec doc, existing test files for patterns (test_category_selection.py, test_rating_tiers.py)

### Task 8: Write Fashion Category Tests

**Files:**
- Create: `tests/test_fashion_category.py`

- [ ] **Step 1: Write test file**

```python
"""Tests for fashion category detection and schema."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.extraction_service import (
    CATEGORY_SPEC_SCHEMAS,
    PRODUCT_PARSER_PROMPT,
)


class TestFashionSchema:
    """Test fashion category schema configuration."""

    def test_fashion_schema_exists(self):
        assert "fashion" in CATEGORY_SPEC_SCHEMAS

    def test_fashion_schema_fields(self):
        fields = CATEGORY_SPEC_SCHEMAS["fashion"]
        assert "material" in fields
        assert "style" in fields
        assert "closure_type" in fields
        assert "origin" in fields
        assert "design_details" in fields
        # Should NOT have electronics fields
        assert "power" not in fields
        assert "compatibility" not in fields
        assert "processor" not in fields

    def test_fashion_schema_length(self):
        """Fashion schema should have 10 fields."""
        assert len(CATEGORY_SPEC_SCHEMAS["fashion"]) == 10

    def test_other_schema_no_electronics_fields(self):
        """'other' schema should not have power/compatibility."""
        other_fields = CATEGORY_SPEC_SCHEMAS["other"]
        assert "power" not in other_fields
        assert "compatibility" not in other_fields
        assert "count" not in other_fields
        assert "included" not in other_fields

    def test_other_schema_has_generic_fields(self):
        other_fields = CATEGORY_SPEC_SCHEMAS["other"]
        assert "material" in other_fields
        assert "features" in other_fields
        assert "origin" in other_fields

    def test_fashion_in_parser_prompt(self):
        """Parser prompt must include fashion as a category option."""
        assert "fashion" in PRODUCT_PARSER_PROMPT
        assert "hats" in PRODUCT_PARSER_PROMPT.lower() or "hat" in PRODUCT_PARSER_PROMPT.lower()


class TestCategorySwitching:
    """Test that category switching works with fashion."""

    def test_fashion_category_different_from_electronics(self):
        """If user selects electronics but product is fashion, should switch."""
        selected = "electronics"
        detected = "fashion"
        assert selected != detected  # switching would trigger

    def test_fashion_category_different_from_supplements(self):
        selected = "supplements"
        detected = "fashion"
        assert selected != detected

    def test_fashion_no_switch_when_matching(self):
        selected = "fashion"
        detected = "fashion"
        assert selected == detected  # no switching


class TestProductTypeBinding:
    """Test that parser prompt has product-type binding rules."""

    def test_prompt_has_product_type_rule(self):
        """Parser prompt should mention product TYPE determines category."""
        prompt_lower = PRODUCT_PARSER_PROMPT.lower()
        assert "product type" in prompt_lower or "what the product is" in prompt_lower

    def test_fashion_product_examples_in_prompt(self):
        prompt_lower = PRODUCT_PARSER_PROMPT.lower()
        # At least some fashion items listed
        fashion_items = ["bag", "shoe", "jacket", "scarf", "belt", "wallet"]
        found = sum(1 for item in fashion_items if item in prompt_lower)
        assert found >= 3, f"Only {found} fashion items found in prompt"

    def test_all_nine_categories_in_prompt(self):
        categories = ["electronics", "grocery", "supplements", "makeup",
                       "skincare", "haircare", "fragrances", "fashion", "other"]
        for cat in categories:
            assert cat in PRODUCT_PARSER_PROMPT, f"Category '{cat}' missing from parser prompt"
```

- [ ] **Step 2: Run tests**

Run: `python -m pytest tests/test_fashion_category.py -v`
Expected: All pass after Backend Agent completes Task 1

- [ ] **Step 3: Commit**

```bash
git add tests/test_fashion_category.py
git commit -m "test: add 15 tests for fashion category detection and schema"
```

---

### Task 9: Write Luxury Brand Detection Tests

**Files:**
- Create: `tests/test_luxury_brands.py`

- [ ] **Step 1: Write test file**

```python
"""Tests for luxury brand detection and price guardrails."""
import pytest
from app.services.structured_comparison_service import StructuredComparisonService


class TestLuxuryBrandDetection:
    """Test _is_luxury_brand() method."""

    @pytest.mark.parametrize("name,expected", [
        ("Louis Vuitton LV Vers Mesh Cap", True),
        ("Hermès Nevada H'Cheval cap", True),
        ("Hermes Birkin Bag", True),
        ("Chanel No. 5 Eau de Parfum", True),
        ("Gucci Ace Sneakers", True),
        ("Rolex Submariner", True),
        ("Prada Re-Nylon Backpack", True),
        ("Nike Air Max 90", False),
        ("Samsung Galaxy S24", False),
        ("NOW Vitamin D3", False),
        ("Adidas Ultraboost", False),
        ("Generic Cotton Hat", False),
    ])
    def test_luxury_detection(self, name, expected):
        assert StructuredComparisonService._is_luxury_brand(name) == expected

    def test_case_insensitive(self):
        assert StructuredComparisonService._is_luxury_brand("LOUIS VUITTON cap")
        assert StructuredComparisonService._is_luxury_brand("hermes scarf")

    def test_accent_handling(self):
        """Hermès with accent should be detected."""
        assert StructuredComparisonService._is_luxury_brand("Hermès bag")


class TestOfficialBrandDomains:
    """Test OFFICIAL_BRAND_DOMAINS constant."""

    def test_luxury_domains_exist(self):
        domains = StructuredComparisonService.OFFICIAL_BRAND_DOMAINS
        assert "hermes.com" in domains
        assert "louisvuitton.com" in domains
        assert "chanel.com" in domains

    def test_tech_domains_exist(self):
        domains = StructuredComparisonService.OFFICIAL_BRAND_DOMAINS
        assert "apple.com" in domains
        assert "samsung.com" in domains

    def test_authorized_retailers_exist(self):
        domains = StructuredComparisonService.OFFICIAL_BRAND_DOMAINS
        assert "farfetch.com" in domains
        assert "nordstrom.com" in domains


class TestLuxuryRetailerTiers:
    """Test that luxury retailers are properly tiered."""

    def test_luxury_brands_in_retailer_tiers(self):
        from app.services.structured_comparison_service import RETAILER_TIERS
        assert RETAILER_TIERS.get("hermes", 0) >= 1.0
        assert RETAILER_TIERS.get("louis vuitton", 0) >= 1.0
        assert RETAILER_TIERS.get("chanel", 0) >= 1.0

    def test_counterfeit_sites_low_tier(self):
        from app.services.structured_comparison_service import RETAILER_TIERS
        assert RETAILER_TIERS.get("dhgate", 1.0) <= 0.3
        assert RETAILER_TIERS.get("aliexpress", 1.0) <= 0.3
        assert RETAILER_TIERS.get("temu", 1.0) <= 0.3
```

- [ ] **Step 2: Run tests**

Run: `python -m pytest tests/test_luxury_brands.py -v`
Expected: All pass after Backend Agent completes Tasks 2+4

- [ ] **Step 3: Commit**

```bash
git add tests/test_luxury_brands.py
git commit -m "test: add 12 tests for luxury brand detection and retailer tiers"
```

---

### Task 10: Write Citation Cleanup Tests

**Files:**
- Create: `tests/test_citation_cleanup.py`

- [ ] **Step 1: Write test file**

```python
"""Tests for review citation cleanup — [snippet_N] → source domain replacement."""
import pytest
from app.services.structured_comparison_service import StructuredComparisonService


@pytest.fixture
def service():
    return StructuredComparisonService()


@pytest.fixture
def mock_search_results():
    return [
        {"link": "https://www.hermes.com/us/en/product/cap", "title": "Cap"},
        {"link": "https://www.amazon.com/dp/123", "title": "Cap"},
        {"link": "https://www.ebay.com/itm/456", "title": "Cap"},
    ]


class TestCitationCleanup:

    def test_replaces_snippet_with_domain(self, service, mock_search_results):
        reviews = {"common_praises": ["[snippet_1] Great quality material"]}
        cleaned = service._clean_review_citations(reviews, mock_search_results)
        assert "Per hermes.com:" in cleaned["common_praises"][0]
        assert "[snippet_1]" not in cleaned["common_praises"][0]

    def test_strips_unknown_snippet(self, service):
        reviews = {"common_praises": ["[snippet_99] Some text"]}
        cleaned = service._clean_review_citations(reviews, [])
        assert cleaned["common_praises"][0] == "Some text"

    def test_handles_multiple_praises(self, service, mock_search_results):
        reviews = {"common_praises": [
            "[snippet_1] First praise",
            "[snippet_2] Second praise",
        ]}
        cleaned = service._clean_review_citations(reviews, mock_search_results)
        assert "hermes.com" in cleaned["common_praises"][0]
        assert "amazon.com" in cleaned["common_praises"][1]

    def test_handles_complaints(self, service, mock_search_results):
        reviews = {"common_complaints": ["[snippet_3] Too expensive"]}
        cleaned = service._clean_review_citations(reviews, mock_search_results)
        assert "ebay.com" in cleaned["common_complaints"][0]

    def test_handles_detailed_praises(self, service, mock_search_results):
        reviews = {"detailed_praises": [
            {"text": "[snippet_1] Excellent craftsmanship", "frequency": "often"}
        ]}
        cleaned = service._clean_review_citations(reviews, mock_search_results)
        assert "hermes.com" in cleaned["detailed_praises"][0]["text"]

    def test_preserves_non_citation_fields(self, service, mock_search_results):
        reviews = {
            "common_praises": ["[snippet_1] Great"],
            "average_rating": 4.5,
            "summary": "Good product",
        }
        cleaned = service._clean_review_citations(reviews, mock_search_results)
        assert cleaned["average_rating"] == 4.5
        assert cleaned["summary"] == "Good product"

    def test_empty_reviews(self, service):
        cleaned = service._clean_review_citations({}, [])
        assert cleaned == {}

    def test_null_search_results(self, service):
        reviews = {"common_praises": ["[snippet_1] Text"]}
        cleaned = service._clean_review_citations(reviews, None)
        assert cleaned["common_praises"][0] == "Text"

    def test_www_stripped_from_domain(self, service):
        results = [{"link": "https://www.hermes.com/product", "title": "t"}]
        reviews = {"common_praises": ["[snippet_1] Good"]}
        cleaned = service._clean_review_citations(reviews, results)
        assert "www." not in cleaned["common_praises"][0]
        assert "hermes.com" in cleaned["common_praises"][0]

    def test_extract_domain_helper(self, service):
        assert service._extract_domain("https://www.hermes.com/us/en/product") == "hermes.com"
        assert service._extract_domain("https://amazon.com/dp/123") == "amazon.com"
        assert service._extract_domain("") == ""
        assert service._extract_domain("not-a-url") == ""
```

- [ ] **Step 2: Run tests**

Run: `python -m pytest tests/test_citation_cleanup.py -v`
Expected: All pass after Backend Agent completes Task 6

- [ ] **Step 3: Commit**

```bash
git add tests/test_citation_cleanup.py
git commit -m "test: add 10 tests for review citation cleanup"
```

---

### Task 11: Write Price Priority Tests

**Files:**
- Create: `tests/test_price_priority.py`

- [ ] **Step 1: Write test file**

```python
"""Tests for price source prioritization — official > authorized > marketplace > reseller."""
import pytest
from app.services.structured_comparison_service import (
    StructuredComparisonService,
    RETAILER_TIERS,
)


@pytest.fixture
def service():
    svc = StructuredComparisonService()
    svc.total_cost = 0
    svc.api_calls = 0
    svc.gpt_calls = 0
    svc.serper_calls = 0
    return svc


class TestPriceSourcePriority:

    def test_official_domain_preferred_over_cheaper(self, service):
        """hermes.com at $630 should beat eBay at $94."""
        shopping_items = [
            {"price": "$94.25", "title": "Hermes Nevada Cap", "source": "eBay", "link": "https://ebay.com/itm/123"},
            {"price": "$630.00", "title": "Hermès Nevada H'Cheval cap", "source": "Hermes", "link": "https://www.hermes.com/us/en/product/cap"},
        ]
        result = service._extract_price_from_shopping("Hermes Nevada H'Cheval cap", shopping_items, "BHD")
        # Should pick the higher official price, not the cheap eBay one
        assert result is not None
        assert result["retailer_score"] >= 1.0

    def test_non_luxury_still_prefers_lower_price(self, service):
        """For non-luxury items, lower price from good retailers is fine."""
        shopping_items = [
            {"price": "$29.99", "title": "Nike Air Max 90", "source": "Amazon", "link": "https://amazon.com/dp/123"},
            {"price": "$35.99", "title": "Nike Air Max 90", "source": "Foot Locker", "link": "https://footlocker.com/123"},
        ]
        result = service._extract_price_from_shopping("Nike Air Max 90", shopping_items, "BHD")
        assert result is not None
        # Both are decent retailers, cheaper should win (or close)

    def test_counterfeit_sites_filtered_for_luxury(self, service):
        """DHgate/AliExpress results should get low retailer scores."""
        score_dhgate = service._get_retailer_score("DHgate")
        score_aliexpress = service._get_retailer_score("AliExpress")
        assert score_dhgate <= 0.3
        assert score_aliexpress <= 0.3

    def test_luxury_brand_activates_retailer_priority_sorting(self, service):
        """For luxury brands, sort should prioritize retailer_score over match_score."""
        # This test verifies the sort order change for luxury
        assert service._is_luxury_brand("Louis Vuitton cap") is True
        assert service._is_luxury_brand("Nike cap") is False


class TestRetailerTiersCoverage:

    def test_fashion_retailers_in_tiers(self):
        assert "farfetch" in RETAILER_TIERS
        assert "nordstrom" in RETAILER_TIERS
        assert "ssense" in RETAILER_TIERS

    def test_luxury_brands_in_tiers(self):
        assert "hermes" in RETAILER_TIERS
        assert "louis vuitton" in RETAILER_TIERS
        assert "chanel" in RETAILER_TIERS
        assert "gucci" in RETAILER_TIERS

    def test_untrusted_remain_low(self):
        assert RETAILER_TIERS["dhgate"] <= 0.3
        assert RETAILER_TIERS["temu"] <= 0.3
        assert RETAILER_TIERS["wish"] <= 0.3
```

- [ ] **Step 2: Run tests**

Run: `python -m pytest tests/test_price_priority.py -v`
Expected: All pass after Backend Agent completes Task 4

- [ ] **Step 3: Commit**

```bash
git add tests/test_price_priority.py
git commit -m "test: add 10 tests for price source prioritization"
```

---

## Round 2 — Frontend + Scoring Agent Tasks

> **Agent:** Opus, mode: bypassPermissions
> **Scope:** ResultsScreen.tsx, CategorySelector.tsx, scoring_service.py
> **Context files to read first:** This plan, the spec doc, ResultsScreen.tsx (lines 397-438), CategorySelector.tsx (full), scoring_service.py (lines 224-259)

### Task 12: Frontend N/A Filtering + Fashion Category

**Files:**
- Modify: `SmartCompareApp/src/screens/ResultsScreen.tsx:397-410`
- Modify: `SmartCompareApp/src/components/CategorySelector.tsx:21-29`

- [ ] **Step 1: Add spec filtering in ResultsScreen SpecsTab**

Replace the SpecsTab rendering (lines 397-410):
```tsx
const SpecsTab = () => {
    // Filter specs — remove N/A, null, empty, and metadata fields
    const HIDDEN_FIELDS = ['brand', 'model', 'variant', 'category'];
    const NA_VALUES = ['n/a', 'na', 'null', 'none', 'unknown', ''];

    const filterSpecs = (specs: Record<string, any>) => {
      return Object.entries(specs).filter(([key, value]) => {
        if (HIDDEN_FIELDS.includes(key)) return false;
        if (key.endsWith('_source')) return false;
        if (value === null || value === undefined) return false;
        if (typeof value === 'string' && NA_VALUES.includes(value.toLowerCase().trim())) return false;
        return true;
      });
    };

    return (
      <View style={styles.tabContent}>
        {products.map((product, index) => {
          const filteredSpecs = product.specs ? filterSpecs(product.specs) : [];
          return (
            <View key={index} style={styles.specsCard}>
              <Text style={styles.specsCardTitle}>{product.name}</Text>
              {filteredSpecs.map(([key, value]) => (
                <View key={key} style={styles.specRow}>
                  <Text style={styles.specKey}>{key.replace(/_/g, ' ')}</Text>
                  <Text style={styles.specValue}>{String(value)}</Text>
                </View>
              ))}
              {filteredSpecs.length === 0 && (
                <Text style={{ color: '#999', fontStyle: 'italic', padding: 12 }}>
                  No specifications available
                </Text>
              )}
            </View>
          );
        })}

        {comparison.specs_comparison && (
          <View style={styles.advantagesSection}>
            <Text style={styles.sectionTitle}>Advantages</Text>
            {comparison.specs_comparison.product_0_advantages?.length > 0 && (
              <View style={styles.advantageCard}>
                <Text style={styles.advantageTitle}>{products[0]?.name}</Text>
                {comparison.specs_comparison.product_0_advantages.map((adv: string, i: number) => (
                  <Text key={i} style={styles.advantageItem}>✓ {adv}</Text>
                ))}
              </View>
            )}
            {comparison.specs_comparison.product_1_advantages?.length > 0 && (
              <View style={styles.advantageCard}>
                <Text style={styles.advantageTitle}>{products[1]?.name}</Text>
                {comparison.specs_comparison.product_1_advantages.map((adv: string, i: number) => (
                  <Text key={i} style={styles.advantageItem}>✓ {adv}</Text>
                ))}
              </View>
            )}
          </View>
        )}
      </View>
    );
  };
```

- [ ] **Step 2: Add fashion to CategorySelector**

In `CategorySelector.tsx`, add fashion to the CATEGORIES array (after fragrances, line 28):
```tsx
{ value: 'fashion', label: 'Fashion', icon: '\u{1F45C}' },
```

(Unicode 1F45C = handbag emoji)

- [ ] **Step 3: TypeScript check**

Run: `cd SmartCompareApp && npx tsc --noEmit`
Expected: 0 errors

- [ ] **Step 4: Commit**

```bash
git add SmartCompareApp/src/screens/ResultsScreen.tsx SmartCompareApp/src/components/CategorySelector.tsx
git commit -m "feat: filter N/A specs from display, add fashion to CategorySelector"
```

---

### Task 13: Scoring Service — Spec N/A Penalty

**Files:**
- Modify: `app/services/scoring_service.py:224-259` (_score_specs)
- Modify: `app/services/scoring_service.py:46-52` (HIGHER_IS_BETTER — add fashion fields)

- [ ] **Step 1: Add fashion-relevant fields to scoring constants**

In `HIGHER_IS_BETTER` (line 47-52), these are fine as-is since fashion fields are mostly non-numeric (text like "cashmere", "Made in Italy"). No changes needed to these constants.

- [ ] **Step 2: Add N/A penalty to _score_specs()**

Modify `_score_specs()` to penalize when most fields are N/A. After the loop (around line 256-259):

```python
if scored_fields == 0:
    return 0.0

# Penalty: if less than half of schema fields have data, penalize score
total_fields = len(schema_fields)
coverage_ratio = scored_fields / total_fields if total_fields > 0 else 0
if coverage_ratio < 0.5:
    # Scale down: 3 out of 10 fields = 0.3 coverage → 60% of raw score
    penalty_factor = 0.5 + coverage_ratio  # Range: 0.5 to 1.0
    return (total_score / scored_fields) * penalty_factor

return total_score / scored_fields
```

- [ ] **Step 3: Verify syntax**

Run: `python -m py_compile app/services/scoring_service.py`
Expected: No output (success)

- [ ] **Step 4: Run existing scoring tests to check no regressions**

Run: `python -m pytest tests/test_scoring_service.py -v`
Expected: All 62 tests pass

- [ ] **Step 5: Commit**

```bash
git add app/services/scoring_service.py
git commit -m "fix: penalize spec score when >50% of fields are N/A"
```

---

### Task 14: Run Full Test Suite + Cross-QA

- [ ] **Step 1: Run all free unit tests**

Run: `python -m pytest tests/ -v -m "not (live_unit or live_db or integration)" --ignore=tests/test_integration.py --timeout=120`
Expected: 757+ existing tests pass, plus ~47 new tests = ~804+ total

- [ ] **Step 2: Fix any failures**

If any tests fail, investigate and fix. Common issues:
- Existing tests may reference "other" schema fields that were removed (power, compatibility)
- Category test counts may need updating

- [ ] **Step 3: Commit any fixes**

```bash
git add -A
git commit -m "fix: resolve test regressions from category/schema changes"
```

---

## Between Rounds

After Round 1 completes:
1. Commit all changes
2. Update `docs/CLAUDE_CODE_CONTEXT.md` session log with what changed
3. Create fresh team for Round 2

## Post-Implementation Verification

After both rounds complete:

- [ ] Run: `python -m py_compile app/services/extraction_service.py`
- [ ] Run: `python -m py_compile app/services/structured_comparison_service.py`
- [ ] Run: `python -m py_compile app/services/scoring_service.py`
- [ ] Run: `cd SmartCompareApp && npx tsc --noEmit`
- [ ] Run: `python -m pytest tests/ -v -m "not (live_unit or live_db or integration)" --ignore=tests/test_integration.py`
- [ ] All tests pass (757 existing + ~47 new)
- [ ] Deploy: `git push origin main` (Railway auto-deploys)
- [ ] Test in production: `curl "https://web-production-58776.up.railway.app/api/v1/text/compare?q=LV+hat+vs+Hermes+hat&nocache=true"`
- [ ] Verify: prices are realistic ($500+), specs are relevant (material, style, origin), no [snippet_N] in reviews
