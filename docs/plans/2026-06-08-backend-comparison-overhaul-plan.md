# Backend Comparison Engine Overhaul — Implementation Plan (Sprint A)

> **For Claude:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task.

**Goal:** Ship Sprint (A) "Wiring + Quality" — wire the category-aware data that's already computed into the mobile-facing response shape, rebuild the tier-cascade as a confidence-driven parallel multi-source race, add Bahrain-first source prioritisation, introduce 25 per-product-type spec schemas, instrument the frontend 88s gap, and prove correctness via a 50-query Bahrain validation merge gate.

**Architecture:** Four parallel Opus lanes operating in dedicated worktrees branching off `main`. Each lane is end-to-end TDD with red-green tests targeting 80% coverage. Lanes merge via dispatcher only after mandatory peer cross-QA. Single `--no-ff` merge to `main` after the 50-query validation gate passes; one EAS update to `preview` channel, then production after a device walk.

**Tech Stack:** Python 3.12 + FastAPI (backend), React Native + Expo SDK (mobile), Supabase Postgres, Upstash Redis, OpenAI gpt-4o + gpt-4o-mini, Serper, Firecrawl, Scrape.do, curl_cffi, pytest, Jest, EAS Update.

**Design source:** `docs/plans/2026-06-08-backend-comparison-overhaul-design.md` (commit `441d85f`).

---

## Pre-flight — Dispatcher checklist (Day 0)

### Task P1: Verify circuit-breaker + budget state in Railway Redis

**Files:** none (read-only)

**Step 1:** Run `mcp__railway__list_variables` (service_id `7ab6a780-e4df-4f72-97c2-b95992b96312`) to confirm Firecrawl/Scrape.do/Serper API keys are set.

**Step 2:** Curl `/admin/costs` with `X-Admin-Key: 9JE8mrED4TwH5U6qLBmvf-n214_Ch3LoBGboFbX62L4` to inspect: `firecrawl_lifetime_used`, `scrapedo_monthly_used`, `serper_monthly_used`, circuit breaker open/closed state per provider.

**Step 3:** Record findings in dispatcher session notes (so Lane 2 starts with known good state).

**Expected:** Firecrawl <450 lifetime used; Scrape.do <900 monthly used; Serper <2200 monthly used; circuits ALL CLOSED. If any circuit is OPEN, run Redis `DEL circuit:firecrawl` / `DEL circuit:scrapedo` via Upstash console BEFORE Lane 2 starts.

### Task P2: Flip Railway escalation flags

**Files:** Railway env vars (no repo change)

**Step 1:** Set via Railway dashboard or `mcp__railway__list_variables` + manual edit:
- `ENABLE_FIRECRAWL=true`
- `ENABLE_SCRAPEDO=true`
- `ENABLE_PAGE_SCRAPE=true`
- `SCRAPING_MODE=hard` (default; revisit after Lane 2 introduces confidence-driven escalation)
- `DEBUG_STAGE_TIMINGS=true` (temporary for the sprint; flip back after Lane 4 closes)

**Step 2:** Trigger Railway redeploy and verify `/health` returns 200.

**Step 3:** Re-run the 3 baseline curls (electronics / fragrances / supplements) and store JSON outputs at `docs/plans/2026-06-08-baseline-curls/` for comparison vs post-merge.

### Task P3: Worktree setup for 4 Opus lanes

**Files:** filesystem only

**Step 1:** From `C:/Users/SynAckITPC/Documents/ai/smartcompare`:

```bash
git worktree add -b feature/A-L1-v2-adapter      ../smartcompare-A-L1 main
git worktree add -b feature/A-L2-parallel-races  ../smartcompare-A-L2 main
git worktree add -b feature/A-L3-mobile-renders  ../smartcompare-A-L3 main
git worktree add -b feature/A-L4-prompts-eval    ../smartcompare-A-L4 main
git worktree list
```

**Step 2:** Verify 4 absolute paths exist as siblings of repo root (per `memory/feedback_worktree_path_resolution.md`).

**Step 3:** Spawn 4-Opus TeamCreate with `mode: "bypassPermissions"` (required for Bash inside worktree subagents). Owners: `L1-be-v2`, `L2-be-races`, `L3-fe-mobile`, `L4-prompts-eval`.

### Task P4: Publish task matrix + Team Execution Contract

**Files:** none (in-session contract)

**Step 1:** Dispatcher sends to each lane owner (individual SendMessage, NOT broadcast — per `memory/feedback_teamcreate_no_structured_broadcast.md`):
- Lane goal + worktree path
- File ownership (no shared files except `docs/plans/`)
- Cross-QA assignment matrix:
  - L1 owner QAs L2's `_compute_data_confidence` + `_build_escalation_scrapers`
  - L2 owner QAs L3's mobile v2 wiring
  - L3 owner QAs L4's prompt-builder integration
  - L4 owner QAs L1's `build_dimensions_v2` rewrite
- Reminder of binding rules: 100% completion before disassembly, idle = red-green tests OR wait, no scope deferral without dispatcher approval, fetch + inspect before any destructive ruling.

---

## Lane 1 — Backend v2 Adapter (Opus #1, ~3 days)

**Goal:** Wire the category-aware data that's already computed into the v2 response shape so mobile renders all design Screens 1–4.

**Worktree:** `../smartcompare-A-L1` on `feature/A-L1-v2-adapter`

**Files affected:**
- Modify: `app/services/scoring_service.py:2006-2050` (`build_dimensions_v2`)
- Modify: `app/services/response_builder.py:353-396` (`_build_factual_verdict`)
- Modify: `app/services/response_builder.py:398-470` (`_build_scoring_v2`)
- Modify: `app/services/response_builder.py:600-700` (overview product block — variant, pros_cons flatten)
- Create: `tests/test_scoring_v2_category_dimensions.py`
- Create: `tests/test_response_builder_factual_verdict.py`
- Create: `tests/test_overview_variant_pros_cons.py`

### Task L1.1: Reproduce the v2 NULL-emission bug as a failing test

**Files:**
- Create: `tests/test_scoring_v2_category_dimensions.py`

**Step 1:** Write the failing test:

```python
import json
import pytest
from app.services.response_builder import _build_scoring_v2

ELECTRONICS_FIXTURE = json.load(open("tests/fixtures/iphone15_vs_galaxys24_product_data.json"))
ELECTRONICS_SCORING_RESULT = json.load(open("tests/fixtures/iphone15_vs_galaxys24_scoring_result.json"))

def test_scoring_v2_emits_category_dimensions_not_generic_dims():
    """v2.dimensions MUST reflect CATEGORY_DIMENSIONS[electronics] (performance,
    value, build_quality, feature, ecosystem, futureproof), NOT the hand-coded
    generic ['price','reviews','value','popularity']."""
    v2 = _build_scoring_v2(
        ELECTRONICS_FIXTURE,
        ELECTRONICS_SCORING_RESULT,
        category_used="electronics",
        winner_index=1,
    )
    dim_keys = [d["key"] for d in v2["dimensions"]]
    assert "performance" in dim_keys
    assert "build_quality" in dim_keys
    assert "feature" in dim_keys
    assert "ecosystem" in dim_keys
    assert "futureproof" in dim_keys
    # And NOT the legacy generics:
    assert "popularity" not in dim_keys, "v2 still emitting generic 'popularity' dim"

def test_scoring_v2_dim_winners_populated_not_null():
    """Every dim must have winner: 0|1|'tie', NOT None."""
    v2 = _build_scoring_v2(
        ELECTRONICS_FIXTURE,
        ELECTRONICS_SCORING_RESULT,
        category_used="electronics",
        winner_index=1,
    )
    for dim in v2["dimensions"]:
        assert dim["winner"] is not None, f"dim {dim['key']} winner is None"
        assert dim["winner"] in (0, 1, "tie")
```

**Step 2:** Run test:

```bash
cd ../smartcompare-A-L1
python -m pytest tests/test_scoring_v2_category_dimensions.py -v
```

Expected: FAIL — first test asserts `"performance" in dim_keys` but production emits `['price','reviews','value','popularity']`; second test asserts winners are populated but they emit None.

**Step 3:** Commit the failing test:

```bash
git add tests/fixtures/iphone15_vs_galaxys24_*.json tests/test_scoring_v2_category_dimensions.py
git commit -- tests/ -m "test(L1): failing red — v2.dimensions must use CATEGORY_DIMENSIONS"
```

### Task L1.2: Create test fixtures from real production responses

**Files:**
- Create: `tests/fixtures/iphone15_vs_galaxys24_product_data.json`
- Create: `tests/fixtures/iphone15_vs_galaxys24_scoring_result.json`
- Create: `tests/fixtures/tomford_vs_creed_product_data.json`
- Create: `tests/fixtures/now_vs_solgar_product_data.json`

**Step 1:** Use the production JSON dumps at `C:/Users/SynAckITPC/AppData/Local/Temp/cmp_elec.json` (etc.) to extract the `product_data` shape passed into `_build_scoring_v2`.

**Step 2:** Add a Python helper script `scripts/extract_test_fixtures.py` that runs `/api/v1/text/compare?q=...&nocache=true` and dumps the intermediate `product_data` + `scoring_result` (intercepted via temporary logging hook in `response_builder.py`). Run for 3 categories.

**Step 3:** Save fixtures to `tests/fixtures/`. Commit:

```bash
git add tests/fixtures/ scripts/extract_test_fixtures.py
git commit -- tests/fixtures/ scripts/extract_test_fixtures.py -m "test(L1): production-derived fixtures for v2 adapter tests"
```

### Task L1.3: Rewrite `build_dimensions_v2` to source from CATEGORY_DIMENSIONS

**Files:**
- Modify: `app/services/scoring_service.py:2006-2050`

**Step 1:** Read current implementation:

```bash
# In ../smartcompare-A-L1
sed -n '2000,2055p' app/services/scoring_service.py
```

**Step 2:** Replace `build_dimensions_v2` body with category-aware lookup:

```python
def build_dimensions_v2(
    products_data: list[dict],
    scoring_result: dict,
    category: str,
    winner_index: int,
) -> list[dict]:
    """Build v2 dimensions array using CATEGORY_DIMENSIONS[category].
    
    Returns one dim entry per dimension defined for the category, with:
      - key: snake_case dim name (e.g., 'performance', 'longevity', 'efficacy')
      - label: human-readable display name
      - product_scores: [score_0, score_1] (0-100)
      - winner: 0 | 1 | 'tie'
      - margin: |score_0 - score_1|
      - delta_text: human-readable difference (e.g., '+23% battery life')
    """
    if category not in CATEGORY_DIMENSIONS:
        category = "other"
    
    dims = CATEGORY_DIMENSIONS[category]
    weights = CATEGORY_DIMENSION_WEIGHTS.get(category, {})
    
    # Pull the per-product breakdowns from scoring_result
    p0_breakdown = scoring_result.get("scores", {}).get("product_0", {}).get("breakdown", {})
    p1_breakdown = scoring_result.get("scores", {}).get("product_1", {}).get("breakdown", {})
    
    result = []
    for dim_key in dims:
        s0 = p0_breakdown.get(dim_key, MISSING_SCORE)
        s1 = p1_breakdown.get(dim_key, MISSING_SCORE)
        
        if s0 == MISSING_SCORE and s1 == MISSING_SCORE:
            winner = None
        elif s0 == MISSING_SCORE:
            winner = 1
        elif s1 == MISSING_SCORE:
            winner = 0
        elif abs(s0 - s1) < 3.0:  # tie threshold (matches legacy)
            winner = "tie"
        else:
            winner = 0 if s0 > s1 else 1
        
        result.append({
            "key": dim_key,
            "label": _humanise_dim_label(dim_key),
            "product_scores": [s0, s1],
            "winner": winner,
            "margin": abs(s0 - s1) if (s0 != MISSING_SCORE and s1 != MISSING_SCORE) else 0,
            "weight": weights.get(dim_key, 0),
            "delta_text": _compose_delta_text(dim_key, products_data, s0, s1, winner),
        })
    
    return result


_DIM_LABEL_MAP = {
    "performance": "Performance",
    "value": "Value",
    "build_quality": "Build Quality",
    "feature": "Features",
    "ecosystem": "Ecosystem",
    "futureproof": "Future-Proof",
    "efficacy": "Efficacy",
    "safety": "Safety",
    "dosage": "Dosage",
    "serving_value": "Serving Value",
    "form": "Form",
    "trust": "Trust",
    "character": "Character",
    "longevity": "Longevity",
    "projection": "Projection",
    "versatility": "Versatility",
    "wear_value": "Wear Value",
    "presentation": "Presentation",
    # ... (one entry per dim across all 9 categories)
}


def _humanise_dim_label(dim_key: str) -> str:
    return _DIM_LABEL_MAP.get(dim_key, dim_key.replace("_", " ").title())


def _compose_delta_text(dim_key, products_data, s0, s1, winner) -> str:
    """Compose a brief, evidence-cited delta phrase. Best-effort; falls back
    to score-margin language if no concrete data point available."""
    if winner in (None, "tie") or (s0 == MISSING_SCORE or s1 == MISSING_SCORE):
        return ""
    # ... category-specific delta composition (see Task L1.4)
    margin = abs(s0 - s1)
    return f"+{margin:.0f}pt advantage"
```

**Step 3:** Run the failing test from L1.1:

```bash
python -m pytest tests/test_scoring_v2_category_dimensions.py -v
```

Expected: PASS — both tests green.

**Step 4:** Commit:

```bash
git add app/services/scoring_service.py tests/test_scoring_v2_category_dimensions.py
git commit -- app/services/scoring_service.py tests/test_scoring_v2_category_dimensions.py \
  -m "feat(L1): build_dimensions_v2 sources from CATEGORY_DIMENSIONS — category-aware dims"
```

### Task L1.4: Per-category delta_text composition (richer evidence)

**Files:**
- Modify: `app/services/scoring_service.py` (`_compose_delta_text`)

**Step 1:** Write failing tests asserting category-specific delta text:

```python
def test_delta_text_electronics_battery_uses_hours():
    products = [
        {"specs": {"battery": "3349 mAh", "battery_hours_estimated": 11.4}},
        {"specs": {"battery": "4000 mAh", "battery_hours_estimated": 14.0}},
    ]
    text = _compose_delta_text("performance", products, 65, 88, winner=1)
    assert "battery" in text.lower() or "performance" in text.lower()
    assert "%" in text or "h" in text  # quantified

def test_delta_text_fragrances_longevity_uses_hours():
    products = [
        {"specs": {"longevity": "6 hours"}},
        {"specs": {"longevity": "10 hours"}},
    ]
    text = _compose_delta_text("longevity", products, 50, 88, winner=1)
    assert "h" in text.lower()  # references hours

def test_delta_text_supplements_dosage_quantified():
    products = [
        {"specs": {"active_ingredient": "Vitamin D3 1000 IU"}},
        {"specs": {"active_ingredient": "Vitamin D3 5000 IU"}},
    ]
    text = _compose_delta_text("dosage", products, 50, 88, winner=1)
    assert "IU" in text or "mg" in text or "x" in text  # references dose
```

**Step 2:** Run, expect FAIL (current returns generic "+X pt advantage").

**Step 3:** Implement category-aware delta composition with per-dim hint extractors. Use UNIVERSAL_TRUST_RULES from `prompt_personalities.py` — quantify, no vague language.

**Step 4:** Run tests, expect PASS.

**Step 5:** Commit:

```bash
git commit -- app/services/scoring_service.py tests/ \
  -m "feat(L1): delta_text quantified per-category (battery h, longevity h, dosage IU)"
```

### Task L1.5: ~~Fix `_build_factual_verdict` NULL emission~~ → **Pin populated state with regression net**

**[CORRECTION 2026-06-08]:** Per L1-be-v2 prod-curl verification (3 categories all returned populated `scoring_v2.factual_verdict.line1/line2`), the original "NULL emission" claim was a dispatcher audit-script error (checked `overview.factual_verdict`, wrong path). The actual task is to add a regression-net test fixture pinning the populated state — preserving the Bundle C A.3.2 builder against future drift. The implementation steps below remain useful as defensive guidance if any future query returns NULL; the test added at commit 9957970 (Sprint A Day 1) is the actual deliverable.

**Files:**
- Modify: `app/services/response_builder.py:353-396`
- Create: `tests/test_response_builder_factual_verdict.py`

**Step 1:** Write failing tests using production fixtures:

```python
def test_factual_verdict_line1_populated_electronics():
    fv = _build_factual_verdict(
        ELECTRONICS_FIXTURE,
        ELECTRONICS_SCORING_RESULT,
        category_used="electronics",
        winner_index=1,
    )
    assert fv["line1"] is not None
    assert len(fv["line1"]) > 20
    assert "Galaxy" in fv["line1"] or "Samsung" in fv["line1"]  # references winner

def test_factual_verdict_line2_populated():
    fv = _build_factual_verdict(...)
    assert fv["line2"] is not None
    assert any(kw in fv["line2"].lower() for kw in ["camera", "battery", "value", "performance"])
```

**Step 2:** Investigate why current impl returns None in prod. Check the upstream `comparison["winner_declaration"]` + `comparison["winner_reason"]` fields — confirm they're populated. The current `_build_factual_verdict` likely returns `{"line1": None, "line2": None}` when its source fields are missing OR has a broken short-circuit.

**Step 3:** Rewrite to draw from existing comparison block:

```python
def _build_factual_verdict(product_data, scoring_result, category_used, winner_index):
    """Compose factual_verdict.line1 + .line2 from existing comparison fields.
    Pain-workflow #1 + #2 + #8 — TL;DR-first, max 2-3 specifics, no hedging."""
    comparison = scoring_result.get("comparison") or product_data.get("comparison") or {}
    
    winner_decl = comparison.get("winner_declaration") or ""
    winner_reason = comparison.get("winner_reason") or ""
    key_tradeoff = comparison.get("key_tradeoff") or ""
    
    # line1: TL;DR — winner + 1 leading evidence point
    if winner_decl:
        line1 = winner_decl.strip()
    else:
        products = product_data.get("products", [])
        if winner_index is not None and 0 <= winner_index < len(products):
            line1 = f"{products[winner_index].get('name', 'Product ' + str(winner_index + 1))} wins."
        else:
            line1 = ""
    
    # line2: pain-workflow-aware specifics — value/budget framing first
    line2 = winner_reason or key_tradeoff or ""
    
    return {"line1": line1.strip() or None, "line2": line2.strip() or None}
```

**Step 4:** Run all factual_verdict tests, expect PASS.

**Step 5:** Commit:

```bash
git commit -- app/services/response_builder.py tests/test_response_builder_factual_verdict.py \
  -m "fix(L1): _build_factual_verdict populates line1/line2 from comparison fields"
```

### Task L1.6: Add `confidence_legs` + `confidence_details` to scoring_v2

**Files:**
- Modify: `app/services/response_builder.py:398-470` (`_build_scoring_v2`)

**Step 1:** Failing test:

```python
def test_scoring_v2_has_confidence_legs():
    v2 = _build_scoring_v2(ELECTRONICS_FIXTURE, ELECTRONICS_SCORING_RESULT, "electronics", 1)
    assert v2["confidence_legs"] is not None
    assert "price" in v2["confidence_legs"]
    assert "reviews" in v2["confidence_legs"]
    assert "specs" in v2["confidence_legs"]
    for leg, level in v2["confidence_legs"].items():
        assert level in ("strong", "acceptable", "weak")

def test_scoring_v2_has_confidence_details():
    v2 = _build_scoring_v2(ELECTRONICS_FIXTURE, ELECTRONICS_SCORING_RESULT, "electronics", 1)
    assert "confidence_details" in v2
    assert "price" in v2["confidence_details"]
    # confidence_details exposes evidence per leg (source count, etc.)
    assert "sources_count" in v2["confidence_details"]["price"]
```

**Step 2:** Run, expect FAIL.

**Step 3:** Add to `_build_scoring_v2`:

```python
from app.services.scoring_service import compute_confidence

def _build_scoring_v2(product_data, scoring_result, category_used, winner_index):
    # ... existing code ...
    
    confidence_obj = compute_confidence(product_data)  # returns dict with strong/acceptable/weak
    confidence_details = _build_confidence_details(product_data)  # per-leg evidence
    
    scoring_v2 = {
        # ... existing keys ...
        "confidence_legs": confidence_obj,
        "confidence_details": confidence_details,
    }
    return scoring_v2


def _build_confidence_details(product_data):
    """Per-leg evidence for confidence-pill tap-to-reveal sheet."""
    products = product_data.get("products", [])
    details = {"price": {}, "reviews": {}, "specs": {}}
    
    # Price: number of agreeing sources
    price_sources_p0 = len(products[0].get("price", {}).get("alternative_retailers", [])) + 1
    price_sources_p1 = len(products[1].get("price", {}).get("alternative_retailers", [])) + 1
    details["price"] = {
        "sources_count": min(price_sources_p0, price_sources_p1),
        "method_p0": products[0].get("price", {}).get("source_method"),
        "method_p1": products[1].get("price", {}).get("source_method"),
    }
    
    # Reviews: review_count + sources
    details["reviews"] = {
        "review_count_p0": products[0].get("review_count", 0),
        "review_count_p1": products[1].get("review_count", 0),
    }
    
    # Specs: field-population ratio
    details["specs"] = {
        "fields_populated_p0": _count_populated_specs(products[0]),
        "fields_populated_p1": _count_populated_specs(products[1]),
    }
    return details
```

**Step 4:** Run tests, expect PASS.

**Step 5:** Commit.

### Task L1.7: Wire `overview.products[i].variant` string

**Files:**
- Modify: `app/services/response_builder.py:600-700` (overview product block)
- Create: `tests/test_overview_variant_pros_cons.py`

**Step 1:** Failing test:

```python
def test_overview_product_has_variant_string():
    response = build_comparison_response(ELECTRONICS_FIXTURE, scoring_result, ...)
    products = response["overview"]["products"]
    assert "variant" in products[0]
    assert products[0]["variant"] is not None  # e.g., "128GB · Black"
    # Variant is composed from specs.storage + specs.color when available

def test_overview_product_variant_empty_string_when_no_data():
    """If specs lack storage/color/etc., variant is empty string (not crash)."""
    minimal_data = {...}  # product with no specs
    response = build_comparison_response(minimal_data, ...)
    assert response["overview"]["products"][0]["variant"] == ""
```

**Step 2:** Run, FAIL.

**Step 3:** Implement variant composer:

```python
def _compose_variant_string(product: dict, category: str) -> str:
    """Build a short variant tag like '128GB · Black' for the product card.
    Category-aware: phones get storage+color, fragrances get volume_ml+concentration,
    fashion gets size+color, etc."""
    specs = product.get("specs", {}) or {}
    parts = []
    
    if category in ("electronics",):
        for key in ("storage", "color", "ram"):
            if specs.get(key):
                parts.append(str(specs[key]).strip())
    elif category == "fragrances":
        if specs.get("volume_ml") or specs.get("volume"):
            parts.append(f"{specs.get('volume_ml') or specs.get('volume')}ml")
        if specs.get("concentration"):
            parts.append(str(specs["concentration"]).strip())
    elif category == "fashion":
        for key in ("size", "color", "material"):
            if specs.get(key):
                parts.append(str(specs[key]).strip())
    # ... other categories
    
    return " · ".join(parts[:3])  # cap to 3 to fit card UI
```

Add to the overview product block builder:

```python
product_card["variant"] = _compose_variant_string(product, category_used)
```

**Step 4:** Run tests, PASS.

**Step 5:** Commit.

### Task L1.8: Flatten `overview.products[i].pros_cons`

**Files:**
- Modify: `app/services/response_builder.py` (overview product block)

**Step 1:** Failing test:

```python
def test_overview_pros_cons_populated_for_electronics():
    response = build_comparison_response(ELECTRONICS_FIXTURE, scoring_result, ...)
    products = response["overview"]["products"]
    assert isinstance(products[0]["pros_cons"], dict)
    assert len(products[0]["pros_cons"]["pros"]) >= 2
    assert len(products[0]["pros_cons"]["cons"]) >= 1

def test_overview_pros_cons_winner_starred():
    response = build_comparison_response(ELECTRONICS_FIXTURE, scoring_result, ..., winner_index=1)
    products = response["overview"]["products"]
    assert products[1]["pros_cons"]["is_winner"] is True
    assert products[0]["pros_cons"]["is_winner"] is False
```

**Step 2:** FAIL.

**Step 3:** Source pros/cons from existing extraction. The extraction service already produces per-product `pros` / `cons` lists in `product_data`; the overview builder currently drops them. Add:

```python
product_card["pros_cons"] = {
    "pros": product.get("pros", [])[:4],  # cap to 4 per design
    "cons": product.get("cons", [])[:4],
    "is_winner": (winner_index == idx),
}
```

**Step 4:** PASS.

**Step 5:** Commit.

### Task L1.9: Per-spec-row winner flag for design Screen 4

**Files:**
- Modify: `app/services/response_builder.py` (specs block)

**Step 1:** Failing test:

```python
def test_specs_block_includes_per_row_winner():
    response = build_comparison_response(ELECTRONICS_FIXTURE, scoring_result, ...)
    specs_comparison = response["specs"]["specs_comparison"]
    # specs_comparison is a list of {field, p0_value, p1_value, winner}
    for row in specs_comparison:
        assert "winner" in row
        assert row["winner"] in (0, 1, "tie", None)
```

**Step 2:** Implement per-row winner detection (numeric specs: larger wins for battery/RAM/storage; smaller wins for weight; string specs: tie unless explicitly category-aware).

**Step 3:** Hook into existing `comparison["specs_comparison"]` builder — augment with winner field.

**Step 4:** PASS.

**Step 5:** Commit.

### Task L1.10: Lane 1 integration test + cross-validation curl

**Files:**
- Create: `tests/test_lane1_integration.py`

**Step 1:** Integration test that runs `compare_from_text()` end-to-end with a fixture and asserts the full v2 shape:

```python
@pytest.mark.live_unit
def test_lane1_full_v2_shape_iphone_galaxy():
    service = get_comparison_service()
    response = asyncio.run(service.compare_from_text(
        "iPhone 15 vs Galaxy S24", region="bahrain"
    ))
    # All Lane 1 invariants in one pass:
    assert response["overview"]["products"][0]["variant"] != ""
    assert response["overview"]["products"][0]["pros_cons"]["pros"]
    assert response["overview"]["products"][0]["pros_cons"]["is_winner"] in (True, False)
    assert response["scoring_v2"]["factual_verdict"]["line1"]
    assert response["scoring_v2"]["factual_verdict"]["line2"]
    assert response["scoring_v2"]["confidence_legs"]["price"] in ("strong", "acceptable", "weak")
    assert response["scoring_v2"]["confidence_details"]["price"]["sources_count"] > 0
    dim_keys = [d["key"] for d in response["scoring_v2"]["dimensions"]]
    assert "performance" in dim_keys
```

**Step 2:** Run against staging (or live prod):

```bash
python -m pytest tests/test_lane1_integration.py -v -m live_unit
```

Expected: PASS.

**Step 3:** Manual prod curl smoke:

```bash
curl -s "https://web-production-58776.up.railway.app/api/v1/text/compare?q=iPhone+15+vs+Galaxy+S24&region=bahrain&nocache=true" | \
  python -c "import json,sys; d=json.load(sys.stdin); print('dims:', [x['key'] for x in d['scoring_v2']['dimensions']]); print('verdict.line1:', d['scoring_v2']['factual_verdict']['line1']); print('verdict.line2:', d['scoring_v2']['factual_verdict']['line2']); print('variant p0:', d['overview']['products'][0]['variant']); print('pros p0:', len(d['overview']['products'][0]['pros_cons']['pros']))"
```

Expected: dim keys include `performance`/`build_quality`/etc.; line1+line2 non-null; variant populated; pros count ≥2.

**Step 4:** Commit + signal Lane 1 ready for cross-QA:

```bash
git commit --allow-empty -m "milestone(L1): integration test green — ready for L4 cross-QA"
```

### Task L1.11: L1 owner QAs L2's `_compute_data_confidence` + `_build_escalation_scrapers` (per matrix)

**Files:** read-only review of L2 worktree

**Step 1:** Once L2 merges its initial implementation, switch worktree:

```bash
cd ../smartcompare-A-L2
git log --oneline | head -10  # confirm L2 state
```

**Step 2:** Review `app/services/confidence_service.py`, `app/services/price_service.py` confidence-driven escalation, `_build_escalation_scrapers` rename. Verify against design § 3.

**Step 3:** Run L2's test suite + a `nocache=true` smoke against a low-confidence Tier 1 case (Tom Ford Black Orchid).

**Step 4:** File findings to dispatcher via SendMessage:
- PASS: features implemented, tests green, prod smoke shows confidence escalation firing
- SUBPAR: list specific gaps with file:line refs → SEND BACK to L2

Per Team Execution Contract — no merge until QA verdict is PASS.

---

## Lane 2 — Backend Parallel Races + Bahrain Sources (Opus #2, ~5 days)

**Goal:** Replace luxury-gated tier waterfall with confidence-driven parallel multi-source race. Implement Bahrain-first source hierarchy. Add 25 per-product-type spec schemas. Add source-trace observability.

**Worktree:** `../smartcompare-A-L2` on `feature/A-L2-parallel-races`

**Files affected:**
- Create: `app/services/confidence_service.py`
- Create: `app/services/source_router.py`
- Create: `app/services/product_type_router.py`
- Modify: `app/services/price_service.py` (rename `_build_luxury_scrapers` → `_build_escalation_scrapers`; remove luxury gate)
- Modify: `app/services/structured_comparison_service.py:996` + `:2245`
- Modify: `app/services/extraction_service.py` (per-category review search terms for 4 fallback categories)
- Modify: `app/services/response_builder.py` (add `metadata.source_trace`)
- Create: `tests/test_confidence_service.py`
- Create: `tests/test_source_router_bahrain_first.py`
- Create: `tests/test_product_type_router.py`
- Create: `tests/test_parallel_race_escalation.py`
- Create: `tests/test_source_trace_observability.py`

### Task L2.1: Create `confidence_service.py` with pure-function signal computation

**Files:**
- Create: `app/services/confidence_service.py`
- Create: `tests/test_confidence_service.py`

**Step 1:** Failing test:

```python
from app.services.confidence_service import compute_price_confidence, compute_specs_confidence

def test_price_confidence_high_when_two_retailers_within_20pct():
    sources = [
        {"src": "serper_shopping", "amount": 142.12, "retailer_score": 0.9},
        {"src": "curl:carrefour.com.bh", "amount": 145.00, "retailer_score": 0.8},
    ]
    result = compute_price_confidence(sources, training_estimate=140.0)
    assert result["level"] == "high"

def test_price_confidence_low_when_single_source_deviates_40pct():
    sources = [{"src": "serper_shopping", "amount": 20.0, "retailer_score": 0.5}]
    result = compute_price_confidence(sources, training_estimate=120.0)
    assert result["level"] == "low"
    assert "deviation" in result["reasons"]

def test_specs_confidence_high_when_80pct_fields_populated():
    schema_fields = ["display", "processor", "ram", "storage", "battery", "rear_camera", "front_camera", "os", "weight", "water_resistance"]
    populated = {f: "value" for f in schema_fields[:9]}  # 9/10 = 90%
    result = compute_specs_confidence(populated, schema_fields)
    assert result["level"] == "high"
```

**Step 2:** Implement:

```python
# app/services/confidence_service.py
"""Pure-function confidence signal computation. No I/O."""

from typing import List, Dict, Any


def compute_price_confidence(sources: List[Dict[str, Any]], training_estimate: float | None = None) -> Dict[str, Any]:
    """Returns: {"level": "high"|"medium"|"low", "reasons": [str], "median": float}"""
    if not sources:
        return {"level": "low", "reasons": ["no_sources"], "median": None}
    
    amounts = [s["amount"] for s in sources if s.get("amount") is not None]
    if not amounts:
        return {"level": "low", "reasons": ["no_amounts"], "median": None}
    
    median = sorted(amounts)[len(amounts) // 2]
    reasons = []
    
    # Multi-source agreement check
    if len(amounts) >= 2:
        within_20pct = sum(1 for a in amounts if 0.8 * median <= a <= 1.2 * median)
        if within_20pct >= 2:
            agreement = "multi_source_agreement"
        else:
            agreement = "multi_source_disagreement"
            reasons.append("sources_disagree")
    else:
        agreement = "single_source"
        reasons.append("only_one_source")
    
    # Training-data sanity check
    if training_estimate and abs(median - training_estimate) / training_estimate > 0.40:
        reasons.append("deviation_from_training_estimate")
    
    # Retailer-score check
    top_retailer_score = max((s.get("retailer_score", 0) for s in sources), default=0)
    if top_retailer_score < 0.7:
        reasons.append("low_retailer_score")
    
    # Decide level
    if not reasons and agreement == "multi_source_agreement":
        level = "high"
    elif "deviation_from_training_estimate" in reasons or len(reasons) >= 2:
        level = "low"
    else:
        level = "medium"
    
    return {"level": level, "reasons": reasons, "median": median, "sources_count": len(sources)}


def compute_specs_confidence(populated: Dict[str, Any], schema_fields: List[str]) -> Dict[str, Any]:
    if not schema_fields:
        return {"level": "low", "reasons": ["no_schema"]}
    
    count_populated = sum(1 for f in schema_fields if populated.get(f))
    ratio = count_populated / len(schema_fields)
    
    if ratio >= 0.8:
        level = "high"
    elif ratio >= 0.5:
        level = "medium"
    else:
        level = "low"
    
    return {
        "level": level,
        "ratio": ratio,
        "populated_count": count_populated,
        "schema_size": len(schema_fields),
    }


def compute_reviews_confidence(review_count_p0: int, review_count_p1: int, sources_count: int = 1) -> Dict[str, Any]:
    min_count = min(review_count_p0, review_count_p1)
    if min_count > 100 and sources_count >= 2:
        level = "high"
    elif min_count > 20:
        level = "medium"
    else:
        level = "low"
    return {"level": level, "min_count": min_count, "sources_count": sources_count}


def should_escalate(confidence_obj: Dict[str, Any]) -> bool:
    """Returns True if any signal warrants firing additional tier(s)."""
    return confidence_obj.get("level") == "low"
```

**Step 3:** Run tests, PASS.

**Step 4:** Commit.

### Task L2.2: Create `source_router.py` with Bahrain-first hierarchy

**Files:**
- Create: `app/services/source_router.py`
- Create: `tests/test_source_router_bahrain_first.py`

**Step 1:** Failing test:

```python
from app.services.source_router import get_sources_for_category, score_source

def test_bahrain_sources_score_higher_than_gcc():
    bh_score = score_source("https://www.lulu.com.bh/product/123", category="electronics")
    gcc_score = score_source("https://www.noon.com/uae-en/product/456", category="electronics")
    global_score = score_source("https://www.amazon.com/dp/B0XXX", category="electronics")
    assert bh_score > gcc_score > global_score
    assert bh_score >= 3.0
    assert gcc_score >= 1.5
    assert global_score >= 1.0

def test_get_sources_for_category_supplements_includes_iherb_and_boots_bh():
    sources = get_sources_for_category("supplements")
    domains = [s.domain for s in sources]
    assert "iherb.com" in domains
    assert "bn.boots.com" in domains
    # Bahrain-tier appears before global
    bh_indices = [i for i, s in enumerate(sources) if s.tier == "bahrain"]
    global_indices = [i for i, s in enumerate(sources) if s.tier == "global"]
    assert max(bh_indices) < min(global_indices, default=999)
```

**Step 2:** Implement source registry:

```python
# app/services/source_router.py
"""Bahrain-first source registry + URL scoring."""

from dataclasses import dataclass
from typing import List
from urllib.parse import urlparse


@dataclass
class Source:
    domain: str
    tier: str  # "bahrain" | "gcc" | "global"
    categories: tuple  # which categories this source serves; empty = all
    weight: float


SOURCE_REGISTRY: List[Source] = [
    # === BAHRAIN PRIMARY (weight 3.0) ===
    Source("lulu.com.bh", "bahrain", (), 3.0),
    Source("carrefourbh.com", "bahrain", (), 3.0),
    Source("sharafdg.com.bh", "bahrain", ("electronics",), 3.0),
    Source("extra.com.bh", "bahrain", ("electronics",), 3.0),
    Source("geant.com.bh", "bahrain", (), 3.0),
    Source("bn.boots.com", "bahrain", ("supplements", "skincare", "makeup", "haircare"), 3.0),
    Source("bolo.bh", "bahrain", ("supplements", "makeup", "skincare"), 3.0),
    Source("behbehani.com", "bahrain", ("electronics", "fashion"), 3.0),
    Source("eroselectronics.com", "bahrain", ("electronics",), 3.0),
    Source("jumboelectronics.com", "bahrain", ("electronics",), 3.0),
    Source("talabat.com", "bahrain", ("grocery",), 3.0),
    Source("spinneysbahrain.com", "bahrain", ("grocery",), 3.0),
    Source("megamart.bh", "bahrain", ("grocery",), 3.0),
    
    # === GCC SECONDARY (weight 1.5) ===
    Source("noon.com", "gcc", (), 1.5),
    Source("amazon.ae", "gcc", (), 1.5),
    Source("sharafdg.com", "gcc", ("electronics",), 1.5),
    Source("ounass.com", "gcc", ("fashion", "fragrances", "makeup"), 1.5),
    Source("bloomingdales.ae", "gcc", ("fashion",), 1.5),
    Source("tryano.com", "gcc", ("fashion", "fragrances"), 1.5),
    
    # === GLOBAL FALLBACK (weight 1.0) ===
    Source("amazon.com", "global", (), 1.0),
    Source("apple.com", "global", ("electronics",), 1.0),
    Source("samsung.com", "global", ("electronics",), 1.0),
    Source("sony.com", "global", ("electronics",), 1.0),
    Source("lg.com", "global", ("electronics",), 1.0),
    Source("iherb.com", "global", ("supplements",), 1.0),
    Source("sephora.com", "global", ("makeup", "skincare", "fragrances"), 1.0),
    Source("walmart.com", "global", (), 1.0),
    Source("fragrantica.com", "global", ("fragrances",), 1.0),
    Source("incidecoder.com", "global", ("skincare", "makeup", "haircare"), 1.0),
    Source("gsmarena.com", "global", ("electronics",), 1.0),
]


def get_sources_for_category(category: str) -> List[Source]:
    """Returns sources ordered by tier (bahrain → gcc → global), filtered by category."""
    result = []
    for tier in ("bahrain", "gcc", "global"):
        tier_sources = [s for s in SOURCE_REGISTRY if s.tier == tier and (not s.categories or category in s.categories)]
        result.extend(tier_sources)
    return result


def score_source(url: str, category: str) -> float:
    """Returns weight 0–3.0 based on Bahrain-first hierarchy."""
    domain = urlparse(url).netloc.lower().lstrip("www.")
    for s in SOURCE_REGISTRY:
        if s.domain == domain or domain.endswith("." + s.domain):
            if not s.categories or category in s.categories:
                return s.weight
    return 0.5  # unknown source
```

**Step 3:** Run tests, PASS.

**Step 4:** Commit.

### Task L2.3: Create `product_type_router.py` + 25 product-type schemas

**Files:**
- Create: `app/services/product_type_router.py`
- Create: `tests/test_product_type_router.py`

**Step 1:** Failing tests for type detection (~20 test cases across categories):

```python
from app.services.product_type_router import detect_product_type, get_schema_for_type

def test_detect_phone_from_iphone():
    assert detect_product_type("iPhone 15 Pro", "electronics") == "electronics.phone"

def test_detect_tv_from_lg_oled():
    assert detect_product_type("LG OLED55C3", "electronics") == "electronics.tv"

def test_detect_washer():
    assert detect_product_type("Samsung WW90T504DAB Washing Machine", "electronics") == "electronics.washer"

def test_detect_ac():
    assert detect_product_type("Carrier 1.5T Split AC", "electronics") == "electronics.ac"

def test_detect_protein_supplement():
    assert detect_product_type("Optimum Nutrition Gold Standard Whey Protein", "supplements") == "supplements.protein"

def test_detect_fragrance_edp():
    assert detect_product_type("Tom Ford Black Orchid Eau de Parfum 50ml", "fragrances") == "fragrances.edp"

def test_get_schema_for_phone():
    schema = get_schema_for_type("electronics.phone")
    expected_fields = ["display", "processor", "ram", "storage", "battery", "rear_camera", "front_camera", "os", "5G", "weight", "water_resistance", "charging_w"]
    assert set(schema) >= set(expected_fields)
```

**Step 2:** Implement type detection (keyword-based; GPT fallback in a separate task L2.4):

```python
# app/services/product_type_router.py
"""Sub-category detection + product-type schema lookup."""

from typing import List

PRODUCT_TYPE_KEYWORDS = {
    # Electronics
    "electronics.phone": ["iphone", "galaxy s", "pixel", "xiaomi", "oneplus", "nothing phone", "smartphone", "phone"],
    "electronics.tv": ["tv", "qled", "oled", "led tv", "smart tv", "bravia", "neo qled"],
    "electronics.laptop": ["macbook", "thinkpad", "xps", "yoga", "envy", "pavilion", "laptop", "notebook"],
    "electronics.tablet": ["ipad", "galaxy tab", "tablet", "surface"],
    "electronics.smartwatch": ["apple watch", "galaxy watch", "fitbit", "garmin", "smartwatch"],
    "electronics.headphones": ["airpods", "wh-1000xm", "qc ultra", "buds", "headphones", "earbuds"],
    "electronics.speaker": ["sonos", "homepod", "bose soundlink", "speaker"],
    "electronics.ac": ["ac", "split ac", "air conditioner", "inverter ac"],
    "electronics.washer": ["washing machine", "washer dryer", "front load", "top load"],
    "electronics.refrigerator": ["refrigerator", "fridge", "side by side", "french door"],
    "electronics.vacuum": ["vacuum", "dyson v", "roomba", "robovac", "stick vacuum"],
    "electronics.gaming_console": ["ps5", "xbox series", "switch", "playstation"],
    # Supplements
    "supplements.vitamin": ["vitamin d", "vitamin c", "vitamin b", "multivitamin"],
    "supplements.mineral": ["zinc", "magnesium", "iron supplement", "calcium"],
    "supplements.protein": ["whey", "casein", "iso100", "plant protein", "protein powder"],
    "supplements.preworkout": ["pre-workout", "preworkout", "pre workout"],
    "supplements.fish_oil": ["fish oil", "omega 3", "omega-3"],
    "supplements.multivitamin": ["multivitamin", "one a day", "centrum"],
    # Fragrances
    "fragrances.edp": ["eau de parfum", "edp"],
    "fragrances.edt": ["eau de toilette", "edt"],
    "fragrances.niche": ["mfk", "creed", "initio", "frederic malle", "amouage"],
    # Makeup
    "makeup.foundation": ["foundation", "pro filt'r", "fit me", "luminous"],
    "makeup.lipstick": ["lipstick", "matte lip", "lip color"],
    "makeup.mascara": ["mascara", "sky high", "telescopic", "diorshow"],
    # Skincare
    "skincare.serum": ["serum", "vitamin c serum", "niacinamide"],
    "skincare.sunscreen": ["sunscreen", "spf", "sun cream"],
    "skincare.cleanser": ["cleanser", "face wash", "foaming wash"],
    # Haircare
    "haircare.shampoo": ["shampoo"],
    # Fashion
    "fashion.bag": ["bag", "tote", "satchel", "handbag", "backpack"],
    "fashion.shoe": ["sneaker", "shoe", "trainer", "boot", "loafer", "air force", "stan smith"],
    "fashion.watch": ["watch", "rolex", "omega", "seiko", "casio"],
    # Grocery
    "grocery.oil": ["olive oil", "cooking oil", "extra virgin"],
    "grocery.tea": ["tea", "earl grey", "green tea", "black tea"],
    "grocery.chocolate": ["chocolate", "cocoa", "dark chocolate"],
}


PRODUCT_TYPE_SCHEMAS = {
    "electronics.phone":     ["display", "processor", "ram", "storage", "battery", "rear_camera", "front_camera", "os", "5G", "weight", "water_resistance", "charging_w"],
    "electronics.tv":        ["screen_size", "panel_type", "resolution", "refresh_rate", "hdr", "smart_os", "ports_hdmi", "audio_w", "consumption_kwh"],
    "electronics.laptop":    ["display", "cpu", "gpu", "ram", "storage", "battery_hrs", "weight", "ports", "os", "keyboard_layout"],
    "electronics.tablet":    ["display", "processor", "ram", "storage", "battery", "weight", "os", "stylus_support"],
    "electronics.smartwatch":["display", "sensors", "battery_days", "water_resistance", "connectivity", "weight", "compatibility"],
    "electronics.headphones":["driver_mm", "anc", "battery_hrs", "weight", "codecs", "bt_version", "water_resistance"],
    "electronics.speaker":   ["driver_count", "power_w", "battery_hrs", "connectivity", "water_resistance", "smart_assistant"],
    "electronics.ac":        ["capacity_btu", "energy_class", "inverter", "noise_db", "modes", "filter", "wifi", "refrigerant"],
    "electronics.washer":    ["capacity_kg", "spin_rpm", "energy_class", "load_type", "programs", "noise_db", "inverter", "dimensions"],
    "electronics.refrigerator":["capacity_l", "doors", "energy_class", "ice_maker", "freezer_position", "noise_db"],
    "electronics.vacuum":    ["suction_pa", "battery_min", "weight", "dustbin_l", "filtration", "attachments"],
    "electronics.gaming_console":["storage", "controller", "video_output", "online_service", "exclusives_count"],
    "supplements.vitamin":   ["dose_iu_mcg", "form", "third_party_tested", "allergens", "serving_size", "count"],
    "supplements.mineral":   ["dose_mg", "form", "chelation", "bioavailability", "serving_size", "count"],
    "supplements.protein":   ["protein_g_serving", "carbs", "fat", "calories", "amino_profile", "filtration", "flavors", "container_size"],
    "supplements.preworkout":["caffeine_mg", "beta_alanine_g", "creatine_g", "citrulline_g", "servings"],
    "supplements.fish_oil":  ["epa_mg", "dha_mg", "third_party_tested", "molecularly_distilled", "serving_size", "count"],
    "supplements.multivitamin":["vitamins_count", "minerals_count", "form", "iron_included", "serving_size", "count"],
    "fragrances.edp":        ["concentration", "longevity_hrs", "sillage", "projection_m", "scent_family", "notes_top", "notes_heart", "notes_base", "volume_ml", "season", "occasion"],
    "fragrances.edt":        ["concentration", "longevity_hrs", "sillage", "scent_family", "notes_top", "notes_heart", "notes_base", "volume_ml", "season", "occasion"],
    "fragrances.niche":      ["concentration", "longevity_hrs", "sillage", "projection_m", "scent_family", "notes_top", "notes_heart", "notes_base", "perfumer", "house_year_founded", "volume_ml"],
    "makeup.foundation":     ["shade_range_count", "finish", "coverage", "skin_type", "spf", "fragrance_free", "vegan", "vol_ml"],
    "makeup.lipstick":       ["finish", "color", "longevity_hrs", "transfer_proof", "moisturising", "vegan", "vol_g"],
    "makeup.mascara":        ["brush_type", "formula", "smudge_proof", "water_proof", "lash_effect", "vegan", "color"],
    "skincare.serum":        ["hero_active", "secondary_actives", "ph", "comedogenic", "fragrance_free", "skin_type", "vol_ml"],
    "skincare.sunscreen":    ["spf", "pa_rating", "filter_type", "finish", "water_resist_min", "fragrance_free", "white_cast"],
    "skincare.cleanser":     ["cleanser_type", "ph", "skin_type", "actives", "fragrance_free", "vol_ml"],
    "haircare.shampoo":      ["sulfate_free", "paraben_free", "silicone_free", "target_concern", "hair_type", "vol_ml", "scent"],
    "fashion.bag":           ["material", "lining", "hardware", "closure", "dimensions", "strap_drop", "origin", "weight"],
    "fashion.shoe":          ["upper_material", "sole", "closure", "sizing_run", "width", "last_shape", "origin"],
    "fashion.watch":         ["case_material", "movement", "water_resist_atm", "crystal", "diameter_mm", "strap", "complications"],
    "grocery.oil":           ["variety", "origin", "acidity_pct", "filtration", "organic", "volume_ml"],
    "grocery.tea":           ["type", "origin", "format", "caffeine", "bags_count", "organic"],
    "grocery.chocolate":     ["cacao_pct", "origin", "vegan", "sugar_g_serving", "weight_g"],
}


def detect_product_type(product_name: str, category: str) -> str:
    """Return product-type key (e.g., 'electronics.phone') based on keyword match.
    Falls back to category-level default if no match."""
    name_lower = product_name.lower()
    candidates = [k for k in PRODUCT_TYPE_KEYWORDS if k.startswith(f"{category}.")]
    
    for type_key in candidates:
        for kw in PRODUCT_TYPE_KEYWORDS[type_key]:
            if kw in name_lower:
                return type_key
    
    # Fallback to first product-type for the category
    if candidates:
        return candidates[0]
    return f"{category}.default"


def get_schema_for_type(type_key: str) -> List[str]:
    return PRODUCT_TYPE_SCHEMAS.get(type_key, [])
```

**Step 2:** Run tests, PASS.

**Step 3:** Commit.

### Task L2.4: GPT-4o-mini fallback for ambiguous product-type detection

**Files:**
- Modify: `app/services/product_type_router.py`

**Step 1:** Failing test:

```python
@pytest.mark.live_unit
def test_detect_ambiguous_falls_to_gpt():
    """When keywords don't match, GPT picks best type. <200ms cached."""
    result = detect_product_type("Eufy RoboVac 11S Max", "electronics")
    assert result == "electronics.vacuum"
```

**Step 2:** Add GPT fallback when keyword scan returns the category-default:

```python
async def detect_product_type_async(product_name: str, category: str) -> str:
    """Async version with GPT fallback for ambiguous inputs."""
    kw_result = detect_product_type(product_name, category)
    if not kw_result.endswith(".default"):
        return kw_result
    
    # GPT fallback (cached in Redis 7 days)
    cache_key = f"product_type:{category}:{product_name.lower()[:80]}"
    cached = await get_cached(cache_key)
    if cached:
        return cached
    
    types_for_cat = [k for k in PRODUCT_TYPE_SCHEMAS if k.startswith(f"{category}.")]
    prompt = f"Classify '{product_name}' into one of: {types_for_cat}. Respond with the exact type key only."
    
    result = await openai_chat(model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}], max_tokens=20)
    if result.strip() in types_for_cat:
        await set_cached(cache_key, result.strip(), ttl_seconds=604800)
        return result.strip()
    return kw_result  # fall back to default
```

**Step 3:** PASS.

**Step 4:** Commit.

### Task L2.5: Replace luxury gate with confidence-driven escalation

**Files:**
- Modify: `app/services/structured_comparison_service.py:2245`
- Modify: `app/services/price_service.py:710` (`_build_luxury_scrapers` → `_build_escalation_scrapers`)

**Step 1:** Failing test:

```python
from app.services.structured_comparison_service import _should_escalate_price_scrape

def test_escalates_when_single_source_deviates():
    """Tom Ford 20 BHD vs $300 training estimate → must escalate."""
    sources = [{"src": "serper_shopping", "amount": 20.0, "retailer_score": 0.4}]
    assert _should_escalate_price_scrape(sources, training_estimate=120.0) is True

def test_no_escalation_when_two_sources_agree():
    sources = [
        {"src": "serper_shopping", "amount": 142.12, "retailer_score": 0.9},
        {"src": "curl:lulu.com.bh", "amount": 145.00, "retailer_score": 1.0},
    ]
    assert _should_escalate_price_scrape(sources, training_estimate=140.0) is False

def test_escalates_for_any_category_not_just_luxury():
    """Non-luxury electronics (e.g., Xiaomi 14) escalates if confidence is low."""
    sources = [{"src": "serper_shopping", "amount": 50.0, "retailer_score": 0.5}]
    # Xiaomi 14 retail ~$700
    assert _should_escalate_price_scrape(sources, training_estimate=700.0, brand="Xiaomi") is True
```

**Step 2:** Implement escalation predicate using confidence_service:

```python
# In structured_comparison_service.py
from app.services.confidence_service import compute_price_confidence, should_escalate

def _should_escalate_price_scrape(sources, training_estimate=None, brand=None) -> bool:
    """GLOBAL — fires for any category. Replaces is_luxury_brand() gate."""
    if not sources:
        return True
    confidence = compute_price_confidence(sources, training_estimate=training_estimate)
    return should_escalate(confidence)
```

**Step 3:** Replace line 2245 in `structured_comparison_service.py`:

```python
# OLD:
# if not price and is_luxury_brand(full_name) and ENABLE_PAGE_SCRAPE:

# NEW:
training_estimate = await _get_training_estimate(full_name, category) if ENABLE_PAGE_SCRAPE else None
tier1_sources = shopping_items if isinstance(shopping_items, list) else []

if ENABLE_PAGE_SCRAPE and _should_escalate_price_scrape(tier1_sources, training_estimate, brand=brand):
    scraping_mode = os.environ.get("SCRAPING_MODE", "hard")
    # ... existing escalation logic (formerly under luxury gate)
```

**Step 4:** Rename `_build_luxury_scrapers` → `_build_escalation_scrapers` in `price_service.py:710` (keep same signature; rename callers).

**Step 5:** Run tests, PASS.

**Step 6:** Commit:

```bash
git commit -- app/services/structured_comparison_service.py app/services/price_service.py tests/ \
  -m "feat(L2): confidence-driven escalation replaces luxury gate — global cascade for all 9 categories"
```

### Task L2.6: Parallel race per data type (price + specs + reviews + image)

**Files:**
- Modify: `app/services/structured_comparison_service.py` (`_fetch_product_data`)

**Step 1:** Failing test asserting parallel topology:

```python
@pytest.mark.live_unit
async def test_phase1_parallel_max_15s():
    """Phase 1 wall-time bounded by slowest race, not sum."""
    service = get_comparison_service()
    start = time.time()
    await service._fetch_product_data(product_name="iPhone 15", region="bahrain")
    elapsed = time.time() - start
    assert elapsed < 15.0, f"Phase 1 took {elapsed}s — race not parallel"
```

**Step 2:** Audit current `_fetch_product_data` — it already uses `asyncio.gather` for specs+price+reviews+image per CLAUDE.md. Verify wait_for caps per race:

```python
async def _fetch_product_data(self, ...):
    # ... unified search ...
    
    phase1_tasks = [
        asyncio.wait_for(self._race_price(...), timeout=15.0),
        asyncio.wait_for(self._race_specs(...), timeout=8.0),
        asyncio.wait_for(self._race_reviews(...), timeout=6.0),
        asyncio.wait_for(self._race_image(...), timeout=5.0),
    ]
    results = await asyncio.gather(*phase1_tasks, return_exceptions=True)
    # ... handle per-race exceptions (TimeoutError → fall back to None + source_trace entry) ...
```

**Step 3:** Refactor existing inline logic into named race methods `_race_price`, `_race_specs`, `_race_reviews`, `_race_image`. Each race internally fans out N sources via `asyncio.gather` with cross-validation.

**Step 4:** Run tests, PASS.

**Step 5:** Commit.

### Task L2.7: Wrap `compare_from_text` in `wait_for(STREAM_HARD_CAP_SECONDS)`

**Files:**
- Modify: `app/services/structured_comparison_service.py:996`

**Step 1:** Failing test:

```python
@pytest.mark.live_unit
async def test_compare_from_text_hard_capped():
    """Non-streaming path now has same 25s cap as streaming."""
    service = get_comparison_service()
    # Inject a slow Phase 1 mock that would otherwise hang for 60s
    with patch.object(service, '_fetch_product_data', new=_slow_60s_mock):
        start = time.time()
        with pytest.raises(asyncio.TimeoutError):
            await service.compare_from_text("foo vs bar", region="bahrain")
        elapsed = time.time() - start
        assert elapsed <= STREAM_HARD_CAP_SECONDS + 2.0  # 2s buffer
```

**Step 2:** Wrap `compare_from_text` body in `asyncio.wait_for(timeout=STREAM_HARD_CAP_SECONDS)`. On timeout, return a `success: false, code: TIMEOUT` response (not raise — preserve user-facing graceful degrade).

**Step 3:** PASS.

**Step 4:** Commit.

### Task L2.8: Cross-validation for price (median of agreeing sources)

**Files:**
- Modify: `app/services/price_service.py` (consolidation logic)

**Step 1:** Failing test asserting outlier rejection:

```python
def test_price_consolidation_drops_outlier():
    sources = [
        {"src": "lulu.com.bh", "amount": 145.00},
        {"src": "carrefour.com.bh", "amount": 142.00},
        {"src": "amazon.ae", "amount": 20.00},  # outlier — clearly wrong
    ]
    consolidated = consolidate_price_sources(sources)
    assert consolidated["amount"] == 143.5  # median of 142 + 145
    assert "outlier_dropped" in consolidated["flags"]
    assert consolidated["cross_validation"] == "passed"
```

**Step 2:** Implement `consolidate_price_sources()` — drop outliers >2σ from median, then take median of remaining.

**Step 3:** PASS.

**Step 4:** Commit.

### Task L2.9: `metadata.source_trace` observability

**Files:**
- Modify: `app/services/response_builder.py` (`metadata` block)
- Modify: `app/services/structured_comparison_service.py` (collect trace during Phase 1)
- Create: `tests/test_source_trace_observability.py`

**Step 1:** Failing test:

```python
def test_response_includes_source_trace():
    response = build_comparison_response(ELECTRONICS_FIXTURE, scoring_result, ...)
    trace = response["metadata"]["source_trace"]
    assert "price" in trace
    assert "specs" in trace
    assert "reviews" in trace
    assert "image" in trace
    
    price_trace = trace["price"]
    assert isinstance(price_trace["sources_tried"], list)
    assert isinstance(price_trace["sources_returned_value"], list)
    assert "median_chosen" in price_trace
    assert "cross_validation" in price_trace
    assert isinstance(price_trace["wall_ms"], int)
```

**Step 2:** Add `SourceTrace` collector class instantiated per-request, threaded through Phase 1 races, emitted in response builder.

**Step 3:** PASS.

**Step 4:** Commit.

### Task L2.10: Per-category review search terms for 4 fallback categories

**Files:**
- Modify: `app/services/review_service.py` (`CATEGORY_REVIEW_TERMS`)

**Step 1:** Failing test:

```python
from app.services.review_service import CATEGORY_REVIEW_TERMS

def test_review_terms_for_supplements_clinical():
    terms = CATEGORY_REVIEW_TERMS["supplements"]
    assert any(w in terms for w in ["dosage", "effectiveness", "side effects", "clinical"])

def test_review_terms_for_fragrances_longevity():
    terms = CATEGORY_REVIEW_TERMS["fragrances"]
    assert any(w in terms for w in ["longevity", "sillage", "projection", "scent"])

def test_review_terms_for_haircare_results():
    terms = CATEGORY_REVIEW_TERMS["haircare"]
    assert any(w in terms for w in ["frizz", "scalp", "texture", "results"])
```

**Step 2:** Add 4 missing category entries:

```python
CATEGORY_REVIEW_TERMS = {
    # ... existing 6 ...
    "supplements": "user reviews dosage effectiveness side effects clinical purity",
    "fragrances": "user reviews longevity sillage projection scent character season",
    "haircare": "user reviews results frizz scalp hair type texture scent",
    "other": "user reviews quality value durability function",
}
```

**Step 3:** PASS.

**Step 4:** Commit.

### Task L2.11: Per-retailer review-quote fetcher (γ from design)

**Files:**
- Modify: `app/services/review_service.py`
- Modify: `app/services/structured_comparison_service.py` (`_race_reviews`)
- Modify: `app/services/response_builder.py` (emit `reviews.products[i].retailer_quotes`)

**Step 1:** Failing test:

```python
@pytest.mark.live_unit
async def test_retailer_quotes_populated_3_per_product():
    response = await service.compare_from_text("iPhone 15 vs Galaxy S24", region="bahrain")
    for p in response["reviews"]["products"]:
        assert "retailer_quotes" in p
        assert len(p["retailer_quotes"]) >= 2  # at least 2 (Amazon, Noon)
        for q in p["retailer_quotes"]:
            assert "retailer" in q
            assert "rating" in q
            assert "text" in q
            assert len(q["text"]) > 20
```

**Step 2:** Add fetcher that runs 3 parallel Serper Search calls (`site:amazon.com/.ae`, `site:noon.com`, `site:x.com`) per product, extracts top review snippet + rating. Cache per product 14d.

**Step 3:** Wire into `_race_reviews`. ~6 calls per comparison × $0.001 = $0.006 added.

**Step 4:** Emit in response builder under `reviews.products[i].retailer_quotes` (3 entries max).

**Step 5:** PASS.

**Step 6:** Commit.

### Task L2.12: Per-product-type schema injection into specs extraction prompt

**Files:**
- Modify: `app/services/extraction_service.py` (`_build_specs_prompt`)

**Step 1:** Failing test:

```python
@pytest.mark.live_unit
async def test_phone_specs_use_product_type_schema():
    result = await extract_specs("iPhone 15", category="electronics")
    expected = set(get_schema_for_type("electronics.phone"))
    populated = {k for k, v in result.items() if v and k != "_field_confidence"}
    coverage = len(populated & expected) / len(expected)
    assert coverage >= 0.7  # 70% of expected fields populated

@pytest.mark.live_unit
async def test_washer_specs_different_from_phone_specs():
    washer = await extract_specs("Samsung WW90T504DAB", category="electronics")
    phone = await extract_specs("iPhone 15", category="electronics")
    # Different product types → different fields
    assert "capacity_kg" in washer and "capacity_kg" not in phone
    assert "rear_camera" in phone and "rear_camera" not in washer
```

**Step 2:** Modify `_build_specs_prompt` to call `detect_product_type` + `get_schema_for_type` and inject the type-specific schema into the system prompt:

```python
def _build_specs_prompt(product_name, category, ...):
    product_type = detect_product_type(product_name, category)
    type_schema = get_schema_for_type(product_type)
    
    schema_str = ", ".join(type_schema)
    return f"""
Extract these specific fields for this {product_type} product:
{schema_str}

Return JSON with only fields that have factual values. Omit any field you cannot verify.
"""
```

**Step 3:** PASS.

**Step 4:** Commit.

### Task L2.13: L2 owner QAs L3's mobile v2 wiring (per matrix)

**Files:** read-only review of L3 worktree

**Step 1:** Once L3 commits initial implementation, switch worktree, read L3 diffs for ResultsContent.tsx + ResultsAccordion.tsx + ConfidencePills.tsx + ConfidenceDetailsSheet.tsx + DimensionBars.tsx.

**Step 2:** Verify L3 consumes new v2 fields correctly (per L1's adapter changes).

**Step 3:** Run `npx tsc --noEmit` + `npm test -- --watchAll=false` in L3 worktree.

**Step 4:** File QA verdict to dispatcher.

### Task L2.14: Lane 2 integration test against production

**Files:**
- Create: `tests/test_lane2_integration.py`

Run 6 queries (2 per scenario: confidence-high, confidence-medium, confidence-low) and assert:
- Source trace shows escalation when expected
- Wall-time stays under 25s
- Price agrees with manually-verified Bahrain retail within 15%

Commit milestone:

```bash
git commit --allow-empty -m "milestone(L2): parallel races + Bahrain sources + 25 product-type schemas — ready for L1 cross-QA"
```

---

## Lane 3 — Mobile Renders + 88s Instrumentation (Opus #3, ~4 days)

**Goal:** Wire mobile to render all v2 design fields. Instrument the 88s frontend wall.

**Worktree:** `../smartcompare-A-L3` on `feature/A-L3-mobile-renders`

**Files affected:**
- Modify: `SmartCompareApp/src/screens/ResultsScreen.tsx`
- Modify: `SmartCompareApp/src/components/results/ResultsContent.tsx`
- Modify: `SmartCompareApp/src/components/results/ResultsAccordion.tsx`
- Modify: `SmartCompareApp/src/components/results/DimensionBars.tsx`
- Modify: `SmartCompareApp/src/components/results/ConfidencePills.tsx`
- Modify: `SmartCompareApp/src/components/results/ConfidenceDetailsSheet.tsx`
- Modify: `SmartCompareApp/src/components/results/FactualVerdict.tsx`
- Create: `SmartCompareApp/src/lib/performance/wallTimeInstrumentation.ts`
- Modify: `SmartCompareApp/src/services/api.ts` (SSE timing hooks)
- Create: `SmartCompareApp/__tests__/ResultsContent.v2Wiring.test.tsx`

### Task L3.1: Wire `variant` string on product card

**Files:**
- Modify: `SmartCompareApp/src/components/results/ResultsContent.tsx`

**Step 1:** Failing Jest test:

```tsx
import { render } from "@testing-library/react-native";
import ResultsContent from "../src/components/results/ResultsContent";

test("renders variant string when backend provides it", () => {
  const props = {
    response: {
      overview: {
        products: [
          { name: "iPhone 15", variant: "128GB · Black", price: { amount: 329, currency: "BHD" } },
          { name: "Galaxy S24", variant: "128GB · Onyx", price: { amount: 299, currency: "BHD" } },
        ],
      },
      // ...
    },
  };
  const { getByText } = render(<ResultsContent {...props} />);
  expect(getByText("128GB · Black")).toBeTruthy();
  expect(getByText("128GB · Onyx")).toBeTruthy();
});
```

**Step 2:** Run, FAIL.

**Step 3:** Add variant render in product card JSX:

```tsx
<Text style={styles.variant}>{product.variant}</Text>
```

with styles aligning to design Screen 1.

**Step 4:** PASS.

**Step 5:** Commit.

### Task L3.2: Per-row emerald winner highlighting in specs table

**Files:**
- Modify: `SmartCompareApp/src/components/results/ResultsAccordion.tsx`

**Step 1:** Failing Jest test asserting that specs cells get `style.color = emerald` when their `winner` field matches the cell's product index.

**Step 2:** Modify specs table renderer:

```tsx
{specs_comparison.map((row, i) => (
  <View key={i} style={styles.row}>
    <Text style={[styles.cell, row.winner === 0 && styles.winnerEmerald]}>{row.p0_value}</Text>
    <Text style={styles.label}>{row.field.toUpperCase()}</Text>
    <Text style={[styles.cell, row.winner === 1 && styles.winnerEmerald]}>{row.p1_value}</Text>
  </View>
))}
```

**Step 3:** Add `winnerEmerald: { color: theme.colors.emerald, fontWeight: "700" }` to styles.

**Step 4:** PASS.

**Step 5:** Commit.

### Task L3.3: Winner-star in pros/cons accordion

**Files:**
- Modify: `SmartCompareApp/src/components/results/ResultsAccordion.tsx`

**Step 1:** Failing test for star rendering when `is_winner: true`.

**Step 2:** Add `<Star />` icon prefixing the winning product's name in the pros/cons block.

**Step 3:** PASS.

**Step 4:** Commit.

### Task L3.4: Per-retailer review quote block (Screen 2)

**Files:**
- Modify: `SmartCompareApp/src/components/results/ResultsAccordion.tsx`

**Step 1:** Failing test:

```tsx
test("renders 3 retailer quotes with rating + text", () => {
  const props = {
    response: {
      reviews: {
        products: [
          {
            retailer_quotes: [
              { retailer: "Amazon", rating: 5, text: "Battery actually lasts a full day, even with heavy use." },
              { retailer: "Noon", rating: 4, text: "Camera in low light is the best I've used at this price." },
              { retailer: "X", rating: 5, text: "Switched from iPhone after 4 years. No regrets." },
            ],
          },
        ],
      },
    },
  };
  const { getByText } = render(<ResultsAccordion {...props} />);
  expect(getByText(/Battery actually lasts/i)).toBeTruthy();
  expect(getByText("AMAZON")).toBeTruthy();
});
```

**Step 2:** PASS by adding retailer-quote block to the Reviews accordion render.

**Step 3:** Commit.

### Task L3.5: Confidence pills + tap-to-reveal sheet wiring

**Files:**
- Modify: `SmartCompareApp/src/components/results/ConfidencePills.tsx`
- Modify: `SmartCompareApp/src/components/results/ConfidenceDetailsSheet.tsx`

**Step 1:** Failing test asserting pill renders with level + opens sheet with confidence_details on tap.

**Step 2:** Wire `response.scoring_v2.confidence_legs` → pills; `response.scoring_v2.confidence_details` → sheet content.

**Step 3:** PASS.

**Step 4:** Commit.

### Task L3.6: Dimension bars use new v2 dimensions (category-aware)

**Files:**
- Modify: `SmartCompareApp/src/components/results/DimensionBars.tsx`

**Step 1:** Failing test ensuring bars render with electronics-specific labels (Camera, Battery, Storage, etc.) not generic (Price, Reviews).

**Step 2:** Update bar renderer to use `dim.label` from v2 + `dim.winner` for emerald coloring.

**Step 3:** Verify FactualVerdict component renders `factual_verdict.line1` + `line2`.

**Step 4:** PASS.

**Step 5:** Commit.

### Task L3.7: Wall-time instrumentation hook

**Files:**
- Create: `SmartCompareApp/src/lib/performance/wallTimeInstrumentation.ts`
- Modify: `SmartCompareApp/src/services/api.ts` (streamComparison)
- Modify: `SmartCompareApp/src/screens/ResultsScreen.tsx`

**Step 1:** Failing test asserting timings get logged to Sentry tags:

```tsx
test("logs frontend wall-time stages to Sentry", async () => {
  const sentrySpy = jest.spyOn(Sentry, 'setTag');
  await renderResultsScreen(/* ... */);
  expect(sentrySpy).toHaveBeenCalledWith('wall_time.ttfb_ms', expect.any(Number));
  expect(sentrySpy).toHaveBeenCalledWith('wall_time.first_card_visible_ms', expect.any(Number));
  expect(sentrySpy).toHaveBeenCalledWith('wall_time.all_cards_visible_ms', expect.any(Number));
  expect(sentrySpy).toHaveBeenCalledWith('wall_time.ready_celebration_ms', expect.any(Number));
  expect(sentrySpy).toHaveBeenCalledWith('wall_time.user_tappable_ms', expect.any(Number));
});
```

**Step 2:** Implement:

```typescript
// wallTimeInstrumentation.ts
import * as Sentry from "@sentry/react-native";

export class WallTimeTracker {
  private startTime: number = 0;
  private milestones: Record<string, number> = {};
  
  start() {
    this.startTime = Date.now();
    this.milestones = {};
  }
  
  mark(stage: 'ttfb' | 'first_card_visible' | 'all_cards_visible' | 'ready_celebration' | 'user_tappable') {
    const elapsed = Date.now() - this.startTime;
    this.milestones[stage] = elapsed;
    Sentry.setTag(`wall_time.${stage}_ms`, elapsed.toString());
  }
  
  report() {
    Sentry.captureMessage('comparison_wall_time', {
      level: 'info',
      tags: this.milestones,
    });
  }
}
```

**Step 3:** Wire `start()` at the moment user taps Compare. `mark('ttfb')` when first SSE event arrives. `mark('first_card_visible')` when first product card animates in. `mark('all_cards_visible')` when both cards present. `mark('ready_celebration')` when the 3-part celebration fires. `mark('user_tappable')` when accordions become tappable.

**Step 4:** PASS.

**Step 5:** Commit.

### Task L3.8: L3 owner QAs L4's prompt-builder integration (per matrix)

**Files:** read-only review

Same pattern as L1.11 — verify prompt builder loads pain_workflow_priors, validation matrix authored, Instagram feasibility test runs cleanly.

### Task L3.9: Lane 3 device walkthrough script

**Files:**
- Create: `docs/plans/2026-06-08-A-L3-device-walkthrough.md`

Step-by-step manual device test covering all 4 design screens + 88s instrumentation tag inspection. Result populates dispatcher's cross-QA gate.

Commit milestone:

```bash
git commit --allow-empty -m "milestone(L3): mobile v2 renders + 88s instrumentation — ready for L2 cross-QA"
```

---

## Lane 4 — Prompts + Validation Matrix + Instagram Feasibility (Opus #4, ~3 days)

**Goal:** ETL survey responses into pain_workflow_priors, inject into verdict prompt, run 50-query Bahrain validation matrix, run Instagram/TikTok feasibility test.

**Worktree:** `../smartcompare-A-L4` on `feature/A-L4-prompts-eval`

**Files affected:**
- Create: `scripts/etl_survey_to_priors.py`
- Create: `data/pain_workflow_priors.json`
- Create: `data/decision_style_priors.json`
- Modify: `app/services/prompt_personalities.py`
- Modify: `app/services/extraction_service.py` (`build_verdict_prompt`)
- Create: `docs/plans/2026-06-08-A-validation-matrix-50q.md`
- Create: `scripts/run_validation_matrix.py`
- Create: `docs/plans/2026-06-08-A-instagram-feasibility-test.md`

### Task L4.1: Survey ETL → pain_workflow_priors.json

**Files:**
- Create: `scripts/etl_survey_to_priors.py`
- Create: `data/pain_workflow_priors.json`

**Step 1:** Failing test:

```python
def test_pain_workflow_priors_has_8_workflows():
    priors = json.load(open("data/pain_workflow_priors.json"))
    assert len(priors["workflows"]) == 8
    assert priors["workflows"][0]["rank"] == 1
    assert priors["workflows"][0]["name"] == "close_option_paralysis"
    assert "prompt_instruction" in priors["workflows"][0]

def test_decision_style_priors_per_cohort():
    priors = json.load(open("data/decision_style_priors.json"))
    # 4-tier preference: show 2-3 / show only differences / suggest one / show all
    for cohort_key in ["18-24_male_bahraini", "25-34_female_bahraini", "35-44_male_non-bahraini"]:
        assert cohort_key in priors
        styles = priors[cohort_key]
        assert sum(styles.values()) == pytest.approx(1.0, abs=0.01)
```

**Step 2:** Implement ETL script that reads:
- `C:/Users/SynAckITPC/Downloads/SURVEY RESPONSES/Fillout ENG results (2).csv`
- `C:/Users/SynAckITPC/Downloads/SURVEY RESPONSES/Fillout arab results (9).csv`

Aggregates the columns:
- "Q7 At what point did the choice feel hardest?" → workflow type counts
- "What were the top 2 difficulties you faced..." → workflow weight
- "Which style of assistance..." → decision_style preference
- "Which of the following best describes you?" + "What is your age group?" + "What is your gender?" → cohort key

Emits 2 JSON files:
- `data/pain_workflow_priors.json` (8 workflows ranked + prompt instructions per design § 6)
- `data/decision_style_priors.json` (cohort → style preference distribution)

**Step 3:** Run script, generate files. Commit:

```bash
python scripts/etl_survey_to_priors.py
git add data/pain_workflow_priors.json data/decision_style_priors.json scripts/etl_survey_to_priors.py tests/
git commit -- data/ scripts/ tests/ -m "feat(L4): survey ETL → pain_workflow + decision_style priors (400+ responses)"
```

### Task L4.2: Inject pain-workflow instructions into verdict prompt

**Files:**
- Modify: `app/services/extraction_service.py` (`build_verdict_prompt` or equivalent)

**Step 1:** Failing test:

```python
def test_verdict_prompt_includes_top_3_pain_workflows():
    prompt = build_verdict_prompt(category="electronics", product_type="electronics.phone", user_cohort={"age_group": "25-34", "gender": "Female"})
    assert "tie-break" in prompt.lower() or "if X" in prompt
    assert "MAX 3 differences" in prompt or "max 3" in prompt.lower()
    assert "value" in prompt.lower() and "budget" in prompt.lower()

def test_verdict_prompt_no_scary_copy():
    prompt = build_verdict_prompt(category="electronics", ...)
    forbidden = ["couldn't", "try again", "Failed to", "تعذر", "فشل"]
    for word in forbidden:
        assert word not in prompt
```

**Step 2:** Implement prompt builder that loads pain_workflow_priors, picks top 3 for cohort, injects as constraints. Also load cohort_priors for context.

**Step 3:** PASS.

**Step 4:** Commit.

### Task L4.3: 50-query Bahrain validation matrix authoring

**Files:**
- Create: `docs/plans/2026-06-08-A-validation-matrix-50q.md`
- Create: `scripts/run_validation_matrix.py`
- Create: `data/validation_gold_truth.json`

**Step 1:** Author the doc listing all 50 queries (per design § 8) with expected outcomes (Ahmed manually fills the gold-truth JSON for current Bahrain retail prices via lulu.com.bh / sharafdg.com manual verification — this is a 2-hour task).

**Step 2:** Implement run script:

```python
# scripts/run_validation_matrix.py
import json, requests, time

QUERIES = json.load(open("data/validation_gold_truth.json"))

results = []
for q in QUERIES:
    start = time.time()
    resp = requests.get(f"https://web-production-58776.up.railway.app/api/v1/text/compare", params={
        "q": q["query"], "region": "bahrain", "nocache": "true"
    })
    wall = time.time() - start
    d = resp.json()
    
    # Score per axis
    price_ok = is_price_within_15pct(d, q["expected_prices"])
    specs_ok = is_specs_correct(d, q["expected_specs"])
    winner_ok = d["overview"]["winner"]["product_index"] == q["expected_winner_index"]
    factual_ok = no_hallucinated_facts(d, q["forbidden_facts"])
    wall_ok = wall <= 25.0
    
    weighted = (0.25 * price_ok) + (0.25 * specs_ok) + (0.30 * winner_ok) + (0.20 * factual_ok)
    results.append({**q, "weighted_score": weighted, "wall_s": wall, ...})

# Aggregate
pass_rate = sum(1 for r in results if r["weighted_score"] >= 0.80) / len(results)
print(f"Pass rate: {pass_rate:.1%}")
assert pass_rate >= 0.80, "Validation matrix BELOW gate — block merge"
```

**Step 3:** PASS gate when ≥80% of queries score ≥0.80 weighted.

**Step 4:** Commit.

### Task L4.4: Instagram/TikTok 5-query feasibility test

**Files:**
- Create: `docs/plans/2026-06-08-A-instagram-feasibility-test.md`
- Create: `scripts/instagram_feasibility_test.py`

**Step 1:** Manual test plan: pick 5 queries (1 fragrance, 1 makeup, 1 fashion, 1 electronics gadget, 1 supplement). For each:
- Open Instagram, search brand main @account
- Note: did brand main provide unique product info NOT in Serper/Reddit/YouTube?
- Open 3 GCC influencer/reviewer accounts in category. Same check.
- Same for TikTok.
- Score 1–5 per query.

**Step 2:** Author findings to doc. Decision rule: if ≥3/5 queries score ≥3 → green-light Apify integration in B.4. Else cut.

**Step 3:** Commit decision into design § 10 update.

### Task L4.5: L4 owner QAs L1's `build_dimensions_v2` rewrite (per matrix)

**Files:** read-only review of L1 worktree

Same pattern. Verify v2 dimensions match CATEGORY_DIMENSIONS for all 9 categories; spot-check delta_text quality; run L1's test suite.

### Task L4.6: Lane 4 milestone commit

```bash
git commit --allow-empty -m "milestone(L4): pain-workflow prompts + 50-query validation gate + Instagram feasibility test — ready for L3 cross-QA"
```

---

## Cross-QA + Merge Gate (Day 12–14, all 4 owners)

### Task M1: Dispatcher confirms all 4 lanes have cross-QA PASS verdicts

**Step 1:** Dispatcher checks task matrix in TaskList. Every cross-QA pair (L1↔L2, L2↔L3, L3↔L4, L4↔L1) must have explicit PASS in task comments.

**Step 2:** Any SUBPAR verdict → work sent back to original lane owner. No merge until ALL PASS.

### Task M2: Run 50-query validation matrix on integrated branch

**Step 1:** Dispatcher creates `feature/A-integration` from main; merges L1 + L2 + L3 + L4 sequentially (path-restricted, conflict-resolved by domain ownership):

```bash
git checkout -b feature/A-integration main
git merge --no-ff feature/A-L1-v2-adapter
git merge --no-ff feature/A-L2-parallel-races
git merge --no-ff feature/A-L3-mobile-renders
git merge --no-ff feature/A-L4-prompts-eval
```

**Step 2:** Run validation matrix against the integrated branch (Railway preview env):

```bash
python scripts/run_validation_matrix.py --env preview
```

Expected: pass_rate ≥80%.

**Step 3:** If <80%, root-cause failures, dispatch targeted fixes per lane, re-merge, re-run. Per Team Execution Contract: NOT disassembled until 100%.

### Task M3: Sentry + Supabase audit gates

**Step 1:** Confirm `mcp__plugin_sentry_sentry__search_issues` returns no new error patterns introduced by integration (post-deploy 15-min watch).

**Step 2:** Supabase audit: verify no schema migrations pending, no FK violations introduced.

**Step 3:** Commit audit findings to dispatcher session log.

### Task M4: Merge to main + deploy

**Step 1:** Final merge:

```bash
git checkout main
git merge --no-ff feature/A-integration -m "Merge Sprint A — backend comparison overhaul (Lanes 1+2+3+4)"
git push origin main
```

**Step 2:** Railway auto-deploys backend in ~90s. Verify via `/health`.

**Step 3:** EAS update mobile to preview channel:

```bash
cd SmartCompareApp
eas update --branch preview --message "Sprint A: backend comparison overhaul + mobile v2 renders + 88s instrumentation"
```

**Step 4:** Force-close + reopen device (two-launch propagation per memory). Verify Wave-1 success.

### Task M5: Device walk + go/no-go for production

**Step 1:** Ahmed runs device walkthrough doc from L3.9.

**Step 2:** If GREEN across all 4 design screens + 88s instrumentation tags present + no Sentry regressions → promote EAS update to production channel.

**Step 3:** Worktree cleanup:

```bash
git worktree remove ../smartcompare-A-L1
git worktree remove ../smartcompare-A-L2
git worktree remove ../smartcompare-A-L3
git worktree remove ../smartcompare-A-L4
git branch -d feature/A-L1-v2-adapter feature/A-L2-parallel-races feature/A-L3-mobile-renders feature/A-L4-prompts-eval feature/A-integration
```

**Step 4:** TeamDelete on the 4-Opus team.

---

## Bundle B Outline (Detailed plan in separate doc, ~6–8 weeks)

After (A) ships and runs for 1 week:

- **B.1 — DB + observability schema** (1 week): audit current `users.preferences` / `comparison_feedback` / `user_events` / `cohort_priors.json`. New tables: `user_preference_history`, `pain_workflow_events`, `verdict_critiques`, `eval_runs`. New `comparison_feedback` columns: `winner_correct`, `price_correct`, `specs_correct`.
- **B.2 — Living Prompt System full** (1.5 weeks): few-shot rotation cron, anti-pattern injection from eval failures, self-critique pass with canary flag.
- **B.3 — Reasoning depth experiments** (1 week): production-wide self-critique if eval lift ≥3%; o3-mini canary; multi-agent split prototype.
- **B.4 — Social-source layer** (2 weeks): Reddit OAuth, YouTube Data API, Fragrantica/INCIDecoder/PubMed direct scrapers, Instagram/TikTok via Apify (if A-L4.4 feasibility test passed).
- **B.5 — Bahrain cultural layer** (1 week): halal cert, climate flags, Ramadan framing, Arabic-content weighting, GCC luxury secondary market.
- **B.6 — 95% accuracy eval pipeline** (continuous): CI eval on every PR; production 5% sampling; weekly `/admin/accuracy` report.

A separate writing-plans pass will produce the detailed Bundle (B) implementation plan once (A) ships and B.1 DB audit completes.

---

## Open items (carried from design § 13)

1. Survey #2 ETL output spec — finalised in L4.1.
2. Bahrain-specific brand inclusion list — Claude drafts in L2.2; Ahmed ratifies before merge.
3. Halal certification source — single DB or composite (B.5).
4. Apify cost ceiling — canary-limited at 10% in B.4.
5. `o3-mini` API access — verify before B.3.
6. Eval gold-set authorship — Ahmed authors in L4.3 (50 queries); 200-query gold set deferred to B.6.

---

Plan complete and saved to `docs/plans/2026-06-08-backend-comparison-overhaul-plan.md`. Two execution options:

**1. Subagent-Driven (this session)** — I dispatch fresh subagent per task, review between tasks, fast iteration. Sprint (A) plan has ~55 numbered tasks across 4 lanes + cross-QA gate. Subagent-driven is well-suited for this since each task is bounded (TDD red-green-commit pattern) and dispatcher (me) reviews + merges.

**2. Parallel Session (separate)** — Open new session with `superpowers:executing-plans` skill, batch execution with checkpoints between lanes.

Which approach?
