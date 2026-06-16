# Fragrance Quality + Personalization + Results Redesign — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task (subagents in this session, review + commit between tasks).

**Goal:** Fix fragrance comparison content (C1–C6), restore personalization correctness (category canonicalization + cohort proof line), and rebuild the results page 1:1 with the design system — as one combined bundle.

**Architecture:** Backend keystone first — canonicalize `category` once at parse time so scent dimensions, scent spec schema, and priority reweighting all resolve correctly (fixes C3 + C4 + fragrance personalization together). Then fragrance content fixes, then emit the missing `cohort_summary` payload, then a FE rewire that swaps already-built-but-unused primitives into the live results screen.

**Tech Stack:** FastAPI / Python 3.12 (root `app/`), pytest; React Native / Expo (`SmartCompareApp/`), Jest, `tsc`.

**Design doc:** `docs/plans/2026-06-16-fragrance-quality-personalization-results-redesign-design.md` (root-cause evidence + decisions + file anchors).

**Sequencing (budget-aware, solo-first per design D6 — weekly at 91%):** Phase 1 keystone → 2 content → 3 cohort → 4 FE → 5 verify. Each task ends in a committed increment. Path-restricted commits. Free unit suite green before each commit.

---

## Phase 1 — KEYSTONE: category canonicalization (fixes C3, C4, fragrance personalization)

### Task 1.1: `canonicalize_category()` helper + unit test

**Files:**
- Modify: `app/services/extraction_service.py` (add module-level helper near `parse_product_query`)
- Test: `tests/test_category_canonicalization.py` (create)

**Step 1 — failing test:**
```python
# tests/test_category_canonicalization.py
import pytest
from app.services.extraction_service import canonicalize_category

@pytest.mark.parametrize("raw,expected", [
    ("Fragrances", "fragrances"),
    ("Fragrance", "fragrances"),
    ("perfume", "fragrances"),
    ("Perfume", "fragrances"),
    ("ELECTRONICS", "electronics"),
    ("smartphone", "electronics"),
    ("  Skincare ", "skincare"),
    ("Make Up", "makeup"),
    ("totally-unknown-thing", "other"),
    ("", "other"),
    (None, "other"),
])
def test_canonicalize_category(raw, expected):
    assert canonicalize_category(raw) == expected
```
Run: `python -m pytest tests/test_category_canonicalization.py -v` → Expected FAIL (no `canonicalize_category`).

**Step 2 — implement.** Add to `extraction_service.py`. The valid set MUST equal the 9 canonical categories used as `CATEGORY_DIMENSIONS` / `CATEGORY_SPEC_SCHEMAS` keys (verify exact keys when implementing): `electronics, grocery, supplements, makeup, skincare, haircare, fragrances, fashion, other`.
```python
_CATEGORY_SYNONYMS = {
    "fragrance": "fragrances", "perfume": "fragrances", "perfumes": "fragrances",
    "cologne": "fragrances", "eau de parfum": "fragrances", "edp": "fragrances", "edt": "fragrances",
    "phone": "electronics", "smartphone": "electronics", "mobile": "electronics",
    "laptop": "electronics", "tablet": "electronics", "gadget": "electronics", "gadgets": "electronics",
    "make up": "makeup", "make-up": "makeup", "cosmetics": "makeup",
    "hair care": "haircare", "skin care": "skincare", "supplement": "supplements", "groceries": "grocery",
}
_CANONICAL_CATEGORIES = {
    "electronics", "grocery", "supplements", "makeup",
    "skincare", "haircare", "fragrances", "fashion", "other",
}

def canonicalize_category(raw) -> str:
    if not raw or not isinstance(raw, str):
        return "other"
    c = raw.strip().lower()
    if c in _CANONICAL_CATEGORIES:
        return c
    if c in _CATEGORY_SYNONYMS:
        return _CATEGORY_SYNONYMS[c]
    # singular/plural tolerance
    if c.endswith("s") and c[:-1] in _CATEGORY_SYNONYMS:
        return _CATEGORY_SYNONYMS[c[:-1]]
    if c + "s" in _CANONICAL_CATEGORIES:
        return c + "s"
    return "other"
```
**Step 3 — run test → PASS.**
**Step 4 — commit:** `git commit -m "feat(category): canonicalize_category helper (keystone)" -- app/services/extraction_service.py tests/test_category_canonicalization.py`

### Task 1.2: Apply canonicalization at parse time + defensive guards

**Files (verify current lines before editing):**
- Modify: `app/services/structured_comparison_service.py` (~`:1836-1842` sync, ~`:2253-2259` streaming — where `category_used`/`detected_category` is set from `products[0].get("category")`)
- Modify (defensive `.lower()`/canonicalize at lookup): `app/services/scoring_service.py:~1062` (`compute_scores`) and `:~2909` (`build_dimensions_v2`); `app/services/extraction_service.py:~735` (`extract_specs` `schema_key`); `app/services/structured_comparison_service.py:~3059` (critical-field cascade)
- Test: `tests/test_category_canonicalization.py` (extend) + a scoring test asserting fragrance → scent dims

**Step 1 — failing test** (scoring path): build minimal `product_data` with `category="Fragrances"`, call `scoring_service.compute_scores`, assert the returned dimension keys are the fragrance scent set (`character_score`/`longevity_score`/`projection_score`/…), NOT `build_score`. Run → FAIL (currently falls to "other"→build).

**Step 2 — implement:** at the orchestrator parse sites, set `category_used = canonicalize_category(products[0].get("category"))` (import the helper). At each lookup site, canonicalize defensively before the `in CATEGORY_*` check. Keep `_product_category` (`:70`) consistent or route it through `canonicalize_category`.

**Step 3 — run scoring test + `tests/test_category_canonicalization.py` → PASS.**
**Step 4 — regression:** `python -m pytest tests/ -m "not (live_unit or live_db or integration)" --ignore=tests/test_integration.py -q` → no new failures (mind known RED-by-design `test_value_math.py`).
**Step 5 — commit** (path-restricted to the touched files + test).

### Task 1.3: Verify/extend fragrance priority adjustments (1b)

**Files:** `app/services/scoring_service.py` (`CATEGORY_PRIORITY_ADJUSTMENTS`, ~`:1191-1234` region)
- **Verify** a `fragrances` entry exists mapping the 8 user priorities onto scent dims. If missing/thin, add one (e.g. `quality`→longevity/projection, `durability`→longevity/wear_value, `latest_features`→character/presentation, `price`→wear_value).
- Test: a fragrance user with `priorities=["quality"]` produces non-trivial `applied_shifts` on scent dims; `scoring_method=="personalized"`.
- Commit.

---

## Phase 2 — Fragrance content fixes

### Task 2.1: C1 — price-pending presentation (decision D4)
**Files:** `app/services/price_service.py` (genuineness/sample detection), `app/services/response_builder.py` (set `price.unavailable` + reason), `app/services/structured_comparison_service.py` (propagate).
- Define genuine `source_method` set; when resolved price is `estimated`, fails the existing `is_implausible_*` guards (`price_service.py:526,565-596`), matches sample/decant signal (title keywords `sample|decant|tester|vial|\d+\s?ml` micro-size + per-ml sanity), or is absent → set `price = {..., "unavailable": True, "reason": "pending_genuine"}` and DO NOT emit an amount.
- Scope (D7): conditional on genuineness — genuine prices still emit normally.
- Tests: sample/estimated fragrance → `unavailable:true`; genuine BHD → amount shown; electronics genuine unaffected. No regression to `is_implausible_high_value_price` / wrong-SKU guard.
- Commit.

### Task 2.2: C2 — consistent size basis (decision D5)
**Files:** `app/services/structured_comparison_service.py` (post price-selection, pre-scoring), reading `price.size` (`price_service.py:1147-1148`).
- Prefer the canonical flagship size (100ml) consistently for BOTH products from already-fetched candidates (no extra live call). If still mismatched, the price is "pending" (Task 2.1), so no apples-to-oranges delta renders.
- Tests: mismatched sizes → either reconciled or both pending; never a delta across differing sizes.
- Commit.

### Task 2.3: C5 — review citation cleaning
**Files:** `app/services/review_service.py:~132-169` (regex `:151`, fields `:156-167`).
- Extend regex to also match bare `\[\d+\]`; scrub all review text fields (consensus + per-quote text), not only praises/complaints/highlights.
- Test: review text with `[2] [3] [snippet_4]` → all markers removed/attributed.
- Commit.

### Task 2.4: C6 — rating vs review-score reconciliation
**Files:** `app/services/scoring_service.py:~2358-2386` (`_dim_reviews`), reference `response_builder.py:99-102,1074-1080`.
- `_dim_reviews` must treat a `rating_derived`-flagged rating as missing → "Limited review data"; never assert "X stars higher" when a displayed rating is N/A.
- Test: one real rating + one derived → no star-delta text; "Limited review data".
- Commit.

---

## Phase 3 — Cohort proof line (decision D3)

### Task 3.1: Emit `cohort_summary`
**Files:** `app/services/response_builder.py` (`build_comparison_response`), source from cohort match (`structured_comparison_service.py:2654-2677` / `cohort_service`).
- Attach `cohort_summary = {"peer_count": int, "governorate": str}` at response root in the exact shape `SmartCompareApp/src/screens/ResultsScreen.tsx:774-791` reads. **Verify** the matched cohort prior carries a sample-size N for `peer_count`.
- Remove the false FE comment at `ResultsScreen.tsx:768`.
- Tests: response includes `cohort_summary` when demographics resolve; omitted/empty when not (badge hides).
- Commit.

### Task 3.2: Confirm `ENABLE_COHORT_PERSONALIZATION` (1d)
- Verify via Railway it is `true` in prod (CLAUDE.md says ON; code-default `false` at `extraction_service.py:1082-1084`). No code change unless off. Note finding in the commit/PR description.

---

## Phase 4 — Results page 1:1 redesign (Thrust 3) — FE

### Task 4.1: Dimension bars → single split + legend
Swap live `components/results/DimensionBars.tsx` to use `components/primitives/DimensionBar.tsx` (single grey-A‖emerald-B). FE computes share `score_a/(score_a+score_b)`. Add per-row "A · B" product-name legend. `tsc` + snapshot. Commit.

### Task 4.2: Confidence pills → dot+label
Swap `components/results/ConfidencePills.tsx` to `components/primitives/ConfidencePill.tsx`; map `strong/acceptable/weak` → `High/Medium/Low` with "· Level" suffix. `tsc` + snapshot. Commit.

### Task 4.3: Price-pending UI
Wire `price.unavailable` → engaging line in the product-pair price slot (`ResultsContent.tsx:117-121` `formatPrice` + `:253-262`); suppress the Price dimension bar + Price confidence pill when pending; keep price out of verdict prose. EN/AR i18n (no-scary; no "estimated"). Commit.

### Task 4.4: Cohort proof box + TopMatchBadge + specs table
- Restyle `CohortBadge.tsx` → subtle rounded box + "N+ shoppers in {governorate} leaned the same way"; renders from `cohort_summary`.
- `TopMatchBadge.tsx`: add ★ + uppercase.
- `ResultsAccordion.tsx:458-528` specs: restructure rows to value · centered-label · value (winner cell already emerald).
- Relocate `PersonalizationChip` directly under the "Why this fits you" headline.
- `tsc` + snapshots. Commit.

---

## Phase 5 — Verify & ship

### Task 5.1: Eval no-regression
- Create the proper smoke20 `--persist` baseline (deferred B2): `python -m scripts.eval_runner --subset smoke20 --persist` (sandbox-disabled, `--concurrency 1`). If box can't DNS-reach Supabase, insert the `eval_runs` row via Supabase MCP (project `qulajmyxdbdkchvecmvc`). Record run-id; update `docs/runbooks/qaren-eval.md` + CLAUDE.md eval-gate note.
- Run smoke20 regression against the new baseline → no regression.

### Task 5.2: Merge + deploy + on-device
- Merge `--no-ff` → `git push origin main` → Railway auto-deploys (~90s) → prod-smoke the Tom Ford curl.
- **On-device verify (loads ≠ correct):** scent dims (not Build), both products' specs populated, no raw `[N]`, consistent rating, "Weighted ↑…" chip + cohort line both render, no wrong fragrance price (price-pending line).
- Ahmed fires warmer cron + `ENABLE_PRICE_CACHE_WARMER` (out of scope here).

---

## Definition of Done
Scent dims for fragrances; both products' specs populated; no raw citations; rating consistent with review-score; personalization chip + cohort proof line render for a logged-in-with-prefs user; no wrong fragrance price (price-pending instead); results page matches the mockups; `npx tsc --noEmit` clean; free unit suite green; smoke20 no-regression; no forbidden vocab (EN/AR).
