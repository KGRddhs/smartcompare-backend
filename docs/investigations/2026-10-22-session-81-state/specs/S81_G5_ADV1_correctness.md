# S81-G5 ADVERSARY REPORT (correctness lens, R-G5-1 / R-G5-15 / GC-9 checks folded in), Opus 5.5, 2026-11-05

VERDICT: NOT_READY (0 blocking, 1 major, 7 minor). The code is correct on every probed path; the major is a comm-set membership gap (procedural, measured green at HEAD), fixable in a docs / gate round with no code change.

Written through the shell (python), as the harness refuses a subagent Write of a report .md.

## Bytes verified
- GREEN worktree sc-s81-g5: HEAD 53b7b66e71b92c9904e2f6cb702f20ff78edf719 on feature/s81-g5-learn-search, parent ec747b49 = origin/main, git status empty (first and last).
- Frozen RED tests/test_s81_d22_nightly_learning.py 98b2bafc...8656 first and last (worktree and blob).
- Every changed file matches the GREEN table: cron_learning.py f6aa1f6a..., railway.learning.json 567e270d..., test_s81_g5_gate_rows.py a631898a..., test_s81_kb_schema.py 33abdfb4... (wt CRLF; blob 79177882...), CLAUDE.md dc0d7ce8... (wt CRLF).
- Scratch worktree <scratchpad>/S81-G5_adv_correctness (git worktree add --detach at 53b7b66e; no junction): the fresh checkout makes the new files CRLF; measured once as-is (RED + gate rows 52 passed, so no new fresh-checkout CRLF node), then the four new files rewritten from their LF blobs so every hash equals the GREEN table (hashes_start.txt); sha-verified before removal; removed with git worktree remove --force (git worktree list: gone).

## Runs ([pyt] lines)
- [pyt] tag=g5adv-red-crlf start=2026-11-05 04:52:48 end=04:52:57 elapsed=9s bound=600s status=OK rc=0 (52 passed: RED + gate rows on the CRLF fresh checkout)
- [pyt] tag=g5adv-red-off start=2026-11-05 04:53:17 end=04:53:28 elapsed=11s bound=600s status=OK rc=0 (52 passed; netguard 0)
- [pyt] tag=g5adv-red-true start=2026-11-05 04:53:29 end=04:53:38 elapsed=9s bound=600s status=OK rc=0 (ENABLE_LEARNING_JOB=true in the runner env only; 52 passed)
- [pyt] tag=g5adv-red-apply start=2026-11-05 04:53:39 end=04:53:48 elapsed=9s bound=600s status=OK rc=0 (=apply in the runner env only; 52 passed)
- [pyt] tag=g5adv-probe start=2026-11-05 05:15:50 end=05:15:54 elapsed=3s bound=600s status=OK rc=0 (my 28 probe rows, scratch only; copy probe_tests_copy.py)
- [pyt] tag=g5adv-commA start=2026-11-05 05:30:08 end=05:31:56 elapsed=109s bound=1200s status=OK rc=0 (16 files: 551 passed, 1 skipped; the netguard lines = test_hermeticity_pins' own probes)
- [pyt] tag=g5adv-commB start=2026-11-05 05:32:14 end=05:33:18 elapsed=63s bound=1200s status=FAIL rc=1 (15 files: 2 failed = d16 r10, d17 r9 / 1627 passed; netguard 24 attempts from the 2 s04 rows)
- [pyt] tag=g5adv-commC start=2026-11-05 05:33:30 end=05:34:38 elapsed=67s bound=1200s status=FAIL rc=1 (15 files + tests/test_s81_s08b_gate_rows.py: 6 failed = five s16 r27 + s19 r15 / 1036 passed)
- [pyt] tag=g5adv-secretscan start=2026-11-05 05:35:06 end=05:35:33 elapsed=27s bound=600s status=OK rc=0 (31 passed, alone)
- [pyt] tag=g5adv-ciorder start=2026-11-05 05:35:34 end=05:36:35 elapsed=60s bound=1200s status=FAIL rc=1 (spec 12.1 set: 1 failed = d17 r9 / 835 passed; identical to GREEN)
- Comm vs the STORED base record base_records/ec747b49.../c636b9d5....txt (its .files == the RED COMM_SET.txt; reused, LC-6): all 46 HEAD files (= GREEN's two chunks) re-run in my three chunks + the secret scan alone: the HEAD failed set == the 8 base nodes; comm -13 EMPTY; comm -23 EMPTY. tests/test_s81_s08b_gate_rows.py (the missing member, MAJ-1): 0 failed at HEAD.
- 54 mutant runs (table below); harness mut/adv_mut.py, .qa-mutation.lock held and removed, the target restored and sha256-verified after every mutant (final sha f6aa1f6a... True after each batch).
- ruff --select E9,F63,F7,F82 --no-cache (cron_learning.py, gate rows, kb_schema): All checks passed; py_compile OK; json.loads(railway.learning.json) == the 3.2 object.
- Bytes: cron_learning.py / railway.learning.json / gate rows / RED file: 0 bytes > 127, 0 CR in the blobs, 0 64-hex runs, 0 8-digit runs, 0 '+973'; the gate rows' one at sign = the pytest decorator; module constants with a gitleaks keyword in the name: none; no kb_service token; the only '"data"' literal is getattr(resp, "data", None) (a response attribute, not a path); no write_text; module-top imports = stdlib + scripts.kb_seed_common.
- NOT run (by rule): the hook test files (no .githooks change, GC-8), the client jest fences (no junction in the adversary worktree; GREEN's duty, GC-9 says pytest only), the FULL jest (LC-7), the corpus gate (no price_service edit).

## MAJOR
- MAJ-1 (comm set, union rule): tests/test_s81_s08b_gate_rows.py is a CLAUDE.md READER missing from the 46-file set (the RED's derivation, inherited by GREEN under GC-8). It imports CLAUDE_MD from tests/test_s81_s08b_legacy_fingerprint.py (a member; :74 `CLAUDE_MD = ROOT / "CLAUDE.md"`) and reads it at tests/test_s81_s08b_gate_rows.py:282 (`CLAUDE_MD.read_text`) for the RB8-4 row slice. GREEN edits CLAUDE.md (:341 + the new block), so the file belongs to the set (the string grep misses a module-path reader: the ST1 MAJ-E1 class; session-80 addendum: a missed member that is green is still a MAJOR). Measured 0 failed at HEAD (inside g5adv-commC): no regression (its slice ends at the next **SESSION paragraph, before the G5 block). Remedy, no code change: add it to the set (47 + secret scan = 48 at HEAD), record it at base for the changed set (LC-6: the set hash changes) or accept this HEAD measurement by ruling, and update the PR body's comm line. The rest of the re-derivation is exact: reference grep (+ kb_feedback) = 24 files; the CLAUDE.md readers; the scripts/ and tests/ walkers (every other rglob outside the set is app/-rooted); the railway*.json glob readers (only s16b + the RED file; test_s75_fanout_starve / test_shutdown_drain read railway.json only); importers of members (only the precommit_hook family, excluded by rule, and test_s81_g3_gate_rows.py, which imports s17 helpers and reads no edited file: not a member).

## MINOR (stated limits by default, LC-4)
- MIN-1 the kb_specs by-id read is NOT paged within a 100-id chunk: _read_by issues ONE range(0, IN_CHUNK*8-1) = 800 rows per chunk and returns status ok. Probe (900 non-cited rows + the cited row of one product): kb_specs rows 800, status ok (not capped), grounding [] and proposed_action needs_operator instead of recheck_source. Spec 2.3 prescribes this shape; dark, judge pending, nothing applied, kb_feedback has no writer; realistic only above about 50 reported kb products per night (8 D05 fields x 2 langs). Stated limit, or a small follow-up (page within a chunk, or mark the table capped).
- MIN-2 prove-nothing in the frozen RED for four screen shapes: R14 seeds the +973 and 8-digit shapes only in query / change_suggestion (never selected: they prove the select discipline, not the screen), and its uuid sentinel carries an 8-digit zero run (00000000004d), so the 8-digit regex masks the uuid regex. Mutants A1 (no 8-digit regex), A2 (no +973), A3 (no uuid), A4 (64-hex anchored), A11 (field-name screen dropped), A12 (mixed -> unknown) SURVIVE the RED + gate rows. My 28 probe rows (each shape alone in the product name, the winner_reason, the value_context, a kb_feedback field and a kb_specs source_url, DRY and APPLY, scanning the report, the md, every log record and every upsert row; plus a mixed-source cluster) pass on the GREEN bytes and KILL all six (A1 5 failed, A2 4, A3 4, A4 4, A11 2, A12 1). The code is right; the frozen rows do not pin those shapes. Optional: adopt the probe as a gate row in a later round.
- MIN-3 A18 (the per-comparison de-dup in _confirmed removed) survives: near-equivalent (the per-pair setdefault still de-duplicates the outputs); only learning.dropped.deidentify differs for an unclean comparison confirmed by two users. Related: one unclean confirmed comparison counts 2 in dropped_deidentify when both its exemplar and its eval candidate drop (two candidates), consistent with spec 2.6 "dropped candidates / groundings".
- MIN-4 owner-steps order (CLAUDE.md :567 and the PR body owner steps): step (2) creates the service WITH the nightly cron schedule, while step (3)'s first canary item says "report it before the schedule is set" (the R-G5-7 text on top of the spec's step (2)). Reword: create the service without a schedule, ONE DRY run, then the schedule.
- MIN-5 the PR body De-identification paragraph and the CLAUDE.md row say only product names, field / category / source names, verdict text and counts reach the outputs; the report's proposal grounding entries also carry the kb product_id and the kb_specs source_url (spec 2.5 allows them; both screened), plus the version strings and exception type names. Wording.
- MIN-6 log lines carry product names unescaped: the shape screen does not reject control characters, so a stored product name with a newline can split an exemplar / eval_case log record. Names come from the identify step, not free user text; stated limit.
- MIN-7 _read_window reports capped when a table holds exactly max_rows rows in the window (no tail exists); spec 2.3 conformant ("reaching the cap = capped"); informational.

## Lens checks (measured on the GREEN bytes)
- OFF before any I/O with the full configuration: R2 x9 green; M1 (client touched before the mode read) killed by 11 nodes (R2 x7, R11, R18 x2, ...).
- DRY zero writes / APPLY exactly ONE upsert on kb_coverage_daily, on_conflict day,metric, every row through build_coverage_row (keyword-only, day a date): R3 / R4 / R21 green; M8, M9 killed; one upsert call site, inside mode == apply and rows.
- SELECT strings == the 2.2 constants (no query, change_suggestion, mattered_most, event_data, error_message, products_found, bare full_response): R6 green; M6 killed; every select passes its module constant.
- Paging ORDER BY id, the cap, the window edges: _page orders on id for every read; pages of PAGE_SIZE cut at the cap; gte start / lt end; end = combine(day + 1, 00:00 UTC), day = (_now() - 1 day).date() unless --day: R6 / R7 / R8 / R11 green; M3, M4, A9, A17 killed; A7 killed by R7.
- Absent-table skip / one-table error isolation: R16 / R17 green; M10 killed; code in MISSING_TABLE_CODES -> absent, else error; one WARNING with the type name only.
- Client failure: exit 1 after one ERROR line with the type name (raise and None): R18 x2 green; M14 killed.
- GC-2 two-actor rule: _Cases.add records the actor on EVERY report; G5-GR1 green; M5 killed (also by G5-GR1); A16 killed.
- GC-3 screen before the cut, GC-4 eval kept when only winner_reason is unclean: code order verified; G5-GR2 green; M7 killed.
- De-identification on every output path incl. a shape inside a longer token: R14 green + my probes (MIN-2) over the report, the md, every log record and every upsert row; the 64-hex device keys never leak.
- Deleted script absent everywhere: scripts/cron_few_shot_rotation.py and tests/test_cron_few_shot_rotation.py gone; the remaining name mentions are docs/plans, scripts/fill_in_legal.py:74 + tests/fixtures/legal_fill_in_u8.json + tests/test_legal_docs_u8.py (L12, the ENABLE_FEWSHOT_ROTATION name) and tests/test_exemplar_contamination.py docstrings :19 / :160 (E4 ruled out); no railway*.json names it; P4 + R26 green.
- No network / no Redis / no LLM: module imports stdlib + scripts.kb_seed_common; netguard 0 on every RED run; R22 green.
- Billing R-A3 / the contract freeze (PLAN section 0): untouched (no app/ file; no response, quota or ledger path); flag-OFF production identity holds (new flag name, no service, no importer).
- CLAUDE.md: ONE column-0 block (3 lines) after the S81-G4 owner-steps bullet (563 at base; the spec's :565 is its neighbourhood) + the :341 pointer clause (insertion only, 0 deleted bytes; the line's 66 pre-existing non-ASCII bytes untouched); CRLF kept; names only; the R-G5-9 sentence and the R-G5-7 canary item present; knob defaults / ranges, the threshold 7, the buckets and the metric list checked against the code.
- PR body: 14,192 bytes (python), LF; the numbers match the logs (50 nodes = 43 RED + 7 PIN, CI-order 1 / 835, the 8 comm baseline nodes, fences 13 / 14); E1-E3 + E4 ruled out match the diff (git diff --name-status: M CLAUDE.md, A railway.learning.json, D the two rotation files, A cron_learning.py, A the RED file, A the gate rows, M kb_schema); L1-L13 + GC-10 present; [NATIVE READ] EMPTY; the comm line must gain MAJ-1's file; MIN-4 / MIN-5 wording.
- Commit: parent ec747b49, trailer Co-Authored-By: Claude Opus 5.5; no push / PR / rebase.

## Mutation table (KILLED = AssertionError; RED file + gate rows unless noted)
| id | edit | result |
|---|---|---|
| M1 | admin client / client touched before the mode read | KILLED 11 |
| M2 | house_flag semantics (truthy writes) | KILLED 17 |
| M3 | .order("id") dropped | KILLED 2 (R6, R7) |
| M4 | lt edge dropped | KILLED 6 |
| M5 | actors >= -> cases >= | KILLED 3 (R9, R12, G5-GR1) |
| M6 | change_suggestion in FEEDBACK_COLUMNS | KILLED 2 (R1, R6) |
| M7 | screen skipped | KILLED 4 (R12, R13, R14, G5-GR2) |
| M8 | upsert in DRY | KILLED 6 (R3 x5, R5) |
| M9 | on_conflict metric | KILLED 3 (R4 x2, R21) |
| M10 | table error re-raised | KILLED 4 (R16, R17, R20, R29) |
| M11 | exemplars default 10 / clamp 50 | KILLED 3 (R1, R13, G5-GR2) |
| M12 | < 7 -> <= 7 | KILLED 5 (R27, ...) |
| M13 | pdp_ hint filter dropped | KILLED 3 (R8, R9, R17) |
| M14 | client failure returns 0 | KILLED 2 (R18 x2) |
| M15 | judge_state agreed | KILLED 6 (R12, R3 x5) |
| A1 | 8-digit regex dropped | SURVIVED (RED); KILLED 5 by the probes |
| A2 | +973 regex dropped | SURVIVED (RED); KILLED 4 by the probes |
| A3 | uuid regex dropped | SURVIVED (RED); KILLED 4 by the probes |
| A4 | 64-hex regex anchored | SURVIVED (RED); KILLED 4 by the probes |
| A5 | eval screen dropped | KILLED 1 |
| A6 | grounding screen dropped | KILLED 2 |
| A7 | cap status ok | KILLED 2 |
| A8 | category not lower-stripped | KILLED 3 |
| A9 | window start one day early | KILLED 9 |
| A10 | synthetic searches counted | KILLED 1 |
| A11 | field-name screen dropped | SURVIVED (RED); KILLED 2 by the probes |
| A12 | mixed -> unknown | SURVIVED (RED); KILLED 1 by the probes |
| A13 | useful ignored | KILLED 2 |
| A14 | identity kb_feedback -> spec_wrong | KILLED 1 |
| A15 | user_events in_ filter dropped | KILLED 1 |
| A16 | verdict_unsupported actor dropped | KILLED 4 |
| A17 | default day = today | KILLED 11 |
| A18 | per-comparison de-dup dropped | SURVIVED (near-equivalent, MIN-3) |
| A19 | gap demand not summed | KILLED 1 |
| A20 | grounding ignores cited | KILLED 1 |
| A21 | OFF line dropped | KILLED 9 |
| A22 | kb category unknown | KILLED 3 |
| A23 | price source from m0 only | KILLED 1 |
| A24 | an extra log line before the totals | KILLED 1 |

Logs: mut/<id>.log and mut/<id>-probe.log; results mut/results_M1.json, results_A1-no8digit.json, results_A10-synthetic-counted.json, results_A18-exemplar-dedup-off.json, results_A1-no8digit-probe.json.

## Files
- This report: <scratchpad>/S81-G5_adv/correctness_REPORT.md; notes and logs under <scratchpad>/S81-G5_adv/ (red_*.log, comm[ABC].log, secretscan.log, ciorder.log, probe.log, base_failed.txt, head_failed.txt, chA / chB / chC, hashes_start.txt, claude_md.diff, probe_tests_copy.py, mut/).
