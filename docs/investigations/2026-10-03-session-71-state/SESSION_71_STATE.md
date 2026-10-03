# Session 71 — resume state (written 2026-10-03 ~07:57 AST, before context compaction; updated 10:27: section 0 is the resume checklist)

Read this file first after any compaction or in a new session. Everything here was measured or decided in session 71. Companion files in this folder: `IMPLEMENTATION_PLAN.md` (approved), `CONFIG_AUDIT_PLAN.md`, `RESEARCH_DIGEST.md`, `FABLE_REVIEW_RED_U4B.md`, `FABLE_REVIEW_RED_OAI.md`, `TRAFFIC_FINDING_2026-10-02.md`, `ledger.md`.

## 0. RESUME CHECKLIST (written 10:27, just before a context compaction) — do these in order

Main is `ca604e0a` (#285 OAI and #279 U4b merged and deployed, `/health` 200). OpenAI is still out of credits. Three workflows are running; their task notifications arrive as system messages. Liveness: list `~/.claude/projects/C--Users-SynAckITPC-Documents-AI/3ffde5dd-0e09-4243-bf73-02955e287dff/subagents/workflows/<run id>/` and read `journal.jsonl`.

1. **U13 `wf_8f9f3ab5-2fb` (task `w9mmqc053`)**: GREEN done, adversaries then fix. When it returns: sha-check `sc-s71-u13` against the fix report; read the diff (three route files + five scripts) and the UG1 test edit; fast-forward the worktree to main (`git merge --ff-only origin/main`; #285 touched none of its files) and re-run the two unit files + the G3 pin set through `pyt.py`; commit spec + tests + fixture + code (path-restricted, Co-Authored-By Claude Fable 5.1); push; `pr_rest.py create`; `bind_pr`; merge on 6 green checks; deploy check; file the follow-ups listed in the U13 section; hand Ahmed the activation runbook (rotate `ADMIN_API_KEY`, three flags in one window, anonymous re-probe = 401, THEN fund OpenAI).
2. **U4c `wf_00126194-212` (task `w24vy9enl`)**: GREEN done, adversaries then fix. When it returns: sha-check `sc-s70-u4b`; confirm exactly ONE `.snap` changed with sha `7d22d544…`; read the code diff; FULL jest once if anything was rebased; commit; PR; merge on green. The unit must be merged before the production build.
3. **U8b `wf_5e17b027-a1b` (task `w78pen5qg`)**: GREEN launched 10:24, then SQL/privacy + backend adversaries, then fix. When it returns: sha-check `sc-s71-u8b`; read migration 043, the rollback, the four `APPLY_043_*.sql` files and the backend diff; commit; PR; merge on green. Then Ahmed runs `APPLY_043_1_PRECHECK.sql` and sends its output BEFORE the one-paste.
4. **T0b**: the spec review is DONE (17 corrections in `sc-s71-t0b/docs/investigations/2026-10-03-session-71-state/T0B_REPO_TOOLING_SPEC.md`, sha256 `a3f9d86f…`). OWED: orchestrator rulings appended to that spec, then an Opus RED workflow (model the script on `scripts/wf_s71_u13_red.js`). The orchestrator must fetch and verify the gitleaks v8.30.1 linux_x64 checksum for the CI job (correction C5) and back up `.claude/settings.local.json` before untracking it (C12).
5. **Docs PR**: `docs/session-71-checkpoint` has no PR yet. Merge `origin/main` into it, add the CLAUDE.md edits (blocker #1 done by #279 with the in-app glyph in #280/U4c; the OAI lines: the `model_router_service` line, "all four AsyncOpenAI" → five, retire the #265 correction, the one-issue-per-template Sentry note; a short SESSION 71 Active-runtime block that points here), the runbook fresh-install note, then open the PR.
6. **Queue after that**: T0c CLAUDE.md contradiction fixes (Opus); U13c camera 401 refresh-and-retry (client); the #283 glyph unit (needs Ahmed to authorise two snapshot files); Step 6 structured code review (security / performance / complexity / dead code, Opus reviewers) once U13, U4c and U8b are merged; U3b / U8 / U10 gated on Ahmed.
7. **Load rule**: probe `node -e 0` before each launch; baseline 0.4-0.6 s; hold a gate-heavy launch above ~1.5 s (done once at 10:05).

**Audit batch A status (10:25):** on Ahmed's instruction the orchestrator applied the plugin and subagent-model part (`--apply --skip-deny`; backup `~/.claude/settings.json.bak-batchA-20261003-102535`). The 20 permission deny rules are NOT applied: permission rules are security settings and stay with the owner. Ahmed runs the script once with `--apply` (it now adds only the deny rules), then `claude mcp add railway --scope user -- cmd /c railway mcp`, `/plugin update context7`, `/mcp` for sentry and supabase, and starts a new session.

**Open decisions for Ahmed:** the three-flag U13 activation and the `ADMIN_API_KEY` rotation; the second old logo (#283); the three privacy defaults in migration 043 (audit-log IP nulled, consent timestamps erased, free quota resets on delete-and-re-register); repo private; D3, D5–D14; the eight legal inputs; testers opening the app; device checks before the production build.

**Lessons added today:** Bash heredoc bodies must not contain apostrophes on this box (write a script file with the Write tool instead); never `cd` outside a subshell; run `date` before writing any time; a spec reviewer's findings changed the design every time (U13 metering, U4c RTL mirror, U8b blocked deletions, T0b fail-open gitleaks): never skip the adversarial spec review.

## 1. Process (binding — Ahmed, 2026-10-03)
- Run under `/synack-build-orchestrator`. **Fable (main session) orchestrates, plans, reviews. EVERY agent is Opus** (`model: 'opus'` on every `agent()` and Agent call), in workflows.
- Per unit: Opus RED → **Fable gate on spec + tests** → Opus GREEN → two Opus adversaries → Opus fix → **Fable diff review** → gates → commit → PR → five required checks → merge. RED and GREEN are separate workflow launches.
- PRD = `docs/investigations/2026-09-29-session-69-state/APP_STORE_LAUNCH_RUNBOOK.md` + `…/2026-09-29-session-69-state.md`. Scope additions need Ahmed's call.
- GitHub through `harness/pr_rest.py` / `issue_rest.py` (repo `KGRddhs/smartcompare-backend`; `gh` dies on this box). Never poll CI in a loop; read status once when re-invoked. PRs #285, #279, #278 and #277 are merged; bind each new PR to the app PR monitor (`bind_pr`, then `get_status`).
- Nothing flips in production without Ahmed's explicit word. Railway variables by NAME only. Never print secrets.

## 2. Where things are
- **main `ca604e0a`** = #285 (OAI/obs, merged 10:02) on `eb86075e` = #279 (U4b, merged 08:28) on `4bd5a09f` = #278 (`5ed4f459`: `pyjwt 2.15.1`, `urllib3 2.8.0`, pip-audit clean) + #277 (session-70 docs + both specs with rulings). Railway `web` deployment `491ee9b0` SUCCESS on `4bd5a09f`. `/health` 200. **OpenAI still 429 `credit_balance_exhausted`.** Serper 200, Firecrawl 1,025, Scrape.do 1,000/1,000.
- **Docs branch** `docs/session-71-checkpoint` (worktree `sc-docs-70`), pushed; this folder lives there. No PR opened yet — open one at the next checkpoint.
- **Scratchpad** (session-temporary): `C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/3ffde5dd-0e09-4243-bf73-02955e287dff/scratchpad` — `harness/` (`pyt.py`, `stall_monitor.py` STOPPED at 08:04 when its 2-hour background limit ended; not restartable, so check agent liveness by hand from the workflow journals at each re-invocation, `pr_rest.py`, `issue_rest.py`, `ci_logs.py`, `active_workflows.txt`), `s70-common.txt` (agent rules), `wf_s71_*.js` (workflow scripts), `snap_pre_ff/` (byte copies of RED files), `traffic/` (Railway HTTP + app logs), `ledger_s71.md`.
- Pinned venv `C:/Users/SynAckITPC/Documents/AI/.venv-qaren` matches the new lock.
- Sentry: the claude.ai Sentry connector works in this session (tools `mcp__25c88de3-88e5-44ab-a39d-7940ee213870__*`; org `qaren-rr`, `regionUrl https://de.sentry.io`; projects `react-native` and `python-fastapi`).

## 3. Units in flight

### U4b — MERGED 08:28 as PR #279 → main `eb86075e` (commit `de66a25f`)
- Gates, adversaries, the fix and the orchestrator review are in the PR body (`pr/PR_279_U4B_BODY.md`) and the ledger. Follow-up issues: #280 (U4c), #281 (RQ5 icon variants + Android splash sizing), #282 (CI `render_myez_icons.py --check`, splash-position and toggle pins).
- Railway `web` deployment `e3ef5cfb` was BUILDING for `eb86075e` at 08:29: verify SUCCESS and `/health` 200 at the next re-invocation.
- Owed in the docs PR: the CLAUDE.md blocker #1 line (launcher art done; the in-app glyph is #280) and the runbook fresh-install note (a phone that had the old build can show the cached launch screen until reinstall).
- Worktree `sc-s70-u4b` is KEPT: it has a real `node_modules` that matches the new lock, and U4c is built in it on a new branch from main. The U4c spec agent measures in it read-only.

### OAI/observability — MERGED 10:02 as PR #285 → main `ca604e0a` (deployed, `/health` 200)
- #265 and #268 closed; follow-ups #286, #287 filed; worktree removed. PR body copy: `pr/PR_285_OAI_BODY.md`.
- Still owed: the CLAUDE.md lines in the docs PR (the `model_router_service` line, "all four AsyncOpenAI" → five, retire the #265 correction, the one-issue-per-template Sentry note); the Sentry check once real compares produce events at the eight sites.

### U13 — paid routes require a caller; GREEN running: `wf_8f9f3ab5-2fb` (task `w9mmqc053`, script `scripts/wf_s71_u13_green.js`, launched 09:21)
- Worktree `sc-s71-u13` (branch `feature/s71-u13-compare-auth-required`, HEAD `eb86075e`). Spec in that worktree (untracked until the unit commit; sha256 `df62ebe3…`): body + corrections C1–C11 + rulings UR1–UR15 + the RED gate UG1–UG6 (copies: `FABLE_RULINGS_U13.md`, `FABLE_REVIEW_RED_U13.md`).
- RED (Opus, `wf_9712c249-8c5`) gated PASS 09:20: `tests/test_s71_u13_compare_auth_required.py` `1849dbfe…`, `tests/test_s71_u13_harness_auth.py` `eb33a12d…`, fixture `fa72e28f…`; 85 RED / 74 PIN. UG1: GREEN first narrows T23 to the `$ref` closure of the ten operations (the only allowed test edit).
- Design: flag `ENABLE_COMPARE_AUTH_REQUIRED` (default OFF, per call); `require_paid_route_user` on the six app routes, `require_paid_route_admin` on the four routes with no caller; harness scripts send `X-Admin-Key` only under `HARNESS_SEND_ADMIN_KEY`; flag OFF byte-identical.
- **Activation is Ahmed's and is THREE flags in one window, before funding OpenAI:** `ENABLE_COMPARE_AUTH_REQUIRED`, `ENABLE_PAID_ROUTE_METERING`, `ENABLE_CAMERA_FAILURE_ENVELOPE`; precondition: rotate `ADMIN_API_KEY`. Residual: free-tier credits of self-registered accounts.
- **Then (orchestrator):** sha-check against the fix report; Fable diff review; commit (spec + tests + code); PR; CLAUDE.md flag row and curl/Serper-probe notes at merge (R14); file the follow-ups (U13c camera retry, per-user limiter key, live tests that will 401, raw query logging, multipart parse before the guard, smoke accounts); deploy check; hand Ahmed the runbook.

### U4c — in-app MYEZ mark; GREEN running: `wf_00126194-212` (task `w24vy9enl`, script `scripts/wf_s71_u4c_green.js`, launched 09:44)
- Worktree `sc-s70-u4b`, branch `feature/s71-u4c-inapp-mark` from `eb86075e` (real `node_modules`). Spec in that worktree (untracked until the unit commit; sha256 `ee3ebb39…`): body + 12 corrections + rulings UR1–UR15 + the RED gate UG1–UG5 (copies: `FABLE_RULINGS_U4C.md`, `FABLE_REVIEW_RED_U4C.md`).
- RED (Opus, `wf_1819c70c-1f2`) gated PASS 09:44, no change: six test files (prefixes `d9241b8c`, `c23f00d8`, `061dfb08`, `ca1d7280`, `4993e2cf`, `85bfc54f`), 27 REDs. GREEN target: 354 suites, 3473 passed / 3499 total, 44 snapshots, after the ONE authorised `jest -u` on the LoadingRings file (expected `.snap` sha `7d22d544…`).
- OUT, issue #283: the `QaranIcon` Q-magnifier in the winner reveal and the text-only logos on ForgotPassword/Register. Device checks owed before the production build: white gap before the first JS frame, one-frame image decode, 2 pt Home header shift, the Arabic hand-off.
- **Then (orchestrator):** sha-check, read the snapshot diff and the code diff, commit (spec + tests + code + assets + manifest), PR, FULL jest only if a rebase is needed, merge on green.

### U8b — account deletion erases everything; GREEN running: `wf_5e17b027-a1b` (task `w78pen5qg`, script `scripts/wf_s71_u8b_green.js`, launched 10:24)
- Worktree `sc-s71-u8b` (branch `feature/s71-u8b-account-deletion`, HEAD `ca604e0a`). Spec in that worktree (untracked until the unit commit; sha256 `848afcbb…`): body + corrections C1–C14 + rulings UR1–UR15 + the RED gate UG1–UG6 (copies: `FABLE_RULINGS_U8B.md`, `FABLE_REVIEW_RED_U8B.md`).
- RED frozen: `tests/test_migration_043_delete_user_cascade.py` `4f8d7dad…`, `tests/test_account_deletion_u8b.py` `846f34e8…`; 35 RED / 26 PIN; copies in scratchpad `u8b/red_frozen`.
- Privacy defaults Ahmed may change before applying 043: audit-log IP nulled (rows kept), consent columns erased, free quota resets on delete-and-re-register. Follow-ups to file at merge: the client's `@qaren_recent_searches`; an audit-log retention window. Issue #284 (the `governorate` readers) is already filed.

### T0b — repo tooling (audit batch C); spec review DONE 10:25, ORCHESTRATOR RULINGS OWED
- Worktree `sc-s71-t0b` (branch `feature/s71-t0b-repo-tooling` from `eb86075e`; fast-forward to main before RED). Spec + 17 binding corrections in the worktree (sha256 `a3f9d86f…`); the headline corrections are in the ledger line of 10:25. `.mcp.json` stays unchanged until Ahmed applies the deny rules and adds the user-scope Railway server.

## 4. Queue (after the above)
1. **U4c** in-app MYEZ mark (after U4b merges; a stopped agent left notes + a prototype in scratchpad `u4c/`). Ahmed approved: drop the app-name text beside the mark; splash mark starts at the launch position and full opacity; ONE `jest -u` on the `LoadingRings` snapshot file with a reviewed diff. Keep the `QarenLogo.tsx` path; RN `Image` with `@1x/@2x/@3x` PNGs from the U4b renderer.
2. **U8b** fix `delete_user_cascade` to null demographics/display name/email (+ a migration Ahmed applies) — approved.
3. **T0b** repo tooling PR (gitleaks + staged-blob lint + eslint + skill-YAML check in pre-commit, CI gitleaks job, fix `qaren-eas-deploy` and `qaren-referrals` frontmatter, untrack `.claude/settings.local.json`, Railway dedupe in `.mcp.json`) and **T0c** CLAUDE.md contradiction fixes — audit batch C approved. Large CLAUDE.md restructure after Milestone 1.
4. **Audit batch A** (approved): global `~/.claude/settings.json`. Verified mechanics: `permissions.deny` IS enforced in bypass mode and for subagents, edits apply to the running session; syntax `Bash(railway variables *)`, exact MCP tool names, `Read(//**/.env)` + `Read(//**/.env.*)`, `PowerShell(...)` rules valid; `CLAUDE_CODE_SUBAGENT_MODEL=opus` (+ `CLAUDE_CODE_SUBAGENT_MODEL_FORCE=1`, build 2.1.286 supports it) in the `env` block; `enabledPlugins: {"<name>@<marketplace>": false}` takes effect in a new session. Today the file has NO `permissions` block, 13 plugins enabled, `env` = `DISABLE_AUTOUPDATER` only. Because permission rules are a security setting, prepare a small apply script (backup + merge) and have Ahmed run it; do not edit his security settings directly. **Apply script written 08:17: `scripts/apply_audit_batch_a.py` (dry run verified: 29 changes = 20 deny rules, 7 plugins off, 2 env; idempotent; `--apply` makes a backup; `--restore` undoes). Ahmed runs it; no agent does. Refinement: plain `git push --force` / `-f` denied, `--force-with-lease` kept for the rebase flow.**
5. **Step 6 structured code review** (security / performance / complexity / dead code, Opus reviewers) after Milestone 1 merges and again before the production build.
6. Batch D housekeeping after the launch lane. Batch B is Ahmed's.
7. Gated on Ahmed: **U3b** (D3; consent withdrawal control now in scope), **U8** (8 legal inputs + D3 + D5; response times 10/15 working days; no Beta label), **U10** (ASC app id; option A block, validate with the resolved submit schema).

## 5. Ahmed's decisions recorded today
PRD = runbook + session-69 audit · GitHub issues via the REST helper · keep U4b's RED · merge #278 on green · plan approved · audit batches A, C, D (D after launch) · U4c design ×3 · legal ×4 (10/15 working days, no Beta label, withdrawal control in U3b, fix deletion in code) · burst = "not sure" · U13 before funding OpenAI · he makes the repo private himself (check first: a private repo on a GitHub Free plan loses branch protection and uses Actions minutes).

## 6. Still Ahmed's
Make the repo private · OpenAI top-up + D8 (prepaid, low cap, until U13's flag is on) + NEW key into Railway `web` (after U13) · read the OpenAI tier / data-sharing enrolment / Chat Completions storage default · D3, D5–D14 · the 8 legal inputs · Supabase paid plan + `qaren://reset-password` · attach `qaren.app` · **testers must open the app** (77 h of prod logs show zero mobile requests; Sentry `react-native` has 0 errors and 0 spans in 30 days, so mobile reporting is still unmeasured) · ASC session with Hussain · demo account, warm-up pairs, screenshots · audit batch B · run the batch-A apply script when offered.

## 7. Lessons added this session
- A killed or stopped agent's files are unverified until re-hashed and re-run; after any stop: orphan check, sha snapshot, clear `active_workflows.txt`.
- `git merge --ff-only origin/main` moves a dirty unit worktree to a new main when main's changes do not touch the dirty files; remove sha-identical untracked copies first.
- `expo install --check` rewrites `package.json` in an interactive TTY; use `CI=1`.
- Read the production HTTP log before trusting a funding plan: the limiter did not stop 51 requests a minute.
