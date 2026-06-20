# Design — Category Resolution + All-Category Render Correctness (2026-06-20)

**Status:** Approved (brainstorm complete). Next: `writing-plans` → 4-Opus cross-QA team build.
**Sibling doc (verified line-level findings):** `docs/plans/2026-06-20-fragrance-category-fix-plan.md`
**Verification provenance:** workflow `wf_01a4745e-9ac` (9 agents, ~1.15M tokens, every audit finding
checked against real code).

## Problem

The two-box (explicit-pair) and camera (vision) comparison paths **skip the GPT parser** and hardcode
`category = "supplements" if is_supplement_query else "other"`; `selected_category` is received but used
only to flip a display flag. Result: a fragrance (or skincare, or any non-supplement) two-box comparison
renders the **`other`** structure — wrong scoring dims (Function/Build/…), a 1-field spec table, fabricated
star ratings shown as real, and the Bahrain fragrance price sources filtered out. The fragrance screenshot
is one instance of a **general** defect: every category except supplements collapses to `other` on these
paths.

## Decisions (this brainstorm)

1. **Category resolution model → Detect-first, chip refines, no silent default.**
2. **All-category scope → Fix routing + audit all 9** (keep existing structure definitions; verify + fix
   that each *renders* correctly; not a redesign).
3. **Detection depth → Deterministic + bounded GPT-mini** (free classifier first; one cheap GPT-mini
   classify only in the uncertain-AND-no-chip corner; gentle chip nudge if still unsure).
4. **API/Scrape.do scope → Free wins + Scrape.do Piece A metering.** Category fix unblocks the FREE BH
   fragrance sources ($0, Serper-positive); fold in Scrape.do cost-header metering ($0, protective).
   Defer all paid unlocks (Scrape.do super-mode, paid Serper).

---

## Design

### Section 1 — Category detection & resolution (safety net)

**Frontend (small):** remove the silent `'electronics'` default — `selectedCategory` starts `null`
(`HomeScreen.tsx:105`). The chip strip already supports `null` (`CategorySelector` `value: string | null`),
so nothing is preselected and `selected_category` is sent **only when the user taps a chip**.
Gentle-nudge polish: when nothing is selected, the strip reads as an invitation (subtle "Pick a category
for the most accurate compare" hint) — non-blocking.

**Backend — shared `resolve_category(product_texts, selected_category)` helper** used by sync text, stream
text, and vision paths (URL engine = follow-on). Replaces the hardcoded binary at all 4 sites
(`structured_comparison_service.py` sync vision `1849` / explicit `1864`; stream vision `2303` / explicit
`2317`) and both resolution blocks (sync `1889-1895`, stream `2341-2347`).

1. **`classify_category_from_text(text) -> str`** — deterministic, **$0**. Reuse `_CATEGORY_SYNONYMS`
   (whole-word, longest-token-first) + extend with fragrance/beauty tokens (`oud`, `eau`, `parfum`, …) +
   `is_supplement_query`. **⚠ function-LOCAL import** of `is_supplement_query` (price_service already
   imports extraction_service → module-level import is circular; verified).
2. **Precedence (detect-first, chip refines):**
   - deterministic **confident** (matched a real category) → use it; if it conflicts with a tapped chip →
     use detection + set `category_switched=True` → gentle FE note ("Showing as Fragrances").
   - deterministic **uncertain** (`other`) + chip set → use the chip.
   - deterministic **uncertain** + no chip → fire **one GPT-mini category classify** (lightweight,
     classify-only — NOT the full parser); confident → use it (+note); still unsure → `other` + chip nudge.
3. **Write-back (load-bearing):** the resolved category is written to **both** `products[0]/[1]["category"]`
   (BEFORE the `_fetch_product_data` gather, sync ~`1924` / stream ~`2370`) **and** `category_used`.
   This is the line the original audit missed — scoring (`compute_scores` reads `products_data[0]["category"]`),
   the spec schema, and category-aware source discovery all key off the **per-product** field, not
   `category_used`. Pin with a `_fetch_product_data` **capture** test, not a `category_used` assertion.

`category_switched` becomes purely informational (FE banner); it never gates behavior.

### Section 2 — All-9-category render correctness (audit + fix)

**Source of truth (definitions unchanged):** `CATEGORY_DIMENSIONS`(+weights) → hero bars (top-4 by weight);
`CATEGORY_SPEC_SCHEMAS` in schema order → "At a glance" + Specs; `CATEGORY_FAIRNESS` → like-for-like basis;
design-sync JSX refs (`.design-sync/`, `ui_kits/mobile/ResultsScreen.jsx`) = visual reference.

Once Section 1 routes correctly, each category gets its own structure. The team then **audits all 9**
(electronics, grocery, supplements, makeup, skincare, haircare, fragrances, fashion, other) end-to-end —
one representative pair each — against the references, producing a **9-row audit matrix**:

| category | dims correct? | spec-schema (order) correct? | At-a-glance correct? | fairness basis correct? | fix shipped |

Fix only **residual per-category gaps** found (e.g. too-thin spec schema, wrong At-a-glance field, missing
fairness basis). Keep the structure definitions; this is verify + targeted fix. Use unit/scoring assertions
for the matrix where possible; reserve live probes for spot-confirmation.

### Section 3 — Honesty fixes (ride the same change — verified real)

Must land WITH Section 1 (correct fragrance dims would otherwise re-surface fabricated data in the verdict):
- **Rating provenance:** null the **derived** rating in the overview (`response_builder.py:~1243`) + reviews
  (`~1312`) projections (keep the internal mutation so existing tests stay green); guard
  `_rating_candidate`/`_safe_rating` (`516-571`) so verdict line1 can't say "X stars higher" off a synthetic
  rating; teach `_dim_value` (`scoring_service.py:2521`) to treat a derived rating as missing; mark/suppress
  the GPT-**estimated** `gpt_review_aggregate` rating+count (`structured_comparison_service.py:3362-3369`).
  **Keep the real `review_count`.** Restores the "ratings are NEVER AI-generated" invariant.
- **Variant "N/A" leak:** reuse the existing `_SPEC_NA_TOKENS` (`response_builder.py:~315`) in
  `_compose_variant_string` (`276-289`) — skip literal `"n/a"/"unknown"/"-"`, not just `None/""/[]`.
- **Fragrance schema Part A ($0):** add `scent_family` to `CRITICAL_SCHEMA_FIELDS_PREFERRED["fragrances"]`
  (rides the existing batched `_smart_fallback_extract` — no per-field fan-out) + a null-when-unknown honesty
  clause in the DYNAMIC fragrance prompt line. **Do NOT promote to NON_NEGOTIABLE** (Serper-costly).

### Section 4 — API / Scrape.do (free wins + metering)

- **Free price win (in-scope via Section 1):** correct `fragrances` category unblocks the BH fragrance
  sources (Ajmal/Al Hajis/Asgharali/Ounass) which are **free `curl_cffi` `/products.json` + Algolia**
  fetchers — genuine BH prices at $0, and **−~4 Serper calls/product** (the broken `other` path fired
  speculative discovery that ended at `estimated`; `_pf_eligible` flips false once real sources exist).
- **Scrape.do Piece A — cost-header metering (in scope, $0):** `render_page_with_status` reads the
  authoritative `Scrape.do-Request-Cost` header and returns it (`(html,status)`→`(html,status,cost)`);
  the sole caller `_scrapedo_scraper` (`structured_comparison_service.py:836`) calls
  `record_usage("scrapedo", count=cost)`. Today render-on-datacenter = 5 credits metered as 1 (~5× under).
  Also record usage (not failure) for billed-but-priceless 400/404/410. Update the 2-tuple-unpacking test.
- **Deferred (NOT this bundle):** Scrape.do Piece B super/`geoCode` residential anti-bot — **$249/mo
  Business plan; free tier 401s** (proven 2026-06-17). Paid Serper warmer for sustained genuine prices.
  Both are business/revenue decisions, not code tasks.

### Section 5 — Team execution & QA discipline

**4-Opus worktree team** (Opus only — no sonnet/haiku), `mode: bypassPermissions`, isolated worktree.
Suggested ownership (delegated):
- **BE-core:** `resolve_category` + `classify_category_from_text` + write-back (sync/stream/vision) +
  rating-provenance + variant-NA + Scrape.do Piece A metering.
- **BE-render:** all-9 audit matrix + residual per-category fixes + fragrance schema Part A.
- **Test:** red-green tests to **80%** across new code — `_fetch_product_data` capture, fragrance-dims,
  sync/stream parity, classifier matrix, override precedence, rating-provenance, variant-NA, Scrape.do
  metering, per-category render assertions.
- **FE:** null-default + nudge polish + FE tests + the single end-to-end prod verification.

**Discipline (per Ahmed):** features **100% complete before disassembly**; each member **QAs another
member's** work; subpar/missed work is **sent back**; an idle member either **writes red-green tests
(target 80%)** or **waits for their QA to return results**. Work must be delegated.

## Scope boundaries

**In:** Sections 1–5 above.
**Deferred to a P1 follow-on (none block this):** image-size validation; `/quick` + URL-engine category
plumbing; the dead `comparisons.category_used`/`products` columns (behavioral category affinity is silently
dead until fixed); camera category picker; Scrape.do super-mode.
**Rejected:** non-negotiable fragrance-schema promotion (Serper-costly); Scrape.do super on free tier.

## Testing & budget

- All backend + **$0** (Serper-*positive*), except the FE null-default (needs an EAS push). GPT-mini
  escalation fires only in the rare uncertain-and-no-chip corner.
- Prefer unit/scoring assertions; reserve **one** cold prod `nocache` probe (FRESH pair, to dodge the
  7d-specs/24h-price cache) for final confirmation. `eval_runner` measures COLD scraping — use the smoke20
  gate (baseline `54b603e8`) for no-regression, not for measuring the warmer.

## Durable gotchas

- `products[i]["category"]` ≠ `category_used` — the whole bug; pin with a capture test.
- Circular import → `is_supplement_query` imported inside `classify_category_from_text`.
- Sync/stream parity — the P0 bug is byte-duplicated; the rating fix lives only in the final
  `build_comparison_response` (SSE reviews event already emits the real `None` — do not "fix" it into a
  derived value). Pin both with parity tests.
- Stale Redis cache masks a deploy — re-test a FRESH pair or `?nocache=true`.
