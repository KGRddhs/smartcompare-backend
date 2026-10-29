# S81-15 RB15-12 re-rebase report (REBASE-AND-GATES agent, Opus 5.5)

- unit: S81-15 REGISTRY-ROBOTS-DENY (ENABLE_MERCHANT_REGISTRY_DB + ENABLE_ROBOTS_REGISTRY_CRON, default OFF)
- verdict: READY_FOR_PR
- worktree: C:/Users/SynAckITPC/Documents/AI/sc-s81-s15 branch feature/s81-s15-registry-robots-deny
- head_before: 40f7e8fc213258401d56b95c7ecda13a92e575ed (three commits on a8f01379)
- base (origin/main, fetched 2026-10-29 04:42 AST): 2922972010b350d3afdca9ee7e30bc08624db4bd (#375 S81-08b LEGACY-FINGERPRINT-READER)
- head_after: 584e7198fda65c578be0b5f8a41a107226ea85f8
- replayed chain (sha, parent, subject):
  - 73b18e0be1c6fb393680333756286e1fa57576ce 2922972010b350d3afdca9ee7e30bc08624db4bd feat(registry): S81-15 REGISTRY-ROBOTS-DENY - kb_merchants registry memo + daily robots cron (dark)
  - 98b3fdce1c3025fa08a9fb839ba699936170d499 73b18e0be1c6fb393680333756286e1fa57576ce fix(registry): S81-15 fix round 1 (RULINGS_FIX1_S81_15 F1-1..F1-23)
  - 584e7198fda65c578be0b5f8a41a107226ea85f8 98b3fdce1c3025fa08a9fb839ba699936170d499 test(registry): S81-15 rebase-round pins RB15-2 / RB15-3 / RB15-4 and the RB15-2 hunk
- old -> new: 34fbe392 -> 73b18e0b (GREEN), 9d574c47 -> 98b3fdce (fix 1), 40f7e8fc -> 584e7198 (the pin commit)
- precedence applied: RB15-12a..d > RB15-1..11 > RULINGS_FIX1_S81_15 > GATE_S81_15 > RULINGS_S81_15

## Conflicts and resolutions

- measured before the rebase: main delta a8f01379..29229720 = CLAUDE.md, app/api/auth_routes.py, tests/test_s81_s08b_gate_rows.py, tests/test_s81_s08b_legacy_fingerprint.py; merge-tree 29229720 40f7e8fc = CONFLICT CLAUDE.md only (tree 577488859454d39d75453f52ed136a731d988b90).
- resolver: conf/resolve2.py (UNION in MERGE order computed from the blobs a8f01379 / 29229720 / the replayed commit, verified against the conflicted working copy: every context line outside the markers equal, every theirs line kept, every ours line kept unless the replayed commit itself replaced it; main -> resolved = the FF line + 5 inserted lines; branch commit -> resolved = exactly main's own a8f01379 -> 29229720 CLAUDE.md changes; non-ASCII = main's 3937; CRLF written).
- commit 1 (34fbe392): CONFLICT CLAUDE.md, 2 blocks:
    FF: anchor a8f0 word 174; main ins 16 words (S81-08b first word 'block.'); branch ins 27 words; union 6035 chars
    rows: S81-08b block main L510-L515 (6 lines); S81-15 block 4 lines inserted at expected L517-L520; ## Tests at L522
    main->expected: replace FF + insert 5 lines; branch->expected == a8f0->main (2 non-FF changes + FF)
    expected: 984 lines, LF bytes 558726, sha256(LF)=dd0aba2c4371f77ec5866eb476bfb284df41cf6dcf09567fbbf53bd91277faa3, non-ASCII 3937 (main 3937)
    block 1 at wc: ours 1 lines, theirs 1 lines -> resolution 1 lines (expected L341-L341); ours lines superseded by the commit: 1; FF union
    block 2 at wc: ours 6 lines, theirs 4 lines -> resolution 11 lines (expected L510-L520); ours lines superseded by the commit: 0
    conflicted wc: 2 blocks, context consistent
    WROTE 559709 bytes CRLF=983 LF=983 sha256(wc)=186ed9a50e29be68a73488eb86ea64e6578f27431a5a7f96d1d7c3d0f31ba93c
- commit 2 (9d574c47): CONFLICT CLAUDE.md, 2 blocks:
    FF: anchor a8f0 word 174; main ins 16 words (S81-08b first word 'block.'); branch ins 28 words; union 6063 chars
    rows: S81-08b block main L510-L515 (6 lines); S81-15 block 4 lines inserted at expected L517-L520; ## Tests at L522
    main->expected: replace FF + insert 5 lines; branch->expected == a8f0->main (2 non-FF changes + FF)
    expected: 984 lines, LF bytes 561528, sha256(LF)=987bc6a56a023ddbf03acae78af1f24d581c267713a452d837c96684b1e0b872, non-ASCII 3937 (main 3937)
    block 1 at wc: ours 1 lines, theirs 1 lines -> resolution 1 lines (expected L341-L341); ours lines superseded by the commit: 1; FF union
    block 2 at wc: ours 11 lines, theirs 4 lines -> resolution 11 lines (expected L510-L520); ours lines superseded by the commit: 4
    conflicted wc: 2 blocks, context consistent
    WROTE 562511 bytes CRLF=983 LF=983 sha256(wc)=135241f4c2d8cff9b310a0351ec8eb5af04c56b1d740a3520fed06398196750a
- commit 3 (40f7e8fc): applied CLEAN, no conflict (its CLAUDE.md change touches only the S81-15 block lines two lines away from the S81-08b insertion, and not the FF line).
- staged / committed CLAUDE.md blobs = the independently computed unions: 73b18e0b dd0aba2c4371f77e..., 98b3fdce 987bc6a56a023ddb..., 584e7198 cb5f1117f275e90f5e92acc713ad1da579f07d631b62624d4fe84e42c61c3410
- resolution text: FF pointer line = main 29229720's line (S81-06 sentence, then S81-08b's ENABLE_LEGACY_FINGERPRINT_READER mention) + this unit's sentence (the two flag names, the knobs incl. ROBOTS_DUE_SLACK_SECONDS) inserted after S81-08b's mention (a8f01379 word anchor 174; main ins 16 words; branch ins 27 words at commit 1, 28 at commits 2/3); rows = S81-06 row (2 lines), blank, S81-08b row (6 lines), blank, S81-15 row (4 lines), blank, ## Tests.
- after every continue: git diff --cached --check and git diff --check clean; at the end git diff --check origin/main HEAD clean; grep for <<<<<<< / >>>>>>> over CLAUDE.md, app/, tests/, scripts/, railway.robots.json: no hit (rc=1).

## Footprint and bytes

- git diff 40f7e8fc HEAD -- <the 18 footprint files other than CLAUDE.md>: EMPTY (0 bytes)
- the 18-file diff vs the base is byte-identical to the previous round's (sha256 of `git diff a8f01379 40f7e8fc -- <18>` = sha256 of `git diff 29229720 HEAD -- <18>` = 50a75d39a1aee7ae...); the 18 files are blob-identical at a8f01379 and 29229720.
- footprint origin/main...HEAD: 19 files (the 19 expected)
```
 CLAUDE.md                                 |    7 +-
 app/services/cache_service.py             |    8 +-
 app/services/magento_graphql_service.py   |    6 +-
 app/services/merchant_registry.py         |  687 +++++++++
 app/services/price_service.py             |   10 +-
 app/services/robots_eval.py               |   13 +
 app/services/robots_registry.py           | 1177 +++++++++++++++
 app/services/sitemap_discovery_service.py |    7 +-
 app/services/source_router.py             |  130 +-
 railway.robots.json                       |   17 +
 scripts/cron_robots_registry.py           |   91 ++
 scripts/seed_kb_merchants.py              |  256 ++++
 tests/fixtures/s81_s15_robots_record.json |   55 +
 tests/test_domain_s76.py                  |   10 +-
 tests/test_legal_disclosure_s77.py        |    1 +
 tests/test_legal_s78.py                   |    2 +-
 tests/test_s81_kb_schema.py               |   42 +-
 tests/test_s81_s15_gate_rows.py           |  905 ++++++++++++
 tests/test_s81_s15_registry_robots.py     | 2210 +++++++++++++++++++++++++++++
 19 files changed, 5610 insertions(+), 24 deletions(-)
```
- blobs at HEAD: RED tests/test_s81_s15_registry_robots.py 66ac62995ab5738510216f228112d8437ed51d1c0901acd49d993cb7ad11b9e1
  fixture tests/fixtures/s81_s15_robots_record.json 314d5e0d2b8fd81929e0f2ee15399afb77b73efc5735e60b3dccb0b882e50d84
  rows tests/test_s81_s15_gate_rows.py 5a17148e2f6c3060b6634762f3d990f5711191cb8bb8d5bd6b0d002e8b29d53c
  CLAUDE.md cb5f1117f275e90f5e92acc713ad1da579f07d631b62624d4fe84e42c61c3410; railway.robots.json e882e469390b384d1906e5464a7fc562baee268c89fc617973fdf4d7a48b185a
- working copy CLAUDE.md: 563014 bytes, CRLF 983 / LF 983, non-ASCII 3937 (main 3937), sha256 bcfea87b5e622fd7d172c663ef95da0251b9fa51f5bd06b96b09ef78781b930a
- added-line sweep (origin/main...HEAD): hits (class counts per file; text never printed): NONE
- railway.robots.json: json.loads / json.load OK (keys $schema, build, deploy; 463 bytes, 0 non-ASCII)

## Pin rows and mutants

- pin_rows_added: NONE (RB15-12a: no new row, no pin commit; the rows file blob is unchanged)
- mutants: none in this round: the 25/25 table of the previous round stands on byte-identical unit files

## Gates at 584e7198 (RB15-12b; pyt.py, .venv-qaren, one pytest at a time, foreground; flags unset unless stated; every ENABLE_* / unit knob name stripped from the child env first: none was present)

- r41 exports=- args=tests/test_s81_s15_registry_robots.py tests/test_s81_s15_gate_rows.py -k r41
  [pyt] tag=s15rb2-r41 start=2026-10-29 04:53:12 end=2026-10-29 04:53:29 elapsed=17s bound=600s status=OK rc=0
  1 passed, 265 deselected, 11 warnings in 13.81s
  [hermeticity] sentinel checked 1 test(s)
  [netguard] blocked 0 attempt(s) from 0 node(s)
  failed: none
- unit-off exports=- args=tests/test_s81_s15_registry_robots.py tests/test_s81_s15_gate_rows.py
  [pyt] tag=s15rb2-unit-off start=2026-10-29 04:53:41 end=2026-10-29 04:54:04 elapsed=23s bound=600s status=OK rc=0
  266 passed, 11 warnings in 19.27s
  [hermeticity] sentinel checked 266 test(s)
  [netguard] blocked 0 attempt(s) from 0 node(s)
  failed: none
- unit-on exports={'ENABLE_MERCHANT_REGISTRY_DB': 'true', 'ENABLE_ROBOTS_REGISTRY_CRON': 'true'} args=tests/test_s81_s15_registry_robots.py tests/test_s81_s15_gate_rows.py
  [pyt] tag=s15rb2-unit-on start=2026-10-29 04:54:10 end=2026-10-29 04:54:26 elapsed=15s bound=600s status=OK rc=0
  266 passed, 11 warnings in 14.36s
  [hermeticity] sentinel checked 266 test(s)
  [netguard] blocked 0 attempt(s) from 0 node(s)
  failed: none
- s08b-rows exports=- args=tests/test_s81_s08b_gate_rows.py
  [pyt] tag=s15rb2-s08b-rows start=2026-10-29 04:54:32 end=2026-10-29 04:54:39 elapsed=7s bound=600s status=OK rc=0
  29 passed, 11 warnings in 6.03s
  [hermeticity] sentinel checked 29 test(s)
  [netguard] blocked 0 attempt(s) from 0 node(s)
  failed: none
- s08b-fp exports=- args=tests/test_s81_s08b_legacy_fingerprint.py
  [pyt] tag=s15rb2-s08b-fp start=2026-10-29 04:54:46 end=2026-10-29 04:54:51 elapsed=5s bound=600s status=OK rc=0
  85 passed, 11 warnings in 3.46s
  [hermeticity] sentinel checked 85 test(s)
  [netguard] blocked 0 attempt(s) from 0 node(s)
  failed: none
- readers exports=- args=tests/test_ci_gates.py tests/test_behavior_dimension_translation.py tests/test_s81_s04_spend_breaker.py
  [pyt] tag=s15rb2-readers start=2026-10-29 04:54:58 end=2026-10-29 04:55:14 elapsed=16s bound=600s status=OK rc=0
  363 passed, 13 warnings in 14.88s
  [hermeticity] sentinel checked 363 test(s)
  [netguard] blocked 24 attempt(s) from 2 node(s)
  failed: none
- kb-schema exports=- args=tests/test_s81_kb_schema.py
  [pyt] tag=s15rb2-kb-schema start=2026-10-29 04:55:21 end=2026-10-29 04:55:30 elapsed=9s bound=600s status=OK rc=0
  529 passed, 11 warnings in 7.15s
  [hermeticity] sentinel checked 529 test(s)
  [netguard] blocked 0 attempt(s) from 0 node(s)
  failed: none
- sr8 exports=- args=tests/test_sentry_channels_u8d_unit.py tests/test_sentry_channels_u8d.py
  [pyt] tag=s15rb2-sr8 start=2026-10-29 04:55:37 end=2026-10-29 04:56:01 elapsed=23s bound=600s status=OK rc=0
  273 passed, 1 warning in 21.02s
  [hermeticity] sentinel checked 273 test(s)
  [netguard] blocked 0 attempt(s) from 0 node(s)
  failed: none
- ci-order exports=- args=34 files
  [pyt] tag=s15rb2-ci-order start=2026-10-29 04:56:10 end=2026-10-29 04:58:52 elapsed=162s bound=1200s status=OK rc=0
  2309 passed, 3 skipped, 1 deselected, 16 warnings in 160.69s (0:02:40)
  [hermeticity] sentinel checked 2309 test(s)
  [netguard] blocked 22 attempt(s) from 21 node(s)
  failed: none
- claude-extra-0 exports=- args=25 files
  [pyt] tag=s15rb2-claude-extra-0 start=2026-10-29 05:02:56 end=2026-10-29 05:03:25 elapsed=28s bound=1200s status=OK rc=0
  670 passed, 9 deselected, 13 warnings in 26.75s
  [hermeticity] sentinel checked 670 test(s)
  [netguard] blocked 17 attempt(s) from 7 node(s)
  failed: none
- claude-extra-1 exports=- args=5 files
  [pyt] tag=s15rb2-claude-extra-1 start=2026-10-29 05:03:37 end=2026-10-29 05:04:17 elapsed=40s bound=1200s status=OK rc=0
  262 passed, 9 skipped, 2 deselected, 35 xfailed, 13 warnings in 36.49s
  [hermeticity] sentinel checked 306 test(s)
  [netguard] blocked 62 attempt(s) from 20 node(s)
  failed: none
- json.load railway.robots.json: OK
- EXTRA chunk files (claude_md_extra.txt): tests/test_auth_routes_invite_fingerprint.py, tests/test_bh_gcc_cascade_wiring.py, tests/test_cellular_generation_cache_key.py, tests/test_channel_freshness.py, tests/test_cohort_personalization_load.py, tests/test_diagnostics_flag_gated.py, tests/test_eval_cache_read_mode.py, tests/test_eval_kpi_baseline.py, tests/test_extraction_pros_cons_diagnostic.py, tests/test_fact_checking.py, tests/test_fan_out_genuine_authority.py, tests/test_feedback_allowlist_superset.py, tests/test_fire_and_forget_wrap.py, tests/test_genuine_beats_converted_selection.py, tests/test_health_loop_lag.py, tests/test_jsonld_shape_ladder.py, tests/test_m18_offload_sweep_residual.py, tests/test_multiplicity_discriminator_policy.py, tests/test_not_a_pdp_filter.py, tests/test_paid_route_metering.py, tests/test_retro_w1_2d.py, tests/test_retro_w2_1.py, tests/test_scraping_mode.py, tests/test_shutdown_drain.py, tests/test_sse_settle_window.py, tests/test_two_input_shape.py, tests/test_value_math.py, tests/test_visible_text_currency_rung.py, tests/test_wall_signature_anchoring.py, tests/test_youtube_cited_evidence.py
- not run, per RB15-12b: ruff / py_compile (no .py change: the 18-file diff above is EMPTY); the hook files tests/test_precommit_hook*.py (RB15-12b(8) 'the hook files not re-run'; RB15-7(9) 'the four tests/test_precommit_hook*.py files are NOT re-run (the unit touches no .githooks input and no file those tests read; CI is the arbiter; stated in the PR body)'; this unit touches no .githooks file); the comm set (RB15-12b: the RB15-8 record stands: 360 files at a8f01379 both sides, branch-only-new EMPTY; main moved only by S81-08b's four files, none imported by any S81-15 footprint module, measured by grep); each conflicted test file alone (no test file conflicted); tests/test_paid_route_metering.py with the flags exported (skippable per the task; flags unset it ran inside claude-extra-0).

## NOT MEASURED

- the comm set at 29229720 (ruled not re-run, RB15-12b); the mutation table, pin sets A / B, the R38 LF swap, the falsy-PIN and seven-flag unit runs (not in RB15-12b; byte-identical code and test files)
- whether git's rebase ran the pre-commit hook on the three replayed commits is not claimed (no --no-verify was passed; no pin commit was made this round)

## Deviations

- EXTRA gate beyond RB15-12b (additive, HEAD only): the 30 other tests/*.py naming CLAUDE.md, 2 chunks, all green (no base run needed).
- one grep listing was written to /tmp/x_all.txt (outside the notes folder) by mistake and deleted at once (test-file names only).
- one top-level `cd` into the notes folder in one Bash call (the shell cwd persists; all git and gate commands used absolute paths or subshells).
- RB15-12c's named deviation of the previous round: two `git commit --amend` uses on its pin commit (60b4c446 -> a8a966ba -> 40f7e8fc; reflog checked); restated in the PR body.

## Files

- worktree: CLAUDE.md is the only file the rebase resolution wrote (committed); nothing else edited
- C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/fe82d828-54b9-4af1-9c1d-685173488382/scratchpad/S81-15_rebase2/PR_BODY.md sha256 023dd5609be61216fcb212c1a6fb62a05ed532677949835931463cf435c0cf55
- C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/fe82d828-54b9-4af1-9c1d-685173488382/scratchpad/S81-15_rebase2/notes.md sha256 a2525ec54c898e446105c489c78b56ba9918155729bd5303db2acfd22e564a4e
- C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/fe82d828-54b9-4af1-9c1d-685173488382/scratchpad/S81-15_rebase2/gates2.py sha256 dcf92fbf346dbd4a0909da8d6bcc202f90a089e62acdd7b78fd4b95908022282
- C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/fe82d828-54b9-4af1-9c1d-685173488382/scratchpad/S81-15_rebase2/mk_pr_body2.py sha256 25fa54198b3bb9d4e4995169287d3eab95f8ebe16b96cf5ea020bdcddd575588
- C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/fe82d828-54b9-4af1-9c1d-685173488382/scratchpad/S81-15_rebase2/mk_report2.py sha256 8675b52a33af7d8d1675a9492a0a2c37adeaefb3392bf06373ed6bc7d7cdc4fb
- C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/fe82d828-54b9-4af1-9c1d-685173488382/scratchpad/S81-15_rebase2/sweep.py sha256 0d6f1d99dd9680699971456d2766d05dcd57104040634623c07c07a5e21ac427
- C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/fe82d828-54b9-4af1-9c1d-685173488382/scratchpad/S81-15_rebase2/sweep.txt sha256 277ede33e0e7a9b5f683176039e02884072ad5fe0ac33bbeeec02c04f355a53f
- C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/fe82d828-54b9-4af1-9c1d-685173488382/scratchpad/S81-15_rebase2/footprint.txt sha256 1b5f7093bc58b5d05dba50e0bbfcf18c2627b0c2edb1c863032ccd2e361efcdd
- C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/fe82d828-54b9-4af1-9c1d-685173488382/scratchpad/S81-15_rebase2/footprint_stat.txt sha256 e33235b3bdb93624f8e43c689e11c080be243c8b1609e1569d86463deeae9bc2
- C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/fe82d828-54b9-4af1-9c1d-685173488382/scratchpad/S81-15_rebase2/claude_md_mentioners.txt sha256 36a2bd6c04c09379917234dfa22a88baf2d0ccecbc17d57913be7d90820ab2fa
- C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/fe82d828-54b9-4af1-9c1d-685173488382/scratchpad/S81-15_rebase2/claude_md_extra.txt sha256 84423f4f9fa36699f3f01e39ae4baaa19d0a723aacac055ac3caa46bff2344ea
- C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/fe82d828-54b9-4af1-9c1d-685173488382/scratchpad/S81-15_rebase2/gates_results.jsonl sha256 57218b2948dbdc2066c4632fb083064ee86a2ce7926cc137b6603879d1c7f0ea
- C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/fe82d828-54b9-4af1-9c1d-685173488382/scratchpad/S81-15_rebase2/conf/resolve2.py sha256 8d28344d0fda5cc839433be75cfd6bd0cf0c4659ca83083c50f7828b5845331e
- C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/fe82d828-54b9-4af1-9c1d-685173488382/scratchpad/S81-15_rebase2/conf/analyze.py sha256 166b034b38fb0b0eb6cc393ff264176f97e32180c5670793ae63cd8cfece671f
- C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/fe82d828-54b9-4af1-9c1d-685173488382/scratchpad/S81-15_rebase2/conf/analysis.txt sha256 cb004b6261abc3d74548ec93f26eccfdc9becca565347e9a18bd877103e48279

## git status --short (worktree)

```
(empty)
```
