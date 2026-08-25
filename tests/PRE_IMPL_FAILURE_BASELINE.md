# Pre-impl free-unit failure baseline — Faithful-Results bundle

> **UPDATE 2026-08-25 (issue #49 — CI gates):** the 35 `test_value_math.py` nodes in the
> table below now report as **xfail, not FAILED**. They carry a module-level
> `pytest.mark.xfail(strict=False)` so `.github/workflows/ci.yml` stops going red for a
> documented non-regression. The gate is a SUBSET check (`current ⊆ baseline`), so the
> 35 stale entries in `tests/.pre_impl_failures.txt` are harmless and deliberately left
> in place rather than forked from QA's canonical file. Effective FAILED denominator on
> a clean tree is therefore **13**, not 48. When Bundle C v1.1 (A.6.x) ships, those nodes
> turn XPASS, the pytestmark comes off in that PR, and both files can be re-synced with QA.

> **CANONICAL SOURCE OF TRUTH = QA's `.qa-discovery/BASELINE_FAILURES.txt`** — dispatcher
> LOCKED at **48 nodes** (QA's FULL-credential capture). A branch is GREEN iff its FAILED
> set ⊆ those 48 (minus the network-flaky exclude). `scripts/regression_gate_diff.py`
> defaults to QA's file when the main tree is on disk, else the local mirror
> `tests/.pre_impl_failures.txt` (re-synced to the SAME 48). Never fork the set —
> reconcile with QA.
>
> **Why 48, not 59:** my FIRST capture (59) ran WITHOUT a worktree `.env`. The extra 11
> were 9 `test_youtube_*` (keyed off the missing `YOUTUBE_API_KEY` — they pass with
> creds present) + `test_invitee_quiz` edge case. QA's full-cred capture is authoritative;
> the 59 partial-cred snapshot is DISCARDED. This confirmed the .env gate-integrity catch
> was real (worktrees don't inherit gitignored `.env`).
>
> **Network-flaky EXCLUDE set** (`NETWORK_FLAKY_EXCLUDE` in `regression_gate_diff.py` —
> gate ignores regardless of baseline membership): the two
> `test_price_cache_bust_probe.py::TestPriceReadBypass` methods (Backend-flagged; live
> Tier-1.5 escalation not mocked) + `test_rate_limiting_complete.py::...prices_endpoint_rate_limited`
> (real GET). These pass-or-fail by live-network reachability, so they must never read as a
> code regression. (The real-GET rate-limit test IS in the 48 baseline; the bust-probe two
> are NOT — either way the exclude neutralizes them.)

**Command (run by QA with full creds):**
```
python -m pytest tests/ -m "not (live_unit or live_db or integration)" \
  --ignore=tests/test_integration.py -q
```

**LOCKED denominator:** 48 known failures. A "no regressions" claim for Phase 7.3 means
*no FAILED nodeid outside those 48* (after the network-flaky exclude). None of the 48 touch
the files this bundle modifies (`scripts/eval_runner.py`, `price_service` cache layer,
`review_service` paraphrase, `extraction_service` category payload, `response_builder`,
FE `results/*`).

## Breakdown (the LOCKED 48)

| File | # | Why pre-existing (not our bundle) |
|---|---|---|
| `test_value_math.py` | 35 | **Known RED-by-design** (CLAUDE.md): TDD stubs for unimplemented Bundle C v1.1 value-math fns. Documented non-regression. |
| `test_camera_vision.py` | 3 | `openai_service._log_cache_telemetry` raises `TypeError: '>' not supported between MagicMock and int` — the mock's `usage` is a bare MagicMock; cache-telemetry code expects numeric. Mock drift, unrelated. |
| `test_personalization_bundle_c.py` | 2 | Bundle C personalization payload-audit; pre-existing. |
| `test_auth_interceptor.py` | 2 | `[B4-BE-DIAG]` Google-sign-in diagnostic string intentionally present (CLAUDE.md). |
| `test_source_usage_field.py` | 1 | `registry_price_source_count` row-count assertion; pre-existing S3. |
| `test_security_regression.py` | 1 | `[GOOGLE-DIAG]` console.log in FE auth — same intentional Google diagnostic instrumentation. |
| `test_referral_e2e.py` | 1 | Referral e2e; pre-existing. |
| `test_rate_limiting_complete.py` | 1 | **Does a real GET** (also in NETWORK_FLAKY_EXCLUDE). |
| `test_lane1_helpers_unit.py` | 1 | `compose_delta_text` missing-score sentinel; pre-existing Bundle C v1.1 family. |
| `test_extraction_prompt_bundle_c.py` | 1 | `response_builder_strips_inference_source`; pre-existing Bundle C. |
| `test_backend_cleanup.py` | 1 | Dead-function/unused-import cleanup assertion; pre-existing. |

(Dropped vs the partial-cred 59: 9 `test_youtube_*` + 1 `test_invitee_quiz` — all
credential/WIP artifacts, NOT real baseline failures.)

## Full failing-id list

`tests/.pre_impl_failures.txt` is a local MIRROR of QA's canonical 48 (machine-readable,
one bare nodeid per line). The gate prefers QA's `.qa-discovery/BASELINE_FAILURES.txt`;
the mirror is the CI/fresh-clone fallback only.
