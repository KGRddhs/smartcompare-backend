# Backend Comparison Engine Overhaul — Design

**Status:** Design approved (brainstorming 2026-06-08, Ahmed + Claude).
**Owner:** Ahmed.
**Approach:** **C** — ship (A) Wiring + Quality sprint first (15–17 working days), then plan + execute (B) Intelligence Layer (6–8 weeks).
**Implementation plan:** to be authored by `superpowers:writing-plans` immediately after this design is committed.

---

## 1. Executive summary

The current backend comparison engine has correct architectural bones (per-request services, parallel Phase 1/2, category-aware extraction, fact-checking) but four load-bearing failures make the user-facing output appear "stupid":

1. **`scoring_v2` schema disconnect** — backend computes 6 category-specific dimensions per legacy `scoring.dimension_winners` but emits only 3–4 hand-coded generic dims (`price`, `reviews`, `value`, `popularity`) into `scoring_v2.dimensions`. Mobile reads v2 and renders identical generic bars for every category.
2. **5 design-parity shape gaps** — `factual_verdict.line1/2` NULL, `confidence_legs` + `confidence_details` NULL, no per-retailer review quote structure, no product variant string ("128GB · Black"), no per-row winner highlighting in specs table.
3. **Tier-cascade luxury-gated** — Firecrawl/Scrape.do fire ONLY for `is_luxury_brand()` queries; non-luxury queries with bad Tier 1 data (Tom Ford at 20 BHD) never escalate, no cross-validation.
4. **Prompts ignore documented user pain** — 400+ surveys + existing personality prompts show users want 2–3 clear differences with explicit budget/value framing and decisive verdicts; current verdict prompt produces hedge-y multi-spec recommendations.

Wall-time is **not** the primary problem (production: 25–29s typical; 88s is frontend rendering, not backend). Cost target ($0.01/comparison) is being met.

(A) fixes the wiring + rebuilds the tier-cascade around confidence-driven parallel multi-source races, adds 50-query Bahrain validation as a merge gate, instruments frontend 88s, and ships per-product-type schemas. (B) wires the social-source layer (Reddit/YouTube/Instagram/TikTok/Fragrantica/INCIDecoder/PubMed), implements the Living Prompt System driven by 400+ surveys + ongoing feedback, adds self-critique reasoning depth, and runs the automated 95% accuracy eval loop in CI + production sampling.

**No paid OpenAI fine-tuning.** The "smarter brain" is achieved via dynamic prompt engineering, RAG-style context injection, few-shot example rotation from top-decile feedback, and self-critique passes — all of which are free or cost <$0.002/comparison.

---

## 2. Audit findings — ground truth (2026-06-08)

Validated against 3 live production curls + Railway env + 4 parallel code agents:

| Claim | Reality |
|---|---|
| "88-second wait" | Backend = 25–29s. 88s is frontend (likely stage-card streaming + image load + min-display floor + OTA two-launch propagation). |
| "Only Serper fires" | 11–12 API calls per comparison; multiple Serper variants + 4–6 GPT calls + image fetch. Firecrawl/Scrape.do gated by `is_luxury_brand() AND ENABLE_PAGE_SCRAPE`; non-luxury queries (95% of traffic) never escalate. Railway env: `ENABLE_FIRECRAWL`/`ENABLE_SCRAPEDO`/`ENABLE_PAGE_SCRAPE`/`SCRAPING_MODE` ALL UNSET. |
| "Output structure faulty" | Confirmed. `scoring_v2.dimensions` has 3–4 generic dims for ALL categories. Electronics doesn't get camera/battery/storage; fragrances doesn't get longevity/sillage. Mobile design Screens 1–4 cannot render with current data. |
| "Per-category not applied" | Partially correct. `CATEGORY_SPEC_SCHEMAS` (9 categories) + `CATEGORY_DIMENSIONS` (per-category weights) + `prompt_personalities.py` (9 distinct tones) exist and work. BUT: 4/9 categories share a generic review-search-term fallback; rating tiers are uniform; review extraction prompt is single-shot for all categories. Most critically, **the category-aware data is computed but never copied into `scoring_v2`**. |
| "Missing data huge problem" | Wiring problem, not extraction problem. Data IS computed; just not piped to mobile-facing response keys. |

**Live production data (3 categories, 2026-06-08, all `nocache=true`):**
- Electronics (iPhone 15 vs Galaxy S24): 29s, 12 API calls, $0.0088. Specs 11 fields populated at `top.specs.products[i].specs`. `scoring_v2.dimensions`: ['price','reviews','value','popularity']. All dim winners NULL. `factual_verdict.line1/2`: NULL. `overview.products[i].pros_cons`: empty. Image URLs present.
- Fragrances (Tom Ford Black Orchid vs Creed Aventus): 28s, 11 API calls, $0.0076. Tom Ford price 20.68 BHD — **wrong** (real retail ~50–130 BHD; Tier 1 picked up a sample/wrong-variant).
- Supplements (Now Foods D3 vs Solgar D3): 25s, 12 API calls, $0.0086. iHerb scrape path firing correctly.

---

## 3. Architecture pivot — parallel multi-source races

**Replace tier-waterfall with multi-source parallel races per data type.** Cross-validation is mandatory regardless of single-source confidence.

```
For one product, inside Phase 1 (asyncio.gather, all 4 races parallel):

┌─ PRICE race (wait_for 15s) ───────────────────────────────────┐
│ Serper Shopping (paid, ~600ms)                                 │
│ Firecrawl on top Bahrain retailers (paid, 5–15s SPA-rendered)  │
│ curl_cffi page-scrape (free, top 5 organic URLs)               │
│ Scrape.do on Cloudflare-detected (paid, ~10s)                  │
│ GPT training-data estimate (cheap, ~1s) — runs as sanity check │
│ → cross-merge: median of agreeing sources within 20% bracket   │
│ → outliers flagged + dropped; <2 agreeing sources → confidence:low + escalate
└────────────────────────────────────────────────────────────────┘
┌─ SPECS race (wait_for 8s) ────────────────────────────────────┐
│ Serper organic + GPT-4o-mini extraction                        │
│ Official brand site (Apple/Samsung/LG/Sony/Tom Ford/etc.)      │
│ GSMArena (electronics.phone) / Fragrantica (fragrances) /      │
│   INCIDecoder (skincare) — category-vertical sites             │
│ → field-level majority across sources; per-field `_confidence` │
└────────────────────────────────────────────────────────────────┘
┌─ REVIEWS race (wait_for 6s) ──────────────────────────────────┐
│ Serper organic reviews                                          │
│ Per-retailer fetch ×3 (Amazon, Noon, X) for design Screen 2    │
│ Reddit search (B addition; wiring prep in A)                   │
│ YouTube review-count signal (B addition)                       │
│ → sentiment-aggregated; single-platform sentiment capped at    │
│   confidence:medium                                             │
└────────────────────────────────────────────────────────────────┘
┌─ IMAGE race (wait_for 5s) ────────────────────────────────────┐
│ Page-scrape og:image + JSON-LD (free, piggyback from price)    │
│ Serper Images (capped 500/day)                                  │
│ Brand official-site image (high confidence)                    │
│ GPT extraction last                                            │
│ → official brand domain ALWAYS preferred, even if slower       │
└────────────────────────────────────────────────────────────────┘

Phase 1 wall = max(price, specs, reviews, image) ≈ 8–12s typical
+ Verdict (gpt-4o, 4–5s) + Self-critique (gpt-4o-mini, 1–2s) + Moderation (0.5s)
= 13–20s typical, hard-capped at 25s on BOTH streaming + non-streaming paths
```

**Wall-time non-regression:**
- Best case (Tier 1 high-confidence) — unchanged 25–29s
- ~30% of queries (previously stuck at bad Tier 1) — now +5–10s escalation but quality jump fixes Tom Ford-class bugs
- Worst case — bounded by 25s outer cap (now wraps non-streaming too)

**Code changes:**
- `app/services/price_service.py` — rename `_build_luxury_scrapers` → `_build_escalation_scrapers`; remove `is_luxury_brand()` gate at line 2245; add `_compute_data_confidence()` helper
- `app/services/structured_comparison_service.py:996,1311` — wrap `compare_from_text` in `asyncio.wait_for(timeout=STREAM_HARD_CAP_SECONDS)` matching streaming path
- New: `app/services/confidence_service.py` — pure-function signal computation (no I/O)
- New: `app/services/source_router.py` — Bahrain-first source priority routing
- New: `app/services/product_type_router.py` — sub-category detection + schema lookup

---

## 4. Bahrain-first source hierarchy

**Strict ordered priority, applied globally across all 9 categories. Bahrain-weighted ×3.0, GCC ×1.5, Global ×1.0.** Cross-validation requires ≥1 Bahrain OR ≥2 GCC sources before emitting price as `confidence: high`.

| Tier | Source list | Categories |
|---|---|---|
| **Bahrain primary** | lulu.com.bh, Carrefour BH, Sharaf DG BH, eXtra BH, Geant BH, bn.boots.com, bolo.bh, behbehani, eros, jumbo electronics, talabat BH, Spinneys BH, Megamart BH | All 9 |
| **Bahrain social** | Bahraini Instagram brand-main accounts + `#bahrain_shopping`, TikTok Bahrain handles, bn-prefixed Twitter/X threads | All 9 |
| **GCC secondary** | noon.com, amazon.ae, sharafdg.com, Ounass, Bloomingdales ME, Tryano, Saudi/UAE retailers; Saudi/UAE Arabic reviews (Sayidaty, Sabq) | All 9 |
| **Global fallback** | Brand-official sites, GSMArena, Fragrantica, INCIDecoder, PubMed, global Reddit/YouTube, generic Serper | Only when Bahrain + GCC return empty |

**Halal/Ramadan/climate flags** (per CLAUDE.md design) added as metadata for grocery/supplements/makeup/skincare in (B).

---

## 5. Per-product-type spec schemas

`CATEGORY_SPEC_SCHEMAS` (9 entries) expands to `PRODUCT_TYPE_SPEC_SCHEMAS` (~55 entries). Detection function `_detect_product_type(name, category)` uses keyword matching + GPT-4o-mini fallback for ambiguous queries (<200ms, cached).

**(A) sprint ships 25 product-type schemas** covering the 50-query validation matrix:
- `electronics.phone | tv | laptop | tablet | smartwatch | headphones | speaker | ac | washing_machine | refrigerator | vacuum | gaming_console`
- `supplements.vitamin | mineral | protein | preworkout | fish_oil | multivitamin`
- `fragrances.edp | edt | niche`
- `makeup.foundation | lipstick | mascara`
- `skincare.serum | sunscreen | cleanser`
- `haircare.shampoo`
- `fashion.bag | shoe | watch`
- `grocery.oil | tea | chocolate`

Remaining ~30 added in (B) Phase B.4 as category-vertical sources come online.

**Schema field examples (full list in implementation plan):**
- `electronics.phone`: display, processor, ram, storage, battery, rear_camera, front_camera, os, 5G, weight, water_resistance, charging_w
- `electronics.ac`: capacity_btu, energy_class, inverter, noise_db, modes, filter, wifi, refrigerant
- `electronics.washer`: capacity_kg, spin_rpm, energy_class, load_type, programs, noise_db, inverter, dimensions
- `supplements.protein`: protein_g_serving, carbs, fat, calories, amino_profile, filtration, flavors, container_size
- `fragrances.edp`: concentration, longevity_hrs, sillage, projection_m, scent_family, notes_top, notes_heart, notes_base, volume_ml, season, occasion
- `fashion.bag`: material, lining, hardware, closure, dimensions, strap_drop, origin, weight

---

## 6. Living Prompt System (replaces paid fine-tuning)

**No OpenAI fine-tuning.** Cost-free alternative achieves "smarter brain" via:

```
┌─ Inputs ──────────────────────────────────────────────────────┐
│ 400+ survey responses (Eng + Arabic)                          │
│ comparison_feedback (useful, mattered_most, change_suggestion)│
│ user_events (clicks, screenshots, re-queries)                 │
│ pain_workflow_events (NEW — abandonment, re-query, share)     │
│ verdict_critiques (NEW — self-critique scores)                │
└───────────────────────────────────────────────────────────────┘
            │
            ▼
┌─ ETL → priors ───────────────────────────────────────────────┐
│ cohort_priors.json (existing — extend with survey #2 data)   │
│ pain_workflow_priors.json (NEW — 8 ranked pain workflows     │
│   with per-cohort weights)                                    │
│ decision_style_priors.json (NEW — "show 2–3 options" vs      │
│   "suggest one" vs "all details" per cohort)                 │
│ few_shot_verdict_examples.jsonl (NEW — top-10% feedback-     │
│   scored verdicts curated weekly)                             │
└───────────────────────────────────────────────────────────────┘
            │
            ▼
┌─ Dynamic prompt builder ─────────────────────────────────────┐
│ build_verdict_prompt(category, product_type, user_cohort):    │
│   1. Personality block (existing per-category)                │
│   2. Pain-workflow constraints (NEW — top 3 for cohort)       │
│   3. Decision style preference (NEW — "show 2–3, narrow down")│
│   4. User cohort context (governorate, language, age)         │
│   5. 3 few-shot examples (rotated weekly from top-decile)     │
│   6. Recent failure corrections (anti-patterns from eval)     │
│   7. Bahrain cultural lens (halal/climate/Ramadan flags)      │
└───────────────────────────────────────────────────────────────┘
            │
            ▼
        GPT-4o (verdict, base model — NO FT)
            │
            ▼
┌─ Self-critique pass (NEW) ───────────────────────────────────┐
│ GPT-4o-mini receives: (verdict + critique instructions)       │
│ Scores: bias, vagueness, hedging-language, missing-citation,  │
│   pain-workflow-alignment                                     │
│ If any score < 7/10 → regenerate with explicit feedback       │
│ Cost: ~$0.001/comparison; wall-time +1–2s                     │
└───────────────────────────────────────────────────────────────┘
            │
            ▼
┌─ Eval loop ──────────────────────────────────────────────────┐
│ 200-query gold set, weighted score:                          │
│   price within 15% × 25% + spec correctness × 25% +          │
│   winner-correct × 30% + factual claims × 20% = 95%+ to ship │
│ CI: every PR → run eval → fail if <95% any axis              │
│ Production: 5% sample scored against secondary source         │
│ Failures → root cause → prompt update → re-eval               │
└───────────────────────────────────────────────────────────────┘
```

**Pain-workflow priors (extracted from survey 2026-06-08):**

| Rank | Workflow | Prompt instruction injected |
|---|---|---|
| 1 | Close-option paralysis | "If scores within 10 points, EXPLICIT tie-break: 'if budget matters → A, if X matters → B.' Never 'both are good.'" |
| 2 | Too many specs/options | "Surface MAX 3 differences in `key_tradeoff`. Never list 6+ specs in the verdict text." |
| 3 | Value/budget uncertainty | "Open verdict with value-per-BHD comparison and budget alignment. Cite price first, scores second." |
| 4 | Trust paralysis | "Cite source counts: 'Confirmed by 3 retailers + 2 reviewer publications.' Never bare claims." |
| 5 | Post-decision regret | "Explicitly name the trade-off the buyer is accepting. 'Choosing A means you give up Y.'" |
| 6 | Brand-loyalty vs evidence | "If user's preferred brand loses, acknowledge: 'Brand X is known for Y, but here Z wins on the specifics that matter for your priorities.'" |
| 7 | Warranty/aftersales missing | "Surface warranty + return policy when applicable. Penalize products lacking it." |
| 8 | Decision speed | "Lead with TL;DR ONE-SENTENCE winner. Detail follows for tap-to-expand readers." |

---

## 7. Frontend 88s instrumentation

Sprint adds per-stage timing to streaming SSE events + Sentry tag breakdown:

```
TTFB → first_card_visible_ms → all_cards_visible_ms → ready_celebration_ms → user_tappable_ms
```

Hypothesis ranking (verified via instrumentation, fixed in Wave 2):
1. `StreamingProductCard` stage-gated reveal blocking on missing event keys
2. Image decoding on slow GCC mobile network
3. OTA two-launch propagation (stale cached bundle)
4. SSE `settle_complete` flush delayed by post-Phase-1 verdict + moderation
5. JS bundle re-download on cold app launch

---

## 8. 50-query Bahrain validation matrix (merge gate)

**Hard merge gate for (A): ≥80% pass rate or architecture pivots again.**

Test queries span all 9 categories × multiple product types (NOT just flagships):

| Category | Sample queries |
|---|---|
| Electronics | iPhone 15 vs Galaxy S24, LG OLED55C3 vs Samsung QN90C, Dyson V15 vs Shark Stratos, Carrier 1.5T AC vs LG 1.5T AC, Sony WH-1000XM5 vs Bose QC Ultra, PS5 vs Xbox Series X, MacBook Air M3 vs Dell XPS 13, Xiaomi 14 vs Nothing Phone 2 |
| Supplements | NOW D3 vs Solgar D3, Optimum Nutrition Whey vs Dymatize ISO100, Centrum Multi vs One A Day, MyProtein Creatine vs Bulk |
| Fragrances | Tom Ford Black Orchid vs Creed Aventus, Dior Sauvage vs YSL Y EDP, Hugo Boss Bottled vs Davidoff Cool Water, MFK Baccarat Rouge vs Initio Oud for Greatness |
| Makeup | Fenty Pro Filt'r vs Maybelline Fit Me, MAC Ruby Woo vs Charlotte Tilbury Pillow Talk, Maybelline Sky High vs L'Oreal Telescopic |
| Skincare | CeraVe Cleanser vs La Roche-Posay Toleriane, The Ordinary Niacinamide vs Paula's Choice 10%, Drunk Elephant C-Firma vs SkinCeuticals CE Ferulic |
| Haircare | Olaplex No. 3 vs K18 Leave-In, Pantene Pro-V vs Head & Shoulders |
| Fashion | Birkenstock Arizona vs Teva Universal, Nike Air Force 1 vs Adidas Stan Smith, Coach Tabby vs Michael Kors Mercer |
| Grocery | Bertolli olive oil vs Carbonell, Twinings Earl Grey vs Ahmad Tea, Lindt 70% vs Godiva 72% |
| Other | Sodastream Terra vs Aarke Carbonator, Dyson Airwrap vs Shark FlexStyle, Eufy RoboVac vs Roborock Q5 |

**Per-query grading sheet (manual, ~3 min/query):**
- Price within 15% of actual Bahrain retail (verify against lulu.com.bh / carrefourbh.com / sharafdg.com manually)
- ≥80% of category-product-type spec fields correctly populated
- Image is the actual product (not lookalike / wrong variant)
- Winner declaration is defensible by domain-expert reviewer
- Wall-time ≤25s

---

## 9. Source-trace observability

**Always-on, not behind `DEBUG_STAGE_TIMINGS`.** Every response includes:

```json
"metadata": {
  "source_trace": {
    "price": {
      "sources_tried": ["serper_shopping", "firecrawl:lulu.com.bh", "curl:carrefour.com.bh", "gpt_training"],
      "sources_returned_value": ["serper_shopping", "curl:carrefour.com.bh"],
      "values": [{"src": "serper_shopping", "amount": 142.12}, {"src": "curl:carrefour.com.bh", "amount": 145.00}],
      "median_chosen": 143.56,
      "cross_validation": "passed",
      "wall_ms": 4200
    },
    "specs": {...}, "reviews": {...}, "image": {...}
  }
}
```

Wired to Sentry tag (per-source firing counts) + `/admin/source-trace` panel. "Did Firecrawl fire?" becomes a query, not a guess.

---

## 10. Instagram / TikTok social-source feasibility test (B-prep)

**Before building, validate utility.** A.4 includes a 1-day spike:

- Manually run 5 queries (1 fragrance, 1 makeup, 1 fashion, 1 electronics gadget, 1 supplement) against:
  - Brand main Instagram account (official @brand handle)
  - 3 related accounts per brand (top-3 GCC influencers / reviewers in category)
  - TikTok equivalent
- Score: did the social signal add unique product info NOT available from Serper + Reddit + YouTube? (Y/N per query)
- Decision: if ≥3/5 add unique value → green-light Apify integration in B.4. If <3/5 → cut Instagram/TikTok from (B) scope.

This is a cheap pre-investment test that prevents building a $0.005/comparison feature for marginal lift.

---

## 11. Team execution contract (binding for both A + B)

All 4-Opus team sessions for this overhaul follow this contract, enforced by dispatcher:

1. **Model: Opus only.** No Sonnet, no Haiku for any team member. Cross-QA reviewers also Opus.
2. **100% completion gate.** Team is NOT disassembled until every assigned task is complete AND cross-QA-verified. Partial-completion + "defer the rest" is rejected.
3. **Peer cross-QA mandatory.** Each member must QA at least one other member's work before disassembly. If any work is subpar OR missed, work is sent back with explicit reason and re-worked. Dispatcher records every QA hand-off in task comments.
4. **Idle-time discipline.** Any member with no active task must EITHER (a) write red-green tests targeting 80% coverage for the lane's new feature OR (b) wait for QA results — no other "useful work" without dispatcher approval.
5. **Delegation explicit.** Dispatcher publishes a task matrix at team kickoff: who owns what file/feature, who QAs whom, what the deliverable proves. No assumed ownership.
6. **Facts over claims.** Agent self-signoff is NOT sufficient. Cross-QA must produce evidence: file diffs read end-to-end, test runs with output, prod curls when applicable. "I verified" without evidence = task sent back.
7. **No scope deferral without dispatcher approval.** Per `memory/feedback_deferral_discipline.md` — agents inventing "future polish phase" to defer JSX-required items is rejected.
8. **Worktree hygiene.** Absolute paths in `git worktree add`. Verify via `git worktree list` before dispatch. Per-lane branches; merge via dispatcher only.
9. **Path-restricted commits.** `git commit -- <paths>` syntax always (per `memory/feedback_git_staging_in_team.md`).
10. **Stop signals respected.** If dispatcher issues a stop/revert/abandon ruling, fetch + inspect actual commits FIRST (per `memory/feedback_dispatcher_fetch_before_ruling.md`); push back BEFORE destructive action if shipped work would be lost.

---

## 12. Phasing

### Sprint (A) — Wiring + Quality (15–17 working days)

| Lane | Owner | Days | Scope |
|---|---|---|---|
| **L1 — Backend v2 adapter** | Opus #1 | 3 | `build_dimensions_v2` from CATEGORY_DIMENSIONS + legacy `scoring.dimension_winners`. Wire `factual_verdict.line1/2`, `confidence_legs`, `confidence_details`. Flatten `overview.products[i].pros_cons`. Add `overview.products[i].variant`. |
| **L2 — Backend parallel races + cross-validation + Bahrain sources** | Opus #2 | 5 | Replace luxury gate with confidence-driven parallel race. Per-category source routing (Bahrain ×3.0 / GCC ×1.5 / Global ×1.0). Source-trace observability. 25 product-type schemas. Per-retailer review-quote fetcher (γ). Per-category review-search terms for the 4 fallback categories. Tier 1.5 trigger on >40% price deviation. Wrap `compare_from_text` in `wait_for(25s)`. Railway flag flip + circuit-breaker state inspect/reset. |
| **L3 — Mobile renders + 88s instrumentation** | Opus #3 | 4 | Wire new v2 fields. Per-row emerald winner highlighting in specs. Variant string on product card. Winner-star in pros/cons. Per-retailer quote blocks. Frontend wall-time instrumentation (TTFB → first-card → all-cards → ready → tappable). |
| **L4 — Living Prompt System scaffolding + 50-query Bahrain validation matrix + Instagram feasibility test** | Opus #4 | 3 | Survey ETL → pain_workflow_priors.json + decision_style_priors.json. Inject top-3 pain workflows + TL;DR-first instruction into verdict prompt. Run 50-query Bahrain validation matrix. Run Instagram/TikTok 5-query feasibility test. Score + decision. |
| **Cross-QA + merge gate** | All | 2 | Each Opus QAs another's work. 50-query validation matrix MUST hit ≥80% pass. All RED items resolved or explicitly deferred with dispatcher approval. |

**Ship sequence:** L1 + L2 + L3 + L4 merge together (single `--no-ff`). One EAS update to preview channel, then production after device walk.

### Bundle (B) — Intelligence Layer (6–8 weeks)

| Phase | Weeks | Scope |
|---|---|---|
| **B.1 — DB + observability schema** | 1 | Audit current schema. New tables: `user_preference_history`, `pain_workflow_events`, `verdict_critiques`, `eval_runs`. New `comparison_feedback` columns: `winner_correct`, `price_correct`, `specs_correct` (3-state per axis). |
| **B.2 — Living Prompt System full** | 1.5 | Few-shot rotation pipeline (weekly cron curates top-decile feedback verdicts → few-shot examples). Anti-pattern injection from eval failures. Self-critique pass implemented + canary-flagged. |
| **B.3 — Reasoning depth experiments** | 1 | Self-critique enabled production-wide if eval lift ≥3%. Try `o3-mini` for verdict in 10% canary cohort; measure quality + cost. Multi-agent split (spec/price/review analyst → editor) prototyped + benched. |
| **B.4 — Social-source layer** | 2 | Reddit OAuth + per-category subreddit search. YouTube Data API. Fragrantica + INCIDecoder + PubMed direct scrapers. Instagram + TikTok via Apify (IF feasibility test in A passed). All wired INTO the parallel races from (A). |
| **B.5 — Bahrain cultural layer** | 1 | Halal cert lookup. Climate-suitability flags. Ramadan-friendly framing. Arabic-content weighting. GCC luxury secondary market sources. |
| **B.6 — 95% accuracy eval pipeline (built throughout)** | continuous | CI runs eval set every PR. Production 5% sampling. Weekly accuracy report on `/admin/accuracy`. Per-category accuracy breakdown. |

Each B-phase merges independently with canary (10% → 50% → 100%) gating.

---

## 13. Open items / TBD

1. **Survey #2 ETL output spec** — exact schema for `pain_workflow_priors.json` + `decision_style_priors.json` derived from Eng + Arabic responses. To be finalized in writing-plans skill output.
2. **Bahrain-specific brand inclusion list** — Claude to draft based on Lulu/Carrefour BH category-leader presence; Ahmed to ratify before B.5.
3. **Halal certification source** — single trusted DB (GAC, JAKIM, HMC, MUI Indonesia) or composite lookup? B.5 decision.
4. **Apify cost ceiling** — $0.005/comparison social-source layer adds 50% to comparison cost. Acceptable for canary; need limit for production rollout.
5. **`o3-mini` API access** — verify availability + rate limits on Ahmed's OpenAI org before B.3 work starts.
6. **Eval gold set authorship** — 200 hand-graded ideal-outcome comparisons. Ahmed authors OR outsourced via Upwork to a domain-expert reviewer? B.6 prerequisite.

---

## 14. Success metrics

**Sprint (A) ship signals:**
- 50-query Bahrain validation ≥80% pass on weighted metric
- Mobile renders all 4 design screens populated (variant, factual_verdict, confidence pills, dimension bars per category, retailer quotes, pros/cons with winner star, specs table with per-row winner highlighting)
- Frontend instrumentation shipped (88s diagnosed by next device walk)
- Zero scary copy / forbidden vocabulary regression
- No backend wall-time regression (typical 25–29s; +5–10s on ~30% of queries triggering escalation accepted)
- Source-trace observable on every response

**Bundle (B) ship signals:**
- 200-query gold eval ≥95% weighted score
- Self-critique pass measurably reduces hedging-language + vagueness vs baseline
- Social-source layer adds ≥1 unique signal per comparison in target categories
- Per-product-type schemas cover ≥90% of organic production traffic
- Pain-workflow-aware verdicts measurably improve `comparison_feedback.useful=true` rate (target +15pp from current baseline)

---

## 15. Implementation plan handoff

This design is complete. Next step: `superpowers:writing-plans` skill converts this design into a sequenced implementation plan with:
- Per-lane task breakdown with file:line targets
- Test specs per feature
- Cross-QA assignments
- Worktree + branch strategy
- EAS update + canary phasing
- Roll-back contingency

Plan file: `docs/plans/2026-06-08-backend-comparison-overhaul-plan.md`.
