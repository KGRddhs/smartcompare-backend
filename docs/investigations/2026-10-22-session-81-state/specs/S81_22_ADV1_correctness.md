# S81-22 ADVERSARY REPORT: lens correctness (Opus 5.5 = claude-opus-5-5, 2026-11-06)

Written through the shell (a python generator run from bash). Verdict: **NOT_READY** (0 blocking, 3 major, 8 minor).
HEAD verified 0d588d0b52a6532359a051d85ae89698e452cd63 on feature/s81-s22-compare-runs (real worktree untouched; status clean).
Frozen RED files re-hashed first and last: c1cb9375...2a52 / 39a46d1c...2199 (byte-identical).
Scratch worktree <scratchpad>/S81-22_adv_correctness at 0d588d0b (no junction); every one of the 15 changed files sha-matched to the GREEN table before any run (corr_hashes_start.txt == corr_hashes_end.txt); removed with git worktree remove --force (gone; `git worktree prune` run on the shared repo, metadata only).
Note: the box's core.autocrlf=true (system gitconfig) checks the new LF files out as CRLF; the GREEN on-disk state (CRLF existing files, LF new files) was reproduced by writing the committed blobs back. The blobs are LF; CI (Linux) is unaffected.

## 1. Runs ([pyt] lines; flags unset unless ON = ENABLE_COMPARE_RUN_LEDGER=true ENABLE_BATCH_JUDGE=apply in the runner env only; s22c-probes rc=2 was a collection error of the probe placed outside tests/, re-run as s22c-probes2)
- [pyt] tag=s22c-red-off start=2026-11-06 18:12:52 end=2026-11-06 18:13:03 elapsed=11s bound=600s status=OK rc=0
- [pyt] tag=s22c-red-on start=2026-11-06 18:13:03 end=2026-11-06 18:13:14 elapsed=11s bound=600s status=OK rc=0
- [pyt] tag=s22c-m01 start=2026-11-06 18:13:14 end=2026-11-06 18:13:27 elapsed=13s bound=600s status=FAIL rc=1
- [pyt] tag=s22c-m03 start=2026-11-06 18:13:28 end=2026-11-06 18:13:38 elapsed=11s bound=600s status=FAIL rc=1
- [pyt] tag=s22c-m05 start=2026-11-06 18:13:39 end=2026-11-06 18:13:50 elapsed=11s bound=600s status=FAIL rc=1
- [pyt] tag=s22c-m09 start=2026-11-06 18:13:50 end=2026-11-06 18:14:01 elapsed=11s bound=600s status=FAIL rc=1
- [pyt] tag=s22c-m11 start=2026-11-06 18:14:02 end=2026-11-06 18:14:13 elapsed=11s bound=600s status=FAIL rc=1
- [pyt] tag=s22c-m13 start=2026-11-06 18:14:13 end=2026-11-06 18:14:24 elapsed=11s bound=600s status=FAIL rc=1
- [pyt] tag=s22c-m16 start=2026-11-06 18:14:25 end=2026-11-06 18:14:36 elapsed=11s bound=600s status=FAIL rc=1
- [pyt] tag=s22c-m19 start=2026-11-06 18:14:36 end=2026-11-06 18:14:47 elapsed=11s bound=600s status=FAIL rc=1
- [pyt] tag=s22c-m26 start=2026-11-06 18:14:47 end=2026-11-06 18:14:59 elapsed=11s bound=600s status=FAIL rc=1
- [pyt] tag=s22c-m30 start=2026-11-06 18:14:59 end=2026-11-06 18:15:11 elapsed=12s bound=600s status=FAIL rc=1
- [pyt] tag=s22c-m33 start=2026-11-06 18:15:11 end=2026-11-06 18:15:23 elapsed=12s bound=600s status=FAIL rc=1
- [pyt] tag=s22c-m35 start=2026-11-06 18:15:23 end=2026-11-06 18:15:35 elapsed=12s bound=600s status=FAIL rc=1
- [pyt] tag=s22c-m37 start=2026-11-06 18:15:36 end=2026-11-06 18:15:47 elapsed=12s bound=600s status=FAIL rc=1
- [pyt] tag=s22c-m40 start=2026-11-06 18:15:48 end=2026-11-06 18:15:59 elapsed=11s bound=600s status=FAIL rc=1
- [pyt] tag=s22c-m45 start=2026-11-06 18:16:00 end=2026-11-06 18:16:12 elapsed=12s bound=600s status=FAIL rc=1
- [pyt] tag=s22c-m48 start=2026-11-06 18:16:12 end=2026-11-06 18:16:24 elapsed=12s bound=600s status=FAIL rc=1
- [pyt] tag=s22c-o01-resume-order start=2026-11-06 18:16:25 end=2026-11-06 18:16:36 elapsed=11s bound=600s status=OK rc=0
- [pyt] tag=s22c-o02-riyadh-sign start=2026-11-06 18:16:36 end=2026-11-06 18:16:49 elapsed=12s bound=600s status=FAIL rc=1
- [pyt] tag=s22c-o03-esc-params start=2026-11-06 18:16:49 end=2026-11-06 18:17:00 elapsed=11s bound=600s status=OK rc=0
- [pyt] tag=s22c-o04-recompare-self start=2026-11-06 18:17:00 end=2026-11-06 18:17:12 elapsed=12s bound=600s status=FAIL rc=1
- [pyt] tag=s22c-o05-personal-scoring start=2026-11-06 18:17:12 end=2026-11-06 18:17:23 elapsed=11s bound=600s status=FAIL rc=1
- [pyt] tag=s22c-o06-no-pending-marker start=2026-11-06 18:17:24 end=2026-11-06 18:17:35 elapsed=12s bound=600s status=FAIL rc=1
- [pyt] tag=s22c-o07-dry-resume-ledger start=2026-11-06 18:17:36 end=2026-11-06 18:17:47 elapsed=11s bound=600s status=OK rc=0
- [pyt] tag=s22c-o08-pepper-blank start=2026-11-06 18:17:47 end=2026-11-06 18:17:58 elapsed=11s bound=600s status=FAIL rc=1
- [pyt] tag=s22c-o09-sample-pct start=2026-11-06 18:17:59 end=2026-11-06 18:18:10 elapsed=11s bound=600s status=OK rc=0
- [pyt] tag=s22c-o10-fit-minimal start=2026-11-06 18:18:10 end=2026-11-06 18:18:22 elapsed=12s bound=600s status=FAIL rc=1
- [pyt] tag=s22c-probes start=2026-11-06 18:18:43 end=2026-11-06 18:18:47 elapsed=4s bound=600s status=FAIL rc=2
- [pyt] tag=s22c-s03-on start=2026-11-06 18:18:47 end=2026-11-06 18:19:00 elapsed=12s bound=600s status=FAIL rc=1
- [pyt] tag=s22c-pins-mig-off start=2026-11-06 18:19:00 end=2026-11-06 18:19:32 elapsed=32s bound=1200s status=OK rc=0
- [pyt] tag=s22c-pins-mig-on start=2026-11-06 18:19:32 end=2026-11-06 18:20:04 elapsed=32s bound=1200s status=OK rc=0
- [pyt] tag=s22c-pins-route-off start=2026-11-06 18:20:05 end=2026-11-06 18:21:03 elapsed=58s bound=1200s status=FAIL rc=1
- [pyt] tag=s22c-ciorder start=2026-11-06 18:21:03 end=2026-11-06 18:21:56 elapsed=52s bound=1200s status=FAIL rc=1
- [pyt] tag=s22c-comm-c01 start=2026-11-06 18:21:56 end=2026-11-06 18:22:24 elapsed=28s bound=1200s status=FAIL rc=1
- [pyt] tag=s22c-comm-c14 start=2026-11-06 18:22:25 end=2026-11-06 18:22:46 elapsed=21s bound=1200s status=FAIL rc=1
- [pyt] tag=s22c-comm-c20 start=2026-11-06 18:22:47 end=2026-11-06 18:23:49 elapsed=62s bound=1200s status=FAIL rc=1
- [pyt] tag=s22c-probes2 start=2026-11-06 18:24:14 end=2026-11-06 18:24:18 elapsed=5s bound=600s status=FAIL rc=1

Outcomes:
- RED + gate rows OFF 201 passed, ON 201 passed.
- Mutants (both RED files + gate rows per mutant; sha-verified restore after each): spec M01 M03 M05 M09 M11 M13 M16 M19 M26 M30 M33 M35 M37 M40 M45 M48 (16) ALL KILLED by AssertionError rows (M01 51 nodes; others 1-6). Own: O02 Riyadh sign KILLED (j16b), O04 recompare self-match KILLED (j07), O05 personalised scoring KILLED (r12b), O06 no pending marker KILLED (j14b), O08 blank pepper KILLED (r08), O10 fit minimal form KILLED (r13). SURVIVED: O01 resume group order reversed, O03 escalation params changed, O07 DRY resume writes a ledger row, O09 sample boundary < -> <=.
- Migration readers + E-row files (11) OFF and ON: green. Route pins (23) OFF, CI-order set (19), comm chunks c01 / c14 / c20 (GREEN's chunk files): every FAILED / ERROR id is in the base record e701a8ba... (comm -23 vs the record EMPTY).
- tests/test_s81_s03_llm_ledger_v2.py ON: 4 failed = test_i2[None|false], test_i6[None|false]; the failing assertion is the leaf-recorder count only ({_count_ok, price_call, current_openai_ledger, current_llm_records}); the value assertions before it (total_cost 0.01731, openai calls 12) pass: no billing change (R-A3 holds); GREEN's Q1 confirmed as stated.
- Runtime probes (corr_probe_test.py, run inside tests/ of the scratch worktree, deleted after): P1 two consecutive FakeClient runs (timeout -> 2 batch_pending rows, 0.0 settle, no ledger, no delete; run 2 resumes first, no re-submission, ONE ledger row with the old provider_batch_id, delete, rows filled, judged_at set) PASS; P2 FAIL (MAJOR-3); P3 pair HMAC equal across the 4 input types, 21 closed keys, blank pepper -> None PASS; P4 snapshot cap / cut order PASS (+ the field_status observation, m2); P5 escalation request = model claude-sonnet-5-5, thinking {type: disabled}, temperature 0 (MAJOR-1).
- Static: ruff E9/F63/F7/F82 (9 files) + full ruff on the two new modules clean; py_compile clean; sqlfluff 048 + rollback clean; railway.judge.json loads; new files 0 bytes > 127, 0 CR, no 64-hex literal. Rollback body == 043 body byte for byte (2477 chars); 048 body = 043 + exactly the one kb_feedback DELETE before the first UPDATE; no migration after 043 redefines delete_user_cascade.
- Comm set re-derivation (union rule: tests naming the touched modules / paths, migration / CLAUDE.md / railway readers, glob / walk / listdir readers, importers of the E-row and S81-20 / 043 helper files): 170 candidates, all in GREEN's 729 except tests/fixtures/_gen_rubric_truth_flag_off_digests.py (a generator, not collected) and tests/test_skill_frontmatter.py (globs .claude/skills only): no missing member.
- Not re-run by this lens: the corpus gate, the jest fences, the full comm set; the hook test files NOT run (no .githooks change).

## 2. Findings

### MAJOR-1 (GREEN-owned; CONFIRMED by probe P5 + the repo's own router): every Sonnet escalation is a request the API rejects
scripts/cron_compare_judge.py `_escalate` sends `ac.messages.create(**req["params"])` with the Haiku batch params reused: `thinking: {"type": "disabled"}` and `temperature: 0` to the escalation model (default claude-sonnet-5-5). app/services/llm_router.py `_escalation_request` (:1078-1083) states "Sonnet 5.5 rejects thinking disabled" and swaps to `between_tools`; the router never sends temperature to Claude (:733). Failure: in apply every escalation raises, is counted in errors, settles None and the run is capped (`escalation_capped`) every night until it expires: the escalation step (user 'wrong', Haiku flags, the sample, self-produced) never produces a sonnet judgement. No RED row pins the escalation params (O03 survives), so GREEN can fix it without touching a frozen row (the router's escalation form).

### MAJOR-2 (spec / frozen-RED-row defect; PLAUSIBLE; needs an orchestrator ruling): the Haiku batch body likely fails validation on the live API
The batch params carry `temperature: 0` (spec 2.10.9, pinned by the frozen J09 `p["temperature"] == 0`) and JUDGE_SCHEMA carries `maxItems` / `maxLength` / `pattern` (spec 2.11). The Anthropic reference for the current models: Claude Haiku 5.5 rejects non-default sampling values with a 400 (API version 2026-10-21 rejects temperature on every model), and structured outputs do not support string-length / complex array constraints (only the SDK parse helpers strip them; batches.create sends the schema raw). The house G2 batch (scripts/seed_kb_batch.py SEED_SCHEMA / build_requests) sends neither. Failure: every batch request errored (no haiku verdict ever), found only at the first apply (DRY never sends). Not measured live (no network). The ruling decides whether J09 / 2.11 are amended (drop temperature; drop the unsupported constraints and keep the client-side caps `_valid_answer` already applies).

### MAJOR-3 (GREEN-owned; CONFIRMED by probe P2): the resume step maps positional custom ids over whichever pending rows survive
`_resume` rebuilds `by_cid = {custom_id(i): run_id}` from the batch_pending rows found NOW, sorted by run id, while submission numbered ALL batch_runs. If any member's pending row is absent at resume (the marker upsert is chunked and a failed chunk is a counted WARNING, not an abort; or the row was removed), every later position shifts: in P2 (runs 1-3 submitted r0001-r0003, run 2's marker absent) run 2's answer ("answer for r0002") was stored on run 3, judged_at was set on run 3 as clean, and run 2 was re-batched (a second paid Haiku call). J14c uses identical answers for every custom id and cannot see a mis-mapping (O01 survives). Silent wrong verdicts + double billing on a transient write error. Fix shape: persist the position (or the custom id) per pending row, or refuse to fill when the group size differs from the batch's request count.

### Minors (stated limits by default, LC-4)
- m1 (prove-nothing) DRY resume writes unpinned: O07 (the `if not apply: continue` before the resume ledger write removed) survives; J20 has no pending batch. The code is correct today.
- m2 `field_status` is copied raw from body metadata into the row (a list of <= 2 dicts, no value check, no size cap: a 100,011-byte value went through in P4b; EVIDENCE_MAX_BYTES and the evidence CHECK do not cover it). For the privacy lens.
- m3 (prove-nothing) the sample boundary (`< pct` vs `<= pct`) unpinned (O09 survives).
- m4 the S81-03 i2 / i6 isolation pins go red with ENABLE_COMPARE_RUN_LEDGER exported (recorder counts only; values unchanged); CI runs the flag unset. Already GREEN's Q1 and the CLAUDE.md sentence: accurate.
- m5 report keys: the brief's `batch.lost` is `resume.lost` in the bytes; spec 2.12's `feedback_join_absent` is absent (consistent with R-S22-29); the PR body names `resume.lost` correctly.
- m6 the URL exit evaluates `int((time.time() - _start) * 1000)` before the flag read; "one env read per exit and nothing else" (CLAUDE.md / PR) is true for state, not for that arithmetic.
- m7 (prove-nothing) G22-GR2 is a text pin; the @> / <@ guard logic never executes (no Postgres in the gate).
- m8 the box-global core.autocrlf=true makes a fresh checkout of the new LF files CRLF (the frozen RED hashes then differ on disk); informational for the rebase / final rounds.

## 3. Claims checked against the bytes (GREEN report, CLAUDE.md block, PR body)
True as written: the flag first statement after the docstring; five plain non-awaited calls right after capture_result_status (+4 / +2 / +2 incl. imports, CRLF kept); the 21 closed keys; "pair:" HMAC for every input type, fail-closed without a pepper; the cut order specs -> verdict prose -> minimal form; prose dropped on a personalisation marker; ONE fire_and_forget with the label; ONE WARNING with the type name; the judge's step order (resume first: P1 + J14c), the 0.0 settle on timeout, the 404 batch_lost arm, one ledger row per batch and per run's escalations, the per-Riyadh-day sonnet-row head count, the DRY head counts, apply-only prunes (365 / 365), exits 0 / 2; the guard's column-set rule; the hook at chunk index 2; the rollback = 043 byte for byte; E1-E4 exactly as tabled; the S81-03 observation. Contract freeze (PLAN section 0): no request field, route parameter or response key changed; flag-OFF identity held at every exit (RED P rows in both states; M01 / M19 killed). Billing R-A3: response costs unchanged under ON (s03 value assertions pass).
Overstated: step (5) "the capped Sonnet escalation" cannot succeed against the live API as built (MAJOR-1); step (4) depends on MAJOR-2; m6.

## 4. Prove-nothing rows
- test_j14c_resume_first: identical answers for every custom id; blind to the positional mapping (MAJOR-3, O01).
- test_j09_batch_body_deidentified: batch bodies only, never the escalation params (O03); it pins temperature 0 (MAJOR-2).
- test_j20_dry_writes_nothing: no pending batch in its world; the DRY resume branch is unexercised (O07).
- test_j18_sample_seed_stable: the expectation uses the same formula; the boundary is unpinned (O09).
- test_g22_gr2_*: text pins of the guard; the SQL logic is not executed (m7).

## 5. Files (under <scratchpad>/S81-22_adv/)
corr_probe_test.py (the probes); corr_driver.py, corr_plan_gen.py, plan1-4.json; corr_progress.txt; corr_logs/; corr_hashes_start.txt / corr_hashes_end.txt (equal); corr_copies/ (mutant byte copies).
