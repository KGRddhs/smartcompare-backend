# Bundle D — Pre-existing RED Test Triage

**Authored by:** test lane (Bundle D)
**Branch:** `feature/bundle-d-testflight-readiness`
**HEAD at triage time:** `3928d7a`
**Date:** 2026-05-23

## Scope

Three pre-existing RED tests live in `tests/` at the start of Bundle D. This document records:

1. The exact failing assertion captured today.
2. Which Bundle D task — and therefore which agent — is expected to flip each test GREEN.
3. The verification command to re-run after that task lands.

Three additional RED frontend test files (`HomeScreen.redesign.test.tsx`, `HomeScreen.modeChipAnim.test.tsx`, `HomeScreen.scanCamera.test.tsx`) are explicitly **out of scope** for Bundle D per design § 12 — they require a mock refresh deferred to a later bundle.

## Triage table

| # | Test ID | File | Failing assertion (today) | Bundle D owner | Expected GREEN-via path | Re-run cmd |
|---|---|---|---|---|---|---|
| 1a | `TestReengagementSubToggles::test_decision_insight_skipped_when_subtoggle_off` | `tests/test_push_token_endpoint.py:270` | `assert result is not None` — `reengagement_service.evaluate_user` returns `None` when `prefs.decision_insight = False`. Expected: insight detector skipped, but other detectors still produce a result. | **Backend** | Task **2.B.7** — Reengagement sub-toggle PUT endpoint + service respect per-detector flags on partial / absent preferences. | `pytest tests/test_push_token_endpoint.py::TestReengagementSubToggles -v` |
| 1b | `TestReengagementSubToggles::test_missing_preferences_treats_as_all_on` | `tests/test_push_token_endpoint.py:310` | `assert result is not None` — when `prefs` row absent, evaluator should default all detectors ON and still yield a candidate. | **Backend** | Task **2.B.7** — service falls back to all-detectors-ON when preferences map is empty or missing. | `pytest tests/test_push_token_endpoint.py::TestReengagementSubToggles::test_missing_preferences_treats_as_all_on -v` |
| 2 | `test_phase1_runs_reviews_in_parallel_with_specs_price` | `tests/test_phase1_includes_reviews.py:66` | `AssertionError: Reviews appears to be running in Phase 2 (took 6.00s, expected <1.2s for parallel with Phase 1). D2 Intervention 1 not effective.` | **Defer** (no owner in Bundle D) | D2 Intervention 1 follow-up — restructure `_fetch_product_data` so review fetch starts in Phase 1 alongside specs+price. Design § 12 explicitly drops this from Bundle D scope. | `pytest tests/test_phase1_includes_reviews.py -v` |
| 3 | `test_comparison_quality_in_response_metadata_payload` | `tests/test_structured_comparison_service.py:155` | `TypeError: build_comparison_response() got an unexpected keyword argument 'products'` — followed by `pytest.fail("RED: build_comparison_response signature does not yet accept metadata.comparison_quality — Bundle C v1.1 wiring incomplete")`. | **Backend** | Task **2.B.1** — B.0 `response_builder` kwarg-only refactor. After kwarg signature lands, `metadata.comparison_quality` round-trips through assembly. | `pytest tests/test_structured_comparison_service.py::test_comparison_quality_in_response_metadata_payload -v` |

## Subclass-level breakdown — `TestReengagementSubToggles`

Class contains 4 tests; 2 GREEN, 2 RED today:

| Test | Status today | Owner if RED |
|---|---|---|
| `test_master_toggle_off_returns_none` | GREEN | — |
| `test_all_subtoggles_off_returns_none` | GREEN | — |
| `test_decision_insight_skipped_when_subtoggle_off` | RED | Backend 2.B.7 |
| `test_missing_preferences_treats_as_all_on` | RED | Backend 2.B.7 |

The two GREEN tests assert the all-off short-circuits, which already work. The two RED tests assert mid-state behaviour (partial off + absent prefs) that the endpoint does not yet handle.

## Notes for implementation agents

### Backend — Task 2.B.7 (reengagement subs)
- Both RED tests call `reengagement_service.evaluate_user(...)` (or its dependency on a stored prefs row). They assert `result is not None` and rely on per-detector skip logic.
- Read the existing GREEN tests (`test_master_toggle_off_returns_none`, `test_all_subtoggles_off_returns_none`) — they pin the contract you must extend, not break.
- After your endpoint + service change lands, re-run the whole class: `pytest tests/test_push_token_endpoint.py::TestReengagementSubToggles -v`. Target: 4/4 GREEN with no other regression.

### Backend — Task 2.B.1 (B.0 response_builder kwarg refactor)
- Today: `build_comparison_response()` accepts positional args; test passes `products=...` keyword and crashes with `TypeError`. Test then falls through to `pytest.fail()` with the v1.1 sentinel message.
- After the refactor, the kwarg call must succeed and `response["metadata"]["comparison_quality"]` must exist + match the value provided. Spot-check additional fields (`personalization`, `scoring_v2`) round-trip too — Bundle C v1.1 polish item #1 names 3 RED tests gated on this signature change.
- Verify with `pytest tests/test_structured_comparison_service.py -k comparison_quality -v` and a quick `pytest tests/test_structured_comparison_service.py -v --tb=short` for full file regression.

### Defer — `test_phase1_includes_reviews`
- Out of Bundle D scope per design § 12. Leave RED. Do NOT add a `@pytest.mark.skip` — the test must stay visible so the next bundle picks it up. If a backend implementation incidentally makes it GREEN, that is fine; no agent should target it.

## Verification

After both owner tasks (2.B.1 and 2.B.7) land:
```
pytest tests/test_push_token_endpoint.py::TestReengagementSubToggles -v
pytest tests/test_structured_comparison_service.py::test_comparison_quality_in_response_metadata_payload -v
```

Both should be GREEN. Bundle D Phase 3 sweep (`pytest tests/ --timeout=180 -v`) must show net-zero new RED tests vs. the 3 documented here (3 → 1 surviving RED, the deferred D2 follow-up).
