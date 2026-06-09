# Bundle B Kickoff Prep — Intelligence Layer

> **Brainstorm in a fresh session.** This doc collects everything Bundle B needs to know — original B.1–B.6 outline + every item deferred from Sprint A + B0 hardening on 2026-06-08/09. Open this doc first when starting Bundle B brainstorm.

**Bundle B owner:** Ahmed.
**Scope (estimate):** 6–8 weeks.
**Pre-requisite:** Sprint A SHIPPED + B0 hardening SHIPPED (main `3f4f8d1` as of 2026-06-09).

---

## Phase B.0 — Architectural FIRST (Sprint A unfulfilled promise — DO BEFORE B.1)

**🔴 Critical — must close before any Phase B social-source feature lands. Discovered by B0-UnfinishedBiz audit 2026-06-09.**

### B.0 — `source_router` cascade wiring (2-3 days)

Sprint A Lane 2 shipped `app/services/source_router.py` with the Bahrain-first ×3.0 / GCC ×1.5 / Global ×1.0 registry promised in design § 4 — **BUT zero production code paths read `SOURCE_REGISTRY`.** `get_sources_for_category()` + `score_source()` are defined but never called. The Tier 1.5 escalation cascade in `structured_comparison_service.py` + `price_service.py` still uses the legacy hard-coded `OFFICIAL_BRAND_DOMAINS` (Apple/Samsung/Sephora/Harrods — no `.bh` domains) + `GCC_LUXURY_RETAILERS` (fashion/luxury only).

**Empirical evidence:** 0% Bahrain retailer hit rate across B0-D's 24-query bias matrix for non-luxury non-electronics queries. Patchi (Bahrain chocolate), Ahmad Tea, Carrier AC, etc. all fall through to Tier 3 GPT-estimate (`metadata.source_trace.price.values[].src == "gpt_training"`).

**Tasks:**
- Wire `get_sources_for_category(category)` into the Tier 1.5 page-scrape escalation
- Add `site:<bahrain_domain>` per-source Serper queries for non-luxury weak-Tier-1
- Cross-cuts `price_service.py` + `structured_comparison_service.py` + `serper_service.py`
- Add per-source hit-rate metric for monitoring
- Every social-source feature in B.4 depends on this layer working

---

## Phase B.1 — Database + observability schema (1 week)

**Already partially scaffolded by L4 idle-time work** — 5 SQL-ready migrations in repo (027–031). Just need to apply + wire.

### Existing scaffold (ship as-is)
- ✅ `migrations/027_comparison_feedback_correctness.sql` — adds `winner_correct`, `price_correct`, `specs_correct` (3-state per-axis)
- ✅ `migrations/028_pain_workflow_events.sql` — per-comparison touch/expand/abandon/screenshot events
- ✅ `migrations/029_user_preference_history.sql` — per-comparison preference touch/expand events
- ✅ `migrations/030_verdict_critiques.sql` — model's self-grade (B.3 reasoning depth)
- ✅ `migrations/031_eval_runs.sql` — CI metrics over time
- ✅ B.1 preflight doc at `docs/plans/2026-06-08-B-phase1-db-schema-audit-preflight.md`

### Pre-apply hardening (from B0-UnfinishedBiz audit, Bucket 4-adjacent)
- 🟡 Drop `comparisons_cache` table (dead since pre-Migration-010, 0 rows, 0 code references)
- 🟡 Add RLS policies to `products` table (currently RLS-disabled, anon-key vector even though current code uses service-role)
- 🟡 Drop duplicate `idx_users_device_fp` (kept canonical `idx_users_device_fingerprint_active`)

### Wiring work (this is the B.1 actual implementation effort)
- Audit current `users.preferences` / `comparison_feedback` / `user_events` / `cohort_priors.json` consumption
- Apply 027 first (smallest blast radius — ALTER TABLE ADD COLUMN)
- Apply 028–031 in parallel batch (no peer deps, fire via Supabase MCP `apply_migration` in 4 sequential calls)
- Wire `pain_workflow_events.log()` call sites into mobile (StreamingProductCard expand/abandon/screenshot)
- Wire `verdict_critiques.write()` from B.3 self-critique pass (depends on B.3 ship)
- Wire `eval_runs.write()` from B.6 CI eval pipeline (depends on B.6)

---

## Phase B.2 — Living Prompt System full (1.5 weeks)

**Already scaffolded by L4 in Sprint A** — `pain_workflow_loader.py` + `build_verdict_prompt(user_cohort=...)` injects top-3 pain workflows + decision-style hint into verdict prompt.

### Already shipped (no work in B.2)
- ✅ Survey ETL: 443 responses → `pain_workflow_priors.json` + `decision_style_priors.json`
- ✅ `build_verdict_prompt` with cohort-context injection
- ✅ Anonymous-safe (verified by B0-D 24-query bias: `applied_shifts: []`)
- ✅ Privacy invariant (no raw demographics in prompt; cohort keys hash-encoded)

### B.2 scope (new work)
- **Few-shot rotation pipeline (weekly cron)** — curate top-decile `comparison_feedback` (useful=true + winner_correct=true) → rotate into `data/few_shot_verdict_examples.jsonl` → inject 3 into verdict prompt per category. ⚠️ Privacy review: ensure no PII bleed from feedback rows.
- **Anti-pattern injection from eval failures** — when B.6 eval set has failures, distill into "what NOT to do" examples; inject as anti-patterns in verdict prompt.
- **Self-critique pass (B.2 prototype, full ship in B.3)** — GPT-4o-mini receives `(verdict + critique instructions)`; scores bias/vagueness/hedging/missing-citation/pain-workflow-alignment; if any < 7/10 → regenerate. Canary flag default OFF.

### Key change from Sprint A design
**NO PAID OPENAI FINE-TUNING.** User confirmed 2026-06-08: smarter brain = prompt engineering + dynamic context + few-shot rotation, NOT $50 fine-tune + 60% per-token cost. B.2 ships entirely on free/cheap mechanisms.

---

## Phase B.3 — Reasoning depth experiments (1-2 weeks)

### Self-critique pass (full ship)
Production-wide if B.6 eval lift ≥3% vs base. Cost: +~$0.001/comparison via gpt-4o-mini. Wall-time +1-2s; needs verification stays inside 30s `STREAM_HARD_CAP_SECONDS` cap (raised from 25→30 in B0-C Item 3).

### Multi-agent split (canary-only)
- `spec-analyst` (gpt-4o-mini specs reasoning)
- `price-analyst` (gpt-4o-mini value framing)
- `review-analyst` (gpt-4o-mini sentiment synthesis)
- `editor` (gpt-4o final assembly + pain-workflow injection)
- Heavier (~2x cost) but more rigorous; canary at 10% cohort to start; promote if quality lift ≥5%

### `o3-mini` for verdict (canary experiment)
- Replace `model_router.get_model(priority="high")` gpt-4o with `o3-mini` for verdict only in 10% cohort
- Measure quality lift vs cost (o3-mini is ~2x cost of gpt-4o-mini, slower)
- Promote if measurable quality improvement + cost-acceptable

### Self-critique writes back to `verdict_critiques` table (B.1)
For observability + ongoing prompt-eng iteration.

---

## Phase B.4 — Social-source layer (2 weeks)

**Depends on B.0 source_router being wired** — every B.4 source plugs into the parallel race architecture from Sprint A § 3, which assumes the registry routes traffic correctly.

### Reddit (Phase 1 of B.4)
- OAuth + per-category subreddit search (free Reddit API)
- Subreddits per `CATEGORY_SPEC_SCHEMAS` category:
  - electronics → r/Android, r/Apple, r/gadgets, r/buildapc
  - supplements → r/Supplements, r/Nootropics, r/Fitness
  - fragrances → r/Fragrance, r/RandomActsOfFragrance
  - makeup → r/MakeupAddiction, r/SkincareAddiction
  - haircare → r/HaircareScience, r/curlyhair
  - fashion → r/malefashionadvice, r/femalefashionadvice
- Add as another source in REVIEWS race (Sprint A § 3)

### YouTube Data API (Phase 2 of B.4)
- Free quota (10,000 units/day) — review-count signal per product
- Add to REVIEWS race

### Instagram + TikTok via Apify (Phase 3 of B.4 — pending feasibility)
- L4 dispatched a 5-query feasibility test (Sprint A L4.4) — Ahmed to execute manually + score relevance ≥3/5 before B.4 builds it
- ~$0.005/comparison if green-lit
- Add to REVIEWS race + new "social_signals" race

### Direct scrapers (Phase 4 of B.4)
- Fragrantica scraper for fragrances (longevity/sillage real-user data)
- INCIDecoder scraper for skincare/makeup ingredient breakdown
- PubMed E-Utilities for supplements clinical references
- All wired INSIDE the parallel races from Sprint A § 3

---

## Phase B.5 — Bahrain cultural layer (1 week)

### Halal certification lookup
- Single DB (GAC, JAKIM, HMC, MUI Indonesia) or composite — final decision TBD
- Lookup at extraction time; flag products with gelatin / animal-derived ingredients
- Categories affected: grocery, supplements, makeup (lipsticks with carmine), some haircare

### Climate-suitability flags
- 45°C summer durability for makeup/skincare formulas (heat-stable vs heat-sensitive)
- Anti-perspirant SPF coverage for fragrances/lotions
- Sweat-proof / heat-proof flags surfaced in dim assessment

### Ramadan-friendly framing (grocery/supplements)
- During Ramadan period (Hijri month 9), boost suhoor/iftar-relevant products
- Dim weights subtly shift for grocery: "shelf-stability" ↑, "quick-prep" ↑

### Arabic-content source weighting
- Saudi/UAE/BH-specific reviews weighted higher than global English content
- Sayidaty, Sabq, Khaleej Times AR, Gulf News AR included as Tier 1.5 sources for relevant categories

### GCC luxury secondary market
- Vestiaire, RealReal, GCC consignment platforms for fashion/luxury authentication
- Cross-validation against official-retail-price for counterfeit detection

---

## Phase B.6 — 95+ accuracy automated eval (continuous, built throughout)

### CI pipeline (built first, runs throughout B.1–B.5)
- Every PR → run eval set against 200-query gold standard
- Fail if `< 95%` pass on any axis: price within 15% / specs correctness / winner-agrees-with-expert / factual claims correctness
- Eval gold-truth at `data/validation_gold_truth.json` (50-query authored in L4.3; **expand to 200 queries** in B.6 prep)

### Production sampling
- 5% of queries scored against secondary source (Bahrain retail check via curl)
- Alert if accuracy drops > 2% from baseline
- Sentry integration for accuracy-regression alerts

### Weekly accuracy dashboard
- `/admin/accuracy` route with per-category accuracy trend over time
- Per-axis breakdown (price/specs/winner/factual)
- Per-cohort breakdown if cohort_personalization shipped

### Eval gold-set authorship
- Sprint A L4 authored 50 queries; B.6 needs +150 to reach 200
- Hand-graded by domain experts OR outsourced via Upwork
- Cover all 9 categories × multiple product types per the matrix in `2026-06-08-A-validation-matrix-50q.md`

---

## Deferred-from-Sprint-A items folded into Bundle B

### Performance follow-ups (from B0-A v2.2 STREAM_HARD_CAP investigation memo)

Source: `docs/plans/2026-06-09-stream-hard-cap-investigation.md`

The Q01/Q10 cap timeouts revealed extraction-layer latency, NOT a v2.2 bug. Three Bundle B perf items:

1. **AC/appliance Tier 1.5 page-scrape selectors** — currently `CATEGORY_SPEC_SCHEMAS["electronics"]` is phone-shaped. AC-specific keys (cooling capacity, energy rating, refrigerant, BTU) would unlock direct extraction from Sharaf DG / Carrefour / Geant / Lulu. Also pairs with B.0 source_router wiring.
2. **Supplements iHerb cascade** — reduce Firecrawl fallback frequency on iHerb miss. Currently iHerb miss → Firecrawl + Scrape.do fan-out adds 5-15s. Tighten the iHerb selectors first.
3. **`tier1_5_hit_rate` per-category metric in `/admin/costs`** — adds observability so future perf regressions surface before user impact.

### Q16 YSL+Lancome edge case (already addressed by B0-E Item 1)

- ✅ B0-E shipped 2026-06-09 — tightened `"opium"` blocklist entry to multi-word phrases. YSL Black Opium now passes L1 prefilter.
- 🟡 Bundle B follow-up: audit ALL single-word entries in `content_blocklist.json` for similar collisions. B0-UnfinishedBiz checked 8 entries; rest of corpus untouched.

### Sentry monitoring

- ✅ **PYTHON-FASTAPI-J** (NoneType.get HIGH actionability) — resolved by L2 None-guard hotfix + v2.1 `_score_specs` None path
- ✅ **PYTHON-FASTAPI-6** (Serper search 400 chronic) — resolved by Serper key swap 2026-06-09
- ✅ **PYTHON-FASTAPI-K** (Serper images 400) — resolved by Serper key swap
- 🟡 **PYTHON-FASTAPI-9** (auth refresh "Already Used") — 1 event 10h old at sprint close, single-occurrence pre-existing, low Seer actionability. **Bundle B: defer-and-monitor.** If recurs >3 times/week, investigate `/auth/refresh` token-rotation race.

### L1.3 v1.1 polish (optional)

- 🟡 Add explicit `winner` field to dim emits (currently FE has fallback via score comparison; backend doesn't authoritatively flag). 20-min improvement; optional.

### 5 pre-existing Jest onboarding fails (Bundle D/E carry-over)

- 🟡 `Screens.bundleD.contract.test.ts`, `OnboardingFlow.analytics.test.tsx`, `authService.b4.test.ts`, `NewOnboardingHost.test.tsx`, `OnboardingFlow.bundleE.test.tsx` — pre-existing Sprint-A, documented in MEMORY.md `feedback_blocking_signal_clarity.md`
- **Bundle B context:** these may interact with B.1 `user_preference_history` wiring (Onboarding writes preferences). Worth fixing as part of B.1 to clear the test foundation before adding new tests.

### `app/legal/{privacy_policy,terms_of_service}.md` redraft (PRE-EXISTING APP STORE BLOCKER)

- 🔴 NOT a Bundle B item per se, but blocking App Store production. Per CLAUDE.md "APP STORE PRODUCTION SHIP-BLOCKERS". 15 legal decisions pending per `docs/plans/2026-05-16-tos-decisions-pending.md`. Multi-week separate workstream.

### Icon ICN-0001 byte-identity (PRE-EXISTING APP STORE BLOCKER)

- 🔴 Same — App Store production blocker, NOT Bundle B. `SmartCompareApp/assets/{icon,splash-icon,adaptive-icon}.png` SHA-256 identical to Expo create-expo-app template. Regenerate as unique render with emerald accent.

---

## Open decisions for Bundle B brainstorm

1. **Sequence:** B.0 first (architectural unblocker) → B.1 (DB + obs) → B.2 (prompts) → B.6 (eval foundation in parallel) → B.4 (social) → B.3 (reasoning depth) → B.5 (Bahrain culture)? Or different?
2. **Self-critique cost ceiling:** acceptable to add ~$0.001-0.002/comparison for self-critique? (Currently $0.0094 avg → ~10-20% increase)
3. **`o3-mini` canary cohort size:** 10% start OK? Smaller (5%) for safety?
4. **Instagram/TikTok feasibility execution:** Ahmed-driven 5-query manual walk before B.4 builds Apify integration. Schedule.
5. **Eval gold-set expansion (50 → 200):** in-house authoring or Upwork? Budget ceiling?
6. **Halal cert source:** single DB or composite? Per-region preference (BH-specific?).
7. **STREAM_HARD_CAP=30 confirmed in CLAUDE.md** — current Railway env shows 30s. Update CLAUDE.md to match if not already.

---

## Ready-to-brainstorm checklist

- ✅ B.1 migrations 027-031 SQL-ready on main
- ✅ B.2 verdict prompt injection live (no fine-tuning)
- ✅ B.0 cascade wiring documented as task #1
- ✅ B.6 eval gold-truth seeded (50 queries by L4.3)
- ✅ Performance follow-ups documented in v2.2 memo
- ✅ Sentry baseline clean (1 unresolved single-event)
- ✅ Sprint A close-out narrative in `SESSION_BUNDLES.md`

**Brainstorm Bundle B opens with:** read this doc + `docs/plans/2026-06-08-backend-comparison-overhaul-design.md` § 13 → trigger `superpowers:brainstorming`.
