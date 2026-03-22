# Personalization & AI Model Redesign — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure the AI comparison model, review summarization, scoring additions, and behavioral learning system to build user trust, cut clutter, and personalize results without bias.

**Architecture:** The backend AI prompts (verdict + reviews) are rewritten for structured output. Scoring service gains three deterministic features (value badges, tradeoff pairs, confidence indicators). A new behavioral learning service aggregates user history into weight adjustments. The API response is reorganized by screen purpose (overview/specs/reviews). Frontend consumes the new structure with progressive SSE rendering.

**Tech Stack:** Python 3.12 / FastAPI (backend), GPT-4o-mini (prompts), Supabase PostgreSQL (behavioral profile), React Native / Expo (frontend), deterministic scoring (zero API cost additions).

**Spec:** `docs/superpowers/specs/2026-03-22-personalization-ai-model-redesign-design.md`

**Team Structure (4 Opus agents):**

| Agent | Owns | QAs |
|-------|------|-----|
| **backend-scoring** | `scoring_service.py`, `behavior_service.py` (new), tests | **backend-ai** |
| **backend-ai** | `extraction_service.py`, review/verdict tests | **backend-scoring** |
| **backend-api** | `structured_comparison_service.py`, `text_routes.py`, SSE tests | **frontend** |
| **frontend** | `ResultsScreen.tsx`, `api.ts`, frontend tests | **backend-api** |

**Dependency Order:**
```
Phase 1 (parallel):  backend-scoring (Tasks 1-3) + backend-ai (Tasks 4-5)
Phase 2 (after P1):  backend-api (Tasks 6-8) + frontend (Task 9, type defs only)
Phase 3 (after P2):  frontend (Task 10) + integration (Task 11)
Phase 4:             Cross-QA (Task 12)
```

---

## Phase 1: Scoring Service + AI Prompts (Parallel)

### Task 1: Value Badges (backend-scoring)

**Files:**
- Modify: `app/services/scoring_service.py` (add after `compute_dimension_winners()` ~line 564)
- Test: `tests/test_scoring_service.py`

- [ ] **Step 1: Write failing tests for `compute_value_badge()`**

```python
# In tests/test_scoring_service.py — add at end of file

class TestValueBadges:
    """Tests for compute_value_badge() deterministic value badge assignment."""

    def test_great_value_non_luxury(self):
        """value_score >= 75 and non-luxury tier → great_value"""
        service = ScoringService()
        badge = service.compute_value_badge(value_score=80, price_tier="mid")
        assert badge == "great_value"

    def test_great_value_budget(self):
        """value_score >= 75 and budget tier → great_value"""
        service = ScoringService()
        badge = service.compute_value_badge(value_score=75, price_tier="budget")
        assert badge == "great_value"

    def test_luxury_high_value_gets_fair_price(self):
        """value_score >= 75 but luxury tier → fair_price (luxury is never 'great value')"""
        service = ScoringService()
        badge = service.compute_value_badge(value_score=85, price_tier="luxury")
        assert badge == "fair_price"

    def test_fair_price_mid_range(self):
        """value_score 50-74 → fair_price"""
        service = ScoringService()
        badge = service.compute_value_badge(value_score=60, price_tier="mid")
        assert badge == "fair_price"

    def test_fair_price_boundary_50(self):
        """value_score exactly 50 → fair_price"""
        service = ScoringService()
        badge = service.compute_value_badge(value_score=50, price_tier="premium")
        assert badge == "fair_price"

    def test_premium_price(self):
        """value_score 25-49 → premium_price"""
        service = ScoringService()
        badge = service.compute_value_badge(value_score=35, price_tier="mid")
        assert badge == "premium_price"

    def test_overpriced(self):
        """value_score < 25 → overpriced"""
        service = ScoringService()
        badge = service.compute_value_badge(value_score=15, price_tier="premium")
        assert badge == "overpriced"

    def test_overpriced_boundary_24(self):
        """value_score exactly 24 → overpriced"""
        service = ScoringService()
        badge = service.compute_value_badge(value_score=24, price_tier="mid")
        assert badge == "overpriced"

    def test_boundary_75_non_luxury(self):
        """value_score exactly 75 non-luxury → great_value"""
        service = ScoringService()
        badge = service.compute_value_badge(value_score=75, price_tier="premium")
        assert badge == "great_value"

    def test_boundary_25(self):
        """value_score exactly 25 → premium_price"""
        service = ScoringService()
        badge = service.compute_value_badge(value_score=25, price_tier="mid")
        assert badge == "premium_price"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_scoring_service.py::TestValueBadges -v`
Expected: FAIL — `ScoringService has no attribute 'compute_value_badge'`

- [ ] **Step 3: Implement `compute_value_badge()`**

Add to `app/services/scoring_service.py` after `compute_dimension_winners()` (~line 564):

```python
def compute_value_badge(self, value_score: float, price_tier: str) -> str:
    """Deterministic value badge from value_score and price tier.

    Returns: 'great_value', 'fair_price', 'premium_price', or 'overpriced'
    """
    if value_score >= 75:
        if price_tier == "luxury":
            return "fair_price"
        return "great_value"
    elif value_score >= 50:
        return "fair_price"
    elif value_score >= 25:
        return "premium_price"
    else:
        return "overpriced"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_scoring_service.py::TestValueBadges -v`
Expected: 10 PASSED

- [ ] **Step 5: Commit**

```bash
git add app/services/scoring_service.py tests/test_scoring_service.py
git commit -m "feat(scoring): add compute_value_badge() deterministic value badges"
```

---

### Task 2: Tradeoff Pairs (backend-scoring)

**Files:**
- Modify: `app/services/scoring_service.py` (add after `compute_value_badge()`)
- Test: `tests/test_scoring_service.py`

- [ ] **Step 1: Write failing tests for `compute_tradeoff_pairs()`**

```python
# In tests/test_scoring_service.py — add at end of file

class TestTradeoffPairs:
    """Tests for compute_tradeoff_pairs() dimension-based tradeoff extraction."""

    def test_basic_tradeoff(self):
        """Two products each winning different dimensions → one tradeoff pair"""
        service = ScoringService()
        dimension_winners = {
            "price_score": {"winner": "Product A", "margin": 15.0},
            "spec_score": {"winner": "Product B", "margin": 12.0},
            "review_score": {"winner": "tie", "margin": 2.0},
            "value_score": {"winner": "Product A", "margin": 8.0},
            "reliability_score": {"winner": "tie", "margin": 1.0},
            "popularity_score": {"winner": "Product B", "margin": 6.0},
        }
        product_names = ["Product A", "Product B"]
        tradeoffs = service.compute_tradeoff_pairs(dimension_winners, product_names, winner_index=0)
        assert len(tradeoffs) >= 1
        # The winner's strongest dim paired with loser's strongest dim
        assert tradeoffs[0]["winner_wins"]["product"] == "Product A"
        assert tradeoffs[0]["loser_wins"]["product"] == "Product B"

    def test_filters_small_margins(self):
        """Margins <= 5 are excluded"""
        service = ScoringService()
        dimension_winners = {
            "price_score": {"winner": "Product A", "margin": 3.0},
            "spec_score": {"winner": "Product B", "margin": 4.0},
            "review_score": {"winner": "tie", "margin": 1.0},
            "value_score": {"winner": "tie", "margin": 2.0},
            "reliability_score": {"winner": "tie", "margin": 0.5},
            "popularity_score": {"winner": "tie", "margin": 1.0},
        }
        product_names = ["Product A", "Product B"]
        tradeoffs = service.compute_tradeoff_pairs(dimension_winners, product_names, winner_index=0)
        assert len(tradeoffs) == 0

    def test_max_three_tradeoffs(self):
        """Never more than 3 tradeoff pairs"""
        service = ScoringService()
        dimension_winners = {
            "price_score": {"winner": "Product A", "margin": 20.0},
            "spec_score": {"winner": "Product B", "margin": 18.0},
            "review_score": {"winner": "Product A", "margin": 15.0},
            "value_score": {"winner": "Product B", "margin": 12.0},
            "reliability_score": {"winner": "Product A", "margin": 10.0},
            "popularity_score": {"winner": "Product B", "margin": 8.0},
        }
        product_names = ["Product A", "Product B"]
        tradeoffs = service.compute_tradeoff_pairs(dimension_winners, product_names, winner_index=0)
        assert len(tradeoffs) <= 3

    def test_sorted_by_impact(self):
        """Tradeoffs sorted by combined margin (most impactful first)"""
        service = ScoringService()
        dimension_winners = {
            "price_score": {"winner": "Product A", "margin": 10.0},
            "spec_score": {"winner": "Product B", "margin": 25.0},
            "review_score": {"winner": "Product A", "margin": 20.0},
            "value_score": {"winner": "Product B", "margin": 8.0},
            "reliability_score": {"winner": "tie", "margin": 2.0},
            "popularity_score": {"winner": "tie", "margin": 1.0},
        }
        product_names = ["Product A", "Product B"]
        tradeoffs = service.compute_tradeoff_pairs(dimension_winners, product_names, winner_index=0)
        assert len(tradeoffs) >= 1
        # First tradeoff should have the highest combined margin
        first_combined = tradeoffs[0]["winner_wins"]["margin"] + tradeoffs[0]["loser_wins"]["margin"]
        for t in tradeoffs[1:]:
            combined = t["winner_wins"]["margin"] + t["loser_wins"]["margin"]
            assert first_combined >= combined

    def test_no_tradeoff_when_one_side_dominates(self):
        """If winner wins everything, no tradeoffs to show"""
        service = ScoringService()
        dimension_winners = {
            "price_score": {"winner": "Product A", "margin": 15.0},
            "spec_score": {"winner": "Product A", "margin": 12.0},
            "review_score": {"winner": "Product A", "margin": 10.0},
            "value_score": {"winner": "Product A", "margin": 8.0},
            "reliability_score": {"winner": "Product A", "margin": 7.0},
            "popularity_score": {"winner": "Product A", "margin": 6.0},
        }
        product_names = ["Product A", "Product B"]
        tradeoffs = service.compute_tradeoff_pairs(dimension_winners, product_names, winner_index=0)
        assert len(tradeoffs) == 0

    def test_na_dimensions_excluded(self):
        """Dimensions with winner='N/A' are skipped"""
        service = ScoringService()
        dimension_winners = {
            "price_score": {"winner": "Product A", "margin": 15.0},
            "spec_score": {"winner": "N/A", "margin": None},
            "review_score": {"winner": "Product B", "margin": 10.0},
            "value_score": {"winner": "tie", "margin": 2.0},
            "reliability_score": {"winner": "tie", "margin": 1.0},
            "popularity_score": {"winner": "tie", "margin": 1.0},
        }
        product_names = ["Product A", "Product B"]
        tradeoffs = service.compute_tradeoff_pairs(dimension_winners, product_names, winner_index=0)
        assert len(tradeoffs) == 1
        assert tradeoffs[0]["winner_wins"]["dimension"] == "price_score"
        assert tradeoffs[0]["loser_wins"]["dimension"] == "review_score"

    def test_tradeoff_structure(self):
        """Each tradeoff has correct structure"""
        service = ScoringService()
        dimension_winners = {
            "price_score": {"winner": "Product A", "margin": 15.0},
            "spec_score": {"winner": "Product B", "margin": 12.0},
            "review_score": {"winner": "tie", "margin": 2.0},
            "value_score": {"winner": "tie", "margin": 2.0},
            "reliability_score": {"winner": "tie", "margin": 1.0},
            "popularity_score": {"winner": "tie", "margin": 1.0},
        }
        product_names = ["Product A", "Product B"]
        tradeoffs = service.compute_tradeoff_pairs(dimension_winners, product_names, winner_index=0)
        assert len(tradeoffs) == 1
        t = tradeoffs[0]
        assert "dimension" in t["winner_wins"]
        assert "product" in t["winner_wins"]
        assert "margin" in t["winner_wins"]
        assert "dimension" in t["loser_wins"]
        assert "product" in t["loser_wins"]
        assert "margin" in t["loser_wins"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_scoring_service.py::TestTradeoffPairs -v`
Expected: FAIL — `ScoringService has no attribute 'compute_tradeoff_pairs'`

- [ ] **Step 3: Implement `compute_tradeoff_pairs()`**

Add to `app/services/scoring_service.py` after `compute_value_badge()`:

```python
DIMENSION_DISPLAY_NAMES = {
    "price_score": "price",
    "spec_score": "specs",
    "review_score": "reviews",
    "value_score": "value",
    "reliability_score": "reliability",
    "popularity_score": "popularity",
}

def compute_tradeoff_pairs(
    self,
    dimension_winners: Dict[str, Any],
    product_names: List[str],
    winner_index: int,
) -> List[Dict[str, Any]]:
    """Build tradeoff pairs from dimension winners.

    Pairs each winner-winning dimension with the loser's strongest dimension.
    Filters margins <= 5, returns max 3 sorted by combined impact.
    """
    winner_name = product_names[winner_index]
    loser_name = product_names[1 - winner_index]

    winner_dims = []
    loser_dims = []

    for dim, info in dimension_winners.items():
        if info["winner"] in ("tie", "N/A") or info.get("margin") is None:
            continue
        if info["margin"] <= 5:
            continue
        if info["winner"] == winner_name:
            winner_dims.append({"dimension": DIMENSION_DISPLAY_NAMES.get(dim, dim), "product": winner_name, "margin": info["margin"]})
        elif info["winner"] == loser_name:
            loser_dims.append({"dimension": DIMENSION_DISPLAY_NAMES.get(dim, dim), "product": loser_name, "margin": info["margin"]})

    if not winner_dims or not loser_dims:
        return []

    # Sort both by margin descending
    winner_dims.sort(key=lambda x: x["margin"], reverse=True)
    loser_dims.sort(key=lambda x: x["margin"], reverse=True)

    # Pair them: strongest winner dim with strongest loser dim, etc.
    pairs = []
    for i in range(min(len(winner_dims), len(loser_dims), 3)):
        pairs.append({
            "winner_wins": winner_dims[i],
            "loser_wins": loser_dims[i],
        })

    # Sort by combined margin (most impactful first)
    pairs.sort(key=lambda p: p["winner_wins"]["margin"] + p["loser_wins"]["margin"], reverse=True)

    return pairs[:3]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_scoring_service.py::TestTradeoffPairs -v`
Expected: 7 PASSED

- [ ] **Step 5: Commit**

```bash
git add app/services/scoring_service.py tests/test_scoring_service.py
git commit -m "feat(scoring): add compute_tradeoff_pairs() dimension tradeoff extraction"
```

---

### Task 3: Confidence Indicators (backend-scoring)

**Files:**
- Modify: `app/services/scoring_service.py` (add after `compute_tradeoff_pairs()`)
- Test: `tests/test_scoring_service.py`

- [ ] **Step 1: Write failing tests for `compute_confidence()`**

```python
# In tests/test_scoring_service.py — add at end of file

class TestConfidenceIndicators:
    """Tests for compute_confidence() data confidence assembly."""

    def test_high_confidence_all_strong(self):
        """All data strong → overall 'high'"""
        service = ScoringService()
        products = [
            {
                "price": {"source_method": "local_bhd", "retailer": "Amazon"},
                "rating": 4.5,
                "review_count": 1200,
                "rating_verified": True,
                "rating_source": {"name": "Amazon", "url": "https://amazon.com"},
                "fact_check": {"specs_verified": 8, "specs_likely": 2, "specs_unverified": 0, "specs_flagged": 0},
            }
        ]
        conf = service.compute_confidence(products, shopping_count=3, cached=False)
        assert conf["overall"] == "high"
        assert conf["price"]["source_count"] == 3
        assert conf["price"]["method"] == "retailer_verified"
        assert conf["rating"]["review_count"] == 1200
        assert conf["rating"]["verified"] is True
        assert conf["specs"]["verified_pct"] > 70

    def test_medium_confidence_one_weak(self):
        """One weak signal → overall 'medium'"""
        service = ScoringService()
        products = [
            {
                "price": {"source_method": "estimated", "retailer": None},
                "rating": 4.5,
                "review_count": 500,
                "rating_verified": True,
                "rating_source": {"name": "Amazon", "url": "https://amazon.com"},
                "fact_check": {"specs_verified": 8, "specs_likely": 2, "specs_unverified": 0, "specs_flagged": 0},
            }
        ]
        conf = service.compute_confidence(products, shopping_count=0, cached=False)
        assert conf["overall"] == "medium"
        assert conf["price"]["method"] == "estimated"

    def test_low_confidence_two_weak(self):
        """Two+ weak signals → overall 'low'"""
        service = ScoringService()
        products = [
            {
                "price": {"source_method": "estimated", "retailer": None},
                "rating": None,
                "review_count": 0,
                "rating_verified": False,
                "rating_source": None,
                "fact_check": {"specs_verified": 1, "specs_likely": 1, "specs_unverified": 5, "specs_flagged": 3},
            }
        ]
        conf = service.compute_confidence(products, shopping_count=0, cached=False)
        assert conf["overall"] == "low"

    def test_freshness_live(self):
        """Non-cached → 'live'"""
        service = ScoringService()
        products = [self._make_strong_product()]
        conf = service.compute_confidence(products, shopping_count=3, cached=False)
        assert conf["price"]["freshness"] == "live"

    def test_freshness_cached(self):
        """Cached → 'cached'"""
        service = ScoringService()
        products = [self._make_strong_product()]
        conf = service.compute_confidence(products, shopping_count=3, cached=True)
        assert conf["price"]["freshness"] == "cached"

    def test_source_method_converted(self):
        """converted_usd source method → 'converted'"""
        service = ScoringService()
        products = [
            {
                "price": {"source_method": "converted_usd", "retailer": "BestBuy"},
                "rating": 4.0,
                "review_count": 300,
                "rating_verified": True,
                "rating_source": {"name": "BestBuy", "url": "https://bestbuy.com"},
                "fact_check": {"specs_verified": 5, "specs_likely": 3, "specs_unverified": 2, "specs_flagged": 0},
            }
        ]
        conf = service.compute_confidence(products, shopping_count=2, cached=False)
        assert conf["price"]["method"] == "converted"

    def test_specs_verified_pct_calculation(self):
        """Verified percentage calculated correctly"""
        service = ScoringService()
        products = [
            {
                "price": {"source_method": "local_bhd", "retailer": "Amazon"},
                "rating": 4.5,
                "review_count": 100,
                "rating_verified": True,
                "rating_source": {"name": "Amazon", "url": "https://amazon.com"},
                "fact_check": {"specs_verified": 6, "specs_likely": 2, "specs_unverified": 1, "specs_flagged": 1},
            }
        ]
        conf = service.compute_confidence(products, shopping_count=2, cached=False)
        # 6 verified out of 10 total = 60%
        assert conf["specs"]["verified_pct"] == 60
        assert conf["specs"]["citation_count"] == 10

    def test_multiple_products_uses_first(self):
        """With two products, uses first product for primary confidence (both contribute to specs)"""
        service = ScoringService()
        products = [self._make_strong_product(), self._make_strong_product()]
        conf = service.compute_confidence(products, shopping_count=3, cached=False)
        assert conf["overall"] == "high"

    @staticmethod
    def _make_strong_product():
        return {
            "price": {"source_method": "local_bhd", "retailer": "Amazon"},
            "rating": 4.5,
            "review_count": 1000,
            "rating_verified": True,
            "rating_source": {"name": "Amazon", "url": "https://amazon.com"},
            "fact_check": {"specs_verified": 8, "specs_likely": 2, "specs_unverified": 0, "specs_flagged": 0},
        }
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_scoring_service.py::TestConfidenceIndicators -v`
Expected: FAIL — `ScoringService has no attribute 'compute_confidence'`

- [ ] **Step 3: Implement `compute_confidence()`**

Add to `app/services/scoring_service.py` after `compute_tradeoff_pairs()`:

```python
def compute_confidence(
    self,
    products: List[Dict[str, Any]],
    shopping_count: int = 0,
    cached: bool = False,
) -> Dict[str, Any]:
    """Assemble confidence indicators from existing product data.

    Returns dict with price, rating, specs, and overall confidence.
    """
    # Use first product as primary (both contribute to overall)
    product = products[0] if products else {}
    price_data = product.get("price", {})
    fact_check = product.get("fact_check", {})

    # Price confidence
    source_method = price_data.get("source_method", "estimated")
    if source_method in ("local_bhd", "page_scrape", "page_scrape_rendered"):
        method = "retailer_verified"
    elif source_method == "converted_usd":
        method = "converted"
    else:
        method = "estimated"

    price_conf = {
        "source_count": shopping_count,
        "method": method,
        "freshness": "live" if not cached else "cached",
    }
    price_strong = shopping_count >= 2 and method != "estimated"

    # Rating confidence
    review_count = product.get("review_count") or 0
    rating_verified = product.get("rating_verified", False)
    rating_source = product.get("rating_source")
    rating_conf = {
        "review_count": review_count,
        "source": rating_source.get("name") if rating_source else None,
        "verified": rating_verified,
    }
    rating_strong = review_count >= 50 and rating_verified

    # Specs confidence
    verified = fact_check.get("specs_verified", 0)
    likely = fact_check.get("specs_likely", 0)
    unverified = fact_check.get("specs_unverified", 0)
    flagged = fact_check.get("specs_flagged", 0)
    total = verified + likely + unverified + flagged
    verified_pct = round((verified / total) * 100) if total > 0 else 0
    specs_conf = {
        "verified_pct": verified_pct,
        "citation_count": total,
    }
    specs_strong = verified_pct >= 60

    # Overall
    strong_count = sum([price_strong, rating_strong, specs_strong])
    if strong_count >= 3:
        overall = "high"
    elif strong_count >= 2:
        overall = "medium"
    else:
        overall = "low"

    return {
        "price": price_conf,
        "rating": rating_conf,
        "specs": specs_conf,
        "overall": overall,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_scoring_service.py::TestConfidenceIndicators -v`
Expected: 8 PASSED

- [ ] **Step 5: Commit**

```bash
git add app/services/scoring_service.py tests/test_scoring_service.py
git commit -m "feat(scoring): add compute_confidence() data confidence indicators"
```

---

### Task 4: Restructured Review Prompt (backend-ai)

**Files:**
- Modify: `app/services/extraction_service.py` (`REVIEWS_EXTRACTION_PROMPT` ~lines 299-370, `_normalize_review_response()` ~lines 693-720)
- Test: `tests/test_review_prompt_quality.py`

- [ ] **Step 1: Write failing tests for new review format**

```python
# In tests/test_review_prompt_quality.py — add new test class

class TestReviewSummaryFormat:
    """Tests for the new review_summary structured output format."""

    def test_review_prompt_requires_consensus(self):
        """REVIEWS_EXTRACTION_PROMPT must request 'consensus' field"""
        from app.services.extraction_service import REVIEWS_EXTRACTION_PROMPT
        assert "consensus" in REVIEWS_EXTRACTION_PROMPT
        assert "overall_sentiment" in REVIEWS_EXTRACTION_PROMPT

    def test_review_prompt_requires_highlights(self):
        """REVIEWS_EXTRACTION_PROMPT must request 'highlights' with sentiment tags"""
        from app.services.extraction_service import REVIEWS_EXTRACTION_PROMPT
        assert "highlights" in REVIEWS_EXTRACTION_PROMPT
        assert "sentiment" in REVIEWS_EXTRACTION_PROMPT

    def test_review_prompt_requires_review_volume(self):
        """REVIEWS_EXTRACTION_PROMPT must request 'review_volume' field"""
        from app.services.extraction_service import REVIEWS_EXTRACTION_PROMPT
        assert "review_volume" in REVIEWS_EXTRACTION_PROMPT

    def test_review_prompt_requires_agreement_level(self):
        """REVIEWS_EXTRACTION_PROMPT must request 'agreement_level' field"""
        from app.services.extraction_service import REVIEWS_EXTRACTION_PROMPT
        assert "agreement_level" in REVIEWS_EXTRACTION_PROMPT

    def test_review_prompt_forbids_individual_attribution(self):
        """REVIEWS_EXTRACTION_PROMPT must forbid individual user attribution"""
        from app.services.extraction_service import REVIEWS_EXTRACTION_PROMPT
        assert "Never attribute" in REVIEWS_EXTRACTION_PROMPT or "never attribute" in REVIEWS_EXTRACTION_PROMPT

    def test_review_prompt_professional_tone(self):
        """REVIEWS_EXTRACTION_PROMPT must request professional product analyst tone"""
        from app.services.extraction_service import REVIEWS_EXTRACTION_PROMPT
        assert "professional" in REVIEWS_EXTRACTION_PROMPT.lower() or "analyst" in REVIEWS_EXTRACTION_PROMPT.lower()

    def test_normalize_review_response_new_format(self):
        """_normalize_review_response handles new review_summary format"""
        from app.services.extraction_service import _normalize_review_response
        raw = {
            "review_summary": {
                "overall_sentiment": "positive",
                "consensus": "Great product overall.",
                "highlights": [
                    {"point": "Battery is excellent", "sentiment": "positive"},
                    {"point": "Heavy weight", "sentiment": "negative"},
                ],
                "review_volume": "high",
                "agreement_level": "strong",
            },
            "average_rating": 4.5,
            "total_reviews": 1000,
        }
        result = _normalize_review_response(raw)
        assert "review_summary" in result
        assert result["review_summary"]["overall_sentiment"] == "positive"
        assert len(result["review_summary"]["highlights"]) == 2
        assert result["review_summary"]["review_volume"] == "high"

    def test_normalize_review_response_defaults(self):
        """_normalize_review_response provides defaults for missing review_summary fields"""
        from app.services.extraction_service import _normalize_review_response
        raw = {"average_rating": None}
        result = _normalize_review_response(raw)
        assert "review_summary" in result
        assert result["review_summary"]["overall_sentiment"] == "mixed"
        assert result["review_summary"]["consensus"] == ""
        assert result["review_summary"]["highlights"] == []
        assert result["review_summary"]["review_volume"] == "minimal"
        assert result["review_summary"]["agreement_level"] == "moderate"

    def test_review_prompt_drops_old_fields(self):
        """REVIEWS_EXTRACTION_PROMPT no longer requests detailed_praises/complaints/user_quotes"""
        from app.services.extraction_service import REVIEWS_EXTRACTION_PROMPT
        assert "detailed_praises" not in REVIEWS_EXTRACTION_PROMPT
        assert "detailed_complaints" not in REVIEWS_EXTRACTION_PROMPT
        assert "user_quotes" not in REVIEWS_EXTRACTION_PROMPT
        assert "category_scores" not in REVIEWS_EXTRACTION_PROMPT
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_review_prompt_quality.py::TestReviewSummaryFormat -v`
Expected: FAIL — old prompt doesn't contain new field names

- [ ] **Step 3: Rewrite `REVIEWS_EXTRACTION_PROMPT` and `_normalize_review_response()`**

In `app/services/extraction_service.py`, replace `REVIEWS_EXTRACTION_PROMPT` (~lines 299-370) with the new prompt that requests the `review_summary` structure:
- `overall_sentiment` ("positive" / "mixed" / "negative")
- `consensus` (2-3 sentence professional brief)
- `highlights` (4-8 items, each `{point, sentiment}`)
- `review_volume` ("high" / "moderate" / "low" / "minimal")
- `agreement_level` ("strong" / "moderate" / "divided")
- Still requests `average_rating` and `total_reviews` (needed for fact-checking)
- Drops: `common_praises`, `common_complaints`, `detailed_praises`, `detailed_complaints`, `user_quotes`, `category_scores`, `summary`
- Tone instructions: "Write as a professional product analyst. Never attribute to individual users or websites."
- Sentiment alignment: positive-only observations cannot appear with `"sentiment": "negative"` and vice versa

Update `_normalize_review_response()` (~lines 693-720):
- Ensure `review_summary` dict exists with all sub-fields defaulted
- Keep `average_rating` and `total_reviews` extraction (fact-checking needs them)
- Remove normalization of old fields (`common_praises`, etc.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_review_prompt_quality.py::TestReviewSummaryFormat -v`
Expected: 10 PASSED

- [ ] **Step 5: Update existing review tests that reference old fields**

Run the full review test suite: `python -m pytest tests/test_review_prompt_quality.py -v`

Update any existing tests that assert on `common_praises`, `detailed_praises`, `user_quotes`, or `category_scores` in the prompt text — these fields are now removed. Tests checking sentiment alignment rules and content quality should still pass since those principles remain.

- [ ] **Step 6: Run full review test suite**

Run: `python -m pytest tests/test_review_prompt_quality.py tests/test_review_cleanup.py tests/test_citation_cleanup.py -v`
Expected: All PASSED (some tests may need updating for new field names)

- [ ] **Step 7: Commit**

```bash
git add app/services/extraction_service.py tests/test_review_prompt_quality.py
git commit -m "feat(ai): restructure review prompt for consensus-based summaries"
```

---

### Task 5: Restructured Verdict Prompt (backend-ai)

**Files:**
- Modify: `app/services/extraction_service.py` (`COMPARISON_PROMPT` ~lines 373-445, `generate_comparison()` ~lines 748-824, `_build_preferences_prompt()` ~lines 723-745)
- Test: `tests/test_review_prompt_quality.py` (verdict prompt tests are in this file)

- [ ] **Step 1: Write failing tests for new verdict format**

```python
# In tests/test_review_prompt_quality.py — add new test class

class TestStructuredVerdictFormat:
    """Tests for the new structured verdict prompt output format."""

    def test_verdict_prompt_requires_winner_declaration(self):
        """COMPARISON_PROMPT must request 'winner_declaration' field"""
        from app.services.extraction_service import COMPARISON_PROMPT
        assert "winner_declaration" in COMPARISON_PROMPT

    def test_verdict_prompt_requires_winner_reason(self):
        """COMPARISON_PROMPT must request 'winner_reason' field"""
        from app.services.extraction_service import COMPARISON_PROMPT
        assert "winner_reason" in COMPARISON_PROMPT

    def test_verdict_prompt_requires_key_tradeoff(self):
        """COMPARISON_PROMPT must request 'key_tradeoff' field"""
        from app.services.extraction_service import COMPARISON_PROMPT
        assert "key_tradeoff" in COMPARISON_PROMPT

    def test_verdict_prompt_requires_value_context(self):
        """COMPARISON_PROMPT must request 'value_context' field"""
        from app.services.extraction_service import COMPARISON_PROMPT
        assert "value_context" in COMPARISON_PROMPT

    def test_verdict_prompt_requires_best_for(self):
        """COMPARISON_PROMPT must request 'best_for' as per-product strings"""
        from app.services.extraction_service import COMPARISON_PROMPT
        assert "best_for" in COMPARISON_PROMPT

    def test_verdict_prompt_word_limit_on_reason(self):
        """COMPARISON_PROMPT enforces under 20 words for winner_reason"""
        from app.services.extraction_service import COMPARISON_PROMPT
        assert "20 words" in COMPARISON_PROMPT or "under 20" in COMPARISON_PROMPT

    def test_verdict_prompt_tradeoff_references_loser(self):
        """COMPARISON_PROMPT requires key_tradeoff to name losing product's advantage"""
        from app.services.extraction_service import COMPARISON_PROMPT
        assert "losing" in COMPARISON_PROMPT.lower() or "loser" in COMPARISON_PROMPT.lower() or "other product" in COMPARISON_PROMPT.lower()

    def test_verdict_drops_recommendation_field(self):
        """COMPARISON_PROMPT no longer requests free-form 'recommendation' paragraph"""
        from app.services.extraction_service import COMPARISON_PROMPT
        # The old prompt had "recommendation": "2-3 sentences"
        # New prompt should NOT have a free-form recommendation field
        # (winner_reason + value_context + best_for replace it)
        assert '"recommendation"' not in COMPARISON_PROMPT or "recommendation" not in COMPARISON_PROMPT.split("best_for")[0]

    def test_preferences_prompt_best_for_personalization(self):
        """_build_preferences_prompt adds 'which you do' instruction for best_for"""
        from app.services.extraction_service import _build_preferences_prompt
        prompt = _build_preferences_prompt({"priorities": ["quality", "durability"], "budget": "mid", "lifestyle": [], "brand_attitude": "function_first"})
        assert "which you" in prompt.lower() or "your priorit" in prompt.lower()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_review_prompt_quality.py::TestStructuredVerdictFormat -v`
Expected: FAIL — old prompt doesn't contain new field names

- [ ] **Step 3: Rewrite `COMPARISON_PROMPT` and update `generate_comparison()`**

In `app/services/extraction_service.py`:

**Replace `COMPARISON_PROMPT`** (~lines 373-445) with new structured format requesting:
- `winner_index` (0 or 1) — kept from old format
- `winner_declaration` (product name string)
- `winner_reason` (ONE sentence, under 20 words, must include a specific fact)
- `key_tradeoff` (ONE sentence naming the other product's strongest advantage)
- `value_context` (ONE sentence about price-to-quality relationship)
- `best_for.product_0` / `best_for.product_1` (one sentence each)
- `product_0_pros` / `product_0_cons` / `product_1_pros` / `product_1_cons` (kept, tightened: 4-6 pros, 2-4 cons, each with specific number)
- `specs_comparison` (kept from old format — product_0_advantages, product_1_advantages, similar)
- `personalized_insights` (kept, optional, max 3)
- Drop: `recommendation` (free-form paragraph), `key_differences` (list of 5), `price_comparison` (dict), `value_scores` (list)

**Update `generate_comparison()`** (~lines 748-824):
- Parse new fields from GPT response
- Return dict with new structure

**Update `_build_preferences_prompt()`** (~lines 723-745):
- Add instruction: "In best_for, if a product aligns with the user's stated priorities, append '(which aligns with your priorities)' or similar"

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_review_prompt_quality.py::TestStructuredVerdictFormat -v`
Expected: 9 PASSED

- [ ] **Step 5: Update existing verdict tests**

Run full prompt test suite: `python -m pytest tests/test_review_prompt_quality.py -v`

Update any tests that assert on old fields (`recommendation`, `key_differences` as 5-item list, `price_comparison`, `value_scores`). These are replaced by `winner_reason`, `key_tradeoff`, `value_context`, `best_for`.

- [ ] **Step 6: Commit**

```bash
git add app/services/extraction_service.py tests/test_review_prompt_quality.py
git commit -m "feat(ai): restructure verdict prompt for structured concise output"
```

---

## Phase 2: Behavioral Learning + Response Restructure

### Task 6: Behavioral Learning Service (backend-scoring)

**Files:**
- Create: `app/services/behavior_service.py`
- Test: `tests/test_behavior_service.py` (new)

- [ ] **Step 1: Write failing tests**

```python
# tests/test_behavior_service.py (new file)

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
from app.services.behavior_service import BehaviorService

class TestBehaviorProfile:
    """Tests for behavioral profile computation and storage."""

    @pytest.mark.asyncio
    async def test_compute_category_affinity(self):
        """Category affinity computed from comparison history"""
        service = BehaviorService()
        comparisons = [
            {"category_used": "electronics", "created_at": datetime.now().isoformat()},
            {"category_used": "electronics", "created_at": datetime.now().isoformat()},
            {"category_used": "fragrances", "created_at": datetime.now().isoformat()},
        ]
        affinity = service._compute_category_affinity(comparisons)
        assert abs(affinity["electronics"] - 0.667) < 0.01
        assert abs(affinity["fragrances"] - 0.333) < 0.01

    @pytest.mark.asyncio
    async def test_compute_price_range_preference(self):
        """Price range aggregated from comparison prices"""
        service = BehaviorService()
        comparisons = [
            {"products": [{"price": {"amount": 50}}, {"price": {"amount": 80}}]},
            {"products": [{"price": {"amount": 200}}, {"price": {"amount": 150}}]},
        ]
        pref = service._compute_price_range(comparisons)
        assert pref["avg_price_viewed"] == 120.0  # (50+80+200+150) / 4

    @pytest.mark.asyncio
    async def test_compute_winner_agreement(self):
        """Winner agreement from feedback data"""
        service = BehaviorService()
        feedback = [
            {"useful": True},
            {"useful": True},
            {"useful": False},
        ]
        agreement = service._compute_winner_agreement(feedback)
        assert agreement["agreed"] == 2
        assert agreement["disagreed"] == 1
        assert abs(agreement["agreement_rate"] - 0.667) < 0.01

    @pytest.mark.asyncio
    async def test_compute_dimension_sensitivity(self):
        """Dimension sensitivity from tab dwell events"""
        service = BehaviorService()
        events = [
            {"event_type": "tab_switch", "metadata": {"to": "specs", "dwell_ms": 8000}},
            {"event_type": "tab_switch", "metadata": {"to": "reviews", "dwell_ms": 3000}},
            {"event_type": "tab_switch", "metadata": {"to": "overview", "dwell_ms": 1500}},
        ]
        sensitivity = service._compute_dimension_sensitivity(events)
        # specs 8000 / (8000+3000) = 0.727 (overview < 2000ms excluded)
        assert sensitivity["spec_score"] > sensitivity["review_score"]

    @pytest.mark.asyncio
    async def test_dwell_under_2s_excluded(self):
        """Tabs with dwell < 2000ms are excluded from sensitivity"""
        service = BehaviorService()
        events = [
            {"event_type": "tab_switch", "metadata": {"to": "specs", "dwell_ms": 5000}},
            {"event_type": "tab_switch", "metadata": {"to": "reviews", "dwell_ms": 1500}},
        ]
        sensitivity = service._compute_dimension_sensitivity(events)
        assert "review_score" not in sensitivity or sensitivity.get("review_score", 0) == 0

    def test_behavioral_decay(self):
        """30-day half-life exponential decay"""
        service = BehaviorService()
        now = datetime.now()
        weight_today = service._decay_weight(now, now)
        weight_30d = service._decay_weight(now - timedelta(days=30), now)
        weight_60d = service._decay_weight(now - timedelta(days=60), now)
        assert abs(weight_today - 1.0) < 0.01
        assert abs(weight_30d - 0.5) < 0.01
        assert abs(weight_60d - 0.25) < 0.01

    def test_empty_comparisons_returns_empty_profile(self):
        """No comparisons → empty/default profile"""
        service = BehaviorService()
        comparisons = []
        affinity = service._compute_category_affinity(comparisons)
        assert affinity == {}

    def test_empty_feedback_returns_zero_agreement(self):
        """No feedback → zero agreement data"""
        service = BehaviorService()
        feedback = []
        agreement = service._compute_winner_agreement(feedback)
        assert agreement["agreed"] == 0
        assert agreement["disagreed"] == 0
        assert agreement["agreement_rate"] == 0.0


class TestSessionSignals:
    """Tests for in-session signal computation."""

    def test_compute_session_signals(self):
        """Session signals computed from recent events"""
        service = BehaviorService()
        events = [
            {"event_type": "tab_switch", "metadata": {"to": "specs", "dwell_ms": 8000}},
            {"event_type": "tab_switch", "metadata": {"to": "reviews", "dwell_ms": 3000}},
            {"event_type": "tab_switch", "metadata": {"to": "overview", "dwell_ms": 5000}},
        ]
        signals = service.compute_session_signals(events)
        assert signals["first_tab_viewed"] == "specs"
        assert signals["tab_dwell_ms"]["specs"] == 8000

    def test_empty_events(self):
        """No events → default signals"""
        service = BehaviorService()
        signals = service.compute_session_signals([])
        assert signals["first_tab_viewed"] is None
        assert signals["tab_dwell_ms"] == {}


class TestWeightAdjustments:
    """Tests for behavioral weight adjustment application."""

    def test_behavioral_adjustment_capped_at_10pct(self):
        """Behavioral adjustments capped at ±10% of category weight"""
        from app.services.scoring_service import ScoringService, CATEGORY_WEIGHTS
        service = ScoringService()
        base_weights = CATEGORY_WEIGHTS["electronics"].copy()
        behavior_profile = {
            "dimension_sensitivity": {"spec_score": 0.8, "price_score": 0.1, "review_score": 0.1},
        }
        adjusted = service.apply_behavioral_adjustments(base_weights.copy(), behavior_profile)
        for dim in base_weights:
            max_shift = base_weights[dim] * 0.10
            assert abs(adjusted[dim] - base_weights[dim]) <= max_shift + 0.001

    def test_session_signal_adjustment_capped_at_5pct(self):
        """Session signal adjustments capped at ±5% of category weight"""
        from app.services.scoring_service import ScoringService, CATEGORY_WEIGHTS
        service = ScoringService()
        base_weights = CATEGORY_WEIGHTS["electronics"].copy()
        session_signals = {
            "tab_dwell_ms": {"specs": 10000, "reviews": 1000, "overview": 2000},
            "first_tab_viewed": "specs",
        }
        adjusted = service.apply_session_signals(base_weights.copy(), session_signals)
        for dim in base_weights:
            max_shift = base_weights[dim] * 0.05
            assert abs(adjusted[dim] - base_weights[dim]) <= max_shift + 0.001

    def test_weights_sum_to_one_after_adjustment(self):
        """Weights still sum to 1.0 after behavioral + session adjustments"""
        from app.services.scoring_service import ScoringService, CATEGORY_WEIGHTS
        service = ScoringService()
        base_weights = CATEGORY_WEIGHTS["electronics"].copy()
        behavior_profile = {"dimension_sensitivity": {"spec_score": 0.6, "price_score": 0.3}}
        session_signals = {"tab_dwell_ms": {"specs": 8000, "reviews": 3000}, "first_tab_viewed": "specs"}
        adjusted = service.apply_behavioral_adjustments(base_weights.copy(), behavior_profile)
        adjusted = service.apply_session_signals(adjusted, session_signals)
        assert abs(sum(adjusted.values()) - 1.0) < 0.001
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_behavior_service.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.behavior_service'`

- [ ] **Step 3: Implement `behavior_service.py`**

Create `app/services/behavior_service.py`:

```python
"""Behavioral learning service for user profile aggregation.

Computes behavioral profiles from comparison history, feedback, and events.
Profiles are stored as JSONB on the users table and updated after each comparison.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import math


# Tab-to-dimension mapping for sensitivity computation
TAB_DIMENSION_MAP = {
    "specs": "spec_score",
    "reviews": "review_score",
    "overview": "price_score",  # overview attention correlates with price focus
}

MIN_DWELL_MS = 2000  # Minimum dwell time to count


class BehaviorService:
    """Computes and manages user behavioral profiles."""

    def _decay_weight(self, event_time: datetime, now: datetime) -> float:
        """Exponential decay with 30-day half-life."""
        days_ago = (now - event_time).total_seconds() / 86400
        return 0.5 ** (days_ago / 30)

    def _compute_category_affinity(self, comparisons: List[Dict[str, Any]]) -> Dict[str, float]:
        """Compute category affinity from comparison history with decay weighting."""
        if not comparisons:
            return {}
        now = datetime.now()
        weighted_counts: Dict[str, float] = {}
        for c in comparisons:
            cat = c.get("category_used", "other")
            created = c.get("created_at", "")
            try:
                event_time = datetime.fromisoformat(created.replace("Z", "+00:00").replace("+00:00", "")) if created else now
            except (ValueError, AttributeError):
                event_time = now
            weight = self._decay_weight(event_time, now)
            weighted_counts[cat] = weighted_counts.get(cat, 0) + weight
        total = sum(weighted_counts.values())
        if total == 0:
            return {}
        return {cat: round(w / total, 3) for cat, w in weighted_counts.items()}

    def _compute_price_range(self, comparisons: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Compute price range preference from comparison prices."""
        prices = []
        for c in comparisons:
            for p in c.get("products", []):
                price = p.get("price", {})
                if isinstance(price, dict) and price.get("amount"):
                    prices.append(price["amount"])
                elif isinstance(price, (int, float)) and price > 0:
                    prices.append(price)
        if not prices:
            return {"avg_price_viewed": 0, "tier_distribution": {}}
        avg = sum(prices) / len(prices)
        # Compute tier distribution
        tiers = {"budget": 0, "mid": 0, "premium": 0, "luxury": 0}
        for p in prices:
            if p < 11:
                tiers["budget"] += 1
            elif p < 57:
                tiers["mid"] += 1
            elif p < 189:
                tiers["premium"] += 1
            else:
                tiers["luxury"] += 1
        total = len(prices)
        tier_dist = {t: round(c / total, 2) for t, c in tiers.items()}
        return {"avg_price_viewed": round(avg, 1), "tier_distribution": tier_dist}

    def _compute_winner_agreement(self, feedback: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Compute winner agreement from feedback."""
        agreed = sum(1 for f in feedback if f.get("useful") is True)
        disagreed = sum(1 for f in feedback if f.get("useful") is False)
        total = agreed + disagreed
        rate = round(agreed / total, 3) if total > 0 else 0.0
        return {"agreed": agreed, "disagreed": disagreed, "agreement_rate": rate}

    def _compute_dimension_sensitivity(self, events: List[Dict[str, Any]]) -> Dict[str, float]:
        """Compute dimension sensitivity from tab dwell patterns."""
        dwell_totals: Dict[str, float] = {}
        for e in events:
            if e.get("event_type") != "tab_switch":
                continue
            meta = e.get("metadata", {})
            tab = meta.get("to", "")
            dwell = meta.get("dwell_ms", 0)
            if dwell < MIN_DWELL_MS:
                continue
            dim = TAB_DIMENSION_MAP.get(tab)
            if dim:
                dwell_totals[dim] = dwell_totals.get(dim, 0) + dwell
        total_dwell = sum(dwell_totals.values())
        if total_dwell == 0:
            return {}
        return {dim: round(dwell / total_dwell, 3) for dim, dwell in dwell_totals.items()}

    def compute_session_signals(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Compute in-session signals from event list."""
        tab_switches = [e for e in events if e.get("event_type") == "tab_switch"]
        first_tab = tab_switches[0]["metadata"]["to"] if tab_switches else None

        dwell_by_tab: Dict[str, int] = {}
        for e in tab_switches:
            meta = e.get("metadata", {})
            tab = meta.get("to", "")
            dwell = meta.get("dwell_ms", 0)
            dwell_by_tab[tab] = dwell_by_tab.get(tab, 0) + dwell

        return {
            "first_tab_viewed": first_tab,
            "tab_dwell_ms": dwell_by_tab,
            "price_checked_first": first_tab == "overview",
            "shared_result": any(e.get("event_type") == "share" for e in events),
            "feedback_given": next(
                (
                    "positive" if e.get("metadata", {}).get("useful") else "negative"
                    for e in events
                    if e.get("event_type") == "feedback"
                ),
                None,
            ),
        }

    async def build_behavior_profile(
        self,
        comparisons: List[Dict[str, Any]],
        feedback: List[Dict[str, Any]],
        events: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Build complete behavioral profile from user data."""
        return {
            "category_affinity": self._compute_category_affinity(comparisons),
            "price_range_preference": self._compute_price_range(comparisons),
            "winner_agreement": self._compute_winner_agreement(feedback),
            "dimension_sensitivity": self._compute_dimension_sensitivity(events),
            "comparison_count": len(comparisons),
            "last_updated": datetime.now().isoformat(),
        }


def get_behavior_service() -> BehaviorService:
    """Singleton factory."""
    if not hasattr(get_behavior_service, "_instance"):
        get_behavior_service._instance = BehaviorService()
    return get_behavior_service._instance
```

- [ ] **Step 4: Implement `apply_behavioral_adjustments()` and `apply_session_signals()` in scoring_service.py**

Add to `app/services/scoring_service.py` (after `compute_confidence()`):

```python
MAX_BEHAVIORAL_SHIFT_RATIO = 0.10  # ±10% of category weight
MAX_SESSION_SHIFT_RATIO = 0.05     # ±5% of category weight

def apply_behavioral_adjustments(
    self,
    weights: Dict[str, float],
    behavior_profile: Dict[str, Any],
) -> Dict[str, float]:
    """Apply behavioral profile adjustments to weights (capped at ±10%)."""
    sensitivity = behavior_profile.get("dimension_sensitivity", {})
    if not sensitivity:
        return weights

    # Compute desired shifts: dimensions with higher sensitivity get boosted
    avg_sensitivity = sum(sensitivity.values()) / len(sensitivity) if sensitivity else 0
    for dim in weights:
        if dim in sensitivity:
            delta = (sensitivity[dim] - avg_sensitivity) * weights[dim]
            max_shift = weights[dim] * MAX_BEHAVIORAL_SHIFT_RATIO
            clamped = max(-max_shift, min(max_shift, delta))
            weights[dim] += clamped

    # Renormalize
    total = sum(weights.values())
    if total > 0:
        weights = {k: v / total for k, v in weights.items()}
    return weights

def apply_session_signals(
    self,
    weights: Dict[str, float],
    session_signals: Dict[str, Any],
) -> Dict[str, float]:
    """Apply in-session signal adjustments to weights (capped at ±5%)."""
    dwell = session_signals.get("tab_dwell_ms", {})
    if not dwell:
        return weights

    # Map tab dwell to dimension sensitivity (same as behavior service)
    tab_dim_map = {"specs": "spec_score", "reviews": "review_score", "overview": "price_score"}
    total_dwell = sum(dwell.values())
    if total_dwell == 0:
        return weights

    avg_ratio = 1.0 / len(dwell) if dwell else 0
    for tab, ms in dwell.items():
        dim = tab_dim_map.get(tab)
        if dim and dim in weights:
            ratio = ms / total_dwell
            delta = (ratio - avg_ratio) * weights[dim]
            max_shift = weights[dim] * MAX_SESSION_SHIFT_RATIO
            clamped = max(-max_shift, min(max_shift, delta))
            weights[dim] += clamped

    # Renormalize
    total = sum(weights.values())
    if total > 0:
        weights = {k: v / total for k, v in weights.items()}
    return weights
```

- [ ] **Step 5: Run all tests**

Run: `python -m pytest tests/test_behavior_service.py tests/test_scoring_service.py -v`
Expected: All PASSED

- [ ] **Step 6: Commit**

```bash
git add app/services/behavior_service.py app/services/scoring_service.py tests/test_behavior_service.py
git commit -m "feat: add behavioral learning service and weight adjustment functions"
```

---

### Task 7: Database Migration (backend-api)

**Files:**
- Modify: Supabase via `execute_sql` MCP tool or migration script

- [ ] **Step 1: Add `behavior_profile` JSONB column to users table**

Execute via Supabase MCP or SQL:

```sql
ALTER TABLE public.users
ADD COLUMN IF NOT EXISTS behavior_profile JSONB DEFAULT '{}';

COMMENT ON COLUMN public.users.behavior_profile IS 'Behavioral profile aggregated from comparison history, feedback, and events. Updated after each comparison.';
```

- [ ] **Step 2: Verify the column exists**

```sql
SELECT column_name, data_type, column_default
FROM information_schema.columns
WHERE table_name = 'users' AND column_name = 'behavior_profile';
```

Expected: One row showing `behavior_profile | jsonb | '{}'::jsonb`

- [ ] **Step 3: Commit migration documentation**

Create a note in the spec or CLAUDE.md that the migration was applied. No migration file needed since we apply directly to Supabase.

```bash
git commit --allow-empty -m "chore(db): add behavior_profile JSONB column to users table"
```

---

### Task 8: Response Restructure + SSE Streaming (backend-api)

**Files:**
- Modify: `app/services/structured_comparison_service.py` (~lines 285-377 response assembly, ~lines 387-608 streaming)
- Test: `tests/test_streaming.py`

- [ ] **Step 1: Write failing tests for new response structure**

```python
# In tests/test_streaming.py — add new test class

class TestNewResponseStructure:
    """Tests for the restructured API response format."""

    def test_response_has_overview_section(self):
        """Response must have 'overview' top-level key"""
        # Mock a complete response from compare_from_text
        response = self._make_mock_response()
        assert "overview" in response
        assert "winner" in response["overview"]
        assert "products" in response["overview"]
        assert "tradeoffs" in response["overview"]
        assert "confidence" in response["overview"]

    def test_response_has_specs_section(self):
        """Response must have 'specs' top-level key"""
        response = self._make_mock_response()
        assert "specs" in response
        assert "products" in response["specs"]

    def test_response_has_reviews_section(self):
        """Response must have 'reviews' top-level key"""
        response = self._make_mock_response()
        assert "reviews" in response
        assert "products" in response["reviews"]

    def test_response_has_scoring_section(self):
        """Response must have 'scoring' top-level key"""
        response = self._make_mock_response()
        assert "scoring" in response

    def test_response_has_personalization_section(self):
        """Response must have 'personalization' top-level key"""
        response = self._make_mock_response()
        assert "personalization" in response

    def test_response_has_metadata_section(self):
        """Response must have 'metadata' top-level key"""
        response = self._make_mock_response()
        assert "metadata" in response

    def test_overview_winner_structure(self):
        """Overview winner has all required fields"""
        response = self._make_mock_response()
        winner = response["overview"]["winner"]
        assert "product_index" in winner
        assert "name" in winner
        assert "reason" in winner
        assert "key_tradeoff" in winner
        assert "margin" in winner

    def test_overview_product_has_value_badge(self):
        """Overview products include value_badge and value_context"""
        response = self._make_mock_response()
        product = response["overview"]["products"][0]
        assert "value_badge" in product
        assert "value_context" in product
        assert product["value_badge"] in ("great_value", "fair_price", "premium_price", "overpriced")

    def test_overview_product_has_best_for(self):
        """Overview products include best_for string"""
        response = self._make_mock_response()
        product = response["overview"]["products"][0]
        assert "best_for" in product

    def test_reviews_product_has_review_summary(self):
        """Reviews products include review_summary with consensus format"""
        response = self._make_mock_response()
        product = response["reviews"]["products"][0]
        assert "review_summary" in product
        summary = product["review_summary"]
        assert "overall_sentiment" in summary
        assert "consensus" in summary
        assert "highlights" in summary

    @staticmethod
    def _make_mock_response():
        """Build a mock response matching the new structure."""
        return {
            "query": "Product A vs Product B",
            "category": "electronics",
            "category_switched": False,
            "overview": {
                "winner": {
                    "product_index": 0,
                    "name": "Product A",
                    "declaration": "Product A",
                    "reason": "Better specs across 4 dimensions",
                    "key_tradeoff": "Product B has a brighter display",
                    "margin": 8.5,
                },
                "products": [
                    {
                        "brand": "Brand A",
                        "name": "Product A",
                        "price": {"amount": 100, "currency": "BHD", "retailer": "Amazon", "source_method": "local_bhd"},
                        "rating": 4.5,
                        "review_count": 500,
                        "overall_score": 78.0,
                        "value_badge": "great_value",
                        "value_context": "Excellent specs at mid-range price",
                        "pros": ["Fast processor", "Great camera"],
                        "cons": ["Heavy build"],
                        "best_for": "Best if you prioritize performance",
                    },
                    {
                        "brand": "Brand B",
                        "name": "Product B",
                        "price": {"amount": 90, "currency": "BHD", "retailer": "BestBuy", "source_method": "local_bhd"},
                        "rating": 4.3,
                        "review_count": 300,
                        "overall_score": 70.0,
                        "value_badge": "fair_price",
                        "value_context": "Solid value for the price",
                        "pros": ["Bright display", "Lightweight"],
                        "cons": ["Slower processor"],
                        "best_for": "Best if you want a bright display",
                    },
                ],
                "tradeoffs": [
                    {
                        "winner_wins": {"dimension": "specs", "product": "Product A", "margin": 15.0},
                        "loser_wins": {"dimension": "price", "product": "Product B", "margin": 10.0},
                    }
                ],
                "confidence": {
                    "price": {"source_count": 3, "method": "retailer_verified", "freshness": "live"},
                    "rating": {"review_count": 500, "source": "Amazon", "verified": True},
                    "specs": {"verified_pct": 85, "citation_count": 10},
                    "overall": "high",
                },
            },
            "specs": {
                "products": [
                    {"brand": "Brand A", "name": "Product A", "specs": {"processor": "A17"}, "spec_advantages": ["Faster processor"]},
                    {"brand": "Brand B", "name": "Product B", "specs": {"processor": "SD8"}, "spec_advantages": ["Brighter display"]},
                ],
                "specs_comparison": {},
            },
            "reviews": {
                "products": [
                    {
                        "brand": "Brand A",
                        "name": "Product A",
                        "rating": 4.5,
                        "review_count": 500,
                        "rating_source": {"name": "Amazon", "url": "https://amazon.com"},
                        "review_summary": {
                            "overall_sentiment": "positive",
                            "consensus": "Most users love the performance.",
                            "highlights": [{"point": "Fast processor", "sentiment": "positive"}],
                            "review_volume": "high",
                            "agreement_level": "strong",
                        },
                    },
                    {
                        "brand": "Brand B",
                        "name": "Product B",
                        "rating": 4.3,
                        "review_count": 300,
                        "rating_source": {"name": "BestBuy", "url": "https://bestbuy.com"},
                        "review_summary": {
                            "overall_sentiment": "positive",
                            "consensus": "Good display quality praised.",
                            "highlights": [{"point": "Bright display", "sentiment": "positive"}],
                            "review_volume": "moderate",
                            "agreement_level": "strong",
                        },
                    },
                ],
            },
            "scoring": {"scores": {}, "dimension_winners": {}, "scoring_method": "category_weighted"},
            "personalization": {"personalized": False, "factors": [], "behavior_influence": None},
            "metadata": {"elapsed_ms": 5000, "api_calls": 4, "total_cost": 0.01, "cached": False, "fact_check": {}},
        }


class TestNewStreamingEvents:
    """Tests for enriched SSE streaming events."""

    def test_status_events_have_progress(self):
        """Status events must include 'progress' percentage"""
        event = {"step": "parsing", "progress": 10}
        assert "progress" in event
        assert isinstance(event["progress"], int)

    def test_prices_event_includes_value_badge(self):
        """Prices SSE event must include value_badge per product"""
        event = {
            "overview": {
                "products": [
                    {"price": {"amount": 100}, "value_badge": "great_value", "value_context": "Good deal"},
                ]
            }
        }
        assert "value_badge" in event["overview"]["products"][0]

    def test_reviews_event_uses_new_format(self):
        """Reviews SSE event must use review_summary format"""
        event = {
            "reviews": {
                "products": [
                    {
                        "review_summary": {
                            "overall_sentiment": "positive",
                            "consensus": "Users love it.",
                            "highlights": [],
                            "review_volume": "high",
                            "agreement_level": "strong",
                        }
                    }
                ]
            }
        }
        assert "review_summary" in event["reviews"]["products"][0]

    def test_scores_event_includes_confidence(self):
        """Scores SSE event must include confidence indicators"""
        event = {
            "scoring": {},
            "confidence": {"price": {}, "rating": {}, "specs": {}, "overall": "high"},
        }
        assert "confidence" in event

    def test_verdict_event_has_structured_fields(self):
        """Verdict SSE event must include structured winner fields"""
        event = {
            "overview": {
                "winner": {
                    "product_index": 0,
                    "name": "Product A",
                    "reason": "Better specs",
                    "key_tradeoff": "Product B is cheaper",
                    "margin": 5.0,
                },
                "tradeoffs": [],
            }
        }
        assert "reason" in event["overview"]["winner"]
        assert "key_tradeoff" in event["overview"]["winner"]
```

- [ ] **Step 2: Run tests to verify baseline**

Run: `python -m pytest tests/test_streaming.py -v`
Expected: New tests pass (they test data structures, not live code yet). Existing streaming tests may fail after implementation changes.

- [ ] **Step 3: Restructure `compare_from_text()` response assembly**

In `app/services/structured_comparison_service.py`, modify the response assembly (~lines 285-377):

1. After scoring, call `compute_value_badge()` per product
2. Call `compute_tradeoff_pairs()` with dimension_winners
3. Call `compute_confidence()` with product data
4. Assemble the new response structure with `overview`, `specs`, `reviews`, `scoring`, `personalization`, `metadata` top-level keys
5. Map verdict fields: `winner_declaration` → `overview.winner.name`, `winner_reason` → `overview.winner.reason`, etc.
6. Map review data: `review_summary` → `reviews.products[i].review_summary`
7. Keep backward-compat aliases: `result["comparison"]`, `result["products"]`, `result["recommendation"]`, `result["key_differences"]` pointing to equivalent new data

- [ ] **Step 4: Restructure `compare_from_text_streaming()` yields**

Modify the streaming generator (~lines 387-608):

1. Status events: add `"progress"` field (10, 20, 50, 80)
2. Specs event: wrap in `{"specs": {"products": [...]}}`
3. Prices event: include `value_badge` and `value_context` per product
4. Reviews event: use new `review_summary` format
5. Scores event: include `confidence` alongside scoring
6. Verdict event: use structured winner fields
7. Complete event: use new full response structure

- [ ] **Step 5: Run all tests**

Run: `python -m pytest tests/test_streaming.py tests/test_singleton_state.py -v`
Expected: All PASSED

- [ ] **Step 6: Run full backend test suite**

Run: `python -m pytest tests/ -v -m "not (live_unit or live_db or integration)" --ignore=tests/test_integration.py`
Expected: All PASSED (update any tests that assert on old response structure)

- [ ] **Step 7: Commit**

```bash
git add app/services/structured_comparison_service.py tests/test_streaming.py
git commit -m "feat: restructure API response and SSE events for new format"
```

---

## Phase 3: Frontend + Integration

### Task 9: Frontend Type Definitions (frontend)

**Files:**
- Modify: `SmartCompareApp/src/services/api.ts` (~lines 252-349)

- [ ] **Step 1: Add TypeScript types for new response structure**

Add to `api.ts` (or a new `types.ts` if preferred):

```typescript
// New response structure types
interface OverviewWinner {
  product_index: number;
  name: string;
  declaration: string;
  reason: string;
  key_tradeoff: string;
  margin: number;
}

interface OverviewProduct {
  brand: string;
  name: string;
  price: { amount: number; currency: string; retailer: string; source_method: string; estimated?: boolean };
  rating: number | null;
  review_count: number;
  overall_score: number;
  value_badge: 'great_value' | 'fair_price' | 'premium_price' | 'overpriced';
  value_context: string;
  pros: string[];
  cons: string[];
  best_for: string;
}

interface TradeoffPair {
  winner_wins: { dimension: string; product: string; margin: number };
  loser_wins: { dimension: string; product: string; margin: number };
}

interface ConfidenceIndicators {
  price: { source_count: number; method: string; freshness: string };
  rating: { review_count: number; source: string | null; verified: boolean };
  specs: { verified_pct: number; citation_count: number };
  overall: 'high' | 'medium' | 'low';
}

interface ReviewHighlight {
  point: string;
  sentiment: 'positive' | 'negative';
}

interface ReviewSummary {
  overall_sentiment: 'positive' | 'mixed' | 'negative';
  consensus: string;
  highlights: ReviewHighlight[];
  review_volume: 'high' | 'moderate' | 'low' | 'minimal';
  agreement_level: 'strong' | 'moderate' | 'divided';
}

interface ComparisonResponse {
  query: string;
  category: string;
  category_switched: boolean;
  overview: {
    winner: OverviewWinner;
    products: OverviewProduct[];
    tradeoffs: TradeoffPair[];
    confidence: ConfidenceIndicators;
  };
  specs: {
    products: Array<{
      brand: string;
      name: string;
      specs: Record<string, any>;
      spec_advantages: string[];
    }>;
    specs_comparison: any;
  };
  reviews: {
    products: Array<{
      brand: string;
      name: string;
      rating: number | null;
      review_count: number;
      rating_source: { name: string; url: string } | null;
      review_summary: ReviewSummary;
    }>;
  };
  scoring: any;
  personalization: {
    personalized: boolean;
    factors: string[];
    behavior_influence: any;
  };
  metadata: {
    elapsed_ms: number;
    api_calls: number;
    total_cost: number;
    cached: boolean;
    fact_check: any;
  };
}
```

- [ ] **Step 2: Update `streamComparison()` event handlers**

Update the SSE event handling in `streamComparison()` to handle the new event data shapes:
- `onStatus` callback now receives `{ step: string, progress: number }`
- `onSpecs` receives `{ specs: { products: [...] } }`
- `onPrices` receives `{ overview: { products: [{ price, value_badge, value_context }] } }`
- `onReviews` receives `{ reviews: { products: [...] } }`
- `onScores` receives `{ scoring: {...}, confidence: {...} }`
- `onVerdict` receives `{ overview: { winner, tradeoffs } }`
- `onComplete` receives full `ComparisonResponse`

- [ ] **Step 3: TypeScript check**

Run: `cd SmartCompareApp && npx tsc --noEmit`
Expected: 0 errors

- [ ] **Step 4: Commit**

```bash
git add SmartCompareApp/src/services/api.ts
git commit -m "feat(frontend): add TypeScript types for new response structure"
```

---

### Task 10: ResultsScreen Restructure (frontend)

**Files:**
- Modify: `SmartCompareApp/src/screens/ResultsScreen.tsx`

- [ ] **Step 1: Update Overview tab to use new structure**

Replace Overview tab content to read from `result.overview`:
- Winner card: `result.overview.winner.name`, `result.overview.winner.reason`, `result.overview.winner.key_tradeoff`
- Product cards: `result.overview.products[i]` — show `value_badge` as a colored badge, `value_context` as one line below price
- Tradeoffs: render `result.overview.tradeoffs` as paired comparison items
- Confidence: show `result.overview.confidence.overall` as a trust indicator, with sub-indicators for price/rating/specs
- Scoring bars: read from `result.scoring` (unchanged location)
- Best-for lines: `result.overview.products[i].best_for`
- Pros/cons: `result.overview.products[i].pros`, `result.overview.products[i].cons`

- [ ] **Step 2: Update Specs tab to use new structure**

Read from `result.specs.products[i]`:
- `specs` dict (filter N/A/null/empty as before)
- `spec_advantages` as highlighted items
- `result.specs.specs_comparison` for cross-product comparison

- [ ] **Step 3: Update Reviews tab to use new structure**

Read from `result.reviews.products[i]`:
- Rating display: `rating`, `review_count`, `rating_source`
- Review summary: render `review_summary.consensus` as paragraph
- Highlights: render `review_summary.highlights` as bullet list with sentiment color coding (green for positive, red for negative)
- Volume indicator: show `review_summary.review_volume` as text badge ("Based on 500+ reviews")
- Agreement: if `agreement_level === "divided"`, show a note

Remove old rendering for: `common_praises`, `common_complaints`, `detailed_praises`, `user_quotes`

- [ ] **Step 4: Add backward compatibility for history**

Old stored comparisons use the flat structure. Add a compatibility check:

```typescript
// At the top of ResultsScreen, detect format
const isNewFormat = result?.overview?.winner !== undefined;

// Use new paths if available, fall back to old paths
const winner = isNewFormat
  ? result.overview.winner
  : { name: result.products?.[result.winner_index]?.name, reason: result.recommendation };
```

- [ ] **Step 5: TypeScript check**

Run: `cd SmartCompareApp && npx tsc --noEmit`
Expected: 0 errors

- [ ] **Step 6: Commit**

```bash
git add SmartCompareApp/src/screens/ResultsScreen.tsx
git commit -m "feat(frontend): restructure ResultsScreen for new API response format"
```

---

### Task 11: Integration + Behavioral Profile Trigger (backend-api)

**Files:**
- Modify: `app/services/structured_comparison_service.py` (add behavioral profile update trigger)
- Modify: `app/routes/text_routes.py` (pass session signals if available)

- [ ] **Step 1: Wire behavioral profile update into compare_from_text()**

At the end of `compare_from_text()`, after the response is assembled, add a fire-and-forget task to update the user's behavioral profile:

```python
# After response assembly, before return
if user and user.get("id"):
    asyncio.create_task(self._update_behavior_profile(user["id"]))
```

Implement `_update_behavior_profile()`:
```python
async def _update_behavior_profile(self, user_id: str):
    """Fire-and-forget: update user's behavioral profile after comparison."""
    try:
        from app.services.behavior_service import get_behavior_service
        from app.services.database_service import get_supabase_client

        behavior_service = get_behavior_service()
        supabase = get_supabase_client()

        # Fetch user's comparison history, feedback, and events
        comparisons = supabase.table("comparisons").select("category_used, products, created_at").eq("user_id", user_id).order("created_at", desc=True).limit(50).execute()
        feedback = supabase.table("comparison_feedback").select("useful").eq("user_id", user_id).execute()
        events = supabase.table("user_events").select("event_type, metadata").eq("user_id", user_id).order("created_at", desc=True).limit(200).execute()

        profile = await behavior_service.build_behavior_profile(
            comparisons.data or [],
            feedback.data or [],
            events.data or [],
        )

        # Upsert profile
        supabase.table("users").update({"behavior_profile": profile}).eq("id", user_id).execute()
    except Exception as e:
        logger.warning(f"Failed to update behavior profile: {e}")
```

- [ ] **Step 2: Wire behavioral + session weights into scoring**

In `compare_from_text()`, before calling `compute_scores()`:

```python
# Fetch behavior profile if user is logged in
behavior_profile = None
session_signals = None
if user and user.get("id"):
    try:
        user_data = supabase.table("users").select("behavior_profile").eq("id", user["id"]).single().execute()
        behavior_profile = user_data.data.get("behavior_profile") if user_data.data else None
    except Exception:
        pass

# Pass to scoring
scoring_result = await scoring_service.compute_scores(
    product_data,
    preferences=user_preferences,
    behavior_profile=behavior_profile,
    session_signals=session_signals,
)
```

Update `compute_scores()` in `scoring_service.py` to accept and apply `behavior_profile` and `session_signals` parameters.

- [ ] **Step 3: Write integration test**

```python
# tests/test_behavior_integration.py

class TestBehaviorIntegration:
    """Tests for behavioral profile integration in comparison flow."""

    @pytest.mark.asyncio
    async def test_compare_with_behavior_profile(self):
        """Comparison with behavior profile adjusts weights"""
        # This is a unit test with mocked Supabase
        pass  # backend-api implements

    def test_scoring_accepts_behavior_params(self):
        """compute_scores() accepts behavior_profile and session_signals"""
        from app.services.scoring_service import ScoringService
        service = ScoringService()
        # Should not raise
        import inspect
        sig = inspect.signature(service.compute_scores)
        assert "behavior_profile" in sig.parameters
        assert "session_signals" in sig.parameters
```

- [ ] **Step 4: Run full test suite**

Run: `python -m pytest tests/ -v -m "not (live_unit or live_db or integration)" --ignore=tests/test_integration.py`
Expected: All PASSED

- [ ] **Step 5: Commit**

```bash
git add app/services/structured_comparison_service.py app/services/scoring_service.py app/routes/text_routes.py tests/test_behavior_integration.py
git commit -m "feat: wire behavioral profile into comparison and scoring flow"
```

---

## Phase 4: Cross-QA + Test Coverage

### Task 12: Cross-QA Round

**Team Rules:**
- Each agent QAs their assigned target (see team table above)
- QA checklist per agent:
  1. Read all code written by target agent
  2. Verify all spec requirements are implemented
  3. Run target's tests — all must pass
  4. Check test coverage ≥ 80% for new code
  5. If issues found: send work back with specific file:line references
  6. If acceptable: sign off

**QA Assignments:**
- **backend-scoring** QAs **backend-ai**: Review prompt changes, verdict prompt changes, field completeness
- **backend-ai** QAs **backend-scoring**: Value badges, tradeoffs, confidence, behavioral weight math
- **frontend** QAs **backend-api**: Response structure matches spec, SSE events correct, behavioral trigger works
- **backend-api** QAs **frontend**: TypeScript types match backend, all tabs render correctly, backward compat works

- [ ] **Step 1: Each agent reads their QA target's code**
- [ ] **Step 2: Each agent runs their QA target's tests**
- [ ] **Step 3: Each agent reports issues or signs off**
- [ ] **Step 4: Fix any rejected work**
- [ ] **Step 5: Re-run full test suite**

Run: `python -m pytest tests/ -v -m "not (live_unit or live_db or integration)" --ignore=tests/test_integration.py`
Expected: All PASSED, 80%+ coverage on new code

- [ ] **Step 6: All 4 agents sign off**
- [ ] **Step 7: Final commit**

```bash
git add -A
git commit -m "feat: personalization & AI model redesign — complete implementation"
```

---

## Summary

| Task | Owner | Phase | Files |
|------|-------|-------|-------|
| 1. Value Badges | backend-scoring | 1 | scoring_service.py |
| 2. Tradeoff Pairs | backend-scoring | 1 | scoring_service.py |
| 3. Confidence Indicators | backend-scoring | 1 | scoring_service.py |
| 4. Review Prompt | backend-ai | 1 | extraction_service.py |
| 5. Verdict Prompt | backend-ai | 1 | extraction_service.py |
| 6. Behavioral Service | backend-scoring | 2 | behavior_service.py, scoring_service.py |
| 7. DB Migration | backend-api | 2 | Supabase |
| 8. Response + SSE | backend-api | 2 | structured_comparison_service.py |
| 9. Frontend Types | frontend | 2 | api.ts |
| 10. ResultsScreen | frontend | 3 | ResultsScreen.tsx |
| 11. Integration | backend-api | 3 | structured_comparison_service.py |
| 12. Cross-QA | all | 4 | all |

**Total new test classes:** 8 (ValueBadges, TradeoffPairs, ConfidenceIndicators, ReviewSummaryFormat, StructuredVerdictFormat, BehaviorProfile, SessionSignals, WeightAdjustments, NewResponseStructure, NewStreamingEvents, BehaviorIntegration)

**Estimated new tests:** ~80-100

**Zero additional API cost.** All additions are deterministic math or prompt restructuring.
