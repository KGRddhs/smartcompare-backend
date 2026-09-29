# Session 70: paste-ready prompt

Written at the session-69 close on 2026-09-29 and fact-checked against main `0e7b72a0`. Every path named below exists on that main unless the text says otherwise. Open a new session in `C:\Users\SynAckITPC\Documents\AI`; the repo clone is `smartcompare/`. Paste everything under the line.

---

You are resuming the **MYEZ (ميّز) Apple launch lane**. The repo is `smartcompare`. Identifiers still say `qaren`: bundle id `com.qaren.app`, slug `qaren`, scheme `qaren://`, EAS project `@kersher2/qaren`, Sentry org `qaren-rr`, `QarenLogo`, the `@qaren_*` storage keys and the `qaren.app` addresses. Do not rename identifiers.

Session 69 closed on 2026-09-29, **paused on Ahmed's inputs**. Almost every remaining unit waits on something he owes. Do not start a gated unit before its input exists. Ask him which of his items (§7) are done.

## 0. Measure first (the repo wins over this prompt)

1. `git -C C:/Users/SynAckITPC/Documents/AI/smartcompare fetch`, then `git log origin/main --oneline -8`. At the close, main was `0e7b72a0` plus the session-69 close docs PR (branch `docs/session-69-close`). Read anything newer first.
2. `curl -s https://web-production-58776.up.railway.app/health`. At the close it returned 200 `"MYEZ API is running"`. Run the compare probe (§4, "After the OpenAI top-up") only after Ahmed confirms the OpenAI top-up.
3. `git worktree list`. Session 69 left only `sc-docs-69d` (branch `docs/session-69-close`, no `node_modules` junction). Remove it after that PR merges. Older worktrees from sessions ≤ 66 and earlier campaigns are still registered. Leave them. If you ever remove one, check it for a junction first.
4. Look for leftover processes: `Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'stall_monitor|pyt\.py|pytest|jest' }`. The venv `python.exe` is a launcher that spawns the base interpreter, so one stall monitor shows as two `python.exe` processes. Session 69 stopped its monitor at the close; stop any that belong to a dead session before you start your own.

## 1. Read, in this order

1. `CLAUDE.md`: first the ship-blockers block at the top, then `## Active runtime (SESSION 69 …)`. Its last bullet is the CLOSE.
2. `docs/investigations/2026-09-29-session-69-state.md`: §4 (the 4.4 units table) and §5 (the state at the pause).
3. `docs/investigations/2026-09-29-session-69-state/APP_STORE_LAUNCH_RUNBOOK.md`:
   * §3 is Ahmed's ordered checklist.
   * §4 is what Claude does next.
   * §5 is the `eas.json` submit block and the command sequence.
   * §6 has the App Store Connect fields.

   The live page https://claude.ai/artifact/Hm3zhCtYJwRockobbgnccx (v14) is the more current copy. Read it with the Artifact tool's `read` action, not with a fetch.
4. Decisions and inputs owed:
   * runbook §3 B lists D1–D11 and the **8 legal inputs**;
   * D12 (spelling MYEZ), D13 (Arabic form ميّز) and D14 (domain and emails) are in the "Ahmed's items" bullet of CLAUDE.md's SESSION 69 block;
   * **applied:** D1-A (iPhone only) and D2-A (honest limit sheet);
   * **pending:** D3–D14 and the 8 legal inputs.
5. `docs/investigations/2026-09-29-session-69-state/LLM_PROVIDER_DECISION.md`. It covers OpenAI at $100, the two retry variables and the §3.5 verification. You need it once the top-up lands.
6. `docs/CONTEXT_SESSION_LOG.md`: the SESSION 69 CLOSE entry and checkpoints 1–3. They hold the harness facts. The checkpoint headings say 2026-09-30, but git dates every session-69 merge to 2026-09-29.

## 2. Merged in session 69 (fourteen PRs, all on 2026-09-29, +0300)

The client units are **on main only**. Phones still run OTA group `561d2cba` (`preview`, from `ab9442ae`, 2026-09-24).

| PR | Merge | What it did |
|---|---|---|
| #251 | `89f2dc6a` | Reworded 8 of the 51 Arabic `results.dimension.*` labels. |
| #252 | `d6e613a3` | `extraction_service.get_client` now logs `OPENAI_API_KEY configured` / `missing` with no key suffix. Backend, deployed. |
| #253 | `e3f87b8b` | 13 SPKI pins and `addSslPinningErrorListener`, which reports to Sentry once per session. These must also be in the store binary. |
| #254 | `386463c3` | Native config: iPhone only, an honest microphone string on expo-camera and expo-image-picker, no Face ID string, `CFBundleLocalizations` en/ar plus `locales/{en,ar}.json`, `expo.name` MYEZ, privacy-manifest purposes. **Native**, so it reaches users only through the production build. |
| #255 | `5634f49e` | The `Paywall` route now shows an honest free-limit sheet. The Profile Upgrade row is gone. |
| #256 | `d792f00e` | Docs checkpoint 1. |
| #257 | `f8c936e2` | The rename to MYEZ / ميّز (catalogs, 9 literals, `/health`, 8 landing pages). Identifiers kept. |
| #258 | `3c5e4ff4` | Error honesty: `home.errors.engineUnavailable.*`, degraded results shown as degraded, and a coded 503 `LLM_UNAVAILABLE` on the image route. |
| #269 | `f40a44d3` | Sign-in and first run:<br>• the native Apple button;<br>• `authErrorCopy.ts`;<br>• no OS push prompt outside onboarding Step 17 or the one-time `PushPrePrompt`;<br>• `bootstrapRtl` reloads once;<br>• a Popular-comparisons tap runs the pair;<br>• honest counts. |
| #270 | `229a5756` | Docs checkpoint 2. |
| #271 | `7c4f82c6` | U9: the ASC checklist and inventory, the store-build rules in CLAUDE.md, and a non-blocking `expo install --check` step in CI. |
| #273 | `c3978a95` | `landing/open.html`, the `/c/ /r/ /q/` hand-off page. |
| #274 | `2ef89e23` | U3a, the one-time AI-processing consent sheet (`aiConsent.ts`, `AiConsentSheet.tsx`, `withAiConsent`). |
| #275 | `0e7b72a0` | Docs checkpoint 3. |

## 3. What is open at the close

These things are still true:

* **Every production compare fails.** OpenAI credits are exhausted (429 `insufficient_quota`). Ahmed tops up.
* **The privacy policy and terms are still the DRAFT template.** `app/legal/privacy_policy.md` says Qaren and promises an AI-sharing opt-out that routes nothing (#266). The #274 consent sheet links this policy, so **U8 is a launch blocker.**
* **The app icon is still the Expo template placeholder** (U4b).
* **The landing service has not been redeployed.** The #257 rename and the #273 hand-off page are on main but not live. `qaren.app` still answers a Cloudflare 522.
* **Migration 042 is not applied.**
* **Phones are on `561d2cba`.**
* **Nothing was flipped.** Railway and Supabase were left untouched.

Issues filed in session 69, each an optional unit once its product call is clear:

| Issue | Problem |
|---|---|
| #259 | The History list has no degraded marker (needs a backend summary field). |
| #260 | Two stale backend comments. |
| #261 | Product call: should a codeless camera 502/504 keep tap-to-retry? |
| #262 | Resolve the invite code before `register_user`. |
| #263 | Login 401s need distinct codes. |
| #264 | The push senders ignore `notifications_enabled`. |
| #265 | `url_extraction_service.get_client` ignores `OPENAI_MAX_RETRIES`. |
| #266 | `select_client_for_user` has 0 callers, so the PDPL opt-out routes nothing. |
| #267 | The smoke pack proves only the parse leg and registers a prod user on every run. |
| #268 | `DAILY_4O_CAP` silently downgrades to the mini model. |
| #272 | `create_invite` builds `/c/?ref=` when `comparisons.share_token` is NULL. |

**Not filed:** a server-side record of the U3a consent (migration + endpoint). File it, or fold it into U3b.

## 4. Units and their exact preconditions

**U3b.** Waits for **D3**.
* Spec: `docs/investigations/2026-09-29-session-69-state/U3_AI_CONSENT_SPEC.md`, R4.
* **D3 = A:** remove the Profile "Help improve AI quality" toggle and its keys. Delete `select_client_for_user` and the `OPENAI_API_KEY_PRIVATE` branch. U8 deletes policy §11.
* **D3 = B:** route all 17 call sites through `select_client_for_user`, unset = OFF. Ahmed provides `OPENAI_API_KEY_PRIVATE`. Set `AI_CONSENT_VERSION = 2` and add an opt-out sentence to the sheet; the copy-hash fence moves with it.
* A unit that adds a string naming the app must extend `BRAND_KEYS` (now 28) in `__tests__/i18n/brand.myez.s69.test.ts`.

**U4b.** Waits for the **original MYEZ logo file**.
* Commit the logo at `docs/brand/myez-logo.png`. That is a suggested target path; the folder does not exist on main yet. Candidate E is in `icon-candidates/`.
* Scope, from runbook §4 row U4:
  * `npx expo install expo@~54.0.37 expo-font expo-localization expo-screen-capture expo-updates` with `expo.install.exclude: ["react-native-svg"]`;
  * uninstall `react-native-gesture-handler` and delete the PENDING_REMOVAL + d3 todo;
  * replace `assets/icon.png`, `adaptive-icon.png` and `splash-icon.png`;
  * set `ICON_ART_SUPPLIED = true` at `__tests__/config/nativeBundle.w37.test.ts:251`.
* **Run it ALONE in the clone.** Every client worktree shares the `node_modules` junction.
* **No U4b spec exists on main. Write one first.** `U4A_NATIVE_CONFIG_SPEC.md` R-C names the deferred set.
* Afterwards, ratchet the CI `expo install --check` step to blocking.

**U8 (legal).** Waits for the **8 legal inputs** (runbook §3 B) and D3.
* **No U8 spec exists on main. Write one first**, drafted under the MYEZ name.
* Scope:
  * rewrite `app/legal/*.md` with no DRAFT lines;
  * `app/api/legal_routes.py` `last_updated`;
  * `TERMS_VERSION` in `SmartCompareApp/src/services/consent.ts` **and** `app/services/consent_service.py` (both `2026-03-26` today);
  * `landing/privacy.html`, `terms.html`, `ar/privacy.html` and `ar/terms.html`;
  * drop the ToS §12 "Premium subscribers earn…" line;
  * §11 per D3.
* Check: `grep -ri draft app/legal landing` returns 0.

**U10.** Waits for the **ASC app id**. Fill the `eas.json` `submit.production` block (runbook §5).

**U11 (optional).** SIWA token revocation, reading `DAILY_4O_CAP` from env, the breaker census comment, guest mode (D6).

**After the OpenAI top-up (Claude):** run `python docs/investigations/2026-09-29-session-69-state/verify_after_credits.py`. It is read-only and spends 3 uncached compares plus 1 stream. Then run the app-shaped REST compare from `LLM_PROVIDER_DECISION.md` §3.5. A pass means a real verdict: no `comparison.error`, specs present, a price present, no 429.

## 5. Harness recipe (from the REPO copies; the session-69 scratchpad is gone)

1. Create `<your scratchpad>/harness/`. Copy these files into it:
   * from `docs/investigations/2026-09-26-session-68-state/harness-2026-09-27/`: `pyt.py`, `stall_monitor.py`, `harvest.py`;
   * from `docs/investigations/2026-09-26-session-68-state/scripts/`: `pr_rest.py`, `issue_rest.py`, `ci_logs.py`.

   Keep them in one folder, because `issue_rest.py` and `ci_logs.py` import `pr_rest`. Also create `harness/active_workflows.txt`: the stall monitor reads the run ids of the workflows it bounds from that file next to itself (one per line — append each run id you launch). Without it the per-agent elapsed/idle bounds silently do nothing.
2. In the copied `stall_monitor.py` and `harvest.py`, set `SESSION = "<this session's id>"`. They ship with session 68b's `0a2845de…`. Do not use `scripts/harvest.py`, which hard-codes an older session's journal path.
3. Start the stall monitor **from the scratchpad**, in the background, before any workflow launch: `python harness/stall_monitor.py --interval 600 --max-minutes <N>`. Session 69 ran it with `--interval 300 --max-minutes 300`. First check that none is already running (§0, step 4). Stop it at the close.
4. Run **every** pytest through the bounded runner: `python harness/pyt.py --bound 600 --tag <name> --log <file> --cwd <worktree> -- <pytest args>`. rc=4 within about 1 s is a pytest usage error (a bad file list), not a result. Read the log head.
5. Agent rules are in `scripts/s68b-common.txt`. The workflow templates are `scripts/s68b-*.mjs`. For a plain fix + adversary, `s68b-round.mjs` needs `maxFixRounds 0`.
6. For GitHub, use `python harness/pr_rest.py create|status|watch|merge …`, `issue_rest.py create …` and `ci_logs.py <pr>`. Never use `gh`: its TLS path dies on this box.

## 6. Binding rules

**Harness.**
* Every pytest goes through the bounded runner. One pytest at a time per agent, in chunks of ≤ 25 files.
* Run at most **2 gate-heavy workflows** at once.
* Start the stall monitor from a scratchpad before launching anything.

**Client units.**
* **Never recursively delete** a worktree that holds a `node_modules` junction. Unlink it first with `cmd /c rmdir <path>\SmartCompareApp\node_modules`.
* **Run the FULL jest suite after any rebase**, before the PR.
* **Never write `jest.mock(path, factory, { virtual: true })` for a module that exists.** It leaks the real module into later test files of the same worker. Reproduce a CI-only red with `--runInBand` in the worker's file order.
* Feed eslint from `SmartCompareApp/` with `git diff --name-only --relative`.
* The pre-commit scan rejects `sk-…`-shaped test sentinels.

**Shell and files.**
* Parallel Bash calls share one shell. Use `( cd … && … )` subshells and absolute paths. Python on Windows needs `C:/` paths.
* A worktree directory the tool shell sits in cannot be deleted until the shell `cd`s away.
* Never `git checkout --` a file that carries uncommitted agent work. Snapshot it and sha-verify.
* After any stop, sha-compare every dirty file against the last completed report and the mutation harness's snapshot.

**Secrets.**
* Never call Railway `list_variables` / `railway variables`, never print env values, never `cat .env`. Read Railway variables as NAMES only.
* Nothing is flipped without Ahmed's explicit word.

**Docs.**
* Historical SESSION blocks and old session-log entries are records. Never rewrite them. Append a dated `**SESSION NN CORRECTION (date):**` line instead.
* A correction on a markdown table row goes inline in the row. A separate line splits the table.
* Run `date` before writing any date.

## 7. Ahmed's items, in dependency order

1. **OpenAI.**
   1. Top up $100 (minimum $50).
   2. Read Settings → Limits (the tier).
   3. Decide D8 (auto-recharge or prepaid) and set a budget with alerts.
   4. Mint a **new** project key. The precondition is met: #252 is deployed.
   5. Make one Railway `web` Variables change with the key, `OPENAI_MAX_RETRIES=1` and `OPENAI_FALLBACK_MAX_RETRIES=0`. Never print the values.
   6. Then Claude runs `verify_after_credits.py`.
2. **D3** (OpenAI data sharing, including the org data-controls setting). Unblocks U3b and part of U8.
3. **The 8 legal inputs** and **D5** (publisher / data controller). Unblocks U8.
4. **The original MYEZ logo file** (D4). Unblocks U4b.
5. **Migration 042.** Run `APPLY_042_1_PRECHECK.sql`, then `APPLY_042_2_ONE_PASTE.sql`, then `APPLY_042_3_POSTCHECK.sql` in the Supabase SQL editor. It is independent of the rest.
6. **The landing.**
   * Run `railway up landing --path-as-root -s qaren-landing -d` from the repo root. This ships the #257 rename and the #273 hand-off page.
   * Attach `qaren.app` to `qaren-landing` and fix the Cloudflare record behind the 522 (runbook §3 A4).
   * Confirm `support@`, `privacy@` and `legal@` receive mail.
7. **The App Store Connect session with Hussain.**
   * API key, the app record `MYEZ — Compare Smart`, `eas credentials`, capability sync.
   * This yields the ASC app id, which unblocks U10.
   * Then fill `APP_STORE_URL` in `landing/open.html` and the Worker's `idTBD`, and redeploy the landing.
8. **The rest of the decisions:** D6, D7, D9 (13+ override, Age Assurance No), D10, D11 (the listing text after a native Arabic review), D12–D14.
9. **Supabase:** the paid plan and the `qaren://reset-password` redirect URL.
10. **Review assets:** the premium demo account, the six warm-up pairs, and six real screenshots (6.9" / 6.5", no iPad).
11. **Optional OTA.** If testers should see #251–#274 before the store build, run `eas update --branch preview --clear-cache` from current main after `npm ls` is clean.
12. **The build.** After U3b, U4b, U8 and U10 merge: a preview build and a smoke test on the 2 registered iPhones, then `eas build --profile production` from a main that contains every fix, then `eas submit`. After launch, JS hotfixes go to `eas update --branch production`, never `preview`.
