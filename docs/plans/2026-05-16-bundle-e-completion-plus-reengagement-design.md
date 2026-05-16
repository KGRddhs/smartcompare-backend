# Bundle E Completion + Re-engagement Push Rollout — Design

> **For Claude:** This design captures decisions from a 2026-05-16 brainstorm.
> The implementation plan lives in `docs/plans/2026-05-16-bundle-e-completion-plus-reengagement.md`
> (created next via superpowers:writing-plans).

**Date:** 2026-05-16
**Status:** Approved (Bundle E scope = A / full; G rollout = D / flip-and-watch)
**Drives:** A 4-Opus TeamCreate dispatch.

---

## Context

Two pieces of partially-built work need closing out before App Store soft-launch:

1. **Bundle E — Results Quality Overhaul** (Session 47, PR #5 `00a2ec1`). Scoring V2 + dimensions[] contract shipped; **scatter-gather pricing pipeline + frontend rebuild are unfinished**. Per CLAUDE.md Session 47 note: the dispatcher absorbed Tasks 2.2–2.5, 3.1–3.8, and 4.4 directly because agents stalled — but the integration of `fan_out_price_lookup` into the live pipeline (Task 2.3) was never completed.
2. **G — Re-engagement Pushes.** `app/services/reengagement_service.py` + `scripts/cron_reengagement.py` + 3 detectors (`decision_insight`, `cohort_curiosity`, `decision_retrospective`) + 7-day per-user cap built. Gated by `ENABLE_REENGAGEMENT_PUSHES` (off in code; flag-check not yet wired through the daily cron). **Rollout strategy was not designed.**

## Brainstorm decisions

### Decision E-1: Bundle E scope = **A (Full)**

> Originally pitched: 84.5s → 10-15s. Today's reality (post-Redis fix): 25s → 10-15s. Win shrank but is still real, and the premium UX wins (radial rings, dimensions[] bars, evaluative-copy lint) are unaffected. User chose A — ship the full design.

Reference: `docs/plans/2026-05-13-results-quality-overhaul-design.md` (canonical design) +
`docs/plans/2026-05-13-results-quality-overhaul.md` (canonical plan). **No changes.** This design doc just confirms execution of the unfinished portions.

### Decision G-1: Re-engagement rollout = **D (Flip-and-watch)**

> With <10 testers pre-launch, percentage canary buckets are statistically meaningless.

Plan:
- Set `ENABLE_REENGAGEMENT_PUSHES=true` on Railway after cron job lands + flag-check wires through `reengagement_service.evaluate_user()`.
- **Pre-launch monitoring:** Sentry for backend errors + Expo push-receipt failure rate via existing `push_service.send()` instrumentation. Kill via Railway env-flag flip if either spikes >5% from baseline.
- **Post-soft-launch:** add `REENGAGEMENT_CANARY_PERCENT` env + `featureBucket.ts`-style `hashBucket(user_id, percent)` gating. Ramp 10 → 50 → 100% over ~1 week. **Build canary infrastructure in this Bundle even though we ship at 100%** — wiring it after launch is harder than wiring it now.
- **No per-detector ramp.** All 3 detectors enabled together. 7-day per-user cap already protects against fatigue.

## What ships in this Bundle

### Backend (Bundle E unfinished — references existing plan)

| Source | Task | Status |
|---|---|---|
| `docs/plans/2026-05-13-results-quality-overhaul.md` | **Task 2.1** quality ranker `select_best_price()` | finish if not done |
| same | **Task 2.2** `price_service.fan_out_price_lookup()` parallel scrapers + cancellation | exists in code per grep; verify integration with Task 2.3 |
| same | **Task 2.3** refactor `structured_comparison_service.compare_from_text_streaming()` to scatter-gather + 13s first-paint + 25s settle window | **THE MISSING INTEGRATION** — wires Task 2.2 into the live request path |
| same | **Task 2.5** new SSE event types `first_paint`, `settle_update`, `settle_complete`, `confidence_upgrade` in `app/api/text_routes.py` | wire in same PR as Task 2.3 |
| `docs/plans/2026-05-16-scraping-mode-gate-wiring.md` | Inline `should_fan_out()` gate at the two existing scraper call sites — **superseded by Task 2.3** (the scatter-gather refactor builds the gate in naturally). Close the gate-wiring plan as redundant once Task 2.3 lands. | — |

### Backend (Re-engagement)

| Surface | Change |
|---|---|
| `app/services/reengagement_service.py` | Read `ENABLE_REENGAGEMENT_PUSHES` env at evaluation time. Fail-CLOSED (no pushes sent) when flag off. **The flag MUST gate `evaluate_user()` itself, not just the cron** — protects against ad-hoc invocations. |
| `scripts/cron_reengagement.py` | Skip the run entirely if flag is off (log "ENABLE_REENGAGEMENT_PUSHES=false, skipping"). |
| `app/services/reengagement_service.py` | Add `REENGAGEMENT_CANARY_PERCENT` env (default 100). Use existing `hashBucket(user_id, percent)` pattern (lift from `SmartCompareApp/src/services/featureBucket.ts` — same djb2 hash, Python implementation. New helper at `app/utils/feature_bucket.py`). |
| `tests/test_reengagement_service.py` (extend) | RED tests for: flag-off → no pushes; flag-on + canary 0% → no pushes; flag-on + canary 100% → all eligible users get pushes; deterministic bucketing (same user always same bucket). |

### Frontend (Bundle E unfinished — references existing plan)

Per `docs/plans/2026-05-13-results-quality-overhaul.md` § Phase 3 Frontend:
- Radial-ring hero card on Results screen (Reanimated + react-native-svg)
- Dimension bars with confidence color coding
- Banned-vocabulary lint pass + AI-proofread Arabic for new copy
- SSE handlers for `first_paint`, `settle_update`, `settle_complete`, `confidence_upgrade`
- Defensive `result?` guards everywhere (Bundle E QA caught a few)
- Falls back to legacy keys when backend serves old `scoring` shape (one-release backward-compat)

## Team composition

**4 Opus agents** dispatched via TeamCreate with `mode: "bypassPermissions"`. All Opus, no Sonnet, no Haiku. Cross-QA before disbanding. Reference: CLAUDE.md "Agent Team Pattern (Session 26+)".

| Agent | Codename | Domain | Primary deliverables |
|---|---|---|---|
| **A** | `backend-opus` | Python / FastAPI / asyncio / scoring / scraping pipeline | Bundle E Tasks 2.1–2.3, 2.5 backend; Re-engagement flag wiring + canary helper + tests |
| **B** | `frontend-opus` | React Native / Expo / Reanimated / SVG / SSE / TypeScript | Bundle E Phase 3 frontend (rings, bars, copy, SSE handlers, fallbacks) |
| **C** | `test-opus` | TDD authoring — pytest + jest red-green tests | Failing tests for every backend AND frontend task BEFORE implementation; coverage gate ≥80% on new files; existing-regression watch |
| **D** | `qa-opus` | Cross-QA reviewer — integration tests + manual checklist + perf bench | Phase 4 integration; perf bench (cold-cache cross-category, same-category, luxury, supplements); regression gating; final sign-off |

### Cardinal rules (every agent honors)

1. **All Opus.** `model: "opus"` on every TeamCreate member.
2. **The feature ships 100% complete or the team does not disassemble.** A task is "complete" only when test passes AND a peer (different agent) cross-QAs the diff and signs off.
3. **Path-restricted commits.** `git commit -m "msg" -- <paths>` to avoid sweeping teammates' staged work.
4. **30-min silent-stall escalation.** Per CLAUDE.md Session 47 lesson: if an agent goes silent past 30 min with uncommitted state on disk despite SendMessage nudges, dispatcher absorbs the task directly. No self-rescue.
5. **No fabricated values.** Use real env vars, real type names. Read before edit.
6. **TDD strict.** RED before GREEN. Verify the test fails before implementing.
7. **One commit per task.** Squash intermediate work.

### Cross-QA matrix

| Task delivered by | QA'd by |
|---|---|
| backend-opus (Bundle E backend) | qa-opus + test-opus |
| backend-opus (re-engagement) | qa-opus |
| frontend-opus (Bundle E UI) | qa-opus + test-opus |
| test-opus (test scaffolding) | the agent who owns the implementation |
| qa-opus (integration tests) | dispatcher |

## Risks + mitigations

| Risk | Mitigation |
|---|---|
| Sandbox network restrictions block worktree agents from `pip install` or `npm install` | Pre-fetch dependencies in main session before dispatch; pin versions in prompt. **Or** dispatch in `mode: "bypassPermissions"` AND verify a sandbox-bypass-clean test run before assigning real work. |
| Scatter-gather refactor regresses existing comparisons (price drops, missing fields) | qa-opus runs cold-cache regression suite across 4 categories before sign-off. Roll back via revert if any category degrades. |
| Re-engagement pushes annoy testers if 7-day cap isn't strictly enforced | qa-opus writes a 14-day simulation test in `test_reengagement_service.py` that runs 30 fake users through 14 days of synthetic events and asserts no user gets >2 pushes. |
| Canary helper bucketing drifts from frontend `featureBucket.ts` djb2 hash → users get different cohorts across sessions | test-opus writes a cross-language parity test: hash N user IDs in Python AND TypeScript, assert identical bucket assignments. |
| Stale worktrees from prior dispatcher runs interfere with new team worktrees | Dispatcher cleans up `.claude/worktrees/agent-*` before team dispatch. |

## Out of scope for this bundle

- Sentry RN SDK (separate parallel agent, in flight as of 2026-05-16)
- Wrangler v3→v4 (separate parallel agent)
- value_context per-product fix (separate parallel agent)
- Scrape.do timeout fix — investigation done (`docs/investigations/2026-05-16-scrapedo-timeout-analysis.md`), recommendation is **accept current behavior**, no code change
- App Store soft-launch decisions (B) — separate brainstorm, decisions-only by you

## Success criteria (qa-opus signs off when ALL pass)

- [ ] Cold-cache non-luxury comparison ≤15s p95 on Railway preview (was 25s before refactor)
- [ ] Cold-cache luxury comparison ≤25s p95
- [ ] Cached comparison <2s p95
- [ ] All existing pytest + jest tests pass; new tests added with ≥80% coverage of new files
- [ ] Re-engagement: flag off → zero pushes (verified by 24h dry-run before flip)
- [ ] Re-engagement: per-user cap holds in 14-day simulation
- [ ] No new Sentry issues at sustained baseline rate
- [ ] Frontend: no banned-vocabulary copy strings (lint passes)
- [ ] Frontend: no React errors in dev console during normal comparison flow

---

**Next step:** `superpowers:writing-plans` produces `docs/plans/2026-05-16-bundle-e-completion-plus-reengagement.md` — the bite-sized task list TeamCreate will execute against.
