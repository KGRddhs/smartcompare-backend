# Genuine-price CORRECTNESS — STRUCTURAL fix plan (42 coverage-review findings)

**Status:** PR #9 (`feature/genuine-price-correctness`) FAILED an external review, then a
3rd dispatcher fix pass, then a **coverage-driven** review workflow (7 agents, real-product
enumeration, both directions, reproduced through the runtime) found **42 verified findings
(10 CRITICAL / 16 HIGH / 10 MEDIUM / 6 LOW)**. The root cause is structural: the runtime
matcher (`_selection_match`) is SUBSET-based, so a candidate that ADDS a distinctive token is
accepted as the queried base SKU across EVERY category, and several discriminating axes (lb/oz,
%, shoe-size, pack, single-digit model, single-letter shade, supplement form) do not exist.
Patch-by-patch (3 passes) keeps leaving gaps. This needs the category-canonical-identity
redesign the first reviewer prescribed. **DO NOT MERGE until re-run through the coverage review.**

Raw findings: `.qa-correctness/coverage_findings.txt` (full repros). Counterexample spec:
`tests/test_correctness_external_review_counterexamples.py` (15 already green) — EXTEND it with
all 42 as failing tests FIRST.

## Cluster A — SYSTEMIC superset/subset leak (the keystone; ~8 CRIT/HIGH)
A candidate ADDING a distinctive token is accepted as the base SKU. The fragrance flanker
near-equality (`_FRAGRANCE_FLANKER_CATEGORIES = {fragrances}`) is the right shape but only
fragrances have it. Reproduced: Canon R6→R6 Mark II, AirPods Pro→Pro 2, Switch→Switch OLED,
RTX 4070→4070 Ti, Magnesium→Magnesium Glycinate, Centrum→Centrum Silver, Fish Oil→Triple
Strength, Creatine→Micronized, Pillow Talk→Pillow Talk Medium, NARS Orgasm→Orgasm X, Samba
OG→Samba Classic, Nescafe Gold→Gold Decaf, Creed Aventus→Aventus Cologne.
**FIX:** generalize the candidate-adds-distinctive-token guard to ALL categories with a
per-category PADDING/noise allowlist (the over-rejection lever — must tolerate descriptive
electronics "Dual SIM Phantom Black 5G Smartphone", multi-colour fashion, chemical-name-in-paren
supplements). This is the HIGH over-rejection-risk piece (round-2's trap) — needs both-direction
tests per category + a re-run of the coverage review. `cologne` must leave `_FRAGRANCE_PADDING`.

## Cluster B — missing NUMERIC axes (~6 CRIT/HIGH; contained, lower risk)
- lb/lbs/pounds + oz weight (supplements/grocery): add to `_WEIGHT_VOLUME_RE`/`_weights_volumes`
  (lb→g ×453.592, oz→g ×28.35). 2lb vs 5lb protein currently matches.
- % active-ingredient strength (skincare/haircare/makeup): new axis (value,%) incl. spaced /
  "percent"/"pct"; both-state-differ → mismatch; query-states-candidate-omits → pend.
- Fashion SHOE size (US/UK/EU/numeric+half) axis; mirror into `size_variant_token`/cache key.
- Grocery PACK count ("6 Pack"/"24x"/"Pack of 6") axis + one-sided pend.
- Single-DIGIT model number preserved as identity for fashion/other (Air Jordan 1 vs 4 — the
  `len>2 or 2+digit` rule drops "1"/"4"). Keep `og`/`gtx`/`mid`/`low` fashion qualifiers.
- Single-letter / 2-char makeup SHADE codes (NARS Orgasm X, MAC shade letters) preserved.

## Cluster C — FORM axis (CRIT/HIGH)
`_form_mismatch` is fragrance/beauty-only. Extend to supplements (softgel/capsule/tablet/gummy/
powder/liquid — one-sided candidate-adds → pend) and skincare/haircare (cream/gel/oil/balm/
serum/toner/essence/mask — currently in `_FORM_NOISE_TOKENS` so swaps leak). Make form
ONE-SIDED-tolerant for skincare/haircare (a serum PDP for a form-omitting query must not pend;
only BOTH-stated-different forms reject) — over-rejection finding.

## Cluster D — CACHE reads + write coverage (HIGH/MEDIUM)
- Revalidate cache READS (scs `_get_price` ~4132 Redis / ~4140 DB): run the cached price through
  `should_cache_price`/identity check vs the request before returning; drop+re-resolve on mismatch
  (poisoned legacy entries are served for the full TTL).
- Write/read gate ASYMMETRY: `should_cache_price` fail-closes but the read-side chokepoint
  fails-open on the same input.
- Supplement page_scrape WRITE (scs ~5502) is ungated by `should_cache_price` (caches an OOS price).
- `should_cache_price` uses subset `_selection_match` → inherits Cluster A leaks into the cache.

## Cluster E — KPI / eval (CRIT/HIGH)
- KPI is DEAD CODE: `count_usable_exact_genuine`/`usable_exact_genuine_for_product` are never
  invoked by `run_eval`/`main`; no CLI run-mode. Wire `--kpi usable_exact_genuine`: load
  `data/usable_exact_genuine_truth.json`, POST each `truth.query` (cold + `--read-cache`), map by
  id to the per-product truth entry, aggregate per-category usable/requested.
- KPI calls `is_exact_match` (token EQUALITY) not `_selection_match` (what the orchestrator runs)
  → genuine descriptive prices score ~0/6, the 0.85 gate is unreachable. Use `_selection_match`
  OR independently validate the structured `expected` fields (storage/concentration/size/colorway).
- `count_usable_exact_genuine` without `truth_entries` silently skips the identity check (a wrong
  product counts as usable) — make truth mandatory / fail-closed when absent.
- Truth set has ZERO supplements (the hardest category) + 6/category makes 0.85 degenerate
  (5/6=0.833 fails). Expand to 30-50/category before treating the gate as live; add supplements.
- Fix `_metadata.how_measured` to match the code.

## Cluster F — chokepoint / reselect / category-inference (HIGH/MEDIUM)
- `reselect_to_target_value` (~2185) bypasses `_selection_match` (electronics-qualifier only) →
  ships a wrong makeup-shade/skincare-strength price. Add `_selection_match` there.
- Chokepoint backstop `_backstop_identity_ok` is token-free numeric-axis-only → can't catch
  wrong shade/colour-synonym/%-strength on a bypass path. Make it brand-tolerant identity-aware.
- Chokepoint is FAIL-OPEN on a no-title-no-url genuine-method price (Cardinal Rule violation).
  Decision needed: the 16-test "calibration" traded this away — re-enable a fail-closed
  no-identity/no-url pend for GENUINE-method prices while keeping the broad showable contract.
- `_infer_category_from_query` (~849) returns None for skincare/haircare/makeup/fashion/grocery →
  the new category axes are inert on the `extract_jsonld_price`/page-scrape path. Add detectors
  (`is_haircare_query` already exists).

## Cluster G — over-rejection (MEDIUM/LOW; the round-2 trap — fix WITH Cluster A)
- House-name prefix: "Christian Dior Sauvage"/"Gianni Versace Eros"/"Lancome Paris"/"Burberry
  London Her" false-pend (the fragrance near-equality rejects the extra house word). Add house
  aliases (Giorgio/Emporio Armani→Armani) + tolerate a known house-prefix.
- `_candidate_missing_query_axis` false-pends a genuine PDP whose title omits the concentration
  (carried in a separate attribute) — scan structured size/concentration attrs before "missing".
- Punctuation/spacing (No.3 vs No. 3; SPF30 vs SPF 30); z/s folding (moisturizing/moisturising).

## Cluster H — flag-OFF / telemetry (MEDIUM)
- Flag-OFF not byte-identical: `extract_jsonld_price` adds `name`/`brand` keys unconditionally;
  `public_price_view` passes them flag-OFF. Gate them, and add a real base-vs-branch GOLDEN
  response byte-compare (not per-helper asserts).
- Telemetry: only the final-gate `guard_rejected` is measured; selector/adapter rejections are
  invisible. Accumulate a per-request rejection counter (by reason) in `select_best` + extractors.

## EXECUTION (the antidote, applied)
1. EXTEND `tests/test_correctness_external_review_counterexamples.py` with ALL 42 as FAILING
   tests (both directions), reproduced through the runtime, FIRST.
2. Cluster B + C + D + E + F + G + H are mostly contained — implement TDD, comm-gate each.
3. Cluster A (the keystone) is the high-over-rejection-risk redesign — do it with per-category
   padding allowlists + both-direction tests + a dedicated over-rejection sweep.
4. RE-RUN the coverage-driven review workflow (`.qa-correctness/review_coverage.mjs`) — a single
   review pass confirms the prompter; the coverage sweep is what falsifies. Gate every finding.
5. THEN comm + flag-OFF golden + the wired KPI cold/warm. Warmer stays PAUSED.
