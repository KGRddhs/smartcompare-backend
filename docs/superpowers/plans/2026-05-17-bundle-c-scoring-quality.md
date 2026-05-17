# Bundle C — Scoring + Personalization Quality Pass — Implementation Plan

> **For Claude:** This plan is designed for parallel execution by a 4-Opus-agent team via `TeamCreate` (`mode: "bypassPermissions"` required — sandbox blocks Bash otherwise, per CLAUDE.md). DO NOT execute single-threaded with `superpowers:executing-plans`. Spawn the team described in the "Team Spawning Instructions" section below, hand each agent their assigned section, and enforce the Cross-QA matrix + Disassembly Gate (Section D) before allowing any agent to terminate.

**Goal:** Replace, deepen, and correct parts of Bundle E with a calibrated-honesty scoring engine. Fix three production bugs (pros/cons empty, `factual_verdict` always None, mainstream prices fall to estimated). Kill the missing-data floor of 30. Add 5-tier budget system (incl. `top_tier`) with category-scaled BHD breakpoints + geometric-mean `other` sub-scale. Make value math priority-aware. Loosen confidence thresholds + replace single-word banner with 3-pill row + tap-reveal. Add qualitative personalization chip below verdict. Surface 3-tier spec fallback so non-negotiable specs are never blank. All changes silent on backend internals; user-facing UI stays calibrated and respectable.

**Architecture:** Backend-driven scoring/calibration changes inside an `ENABLE_BUNDLE_C_SCORING` feature flag (default OFF in code, flipped ON in Railway). Frontend ships tier-expansion UI ungated (additive); ships the rest defensively (renders correctly with flag OFF using legacy contract). Diagnostic-first discipline for §1a / §1b / §1c — evidence captured before any patch lands.

**Tech Stack:** Python 3.12 / FastAPI / Supabase JSONB / Redis (existing) / React Native + Expo / pytest / Jest.

**Branch:** `feature/bundle-c-scoring` (current HEAD when planning began).

**Design doc:** `docs/superpowers/specs/2026-05-17-bundle-c-scoring-quality-design.md`

**Coverage target:**
- 80% line coverage on touched backend files (scoring_service, extraction_service, response_builder, structured_comparison_service).
- 90% on new scoring formulas (`_compute_value_score`, `_detect_price_tier`, `_compute_raw_scores`, `calibrate_score`, `_compute_applied_shifts`, `_classify_comparison_quality`).
- 80% on new frontend components (DimensionBars, ConfidencePills, PersonalizationChip, BudgetPicker).
- 100% branch coverage on `value_match` (4 states) and `comparison_quality` (3 states) classifiers.

---

## CRITICAL RULES (absorbed during brainstorm — every agent must enforce these)

These five rules are NON-NEGOTIABLE. Every commit, every PR, every QA pass must respect them:

1. **NO info banners in user-facing UI** — per-element microcopy only (pills, captions, verdict text). Reference: `memory/feedback_no_info_banners.md`.
2. **NO backend internals in user-facing diagnostic reveals** — qualitative arrows/labels only. Never coefficients, cap percentages, or shift math in API responses or UI. Reference: `memory/feedback_no_backend_internals_in_reveals.md`.
3. **NEVER use "estimated" / "reference price" / "indicative" in user-facing UI** — backend `source_method="estimated"` enum stays, UI silent on price provenance. Disclosure shifts to Terms (spec § 2i). Reference: `memory/feedback_no_estimated_word_in_ui.md`.
4. **Diagnostic-first for §1a / §1b / §1c** — evidence gate (Section D.1) is BLOCKING before any patch ships. No speculative fixes. Reference: `memory/feedback_measure_before_optimize.md`.
5. **NO scary copy in user-facing i18n** — forbidden vocabulary in EN: `couldn't`, `try again`, `Failed to`. Forbidden in AR: `تعذر`, `فشل`. Approved vocabulary in design § 6.

---

## Pre-Flight (manual, ONE-TIME — Ahmed runs these first)

Before spawning the team:

- [ ] Decide whether to apply Migration 024 BEFORE or DURING team session. **Recommendation: during session, via Supabase MCP `apply_migration` after Section A.1.1 writes the SQL.** Tracks in migration history table.
- [ ] Verify `ENABLE_BUNDLE_C_SCORING` env var slot exists in Railway. Default value: `false`. Will be flipped after D.4.2 backwards-compat smoke passes.
- [ ] Confirm Firecrawl + Scrape.do API budgets have headroom for D.1.2 diagnostic probes (6-7 cold-cache `?nocache=true` calls). Per CLAUDE.md: Firecrawl 450 lifetime, Scrape.do 900/month, Serper 2200 lifetime. Confirm Redis circuit-breaker state clean before starting.
- [ ] Decide whether to bump Sentry sampling for the 24h post-deploy window (per D.6.4). Default is "no — current sampling is enough for low-tester volume."
- [ ] (If applicable) Pre-clear any in-flight `feature/*` branches that touch `scoring_service.py`, `extraction_service.py`, or `response_builder.py` to avoid merge conflicts before spawning the team.
- [ ] Confirm `feature/bundle-c-scoring` branch is current HEAD (per design doc header).
- [ ] Confirm `STREAM_HARD_CAP_SECONDS=25.0` is the current production lock (verify in Railway).
- [ ] Confirm Bundle E's `scoring_v2` + `dimensions[]` contract is the current baseline (per design doc header: predecessor).

---

## Team Spawning Instructions

After pre-flight, spawn 4 Opus agents in a single `TeamCreate` call with `mode: "bypassPermissions"`. Hand each agent their numbered section block below + the design doc path.

**Per-agent assignments:**
- **Section A** → `backend-bundle-c` (owns backend services + migration + legal markdown)
- **Section B** → `frontend-bundle-c` (owns React Native screens, components, i18n, types)
- **Section C** → `test-bundle-c` (owns all pytest + Jest test files, coverage gates)
- **Section D** → `qa-bundle-c` (cross-QA, migration apply, flag rollout, post-deploy verification, memory updates)

**Common preamble for ALL agents:**

> Read `docs/superpowers/specs/2026-05-17-bundle-c-scoring-quality-design.md` and `CLAUDE.md` before doing anything. You are part of a 4-agent team. Your assigned tasks are in `docs/superpowers/plans/2026-05-17-bundle-c-scoring-quality.md` under your section. Follow TDD strictly — write the failing test FIRST, run it to confirm failure, then implement the minimal code to make it pass, then commit. Honor the FIVE critical rules at the top of the plan. Diagnostic-first for §1a / §1b / §1c — Section D.1 evidence gate is BLOCKING before any §1a/§1b/§1c fix may land. Idle behavior: NEVER idle silently — pick from your section's idle-work backlog or send-back any waiting peer reviews. Cross-QA is mandatory before disassembly — see Section D.2 + D.8.
>
> Path-restricted commits in this team session: ALWAYS use `git commit -m "msg" -- <paths>` (NOT `git commit -- <paths> -m "msg"` — the `--` is a path separator). Per CLAUDE.md: anything after `--` is treated as a path and `-m` errors. This prevents sweeping teammates' staged work into your commits.
>
> If you go silent mid-task for > 30 min: per CLAUDE.md "Multi-agent silent stalls" rule, you will be replaced by dispatcher takeover. Save state frequently and respond to all `SendMessage` nudges within 5 min.

> ⚠️ **CROSS-SECTION NOTE:** Section A's header inside this plan says "backend-cohort" (a copy-paste artifact from the reference cohort plan). The agent is named `backend-bundle-c` per the team spawn config. All Section A content is current and correct; only the agent-name string in the section's title line is stale. Section A may rename their own header in their first commit if they wish — non-blocking.

---

## Section interdependencies (cross-section blockedBy summary)

These are the inter-section dependencies extracted during assembly. Each agent should read this BEFORE starting their section:

| Dependent | Depends on | Reason |
|---|---|---|
| **A.3.1** (§1a fix) | **D.1.3** (root-cause documented) | Diagnostic-first — no speculative patches. |
| **A.3.2** (§1b factual_verdict builder) | **D.1.3** (root-cause documented) | Pure template fix, but still gated by evidence-first principle. |
| **A.3.3** (§1c price-pipeline fix) | **D.1.3** (root-cause documented) | Diagnostic-first — no speculative patches. |
| **A.2.4** (capture 6-probe evidence) | **A.2.1, A.2.2, A.2.3** (diagnostic logging in place) | Logging must land before probes run. |
| **D.1.1, D.1.2, D.1.3** (diagnostic gate) | **A.2.1, A.2.2, A.2.3, A.2.4** (logging hooks + probe runner) | qa orchestrates, backend executes. |
| **D.1.4** (disable diag env vars) | **A.10.1** (remove diagnostic logging in code) | Cleanup pairs across A + D. |
| **B.x** (frontend) | **A.1.x** (contract definitions in `scoring_service` + `response_builder`) | Frontend stubs API shape against design spec and starts UI work immediately — final wire-up validated at QA per Section B blocked-by note. Frontend is NOT hard-blocked. |
| **B.3 / B.4** (BudgetPicker 5-tier) | **A.5.4** (Pydantic `BudgetValue` Literal extension) | Frontend literal mirrors backend literal. |
| **C.x.x** (test tasks) | various A.x / B.x impl tasks | Per Section C's pre-flight: tests are written failing FIRST against the design spec. The test itself can land before the impl; it stays RED until the impl lands. |
| **D.3.1** (apply Migration 024) | **A.1.1** (write Migration 024 SQL) | Migration SQL must exist before apply. |
| **D.4.x** (flag rollout) | All A + B + C tasks complete | Cannot deploy until impl + tests green. |
| **D.6.x** (post-deploy verification) | **D.4.3** (flag flipped ON in Railway) | Verification runs against production with flag ON. |
| **D.8** (Disassembly Gate) | EVERY other task above | Final gate. |
| **D.9.1, D.9.2, D.9.3** (memory + docs updates) | A.11.1, A.11.2, A.11.3 (Section A also updates CLAUDE.md/MEMORY/SESSION_BUNDLES) | **Coordination point** — Section A documents technical changes; Section D adds rollout/canary/ship evidence. **Resolution:** Section A goes FIRST (writes the technical entries), Section D APPENDS rollout + verification evidence to the same files. No conflict if Section D respects pre-existing entries from Section A. |

---

## Files-to-touch summary (union of A + B + C + D owner-file lists)

### Backend (Section A)
- `app/services/scoring_service.py` — calibration, missing-data, fabricated-default removal, tier maps, value math, applied_shifts, build_dimensions_v2 adapter
- `app/services/extraction_service.py` — pros/cons diagnostic logging, 3-tier spec fallback (Tier 2 + Tier 3), verdict prompt instructions, CRITICAL_SCHEMA_FIELDS split
- `app/services/structured_comparison_service.py` — pros/cons raw-response logging hook, weird-comparison detector, fallback Tier 2/3 orchestration
- `app/services/response_builder.py` — `factual_verdict` builder restoration, `personalization.applied_shifts[]` shaping, `comparison_quality` + `value_match` + `budget_mismatch` passthrough
- `app/services/trust_validation_service.py` — verify validation order does not strip pros/cons fields before pop (1a root-cause check only)
- `app/services/firecrawl_service.py` — diagnostic invocation-counter logging (1c, no behavior change)
- `app/services/scrapedo_service.py` — diagnostic invocation-counter logging (1c, no behavior change)
- `app/services/api_budget_service.py` — diagnostic surface for credit/circuit-breaker state (1c, read-only logging hook)
- `app/legal/terms_of_service.md` + Arabic equivalent — §2i AI-extraction disclosure clause
- `app/legal/privacy_policy.md` + Arabic equivalent — §2i clause if data-quality section exists
- `migrations/024_top_tier_budget.sql` + `migrations/rollback/024_top_tier_budget.sql`

### Frontend (Section B)
- `SmartCompareApp/src/components/BudgetPicker.tsx`
- `SmartCompareApp/src/screens/onboarding/Step09Budget.tsx`
- `SmartCompareApp/src/screens/onboarding/types.ts` (`OnboardingBudget` literal extension)
- `SmartCompareApp/src/components/results/DimensionBars.tsx`
- `SmartCompareApp/src/components/results/HeroRings.tsx` (copy + sparse-data adaptation only)
- `SmartCompareApp/src/components/results/FactualVerdict.tsx` (contract verification only — backend wires line1/line2 in Section A 1b)
- `SmartCompareApp/src/components/results/ConfidencePills.tsx` (NEW — 3-pill horizontal row)
- `SmartCompareApp/src/components/results/ConfidenceDetailsSheet.tsx` (NEW — "What we know" bottom sheet)
- `SmartCompareApp/src/components/results/PersonalizationChip.tsx` (NEW)
- `SmartCompareApp/src/components/results/DimensionBarsExpand.tsx` (NEW — expand row + animated container, OR co-located in `DimensionBars.tsx`)
- `SmartCompareApp/src/screens/ResultsScreen.tsx` (integration — pills, chip, delta hero captions, weird-mode rendering, suppression of legacy banner)
- `SmartCompareApp/src/screens/EditPreferencesFlow.tsx` (5-tier prop pass-through, no logic change beyond literal type)
- `SmartCompareApp/src/services/sourceMethod.ts` (NEW — `parseSourceMethod()` helper)
- `SmartCompareApp/src/types.ts` (Dimension confidence stays optional, new `comparison_quality`, `value_match`, `applied_shifts`, `source_method` types, `BudgetValue` extension)
- `SmartCompareApp/src/i18n/en.json` + `ar.json`
- `SmartCompareApp/__tests__/` snapshot + behavioral tests under `results/` subdir

### Tests (Section C)
- `tests/test_scoring_calibration.py` (extend)
- `tests/test_scoring_service.py` (extend)
- `tests/test_scoring_v2_models.py` (extend)
- `tests/test_dimensions_builder.py` (extend)
- `tests/test_personalization.py` (extend)
- `tests/test_extraction_prompt.py` (extend)
- `tests/test_structured_comparison_service.py` (extend)
- `tests/test_tier_detection.py` (NEW)
- `tests/test_value_math.py` (NEW)
- `tests/test_confidence_thresholds.py` (NEW)
- `tests/test_bundle_c_integration.py` (NEW, `@pytest.mark.integration`)
- `tests/test_security_regression.py` (extend — invariants on existing routes only)
- `tests/_bundle_c_helpers.py` (NEW — assertion helpers)
- `SmartCompareApp/__tests__/DimensionBars.test.tsx` (NEW)
- `SmartCompareApp/__tests__/ConfidencePills.test.tsx` (NEW)
- `SmartCompareApp/__tests__/PersonalizationChip.test.tsx` (NEW)
- `SmartCompareApp/__tests__/BudgetPicker.test.tsx` (NEW or extend)
- `SmartCompareApp/__tests__/ResultsScreen.test.tsx` (extend)
- `SmartCompareApp/src/components/results/__snapshots__/` (snapshots committed)

### QA + Docs (Section D)
- `docs/SESSION_BUNDLES.md` (Bundle C entry — appended in D.1.3 / D.4.2 / D.4.3 / D.6.3 / D.6.4 / D.6.5 / D.7.1 / D.7.3 / D.9.2)
- `CLAUDE.md` (1-line breadcrumb at end of "Bundle history" line — D.9.1)
- `memory/MEMORY.md` and per-topic memory files (drop "Bucket C brainstorm" pending entry — D.9.3)
- `migrations/rollback/024_pre_rollback_downgrade.sql` (NEW — D.7.3 emergency tier-downgrade SQL)
- `docs/runbooks/qaren-canary-onboarding.md` (optional 2-3 line Bundle-C-specific addition — D.5.3)
- `tests/post_deploy/bundle_c_acceptance.md` (idle-work — D idle backlog item 1)

---

## Risk + Rollback (Section D.7 restated at plan level)

**Primary rollback path:** single env-var flip.

```
# Railway:
ENABLE_BUNDLE_C_SCORING=false
```

This reverts ALL scoring/calibration/value/confidence/personalization changes in one command. Frontend gracefully degrades: DimensionBars falls back to legacy 6-dim breakdown, confidence pill row falls back to single-word banner, personalization chip hidden when `applied_shifts` undefined. Budget picker 5-tier UI is non-destructive (additive, ungated).

**Migration rollback:** `migrations/rollback/024_top_tier_budget.sql` drops `top_tier` from the CHECK enum. **Pre-rollback step required:** downgrade any persisted `top_tier` and `luxury` user rows to `premium` first using `migrations/rollback/024_pre_rollback_downgrade.sql`. Otherwise existing rows violate the post-rollback CHECK on next update.

**UI rollback:** non-destructive (additive). Reverting the picker is a fresh `eas update` to the previous bundle. Users' saved `top_tier`/`luxury` preferences silently degrade to `premium` math if both backend flag AND picker revert.

**Sentry watch window:** 24h post-flip (D.6.4). Any new "scoring_service" / "extraction_service" / "response_builder" stack-trace issue triggers emergency flag-off + send-back to backend-bundle-c.

---

## Disassembly Gate (Section D.8 restated at plan level)

Team disassembles ONLY when ALL of these are checked. See Section D.8 for the full enforcement protocol:

- [ ] All Section A tasks complete + committed
- [ ] All Section B tasks complete + committed
- [ ] All Section C tasks complete + committed
- [ ] Cross-QA matrix evidence captured (D.2.1 through D.2.7 all signed off)
- [ ] D.1 diagnostic findings shipped (D.1.3 committed) BEFORE A.3.1 / A.3.2 / A.3.3 patches landed
- [ ] D.1.4 confirmed: all diagnostic env vars disabled post-window
- [ ] D.3.1 Migration 024 applied via Supabase MCP + D.3.3 rollback drill done
- [ ] D.4.2 backwards-compat probes (flag OFF) match Bundle E baseline
- [ ] D.4.3 flag-ON smoke probes confirm all 6 acceptance criteria
- [ ] D.4.4 tier expansion UI works in both flag states
- [ ] D.5 canary phasing documented (D.5.1, D.5.2, D.5.3)
- [ ] D.6.2 post-deploy 6-criteria acceptance ≥6 of 7 probes pass
- [ ] D.6.3 ship evidence captured + committed
- [ ] D.6.4 Sentry 24h baseline diff clean
- [ ] D.6.5 EAS Update preview channel pushed + tester-device confirmed
- [ ] D.7 rollback path verified end-to-end
- [ ] `pytest tests/ -v -m "not (live_unit or live_db or integration)" --timeout=180` 100% pass
- [ ] `cd SmartCompareApp && npx tsc --noEmit` 0 errors
- [ ] `pytest tests/test_security_regression.py -v` 100% pass
- [ ] No PRE-EXISTING tests regressed
- [ ] D.9 memory updates complete

**If ANY gate fails:** team continues. NO premature disassembly. qa-bundle-c may NOT respond `approve: true` to a `shutdown_request` until every box above is checked.

---

## Cross-QA Matrix (Section D.2 restated at plan level)

```
backend-bundle-c   ──reviews──▶  frontend-bundle-c    (D.2.1)
frontend-bundle-c  ──reviews──▶  backend-bundle-c     (D.2.2)
test-bundle-c      ──reviews──▶  backend-bundle-c     (D.2.3)
test-bundle-c      ──reviews──▶  frontend-bundle-c    (D.2.4)
qa-bundle-c        ──reviews──▶  backend-bundle-c     (D.2.5)
qa-bundle-c        ──reviews──▶  frontend-bundle-c    (D.2.6)
qa-bundle-c        ──reviews──▶  test-bundle-c        (D.2.7)
```

Each peer-review pairing must complete BEFORE the Disassembly Gate opens. See Section D.2 for per-review checklists + send-back template.

---



---

# SECTION A — backend-bundle-c tasks (Bundle C: Scoring + Personalization Quality Pass)

> **For Claude:** This is Section A of the Bundle C implementation plan. The full plan is composed across 4 sections (A backend, B frontend, C tests, D qa). Read `docs/superpowers/specs/2026-05-17-bundle-c-scoring-quality-design.md` before doing anything in this section. TDD strictly: failing test first → run to confirm fail → minimal impl → run to confirm pass → commit. Honor the three project-wide rules absorbed in design § 0: no info banners, no backend internals in user-facing reveals, no "estimated" word in user-facing UI. Diagnostic-first for § 1a/1b/1c — no speculative fixes; evidence-gate before patch.

**Owner files (backend scope):**
- `app/services/scoring_service.py` — calibration, missing-data, fabricated-default removal, tier maps, value math, applied_shifts, build_dimensions_v2 adapter
- `app/services/extraction_service.py` — pros/cons diagnostic logging, 3-tier spec fallback (Tier 2 + Tier 3), verdict prompt instruction for `comparison_quality` + `budget_mismatch`, CRITICAL_SCHEMA_FIELDS split
- `app/services/structured_comparison_service.py` — pros/cons raw-response logging hook, weird-comparison detector orchestration, fallback Tier 2/3 orchestration inside STREAM_HARD_CAP_SECONDS budget
- `app/services/response_builder.py` — `factual_verdict` builder restoration, `personalization.applied_shifts[]` shaping, `comparison_quality` + `value_match` + `budget_mismatch` passthrough
- `app/services/trust_validation_service.py` — verify validation order does not strip pros/cons fields before pop (1a root-cause check only)
- `app/services/firecrawl_service.py` — diagnostic invocation-counter logging (1c, no behavior change)
- `app/services/scrapedo_service.py` — diagnostic invocation-counter logging (1c, no behavior change)
- `app/services/api_budget_service.py` — diagnostic surface for credit/circuit-breaker state (1c, read-only logging hook)
- `app/legal/terms_of_service.md` + Arabic equivalent — 2i AI-extraction disclosure clause
- `app/legal/privacy_policy.md` + Arabic equivalent — 2i clause if data-quality section exists
- `migrations/024_top_tier_budget.sql` + `migrations/rollback/024_top_tier_budget.sql`

**Owner non-files (backend-side contracts the frontend consumes):**
- `dimensions[i].score_a` / `score_b` emits `null` cleanly for genuinely-missing signals (frontend renders "—" row per 2b — backend contract only)
- `response.personalization.applied_shifts[]` qualitative direction only (`up`/`down`), never magnitude
- `response.comparison_quality: "normal" | "weak" | "weird"` (no banner trigger)
- `response.products[].value_match: "in_range" | "above_range" | "below_range"`
- `response.metadata.budget_mismatch: "above" | "below" | null` passed to verdict prompt
- Backend strings hitting user-facing fields audited for "estimated" / "reference price" leakage
- No `applied_shifts` magnitude, no value formula coefficients, no calibration band numbers exposed in API responses

**Coverage target:** 80% line coverage on new code (`scoring_service` additions, `response_builder` additions, Tier 2/3 fallback in `extraction_service`, weird detector in `structured_comparison_service`). Push to 90% on `_detect_price_tier` (3e+3f) and `_compute_value_score` (4a-e).

**Pre-flight check (backend-cohort runs once before A.1):**
- [ ] Confirm `feature/bundle-c-scoring` branch is current HEAD (per design § header).
- [ ] Confirm `DEBUG_STAGE_TIMINGS` env var slot is wired (already in CLAUDE.md env vars section).
- [ ] Confirm `STREAM_HARD_CAP_SECONDS=25.0` is the current production lock (verify in Railway).
- [ ] Confirm Bundle E's `scoring_v2` + `dimensions[]` contract is the current baseline (per design § header: predecessor).

---

## A.1 — Migration 024 (top_tier in budget enum)

### Task A.1.1: Write Migration 024 SQL + rollback

**File:** Create `migrations/024_top_tier_budget.sql` and `migrations/rollback/024_top_tier_budget.sql`.

**Step 1:** Write `migrations/024_top_tier_budget.sql`:

```sql
-- Migration 024: Add top_tier to users.preferences.budget CHECK enum
-- Bundle C tier expansion (per design § 3a/3d/8a)
-- Apply via Supabase MCP: mcp__plugin_supabase_supabase__apply_migration

ALTER TABLE public.users
  DROP CONSTRAINT IF EXISTS users_preferences_budget_check;

ALTER TABLE public.users
  ADD CONSTRAINT users_preferences_budget_check
  CHECK (
    preferences->>'budget' IS NULL
    OR preferences->>'budget' IN ('budget', 'mid', 'premium', 'luxury', 'top_tier')
  );

-- Existing rows untouched. New users default to 'mid' (per design § 3d).
-- Backwards-compat: 3-tier values ('budget','mid','premium') remain valid (per design § 3d).
```

**Step 2:** Write `migrations/rollback/024_top_tier_budget.sql`:

```sql
-- Rollback Migration 024 — revert to pre-Bundle-C 4-tier enum
-- WARNING: Any users with budget='top_tier' will fail CHECK; UPDATE to 'luxury' first.

UPDATE public.users
SET preferences = jsonb_set(preferences, '{budget}', '"luxury"')
WHERE preferences->>'budget' = 'top_tier';

ALTER TABLE public.users
  DROP CONSTRAINT IF EXISTS users_preferences_budget_check;

ALTER TABLE public.users
  ADD CONSTRAINT users_preferences_budget_check
  CHECK (
    preferences->>'budget' IS NULL
    OR preferences->>'budget' IN ('budget', 'mid', 'premium', 'luxury')
  );
```

**Step 3:** Update CLAUDE.md `## Commands → Migrations` to add: `024 (Bundle C, pending via MCP) adds 'top_tier' to users.preferences.budget CHECK enum; existing rows untouched, backwards-compat with 3-tier values.`

**Step 4:** Commit:
```bash
git commit -m "migration: 024 top_tier in users.preferences.budget CHECK (Bundle C § 3a)" -- migrations/024_top_tier_budget.sql migrations/rollback/024_top_tier_budget.sql CLAUDE.md
```

**Evidence required for this task:** none beyond compile.

**blockedBy:** none.

---

## A.2 — Diagnostic-first: capture evidence before patches (1a / 1b / 1c)

> **Hard rule (per design § 1):** No speculative fixes. These diagnostics MUST land + capture evidence BEFORE A.3 root-cause patches ship. The diagnostic IS the gate.

### Task A.2.1: Add raw-response logging hook for empty pros/cons (1a diagnostic)

**File:** `app/services/extraction_service.py` (around line 1085+ in `generate_comparison`).

**Step 1:** Write failing test `tests/test_extraction_pros_cons_diagnostic.py`:

```python
import pytest
from unittest.mock import patch, AsyncMock
from app.services.extraction_service import generate_comparison

@pytest.mark.asyncio
async def test_logs_raw_response_when_pros_empty(caplog):
    fake_response_content = '{"winner_declaration": "iPhone wins", "product_0_pros": [], "product_1_pros": []}'
    with patch("app.services.extraction_service.openai_client.chat.completions.create",
               new=AsyncMock(return_value=type("R", (), {
                   "choices": [type("C", (), {"message": type("M", (), {"content": fake_response_content})()})()]
               })())):
        await generate_comparison(...)  # minimal args
    assert "PROS_CONS_DIAGNOSTIC" in caplog.text
    assert "product_0_pros" in caplog.text
```

**Step 2:** Run → FAIL (logging hook doesn't exist).

**Step 3:** In `generate_comparison()`, after `response.choices[0].message.content` is parsed BUT BEFORE `validate_verdict` runs, add:

```python
if len(comparison.get("product_0_pros", []) or []) == 0 or len(comparison.get("product_1_pros", []) or []) == 0:
    logger.warning(
        "PROS_CONS_DIAGNOSTIC raw_response=%s comparison_keys=%s",
        response.choices[0].message.content[:2000],
        list(comparison.keys())
    )
```

**Step 4:** Run → pass.

**Step 5:** Commit `feat(extraction): log raw GPT response when pros/cons empty (1a diagnostic)`.

**Evidence required:** none yet — evidence captured in A.2.4.

**blockedBy:** none.

### Task A.2.2: Add `factual_verdict` None-emit diagnostic (1b diagnostic)

**File:** `app/services/response_builder.py` (around `_build_scoring_v2` line ~36).

**Step 1:** Write failing test `tests/test_response_builder_factual_verdict_diagnostic.py` asserting log fires when builder emits `factual_verdict=None`.

**Step 2:** Run → FAIL.

**Step 3:** In `_build_scoring_v2`, after `factual_verdict` is computed, add:

```python
if factual_verdict is None or (factual_verdict.get("line1") is None and factual_verdict.get("line2") is None):
    logger.warning(
        "FACTUAL_VERDICT_DIAGNOSTIC scoring_v2_emitted_none winner_index=%s products=%s",
        winner_index,
        [(p.get("name"), p.get("price", {}).get("amount"), p.get("rating", {}).get("score")) for p in products]
    )
```

**Step 4:** Run → pass.

**Step 5:** Commit `feat(response): log when factual_verdict emits None (1b diagnostic)`.

**blockedBy:** none.

### Task A.2.3: Add Firecrawl + Scrape.do + Serper invocation-count + circuit-breaker state logging (1c diagnostic)

**Files:**
- `app/services/firecrawl_service.py`
- `app/services/scrapedo_service.py`
- `app/services/api_budget_service.py`

**Step 1:** Write failing test `tests/test_price_pipeline_diagnostic.py`:

```python
@pytest.mark.asyncio
async def test_price_pipeline_diagnostic_emits_per_product_tier_trace(caplog):
    # Run a fake price-pipeline call with DEBUG_STAGE_TIMINGS=true
    # Assert log lines include: source_method per tier (1, 1.5a, 1.5d, 2, 3), Firecrawl/Scrape.do/Serper invocation counts, circuit-breaker state per call
    ...
```

**Step 2:** Run → FAIL.

**Step 3:** Add at each Firecrawl and Scrape.do call site:

```python
# Inside firecrawl_service.scrape_page_with_status():
if os.getenv("DEBUG_STAGE_TIMINGS", "false").lower() == "true":
    logger.info("PRICE_PIPELINE_DIAG firecrawl_invocation url=%s credits_remaining=%s breaker_state=%s",
                url, api_budget.get_remaining("firecrawl"), api_budget.get_breaker_state("firecrawl"))
```

Add analogous logging in `scrapedo_service.scrape_page_rendered()` and in the Serper Shopping call wrapper inside `price_service.py`.

Add to `structured_comparison_service.compare_from_text` (only when `DEBUG_STAGE_TIMINGS=true`): per-product per-tier `source_method` trace log.

**Step 4:** Run → pass.

**Step 5:** Commit `feat(diag): per-tier source_method + scrape invocation logging (1c diagnostic, flag-gated)`.

**blockedBy:** none.

### Task A.2.4: Capture evidence on staging — 6 cold-cache probes

**Step 1:** Set `DEBUG_STAGE_TIMINGS=true` on Railway (manual step — Ahmed runs).

**Step 2:** Run 6 cold-cache probes via curl (per design § 1a + § 1c):

```bash
for q in \
  "iPhone+16+vs+Galaxy+S25" \
  "CeraVe+vs+Cetaphil+Moisturizing+Cream" \
  "Centrum+Silver+vs+One+A+Day+Men's" \
  "Zara+blazer+vs+H%26M+blazer" \
  "Tom+Ford+Oud+Wood+vs+Dior+Sauvage" \
  "Almarai+laban+vs+Saudia+laban"
do
  curl "https://web-production-58776.up.railway.app/api/v1/text/compare?q=${q}&nocache=true" > "evidence_${q}.json"
done
```

**Step 3:** Inspect Railway logs for the 3 diagnostic log groups (PROS_CONS_DIAGNOSTIC, FACTUAL_VERDICT_DIAGNOSTIC, PRICE_PIPELINE_DIAG). Save raw logs to `docs/investigations/2026-05-17-bundle-c-cold-cache-evidence.md`.

**Step 4:** From evidence, identify per § 1a: which suspect fires (verdict JSON drops keys / model omits / validate_verdict strips). Per § 1c: which tier products traverse + where they fall (Serper regional gap / api_budget exhaustion / breaker tripped / `_validate_price_query` reject / `_extract_price_from_html` regression).

**Step 5:** Disable `DEBUG_STAGE_TIMINGS=true` on Railway after evidence captured (per project measure-before-optimize rule + CLAUDE.md env-var note).

**Step 6:** Commit `docs(investigation): Bundle C cold-cache evidence + root-cause identification`.

**Evidence required:** investigation file MUST identify root cause for each of 1a / 1b / 1c before A.3 patches land.

**blockedBy:** A.2.1, A.2.2, A.2.3.

---

## A.3 — Bug fix patches (gated by A.2.4 evidence)

### Task A.3.1: Patch 1a root cause (pros/cons empty) — implementation TBD by A.2.4 evidence

**File:** depends on root cause identified in A.2.4 — likely `app/services/extraction_service.py` (line 580-587, line 1085+) or `app/services/trust_validation_service.py` (validate_verdict ordering).

**Step 1:** Write failing test `tests/test_extraction_pros_cons_populated.py`:

```python
@pytest.mark.asyncio
@pytest.mark.parametrize("category,query", [
    ("electronics", "iPhone 16 vs Galaxy S25"),
    ("skincare", "CeraVe vs Cetaphil"),
    ("supplements", "Centrum Silver vs One A Day"),
    ("fashion", "Zara blazer vs H&M blazer"),
    ("fragrances", "Tom Ford Oud Wood vs Dior Sauvage"),
    ("grocery", "Almarai laban vs Saudia laban"),
])
async def test_pros_cons_populated(category, query, mock_openai_realistic):
    result = await get_comparison_service().compare_from_text(query=query, region="bahrain", selected_category=category)
    assert len(result["products"][0]["pros"]) > 0, f"{category}: product 0 pros empty"
    assert len(result["products"][1]["pros"]) > 0, f"{category}: product 1 pros empty"
    assert len(result["products"][0]["cons"]) > 0, f"{category}: product 0 cons empty"
    assert len(result["products"][1]["cons"]) > 0, f"{category}: product 1 cons empty"
```

**Step 2:** Run → FAIL (matches design § 1a probe evidence).

**Step 3:** Patch ONLY the root cause identified in A.2.4. Per design § 1a, do NOT add fallback re-prompt unless diagnosis proves it. The likely candidates:
- If verdict JSON drops keys: tighten prompt instruction in `_build_preferences_prompt` or `extraction_service.py:580-587`.
- If model omits: move the cohort/preference block earlier OR shorten it.
- If `validate_verdict` strips: reorder pop + validation in `structured_comparison_service.py:704-712`.

**Step 4:** Run all 6 probes → all PASS.

**Step 5:** Commit `fix(extraction): root-cause patch for empty pros/cons (1a — <root cause from A.2.4>)`.

**Evidence required:** A.2.4 root-cause identification + 6/6 probes pass.

**blockedBy:** A.2.4.

### Task A.3.2: Restore `factual_verdict` builder in response_builder.py (1b)

**File:** `app/services/response_builder.py`.

**Step 1:** Write failing test `tests/test_response_builder_factual_verdict.py`:

```python
def test_factual_verdict_line1_is_strongest_factual_delta():
    products = [
        {"name": "iPhone 16", "price": {"amount": 350.0}, "rating": {"score": 4.5, "count": 1200}, "scores": {"performance": 88}},
        {"name": "Galaxy S25", "price": {"amount": 280.0}, "rating": {"score": 4.4, "count": 800}, "scores": {"performance": 92}},
    ]
    fv = _build_factual_verdict(products=products, winner_index=0)
    assert fv["line1"] is not None
    # line1 must reference the strongest delta — could be price gap, rating gap, or top dim margin
    assert any(kw in fv["line1"].lower() for kw in ["cheaper", "less", "more", "higher", "stars", "performance"])

def test_factual_verdict_line2_is_runner_up_counter_fact():
    fv = _build_factual_verdict(products=products, winner_index=0)
    assert fv["line2"] is not None
    # line2 must be the runner-up's strongest counter-fact (e.g., "but Galaxy is 20% cheaper")
    assert fv["line2"] != fv["line1"]

def test_factual_verdict_never_uses_estimated_word():
    # Per design § 0 rule 3 + § 11
    fv = _build_factual_verdict(products=products_with_estimated_price, winner_index=0)
    assert "estimated" not in fv["line1"].lower()
    assert "estimated" not in fv["line2"].lower()
    assert "reference price" not in fv["line1"].lower()
    assert "reference price" not in fv["line2"].lower()
```

**Step 2:** Run → FAIL (builder missing per design § 1b).

**Step 3:** Implement `_build_factual_verdict(products, winner_index)` pure template — zero GPT cost:
- `line1` = compute three candidate deltas (price gap %, rating gap stars, top-dim margin), pick the largest absolute magnitude, render winner-anchored.
- `line2` = compute runner-up's largest non-overlapping counter-fact, render anchored to runner-up.
- Audit string templates for forbidden words: `estimated`, `reference price`, `couldn't`, `try again`, `Failed to`, `تعذر`, `فشل` (per project copy contract in CLAUDE.md Qaren UX section).

**Step 4:** Wire into `_build_scoring_v2` so `factual_verdict.line1` + `factual_verdict.line2` always populate.

**Step 5:** Run → pass. Re-run 6 probes from A.2.4; verify `scoring_v2.factual_verdict.line1` non-null on all 6.

**Step 6:** Commit `feat(response): restore factual_verdict builder with zero GPT cost (1b § 1b)`.

**blockedBy:** A.2.4 (need confirmation the builder is genuinely missing, not just gated by a flag).

### Task A.3.3: Patch 1c price-pipeline root cause — implementation TBD by A.2.4

**File:** depends on root cause from A.2.4.

**Step 1:** Write failing test `tests/test_price_pipeline_real_prices.py` parameterized over 6 categories — asserts no product hits `source_method="estimated"` for mainstream queries that should hit Tier 1 Serper Shopping.

**Step 2:** Run → FAIL (matches probe evidence).

**Step 3:** Patch ONLY the root cause identified in A.2.4. Candidates per design § 1c:
- Serper Shopping regional gap → adjust regional query expansion in `price_service.py`.
- `api_budget_service` reporting exhausted Firecrawl credits → top-up is operational not code (design § 9 explicitly defers).
- Circuit breakers tripped → reset breaker state via env or admin endpoint.
- `_validate_price_query` rejecting queries → loosen validation, add test for the rejected pattern.
- `_extract_price_from_html` parser regression → fix parser, add regression test for the failed snippet.

**Step 4:** Run probes → real prices land for ≥5 of 6 mainstream queries.

**Step 5:** Commit `fix(price): root-cause patch for fallback-to-estimated regression (1c — <root cause from A.2.4>)`.

**Evidence required:** A.2.4 evidence + 5/6 probes green.

**blockedBy:** A.2.4.

---

## A.4 — Calibration philosophy + missing-data handling (§ 2)

### Task A.4.1: Kill the missing-data floor of 30 (§ 2a)

**File:** `app/services/scoring_service.py` — `_compute_raw_scores` + `_normalize_*` family.

**Step 1:** Write failing test `tests/test_scoring_missing_propagates_none.py`:

```python
def test_missing_signal_propagates_as_none_not_floor():
    # Product with no performance signal at all
    product = {"name": "X", "specs": {}, "rating": None, "price": None}
    raw_scores = _compute_raw_scores(product, category="electronics")
    assert raw_scores["performance"] is None  # NOT 30, NOT 50, NOT a number
    assert raw_scores["build_quality"] is None
    # Price/Reviews dims may still emit if comparison-level signal exists; per-product missing → None

def test_no_missing_score_constant_left_in_scoring_module():
    import inspect
    from app.services import scoring_service
    src = inspect.getsource(scoring_service)
    # MISSING_SCORE=50 should be removed; any remaining 30-floor injection should be flagged
    assert "MISSING_SCORE" not in src or "# removed" in src.lower()
```

**Step 2:** Run → FAIL.

**Step 3:** Remove `MISSING_SCORE=50` constant + the call sites that inject it when a signal is missing. Replace with `None` propagation. `build_dimensions_v2` (A.7) silently omits dims where either side is `None`.

**Step 4:** Run all `tests/test_scoring*.py` → no regressions.

**Step 5:** Commit `fix(scoring): missing signals propagate None, not phantom 30-floor (§ 2a)`.

**blockedBy:** none.

### Task A.4.2: Eliminate fabricated defaults (§ 2g)

**File:** `app/services/scoring_service.py` — full audit pass.

**Step 1:** Write failing test `tests/test_scoring_no_fabricated_defaults.py`:

```python
def test_dim_value_does_not_fabricate_4_0_rating():
    a = {"price": {"amount": 100}, "rating": None}  # no rating → must NOT default to 4.0
    b = {"price": {"amount": 200}, "rating": {"score": 4.2}}
    result = _dim_value(a, b, category="electronics")
    # Missing rating on side A means value dim cannot be computed for that side
    assert result["score_a"] is None

def test_no_or_4_0_pattern_in_scoring():
    import re, inspect
    from app.services import scoring_service
    src = inspect.getsource(scoring_service)
    # Audit for `or 4.0`, `or 0.1`, `or 1` patterns that silently fabricate defaults
    forbidden = [r"\bor 4\.0\b", r"\bor 0\.1\b", r"\bor 1\b\s*[,\)]"]
    for pattern in forbidden:
        matches = re.findall(pattern, src)
        assert not matches, f"Fabricated default found: {pattern} → {matches}"
```

**Step 2:** Run → FAIL.

**Step 3:** Audit + remove every `or <number>` silent default in `scoring_service.py` (`ra = a.get("rating") or 4.0` at line 1247 is the headline; sweep for `price or 0.1`, `warranty or 1`, etc.). Replace with explicit `None` propagation; dim emits `null` instead. Every fallback becomes explicit (Tier 3 inference at extraction layer per § 2f) or the dim drops.

**Step 4:** Run all `tests/test_scoring*.py` + new test → green.

**Step 5:** Commit `fix(scoring): eliminate fabricated defaults — None propagates instead of phantom values (§ 2g)`.

**blockedBy:** A.4.1.

### Task A.4.3: Calibration band `[60, 95]` for populated signals (§ 2c)

**File:** `app/services/scoring_service.py` — `calibrate_score`.

**Step 1:** Write failing test `tests/test_calibrate_band.py`:

```python
def test_populated_signal_falls_inside_60_95_band():
    for raw in range(40, 101, 5):
        cal = calibrate_score(raw, has_signal=True)
        assert 60 <= cal <= 95, f"raw={raw} → cal={cal} outside [60,95]"

def test_honesty_guard_low_raw_caps_at_69():
    # Per design § 2c: raw_signals < 40 → display ≤ 69
    cal = calibrate_score(35, has_signal=True)
    assert cal <= 69

def test_missing_signal_returns_none_not_60():
    cal = calibrate_score(None, has_signal=False)
    assert cal is None
```

**Step 2:** Run → FAIL or regression on existing tests.

**Step 3:** Verify current `calibrate_score` formula keeps floor=60, ceiling=95. Add explicit `if not has_signal: return None` short-circuit. Add the `raw_signals < 40 → cap ≤ 69` honesty guard if not already present.

**Step 4:** Run → green.

**Step 5:** Commit `feat(scoring): explicit [60,95] band + honesty guard + None passthrough (§ 2c)`.

**blockedBy:** A.4.1.

### Task A.4.4: Backend contract for "Insufficient data" row (§ 2b)

**File:** `app/services/scoring_service.py` + `app/services/response_builder.py`.

> **Scope clarifier (per teammate brief):** Frontend renders the "—" row. Backend contract: emit `score_a=null` / `score_b=null` cleanly with no provenance copy that would leak to UI.

**Step 1:** Write failing test `tests/test_dimensions_null_score_contract.py`:

```python
def test_dim_emits_null_scores_without_provenance_copy():
    # Scenario: BOTH products lack the underlying signal AND single-dim scenario forces emission
    dims = build_dimensions_v2(scoring_result_with_single_missing_dim, category="electronics")
    last_resort = [d for d in dims if d.get("score_a") is None and d.get("score_b") is None]
    assert len(last_resort) <= 1
    if last_resort:
        d = last_resort[0]
        # MUST emit null scores, MUST NOT emit "estimated" / "reference" / "limited data" string from backend
        assert d["score_a"] is None
        assert d["score_b"] is None
        # Backend can emit a category-key caption hint, but never the forbidden words
        assert "estimated" not in (d.get("caption_key") or "").lower()
        assert "reference price" not in (d.get("caption_key") or "").lower()
```

**Step 2:** Run → FAIL.

**Step 3:** In `build_dimensions_v2`, add the last-resort path: when single-dim scenario AND both sides missing, emit `{"dim_key": ..., "score_a": null, "score_b": null, "caption_key": "limited_data"}`. The frontend reads `caption_key`. No banner.

**Step 4:** Verify NO forbidden user-facing strings (`estimated`, `reference price`, `couldn't`, etc.) leak from backend.

**Step 5:** Commit `feat(scoring): null-score dim contract for last-resort cases (§ 2b backend)`.

**blockedBy:** A.4.1, A.4.3.

### Task A.4.5: `comparison_quality` detector — verdict-text only, NO banner (§ 2e)

**File:** `app/services/structured_comparison_service.py` + `app/services/extraction_service.py`.

**Step 1:** Write failing test `tests/test_comparison_quality_detector.py`:

```python
def test_normal_comparison():
    products = [{"name": "iPhone 16", "category": "electronics"}, {"name": "Galaxy S25", "category": "electronics"}]
    assert detect_comparison_quality(products) == "normal"

def test_weak_when_50_percent_specs_missing_after_fallback():
    products = [
        {"name": "X", "category": "electronics", "specs": {"battery": "4000mAh"}},  # 1 of 8 expected
        {"name": "Y", "category": "electronics", "specs": {"battery": "5000mAh", "processor": "A18"}},
    ]
    assert detect_comparison_quality(products, post_fallback=True) == "weak"

def test_weird_when_categories_mismatch():
    products = [{"category": "electronics"}, {"category": "skincare"}]
    assert detect_comparison_quality(products) == "weird"

def test_weird_when_10x_price_gap():
    products = [{"price": {"amount": 5.0}}, {"price": {"amount": 350.0}}]
    assert detect_comparison_quality(products) == "weird"

def test_response_field_present_no_banner_emitted():
    response = build_comparison_response(...)
    assert response["comparison_quality"] in ("normal", "weak", "weird")
    # NO banner trigger, NO top-level UI flag, just the response field
    assert "banner" not in response
    assert "warning" not in response.get("metadata", {})
```

**Step 2:** Run → FAIL.

**Step 3:** Implement `detect_comparison_quality(products, post_fallback=False)` per design § 2e triggers:
- Cross-category (`category_used` mismatch) → `weird`.
- After 3-tier fallback, >50% of one product's spec slots empty → `weird`.
- Price spread ≥ 10× order of magnitude → `weird`.
- Otherwise → `normal` or `weak` based on softer thresholds.

Emit `response.comparison_quality` from `response_builder.build_comparison_response()`.

**Step 4:** In `_build_preferences_prompt` (`extraction_service.py:870+`), when `comparison_quality == "weird"`, append instruction:

> "When comparison_quality is 'weird', do NOT force a winner. Rewrite winner_declaration to acknowledge the products serve different purposes; rewrite winner_reason to help the user decide between the options shown. Do not use info-banner phrasing — write natural sentences. Forbidden words: estimated, reference price, couldn't, try again, Failed to, تعذر, فشل."

**Step 5:** When `weird`, hero overall score suppressed at the response_builder level: `response.scoring_v2.overall_score_suppressed = true`. Frontend reads this flag and renders `—`.

**Step 6:** Commit `feat(comparison): comparison_quality detector + verdict-prompt weird flag (§ 2e)`.

**blockedBy:** A.4.1.

### Task A.4.6: 3-tier spec fallback — split CRITICAL_SCHEMA_FIELDS (§ 2f Step 1)

**File:** `app/services/extraction_service.py:180` — `CRITICAL_SCHEMA_FIELDS`.

**Step 1:** Write failing test `tests/test_critical_schema_fields_split.py`:

```python
from app.services.extraction_service import CRITICAL_SCHEMA_FIELDS_NON_NEGOTIABLE, CRITICAL_SCHEMA_FIELDS_PREFERRED

def test_electronics_non_negotiable_has_4_fields():
    assert set(CRITICAL_SCHEMA_FIELDS_NON_NEGOTIABLE["electronics"]) == {"battery", "processor", "ram", "rear_camera"}

def test_electronics_preferred_has_4_fields():
    assert set(CRITICAL_SCHEMA_FIELDS_PREFERRED["electronics"]) == {"front_camera", "water_resistance", "os", "weight"}

def test_supplements_split():
    assert set(CRITICAL_SCHEMA_FIELDS_NON_NEGOTIABLE["supplements"]) == {"dosage", "form"}
    assert set(CRITICAL_SCHEMA_FIELDS_PREFERRED["supplements"]) == {"count", "serving_size", "active_ingredient"}

# Repeat for: fragrances, fashion, skincare, haircare, makeup, grocery, other (per design § 2f table)
```

**Step 2:** Run → FAIL.

**Step 3:** Replace existing flat `CRITICAL_SCHEMA_FIELDS` dict with two dicts per design § 2f table (8 categories non-negotiable + preferred + `other` with no non-negotiables).

**Step 4:** Update existing call sites that referenced `CRITICAL_SCHEMA_FIELDS[category]` to use either the non-negotiable or the union, depending on which layer they belong to.

**Step 5:** Commit `feat(extraction): split CRITICAL_SCHEMA_FIELDS into non-negotiable + preferred (§ 2f Step 1)`.

**blockedBy:** none.

### Task A.4.7: Tier 2 fallback — targeted Serper+GPT-mini per missing non-negotiable (§ 2f Step 2)

**File:** `app/services/extraction_service.py` + `app/services/structured_comparison_service.py`.

**Step 1:** Write failing test `tests/test_spec_fallback_tier2.py`:

```python
@pytest.mark.asyncio
async def test_tier2_runs_when_non_negotiable_missing(mock_serper_returns_battery):
    initial_specs = {"processor": "A18"}  # battery, ram, rear_camera missing for electronics
    enriched = await run_tier2_fallback(initial_specs, category="electronics", product_name="iPhone 16")
    assert "battery" in enriched
    # Wall time must be ≤4s (per design § 2f Tier 2 budget)

@pytest.mark.asyncio
async def test_tier2_runs_only_for_non_negotiable_gaps():
    initial = {"battery": "4000mAh", "processor": "A18", "ram": "8GB", "rear_camera": "48MP", "front_camera": None}
    # All non-negotiable present, only preferred missing — Tier 2 should NOT fire
    enriched = await run_tier2_fallback(initial, category="electronics", product_name="iPhone 16")
    assert enriched == initial  # no Serper/GPT calls
```

**Step 2:** Run → FAIL.

**Step 3:** Implement `run_tier2_fallback(initial_specs, category, product_name)`:
- Compute set of still-missing non-negotiable fields.
- For each missing field, issue targeted parallel Serper query `f"{product_name} {field}"` with 0.5s per-field budget.
- Pipe top organic result to GPT-mini extraction prompt (single field at a time, JSON-mode).
- Total wall: 4s with `asyncio.wait_for`. 1 retry per field. Return enriched specs dict.
- Track cost via `self._track_cost()`.

**Step 4:** Wire into orchestration: after Tier 1 in `structured_comparison_service.compare_from_text`, if non-negotiable gaps remain, call Tier 2.

**Step 5:** Run → pass.

**Step 6:** Commit `feat(extraction): Tier 2 targeted Serper+GPT-mini for non-negotiable spec gaps (§ 2f)`.

**blockedBy:** A.4.6.

### Task A.4.8: Tier 3 fallback — GPT-4o knowledge synthesis batched (§ 2f Step 3)

**File:** `app/services/extraction_service.py`.

**Step 1:** Write failing test `tests/test_spec_fallback_tier3.py`:

```python
@pytest.mark.asyncio
async def test_tier3_batched_single_call(mock_openai_4o):
    gaps = {"product_0": ["battery", "ram"], "product_1": ["rear_camera"]}
    enriched = await run_tier3_fallback(gaps, products=[...], category="electronics")
    assert mock_openai_4o.call_count == 1, "Tier 3 must be a single batched call across ALL gaps"
    assert enriched["product_0"]["battery"] is not None
    assert enriched["product_0"]["inference_source"] == "model_knowledge"
    # inference_source MUST NEVER bubble to user-facing response (QA/dashboards only)

@pytest.mark.asyncio
async def test_tier3_inference_source_never_in_user_facing_response():
    # Run full comparison; verify response_builder strips inference_source from products[].specs
    response = await get_comparison_service().compare_from_text(...)
    for p in response["products"]:
        assert "inference_source" not in p["specs"]
        assert "inference_source" not in p
```

**Step 2:** Run → FAIL.

**Step 3:** Implement `run_tier3_fallback(gaps, products, category)`:
- Single batched GPT-4o call with all remaining gap fields across both products.
- Prompt instructs: "Return best-inference values from your knowledge. Do not invent SKUs. Mark each field with `inference_source: 'model_knowledge'`."
- 3s wall via `asyncio.wait_for`.
- Returns enriched per-product specs with internal `inference_source` flag.

**Step 4:** In `response_builder.build_comparison_response`, strip `inference_source` from `products[].specs` before emission (QA/dashboards only per design § 2f).

**Step 5:** Verify total budget Tier 1 + Tier 2 + Tier 3 stays inside `STREAM_HARD_CAP_SECONDS=25` (existing outer cap covers this; Tier 2 = 4s, Tier 3 = 3s fire in parallel-after-Phase-1 window).

**Step 6:** Commit `feat(extraction): Tier 3 GPT-4o knowledge synthesis batched fallback (§ 2f, inference_source stripped from API)`.

**blockedBy:** A.4.7.

### Task A.4.9: Silent omission of dims with truly-missing data (§ 2h)

**File:** `app/services/scoring_service.py` — `build_dimensions_v2`.

**Step 1:** Write failing test `tests/test_dim_silent_omission.py`:

```python
def test_dim_silently_omitted_when_both_sides_null():
    scores = {
        "product_0": {"price": 75, "reviews": 80, "performance": None},
        "product_1": {"price": 82, "reviews": 78, "performance": None},
    }
    dims = build_dimensions_v2(scores, category="electronics")
    dim_keys = {d["dim_key"] for d in dims}
    assert "performance" not in dim_keys  # omitted entirely, NO "—" row

def test_response_products_specs_has_no_null_fields_after_omission():
    # Per § 2h: field omitted from response.products[].specs entirely
    response = build_comparison_response(products_with_post_fallback_missing_specs)
    for p in response["products"]:
        assert None not in p["specs"].values()
        assert "null" not in str(p["specs"])
```

**Step 2:** Run → FAIL.

**Step 3:** In `build_dimensions_v2`, skip emission entirely when both `score_a` and `score_b` are `None` (unless it's the rare last-resort case from A.4.4 — which requires the single-dim flag).

In `response_builder`, sanitize `products[].specs` to drop keys with `None` values before emission.

**Step 4:** Run all dim-emission + spec tests → green.

**Step 5:** Commit `feat(scoring): silent omission of dims + specs with null values (§ 2h)`.

**blockedBy:** A.4.1, A.4.2, A.4.4.

### Task A.4.10: Legal disclosure clause in terms_of_service.md + Arabic + privacy_policy.md (§ 2i)

**Files:**
- `app/legal/terms_of_service.md`
- `app/legal/terms_of_service_ar.md` (or equivalent — verify filename via Glob first)
- `app/legal/privacy_policy.md` + Arabic if it has a data-quality section

**Step 1:** Glob `app/legal/*.md` to confirm filenames.

**Step 2:** Append clause to English ToS (exact text per design § 2i):

> "AI extraction is approximate. Specifications, prices, and ratings may contain inaccuracies. Always verify critical details with the retailer before purchase."

**Step 3:** Append Arabic translation (Ahmed reviews translation if uncertain — tag pre-existing translated section style):

> "استخراج البيانات بالذكاء الاصطناعي تقريبي. قد تحتوي المواصفات والأسعار والتقييمات على بعض الأخطاء. يرجى التحقق من التفاصيل المهمة مع المتجر قبل الشراء."

**Step 4:** If `privacy_policy.md` has a data-quality / accuracy section, append the same clause. Otherwise skip (per design § 2i: "if one exists").

**Step 5:** Verify clause text is rendered via `/api/v1/legal/*` endpoint (existing route serves markdown files live).

**Step 6:** Commit `legal: AI extraction disclosure clause in ToS + Privacy (EN+AR) (§ 2i)`.

**blockedBy:** none.

---

## A.5 — Budget tier expansion (§ 3)

### Task A.5.1: `PRICE_TIERS_BY_CATEGORY` dict (§ 3b + 3e)

**File:** `app/services/scoring_service.py`.

**Step 1:** Write failing test `tests/test_price_tiers_by_category.py`:

```python
from app.services.scoring_service import PRICE_TIERS_BY_CATEGORY, _detect_price_tier

def test_electronics_tiers():
    assert _detect_price_tier(50, "electronics") == "budget"
    assert _detect_price_tier(300, "electronics") == "mid"
    assert _detect_price_tier(600, "electronics") == "premium"
    assert _detect_price_tier(1500, "electronics") == "luxury"
    assert _detect_price_tier(2500, "electronics") == "top_tier"

def test_supplements_tiers_fold_top_tier_into_luxury():
    # Per design § 3e: supplements top_tier folds into luxury
    assert _detect_price_tier(8, "supplements") == "budget"
    assert _detect_price_tier(20, "supplements") == "mid"
    assert _detect_price_tier(45, "supplements") == "premium"
    assert _detect_price_tier(80, "supplements") == "luxury"
    assert _detect_price_tier(500, "supplements") == "luxury"  # top_tier folded

def test_fashion_fragrances_skincare_haircare_makeup_grocery_tiers():
    # Verify each category's breakpoints per design § 3e table
    ...
```

**Step 2:** Run → FAIL.

**Step 3:** Replace existing flat `PRICE_TIERS` with `PRICE_TIERS_BY_CATEGORY` dict per design § 3e table:

```python
PRICE_TIERS_BY_CATEGORY = {
    "electronics": [(100, "budget"), (400, "mid"), (800, "premium"), (2000, "luxury"), (float("inf"), "top_tier")],
    "supplements": [(11, "budget"), (30, "mid"), (60, "premium"), (float("inf"), "luxury")],  # top_tier folded
    # ...all 8 categories per design § 3e
}
```

Implement `_detect_price_tier(price, category, *, comparison_prices=None)` walking the per-category list.

**Step 4:** Run → pass.

**Step 5:** Commit `feat(scoring): PRICE_TIERS_BY_CATEGORY per-category tier breakpoints (§ 3b + 3e)`.

**blockedBy:** none.

### Task A.5.2: `TIER_EXPECTATIONS` extension (§ 3b)

**File:** `app/services/scoring_service.py`.

**Step 1:** Write failing test asserting:

```python
def test_tier_expectations_5_tiers():
    assert TIER_EXPECTATIONS["budget"] == 0.60
    assert TIER_EXPECTATIONS["mid"] == 0.70
    assert TIER_EXPECTATIONS["premium"] == 0.80
    assert TIER_EXPECTATIONS["luxury"] == 0.88  # was 0.85
    assert TIER_EXPECTATIONS["top_tier"] == 0.90
```

**Step 2:** Run → FAIL.

**Step 3:** Update `TIER_EXPECTATIONS` per design § 3b: re-split today's `luxury=0.85` into `luxury=0.88` + `top_tier=0.90`.

**Step 4:** Run → pass.

**Step 5:** Commit `feat(scoring): TIER_EXPECTATIONS extends to 5 tiers (§ 3b)`.

**blockedBy:** none.

### Task A.5.3: `CATEGORY_BUDGET_ADJUSTMENTS` extension (§ 3b)

**File:** `app/services/scoring_service.py`.

**Step 1:** Write failing test asserting that for each category, both `luxury` and `top_tier` entries exist; `top_tier` adds +0.05 to the category's headline spec dim (e.g., `craft_score` for fashion, `performance_score` for electronics).

**Step 2:** Run → FAIL.

**Step 3:** Extend `CATEGORY_BUDGET_ADJUSTMENTS` per design § 3b: `luxury` mirrors `premium` with slightly steeper spec emphasis; `top_tier` adds +0.05 to headline spec dim.

**Step 4:** Run → pass.

**Step 5:** Commit `feat(scoring): CATEGORY_BUDGET_ADJUSTMENTS for luxury + top_tier (§ 3b)`.

**blockedBy:** A.5.2.

### Task A.5.4: Pydantic `BudgetValue` Literal extension (§ 3b)

**File:** wherever `BudgetValue` is defined (likely `app/services/cohort_service.py` or `app/api/auth_routes.py` Pydantic models). Glob first.

**Step 1:** Write failing test `tests/test_budget_value_literal.py`:

```python
def test_budget_value_accepts_5_tiers():
    from app.api.auth_routes import PreferencesBody  # or wherever BudgetValue lives
    body = PreferencesBody(budget="top_tier")
    assert body.budget == "top_tier"
    body = PreferencesBody(budget="luxury")
    assert body.budget == "luxury"

def test_budget_value_still_accepts_legacy_3_tier():
    # Per design § 3d backwards-compat
    body = PreferencesBody(budget="premium")
    assert body.budget == "premium"

def test_budget_value_rejects_unknown():
    with pytest.raises(ValidationError):
        PreferencesBody(budget="ultra_mega")
```

**Step 2:** Run → FAIL.

**Step 3:** Extend `BudgetValue = Literal['budget', 'mid', 'premium', 'luxury', 'top_tier']`.

**Step 4:** Run → pass.

**Step 5:** Commit `feat(auth): BudgetValue Literal extends to 5 tiers, backwards-compat (§ 3b)`.

**blockedBy:** A.1.1 (migration applied first to ensure CHECK constraint matches).

### Task A.5.5: `other` runtime sub-scale detection — geometric mean (§ 3f)

**File:** `app/services/scoring_service.py`.

**Step 1:** Write failing test `tests/test_other_sub_scale.py`:

```python
import math
from app.services.scoring_service import _detect_price_tier

def test_other_light_sub_scale():
    # gm < 30
    prices = [5.0, 15.0]
    assert _detect_price_tier(5.0, "other", comparison_prices=prices) == "budget"
    assert _detect_price_tier(15.0, "other", comparison_prices=prices) == "mid"

def test_other_ultra_for_cars():
    # Cars: ~5000 + 8000 BHD → gm=6324 → other_ultra
    prices = [5000.0, 8000.0]
    assert _detect_price_tier(5000.0, "other", comparison_prices=prices) == "budget"
    assert _detect_price_tier(8000.0, "other", comparison_prices=prices) == "budget"
    # Top-tier in other_ultra means 100,000+
    assert _detect_price_tier(120000.0, "other", comparison_prices=prices) == "top_tier"

def test_other_falls_back_to_other_light_without_comparison_prices():
    assert _detect_price_tier(5.0, "other") == "budget"
    assert _detect_price_tier(60.0, "other") == "mid"
```

**Step 2:** Run → FAIL.

**Step 3:** Extend `_detect_price_tier(price, category, *, comparison_prices=None)` to handle `category=="other"`: compute `gm = sqrt(p1 * p2)`, pick sub-scale per design § 3f table (`other_light` / `other_mid` / `other_high` / `other_ultra`), then apply that sub-scale's breakpoints. When `comparison_prices` not provided, fall back to `other_light`.

**Step 4:** Run → pass.

**Step 5:** Commit `feat(scoring): geometric-mean sub-scale detection for 'other' category (§ 3f)`.

**blockedBy:** A.5.1.

---

## A.6 — Value math (§ 4)

### Task A.6.1: `VALUE_FORMULA_BY_PRIORITY` dict + dynamic value coefficients (§ 4a)

**File:** `app/services/scoring_service.py`.

**Step 1:** Write failing test `tests/test_value_formula_by_priority.py`:

```python
from app.services.scoring_service import VALUE_FORMULA_BY_PRIORITY, _compute_value_score

def test_price_priority_uses_60_40_split():
    score = _compute_value_score(
        spec_score=80, price_score=90,
        preferences={"priorities": ["price"]}
    )
    assert score == pytest.approx(80 * 0.40 + 90 * 0.60)

def test_quality_priority_uses_70_30_split():
    score = _compute_value_score(
        spec_score=80, price_score=90,
        preferences={"priorities": ["quality"]}
    )
    assert score == pytest.approx(80 * 0.70 + 90 * 0.30)

def test_default_60_40_when_no_priority():
    score = _compute_value_score(spec_score=80, price_score=90, preferences={})
    assert score == pytest.approx(80 * 0.60 + 90 * 0.40)

def test_first_match_wins_when_multiple_priorities():
    score = _compute_value_score(
        spec_score=80, price_score=90,
        preferences={"priorities": ["quality", "price"]}
    )
    # "quality" first → 0.70/0.30
    assert score == pytest.approx(80 * 0.70 + 90 * 0.30)
```

**Step 2:** Run → FAIL.

**Step 3:** Replace constant `0.6 spec + 0.4 price` in `_compute_value_score` with dict-driven coefficients per design § 4a:

```python
VALUE_FORMULA_BY_PRIORITY = {
    "price": (0.40, 0.60),
    "quality": (0.70, 0.30),
    "durability": (0.65, 0.35),
    "latest_features": (0.65, 0.35),
    "brand_reputation": (0.65, 0.35),
    "eco_friendly": (0.55, 0.45),
    "ease_of_use": (0.55, 0.45),
}
DEFAULT_VALUE_FORMULA = (0.60, 0.40)
```

First-match-wins from `preferences.get("priorities", [])`. Cross-tier path keeps `TIER_EXPECTATIONS` formula but `delivery * 0.8` becomes `0.9` for `price` priority and `0.7` for `quality` priority.

**Step 4:** Run → pass.

**Step 5:** Commit `feat(scoring): dynamic value coefficients by user priority (§ 4a)`.

**blockedBy:** A.4.2.

### Task A.6.2: Richer `delta_text` strings (§ 4b)

**File:** `app/services/response_builder.py` or `app/services/scoring_service.py` (verify which builds delta_text).

**Step 1:** Write failing test `tests/test_delta_text_richer_strings.py`:

```python
def test_price_delta_renders_percent_less():
    a = {"price": {"amount": 100}}
    b = {"price": {"amount": 60}}
    delta = _compute_delta_text(a, b, dim="price", winner_index=1)
    assert "40% less" in delta or "40 percent less" in delta.lower()

def test_reviews_delta_unchanged():
    a = {"rating": {"score": 4.5}}
    b = {"rating": {"score": 3.6}}
    delta = _compute_delta_text(a, b, dim="reviews", winner_index=0)
    assert "0.9 stars higher" in delta

def test_value_delta_with_matched_priority():
    delta = _compute_delta_text(a, b, dim="value", winner_index=0, priority_matched=True)
    assert delta == "Better value for your priority"

def test_value_delta_without_priority_match():
    delta = _compute_delta_text(a, b, dim="value", winner_index=0, priority_matched=False)
    assert delta == "Stronger value ratio"

def test_no_estimated_word_in_delta_text():
    # Per design § 0 rule 3
    a_estimated = {"price": {"amount": 100, "source_method": "estimated"}}
    b = {"price": {"amount": 60}}
    delta = _compute_delta_text(a_estimated, b, dim="price", winner_index=1)
    assert "estimated" not in delta.lower()
    assert "reference price" not in delta.lower()
```

**Step 2:** Run → FAIL.

**Step 3:** Update `_compute_delta_text` (locate via Grep) to compute percentage-deltas for price, keep stars-higher for reviews, branch value-string on `priority_matched` flag. Audit for forbidden user-facing words.

**Step 4:** Run → pass.

**Step 5:** Commit `feat(response): richer delta_text strings with % less, priority-aware value (§ 4b)`.

**blockedBy:** A.6.1.

### Task A.6.3: Cross-tier value framing (§ 4c)

**File:** `app/services/scoring_service.py` + `app/services/response_builder.py`.

**Step 1:** Write failing test `tests/test_cross_tier_value_framing.py`:

```python
def test_cross_tier_value_caption_muted_no_winner():
    products = [
        {"price": {"amount": 5}, "rating": {"score": 4.5}},   # budget tier
        {"price": {"amount": 50}, "rating": {"score": 4.7}},  # premium tier
    ]
    response = build_comparison_response(products, category="skincare", ...)
    value_dim = next(d for d in response["scoring_v2"]["dimensions"] if d["dim_key"] == "value")
    # Cross-tier — both muted, no emerald winner
    assert value_dim.get("winner_index") is None or value_dim.get("muted") is True
    assert "Different tier — held to higher bar" in value_dim.get("delta_text", "")
```

**Step 2:** Run → FAIL.

**Step 3:** When `_detect_price_tier(p0) != _detect_price_tier(p1)` (`is_cross_tier=True`), set value-row `delta_text = "Different tier — held to higher bar"`, set `winner_index = None` (no emerald). Both products muted.

**Step 4:** Run → pass.

**Step 5:** Commit `feat(scoring): cross-tier value framing — muted, no winner (§ 4c)`.

**blockedBy:** A.5.5, A.6.2.

### Task A.6.4: `value_match` per-product field (§ 4d)

**File:** `app/services/scoring_service.py` + `app/services/response_builder.py`.

**Step 1:** Write failing test `tests/test_value_match.py`:

```python
def test_value_match_in_range():
    # User picked "mid"; product's detected tier is "mid"
    response = build_comparison_response(products, category="skincare",
                                          user_preferences={"budget": "mid"})
    assert response["products"][0]["value_match"] == "in_range"

def test_value_match_above_range_one_tier():
    response = build_comparison_response(products, category="skincare",
                                          user_preferences={"budget": "mid"})  # product is "premium"
    assert response["products"][0]["value_match"] == "above_range"

def test_value_match_below_range():
    response = build_comparison_response(products, category="skincare",
                                          user_preferences={"budget": "premium"})  # product is "mid"
    assert response["products"][0]["value_match"] == "below_range"

def test_value_match_two_plus_tiers_off_includes_key_tradeoff():
    # Per design § 4d: 2+ tiers off → caption + key_tradeoff snippet
    response = build_comparison_response(products, category="electronics",
                                          user_preferences={"budget": "budget"})  # product is "luxury"
    assert response["products"][0]["value_match"] == "above_range"
    assert response["products"][0].get("value_match_explanation") is not None  # carries key_tradeoff snippet
```

**Step 2:** Run → FAIL.

**Step 3:** Compute `value_match` per product: compare detected tier (via `_detect_price_tier`) vs `preferences.budget`. Tier ladder index distance: 0=`in_range`, +1=`above_range`, -1=`below_range`, ≥2=`above_range` + `value_match_explanation` carrying `key_tradeoff` snippet.

Emit `response.products[].value_match` + optional `value_match_explanation`. Frontend renders captions (no backend caption text — frontend reads i18n key).

**Step 4:** Run → pass.

**Step 5:** Commit `feat(scoring): value_match per-product field with above/below/in range (§ 4d)`.

**blockedBy:** A.5.5.

### Task A.6.5: Tier-mismatch handling — `budget_mismatch` to verdict prompt (§ 4e)

**File:** `app/services/scoring_service.py` + `app/services/extraction_service.py` + `app/services/response_builder.py`.

**Step 1:** Write failing test `tests/test_budget_mismatch_to_verdict.py`:

```python
def test_both_above_user_tier_sets_budget_mismatch_above():
    # User picked top_tier, comparing entry-level cars
    response = build_comparison_response(low_priced_cars, category="other",
                                          user_preferences={"budget": "top_tier"})
    assert response["metadata"]["budget_mismatch"] == "below"  # products are below user's stated tier

def test_both_below_user_tier_sets_budget_mismatch_below():
    response = build_comparison_response(cheap_supplements, category="supplements",
                                          user_preferences={"budget": "luxury"})
    assert response["metadata"]["budget_mismatch"] == "below"

def test_match_sets_budget_mismatch_null():
    response = build_comparison_response(matched_products, category="electronics",
                                          user_preferences={"budget": "mid"})
    assert response["metadata"]["budget_mismatch"] is None

def test_budget_mismatch_passes_to_verdict_prompt():
    prompt = _build_preferences_prompt(
        explicit_prefs={"budget": "top_tier"}, behavioral={}, demographics_profile=None,
        budget_mismatch="below"
    )
    assert "budget_mismatch" in prompt or "below your usual range" in prompt.lower()
    # Instruction added per § 4e
    assert "acknowledge naturally" in prompt or "outside the user's usual range" in prompt
```

**Step 2:** Run → FAIL.

**Step 3:** Compute `budget_mismatch: "above" | "below" | None` at response_builder level:
- Both products' detected tiers above user's stated tier → `"above"`.
- Both products' detected tiers below user's stated tier → `"below"`.
- Otherwise → `None`.

Pass `budget_mismatch` into `_build_preferences_prompt` and append instruction per design § 4e:

> "When `budget_mismatch` is set ('above' or 'below'), acknowledge naturally in `best_for` / `value_context` that products are outside the user's usual range, but still help them decide between the options shown. Do not use info-banner phrasing. Forbidden words: estimated, reference price, banner, warning."

**Step 4:** Math: `CATEGORY_BUDGET_ADJUSTMENTS` weights stay active per design § 4e Case 2. Cheaper product gets value lift naturally via math when both below user's tier (e.g., car example).

**Step 5:** Per design § 4e: NO UI banner. Backend emits metadata field only.

**Step 6:** Run → pass.

**Step 7:** Commit `feat(scoring+extraction): budget_mismatch metadata + verdict prompt instruction (§ 4e)`.

**blockedBy:** A.5.5, A.6.4, A.4.5.

---

## A.7 — Confidence widget (§ 5)

### Task A.7.1: Loosen confidence thresholds (§ 5a)

**File:** `app/services/scoring_service.py` — `compute_confidence`.

**Step 1:** Write failing test `tests/test_confidence_thresholds_loosened.py`:

```python
def test_rating_strong_drops_verified_requirement():
    # review_count >= 100 alone qualifies, even if rating_verified=False
    legs = compute_confidence(
        rating={"count": 1200, "verified": False},
        price={"source_method": "page_scrape"},
        specs={"verified_pct": 50}
    )
    assert legs["rating_strength"] == "strong"

def test_price_strong_when_one_product_has_real_source():
    # Per § 5a: drop "method != estimated" blocker IF at least one product's source_method in trusted set
    legs = compute_confidence(
        price={"source_methods": ["estimated", "firecrawl"]},
        ...
    )
    assert legs["price_strength"] == "strong"

def test_price_strong_when_shopping_count_3_plus():
    legs = compute_confidence(
        price={"source_methods": ["estimated", "estimated"], "shopping_count": 4},
        ...
    )
    assert legs["price_strength"] == "strong"

def test_specs_strong_with_citation_count_8_plus():
    # Per § 5a: specs_strong when verified_pct >= 40 OR citation_count >= 8
    legs = compute_confidence(
        specs={"verified_pct": 35, "citation_count": 9},
        ...
    )
    assert legs["specs_strength"] == "strong"

def test_overall_threshold_unchanged():
    # 3 strong = high, 2 = medium, ≤1 = low
    legs = compute_confidence(rating={"count": 1200}, price={"shopping_count": 4},
                              specs={"verified_pct": 50})
    assert legs["overall"] == "high"
```

**Step 2:** Run → FAIL.

**Step 3:** Update `compute_confidence` per design § 5a:
- `rating_strong`: drop `verified=True`. New rule: `review_count >= 100`.
- `price_strong`: drop `method != "estimated"` blocker IF at least one product's `source_method` in `{official_brand, page_scrape, firecrawl, scrapedo_rendered, local_bhd}` OR `shopping_count >= 3`.
- `specs_strong`: lower `verified_pct >= 60` to `verified_pct >= 40` OR `citation_count >= 8`.
- Overall threshold unchanged.

**Step 4:** Run → pass.

**Step 5:** Commit `feat(scoring): loosen confidence thresholds per § 5a`.

**blockedBy:** A.4.1.

### Task A.7.2: Backend contract for price-pill silent fallback (§ 5c)

**File:** `app/services/scoring_service.py` + `app/services/response_builder.py`.

> **Scope clarifier:** Frontend hides the Price pill when any product has `source_method == "estimated"`. Backend's job is to ensure NO provenance copy leaks from backend strings.

**Step 1:** Write failing test `tests/test_price_pill_no_provenance_leak.py`:

```python
def test_no_provenance_string_in_response_when_estimated():
    products = [
        {"price": {"amount": 100, "source_method": "estimated"}, ...},
        {"price": {"amount": 60, "source_method": "firecrawl"}, ...},
    ]
    response = build_comparison_response(products, ...)
    # Audit every user-facing string for forbidden words
    response_str = json.dumps(response)
    assert "estimated" not in response_str.lower() or _only_in_enum_field(response, "estimated")
    assert "reference price" not in response_str.lower()
    assert "approximate" not in response_str.lower()  # except in legal disclosure which isn't in API response

def _only_in_enum_field(response, word):
    # Helper: word may appear only as enum value of source_method, never in display strings
    ...
```

**Step 2:** Run → FAIL.

**Step 3:** Audit `response_builder` + `scoring_service` for any string template that conditionally includes "estimated" / "reference price" / "approximate" / "limited data" in user-facing fields (delta_text, verdict_text, dim captions). Replace with silent omission OR i18n-key references the frontend resolves.

**Step 4:** Verify `source_method="estimated"` enum stays in `products[].price.source_method` for QA/dashboards (per design § 0 rule 3). Frontend reads this enum to decide pill visibility.

**Step 5:** Run → pass.

**Step 6:** Commit `fix(response): audit + remove backend provenance copy leaks (§ 5c backend)`.

**blockedBy:** A.6.2.

---

## A.8 — DimensionBars backend contract (§ 6)

### Task A.8.1: `build_dimensions_v2` thin adapter sourced from `CATEGORY_DIMENSIONS` (§ 6a)

**File:** `app/services/scoring_service.py`.

**Step 1:** Write failing test `tests/test_build_dimensions_v2_thin_adapter.py`:

```python
def test_dimensions_v2_emits_3_cross_category_core_first():
    dims = build_dimensions_v2(scores, category="electronics")
    first_three_keys = [d["dim_key"] for d in dims[:3]]
    assert set(first_three_keys) == {"price", "reviews", "value"}

def test_dimensions_v2_then_up_to_3_category_specific():
    dims = build_dimensions_v2(scores_with_all_signals, category="electronics")
    category_specific = [d["dim_key"] for d in dims[3:]]
    assert len(category_specific) <= 3
    # Per CATEGORY_DIMENSIONS["electronics"]: performance, build_quality, future_proofing
    assert set(category_specific).issubset({"performance", "build_quality", "future_proofing"})

def test_no_hand_coded_dim_builders_remain():
    import inspect
    from app.services import scoring_service
    src = inspect.getsource(scoring_service)
    # Per § 6a: drop _dim_dpi / _dim_popularity / _dim_build_quality builders
    assert "_dim_dpi" not in src or "# removed" in src.lower()
    assert "_dim_popularity" not in src or "# removed" in src.lower()

def test_skips_dim_when_either_side_null():
    scores_with_gap = {"product_0": {"performance": None, "price": 80}, "product_1": {"performance": 85, "price": 70}}
    dims = build_dimensions_v2(scores_with_gap, category="electronics")
    dim_keys = {d["dim_key"] for d in dims}
    assert "performance" not in dim_keys  # silently omitted
```

**Step 2:** Run → FAIL.

**Step 3:** Replace `build_dimensions_v2` with thin adapter:
- For each dim in `CATEGORY_DIMENSIONS[category]`, emit a `dimensions[]` entry ONLY if BOTH products have non-null score.
- Order: 3 cross-category core dims first (Price · Reviews · Value), then up to 3 category-specific dims.
- Drop hand-coded `_dim_dpi`, `_dim_popularity`, `_dim_build_quality` builders.
- Pull dim labels via `DIMENSION_DISPLAY_NAMES` (`scoring_service.py:248`).

**Step 4:** Run all scoring tests → no regressions.

**Step 5:** Commit `refactor(scoring): build_dimensions_v2 thin adapter sourced from CATEGORY_DIMENSIONS (§ 6a)`.

**blockedBy:** A.4.1, A.4.9.

---

## A.9 — Personalization chip backend (§ 7b)

### Task A.9.1: `personalization.applied_shifts[]` qualitative-only contract (§ 7b)

**File:** `app/services/scoring_service.py` (`compute_scores`) + `app/services/response_builder.py`.

**Step 1:** Write failing test `tests/test_applied_shifts.py`:

```python
def test_applied_shifts_emits_top_3_by_magnitude():
    scores_result = compute_scores(
        products=...,
        preferences={"priorities": ["quality", "durability", "latest_features"]},
        category="electronics"
    )
    shifts = scores_result["personalization"]["applied_shifts"]
    assert len(shifts) <= 3
    # All shifts must be qualitative — direction only, no magnitude
    for s in shifts:
        assert s["direction"] in ("up", "down")
        assert "magnitude" not in s
        assert "percent" not in s
        assert "delta" not in s
        assert "coefficient" not in s

def test_applied_shifts_sorted_by_absolute_magnitude():
    # Largest 3 absolute shifts win; sort hidden but order observable
    shifts = scores_result["personalization"]["applied_shifts"]
    # First shift was the largest-magnitude one
    assert shifts[0]["dim_display"] in DIMENSION_DISPLAY_NAMES.values()

def test_applied_shifts_empty_when_no_priorities():
    scores_result = compute_scores(products=..., preferences={}, category="electronics")
    assert scores_result["personalization"]["applied_shifts"] == []

def test_applied_shifts_dim_display_via_dimension_display_names():
    shifts = scores_result["personalization"]["applied_shifts"]
    for s in shifts:
        assert s["dim_display"] in DIMENSION_DISPLAY_NAMES.values()

def test_no_backend_internals_in_applied_shifts():
    # Per design § 0 rule 2 + § 11
    shifts_str = json.dumps(scores_result["personalization"]["applied_shifts"])
    assert "weights_used" not in shifts_str
    assert "CATEGORY_DIMENSION_WEIGHTS" not in shifts_str
    assert "coefficient" not in shifts_str
    assert "cap_percent" not in shifts_str
```

**Step 2:** Run → FAIL.

**Step 3:** In `compute_scores`, after `weights_used` is computed:

```python
applied_shifts = []
defaults = CATEGORY_DIMENSION_WEIGHTS[category]
deltas = [(dim, weights_used[dim] - defaults.get(dim, 0)) for dim in weights_used]
# Sort by absolute magnitude descending; take top 3
deltas.sort(key=lambda x: abs(x[1]), reverse=True)
for dim, delta in deltas[:3]:
    if abs(delta) < 0.001:  # noise floor; chip hides itself if all shifts trivial
        continue
    applied_shifts.append({
        "dim_display": DIMENSION_DISPLAY_NAMES.get(dim, dim),
        "direction": "up" if delta > 0 else "down",
    })
```

Emit at `response.personalization.applied_shifts[]`.

**Step 4:** Verify NO backend internals (`weights_used`, coefficients, magnitudes, cap percents) leak into the response.

**Step 5:** Commit `feat(scoring): personalization.applied_shifts qualitative-only contract (§ 7b)`.

**blockedBy:** A.6.1.

---

## A.10 — Diagnostic cleanup + post-deploy verification (§ 8d-f)

### Task A.10.1: Remove A.2 diagnostic logging gated on `DEBUG_STAGE_TIMINGS=true`

> **Per CLAUDE.md env-var note + project measure-before-optimize rule:** `DEBUG_STAGE_TIMINGS` is opt-in. The diagnostic logs from A.2.1 / A.2.2 / A.2.3 should be flag-gated, not always-on. Verify after capture.

**Step 1:** Audit each diagnostic log added in A.2 (PROS_CONS_DIAGNOSTIC, FACTUAL_VERDICT_DIAGNOSTIC, PRICE_PIPELINE_DIAG). Wrap each in:

```python
if os.getenv("DEBUG_STAGE_TIMINGS", "false").lower() == "true":
    logger.warning(...)
```

If already wrapped, skip.

**Step 2:** Write regression test `tests/test_diagnostics_flag_gated.py`:

```python
def test_pros_cons_diagnostic_silent_when_flag_off(caplog, monkeypatch):
    monkeypatch.setenv("DEBUG_STAGE_TIMINGS", "false")
    # Run scenario that previously triggered PROS_CONS_DIAGNOSTIC
    ...
    assert "PROS_CONS_DIAGNOSTIC" not in caplog.text
```

**Step 3:** Run → pass.

**Step 4:** Commit `chore(diag): gate Bundle C diagnostics on DEBUG_STAGE_TIMINGS (cleanup)`.

**blockedBy:** A.3.1, A.3.2, A.3.3.

### Task A.10.2: Verdict prompt audit — no forbidden user-facing words

**File:** `app/services/extraction_service.py` — `_build_preferences_prompt` and any verdict prompt templates.

**Step 1:** Write failing test `tests/test_verdict_prompt_no_forbidden_words.py`:

```python
def test_verdict_prompt_instructs_against_forbidden_words():
    # Per design § 0 rules + § 11 + CLAUDE.md Qaren UX copy contract
    prompt = _build_preferences_prompt(..., comparison_quality="weird")
    # The prompt itself should not contain user-facing forbidden words EXCEPT as instructions
    forbidden = ["estimated", "reference price"]
    # These may appear ONLY in negative-instruction context ("do not say X")
    for word in forbidden:
        occurrences = prompt.lower().count(word.lower())
        if occurrences > 0:
            # Must be preceded by "not", "do not", "forbidden", "avoid", "never"
            assert any(neg in prompt.lower() for neg in ["do not say", "avoid", "never use", "forbidden"])
```

**Step 2:** Run → FAIL or pass depending on current state.

**Step 3:** Audit all verdict / comparison / value prompts for unintended bare uses of forbidden words. Add negative instructions where needed.

**Step 4:** Commit `chore(extraction): audit verdict prompts for forbidden user-facing words (§ 0 rules)`.

**blockedBy:** A.4.5, A.6.5.

### Task A.10.3: Post-deploy 6-category probe suite (§ 8f)

**Step 1:** Write smoke test `tests/test_bundle_c_post_deploy_smoke.py` (marked `@pytest.mark.integration`):

```python
@pytest.mark.integration
@pytest.mark.parametrize("category,query,expect_dims_min", [
    ("electronics", "iPhone 16 vs Galaxy S25", 5),
    ("skincare", "CeraVe vs Cetaphil Moisturizing Cream", 4),
    ("supplements", "Centrum Silver vs One A Day Men's", 3),
    ("fashion", "Zara blazer vs H&M blazer", 3),
    ("fragrances", "Tom Ford Oud Wood vs Dior Sauvage", 4),
    ("grocery", "Almarai laban vs Saudia laban", 3),
])
def test_post_deploy_6_category_probe(category, query, expect_dims_min):
    r = requests.get(f"{PROD_BASE}/api/v1/text/compare", params={"q": query, "nocache": "true"})
    data = r.json()
    # § 1a: pros/cons populated
    assert all(len(p["pros"]) > 0 and len(p["cons"]) > 0 for p in data["products"])
    # § 1b: factual_verdict non-null
    assert data["scoring"]["scoring_v2"]["factual_verdict"]["line1"] is not None
    # § 1c: real prices (≤1 product on estimated tolerated)
    estimated_count = sum(1 for p in data["products"] if p["price"].get("source_method") == "estimated")
    assert estimated_count <= 1, f"{category}: {estimated_count} products on estimated"
    # § 6a: expected dim count
    assert len(data["scoring"]["scoring_v2"]["dimensions"]) >= expect_dims_min
    # § 2e: comparison_quality emitted
    assert data["comparison_quality"] in ("normal", "weak", "weird")
    # § 7b: applied_shifts qualitative only (when set)
    if data.get("personalization", {}).get("applied_shifts"):
        for s in data["personalization"]["applied_shifts"]:
            assert "magnitude" not in s and "percent" not in s
    # § 5c: NO "estimated" / "reference price" in user-facing strings
    body = json.dumps(data)
    assert "reference price" not in body.lower()
    # "estimated" may appear ONLY as source_method enum
    if "estimated" in body.lower():
        # Confirm it's only in source_method, not in delta_text, factual_verdict, captions, etc.
        for p in data["products"]:
            assert p["price"].get("source_method") in ("estimated", "page_scrape", "firecrawl",
                                                       "scrapedo_rendered", "local_bhd", "official_brand",
                                                       "page_scrape_rendered", "converted_usd")
```

**Step 2:** Add to docs: `docs/SESSION_BUNDLES.md` Bundle C ship entry post-deploy will reference this test + captured evidence.

**Step 3:** Commit `test(integration): post-deploy 6-category Bundle C probe suite (§ 8f)`.

**blockedBy:** all of A.3, A.4, A.5, A.6, A.7, A.8, A.9.

### Task A.10.4: Coverage report — verify 80% line coverage

**Step 1:** Run:

```bash
pytest tests/test_scoring*.py tests/test_extraction_pros_cons*.py tests/test_response_builder*.py \
       tests/test_comparison_quality_detector.py tests/test_spec_fallback*.py \
       tests/test_value_*.py tests/test_confidence*.py tests/test_dim*.py \
       tests/test_price_tiers*.py tests/test_other_sub_scale.py tests/test_applied_shifts.py \
       --cov=app/services/scoring_service \
       --cov=app/services/response_builder \
       --cov=app/services/extraction_service \
       --cov-report=term-missing --cov-fail-under=80
```

**Step 2:** If any module below 80%, add tests for uncovered branches. Push `_detect_price_tier` + `_compute_value_score` to 90% (per coverage target).

**Step 3:** Commit `test(coverage): Bundle C backend at 80%+ (90% on tier-detect + value-formula)`.

**blockedBy:** A.10.3.

---

## A.11 — Documentation updates (§ 8a)

### Task A.11.1: Update CLAUDE.md

Add the following to CLAUDE.md (in approximate locations):

- **Migrations subsection**: append `024 (Bundle C, pending via MCP) adds 'top_tier' to users.preferences.budget CHECK enum; rollback at migrations/rollback/024_top_tier_budget.sql.`
- **Architecture > Backend > Core service**: brief note that `comparison_quality` + `value_match` + `applied_shifts` + `budget_mismatch` are new response fields with qualitative-only contracts.
- **Important Patterns > Deterministic scoring**: add one line: "Bundle C (Session 51, 2026-05-17): 5-tier per-category breakpoints via `PRICE_TIERS_BY_CATEGORY`, dynamic value coefficients by priority, qualitative `applied_shifts[]`, silent dim omission, 3-tier spec fallback, weird-comparison detector via verdict-text only (no banners). Spec: `docs/superpowers/specs/2026-05-17-bundle-c-scoring-quality-design.md`."
- **Environment Variables > Feature Flags**: add `ENABLE_BUNDLE_C_SCORING` (default OFF in code, flip in Railway).
- **Known Remaining Bugs**: remove any entries resolved by Bundle C bug fixes (1a / 1b / 1c).

### Task A.11.2: Update MEMORY.md pending follow-ups

- Remove the **Bucket C brainstorm** entry from MEMORY.md (it has now shipped as Bundle C). Replace with a brief one-liner ship entry.

### Task A.11.3: Update docs/SESSION_BUNDLES.md

Add Bundle C ship entry (template per existing Bundle E entry). Reference: design doc path, plan path, this section, captured A.2.4 evidence path, A.10.3 post-deploy results.

**Commit:** `docs: Bundle C in CLAUDE.md + MEMORY.md + SESSION_BUNDLES.md`.

**blockedBy:** A.10.4.

---

# Summary

**Total tasks in Section A: 33** (A.1.1, A.2.1–A.2.4, A.3.1–A.3.3, A.4.1–A.4.10, A.5.1–A.5.5, A.6.1–A.6.5, A.7.1–A.7.2, A.8.1, A.9.1, A.10.1–A.10.4, A.11.1–A.11.3).

**Dependency chain (top-level):**

```
A.1.1 (migration) ─────────────────────────────────────────────────┐
                                                                    │
A.2.1 → A.2.2 → A.2.3 → A.2.4 (evidence capture) ──┬─→ A.3.1       │
                                                    ├─→ A.3.2       │
                                                    └─→ A.3.3       │
                                                                    │
A.4.1 → A.4.2 → A.4.3 → A.4.4 → A.4.5 → A.4.6 → A.4.7 → A.4.8 → A.4.9
                                                                    │
A.4.10 (legal, parallel) ───────────────────────────────────────────┤
                                                                    │
A.5.1 → A.5.2 → A.5.3 → A.5.4 (←A.1.1) → A.5.5 ─────────────────────┤
                                                                    │
A.6.1 → A.6.2 → A.6.3 → A.6.4 → A.6.5 ──────────────────────────────┤
                                                                    │
A.7.1 → A.7.2 ──────────────────────────────────────────────────────┤
                                                                    │
A.8.1 ──────────────────────────────────────────────────────────────┤
                                                                    │
A.9.1 ──────────────────────────────────────────────────────────────┤
                                                                    │
A.10.1 (cleanup) → A.10.2 (audit) → A.10.3 (smoke) → A.10.4 (coverage)
                                                                    │
A.11.1 → A.11.2 → A.11.3 ───────────────────────────────────────────┘
```

**Critical evidence gates:**
- A.2.4 BLOCKS A.3.1, A.3.2, A.3.3 (no speculative fixes).
- A.10.3 + A.10.4 BLOCK A.11 (docs only ship after evidence-validated).
- A.1.1 BLOCKS A.5.4 (Pydantic Literal extension after CHECK constraint).
- A.4.10 (legal clause) is parallel and unblocked — can ship in the first wave.

**Parallel waves (suggested execution order):**
- **Wave 1 (parallel):** A.1.1, A.2.1, A.2.2, A.2.3, A.4.6, A.4.10, A.5.1, A.5.2, A.5.3, A.5.5, A.6.1, A.7.1.
- **Wave 2 (after A.2.4 evidence):** A.3.1, A.3.2, A.3.3.
- **Wave 3 (calibration cascade):** A.4.1 → A.4.2 → A.4.3 → A.4.4 → A.4.5 → A.4.7 → A.4.8 → A.4.9.
- **Wave 4 (value math + remaining):** A.5.4 (after migration applied), A.6.2 → A.6.3 → A.6.4 → A.6.5, A.7.2, A.8.1, A.9.1.
- **Wave 5 (cleanup + verification):** A.10.1 → A.10.2 → A.10.3 → A.10.4.
- **Wave 6 (docs):** A.11.1 → A.11.2 → A.11.3.

**Evidence artifacts produced:**
- `docs/investigations/2026-05-17-bundle-c-cold-cache-evidence.md` (A.2.4)
- `docs/SESSION_BUNDLES.md` Bundle C ship entry (A.11.3)
- Post-deploy 6-category probe results (A.10.3)
- Coverage report ≥80% on `scoring_service` + `response_builder` + Bundle-C-touched paths in `extraction_service` (A.10.4)

**End of Section A.**


---

# SECTION B — frontend-bundle-c tasks

**Owner files:**
- `SmartCompareApp/src/components/BudgetPicker.tsx`
- `SmartCompareApp/src/screens/onboarding/Step09Budget.tsx`
- `SmartCompareApp/src/screens/onboarding/types.ts` (`OnboardingBudget` literal extension)
- `SmartCompareApp/src/components/results/DimensionBars.tsx`
- `SmartCompareApp/src/components/results/HeroRings.tsx` (copy + sparse-data adaptation only)
- `SmartCompareApp/src/components/results/FactualVerdict.tsx` (contract verification only — backend wires line1/line2 in Section A 1b)
- `SmartCompareApp/src/components/results/ConfidencePills.tsx` (NEW — 3-pill horizontal row)
- `SmartCompareApp/src/components/results/ConfidenceDetailsSheet.tsx` (NEW — "What we know" bottom sheet)
- `SmartCompareApp/src/components/results/PersonalizationChip.tsx` (NEW)
- `SmartCompareApp/src/components/results/DimensionBarsExpand.tsx` (NEW — expand row + animated container, OR co-located in `DimensionBars.tsx`)
- `SmartCompareApp/src/screens/ResultsScreen.tsx` (integration — pills, chip, delta hero captions, weird-mode rendering, suppression of legacy banner)
- `SmartCompareApp/src/screens/EditPreferencesFlow.tsx` (5-tier prop pass-through, no logic change beyond literal type)
- `SmartCompareApp/src/services/sourceMethod.ts` (NEW — `parseSourceMethod()` helper)
- `SmartCompareApp/src/types.ts` (Dimension confidence stays optional, new `comparison_quality`, `value_match`, `applied_shifts`, `source_method` types, `BudgetValue` extension)
- `SmartCompareApp/src/i18n/en.json` + `ar.json`
- `SmartCompareApp/__tests__/` snapshot + behavioral tests under `results/` subdir

**Coverage target:** 80% line coverage on new components (`ConfidencePills`, `ConfidenceDetailsSheet`, `PersonalizationChip`, `sourceMethod.ts`), 90% on `parseSourceMethod()` decision logic. Snapshot coverage for `DimensionBars`, `BudgetPicker`, `Step09Budget`, `FactualVerdict`, `ResultsScreen` scoring_v2 section.

**Blocked-by:**
- A.1.x (`comparison_quality`, `value_match`, `personalization.applied_shifts`, `source_method` per-product, `dimensions[].confidence` propagation) — frontend stubs the API shape and starts UI work immediately; final wire-up validated at QA.
- A.3.x (`PRICE_TIERS_BY_CATEGORY` + `BudgetValue` Literal extension) — frontend `BudgetValue` mirrors backend Literal; coordinate via shared spec section 3a label table.
- Migration 024 — non-blocking for B (preferences post still accepts old 3-tier values; the 5-tier picker writes new tier strings that the migration accepts post-apply).

**Common preamble for frontend agents:**
> Read `docs/superpowers/specs/2026-05-17-bundle-c-scoring-quality-design.md` Sections 0, 2 (parts b/d/e/h), 3c, 4b/d/e, 5b/c/d, 6a/b/c, 7a/c, 8d (frontend snapshots) before doing anything. Honor the absorbed rules in Section 0: NO info banners, NO backend internals in tap-reveals, NO "estimated"/"reference price"/"تقدير" copy ANYWHERE. Forbidden scary words (English + Arabic): `couldn't`, `try again`, `Failed to`, `تعذر`, `فشل`. TDD: write failing Jest test FIRST, run to confirm fail, implement minimal code, run again, commit. Snapshot tests for visual surface; behavioral tests for branching logic. Use `npx tsc --noEmit` after each component to catch TS errors (LSP unreliable on Windows per `MEMORY.md` — trust ONLY tsc exit code).

---

## B.1 — TypeScript contract additions

Establishes the type surface every downstream task depends on. Ship before component work begins.

### Task B.1.1: Failing test for new TypeScript contract fields

**File:** `SmartCompareApp/__tests__/types.contract.test.ts` (new)

**Step 1:** Write a compile-time + runtime sanity test:
```typescript
import type { BudgetValue, Dimension, ScoringV2, PersonalizationApplied, ValueMatch, ComparisonQuality, SourceMethod } from '../src/types';

test('BudgetValue accepts 5 literal tiers', () => {
  const valid: BudgetValue[] = ['budget', 'mid', 'premium', 'luxury', 'top_tier'];
  expect(valid).toHaveLength(5);
});

test('Dimension.confidence is optional and accepts low|medium|high', () => {
  const d: Dimension = { key: 'price', label: 'Price', score_a: 80, score_b: 72, delta_text: '10% less', confidence: 'high' };
  expect(d.confidence).toBe('high');
});

test('PersonalizationApplied carries applied_shifts array', () => {
  const p: PersonalizationApplied = { applied_shifts: [{ dim_display: 'performance', direction: 'up' }] };
  expect(p.applied_shifts[0].direction).toBe('up');
});

test('ValueMatch literal accepts in_range|above_range|below_range', () => {
  const v: ValueMatch[] = ['in_range', 'above_range', 'below_range'];
  expect(v).toHaveLength(3);
});

test('ComparisonQuality literal accepts normal|weak|weird', () => {
  const q: ComparisonQuality[] = ['normal', 'weak', 'weird'];
  expect(q).toHaveLength(3);
});

test('SourceMethod includes estimated enum', () => {
  const m: SourceMethod = 'estimated';
  expect(m).toBe('estimated');
});
```

**Step 2:** Run `cd SmartCompareApp && npx jest __tests__/types.contract.test.ts` → FAIL (type imports do not exist).

### Task B.1.2: Implement type additions in `src/types.ts`

**blockedBy:** B.1.1

**File:** `SmartCompareApp/src/types.ts`

Extend in one pass:
- `BudgetValue` becomes `'budget' | 'mid' | 'premium' | 'luxury' | 'top_tier'`.
- `ValueMatch = 'in_range' | 'above_range' | 'below_range'`.
- `ComparisonQuality = 'normal' | 'weak' | 'weird'`.
- `SourceMethod = 'local_bhd' | 'converted_usd' | 'page_scrape' | 'page_scrape_rendered' | 'firecrawl' | 'scrapedo_rendered' | 'estimated'` (mirrors backend enum).
- `PersonalizationApplied = { applied_shifts: Array<{ dim_display: string; direction: 'up' | 'down' }> }`.
- Extend `ScoringV2` with optional `comparison_quality?: ComparisonQuality`, `value_match?: { product_a: ValueMatch; product_b: ValueMatch }`, `personalization?: PersonalizationApplied`.
- Extend `Product.price` to include optional `source_method?: SourceMethod`.

**Step 3:** Run jest → all 6 pass. Run `npx tsc --noEmit` → 0 errors.

**Step 4:** Commit `feat(types): add Bundle C scoring contract fields (BudgetValue 5-tier, comparison_quality, value_match, applied_shifts, source_method)`.

---

## B.2 — i18n key additions (EN + AR)

Establishes copy before component imports. Honors Section 0 forbidden-words list + Section 5c silence-on-fallback rule.

### Task B.2.1: Failing snapshot for missing i18n keys

**File:** `SmartCompareApp/__tests__/i18n.bundle_c.test.ts` (new)

**Step 1:**
```typescript
import en from '../src/i18n/en.json';
import ar from '../src/i18n/ar.json';

const REQUIRED_KEYS = [
  // Section 3c — 5-tier picker
  'onboarding.s9.luxury', 'onboarding.s9.luxury_range',
  'onboarding.s9.top_tier', 'onboarding.s9.top_tier_range',
  'onboarding.s9.caveat',
  // Section 4d — value-match captions
  'results.valueMatch.above_range', 'results.valueMatch.below_range',
  'results.valueMatch.above_range_with_tradeoff', 'results.valueMatch.cheaper_of_two',
  // Section 5b — confidence pills + sheet
  'results.confidence.pill.price', 'results.confidence.pill.reviews', 'results.confidence.pill.specs',
  'results.confidence.sheet.title', 'results.confidence.sheet.close',
  // Section 7c — personalization chip
  'results.personalization.chip_template',
  'results.personalization.arrow_up',
  'results.personalization.arrow_down',
] as const;

test.each(REQUIRED_KEYS)('EN has key %s', (k) => expect((en as Record<string, string>)[k]).toBeTruthy());
test.each(REQUIRED_KEYS)('AR has key %s', (k) => expect((ar as Record<string, string>)[k]).toBeTruthy());

const FORBIDDEN_EN = /\b(couldn't|try again|Failed to|estimated|reference price|indicative)\b/i;
const FORBIDDEN_AR = /(تعذر|فشل|تقدير|مُقدَّر)/;

test('no forbidden EN copy across Bundle C keys', () => {
  for (const k of REQUIRED_KEYS) {
    const v = (en as Record<string, string>)[k];
    expect(v).not.toMatch(FORBIDDEN_EN);
  }
});
test('no forbidden AR copy across Bundle C keys', () => {
  for (const k of REQUIRED_KEYS) {
    const v = (ar as Record<string, string>)[k];
    expect(v).not.toMatch(FORBIDDEN_AR);
  }
});
```

**Step 2:** Run → FAIL (keys missing).

### Task B.2.2: Add new EN + AR keys

**blockedBy:** B.2.1

**Files:** `SmartCompareApp/src/i18n/en.json`, `SmartCompareApp/src/i18n/ar.json`

Per spec Section 3a + 4d + 5b + 7a:

EN additions:
- `"onboarding.s9.luxury": "Luxury"`
- `"onboarding.s9.luxury_range": "189–500 BHD"`
- `"onboarding.s9.top_tier": "Top-tier"`
- `"onboarding.s9.top_tier_range": "500+ BHD"`
- `"onboarding.s9.caveat": "Varies by category"`
- `"results.valueMatch.above_range": "Above your usual range"`
- `"results.valueMatch.below_range": "Within your range"`
- `"results.valueMatch.above_range_with_tradeoff": "Above your usual range — but here's why"`
- `"results.valueMatch.cheaper_of_two": "Cheaper of the two"`
- `"results.confidence.pill.price": "Price"`
- `"results.confidence.pill.reviews": "Reviews"`
- `"results.confidence.pill.specs": "Specs"`
- `"results.confidence.sheet.title": "What we know"`
- `"results.confidence.sheet.close": "Close"`
- `"results.personalization.chip_template": "Weighted {{arrows}} (based on your priorities)"`
- `"results.personalization.arrow_up": "↑ {{dim}}"`
- `"results.personalization.arrow_down": "↓ {{dim}}"`

AR additions (mirror; ranges keep ASCII digits inside spec strings; ranges in onboarding currently use Arabic-Indic digits per existing convention):
- `"onboarding.s9.luxury": "فاخر"`
- `"onboarding.s9.luxury_range": "١٨٩–٥٠٠ دينار"`
- `"onboarding.s9.top_tier": "الأعلى"`
- `"onboarding.s9.top_tier_range": "٥٠٠+ دينار"`
- `"onboarding.s9.caveat": "يختلف حسب الفئة"`
- `"results.valueMatch.above_range": "أعلى من نطاقك المعتاد"`
- `"results.valueMatch.below_range": "ضمن نطاقك"`
- `"results.valueMatch.above_range_with_tradeoff": "أعلى من نطاقك المعتاد — وإليك السبب"`
- `"results.valueMatch.cheaper_of_two": "الأرخص بين الاثنين"`
- `"results.confidence.pill.price": "السعر"`
- `"results.confidence.pill.reviews": "التقييمات"`
- `"results.confidence.pill.specs": "المواصفات"`
- `"results.confidence.sheet.title": "ما نعرفه"`
- `"results.confidence.sheet.close": "إغلاق"`
- `"results.personalization.chip_template": "مرجَّح {{arrows}} (بناءً على أولوياتك)"`
- `"results.personalization.arrow_up": "↑ {{dim}}"`
- `"results.personalization.arrow_down": "↓ {{dim}}"`

**Step 3:** Run jest → all key + forbidden-word assertions pass.

**Step 4:** Commit `i18n(bundle-c): add 5-tier picker, value-match captions, confidence pills + sheet, personalization chip (EN + AR)`.

### Task B.2.3: Adjust existing `onboarding.s9.budget_range` + `mid_range` + `premium_range` for tier rescale

**blockedBy:** B.2.2 (additions land first so we don't churn the file twice)

**Files:** `SmartCompareApp/src/i18n/en.json`, `SmartCompareApp/src/i18n/ar.json`

Per spec Section 3e (`other_light` default sub-scale used for general onboarding picker — the picker shows general guidance, per-category re-anchoring is server-side and invisible):
- `"onboarding.s9.budget_range"` → `"Under 11 BHD"` (unchanged)
- `"onboarding.s9.mid_range"` → `"11–57 BHD"` (unchanged)
- `"onboarding.s9.premium_range"` → `"57–189 BHD"` (unchanged)
- New `luxury_range`/`top_tier_range` above continue the sequence.

Verify EN + AR ranges form a contiguous monotonic ladder. No changes needed if existing values match spec — confirm via test:

```typescript
test('budget ranges form monotonic ladder', () => {
  // anchor-spot check via numeric extraction from EN copy
  expect((en as any)['onboarding.s9.budget_range']).toMatch(/11/);
  expect((en as any)['onboarding.s9.mid_range']).toMatch(/57/);
  expect((en as any)['onboarding.s9.premium_range']).toMatch(/189/);
  expect((en as any)['onboarding.s9.luxury_range']).toMatch(/500/);
});
```

**Step:** Commit `i18n(bundle-c): verify onboarding budget ladder is monotonic across 5 tiers`.

---

## B.3 — BudgetPicker (5-tier expansion)

**Spec:** Section 3a + 3c. Visual treatment: `premium/luxury/top_tier` get subtle dark accent + serif label weight (`Geist Display Medium` for `top_tier`).

### Task B.3.1: Failing snapshot test — 5 cards render

**blockedBy:** B.1.2, B.2.2

**File:** `SmartCompareApp/__tests__/components/BudgetPicker.test.tsx` (new)

**Step 1:**
```typescript
import { render } from '@testing-library/react-native';
import BudgetPicker from '../../src/components/BudgetPicker';

test('renders 5 tier cards', () => {
  const { getByTestId } = render(<BudgetPicker value="mid" onChange={() => {}} />);
  ['budget', 'mid', 'premium', 'luxury', 'top_tier'].forEach((v) => {
    expect(getByTestId(`budget-${v}`)).toBeTruthy();
  });
});

test('snapshot — 5 tier picker', () => {
  const tree = render(<BudgetPicker value="luxury" onChange={() => {}} />).toJSON();
  expect(tree).toMatchSnapshot();
});

test('selected card receives selected accessibility state', () => {
  const { getByTestId } = render(<BudgetPicker value="top_tier" onChange={() => {}} />);
  expect(getByTestId('budget-top_tier').props.accessibilityState.selected).toBe(true);
  expect(getByTestId('budget-budget').props.accessibilityState.selected).toBe(false);
});
```

**Step 2:** Run → FAIL (3-card output).

### Task B.3.2: Extend `BudgetPicker.tsx` to 5 tiers with visual treatment

**blockedBy:** B.3.1

**File:** `SmartCompareApp/src/components/BudgetPicker.tsx`

**Implementation outline:**
- Extend `BudgetValue` import (already from B.1.2).
- `BUDGETS` array gains 2 entries: `luxury`, `top_tier`.
- New style branch for premium/luxury/top_tier — subtle dark accent (use `colors.bg.tertiary` or design-spec'd dark accent token; if missing add via theme PR-thin update in B.3.3 below).
- `top_tier` label uses serif/Geist Display Medium — pull `typography.displayEmphasis` if present, else apply `fontFamily: 'GeistDisplay-Medium'` (already loaded per existing theme; verify in `theme/index.ts`).
- Editorial restraint per spec § 3c — NO gaudy gold, NO border glow, NO icon. Just font + accent shade.

**Step 3:** Run jest → snapshot generated + 5-card test passes. Run `npx tsc --noEmit` → 0 errors.

**Step 4:** Commit `feat(ui): BudgetPicker expands to 5 tiers with editorial dark accent on premium/luxury/top_tier`.

### Task B.3.3: Theme token for "dark accent" if missing

**blockedBy:** B.3.2 (only ship if theme.index.ts lacks a suitable token)

**File:** `SmartCompareApp/src/theme/index.ts`

If `colors.bg.tertiary` or equivalent restrained dark accent does not exist, add `colors.accents.editorialDark = '#1A1A1A'` (or design-doc-confirmed value). No semantic shift to existing emerald — accent stays neutral dark.

**Step:** Commit `theme(bundle-c): editorialDark accent token for premium tier visual differentiation` (skip if token already exists).

---

## B.4 — Step09Budget (onboarding 5-tier mirror)

**Spec:** Section 3c. Mirror BudgetPicker behavior + add the GENERAL guidance caveat line per spec.

### Task B.4.1: Update `OnboardingBudget` type

**blockedBy:** B.1.2

**File:** `SmartCompareApp/src/screens/onboarding/types.ts`

Set `OnboardingBudget` = `BudgetValue` (5-tier) — re-export or alias.

**Commit:** `types(onboarding): OnboardingBudget mirrors 5-tier BudgetValue`.

### Task B.4.2: Failing snapshot test for Step09Budget — 5 cards + caveat

**blockedBy:** B.4.1, B.2.2

**File:** `SmartCompareApp/__tests__/screens/Step09Budget.test.tsx` (new)

```typescript
test('renders 5 cards + caveat line', () => {
  const { getByTestId, getByText } = render(<Step09Budget value="mid" onChange={() => {}} />);
  ['budget', 'mid', 'premium', 'luxury', 'top_tier'].forEach((v) => {
    expect(getByTestId(`budget-${v}`)).toBeTruthy();
  });
  expect(getByText(/varies by category/i)).toBeTruthy();
});
test('snapshot', () => {
  expect(render(<Step09Budget value="top_tier" onChange={() => {}} />).toJSON()).toMatchSnapshot();
});
```

Run → FAIL.

### Task B.4.3: Implement Step09Budget 5-tier expansion

**blockedBy:** B.4.2

**File:** `SmartCompareApp/src/screens/onboarding/Step09Budget.tsx`

- `BUDGETS` array gains `luxury` + `top_tier`.
- Add single-line caveat `<Text>{t('onboarding.s9.caveat')}</Text>` below the cards list. Style: caption, secondary color, marginTop spacing.sm.
- Apply same visual treatment as BudgetPicker (premium/luxury/top_tier subtle dark accent, top_tier serif).

Run jest → pass. `npx tsc --noEmit` → 0 errors.

**Commit:** `feat(onboarding): Step09Budget expands to 5 tiers with general-guidance caveat`.

### Task B.4.4: EditPreferencesFlow pass-through verification

**blockedBy:** B.4.3

**File:** `SmartCompareApp/src/screens/EditPreferencesFlow.tsx`

Open file; verify the budget step delegates to `BudgetPicker` (it likely already does). If `BudgetValue` is hard-coded to a 3-literal union in this file, replace with import from `types.ts`. No logic change; type passthrough only.

Add focused test:
```typescript
test('EditPreferencesFlow forwards top_tier selection upward', () => {
  const onSave = jest.fn();
  const { getByTestId } = render(<EditPreferencesFlow initialBudget="mid" onSave={onSave} />);
  fireEvent.press(getByTestId('budget-top_tier'));
  fireEvent.press(getByTestId('edit-prefs-save'));
  expect(onSave).toHaveBeenCalledWith(expect.objectContaining({ budget: 'top_tier' }));
});
```

**Commit:** `feat(prefs): EditPreferencesFlow accepts 5-tier BudgetValue end-to-end`.

---

## B.5 — DimensionBars overhaul (sparse-data + hero + expand)

**Spec:** Sections 2b (insufficient-data row), 2d (hero clean), 2e (weird mode), 2h (silent omission), 4b (delta hero layout), 4d (value-match captions), 6a–c (contract sourcing, hero + expand, missing-data rules).

### Task B.5.1: Failing snapshot — DimensionBars with null-score row silently omitted

**blockedBy:** B.1.2

**File:** `SmartCompareApp/__tests__/components/DimensionBars.silent_omission.test.tsx` (new)

```typescript
import { render } from '@testing-library/react-native';
import { DimensionBars } from '../../src/components/results/DimensionBars';

test('dimensions with null score on either side are silently omitted (spec § 2h)', () => {
  const dims = [
    { key: 'price', label: 'Price', score_a: 80, score_b: 72, delta_text: '10% less' },
    { key: 'reviews', label: 'Reviews', score_a: null, score_b: 75, delta_text: '' }, // omit
    { key: 'specs', label: 'Specs', score_a: 70, score_b: 80, delta_text: '' },
  ] as any;
  const { queryByTestId } = render(<DimensionBars dimensions={dims} winnerIndex={0} testID="bars" />);
  expect(queryByTestId('bars-row-price')).toBeTruthy();
  expect(queryByTestId('bars-row-reviews')).toBeNull(); // silently omitted
  expect(queryByTestId('bars-row-specs')).toBeTruthy();
});
```

Run → FAIL (current impl renders the null row via TS coercion or contract-violation node).

### Task B.5.2: Implement silent-omission filter at component entry

**blockedBy:** B.5.1

**File:** `SmartCompareApp/src/components/results/DimensionBars.tsx`

Modify `DimensionBars` to filter `dimensions` array on entry:
```typescript
const renderableDims = dimensions.filter(
  (d) => d.score_a != null && d.score_b != null && d.score_a > 0 && d.score_b > 0,
);
```

Keep the existing `hasZero` contract-violation node ONLY for the dev-mode case where backend emits `score=0` (regression safety net per spec § 6d). The new filter handles `null` cleanly.

Run jest → silent-omission test passes. Existing contract-violation test still passes (zero score still trips violation, not silent).

**Commit:** `feat(dims): silently omit dimensions with null scores per spec § 2h`.

### Task B.5.3: Failing test — insufficient-data row (last-resort visible)

**blockedBy:** B.5.2

**Step 1:** Test:
```typescript
test('renders insufficient-data row when dimension flagged data_insufficient=true (spec § 2b)', () => {
  const dims = [
    { key: 'durability', label: 'Durability', score_a: null, score_b: null, delta_text: '', data_insufficient: true },
  ] as any;
  const { getByTestId, getByText } = render(<DimensionBars dimensions={dims} winnerIndex={0} testID="bars" />);
  expect(getByTestId('bars-row-durability-insufficient')).toBeTruthy();
  expect(getByText(/limited data/i)).toBeTruthy();
});

test('insufficient row has no bar fill and no emerald accent', () => {
  // assert via style snapshot or by query for absence of fill testIDs
  // bars-row-durability-fill-a should NOT exist
});
```

Run → FAIL.

### Task B.5.4: Implement insufficient-data row rendering

**blockedBy:** B.5.3

Add new path in DimensionBars: when `dim.data_insufficient === true`, render a row with the label + a neutral muted caption `"Limited data"` (i18n key `results.dimensions.limited_data` — add to i18n in this task), no bar tracks, no fill, no scores. Add `bars-row-{key}-insufficient` testID.

i18n EN: `"results.dimensions.limited_data": "Limited data"`.
i18n AR: `"results.dimensions.limited_data": "بيانات محدودة"`.

Run jest → pass.

**Commit:** `feat(dims): insufficient-data row (last-resort visible state per spec § 2b)`.

### Task B.5.5: Failing test — value/price delta hero layout

**blockedBy:** B.5.2

**Step 1:** Test (`DimensionBars.delta_hero.test.tsx`):
```typescript
test('value row promotes delta_text to hero typography.title with emerald winner styling', () => {
  const dims = [
    { key: 'value', label: 'Value', score_a: 88, score_b: 78, delta_text: '40% less' },
  ] as any;
  const { getByTestId } = render(<DimensionBars dimensions={dims} winnerIndex={0} testID="bars" />);
  const delta = getByTestId('bars-row-value-delta-hero');
  // Resolved style includes emerald color for winner row
  const flat = StyleSheet.flatten(delta.props.style);
  expect(flat.color).toBe(colors.accent);
  expect(flat.fontSize).toBeGreaterThanOrEqual(typography.title.fontSize);
});

test('score numbers shrink to caption size beside bars', () => {
  // assert bars-row-value-score-a has typography.caption-equivalent fontSize
});
```

Run → FAIL.

### Task B.5.6: Implement delta hero promotion in DimensionRow

**blockedBy:** B.5.5

Restructure `DimensionRow` for `value` + `price` rows specifically:
- Move `delta_text` from caption-size right-of-label to center-large under label.
- Apply `typography.title` weight + emerald (`colors.accent`) when the row's winning side matches `winnerIndex`; neutral (`colors.text.primary`) on tie.
- Score numbers (`ScoreText` component) drop to `typography.caption` size beside the bars.
- Add `bars-row-{key}-delta-hero` testID on the centered delta Text.
- For dims OTHER than `value` / `price`, keep existing inline-right delta caption layout (incremental migration; spec 4b focuses on value/price).

Add cross-tier handling per spec § 4c: when `dim.is_cross_tier === true`, delta hero text reads `"Different tier — held to higher bar"` (new i18n key `results.value.different_tier`), no winner-emerald (both sides muted).

i18n EN: `"results.value.different_tier": "Different tier — held to higher bar"`.
i18n AR: `"results.value.different_tier": "فئة مختلفة — مقاسة بمعيار أعلى"`.

Run jest → pass.

**Commit:** `feat(dims): promote delta_text to hero typography on value/price rows (spec § 4b + 4c)`.

### Task B.5.7: Failing test — value-match caption renders per backend signal

**blockedBy:** B.5.6

**Step 1:** Test (`DimensionBars.value_match.test.tsx`):
```typescript
test('value row renders above_range caption when value_match=above_range', () => {
  const dims = [
    { key: 'value', label: 'Value', score_a: 80, score_b: 75, delta_text: 'Stronger value', value_match_a: 'above_range', value_match_b: 'in_range' } as any,
  ];
  const { getByText } = render(<DimensionBars dimensions={dims} winnerIndex={0} testID="bars" />);
  expect(getByText(/above your usual range/i)).toBeTruthy();
});

test('silent on in_range / in_range (spec § 4d exact match)', () => {
  const dims = [{ key: 'value', label: 'Value', score_a: 80, score_b: 78, delta_text: '5% less', value_match_a: 'in_range', value_match_b: 'in_range' } as any];
  const { queryByText } = render(<DimensionBars dimensions={dims} winnerIndex={0} testID="bars" />);
  expect(queryByText(/range/i)).toBeNull();
});

test('renders cheaper_of_two caption when value_match=below_range on both products', () => {
  const dims = [{ key: 'value', label: 'Value', score_a: 80, score_b: 75, delta_text: '20% less', value_match_a: 'below_range', value_match_b: 'below_range' } as any];
  const { getByText } = render(<DimensionBars dimensions={dims} winnerIndex={0} testID="bars" />);
  expect(getByText(/cheaper of the two/i)).toBeTruthy();
});
```

Run → FAIL.

### Task B.5.8: Implement value-match caption rendering inside DimensionRow

**blockedBy:** B.5.7

Per-row optional caption block beneath the bars (only `value` row gets this — `price` row keeps clean):
- If `value_match_a === 'in_range' && value_match_b === 'in_range'` → silent (no caption rendered).
- If product A is `above_range` and dimension is winning that side → caption `t('results.valueMatch.above_range')`.
- If product is `below_range` → caption `t('results.valueMatch.below_range')`.
- If `key_tradeoff` exists AND value_match is 2+ tiers off → caption `t('results.valueMatch.above_range_with_tradeoff') + ' ' + key_tradeoff_snippet`.
- If both `below_range` → caption `t('results.valueMatch.cheaper_of_two')`.

Caption styled as `typography.caption`, muted color, marginTop spacing.xs.

NOTE: per spec, no banner ANYWHERE. Caption renders inline below value row only.

Run jest → 3 cases pass.

**Commit:** `feat(dims): value-match per-row captions for above/below range + cross-tier tradeoffs (spec § 4d + 4e)`.

### Task B.5.9: Hero card + expand layout — failing test

**blockedBy:** B.5.6

**File:** `SmartCompareApp/__tests__/components/DimensionBars.hero_expand.test.tsx`

```typescript
test('hero card shows top 3-4 dims by default (collapsed)', () => {
  const dims = [
    { key: 'price', label: 'Price', score_a: 85, score_b: 75, delta_text: '10% less' },
    { key: 'reviews', label: 'Reviews', score_a: 88, score_b: 80, delta_text: '0.5★ higher' },
    { key: 'value', label: 'Value', score_a: 90, score_b: 70, delta_text: 'Stronger value' },
    { key: 'performance', label: 'Performance', score_a: 82, score_b: 78, delta_text: '' },
    { key: 'build', label: 'Build', score_a: 80, score_b: 76, delta_text: '' },
    { key: 'longevity', label: 'Longevity', score_a: 75, score_b: 72, delta_text: '' },
  ] as any;
  const { queryByTestId, getByText } = render(<DimensionBars dimensions={dims} winnerIndex={0} testID="bars" />);
  // top 4 visible
  expect(queryByTestId('bars-row-price')).toBeTruthy();
  expect(queryByTestId('bars-row-reviews')).toBeTruthy();
  expect(queryByTestId('bars-row-value')).toBeTruthy();
  expect(queryByTestId('bars-row-performance')).toBeTruthy();
  // bottom 2 hidden behind expand
  expect(queryByTestId('bars-row-build')).toBeNull();
  expect(queryByTestId('bars-row-longevity')).toBeNull();
  // expand row visible
  expect(getByText(/see full breakdown/i)).toBeTruthy();
});

test('tapping expand row reveals remaining dims', () => {
  const dims = [/* same 6 dims */] as any;
  const { getByText, getByTestId } = render(<DimensionBars dimensions={dims} winnerIndex={0} testID="bars" />);
  fireEvent.press(getByTestId('bars-expand-row'));
  expect(getByTestId('bars-row-build')).toBeTruthy();
  expect(getByTestId('bars-row-longevity')).toBeTruthy();
});

test('no expand row when ≤4 dims', () => {
  const dims = [/* 3 dims */] as any;
  const { queryByTestId } = render(<DimensionBars dimensions={dims} winnerIndex={0} testID="bars" />);
  expect(queryByTestId('bars-expand-row')).toBeNull();
});
```

Run → FAIL.

### Task B.5.10: Implement hero + expand inline animated reveal

**blockedBy:** B.5.9

**File:** `SmartCompareApp/src/components/results/DimensionBars.tsx` (extend) — OR co-locate the expand logic in a new file `DimensionBarsExpand.tsx` and import. Prefer co-location to keep API single-export.

- Internal state `expanded: boolean` default `false`.
- Slice `renderableDims` into `heroDims = renderableDims.slice(0, 4)` + `extraDims = renderableDims.slice(4)`.
- Render heroDims always.
- If `extraDims.length > 0`: render `<TouchableOpacity testID="bars-expand-row">` with `t('results.dimensions.see_full_breakdown')` chevron icon.
- Animated height container around `extraDims` using `react-native-reanimated` `useSharedValue` + `withTiming` on `height` (or `Animated.View` with measured height). Spec § 6b says "animated height transition (use Reanimated)".
- Chevron flips on `expanded`.
- Add haptic on transition INTO expanded (per project pattern: `light` intensity, never error/heavy per CLAUDE.md motion vocabulary).

i18n EN: `"results.dimensions.see_full_breakdown": "See full breakdown"`.
i18n AR: `"results.dimensions.see_full_breakdown": "اعرض التفصيل الكامل"`.

Run jest → 3 cases pass. Note: animation timing tests may need fake timers; use `jest.useFakeTimers()` + `act(() => jest.advanceTimersByTime(...))`.

**Commit:** `feat(dims): hero card with top 3-4 dims + animated expand row for full breakdown (spec § 6b)`.

### Task B.5.11: Snapshot test pass — DimensionBars full coverage

**blockedBy:** B.5.10

**File:** `SmartCompareApp/__tests__/components/DimensionBars.snapshot.test.tsx`

3 snapshots:
- `snapshot — 6 dims collapsed (hero state)`
- `snapshot — 6 dims expanded`
- `snapshot — 2 dims (no expand row)`

Run → snapshots generated. Commit `test(dims): snapshot coverage for hero + expand states`.

---

## B.6 — Hero overall score adaptation + weird-mode rendering

**Spec:** Sections 2d (hero clean, no Limited data pill), 2e (weird mode renders hero as `—`).

### Task B.6.1: Failing test — hero score renders cleanly when data sparse (no pill)

**blockedBy:** B.1.2

**File:** `SmartCompareApp/__tests__/components/HeroRings.sparse.test.tsx`

```typescript
test('renders score cleanly with no Limited data pill even when scores are low', () => {
  const { queryByText } = render(<HeroRings scoreA={61} scoreB={62} winnerIndex={1} />);
  expect(queryByText(/limited data/i)).toBeNull();
  expect(queryByText(/low confidence/i)).toBeNull();
});
```

Run → likely passes today (HeroRings is already clean) — confirms the contract.

### Task B.6.2: Failing test — weird-mode hero suppression

**blockedBy:** B.1.2

**File:** `SmartCompareApp/__tests__/screens/ResultsScreen.weird_mode.test.tsx`

```typescript
test('renders hero overall as em-dash when comparison_quality=weird (spec § 2e)', () => {
  const result = mockResultWithScoringV2({
    scoring_v2: {
      comparison_quality: 'weird',
      overall_score: { product_a: 0, product_b: 0 },
      dimensions: [{ key: 'price', label: 'Price', score_a: 80, score_b: 60, delta_text: '20% less' }],
    },
  });
  const { getByTestId, queryByTestId } = render(<ResultsScreen route={{ params: { result } }} />);
  // Hero renders em-dash placeholder, NOT zeros
  expect(getByTestId('results-v2-hero-em-dash')).toBeTruthy();
  expect(queryByTestId('results-v2-hero-rings')).toBeNull();
  // No banner
  expect(queryByTestId('results-weird-banner')).toBeNull();
});
```

Run → FAIL.

### Task B.6.3: Implement weird-mode hero suppression in ResultsScreen

**blockedBy:** B.6.2

**File:** `SmartCompareApp/src/screens/ResultsScreen.tsx`

In the scoring_v2 section (around line 1078 — see `ResultsScreen.tsx:1078`):
- Compute `isWeird = scoring_v2?.comparison_quality === 'weird'`.
- When `isWeird`: replace `<HeroRings ... />` with a centered `<Text testID="results-v2-hero-em-dash">—</Text>` block (typography.display, muted color). Still render `TopMatchBadge`? — NO, suppress badge in weird mode (spec § 2e says verdict text carries meaning).
- When `isWeird` AND `dimensions.length === 0`: render only the FactualVerdict line + suppressed hero. DimensionBars naturally renders only signal-bearing dims per B.5 silent-omission.
- NO banner anywhere — verdict text already adapts via backend prompt (spec § 2e).

Run jest → weird-mode test passes. Existing scoring_v2 hero rendering unchanged for `normal | weak`.

**Commit:** `feat(results): suppress hero rings in weird-comparison mode, render em-dash (spec § 2e)`.

---

## B.7 — Confidence widget — 3-pill row + bottom sheet

**Spec:** Sections 5b–d. Replace legacy single-word confidence banner at `ResultsScreen.tsx:737-761`.

### Task B.7.1: Failing snapshot — ConfidencePills component renders 3 pills

**blockedBy:** B.1.2, B.2.2

**File:** `SmartCompareApp/__tests__/components/ConfidencePills.test.tsx` (new)

```typescript
import { ConfidencePills } from '../../src/components/results/ConfidencePills';

test('renders 3 pills with correct labels + emojis', () => {
  const confidence = { price: 'strong', reviews: 'acceptable', specs: 'weak' } as const;
  const { getByText } = render(<ConfidencePills confidence={confidence} onPillPress={() => {}} />);
  expect(getByText(/Price/)).toBeTruthy();
  expect(getByText(/Reviews/)).toBeTruthy();
  expect(getByText(/Specs/)).toBeTruthy();
});

test('emerald color on strong, amber on acceptable, muted-gray on weak', () => {
  // resolve testID styles, assert background colors per spec § 5b
});

test('omits Price pill when any product source_method=estimated (spec § 5c)', () => {
  const { queryByText } = render(<ConfidencePills confidence={{ price: 'strong', reviews: 'strong', specs: 'strong' }} hidePricePill onPillPress={() => {}} />);
  expect(queryByText(/Price/)).toBeNull();
  expect(queryByText(/Reviews/)).toBeTruthy();
  expect(queryByText(/Specs/)).toBeTruthy();
});
```

Run → FAIL.

### Task B.7.2: Implement `ConfidencePills.tsx`

**blockedBy:** B.7.1

**File:** `SmartCompareApp/src/components/results/ConfidencePills.tsx` (new)

Component contract:
```typescript
interface Props {
  confidence: { price?: 'strong' | 'acceptable' | 'weak'; reviews?: 'strong' | 'acceptable' | 'weak'; specs?: 'strong' | 'acceptable' | 'weak' };
  hidePricePill?: boolean;
  onPillPress: (leg: 'price' | 'reviews' | 'specs') => void;
  testID?: string;
}
```

- Horizontal row of TouchableOpacity pills (3 max).
- Each pill: emoji prefix (💰/⭐/📋) + label from i18n + colored background.
- Color map: `strong → colors.accent`, `acceptable → colors.warning` (amber), `weak → colors.text.secondary + bg muted`. Confirm `colors.warning` is amber per theme; if not, add `colors.amber` token.
- Tapping fires `onPillPress(leg)`.
- Hide Price pill entirely when `hidePricePill === true` (per spec § 5c — Price NUMBER still renders in dim bars silently; only the pill is suppressed).
- NO scary copy in microcopy. NO "Limited" / "Low" / "fallback" wording.

Run jest → 3 pills pass + suppression case passes.

**Commit:** `feat(results): ConfidencePills 3-pill row (Price/Reviews/Specs) with strong/acceptable/weak coloring`.

### Task B.7.3: Failing test — ConfidenceDetailsSheet renders 2-3 factual lines per leg

**blockedBy:** B.7.2

**File:** `SmartCompareApp/__tests__/components/ConfidenceDetailsSheet.test.tsx`

```typescript
import { ConfidenceDetailsSheet } from '../../src/components/results/ConfidenceDetailsSheet';

test('renders 2-3 factual lines for reviews leg', () => {
  const details = {
    reviews: ['1200 reviews aggregated from Amazon, Best Buy, Google.', 'Source verification pending.'],
  };
  const { getByText } = render(<ConfidenceDetailsSheet visible leg="reviews" details={details} onClose={() => {}} />);
  expect(getByText(/1200 reviews aggregated/)).toBeTruthy();
  expect(getByText(/Source verification pending/)).toBeTruthy();
});

test('NO threshold numbers or coefficient leaks (countable facts only)', () => {
  // assertion: rendered text never matches /\d+%|coefficient|threshold|cap of \d|multiplier/i
});

test('NO scary copy across all rendered facts', () => {
  // assert /couldn't|try again|failed/i not present
});
```

Run → FAIL.

### Task B.7.4: Implement `ConfidenceDetailsSheet.tsx`

**blockedBy:** B.7.3

**File:** `SmartCompareApp/src/components/results/ConfidenceDetailsSheet.tsx` (new)

- Bottom sheet using existing pattern (reference: `SmartCompareApp/src/components/DemographicsBottomSheet.tsx` for animation/lift/dim style — peers reference this in Section A's plan section as the canonical bottom-sheet pattern).
- Props: `visible, leg ('price' | 'reviews' | 'specs'), details (per-leg string[]), onClose`.
- Render heading `t('results.confidence.sheet.title')` ("What we know"), list of factual lines, close button.
- Each line is a `<Text>{fact}</Text>` — backend provides the strings (Section A spec emits these via new `scoring_v2.confidence_details: { price: string[], reviews: string[], specs: string[] }`). Frontend NEVER composes the strings.
- NO threshold numbers — backend invariant per spec § 5b. Frontend defends with a regex test (B.7.3).

**Commit:** `feat(results): ConfidenceDetailsSheet bottom sheet with 2-3 factual lines per leg`.

### Task B.7.5: parseSourceMethod helper — failing test

**blockedBy:** B.1.2

**File:** `SmartCompareApp/__tests__/services/sourceMethod.test.ts`

```typescript
import { parseSourceMethod, anyEstimated } from '../../src/services/sourceMethod';

test.each([
  ['local_bhd', 'Direct local listing'],
  ['converted_usd', 'Local listing'],
  ['page_scrape', 'Retailer page'],
  ['page_scrape_rendered', 'Retailer page'],
  ['firecrawl', 'Retailer page'],
  ['scrapedo_rendered', 'Retailer page'],
])('parseSourceMethod(%s) returns approved phrasing %s', (method, expected) => {
  expect(parseSourceMethod(method as any)).toBe(expected);
});

test('parseSourceMethod("estimated") returns null (caller must suppress)', () => {
  expect(parseSourceMethod('estimated')).toBeNull();
});

test('anyEstimated returns true when ANY product has estimated source', () => {
  const products = [{ price: { source_method: 'firecrawl' } }, { price: { source_method: 'estimated' } }] as any;
  expect(anyEstimated(products)).toBe(true);
});

test('anyEstimated returns false when no product has estimated source', () => {
  const products = [{ price: { source_method: 'firecrawl' } }, { price: { source_method: 'local_bhd' } }] as any;
  expect(anyEstimated(products)).toBe(false);
});

test('parseSourceMethod NEVER returns forbidden words', () => {
  const all: any[] = ['local_bhd', 'converted_usd', 'page_scrape', 'page_scrape_rendered', 'firecrawl', 'scrapedo_rendered'];
  const forbidden = /\b(estimated|reference price|indicative|approximate|تقدير|مُقدَّر)\b/i;
  for (const m of all) {
    const phrase = parseSourceMethod(m);
    expect(phrase).not.toBeNull();
    expect(phrase!).not.toMatch(forbidden);
  }
});
```

Run → FAIL.

### Task B.7.6: Implement `sourceMethod.ts` helper

**blockedBy:** B.7.5

**File:** `SmartCompareApp/src/services/sourceMethod.ts` (new)

```typescript
import type { Product, SourceMethod } from '../types';

const APPROVED: Partial<Record<SourceMethod, string>> = {
  local_bhd: 'Direct local listing',
  converted_usd: 'Local listing',
  page_scrape: 'Retailer page',
  page_scrape_rendered: 'Retailer page',
  firecrawl: 'Retailer page',
  scrapedo_rendered: 'Retailer page',
  // 'estimated' deliberately NOT mapped — returns null
};

export function parseSourceMethod(method: SourceMethod | undefined): string | null {
  if (!method) return null;
  return APPROVED[method] ?? null;
}

export function anyEstimated(products: Pick<Product, 'price'>[]): boolean {
  return products.some((p) => p.price?.source_method === 'estimated');
}
```

i18n keys NOT used here — strings live in the helper because they are short, single-purpose, and not user-editable language-pack content (callers may localize via t() later if needed; defer). NOTE: re-evaluate if AR localization becomes required; spec § 5c suggests these strings rarely surface (Price pill hidden when estimated).

Run jest → all cases pass.

**Commit:** `feat(services): parseSourceMethod helper returns null on estimated (caller suppresses UI element)`.

---

## B.8 — ResultsScreen integration

**Spec:** Sections 1b (FactualVerdict line1/line2 contract verification), 2d/2e (hero adaptations), 5b (replace legacy banner with pills), 5c (hide Price pill on estimated), 5d (drop overall single-word label), 7a (personalization chip below verdict).

### Task B.8.1: Failing integration test — confidence banner removed, pills present

**blockedBy:** B.7.4, B.7.6

**File:** `SmartCompareApp/__tests__/screens/ResultsScreen.confidence.integration.test.tsx`

```typescript
test('legacy single-word confidence banner is gone (spec § 5d)', () => {
  const result = mockResultWithScoringV2({ scoring_v2: { overall_score: { product_a: 80, product_b: 75 }, dimensions: [/*...*/], confidence: { price: 'strong', reviews: 'strong', specs: 'strong' } } });
  const { queryByText } = render(<ResultsScreen route={{ params: { result } }} />);
  expect(queryByText(/high confidence data/i)).toBeNull();
  expect(queryByText(/medium confidence data/i)).toBeNull();
});

test('ConfidencePills row renders when scoring_v2.confidence present', () => {
  // assert testID present, 3 pills visible
});

test('Price pill suppressed when any product source_method=estimated (spec § 5c)', () => {
  const result = mockResultWithScoringV2({
    products: [{ price: { source_method: 'estimated' } }, { price: { source_method: 'firecrawl' } }],
    scoring_v2: { confidence: { price: 'strong', reviews: 'strong', specs: 'strong' } },
  });
  const { queryByText } = render(<ResultsScreen route={{ params: { result } }} />);
  expect(queryByText('Price')).toBeNull();
  expect(queryByText('Reviews')).toBeTruthy();
  expect(queryByText('Specs')).toBeTruthy();
});

test('no provenance copy ANYWHERE on Results screen (spec § 5c forbidden vocab)', () => {
  // render full results screen, then assert no text matches /estimated|reference price|indicative|تقدير/i
});
```

Run → FAIL.

### Task B.8.2: Remove legacy confidence banner, wire ConfidencePills

**blockedBy:** B.8.1

**File:** `SmartCompareApp/src/screens/ResultsScreen.tsx`

- Delete the block at `ResultsScreen.tsx:737-761` (confidenceBanner View + AlertCircle + Shield).
- Remove now-unused styles `confidenceBanner`, `confidenceText` from the stylesheet at the bottom of the file.
- Remove now-unused i18n key lookups for `results.confidence.high/medium/low` IN this file (the keys themselves stay in i18n for now to avoid churning translations — they're orphaned and can be deleted in a future cleanup if all references are gone).
- Import `ConfidencePills`, `ConfidenceDetailsSheet`, `anyEstimated`.
- Inside the scoring_v2 section (around `ResultsScreen.tsx:1078`), render `<ConfidencePills confidence={scoring_v2.confidence_legs} hidePricePill={anyEstimated(products)} onPillPress={(leg) => setSheetLeg(leg)} />` ABOVE the HeroRings (spec § 5b places pills near hero).
- Manage local state `[sheetLeg, setSheetLeg] = useState<'price'|'reviews'|'specs'|null>(null)`.
- Render `<ConfidenceDetailsSheet visible={!!sheetLeg} leg={sheetLeg!} details={scoring_v2.confidence_details} onClose={() => setSheetLeg(null)} />` once at end of scroll view (or modal-style top-level).

Run jest → integration tests pass.

**Commit:** `refactor(results): replace confidence banner with 3-pill row + details sheet, suppress Price pill when estimated`.

### Task B.8.3: Failing test — personalization chip below verdict

**blockedBy:** B.1.2, B.2.2

**File:** `SmartCompareApp/__tests__/components/PersonalizationChip.test.tsx`

```typescript
import { PersonalizationChip } from '../../src/components/results/PersonalizationChip';

test('renders chip with 3 arrows when applied_shifts has 3+ entries', () => {
  const shifts = [
    { dim_display: 'performance', direction: 'up' as const },
    { dim_display: 'build', direction: 'up' as const },
    { dim_display: 'brand_recognition', direction: 'down' as const },
  ];
  const { getByText } = render(<PersonalizationChip appliedShifts={shifts} />);
  // single line, contains chip_template substring
  expect(getByText(/Weighted/)).toBeTruthy();
  expect(getByText(/↑/)).toBeTruthy();
  expect(getByText(/↓/)).toBeTruthy();
});

test('caps to 3 arrows even when more shifts emitted', () => {
  const shifts = [/* 5 shifts */];
  // assert only 3 visible
});

test('hidden when applied_shifts empty', () => {
  const { container } = render(<PersonalizationChip appliedShifts={[]} />);
  expect(container.children.length).toBe(0);
});

test('hidden when undefined (no priorities set upstream)', () => {
  const { container } = render(<PersonalizationChip appliedShifts={undefined} />);
  expect(container.children.length).toBe(0);
});

test('NO percentages, NO coefficient leaks (spec § 7a + no-backend-internals rule)', () => {
  const shifts = [{ dim_display: 'performance', direction: 'up' as const }];
  const { container } = render(<PersonalizationChip appliedShifts={shifts} />);
  const text = JSON.stringify(container);
  expect(text).not.toMatch(/\d+%/);
  expect(text).not.toMatch(/coefficient|weight: \d|cap of/i);
});
```

Run → FAIL.

### Task B.8.4: Implement `PersonalizationChip.tsx`

**blockedBy:** B.8.3

**File:** `SmartCompareApp/src/components/results/PersonalizationChip.tsx` (new)

```typescript
interface Props {
  appliedShifts: Array<{ dim_display: string; direction: 'up' | 'down' }> | undefined;
  testID?: string;
}

export function PersonalizationChip({ appliedShifts, testID = 'personalization-chip' }: Props) {
  const { t } = useTranslation();
  if (!appliedShifts || appliedShifts.length === 0) return null;
  const top3 = appliedShifts.slice(0, 3);
  const arrows = top3.map((s) =>
    t(s.direction === 'up' ? 'results.personalization.arrow_up' : 'results.personalization.arrow_down', { dim: s.dim_display.replace(/_/g, ' ') }),
  ).join(' · ');
  return (
    <View style={styles.chip} testID={testID}>
      <Text style={styles.text}>{t('results.personalization.chip_template', { arrows })}</Text>
    </View>
  );
}
```

Style: single-line chip-style View, muted background (`colors.bg.secondary`), `typography.caption`, marginTop spacing.sm below verdict text. NO tap handler, NO expand.

Run jest → 5 tests pass.

**Commit:** `feat(results): PersonalizationChip single-line below verdict with up to 3 arrows`.

### Task B.8.5: Wire PersonalizationChip into ResultsScreen

**blockedBy:** B.8.4

**File:** `SmartCompareApp/src/screens/ResultsScreen.tsx`

In the "Why we picked this" verdict section (around `ResultsScreen.tsx:763-770`), AFTER the `verdictText` + `tradeoffNote`, append:
```tsx
<PersonalizationChip appliedShifts={scoring_v2?.personalization?.applied_shifts} />
```

`CohortBadge` continues to live in its own slot (spec § 7d) — DO NOT merge.

Run snapshot of ResultsScreen verdict section → pass.

**Commit:** `feat(results): mount PersonalizationChip below verdict (spec § 7a)`.

### Task B.8.6: FactualVerdict contract verification — failing snapshot

**blockedBy:** A.1.b (backend wires line1/line2; frontend just verifies once available)

**File:** `SmartCompareApp/__tests__/components/FactualVerdict.bundle_c.test.tsx`

```typescript
test('renders line1 + line2 when both present (spec § 1b backend now emits)', () => {
  const { getByText } = render(<FactualVerdict line1="iPhone 16 — BHD 30 less, 0.2★ higher" line2="If you want larger battery, Galaxy S25 lasts +8h" />);
  expect(getByText(/BHD 30 less/)).toBeTruthy();
  expect(getByText(/larger battery/)).toBeTruthy();
});

test('renders only line1 when line2 empty', () => {
  const { getByText, queryByText } = render(<FactualVerdict line1="iPhone 16 — BHD 30 less" line2="" />);
  expect(getByText(/BHD 30 less/)).toBeTruthy();
  // line2 collapses
});

test('contract violation node when evaluative vocab leaks (existing FactualVerdict guard)', () => {
  // existing behavior already enforced — re-verify after Bundle C wiring
});
```

Component already supports the contract per `FactualVerdict.tsx:47`. This task is verification-only — confirm passing snapshot after backend wires the fields.

**Commit:** `test(verdict): Bundle C contract verification — FactualVerdict renders line1/line2 once backend emits`.

---

## B.9 — Cleanup + theme regression sanity

### Task B.9.1: Audit Results screen for legacy single-word `confidence.overall` references

**blockedBy:** B.8.2

`grep -nR "confidence.overall" SmartCompareApp/src/` — confirm no remaining references after B.8.2. If found in other components/screens, log as orphaned and remove or scope-out (no spec coverage for those).

**Commit:** `chore(results): remove dead confidence.overall references` (if any).

### Task B.9.2: TypeScript regression sweep

**blockedBy:** B.8.5

```bash
cd SmartCompareApp && npx tsc --noEmit
```

Zero errors required. Fix any cascade caused by `BudgetValue` literal expansion or new `Dimension.confidence` typing.

**Commit:** `chore(types): close any tsc gaps from Bundle C frontend additions` (if any).

### Task B.9.3: Forbidden-words sweep on rendered Results screen

**blockedBy:** B.8.5

**File:** `SmartCompareApp/__tests__/screens/ResultsScreen.forbidden_words.test.tsx` (new)

```typescript
test('no forbidden EN copy on rendered Results screen', () => {
  const result = mockFullResult();
  const { container } = render(<ResultsScreen route={{ params: { result } }} />);
  const text = JSON.stringify(container);
  expect(text).not.toMatch(/\b(couldn't|try again|Failed to|estimated|reference price|indicative)\b/i);
});

test('no forbidden AR copy on rendered Results screen with AR locale', () => {
  // mount with i18n locale=ar and re-test against AR forbidden patterns
  expect(text).not.toMatch(/(تعذر|فشل|تقدير|مُقدَّر)/);
});
```

Run → both pass. Captures the absorbed-rules-during-brainstorm anchor (spec § 0).

**Commit:** `test(results): forbidden-words sweep on rendered screen (EN + AR)`.

---

## B.10 — Snapshot baseline + final coverage

### Task B.10.1: Generate full snapshot baseline

**blockedBy:** all of B.3–B.8 complete

Run:
```bash
cd SmartCompareApp && npx jest --updateSnapshot src/components/results src/components/BudgetPicker src/screens/onboarding/Step09Budget src/screens/ResultsScreen
```

Review snapshot diffs; commit the baseline.

**Commit:** `test(bundle-c): baseline snapshots for DimensionBars hero+expand, ConfidencePills 3-leg, PersonalizationChip, BudgetPicker 5-tier, Step09Budget 5-tier, FactualVerdict, ResultsScreen scoring_v2 integration`.

### Task B.10.2: Coverage gate

**blockedBy:** B.10.1

```bash
cd SmartCompareApp && npx jest --coverage src/components/results src/services/sourceMethod
```

Verify ≥80% line coverage on each new file. If gaps, add tests for uncovered branches (typical gaps: error states, edge case props).

**Commit:** `test(bundle-c): coverage gate ≥80% on new components + sourceMethod helper`.

---

## Dependency chain summary

```
B.1.1 → B.1.2 (types)
   ↓
B.2.1 → B.2.2 → B.2.3 (i18n)
   ↓
B.3.1 → B.3.2 → B.3.3 (BudgetPicker)
B.4.1 → B.4.2 → B.4.3 → B.4.4 (Step09Budget + EditPrefs)
   ↓ (independent of each other; parallelize)
B.5.1 → B.5.2 → B.5.3 → B.5.4 → B.5.5 → B.5.6 → B.5.7 → B.5.8 → B.5.9 → B.5.10 → B.5.11 (DimensionBars)
B.6.1 → B.6.2 → B.6.3 (Hero adaptation)
B.7.1 → B.7.2 → B.7.3 → B.7.4 → B.7.5 → B.7.6 (Confidence pills + sourceMethod)
   ↓
B.8.1 → B.8.2 → B.8.3 → B.8.4 → B.8.5 → B.8.6 (ResultsScreen integration)
   ↓
B.9.1 → B.9.2 → B.9.3 (cleanup)
   ↓
B.10.1 → B.10.2 (final snapshot + coverage gate)
```

Parallel-safe lanes (after B.1.2 + B.2.2 land):
- B.3 + B.4 (picker work) ‖ B.5 (DimensionBars) ‖ B.6 (Hero adaptation) ‖ B.7 (Confidence pills + sourceMethod).
- All converge at B.8 (ResultsScreen integration).

Total Section B task count: **32 tasks** across 10 sub-sections (B.1–B.10). Bite-sized: each <1 hour ideal; B.5 has the largest sub-chain (11 tasks) reflecting the DimensionBars overhaul scope per spec § 6.


---

# SECTION C — test-bundle-c tasks

**Role:** Test planner. Writes failing tests FIRST against the design spec, then verifies implementation tasks (A.x / B.x) make them green. Owns coverage gates + regression discipline. Idle behavior: when waiting on impl, expand edge-case tests + run coverage reports.

**Owner files (absolute paths from repo root):**

Backend tests (pytest):
- `tests/test_scoring_calibration.py` — extend (existing file: calibration band, missing-data, fabricated-defaults removal)
- `tests/test_scoring_service.py` — extend (existing file: priority-driven value formula, omission rules)
- `tests/test_scoring_v2_models.py` — extend (existing file: Pydantic Literal expansion for `BudgetValue` + new fields)
- `tests/test_dimensions_builder.py` — extend (existing file: `build_dimensions_v2` adapter, silent omission)
- `tests/test_personalization.py` — extend (existing file: `applied_shifts[]` direction-only contract)
- `tests/test_extraction_prompt.py` — extend (existing file: 3-tier fallback prompt, weird-comparison flag, `budget_mismatch`)
- `tests/test_structured_comparison_service.py` — extend (existing file: weird detector + 3-tier orchestration)
- `tests/test_tier_detection.py` — NEW (5-tier per-category map, geometric-mean sub-scale, `_detect_price_tier`)
- `tests/test_value_math.py` — NEW (priority-driven coefficients, delta_text, value_match, cross-tier framing)
- `tests/test_confidence_thresholds.py` — NEW (5a loosened thresholds; Price-pill-hidden invariant)
- `tests/test_bundle_c_integration.py` — NEW (6-category cold-cache probe suite; `@pytest.mark.integration`)
- `tests/test_security_regression.py` — extend (no new endpoints; only verify no collision and add invariants on existing routes)

Frontend tests (Jest / RNTL):
- `SmartCompareApp/__tests__/DimensionBars.test.tsx` — NEW (hero+expand, omission silent, "—" last-resort row)
- `SmartCompareApp/__tests__/ConfidencePills.test.tsx` — NEW (3-leg pill row, Price-pill-hidden when any product estimated, tap-reveal copy backtest)
- `SmartCompareApp/__tests__/PersonalizationChip.test.tsx` — NEW (arrows-only render, hidden when no shifts, i18n EN+AR)
- `SmartCompareApp/__tests__/BudgetPicker.test.tsx` — NEW or extend (5-tier render, both flag states)
- `SmartCompareApp/__tests__/ResultsScreen.test.tsx` — extend (delta-hero in value row; weird-comparison renders `—` hero; no banners anywhere)
- `SmartCompareApp/src/components/results/__snapshots__/` — frontend snapshots committed alongside

**Coverage targets:**
- 80% line coverage on touched files in `app/services/scoring_service.py`, `app/services/extraction_service.py`, `app/services/response_builder.py`, `app/services/structured_comparison_service.py`.
- **90% line coverage on new scoring formulas:** `_compute_value_score`, `_detect_price_tier`, `_compute_raw_scores`, `calibrate_score`, `_compute_applied_shifts`, `_classify_comparison_quality`.
- 80% on new frontend components: `DimensionBars`, `ConfidencePills`, `PersonalizationChip`, `BudgetPicker`.
- 100% branch coverage on `value_match` classification (4 states) and `comparison_quality` classifier (3 states).

**Pre-flight assumption:** All Section C tasks can begin BEFORE Section A/B impl is merged — tests are written failing first against the design spec. Where a task says `blockedBy: [A.x impl]`, that means the test STAYS RED until that impl lands; the test itself can still be written and committed.

**Critical assertion invariants every Section C test MUST enforce when applicable** (write these as reusable helper functions in a new `tests/_bundle_c_helpers.py`):

```python
# tests/_bundle_c_helpers.py
FORBIDDEN_UI_STRINGS_EN = {
    "estimated", "estimate", "reference", "indicative",
    "couldn't", "try again", "Failed to",
}
FORBIDDEN_UI_STRINGS_AR = {"تقدير", "مُقدَّر", "تعذر", "فشل"}

def assert_no_forbidden_strings(rendered_text: str) -> None:
    """Backtest rendered UI string against forbidden vocabulary."""
    lower = rendered_text.lower()
    for term in FORBIDDEN_UI_STRINGS_EN:
        assert term.lower() not in lower, f"Forbidden UI string '{term}' found"
    for term in FORBIDDEN_UI_STRINGS_AR:
        assert term not in rendered_text, f"Forbidden AR string '{term}' found"

def assert_no_magnitude_fields(personalization_payload: dict) -> None:
    """Backend internals (coefficients, caps, percentages) must NEVER reach API."""
    forbidden_keys = {"magnitude", "shift_pct", "weight_delta", "cap_pct",
                      "coefficient", "raw_shift", "shift_value"}
    def _walk(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                assert k not in forbidden_keys, f"Forbidden magnitude key '{k}' in personalization"
                _walk(v)
        elif isinstance(obj, list):
            for item in obj: _walk(item)
    _walk(personalization_payload)
```

Frontend equivalent helper in `SmartCompareApp/__tests__/_bundle_c_helpers.ts`:

```typescript
export const FORBIDDEN_UI_STRINGS = [
  /estimated/i, /estimate/i, /reference/i, /indicative/i,
  /couldn't/i, /try again/i, /Failed to/i,
  /تقدير/, /مُقدَّر/, /تعذر/, /فشل/,
];
export function expectNoForbiddenStrings(renderedTree: ReactTestInstance) {
  const text = JSON.stringify(renderedTree.toJSON());
  for (const re of FORBIDDEN_UI_STRINGS) expect(text).not.toMatch(re);
}
export function expectNoBanner(queryByRole: any, queryByLabelText: any) {
  // Banner-like elements that we explicitly forbid (per project rule #1)
  expect(queryByRole('alert')).toBeNull();
  expect(queryByLabelText(/info banner/i)).toBeNull();
  expect(queryByLabelText(/warning banner/i)).toBeNull();
  expect(queryByLabelText(/insufficient.*data/i)).toBeNull();
}
```

---

## C.0 — Bootstrap

### Task C.0.1: Create assertion helpers

**Files:**
- `tests/_bundle_c_helpers.py` (the snippet above)
- `SmartCompareApp/__tests__/_bundle_c_helpers.ts` (the snippet above)

**Step 1:** Write both files exactly per the snippets above.

**Step 2:** Add minimal smoke test in `tests/test_bundle_c_helpers_smoke.py`:
```python
import pytest
from tests._bundle_c_helpers import assert_no_forbidden_strings, assert_no_magnitude_fields

def test_forbidden_string_detected():
    with pytest.raises(AssertionError, match="estimated"):
        assert_no_forbidden_strings("This price is estimated")

def test_clean_string_passes():
    assert_no_forbidden_strings("Better value for your priority")

def test_magnitude_field_detected():
    with pytest.raises(AssertionError, match="magnitude"):
        assert_no_magnitude_fields({"applied_shifts": [{"magnitude": 0.3}]})

def test_clean_payload_passes():
    assert_no_magnitude_fields({"applied_shifts": [{"dim_display": "performance", "direction": "up"}]})
```

**Step 3:** `pytest tests/test_bundle_c_helpers_smoke.py -v` → all pass.

**Step 4:** Commit: `test(bundle-c): assertion helpers for forbidden UI strings + magnitude leaks`

**blockedBy:** none.

---

## C.1 — Calibration + missing-data tests (spec §2a, 2b, 2c, 2g, 2h)

### Task C.1.1: Test — missing-data floor of 50 REMOVED → None propagation (§2a)

**File:** Append to `tests/test_scoring_calibration.py`.

```python
def test_missing_signal_emits_none_not_default(service):
    """Spec §2a: _compute_raw_scores returns None when signal absent (not MISSING_SCORE=50)."""
    product_no_specs = _make_product(specs={})
    product_full = _make_product()
    raw_a, raw_b = service._compute_raw_scores(product_no_specs, product_full,
                                               category="electronics", weights=...)
    # performance_score depends on processor/ram/storage — absent → None
    assert raw_a.get("performance_score") is None, \
        "Missing specs must propagate None, not MISSING_SCORE"
    assert raw_b.get("performance_score") is not None, \
        "Populated specs still produce numeric score"

def test_legacy_missing_score_constant_still_exists():
    """MISSING_SCORE=50 constant kept for backwards-compat (legacy breakdown), but
    new _compute_raw_scores must NOT inject it. Constant should be unused in v2 path."""
    from app.services.scoring_service import MISSING_SCORE
    assert MISSING_SCORE == 50  # constant value retained
```

**blockedBy:** A.x — spec §2a impl (kill missing-data floor in `_compute_raw_scores`).

**Coverage:** 90% on `_compute_raw_scores` branches.

---

### Task C.1.2: Test — calibration band intact for populated signals (§2c)

**File:** Append to `tests/test_scoring_calibration.py`.

```python
@pytest.mark.parametrize("raw_signal,expected_min,expected_max", [
    (0,    60, 60),   # floor clamp
    (40,   60, 69),   # honesty guard zone (raw < 40 → display ≤ 69)
    (50,   60, 95),
    (95,   60, 95),
    (100,  95, 95),   # ceiling clamp
])
def test_calibrate_score_band(service, raw_signal, expected_min, expected_max):
    out = service.calibrate_score(raw_signal)
    assert expected_min <= out <= expected_max

def test_honesty_guard_fires_when_all_raw_below_40(service):
    """Per spec §2c: when all raw_signals < 40, display ≤ 69."""
    raw_dict = {"performance_score": 30, "value_score": 25, "build_quality_score": 35}
    calibrated = service._apply_honesty_guard(raw_dict)
    assert all(v <= 69 for v in calibrated.values())
```

**blockedBy:** A.x — `calibrate_score` unchanged for populated signals (regression check only).

**Coverage:** 90% on `calibrate_score` + `_apply_honesty_guard` branches.

---

### Task C.1.3: Test — no fabricated defaults (`or <number>` audit) (§2g)

**File:** Append to `tests/test_scoring_service.py`.

```python
def test_dim_value_no_fabricated_rating(service):
    """Spec §2g: scoring_service.py:1247 `ra = a.get('rating') or 4.0` REMOVED.
    Missing rating must propagate as None to value formula."""
    product_no_rating = _make_product(rating=None)
    product_full = _make_product(rating=4.5)
    val = service._dim_value(product_no_rating, product_full, category="electronics",
                             priorities=["quality"])
    # When rating is None, value_score for product A must be None (not fabricated default)
    assert val["score_a"] is None, "Missing rating must propagate, not fabricate 4.0"

def test_no_or_zero_defaults_in_price_math(service):
    """Audit: `price or 0.1`, `warranty or 1` patterns REMOVED."""
    product_no_price = _make_product()
    product_no_price["price"] = {"amount": None, "currency": "BHD"}
    product_full = _make_product()
    raw_a, raw_b = service._compute_raw_scores(product_no_price, product_full,
                                               category="electronics", weights=...)
    # value_score requires price — must be None when price absent
    assert raw_a.get("value_score") is None

def test_audit_no_silent_or_default_patterns():
    """Static check — scan scoring_service.py source for forbidden `or 4.0`, `or 0.1` patterns."""
    import re
    from pathlib import Path
    src = Path("app/services/scoring_service.py").read_text(encoding="utf-8")
    # These were the documented offenders in spec §2g
    forbidden_patterns = [
        r"\.get\(['\"]rating['\"]\)\s+or\s+4",
        r"price\s+or\s+0\.\d",
        r"warranty\s+or\s+1",
    ]
    for pat in forbidden_patterns:
        assert not re.search(pat, src), \
            f"Fabricated default pattern still present: {pat!r}"
```

**blockedBy:** A.x — remove `or <number>` defaults across `_dim_value`, `_dim_*` builders.

**Coverage:** Static-source assertion covers every removal. 100% pattern coverage.

---

### Task C.1.4: Test — silent omission in `dimensions[]` (§2h)

**File:** Append to `tests/test_dimensions_builder.py`.

```python
def test_dimensions_silently_omits_when_both_products_null():
    """Spec §2h: dims with score_a===null AND score_b===null are silently OMITTED
    from dimensions[] entirely (not present-with-null)."""
    from app.services.response_builder import build_dimensions_v2
    raw_a = {"performance_score": None, "value_score": 80, "build_quality_score": None}
    raw_b = {"performance_score": None, "value_score": 75, "build_quality_score": None}
    dims = build_dimensions_v2(raw_a, raw_b, category="electronics")
    dim_keys = {d["dim_key"] for d in dims}
    assert "performance_score" not in dim_keys, "Dim must be silently omitted"
    assert "build_quality_score" not in dim_keys
    assert "value_score" in dim_keys

def test_dimension_with_one_null_still_emitted_or_silent():
    """When only ONE product has null — per spec, emit dim with that product null,
    OR silently omit. Both behaviors acceptable per design. Test current contract."""
    raw_a = {"performance_score": 80, "value_score": 80}
    raw_b = {"performance_score": None, "value_score": 75}
    dims = build_dimensions_v2(raw_a, raw_b, category="electronics")
    # Find performance_score dim
    perf = next((d for d in dims if d["dim_key"] == "performance_score"), None)
    if perf is not None:
        assert perf["score_b"] is None  # explicit null, not fabricated default
```

**blockedBy:** A.x — `build_dimensions_v2` refactor (spec §6a + §2h).

**Coverage:** 90% on `build_dimensions_v2`.

---

### Task C.1.5: Test — last-resort "—" row when single dim survives (§2b)

**File:** Append to `tests/test_dimensions_builder.py`.

```python
def test_last_resort_emit_null_dim_when_both_missing_but_required(service):
    """Spec §2b: rare case — when ALL non-omittable dims have both products null,
    backend emits ONE null dim so frontend can render the muted '—' row.
    Frontend logic: if dimensions[].length === 1 && score_a===null && score_b===null,
    render the last-resort row."""
    # Scenario: a category with only one non-negotiable dim, both products lack signal
    # even after Tier 3 fallback
    raw_a = {"sole_dim": None}
    raw_b = {"sole_dim": None}
    dims = build_dimensions_v2(raw_a, raw_b, category="other",
                                last_resort_dim="sole_dim")
    assert len(dims) == 1
    assert dims[0]["dim_key"] == "sole_dim"
    assert dims[0]["score_a"] is None
    assert dims[0]["score_b"] is None
    assert dims[0]["caption"] == "Limited data"
```

**blockedBy:** A.x — implement last-resort fallback in `build_dimensions_v2`.

**Coverage:** Branch coverage for the "all-omitted-would-leave-zero-dims" case.

---

## C.2 — Weird comparison detector tests (spec §2e)

### Task C.2.1: Backend — `comparison_quality` classifier (3 states)

**File:** `tests/test_structured_comparison_service.py` — append.

```python
import pytest
from app.services.structured_comparison_service import _classify_comparison_quality

@pytest.mark.parametrize("scenario,expected", [
    # category mismatch → weird
    (dict(cat_a="electronics", cat_b="fragrances", spec_coverage_a=1.0,
          spec_coverage_b=1.0, price_a=100, price_b=120), "weird"),
    # >50% specs missing post-Tier-3 → weird
    (dict(cat_a="electronics", cat_b="electronics", spec_coverage_a=0.3,
          spec_coverage_b=1.0, price_a=100, price_b=120), "weird"),
    # 10× price spread → weird
    (dict(cat_a="electronics", cat_b="electronics", spec_coverage_a=1.0,
          spec_coverage_b=1.0, price_a=10, price_b=200), "weird"),
    # Moderate spec gap → weak
    (dict(cat_a="electronics", cat_b="electronics", spec_coverage_a=0.6,
          spec_coverage_b=0.9, price_a=100, price_b=200), "weak"),
    # All normal → normal
    (dict(cat_a="electronics", cat_b="electronics", spec_coverage_a=1.0,
          spec_coverage_b=0.9, price_a=100, price_b=140), "normal"),
])
def test_comparison_quality_classifier(scenario, expected):
    assert _classify_comparison_quality(**scenario) == expected

def test_comparison_quality_in_response_payload():
    """Spec §2e: backend emits `comparison_quality` field in response."""
    # Integration-style: mock comparison call, assert response.metadata.comparison_quality present
    ...
```

**blockedBy:** A.x — implement `_classify_comparison_quality` + wire into response.

**Coverage:** 100% branch on the 3-class state machine.

---

### Task C.2.2: Verdict prompt receives the flag (no forced winner when weird)

**File:** Append to `tests/test_extraction_prompt.py`.

```python
def test_weird_flag_forwarded_to_verdict_prompt(monkeypatch):
    """Spec §2e: when comparison_quality='weird', verdict prompt rewrites
    winner_declaration to non-forced framing."""
    from app.services.extraction_service import build_verdict_prompt
    prompt = build_verdict_prompt(products=[...], comparison_quality="weird")
    assert "different purposes" in prompt or "no forced winner" in prompt.lower()
    assert "weird" in prompt.lower() or "cross-category" in prompt.lower()

def test_normal_flag_keeps_winner_framing():
    prompt = build_verdict_prompt(products=[...], comparison_quality="normal")
    assert "different purposes" not in prompt
```

**blockedBy:** A.x — `build_verdict_prompt` accepts `comparison_quality` arg.

**Coverage:** Snapshot diff between normal/weak/weird prompt outputs.

---

### Task C.2.3: Frontend — weird hero renders `—`, no banner

**File:** `SmartCompareApp/__tests__/ResultsScreen.test.tsx` — append.

```typescript
import { render } from '@testing-library/react-native';
import { expectNoBanner, expectNoForbiddenStrings } from './_bundle_c_helpers';
import ResultsScreen from '../src/screens/ResultsScreen';

test('weird comparison renders hero overall as em-dash', () => {
  const mockResponse = {
    metadata: { comparison_quality: 'weird' },
    scoring: { products: [{ overall_score: null }, { overall_score: null }] },
    dimensions: [{ dim_key: 'value_score', score_a: 70, score_b: 65 }],
    // ...
  };
  const { getByLabelText, queryByRole, queryByLabelText } = render(<ResultsScreen response={mockResponse} />);
  expect(getByLabelText('hero-overall-a')).toHaveTextContent('—');
  expect(getByLabelText('hero-overall-b')).toHaveTextContent('—');
  // CRITICAL: NO banner of any kind (per project rule #1)
  expectNoBanner(queryByRole, queryByLabelText);
});

test('weird DimensionBars renders only signal-bearing dims', () => {
  const mockResponse = {
    metadata: { comparison_quality: 'weird' },
    dimensions: [
      { dim_key: 'value_score', score_a: 70, score_b: 65 },  // signal-bearing
      // performance_score etc are SILENTLY OMITTED — never reach frontend
    ],
  };
  const { queryByLabelText, toJSON } = render(<DimensionBars dimensions={mockResponse.dimensions} />);
  expect(queryByLabelText(/performance/i)).toBeNull();
  expect(queryByLabelText(/value/i)).toBeTruthy();
  expectNoForbiddenStrings(toJSON());
});
```

**blockedBy:** B.x — ResultsScreen weird rendering; DimensionBars uses dimensions[] adapter from §6a.

**Coverage:** Snapshot for weird state.

---

## C.3 — 3-tier spec fallback tests (spec §2f)

### Task C.3.1: Non-negotiable vs preferred classification per category

**File:** Append to `tests/test_extraction_prompt.py`.

```python
from app.services.extraction_service import (
    NON_NEGOTIABLE_FIELDS_BY_CATEGORY,
    PREFERRED_FIELDS_BY_CATEGORY,
)

# Table from spec §2f
EXPECTED_NON_NEGOTIABLE = {
    "electronics": {"battery", "processor", "ram", "rear_camera"},
    "supplements": {"dosage", "form"},
    "fragrances": {"concentration", "longevity"},
    "fashion": {"material"},
    "skincare": {"volume", "ingredients"},
    "haircare": {"volume", "ingredients"},
    "makeup": {"volume", "shade_range"},
    "grocery": {"weight", "ingredients"},
    "other": set(),  # all preferred
}

@pytest.mark.parametrize("category,expected", list(EXPECTED_NON_NEGOTIABLE.items()))
def test_non_negotiable_fields_per_category(category, expected):
    assert set(NON_NEGOTIABLE_FIELDS_BY_CATEGORY[category]) == expected
```

**blockedBy:** A.x — define `NON_NEGOTIABLE_FIELDS_BY_CATEGORY` + `PREFERRED_FIELDS_BY_CATEGORY` in `extraction_service.py`.

**Coverage:** 100% — every category tested.

---

### Task C.3.2: Tier 2 fires only when non-negotiables remain blank after Tier 1

**File:** Append to `tests/test_extraction_prompt.py`.

```python
@pytest.mark.asyncio
async def test_tier2_skipped_when_non_negotiables_filled(mock_serper, mock_openai):
    """Spec §2f: Tier 2 (targeted Serper+GPT-mini) fires ONLY when Tier 1
    leaves non-negotiable fields blank."""
    from app.services.extraction_service import resolve_specs_with_tiered_fallback
    # Tier 1 fills all electronics non-negotiables
    tier1_result = {"battery": "3274 mAh", "processor": "A17", "ram": "8 GB",
                    "rear_camera": "48 MP"}
    result, telemetry = await resolve_specs_with_tiered_fallback(
        query="iPhone 16", category="electronics", tier1_specs=tier1_result
    )
    assert telemetry["tier2_called"] is False
    assert telemetry["tier3_called"] is False

@pytest.mark.asyncio
async def test_tier2_fires_when_non_negotiable_missing(mock_serper, mock_openai):
    tier1_result = {"battery": "3274 mAh"}  # missing processor, ram, rear_camera
    result, telemetry = await resolve_specs_with_tiered_fallback(
        query="iPhone 16", category="electronics", tier1_specs=tier1_result
    )
    assert telemetry["tier2_called"] is True
    assert telemetry["tier2_fields_queried"] == ["processor", "ram", "rear_camera"]
```

**blockedBy:** A.x — implement `resolve_specs_with_tiered_fallback`.

**Coverage:** Branch coverage on tier-skip logic.

---

### Task C.3.3: Tier 3 fires only when non-negotiables remain blank after Tier 2

**File:** Append to `tests/test_extraction_prompt.py`.

```python
@pytest.mark.asyncio
async def test_tier3_fires_only_after_tier2_exhausted(mock_serper, mock_openai):
    tier1_result = {}
    mock_serper.return_value = {}  # Tier 2 also returns nothing
    result, telemetry = await resolve_specs_with_tiered_fallback(
        query="obscure product", category="electronics", tier1_specs=tier1_result
    )
    assert telemetry["tier2_called"] is True
    assert telemetry["tier3_called"] is True

@pytest.mark.asyncio
async def test_tier3_skipped_when_tier2_fills_gaps(mock_serper, mock_openai):
    tier1_result = {"battery": "3274 mAh"}
    mock_serper.return_value = {"processor": "A17", "ram": "8 GB", "rear_camera": "48 MP"}
    result, telemetry = await resolve_specs_with_tiered_fallback(...)
    assert telemetry["tier3_called"] is False
```

**blockedBy:** A.x — Tier 3 GPT-4o knowledge synthesis.

**Coverage:** 100% branch on `tier3_called` logic.

---

### Task C.3.4: Wall-time stays inside `STREAM_HARD_CAP_SECONDS` budget

**File:** Append to `tests/test_extraction_prompt.py`.

```python
@pytest.mark.asyncio
async def test_3tier_fallback_within_stream_hard_cap(mock_serper_slow, mock_openai_slow):
    """Spec §2f: Tier 2 + Tier 3 combined wall-time must stay inside STREAM_HARD_CAP_SECONDS=25.
    Tier 2 budget: 4s. Tier 3 budget: 3s. Both can run parallel within post-Phase-1 window."""
    import asyncio, time
    start = time.monotonic()
    result, telemetry = await asyncio.wait_for(
        resolve_specs_with_tiered_fallback(...),
        timeout=8.0  # generous local upper bound; spec says 7s combined max
    )
    elapsed = time.monotonic() - start
    assert elapsed < 8.0, f"3-tier fallback exceeded budget: {elapsed}s"
```

**blockedBy:** A.x — `asyncio.wait_for` wrappers per tier.

**Coverage:** Smoke test for timeout enforcement.

---

### Task C.3.5: `inference_source="model_knowledge"` flag NEVER reaches user-visible response

**File:** Append to `tests/test_extraction_prompt.py`.

```python
@pytest.mark.asyncio
async def test_inference_source_flag_internal_only(mock_serper, mock_openai):
    """Spec §2f: Tier 3 outputs tagged inference_source='model_knowledge' — QA/dashboards only.
    NEVER reaches response.products[].specs or any user-visible field."""
    result, telemetry = await resolve_specs_with_tiered_fallback(...)
    # Internal telemetry sees it
    assert telemetry["tier3_fields"].get("processor", {}).get("inference_source") == "model_knowledge"
    # But user-facing specs dict has no such key
    assert "inference_source" not in result["specs"]
    # And the value is a clean string, not annotated
    assert result["specs"]["processor"] == "A17 Pro"  # not "A17 Pro (estimated)"

@pytest.mark.asyncio
async def test_inference_source_not_in_response_builder_output():
    """Belt-and-braces: response_builder must strip inference_source before serialization."""
    from app.services.response_builder import build_comparison_response
    response = build_comparison_response(
        products=[{"specs": {"processor": "A17"},
                   "_internal": {"processor_inference_source": "model_knowledge"}}],
        ...
    )
    import json
    serialized = json.dumps(response)
    assert "model_knowledge" not in serialized
    assert "inference_source" not in serialized
```

**blockedBy:** A.x — `response_builder` strips internal flags.

**Coverage:** 100% — both layers tested.

---

### Task C.3.6: Live integration probe — end-to-end 3-tier

**File:** Append to `tests/test_bundle_c_integration.py` (created in C.9).

```python
@pytest.mark.live_unit
@pytest.mark.asyncio
async def test_3tier_fallback_live_obscure_product():
    """Live probe: query an obscure electronics product whose specs are unlikely
    in Tier 1. Verify Tier 2 + Tier 3 fill non-negotiables."""
    from app.services.extraction_service import resolve_specs_with_tiered_fallback
    result, telemetry = await resolve_specs_with_tiered_fallback(
        query="Realme GT Master Edition", category="electronics", tier1_specs={}
    )
    # All non-negotiables must be filled
    for field in NON_NEGOTIABLE_FIELDS_BY_CATEGORY["electronics"]:
        assert result["specs"].get(field), f"Non-negotiable {field} still blank"
```

**blockedBy:** A.x — full 3-tier implementation. Marked `@pytest.mark.live_unit` so it runs in live-tier suite (~$0.03).

**Coverage:** End-to-end smoke.

---

## C.4 — Budget tier expansion tests (spec §3)

### Task C.4.1: Per-category `PRICE_TIERS_BY_CATEGORY` table

**File:** `tests/test_tier_detection.py` — NEW.

```python
import pytest
from app.services.scoring_service import (
    PRICE_TIERS_BY_CATEGORY,
    _detect_price_tier,
)

# Table from spec §3e
EXPECTED_TIERS = {
    "electronics": {"budget_max": 100, "mid_max": 400, "premium_max": 800,
                    "luxury_max": 2000},  # top_tier = 2000+
    "supplements": {"budget_max": 11, "mid_max": 30, "premium_max": 60,
                    "luxury_max": None},  # folds
    "fashion": {"budget_max": 30, "mid_max": 150, "premium_max": 500,
                "luxury_max": 2000},
    "fragrances": {"budget_max": 30, "mid_max": 80, "premium_max": 180,
                   "luxury_max": 500},
    "skincare": {"budget_max": 11, "mid_max": 40, "premium_max": 100,
                 "luxury_max": 300},
    "haircare": {"budget_max": 15, "mid_max": 40, "premium_max": 100,
                 "luxury_max": 200},
    "makeup": {"budget_max": 15, "mid_max": 50, "premium_max": 120,
               "luxury_max": 300},
    "grocery": {"budget_max": 5, "mid_max": 15, "premium_max": 50,
                "luxury_max": None},
}

@pytest.mark.parametrize("category,bounds", list(EXPECTED_TIERS.items()))
def test_per_category_breakpoints_loaded(category, bounds):
    cat_tiers = PRICE_TIERS_BY_CATEGORY[category]
    assert cat_tiers["budget"]["max"] == bounds["budget_max"]
    assert cat_tiers["mid"]["max"] == bounds["mid_max"]
    assert cat_tiers["premium"]["max"] == bounds["premium_max"]
    if bounds["luxury_max"] is not None:
        assert cat_tiers["luxury"]["max"] == bounds["luxury_max"]
```

**blockedBy:** A.x — define `PRICE_TIERS_BY_CATEGORY` in `scoring_service.py`.

**Coverage:** 100% — every category breakpoint asserted.

---

### Task C.4.2: `_detect_price_tier` resolution per category

**File:** Append to `tests/test_tier_detection.py`.

```python
@pytest.mark.parametrize("price,category,expected_tier", [
    # electronics
    (50,   "electronics", "budget"),
    (300,  "electronics", "mid"),
    (700,  "electronics", "premium"),
    (1500, "electronics", "luxury"),
    (3000, "electronics", "top_tier"),
    # supplements (fold: luxury+top_tier collapse)
    (5,    "supplements", "budget"),
    (20,   "supplements", "mid"),
    (50,   "supplements", "premium"),
    (100,  "supplements", "luxury"),  # spec §3e: 60+ folds to luxury
    # fragrances
    (25,   "fragrances", "budget"),
    (60,   "fragrances", "mid"),
    (120,  "fragrances", "premium"),
    (300,  "fragrances", "luxury"),
    (800,  "fragrances", "top_tier"),
    # fashion
    (20,   "fashion", "budget"),
    (100,  "fashion", "mid"),
    (300,  "fashion", "premium"),
    (1000, "fashion", "luxury"),
    (5000, "fashion", "top_tier"),
])
def test_detect_price_tier_per_category(price, category, expected_tier):
    assert _detect_price_tier(price, category) == expected_tier

def test_detect_price_tier_boundary_inclusive_exclusive():
    """Spec §3e: ranges are [min, max). Test boundary at exactly 100 BHD electronics."""
    assert _detect_price_tier(100, "electronics") == "mid"  # exactly mid_min
    assert _detect_price_tier(99.99, "electronics") == "budget"
```

**blockedBy:** A.x — implement `_detect_price_tier`.

**Coverage:** 100% branch + boundary.

---

### Task C.4.3: Pydantic `BudgetValue` Literal accepts 5 values

**File:** Append to `tests/test_scoring_v2_models.py`.

```python
from pydantic import ValidationError
from app.models.scoring import BudgetValue  # or wherever the Literal lives

@pytest.mark.parametrize("val,should_pass", [
    ("budget", True),
    ("mid", True),
    ("premium", True),
    ("luxury", True),
    ("top_tier", True),
    ("free", False),
    ("ultra_luxury", False),
    ("", False),
    (None, False),
])
def test_budget_value_literal(val, should_pass):
    from app.models.preferences import PreferencesPayload  # actual model
    if should_pass:
        PreferencesPayload(budget=val)
    else:
        with pytest.raises(ValidationError):
            PreferencesPayload(budget=val)
```

**blockedBy:** A.x — extend `BudgetValue` Literal.

**Coverage:** 100% on Pydantic validation.

---

### Task C.4.4: `other` geometric-mean sub-scale detection

**File:** Append to `tests/test_tier_detection.py`.

```python
@pytest.mark.parametrize("p1,p2,expected_subscale", [
    (5, 10, "other_light"),       # gm ~7 < 30
    (50, 100, "other_mid"),       # gm ~71, in [30, 300)
    (500, 2000, "other_high"),    # gm ~1000, in [300, 5000)
    (5000, 8000, "other_ultra"),  # gm ~6324, >= 5000
])
def test_other_subscale_from_geometric_mean(p1, p2, expected_subscale):
    from app.services.scoring_service import _detect_other_subscale
    assert _detect_other_subscale(p1, p2) == expected_subscale

@pytest.mark.parametrize("p1,p2,expected_tier_p1,expected_tier_p2", [
    # Car comparison: 5000 + 6000 BHD → gm ~5477 → other_ultra
    # In other_ultra: budget <5000, mid 5000-15000, premium 15000-40000, luxury 40000-100000, top_tier 100000+
    (5000, 6000, "mid", "mid"),
    # Snack comparison: 2 + 4 BHD → gm ~2.83 → other_light
    # In other_light: budget <11, mid 11-57, premium 57-189, luxury 189-500, top_tier 500+
    (2, 4, "budget", "budget"),
    # Mid-range: 100 + 200 BHD → gm ~141 → other_mid
    # In other_mid: budget <30, mid 30-120, premium 120-400, luxury 400-1000, top_tier 1000+
    (100, 200, "mid", "premium"),
])
def test_detect_price_tier_other_category_with_comparison(p1, p2, expected_tier_p1, expected_tier_p2):
    """Spec §3f: when category='other' and comparison_prices provided, use gm to pick sub-scale."""
    assert _detect_price_tier(p1, "other", comparison_prices=[p1, p2]) == expected_tier_p1
    assert _detect_price_tier(p2, "other", comparison_prices=[p1, p2]) == expected_tier_p2

def test_detect_price_tier_other_default_to_light_when_no_comparison():
    """When comparison_prices=None and category='other', fall back to other_light."""
    assert _detect_price_tier(20, "other") in {"mid", "budget"}  # 20 BHD in other_light → mid
```

**blockedBy:** A.x — `_detect_other_subscale` + `_detect_price_tier(comparison_prices=...)` plumbing.

**Coverage:** 100% on 4 sub-scales × 5 tiers.

---

### Task C.4.5: Car case from spec — full path

**File:** Append to `tests/test_tier_detection.py`.

```python
def test_car_comparison_spec_example():
    """Spec §3f exact example: 5000 + 6000 BHD cars → gm 5477 → other_ultra → both 'mid'."""
    p1, p2 = 5000, 6000
    tier_a = _detect_price_tier(p1, "other", comparison_prices=[p1, p2])
    tier_b = _detect_price_tier(p2, "other", comparison_prices=[p1, p2])
    assert tier_a == "mid"
    assert tier_b == "mid"

def test_user_budget_searching_cars_picks_cheapest():
    """Spec §4e Case 2: user picked 'budget' + comparing 5000+6000 BHD cars.
    Cheapest product gets value lift via math; budget adjustments stay active."""
    from app.services.scoring_service import compute_scores
    products = [
        _make_product(price_amount=5000, category="other"),  # Honda
        _make_product(price_amount=6000, category="other"),  # Toyota
    ]
    result = compute_scores(products, category="other",
                            preferences={"budget": "budget", "priorities": ["price"]})
    # Cheaper product wins on value
    assert result["products"][0]["value_score"] > result["products"][1]["value_score"]
    # AND budget_mismatch is "below" for both products
    assert result.get("budget_mismatch") == "below"
```

**blockedBy:** A.x — value formula + budget_mismatch propagation.

**Coverage:** 100% on `budget_mismatch` branch logic.

---

## C.5 — Value math tests (spec §4)

### Task C.5.1: `VALUE_FORMULA_BY_PRIORITY` coefficients

**File:** `tests/test_value_math.py` — NEW.

```python
import pytest
from app.services.scoring_service import (
    VALUE_FORMULA_BY_PRIORITY,
    _compute_value_score,
)

# Table from spec §4a
EXPECTED_COEFFICIENTS = {
    "price":             {"spec": 0.40, "price": 0.60},
    "quality":           {"spec": 0.70, "price": 0.30},
    "durability":        {"spec": 0.65, "price": 0.35},
    "latest_features":   {"spec": 0.65, "price": 0.35},
    "brand_reputation":  {"spec": 0.65, "price": 0.35},
    "eco_friendly":      {"spec": 0.55, "price": 0.45},
    "ease_of_use":       {"spec": 0.55, "price": 0.45},
    "_default":          {"spec": 0.60, "price": 0.40},
}

@pytest.mark.parametrize("priority,coeffs", list(EXPECTED_COEFFICIENTS.items()))
def test_value_formula_coefficients(priority, coeffs):
    actual = VALUE_FORMULA_BY_PRIORITY.get(priority, VALUE_FORMULA_BY_PRIORITY["_default"])
    assert actual["spec"] == coeffs["spec"]
    assert actual["price"] == coeffs["price"]
    assert actual["spec"] + actual["price"] == pytest.approx(1.0)
```

**blockedBy:** A.x — define `VALUE_FORMULA_BY_PRIORITY`.

**Coverage:** 100% — every coefficient row tested.

---

### Task C.5.2: First-match priority wins

**File:** Append to `tests/test_value_math.py`.

```python
def test_value_formula_first_match_wins():
    """Spec §4a: function reads preferences.get('priorities', []) first-match wins."""
    # priorities=['quality', 'price'] → uses quality coefficients (0.70/0.30)
    score = _compute_value_score(spec_score=80, price_score=60,
                                 priorities=["quality", "price"])
    expected = 0.70 * 80 + 0.30 * 60  # = 56 + 18 = 74
    assert score == pytest.approx(expected, abs=0.1)

    # Reverse order → uses price coefficients (0.40/0.60)
    score2 = _compute_value_score(spec_score=80, price_score=60,
                                  priorities=["price", "quality"])
    expected2 = 0.40 * 80 + 0.60 * 60  # = 32 + 36 = 68
    assert score2 == pytest.approx(expected2, abs=0.1)

def test_value_formula_default_when_no_priorities():
    """No priorities → 0.60 spec + 0.40 price."""
    score = _compute_value_score(spec_score=80, price_score=60, priorities=[])
    expected = 0.60 * 80 + 0.40 * 60
    assert score == pytest.approx(expected, abs=0.1)
```

**blockedBy:** A.x — `_compute_value_score` priority-aware.

**Coverage:** Priority-list branch coverage.

---

### Task C.5.3: Cross-tier formula uses TIER_EXPECTATIONS, modified for priority

**File:** Append to `tests/test_value_math.py`.

```python
def test_cross_tier_formula_keeps_tier_expectations(service):
    """Spec §4a: cross-tier path keeps TIER_EXPECTATIONS but
    `delivery * 0.8` → 0.9 for price priority and 0.7 for quality priority."""
    # Mock cross-tier: product A=budget, product B=premium
    # Same-tier path uses VALUE_FORMULA_BY_PRIORITY
    # Cross-tier path uses TIER_EXPECTATIONS + priority modifier
    score_price_pri = service._compute_value_cross_tier(
        product_score=70, tier="premium", priorities=["price"]
    )
    score_quality_pri = service._compute_value_cross_tier(
        product_score=70, tier="premium", priorities=["quality"]
    )
    # quality priority demands MORE from premium tier (0.7 multiplier — harder)
    # price priority is MORE forgiving (0.9 multiplier — easier)
    assert score_price_pri > score_quality_pri
```

**blockedBy:** A.x — cross-tier formula adjustment.

**Coverage:** 100% on cross-tier priority modifier.

---

### Task C.5.4: `delta_text` enriched with percentage math

**File:** Append to `tests/test_value_math.py`.

```python
def test_delta_text_price_percentage():
    """Spec §4b: delta_text for price reads '40% less' (was 'BHD 3.76 less')."""
    from app.services.response_builder import build_value_delta_text
    delta = build_value_delta_text(price_a=10, price_b=6, signal="price")
    assert "40% less" in delta
    # Secondary BHD framing may still appear as caption — kept for clarity
    assert "BHD" in delta or "less" in delta

def test_delta_text_rating_stars():
    """Spec §4b: delta_text for reviews reads '0.9 stars higher'."""
    delta = build_value_delta_text(rating_a=4.5, rating_b=3.6, signal="reviews")
    assert "0.9 stars" in delta or "0.9" in delta

def test_delta_text_value_with_priority_match():
    """Spec §4b: when priority matches dim, copy is 'Better value for your priority'."""
    delta = build_value_delta_text(signal="value", priority_match=True)
    assert delta == "Better value for your priority"

def test_delta_text_value_no_priority():
    """Spec §4b: when no priority match, default 'Stronger value ratio'."""
    delta = build_value_delta_text(signal="value", priority_match=False)
    assert delta == "Stronger value ratio"
```

**blockedBy:** A.x — implement `build_value_delta_text`.

**Coverage:** 4 signal variants tested.

---

### Task C.5.5: `value_match` classification (4 states)

**File:** Append to `tests/test_value_math.py`.

```python
@pytest.mark.parametrize("user_budget,product_tier,expected_value_match", [
    ("mid", "mid", "in_range"),         # exact match → silent
    ("mid", "premium", "above_range"),  # 1 tier above
    ("mid", "budget", "below_range"),   # 1 tier below
    ("mid", "luxury", "above_range"),   # 2+ tiers above — caption changes copy
    ("luxury", "budget", "below_range"), # 3 tiers below — caption changes copy
])
def test_value_match_classification(user_budget, product_tier, expected_value_match):
    from app.services.scoring_service import _classify_value_match
    assert _classify_value_match(user_budget=user_budget, product_tier=product_tier) == expected_value_match

def test_value_match_caption_copy():
    """Spec §4d: per-row caption rendering."""
    from app.services.response_builder import build_value_match_caption
    assert build_value_match_caption("in_range") == ""  # silent
    assert build_value_match_caption("above_range", tier_delta=1) == "Above your usual range"
    assert build_value_match_caption("below_range", tier_delta=1) == "Within your range"
    assert build_value_match_caption("above_range", tier_delta=2, key_tradeoff="...") == \
        "Above your usual range — but here's why"
```

**blockedBy:** A.x — `_classify_value_match` + `build_value_match_caption`.

**Coverage:** 100% — 4 states × caption variants.

---

### Task C.5.6: `budget_mismatch` propagation to verdict prompt

**File:** Append to `tests/test_extraction_prompt.py`.

```python
@pytest.mark.parametrize("user_budget,product_tiers,expected_mismatch", [
    ("budget", ["luxury", "luxury"], "above"),    # both above
    ("luxury", ["budget", "mid"], "below"),       # both below
    ("mid", ["mid", "premium"], None),            # spans user tier — no mismatch
    ("mid", ["mid", "mid"], None),                # exact match
])
def test_budget_mismatch_classification(user_budget, product_tiers, expected_mismatch):
    from app.services.extraction_service import _classify_budget_mismatch
    assert _classify_budget_mismatch(user_budget, product_tiers) == expected_mismatch

def test_budget_mismatch_in_verdict_prompt():
    """Spec §4e: budget_mismatch passed to _build_preferences_prompt — adds instruction."""
    from app.services.extraction_service import _build_preferences_prompt
    prompt = _build_preferences_prompt(
        explicit_prefs={"budget": "budget"},
        behavioral={}, demographics_profile=None,
        budget_mismatch="above"
    )
    assert "outside the user's usual range" in prompt or "budget_mismatch" in prompt
    # NO UI banner directive — only prompt context
    assert "show banner" not in prompt.lower()
```

**blockedBy:** A.x — `_classify_budget_mismatch` + prompt builder extension.

**Coverage:** 100% branch on the 3 mismatch states + 1 null state.

---

### Task C.5.7: Tier-mismatch math test (Case 2 from spec §4e)

**File:** Append to `tests/test_value_math.py`.

```python
def test_tier_mismatch_case2_budget_user_above_range_products(service):
    """Spec §4e Case 2: user='budget' picking, both products above tier.
    Budget adjustments stay active. Value formula respects price priority.
    Cheaper product gets value lift via math."""
    products = [
        _make_product(price_amount=5000, category="other"),
        _make_product(price_amount=6000, category="other"),
    ]
    result = service.compute_scores(
        products, category="other",
        preferences={"budget": "budget", "priorities": ["price"]}
    )
    # Cheaper product wins on value
    assert result["products"][0]["value_score"] > result["products"][1]["value_score"]
    # Verify budget adjustments active (price-heavier weights)
    weights_used = result["weights_used"]
    default_weights = service._get_default_weights("other")
    # The weight on price-like dim should be HIGHER in budget mode
    assert weights_used.get("value_score", 0) > default_weights.get("value_score", 0)
```

**blockedBy:** A.x — budget adjustments + value formula coordination.

**Coverage:** Integration of value math + budget adjustments.

---

## C.6 — Confidence widget tests (spec §5)

### Task C.6.1: Loosened thresholds

**File:** `tests/test_confidence_thresholds.py` — NEW.

```python
import pytest
from app.services.scoring_service import compute_confidence

def test_rating_strong_at_review_count_100_even_unverified():
    """Spec §5a: rating_strong drops verified=True requirement.
    New rule: review_count >= 100."""
    products = [{"review_count": 120, "rating_verified": False}]
    conf = compute_confidence(products)
    assert conf["legs"]["reviews"] == "strong"

def test_rating_strong_below_100_is_acceptable():
    products = [{"review_count": 50, "rating_verified": True}]
    conf = compute_confidence(products)
    assert conf["legs"]["reviews"] in ("acceptable", "weak")

def test_price_strong_when_one_product_estimated(service):
    """Spec §5a: price_strong accepts shopping_count >= 3 even when one product is estimated."""
    products = [
        {"price": {"source_method": "page_scrape"}, "shopping_count": 5},
        {"price": {"source_method": "estimated"}, "shopping_count": 0},
    ]
    conf = compute_confidence(products)
    assert conf["legs"]["price"] == "strong"

def test_specs_strong_via_citation_count_alone():
    """Spec §5a: specs_strong fires at citation_count >= 8 OR verified_pct >= 40."""
    products = [{"fact_check": {"citation_count": 9, "verified_pct": 20}}]
    conf = compute_confidence(products)
    assert conf["legs"]["specs"] == "strong"

def test_specs_strong_at_verified_pct_40():
    products = [{"fact_check": {"verified_pct": 45, "citation_count": 2}}]
    conf = compute_confidence(products)
    assert conf["legs"]["specs"] == "strong"

def test_overall_threshold_unchanged():
    """Spec §5a: overall threshold unchanged (3 strong = high, 2 = medium, ≤1 = low)."""
    # 3 strong legs → high
    products_high = [{"review_count": 200, "fact_check": {"verified_pct": 50},
                      "price": {"source_method": "page_scrape"}, "shopping_count": 5}]
    assert compute_confidence(products_high)["overall"] == "high"
    # 1 strong leg → low
    products_low = [{"review_count": 5, "fact_check": {"verified_pct": 10},
                     "price": {"source_method": "estimated"}, "shopping_count": 0,
                     "rating_verified": False}]
    assert compute_confidence(products_low)["overall"] == "low"
```

**blockedBy:** A.x — `compute_confidence` threshold loosening.

**Coverage:** 100% branch on 3-leg classification + overall aggregator.

---

### Task C.6.2: 3-leg pill computation (each leg returns strength)

**File:** Append to `tests/test_confidence_thresholds.py`.

```python
def test_compute_confidence_returns_three_legs():
    """Spec §5b: response payload has price/reviews/specs legs with strength enum."""
    products = [{"review_count": 100, "fact_check": {"verified_pct": 50},
                 "price": {"source_method": "page_scrape"}, "shopping_count": 5}]
    conf = compute_confidence(products)
    assert "legs" in conf
    assert set(conf["legs"].keys()) == {"price", "reviews", "specs"}
    for leg in conf["legs"].values():
        assert leg in {"strong", "acceptable", "weak"}

def test_legacy_overall_field_kept_for_backwards_compat():
    """Spec §5d: legacy `overall: 'low'` field stays in API for backwards-compat.
    Frontend doesn't render it, but it must still serialize."""
    products = [{"review_count": 5, ...}]
    conf = compute_confidence(products)
    assert "overall" in conf
    assert conf["overall"] in {"high", "medium", "low"}
```

**blockedBy:** A.x — response shape.

**Coverage:** Output schema assertion.

---

### Task C.6.3: Frontend — Price pill HIDDEN when any product estimated

**File:** `SmartCompareApp/__tests__/ConfidencePills.test.tsx` — NEW.

```typescript
import { render } from '@testing-library/react-native';
import { expectNoForbiddenStrings } from './_bundle_c_helpers';
import ConfidencePills from '../src/components/results/ConfidencePills';

test('Price pill hidden entirely when any product is estimated', () => {
  const products = [
    { price: { source_method: 'page_scrape' }, ... },
    { price: { source_method: 'estimated' }, ... },  // any product
  ];
  const confidence = { legs: { price: 'strong', reviews: 'strong', specs: 'strong' } };
  const { queryByLabelText, toJSON } = render(
    <ConfidencePills products={products} confidence={confidence} />
  );
  // Spec §5c: pill ABSENT from render tree, not muted
  expect(queryByLabelText(/price.*pill/i)).toBeNull();
  expect(queryByLabelText(/💰/)).toBeNull();
  // Reviews + Specs still render
  expect(queryByLabelText(/reviews.*pill/i)).toBeTruthy();
  expect(queryByLabelText(/specs.*pill/i)).toBeTruthy();
  // No "estimated" wording anywhere
  expectNoForbiddenStrings(toJSON());
});

test('All 3 pills render when no product is estimated', () => {
  const products = [
    { price: { source_method: 'page_scrape' } },
    { price: { source_method: 'firecrawl' } },
  ];
  const confidence = { legs: { price: 'strong', reviews: 'strong', specs: 'strong' } };
  const { queryByLabelText } = render(<ConfidencePills products={products} confidence={confidence} />);
  expect(queryByLabelText(/price.*pill/i)).toBeTruthy();
  expect(queryByLabelText(/reviews.*pill/i)).toBeTruthy();
  expect(queryByLabelText(/specs.*pill/i)).toBeTruthy();
});

test('Pill colors map correctly: strong=emerald, acceptable=amber, weak=gray-muted', () => {
  const confidence = { legs: { price: 'strong', reviews: 'acceptable', specs: 'weak' } };
  const { getByLabelText } = render(<ConfidencePills products={[...]} confidence={confidence} />);
  expect(getByLabelText(/price.*pill/i)).toHaveStyle({ backgroundColor: expect.stringMatching(/emerald|#10B981/i) });
  expect(getByLabelText(/reviews.*pill/i)).toHaveStyle({ backgroundColor: expect.stringMatching(/amber/i) });
  expect(getByLabelText(/specs.*pill/i)).toHaveStyle({ backgroundColor: expect.stringMatching(/gray/i) });
});
```

**blockedBy:** B.x — `ConfidencePills` component implementation.

**Coverage:** Visual + structural assertion.

---

### Task C.6.4: Tap-reveal copy — countable facts only, no forbidden vocabulary

**File:** Append to `SmartCompareApp/__tests__/ConfidencePills.test.tsx`.

```typescript
import { fireEvent } from '@testing-library/react-native';

test('Tap reveals What We Know sheet with countable facts only', async () => {
  const products = [{
    review_count: 1200,
    review_sources: ['Amazon', 'Best Buy', 'Google'],
    fact_check: { citation_count: 23, verified_pct: 60 },
    price: { source_method: 'page_scrape' },
  }];
  const confidence = { legs: { price: 'strong', reviews: 'strong', specs: 'strong' } };
  const { getByLabelText, getByText, toJSON } = render(<ConfidencePills ... />);
  fireEvent.press(getByLabelText(/reviews.*pill/i));
  // Sheet now visible
  expect(getByText(/1200 reviews/i)).toBeTruthy();
  expect(getByText(/Amazon.*Best Buy.*Google/i)).toBeTruthy();
  // No threshold/percentage exposure
  expect(toJSON()).not.toMatch(/40%/);
  expect(toJSON()).not.toMatch(/>= 100/);
  // No "estimated"/"reference"/"indicative" copy
  expectNoForbiddenStrings(toJSON());
});

test('Specs tap-reveal lists field count, never coefficient', () => {
  fireEvent.press(getByLabelText(/specs.*pill/i));
  expect(getByText(/23 of 30 fields/i)).toBeTruthy();
  expect(toJSON()).not.toMatch(/coefficient/i);
  expect(toJSON()).not.toMatch(/threshold/i);
});
```

**blockedBy:** B.x — bottom-sheet implementation.

**Coverage:** Forbidden-vocabulary backtest on tap reveal.

---

## C.7 — DimensionBars contract tests (spec §6)

### Task C.7.1: `build_dimensions_v2` emits from `CATEGORY_DIMENSIONS`

**File:** Append to `tests/test_dimensions_builder.py`.

```python
def test_build_dimensions_v2_uses_category_dimensions():
    """Spec §6a: build_dimensions_v2 emits dims from CATEGORY_DIMENSIONS[category],
    NOT hand-coded builders like _dim_dpi / _dim_popularity / _dim_build_quality."""
    from app.services.response_builder import build_dimensions_v2
    from app.services.scoring_service import CATEGORY_DIMENSIONS
    raw_a = {dim: 70 for dim in CATEGORY_DIMENSIONS["electronics"]}
    raw_b = {dim: 75 for dim in CATEGORY_DIMENSIONS["electronics"]}
    dims = build_dimensions_v2(raw_a, raw_b, category="electronics")
    emitted_keys = {d["dim_key"] for d in dims}
    # Every category dim with non-null both-product scores is emitted
    assert emitted_keys == set(CATEGORY_DIMENSIONS["electronics"])

def test_build_dimensions_v2_orders_core_first():
    """Spec §6a: order — 3 cross-category core dims (Price, Reviews, Value)
    first, then up to 3 category-specific."""
    dims = build_dimensions_v2(raw_a={"value_score": 70, "performance_score": 80, ...},
                                raw_b={"value_score": 65, "performance_score": 75, ...},
                                category="electronics")
    # First 3 should include value-like dims
    core_dim_keys = {d["dim_key"] for d in dims[:3]}
    assert "value_score" in core_dim_keys
```

**blockedBy:** A.x — `build_dimensions_v2` refactor.

**Coverage:** 90% on `build_dimensions_v2`.

---

### Task C.7.2: Frontend hero + expand UI

**File:** `SmartCompareApp/__tests__/DimensionBars.test.tsx` — NEW.

```typescript
import { render, fireEvent } from '@testing-library/react-native';
import { expectNoBanner, expectNoForbiddenStrings } from './_bundle_c_helpers';
import DimensionBars from '../src/components/results/DimensionBars';

test('Hero card shows top 3-4 dims visible immediately', () => {
  const dims = [
    { dim_key: 'price', score_a: 80, score_b: 75 },
    { dim_key: 'reviews', score_a: 85, score_b: 80 },
    { dim_key: 'value_score', score_a: 78, score_b: 72 },
    { dim_key: 'performance_score', score_a: 82, score_b: 79 },
    { dim_key: 'build_quality_score', score_a: 70, score_b: 75 },
    { dim_key: 'futureproof_score', score_a: 78, score_b: 76 },
  ];
  const { getAllByLabelText, queryByLabelText } = render(<DimensionBars dimensions={dims} category="electronics" />);
  const visibleBars = getAllByLabelText(/dimension-bar/i);
  expect(visibleBars.length).toBeGreaterThanOrEqual(3);
  expect(visibleBars.length).toBeLessThanOrEqual(4);
  // See full breakdown row exists (collapsed by default)
  expect(queryByLabelText(/see.*full.*breakdown/i)).toBeTruthy();
});

test('Expand reveals all dims with animated height transition', () => {
  const { getByLabelText, getAllByLabelText } = render(<DimensionBars dimensions={...} />);
  const expandRow = getByLabelText(/see.*full.*breakdown/i);
  fireEvent.press(expandRow);
  // After expand, all 6 dims visible
  const visibleBars = getAllByLabelText(/dimension-bar/i);
  expect(visibleBars.length).toBe(6);
});

test('Hero card snapshot', () => {
  const tree = render(<DimensionBars dimensions={[...]} category="electronics" />).toJSON();
  expect(tree).toMatchSnapshot();
});
```

**blockedBy:** B.x — DimensionBars hero+expand refactor.

**Coverage:** Snapshot + interaction.

---

### Task C.7.3: Both-products-null silently omitted

**File:** Append to `SmartCompareApp/__tests__/DimensionBars.test.tsx`.

```typescript
test('Dims with both products null are silently omitted from render', () => {
  const dims = [
    { dim_key: 'value_score', score_a: 70, score_b: 65 },
    // performance_score absent from dims[] entirely (backend silent omission per §2h)
  ];
  const { queryByLabelText, toJSON } = render(<DimensionBars dimensions={dims} category="electronics" />);
  // No performance bar
  expect(queryByLabelText(/performance/i)).toBeNull();
  // NO "—" or "Limited data" copy when dim is silently omitted
  expect(toJSON()).not.toMatch(/—/);
  expect(toJSON()).not.toMatch(/Limited data/i);
});

test('Last-resort row renders muted — when single dim survives with both null', () => {
  const dims = [
    { dim_key: 'sole_dim', score_a: null, score_b: null, caption: 'Limited data' },
  ];
  const { getByLabelText, getByText } = render(<DimensionBars dimensions={dims} />);
  expect(getByText(/Limited data/i)).toBeTruthy();
  // Bar element exists but muted (no fill)
  const bar = getByLabelText(/dimension-bar.*sole_dim/i);
  expect(bar).toHaveStyle({ opacity: expect.toBeLessThan(1) });
});
```

**blockedBy:** B.x — DimensionBars omission rendering.

**Coverage:** Both omission paths.

---

### Task C.7.4: Contract violation node still fires on zero-score input

**File:** Append to `SmartCompareApp/__tests__/DimensionBars.test.tsx`.

```typescript
test('Contract violation node logs error on zero-score dim (dev-mode safety net)', () => {
  const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
  const dims = [{ dim_key: 'value_score', score_a: 0, score_b: 0 }];  // zero scores
  render(<DimensionBars dimensions={dims} />);
  // Per spec §6d: zero-score detector remains; backend should never emit, but UI catches regression
  expect(consoleErrorSpy).toHaveBeenCalledWith(expect.stringMatching(/contract violation/i));
  consoleErrorSpy.mockRestore();
});
```

**blockedBy:** B.x — `DimensionBars.tsx:53-69` zero-score detector retained.

**Coverage:** Safety-net regression.

---

## C.8 — Personalization chip tests (spec §7)

### Task C.8.1: `applied_shifts[]` correctly computed

**File:** Append to `tests/test_personalization.py`.

```python
def test_applied_shifts_direction_only(service):
    """Spec §7b: response.personalization.applied_shifts = [{dim_display, direction}, ...]
    where direction = 'up' | 'down'. Magnitude HIDDEN — never reaches API."""
    from app.services.scoring_service import _compute_applied_shifts, CATEGORY_DIMENSION_WEIGHTS
    weights_used = {"performance_score": 0.30, "build_quality_score": 0.25,
                    "ecosystem_score": 0.10, ...}
    defaults = CATEGORY_DIMENSION_WEIGHTS["electronics"]
    shifts = _compute_applied_shifts(weights_used, defaults)
    # Each shift is dict with only 2 keys
    for shift in shifts:
        assert set(shift.keys()) == {"dim_display", "direction"}
        assert shift["direction"] in {"up", "down"}
    # No magnitude leak
    from tests._bundle_c_helpers import assert_no_magnitude_fields
    assert_no_magnitude_fields({"applied_shifts": shifts})

def test_applied_shifts_sorted_by_absolute_magnitude():
    """Spec §7b: sorted by absolute magnitude (largest 3)."""
    weights_used = {"a": 0.50, "b": 0.10, "c": 0.30, "d": 0.05}
    defaults = {"a": 0.25, "b": 0.25, "c": 0.25, "d": 0.25}
    shifts = _compute_applied_shifts(weights_used, defaults)
    # 'a' has biggest absolute shift (+0.25), should be first
    assert shifts[0]["dim_display"] == "a"
    # Up to 3 returned
    assert len(shifts) <= 3

def test_applied_shifts_returns_empty_when_no_priorities():
    """Spec §7a: chip hidden when no priorities set OR no significant shifts."""
    weights_used = defaults = {"a": 0.33, "b": 0.33, "c": 0.34}
    shifts = _compute_applied_shifts(weights_used, defaults)
    assert shifts == []
```

**blockedBy:** A.x — `_compute_applied_shifts` impl.

**Coverage:** 90% on `_compute_applied_shifts`.

---

### Task C.8.2: API response payload has no magnitude fields

**File:** Append to `tests/test_personalization.py`.

```python
def test_response_personalization_payload_no_magnitude():
    """Spec §7b: full response shape audit — no magnitude/coefficient/shift_pct leaks."""
    from app.services.response_builder import build_comparison_response
    from tests._bundle_c_helpers import assert_no_magnitude_fields
    response = build_comparison_response(
        products=[...],
        scoring_result={"applied_shifts": [{"dim_display": "performance_score", "direction": "up"}],
                        "weights_used": {...}, ...},
        ...
    )
    assert_no_magnitude_fields(response.get("personalization", {}))
    # Belt-and-braces: serialize and grep
    import json
    serialized = json.dumps(response)
    assert '"magnitude"' not in serialized
    assert '"shift_pct"' not in serialized
    assert '"coefficient"' not in serialized
```

**blockedBy:** A.x — response_builder cleanup.

**Coverage:** Full-response grep.

---

### Task C.8.3: Frontend — chip rendering

**File:** `SmartCompareApp/__tests__/PersonalizationChip.test.tsx` — NEW.

```typescript
import { render } from '@testing-library/react-native';
import PersonalizationChip from '../src/components/results/PersonalizationChip';

test('Chip renders up to 3 arrows below verdict', () => {
  const shifts = [
    { dim_display: 'performance_score', direction: 'up' },
    { dim_display: 'build_quality_score', direction: 'up' },
    { dim_display: 'brand_recognition', direction: 'down' },
  ];
  const { getByText } = render(<PersonalizationChip appliedShifts={shifts} />);
  expect(getByText(/↑.*Performance/i)).toBeTruthy();
  expect(getByText(/↑.*Build/i)).toBeTruthy();
  expect(getByText(/↓.*Brand/i)).toBeTruthy();
  expect(getByText(/based on your priorities/i)).toBeTruthy();
});

test('Chip hidden when no shifts', () => {
  const { queryByText } = render(<PersonalizationChip appliedShifts={[]} />);
  expect(queryByText(/based on your priorities/i)).toBeNull();
});

test('Chip hidden when shifts is null/undefined', () => {
  const { queryByText } = render(<PersonalizationChip appliedShifts={null as any} />);
  expect(queryByText(/based on your priorities/i)).toBeNull();
});

test('NO percentages or magnitudes in rendered chip', () => {
  const shifts = [{ dim_display: 'performance_score', direction: 'up' }];
  const { toJSON } = render(<PersonalizationChip appliedShifts={shifts} />);
  expect(JSON.stringify(toJSON())).not.toMatch(/\d+%/);
  expect(JSON.stringify(toJSON())).not.toMatch(/coefficient/i);
});

test('Snapshot — single arrow', () => {
  const shifts = [{ dim_display: 'performance_score', direction: 'up' }];
  expect(render(<PersonalizationChip appliedShifts={shifts} />).toJSON()).toMatchSnapshot();
});

test('Snapshot — 3 arrows', () => {
  const shifts = [
    { dim_display: 'performance_score', direction: 'up' },
    { dim_display: 'build_quality_score', direction: 'up' },
    { dim_display: 'brand_recognition', direction: 'down' },
  ];
  expect(render(<PersonalizationChip appliedShifts={shifts} />).toJSON()).toMatchSnapshot();
});
```

**blockedBy:** B.x — `PersonalizationChip` component.

**Coverage:** 80%+ on PersonalizationChip + snapshot lock.

---

### Task C.8.4: i18n EN + AR

**File:** Append to `SmartCompareApp/__tests__/PersonalizationChip.test.tsx`.

```typescript
import i18n from '../src/i18n';

test('i18n EN — chip template + arrows', () => {
  i18n.changeLanguage('en');
  const shifts = [{ dim_display: 'performance_score', direction: 'up' }];
  const { getByText } = render(<PersonalizationChip appliedShifts={shifts} />);
  expect(getByText(/Weighted.*Performance.*based on your priorities/i)).toBeTruthy();
});

test('i18n AR — chip template + arrows (RTL)', () => {
  i18n.changeLanguage('ar');
  const shifts = [{ dim_display: 'performance_score', direction: 'up' }];
  const { getByText, toJSON } = render(<PersonalizationChip appliedShifts={shifts} />);
  // Arabic translation key exists
  expect(getByText(/بناء على/i)).toBeTruthy();
  // No forbidden AR strings
  expect(JSON.stringify(toJSON())).not.toMatch(/تعذر/);
  expect(JSON.stringify(toJSON())).not.toMatch(/فشل/);
});
```

**blockedBy:** B.x — i18n keys added.

**Coverage:** EN + AR locale switching.

---

### Task C.8.5: Cohort badge stays separate component

**File:** Append to `SmartCompareApp/__tests__/PersonalizationChip.test.tsx`.

```typescript
test('CohortBadge and PersonalizationChip render as separate components', () => {
  /** Spec §7d: existing CohortBadge stays own component. No merging. */
  const cohortMatch = { persona_label: 'Quality-first', n: 23 };
  const shifts = [{ dim_display: 'performance_score', direction: 'up' }];
  const { getByLabelText } = render(
    <>
      <PersonalizationChip appliedShifts={shifts} />
      <CohortBadge cohortMatch={cohortMatch} />
    </>
  );
  expect(getByLabelText(/personalization.*chip/i)).toBeTruthy();
  expect(getByLabelText(/cohort.*badge/i)).toBeTruthy();
});
```

**blockedBy:** Existing CohortBadge (no change required — invariant assertion).

**Coverage:** Cross-component isolation.

---

## C.9 — Integration probe suite (spec §1c, §8d)

### Task C.9.1: Create `tests/test_bundle_c_integration.py` skeleton

**File:** `tests/test_bundle_c_integration.py` — NEW.

```python
"""Bundle C integration probe — 6-category cold-cache + 1 'other' car-like.

Re-run post-deploy to capture ship evidence. Designed against live Railway
backend with ?nocache=true. Each probe should complete inside
STREAM_HARD_CAP_SECONDS budget.

Run: pytest tests/test_bundle_c_integration.py -v -m integration --timeout=180
"""
import pytest
import os
import requests
from tests._bundle_c_helpers import assert_no_forbidden_strings

BASE_URL = os.getenv("BUNDLE_C_PROBE_URL", "https://web-production-58776.up.railway.app")


@pytest.fixture(scope="module")
def probe_session():
    s = requests.Session()
    s.headers.update({"Accept": "application/json"})
    return s


PROBES = [
    # (category, query, expected_min_dimensions)
    ("electronics", "iPhone 16 vs Galaxy S25", 4),
    ("skincare", "CeraVe vs Cetaphil moisturizing cream", 3),
    ("supplements", "Solgar Vitamin D3 vs NOW Vitamin D3", 3),
    ("fashion", "Adidas Samba vs Nike Air Force 1", 3),
    ("fragrances", "Tom Ford Black Orchid vs Dior Sauvage", 3),
    ("grocery", "Lurpak butter vs President butter", 3),
]
```

**blockedBy:** none — skeleton can be committed first.

---

### Task C.9.2: 6-category cold-cache probes — real prices land

**File:** Append to `tests/test_bundle_c_integration.py`.

```python
@pytest.mark.integration
@pytest.mark.parametrize("category,query,min_dims", PROBES)
def test_cold_cache_probe_real_prices(probe_session, category, query, min_dims):
    """Spec §1c + §8d: real prices land (NOT all estimated for mainstream products).
    pros/cons populated. dimensions[] count >= min_dims per category.
    confidence pills render correctly."""
    response = probe_session.get(
        f"{BASE_URL}/api/v1/text/compare",
        params={"q": query, "nocache": "true", "region": "bahrain",
                "selected_category": category},
        timeout=30,
    )
    assert response.status_code == 200
    data = response.json()

    # Real prices for at least ONE product per probe (spec §1c)
    estimated_count = sum(
        1 for p in data["products"]
        if p.get("price", {}).get("source_method") == "estimated"
    )
    assert estimated_count < len(data["products"]), \
        f"All products estimated for {category}/{query} — Bundle C §1c regression"

    # Pros/cons populated (spec §1a)
    assert all(p.get("pros") for p in data["products"]), \
        f"Empty pros for {category}/{query} — Bundle C §1a regression"
    assert all(p.get("cons") for p in data["products"]), \
        f"Empty cons for {category}/{query} — Bundle C §1a regression"

    # scoring_v2.dimensions[] count >= min per category (spec §6a)
    dims = data.get("scoring_v2", {}).get("dimensions", [])
    assert len(dims) >= min_dims, \
        f"Only {len(dims)} dims for {category} (expected >= {min_dims})"

    # factual_verdict populated (spec §1b)
    fv = data.get("scoring_v2", {}).get("factual_verdict", {})
    assert fv.get("line1"), f"factual_verdict.line1 missing for {category}/{query}"
    assert fv.get("line2"), f"factual_verdict.line2 missing for {category}/{query}"
```

**blockedBy:** Full Bundle C ship (A.x + B.x). Marked `@pytest.mark.integration` — run post-deploy.

**Coverage:** End-to-end across 6 categories.

---

### Task C.9.3: `other` car-like comparison probe

**File:** Append to `tests/test_bundle_c_integration.py`.

```python
@pytest.mark.integration
def test_other_car_like_comparison(probe_session):
    """Spec §3f exact case: used Toyota Corolla 5000 vs Honda Civic 6000.
    Geometric mean ~5477 → other_ultra. Both products in 'mid' tier of that sub-scale.
    User preferring 'budget' still gets price-weighted value math."""
    response = probe_session.get(
        f"{BASE_URL}/api/v1/text/compare",
        params={"q": "Toyota Corolla 2020 vs Honda Civic 2020", "nocache": "true",
                "region": "bahrain", "selected_category": "other"},
        timeout=30,
    )
    assert response.status_code == 200
    data = response.json()
    # Both products detected in 'mid' tier of other_ultra sub-scale
    tiers = [p.get("scoring_v2", {}).get("price_tier") for p in data["products"]]
    assert tiers[0] == "mid" or tiers[1] == "mid", \
        f"Geometric-mean sub-scale not firing — tiers: {tiers}"
```

**blockedBy:** A.x — `_detect_other_subscale` + tier propagation to response.

---

### Task C.9.4: `value_match` captions fire correctly

**File:** Append to `tests/test_bundle_c_integration.py`.

```python
@pytest.mark.integration
def test_value_match_caption_fires_when_above_user_budget(probe_session):
    """Spec §4d: user preferring 'budget' searching iPhone 16 (luxury) →
    value_match='above_range' → caption renders 'Above your usual range'."""
    # Mock the user's preferences to budget
    response = probe_session.get(
        f"{BASE_URL}/api/v1/text/compare",
        params={"q": "iPhone 16 vs Galaxy S25", "nocache": "true",
                "region": "bahrain", "selected_category": "electronics",
                "preferences[budget]": "budget"},
        timeout=30,
    )
    data = response.json()
    products = data["products"]
    # At least one product should have value_match='above_range'
    matches = [p.get("scoring_v2", {}).get("value_match") for p in products]
    assert "above_range" in matches, f"value_match not firing: {matches}"
```

**blockedBy:** A.x — `value_match` in response.

---

### Task C.9.5: No forbidden vocabulary in any probe response

**File:** Append to `tests/test_bundle_c_integration.py`.

```python
@pytest.mark.integration
@pytest.mark.parametrize("category,query,min_dims", PROBES)
def test_no_forbidden_strings_in_response(probe_session, category, query, min_dims):
    """Spec rule: no 'estimated' / 'reference' / 'indicative' / scary copy in user-visible fields."""
    response = probe_session.get(
        f"{BASE_URL}/api/v1/text/compare",
        params={"q": query, "nocache": "true", "selected_category": category},
        timeout=30,
    )
    data = response.json()

    # User-visible fields ONLY (NOT internal source_method enum which retains "estimated")
    user_visible_fields = []
    for p in data.get("products", []):
        user_visible_fields.append(p.get("verdict_text", ""))
        user_visible_fields.append(" ".join(p.get("pros", [])))
        user_visible_fields.append(" ".join(p.get("cons", [])))
    user_visible_fields.append(data.get("scoring_v2", {}).get("factual_verdict", {}).get("line1", ""))
    user_visible_fields.append(data.get("scoring_v2", {}).get("factual_verdict", {}).get("line2", ""))

    combined = " ".join(user_visible_fields)
    assert_no_forbidden_strings(combined)
```

**blockedBy:** Full Bundle C ship.

**Coverage:** Forbidden-string backtest on user-visible response.

---

### Task C.9.6: Wall-time inside `STREAM_HARD_CAP_SECONDS` per probe

**File:** Append to `tests/test_bundle_c_integration.py`.

```python
@pytest.mark.integration
@pytest.mark.parametrize("category,query,min_dims", PROBES)
def test_probe_within_stream_hard_cap(probe_session, category, query, min_dims):
    """Each probe completes inside 25s STREAM_HARD_CAP_SECONDS."""
    import time
    start = time.monotonic()
    response = probe_session.get(
        f"{BASE_URL}/api/v1/text/compare",
        params={"q": query, "nocache": "true", "selected_category": category},
        timeout=30,
    )
    elapsed = time.monotonic() - start
    assert response.status_code == 200
    assert elapsed < 26.0, f"{category}/{query} took {elapsed}s — exceeds cap"
```

**blockedBy:** Full Bundle C ship.

**Coverage:** Wall-time guard.

---

## C.10 — Regression verification

### Task C.10.1: All existing scoring/personalization tests pass

**Step 1:** After every Bundle C impl commit:
```bash
pytest tests/test_scoring_service.py tests/test_scoring_calibration.py \
       tests/test_scoring_edge_cases.py tests/test_scoring_v2_models.py \
       tests/test_personalization.py tests/test_dimensions_builder.py \
       tests/test_extraction_prompt.py -v --timeout=180
```

Expected: 100% pass. Any pre-existing failure must be filed as send-back to responsible Bundle C agent.

**blockedBy:** Each A.x / B.x commit.

---

### Task C.10.2: Security regression untouched

```bash
pytest tests/test_security_regression.py -v
```

Expected: all ~98 existing tests pass. No new collisions with Bundle C changes (Bundle C adds NO new endpoints — only modifies existing ones at `/api/v1/text/compare`).

**blockedBy:** Each A.x commit.

---

### Task C.10.3: No flakiness — run new tests 3× to verify

```bash
# Run each new Bundle C test file 3 times back-to-back
for i in 1 2 3; do
  pytest tests/test_value_math.py tests/test_tier_detection.py \
         tests/test_confidence_thresholds.py -v --timeout=60
done
```

Expected: 3/3 green. Any test that flakes (passes 2x, fails 1x) must be hardened (typically mock-state contamination).

**blockedBy:** New test files merged.

---

### Task C.10.4: Frontend snapshot regression

```bash
cd SmartCompareApp && npx jest --ci --runInBand src/components/results/
```

Expected: no snapshot drift outside Bundle C changes (`DimensionBars`, `ConfidencePills`, `PersonalizationChip`, `BudgetPicker`). Unrelated snapshots must NOT change.

**blockedBy:** Each B.x commit.

---

## C.11 — Feature flag verification

### Task C.11.1: `ENABLE_BUNDLE_C_SCORING=false` → legacy behavior

**File:** Append to `tests/test_scoring_service.py`.

```python
def test_bundle_c_flag_off_uses_legacy_behavior(monkeypatch):
    """Spec §8b: ENABLE_BUNDLE_C_SCORING=false → legacy Bundle E behavior unchanged."""
    monkeypatch.setenv("ENABLE_BUNDLE_C_SCORING", "false")
    from app.services.scoring_service import compute_scores
    # Legacy missing-data floor of 50 still injected
    product_no_specs = _make_product(specs={})
    product_full = _make_product()
    result = compute_scores([product_no_specs, product_full], category="electronics")
    # Legacy path: missing signals → MISSING_SCORE=50 (NOT None)
    raw_a = result["products"][0]["raw_scores"]
    assert raw_a.get("performance_score") == 50  # MISSING_SCORE default
```

**blockedBy:** A.x — feature flag wired.

**Coverage:** Feature-flag dual path.

---

### Task C.11.2: `ENABLE_BUNDLE_C_SCORING=true` → all new behavior

```python
def test_bundle_c_flag_on_activates_all_changes(monkeypatch):
    """Spec §8b: ENABLE_BUNDLE_C_SCORING=true → all new behavior activates together."""
    monkeypatch.setenv("ENABLE_BUNDLE_C_SCORING", "true")
    from app.services.scoring_service import compute_scores
    product_no_specs = _make_product(specs={})
    product_full = _make_product()
    result = compute_scores([product_no_specs, product_full], category="electronics")
    # New path: missing signals → None (NOT MISSING_SCORE)
    raw_a = result["products"][0]["raw_scores"]
    assert raw_a.get("performance_score") is None
    # New fields present
    assert "applied_shifts" in result.get("personalization", {})
    assert "comparison_quality" in result.get("metadata", {})
```

**blockedBy:** A.x — feature flag wired.

**Coverage:** Feature-flag dual path.

---

### Task C.11.3: Tier expansion UI ships ungated — both flag states render 5 tiers

**File:** Append to `SmartCompareApp/__tests__/BudgetPicker.test.tsx`.

```typescript
test('Budget picker renders 5 tiers when Bundle C flag OFF (additive ship)', () => {
  // Mock config: ENABLE_BUNDLE_C_SCORING=false
  jest.mock('../src/config/features', () => ({ ENABLE_BUNDLE_C_SCORING: false }));
  const { getByText } = render(<BudgetPicker selected="mid" onChange={jest.fn()} />);
  // All 5 tier labels present
  expect(getByText(/Budget-savvy/i)).toBeTruthy();
  expect(getByText(/Mid-range/i)).toBeTruthy();
  expect(getByText(/Premium/i)).toBeTruthy();
  expect(getByText(/Luxury/i)).toBeTruthy();
  expect(getByText(/Top-tier/i)).toBeTruthy();
});

test('Budget picker renders 5 tiers when Bundle C flag ON', () => {
  jest.mock('../src/config/features', () => ({ ENABLE_BUNDLE_C_SCORING: true }));
  // Same assertion — picker is additive, ungated
  const { getByText } = render(<BudgetPicker selected="mid" onChange={jest.fn()} />);
  expect(getByText(/Top-tier/i)).toBeTruthy();
});
```

**blockedBy:** B.x — BudgetPicker 5-tier expansion.

**Coverage:** Ungated-additive contract.

---

### Task C.11.4: Backwards-compat — API accepts old 3-tier values

**File:** Append to `tests/test_scoring_v2_models.py`.

```python
def test_legacy_3tier_values_still_valid():
    """Spec §3d: API still accepts old 3-tier values ('budget'/'mid'/'premium')
    for older clients."""
    from app.models.preferences import PreferencesPayload
    # All 3 legacy values pass validation
    PreferencesPayload(budget="budget")
    PreferencesPayload(budget="mid")
    PreferencesPayload(budget="premium")
    # New values also pass
    PreferencesPayload(budget="luxury")
    PreferencesPayload(budget="top_tier")
```

**blockedBy:** A.x — Pydantic Literal extension.

**Coverage:** Backwards-compat assertion.

---

### Task C.11.5: Final coverage gate

**File:** No new file — run on commit hook or in qa-bundle-c verification.

```bash
pytest --cov=app/services/scoring_service \
       --cov=app/services/response_builder \
       --cov=app/services/extraction_service \
       --cov=app/services/structured_comparison_service \
       --cov-branch \
       --cov-report=term-missing \
       --cov-fail-under=80 \
       tests/test_scoring_service.py tests/test_scoring_calibration.py \
       tests/test_dimensions_builder.py tests/test_personalization.py \
       tests/test_tier_detection.py tests/test_value_math.py \
       tests/test_confidence_thresholds.py tests/test_extraction_prompt.py \
       tests/test_structured_comparison_service.py
```

Specifically verify:
- `_compute_raw_scores`: 90%+
- `calibrate_score`: 90%+
- `_compute_value_score`: 90%+
- `_detect_price_tier`: 90%+
- `_compute_applied_shifts`: 90%+
- `_classify_comparison_quality`: 100% branch
- `_classify_value_match`: 100% branch

Frontend coverage:
```bash
cd SmartCompareApp && npx jest --coverage \
  src/components/results/DimensionBars \
  src/components/results/ConfidencePills \
  src/components/results/PersonalizationChip \
  src/components/BudgetPicker
```

Expected: 80%+ on each. 100% on branch coverage for omission rules.

**Commit:** `test(bundle-c): verify coverage gates met`

**blockedBy:** All previous C tasks merged.

---

## Section C — Summary

**Task count:** 32 tasks across 12 task groups (C.0–C.11).

**Coverage breakdown:**
- **Backend new code:** 90% on new scoring formulas (`_compute_value_score`, `_detect_price_tier`, `_compute_raw_scores`, `calibrate_score`, `_compute_applied_shifts`, `_classify_comparison_quality`, `_classify_value_match`).
- **Backend touched code:** 80% on `scoring_service.py`, `response_builder.py`, `extraction_service.py`, `structured_comparison_service.py`.
- **Frontend new components:** 80% on `DimensionBars`, `ConfidencePills`, `PersonalizationChip`, `BudgetPicker`.
- **Branch coverage:** 100% on `comparison_quality` (3 states), `value_match` (4 states), `budget_mismatch` (3+1 states), tier classification (5 tiers × 9 categories), `other` sub-scale (4 sub-scales).

**Test discipline enforced:**
- TDD: every C.x task is failing-first, then made green by referenced A.x/B.x impl task.
- Reusable assertion helpers (`assert_no_forbidden_strings`, `assert_no_magnitude_fields`, `expectNoBanner`) backtest the 4 critical invariants on every render/response.
- Live integration probes (`@pytest.mark.integration` + `@pytest.mark.live_unit`) double as post-deploy ship evidence per spec §8f.
- Regression suite (C.10) gates each agent's commit.
- Feature flag tests (C.11) verify both legacy and Bundle C paths render correctly.

**Critical invariants asserted:**
- NO info banners in any rendered output (jest `queryByRole('alert')` + `queryByLabelText` absence).
- NO backend coefficients/magnitudes in API response (recursive payload audit).
- NO "estimated"/"reference"/"indicative"/scary copy in user-visible rendered output (regex backtest).
- NO "—" or "Limited data" copy when dim is silently omitted (only renders in last-resort single-dim case).
- `inference_source="model_knowledge"` flag NEVER serialized to response.


---

# SECTION D — qa-bundle-c tasks

**Role:** Diagnostic-first gatekeeper. Runs full test suite after every commit by another agent. Cross-reviews ALL three peer agents' work (backend, frontend, test). Owns Migration 024 application + rollback drill. Owns feature-flag rollout + canary phasing + post-deploy verification + memory updates. Signs off final disassembly.

**Owner files / artifacts:**
- `docs/SESSION_BUNDLES.md` (Bundle C entry — appended)
- `CLAUDE.md` (1-line breadcrumb at end of "Bundle history" line)
- `memory/MEMORY.md` and per-topic memory files (drop "Bucket C brainstorm" pending entry)
- `docs/runbooks/` (canary monitoring notes, if any)
- Diagnostic-evidence appendix (raw logs from `DEBUG_STAGE_TIMINGS=true` window — captured in `docs/SESSION_BUNDLES.md` Bundle C entry, NOT committed as raw .log files)

**Coverage target:** N/A (qa-planner runs coverage gates, doesn't add code coverage themselves).

**Idle behavior:** while waiting on peers, expand D.6 evidence-acceptance criteria into more granular per-category assertions, draft post-mortem questions for next-session triage, or write integration-test stubs spanning backend+frontend that test-bundle-c can pick up. NEVER idle silently.

**Critical reminders absorbed during brainstorm (every QA pass must enforce these):**

1. NO info banners anywhere in user-facing UI — per-element microcopy only.
2. NO backend internals (coefficients, cap percentages, shift math) in user-facing diagnostic reveals — qualitative arrows/labels only.
3. NEVER use "estimated" / "reference price" / "indicative" in user-facing UI — backend `source_method="estimated"` enum stays, UI silent, disclosure in Terms (Section 2i clause).
4. Diagnostic-first for §1a / §1b / §1c — evidence gate is BLOCKING before any patch.
5. NO scary copy in user-facing i18n — forbidden vocabulary: `couldn't`, `try again`, `Failed to`, `تعذر`, `فشل`.

---

## D.0 — Conflict resolution (pre-execution, BLOCKING if any conflicts flagged)

### Task D.0.1: Read assembled plan + identify cross-section conflicts

**Step 1:** Open the final assembled plan `docs/superpowers/plans/2026-05-17-bundle-c-scoring-quality.md` and scan for any `> ⚠️ CROSS-SECTION CONFLICT` callout boxes that the assembler flagged (e.g., backend task A.x.y contradicts frontend task B.x.y, or test task C.x.y expects a contract shape backend didn't ship).

**Step 2:** For each conflict, post a message to the relevant section owners asking for a decision within 2 hours. If no resolution by 2h mark, escalate to Ahmed via `SendMessage to: "team-lead"` with a clear ask.

**Step 3:** Once resolved, update the assembled plan to remove the callout box + record the decision inline near the task. Commit:

```bash
git add docs/superpowers/plans/2026-05-17-bundle-c-scoring-quality.md
git commit -m "plan(bundle-c): resolve cross-section conflict <A.x.y>/<B.x.y>"
```

**Evidence:** screenshot or message-log link of the resolution thread saved inline in the plan.

> If the assembled plan has NO conflict callouts, mark D.0.1 complete immediately and proceed to D.1.

---

## D.1 — Pre-deploy diagnostic gate (BLOCKING for §1a / §1b / §1c fixes)

Per spec §1a, §1b, §1c, and the project rule "measure per-stage before optimizing pipelines". No speculative patches. Evidence first, root-cause second, fix third.

### Task D.1.1: Capture raw GPT verdict response (§1a pros/cons empty diagnostic)

**Owner:** qa-bundle-c orchestrates, backend-bundle-c executes the logging hook.

**Step 1:** Coordinate with backend-bundle-c to confirm the diagnostic logging branch from spec §1a step 1 is in `extraction_service.py:1085+` (logs raw `response.choices[0].message.content` whenever `len(comparison.get("product_0_pros", [])) == 0`). This is **Task A.2.1** — the diagnostic patch (NOT the fix), gated behind a `DEBUG_VERDICT_RAW=true` env var so it only fires during this window.

**Step 2:** Once the diagnostic logging is deployed to Railway staging with `DEBUG_VERDICT_RAW=true`, run the 6-category cold-cache probe in D.1.2 (combine the two diagnostic windows — single Railway push, single set of probe runs, capture both stage timings AND raw verdict logs).

**Step 3:** Pull raw logs via `railway logs --tail 1000 > /tmp/verdict-raw.log` (or Railway dashboard log export). Inspect for at least 6 entries showing the raw GPT JSON body for empty-pros cases.

**Evidence (REQUIRED before §1a fix lands):**
- 6 distinct raw GPT response payloads captured (one per probe category).
- For each, the diagnosed root cause documented in `docs/SESSION_BUNDLES.md` Bundle C diagnostic section: one of {model dropped fields, validate_verdict stripped, comparison.pop fallback, temperature/length issue, prompt structural issue}.
- Sign-off comment from backend-bundle-c that the proposed fix targets the diagnosed cause (NOT a speculative re-prompt fallback).

**Step 4:** After fix lands and 6 probes show non-empty pros/cons, request backend-bundle-c to **remove** the `DEBUG_VERDICT_RAW` env var read + diagnostic logging in a follow-up commit. Verify in a final commit-diff review that the diagnostic code is gone before D.8 gate opens.

### Task D.1.2: Run 6-category cold-cache probe with diagnostics enabled (§1c)

**Step 1:** Coordinate with Ahmed (via `SendMessage to: "team-lead"` if needed) to set on Railway:
```
DEBUG_STAGE_TIMINGS=true
DEBUG_VERDICT_RAW=true          # for D.1.1
DEBUG_FIRECRAWL_INVOCATIONS=true # if backend-bundle-c added this for §1c (else use existing firecrawl_service logging)
DEBUG_SCRAPEDO_INVOCATIONS=true  # likewise
```
These are **temporary**. D.1.4 disables them after evidence captured.

**Step 2:** Wait for Railway deploy (~90s). Confirm `/health` returns 200 + new env vars are set (check via an admin endpoint that returns env state, or by inspecting the first probe's response `metadata.stage_timings_ms` block).

**Step 3:** Run 6 cold-cache probes against staging (or production with `?nocache=true` if staging mirrors prod):

```bash
# All probes use nocache=true to force cold path
for q in "iPhone+16+vs+Galaxy+S25" "CeraVe+vs+Cetaphil+Moisturizing+Cream" "Centrum+vs+One+A+Day" "Tom+Ford+Oud+Wood+vs+Creed+Aventus" "Levis+501+vs+Wrangler+Texas" "Nestle+Pure+Life+vs+Aquafina"
do
  curl "https://web-production-58776.up.railway.app/api/v1/text/compare?q=${q}&region=bahrain&nocache=true" > "/tmp/probe-${q//+/_}.json"
  sleep 5
done
```

Categories covered: electronics / skincare / supplements / fragrances / fashion / grocery. (Spec §8d also lists `+ 1 "other" car-like comparison`; if Section A adds an `other` integration test, capture it here too — otherwise defer to D.6.)

**Step 4:** For each probe JSON response, extract:
- `metadata.stage_timings_ms` block (Phase 1 / Phase 2 / verdict / scoring breakdown).
- For each product: `price.source_method`, `price.estimated`, `price.shopping_count` (if present), `confidence.*` blocks, `dimensions[]` count.
- `pros / cons` lengths per product (for §1a evidence).
- Wall-clock total time (`metadata.total_time_ms` if present, else infer from curl `time -v`).

**Step 5:** Pull Railway logs for the same time window: `railway logs --since 30m > /tmp/probe-logs.log`. Grep for:
- Firecrawl invocations + outcomes (success / timeout / circuit-broken / budget-exhausted).
- Scrape.do invocations + outcomes.
- Serper Shopping raw response sizes per product.
- `api_budget_service` credit-state lines.
- Circuit-breaker state transitions.

**Evidence (REQUIRED before §1c fix lands):**
- 6 probe JSON files captured + zipped + linked from `docs/SESSION_BUNDLES.md` Bundle C diagnostic section (do NOT commit raw probe payloads; link via gist or summarize inline).
- Per-category root-cause table:

  | Category | Phase 1 wall (ms) | Tier traversed (1 → 1.5a → 1.5d → 2 → 3) | Final `source_method` | Firecrawl fired? (Y/N + outcome) | Scrape.do fired? | Diagnosed root cause |
  |---|---|---|---|---|---|---|
  | electronics | ... | ... | ... | ... | ... | ... |
  | skincare | ... | ... | ... | ... | ... | ... |
  | supplements | ... | ... | ... | ... | ... | ... |
  | fragrances | ... | ... | ... | ... | ... | ... |
  | fashion | ... | ... | ... | ... | ... | ... |
  | grocery | ... | ... | ... | ... | ... | ... |

- Identified ranked root causes for `source_method=estimated` regression (spec §1c lists 5 likely causes — narrow to 1-2 actual).
- Sign-off from backend-bundle-c that proposed §1c fix targets the diagnosed cause.

### Task D.1.3: Document root causes in `docs/SESSION_BUNDLES.md` BEFORE any §1a / §1c fix lands

**Step 1:** Append a `Bundle C diagnostic findings (Session 51 day-1)` subsection to `docs/SESSION_BUNDLES.md` with:
- Full per-category root-cause table from D.1.2.
- 6 raw-verdict cause categorisations from D.1.1.
- §1b factual_verdict tracer: cite `response_builder.py:36` confirmed-missing builder location.
- Ranked next-action list: which subsection of Section A unblocks each root cause.

**Step 2:** Commit (path-restricted to avoid sweeping peers' work):

```bash
git commit -m "docs(bundle-c): D.1 diagnostic findings — root causes for 1a/1b/1c" -- docs/SESSION_BUNDLES.md
```

**Step 3:** Broadcast `D.1 evidence captured + root causes documented` via `SendMessage to: "*"` so backend-bundle-c can unblock §1a / §1c fix tasks.

**Gate:** Section A tasks tagged `blockedBy D.1.3` — specifically **A.3.1** (§1a pros/cons empty fix), **A.3.2** (§1b factual_verdict builder restoration), and **A.3.3** (§1c price-pipeline fix) — CANNOT start until this task completes. Enforce by refusing to QA-sign any §1a/§1b/§1c implementation that lands before D.1.3 is checked in.

### Task D.1.4: Disable diagnostic env vars after evidence captured

**Step 1:** Once D.1.1 + D.1.2 + D.1.3 are complete AND all relevant Section A diagnosis-driven fixes have landed AND a final non-debug probe run confirms the fix worked, coordinate with Ahmed to set on Railway:

```
DEBUG_STAGE_TIMINGS=false   # (or unset — both work; default is false)
DEBUG_VERDICT_RAW=false     # (must be unset/removed entirely after final commit removes the env var read)
DEBUG_FIRECRAWL_INVOCATIONS=false
DEBUG_SCRAPEDO_INVOCATIONS=false
```

**Step 2:** Verify by running 1 probe and checking `metadata.stage_timings_ms` is NOT present in the response.

**Step 3:** Note in `docs/SESSION_BUNDLES.md` that diagnostic window closed at <timestamp>.

**Why:** Per the project rule (`memory/feedback_measure_before_optimize.md`), diagnostic env vars cost zero in production with the flag off, BUT leaving them on long-term invites accidental dependencies (e.g., a teammate reading `stage_timings_ms` from prod responses on the assumption it's always there). Close the window cleanly.

---

## D.2 — Cross-QA matrix (BLOCKING — gates disassembly)

Each agent reviews one peer's work. qa-bundle-c reviews ALL three. Send-back protocol: use the template at the bottom of this section.

### Cross-QA matrix

| Reviewer | Reviewing | Review tasks | Evidence required |
|---|---|---|---|
| backend-bundle-c | frontend-bundle-c (contract usage) | D.2.1 | Backend asserts frontend reads `applied_shifts[]`, `value_match`, `comparison_quality`, `factual_verdict.line1/line2`, `personalization.applied_shifts`, `dimensions[]` correctly. Pasted code references with file:line. |
| frontend-bundle-c | backend-bundle-c (response shape) | D.2.2 | Frontend asserts the backend response includes every key the UI consumes, in the expected shape (arrays not nulls where iteration happens, etc.). Pasted curl + jq output. |
| test-bundle-c | both backend AND frontend | D.2.3 + D.2.4 | Test agent runs the full backend pytest + frontend Jest suites against the latest commits + reports coverage. Asserts new tests are RED-GREEN (revert impl → tests fail → re-apply impl → tests pass). |
| qa-bundle-c | all three (own diagnostics included) | D.2.5 + D.2.6 + D.2.7 | qa-bundle-c reviews each peer's work against design doc sections + spot-checks evidence files exist. qa-bundle-c also self-reviews D.1 diagnostic outputs (cannot mark D.1 complete without a peer or Ahmed sign-off). |

### Task D.2.1: backend-bundle-c reviews frontend-bundle-c contract usage

**Reviewer:** backend-bundle-c. **Reviewing:** frontend-bundle-c's owner files (see Section B).

**Checklist:**
- [ ] `SmartCompareApp/src/types.ts` includes new fields: `applied_shifts: {dim_display: string, direction: 'up'|'down'}[]`, `value_match: 'in_range'|'above_range'|'below_range'`, `comparison_quality: 'normal'|'weak'|'weird'`, `factual_verdict: {line1: string, line2: string}`, budget tier `'budget'|'mid'|'premium'|'luxury'|'top_tier'`.
- [ ] `DimensionBars.tsx` iterates `dimensions[]` length-safe (no crash when len < 3 or when array empty for `weird` case).
- [ ] `ResultsScreen.tsx` hides Price confidence pill when ANY product `source_method === 'estimated'` (per spec §5c).
- [ ] Frontend never renders the words `estimated`, `reference price`, `indicative` (grep `i18n/{en,ar}.json` — should be zero matches).
- [ ] Frontend never renders cap percentages, coefficients, or shift magnitudes — only arrow direction (per spec §7a + project rule no-backend-internals).
- [ ] Personalization chip hidden when `applied_shifts[]` is empty.

**Send-back template** (paste into SendMessage when issue found): see "Send-Back Template" at bottom of Section D.

### Task D.2.2: frontend-bundle-c reviews backend-bundle-c response shape

**Reviewer:** frontend-bundle-c. **Reviewing:** backend-bundle-c's owner files (see Section A).

**Checklist:**
- [ ] Run a fresh `?nocache=true` probe against staging once backend-bundle-c signals ready: `curl ... | jq '.scoring_v2'`.
- [ ] Verify response includes:
  - `scoring_v2.factual_verdict.line1` (non-empty string)
  - `scoring_v2.factual_verdict.line2` (non-empty string)
  - `scoring_v2.dimensions[]` (length ≥ 3 for populated comparisons)
  - `scoring_v2.personalization.applied_shifts[]` (may be empty, must be present as array)
  - `scoring_v2.comparison_quality` (one of `normal`/`weak`/`weird`)
  - per product `price.source_method` enum still exists
  - per product `value_match` (one of `in_range`/`above_range`/`below_range`)
  - confidence pills payload per-leg (price, reviews, specs)
- [ ] Confirm legacy fields still emitted for backwards-compat (`overview`, `specs`, `reviews`, `scoring`, `metadata`, `products`, `comparison`, `winner_index`, `recommendation`, `key_differences`).
- [ ] When `ENABLE_BUNDLE_C_SCORING=false`, response matches pre-Bundle-C shape exactly (no new fields breaking older clients).

**Evidence:** paste jq output sample inline in review message.

### Task D.2.3: test-bundle-c reviews backend-bundle-c

**Reviewer:** test-bundle-c. **Reviewing:** Section A implementation against Section C test expectations.

**Checklist:**
- [ ] All backend tests in Section C pass against backend-bundle-c's latest commit.
- [ ] Tests are RED-GREEN: pick 3 new tests at random, revert the implementation commit they target, confirm tests FAIL, re-apply, confirm PASS.
- [ ] Coverage: `pytest --cov=app/services/scoring_service --cov=app/services/extraction_service --cov=app/services/response_builder --cov-fail-under=80` passes.
- [ ] No PRE-EXISTING tests regressed (`pytest tests/ -v -m "not (live_unit or live_db or integration)" --timeout=180`).

### Task D.2.4: test-bundle-c reviews frontend-bundle-c

**Reviewer:** test-bundle-c. **Reviewing:** Section B implementation against Section C frontend test expectations.

**Checklist:**
- [ ] `cd SmartCompareApp && npm test` passes 100%.
- [ ] `cd SmartCompareApp && npx tsc --noEmit` zero errors.
- [ ] Snapshot tests for DimensionBars hero+expand (spec §6b), 3-leg confidence pills row (§5b), personalization chip 3-arrow template (§7a), and 5-tier budget picker (§3c) all updated + match.
- [ ] Snapshots reviewed visually (not auto-accepted) — paste snapshot diff inline in review message.

### Task D.2.5: qa-bundle-c reviews backend-bundle-c

After backend-bundle-c signals "ready for QA":

- [ ] §1a fix lands AFTER D.1.3 commit (verified by git log order).
- [ ] §1b factual_verdict builder lands; spec §1b template fix is pure (zero GPT cost).
- [ ] §1c price-pipeline fix lands AFTER D.1.3 commit; targets diagnosed root cause (per D.1.3 sign-off).
- [ ] §2a missing-data floor of 30 removed; `MISSING_SCORE=50` reference gone or replaced with `None` propagation.
- [ ] §2f 3-tier spec fallback implemented per spec §2f table (non-negotiable vs preferred split correct).
- [ ] §2g `_dim_value` no longer does `or 4.0` silent default; null-propagation throughout.
- [ ] §2h silent omission: dim with `score_a is None or score_b is None` not emitted to `dimensions[]`.
- [ ] §2e weird comparison detector emits `comparison_quality` correctly for cross-category / >50% missing / 10×+ price spread cases. Verdict prompt receives the flag.
- [ ] §3 5-tier system: `PRICE_TIERS_BY_CATEGORY` dict exists with correct BHD ranges per spec §3e. `TIER_EXPECTATIONS` extended to 5 keys. Pydantic `BudgetValue` Literal extended.
- [ ] §3f geometric-mean sub-scale picker implemented; `_detect_price_tier(price, category, *, comparison_prices=None)` signature matches spec.
- [ ] §4a `VALUE_FORMULA_BY_PRIORITY` dict matches spec table; first-match-wins logic confirmed.
- [ ] §4d `value_match` field emitted per product.
- [ ] §4e verdict prompt receives `budget_mismatch` flag; no UI banner.
- [ ] §5a confidence threshold loosening: `rating_strong` drops `verified=True` (count-only ≥100), `price_strong` allows `shopping_count >= 3` fallback, `specs_strong` lowers to 40% OR citation_count ≥ 8.
- [ ] §7b `applied_shifts` computation: sorted by abs(magnitude) desc, top 3, magnitude stripped before emit.
- [ ] §2i Terms of Service + Privacy Policy clause appended in EN + AR.
- [ ] `ENABLE_BUNDLE_C_SCORING` flag defaults `false` in code; flag-off path is verified Bundle-E-identical.
- [ ] No backend internals leak in response (grep response for coefficients, cap percentages, magnitude values).

**Evidence required from backend-bundle-c:** paste 2 probe outputs (1 with flag on, 1 with flag off) showing field-by-field comparison + git log proving §1a/§1c fixes landed after D.1.3.

### Task D.2.6: qa-bundle-c reviews frontend-bundle-c

After frontend-bundle-c signals "ready for QA":

- [ ] Budget picker (`BudgetPicker.tsx` + `Step09Budget.tsx`): 5 tier cards. Visual treatment per spec §3c (premium / luxury / top_tier get dark accent + serif label weight for top_tier). No gaudy gold.
- [ ] `EditPreferencesFlow.tsx` passes new tier prop through.
- [ ] `DimensionBars.tsx`: hero card shows top 3-4 dims by default. "See full breakdown" expand row tappable. Animated height transition. Dim labels via `DIMENSION_DISPLAY_NAMES`. Zero-score detector at lines 53-69 still in place as dev-mode regression catcher.
- [ ] `ResultsScreen.tsx`:
  - 3-pill confidence row (Price · Reviews · Specs) at line 737 (replaces single-word banner).
  - Price pill HIDDEN when any product `source_method === 'estimated'`.
  - Personalization chip below verdict — qualitative arrows only, no percentages, no expand, no tap.
  - Value/Price delta hero layout per spec §4b (delta text large/center, score numbers as small captions).
  - Per-row caption rendering for value_match per spec §4d.
- [ ] `FactualVerdict.tsx`: renders `line1` + `line2` from backend.
- [ ] `HeroRings.tsx`: copy adjustments per design doc applied. Overall score shows `—` when `comparison_quality === 'weird'`.
- [ ] i18n keys present in EN AND AR: `onboarding.s9.luxury`, `onboarding.s9.luxury_range`, `onboarding.s9.top_tier`, `onboarding.s9.top_tier_range`, `results.personalization.chip_template`, `results.personalization.arrow_up`, `results.personalization.arrow_down`, plus value_match captions per §4d.
- [ ] ZERO forbidden vocabulary in i18n: grep `couldn't|try again|Failed to|تعذر|فشل|estimated|reference price|indicative` against `i18n/en.json` AND `i18n/ar.json` → zero matches.
- [ ] ZERO info banner usage for scoring/value/confidence content. (Existing onboarding banners unrelated to Bundle C may stay.)
- [ ] RTL: launch in Arabic and verify hero card, 3-pill row, personalization chip, budget picker all render correctly RTL.

**Evidence:** screenshots (or screen-recordings) of: hero card EN+AR, 3-pill row EN+AR, personalization chip EN+AR, budget picker 5-tier EN+AR, weird-comparison verdict rendering.

### Task D.2.7: qa-bundle-c reviews test-bundle-c

After test-bundle-c signals "ready for QA":

- [ ] `pytest --cov` reports ≥80% on `scoring_service.py` and `extraction_service.py` changes, ≥90% on new tier-detection + geometric-mean logic.
- [ ] All new tests follow red-green discipline (test-bundle-c demonstrates 3 examples in their review message).
- [ ] Integration test suite `tests/test_bundle_c_integration.py` exists with 6-category cold-cache probes (electronics / skincare / supplements / fashion / fragrances / grocery + 1 `other` car-like).
- [ ] Frontend snapshot tests for: DimensionBars hero+expand, 3-pill confidence row, personalization chip 3-arrow, 5-tier budget picker.
- [ ] No tests skipped without `@pytest.mark.skip(reason=...)` documenting why.
- [ ] Regression suite passes: `pytest tests/test_security_regression.py -v` → 100%.

**Evidence:** paste `pytest --cov-report=term-missing` output inline showing line coverage per file.

---

## D.3 — Migration application (Migration 024)

Per spec §8a. Use Supabase MCP `apply_migration` (NOT SQL Editor) for migration-history tracking.

### Task D.3.1: Apply Migration 024 via Supabase MCP

**Pre-condition:** backend-bundle-c has authored `migrations/024_*.sql` (likely `migrations/024_budget_top_tier.sql`) + `migrations/rollback/024_*.sql`, and the migration is committed to the branch.

**Step 1:** Read `migrations/024_*.sql` content. Verify it adds `top_tier` to `users.preferences.budget` CHECK constraint, uses `IF NOT EXISTS` patterns where applicable, has no DROP CASCADE statements outside expected places, leaves existing rows with `budget='premium'` valid.

**Step 2:** Apply via Supabase MCP:
```
mcp__plugin_supabase_supabase__apply_migration(name="024_budget_top_tier", query=<paste full SQL>)
```

**Step 3:** Verify the migration applied:
```
mcp__plugin_supabase_supabase__list_migrations()  # should include 024
mcp__plugin_supabase_supabase__execute_sql(query="
  SELECT pg_get_constraintdef(oid)
  FROM pg_constraint
  WHERE conrelid = 'users'::regclass
    AND contype = 'c'
    AND conname LIKE '%budget%';
")  # should show top_tier in the enum list
```

**Step 4:** Update CLAUDE.md `### Migrations` section to add migration 024 entry (1 line, list of added values).

**Step 5:** Commit:
```bash
git commit -m "migration(024): top_tier in users.preferences.budget enum (applied via MCP)" -- CLAUDE.md
```

### Task D.3.2: Verify `users.preferences.budget` CHECK accepts new values

**Step 1:** Insert test rows:
```sql
-- Should succeed:
INSERT INTO users (id, email, preferences) VALUES (gen_random_uuid(), 'qa-test1@qaren.app', '{"budget": "top_tier"}'::jsonb);
INSERT INTO users (id, email, preferences) VALUES (gen_random_uuid(), 'qa-test2@qaren.app', '{"budget": "luxury"}'::jsonb);
INSERT INTO users (id, email, preferences) VALUES (gen_random_uuid(), 'qa-test3@qaren.app', '{"budget": "premium"}'::jsonb);
INSERT INTO users (id, email, preferences) VALUES (gen_random_uuid(), 'qa-test4@qaren.app', '{"budget": "mid"}'::jsonb);
INSERT INTO users (id, email, preferences) VALUES (gen_random_uuid(), 'qa-test5@qaren.app', '{"budget": "budget"}'::jsonb);

-- Should fail (CHECK violation):
INSERT INTO users (id, email, preferences) VALUES (gen_random_uuid(), 'qa-test6@qaren.app', '{"budget": "ultraluxe"}'::jsonb);
```

**Step 2:** Clean up test rows:
```sql
DELETE FROM users WHERE email LIKE 'qa-test%@qaren.app';
```

**Evidence:** paste SQL outputs (5 inserts succeeded, 1 failed with CHECK violation, 5 deletes).

### Task D.3.3: Rollback drill

**Step 1:** Apply the rollback SQL `migrations/rollback/024_*.sql` to a Supabase BRANCH (NOT main).
```
mcp__plugin_supabase_supabase__create_branch(name="qa-024-rollback-drill")
```
Wait for branch ready.

**Step 2:** Switch to branch, apply main migration 024, then rollback:
```
mcp__plugin_supabase_supabase__apply_migration(name="024_budget_top_tier", query=<paste forward SQL>)  # on branch
mcp__plugin_supabase_supabase__execute_sql(query=<paste rollback SQL>)  # on branch
```

**Step 3:** Verify rollback removed `top_tier` from the CHECK constraint; existing rows with budget='premium' still valid.

**Step 4:** Re-apply forward migration on branch to confirm it's idempotent. Drop the branch:
```
mcp__plugin_supabase_supabase__delete_branch(branch_id=<branch-id>)
```

**Evidence:** paste before/after `pg_get_constraintdef` output showing the rollback worked + branch deleted.

> If Supabase branching is not available on the current Supabase plan, perform the drill against a `qa_test_users` shadow table on main instead (CREATE TABLE LIKE users → apply migration → verify → apply rollback → verify → DROP TABLE). Document the substitution in evidence.

---

## D.4 — Feature flag rollout

Per spec §8b. Flag stays OFF in code (`ENABLE_BUNDLE_C_SCORING` default `false`); flipped ON in Railway during testing per iteration-phase discipline (`memory/feedback_iteration_phase_flag_discipline.md`).

### Task D.4.1: Set `ENABLE_BUNDLE_C_SCORING=false` in Railway

**Step 1:** Coordinate with Ahmed via `SendMessage to: "team-lead"` to set on Railway:
```
ENABLE_BUNDLE_C_SCORING=false
```
This is the initial post-deploy state. Default in code is also `false` so removing the var entirely also works, but explicit is better.

**Step 2:** Verify by inspecting the env-state admin endpoint (or via a probe — a flag-off probe should match Bundle E response shape exactly).

### Task D.4.2: Deploy to Railway main; smoke-test backwards-compat (flag OFF)

**Step 1:** Merge branch `feature/bundle-c-scoring` to main (or coordinate with Ahmed to do so) AFTER all D.2 cross-QA passes + all D.3 migration tasks complete. Wait ~90s for Railway auto-deploy.

**Step 2:** Run 3 cold-cache probes against production with `?nocache=true`:
```bash
curl "https://web-production-58776.up.railway.app/api/v1/text/compare?q=iPhone+16+vs+Galaxy+S25&region=bahrain&nocache=true" > /tmp/prod-flag-off-1.json
curl "https://web-production-58776.up.railway.app/api/v1/text/compare?q=CeraVe+vs+Cetaphil+Moisturizing+Cream&region=bahrain&nocache=true" > /tmp/prod-flag-off-2.json
curl "https://web-production-58776.up.railway.app/api/v1/text/compare?q=Centrum+vs+One+A+Day&region=bahrain&nocache=true" > /tmp/prod-flag-off-3.json
```

**Step 3:** Diff each response against a Bundle E baseline capture (saved from before the merge). The shapes MUST match for backwards-compat:
- Same top-level keys.
- Same `scoring_v2` structure (legacy contracts unchanged).
- No new fields breaking older clients.
- Old 3-tier budget values (`mid`, `premium`) still accepted on the request side (test by hitting `/auth/preferences` with `{"budget": "premium"}`).

**Evidence:** diff output committed inline in `docs/SESSION_BUNDLES.md` (snippet, not full payloads).

### Task D.4.3: Flip flag to `true` in Railway; run smoke probes

**Step 1:** Coordinate with Ahmed to set `ENABLE_BUNDLE_C_SCORING=true` in Railway. Wait for Railway to reboot the app (~30s).

**Step 2:** Run the SAME 3 probes from D.4.2:
```bash
curl "https://web-production-58776.up.railway.app/api/v1/text/compare?q=iPhone+16+vs+Galaxy+S25&region=bahrain&nocache=true" > /tmp/prod-flag-on-1.json
curl "https://web-production-58776.up.railway.app/api/v1/text/compare?q=CeraVe+vs+Cetaphil+Moisturizing+Cream&region=bahrain&nocache=true" > /tmp/prod-flag-on-2.json
curl "https://web-production-58776.up.railway.app/api/v1/text/compare?q=Centrum+vs+One+A+Day&region=bahrain&nocache=true" > /tmp/prod-flag-on-3.json
```

**Step 3:** Verify flag-ON behavior:
- `scoring_v2.factual_verdict.line1` AND `.line2` populated (non-empty strings) — §1b confirmed.
- `pros` AND `cons` arrays non-empty (length ≥ 1 per product) — §1a confirmed.
- `dimensions[]` length ≥ 3 — §6a confirmed.
- `scoring_v2.personalization.applied_shifts[]` present (may be empty array if user has no priorities).
- `scoring_v2.comparison_quality` present.
- Confidence pills payload structured per-leg.

**Step 4:** If any of D.4.3 Step 3 checks fail → emergency `SendMessage to: "team-lead"` + immediate flag flip to false. Do NOT proceed to D.4.4 / D.5 / D.6.

**Evidence:** paste 3 jq snippets inline in `docs/SESSION_BUNDLES.md` confirming each populated field.

### Task D.4.4: Verify tier expansion UI works in BOTH flag states (additive, ungated)

Per spec §3 and §8b: budget picker 5-tier UI ships **ungated** (purely additive; no harm being live regardless of scoring flag).

**Step 1:** With `ENABLE_BUNDLE_C_SCORING=false`:
- Open the app (EAS Update preview channel — see D.6.5).
- Onboarding Step 9 (or Edit Preferences from Profile) → confirm 5 tier cards visible.
- Pick `top_tier` → save → verify backend accepts the value (200 response).
- Run a comparison → verify scoring math falls back to legacy Bundle-E behavior (no new tier-specific scoring applied even though `top_tier` is the stated preference).

**Step 2:** With `ENABLE_BUNDLE_C_SCORING=true`:
- Reopen the app.
- Verify the same 5-tier picker.
- Pick `top_tier` → save → run a comparison → verify Bundle-C tier-aware scoring activates (different `value_match` semantics, different `TIER_EXPECTATIONS` weighting).

**Evidence:** screen-recording showing both states + Supabase row-state diff for the test user.

---

## D.5 — Canary phasing

Per spec §8c + CLAUDE.md "Canary phasing" rule (<10 testers → 100%).

### Task D.5.1: Document canary at 100% (pre-launch state)

**Step 1:** Add to `docs/SESSION_BUNDLES.md` Bundle C entry:
```
Canary: 100% (pre-launch <10 testers, per CLAUDE.md rule)
ENABLE_BUNDLE_C_SCORING=true in Railway from <date> after D.4.3 smoke passed.
Trigger to drop to 10%: App Store soft-launch (see D.5.2).
```

**Step 2:** Update CLAUDE.md "Bundle history" line with 1-word Bundle C breadcrumb at end.

### Task D.5.2: Document trigger to drop to 10% (App Store soft-launch)

**Step 1:** In `docs/SESSION_BUNDLES.md` Bundle C entry, note explicitly:
> Drop `ENABLE_BUNDLE_C_SCORING` rollout to a hash-bucketed 10% canary ONLY when tester pool grows above 10 (target: App Store soft-launch). Ramp 10 → 50 → 100 per `docs/runbooks/qaren-canary-onboarding.md`. The flag itself is binary in Railway; a canary % requires either (a) splitting the flag into a numeric `BUNDLE_C_CANARY_PERCENT` env var with `app/utils/feature_bucket.py::hash_bucket()` reads at request entry, OR (b) gating via the existing `featureBucket.ts` on the frontend AND a backend bucket read. Choice deferred to soft-launch session.

**Step 2:** Add a memory entry pointer:
```
- [Bundle C canary trigger](project_bundle_c_canary_trigger.md) — flag binary today; convert to bucketed % at soft-launch
```
Create the memory file with the same details for cross-session recall.

### Task D.5.3: Reference `docs/runbooks/qaren-canary-onboarding.md` ramp schedule

**Step 1:** Verify the runbook exists. If yes, link from `docs/SESSION_BUNDLES.md` Bundle C entry: "Canary ramp schedule: see `docs/runbooks/qaren-canary-onboarding.md`."

**Step 2:** Skim the runbook for any Bundle-C-specific addition needed (e.g., "monitor `comparison_quality='weird'` rate"). If yes, append a 2-3 line Bundle C subsection to the runbook.

---

## D.6 — Post-deploy verification

Per spec §8f. Run the 6-category integration probe suite against production with `?nocache=true`, verify against 6 evidence acceptance criteria, capture into `docs/SESSION_BUNDLES.md`, monitor Sentry, verify EAS update lands.

### Task D.6.1: Run 6-category integration probe suite against production

**Pre-condition:** D.4.3 passed (flag ON, smoke probes confirmed populated fields).

**Step 1:** Run 7 probes (6 spec categories + 1 `other` car-like for tier sub-scale validation):

```bash
mkdir -p /tmp/bundle-c-postdeploy
declare -A probes=(
  [electronics]="iPhone+16+vs+Galaxy+S25"
  [skincare]="CeraVe+vs+Cetaphil+Moisturizing+Cream"
  [supplements]="Centrum+vs+One+A+Day"
  [fragrances]="Tom+Ford+Oud+Wood+vs+Creed+Aventus"
  [fashion]="Levis+501+vs+Wrangler+Texas"
  [grocery]="Nestle+Pure+Life+vs+Aquafina"
  [other_car]="Toyota+Corolla+vs+Honda+Civic+2024"
)
for cat in "${!probes[@]}"; do
  q="${probes[$cat]}"
  curl "https://web-production-58776.up.railway.app/api/v1/text/compare?q=${q}&region=bahrain&nocache=true" > "/tmp/bundle-c-postdeploy/${cat}.json"
  sleep 8
done
```

### Task D.6.2: Verify against 6 evidence acceptance criteria

For EACH of the 7 probe JSON files, assert:

| # | Criterion | jq query | Pass = |
|---|---|---|---|
| 1 | Real prices land (not estimated) | `jq '[.products[].price.source_method] \| map(. == "estimated") \| any'` | `false` (no product is estimated) for ≥5 of 7 probes |
| 2 | Pros + cons populated | `jq '[.products[] \| (.pros \| length), (.cons \| length)] \| min'` | `≥ 1` (every product has ≥ 1 pro AND ≥ 1 con) |
| 3 | Dimensions emit ≥ 3 | `jq '.scoring_v2.dimensions \| length'` | `≥ 3` (except weird comparisons may emit fewer — verify with §2e logic) |
| 4 | Confidence pills correct | `jq '.scoring_v2.confidence_legs'` (or whichever key Section A chose) | each pill has `level: "strong"\|"acceptable"\|"weak"`; Price pill HIDDEN when any product `source_method == "estimated"` |
| 5 | `value_match` captions fire | `jq '[.products[].value_match] \| unique'` | each product has a `value_match` enum value; UI shows caption when ≠ `in_range` (verify in app screenshot) |
| 6 | Personalization chip renders when shifts exist | `jq '.scoring_v2.personalization.applied_shifts'` | array present; if a test user has priorities set, array length ≥ 1 |

**Pass threshold:** ≥6 of 7 probes satisfy all 6 criteria. If <6 → emergency hold; flip flag to false; re-investigate.

**Granular evidence-acceptance additions (per teammate idle-work request):**

- **Per-category Phase 1 wall:** must be < `STREAM_HARD_CAP_SECONDS` (currently 25s). For mainstream categories (electronics / skincare / grocery) target ≤17s warm cache, ≤22s cold. For luxury (fragrances / fashion top-tier) target ≤25s cold.
- **Confidence pill color sanity:**
  - For probe with `source_method="firecrawl"` or `source_method="page_scrape"` → Price pill emerald or amber (not gray).
  - For probe with `source_method="estimated"` → Price pill ABSENT from UI (not gray, not amber — absent per §5c).
- **Weird-comparison surface:** include a deliberate 8th cross-category probe (e.g., "iPhone+16+vs+CeraVe+Moisturizer") to verify `comparison_quality === "weird"` → hero overall renders `—`, verdict text reframes naturally, no banner appears.
- **Personalization chip empty path:** for a brand-new anonymous user (no priorities), the chip must be HIDDEN entirely. Verify by hitting `?user_id=<fresh-uuid>` and confirming `applied_shifts` is `[]` AND UI does not render the chip.
- **Backend-internals leak grep:** `cat /tmp/bundle-c-postdeploy/*.json | jq '..' | grep -iE '(weight|coefficient|cap_pct|shift_magnitude|scaling_factor)'` → expected: zero matches (per "no backend internals" rule).

### Task D.6.3: Capture results into `docs/SESSION_BUNDLES.md` as Bundle C ship evidence

**Step 1:** Append a `Bundle C — Ship evidence (post-deploy verification)` subsection to `docs/SESSION_BUNDLES.md` with:
- Date + Railway deploy SHA.
- Migration 024 applied (date + via MCP).
- Flag state: `ENABLE_BUNDLE_C_SCORING=true` (canary 100%).
- 7-probe acceptance table (criterion 1-6 per row).
- Granular evidence-acceptance results (Phase 1 walls, confidence colors, weird-probe outcome, empty-personalization outcome, no-internals-leak).
- §1a / §1b / §1c root cause summaries (link back to D.1.3 entry).

**Step 2:** Commit (path-restricted):
```bash
git commit -m "docs(bundle-c): ship evidence — 6 acceptance criteria + diagnostic followup" -- docs/SESSION_BUNDLES.md
```

### Task D.6.4: Verify Sentry shows no new error rate above baseline for 24h

**Step 1:** Snapshot Sentry "Issues" page baseline rate BEFORE D.4.3 flag flip:
```
mcp__plugin_sentry_sentry__search_issues(query="is:unresolved age:-24h", organizationSlug="qaren-rr")
```
Save count.

**Step 2:** 24h after D.4.3 flag flip, snapshot again. Diff. Acceptable:
- 0-5 new low-severity issues OK if all are pre-existing flake or unrelated.
- ANY new "scoring_service" / "extraction_service" / "response_builder" stack-trace issue → block disassembly + send back to backend-bundle-c.

**Step 3:** Also check `mcp__plugin_sentry_sentry__search_events` for the same 24h window filtered to mobile platform — verify no spike in `frontend-bundle-c` change areas (DimensionBars, ResultsScreen, BudgetPicker).

**Evidence:** paste counts (before / after / diff) into `docs/SESSION_BUNDLES.md` Bundle C ship evidence subsection.

### Task D.6.5: Verify EAS Update for frontend lands cleanly (two-lever launch model)

Per CLAUDE.md "Two-lever launch model" — backend (Railway) and frontend (EAS) deploys are independent.

**Step 1:** Once Section B frontend tasks are complete and committed:
```bash
cd SmartCompareApp
git status   # confirm clean
eas update --branch preview --message "Bundle C: tier expansion + dim hero + 3-pill confidence + personalization chip"
```

**Step 2:** Note the EAS Update group ID. Commit (no code change, just log):
```bash
# from repo root
git commit --allow-empty -m "ops(bundle-c): EAS Update <group-id> pushed to preview channel"
```

**Step 3:** Wait 2 minutes, then on a tester device with `preview` channel build:
- Force-close the app.
- Reopen.
- Verify the update landed (build number bump in About screen, or just confirm the new 5-tier picker / 3-pill row visible).

**Step 4:** Run the 6 D.6.2 criteria again in the app (not just curl) — flow:
- Onboarding → pick `top_tier` → run iPhone-vs-Galaxy comparison → verify hero card, 3-pill confidence row, personalization chip, weird-comparison handling on an explicit cross-cat probe.

**Step 5:** Add EAS update ID + tester-device confirmation to `docs/SESSION_BUNDLES.md` Bundle C ship evidence subsection.

> If `eas update` fails (network, auth) — escalate to Ahmed via `SendMessage to: "team-lead"`. He runs interactive EAS commands directly per CLAUDE.md ("Interactive Expo commands need a real terminal — Ahmed runs these directly").

---

## D.7 — Rollback path

Per spec §8e. Single-env-var flip reverts behavior; migration has rollback SQL; tier expansion UI is non-destructive.

### Task D.7.1: Verify env-var flip reverts scoring/UI changes (test in staging)

**Step 1:** Before D.4.3 (i.e. while flag is still OFF post-deploy), use this window to confirm:
- `ENABLE_BUNDLE_C_SCORING=false` → response shape identical to Bundle E baseline (D.4.2 already covers this; this task just re-asserts).
- Frontend renders pre-Bundle-C scoring UI when backend response lacks Bundle C fields:
  - DimensionBars falls back to legacy 6-dim breakdown.
  - Confidence pill row falls back to single-word banner (legacy behavior is preserved as a fallback path in Section B).
  - Personalization chip hidden when `applied_shifts` undefined.
  - Budget picker still shows 5 tiers (additive, ungated) but scoring uses legacy 3-tier math.

**Step 2:** Document in `docs/SESSION_BUNDLES.md`: "Rollback verified: env-var flip OFF restores Bundle E behavior end-to-end."

### Task D.7.2: Test Migration 024 rollback SQL in staging

This task is partially handled by D.3.3 (rollback drill on a branch). D.7.2 just verifies the rollback SQL is checked in + referenced:

- [ ] `migrations/rollback/024_*.sql` exists.
- [ ] Rollback SQL drops the `top_tier` value from the CHECK enum BUT does NOT touch user rows.
- [ ] Rollback SQL is idempotent (safe to run twice).
- [ ] Rollback SQL referenced in CLAUDE.md `### Migrations` section.

**Evidence:** D.3.3 drill outcome + file inspection notes inline in `docs/SESSION_BUNDLES.md`.

### Task D.7.3: Document non-destructive tier expansion (degradation path)

**Step 1:** Append to `docs/SESSION_BUNDLES.md` Bundle C entry, rollback subsection:

> Tier expansion is non-destructive. If we revert Migration 024 (e.g., emergency rollback) but leave the frontend 5-tier picker in place, persisted `users.preferences.budget = 'top_tier'` rows would violate the post-rollback CHECK. Mitigation if rollback needed: PRE-rollback migration step downgrades all `top_tier` and `luxury` rows to `premium`:
>
> ```sql
> UPDATE users SET preferences = preferences || jsonb_build_object('budget', 'premium')
> WHERE preferences->>'budget' IN ('top_tier', 'luxury');
> ```
>
> User-side UX impact: their saved preference silently degrades to `premium`; the picker still shows 5 tiers (UI is ungated and additive) but selecting `top_tier`/`luxury` will fail with a CHECK violation on save until the picker is also rolled back. This is acceptable for an emergency-only path.

**Step 2:** Add the downgrade SQL to a NEW file `migrations/rollback/024_pre_rollback_downgrade.sql` so it's checked into the repo for reuse. Commit:
```bash
git add migrations/rollback/024_pre_rollback_downgrade.sql
git commit -m "ops(bundle-c): pre-rollback downgrade SQL for tier expansion"
```

---

## D.8 — Disassembly Gate (BLOCKING)

Team disassembles ONLY when ALL of these are checked. NO premature disassembly. If ANY gate fails, the team continues until resolved.

### Gate checklist

- [ ] All Section A tasks complete + committed (verify by reading Section A's owner-files diff).
- [ ] All Section B tasks complete + committed.
- [ ] All Section C tasks complete + committed.
- [ ] Cross-QA matrix evidence captured (D.2.1 through D.2.7 all signed off with evidence files / messages).
- [ ] D.1 diagnostic findings shipped to `docs/SESSION_BUNDLES.md` (D.1.3 committed).
- [ ] D.1.4 confirmed: all diagnostic env vars disabled post-window.
- [ ] D.3 migrations applied via Supabase MCP + rollback drill done (D.3.1, D.3.2, D.3.3 all green).
- [ ] D.4.2 backwards-compat probes (flag OFF) match Bundle E baseline.
- [ ] D.4.3 flag-ON smoke probes confirm all 6 acceptance criteria.
- [ ] D.4.4 tier expansion UI works in both flag states.
- [ ] D.5 canary phasing documented (D.5.1, D.5.2, D.5.3).
- [ ] D.6.2 post-deploy 6-criteria acceptance ≥6 of 7 probes pass.
- [ ] D.6.3 ship evidence captured + committed.
- [ ] D.6.4 Sentry 24h baseline diff clean (≤5 unrelated low-sev new issues).
- [ ] D.6.5 EAS Update preview channel pushed + tester-device confirmed.
- [ ] D.7 rollback path verified end-to-end (env-var, migration, tier-degradation SQL).
- [ ] `pytest tests/ -v -m "not (live_unit or live_db or integration)" --timeout=180` 100% pass.
- [ ] `cd SmartCompareApp && npx tsc --noEmit` 0 errors.
- [ ] `pytest tests/test_security_regression.py -v` 100% pass.
- [ ] No PRE-EXISTING tests regressed (full-suite green).
- [ ] D.9 memory updates complete.

**If ANY gate fails:** team continues. NO premature disassembly. qa-bundle-c may NOT respond `approve: true` to a `shutdown_request` until every box above is checked. Per the CLAUDE.md rule: "Multi-agent silent stalls: escalate after 30 min" — if any peer is stuck silent, qa-bundle-c is the dispatcher-takeover candidate.

---

## D.9 — Memory updates (per CLAUDE.md operating principle 5)

After D.8 gate opens.

### Task D.9.1: Update CLAUDE.md with Bundle C breadcrumb (1 line max)

**Step 1:** Open `CLAUDE.md`. Find the "Bundle history" line under the `### Bundle history (sessions 44-50)` subsection. Append a 1-line Bundle C breadcrumb at the end of the comma-separated session list:

```
... **Session 50** ..., **Session 51** (Bundle C scoring quality pass + tier expansion + diag-first §1a/§1b/§1c + 3-pill confidence + personalization chip, head `<git-sha>`; flag `ENABLE_BUNDLE_C_SCORING=true` 100% canary).
```

**Step 2:** Verify CLAUDE.md line count stays under target (≤270 per memory note). If close to limit, trim the OLDEST session entry to a half-line.

**Step 3:** Commit:
```bash
git commit -m "docs(claude.md): Session 51 Bundle C breadcrumb" -- CLAUDE.md
```

### Task D.9.2: Update `docs/SESSION_BUNDLES.md` with full Bundle C entry

By this point, several subsections of `docs/SESSION_BUNDLES.md` have been appended in D.1.3, D.4.2, D.4.3, D.6.3, D.6.4, D.6.5, D.7.1, D.7.3. Now consolidate into a single coherent `## Bundle C — Scoring + Personalization Quality Pass (Session 51)` heading at the top:

- Summary paragraph: what shipped, why, head SHA.
- Diagnostic findings (§1a / §1b / §1c root causes).
- Migration 024 (applied via MCP, rollback drill outcome).
- Feature flag rollout (timing, smoke results).
- Canary state (100% pre-launch, trigger to drop to 10%).
- Ship evidence (7-probe acceptance table + granular criteria).
- Sentry baseline diff.
- EAS Update group ID.
- Rollback path summary.

**Step 1:** Re-organize. Commit:
```bash
git commit -m "docs(bundle-c): consolidate Bundle C session 51 entry" -- docs/SESSION_BUNDLES.md
```

### Task D.9.3: Update MEMORY.md pending follow-ups

**Step 1:** Open `C:/Users/SynAckITPC/.claude/projects/C--Users-SynAckITPC-Documents-AI-smartcompare/memory/MEMORY.md`. Find the "Bucket C brainstorm (scoring + personalization)" entry under "Pending follow-ups" and DELETE that line entirely (or replace with a short COMPLETED breadcrumb if memory discipline prefers).

**Step 2:** Also drop these resolved-or-superseded entries if no longer relevant:
- "D2 Section 3" entry — RESOLVED Session 50, can stay or be moved to a "Completed bundles" archive.

**Step 3:** Add NEW pending follow-up if D.5.2 deferred the canary-percent conversion:
```
- **Bundle C canary % conversion** — `ENABLE_BUNDLE_C_SCORING` is binary today. Convert to `BUNDLE_C_CANARY_PERCENT` numeric env var + `hash_bucket()` read at App Store soft-launch when tester pool > 10. Memory pointer: project_bundle_c_canary_trigger.md.
```

**Step 4:** Save the project memory file `memory/project_bundle_c_canary_trigger.md` (created in D.5.2) — verify it exists.

**Step 5:** No git commit for MEMORY.md (it's outside the repo, in `~/.claude/projects/...`).

---

## Cross-QA Matrix Quick Reference (re-stated)

```
backend-bundle-c   ──reviews──▶  frontend-bundle-c    (D.2.1)
frontend-bundle-c  ──reviews──▶  backend-bundle-c     (D.2.2)
test-bundle-c      ──reviews──▶  backend-bundle-c     (D.2.3)
test-bundle-c      ──reviews──▶  frontend-bundle-c    (D.2.4)
qa-bundle-c        ──reviews──▶  backend-bundle-c     (D.2.5)
qa-bundle-c        ──reviews──▶  frontend-bundle-c    (D.2.6)
qa-bundle-c        ──reviews──▶  test-bundle-c        (D.2.7)
```

Each peer-review pairing must complete BEFORE D.8 gate opens. qa-bundle-c reviews are the final layer.

---

## Send-Back Template (use this format)

When a reviewer finds an issue and sends work back to the implementer:

```markdown
## REVIEW: SEND BACK

**Reviewer:** <agent-name>
**Reviewing:** <other-agent-name>'s task <task-id>
**Status:** Send back

### What's wrong
<specific issue with file:line reference>

### What's missing
<specific deliverable not present>

### What's expected (per design doc or plan)
<quote from design doc with section reference, OR plan with task-id>

### Suggested fix or pointer
<concrete next step the implementer can take>

### Blocking gate
<which D.x gate this send-back blocks — usually D.2.x or D.8>
```

---

## Idle-work backlog (qa-bundle-c picks from this when waiting on peers)

Per cohort-plan team protocol: NEVER idle silently. While waiting on peers, work through these from top to bottom:

1. **Expand D.6.2 granular acceptance** — write per-category Phase 1 wall budgets into a checked-in file `tests/post_deploy/bundle_c_acceptance.md` so the next dispatcher can re-run mechanically.
2. **Draft Bundle C post-mortem questions** for the next-session triage: what surprised us in diagnostics? Did D.1's evidence change the implementation we'd planned? Did the 100% canary catch anything a 10% canary would have caught? Save to `docs/SESSION_BUNDLES.md` Bundle C entry under "Post-mortem questions".
3. **Write integration-test stubs** for `tests/test_bundle_c_integration.py` covering edge cases test-bundle-c didn't list (e.g., comparison where one product has `source_method=estimated` AND the other has `source_method=firecrawl` → confidence pill behavior). Stubs marked `@pytest.mark.skip(reason="bundle-c idle stub")` until test-bundle-c picks them up.
4. **Pre-write the PR body** so it's ready when D.8 opens (see PR template — to be added to plan-level Section "PR + handoff" if Section A/B/C don't cover it). Save to `/tmp/bundle-c-pr-body.md`.
5. **Re-read the design doc Section 0 (score-rendering principle)** and audit every committed change against the principle. Flag any drift via SendMessage.

If you exhaust all 5 idle-work items, post a `SendMessage to: "team-lead"` asking for a new direction. Do not request shutdown while peers are still working.

---

## Final acceptance (qa-bundle-c sign-off)

When D.8 gate is fully green, post a final broadcast:

> ALL D.x GATES PASSED. Bundle C ready for disassembly + PR. <ship-evidence-link>. <eas-update-group-id>. <railway-deploy-sha>. Cohort-style "safe to disassemble" — team can `approve: true` on `shutdown_request` cycle.

Only then may team agents respond `approve: true` to shutdown requests.


---

# Out of scope for this plan

Per design § 9:

- **Bucket B (two-input UX redesign)** — text + URL compare with paired input boxes. Separate dedicated brainstorm.
- **V2 logarithmic auto-scaling** for `other` category (design § 3g). Architecture leaves the swap point at `_detect_price_tier`.
- **Cohort badge merge with personalization chip** (design § 7d). Stays separate.
- **Targeted verdict re-prompt fallback** for empty pros/cons (design § 1a). Only ships if D.1 diagnostic proves the verdict model genuinely cannot fit all fields.
- **Top-up of API budget credits** (design § 1c potential fix). Operational not design.
- **Bundle C canary  onversion** — flag is binary today. Convert to `BUNDLE_C_CANARY_PERCENT` numeric + `hash_bucket()` at App Store soft-launch when tester pool > 10.

---
