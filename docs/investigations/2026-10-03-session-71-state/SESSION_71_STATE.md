# Session 71 — resume state (written 2026-10-03 ~08:25 AST, before context compaction)

Read this file first after any compaction or in a new session. Everything here was measured or decided in session 71. Companion files in this folder: `IMPLEMENTATION_PLAN.md` (approved), `CONFIG_AUDIT_PLAN.md`, `RESEARCH_DIGEST.md`, `FABLE_REVIEW_RED_U4B.md`, `FABLE_REVIEW_RED_OAI.md`, `TRAFFIC_FINDING_2026-10-02.md`, `ledger.md`.

## 1. Process (binding — Ahmed, 2026-10-03)
- Run under `/synack-build-orchestrator`. **Fable (main session) orchestrates, plans, reviews. EVERY agent is Opus** (`model: 'opus'` on every `agent()` and Agent call), in workflows.
- Per unit: Opus RED → **Fable gate on spec + tests** → Opus GREEN → two Opus adversaries → Opus fix → **Fable diff review** → gates → commit → PR → five required checks → merge. RED and GREEN are separate workflow launches.
- PRD = `docs/investigations/2026-09-29-session-69-state/APP_STORE_LAUNCH_RUNBOOK.md` + `…/2026-09-29-session-69-state.md`. Scope additions need Ahmed's call.
- GitHub through `harness/pr_rest.py` / `issue_rest.py` (repo `KGRddhs/smartcompare-backend`; `gh` dies on this box). Never poll CI in a loop; read status once when re-invoked. Session is bound to PR #278 (merged).
- Nothing flips in production without Ahmed's explicit word. Railway variables by NAME only. Never print secrets.

## 2. Where things are
- **main `4bd5a09f`** = #278 (`5ed4f459`: `pyjwt 2.15.1`, `urllib3 2.8.0`, pip-audit clean) + #277 (session-70 docs + both specs with rulings). Railway `web` deployment `491ee9b0` SUCCESS on `4bd5a09f`. `/health` 200. **OpenAI still 429 `credit_balance_exhausted`.** Serper 200, Firecrawl 1,025, Scrape.do 1,000/1,000.
- **Docs branch** `docs/session-71-checkpoint` (worktree `sc-docs-70`), pushed; this folder lives there. No PR opened yet — open one at the next checkpoint.
- **Scratchpad** (session-temporary): `C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/3ffde5dd-0e09-4243-bf73-02955e287dff/scratchpad` — `harness/` (`pyt.py`, `stall_monitor.py` running as bash task `b0j75pvg6` until ~13:05, `pr_rest.py`, `issue_rest.py`, `ci_logs.py`, `active_workflows.txt`), `s70-common.txt` (agent rules), `wf_s71_*.js` (workflow scripts), `snap_pre_ff/` (byte copies of RED files), `traffic/` (Railway HTTP + app logs), `ledger_s71.md`.
- Pinned venv `C:/Users/SynAckITPC/Documents/AI/.venv-qaren` matches the new lock.
- Sentry: the claude.ai Sentry connector works in this session (tools `mcp__25c88de3-88e5-44ab-a39d-7940ee213870__*`; org `qaren-rr`, `regionUrl https://de.sentry.io`; projects `react-native` and `python-fastapi`).

## 3. Units in flight

### U4b — icons + Expo SDK 54 bumps + gesture-handler removal + CI split (worktree `sc-s70-u4b`, own `node_modules`, HEAD `4bd5a09f`, uncommitted)
- Workflow `wf_053464cc-8cd` (task `w3l90g4cx`, script `wf_s71_u4b_green.js`): **GREEN DONE** (all gates green: W3-7 file 58/58; full jest 351 suites / 3,448 passed / 13 skipped / 13 todo / 44 snapshots; tsc + eslint clean, 148 warnings before and after; offline `expo install --check` exit 0; renderer deterministic, outputs sha-equal to the session-70 prototype; G11 178 passed). Two adversaries (app-review, engineering) running since 07:38; a fix round follows if they find anything.
- GREEN shas: `package.json` `ffa73b00…`, lock `42497207…`, `icon.png` `2530d5b3…`, `adaptive-icon.png` `b336b66b…`, `splash-icon.png` `bf8df272…`, `favicon.png` `3d225c46…`, test `c73ee369…` (RED `9225b396…` + RQ19 name trims), helper `004cebe9…`, renderer `8b388402…`, manifest `879941db…`, `ci.yml` `82896656…`.
- Resolved versions = the ruled nine (expo 54.0.37, expo-font 14.0.12, expo-localization 17.0.9, expo-screen-capture 8.0.10, expo-updates 29.0.20, expo-file-system 19.0.24, expo-constants 18.0.14, babel-preset-expo 54.0.12, @expo/metro-config 54.0.17); `@expo/cli` 54.0.27, `@expo/prebuild-config` 54.0.9 (legacy splash path still holds), eslint-config-expo 10.0.0.
- **Open orchestrator ruling:** a DUPLICATE `expo-constants` (root 18.0.13 + `expo/node_modules` 18.0.14; delta is an Android gradle file only). Expected ruling RQ22: run `npm dedupe` in `sc-s70-u4b/SmartCompareApp`, then re-run P8, the offline check, G6, G7, G9, `npm ls --all`. Decide after the adversaries report.
- **Then (orchestrator):** sha-check every file against the last report; Fable diff review; `CI=1 npx expo install --check` ONLINE and `npx expo-doctor` in the worktree; commit (`git commit -m … -- <paths>` incl. the spec addendum); push; PR via `pr_rest.py` (body: the nine versions, correction 4's executable rule, "pixel-equivalent not byte-identical", favicon web-only, limits); FULL jest after any rebase; merge on green; file follow-ups (U4c; Android/iOS icon variants + legacy Android splash size).

### OAI/observability — #265, #268, 8 log sites, gather future (worktree `sc-s70-oai`, HEAD `4bd5a09f`, uncommitted)
- RED DONE by Opus (`wf_15d14c45-c54`), Fable gate PASS. Test shas: url `107b7b79…`, exc_summary `b714ba46…`, prefetch `2c9e279b…`, router `f905b305…`; 116 nodes = 60 RED / 56 PIN.
- GREEN workflow `wf_31aee254-a83` (task `wx03kqwr4`, script `wf_s71_oai_green.js`): green → correctness + regression adversaries → fix. Started 07:40.
- **Then (orchestrator):** sha-check; Fable diff review; Railway `web` variable NAMES check that `DAILY_4O_CAP` is absent (C7); commit; PR (pr_text from the report; no contextvar rationale); at merge edit CLAUDE.md (the `model_router_service.py` line ~169, "all four AsyncOpenAI" → five ~351, retire the #265 correction ~352 with a dated line — re-anchor by text); file follow-ups (`cache_service._redis_get` empty-text ERROR log; discovery prefetch Task noise; #226 stays); after deploy check Sentry: one accumulating issue per template titled `<prefix><TypeName>`, then resolve the old per-text issues.

### U13 — paid compare routes require an authenticated user (NEW; gates the OpenAI top-up; worktree `sc-s71-u13`, branch `feature/s71-u13-compare-auth-required`)
- Why: `TRAFFIC_FINDING_2026-10-02.md` — 322 anonymous `/text/compare` calls from 155 rotating datacenter IPs on 2026-10-02, 51/min peak, no 429; the repo is public. Ahmed: "not sure" it was his → treat as third-party; **build U13 first, then fund OpenAI**.
- Spec + adversarial review workflow `wf_b52ebf22-121` (task `ws092cf7t`) launched 08:27 (script `wf_s71_u13_spec.js`; copies of every session-71 workflow script and the agent rules are in this folder's `scripts/`; spec path `sc-s71-u13/docs/investigations/2026-10-03-session-71-state/U13_COMPARE_AUTH_SPEC.md`). Then: Fable rulings → Opus RED → gate → GREEN → adversaries → diff review → PR → deploy → smoke → **Ahmed sets the flag** → anonymous re-probe = 401 → only then the top-up.
- Design intent: ONE default-OFF flag (suggested `ENABLE_COMPARE_AUTH_REQUIRED`), a single dependency refusing anonymous callers with 401 `AUTH_REQUIRED` before any provider work/metering/log write; an explicit credential for the repo's own harness scripts; expired bearer = a 401 the client refreshes on; flag OFF byte-identical.

## 4. Queue (after the above)
1. **U4c** in-app MYEZ mark (after U4b merges; a stopped agent left notes + a prototype in scratchpad `u4c/`). Ahmed approved: drop the app-name text beside the mark; splash mark starts at the launch position and full opacity; ONE `jest -u` on the `LoadingRings` snapshot file with a reviewed diff. Keep the `QarenLogo.tsx` path; RN `Image` with `@1x/@2x/@3x` PNGs from the U4b renderer.
2. **U8b** fix `delete_user_cascade` to null demographics/display name/email (+ a migration Ahmed applies) — approved.
3. **T0b** repo tooling PR (gitleaks + staged-blob lint + eslint + skill-YAML check in pre-commit, CI gitleaks job, fix `qaren-eas-deploy` and `qaren-referrals` frontmatter, untrack `.claude/settings.local.json`, Railway dedupe in `.mcp.json`) and **T0c** CLAUDE.md contradiction fixes — audit batch C approved. Large CLAUDE.md restructure after Milestone 1.
4. **Audit batch A** (approved): global `~/.claude/settings.json`. Verified mechanics: `permissions.deny` IS enforced in bypass mode and for subagents, edits apply to the running session; syntax `Bash(railway variables *)`, exact MCP tool names, `Read(//**/.env)` + `Read(//**/.env.*)`, `PowerShell(...)` rules valid; `CLAUDE_CODE_SUBAGENT_MODEL=opus` (+ `CLAUDE_CODE_SUBAGENT_MODEL_FORCE=1`, build 2.1.286 supports it) in the `env` block; `enabledPlugins: {"<name>@<marketplace>": false}` takes effect in a new session. Today the file has NO `permissions` block, 13 plugins enabled, `env` = `DISABLE_AUTOUPDATER` only. Because permission rules are a security setting, prepare a small apply script (backup + merge) and have Ahmed run it; do not edit his security settings directly.
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
