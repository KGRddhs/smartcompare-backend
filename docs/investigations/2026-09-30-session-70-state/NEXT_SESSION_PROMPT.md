# Session 71: paste-ready prompt

Written at the session-70 pause on 2026-09-30 (~06:15 AST); main `94c097cd` plus this docs PR (branch `docs/session-70-checkpoint`). Open a new session in `C:\Users\SynAckITPC\Documents\AI`; the repo clone is `smartcompare/`. Paste everything under the line.

---

You are resuming the **MYEZ (ميّز) Apple launch lane**. Identifiers still say `qaren` (bundle id `com.qaren.app`, slug, `qaren://`, EAS project, Sentry org `qaren-rr`, `@qaren_*` keys, `qaren.app` addresses) — never rename them. Session 70 paused at the model usage limit with two units specified and reviewed but not built. **Ask Ahmed which of his items (§5) are done before starting a gated unit.**

## 0. Measure first (the repo wins over this prompt)
1. `git -C C:/Users/SynAckITPC/Documents/AI/smartcompare fetch` → `git log origin/main --oneline -5`. Expect `94c097cd` + the session-70 docs merge. Read anything newer first.
2. `curl -s https://web-production-58776.up.railway.app/health` (200 "MYEZ API is running" at the pause). Provider state: `railway run -s web python docs/investigations/2026-09-30-session-70-state/scripts/probe_providers.py` (status only; spends 1 Serper credit + a 1-token OpenAI call). At the pause OpenAI was 429 `credit_balance_exhausted`.
3. `git worktree list`: `sc-s70-u4b` (REAL node_modules, not a junction), `sc-s70-oai`, and `sc-docs-70` (remove after its PR merged; no junction).
4. Leftover processes: `Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'stall_monitor|pyt\.py|pytest|jest' }`.

## 1. Read, in this order
1. `CLAUDE.md` → the ship-blockers block, then `## Active runtime (SESSION 70 …)`, then SESSION 69.
2. `docs/investigations/2026-09-30-session-70-state.md` (what was done, measured, the partial RED files with sha256 prefixes, rulings owed).
3. The two specs in `docs/investigations/2026-09-30-session-70-state/` — `U4B_ICONS_DEPS_SPEC.md` and `OAI_OBS_SPEC.md` — **each ends with a BINDING review-corrections section that supersedes its body.**
4. `docs/investigations/2026-09-29-session-69-state/NEXT_SESSION_PROMPT.md` §4 (U3b / U8 / U10 preconditions), §6 (binding rules) and §7 (Ahmed's items) — still valid except what §5 below marks done.

## 2. First work: rule, then resume the two units from RED
1. Append `## Orchestrator rulings (BINDING)` to each spec. Recommended (session-70 orchestrator, not yet ruled): U4b Q1 ALIGN eslint-config-expo to ~10.0.0; Q2 KEEP `expo.version` 1.0.0 with review correction 4's executable rule; Q3 split CI (blocking `EXPO_OFFLINE=1 npx expo install --check` + report-only online step); Q4 file U4c (the JS splash and Home/Profile/History/onboarding/LoadingRings still render the old `QarenLogo` Q-ring — do it before the review build); Q5 follow-ups; Q6 `scripts/render_myez_icons.py`. OAI OQ1 set `metadata.model_downgraded` for both the cap and the 429 fallback (add a reason field only if cheap); OQ2 accept (document); OQ3 YES (binding already); OQ4 yes; OQ5 at merge; OQ6 Ahmed.
2. **Before RED resumes, sync the spec copies:** main now carries both specs at the same paths as the untracked copies in the unit worktrees. sha-compare; if equal, delete the worktree copy before rebasing; if the worktree copy is newer, keep it and commit it in the unit PR.
3. The partial RED files (listed with sha256 prefixes in the state doc §3) are UNVERIFIED: re-hash them first; the RED agent must read, finish and run them, showing each fails for the right reason.
4. Relaunch with the saved scripts `docs/investigations/2026-09-30-session-70-state/scripts/wf_s70_u4b.js` / `wf_s70_oai.js`: set the `SP` constant to your scratchpad, point `RULES` at your copy of `scripts/s70-common.txt` (fix its pyt.py path too), and **delete the Spec and Review stages** (they are done — `resumeFromRunId` does not work across sessions). Pass the spec path and your rulings into the RED prompt. U4b's GREEN agent may run the package-manager commands ONLY inside `sc-s70-u4b/SmartCompareApp` (its own install); network steps (online `install --check`, `expo-doctor`) are the orchestrator's.
5. **Budget:** at ≥ 90 % of the weekly limit run ONE workflow at a time (two spec+review workflows cost ~2.5 M tokens in ~63 min).

## 3. Harness
Same recipe as session 69's prompt §5 (copies from `docs/investigations/2026-09-26-session-68-state/harness-2026-09-27/` + `scripts/`), plus: copy `qaren_netguard.py` from `…/2026-09-26-session-68-state/scripts/` into `<scratchpad>/harness/netguard/` (pyt.py's `NETGUARD_DIR`); set `SESSION` in `stall_monitor.py` + `harvest.py`; append each workflow run id to `harness/active_workflows.txt`. GitHub helpers: the repo is **`KGRddhs/smartcompare-backend`**; `pr_rest.api()` returns `(status, json)`.

## 4. Session 70 facts you must not redo
- Railway `web` retry vars set (`OPENAI_MAX_RETRIES=1`, `OPENAI_FALLBACK_MAX_RETRIES=0`).
- Landing redeployed (MYEZ title, `/c/ /r/ /q/` hand-off live on the Railway domain).
- Preview OTA group `e2bde9c9-c130-44e1-9d5a-388e40a24625` from `94c097cd` (sourcemaps NOT uploaded — needs `SENTRY_AUTH_TOKEN`).
- Migration 042 APPLIED (outputs `2026-09-29-session-69-state/APPLY_OUTPUTS.md`).
- D4 = `C:\Users\SynAckITPC\Downloads\MYEZ-icon-white-2048.png`. Scrapers: no flips until App Store approval (Ahmed).

## 5. Ahmed's items (dependency order)
1. **OpenAI:** top up $100 (min $50) + auto-recharge + alerts (D8); read the tier; mint a NEW key and paste it into Railway `web` → `OPENAI_API_KEY` himself. Then Claude runs `python docs/investigations/2026-09-29-session-69-state/verify_after_credits.py` and the §3.5 REST compare of `LLM_PROVIDER_DECISION.md`.
2. **Decisions D3, D5–D14** (he chose to answer individually; D3 unblocks U3b + U8).
3. **The 8 legal inputs** (runbook §3 B) → U8 (write its spec first).
4. **Supabase:** paid plan; the `qaren://reset-password` redirect URL (Claude offered to add it from the signed-in browser pane — needs his yes).
5. **`qaren.app`:** attach to `qaren-landing` + fix the Cloudflare 522; confirm support@/privacy@/legal@ receive mail.
6. **Testers:** two cold launches for the OTA, the Arabic walkthrough, and **open the app once so the `react-native` Sentry project shows an event** — it had ZERO events in 30 days; if still zero after the OTA, fix mobile reporting before the store build.
7. **Sentry MCP:** authenticate with `/mcp` in an interactive `claude` terminal (user-scope `sentry` server is configured) or connect the claude.ai Sentry connector.
8. **ASC session with Hussain** → ASC app id → U10; then `APP_STORE_URL` in `landing/open.html` + the Worker's `idTBD`.
9. Demo account, warm-up pairs, six screenshots; then the preview build smoke test → `eas build --profile production` → `eas submit` (after U3b, U4b(+U4c), U8, U10).
10. Unblocked by 042 (his call): `ENABLE_SEARCH_LOG_TRUTH`, then `SEARCH_LOG_SYNTHETIC_TOKEN` + `ENABLE_SEARCH_LOG_SYNTHETIC_MARKER`. `DAILY_4O_CAP` sizing after the OAI unit merges.
