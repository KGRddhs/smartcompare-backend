# Design — Faithful Results + Genuine-BH on Free Tier (2026-06-17)

**Status:** DESIGN APPROVED (brainstorm complete). Next: `writing-plans` → dynamic ultracode discovery workflow (enhances the plan) → Opus team executes.
**Origin session:** main `f409f71` (Session 63 shipped: fragrance quality, cohort proof line, results 1:1 redesign, per-source review quotes, CATEGORY_FAIRNESS standard).
**Owner:** dispatcher (Ahmed). Design URL handoff: `https://api.anthropic.com/v1/design/h/L_VQdhHRVwiFnZnAQ5tjGA` (UI Kit — Mobile Results).

---

## 0. Key findings from grounding (why this scope)

1. **The design file `L_VQ…` is the SAME Results design Session 63 implemented against.** New handoff's `ResultsScreen.jsx` is **byte-identical** to the on-disk copy at `.qa-bias-rerun/_handoff/qaren-design-system/project/ui_kits/mobile/ResultsScreen.jsx` (410 lines, zero diff). The only new artifacts are `Logo Studio.html` + 2 logo screenshots (icon ship-blocker, OUT of scope) + an updated chat log. ⇒ The work is **"where does live diverge from the design + where does data fail to populate,"** not a fresh implementation.
2. **The design is a single ELECTRONICS template.** Its Specs accordion is hardcoded phone specs (Display/Camera/Battery/RAM/…); dimension bars are Camera/Battery/Price. ⇒ **"Structure based on category" is an EXTENSION** — fragrance→scent+notes, supplements→count/dosage, etc. Backend already has `CATEGORY_DIMENSIONS` + `CATEGORY_SPEC_SCHEMAS` (9 cats); the question is faithful render + completeness per category.
3. **"Overwhelming breakdown" = live renders MORE than the design.** Live `ResultsContent.tsx` adds a whole `HeroRings` score-rings card on top of `DimensionBars` + `ConfidencePills` + a spec-heavy accordion, each in its own bordered card. The design has **no rings**. Pruning toward the design is the fix.
4. **The "convince / runner-up" gap is partly a REAL FE BUG.** The verdict prompt DOES emit `key_tradeoff` (losing product's strongest advantage, `extraction_service.py:605/635/1562`), but `ResultsContent.tsx:297-316` renders `FactualVerdict` and **skips the runner-up caption block whenever `scoring_v2.factual_verdict.line1` exists** (≈ always). So the "why the other could be better" line is generated but never shown.
5. **Personalization "not clicking":** chip shows `applied_shifts` but the verdict prose isn't required to reference the user's actual priorities in a felt way; cohort line only just wired (Session 63).
6. **Reviews legal nuance:** today `clean_review_citations` turns `[N]` → source domain and quotes are VERBATIM. Safest posture for "praise, no citations" is **paraphrased praise (synthesized, non-verbatim)**, NOT de-attributing verbatim UGC.

---

## 1. Locked decisions (brainstorm Q&A)

| # | Decision | Choice |
|---|---|---|
| D1 | Execution shape | **A — Audit-then-fix** (dynamic discovery workflow → plan → Opus team) |
| D2 | Per-category scope | **All 9 categories faithful** |
| D3 | Scrape provider test | **Measure-only this cycle** (no live-pipeline rewire mid-sprint beyond the agreed tiering) |
| D4 | Reviews legal posture | **Paraphrased praise, no citations** (safest) |
| D5 | Eval/harness scope | **All of it** — B2 baseline + regression gate + A4 (build now, measure post-warmer) |
| D6 | Sourcing model | **Firecrawl/Scrape.do = heavy BH render; Serper = light discovery + lighter lookups** |
| D7 | Operating constraint | **Free subscriptions to start ⇒ cache-maximal is mandatory** |
| D8 | Team | **4-Opus** (no Sonnet/Haiku), domain-delegated, cross-QA before disassembly, send-back on subpar, idle→red-green to 80%, work delegated |

---

## 2. North star (what "done" looks like)

Every comparison renders the **Qaren design-system Results layout** with **category-appropriate structure**, all information populated (no blank specs, no raw `[N]`, genuine-or-pending prices, fairness-correct sizes), a verdict that **convinces + makes the runner-up's case + lands personalization**, **paraphrased-praise** reviews (no citations, legally safe), and a **lean** breakdown (pruned toward the design). Genuine-BH prices are served mostly from cache ($0) on free scraper subscriptions.

---

## 3. Workstream 1 — Sourcing + Caching architecture (free-tier survival)

### 3a. Tiering
- **Serper (light):** discover candidate BH URLs (~1 credit) + lighter lookups. Feeds the scrapers; does NOT do heavy genuine extraction.
- **Firecrawl / Scrape.do (heavy):** render genuine BH retailer PDPs for real prices + useful info. Head-to-head picks the primary.
- **Warmer:** fixed URL catalog → **scraper-first, zero Serper** (the key unlock — decouples genuine-share from the finite Serper budget).

### 3b. Cache-maximal (complete; free-tier is tiny — Firecrawl free = 500 cr = ~100 stealth scrapes EVER)
1. Long-TTL genuine-BH prices (24h→7–30d); estimated/converted short TTL.
2. Both layers (L1 Redis + L2 DB `product_data_service`) TTLs reviewed; genuine persisted to L2 append-history.
3. Warm-once-serve-long (re-warm only on TTL expiry; `warmer:cursor`).
4. Cache-first before ANY render (gate firecrawl/scrape.do behind L1→L2 miss).
5. Negative-cache structural dead-ends (luxury fragrance/haircare/gadgets) — never re-burn a scrape.
6. Fairness-correct cache keys (normalized product + size/variant).
7. A4 cache-reading eval variant (measures warmed share; eval today is `nocache`/cold).
8. Hit-rate observability (hit/miss + genuine-from-cache; head-to-head measures cache impact).
9. Free-tier preservation is the PURPOSE of the heavy caching.
10. Verification discipline: stale-cache-masks-deploy → verify with fresh pairs / `nocache`.

### 3c. Free-tier-first
Head-to-head measures **accuracy AND credits-per-genuine-price AND cache-hit impact**. Target: most user hits are $0 cache hits; scrapers fire rarely + durably. Paid tiers ($83 Firecrawl Standard OR $99 Scrape.do Pro + $50 Serper Starter) are a LATER decision once free runway proves the model.

**Touch points:** `price_service.py` (tier cascade, `CATEGORY_FAIRNESS`), `product_data_service.py` (L2 TTLs), `cache_service.py` (L1 TTLs/helpers), `api_budget_service.py` (`PROVIDER_CONFIGS`, circuit breakers), `firecrawl_service.py`/`scrapedo_service.py`, `scripts/cron_warm_price_cache.py`, `data/warmer_catalog.json` (16 pairs).

---

## 4. Workstream 2 — Results faithfulness (FE + backend content)

- **FE prune → design:** remove `HeroRings` redundancy + lighten section chrome (`ResultsContent.tsx`, `HeroRings.tsx`, `DimensionBars.tsx`); match the design's lean single-pass.
- **Category-aware render (all 9):** specs table, dimension bars, and a category "profile" block (fragrance scent family + notes + longevity/sillage; supplements count/dosage; etc.) driven by backend category schemas. No electronics-flavored labels on non-electronics.
- **Un-suppress the runner-up caption** (FE bug #4) — show the "why the other could be better" line even when `factual_verdict.line1` is present.
- **Price-pending UI** preserved; **paraphrased-praise** review lines; **EN/AR i18n** for all new copy; `.copy-policy.json` compliance.
- **Specs-population fixes** per category (no blank 2nd-product specs — the keystone fixed fragrance; audit the rest).

## 5. Workstream 3 — Verdict / personalization
- System prompt (`extraction_service.py` `COMPARISON_SYSTEM` ~596 + verdict builder ~1539): **convince** + **make the runner-up's case** (enrich `key_tradeoff` from one thin sentence to a genuine "who should pick the other") + **weave the user's stated priorities** explicitly.
- Verify personalization end-to-end: explicit priorities ±30%, `applied_shifts` chip, cohort proof line (`cohort_summary`).

## 6. Workstream 4 — Reviews (paraphrased praise)
- Replace verbatim-quote + citation surfacing with **synthesized positive summary** per product from real review sentiment — no verbatim copying, no `[N]`/domain markers. Ratings only when a real one exists (never fabricated). `review_service.py` (`clean_review_citations` ~132, `build_retailer_quotes_from_reviews` ~243).

## 7. Workstream 5 — Fairness (audit-driven)
- `CATEGORY_FAIRNESS` (price_service) audited across all 9 incl. edge cases (missing size, tolerance bands, one-fixed-size, honor-each). Wrong fairness decision = wrong/pended price = the "prices wrong" symptom. Fix what the audit surfaces. Fragrance-size capture (P2): improve when size only in a variant-widget/image (currently falls to flagship-100ml).

## 8. Workstream 6 — Eval / harness
- **B2:** proper smoke20 `--persist` baseline (documented `4aee8e88` is full-200, mismatches the smoke20 gate). Insert `eval_runs` row via Supabase MCP (project `qulajmyxdbdkchvecmvc`) if the box can't DNS-reach Supabase.
- **Regression gate** on the team's changes (`--concurrency 1`, sandbox-disabled, no-prod-write in the harness).
- **A4:** cache-reading eval variant — build now; measurement blocked until warmer activation (Ahmed).

---

## 9. Orchestration (two-stage)

### Stage 1 — Dynamic ultracode discovery workflow (read-only, adversarially verified, loops-until-dry)
1. **Firecrawl-vs-Scrape.do head-to-head FIRST** (known BH PDP URLs): accuracy + credits-per-genuine-price + cache impact → decides warmer engine + tiering.
2. Per-category **data + render + fairness** audit ×9 (cached-first; targeted `nocache` only to measure genuine-share).
3. FE-vs-design divergence catalog (against the handoff file, not screenshots).
4. Verdict / personalization / reviews review.
5. Completeness critic (what modality/claim/category wasn't covered).
- **Output:** verified findings doc that **enhances** the plan.

### Stage 2 — Plan synthesis
- Dispatcher folds findings into the executable plan (`writing-plans`).

### Stage 3 — Opus team (TeamCreate, `bypassPermissions`)
- Domain-delegated: **Backend / Frontend / Test / Integration-QA.** Opus-only.
- **Rules:** features 100% complete; **every member QAs another's work before disassembly**; subpar/missed → **sent back**; idle member → **red-green tests to 80%** OR await QA; work **delegated**.
- **Operational constraints to resolve in the plan:** FE worktree `node_modules` (junction main tree's, or FE works in main tree); path-restricted commits (`git commit -m … -- <paths>`); git-index races; inbox-ACK discipline; escalate idle >30min / 3 silent nudges.

---

## 10. Verification + deploy

- **Claude-side:** backend `nocache` prod curls per category + FE-code-vs-design (handoff file) + eval regression gate.
- **Ahmed-side:** on-device walk (tight checklist produced for him); warmer cron + `ENABLE_PRICE_CACHE_WARMER`; EAS two-relaunch.
- **Deploy:** backend merge `--no-ff` → Railway ~90s → prod-smoke (`?nocache=true`) → `eas update --branch preview` → on-device verify. Railway MCP/CLI may be `invalid_grant` → verify via prod API probe.

## 11. Boundaries + invariants
- **OUT:** icon/Logo Studio, legal redraft.
- **Invariants:** EN/AR i18n, `.copy-policy.json` (no "Winner"/"Failed"/"couldn't"/"try again"; AR تعذر/فشل), no-regression on existing tests, two-lever deploy, ratings never AI-generated.

## 12. Cost model (reference)
- Cold comparison (measured, prod dumps): **~$0.015–0.017** (≈$0.011 OpenAI + ≈$0.006 Serper). Cached: **~$0.00**. Cold+luxury render: ~$0.02.
- Per-unit: gpt-4o-mini $0.15/$0.60 per 1M; Serper $0.001/cr (free 2,500); Firecrawl 1cr/page, 5cr/stealth, Standard $83/100k (free 500); Scrape.do JS-render Pro $99/1.25M (free 1,000).
- Warmer (16 pairs/32 products) @ 2×/day ≈ $8–13/mo marginal, but free tiers ⇒ caching mandatory.
- Sustained paid floor (later): ~$145–165/mo (Serper $50 + one scraper $83–99 + OpenAI ~$12); amortizes to ~$0.15/compare @1k/mo → ~$0.015 @10k/mo.
- This increment one-time burn: ~450 Serper credits (of free ~2,490) + ~$1.50 OpenAI.

## 13. Sequencing
Head-to-head **first** (decides architecture) → category/fairness/FE audit (parallel) → finalize plan → Opus team build + cross-QA → eval gate → deploy → Ahmed on-device walk.

## 14. Open items for the plan
- Exact team topology (worktree vs main-tree FE) + node_modules handling.
- Concrete TTL values (genuine 7d vs 30d) + negative-cache TTL.
- Head-to-head URL set (which BH PDPs) + success metric thresholds.
- Whether the warmer goes fully Serper-free now or keeps a Serper discovery fallback.
- Category "profile" block component design per category (the new FE piece).
