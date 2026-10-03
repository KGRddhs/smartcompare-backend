
---

## Orchestrator gate on the RED tests (BINDING - supersedes everything above where they differ)

Fable orchestrator, session 71, 2026-10-03 10:04 +03. Verdict: **PASS, no change**. GREEN may start.

Reviewed: `tests/test_migration_043_delete_user_cascade.py` (sha256 `4f8d7dadf5ad3729...`, 1336 lines, 51 nodes) and `tests/test_account_deletion_u8b.py` (`846f34e8274e64f1...`, 266 lines, 10 nodes). Measured by the RED agent at `eb86075e`: 35 failed / 26 passed, 0 collection errors, 0 network attempts; every RED fails for its stated reason (the missing 043, rollback and one-paste files fail inside the test body; the two coverage tests list exactly the 20 users gaps and 5 table gaps of the 025 body; the backend reds show the sentinel in the logged text, zero purge calls and the missing constant); the PIN set is 241 passed without the files and only the 35 REDs fail with them; a spec-shaped prototype in a detached scratch worktree passed all 61 nodes and the full PIN set (303 passed), and 26 of 26 file-level mutants were killed. The orchestrator read the report, the expected tombstone map (25 columns, the three NOT NULL columns at 0 / false / 0) and the KEEP lists.

- **UG1 - the RED deviations are accepted:** the route's 500 text is read under `error` or `detail` (the envelope renders it under `error`); the cascade-body mutant self-tests run over the LATEST cascade definition, so they are PINs at base; the KEPT cache-key list lives in the static test file; the seven extra tests; the stronger no-GRANT scan.
- **UG2 - the two RED files are FROZEN.** A test edit needs a test defect proven by measurement and is reported as a deviation.
- **UG3 - the SQL keeps the spec's SHAPES.** The guard arrays, the temp-table probe (`CREATE TEMP TABLE u8b_probe (LIKE public.users INCLUDING DEFAULTS INCLUDING CONSTRAINTS) ON COMMIT DROP`) and the statement order are parsed by the tests as the spec writes them; a semantically equal rewrite is not accepted.
- **UG4 - the base moved** to main `ca604e0a` (PR #285). Measured: #285 changed none of `auth_service.py`, `database_service.py`, `auth_routes.py`, `cache_service.py`, `home_routes.py` or `migrations/`. The worktree is fast-forwarded; BASE for the comm gate is `ca604e0a`.
- **UG5 - the PostgreSQL 18 single-user run (G8) is MANDATORY for GREEN**, including the three abort paths that must leave the 025 body in force.
- **UG6 - the PR text carries the owner's apply runbook** (PRECHECK first and its STOP rules, ONE_PASTE, POSTCHECK, the optional BACKFILL, the rollback and its limit), the three privacy defaults he may change before applying (UR3, UR5, UR10), the corrected policy statement for U8 (C10) and the follow-ups. Merging the PR applies nothing to the database.
