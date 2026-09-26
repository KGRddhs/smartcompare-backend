# FABLE REVIEW RULINGS W4-13 (binding, 2026-09-26, session 68) - these OVERRIDE the spec body and the adversarial review where they differ

Verdict: APPROVED WITH THE CORRECTIONS BELOW. Base 61585c58 (re-anchor by symbol). This unit lands FIRST in the W4 batch ("before any launch gate reads a number").

Q1 - KEEP ENABLE_SEARCH_LOG_TRUTH (flag 1). `tests/test_m18_preverdict_disconnect_refund.py::test_refund_survives_an_aclose_that_raises` (`not any(log_search)`) is a flag-OFF pin: it stays and gets `monkeypatch.delenv` of the new flag; the unit adds its flag-ON twin (exactly one failure row, after the refund).

Q2 (backfill, with correction C1) - migration 042 tags rows whose `lower(btrim(query))` is one of the 13 measured strings AND `created_at` < the APPLY time, EXCEPT rows of probe #1 (`iphone 15 vs galaxy s24`) with `duration_ms >= 10000` (the app's own parse-failure copy suggests that pair, and 292 sync rows >= 10 s may be organic - they stay NULL and pr_text states the residual ambiguity). The header carries a BEFORE census (count of 13-string rows before the pull max 2026-09-02T01:05:41Z = 11,724 expected, the count between the pull max and apply time, the count of excluded probe-#1 rows) and the AFTER check = BEFORE minus the exclusion, computed in the same transaction; the 1,513-row organic baseline is re-stated with the exclusion. Rollback drops the column; header says flag 2 OFF first.

Q3 (classifier authority) - a dedicated `SEARCH_LOG_SYNTHETIC_TOKEN` (least privilege) with correction C2 (`_is_synthetic_request` returns False when the token OR the header is empty, BEFORE any compare; test 13 gains 'token unset AND header absent' -> False; mutation M25; no broad try/except) AND D4: `X-Qaren-Synthetic` joins `_scrub_request`'s redacted headers in sentry_service.py in THIS unit (comm set += test_observability, test_retro_w1_9, test_sentry_503_suppression); rotation = set a new token on Railway + eval_runner env, no code.

Q4 (partial marker) - `error_message = 'partial:<stage>'` on a success row (no schema change; success keeps meaning delivered).

Q5 (PO-RECORDED-MEASURED-17 anon_id) - stays OPEN, its own row for Ahmed (a fingerprint-derived id is re-linkable); pr_text says so.

Q6 - CD-wave-diffs-02 (the stream route METERS success:False terminals) is scheduled as W4-13b right after this unit; pr_text states that under flag 1 the log says failure while the bill says delivered for those terminals until W4-13b lands.

Q7 / D1 - `POST /api/v1/text/quick` is FOLDED IN (same class as PO-11, measured: paid anonymous compare, zero rows): T9 writes success/failure rows under flag 1 (input_type 'text', cost from the result, never str(e)); the other three prod-HTTP harnesses' synthetic header = follow-up W4-13c (eval_runner only here).

Q8 - no reader-side stopgap before 042; confirmed. Q9 - file PO-RECORDED-MEASURED-01c (readers without `.range()`; also D6, the PostgREST cap is a precondition for the activation-step-4 canary) and the moderation-refusal `total_cost` (D2: the sync CONTENT_UNAVAILABLE exits carry no total_cost, so T1 logs 0.0 for a paid moderation_api run - stated limit; adding total_cost to those exits is scs and is the follow-up).

C3 (refund safety, LOAD-BEARING) - every NEW log row sits AFTER its refund `fire_and_forget` and before the raise; `_failure_log_cost` totals over ANY object (non-dict -> 0.0); `error_payload` captured only for dicts; test: a raising row builder still fires `usage_refund.*`; mutation M26; test 28's ordering flips accordingly.

C4 - T5 keys its message on `client_gone`, not `complete_response` (the Half-B ON disconnect case measured); test 21 gains the Half-B case; M29.

C5-C12 - ADOPTED: test 15 turns flag 1 ON too; tests 10 and 14 relabelled RED, test 14 asserts on the decoded non-ASCII value, test 20's camera cost = 0.02 + vision, test 6 states whether it asserts `synthetic_excluded` (RED) or counts only (PIN); the equality ledger and pin 34 send a fixed `X-Request-ID` (the middleware echoes it) and normalise `duration_ms`; the url_validator memo test is recorded as a timing flake (re-run alone 3x before it counts); C9 T6 = top-level `total_cost` (finite, >= 0) + `vision_cost` (no double count); C10 Preserve += test_m13_26_image_error_envelope, test_m13_03_paid_work_gating; C11 mutations M25-M29 and the forbidden broad except; C12 the url red tests stub `url_routes._validate_url_offloop_or_sync`.

D3 / D7 / D8 - the NULL window (rows from 2026-09-03 to the flag-2 flip are never classified) is measured at activation and stated; under T5/T3 abandoned streams count as failures in `get_error_stats` - ACCEPTED (they are failures to deliver), stated as a KPI series change at the flip; the flag-2 deploy canary: one minute after the flip the count of rows written after the flip must be > 0 (`log_search` swallows insert errors).

Gates - the call-ledger flag-OFF equality gate as amended (C7), base -> head -> base2 in a detached scratch worktree with flags + token unset, record-by-record; the 113-file comm set (+ the three Sentry files) base vs head, `comm -13` empty against the baseline + the guard-caused SSRF nodes + the memo flake; the 32-file Preserve set; the CI-order pin set in one invocation per flag state; ruff + py_compile; sqlfluff on 042 + its rollback with the repo config; the migration pins in the style of tests/test_migration_041_*.py (statement shape, `IS NULL` predicate, the exclusion clause, the BEFORE/AFTER census queries present in the header, rollback re-creates nothing it should not). Migration numbering: 042 (039 reserved; 040/041 exist). The migration is APPLIED by Ahmed after merge (APPLY_PACK row), flag 2's precondition.

Files - app/services/database_service.py (readers + log_search + the two flag readers + `_is_synthetic_request`), app/services/analytics_service.py, app/api/text_routes.py, app/api/url_routes.py, app/api/image_routes.py, app/services/sentry_service.py (one header), scripts/eval_runner.py (the header), migrations/042_*.sql + migrations/rollback/042_*.sql, tests. Anything else under app/ = STOP and report.
