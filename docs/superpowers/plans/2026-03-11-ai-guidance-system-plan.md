# AI Guidance System Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add personalized winner badges, GPT-generated insight cards, and improved fallbacks to the comparison results screen.

**Architecture:** Badges are deterministic (derived from existing scoring breakdown, $0). Insight cards ride on the existing GPT verdict call (~50 extra tokens). Price fallback adds 1 broader Serper search when Tier 1+2 fail. Frontend gets graceful empty states for all missing data.

**Tech Stack:** Python 3.12 (FastAPI), React Native (Expo), GPT-4o-mini, Serper API

**Spec:** `docs/superpowers/specs/2026-03-11-ai-guidance-system-design.md`

---

## Team Strategy (Pro Subscription Token Management)

### Phase Structure
- **Phase 1** (2 Opus agents): `backend-agent` + `frontend-agent` work in parallel
- **Phase 2** (2 Opus agents): Cross-QA + test gap coverage
- Each agent gets a **minimal, task-specific prompt** — NOT the full project context
- **Checkpoint file** written after each phase: `docs/superpowers/plans/session21-checkpoint.md`

### Context Management (Critical for Pro Limits)
- Agent prompts reference ONLY the files they need to touch (exact paths + line ranges)
- No agent reads CLAUDE.md or MEMORY.md — all needed context is in this plan
- After each phase: update `docs/CONTEXT_SESSION_LOG.md` with what changed
- If rate limits hit mid-phase: agents resume from checkpoint, not from scratch

### Cross-QA Protocol
1. After Phase 1, each agent QAs the other's work
2. QA checks: syntax (`py_compile` / `tsc --noEmit`), correctness (read + review), test pass
3. QA failures → specific feedback sent back → fix → re-QA
4. Idle agents write red-green tests targeting 80% coverage
5. No phase completes until BOTH agents sign off

### Agent Assignments
| Agent | Phase 1 Work | Phase 2 Work |
|---|---|---|
| `backend-agent` | Tasks 1-3 (prompt, validation, fallback) | QA frontend work + write backend tests |
| `frontend-agent` | Tasks 4-6 (types, badges, insights UI, fallbacks) | QA backend work + write frontend tests |

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `app/services/extraction_service.py` | Modify:307-364,637-681 | Add `personalized_insights` to COMPARISON_PROMPT schema + validation in `generate_comparison()` |
| `app/services/structured_comparison_service.py` | Modify:300-320,481-486,981-999 | Add `personalized_insights` to response + SSE verdict event; broader price fallback before Tier 3 |
| `SmartCompareApp/src/types/types.ts` | Modify:77-120 | Add `PersonalizedInsight` interface, update `Comparison` and `ComparisonResult` |
| `SmartCompareApp/src/screens/ResultsScreen.tsx` | Modify:257-301,411-470 | Add `AspectBadges`, `InsightCard`, `PreferencePromptBanner`, graceful empty states |
| `tests/test_guidance_insights.py` | Create | Backend tests for insights prompt, validation, truncation |
| `tests/test_fallback_improvements.py` | Create | Backend tests for broader search fallback |

---

## Chunk 1: Backend Changes

### Task 1: Add `personalized_insights` to COMPARISON_PROMPT

**Files:**
- Modify: `app/services/extraction_service.py:307-364` (COMPARISON_PROMPT)
- Modify: `app/services/extraction_service.py:637-681` (generate_comparison)
- Test: `tests/test_guidance_insights.py`

- [ ] **Step 1: Write failing test for insights in verdict response**

Create `tests/test_guidance_insights.py`:

```python
"""Tests for AI Guidance System — personalized insights in verdict."""
import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.fixture
def sample_product_1():
    return {
        "brand": "Apple",
        "name": "iPhone 15",
        "specs": {"battery": "3349 mAh", "ram": "6 GB", "storage": "128 GB"},
        "price": {"amount": 299, "currency": "BHD", "retailer": "Amazon"},
        "rating": 4.5,
        "review_count": 1200,
    }


@pytest.fixture
def sample_product_2():
    return {
        "brand": "Samsung",
        "name": "Galaxy S24",
        "specs": {"battery": "4000 mAh", "ram": "8 GB", "storage": "128 GB"},
        "price": {"amount": 259, "currency": "BHD", "retailer": "Jarir"},
        "rating": 4.3,
        "review_count": 800,
    }


@pytest.fixture
def sample_preferences():
    return {
        "priorities": ["price", "quality"],
        "budget": "budget",
        "lifestyle": ["fitness"],
        "brand_attitude": "function_first",
    }


class TestComparisonPromptHasInsightsSchema:
    """Verify COMPARISON_PROMPT includes personalized_insights schema."""

    def test_prompt_contains_personalized_insights_field(self):
        from app.services.extraction_service import COMPARISON_PROMPT
        assert "personalized_insights" in COMPARISON_PROMPT

    def test_prompt_contains_focus_area_field(self):
        from app.services.extraction_service import COMPARISON_PROMPT
        assert "focus_area" in COMPARISON_PROMPT

    def test_prompt_contains_product_index_field(self):
        from app.services.extraction_service import COMPARISON_PROMPT
        assert "product_index" in COMPARISON_PROMPT

    def test_prompt_contains_insight_field(self):
        from app.services.extraction_service import COMPARISON_PROMPT
        assert '"insight"' in COMPARISON_PROMPT


class TestGenerateComparisonInsightsValidation:
    """Verify generate_comparison validates personalized_insights."""

    @pytest.mark.asyncio
    async def test_insights_stripped_when_no_preferences(self, sample_product_1, sample_product_2):
        """When user_preferences is None, personalized_insights should be removed from response."""
        mock_response = {
            "winner_index": 0,
            "winner_reason": "Better camera",
            "product_0_pros": ["pro1"],
            "product_0_cons": ["con1"],
            "product_1_pros": ["pro1"],
            "product_1_cons": ["con1"],
            "price_comparison": {"cheaper_index": 1, "price_difference": "40 BHD", "better_value_index": 1},
            "specs_comparison": {"product_0_advantages": [], "product_1_advantages": [], "similar": []},
            "value_scores": [7.0, 8.0],
            "best_for": {"budget": 1, "performance": 0, "features": 0, "reliability": 0},
            "recommendation": "Get Galaxy S24 for value.",
            "key_differences": ["diff1"],
            "personalized_insights": [
                {"focus_area": "price", "product_index": 1, "insight": "S24 is cheaper"}
            ],
        }
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(
            return_value=MagicMock(
                choices=[MagicMock(message=MagicMock(content=json.dumps(mock_response)))]
            )
        )
        with patch("app.services.extraction_service.get_client", return_value=mock_client):
            from app.services.extraction_service import generate_comparison
            result = await generate_comparison(
                sample_product_1, sample_product_2, "bahrain",
                user_preferences=None,
            )
            assert "personalized_insights" not in result

    @pytest.mark.asyncio
    async def test_insights_truncated_to_3(self, sample_product_1, sample_product_2, sample_preferences):
        """When GPT returns >3 insights, truncate to first 3."""
        mock_response = {
            "winner_index": 0,
            "winner_reason": "Better camera",
            "product_0_pros": ["pro1"], "product_0_cons": ["con1"],
            "product_1_pros": ["pro1"], "product_1_cons": ["con1"],
            "price_comparison": {"cheaper_index": 1, "price_difference": "40 BHD", "better_value_index": 1},
            "specs_comparison": {"product_0_advantages": [], "product_1_advantages": [], "similar": []},
            "value_scores": [7.0, 8.0],
            "best_for": {"budget": 1, "performance": 0, "features": 0, "reliability": 0},
            "recommendation": "Get Galaxy S24.",
            "key_differences": ["diff1"],
            "personalized_insights": [
                {"focus_area": "price", "product_index": 1, "insight": "Cheaper"},
                {"focus_area": "battery", "product_index": 1, "insight": "Longer"},
                {"focus_area": "camera", "product_index": 0, "insight": "Better"},
                {"focus_area": "display", "product_index": 0, "insight": "Brighter"},
                {"focus_area": "storage", "product_index": 0, "insight": "More"},
            ],
        }
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(
            return_value=MagicMock(
                choices=[MagicMock(message=MagicMock(content=json.dumps(mock_response)))]
            )
        )
        with patch("app.services.extraction_service.get_client", return_value=mock_client):
            from app.services.extraction_service import generate_comparison
            result = await generate_comparison(
                sample_product_1, sample_product_2, "bahrain",
                user_preferences=sample_preferences,
            )
            assert len(result.get("personalized_insights", [])) <= 3

    @pytest.mark.asyncio
    async def test_insights_kept_when_preferences_present(self, sample_product_1, sample_product_2, sample_preferences):
        """When user_preferences present and GPT returns 2-3 insights, keep them."""
        mock_response = {
            "winner_index": 1,
            "winner_reason": "Better value",
            "product_0_pros": ["pro1"], "product_0_cons": ["con1"],
            "product_1_pros": ["pro1"], "product_1_cons": ["con1"],
            "price_comparison": {"cheaper_index": 1, "price_difference": "40 BHD", "better_value_index": 1},
            "specs_comparison": {"product_0_advantages": [], "product_1_advantages": [], "similar": []},
            "value_scores": [7.0, 8.5],
            "best_for": {"budget": 1, "performance": 0, "features": 0, "reliability": 0},
            "recommendation": "S24 wins on value.",
            "key_differences": ["diff1"],
            "personalized_insights": [
                {"focus_area": "price", "product_index": 1, "insight": "15% cheaper at 259 vs 299 BHD"},
                {"focus_area": "battery", "product_index": 1, "insight": "4000 vs 3349 mAh — ~2h more"},
            ],
        }
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(
            return_value=MagicMock(
                choices=[MagicMock(message=MagicMock(content=json.dumps(mock_response)))]
            )
        )
        with patch("app.services.extraction_service.get_client", return_value=mock_client):
            from app.services.extraction_service import generate_comparison
            result = await generate_comparison(
                sample_product_1, sample_product_2, "bahrain",
                user_preferences=sample_preferences,
            )
            assert "personalized_insights" in result
            assert len(result["personalized_insights"]) == 2
            assert result["personalized_insights"][0]["focus_area"] == "price"

    @pytest.mark.asyncio
    async def test_insights_empty_array_when_gpt_returns_none(self, sample_product_1, sample_product_2, sample_preferences):
        """When GPT returns no insights despite preferences, set empty array."""
        mock_response = {
            "winner_index": 0,
            "winner_reason": "Better camera",
            "product_0_pros": ["pro1"], "product_0_cons": ["con1"],
            "product_1_pros": ["pro1"], "product_1_cons": ["con1"],
            "price_comparison": {"cheaper_index": 1, "price_difference": "40 BHD", "better_value_index": 1},
            "specs_comparison": {"product_0_advantages": [], "product_1_advantages": [], "similar": []},
            "value_scores": [7.0, 8.0],
            "best_for": {"budget": 1, "performance": 0, "features": 0, "reliability": 0},
            "recommendation": "iPhone 15 wins.",
            "key_differences": ["diff1"],
        }
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(
            return_value=MagicMock(
                choices=[MagicMock(message=MagicMock(content=json.dumps(mock_response)))]
            )
        )
        with patch("app.services.extraction_service.get_client", return_value=mock_client):
            from app.services.extraction_service import generate_comparison
            result = await generate_comparison(
                sample_product_1, sample_product_2, "bahrain",
                user_preferences=sample_preferences,
            )
            assert result.get("personalized_insights") == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_guidance_insights.py -v`
Expected: FAIL — `personalized_insights` not in COMPARISON_PROMPT, no validation logic yet

- [ ] **Step 3: Add `personalized_insights` to COMPARISON_PROMPT**

In `app/services/extraction_service.py`, modify COMPARISON_PROMPT (line ~318-351). **NOTE**: COMPARISON_PROMPT is a regular string (NOT an f-string), so use SINGLE braces for JSON. The only double-brace sections are `{{` and `}}` used by `.format()` — the existing prompt already uses `{{` for JSON braces because `.format()` is called on it. Match that pattern.

Add the `personalized_insights` field to the JSON schema (after `"key_differences"` array, before the closing `}}`):

```python
# After the existing "key_differences" array (line ~350), add a comma and:
    "personalized_insights": [
        {{{{
            "focus_area": "user priority area (e.g., battery_life, price, camera)",
            "product_index": 0 or 1,
            "insight": "1-2 sentence insight with specific number (max 200 chars)"
        }}}}
    ]
```

**IMPORTANT**: The COMPARISON_PROMPT uses `.format()` so literal JSON braces must be doubled: `{{` for `{` and `}}` for `}`. The existing prompt already does this (see lines 319-351). Match that exact pattern.

And add these rules to the RULES section (after the existing rules, before the closing `"""`):

```
- personalized_insights: Generate ONLY if "User Preferences" section is present below. 2-3 insights, each tied to a different user priority. Each must cite a specific number. If no preferences section, omit this field entirely.
```

- [ ] **Step 4: Add validation in `generate_comparison()`**

In `app/services/extraction_service.py`, after `return json.loads(result)` (line ~677), add validation before the return:

```python
        parsed = json.loads(result)

        # Validate personalized_insights
        # Empty dict {} is falsy but also means "no real preferences"
        has_preferences = user_preferences and any(user_preferences.values())
        if not has_preferences:
            # Strip insights when no preferences (GPT may hallucinate them)
            parsed.pop("personalized_insights", None)
        else:
            insights = parsed.get("personalized_insights")
            if insights is None or not isinstance(insights, list):
                parsed["personalized_insights"] = []
            elif len(insights) > 3:
                parsed["personalized_insights"] = insights[:3]

        return parsed
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_guidance_insights.py -v`
Expected: All 7 tests PASS

- [ ] **Step 6: Syntax check**

Run: `python -m py_compile app/services/extraction_service.py`
Expected: No output (success)

- [ ] **Step 7: Commit**

```bash
git add tests/test_guidance_insights.py app/services/extraction_service.py
git commit -m "feat: add personalized_insights to verdict prompt + validation"
```

---

### Task 2: Wire insights through response and SSE stream

**Files:**
- Modify: `app/services/structured_comparison_service.py:300-320` (non-streaming response)
- Modify: `app/services/structured_comparison_service.py:481-486` (SSE verdict event)
- Test: `tests/test_guidance_insights.py` (extend)

- [ ] **Step 1: Write failing test for insights in response**

Append to `tests/test_guidance_insights.py`:

```python
class TestInsightsInResponse:
    """Verify personalized_insights flows through to final response."""

    def test_insights_in_comparison_field(self):
        """comparison dict should preserve personalized_insights from GPT."""
        comparison = {
            "winner_index": 0,
            "recommendation": "Buy A",
            "key_differences": [],
            "personalized_insights": [
                {"focus_area": "price", "product_index": 1, "insight": "15% cheaper"}
            ],
        }
        # The service copies comparison into response — insights should survive
        assert "personalized_insights" in comparison
        assert comparison["personalized_insights"][0]["focus_area"] == "price"

    def test_insights_in_sse_verdict_event(self):
        """SSE verdict event should include personalized_insights."""
        verdict_event = {
            "comparison": {
                "winner_index": 0,
                "personalized_insights": [
                    {"focus_area": "battery", "product_index": 1, "insight": "Lasts 2h longer"}
                ],
            },
            "winner_index": 0,
            "recommendation": "Buy A",
            "key_differences": [],
            "personalized_insights": [
                {"focus_area": "battery", "product_index": 1, "insight": "Lasts 2h longer"}
            ],
        }
        assert "personalized_insights" in verdict_event
        assert verdict_event["personalized_insights"][0]["focus_area"] == "battery"
```

- [ ] **Step 2: Add `personalized_insights` to SSE verdict event**

In `app/services/structured_comparison_service.py`, modify the SSE verdict yield (~line 481):

```python
            yield ("verdict", {
                "comparison": comparison,
                "winner_index": comparison.get("winner_index", 0),
                "recommendation": comparison.get("recommendation", ""),
                "key_differences": comparison.get("key_differences", []),
                "personalized_insights": comparison.get("personalized_insights", []),
            })
```

- [ ] **Step 3: Add `personalized_insights` to non-streaming response**

In `app/services/structured_comparison_service.py`, in the response dict (~line 300), the `comparison` dict already contains `personalized_insights` from `generate_comparison()`. It's passed as `"comparison": comparison` which preserves all fields. Also add it as a top-level field for easy frontend access:

After line ~312 (`"personalization_factors": personalization_factors,`), add:

```python
                "personalized_insights": comparison.get("personalized_insights", []),
```

Do the same in the streaming complete_response (~line 512).

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_guidance_insights.py -v`
Expected: All PASS

- [ ] **Step 5: Syntax check**

Run: `python -m py_compile app/services/structured_comparison_service.py`
Expected: No output (success)

- [ ] **Step 6: Run existing test suite to check for regressions**

Run: `python -m pytest tests/ -v -m "not (live_unit or live_db or integration)" --ignore=tests/test_integration.py -x`
Expected: All 579+ tests PASS

- [ ] **Step 7: Commit**

```bash
git add app/services/structured_comparison_service.py tests/test_guidance_insights.py
git commit -m "feat: wire personalized_insights through response and SSE stream"
```

---

### Task 3: Broader price fallback search

**Files:**
- Modify: `app/services/structured_comparison_service.py:981-999` (Tier 3 fallback area)
- Test: `tests/test_fallback_improvements.py`

- [ ] **Step 1: Write failing tests for broader fallback**

Create `tests/test_fallback_improvements.py`:

```python
"""Tests for improved price fallback — broader search before Tier 3."""
import pytest
import re


# The regex that strips model variants for broader search
MODEL_VARIANT_PATTERN = re.compile(r'\s+(pro|plus|max|ultra|\d{2,}gb|\d+tb)$', re.IGNORECASE)


class TestModelVariantStripping:
    """Test regex for stripping model variants from product names."""

    def test_strips_pro(self):
        result = MODEL_VARIANT_PATTERN.sub('', "iPhone 15 Pro")
        assert result == "iPhone 15"

    def test_strips_plus(self):
        result = MODEL_VARIANT_PATTERN.sub('', "Galaxy S24 Plus")
        assert result == "Galaxy S24"

    def test_strips_max(self):
        result = MODEL_VARIANT_PATTERN.sub('', "iPhone 15 Pro Max")
        # Only strips trailing "Max", leaves "Pro" in middle
        result2 = MODEL_VARIANT_PATTERN.sub('', result)
        assert "iPhone 15" in result2

    def test_strips_storage_variant(self):
        result = MODEL_VARIANT_PATTERN.sub('', "Galaxy S24 256GB")
        assert result == "Galaxy S24"

    def test_strips_ultra(self):
        result = MODEL_VARIANT_PATTERN.sub('', "Galaxy S24 Ultra")
        assert result == "Galaxy S24"

    def test_preserves_base_name(self):
        result = MODEL_VARIANT_PATTERN.sub('', "iPhone 15")
        assert result == "iPhone 15"

    def test_preserves_short_numbers(self):
        """Single digit numbers (like '15') should NOT be stripped."""
        result = MODEL_VARIANT_PATTERN.sub('', "iPhone 15")
        assert result == "iPhone 15"

    def test_case_insensitive(self):
        result = MODEL_VARIANT_PATTERN.sub('', "Pixel 8 PRO")
        assert result == "Pixel 8"


class TestBroaderFallbackTrigger:
    """Test that broader search only triggers when Tier 1+2 both fail."""

    def test_broader_query_differs_from_original(self):
        """Broader query should be different (shorter) than original."""
        original = "Apple iPhone 15 Pro 256GB"
        broader = MODEL_VARIANT_PATTERN.sub('', original).strip()
        # May need multiple passes for chained variants
        broader = MODEL_VARIANT_PATTERN.sub('', broader).strip()
        assert len(broader) < len(original)
        assert "Apple iPhone 15" in broader

    def test_no_broader_search_when_name_unchanged(self):
        """If stripping produces the same name, skip broader search."""
        original = "Sony WH-1000XM5"
        broader = MODEL_VARIANT_PATTERN.sub('', original).strip()
        assert broader == original  # No variant to strip, so skip broader search
```

- [ ] **Step 2: Run tests to verify they fail/pass as expected**

Run: `python -m pytest tests/test_fallback_improvements.py -v`
Expected: All PASS (these test the regex directly, not the integration yet)

- [ ] **Step 3: Add broader search fallback to `_get_product_price()`**

In `app/services/structured_comparison_service.py`, first check if `re` is already imported (`grep for 'import re'`). If not, add it. Then add the constant near the top (after existing imports):

```python
# Add if not already imported:
import re

MODEL_VARIANT_PATTERN = re.compile(r'\s+(pro|plus|max|ultra|\d{2,}gb|\d+tb)$', re.IGNORECASE)
```

Then insert the broader search code **BEFORE** the Tier 3 block (line ~981). The insertion point is between where Tier 2 extraction returns `None` (organic search failed, ~line 979) and the `# --- Tier 3: GPT training data fallback ---` comment at line 981:

```python
        # --- Broader search fallback (max 1 extra Serper call) ---
        broader_name = full_name
        for _ in range(3):  # Strip up to 3 trailing variants
            stripped = MODEL_VARIANT_PATTERN.sub('', broader_name).strip()
            if stripped == broader_name:
                break
            broader_name = stripped

        if broader_name != full_name and not is_supplement:
            logger.info(f"[PRICE] Trying broader search: '{broader_name}' (was '{full_name}')")
            broader_results = await search_product_prices(broader_name, region_info["code"])
            self._track_cost(0.001)
            broader_shopping = broader_results.get("shopping", [])
            if broader_shopping:
                # Try direct extraction from broader shopping results
                for item in broader_shopping:
                    extracted = item.get("price")
                    if extracted:
                        price = self._extract_shopping_price(item, currency)
                        if price and price.get("amount"):
                            logger.info(f"[PRICE] Broader search hit: {currency} {price['amount']}")
                            set_cached(cache_key, price, PRICE_CACHE_TTL)
                            price["_cached"] = False
                            return price

        # --- Tier 3: GPT training data fallback ---
        logger.info(f"[PRICE] Tiers 1-2 + broader failed, falling back to GPT estimate for {full_name}")
```

- [ ] **Step 4: Run all tests**

Run: `python -m pytest tests/ -v -m "not (live_unit or live_db or integration)" --ignore=tests/test_integration.py -x`
Expected: All PASS (no regressions)

- [ ] **Step 5: Syntax check**

Run: `python -m py_compile app/services/structured_comparison_service.py`

- [ ] **Step 6: Commit**

```bash
git add tests/test_fallback_improvements.py app/services/structured_comparison_service.py
git commit -m "feat: add broader search fallback before Tier 3 GPT estimate"
```

---

## Chunk 2: Frontend Changes

### Task 4: Add TypeScript types for insights

**Files:**
- Modify: `SmartCompareApp/src/types/types.ts:77-120`

- [ ] **Step 1: Add `PersonalizedInsight` interface**

In `SmartCompareApp/src/types/types.ts`, after the `Comparison` interface (~line 95), add:

```typescript
export interface PersonalizedInsight {
  focus_area: string;
  product_index: number;
  insight: string;
}
```

- [ ] **Step 2: Add `personalized_insights` to `ComparisonResult`**

In the `ComparisonResult` interface (~line 108), after `personalization_factors?: string[];`, add:

```typescript
  personalized_insights?: PersonalizedInsight[];
```

- [ ] **Step 3: Update imports in ResultsScreen.tsx**

In `SmartCompareApp/src/screens/ResultsScreen.tsx` line 18, add `PersonalizedInsight` to the import:

```typescript
import { RootStackParamList, Product, Comparison, RatingSource, ComparisonResult, ScoringResult, ProductScores, ScoreBreakdown, PersonalizedInsight } from '../types';
```

- [ ] **Step 4: TypeScript check**

Run: `cd SmartCompareApp && npx tsc --noEmit`
Expected: 0 errors

- [ ] **Step 5: Commit**

```bash
git add SmartCompareApp/src/types/types.ts SmartCompareApp/src/screens/ResultsScreen.tsx
git commit -m "feat: add PersonalizedInsight type + update ComparisonResult"
```

---

### Task 5: AspectBadges component + InsightCard + PreferencePromptBanner

**Files:**
- Modify: `SmartCompareApp/src/screens/ResultsScreen.tsx:257-301,411-470`

- [ ] **Step 1: Add badge mapping constant and `AspectBadges` component**

In `ResultsScreen.tsx`, after the `SCORE_LABELS` constant (~line 106), add:

```typescript
  // Badge mapping: scoring dimension → label + icon
  const BADGE_MAP: Record<keyof ScoreBreakdown, { label: string; icon: string }> = {
    price_score: { label: 'Best Price', icon: 'pricetag-outline' },
    spec_score: { label: 'Best Specs', icon: 'hardware-chip-outline' },
    review_score: { label: 'Top Rated', icon: 'star-outline' },
    value_score: { label: 'Best Value', icon: 'trophy-outline' },
    reliability_score: { label: 'Most Reliable', icon: 'shield-checkmark-outline' },
    popularity_score: { label: 'Most Popular', icon: 'trending-up-outline' },
  };

  const BADGE_THRESHOLD = 3; // Minimum point difference to award badge

  // Compute which badges each product wins
  const getProductBadges = (index: number): Array<{ label: string; icon: string }> => {
    if (!scoring) return [];
    const myScores = getProductScores(index);
    const otherScores = getProductScores(index === 0 ? 1 : 0);
    if (!myScores || !otherScores) return [];

    const badges: Array<{ label: string; icon: string }> = [];
    for (const [dim, meta] of Object.entries(BADGE_MAP)) {
      const key = dim as keyof ScoreBreakdown;
      if (myScores.breakdown[key] - otherScores.breakdown[key] >= BADGE_THRESHOLD) {
        badges.push(meta);
      }
    }
    return badges;
  };

  // AspectBadges component
  const AspectBadges = ({ index }: { index: number }) => {
    const badges = getProductBadges(index);
    const isOverallWinner = scoring && scoring.winner_index === index;
    if (badges.length === 0 && !isOverallWinner) return null;

    return (
      <View style={styles.aspectBadgesRow}>
        {isOverallWinner && (
          <View style={[styles.aspectBadge, styles.overallBadge]}>
            <Ionicons name="ribbon-outline" size={10} color="#FFF" />
            <Text style={styles.overallBadgeText}>
              {result.personalized ? 'Best for You' : 'Best Overall'}
            </Text>
          </View>
        )}
        {badges.map((badge, i) => (
          <View key={i} style={[styles.aspectBadge, isOverallWinner ? styles.winnerAspectBadge : styles.otherAspectBadge]}>
            <Ionicons name={badge.icon as any} size={10} color={isOverallWinner ? '#2E7D32' : '#1565C0'} />
            <Text style={[styles.aspectBadgeText, { color: isOverallWinner ? '#2E7D32' : '#1565C0' }]}>
              {badge.label}
            </Text>
          </View>
        ))}
      </View>
    );
  };
```

- [ ] **Step 2: Add `InsightCard` component**

After `AspectBadges`, add:

```typescript
  // Icon mapping for insight focus areas
  const getInsightIcon = (focusArea: string): string => {
    const lower = focusArea.toLowerCase();
    if (lower.includes('battery')) return 'battery-charging-outline';
    if (lower.includes('price') || lower.includes('budget') || lower.includes('value')) return 'cash-outline';
    if (lower.includes('camera') || lower.includes('photo')) return 'camera-outline';
    if (lower.includes('durability') || lower.includes('build')) return 'shield-checkmark-outline';
    if (lower.includes('display') || lower.includes('screen')) return 'phone-portrait-outline';
    if (lower.includes('performance') || lower.includes('speed')) return 'speedometer-outline';
    if (lower.includes('storage') || lower.includes('memory')) return 'server-outline';
    return 'information-circle-outline';
  };

  // InsightCard component
  const InsightCard = ({ insight }: { insight: PersonalizedInsight }) => {
    const productName = products[insight.product_index]?.name || 'Product';
    return (
      <View style={styles.insightCard}>
        <View style={styles.insightIconRow}>
          <Ionicons name={getInsightIcon(insight.focus_area) as any} size={20} color="#2196F3" />
          <Text style={styles.insightFocusArea}>
            {insight.focus_area.replace(/_/g, ' ')}
          </Text>
        </View>
        <Text style={styles.insightText}>{insight.insight}</Text>
      </View>
    );
  };

  // PreferencePromptBanner for anonymous / non-personalized users
  const PreferencePromptBanner = () => {
    if (result.personalized && result.personalized_insights && result.personalized_insights.length > 0) {
      return null; // Don't show banner when we have personalized insights
    }
    return (
      <TouchableOpacity
        style={styles.preferencePromptBanner}
        onPress={() => navigation.navigate('Preferences', { mode: 'onboarding' })}
      >
        <Ionicons name="person-circle-outline" size={24} color="#2196F3" />
        <View style={styles.preferencePromptTextContainer}>
          <Text style={styles.preferencePromptTitle}>Get personalized guidance</Text>
          <Text style={styles.preferencePromptSubtext}>Set your preferences to see insights tailored to you</Text>
        </View>
        <Ionicons name="chevron-forward" size={20} color="#999" />
      </TouchableOpacity>
    );
  };
```

- [ ] **Step 3: Update ProductCard to use AspectBadges**

In the `ProductCard` component (~line 257-301), replace the existing winner badge (lines 263-267) with `AspectBadges`. The `AspectBadges` goes at the TOP of the card (same position as the old winner badge), followed by the existing `ScoreBadge` at line 270:

Replace:
```typescript
        {isWinner && (
          <View style={styles.winnerBadge}>
            <Text style={styles.winnerBadgeText}>🏆 WINNER</Text>
          </View>
        )}
```

With:
```typescript
        <AspectBadges index={index} />
```

Keep `<ScoreBadge index={index} />` on the line below (line 270) — do NOT remove it.

- [ ] **Step 4: Add InsightCards and PreferencePromptBanner to Overview tab**

In the Overview tab section (~line 411-470), after the ProductCards `</View>` and before `<ScoringSection />`, add:

```typescript
            {/* Personalized Insight Cards (or preference prompt) */}
            {result.personalized_insights && result.personalized_insights.length > 0 ? (
              <View style={styles.insightsSection}>
                {result.personalized_insights.map((insight, index) => (
                  <InsightCard key={index} insight={insight} />
                ))}
              </View>
            ) : (
              <PreferencePromptBanner />
            )}
```

- [ ] **Step 5: Add styles for new components**

Append to the `StyleSheet.create({...})`:

```typescript
  // Aspect badges
  aspectBadgesRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 4,
    marginBottom: 8,
  },
  aspectBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 10,
    gap: 3,
  },
  overallBadge: {
    backgroundColor: '#4CAF50',
  },
  overallBadgeText: {
    fontSize: 9,
    fontWeight: 'bold',
    color: '#FFF',
  },
  winnerAspectBadge: {
    backgroundColor: '#E8F5E9',
  },
  otherAspectBadge: {
    backgroundColor: '#E3F2FD',
  },
  aspectBadgeText: {
    fontSize: 9,
    fontWeight: '600',
  },

  // Insight cards
  insightsSection: {
    paddingHorizontal: 10,
    marginBottom: 5,
  },
  insightCard: {
    backgroundColor: '#FFF',
    borderRadius: 12,
    padding: 15,
    marginBottom: 8,
    borderLeftWidth: 3,
    borderLeftColor: '#2196F3',
  },
  insightIconRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 6,
  },
  insightFocusArea: {
    fontSize: 12,
    fontWeight: '600',
    color: '#2196F3',
    textTransform: 'capitalize',
  },
  insightText: {
    fontSize: 13,
    color: '#555',
    lineHeight: 20,
  },

  // Preference prompt banner
  preferencePromptBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#FFF',
    marginHorizontal: 10,
    marginBottom: 5,
    padding: 12,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#E3F2FD',
    gap: 10,
  },
  preferencePromptTextContainer: {
    flex: 1,
  },
  preferencePromptTitle: {
    fontSize: 13,
    fontWeight: '600',
    color: '#333',
  },
  preferencePromptSubtext: {
    fontSize: 11,
    color: '#999',
    marginTop: 2,
  },
```

- [ ] **Step 6: TypeScript check**

Run: `cd SmartCompareApp && npx tsc --noEmit`
Expected: 0 errors

- [ ] **Step 7: Commit**

```bash
git add SmartCompareApp/src/screens/ResultsScreen.tsx
git commit -m "feat: add AspectBadges, InsightCard, PreferencePromptBanner"
```

---

### Task 6: Graceful empty states

**Files:**
- Modify: `SmartCompareApp/src/screens/ResultsScreen.tsx`

- [ ] **Step 1: Fix SpecsTab empty rows**

In the `SpecsTab` component (~line 304-345), the existing code already filters null values with `value && (`. This is correct — no change needed. Verify by reading.

- [ ] **Step 2: Add empty state to ReviewsTab**

In the `ReviewsTab` component (~line 348-381), wrap the content in a check:

```typescript
  const ReviewsTab = () => {
    const hasAnyReviews = products.some(p =>
      (p.pros && p.pros.length > 0) || (p.cons && p.cons.length > 0) || p.rating
    );

    if (!hasAnyReviews) {
      return (
        <View style={styles.tabContent}>
          <View style={styles.emptyStateCard}>
            <Ionicons name="chatbubble-ellipses-outline" size={40} color="#CCC" />
            <Text style={styles.emptyStateText}>Reviews not available for these products</Text>
          </View>
        </View>
      );
    }

    return (
      <View style={styles.tabContent}>
        {/* existing content */}
      </View>
    );
  };
```

- [ ] **Step 3: Add empty state styles**

```typescript
  emptyStateCard: {
    backgroundColor: '#FFF',
    borderRadius: 12,
    padding: 30,
    alignItems: 'center',
    justifyContent: 'center',
    margin: 10,
  },
  emptyStateText: {
    fontSize: 14,
    color: '#999',
    marginTop: 10,
    textAlign: 'center',
  },
```

- [ ] **Step 4: TypeScript check**

Run: `cd SmartCompareApp && npx tsc --noEmit`
Expected: 0 errors

- [ ] **Step 5: Commit**

```bash
git add SmartCompareApp/src/screens/ResultsScreen.tsx
git commit -m "feat: add graceful empty states for missing data"
```

---

## Chunk 3: Phase 2 — Cross-QA + Test Coverage

### Task 7: Backend agent QAs frontend work

- [ ] **Step 1: Read all frontend changes and verify correctness**

Read `SmartCompareApp/src/screens/ResultsScreen.tsx` and `SmartCompareApp/src/types/types.ts`. Check:
- `PersonalizedInsight` interface matches backend output schema
- `AspectBadges` threshold logic is correct (>= 3 points)
- `InsightCard` handles missing product name gracefully
- `PreferencePromptBanner` navigation target exists in `RootStackParamList`
- All new styles are properly referenced
- No TypeScript errors (`npx tsc --noEmit`)

- [ ] **Step 2: Report QA findings**

If issues found: send specific feedback to frontend-agent with file, line, and fix.
If no issues: sign off on frontend work.

### Task 8: Frontend agent QAs backend work

- [ ] **Step 1: Read all backend changes and verify correctness**

Read `app/services/extraction_service.py` and `app/services/structured_comparison_service.py`. Check:
- COMPARISON_PROMPT JSON schema is valid (no unescaped braces)
- `generate_comparison()` validation handles all edge cases
- `personalized_insights` flows through both streaming and non-streaming paths
- Broader search fallback doesn't trigger for supplements
- `MODEL_VARIANT_PATTERN` regex compiles and handles edge cases
- No syntax errors (`python -m py_compile`)

- [ ] **Step 2: Report QA findings**

If issues found: send specific feedback to backend-agent with file, line, and fix.
If no issues: sign off on backend work.

### Task 9: Test coverage to 80%

- [ ] **Step 1: Run existing tests and identify coverage gaps**

Run: `python -m pytest tests/test_guidance_insights.py tests/test_fallback_improvements.py -v`
Expected: All PASS

- [ ] **Step 2: Add edge case tests to reach 80%**

Add to `tests/test_guidance_insights.py`:

```python
class TestInsightsEdgeCases:
    """Edge cases for personalized insights."""

    @pytest.mark.asyncio
    async def test_insights_with_empty_preferences(self, sample_product_1, sample_product_2):
        """Empty dict preferences should strip insights (not crash)."""
        mock_response = {
            "winner_index": 0, "winner_reason": "Better",
            "product_0_pros": ["pro"], "product_0_cons": ["con"],
            "product_1_pros": ["pro"], "product_1_cons": ["con"],
            "price_comparison": {"cheaper_index": 0, "price_difference": "10 BHD", "better_value_index": 0},
            "specs_comparison": {"product_0_advantages": [], "product_1_advantages": [], "similar": []},
            "value_scores": [7.0, 6.0],
            "best_for": {"budget": 0, "performance": 0, "features": 0, "reliability": 0},
            "recommendation": "Buy A.", "key_differences": ["diff"],
            "personalized_insights": [
                {"focus_area": "price", "product_index": 0, "insight": "Hallucinated insight"}
            ],
        }
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(
            return_value=MagicMock(
                choices=[MagicMock(message=MagicMock(content=json.dumps(mock_response)))]
            )
        )
        with patch("app.services.extraction_service.get_client", return_value=mock_client):
            from app.services.extraction_service import generate_comparison
            # Empty dict should be treated as "no preferences"
            result = await generate_comparison(
                sample_product_1, sample_product_2, "bahrain",
                user_preferences={},
            )
            assert "personalized_insights" not in result

    @pytest.mark.asyncio
    async def test_insights_malformed_returns_empty_array(self, sample_product_1, sample_product_2, sample_preferences):
        """When GPT returns non-list insights, set empty array (don't crash)."""
        mock_response = {
            "winner_index": 0, "winner_reason": "Better",
            "product_0_pros": ["pro"], "product_0_cons": ["con"],
            "product_1_pros": ["pro"], "product_1_cons": ["con"],
            "price_comparison": {"cheaper_index": 0, "price_difference": "10 BHD", "better_value_index": 0},
            "specs_comparison": {"product_0_advantages": [], "product_1_advantages": [], "similar": []},
            "value_scores": [7.0, 6.0],
            "best_for": {"budget": 0, "performance": 0, "features": 0, "reliability": 0},
            "recommendation": "Buy A.", "key_differences": ["diff"],
            "personalized_insights": "not a list",
        }
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(
            return_value=MagicMock(
                choices=[MagicMock(message=MagicMock(content=json.dumps(mock_response)))]
            )
        )
        with patch("app.services.extraction_service.get_client", return_value=mock_client):
            from app.services.extraction_service import generate_comparison
            result = await generate_comparison(
                sample_product_1, sample_product_2, "bahrain",
                user_preferences=sample_preferences,
            )
            assert result.get("personalized_insights") == []

    def test_model_variant_pattern_multiple_passes(self):
        """Stripping should handle chained variants like 'Pro Max 256GB'."""
        from app.services.structured_comparison_service import MODEL_VARIANT_PATTERN
        name = "iPhone 15 Pro Max 256GB"
        for _ in range(3):
            name = MODEL_VARIANT_PATTERN.sub('', name).strip()
        assert name == "iPhone 15"
```

- [ ] **Step 3: Run full test suite**

Run: `python -m pytest tests/ -v -m "not (live_unit or live_db or integration)" --ignore=tests/test_integration.py`
Expected: All PASS, 0 regressions

- [ ] **Step 4: TypeScript check**

Run: `cd SmartCompareApp && npx tsc --noEmit`
Expected: 0 errors

- [ ] **Step 5: Final commit**

```bash
git add tests/test_guidance_insights.py tests/test_fallback_improvements.py
git commit -m "test: add edge case tests for guidance system (80%+ coverage)"
```

---

## Checkpoint Protocol

After Phase 1 (Tasks 1-6) completes, write `docs/superpowers/plans/session21-checkpoint.md`:

```markdown
# Session 21 Checkpoint — Phase 1 Complete

## What Changed
- `app/services/extraction_service.py` — personalized_insights in COMPARISON_PROMPT + validation
- `app/services/structured_comparison_service.py` — insights in response/SSE + broader price fallback
- `SmartCompareApp/src/types/types.ts` — PersonalizedInsight interface
- `SmartCompareApp/src/screens/ResultsScreen.tsx` — AspectBadges, InsightCard, PreferencePromptBanner, empty states
- `tests/test_guidance_insights.py` — 11+ tests
- `tests/test_fallback_improvements.py` — 10 tests

## Status
- [ ] All unit tests passing
- [ ] TypeScript compiles with 0 errors
- [ ] Cross-QA not yet started

## Remaining
- Tasks 7-9: Cross-QA + test coverage gap fill
```

After Phase 2 (Tasks 7-9) completes:
- Update `docs/CONTEXT_SESSION_LOG.md` with Session 21 entry
- Update `MEMORY.md` with AI Guidance System section
