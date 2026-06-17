# Faithful Results + Genuine-BH on Free Tier — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Design source of truth: `docs/plans/2026-06-17-faithful-results-genuine-bh-freetier-design.md`.

**Goal:** Make every comparison render the Qaren design-system Results layout with category-faithful structure, fully populated information, a convincing+personalized verdict, paraphrased-praise reviews, fairness-correct prices, and genuine-BH prices served mostly from cache on free scraper subscriptions.

**Architecture:** Two stages. **Stage 1 (Phase 0)** = a dynamic ultracode *discovery* workflow (read-only, adversarial, loops-until-dry) that empirically audits the live system and emits a verified findings doc that *enhances* this plan. **Stage 2 (Phases 1–8)** = a 4-Opus team implements the fixes with TDD + cross-QA, then eval-gate + two-lever deploy.

**Tech Stack:** FastAPI + Python 3.12 (root `app/`), React Native + Expo (`SmartCompareApp/`), Upstash Redis (L1) + Supabase (L2/DB), Serper + Firecrawl + Scrape.do + OpenAI gpt-4o-mini, EAS OTA, Railway.

**Operating constraints (read before any task):**
- Two `app/` dirs — edit **root `app/`** only (`backend/app/` is NOT deployed).
- Windows: pass `encoding='utf-8'` to `open()`/`subprocess`; Bash cwd persists after `cd` into `SmartCompareApp`.
- Trust ONLY `npx tsc --noEmit` for TS, not LSP diagnostics.
- Free-unit tests: `python -m pytest tests/ -v -m "not (live_unit or live_db or integration)" --ignore=tests/test_integration.py`.
- `.copy-policy.json`: no "Winner"/"Failed"/"couldn't"/"try again"; AR no تعذر/فشل. EN/AR i18n for all new copy.
- Path-restricted commits in team work: `git commit -m "msg" -- <paths>`.
- Stale Redis masks deploys — verify with FRESH pairs or `?nocache=true`, never a re-run.

---

## Phase 0 — Discovery (the dynamic ultracode workflow)

**Owner:** dispatcher (not the team). **Output:** `.qa-discovery/FINDINGS.md` + per-area JSON, which fills the `[per findings F-x]` placeholders in Phases 1–8.

### Task 0.1: Dispatcher pre-fetch (controlled, so agents run offline)
**Files:** Create `.qa-discovery/` (gitignored scratch).
- Curl prod `?nocache=true` for **2 pairs × 9 categories** (18 responses) → save JSON. Budget: ~108 Serper + ~$0.31. Use the gold/warmer pairs where they exist.
- Run the **firecrawl-vs-scrape.do head-to-head** probe: a python script (`encoding='utf-8'`, no-prod-write) that calls BOTH providers on ~10 known BH PDP URLs (from `data/warmer_catalog.json` + BH retailers: alhajis, ounass, sonyworld.bh, bn.boots.com, sephora.bh) and records {provider, url, got_price, price, source_method, latency, credits_used}.
- Save the design reference path for agents: `.qa-bias-rerun/_handoff/qaren-design-system/project/ui_kits/mobile/ResultsScreen.jsx`.

### Task 0.2: Build + run the discovery Workflow
**Mechanism:** `Workflow` tool (ultracode), read-only agents analyzing the pre-fetched artifacts + codebase. Phases:
1. **Head-to-head analysis** — agent reads the probe results → recommends warmer engine (firecrawl|scrapedo|both) + per-category source reliability + credits-per-genuine-price. **Decides §3a tiering + §14 open item.**
2. **Per-category audit ×9** (one agent per category, parallel) — read the saved prod JSON + `CATEGORY_SPEC_SCHEMAS`/`CATEGORY_DIMENSIONS`/`CATEGORY_FAIRNESS` → structured findings: {category, specs_populated, dims_correct, fairness_decision_correct, price_state, profile_block_fields_needed}.
3. **FE-vs-design catalog** — agent diffs each live `SmartCompareApp/src/components/results/*` against `ResultsScreen.jsx` → divergence list with severity.
4. **Verdict/personalization/reviews review** — agent reads `extraction_service.COMPARISON_SYSTEM` + sample verdicts + `review_service` → gaps {runner_up_shown, priorities_woven, cohort_emitted, citations_present}.
5. **Completeness critic** — what category/claim/modality wasn't covered; loop back if gaps.
- **Adversarial verify:** every "this is broken" finding gets a second skeptic agent that tries to refute it (default-refuted-if-uncertain). Only confirmed findings enter `FINDINGS.md`.

### Task 0.3: Synthesize + enhance the plan
- Dispatcher folds `FINDINGS.md` into Phases 1–8 (fill `[per findings F-x]`), re-orders by severity, marks any workstream that the audit clears as "no-op."
- **Gate:** dispatcher reviews findings before dispatching the team.

---

## Phase 1 — Sourcing + cache architecture (Backend owner)

> The free-tier survival layer. TDD each task. Genuine source methods set: `_GENUINE_BH_SOURCE_METHODS` (keep eval parity — `tests/test_eval_genuine_methods_parity.py`).

### Task 1.1: Long-TTL for genuine-BH prices
**Files:** Modify `app/services/product_data_service.py` (L2 price TTL) + `app/services/cache_service.py` (L1 price TTL); Test `tests/test_price_cache_ttl.py`.
- TDD: test that a genuine source-method price caches with the long TTL (value `[per findings F-cache]`, default 7d) and an `estimated`/`converted_fallback` price keeps the short TTL (24h). Implement TTL branch keyed on source_method. Commit.

### Task 1.2: Cache-first gate before any render
**Files:** Modify `app/services/price_service.py` (the firecrawl/scrapedo call sites); Test `tests/test_cache_first_render_gate.py`.
- TDD: test that with a cache hit present, NO firecrawl/scrapedo call is made (mock the services, assert not called). Implement an L1→L2 check ahead of the render cascade. Commit.

### Task 1.3: Negative-cache structural dead-ends
**Files:** Modify `app/services/price_service.py` + `cache_service.py`; Test `tests/test_negative_cache_structural_gap.py`.
- TDD: test that after a "no genuine BH source" outcome for a known-structural item, a second call within TTL skips the scrape cascade and returns the pending/estimated state from cache. Implement a `nogenuine:{key}` sentinel with its own TTL. Commit.

### Task 1.4: Fairness-correct cache keys
**Files:** Modify the cache-key builder in `price_service.py`/`product_data_service.py`; Test `tests/test_cache_key_size_variant.py`.
- TDD: test that "iPhone 15 256GB" and "iPhone 15 128GB" produce DISTINCT cache keys. Implement normalized-product + size/variant key. Commit.

### Task 1.5: Tiering — Serper-light discovery feeds scraper-heavy render
**Files:** Modify `price_service.py` cascade order per Phase-0 head-to-head winner; Test `tests/test_sourcing_tiering.py`.
- `[per findings F-headtohead]` — set primary heavy renderer; keep Serper as light discovery. TDD the order + the warmer's Serper-free path. Commit.

### Task 1.6: Hit-rate observability
**Files:** Modify `app/services/structured_comparison_service.py` (metadata) + `/admin/costs`; Test `tests/test_cache_hitrate_metadata.py`.
- TDD: response `metadata` carries `{cache_hit, genuine_from_cache}`. Implement counters. Commit.

---

## Phase 2 — Results FE prune → design (Frontend owner)

### Task 2.1: Remove the redundant HeroRings card
**Files:** Modify `SmartCompareApp/src/components/results/ResultsContent.tsx:329-414` (the scoring_v2 hero block) + `HeroRings.tsx`; Test `__tests__/components/ResultsContent.*`.
- `[per findings F-fe]` — TDD that the rings card is gone and DimensionBars remains in the design's slot; update `rewriteOrder` test anchors. Commit.

### Task 2.2: Un-suppress the runner-up caption (FE BUG #4 — confirmed)
**Files:** Modify `ResultsContent.tsx:297-316`; Test `__tests__/components/ResultsContent.runnerUp.test.tsx`.
- TDD: when `scoring_v2.factual_verdict.line1` AND `overview.winner.key_tradeoff` both exist, the runner-up caption block STILL renders. Implement: render FactualVerdict AND the runner-up caption (don't gate one out). Commit.

### Task 2.3: Lighten section chrome to match design
**Files:** Modify `ResultsContent.tsx` styles; Test snapshot.
- `[per findings F-fe]` — TDD against the design's lean section treatment. Commit.

---

## Phase 3 — Category-faithful render, all 9 (Frontend + Backend)

### Task 3.1: Category "profile" block component
**Files:** Create `SmartCompareApp/src/components/results/CategoryProfile.tsx`; Test `__tests__/components/CategoryProfile.test.tsx`.
- `[per findings F-cat-*]` — renders category-appropriate block (fragrance: scent family + notes + longevity/sillage; supplements: count/dosage; electronics: key specs; …) from backend payload. Hidden when fields missing. TDD per category fixture. Commit per category.

### Task 3.2: Backend category payload completeness ×9
**Files:** Modify `app/services/extraction_service.py` (`CATEGORY_SPEC_SCHEMAS`) + `response_builder.py`; Test `tests/test_category_payload_completeness.py`.
- `[per findings F-cat-*]` — for each category flagged with blank/partial specs, fix the schema/prompt so both products populate. TDD with the Phase-0 prod fixtures. Commit per category.

### Task 3.3: Category dims correctness
**Files:** `app/services/scoring_service.py` (`CATEGORY_DIMENSIONS`); Test `tests/test_category_dimensions.py`.
- `[per findings F-cat-*]` — ensure no electronics-flavored dims leak to other categories (keystone fixed fragrance; verify the rest). Commit.

---

## Phase 4 — Verdict / personalization (Backend owner)

### Task 4.1: System prompt — convince + runner-up case + priorities
**Files:** Modify `app/services/extraction_service.py` `COMPARISON_SYSTEM` (~596) + verdict builder (~1539-1562); Test `tests/test_verdict_prompt_contract.py`.
- TDD (prompt-contract style): the prompt instructs (a) make the winner's case convincingly, (b) name who should pick the runner-up and why, (c) reference the user's stated priorities explicitly. Assert the forbidden-words audit still passes. Commit.

### Task 4.2: Personalization end-to-end verification
**Files:** verify `scoring_v2.personalization.applied_shifts` + `cohort_summary` emission; Test `tests/test_personalization_e2e.py`.
- `[per findings F-pers]` — TDD that explicit priorities produce shifts + chip, and cohort line emits when block active. Fix gaps. Commit.

---

## Phase 5 — Reviews: paraphrased praise (Backend + Frontend)

### Task 5.1: Synthesized positive summary (no verbatim, no citations)
**Files:** Modify `app/services/review_service.py` (`build_retailer_quotes_from_reviews` ~243, `clean_review_citations` ~132); Test `tests/test_review_paraphrase.py`.
- TDD: output is a synthesized praise line per product (non-verbatim), no `[N]`/domain markers; rating only when a real one exists (never fabricated). Commit.

### Task 5.2: FE review line renders paraphrase
**Files:** Modify the review accordion in `SmartCompareApp/src/components/results/ResultsAccordion.tsx`; Test `__tests__`.
- TDD: renders the paraphrase line, no citation chips; EN/AR. Commit.

---

## Phase 6 — Fairness audit fixes (Backend owner)

### Task 6.1: Fairness edge-case fixes
**Files:** Modify `app/services/price_service.py` (`CATEGORY_FAIRNESS`, `target_pair_value`, `reconcile_pair_fairness`); Test `tests/test_pair_fairness*.py`.
- `[per findings F-fair-*]` — fix whatever edge cases the audit surfaces (missing size, tolerance bands, one-fixed-size, honor-each). TDD each. Commit.

### Task 6.2: Fragrance size capture (P2)
**Files:** Modify `extract_size_ml_any`/`extract_price_from_html` in `price_service.py`; Test `tests/test_fragrance_size_capture.py`.
- `[per findings F-frag-size]` — improve capture when size is in a variant-widget/image (not JSON-LD/title). TDD; flagship-100ml stays last-resort. Commit.

---

## Phase 7 — Eval / harness (Test owner)

### Task 7.1: B2 — proper smoke20 `--persist` baseline
- Run `python -m scripts.eval_runner --subset smoke20 --mode baseline --persist --concurrency 1` (sandbox-disabled). If box can't DNS-reach Supabase, insert the `eval_runs` row via Supabase MCP (project `qulajmyxdbdkchvecmvc`). Record the new baseline run-id in the runbook. Commit runbook update.

### Task 7.2: A4 — cache-reading eval variant (build now, measure later)
**Files:** Modify `scripts/eval_runner.py` (a `--read-cache` mode that does NOT pass `nocache=true`); Test `tests/test_eval_cache_read_mode.py`.
- TDD the mode flag. Note in output: measurement is meaningful only post-warmer-activation. Commit.

### Task 7.3: Regression gate on team changes
- After Phases 1–6 merge, run `python -m scripts.eval_runner --subset smoke20 --mode regression --baseline-run-id <B2 id> --concurrency 1`. Gate: no weighted-score regression. Record result.

---

## Phase 8 — Verify + deploy (dispatcher)

- **Claude-side:** per-category `?nocache=true` prod curls (data populates, fairness correct, genuine-or-pending) + FE-code-vs-design (`ResultsScreen.jsx`) + Phase-7 regression gate green.
- **Deploy:** backend merge `--no-ff` → Railway ~90s → prod-smoke → `cd SmartCompareApp && eas update --branch preview` → confirm OTA group SHA.
- **Ahmed handoff (zero Claude tokens):** on-device walk checklist (relaunch ×2; fresh fragrance + phone + 1 other category; verify scent dims/specs/paraphrase/runner-up line/cohort line/fairness); warmer cron + `ENABLE_PRICE_CACHE_WARMER`; EAS two-relaunch.

---

## Team structure + rules (Stage 2)

- **4 Opus agents** (no Sonnet/Haiku), worktree-isolated (`bypassPermissions`): **Backend** (Phases 1,4,6 + 3.2/3.3), **Frontend** (Phases 2,3.1,5.2), **Test** (Phase 7 + red-green to 80% for all new code), **Integration-QA** (cross-checks + Phase 8 prep).
- **Rules (from Ahmed):** features 100% complete; **every member QAs another's work before disassembly**; subpar/missed → **sent back**; idle member → **write red-green tests to 80%** OR await QA; work **delegated**, not hoarded.
- **Ops:** FE worktree needs `node_modules` (junction the main tree's, or FE member works in main tree); path-restricted commits; inbox-ACK every ruling; escalate idle >30min / 3 silent nudges.

---

## Execution model

1. Dispatcher runs **Phase 0** (discovery workflow) → `FINDINGS.md`.
2. Dispatcher enhances this plan (fills `[per findings F-x]`).
3. Dispatcher dispatches the **4-Opus team** for Phases 1–7 with cross-QA.
4. Dispatcher runs **Phase 8** verify + deploy; hands Ahmed the on-device checklist.
