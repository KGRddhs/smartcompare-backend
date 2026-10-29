# S81-08 CLIENT-FIRST-OTA fix round 1 - RE-VERIFY report, lens: CORRECTNESS (Opus 5.5)

Unit S81-08 CLIENT-FIRST-OTA (client lane, SmartCompareApp + docs, NO runtime flag). Worktree C:/Users/SynAckITPC/Documents/AI/sc-s81-s08, branch feature/s81-s08-client-first-ota, HEAD bcf75f844d50ad11935a2512f77054d5a36ed4b3 VERIFIED at start and at the end (parent 3f990a69 GREEN, base e7c81956); `git status --short` EMPTY at start, before and after every read-only jest run there, and at the end; no .qa-mutation.lock; the junction intact (node_modules/@babel/core + .bin/jest present at the end). The unit worktree was NEVER edited.

<scratchpad> = C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/fe82d828-54b9-4af1-9c1d-685173488382/scratchpad. Notes folder <scratchpad>/S81-08_fix1_rv (notes.md, rehash.py + rehash_start/end.txt, treecmp.py, align.py, jrun.py, mut.py, mutants.json, offstates.json, mut/*.json|.log, bytecopies/, the probe source, be_*.log, hook_*.log, runlines.txt). Scratch worktrees (both `git worktree add --detach` at bcf75f84, no junction, no node_modules, removed with `git worktree remove --force` at 14:10, 0 entries in `git worktree list`, gone from disk): <scratchpad>/S81-08_fix1_adv (jest probes + every mutant) and <scratchpad>/S81-08_fix1_be (the backend pytest only, never mutated). This report is written THROUGH THE SHELL (Write of a .txt, python copy to .md); pure ASCII, LF.

Inputs read in full: s81-common.txt (twice); RULINGS_FIX1_S81_08 (F1-1..F1-12 + the Re-verifier section; twice); GATE_S81_08 (GC-1..GC-11); RULINGS_S81_08 (R-S08-1..15 + the R-S08B amendment); both ADV1 reports (correctness, appreview); the fix report S81-08_FIX1_REPORT.md; PR_BODY.md; the fix-round diff 3f990a69..bcf75f84 of every file (src, setup.ts, CLAUDE.md, the inventory) and the full gateRows file; the HEAD bodies of useComparisonCounter.ts, resetTime.ts, aiConsent.ts (memo), requestContext.ts (builders), authService.ts logout(), deviceFingerprint.ts, the HomeScreen pill and PaywallScreen's sheetResetClock call; S81_09_BRIEF Q8; OWNER_ACTIONS_S81 item 34; RULINGS_FIX1_S81_12 F2-7; the session-81 ledger tail (newest dated line 2026-10-29 11:11; no dated ENABLE_LEGACY_FINGERPRINT_READER=true line, so the OTA precondition is OPEN, as the PR body states). PLAN_S81 / PLAN_S80 sections were not re-read beyond what the brief and rulings quote.

## 0. Verdict

SOUND: 0 blocking, 0 major, 4 minor (all documentation / unpinned-detail items on the fix agent's own deviations; HEAD code correct on every path probed).

Every fix ruling is implemented and pinned on the exact bytes: F1-1 (M24 KILLED by F1-1a + F1-1b; the logout drop KILLED two ways by F1-1c), F1-2 (X4 / X6 / X9 each KILLED by its row; X31 / M26 / M31 survive as ruled), F1-3 (four mutants KILLED by F1-3a / F1-3b / L1; the full suite moves no node), F1-4 (three mutants KILLED by F1-4), F1-5 (doc comment bytes checked), F1-6 / F1-7 (docs checked sentence by sentence; inventory fences green), F1-8 (five selection mutants KILLED by F1-8a / F1-8b), F1-9 (MF9 and M33 KILLED). The previous round's MAJ-1 / MAJ-A1 is CLOSED and every previous MINOR is closed or recorded (section 2). The four minors below do not move the verdict: none is a defect on a ruled invariant of today's or S81-09's contracted traffic.

## 1. Findings (MINOR only)

m-R1 (unpinned detail of F1-8, GREEN-fix deviation 6; open question Q2 / Q3 of the fix report): the counted-axis DENOMINATOR `limits.daily` is unpinned, and with it the rendered count whenever the axis remaining exceeds 3. Mutants RV8a (`pillTotal = FREE_LIMIT`) and RV8b (`pillTotal = total`, the lifetime cap) SURVIVE the s81_08 set (100/100 each) because every F1-8 row uses limits.daily = 3 = FREE_LIMIT = lifetime_free. Probe P2 (scratch, HEAD bytes): limits.daily 5, remaining.device_daily 2 -> {free 2, total 5}; under RV8a the same status renders 2/3; probe P3 (premium, counted_scope daily, limits.daily 10, remaining.daily 7) -> 7/10 at HEAD, 3/3 under RV8a (the pill would then NOT show the axis's remaining, which is what F1-8 requires). The PR body and the CLAUDE.md row state "total = limits.daily" as fact. Not reachable with today's server (no counted_scope) nor with S81-09's free 3/day cap; reachable for a premium daily axis or a device cap knob above 3. Fix (cheap, test-only): one gate row with limits.daily != 3 (e.g. 5, remaining 4 -> "4/5"), added when Q2 / Q3 are ruled (S81-09 may send limits.device_daily). RV8c (the outer max(0, ...) clamp) also survives; equivalent under valid server values (remaining <= cap); probe P4 shows HEAD renders 3/3 for an inconsistent remaining 5 > cap 3 where RV8c would render 5/3.

m-R2 (defence in depth, contract-guarded by S81-09 brief Q8): a status whose counted_scope names a daily axis but that LACKS that axis's remaining renders the lifetime count BESIDE a reset time. Probe P1 (HEAD): counted_scope 'device_daily', resets_at now+5 h, remaining without device_daily, used.lifetime 2 -> hook {free 1, total 3, resetsAt '2026-10-23T14:00:00.000Z'}, i.e. the pill "1/3 free . resets HH:MM . +B": the BL2 shape (a reset time next to a count that does not reset) that R-S08-2 / F1-8 exist to prevent. F1-8b pins the lifetime count for that shape but carries no resets_at, so the reset node there is unobserved; F1-8's text says the lifetime math "stays for a status without counted_scope", and the PR body's "which stays for a status without one" reads either way. Today unreachable (no counted_scope) and S81-09 is bound by Q8 to send the axis remaining; a safer client would expose resetsAt only when the counted axis's remaining is a number. Ruling asked: state it as a stated limit (and let S81-09's spec pin the status shape), or null resetsAt in that case in a later client unit.

m-R3 (documentation precision, F1-4 / fix deviation 4): the anchor also fixes the WINDOW check of an absolute `resets_at` carried by the 429 detail itself (resolveResetAt(initial, anchoredNow(initial, nowMs))), so such a reset that has passed keeps rendering on every later render of the same sheet (before F1-4 it dropped at the next render). Stated limit 4 in the PR body (and the CLAUDE.md stated limits) still say only "the line stays until the next render" plus the relative anchoring. R-S08-14 has S81-09 send resets_at on the USAGE_LIMIT detail together with retry_after (which takes precedence), so the case needs a 429 with resets_at and no usable retry field. The fix report's deviation 4 says "S81-09 puts resets_at on /usage/status" only, which understates R-S08-14. Add one clause to stated limit 4. Same paragraph, a citation nit: "the fetched status ... still decides first (GC-2)" (PR body, CLAUDE.md row): GC-2 is the field precedence; the fetched-first rule is R-S08-10's M37 (KILLED here as M37f by G11).

m-R4 (documentation precision, CLAUDE.md row "Build-3 identity and pins"): "no response is read differently except the optional reset fields" predates F1-8: the client now also reads `remaining.device_daily` (new optional type field in usageService.ts) and uses counted_scope for the COUNT, not only for the reset line. Behaviour with today's server is unchanged (no counted_scope: the lifetime math byte for byte, pinned by F1-8b / F1-9b), so this is wording only: "except the optional reset and counted-axis fields".

## 2. Previous-round findings: closure (measured on bcf75f84)

| id | status | evidence |
|---|---|---|
| correctness MAJ-1 = appreview MAJ-A1 (memo account key unpinned; M24 survived) | CLOSED | gate rows F1-1a / F1-1b; M24 KILLED by F1-1a + F1-1b (98/100); also M13 now KILLED by F1-1a / F1-1b / F1-1c / X4 beside B5 / E9 / B14b |
| correctness m1 (M26 equivalent) | RECORDED | F1-2 accepts; re-measured SURVIVED (100/100); equivalence holds on these bytes (the real hasCurrentAiConsentForRequest(null) and the new global mock both return false before that guard); PR stated limit 8 + CLAUDE.md |
| correctness m2 (M31 equivalent) | RECORDED | F1-2 accepts; re-measured SURVIVED (100/100); PaywallScreen's monthly branch never reads resetClock (unchanged, 249 lines) |
| correctness m3 (share BODY value) | CLOSED | PR body "Changed VALUES (F1-6)"; CLAUDE.md device-id bullet; true per code (ShareBottomSheet -> getDeviceFingerprint) |
| correctness m4 (jest-only fallback) | CLOSED | setup.ts mock exports hasCurrentAiConsentForRequest; fallback deleted; MF3 KILLED by F1-3b; MF3a KILLED by F1-3a + L1; RV3a / RV3b KILLED by F1-3a; full suite 3794 passed, node diff vs the fix agent's run 0 |
| correctness m5 (sign-out invalidation) | CLOSED | authService.logout() finally drops the memo after clearSession(); MF1 and RV1 (un-export) KILLED by F1-1c |
| correctness m6 (relative reset re-anchored) | CLOSED | WeakMap anchor in resetTime.ts; MF4, MF4b, RV4 KILLED by F1-4 (see m-R3 for the absolute-window wording) |
| correctness m7 (sentry.ts doc comment) | CLOSED | the header comment names x-device-fingerprint and x-device-fingerprint-legacy (diff read) |
| correctness m8 (CLAUDE.md "no request body ..." wording) | CLOSED | now "no request SHAPE changes ...; the device VALUE changes as the device-id bullet says" (see m-R4 for the response-side clause) |
| correctness m9 (X probes) | CLOSED / RECORDED | X4, X6, X9 rows exist and each mutant is KILLED by its row; X5 / X10 / X11 / X12 / X24 / X30 / X31 are stated limits (PR body 8, CLAUDE.md); X31 re-measured SURVIVED (equivalent while the key and the logout drop hold) |
| appreview m1 (owner step 1 re-verify) | CLOSED | CLAUDE.md step (1) and PR step 1 read "re-verify ... published 2026-10-11; no change or re-attestation expected" |
| appreview m2 (inventory row 7) | CLOSED | WHERE cell refreshed (CRLF kept, the added line ASCII, non-ASCII bytes 60 -> 54 = the two arrows); type / Linked / Tracking / Purposes unchanged; the client readers nativeBundle.w37 (c3 / c5 / u15 / u16), privacyManifest.s74, nativeStrings.b3a green in my full run; no backend test reads the file (grep) |
| appreview m3 (LEGAL-V3 precondition) | CLOSED | CLAUDE.md row header + owner step (3); PR body header + step 3 |
| appreview m4 (pill count cross-unit gap) | CLOSED (residuals m-R1 / m-R2) | the hook counts the named axis; MF8a-MF8e KILLED; hook comment rewritten; S81_09_BRIEF Q8 carries the contract |
| appreview m5 (pill order) | CLOSED | resets node before the bonus block; MF9 KILLED by F1-9; M33 KILLED by F1-9b / G9 / G9b; the [NATIVE READ] question added (PR body, CLAUDE.md step 5) |
| appreview m6 (IDFV clause in LEGAL-V3) | RECORDED (cross-unit) | RULINGS_FIX1_S81_12 F2-7 exists (read) |
| appreview m7 (1.0.1 Notes) | RECORDED | OWNER_ACTIONS_S81 item 34 exists (read); CLAUDE.md step (6), PR step 5 |

## 3. RED files (re-hash)

All ten at the start and at the end, blob at bcf75f84 AND real-worktree disk bytes (LF), equal to the given sha256: gateRows c306ae0a..., cameraHeaders ab242206..., consentRecord c8b489fb..., deviceId 66f3ffb5..., i18nKeys c57792aa..., requestHeaders e76fa815..., resetRender 5ab229ee..., resetTime b5527c05..., socialLegacy d44e06de..., sseHeaders f01bd05b... (bad=0 both times); the nine frozen blobs are also byte-equal at 3f990a69 (untouched by the fix round). gateRows: 13 rows (F1-3a F1-4 F1-9 F1-9b F1-8a F1-8b X6 F1-1a F1-1b F1-1c X4 F1-3b X9), 0 non-ASCII bytes, synthetic values only (user-a/b-synthetic, x9.user@example.invalid, IDFV-SYNTHETIC-0001), no credential shape.

## 4. Unit ON / OFF (no runtime flag: ON = the HEAD bytes, OFF = the GREEN bytes for the gate rows and the base bytes for the nine)

- ON, real worktree (read-only): 10 suites, 100 / 100 passed. Same run in the scratch: 100 / 100, per-node diff vs the real run = 0.
- OFF-GREEN (scratch: the nine fix-round files written from `git show 3f990a69:<path>`, restored and sha-verified): 94 passed / 6 failed; the failures are exactly F1-1c, F1-3a, F1-3b, F1-4, F1-8a, F1-9, each an expect() assertion (no other error): the PR body's RED / PIN split CONFIRMED (PIN-type at GREEN: F1-1a, F1-1b, X4, X6, X9, F1-8b, F1-9b).
- OFF-BASE (scratch: the thirteen unit-changed src files + setup.ts from e7c81956, requestContext.ts and resetTime.ts removed; restored and sha-verified): the nine RED files 54 failed / 33 passed, every failure an assertion (GATE_S81_08's base record CONFIRMED); the gate rows at base 11 failed / 2 passed, 6 of them "Cannot find module requestContext" (expected: the gate rows' RED state is defined at the GREEN HEAD, F1 procedure step 2).

## 5. Mutation table (33 mutants on the exact bcf75f84 bytes, in my scratch worktree; .qa-mutation.lock held there for the run and removed; each target byte-copied before its first mutant, exact-string edit matching once (EOL-aware), restore from memory + sha256 compare against the original and the byte copy after EVERY mutant: 33 x restored-sha-OK; afterwards the scratch's 3,454 tracked files were byte-equal to the real worktree except the harness tsconfig line, section 10). Each run = jest --ci over __tests__/s81_08/ (the nine + gateRows, 100 nodes).

Counts: 27 KILLED, 6 SURVIVED (X31, M26, M31 = ruled equivalents / stated limits; RV8a, RV8b, RV8c = m-R1).

| id | verdict | failing rows (assertion) | expected | fix | what |
|---|---|---|---|---|---|
| M24 | KILLED | F1-1a F1-1b | F1-1a,F1-1b | F1-1 | memo ignores the account (spec M24) |
| MF1 | KILLED | F1-1c | F1-1c | F1-1 | logout() keeps the memo |
| RV1 | KILLED | F1-1c | F1-1c | F1-1 | forgetRequestConsent un-exported (logout's typeof guard becomes a silent no-op) |
| X4 | KILLED | X4 | X4 | F1-2 | generation guard removed |
| X6 | KILLED | X6 | X6 | F1-2 | only-if-absent case-sensitive |
| X9 | KILLED | X9 | X9 | F1-2 | a failed legacy read replayed for the process |
| X31 | SURVIVED | - | - | F1-2 | a signed-out request does not drop the memo (stated limit) |
| M22 | KILLED | E9 X4 | E9 | (memo) | not invalidated by recordAiConsent |
| M23 | KILLED | E9 | E9 | (memo) | not invalidated by clearAiConsent |
| M13 | KILLED | B14b B5 E9 F1-1a F1-1b F1-1c X4 | B5,E9 | F1-3 file | consent header without a current record |
| M26 | SURVIVED | - | - | F1-2 | signed-out guard dropped (accepted equivalent) |
| M15b | KILLED | B14b F1-3b | B14b | F1-3 file | consent builder failure throws through |
| MF3 | KILLED | F1-3b | F1-3b | F1-3 | the jest-only fallback restored |
| MF3a | KILLED | F1-3a L1 | F1-3a,L1 | F1-3 | global mock loses hasCurrentAiConsentForRequest |
| RV3a | KILLED | F1-3a | F1-3a | F1-3 | global mock answers true for a null user |
| RV3b | KILLED | F1-3a | F1-3a | F1-3 | global mock answers a constant, not the mocked hasCurrentAiConsent |
| MF4 | KILLED | F1-4 | F1-4 | F1-4 | relative reset re-anchored every render |
| MF4b | KILLED | F1-4 | F1-4 | F1-4 | anchor never stored |
| RV4 | KILLED | F1-4 | F1-4 | F1-4 | anchor refreshed on every call (latest render wins) |
| M37f | KILLED | G11 | G11 | F1-4 line | sheet prefers initialUsage over the fetched status |
| M31 | SURVIVED | - | - | F1-2 | monthly guard of sheetResetClock removed (accepted equivalent) |
| M47 | KILLED | G5b G6 | G5b,G6 | F1-4 file | open / unknown states ignore the scope |
| MF8a | KILLED | F1-8a | F1-8a | F1-8 | pill ignores the counted axis |
| MF8b | KILLED | F1-8a F1-8b | F1-8a | F1-8 | device axis counted from remaining.daily |
| MF8c | KILLED | F1-8a | F1-8a | F1-8 | axis count ignores local compares |
| MF8d | KILLED | F1-8b | F1-8b | F1-8 | a non-daily counted_scope drives the count |
| MF8e | KILLED | F1-8b | F1-8b | F1-8 | named axis without its remaining falls back to remaining.daily |
| RV8a | SURVIVED | - | - | F1-8 | denominator always FREE_LIMIT (m-R1) |
| RV8b | SURVIVED | - | - | F1-8 | denominator keeps the lifetime total (m-R1) |
| RV8c | SURVIVED | - | - | F1-8 | outer used clamp removed (equivalent under valid values) |
| M46 | KILLED | G7 | G7 | F1-8 file | hook ignores counted_scope for resetsAt |
| MF9 | KILLED | F1-9 | F1-9 | F1-9 | pill order reverted (bonus before resets; byte-level block swap) |
| M33 | KILLED | F1-9b G9 G9b | G9,F1-9b | F1-9 | resets node rendered when absent |

Per fix (the brief's "one per fix"): F1-1 M24 / MF1 / RV1; F1-2 X4 / X6 / X9; F1-3 MF3 / MF3a / RV3a / RV3b; F1-4 MF4 / MF4b / RV4; F1-8 MF8a-MF8e; F1-9 MF9 / M33; F1-5 / F1-6 / F1-7 are text-only (no behavioural mutant possible; bytes checked in sections 8 and 2). RV1, RV3a, RV3b, RV4, RV8a-c are new here (not in the fix agent's table). The fix agent's 24-row table is reproduced on these bytes for every id it lists (23 KILLED, M26 SURVIVED).

## 6. Client gates (real worktree, read-only, tools by path through its junction: node v24.11.1, jest 29.7.0)

- nine + gateRows: 10 suites 100 / 100 (rv-real-red10).
- the 4.1 suites (deviceFingerprint.test, screens/paywall.noSubscriptionUi.s69, api.cameraAuthRetry.u13c): 3 suites 38 / 38 (rv-real-4.1) = the fix agent's figure; E3 holds (u13c green).
- FULL suite once at HEAD (rv-real-full): Test Suites 1 failed, 3 skipped, 385 passed, 386 of 389; Tests 4 failed, 13 skipped, 13 todo, 3794 passed, 3824 total; Snapshots 42 / 42. The 4 failures = nativeBundle.w37 d5 / k2 / k4 / k5 (the accepted drift nodes, expect() assertions). Per-node diff vs the fix agent's g_full.json: 0. 3794 = 3694 + 87 + 13.
- tsc / eslint / the 55-suite set / the in-band order pairs: NOT re-run (the fix agent's lines stand; nothing in my findings depends on them).

## 7. Backend (no backend file in the unit diff e7c81956..bcf75f84: CLAUDE.md, docs/privacy-data-inventory.md and SmartCompareApp only)

Comm set re-derived for the fix-round files (grep over tests/ in the clean scratch): CLAUDE.md string-literal readers = test_behavior_dimension_translation, test_ci_gates, test_s81_s04_spend_breaker, test_s81_s08b_legacy_fingerprint (all in the 30); readers of docs/privacy-data-inventory.md: none; SmartCompareApp-path readers: the 23 in the 30 plus the two hook files (excluded by rule, run alone); backend tests naming HomeScreen (test_endpoint_shapes_vs_jsx, test_home_routes) do so in comments only; no backend test reads the client sentry.ts. The 30-file set is complete for this round.

CI-order set = the 30 files sorted (CI collection order), executed as two chunks of 25 + 5 that are also the comm chunks (a separate single 30-file call was not made: same files, same order), in the clean scratch S81-08_fix1_be at bcf75f84:
- [pyt] tag=s08rv-be-ciorder-A start=2026-10-29 13:31:58 end=2026-10-29 13:36:34 elapsed=276s bound=1200s status=OK rc=0 (2284 passed, 4 deselected; [hermeticity] sentinel checked 2284 test(s); [netguard] blocked 28 attempt(s) from 6 node(s): the existing neutralized.supabase.invalid sentinel class in test_auth_routes_invite_fingerprint, test_paid_route_metering, test_s81_s04_spend_breaker)
- [pyt] tag=s08rv-be-ciorder-B start=2026-10-29 13:37:56 end=2026-10-29 13:41:35 elapsed=218s bound=1200s status=OK rc=0 (204 passed; [hermeticity] sentinel checked 204 test(s); [netguard] blocked 37 attempt(s) from 27 node(s))
- 2284 + 204 = 2488 passed, 0 failed = GATE_S81_08's base record (2,488) and GREEN's fresh e7c81956 record (1899 + 589): FAILED node ids at HEAD = none, so branch-only-new is EMPTY.

Hook test files ALONE (tests/test_precommit_hook*.py, the four files): NOT MEASURED.
- [pyt] tag=s08rv-hook-notdash start=2026-10-29 13:42:03 end=2026-10-29 14:02:07 elapsed=1204s bound=1200s status=TIMEOUT rc=124 (167 selected / 160 deselected by -k "not dash"; 16 nodes ran; one F at node 4 = test_scenario[sh-red_git_mv_to_env_refused])
- diagnostic of that node alone: [pyt] tag=s08rv-hook-node4 start=2026-10-29 14:07:15 end=2026-10-29 14:08:14 elapsed=60s bound=600s status=OK rc=0 (1 passed in 53.93 s): the F was the per-test --timeout=120 under load, not a hook defect.
- Why no re-run: the box is in the slow-spawn state (node -e 0 4.7 s, a plain ls 3.6 s, CPU 100 % with another lane's pytest and my jest workers); at >= 54 s per node ALONE, 167 nodes need >= 9,000 s, five times the 1,800 s ceiling, so the TIMEOUT rule's single re-run could not complete; the -k dash half (160 nodes) was not launched for the same arithmetic. This is a DEVIATION from the letter of the TIMEOUT rule, stated here. Context: the unit edits no .githooks file and no backend file (so the hook files are outside the comm set by the common brief), and bcf75f84 itself was committed THROUGH the hook (fix report: rc=0, 166 s).

## 8. CLAUDE.md row and PR body vs the bytes (sentence by sentence)

CLAUDE.md row (lines 522-529 at HEAD; CRLF kept: 992 CRLF / 0 LF-only lines in the working copy; the 7 added lines 0 non-ASCII; file non-ASCII 3937 -> 3937; placed after the S81-15 owner-steps line and before ## Tests): header precondition (LEGAL-V3 live, backend deployed AND landing redeployed, then the dated item-32 line, UB-R4 / 5.1.2(i)) TRUE vs F1-6; rulings list incl. RULINGS_FIX1 F1-1..F1-12 TRUE; request-headers bullet unchanged and TRUE (prior adversary + code read); device-id bullet: "a failed legacy read is retried ... never latched (gate row X9)" TRUE (X9 KILLED; the row covers register, the shared code covers the social sign-ins), "VALUES change ... register / social X-Device-Fingerprint and the share BODY's device_fingerprint_hash carry the new id; invite rows mix the compositions; a revived SAME_DEVICE (S81-08d) must match both" TRUE; consent bullet (memo keyed by the account, pinned by F1-1a / F1-1b killing M24; dropped by record / clear, a signed-out request and logout(); the generation guard X4; setup.ts export, no jest-only fallback) TRUE, each measured in section 5; reset bullet (anchored relative reset; fetched first; the counted-axis count with total = limits.daily; the pill order N/T free . resets HH:MM . +B; a11y unchanged) TRUE in code, with m-R1 (denominator unpinned), m-R3 (absolute-window clause, GC-2 cite) and m-R2 (axis without its remaining); pins bullet ("87 rows" + "13 rows" gate file, E1 / E2 / E4, setup.ts) TRUE (counted from the run JSON), wording m-R4; owner steps (1) re-verify published 2026-10-11 TRUE vs F1-7, (2) item 32 TRUE, (3) LEGAL-V3 + item 32 TRUE vs F1-6, (4) TestFlight, (5) native read incl. the pill-order question TRUE vs F1-9, (6) OWNER_ACTIONS item 34 TRUE (item exists); stated limits list X5 / X10-X12 / X24 / X30 / X31 / M26 / M31 TRUE vs F1-2.

PR body (22,520 B, LF, 4 non-ASCII bytes = the attribution emoji only): header precondition TRUE; "no dated flip line is recorded" TRUE (ledger newest dated line 11:11, no ENABLE_LEGACY_FINGERPRINT_READER=true line); "Build 3 ... in review" consistent with the ledger (no approval line); commits 3f990a69 / bcf75f84 TRUE (git log); every "What it does" bullet TRUE on the bytes except the m-R1 / m-R2 / m-R3 precision points; the id -> node table: every node id listed exists (row ids read from the run JSON: requestHeaders B1-B19 without B3, cameraHeaders C1-C6, sseHeaders D1-D6, deviceId A1-A13, consentRecord E1-E10 + A9b, socialLegacy I1-I5, resetTime F1-F6, resetRender G1-G11 + G5b / G7b / G9b + L1, i18nKeys H1-H3, gateRows the 13), total 87 + 13 = 100 TRUE; "PIN-type ... F1-1a / F1-1b (spec M24), X4, X6, X9; F1-8b and F1-9b ...; RED gate rows ... F1-1c, F1-3a, F1-3b, F1-4, F1-8a, F1-9" TRUE (OFF-GREEN, section 4); E-rows table TRUE (E3 none: u13c 38 / 38 with the 4.1 set); "No .snap, package*.json, app.json, eas.json or native file changed; every __mocks__ shim untouched; PaywallScreen.tsx untouched by the fix round (249 lines)" TRUE (git diff --stat e7c81956..bcf75f84 and 3f990a69..bcf75f84); gate lines: the fix agent's; every figure I re-measured matches (red+gate 100 / 100, 4.1 38 / 38, full 3794 / 4 drift, backend 2488 / 0); mutation table: reproduced (section 5); [NATIVE READ]: AR unchanged by the fix round (no i18n file in the fix diff); stated limits 1-10 TRUE with m-R1 / m-R2 / m-R3 as precision gaps; owner steps 1-5 TRUE; cross-unit F1-10 -> RULINGS_FIX1_S81_12 F2-7 exists, F1-8 -> S81_09_BRIEF Q8 exists and says what the body says; the CLAUDE.md paragraph TRUE (the GREEN api.ts bullet and usage_service Device-bound sentence exist in the e7c81956..bcf75f84 diff).

Inventory row 7 (F1-7): the new WHERE cell matches the code (stableHash = sha256(trim(lower(id))) for the nonce AND the IDFV / ANDROID_ID fallback; fallback only when readNonce throws, never cached; the metered list = withRequestContext call sites + camera + SSE; register / social / share body; legacy at register + two social sign-ins until 2027-03-31T21:00Z; build-3 sentence). Fences: nativeBundle.w37 c3 / c5 / u15 / u16, privacyManifest.s74, nativeStrings.b3a green in the full run.

## 9. Prove-nothing rows (gate rows, measured)

No gate row is vacuous: every one is killed by at least one mutant (F1-3a: MF3a / RV3a / RV3b; F1-4: MF4 / MF4b / RV4; F1-9: MF9; F1-9b: M33; F1-8a: MF8a / MF8b / MF8c; F1-8b: MF8b / MF8d / MF8e; X6: X6; F1-1a / F1-1b: M24 / M13; F1-1c: MF1 / RV1 / M13; X4: X4 / M22 / M13; F1-3b: MF3 / M15b; X9: X9). Partial blind spots: F1-8a / F1-8b never vary limits.daily (all 3) nor exceed it (m-R1); F1-8b's axis-without-remaining case carries no resets_at (m-R2); F1-4 exercises only the relative field (m-R3). Frozen-file notes carried from the previous round: E9's account-switch step is now superseded by F1-1a / F1-1b; B15's signed-out half now exercises the global mock's request read (null -> false), still not the production memo (the real null path is covered by E9's null step; M26 / X31 equivalent).

## 10. Harness, deviations and why they do not weaken the evidence

1. Mutants and probes ran in MY detached scratch worktree, not in place (the task: "Never edit the worktree"; GC-11 / the fix-round Re-verifier section say "in place"; the task's prohibition wins and the intent - byte copies, restore, sha-verify - is kept). jest ran there with NODE_PATH = the real worktree's SmartCompareApp/node_modules (read-only through its junction; no junction or node_modules created in any scratch). Validation: (a) the scratch's 12 LF files (the ten RED files, requestContext.ts, resetTime.ts) were re-written from their blobs so all 3,454 tracked files are byte-equal to the real worktree (treecmp 3454 / 3454); (b) the only harness delta: SmartCompareApp/tsconfig.json `extends` pointed at the absolute expo/tsconfig.base.json in the real node_modules (ts-jest resolves `extends` with TypeScript's own resolver, which ignores NODE_PATH; the compiled options are the same file); original sha 559ce983..., restored before removal; never present in the backend scratch; (c) the baseline in the scratch reproduced the real run node for node (100 / 100, diff 0); (d) OFF-GREEN and OFF-BASE reproduce the fix report's 6 / 7 split and GATE's 54 / 33 record.
2. Backend pytest ran in a SECOND clean scratch worktree (S81-08_fix1_be), because backend tests read SmartCompareApp sources by path (e.g. test_security_regression reads authService.ts) and must never see a mutant.
3. One collection-only `python -m pytest --co -q` (no test executed, 120 s timeout) listed the hook node ids for the diagnostic; every executing pytest went through pyt.py.
4. The first real-worktree run waited 600 s on a probe bug of mine (the probe matched the orchestrator's stall_monitor command line "--pytest-max"); fixed, no effect on any result.
5. The hook TIMEOUT re-run was not attempted (section 7).
6. Budget: about 115 minutes against the 90-minute adversary budget (the box's slow-spawn state; mutant runs 26-137 s each).

## 11. Every run (in order)

- [jest] tag=rv-real-red10 start=1793267490 end=1793267506 rc=0 elapsed=16s waited=600s | Test Suites: 10 passed, 10 total | Tests: 100 passed, 100 total (real worktree, read-only; git status empty before / after)
- [jest] tag=rv-scratch-red10 start=1793267651 end=1793267681 rc=1 elapsed=30s | Test Suites: 10 failed (TS6053 'expo/tsconfig.base' not found: the harness gap fixed in 10.1b; not a result)
- [jest] tag=rv-scratch-red10b start=1793267759 end=1793267830 rc=0 elapsed=71s | Test Suites: 10 passed | Tests: 100 passed (scratch baseline; node diff vs the real run 0)
- mutation run tag rv (mut.py, 13:06-13:52): 33 mutants, 27 KILLED / 6 SURVIVED, 33 x restored-sha-OK, wait 0 s each (table in section 5; per-mutant JSON + logs in mut/)
- [pyt] tag=s08rv-be-ciorder-A ... status=OK rc=0 (2284 passed) and [pyt] tag=s08rv-be-ciorder-B ... status=OK rc=0 (204 passed) (full lines in section 7)
- [pyt] tag=s08rv-hook-notdash ... elapsed=1204s bound=1200s status=TIMEOUT rc=124 (section 7)
- OFF run tag off (mut.py offstates.json): OFF-GREEN 94 passed / 6 failed (59 s), OFF-BASE nine 54 failed / 33 passed + gate rows 11 / 2 (57 s); both restored-sha-OK
- [jest] tag=rv-probe-axis start=1793271743 end=1793271759 rc=0 elapsed=16s | Tests: 4 passed (scratch probe P1-P4, file deleted before removal; outputs quoted in m-R1 / m-R2)
- [jest] tag=rv-real-4.1 start=1793271844 end=1793271858 rc=0 elapsed=14s | Test Suites: 3 passed | Tests: 38 passed, 38 total
- [jest] tag=rv-real-full start=1793271883 end=1793271980 rc=1 elapsed=97s | Test Suites: 1 failed, 3 skipped, 385 passed, 386 of 389 total | Tests: 4 failed, 13 skipped, 13 todo, 3794 passed, 3824 total | Snapshots: 42 passed, 42 total
- [pyt] tag=s08rv-hook-node4 start=2026-10-29 14:07:15 end=2026-10-29 14:08:14 elapsed=60s bound=600s status=OK rc=0 (1 passed)

## 12. NOT MEASURED

- The pre-commit hook test files (both halves): TIMEOUT once, re-run infeasible on this box today (section 7).
- tsc, eslint, the 55-suite set, the --runInBand order pairs (the fix agent's records stand; no finding of mine depends on them).
- The spec section-6 mutants on code the fix round did not change (the previous correctness adversary's 48 / 51 table on the GREEN bytes stands; those files are byte-identical except the comment-only sentry.ts hunk and the usageService.ts type line).
- Real devices, the OTA, App Store Connect (owner steps).

## 13. End state

- sc-s81-s08: HEAD bcf75f844d50ad11935a2512f77054d5a36ed4b3, `git status --short` EMPTY, no .qa-mutation.lock, junction intact; the ten RED files equal the given sha256 (blob and disk) at the end.
- Both scratch worktrees removed (`git worktree remove --force`, rc 0 each; 0 matching entries in `git worktree list`; gone from disk); neither ever held a junction or node_modules.
- No process of mine left running; no package manager, no npx, no git write in any existing worktree, no .env read, no personal value written.
