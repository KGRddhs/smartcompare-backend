# S81-08 CLIENT-FIRST-OTA fix round 2 (PIN-FIX) - REPORT (Opus 5.5)

Verdict: BLOCKED (a ruling conflict, measured). NO commit made. HEAD before = HEAD after = bcf75f844d50ad11935a2512f77054d5a36ed4b3 (branch feature/s81-s08-client-first-ota, worktree C:/Users/SynAckITPC/Documents/AI/sc-s81-s08, origin/main e7c81956). git status --short EMPTY at the start and at the end. No .qa-mutation.lock left. This report is written through the shell (quoted heredoc), pure ASCII.

Inputs read in full: s81-common.txt; RULINGS_FIX1_S81_08.md (F1 rulings + the F2 addendum); S81-08_fix1/REVERIFY_REPORT.md (m-R1..m-R4, RV8a-c, probe P1).

## 1. The blocker (measured)

E1 (F2-2: resetsAt exposed ONLY when remaining[counted_scope] is a number) contradicts two rows of the FROZEN RED file SmartCompareApp/__tests__/s81_08/resetRender.s81_08.test.tsx (sha256 5ab229ee..., must stay byte-identical; G1 requires every node green):
- G7 (lines 332-343), 2nd element: status({ resets_at: at, counted_scope: 'device_daily' }); the file's default status() remaining is { daily: 0, monthly: 7, lifetime_free: 0 } (no device_daily); the row expects resetsAt = at.
- G7b (lines 345-356): status({ used: { daily: 1, monthly: 1 }, remaining: { daily: 2, monthly: 9 }, resets_at: at, counted_scope: 'device_daily' }); expects r.resetsAt toBe(at).
Both are exactly the m-R2 / probe-P1 shape (a device_daily axis WITHOUT remaining.device_daily) that F2-2 orders nulled. They were written at RED under R-S08-2 (resetsAt for any daily counted_scope), before F1-8 introduced remaining.device_daily.

Trial (the E1 one-line hunk + the two E2 rows, in place, byte copies first, under the lock):
[jest] tag=fix2-trial-red10 start=1793273537 end=1793273634 rc=1 elapsed=97s | Test Suites: 1 failed, 9 passed, 10 total | Tests: 2 failed, 100 passed, 102 total
Failures (expect assertions only): G7 at resetRender.s81_08.test.tsx:342 (received [at, null, null, null, null, null], expected [at, at, null, null, null, null]); G7b at :354 (expected "2026-10-23T14:00:00.000Z", received null). The two new rows F2-1 and F2-2 passed; every other node passed.

So E1 as ruled, "the nine frozen RED files stay byte-identical" and G1 "every node green (102)" cannot all hold. Any guard that nulls resetsAt for device_daily-without-its-remaining turns G7 / G7b red; any guard that keeps them green leaves m-R2's own probe shape unfixed. The choice is a ruling, not mine: per "apply EXACTLY these, nothing else" I committed nothing and restored the worktree (section 2).

## 2. Applied, measured, restored (E0-E2); E3 / E4 not done

E0: git diff --name-only origin/main...HEAD (bcf75f84 vs e7c81956), sorted: 29 files, saved as <notes>/E0_footprint.txt (CLAUDE.md, docs/privacy-data-inventory.md and 27 SmartCompareApp paths).

Byte copies (<notes>/bytecopies/) and sha256 BEFORE:
- SmartCompareApp/src/hooks/useComparisonCounter.ts 8511e43acf642298725c317e73b2d0ea7b47b02e87ecbadfce5a8b730eab51b8 (6390 B, CRLF 130, LF-only 0, non-ASCII 15)
- SmartCompareApp/__tests__/s81_08/gateRows.s81_08.test.ts c306ae0a0a7a6bc76e67fe706d08422cf30c51c4759f696e158f4ed5b9376de8 (27998 B, LF 697, non-ASCII 0)
- CLAUDE.md f4c5bd6f77f3c68ca575e8979fa63173ee5fc1489ca4c3448e98006643ccda4b (572847 B, CRLF 992, non-ASCII 3937): never edited this round
TRIAL bytes (measured, then restored): hook aa9ae4dec3ce1a829b4996eda899f4d3fda809b3ebe02ca3b8bfc8bd3cf0b67c (6443 B, CRLF 130, non-ASCII 15: the hunk added none); gateRows 348849017feb39624c083ede2aa33da801b7a1a0edbdf8b6e2a172874229ad31 (29581 B, LF 728, non-ASCII 0).
AFTER restore (shutil.copyfile from the byte copies): hook 8511e43a... and gateRows c306ae0a... = BEFORE (compared in full); the nine frozen RED files equal their recorded sha256 at start, after the trial and at the end: cameraHeaders ab242206, consentRecord c8b489fb, deviceId 66f3ffb5, i18nKeys c57792aa, requestHeaders e76fa815, resetRender 5ab229ee, resetTime b5527c05, socialLegacy d44e06de, sseHeaders f01bd05b.
The exact trial diff (the E1 line + both rows) is kept for the next round: <notes>/trial_E1_E2.patch (2923 B, git diff of the trial).

E1 trial hunk (the return line): "increment, resetsAt };" -> "increment, resetsAt: typeof axisRemaining === 'number' ? resetsAt : null };"
E2 rows (inside the fix-round-1 describe, after F1-8b and before X6, using the file's hookFor / pill / lifetimeStatus / home / pillRuns idioms):
- F2-1 (PIN, killed by RV8a / RV8b): status used.lifetime 0, limits.daily 5, remaining { daily 4, monthly 9, lifetime_free 3, device_daily 2 }, counted_scope 'device_daily', resets_at now+5h -> the hook pill {free 2, total 5}; HomeScreen fed that hook result renders the first pill run '2/5 ' + t('home.headerCounter.free').
- F2-2 (RED at bcf75f84, killed by MG1): lifetimeStatus with counted_scope 'daily', remaining { monthly 9, lifetime_free 1, device_daily 0 } (no daily), resets_at now+5h -> {free 1, total 3, resetsAt null}; HomeScreen renders '1/3 ' + free and no home-header-counter-resets node.

## 3. Mutants (in place under .qa-mutation.lock, on the trial bytes; exact-string edit matching once; restore from memory + sha256 compare after each)

[jest] tag=fix2-mut-RV8a start=1793273763 end=1793273804 rc=1 elapsed=40s | Tests: 1 failed, 14 passed, 15 total | KILLED by F2-1(assert) | restored-sha-OK
[jest] tag=fix2-mut-RV8b start=1793273804 end=1793273866 rc=1 elapsed=61s | Tests: 1 failed, 14 passed, 15 total | KILLED by F2-1(assert) | restored-sha-OK
[jest] tag=fix2-mut-RV8c start=1793273867 end=1793273916 rc=0 elapsed=49s | Tests: 0 failed, 15 passed, 15 total | SURVIVED | restored-sha-OK
[jest] tag=fix2-mut-MG1 start=1793273932 end=1793274035 rc=1 elapsed=103s | Tests: 1 failed, 101 passed, 102 total | KILLED by F2-2(assert); G7 / G7b green | restored-sha-OK
[jest] tag=fix2-mut-ALTB start=1793274035 end=1793274116 rc=0 elapsed=80s | Tests: 0 failed, 102 passed, 102 total | alternative guard trial (not a mutant, NOT applied) | restored-sha-OK

Mutant definitions: RV8a = "pillTotal = FREE_LIMIT;"; RV8b = "pillTotal = total;" (the lifetime total); RV8c = the outer Math.max(0, ...) clamp on pillUsed removed (RV8a-c run on the gate-rows file alone, 15 nodes); MG1 = the return line back to "resetsAt };" (= the bcf75f84 hook) run on the nine + the gate rows (102 nodes); that run also proves F2-2 is RED at bcf75f84 and F2-1 is PIN-type (green there).
- RV8c SURVIVES F2-1 (equivalent under valid values, remaining <= cap). The F2-1 ruling text says the row "kills RV8a / RV8b / RV8c"; measured: RV8a and RV8b only (the brief's G2 names only those two). Killing RV8c needs an inconsistent status (remaining > cap, re-verifier probe P4): a ruling item if wanted.
- ALTB = "resetsAt: countedScope !== 'daily' || typeof axisRemaining === 'number' ? resetsAt : null };" (the guard limited to the 'daily' axis): 102 / 102 with the frozen files untouched. MG1's bytes are identical whichever guard it replaces, so F2-2 is killed by MG1 under ALTB as well.

## 4. Ruling needed (options with what I measured; none applied)

(A) Keep E1 as ruled and authorize a deliberate E-row change to the frozen resetRender.s81_08.test.tsx: give G7's device_daily case and G7b a numeric remaining.device_daily (two lines). Fixes m-R2 on both axes (probe P1 included). NOT measured (I do not edit frozen files).
(B) Narrow E1 to the 'daily' axis (ALTB): measured 102 / 102, F2-2 green, MG1 killed, frozen files byte-identical; the device_daily-without-its-remaining shape (P1) stays a stated limit carried by S81-09 brief Q8 (S81-09 sends remaining.device_daily with counted_scope 'device_daily').
(C) No hook change: m-R2 becomes a stated limit (the re-verifier's first option); only F2-1 and E3 land, the F2-2 row is dropped.
Docs note for (A) or (B): the CLAUDE.md S81-08 row (line 526, the Reset time bullet) says "useComparisonCounter exposes resetsAt only then" (only for a daily counted axis); E3 as briefed does not touch that clause, so with a guard it under-states the rule (one clause to add, ruled wording).
Count note: F2-4 says the full suite passed = "base + 89"; the brief says 3694 + 87 + 13 + 2 = 3796 (= base + 102). The re-verifier measured 3794 = 3694 + 87 + 13 at bcf75f84, so 3796 is the consistent target; F2-4's 89 omits the 13 fix-round-1 rows.

## 5. E3 targets pre-checked (read-only, nothing edited)
- "except the optional reset fields": exactly 1 occurrence, CLAUDE.md line 527 (the Build-3 identity and pins bullet).
- "still decides first (GC-2)": exactly 1 occurrence, line 526 (the Reset time bullet); "(GC-2)" occurs once in the file.
- Stated limit 4 = the 4th semicolon item of the row's Stated limits bullet (line 529): "the reset time is device-local (UAE / Oman read 01:00 for a Riyadh midnight), renders only once S81-09 sends it, and neither the sheet nor the pill re-renders when the instant passes;" (exactly 1 occurrence; the CLAUDE.md list is unnumbered, the numbering is the PR body's).

## 6. Gates
- G1: NOT MEASURED on committed bytes (no commit). Trial: 100 / 102 (G7, G7b red), section 1.
- G2: RV8a and RV8b KILLED by F2-1; MG1 KILLED by F2-2 (on the trial bytes); every restore sha-verified.
- G3 (the full suite), G4 (tsc, eslint, the hook on a commit), G5 (diff vs bcf75f84): NOT MEASURED (blocked before the commit; nothing to gate).
- No pytest this round: no [pyt] lines (none run). The hook test files tests/test_precommit_hook*.py: not run, as briefed.
- Tools by path: node v24.11.1, jest 29.7.0, typescript 5.9.3, eslint 9.39.4; the junction intact (node_modules/@babel/core and node_modules/.bin/jest present); node -e 0 = 3.4 s (the slow-spawn state); one jest at a time.

## 7. Footprint
- E0 list (29 files) and the end list are identical (cmp equal; <notes>/E0_footprint.txt, footprint_end.txt): this round adds and removes no file.
- git diff --check origin/main...HEAD clean (rc 0); numstat: no whole-file rewrite (only SmartCompareApp/__tests__/setup.ts 31/22 and src/services/deviceFingerprint.ts 171/37 exceed 20 deleted lines, earlier rounds' reviewed hunks).
- The 30-file backend comm record of fix round 1 restated unchanged (no byte moved this round; 2488 passed / 0 failed per the re-verifier).

## 8. PR body
NOT patched: no fix-round-2 commit exists, and patching it would claim a HEAD that was not observed. S81-08_fix1/PR_BODY.md unchanged: 22520 B, sha256 5cdb6e2a24042e8c35ae1090466a8f343f1a86195a785791403861035b99942a, 4 non-ASCII bytes (the attribution emoji).

## 9. Deviations
1. E1 measured in place and found to break two frozen RED rows (G7, G7b); E1-E4 not committed; the trial edits restored from the byte copies (sha-verified).
2. ALTB (an alternative guard, not in the brief) measured as an in-place trial for the ruling; not applied.
3. RV8c measured (beyond G2) to test F2-1's "kills RV8c": it survives.
4. E3 not applied (blocked before the commit); its targets pre-checked read-only (section 5).
5. PR body not patched (section 8).

## 10. End state
sc-s81-s08 HEAD bcf75f844d50ad11935a2512f77054d5a36ed4b3; git status --short EMPTY; .qa-mutation.lock created 14:30:51 and removed after the last restore (~14:44); the junction untouched; no package manager, no npx, no push, no commit, no git write in any worktree; no personal value written (synthetic statuses only). Notes in <notes> = C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/fe82d828-54b9-4af1-9c1d-685173488382/scratchpad/S81-08_fix2: notes.md, backup.py, before_sha.json, after_trial_sha.json, after_restore_sha.json, bytecopies/, trial_E1_E2.patch, jrun.sh, g_trial_red10.json / .log, mut.py, mut/*.json / *.log, mut/lines.txt, E0_footprint.txt, footprint_end.txt.
