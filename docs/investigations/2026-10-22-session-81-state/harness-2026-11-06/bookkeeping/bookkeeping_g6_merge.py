import datetime, io, os, re
D = "C:/Users/SynAckITPC/Documents/AI/sc-docs-70/docs/investigations/2026-10-22-session-81-state"
os.chdir(D)
ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
MAIN = "00e4120d"

def rw(path, fn):
    t = io.open(path, encoding="utf-8").read()
    t2 = fn(t)
    io.open(path, "w", encoding="utf-8", newline="\n").write(t2)

# DEFECT_LEDGER: the CL2 row status
def f_defect(t):
    n = len(re.findall(r"\| spec reviewed \(RULINGS_S81_G6, [^)]*\); RED running \|", t))
    assert n == 1, "CL2 row status not found once: %d" % n
    return re.sub(r"\| spec reviewed \(RULINGS_S81_G6, [^)]*\); RED running \|",
                  "| MERGED #387 2026-11-05 06:17 (main %s; HEAD a93b0153: GREEN ab4b3b31 + the final-round commit; 58 nodes, 25 + 38 mutants, the full jest 3,852 + the four w37 drift nodes) |" % MAIN, t)
rw("DEFECT_LEDGER.md", f_defect)

# PLAN_STATUS: the Finished row after the S81-16b row + a dated line at the end
row = ("| CL2 CLIENT-SPEED (G6 CLIENT-PERF, client) | #387 | 2026-11-05 06:17 | NO runtime flag (a client unit: merges now, SHIPS ONLY in the OTA with the first KB-first canary, after the first review-safe OTA; the OTA step runs npm ls / npm ci first): the Home floor through src/utils/clientSpeed.ts (under 300 ms renders now, else the 400 ms floor; the A17 rule), the 800 ms reveal cut ONLY on a measured fast hit (the additive Results route param fastHit from Home when the response landed within 300 ms; history / camera / slow compares keep 800), Image.prefetch of the two product images (src/services/imagePrefetch.ts: https only, two, fire-and-forget, FIFO dedupe 32), the History SWR cache (src/services/swrCache.ts: per user, a 30 s focus throttle, invalidated on every Results mount and on delete, cleared through ONE App.tsx effect keyed on the user id; Home NOT cached: the quota pill refetch), getSentryExpoConfig(includeWebReplay false) composed with qarenCacheVersion in metro.config.js (the export shrank 6,594,787 -> 6,355,018 B), five lazy screens through src/navigation/lazyScreen.tsx with a themed fallback (Onboarding, NewOnboardingHost, ScanCamera, InviteeQuiz, ReferralLanding; Legal and Paywall stay eager), getStableId started before the language read, freezeOnBlur on the tabs; stated limits CL2-L1..L6; SS1 + CL5 = G6b after owner item 19 (#118), the Geist drop = CL2b after the TestFlight device check; main %s |\n") % MAIN
def f_plan(t):
    anchor = "\n| S81-16b KB-BRANDS (FOCUS) |"
    i = t.find(anchor)
    assert i >= 0, "S81-16b row not found"
    j = t.find("\n", i + 1)
    t = t[:j + 1] + row + t[j + 1:]
    t = t.rstrip("\n") + ("\n- %s FINISHED: G6 CLIENT-PERF (CL2 CLIENT-SPEED; the first CLIENT group under LC-9) merged as PR #387 (main %s; 30 files, no backend file). Lesson recorded from the G5 adversary MAJ-1: the CLAUDE.md readers include the gate-rows files that import a reader's constant (tests/test_s81_s08b_gate_rows.py through test_s81_s08b_legacy_fingerprint.py): list them by the import graph. In flight: the G5 LEARN-SEARCH (D22) FINAL round replaying onto %s (RULINGS_REBASE_S81_G5); then its PR, merge and bookkeeping; then NEXT_SESSION_PROMPT_S85.md at the clean point. S81-12 draft PR #378 HELD.\n") % (ts, MAIN, MAIN)
    return t
rw("PLAN_STATUS_S81_2026-10-24.md", f_plan)

# s81-common: the MOVING MAIN line
mm = ("- MOVING MAIN 2026-11-05 06:17: origin/main = %s (#387 S81-G6 CLIENT-PERF = CL2 CLIENT-SPEED merged 06:17: a CLIENT unit, no runtime flag, ships only in the OTA with the first KB-first canary; 30 files: NEW SmartCompareApp/src/utils/clientSpeed.ts, src/services/swrCache.ts, src/services/imagePrefetch.ts, src/navigation/lazyScreen.tsx and the thirteen files under SmartCompareApp/__tests__/cl2/ (the twelve frozen RED files + gateRows.cl2.test.tsx); EDITED SmartCompareApp/App.tsx (five lazy bindings, the setSwrUser effect, the parallel getStableId read, freezeOnBlur), metro.config.js (getSentryExpoConfig with includeWebReplay false composed with qarenCacheVersion), src/screens/HomeScreen.tsx, ResultsScreen.tsx, HistoryScreen.tsx, src/types/types.ts (the additive Results param fastHit), the six E-row test files (metro.cacheVersion.pb1, HomeScreen.bundleB.contract, HomeScreen.eS3hf.dedupe, HomeScreen.eS3hf.loaderVisibility, ResultsEntryParams.a18, HomeScreen.minDisplayFloor), CLAUDE.md (the S81-G6 block after the S81-G4 owner-steps bullet)). NO app/, scripts/, migrations/ or tests/*.py file: every backend base record (the stored ec747b49 record c636b9d5... 46 files, the e1491c97 and 0b19de5b records) stays reusable PER FILE for members that reference no SmartCompareApp/ file nor CLAUDE.md and are not glob walkers (GC-9); the CLAUDE.md readers and the SmartCompareApp-scanning backend tests need a base re-run at %s. CLAUDE.md READERS (the G5 adversary MAJ-1 lesson, 2026-11-05): beside tests/test_ci_gates.py and test_behavior_dimension_translation.py the set holds test_s81_s04_spend_breaker.py, test_s81_s08b_legacy_fingerprint.py, test_s81_s08b_gate_rows.py (it imports the reader's CLAUDE_MD constant) and test_s81_s23_bypass_retire.py: derive the set by the import graph, never by a grep for the literal alone. The full jest baseline is now 3,852 passed + the four config/nativeBundle.w37 drift nodes.\n") % (MAIN, MAIN)
with io.open("scripts/s81-common.txt", "a", encoding="utf-8", newline="\n") as fh:
    fh.write(mm)

# ledger
line = ("- %s G6 CLIENT-PERF (CL2) MERGED: PR #387 merged 06:17 (7 / 7 green, mergeable_state clean; `pr_rest.py merge 387`) -> origin/main %s (the merge commit of a93b0153 on ec747b49; 30 files, 2,445 insertions / 37 deletions: the four new client leaves, the thirteen cl2 test files, App.tsx, metro.config.js, the three screens, src/types/types.ts, the six E-row suites, CLAUDE.md). A client unit with no runtime flag: nothing changes in production until the OTA with the first KB-first canary (after the first review-safe OTA; npm ls / npm ci first). Bookkeeping: DEFECT_LEDGER CL2 -> MERGED; PLAN_STATUS Finished row + the dated line (+ the CLAUDE.md-reader lesson); the MOVING MAIN line in scripts/s81-common.txt (the 30 files, the base-record reuse rule, the reader set, the jest baseline 3,852); memory. The sc-s81-g6 junction unlinked with [System.IO.Directory]::Delete (the clone's node_modules/@babel/core verified) and the worktree removed. NEXT: `git merge-tree --write-tree --name-only %s 53b7b66e` for the G5 replay, get_usage + the node probe, the G5 FINAL round (RULINGS_REBASE_S81_G5; args <scratchpad>/S81-G5_final_args.json), its PR via pr_rest.py, merge on 7 / 7 green, bookkeeping, then NEXT_SESSION_PROMPT_S85.md at the clean point." % (ts, MAIN, MAIN))
with io.open("ledger.md", "a", encoding="utf-8", newline="\n") as fh:
    fh.write(line + "\n")

# memory
M = "C:/Users/SynAckITPC/.claude/projects/C--Users-SynAckITPC-Documents/memory/project-myez-session84-resume-2026-11-05.md"
t = io.open(M, encoding="utf-8").read()
t = t.rstrip("\n") + ("\n\n**Update %s AST:** PR #387 (G6 CLIENT-PERF = CL2) MERGED at 06:17 -> main %s (30 client files + CLAUDE.md, no backend file; ships only in the post-approval OTA); sc-s81-g6 retired (junction unlinked, worktree removed); the bookkeeping done. In flight next: the G5 (D22) FINAL round replaying 53b7b66e onto %s (CLAUDE.md both-sides-added union; args <scratchpad>/S81-G5_final_args.json), then its PR (`pr_rest.py create feature/s81-g5-learn-search ...`), merge, bookkeeping, and NEXT_SESSION_PROMPT_S85.md at the clean point.\n") % (ts, MAIN, MAIN)
io.open(M, "w", encoding="utf-8", newline="\n").write(t)
print("bookkeeping done", ts)
