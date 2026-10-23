# S81-05 FIX ROUND 1 REPORT (REQUEST-CONTEXT, ENABLE_REQUEST_CONTEXT_HEADERS, lane B)

- Agent: fix agent, Opus 5.5 (claude-opus-5-5). Start 2026-10-23 17:23 AST, end ~18:35 AST.
- Worktree C:/Users/SynAckITPC/Documents/AI/sc-s81-s05, branch feature/s81-s05-request-context. Start HEAD e9fd714868c4036f904e1f840e77cb217bf3c96e verified, `git status --short` empty. End HEAD **b7b30dcd6497b95569e547a3dba4efc2a68eb109** (ONE commit through the pre-commit hook; no push, no rebase, no stash, no other git write; no scratch worktree). `git status --short` at the end: empty. Measurement base stays 84c861f6.
- Inputs read: s81-common.txt, RULINGS_FIX1_S81_05 (binding), RULINGS_S81_05, GATE_S81_05, both ADV1 reports, the GREEN report, the GREEN PR body draft; the sibling fix-round procedures (RULINGS_FIX1_ST1 / RULINGS_FIX1_D03) as the template, because RULINGS_FIX1_S81_05 has no "Procedure for the fix agent" section.
- Notes folder: <scratchpad>/S81-05_fix1/ (notes.md, before/ byte copies + SHA256SUMS.txt, red.log, unit_*.log, p04_*.log, g6_flagon.log, ciorder_*.log, pins28_*.log, billing_on.log, mutate_fix1.py, mutation_results_fix1.json, mut_logs/, mut_backup/, runchunk.sh, comm/, comm_summary.py, comm_summary.txt, PR_BODY.md).

## Files (sha256 of the bytes on disk at the end)

| path | before (e9fd7148) | after | +/- |
|---|---|---|---|
| app/utils/request_context.py (LF, 0 bytes > 127) | ae5bc868ef0a6821dae493dcb68fce82ef9d0f48556348a0cf26066ddcfda949 | df794edbc5b1470c000767852820f2d46ecaacf76204f3ddb5be7bdd62b3691a | +21 / -15 |
| app/main.py (CRLF 635/635, 36 bytes > 127 as before) | 5b55a9cd3c04bf403fc7fab2734b554ed1d4439615e3ef12a78bc63f848868c4 | 923c40c87efa18fe4cf2f61c28d671e526fe56520f043c381507c8b69ef1431a | +9 / -5 |
| CLAUDE.md (CRLF 949/949, 3946 bytes > 127 as before) | c0db53781d2da8918bd1dc3810add1f0518ab44b08be40a9707f196c83c8997b | 52770c0bd9c76c505c7d07303c4dfe2cea2ca57d630e392d8aa9885966779f42 | +2 / -2 (two lines rewritten in place) |
| tests/test_s81_s05_request_context.py (LF, 0 bytes > 127) | b7a21c742174ab682968ce7dba1e5d6f3f7696b8c37afed116d0884d79fd6c83 | 4cef1984dbd52eb9ea2fbab01010f0d985974adf1fb511900185335d5e087b1e | +62 / -0 |

RED file: the GREEN bytes (b7a21c74...) are a strict prefix of the new file (byte compare True); the frozen 52,230 bytes still hash to ecdb579286f0cc1f19798b0349e5b001e982a8bff325282d5769584d4fb3a26d. Committed blobs: leaf df794edb... and test 4cef1984... (LF files, equal to disk); main.py blob 265fa25a..., CLAUDE.md blob 81d09d71... (index LF, disk CRLF). Middleware untouched (d6f06adf...). Added lines: 0 non-ASCII bytes; sweep (@gmail, +973, 8-digit runs, sk- / eyJ / PEM / credentialed URL) empty.

## What changed

- F1-1: `device_key` wraps the pepper encode in `try: key = pepper.strip().encode("utf-8") except UnicodeError: _warn_pepper_once(); return None` (the SAME rate-limited WARNING naming DEVICE_KEY_PEPPER; never the value, never the exception text); the HMAC uses `key`.
- F1-2: `_header_index` compares bytes names as exact bytes (`bytes(name)`, no `.lower()`); `header_state` returns the bound state directly (the non-constant-state filter removed). The try/except "a state read is total" arm is kept (not named by the ruling).
- Leaf docstring: F1-7 (flag read once per ASGI call of any scope type, binds for HTTP only), F1-2 (exact bytes / str case-insensitive), F1-1 (the unencodable pepper case, same line). `header_state` docstring per F1-2.
- main.py S81-05 comment: F1-7 ("read once per ASGI call of any scope type ... as its first statement"; "flag OFF = one os.getenv per ASGI call"), engineering m3 ("SlowAPIASGI (when enabled)"), F1-3 (the key_func sentence verbatim: "never through the default-limit (SlowAPIASGIMiddleware) key_func, which runs outside the ContextVar scope; a per-route @limiter.limit key_func runs inside it and may read these values (measured)").
- CLAUDE.md S81-05 row rewritten in place: the header names the fix-round rulings; F1-7 (intro read sentence, Flag OFF "per ASGI call", limit (9), rollback); F1-2 (header_state exact bytes / str case-insensitive, only the three constants bound); F1-1 (the unencodable pepper, the same line); F1-6 (the byte-identity sentence); F1-5 (r26 / qaren-worker); F1-3 (limit (4)); F1-4 (canary).
- PR body draft: <scratchpad>/S81-05_fix1/PR_BODY.md (sha256 after the commit-sha edit recorded by the orchestrator's read; ASCII except the 4-byte attribution emoji line carried over from GREEN's draft): F1-3 (limit 5), F1-5 (limit 4), F1-6, F1-7 (flag read, limit 10, rollback), F1-4 (canary line), F1-10 (pin table: p19 / p20 = GREEN-time contract rows, red at base because the leaf is absent), the F1-1 row in the id table, a "Fix round 1" section and the fix-round gate lines.

## RED step

- Row appended: `test_s05_fx1_device_key_fails_closed_on_unencodable_pepper` (2 params: `surrogateescape` = "s05" + chr(0xDCFF) + "pepper", `lone-high` = "  " + chr(0xD800) + "s05\t"; built at run time; `os.getenv` patched for the pepper name only, the r11 house pattern, because that is what os.environ returns for a non-UTF-8 env byte on POSIX and it is platform-independent). Asserts: no exception over 3 calls, all None, exactly ONE leaf record, WARNING, the exact WARN_TEXT, names DEVICE_KEY_PEPPER, no exc_info, neither the stripped pepper nor "surrogate" / "codec" / "UnicodeEncodeError" / "UnicodeError" / the fingerprint in caplog, `dk("zz")` None, latch reset gives a second WARNING.
- Run on the pre-fix app bytes (leaf sha ae5bc868... = the e9fd7148 blob, before any GREEN edit, no checkout; only the test file appended): `[pyt] tag=s05f1-red start=2026-10-23 17:37:33 end=2026-10-23 17:37:55 elapsed=22s bound=600s status=FAIL rc=1` -> 2 failed, 173 passed; [hermeticity] sentinel checked 175 test(s); [netguard] blocked 0 attempt(s) from 0 node(s). Both failures `E AssertionError: ['UnicodeEncodeError', 'UnicodeEncodeError', 'UnicodeEncodeError']` (test line 1703): the exception seen at e9fd7148 is UnicodeEncodeError raised out of device_key. 0 non-assertion failure lines. Mutant MF1a (the pre-fix encode restored on a byte copy of the fix bytes) is the same measurement on the fix bytes: KILLED on assertions.

## Runs (every [pyt] line)

- unit OFF (after the leaf fix): `[pyt] tag=s05f1-unit-off start=2026-10-23 17:39:36 end=2026-10-23 17:39:48 elapsed=12s bound=600s status=OK rc=0` 175 passed; [hermeticity] 175; [netguard] blocked 0
- unit ON (flag exported): `[pyt] tag=s05f1-unit-on start=2026-10-23 17:39:51 end=2026-10-23 17:40:22 elapsed=31s bound=600s status=OK rc=0` 175 passed; [hermeticity] 175; [netguard] blocked 0
- unit OFF final bytes: `[pyt] tag=s05f1-unit-off-final start=2026-10-23 18:25:17 end=2026-10-23 18:25:29 elapsed=12s bound=600s status=OK rc=0` 175 passed; [hermeticity] sentinel checked 175 test(s); [netguard] blocked 0 attempt(s) from 0 node(s)
- unit ON final bytes: `[pyt] tag=s05f1-unit-on-final start=2026-10-23 18:25:33 end=2026-10-23 18:25:40 elapsed=7s bound=600s status=OK rc=0` 175 passed; [hermeticity] sentinel checked 175 test(s); [netguard] blocked 0 attempt(s) from 0 node(s)
- P4 OFF: `[pyt] tag=s05f1-p04-off start=2026-10-23 17:57:35 end=2026-10-23 17:58:20 elapsed=45s bound=600s status=OK rc=0` 8 passed, 167 deselected; [hermeticity] 8; [netguard] blocked 0
- P4 ON (flag exported): `[pyt] tag=s05f1-p04-on start=2026-10-23 17:58:24 end=2026-10-23 17:58:30 elapsed=7s bound=600s status=OK rc=0` 8 passed, 167 deselected; [hermeticity] 8; [netguard] blocked 0
- G6 identity pins, flag exported (test_s75_fanout_identity, test_w4_13_flag_off_ledger, test_s71_u13_compare_auth_required, test_retro_w1_9, test_observability, test_security_middleware): `[pyt] tag=s05f1-g6-flagon start=2026-10-23 17:58:56 end=2026-10-23 17:59:23 elapsed=27s bound=1200s status=OK rc=0` 215 passed (= GREEN 215); [hermeticity] 215; [netguard] blocked 0
- CI-order set chunk 1 (auth_routes_invite_fingerprint, behavior_dimension_translation, ci_gates, conftest_env_safety, m13_01_slowapi_middleware, observability, retro_w1_9, s71_u13_compare_auth_required): `[pyt] tag=s05f1-ciorder-1 start=2026-10-23 18:00:09 end=2026-10-23 18:00:47 elapsed=38s bound=1200s status=OK rc=0` 329 passed, 1 skipped, 2 deselected; [hermeticity] 330; [netguard] blocked 4 attempt(s) from 4 node(s) (neutralized.supabase.invalid sentinels)
- CI-order set chunk 2 (s75_fanout_identity, s79_b3b_apple_revoke, s81_s05_request_context, security_middleware, security_regression, sentry_channels_u8d_unit, social_login_device_fingerprint, w4_13_flag_off_ledger): `[pyt] tag=s05f1-ciorder-2 start=2026-10-23 18:01:01 end=2026-10-23 18:01:30 elapsed=28s bound=1200s status=OK rc=0` 573 passed; [hermeticity] 573; [netguard] blocked 12 attempt(s) from 6 node(s). Together 902 passed + 1 skipped + 2 deselected = GREEN's 900 + the 2 fx1 nodes; netguard 16 / 10 = GREEN.
- 28-file pin set extras a (image_identify_llm_unavailable_s69, m18_usage_symmetry, paid_route_metering, retro_w2_1, s80_url_mode_v2, migration_index_predicate_immutability): `[pyt] tag=s05f1-pins28-a start=2026-10-23 18:02:03 end=2026-10-23 18:02:17 elapsed=14s bound=1200s status=OK rc=0` 647 passed; [hermeticity] 647; [netguard] blocked 2 attempt(s) from 2 node(s)
- 28-file pin set extras b (model_config, model_config_enforced, openai_key_log_hygiene_s69, prompt_fence, start_command, u3c_store_false_pin): `[pyt] tag=s05f1-pins28-b start=2026-10-23 18:02:35 end=2026-10-23 18:02:47 elapsed=12s bound=1200s status=OK rc=0` 167 passed; [hermeticity] 167; [netguard] blocked 0
- billing / identity pins, flag exported (the first five of extras a): `[pyt] tag=s05f1-billing-on start=2026-10-23 18:02:51 end=2026-10-23 18:03:05 elapsed=14s bound=1200s status=OK rc=0` 604 passed; [hermeticity] 604; [netguard] blocked 2 attempt(s) from 2 node(s)
- Mutation table (25 mutants, whole unit file each, byte copy -> exact edit matching once (dry-checked 25 / 0 bad anchors) -> run -> restore -> sha256 compare (pre_mutation_SHA256SUMS.txt OK after the run), .qa-mutation.lock created and removed): 25 KILLED, 0 errors, 0 non-assertion failures:
  - `[pyt] tag=s05f1-mut-X20 start=2026-10-23 17:42:00 end=2026-10-23 17:43:05 elapsed=65s bound=600s status=FAIL rc=1` (5: r10, r12)
  - `[pyt] tag=s05f1-mut-X21 start=2026-10-23 17:43:08 end=2026-10-23 17:43:17 elapsed=9s bound=600s status=FAIL rc=1` (8: r11)
  - `[pyt] tag=s05f1-mut-X22 start=2026-10-23 17:43:18 end=2026-10-23 17:43:27 elapsed=9s bound=600s status=FAIL rc=1` (2: r10)
  - `[pyt] tag=s05f1-mut-X23 start=2026-10-23 17:43:28 end=2026-10-23 17:43:51 elapsed=23s bound=600s status=FAIL rc=1` (6: fx1, r10)
  - `[pyt] tag=s05f1-mut-X24 start=2026-10-23 17:43:53 end=2026-10-23 17:44:10 elapsed=17s bound=600s status=FAIL rc=1` (5: r10, r24)
  - `[pyt] tag=s05f1-mut-X25 start=2026-10-23 17:44:12 end=2026-10-23 17:44:23 elapsed=11s bound=600s status=FAIL rc=1` (3: r09, r26)
  - `[pyt] tag=s05f1-mut-X25b start=2026-10-23 17:44:25 end=2026-10-23 17:44:38 elapsed=13s bound=600s status=FAIL rc=1` (3: r09, r26)
  - `[pyt] tag=s05f1-mut-ME8 start=2026-10-23 17:44:39 end=2026-10-23 17:44:48 elapsed=9s bound=600s status=FAIL rc=1` (1: r09[padded])
  - `[pyt] tag=s05f1-mut-X37 start=2026-10-23 17:44:49 end=2026-10-23 17:44:57 elapsed=8s bound=600s status=FAIL rc=1` (4: p01, r20-atomic, r23, r24)
  - `[pyt] tag=s05f1-mut-MF1a start=2026-10-23 17:44:58 end=2026-10-23 17:45:04 elapsed=7s bound=600s status=FAIL rc=1` (2: fx1) - the except removed (the ruling's mutant)
  - `[pyt] tag=s05f1-mut-MF1b start=2026-10-23 17:45:06 end=2026-10-23 17:45:35 elapsed=30s bound=600s status=FAIL rc=1` (2: fx1) - the except arm without the WARNING
  - `[pyt] tag=s05f1-mut-MF1c start=2026-10-23 17:45:38 end=2026-10-23 17:46:22 elapsed=44s bound=600s status=FAIL rc=1` (2: fx1) - a surrogatepass fallback key
  - `[pyt] tag=s05f1-mut-MF1d start=2026-10-23 17:46:24 end=2026-10-23 17:46:31 elapsed=7s bound=600s status=FAIL rc=1` (2: fx1) - `except UnicodeDecodeError`
  - `[pyt] tag=s05f1-mut-MF1e start=2026-10-23 17:47:04 end=2026-10-23 17:47:12 elapsed=7s bound=600s status=FAIL rc=1` (3: fx1, r24) - the exception text logged
  - `[pyt] tag=s05f1-mut-X40 start=2026-10-23 17:47:13 end=2026-10-23 17:47:20 elapsed=7s bound=600s status=FAIL rc=1` (26)
  - `[pyt] tag=s05f1-mut-XSLV start=2026-10-23 17:47:22 end=2026-10-23 17:47:40 elapsed=17s bound=600s status=FAIL rc=1` (9: p19, p20, r13) - with the filter gone this is GREEN's XSLV2
  - `[pyt] tag=s05f1-mut-XP19a start=2026-10-23 17:47:41 end=2026-10-23 17:47:49 elapsed=8s bound=600s status=FAIL rc=1` (3: p19)
  - `[pyt] tag=s05f1-mut-XP19b start=2026-10-23 17:47:50 end=2026-10-23 17:48:01 elapsed=11s bound=600s status=FAIL rc=1` (3: p19)
  - `[pyt] tag=s05f1-mut-XP19c start=2026-10-23 17:48:03 end=2026-10-23 17:48:23 elapsed=20s bound=600s status=FAIL rc=1` (2: p19)
  - `[pyt] tag=s05f1-mut-XP19d start=2026-10-23 17:48:24 end=2026-10-23 17:48:31 elapsed=7s bound=600s status=FAIL rc=1` (19) - new: the bytes branch returns None
  - `[pyt] tag=s05f1-mut-X26s start=2026-10-23 17:48:32 end=2026-10-23 17:48:41 elapsed=8s bound=600s status=FAIL rc=1` (12)
  - `[pyt] tag=s05f1-mut-X27s start=2026-10-23 17:48:42 end=2026-10-23 17:48:49 elapsed=8s bound=600s status=FAIL rc=1` (3: r20-atomic)
  - `[pyt] tag=s05f1-mut-XP20 start=2026-10-23 17:48:50 end=2026-10-23 17:49:03 elapsed=12s bound=600s status=FAIL rc=1` (3: p20)
  - `[pyt] tag=s05f1-mut-XP20b start=2026-10-23 17:49:08 end=2026-10-23 17:49:39 elapsed=31s bound=600s status=FAIL rc=1` (3: p20)
  - `[pyt] tag=s05f1-mut-XHSO start=2026-10-23 17:49:42 end=2026-10-23 17:49:54 elapsed=12s bound=600s status=FAIL rc=1` (3: p19) - new: a bound unknown name reads "ok"
- Comm set at the fix bytes (GREEN's 210 files and its 15 chunk lists verbatim; c05 split in halves to stay inside one tool call): totals 9,320 passed, 2 failed, 33 skipped, 35 xfailed, 79 deselected vs GREEN 9,318 / 2 / 33 / 35 / 79 (+2 = the fx1 rows in c11). FAILED set = GREEN's = {tests/test_auth_interceptor.py::test_sign_in_with_social_exception, ::test_social_login_user_insert_fails_gracefully} (tests/.pre_impl_failures.txt rows). **branch-only-NEW vs the GREEN record: EMPTY.** Netguard nodes equal GREEN's per chunk except c04's `tests/test_flush_live_price_key.py::test_flag_off_body_is_the_legacy_shape_exactly [egress] socket.getaddrinfo api.openai.com:443` (listed in tests/.network_attempt_baseline.txt:41; the file is unchanged since 84c861f6; the node passed) and c05's ephemeral loopback ports in test_hermeticity_pins (same nodes).
  - `[pyt] tag=s05f1-comm-c00 start=2026-10-23 18:04:00 end=2026-10-23 18:04:17 elapsed=17s bound=1200s status=OK rc=0` 447 passed; [hermeticity] 447; [netguard] blocked 0 attempt(s) from 0 node(s)
  - `[pyt] tag=s05f1-comm-c01 start=2026-10-23 18:04:28 end=2026-10-23 18:04:49 elapsed=22s bound=1200s status=FAIL rc=1` 2 failed, 555 passed, 25 deselected; [hermeticity] 557; [netguard] blocked 19 attempt(s) from 8 node(s)
  - `[pyt] tag=s05f1-comm-c02 start=2026-10-23 18:05:00 end=2026-10-23 18:05:23 elapsed=23s bound=1200s status=OK rc=0` 856 passed, 11 deselected; [hermeticity] 856; [netguard] blocked 13 attempt(s) from 8 node(s)
  - `[pyt] tag=s05f1-comm-c03 start=2026-10-23 18:05:58 end=2026-10-23 18:06:34 elapsed=35s bound=1200s status=OK rc=0` 154 passed, 1 skipped, 11 deselected; [hermeticity] 155; [netguard] blocked 2 attempt(s) from 1 node(s)
  - `[pyt] tag=s05f1-comm-c04 start=2026-10-23 18:06:46 end=2026-10-23 18:07:30 elapsed=44s bound=1200s status=OK rc=0` 1262 passed; [hermeticity] 1262; [netguard] blocked 32 attempt(s) from 12 node(s)
  - `[pyt] tag=s05f1-comm-c05a start=2026-10-23 18:08:42 end=2026-10-23 18:11:27 elapsed=165s bound=1200s status=OK rc=0` 218 passed; [hermeticity] 218; [netguard] blocked 29 attempt(s) from 28 node(s)
  - `[pyt] tag=s05f1-comm-c05b start=2026-10-23 18:11:57 end=2026-10-23 18:12:07 elapsed=10s bound=1200s status=OK rc=0` 212 passed, 9 deselected; [hermeticity] 212; [netguard] blocked 0 attempt(s) from 0 node(s)
  - `[pyt] tag=s05f1-comm-c06 start=2026-10-23 18:12:25 end=2026-10-23 18:12:37 elapsed=12s bound=1200s status=OK rc=0` 132 passed; [hermeticity] 132; [netguard] blocked 3 attempt(s) from 3 node(s)
  - `[pyt] tag=s05f1-comm-c07 start=2026-10-23 18:12:48 end=2026-10-23 18:13:11 elapsed=23s bound=1200s status=OK rc=0` 339 passed, 10 deselected; [hermeticity] 339; [netguard] blocked 0 attempt(s) from 0 node(s)
  - `[pyt] tag=s05f1-comm-c08 start=2026-10-23 18:13:22 end=2026-10-23 18:13:45 elapsed=23s bound=1200s status=OK rc=0` 363 passed, 21 skipped, 2 deselected; [hermeticity] 363; [netguard] blocked 26 attempt(s) from 12 node(s)
  - `[pyt] tag=s05f1-comm-c09 start=2026-10-23 18:14:47 end=2026-10-23 18:16:39 elapsed=112s bound=1200s status=OK rc=0` 461 passed, 1 skipped, 1 deselected; [hermeticity] 461; [netguard] blocked 89 attempt(s) from 8 node(s)
  - `[pyt] tag=s05f1-comm-c10 start=2026-10-23 18:16:54 end=2026-10-23 18:18:19 elapsed=85s bound=1200s status=OK rc=0` 598 passed; [hermeticity] 598; [netguard] blocked 0 attempt(s) from 0 node(s)
  - `[pyt] tag=s05f1-comm-c11 start=2026-10-23 18:18:57 end=2026-10-23 18:20:56 elapsed=119s bound=1200s status=OK rc=0` 1909 passed; [hermeticity] 1909; [netguard] blocked 5 attempt(s) from 3 node(s)
  - `[pyt] tag=s05f1-comm-c12 start=2026-10-23 18:21:12 end=2026-10-23 18:21:40 elapsed=28s bound=1200s status=OK rc=0` 612 passed, 1 skipped, 8 deselected; [hermeticity] 613; [netguard] blocked 14 attempt(s) from 8 node(s)
  - `[pyt] tag=s05f1-comm-c13 start=2026-10-23 18:22:08 end=2026-10-23 18:23:12 elapsed=64s bound=1200s status=OK rc=0` 370 passed, 2 deselected; [hermeticity] 370; [netguard] blocked 130 attempt(s) from 58 node(s)
  - `[pyt] tag=s05f1-comm-c14 start=2026-10-23 18:23:33 end=2026-10-23 18:24:06 elapsed=33s bound=1200s status=OK rc=0` 832 passed, 9 skipped, 35 xfailed; [hermeticity] 876; [netguard] blocked 8 attempt(s) from 8 node(s)
- Lint (not pytest): ruff `--select E9,F63,F7,F82 --no-cache` on the leaf, main.py and the test file: All checks passed; py_compile OK on the three; black 26.5.1 `--check --config pyproject.toml` on the leaf and the test file: unchanged (main.py is not in .github/black-clean-paths.txt and was "would be reformatted" at 84c861f6 and at e9fd7148 too, measured from the blobs). Pre-commit hook on the commit: passed (ruff + the black allowlist mirror + the secret scans); no --no-verify.
- Load: node -e 0 1.43 s (17:34), 12.2 s (17:56), 1.48 s (18:00), 2.72 s (18:28): never idle, so F1-9 applies.

## Counts

- RED rows added 2 (one function, 2 params); both fail at e9fd7148 on AssertionError only; 173 existing rows green at that run.
- Mutants 25 / 25 KILLED (the 9 device_key rows of GREEN's table re-anchored, 5 F1-1 mutants, 11 header_state / state rows incl. 2 new: XP19d, XHSO). The STATELEAK / case-fold mutants fall away by F1-2 (removed code, no pin), as ruled.

## Deviations

- D1 RULINGS_FIX1_S81_05 carries no "Procedure for the fix agent" section (grep); the task text and the RULINGS_FIX1_ST1 / D03 procedure were followed.
- D2 The pre-fix RED evidence was measured in the worktree on the UNMODIFIED e9fd7148 app bytes (only the test file appended; leaf sha ae5bc868... checked before the run), not on a separate scratch checkout: a scratch worktree is a git write and the task allows ONE commit and no other git write. MF1a (the pre-fix encode restored on a byte copy) repeats it on the fix bytes. No checkout anywhere.
- D3 "The 28-file pin set" is not defined in any file I read; I composed it as GREEN's 16-file CI-order set + the five billing / identity pins the correctness adversary ran ON + seven source-scanning pins (16 + 5 + 7 = 28). Assumption, for the orchestrator to confirm.
- D4 The mutation table goes beyond the ruling's one F1-1 mutant (five F1-1 mutants, plus XP19d and XHSO for the new header_state body).
- D5 The middleware module docstring was not edited: it already says "read once per call as the FIRST statement" (accurate); the rulings name the CLAUDE.md row, the PR body, the main.py comment and the leaf docstring only.
- D6 The leaf docstring carries no "pinned by r26" phrase, so F1-5 lands in the row and the PR body only.
- D7 The F1-3 sentence is placed in CLAUDE.md limit (4) with code spans (`SlowAPIASGIMiddleware`, `@limiter.limit`); in main.py it follows "A device-keyed limiter reads these values" to form a sentence.
- D8 The WARNING text stays "[REQUEST-CONTEXT] DEVICE_KEY_PEPPER unset or blank; device keys disabled (fail closed)" for the unencodable case too (the ruling says the SAME warning; r10 and the new row pin the exact text); the row and the docstring say "the same line for both".
- D9 PR_BODY.md keeps the 4-byte attribution emoji line of GREEN's draft (the only bytes > 127 in it).
- D10 The commit call ran `cd <worktree> && git ...` outside a subshell (the tool resets the cwd between calls; no effect on any other worktree).

## Questions for the gate

- Q1 Confirm or replace the 28-file pin set composition (D3).
- Q2 The WARNING text says "unset or blank" for an unencodable pepper too (D8): keep (as ruled) or broaden in a later unit (S81-09 reads it)?
- Q3 Next step per F1-11: the rebase onto the main of that moment (CLAUDE.md anchor union in the session order and the FY25 UNIT_ENV union); not done here.

## NOT MEASURED

- `tests/test_precommit_hook.py -k black` (4 nodes): NOT MEASURED locally this round under F1-9 (box never idle; no .githooks or black-ratchet change in the round; GREEN's run was green; CI covers them).
- No live socket / uvicorn run (as in GREEN).

## git status --short of the worktree at the end

(empty)
