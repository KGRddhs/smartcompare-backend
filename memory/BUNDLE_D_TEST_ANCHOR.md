---
name: Bundle D Test Anchor
description: Per-lane scope + verification commands + targets for Bundle D Test agent
type: project
---

# Lane: Test

## My scope (continuous, all phases)

### Phase 1 — Foundation
1. **Task 1.T.1** — Pre-existing RED test triage + red-green scaffolds.
   - Inventory 3 known RED tests: `TestReengagementSubToggles`, `test_phase1_includes_reviews`, `test_comparison_quality_in_response_metadata_payload`.
   - Confirm RED today via isolated runs (`pytest -k <name> -v`).
   - Triage table in PR comment with Bundle D owner + expected GREEN-via path.
   - Commit `docs/plans/bundle-d-red-test-triage.md`.

### Phase 2 — Integration
2. Extend coverage on Phase 2 touched files:
   - `app/services/response_builder.py` (B.0 kwarg refactor)
   - `app/services/scoring_service.py` (A.8.1 + A.6.2-A.6.5)
   - `app/services/extraction_service.py` (A.4.8)
   - `app/api/auth_routes.py` (preferences save, reengagement subs)
   - `app/api/legal_routes.py` (legal endpoints fix)
   - `app/services/sentry_service.py` (C14 query-string scrub)
   - `SmartCompareApp/src/services/api.ts` (refresh-token mutex)
   - `SmartCompareApp/src/screens/ProfileScreen.tsx` (optimistic toggles + C17 default)
   - `SmartCompareApp/src/screens/HomeScreen.tsx` (Claude-Design refresh)
3. Write red-green tests BEFORE implementation when paired with another agent.

### Phase 3
4. **Task 3.T.1** — Full test sweep:
   - Backend: `python -m pytest tests/ --timeout=180 -v` (baseline ≥503/503 + new tests added)
   - Frontend: `cd SmartCompareApp && npx tsc --noEmit && npx jest` (tsc 0 errors, jest ≥1011/1011 + 30 snapshots)

### Phase 4
5. Final test sweep — re-run full pytest + tsc + jest one last time pre-merge.
6. **Idle time = red-green tests** (Ahmed contract rule #4) — any wait on QA = write tests for in-flight features, target 80% line coverage on touched files.

## Targets
- ≥80% line coverage on every file touched by Backend + Frontend lanes (Test lane GREEN gate)
- Net new tests count ≥ count of new features
- Zero net new RED tests (pre-existing triaged, no new ones introduced)
- Backend baseline ≥503/503 maintained
- Frontend baseline ≥1011 jest + 30 snapshots + tsc 0 errors maintained

## Memory facts I need (anti-hallucination)
- IDE/LSP TS diagnostics on Windows are unreliable. Trust ONLY `npx tsc --noEmit` exit code.
- `conftest.py` auto-loads `.env` via python-dotenv.
- Test markers: `live_unit`, `live_db`, `integration`. Free unit run: `pytest -m "not (live_unit or live_db or integration)"`. Live: `pytest -m "not (live_db or integration)"`.
- Pre-existing RED files NOT my responsibility to fix in Bundle D: `HomeScreen.redesign.test.tsx`, `HomeScreen.modeChipAnim.test.tsx`, `HomeScreen.scanCamera.test.tsx` (design § 12 out-of-scope; need mock refresh for `react-i18next` + new `trackEvent` + testID rename `home-camera-card` → `home-center-area`).
- 3 known RED tests in scope for Bundle D triage: `TestReengagementSubToggles` (greens via Backend 2.B.7), `test_phase1_includes_reviews` (Test defer — D2 Intervention 1 follow-up, NOT Bundle D), `test_comparison_quality_in_response_metadata_payload` (greens via Backend 2.B.1 B.0 refactor).
- ~100 test files in `tests/`, one per service. 80%+ coverage target for new features.
- Frontend tests at `SmartCompareApp/src/__tests__/` + `src/services/__tests__/`.
- `pytest tests/test_security_regression.py` (~98 tests) must stay 100% GREEN — DO NOT delete or skip.
- Backend total pre-Bundle-D baseline: 503/503 GREEN (per Test agent confirmation Bundle C close).
- Frontend total pre-Bundle-D baseline: 1011/1011 jest + 30 snapshots (per Bundle C frontend Section B close).

## Pre-flight commands (run before starting)
- `git log --oneline -5` — confirm starting commit
- `python -m pytest tests/ --collect-only -q 2>&1 | tail -5` — total test count
- `python -m pytest tests/ -v --tb=no -q --timeout=120 -m "not (live_db or integration)" 2>&1 | tail -20` — baseline GREEN count
- `cd SmartCompareApp && npx jest --listTests | wc -l` — test file count
- `cd SmartCompareApp && npx tsc --noEmit` — baseline 0 errors

## Verification commands (run before "done")
- `python -m pytest tests/ --timeout=180 -v` — full backend sweep
- `python -m pytest tests/test_security_regression.py -v` — security regression 100% GREEN
- `cd SmartCompareApp && npx tsc --noEmit` — 0 errors
- `cd SmartCompareApp && npx jest` — ≥1011 + 30 snapshots
- Coverage spot-check: `python -m pytest --cov=app/services/response_builder tests/ -q` ≥80% for touched files (use `coverage` package if not installed via pip)

## Dependencies
- **Blocked by:** Backend + Frontend Phase 2 implementation work (I write tests in parallel or red-first)
- **Blocking:** QA cross-review depends on my tests being GREEN

## Rollback recipes
- **New test breaks unrelated suite:** revert test file commit; pre-existing baseline preserved
- **Test infrastructure regression (conftest.py / pytest.ini):** revert to prior config commit; baseline returns
