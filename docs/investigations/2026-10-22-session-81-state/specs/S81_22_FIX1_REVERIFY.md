# S81-22 FIX ROUND 1: RE-VERIFIER REPORT (correctness lens, Opus 5.5, 2026-11-06)

Verdict: **SOUND** (0 blocking, 0 major, 6 minor; the minors are stated limits per LC-4).

Unit S81-22 COMPARE-RUNS + capped judge, fix round 1 (RULINGS_FIX1_S81_22 F1-1..F1-8, section D). Worktree C:/Users/SynAckITPC/Documents/AI/sc-s81-s22, branch feature/s81-s22-compare-runs. HEAD verified c22ff9c03ccb39273c32bdb190f72607b6ad9fb5 (at the start and at the end; git status --short empty; the worktree was never edited). Probes and mutants ran in my own detached scratch worktree <scratchpad>/S81-22_fix1_adv at c22ff9c0, checked out with `-c core.autocrlf=false` so the working bytes equal the blobs (a default checkout on this box makes the LF blobs CRLF and turns test_j01 / test_b02 red: correctness m8, reproduced, environmental). The scratch worktree was removed at the end (no node_modules junction in it).

## 1. RED file hashes (blob == scratch disk == fix report)

- tests/test_s81_s22_judge.py b7c2c377e4c6b8c5b0db77dc16a746963b16f6f765910275c60df436577d8430 EQUAL
- tests/test_s81_s22_compare_runs.py db13c005e04f3e9986190a538f6baa77ddaa587178ab1677f8399360922000eb EQUAL
- tests/test_s81_s22_gate_rows.py 6ad6b7eac8a7aa35c54d4586428b685f7a623d95711e696afe2e0b661b4c6d06 EQUAL
- scripts/cron_compare_judge.py 0c2bf368... and app/services/compare_runs.py 0605ee62... = the fix report's shas.
- Frozen-row diff 0d588d0b..c22ff9c0 (`git diff -U0`): exactly the 7 hunks the fix report lists (J09 :626-627 / :636-637, J11 :667-668, J14 :739, J14c :782-783, J15 :854, J15b :866) plus the appended FIX ROUND 1 section; test_s81_s22_compare_runs.py: only the appended R-F1-4; gate rows: only GR4 / GR5 appended. D1 (J11 / J14 / J15 / J15b) reviewed: each is the minimal form forced by F1-3 (J11 gains the one marker upsert step; the three reads drop rows whose flags are exactly ["batch_pending"]); none weakens a frozen assertion about a filled row. I recommend the orchestrator accept D1 (fix report Q2).
- Node counts (collect): judge 58 + compare_runs 140 = 198 (CLAUDE.md "198 nodes" correct); gate rows 11.

## 2. Unit ON / OFF (bounded runner; the pinned venv runs are the record, the global-python runs below them agree)

- [pyt] tag=s22rv-venv-off (venv, flags unset, + my 5 probes) start=2026-11-06 20:05:43 end=2026-11-06 20:05:55 elapsed=12s bound=600s status=OK rc=0 ; 214 passed ; [hermeticity] sentinel checked 214 test(s) ; [netguard] blocked 0 attempt(s) from 0 node(s)
- [pyt] tag=s22rv-venv-on (venv, ENABLE_COMPARE_RUN_LEDGER=true ENABLE_BATCH_JUDGE=apply in the runner env only, + probes) start=2026-11-06 20:05:55 end=2026-11-06 20:06:11 elapsed=16s bound=600s status=OK rc=0 ; 214 passed ; [hermeticity] 214 ; [netguard] blocked 0

- [pyt] tag=s22rv-off2 start=2026-11-06 19:32:07 end=2026-11-06 19:32:18 elapsed=11s bound=600s status=OK rc=0 ; 209 passed
- [pyt] tag=s22rv-on (ENABLE_COMPARE_RUN_LEDGER=true ENABLE_BATCH_JUDGE=apply, runner env only) start=2026-11-06 19:32:18 end=2026-11-06 19:32:29 elapsed=11s bound=600s status=OK rc=0 ; 209 passed ; [hermeticity] sentinel checked 209 test(s) ; [netguard] blocked 0 attempt(s) from 0 node(s)
- (first attempt on the CRLF default checkout: [pyt] tag=s22rv-off start=2026-11-06 19:31:32 end=2026-11-06 19:31:43 elapsed=12s bound=600s status=FAIL rc=1 ; 2 failed (test_j01, test_b02: CR bytes in railway.judge.json / 048 working copies; m8), 207 passed. Re-checked out LF and re-run above.)

## 3. Probes (tests/test_zz_s22rv_probe.py in the scratch worktree only; copy kept at S81-22_fix1_adv_logs/test_zz_s22rv_probe.py.txt)

- [pyt] tag=s22rv-probe3 start=2026-11-06 19:34:25 end=2026-11-06 19:34:28 elapsed=4s bound=600s status=OK rc=0 ; 5 passed
- P1 (ruling D: two consecutive FakeClient runs with a missing marker row): run 1, three runs, WRITE_BATCH=1, the 2nd marker chunk fails, the batch times out: markers_written 2, markers_failed 1, pending 1, cancelled 0, no ledger, no delete. Run 2 (old batch ended, new batch id): resume.batches 1, filled 2, unmatched 1; each marked run carries the note of ITS OWN hashed id (no shift) and batch_id msgbatch_one; the marked runs are NOT re-submitted; the unmarked run alone is re-batched in msgbatch_two and filled from it; ledger rows = [msgbatch_one, msgbatch_two], both batches deleted. Run 3: no create, no ledger, resume.batches 0. PASS.
- P1b: the marker of the FIRST sorted run (the positional worst case) deleted between runs: the other two runs get their own answers; no re-submission. PASS.
- P2 (measurement, privacy m2's q3b arm): the batch ends within the wait, the ledger row is written, the FINAL upsert fails: the markers stay batch_pending, the batch is not deleted; the next run resumes it with NO re-submission (one create in total) but writes a SECOND llm_spend_ledger row for the same provider_batch_id (and records the actual again on the offclock lane). Double billing is closed; a double ledger record remains (minor m3 below).
- P4: field_status serialized exactly 16,384 bytes is kept; 16,385 -> {"truncated": true}; non-ASCII expands under ensure_ascii and truncates; a non-list -> None. PASS.
- P5: an escalation end to end: model claude-sonnet-5-5, thinking {"type": "between_tools"}, no temperature, output_config json_schema, max_tokens 400; the escalation ledger row on the Sonnet model; 12 flags cut to 8, escalation.answer_capped 1; no run id in any batch body. PASS.

## 4. Mutants (byte copies of the two code files, one at a time, killing rows = the three S22 files, restored + sha-verified after each; 17 / 19 KILLED by AssertionError only, nonassert_E 0; 2 survivors = prove-nothing minors)

- rv01 escalation router form dropped | KILLED (jf1_1) | [pyt] tag=s22rv-rv01 start=2026-11-06 19:35:02 end=2026-11-06 19:35:14 elapsed=12s bound=600s status=FAIL rc=1
- rv02 escalation model swap only, thinking disabled | KILLED (jf1_1) | [pyt] tag=s22rv-rv02 start=2026-11-06 19:35:14 end=2026-11-06 19:35:25 elapsed=12s bound=600s status=FAIL rc=1
- rv03 temperature re-added after the router form | KILLED (jf1_1) | [pyt] tag=s22rv-rv03 start=2026-11-06 19:35:25 end=2026-11-06 19:35:37 elapsed=12s bound=600s status=FAIL rc=1
- rv04 batch temperature 0 restored | KILLED (j09, jf1_1, jf1_2) | [pyt] tag=s22rv-rv04 start=2026-11-06 19:35:37 end=2026-11-06 19:35:49 elapsed=12s bound=600s status=FAIL rc=1
- rv05 schema flag-item pattern restored | KILLED (jf1_2) | [pyt] tag=s22rv-rv05 start=2026-11-06 19:35:49 end=2026-11-06 19:36:00 elapsed=12s bound=600s status=FAIL rc=1
- rv06 schema note maxLength restored | KILLED (jf1_2) | [pyt] tag=s22rv-rv06 start=2026-11-06 19:36:00 end=2026-11-06 19:36:12 elapsed=12s bound=600s status=FAIL rc=1
- rv07 note not cut in code | KILLED (j15b, jf1_2) | [pyt] tag=s22rv-rv07 start=2026-11-06 19:36:12 end=2026-11-06 19:36:24 elapsed=12s bound=600s status=FAIL rc=1
- rv08 > 8 flags rejected (old rule) instead of cut | KILLED (jf1_2) | [pyt] tag=s22rv-rv08 start=2026-11-06 19:36:24 end=2026-11-06 19:36:35 elapsed=12s bound=600s status=FAIL rc=1
- rv09 custom id 12 hex | KILLED (gr4, j09, j14c[ended], jf1_2, jf1_3a) | [pyt] tag=s22rv-rv09 start=2026-11-06 19:36:35 end=2026-11-06 19:36:47 elapsed=12s bound=600s status=FAIL rc=1
- rv10 resume by_cid by position over the pending group | KILLED (gr4, j14c[ended], jf1_3a) | [pyt] tag=s22rv-rv10 start=2026-11-06 19:36:47 end=2026-11-06 19:36:59 elapsed=11s bound=600s status=FAIL rc=1
- rv11 resume orphan counted under batch | KILLED (jf1_3a) | [pyt] tag=s22rv-rv11 start=2026-11-06 19:36:59 end=2026-11-06 19:37:10 elapsed=12s bound=600s status=FAIL rc=1
- rv12 markers only on the timeout path (old timing) | KILLED (j11, j14b, jf1_3b, jf1_3c) | [pyt] tag=s22rv-rv12 start=2026-11-06 19:37:10 end=2026-11-06 19:37:22 elapsed=12s bound=600s status=FAIL rc=1
- rv13 cancel on a partial marker failure | KILLED (jf1_3c) | [pyt] tag=s22rv-rv13 start=2026-11-06 19:37:22 end=2026-11-06 19:37:34 elapsed=12s bound=600s status=FAIL rc=1
- rv14 cancel arm does not settle the reservation | KILLED (jf1_3c) | [pyt] tag=s22rv-rv14 start=2026-11-06 19:37:34 end=2026-11-06 19:37:46 elapsed=12s bound=600s status=FAIL rc=1
- rv15 cancel arm polls on (no early return) | KILLED (jf1_3c) | [pyt] tag=s22rv-rv15 start=2026-11-06 19:37:46 end=2026-11-06 19:37:57 elapsed=12s bound=600s status=FAIL rc=1
- rv16 field_status cap raised to 1 MB | KILLED (rf1_4) | [pyt] tag=s22rv-rv16 start=2026-11-06 19:37:57 end=2026-11-06 19:38:09 elapsed=12s bound=600s status=FAIL rc=1
- rv17 field_status boundary `>=` | SURVIVED | [pyt] tag=s22rv-rv17 start=2026-11-06 19:38:09 end=2026-11-06 19:38:19 elapsed=10s bound=600s status=OK rc=0 (minor m1; my P4 kills it)
- rv18 escalation.answer_capped counter dropped | SURVIVED | [pyt] tag=s22rv-rv18 start=2026-11-06 19:38:19 end=2026-11-06 19:38:29 elapsed=10s bound=600s status=OK rc=0 (minor m2; my P5 kills it)
- rv19 marker chunk failure not counted | KILLED (jf1_3c) | [pyt] tag=s22rv-rv19 start=2026-11-06 19:38:29 end=2026-11-06 19:38:41 elapsed=12s bound=600s status=FAIL rc=1
- Both code files sha-verified equal to the fix shas after the last restore.

## 5. Comm chunks (the fix agent's 54-file set, its 3 chunks, venv python, flags unset) and the CI-order set

- [pyt] tag=s22rv-comm2-c00 start=2026-11-06 19:39:39 end=2026-11-06 19:42:00 elapsed=141s bound=1200s status=FAIL rc=1 ; 1498 passed, 2 skipped, 4 deselected, 1 xfailed, 2 errors (the two cold-tiktoken test_prompt_truth ERRORs) ; [netguard] lines = the hermeticity pins' own probes + the neutralized supabase sentinel
- [pyt] tag=s22rv-comm2-c01 start=2026-11-06 19:42:00 end=2026-11-06 19:43:32 elapsed=92s bound=1200s status=OK rc=0 ; 3136 passed (the 6 CRLF-class base nodes pass in an LF checkout)
- [pyt] tag=s22rv-comm2-c02 start=2026-11-06 19:43:32 end=2026-11-06 19:43:45 elapsed=12s bound=1200s status=OK rc=0 ; 264 passed ; [hermeticity] sentinel checked 264 test(s) ; [netguard] blocked 0
- (a first launch, tags s22rv-comm-c00..c02, was a pytest USAGE error, rc=4 in 0 s: CR in my file list; not a result.)
- FAILED/ERROR at HEAD (2) vs the record's ids of the same files (8): comm -13 EMPTY; comm -23 = the 6 CRLF-class nodes (s10 r06, s16 r27 x5), absent here only because of the LF checkout (environmental).
- [pyt] tag=s22rv-ciorder start=2026-11-06 19:44:03 end=2026-11-06 19:44:57 elapsed=53s bound=1200s status=FAIL rc=1 ; 1769 passed, 2 skipped, 1 xfailed, 2 errors (cold tiktoken) = the base noise (r06 passes in LF).

## 6. Hook test files, ALONE (as the task directs; no .githooks change on the branch)

- [pyt] tag=s22rv-hook-notdash start=2026-11-06 19:47:10 end=2026-11-06 19:51:52 elapsed=282s bound=1800s status=OK rc=0 ; 167 passed, 160 deselected ; [hermeticity] 167 ; [netguard] blocked 0
- [pyt] tag=s22rv-hook-dash start=2026-11-06 19:52:02 end=2026-11-06 19:59:40 elapsed=458s bound=1800s status=OK rc=0 ; 157 passed, 3 skipped, 167 deselected ; [hermeticity] 160 ; [netguard] blocked 0
- No TIMEOUT; nothing NOT MEASURED.

## 7. Code review of the fixes against the rulings

- F1-1: `_escalate` sets `req["params"] = lr._escalation_request(req["params"])` over the batch params: escalation model from model_config, thinking between_tools, the router's own function (D3, cannot drift), no temperature (the batch params carry none since F1-2); `_escalate` is called with the Sonnet model, so request_bound and anthropic_usage_record price the escalation model. CLOSED.
- F1-2: `build_request` = the seed_kb_batch.build_requests key set; JUDGE_SCHEMA without maxItems / maxLength / pattern; FLAGS_MAX 8 / NOTE_MAX 300 cut in `_valid_answer`, counted (batch.answer_capped, escalation.answer_capped); a flag off _FLAG_RX stays unparsed. CLOSED.
- F1-3: custom_id = "r" + sha256(str(run_id))[:16]; `_resume` recomputes over the pending group; an unknown id is counted (`<where>.unmatched`) and ignored; markers upserted right after create, before the poll; zero written -> batches.cancel + settle(None) + return before any poll; partial -> keep. CLOSED (P1 / P1b / rv09-rv15).
- F1-4: field_status cap at 16,384 serialized bytes; unserializable -> truncated; only inside build_run_row (flag ON). CLOSED.
- F1-5: G22-GR4 (kills O07 / rv10) and G22-GR5 (kills O09 per the fix report). CLOSED.
- F1-6: measured on a local PostgreSQL 18.1 cluster (S81-22_fix1/f16/f16_outputs.txt read: every step PASS, guard raises rc=3 '048 guard:' for both probes, hook / privileges / prune / rollback as stated; 0 FAIL lines). CLOSED as a measurement; G22-GR2 a text pin (stated).
- F1-7 / F1-8: see section 8.
- Lint: ruff E9/F63/F7/F82 on the 5 files "All checks passed!"; py_compile clean; the 5 files LF with 0 bytes > 127; added code / test lines carry no sk- / eyJ / AKIA / PEM / credentialed URL / 64-hex literal; the CLAUDE.md added lines are ASCII and the CLAUDE.md blob is LF (0 CR; the CRLF is the autocrlf working copy).

## 8. CLAUDE.md S81-22 block and the PR body, sentence by sentence against the bytes

CLAUDE.md (5 edited lines): header counts (198 nodes; G22-GR1..GR5) TRUE; ENABLE_COMPARE_RUN_LEDGER: the F1-4 cap sentence TRUE; "the URL exit computes its compare_ms arithmetic before the flag read" TRUE (url_routes.py:393-394); L-I2I6 + S81-22d TRUE. ENABLE_BATCH_JUDGE step (4): hashed id, the build_requests form, no temperature, the schema without the three keywords, caps in code + batch.answer_capped, markers before any poll + markers_written / markers_failed + ERROR line + the only cancel, timeout keeps the markers + 0.0 settle, recomputed resume + resume.unmatched: TRUE. Step (5): the router form, ONE escalation ledger row per cron run: TRUE (one ledger write per `_escalate` call, one call per main). Step (7) report key names TRUE (_new_report). L-VERDICT / L-POSTFLIP widened, L-API, the autocrlf note: TRUE. L-MARKER: TRUE except the wording nuance in m4. Migration bullet: matches f16_outputs.txt. Owner steps: JUDGE_ESCALATION_MAX_PER_DAY=0 is the off switch TRUE (int_knob low 0 admits 0); a 0 JUDGE_ESCALATION_MAX_USD maps to the default TRUE (float_knob <= 0 -> default); S81-22d before step 4 TRUE.

PR body (18,684 B <= 25,600; LF; the ONE non-ASCII line is the attribution line, line 77): every F1 sentence matches the bytes as above; the amended-row list matches the diff; "+6 RED rows ... 198 + 11 = 209" TRUE; the 10 RED-at-GREEN-HEAD nodes and the 14 / 14 mutants match the fix report; the CI-order line matches my re-run (1768 in the CRLF tree, 1769 here). One sentence is now stale: "The hook test files ... were NOT run" (true of the fix round; this re-verifier ran them alone, green: m5).

## 9. Previous-round findings: closed or recorded

Correctness adversary: MAJOR-1 CLOSED (F1-1; rv01-rv03; P5). MAJOR-2 CLOSED in the bytes (F1-2; rv04-rv08), live acceptance stated as L-API. MAJOR-3 CLOSED (F1-3; rv09-rv11; P1 / P1b). m1 CLOSED (G22-GR4). m2 CLOSED (F1-4; rv16; boundary unpinned = m1 here). m3 CLOSED (G22-GR5). m4 RECORDED (L-I2I6 + owner step 4). m5 RECORDED (key names supersede spec 2.12). m6 RECORDED (softened wording + the URL-exit sentence). m7 MEASURED (F1-6) + RECORDED (GR2 a text pin). m8 RECORDED (autocrlf note; reproduced here).
Privacy-and-spend adversary: m1 RECORDED (owner step, verified against kb_seed_common). m2 the double BILLING arms CLOSED (markers before the poll; a total marker failure cancels; P1 shows no re-submission of a marked run), the double LEDGER residue on a failed final upsert NOT stated (m3 here). m3 RECORDED (L-VERDICT). m4 RECORDED (L-POSTFLIP). m5 RECORDED (the attribution-line exception). m6 RECORDED ("per cron run").

## 10. Minors (stated limits; none production-visible beyond a conservative ledger over-count)

- m1 (prove-nothing): the field_status boundary (`>` vs `>=` at exactly 16,384 bytes) is unpinned (rv17 survives; P4 would pin it).
- m2 (prove-nothing): `escalation.answer_capped` is unpinned (rv18 survives; P5 would pin it).
- m3 (stated-limit gap): an ended batch whose final compare_judgements upsert fails keeps its markers and is not deleted; the next run's resume fills it without re-submission but writes a SECOND llm_spend_ledger row with the same provider_batch_id and records the actual on the offclock lane again (P2). Conservative over-count, no double billing; not named in L-MARKER (CLAUDE.md / PR body).
- m4 (wording): L-MARKER's "a failed marker chunk keeps the batch; its runs are re-batched next night" holds only when the batch does not end within the wait; when it ends, the unmarked runs are filled in the same run (P1 shows the re-batch on the timeout path).
- m5 (PR body): "The hook test files ... were NOT run" is stale after this re-verification (324 passed, 3 skipped, alone, section 6).
- m6 (process disclosure): the probe runs (s22rv-probe*) and the 19 mutant runs used the global Python 3.12 interpreter, not the pinned venv (the venv re-run of the three files + probes in both flag states is green, section 2; the comm chunks, the CI-order set and the hook files ran on the venv). To count nodes I ran `pytest --collect-only -q` on the three S22 files outside the bounded runner (collection only, no test executed, a few seconds); every test execution went through pyt.py.

## 11. Cleanup

The scratch worktree <scratchpad>/S81-22_fix1_adv removed with `git worktree remove --force` (no junction inside); logs, mutant snapshots, the probe file copy and rv_mut.py kept under <scratchpad>/S81-22_fix1_adv_logs/. The unit worktree: HEAD c22ff9c0, git status --short empty, never edited. No .env read, no flag in any .env or the OS environment, no network beyond the hermetic tests.
