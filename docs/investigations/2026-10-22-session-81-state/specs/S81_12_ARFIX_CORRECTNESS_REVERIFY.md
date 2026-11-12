# S81-12 ARFIX CORRECTNESS RE-VERIFY -- verdict SOUND
unit S81-12 LEGAL-V3 ARFIX; lens correctness (AF-9 items 1-5); re-verifier Opus 5.5; 2026-11-12 03:25-04:45 AST
HEAD a0244f4403c55326ddf0171455805e7d2a5879aa on feature/s81-legal-v3, ONE parent dd9738f77650fbda370ca75a99c8596e44d00412; git status --short EMPTY at start and end; nothing edited in the worktree; origin/main (local ref, no fetch: network not granted) 6b909e0a.

## (1) Re-hash (git bytes; scripts rehash.py / rehash2.py, outputs rehash_out.txt / rehash2_out.txt)
- footprint dd9738f7..HEAD: 14 files +203/-37; origin/main...HEAD 45 files (no new path).
- app/legal/privacy_policy_ar.md 5cc039a3... (34,433 B), terms_of_service_ar.md 7d9c53e5... (25,950 B), SmartCompareApp/src/i18n/ar.json 1fe60d12... (71,911 B): all = ARFIX_INPUTS; LF, no BOM; cmp with s12/arfix/expected/* BYTE-EQUAL; base shas f9a9de3b / 693fca9c / b5d84aae at dd9738f7 OK.
- applying the ten spans of arfix_edits.json to the dd9738f7 bytes reproduces HEAD exactly for all three files (old counts at base 2,2,1,1,1 / 1 / 1,1 = expected; new counts at HEAD equal): no other Arabic byte moved in the three files.
- English: privacy_policy.md 75e4fde3..., terms_of_service.md c48e97c5..., en.json 8e3f2206... OK and byte-identical to dd9738f7; landing/privacy.html + landing/terms.html unchanged; scripts/legal_variants_u8.json 7e896e67... + tests/fixtures/legal_fill_in_u8.json 955a13d0... unchanged.
- fence digest recomputed by its recipe (EN title, EN body, AR title, AR body joined by LF): dd9738f7 77ac6348..., HEAD adfc77d2... = expected; aiConsentVersion.s69 pins adfc77d2 and version 3; AR 1,011 keys, same order, EN == AR key set; changed keys exactly onboarding.s5.privacy_anon_body + aiConsent.body.
- frozen: tests/test_s81_12_legal_v3.py e860e18d -> 3df7c93c..., diff = EK6 only (+BOT_URL_AR at :132; R6 AR needle BOT_URL -> BOT_URL_AR at :620; +2 lines at :623-624 refusing BOT_URL in AR s6); legalV3.s81_12.test.ts f8f21f89 unchanged; gate rows b98caa6a -> 4dd5c284... (16 defs, 27 nodes, G-k..G-o present).
- landing/ar/privacy.html +6/-6, landing/ar/terms.html +1/-1 (line diff).
- CLAUDE.md: 1,105 lines both sides; diff = line 199 (77ac6348... -> adfc77d2... + the copy-fix / material-change rule, consistent with the fence file's RULE header) and line 641 (one ARFIX sentence inserted: 27 nodes, EK6, G-k..G-o, R8 -> S81-12c, R6 / R7 limits); 77ac6348 mentions 0, adfc77d2 1; HEAD blob sha256 5384218a... (748,819 B). No other line moved; the row states no other gate-row count to falsify.

## (2) Mutants (detached scratch worktree S81-12_arfix/adv at a0244f44, python only, no junction; .qa-mutation.lock; byte copy + sha restore each; removed with git worktree remove --force; git worktree list shows none)
10 / 10 KILLED, every killing failure an AssertionError (no other error type in any mutant log):
MUTANT m01_J1_rev: applied on SmartCompareApp/src/i18n/ar.json (old count 1, occ None); sha 2ce124d01aa3 -> cde27821eefb
[wait] m01_J1_rev waited 3s; probe clean at 03:29:33
   [pyt] tag=s12a-m01_J1_rev start=2026-11-12 03:29:33 end=2026-11-12 03:29:39 elapsed=6s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\dc5dcae5-8753-4884-a665-dd310b93b8f5\scratchpad\S81-12_arfix\corr\m01_J1_rev.log
   FAILED tests/test_s81_12_gate_rows.py::test_g_k_move_to_anthropic_in_progress_tense
   FAILED tests/test_s81_12_legal_v3.py::test_h1_merge_window_recorded
   FAILED tests/test_s81_12_legal_v3.py::test_r14_consent_v3_version_copy_and_fence
   KILL expected ['test_g_k_'] -> hit ['test_g_k_']; failure types ['Asserti']; verdict KILLED
   restore m01_J1_rev: sha equal True
MUTANT m02_T1_rev: applied on app/legal/terms_of_service_ar.md (old count 1, occ None); sha 65e9a3c7a7ea -> 0259dd56ee4c
[wait] m02_T1_rev waited 1s; probe clean at 03:29:40
   [pyt] tag=s12a-m02_T1_rev start=2026-11-12 03:29:40 end=2026-11-12 03:29:47 elapsed=7s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\dc5dcae5-8753-4884-a665-dd310b93b8f5\scratchpad\S81-12_arfix\corr\m02_T1_rev.log
   FAILED tests/test_s81_12_gate_rows.py::test_g_k_move_to_anthropic_in_progress_tense
   FAILED tests/test_s81_12_legal_v3.py::test_h1_merge_window_recorded
   FAILED tests/test_s81_12_legal_v3.py::test_p1_fill_in_idempotent_and_landing_regions_current
   KILL expected ['test_g_k_'] -> hit ['test_g_k_']; failure types ['Asserti']; verdict KILLED
   restore m02_T1_rev: sha equal True
MUTANT m03_P1_rev_s4: applied on app/legal/privacy_policy_ar.md (old count 2, occ 1); sha d127339d4d58 -> 2c90e93c1b1f
[wait] m03_P1_rev_s4 waited 1s; probe clean at 03:29:49
   [pyt] tag=s12a-m03_P1_rev_s4 start=2026-11-12 03:29:49 end=2026-11-12 03:29:53 elapsed=4s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\dc5dcae5-8753-4884-a665-dd310b93b8f5\scratchpad\S81-12_arfix\corr\m03_P1_rev_s4.log
   FAILED tests/test_s81_12_gate_rows.py::test_g_k_move_to_anthropic_in_progress_tense
   FAILED tests/test_s81_12_legal_v3.py::test_h1_merge_window_recorded
   FAILED tests/test_s81_12_legal_v3.py::test_p1_fill_in_idempotent_and_landing_regions_current
   KILL expected ['test_g_k_'] -> hit ['test_g_k_']; failure types ['Asserti']; verdict KILLED
   restore m03_P1_rev_s4: sha equal True
MUTANT m04_J2_rev: applied on SmartCompareApp/src/i18n/ar.json (old count 1, occ None); sha 2ce124d01aa3 -> 75e3fbb356c0
[wait] m04_J2_rev waited 1s; probe clean at 03:29:55
   [pyt] tag=s12a-m04_J2_rev start=2026-11-12 03:29:55 end=2026-11-12 03:29:59 elapsed=4s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\dc5dcae5-8753-4884-a665-dd310b93b8f5\scratchpad\S81-12_arfix\corr\m04_J2_rev.log
   FAILED tests/test_s81_12_gate_rows.py::test_g_l_onboarding_step5_never_sends_clause
   FAILED tests/test_s81_12_legal_v3.py::test_h1_merge_window_recorded
   KILL expected ['test_g_l_'] -> hit ['test_g_l_']; failure types ['Asserti']; verdict KILLED
   restore m04_J2_rev: sha equal True
MUTANT m05_P3_rev: applied on app/legal/privacy_policy_ar.md (old count 1, occ None); sha d127339d4d58 -> 640021cf680f
[wait] m05_P3_rev waited 1s; probe clean at 03:30:01
   [pyt] tag=s12a-m05_P3_rev start=2026-11-12 03:30:01 end=2026-11-12 03:30:08 elapsed=7s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\dc5dcae5-8753-4884-a665-dd310b93b8f5\scratchpad\S81-12_arfix\corr\m05_P3_rev.log
   FAILED tests/test_s81_12_gate_rows.py::test_g_m_privacy_s6_links_and_canonical_bot_address
   FAILED tests/test_s81_12_legal_v3.py::test_h1_merge_window_recorded
   FAILED tests/test_s81_12_legal_v3.py::test_p1_fill_in_idempotent_and_landing_regions_current
   KILL expected ['test_g_m_'] -> hit ['test_g_m_']; failure types ['Asserti']; verdict KILLED
   restore m05_P3_rev: sha equal True
MUTANT m06_P5_rev: applied on app/legal/privacy_policy_ar.md (old count 1, occ None); sha d127339d4d58 -> fce41cfa0978
[wait] m06_P5_rev waited 1s; probe clean at 03:30:10
   [pyt] tag=s12a-m06_P5_rev start=2026-11-12 03:30:10 end=2026-11-12 03:30:14 elapsed=5s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\dc5dcae5-8753-4884-a665-dd310b93b8f5\scratchpad\S81-12_arfix\corr\m06_P5_rev.log
   FAILED tests/test_s81_12_gate_rows.py::test_g_n_privacy_s14_random_install_identifier
   FAILED tests/test_s81_12_legal_v3.py::test_h1_merge_window_recorded
   FAILED tests/test_s81_12_legal_v3.py::test_p1_fill_in_idempotent_and_landing_regions_current
   KILL expected ['test_g_n_'] -> hit ['test_g_n_']; failure types ['Asserti']; verdict KILLED
   restore m06_P5_rev: sha equal True
MUTANT m07_P2_rev_first: applied on app/legal/privacy_policy_ar.md (old count 2, occ 0); sha d127339d4d58 -> 74c69a747a70
[wait] m07_P2_rev_first waited 1s; probe clean at 03:30:16
   [pyt] tag=s12a-m07_P2_rev_first start=2026-11-12 03:30:16 end=2026-11-12 03:30:23 elapsed=7s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\dc5dcae5-8753-4884-a665-dd310b93b8f5\scratchpad\S81-12_arfix\corr\m07_P2_rev_first.log
   FAILED tests/test_s81_12_gate_rows.py::test_g_c_pre_switch_carve_out_sentence[ar]
   FAILED tests/test_s81_12_gate_rows.py::test_g_o_data_shared_with_openai_common_construction
   FAILED tests/test_s81_12_legal_v3.py::test_h1_merge_window_recorded
   FAILED tests/test_s81_12_legal_v3.py::test_p1_fill_in_idempotent_and_landing_regions_current
   KILL expected ['test_g_o_'] -> hit ['test_g_o_']; failure types ['Asserti']; verdict KILLED
   restore m07_P2_rev_first: sha equal True
MUTANT m08_P4_slash_readded: applied on app/legal/privacy_policy_ar.md (old count 1, occ None); sha d127339d4d58 -> 2d064f11703b
[wait] m08_P4_slash_readded waited 1s; probe clean at 03:30:24
   [pyt] tag=s12a-m08_P4_slash_readded start=2026-11-12 03:30:24 end=2026-11-12 03:30:29 elapsed=4s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\dc5dcae5-8753-4884-a665-dd310b93b8f5\scratchpad\S81-12_arfix\corr\m08_P4_slash_readded.log
   FAILED tests/test_s81_12_gate_rows.py::test_g_m_privacy_s6_links_and_canonical_bot_address
   FAILED tests/test_s81_12_legal_v3.py::test_h1_merge_window_recorded
   FAILED tests/test_s81_12_legal_v3.py::test_p1_fill_in_idempotent_and_landing_regions_current
   FAILED tests/test_s81_12_legal_v3.py::test_r6_privacy_s6_catalogue_crawler_and_sponsored[ar]
   KILL expected ['test_r6_privacy_s6_catalogue_crawler_and_sponsored[ar]', 'test_g_m_'] -> hit ['test_r6_privacy_s6_catalogue_crawler_and_sponsored[ar]', 'test_g_m_']; failure types ['Asserti']; verdict KILLED
   restore m08_P4_slash_readded: sha equal True
MUTANT m09_classT_prefill_P5_rev: applied on tests/fixtures/legal_prefill_u8/privacy_policy_ar.md (old count 1, occ None); sha 098832462dc3 -> e5836d0fa5a5
[wait] m09_classT_prefill_P5_rev waited 1s; probe clean at 03:30:30
   [pyt] tag=s12a-m09_classT_prefill_P5_rev start=2026-11-12 03:30:30 end=2026-11-12 03:30:38 elapsed=8s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\dc5dcae5-8753-4884-a665-dd310b93b8f5\scratchpad\S81-12_arfix\corr\m09_classT_prefill_P5_rev.log
   FAILED tests/test_legal_docs_u8_polish.py::test_polish_prefill_snapshot_tracks_the_documents
   FAILED tests/test_s81_12_legal_v3.py::test_h1_merge_window_recorded
   KILL expected ['test_polish_prefill_snapshot_tracks_the_documents'] -> hit ['test_polish_prefill_snapshot_tracks_the_documents']; failure types ['Asserti']; verdict KILLED
   restore m09_classT_prefill_P5_rev: sha equal True
MUTANT m10_EN_byte_flip_crawler: applied on app/legal/privacy_policy.md (old count 1, occ None); sha fc4b46d467a9 -> a1ecb416b82c
[wait] m10_EN_byte_flip_crawler waited 1s; probe clean at 03:30:39
   [pyt] tag=s12a-m10_EN_byte_flip_crawler start=2026-11-12 03:30:39 end=2026-11-12 03:30:44 elapsed=5s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\dc5dcae5-8753-4884-a665-dd310b93b8f5\scratchpad\S81-12_arfix\corr\m10_EN_byte_flip_crawler.log
   FAILED tests/test_s81_12_legal_v3.py::test_h1_merge_window_recorded
   FAILED tests/test_s81_12_legal_v3.py::test_p1_fill_in_idempotent_and_landing_regions_current
   FAILED tests/test_s81_12_legal_v3.py::test_r6_privacy_s6_catalogue_crawler_and_sponsored[en]
   KILL expected ['test_r6_privacy_s6_catalogue_crawler_and_sponsored[en]'] -> hit ['test_r6_privacy_s6_catalogue_crawler_and_sponsored[en]']; failure types ['Asserti']; verdict KILLED
   restore m10_EN_byte_flip_crawler: sha equal True
adv git status after all mutants: []
Not run as a mutant: the jest fence (aiConsentVersion.s69 PINNED digest): no junction in a scratch worktree; the CLASS T requirement is met by m09 (the prefill snapshot), and the digest itself is recomputed above.

## (3) Gates at the real HEAD (worktree sc-s81-s12, probe-gated)
=================== 1 failed, 37 passed, 1 warning in 2.73s ===================
[hermeticity] sentinel checked 38 test(s)
[netguard] blocked 0 attempt(s) from 0 node(s)
FAILED tests/test_s81_12_legal_v3.py::test_h1_merge_window_recorded - Asserti...
[pyt] tag=s12a-corr-unit start=2026-11-12 03:32:11 end=2026-11-12 03:32:15 elapsed=4s bound=1200s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\dc5dcae5-8753-4884-a665-dd310b93b8f5\scratchpad\S81-12_arfix\corr\corr-unit.log
======================== 27 passed, 1 warning in 1.90s ========================
[hermeticity] sentinel checked 27 test(s)
[netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s12a-corr-gaterows start=2026-11-12 03:32:23 end=2026-11-12 03:32:26 elapsed=3s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\dc5dcae5-8753-4884-a665-dd310b93b8f5\scratchpad\S81-12_arfix\corr\corr-gaterows.log
legal set (15 + both unit files):
================= 1 failed, 559 passed, 11 warnings in 28.52s =================
[hermeticity] sentinel checked 560 test(s)
[netguard] blocked 0 attempt(s) from 0 node(s)
FAILED tests/test_s81_12_legal_v3.py::test_h1_merge_window_recorded - Asserti...
[pyt] tag=s12a-corr-legalset start=2026-11-12 03:32:32 end=2026-11-12 03:33:01 elapsed=30s bound=1200s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\dc5dcae5-8753-4884-a665-dd310b93b8f5\scratchpad\S81-12_arfix\corr\corr-legalset.log
CI-order set RB2-7 (10), 19 files sorted, one process:
================ 1 failed, 1176 passed, 13 warnings in 57.88s =================
[hermeticity] sentinel checked 1177 test(s)
[netguard] blocked 24 attempt(s) from 2 node(s)
[netguard]   tests/test_s81_s04_spend_breaker.py::test_r42_on_with_headroom_accounts_every_create [sentinel] socket.create_connection neutralized.supabase.invalid:443
[netguard]   tests/test_s81_s04_spend_breaker.py::test_p08_on_with_headroom_changes_no_response_field [sentinel] socket.create_connection neutralized.supabase.invalid:443
FAILED tests/test_s81_12_legal_v3.py::test_h1_merge_window_recorded - Asserti...
[pyt] tag=s12a-corr-ciorder start=2026-11-12 03:33:09 end=2026-11-12 03:34:09 elapsed=60s bound=1200s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\dc5dcae5-8753-4884-a665-dd310b93b8f5\scratchpad\S81-12_arfix\corr\corr-ciorder.log
H1 the only red in every gate.

## (4) Comm set (RB2-8)
- derivation: derive_comm.py of the merge round re-run at HEAD with ARFIX reference terms added (ar.json, en.json, i18n, aiConsent, landing/ar, landing, privacy_anon, getmyez.com/bot): 191 derived + tests/test_s71_u13_compare_auth_required.py (kept from the 172 of record) = 192 members, set sha256 4e9a695d...; 20 additions over the 172 (all class ref:*, a superset incl. false positives such as '*golden.json' matching 'en.json'); none removed; no hook file; the eight CLAUDE.md readers by the import graph are members.
- BASE: every member present at 6b909e0a (190; the two s81_12 files absent) run in a detached scratch worktree of 6b909e0a (S81-12_arfix/base, no junction; removed, verified gone): NO LC-6 reuse. Record stored: <scratch>/harness/base_records/6b909e0a92067d6b3562eee325e4956c116441f7/4e9a695d6197....(files, txt, pyt.log).
- every chunk list written LF and byte-checked (no CR, entries == list; g.sh refuses a CR and checks each path exists: missing=0 everywhere); 45 s pause + re-probe after each chunk; waits of 848 s (base chunk 07) and 344 s (head chunk 00) for a foreign s07r- mutation pytest; nothing killed.
base chunks 8 head chunks 8
[pyt] tag=s12a-comm-base-bchunk_00 start=2026-11-12 03:36:16 end=2026-11-12 03:36:50 elapsed=34s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\dc5dcae5-8753-4884-a665-dd310b93b8f5\scratchpad\S81-12_arfix\corr\comm-base-bchunk_00.log
[pyt] tag=s12a-comm-base-bchunk_01 start=2026-11-12 03:37:42 end=2026-11-12 03:40:06 elapsed=143s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\dc5dcae5-8753-4884-a665-dd310b93b8f5\scratchpad\S81-12_arfix\corr\comm-base-bchunk_01.log
[pyt] tag=s12a-comm-base-bchunk_02 start=2026-11-12 03:41:10 end=2026-11-12 03:41:46 elapsed=36s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\dc5dcae5-8753-4884-a665-dd310b93b8f5\scratchpad\S81-12_arfix\corr\comm-base-bchunk_02.log
[pyt] tag=s12a-comm-base-bchunk_03 start=2026-11-12 03:42:44 end=2026-11-12 03:44:34 elapsed=110s bound=1200s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\dc5dcae5-8753-4884-a665-dd310b93b8f5\scratchpad\S81-12_arfix\corr\comm-base-bchunk_03.log
[pyt] tag=s12a-comm-base-bchunk_04 start=2026-11-12 03:45:45 end=2026-11-12 03:47:52 elapsed=127s bound=1200s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\dc5dcae5-8753-4884-a665-dd310b93b8f5\scratchpad\S81-12_arfix\corr\comm-base-bchunk_04.log
[pyt] tag=s12a-comm-base-bchunk_05 start=2026-11-12 03:48:44 end=2026-11-12 03:50:36 elapsed=112s bound=1200s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\dc5dcae5-8753-4884-a665-dd310b93b8f5\scratchpad\S81-12_arfix\corr\comm-base-bchunk_05.log
[pyt] tag=s12a-comm-base-bchunk_06 start=2026-11-12 03:51:28 end=2026-11-12 03:53:03 elapsed=95s bound=1200s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\dc5dcae5-8753-4884-a665-dd310b93b8f5\scratchpad\S81-12_arfix\corr\comm-base-bchunk_06.log
[pyt] tag=s12a-comm-base-bchunk_07 start=2026-11-12 04:08:05 end=2026-11-12 04:08:45 elapsed=40s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\dc5dcae5-8753-4884-a665-dd310b93b8f5\scratchpad\S81-12_arfix\corr\comm-base-bchunk_07.log
comm-base-bchunk_00.out: 912 passed, 3 skipped, 21 warnings in 32.10s
comm-base-bchunk_01.out: 2471 passed, 1 skipped, 18 warnings in 141.30s (0:02:21)
comm-base-bchunk_02.out: 686 passed, 4 deselected, 11 warnings in 34.82s
comm-base-bchunk_03.out: 997 passed, 26 skipped, 2 deselected, 1 xfailed, 13 warnings, 2 errors in 106.64s (0:01:46)
comm-base-bchunk_04.out: 5 failed, 2418 passed, 261 warnings in 113.37s (0:01:53)
comm-base-bchunk_05.out: 7 failed, 3012 passed, 63 warnings in 109.18s (0:01:49)
comm-base-bchunk_06.out: 4 failed, 1852 passed, 1 xfailed, 45 warnings in 92.46s (0:01:32)
comm-base-bchunk_07.out: 856 passed, 1 skipped, 35 xfailed, 15 warnings in 38.53s
[pyt] tag=s12a-comm-head-hchunk_00 start=2026-11-12 04:15:19 end=2026-11-12 04:16:14 elapsed=54s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\dc5dcae5-8753-4884-a665-dd310b93b8f5\scratchpad\S81-12_arfix\corr\comm-head-hchunk_00.log
[pyt] tag=s12a-comm-head-hchunk_01 start=2026-11-12 04:17:06 end=2026-11-12 04:19:06 elapsed=120s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\dc5dcae5-8753-4884-a665-dd310b93b8f5\scratchpad\S81-12_arfix\corr\comm-head-hchunk_01.log
[pyt] tag=s12a-comm-head-hchunk_02 start=2026-11-12 04:20:33 end=2026-11-12 04:21:21 elapsed=48s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\dc5dcae5-8753-4884-a665-dd310b93b8f5\scratchpad\S81-12_arfix\corr\comm-head-hchunk_02.log
[pyt] tag=s12a-comm-head-hchunk_03 start=2026-11-12 04:23:32 end=2026-11-12 04:25:00 elapsed=88s bound=1200s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\dc5dcae5-8753-4884-a665-dd310b93b8f5\scratchpad\S81-12_arfix\corr\comm-head-hchunk_03.log
[pyt] tag=s12a-comm-head-hchunk_04 start=2026-11-12 04:27:01 end=2026-11-12 04:28:21 elapsed=80s bound=1200s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\dc5dcae5-8753-4884-a665-dd310b93b8f5\scratchpad\S81-12_arfix\corr\comm-head-hchunk_04.log
[pyt] tag=s12a-comm-head-hchunk_05 start=2026-11-12 04:29:47 end=2026-11-12 04:31:29 elapsed=102s bound=1200s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\dc5dcae5-8753-4884-a665-dd310b93b8f5\scratchpad\S81-12_arfix\corr\comm-head-hchunk_05.log
[pyt] tag=s12a-comm-head-hchunk_06 start=2026-11-12 04:34:02 end=2026-11-12 04:35:48 elapsed=105s bound=1200s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\dc5dcae5-8753-4884-a665-dd310b93b8f5\scratchpad\S81-12_arfix\corr\comm-head-hchunk_06.log
[pyt] tag=s12a-comm-head-hchunk_07 start=2026-11-12 04:37:49 end=2026-11-12 04:38:34 elapsed=45s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\dc5dcae5-8753-4884-a665-dd310b93b8f5\scratchpad\S81-12_arfix\corr\comm-head-hchunk_07.log
comm-head-hchunk_00.out: 915 passed, 21 warnings in 52.32s
comm-head-hchunk_01.out: 2471 passed, 1 skipped, 18 warnings in 118.33s (0:01:58)
comm-head-hchunk_02.out: 687 passed, 4 deselected, 11 warnings in 47.24s
comm-head-hchunk_03.out: 997 passed, 26 skipped, 2 deselected, 1 xfailed, 13 warnings, 2 errors in 86.32s (0:01:26)
comm-head-hchunk_04.out: 1 failed, 2424 passed, 260 warnings in 76.56s (0:01:16)
comm-head-hchunk_05.out: 12 failed, 2891 passed, 64 warnings in 99.73s (0:01:39)
comm-head-hchunk_06.out: 4 failed, 1797 passed, 1 xfailed, 47 warnings in 103.22s (0:01:43)
comm-head-hchunk_07.out: 1090 passed, 1 skipped, 35 xfailed, 16 warnings in 43.11s
BASE FAILED/ERROR (18):
tests/test_prompt_truth.py::test_render_digests_match_base_except_the_fence
tests/test_prompt_truth.py::test_truth_on_prefix_static_and_cacheable
tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[OFF]
tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[empty]
tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[false]
tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[pad0]
tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[unset]
tests/test_s81_s10_fragrance_gate.py::test_r06_production_lexicon_content
tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[cron_feed_walker]
tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[cron_pdp_discovery]
tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[kb_seed_common]
tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[seed_kb_batch]
tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[seed_kb_brands_wikidata]
tests/test_s81_s18b_store_label.py::test_r2_table_shape
tests/test_s81_s22_compare_runs.py::test_b02_one_transaction_ascii_lf
tests/test_s81_s22_judge.py::test_j01_script_exists_and_off_first
tests/test_s81_s24_auth_throttle.py::test_p83_red_file_setenv_hygiene
tests/test_s81_s24_auth_throttle.py::test_r92_hygiene
HEAD FAILED/ERROR (19):
tests/test_prompt_truth.py::test_render_digests_match_base_except_the_fence
tests/test_prompt_truth.py::test_truth_on_prefix_static_and_cacheable
tests/test_s81_12_legal_v3.py::test_h1_merge_window_recorded
tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[OFF]
tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[empty]
tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[false]
tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[pad0]
tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[unset]
tests/test_s81_s10_fragrance_gate.py::test_r06_production_lexicon_content
tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[cron_feed_walker]
tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[cron_pdp_discovery]
tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[kb_seed_common]
tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[seed_kb_batch]
tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[seed_kb_brands_wikidata]
tests/test_s81_s18b_store_label.py::test_r2_table_shape
tests/test_s81_s22_compare_runs.py::test_b02_one_transaction_ascii_lf
tests/test_s81_s22_judge.py::test_j01_script_exists_and_off_first
tests/test_s81_s24_auth_throttle.py::test_p83_red_file_setenv_hygiene
tests/test_s81_s24_auth_throttle.py::test_r92_hygiene
comm -13 (branch-only-new) (1):
tests/test_s81_12_legal_v3.py::test_h1_merge_window_recorded
comm -23 (base-only) (0):

- totals: base 13,204 passed; head 13,272 passed (+64 from the two unit files, +3 base-skipped nodes passing in head chunk 00, +1 parametrised node); the 18 shared reds are environmental on this box (test_prompt_truth cold tiktoken; CRLF-working-copy hygiene / golden rows) and identical at both sides.
- RESULT: comm -13 = EXACTLY tests/test_s81_12_legal_v3.py::test_h1_merge_window_recorded; comm -23 empty.

## (5) PR body (<notes>/PR_BODY.md, 25,454 B <= 25,600, sha256 d07616cb...; non-ASCII only line 164 = the attribution line, which ends the body) checked against the bytes
Verified: HEAD / parent / commit list; 45 files, ARFIX 14 of them none new; the three cmp shas; landing 6 / 1 lines; fence 77ac6348 -> adfc77d2 version 3; seven sanctioned frozen amendments EK1/ECF1/EK2/EK3/EK4/EK5/EK6; 27 gate nodes; RED 38 = 37 + H1; legal set 559 + H1 (re-measured); G-k..G-o red at dd9738f7 on AssertionError only (red.log: six AssertionError lines, H1 + the five).
CORRECTIONS for the orchestrator (no edit made by this agent):
 C1 (line 12) 'CLASS L five literals of old spans' -> 'CLASS L six literals in five places' (CARVE_AR; legal_s78.json s5_carveout_ar and tos_s8_openai_ar; legal_d3c_u8.json fix2_ar.s5_carveout_head; aiConsentV2.s75 AR_SENTENCE and AR_SECTION2), as the table at line 86 lists.
 C2 (line 13) 'Comm set and mutants: the correctness re-verifier's (AF-9)' -> fill: mutants 10 / 10 KILLED (reverse J1, T1, P1-s4, J2, P3, P5, P2-first; the slash re-added; CLASS T prefill revert; one EN byte); CI-order set (19 files) 1,176 passed + H1; comm set 192 members (set 4e9a695d...), base all-run at 6b909e0a and stored, 8 + 8 chunks, comm -13 = H1 only.
 C3 (line 13) 'CLAUDE.md readers (6 files) 510 passed': the import-graph reader set is 8 files (+ tests/test_s81_s23b_scrapedo_super_retire.py, tests/test_scoring_rubric_truth.py, as the merge round ran 609 + 1 xfailed); all 8 are green inside the comm set at HEAD: state '8 files, green in the comm set' or keep '6 files' with that note.
 C4 (line 17) the merge-round 'comm set NOT MEASURED locally' stays history, but this round now has a measured comm set (C2): add 'measured at the ARFIX head'.

## Findings
blocking: none. major: none.
minor (stated limits by LC-4):
 m1 PR body C1 / C3 wording (counts of literals and readers): documentation only.
 m2 the CLASS T jest fence was not mutated (no junction in a scratch worktree); its digest is recomputed by the recipe in python and equals the pinned value; the fix agent's jest subset ran it green.
 m3 origin/main read from the local ref only (no git fetch: no network grant); the orchestrator re-checks at AF-10.
Deviations: none (one pytest at a time; every run probe-gated; no foreign process touched; both scratch worktrees removed and verified gone).
NOT MEASURED: none of the assigned gates. Hook test files tests/test_precommit_hook*.py not run (no .githooks change).
