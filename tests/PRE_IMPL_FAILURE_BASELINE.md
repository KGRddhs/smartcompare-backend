# Pre-impl free-unit failure baseline — Faithful-Results bundle

> **CANONICAL SOURCE OF TRUTH = QA's `.qa-discovery/BASELINE_FAILURES.txt`** (dispatcher
> ruling: ONE ignore-set the 7.3 gate trusts). This file's local snapshot
> `tests/.pre_impl_failures.txt` was **reconciled set-identical to QA's (59 == 59, zero
> diff)** and serves only as the harness FALLBACK when the main tree's `.qa-discovery/`
> isn't on disk (fresh clone / CI). `scripts/regression_gate_diff.py` defaults to QA's
> file when present, else the snapshot. Never fork the set — reconcile with QA.
>
> **Network-flaky EXCLUDE set** (`NETWORK_FLAKY_EXCLUDE` in `regression_gate_diff.py` —
> gate ignores regardless of baseline membership): the two
> `test_price_cache_bust_probe.py::TestPriceReadBypass` methods (Backend-flagged; live
> Tier-1.5 escalation not mocked) + `test_rate_limiting_complete.py::...prices_endpoint_rate_limited`
> (real GET). These pass-or-fail by live-network reachability, so they must never read as a
> code regression.

**Captured by:** Test member, 2026-06-17, worktree `feature/faithful-test` BEFORE any
Backend/Frontend impl landed (both branches still at main HEAD `2c10cb8` for `app/`
code at capture time). Verified set-identical to QA's independently-captured baseline.

**Command:**
```
python -m pytest tests/ -m "not (live_unit or live_db or integration)" \
  --ignore=tests/test_integration.py -q
```

**Result at capture:** `59 failed, 6880 passed, 8 skipped, 109 deselected`.

These 59 are the **regression gate denominator** for Phase 7.3 — a "no regressions"
claim means *no NEW failures beyond this list*, NOT zero failures. None of these touch
the files this bundle modifies (`scripts/eval_runner.py`, `price_service` cache layer,
`review_service` paraphrase, `extraction_service` category payload, `response_builder`,
FE `results/*`).

## Breakdown

| File | # | Why pre-existing (not our bundle) |
|---|---|---|
| `test_value_math.py` | 35 | **Known RED-by-design** (CLAUDE.md): TDD stubs for unimplemented Bundle C v1.1 value-math fns. Documented non-regression. |
| `test_youtube_service.py` | 6 | S3 YouTube-signal WIP; API-shape/cache-mock dependent. |
| `test_camera_vision.py` | 3 | `openai_service._log_cache_telemetry` raises `TypeError: '>' not supported between MagicMock and int` — the test mock's `usage` is a bare MagicMock; cache-telemetry code added later expects numeric. Mock drift, unrelated. |
| `test_youtube_circuit_breaker.py` | 2 | YouTube WIP (same family as above). |
| `test_personalization_bundle_c.py` | 2 | Bundle C personalization payload-audit; pre-existing. |
| `test_auth_interceptor.py` | 2 | `[B4-BE-DIAG]` Google-sign-in diagnostic string intentionally present (CLAUDE.md: "diagnostic instrumentation kept in auth_service.py until Google sign-in resolved"). |
| `test_youtube_flag_and_cache.py` | 1 | YouTube WIP. |
| `test_source_usage_field.py` | 1 | `registry_price_source_count` row-count assertion; pre-existing S3. |
| `test_security_regression.py` | 1 | `[GOOGLE-DIAG]` console.log in FE auth — same intentional Google diagnostic instrumentation. |
| `test_referral_e2e.py` | 1 | Referral e2e; pre-existing. |
| `test_rate_limiting_complete.py` | 1 | **Does a real GET** (CLAUDE.md: network-dependent "free" test — exclude from gate batches). |
| `test_lane1_helpers_unit.py` | 1 | `compose_delta_text` missing-score sentinel; pre-existing Bundle C v1.1 family. |
| `test_invitee_quiz.py` | 1 | Invite-token edge case; pre-existing. |
| `test_extraction_prompt_bundle_c.py` | 1 | `response_builder_strips_inference_source`; pre-existing Bundle C. |
| `test_backend_cleanup.py` | 1 | Dead-function/unused-import cleanup assertion; pre-existing. |

## Full failing-id list (sorted)

See `tests/.pre_impl_failures.txt` (machine-readable, one `FAILED <id>` per line) committed
alongside this doc. Phase 7.3 diffs the post-merge failure set against that file.
