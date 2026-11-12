# S81-07 MERGE RE-VERIFY (the one re-verifier, both lenses, Opus 5.5; 2026-11-12 14:44-16:05 AST)
Unit worktree sc-s81-s07, branch feature/s81-07-meas-claude-gate, HEAD dca3a36042a9dfea000d4538d6d72da3cdf1820b, git status --short empty before and after. Nothing edited in the worktree.

## VERDICT: NOT_READY (1 BLOCKING: the comm set has a branch-only failure)

## (1) HEAD and history: PASS
- dca3a360 (one parent a52523ac) <- a52523ac (parents e600215d, 445f8de3). git fetch origin main = 445f8de3 (= M).
- git diff --name-only origin/main HEAD = exactly the M-2 footprint (CLAUDE.md, the script, tests/_env_safety.py, the six fixtures, the RED file); the app/ diff is empty; the merge left the unit's files byte-unchanged vs e600215d; the fix commit = script + RED + CLAUDE.md.
- tests/_env_safety.py vs main: one added line (MEAS_ANTHROPIC_TEST_KEY).
- CLAUDE.md vs main: line 341 = main's line plus ONE pure insertion (the S81-07 pointer sentence; deleting it gives main's bytes exactly); one 11-line block + blank line inserted after the MON1 block, before ## Tests. No sentence of main dropped or re-worded. Block vs e600215d: four word-level replaces only (m5 loopback, m1 killed intent, m6 failed tail leg, m3 code-default).

## (2) MUTANTS (scratch worktree of dca3a360 under rv/adv; the 8 unit LF files came out CRLF and were rewritten from their blobs: script 4a6d73bf..., RED d98c3c12... = the unit worktree; each mutant on a sha-verified byte copy, restored, sha compare OK; lock removed)
| mutant | result | killing row | type |
|---|---|---|---|
| M93 prefix rule restored | KILLED | test_r93_loopback_is_a_parsed_address | AssertionError |
| N11 unmatched intent not in cost | KILLED | test_r94_unmatched_intent_counts_in_its_round_cost | AssertionError (p95 0.00032 vs 0.25032) |
| M95 failed leg span admitted (failed = False) | KILLED | test_r95_failed_tail_leg_excludes_its_round | AssertionError |
| M96 label reverted (KNOB_VALUE_LABEL = "") | KILLED | test_r96_knob_values_labelled_code_default | AssertionError |
| N04 connect port ignored | KILLED | test_r79_connect_admits_only_addresses_resolved_for_the_allowed_host | AssertionError |
| N05 bytes case kept | KILLED | test_r78_other_host_refused_as_str_and_bytes, test_r93 | AssertionError |
| N08 summary tail_n_censored = 0 | SURVIVED (full file) | - | MINOR m-a |
| N10 report censored = 0 (re-anchored on the new line) | KILLED | test_r81_timed_out_tail_leg_is_infinite_and_counted | AssertionError |
| N15 per day ceil | KILLED | test_r84_compares_per_day_under_the_code_default_cap | AssertionError |
| N17 sensitive needs both | KILLED | test_r86_sensitive_subset_of_a4 | AssertionError |
| N18 sensitive refusals over all | KILLED | test_r86_sensitive_subset_of_a4 | AssertionError |
| N20 report stage post-import re-scan removed | SURVIVED (full file) | - | MINOR m-b |
| N21 non-finite tail span accepted on read-back | SURVIVED (full file) | - | MINOR m-c |

[pyt] lines (rows r76-r96 first; the full file when they passed):
[pyt] tag=s07m-rv-M93 start=2026-11-12 14:52:03 end=2026-11-12 14:52:48 elapsed=45s bound=600s status=FAIL rc=1
[pyt] tag=s07m-rv-N11 start=2026-11-12 14:54:08 end=2026-11-12 14:55:00 elapsed=52s bound=600s status=FAIL rc=1
[pyt] tag=s07m-rv-M95 start=2026-11-12 14:55:50 end=2026-11-12 14:56:40 elapsed=50s bound=600s status=FAIL rc=1
[pyt] tag=s07m-rv-M96 start=2026-11-12 15:05:05 end=2026-11-12 15:05:58 elapsed=53s bound=600s status=FAIL rc=1
[pyt] tag=s07m-rv-N04 start=2026-11-12 15:07:49 end=2026-11-12 15:08:51 elapsed=62s bound=600s status=FAIL rc=1
[pyt] tag=s07m-rv-N05 start=2026-11-12 15:10:16 end=2026-11-12 15:11:24 elapsed=68s bound=600s status=FAIL rc=1
[pyt] tag=s07m-rv-N08 start=2026-11-12 15:15:20 end=2026-11-12 15:16:30 elapsed=70s bound=600s status=OK rc=0
[pyt] tag=s07m-rv-N08-full start=2026-11-12 15:20:28 end=2026-11-12 15:22:22 elapsed=114s bound=600s status=OK rc=0
[pyt] tag=s07m-rv-N10 start=2026-11-12 15:26:30 end=2026-11-12 15:28:05 elapsed=95s bound=600s status=FAIL rc=1
[pyt] tag=s07m-rv-N15 start=2026-11-12 15:29:27 end=2026-11-12 15:31:15 elapsed=108s bound=600s status=FAIL rc=1
[pyt] tag=s07m-rv-N17 start=2026-11-12 15:32:39 end=2026-11-12 15:34:04 elapsed=85s bound=600s status=FAIL rc=1
[pyt] tag=s07m-rv-N18 start=2026-11-12 15:34:54 end=2026-11-12 15:36:08 elapsed=74s bound=600s status=FAIL rc=1
[pyt] tag=s07m-rv-N20 start=2026-11-12 15:37:03 end=2026-11-12 15:38:11 elapsed=68s bound=600s status=OK rc=0
[pyt] tag=s07m-rv-N20-full start=2026-11-12 15:39:02 end=2026-11-12 15:40:57 elapsed=115s bound=600s status=OK rc=0
[pyt] tag=s07m-rv-N21 start=2026-11-12 15:41:57 end=2026-11-12 15:44:18 elapsed=141s bound=600s status=OK rc=0
[pyt] tag=s07m-rv-N21-full start=2026-11-12 15:45:14 end=2026-11-12 15:48:15 elapsed=181s bound=600s status=OK rc=0
Every row-subset run: netguard blocked 0, hermeticity sentinel checked 23. The wait rule held: a probe before and after every run (no bound, own tag only excluded); the comm agent's chunks and these runs alternated, never overlapped.

## (3) PROBES (fake resolvers, a connect recorder that refuses locally, MockTransport; nothing left the machine)
- Guard end to end, real httpx2 transport: default (proactor) loop, resolver -> 127.0.0.1: exit 6 max_calls, hosts_refused [], the resolver reached once with b'api.anthropic.com' (the allowed host as BYTES passes). Selector loop, resolver -> 192.0.2.7, recorder refusing: hosts_refused [], the only connect attempt (192.0.2.7, 443).
- loop.getaddrinfo on BOTH loops (ProactorEventLoop, _WindowsSelectorEventLoop), live and loopback-only: b'api.anthropic.com' passes live, refused loopback-only; evil.example, 127.evil.example and b'127.evil.example' refused in both modes and never reach the resolver; on the selector loop sock_connect to the unresolved literal 192.0.2.99 refused; recorder connects [].
- Units: host_allowed False for 127.evil.example (str and bytes), 127.1, 0x7f.0.0.1, 127.0.0.1., LOCALHOST.; True for 127.0.0.1, ::1, localhost, ::ffff:127.0.0.1 (all fail-closed).
- Credential canary (a run-time test canary only): success path exit 6 max_calls, 5 sends; 401 path exit 5 auth, 1 send; no canary in --out, stdout or stderr; the variable absent after start; no lock left; no Authorization header.
- The module docstring run template is byte-equal to e600215d's (1,827 chars; the raw 1,833-byte prefix identical).
[pyt] tag=s07m-rv-unitprobe start=2026-11-12 15:49:14 end=2026-11-12 15:53:29 elapsed=255s bound=600s status=FAIL rc=1 : 193 PASSED (the 187 unit nodes + 6 probes), then my async probe as first written HUNG (its recorder swallowed the loop's own self-pipe connect: a PROBE defect, pytest-timeout fired, no product signal). Fixed (loopback passed through) and re-run:
[pyt] tag=s07m-rv-probe2 start=2026-11-12 15:59:49 end=2026-11-12 15:59:53 elapsed=4s bound=600s status=OK rc=0 (4 passed; netguard 0)

## (4) Unit file, dry runs, request shape
- Unit file: 187 of 187 PASSED inside s07m-rv-unitprobe (174 nodes named test_r*, 13 named test_p*; the PR body's 168 R + 19 P is a red/pin classification not checkable by name). No separate unit-only OK line: the combined run's rc=1 is the probe hang above.
- Dry runs (dry_all.py, each stage in its own child, variable unset): [run] s07m-rv-dry start=15:54:19 end=15:54:47 rc=0 stderr_bytes=0: text 622 / 1.443423, moderation 200 / 0.261435, vision --set 300 / 3.61238, web_search --owner-line 80 / 1.33096; vision / web_search without inputs and report exit 0; blocked 0, key_reads 0, clients 0, child stderr 0 B: unchanged.
- Request-shape comparison (fidelity_probe.py): [run] s07m-rv-fid start=15:54:47 end=15:55:00 rc=0: rounds 0 / 7 / 13 = 16 / 16 equal each (48 / 48), blocked [], the dispatcher sends request + timeout 25.0.

## (5) THE COMM SET: BLOCKING
The merge agent did not measure it; a separate comm agent (tags s07c-comm-*, folder S81-07_comm) ran it during this review (base 14:53-15:09, head 15:10-15:29). Recomputed by me from the stored lists:
- base record present: harness/base_records/445f8de3e624d3d52a6903bafa6bfae0cb750cf6/d79dfdf0... (.files, .txt, .pyt.log); the .files sha256 = d79dfdf0733c... = the merge round's comm_list.txt (187 members, identical after CR strip); the record's ids = S81-07_comm/base_failed_ids.txt (12 ids, the CRLF hygiene class).
- comm -13 (sorted base, head FAILED ids) is NOT EMPTY:
  FAILED tests/test_inc_mon1_credential_health.py::test_y01_env_names_and_env_safety
  comm-head-03.log: AssertionError, base64(sha256(repr(sorted(_env_safety.CREDENTIALS_UNSET)))) 'KuyarpanjcDi...' != the pinned ENV_SAFETY_UNSET_B64 'p3FiYhXjh1kB...'. Cause: MON1 (#401, in M) pins a DIGEST of CREDENTIALS_UNSET; the unit's E1 line adds MEAS_ANTHROPIC_TEST_KEY, so the merged head fails this node deterministically: CI will be red.
- M-3 did not catch it (the node is not among the 18 pins). It is outside M-3 (i)-(iv) as written (consequence (i) covers the harness's refused names, not another suite's digest pin) and its fix lies in a file outside the M-2 footprint: by M-7 it needs an orchestrator ruling (for example an E-row re-pinning ENV_SAFETY_UNSET_B64 in tests/test_inc_mon1_credential_health.py to the new digest, then that file and the comm set re-run).
- comm -23 empty. comm_wait.txt (32 lines) and comm_done.txt are present (written by the comm agent).
- Head [pyt] lines (the base lines are in S81-07_comm/drv_base.out): head-01 OK, -02 OK, -03 FAIL (the new node + a base node), -04 OK, -05 FAIL, -06 FAIL, -07 FAIL, -08 OK (bound 1200 each); every FAIL chunk's other ids are in the base record.

## (6) CLAUDE.md block and the PR body
- CLAUDE.md block: the m5 / m1 / m6 / m3 sentences match the code (KNOB_VALUE_LABEL, _is_loopback_name, the write_tail failed arm, n_failed); the dry-run figures 622 / 1.44, 200 / 0.26, 300 / 3.61, 80 / 1.33 = measured; ASCII (max byte 121).
- PR body: 24,802 B, 0 CR, one non-ASCII line (the attribution). Checked correct: the dry-run figures, the 3.00 code-default live-cap label, the template copy, the footprint, the merge parents, the fix sentences. WRONG or STALE (MINOR, docs):
  d1 MERGE section: "markers in comm_wait.txt" although the merge report says that round never wrote comm_wait.txt (it exists now only from the later comm agent); and the comm set is no longer NOT MEASURED: the body must carry this round's figures (187 members; base 12 / head 13; comm -13 = the MON1 y01 node) once ruled.
  d2 "What this is": "next: TWO adversaries (correctness; security-and-spend)" is stale (the GREEN round's wording).
  d3 the 18 pins and the fourteen client fences stand NOT MEASURED at dca3a360 in the body (the comm agent's folder holds pin logs for 7 of them; not verified by me).

## MINORS (stated limits by default, LC-4)
- m-a N08 survives: results.json tail_n_censored is pinned only at 0 (R95); the REPORT line's censored count is pinned (N10 killed), the results.json figure is not.
- m-b N20 survives: the report stage's post-import refused-env re-scan is unpinned (the report stage reads no key and sends nothing: defense in depth).
- m-c N21 survives: a non-finite span on a hand-edited ledger tail line is accepted on read-back (only a corrupted ledger reaches it).
- m-d the PR body items d1-d3.

## NOT MEASURED by me
- The 18 pins and the fourteen client fences at dca3a360 (budget; the comm agent's lane runs them).

## Live and secrets
No live run, no network call beyond git fetch origin main, no key or dotenv file read, no production value; the credential variable was set only to a run-time test canary inside the probes. Scratch worktree removed with git worktree remove --force; absent from git worktree list; the path is gone.
