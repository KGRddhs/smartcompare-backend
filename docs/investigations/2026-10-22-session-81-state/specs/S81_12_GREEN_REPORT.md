# S81-12 LEGAL-V3 GREEN report (Opus 5.5 GREEN agent, 2026-10-29 04:05-05:35)

Unit S81-12 LEGAL-V3 (docs-legal, NO flag, HELD PR). Worktree C:/Users/SynAckITPC/Documents/AI/sc-s81-s12, branch feature/s81-legal-v3 created from the detached base a8f01379b05c0079c72a74418bdbce2f4acfbe7d. HEAD 3c4a198dca34745ad105aef404f381f13a393f58 (ONE commit, 41 files, through the pre-commit hook; the frozen RED .py file is staged but NOT committed: Q2). Notes: <scratchpad>/S81-12_green/ (notes.md, logs, apply_docs.py, apply_tests.py, apply_claude_md.py, texts_v3.py, build_comm_head.py, comm_files_head.txt, comm_reasons_head.tsv, comm_base_failed.txt, comm_head_failed.txt, files_changed.json); byte copies + SHA256SUMS.txt in <scratchpad>/S81-12_green_before/. This report and PR_BODY.md were written through the shell (make_reports.py run by python).

RED files re-hashed at start and end: tests/test_s81_12_legal_v3.py 94ef61a526ccfc10f15c51b61b82fa11755469e8e332bb030c705111e4dcd6b5, SmartCompareApp/__tests__/s81_12/legalV3.s81_12.test.ts 2af065a2bc230881760d54766312d6a87d24ad5161f6284d477f210b322b6a75 (unchanged).

## Runs
- gate0: [pyt] tag=s12green-gate0 start=2026-10-29 04:07:42 end=2026-10-29 04:08:00 elapsed=19s bound=600s status=FAIL rc=1 (30 failed, all AssertionError / 8 passed; [hermeticity] sentinel checked 38 test(s); [netguard] blocked 0 attempt(s) from 0 node(s))
- unit1: [pyt] tag=s12green-unit1 start=2026-10-29 04:35:07 end=2026-10-29 04:35:11 elapsed=4s bound=600s status=FAIL rc=1 (2 failed: R9 before the PUBLIC_NAME_IDS pin edits, H1 by design / 36 passed)
- legal_pre: [pyt] tag=s12green-legal16-pre start=2026-10-29 04:35:23 end=2026-10-29 04:36:02 elapsed=39s bound=1200s status=FAIL rc=1 (66 failed / 466 passed: the prototype's 63 E-rows + T7 schema + R9 (both the PUBLIC_NAME_IDS edit) + H1; [hermeticity] sentinel checked 532 test(s); [netguard] blocked 0 attempt(s) from 0 node(s))
- legal_a: [pyt] tag=s12green-legal16-a start=2026-10-29 04:43:41 end=2026-10-29 04:45:07 elapsed=86s bound=1200s status=FAIL rc=1 (1 failed = H1 by design / 532 passed; [hermeticity] sentinel checked 533 test(s); [netguard] blocked 0 attempt(s) from 0 node(s))
- h1window: [pyt] tag=s12green-h1window start=2026-10-29 05:12:38 end=2026-10-29 05:13:01 elapsed=23s bound=600s status=OK rc=0 (H1 + H1b 2 passed with a TEMPORARY tests/fixtures/legal_v3_window.json = 2026-10-29, removed after the run, absent from the commit)
- ci: [pyt] tag=s12green-ci-order start=2026-10-29 05:13:31 end=2026-10-29 05:17:08 elapsed=217s bound=1200s status=FAIL rc=1 (1 failed = H1 / 1157 passed; 18 files in sorted order: the 15-file legal set + the unit file + test_s81_s06_anthropic_router + test_s81_s04_spend_breaker; [hermeticity] sentinel checked 1158 test(s); [netguard] blocked 24 attempt(s) from 2 node(s))
- unit_final: [pyt] tag=s12green-unit-final start=2026-10-29 05:26:36 end=2026-10-29 05:26:58 elapsed=23s bound=600s status=FAIL rc=1 (1 failed = H1 by design / 37 passed; on the committed bytes; [hermeticity] sentinel checked 38 test(s); [netguard] blocked 0 attempt(s) from 0 node(s))
- [jest] tag=s12green-jest-subset start=04:46:12 end=04:46:53 rc=1 (by path: the client RED file + the five jest E-row files; 62 passed / 2 failed = the two C2 rows of the frozen client RED file; node v24.11.1, jest 29.7.0, @babel/core 7.29.0, junction verified: LinkType Junction -> the clone's SmartCompareApp/node_modules)
- [jest] tag=s12green-jest-full start=04:48:27 end=04:50:15 rc=1 (FULL suite once, no -u: Test Suites 2 failed, 3 skipped, 375 passed; Tests 6 failed, 13 skipped, 13 todo, 3701 passed; Snapshots 42 passed, none written; failed = the 4 accepted nativeBundle.w37 drift nodes (d5, k2, k4, k5) + the 2 C2 rows)
- [tsc] tag=s12green-tsc start=04:47:41 end=04:48:12 rc=0 (node node_modules/typescript/bin/tsc --noEmit, TypeScript 5.9.3)
- comm base-00: [pyt] tag=s12green-base-00 start=2026-10-29 04:54:07 end=2026-10-29 04:54:35 elapsed=28s bound=1200s status=OK rc=0 (1274 passed; [netguard] blocked 3 attempt(s) from 1 node(s); [hermeticity] sentinel checked 1274 test(s))
- comm base-01: [pyt] tag=s12green-base-01 start=2026-10-29 04:54:43 end=2026-10-29 04:56:33 elapsed=109s bound=1200s status=OK rc=0 (2202 passed, 4 deselected; [netguard] blocked 56 attempt(s) from 33 node(s); [hermeticity] sentinel checked 2202 test(s))
- comm base-02: [pyt] tag=s12green-base-02 start=2026-10-29 04:56:40 end=2026-10-29 04:58:29 elapsed=109s bound=1200s status=FAIL rc=1 (1342 passed, 23 skipped, 2 deselected, 1 xfailed, 2 errors (tests/test_prompt_truth.py cold tiktoken x2); [netguard] blocked 2 attempt(s) from 2 node(s); [hermeticity] sentinel checked 1345 test(s))
- comm base-03: [pyt] tag=s12green-base-03 start=2026-10-29 04:58:36 end=2026-10-29 05:02:15 elapsed=219s bound=1200s status=FAIL rc=1 (30 failed (the 30 RED rows) / 3827 passed, 1 skipped; [netguard] blocked 63 attempt(s) from 31 node(s); [hermeticity] sentinel checked 3858 test(s))
- comm base-04: [pyt] tag=s12green-base-04 start=2026-10-29 05:02:26 end=2026-10-29 05:02:40 elapsed=14s bound=1200s status=OK rc=0 (474 passed, 35 xfailed; [netguard] blocked 0 attempt(s) from 0 node(s); [hermeticity] sentinel checked 509 test(s))
- comm head-00: [pyt] tag=s12green-head-00 start=2026-10-29 05:02:48 end=2026-10-29 05:03:21 elapsed=32s bound=1200s status=OK rc=0 (1274 passed; [netguard] blocked 3 attempt(s) from 1 node(s); [hermeticity] sentinel checked 1274 test(s))
- comm head-01: [pyt] tag=s12green-head-01 start=2026-10-29 05:03:31 end=2026-10-29 05:06:22 elapsed=171s bound=1200s status=OK rc=0 (2203 passed, 4 deselected (+1 = the new u8 control node); [netguard] blocked 53 attempt(s) from 32 node(s); [hermeticity] sentinel checked 2203 test(s))
- comm head-02: [pyt] tag=s12green-head-02 start=2026-10-29 05:06:30 end=2026-10-29 05:08:17 elapsed=107s bound=1200s status=FAIL rc=1 (1342 passed, 23 skipped, 2 deselected, 1 xfailed, 2 errors (the same two cold-tiktoken ERRORs); [netguard] blocked 2 attempt(s) from 2 node(s); [hermeticity] sentinel checked 1345 test(s))
- comm head-03: [pyt] tag=s12green-head-03 start=2026-10-29 05:08:24 end=2026-10-29 05:10:37 elapsed=133s bound=1200s status=FAIL rc=1 (1 failed (H1, by design) / 3856 passed, 1 skipped; [netguard] blocked 63 attempt(s) from 31 node(s); [hermeticity] sentinel checked 3858 test(s))
- comm head-04: [pyt] tag=s12green-head-04 start=2026-10-29 05:10:43 end=2026-10-29 05:10:54 elapsed=11s bound=1200s status=OK rc=0 (474 passed, 35 xfailed; [netguard] blocked 0 attempt(s) from 0 node(s); [hermeticity] sentinel checked 509 test(s))

## Counts
- unit file (38 nodes): 37 green / 1 red by design (H1): 29 of the 30 base-RED nodes turned green (H1 stays red), the 8 PIN nodes stay green.
- legal set (15 files + unit): 532 passed / 1 failed (H1); +1 node vs base = the new u8 pin test_t8_history_allow_list_is_exact.
- client: RED file C1, C3, C4, C5 green; C2 (2 nodes) red = wrong RED row (Q1). Full jest: 3701 passed, 6 failed (4 accepted nativeBundle.w37 + 2 C2), 42 snapshots passed (none written). tsc rc 0.
- comm: 106 files; branch-only-new EMPTY.
- mutants: none run by GREEN (the RED's 23/23 KILLED on the prototype; the adversaries re-run them on these bytes).

## Files (final sha256)
- CLAUDE.md: +4 -2; before 33196b9de6132d2e69787584b92267bada2284b987b70804fcc649f7085e4e30; after 6b8c5830b8b2a2720a7889479c5b55ef8915e32138cf4f668d82867d9ca9b8d8
- SmartCompareApp/__tests__/consent/aiConsentV2.s75.test.ts: +24 -13; before 432c15bd4207f20efa80fd490f7b6ac3d37f5e6af0ddff72c806f0191107c12b; after c00852091e263e9deb336357e813a4c85583aa14301b2d77e8e2d900fd31fead
- SmartCompareApp/__tests__/consent/aiConsentVersion.s69.test.ts: +8 -3; before 6360330bad846f6b8b28a8bbef8fddd924de7d91eeaa54d06c75d5cd38f6ee8b; after 9f26d5fbd4eddb845ea130c767106aa81fb9bfc6ddddb6fafd7f582f02ae0b11
- SmartCompareApp/__tests__/consent/aiProcessingConsent.s69.test.tsx: +4 -0; before e6de4c5a3172458bf5f7319e28cbcddc31f20528bc91c1d823109379297224f5; after 9a2bfa018dcf56e9c6ce1f43c1752f8c62875a5813358ff3244acf45488cc806
- SmartCompareApp/__tests__/landing.brand.s69.test.ts: +3 -2; before c9a6a61d592dd7d32985e903b8f1cc85339f30b046d889001e79dacc5b9cff1f; after d2bd1443f09d1f68f0000ef008670978d003f11898e058e330c010b0840b39fc
- SmartCompareApp/__tests__/onboarding/step05Trust.s69.test.tsx: +6 -2; before b4e2863d76f71fd1618dbeac1cbecd563c15bbbeb59f5c0f684c92d662f57d21; after 0611f1e61e2715c8806d8a824cf28ffa4a0dee0b446a3353662bb6942448fb4a
- SmartCompareApp/__tests__/s81_12/legalV3.s81_12.test.ts: +164 -0; before 2af065a2bc230881760d54766312d6a87d24ad5161f6284d477f210b322b6a75; after 2af065a2bc230881760d54766312d6a87d24ad5161f6284d477f210b322b6a75
- SmartCompareApp/__tests__/setup.ts: +1 -1; before 9579b4b5d6d8e20418d0678be3c5134dd38b3944a1769979f0ba4845f3d1ef2e; after 9d829b38a169f71f51fe0e1251555d2e6edc0f0067809ab8a400cd1e5b34616e
- SmartCompareApp/src/components/AiConsentSheet.tsx: +3 -3; before af8bc8ee557bf9ab64f6790e4e82cc67a0e0d8af76b74b48565567ed059ed65c; after 31d15c3f325aa50cdbb9cf89fccb93be565fd11dae7f4f06022d6dee1b78e118
- SmartCompareApp/src/i18n/ar.json: +3 -3; before 7aea08684554f15371ebb2d46eccfbfa44c1a83d66b98c1ab60d9567893fcbbe; after ef8ef3a952f7a57b419049af956712b2b7620f3135da0bbd2ea0adebf5018ebf
- SmartCompareApp/src/i18n/en.json: +3 -3; before 5b42c7a3542659810087a32b38e5534ed58cb2d3cf9124b4f31ce2189528ffb1; after d049045d84ae76775f6d81f5aeb98ef7caf5459ec7112d7463688c49d4523fe8
- SmartCompareApp/src/screens/onboarding/Step05Trust.tsx: +6 -5; before 490127e5a0a8d5bd9350bcb2a9365aa8f37fbeb0e5fb988ab0a610536b995f7b; after 008668f010d26f54c1f13d330d8b1c325807b562b0a46f2bd1fce8f6fc405e31
- SmartCompareApp/src/services/aiConsent.ts: +10 -6; before a7dc249cb1606d271e7cd01e48a272df2b6c7b7bb91cd366b599d8ee8817b5d1; after 009b7e62c97c71b38f59570a2935474be5391e6687097149c1c7f88fb8984d14
- SmartCompareApp/src/services/consent.ts: +1 -1; before 9e9ce36192409207240a1516b5c34eec136ff54a272698cde28337fa6efdb51c; after c3cdbe512a2a525feb1e6763c325575dc7c04afb6cb03ba266b863d651e93612
- app/legal/privacy_policy.md: +28 -16; before 82f1d7b93dc3eeef5911bb61d4d41726f3536faffb25746a7699f96a4341589d; after 10158a061c6b097338a742327a4a22a44a400c7af703557ba6b26d55e7b4655c
- app/legal/privacy_policy_ar.md: +28 -16; before 2f853902968119ff2f2988518d6cd6a657107e5a271e2c481751021708bf3485; after bc03944d5d9bf317fed99adb873ce1aea7898b938e02f86346da02bcf9f71fcc
- app/legal/processors.json: +2 -2; before 79b52fc61ebaad69dc4aeba871882285f4a19217aa1ca410819ad3400e55904b; after 838ebf2a074f827e98112f1b4bf69aa2e256eda74c662156db0cc99f8ff193dc
- app/legal/terms_of_service.md: +4 -2; before c56d2b5d388fe8d8da2f6427520f8c233ecf0a7060f8f0f126fc198f99588733; after 77953e637d986af01e40d9428319f828e8424aa0325e453fcdb80cc071b9f863
- app/legal/terms_of_service_ar.md: +4 -2; before b3880b9d110a3408c0db53429b8020b8f937f6890263fc2171b43737818ac383; after e7a61482db7f598c1c38215e5bf94df08b849f70c96e75a4678dbf5528b83d0a
- app/services/consent_service.py: +1 -1; before a497bcf3146c86224d6cad2fb4c9a16c212fce6d256d016127ac1cb1b64ca947; after 62c61a456cf7de067abe63ddf360b539f5d01e2207c12472d7d8a8c778b345a8
- landing/ar/privacy.html: +22 -16; before 2181903c212fdd3a245cb0d3bc459432c3e159d14c91756e93b0feeef89fc94d; after f22da2e6632f212a5c8b98265e631175c81313970ce9664518bc2e93518d6f9b
- landing/ar/terms.html: +3 -2; before c764ff63ba4bb38eadd33a56fbffb23ed5ef9f2555c401155930d5b5be875b8c; after c4b9c44b9426bd56093fa8edf5bd8b114f27aa23959aab823a178dab545a7458
- landing/privacy.html: +22 -16; before 0a943cc37939919ed87ba0940a9c19efce0e76e6289e21bab64274c4dc04c482; after fe0f005f7c367dfcd82207945af1b6f51defaa89b733ef448c7eb88892fde229
- landing/terms.html: +3 -2; before f47834b19a14b0aef2f5be1725b87f9ea845d65164773487c41648208b9b76eb; after db3f1f87a520ff07033c45525c994f65dd196fa2388427dfc45fcd9d2dc52a1e
- scripts/fill_in_legal.py: +2 -0; before 81696741f34df81c92044fbd24daa9308d61d25fda997ad47301eaa92afb7019; after 9b157585917a74bec244daaf2c644cd346199bad1e178c506bce6def28da73cc
- scripts/legal_variants_u8.json: +75 -31; before 3d4cb841550b95247116998a4ff974e454406a4b904d3e04927c40864b03819e; after 24b9894c9a9a9cd1d0a86f90e035dd4bf760c3f6ce04018e49c781dd46ea071e
- tests/fixtures/legal_d3c_u8.json: +14 -6; before 44123f3cf5480880da13c0ecc0e8266672399f797c9b345344898a7e9a7c46b6; after ff64cba63f8c012493e3d04e905bce6c59e81d561c8426602c98c90fe4e02f7d
- tests/fixtures/legal_disclosure_s77.json: +16 -6; before 2d448d321f3b94c0865a53ece29e38772de6d354482a6b9ce2392d292c993827; after bc131d252b7457ecd0004a939df99e8d7aa1657313085b11a7058e624bf24585
- tests/fixtures/legal_fill_in_u8.json: +15 -4; before f4b8b05601582e526e0b78cb8abba501e4c9ca3a2915fccaba57b5edb0a9a96b; after 181dc71bff2d299e13c342d30f5b55b26a3aa3b6d3917b22e511d1b5560aee76
- tests/fixtures/legal_prefill_u8/privacy_policy.md: +30 -18; before 2f37571dc273b938cc44558e24f867682562a3372b8e75e42f60066c7f70e606; after 1233ee53b441307c404f4ad636721b4bbdb5f37cc92d0fe0d02556fede335eb4
- tests/fixtures/legal_prefill_u8/privacy_policy_ar.md: +30 -18; before 270af6a1861dca4d9ed4a0537c4f5a331594c689fa203d99debcfb839945ac38; after bb7697c2de672cb51405a821a550981771b0361d0c46b285d4d420635875c91d
- tests/fixtures/legal_prefill_u8/terms_of_service.md: +4 -2; before 0305b7d450114f25753071cc2199466fa16c6c5abf9e091a5dffee28cf24f227; after f24c984f56d9ebe3b5de5d5719a7c365bcba1a3fda4ba44e96337e26287eba8b
- tests/fixtures/legal_prefill_u8/terms_of_service_ar.md: +4 -2; before 10fd2a640cf09c07b7466497661e845c693d4f7467a7da10bc486f60d851b5d8; after fefa04e0277476e6afd687ace419169cf5296e575804ef3629e33a2ff7acd361
- tests/fixtures/legal_s78.json: +5 -5; before 61a68c6ec05f8fa8efded8259e4b3ae22b3e17892af96f356943241a177c5f92; after a363512a01b8f0c434169ad468a784bf859e8857d8d6fa5366a707f19bbe05b8
- tests/test_consent_capture_w3_16.py: +1 -1; before 3423b72838b18ab2b714014a9965d9add5d42a86643cc3764254805175ab983a; after b2142b511112501ef268dea99b9da7573984feb7683588da14fbcec79a86fa20
- tests/test_legal_disclosure_s77.py: +70 -37; before c4bc8c47a1e47dc4ff70a86b9d10aa272f0f9bf8127f68375ded583caca59d64; after 242461809c27038031dfac34d1ea4b086bdf2d210712596913aeafd09ec62adb
- tests/test_legal_docs_u8.py: +81 -5; before 9d77e30d497a56480d1554f41229c2e54e7d131054d9bf4b8248d32b8ec1e7f6; after ef47a313021f95f2597738ece9bf7f7affd6729711ee7b71b7be734cbc7a3148
- tests/test_legal_docs_u8_d3c.py: +107 -95; before 3700c6cbc2973fcf0925a232aedff7a8d18159ecacc36ed2f535b37cbaf1f459; after ab91775ab55b1e0ac9c7fc2c308a1bf0359e8b489704021984bc4212727e48d2
- tests/test_legal_docs_u8_polish.py: +20 -9; before bf08af2c1dbef9968b71122824955954501c38b198e02b29d98fe9509ed4f81c; after 45893b22c22b5161333a63f05fb71b255dfdcf50aea62c4bdd0e48051763bdb0
- tests/test_legal_s78.py: +20 -7; before 0f5868f9d40e2b7b8bc19fbde97927b96dbe5d2becd8dae68f76e6b05f9b9c1f; after 87152f5565ddc950ae0154fd5d6836e0caff69ef936764913d68977a140bb8d8
- tests/test_s81_s06_anthropic_router.py: +4 -2; before 75342e9dc645ee28f98d5aff9bf0b92863cd8285e8899a71d74eb519a01f577c; after e17e8fd8ed9f2c143bdd52d318d4316009e5a4eba3b066494e428d3ed1f6b0d9
- tests/test_s81_12_legal_v3.py (staged, NOT committed: gitleaks): +1310 -0; before (new file); after 94ef61a526ccfc10f15c51b61b82fa11755469e8e332bb030c705111e4dcd6b5

## Deviations
- D1: the frozen RED .py file is not in the commit (hook gitleaks refusal on its line 211; Q2); everything else is ONE commit.
- D2: the client RED row C2 stays red (wrong row: the record API takes the user id; Q1). No production API change made.
- D3: an extra E-row outside GC-8's list: tests/test_s81_s06_anthropic_router.py::test_r36_manifest_row (public_name False -> True, R-S12-11; Q3).
- D4: T8 EN amended beside T8 AR per R-S12-4, plus a NEW pin node test_t8_history_allow_list_is_exact (Q4).
- D5: the commit trailer names this agent's own model (Co-Authored-By: Claude Opus 5.5) per the common brief and the session attribution, not the 'Claude Fable 5.1' text of the task prompt (an agent never claims another model).
- D6: the kb_feedback bullet is its own clause KB_FEEDBACK_CLAUSE selected by COMPARE_RUN_RETENTION (GC-2: one key gates both; no new retention key); its null data key joins the placeholders (11 new keys in all).
- D7: s2 and Terms s8 carry short UNDATED past-tense programme sentences beside the ONE dated history sentence of privacy s4 (R2 counts only s4); the T8 allow-list covers the dated s4 sentence.
- D8: 'git worktree prune' ran once after the scratch worktree removal (it only drops administrative entries of worktrees whose directories are gone).
- D9: tests that read the dates (D2, R11, the u8 allow-list, d3c (n)) read AI_SWITCH_DATE / _AR from the fill-in data, so the re-date recipe needs no new literal; the test literals of TERMS_VERSION stay the recipe's own (tests/test_consent_capture_w3_16.py).

## Open questions
- Q1 (client RED row C2, 2 nodes, wrong row): the frozen SmartCompareApp/__tests__/s81_12/legalV3.s81_12.test.ts C2 calls aiConsent.hasCurrentAiConsent() and aiConsent.recordAiConsent() with NO user id, but on main both take the user id explicitly (src/services/aiConsent.ts: hasCurrentAiConsent(userId: string | null), recordAiConsent(userId: string | null, now?)); with no argument they read 'no user' (false / nothing persisted), so C2 cannot pass without changing the record API (S81-08's lane, R-S08-3). The contract C2 meant (a v2 record no longer counts; Agree writes 3; a v3 record counts) is GREEN in aiConsentV2.s75 V2a-V2c through ensureAiConsent (E3). Ruling needed: re-write C2 with the user id (e.g. hasCurrentAiConsent(userId) / ensureAiConsent(ask)), or accept a default-argument API change (not made here). tsc passes (the RED file loads the module with require, so the calls are untyped).
- Q2 (the frozen RED .py file is not committed): the hook's gitleaks step (rule generic-api-key) refuses tests/test_s81_12_legal_v3.py:211, BASE_I18N_KEYS_SHA256 = "9ff8684f..." "...14273" (a hex literal, split, under a KEY-named variable). The hook passes --ignore-gitleaks-allow and reads .gitleaks.toml from HEAD (a .gitleaksignore is refused), so only an edit of that frozen line clears it, e.g. rename the constant to a name without key/token/secret (BASE_I18N_NAMESET_SHA256, 3 occurrences incl. the P3 docstring) or wrap the literal in parentheses. The file is byte-identical (94ef61a5...d6b5), staged, uncommitted. Ruling needed before the PR.
- Q3 (an E-row outside GC-8's list): tests/test_s81_s06_anthropic_router.py::test_r36_manifest_row pinned S81-06's interim public_name False; R-S12-11 assigns the flip to this unit and R9 requires True, so the pin moved (one assertion + a dated docstring sentence). Confirm.
- Q4 (T8 EN): beyond GC-8's T8-AR, R-S12-4 asks the EN pattern amended too: D3_FORBIDDEN_EN['A'] now reads 'data[- ]sharing program' (case-insensitive), with the same exact-sentence allow-list, and a new pin node test_t8_history_allow_list_is_exact carries the positive control and the date mutant. Confirm.
- Q5 (comm set): re-derived at HEAD = 106 files (the RED's 94 + 12: test_s81_s06_anthropic_router, test_s81_s06_router_gate_rows, test_s81_kb_schema, test_s81_s04_spend_breaker (opens CLAUDE.md), five module-path readers, two .github readers, test_channel_freshness). The CLAUDE.md-mention class was narrowed to tests that open CLAUDE.md by a string path (3 files); 23 files only mention it in prose and were not added.

## NOT MEASURED
- mutation table on the GREEN bytes (left to the adversaries); eslint on the changed client files (not named by GC-7); Anthropic's documents (no web grant, R-S12-13); the Arabic native read.

## git status --short (after the commit)
- `A  tests/test_s81_12_legal_v3.py` (the frozen RED .py file, staged, uncommitted: Q2); nothing else.
