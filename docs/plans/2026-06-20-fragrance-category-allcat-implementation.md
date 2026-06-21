# Category Resolution + All-Category Render Correctness — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (or superpowers:subagent-driven-development for a same-session team) to implement this plan task-by-task.
>
> **v2 (2026-06-20):** revised after an adversarial 4-lens plan review (workflow `wf_0a49790d-765`).
> Applied: the team-model serialization blocker fix + 5 must-edits + sharpening edits. Diff-worthy
> changes are tagged `[REVIEW]`.

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

**Reference docs (read all three before starting):**
- Design: `docs/plans/2026-06-20-fragrance-category-allcat-design.md`
- Verified line-level findings (workflow `wf_01a4745e-9ac`): `docs/plans/2026-06-20-fragrance-category-fix-plan.md`
- (This doc supersedes its own v1; the review that produced v2 is `wf_0a49790d-765`.)

---

## ⚠️ Load-bearing constraints (violating any of these = broken fix)

1. **`products[i]["category"]` ≠ `category_used`.** Scoring (`compute_scores` reads
   `products_data[0]["category"]`, scoring_service.py:1067; `build_dimensions_v2` :3051), spec-schema
   selection, and category-aware source discovery all key off the **per-product** field via
   `_fetch_product_data → result["category"]` (:2890/:2903). The resolved category MUST be written onto
   `products[0]/[1]["category"]` **before the `_fetch_product_data` gather** (sync ~`1924`, stream ~`2370`).
   **Pin with a `_fetch_product_data` capture test, NOT a `category_used` assertion.**
2. **Circular import:** `classify_category_from_text` lives in `extraction_service.py`; `price_service.py:16`
   already imports `extraction_service`. Import `is_supplement_query` **inside the function**, never at
   module level.
3. **Sync + stream duplicate the category logic but are NOT byte-identical.** `[REVIEW]` The SYNC path has
   `_partial_build_ctx` machinery (init ~1807, update ~1900-1905 with `category_used/switched/original`)
   that the STREAM path lacks. Patch the category-resolution + write-back logic in BOTH; do **not** copy the
   `_partial_build_ctx` block into the stream path, and in the sync path KEEP the ~1900-1905 ctx update
   consuming the newly-resolved `category_used`. Pin parity with a test.
4. **Two AI-origin rating paths — both must be made honest.** `[REVIEW]`
   - **(a) `derive_rating_from_scores`** (response_builder.py:159) mutates the product at :1144-1150 and lives
     ONLY in the final `build_comparison_response` → the SSE intermediate `reviews` event (~2474) is already
     honest for THIS path; the fix is the projection guard.
   - **(b) `gpt_review_aggregate`** (structured_comparison_service.py:3362-3376) runs INSIDE
     `_fetch_product_data`, so its GPT-**estimated** rating + count are on the product dict BEFORE the SSE
     reviews event fires — it leaks into the intermediate event too. Fix it **at the source** (set
     `rating_derived=True` at ~3368-3370) so every downstream guard catches it for free.
5. **Keep the real `review_count`; null the fabricated one.** `[REVIEW]` A review_count from a real rating
   provider is preserved. The `gpt_review_aggregate` `total_reviews` (an LLM ESTIMATE promoted to
   review_count — the "2,187 reviews" in the repro) is NOT real → null/flag it with its rating in A5.
6. **Do NOT break the SSE path.** The SSE `reviews` event emits the REAL `None` rating for the
   `derive_rating_from_scores` path (constraint #4a). Don't introduce a derived value there.
7. **Deployed backend is root `app/`** — never edit `backend/app/`.
8. **Line numbers drift** — every task: `grep`/Read to confirm the anchor before editing.

---

## Team model & discipline (per Ahmed) + `[REVIEW]` race mitigation

- **4-Opus worktree team, Opus only** (no sonnet/haiku), `mode: "bypassPermissions"`.
- **100% complete before disassembly.** No partial merges.
- **Cross-QA:** each member QAs another member's work before sign-off; subpar/missed work is **sent back**
  with specifics. The dispatcher verifies contested "complete" claims against the actual commit
  (`git show`), never the report.
- **Idle members** either write red-green tests toward **80%** *in a test file they own* (see ownership
  table) or wait for their QA to return.
- **Work is delegated** — owners below.

### 🚧 `[REVIEW R4-1 BLOCKER]` Shared-file ownership + serialization (prevents git-index race)

A parallel team in one worktree WILL corrupt the index if two agents edit one file at once. Two files are
shared: **`extraction_service.py`** (be-core A1/A2/A2b + be-render B1) and **`scoring_service.py`**
(be-core A5 + be-render B2). Hard rules the dispatcher enforces:

| File | Sole owner until released | Released to | When |
|------|---------------------------|-------------|------|
| `app/services/extraction_service.py` | **be-core** | be-render (B1) | after A1+A2+A2b committed |
| `app/services/structured_comparison_service.py` | **be-core** | — (be-core only) | n/a |
| `app/services/scoring_service.py` | **be-core** (A5) | be-render (B2 approved fixes) | after A5 committed |
| `app/services/response_builder.py` | **be-core** | — | n/a |
| `app/services/scrapedo_service.py` + `price_service.py` | **be-core** (A7) / shared read | be-render (B2 price gaps) | after A7 committed |
| `SmartCompareApp/**` | **fe** | — | n/a |

**Rule:** be-render does **audit-only** (read) on shared files until be-core releases them, then
**rebases before editing**. The dispatcher serializes the two handoffs. (Alternative if you'd rather not
serialize: run the whole bundle **solo/sequential** — that's the verified-findings recommendation and is
cheaper; the file dependencies make solo low-risk.)

### Workstream owners & cross-QA assignments

| WS | Owner | Scope | QA'd by |
|----|-------|-------|---------|
| **A** | `be-core` | `resolve_category` + classifier + write-back (sync/stream/vision) + rating-provenance (both paths) + variant-NA + Scrape.do metering | `be-render` |
| **B** | `be-render` | All-9 audit matrix (AUDIT-ONLY first) + approved residual fixes + fragrance schema Part A | `be-core` |
| **C** | `test` | Red-green tests to 80% in C-owned files; owns the no-regression gate run | `fe` |
| **D** | `fe` | FE null-default (conditional send) + nudge + FE tests + the single end-to-end prod verification | `test` |

### `[REVIEW R4-9]` New-test-file single ownership (third collision vector)

| Test file | Sole owner |
|-----------|-----------|
| `tests/test_explicit_pair_category.py` | be-core (A3/A4) |
| `tests/test_resolve_category.py` | be-core (A2/A2b) |
| `tests/test_rating_provenance.py` | be-core (A5/A6) |
| `tests/test_all_category_render.py` | be-render (B2) |
| existing files (test_scrapedo_service.py, test_decomposed_services.py, …) | the task that edits them |

`test` (C) owns ONLY the gate run + coverage backfill in files no active task holds. Idle members never edit
a test file owned by an active task.

### Dependency graph

```
A1 (classifier) -> A2 (resolve_category) -> A2b (GPT-mini) -> A3 (write-back sync) -> A4 (write-back stream)
A5 (rating-provenance, both paths) ── be-core, response_builder + scoring + structured_comparison
A6 (variant-NA) ── be-core, response_builder
A7 (scrapedo metering) ── be-core, fully independent
B1 (scent_family) ── be-render; INERT until A3/A4; needs extraction_service RELEASED by be-core
B2 (all-9 audit) ── be-render; AUDIT-ONLY until A* committed; approved fixes need scoring/extraction RELEASED
D1 (FE null-default) ── fe; independent
C* (gate) ── runs last
```
**Critical path:** A1 → A2 → A2b → A3 → A4 → (be-core releases shared files) → B1/B2 approved fixes → C gate.

---

## Prerequisites (dispatcher, once)

```bash
git worktree add -b feature/category-allcat-fix ../smartcompare-catfix main   # absolute path; verify with `git worktree list`
```
Free unit-test command:
```bash
python -m pytest tests/<file> -v -m "not (live_unit or live_db or integration)"
```
No-regression gate (run before final sign-off; `[REVIEW R4-3]` FULL UUID required):
```bash
python -m pytest tests/ -v -m "not (live_unit or live_db or integration)" --ignore=tests/test_integration.py
python -m scripts.eval_runner --subset smoke20 --mode regression \
  --baseline-run-id 54b603e8-4eab-41c9-a34d-a5e391446559 --concurrency 1   # dispatcher GO (Serper)
```
> `[REVIEW R3-3]` **The smoke20 gate is a NO-REGRESSION guard for the parser (`q=`) path ONLY.**
> `eval_runner` hits `GET /text/compare?q=…` → `parse_product_query()`, which is NOT the path this bundle
> fixes (explicit_pair + vision). **Winner-rate is EXPECTED to stay flat** — a flat number is NOT "the fix
> didn't work." The load-bearing coverage for THIS fix = the sync+stream `_fetch_product_data` capture tests
> + the fragrance-dims unit test + D2's single explicit-pair cold probe.

Commit convention (team session): `git commit -m "msg" -- <paths>`. End messages with the project
`Co-Authored-By` line.

---

# Workstream A — `be-core`

## Task A1: Deterministic category classifier

**Files:** Modify `app/services/extraction_service.py` (fn next to `canonicalize_category` ~760; `_CATEGORY_SYNONYMS`
~679-728, `_CANONICAL_CATEGORIES` ~675 exist); Test `tests/test_category_canonicalization.py`.

`[REVIEW R1-1]` **The deterministic layer only recognizes generic category WORDS, not brand/model strings.**
A bare brand/model with no category word (`iPhone`, `Galaxy`, `Tom Ford Soleil Neige`) is EXPECTED to return
`"other"` and is resolved by the chip (A3) or the A2b GPT-mini escalation. **Do NOT widen `_CATEGORY_SYNONYMS`
with brand/model names** (brittle, unbounded).

**Step 1 — failing test** (`tests/test_category_canonicalization.py`):
```python
import pytest
from app.services.extraction_service import classify_category_from_text

@pytest.mark.parametrize("text,expected", [
    ("Dior Sauvage perfume", "fragrances"),
    ("Creed Aventus cologne", "fragrances"),
    ("Tom Ford Oud Wood EDP", "fragrances"),     # 'edp' token
    ("NOW Foods Vitamin D3", "supplements"),
    ("gaming laptop", "electronics"),            # 'laptop' token (confirm it's in synonyms; else use a token that is)
    ("iPhone 15 Pro", "other"),                  # [REVIEW] brand/model only -> 'other' (chip/A2b resolves)
    ("Tom Ford Soleil Neige 100ml", "other"),    # [REVIEW] no category word -> 'other'
    ("plain mystery object", "other"),
    ("", "other"),
    (None, "other"),
])
def test_classify_category_from_text(text, expected):
    assert classify_category_from_text(text) == expected
```
> Before asserting a token (`laptop`, `perfume`), grep `_CATEGORY_SYNONYMS` to confirm it's present; only
> assert tokens that exist (or add genuinely-generic ones — never brand names).

**Step 2 — run, expect FAIL** (`ImportError`): `python -m pytest tests/test_category_canonicalization.py -k classify -v`

**Step 3 — implement** (after `canonicalize_category`):
```python
def classify_category_from_text(text: str) -> str:
    """Cheap deterministic product-type -> canonical category. $0, no LLM.
    Recognizes generic category WORDS only (perfume/cologne/edp/laptop/vitamin...),
    NOT brand/model strings. Returns "other" when nothing matches (caller honors a
    chip or escalates to A2b)."""
    if not isinstance(text, str) or not text.strip():
        return "other"
    from app.services.price_service import is_supplement_query  # function-local: avoids circular import
    if is_supplement_query(text):
        return "supplements"
    import re as _re
    low = text.lower()
    for token in sorted(_CATEGORY_SYNONYMS, key=len, reverse=True):
        if _re.search(rf"\b{_re.escape(token)}\b", low):
            return _CATEGORY_SYNONYMS[token]
    return "other"
```
> `[REVIEW R3-7]` Optional: add whole-word single tokens `oud`, `eau` → `fragrances` (collapsed multi-word
> keys like `eaudeparfum` are inert against spaced raw text; `parfum` already catches "eau de parfum"). If you
> add them, add a spaced-multi-word test case.

**Step 4 — run, expect PASS. Step 5 — commit** `-- app/services/extraction_service.py tests/test_category_canonicalization.py`.

## Task A2: `resolve_category()` precedence helper

**Files:** Modify `app/services/extraction_service.py`; Test `tests/test_resolve_category.py` (NEW, be-core-owned).

`[REVIEW R2-4]` **Detection input is the product NAMES**, not the (about-to-be-overwritten) `category` field —
classify on `f"{products[0]['search_query']} {products[1]['search_query']}"` (or per-product, take a confident
hit). Returns `(category, switched, needs_llm)`:
- `det = classify_category_from_text(<combined names>)`; `sel = canonicalize_category(selected_category) if selected_category else None`
- if `det != "other"`: use `det`; `switched = bool(sel and sel != det)`; `needs_llm = False`
- elif `sel and sel != "other"`: use `sel`; `switched = False`; `needs_llm = False`
- else: `("other", False, True)` ← escalation sentinel (blind detection AND no chip)

**Tests:** keyword wins; chip used when detection blind; confident detection overrides a conflicting chip
(`switched=True`); `selected_category="other"`/unknown never clobbers a confident detection; blind+no-chip
returns `needs_llm=True`; `[REVIEW R2-4]` a mixed-token pair (one fragrance name + one ambiguous) still
resolves both. TDD → commit.

## Task A2b: Bounded GPT-mini escalation (classify-only)

**Files:** Modify `app/services/extraction_service.py` (`classify_category_llm(texts)`); Test
`tests/test_resolve_category.py` (mock OpenAI).

`[REVIEW R3-4]` **MUST be a NEW classify-only OpenAI call — NOT `parse_product_query`.**
`tests/test_two_input_shape.py::test_parse_product_query_not_called_for_explicit_pair` asserts
`parse_product_query` await_count==0 on the explicit_pair path and **must stay green**.
- Fires ONLY when `needs_llm` (blind AND no chip). gpt-4o-mini, ~100 tokens, returns one of the 9 canonical
  keys → `canonicalize_category` it; any error/timeout → `"other"`.
- **Tests (mocked OpenAI):** "Tom Ford Soleil Neige" → `fragrances`; NOT called when detection confident or a
  chip is set (sibling test).

## Task A3: Wire resolution + WRITE-BACK into the SYNC path

**Files:** Modify `app/services/structured_comparison_service.py` (sync vision ~`1849`, explicit ~`1864`,
resolution ~`1889-1895`, write-back before gather ~`1924`); Test `tests/test_explicit_pair_category.py` (NEW, be-core-owned).

**Step 1 — failing CAPTURE test (the load-bearing proof — this, not the dims test, proves the write-back):**
```python
import asyncio, pytest
from unittest.mock import patch
from app.services.structured_comparison_service import get_comparison_service

def test_explicit_pair_selected_category_is_authority_sync():
    svc = get_comparison_service()
    captured = []
    async def fake_fetch(product_info, *a, **k):           # matches _fetch_product_data(self, product_info, region, ...)
        captured.append(dict(product_info))
        raise RuntimeError("stop after capture")           # capture happens BEFORE the raise
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
> `[REVIEW R1-5]` The RuntimeError may be swallowed by the L2.7 hard-cap wrapper; the assertion relies on the
> capture happening BEFORE the raise, not on the exception surfacing. That's intentional.

**Step 2 — run, expect FAIL** (captured categories are `"other"`).
**Step 3 — implement:** replace the binary at ~1849 + ~1864 with `classify_category_from_text(<text>)`; replace
the resolution block to call `resolve_category(...)` (+ A2b when `needs_llm`); set `category_used`,
`category_switched`, `original_category`; `[REVIEW R4-5]` KEEP the ~1900-1905 `_partial_build_ctx.update`
consuming the resolved `category_used`; **write-back** `products[0]["category"] = products[1]["category"] = category_used`
immediately before the `_fetch_product_data` gather (~1924).
**Step 4 — PASS. Step 5 — commit.**

`[REVIEW R3-9/R4-8]` Sibling **routing sanity check** (label it as such — it duplicates
`tests/test_category_keystone_scoring.py`, it is NOT the write-back proof): feed two `category="fragrances"`
dicts to `ScoringService().compute_scores`, assert breakdown includes `longevity_score`/`projection_score`,
excludes `build_score`. Also add: classifier-without-chip cases, supplements-still-classified.

## Task A4: Mirror into the STREAMING path

**Files:** Modify `structured_comparison_service.py` (stream vision ~`2303`, explicit ~`2317`, resolution
~`2341-2347`, write-back ~`2370`); Test `tests/test_explicit_pair_category.py`.
`[REVIEW R4-5]` **Apply the SAME category-resolution + write-back logic — NOT a byte-copy.** The stream path has
NO `_partial_build_ctx` block; do not add one. Add `test_streaming_explicit_pair_selected_category_is_authority`
(capture harness on `compare_from_text_streaming`, async-gen) + a **sync/stream parity** test (same input → same
`category_used`).

## Task A5: Rating-provenance suppression — BOTH AI-origin paths `[REVIEW]`

**Files:** Modify `app/services/response_builder.py` (overview proj ~`1243`, reviews proj ~`1312`, `_safe_rating`
~`516`), `app/services/scoring_service.py` (`_dim_value` ~`2505-2538`), `app/services/structured_comparison_service.py`
(`gpt_review_aggregate` ~`3362-3376`); Tests `tests/test_rating_provenance.py` (NEW, be-core-owned), extend
`tests/test_decomposed_services.py`, `tests/test_dim_reviews_derived_rating.py`.

1. **Projections:** `"rating": (None if pd.get("rating_derived") is True else pd.get("rating"))` at ~1243 and
   ~1312. Keep `review_count` from real providers. **Keep the internal mutation at 1144-1150**
   (`test_decomposed_services.py:299` asserts it) — change only the PROJECTION.
2. `[REVIEW R2-1/R4-7]` **Guard inside `_safe_rating`** (NOT `_rating_candidate`): `if p.get("rating_derived") is True: return None`.
   `_safe_rating` is the single chokepoint for BOTH `_rating_candidate` (line1, ~556) AND `_format_line2`
   (line2, ~777), so this fixes both. Verify the line1 price/dim fallback (~816-829) still fires.
3. `_dim_value` (~2521): add the `rating_derived` guard `_dim_reviews` already has (~2476-2479) so synthetic
   ratings take the "Limited value data" path.
4. `[REVIEW R3-5]` **`gpt_review_aggregate` at SOURCE** (~3368-3370): set `rating_derived=True` (so the
   projection/`_safe_rating`/`_dim_value`/`_dim_reviews` guards ALL catch it for free) AND null/flag the
   GPT-estimated `review_count` (`total_reviews`). This also cleans the SSE intermediate event (constraint #4b).

**Tests:** derived rating NOT in overview/reviews projection; `_safe_rating` returns None on derived;
**verdict line1 AND line2** contain no "stars higher"/"rates higher" when both ratings derived; `[REVIEW R3-6]`
`_dim_value` test fixture sets numeric ratings + valid positive prices on BOTH + `rating_derived=True` (so it
fails before, passes after) + a real-ratings-still-produce-a-delta regression; gpt_review_aggregate rating NOT
forwarded + its count not presented as counted; **real rating still renders** (no regression). Do NOT alter the
SSE path for the derive path (#4a/#6).

## Task A6: Variant "N/A" leak

**Files:** Modify `response_builder.py` `_compose_variant_string` (~`276-290`); reuse `_SPEC_NA_TOKENS` (~`315`).
Test `tests/test_rating_provenance.py`. Skip values whose lowercased form ∈ `_SPEC_NA_TOKENS`
(`"n/a"`,`"unknown"`,`"-"`,`"none"`), not just `None/""/[]`. Test: literal `"N/A"` specs → no `"N/A · N/A"` variant.

## Task A7: Scrape.do Piece A — cost-header metering `[REVIEW R1-2/R3-1/R3-2]`

**Files:** Modify `app/services/scrapedo_service.py` (`render_page_with_status` ~`104-138`),
`app/services/structured_comparison_service.py` (`_scrapedo_scraper` ~`832-842`); Tests
`tests/test_scrapedo_service.py` (**all** unpack sites) + `tests/test_cache_first_render_gate.py` (mocks).

- `render_page_with_status` returns `(html, status, cost)`.
  - `cost = 0` on the **no-request** paths (token-missing ~108, TimeoutException ~135, generic Exception ~138 —
    no `resp`, 0 credits billed).
  - `cost = int(resp.headers.get("Scrape.do-Request-Cost", 5))` (fallback 5, wrap parse) ONLY where `resp`
    exists (200-with-html, 200-no-content, billed non-200 400/404/410).
- `_scrapedo_scraper`: `record_usage("scrapedo", count=cost)`; also `record_usage` (NOT failure) for billed
  200/400/404/410.
- **Update EVERY 2-tuple unpack** (`grep "html, status = await .*render_page_with_status"` repo-wide — do NOT
  touch firecrawl's separate `scrape_page_with_status`): all 9 sites in `tests/test_scrapedo_service.py`
  (incl. the 3 standalone methods ~265/279/303) + the 3 `AsyncMock(return_value=(None,0))` in
  `tests/test_cache_first_render_gate.py` → `(None,0,0)`. **Add `test_cache_first_render_gate.py` to the
  no-regression list.**
- **Pin:** timeout → `(None,0,0)`; 200 header `"25"` → `(html,200,25)`; 200 header missing → `(html,200,5)`.

> **⚠️ SHIPPED NOTE — A7 intentionally CHANGED Scrape.do burn semantics (CLEANUP-4c).** Pre-A7 the
> meter recorded a FLAT 1 credit and only on HTTP 200. Post-A7 the meter records the REAL credit cost
> from the `Scrape.do-Request-Cost` header (a `render=true` request is ~5, fallback 5) AND it now records
> usage on **billed non-200 responses too** (400/404/410/429/503 — Scrape.do charges for these). Net: the
> `budget:scrapedo:*` counter rises FASTER and more accurately than before. This is deliberate (the old
> meter under-counted spend and ignored billed failures); the monthly Scrape.do cap (900/mo) is now hit on
> true spend. Transient 429/503/0 still also `record_failure` for the circuit breaker. If a future audit
> sees the Scrape.do counter climbing faster than the old baseline, this is why — not a regression.

---

# Workstream B — `be-render`

## Task B1: Fragrance schema Part A (scent_family + honesty) — INERT until A3/A4; needs extraction_service RELEASED

**Files:** Modify `app/services/extraction_service.py` (PREFERRED `~234`; DYNAMIC fragrance guidance `~464`);
Tests `tests/test_critical_schema_fields_split.py` (`~57-65`), `tests/test_category_selection.py` (`~196-199`).
`[REVIEW]` `scent_family` is already in `CATEGORY_SPEC_SCHEMAS["fragrances"]:169` — B1 adds it to PREFERRED only.
- Add `"scent_family"` to PREFERRED (rides the existing batched `_smart_fallback_extract` — NOT the per-field
  NON_NEGOTIABLE fan-out). **Assert it is NOT in NON_NEGOTIABLE**; keep `NON_NEGOTIABLE["fragrances"]==
  {concentration, longevity}` byte-stable.
- Add a null-when-unknown honesty clause to the DYNAMIC fragrance prompt line (cache prefix intact). Test the
  rendered prompt contains `scent_family` + the clause.
> ⚠ Wait for be-core to RELEASE `extraction_service.py` (after A1/A2/A2b committed), then rebase before editing.

## Task B2: All-9-category render audit — `[REVIEW R4-2]` AUDIT-ONLY first, GO-gated fixes

**Files:** Create `tests/test_all_category_render.py` (be-render-owned). **No edits to
`scoring_service.py`/`extraction_service.py`/`price_service.py` without dispatcher GO** (those are be-core's
until released; a "too-thin schema" may be a deliberate definition, not a bug).

**Phase 1 (audit-only):** for EACH of the 9 categories (electronics, grocery, supplements, makeup, skincare,
haircare, fragrances, fashion, other) with a representative explicit pair, produce a **9-row matrix** +
`docs/plans/2026-06-20-allcat-audit-matrix.md`:
| category | dims == CATEGORY_DIMENSIONS? | spec-schema (schema order) correct? | At-a-glance correct? | fairness basis (CATEGORY_FAIRNESS) correct? | proposed fix (if gap) |
1. `compute_scores` breakdown keys == `CATEGORY_DIMENSIONS[category]`.
2. `extract_specs` selects `CATEGORY_SPEC_SCHEMAS[category]`; renders in SCHEMA ORDER; no other-category leakage.
3. `CATEGORY_FAIRNESS[category]` basis applied (fashion/other → None → no like-for-like caption).
4. `[REVIEW R4-6]` Optional visual cross-check: `.design-sync/staging/ui_kits/mobile/ResultsScreen.jsx`
   (Glob for it; duplicates under `docs/claude-design-handoff/`). Prefer $0 unit/scoring assertions.

**Phase 2 (GO-gated):** present proposed gap fixes to the dispatcher. Each APPROVED fix = a discrete sub-task
with its own TDD cycle, applied AFTER be-core releases the shared file. Keep definitions; fix only genuine bugs.

---

# Workstream C — `test` (target 80%, all $0)

Own the no-regression gate run + coverage backfill in files **no active task owns** (see ownership tables —
do NOT append to be-core/be-render test files). Run the gate: full free unit suite + smoke20 baseline
`54b603e8-4eab-41c9-a34d-a5e391446559` (NO-REGRESSION for the parser path only; winner-rate EXPECTED flat —
see Prerequisites). `[REVIEW R3-3]` Optionally add a **mocked `explicit_pair` integration test** ($0) that
drives `compare_from_text(explicit_pair=…)` and asserts the scoring breakdown is fragrance dims — closes the
e2e gap with no Serper cost. If any WS is <80% on its new code, send it back.

---

# Workstream D — `fe` (needs EAS to reach devices)

## Task D1: Remove the silent 'electronics' default + conditional send + nudge `[REVIEW R3-8/R4-4]`
**Files:** Modify `SmartCompareApp/src/screens/HomeScreen.tsx` (`~105`: `useState<string | null>(null)`;
**make `selected_category` conditional** — omit the key when `selectedCategory` is null at BOTH `~303`
(stream options) and `~404` (url body), e.g. `...(selectedCategory ? { selected_category: selectedCategory } : {})`).
`CategorySelector` already renders nothing-selected. Add a non-blocking "Pick a category for the most accurate
compare" hint when `selectedCategory == null`.
> Non-load-bearing: the backend treats null/`"other"`/unknown as no-opinion and the URL path ignores it
> (follow-on #8), so this FE/EAS leg cannot block the backend fix.
**Tests:** default is null; no `selected_category` key sent until a chip is tapped; nudge shows when null, hides
when selected. Run `npx tsc --noEmit` (ground truth). **Then** dispatcher fires
`cd SmartCompareApp && eas update --branch preview` after merge.

## Task D2: End-to-end verification (single cold probe, dispatcher GO)
After A/B merge + deploy, ONE cold prod probe on a FRESH fragrance pair (`?nocache=true`): confirm
`category_used="fragrances"`, fragrance dims, genuine BH price source, no fabricated rating. Everything else =
unit/scoring assertions (Serper budget).

---

## Definition of Done (before disassembly)

- [ ] **Capture test green (the write-back proof):** explicit fragrance pair → `products[i]["category"]=="fragrances"`
      (sync AND stream). (A green fragrance-dims test alone is NOT proof — it's a routing sanity check.)
- [ ] Fragrance pair renders fragrance dims (character/longevity/projection…), NOT `other` dims.
- [ ] 9-row audit matrix complete; every approved residual gap fixed (GO-gated); definitions preserved.
- [ ] No derived/estimated rating shown as authoritative anywhere — overview, reviews, verdict **line1 AND
      line2**, `_dim_value`, AND the `gpt_review_aggregate` path (fixed at source). Real `review_count` preserved;
      gpt-estimate count nulled/flagged.
- [ ] Variant "N/A" leak gone; `scent_family` in PREFERRED (+ honesty clause); Scrape.do meters real cost
      (0 on no-request paths) — all 12 unpack/mocks updated; firecrawl untouched.
- [ ] FE: no silent default; `selected_category` omitted when null; `npx tsc --noEmit` clean.
- [ ] Coverage ≥80% on new code; full free unit suite green; smoke20 vs `54b603e8-4eab-41c9-a34d-a5e391446559`
      no regression (winner-rate flat is EXPECTED).
- [ ] Every workstream cross-QA'd by its assigned reviewer; sent-back items resolved; shared-file handoffs
      serialized (no concurrent edits to extraction_service.py / scoring_service.py).
- [ ] EAS `preview` update fired for the FE change; one cold prod probe confirms the fragrance render.

---

## Execution handoff

Plan is dispatch-ready after this v2 revision. Per Ahmed: **4-Opus worktree team** (Opus only, cross-QA,
100%-before-disassembly) **with the `[REVIEW]` shared-file serialization rule** so be-render only touches
`extraction_service.py`/`scoring_service.py` after be-core commits A1/A2/A2b/A5. (Solo/sequential remains the
cheaper, lower-risk alternative if preferred.) Dispatcher: create the worktree, `TeamCreate` 4 Opus agents
(`be-core`/`be-render`/`test`/`fe`, `bypassPermissions`), enforce the file-ownership + new-test-file ownership
tables, serialize the two shared-file handoffs, and gate the Definition of Done against actual commits
(`git show`), not reports.
