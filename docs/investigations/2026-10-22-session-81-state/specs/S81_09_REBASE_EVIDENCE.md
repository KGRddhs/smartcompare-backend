# S81_09_REBASE_EVIDENCE (the S81-09 rebase round, HEAD f563b0c2636a921c31639e3f896f587610f6ecb3 on origin/main 6c14ac954f601902d322547de04982033aca5925; written by the rebase agent through the shell)

## Moved verbatim from the PR body (LC-3): GREEN's gates at e7c81956

## Gates (every pytest through `pyt.py`, one at a time; flags exported to one runner call only)

- RED file, ambient flags OFF: `[pyt] tag=s09green-unit-off elapsed=133s bound=600s status=OK rc=0` -- 193 passed in 120.32s (0:02:00)
- RED file, both flags ON in the runner env: `[pyt] tag=s09green-unit-on elapsed=42s bound=600s status=OK rc=0` -- 193 passed in 30.15s
- E-row probe: the BASE ST1 pin bytes (temp copy) + the 043 census vs the GREEN code: `[pyt] tag=s09green-erow-probe elapsed=149s bound=600s status=FAIL rc=1` -- 7 failed, 575 passed in 138.93s (0:02:18)
- ST1 pin file after E1/E2: `[pyt] tag=s09green-st1 elapsed=82s bound=600s status=OK rc=0` -- 531 passed in 62.19s (0:01:02)
- gate rows file: `[pyt] tag=s09green-gaterows elapsed=51s bound=600s status=OK rc=0` -- 20 passed in 37.82s
- E3 probe: the BASE S05 pin bytes (temp copy) + the edited S05 file vs the GREEN code: `[pyt] tag=s09green-e3-probe elapsed=66s bound=600s status=FAIL rc=1` -- 1 failed, 351 passed in 54.30s
- RED file + gate rows, final code, flags OFF: `[pyt] tag=s09green-unit-off2 elapsed=49s bound=600s status=OK rc=0` -- 213 passed in 40.59s
- RED file + gate rows, final code, flags ON: `[pyt] tag=s09green-unit-on2 elapsed=47s bound=600s status=OK rc=0` -- 213 passed in 32.96s
- CI-order set (25 files, flags OFF): `[pyt] tag=s09green-ci-order elapsed=302s bound=1200s status=OK rc=0` -- 1309 passed in 269.63s (0:04:29)
- tests/test_secret_scan_static.py alone minus the load-timed-out tracked-binaries node (the index holds the staged new files): `[pyt] tag=s09green-secret-rest elapsed=41s bound=600s status=OK rc=0` -- 30 passed, 1 deselected in 34.93s
- the amended RED copy (gitleaks fix, temp probe), flags OFF: `[pyt] tag=s09green-amended-off elapsed=81s bound=600s status=OK rc=0` -- 193 passed in 63.14s (0:01:03)
- the amended RED copy (gitleaks fix, temp probe), flags ON: `[pyt] tag=s09green-amended-on elapsed=52s bound=600s status=OK rc=0` -- 193 passed in 41.79s
- 3 gate-row sanity mutants (G1 the pause reads the lifetime slot, G2 no binding min, G3 no limits.device_daily): all KILLED by AssertionError, restores sha-verified (the [pyt] lines are in the GREEN report).

Comm set: the RED's 200-file list re-derived at HEAD by the union rule (+ the GREEN symbols, the importers of the two edited pin files, the gate-rows file kept out like the RED file): IDENTICAL, set sha256 `c9f7585d...`; no addition, so the CACHED base record at e7c81956 was REUSED (LC-6; 11,971 passed, failed/error set = the 2 known cold-tiktoken `test_prompt_truth` ERRORs); no base re-run. HEAD, one chunk at a time, `test_secret_scan_static.py` alone (GC-7):

- `[pyt] tag=s09green-comm-00 start=2026-10-29 17:58:34 end=2026-10-29 18:00:52 elapsed=138s bound=1200s status=OK rc=0` -- 17 files: 899 passed in 128.44s (0:02:08)
- `[pyt] tag=s09green-comm-01 start=2026-10-29 18:00:58 end=2026-10-29 18:06:51 elapsed=354s bound=1200s status=OK rc=0` -- 10 files: 1352 passed in 340.97s (0:05:40)
- `[pyt] tag=s09green-comm-02 start=2026-10-29 18:07:00 end=2026-10-29 18:11:46 elapsed=286s bound=1200s status=OK rc=0` -- 25 files: 969 passed, 6 deselected in 273.22s (0:04:33)
- `[pyt] tag=s09green-comm-03 start=2026-10-29 18:11:51 end=2026-10-29 18:15:12 elapsed=201s bound=1200s status=OK rc=0` -- 25 files: 2284 passed in 192.84s (0:03:12)
- `[pyt] tag=s09green-comm-04 start=2026-10-29 18:15:13 end=2026-10-29 18:26:24 elapsed=670s bound=1200s status=OK rc=0` -- 25 files: 727 passed in 661.34s (0:11:01)
- `[pyt] tag=s09green-comm-05 start=2026-10-29 18:26:29 end=2026-10-29 18:30:26 elapsed=237s bound=1200s status=FAIL rc=1` -- 25 files: MEASUREMENT FAILURE (pytest-timeout 120 s inside a module import in tests/test_observability.py under box load, no pytest summary); re-run once alone as 05r
- `[pyt] tag=s09green-comm-05r start=2026-10-29 18:30:32 end=2026-10-29 18:33:02 elapsed=150s bound=1200s status=FAIL rc=1` -- 25 files: 969 passed, 27 skipped, 6 deselected, 1 xfailed, 2 errors in 135.70s (0:02:15); FAILED/ERROR: ERROR tests/test_prompt_truth.py::test_render_digests_match_base_except_the_fence, ERROR tests/test_prompt_truth.py::test_truth_on_prefix_static_and_cacheable
- `[pyt] tag=s09green-comm-06 start=2026-10-29 18:33:08 end=2026-10-29 18:39:24 elapsed=376s bound=1200s status=OK rc=0` -- 25 files: 1041 passed in 351.23s (0:05:51)
- `[pyt] tag=s09green-comm-07 start=2026-10-29 18:39:36 end=2026-10-29 18:51:08 elapsed=692s bound=1200s status=OK rc=0` -- 24 files: 2569 passed, 1 skipped, 8 deselected in 647.31s (0:10:47)
- `[pyt] tag=s09green-comm-08 start=2026-10-29 18:51:15 end=2026-10-29 18:55:04 elapsed=229s bound=1200s status=OK rc=0` -- 23 files: 1130 passed, 9 skipped, 2 deselected, 35 xfailed in 219.02s (0:03:39)
- `[pyt] tag=s09green-comm-09 start=2026-10-29 18:55:06 end=2026-10-29 18:58:27 elapsed=200s bound=600s status=FAIL rc=1` -- 1 files: MEASUREMENT FAILURE (9 passed, then pytest-timeout 120 s on test_tracked_binaries_carry_the_magic_bytes_of_their_extension under box load); re-run once alone as 09r
- `[pyt] tag=s09green-comm-09r start=2026-10-29 18:58:38 end=2026-10-29 19:03:03 elapsed=265s bound=600s status=FAIL rc=1` -- 1 files: MEASUREMENT FAILURE again on the same node (not measured by GREEN). MEASURED since (F1-13, superseding GC-14 (d)): the quota-and-billing adversary's `[pyt] tag=s09adv-qb-secret elapsed=5s bound=600s status=OK rc=0` -- 31 passed incl. that node; at HEAD: s09fix1-secret below

HEAD failed/error set: ERROR tests/test_prompt_truth.py::test_render_digests_match_base_except_the_fence, ERROR tests/test_prompt_truth.py::test_truth_on_prefix_static_and_cacheable. Branch-only-new (HEAD minus the base record): **EMPTY**.

Client fences (the 14 backend-scanning suites by path through the orchestrator junction, node v24.11.1, jest 29.7.0, one jest at a time):

- shareTruth.s74 alone (first; reads app/services/referral_service.py by path): Test Suites: 1 passed, 1 total / Tests:       10 passed, 10 total (tag s09green-fence-shareTruth)
- the other 13 fences: Test Suites: 1 failed, 12 passed, 13 total / Tests:       5 failed, 225 passed, 230 total (tag s09green-fences-13)
- nativeBundle.w37 re-run alone: Test Suites: 1 failed, 1 total / Tests:       4 failed, 54 passed, 58 total (tag s09green-fence-nativeBundle-rerun)
- `[jest] tag=s09green-fence-shareTruth start=2026-10-29 17:59:22 end=2026-10-29 18:00:25 rc=0`
- `[jest] tag=s09green-fences-13 start=2026-10-29 18:00:50 end=2026-10-29 18:03:19 rc=1` (12 suites PASS; nativeBundle.w37 d5, k2, k4, k5 drift + u12 a 5 s timeout under load)
- `[jest] tag=s09green-fence-nativeBundle-rerun start=2026-10-29 18:04:36 end=2026-10-29 18:05:22 rc=1` (alone: exactly the 4 accepted drift nodes d5, k2, k4, k5; u12 passed)

The 4 nativeBundle.w37 nodes are the accepted drift class (the junctioned clone's node_modules older than this worktree's lock: expo 54.0.34 vs 54.0.37, eslint-config-expo 55.0.1, react-native-gesture-handler installed); the unit touches no SmartCompareApp file and none of the files that suite reads. No unit-caused red fence, so the FULL jest suite runs once in the last round before the PR (LC-7). ruff (E9,F63,F7,F82) and py_compile clean on every touched python file; `black --check` clean on the black-listed S05 pin file; CRLF kept, no added non-ASCII byte.

## Moved verbatim from the PR body (LC-3): fix round 1's gates at 990f06d8

## Fix round 1 gates (HEAD `990f06d8`; test + docs + EK4, no app/ byte moved, no re-verifier, LC-2)

- RED file OFF / ON (s09fix1-unit-off / -on, status=OK rc=0): 193 / 193 each; gate rows OFF / ON (s09fix1-gaterows-off / -on, status=OK rc=0): 24 / 24 each
- the lenses' pin gaps as 4 new mutants on byte copies under `.qa-mutation.lock` (MF2 = X10 UTC-day status key, MF3 = X07 NULL-tier status path, MF4 = X01 code-2 clause dropped, MF12 = B40 process-global stash; the lenses measured 57 / 61 and 33 / 33 KILLED, X03 equivalent): 4/4 KILLED by AssertionError, each by its row alone (s09fix1-post-mut-*, status=FAIL rc=1); restores sha-verified, lock removed
- CI-order set (25 files, flags OFF): `[pyt] tag=s09fix1-ci-order elapsed=41s bound=1200s status=OK rc=0` -- 1313 passed (1309 + 4); secret scan alone (GC-7, new files tracked): s09fix1-secret status=OK rc=0, 31 passed
- ruff + py_compile clean; no comm / fence re-run (F1-14: every app/ sha256 equals the GREEN snapshot before and after; both run at the rebase).

## Moved from the PR body's E-rows table (LC-3): E1, the six re-recorded BASE_DIGESTS

- BASE_DIGESTS re-recorded: 3f76488c -> ebfcb0ba, 63ff3c9e -> 5b47fefd, b3c3dd2e -> 7b808f15, 885f6947 -> 9e40493a, cfe716e2 -> f77292f5, 65eabb27 -> 67a67f8d (one comment naming S81-09)

## This round: the 13 files at HEAD (blob = git show HEAD:path; working copy = the bytes on disk, CRLF)

- CLAUDE.md: +9 / -2, blob d14e0f8b3caa892ed88184fbdd30416a8365a30d10825bce7db225e098e2c67a (582761 B, non-ASCII 3931), working copy 0b8b54b6959bb5a260d11f45f5c70070f7448b610d56223de3ac3286f21ca5d3 (CRLF 999), blob equal to 990f06d8: False
- app/api/image_routes.py: +4 / -1, blob abb783f1b50c80c3e72119c78a7bf38dd5ae536004557fb42c5f77b983a3631a (36406 B, non-ASCII 21), working copy 717d1e5a05d455dceb66b8c0bc38806d74c7d39cb2c7d57fd25e845654959719 (CRLF 738), blob equal to 990f06d8: True
- app/api/text_routes.py: +14 / -3, blob d191e0fcf14dd1d3ff33ab091950be8595ffadf2d77b954fb3c3dc4720bf5567 (95803 B, non-ASCII 267), working copy 767be4451ba9d89b4d656675f95c9cd59e98760a98a1496abe8b5446363d4652 (CRLF 2020), blob equal to 990f06d8: True
- app/api/url_routes.py: +6 / -1, blob 508fec0ad7d29ea2fbdc58bd7f4e794e1788dfa01385baf700ab6756f8fdbe87 (23390 B, non-ASCII 0), working copy c0ff7eb2f4e2c046fae7a59667238d69b63040bc0e2d9f88e23ec05a9f87b9b7 (CRLF 569), blob equal to 990f06d8: True
- app/api/usage_routes.py: +16 / -1, blob 47336e28dbd46f2043f8006ca710740f45c5ebe296d40a39c9e8d4e18ab9ef66 (1172 B, non-ASCII 0), working copy 8645776ffaffc56c69347712569a6e73797ca5d72b9b1e328615c20590565c98 (CRLF 30), blob equal to 990f06d8: True
- app/middleware/error_handler.py: +29 / -0, blob bf71cbd1dcd05071b3bb83aacc2ea97d0150fdfe2f3b0b471a2d3a09008c8198 (12576 B, non-ASCII 3), working copy 56332100e766db5f1bbe281540e17b657fe57715000b6502b6ed70a604f7961c (CRLF 315), blob equal to 990f06d8: True
- app/services/referral_service.py: +38 / -6, blob aad54e3cc4227c8f67c6067969d519903be9d371005867dc2ba6c7c7f1447cbb (40168 B, non-ASCII 105), working copy a928a6b65b69c29b808b652f1424860b750c115d724b4f77394e558bf9f11807 (CRLF 968), blob equal to 990f06d8: True
- app/services/usage_service.py: +478 / -12, blob b096a76733a291fb02846c539d44c6e3d28c6b0d342c167f57cd67d47a1665b8 (58174 B, non-ASCII 105), working copy 570785b43ead06fa1c648cd7a4b27dabf17403c05386c7ffbae476279175e88c (CRLF 1305), blob equal to 990f06d8: True
- tests/fixtures/s81_s09_flag_off_golden.json: +722 / -0, blob 02b29cc6d3a649324f71b27472ae135cc015ba39e9659b49c0306d1e249e6176 (16589 B, non-ASCII 0), working copy 5b0afe5e2198f68e6dd10d3d76e3fd6079845123b0b0d196e2c81e0dbe9bcd34 (CRLF 722), blob equal to 990f06d8: True
- tests/test_s81_s05_request_context.py: +27 / -4, blob c0394a5307c5038822e4ef8b668942ae244b3a7ab9f3f5f476bee2b095b62ce7 (63418 B, non-ASCII 0), working copy 49d0b015fdd6fe53266fa9a15a0fdf377f706e6f106613afc86fd7483de8b5cc (CRLF 1848), blob equal to 990f06d8: True
- tests/test_s81_s09_device_quota.py: +2068 / -0, blob 551a3167ac54d1ef842f76d1603c05c3a7e404384f6f161bb33bc1c4fad6963f (87175 B, non-ASCII 0), working copy 6ebac73289d2613b8c9715df94098676df1bfa58c1c8e66a6e1256d7e5c27d69 (CRLF 2068), blob equal to 990f06d8: True
- tests/test_s81_s09_gate_rows.py: +389 / -0, blob a8e01fcf6f22c5dee37d10ba461176c642976fd930a7c5a750c99c0fa152ba5e (18716 B, non-ASCII 0), working copy 0e30c1df7d075ee92e8514c0671f6c7d0e321dd99ca77879624b2836a4498e0b (CRLF 389), blob equal to 990f06d8: True
- tests/test_s81_st1_usage_path_offloop.py: +15 / -7, blob 6a0d65ad05c62ecfc3d520d326b7c45ad6fa19e00048f1010e948f5f29153273 (135307 B, non-ASCII 0), working copy 6380fff98dadf14856630060255da9ef52ef8816b1e8d0fb9b93e10f2f177b16 (CRLF 2776), blob equal to 990f06d8: True

## This round: every runner line with its guard lines

- `[pyt] tag=s09rb-unit-off start=2026-11-02 12:05:20 end=2026-11-02 12:05:24 elapsed=4s bound=600s status=OK rc=0` -- 193 passed, 11 warnings in 3.53s
  - args: tests/test_s81_s09_device_quota.py
  - [hermeticity] sentinel checked 193 test(s)
  - [netguard] blocked 0 attempt(s) from 0 node(s)
- `[pyt] tag=s09rb-unit-on start=2026-11-02 12:05:24 end=2026-11-02 12:05:29 elapsed=4s bound=600s status=OK rc=0` -- 193 passed, 11 warnings in 3.50s
  - args: tests/test_s81_s09_device_quota.py
  - [hermeticity] sentinel checked 193 test(s)
  - [netguard] blocked 0 attempt(s) from 0 node(s)
- `[pyt] tag=s09rb-rows-off start=2026-11-02 12:05:29 end=2026-11-02 12:05:32 elapsed=3s bound=600s status=OK rc=0` -- 24 passed, 10 warnings in 2.68s
  - args: tests/test_s81_s09_gate_rows.py
  - [hermeticity] sentinel checked 24 test(s)
  - [netguard] blocked 0 attempt(s) from 0 node(s)
- `[pyt] tag=s09rb-rows-on start=2026-11-02 12:05:32 end=2026-11-02 12:05:35 elapsed=3s bound=600s status=OK rc=0` -- 24 passed, 10 warnings in 2.69s
  - args: tests/test_s81_s09_gate_rows.py
  - [hermeticity] sentinel checked 24 test(s)
  - [netguard] blocked 0 attempt(s) from 0 node(s)
- `[pyt] tag=s09rb-r8pair start=2026-11-02 12:05:36 end=2026-11-02 12:05:53 elapsed=17s bound=600s status=OK rc=0` -- 273 passed, 1 warning in 16.26s
  - args: tests/test_sentry_channels_u8d_unit.py tests/test_sentry_channels_u8d.py
  - [hermeticity] sentinel checked 273 test(s)
  - [netguard] blocked 0 attempt(s) from 0 node(s)
- `[pyt] tag=s09rb-metering-off start=2026-11-02 12:05:53 end=2026-11-02 12:05:56 elapsed=4s bound=600s status=OK rc=0` -- 21 passed, 13 warnings in 2.91s
  - args: tests/test_paid_route_metering.py
  - [hermeticity] sentinel checked 21 test(s)
  - [netguard] blocked 2 attempt(s) from 2 node(s)
- `[pyt] tag=s09rb-metering-on start=2026-11-02 12:05:57 end=2026-11-02 12:06:00 elapsed=4s bound=600s status=OK rc=0` -- 21 passed, 13 warnings in 2.99s
  - args: tests/test_paid_route_metering.py
  - [hermeticity] sentinel checked 21 test(s)
  - [netguard] blocked 2 attempt(s) from 2 node(s)
- `[pyt] tag=s09rb-readers start=2026-11-02 12:06:00 end=2026-11-02 12:06:05 elapsed=5s bound=600s status=OK rc=0` -- 79 passed, 1 warning in 4.44s
  - args: tests/test_ci_gates.py tests/test_behavior_dimension_translation.py
  - [hermeticity] sentinel checked 79 test(s)
  - [netguard] blocked 0 attempt(s) from 0 node(s)
- `[pyt] tag=s09rb-ciorder start=2026-11-02 12:06:06 end=2026-11-02 12:06:55 elapsed=50s bound=1200s status=OK rc=0` -- 1711 passed, 347 warnings in 48.01s
  - args: tests/test_429_contract.py tests/test_behavior_dimension_translation.py tests/test_ci_gates.py tests/test_error_middleware.py tests/test_image_identify_llm_unavailable_s69.py tests/test_legal_disclosure_s77.py tests/test_m13_37_freemium_atomic_consume.py tests/test_m18_preverdict_disconnect_refund.py tests/test_m18_usage_symmetry.py tests/test_migration_043_delete_user_cascade.py tests/test_paid_route_metering.py tests/test_referral_loop2.py tests/test_referral_service.py tests/test_register_benefits_parity_s69.py tests/test_retro_w1_9.py tests/test_retro_w1_9_429.py tests/test_s81_s05_request_context.py tests/test_s81_s09_device_quota.py tests/test_s81_s09_gate_rows.py tests/test_s81_st1_usage_path_offloop.py tests/test_u3c_referral_push_name.py tests/test_usage_device_inheritance.py tests/test_usage_referral_bonus.py tests/test_usage_service_internals.py tests/test_usage_tiers.py tests/test_s81_s04_spend_breaker.py tests/test_s81_s08b_legacy_fingerprint.py tests/test_s81_s08b_gate_rows.py
- `[pyt] tag=s09rb-base-u15 start=2026-11-02 12:08:05 end=2026-11-02 12:08:23 elapsed=18s bound=1200s status=OK rc=0` -- 102 passed, 2 warnings in 16.84s
  - args: tests/test_feedback_service.py tests/test_m13_37_freemium_atomic_consume.py tests/test_referral_expiry.py tests/test_referral_full_response_column.py tests/test_referral_lifetime_cap.py tests/test_referral_loop2.py tests/test_referral_service_internals.py tests/test_referral_share_status_lifetime.py tests/test_register_invite_linking.py tests/test_scoring_calibration_bundle_c.py tests/test_url_validator_offloop_hops.py tests/test_usage_device_inheritance.py tests/test_usage_referral_bonus.py tests/test_usage_service_internals.py tests/test_usage_tiers.py
  - [hermeticity] sentinel checked 102 test(s)
  - [netguard] blocked 4 attempt(s) from 3 node(s)
- `[pyt] tag=s09rb-comm-00 start=2026-11-02 12:08:23 end=2026-11-02 12:08:51 elapsed=28s bound=1200s status=OK rc=0` -- 899 passed, 345 warnings in 26.45s
  - args: tests/test_usage_service_internals.py tests/test_usage_tiers.py tests/test_usage_referral_bonus.py tests/test_usage_device_inheritance.py tests/test_m18_usage_symmetry.py tests/test_m13_37_freemium_atomic_consume.py tests/test_m18_preverdict_disconnect_refund.py tests/test_paid_route_metering.py tests/test_s81_st1_usage_path_offloop.py tests/test_s81_s05_request_context.py tests/test_legal_disclosure_s77.py tests/test_register_benefits_parity_s69.py tests/test_429_contract.py tests/test_retro_w1_9.py tests/test_retro_w1_9_429.py tests/test_error_middleware.py tests/test_image_identify_llm_unavailable_s69.py
  - [hermeticity] sentinel checked 899 test(s)
  - [netguard] blocked 2 attempt(s) from 2 node(s)
- `[pyt] tag=s09rb-comm-01 start=2026-11-02 12:08:51 end=2026-11-02 12:09:28 elapsed=37s bound=1200s status=OK rc=0` -- 1352 passed, 13 warnings in 35.42s
  - args: tests/test_s80_url_mode_v2.py tests/test_s81_s04_spend_breaker.py tests/test_s81_s08b_legacy_fingerprint.py tests/test_s81_s08b_gate_rows.py tests/test_text_routes_error_mapping.py tests/test_s81_s06_anthropic_router.py tests/test_cron_expire_bonuses.py tests/test_referral_expiry.py tests/test_retro_w2_1.py tests/test_shutdown_drain.py
  - [hermeticity] sentinel checked 1352 test(s)
  - [netguard] blocked 25 attempt(s) from 3 node(s)
- `[pyt] tag=s09rb-comm-02 start=2026-11-02 12:09:28 end=2026-11-02 12:10:07 elapsed=39s bound=1200s status=OK rc=0` -- 969 passed, 6 deselected, 23 warnings in 37.22s
  - args: tests/test_account_deletion.py tests/test_account_deletion_u8b.py tests/test_adapter_drop_visibility.py tests/test_admin_key_and_sentry_scrub.py tests/test_admin_referral_endpoints.py tests/test_arabic_verdict_output_w414.py tests/test_attribution_endpoint.py tests/test_auth_demographics.py tests/test_auth_error_log_hygiene.py tests/test_auth_refresh_and_revocation.py tests/test_auth_routes_invite_fingerprint.py tests/test_b2_strict_optional_auth.py tests/test_backend_cleanup.py tests/test_be_harness.py tests/test_behavior_dimension_translation.py tests/test_behavior_integration.py tests/test_bh_gcc_cascade_wiring.py tests/test_cache_service_bounded_transport.py tests/test_camera_vision.py tests/test_category_aware_discovery_i55.py tests/test_category_selection.py tests/test_cellular_generation_cache_key.py tests/test_channel_freshness.py tests/test_ci_gates.py tests/test_cohort_personalization_load.py
- `[pyt] tag=s09rb-comm-03 start=2026-11-02 12:10:07 end=2026-11-02 12:10:41 elapsed=34s bound=1200s status=OK rc=0` -- 2284 passed, 13 warnings in 32.19s
  - args: tests/test_cohort_summary_orchestrator.py tests/test_comparison_id_echo.py tests/test_comparison_quality_v2.py tests/test_comparison_response_image_url.py tests/test_consent_capture_w3_16.py tests/test_content_blocklist_arabic_parity.py tests/test_cost_meter_s74.py tests/test_cron_reengagement.py tests/test_diagnostics_flag_gated.py tests/test_dimension_label_catalog_parity_w414.py tests/test_discovery_window_i54.py tests/test_domain_s76.py tests/test_eval_cache_read_mode.py tests/test_eval_kpi_baseline.py tests/test_events_allowlist_superset.py tests/test_extraction_pros_cons_diagnostic.py tests/test_fact_checking.py tests/test_fan_out_genuine_authority.py tests/test_feature_bucket_parity.py tests/test_feedback_allowlist_superset.py tests/test_feedback_service.py tests/test_fire_and_forget_wrap.py tests/test_flush_live_price_key.py tests/test_genuine_beats_converted_selection.py tests/test_genuine_predicate_parity.py
- `[pyt] tag=s09rb-comm-04 start=2026-11-02 12:10:41 end=2026-11-02 12:11:48 elapsed=67s bound=1200s status=OK rc=0` -- 727 passed, 18 warnings in 66.01s (0:01:06)
  - args: tests/test_genuine_price_clobber_guard.py tests/test_genuine_price_priority.py tests/test_genuine_reach_cascade.py tests/test_health_loop_lag.py tests/test_hermeticity_pins.py tests/test_http_400_cap_cut_mapping.py tests/test_iherb_page_currency_signal.py tests/test_invitee_quiz.py tests/test_js_rendering.py tests/test_jsonld_shape_ladder.py tests/test_landing_fallback_pages_s69.py tests/test_legal_docs_u8.py tests/test_legal_docs_u8_d3c.py tests/test_legal_docs_u8_polish.py tests/test_legal_routes.py tests/test_legal_s78.py tests/test_limiter_endpoint_key.py tests/test_logger_no_query_leak.py tests/test_loop2_gift_copy.py tests/test_m13_03_paid_work_gating.py tests/test_m13_25_compare_body_maxlength.py tests/test_m13_26_image_error_envelope.py tests/test_m13_28_referral_hardening.py tests/test_m13_35_sse_disconnect_finally.py tests/test_m18_factcheck_honest.py
- `[pyt] tag=s09rb-comm-05 start=2026-11-02 12:11:48 end=2026-11-02 12:12:13 elapsed=25s bound=1200s status=FAIL rc=1` -- 969 passed, 27 skipped, 6 deselected, 1 xfailed, 12 warnings, 2 errors in 23.85s
  - args: tests/test_m18_offload_sweep_residual.py tests/test_m21_brand_dedup_and_verdict_copy.py tests/test_migration_037_security_definer_grants.py tests/test_migration_042_search_logs_is_synthetic.py tests/test_migration_043_delete_user_cascade.py tests/test_migration_044_apple_siwa_tokens.py tests/test_migration_index_predicate_immutability.py tests/test_model_config.py tests/test_model_config_enforced.py tests/test_multiplicity_discriminator_policy.py tests/test_nasser_adapter.py tests/test_negcache_genuine_invalidation.py tests/test_no_luxury_gate_in_tier3.py tests/test_not_a_pdp_filter.py tests/test_observability.py tests/test_og_cascade_position.py tests/test_openai_breaker.py tests/test_openai_key_log_hygiene_s69.py tests/test_password_reset_deep_link.py tests/test_phase1_per_race_timeouts.py tests/test_platform_router.py tests/test_price_kpi_endpoint.py tests/test_prompt_fence.py tests/test_prompt_truth.py tests/test_referral_e2e.py
  - ERROR tests/test_prompt_truth.py::test_truth_on_prefix_static_and_cacheable
  - ERROR tests/test_prompt_truth.py::test_render_digests_match_base_except_the_fence
- `[pyt] tag=s09rb-comm-06 start=2026-11-02 12:12:13 end=2026-11-02 12:13:53 elapsed=99s bound=1200s status=OK rc=0` -- 1041 passed, 13 warnings in 98.31s (0:01:38)
  - args: tests/test_referral_feature_flag.py tests/test_referral_full_response_column.py tests/test_referral_lifetime_cap.py tests/test_referral_loop2.py tests/test_referral_must_fixes.py tests/test_referral_routes.py tests/test_referral_service.py tests/test_referral_service_internals.py tests/test_referral_share_privacy.py tests/test_referral_share_status_lifetime.py tests/test_register_invite_linking.py tests/test_response_builder_phase1_none_guard.py tests/test_retro_w0_4.py tests/test_retro_w0_4_efg.py tests/test_retro_w1_2b.py tests/test_retro_w1_2d.py tests/test_review_paraphrase.py tests/test_robots_unreadable_ruling.py tests/test_s70_exc_summary_logs.py tests/test_s70_model_router_downgrade.py tests/test_s70_prefetch_gather_retrieved.py tests/test_s71_u13_compare_auth_required.py tests/test_s71_u13_pins.py tests/test_s75_fanout_starve.py tests/test_s77_redis_offloop.py
  - [netguard] blocked 6 attempt(s) from 5 node(s)
- `[pyt] tag=s09rb-comm-07 start=2026-11-02 12:13:53 end=2026-11-02 12:15:45 elapsed=112s bound=1200s status=OK rc=0` -- 2569 passed, 1 skipped, 8 deselected, 12 warnings in 110.59s (0:01:50)
  - args: tests/test_s78_all_timeout_cap_as_timeout.py tests/test_s79_b3b_apple_revoke.py tests/test_s80_b1.py tests/test_s80_b3_vision_identity_v2.py tests/test_s81_d03_deny_and_guards.py tests/test_s81_kb_schema.py tests/test_s81_s03_llm_ledger_v2.py tests/test_s81_s06_router_gate_rows.py tests/test_s81_s15_gate_rows.py tests/test_s81_s15_registry_robots.py tests/test_scoring_calibration_bundle_c.py tests/test_scraping_mode.py tests/test_security_hardening.py tests/test_security_regression.py tests/test_sentry_channels_u8d.py tests/test_sentry_channels_u8d_unit.py tests/test_shopify_pdp_json.py tests/test_skill_frontmatter.py tests/test_social_login_device_fingerprint.py tests/test_social_login_smoke.py tests/test_specs_no_fabrication_guard.py tests/test_sse_settle_window.py tests/test_start_command.py tests/test_streaming.py
- `[pyt] tag=s09rb-comm-08 start=2026-11-02 12:15:45 end=2026-11-02 12:16:44 elapsed=59s bound=1200s status=OK rc=0` -- 1130 passed, 9 skipped, 2 deselected, 35 xfailed, 17 warnings in 57.76s
  - args: tests/test_supabase_client_reuse.py tests/test_text_error_envelope_no_raw_exception.py tests/test_text_routes_sse_contract.py tests/test_timeout_partial_integration.py tests/test_two_input_shape.py tests/test_u13e_url_detect_guard.py tests/test_u3b_sharing_branch_removed.py tests/test_u3c_referral_push_name.py tests/test_u3c_store_false_pin.py tests/test_url_validator_offloop.py tests/test_url_validator_offloop_hops.py tests/test_value_badge_category_dims.py tests/test_value_math.py tests/test_visible_text_currency_rung.py tests/test_w4_12_display_contract.py tests/test_w4_13_measurement_truth.py tests/test_w4_7_confidence_single_computation.py tests/test_w4_7_factcheck_shopping_key.py tests/test_wall_caps_i57.py tests/test_wall_signature_anchoring.py tests/test_wide_signal_text.py tests/test_youtube_cited_evidence.py tests/test_youtube_flag_and_cache.py
- `[pyt] tag=s09rb-secretscan start=2026-11-02 12:16:44 end=2026-11-02 12:16:49 elapsed=5s bound=600s status=OK rc=0` -- 31 passed, 1 warning in 4.15s
  - args: tests/test_secret_scan_static.py
  - [hermeticity] sentinel checked 31 test(s)
  - [netguard] blocked 0 attempt(s) from 0 node(s)
- `[pyt] tag=s09rb-hook-notdash start=2026-11-02 12:16:57 end=2026-11-02 12:21:36 elapsed=280s bound=1800s status=OK rc=0` -- 167 passed, 160 deselected, 7 warnings in 278.95s (0:04:38)
  - args: tests/test_precommit_hook.py tests/test_precommit_hook_phase_b.py tests/test_precommit_hook_phase_b_round2.py tests/test_precommit_hook_round2.py -k not dash
  - [hermeticity] sentinel checked 167 test(s)
  - [netguard] blocked 0 attempt(s) from 0 node(s)
- `[pyt] tag=s09rb-hook-dash start=2026-11-02 12:21:36 end=2026-11-02 12:29:48 elapsed=492s bound=1800s status=OK rc=0` -- 157 passed, 3 skipped, 167 deselected, 7 warnings in 491.12s (0:08:11)
  - args: tests/test_precommit_hook.py tests/test_precommit_hook_phase_b.py tests/test_precommit_hook_phase_b_round2.py tests/test_precommit_hook_round2.py -k dash
  - [hermeticity] sentinel checked 160 test(s)
  - [netguard] blocked 0 attempt(s) from 0 node(s)
- `[jest] tag=s09rb-fence-shareTruth start=2026-11-02 12:09:24 end=2026-11-02 12:09:27 rc=0` -- Test Suites: 1 passed, 1 total / Tests: 10 passed, 10 total
- `[jest] tag=s09rb-fences-13 start=2026-11-02 12:09:36 end=2026-11-02 12:09:42 rc=1` -- Test Suites: 1 failed, 12 passed, 13 total / Tests: 4 failed, 226 passed, 230 total
- `[jest] tag=s09rb-jest-full start=2026-11-02 12:09:51 end=2026-11-02 12:10:08 rc=1` -- Test Suites: 1 failed, 3 skipped, 385 passed, 386 of 389 total / Tests: 4 failed, 13 skipped, 13 todo, 3794 passed, 3824 total
- `[tsc] tag=s09rb-tsc start=2026-11-02 12:10:39 end=2026-11-02 12:10:47 rc=0`
- `[hook] tag=s09rb-hook-replayed start=2026-11-02 12:11:12 end=2026-11-02 12:11:15 rc=0`

## The base record at 6c14ac95 (LC-6)

- stored: harness/base_records/6c14ac954f601902d322547de04982033aca5925/c9f7585d75ab76dab68c1d7e222563357c6ea34f327c728270cecbde479bb9fd.txt (+ .pyt.log, .files)
- the 15 files run here: tests/test_feedback_service.py, tests/test_m13_37_freemium_atomic_consume.py, tests/test_referral_expiry.py, tests/test_referral_full_response_column.py, tests/test_referral_lifetime_cap.py, tests/test_referral_loop2.py, tests/test_referral_service_internals.py, tests/test_referral_share_status_lifetime.py, tests/test_register_invite_linking.py, tests/test_scoring_calibration_bundle_c.py, tests/test_url_validator_offloop_hops.py, tests/test_usage_device_inheritance.py, tests/test_usage_referral_bonus.py, tests/test_usage_service_internals.py, tests/test_usage_tiers.py
- base failed/error set: tests/test_prompt_truth.py::test_render_digests_match_base_except_the_fence, tests/test_prompt_truth.py::test_truth_on_prefix_static_and_cacheable
- HEAD failed/error set: tests/test_prompt_truth.py::test_render_digests_match_base_except_the_fence, tests/test_prompt_truth.py::test_truth_on_prefix_static_and_cacheable
- comm -13: EMPTY; comm -23: empty

## The CLAUDE.md resolution (resolve_claude.py apply)

- line 170: branch rewrite (1169 B) + main's appended S81-08 sentence (279 B, non-ASCII 0) = 1448 B
- line 194 (api.ts bullet): main's text (branch unchanged)
- line 340 (Feature Flags pointer): main's text at 6c14ac95 == base's; the branch's pointer added where the branch put it = the branch's line
- anchor: main's S81-08 block (9 lines) then the branch's S81-09 block (7 lines), then base[520:] ('', '## Tests', ...)
- line 340: the branch inserted 228 B at offset 2536 (non-ASCII 0); main's text kept whole
- order: S81-15 owner-steps line 519, S81-08 header line 521, S81-09 header line 530, '## Tests' line 537
- non-ASCII bytes: base 3937, branch 3931 (delta -6), main 3937, resolved 3931 (= main + branch delta)
- resolved LF: 582761 B, 999 LF, sha256 d14e0f8b3caa892ed88184fbdd30416a8365a30d10825bce7db225e098e2c67a
- resolved CRLF (working copy): 583760 B, sha256 0b8b54b6959bb5a260d11f45f5c70070f7448b610d56223de3ac3286f21ca5d3
- conflicted working copy: 584792 B, CRLF 1005, 2 conflict regions at lines [(170, 174), (525, 541)]
- auto-merged text outside the markers (984 lines) is an in-order subsequence of the resolution
- written to the working copy (CRLF), read back byte-equal
