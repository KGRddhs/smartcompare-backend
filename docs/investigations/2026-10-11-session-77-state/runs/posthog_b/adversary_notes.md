# phadv notes (adversary S77 POSTHOG B) start 2026-10-12 04:05 AST
- pre.sha recorded, 17 files, matches GREEN table; snapshot in snap/
- 04:11 baseline RED files: [pyt] tag=phadv-base elapsed=9s status=OK rc=0 (139 passed)
- 04:14 probes (temp file tests/test_zz_phadv_probe.py, removed): [pyt] tag=phadv-probe elapsed=4s status=FAIL rc=1 (7 failed = defects reproduced, 1 passed control)
  P1 stale pref cache after opt-out (same process) REPRODUCED
  P2 capture of a user marked deleted during the pref read REPRODUCED
  P4 PUT /auth/preferences erases analytics_enabled False REPRODUCED (MAJOR)
  P5 cohort should_seed({analytics_enabled: False}) True -> whole-object reseed REPRODUCED
  P6 scheme-less link keeps its query REPRODUCED
  P7 failed pref read not cached (re-read every capture) REPRODUCED
  P8 track_after_persist follow-ups wait 0.39 s for the analytics read REPRODUCED
- 04:15-04:22 mutation harness mut.py: 30 RED mutants + 4 legal mutants; survivors M03 M10 M15 M16 M19(equivalent) M23; L01-L04 killed
- 04:23 fill_in_legal --dry-run rc=0 (no would-write), render --check rc=0
- 04:24 adjacent pins w314 + u8d sentry: [pyt] tag=phadv-adj status=OK (159 passed)
- httpx.AsyncClient ctor+enter on loop: min 179 ms p50 181 ms max 266 ms (30 runs, this box)
- real posthog 7.60.1 adds only $geoip_disable $is_server $lib $lib_version $os $os_version $python_runtime $python_version (no $ip)
- pre.sha == post.sha IDENTICAL (17 files); lock removed
