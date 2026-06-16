# Fragrance Quality + Personalization Correctness + Results Redesign — DESIGN

**Date:** 2026-06-16 · **Status:** Brainstormed + designed (this session). **Build: NEXT session.**
**Predecessor:** genuine-bh-latency-warmer bundle + S3.1 (main `556022c`). The fragrance "couldn't load"
crash is fixed; this bundle fixes the *content* + *personalization* + *presentation* of the result.

> One combined bundle (Ahmed's call). The three thrusts share a single keystone root cause —
> **product `category` is never canonicalized** — which breaks fragrance content AND fragrance
> personalization at once. The redesign's cohort proof line depends on the personalization fix.

---

## 0. Validated diagnosis (evidence-backed, this session)

Three read-only investigators traced the code. Key findings:

1. **Personalization IS mostly wired** — explicit priorities reach scoring (±30%, `scoring_method="personalized"`)
   and the GPT verdict prompt (`extraction_service.py:1459-1462`, ungated); the "Weighted ↑Camera ↑Battery"
   `PersonalizationChip` renders end-to-end from `scoring_v2.personalization.applied_shifts`
   (`response_builder.py:927-929` → `ResultsContent.tsx:368-371`).
2. **Cohort proof line is HARD-BROKEN.** FE reads `result.cohort_summary` / `result.personalization.cohort`
   (`ResultsScreen.tsx:774-791`); the backend **never emits either key** (zero `cohort_summary` in `app/`).
   `CohortBadge` (`CohortBadge.tsx:62`) renders nothing for *every* user, always. A false FE comment
   (`ResultsScreen.tsx:768`) claims the backend sends it.
3. **THE KEYSTONE: `category` is never normalized.** `parse_product_query` returns the raw LLM string
   (`extraction_service.py:692`); the orchestrator passes it straight through (`structured_comparison_service.py:1836-1842, 2253-2259`).
   Lowercase-keyed lookups then fail exact-match and fall back to `"other"`:
   - `scoring_service.py:1062-1064` (`compute_scores`) → `"other"` dims = function/**build**/review/value/reliability/feature_match.
   - `scoring_service.py:2909` (`build_dimensions_v2`).
   - `extraction_service.py:735` (`extract_specs` → `"other"` spec schema, no scent fields).
   - `structured_comparison_service.py:3059` (critical-field cascade).
   The LLM returned **"Fragrances"** (capital F) → fell to `"other"` → produced the on-device "Build" dimension (C3),
   the blank product_1 specs (C4), **and** degraded personalization (priorities reweighted generic "other"
   dims, not scent dims). **Ahmed confirmed he was signed-in with prefs set → this was a real personalization
   bug, not expected behavior.** A `_product_category` helper that does the right `.strip().lower()` already
   exists (`structured_comparison_service.py:70`) but is NOT applied on the scoring/spec path.

## 1. Locked decisions (this session)

| # | Decision |
|---|---|
| D1 | **One combined bundle** (fragrance content + personalization correctness + results redesign). |
| D2 | **Results page = full 1:1** with the design-system "UI Kit — Mobile Results" mockups, **including backend data plumbing** (cohort_summary, variant subtitles, normalized dimension shares). |
| D3 | **Cohort layer fully fixed + enabled** — emit `cohort_summary`, verify `ENABLE_COHORT_PERSONALIZATION=true` in Railway, wire `CohortBadge`. |
| D4 | **C1 = "price-pending" presentation, not a price floor.** When a price is NOT genuine, show an engaging "pricing in a future update" line instead of a number. Genuine prices still show (electronics, warmed fragrances). |
| D5 | **C2 = guaranteed matching size basis** for the comparison; the off-clock warmer does the size-matched genuine fetch. No apples-to-oranges deltas. |
| D6 | **Build SOLO-first** (weekly limit at 91% on 20x). Dispatcher does backend keystone + content + personalization solo; FE redesign as a focused pass. Worktree-subagent parallelism only if next-session budget has reset. |
| D7 | **Scope assumption (Ahmed may veto):** price-pending is conditional on genuineness, not blanket fragrance suppression. |

## 2. Thrust 1 — Personalization correctness

### 1a · Category canonicalization (KEYSTONE — do first)
- Add `canonicalize_category(raw) -> str`: `.strip().lower()` + synonym map
  (`perfume`/`fragrance` → `fragrances`; `phone`/`mobile`/`smartphone` → `electronics`; etc.),
  returning a value guaranteed to be a `CATEGORY_DIMENSIONS` / `CATEGORY_SPEC_SCHEMAS` key (else `"other"`).
- Apply **once** at parse time where `category_used` is set (`structured_comparison_service.py:~1836, ~2253`)
  so a single canonical string flows everywhere. Reuse/extend the existing `_product_category` helper (`:70`).
- **Defensive `.lower()` guards** at the four lookup sites (`scoring_service.py:1062, 2909`;
  `extraction_service.py:735`; `structured_comparison_service.py:3059`) — belt-and-suspenders.
- Tests: each casing/synonym variant ("Fragrances", "Perfume", "fragrance") → correct scent dims + fragrance spec schema, never "other".

### 1b · Priority → scent-dim mapping
- **Verify/extend** `CATEGORY_PRIORITY_ADJUSTMENTS` (`scoring_service.py:1191-1234`) has a `fragrances` entry
  mapping the 8 user priorities onto scent dims (longevity/sillage/projection/character/wear_value/presentation).
  If absent, a fragrance user's priorities won't bite even after 1a. **Build-time verification item.**

### 1c · Emit `cohort_summary` (fixes the dead proof line)
- In `response_builder.build_comparison_response`, build `cohort_summary = {peer_count, governorate}` from the
  cohort-match data and attach it at the response root (the exact shape `ResultsScreen.tsx:774-791` reads).
- Source `peer_count` from the cohort match (`cohort_service` / `_derive_cohort_profile`,
  `structured_comparison_service.py:2654-2677`). **Build-time verify** the matched prior carries a sample-size N.
- Delete the false FE comment (`ResultsScreen.tsx:768`).
- Tests: response includes `cohort_summary` when demographics resolve; absent/empty when they don't (badge hides).

### 1d · Confirm flag
- Verify `ENABLE_COHORT_PERSONALIZATION=true` in Railway (CLAUDE.md says ON; code-default `false` at
  `extraction_service.py:1082-1084`). It gates the cohort prompt thin-context block (`:1005`). The cohort score
  nudge (`structured_comparison_service.py:2664-2665`) only fires for users with NO explicit prefs (explicit wins — by design, keep).

### 1e · On-device verification (the "loads ≠ correct" rule)
- A logged-in-with-prefs fragrance compare must show: scent dimensions (not Build), priorities reflected in
  the reweight, the "Weighted ↑…" chip, and the cohort proof line.

## 3. Thrust 2 — Fragrance content fixes (C1–C6)

- **C1 (price-pending mode).** Replace the too-low fragrance floor approach with a presentation state.
  Resolve price genuineness via `source_method` ∈ {`local_bhd`, `page_scrape_jsonld`, `shopify_json`,
  trustworthy `converted_usd`}. When the resolved price is `estimated`, fails the sample/decant signal
  (title keywords: sample/decant/tester/vial + per-ml sanity), or is absent → set `price.unavailable=true`
  (+ a reason) and DO NOT emit a number. Keep the existing `is_implausible_*` guards (`price_service.py:526, 565-596`)
  as the sample detector feeding this flag. Scoring already drops/suppresses a one-sided-MISSING price dimension.
- **C2 (size consistency).** During candidate selection prefer the canonical flagship size (100ml) for BOTH
  products consistently (re-rank within already-fetched candidates — no extra live call). The **warmer**
  (`scripts/cron_warm_price_cache.py`, 60s off-clock budget) fetches the size-matched genuine pair so cache
  serves matched. If a live cold pair still mismatches, the price is "pending" (D4) anyway — so no
  apples-to-oranges delta ever renders. `price.size` annotation at `price_service.py:1147-1148`.
- **C3 + C4** — resolved by 1a keystone. Plus promote key scent fields (scent_family/notes/sillage) toward
  non-negotiable (`extraction_service.py:218`) so the per-product Tier-2/3 fill cascade
  (`structured_comparison_service.py:3112, 3135`) re-fires for product_1 when blank.
- **C5 (raw `[2][3]`).** Extend `_clean_review_citations` (`review_service.py:132-169`, regex `:151`) to also
  match bare numeric `\[\d+\]`, and scrub all review text fields (not only praises/complaints/highlights, `:156-167`).
- **C6 (rating vs N/A).** `_dim_reviews` (`scoring_service.py:2358-2386`) must honor the `rating_derived` flag:
  a derived rating (from `derive_rating_from_scores`, `response_builder.py:99-102`, injected at `:1074-1080`)
  counts as missing → "Limited review data", never "X stars higher". Alternative: stop the in-place
  `pd_item["rating"]` mutation and keep the derived value in a display-only field.

## 4. Thrust 3 — Results page, 1:1 with mockups (rewire, not rebuild)

All 8 target sections have live counterparts in `SmartCompareApp/src/components/results/`. The two
highest-fidelity gaps already exist as **unused primitives** — swap them in.

| Target section | Action | Anchor |
|---|---|---|
| Header ★ TOP MATCH pill | Add star glyph + uppercase | `TopMatchBadge.tsx:23-30` |
| Product pair (image/name/subtitle/price, emerald winner, vs pill) | Keep (already complete); wire **price-pending** line into the price slot via `price.unavailable` | `ResultsContent.tsx:195-278`, `formatPrice :117-121` |
| "WHY THIS FITS YOU" + headline + subline | Keep `FactualVerdict` + relocate `PersonalizationChip` directly under headline | `ResultsContent.tsx:280-307`, `PersonalizationChip.tsx` |
| Dimension bars (single grey-A‖emerald-B split + per-row "A · B" legend) | **Swap** mirrored `DimensionBars` → `primitives/DimensionBar` (single split); FE computes share `score_a/(score_a+score_b)`; add product-name legend row | live `DimensionBars.tsx:255-278` → `primitives/DimensionBar.tsx:30-51` |
| "WHAT WE KNOW" confidence pills (dot + "· High/Medium/Low") | **Swap** emoji `ConfidencePills` → `primitives/ConfidencePill` (dot+label); map strong/acceptable/weak → High/Medium/Low | live `ConfidencePills.tsx:46-91` → `primitives/ConfidencePill.tsx:25-41` |
| Cohort proof box ("N+ shoppers in {gov} leaned the same way") | Restyle `CohortBadge` to subtle rounded box + copy; **needs 1c payload** | `CohortBadge.tsx:62-87` |
| Dig Deeper accordion — Reviews / Pros&Cons | Keep (already match) | `ResultsAccordion.tsx:250-378` |
| Dig Deeper — Specs table (value · centered-label · value) | Restructure rows to value/center-label/value; winner cell bold-emerald (already emerald) | `ResultsAccordion.tsx:458-528` |
| "Was this helpful?" chips | Keep (superset) | `FeedbackCard.tsx` |

**Backend data the redesign needs (D2):**
- `cohort_summary` — Thrust 1c.
- `product.variant` subtitle — populate ("100ml · EDP" fragrance / "128GB · Black" electronics); graceful-hide if absent (`ResultsContent.tsx:244-252`).
- Per-dimension share — FE-computed from existing `score_a`/`score_b` (no backend change).
- Confidence level word — FE maps existing `strong`/`acceptable`/`weak`.

**Copy:** no-scary contract (forbidden EN `couldn't`/`try again`/`Failed to`; AR `تعذر`/`فشل`/`تقدير`/`مُقدَّر`).
Price-pending EN candidate (fe/i18n to bless): *"Pricing lands in an upcoming update — the pick still holds on specs & reviews."* No "estimated".

## 5. Testing & verification
- **Backend red-green:** category canonicalization (casing/synonyms → correct dims+specs); price-pending
  (sample/estimated → `unavailable`, genuine → shown); C2 size consistency; C5 bare-`[N]` regex; C6 derived-rating;
  `cohort_summary` emission present/absent.
- **FE:** `npx tsc --noEmit` clean; snapshots for swapped `DimensionBar`/`ConfidencePill`; cohort line
  renders-when-present / hides-when-absent; price-pending renders the engaging line.
- **Eval:** smoke20 `--concurrency 1` no-regression. **Prereq:** create the proper smoke20 `--persist` baseline
  (deferred B2 — the documented `4aee8e88` is `subset:"full"`). If the box can't DNS-reach Supabase, insert the
  `eval_runs` row via Supabase MCP (project `qulajmyxdbdkchvecmvc`).
- **On-device:** the Tom Ford Ombré Leather vs Tobacco Vanille repro — verify RENDERED content (scent dims,
  populated specs both products, no raw citations, consistent rating, personalization + cohort line, price-pending).

## 6. Out of scope (Ahmed's levers / deferred)
- Warmer cron registration + `ENABLE_PRICE_CACHE_WARMER=true` (the genuine-share win — Ahmed; runbook `docs/runbooks/qaren-warmer-activation.md`).
- CF-bypass scraper tier for CF-walled luxury (`docs/investigations/2026-06-15-render-wall-bh-retailers.md`) — budget/vendor decision.
- A4 cache-reading eval variant — meaningful only after warmer activation.

## 7. Execution model (D6 — solo-first, budget-aware)
Weekly limit at **91% (20x plan)** → **do NOT spawn a fleet.** Recommended next-session order (solo dispatcher):
1. **1a category canonicalization (keystone)** + tests — unblocks C3/C4/personalization.
2. **Thrust 2 content** (C1 price-pending, C2 size, C5, C6) + 1b priority mapping + tests.
3. **1c cohort_summary** emission + 1d flag check + tests.
4. **Thrust 3 FE redesign** (primitive swaps + price-pending UI + cohort box + specs table) + `tsc` + snapshots.
5. Eval smoke20 no-regression → merge `--no-ff` → Railway deploy → prod-smoke → **on-device verify**.
6. Ahmed fires warmer cron + flag + (already-pushed) EAS bundle.

Escalate to worktree subagents (backend-content lane ∥ FE-redesign lane) ONLY if the weekly budget has reset
and the scope warrants it. Path-restricted commits; verify "complete" via `git show`.

## 8. Ready-to-paste NEXT-SESSION kickoff prompt
> Build the Qaren "fragrance-quality + personalization-correctness + results-redesign" bundle. FIRST read
> `docs/plans/2026-06-16-fragrance-quality-personalization-results-redesign-design.md` (this doc) + memory
> `project-fragrance-quality-personalization-redesign`. Then EXECUTE **solo-first** (weekly budget was 91% on 20x —
> check current %; spawn a worktree team ONLY if reset). Order: (1) category canonicalization KEYSTONE
> (`structured_comparison_service.py` parse-time + defensive guards at the 4 lookup sites) + tests; (2) Thrust 2
> content fixes C1 price-pending / C2 size / C5 citations / C6 rating + 1b fragrances priority-adjustments; (3) 1c
> `cohort_summary` emission + 1d verify `ENABLE_COHORT_PERSONALIZATION`; (4) Thrust 3 FE 1:1 redesign (swap in
> `primitives/DimensionBar` + `primitives/ConfidencePill`, ★+uppercase TopMatchBadge, value·label·value specs,
> cohort box, price-pending UI via `price.unavailable`). Red-green ≥80%, `npx tsc --noEmit` clean, no-scary copy
> (EN/AR), smoke20 `--concurrency 1` no-regression (create the proper smoke20 `--persist` baseline first).
> Merge `--no-ff` → Railway → prod-smoke the Tom Ford curl → **verify RENDERED content on-device** (loads ≠ correct).
> DoD: scent dims (not Build), both products' specs populated, no raw `[N]` citations, consistent rating, the
> "Weighted ↑…" chip + cohort proof line both render for a logged-in-with-prefs user, no wrong fragrance price
> (price-pending line instead).
