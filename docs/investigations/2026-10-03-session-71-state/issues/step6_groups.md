=== TITLE: Step 6 (session 71) hook follow-ups: .env filename forms, rotation precondition, process count, shared frontmatter check
=== LABELS: tooling,step6
## Source
Step 6 structured code review of session 71 (low, unverified; plan in `docs/investigations/2026-10-03-session-71-state/STEP6_ACTION_PLAN.md`). The two confirmed hook findings (binary blobs skip every scan; the pinned four-branch line under `color.ui=always` / `diff.external`) are their own issues. Belongs with T0b Phase B.

## Items (file `.githooks/pre-commit` as merged in #312)
- **SEC-4** the `.env` filename regex misses `prod.env`, `railway.env`, `.env-backup`, `.env_prod`, `.envrc`. Widen to `(^|/)(\.env([._-][^/]*)?|[^/]+\.env|\.envrc)$`, case-insensitive, one refusal pin per form (no tracked file is newly refused).
- **SEC-3** the 4b value pass reads the main checkout's root `.env`; the `ADMIN_API_KEY` rotated on 2026-10-03 exists only on Railway, so the stale local file gives 4b nothing to match. Operational: the rotation runbook gains a step where the owner (never an agent) writes the new value into the root `.env`; state it as a 4b precondition.
- **PER-4** about 23 processes per empty commit against 8 before (three full staged diffs, four name-only diffs, one Python per SKILL.md): one staged diff written to `$TMP` feeding 4a and 4b (keep the Z trailer), skip the 4b awk when there are no entries, list staged names once, check every SKILL.md in one Python process. Keep the pinned line 150 and the TG4 black probe.
- **COM-9** the frontmatter rule exists twice (hook 4c and `tests/test_skill_frontmatter.py`): one `scripts/check_skill_frontmatter.py` `check(text)` used by both, or a parity test over one corpus.
- **COM-10** the shell `to_upper` loop and one grep spawn per URL-shaped value: move the NAME and credentialed-URL filters into `ENV_MATCH_AWK` (check mawk support for `[:space:]` on CI first).
- **DEA-8** the unreachable `*)` arm of `run_tool` (optional).

=== TITLE: Step 6 (session 71) account-deletion follow-ups: one multi-key purge, run_db offload, 044 indexes, DELETE order
=== LABELS: backend,step6
## Source
Step 6 structured code review of session 71 (low, unverified; plan in `docs/investigations/2026-10-03-session-71-state/STEP6_ACTION_PLAN.md`). The refuted PER-1 (the detach UPDATEs as a blocking scan) is NOT part of this: 99% of the cascade cost is the comparisons FK check that 025 already paid.

## Items
- **PER-2 + DEA-6** `app/services/auth_service.py` `_purge_deleted_user_caches`: five sequential Upstash DELs; with Redis down and the offload flag OFF each costs attempt + 3 s sleep + attempt inline on the loop (35 s measured on this box, about 15 s reasoned on Linux) against 7 s for one multi-key DEL. Fix: one fail-soft `redis_client.delete(*keys)`, one `to_thread` hop when `ENABLE_ASYNC_REDIS_OFFLOAD` is on. The `except` after `delete_cached` cannot fire (it swallows): keep as a documented guard or check the False return.
- **PER-3** `database_service.delete_user_data_cascade` and the auth admin delete are bare synchronous calls in async defs, outside `ENABLE_SYNC_DB_OFFLOAD`: wrap both in `await run_db(lambda: ...)`, byte-identical with the flag OFF.
- **PER-7** new migration 044 (indexes only): `deep_review_credits` has only a partial `(user_id, expires_at) WHERE consumed_at IS NULL` index, so 043's DELETE scans consumed rows; `user_events` and `comparison_feedback` lack a `comparison_id` index (LS-DB-QUERIES-07). `CREATE INDEX CONCURRENTLY` on all three plus a `pg_indexes` row in PRECHECK. Latent at today's scale.
- **PER-8** in 043 the comparisons DELETE fires SET NULL updates on the user's own rows that the four U8b DELETEs then remove; moving the four DELETEs first needs a ruling and a test update (the order is pinned). Latent.
- **DEA-7** the 043 `$assert$` prosecdef / proconfig check cannot fire in the file as committed: label it a self-check against edits (no change).

=== TITLE: Step 6 (session 71) U13 tidy: the get_gcc_prices comment and inline key check, guard helpers, the moot anon gate
=== LABELS: backend,step6
## Source
Step 6 structured code review of session 71 (low, unverified; plan in `docs/investigations/2026-10-03-session-71-state/STEP6_ACTION_PLAN.md`). Do after `ENABLE_COMPARE_AUTH_REQUIRED` is permanent.

## Items (`app/api/text_routes.py`)
- **COM-3 + DEA-3** `get_gcc_prices`: the W2-1 comment argues against the router dependency U13 deliberately attached; the inline `verify_admin_key` is redundant when both flags are ON (still needed while U13 is OFF and metering ON). Rewrite the comment now; delete the inline branch when U13 is permanent; pin that with both flags ON a wrong key gives exactly one 403.
- **COM-6** the two guards share a duplicated tail and `_refuse_paid_route` lacks `-> NoReturn`: add the annotation, `_log_refusal` and `_admin_or_refuse`; the ruled `_PAID_AUTH_DETAIL` duplicate stays (R9).
- **DEA-1 (documented limit, UR5)** with U13 ON app users never reach the anonymous usage gate or the #128 refund wiring: mark the `ENABLE_ANON_USAGE_GATE` row and #128 as moot in CLAUDE.md; delete the code when U13 is permanent.

=== TITLE: Step 6 (session 71) harness scripts: one admin-key opt-in helper instead of five copies
=== LABELS: backend,step6
## Source
Step 6 structured code review of session 71 (low, unverified).

## Items
- **COM-2 + DEA-11 (+ DEA-9)** `_harness_auth_headers` exists as five AST-identical copies (`scripts/eval_runner.py`, `run_validation_matrix.py`, `bias_matrix_probe.py`, `bundle_d_prod_smoke.py`, `docs/.../verify_after_credits.py`); H07 tests only `'1'` and unset, so drift in four copies goes undetected. One `scripts/harness_auth.py` imported by the four scripts (the docs copy stays a copy); parametrise H07 over the 9-cell opt-in matrix or add an AST-equality test. In `bias_matrix_probe` the `headers={}` conditional is redundant on httpx 0.28.1 (measured equal to the default).

=== TITLE: Step 6 (session 71) observability: cap exc_summary input, one scrub pipeline, structured_comparison_service duplicates
=== LABELS: backend,observability,step6
## Source
Step 6 structured code review of session 71 (low, unverified).

## Items
- **PER-6 (documented follow-up OR20)** `app/services/log_scrub.py` `exc_summary`: the quadratic JWT pattern runs over the uncapped `str(exc)` on the event loop (5.25 s at 368 KB adversarial; 48 ms/MB realistic). Pre-cap with `str(exc)[:16384]` before both scrubs; the 200-char cut stays last.
- **COM-7** the scrub order is implemented twice (`_scrub_text` and the inline pipeline in `exc_summary`): one `_scrub_text(text, *, key_shapes=False)` shared by both; `safe_exc` output stays byte-identical (R3.1).
- **COM-11 + DEA-5 + DEA-4** `app/services/structured_comparison_service.py`: the per-run resets are duplicated, the downgrade read has three copies, the `getattr` defaults are dead and the `cancelled()` skip arm is unreachable. Add `_usage_marks_downgrade()` and `_reset_run_state()`; read the attribute directly; keep the :320 guard as documented forward-defence. Test: run the stream path twice on one instance.

=== TITLE: Step 6 (session 71) client follow-ups: proactive refresh before the camera upload, shared retry headers, one empty-state table, docstrings
=== LABELS: mobile,step6
## Source
Step 6 structured code review of session 71 (low, unverified). PER-5 is the documented limit L2 of the U13c spec.

## Items (`SmartCompareApp`)
- **PER-5** `identifyFromImages`: an expired token is discovered only after the full multipart upload, so every expired-token camera compare uploads the JPEGs twice. Export `isJwtExpired` from authService and refresh proactively before the first fetch; keep the reactive 401 retry.
- **COM-5** the retry builds its own header literal (a header later added to the first request would be missing from the retry), the `unretriedAuthBody` placeholder and a double `JSON.parse`: `authHeaders(t)` and `toServerError(status, text)` shared by both fetches; lock with the u13c suite.
- **COM-4** `ResultsScreen` has five parallel ternary chains on `loadError`: one `EMPTY_STATE` table plus one parametrised render test over every `loadError` value.
- **COM-8** the `QarenLogo` docstring says every site is white; the RevealBurst badge is `#ECFDF5`. Update it.
- **DEA-2 (optional)** five icons in `UtilityIcons.tsx` have no consumer and the revealGlyph R7 pin locks them in: delete and update R7, or mark reserved.
- **DEA-10** `__tests__/config/nativeBundle.w37.test.ts`: the `ICON_ART_SUPPLIED` latch is permanently true; use `it` directly (overlaps the render-check CI issue #282).
