# Bundle B — Intelligence Layer Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Session 1 is fully specified below; S2/S3 are structured outlines refined at session boundaries (their detail depends on S1 outputs: eval baseline, IG/TT walk verdict, dim-winners root cause).

**Goal:** Wire the Bahrain-first source registry into production, stand up the DB/observability schema and the CI eval gate, then layer prompt intelligence, verified reasoning depth, and social sources on top — all inside a ≤$0.015/comparison envelope.

**Architecture:** 3 bounded team sessions (fresh 4–6 Opus lanes each). S1 "Foundation" runs 5 parallel lanes (B.0 registry wiring ∥ extraction/perf ∥ B.1 DB ∥ B.6 eval ∥ gold-set 50→200). Registry-first-legacy-fallback on the hottest path with `source_trace` observability. Two-mode eval gate: regression (>2% drop fails) during the bundle, absolute ≥95% at exit.

**Tech Stack:** FastAPI + Python 3.12, Supabase (MCP migrations), Upstash Redis, Serper, gpt-4o/-mini, o3-mini (shadow only), curl_cffi, pytest + Jest, EAS (one FE touch).

**Design:** `docs/plans/2026-06-10-bundle-b-intelligence-layer-design.md` (8-decision log — halal CUT, B.5 dissolved, shadow-eval promotion, $0.015 envelope).

---

## Team discipline (all sessions — Sprint A contract carries over)

- Opus-only teams, `mode: "bypassPermissions"`, worktrees via **ABSOLUTE paths** (`git worktree add C:/Users/SynAckITPC/Documents/ai/smartcompare-<lane> -b feature/<lane> main` → verify `git worktree list`).
- Path-restricted commits: `git commit -m "msg" -- <paths>`. **No-stash policy. Push-per-commit.**
- Mandatory ring cross-QA before merge: F1→F2→F3→F4→F5→F1.
- TDD per task: failing test → run (confirm fail) → minimal impl → run (confirm pass) → commit. Free-tier tests (`-m "not (live_unit or live_db or integration)"`) must stay green; live tests marked.
- Stall rule: 30 min silent OR 3 silent nudges → dispatcher takeover / fresh one-shot replacement.
- Merge order at S1 close: F2 → F3 → F4 → F5 → **F1 last** (hottest path), then bias-matrix re-run + immediate prod curl smoke (the `ec2751b` lesson).

## Ahmed's parallel checklist (S1 week, ~4h)

1. IG/TikTok 5-query feasibility walk (Sprint A L4.4 plan) → verdict ≥3/5 gates S3 Lane Apify.
2. Ratify 150 gold-set winner labels (~2.5h) — F5.4 checkpoint.
3. Verify o3-mini API access on OpenAI org (1 min) — unblocks S2 Lane I4.
4. Ratify Bahrain brand/retailer registry additions — F1.5 checkpoint.
5. (S2 week) Create Reddit OAuth app + YouTube Data API key (~10 min) — unblocks S3.

---

# SESSION 1 — "Foundation" (5 lanes)

## Lane F1 — B.0 source_router cascade wiring

**Branch:** `feature/B0-source-router` · **Verified premise:** `get_sources_for_category()` / `score_source()` (`app/services/source_router.py:80,97`) have **zero callers** outside the module.

### Task F1.1: `build_site_discovery_query()` helper

**Files:** Modify `app/services/source_router.py` · Test `tests/test_source_router_discovery.py` (create)

**Step 1 — failing test:**
```python
from app.services.source_router import build_site_discovery_query

def test_site_query_electronics_bahrain_tier():
    q = build_site_discovery_query("Carrier 1.5 ton AC", "electronics", tier="bahrain", limit=4)
    # Bahrain electronics sources, registry order, OR-joined site: operators
    assert q.startswith("Carrier 1.5 ton AC ")
    assert "site:lulu.com.bh" in q and "site:sharafdg.com.bh" in q
    assert "site:noon.com" not in q  # gcc tier excluded
    assert q.count("site:") <= 4

def test_site_query_empty_for_unknown_category_tier():
    assert build_site_discovery_query("x", "other", tier="bahrain", limit=4) != ""  # () categories match all
```
**Step 2:** `python -m pytest tests/test_source_router_discovery.py -v` → FAIL (ImportError).
**Step 3 — minimal impl** (append to `source_router.py`):
```python
def build_site_discovery_query(product_query: str, category: str, tier: str = "bahrain", limit: int = 4) -> str:
    """Serper query targeting registry sources of one tier for a category.

    Returns '<query> site:a OR site:b ...' — empty string when the tier has
    no sources for the category (caller skips the discovery call).
    """
    domains = [s.domain for s in get_sources_for_category(category) if s.tier == tier][:limit]
    if not domains:
        return ""
    return f"{product_query} " + " OR ".join(f"site:{d}" for d in domains)
```
**Step 4:** re-run → PASS. **Step 5:** `git commit -m "feat(B0): site-discovery query builder from SOURCE_REGISTRY" -- app/services/source_router.py tests/test_source_router_discovery.py && git push`

### Task F1.2: Bahrain discovery tier in the Tier 1.5 escalation

**Files:** Modify `app/services/structured_comparison_service.py:2476-2546` · Test `tests/test_tier15_bahrain_discovery.py` (create)

**Step 1 — failing test:** mock `search_web`, assert that when `_should_escalate_price_scrape` fires for a NON-luxury product, a `("bahrain", ...)` discovery task is dispatched FIRST with the F1.1 query, and its organic links enter `candidate_urls` ahead of official/authorized/gcc.
**Step 2:** run → FAIL.
**Step 3 — impl:** in the discovery block (`:2489`), prepend:
```python
bahrain_query = build_site_discovery_query(full_name, category, tier="bahrain", limit=4)
if bahrain_query:
    discovery_tasks.insert(0, ("bahrain", search_web(bahrain_query)))
```
Harvest in priority order **bahrain → official → authorized → gcc**; bahrain candidates gate via `score_source(link, category) >= 1.5` (registry membership IS the counterfeit whitelist — unknown domains score 0.5 and are rejected; Dispatcher invariant #1 preserved).
**Step 4:** run new test + existing `tests/test_parallel_race_escalation.py` → PASS, no regression. **Step 5:** commit (path-restricted) + push.

### Task F1.3: Registry-first gates with legacy fallback

**Files:** Modify `structured_comparison_service.py:2535,2544` · Test `tests/test_tier15_registry_gate.py` (create)

Replace set-membership gates with `score_source(link, category) >= 1.5 or link_domain in <legacy set>` (registry-first, legacy-fallback — legacy sets at `price_service.py:229-249` stay untouched this bundle). Test: an `ounass.com` fashion link passes via registry; a `dhgate.com` link fails both; a legacy-only domain still passes via fallback. TDD steps as above; commit.

### Task F1.4: source_trace records routing path

**Files:** Modify the `source_trace` collector in `structured_comparison_service.py` · extend `tests/test_source_trace_observability.py`

Add `route: "registry" | "legacy_fallback" | "tier1"` + `source_weight` to each price-value trace entry. Test asserts both fields present on escalated paths. Commit.

### Task F1.5: Registry expansion (Bahrain brands + Arabic content sources)

**Files:** Modify `app/services/source_router.py:26-67` · extend `tests/test_source_router_bahrain_first.py`

Draft additions from Lulu/Carrefour BH category leaders (grocery/supplements/haircare gaps: e.g. alosra.com.bh, sterling pharmacy, mPharmacy) + Arabic review-content sources (sayidaty.net, khaleejtimes.com AR, gulfnews.com AR) tagged for review categories at gcc weight. **CHECKPOINT: Ahmed ratifies the list before merge.** Tests: tier ordering invariants hold; new domains score correctly. Commit.

### Task F1.6: `tier1_5_hit_rate` metrics in /admin/costs

**Files:** Modify `app/services/structured_comparison_service.py` (escalation outcomes), `app/api/admin_routes.py:89-123` (`api_costs`) · Test `tests/test_tier15_hit_rate_metric.py` (create)

Redis counters via `cache_service` helpers: `tier15:attempts:{category}:{YYYYMMDD}`, `tier15:hits:{category}:{YYYYMMDD}`, `tier15:source_hits:{domain}:{YYYYMMDD}` (30d TTL, fire-and-forget, fail-open). `/admin/costs` gains `tier1_5_hit_rate` block (per-category 7-day aggregate). TDD; commit.

### Task F1.7: Lane QA — bias-matrix Bahrain consultation probe

Run the 24-query matrix (`.qa-bias-rerun/` fixture) against a local uvicorn with F1 branch; assert ≥1 `route: "registry"` trace on every non-luxury escalating query; record before/after `gpt_training`-priced counts in the lane report. No commit (evidence artifact to team channel).

## Lane F2 — Extraction/perf follow-ups

**Branch:** `feature/B0-extraction-perf`

- **F2.1 AC/appliance schema:** add `air_conditioner` product-type keys (cooling_capacity_btu, energy_rating, refrigerant, inverter, coverage_sqm) to `app/services/product_type_router.py` (34→35 schemas). TDD against `tests/test_product_type_router.py` pattern; verify PRODUCT_PARSER electronics enum (B0-A BUG #1) routes "Carrier 1.5 ton" → schema. Commit.
- **F2.2 iHerb cascade tightening:** in `price_service.py` `fetch_iherb_price`, add the 2 missing selector fallbacks (price-in-JSON-LD + meta itemprop) BEFORE the miss path that triggers Firecrawl/Scrape.do fan-out (the 5–15s cost). Test with recorded HTML fixtures (no live calls in free tier). Commit.
- **F2.3 Blocklist single-word audit:** script `scripts/audit_blocklist_collisions.py` — for each single-word entry in `data/content_blocklist.json`, grep a product-name corpus (gold-truth queries + brand lists) for substring collisions; convert flagged entries to multi-word phrases (the B0-E "opium" pattern, `9f6e498`). Regression tests per fix. Commit.
- **F2.4 Dim-winners population gap (L1.3):** root-cause at `scoring_service.py:2320` (`build_dimensions_v2`) — trace why `dimensions[i].winner` emits None while `compute_dimension_winners` (`:1438`) computes correctly; suspect breakdown-key mismatch or `MISSING_SCORE=50` short-circuit. Fix + authoritative `winner` field + missing `ecosystem`/`futureproof` dims; pin with the 3 prod fixtures from L1's factual_verdict regression net. Commit.
- **F2.5 lru_cache isolation:** verify B0-C's autouse fixture covers `tests/test_pain_workflow_loader_edges.py` lines 74-122; if not, add `pwl.reset_cache()` autouse fixture (~5 min). Commit.

## Lane F3 — B.1 DB + wiring

**Branch:** `feature/B1-db-wiring` · Migrations apply via Supabase MCP `apply_migration` (NOT SQL Editor), schema-verified after EACH (`information_schema.columns`).

- **F3.1 Migration 032 (pre-apply hardening):** write `migrations/032_b1_pre_hardening.sql` + rollback — drop `comparisons_cache` (0 rows, 0 refs), `ALTER TABLE products ENABLE ROW LEVEL SECURITY` + service-role policy, drop duplicate `idx_users_device_fp`. Apply; verify. Commit SQL.
- **F3.2 Apply 027** (`comparison_feedback` 3-state per-axis columns — 0 prod rows, vacuously safe). Verify columns; smoke `POST /api/v1/feedback` still 200 (4-field contract unchanged — columns are nullable extras). Commit any wiring.
- **F3.3 Apply 028–031** sequentially; verify each. `eval_runs` (031) run_kind taxonomy: `ci_pr|nightly|manual|staging_smoke`; `gold_truth_version` = git SHA.
- **F3.4 user_preference_history writes:** wire per preflight doc § 4.3 (`docs/plans/2026-06-08-B-phase1-db-schema-audit-preflight.md`) — fire-and-forget via `_fire_and_forget(coro, label)`, never bare `create_task`. TDD. Commit.
- **F3.5 Mobile pain_workflow_events:** trackEvent call sites in `SmartCompareApp/src/components/StreamingProductCard.tsx` (expand/abandon/screenshot) → existing `/events` batch endpoint. Jest via sync-render pattern (`useFocusEffect` mock as pass-through, plain `render()` + `waitFor()`). `npx tsc --noEmit` green. Commit.
- **F3.6 Fix 5 pre-existing Jest onboarding failures** (Screens.bundleD.contract / OnboardingFlow.analytics / authService.b4 / NewOnboardingHost / OnboardingFlow.bundleE) — structured mock refresh; they sit where F3.4/F3.5 tests live. Commit per file.
- **F3.7 (dispatcher, S1 close):** EAS update for the FE touch — `cd SmartCompareApp && eas update --branch preview --message "B1: pain workflow events"`. Two-launch propagation caveat applies on device verification.

## Lane F4 — B.6 eval pipeline

**Branch:** `feature/B6-eval-pipeline`

- **F4.1 Runner core:** `scripts/eval_runner.py` — load `data/validation_gold_truth.json`, execute queries vs `TARGET_BASE_URL` (httpx async, `nocache=true`, concurrency 3, per-query timeout = `max_wall_seconds` + 10), collect responses + wall times. TDD with mocked transport (`tests/test_eval_runner.py`).
- **F4.2 Grading functions (pure, unit-tested):**
```python
def grade_price(actual_amount, expected: dict) -> bool:   # within [min*0.85, max*1.15]
def grade_specs(actual_specs, expected: dict) -> float:   # fraction of expected keys matched (case/unit-tolerant)
def grade_winner(actual_winner_index, expected_winner_index) -> bool
def grade_factual(response_text, forbidden_facts: list) -> bool  # no forbidden fact appears
```
Weighted pass per query (price .3 / specs .3 / winner .25 / factual .15 — calibratable constant). TDD each.
- **F4.3 eval_runs persistence:** write one row per run (031 schema: run_kind, gold_truth_version = `git rev-parse HEAD:data/validation_gold_truth.json`, pass rates, per-axis averages, p50/p95 wall). Service-role client. TDD with mocked client. Commit.
- **F4.4 Two-mode gate + smoke subset:** CLI — `--mode regression --baseline-run-id <id>` (exit 1 if any axis drops >2% vs baseline row) / `--mode absolute --threshold 0.95` / `--subset smoke20` (curated 20-id list spanning 9 categories, committed as `data/eval_smoke_subset.json`). TDD gate logic. Commit.
- **F4.5 Cadence wiring:** pre-merge = dispatcher runs `--subset smoke20 --mode regression` (documented in this plan + SESSION close-out checklists); nightly = `scripts/cron_eval_nightly.py` (cron_reengagement pattern) — **dispatcher decision at S1 close: register Railway cron or defer to S3** (cost ~$2/night). p95-vs-30s-cap check included in report.
- **F4.6 S1 baseline (AFTER F5 merges):** run full 200 vs prod, `run_kind=manual`; record `run_id` + per-axis baseline in `docs/plans/2026-06-10-bundle-b-s1-baseline.md`. This row is the regression-gate anchor for S2/S3.

## Lane F5 — Gold-set expansion 50→200

**Branch:** `feature/B6-gold-200` · **Note:** live research needs network — team agents (bypassPermissions), NOT sandboxed worktree subagents (memory: `feedback_worktree_subagent_sandbox`).

- **F5.1 Taxonomy:** extend `2026-06-08-A-validation-matrix-50q.md` distribution to +150 specs (9 categories × product types; heavier on the 0%-Bahrain-hit-rate classes: grocery local brands, AC/appliances, haircare). ID scheme continues (`elec-051`…).
- **F5.2 Fact-anchored authoring (batched 25/agent):** live Bahrain prices (lulu.com.bh / sharafdg / boots BH checks), official spec sheets, `expected_winner_index` + rationale, `forbidden_facts` (3+ per query), `max_wall_seconds: 30.0` (new cap), provenance `note` per price band.
- **F5.3 Schema validation test:** `tests/test_gold_truth_schema.py` — all 200 validate (pydantic model mirroring verified schema), unique ids, per-category counts match taxonomy, every new entry has provenance. Commit data + test.
- **F5.4 CHECKPOINT:** Ahmed ratifies all 150 winner labels → `_metadata.ratified_by/at`. **Blocks F4.6 baseline.**

## S1 exit gate (dispatcher checklist)

1. Ring cross-QA green (F1→F2→F3→F4→F5→F1). 2. Merge F2→F3→F4→F5→F1 (`--no-ff`, smoke20 regression run between merges). 3. Bias-matrix re-run: Bahrain consultation on 100% of non-luxury escalations; record `gpt_training`→scraped upgrade %. 4. Immediate prod curl smoke post-push. 5. F4.6 baseline recorded. 6. EAS update (F3.7) + device walk. 7. `pip-audit` + `npm audit` clean. 8. SESSION_BUNDLES.md S1 entry. 9. Worktrees pruned, team disassembled (TeamDelete from the team's own session — leftover dirs need manual reap otherwise).

---

# SESSION 2 — "Intelligence" (outline — refine at S1 close)

**S2.0 (dispatcher, first task):** refine this outline into bite-sized tasks using S1 outputs (baseline numbers, dim-winners root cause, o3-mini access confirmation). Same TDD/team discipline.

- **Lane I1 — Few-shot rotation:** `scripts/cron_few_shot_rotation.py` (weekly) — top-decile `comparison_feedback` (useful=true + winner_correct=true, 027 columns) → `data/few_shot_verdict_examples.jsonl` → inject 3/category into verdict prompt (`extraction_service.py` `build_verdict_prompt`). **Cold-start: seed from gold-set highest-scoring eval outputs.** Privacy: product names + verdict text only.
- **Lane I2 — Anti-patterns + climate flags:** eval-failure distillation → "what NOT to do" prompt exemplars. Climate keys (heat_stability) in makeup/skincare/fragrance schemas + verdict awareness. **NO new scoring dims.**
  - **CARRY-OVER from S1 Lane F1.5 (Arabic review-content sources DEFERRED here, ratified by Ahmed 2026-06-10):** sayidaty.net / khaleejtimes.com (AR) / gulfnews.com (AR) were verified-real but NOT added to `SOURCE_REGISTRY` in S1 because the registry currently feeds ONLY the Tier 1.5 **price-discovery** cascade (`_harvest_candidate_urls` admits any domain scoring ≥1.5 into the scrape pool). News/content domains have no product prices → adding them would burn curl/Firecrawl/Scrape.do budget on price-less pages. **Design to implement here:** add a `usage` (or `kind`) field to the `Source` dataclass — `"price"` | `"review"` | `"both"` (default `"price"` for all existing 30+ entries, so no behavior change) — and have `_harvest_candidate_urls` filter to `usage in ("price","both")` while a NEW review-content path (this lane's confidence wiring) consumes `usage in ("review","both")`. Then add the 3 Arabic sources as `usage="review"`, gcc weight, tagged for review categories (fashion/makeup/skincare/haircare/fragrances). Tests: existing price-harvest invariants unchanged; review path consults the Arabic sources. Source: F1 lane close-out.
- **Lane I3 — Self-critique:** gpt-4o-mini pass, 5 axes 0–10, any <7 → ONE regen. `ENABLE_SELF_CRITIQUE` default OFF. Writes `verdict_critiques` (030) via `_fire_and_forget`. Gates: ≤$0.002/cmp, p95 inside 30s, shadow lift ≥3%. Critique failure → serve original verdict.
- **Lane I4 — Shadow experiments:** o3-mini-verdict arm + multi-agent arm (3× mini analysts + 4o editor) offline vs gold set + replayed prod queries, graded by F4 runner. Promotion: o3-mini quality-up at cost-neutral; multi-agent ≥5% lift. **Envelope rule: multi-agent + self-critique cannot BOTH promote (>$0.015) — at most one, or editor absorbs critique.**

**S2 exit:** eval vs baseline zero-regression + documented lifts · promotion decisions on evidence · few-shot live (seeded) · climate flags on device · merged + smoked. **Ahmed: Reddit app + YouTube key created this week.**

# SESSION 3 — "Sources" (outline — refine at S2 close)

**S3.0 (dispatcher, first task):** refine using S2 outputs + IG/TT walk verdict (known since week 1).

- **Lane S1 — Reddit:** OAuth, per-category subreddit map (kickoff-prep § B.4), REVIEWS-race participant (`wait_for` cap, None on miss), 14d cache, `ENABLE_REDDIT_SOURCE`.
- **Lane S2 — YouTube:** Data API, review-count + top-video-title signal, REVIEWS race, quota 100 search/day tracked in `api_budget_service`, `ENABLE_YOUTUBE_SOURCE`.
- **Lane S3 — Apify IG/TT (CONDITIONAL: walk ≥3/5):** fragrances/makeup/skincare/fashion ONLY; `apify` counters + breaker (Firecrawl pattern, `api_budget_service.py:81-171`); ≤$0.005/cmp; 7d+ cache; `ENABLE_APIFY_SOCIAL`. Walk RED → lane re-scopes to S4 depth.
- **Lane S4 — Direct scrapers:** Fragrantica (longevity/sillage), INCIDecoder (ingredients), PubMed E-utilities (supplements), luxury secondary-market price sanity (Vestiaire/RealReal) — curl_cffi-first iHerb pattern, graceful None, inside races.
- **Lane S5 — B.6 close-out:** `/admin/accuracy` dashboard (Chart.js + admin-static CSP carve-out), 5% production sampling, Sentry accuracy alerts, **bundle-exit eval: absolute ≥95% binding** (short → per-axis gap analysis = post-bundle backlog).

**S3 exit:** ≥1 unique social signal in target categories · exit eval ≥95% or documented gaps · trailing blended cost ≤$0.015 from `/admin/costs` · device walk · SESSION_BUNDLES.md close-out · Sentry zero new unresolved.

---

## Bundle-exit success metrics

200-query eval ≥95% weighted · Bahrain source consulted on 100% of non-luxury escalations, ≥40% `gpt_training`→scraped upgrade on gold queries · self-critique promoted only on ≥3% lift · ≥1 social signal/comparison in target categories · blended ≤$0.015 · p95 inside 30s cap · PYTHON-FASTAPI-9 defer-and-monitor.
