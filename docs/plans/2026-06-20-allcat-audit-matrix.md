# All-9-Category Render Audit Matrix (Task B2, Phase 1 — AUDIT-ONLY)

> **Owner:** be-render (team catfix). **Status:** Phase 1 complete (audit-only / read).
> **Scope:** verify each of the 9 categories renders its TRUE structure once the
> per-product `category` is correct (be-core A3/A4 write-back). NO shared-file edits
> here — proposed fixes below are GO-gated (Phase 2).
>
> **Method:** every cell verified against real code by reading the definition + the
> render path AND by running the deterministic functions ($0, no API). Repro harness
> = `tests/test_all_category_render.py` (be-render-owned).

## Render-path source of truth (verified)

| Surface | Function | Keys off | File:line |
|---|---|---|---|
| Hero/dimension bars + breakdown | `compute_scores` → `breakdown` | `CATEGORY_DIMENSIONS[cat]` via `_DIMENSION_SIGNAL_MAP[cat]` | `scoring_service.py:1099,1693-1701` |
| v2 dimensions tab | `build_dimensions_v2` | `CATEGORY_DIMENSIONS[cat]` (3 core + 5 contextual, cap 8) | `scoring_service.py:3055-3077` |
| "At a glance" block | `build_category_profile` | `CATEGORY_SPEC_SCHEMAS[cat]` (schema order, populated subset) | `extraction_service.py:877-889` |
| Side-by-side Specs table | `extract_specs` filter | `CATEGORY_SPEC_SCHEMAS[cat]` (schema order) | `extraction_service.py:982-998` |
| Specs **prompt** (extraction depth) | `_build_specs_prompt` | **`PRODUCT_TYPE_SCHEMAS[subtype]`** (overrides cat) ELSE `CATEGORY_SPEC_SCHEMAS[cat]` | `extraction_service.py:439-443` |
| Like-for-like fairness basis | `fairness_for_category` | `CATEGORY_FAIRNESS[cat]` (`unit=None` → no caption) | `price_service.py:1640-1649` |

**Keystone (shipped prior bundle):** all six surfaces `canonicalize_category()` the
input, so a capital-cased / synonym category routes correctly. This catfix bundle's
write-back (A3/A4) sets `products[i]["category"] = category_used` so `compute_scores`
(`products_data[0]["category"]`) and `_fetch_product_data → result["category"]` (→
`extract_specs`/profile/sources) all read the resolved category. **The render machinery
below is correct; the bug being fixed is upstream routing, not these definitions.**

---

## THE MATRIX

Legend: ✅ correct · ⚠️ gap (see notes) · n/a not applicable.

| # | category | dims == `CATEGORY_DIMENSIONS`? | spec-schema (schema order, no leak)? | At-a-glance correct? | fairness basis (`CATEGORY_FAIRNESS`)? | residual gap |
|---|----------|:---:|:---:|:---:|:---:|---|
| 1 | electronics | ✅ (6 dims, weights Σ=1.0) | ✅ filter in schema order | ✅ | ✅ `GB` / "storage (GB)" (discrete) | ⚠️ **G1** subtype-filter drop (tv/laptop/etc.) |
| 2 | grocery | ✅ | ✅ | ✅ | ✅ `net` / "net weight/volume" | ⚠️ **G1** (oil/tea/chocolate) |
| 3 | supplements | ✅ | ✅ | ✅ | ✅ `count` / "unit count" (discrete) | ⚠️ **G1** (protein/preworkout fully dropped) |
| 4 | makeup | ✅ | ✅ | ✅ | ✅ `volume` / "volume/weight" | ⚠️ **G1** (foundation/lipstick/mascara) |
| 5 | skincare | ✅ | ✅ | ✅ | ✅ `volume` / "volume/weight" | ⚠️ **G1** (serum/sunscreen/cleanser) |
| 6 | haircare | ✅ | ✅ | ✅ | ✅ `volume` / "volume (ml)" | ⚠️ **G1** (shampoo) + **G2** label "Scent" |
| 7 | fragrances | ✅ (longevity/projection/character) | ✅ | ✅ | ✅ `ml` / "volume (ml)" (continuous) | ⚠️ **G1** partial (9/12 survive) — `longevity_hrs`/`volume_ml` dropped |
| 8 | fashion | ✅ | ✅ | ✅ | ✅ `unit=None` → NO like-for-like caption | ⚠️ **G1** (bag/shoe/watch fully dropped) |
| 9 | other | ✅ (6 dims) | ✅ | ✅ | ✅ `unit=None` → NO caption | ⚠️ **G3** minor `build_dimensions_v2` dim redundancy |

**Structural baseline (all $0-verified):** all 9 categories are keys in
`CATEGORY_DIMENSIONS`, `CATEGORY_DIMENSION_WEIGHTS`, `_DIMENSION_SIGNAL_MAP`,
`CATEGORY_SPEC_SCHEMAS`, `CATEGORY_FAIRNESS`; every dims list = 6 keys with weights
summing to 1.0; `build_category_profile` renders in schema order with ZERO
cross-category leakage; `fairness_for_category` resolves canonical + falls back to the
`unit=None` "other" spec for unknown/None. **The category-routing layer this bundle
fixes is sound — the matrix is GREEN on dims/profile/fairness for all 9.**

---

## GAPS (proposed fixes — Phase 2, GO-gated; NOT applied)

> **DISPATCHER RULING (2026-06-20): G1 = DEFERRED to its own follow-on bundle.**
> Rationale (confirmed): pre-existing + orthogonal to this bundle's explicit-pair/vision
> category-ROUTING fix (G1 also hits the already-correct `q=` parser path, so folding it
> in would muddy the clean smoke20 no-regression story); fragrances render correctly
> WITHOUT it; large blast radius. **B2 Phase 2 shipped ZERO shared-file edits.** This
> section is the tracked carry-over: the evidence, the proposed-fix sketch, and the
> blast-radius list below are the follow-on's starting point. The pin
> `tests/test_all_category_render.py::test_G1_fragrances_survive_enough_for_this_bundle`
> guards that fragrances stay adequate; the `test_G1_subtype_fields_fully_dropped_*`
> parametrized test documents the live gap (flips RED — a prompt to write a survival guard
> — the day G1 is fixed).
>
> **➡️ DEFERRED FOLLOW-UP — "subtype spec-schema survival" (P1, ~$0, no Serper):** make
> `extract_specs`'s render filter use the SAME effective schema the prompt used (subtype
> when one was detected), so subtype-specific fields survive instead of being silently
> dropped. Scope below.

### ⚠️ G1 (HIGH severity, render correctness) — subtype prompt fields silently dropped by the category-schema filter — **[DEFERRED — see ruling above]**

**The bug.** `_build_specs_prompt` (`extraction_service.py:439-443`) prompts GPT with
`PRODUCT_TYPE_SCHEMAS[subtype]` field names when `detect_product_type` matches (it
matches for nearly every real query — see `PRODUCT_TYPE_KEYWORDS`). But `extract_specs`
(`extraction_service.py:982-998`) FILTERS the result to `CATEGORY_SPEC_SCHEMAS[category]`.
When the subtype field name ≠ a category-schema field name, **the extracted value is
silently discarded** → the Specs table + "At a glance" render empty/sparse even though
GPT successfully extracted the data.

**Evidence (real queries, $0 harness):**

| query | subtype fired | prompt fields | survive filter | rendered |
|---|---|:---:|:---:|---|
| Sony Bravia QLED | `electronics.tv` | 9 | **0** | EMPTY |
| Omega Seamaster watch | `fashion.watch` | 7 | **0** | EMPTY |
| Optimum whey protein | `supplements.protein` | 8 | **0** | EMPTY |
| Tom Ford Oud Wood EDP | `fragrances.edp` | 12 | 9 | partial (`longevity_hrs`,`projection_m`,`volume_ml` dropped) |
| iPhone 15 Pro | `electronics.phone` | 12 | 10 | OK (`5G`,`charging_w` dropped) |
| MacBook Air laptop | `electronics.laptop` | 10 | 5 | thin (`cpu`,`gpu`,`battery_hrs`,`ports`,`keyboard_layout` dropped) |

**Across ALL 34 subtypes: 157 prompted fields are dropped by the category filter.**
8 subtypes drop 100% of their fields (`electronics.tv/ac/washer/refrigerator`,
`supplements.protein/preworkout`, `fashion.watch`).

**Proof it's an unintended gap, not a definition choice:** `test_climate_spec_keys.py:7-8`
states *"the subtype path overrides the category list for nearly every real query, so a
category-only key would be dead"* — the authors hit exactly this and worked around it for
the 3 `heat_stability` keys by registering them in BOTH the category schema AND every
relevant subtype. Every other subtype field has NO such dual-registration → it's dropped.
The L2.12 tests (`test_specs_prompt_product_type_schema.py`) assert only the PROMPT side
(`capacity_kg in sys`), never that the field SURVIVES `extract_specs` — false confidence.

**Proposed fix (Phase 2 — needs `extraction_service.py` RELEASED + GO):** make the
`extract_specs` filter use the SAME schema the prompt used. Recompute the subtype via the
identical `detect_product_type(full_name, category)` → `get_schema_for_type(type_key)`;
when non-empty, filter+order on the subtype field list (union with category meta keys);
else keep `CATEGORY_SPEC_SCHEMAS[category]`. Then `build_category_profile` must render
subtype fields too (extend `_CATEGORY_PROFILE_LABEL_OVERRIDES` for the new keys, OR have
the profile read the same effective schema).

**Blast-radius (the follow-on must touch ALL of these — why it's its own bundle):**
this is a PRE-EXISTING gap in the L2.12 product-type layer — it also affects the
already-correct `q=` parser path, so it is *orthogonal* to this bundle's explicit-pair/
vision category routing. A complete fix touches:
- `extract_specs` filter (`extraction_service.py:982-998`) — the survival logic
- the `category_profile` Contract-1 surface (`build_category_profile`) — render subtype fields
- `_CATEGORY_PROFILE_LABEL_OVERRIDES` — humanized labels for the new subtype keys
  (`capacity_kg`→"Capacity (kg)", `screen_size`, `protein_g_serving`, `perfumer`, …)
- the FE generic `CategoryProfile` consumer + i18n `results.spec.<key>` (EN+AR) for new keys
- likely the `CATEGORY_FAIRNESS` extractors that key off category-schema field names
- the L2.12 tests (`test_specs_prompt_product_type_schema.py`) must add a SURVIVAL assertion
**DEFERRED per dispatcher ruling (above).** The catfix DoD's fragrance render is GREEN
without it (fragrances survive 9/12 incl. `scent_family`/notes/`sillage`/`concentration`);
the dropped `longevity_hrs`/`volume_ml` have category equivalents `longevity`/`volume`. So
**fragrances need NO G1 fix.** G1 is a general electronics/fashion/supplements problem.

### ⚠️ G2 (LOW, cosmetic) — haircare `scent` field label

`build_category_profile` labels `scent` via the snake→Title fallback → "Scent". Fine, but
the fragrance schema uses `scent_family`→"Scent family". No conflict; only flagging that
`scent` has no override entry (renders "Scent", acceptable). **No fix proposed.**

### ⚠️ G3 (LOW, cosmetic) — `other` category `build_dimensions_v2` dim redundancy

For `other`, `build_dimensions_v2` emits `['price','reviews','value','review','reliability','feature_match']`.
`review_score`→public "review" co-exists with the core `reviews` row (near-duplicate
label), and `function_score`/`build_score` are dropped (the first-5-non-core slice +
core-covered skip). This is the documented `other` behavior (the generic catch-all), not
a routing bug. **No fix proposed** — it only affects `category=other` (a true mystery
product), and the design says keep `other` as the generic fallback.

---

## What is NOT a gap (verified, do not "fix")

- **Spec schemas of differing length** (other=7, fashion/haircare=10, makeup=12). These
  are deliberate per-category definitions, not "too thin." `other`'s 7 is intentionally
  generic.
- **`extract_specs` filtering to the category schema** is the correct *render contract*
  (no leakage, schema order). The G1 bug is the prompt/filter *schema mismatch*, not the
  filtering itself.
- **fashion/other `unit=None`** → no like-for-like caption is correct by design
  (`CATEGORY_FAIRNESS` + `.design-sync` ResultsScreen reference: no basis caption for
  these two).
- **`build_dimensions_v2` capping at 8 rows** (3 core + 5 contextual) is the shipped
  S2 I3.4 decision.

---

## Phase-2 outcome (dispatcher-ruled 2026-06-20)

1. **G1** — real HIGH-severity render gap (empty spec tables for TV/watch/protein/etc.).
   **RULING: DEFERRED to a dedicated follow-on** (orthogonal to catfix's category routing;
   large blast radius across extract_specs + profile + labels + FE i18n + fairness).
   Fragrances do NOT need it for this bundle's DoD. Tracked above as the "subtype
   spec-schema survival" follow-up; pinned by the two `test_G1_*` tests.
2. **G2 / G3** — cosmetic, **no fix** (ruled).

**B2 Phase 2 = ZERO shared-file edits.** Only be-render-owned files were created/edited
(this matrix + `tests/test_all_category_render.py`).

**Net: the all-9 routing/dims/profile/fairness layer is GREEN. The one genuine render
gap (G1) is pre-existing, fragrance-irrelevant, and best handled as its own bundle.**
