# S81-G7 GREEN REPORT (agent: Opus 5.5, claude-opus-5-5), 2026-11-05

Unit: S81-G7 FOLLOWUPS = D16b + D17b + D22c (1)+(2) + D22d. Worktree C:/Users/SynAckITPC/Documents/AI/sc-s81-g7.
Base 6869a3e655805afd3adbba43f99578dd79585934. Branch feature/s81-g7-followups (git checkout -b, the one branch command).
HEAD 4b0f3b9c9192c3c6c69c883c0c4a60461aca9ec5 (ONE commit through the pre-commit hook: ruff + gitleaks "All checks passed!"; no --no-verify; no push, no PR, no rebase).
Report and PR body written through the shell (python) under S81-G7_green/.

## Frozen files (GC-1): re-hashed FIRST (before any edit) and LAST (working copy AND HEAD blob): all six equal
6fd81d37... d16b, 927dc060... d17b, ff9b45da... d22c profile, 79a33372... d22c varhint, 15c5dc0f... d22d, 8c793a16... golden. Committed with the GREEN files.

## Byte copies (before): S81-G7_green_before/ + SHA256SUMS.txt (10 files incl. data/variant_hint_learned.json a7f62a57...).

## Files changed (sha256 after, working copy CRLF where the base was CRLF; numstat +/-)
- app/services/kb_serve.py 82bb323e1e2662e0d83bd6a9af4a82f7714ea0821dd64566752c1ba047f3e898 (+16/-2): FUTURE_SKEW_SECONDS=300, beyond_skew(), classify future check, docstring line.
- app/services/kb_operator.py a99da79cbcff3edcdc7a013714485f486ec9f517e3c34f4efede55c523b960a6 (+17/-0): the captured_at field validator (kb_serve.beyond_skew, _now seam, naive->UTC), docstring line.
- app/services/structured_comparison_service.py 4f21254651a8081662528f98c46749daa4316354836d811c8390ee7ed282fdf0 (+50/-3): behavior_profile_rebuild_enabled(), _PROFILE_COMPARISON_COLUMNS_V2 / _PROFILE_EVENT_COLUMNS_V2, _profile_rows_v2(), the flag read as the first try statement, the two conditional select strings (OFF literals unchanged), ON-only normalisation.
- app/services/price_service.py 47c92eaed821f7b77bd8d61082020858281e3fa6b7f0ff70cf832a0d37bee97e (+3/-28): _VARHINT_LEARNED_PATH, _varhint_append_learned and its call deleted; comment + docstring rewritten (_varhint_normalized_family kept: still used by the verdict key).
- data/variant_hint_learned.json DELETED (git rm) (+0/-7).
- scripts/cron_kb_coverage.py 79f7c167202e62273074b1a8fefacb22841c3ccb0acaffd2f903798f4b357567 (+27/-5): PAGE_ORDER_COLUMN, _paged .order(...), exec/execute fallback, _past() (function-local kb_serve import), _field_shares/_ages read _past.
- scripts/cron_learning.py 6997e62399acddcc5c6f973940de71b808b38b8818b52a677de6d97645b3ec43 (+41/-9): _RENDER_ESCAPES + _render (str.translate), _read_by paging, dropped_fields counter (spec_wrong branch), main seeds dropped, the three render sites.
- tests/test_variant_llm_hint_b3b.py aeb8fc4d960085d0ad123714fb8f2c38817d9a15b805c024990541a134834d3d (+13/-20): E1 (fixture + 13 signatures).
- tests/test_s81_g5_gate_rows.py 306cd6acd7b9b8b3dc9037cd97ba65c568afe908f4a762c52c56c9601e348808 (+3/-2): E2 (GR6 0 -> 6 + the docstring sentence).
- CLAUDE.md 360cc6e18cbf2de8bddc260fd55c99f524a616f7ab7248c6e97101fa7d8f3ad9 (+8/-1): ONE S81-G7 block after the S81-G5 owner-steps bullet (heading + five rows + owner steps; added text pure ASCII; CRLF kept; no line with scoring_method and enum; no S23 forbidden phrase) + the :341 pointer clause.
git diff --stat: hunks only, no whole-file diff.

## Gates ([pyt] / [jest] lines; full list S81-G7_green/GATE_LINES.txt)
[pyt] tag=g7green-units-off start=2026-11-05 13:46:54 end=2026-11-05 13:47:01 elapsed=7s bound=600s status=OK rc=0 (60 passed; flag unset)
[pyt] tag=g7green-units-on start=2026-11-05 13:47:08 end=2026-11-05 13:47:15 elapsed=7s bound=600s status=OK rc=0 (60 passed; ENABLE_BEHAVIOR_PROFILE_REBUILD=true in the runner env only)
[pyt] tag=g7green-pins start=2026-11-05 13:47:38 end=2026-11-05 13:48:07 elapsed=29s bound=1200s status=FAIL rc=1 (3 failed = d16 r10 / d17 r9 / s19 r15 env CRLF; 946 passed; 14 files)
[pyt] tag=g7green-ciorder start=2026-11-05 13:49:18 end=2026-11-05 13:50:46 elapsed=88s bound=1200s status=FAIL rc=1 (3 failed = the same 3 env nodes; 1161 passed; hermeticity 1164; netguard 22 from 21 nodes, all test_hermeticity_pins by design)
[hermeticity] sentinel checked 60 test(s)
[netguard] blocked 0 attempt(s) from 0 node(s)
======================= 60 passed, 11 warnings in 5.20s =======================
[hermeticity] sentinel checked 60 test(s)
[netguard] blocked 0 attempt(s) from 0 node(s)
======================= 60 passed, 11 warnings in 5.54s =======================
[hermeticity] sentinel checked 949 test(s)
[netguard] blocked 0 attempt(s) from 0 node(s)
================= 3 failed, 946 passed, 12 warnings in 27.47s =================
[hermeticity] sentinel checked 1164 test(s)
[netguard] blocked 22 attempt(s) from 21 node(s)
=========== 3 failed, 1161 passed, 17 warnings in 86.19s (0:01:26) ============
[pyt] tag=g7green-comm-chunk_00 start=2026-11-05 13:52:14 end=2026-11-05 13:53:00 elapsed=46s bound=1200s status=OK rc=0
[pyt] tag=g7green-comm-chunk_01 start=2026-11-05 13:53:05 end=2026-11-05 13:53:42 elapsed=38s bound=1200s status=FAIL rc=1
[pyt] tag=g7green-comm-chunk_02 start=2026-11-05 13:53:45 end=2026-11-05 13:54:13 elapsed=28s bound=1200s status=OK rc=0
[pyt] tag=g7green-comm-chunk_03 start=2026-11-05 13:54:15 end=2026-11-05 13:55:09 elapsed=54s bound=1200s status=OK rc=0
[pyt] tag=g7green-comm-chunk_04 start=2026-11-05 13:55:12 end=2026-11-05 13:55:50 elapsed=38s bound=1200s status=OK rc=0
[pyt] tag=g7green-comm-chunk_05 start=2026-11-05 13:55:52 end=2026-11-05 13:56:08 elapsed=15s bound=1200s status=OK rc=0
[pyt] tag=g7green-comm-chunk_06 start=2026-11-05 13:56:10 end=2026-11-05 13:56:32 elapsed=22s bound=1200s status=OK rc=0
[pyt] tag=g7green-comm-chunk_07 start=2026-11-05 13:56:34 end=2026-11-05 13:57:08 elapsed=34s bound=1200s status=OK rc=0
[pyt] tag=g7green-comm-chunk_08 start=2026-11-05 13:57:11 end=2026-11-05 13:58:47 elapsed=96s bound=1200s status=OK rc=0
[pyt] tag=g7green-comm-chunk_09 start=2026-11-05 13:58:51 end=2026-11-05 13:59:07 elapsed=16s bound=1200s status=OK rc=0
[pyt] tag=g7green-comm-chunk_10 start=2026-11-05 13:59:10 end=2026-11-05 13:59:51 elapsed=41s bound=1200s status=OK rc=0
[pyt] tag=g7green-comm-chunk_11 start=2026-11-05 13:59:55 end=2026-11-05 14:00:12 elapsed=17s bound=1200s status=OK rc=0
[pyt] tag=g7green-comm-chunk_12 start=2026-11-05 14:00:15 end=2026-11-05 14:00:29 elapsed=15s bound=1200s status=OK rc=0
[pyt] tag=g7green-comm-chunk_13 start=2026-11-05 14:00:32 end=2026-11-05 14:01:07 elapsed=35s bound=1200s status=OK rc=0
[pyt] tag=g7green-comm-chunk_14 start=2026-11-05 14:01:10 end=2026-11-05 14:01:47 elapsed=37s bound=1200s status=FAIL rc=1
[pyt] tag=g7green-comm-chunk_15 start=2026-11-05 14:01:50 end=2026-11-05 14:02:16 elapsed=26s bound=1200s status=OK rc=0
[pyt] tag=g7green-comm-chunk_16 start=2026-11-05 14:02:18 end=2026-11-05 14:02:40 elapsed=22s bound=1200s status=FAIL rc=1
[pyt] tag=g7green-comm-chunk_17 start=2026-11-05 14:02:43 end=2026-11-05 14:04:33 elapsed=110s bound=1200s status=OK rc=0
[pyt] tag=g7green-comm-chunk_18 start=2026-11-05 14:04:35 end=2026-11-05 14:06:07 elapsed=91s bound=1200s status=OK rc=0
[pyt] tag=g7green-comm-chunk_19 start=2026-11-05 14:06:09 end=2026-11-05 14:08:04 elapsed=114s bound=1200s status=FAIL rc=1
[pyt] tag=g7green-comm-chunk_20 start=2026-11-05 14:08:06 end=2026-11-05 14:10:07 elapsed=120s bound=1200s status=FAIL rc=1
[pyt] tag=g7green-comm-chunk_21 start=2026-11-05 14:10:10 end=2026-11-05 14:10:44 elapsed=34s bound=1200s status=OK rc=0
[pyt] tag=g7green-comm-chunk_22 start=2026-11-05 14:10:47 end=2026-11-05 14:11:48 elapsed=61s bound=1200s status=OK rc=0
[pyt] tag=g7green-comm-chunk_23 start=2026-11-05 14:11:52 end=2026-11-05 14:12:32 elapsed=40s bound=1200s status=OK rc=0
[pyt] tag=g7green-comm-chunk_24 start=2026-11-05 14:12:36 end=2026-11-05 14:13:19 elapsed=43s bound=1200s status=OK rc=0
[pyt] tag=g7green-comm-chunk_25 start=2026-11-05 14:13:22 end=2026-11-05 14:14:04 elapsed=42s bound=1200s status=OK rc=0
[pyt] tag=g7green-comm-chunk_26 start=2026-11-05 14:14:07 end=2026-11-05 14:14:42 elapsed=35s bound=1200s status=OK rc=0
[pyt] tag=g7green-comm-chunk_27 start=2026-11-05 14:14:45 end=2026-11-05 14:15:06 elapsed=21s bound=1200s status=OK rc=0
[pyt] tag=g7green-secretscan start=2026-11-05 14:15:08 end=2026-11-05 14:15:34 elapsed=26s bound=600s status=OK rc=0
[jest] tag=g7green-fences start=2026-11-05 13:52:34 end=2026-11-05 13:52:54 rc=1
RECORDS n=414 skipped_no_html=6 distinct_queries=362 non_none=829 calls=1656
OVERALL SHA256 d2e16d30076129b526be97c2b783150390333337f694c206e69ea891d0b263cf
exit=0 start=2026-11-05 14:16:20 end=2026-11-05 14:23:57

Summary: RED files 60/60 OFF and 60/60 ON. Pins 946 + the 3 env CRLF nodes (identical to RED's prototype run). CI-order 1161 passed + the same 3 (base 1135 + 3 env + 26 RED).
Comm: 699 files at HEAD = RED's 691 minus tests/test_secret_scan_static.py (run alone: 31 passed) + 4 GREEN re-derivation members (tests/test_database_service.py, test_history.py, test_quality_ranker.py, test_verdict_exemplar_loader.py: substring hits of `_render` on `_renderable` / `_rendered` / `_renders_into_block`; none references an edited module; all green at HEAD, so no base run needed) + the 5 RED files; 28 chunks; 26397 passed, 49 skipped; HEAD FAILED set = 17 nodes, IDENTICAL to the reused base record ab9758ed... (LC-6); comm -13 EMPTY; comm -23 EMPTY.
Fences: jest 29.7.0 / node v24.11.1 by path through the junction: 13/14 suites, 236 passed, 4 failed = d5 react-native-gesture-handler, k2, k4, k5 of config/nativeBundle.w37 (the known drift nodes). Hook test files not run; full jest not run (LC-7).
Corpus gate at HEAD bytes: OVERALL SHA256 d2e16d30076129b526be97c2b783150390333337f694c206e69ea891d0b263cf == the RED base value (GC-4). Run alone (no pytest alive), start 14:16:20 end 14:23:57.
Lint: ruff 0.16.5 --select E9,F63,F7,F82: All checks passed; py_compile OK (8 files).
Hygiene: added-line sweep: no 8-digit run, no at sign beyond the @field_validator / @classmethod decorators, no 64-hex, no key shape; new constants FUTURE_SKEW_SECONDS, PAGE_ORDER_COLUMN, _PROFILE_COMPARISON_COLUMNS_V2, _PROFILE_EVENT_COLUMNS_V2, _RENDER_ESCAPES carry no gitleaks keyword. No dependency, migration, client file, requirements, .githooks. Never read .env; no flag set outside one runner call.

## Deviations
- D-G1: my own code differs from the prototype in shape: one shared rule kb_serve.beyond_skew() used by classify, the ingest validator and cron_kb_coverage._past (the prototype inlined the comparison three times); the scs select strings are chosen into locals before the lambdas and the normalisation is a module function _profile_rows_v2; _render uses a translate table; the D22d counter sits in the spec_wrong branch (equivalent: price / identity are clean literals).
- D-G2: 4 comm members added by the re-derivation (false-positive substring hits; green at HEAD); the union is 695 + 5 RED.
- D-G3: the commit trailer names my own model (Claude Opus 5.5) per the brief's "the trailer names your own model", not the Fable 5.1 text of the procedure template.
- D-G4: test_secret_scan_static.py is a member of the 691 and was run alone, not inside a chunk.

## Open questions: none. NOT MEASURED: none.
## git status --short after the commit: empty.
