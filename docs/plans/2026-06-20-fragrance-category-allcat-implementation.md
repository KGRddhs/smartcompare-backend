# Category Resolution + All-Category Render Correctness — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (or superpowers:subagent-driven-development for a same-session team) to implement this plan task-by-task.

**Goal:** Make every two-box / camera comparison render its TRUE category structure (a fragrance is a
fragrance, not `other`/electronics), with honest ratings and correct Bahrain price sourcing — all backend,
all $0.

**Architecture:** Replace the hardcoded `supplements/other` category binary on the explicit-pair + vision
paths with a shared `resolve_category()` (deterministic classifier + bounded GPT-mini + user-chip refine),
and **write the resolved category back onto `products[i]["category"]`** so scoring, spec-schema, and price
sources all key off it. Then audit all 9 categories render correctly, suppress AI-derived ratings shown as
real, and meter Scrape.do's true credit cost.

**Tech Stack:** Python 3.12 / FastAPI (root `app/`), pytest, React Native/Expo (`SmartCompareApp/`), Redis,
Serper/OpenAI/Scrape.do.

**Reference docs (read both before starting):**
- Design: `docs/plans/2026-06-20-fragrance-category-allcat-design.md`
- Verified line-level findings (every claim checked vs real code, workflow `wf_01a4745e-9ac`):
  `docs/plans/2026-06-20-fragrance-category-fix-plan.md`

---

## ⚠️ Load-bearing constraints (violating any of these = broken fix)

1. **`products[i]["category"]` ≠ `category_used`.** Scoring (`compute_scores` reads
   `products_data[0]["category"]`), spec-schema selection, and category-aware source discovery all key off
   the **per-product** field via `_fetch_product_data → result["category"]`. The resolved category MUST be
   written onto `products[0]/[1]["category"]` **before the `_fetch_product_data` gather** (sync ~`1924`,
   stream ~`2370`). **Pin with a `_fetch_product_data` capture test, NOT a `category_used` assertion.**
2. **Circular import:** `classify_category_from_text` lives in `extraction_service.py`; `price_service.py`
   already imports `extraction_service`. Import `is_supplement_query` **inside the function**, never at
   module level.
3. **Sync + stream are byte-duplicated.** Every category change exists twice
   (`compare_from_text` ~1768+ and `compare_from_text_streaming` ~2240+). Patch BOTH; pin parity.
4. **Do NOT break the SSE path.** The SSE `reviews` event (~`2474`) emits the REAL `None` rating BEFORE the
   derive mutation — it is already honest. The rating-provenance fix lives only in the final
   `build_comparison_response`.
5. **Keep the real `review_count`.** Only the synthetic/estimated RATING is suppressed.
6. **Deployed backend is root `app/`** — never edit `backend/app/`.
7. **Line numbers drift** — every task: `grep`/Read to confirm the anchor before editing.

---

## Team model & discipline (per Ahmed)

- **4-Opus worktree team, Opus only** (no sonnet/haiku), `mode: "bypassPermissions"`.
- **100% complete before disassembly.** No partial merges.
- **Cross-QA:** each member QAs another member's work before sign-off; subpar/missed work is **sent back**
  with specifics. The dispatcher verifies contested "complete" claims against the actual commit
  (`git show`), never the report.
- **Idle members** either write red-green tests toward the **80%** target or wait for their QA to return.
- **Work is delegated** — owners below.

### Workstream owners & cross-QA assignments

| WS | Owner | Scope | QA'd by |
|----|-------|-------|---------|
| **A** | `be-core` | `resolve_category` + classifier + write-back (sync/stream/vision) + rating-provenance + variant-NA + Scrape.do metering | `be-render` |
| **B** | `be-render` | All-9-category render audit matrix + residual per-category fixes + fragrance schema Part A | `be-core` |
| **C** | `test` | Red-green tests to 80% across all new code; owns the no-regression gate | `fe` |
| **D** | `fe` | FE null-default + nudge polish + FE tests + the single end-to-end prod verification | `test` |

### Dependency graph

```
A1 (classifier) ──> A2 (resolve_category) ──> A3 (write-back sync) ──> A4 (write-back stream)
                                                      │
A5 (rating-provenance) ─── independent of A1-A4, same files ──┐
A6 (variant-NA) ─── independent ──┐                           │
A7 (scrapedo metering) ─── fully independent ──┐              │
B1 (scent_family schema) ── INERT until A3/A4 ─┘              │
B2 (all-9 audit matrix) ── needs A3/A4 merged ───────────────┘
D1 (FE null-default) ── independent; integrates after A live
C* (tests) ── written alongside each WS; gate runs last
```
**Critical path:** A1 → A2 → A3 → A4 → B2. A5/A6/A7/D1 run in parallel. B1 can be written anytime but is
INERT (delivers nothing user-visible) until A3/A4 land, so it MUST ship in the same PR.

---

## Prerequisites (dispatcher, once)

```bash
# Absolute path; verify with `git worktree list` before dispatch
git worktree add -b feature/category-allcat-fix ../smartcompare-catfix main
```
Free unit-test command (used everywhere below):
```bash
python -m pytest tests/<file> -v -m "not (live_unit or live_db or integration)"
```
No-regression gate (run before final sign-off):
```bash
python -m pytest tests/ -v -m "not (live_unit or live_db or integration)" --ignore=tests/test_integration.py
python -m scripts.eval_runner --subset smoke20 --mode regression --baseline-run-id 54b603e8 --concurrency 1   # dispatcher GO required (Serper)
```
Commit convention (team session): `git commit -m "msg" -- <paths>` (the `--` is a path separator). End
messages with the project `Co-Authored-By` line.

---

# Workstream A — `be-core`

## Task A1: Deterministic category classifier

**Files:**
- Modify: `app/services/extraction_service.py` (add fn next to `canonicalize_category`, ~line 760; the
  synonym map `_CATEGORY_SYNONYMS` ~679-728 and `_CANONICAL_CATEGORIES` ~675 already exist)
- Test: `tests/test_category_canonicalization.py` (already covers `canonicalize_category`)

**Step 1 — failing test** (`tests/test_category_canonicalization.py`):
```python
import pytest
from app.services.extraction_service import classify_category_from_text

@pytest.mark.parametrize("text,expected", [
    ("Dior Sauvage perfume", "fragrances"),
    ("Creed Aventus cologne", "fragrances"),
    ("Tom Ford Oud Wood EDP", "fragrances"),
    ("iPhone 15 Pro", "electronics"),
    ("NOW Foods Vitamin D3", "supplements"),
    ("plain mystery object", "other"),
    ("", "other"),
    (None, "other"),
])
def test_classify_category_from_text(text, expected):
    assert classify_category_from_text(text) == expected
```

**Step 2 — run, expect FAIL** (`ImportError: cannot import name 'classify_category_from_text'`):
`python -m pytest tests/test_category_canonicalization.py -k classify -v`

**Step 3 — implement** (in `extraction_service.py`, after `canonicalize_category`):
```python
def classify_category_from_text(text: str) -> str:
    """Cheap deterministic product-type -> canonical category. $0, no LLM.
    Token-scans the existing synonym table + supplement heuristic.
    Returns "other" when nothing matches (caller decides whether to honor a
    selected_category or escalate)."""
    if not isinstance(text, str) or not text.strip():
        return "other"
    # supplements first (existing tuned heuristic). FUNCTION-LOCAL import:
    # price_service imports extraction_service at module load -> circular if top-level.
    from app.services.price_service import is_supplement_query
    if is_supplement_query(text):
        return "supplements"
    import re as _re
    low = text.lower()
    for token in sorted(_CATEGORY_SYNONYMS, key=len, reverse=True):
        if _re.search(rf"\b{_re.escape(token)}\b", low):
            return _CATEGORY_SYNONYMS[token]
    return "other"
```
> If `_CATEGORY_SYNONYMS` lacks fragrance breadth (e.g. `oud`, `eau`, `parfum`), add those keys mapping to
> `"fragrances"` (and any obvious electronics/beauty tokens) — but ONLY whole-word, and keep the existing
> `canonicalize_category` synonym contract intact (its test must stay green).

**Step 4 — run, expect PASS.** **Step 5 — commit** `-- app/services/extraction_service.py tests/test_category_canonicalization.py`.

## Task A2: `resolve_category()` precedence helper

**Files:** Modify `app/services/extraction_service.py` (add helper); Test `tests/test_resolve_category.py` (NEW)

**Behavior (detect-first, chip refines):**
- `det = classify_category_from_text(<combined product text>)`
- `sel = canonicalize_category(selected_category) if selected_category else None`
- If `det != "other"`: use `det`; `switched = bool(sel and sel != det)`.
- elif `sel and sel != "other"`: use `sel`; `switched = False`.
- else: return sentinel `("other", needs_llm=True)` so the caller can fire the bounded GPT-mini escalation
  (Task A2b) only when there's no chip and detection is blind.

**Step 1 — failing tests** (`tests/test_resolve_category.py`): keyword wins; chip used when detection blind;
confident detection overrides a conflicting chip (`switched=True`); `selected_category="other"`/unknown never
clobbers a confident detection; blind+no-chip returns the escalation sentinel.
**Steps 2-5:** implement the helper returning `(category, switched, needs_llm)`; run; commit.

## Task A2b: Bounded GPT-mini escalation (classify-only)

**Files:** Modify `app/services/extraction_service.py` (a tiny `classify_category_llm(texts)` — classify-only,
NOT the full `parse_product_query`); Test `tests/test_resolve_category.py` (mock the OpenAI call).
- Fires ONLY when `needs_llm` (blind detection AND no chip). gpt-4o-mini, ~100 tokens, returns one of the 9
  canonical keys → `canonicalize_category` the result; on any error/timeout fall back to `"other"`.
- **Test with the OpenAI client mocked** (no live call): assert it maps "Tom Ford Soleil Neige" → `fragrances`,
  and that it is NOT called when a chip is set or detection is confident.

## Task A3: Wire resolution + WRITE-BACK into the SYNC path

**Files:** Modify `app/services/structured_comparison_service.py` (sync vision `~1849`, explicit `~1864`,
resolution block `~1889-1895`, write-back before `_fetch_product_data` gather `~1924`); Test
`tests/test_explicit_pair_category.py` (NEW).

**Step 1 — failing CAPTURE test** (the load-bearing assertion):
```python
import asyncio, pytest
from unittest.mock import patch
from app.services.structured_comparison_service import get_comparison_service

def test_explicit_pair_selected_category_is_authority_sync():
    svc = get_comparison_service()
    captured = []
    async def fake_fetch(product_info, *a, **k):
        captured.append(dict(product_info))
        raise RuntimeError("stop after capture")  # short-circuit downstream
    with patch.object(svc, "_fetch_product_data", side_effect=fake_fetch):
        try:
            asyncio.run(svc.compare_from_text(
                query="Tom Ford Soleil Neige 100ml vs Tom Ford Oud Voyager 100ml",
                explicit_pair=("Tom Ford Soleil Neige 100ml", "Tom Ford Oud Voyager 100ml"),
                selected_category="fragrances",
            ))
        except Exception:
            pass
    assert captured, "_fetch_product_data was never reached"
    assert all(c.get("category") == "fragrances" for c in captured), \
        f"per-product category not written back: {[c.get('category') for c in captured]}"
```
**Step 2 — run, expect FAIL** (captured categories are `"other"`).
**Step 3 — implement:**
- Replace the binary at vision `~1849` and explicit `~1864` with `classify_category_from_text(<text>)`.
- Replace the resolution block `~1889-1895` to call `resolve_category(...)` (+ A2b escalation when
  `needs_llm`), set `category_used`, `category_switched`, `original_category`.
- **Write-back** (the fix): immediately after resolving and BEFORE the `_fetch_product_data` gather, set
  `products[0]["category"] = products[1]["category"] = category_used`.
**Step 4 — run, expect PASS.** **Step 5 — commit.**

Add sibling tests in the same file: classifier-without-chip (token-bearing pair → fragrances; no-token pair →
other); supplements still classified; **scoring dims** test — feed the two `category="fragrances"` product
dicts into `ScoringService().compute_scores` and assert the breakdown includes `longevity_score`/
`projection_score` and EXCLUDES `build_score` (mirror `tests/test_category_keystone_scoring.py`).

## Task A4: Mirror into the STREAMING path

**Files:** Modify `structured_comparison_service.py` (stream vision `~2303`, explicit `~2317`, resolution
`~2341-2347`, write-back `~2370`); Test `tests/test_explicit_pair_category.py`.
- Apply the IDENTICAL change. Add `test_streaming_explicit_pair_selected_category_is_authority` — same capture
  harness against `compare_from_text_streaming` (async-gen; iterate a few events inside try/except).
- **Parity guard:** a test asserting sync and stream produce the same `category_used` for the same input.

## Task A5: Rating-provenance suppression (honesty)

**Files:** Modify `app/services/response_builder.py` (overview projection `~1243`, reviews projection `~1312`,
`_safe_rating`/`_rating_candidate` `~516-571`), `app/services/scoring_service.py` (`_dim_value` `~2521`),
`app/services/structured_comparison_service.py` (`gpt_review_aggregate` promotion `~3362-3369`);
Tests `tests/test_decomposed_services.py`, `tests/test_dim_reviews_derived_rating.py` (extend),
new `tests/test_rating_provenance.py`.

**Changes (each its own TDD cycle):**
1. Overview + reviews projections: `"rating": (None if pd.get("rating_derived") is True else pd.get("rating"))`.
   Keep `review_count` untouched. (Keep the internal mutation at `1144-1150` so `test_decomposed_services.py:299`
   stays green — change only the PROJECTION.)
2. `_rating_candidate` (or `_safe_rating`): return `None` when either product `rating_derived is True` →
   verdict line1 can't emit "X stars higher" off a synthetic rating. Verify the price/dim fallback (`816-829`)
   still produces a sensible line1.
3. `_dim_value`: add the `rating_derived` guard already used by `_dim_reviews` (`scoring_service.py:2476-2479`)
   so synthetic ratings force the "Limited value data" path.
4. `gpt_review_aggregate` path: mark its GPT-estimated `average_rating`/`total_reviews` as estimated (flag) or
   `None` so the accordion header stops presenting an estimate as a counted volume. (GAP2 — second AI-origin path.)

**Tests:** derived rating NOT forwarded to overview/reviews; `_rating_candidate` returns None on derived;
`_dim_value` returns "Limited value data" when both ratings derived; **real rating still renders** (no
regression); gpt-aggregate count not presented as counted. Do NOT alter the SSE reviews event.

## Task A6: Variant "N/A" leak

**Files:** Modify `app/services/response_builder.py` `_compose_variant_string` (`~276-289`); reuse the existing
`_SPEC_NA_TOKENS` (`~315`). Test `tests/test_rating_provenance.py` or `tests/test_decomposed_services.py`.
- Skip values whose lowercased form is in `_SPEC_NA_TOKENS` (`"n/a"`, `"unknown"`, `"-"`, `"none"`), not just
  `None/""/[]`. Test: spec values of literal `"N/A"`/`"unknown"` produce no `"N/A · N/A"` variant.

## Task A7: Scrape.do Piece A — cost-header metering (independent, $0)

**Files:** Modify `app/services/scrapedo_service.py` (`render_page_with_status` `~113-121`),
`app/services/structured_comparison_service.py` (`_scrapedo_scraper` `~836-840`); Test
`tests/test_scrapedo_service.py` (the `TestRenderPageWithStatus` currently unpacks a 2-tuple — update it).
- `render_page_with_status` reads `resp.headers.get("Scrape.do-Request-Cost")`, parses int (fallback `5` when
  absent/non-numeric), returns `(html, status, cost)`.
- `_scrapedo_scraper`: `record_usage("scrapedo", count=cost)`; also `record_usage` (NOT failure) for billed
  200/400/404/410.
- Tests: header `25` → metered 25; header missing → fallback; billed-priceless path advances meter, not failure.

---

# Workstream B — `be-render`

## Task B1: Fragrance schema Part A (scent_family + honesty) — INERT until A3/A4

**Files:** Modify `app/services/extraction_service.py` (`CRITICAL_SCHEMA_FIELDS_PREFERRED["fragrances"]` `~234`;
DYNAMIC fragrance guidance line `~464`); Tests `tests/test_critical_schema_fields_split.py` (`test_fragrances_split`
`~57-65`), `tests/test_category_selection.py` (`~196-199`).
- Add `"scent_family"` to PREFERRED (rides the existing batched `_smart_fallback_extract` — NOT the per-field
  non-negotiable fan-out). **Assert `scent_family` is NOT in NON_NEGOTIABLE** (Serper-budget guard); keep
  `NON_NEGOTIABLE["fragrances"] == {concentration, longevity}` byte-stable.
- Strengthen the fragrance prompt line with a null-when-unknown honesty clause (in the DYNAMIC section so the
  OpenAI cache prefix stays intact). Test the rendered fragrance prompt contains `scent_family` + the clause.

## Task B2: All-9-category render audit matrix (needs A3/A4 merged)

**Files:** Create `tests/test_all_category_render.py`; fix residual gaps in
`scoring_service.py` / `extraction_service.py` / `price_service.py` as found (definitions stay — only fix
genuine bugs). Produce `docs/plans/2026-06-20-allcat-audit-matrix.md`.

For EACH of the 9 categories (electronics, grocery, supplements, makeup, skincare, haircare, fragrances,
fashion, other), with a representative explicit pair:
1. **Dims:** `compute_scores` breakdown keys == `CATEGORY_DIMENSIONS[category]` (top-4-by-weight feed hero bars).
2. **Spec schema:** `extract_specs` selects `CATEGORY_SPEC_SCHEMAS[category]`; "At a glance"/Specs render in
   SCHEMA ORDER; no other-category leakage.
3. **Fairness:** `CATEGORY_FAIRNESS[category]` basis applied (fashion/other → None → no like-for-like caption).
4. Cross-check vs the design-sync JSX refs (`.design-sync/`, `ui_kits/mobile/ResultsScreen.jsx`).

Record pass/fail per cell in the matrix; fix only real gaps (e.g. a too-thin spec schema, a wrong At-a-glance
field). Prefer `$0` unit/scoring assertions; one optional cold spot-probe per dispatcher GO.

---

# Workstream C — `test` (target 80%, all $0)

Own the suite. Write red-green tests alongside A/B (coordinate so you're not duplicating their TDD tests).
Net new coverage to own: the classifier matrix, `resolve_category` precedence + escalation (mocked OpenAI),
the `_fetch_product_data` capture (sync + stream + parity), fragrance-dims, rating-provenance (all 4
consumers), variant-NA, Scrape.do metering, and the all-9 render matrix. Run + own the **no-regression gate**
(full free unit suite + smoke20 baseline `54b603e8`). Report coverage %; if a WS is <80%, send it back.

---

# Workstream D — `fe` (needs EAS to reach devices)

## Task D1: Remove the silent 'electronics' default + nudge
**Files:** Modify `SmartCompareApp/src/screens/HomeScreen.tsx` (`~105`: `useState<string | null>(null)`);
verify `CategorySelector` renders nothing-selected cleanly (it already accepts `null`); add a non-blocking
"Pick a category for the most accurate compare" hint when `selectedCategory == null`. Confirm `selected_category`
is sent ONLY when set (`~303`, `~404`).
**Tests:** `SmartCompareApp/__tests__/...HomeScreen...` — default is null; no `selected_category` sent until a
chip is tapped; nudge shows when null and hides once selected. Run `npx tsc --noEmit` (ground truth).
**Then:** the dispatcher fires `cd SmartCompareApp && eas update --branch preview` after merge.

## Task D2: End-to-end verification (single cold probe, dispatcher GO)
After A/B merge to the worktree branch and deploy, run ONE cold prod probe on a FRESH fragrance pair
(`?nocache=true`) to confirm `category_used="fragrances"`, fragrance dims, genuine BH price source, no
fabricated rating. Prefer the unit/scoring assertions for everything else (Serper budget).

---

## Definition of Done (before disassembly)

- [ ] Capture test green: explicit fragrance pair → `products[i]["category"]=="fragrances"` (sync AND stream).
- [ ] Fragrance pair renders fragrance dims (character/longevity/projection…), NOT `other` dims.
- [ ] All-9 audit matrix complete; every residual gap fixed or explicitly accepted.
- [ ] No derived/estimated rating shown as authoritative anywhere (accordion, verdict line1, `_dim_value`,
      gpt-aggregate header); real `review_count` preserved.
- [ ] Variant "N/A" leak gone; `scent_family` in PREFERRED (+ honesty clause); Scrape.do meters real cost.
- [ ] FE: no silent default; `selected_category` sent only when chosen; `npx tsc --noEmit` clean.
- [ ] Coverage ≥80% on new code; full free unit suite green; smoke20 vs `54b603e8` no regression.
- [ ] Every workstream cross-QA'd by its assigned reviewer; sent-back items resolved.
- [ ] EAS `preview` update fired for the FE change; one cold prod probe confirms the fragrance render.

---

## Execution handoff

Plan complete. Per Ahmed's directive this executes as a **4-Opus worktree team** (Opus only, cross-QA,
100%-before-disassembly). Dispatcher: create the worktree, `TeamCreate` 4 Opus agents
(`be-core`/`be-render`/`test`/`fe`, `mode: bypassPermissions`), delegate the workstreams above with the
cross-QA matrix, and gate the Definition of Done against actual commits (`git show`), not reports.
