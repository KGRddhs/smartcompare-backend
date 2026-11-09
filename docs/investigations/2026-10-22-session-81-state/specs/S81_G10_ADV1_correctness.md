# S81-G10 ADVERSARY REPORT - correctness lens (R-G10-14 checks folded in)

- Unit: S81-G10 FOLLOWUPS = D-S22-J1 + S81-22b + S81-22c (with D-S22-K1) + S81-04d; the tenth SAFE group under LC-9; orchestrator Opus 5.5 by the owner's ruling of 2026-11-07.
- Agent: the S81-G10 correctness adversary, Opus 5.5 (claude-opus-5-5). First tool call 2026-11-09 19:53:56 AST; report 20:33 AST (about 40 min of the 90).
- HEAD verified first: sc-s81-g10 = aed1393bb662480a759fe9e378031e1669b57e50 on feature/s81-g10-followups, parent 90d4ed74bdd16f62130dc9f7a4727620f8a1cea2, ONE commit, status clean, trailer "Co-Authored-By: Claude Opus 5.5". Unchanged at the end.
- Scratch: detached worktree <scratchpad>/S81-G10_adv_correctness at aed1393b (no junction, no node_modules), every probe and mutant there; removed with git worktree remove --force; git worktree list holds no entry for it. The GREEN worktree was never written.
- Written through the shell (report .md rule). Notes, logs and tools: <scratchpad>/S81-G10_adv/.

## VERDICT: SOUND (blocking 0, major 0, minor 6)

## 1. Frozen files (GC-1), re-hashed first (19:54) and last (20:31) from the LF bytes
- GREEN worktree (raw = LF, cr=0, gt127=0) and the scratch checkout (CRLF working copy, LF form compared): all five equal GC-1:
  94143f05... test_s81_s22j1_judge_jsonb_filter.py (21,706 B); bd94edc8... test_s81_s22b_self_critique_retire.py (21,860 B); 364f88a8... test_s81_s22c_kb_product_ids.py (13,654 B); 5be53dbd... test_s81_s04d_durable_retrieve.py (16,807 B); de994a8e... tests/fixtures/s81_s22b_flag_off_golden.json (146,604 B). ALL_OK both times.

## 2. Changed bytes vs the GREEN table
- git diff --raw 90d4ed74..aed1393b: 36 paths (28 modified, 5 added, 3 deleted); every base -> new blob equals the GREEN report section 3 table and the PR body E-rows column (10-char prefixes checked one by one).
- Every HEAD blob is LF-only (crlf=0, processors.json and CLAUDE.md included); bytes > 127 = 0 in the five new files; git diff --stat is hunks only.
- EJ2: 86614fb4998b981b08adca3b20c01224ad8b927da9dccaa5c1d39099abacc99e = the measured sha256 of the HEAD blob of tests/test_s81_s22_judge.py (longest digit run 5).
- Lint at HEAD (scratch): ruff --select E9,F63,F7,F82 "All checks passed!" and py_compile clean on the 9 app/scripts files + 20 test files; ruff F401/F841/F811 clean on feedback_service / llm_router / model_config / compare_runs / llm_spend_breaker / cron_compare_judge (importlib still used by the router); json.loads clean on processors.json, legal_s78.json, the golden.
- Added-line sweeps: no digest constant named with a gitleaks keyword, no 8-digit run (golden included), no personal / key shape.

## 3. Every [pyt] line of this run (the scratch worktree at aed1393b; one pytest at a time)
```
[pyt] tag=g10adv-red-off start=2026-11-09 19:56:47 end=2026-11-09 19:57:01 elapsed=13s bound=600s status=OK rc=0 | 75 passed, 11 warnings in 12.25s | [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=g10adv-red-on start=2026-11-09 19:57:05 end=2026-11-09 19:57:18 elapsed=13s bound=600s status=OK rc=0 | 75 passed, 11 warnings in 12.03s | [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=g10adv-ciorder start=2026-11-09 20:06:07 end=2026-11-09 20:07:35 elapsed=88s bound=1200s status=FAIL rc=1 | 3 failed, 2099 passed, 14 warnings in 86.65s (0:01:26)
[pyt] tag=g10adv-comm-c1 start=2026-11-09 20:09:12 end=2026-11-09 20:10:13 elapsed=61s bound=1200s status=OK rc=0 | 308 passed, 9 deselected, 13 warnings in 60.01s (0:01:00)
[pyt] tag=g10adv-comm-c2 start=2026-11-09 20:10:17 end=2026-11-09 20:10:55 elapsed=38s bound=1200s status=OK rc=0 | 1272 passed, 11 warnings in 36.16s | [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=g10adv-comm-c3 start=2026-11-09 20:10:59 end=2026-11-09 20:11:58 elapsed=58s bound=1200s status=FAIL rc=1 | 9 failed, 1444 passed, 43 warnings in 55.88s | [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=g10adv-comm-c4 start=2026-11-09 20:14:56 end=2026-11-09 20:16:21 elapsed=85s bound=1200s status=OK rc=0 | 741 passed, 3 deselected, 35 xfailed, 13 warnings in 84.04s (0:01:24)
```
- netguard / hermeticity: red-off and red-on blocked 0 (75 checked each); ciorder blocked 189 attempt(s) from 18 node(s) (the s20 neutralized supabase.invalid sentinel nodes, base behaviour), 2102 checked; c1 blocked 53 from 23 node(s), 308 checked; c2 blocked 0, 1272 checked; c3 blocked 0, 1453 checked; c4 blocked 68 from 24 node(s), 776 checked.
- red-off = no flag set; red-on = ENABLE_SELF_CRITIQUE, ENABLE_KB_FIRST_SERVE, ENABLE_COMPARE_RUN_LEDGER, ENABLE_BATCH_JUDGE, ENABLE_LLM_SPEND_BREAKER = true in that one runner call only.
- CI-order set (spec 12.3, 33 files, GREEN's list): 3 failed / 2099 passed = exactly GREEN's result; the 3 FAILED ids are base-record CRLF-environment nodes.
- Comm chunks of my choice (all members of the HEAD set 3fa62c6b..., none in the CI-order set): c1 = SSE / stream / deadline / history / share / referral-share privacy / security regression / camera + the two CLAUDE.md readers (15 files); c2 = the legal manifest readers + the source-scanning pins + the verdict-prompt suites (22 files); c3 = offloop / shutdown drain / S81-24 throttle / KB / learning / coverage (20 files); c4 = the remaining CLAUDE.md readers + tests/test_secret_scan_static.py (18 files).
- comm -13 of (CI-order + c1..c4 FAILED ids, 12 unique) against the STORED base record harness/base_records/90d4ed74.../1f35353b....txt (27 ids): EMPTY. Every HEAD failure is a base-record environmental id (the CRLF hygiene nodes of s16 / s18b / s19 / s22 / s24 / d17).
- Corpus gate, ALONE (no pytest live), the eight-flag list, cwd = the scratch tree at aed1393b: start 2026-11-09 20:18:43, end 20:25:20, rc=0; RECORDS n=414 skipped_no_html=6 distinct_queries=362 non_none=829 calls=1656; OVERALL SHA256 387fa35c600f6ea9f049d38a84966f435b9827ed2ed636c0144b7b56f1d09181 = EQUAL to the base value (outputs corpus_head.json / corpus_stdout.txt in the notes folder).

## 4. Mutants (byte copy, one exact-string edit matching once, the killing rows via pyt.py -k / file, restore, sha256 compare; a .qa-mutation.lock held for the run; every restore sha-equal; tools/mutants.py + mutants2.py)
22 of the 30 spec mutants re-applied (20 KILLED by AssertionError rows, the 2 ruled equivalents survive as ruled) + 8 own mutants (all KILLED) + 3 floor measurements.

| id | edit | result | killing rows |
|---|---|---|---|
| J-M1 | operand back to the list | KILLED 6 | J1 r1-r6 |
| J-M2 | json.dumps(["batch_lost"]) | KILLED 8 | r1-r6, p2 x2 |
| J-M3 | .filter("flags","cs","{batch_pending}") | KILLED 7 | r1-r6, p3 |
| J-M4 | drop .eq("judge","haiku") | KILLED 3 | r1, p2 x2 |
| J-M5 | EJ1 reverted (fake iterates the str) | KILLED 5 | s22_judge j14c x3 (StopIteration), jf1_3a, j01 (j01 is also a base env id) |
| J-M6 | compact separators | SURVIVED = EQUIVALENT (identical bytes; L-J1-4) | - |
| B-M5 | preflight critic leg restored on os.getenv | KILLED 1 | 22b r6 |
| B-M6 | processors.json line restored | KILLED 1 | 22b r7 |
| B-M7 | Claude critic default over-deleted | KILLED 1 | 22b p2 |
| B-M10 | metadata._verdict_critique = {} when the name is true | KILLED 3 | 22b r8, r9, r9b |
| C-M1 | stamp dropped | KILLED 5 | 22c r1-r4, r7 |
| C-M2 | stamp also when both null | KILLED 2 | 22c p2 x2 |
| C-M3 | a miss view pid accepted | KILLED 1 | 22c r3 |
| C-M5 | build_run_row keeps None | KILLED 2 | 22c r5, r7 |
| C-M6 | K1 widening reverted | KILLED 2 | 22c r6, r7 |
| C-M7 | any str mark accepted | KILLED 1 | 22c r6 |
| C-M8 | stamp outside if kb_marks (any() kept) | SURVIVED = EQUIVALENT (views and marks set together; L-22c-5) | - |
| D-M1 | no attach | KILLED 4 | 04d r1-r4 |
| D-M2 | twin without the cancelled guard | KILLED 2 | 04d r4, p2 |
| D-M3 | attach only when not durable | KILLED 5 | 04d r1-r4, p4 |
| D-M4 | the callback logs a WARNING | KILLED 2 | 04d r3, r4 |
| D-M5 | attach on both branches | KILLED 2 | 04d r4, p4 (GC-3 record confirmed) |
| A-M1 (own) | _kb_product_ids returns [None, None] instead of NULL | KILLED 1 | 22c p3 |
| A-M2 (own) | partial views dropped from the stamp | KILLED 1 | 22c r3 |
| A-M3 (own) | the frozen synthetic "hit" mark dropped | KILLED 3 | 22c r6, s22_compare_runs r16 (+ b02 base env id) |
| A-M4 (own) | the KEPT moderation leg over-deleted from the preflight | KILLED 1 | s06 gate rows g05[cell0] |
| A-M5 (own) | persist_comparison hands a COPY to save_comparison | KILLED 7 | 22b r10, p1 x6 |
| A-M6 (own) | callback attached to the OUTER shield future | KILLED 4 | 04d r1-r4 (behavioural r1-r3, not only the AST row) |
| A-M7 (own) | 256-char element cap removed | KILLED 2 | 22c r5, p3 |
| A-M8 (own) | a partial view pid nulled | KILLED 1 | 22c r3 |
| F-EB11 | floor sites >= 16 at HEAD | FAIL "saw 15" | measured: exactly 15 routed sites |
| F-EB11b | floor spreads >= 32 at HEAD | FAIL "saw 31" | measured: exactly 31 spreads (15 + 15 + 1) |
| F-EB5 | floor len(sites) >= 16 at HEAD | FAIL "only 15" | measured: exactly 15 chat sites |

Mutant [pyt] lines:
```
[pyt] tag=g10adv-mut-j-m1 start=2026-11-09 20:01:28 end=2026-11-09 20:01:33 elapsed=6s bound=600s status=FAIL rc=1 | 6 failed, 16 passed, 11 warnings in 5.15s
[pyt] tag=g10adv-mut-j-m2 start=2026-11-09 20:01:34 end=2026-11-09 20:01:39 elapsed=6s bound=600s status=FAIL rc=1 | 8 failed, 14 passed, 11 warnings in 5.10s
[pyt] tag=g10adv-mut-j-m3 start=2026-11-09 20:01:39 end=2026-11-09 20:01:45 elapsed=6s bound=600s status=FAIL rc=1 | 7 failed, 15 passed, 11 warnings in 5.09s
[pyt] tag=g10adv-mut-j-m4 start=2026-11-09 20:01:45 end=2026-11-09 20:01:51 elapsed=6s bound=600s status=FAIL rc=1 | 3 failed, 19 passed, 11 warnings in 5.06s
[pyt] tag=g10adv-mut-j-m5 start=2026-11-09 20:01:51 end=2026-11-09 20:01:58 elapsed=7s bound=600s status=FAIL rc=1 | 5 failed, 53 passed, 11 warnings in 5.92s
[pyt] tag=g10adv-mut-b-m5 start=2026-11-09 20:01:58 end=2026-11-09 20:02:02 elapsed=4s bound=600s status=FAIL rc=1 | 1 failed, 18 deselected, 11 warnings in 3.31s
[pyt] tag=g10adv-mut-b-m6 start=2026-11-09 20:02:02 end=2026-11-09 20:02:06 elapsed=4s bound=600s status=FAIL rc=1 | 1 failed, 18 deselected, 11 warnings in 3.27s
[pyt] tag=g10adv-mut-b-m7 start=2026-11-09 20:02:06 end=2026-11-09 20:02:10 elapsed=4s bound=600s status=FAIL rc=1 | 1 failed, 18 deselected, 11 warnings in 3.27s
[pyt] tag=g10adv-mut-b-m10 start=2026-11-09 20:02:10 end=2026-11-09 20:02:15 elapsed=4s bound=600s status=FAIL rc=1 | 3 failed, 16 deselected, 10 warnings in 3.44s
[pyt] tag=g10adv-mut-c-m1 start=2026-11-09 20:02:29 end=2026-11-09 20:02:34 elapsed=5s bound=600s status=FAIL rc=1 | 5 failed, 19 passed, 10 warnings in 4.49s
[pyt] tag=g10adv-mut-c-m2 start=2026-11-09 20:02:34 end=2026-11-09 20:02:39 elapsed=5s bound=600s status=FAIL rc=1 | 2 failed, 22 passed, 10 warnings in 4.47s
[pyt] tag=g10adv-mut-c-m3 start=2026-11-09 20:02:39 end=2026-11-09 20:02:45 elapsed=5s bound=600s status=FAIL rc=1 | 1 failed, 23 passed, 10 warnings in 4.44s
[pyt] tag=g10adv-mut-c-m5 start=2026-11-09 20:02:45 end=2026-11-09 20:02:50 elapsed=5s bound=600s status=FAIL rc=1 | 2 failed, 22 passed, 10 warnings in 4.37s
[pyt] tag=g10adv-mut-c-m6 start=2026-11-09 20:02:50 end=2026-11-09 20:02:55 elapsed=5s bound=600s status=FAIL rc=1 | 2 failed, 22 passed, 10 warnings in 4.41s
[pyt] tag=g10adv-mut-c-m7 start=2026-11-09 20:02:55 end=2026-11-09 20:03:00 elapsed=5s bound=600s status=FAIL rc=1 | 1 failed, 23 passed, 10 warnings in 4.37s
[pyt] tag=g10adv-mut-a-m1 start=2026-11-09 20:03:00 end=2026-11-09 20:03:05 elapsed=5s bound=600s status=FAIL rc=1 | 1 failed, 23 passed, 10 warnings in 4.41s
[pyt] tag=g10adv-mut-a-m2 start=2026-11-09 20:03:06 end=2026-11-09 20:03:11 elapsed=5s bound=600s status=FAIL rc=1 | 1 failed, 23 passed, 10 warnings in 4.38s
[pyt] tag=g10adv-mut-a-m3 start=2026-11-09 20:03:11 end=2026-11-09 20:03:19 elapsed=9s bound=600s status=FAIL rc=1 | 3 failed, 161 passed, 10 warnings in 7.87s
[pyt] tag=g10adv-mut-a-m7 start=2026-11-09 20:03:19 end=2026-11-09 20:03:25 elapsed=5s bound=600s status=FAIL rc=1 | 2 failed, 22 passed, 10 warnings in 4.45s
[pyt] tag=g10adv-mut-a-m8 start=2026-11-09 20:03:25 end=2026-11-09 20:03:30 elapsed=5s bound=600s status=FAIL rc=1 | 1 failed, 23 passed, 10 warnings in 4.37s
[pyt] tag=g10adv-mut-d-m1 start=2026-11-09 20:03:35 end=2026-11-09 20:03:44 elapsed=9s bound=600s status=FAIL rc=1 | 4 failed, 6 passed, 10 warnings in 7.90s
[pyt] tag=g10adv-mut-d-m2 start=2026-11-09 20:03:44 end=2026-11-09 20:03:53 elapsed=9s bound=600s status=FAIL rc=1 | 2 failed, 8 passed, 10 warnings in 7.90s
[pyt] tag=g10adv-mut-d-m3 start=2026-11-09 20:03:53 end=2026-11-09 20:04:01 elapsed=9s bound=600s status=FAIL rc=1 | 5 failed, 5 passed, 10 warnings in 7.92s
[pyt] tag=g10adv-mut-d-m4 start=2026-11-09 20:04:02 end=2026-11-09 20:04:10 elapsed=9s bound=600s status=FAIL rc=1 | 2 failed, 8 passed, 10 warnings in 7.90s
[pyt] tag=g10adv-mut-a-m4 start=2026-11-09 20:04:10 end=2026-11-09 20:04:14 elapsed=4s bound=600s status=FAIL rc=1 | 1 failed, 6 passed, 74 deselected, 11 warnings in 3.48s
[pyt] tag=g10adv-mut-a-m5 start=2026-11-09 20:04:15 end=2026-11-09 20:04:19 elapsed=4s bound=600s status=FAIL rc=1 | 7 failed, 12 deselected, 10 warnings in 3.57s
[pyt] tag=g10adv-mut-a-m6 start=2026-11-09 20:04:19 end=2026-11-09 20:04:28 elapsed=9s bound=600s status=FAIL rc=1 | 4 failed, 6 passed, 10 warnings in 7.90s
[pyt] tag=g10adv-mut-f-eb11 start=2026-11-09 20:04:28 end=2026-11-09 20:04:31 elapsed=4s bound=600s status=FAIL rc=1 | 1 failed, 30 deselected, 1 warning in 3.07s
[pyt] tag=g10adv-mut-f-eb11b start=2026-11-09 20:04:31 end=2026-11-09 20:04:35 elapsed=4s bound=600s status=FAIL rc=1 | 1 failed, 30 deselected, 1 warning in 3.06s
[pyt] tag=g10adv-mut-f-eb5 start=2026-11-09 20:04:35 end=2026-11-09 20:04:39 elapsed=4s bound=600s status=FAIL rc=1 | 1 failed, 24 deselected, 1 warning in 3.29s
[pyt] tag=g10adv-mut-d-m5 start=2026-11-09 20:26:41 end=2026-11-09 20:26:50 elapsed=8s bound=600s status=FAIL rc=1 | 2 failed, 8 passed, 10 warnings in 7.78s
[pyt] tag=g10adv-mut-j-m6 start=2026-11-09 20:26:50 end=2026-11-09 20:26:55 elapsed=5s bound=600s status=OK rc=0 | 22 passed, 11 warnings in 4.44s
[pyt] tag=g10adv-mut-c-m8 start=2026-11-09 20:26:55 end=2026-11-09 20:27:00 elapsed=4s bound=600s status=OK rc=0 | 24 passed, 10 warnings in 3.76s
```

## 5. Runtime truth per unit (measured, or read at the HEAD bytes)
- D-S22-J1: 048 declares compare_judgements.flags jsonb NOT NULL DEFAULT [] CHECK jsonb_typeof = array (P4 pins it). Measured on the pinned postgrest 2.31.0 with an httpx MockTransport (no network): the HEAD chain renders select=run_id,batch_id,model,flags and judge=eq.haiku and flags=cs.["batch_pending"]; the base list form renders flags=cs.{batch_pending} (the PostgreSQL array literal). The one .contains( site in app/ and scripts/ (git grep; P3 pins it). json is imported at module top. DRY / apply resume end to end: J1 r3-r6 green, every other judge request P2-pinned (J-M2 / J-M4 kill it).
- S81-22b: app/ scripts/ data/ railway configs carry no retired identifier (R2); remaining "critique" words are comments (text_routes :857, extraction_service :2495, scs :1716 / :1727 / :4984) and the kept table name. llm_router: the ONLY hunk is _self_critique_on + the preflight leg + its docstring clause; ROLE_FLAGS / _ENTRY_ROLES / SITES[critique] / the consent gates / ENABLE_ANTHROPIC_CRITIC untouched by the diff (P2 green; A-M4 shows the kept moderation leg is still guarded). model_config: resolved_models() = moderation / standard / verdict / vision (measured); its only consumer is the startup [models] log line (app/main.py :52-54); anthropic_model("critic") stays claude-haiku-5-5 (the judge selector, cron_compare_judge :834). Flag-OFF identity of the deletions, re-derived: with the name unset, base _apply_self_critique returned the same object before any await, so dropping the sync call and the stream wait_for(_critique_coro, _tail_residual()) block cannot move an SSE event: _tail_residual floors at 0.05 s (scs :5000-5003) and the coroutine completed without a suspension, so no deadline PARTIAL could fire there at base. R8 / R9 / R9b / P1 (the base golden, REST + SSE both deadline states + persisted payload + follow-ups + compare_runs row) green at HEAD with the name unset and with it true (red-on run); zero critique dispatch (the route recorder; non-vacuous: R8-R9b were red at base by GC-2). Ledger: ENABLE_SELF_CRITIQUE UNSET on web (2026-11-06 / 2026-11-07 06:24 reads), so no stored or cached body carries _verdict_critique and dropping _without_verdict_critique is identity for production (base already passed the same object when the key was absent).
- S81-22c: the stamp sits inside if kb_marks after the kb_hit stamp; an id only for a dict view with hit full / partial and a non-empty str pid; absent when every element is null (P2 both-miss, C-M2). _kb_views and _kb_hit_marks are set together under the flag (C-M8 equivalent, confirmed SURVIVED). compare_runs: meta = _dict(body.metadata); _kb_product_ids keeps a str of 1..256 per element, NULL when no element survives (A-M1 / A-M7 killed); no kb_service / kb_serve import (P4). D-S22-K1: no reader of sources_used.kb_hit exists in app/ scripts/ migrations/ (git grep), so the widening changes only the stored marks. kb_products.id is minted by kb_service.kb_product_id from the catalogue card (not from user text).
- S81-04d: the twin equals redis_offloop._retrieve_quietly (R4 AST); attached inside if durable before asyncio.shield; the late-record INFO / fail-open accounting live in _record_finished / _record_gave_up (the job side), untouched; no logger call added (diff). Cancelled inner (P2), exception after the bound (R1), awaiter cancelled (R2), record_soon late EVAL failure (R3), late success landing once (P1), in-bound failure propagation both branches (P3), plain path unchanged (P4): green; the W1-6 drain (test_shutdown_drain.py, c3) and test_s77_redis_offloop.py (c3), test_s81_s04_spend_breaker.py (CI-order) green.

## 6. The R-G10-14 folded checks
- (a) data and privacy: metadata.kb_product_ids rides full_response into the comparisons row; history returns it; the PUBLIC share strips only metadata.openai / metadata.llm (share_routes.py :65-79, a denylist), so the ids reach the public share like kb_hit (L-22c-1; catalogue ids). compare_runs: RUN_COLUMNS unchanged (kb_product_ids was already a column, 048 :130 jsonb array CHECK); the row already carries product identity text in evidence (spec 22c 1.8), so no new data category. Client: no SmartCompareApp src / __tests__ file reads kb_hit / kb_product / the edited backend files (git grep).
- (b) asyncio: section 5 (S81-04d); no new log line; drain and durable landing green.
- (c) legal manifest: app/legal/processors.json has NO app/ or scripts/ reader (git grep: only a comment in llm_router); its readers are the seven test files, all green at HEAD (legal_docs_u8 / legal_s78 / s06 router in CI-order; legal_disclosure_s77 / legal_docs_u8_polish / s79_b3b in c2; 22b r7). No app/legal/*.md, landing or privacy text in the diff.
- (d) consent-gate KEEP rows: byte-identical by the diff (one router hunk only); P2 green; B-M7 / A-M4 killed.
- (e) E-row legitimacy: each census floor change equals exactly the one deleted dispatch site, measured at HEAD (15 sites, 31 spreads, 15 chat sites; G13 is an exact frozenset of 15 keys, 16 at base). Every dropped assertion guarded deleted code only: test_33 / R2.6 / TestCritiqueHedgingExemption / MINOR 6 / the critique SHIPPED rows / R14 critique case / the three critic config rows. G05 cell 4 True -> False is the retirement itself (the critic no longer calls OpenAI). EB12b replaces the keeps-_verdict_critique assert with row metadata == response metadata (stronger). EC1 / EC2 set the key aside AND assert its value (no blind pop). EJ1 keeps the list form and decodes a JSON str (the real operand is pinned by J1 r1 / r2). The importers of every edited test module are comm members (test_openai_breaker: 4 importers; d22: d22d + g5 rows; s06 router: gate rows; s18b: g8 rows; s22_judge: s22 gate rows).
- (f) corpus gate EQUAL 387fa35c... (section 3); the save-path / SSE identity rows green with the name unset and true.

## 7. CLAUDE.md row and PR body vs the bytes
- The G10 block (:630-635) matches the code: postgrest 2.31.0 pinned in requirements.txt; cs.["batch_pending"] measured; the 2026-11-07 DRY 400 is the ledger D-S22-J1 line; the [models] line loses critic (measured); 15 chat sites (8 + 5 + 1 + 1) measured; the 1..256 element rule = compare_runs; the twin / attach point = R4. The :341 pointer sentence and the ENABLE_SELF_CRITIQUE retirement are in place. The 12.6 first-OTA rows were rewritten with the ruled values (2026-11-07 16:10 AST, 08de6433-3883-4c4d-bada-fb450ba29100, runtime 1.0.0, f1e20c39 = ledger lines 394 / 395).
- PR body: 19,673 B (python), 4 bytes > 127 (the robot line), CR 0; the ruled sentence, the S81-04b -> S81-04d note, S81-22e / 22f / 22h / 22i, names-only owner steps, L-J1-1..4 / L-22b-1..6 / L-22c-1..5 / L-04d-1..2, 75 nodes (22 + 19 + 24 + 10 = 6/16, 10/9, 7/17, 4/6 measured), 30 mutants with J-M6 / C-M8 equivalent, comm 729 / EMPTY, corpus EQUAL, fences; every E-row blob prefix equals the measured blob.

## 8. Findings
BLOCKING: none. MAJOR: none.

MINOR (documentation rulings for the orchestrator; LC-4: a stated limit by default):
- m1 (CLAUDE.md, principle 5): sentences that still describe the self-critique as live sit OUTSIDE the spec's 22b list, so R-G10-11 kept GREEN off them and both versions now load next to the G10 block's "inert retired name": HEAD :778 (the W4-11 activation note: with ENABLE_SELF_CRITIQUE ON the critic's balanced axis may regenerate an honest empty-cons verdict - false since S81-22b); HEAD :573 (the D22 row: verdict_unsupported "only while ENABLE_SELF_CRITIQUE has run" - no writer remains); HEAD :609 (the S81-22 owner step (6) "read ENABLE_SELF_CRITIQUE by name (S81-22b)" - answered 2026-11-06, moot; GREEN Q-G1); HEAD :780 ("all LLM call sites (16 since the S81-06 census ...)", "an AST pin over >= 16 sites since S81-06" - 15 sites and >= 15 since S81-22b, measured; GREEN Q-G1b). Suggest: the final round rewrites the four in place, dated.
- m2 (CLAUDE.md, R-A15): first-OTA lags outside the 12.6 list remain: HEAD :195 (api.ts: S81-08 "reaches phones only with the first post-approval OTA"); HEAD :341, the S81-11 clause on the very line GREEN edited ("it ships in the first post-approval OTA"); HEAD :528, the S81-08 owner step (3) "publish the first post-approval OTA only after LEGAL-V3 is live", which now CONTRADICTS the rewritten :522 of the same block ("SHIPPED ... BEFORE LEGAL-V3"). GREEN raised :195 / :528 (Q-G1); the :341 clause is new here. Suggest: the same final-round in-place rewrite.
- m3 (code comments only, no runtime): app/api/text_routes.py :857-858 still lists "the four follow-ups (savings-cache bust, cohort event, critique persist, referral Loop 2)" beside the track_after_persist call (three since S81-22b); app/services/extraction_service.py :2495-2496 still says "all three generate_comparison call sites (sync / stream / self-critique regen)" (two remain); scs :1716 / :1727 / :4984 kept deliberately (D-G5). Outside the GC-5 footprint; a stated limit or a later comment sweep.
- m4 (22c stated-limit wording): compare_runs._kb_product_ids nulls an element longer than 256 characters, but a valid KB id may be 14..512 (045 :136 CHECK; kb_service :540 _str_len(id, 14, 512)); measured: a 300-character id -> NULL in the run row while the response key carries it. Realistic juice ids are far shorter; L-22c-1..5 do not state it. Suggest L-22c-6 (or a later widening to 512).
- m5 (PR body form): the E-rows column carries 10-character blob prefixes (each checked equal) where GC-8 names "the base and new LF blob shas"; the full 40-character values are in the GREEN report section 3 (LC-3 offload). Rule acceptable or expand.
- m6 (cosmetic, GREEN Q-G2): three test names keep words the retirement made stale (..._all_four_follow_ups, ..._while_the_response_keeps_it, ..._covers_moderation_and_critic), kept for node-id stability; docstrings updated.

## 9. Prove-nothing rows (form pins; each is still killed by its mutant)
- Source / AST / file pins that prove shape, not runtime: 22b R1 / R3 / R4 / R5 / P3 (migration 030 and listing digests), 22c P4, 04d R4 / P5, J1 P3 / P4. Each is backed by a behavioural row (22b R6-R10 / P1, 22c R1-R7 / P1-P3 / P5, 04d R1-R3 / P1-P4, J1 R1-R6 / P1-P2).
- EB8 (d22 p5) now pins the job's own literal CRITIQUE_THRESHOLD == 7 and its CRITIQUE_COLUMNS names against 030: with the mirror module gone it proves a literal only.
- J1 (L-J1-1): the fake PostgREST cannot prove the live jsonb parse; the owner's DRY run is the live proof.

## 10. NOT MEASURED / not run (by rule or by choice)
- The fourteen backend-scanning client fences + b3a / nativeStrings: not re-run (GC-9 makes the adversary worktree junction-free); GREEN measured them; git grep shows no SmartCompareApp test reads a file this unit edits (CLAUDE.md only in comments).
- The full 729-member comm set: not re-run; the CI-order set + four chunks of my choice re-run (5,911 nodes: 2,102 + 308 + 1,272 + 1,453 + 776), comm -13 EMPTY.
- Full jest: not run (LC-7). The pre-commit hook files: not run (no .githooks change).

## 11. Questions for the orchestrator
- Q-A1: rule m1 + m2 as in-place CLAUDE.md rewrites in the final round (principle 5 / R-A15), or as stated limits.
- Q-A2: rule m4 as a stated limit L-22c-6.

Not done by this adversary: no edit in sc-s81-g10; no commit, push or PR; no network; no secret or .env read; no flag set outside one runner call.
