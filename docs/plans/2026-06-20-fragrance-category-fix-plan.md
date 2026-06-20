# Fragrance / Two-Box Category Fix — Verified Plan (2026-06-20)

**Repro:** Two-box compare "Tom Ford Soleil Neige 100ml" vs "Tom Ford Oud Voyager 100ml"
(+ `selected_category=fragrances`) renders **`other`-category dimensions** (Function / Build /
Review / Value / Reliability / Feature-match), a 1-dimension spec table, fabricated star ratings
(4.5 / 3.7) + an estimated "2,187 reviews" shown as real, and a card labelled 100ML over a 30ML
bottle image.

**Method:** Every audit finding was verified against the real code by a parallel agent fan-out
(9 agents, ~1.15M tokens) — confirming/refuting line-by-line. This doc records only what survived
verification. Source audit: user-supplied, 2026-06-20. Verification run: `wf_01a4745e-9ac`.

---

## TL;DR

- **Root cause (P0, CONFIRMED):** the explicit-pair (two-box) *and* vision (camera) product-resolution
  branches **skip the GPT parser** and hardcode `category = "supplements" if is_supplement_query else "other"`.
  `selected_category` is received but used **only to flip a display flag** (`category_switched`) — it is
  **never** the category authority.
- **The keystone nuance the audit under-specified:** scoring dims, the spec schema, *and* category-aware
  source discovery all key off **`products[i]["category"]`** (→ `_fetch_product_data` → `result["category"]`),
  **not** the request-level `category_used`. A fix that sets only `category_used` passes a `category_used`
  assertion and leaves all three broken. **The fix must write the resolved category back onto the product
  dicts before the `_fetch_product_data` gather.**
- **One fix unblocks five consumers:** correct per-product category simultaneously fixes (1) scoring dims,
  (2) the fragrance spec schema (2nd-product blank specs), (3) the critical-field fallback cascade,
  (4) the Bahrain fragrance Shopify/Algolia sources (P1-SOURCE-ROUTER is **entirely subsumed** — zero
  `source_router.py` edits), and (5) fragrance personalization.
- **Budget:** the whole P0 set is **$0 and Serper-*positive*** — with `category="other"`, `_pf_eligible`
  is TRUE and fires up to 4 speculative Serper discovery calls that still end at `estimated`; with the
  correct `fragrances` category those calls are **skipped** and the genuine BHD price comes from **free**
  `curl_cffi /products.json` + Algolia fetches. ≈ **−4 Serper calls per fragrance product.**
- **Honesty bugs ride the same PR:** turning on correct fragrance dims would *re-surface* fabricated
  ratings in the verdict ("X stars higher") unless the rating-provenance leak is fixed in the same change.

---

## What the audit got RIGHT vs WRONG (verification deltas)

| Finding | Verdict | Correction |
|---|---|---|
| **P0-CATEGORY** | ✅ Confirmed | Audit said "set `category_used`" — **trap**. Real authority is `products[i]["category"]`. Must write-back before the gather; pin with a `_fetch_product_data` *capture* test, not a `category_used` assert. |
| **P1-SOURCE-ROUTER** | ✅ Confirmed | **No `source_router.py` change** — entirely subsumed by P0. System is NOT "Serper-only": `fetch_shopify_price`/`fetch_algolia_price` are free `curl_cffi` direct fetchers. Add 3 registry-scoping *guard* tests only. |
| **P1-SCRAPEDO** | ⚠️ Confirmed → **P2** | Split: **Piece A** (read `Scrape.do-Request-Cost` header, meter real credits — $0, protective, ship-worthy; meter is ~5× low **today** on datacenter+render). **Piece B** (super/geoCode) is a **$249/mo Business-plan** feature that 401s on free tier (proven 2026-06-17) → dormant/deferred, never default-on. |
| **P1-UI-CONFIDENCE** | ⚠️ Partial | Audit blamed the FE accordion math — **wrong target**. Real defect is backend: `response_builder.derive_rating_from_scores` ships a synthetic rating with `rating_derived` **stripped** from the projections. `review_count` is **real — do NOT suppress it**. The "card N/A vs accordion 4.5" screenshot framing is stale (current card renders no rating row). Specs pill IS sparsity-blind (fact-check-only). |
| **P1-FRAGRANCE-SCHEMA** | ⚠️ Partial → **P2** | "Promote to non-negotiable, $0" is **false** — non-negotiable promotion fires a per-field Serper+GPT fan-out (~10 Serper/cold fragrance compare). `sillage`+`notes_*` are **already** in PREFERRED. Correct $0 scope: add **`scent_family`** to PREFERRED + a prompt honesty clause. **Inert until P0 lands.** |
| **P1-IMAGE-VARIANT** | ✅ Confirmed → **defer** | Feasible & cheaper than implied: requested size is in `full_name`, candidate size is in the Serper KG/Images `title` (both currently discarded). Reuse `extract_size_ml_any`/`values_within_tolerance`. Scope to fragrances first; never reject no-size candidates (fidelity > strictness). $0. |

**New issues discovered (not in the audit):**
- **DISC-MISSED A/B/C:** the fabricated rating leaks into (A) the reviews accordion stars, (B) the
  factual-verdict line1 ("X stars higher" — the C6 fix only patched `_dim_reviews`), and (C) the Value
  dimension (`_dim_value` computes value off a synthetic rating).
- **DISC-MISSED D:** "2,187 reviews" is a **GPT-estimated `total_reviews`** promoted to `review_count` as
  if counted — a **second** AI-origin rating/count path (`gpt_review_aggregate`) besides
  `derive_rating_from_scores`. Both bypass the "ratings never AI-generated" invariant.
- **DISC-MISSED E:** `_compose_variant_string` skips only `None/""/[]`, not literal `"N/A"` → the
  "N/A · N/A" variant leak. Reuse the existing `_SPEC_NA_TOKENS` set.
- **Verdict copy** ("leads on Feature match") is **template-driven, not GPT** → fixed automatically by P0
  (correct dims/labels). No separate copy/prompt fix.
- **GAP (callsites):** the behavior-replay `SELECT category_used, products …` (`structured_comparison_service.py:2869`)
  reads **two columns that don't exist** in the live `comparisons` schema → category affinity is silently
  always-empty. The corrected category won't improve behavioral personalization until this is addressed.

---

## SCOPE

### ✅ P0 HOTFIX BUNDLE — one backend PR, all $0, Serper-independent (buildable now, no rotation needed)

Internally complete: makes the fragrance render **correct** (right dims/specs/sources) **and honest**
(no AI rating shown as real). Items B–D ride the same PR because they share the `rating_derived` flag and
because B is required to keep the *corrected* render honest.

**A. P0-CATEGORY** — `extraction_service.py`, `structured_comparison_service.py`
1. Add `classify_category_from_text(text) -> str` next to `canonicalize_category` (~line 760). Deterministic,
   $0: reuse `_CATEGORY_SYNONYMS` (whole-word scan, longest-token-first) + `is_supplement_query`.
   **⚠️ `is_supplement_query` must be a FUNCTION-LOCAL import** — `price_service.py:16` already imports
   `extraction_service`, so a module-level import is circular (verified).
2. Replace the `"supplements" if … else "other"` binary at **all 4 sites**: sync vision `1849`,
   sync explicit_pair `1864`, stream vision `2303`, stream explicit_pair `2317` →
   `category = classify_category_from_text(<the product text>)`.
3. Make `selected_category` the **authority** in **both** resolution blocks (sync `1889-1895`,
   stream `2341-2347`): when `canonicalize_category(selected_category)` is valid and `!= "other"`,
   set `category_used = sel`. Treat `"other"`/unknown as "no opinion" (don't clobber a confident detection).
   `category_switched` becomes purely informational (FE banner) and **never gates behavior**.
4. **WRITE-BACK:** set `products[0]["category"] = products[1]["category"] = category_used` **before** the
   `_fetch_product_data` gather (sync ~`1924`, stream ~`2370`). *This is the load-bearing line* — it makes
   `_fetch_product_data → result["category"]` (`2890/2903`) carry the right value into scoring/specs/sources.
5. Vision path has no `selected_category` (camera UI has no picker) → step 2's classifier is its only fix.
   Do **not** thread `selected_category` into `image_routes.py` here (follow-on #7).

**B. Rating-provenance suppression** — `response_builder.py`, `scoring_service.py`
- Null the rating in the **overview** (`~1243`) + **reviews** (`~1312`) projections when
  `pd.get("rating_derived") is True`. **Keep the internal mutation** (so `test_decomposed_services.py:299`
  stays green — change only the *projection*). **Do NOT touch `review_count`** (it's real).
- Guard `_rating_candidate`/`_safe_rating` (`516-571`) to return `None` on a derived rating → verdict line1
  can't say "X stars higher" off a fabricated rating. Verify the price/dim fallback (`816-829`) still fires.
- Add `rating_derived` recognition to `_dim_value` (`scoring_service.py:2521`) — mirror the existing
  `_dim_reviews` guard so synthetic ratings force "Limited value data".
- **`gpt_review_aggregate` path** (`structured_comparison_service.py:3362-3369`): mark its
  `average_rating`/`total_reviews` as estimated (or `None`) so the accordion header stops presenting a GPT
  estimate as a counted review volume. (GAP2 — this is the *second* AI-origin path; cover it too.)
- **SSE parity caution:** the SSE `reviews` event (`~2474`) emits the real `None` rating BEFORE the derive
  mutation — it's already honest. Do **not** "fix" it into emitting a derived value.

**C. Variant "N/A" leak** — `response_builder.py`
- `_compose_variant_string` (`276-289`): reuse the existing `_SPEC_NA_TOKENS` (`~315`) to skip literal
  `"n/a"/"unknown"/"-"/"none"`, not just `None/""/[]`.

**D. P1-FRAGRANCE-SCHEMA Part A** — `extraction_service.py` (rides the PR; inert without A)
- Add `scent_family` to `CRITICAL_SCHEMA_FIELDS_PREFERRED["fragrances"]` (`~234`) — rides the **existing
  batched `_smart_fallback_extract`** (one shared call already fires when any field is blank → ~0 Serper delta).
- Strengthen the fragrance line in the **DYNAMIC** prompt section (`~464`) with a null-when-unknown honesty
  clause (keeps OpenAI cache prefix intact). **Do NOT promote to NON_NEGOTIABLE** (Serper-costly).

**Explicitly rejected from P0:** non-negotiable schema promotion (Serper-costly), Scrape.do super-mode
(Business-plan-gated), and any FE/EAS change (the backend null-projection makes FE work optional).

### ⏭️ P1 FOLLOW-ON BUNDLE — separate, lower urgency, mostly $0

- **P1-SCRAPEDO Piece A** — cost-header metering (protective; small return-arity change `(html,status)`→
  `(html,status,cost)`, update sole caller `_scrapedo_scraper:836` + the 2-tuple test). Ship when convenient.
- **P1-IMAGE-VARIANT** — image candidate size validation, fragrances-first via `is_fragrance_query`; add a
  shared `image_size_matches()` in `price_service` so image+price share one tolerance. $0 (keep Tier-1 at a
  single Serper Images call even if `num_results` 1→5).
- **DISC-CALLSITES #6** — `/quick` `selected_category` plumbing.
- **DISC-CALLSITES #8** — URL engine: it **drops** the FE-sent `selected_category` (Pydantic), is
  category-blind, and uses a **non-canonical** enum (`beauty/home/sports/automotive`). Add the field +
  canonicalize + pass category into `generate_comparison`.
- **DISC-CALLSITES #9 (+GAP1)** — dead `comparisons.category_used` **and** `products` columns → behavioral
  category affinity is dead. Either add a column via migration (Supabase MCP, verify `information_schema`) or
  read category from `full_response` JSON.
- **DISC-CALLSITES #7** — camera category picker (genuine FE+BE feature + EAS) → scope last.

---

## Tests (all $0 — unit/scoring, no live APIs)

P0 set:
- `tests/test_explicit_pair_category.py` (NEW): `_fetch_product_data` **capture** test → both
  `product_info["category"] == "fragrances"` for the Tom Ford pair + `selected_category="fragrances"`
  (sync AND streaming — byte-mirror parity); classifier-without-`selected_category` (token-bearing name →
  `fragrances`, no-token luxury pair → `other`); supplements still classified; vision path classifier.
- Scoring: explicit fragrance pair → `compute_scores` breakdown includes `longevity_score`/`projection_score`,
  EXCLUDES `build_score` (mirror `tests/test_category_keystone_scoring.py`).
- `selected_category` override precedence: heuristic says `other`, user picked `makeup` → `makeup`;
  `selected_category="other"` must NOT clobber a confident detection.
- Source-router guard: `get_shopify_sources_for_category("fragrances")` returns ajmal/alhajis/asgharali;
  `("other")` returns `[]`.
- Rating-provenance: derived rating NOT forwarded to overview/reviews; `_rating_candidate` returns `None` so
  verdict line1 has no "stars higher"; `_dim_value` returns "Limited value data" when both ratings derived;
  real rating still renders (no regression); `gpt_review_aggregate` count not presented as counted.
- `_compose_variant_string` skips literal `"N/A"`.
- `test_critical_schema_fields_split.py::test_fragrances_split` — add `scent_family` to PREFERRED, assert it
  is NOT in NON_NEGOTIABLE; prompt-render test asserts `scent_family` + honesty clause present.

Regression gates: existing scoring/spec-schema suites (electronics/supplements unaffected),
`test_decomposed_services.py:299`, `test_dim_reviews_derived_rating.py`.

---

## Sequencing

1. **STEP 1 (keystone, must land first):** P0-CATEGORY (A) + the 3 source-router guard tests.
2. **STEP 2 (same PR):** rating-provenance suppression (B) + variant-NA (C) — shares the `rating_derived`
   flag; required so the *corrected* fragrance render stays honest.
3. **STEP 3 (same PR or adjacent; inert before STEP 1):** fragrance-schema Part A (D).
4. **STEP 4+ (follow-on bundle):** Scrape.do Piece A → image-variant → #9/GAP1 (if behavioral
   personalization matters) → #6 / #8 → #7 (camera feature, last).

---

## Gotchas / risks (durable)

- **`products[i]["category"]` ≠ `category_used`** — the whole bug. Pin with a capture test.
- **Circular import** — `classify_category_from_text` must import `is_supplement_query` *inside the function*.
- **Stream/sync parity** — the P0 bug is byte-duplicated across both engines; the rating fix is NOT (it lives
  only in the final `build_comparison_response`). Patch both engines; pin parity.
- **Keep `review_count`** real; only the synthetic RATING is suppressed.
- **Verification budget** — a prod `nocache=true` end-to-end compare burns ~10–15 Serper credits/cold run and
  `eval_runner` measures COLD scraping. **Prefer unit/scoring assertions; reserve ONE cold prod probe** for
  final confirmation (use a FRESH pair to dodge the 7d-specs/24h-price cache that masks deploys).
- **Stale Redis cache masks a deploy** — re-running the same pair serves the pre-fix cached payload; re-test
  a fresh pair or `?nocache=true`.

## Execution

All P0 work is backend + $0 + Serper-independent. Recommended: **solo / sequential** (the `rating_derived`
flag threads through several files → a worktree team would race the git index for little gain). No EAS push
required for the recommended (backend null-projection) path — FE star-suppression is optional defense-in-depth.
