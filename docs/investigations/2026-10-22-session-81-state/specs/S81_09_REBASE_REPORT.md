# S81-09 DEVICE-QUOTA-RIYADH: REBASE ROUND REPORT (RULINGS_REBASE_S81_09 RB9-1..RB9-4; agent Claude Opus 5.5; written through the shell)

- unit: S81-09 DEVICE-QUOTA-RIYADH (lane B backend; ENABLE_DEVICE_DAILY_QUOTA + ENABLE_RIYADH_RESET, default OFF, read per call; FOCUS unit)
- worktree C:/Users/SynAckITPC/Documents/AI/sc-s81-s09, branch feature/s81-s09-device-quota-riyadh; notes folder C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/fe82d828-54b9-4af1-9c1d-685173488382/scratchpad/S81-09_rebase
- head_before 990f06d85a016f3d9f7f0f64f22849c99a4ba8e8 (verified with the branch name and an EMPTY `git status --short` before the first git write)
- base_main = origin/main 6c14ac954f601902d322547de04982033aca5925 (`git fetch origin main` 2026-11-02 12:00; #377 S81-08 on top of e7c81956)
- head_after f563b0c2636a921c31639e3f896f587610f6ecb3 (rev-parse now: f563b0c2636a921c31639e3f896f587610f6ecb3); ONE commit on the base = 990f06d8 replayed; NOT pushed; no new commit (no pin row)
- verdict: READY_FOR_PR (every gate the rulings name measured green or equal to base; the hook files: see below)

## Conflicts and resolutions

- `git merge-tree --write-tree --name-only origin/main 990f06d8` re-measured: CONFLICT (content) CLAUDE.md only (RB9-1)
- `git rebase origin/main`: `UU CLAUDE.md`, every other path staged cleanly (12); two conflict regions in the working copy at lines 171-175 and 526-542
- resolve: line 170: branch rewrite (1169 B) + main's appended S81-08 sentence (279 B, non-ASCII 0) = 1448 B
- resolve: line 194 (api.ts bullet): main's text (branch unchanged)
- resolve: line 340 (Feature Flags pointer): main's text at 6c14ac95 == base's; the branch's pointer added where the branch put it = the branch's line
- resolve: anchor: main's S81-08 block (9 lines) then the branch's S81-09 block (7 lines), then base[520:] ('', '## Tests', ...)
- resolve: line 340: the branch inserted 228 B at offset 2536 (non-ASCII 0); main's text kept whole
- resolve: order: S81-15 owner-steps line 519, S81-08 header line 521, S81-09 header line 530, '## Tests' line 537
- resolve: non-ASCII bytes: base 3937, branch 3931 (delta -6), main 3937, resolved 3931 (= main + branch delta)
- resolve: resolved LF: 582761 B, 999 LF, sha256 d14e0f8b3caa892ed88184fbdd30416a8365a30d10825bce7db225e098e2c67a
- resolve: resolved CRLF (working copy): 583760 B, sha256 0b8b54b6959bb5a260d11f45f5c70070f7448b610d56223de3ac3286f21ca5d3
- resolve: conflicted working copy: 584792 B, CRLF 1005, 2 conflict regions at lines [(170, 174), (525, 541)]
- resolve: auto-merged text outside the markers (984 lines) is an in-order subsequence of the resolution
- resolve: written to the working copy (CRLF), read back byte-equal
- region 1 (the Key-services usage_service.py bullet): main had APPENDED one S81-08 sentence (279 B, ASCII) to the base text; the branch had rewritten the bullet in place (RB9-2 c). Union = the branch's rewrite + main's sentence verbatim at the end (no text of either side dropped or reworded).
- region 2 (the anchor before `## Tests`): main's S81-08 CLIENT-FIRST-OTA block (blank + 8 lines) first, then the branch's S81-09 block (blank + 6 lines), then base's blank + `## Tests` (RB9-2 b: S81-09 immediately after S81-08, before `## Tests`)
- auto-merged (checked against the composed bytes): line 194 the api.ts bullet (main only); line 340 the `**Feature Flags:**` pointer paragraph (branch only: +228 B inserted at offset 2536 into main's text, which is unchanged since e7c81956) (RB9-2 a)
- `git add CLAUDE.md`: index blob sha256 d14e0f8b3caa892ed88184fbdd30416a8365a30d10825bce7db225e098e2c67a (= the composed LF bytes); `git diff --cached --check` rc 0; `GIT_EDITOR=true git rebase --continue` -> f563b0c2, 'Successfully rebased and updated refs/heads/feature/s81-s09-device-quota-riyadh'; no hook output (git's sequencer commits a resolved pick with -n)
- after: `git diff --check origin/main HEAD` rc 0; `git grep -n -E '^(<<<<<<<|>>>>>>>)( |$)' HEAD -- CLAUDE.md app tests`: no match (rc 1); `git diff --stat origin/main...HEAD`: 13 files, 3815 insertions(+), 37 deletions(-) (identical to 990f06d8's stat), no whole-file diff
- `git diff --name-only origin/main...HEAD` = 13 files: CLAUDE.md, app/api/image_routes.py, app/api/text_routes.py, app/api/url_routes.py, app/api/usage_routes.py, app/middleware/error_handler.py, app/services/referral_service.py, app/services/usage_service.py, tests/fixtures/s81_s09_flag_off_golden.json, tests/test_s81_s05_request_context.py, tests/test_s81_s09_device_quota.py, tests/test_s81_s09_gate_rows.py, tests/test_s81_st1_usage_path_offloop.py
- the 12 non-CLAUDE blobs at HEAD are byte-identical to 990f06d8 (`git diff 990f06d8 HEAD` outside CLAUDE.md lists only main's S81-08 files)

## Files at HEAD (blob = git show HEAD:path, the frozen-file identity; working copy = bytes on disk)

- CLAUDE.md +9/-2 blob d14e0f8b3caa892ed88184fbdd30416a8365a30d10825bce7db225e098e2c67a working-copy 0b8b54b6959bb5a260d11f45f5c70070f7448b610d56223de3ac3286f21ca5d3 (CRLF 999) blob==990f06d8 False
- app/api/image_routes.py +4/-1 blob abb783f1b50c80c3e72119c78a7bf38dd5ae536004557fb42c5f77b983a3631a working-copy 717d1e5a05d455dceb66b8c0bc38806d74c7d39cb2c7d57fd25e845654959719 (CRLF 738) blob==990f06d8 True
- app/api/text_routes.py +14/-3 blob d191e0fcf14dd1d3ff33ab091950be8595ffadf2d77b954fb3c3dc4720bf5567 working-copy 767be4451ba9d89b4d656675f95c9cd59e98760a98a1496abe8b5446363d4652 (CRLF 2020) blob==990f06d8 True
- app/api/url_routes.py +6/-1 blob 508fec0ad7d29ea2fbdc58bd7f4e794e1788dfa01385baf700ab6756f8fdbe87 working-copy c0ff7eb2f4e2c046fae7a59667238d69b63040bc0e2d9f88e23ec05a9f87b9b7 (CRLF 569) blob==990f06d8 True
- app/api/usage_routes.py +16/-1 blob 47336e28dbd46f2043f8006ca710740f45c5ebe296d40a39c9e8d4e18ab9ef66 working-copy 8645776ffaffc56c69347712569a6e73797ca5d72b9b1e328615c20590565c98 (CRLF 30) blob==990f06d8 True
- app/middleware/error_handler.py +29/-0 blob bf71cbd1dcd05071b3bb83aacc2ea97d0150fdfe2f3b0b471a2d3a09008c8198 working-copy 56332100e766db5f1bbe281540e17b657fe57715000b6502b6ed70a604f7961c (CRLF 315) blob==990f06d8 True
- app/services/referral_service.py +38/-6 blob aad54e3cc4227c8f67c6067969d519903be9d371005867dc2ba6c7c7f1447cbb working-copy a928a6b65b69c29b808b652f1424860b750c115d724b4f77394e558bf9f11807 (CRLF 968) blob==990f06d8 True
- app/services/usage_service.py +478/-12 blob b096a76733a291fb02846c539d44c6e3d28c6b0d342c167f57cd67d47a1665b8 working-copy 570785b43ead06fa1c648cd7a4b27dabf17403c05386c7ffbae476279175e88c (CRLF 1305) blob==990f06d8 True
- tests/fixtures/s81_s09_flag_off_golden.json +722/-0 blob 02b29cc6d3a649324f71b27472ae135cc015ba39e9659b49c0306d1e249e6176 working-copy 5b0afe5e2198f68e6dd10d3d76e3fd6079845123b0b0d196e2c81e0dbe9bcd34 (CRLF 722) blob==990f06d8 True
- tests/test_s81_s05_request_context.py +27/-4 blob c0394a5307c5038822e4ef8b668942ae244b3a7ab9f3f5f476bee2b095b62ce7 working-copy 49d0b015fdd6fe53266fa9a15a0fdf377f706e6f106613afc86fd7483de8b5cc (CRLF 1848) blob==990f06d8 True
- tests/test_s81_s09_device_quota.py +2068/-0 blob 551a3167ac54d1ef842f76d1603c05c3a7e404384f6f161bb33bc1c4fad6963f working-copy 6ebac73289d2613b8c9715df94098676df1bfa58c1c8e66a6e1256d7e5c27d69 (CRLF 2068) blob==990f06d8 True
- tests/test_s81_s09_gate_rows.py +389/-0 blob a8e01fcf6f22c5dee37d10ba461176c642976fd930a7c5a750c99c0fa152ba5e working-copy 0e30c1df7d075ee92e8514c0671f6c7d0e321dd99ca77879624b2836a4498e0b (CRLF 389) blob==990f06d8 True
- tests/test_s81_st1_usage_path_offloop.py +15/-7 blob 6a0d65ad05c62ecfc3d520d326b7c45ad6fa19e00048f1010e948f5f29153273 working-copy 6380fff98dadf14856630060255da9ef52ef8816b1e8d0fb9b93e10f2f177b16 (CRLF 2776) blob==990f06d8 True
- frozen RED tests/test_s81_s09_device_quota.py blob 551a3167ac54d1ef842f76d1603c05c3a7e404384f6f161bb33bc1c4fad6963f (byte-identical; its working copy is now CRLF after the rebase checkout, 89,243 B); golden 02b29cc6d3a649324f71b27472ae135cc015ba39e9659b49c0306d1e249e6176 (byte-identical); gate rows a8e01fcf6f22c5dee37d10ba461176c642976fd930a7c5a750c99c0fa152ba5e (unchanged, 24 nodes)

## Pin rows and mutants

- none (RB9: the base moved by client files, CLAUDE.md and docs only; no literal this unit reads moved; no gate went red); no pin commit; no mutation harness run (no .qa-mutation.lock created)

## Every runner line (pyt.py, one pytest process at a time; batches run by a sequential background driver launched once each and polled)

### batch1

    # driver start 2026-11-02 12:05:20, 9 runs
    ## run s09rb-unit-off flags_on=False files=1
    ====================== 193 passed, 11 warnings in 3.53s =======================
    [hermeticity] sentinel checked 193 test(s)
    [netguard] blocked 0 attempt(s) from 0 node(s)
    [pyt] tag=s09rb-unit-off start=2026-11-02 12:05:20 end=2026-11-02 12:05:24 elapsed=4s bound=600s status=OK rc=0
    ## end s09rb-unit-off rc=0
    ## run s09rb-unit-on flags_on=True files=1
    ====================== 193 passed, 11 warnings in 3.50s =======================
    [hermeticity] sentinel checked 193 test(s)
    [netguard] blocked 0 attempt(s) from 0 node(s)
    [pyt] tag=s09rb-unit-on start=2026-11-02 12:05:24 end=2026-11-02 12:05:29 elapsed=4s bound=600s status=OK rc=0
    ## end s09rb-unit-on rc=0
    ## run s09rb-rows-off flags_on=False files=1
    ======================= 24 passed, 10 warnings in 2.68s =======================
    [hermeticity] sentinel checked 24 test(s)
    [netguard] blocked 0 attempt(s) from 0 node(s)
    [pyt] tag=s09rb-rows-off start=2026-11-02 12:05:29 end=2026-11-02 12:05:32 elapsed=3s bound=600s status=OK rc=0
    ## end s09rb-rows-off rc=0
    ## run s09rb-rows-on flags_on=True files=1
    ======================= 24 passed, 10 warnings in 2.69s =======================
    [hermeticity] sentinel checked 24 test(s)
    [netguard] blocked 0 attempt(s) from 0 node(s)
    [pyt] tag=s09rb-rows-on start=2026-11-02 12:05:32 end=2026-11-02 12:05:35 elapsed=3s bound=600s status=OK rc=0
    ## end s09rb-rows-on rc=0
    ## run s09rb-r8pair flags_on=False files=2
    ======================= 273 passed, 1 warning in 16.26s =======================
    [hermeticity] sentinel checked 273 test(s)
    [netguard] blocked 0 attempt(s) from 0 node(s)
    [pyt] tag=s09rb-r8pair start=2026-11-02 12:05:36 end=2026-11-02 12:05:53 elapsed=17s bound=600s status=OK rc=0
    ## end s09rb-r8pair rc=0
    ## run s09rb-metering-off flags_on=False files=1
    ======================= 21 passed, 13 warnings in 2.91s =======================
    [hermeticity] sentinel checked 21 test(s)
    [netguard] blocked 2 attempt(s) from 2 node(s)
    [pyt] tag=s09rb-metering-off start=2026-11-02 12:05:53 end=2026-11-02 12:05:56 elapsed=4s bound=600s status=OK rc=0
    ## end s09rb-metering-off rc=0
    ## run s09rb-metering-on flags_on=True files=1
    ======================= 21 passed, 13 warnings in 2.99s =======================
    [hermeticity] sentinel checked 21 test(s)
    [netguard] blocked 2 attempt(s) from 2 node(s)
    [pyt] tag=s09rb-metering-on start=2026-11-02 12:05:57 end=2026-11-02 12:06:00 elapsed=4s bound=600s status=OK rc=0
    ## end s09rb-metering-on rc=0
    ## run s09rb-readers flags_on=False files=2
    ======================== 79 passed, 1 warning in 4.44s ========================
    [hermeticity] sentinel checked 79 test(s)
    [netguard] blocked 0 attempt(s) from 0 node(s)
    [pyt] tag=s09rb-readers start=2026-11-02 12:06:00 end=2026-11-02 12:06:05 elapsed=5s bound=600s status=OK rc=0
    ## end s09rb-readers rc=0
    ## run s09rb-ciorder flags_on=False files=28
    ===================== 1711 passed, 347 warnings in 48.01s =====================
    [pyt] tag=s09rb-ciorder start=2026-11-02 12:06:06 end=2026-11-02 12:06:55 elapsed=50s bound=1200s status=OK rc=0
    ## end s09rb-ciorder rc=0
    # driver end 2026-11-02 12:06:55

### batch2

    # driver start 2026-11-02 12:08:05, 11 runs
    ## run s09rb-base-u15 flags_on=False files=15
    ====================== 102 passed, 2 warnings in 16.84s =======================
    [hermeticity] sentinel checked 102 test(s)
    [netguard] blocked 4 attempt(s) from 3 node(s)
    [pyt] tag=s09rb-base-u15 start=2026-11-02 12:08:05 end=2026-11-02 12:08:23 elapsed=18s bound=1200s status=OK rc=0
    ## end s09rb-base-u15 rc=0
    ## run s09rb-comm-00 flags_on=False files=17
    ===================== 899 passed, 345 warnings in 26.45s ======================
    [hermeticity] sentinel checked 899 test(s)
    [netguard] blocked 2 attempt(s) from 2 node(s)
    [pyt] tag=s09rb-comm-00 start=2026-11-02 12:08:23 end=2026-11-02 12:08:51 elapsed=28s bound=1200s status=OK rc=0
    ## end s09rb-comm-00 rc=0
    ## run s09rb-comm-01 flags_on=False files=10
    ===================== 1352 passed, 13 warnings in 35.42s ======================
    [hermeticity] sentinel checked 1352 test(s)
    [netguard] blocked 25 attempt(s) from 3 node(s)
    [pyt] tag=s09rb-comm-01 start=2026-11-02 12:08:51 end=2026-11-02 12:09:28 elapsed=37s bound=1200s status=OK rc=0
    ## end s09rb-comm-01 rc=0
    ## run s09rb-comm-02 flags_on=False files=25
    =============== 969 passed, 6 deselected, 23 warnings in 37.22s ===============
    [pyt] tag=s09rb-comm-02 start=2026-11-02 12:09:28 end=2026-11-02 12:10:07 elapsed=39s bound=1200s status=OK rc=0
    ## end s09rb-comm-02 rc=0
    ## run s09rb-comm-03 flags_on=False files=25
    ===================== 2284 passed, 13 warnings in 32.19s ======================
    [pyt] tag=s09rb-comm-03 start=2026-11-02 12:10:07 end=2026-11-02 12:10:41 elapsed=34s bound=1200s status=OK rc=0
    ## end s09rb-comm-03 rc=0
    ## run s09rb-comm-04 flags_on=False files=25
    ================= 727 passed, 18 warnings in 66.01s (0:01:06) =================
    [pyt] tag=s09rb-comm-04 start=2026-11-02 12:10:41 end=2026-11-02 12:11:48 elapsed=67s bound=1200s status=OK rc=0
    ## end s09rb-comm-04 rc=0
    ## run s09rb-comm-05 flags_on=False files=25
    = 969 passed, 27 skipped, 6 deselected, 1 xfailed, 12 warnings, 2 errors in 23.85s =
    ERROR tests/test_prompt_truth.py::test_truth_on_prefix_static_and_cacheable
    ERROR tests/test_prompt_truth.py::test_render_digests_match_base_except_the_fence
    [pyt] tag=s09rb-comm-05 start=2026-11-02 12:11:48 end=2026-11-02 12:12:13 elapsed=25s bound=1200s status=FAIL rc=1
    ## end s09rb-comm-05 rc=1
    ## run s09rb-comm-06 flags_on=False files=25
    ================ 1041 passed, 13 warnings in 98.31s (0:01:38) =================
    [netguard] blocked 6 attempt(s) from 5 node(s)
    [pyt] tag=s09rb-comm-06 start=2026-11-02 12:12:13 end=2026-11-02 12:13:53 elapsed=99s bound=1200s status=OK rc=0
    ## end s09rb-comm-06 rc=0
    ## run s09rb-comm-07 flags_on=False files=24
    === 2569 passed, 1 skipped, 8 deselected, 12 warnings in 110.59s (0:01:50) ====
    [pyt] tag=s09rb-comm-07 start=2026-11-02 12:13:53 end=2026-11-02 12:15:45 elapsed=112s bound=1200s status=OK rc=0
    ## end s09rb-comm-07 rc=0
    ## run s09rb-comm-08 flags_on=False files=23
    === 1130 passed, 9 skipped, 2 deselected, 35 xfailed, 17 warnings in 57.76s ===
    [pyt] tag=s09rb-comm-08 start=2026-11-02 12:15:45 end=2026-11-02 12:16:44 elapsed=59s bound=1200s status=OK rc=0
    ## end s09rb-comm-08 rc=0
    ## run s09rb-secretscan flags_on=False files=1
    ======================== 31 passed, 1 warning in 4.15s ========================
    [hermeticity] sentinel checked 31 test(s)
    [netguard] blocked 0 attempt(s) from 0 node(s)
    [pyt] tag=s09rb-secretscan start=2026-11-02 12:16:44 end=2026-11-02 12:16:49 elapsed=5s bound=600s status=OK rc=0
    ## end s09rb-secretscan rc=0
    # driver end 2026-11-02 12:16:49

### batch3

    # driver start 2026-11-02 12:16:57, 2 runs
    ## run s09rb-hook-notdash flags_on=False files=4
    ========= 167 passed, 160 deselected, 7 warnings in 278.95s (0:04:38) =========
    [hermeticity] sentinel checked 167 test(s)
    [netguard] blocked 0 attempt(s) from 0 node(s)
    [pyt] tag=s09rb-hook-notdash start=2026-11-02 12:16:57 end=2026-11-02 12:21:36 elapsed=280s bound=1800s status=OK rc=0
    ## end s09rb-hook-notdash rc=0
    ## run s09rb-hook-dash flags_on=False files=4
    === 157 passed, 3 skipped, 167 deselected, 7 warnings in 491.12s (0:08:11) ====
    [hermeticity] sentinel checked 160 test(s)
    [netguard] blocked 0 attempt(s) from 0 node(s)
    [pyt] tag=s09rb-hook-dash start=2026-11-02 12:21:36 end=2026-11-02 12:29:48 elapsed=492s bound=1800s status=OK rc=0
    ## end s09rb-hook-dash rc=0
    # driver end 2026-11-02 12:29:48

## Comm set and the base record (RB9-3 d, LC-6)

- re-derived at the rebased HEAD with the RED's builder (build_comm_rebase.py = the GREEN's build_comm_head.py, seed S81-09_spec/comm_seed.txt): 200 members, IDENTICAL to specs/S81_09_COMM_SET.txt; chunks identical to GREEN's (17, 10, 25 x 6, 23); no addition (main #377 touched no tests/ or app/ file)
- base record at 6c14ac954f601902d322547de04982033aca5925: 185 files reused per file from the stored records 0ea73814... (S81-12 rebase-fix, 110 files) and 336233f0... (S81-10 RED, 425 files), which agree on every shared file; the 15 files not yet recorded run in a detached scratch worktree (git -c core.longpaths=true worktree add --detach <notes>/b origin/main; no junction): tests/test_feedback_service.py, tests/test_m13_37_freemium_atomic_consume.py, tests/test_referral_expiry.py, tests/test_referral_full_response_column.py, tests/test_referral_lifetime_cap.py, tests/test_referral_loop2.py, tests/test_referral_service_internals.py, tests/test_referral_share_status_lifetime.py, tests/test_register_invite_linking.py, tests/test_scoring_calibration_bundle_c.py, tests/test_url_validator_offloop_hops.py, tests/test_usage_device_inheritance.py, tests/test_usage_referral_bonus.py, tests/test_usage_service_internals.py, tests/test_usage_tiers.py
- [pyt] tag=s09rb-base-u15 start=2026-11-02 12:08:05 end=2026-11-02 12:08:23 elapsed=18s bound=1200s status=OK rc=0 -- 102 passed, 0 failed
- union stored: harness/base_records/6c14ac954f601902d322547de04982033aca5925/c9f7585d75ab76dab68c1d7e222563357c6ea34f327c728270cecbde479bb9fd.txt + .pyt.log + .files (set sha256 = c9f7585d75ab76dab68c1d7e222563357c6ea34f327c728270cecbde479bb9fd, the same set sha as the e7c81956 record c9f7585d...)
- base failed/error set: tests/test_prompt_truth.py::test_render_digests_match_base_except_the_fence, tests/test_prompt_truth.py::test_truth_on_prefix_static_and_cacheable
- HEAD failed/error set: tests/test_prompt_truth.py::test_render_digests_match_base_except_the_fence, tests/test_prompt_truth.py::test_truth_on_prefix_static_and_cacheable
- comm -13 (branch-only-new): EMPTY; comm -23 (base-only): empty
- this box's four deterministic failures (tests/test_auth_interceptor.py x2, tests/test_page_scraping.py x2 in the S81-10 record) are not members of the 200-file set (neither file is selected by the union rule), so they appear on neither side
- the scratch worktree removed with `git worktree remove --force` and verified gone (`git worktree list` has no entry, the directory is gone); the temp index file removed

## Client gates (RB9-3 e, f)

- tools by path from sc-s81-s09/SmartCompareApp through the orchestrator junction (node_modules/@babel/core and node_modules/.bin/jest present; never touched): node v24.11.1, jest 29.7.0, tsc Version 5.9.3
- jest_shareTruth.log: [jest] tag=s09rb-fence-shareTruth start=2026-11-02 12:09:24 end=2026-11-02 12:09:27 rc=0
- jest_shareTruth.log: Test Suites: 1 passed, 1 total
- jest_shareTruth.log: Tests: 10 passed, 10 total
- jest_shareTruth.log: Snapshots: 0 total
- jest_fences13.log: [jest] tag=s09rb-fences-13 start=2026-11-02 12:09:36 end=2026-11-02 12:09:42 rc=1
- jest_fences13.log: Test Suites: 1 failed, 12 passed, 13 total
- jest_fences13.log: Tests: 4 failed, 226 passed, 230 total
- jest_fences13.log: Snapshots: 0 total
- jest_full.log: [jest] tag=s09rb-jest-full start=2026-11-02 12:09:51 end=2026-11-02 12:10:08 rc=1
- jest_full.log: Test Suites: 1 failed, 3 skipped, 385 passed, 386 of 389 total
- jest_full.log: Tests: 4 failed, 13 skipped, 13 todo, 3794 passed, 3824 total
- jest_full.log: Snapshots: 42 passed, 42 total
- the red nodes in both runs: nativeBundle.w37 d5 (react-native-gesture-handler removed), k2, k4, k5 (Expo SDK 54 patch level / eslint-config-expo / offline expo-install consistency) = the four accepted drift nodes; no other red
- [tsc] tag=s09rb-tsc start=2026-11-02 12:10:39 end=2026-11-02 12:10:47 rc=0 (0 error TS lines)
- no -u, no .snap; `git status --short` empty after the jest runs

## The hook on the replayed commit (RB9-3 g)

- `git rebase --continue` printed no hook output (git's sequencer commits a resolved pick with `git commit -n`); so the repo hook was run BY HAND on the replayed diff: in the detached scratch worktree at 6c14ac95, `GIT_INDEX_FILE=<notes>/hook_index git read-tree f563b0c2` (a temp index file in the notes folder; the scratch worktree's own index, HEAD and refs untouched), then `GIT_INDEX_FILE=<notes>/hook_index sh .githooks/pre-commit` (main's hook bytes = HEAD's)
    All checks passed!
    Warning: Python 3.12 cannot parse code formatted for Python 3.15. To fix this: run Black with Python 3.15, set --target-version to py312, or use --fast to skip the safety check. Black's safety check verifies equivalence by parsing the AST, which fails when the running Python is older than the target version.
    All done! \u2728 \U0001f370 \u2728
    1 file would be left unchanged.
    [hook] tag=s09rb-hook-replayed start=2026-11-02 12:11:12 end=2026-11-02 12:11:15 rc=0
- read-only `gitleaks git --log-opts=6c14ac95..f563b0c2 --redact --no-banner --no-color --ignore-gitleaks-allow --config <HEAD:.gitleaks.toml copy>`: rc 0, '1 commits scanned', 'no leaks found' (report [])

## NOT MEASURED

- none (every gate the task and RB9-3 name was measured)

## Deviations and notes for the gate

1. RB9-2 (c) says the usage_service.py bullet 'as the branch rewrote it'; main's S81-08 had appended one sentence to the same bullet (the ruling does not name it). Kept verbatim after the branch's rewrite under the union rule (never drop main text); if the orchestrator wants the bullet without it, that is a one-sentence docs edit.
2. RB9-2 (a) says main's Feature Flags paragraph 'carries S81-06, S81-08b, S81-15, S81-08'; measured: main's paragraph is byte-identical to e7c81956's (S81-08 added no pointer there; it has no runtime flag); the union therefore equals the branch's paragraph (main's text + this unit's pointer).
3. The hook check on the replayed commit used `git read-tree` into a temp index file under the notes folder inside the scratch worktree (a git plumbing write that the task's git-exception list does not name; it wrote only that notes file, moved no ref and touched no worktree index); stated for transparency.
4. Concurrency: the pytest batches ran one pytest process at a time through a sequential driver (background, launched once, polled: the harness rule); the jest runs and tsc (one at a time) overlapped the pytest driver (different tools); the box was fast throughout (node -e 0 0.09 s; no other pytest seen).
5. The CI-order set is 28 files (GREEN's 25 + spend_breaker, s08b legacy, s08b gate rows; the two readers were already members): 1711 passed vs fix round 1's 25-file 1313 (the three files add 398 nodes).
6. The PR body is pure ASCII without the generation trailer (the orchestrator appends it); the GREEN / fix-round per-run lines and the E1 digest list moved to S81_09_REBASE_EVIDENCE.md to stay under 25,600 B.

## git status --short (sc-s81-s09)

    (empty)

## git worktree list (after the scratch removal)

    C:/Users/SynAckITPC/Documents/AI/sc-s81-s09                                                                                                     f563b0c2 [feature/s81-s09-device-quota-riyadh]

## Notes-folder outputs (sha256)

- PR_BODY.md 25272 B sha256 6dce5f01fd19fe4cf01d5bfde925b81aa0eeb4421b18937f8ec79bcf82080a22
- S81_09_REBASE_EVIDENCE.md 30479 B sha256 748eea425bb46589bc5811b37a02b2c40fb79bad1598914f714157853fa76709
- notes.md 1599 B sha256 693ba0e174a595a377f911d84f1cbc9d4325c0d730ec363c109e6827d9e35740
- CLAUDE.resolved.lf.md 582761 B sha256 d14e0f8b3caa892ed88184fbdd30416a8365a30d10825bce7db225e098e2c67a
- resolve_claude.py 6977 B sha256 3f6ab481135133482a9559ea4e1ec24b056287d96835fdd0ba75d92868baf89c
- comm_result.json 1820 B sha256 f12173ac56d9ae1da0717e9ebadb5e4ad9e983cb900ada6abafb678a0675bbc6
