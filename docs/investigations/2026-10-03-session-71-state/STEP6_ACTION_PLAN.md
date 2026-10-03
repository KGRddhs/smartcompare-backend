# Step 6 action plan: MYEZ launch lane, session 71 (2026-10-03)

Scope reviewed: main 1974e217 since base 4bd5a09f (#279 U4b, #285 OAI/obs, #288 U4c, #290 U8b, #297 U13, #307 U4d, #310 U8c) plus open PRs #312 (T0b Phase A hook, worktree sc-s71-t0b @ 62bebafb) and #313 (U13c camera 401, worktree sc-s70-u4b).

Tally:
- 0 critical, 0 high.
- 1 medium confirmed (SEC-1).
- 1 low confirmed group (COM-1, with SEC-2 and DEA-8's ++ hole folded in).
- 32 low unverified findings (SEC 3, PER 7, COM 10, DEA 12), grouped into 6 units plus one report-only line; several are duplicates folded together.
- 1 refuted (PER-1).

Merge verdicts:
- **#312 can merge.** Neither confirmed finding is a regression; both are gaps in the pinned step-4 line that existed before the PR, inherited by the new 4a/4b. Before merging, add both blind spots to the PR's "Stated limits" (see I-1 and I-2). If the orchestrator rules for it, the cheap half of SEC-1 (`--text --no-textconv` on 4a/4b) can also go in before merge.
- **#313 can merge.** It has no confirmed finding. PER-5 and COM-5 are follow-ups.
- **Merged code (U13, U8b/U8c, OAI, U4b/c/d):** no finding above low.

Format: severity | file:location | problem | fix.

## A. Confirmed (highest severity first)

1. **medium** | `.githooks/pre-commit` (PR #312): line 150 (step 4), line 171 (4a), line 323 (4b) | **[SEC-1, CONFIRMED; votes medium + low]**
   - **Problem:** A staged blob that git treats as binary is printed as `Binary files ... differ` and reaches none of the scans: the JWT, the credentialed URL, the AKIA key or the .env value. Real commits holding FAKE values went through in every case: a NUL byte, UTF-16LE, a `-diff`/`binary` attribute, and a textconv driver. The same content as plain text was refused.
   - **Phase B does not close it:** gitleaks 8.30.1, in both `--pre-commit --staged` and log mode, also misses NUL and UTF-16 (measured).
   - **Fix (a), cheap, needs a ruling, can go in #312:** append `--text --no-textconv` AFTER `-U0` on 4a and 4b.
     - The round-2 git shim matches the argv `diff --cached --no-color --no-ext-diff -U0 ` (tests/test_precommit_hook_round2.py:87, :306, :327), so inserting the flags before `-U0` silently disarms the R3 pins.
     - Add refusal pins for the NUL, `-diff` and textconv cases.
     - Add a no-false-positive pin: staging an existing PNG asset passes.
     - Record in the #312 stated limits: "UTF-16 and line 150 binary stay open".
   - **Fix (b), its own scoped unit (Phase B):** refuse a staged ACMR file that `git diff --cached --numstat --no-textconv` reports as `-<TAB>-`, unless its path is on an allowlist built from the 65 tracked binary files in 13 directories. This closes UTF-16. Fix (b) alone does not cover textconv, because numstat --no-textconv shows such a file as text, so both (a) and (b) are needed.

2. **low** | `.githooks/pre-commit` (PR #312): line 150-153 (the four-branch line), pinned by `tests/test_ci_gates.py:1408-1464` | **[COM-1, CONFIRMED; votes low + low. Folds in SEC-2 (the same mechanism, security lens) and the ++ hole half of DEA-8 (documented TF3)]**
   - **Problem:** The pinned sk-/AKIA/xox/PEM line runs a bare `git diff --cached -U0`. Under `color.ui=always`, `color.diff=always` or `diff.external`, it sees no added lines: an AKIA key was committed with rc=0 (measured). 4a and 4b still refuse under the same config.
   - **Why low:** not a regression (the same bytes have been there since 6205a7ce, 2026-08-30); it needs a non-default config, and none is set on this box; the hook is bypassable with `--no-verify`; it is unrecorded in TF3/TF7.
   - **Fix (needs an orchestrator ruling that lifts correction 6's byte-equal pin; Phase B):** feed the same ERE from `git diff --cached --no-color --no-ext-diff -U0 | awk "$ADDED_LINES_AWK"`. That also closes the TF3 `++` hole. In test_ci_gates, pin only the ERE string, not the whole pipeline line. Add two refusal scenarios: `color.ui=always` and `diff.external=true`.
   - **Until then:** add the bypass to the #312 stated limits next to TF3/TF7.

## B. Low (unverified), grouped by unit of work

### Unit H: pre-commit hook follow-ups (T0b Phase B; same file as A1/A2)
3. **low** | hook line 150 | **[SEC-2]** A duplicate of COM-1 from the security lens. The COM-1 verifiers measured the same mechanism. | Folded into I-2.
4. **low** | hook 4b ENV_FILE resolution; ledger 14:13 | **[SEC-3]**
   - **Problem:** The 64-char ADMIN_API_KEY rotated at 14:13 exists only on Railway. 4b knows only the root .env, which is now stale, and the key has no recognisable shape, so no scan catches it.
   - **Fix, operational:** add a step to the rotation runbook. After each rotation, Ahmed (never an agent) writes the new value into the main checkout's root .env. State this as a 4b precondition in the PR #312 text.
5. **low** | hook :181, the `.env` filename regex | **[SEC-4]**
   - **Problem:** `prod.env`, `railway.env`, `.env-backup`, `.env_prod` and `.envrc` are not refused.
   - **Fix:** widen the regex to `(^|/)(\.env([._-][^/]*)?|[^/]+\.env|\.envrc)$`, case-insensitive, and add one refusal pin per form. No tracked file would newly be refused.
6. **low** | hook steps 4/4a/4b; lines :16, :17, :181, :343; :132; :373 | **[PER-4]**
   - **Problem:** The hook spawns about 23 processes on an empty commit, against about 8 for the base hook: three full staged diffs, four name-only diffs and one Python process per SKILL.md. An empty commit took 44.3 s against 12.0-13.7 s on the slow-spawn box. Use the ratios; the absolute numbers come from a pathological box.
   - **Fix:**
     - Run one staged diff into `$TMP` and feed both 4a and 4b from it, keeping the Z trailer.
     - Skip the 4b awk pass when there are no entries.
     - List the staged names once.
     - Check every SKILL.md in one Python process.
     - Keep the pinned line 150 and the TG4 black probe.
   - This refactor touches the same lines as the A2 fix.
7. **low** | hook :347-370 and `tests/test_skill_frontmatter.py:33-60` | **[COM-9]**
   - **Problem:** The frontmatter rule exists twice.
   - **Fix:** create `scripts/check_skill_frontmatter.py` with `check(text)` and use it from both places, or add a test that both give the same verdicts on one corpus.
8. **low** | hook :204-220 (to_upper), :296-307 | **[COM-10]**
   - **Problem:** A 17-line shell upper-case loop, plus one grep spawn per URL-shaped value.
   - **Fix:** move the NAME and credentialed-URL filters into ENV_MATCH_AWK.
   - UNCERTAIN: whether mawk on CI supports the `[:space:]` bracket class.
9. **low** | hook :68, the `run_tool *)` arm | **[DEA-8]**
   - The `*)` arm is unreachable (only compile, ruff and black are passed). Dropping it is optional.
   - The `++` hole half is documented (TF3) and closed by the A2 fix.

### Unit D: account-deletion follow-ups (U8b)
10. **low** | `app/services/auth_service.py` `_purge_deleted_user_caches` :993-1006 | **[PER-2 + DEA-6]**
    - **Problem:** The purge makes five sequential Upstash DELs. With Redis down and offload OFF (the production default), each one costs attempt + 3 s sleep + attempt, inline on the loop: 35.2 s measured on this box, about 15 s reasoned on Linux. One multi-key DEL measured 7.05 s. The loop placement is documented (UF7); the five round trips are not.
    - **Fix:** one fail-soft `redis_client.delete(*keys)`, through a helper or inline, made as one to_thread hop when the offload flag is ON.
    - **DEA-6:** the `except` at :1004 cannot fire, because delete_cached already swallows exceptions. Either keep it as a documented guard or check the False return instead.
11. **low** | `app/services/database_service.py:396`; `auth_service.py:1022` | **[PER-3]**
    - **Problem:** The cascade RPC and the auth admin delete are bare synchronous calls inside async defs, so ENABLE_SYNC_DB_OFFLOAD cannot cover them.
    - **Fix:** `await run_db(lambda: ...)` for both. Byte-identical with the flag OFF. Reasoned, not measured.
12. **low** | new migration 044 (indexes only) | **[PER-7, plus the PER-1 residual]**
    - **Problem:** deep_review_credits has only the partial index (user_id, expires_at) WHERE consumed_at IS NULL, so 043's DELETE by user_id sequentially scans the consumed rows. user_events and comparison_feedback lack a comparison_id index (LS-DB-QUERIES-07, P3).
    - **Fix:** `CREATE INDEX CONCURRENTLY` on all three, plus a pg_indexes row in PRECHECK. Latent at today's scale.
13. **low** | `migrations/043`: :185 before :195-198 | **[PER-8]**
    - **Problem:** The comparisons DELETE runs first and fires SET NULL updates on the user's own rows, which the following DELETEs then remove.
    - **Fix:** move the four U8b DELETEs above the C2 detach UPDATEs and the comparisons DELETE. The order is pinned, so this needs a ruling and a test update. Reasoned, latent.
14. **low** | `migrations/043` $assert$ :240-248 | **[DEA-7]**
    - **Problem:** The prosecdef/proconfig assert cannot fire in the file as committed.
    - **Fix:** no change; label it as a self-check against edits to this file.

### Unit U: U13 / text_routes tidy (after U13 is permanent)
15. **low** | `app/api/text_routes.py` get_gcc_prices :1475 against :1497-1522 | **[COM-3 + DEA-3, one finding]**
    - **Problem:** The W2-1 comment argues against the dependency that U13 deliberately attached, and the inline verify_admin_key is redundant when both flags are ON.
    - **Fix now:** rewrite the comment.
    - **Fix later:** delete the inline branch once ENABLE_COMPARE_AUTH_REQUIRED is permanent. It is still needed while U13 is OFF and metering is ON.
    - **Pin:** with both flags ON, a wrong key gives exactly one 403.
16. **low** | text_routes :233, :274-346 | **[COM-6]**
    - **Problem:** The two guards share a duplicated tail, and `_refuse_paid_route` lacks a NoReturn annotation.
    - **Fix:** add `-> NoReturn`, `_log_refusal` and `_admin_or_refuse`. The `_PAID_AUTH_DETAIL` duplication is ruled (R9); leave it.
17. **low, documented limit** (U13 spec :276, UR5) | image_routes :185, text_routes :1388-1400, usage_service :25-160 | **[DEA-1]**
    - **Problem:** With U13 ON, app users never reach the anonymous usage gate or the #128 refund wiring.
    - **Fix, docs only:** mark the ENABLE_ANON_USAGE_GATE row and #128 as moot in CLAUDE.md. Delete the code when U13 becomes permanent.

### Unit S: harness scripts
18. **low** | `scripts/eval_runner.py:1220` plus `run_validation_matrix:178`, `bias_matrix_probe:147`, `bundle_d_prod_smoke:63`, `verify_after_credits:49` | **[COM-2 + DEA-11, one finding; folds DEA-9]**
    - **Problem:** The admin-key opt-in helper exists as five AST-identical copies. H07 tests only `'1'` and unset, so drift in four of them goes undetected.
    - **Fix:** one `scripts/harness_auth.py`, imported by the four scripts; verify_after_credits stays as a docs copy. Then either parametrise H07 over the 9-cell matrix or add an AST-equality test.
    - **DEA-9:** in bias_matrix_probe :169 the conditional is redundant (httpx 0.28.1 `headers={}` equals the default, measured). Simplify it to `httpx.AsyncClient(headers=_harness_auth_headers())`.

### Unit O: observability (OAI follow-up)
19. **low, documented follow-up OR20** | `app/services/log_scrub.py` exc_summary | **[PER-6]**
    - **Problem:** The quadratic JWT pattern runs over the uncapped `str(exc)` on the event loop: 5.25 s at 368 KB adversarial, 0.34 s at 92 KB; realistic HTML costs 48 ms/MB. It was relocated from Sentry's before_send, so it is not a regression.
    - **Fix:** pre-cap with `str(exc)[:16384]` before both scrubs; the 200-char cut stays last.
20. **low** | log_scrub.py :55-105 | **[COM-7]**
    - **Problem:** The scrub order is implemented twice.
    - **Fix:** `_scrub_text(text, *, key_shapes=False)`, shared by both callers; safe_exc output stays byte-identical (R3.1). Same unit as item 19.
21. **low** | `app/services/structured_comparison_service.py`: :3777-3780, :4394-4397, :4048, :4834, :8980, :4159, :4980, :3137, :320 | **[COM-11 + DEA-5 + DEA-4]**
    - **Problem:** The per-run resets are duplicated, the downgrade read has three copies, the getattr defaults are dead, and the `cancelled()` skip arm is unreachable.
    - **Fix:** add `_usage_marks_downgrade()` and `_reset_run_state()`, and read the attribute directly at :4159 and :4980. Keep the :320 guard as documented forward-defence. Test: run the stream path twice on one instance.

### Unit C: client follow-ups (#313, U4c, U4d)
22. **low, documented limit L2** (U13C spec) | `SmartCompareApp/src/services/api.ts` identifyFromImages :252-330; `authService.isJwtExpired` :438 | **[PER-5]**
    - **Problem:** An expired token is discovered only after the full multipart upload, so every expired-token camera compare uploads all JPEGs twice.
    - **Fix:** export isJwtExpired and refresh proactively before the first fetch; keep the reactive 401 retry. Reasoned.
23. **low** | api.ts :297-367 | **[COM-5]**
    - **Problem:** The retry builds its own header literal, so a header later added to the first request would silently be missing from the retry. There is also an `unretriedAuthBody` placeholder and a double JSON.parse.
    - **Fix:** `authHeaders(t)` and `toServerError(status, text)`, shared by both fetches. Lock: the u13c suite, 20/20. Same unit as item 22.
24. **low** | `SmartCompareApp/src/screens/ResultsScreen.tsx` :763-835, :383-388 | **[COM-4]**
    - **Problem:** Five parallel ternary chains on loadError.
    - **Fix:** one `EMPTY_STATE` table, plus one parametrised render test over every loadError value.
25. **low** | `SmartCompareApp/src/components/QarenLogo.tsx` :11-12 | **[COM-8]**
    - **Problem:** The docstring says every site is white, but the RevealBurst badge is #ECFDF5.
    - **Fix:** update the docstring. Optional: a pin on an allowlist of import sites.
26. **low, optional, out of lane** | `SmartCompareApp/src/icons/UtilityIcons.tsx` :54-91 | **[DEA-2]**
    - **Problem:** Five icons have 0 consumers, and the revealGlyph R7 pin locks them in.
    - **Fix:** delete them and update R7, or mark them as reserved.
27. **low** | `SmartCompareApp/__tests__/config/nativeBundle.w37.test.ts` :270-271 | **[DEA-10]**
    - **Problem:** The `ICON_ART_SUPPLIED` latch is permanently true.
    - **Fix:** use `it` directly (a test-only change). This overlaps item 3 of the filed render_check_ci issue.

### Tests (report only)
28. **low** | `tests/test_s71_u13_compare_auth_required.py` T10/T11 [U1, A2]; the u8b route-log and templates nodes | **[DEA-12]**
    - **Problem:** Frozen RED nodes are covered by stronger pins.
    - **Fix:** no deletion now; prune them or note the overlap when the files are next unfrozen.

## C. Refuted
- **PER-1** (claimed medium), migrations/043 detach UPDATEs: "every deletion scans user_events/comparison_feedback in a blocking RPC". Both verifiers refuted it:
  - 99% of the cost is the per-row FK check of `DELETE FROM comparisons`, which 025 already runs (025: 12.2-12.7 s; 043: 12.4-12.9 s, at 1M rows). The detach UPDATEs are about 1.4%.
  - The live pg_indexes capture lists a user_events(user_id) index.
  - The synchronous `.execute()` is unchanged by the diff.
  - The backfill runs once, in the SQL editor.
  - At deployed scale (146 user_events rows) the cascade takes well under a millisecond.
  - Residual: a pre-existing comparison_id index gap (LS-DB-QUERIES-07, P3), handled in item 12.

## D. Healthy (reviewer verdicts, condensed)
- **U13 guards** (text_routes :220-347):
  - Router-level `dependencies=` run them before slowapi and before every handler leg, with the flag read per call.
  - A refusal logs only the template and a reason.
  - OpenAPI is unchanged.
  - An empty key counts as no attempt, a wrong key gets 403 from verify_admin_key, and an unset key fails closed.
  - Ten routes are guarded and there is no alternate registration.
  - `[pyt] tag=sec-u13-u8c elapsed=17s status=OK rc=0` (100 passed).
- **U13 ordering and timing:** L5/L6/L7 are documented; the key was rotated to 64 chars, so L6 guessing is infeasible.
- **The stream route** is guarded the same way; there is no query-string token path.
- **Harness scripts:** X-Admin-Key is sent only under opt-in with a non-empty key. Redirects are off, and no header or key is ever logged.
- **Migration 043:**
  - SECURITY DEFINER with search_path pinned to public, and every relation schema-qualified.
  - The REVOKE is restated, and the asserts can fire.
  - The file is one transaction, and the rollback restores 025.
  - There is no IDOR.
  - Existing user_id indexes serve the new DELETEs.
- **Account deletion:**
  - The order is cascade, then purge, then auth delete.
  - Logs carry the exception type and sqlstate only.
  - The purge keys match their five writers.
  - U8c's `from None` is honoured by sentry-sdk 2.68.1.
- **OAI:**
  - exc_summary runs URL scrub, then key shapes, then the cut last.
  - daily_4o_cap never raises.
  - The prefetch done-callback is correct.
  - The max_retries default is unchanged.
  - safe_exc is linear.
- **Camera retry (#313):**
  - Exactly one refresh, through the shared single flight, then one retry to the fixed API_BASE_URL under the same deadline.
  - The abort listener is removed on every settle path.
  - jest u13c: 24/24.
- **Hook value-pass hygiene:**
  - No .env value reaches argv, a temp file or output.
  - The xtrace and allexport guards are in place.
  - The Z trailer makes 4b fail closed.
  - The private mktemp directory fails closed.
- **settings.local.json** on main: a shape-only scan found no secret.
- **Icon renderer:** the master is pinned by SHA-256, there is no network or subprocess, and a full render takes 1.29 s; it is not referenced by CI.
- **CI and dependencies:**
  - The ci.yml drift split is ruled (RQ3), with no pull_request_target.
  - The SDK-54 bumps are patch releases.
  - The client diff adds no network, token-logging or WebView code.
- **Performance of the guards and splash:**
  - The U13 guards cost one verify_token through the shared dependency cache (`[pyt] tag=perf-u13-cache status=OK rc=0`, 20 passed).
  - Refusals cut the work an anonymous caller costs.
  - Per-call env reads are negligible.
  - splashMarkLayout and QarenLogo are trivial; the mark PNGs are 4.7-13.7 KB.
- **Code health:**
  - The 25-column tombstone lists in 043 are pinned equal.
  - splashMarkLayout is pure and pinned to the manifest (B5).
  - U13 has one definition per guard, reused across routers.
  - The deletion logs are type-only.
  - waitForIdentifyRefresh is sound.
  - The sessionEvents comment is accurate.
  - The serper `[brightdata]` INFO lines are ruled out of scope (OAI spec :199).
- **Dead code:**
  - ruff F401/F811/F841 shows 0 new findings across the 18 changed .py files, and ESLint unused-vars counts are equal at base and head.
  - Every new env read is consumed.
  - QaranIcon is fully removed (R6/R8).
  - The QarenLogo color prop is gone with no caller passing it.
  - The 043 asserts and guards can fire.
  - Both ci.yml drift steps run.
  - The hook test lists do not overlap.

## E. Issues (bundle; only confirmed findings or groups)
I-1: SEC-1 (medium). I-2: COM-1 group (low). The bodies are in the StructuredOutput `issues_markdown`; no issue for the refuted PER-1 or for documented-limit items (DEA-1, PER-5, PER-6, DEA-8 ++ half).
