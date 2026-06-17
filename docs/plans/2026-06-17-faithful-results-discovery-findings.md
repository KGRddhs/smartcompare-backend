# Discovery Findings — Faithful Results + Genuine-BH (2026-06-17)

> Enhances `2026-06-17-faithful-results-genuine-bh-freetier-plan.md` (fills the `[per findings F-x]` placeholders). Source: dispatcher prefetch (9 cold `nocache` prod compares) + anti-bot head-to-head probes + ultracode discovery workflow (run `wf_3350515a-7c4`).

## Method + transparency (no silent caps)
- **Prefetch:** 9 cold `nocache` prod compares, 1 representative pair/category → `.qa-bias-rerun/_discovery/prod/*.json`.
- **Head-to-head:** firecrawl basic/enhanced + scrapedo render/super on CF-walled BH retailers + bolo follow-ups → `headtohead.json` + `sourcing_extra.md`.
- **Workflow (22 agents):** the 9 per-category **verify** agents + **fe-vs-design** + **headtohead** were **rate-limited** (transient server-side, NOT usage limit). The **verdict-reviews** agent + the **synthesis** agent (which ran its own substantiation pass against prod JSON + source lines) succeeded. ⇒ verdict/reviews/personalization/cohort findings are agent-substantiated; per-category **data** findings are from the prefetch; FE-vs-design + sourcing are dispatcher-analyzed. The dedicated adversarial-verify layer is INCOMPLETE — every finding below is nonetheless backed by prod-JSON evidence + a file:line anchor.

## Headline
**Session 63's keystone is HOLDING in prod** — dims category-correct across all 9, specs populated (11-13), zero citation-marker leaks. The **dominant remaining issue is GENUINE PRICE (Phase 1)**, plus **3 real verdict/scoring defects** and **2 auth-gated verification items**.

## ✅ Confirmed working — do NOT rebuild
- Category dimensions correct all 9 (fragrance=character/longevity/projection, supplements=efficacy/dosage/form, …).
- Specs populated 11-13 fields both products (except fashion asymmetry, F3.1).
- Citation cleaning: 0 `[N]`/`[snippet_N]` leaks (C5 holds).
- Runner-up case IS made at the **prose** layer (`key_tradeoff` + per-product `best_for`).
- Reviews emit ratings ONLY when real (no fabrication).

---

## Findings by plan phase

### Phase 1 — Sourcing + cache (HIGHEST LEVERAGE)
- **F1.1 [high] Genuine price is rare.** Only 4/9 got genuine `page_scrape_jsonld` (grocery both, skincare CeraVe, fashion Adidas, other Dyson); the rest are `converted_usd` (not genuine BH). This is THE genuine-share problem the cache+warmer attacks.
- **F1.2 [high] Two wrong-cheap sample prices.** Tobacco Vanille **28.2 BHD** (genuine ~118 — a decant/all-over-body-spray leak), K18 **4.51 BHD** (genuine ~30+). → fragrance/haircare designer floor + size/SKU plausibility guard (extends `is_implausible_low_fragrance_price`).
- **F1.3 [high] Supplements: no price + empty verdict.** NOW Foods/Solgar D3 → `price=None`, and the request hit the 30s `STREAM_HARD_CAP` at 31.0s → `metadata.partial=true`, `comparison={}`, `recommendation=''`. Latency wall + price gap. (`structured_comparison_service.py:1605-1637`)
- **F1.4 [med] Sourcing verdict (your firecrawl/scrape.do question).** Firecrawl `enhanced` does NOT crack Cloudflare; Scrape.do `super` DOES (proven — 671KB real Bolo render) but is **$249/mo Business** (free plan 401s after a trial). **Free-tier path = curl-extractable non-CF genuine sources + cache + honest `converted_usd`.** Future luxury lever = Scrape.do Business. (`sourcing_extra.md`)
- **F1.5 [planned] Cache architecture** — long-TTL genuine (24h→7-30d), negative-cache structural dead-ends, warm-once-serve-long, cache-first before render, fairness-correct keys, hit-rate observability.

### Phase 2 — FE prune → design
- **F2.1 [med] Extra HeroRings card not in design.** Live `ResultsContent.tsx:329-414` renders a score-rings card the design omits → prune.
- **F2.2 [high] Runner-up caption SUPPRESSED.** `ResultsContent.tsx:297-316` renders `FactualVerdict` and skips the runner-up caption block whenever `scoring_v2.factual_verdict.line1` exists (≈ always). FE half of the runner-up gap.
- **F2.3 [med] Heavy section chrome** (bordered secondary-bg cards) vs the design's lean treatment.

### Phase 3 — Category render
- **F3.1 [med] Fashion specs asymmetric** (Adidas 5 vs Nike 11) — schema/extraction gap for fashion.
- **F3.2 [needs-auth] cohort_summary** absent for anonymous probes (correct behaviour). Code path sound (`structured_comparison_service.py:2763-2808` + `response_builder.py:1357-1378`) but UNEXERCISED — verify it emits `{peer_count, governorate}` end-to-end for an authed cohort user.
- **F3.3 Category profile blocks** (fragrance notes/longevity, supplements dosage/count) — confirm each renders from payload.

### Phase 4 — Verdict / personalization
- **F4.1 [med] FRAGRANCE LONGEVITY CONTRADICTION.** `scoring_v2.dimensions.longevity` = Ombre wins (+8pt), but `key_tradeoff` + cons + reviews say **Tobacco** wins all-day longevity. `verdict_validation` passed it (`winner_aligned:true`). Reconcile the longevity scorer with the review-extracted signal, OR have `trust_validation_service` cross-check `key_tradeoff`/cons longevity claims vs the longevity dimension winner. (`scoring_service.py` longevity scorer + `trust_validation_service.py`)
- **F4.2 [med] EMPTY TRADEOFFS when winner sweeps.** `compute_tradeoff_pairs` returns `[]` if loser wins 0 dims `>5pt` (`scoring_service.py:1961-1962`). Both samples → `overview.tradeoffs=[]`, the dedicated "where the runner-up wins" card renders nothing. Backend half of the runner-up gap → fall back to the loser's single best dimension.
- **F4.3 [high] Personalization weaving NOT validated in the MAIN verdict.** Only the `personalized_insights` side-array is structurally validated; the prompt instructs weaving priorities into `winner_reason`/`best_for` (rules 2 & 8) but nothing enforces it. **This is Ahmed's "personalization isn't clicking."** Ensure the verdict prose NAMES the user's priorities. (`extraction_service.py:1059-1095, 1570-1576, 1705-1714`)
- **F4.4 [med] Partial-path empty verdict.** On hard-cap, emit at least a deterministic-scoring verdict (`winner_reason` from scores) so the user gets SOMETHING. (`structured_comparison_service.py:1605-1637`)
- **F4.5 Prompt enrichment** — `best_for[loser]` should name a CONCRETE buyer who'd prefer the runner-up, not just describe the product.

### Phase 5 — Reviews (paraphrase)
- **F5.1 [change, NOT no-fix] Current = verbatim + source-cited.** The audit confirmed reviews are verbatim raw snippets with source domains (e.g. fragrantica.com 4.32/5). **Per Ahmed's directive the TARGET is paraphrased praise, no citations** — so this confirms the current state Phase 5 must CHANGE. Convert `build_retailer_quotes_from_reviews` to a synthesized praise line (non-verbatim, no markers), real-only ratings preserved. (`review_service.py:243-306`)

### Phase 6 — Fairness
- **F6.1 electronics honor-each WORKING** — 256GB vs 128GB both shown (not pended); verdict `key_tradeoff` acknowledges "iPhone offers a larger storage capacity of 256GB". Good.
- **F6.2** Verify grocery weight-fairness (Nutella 750g vs Biscoff 400g) + the rest from the prefetch JSONs.
- **F6.3** Fragrance size + designer floor (ties to F1.2).

### Phase 7 — Eval
- B2 smoke20 `--persist` baseline + regression gate + A4 cache-reading variant, as planned.

## Verification gaps (close in Phase 8)
- **Authenticated re-run** for personalization weaving (F4.3) + cohort_summary (F3.2) — Ahmed is signed-in with prefs on-device and already observes the personalization gap, so the Phase-4 fix targets the root cause; the authed re-run is the post-fix proof.
- The per-category **adversarial-verify** layer was rate-limited — optional `Workflow({scriptPath, resumeFromRunId:"wf_3350515a-7c4"})` to complete it if deeper rigor is wanted before the team runs.
