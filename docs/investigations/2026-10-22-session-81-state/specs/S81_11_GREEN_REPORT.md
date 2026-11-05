# S81-11 GREEN REPORT (HONEST-FRAGRANCE-UI + D20) -- GREEN agent, Claude Opus 5.5, 2026-11-05 10:05-10:50 AST

Unit S81-11; base 6869a3e655805afd3adbba43f99578dd79585934 (origin/main); branch feature/s81-s11-honest-fragrance-ui; HEAD 5fcb9fba3b9d78c23289685613c0ae75f4d1199d (one commit through the pre-commit hook; no push, no PR, no rebase). Written through the shell (python), per the harness rule. `git status --short` after the commit: clean.

## Method
- Byte copies of all 55 candidate paths first: <scratchpad>/S81-11_green_before/ (+ SHA256SUMS.txt). The RED prototype (prototype.diff + prototype_files/) was used as the starting reference and every hunk was reviewed against the spec as amended by RULINGS_S81_11 and GATE_S81_11; changed versus the prototype: errorCopy (the reason-set constant moved above the A11 doc block, the doc extended), HomeScreen (one `sendCategory` const per send site, the `(data as any)` read replaced by a typed `reason`, the chip comment), types.ts (top-level `reason?: string`; `Record<string, any>[]`), ResultsContent (the IIFE replaced by `provenanceFor` / `renderProvenanceLine`, provenance computed once per card, typed useTranslation, the empty whitespace line and the unused `cohortSlot` style removed, comments without the component name), ResultsAccordion (array type), the dead styles / comments / the unused `useLanguage` in HomeEditorialSections, ProfileEditorialSections, HistoryScreen, ReferralLandingScreen, the comment rewrites of C2 / C3 (LoadingRings header, InviteeQuiz, LoadingScreenVariants), the catalogs (GC-4 diacritics stripped from 9 AR values; quote_3 AR re-cut for the r31 verb fence). Kept byte-identical to the reference after review: launchSurfaces.ts, fieldStatusView.ts, ResultsScreen.tsx (a deviation from "re-derive every hunk" in letter: the text was read line by line against R-S11-12/13/14/18/19/21/23/24/26/27 and left as is). The 13 E1b mock removals and every other E-row were re-derived from the base bytes by my own scripts (erows1.py / erows2.py / e1b.py).
- No mutation in GREEN (the adversaries run them); no .qa-mutation.lock was created.

## Runs
# S81-11 GREEN gate log lines (HEAD 5fcb9fba; base 6869a3e6)
toolchain: node v24.11.1, jest 29.7.0, typescript 5.9.3, eslint v9.39.4 (by path through the junction)
[jest] tag=s11green-red1 start=2026-11-05 10:21:30 end=2026-11-05 10:21:48 rc=0
[jest] tag=s11green-comm-00 start=2026-11-05 10:22:25 end=2026-11-05 10:22:40 rc=0
[jest] tag=s11green-comm-01 start=2026-11-05 10:22:44 end=2026-11-05 10:22:56 rc=0
[jest] tag=s11green-comm-02 start=2026-11-05 10:23:00 end=2026-11-05 10:23:13 rc=0
[jest] tag=s11green-comm-03 start=2026-11-05 10:23:17 end=2026-11-05 10:23:30 rc=1
[jest] tag=s11green-comm-04 start=2026-11-05 10:23:33 end=2026-11-05 10:23:49 rc=1
[jest] tag=s11green-comm-03 start=2026-11-05 10:24:21 end=2026-11-05 10:24:39 rc=0
[jest] tag=s11green-comm-04 start=2026-11-05 10:24:43 end=2026-11-05 10:24:57 rc=0
[jest] tag=s11green-comm-05 start=2026-11-05 10:25:01 end=2026-11-05 10:25:14 rc=0
[jest] tag=s11green-comm-06 start=2026-11-05 10:25:18 end=2026-11-05 10:25:35 rc=1
[jest] tag=s11green-comm-07 start=2026-11-05 10:25:39 end=2026-11-05 10:25:53 rc=0
[jest] tag=s11green-comm-08 start=2026-11-05 10:26:04 end=2026-11-05 10:26:17 rc=0
[jest] tag=s11green-comm-09 start=2026-11-05 10:26:22 end=2026-11-05 10:26:34 rc=0
[jest] tag=s11green-comm-00 start=2026-11-05 10:26:38 end=2026-11-05 10:26:52 rc=0
[jest] tag=s11green-comm-01 start=2026-11-05 10:26:56 end=2026-11-05 10:27:10 rc=0
[jest] tag=s11green-comm-02 start=2026-11-05 10:27:14 end=2026-11-05 10:27:28 rc=0
[jest] tag=s11green-pair-home-ab start=2026-11-05 10:29:30 end=2026-11-05 10:29:38 rc=0
[jest] tag=s11green-pair-home-ba start=2026-11-05 10:29:42 end=2026-11-05 10:29:47 rc=0
[jest] tag=s11green-pair-home2-ab start=2026-11-05 10:29:52 end=2026-11-05 10:29:57 rc=0
[jest] tag=s11green-pair-home2-ba start=2026-11-05 10:30:01 end=2026-11-05 10:30:04 rc=0
[jest] tag=s11green-pair-rc-ab start=2026-11-05 10:30:07 end=2026-11-05 10:30:11 rc=0
[jest] tag=s11green-pair-rc-ba start=2026-11-05 10:30:14 end=2026-11-05 10:30:18 rc=0
[jest] tag=s11green-pair-api-ab start=2026-11-05 10:30:22 end=2026-11-05 10:30:24 rc=0
[jest] tag=s11green-pair-api-ba start=2026-11-05 10:30:28 end=2026-11-05 10:30:31 rc=0
[jest] tag=s11green-pair-err-ab start=2026-11-05 10:30:34 end=2026-11-05 10:30:39 rc=0
[jest] tag=s11green-pair-err-ba start=2026-11-05 10:30:43 end=2026-11-05 10:30:48 rc=0
[jest] tag=s11green-pair-ver-ab start=2026-11-05 10:30:53 end=2026-11-05 10:30:59 rc=0
[jest] tag=s11green-pair-ver-ba start=2026-11-05 10:31:02 end=2026-11-05 10:31:05 rc=0
[jest] tag=s11green-pair-cam-ab start=2026-11-05 10:31:11 end=2026-11-05 10:31:16 rc=0
[jest] tag=s11green-pair-cam-ba start=2026-11-05 10:31:19 end=2026-11-05 10:31:25 rc=0
[jest] tag=s11green-inband-touched start=2026-11-05 10:31:43 end=2026-11-05 10:31:55 rc=0
[tsc] tag=s11green-tsc start=2026-11-05 10:32:03 end=2026-11-05 10:32:12 rc=0
[eslint] tag=s11green-eslint files=55 start=2026-11-05 10:32:22 end=2026-11-05 10:32:40 rc=0
[tsc] tag=s11green-tsc2 start=2026-11-05 10:36:26 end=2026-11-05 10:36:34 rc=0
[jest] tag=s11green-inband-touched2 start=2026-11-05 10:36:41 end=2026-11-05 10:36:53 rc=0
[hermeticity] sentinel checked 1846 test(s)
[netguard] blocked 39 attempt(s) from 29 node(s)
========= 1846 passed, 4 deselected, 13 warnings in 69.41s (0:01:09) ==========
[hermeticity] sentinel checked 458 test(s)
[netguard] blocked 24 attempt(s) from 2 node(s)
====================== 458 passed, 13 warnings in 13.75s ======================
jest comm set: 239 suites (RED COMM_SET 240 jest entries minus the deleted CohortBadge.test) in 10 chunks of <= 25; head failures = the 4 config/nativeBundle.w37 drift nodes only; comm -13 EMPTY; comm -23 EMPTY
head failed nodes:
__tests__/config/nativeBundle.w37.test.ts :: W3-7 (d) runtime dependencies are imported, justified, or pending removal > d5 react-native-gesture-handler is removed from package.json, package-lock.json and node_modules
__tests__/config/nativeBundle.w37.test.ts :: session 70 U4b ? Expo SDK 54 patch level with one deliberate exclusion > k2 package-lock.json and node_modules resolve the five packages at or above those patches
__tests__/config/nativeBundle.w37.test.ts :: session 70 U4b ? Expo SDK 54 patch level with one deliberate exclusion > k4 eslint-config-expo is on the SDK-54 line (~10.0.x) in package.json, the lock and node_modules
__tests__/config/nativeBundle.w37.test.ts :: session 70 U4b ? Expo SDK 54 patch level with one deliberate exclusion > k5 offline expo-install consistency: every declared package the installed expo bundles satisfies its bundled range, apart from expo.install.exclude

## Results
- RED 124 / 124 (8 files); RED files re-hashed before the work, before the commit and after it: all eight equal GC-1.
- In-band pairs (7 pairs x 2 orders) rc 0; the touched set in band 51 suites / 677 passed.
- tsc rc 0; eslint 0 errors (55 files).
- Jest comm (239 suites): head failures = the 4 w37 drift nodes = base; comm -13 EMPTY, comm -23 EMPTY. Backend 23 pins 1846 passed / 6 readers 458 passed, both = base; comm -13 EMPTY.
- Catalogs: 1,011 / 1,011, parity 0; 15 added, 10 changed, 17 deleted; GC-4 0 hits; no forbidden word; no EN digit.

## Deviations / notes for the gate
- D-G1 key counts 15 / 10 / 17 (the gate text says 12 / 7 / 17; the 1,011 leaf count is consistent with 15 / 10).
- D-G2 onboarding.s1.quote_3 AR re-cut (the spec cell carried the standalone verb the b3a r31 PIN forbids in a changed value; r31 went red once and is green after the re-cut; not an E-row).
- D-G3 E1c: per spec E1c the two cohort rows became ONE absence row, so the passing node "renders nothing in the cohort slot when peerCount=0" is removed with the failing one; E1d / E1e / E2 / E6 / E7 / E8 / E8b / E11 rows carry new titles; E6 changes "27" to "26" (BRAND_KEYS loses basedOn; the six count keys stay by R-S11-11); the s3 ORDERED_ANCHORS list loses one it.each node.
- D-G4 the fixture `_doc` of b3a_copy.json gained a one-sentence S81-11 prefix (the reason comment for E4 / E13; JSON has no comments).
- D-G5 the PR body is pure ASCII except the required attribution line (4 bytes, the robot emoji); S81_11_NATIVE_READ.md carries the Arabic script (the S81_10_NATIVE_READ.md precedent; a native reader cannot read \u escapes).
- D-G6 the commit trailer names Claude Opus 5.5 (the session's agent model), not Fable.
- Open: the CLAUDE.md "Results redesign ... CohortBadge inline below verdict" line (Frontend section) and the PersonalizationChip.tsx header comment still name the badge; GC-14 limits CLAUDE.md to the one block + :341 and PersonalizationChip is outside the footprint, so both are left for the orchestrator's ruling.
- NOT RUN by ruling: the R8 pair, paid-route metering as a gate, the hook test files, a pytest CI-order set, the corpus gate, a base scratch worktree; the FULL jest suite (LC-7).

## Files (path, +, -, sha256 after)
- CLAUDE.md +9 -1 bfdd062772145c06245116b71e16a1ebc97ab5a5539640d302e3ed0e26271192
- SmartCompareApp/__tests__/HistoryScreen.bundleE.s3.test.tsx +4 -2 ac89d8e02468d50c8d8a956166a9a7fb1bd3aec93f2572fe73c0fc3e6a405a05
- SmartCompareApp/__tests__/HomeScreen.bundleE.s3.integration.test.tsx +42 -22 ff90f9a75c2b9b5a807fe5b4d73aaeef8f4835ec02e5afe525cc2092b840adc9
- SmartCompareApp/__tests__/HomeScreen.bundleE.s3.test.tsx +5 -3 9e2af9b4757934ed616e1964409fe395034ba1d3ee58dd01a96700b36296f2c4
- SmartCompareApp/__tests__/HomeScreen.catfix.d1.test.tsx +22 -18 980c7d9792f69bc7cc0797be8571deeeff84f20bf768a613ae86d10e8a35f810
- SmartCompareApp/__tests__/InviteeQuizScreen.matchScore.m18.test.tsx +6 -3 5db14b1a3cbb08bd4d5724c1b1b81eb728db8144d699c8b2e0f8d31fbee88d92
- SmartCompareApp/__tests__/ReferralLandingScreen.redesign.test.tsx +6 -3 fd556b3cdc3838c7706f23942e2252228d853aceb13fc95193d05fd00bc46860
- SmartCompareApp/__tests__/ResultsContent.confidenceSheet.test.tsx +1 -1 63ffaf6ce27e1c5782870a1d7cf96c877a1a1fd784d7516a6f7ef45dd54cd2d5
- SmartCompareApp/__tests__/ResultsContent.imageUrl.test.tsx +1 -1 7927e1ebff0ce6ef102c889c2f0942a540929ba3337ce4568e4c4da0b0216025
- SmartCompareApp/__tests__/ResultsContent.partialNote.test.tsx +1 -1 95ea261fca928fbf9346b2c59e3f708a804a5a09da8ecf9927339a7719779a35
- SmartCompareApp/__tests__/ResultsContent.perCategory.test.tsx +1 -1 ff689fba9b086153c77e2dbc54ad97e4c96faba2250e24ab94c5535c825b3edd
- SmartCompareApp/__tests__/ResultsContent.scoreGuard.test.tsx +1 -1 c627a8943c0a255324e4296ceadc13822733c03394c6619630bdfa1c6034453a
- SmartCompareApp/__tests__/ResultsContent.specsComparisonShape.test.tsx +1 -1 ccc2c5042c0f55cb2168b154e69ca5033b0cbf869d1afcf1a8bd579bc4c5b7e6
- SmartCompareApp/__tests__/ResultsContent.v2Wiring.test.tsx +1 -1 e57ed4aa3797348c6b50addd8bc3978ad95c1de266cece774ada42e22b176de9
- SmartCompareApp/__tests__/ResultsScreen.bundleE.s3.test.tsx +6 -5 c8cb6630ecf06cd56f9de09ca08371f7a61764ec4da876c1ea81a74771929f5a
- SmartCompareApp/__tests__/ResultsScreen.networkMatrix.m18.test.ts +5 -1 ed3dfb330b52293e95a3d8ef0a4eeafceaa17546c2f0a36833903d01276cc5b5
- SmartCompareApp/__tests__/ResultsScreen.redesign.test.tsx +6 -5 125e236221218eb759ff14649b4ca50d5f8428db0177a0002a696dbadb10bc13
- SmartCompareApp/__tests__/ShareBottomSheet.redesign.test.tsx +6 -4 2d4477e19f0cd25c61b3a2c2649f55a8dbd98e9d3d9c1fec789e0019134a8674
- SmartCompareApp/__tests__/clientTruth/medicalNote.s74.test.tsx +1 -11 99b00383873e39a3582c1cbe87abe49611efad4257a710a2a49b8a8fe33ef0c3
- SmartCompareApp/__tests__/components/CategorySelector.test.tsx +38 -22 7e2b0ad594de3c940e902a9dc58bf56dd2c961872c03a7d49368f28ede6e78be
- SmartCompareApp/__tests__/components/CohortBadge.test.tsx +0 -86 DELETED
- SmartCompareApp/__tests__/components/ResultsContent.a11y.w311.test.tsx +1 -3 62f812a9232762d7ad2cc6a20534be0ae066196bf91fab736cbede67744b91b0
- SmartCompareApp/__tests__/components/ResultsContent.render.test.tsx +8 -22 91f31492e74217a4395225c6e3f4d6be1717f4cecca19dd39aac1a4f270ab62d
- SmartCompareApp/__tests__/components/ResultsContent.rewriteOrder.test.tsx +6 -13 8cd64bf915f67ca1daef1bcc5441c7fa0883658a64d7345b76dfcc133b441d96
- SmartCompareApp/__tests__/components/ResultsContent.runnerUp.test.tsx +1 -1 f4e39c69a570cc08cb93ed75ab750878bc79bc872cf2c7414fe2bdc8b5a104ed
- SmartCompareApp/__tests__/demographics.i18n.test.ts +3 -5 dbfbe6a8b108033d23b19001426a56fce444f65e30965062179ad3e0b28baa71
- SmartCompareApp/__tests__/fixtures/b3a_copy.json +10 -16 43a6378a09bb68e7301f99a4c26b1f3c6771bdd1d19228d559c85f983dc71fc2
- SmartCompareApp/__tests__/hero/LoadingRings.test.tsx +3 -4 276afc0d538d1bfe5248e94821ed88a8d96845cb38987da54feebeb772ac1f74
- SmartCompareApp/__tests__/hero/__snapshots__/LoadingRings.test.tsx.snap +0 -147 00fef2b97703fb4066b08feb63ecf0f1e5149c2c6af8fe67272ed342e07a037d
- SmartCompareApp/__tests__/i18n/brand.myez.s69.test.ts +3 -4 772b09cc7654911a5b4dd5d11291450bb40d46491cf2425312cab73637b9e0e0
- SmartCompareApp/__tests__/i18n/priceDigits.crossScreen.w414.test.ts +2 -2 5092809107edd25106dc2b6b70282a0abf62b3cb2a14b9f02bbeb860fb8c79fc
- SmartCompareApp/__tests__/s11/categoryRow.s11.test.tsx +460 -0 b30471b3b72c468c84179ffb189a3ea2b5efe1e007559f367c913c6706af0b5e
- SmartCompareApp/__tests__/s11/copy.s11.test.tsx +261 -0 f676178130161ea4159c75b5f1b4c258997e55c0c4b2e0bc22be15119eed0d7e
- SmartCompareApp/__tests__/s11/fabricated.s11.test.tsx +268 -0 35aa66559feacf7d067532232a5aa3e2b8d1143b6b5b29cd547fb7edad64529e
- SmartCompareApp/__tests__/s11/honestUnknowns.s11.test.tsx +669 -0 489889830480f09a4b7e97777b43a6e42145b05283e0111096ed6b272daa08de
- SmartCompareApp/__tests__/s11/launchSurfaces.s11.test.ts +296 -0 e4abba60b17be97e22e7c980525842f4db0faeda4c0072e5f71a628dde8fe726
- SmartCompareApp/__tests__/s11/refusals.s11.test.tsx +525 -0 751b24d660e3ae2b5c0a225113491dcd8c5115467dadd647069bddaca9fe07f5
- SmartCompareApp/__tests__/s11/refusalsCamera.s11.test.tsx +224 -0 573a9c139e8da60105b9337c3c3a286992fd90f4a367fd1d4e2dff2a1ea11152
- SmartCompareApp/__tests__/s11/sseFallback.s11.test.ts +327 -0 c3e4224ca2065b9c99450b680edcdaa0da523841c62ca11344f250b317161256
- SmartCompareApp/__tests__/screens/ResultsScreen.bundle_c_integration.test.tsx +5 -4 4b376ae65d2f7f24572685a9e54b335b4e52d26740397639afa7db5e5cff2fc4
- SmartCompareApp/__tests__/screens/ResultsScreen.degraded.s69.test.tsx +1 -1 05f7a4409b59a15cd0617ccc2562dfff280797cbe3899a3ccd583ca21eb99a73
- SmartCompareApp/src/components/CategorySelector.tsx +47 -11 20d998047c98c8db50d1c3fc1b68e4aec9e732bd36bcf82aaca760f030d653ea
- SmartCompareApp/src/components/CohortBadge.tsx +0 -105 DELETED
- SmartCompareApp/src/components/HomeEditorialSections.tsx +7 -85 0d80f100f5fb34c76e0ee4c8cbed9b5c3a0b9c673c6d0c2cc176ad83c26f006d
- SmartCompareApp/src/components/ProfileEditorialSections.tsx +0 -10 76df053c84aa4a39b09aef389864a7b983dc3aa2e85774518f60bd7f71e0f75e
- SmartCompareApp/src/components/hero/LoadingRings.tsx +14 -9 42add6db20adc60175d97cd9e4ad04471918dfb681d3ec2c7ba5ce94f0b5ad98
- SmartCompareApp/src/components/results/ResultsAccordion.tsx +45 -0 7641c345089c85d5e3539fe6839fa6143ca6bca3884041d65383d59a2ceb12c1
- SmartCompareApp/src/components/results/ResultsContent.tsx +104 -32 4358e4c68fa7d4b2b6b0efcc78384cd009ad7521b64b29109a8f7f7055f5e0d9
- SmartCompareApp/src/i18n/ar.json +25 -27 6b9471c6a03b5d322278afc26f09877158df598bf575cf0346f51735c7165f68
- SmartCompareApp/src/i18n/en.json +25 -27 89c6bc1d04fd94c44f27466e356aed1651ea7b79ba8dfb8dc052a266c9f5612f
- SmartCompareApp/src/screens/HistoryScreen.tsx +5 -18 b59d233cd7bf8215c2b9dfebb0bae5607ba649d02339abba1d938b76adad0885
- SmartCompareApp/src/screens/HomeScreen.tsx +64 -19 0913e78d1f10356f9bace5ea37adc849543dfe1913a14204c79fa5b101ae7902
- SmartCompareApp/src/screens/InviteeQuizScreen.tsx +11 -6 8c21f931b38489bca6781f243a967a0e00e79bcb2279d375ab83e8acdf5e0a88
- SmartCompareApp/src/screens/LoadingScreenVariants.tsx +4 -4 24dcc2001175fc1658d4c540dd60b1739c2a14ca3817afe858e644f6cceb600c
- SmartCompareApp/src/screens/ReferralLandingScreen.tsx +0 -24 78b056f8a40fa97dc3b367f937a47b693fcec45814e3fc4d87cce9c91a190b02
- SmartCompareApp/src/screens/ResultsScreen.tsx +46 -34 4d5a907c977da13d301e9e0701da401d794e04dc6faac458d9a384f27d6ab0a3
- SmartCompareApp/src/services/api.ts +51 -2 f59451e21e7c91a39b8e962e864a1b8f7b9cc459b5727a55856ce8a4575fa0bf
- SmartCompareApp/src/services/appVersionService.ts +2 -0 fcd59e30a82e7de2629c286ab948c0f811018326d36b5124db0c0a08fb53c425
- SmartCompareApp/src/services/errorCopy.ts +19 -1 37dc5ef321f576f3802dcc42b786f3d83e960359af26e88396a5373cf9a368c9
- SmartCompareApp/src/services/fieldStatusView.ts +100 -0 d3148aa4c3d01e9855e62f22211dcd9768d3b61d929de01ee60399fb3544b261
- SmartCompareApp/src/services/launchSurfaces.ts +89 -0 0c45ca30f62a4f0002a8f90a44e557f945b6774cdc0accd87414004c8d99aca4
- SmartCompareApp/src/types/types.ts +10 -0 2f193ccd08a4c38afcdd7d42a52b9ddc3dd31860a4a0b7400aef1252f309551c

## Deliverables
- <scratchpad>/S81-11_green/PR_BODY.md, S81_11_NATIVE_READ.md, S81_11_GREEN_GATE_LOGS.txt, runs/ (jest json + logs, pyt logs), files_changed.json, head_failed.txt.
