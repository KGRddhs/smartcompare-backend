# B3A RED notes
start 2026-10-17T08:00:17
08:00 read common/rulings/spec/review. toolchain: node v24.11.1 jest 29.7.0 tsc 5.9.3 eslint v9.39.4; @babel/core + .bin/jest present.
08:30 wrote fixture + 7 test files under __tests__/b3a. Now base run.
[jest] tag=b3a-red-base-1 start=2026-10-17 08:31:13 end=2026-10-17 08:31:29 rc=1
[jest] tag=b3a-red-base-2 start=2026-10-17 08:32:48 end=2026-10-17 08:33:03 rc=1
08:38:33 prototype applied
[jest] tag=b3a-red-proto-1 start=2026-10-17 08:38:42 end=2026-10-17 08:39:03 rc=1
[jest] tag=b3a-red-proto-2 start=2026-10-17 08:39:34 end=2026-10-17 08:39:54 rc=0
Test Suites: 7 passed, 7 total
Tests:       84 passed, 84 total
[jest] tag=b3a-red-proto-subset start=2026-10-17 08:40:19 end=2026-10-17 08:40:38 rc=1
Test Suites: 2 failed, 3 skipped, 165 passed, 167 of 170 total
Tests:       13 failed, 13 skipped, 5 todo, 1718 passed, 1749 total
Snapshots:   0 total
[jest] tag=b3a-red-proto-subset-2 start=2026-10-17 08:41:55 end=2026-10-17 08:42:16 rc=1
Test Suites: 1 failed, 3 skipped, 166 passed, 167 of 170 total
Tests:       4 failed, 13 skipped, 5 todo, 1727 passed, 1749 total
Snapshots:   0 total
[tsc] tag=b3a-red-proto start=2026-10-17 08:42:30 end=2026-10-17 08:42:39 rc=0
[eslint] tag=b3a-red-proto start=2026-10-17 08:42:50 end=2026-10-17 08:43:06 rc=0

✖ 27 problems (0 errors, 27 warnings)
  0 errors and 12 warnings potentially fixable with the `--fix` option.

08:45:27 mutation batch 1 start
08:51:40 mutation batch 2 start (M20 rerun with r28b + M23-M45)
[jest] tag=b3a-red-proto-final start=2026-10-17 08:57:44 end=2026-10-17 08:58:00 rc=0
Test Suites: 7 passed, 7 total
Tests:       85 passed, 85 total
restore: 24 files compared, mismatches=[]
differs from snapshot: 0 []
created present: []
?? SmartCompareApp/__tests__/b3a/
?? SmartCompareApp/__tests__/fixtures/b3a_copy.json
[jest] tag=b3a-red-base-final start=2026-10-17 08:58:25 end=2026-10-17 08:58:41 rc=1
Test Suites: 7 failed, 7 total
Tests:       64 failed, 21 passed, 85 total
COUNTS red_rows=64 pin_rows=21 problems=[]
[pyt] --- summary lines ---
============== 1846 passed, 4 deselected, 13 warnings in 57.00s ===============
[netguard]   tests/test_timeout_partial_integration.py::TestRoutePartialReturns200::test_post_partial_returns_200_parity [sentinel] socket.create_connection neutralized.supabase.invalid:443
[netguard]   tests/test_timeout_partial_integration.py::TestRouteTimeoutMapsTo503::test_get_timeout_maps_to_503_with_code_preserved [sentinel] socket.create_connection neutralized.supabase.invalid:443
[netguard]   tests/test_timeout_partial_integration.py::TestRouteTimeoutMapsTo503::test_post_timeout_maps_to_503_parity [sentinel] socket.create_connection neutralized.supabase.invalid:443
[netguard]   tests/test_timeout_partial_integration.py::TestInsufficientDataUnchanged::test_insufficient_data_passthrough [sentinel] socket.create_connection neutralized.supabase.invalid:443
[netguard]   tests/test_timeout_partial_integration.py::TestStreamingTimeoutD2Contract::test_stream_hardcap_yields_stream_timeout_partial [egress] socket.getaddrinfo api.openai.com:443
[netguard]   tests/test_timeout_partial_integration.py::TestStreamingTimeoutD2Contract::test_stream_timeout_copy_has_no_forbidden_vocab [egress] socket.getaddrinfo api.openai.com:443
[pyt] tag=b3a-red-base-commA start=2026-10-17 08:59:25 end=2026-10-17 09:00:25 elapsed=59s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\2dae842f-c924-40f1-bd05-6b610eed0f5f\scratchpad\b3a_red\base_commA.log
[pyt] --- summary lines ---
======================= 350 passed, 1 warning in 37.11s =======================
[hermeticity] sentinel checked 350 test(s)
[netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=b3a-red-base-commB start=2026-10-17 09:00:39 end=2026-10-17 09:01:19 elapsed=40s bound=600s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\2dae842f-c924-40f1-bd05-6b610eed0f5f\scratchpad\b3a_red\base_commB.log
[jest] tag=b3a-red-proto-verify start=2026-10-17 09:01:36 end=2026-10-17 09:02:39 rc=127
restore: 24 files compared, mismatches=[]
differs from snapshot: 0 []
created present: []
