# Bundle B — S2 "Intelligence" Design Inputs Dossier

> Audience: S2.0 planning session + Ahmed. Baseline: `eval_runs` row `4aee8e88` (2026-06-10, gold-200, concurrency 1) — **21.0% weighted pass**; axes price .455 / specs .708 / winner .360 / factual .770; p95 30.7s vs 30s cap. Lane binding + exit criteria: `2026-06-10-bundle-b-s2-prep-notes.md` §0. Raw evidence: `.qa-bias-rerun/baseline_s1_per_query.jsonl` (+`_diag_themes.py`, `_winner_fail_dump.json`), `data/validation_gold_truth.json`, the F1.7 routing-evidence doc.

## 1. Failure taxonomy

200 queries = **42 passing + 112 graded-but-failing + 46 error/timeout** (39 http_400, 6 http_502, 1 hard timeout — elec-019, 40.0s). Error rows zero ALL axes and suppress every headline number:

| Axis | Baseline | Decomposition |
|---|---|---|
| factual .770 | = 154/200 exactly | **0 genuine factual failures** — gap is 100% error rows |
| specs .708 | ≈ .92 graded mean × 77% graded | graded specs are healthy |
| price .455 | 91/200 pass | 109 fails = 63 answered-out-of-band + 46 starved-by-error |
| winner .360 | 72/200 pass | 128 raw fails = 82 graded + 46 error |

| Cat | n | pass | win-fail | price-fail | err | graded win-fail rate |
|---|---|---|---|---|---|---|
| electronics | 34 | 2 | 16 | 15 | 12 | 73% |
| grocery | 32 | 5 | 14 | 16 | 5 | 52% |
| supplements | 22 | 1 | 2 | 1 | **17** | 40% |
| haircare | 21 | 6 | 6 | 10 | 2 | 32% |
| skincare | 19 | 4 | 9 | 3 | 4 | 60% |
| other | 19 | 5 | 8 | 4 | 5 | 57% |
| makeup | 18 | 8 | 8 | 4 | 0 | 44% |
| fragrances | 18 | 4 | 9 | 7 | 1 | 53% |
| fashion | 17 | 7 | 10 | 3 | 0 | 59% |

**Pure winner-bias set: 45 ids** (no error, price+factual pass, specs ≥0.5, winner fails) = 29.2% of 154 graded. Spread: fashion 7, makeup 6, skincare 6, grocery 6, fragrances 6, other 5, electronics 4, haircare 3, supplements 2. Only 2 of 45 are over-cap — clean judgment failures.

**Flip arithmetic, winner .360 → ≥.60:** 72 → 120/200 passes = **48 net flips**. The pure-bias set maxes at +45 → 117/200 = **0.585 — short even at 100% conversion**. The exit therefore structurally needs BOTH lanes: realistic 60–70% conversion of the 45 (+27–31), remainder from (a) the 46 error rows (graded winner-pass runs 46.8% → full recovery ≈ +21) and/or (b) the 37 compound fails. **I1/I2 alone cannot reach 0.60; I5 error-path recovery is load-bearing for the winner gate.** (Edge: supp-010, skin-012 fail solely on specs_score=0.0.)

## 2. Ranked bias hypotheses → countermeasures

82 graded winner-fails; themes multi-tagged, each (id,theme) pair backed by a verbatim rationale substring. **Meta-signal: 32/82 (39%) gold rationales carry an explicit Bahrain/GCC/Gulf marker — 34/82 (41%) counting broader localization wording ('everyday Emirati dates', 'Local market favourite') — Ahmed grades as a Bahrain buyer; the engine grades a global spec sheet.**

| H | n/82 | Gold evidence (verbatim) | Countermeasure (anti-pattern → few-shot) |
|---|---|---|---|
| **H1 value-per-dinar** | 21 | "e.l.f. Halo Glow delivers a similar lit-from-within glow at a fraction of the Charlotte Tilbury price" | AP "spec-sheet edge beats price parity." FS: parity specs + large price gap → cheaper wins with value framing |
| **H2 GCC brand resonance** | 14 | "Lattafa Yara… is the GCC viral crowd-pleaser with broad daily appeal" | AP "global prestige outranks GCC market reality." FS: regional staple vs import → staple wins on adoption |
| **H3 premium-justified** | 13 | "Daikin's compressor reliability… justify the premium for long Bahrain summers" | AP "cheaper always equals better value." FS: durable premium vs budget rival → premium wins, justification language |
| **H4 local presence/service** | 12 | "Epson EcoTank's… reliable refill availability in Bahrain" | AP "identical on paper = identical in Bahrain." FS: Bahrain consumables/service ecosystem breaks a spec tie |
| **H5 use-case/audience fit** | 12 | "CeraVe's encapsulated retinol… gentler for beginners" | Heterogeneous; persona-sentence garnish in rationales, not a primary AP |
| **H6 heritage/gold-standard** | 11 | "Clinically established formulation gold standard" | AP "newer spec sheet beats canonical benchmark"; rides H3 exemplars |
| **H7 durability/ownership horizon** | 9 | "Citizen Eco-Drive's solar movement needs no… battery swaps" | Covered by H3 few-shots carrying durability language |
| **H8 Gulf climate** | 7 | "Rimmel Stay Matte's shine control lasts well through humid days" | AP "climate-neutral verdicts in a 45° market." Short, unambiguous — ideal few-shot clause |

**H1+H3 are a disjoint mirror pair (34/82, zero id overlap): price-positioning judgment is broken in BOTH directions** — exemplars must teach the discriminator (when value wins vs when premium is licensed), never a direction. **Not a data-layer problem:** graded specs means equal (.915/.924); price_pass=false 43% among fails vs 39% among passes. **Residuals:** (i) position bias — expected_winner_index=1 fails 65% (33/51) vs 48% (49/103) for index 0, surviving the v2.2 phantom-tie work; (ii) 11/82 fails are pure spec-superiority — engine home turf, evidence for position bias, low-precision for few-shots; (iii) ecosystem (4) too small to rank.

## 3. I1/I2 design recommendation

**Exemplar selection.** Mine the 45-id pure-bias set — single-axis failures are unambiguous teaching signal. Per category ≤3 compact exemplars: one H1 + one H3 (the discriminator pair) + one category-precise third — H8 for skincare/makeup/appliances (skin-013, make-013, skin-009, other-019), H2 for grocery/fragrances/makeup (groc-002, frag-016, make-011), H4 for electronics (elec-024, elec-018); strong H1 templates supp-013, make-016, groc-009, skin-018. **Contamination rule: exemplars are synthetic rewrites of these patterns (different brands, same structure), never verbatim gold pairs — else the 0.60 re-measure is trained-on-test.** Migration 027 `winner_correct` feedback is the future uncontaminated curation source.

**Anti-pattern phrasing.** Named failure mode + one-line counter-rule, e.g. "ANTI-PATTERN — spec-sheet edge at price parity: when performance is near parity, prefer the lower Bahrain price on value-per-dinar UNLESS a durability, service-network, or update-guarantee gap licenses the premium." Global APs (H1/H3 discriminator + localization directive) extend `COMPARISON_SYSTEM`'s RULES (`extraction_service.py:613-621`; `:614` is precedent); per-category APs sit beside exemplars. All injected text must pass the forbidden-words audit (`tests/test_comparison_quality_detector.py:180`) — no "estimated", no scary vocab.

**Mechanism (per architecture map).** New `data/verdict_exemplars.json` keyed by the 9 categories `{exemplars, anti_patterns}`; `@lru_cache` loader + `build_exemplar_block(category)` + `reset_cache()` mirroring `pain_workflow_loader.py:54-82`. Inject after `build_personality_prompt` (`extraction_service.py:1178`; `:1132` in `build_verdict_prompt`), BEFORE pain-workflow `:1184` — inside the static-per-category prefix for OpenAI prompt caching (D2 discipline). **Also fix the drift: prod `generate_comparison` (`:1152-1321`) never injects `_WEIRD_VERDICT_INSTRUCTION`; test-only `build_verdict_prompt` does — unify prod onto `build_verdict_prompt` so audits grep what production runs.**

**Token budget.** Current prompt ≈2,700–3,100 tok (~$0.008/call on 4o). Compact exemplars (150–250 tok ×3 ≈ 700) + ~100 tok APs ≈ **+$0.002/call** — fits the $0.015 ceiling alongside at most ONE of I3 critique (≤$0.002) / I4 multi-agent (+~$0.005). Full-schema exemplars (~1,200 tok) rejected.

**Format constraints.** JSON-mode safe: label "EXAMPLE — do not copy"; exact schema `:582-611` (winner_index 0/1; winner_reason <20 words with a number; `value_context`/`best_for` per-product dicts — PR #7 regression; pros 4–6 / cons 2–4 never empty); omit `personalized_insights`; `validate_verdict` cross-check unchanged.

**Position-bias check (one targeted experiment).** Re-run ~20 index-1-expected fails with product order swapped; if winners follow position, the fix is order-neutrality in scoring tie-breaks/verdict prompt — worth up to ~15 flips independent of few-shots.

## 4. Lane I5 "Yield & Wall" — scoped work items (ordered)

Latency: p50 23.2s / p90 30.5s / p95 30.7s / max 40.0s; worst per-category p95 electronics 33.9s, supplements 31.3s, skincare 31.0s; 14 graded ids sit at 27–30s (10 if the 4 wall_over_cap graded rows are excluded).

**Scrape-yield verdict (electronics 0/14 vs grocery 3/5): PRIMARY cause is discovery.** The electronics Bahrain `site:` query is built exclusively from DNS-dead, never-live-verified domains (`lulu.com.bh`, `carrefourbh.com`, `sharafdg.com.bh`, `extra.com.bh`, `geant.com.bh` — all `curl (6)` 2026-06-10), and `build_site_discovery_query(..., limit=4)` (ssc:2612 → source_router.py:159-161) slices exactly those 4 dead rows; live, F1.5-verified `shopalmoayyed.com` sits 9th and is never queried. Grocery survives because `talabat.com` (live, weight 3.0) is inside its window. JSON-LD parsing RULED OUT (shopalmoayyed list-offers and bh.asgharali dict-offers both parse via `extract_jsonld_price`); timeout RULED OUT (price walls 4.6–7.9s vs 15s cap).

| # | Item | Where | Axis impact |
|---|---|---|---|
| 1 | **Confirm http_400 = cap-cut, then fix the wall.** All 39 http_400 + the timeout carry wall_over_cap=true (the 6 http_502 don't) — consistent with the 30s outer `wait_for` surfacing as 400; verify via Railway logs FIRST | L2.7 cap path; levers below | 46 rows zero ALL axes; recovery at baseline graded rates ≈ +13pt price, +10pt winner, +21pt specs, factual →~1.0. Supplements (17/22 errored) is the unlock |
| 2 | Replace dead registry domains: `lulu.com.bh`→`luluhypermarket.com`, `sharafdg.com.bh`→`bahrain.sharafdg.com` (or delete — gcc row :80 covers), `extra.com.bh`→`extra.com`; carrefour/geant BH verify-or-delete (carrefour.com.bh also dead — never fabricate); verify behbehani/eros/jumbo | `source_router.py:28-32,40-42` | price OOB (elec 15, groc 16); exit: electronics tier1_5 hit_rate >0 |
| 3 | Get shopalmoayyed into the window: reorder verified-first OR `limit=4`→8 (same single Serper call, longer OR-chain) | `source_router.py:26-75` / ssc:2613 | electronics yield |
| 4 | Category-aware authorized/gcc discovery — farfetch/ounass strings are nonsense for an AC; build from registry gcc tier for non-fashion | ssc:2605-2606 | electronics/grocery price |
| 5 | **S2-safe latency stack = Levers 4+5+6:** `_get_price` concurrent with unified search (ssc:2051); behavior/demographics alongside product gather (:1347/:1761); cap the uncapped Phase-2 rating race ~4s (:2282/:2253) | ssc | **−1 to −2.5s mean, zero quality risk** → shrinks the 46-row error set + serves the p95<30s gate |
| 6 | Lever 3: fan_out 15s→12s + price race 18s→~14–15s (12s defensible; 10s needs-Ahmed). Escalation triggering untouched — never blind the instrument | ssc:2673 / :2088 | −3 to −5s escalating worst-case; risk: slow-but-successful Cloudflare/Scrape.do scrapes lose → more Tier-3 luxury prices |
| 7 | Per-domain `tier15:source_hits:{domain}` dashboard line + probe price-only cache-bust flag (binding §0 first task, ~10 min) | /admin/costs | yield observability = exit evidence |
| 8 | Registry liveness gate: `scripts/verify_source_registry.py` (HEAD-resolve all rows) + `live_unit` test | scripts/, tests/ | prevents recurrence |
| 9 | Serper ceiling reconciliation vs real balance + 80%-burn alert (S1 depletion incident) | api_budget_service | run integrity |
| 10 | Parser hardening: list-valued `@type`; `AggregateOffer.lowPrice` (defensive, not causal) | price_service.py:685,693,716 | future non-Shopify stores |

**Needs-Ahmed levers (NOT in the S2-safe stack):** Lever 1 reviews trim `[:4000]→[:2500]` + `max_tokens 1000→600` (−1–2s; pros/cons nuance cost D2 deferred); Lever 2 verdict∥reviews (recommend against — verdict goes review-blind); Lever 7 verdict on mini (recommend against — D2 rejected; truncated-JSON risk). Retailer anchors behind #2–4: LuLu family **43** failed bands, noon 28, carrefourbh 22, Sharaf DG 18, bn.boots 14, amazon.ae 14, iherb 11, talabat 11.

## 5. What S2 cannot fix (honest)

- **Bahrain shelf-price coverage.** LuLu/Carrefour BH are SPAs, talabat an app, Serper gl=bh shopping thin upstream. Registry fixes raise yield, but **price ≥0.70 is bound to S3 exit** (lanes S1–S4); long-term need is a real merchant feed (`memory/project_bahrain_shopping_feed_gap.md`).
- **H2/H4 have no data layer.** Few-shots teach the reasoning move, but GCC-adoption / Bahrain-service claims ride GPT prior knowledge — hallucination risk; a curated local-presence dataset is S3+ work.
- **Reviews+verdict ~9–10s sequential floor** stands (Lever 2 rejected); sub-22s cold walls need a quality trade.
- **Gold-set hygiene:** 35/109 failed bands have no provenance note (+2 domain-less) — band-defensibility work, separate lane.
- **supp-003/supp-002 persistent-slow iHerb pairs:** both are http_400 cap-cuts at 30.5s / 30.4s in this baseline — the previously cited 49–55s / 37s walls (prior F2.x measurements) are not reproducible from this run's evidence. F2.2 microdata fallback may help — re-measure; no S2 lever guarantees them.
- 6 http_502 = upstream transients (monitor). The **95% absolute gate binds at S3 exit**, not S2.

## 6. Open questions for Ahmed (beyond standing UX Decisions A/B)

1. **Exemplar contamination policy:** ratify synthetic-pattern exemplars (recommended) vs verbatim gold pairs with holdout-only reporting?
2. **H2/H4 scope:** may verdicts assert Bahrain availability/service/popularity from model prior knowledge (41% of gold rationales are localization-driven), or restrict S2 few-shots to H1/H3/H8 until a data layer exists?
3. **Lever 3 @12s** — ratify (10s explicitly needs you). **Lever 1 reviews trim** — take −1–2s now at pros/cons-nuance cost, or hold?
4. **Carrefour/Géant BH registry rows:** delete-if-unverifiable (forfeits the 22 carrefourbh-anchored bands until S3) or hold for verified domains?
5. **Position bias:** if the swap A/B confirms a mechanical product_0 lean, authorize a tie-break/order-neutrality change in deterministic scoring (smoke20-gated)?
6. **Cost envelope:** +$0.002 exemplar prefill assumed accepted; which of I3 critique / I4 multi-agent takes the one remaining promotion slot under $0.015?

## 7. S2 exit re-measurement protocol

1. **Mid-session leading indicators (cheap, before the full rerun):** (a) 45-id pure-bias subset after I1/I2 — target ≥60% flipped; (b) supplements-22 + over-cap set after wall levers — target errors 46→<10; (c) 20-query swapped-order position A/B.
2. **Full gold-200 rerun:** concurrency 1 (`docs/runbooks/qaren-eval.md`), `nocache=true`, same grader; new `eval_runs` row compared axis-by-axis vs `4aee8e88`, per-category + estimate-share in metadata. Pre-check Serper balance (~600–1,000 credits/run) — item #9 lands first.
3. **Gates:** winner ≥0.60 (≥120/200), reported BOTH full-set and excluding exemplar-template ids; electronics tier1_5 hit_rate >0 with elec-013/014/015-class priced `source_method != estimated`; p95 <30s and the 4 persistent-slow queries complete; factual →~1.0 (any genuine factual fail is a NEW regression — zero exist today); graded specs mean holds ~0.92; smoke20 at every merge (no axis >2pp drop).
4. **During the run:** Sentry watch + `/admin/costs` Serper canary; the per-domain `tier15:source_hits` line is the exit-review yield evidence.
