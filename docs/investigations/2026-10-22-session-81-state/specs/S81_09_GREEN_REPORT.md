# S81-09 DEVICE-QUOTA-RIYADH -- GREEN report

- Agent: GREEN, Opus 5.5 (claude-opus-5-5). Written THROUGH THE SHELL (compose.py run by the venv python; the harness refuses a subagent Write of a report .md).
- Worktree C:/Users/SynAckITPC/Documents/AI/sc-s81-s09, branch feature/s81-s09-device-quota-riyadh created from the detached base e7c81956f11749b1378aa449c4ac616c82bfe6a9; HEAD = e7c81956f11749b1378aa449c4ac616c82bfe6a9 (the base): the GREEN COMMIT IS BLOCKED. `git commit -- <13 paths>` through the hook was refused by its gitleaks step on ONE finding in the FROZEN RED file (generic-api-key, tests/test_s81_s09_device_quota.py:831, `[the synthetic share-token field: value elided for the docs hook, see the unit report]`). Not bypassed (no --no-verify), the frozen file not edited, .gitleaks.toml not touched. The 13 paths are left STAGED (git add); no push, no rebase, no PR.
- Measured fix for the ruling: the one-line amendment `[the synthetic share-token field: value elided for the docs hook, see the unit report]` -> sha256 551a3167ac54d1ef842f76d1603c05c3a7e404384f6f161bb33bc1c4fad6963f (87,175 bytes, ASCII, LF), 0 gitleaks findings with HEAD:.gitleaks.toml (the frozen bytes: 1), 193/193 OFF and ON as a temp probe copy (removed). Copy: <scratchpad>/S81-09_green/gitleaks/amended/test_s81_s09_device_quota.py; findings: <scratchpad>/S81-09_green/gitleaks/findings.json (redacted).
- Inputs read in full: s81-common.txt (incl. LC-1..LC-9, MOVING MAIN), PLAN_S81 (context, standing constraints, VERIFY quota bullets, M3, build/flip order, owner rulings), PLAN_S80 s0/s1, RULINGS_S81_09, GATE_S81_09 (re-read after GC-13 appeared at 17:43), S81_09_BRIEF, S81_09_RED_REPORT, the spec, the review, the RED file and the golden, the prototype diff (reference only, never applied).
- RED files re-hashed at the start and before the commit: tests/test_s81_s09_device_quota.py 843a6bab0215ca5289482a13f52646d9f9bbb0d334e4e5f78a2e9b1bd6c1ddae, tests/fixtures/s81_s09_flag_off_golden.json 02b29cc6d3a649324f71b27472ae135cc015ba39e9659b49c0306d1e249e6176 (both unchanged).

## Files (git diff --cached --numstat against the base, the commit being blocked; sha256 over the bytes on disk; before = the byte copies in <scratchpad>/S81-09_green_before/)

| file | lines | sha256 before | sha256 after |
|---|---|---|---|
| CLAUDE.md | +9 / -2 | bcfea87b5e622fd7d172c663ef95da0251b9fa51f5bd06b96b09ef78781b930a | 7403487481d6da9bab8ce04705b240fcfd6c04f4308e9915cb546c27de30b6ac |
| app/api/image_routes.py | +4 / -1 | 9795c3598672d4f19a4c91b3f7fefb6b639c4273256abb0065e5709f86ddbb0c | 717d1e5a05d455dceb66b8c0bc38806d74c7d39cb2c7d57fd25e845654959719 |
| app/api/text_routes.py | +14 / -3 | 9da410d6e57386d827c9fb11b10a3ac72a171d51510747f0d01565606d3bd416 | 767be4451ba9d89b4d656675f95c9cd59e98760a98a1496abe8b5446363d4652 |
| app/api/url_routes.py | +6 / -1 | bd8c6e47fe1a66ca2b268704ec27aa31cb9849b7bf0c492d157fe8a5181e65ff | c0ff7eb2f4e2c046fae7a59667238d69b63040bc0e2d9f88e23ec05a9f87b9b7 |
| app/api/usage_routes.py | +16 / -1 | 4d6caa3665b560885b5b229efeeef458efa4225109ee6bba4aca99d9b33b3769 | 8645776ffaffc56c69347712569a6e73797ca5d72b9b1e328615c20590565c98 |
| app/middleware/error_handler.py | +29 / -0 | 7e539cc7b17fcc6c9b982a2ebe4b212096af57deb8c1bded330eb57e5fc6d482 | 56332100e766db5f1bbe281540e17b657fe57715000b6502b6ed70a604f7961c |
| app/services/referral_service.py | +38 / -6 | 3e93b86ef4fc7e8a05b537f1dbd4843d7de61eee1e8e5d3c01fd53f729b4a737 | a928a6b65b69c29b808b652f1424860b750c115d724b4f77394e558bf9f11807 |
| app/services/usage_service.py | +478 / -12 | 6940fddd7f6cb2cc3bb78d9569251b24aee5e08b315f6dfcc16abc9949e7c89d | 570785b43ead06fa1c648cd7a4b27dabf17403c05386c7ffbae476279175e88c |
| tests/fixtures/s81_s09_flag_off_golden.json | +722 / -0 | 02b29cc6d3a649324f71b27472ae135cc015ba39e9659b49c0306d1e249e6176 | 02b29cc6d3a649324f71b27472ae135cc015ba39e9659b49c0306d1e249e6176 |
| tests/test_s81_s05_request_context.py | +27 / -4 | 71cdb79401ef03723282e259dbb259282b36d167692edf984f82d50830172d6f | 49d0b015fdd6fe53266fa9a15a0fdf377f706e6f106613afc86fd7483de8b5cc |
| tests/test_s81_s09_device_quota.py | +2068 / -0 | 843a6bab0215ca5289482a13f52646d9f9bbb0d334e4e5f78a2e9b1bd6c1ddae | 843a6bab0215ca5289482a13f52646d9f9bbb0d334e4e5f78a2e9b1bd6c1ddae |
| tests/test_s81_s09_gate_rows.py | +252 / -0 | (new file) | 992e2eab6af121dd180ff6408849378066c1f3f5c9a241fcc179fdaeaada153d |
| tests/test_s81_st1_usage_path_offloop.py | +15 / -7 | ad0b9726a5af043a20d280c4430f2231d28d5c67ed640b38e98534183bece1eb | 6380fff98dadf14856630060255da9ef52ef8816b1e8d0fb9b93e10f2f177b16 |

## Every run

- RED file, ambient flags OFF: `[pyt] tag=s09green-unit-off start=2026-10-29 17:20:47 end=2026-10-29 17:22:59 elapsed=133s bound=600s status=OK rc=0` -- 193 passed, 11 warnings in 120.32s (0:02:00); [hermeticity] sentinel checked 193 test(s); [netguard] blocked 0 attempt(s) from 0 node(s)
- RED file, both flags ON in the runner env: `[pyt] tag=s09green-unit-on start=2026-10-29 17:23:14 end=2026-10-29 17:23:55 elapsed=42s bound=600s status=OK rc=0` -- 193 passed, 11 warnings in 30.15s; [hermeticity] sentinel checked 193 test(s); [netguard] blocked 0 attempt(s) from 0 node(s)
- E-row probe: the BASE ST1 pin bytes (temp copy) + the 043 census vs the GREEN code: `[pyt] tag=s09green-erow-probe start=2026-10-29 17:25:49 end=2026-10-29 17:28:18 elapsed=149s bound=600s status=FAIL rc=1` -- 7 failed, 575 passed, 43 warnings in 138.93s (0:02:18); [hermeticity] sentinel checked 582 test(s); [netguard] blocked 0 attempt(s) from 0 node(s)
- ST1 pin file after E1/E2: `[pyt] tag=s09green-st1 start=2026-10-29 17:28:56 end=2026-10-29 17:30:18 elapsed=82s bound=600s status=OK rc=0` -- 531 passed, 21 warnings in 62.19s (0:01:02); [hermeticity] sentinel checked 531 test(s); [netguard] blocked 0 attempt(s) from 0 node(s)
- gate rows file: `[pyt] tag=s09green-gaterows start=2026-10-29 17:32:51 end=2026-10-29 17:33:42 elapsed=51s bound=600s status=OK rc=0` -- 20 passed, 10 warnings in 37.82s; [hermeticity] sentinel checked 20 test(s); [netguard] blocked 0 attempt(s) from 0 node(s)
- E3 probe: the BASE S05 pin bytes (temp copy) + the edited S05 file vs the GREEN code: `[pyt] tag=s09green-e3-probe start=2026-10-29 17:53:25 end=2026-10-29 17:54:31 elapsed=66s bound=600s status=FAIL rc=1` -- 1 failed, 351 passed, 111 warnings in 54.30s; [hermeticity] sentinel checked 352 test(s); [netguard] blocked 0 attempt(s) from 0 node(s)
- RED file + gate rows, final code, flags OFF: `[pyt] tag=s09green-unit-off2 start=2026-10-29 17:54:57 end=2026-10-29 17:55:46 elapsed=49s bound=600s status=OK rc=0` -- 213 passed, 11 warnings in 40.59s; [hermeticity] sentinel checked 213 test(s); [netguard] blocked 0 attempt(s) from 0 node(s)
- RED file + gate rows, final code, flags ON: `[pyt] tag=s09green-unit-on2 start=2026-10-29 17:56:07 end=2026-10-29 17:56:54 elapsed=47s bound=600s status=OK rc=0` -- 213 passed, 11 warnings in 32.96s; [hermeticity] sentinel checked 213 test(s); [netguard] blocked 0 attempt(s) from 0 node(s)
- gate-row sanity mutant G1 (the pause reads the lifetime slot): `[pyt] tag=s09green-mut-G1 start=2026-10-29 17:34:22 end=2026-10-29 17:35:07 elapsed=46s bound=600s status=FAIL rc=1` -- 1 failed, 19 deselected, 10 warnings in 36.77s; [hermeticity] sentinel checked 1 test(s); [netguard] blocked 0 attempt(s) from 0 node(s)
- gate-row sanity mutant G2 (no binding min in the consume result): `[pyt] tag=s09green-mut-G2 start=2026-10-29 17:35:11 end=2026-10-29 17:35:59 elapsed=48s bound=600s status=FAIL rc=1` -- 2 failed, 1 passed, 17 deselected, 10 warnings in 38.48s; [hermeticity] sentinel checked 3 test(s); [netguard] blocked 0 attempt(s) from 0 node(s)
- gate-row sanity mutant G3 (no limits.device_daily): `[pyt] tag=s09green-mut-G3 start=2026-10-29 17:36:01 end=2026-10-29 17:36:52 elapsed=51s bound=600s status=FAIL rc=1` -- 1 failed, 19 deselected, 11 warnings in 32.31s; [hermeticity] sentinel checked 1 test(s); [netguard] blocked 0 attempt(s) from 0 node(s)
- CI-order set (25 files, flags OFF): `[pyt] tag=s09green-ci-order start=2026-10-29 19:05:36 end=2026-10-29 19:10:37 elapsed=302s bound=1200s status=OK rc=0` -- 1309 passed, 321 warnings in 269.63s (0:04:29); [hermeticity] sentinel checked 1309 test(s); [netguard] blocked 5 attempt(s) from 4 node(s)
- tests/test_secret_scan_static.py alone minus the load-timed-out tracked-binaries node (the index holds the staged new files): `[pyt] tag=s09green-secret-rest start=2026-10-29 19:19:30 end=2026-10-29 19:20:10 elapsed=41s bound=600s status=OK rc=0` -- 30 passed, 1 deselected, 1 warning in 34.93s; [hermeticity] sentinel checked 30 test(s); [netguard] blocked 0 attempt(s) from 0 node(s)
- the amended RED copy (gitleaks fix, temp probe), flags OFF: `[pyt] tag=s09green-amended-off start=2026-10-29 19:16:32 end=2026-10-29 19:17:53 elapsed=81s bound=600s status=OK rc=0` -- 193 passed, 11 warnings in 63.14s (0:01:03); [hermeticity] sentinel checked 193 test(s); [netguard] blocked 0 attempt(s) from 0 node(s)
- the amended RED copy (gitleaks fix, temp probe), flags ON: `[pyt] tag=s09green-amended-on start=2026-10-29 19:17:57 end=2026-10-29 19:18:50 elapsed=52s bound=600s status=OK rc=0` -- 193 passed, 11 warnings in 41.79s; [hermeticity] sentinel checked 193 test(s); [netguard] blocked 0 attempt(s) from 0 node(s)

## Comm set (LC-6 reuse; base record <scratchpad>/harness/base_records/e7c81956f11749b1378aa449c4ac616c82bfe6a9/c9f7585d75ab76dab68c1d7e222563357c6ea34f327c728270cecbde479bb9fd.txt)

- `[pyt] tag=s09green-comm-00 start=2026-10-29 17:58:34 end=2026-10-29 18:00:52 elapsed=138s bound=1200s status=OK rc=0` -- 17 files: 899 passed, 335 warnings in 128.44s (0:02:08); [hermeticity] sentinel checked 899 test(s); [netguard] blocked 2 attempt(s) from 2 node(s)
- `[pyt] tag=s09green-comm-01 start=2026-10-29 18:00:58 end=2026-10-29 18:06:51 elapsed=354s bound=1200s status=OK rc=0` -- 10 files: 1352 passed, 13 warnings in 340.97s (0:05:40); [hermeticity] sentinel checked 1352 test(s); [netguard] blocked 25 attempt(s) from 3 node(s)
- `[pyt] tag=s09green-comm-02 start=2026-10-29 18:07:00 end=2026-10-29 18:11:46 elapsed=286s bound=1200s status=OK rc=0` -- 25 files: 969 passed, 6 deselected, 23 warnings in 273.22s (0:04:33); 
- `[pyt] tag=s09green-comm-03 start=2026-10-29 18:11:51 end=2026-10-29 18:15:12 elapsed=201s bound=1200s status=OK rc=0` -- 25 files: 2284 passed, 13 warnings in 192.84s (0:03:12); 
- `[pyt] tag=s09green-comm-04 start=2026-10-29 18:15:13 end=2026-10-29 18:26:24 elapsed=670s bound=1200s status=OK rc=0` -- 25 files: 727 passed, 18 warnings in 661.34s (0:11:01); 
- `[pyt] tag=s09green-comm-05 start=2026-10-29 18:26:29 end=2026-10-29 18:30:26 elapsed=237s bound=1200s status=FAIL rc=1` -- 25 files: MEASUREMENT FAILURE (pytest-timeout 120 s inside a module import in tests/test_observability.py under box load, no pytest summary); re-run once alone as 05r; 
- `[pyt] tag=s09green-comm-05r start=2026-10-29 18:30:32 end=2026-10-29 18:33:02 elapsed=150s bound=1200s status=FAIL rc=1` -- 25 files: 969 passed, 27 skipped, 6 deselected, 1 xfailed, 12 warnings, 2 errors in 135.70s (0:02:15); ; FAILED/ERROR: ERROR tests/test_prompt_truth.py::test_render_digests_match_base_except_the_fence, ERROR tests/test_prompt_truth.py::test_truth_on_prefix_static_and_cacheable
- `[pyt] tag=s09green-comm-06 start=2026-10-29 18:33:08 end=2026-10-29 18:39:24 elapsed=376s bound=1200s status=OK rc=0` -- 25 files: 1041 passed, 13 warnings in 351.23s (0:05:51); [netguard] blocked 6 attempt(s) from 5 node(s)
- `[pyt] tag=s09green-comm-07 start=2026-10-29 18:39:36 end=2026-10-29 18:51:08 elapsed=692s bound=1200s status=OK rc=0` -- 24 files: 2569 passed, 1 skipped, 8 deselected, 12 warnings in 647.31s (0:10:47); 
- `[pyt] tag=s09green-comm-08 start=2026-10-29 18:51:15 end=2026-10-29 18:55:04 elapsed=229s bound=1200s status=OK rc=0` -- 23 files: 1130 passed, 9 skipped, 2 deselected, 35 xfailed, 17 warnings in 219.02s (0:03:39); 
- `[pyt] tag=s09green-comm-09 start=2026-10-29 18:55:06 end=2026-10-29 18:58:27 elapsed=200s bound=600s status=FAIL rc=1` -- 1 files: MEASUREMENT FAILURE (9 passed, then pytest-timeout 120 s on test_tracked_binaries_carry_the_magic_bytes_of_their_extension under box load); re-run once alone as 09r; 
- `[pyt] tag=s09green-comm-09r start=2026-10-29 18:58:38 end=2026-10-29 19:03:03 elapsed=265s bound=600s status=FAIL rc=1` -- 1 files: MEASUREMENT FAILURE again on the same node: it is NOT MEASURED by name; the file's other 30 nodes passed in their own run (s09green-secret-rest); 

HEAD failed/error set: ERROR tests/test_prompt_truth.py::test_render_digests_match_base_except_the_fence, ERROR tests/test_prompt_truth.py::test_truth_on_prefix_static_and_cacheable. Branch-only-new: EMPTY.

## Client fences

- shareTruth.s74 alone (first; reads app/services/referral_service.py by path): Test Suites: 1 passed, 1 total / Tests:       10 passed, 10 total (tag s09green-fence-shareTruth)
- the other 13 fences: Test Suites: 1 failed, 12 passed, 13 total / Tests:       5 failed, 225 passed, 230 total (tag s09green-fences-13)
- nativeBundle.w37 re-run alone: Test Suites: 1 failed, 1 total / Tests:       4 failed, 54 passed, 58 total (tag s09green-fence-nativeBundle-rerun)
- `[jest] tag=s09green-fence-shareTruth start=2026-10-29 17:59:22 end=2026-10-29 18:00:25 rc=0`
- `[jest] tag=s09green-fences-13 start=2026-10-29 18:00:50 end=2026-10-29 18:03:19 rc=1` (12 suites PASS; nativeBundle.w37 d5, k2, k4, k5 drift + u12 a 5 s timeout under load)
- `[jest] tag=s09green-fence-nativeBundle-rerun start=2026-10-29 18:04:36 end=2026-10-29 18:05:22 rc=1` (alone: exactly the 4 accepted drift nodes d5, k2, k4, k5; u12 passed)

## Counts

- RED file: 193 / 193 green with the flags OFF and ON (87 RED + 106 PIN), the golden under the five OFF spellings (p01-p03 x5).
- Gate rows: 20 / 20 (GC-1 a/b, GC-2 x9, GC-3, g4, g5, g6 x2); 3 sanity mutants G1-G3 KILLED by AssertionError, every restore sha-verified, the mutation lock removed.
- E-rows: E1 (6) + E2 (1) + E3 (1) = 8 nodes, each measured by running the BASE pin bytes against the GREEN code.
- PR body: 22195 bytes (cap 25,600).

## Deviations (see the PR body section for the reasons)

1. GC-13 E3 pins usage_service's leaf attributes as {device_fingerprint, device_key, header_state, HEADER_DEVICE_FINGERPRINT} and allows the header_state needle there (GC-13's text says {device_fingerprint, device_key} and no header_state): the frozen r22 needs header_state. Import kept module-level (GC-13 says function-local; the cited S81-06 form is module-level).
2. usage_routes.py does not name the leaf (it passes **device_quota_kwargs()); spec 3.6 imported the leaf there.
3. The quota-path status GETs take the ST1 pool under ENABLE_USAGE_PATH_OFFLOOP (spec 2.7 asked for it; the prototype read inline).
4. GC-1: steps 1-4 skipped under the pause inside _grant_loop2_rewards; the redeemed mark (written by try_trigger_loop2) kept.
5. GC-2: the consume result's remaining.daily is the binding min on success and on both refusals.
6. The commit is BLOCKED (gitleaks on the frozen RED file, see the header); the prepared commit trailer is "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" (the committing agent's own model per s81-common and the session attribution), not the task text's "Claude Fable 5.1" (this agent is Opus 5.5).
7. Two extra git index writes: a numstat preview ran `git add -N` on the three new test files and `git reset -q --` of the same paths at once (state unchanged); then `git add` of the 13 paths for the commit (left staged after the refusal).
8. Budget: about 2 h 35 min from the first tool call (16:47) to the report, against 2 h; the overrun is box load (plain ls 9-10 s, git grep over app/ more than 120 s, comm chunks 04 / 07 at 661 / 647 s) plus GC-13 arriving at 17:43 and the gitleaks refusal at 19:13.
9. Comm chunk 05 had a measurement failure (pytest-timeout 120 s inside an import in tests/test_observability.py under load, no summary) and was re-run once alone (05r = the base record); the secret scan's tracked-binaries node timed out twice (09, 09r) and is NOT MEASURED by name; the file's other 30 nodes passed in their own run with that node deselected.

## Rebase notes (for the rebase round; nothing rebased here)

- origin/main 6c14ac95 (S81-08) also edits CLAUDE.md :171 (appends "With the S81-08 OTA the client value becomes the SHA-256 of the SecureStore id; ..." to the usage_service bullet) and adds its "SESSION 81 unit (S81-08 CLIENT-FIRST-OTA, ...)" block before "## Tests": the union keeps my in-place rewrite of :171 plus S81-08's appended sentence, and places the S81-09 block after the S81-08 block (GC-10).
- The comm set and its base record recompute at the then-main (GC-6, LC-6); the full jest suite runs once in that last round (LC-7).

## NOT MEASURED

- tests/test_secret_scan_static.py::test_tracked_binaries_carry_the_magic_bytes_of_their_extension at HEAD (pytest-timeout 120 s twice under box load: [pyt] s09green-comm-09 and s09green-comm-09r; the unit adds no binary and the hook's binary check passed).
- The Lua scripts on a real Redis / Upstash (no Lua runtime; the canary is the first execution).
- The FULL jest suite (LC-7: the last round before the PR; no unit-caused red fence).
- The comm set at the moved main 6c14ac95 (GC-6: the rebase round recomputes).
- The mutation table (the adversaries re-run it on the GREEN bytes, GC-11 g).
