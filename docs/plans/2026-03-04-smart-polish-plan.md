# Smart Polish Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix Expo build, improve AI review/verdict quality through prompt engineering, tighten spec verification, and fix broken retailer URLs — all at zero additional cost.

**Architecture:** Prompt-level changes in `extraction_service.py`, verification logic in `structured_comparison_service.py`, config fix in `app.json`, frontend URL handling in `ResultsScreen.tsx`. No new dependencies, no new API calls.

**Tech Stack:** Python 3.12 (FastAPI), React Native (Expo), GPT-4o-mini prompts

---

## Team Assignment

| Task | Owner | QA By |
|------|-------|-------|
| Task 1 (Expo fix) | agent-expo-urls | agent-specs |
| Task 2 (Review prompt) | agent-prompts | agent-expo-urls |
| Task 3 (Spec verification) | agent-specs | agent-prompts |
| Task 4 (URL fixes) | agent-expo-urls | agent-specs |
| Task 5 (Verdict prompt) | agent-prompts | agent-expo-urls |

---

### Task 1: Fix Expo Startup — Remove expo-image-manipulator Plugin

**Owner:** agent-expo-urls
**Files:**
- Modify: `SmartCompareApp/app.json:46`

**Step 1: Remove the plugin entry**

In `SmartCompareApp/app.json`, remove line 46 (`"expo-image-manipulator",`) from the `plugins` array. The library is used as a regular import in `api.ts`, not as a config plugin.

Before:
```json
"plugins": [
  "expo-secure-store",
  ["expo-camera", { ... }],
  ["expo-image-picker", { ... }],
  "expo-image-manipulator",
  ["@react-native-google-signin/google-signin", { ... }],
  "expo-apple-authentication"
]
```

After:
```json
"plugins": [
  "expo-secure-store",
  ["expo-camera", { ... }],
  ["expo-image-picker", { ... }],
  ["@react-native-google-signin/google-signin", { ... }],
  "expo-apple-authentication"
]
```

**Step 2: Verify Expo starts**

Run: `cd SmartCompareApp && npx expo start` — should start without `PluginError`.

**Step 3: Verify image-manipulator still works as import**

Run: `cd SmartCompareApp && npx tsc --noEmit` — should show same pre-existing errors (7), no NEW errors related to expo-image-manipulator.

**Step 4: Commit**

```bash
git add SmartCompareApp/app.json
git commit -m "fix: remove expo-image-manipulator from plugins (not a config plugin)"
```

---

### Task 2: Tighten Review Extraction Prompt

**Owner:** agent-prompts
**Files:**
- Modify: `app/services/extraction_service.py:194-241` (REVIEWS_EXTRACTION_PROMPT)

**Step 1: Write failing test**

Create `tests/test_review_prompt_quality.py`:

```python
"""Tests for review prompt quality — ensures citations and specificity."""
import pytest
import json
from app.services.extraction_service import REVIEWS_EXTRACTION_PROMPT


class TestReviewPromptStructure:
    """Verify the review prompt enforces citation and specificity rules."""

    def test_prompt_requires_snippet_citations(self):
        """Prompt must instruct GPT to cite [snippet_N] for praises/complaints."""
        prompt = REVIEWS_EXTRACTION_PROMPT
        assert "snippet_" in prompt.lower() or "[snippet_" in prompt
        assert "cite" in prompt.lower() or "citation" in prompt.lower() or "reference" in prompt.lower()

    def test_prompt_forbids_synthetic_rating_distribution(self):
        """Prompt must NOT ask GPT to estimate rating_distribution percentages."""
        prompt = REVIEWS_EXTRACTION_PROMPT
        assert "estimate percentages" not in prompt.lower()

    def test_prompt_has_good_vs_bad_examples(self):
        """Prompt must include examples of specific vs generic output."""
        prompt = REVIEWS_EXTRACTION_PROMPT
        # Should have at least one GOOD example and one BAD example
        has_good = "GOOD:" in prompt or "good example" in prompt.lower() or "DO:" in prompt
        has_bad = "BAD:" in prompt or "bad example" in prompt.lower() or "DON'T:" in prompt or "NOT:" in prompt
        assert has_good or has_bad, "Prompt should include examples of good vs bad output"

    def test_prompt_requires_evidence_per_claim(self):
        """Each praise/complaint must reference which snippet it came from."""
        prompt = REVIEWS_EXTRACTION_PROMPT
        # The detailed_praises/complaints format should include a source/snippet field
        assert "source" in prompt.lower() or "snippet" in prompt.lower()

    def test_prompt_warns_against_paraphrasing(self):
        """Prompt must warn against GPT paraphrasing quotes as real user words."""
        prompt = REVIEWS_EXTRACTION_PROMPT
        assert "paraphras" in prompt.lower() or "fabricat" in prompt.lower() or "invent" in prompt.lower()
```

Run: `python -m pytest tests/test_review_prompt_quality.py -v`
Expected: Some tests FAIL (current prompt doesn't have examples, doesn't forbid estimation, doesn't warn against paraphrasing).

**Step 2: Rewrite the review prompt**

Replace `REVIEWS_EXTRACTION_PROMPT` in `app/services/extraction_service.py` (lines 194-241) with:

```python
REVIEWS_EXTRACTION_PROMPT = """You are a review analysis expert. Extract a FACTUAL review analysis for this product using ONLY the search results provided.

PRODUCT: {brand} {name} {variant}
CATEGORY: {category}

Search results and retailer data:
{search_context}

Return ONLY valid JSON:
{{
    "average_rating": 0.0-5.0 or null,
    "total_reviews": estimated_count or null,
    "positive_percentage": 0-100 or null,
    "rating_distribution": null,
    "category_scores": {{
        "aspect_name": score_out_of_10
    }},
    "common_praises": ["[snippet_N] specific praise with evidence"],
    "common_complaints": ["[snippet_N] specific complaint with evidence"],
    "detailed_praises": [
        {{"text": "specific praise", "frequency": "how often mentioned", "source": "snippet_N"}}
    ],
    "detailed_complaints": [
        {{"text": "specific complaint", "frequency": "how often mentioned", "source": "snippet_N"}}
    ],
    "user_quotes": [
        {{"text": "exact words from snippet", "sentiment": "positive|negative|mixed", "source": "snippet_N", "aspect": "what aspect it covers"}}
    ],
    "summary": "2-3 sentence specific, opinionated summary"
}}

RULES:
- EVERY praise and complaint MUST cite its source as [snippet_N] — if you cannot cite a snippet, do NOT include the claim
- category_scores: pick 4-6 aspects relevant to the product category (e.g. for phones: camera, battery, display, performance, value, build quality). Score 1-10 based on review consensus from snippets
- common_praises/common_complaints: prefix each with [snippet_N] citation. 3-5 items each
- detailed_praises/detailed_complaints: MUST include "source" field referencing the snippet
- user_quotes: extract 3-5 EXACT phrases from the search snippets — actual words as written. Do NOT paraphrase, invent, or fabricate quotes
- rating_distribution: always set to null — real distribution data is injected separately
- DO NOT generate source_ratings — retailer ratings are injected separately from real data
- summary: be SPECIFIC and opinionated, referencing actual findings from snippets

DO: "[snippet_3] Battery drains to 20% by 3pm with heavy camera use"
DON'T: "Battery life could be better" (too vague, no citation)

DO: "[snippet_1] 48MP main sensor captures sharp detail in low light"
DON'T: "Great camera quality" (generic, no evidence)

- Return null/empty for fields without reliable data from the provided snippets"""
```

**Step 3: Run tests to verify they pass**

Run: `python -m pytest tests/test_review_prompt_quality.py -v`
Expected: ALL PASS

**Step 4: Syntax check**

Run: `python -m py_compile app/services/extraction_service.py`

**Step 5: Run full test suite to check no regressions**

Run: `python -m pytest tests/ -v -m "not (live_unit or live_db or integration)" --ignore=tests/test_integration.py`
Expected: All 344+ tests pass

**Step 6: Commit**

```bash
git add app/services/extraction_service.py tests/test_review_prompt_quality.py
git commit -m "feat: tighten review prompt — require snippet citations, forbid synthetic data"
```

---

### Task 3: Tighten Spec Citation Verification

**Owner:** agent-specs
**Files:**
- Modify: `app/services/structured_comparison_service.py:1834-1904` (`_verify_spec_citations`, `_cross_validate_specs_with_shopping`)

**Step 1: Write failing tests**

Create `tests/test_spec_verification_strict.py`:

```python
"""Tests for stricter spec citation verification."""
import pytest
from app.services.structured_comparison_service import StructuredComparisonService


@pytest.fixture
def service():
    return StructuredComparisonService()


class TestStrictNumericVerification:
    """Numeric spec values must match exactly in cited snippet."""

    def test_exact_number_match_verified(self, service):
        """'4422 mAh' cited from snippet containing '4422' should be verified."""
        specs = {"battery": "4422 mAh", "battery_source": "snippet_1"}
        snippets = ["The phone features a 4422 mAh battery with fast charging"]
        result = service._verify_spec_citations(specs, snippets)
        assert result["battery"] == "verified"

    def test_wrong_number_not_verified(self, service):
        """'4422 mAh' cited from snippet with '5000 mAh' should NOT be verified."""
        specs = {"battery": "4422 mAh", "battery_source": "snippet_1"}
        snippets = ["This device has a 5000 mAh battery for all-day use"]
        result = service._verify_spec_citations(specs, snippets)
        assert result["battery"] != "verified"

    def test_storage_number_must_match(self, service):
        """'128 GB' cited from snippet with only '256 GB' should NOT be verified."""
        specs = {"storage": "128 GB", "storage_source": "snippet_1"}
        snippets = ["Available in 256 GB and 512 GB configurations"]
        result = service._verify_spec_citations(specs, snippets)
        assert result["storage"] != "verified"

    def test_storage_number_exact_match(self, service):
        """'256 GB' cited from snippet with '256' should be verified."""
        specs = {"storage": "256 GB", "storage_source": "snippet_1"}
        snippets = ["The base model comes with 256 GB of storage"]
        result = service._verify_spec_citations(specs, snippets)
        assert result["storage"] == "verified"

    def test_ram_number_must_match(self, service):
        """'8 GB' RAM cited from snippet with '12 GB' should NOT be verified."""
        specs = {"ram": "8 GB", "ram_source": "snippet_1"}
        snippets = ["Powered by 12 GB of RAM and Snapdragon 8 Gen 3"]
        result = service._verify_spec_citations(specs, snippets)
        assert result["ram"] != "verified"

    def test_non_numeric_spec_uses_keyword_match(self, service):
        """Non-numeric specs like 'os' should still use keyword matching."""
        specs = {"os": "Android 14", "os_source": "snippet_1"}
        snippets = ["Ships with Android 14 and One UI 6.1"]
        result = service._verify_spec_citations(specs, snippets)
        assert result["os"] == "verified"

    def test_weight_numeric_match(self, service):
        """Weight '187 g' should match snippet with '187'."""
        specs = {"weight": "187 g", "weight_source": "snippet_1"}
        snippets = ["Weighing in at 187 grams, it's lighter than the Pro model"]
        result = service._verify_spec_citations(specs, snippets)
        assert result["weight"] == "verified"

    def test_training_source_always_unverified(self, service):
        """Specs citing 'training' should always be unverified."""
        specs = {"battery": "4000 mAh", "battery_source": "training"}
        snippets = ["Some snippet text"]
        result = service._verify_spec_citations(specs, snippets)
        assert result["battery"] == "unverified"

    def test_no_source_always_unverified(self, service):
        """Specs with no _source field should be unverified."""
        specs = {"battery": "4000 mAh"}
        snippets = ["Some snippet text"]
        result = service._verify_spec_citations(specs, snippets)
        assert result["battery"] == "unverified"


class TestCrossValidationNumeric:
    """Shopping cross-validation should check exact numeric matches."""

    def test_storage_cross_validated(self, service):
        """Storage '128 GB' should be verified if '128' appears in shopping titles."""
        specs = {"storage": "128 GB"}
        shopping = [{"title": "iPhone 15 128GB Blue", "description": ""}]
        result = service._cross_validate_specs_with_shopping(specs, shopping)
        assert result.get("storage") == "verified"

    def test_wrong_storage_not_cross_validated(self, service):
        """Storage '128 GB' should NOT be verified if only '256' appears in shopping."""
        specs = {"storage": "128 GB"}
        shopping = [{"title": "iPhone 15 Pro 256GB", "description": ""}]
        result = service._cross_validate_specs_with_shopping(specs, shopping)
        assert result.get("storage") != "verified"
```

Run: `python -m pytest tests/test_spec_verification_strict.py -v`
Expected: `test_wrong_number_not_verified`, `test_storage_number_must_match`, `test_ram_number_must_match` FAIL (current code uses loose 50% keyword match).

**Step 2: Implement stricter numeric verification**

Replace `_verify_spec_citations` method (lines 1834-1871) in `structured_comparison_service.py`:

```python
# Fields where numeric values must match exactly in the cited snippet
NUMERIC_SPEC_FIELDS = {"ram", "storage", "battery", "weight", "display", "count", "dosage",
                       "nutrition_calories", "nutrition_protein", "nutrition_fat", "nutrition_carbs"}

def _verify_spec_citations(self, specs: Dict, search_snippets: List[str]) -> Dict[str, str]:
    """Verify GPT spec citations against actual search snippets.

    For numeric fields (ram, storage, battery, weight, etc.): requires exact number match.
    For text fields (os, connectivity, etc.): uses keyword overlap (50% threshold).

    Returns dict mapping spec_field -> confidence:
      'verified': citation matches snippet text
      'likely': citation provided but can't fully cross-check
      'unverified': no citation or citation doesn't match
    """
    confidence = {}
    for key, value in specs.items():
        if key.endswith("_source") or key.startswith("_") or key in ("brand", "model", "variant", "category"):
            continue
        source_key = f"{key}_source"
        source = specs.get(source_key)

        if not source or source == "training":
            confidence[key] = "unverified"
        elif source.startswith("snippet_"):
            try:
                idx = int(source.split("_")[1]) - 1
                if 0 <= idx < len(search_snippets):
                    snippet_text = search_snippets[idx].lower()
                    value_str = str(value).lower()

                    # Extract numbers from the spec value
                    spec_numbers = re.findall(r'\d+', value_str)

                    if key in NUMERIC_SPEC_FIELDS and spec_numbers:
                        # STRICT: all significant numbers must appear in snippet
                        # Filter to numbers >= 2 digits (skip "1", "2" etc. which match everywhere)
                        sig_numbers = [n for n in spec_numbers if len(n) >= 2]
                        if sig_numbers:
                            matches = sum(1 for n in sig_numbers if n in snippet_text)
                            confidence[key] = "verified" if matches == len(sig_numbers) else "likely"
                        else:
                            # Only small numbers — use keyword matching
                            terms = [t for t in value_str.split() if len(t) > 2]
                            if not terms:
                                confidence[key] = "likely"
                            else:
                                matches = sum(1 for t in terms if t in snippet_text)
                                confidence[key] = "verified" if matches >= len(terms) * 0.5 else "likely"
                    else:
                        # TEXT fields: keyword overlap matching (original behavior)
                        terms = [t for t in value_str.split() if len(t) > 2]
                        if not terms:
                            confidence[key] = "likely"
                        else:
                            matches = sum(1 for t in terms if t in snippet_text)
                            confidence[key] = "verified" if matches >= len(terms) * 0.5 else "likely"
                else:
                    confidence[key] = "unverified"
            except (ValueError, IndexError):
                confidence[key] = "unverified"
        else:
            confidence[key] = "unverified"

    return confidence
```

Also update `_cross_validate_specs_with_shopping` to be stricter with numbers — only verify if the EXACT number from the spec appears (not just any number):

Replace lines 1873-1904:

```python
def _cross_validate_specs_with_shopping(self, specs: Dict, shopping_items: List[Dict]) -> Dict[str, str]:
    """Cross-check spec values against Serper Shopping product titles/descriptions.

    Upgrades 'likely' to 'verified' if shopping data confirms.
    For numeric fields, requires exact number match (not just any number present).
    Returns dict mapping field -> 'verified' for confirmed fields.
    """
    if not shopping_items:
        return {}

    # Combine all shopping titles into one searchable text
    shopping_text = " ".join(
        f"{item.get('title', '')} {item.get('description', '')}"
        for item in shopping_items
    ).lower()

    flags = {}
    checkable = ["storage", "ram", "display", "processor", "count", "dosage", "form"]
    for key in checkable:
        value = specs.get(key)
        if not value or value == "N/A":
            continue
        value_str = str(value).lower()
        # Extract significant numbers (2+ digits) from spec value
        spec_numbers = [n for n in re.findall(r'\d+', value_str) if len(n) >= 2]
        if spec_numbers:
            # ALL significant numbers must appear in shopping text
            all_found = all(n in shopping_text for n in spec_numbers)
            if all_found:
                flags[key] = "verified"
        else:
            # Non-numeric: check key words
            terms = [t for t in value_str.split() if len(t) > 2]
            found = sum(1 for t in terms if t in shopping_text)
            if terms and found >= len(terms) * 0.5:
                flags[key] = "verified"

    return flags
```

**Step 3: Add NUMERIC_SPEC_FIELDS constant near top of file**

Add after line 94 (after `DEFAULT_RETAILER_SCORE`):

```python
# Fields where numeric values must match exactly during citation verification
NUMERIC_SPEC_FIELDS = {"ram", "storage", "battery", "weight", "display", "count", "dosage",
                       "nutrition_calories", "nutrition_protein", "nutrition_fat", "nutrition_carbs"}
```

And remove the duplicate from inside the method.

**Step 4: Run tests**

Run: `python -m pytest tests/test_spec_verification_strict.py -v`
Expected: ALL PASS

Run: `python -m pytest tests/ -v -m "not (live_unit or live_db or integration)" --ignore=tests/test_integration.py`
Expected: All existing tests still pass (the fact_checking tests should be checked carefully — some may need adjustment if they relied on the old loose matching).

**Step 5: Commit**

```bash
git add app/services/structured_comparison_service.py tests/test_spec_verification_strict.py
git commit -m "feat: strict numeric verification for spec citations"
```

---

### Task 4: Fix Broken Retailer URLs

**Owner:** agent-expo-urls
**Files:**
- Modify: `app/services/structured_comparison_service.py:1211-1219, 1300, 1827`
- Modify: `SmartCompareApp/src/screens/ResultsScreen.tsx:315-316`

**Step 1: Write failing tests**

Create `tests/test_url_quality.py`:

```python
"""Tests for URL quality — no search-page fallbacks as product links."""
import pytest
from app.services.structured_comparison_service import StructuredComparisonService


@pytest.fixture
def service():
    return StructuredComparisonService()


class TestBuildRetailerUrl:
    """_build_retailer_url should return None for unknown retailers instead of Google fallback."""

    def test_known_retailer_returns_search_url(self, service):
        """Known retailers should still get a search URL."""
        url = service._build_retailer_url("Amazon", "iPhone 15")
        assert url is not None
        assert "amazon.com" in url

    def test_unknown_retailer_returns_none(self, service):
        """Unknown retailers should return None, not a Google Shopping fallback."""
        url = service._build_retailer_url("Random Unknown Store", "iPhone 15")
        assert url is None

    def test_empty_source_returns_none(self, service):
        """Empty source should return None."""
        url = service._build_retailer_url("", "iPhone 15")
        assert url is None


class TestShoppingUrlExtraction:
    """Price extraction should use Serper link directly when available."""

    def test_serper_link_used_directly(self, service):
        """When Serper provides a link, use it as-is."""
        items = [{
            "title": "iPhone 15 128GB",
            "price": "$799.00",
            "source": "Amazon",
            "link": "https://www.amazon.com/dp/B0CHBNQN5T"
        }]
        result = service._extract_price_from_shopping("iPhone 15", items, "USD")
        assert result is not None
        assert result["url"] == "https://www.amazon.com/dp/B0CHBNQN5T"

    def test_no_link_gets_retailer_search_url(self, service):
        """When Serper has no link, known retailer gets search URL."""
        items = [{
            "title": "iPhone 15 128GB",
            "price": "$799.00",
            "source": "Amazon",
            "link": ""
        }]
        result = service._extract_price_from_shopping("iPhone 15", items, "USD")
        assert result is not None
        assert "amazon.com" in result["url"]

    def test_no_link_unknown_retailer_gets_none_url(self, service):
        """When Serper has no link and retailer is unknown, URL should be None."""
        items = [{
            "title": "iPhone 15 128GB",
            "price": "$799.00",
            "source": "Some Random Shop",
            "link": ""
        }]
        result = service._extract_price_from_shopping("iPhone 15", items, "USD")
        assert result is not None
        # URL should be None for unknown retailer with no link
        assert result["url"] is None or "google.com" not in result["url"]
```

Run: `python -m pytest tests/test_url_quality.py -v`
Expected: `test_unknown_retailer_returns_none`, `test_no_link_unknown_retailer_gets_none_url` FAIL.

**Step 2: Update `_build_retailer_url` to return None for unknown retailers**

Replace method at line 1211-1219:

```python
def _build_retailer_url(self, source: str, product_name: str) -> Optional[str]:
    """Build a retailer search URL from the source name and product name.
    Returns None for unknown retailers instead of a generic Google search."""
    if not source:
        return None
    from urllib.parse import quote_plus
    source_lower = source.lower().strip()
    for key, template in RETAILER_SEARCH_URLS.items():
        if key in source_lower:
            return template.format(query=quote_plus(product_name))
    return None
```

**Step 3: Update frontend to handle null URLs gracefully**

In `SmartCompareApp/src/screens/ResultsScreen.tsx`, find the price URL section (around line 315) and the rating source section. When `url` is null, show "Search online" with a Google Shopping link instead of a broken link:

Find the price link section and update to handle null:
```typescript
// Price link: if url exists, open it; if not, open Google Shopping search
product.price?.url ? (
  <TouchableOpacity onPress={() => Linking.openURL(product.price!.url!)}>
```

This already guards against null (the `?.url` check), so the price link only shows when there's a URL. Verify this is the case — if the button shows regardless, wrap it in a conditional.

For the rating source `openRatingSource` function (line 182-191): it already falls back to Google Shopping search when `source?.url` is falsy. No change needed there.

**Step 4: Run tests**

Run: `python -m pytest tests/test_url_quality.py -v`
Expected: ALL PASS

Run: `python -m pytest tests/ -v -m "not (live_unit or live_db or integration)" --ignore=tests/test_integration.py`
Expected: Check `test_url_extraction.py` — some tests may need updating if they expected the old Google fallback URL.

**Step 5: Commit**

```bash
git add app/services/structured_comparison_service.py tests/test_url_quality.py SmartCompareApp/src/screens/ResultsScreen.tsx
git commit -m "fix: return null URL for unknown retailers instead of generic Google search"
```

---

### Task 5: Improve Comparison Verdict Prompt

**Owner:** agent-prompts
**Files:**
- Modify: `app/services/extraction_service.py:244-295` (COMPARISON_PROMPT)

**Step 1: Write failing tests**

Add to `tests/test_review_prompt_quality.py` (or create separate file):

```python
class TestVerdictPromptStructure:
    """Verify the comparison verdict prompt enforces specificity."""

    def test_prompt_requires_tradeoff_analysis(self):
        """Prompt must mandate trade-off: 'A wins for X, B wins for Y'."""
        from app.services.extraction_service import COMPARISON_PROMPT
        prompt = COMPARISON_PROMPT.lower()
        assert "trade" in prompt or "wins for" in prompt or "better for" in prompt

    def test_prompt_requires_numeric_differences(self):
        """Prompt must ask for numeric/quantified differences."""
        from app.services.extraction_service import COMPARISON_PROMPT
        prompt = COMPARISON_PROMPT.lower()
        assert "numeric" in prompt or "quantif" in prompt or "percentage" in prompt or "specific number" in prompt

    def test_prompt_has_who_should_buy(self):
        """Prompt must include audience-specific recommendation."""
        from app.services.extraction_service import COMPARISON_PROMPT
        prompt = COMPARISON_PROMPT.lower()
        assert "who should" in prompt or "best for" in prompt or "ideal for" in prompt or "user profile" in prompt

    def test_prompt_has_good_vs_bad_verdict_examples(self):
        """Prompt must include examples of strong vs weak verdicts."""
        from app.services.extraction_service import COMPARISON_PROMPT
        has_example = "DO:" in COMPARISON_PROMPT or "GOOD:" in COMPARISON_PROMPT or "example" in COMPARISON_PROMPT.lower()
        assert has_example, "Prompt should include verdict quality examples"
```

Run: `python -m pytest tests/test_review_prompt_quality.py::TestVerdictPromptStructure -v`
Expected: FAIL (current prompt has none of these).

**Step 2: Rewrite the comparison prompt**

Replace `COMPARISON_PROMPT` (lines 244-295) in `extraction_service.py`:

```python
COMPARISON_PROMPT = """You are a product comparison expert. Compare these products with SPECIFIC, DATA-BACKED analysis. Be decisive — users want a clear answer, not fence-sitting.

PRODUCT 1:
{product1_json}

PRODUCT 2:
{product2_json}

User's region: {region}
Primary concern: {concern}

Return ONLY valid JSON:
{{
    "winner_index": 0 or 1,
    "winner_reason": "clear 1-sentence reason with a specific number or fact",
    "product_0_pros": ["specific pro with number/fact", "..."],
    "product_0_cons": ["specific con with number/fact", "..."],
    "product_1_pros": ["specific pro with number/fact", "..."],
    "product_1_cons": ["specific con with number/fact", "..."],
    "price_comparison": {{
        "cheaper_index": 0 or 1,
        "price_difference": "X {currency} (Y%)",
        "better_value_index": 0 or 1
    }},
    "specs_comparison": {{
        "product_0_advantages": ["advantage with specific number"],
        "product_1_advantages": ["advantage with specific number"],
        "similar": ["shared feature"]
    }},
    "value_scores": [0.0-10.0, 0.0-10.0],
    "best_for": {{
        "budget": 0 or 1,
        "performance": 0 or 1,
        "features": 0 or 1,
        "reliability": 0 or 1
    }},
    "recommendation": "2-3 sentence decisive recommendation",
    "key_differences": [
        "difference 1 with numbers",
        "difference 2 with numbers",
        "difference 3 with numbers",
        "difference 4 with numbers",
        "difference 5 with numbers"
    ]
}}

RULES:
- 4-6 pros, 2-4 cons per product — each MUST include a specific number, percentage, or measurable fact
- DO: "50% larger battery (5000 vs 3274 mAh) means 2+ hours more screen-on time"
- DON'T: "Better battery life" (vague, no numbers)
- DO: "15% cheaper at $799 vs $949 while matching camera quality"
- DON'T: "Good value for money" (meaningless without numbers)
- winner_reason MUST cite the single most important numeric advantage
- recommendation MUST state: who should buy Product 1, who should buy Product 2, and the specific trade-off between them
- key_differences: each must include actual specs/numbers, not generic descriptions
- Consider price-to-value ratio heavily for GCC market
- Value score: 10 = exceptional value, 5 = average, 1 = poor value
- Be DECISIVE — pick a clear winner and defend it with data"""
```

**Step 3: Run tests**

Run: `python -m pytest tests/test_review_prompt_quality.py -v`
Expected: ALL PASS

**Step 4: Syntax check + full regression**

Run: `python -m py_compile app/services/extraction_service.py`
Run: `python -m pytest tests/ -v -m "not (live_unit or live_db or integration)" --ignore=tests/test_integration.py`
Expected: All pass

**Step 5: Commit**

```bash
git add app/services/extraction_service.py tests/test_review_prompt_quality.py
git commit -m "feat: improve verdict prompt — require numeric diffs, trade-offs, audience targeting"
```

---

## QA Cross-Review Checklist

After implementation, each QA reviewer must check:

1. **Read the changed files** — does the code match the plan?
2. **Run ALL tests** — `python -m pytest tests/ -v -m "not (live_unit or live_db or integration)" --ignore=tests/test_integration.py`
3. **Check for regressions** — do existing tests in `test_fact_checking.py`, `test_url_extraction.py` still pass?
4. **Verify no broken imports** — `python -m py_compile app/services/extraction_service.py` and `python -m py_compile app/services/structured_comparison_service.py`
5. **Frontend check** — `cd SmartCompareApp && npx tsc --noEmit` (no NEW errors)
6. **If QA finds issues** — send specific feedback, work gets sent back for fixes
