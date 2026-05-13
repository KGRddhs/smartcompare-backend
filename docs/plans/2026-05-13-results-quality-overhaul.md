# Bundle E — Results Quality Overhaul Implementation Plan (4-Opus Team)

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans + superpowers:dispatching-parallel-agents to dispatch the team and orchestrate cross-QA gates.

**Goal:** Eliminate every quality flaw from the Glorious-mouse-vs-Ducky-keyboard tester walkthrough: history crash, dead buttons, empty score bars, simulated numbers, evaluative copy, 84.5s latency. Result must always look complete and feel premium regardless of what the user compares.

**Architecture:** Backend emits a self-describing `dimensions[]` contract with a guaranteed core (Price / Reviews / Value) + 0-3 contextual extras — never an incomplete dimension. Scoring re-calibrated so above-average commercial products land in the 80-89 range. Scraping moves from sequential tiers to scatter-gather fan-out with a quality ranker and 13s first-paint + 25s settle window. Frontend rebuilds the Results "answer" card around two animated radial rings + factual delta line + dimension bars. All evaluative copy ("Best Pick", "Excellent") replaced with match-based, fact-based, attributed, or conditional framing per legal-safe rules.

**Tech Stack:** Python 3.12 + FastAPI + asyncio (backend), React Native + Expo + Reanimated + react-native-svg (frontend), Supabase Postgres, Upstash Redis, OpenAI GPT-4o-mini, Serper, Firecrawl, Scrape.do, curl_cffi.

**Design doc:** `docs/plans/2026-05-13-results-quality-overhaul-design.md`

---

## Team Charter

### Roster — 4 Opus agents (no Sonnet, no Haiku)

| Agent | Codename | Domain | Primary deliverables |
|---|---|---|---|
| **Agent A** | `backend-opus` | Python / FastAPI / scoring / scraping pipeline | Phase 1 (foundation) + Phase 2 (scatter-gather) backend |
| **Agent B** | `frontend-opus` | React Native / Expo / SSE / TypeScript | Phase 0 hotfixes + Phase 3 (rings, bars, copy) frontend |
| **Agent C** | `test-opus` | TDD authoring — pytest + jest red-green tests | Failing tests for every task BEFORE implementation; coverage gate ≥80% on all new files |
| **Agent D** | `qa-opus` | Cross-QA reviewer — integration tests + manual checklist + perf bench | Phase 4 integration + perf + regression gating |

### Cardinal rules (every agent must honor)

1. **All agents are Opus.** When dispatching via `TeamCreate`, set `model: "opus"` on every member. No Sonnet, no Haiku — no exceptions.
2. **The feature ships 100% complete or the team does not disassemble.** A task is "complete" only when:
   - Implementation merged into `feature/bundle-e-results`
   - Red-green tests authored by Agent C pass
   - Cross-QA sign-off from at least ONE other agent (logged in `docs/plans/2026-05-13-bundle-e-qa-log.md`)
   - For Phase 4 tasks: Agent D's manual checklist passes
3. **Cross-QA is blocking.** Before any agent declares its work done, the assigned reviewer (see Matrix below) must inspect the work and reply with one of:
   - `SIGN-OFF` (work meets spec, no defects)
   - `SEND-BACK: <specific defects with file:line>` — author must fix and resubmit
   - Reviewer never gives a vague "looks good" — sign-off requires explicit verification commands run.
4. **Idle protocol.** An agent with no in-flight task MUST choose ONE of:
   - **(a)** Write red-green tests for an upcoming task in their domain (target: bring coverage on the new file to ≥80% before implementation lands)
   - **(b)** Wait in observe-mode for a cross-QA request from another agent
   - Never invent work outside the plan. Never refactor unrelated code. Never edit files outside their assigned domain.
5. **Path-restricted commits.** Use `git commit -m "msg" -- <paths>` to avoid sweeping teammates' staged work. Order matters: `-m` BEFORE `--`. (See CLAUDE.md Operating Principle #6.)
6. **Worktree:** All work happens in `../smartcompare-bundle-e` on branch `feature/bundle-e-results`. No direct-to-main except the Phase 0 hotfix cherry-pick (explicit step in Task 0.3).
7. **One file at a time per agent** unless the change is genuinely atomic. Two agents must never edit the same file in the same dispatch round.

### Cross-QA matrix

| Author | Reviewer | Focus |
|---|---|---|
| Agent A (backend) | Agent D (qa) | Spec correctness, no banned vocab in delta_text, calibration math, SSE contract |
| Agent A (backend) | Agent C (test) | Test coverage on new files ≥80%, all red-green tests genuinely fail before impl |
| Agent B (frontend) | Agent D (qa) | UI matches design doc § Decision 3 + Decision 5, RTL pass, manual flow on device |
| Agent B (frontend) | Agent C (test) | jest coverage on new components ≥80%, copy-policy ESLint rule fails on banned words |
| Agent C (test) | Agent A or B | Tests are red-green (verify they fail before impl exists), not just snapshot-stamps |
| Agent D (qa) | Agent A | Integration test fixtures match real backend contract |

Two reviewers per author means every PR has at least 2 sign-offs in the QA log before merge.

---

## Worktree Setup (the dispatcher does this BEFORE TeamCreate)

```bash
git worktree add -b feature/bundle-e-results ../smartcompare-bundle-e main
cd ../smartcompare-bundle-e
cd SmartCompareApp && npm install && cd ..
python -m pip install -r requirements.txt
```

Verify clean state (dispatcher runs all three):
- `git status` → clean
- `python -m pytest tests/ -v -m "not (live_unit or live_db or integration)" --ignore=tests/test_integration.py` → green
- `cd SmartCompareApp && npx tsc --noEmit && npm test -- --watchAll=false` → green

Create the cross-QA log file (empty):

```bash
touch docs/plans/2026-05-13-bundle-e-qa-log.md
```

Format for entries (every cross-QA action gets a line):

```
[2026-05-13 14:32 | Agent D → Agent A | Task 1.2] SIGN-OFF — calibration math verified, 8/8 tests pass.
[2026-05-13 14:45 | Agent C → Agent B | Task 3.2] SEND-BACK — HeroRings.tsx:42 uses orange #F59E0B for losing ring; design § 3 forbids orange. Replace with colors.neutral.gray400.
```

---

## TeamCreate dispatch (the launch command)

```ts
TeamCreate({
  team_name: "bundle-e-results",
  members: [
    { name: "backend-opus",  agent: "general-purpose", model: "opus",
      prompt: "<see Agent A mission below>", mode: "bypassPermissions" },
    { name: "frontend-opus", agent: "general-purpose", model: "opus",
      prompt: "<see Agent B mission below>", mode: "bypassPermissions" },
    { name: "test-opus",     agent: "general-purpose", model: "opus",
      prompt: "<see Agent C mission below>", mode: "bypassPermissions" },
    { name: "qa-opus",       agent: "general-purpose", model: "opus",
      prompt: "<see Agent D mission below>", mode: "bypassPermissions" },
  ],
})
```

---

## Agent Mission Briefs

### Agent A — backend-opus

**Domain:** `app/**` Python files only. Never touch `SmartCompareApp/`.

**Task list (sequential within domain; each task is one commit):**

- **Task 1.1** — Create `app/models/scoring_v2.py` per design doc § Decision 2.
- **Task 1.2** — Add `calibrate_score()` to `app/services/scoring_service.py` per § Decision 4.
- **Task 1.3** — Add `build_dimensions_v2()` to `app/services/scoring_service.py` per § Decision 2 contract.
- **Task 1.4** — Create `app/services/verdict_builder.py` with `build_factual_verdict()` per § Decision 5.
- **Task 1.5** — Modify `app/services/fact_check_service.py` to omit default `overall_confidence` pill per § Decision 7.
- **Task 1.6** — Modify `app/services/response_builder.py` to emit `scoring_v2` alongside legacy `scoring` (backward-compat one release).
- **Task 2.1** — Create `app/services/quality_ranker.py` with `select_best_price()` per § Decision 8.
- **Task 2.2** — Refactor `app/services/price_service.py` to `fan_out_price_lookup()` with parallel scrapers + cancellation.
- **Task 2.3** — Modify `app/services/structured_comparison_service.py::compare_from_text_streaming()` to scatter-gather + settle window (13s first paint, 25s hard cap).
- **Task 2.4** — Add `SCRAPING_MODE` env switch in `app/main.py` (hard | soft).
- **Task 2.5** — Modify `app/api/text_routes.py` to emit `first_paint`, `settle_update`, `confidence_upgrade`, `settle_complete` SSE event types.

**TDD discipline for every task:**
1. Receive failing tests from Agent C BEFORE coding (or write them yourself if Agent C is mid-flight on another).
2. Verify the test fails: `python -m pytest <test> -v` → expect FAIL.
3. Implement the minimal code to make it pass.
4. Verify pass.
5. Run the full pytest suite to catch regressions:
   ```bash
   python -m pytest tests/ -v --timeout=180 -m "not (live_unit or live_db or integration)" --ignore=tests/test_integration.py
   ```
6. Commit with path-restricted git add:
   ```bash
   git add app/models/scoring_v2.py tests/test_scoring_v2_models.py
   git commit -m "feat(scoring): add ScoringV2 dimensions[] contract" -- app/models/scoring_v2.py tests/test_scoring_v2_models.py
   ```
7. Request cross-QA from Agent D (sign-off) AND Agent C (coverage check).
8. Wait for SIGN-OFF before moving to next task.

**Hard rules:**
- `Dimension.delta_text` MUST pass the evaluative-language validator. If it fails, that's a bug in your phrasing — fix it, do not relax the validator.
- Calibration is monotonic — winners must still rank correctly. If a calibration change flips a winner, that's a bug.
- `fan_out_price_lookup` MUST cancel still-pending scrapers when 2+ sources confirm within 5%. Verify cancellation in test.
- Hard 25s cap is non-negotiable. Add `asyncio.wait_for(timeout=25)` at the outermost level.

**Idle protocol for Agent A:**
- (a) Write pytest red-green tests for upcoming backend tasks if Agent C is behind.
- (b) Cross-QA Agent A's domain when Agent D requests.
- Never edit frontend, never refactor unrelated services.

---

### Agent B — frontend-opus

**Domain:** `SmartCompareApp/**` TypeScript/TSX files only. Never touch `app/`.

**Task list (Phase 0 first, then Phase 3):**

**Phase 0 hotfixes (highest priority — these ship FAST):**
- **Task 0.1** — Add `?.` to `ResultsScreen.tsx:210` + empty-state guard at top of component. Fix the history → Results crash.
- **Task 0.2** — Delete "What's next?" + "Save" buttons from `ResultsScreen.tsx`. Remove `results.whatsNext` + `results.save` i18n keys.
- **Task 0.3** — DISPATCHER ONLY (not Agent B): cherry-pick 0.1 + 0.2 to main, push, EAS update.

**Phase 3 frontend rebuild:**
- **Task 3.1** — Add `Dimension`, `OverallScore`, `ScoringV2`, `ComparisonResultV2` types to `SmartCompareApp/src/types/index.ts`.
- **Task 3.2** — Create `SmartCompareApp/src/components/results/HeroRings.tsx` per § Decision 3 visuals. SVG circles, Reanimated worklet, emerald (winner) + gray (other) only.
- **Task 3.3** — Create `SmartCompareApp/src/components/results/DimensionBars.tsx`. One row per dimension. Throws if a dimension has score 0 (defensive — backend should never emit those).
- **Task 3.4** — Create `SmartCompareApp/src/components/results/TopMatchBadge.tsx` + `FactualVerdict.tsx`.
- **Task 3.5** — Wire all new components into `ResultsScreen.tsx`. Read from `scoring_v2` if present; fall back to legacy `scoring` for one release.
- **Task 3.6** — Extend `SmartCompareApp/src/services/api.ts::streamComparison()` to dispatch `first_paint`, `settle_update`, `confidence_upgrade`, `settle_complete` events. In-place state merge on settle_update (no remount).
- **Task 3.7** — Copy policy: create `.copy-policy.json`, scrub banned keys from `en.json` + `ar.json`, add new keys, create ESLint rule `qaren/no-evaluative-copy`, register in `eslint.config.js`.
- **Task 3.8** — Add `common.or` i18n key (deferred from Bundle B/C/D).

**TDD discipline:** Same as Agent A but with jest:
1. Receive failing jest tests from Agent C.
2. Verify FAIL: `npx jest <test-path> --no-coverage`.
3. Implement minimal code.
4. Verify PASS.
5. Run full jest + tsc + eslint:
   ```bash
   cd SmartCompareApp
   npx jest --watchAll=false
   npx tsc --noEmit
   npx eslint src/ --max-warnings 0
   ```
6. Path-restricted commit.
7. Request cross-QA from Agent D + Agent C.
8. Wait for SIGN-OFF.

**Hard rules:**
- Never use orange or red on any score bar/ring/badge. Only emerald (`colors.accent`) for winners and gray (`colors.neutral.gray400`) for losers. Verify by grepping your new files: `grep -r "F59\|orange\|destructive\|dc2" SmartCompareApp/src/components/results/` → must return 0 lines.
- Every new component must have `testID` props on key elements so tests + manual QA can verify.
- AR strings come from i18n only — never hardcode Arabic strings in TSX. Run `npx eslint --rule 'i18next/no-literal-string: error' src/components/results/` after each task.
- Hero rings size: 88px diameter, 8px stroke (per design doc). Do not improvise.

**Idle protocol for Agent B:**
- (a) Write jest red-green tests for upcoming frontend tasks if Agent C is behind.
- (b) Cross-QA when Agent D requests.
- Never edit backend, never refactor unrelated screens.

---

### Agent C — test-opus

**Domain:** `tests/**` (pytest) AND `SmartCompareApp/__tests__/**` (jest). Authors red-green failing tests for every task before implementation lands.

**Task list (parallel with A + B; tests must exist BEFORE the implementing agent starts):**

- **Test-1.1** — `tests/test_scoring_v2_models.py` — 4 tests covering Dimension required fields, evaluative-language validator, ≥3 core requirement, max 6 dimensions.
- **Test-1.2** — `tests/test_scoring_calibration.py` — parametrized test for the calibrate_score curve (50→70, 70→80, 90→90, 30→60, clamp 60/95) + honesty guard.
- **Test-1.3** — `tests/test_dimensions_builder.py` — emits 3 core; skips dimension when data incomplete on either side; delta_text is factual only; cross-category emits universal dims only.
- **Test-1.4** — `tests/test_verdict_builder.py` — no score numbers, no evaluative words, uses delta_text, conditional alternative for runner-up.
- **Test-1.5** — `tests/test_fact_check_service.py` — overall_confidence omitted when data is normal; data_freshness flagged only when shaky.
- **Test-2.1** — `tests/test_quality_ranker.py` — confirmed-multi-source wins, highest-rank wins when no confirmation, empty candidates returns None.
- **Test-2.2** — `tests/test_scatter_gather_price.py` — fan-out runs concurrently (max not sum); first valid high-rank cancels others.
- **Test-2.3** — `tests/test_sse_settle_window.py` — first_paint precedes settle_complete; first_paint within 13s.
- **Test-2.4** — `tests/test_scraping_mode.py` — soft mode skips Firecrawl non-luxury; hard mode always fires.
- **Test-3.2** — `SmartCompareApp/__tests__/components/HeroRings.test.tsx` — renders two rings, emerald winner / gray loser, never orange/red.
- **Test-3.3** — `__tests__/components/DimensionBars.test.tsx` — one row per dimension, throws on zero score, low-confidence opacity 0.6 + "≈" prefix.
- **Test-3.4** — `__tests__/components/TopMatchBadge.test.tsx` + `FactualVerdict.test.tsx` — banned-word checks.
- **Test-3.5** — `__tests__/screens/ResultsScreen.integration.test.tsx` — uses scoring_v2 when present, falls back to legacy.
- **Test-3.6** — `__tests__/services/api.settle.test.ts` — streamComparison emits all 4 event types to callbacks.
- **Test-3.7** — `__tests__/copy-policy.test.ts` — en.json + ar.json contain no banned words.
- **Test-0.1, 0.2** — `__tests__/screens/ResultsScreen.test.tsx` — defensive guard tests + button-removal assertions.

**Discipline:**
1. Read the corresponding design doc section before writing tests.
2. Write the test using the exact code snippets in the design doc.
3. **Verify the test FAILS before signaling Agent A or B to start.** Run the test against the current (un-implemented) codebase: `pytest <test> -v` must show RED. This is the red half of red-green. A test that passes against missing code is a false-positive — investigate (likely a stub or mock that should be removed).
4. Post in QA log: `[timestamp | Agent C | Test-X.Y] RED — verified failing, ready for implementation by Agent A/B`.
5. After Agent A/B commits the implementation, run the test again — it must be GREEN.
6. If GREEN: post `[timestamp | Agent C → Agent A | Task X.Y] SIGN-OFF — coverage X% on new file`.
7. If RED still: post `[timestamp | Agent C → Agent A | Task X.Y] SEND-BACK — <specific failure with assertion message>`.

**Coverage gate:** Every new file must hit ≥80% statement coverage. Run:

```bash
python -m pytest tests/ --cov=app/models/scoring_v2 --cov=app/services/quality_ranker --cov=app/services/verdict_builder --cov-report=term-missing
cd SmartCompareApp && npx jest --coverage --collectCoverageFrom='src/components/results/**'
```

If any new file is <80%, write additional tests OR send back to the implementer with the missing-line numbers.

**Idle protocol for Agent C:**
- (a) Write tests for upcoming tasks ahead of schedule.
- (b) Run mutation testing on critical new files (`mutmut run --paths-to-mutate app/services/quality_ranker.py`) — kill rate ≥80%.
- (c) Cross-QA an Agent A or B commit when requested.

**Hard rule:** Never delete or skip a failing test to make the suite green. If a pre-existing test breaks due to Bundle E changes, that's a regression — flag it and send back to the author who broke it.

---

### Agent D — qa-opus

**Domain:** Integration tests in `tests/test_bundle_e_integration.py`, perf bench in `tests/perf/test_latency_bench.py`, manual QA checklist `docs/plans/2026-05-13-bundle-e-qa-checklist.md`, and the QA log `docs/plans/2026-05-13-bundle-e-qa-log.md`.

**Task list (most are reactive — triggered by other agents requesting cross-QA):**

- **Task 4.1** — Create `tests/test_bundle_e_integration.py` with the original-failure-case e2e (mouse vs keyboard → no empty dimensions, calibrated scores ≥70, no evaluative verbose).
- **Task 4.2** — Create `tests/perf/test_latency_bench.py` with P50/P95 first-paint bench (20 cold queries).
- **Task 4.3** — Create + maintain `docs/plans/2026-05-13-bundle-e-qa-checklist.md` (manual on-device checks).
- **Task 4.4** — Run the full regression gauntlet before final sign-off:
  ```bash
  python -m pytest tests/ -v --timeout=180 -m "not (live_unit or live_db or integration)" --ignore=tests/test_integration.py
  python -m pytest tests/test_security_regression.py -v
  cd SmartCompareApp && npx jest --watchAll=false && npx tsc --noEmit && npx eslint src/ --max-warnings 0
  ```
  All must be green. Any red is a SEND-BACK.
- **Task 4.5** — Run perf bench against Railway preview deploy after Phase 2 lands. Document results in `docs/runbooks/bundle-e-perf-bench.md`.
- **Task 4.6** — Final manual QA on Ahmed's device: walk through the checklist, sign off each row. Run the original mouse-vs-keyboard query and verify every original symptom is gone.

**Cross-QA reactive tasks:**

When Agent A or B requests cross-QA, run this protocol:
1. `git diff main..feature/bundle-e-results -- <files-author-touched>` — read every line of the diff.
2. Run the test suite the author claims is green: paste the actual exit code in the QA log.
3. Verify each design doc requirement listed in the cross-QA matrix for that author.
4. For backend: `grep -E "best|winner|excellent|great" app/services/verdict_builder.py app/services/scoring_service.py` → must be empty (case-insensitive, in user-facing strings only).
5. For frontend: visual diff on Expo Go (Ahmed's device or AVD) — compare to the design doc § 3 ascii sketch.
6. Post SIGN-OFF or SEND-BACK in the QA log with explicit evidence.

**Hard rules:**
- Never approve a "looks good" without running the verification commands.
- If you find a defect, the SEND-BACK must point to file:line and quote the design-doc requirement violated.
- You are the final gate before merge. If you sign off and the bundle ships broken, that's on the team — be thorough.

**Idle protocol for Agent D:**
- (a) Run mutation testing (`mutmut`) on backend critical files.
- (b) Manually exercise the Expo Go app on AVD, hunt for bugs outside the design scope but ON the touched surfaces.
- (c) Update the cross-QA log with structural improvements (group entries by task).

---

## Phase-by-Phase Orchestration (the dispatcher's playbook)

### Phase 0 — Hotfix sprint (Day 1, ~2 hours total)

**Goal:** Ship Tasks 0.1 + 0.2 to main as hotfix, before deep Bundle E work begins.

**Sequence:**
1. Dispatcher creates worktree, runs verification.
2. Dispatch only Agent B + Agent C with Phase 0 tasks. Agents A and D stay idle (Agent C can pre-author Phase 1 tests, Agent A can pre-read the design doc).
3. Agent C writes failing tests for 0.1 and 0.2 first. Verifies RED.
4. Agent B implements 0.1, then 0.2. Verifies GREEN.
5. Agent D cross-QAs both tasks.
6. **DISPATCHER (not Agent B)** runs Task 0.3: cherry-pick to main, push, EAS update.
7. Phase 0 complete. Now ramp up Phases 1-3.

### Phase 1 + 2 — Backend foundation + pipeline (Days 2-4)

1. Agent C writes failing tests for all Phase 1 + 2 tasks, verifies RED, posts to QA log.
2. Agent A implements 1.1 → 1.2 → 1.3 → 1.4 → 1.5 → 1.6 → 2.1 → 2.2 → 2.3 → 2.4 → 2.5 sequentially.
3. After each task: Agent A requests cross-QA from D + C. Must get SIGN-OFF from BOTH before moving to next task.
4. If SEND-BACK: Agent A pauses, fixes, re-requests. Agent A does not move on with red work.
5. Agent B in idle: pre-authors Phase 3 jest tests OR waits.
6. Agent D in idle: cross-QAs, runs perf checks on intermediate Railway preview deploys.

### Phase 3 — Frontend rebuild (Days 4-6, can start parallel to late Phase 2)

1. Agent C writes failing jest tests for 3.1-3.8, verifies RED.
2. Agent B implements 3.1 → 3.2 → 3.3 → 3.4 → 3.5 → 3.6 → 3.7 → 3.8.
3. Cross-QA after each.
4. Agent B may start Phase 3 as soon as Task 1.6 lands (backend emits `scoring_v2` — frontend can wire to it).

### Phase 4 — QA gauntlet (Day 7)

1. Agent D runs the full regression suite (Task 4.4). Any red is a blocker.
2. Agent D runs the perf bench (Task 4.5). P50 ≤10s, P95 ≤14s required.
3. Agent D walks the manual checklist on Ahmed's device (Task 4.6).
4. If all green: Agent D posts FINAL-SIGN-OFF in QA log.
5. **DISPATCHER (not any agent)** opens PR, merges with squash, pushes EAS update.

---

## 100%-Complete Definition (the team cannot disassemble until ALL of these are green)

Run by the dispatcher before issuing `TeamDelete`:

```bash
# 1. All design-doc decisions implemented
grep -c "SIGN-OFF" docs/plans/2026-05-13-bundle-e-qa-log.md   # ≥ 18 (9 tasks × 2 reviewers)

# 2. Full backend regression
python -m pytest tests/ -v --timeout=180 -m "not (live_unit or live_db or integration)" --ignore=tests/test_integration.py
# ↑ exit 0 required

# 3. Security regression
python -m pytest tests/test_security_regression.py -v
# ↑ 98/98 PASS required

# 4. Frontend gauntlet
cd SmartCompareApp
npx jest --watchAll=false
npx tsc --noEmit
npx eslint src/ --max-warnings 0
# ↑ all exit 0 required

# 5. Coverage gates on new files
python -m pytest tests/ \
  --cov=app/models/scoring_v2 \
  --cov=app/services/quality_ranker \
  --cov=app/services/verdict_builder \
  --cov-fail-under=80
cd SmartCompareApp && npx jest --coverage \
  --collectCoverageFrom='src/components/results/**' \
  --coverageThreshold='{"global":{"statements":80}}'

# 6. Integration test (live backend)
python -m pytest tests/test_bundle_e_integration.py -v -m integration
# ↑ exit 0 required

# 7. Perf bench
python -m pytest tests/perf/test_latency_bench.py -v -m bench
# ↑ P50 ≤10s, P95 ≤14s

# 8. Manual QA checklist 100% checked
grep -c "^\[x\]" docs/plans/2026-05-13-bundle-e-qa-checklist.md   # = total checklist items

# 9. Banned-word grep (extra paranoia)
grep -riE "best pick|smart pick|excellent|recommend " SmartCompareApp/src/i18n/
# ↑ exit 1 required (i.e., zero matches)

# 10. PR merged
gh pr view feature/bundle-e-results --json state  # state: "MERGED"
```

If any of 1-10 is not green, the team continues. The dispatcher does NOT call `TeamDelete` until everything is green.

---

## Disassembly procedure

Only after all 10 gates above are green:

1. Dispatcher posts `[2026-05-XX HH:MM | DISPATCHER] All 10 gates green. Disassembling team.` in QA log.
2. `TeamDelete({ team_name: "bundle-e-results" })`.
3. Update `CLAUDE.md` § "Bundle E (PR #X merged YYYY-MM-DD)" with summary.
4. Update `MEMORY.md` with Session-47-style entry.
5. Run `eas update --branch preview --message "Bundle E live"` if not already done.

---

## SEND-BACK protocol (when QA finds a defect)

When Agent D or C posts SEND-BACK on Agent A or B's work:

1. Agent A/B reads the SEND-BACK in QA log.
2. Agent A/B does NOT argue. If the spec says "no orange" and you used orange, you fix it. Discussion of design decisions happens BEFORE coding, not after QA.
3. Agent A/B fixes the defect, re-runs the same verification the reviewer ran, commits the fix with `fix(...)` prefix.
4. Agent A/B re-requests cross-QA from the SAME reviewer (same person verifies their feedback was addressed).
5. Reviewer either SIGN-OFF (defect resolved) or SEND-BACK again (only if a NEW defect or the same defect not actually fixed).
6. **Three SEND-BACKs on the same task** = dispatcher steps in, reviews the situation, may escalate to a fresh agent or revise the design.

---

## Idle reporting

Any agent that has been idle for >15 minutes posts in QA log:

```
[timestamp | Agent X] IDLE — chose option (a) writing tests for Test-Y.Z OR (b) waiting on cross-QA from Agent Z.
```

This makes it visible whether the team is blocked or just waiting on long-running tasks.

---

## Files Created/Modified Summary

### Backend (Agent A)

| File | Action |
|---|---|
| `app/models/scoring_v2.py` | Create |
| `app/services/scoring_service.py` | Modify (add calibrate_score, build_dimensions_v2) |
| `app/services/verdict_builder.py` | Create |
| `app/services/fact_check_service.py` | Modify (omit overall_confidence default) |
| `app/services/response_builder.py` | Modify (emit scoring_v2) |
| `app/services/quality_ranker.py` | Create |
| `app/services/price_service.py` | Modify (fan_out_price_lookup, cancellation) |
| `app/services/structured_comparison_service.py` | Modify (scatter-gather + settle window) |
| `app/services/firecrawl_service.py` | Modify (cancellable wrapper) |
| `app/services/scrapedo_service.py` | Modify (cancellable wrapper) |
| `app/api/text_routes.py` | Modify (new SSE event types) |
| `app/main.py` | Modify (SCRAPING_MODE env var) |

### Frontend (Agent B)

| File | Action |
|---|---|
| `SmartCompareApp/src/screens/ResultsScreen.tsx` | Modify (defensive guards, wire new components, remove dead buttons) |
| `SmartCompareApp/src/types/index.ts` | Modify (Dimension, ScoringV2 types) |
| `SmartCompareApp/src/components/results/HeroRings.tsx` | Create |
| `SmartCompareApp/src/components/results/DimensionBars.tsx` | Create |
| `SmartCompareApp/src/components/results/TopMatchBadge.tsx` | Create |
| `SmartCompareApp/src/components/results/FactualVerdict.tsx` | Create |
| `SmartCompareApp/src/services/api.ts` | Modify (new SSE handlers) |
| `SmartCompareApp/src/i18n/en.json` | Modify (remove banned keys, add new) |
| `SmartCompareApp/src/i18n/ar.json` | Modify (remove banned keys, add new) |
| `SmartCompareApp/src/i18n/.copy-policy.json` | Create |
| `SmartCompareApp/eslint.config.js` | Modify (register no-evaluative-copy rule) |
| `SmartCompareApp/eslint-rules/no-evaluative-copy.js` | Create |

### Tests (Agent C)

| File | Tests | Coverage target |
|---|---|---|
| `tests/test_scoring_v2_models.py` | 4 | n/a |
| `tests/test_scoring_calibration.py` | 8 | scoring_service.calibrate_score 100% |
| `tests/test_dimensions_builder.py` | 4 | build_dimensions_v2 ≥80% |
| `tests/test_verdict_builder.py` | 4 | verdict_builder.py ≥85% |
| `tests/test_fact_check_service.py` | 2 (new) | n/a (existing module) |
| `tests/test_quality_ranker.py` | 3 | quality_ranker.py ≥90% |
| `tests/test_scatter_gather_price.py` | 2 | n/a (orchestration) |
| `tests/test_sse_settle_window.py` | 2 | n/a (orchestration) |
| `tests/test_scraping_mode.py` | 2 | n/a |
| `SmartCompareApp/__tests__/components/HeroRings.test.tsx` | 3 | HeroRings.tsx ≥80% |
| `SmartCompareApp/__tests__/components/DimensionBars.test.tsx` | 3 | DimensionBars.tsx ≥80% |
| `SmartCompareApp/__tests__/components/TopMatchBadge.test.tsx` | 1 | 100% |
| `SmartCompareApp/__tests__/components/FactualVerdict.test.tsx` | 2 | 100% |
| `SmartCompareApp/__tests__/screens/ResultsScreen.test.tsx` | 4 | n/a (existing) |
| `SmartCompareApp/__tests__/screens/ResultsScreen.integration.test.tsx` | 2 | n/a |
| `SmartCompareApp/__tests__/services/api.settle.test.ts` | 1 | api.ts settle handlers 100% |
| `SmartCompareApp/__tests__/copy-policy.test.ts` | 2 | n/a |

### QA (Agent D)

| File | Action |
|---|---|
| `tests/test_bundle_e_integration.py` | Create (integration tests, live Railway) |
| `tests/perf/test_latency_bench.py` | Create (P50/P95 bench) |
| `docs/plans/2026-05-13-bundle-e-qa-checklist.md` | Create (manual on-device QA) |
| `docs/plans/2026-05-13-bundle-e-qa-log.md` | Maintain (cross-QA sign-off log) |
| `docs/runbooks/bundle-e-perf-bench.md` | Create (perf results) |

---

## Rollback Plan

If Bundle E causes regressions in production after merge:

```bash
# Backend revert
git revert <merge-commit-hash>
git push origin main  # ~90s redeploy

# Frontend EAS rollback
cd SmartCompareApp
eas update:rollback --branch preview
```

Feature flag killswitch: `BUNDLE_E_NEW_RESULTS=false` on Railway → backend emits only legacy `scoring`, frontend falls back to legacy code path (one release of backward-compat).

---

## References

- **Design doc:** `docs/plans/2026-05-13-results-quality-overhaul-design.md`
- **CLAUDE.md:** Operating Principle #4 (parallel agent teams), #6 (path-restricted commits)
- **Predecessor bundle pattern:** `docs/plans/2026-05-12-bundle-bcd-consolidated.md` (4-Opus, cross-QA, blocking gate)
- **TDD discipline:** `superpowers:test-driven-development`
- **Team execution:** `superpowers:executing-plans` + `superpowers:dispatching-parallel-agents`
