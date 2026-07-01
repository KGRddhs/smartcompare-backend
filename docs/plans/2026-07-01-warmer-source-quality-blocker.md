# Warmer source-quality blocker — fix plan (must precede Wave 2)

**Origin:** the Wave-1 warmer gate came back RED (1/18 usable; `docs/investigations/2026-06-30-warmer-kpi-result.md`). The warmer *machinery* (PR #12) is correct + safe — PR #9's fail-closed `should_cache_price` correctly refuses the low-quality resolutions the price cascade currently produces, so the warmer caches ~nothing. **This plan fixes the upstream source quality so genuine prices become cacheable; only then does warmer activation (and Wave 2) make sense.**

**Branch:** `feature/genuine-price-source-quality` (off main `cdaf5c5`).

## The 6 facets (from the 18-product gate diagnosis)

**PROGRESS: warmed KPI 1/18 → 5/18** (fragrances 0→3, fashion 0→1) after the identity + listing-url + brand fixes. Remaining gap to 0.85 is the coverage/determinism/OOS/PDP-discovery facets below.

| # | Facet | Count | Status |
|---|---|---|---|
| P1a | **JSON-LD page-scrape prices carry no identity** | ~6 | ✅ **FIXED** (`8746377`) — proven 0→3 frag, 0→1 fash |
| P1a2 | JSON-LD fix dropped the matched `brand` (brand-field-only PDPs) | ~1 | ✅ **FIXED** (brand-forwarding) — sweep MED |
| P2 | genuine prices served with **search/listing URLs** (WP `?s=`) | ~2 | ✅ **classifier FIXED** (`eb366ad`) — now correctly rejected; PDP-discovery to RECOVER them is ⏳ |
| P1b | one `local_bhd` DB-served path returns no identity | 1 | ⏳ = the DB round-trip (my Wave-1 fix; needs migration + flag ON) |
| P3 | **no genuine source** found (→ `gpt_organic_extract` / `converted_usd`) | ~6 | ⏳ coverage (biggest lever) |
| P4 | genuine PDP but **out-of-stock** | 3 | ⏳ |
| P5 | **non-determinism** (races genuine vs converted) | ~2 | ⏳ |

**Over-rejection sweep (`wf_3f7d0dbd`, coverage-driven, both directions):** the JSON-LD identity stamp introduces NO new over-rejection through the full `extract_price_from_html` path — the ONE real regression was the dropped brand (fixed). AirPods-charging-case / Centrum-50+ / Anthelios-SPF-50+ are NOT-EMITTED (filtered UPSTREAM by `extract_jsonld_price`'s own `_selection_match`) → **pre-existing PR#9-matcher token over-rejections (the Wave-2 / VariantDescriptor class)**, not introduced here. The listing-url fix: 0 over-catch / 0 under-catch across 20 real PDP + 15 real listing + 22 edge URLs.

### P1a — JSON-LD identity (DONE, proven)
`extract_price_from_html`'s JSON-LD branch built its result with **no `name`/`title`**, while the OG/microdata/WC branches already stamp `name` (the M2 pattern). Fix (`8746377`): stamp `result["name"] = price_data.get("name")` (the matched Product name, flag-gated). **Proven live:** YSL Black Opium → `page_scrape_jsonld` + identity + `should_cache_price=True` (was False). Test `tests/test_jsonld_identity_stamp.py`.

### P1b — audit every genuine `source_method` path for identity
Most `local_bhd` paths DO stamp `title` (shopping `5505`, nasser `7204/7361/7496`, sitemap `6894/6993`). But a live iPhone resolution returned `local_bhd 431.684` with `ident=None`. **Task:** a coverage-driven per-path trace — for EACH genuine method (`local_bhd` shopping vs adapter vs discovery-PDP, `page_scrape*`, `woo_store_api`, `salla_api`, `occ_rest_bhd`, `magento_graphql_bhd`, `rest_json_bhd`, `shopify_json`, `zyte_render_bhd`), resolve a real product and assert the returned price carries `title` OR `name`. Stamp identity anywhere it's missing (flag-gated, using the listing's real name — never the query).

### P2 — search/listing URLs served as genuine
- sharafdg `local_bhd` arrives with `https://bahrain.sharafdg.com/?s=<q>&post_type=product` (a WP search URL) — and `_is_listing_url` classified it **NON-listing** (a gap: it doesn't catch WP `?s=` search). noon `local_bhd` arrives with `noon.com/search?q=...` (correctly caught). **Task:** (a) extend `_is_listing_url`/`is_non_pdp_listing_url` to catch WP `?s=` + other search-query URLs so a search-page price is never cached (fail-closed, correct); (b) BETTER — a PDP-discovery step that resolves the retailer search to the actual PDP URL (so the genuine price gets a real PDP + caches). (a) is the safe floor; (b) is the coverage win.

### P3 — coverage gaps (no genuine BH source)
iPad Air M2, MacBook Air M3, Nintendo Switch OLED, Nike AF1, Ray-Ban RB3025, Levis 501 fell to `gpt_organic_extract` (no URL → never cacheable) or `converted_usd`. **Task:** wire genuine BH sources for these categories/brands — the catalog adapters already discovered (`data/bh_gcc_sources.json`, the 274 live rows) + the electronics/fashion retailers (extra/sharafdg/noon PDPs, ounass, level shoes). This overlaps the BH/GCC source build epic.

### P4 — out-of-stock
Acqua di Gio (ounass), La Vie Est Belle (alhajis), Tommy Hilfiger (ounass) resolved genuine PDPs but `in_stock=False`. **Task:** verify the OOS is real (vs an availability-parse bug); if real, find an in-stock alternate retailer for the truth set (or accept these as legitimately unavailable — the KPI correctly excludes them).

### P5 — non-determinism
The same query resolves to a genuine PDP on one run and a converted/search result on the next (Samsung: `local_bhd 426.22` vs `converted_usd 144.59`). **Task:** make the genuine-source cascade deterministic — prefer a genuine PDP hit over a converted/shopping fallback consistently (source ordering + a stable tiebreak), so the warmer reliably lands the cacheable variant.

## Method (each facet)
recon (coverage-driven, reproduce through the runtime selector) → TDD fix (flag-gated where it touches the live path, byte-identical flag-OFF) → **coverage sweep** (adding identity makes the chokepoint backstop RUN on more prices — verify NO over-rejection of correct products, the PR #9 discipline) → comm gate (branch-only-NEW == [] vs `.qa-correctness/main-baseline-failed.txt`) → re-warm the KPI truth set + re-measure (`scripts/warm_kpi_truth.py` + `eval_runner --kpi usable_exact_genuine --read-cache`) to quantify the KPI lift.

## Exit criterion
Per-category warmed `usable_exact_genuine` KPI ≥ 0.85 (the same gate PR #12 built). Then: activate the warmer (runbook `docs/runbooks/2026-06-30-warmer-activation.md`) → **then** build Wave 2 (VariantDescriptor).

## Gotchas (carried)
- The identity stamp must use the **listing's real name** (extractor/JSON-LD/adapter), NEVER the query — else it trivially self-matches and defeats the exact-SKU gate.
- Adding identity is a CORE-PATH change (not warmer-inert) → coverage-sweep for over-rejection before merge; flag-gate (`exact_gate_enabled()`) for flag-OFF byte-identity.
- `nocache=True` local warm/resolve STILL WRITES the shared prod cache (bypasses the READ, not the WRITE).
- Run the heavy coverage sweeps in a FRESH session (rate-limit throttle worsens with session length).
