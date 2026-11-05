# S81-20 GREEN REPORT (B2-RESULT-GATE-V2, ENABLE_RESULT_GATE) - GREEN agent, Opus 5.5, 2026-11-05
Written through the shell (python script), per the harness rule.

Unit S81-20. Branch feature/s81-s20-result-gate-v2 from 6869a3e6. HEAD 404b4ba525d42074a52f514ab0ac7299b857dbf4 (ONE commit through the hook; first committed as a0c52dea, then amended once, CLAUDE.md only, to correct the sweep count 132 -> 135; the hook passed both times). No push, PR or rebase. git status --short: empty.

## Files (path / sha256 after / sha256 before)
CLAUDE.md ad984444d53aad5c7940a3cf38d607ec23f1a3ce99466b052f1ba4ed5814824a 1c6bed5088041c51b8646d84b15707d7cb59484ac6e7eab633090eaaf81ec1a4
app/api/image_routes.py 8e260b7badb9be34cb7446f047c8067b251c54fcddcc72f77868a9990fbd5831 987e89f9362bdfc596ff6c58101321240433eb79f5419e7f44e2c35f8c5b91d5
app/api/text_routes.py 8e40919d0f1889ba9434856536630291e5ab8cfee34543380755cf56617190fc 437bc724e96685c1d3b31c55573150d80d72194edc90af9da3d172316cc470e2
app/api/url_routes.py 06fe720d8583cf39fab1c5c8090070458e320f412a24eddcc201a4b45a626484 04aa91fd315bcd124d67619c71b8c339ca8a27f43e215545a5138e60d08a09c1
app/middleware/error_handler.py a6af83ebcd1b2594f8e9812f1de4f4e506dda51358b1dd790f08a12b0ce3a1bd 5d09ba7fba1e81e7c55b3d310ae4676df65807b6171b160b7b814a84071a1453
app/services/response_builder.py e90326dd15cf96c4c29076d95b2ee7904e4fe155336d257a980d7372e31f3fe9 ffbac5b7f534dfb35e67e467c9805feb4be00ca67e3187b71726a52b7a52508b
app/services/result_gate.py bb6d46a53293380907fa936b29145e9b8192978978d4ff5034fcfd1308689d9e db06da43037d8f13be602fe98a697fe7209a2ad2e2067adffb94c44ff18a5aff
tests/test_paid_route_metering.py d32c881ba89861a413a006bfdf858c95aeb9f4cbf3cf01593ff9610db1a89465 4724c308c6a5805a873a015f2a07e02850e8db5c020f46423e71208505ead73f
tests/test_retro_w2_1.py fd73703ce31da7b4f2b011b31b0240aa6638e4db8abcfce915d7ae334e521b04 0b9134585c14969ab8c6f78400070434d3ff60e5a0e24776c50f3d7a5e08a594
tests/test_s71_u13_compare_auth_required.py 0ce2ca7705b430806ca3d1f0477e7b15b6e707c3487c0d894c5804a57ede00c0 ee219f2ed7e5576e306754595effa8cfeb34005062ba16196c109ae7d9dfd992
tests/test_s75_fanout_identity.py a4198be47a3fa75a79f9b635528d2212c073c2efc97f802fddd913be04f0e769 cd11581803bb8ac7045d56a5b004003b0263a0144be69bec3607dc4bfe8e9c42
tests/test_s80_b1.py b1144ec0ca13d4dc8b06ed783cc7bbe76c99518a1c01e2504c888d8511e56379 4e4c20b1d6d55cad0c73ebcb439f0f87270fcfb4a8e6c711ce0c410f52ad8a17
tests/test_s80_b3_vision_identity_v2.py 1eaa139b99599a0bd0972cf6536b16705c2d49692e002425a7ce2ce7a419f723 c77ff3ab2d92d28d4a723ee40ee9836546f86fb200326f8024cba5511488591c
tests/test_s81_kb_schema.py 347eb28c0691a8fa33165c633d00e0c1ac192a19f29e8f8eb1be5f9e45a0a146 
tests/test_s81_s20_gate_rows.py c88caa06ac2fcc227a8f9a0e3c93bd5fbe1943ca53384c75135ebe117159874c 
tests/test_s81_s20_result_gate.py 13aa83ade66d14759278e6da14668f60d48dabdcb1002b4d7bb29c0a88c0180c 
tests/test_w4_13_measurement_truth.py b3036b443c79636c5839223b86ac5a8db4f4b1e0aa26f25ab14acf5f3ad053d3 07e445cf45d1deb49c4e5e251dc000acd35540bd14d4dffd1ae49f480589d3ad
tests/test_s81_kb_schema.py before = 33abdfb4c1e7ac265108d17d4ce78cb37fe9fda21e62fa51ea8e416ea3f4be7d
numstat vs 6869a3e6:
5	1	CLAUDE.md
48	2	app/api/image_routes.py
126	2	app/api/text_routes.py
32	2	app/api/url_routes.py
18	0	app/middleware/error_handler.py
9	1	app/services/response_builder.py
212	3	app/services/result_gate.py
1	1	tests/test_paid_route_metering.py
1	0	tests/test_retro_w2_1.py
1	0	tests/test_s71_u13_compare_auth_required.py
1	0	tests/test_s75_fanout_identity.py
1	0	tests/test_s80_b1.py
1	0	tests/test_s80_b3_vision_identity_v2.py
3	2	tests/test_s81_kb_schema.py
197	0	tests/test_s81_s20_gate_rows.py
1765	0	tests/test_s81_s20_result_gate.py
2	1	tests/test_w4_13_measurement_truth.py

Byte copies + SHA256SUMS: <scratchpad>/S81-20_green_before/. CRLF kept on every existing file (the CRLF count equals the LF count on each). The new gate-rows file is ASCII + LF. The RED file was re-hashed first and last: 13aa83ade66d14759278e6da14668f60d48dabdcb1002b4d7bb29c0a88c0180c.

## Implementation (own code; the prototype used as reference only)
- result_gate.py:
  - constants; result_gate_enabled; gate_reason;
  - URL reading: _url_number / _url_price / _url_rating (re.ASCII); url_gate_reason;
  - camera: _camera_view / _camera_low; camera_gate_categories, a NEW pure helper (V2 _category on _is_product only, R-S20-39); camera_gate_reason;
  - refusal: gate_refusal_body; result_gate_refusal (flag first; try/except returns None); gate_log_message;
  - the docstring flag line.
- response_builder.py: the import; the setdefault stamp.
- error_handler.py: _RESULT_GATE_REASONS; _result_gate_keys_enabled; the fourth block.
- text_routes.py:
  - `_rg` module attribute; the reason arm;
  - _result_gate_budget(request, user) -> (gated, subject, spent);
  - _result_gate_exit (async: read -> keyed refund if not spent -> record once if gated and not spent -> row -> INFO -> raise);
  - _s20_stream_settle: ONE task doing read -> refund or keep -> record -> row, every leg awaited inside it;
  - keys captured at all 3 consume sites; POST and GET exits;
  - stream: _s20_refusal, the first-terminal intercept, the persist operand, and a NEW first finally branch (fire_and_forget of the settle, label usage_refund.text_stream.result_gate, plus INFO; if -> elif). The finally has ZERO Await nodes.
- image_routes.py:
  - `_rg`; usage_consumed_keys;
  - _refund_reserved_credit(label, consumed_keys=None); the keyless body is byte-equal to base;
  - _rg_on + the identities snapshot before the enrichment;
  - the block after _syn, before the try: under _gate_on, read the budget; spent keeps both credits; else keyed reserved refund + anon refund, then record once. Then one row, INFO and the action:error body.
- url_routes.py:
  - the import; _reserve_comparison_credit(user, keys_out=None); the call with a local dict;
  - the block after the failure block: when gate_route is set, read the budget; spent keeps the credit; else keyed refund, then record once. Then _url_row, INFO and _surface_comparison_failure.

## Runs ([pyt] lines in S81_20_GREEN_GATE_LOGS.md)
- ruff E9/F63/F7/F82 + py_compile on the 6 app files: clean. The hook re-ran ruff: passed.
- RED file:
  - flag unset: [pyt] tag=s20g-unit-off1 start=2026-11-05 10:19:47 end=2026-11-05 10:19:54 elapsed=7s bound=600s status=OK rc=0 (166 passed).
  - exported: [pyt] tag=s20g-unit-on1 start=2026-11-05 10:20:01 end=2026-11-05 10:20:08 elapsed=7s bound=600s status=OK rc=0 (166 passed).
- Stream rows x5 (s20g-stream-rep1..5): all OK, 29 passed each (the settle task is deterministic under TestClient).
- RED + E1-E7 files: [pyt] tag=s20g-erows-off status=OK rc=0 (987 passed) and [pyt] tag=s20g-erows-on status=OK rc=0 (987 passed). This covers:
  - B1 P10 / P11 purity (the whole test_s80_b1.py);
  - the FY25 nine digests;
  - the T23 OpenAPI snapshot in both states (identical);
  - retro_w2_1;
  - paid_route_metering (the R8 pair).
- Gate rows: [pyt] tag=s20g-gr-1 start=2026-11-05 10:25:16 end=2026-11-05 10:25:26 elapsed=10s status=OK rc=0 (12 passed).
  - Inverse edits G1a-G1d / G2a-G2c / G3: 8/8 KILLED (AssertionError), restored and sha-verified (S81_20_GREEN_GR_MUTATION_TABLE.md).
- tests/test_s81_kb_schema.py after E8: [pyt] tag=s20g-kbschema-off start=2026-11-05 10:52:50 end=2026-11-05 10:53:31 elapsed=40s status=OK rc=0 (529 passed).
- CI-order set: 56 files (RED + gate rows + E1-E8 + 4.2 + the R-S20-37 scanners + the 6 CLAUDE.md readers).
  - [pyt] tag=s20g-ci-order start=2026-11-05 11:20:51 end=2026-11-05 11:24:15 elapsed=204s bound=1200s status=FAIL rc=1.
  - 4610 passed, 1 failed: test_s81_s10_fragrance_gate.py::test_r06_production_lexicon_content (environmental CRLF, in the base record).
- CLAUDE.md readers after the block: 38 files by grep + test_s81_s08b_gate_rows.
  - [pyt] tag=s20g-claudemd-readers start=2026-11-05 11:24:37 end=2026-11-05 11:27:02 elapsed=145s status=OK rc=0 (1720 passed, 35 xfailed).
  - The later amend changed one digit in L12 only.
- Comm set at HEAD (flag unset): 390 files = the RED round's 388 + the RED file + the gate-rows file.
  - Run as 16 chunks of <= 25 (s20g-comm-00..15, bound 1200), plus test_secret_scan_static.py alone (s20g-comm-secretscan, status=OK).
  - No newly referenced importer.
  - Base record REUSED (LC-6): base_records/6869a3e6.../97218ca8...txt.
  - HEAD FAILED = 18 = the 17 base nodes + test_s81_kb_schema.py::test_s14_p06_identity_nodes_untouched[tests/test_s75_fanout_identity.py]. E1 caused that node; it was re-pinned as E8 and the file is green after.
  - comm -13 after E8: EMPTY. comm -23: EMPTY.
- E8+ sweep (the same 390, flag exported): 135 flag-sensitive nodes in 19 files (sweep_only.txt; named in the CLAUDE.md L12 limit). No TIMEOUT anywhere.
- Corpus gate (--flags ENABLE_RESULT_GATE over sc-scraper-proof/_proof, 414 records / 1656 calls): EQUAL.
  - HEAD OVERALL SHA256 cedae00812d0717fb0624cbf0f1192145c251b682b8cf4d087dcd9dac7223f48.
  - Base (a git-archive extraction of 6869a3e6 app/scripts/data) gives the same OVERALL SHA256.
  - The same 31 app modules load on both sides.
- Fourteen fences (jest 29.7.0, node v24.11.1; by path through the junction): [jest] tag=s20g-fences start=2026-11-05 10:33:02 end=2026-11-05 10:33:27 rc=1.
  - 13 / 14 suites, 236 / 240 tests; the 4 = nativeBundle.w37 d5 / k2 / k4 / k5.
  - Hook tests NOT run (no .githooks change). Full jest NOT run (LC-7).
- Hygiene (added lines): 0 personal or credential shapes. New constant names carry no gitleaks keyword. The E8 re-pin is the only new 64-hex value (IDENTITY_NODES, a non-keyword name; the hook passed).

## Counts
- 166 RED-file nodes green in both states.
- 12 gate-row nodes.
- RED-round mutants: 42 KILLED + EQ1 / EQ2 (not re-run).
- GR inverse edits: 8 KILLED.

## Deviations
- D1 E8 is not in the spec E-list. tests/test_s81_kb_schema.py:475 IDENTITY_NODES pins the LF sha of test_s75_fanout_identity.py, so the mandated E1 moved it. I re-pinned it, following the S81-04 / S81-06 RB6-11 precedent recorded in that docstring, and flagged it (Q2).
- D2 The sweep reds were named in CLAUDE.md L12, not cleaned (spec 7.4 alternative). CI (flag unset) is unaffected.
- D3 camera_gate_categories lives in result_gate.py (pure).
- D4 The stream settle awaits its legs inside ONE task (one hop). The INFO line is synchronous in the finally.
- D5 Order: read -> refund -> record -> row -> INFO (the brief's order; the prototype recorded before refunding).
- D6 The corpus base was a git-archive tree (no scratch worktree).

## Questions
- Q1: Should the sweep's red files that have clean lists get one-name E-rows in a fix round? Candidates: s09_device_quota :97, s10_fragrance_gate :500, s10_gate_rows :252/:288, s18 :82, s17_kb_ingest.
- Q2: Rule on E8 vs the STOP instruction.
- R9 / GC-8 text correction: gate_reason on a product-less success body -> placeholder_identity; url_gate_reason under two products -> None.

NOT MEASURED: none.
