# S81-10 FRAGRANCE-ONLY-GATE: FIX ROUND 1 report (Opus 5.5 fix agent; written through the shell)

- unit: S81-10 FRAGRANCE-ONLY-GATE (lane A backend, FOCUS; ENABLE_FRAGRANCE_ONLY_GATE default OFF, read per call)
- worktree C:/Users/SynAckITPC/Documents/AI/sc-s81-s10, branch feature/s81-s10-fragrance-only-gate; start HEAD 0523a06fe25e4df3682b26a83daa72bf2f2ee543 (verified, `git status --short` empty, no mutation lock); new HEAD 0e4b69e8065654293db548f0c114ff09714cf4e6
- rulings followed: RULINGS_FIX1_S81_10 'Procedure for the fix agent (final)' steps 1-4, in order; s81-common; GATE_S81_10; RULINGS_S81_10
- RED files: tests/test_s81_s10_fragrance_gate.py d988882a08ac3c57624b8d1ef89492b5a8d0d7ed203a73fa9cfb76fbadad12ac -> fe2032237c2a09564f23c8595378939b339afb69ba0e84eb0d269961637ff28e (EK1, the ONE sanctioned amendment; git diff +30 / -0); tests/fixtures/s81_s10_flag_off_golden.json 159fadb8544f4b44f7f20f7ab1d6a27b0fd6f603592e580607ecfc391e30eb1a (byte-identical)
- git blob ids at the new HEAD: RED file 3857c91e02cfd5cac120e20f09b774ee49d3e819; golden 18bd5ff2e1005f84332ee315789ac079ff8bad79

## Commit
```
0e4b69e8065654293db548f0c114ff09714cf4e6
fix(category-gate): S81-10 fix round 1 (EK1 golden clock, F1-2 stub rewrite, gate rows)

EK1 (RULINGS_FIX1_S81_10 F1-1), the one sanctioned amendment of the frozen RED file
tests/test_s81_s10_fragrance_gate.py: _run_golden runs the real smart-pick formatter
with the clock its function-local import reads frozen at the record instant
2026-11-02T08:30:00Z, so P01 / R54 no longer depend on the wall clock (the golden
fixture is byte-identical; green at the real clock and at +10 d / +400 d).

F1-2: under ENABLE_FRAGRANCE_ONLY_GATE the GC-1 form override also rewrites the
overridden product's own stub to fragrances on both orchestrator paths
(category_gate.apply_form_override_stubs), so the B1 per-product categories agree
with category_used. It runs only when a route passed its decision (never flag OFF).

Gate rows (13 -> 31 nodes): F1-2, F1-4 (D3 / GC-2), F1-5, F1-6 (A14, A17, A29) and
the ported end-to-end QB02 / QB03 / QB04 rows; F1-7 drops two static asserts.
CLAUDE.md: the S81-10 row's stated limits and the admin-bypass condition.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>


 CLAUDE.md                                     |   2 +-
 app/services/category_gate.py                 |  15 ++
 app/services/structured_comparison_service.py |   4 +
 tests/test_s81_s10_fragrance_gate.py          |  30 +++
 tests/test_s81_s10_gate_rows.py               | 358 +++++++++++++++++++++++++-
 5 files changed, 402 insertions(+), 7 deletions(-)
```

## Files (sha256 of the bytes on disk; before = the 0523a06f working copy; numstat vs 0523a06f)
```
path	sha256_before	sha256_after	added	deleted	bytes	crlf	bare_lf	added_gt127	file_gt127
app/services/category_gate.py	4bc821f4ae9333b332e814d93f98341c35a756a0977f75cc40c7f11d7ce4c026	9b2d6cc3188b26657c6dc2816f9f3da6f0f5fb7ec76295c1f3af7cc8725d2589	15	0	34377	0	754	0	0
app/services/structured_comparison_service.py	dcdbf6804ac6af4ed18dfe8a5c7618faf01f4392bb8b6222fe4394502397c833	eb0beae729214847ca47f88910864131dbbce27e19483bcf22a81c299ba1ff62	4	0	552747	9895	0	0	3006
tests/test_s81_s10_fragrance_gate.py	d988882a08ac3c57624b8d1ef89492b5a8d0d7ed203a73fa9cfb76fbadad12ac	fe2032237c2a09564f23c8595378939b339afb69ba0e84eb0d269961637ff28e	30	0	111629	0	2398	0	0
tests/test_s81_s10_gate_rows.py	5335af551053c6b962637137d3fba4872c0bd8f7df0e753decddbfa37c4c0a1e	4d44606eac7d6d83f981ff05d986dcf4e73f332a26a42104badfd60dac5a5572	352	6	35758	0	647	0	0
CLAUDE.md	75b64dee9f3dac91c65dee0f0f48eea3eabb8f543e99fd019fb9e82006c4d63f	0d1f902651c4ca951ab9a59bb0ddb950855a453e4bcef4d5e261e7ec471b81af	1	1	581759	996	0	0	3937
tests/fixtures/s81_s10_flag_off_golden.json	159fadb8544f4b44f7f20f7ab1d6a27b0fd6f603592e580607ecfc391e30eb1a	159fadb8544f4b44f7f20f7ab1d6a27b0fd6f603592e580607ecfc391e30eb1a	0	0	17123	0	751	0	0
```

## Every run (from the pyt ledger; the [hermeticity] / [netguard] / [s10-clock-probe] lines from each log)
```
[pyt] tag=s10fix1-probe-stubs start=2026-11-02 14:41:46 end=2026-11-02 14:41:50 elapsed=4s bound=600s status=OK rc=0
    summary: 1 passed, 10 warnings in 2.60s
    [hermeticity] sentinel checked 1 test(s)
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10fix1-ek1-red-real start=2026-11-02 14:45:34 end=2026-11-02 14:45:39 elapsed=6s bound=600s status=FAIL rc=1
    summary: 10 failed, 130 deselected, 11 warnings in 4.75s
    [hermeticity] sentinel checked 10 test(s)
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10fix1-ek1-red-p10 start=2026-11-02 14:46:13 end=2026-11-02 14:46:20 elapsed=6s bound=600s status=FAIL rc=1
    summary: 10 failed, 130 deselected, 11 warnings in 5.21s
    [hermeticity] sentinel checked 10 test(s)
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10fix1-gaterows-red start=2026-11-02 14:50:23 end=2026-11-02 14:50:28 elapsed=4s bound=600s status=FAIL rc=1
    summary: 2 failed, 29 passed, 10 warnings in 3.54s
    [hermeticity] sentinel checked 31 test(s)
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10fix1-ek1-green-real start=2026-11-02 14:51:19 end=2026-11-02 14:51:23 elapsed=4s bound=600s status=OK rc=0
    summary: 10 passed, 130 deselected, 11 warnings in 3.03s
    [hermeticity] sentinel checked 10 test(s)
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10fix1-ek1-green-p10 start=2026-11-02 14:51:32 end=2026-11-02 14:51:36 elapsed=4s bound=600s status=OK rc=0
    summary: =============== 10 passed, 130 deselected, 11 warnings in 3.14s ===============
    [s10-clock-probe] wall clock shifted by 10.0 day(s)
    [hermeticity] sentinel checked 10 test(s)
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10fix1-ek1-green-p400 start=2026-11-02 14:51:36 end=2026-11-02 14:51:40 elapsed=4s bound=600s status=OK rc=0
    summary: =============== 10 passed, 130 deselected, 11 warnings in 3.14s ===============
    [s10-clock-probe] wall clock shifted by 400.0 day(s)
    [hermeticity] sentinel checked 10 test(s)
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10fix1-gaterows-green start=2026-11-02 14:52:19 end=2026-11-02 14:52:23 elapsed=4s bound=600s status=OK rc=0
    summary: 31 passed, 10 warnings in 3.00s
    [hermeticity] sentinel checked 31 test(s)
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10fix1-red-off-pre start=2026-11-02 14:52:33 end=2026-11-02 14:52:39 elapsed=6s bound=600s status=OK rc=0
    summary: 140 passed, 11 warnings in 4.75s
    [hermeticity] sentinel checked 140 test(s)
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10fix1-gaterows-green2 start=2026-11-02 14:54:02 end=2026-11-02 14:54:06 elapsed=4s bound=600s status=OK rc=0
    summary: 31 passed, 10 warnings in 3.02s
    [hermeticity] sentinel checked 31 test(s)
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10fix1-mut-f12-m1 start=2026-11-02 14:54:15 end=2026-11-02 14:54:20 elapsed=5s bound=600s status=FAIL rc=1
    summary: 2 failed, 29 passed, 10 warnings in 4.02s
    [hermeticity] sentinel checked 31 test(s)
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10fix1-mut-f12-m2 start=2026-11-02 14:54:20 end=2026-11-02 14:54:26 elapsed=6s bound=600s status=FAIL rc=1
    summary: 2 failed, 29 passed, 10 warnings in 3.78s
    [hermeticity] sentinel checked 31 test(s)
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10fix1-mut-f12-m3 start=2026-11-02 14:54:26 end=2026-11-02 14:54:31 elapsed=5s bound=600s status=FAIL rc=1
    summary: 2 failed, 29 passed, 10 warnings in 3.73s
    [hermeticity] sentinel checked 31 test(s)
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10fix1-mut-f12-m1s start=2026-11-02 14:54:31 end=2026-11-02 14:54:36 elapsed=5s bound=600s status=FAIL rc=1
    summary: 1 failed, 30 passed, 10 warnings in 3.78s
    [hermeticity] sentinel checked 31 test(s)
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10fix1-mut-f12-m1t start=2026-11-02 14:54:36 end=2026-11-02 14:54:42 elapsed=5s bound=600s status=FAIL rc=1
    summary: 1 failed, 30 passed, 10 warnings in 3.79s
    [hermeticity] sentinel checked 31 test(s)
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10fix1-mut-f12-m2b start=2026-11-02 14:54:42 end=2026-11-02 14:54:47 elapsed=6s bound=600s status=FAIL rc=1
    summary: 2 failed, 29 passed, 10 warnings in 4.47s
    [hermeticity] sentinel checked 31 test(s)
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10fix1-mut-a02 start=2026-11-02 14:54:48 end=2026-11-02 14:54:53 elapsed=5s bound=600s status=FAIL rc=1
    summary: 1 failed, 30 passed, 10 warnings in 3.79s
    [hermeticity] sentinel checked 31 test(s)
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10fix1-mut-a03 start=2026-11-02 14:54:53 end=2026-11-02 14:54:57 elapsed=5s bound=600s status=FAIL rc=1
    summary: 1 failed, 30 passed, 10 warnings in 3.81s
    [hermeticity] sentinel checked 31 test(s)
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10fix1-mut-a11 start=2026-11-02 14:54:58 end=2026-11-02 14:55:04 elapsed=6s bound=600s status=FAIL rc=1
    summary: 2 failed, 29 passed, 10 warnings in 3.79s
    [hermeticity] sentinel checked 31 test(s)
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10fix1-mut-a12 start=2026-11-02 14:55:04 end=2026-11-02 14:55:09 elapsed=6s bound=600s status=FAIL rc=1
    summary: 1 failed, 30 passed, 10 warnings in 4.61s
    [hermeticity] sentinel checked 31 test(s)
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10fix1-mut-a14 start=2026-11-02 14:55:09 end=2026-11-02 14:55:14 elapsed=5s bound=600s status=FAIL rc=1
    summary: 1 failed, 30 passed, 10 warnings in 3.99s
    [hermeticity] sentinel checked 31 test(s)
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10fix1-mut-a17 start=2026-11-02 14:55:15 end=2026-11-02 14:55:20 elapsed=5s bound=600s status=FAIL rc=1
    summary: 1 failed, 30 passed, 10 warnings in 4.41s
    [hermeticity] sentinel checked 31 test(s)
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10fix1-mut-a29 start=2026-11-02 14:55:20 end=2026-11-02 14:55:26 elapsed=6s bound=600s status=FAIL rc=1
    summary: 1 failed, 30 passed, 10 warnings in 4.79s
    [hermeticity] sentinel checked 31 test(s)
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10fix1-mut-qm09 start=2026-11-02 14:55:26 end=2026-11-02 14:55:31 elapsed=5s bound=600s status=FAIL rc=1
    summary: 1 failed, 30 passed, 10 warnings in 3.73s
    [hermeticity] sentinel checked 31 test(s)
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10fix1-mut-qm12 start=2026-11-02 14:55:31 end=2026-11-02 14:55:35 elapsed=5s bound=600s status=FAIL rc=1
    summary: 2 failed, 29 passed, 10 warnings in 3.72s
    [hermeticity] sentinel checked 31 test(s)
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10fix1-red-off-d0 start=2026-11-02 14:57:52 end=2026-11-02 14:58:00 elapsed=8s bound=600s status=OK rc=0
    summary: ====================== 140 passed, 11 warnings in 7.01s =======================
    [s10-clock-probe] wall clock shifted by 0.0 day(s)
    [hermeticity] sentinel checked 140 test(s)
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10fix1-red-off-d10 start=2026-11-02 14:58:01 end=2026-11-02 14:58:08 elapsed=7s bound=600s status=OK rc=0
    summary: ====================== 140 passed, 11 warnings in 4.62s =======================
    [s10-clock-probe] wall clock shifted by 10.0 day(s)
    [hermeticity] sentinel checked 140 test(s)
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10fix1-red-off-d400 start=2026-11-02 14:58:08 end=2026-11-02 14:58:15 elapsed=7s bound=600s status=OK rc=0
    summary: ====================== 140 passed, 11 warnings in 5.88s =======================
    [s10-clock-probe] wall clock shifted by 400.0 day(s)
    [hermeticity] sentinel checked 140 test(s)
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10fix1-red-on-d0 start=2026-11-02 14:58:16 end=2026-11-02 14:58:21 elapsed=6s bound=600s status=OK rc=0
    summary: ====================== 140 passed, 11 warnings in 4.84s =======================
    [s10-clock-probe] wall clock shifted by 0.0 day(s)
    [hermeticity] sentinel checked 140 test(s)
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10fix1-red-on-d10 start=2026-11-02 14:58:22 end=2026-11-02 14:58:29 elapsed=7s bound=600s status=OK rc=0
    summary: ====================== 140 passed, 11 warnings in 6.06s =======================
    [s10-clock-probe] wall clock shifted by 10.0 day(s)
    [hermeticity] sentinel checked 140 test(s)
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10fix1-red-on-d400 start=2026-11-02 14:58:30 end=2026-11-02 14:58:36 elapsed=6s bound=600s status=OK rc=0
    summary: ====================== 140 passed, 11 warnings in 4.86s =======================
    [s10-clock-probe] wall clock shifted by 400.0 day(s)
    [hermeticity] sentinel checked 140 test(s)
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10fix1-gaterows-on start=2026-11-02 14:58:48 end=2026-11-02 14:58:52 elapsed=4s bound=600s status=OK rc=0
    summary: 31 passed, 10 warnings in 3.52s
    [hermeticity] sentinel checked 31 test(s)
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10fix1-gaterows-d400 start=2026-11-02 14:58:53 end=2026-11-02 14:59:00 elapsed=7s bound=600s status=OK rc=0
    summary: ======================= 31 passed, 10 warnings in 6.00s =======================
    [s10-clock-probe] wall clock shifted by 400.0 day(s)
    [hermeticity] sentinel checked 31 test(s)
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10fix1-ciorder start=2026-11-02 14:59:10 end=2026-11-02 15:00:34 elapsed=84s bound=1200s status=OK rc=0
    summary: ========= 2461 passed, 4 deselected, 313 warnings in 82.18s (0:01:22) =========
    [hermeticity] sentinel checked 2461 test(s)
    [netguard] blocked 89 attempt(s) from 34 node(s)
[pyt] tag=s10f1c-00 start=2026-11-02 15:01:23 end=2026-11-02 15:02:38 elapsed=76s bound=1200s status=OK rc=0
    summary: 1295 passed, 12 warnings in 74.70s (0:01:14)
    [hermeticity] sentinel checked 1295 test(s)
    [netguard] blocked 50 attempt(s) from 11 node(s)
[pyt] tag=s10f1c-01 start=2026-11-02 15:02:39 end=2026-11-02 15:03:14 elapsed=35s bound=1200s status=OK rc=0
    summary: 548 passed, 1 skipped, 11 warnings in 33.85s
    [hermeticity] sentinel checked 548 test(s)
    [netguard] blocked 56 attempt(s) from 19 node(s)
[pyt] tag=s10f1c-02 start=2026-11-02 15:03:14 end=2026-11-02 15:04:02 elapsed=48s bound=1200s status=OK rc=0
    summary: 1570 passed, 5 deselected, 13 warnings in 46.62s
    [hermeticity] sentinel checked 1570 test(s)
    [netguard] blocked 19 attempt(s) from 4 node(s)
[pyt] tag=s10f1c-03 start=2026-11-02 15:04:02 end=2026-11-02 15:04:39 elapsed=37s bound=1200s status=FAIL rc=1
    summary: 2 failed, 637 passed, 16 warnings in 35.51s
    [hermeticity] sentinel checked 639 test(s)
    [netguard] blocked 154 attempt(s) from 19 node(s)
[pyt] tag=s10f1c-04 start=2026-11-02 15:04:40 end=2026-11-02 15:06:25 elapsed=106s bound=1200s status=OK rc=0
    summary: 818 passed, 8 deselected, 10 warnings in 104.14s (0:01:44)
    [hermeticity] sentinel checked 818 test(s)
    [netguard] blocked 38 attempt(s) from 7 node(s)
[pyt] tag=s10f1c-05 start=2026-11-02 15:06:25 end=2026-11-02 15:09:29 elapsed=183s bound=1200s status=OK rc=0
    summary: 3340 passed, 12 warnings in 180.74s (0:03:00)
    [hermeticity] sentinel checked 3340 test(s)
    [netguard] blocked 43 attempt(s) from 11 node(s)
[pyt] tag=s10f1c-06 start=2026-11-02 15:09:29 end=2026-11-02 15:10:28 elapsed=59s bound=1200s status=OK rc=0
    summary: 414 passed, 2 skipped, 12 deselected, 16 warnings in 55.95s
    [hermeticity] sentinel checked 415 test(s)
    [netguard] blocked 128 attempt(s) from 47 node(s)
[pyt] tag=s10f1c-07 start=2026-11-02 15:10:28 end=2026-11-02 15:10:59 elapsed=31s bound=1200s status=OK rc=0
    summary: 946 passed, 6 deselected, 13 warnings in 30.15s
    [hermeticity] sentinel checked 946 test(s)
    [netguard] blocked 84 attempt(s) from 32 node(s)
[pyt] tag=s10fix1-secretscan start=2026-11-02 15:11:39 end=2026-11-02 15:11:47 elapsed=8s bound=600s status=OK rc=0
    summary: 31 passed, 1 warning in 7.07s
    [hermeticity] sentinel checked 31 test(s)
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10fix1-red-off-final start=2026-11-02 15:11:55 end=2026-11-02 15:12:04 elapsed=9s bound=600s status=OK rc=0
    summary: 140 passed, 11 warnings in 7.80s
    [hermeticity] sentinel checked 140 test(s)
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10fix1-red-on-final start=2026-11-02 15:12:04 end=2026-11-02 15:12:09 elapsed=5s bound=600s status=OK rc=0
    summary: 140 passed, 11 warnings in 4.16s
    [hermeticity] sentinel checked 140 test(s)
    [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10fix1-gaterows-final start=2026-11-02 15:12:10 end=2026-11-02 15:12:13 elapsed=4s bound=600s status=OK rc=0
    summary: 31 passed, 10 warnings in 2.82s
    [hermeticity] sentinel checked 31 test(s)
    [netguard] blocked 0 attempt(s) from 0 node(s)
```

## Mutation table (15 mutants; byte copies in place, the lock held, restored and sha-verified; harness mut_harness.py)
```
id	verdict	file	killing rows (failed nodes)	error types	[pyt]
F12-M1	KILLED	app/services/category_gate.py	test_f1_2_form_override_rewrites_the_overridden_stub[sync], test_f1_2_form_override_rewrites_the_overridden_stub[stream]	AssertionError	[pyt] tag=s10fix1-mut-f12-m1 start=2026-11-02 14:54:15 end=2026-11-02 14:54:20 elapsed=5s bound=600s status=FAIL rc=1
F12-M2	KILLED	app/services/category_gate.py	test_f1_2_form_override_rewrites_the_overridden_stub[sync], test_f1_2_form_override_rewrites_the_overridden_stub[stream]	AssertionError	[pyt] tag=s10fix1-mut-f12-m2 start=2026-11-02 14:54:20 end=2026-11-02 14:54:26 elapsed=6s bound=600s status=FAIL rc=1
F12-M3	KILLED	app/services/category_gate.py	test_f1_2_form_override_rewrites_the_overridden_stub[sync], test_f1_2_form_override_rewrites_the_overridden_stub[stream]	AssertionError	[pyt] tag=s10fix1-mut-f12-m3 start=2026-11-02 14:54:26 end=2026-11-02 14:54:31 elapsed=5s bound=600s status=FAIL rc=1
F12-M1s	KILLED	app/services/structured_comparison_service.py	test_f1_2_form_override_rewrites_the_overridden_stub[sync]	AssertionError	[pyt] tag=s10fix1-mut-f12-m1s start=2026-11-02 14:54:31 end=2026-11-02 14:54:36 elapsed=5s bound=600s status=FAIL rc=1
F12-M1t	KILLED	app/services/structured_comparison_service.py	test_f1_2_form_override_rewrites_the_overridden_stub[stream]	AssertionError	[pyt] tag=s10fix1-mut-f12-m1t start=2026-11-02 14:54:36 end=2026-11-02 14:54:42 elapsed=5s bound=600s status=FAIL rc=1
F12-M2b	KILLED	app/services/category_gate.py	test_f1_2_form_override_rewrites_the_overridden_stub[sync], test_f1_2_form_override_rewrites_the_overridden_stub[stream]	AssertionError	[pyt] tag=s10fix1-mut-f12-m2b start=2026-11-02 14:54:42 end=2026-11-02 14:54:47 elapsed=6s bound=600s status=FAIL rc=1
A02	KILLED	app/api/text_routes.py	test_qb03_admin_key_bypass_get_and_stream[get]	AssertionError	[pyt] tag=s10fix1-mut-a02 start=2026-11-02 14:54:48 end=2026-11-02 14:54:53 elapsed=5s bound=600s status=FAIL rc=1
A03	KILLED	app/api/text_routes.py	test_qb03_admin_key_bypass_get_and_stream[stream]	AssertionError	[pyt] tag=s10fix1-mut-a03 start=2026-11-02 14:54:53 end=2026-11-02 14:54:57 elapsed=5s bound=600s status=FAIL rc=1
A11	KILLED	app/services/category_gate.py	test_f1_4_d3_house_pair_no_chip_refused_chip_proceeds, test_f1_4_qb06_camera_house_pair_refused_and_counted	AssertionError	[pyt] tag=s10fix1-mut-a11 start=2026-11-02 14:54:58 end=2026-11-02 14:55:04 elapsed=6s bound=600s status=FAIL rc=1
A12	KILLED	app/services/category_gate.py	test_f1_5_other_chip_refused_with_one_a2b_call	AssertionError	[pyt] tag=s10fix1-mut-a12 start=2026-11-02 14:55:04 end=2026-11-02 14:55:09 elapsed=6s bound=600s status=FAIL rc=1
A14	KILLED	app/services/category_gate.py	test_f1_6_retry_after_rounds_up_a_fractional_second	AssertionError	[pyt] tag=s10fix1-mut-a14 start=2026-11-02 14:55:09 end=2026-11-02 14:55:14 elapsed=5s bound=600s status=FAIL rc=1
A17	KILLED	app/services/category_gate.py	test_f1_6_camera_vision_texts_carry_the_brand	AssertionError	[pyt] tag=s10fix1-mut-a17 start=2026-11-02 14:55:15 end=2026-11-02 14:55:20 elapsed=5s bound=600s status=FAIL rc=1
A29	KILLED	app/services/category_gate.py	test_f1_6_exemption_allow_list_matches_any_case	AssertionError	[pyt] tag=s10fix1-mut-a29 start=2026-11-02 14:55:20 end=2026-11-02 14:55:26 elapsed=6s bound=600s status=FAIL rc=1
QM09	KILLED	app/api/image_routes.py	test_qb04_camera_budget_anon_metering_on_refunds_once	AssertionError	[pyt] tag=s10fix1-mut-qm09 start=2026-11-02 14:55:26 end=2026-11-02 14:55:31 elapsed=5s bound=600s status=FAIL rc=1
QM12	KILLED	app/api/image_routes.py	test_f1_4_qb06_camera_house_pair_refused_and_counted, test_qb02_camera_post_resolve_counted_once_refunded_once	AssertionError	[pyt] tag=s10fix1-mut-qm12 start=2026-11-02 14:55:31 end=2026-11-02 14:55:35 elapsed=5s bound=600s status=FAIL rc=1
```
- F12-M1 (app/services/category_gate.py): F1-2 stub rewrite dropped
- F12-M2 (app/services/category_gate.py): F1-2 applied to the wrong product (the partner)
- F12-M3 (app/services/category_gate.py): F1-2 applied regardless of the override flag
- F12-M1s (app/services/structured_comparison_service.py): F1-2 call dropped on the sync path only
- F12-M1t (app/services/structured_comparison_service.py): F1-2 call dropped on the stream path only
- F12-M2b (app/services/category_gate.py): F1-2 applied to the first product always
- A02 (app/api/text_routes.py): GET admin bypass check removed (= QM01)
- A03 (app/api/text_routes.py): stream admin bypass check removed (= QM02)
- A11 (app/services/category_gate.py): D3 reverted: evidence proceeds before the no-chip resolver category
- A12 (app/services/category_gate.py): an 'other' chip treated as a real chip (a second A2b)
- A14 (app/services/category_gate.py): retry_after floor instead of ceil
- A17 (app/services/category_gate.py): vision texts drop the brand
- A29 (app/services/category_gate.py): allow-list match case-sensitive
- QM09 (app/api/image_routes.py): camera budget exit without the anon refund
- QM12 (app/api/image_routes.py): camera post-resolve arm counts the refusal again
The exact search / replace strings (for the re-verifier) are the MUTANTS list of C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/fe82d828-54b9-4af1-9c1d-685173488382/scratchpad/S81-10_fix1\mut_harness.py; manifest of the four touched files before / after: app/api/image_routes.py a5a5995a75cbcd488fc1a59f5164a2c2ce7b21da96093386e857ec3f684ad5e8 a5a5995a75cbcd488fc1a59f5164a2c2ce7b21da96093386e857ec3f684ad5e8 SAME | app/api/text_routes.py 8701a93f6cac1e8ca786ee50cb0c09232c8640f07dd31cccdcafd48c62c914ab 8701a93f6cac1e8ca786ee50cb0c09232c8640f07dd31cccdcafd48c62c914ab SAME | app/services/category_gate.py 9b2d6cc3188b26657c6dc2816f9f3da6f0f5fb7ec76295c1f3af7cc8725d2589 9b2d6cc3188b26657c6dc2816f9f3da6f0f5fb7ec76295c1f3af7cc8725d2589 SAME | app/services/structured_comparison_service.py eb0beae729214847ca47f88910864131dbbce27e19483bcf22a81c299ba1ff62 eb0beae729214847ca47f88910864131dbbce27e19483bcf22a81c299ba1ff62 SAME

## Comm subset (LC-6)
- list: the 192 of the 425 files of specs/S81_10_COMM_SET.txt whose text references structured_comparison_service (grep at the worktree bytes): C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/fe82d828-54b9-4af1-9c1d-685173488382/scratchpad/S81-10_fix1\comm_subset.txt
- base: the cached record at 6c14ac95 (336233f0....txt, 6 ids) filtered to the subset's files: ['tests/test_page_scraping.py::TestFetchPagePriceJsonLD::test_jsonld_nested_offers_picks_lowest', 'tests/test_page_scraping.py::TestFetchPagePriceOpenGraph::test_og_meta_extraction']
- HEAD failures: ['tests/test_page_scraping.py::TestFetchPagePriceJsonLD::test_jsonld_nested_offers_picks_lowest', 'tests/test_page_scraping.py::TestFetchPagePriceOpenGraph::test_og_meta_extraction']
- branch-only-new (comm -13): EMPTY ; base-only (comm -23): none

## Notes (running log)
# S81-10 FIX1 notes (Opus 5.5 fix agent)
- 14:31:10 start. W=sc-s81-s10 HEAD 0523a06fe25e4df3682b26a83daa72bf2f2ee543 branch feature/s81-s10-fragrance-only-gate; status 0 lines; no mutation lock.
- RED file d988882a08ac3c57624b8d1ef89492b5a8d0d7ed203a73fa9cfb76fbadad12ac (110434 B, LF, 0 non-ASCII); golden 159fadb8544f4b44f7f20f7ab1d6a27b0fd6f603592e580607ecfc391e30eb1a (17123 B, LF); gate rows 5335af551053c6b962637137d3fba4872c0bd8f7df0e753decddbfa37c4c0a1e (15630 B, LF).
- eol: category_gate.py / RED / golden / gate rows = i/lf w/lf; scs.py, home_routes.py, CLAUDE.md = i/lf w/crlf (autocrlf true).
- 14:41 probe_stubs (temporary tests/test_zz_s10fix1_probe.py, deleted after use): stubs: 'Kerastase Genesis Hair Mist' haircare, 'Dior Sauvage EDT' fragrances, 'Kayali Vanilla 28' other, 'Gucci Dionysus'/'Prada Galleria'/'iPhone 15'/'Gucci Guilty' other; combined hm+edt -> haircare. At HEAD: hm/edt (chip or not) category_used fragrances, product_categories [haircare, fragrances] (B1 conflict, m5 confirmed); hm/kayali -> [haircare, other]; hm pair -> [haircare, haircare]; gucci/prada no chip -> refused fashion, 1 classify, 1 eval; chip fragrances -> proceeds 0 classify; iPhone pair chip 'other' -> refused electronics, 1 classify, 1 eval.
- Design EK1: FREEZE form (F1-1 primary). The golden echoes no raw created_at value (only the column name in select/order) so the relative form would also be allowed; freeze keeps the Harness rows byte-identical. _run_golden monkeypatches home_routes._format_updated_at with a wrapper that runs the REAL formatter while the stdlib attribute datetime.datetime (what its function-local import reads) is a subclass whose now() is 2026-11-02T08:30:00Z, restored after each call.
- Design F1-2: category_gate.apply_form_override_stubs(verdict, products): returns unless verdict.form_override; else every product whose own name carries a concentration / form word gets stub 'fragrances'; called on both orchestrator paths inside the gate block (before the B1 capture). Mutants: dropped / wrong product / regardless of the override flag.
- 14:45 EK1 RED at the real clock (before the amendment): [pyt] tag=s10fix1-ek1-red-real start=2026-11-02 14:45:34 end=2026-11-02 14:45:39 elapsed=6s bound=600s status=FAIL rc=1 -> 10 failed (P01 x5, R54 x5), every one AssertionError ('G10', 'body', ...): got '4d ago', golden '3d ago' (10 / 10 each).
- 14:46 control, the unamended nodes with the probe plugin shifting the wall clock +10 d: [pyt] tag=s10fix1-ek1-red-p10 start=2026-11-02 14:46:13 end=2026-11-02 14:46:20 elapsed=6s bound=600s status=FAIL rc=1 -> 10 failed with 'Older' (the shift reaches the formatter).
- 14:50 gate rows with the 18 new nodes at HEAD (app unchanged): [pyt] tag=s10fix1-gaterows-red start=2026-11-02 14:50:23 end=2026-11-02 14:50:28 elapsed=4s bound=600s status=FAIL rc=1 -> 2 failed (test_f1_2_form_override_rewrites_the_overridden_stub[sync|stream], AssertionError at ctx["product_categories"] == ["fragrances","fragrances"], part a), 29 passed (13 old + 16 new coverage rows green at HEAD by design). Temporary probe file removed before this run.
- 14:51 EK1 applied (+30 lines, 0 deleted; RED file 111,629 B, sha256 fe2032237c2a09564f23c8595378939b339afb69ba0e84eb0d269961637ff28e, LF, 0 non-ASCII). Ten nodes: real clock [pyt] tag=s10fix1-ek1-green-real start=2026-11-02 14:51:19 end=2026-11-02 14:51:23 elapsed=4s bound=600s status=OK rc=0 (10 passed); +10 d [pyt] tag=s10fix1-ek1-green-p10 start=2026-11-02 14:51:32 end=2026-11-02 14:51:36 elapsed=4s bound=600s status=OK rc=0 (10 passed); +400 d [pyt] tag=s10fix1-ek1-green-p400 start=2026-11-02 14:51:36 end=2026-11-02 14:51:40 elapsed=4s bound=600s status=OK rc=0 (10 passed).
- 14:52 F1-2 hunk applied (category_gate.apply_form_override_stubs + one call on each orchestrator path): gate rows [pyt] tag=s10fix1-gaterows-green start=2026-11-02 14:52:19 end=2026-11-02 14:52:23 elapsed=4s bound=600s status=OK rc=0 (31 passed).
- 14:54-14:55 mutation table (harness mut_harness.py, lock held, byte copies in place, gate rows file per mutant): 15 / 15 KILLED, each by its named row, every failure an AssertionError; manifest of the 4 touched files SAME before/after; lock removed. F12-M1 / M2 / M3 (+ M1s sync-only, M1t stream-only, M2b first-product) by test_f1_2; A02 / A03 by qb03[get] / [stream]; A11 by both f1_4 rows; A12 by f1_5; A14 / A17 / A29 by the f1_6 rows; QM09 by qb04 metering_on; QM12 by qb02 camera (+ f1_4 qb06). Table: mut_table.txt.
- 14:57-14:59 RED file 140 / 140 ambient OFF and ON at d0 / +10 / +400 (6 runs through the probe plugin; the d0 run = the real clock with a zero shift; plain runs without the plugin also green: s10fix1-red-off-pre 14:52); gate rows 31 / 31 ambient ON and at +400 d.
- 14:59-15:00 CI-order set (GREEN's 30 files, flag OFF): 2461 passed (= 2443 + the 18 new gate-row nodes), 4 deselected, 0 failed.
- CLAUDE.md: S81-10 row edited in place (1 line changed): F1-2 clause, the bypass condition (F1-12 m4), the canary pair (F1-13) + stream read (F1-14), the stated limits (F1-4 / F1-8 / F1-11 / F1-12 / F1-13 / F1-14); CRLF 996 / bare LF 0; bytes > 127 3937 before and after.
- Deviations (each with its reason):
  - DV1 F1-2 lives in a category_gate helper (apply_form_override_stubs) plus ONE call on each orchestrator path (scs +4 lines, category_gate +15): one logical app change on both paths; the helper keeps the per-product rule (a concentration / form word in the product's own name, the same expression post_resolve_refusal uses) beside its twin and gives the three ruled mutants a single site each. It runs inside the gate block after the GC-1 rewrite, whenever the override fired (also when category_used was already fragrances), so B1 agrees in every override case.
  - DV2 EK1 freeze mechanics: home_routes reads datetime through a function-local import (no module name, no now-seam), so _run_golden monkeypatches home_routes._format_updated_at with a wrapper that runs the REAL formatter while the stdlib attribute datetime.datetime is the record-instant subclass, restored in a finally after each call; nothing else in the scenario sees the frozen clock.
  - DV3 extra mutant variants beyond the ruled three F1-2 mutants (F12-M1s sync-only drop, F12-M1t stream-only drop, F12-M2b first product always) and the reversed F12_ONE pair in the F1-2 row (part b) that kills M2b; all KILLED.
  - DV4 the camera half of F1-4 is the ported QB06 (test_f1_4_qb06_camera_house_pair_refused_and_counted); QB05 (Half-B ON, stream) and QB01 (superseded by EK1) are not ported.
  - DV5 the RED-file runs at the three clocks go through the probe plugin (shift 0 / 10 / 400 days); the plain runs without the plugin are listed separately (s10fix1-red-off-pre, -final, -on-final).
- Open questions: Q1 confirm DV1 (the stub rewrite also when category_used was already fragrances); Q2 port QB05 at the rebase (S81-09's device debit rows RB10-7 b2 touch the same stream arm)?
- 15:01-15:11 comm SUBSET (192 of the 425 files reference structured_comparison_service; comm_subset.txt), driver comm_driver.py (= the GREEN comm_driver_head.py byte copy) launched ONCE, 8 chunks of <= 25, bound 1200, one pytest at a time: 00 1295 passed; 01 548 passed / 1 skipped; 02 1570 passed / 5 deselected; 03 2 failed / 637 passed; 04 818 passed / 8 deselected; 05 3340 passed; 06 414 passed / 2 skipped / 12 deselected; 07 946 passed / 6 deselected. HEAD failures = tests/test_page_scraping.py::TestFetchPagePriceJsonLD::test_jsonld_nested_offers_picks_lowest + ::TestFetchPagePriceOpenGraph::test_og_meta_extraction = exactly the cached base record's failures for these files (336233f0....txt filtered to the subset; GC-7); branch-only-new EMPTY; base-only none. The other four base ids (test_auth_interceptor x2, test_prompt_truth x2) are in files outside the subset.
- 15:11 tests/test_secret_scan_static.py ALONE: 31 passed. 15:11-15:12 final plain runs: RED OFF 140, RED ON 140, gate rows 31 (no probe plugin).
- 15:13 ONE commit through the hook (git add + git commit -F <msg> -- <5 paths>; hook: All checks passed!): 0e4b69e8065654293db548f0c114ff09714cf4e6 "fix(category-gate): S81-10 fix round 1 (EK1 golden clock, F1-2 stub rewrite, gate rows)", 5 files, 402 insertions, 7 deletions; trailer Co-Authored-By: Claude Opus 5.5. git status --short empty; git diff HEAD empty. Committed blobs: RED file sha256 fe2032237c2a09564f23c8595378939b339afb69ba0e84eb0d269961637ff28e (git blob 3857c91e02cfd5cac120e20f09b774ee49d3e819); golden 159fadb8544f4b44f7f20f7ab1d6a27b0fd6f603592e580607ecfc391e30eb1a (blob 18bd5ff2e1005f84332ee315789ac079ff8bad79, unchanged).
- 15:14 PR body patched in place (<scratchpad>/S81-10_green/PR_BODY.md): 22,976 -> 25,290 bytes (<= 25,600), non-ASCII 494 (the [NATIVE READ] Arabic column + the attribution line, unchanged), LF; before f15118d13b82c08397c8e5f969ec440dde2cd0f6392520491716f795484c9131, after 745aa91deff14bf205f805ac5d6d3ffdfbe5e16043cb1cf2e276a886dc0297d3 (copies PR_BODY_before_fix1.md / PR_BODY_after_fix1.md; script patch_pr_body.py, values.json). Content: header HEAD; item 3 (F1-2); item 5 (the bypass condition, F1-12); the flag-OFF line (EK1); the files table; the requirement map; the Gates section (GREEN summary + the fix-round lines; GREEN's chunk lines moved to its report, LC-3); a new 'Fix round 1' section (EK1 with both blob shas, F1-2, F1-7, the rows, the mutants, the re-verifier line PENDING); stated limits L3 (F1-4 / F1-13), L4 (F1-8 m4), L5 (GR-9 a), L11 (F1-8 m6), C27 (F1-12 m9), F1-8 m7 / m10 / m11, F1-11 / F1-12 (QM10 / QM15, m5), F1-14; the cross-unit S81-11 line (F1-14); the canary (F1-13 pair, F1-14 read); the GREEN deviations compressed (ruled ACCEPTED).
- COUNTS: RED file 140 nodes (99 RED + 41 PIN, the node set unchanged by EK1): 140 / 140 ambient OFF and ON at the real clock, +10 d and +400 d, and in the final plain runs; gate rows 13 -> 31 (new: F1-2 x2, F1-4 x2, F1-5 x1, F1-6 x3, QB02 x5, QB03 x3, QB04 x2 = 18); mutants 15 / 15 KILLED; CI-order 2461 passed / 4 deselected; comm subset 192 files, 8 chunks, branch-only-new EMPTY; secret scan 31 passed.
- NOT MEASURED / NOT RUN: the fourteen client fences (not re-run by the ruling: no literal moved outside the orchestrator block; the rebase round runs them); the full 425-file comm set (the subset per the ruling; the full set at the rebase); the full jest suite (LC-7, the last round); the pre-commit hook test files (no .githooks change); a live Upstash MGET / EVAL; the B1 result gate on a DELIVERED compare (F1-2 measured at B1's capture, the ctx product_categories, plus result_gate.identity_coherence: the SvcHarness fetch ends every compare at INSUFFICIENT_DATA); the re-verifier (stage 2, not this agent).
- Hygiene: the temporary probe test file tests/test_zz_s10fix1_probe.py was deleted before the gate runs (never staged); .qa-mutation.lock created and removed by the harness; no pytest of mine left running; the probe plugin and every script live in this notes folder only.

## git status --short (after the commit)
```
(clean)
```

## Supporting files
- probe plugin (never committed): C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/fe82d828-54b9-4af1-9c1d-685173488382/scratchpad/S81-10_fix1\probe_plugin\s10_clock_probe.py sha256 c4daed824a5a48da45dda6b9da4ebb49fcb896e1dc769656d8b77cfb99845e0b
- PR body patched in place: <scratchpad>/S81-10_green/PR_BODY.md (25290 bytes); copies before / after and the patch script in C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/fe82d828-54b9-4af1-9c1d-685173488382/scratchpad/S81-10_fix1
