# S81-07 FIX1 RE-VERIFY (the one re-verifier, both lenses; Opus 5.5; 2026-11-12 10:25-12:20 AST; written by a shell python step)

VERDICT: SOUND (0 blocking, 0 major, 6 minor = stated limits by default; two gates NOT MEASURED by name below).

## (1) HEAD and footprint
- Unit worktree sc-s81-s07: branch feature/s81-07-meas-claude-gate, HEAD e600215d4f7e2122926ac083d21c664839e3905a, exactly one parent f10c6ae34fcf72232f88362e094801bad954a80c; git status --short empty at start and at end. Nothing edited there.
- Footprint f10c6ae3..HEAD: CLAUDE.md (8 lines), scripts/meas_claude_gate.py (+248/-30), tests/test_s81_s07_meas_harness.py (+529). tests/_env_safety.py untouched. No app/ byte.
- Blobs: script sha256 24ef67a4... (= the fix report), RED 49ba5bfb... (= the fix report).

## (2) Mutants (ONE detached scratch worktree <notes>/rv/adv at e600215d, python only, fixtures/script/RED rewritten from their LF blobs; each mutant an exact-string edit matching once on a byte copy, restored and sha256-verified (24ef67a4...) after every run and at the end; .qa-mutation.lock created and removed; the scratch worktree removed with git worktree remove --force, absent from git worktree list, path gone)
Method: each mutant first against the 19 fix-round nodes (-k r76..r92), and against the WHOLE unit file when it survived there. Kill type: every killing log carries only AssertionError / plain assert E-lines (build_report.py scanned each log for any other exception type: none).
Scratch base: [pyt] tag=s07f-unit-adv start=2026-11-12 10:30:42 end=2026-11-12 10:32:17 elapsed=94s bound=600s status=OK rc=0 (183 passed; [hermeticity] sentinel checked 183; [netguard] blocked 0)

| mutant | result | killing rows (first 4) | E types | [pyt] |
|---|---|---|---|---|
| A01 | KILLED | test_r88_decision_path_fail | - | [pyt] tag=s07f-mut-A01 start=2026-11-12 10:34:46 end=2026-11-12 10:35:45 elapsed=60s bound=600s status=FAIL rc=1 |
| A02 | KILLED | test_r88_decision_path_fail | - | [pyt] tag=s07f-mut-A02 start=2026-11-12 10:36:42 end=2026-11-12 10:37:38 elapsed=55s bound=600s status=FAIL rc=1 |
| A03 | KILLED | test_r87_decision_path_pass, test_r88_decision_path_fail | - | [pyt] tag=s07f-mut-A03 start=2026-11-12 10:38:32 end=2026-11-12 10:39:24 elapsed=52s bound=600s status=FAIL rc=1 |
| A05 | KILLED | test_r88_decision_path_fail | - | [pyt] tag=s07f-mut-A05 start=2026-11-12 10:40:13 end=2026-11-12 10:40:59 elapsed=47s bound=600s status=FAIL rc=1 |
| A06 | KILLED | test_r88_decision_path_fail | - | [pyt] tag=s07f-mut-A06 start=2026-11-12 10:41:49 end=2026-11-12 10:42:39 elapsed=50s bound=600s status=FAIL rc=1 |
| A15 | KILLED | test_r91_completed_nontransient_call_never_resent | AssertionError | [pyt] tag=s07f-mut-A15 start=2026-11-12 10:43:27 end=2026-11-12 10:44:15 elapsed=48s bound=600s status=FAIL rc=1 |
| A19 | SURVIVED | - | - | [pyt] tag=s07f-mut-A19-full start=2026-11-12 11:10:02 end=2026-11-12 11:11:25 elapsed=83s bound=600s status=OK rc=0 |
| A20 | SURVIVED | - | - | [pyt] tag=s07f-mut-A20-full start=2026-11-12 10:46:41 end=2026-11-12 10:47:56 elapsed=75s bound=600s status=OK rc=0 |
| A20b | KILLED | test_r80_resume_gives_the_same_tail_spans, test_r87_decision_path_pass | AssertionError | [pyt] tag=s07f-mut-A20b start=2026-11-12 12:05:59 end=2026-11-12 12:06:46 elapsed=46s bound=600s status=FAIL rc=1 |
| A24 | KILLED | test_r86_sensitive_subset_of_a4, test_r88_decision_path_fail | AssertionError | [pyt] tag=s07f-mut-A24 start=2026-11-12 10:48:44 end=2026-11-12 10:49:33 elapsed=49s bound=600s status=FAIL rc=1 |
| A26 | KILLED | test_r87_decision_path_pass | AssertionError | [pyt] tag=s07f-mut-A26 start=2026-11-12 10:50:22 end=2026-11-12 10:51:10 elapsed=48s bound=600s status=FAIL rc=1 |
| A27 | KILLED | test_r88_decision_path_fail | - | [pyt] tag=s07f-mut-A27 start=2026-11-12 10:51:59 end=2026-11-12 10:52:45 elapsed=46s bound=600s status=FAIL rc=1 |
| A28 | KILLED | test_r88_decision_path_fail | - | [pyt] tag=s07f-mut-A28 start=2026-11-12 10:53:34 end=2026-11-12 10:54:21 elapsed=46s bound=600s status=FAIL rc=1 |
| A32 | KILLED | test_r92_retry_after_floor[0], test_r92_retry_after_floor[-5], test_r92_retry_after_floor[0.2] | - | [pyt] tag=s07f-mut-A32 start=2026-11-12 10:55:10 end=2026-11-12 10:56:05 elapsed=55s bound=600s status=FAIL rc=1 |
| A34 | KILLED | test_r80_resume_gives_the_same_tail_spans | AssertionError | [pyt] tag=s07f-mut-A34 start=2026-11-12 10:56:54 end=2026-11-12 10:57:45 elapsed=52s bound=600s status=FAIL rc=1 |
| A35 | KILLED | test_r87_decision_path_pass, test_r88_decision_path_fail | AssertionError | [pyt] tag=s07f-mut-A35 start=2026-11-12 10:58:36 end=2026-11-12 11:00:01 elapsed=85s bound=600s status=FAIL rc=1 |
| A36 | KILLED | test_r87_decision_path_pass | AssertionError | [pyt] tag=s07f-mut-A36 start=2026-11-12 11:00:50 end=2026-11-12 11:01:34 elapsed=44s bound=600s status=FAIL rc=1 |
| A37 | KILLED | test_r87_decision_path_pass | AssertionError | [pyt] tag=s07f-mut-A37 start=2026-11-12 11:02:23 end=2026-11-12 11:03:54 elapsed=91s bound=600s status=FAIL rc=1 |
| N01_bytes_branch_removed | KILLED | test_r77_live_guard_admits_the_allowed_host_end_to_end, test_r78_other_host_refused_as_str_and_bytes, test_r79_connect_admits_only_addresses_resolved_for_the_allowed_host | AssertionError | [pyt] tag=s07f-mut-N01 start=2026-11-12 11:14:51 end=2026-11-12 11:15:43 elapsed=51s bound=600s status=FAIL rc=1 |
| N02_resolved_set_ignored | KILLED | test_r79_connect_admits_only_addresses_resolved_for_the_allowed_host | AssertionError | [pyt] tag=s07f-mut-N02 start=2026-11-12 11:45:40 end=2026-11-12 11:47:19 elapsed=99s bound=600s status=FAIL rc=1 |
| N03_set_filled_every_host | KILLED | test_r79_connect_admits_only_addresses_resolved_for_the_allowed_host | AssertionError | [pyt] tag=s07f-mut-N03 start=2026-11-12 11:48:07 end=2026-11-12 11:48:56 elapsed=48s bound=600s status=FAIL rc=1 |
| N06_tail_for_replayed_round | KILLED | test_r80_resume_gives_the_same_tail_spans | - | [pyt] tag=s07f-mut-N06 start=2026-11-12 11:49:45 end=2026-11-12 11:50:50 elapsed=65s bound=600s status=FAIL rc=1 |
| N07_censored_ignored | KILLED | test_r81_timed_out_tail_leg_is_infinite_and_counted | - | [pyt] tag=s07f-mut-N07 start=2026-11-12 11:51:48 end=2026-11-12 11:53:16 elapsed=88s bound=600s status=FAIL rc=1 |
| N09_knob_tail_literal | KILLED | test_r82_report_reads_the_current_knob_values | AssertionError | [pyt] tag=s07f-mut-N09 start=2026-11-12 11:54:05 end=2026-11-12 11:54:52 elapsed=47s bound=600s status=FAIL rc=1 |
| N11_unmatched_intent_not_in_cost | SURVIVED | - | - | [pyt] tag=s07f-mut-N11-full start=2026-11-12 11:57:17 end=2026-11-12 11:58:39 elapsed=82s bound=600s status=OK rc=0 |
| N12_incomplete_rounds_counted | KILLED | test_r83_cost_per_synthetic_compare | AssertionError | [pyt] tag=s07f-mut-N12 start=2026-11-12 11:59:28 end=2026-11-12 12:00:20 elapsed=52s bound=600s status=FAIL rc=1 |
| N13_p95_is_p50 | KILLED | test_r83_cost_per_synthetic_compare | - | [pyt] tag=s07f-mut-N13 start=2026-11-12 12:01:08 end=2026-11-12 12:01:57 elapsed=49s bound=600s status=FAIL rc=1 |
| N14_cap_wrong_lane | KILLED | test_r84_compares_per_day_under_the_code_default_cap | - | [pyt] tag=s07f-mut-N14 start=2026-11-12 12:02:47 end=2026-11-12 12:03:33 elapsed=47s bound=600s status=FAIL rc=1 |
| N16_cache_numerator_write | KILLED | test_r85_cache_read_share | - | [pyt] tag=s07f-mut-N16 start=2026-11-12 12:07:34 end=2026-11-12 12:08:29 elapsed=55s bound=600s status=FAIL rc=1 |
| N19_env_pop_live_only | KILLED | test_r89_variable_removed_in_every_mode_before_a_child | - | [pyt] tag=s07f-mut-N19 start=2026-11-12 12:04:21 end=2026-11-12 12:05:10 elapsed=48s bound=600s status=FAIL rc=1 |
| S06 | KILLED | test_r90_unit_ceiling_clause_of_the_reservation | - | [pyt] tag=s07f-mut-S06 start=2026-11-12 11:04:43 end=2026-11-12 11:05:31 elapsed=47s bound=600s status=FAIL rc=1 |

Survivors of the two reports (16 of F-6 / F-4 / F-7 + S06): 15 KILLED by named rows (A01 A02 A03 A05 A06 A15 A24 A26 A27 A28 A32 A34 A35 A36 A37) + S06 KILLED by R90. A30 is byte-identical to S06 (the same exact-string edit), so it is now killed by R90 too.
- A20 as specified (p2 = _monotonic() at the round start) SURVIVED the full file and is EQUIVALENT: the Phase 2 line `p2 = _monotonic()` (meas_claude_gate.py _run_a1, the reviews branch) overwrites p2 before every verdict read, so no round can observe the start value (true at f10c6ae3 too; F-4's "R80 kills A20" is unreachable for this exact string). The meaningful variant A20b (the round-start value KEPT: the Phase-2 reassignment removed) is KILLED by R80 and R87. Accepted here as equivalent.
- A19: SURVIVED the full file; equivalent under start step 7 as F-6 ruled (accepted).
New mutants on the fix lines (13 measured): F-3 N01 N02 N03 (all KILLED: R77/R78/R79, R79, R79); F-4 N06 N07 N09 + A20b (KILLED: R80, R81, R82, R80/R87); F-5 N11 N12 N13 N14 N16 (N12 R83, N13 R83, N14 R84, N16 R85 KILLED; N11 SURVIVED, minor m1); F-7 N19 (KILLED R89).
NOT MEASURED by name (budget: the incident lane's comm chunks held the box 11:16-11:42): N04_connect_port_ignored, N05_bytes_case_kept, N08_summary_censored_count_zero, N10_report_tail_censored_zero, N15_per_day_ceil, N17_sensitive_needs_both, N18_sensitive_refusals_all, N20_report_no_rescan, N21_tail_span_nonfinite_accepted (definitions in rv_mutants.py). N17 was started at 12:09 and stopped before its result; the script was restored from the byte copy and sha-verified.

## (3) M1 again, end to end, both loops (probe file test_zz_rv_probe_s07.py, run in the scratch worktree then deleted)
- Default (proactor) loop, REAL httpx2 transport, fake resolver -> 127.0.0.1: exit 6 stop max_calls, hosts_refused [], the resolver reached once with b'api.anthropic.com' (bytes: the M1 case). (probe_out/m1_default_loopback.json)
- Selector loop, REAL transport, fake resolver -> 192.0.2.7 (TEST-NET-1), socket.socket.connect replaced BEFORE the guard by a recorder (loopback passed through for the loop's own socketpair; every other address recorded and refused locally, no packet): the guard ADMITTED the resolved address: connect_attempts [("192.0.2.7", 443)], hosts_refused [], stop max_calls. This is the resolved-address path R77 does not exercise (R77's resolver returns loopback, admitted by the loopback rule; R79 pins the path at unit level). (m1_selector_testnet.json; the first two attempts failed on probe defects: a missing fixture import, then my recorder refusing the selector loop's self-pipe; fixed, re-run.)
- Units: host_allowed(b"api.anthropic.com",443) True; b"evil.example" False; port 80 False; undecodable False; a literal before resolution refused; another name refused before resolution; create_connection to an unresolved literal refused; nothing reached the connect recorder (m1_units.json). netguard blocked 0 on every run.
- [pyt] tag=s07f-probe start=2026-11-12 11:42:46 end=2026-11-12 11:43:01 elapsed=15s bound=600s status=FAIL rc=1 (17 errors: the probe's missing fixture import; 1 passed = m1_units)
- [pyt] tag=s07f-probe2 start=2026-11-12 11:43:58 end=2026-11-12 11:44:44 elapsed=45s bound=600s status=FAIL rc=1 (15 passed, 3 failed: probe defects, see (3), (6), (7))
- [pyt] tag=s07f-probe3 start=2026-11-12 12:09:42 end=2026-11-12 12:10:00 elapsed=18s bound=600s status=FAIL rc=1 (15 passed; 3 failed: the selector recorder defect, the resume probe's own assertion (see 6), the figures probe's report assertion (minor m2))
- [pyt] tag=s07f-probe4 start=2026-11-12 12:11:19 end=2026-11-12 12:11:28 elapsed=9s bound=600s status=OK rc=0 (the selector M1 probe, 1 passed); [netguard] blocked 0 on all four.

## (4) B1 again (Git Bash env.exe on this box, a NON-credential name S07RV_ARGV_PROBE and a run-time canary read by command substitution from a file ending CR LF; Get-CimInstance Win32_Process while the child slept)
- The corrected template shape `S07RV_ARGV_PROBE="$(cat f)" env -u S07RV_NOPE <PY> -c ...`: env.exe command line `"...env.exe" -u S07RV_NOPE C:/.../python.exe -c ...`, NO canary window; the child saw the variable (True).
- The control (assignment after env): env.exe command line carries `S07RV_ARGV_PROBE=rvprobe<CANARY>` (window found). The canary file was deleted; procs.txt is masked.
- The template text: the module docstring line, the CLAUDE.md "THE RUN COMMAND" bullet and PR_BODY.md:79 are the same string with the assignment before `env`; the dry-run template carries no assignment (R76 pins the docstring and CLAUDE.md).

## (5) The credential canary on every path (the REAL SDK client the harness builds, with its request hook, over an httpx2 MockTransport that echoes the x-api-key header into the body, a response header and the exception text)
success (code 6 max_calls), 400 (6), 401 (5, one send), 429 retry-after 0 (0, 4 sends), 500 (6 transient), ConnectError(<key>) (6 transient), ValueError(<key>) raised in the transport (6 transient: the SDK wraps it), KeyboardInterrupt (130): no 4-character window of the canary in any file under --out, stdout or stderr; the variable absent after main; the lock gone; no authorization header ever sent; stderr 0 lines. Modes: text --dry-run, moderation --dry-run, report, vision NOT RUNNABLE, web_search NOT RUNNABLE: exit 0, the variable absent after start, 0 key reads, no leak. A child text --dry-run started WITH the variable set (rv_dry_canary.py, outside pytest): key_reads 0, the git child did not see the variable, no leak, stderr 0, exit 0. (A crash raised OUTSIDE the transport is covered by R10 / R42, green in the unit run; not re-probed.)

## (6) MAJ-2 resume with a fake clock
R80 green at the head and kills A34, N06, A20b. Independent probe (probe_out/resume_tail.json): spans are written only for rounds whose tail legs were all sent in one process: a stop after round 0's first review (max-calls 9) gives NO span for round 0 on resume (n printed 3 for 4 rounds), a stop after the verdict keeps the span; no replayed round produced a 0-ms span (the MAJ-2 defect is gone). The probe's own equality assertion failed by my design (per-run create numbering moved the fake clock's tail cost, and my "pure replay" run sent a new round); no defect there. A round split by a stop loses its span: by F-4 (a), stated, visible as n.

## (7) MAJ-3: the four figures recomputed by hand (probe_out/figures_by_hand.json)
Ledger: A1 run 1 with 17 sends, its last done line deleted (a kill after the intent), resume with 64 sends (a 400 inside round 2), then A4 with 4 refusals. By hand from the ledger: 5 complete rounds; cost p50 0.00059557, p95 0.00124832 USD (the unmatched intent's worst_usd included); compares per day at the code-default live cap 3.0: floor(3.0/p95) = 2403, floor(3.0/p50) = 5037; cache_read share pooled 0.07958989 (classify 0.105607477); A4 sensitive-looking n 21, refusals 0 (my refusal indexes missed that subset; R86 pins a non-zero case). The script's results.json A1 block after the A1 run: identical on all four (n 5, p50 0.00059557, p95 0.00124832, pooled 0.07958989, classify 0.105607477, n_sensitive 21 / 0). BUT the REPORT after the later A4-only run printed "NOT MEASURED" for cost and compares per day and "pooled None" for the share: minor m2.

## (8) Unit file, pins, dry runs
- Unit file: 183 passed on the committed bytes (the scratch base above).
- Pins: not re-run by me (budget); the fix report's 18 pin lines are read and match GREEN's counts (s22_judge's one CRLF base node j01). NOT MEASURED here.
- Dry runs on the committed script bytes (a byte copy of the blob + the fixtures from git show + app/ copied from the scratch worktree, each stage its own child, the fix agent's dry_all.py unchanged): text 622 / 1.443423, moderation 200 / 0.261435, vision --set 300 / 3.61238, web_search --owner-line 80 / 1.33096, vision / web_search NOT RUNNABLE and report exit 0; every child exit 0, stderr 0 B, blocked 0, key_reads 0, clients 0 (dry/dry_all.json). The report child now imports the app modules (F-4 (d)): still no socket, no key read.

## (9) CLAUDE.md and the PR body against the bytes
- Command shape: correct in the docstring, CLAUDE.md and PR_BODY.md:79/81 (assignment before env; the dry run with none).
- Booking: CLAUDE.md / PR "400, 401, 403, 404, 413, 422 or 429 books 0.0; 409 and every other status book the worst case" = UNBILLED_STATUSES (meas_claude_gate.py:71) and NON_TRANSIENT; correct.
- Figures: 622 / 200 / 300 / 80 calls and 1.443 / 0.261 / 3.612 / 1.331 USD match the re-run; the code-default cap 3.0 = llm_spend_breaker.DEFAULT_CAPS_USD["live"]; "183 passed" matches.
- Wrong / stale: PR_BODY.md line 4 still says the RED file has "164 nodes = 152 R + 12 P" (now 183): minor m4. "the CURRENT values ... read from the router": see minor m3.
- PR body 24,669 B (<= 25,600), 0 CR, 4 non-ASCII bytes (the attribution emoji only).

## MINORS (stated limits by default; none production-visible: the harness is an offline ops tool)
- m1 N11 SURVIVES the whole file: no row pins F-5 (a)'s clause that an unmatched intent's worst_usd counts in its round's cost (no R83 ledger carries a killed call). The code is right (recomputed by hand in (7) with a killed call). A row would close it.
- m2 results.json holds only the settings of the LAST invocation of a stage: after `text --settings A4_refusal_names` the report's cost-per-compare, compares-per-day and cache_read lines read NOT MEASURED / None (measured in (7)), and the A1-based TEXT bars lose their inputs, although the ledger holds every A1 call. Operator rule for the READY pack: the last text invocation before `report` runs every setting (a resume replays completed calls at no cost). Pre-existing for the bar metrics; it now also hides the F-5 figures.
- m3 The "current" knob values on the proposal lines are always the CODE DEFAULTS in a real run: the knobs are ANTHROPIC_* environment reads and every ANTHROPIC_* name refuses the start (REFUSED_ENV_PREFIXES), so a production override (e.g. a Railway ANTHROPIC_TAIL_RESERVE_SECONDS) can never be seen. CLAUDE.md and the PR body say "CURRENT values ... read from the router"; the line should say "code default (production overrides are not visible to this run)".
- m4 PR_BODY.md line 4: "164 nodes = 152 R + 12 P" is stale (183 nodes since FIX1).
- m5 Pre-existing guard breadth: a NAME starting "127." (e.g. "127.evil.example") counts as loopback in host_allowed / _loopback, so in live mode its resolution is allowed (probe: gai "passed"); on a selector loop the connect to its non-loopback address is still refused (not in the resolved set), on the proactor loop the connect wrapper does not see the connect (L15). The harness client's request hook refuses any such URL; only an app-module resolution could reach it. Defense in depth only.
- m6 A tail leg that fails fast (a 5xx / connection error, not a timeout) still yields a finite, short span for its round (only APITimeoutError censors); a resumed round keeps that span (the last tail line per round wins and a replayed round writes none).

## GATES NOT MEASURED (by name)
- The comm set at e600215d (F-10 (8)): the fix report left it NOT MEASURED and F-11 does not assign it; I did not run it (budget). The orchestrator runs it before the PR; the footprint is the script, the RED file and CLAUDE.md (the CLAUDE.md readers were run as pins by the fix agent).
- The fix report's 18 pins (re-read, not re-run). The nine new mutants listed in (2).

## Process
Every pytest went through pyt.py, one at a time, after the foreign-process probe (waitfree.ps1 excluding ONLY the run's own exact tag), with a 45 s yield and a second probe after each; the incident lane's inc-mon1-final chunks were waited out (11:16-11:42; the longest wait 26 min). I stopped only my own processes (my mutant driver, twice; its pytest child exited with it); the script restored from the byte copy and sha-verified both times. No live run, no network call (netguard 0 everywhere; the only connect target outside loopback, 192.0.2.7, went to a recorder), no key file or dotenv read, the credential variable only ever a run-time test canary, no credential-shaped value printed.
Files (<notes>/rv): notes.md, rv_run.py, waitfree.ps1, rv_mutants.py, mut_results.json, mut_table.md, mut_driver.out, mut_driver2.out, mut-*.log, test_zz_rv_probe_s07.py, probe*.log, probe_out/*.json, b1/procs.txt (masked), dry/dry_all.json, rv_dry_canary.py, drycopy/ (a byte copy for the dry runs), build_report.py, write_report.py.
