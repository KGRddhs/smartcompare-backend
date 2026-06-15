# Genuine-Share Push + Polish — follow-on to the genuine-bh-latency-warmer bundle

**Context:** The latency+warmer bundle shipped (main `2c27c5e`): timeouts are graceful, no regression, Sentry clean. Genuine-BH-share is the remaining primary KPI — prod cold ~18.9% (smoke20), warmed ~33% (S3 probe), ceilinged by the **structural-estimate categories** (Cloudflare-walled luxury fragrance/haircare/gadgets — see `docs/investigations/2026-06-15-render-wall-bh-retailers.md`). This follow-on pushes genuine-share up AND tightens the just-shipped bundle.

**Team model:** re-engaged 4-lane Opus team (be-core, be-sourcing, test, qa) on team `genuine-bh-glb`. Opus only. Cross-QA mandatory. Path-restricted commits. Verify "complete" via `git show`.

## Thrust A — Genuine-BH-share (be-sourcing lead)
- **A1 Discovery (budget-capped):** find + add CF-FREE genuine BH sources for the structural categories (luxury fragrance beyond alhajis/ajmal/asgharali; premium haircare; gadgets) via targeted Serper/curl-JSON-LD probing. **HARD CAP ≤100 Serper for the scoping pass; report cost + findings to dispatcher BEFORE any broad add.** Add winners to the source registry + verify liveness (`scripts/verify_source_registry.py`). Prefer Shopify `/products.json` + JSON-LD (no render needed).
- **A2 Warmer catalog:** expand `data/warmer_catalog.json` with more real-traffic + gold-covering structural pairs. FREE (code only; warming runs on Ahmed's Railway cron, not locally). Keep separate from `validation_gold_truth.json`.
- **A3 Structural-estimate attack:** for the CF-walled luxury (sephora.bh/bolo.bh/boutiqaat), is there ANY reachable genuine source (alt retailer, brand `.com`, public API, or a *justified* CF-bypass)? Document findings + a recommendation. **Firecrawl ≤ a handful of targeted URLs — never broad (450 lifetime).**

## Thrust B — Quality polish
- **B1 Cold-partial fragrance fallback (be-core):** extend the accuracy guards to fragrance size-plausibility — on a hard-cap PARTIAL, reject/suppress an implausibly-low fragrance converted price (the prod smoke surfaced Ombré Leather 19.93 BHD = a sample-grade listing) and prefer a plausible full-size price or none. Don't regress `is_implausible_high_value_price` / the wrong-SKU guard. Red-green tests.
- **B2 Eval rigor (qa):** create a PROPER smoke20 baseline — run `eval_runner --subset smoke20 --persist` against current prod and record the new baseline run-id, so future regression gates compare like-to-like (the documented `4aee8e88` is `subset:"full"`, which mismatches the smoke20 gate). Update `docs/runbooks/qaren-eval.md` + the CLAUDE.md eval-gate note. ONE run, `--concurrency 1`.
- **B3 Test-infra hygiene (test):** mark `test_phase1_includes_reviews` / `test_phase1_per_race_timeouts` / `test_unified_search` as `live_unit` (they make real network calls but slip the free-unit filter); fix the `test_share_routes` `SUPABASE_URL` delenv-without-restore pollution; broaden the `limiter.reset` autouse fixture where the cross-file 429-flake surfaced.
- **A4 Cache-reading eval variant (qa/test):** the eval uses `nocache=true` (cold) so it cannot measure the warmer's cached genuine-share. Build a cache-reading eval variant to measure the warmed genuine-% (the 70% target). Measures meaningfully only AFTER Ahmed activates the warmer.

## Budget guardrails (Serper finite ~2,000 left, shared with live)
A1 discovery ≤100 Serper, report before broad. A3 Firecrawl ≤ handful targeted. qa eval = 1 smoke20 run `--concurrency 1`. NO broad local warming (Ahmed's cron). Cache-disabled repro via `.qa-bias-rerun/` (in-script blank SUPABASE/UPSTASH after import — no prod write).

## Gate / DoD
Cross-QA each lane vs `git show`; free unit suite green (no regression); B2 smoke20 baseline persisted + runbook updated; B1 fragrance-plausibility tests green; no forbidden vocab (EN/AR); `npx tsc --noEmit` clean if FE touched. Then merge `--no-ff` → Railway deploy → prod-smoke. Genuine-share gains land when Ahmed fires the warmer cron.

## Thrust C — FRAGRANCE RESULT-QUALITY (found ON-DEVICE 2026-06-15, screenshots — HIGH priority)
Tom Ford Ombré Leather vs Tobacco Vanille LOADED in-app (timeout-crash fix ✓), but the result had multiple content mistakes:
- **C1 Prices sample-grade, not genuine** — Ombré **25.19 BHD** / Tobacco Vanille (30 ML) **28.2 BHD** (genuine Tom Ford 100ml ≈ 80+ BHD; the diagnosed Al Hajis price was 80). B1's designer-fragrance floor (25 BHD/100ml basis) is **TOO LOW** — 25.19 slipped just over it. RECALIBRATE the floor up (designer 100ml ≥ ~50-60 BHD) AND check `source_method` (these read as sample/decant listings, not full-bottle). This is a miscalibration of THIS bundle's B1 — our miss.
- **C2 Inconsistent size basis** — product_0 shows NO size, product_1 shows "30 ML" → the "BHD 3.01 less" delta + the verdict are apples-to-oranges. Needs the WS5-deferred option-B (cross-product size consistency in the orchestrator, using the price.size annotations).
- **C3 "Build" dimension on a FRAGRANCE** — nonsensical (screenshot: "Build 30/40, +10pt build"). `CATEGORY_DIMENSIONS` (scoring_service) must use scent dims (longevity/sillage/projection/scent) for fragrances, not Build/Feature. PRE-EXISTING.
- **C4 Product_1 specs ALL blank (—)** — Tobacco Vanille scent family/notes/sillage/concentration empty in the table while product_0 is populated. Spec-coverage failure for the 2nd product. PRE-EXISTING.
- **C5 Raw citation markers** — review text shows literal `[2] [3] [5] [8]` instead of source attributions → `_clean_review_citations()` not replacing snippet indices. PRE-EXISTING.
- **C6 (minor)** Reviews "1.0 stars higher" (88/82) while product_1 rating shows "N/A · N/A" — inconsistent rating vs review-score.
Scope: C1 (B1 recalibration) + C2 (WS5 option-B) are bundle-adjacent; C3/C4/C5/C6 are pre-existing fragrance/scoring content bugs now visible because the comparison no longer crashes. Likely a focused "fragrance result-quality" sub-bundle.
