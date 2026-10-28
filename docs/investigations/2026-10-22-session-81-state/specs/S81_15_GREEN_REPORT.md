# S81-15 REGISTRY-ROBOTS-DENY GREEN report (agent: Opus 5.5, 2026-10-28; written through the shell: the harness refuses a subagent Write of a report .md)

- Unit: S81-15 (ENABLE_MERCHANT_REGISTRY_DB + ENABLE_ROBOTS_REGISTRY_CRON, lane B). Worktree C:/Users/SynAckITPC/Documents/AI/sc-s81-s15, branch feature/s81-s15-registry-robots-deny.
- Base 86d5a24d17f5782e733dee82d52f38dcbf3606ff (= origin/main with S81-14 #373). HEAD ce01175fc07335025932a1c3d51f25604073893f (one commit, hook passed, trailer Co-Authored-By: Claude Opus 5.5; not pushed, no rebase, no PR).
- RED files re-hashed first and last: test 5bb3bc4c1ccd21abffeece4b221d82289b9a250008c391bf91f3c0e23f52be09, fixture 314d5e0d2b8fd81929e0f2ee15399afb77b73efc5735e60b3dccb0b882e50d84 (working copy AND committed blob): OK.
- git status --short after the commit: empty.

## Gate 0
192 failed / 37 passed at 86d5a24d, 192 'E   AssertionError' lines (the one ModuleNotFoundError text is R37's subprocess stderr inside its assertion).
[pyt] tag=s15g-gate0 start=2026-10-28 21:37:57 end=2026-10-28 21:38:17 elapsed=20s bound=600s status=FAIL rc=1; [hermeticity] sentinel checked 229 test(s); [netguard] blocked 0 attempt(s) from 0 node(s)

## Files (sha256 of the bytes on disk after the commit; before = the byte copy in S81-15_green_before)
- app/services/merchant_registry.py NEW 4f5e9e25dcf442775fbbd3495b8b7482bffc80b237ea7dae4a5d1982a8484ef7 (+675)
- app/services/robots_registry.py NEW a10560ccea2d2b45bdda2b8156081610e32fabf6c34e78286b34e6bfd6e2f89c (+1026)
- app/services/source_router.py afd3dd24...-> b696d10d1322ed0cafa8888ce70508d4430f34ae1bf460f0b872f09ddf402de9 (+126 -4)
- app/services/price_service.py f3dcdf1e...-> e2997e6b6d1775489fe565be93a88cccc5a4d688bbe5e12e5f9455c09ed45d44 (+7 -3)
- app/services/cache_service.py 54257ced...-> 5f0b1efaac693db049544b7e1654c78c69b65b36ca5c64137e5089fdacbf9249 (+5 -3)
- app/services/magento_graphql_service.py 96ede220...-> bee455bad8a4a198cad8f0bfef3d4f703105c482c36ca96e693726dee8041b0d (+4 -2)
- app/services/robots_eval.py 031971a2...-> bbfbdb9285985e938bc78839d992494084b1ee1576b3181768b9620f33bdfdf5 (+8)
- app/services/sitemap_discovery_service.py ad73d799...-> 35183a5c34dcffd0ac7eabd9ad0df12233e0a23adb1578390f21ed0d78bdf169 (+6)
- scripts/seed_kb_merchants.py NEW 4c228f1b3a2d1e2a5c4b8b159ea9c8540718a5afb33bd349cb2c4296b8a1a485 (+250)
- scripts/cron_robots_registry.py NEW 2be9846297ca1681d4da1ec91721a50d8bece3454f1b2fb02f620da7ab3095f1 (+79)
- railway.robots.json NEW 5dbab6d753b8e3497e777ce5c188342c811ec0256ab54f031e3aad9304c6c94d (+15)
- tests/test_s81_s15_gate_rows.py NEW d77f554cac5882790b9fd5e3b328893ee9d248637dcef19f5e96cfde96b50b88 (+400; the GATE_S81_15 gate-named rows GC-1..GC-8, GC-10)
- tests/test_legal_disclosure_s77.py c4bc8c47...-> ebc8743e6a00bba171f44857c27f794878f776ec8190e20956a0a17a5536c959 (E1, +1)
- tests/test_legal_s78.py 0f5868f9...-> 1f80abe949bce28f767a82caeb9ce45252123e89ab32135874c3eb2f960cc446 (E2, +1 -1)
- CLAUDE.md 1b2375cb...-> c1934e2fac3e0575d6d8fe7022cf4e32646b5e27abcb7dfe224f8c76dfce02bc (+6 -1: the S81-15 block after the S81-14 block, the Feature Flags sentence; CRLF kept, non-ASCII count 3937 unchanged)
- tests/test_s81_s15_registry_robots.py + tests/fixtures/s81_s15_robots_record.json (the frozen RED files, committed unchanged)
New files: LF, 0 bytes > 127. Edited CRLF files: 0 bare LF, non-ASCII counts unchanged, no whole-file diff.

## Unit and pin runs ([pyt] lines; each run: [netguard] blocked 0 unless stated)
- RED file, flags unset: 2 failed / 227 passed. [pyt] tag=s15g-unit1 start=2026-10-28 22:11:33 end=2026-10-28 22:11:48 elapsed=15s bound=600s status=FAIL rc=1; [hermeticity] 229. Failures: test_r9_entry_round_trip (AssertionError ['search']), test_r22_seed_rows_counts_and_contract (TypeError: _registry_ok() missing 'host').
- Gate rows: 9 passed. [pyt] tag=s15g-gaterows1 start=2026-10-28 22:13:39 end=2026-10-28 22:13:44 elapsed=5s bound=600s status=OK rc=0; [hermeticity] 9.
- Both unit files, ENABLE_MERCHANT_REGISTRY_DB=true ENABLE_ROBOTS_REGISTRY_CRON=true exported: 2 failed (R9, R22) / 236 passed. [pyt] tag=s15g-unit-on start=2026-10-28 22:13:52 end=2026-10-28 22:14:10 elapsed=17s bound=600s status=FAIL rc=1; [hermeticity] 238.
- Both unit files, flags unset: 2 failed (R9, R22) / 236 passed. [pyt] tag=s15g-unit-off start=2026-10-28 22:14:18 end=2026-10-28 22:14:33 elapsed=15s bound=600s status=FAIL rc=1; [hermeticity] 238.
- PIN rows (-k test_p) with ENABLE_MERCHANT_REGISTRY_DB=false ENABLE_ROBOTS_REGISTRY_CRON=off exported: 37 passed. [pyt] tag=s15g-pins-falsy start=2026-10-28 22:14:33 end=2026-10-28 22:14:39 elapsed=6s bound=600s status=OK rc=0; [hermeticity] 37.
- RED-A/B on an amended COPY (3 strings), -k r9|r22: 2 passed. [pyt] tag=s15g-r9r22-amended start=2026-10-28 22:14:54 end=2026-10-28 22:14:58 elapsed=4s bound=600s status=OK rc=0 (copy deleted from tests/; kept as r9_r22_amended_copy.py in the notes).
- Identity pins A (18 registry files + E1/E2 files + test_domain_s76, 21 files): 932 passed, 3 skipped. [pyt] tag=s15g-pinsA start=2026-10-28 22:15:26 end=2026-10-28 22:15:41 elapsed=15s bound=1200s status=OK rc=0; [hermeticity] 932.
- Identity pins B (8 spec pins + test_s81_kb_schema): 2 failed (test_s14_p01, test_s14_p02). [pyt] tag=s15g-pinsB start=2026-10-28 22:15:47 end=2026-10-28 22:16:44 elapsed=57s bound=1200s status=FAIL rc=1; netguard blocked 22 from 21 nodes (test_hermeticity_pins' designed rows).
- E3/E4 on an amended COPY of test_s81_kb_schema.py, -k p01|p02: 2 passed. [pyt] tag=s15g-kbp01p02-amended start=2026-10-28 22:18:17 end=2026-10-28 22:18:22 elapsed=5s bound=600s status=OK rc=0 (copy deleted; kept as kb_p01_p02_amended_copy.py).
- After the W0-4c fix (extract_price_from_html via asyncio.to_thread): test_retro_w0_4 + both unit files 393 passed / 2 failed (R9, R22). [pyt] tag=s15g-w04-unit3 start=2026-10-28 22:33:13 end=2026-10-28 22:34:24 elapsed=71s bound=600s status=FAIL rc=1.
- CI-order set (31 files, alphabetical: the 26 spec files + E1/E2 files + test_domain_s76 + both unit files): 1472 passed, 3 skipped, 2 failed (R9, R22). [pyt] tag=s15g-ci-order start=2026-10-28 22:53:05 end=2026-10-28 22:54:51 elapsed=106s bound=1200s status=FAIL rc=1; [hermeticity] 1474; [netguard] blocked 22 from 21 nodes (designed).
- Final at HEAD (both unit files + E1/E2 files + test_domain_s76 + test_retro_w0_4): 460 passed / 2 failed (R9, R22). [pyt] tag=s15g-final-head start=2026-10-28 22:57:31 end=2026-10-28 22:58:51 elapsed=80s bound=600s status=FAIL rc=1; [hermeticity] 462.
- Lint: py_compile OK on all 12 changed python files; ruff --select E9,F63,F7,F82 --no-cache: All checks passed; full repo ruff config on the 4 new python files: All checks passed (after 4 C420 fixes).

## Comm set (GC-12)
340 files = the RED's 308 (comm_files.txt) UNION 32 re-derived at HEAD (derive_comm.py: module refs to the 6 edited + 2 new modules, symbol refs, app/scripts source readers, tree walkers, railway readers, named pins + CLAUDE.md readers + the E1/E2 files, importers of the edited tests, the two unit files; minus test_precommit_hook*). Lists: comm_files_head.txt, comm_reasons_head.tsv, comm_chunks_head.json (14 chunks <= 25). HEAD = worktree; BASE = a FRESH record in a detached scratch worktree at 86d5a24d under the notes folder (no junction; removed with git worktree remove --force; gone from git worktree list and from disk). New files absent at base are skipped there; the RED file's base record is gate 0.
Per-chunk [pyt] lines (HEAD chunks 08-10 re-run after the last code change, side 'headr'):
- chunk 00 files=25 failed=0 | [pyt] tag=s15g-head-00 start=2026-10-28 22:22:21 end=2026-10-28 22:22:58 elapsed=37s bound=1200s status=OK rc=0
- chunk 01 files=25 failed=0 | [pyt] tag=s15g-head-01 start=2026-10-28 22:22:58 end=2026-10-28 22:23:42 elapsed=44s bound=1200s status=OK rc=0
- chunk 02 files=25 failed=0 | [pyt] tag=s15g-head-02 start=2026-10-28 22:23:43 end=2026-10-28 22:23:59 elapsed=16s bound=1200s status=OK rc=0
- chunk 03 files=25 failed=0 | [pyt] tag=s15g-head-03 start=2026-10-28 22:24:04 end=2026-10-28 22:24:34 elapsed=31s bound=1200s status=OK rc=0
- chunk 04 files=25 failed=0 | [pyt] tag=s15g-head-04 start=2026-10-28 22:24:34 end=2026-10-28 22:25:53 elapsed=79s bound=1200s status=OK rc=0
- chunk 05 files=25 failed=0 | [pyt] tag=s15g-head-05 start=2026-10-28 22:25:53 end=2026-10-28 22:26:17 elapsed=24s bound=1200s status=OK rc=0
- chunk 06 files=25 failed=0 | [pyt] tag=s15g-head-06 start=2026-10-28 22:26:22 end=2026-10-28 22:26:46 elapsed=24s bound=1200s status=OK rc=0
- chunk 07 files=25 failed=0 | [pyt] tag=s15g-head-07 start=2026-10-28 22:26:46 end=2026-10-28 22:27:03 elapsed=17s bound=1200s status=OK rc=0
- chunk 08 files=25 failed=4 | [pyt] tag=s15g-head-08 start=2026-10-28 22:27:03 end=2026-10-28 22:28:38 elapsed=94s bound=1200s status=FAIL rc=1
- chunk 09 files=25 failed=2 | [pyt] tag=s15g-head-09 start=2026-10-28 22:28:43 end=2026-10-28 22:31:07 elapsed=144s bound=1200s status=FAIL rc=1
- chunk 10 files=25 failed=3 | [pyt] tag=s15g-head-10 start=2026-10-28 22:31:07 end=2026-10-28 22:32:11 elapsed=64s bound=1200s status=FAIL rc=1
- chunk 11 files=25 failed=0 | [pyt] tag=s15g-head-11 start=2026-10-28 22:32:11 end=2026-10-28 22:32:28 elapsed=17s bound=1200s status=OK rc=0
- chunk 12 files=25 failed=0 | [pyt] tag=s15g-head-12 start=2026-10-28 22:34:33 end=2026-10-28 22:35:16 elapsed=43s bound=1200s status=OK rc=0
- chunk 13 files=15 failed=0 | [pyt] tag=s15g-head-13 start=2026-10-28 22:35:17 end=2026-10-28 22:35:40 elapsed=23s bound=1200s status=OK rc=0
- chunk 08 files=25 failed=2 | [pyt] tag=s15g-headr-08 start=2026-10-28 22:35:47 end=2026-10-28 22:37:24 elapsed=96s bound=1200s status=FAIL rc=1
- chunk 09 files=25 failed=2 | [pyt] tag=s15g-headr-09 start=2026-10-28 22:37:24 end=2026-10-28 22:39:48 elapsed=144s bound=1200s status=FAIL rc=1
- chunk 10 files=25 failed=3 | [pyt] tag=s15g-headr-10 start=2026-10-28 22:39:48 end=2026-10-28 22:40:56 elapsed=68s bound=1200s status=FAIL rc=1
- chunk 00 files=25 failed=0 | [pyt] tag=s15g-base-00 start=2026-10-28 22:41:05 end=2026-10-28 22:41:38 elapsed=33s bound=1200s status=OK rc=0
- chunk 01 files=25 failed=0 | [pyt] tag=s15g-base-01 start=2026-10-28 22:41:39 end=2026-10-28 22:42:31 elapsed=52s bound=1200s status=OK rc=0
- chunk 02 files=25 failed=0 | [pyt] tag=s15g-base-02 start=2026-10-28 22:42:31 end=2026-10-28 22:42:48 elapsed=17s bound=1200s status=OK rc=0
- chunk 03 files=25 failed=0 | [pyt] tag=s15g-base-03 start=2026-10-28 22:42:48 end=2026-10-28 22:43:20 elapsed=31s bound=1200s status=OK rc=0
- chunk 04 files=25 failed=0 | [pyt] tag=s15g-base-04 start=2026-10-28 22:43:26 end=2026-10-28 22:44:35 elapsed=69s bound=1200s status=OK rc=0
- chunk 05 files=25 failed=0 | [pyt] tag=s15g-base-05 start=2026-10-28 22:44:35 end=2026-10-28 22:44:57 elapsed=21s bound=1200s status=OK rc=0
- chunk 06 files=25 failed=0 | [pyt] tag=s15g-base-06 start=2026-10-28 22:44:57 end=2026-10-28 22:45:27 elapsed=30s bound=1200s status=OK rc=0
- chunk 07 files=25 failed=0 | [pyt] tag=s15g-base-07 start=2026-10-28 22:45:28 end=2026-10-28 22:45:51 elapsed=23s bound=1200s status=OK rc=0
- chunk 08 files=25 failed=2 | [pyt] tag=s15g-base-08 start=2026-10-28 22:45:57 end=2026-10-28 22:47:31 elapsed=94s bound=1200s status=FAIL rc=1
- chunk 09 files=25 failed=0 | [pyt] tag=s15g-base-09 start=2026-10-28 22:47:31 end=2026-10-28 22:49:57 elapsed=145s bound=1200s status=OK rc=0
- chunk 10 files=23 failed=1 | [pyt] tag=s15g-base-10 start=2026-10-28 22:49:57 end=2026-10-28 22:51:06 elapsed=69s bound=1200s status=FAIL rc=1
- chunk 11 files=25 failed=0 | [pyt] tag=s15g-base-11 start=2026-10-28 22:51:13 end=2026-10-28 22:51:31 elapsed=18s bound=1200s status=OK rc=0
- chunk 12 files=25 failed=0 | [pyt] tag=s15g-base-12 start=2026-10-28 22:51:31 end=2026-10-28 22:52:15 elapsed=44s bound=1200s status=OK rc=0
- chunk 13 files=15 failed=0 | [pyt] tag=s15g-base-13 start=2026-10-28 22:52:15 end=2026-10-28 22:52:40 elapsed=24s bound=1200s status=OK rc=0
- chunk 00 files=25 failed=0 | [pyt] tag=s15g-routeron-00 start=2026-10-28 22:55:04 end=2026-10-28 22:55:33 elapsed=28s bound=1200s status=OK rc=0
- chunk 01 files=23 failed=2 | [pyt] tag=s15g-routeron-01 start=2026-10-28 22:55:33 end=2026-10-28 22:56:06 elapsed=34s bound=1200s status=FAIL rc=1
Netguard / hermeticity per chunk: in the *_pyt_lines.txt files beside this report (every hermeticity line clean; netguard counts are pre-existing designed blocks).
HEAD failures (7): test_prompt_truth.py::test_render_digests_match_base_except_the_fence (ERROR), ::test_truth_on_prefix_static_and_cacheable (ERROR) [cold tiktoken, identical both sides]; test_sentry_channels_u8d.py::TestU8dPins::test_u8d_pin_integration_list_unchanged [identical both sides: sentry auto-enables AnthropicIntegration on the shared venv; environmental]; test_s81_kb_schema.py::test_s14_p01_no_importer_of_kb_service and ::test_s14_p02_no_kb_relation_literal_outside_the_leaf [branch-only-new: E3/E4]; test_s81_s15_registry_robots.py::test_r9_entry_round_trip and ::test_r22_seed_rows_counts_and_contract [red at base too: RED-A/B].
BASE failures: the 3 environmental nodes above + the 192 RED nodes (gate 0) = 195 ids (comm_base_failed_all_86d5a24d.txt).
**branch-only-new = 2 (comm_branch_only_new.txt): tests/test_s81_kb_schema.py::test_s14_p01_no_importer_of_kb_service, ::test_s14_p02_no_kb_relation_literal_outside_the_leaf.** Not a regression: the S81-14 'ships inert' pins, named in PR #373's body as 'the deliberate-change points for S81-15 (KB_MERCHANTS_TABLE), S81-17 and S81-18'; any GC-2-conforming implementation reddens them (an importer of kb_service and the table literal are required). Footprint minimised to ONE file (merchant_registry.py: one lazy import + one literal); E3/E4 measured green on a copy; NOT applied (the brief allows E1/E2 only).
Gate 6 (spec 7.6): the 48 files referencing source_router, ENABLE_MERCHANT_REGISTRY_DB=true exported, 2 chunks: no node turned red under the flag (only the flag-independent p01/p02).

## Gate conditions
- GC-1: CRON_REASONS = robots_unreadable, robots_disallow, challenge, ssrf_redirect (gc1 row).
- GC-2: build_seed_rows calls the REAL kb_service.build_merchant_row once per row (410; gc2 recorder) and adds created_at = updated_at; plan_seed updates never carry created_at.
- GC-3: entries carry order, origin and every Source field except deny (a row column) under their FIELD names (search_descriptor, not the spec's 'search': the post-F1-3 validator refuses a non-field key); all 319 Sources pass the real _registry_ok([e], host) and round-trip (gc3). R9 / R22 (frozen) still call the 1-arg form and want 'search': RED-A/B.
- GC-4: .order('host') on every page of the paged read (gc4, 3 pages of 1,200 rows).
- GC-5: a residential / operator record younger than 30 days keeps its verdict and status on ANY datacenter result (allow included); the result lands in health.last_datacenter_result; older than 30 days the datacenter result applies (gc5, r31b).
- GC-6: initial refusal = robots_unreadable + health.ssrf 'initial', no fetch; refused hop = ssrf_redirect + health.ssrf 'hop' (gc6). R35 (frozen) still accepts either: tightened by the new gc6 row, not by an edit.
- GC-7: cross-site sample -> https://<host>/robots.txt is the primary record, sample origin in robots.other_origins, probed '/' only; same-site (www) sample -> its origin (gc7, r34c).
- GC-8: --classify (default 20) = LIVE rows with platform NULL whose entries carry no mechanism, literal rows included, sorted by host, dry run unless --apply (gc8, r26).
- GC-9: score_source / source_usage / is_render_only_domain on SELECTION (_routable_registry); match_registry_apex / registry_tier / descriptor_for_host on LOOKUP via _registry_row_for_host (r11b, r21b, p1).
- GC-10: the PDP gate passes the page <title> (entity-decoded, whitespace-collapsed) through prompt_sanitizer.sanitize_prompt_input to extract_price_from_html (gc10 recorder); the extractor runs via asyncio.to_thread (W0-4c rule).
- GC-11: the accepted deviations are kept (Source.status reused + appended Source.deny, consumer split, candidates never blocked, NULL platform for blank / unmapped mechanisms, R17 classes, sha snapshot, decide_robots(status, headers, body, probe_urls), run_cron(client, fetch, sleep, now_clock, validate), politeness order, seed passes genuine_method or None, kb_service imported lazily).
- GC-12: comm set above; CLAUDE.md block after the S81-14 block; the Feature Flags list gains both flags and the five knobs.
- GC-13: this report + PR_BODY.md, written through the shell.

## Deviations
1. RED-A/B (wrong rows, not edited): R9 and R22 fail against the real post-F1-3 kb_service (2-arg _registry_ok; Source-field keys). Proposed amendment measured green on a copy.
2. E3/E4 required but not applied (brief: E1/E2 only): test_s14_p01 / test_s14_p02 are branch-only-new.
3. tests/test_domain_s76.py::test_t4 (unlisted reader of sitemap_discovery_service source) kept green by keeping the UA literal as a mirror line and rebinding _ROBOTS_UA = robots_eval.QARENBOT_UA on the next line (R39 identity holds; the value sent is the leaf's). Clean alternative: E5 + delete the mirror line.
4. W0-4c guard (tests/test_retro_w0_4.py) caught an inline extract_price_from_html in the async PDP gate: fixed (asyncio.to_thread), green.
5. Gate-named rows live in a NEW file tests/test_s81_s15_gate_rows.py (the RED file is frozen); GC-6's 'tighten the row that accepted either' is a new gc6 row, R35 unchanged.
6. The table name is defined once (merchant_registry.KB_MERCHANTS_TABLE) and imported by robots_registry and the seed (shrinks E4 to one literal).
7. Commit trailer names the committing model, Claude Opus 5.5 (the computed brief said Fable 5.1; this agent runs on Opus 5.5 and never claims another model).
8. robots.rules_truncated is an additive key present only when a list was capped; robots.other_origins only when non-empty (the fixture record has neither).
9. Residential seed records carry the 2026-08-31 date (honest), so the R-S15-4 protection has lapsed for them on the first run: owner step 3 (a fresh residential read) precedes the first cron run.

## Questions for the orchestrator
1. Rule E3/E4 (test_s81_kb_schema p01/p02 exempt merchant_registry.py: its one lazy kb_service import and its one 'kb_merchants' literal); exact edits in kb_p01_p02_amended_copy.py.
2. Rule RED-A/B (R9: want_keys 'search' -> 'search_descriptor', kb._registry_ok([e2], s.domain); R22: kb._registry_ok(r['registry'], r['host'])); exact edits in r9_r22_amended_copy.py.
3. test_domain_s76 t4: keep the mirror line (as shipped) or rule E5 (read robots_eval QARENBOT_UA) and delete it?
4. R38 byte check vs Windows checkouts with core.autocrlf=true: the four new .py files arrive CRLF on a fresh Windows checkout and R38 then fails locally (CI Linux is LF). Add a .gitattributes eol=lf entry for them in a later unit, or accept?
5. test_sentry_channels_u8d::test_u8d_pin_integration_list_unchanged fails at base AND head on .venv-qaren (AnthropicIntegration auto-enabled: the anthropic package is now importable there): environmental, outside this unit.

## NOT MEASURED
- Real curl_cffi fetch / redirect / DNS behaviour (every fetch, sleep, clock and SSRF check is a seam; netguard on; 0 blocked attempts from the unit files).
- extract_price_from_html, detect_platform_verdict and detect_platform on a real PDP (recorders in R32 / gc10).
- A GREEN-side mutation table (the RED's 65 mutants stand; the gate rows are direct assertions, not mutation-measured here).
- Live Supabase / PostgREST behaviour of .order().range() paging and the conditional update return shape (fakes only; supabase 2.31.0 returns the updated rows by default).
- Protego parity (R-S15-19, by design).

## git status --short (worktree, after the commit)
(empty)
