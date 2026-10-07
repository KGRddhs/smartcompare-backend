# Session 73: paste-ready prompt

Written 2026-10-05 23:30 AST, before a scheduled PC shutdown at 00:40 (Ahmed's request). Open a new session in `C:\Users\SynAckITPC\Documents\AI`; the repo clone is `smartcompare` (never checkout, stash or reset in it; work in worktrees).

---

You are resuming the **MYEZ (ميّز) Apple launch lane** under `/synack-build-orchestrator`: Fable orchestrates, plans, gates and reviews; EVERY workflow agent is Opus (`model: 'opus'`; confirmed `claude-opus-5-5`); per unit: Opus spec -> Opus adversarial spec review -> Fable rulings -> Opus RED -> Fable gate -> Opus GREEN -> two Opus adversaries -> fix -> a final adversary on the exact bytes -> Fable diff review -> commit -> PR -> merge on 6 green checks. Identifiers still say `qaren`: never rename them.

## 0. Measure first
1. `mcp__ccd_session_mgmt__get_usage`: the weekly Fable limit was at 97 % on 2026-10-05 23:08 (resets 2026-10-07 16:00 AST). Below the reset: one workflow at a time, short turns.
2. `git -C C:/Users/SynAckITPC/Documents/AI/sc-docs-70 fetch` -> `git log origin/main --first-parent --oneline -3`. Expect `1156f03c` (#325, U8d). `/health` 200; anonymous `GET /api/v1/text/compare?q=...` = 401.
3. Read `docs/investigations/2026-10-05-session-72-state/ledger.md` (tail) and `IMPLEMENTATION_PLAN_S72.md`. The docs branch `docs/session-72-checkpoint` (worktree `sc-docs-70`) has an OPEN docs PR: merge it FIRST when its checks are green (it is clean under today's main; after T0b-B merges it would need a rebase, ruling TBF9).
4. Leftover processes and load: `Get-CimInstance Win32_Process | ? { $_.CommandLine -match 'pyt\.py|pytest|jest' }`; `time node -e 0` (it measured 2.4-5 s late on 2026-10-05: slow-spawn spikes).

## 1. T0b Phase B (secret scanning) - UNCOMMITTED in `sc-s71-t0b` (branch `feature/s72-t0b-b-secret-scan`, HEAD `845ece15`)
The round-2 workflow `wf_9d12c23d-cd9` (session id `2979ae70-049c-4e99-87ac-061e7d245fff`) was in its FINAL ADVERSARY when the PC shut down, and that adversary applies byte-copy mutants to the hook. **Before anything else re-hash the nine unit files against `C:/Users/SynAckITPC/Documents/AI/_s72_t0b_b_snapshot_fix2/SHA256SUMS.txt` (the exact bytes after fix round 2; hook `864d30e5...`). Any file that differs is a killed mutant or a half-finished edit: restore it from that snapshot folder by a byte copy and re-hash.** Then read the workflow journal (`~/.claude/projects/C--Users-SynAckITPC-Documents-AI/2979ae70-.../subagents/workflows/wf_9d12c23d-cd9/journal.jsonl`): a completed adversary result there is still valid for the fix-2 bytes; an unfinished one is re-run.

Rulings already made for the next fix round (pre-decided on 2026-10-05, from the fix-2 report; write them as TBF10-TBF13 in `specs/`):
- TBF10: `--no-color` on the hook's gitleaks call is accepted (without it 8.30.1 colours the level and the ` ERR ` test never matches).
- TBF11 (blocking class): the CI `secret-scan` step calls gitleaks without `--no-color`, so its ` ERR ` grep is fail-open: add `--no-color` there too, with a node that feeds a coloured log.
- TBF12: the new fail text `could not write the default-rules config for gitleaks` is accepted.
- TBF13: the 129-file batching node is accepted as the one node.
Still NOT MEASURED and owed before the commit: the full-file runs of the four hook test files with gitleaks STRIPPED from PATH (both shells); the real CI run of `secret-scan` (first on the PR; the mawk NUL canary: the pre-authorised fix is `tr -d '\000'` when the staged-diff views are written). Then: Fable reads the whole hook diff (`git diff -U2 --ignore-cr-at-eol .githooks/pre-commit`), re-runs the pin set and the hook files once, commits THROUGH THE NEW HOOK, opens the PR, merges on green. Spec set: `specs/T0B_PHASE_B_ADDENDUM.md`, `T0B_PHASE_B_REVIEW.md`, `FABLE_RULINGS_T0B_PHASE_B.md`, `FABLE_REVIEW_RED_T0B_PHASE_B.md`, `FABLE_RULINGS_T0B_PHASE_B_POST_ADVERSARY.md`; agent notes in the session-72 scratchpad `t0b_b/` (Temp; may be gone: the snapshot and the docs are the durable record).

## 2. Waiting for Ahmed (asked on 2026-10-05, unanswered at the close)
- Approval of seven NEW units (not in the session-71 plan): U3c (`store=False` on every OpenAI call + the referral push never uses an email prefix), BE-HARNESS (the canary script passes on a degraded 200; a signed-in warm-up script), U13e (`/url/detect` behind the admin guard; decision W0), CLIENT-TRUTH (the Share sheet's non-existent "Deep Review" reward and placeholder link, two placeholder lines, a medical-advice line, the clipboard read, #295, #239), DOCS-CONFIG (CLAUDE.md still tells agents to copy `.env`), COST-METER (#66), SSRF-PHARMACY (#79).
- The legal form `specs/U8_INPUT_FORM_AHMED.md` (+ review C17/C18/C20 additions: the exact legal name on the Apple membership, the IP licence, D14, a guardian/DPO).
- The decisions block: section D of `readiness/LAUNCH_PUNCH_LIST.md` + SHARE, MED, CLIP, TERR, W0, SMTP (plan section 6).
- Fund OpenAI + the NEW key on every Railway service that holds the name; a tester opens the app signed in (mobile Sentry has never shown an event); the 043 PRECHECK grid; the Apple session with Hussain (agreements, API key, app record -> the numeric Apple ID, `eas credentials`); the GitHub plan check; the deny rules (`apply_audit_batch_a.py --apply`); Sentry "Prevent Storing of IP Addresses" on both projects (U8d is live).

## 3. Next units when approved (two gate-heavy slots)
Slot A (backend): U3c -> BE-HARNESS -> U13e -> COST-METER -> SSRF-PHARMACY. Slot B: T0b-B finish -> CLIENT-TRUTH (in `sc-s70-u4b`, the only worktree with a real `node_modules`) -> U3b (after D3) -> U8 legal (RED/GREEN on placeholders on a branch; the fill-in and the merge wait for the inputs, 043 applied, U3b + U3c merged, sharing OFF confirmed). The U8 spec + 28 binding corrections and the U8d-derived policy sentence (ruling UF7) are in `specs/`. Step 6 structured review before the production build.

## 4. Rules carried forward (new this session)
- A final adversary on the exact bytes is mandatory after any fix round that changes production code; every fix round so far changed something the first adversaries had not seen.
- An adversary's mutation harness holds a MUTANT on disk between apply and restore: never snapshot, hash or stop a worktree while one runs without checking against the last completed report.
- Each new worktree whose file is opened with the Read tool injects its CLAUDE.md (about 86 K tokens): read worktree files with Bash `sed` / `grep`, and parse workflow results from the journal with a short Python script.
- Run `date` before writing any time; the Bash heredoc cannot carry apostrophes; never `cd` outside a subshell; the agent rules are `scripts/s72-common.txt`.
- Nothing flips in production without Ahmed's explicit word; Railway variables by NAME only; agents never touch Railway, Supabase, a real `.env` or the network.
