# Session 70 — state at the pause (2026-09-30 ~06:10 AST)

Session 70 resumed the MYEZ (ميّز) Apple launch lane from `docs/investigations/2026-09-29-session-69-state/NEXT_SESSION_PROMPT.md`. It **paused at the model usage limit** (Fable 5.1 limit reached mid-workflow; the account was at ~98 %). Main is unchanged at `94c097cd`: no code PR merged this session; this docs PR is the only merge. Everything below was measured, not recalled.

## 1. Production actions done (each on Ahmed's explicit yes in chat)

| When (AST) | Action | Result |
|---|---|---|
| 02:47 | Railway `web`: `OPENAI_MAX_RETRIES=1`, `OPENAI_FALLBACK_MAX_RETRIES=0` (CLI `railway variables --set`, values are not secrets) | read back via `railway run -s web` as `'1'` / `'0'`; deploy `d88b5957` SUCCESS. The **new OpenAI key is still owed** (Ahmed pastes it into `OPENAI_API_KEY` himself). |
| 02:47 | Landing redeploy `railway up landing --path-as-root -s qaren-landing -d` | deploy `b054fdd9` SUCCESS; `https://qaren-landing-production.up.railway.app/` title "MYEZ — Smart product comparison for the GCC" (was "Qaren — …"); `/c/x` 200 (was 404). The #257 rename and the #273 hand-off page are LIVE on the Railway domain. `qaren.app` still 522 (not attached). |
| 02:49 | Tester OTA `eas update --branch preview --clear-cache --non-interactive --json` from main `94c097cd` (clean tree, on main) | group `e2bde9c9-c130-44e1-9d5a-388e40a24625`; iOS `01a0ef93-2045-7813-a185-c6d83940869f`, Android `01a0ef93-2045-70bb-86d3-6a58a8b36c40`; runtime 1.0.0; createdAt 2026-09-29T23:49:51Z. Carries #251 #253 #255 #257 #258 #269 #274. `npm ls` clean first. Native compatibility: the installed preview build `773a9375` was built from `6042506d`; the lock diff since then is `+intl-pluralrules` only (pure JS). **Sourcemaps NOT uploaded** (no Sentry token). Ledger row added to `docs/runbooks/qaren-canary-onboarding.md` §9. |
| 03:05–03:10 | **Migration 042 APPLIED** (Supabase SQL editor in the browser pane; Ahmed signed in; each paste SHA-256-verified against the file before Run) | outputs in `2026-09-29-session-69-state/APPLY_OUTPUTS.md`: BEFORE a=14,482 b=7 c=422 a_pull=11,724 (= anchor) c_pull=295 (= anchor); AFTER 14,067 = (a+b)−c exactly; post: `is_synthetic` boolean with the verbatim comment, 14,067 TRUE, 2,634 of them before 2026-06-01, 2,225 NULL, 16,292 rows. The `ENABLE_SEARCH_LOG_*` flags stay OFF (Ahmed's call; activation order in CLAUDE.md SESSION 68b W4-13 rows). |

Ahmed's choices recorded this session: **D4 icon = `C:\Users\SynAckITPC\Downloads\MYEZ-icon-white-2048.png`** (2048×2048 RGBA master, 2026-06-10; the other file, `MYEZLogo.jpeg`, is a 1600 px JPEG on grey). **Scrapers: keep as-is until App Store approval** (no dark adapter flips). D3, D5–D14: "I'll answer individually" — still pending. The 8 legal inputs: pending.

## 2. Measured

**Providers** (`scripts/probe_providers.py` via `railway run -s web`, status only, no values printed): OpenAI **429 `credit_balance_exhausted` / `insufficient_quota`** (every compare still fails); Serper 200 (paid key live); Firecrawl 200, 1,025 credits left; Scrape.do active, 1,000/month; Bright Data fallback + budget gate both `true`; `ZYTE_API_KEY` unset on `web` (the off-clock seed only). Nothing to buy for scrapers.

**Sentry** (org `qaren-rr`, read through the browser pane after Ahmed signed in — the Sentry MCP is configured but was NOT connected in this session, see §5):
- `python-fastapi`, unresolved 14 d: `PYTHON-FASTAPI-R` OpenAI 429 no-credits (13) + `-1M` specs 429 (2); `-N` "Search error: " (11) and `-14` "Serper shopping call error (gl=us): " (4) — **empty messages** because `str(e)` is `''` for timeouts/connection errors; `-1K/-1J/-Y/-1N/-17` (~16) `_GatheringFuture exception was never retrieved` (CancelledError via `_timeout_none` ← `occ_service.fetch_occ_rest_price`); `-1H` refresh-token invalid (2).
- `react-native` (project `4511397433180240`, the `FALLBACK_DSN` target): **zero events of any category in 30 days**; last issues are from July. Either no tester opened the app, or mobile reporting is broken. **Check after the OTA lands on a tester phone**; if still zero, it is a launch-blocking observability bug.
- `booking-os-web` is an unrelated product in the same org.

## 3. Units in flight — both STOPPED at the usage limit after spec + adversarial review

Both workflows ran spec → adversarial spec review (APPROVED_WITH_CORRECTIONS, a BINDING section appended to each spec) and died at RED. The RED agents wrote files before dying: **partial, unverified** (sha256 prefixes below, 2026-09-30 06:06).

### U4b — icons + Expo patch bumps + gesture-handler removal + CI ratchet (worktree `sc-s70-u4b`, branch `feature/s70-u4b-icons-deps`, base `94c097cd`)
- **This worktree has its OWN real `node_modules` (`npm ci`), NOT a junction** — removal is safe; it keeps U4b's package changes off the shared clone install.
- Spec: `2026-09-30-session-70-state/U4B_ICONS_DEPS_SPEC.md` (copy on main via this PR; the worktree has the same bytes, sha `d59db055…`). Key measured facts: drift = expo 54.0.37, expo-font 14.0.12, expo-localization 17.0.9, expo-screen-capture 8.0.10, expo-updates 29.0.20; react-native-svg excluded (15.15.5 already in the preview binary); eslint-config-expo 55.0.1 vs ~10.0.0 content-identical; react-native-gesture-handler has only devDependency edges (removal drops 3 lock packages; the runbook's "react-navigation needs it" is wrong); `app.json` needs NO change; master PNG geometry measured; prototype renderer deterministic (in `notes/render_proto.py`). Full jest at base 351/3428/44 (one known flake `HistoryScreen.mobileJank.m21`).
- Partial RED on disk (uncommitted): `SmartCompareApp/__tests__/config/nativeBundle.w37.test.ts` (modified, `452e5aaa…`), `SmartCompareApp/__tests__/helpers/pngDecode.ts` (new, `004cebe9…`).

### OAI + observability — #265, #268, two Sentry-found defects (worktree `sc-s70-oai`, branch `feature/s70-openai-companions`, base `94c097cd`, no node_modules)
- Spec: `2026-09-30-session-70-state/OAI_OBS_SPEC.md` (sha `3c341ed9…`). Items: (1) #265 `url_extraction_service.get_client` gains `max_retries=openai_max_retries()`; (2) #268 `DAILY_4O_CAP` per-call env read (total parser), one `[MODEL_ROUTER] 4o cap reached` INFO line, additive `metadata.model_downgraded` threaded through the usage dict on sync + SSE; (3) eight empty-capable ERROR sites (serper :665 :825 :1013 :1096 :1173, extraction :1711 :1763 :1818) → constant %-templates + `exc_summary(e)` in a new leaf `app/services/log_scrub.py` (also receives `_safe_exc`, re-exported — importing it from scs is a cycle); (4) `_cancel_prefetched_direct` (scs ~:6700) cancels prefetch gathers without retrieving their exception → a done-callback that calls `.exception()`. Probe experiments green; module-reference comm set = 245 files. No stop condition hit.
- Partial RED on disk (untracked): `tests/test_s70_exc_summary_logs.py` (`8e6c12f1…`), `tests/test_s70_model_router_downgrade.py` (`2d70b448…`), `tests/test_s70_url_client_retries.py` (`9368b8d1…`).

## 4. Orchestrator rulings still owed before RED resumes (reviewer recommendations in each spec's BINDING section)
- **U4b:** Q1 eslint-config-expo → ALIGN to ~10.0.0 (recommended); Q2 `expo.version` → KEEP 1.0.0 with the review's executable rule (correction 4: `npm ls` equals the recorded set; diff `@expo/cli build/src/export/**` or smoke the first post-U4b OTA on one device; bump for every native change from the first production build on); Q3 CI → split: blocking `EXPO_OFFLINE=1 npx expo install --check` + report-only online step (the online expected set moves with every SDK-54 patch); Q4 **the JS splash and Home/Profile/History/onboarding/LoadingRings still render the old `QarenLogo` Q-ring** → a follow-up unit U4c (OTA-capable) — worth doing before review; Q5 notification icon / monochrome / iOS dark-tinted variants → follow-ups; Q6 renderer at `scripts/render_myez_icons.py`. Review correction 3: pin the exact nine resolved versions (Expo published again 2026-09-29); network steps (online `install --check`, `expo-doctor`) belong to the orchestrator.
- **OAI:** OQ1 marker on the 429-fallback too? (spec: yes); OQ2 router line also fires for Tier-3 synthesis (accept vs a `purpose` kwarg); OQ3 → YES (review C1, binding); OQ4 admin gauge reads `daily_4o_cap()` (byte-identical unset); OQ5 CLAUDE.md edits at merge; OQ6 `DAILY_4O_CAP=2000000` is MODELLED — Ahmed's cost call.

## 5. Left running / on disk
- Worktrees: `sc-s70-u4b` (real node_modules), `sc-s70-oai`, `sc-docs-70` (this PR; remove after merge, no junction). Older worktrees from sessions ≤ 66 untouched.
- Browser pane: Supabase SQL editor and Sentry both signed in (Ahmed's sessions).
- Sentry MCP: `~/.claude.json` has a user-scope `sentry` http server (`https://mcp.sentry.dev/mcp`) and the project enables the `sentry@claude-plugins-official` plugin, but neither loaded in session 70 (not authenticated). Ahmed authenticates with `/mcp` in an interactive `claude` terminal, or the claude.ai Sentry connector.
- The session-70 stall monitor was stopped at the pause.

## 6. Lessons
- A workflow's RED agent can write files before a usage-limit death; the orchestrator must hash them and treat them as unverified (done above).
- Two spec+review workflows in parallel consumed ~2.5 M subagent tokens in ~63 min; at ≥ 90 % of the weekly budget, launch one workflow at a time.
- The GitHub repo is `KGRddhs/smartcompare-backend` (a helper that hard-codes `…/smartcompare` returns empty issues).
- The Supabase SQL editor accepts a single-line paste; verify the editor text by SHA-256 against the file (`monaco.editor.getModels()[0].getValue()` + `crypto.subtle.digest`) before every Run.
