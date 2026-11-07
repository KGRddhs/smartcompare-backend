# S81-G9 ADVERSARY REPORT - correctness lens (data, privacy and robots-policy checks folded in)

Agent: adversary, Opus 5.5 (claude-opus-5-5). Unit S81-G9 FOLLOWUPS (S81-16c + D17c (+ D17d PINs) + S81-22d + S81-23b). Written through the shell (python gen_report.py over this template). Scratch worktree <scratchpad>/S81-G9_adv_correctness detached at b39e265f (no junction), removed at the end with git worktree remove --force; sc-s81-g9 never edited.

VERDICT: SOUND (0 blocking, 0 major, 5 minor -> stated limits / doc rulings, LC-4).

## 1. HEAD and hashes
- sc-s81-g9 HEAD = b39e265fa9d6f808251b8070ab72125660d98ca8 (feature/s81-g9-followups), git status empty; the scratch worktree at the same sha.
- The four frozen RED files (GC-1) re-hashed first (working copy + HEAD blobs) and last (working copy): 8dca7516... / 8a6ced21... / 6faeecc8... / af701284... all EQUAL.
- Every changed file in sc-s81-g9 hashes to the GREEN table's 'after (working copy)' column (16 / 16, 0 mismatches); the three E-row LF blobs (EK1 7732fa24 -> 4ccc2c56, EK2 6cf8c6d3 -> e686619a, EK3 76a00ea5 -> 959ad7a6) equal the PR body table.
- Policy doc: the scratchpad bytes <scratchpad>/g9spec/2026-11-07-wdqs-robots-exemption.md hash 9613f9feb7161b0ff899b8ddfedb9082da17557408c6b97629d27f1e814cb7dd (3,986 B, 0 CR, 0 bytes > 127); the committed blob hashes the same. The pointer line is appended to docs/policies/2026-08-31-robots-unreadable-ruling.md (2 added lines: blank + pointer), blob LF.
- Blob hygiene (python over git cat-file): 0 CR in every changed blob; the count of bytes > 127 per file is unchanged base vs HEAD (CLAUDE.md 3913 / 3913, source_router 489 / 489, ...); 3 added diff lines carry non-ASCII, all pre-existing characters inside in-place-rewritten lines (CLAUDE.md :141 / :341, one structured_comparison_service comment line); the newly written text is ASCII; the new files have 0 bytes > 127.
- ruff 0.16.5 --select E9,F63,F7,F82 clean and py_compile clean on the 13 changed Python files; an extra --select F401,F841,F811 on the 4 code files is clean.
- Commit: one commit, trailer Co-Authored-By: Claude Opus 5.5; no 64-hex literal beside a keyword-named constant (the RED constants are *_LF_SHA); no personal value in any added line (grep for emails / phones / names / key shapes: none).

## 2. Runs ([pyt] lines; every pytest through pyt.py, one at a time, the GREEN driver's wait-for-foreign idiom; nothing killed)
- `[pyt] tag=g9adv-red-off start=2026-11-07 14:32:13 end=2026-11-07 14:32:30 elapsed=17s bound=600s status=OK rc=0 | 68 passed, 10 warnings in 16.34s`
- `[pyt] tag=g9adv-red-on start=2026-11-07 14:33:19 end=2026-11-07 14:33:31 elapsed=11s bound=600s status=OK rc=0 | 68 passed, 10 warnings in 9.34s`
- `[pyt] tag=g9adv-s03-off start=2026-11-07 14:35:03 end=2026-11-07 14:35:15 elapsed=13s bound=600s status=OK rc=0 | 226 passed, 11 warnings in 11.58s`
- `[pyt] tag=g9adv-s03-on start=2026-11-07 14:35:23 end=2026-11-07 14:35:36 elapsed=12s bound=600s status=OK rc=0 | 226 passed, 13 warnings in 11.36s`
- `[pyt] tag=g9adv-ciorder start=2026-11-07 14:35:53 end=2026-11-07 14:37:28 elapsed=95s bound=1200s status=FAIL rc=1 | 7 failed, 1622 passed, 15 warnings in 93.59s (0:01:33)`
- `[pyt] tag=g9adv-crlf-lf start=2026-11-07 14:39:13 end=2026-11-07 14:39:27 elapsed=14s bound=600s status=FAIL rc=1 | 1 failed, 302 passed, 11 warnings in 12.46s`
- `[pyt] tag=g9adv-crlf-lf2 start=2026-11-07 14:39:42 end=2026-11-07 14:39:53 elapsed=11s bound=600s status=OK rc=0 | 303 passed, 11 warnings in 10.10s`
- `[pyt] tag=g9adv-mut-16c-M1 start=2026-11-07 14:40:51 end=2026-11-07 14:40:56 elapsed=5s bound=600s status=FAIL rc=1 | 1 failed, 29 passed, 10 warnings in 4.01s`
- `[pyt] tag=g9adv-mut-16c-M2 start=2026-11-07 14:41:03 end=2026-11-07 14:41:09 elapsed=5s bound=600s status=FAIL rc=1 | 3 failed, 27 passed, 10 warnings in 3.83s`
- `[pyt] tag=g9adv-mut-16c-M3 start=2026-11-07 14:41:16 end=2026-11-07 14:41:21 elapsed=4s bound=600s status=FAIL rc=1 | 2 failed, 28 passed, 10 warnings in 3.53s`
- `[pyt] tag=g9adv-mut-16c-M4 start=2026-11-07 14:41:28 end=2026-11-07 14:41:33 elapsed=4s bound=600s status=FAIL rc=1 | 2 failed, 28 passed, 10 warnings in 3.46s`
- `[pyt] tag=g9adv-mut-16c-M6 start=2026-11-07 14:41:40 end=2026-11-07 14:41:45 elapsed=4s bound=600s status=FAIL rc=1 | 7 failed, 23 passed, 10 warnings in 3.52s`
- `[pyt] tag=g9adv-mut-16c-M8 start=2026-11-07 14:41:52 end=2026-11-07 14:41:57 elapsed=4s bound=600s status=FAIL rc=1 | 2 failed, 28 passed, 10 warnings in 3.42s`
- `[pyt] tag=g9adv-mut-16c-M9 start=2026-11-07 14:42:04 end=2026-11-07 14:42:10 elapsed=5s bound=600s status=FAIL rc=1 | 2 failed, 28 passed, 10 warnings in 3.54s`
- `[pyt] tag=g9adv-mut-16c-M10 start=2026-11-07 14:42:18 end=2026-11-07 14:42:23 elapsed=5s bound=600s status=FAIL rc=1 | 1 failed, 29 passed, 10 warnings in 3.52s`
- `[pyt] tag=g9adv-mut-16c-M12 start=2026-11-07 14:42:32 end=2026-11-07 14:42:47 elapsed=15s bound=600s status=FAIL rc=1 | 4 failed, 26 passed, 10 warnings in 11.77s`
- `[pyt] tag=g9adv-mut-d17c-M1 start=2026-11-07 14:42:54 end=2026-11-07 14:43:02 elapsed=8s bound=600s status=FAIL rc=1 | 2 failed, 9 passed, 11 warnings in 6.81s`
- `[pyt] tag=g9adv-mut-d17c-M3 start=2026-11-07 14:43:10 end=2026-11-07 14:43:19 elapsed=9s bound=600s status=FAIL rc=1 | 4 failed, 7 passed, 11 warnings in 7.23s`
- `[pyt] tag=g9adv-mut-d17c-M5 start=2026-11-07 14:43:27 end=2026-11-07 14:43:34 elapsed=7s bound=600s status=FAIL rc=1 | 1 failed, 10 passed, 11 warnings in 6.14s`
- `[pyt] tag=g9adv-mut-d17c-M6 start=2026-11-07 14:43:42 end=2026-11-07 14:43:49 elapsed=7s bound=600s status=FAIL rc=1 | 2 failed, 9 passed, 11 warnings in 6.11s`
- `[pyt] tag=g9adv-mut-d17c-M8 start=2026-11-07 14:43:57 end=2026-11-07 14:44:04 elapsed=7s bound=600s status=FAIL rc=1 | 1 failed, 10 passed, 11 warnings in 6.10s`
- `[pyt] tag=g9adv-mut-22d-M1 start=2026-11-07 14:44:12 end=2026-11-07 14:44:19 elapsed=7s bound=600s status=FAIL rc=1 | 4 failed, 7 passed, 11 warnings in 6.24s`
- `[pyt] tag=g9adv-mut-23b-M1 start=2026-11-07 14:44:27 end=2026-11-07 14:44:32 elapsed=5s bound=600s status=FAIL rc=1 | 6 failed, 10 passed, 11 warnings in 4.06s`
- `[pyt] tag=g9adv-mut-23b-M4 start=2026-11-07 14:44:39 end=2026-11-07 14:44:45 elapsed=5s bound=600s status=FAIL rc=1 | 1 failed, 15 passed, 11 warnings in 4.12s`
- `[pyt] tag=g9adv-mut-ADV-O1 start=2026-11-07 14:44:53 end=2026-11-07 14:45:00 elapsed=7s bound=600s status=FAIL rc=1 | 1 failed, 29 passed, 10 warnings in 3.81s`
- `[pyt] tag=g9adv-mut-ADV-O2 start=2026-11-07 14:45:08 end=2026-11-07 14:45:12 elapsed=5s bound=600s status=FAIL rc=1 | 1 failed, 29 passed, 10 warnings in 3.49s`
- `[pyt] tag=g9adv-mut-ADV-O3 start=2026-11-07 14:45:20 end=2026-11-07 14:45:24 elapsed=4s bound=600s status=OK rc=0 | 30 passed, 10 warnings in 2.76s`
- `[pyt] tag=g9adv-mut-ADV-O4 start=2026-11-07 14:45:32 end=2026-11-07 14:45:37 elapsed=5s bound=600s status=FAIL rc=1 | 5 failed, 25 passed, 10 warnings in 4.03s`
- `[pyt] tag=g9adv-mut-ADV-O6 start=2026-11-07 14:45:45 end=2026-11-07 14:45:50 elapsed=4s bound=600s status=FAIL rc=1 | 4 failed, 26 passed, 10 warnings in 3.46s`
- `[pyt] tag=g9adv-mut-ADV-O7 start=2026-11-07 14:45:57 end=2026-11-07 14:46:07 elapsed=9s bound=600s status=FAIL rc=1 | 2 failed, 9 passed, 11 warnings in 8.35s`
- `[pyt] tag=g9adv-mut-ADV-O8 start=2026-11-07 14:46:16 end=2026-11-07 14:46:24 elapsed=8s bound=600s status=FAIL rc=1 | 4 failed, 7 passed, 11 warnings in 7.01s`
- `[pyt] tag=g9adv-mut-ADV-O9 start=2026-11-07 14:46:32 end=2026-11-07 14:46:38 elapsed=6s bound=600s status=OK rc=0 | 30 passed, 10 warnings in 3.71s`
- `[pyt] tag=g9adv-mut-ADV-O10 start=2026-11-07 14:46:45 end=2026-11-07 14:46:50 elapsed=5s bound=600s status=FAIL rc=1 | 2 failed, 28 passed, 10 warnings in 3.76s`
- `[pyt] tag=g9adv-mut-ADV-O11 start=2026-11-07 14:46:58 end=2026-11-07 14:47:02 elapsed=4s bound=600s status=FAIL rc=1 | 1 failed, 29 passed, 10 warnings in 3.53s`
- `[pyt] tag=g9adv-mut-ADV-O12 start=2026-11-07 14:47:11 end=2026-11-07 14:47:15 elapsed=4s bound=600s status=OK rc=0 | 30 passed, 10 warnings in 2.82s`
- `[pyt] tag=g9adv-probe start=2026-11-07 14:49:00 end=2026-11-07 14:49:04 elapsed=4s bound=600s status=FAIL rc=1 | 2 failed, 3 passed, 10 warnings in 3.27s`
- `[pyt] tag=g9adv-comm-A start=2026-11-07 14:49:53 end=2026-11-07 14:50:12 elapsed=19s bound=1200s status=OK rc=0 | 286 passed in 16.19s`
- `[pyt] tag=g9adv-comm-B start=2026-11-07 14:50:20 end=2026-11-07 14:50:58 elapsed=38s bound=1200s status=OK rc=0 | 662 passed, 1 deselected, 13 warnings in 36.40s`
- `[pyt] tag=g9adv-comm-C start=2026-11-07 14:51:06 end=2026-11-07 14:53:09 elapsed=123s bound=1200s status=FAIL rc=1 | 1 failed, 1721 passed, 11 warnings in 120.58s (0:02:00)`
- Corpus gate at HEAD alone (no pytest beside it), every ENABLE_* and SCRAPEDO_SUPER removed from the child env: start 2026-11-07 14:55:05 end 15:02:18 rc 0; RECORDS n=414 skipped_no_html=6 distinct_queries=362 non_none=829 calls=1656; OVERALL SHA256 cce256e1940c91a1a3b07e181a91b870d26ffce7247559630ccb66b35d8fe60c = EQUAL to the gate value.

Readout:
- RED files from the exact bytes: 68 / 68 unset (g9adv-red-off) and 68 / 68 with ENABLE_KB_BRANDS=true ENABLE_KB_COVERAGE_ROLLUP=true ENABLE_COMPARE_RUN_LEDGER=true exported in the runner call only (g9adv-red-on).
- S03 file + 22d file: 226 passed unset and 226 passed with ENABLE_COMPARE_RUN_LEDGER=true exported.
- CI-order set (spec 12.1, the RED's ci_order_set.txt): 7 failed / 1622 passed = exactly the CRLF working-copy class (s16 r27 x5, d17 r9, s22 b02). Proven environmental: with the LF blob bytes written for the 9 files those rows read (5 seed / cron scripts, cron_kb_coverage, railway.kbcoverage.json, migration 048 + rollback), the three files ran 303 / 303 passed (g9adv-crlf-lf2; the first attempt g9adv-crlf-lf ran before the two 048 files were restored: 1 failed = b02, as expected).
- Three comm chunks of my choice (25 files each, bound 1200): A = the first 25 GREEN-added members (extra_members.txt): 286 passed; B = the source-scanning pins (test_model_config.py, test_model_config_enforced.py, test_prompt_fence.py, test_secret_scan_static.py, test_u3c_referral_push_name.py, test_u3c_store_false_pin.py) + test_robots_unreadable_ruling.py + 18 CLAUDE.md readers: 662 passed; C = the tests naming scrapedo_service / SCRAPEDO_SUPER / seed_kb_brands_wikidata / cron_kb_coverage / ab_render_providers (first 25 sorted): 1 failed = tests/test_s81_s19_gap_queue.py::test_r15_hygiene, which IS in the stored base record 39ac80ba/fe55771e... (the CRLF class) -> branch-only-new EMPTY for all three chunks. The stored record was REUSED (LC-6), not re-run.
- The four hook test files: NOT run (no .githooks change). The client fences were not re-run (no client file changed; GREEN's jest line stands; LC-7).

## 3. Mutants (sha-verified byte copies in the scratch worktree; the file restored and its sha re-verified after each run; the unit's RED file alone, bound 600)
17 of the 28 spec mutants re-applied (> 10): all 17 KILLED. 12 own mutants (ADV-O*): 9 KILLED, 3 SURVIVED (analysed below).

| mutant | result | killed by (first rows) |
|---|---|---|
| 16c-M1 | KILLED | test_r4_helper_url_and_rules |
| 16c-M2 | KILLED | test_p2_named_group_body_refuses, test_r3_qarenbot_group_refuses, test_r4_helper_url_and_rules |
| 16c-M3 | KILLED | test_p1_r24_shapes_still_refuse[disallow], test_r4_helper_url_and_rules |
| 16c-M4 | KILLED | test_r1b_reordered_live_body_exempt, test_r4_helper_url_and_rules |
| 16c-M6 | KILLED | test_r5_429_then_200_one_retry, test_r5b_429_no_hint_waits_the_cap, test_r6_429_twice_gives_up |
| 16c-M8 | KILLED | test_r7b_hint_above_cap_gives_up[body300], test_r7b_hint_above_cap_gives_up[header999] |
| 16c-M9 | KILLED | test_r7_retry_after_header_and_body[header30], test_r7b_hint_above_cap_gives_up[header999] |
| 16c-M10 | KILLED | test_p5_non_retry_failure_line |
| 16c-M12 | KILLED | test_r2_slash_and_extra_rules_refuse[allow], test_r2_slash_and_extra_rules_refuse[empty], test_r2_slash_and_extra_rules_refuse[slash] |
| d17c-M1 | KILLED | test_r1_zero_hosts_no_pipeline_sdk, test_r2_zero_hosts_no_pipeline_fake |
| d17c-M3 | KILLED | test_r3_400_counts_the_family[1], test_r3_400_counts_the_family[2], test_r4_exec_raise_counts_the_family |
| d17c-M5 | KILLED | test_r1_zero_hosts_no_pipeline_sdk |
| d17c-M6 | KILLED | test_r4_exec_raise_counts_the_family, test_r4b_failed_non_hosts_family_counts |
| d17c-M8 | KILLED | test_r4b_failed_non_hosts_family_counts |
| 22d-M1 | KILLED | test_r1_rows_name_the_flag, test_r2_rows_green_with_flag_exported[i6off-None], test_r2_rows_green_with_flag_exported[i6off-false] |
| 23b-M1 | KILLED | test_r1_legacy_alone_is_off[TRUE], test_r1_legacy_alone_is_off[true], test_r2_legacy_name_never_read |
| 23b-M4 | KILLED | test_p1_new_name_truthy_on[ON_padded] |
| ADV-O1 retry result not re-checked (no retries=1 line) | KILLED | test_r6_429_twice_gives_up |
| ADV-O2 past HTTP date gives a negative wait | KILLED | test_r7_retry_after_header_and_body[date_body45] |
| ADV-O3 named group exact token only | SURVIVED | - |
| ADV-O4 unreadable robots fails open | KILLED | test_p1_r24_shapes_still_refuse[403], test_p1_r24_shapes_still_refuse[timeout], test_p3_unreadable_fail_closed[403] |
| ADV-O6 retry pause skipped | KILLED | test_r5_429_then_200_one_retry, test_r5b_429_no_hint_waits_the_cap, test_r7_retry_after_header_and_body[date_body45] |
| ADV-O7 pipeline_refused label lost | KILLED | test_r3_400_counts_the_family[1], test_r3_400_counts_the_family[2] |
| ADV-O8 main does not add families | KILLED | test_r3_400_counts_the_family[1], test_r3_400_counts_the_family[2], test_r4_exec_raise_counts_the_family |
| ADV-O9 set equality (duplicates allowed) | SURVIVED | - |
| ADV-O10 body hint ignored | KILLED | test_r7_retry_after_header_and_body[date_body45], test_r7b_hint_above_cap_gives_up[body300] |
| ADV-O11 retry on 503 dropped | KILLED | test_r7_retry_after_header_and_body[header30] |
| ADV-O12 exemption not consulted when only '*' disallows | SURVIVED | - |

Survivors:
- ADV-O12 (the exemption consulted only when the QarenBot can_fetch refuses, not when only '*' refuses): EQUIVALENT by the 16c-M5 argument (with no named group, rules_for_agent(QarenBot) == rules_for_agent('*'), so both can_fetch answers agree; a named group refuses first).
- ADV-O9 (set equality instead of the multiset): survives; the duplicated-rule refusal (D-G3, stated in L-S16c-7) has no pin. PN-1.
- ADV-O3 (the named-group check reduced to the exact token 'qarenbot'): survives; my probe shows the GREEN code refuses partial tokens ('qarenbot/1.0', 'bot') as named_group (fail closed, the rules_for_agent token rule), but no RED row pins a partial-token group. PN-2.

## 4. Runtime truth per unit (fakes only; no live request; the plain probe disabled socket connect)
S81-16c (probe16c.py under python -I in the scratch worktree; the probe rows test_zz_adv_probe.py ran once and were deleted):
- wdqs_exemption_check: the LIVE body None; reordered None; comments + Crawl-delay None; two '*' groups splitting the pair None; a Googlebot 'Disallow: /' group beside the pair None (other agents' groups are not read, consistent with the ruled two-rule-set test); a QarenBot group -> named_group; a group 'qarenbot/1.0' or 'bot' -> named_group; 'Disallow: /' -> rule_set; an extra Allow -> rule_set; a duplicated rule -> rule_set; '/SPARQL' -> rule_set; one rule -> rule_set; garbage / empty -> rule_set. URL: http, :443, a trailing slash, a fragment, an upper-case host, /bigdata -> url; the SPARQL URL with any query -> None (the query string is not compared; the script only ever passes sparql_url()).
- Retry wait: '30' -> 30; ' 120 ' -> 120; '121' -> give up; '0' -> 0; a future HTTP date +60 s -> 59.1; +1 h -> give up; a past date with a 45 s body hint -> 45; an unparseable header + body 'Retry in 7 seconds' -> 7; body 300 -> give up; nothing -> the 120 s cap; non-integer '1.5' / '-5' -> the cap.
- Probe rows (g9adv-probe: 3 passed, 2 failed, the failures being the finding): the exempt path with 429 + Retry-After 3 then 200 makes 3 fetches, every one with User-Agent == robots_registry.QARENBOT_UA, sleeps [2.0, 3.0, 2.0], the exemption INFO logged; 503 then 500 -> 3 fetches, 'query failed status=500 retries=1', no write, no report; the DRY exempt run writes nothing to the client. FAILED (MIN-1): Retry-After '9999999' and the body 'retry in 1234567 seconds' WAIT THE 120 s CAP AND RETRY (3 fetches, sleeps [2.0, 120.0, 2.0]) instead of giving up.
- Unreadable robots stays fail-closed (P1 [403] / [timeout], P3; ADV-O4 killed). No QarenBot literal in the script (only re_.QARENBOT_UA references). robots_eval.py and kb_seed_common.py untouched (the RED pins their LF shas; green).
D17c (code read + the RED rows + mutants): 0 hosts -> one INFO 'family=hosts skipped hosts=0' and return BEFORE self.redis.pipeline() (d17c-M1 / M5 killed); every guarded family failure increments families_not_built once (d17c-M3 / M8, ADV-O8 killed) and main adds it to not_built once; the pipeline_refused label only for an AttributeError out of the exec / execute call (d17c-M6, ADV-O7 killed); no per-host counting (one increment per guarded call; d17c-M4 in the RED table); the WARNING / INFO formats carry the family label and an exception type name or the constant only (no host, key or value); P4 / P5 (both cron mains in a python -I child, rc 0, threads == []) green in both runs.
S81-22d: the S03 file + the 22d file green unset and exported; the literal monkeypatch.delenv("ENABLE_COMPARE_RUN_LEDGER", raising=False) occurs exactly twice in tests/test_s81_s03_llm_ledger_v2.py (lines 2443 / 2735, the first statement after each docstring); the three S81-22 test files unchanged base -> HEAD (git diff --quiet); 22d-M1 killed.
S81-23b: grep over app/ and scripts/ for the bare legacy name: 0 hits (the AST census r5 and the recording-os r2 green; 23b-M1 / M4 killed); ab_render_providers.py sets ENABLE_ZYTE_RENDER / ZYTE_TIMEOUT / SCRAPEDO_GEOCODE / SCRAPEDO_TIMEOUT only, never ENABLE_SCRAPEDO_SUPER (only a comment names it); the source_router (5 lines) and structured_comparison_service (1 line) edits are comment / docstring text only (diff read); the corpus gate EQUAL at HEAD.
Production-state claims (from the newest dated ledger lines only, 2026-10-22-session-81-state/ledger.md): SCRAPEDO_SUPER unset on web + price-warmer 2026-11-07 09:02 with 'ENABLE_SCRAPEDO_SUPER never set' (supports 'production carries neither name'); ENABLE_KB_COVERAGE_ROLLUP=apply on kb-coverage at 11:20 (supports the D17c row); ENABLE_KB_BRANDS only ever in a command's own environment (supports 'unset in production').

## 5. Comm re-derivation (union rule; comm_adv.py)
- Import graph over app/ + scripts/ + tests/ (absolute imports, 'from pkg import module' as the module, function-level imports, relative imports resolved (none exist in app / scripts), importlib.import_module / __import__ / spec_from_file_location / run_path constants, dotted 'app.' / 'scripts.' / 'tests.' string constants and bareword module-name constants for the variable-name import_module form); the edited set = the 6 code modules + the 3 E-row test modules; the closure iterated to a fixpoint in BOTH directions (importers of members, and test modules imported BY test members, re-closed); conftest excluded as a carrier (auto-loaded by every test). Plus text readers (the edited paths, CLAUDE.md, docs/policies, the legacy name, the E-row file names) and directory walkers over app / scripts / docs; the hook test files subtracted.
- Result: importer members 675, text readers 274, walkers 40; against the record's 673 + the 27 GREEN additions + the 4 RED files: ONE candidate, tests/test_regression_gate_diff.py, a FALSE POSITIVE of my bareword heuristic (it carries the string 'test_invitee_quiz' as data; it imports only scripts.regression_gate_diff, which imports nothing in the closure). Every CLAUDE.md reader (38) is in the record. 21 record files are not derived by my rules (the record is a superset there).
- The 27 GREEN additions are REAL members the record of 673 missed (verified: e.g. test_ourshopee_demotion / test_bh_gcc_registry_loader / test_registry_row_corrections_94 'from app.services import source_router'; test_async_redis_offload / test_comparison_quality_detector / test_price_parse_offload 'from app.services import structured_comparison_service'): the record's derivation missed the 'from app.services import X' form for the two newly edited modules. GREEN ran all 27 at HEAD (286 + 25 passed); I re-ran 25 of them (chunk A, 286 passed). MIN-2.

## 6. CLAUDE.md and the PR body against the bytes
- CLAUDE.md (HEAD blob LF; the working copy CRLF): the G9 heading at line 616 equals the spec 12.5 heading byte for byte; one blank line before it after the S81-G8 owner-steps bullet; four rows + one owner-steps bullet; one blank line, then '## Tests'. The :341 sentence follows the S81-G8 sentence and equals the spec 12.5 text. In-place edits at :141 / :540 / :541 / :550 / :562 / :605 / :608 only (word diff read); :92 and the S81-08b row untouched; the G1 row keeps ENABLE_SCRAPEDO_SUPER and 2026-08-31-robots-unreadable-ruling.md; lines with both 'scoring_method' and 'enum': 2 at base, 2 at HEAD (none added). Every factual clause checked against the code: true, except the 16c row's 'a hint above the cap gives up' (false for a 7+ digit hint, MIN-1).
- PR body: 16,420 B (python), 0 CR, ASCII except the attribution line; base / HEAD shas right; the E-rows table shas equal my blob hashes; node counts 30 / 11 / 11 / 16 = 68 with 33 RED (= GC-2); 28 mutants with M5 equivalent; the corpus pair EQUAL; the comm 673 + 4 vs the stored record + the 27 additions; fences as reported; stated limits by id incl. L-S16c-5 and L-D17c-5; owner steps names-only; [NATIVE READ] EMPTY. Inaccuracies: MIN-3 ('bytes > 127 = 0 in every added line') and MIN-1 (the give-up sentence).

## 7. Findings
BLOCKING: none.
MAJOR: none.
MINOR (stated limits / doc rulings, LC-4):
- MIN-1 (16c, the retry bound): a Retry-After of 7 or more digits (>= 1,000,000 s) or a body 'retry in N seconds' with N of 7+ digits is not recognised (_RETRY_SECONDS_RE and _RETRY_IN_RE are bounded to 1-6 digits), so the wait falls to the 120 s cap and the script RETRIES ONCE against a longer ask, contrary to R-G9-4 Q-16c-3 ('never retry against a longer ask'); reproduced by two probe rows (3 fetches, sleeps [2.0, 120.0, 2.0]). Bounded: one extra GET after 120 s + 2 s, never a loop, only on an implausible header. Either a stated limit L-S16c-8 or the trivial fix (unbounded digits in both patterns + one row) in the final round; the CLAUDE.md 16c row and the PR body sentence 'a hint above the cap gives up' then name the limit.
- MIN-2 (the comm set of record): the 673 misses the 27 'from app.services import X' importers of source_router / structured_comparison_service that GREEN found; they ran green at HEAD (GREEN, and my chunk A), so branch-only-new stays EMPTY, but the final round's comm set must be the 673 + 27 (+ the 4 RED files) with base-record entries or the HEAD-green argument restated (GREEN Q1: answer YES). Not a MAJOR because no member went unrun.
- MIN-3 (PR body / GREEN report wording): 'bytes > 127 = 0 in every added line' is literally false: 3 added lines carry pre-existing non-ASCII from in-place rewrites; the per-file counts are unchanged and the new text is ASCII. Reword to 'in the added text'.
- MIN-4 (the spec footprint vs GC-6): the spec's footprint sentence says 'no app/ file other than scrapedo_service.py' while GC-6 / Q-23b-3 rule the source_router / structured_comparison_service comment rewordings in; GREEN followed the ruling (5 + 1 comment / docstring lines; 'one line each' read as per comment). A doc ruling only.
- MIN-5 (16c pin coverage): ADV-O9 (multiset vs set, the duplicate-rule refusal claimed in L-S16c-7) and ADV-O3 (partial-token named groups) survive: the code is right by probe, but no row pins either (PN-1 / PN-2).

## 8. Prove-nothing rows
- PN-1: no 16c row distinguishes the multiset from set equality (ADV-O9 survives): the 'duplicate refuses' behaviour of D-G3 is unpinned.
- PN-2: no 16c row carries a named group whose token is a substring of the agent string other than the agent name (ADV-O3 survives).
- PN-3: 16c R7b header999 / body300 prove the give-up only for 3-digit hints; the 6-digit regex bound is invisible to every row (MIN-1).
- PN-4: the corpus gate cannot reach scrapedo_super_enabled (L-S23b-3, reader calls 0 in the gate); its EQUAL proves the extraction spine only.
- PN-5: 16c-M5 / ADV-O12: the '*' and the QarenBot rule-set comparisons cannot be told apart by any body once the named-group check runs first (L-S16c-5).

## 9. State
The scratch worktree removed (git worktree list: no S81-G9_adv entry; no junction was ever made). No pytest / jest of mine alive. sc-s81-g9 untouched (HEAD b39e265f, status empty). Artifacts under <scratchpad>/S81-G9_adv/: driver.py, mutants.py, mutants.json, comm_adv.py, comm_missing.txt, probe16c.py, test_zz_adv_probe.py, chunkA-C.txt, pyt_lines.txt, pyt_clean.txt, logs/, corpus_head.txt.
