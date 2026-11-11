# MON1 GREEN REPORT (LLM-CREDENTIAL-HEALTH; Opus 5.5 GREEN agent; 2026-11-11)

Unit MON1 (FOCUS). Base a74caba7e3ff66b12e94178c912197c845ccbd14; branch fix/inc-mon1-llm-credential-health; ONE commit c6592b539920b6189552dbc6aa23d7d7be435d91 (the hook passed: ruff tier + black). Not pushed, not rebased, no PR. `git status --short` is empty after the commit. Once merged, the unit is "merged, NOT yet proven" (H6).

## RED files (frozen; re-hashed at the start and the end, unchanged)
- tests/test_inc_mon1_credential_health.py 10061c0a64da034588602258d5020c015f97e95f7020e9eb0251a2c94bf56c71
- tests/test_inc_mon1_probe.py 2950c33e70d30a3dd69361a9726ce1421b778c4a9a00354067b213a530845880

## Files (sha256 after, at HEAD; the before copies are in MON1_green_before/ with SHA256SUMS.txt)
- .github/black-clean-paths.txt +5 cd12403b (5 ratchet entries, including the gate-rows file)
- CLAUDE.md +9/-1 4b9bb8be (the MON1 block after the S81-G10 block, before ## Tests; one sentence appended to the :341 pointer clause; CRLF kept)
- app/main.py +77/-1 35bcf11e (the snapshots, the probe start/stop, the /health entries, GET /health/llm)
- app/services/api_budget_service.py +11/-1 da636996 (the import; H1-H4)
- app/services/content_safety_service.py +7 a55c177a (the import; H7, H8)
- app/services/llm_router.py +7 c988a5f2 (the import; H5, H6)
- app/services/sentry_service.py +75 65a0a38e (capture_credential_alert, the scope recipe, the GC-5 fail-safe)
- app/services/serper_service.py +66 b2a7a46f (the key-pool state, H9)
- app/services/llm_credential_health.py NEW 331 c5b22404
- app/services/llm_credential_probe.py NEW 161 0fe08aaa
- tests/conftest.py +18 e8ca16ee (the autouse _reset_credential_health_state fixture)
- tests/test_s81_s03_llm_ledger_v2.py +6/-2 1220de8e (E1: K1 = "372cee1c8" + "d448ee35656cc891f83bc96902dc08ddf2e2ceb1fe5a928ab5733aa")
- tests/test_s81_s04_spend_breaker.py +3/-1 4e6cfa17 (E2: the test_p05 allowed set gains exactly llm_credential and serper_keys)
- tests/test_inc_mon1_gate_rows.py NEW 156 fb468da9 (G1 + the G1 control, G2, G3, G4)

## Every [pyt] line
```
[pyt] tag=inc-mon1-green-red-on start=2026-11-11 21:03:37 end=21:04:09 elapsed=32s bound=600s status=FAIL rc=1  (1 failed: Y01, a getenv over a parameter; fixed and re-run)
[pyt] tag=inc-mon1-green-red-on2 start=2026-11-11 21:05:03 end=21:05:34 elapsed=31s bound=600s status=OK rc=0  (135 passed with PROBE=true; [hermeticity] 135 checked; [netguard] blocked 0)
[pyt] tag=inc-mon1-green-red-off start=2026-11-11 21:05:41 end=21:06:27 elapsed=47s bound=600s status=OK rc=0  (135 passed with PROBE=false; [netguard] blocked 0)
[pyt] tag=inc-mon1-mut-mg1 elapsed=7s status=FAIL rc=1 (KILLED)
[pyt] tag=inc-mon1-mut-mg2 elapsed=5s status=FAIL rc=1 (KILLED)
[pyt] tag=inc-mon1-mut-mg3 elapsed=10s status=FAIL rc=1 (KILLED)
[pyt] tag=inc-mon1-mut-mg4 elapsed=9s status=FAIL rc=1 (KILLED)
[pyt] tag=inc-mon1-green-pins start=2026-11-11 21:08:18 end=21:11:08 elapsed=170s bound=1200s status=FAIL rc=1  (4324 passed, 2 failed: s24 test_r92_hygiene + test_p83_red_file_setenv_hygiene = the base CRLF rows, GC-2)
[pyt] tag=inc-mon1-gcomm-01..31  (bound 1200 each: 25 status=OK, 6 status=FAIL with base-record ids only; the full lines are in MON1_green/comm/pyt_lines.txt)
[pyt] tag=inc-mon1-green-claudemd start=2026-11-11 21:36:09 end=21:36:28 elapsed=19s bound=600s status=OK rc=0  (510 passed; the 6 CLAUDE.md readers, re-run after the CLAUDE.md edit)
[pyt] tag=inc-mon1-green-ciorder start=2026-11-11 21:36:37 end=21:38:00 elapsed=84s bound=1200s status=FAIL rc=1  (1492 passed; the same 2 base CRLF rows)
```

## Comm set
- 766 files = the RED comm_all.txt (763 files, set 23f5330f) plus the 2 RED files and the gate-rows file; no other file is newly referenced. 31 chunks: 29,536 passed, 56 skipped. HEAD FAILED ids: 27 (comm/head_failed.txt). Base record: 28 ids.
- branch-only-NEW: EMPTY. Base-only: tests/test_s80_url_mode_v2.py::test_deadline_yields_timeout_503[POST], the known wall-clock flake, which passed at HEAD.
- The E-row nodes (test_k1, test_p05) are green at HEAD.

## Gate-row mutants (GC-10; on the GREEN bytes; the lock was created and removed; every restore sha256-verified)
MG1: the fail-safe send replaced by return; G1 kills it. MG2: the suppressed WARNING removed; G2 kills it. MG3: level info for the state test; G3 kills it. MG4: the cool-down keyed on the state alone; G4 kills it. 4/4 KILLED, each on an AssertionError. The 36 RED mutants of GC-3 were not re-run on the GREEN bytes.

## Hygiene
- ruff (tier) and py_compile: clean on 14 files. black 26.5.1: clean on the ratchet files.
- Added lines: ASCII only, no 8-digit run, no key shape.
- New files are LF; edited files keep CRLF; no whole-file diff.
- No .env read, no production probe, no package manager run.

## Deviations
1. The commit trailer names Opus 5.5, my own model (the prompt's first paragraph). The step-7 template asked for "Fable 5.1".
2. classify takes an optional third argument, source (default dispatch), which carries R-MON1-18. The rows call the two-argument form. note_failure and note_success return None.
3. R-MON1-18's INFO line is its own line, `[LLM_PROBE] inconclusive failure provider=%s class=%s (first in this process)`, logged beside the per-tick L4 line.
4. The serper_keys event shares the cool-down: one emit_alert, keyed on (kind, provider, state).
5. capture_credential_alert drops a call whose kind, provider or state is outside the closed sets.
6. tests/test_inc_mon1_gate_rows.py was added to the black ratchet.
7. Only the GC-11 lifespan-first CI-order run was made. The pure-alphabetical second run of spec 7.3 was not made.
8. The RED comm list path is <SP>/MON1/red/comm_all.txt, not <SP>/MON1_red/comm_files.txt.

## Open questions
- O2 and O3 are open (the owner's).
- A1-3: OpenAI stays "in use" while OPENAI_API_KEY is set; no flag moves it out.
- Owner step 4 uses `railway run -s web python -c ...` from the ops checkout. The relay should confirm that this is the ops lane's run path.
