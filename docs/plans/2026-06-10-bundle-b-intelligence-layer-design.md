# Bundle B — Intelligence Layer: Design

**Status:** APPROVED (Ahmed, 2026-06-10, section-by-section via brainstorming skill)
**Owner:** Ahmed. **Duration:** 6–8 weeks (3 bounded team sessions + buffer).
**Baseline:** main `88dfa85`, Sprint A + B0 shipped 2026-06-09, Sentry 1 unresolved (PYTHON-FASTAPI-9, defer-and-monitor), `STREAM_HARD_CAP_SECONDS=30`.
**Inputs:** `docs/plans/2026-06-09-bundle-b-kickoff-prep.md` · `docs/plans/2026-06-08-backend-comparison-overhaul-design.md` § 13 · `docs/SESSION_BUNDLES.md` Sprint A entry.
**Next step:** `superpowers:writing-plans` → `docs/plans/2026-06-10-bundle-b-intelligence-layer-plan.md`.

---

## 1. Decision log (2026-06-10 brainstorm)

| # | Decision | Outcome |
|---|----------|---------|
| 1 | Sequencing | **B.0 → (B.1 ∥ B.6) → B.2 → (B.3 ∥ B.4)**. Eval gate live before any prompt/reasoning change ships; migration 027 applied early so feedback data accumulates for B.2. |
| 2 | Cost envelope | **≤$0.015 blended/comparison at bundle exit** (+60% over $0.0094 baseline), with per-feature gates: self-critique ≤$0.002, Apify ≤$0.005 category-scoped, o3-mini cost-neutral vs the gpt-4o verdict it replaces. Ceiling is architectural discipline, not budget panic — absolute spend at current volume is trivial. |
| 3 | B.3 experiment design | **Shadow eval, NO percentage canary.** At <10 testers a 10% canary buckets ~1 user (zero signal — per CLAUDE.md canary doctrine). o3-mini + multi-agent arms run offline vs gold set + replayed prod queries, graded by B.6 pipeline. Promote to 100% behind flag on lift ≥ threshold. |
| 4 | IG/TikTok feasibility walk | **Week 1, Ahmed-driven** (5 queries from Sprint A L4.4 plan, score ≥3/5). Gates B.4 Phase 3 (Apify) as a CONDITIONAL plan task — resolves ~3 weeks before the B.4 lane starts. RED verdict → Apify cut cleanly, S3 lane re-scopes to direct scrapers. |
| 5 | Gold-set expansion 50→200 | **Agent-drafted, Ahmed-ratified.** Agents draft +150 fact-anchored queries (live-researched Bahrain prices, official spec sheets); Ahmed ratifies ALL winner labels (~2.5h — the one subjective axis). $0; Upwork held in reserve as independent audit if eval results ever look suspicious. Circularity risk accepted because 3 of 4 axes are externally fact-anchored. |
| 6 | **Halal certification: CUT (permanent)** | Ahmed: "overkill and could sabotage us." Risk asymmetry: nice-to-have signal vs religious mis-assertion in a Muslim-majority market. Even conservative ingredient-flagging reads as casting doubt (waswasa) on already-certified, import-regulated products, and positions a tech startup as a religious authority. **Do not re-propose.** |
| 7 | B.5 dissolved as a phase | Arabic-content source weighting → B.0 (it IS registry weighting). Climate-suitability flags → B.2 (extraction/prompt enrichment; seasonally live NOW). Luxury secondary market → B.4 direct scrapers. **Ramadan framing DEFERRED** (next Ramadan ≈ Feb 2027; unvalidatable this bundle; YAGNI). |
| 8 | Execution shape | **3 bounded sessions, fresh team each, flexed lane width** (S1: 5–6, S2: 4, S3: 4–5) + fresh one-shot QA agents mid-session. Context rot is fought by REPLACING agents at session boundaries, not by adding agents (more agents = more rotted contexts + more stall surface). Sprint A discipline carries over: Opus-only, mandatory ring cross-QA, path-restricted commits, no-stash, push-per-commit. |

§ 13 open items all closed: #1 done in Sprint A · #2 Bahrain brand list → B.0 (Ahmed ratifies) · #3 halal cut · #4 Apify ceiling set · #5 o3-mini access = Ahmed week-1 check · #6 gold-set decision made.

**Standing constraint:** NO paid OpenAI fine-tuning anywhere in Bundle B (Ahmed, 2026-06-08).

---

## 2. Scope summary

Bundle B converts the Sprint A engine (correct, fast, observable) into an intelligent one: sources route Bahrain-first, every change is measured by a CI eval gate, prompts learn from real feedback, and reasoning quality is experimentally verified before it costs money.

- **Session 1 "Foundation" (weeks 1–2):** B.0 source_router wiring + perf follow-ups ∥ B.1 DB/observability ∥ B.6 eval pipeline ∥ gold-set expansion — 5–6 lanes
- **Session 2 "Intelligence" (weeks 3–4):** B.2 living prompts + climate flags ∥ B.3 self-critique + shadow reasoning experiments — 4 lanes
- **Session 3 "Sources" (weeks 5–6):** B.4 Reddit / YouTube / conditional Apify / direct scrapers + B.6 close-out — 4–5 lanes
- **Weeks 7–8:** buffer

Each session ends merged-to-main, prod-smoked, device-walked, with the 24-query bias matrix re-run.

---

## 3. Session 1 — "Foundation" (B.0 ∥ B.1 ∥ B.6)

### Lane F1 — B.0 source_router cascade wiring (headline)
- Wire `get_sources_for_category()` + `score_source()` into Tier 1.5 escalation in `structured_comparison_service.py` + `price_service.py` + `serper_service.py`. (Verified 2026-06-10: zero callers outside `source_router.py` itself.)
- **Strategy: registry-first, legacy-fallback.** Registry drives source selection; hard-coded `OFFICIAL_BRAND_DOMAINS`/`GCC_LUXURY_RETAILERS` remain as fallback. `metadata.source_trace` records which path fired — watch the registry win before deleting legacy.
- `site:<bahrain_domain>` per-source Serper queries for non-luxury weak-Tier-1, gated by `has_budget("serper")`.
- Expand `SOURCE_REGISTRY`: Bahrain brand/retailer inclusion list drafted from Lulu/Carrefour BH category leaders (**Ahmed ratifies**) + Arabic-content sources (Sayidaty, Khaleej Times AR, Gulf News AR) for review-content categories *(dissolved from B.5)*.
- `tier1_5_hit_rate` per-category + per-source hit-rate metrics in `/admin/costs`.

### Lane F2 — Extraction/perf follow-ups (same code area)
- AC/appliance spec keys (cooling capacity, BTU, energy rating, refrigerant) — unlocks Sharaf DG / Carrefour / Geant / Lulu direct extraction.
- Supplements iHerb cascade tightening — reduce the 5–15s Firecrawl/Scrape.do fan-out on iHerb miss.
- Full single-word `content_blocklist.json` collision audit (beyond the 8 entries B0-UnfinishedBiz checked; Q16 "opium" class).
- **Dim-winners population gap fix** (L1.3 v1.1): `scoring_v2.dimensions[i].winner` None on prod + missing `ecosystem`/`futureproof` electronics dims; add explicit authoritative `winner` emit. Root-cause hunt starts at `build_dimensions_v2` winner derivation vs `MISSING_SCORE=50` short-circuit.
- `tests/test_pain_workflow_loader_edges.py` lru_cache isolation fix (8 sites, autouse `reset_cache()` fixture) — if not already closed by B0-C.

### Lane F3 — B.1 DB + wiring
- Pre-apply hardening: drop `comparisons_cache` (dead, 0 rows), add RLS to `products`, drop duplicate `idx_users_device_fp`.
- Apply 027 FIRST (smallest blast radius; starts `winner_correct` feedback accumulating for B.2), then 028–031 via Supabase MCP `apply_migration`, schema-verified after each (SQL-Editor-transaction gotcha applies to fallback path only).
- Wire `user_preference_history` writes (onboarding preference touches).
- Wire mobile `pain_workflow_events` trackEvent call sites — StreamingProductCard expand/abandon/screenshot. **The bundle's one FE touch; EAS update fires at S1 close** (two-lever model).
- Fix 5 pre-existing Jest onboarding failures (Screens.bundleD.contract / OnboardingFlow.analytics / authService.b4 / NewOnboardingHost / OnboardingFlow.bundleE) — they sit where preference-write tests will live.

### Lane F4 — B.6 eval pipeline
- Eval runner: executes gold-set queries vs `TARGET_BASE_URL` (prod or local), grades 4 axes — price-within-15% / specs correctness / winner-agrees-with-expert / factual claims.
- **Two-mode gate semantics:** during bundle = REGRESSION gate (>2% drop on any axis vs recorded S1 baseline fails); bundle exit = ABSOLUTE ≥95% weighted. (System is below 95% today — that is why Bundle B exists; an absolute gate from day 1 would just be permanently red.)
- Cadence: per-PR 20-query smoke subset (~$0.20, ~10 min); full 200 nightly + pre-merge.
- Writes `eval_runs` (031). Tracks p95 stream-completion latency vs the 30s cap (wall-budget watch).

### Lane F5 — Gold-set expansion (50→200)
- Agents draft +150 queries per the `2026-06-08-A-validation-matrix-50q.md` pattern: 9 categories × product types, fact-anchored truth (live Bahrain retail prices, official spec sheets), per-query provenance.
- Output: expanded `data/validation_gold_truth.json` (schema-compatible with existing 50).
- Ahmed ratifies all 150 winner labels (~2.5h, async during S1).

### Ahmed's S1 parallel tasks (~4h total)
1. IG/TikTok 5-query feasibility walk (L4.4 plan) → gates B.4 Phase 3.
2. Ratify 150 gold-set winner labels (~2.5h).
3. Verify o3-mini API access on OpenAI org (1 min).
4. Ratify Bahrain brand inclusion list (F1).

### S1 exit gate
Migrations applied + RLS verified · eval baseline recorded on full 200 · bias-matrix re-run shows Bahrain sources consulted on non-luxury queries · `tier1_5_hit_rate` live · pytest/tsc green · merged + **immediate post-merge prod smoke** (the `ec2751b` lesson) · device walk · EAS update for the FE touch.

---

## 4. Session 2 — "Intelligence" (B.2 ∥ B.3)

### Lane I1 — Few-shot rotation pipeline
- Weekly cron (pattern: `cron_reengagement.py`) curates top-decile `comparison_feedback` (useful=true + winner_correct=true) → `data/few_shot_verdict_examples.jsonl` → inject 3 per category into verdict prompt.
- **Cold-start design:** at <10 testers top-decile feedback is sparse — seed initial exemplars from the gold set's highest-scoring eval outputs; rotate to real feedback as volume grows. Without this the cron ships dead.
- Privacy: exemplars carry product names + verdict text ONLY. Zero user references/PII from feedback rows.

### Lane I2 — Anti-pattern injection + climate flags
- Distill B.6 eval FAILURES into "what NOT to do" anti-pattern exemplars in the verdict prompt (failure-mode classes, not verbatim outputs).
- Climate-suitability flags *(dissolved from B.5)*: heat-stability extraction keys for makeup/skincare/fragrances (45°C GCC summer — seasonally live at ship time) + verdict-prompt awareness. **Scope tight: extraction enrichment + prompt context only; NO new scoring dimensions** (deterministic scoring untouched).

### Lane I3 — Self-critique (B.3 full ship)
- gpt-4o-mini critique pass scores verdict on bias / vagueness / hedging / missing-citation / pain-workflow-alignment (0–10); any axis <7 → **ONE** regeneration (hard cap — bounds cost + latency).
- Writes `verdict_critiques` (030). Flag `ENABLE_SELF_CRITIQUE` default OFF in code.
- Gates: cost ≤$0.002/comparison; wall +1–2s verified inside 30s cap via p95; promotion requires shadow-eval lift ≥3%.
- Failure mode: critique error → serve original verdict; never blocks the response.

### Lane I4 — Reasoning experiments (shadow only, zero user exposure)
- **o3-mini verdict arm:** vs gpt-4o baseline, offline on gold set + replayed prod queries, graded by B.6 pipeline. Promote only at quality lift AND cost-neutral-or-better.
- **Multi-agent split arm:** spec-analyst / price-analyst / review-analyst (gpt-4o-mini) + editor (gpt-4o) in the same harness. Promote only at ≥5% lift.
- **Envelope interaction (explicit rule):** multi-agent (+~$0.005) and self-critique (+$0.002) both promoting would breach $0.015 → at most ONE promotes, OR the multi-agent editor absorbs the critique role inline. Eval data decides.

### S2 exit gate
Eval re-run vs S1 baseline: zero regression + documented lifts · self-critique promotion decision made on evidence · few-shot injection live (gold-seeded) · climate flags rendering on device · merged + smoked.

**Ahmed's S2 parallel tasks (~10 min):** create Reddit OAuth app + YouTube Data API key so S3 starts unblocked.

---

## 5. Session 3 — "Sources" (B.4 + B.6 close-out)

### Lane S1 — Reddit (B.4 Phase 1)
- OAuth (credentials from Ahmed's S2 prep), per-category subreddit search per the kickoff-prep subreddit map, free API (100 QPM ample).
- Joins REVIEWS race: per-race `wait_for` cap, None on miss, never blocks. 14d review cache.

### Lane S2 — YouTube (B.4 Phase 2)
- Data API key (Ahmed's S2 prep). Review-count signal + top review-video titles into REVIEWS race.
- Quota: search = 100 units of 10k/day → 100 searches/day; fine at current volume with 14d cache.

### Lane S3 — Apify IG/TT (B.4 Phase 3 — CONDITIONAL on week-1 walk ≥3/5)
- Category-scoped: fragrances / makeup / skincare / fashion ONLY (never electronics/grocery/supplements).
- New `apify` counters + circuit breaker in `api_budget_service` (Firecrawl pattern). ≤$0.005/comparison; 7d+ caching.
- Walk RED → this lane re-scopes to deepening Lane S4 scrapers.

### Lane S4 — Direct scrapers (B.4 Phase 4)
- Fragrantica (fragrance longevity/sillage), INCIDecoder (skincare/makeup ingredients), PubMed E-utilities (supplements clinical refs), luxury secondary market cross-check *(dissolved from B.5)* — Vestiaire/RealReal price sanity vs official retail for counterfeit detection.
- Each: curl_cffi-first (iHerb pattern), JSON-LD/embedded-state parse, graceful None, inside parallel races.

### Lane S5 — B.6 close-out
- `/admin/accuracy` dashboard (Chart.js, existing `_AdminAuthenticatedStaticFiles` pattern + its CSP carve-out): per-category + per-axis accuracy trend.
- 5% production sampling vs secondary source; Sentry accuracy-regression alerts (>2% drop from baseline).
- **Bundle-exit eval: absolute ≥95% gate binding.** If short → per-axis gap analysis becomes the post-bundle backlog, documented not hidden.

### Flags
`ENABLE_REDDIT_SOURCE` / `ENABLE_YOUTUBE_SOURCE` / `ENABLE_APIFY_SOCIAL` — default OFF in code, flipped in Railway per-lane when QA is green. Independent kill switches.

### S3 exit gate
≥1 unique social signal per comparison in target categories with flags on · bundle-exit eval ≥95% or documented gap analysis · trailing-window blended cost ≤$0.015 from `/admin/costs` · device walk · SESSION_BUNDLES.md close-out.

---

## 6. Cross-cutting architecture

**Cost.** `api_budget_service` grows per-source counters + breakers (Apify paid; Reddit/YouTube free-but-quota-tracked). Every source reports into `self.total_cost`; `/admin/costs` shows per-feature deltas. **Promotion arithmetic rule:** a feature promotes only while projected blended ≤$0.015 — this is what enforces the multi-agent/self-critique either-or.

**Eval.** Per-PR 20-query smoke (~$0.20) · nightly + pre-merge full 200 (~$2) · during-bundle regression gate (>2% drop fails) · exit absolute ≥95%. Eval failures feed I2 anti-patterns.

**Error handling (all existing patterns).** New sources: race participants, `wait_for`-capped, None on failure, never critical-path — verdict always renders without them. Self-critique: failure serves original verdict. Shadow harness: fully offline. Budget breakers: fail-open on Redis down. New async writes (`verdict_critiques`, `eval_runs`, `pain_workflow_events`): via `_fire_and_forget(coro, label)` — never bare `create_task`. Sentry: per-source scoped tags.

**Privacy.** Few-shot exemplars: product names + verdict text only. Event writes keep cohort hash-key invariant. Reddit/YouTube content is public API data; commercial-use ToS review noted for the separate legal workstream (not a Bundle B blocker for internal testing).

---

## 7. Testing + risks

**Testing.** TDD per superpowers discipline; tests ship with impl per lane. 24-query bias matrix (`.qa-bias-rerun/` canonical fixture) re-runs at EVERY session close. Security regression suite (~98 tests) untouched. Mobile touch uses sync-render/`useFocusEffect` Jest pattern. Live-cost tests marked `live_unit`.

**Risks.**
1. B.0 touches the hottest path (price escalation) → registry-first-legacy-fallback + source_trace + bias-matrix pre-merge + immediate post-merge prod smoke.
2. Credential prereqs stall S3 → Ahmed creates Reddit + YouTube apps during S2 week (~10 min).
3. Wall-time creep → all additions inside race caps; p95 vs 30s is a standing B.6 metric; self-critique +1–2s verified pre-promotion.
4. Few-shot cold start → gold-seeded exemplars (designed in).
5. Team stalls → 30-min/3-nudge escalation; fresh one-shot QA agents pattern.
6. Eval cost creep → tiered cadence caps at ~$2/day nightly.
7. o3-mini access unverified → Ahmed week-1 check before I4 builds.

---

## 8. Bundle-exit success metrics

- 200-query gold eval **≥95% weighted** (price-within-15% / specs / winner / factual)
- Bahrain/GCC source consulted on **100%** of non-luxury escalations; **≥40%** of previously-`gpt_training`-priced gold queries upgrade to scraped/structured source (calibratable in plan — many products genuinely lack Bahrain online retail)
- Self-critique promoted only on ≥3% eval lift, with measurable hedging/vagueness reduction
- ≥1 unique social signal per comparison in target categories
- Blended cost **≤$0.015** verified over trailing window
- Sentry: zero new unresolved patterns; PYTHON-FASTAPI-9 defer-and-monitor
- p95 stream completion inside the 30s cap

---

## 9. Out of scope / standing reminders

- **App Store production blockers** (icon ICN-0001 byte-identity; legal-doc Qaren-jurisdiction redraft, 15 pending decisions) — NOT Bundle B; separate workstreams. TestFlight internal unaffected.
- Bundle F backlog (frontend-heavy: wrong-product extraction, image orientation, SmartPickCard focus refresh) — separate brainstorm.
- Halal certification — CUT, do not re-propose (decision log #6).
- Ramadan framing — deferred to a pre-Ramadan-2027 bundle.
