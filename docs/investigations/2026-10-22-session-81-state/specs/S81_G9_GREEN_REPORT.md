# S81-G9 GREEN REPORT (G9 FOLLOWUPS: S81-16c + D17c (+ D17d PINs) + S81-22d + S81-23b)

Agent: GREEN, Opus 5.5 (claude-opus-5-5). Base 39ac80ba437760d1a77eaac9670faeea505f08f4; HEAD b39e265fa9d6f808251b8070ab72125660d98ca8 on feature/s81-g9-followups (ONE commit through the hook; no push, no PR, no rebase). Written through the shell (python gen_report.py over this template). Binding inputs read in full: s81-common.txt, RULINGS_S81_G9, GATE_S81_G9, S81_G9_BRIEF, RULINGS_S81_16C, the spec (f94aaf71...), the RED report.

## 1. Frozen RED files (GC-1)

Re-hashed first (before any edit) and last (the committed blobs at HEAD): all four EQUAL (8dca7516..., 8a6ced21..., 6faeecc8..., af701284...).

## 2. Files (byte copies before: <scratchpad>/S81-G9_green_before/ + SHA256SUMS.txt)

| file | sha256 before (working copy) | sha256 after (working copy) | LF blob after |
|---|---|---|---|
| CLAUDE.md | 07ec1c0cdf372137a3c0f219ab8f63c3504b80f09bd9ac3d1c2f3b5f210fa2d0 | 9d99e9754fd67ad9183a82272497ff710030fcb5626e4d67787d81d00617454f | 4defe23f547443f34a01ab1af3e60a30d677423d2d74b7d08057ba6a583b0f86 |
| app/services/scrapedo_service.py | 81ac20db7975c14117983edbc925879b41352789cba83d114b595488025fc23f | 920d54782faa4c9ce40ae1ba298785cd0a89a9bdc2025229cdba4e391c86ea2b | 3c5678ed68143c1a513c4bf316e122a8581657c41892ef1965309b8e6f637a83 |
| app/services/source_router.py | b696d10d1322ed0cafa8888ce70508d4430f34ae1bf460f0b872f09ddf402de9 | 958e7c749af26e01b5953172d5213f7f3aca37a239cf59084e024b123a429ebf | c3d3e6eafa449dce6e0b4254fa6cf0a279aa5d28a429961c9e729fda43d136c5 |
| app/services/structured_comparison_service.py | 42716f8490fc3d85b9e06bd6d5f7d27fc32cc2e1d1d54121ffbf9a23a7c17737 | 3678b52ea84c73892f9fb244ba83376e2ed49c5e35d4457e9408662d5313d0d5 | ab7eb4a1a5116d01a0146d567ee72ff60806feeab54c17ac89b8792924a12423 |
| docs/policies/2026-08-31-robots-unreadable-ruling.md | 2e2ede4647b9c59b819e4c3363aae252e01d03ad08f129012ece42d7a4726d04 | 25761d20c92476d8cc920152627778414f85fef510ba12ec398acce2db4cb90e | 58d75e38e685ac25cd7d06219b80d350cec114933512b6ec078f4af6ed837c2a |
| docs/policies/2026-11-07-wdqs-robots-exemption.md | (new) | 9613f9feb7161b0ff899b8ddfedb9082da17557408c6b97629d27f1e814cb7dd | 9613f9feb7161b0ff899b8ddfedb9082da17557408c6b97629d27f1e814cb7dd |
| scripts/ab_render_providers.py | 920caed21f22abc72200de650e453f6c71c1212daa37d63286ab4408d4d44033 | cd757b9c547f780210071c75b5ea3aa95547f665bc82d9dc17d43429d23ecef0 | c8f8be0b7b4a2d593b91b9631902073425c43640c5ddaf5ba37dd4124a0e541c |
| scripts/cron_kb_coverage.py | 79f7c167202e62273074b1a8fefacb22841c3ccb0acaffd2f903798f4b357567 | 6ae3174eed7c49efe007c1a6e8da451ee9300d5708bd4af75dbede59d3332ae0 | f9a5eb688f6c0321521ce234da9fb74ac33138326ace4a14ec6ba9ca493b8016 |
| scripts/seed_kb_brands_wikidata.py | 61c54417802dd5ab970bde94580598b07bc76ec29faa079362d8b642639cf031 | bdbc2fbfce1898af4c935f37fd1b45c2a90a0501e2c7e75cf8a09bdd86243285 | 6691856cdfb850b66c21bdf9817d08f43c6e71023664db3a80d76071e631abb6 |
| tests/test_fragrance_content_quality.py | e3c5963407594f4611f755548cd8e184cc2bd5e763e055683f5b1942488c7185 | 2d1f775b80f0467e9f62861e79811822a45840ef1d5b77830740e3a0cf2ea47a | 959ad7a69faca71133732cfa99d83456acdff2d3c8948593cddd804538520ecf |
| tests/test_s81_s03_llm_ledger_v2.py | 106c7fcb25d32475522bff4b5c30e50a3a2a8e710af55f482060ff231ce52942 | 72fa8dc868face4d5947a4f0f3f92fac56b5f642b205054f15dbc15ab98edabc | 4ccc2c5641acf3bb02f4bb06f4f257004e1aa97920afa3579c423d24011e6083 |
| tests/test_s81_s23_bypass_retire.py | 28d93fa602d275aecf29b294948eaab1b866bc7c18ae35132a7a224fe2d4391d | 2a11b136f5430ab0b3334ef1af36880db041691fcae7f0cf567d7feb6ed7d445 | e686619acc3797d3914cfd9765dd06ff3cb8afa1af8fa3908b076895db899e6d |
| tests/test_s81_s16c_wdqs_exemption.py | (new) | 8dca75163ca4c2c0aaf1ae47bbd2dfcb03b95aca0b25a001dce359a289711e94 | 8dca75163ca4c2c0aaf1ae47bbd2dfcb03b95aca0b25a001dce359a289711e94 |
| tests/test_s81_d17c_coverage_hosts.py | (new) | 8a6ced21d2a7bc27d67e2bdbdd5fbde89c52de567150bd914d3c767800464488 | 8a6ced21d2a7bc27d67e2bdbdd5fbde89c52de567150bd914d3c767800464488 |
| tests/test_s81_s22d_ledger_pins.py | (new) | 6faeecc8c05ce6809d19c4b4ee70d5bf8e9c205022e4677e7364925153ea519b | 6faeecc8c05ce6809d19c4b4ee70d5bf8e9c205022e4677e7364925153ea519b |
| tests/test_s81_s23b_scrapedo_super_retire.py | (new) | af7012844356d8a73fc415626a63194fdcce32695ecc30bf0db88e0bdda0d92e | af7012844356d8a73fc415626a63194fdcce32695ecc30bf0db88e0bdda0d92e |

git diff --stat 39ac80ba..HEAD: 16 files, +1084 / -66, hunks only (no whole-file diff). The policy doc's committed blob sha256 9613f9fe... = the scratchpad bytes (3,986 B, LF). Added text ASCII (CLAUDE.md replacements encoded as ASCII; the new docs / test files 0 bytes > 127). ruff --select E9,F63,F7,F82 + py_compile clean on the 13 Python files; the hook passed (ruff All checks passed; gitleaks clean).

## 3. Runs ([pyt] lines, stdout captured)

- `[pyt] tag=g9green-red-off start=2026-11-07 13:35:21 end=2026-11-07 13:35:32 elapsed=11s bound=600s status=OK rc=0 | 68 passed, 10 warnings in 10.08s`
- `[pyt] tag=g9green-red-on start=2026-11-07 13:36:26 end=2026-11-07 13:36:36 elapsed=10s bound=600s status=OK rc=0 | 68 passed, 10 warnings in 9.36s`
- `[pyt] tag=g9green-s03-off start=2026-11-07 13:36:44 end=2026-11-07 13:36:56 elapsed=12s bound=600s status=OK rc=0 | 226 passed, 11 warnings in 10.61s`
- `[pyt] tag=g9green-s03-on start=2026-11-07 13:37:03 end=2026-11-07 13:37:15 elapsed=12s bound=600s status=OK rc=0 | 226 passed, 13 warnings in 10.96s`
- `[pyt] tag=g9green-ciorder start=2026-11-07 13:37:23 end=2026-11-07 13:38:59 elapsed=96s bound=1200s status=FAIL rc=1 | 7 failed, 1622 passed, 15 warnings in 93.88s (0:01:33)`
- `[pyt] tag=g9green-secretscan start=2026-11-07 13:39:07 end=2026-11-07 13:39:17 elapsed=10s bound=600s status=OK rc=0 | 31 passed, 1 warning in 8.65s`
- `[pyt] tag=g9green-comm-c00 start=2026-11-07 13:41:07 end=2026-11-07 13:41:47 elapsed=40s bound=1200s status=FAIL rc=1 | 2 failed, 916 passed, 19 warnings in 38.22s`
- `[pyt] tag=g9green-comm-c01 start=2026-11-07 13:41:54 end=2026-11-07 13:42:23 elapsed=29s bound=1200s status=OK rc=0 | 592 passed, 23 warnings in 27.29s`
- `[pyt] tag=g9green-comm-c02 start=2026-11-07 13:42:57 end=2026-11-07 13:43:39 elapsed=43s bound=1200s status=OK rc=0 | 1117 passed, 5 deselected, 13 warnings in 41.18s`
- `[pyt] tag=g9green-comm-c03 start=2026-11-07 13:43:47 end=2026-11-07 13:44:53 elapsed=66s bound=1200s status=OK rc=0 | 1189 passed, 1 skipped, 3 deselected, 11 warnings in 64.98s (0:01:04)`
- `[pyt] tag=g9green-comm-c04 start=2026-11-07 13:45:02 end=2026-11-07 13:45:22 elapsed=20s bound=1200s status=OK rc=0 | 621 passed, 1 xfailed, 13 warnings in 18.69s`
- `[pyt] tag=g9green-comm-c05 start=2026-11-07 13:45:31 end=2026-11-07 13:45:50 elapsed=19s bound=1200s status=OK rc=0 | 430 passed, 11 warnings in 16.51s`
- `[pyt] tag=g9green-comm-c06 start=2026-11-07 13:45:58 end=2026-11-07 13:46:22 elapsed=24s bound=1200s status=OK rc=0 | 485 passed, 2 skipped, 1 warning in 22.87s`
- `[pyt] tag=g9green-comm-c07 start=2026-11-07 13:47:14 end=2026-11-07 13:47:56 elapsed=43s bound=1200s status=OK rc=0 | 986 passed, 10 warnings in 39.39s`
- `[pyt] tag=g9green-comm-c08 start=2026-11-07 13:48:04 end=2026-11-07 13:49:18 elapsed=73s bound=1200s status=OK rc=0 | 1428 passed, 1 skipped, 5 deselected, 18 warnings in 70.31s (0:01:10)`
- `[pyt] tag=g9green-comm-c09 start=2026-11-07 13:49:26 end=2026-11-07 13:50:09 elapsed=43s bound=1200s status=OK rc=0 | 607 passed, 1 xfailed, 12 warnings in 39.69s`
- `[pyt] tag=g9green-comm-c10 start=2026-11-07 13:50:16 end=2026-11-07 13:50:34 elapsed=18s bound=1200s status=OK rc=0 | 253 passed, 12 warnings in 16.51s`
- `[pyt] tag=g9green-comm-c11 start=2026-11-07 13:50:41 end=2026-11-07 13:51:02 elapsed=21s bound=1200s status=OK rc=0 | 496 passed, 1 skipped, 6 deselected, 2 warnings in 19.89s`
- `[pyt] tag=g9green-comm-c12 start=2026-11-07 13:51:10 end=2026-11-07 13:51:44 elapsed=34s bound=1200s status=OK rc=0 | 3792 passed, 22 skipped, 4 warnings in 32.03s`
- `[pyt] tag=g9green-comm-c13 start=2026-11-07 13:51:51 end=2026-11-07 13:52:30 elapsed=39s bound=1200s status=FAIL rc=1 | 4 failed, 724 passed, 3 skipped, 3 deselected, 18 warnings in 37.73s`
- `[pyt] tag=g9green-comm-c14 start=2026-11-07 13:52:38 end=2026-11-07 13:52:59 elapsed=21s bound=1200s status=FAIL rc=1 | 420 passed, 3 skipped, 10 deselected, 1 xfailed, 11 warnings, 2 errors in 20.00s`
- `[pyt] tag=g9green-comm-c15 start=2026-11-07 13:53:07 end=2026-11-07 13:53:26 elapsed=20s bound=1200s status=OK rc=0 | 343 passed, 1 skipped, 3 deselected, 13 warnings in 18.29s`
- `[pyt] tag=g9green-comm-c16 start=2026-11-07 13:53:34 end=2026-11-07 13:56:18 elapsed=165s bound=1200s status=OK rc=0 | 728 passed, 19 warnings in 162.83s (0:02:42)`
- `[pyt] tag=g9green-comm-c17 start=2026-11-07 13:56:26 end=2026-11-07 13:58:08 elapsed=102s bound=1200s status=OK rc=0 | 1185 passed, 262 warnings in 100.63s (0:01:40)`
- `[pyt] tag=g9green-comm-c18 start=2026-11-07 13:58:17 end=2026-11-07 13:59:24 elapsed=67s bound=1200s status=FAIL rc=1 | 7 failed, 1865 passed, 12 warnings in 65.40s (0:01:05)`
- `[pyt] tag=g9green-comm-c19 start=2026-11-07 13:59:32 end=2026-11-07 14:01:07 elapsed=95s bound=1200s status=FAIL rc=1 | 8 failed, 3084 passed, 62 warnings in 92.34s (0:01:32)`
- `[pyt] tag=g9green-comm-c20 start=2026-11-07 14:01:14 end=2026-11-07 14:01:59 elapsed=44s bound=1200s status=FAIL rc=1 | 2 failed, 1570 passed, 1 xfailed, 43 warnings in 42.77s`
- `[pyt] tag=g9green-comm-c21 start=2026-11-07 14:02:06 end=2026-11-07 14:03:15 elapsed=69s bound=1200s status=OK rc=0 | 860 passed, 13 warnings in 67.59s (0:01:07)`
- `[pyt] tag=g9green-comm-c22 start=2026-11-07 14:03:23 end=2026-11-07 14:03:44 elapsed=21s bound=1200s status=OK rc=0 | 726 passed, 2 skipped, 2 deselected, 16 warnings in 19.97s`
- `[pyt] tag=g9green-comm-c23 start=2026-11-07 14:03:54 end=2026-11-07 14:04:38 elapsed=45s bound=1200s status=OK rc=0 | 437 passed, 6 skipped, 10 deselected, 19 warnings in 42.97s`
- `[pyt] tag=g9green-comm-c24 start=2026-11-07 14:04:46 end=2026-11-07 14:05:38 elapsed=52s bound=1200s status=OK rc=0 | 496 passed, 6 deselected, 12 warnings in 50.21s`
- `[pyt] tag=g9green-comm-c25 start=2026-11-07 14:05:46 end=2026-11-07 14:06:25 elapsed=40s bound=1200s status=OK rc=0 | 1015 passed, 35 xfailed, 12 warnings in 38.32s`
- `[pyt] tag=g9green-comm-c26 start=2026-11-07 14:06:34 end=2026-11-07 14:06:59 elapsed=25s bound=1200s status=OK rc=0 | 682 passed, 10 skipped, 11 warnings in 23.64s`
- `[pyt] tag=g9green-comm-c27 start=2026-11-07 14:07:06 end=2026-11-07 14:07:15 elapsed=8s bound=1200s status=OK rc=0 | 27 passed, 11 warnings in 6.54s`
- `[pyt] tag=g9green-comm-x00 start=2026-11-07 14:07:26 end=2026-11-07 14:07:41 elapsed=15s bound=1200s status=OK rc=0 | 286 passed in 13.87s`
- `[pyt] tag=g9green-comm-x01 start=2026-11-07 14:07:49 end=2026-11-07 14:07:52 elapsed=3s bound=1200s status=OK rc=0 | 25 passed, 1 warning in 2.30s`
- jest (the fourteen fences + b3a/nativeStrings by path through the junction, untouched): [jest] tag=g9green-fences start=2026-11-07 13:24:16 end=2026-11-07 13:24:29 rc=1 node=v24.11.1 jest=29.7.0 / Test Suites: 1 failed, 14 passed, 15 total / Tests:       4 failed, 242 passed, 246 total; the one red suite is config/nativeBundle.w37 with exactly d5, k2, k4, k5 (the four known drift nodes); b3a green. FULL jest NOT run (LC-7).
- corpus gate at HEAD, every flag OFF, alone (no pytest beside it): start=2026-11-07 14:10:39 end=2026-11-07 14:17:35 rc=0 / RECORDS n=414 skipped_no_html=6 distinct_queries=362 non_none=829 calls=1656 / OVERALL SHA256 cce256e1940c91a1a3b07e181a91b870d26ffce7247559630ccb66b35d8fe60c -> EQUAL to cce256e1940c91a1a3b07e181a91b870d26ffce7247559630ccb66b35d8fe60c.
- the four hook test files: NOT run (no .githooks change).

## 4. Results

- RED files: 68 / 68 unset; 68 / 68 with ENABLE_KB_BRANDS=true ENABLE_KB_COVERAGE_ROLLUP=true ENABLE_COMPARE_RUN_LEDGER=true exported in the runner call only.
- The S03 file + the 22d file: 226 passed unset; 226 passed with ENABLE_COMPARE_RUN_LEDGER=true exported.
- CI-order set (spec 12.1): 7 failed / 1622 passed; the 7 = the CRLF working-copy class (s16 r27 x5, d17 r9, s22 b02), as at base and at the RED prototype. On LF bytes the two edited scripts carry no CR and no byte > 127.
- tests/test_secret_scan_static.py alone: 31 passed.
- Comm set: the record's 673 (COMM_SET.txt, sha fe55771e...) + the 4 RED files = 677 files in 28 chunks (c00-c27); HEAD FAILED 25 = the stored record's 25 ids exactly (the STORED base record 39ac80ba/fe55771e... REUSED, LC-6); comm -13 EMPTY; comm -23 EMPTY.
- GREEN comm additions: 27 files (x00 / x01): an AST import-graph re-derivation (comm_rederive.py: the importer closure of the edited code modules incl. source_router / structured_comparison_service / ab_render_providers, with the `from app.services import <module>` and import_module string forms, test-importer fixpoint) plus a grep for source_router / structured_comparison_service / docs/policies readers found 27 test files outside the record's 673 (e.g. tests/test_ourshopee_demotion.py imports source_router; list <scratchpad>/S81-G9_green/extra_members.txt). All 27 at HEAD: 286 + 25 passed, 0 failed, so branch-only-new stays EMPTY without a base run.

## 5. Deviations / decisions

- D-G1 (comm set): the record's 673 appears to miss 26 importers of closure modules in the `from app.services import X` form (+1 grep hit, test_async_utils); GREEN ran them at HEAD (all green). For the adversary's re-derivation; no base run was needed (no HEAD failure).
- D-G2 (16c Retry-After): an HTTP-date Retry-After is honoured when in the future (the delta vs common._now(); above the cap = give up); a past or unparseable date carries no wait and falls to the body hint, else the cap (R7 date_body45 holds because the Rig clock 2026-11-01 is after the header date). The prototype ignored dates; GC-6 names seconds or an HTTP date. Stated limit L-S16c-7.
- D-G3 (16c rule set): order-insensitive multiset (sorted-list) equality: a duplicated exempt rule refuses (fail closed); R-G9-4 says set equality, so this is stricter on duplicates only.
- D-G4 (stated-limit ids): GC-3 assigns L-S16c-5 to the M5 equivalence, so the spec's L-S16c-5 (the production agent's 429 behaviour unmeasured) is L-S16c-6; L-S16c-7 added (D-G2 / D-G3). L-D17c-5 = GC-4 D6 (the SDK private seam).
- D-G5 (23b wording): ab_render_providers.py: the legacy write deleted, the :33 comment reworded, plus its two docstring mentions and one config comment (no behaviour beyond the deleted write; it never sets ENABLE_SCRAPEDO_SUPER); EK3 = the 7 env-key edits + the 4 docstring lines of those rows (11 lines); source_router 5 comment / docstring lines + structured_comparison_service 1 comment line: SCRAPEDO_SUPER -> ENABLE_SCRAPEDO_SUPER (names only).
- D-G6 (D17c): the pipeline_refused label applies only to an AttributeError raised by the exec / execute call (narrow wrap); every failed family (registry included) counts once in not_built (R-G9-2); the 0-host skip returns before any pipeline() call.
- D-G7 (trailer): the commit trailer names the agent's own model (Co-Authored-By: Claude Opus 5.5) per GC-8 / s81-common, not the template's Fable line.
- D-G8: mutants not re-run at GREEN (the RED's 28 stand: 27 KILLED + 16c-M5 equivalent; GC-9 gives re-application to the adversary). A full-config `ruff check` flags B009 on the unchanged base line cron_kb_coverage.py:320 (pre-existing; the house select and the hook are clean).
- D-G9: CLAUDE.md :92 apply record and the S81-08b row NOT edited (GC-6 / R-G9-7: the S81-24 final round carries them).

## 6. Open questions

- Q1: do the 27 GREEN comm additions join the comm set of record for the final round (a derivation gap in the `from pkg import module` form)?
- Q2: confirm D-G2 (the HTTP-date handling) and D-G3 (the multiset comparison).

## 7. State

git status --short at the end: empty (the gitignored .qa-s80/ only). Branch feature/s81-g9-followups at b39e265f; nothing pushed. No pytest / jest of mine alive. PR body: <scratchpad>/S81-G9_green/PR_BODY.md (16,420 bytes; ASCII except the attribution line).
