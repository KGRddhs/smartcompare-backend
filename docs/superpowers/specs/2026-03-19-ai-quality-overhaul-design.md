# AI Quality Overhaul — Design Spec

**Date:** 2026-03-19 (Session 25)
**Status:** Reviewed (spec review passed with revisions applied)
**Problem:** AI results are wrong for luxury/fashion products — wrong prices, irrelevant specs, raw citations in reviews, broken category detection

## Problem Statement

Comparing "LV hat vs Hermes hat" reveals systemic failures:
- **Price:** BHD 56.55 (LV) and BHD 94.25 (Hermes) shown. Real prices: LV ~$600, Hermes $630. Official hermes.com price was IN the search results but ignored.
- **Specs:** "other" schema used — shows Power, Compatibility, Count (all N/A) for a hat
- **Reviews:** Raw `[snippet_1]` citations visible to users
- **Category:** No "fashion" category exists. No switching detected or shown.

### Root Causes

1. **Price extraction prompt** says "extract the LOWEST reasonable new retail price" — picks counterfeit/reseller prices over official
2. **`HIGH_VALUE_KEYWORDS`** only contains electronics brands — luxury brands not recognized as high-value
3. **No fashion category** in `CATEGORY_SPEC_SCHEMAS` — hats fall to "other" with electronics-centric fields
4. **"EVERY field MUST have a value"** in spec prompt forces N/A spam
5. **`[snippet_N]` citations** not stripped before sending to frontend
6. **Category switching** can't fire because "fashion" doesn't exist as a detection target

## Design

### 1. Category System Overhaul (ALL categories)

**Add "fashion" as 9th category** with clear product-type bindings in `PRODUCT_PARSER_PROMPT`:

```
electronics: phones, laptops, TVs, cameras, headphones, tablets, consoles, smartwatches
grocery: food, beverages, household items, cleaning products
supplements: vitamins, minerals, health supplements, protein powder
makeup: foundation, lipstick, mascara, eyeshadow, concealer, blush, primer
skincare: moisturizer, serum, cleanser, sunscreen, toner, face wash
haircare: shampoo, conditioner, hair treatment, styling products, hair oil
fragrances: perfume, cologne, eau de toilette, eau de parfum, body spray
fashion: hats, caps, bags, handbags, shoes, sneakers, jackets, coats, scarves, belts, wallets, clothing, dresses, watches, jewelry, sunglasses
other: anything not fitting above categories
```

**Product-category binding rule** added to parser prompt:
> "Match products to categories based on what the product IS, not the brand. An LV hat is fashion (it's a hat). A Chanel perfume is fragrances (it's perfume). A Rolex is fashion (it's a watch/accessory). Category is determined by product type, NEVER by brand."

**Exact insertion point:** In `PRODUCT_PARSER_PROMPT` (extraction_service.py line 56), change `"category"` enum to include `fashion`:
```python
"category": "electronics|grocery|supplements|makeup|skincare|haircare|fragrances|fashion|other"
```
And replace the category detection rules block (lines 69-77) with the expanded product-type bindings above, plus the product-category binding rule.

**Files:** `app/services/extraction_service.py` (PRODUCT_PARSER_PROMPT lines 45-78, CATEGORY_SPEC_SCHEMAS lines 81-155)

### 2. Per-Category Spec Schemas

**New fashion schema:**
```python
"fashion": [
    "material", "style", "closure_type", "size_options",
    "care_instructions", "craftsmanship", "collection_season",
    "origin", "color", "design_details"
]
```

**Fix "other" schema** — remove electronics-centric fields:
```python
# Before:
"other": ["count", "dimensions", "weight", "material", "color", "warranty", "power", "features", "included", "compatibility", "origin"]
# After:
"other": ["dimensions", "weight", "material", "color", "features", "origin", "warranty"]
```

**Smart field handling (ALL categories):**
- Change spec prompt from "EVERY field MUST have a value" to: "Only include fields genuinely relevant to this specific product. Omit irrelevant fields rather than writing N/A. A hat does not need 'power'. A phone does not need 'care_instructions'."
- Frontend filters out any remaining N/A values before rendering Specs tab

**Files:** `app/services/extraction_service.py` (schemas, spec prompt), `SmartCompareApp/src/screens/ResultsScreen.tsx` (N/A filtering)

### 3. Luxury Brand Detection (Category-Independent)

**New `LUXURY_BRAND_KEYWORDS` constant** — separate from `HIGH_VALUE_KEYWORDS`, triggers price guardrails regardless of detected category:

```python
LUXURY_BRAND_KEYWORDS = [
    "louis vuitton", "lv", "hermes", "hermès", "chanel", "gucci", "prada",
    "dior", "burberry", "fendi", "balenciaga", "versace", "givenchy",
    "ysl", "saint laurent", "cartier", "rolex", "omega", "patek philippe",
    "tag heuer", "tiffany", "tom ford", "bottega veneta", "valentino",
    "celine", "loewe", "moncler", "balmain", "alexander mcqueen"
]
```

**Detection function:**
```python
@staticmethod
def _is_luxury_brand(product_name: str) -> bool:
    name_lower = product_name.lower()
    return any(brand in name_lower for brand in LUXURY_BRAND_KEYWORDS)
```

Triggers:
- Price sanity check (reject Serper Shopping if <40% of GPT estimate)
- Seller trust scoring (prefer official brand domains)
- Prompt enrichment (tell GPT to prefer official sources)

**Two-layer defense:**
| Rule | Triggered by | Fails if category wrong? |
|------|-------------|------------------------|
| Fashion spec schema | Category = "fashion" | Yes — N/A filtering still cleans up |
| Luxury price guardrails | Brand name (LUXURY_BRANDS) | No — works regardless |
| Seller trust scoring | Brand name | No — works regardless |
| Citation stripping | Always (all categories) | No |
| N/A filtering | Always (all categories) | No |

**Files:** `app/services/structured_comparison_service.py`

### 4. Price Extraction Overhaul (ALL categories)

**Prompt rewrite — key rule change:**
```
# Before:
"Compare ALL prices shown in the results and extract the LOWEST reasonable new retail price"

# After:
"Extract the MOST AUTHORITATIVE retail price. Prioritize official brand websites and authorized retailers over marketplace/reseller listings. A higher price from an official source is MORE RELIABLE than a lower price from an unknown seller."
```

**Source priority hierarchy** added to prompt:
```
Priority 1: Official brand website (hermes.com, louisvuitton.com, apple.com)
Priority 2: Authorized retailers (Nordstrom, Sephora, Harrods, Farfetch, SSENSE)
Priority 3: Major marketplaces (Amazon) — cross-check against Priority 1-2 if available
Priority 4: Resellers (eBay, StockX, TheRealReal) — flag as "resale", never use as primary
Priority 5: Untrusted (DHgate, AliExpress, Temu, Wish) — REJECT entirely
```

**DO/DON'T examples** covering multiple categories:
```
DO: Extract $630 from hermes.com (official brand site)
DON'T: Extract $94 from eBay reseller listing

DO: Extract $999 from apple.com (official)
DON'T: Extract $750 from unknown electronics reseller

DO: Extract BHD 8.500 from iherb.com (authorized supplement retailer)
DON'T: Extract BHD 2.000 from unverified supplement seller
```

**Backend seller trust scoring** in `_extract_price_from_shopping()`:
- Map known official brand domains → trust score 1.0
- Map authorized retailers → trust score 0.8
- Map major marketplaces → trust score 0.6
- Map known counterfeit risk → trust score 0.1 (effectively rejected)
- When luxury brand detected: require trust score >= 0.6 for primary price

**Luxury brand official domain mapping** — add to `RETAILER_TIERS` or new `OFFICIAL_BRAND_DOMAINS` dict in `structured_comparison_service.py`:
```python
OFFICIAL_BRAND_DOMAINS = {
    "hermes.com": "Hermès", "louisvuitton.com": "Louis Vuitton",
    "chanel.com": "Chanel", "gucci.com": "Gucci", "prada.com": "Prada",
    "dior.com": "Dior", "burberry.com": "Burberry", "fendi.com": "Fendi",
    "balenciaga.com": "Balenciaga", "cartier.com": "Cartier",
    "rolex.com": "Rolex", "omegawatches.com": "Omega",
    "tiffany.com": "Tiffany", "tomford.com": "Tom Ford",
    "apple.com": "Apple", "samsung.com": "Samsung",
}
```
In `_extract_price_from_shopping()`: when iterating Shopping results, check if `link` domain is in `OFFICIAL_BRAND_DOMAINS` → give trust score 1.0, prioritize over lower-priced results from untrusted sellers.

**Note on context truncation:** The current codebase does NOT truncate search context by character count — `_format_numbered_search_results()` formats the first 5 organic results directly. No truncation change needed. The spec reviewer's concern about "2000 to 3000 chars" was based on incorrect assumption. Remove this claim.

**Files:** `app/services/extraction_service.py` (PRICE_EXTRACTION_PROMPT lines 201-229), `app/services/structured_comparison_service.py` (_extract_price_from_shopping, OFFICIAL_BRAND_DOMAINS, sanity check logic)

### 5. Review Citation Cleanup (ALL categories)

**Backend post-processing** — new method `_clean_review_citations()` on `StructuredComparisonService`, called in `compare_from_text()` AFTER fact-checking completes but BEFORE building the response dict. Must NOT touch spec `_source` fields (those use suffix pattern, not inline `[snippet_N]`).

```python
import re
from urllib.parse import urlparse

def _extract_domain(url: str) -> str:
    """Extract clean domain from URL. e.g., 'https://www.hermes.com/us/en/product/...' -> 'hermes.com'"""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.replace("www.", "")
        return domain or ""
    except Exception:
        return ""

def _clean_review_citations(self, reviews: dict, search_results: list) -> dict:
    """Replace [snippet_N] with source domain name, or strip if source unknown.

    Only applies to review text fields (common_praises, common_complaints,
    detailed_praises, detailed_complaints). Does NOT touch spec _source fields.
    """
    # Build snippet index → source domain map from search results
    snippet_source_map = {}
    for i, result in enumerate(search_results):
        link = result.get("link", "")
        if link:
            snippet_source_map[str(i + 1)] = self._extract_domain(link)

    def replace_citation(text: str) -> str:
        def replacer(match):
            snippet_num = match.group(1)
            domain = snippet_source_map.get(snippet_num, "")
            if domain:
                return f"Per {domain}: "
            return ""  # Strip unknown citations entirely
        return re.sub(r'\[snippet_(\d+)\]\s*', replacer, text)

    cleaned = dict(reviews)
    # Clean string lists
    for key in ["common_praises", "common_complaints"]:
        if key in cleaned and isinstance(cleaned[key], list):
            cleaned[key] = [replace_citation(item) for item in cleaned[key]]
    # Clean detailed lists (dict with "text" field)
    for key in ["detailed_praises", "detailed_complaints"]:
        if key in cleaned and isinstance(cleaned[key], list):
            for item in cleaned[key]:
                if isinstance(item, dict) and "text" in item:
                    item["text"] = replace_citation(item["text"])
    return cleaned
```

**Call site:** In `compare_from_text()`, after `_verify_review_sentiment()` runs and before building the final response dict. The search results list is available as `unified_results` (the pre-fetched Serper results).

**Applies to ALL categories** — every comparison gets clean review text.

**Files:** `app/services/structured_comparison_service.py` (new helper + call site)

### 6. Prompt Engineering Improvements (ALL prompts)

**Structured format** for all prompts — Role + Context + Task + Constraints + Examples:

**Spec prompt improvements:**
- Category-aware examples (electronics AND fashion AND supplements shown as examples)
- "Only include fields genuinely relevant to this specific product"

**Review prompt improvements:**
- When reviews are sparse (luxury/niche items): "If fewer than 3 credible review sources exist, return fewer items rather than inventing content. Quality over quantity."
- Category-specific `category_scores` guidance:
  - Electronics: camera, battery, display, performance, value, build_quality
  - Fashion: style, material_quality, craftsmanship, comfort, durability, value
  - Fragrances: longevity, projection, uniqueness, versatility, value
  - Supplements: effectiveness, ingredients, taste, absorption, value

**Verdict prompt improvements:**
- Dynamic `best_for` categories based on detected category:
  - Electronics: budget, performance, features, reliability
  - Fashion: budget, style, craftsmanship, versatility
  - Fragrances: budget, longevity, occasion_range, uniqueness
  - Default: budget, performance, features, reliability
- "For luxury/designer products, price-to-value comparison should consider brand prestige and craftsmanship, not just raw cost per feature"

**Files:** `app/services/extraction_service.py` (all prompts)

### 7. Scoring Adjustments

- **Spec score penalty:** If >50% of spec fields are N/A or omitted, reduce spec score proportionally (don't give 70/100 for mostly-empty specs)
- **Luxury price scoring:** When luxury brand detected, don't penalize for high price — score based on price relative to category norm, not absolute cost

**Files:** `app/services/scoring_service.py`

### 8. Frontend N/A Filtering

In `ResultsScreen.tsx` Specs tab rendering, add filtering before display:

```tsx
// Filter specs before rendering — remove N/A, null, empty fields
const filterSpecs = (specs: Record<string, any>) => {
  const HIDDEN_FIELDS = ['brand', 'model', 'variant', 'category']; // metadata, not specs
  const NA_VALUES = ['n/a', 'na', 'null', 'none', 'unknown', ''];
  return Object.entries(specs).filter(([key, value]) => {
    if (HIDDEN_FIELDS.includes(key)) return false;
    if (key.endsWith('_source')) return false; // internal citation fields
    if (value === null || value === undefined) return false;
    if (typeof value === 'string' && NA_VALUES.includes(value.toLowerCase().trim())) return false;
    return true;
  });
};
```

- Applies to ALL categories — every Specs tab renders only meaningful fields
- "other" category is backend-only fallback — NOT shown in CategorySelector UI (7 visible + fashion = 8 visible categories)

**Files:** `SmartCompareApp/src/screens/ResultsScreen.tsx`, `SmartCompareApp/src/components/CategorySelector.tsx`

## Implementation Plan — Agent Teams

### Context Management (Critical for Pro Subscription)

**Problem:** Each Opus agent inherits full conversation context. After usage limit pauses, context reload spikes to ~60% in 30 seconds.

**Mitigations:**
- Trim MEMORY.md to <150 lines before starting agents
- 2 agents per round maximum (not 4)
- Fresh team per round — no agent resumption
- Each agent gets ONLY the files they need (targeted prompt, not full project context)
- Commit + update context files between rounds

### Round 1: Backend Agent + Test Agent

**Agent 1 (Backend):**
- Add fashion category to PRODUCT_PARSER_PROMPT and CATEGORY_SPEC_SCHEMAS
- Add LUXURY_BRAND_KEYWORDS + _is_luxury_brand() detection
- Rewrite PRICE_EXTRACTION_PROMPT (source priority, DO/DON'T examples)
- Add review citation cleanup post-processing
- Fix spec prompt (remove "EVERY field MUST have a value")
- Fix "other" schema
- Update seller trust scoring in _extract_price_from_shopping()
- Increase organic context from 2000 to 3000 chars

**Agent 2 (Test):**
- Write tests for fashion category detection (parser picks "fashion" for hats, bags, shoes)
- Write tests for luxury brand detection (_is_luxury_brand)
- Write tests for price priority (official > reseller)
- Write tests for citation stripping (regex replacement)
- Write tests for N/A field filtering
- Target: 80%+ coverage on new code
- QA Agent 1's work when complete

**Cross-QA:** Each agent reviews the other's output before round ends.

### Round 2: Frontend Agent + Integration Agent

**Agent 3 (Frontend):**
- Add N/A filtering in ResultsScreen Specs tab
- Add "fashion" to CategorySelector
- Verify category switching banner works with new categories

**Agent 4 (Scoring + Integration):**
- Update scoring_service.py for spec score penalty and luxury price scoring
- Update verdict prompt with dynamic best_for categories
- Update review prompt with category-specific category_scores
- Run full test suite to verify no regressions
- QA Agent 3's work

**Cross-QA:** Same pattern — each agent reviews the other's work.

### Between Rounds
- Commit all Round 1 changes
- Update CONTEXT_SESSION_LOG.md with what changed
- Fresh team for Round 2

## Test Coverage Requirements

New tests needed (target 80%+):

**`test_fashion_category.py`** (~15 tests):
- Parser detects "LV hat" → category "fashion" (not "other")
- Parser detects "Hermes scarf" → "fashion", "Chanel perfume" → "fragrances" (not fashion)
- Fashion schema has correct fields (material, style, etc.)
- Category switching: selected=electronics + product=hat → switched=true, used=fashion
- Category switching: selected=fashion + product=hat → switched=false
- "other" schema no longer has power/compatibility fields

**`test_luxury_brands.py`** (~12 tests):
- `_is_luxury_brand("Louis Vuitton LV Vers Mesh Cap")` → True
- `_is_luxury_brand("Nike Air Max")` → False
- `_is_luxury_brand("Hermès Nevada cap")` → True (accent handling)
- Price guardrail: luxury brand + Shopping price < 40% of GPT estimate → reject Shopping price
- Price guardrail: non-luxury brand → normal behavior (no rejection)
- Official domain mapping: hermes.com → trust 1.0, ebay.com → trust 0.1

**`test_citation_cleanup.py`** (~10 tests):
- `"[snippet_1] Great quality"` → `"Per hermes.com: Great quality"` (when snippet 1 source is hermes.com)
- `"[snippet_3] Some text"` → `"Some text"` (when snippet 3 has no source URL)
- Multiple citations in one list handled correctly
- Spec `_source` fields NOT touched by cleanup
- Empty/null review fields handled gracefully

**`test_price_priority.py`** (~10 tests):
- Shopping results with hermes.com link prioritized over eBay link even if eBay is cheaper
- OFFICIAL_BRAND_DOMAINS returns correct trust scores
- Untrusted sellers (DHgate, AliExpress) effectively rejected (trust < 0.2)
- Non-luxury products still use normal price selection logic

Existing tests must continue passing (757 unit tests).

## Cost Impact

- **Zero extra API calls** — all changes are prompt improvements and post-processing
- **Same ~$0.010/comparison** target maintained
- Prompt token count increases slightly (~50-100 tokens) for better instructions — negligible cost

## Files Changed

| File | Changes |
|------|---------|
| `app/services/extraction_service.py` | PRODUCT_PARSER_PROMPT, CATEGORY_SPEC_SCHEMAS, _build_specs_prompt, PRICE_EXTRACTION_PROMPT, REVIEWS_EXTRACTION_PROMPT, COMPARISON_PROMPT |
| `app/services/structured_comparison_service.py` | LUXURY_BRAND_KEYWORDS, _is_luxury_brand(), _extract_price_from_shopping(), citation cleanup, context size increase |
| `app/services/scoring_service.py` | Spec score penalty for N/A, luxury price scoring |
| `SmartCompareApp/src/screens/ResultsScreen.tsx` | N/A spec filtering, citation display |
| `SmartCompareApp/src/components/CategorySelector.tsx` | Add "fashion" category |
| `tests/test_fashion_category.py` | NEW — fashion detection tests |
| `tests/test_luxury_brands.py` | NEW — luxury brand detection tests |
| `tests/test_citation_cleanup.py` | NEW — citation stripping tests |
| `tests/test_price_priority.py` | NEW — price source hierarchy tests |
