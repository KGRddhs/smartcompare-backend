# Critique of LAUNCH_PUNCH_LIST.md: engineering and operations lens

Critic: critic-eng-ops (Opus). Read-only checkout of main `845ece15` (`git rev-parse HEAD` = 845ece15f118...). Written 2026-10-05, 14:17-14:40 AST.

Method:
- I wrote my own list of first-submission failure modes before I opened the punch list (notes.md, step 3).
- I re-derived each claim below from files at `845ece15`, from the session-69/71 state documents, or from the installed `node_modules` in `sc-s70-u4b` (Expo 54.0.37, @sentry/react-native 7.2.0).
- No network, no Railway, no EAS, no Supabase. Anything that needs a dashboard is marked NOT VERIFIED.

## 0. Verdict: SOUND_WITH_CORRECTIONS

The seven hard stops are real, and the order (money, decisions, Apple, builds, listing) is right. Within my lens, the list has:
- one false headline claim;
- one decision default whose stated consequence is wrong (W0), and that changes the recommendation;
- one owner step that a finder named but the synthesis dropped (custom SMTP);
- four dependency errors on the critical path, one of which holds the device-check build hostage to the legal inputs;
- missing launch-window operations: a merge freeze, the release mode, alert routing, and a per-step rollback list.

None of these blocks the plan. All of them should be folded in before Ahmed acts on it.

## 1. Refuted claims

| Line | Claim | What the code or source shows |
|---|---|---|
| A, line 27 | "Every Claude unit that needed no owner input has merged" | False by the list's own section C. BE-HARNESS (MUST, "Waits for: none"), DOCS-CONFIG, OBS, COST-METER, DEVICE-PURGE, SSRF-PHARMACY and T0b Phase B need no input and are unmerged. `docs/investigations/2026-09-29-session-69-state/verify_after_credits.py:38`, `:67`, `:68` still pass a degraded 200 and any stream event. |
| D, W0 (A rec) and E13 | "one reviewer Link compare to a black-holed host can freeze the worker 11-12 s; review traffic is one user" | The exposure is any anonymous internet caller, not the reviewer. `POST/GET /url/detect` have no `dependencies=` (`app/api/url_routes.py:390`, `:410`). U13 did not cover them. They call `_validate_url_offloop_or_sync` (`:398`, `:417`). With the flag OFF that runs the sync `validate_external_url` inline on the loop (`app/utils/url_validator.py:535-537`; `socket.getaddrinfo` at `:355`). There is one uvicorn process (`railway.json:7`). The `20/minute` decorator keys on the edge peer, which spreads over Railway edge addresses (CLAUDE.md SESSION 71 finding, 322 calls from 155 addresses with no 429). The repo is public, and the API URL is hard-coded (`SmartCompareApp/src/services/api.ts:20`). |
| backend READINESS section 4 | "U13 removed the anonymous load" | Only the paid routes are covered. `/url/detect` (DNS) and `/url/retailers` stay anonymous (same lines as above). |
| B2 (vs BE-07) | B2 asks Ahmed only to "read Confirm-email, the sender and the templates" | The backend finder's BE-07 row (READINESS_BACKEND.md:151) also says "use custom SMTP if confirmations are ON". The synthesis dropped it. `register_user` returns `access_token: None` when Supabase withholds the session (`app/services/auth_service.py:419-422`), so a sign-up waiting on an e-mail that never arrives cannot sign in. |
| B12 | "confirm `SENTRY_AUTH_TOKEN` in the production environment **or** add `SENTRY_ALLOW_FAILURE=true`" | It needs both, or the preview build proves nothing for production. The upload phase prints `error:` (an Xcode build error) on any failed upload unless `SENTRY_ALLOW_FAILURE` or `SENTRY_DISABLE_AUTO_UPLOAD` is set (`node_modules/@sentry/react-native/scripts/sentry-xcode-debug-files.sh:63-77`, `sentry-xcode.sh:51-58`, v7.2.0). The preview and production profiles read separate EAS environments: `eas.json:13-21` has no `environment` key, so the EAS default per profile applies (the default mapping is NOT VERIFIED). A green preview build therefore does not prove the production token. Commit `43cca757` records the token as created for both environments on 2026-05-23. Its validity today is NOT VERIFIED. |

## 2. DONE rows re-derived (section A3)

| Item | Result at 845ece15 |
|---|---|
| Launcher icon + launch screen (#279) | PROVEN. `de66a25f` is an ancestor. `assets/icon.png` is 1024x1024, PNG colour type 2 (RGB, no alpha). `splash-icon.png` is RGBA on a `#ffffff` splash background (app.json:10-14), which is fine. |
| supportsTablet false, mic strings, no Face ID, ar localization (#254) | PROVEN. app.json:22, :197, :203-205, :212-213, :220-221; `locales/{en,ar}.json` exist. Also `ITSAppUsesNonExemptEncryption:false` (app.json:145), the privacy manifest (app.json:25-143) and the Google `iosUrlScheme` (app.json:227). |
| 13 pins + listener (#253) | PARTLY PROVEN. I counted 13 SPKI literals in `certificatePinning.ts`. I did not re-read the listener lines. |
| Honest limit sheet on phones (#255) | PROVEN on the OTA base. `5634f49e` is an ancestor of `94c097cd` (OTA e2bde9c9). |
| Deletion route (#290/#310) | PROVEN. auth_routes.py:1165-1181. Rollback `migrations/rollback/043_delete_user_cascade_full_erasure.sql` is present. |
| U13 active | PROVEN for the paid routes (the orchestrator measured production; `dependencies=[Depends(require_paid_route_*)]` at url_routes.py:273, :310, :331, :368). Not true for `/url/detect` (section 1). |
| In-app mark (#288/#307) | PROVEN. `60278405` and `72b13bc5` are ancestors. |
| Landing hand-off page (#273) | PROVEN in code (`landing/nginx.conf.template:63-71`). The AASA appID `8K562M549D.com.qaren.app` is correct (`landing/.well-known/apple-app-site-association`). |
| pip-audit blocking | PROVEN. ci.yml:213-216 has no `continue-on-error`. |

## 3. Over-scoping (a MUST or a dependency that does not truly block)

1. **The preview build (step 15) waits on U8 (step 9).** The in-app policy is fetched at runtime (`LegalScreen.tsx:33-34`, `:53`; AsyncStorage is only the offline fallback, `:56-58`). U8's only binary content is `consent.ts:12` `TERMS_VERSION` (plus the optional `lang` param). The legal inputs are the longest pole, and the device checks (Google, splash, prompts, pinning, Sentry) do not need them. Re-wire:
   - 15 waits on 10 and 11 (or run T3 now);
   - 18 waits on 9;
   - the TestFlight internal smoke on the production binary is the exact-binary check.
   This saves a build cycle whenever a conditional native unit fires.
2. **Step 18 waits on U10 (step 14)**, yet section C2 calls U10 SHOULD with interactive `eas submit` as the fallback. Make 14 optional for 18.
3. **The screenshots (step 20) reach BE-HARNESS through steps 8 and 19.** The screenshots need a funded, passing canary. The existing script plus the orchestrator reading the JSON against the A1.8 rule is enough. Keep BE-HARNESS as the gate for the review-notes pairs (19 -> 22) only.
4. **U-CANARY under CAN=A is docs-only.** `features.ts:30` is already 100. With CAN=A it is a CLAUDE.md and runbook edit (fold it into DOCS-CONFIG), not a binary MUST.

## 4. Missing items (diff of my independent list against the punch list)

Row schema: id | title | status | launch_severity | evidence | next_action.

- EO-01 | Anonymous `/url/detect` freezes the single worker on a black-holed host; the W0 consequence is wrong | OPEN-AHMED (decision W0) | high | url_routes.py:390-417; url_validator.py:535-537, :355; railway.json:7; CLAUDE.md SESSION 71 limiter finding | Change the W0 recommendation to B: flip `ENABLE_OFFLOOP_DNS_RESOLVE` alone, with one canary (3 compares + `/health` `loop_lag_max_60s_ms` < 1000), before submission. U13 is the precedent for an owner exception. Rewrite E13.
- EO-02 | Supabase e-mail delivery: custom SMTP was dropped from B2. A paid plan (SB=A) does not change the built-in sender | OPEN-AHMED | high (real sign-ups on launch day; a reviewer who registers by e-mail) | READINESS_BACKEND.md:151; auth_service.py:419-422; the built-in sender's limits are NOT VERIFIED (dashboard) | In B2, also read Authentication -> SMTP settings. If Confirm-email is ON, or reset mails are expected, set up custom SMTP before submission. Send one confirmation and one reset to an address that is not a team member.
- EO-03 | A green preview build does not prove the production build's EAS environment | OPEN-AHMED | medium | eas.json:13-21; sentry-xcode-debug-files.sh:63-77; commit 43cca757 | In B12, set `SENTRY_ALLOW_FAILURE=true` in the production environment (and the token), and list the production environment's variable NAMES (`eas env:list`).
- EO-04 | `eas submit --latest` can pick a non-store build | OPEN-AHMED | low | punch list B18. The session-71 IMPLEMENTATION_PLAN Milestone 3 uses `eas submit --id <build>`. Whether `--latest` filters by profile is NOT VERIFIED | Use `eas build -p ios --profile production --auto-submit`, or `eas submit --id <production build id>`.
- EO-05 | No backend merge freeze and no rollback recipe for the review window | OPEN-BOTH | medium | Every merge to main auto-deploys `web` (CLAUDE.md Commands). A variable change rebuilds `web` from GitHub main (SESSION 67 block, deployment 2c4dbf6e). C2 holds 8+ backend-deploy units with no window rule | Freeze backend merges from Submit to approval, except fixes on the reviewer path, each with the authenticated canary. Rollback: Railway -> web -> Deployments -> redeploy the previous SUCCESS deployment (Ahmed). Write it into the runbook.
- EO-06 | Release mode not decided; automatic release puts the app live before B24 and monitoring are ready | OPEN-AHMED | medium | Absent from sections B and D; B24 assumes a controlled release | In B22, choose "Manually release this version". Release after `APP_STORE_URL`, the balance and the alert routing are checked.
- EO-07 | No alert routing for the launch window | OPEN-AHMED | medium | The only monitor seen is SentryUptimeBot on `/`, which is static (`app/main.py:494-500`) and sees neither OpenAI nor the DB. `/health` has no DB probe (E6). Whether any Sentry alert rule e-mails Ahmed is NOT VERIFIED. Mobile Sentry has never shown an event | Ahmed: a Sentry issue alert on python-fastapi (new or regressed issue, and LLM_UNAVAILABLE / 429 frequency) to his phone, verified with one test alert. Under D8=A a drained prepaid balance is otherwise found only by the daily warm-up.
- EO-08 | Key rotation scope: B1/B6 name only `web` | OPEN-AHMED | low | price-warmer runs the price pipeline (railway.warmer.json:10). Which services hold `OPENAI_API_KEY` is NOT VERIFIED (agents may not read Railway) | Before B6, check variable NAMES per service, set the new key on every holder, then revoke.
- EO-09 | `restartPolicyMaxRetries: 3`: a crash loop leaves `web` down until a manual redeploy | OPEN-AHMED | low | railway.json:11-12. Whether Railway resets the counter is NOT VERIFIED | Consider `ALWAYS` for the review window, or know that the lever is a redeploy.
- EO-10 | The 30-day negative price cache can hide prices on review pairs, and no purge lever is listed | OPEN-CLAUDE | low | price_service.py:148. structured_comparison_service.py:8897-8913 plants 30 d unless the cause is a Serper/guard degradation. A flush of `nogenuine:` exists only behind the dark `ENABLE_FLUSH_LIVE_PRICE_KEY`. Whether any review pair carries a sentinel is NOT VERIFIED | BE-HARNESS reports "no price" pairs separately, and the runbook says to drop such a pair from the review notes (no flag flip).
- EO-11 | Apple's upload SDK floor vs the EAS default image is not checked | OPEN-AHMED | low | eas.json has no `ios.image`; Expo 54.0.37. Apple's current minimum is NOT VERIFIED (no web) | Read the Xcode version in the B16 preview build log. If it is below Apple's minimum, pin `ios.image` in the production profile before B18. The failure would otherwise first show at upload, after the whole device cycle.
- EO-12 | ASC account-holder prerequisites: pending agreements block uploads; EU storefronts need the DSA trader status | OPEN-AHMED | low | Not in B10-B11; NOT VERIFIED (knowledge, no web) | Hussain, in B10: accept any pending agreement, and either set the trader status or exclude EU storefronts in Pricing and Availability.
- EO-13 | U8 can publish "no AI data sharing" before the switch is off | OPEN-AHMED (dependency) | medium | Step 9 waits on 1 and 6, not on 2. U8 deploys its policy at merge (backend auto-deploy); the policy is fetched at runtime (LegalScreen.tsx:53) | Add 9 <- 2: Ahmed confirms org data sharing is OFF before U8 merges.
- EO-14 | U3b and U8 both edit policy section 11 | OPEN-CLAUDE (dependency) | low | Step 10 scope: "toggle, policy section 11 and the router"; U8 replaces `app/legal/*.md` | U8 owns all policy text. Drop "policy section 11" from U3b, or sequence U3b first and rebase U8.
- EO-15 | Step 18 (TestFlight smoke with a compare) and step 17's own check need funded OpenAI | dependency | low | A1 row 18 waits on 7, 14, 15, 16 only. B17 verifies with "a real verdict". Runbook section 3 D.1 includes "a compare" | Add 17 <- 8 and 18 <- 8.
- EO-16 | B19 command form: `railway run ... -- env X=1 python ...` needs an `env` binary, which PowerShell lacks | OPEN-CLAUDE | low | punch list B19 | Name Git Bash as the terminal, or have BE-HARNESS give the warm-up script a `--send-admin-key` flag.
- EO-17 | The B15 OTA onto the old binary shows a mismatched splash hand-off | info | low | READINESS_CLIENT.md:248 (the U4c geometry matches only the NEW launch screen) | Do not judge U-SPLASH from the OTA; judge it from B16.
- EO-18 | Supabase pause timing: the uptime pings never touch the DB, and there has been no app traffic since 2026-10-03 | OPEN-AHMED | medium (time-boxed) | `/` is static (main.py:494-500); orchestrator: 0 mobile-UA requests in 38 h. Supabase's exact inactivity rule is NOT VERIFIED | Keep B2 (paid plan) marked TODAY. Until then, one signed-in action per day keeps the project awake.
- EO-19 | CLAUDE.md:198 says "Sourcemap upload deferred", but upload has been on since `43cca757` (app.json:249-256 has no `disableAutoUpload`) | OPEN-CLAUDE | low | CLAUDE.md:198; sentry.ts:10-16 header | Add it as a DOCS-CONFIG rider, so no agent "fixes" the build by re-adding `disableAutoUpload`.

## 5. Critical-path dependency corrections (summary)

- 15 <- 10, 11 (not 9); 18 <- 9 (EO-15 / section 3.1).
- 9 <- 2, the data-sharing switch (EO-13).
- 17 <- 8; 18 <- 8 (EO-15).
- 18: 14 is optional (section 3.2).
- 20 <- 8 only; 19 <- 5 stays for the review notes (section 3.3).
- 10 and 9 must not both edit policy section 11 (EO-14).
- Add W0=B as a step between 8 and 22 (EO-01).
- Add a merge freeze from 22 to approval (EO-05).
- Choose the release mode inside 21 (EO-06).
- Confirmed correct as listed:
  - 043 is applied before U8 publishes deletion wording (9 <- 6);
  - the canary percent is set before the production build (11 -> 15 -> 18);
  - the landing redeploy follows U8 (13 <- 9);
  - U13 is active before funding;
  - `ENABLE_PASSWORD_RESET_DEEP_LINK` waits until after the store build;
  - `expo.version` stays 1.0.0 (runtimeVersion `appVersion`, app.json:264-266), so the first store build carries runtime 1.0.0 on a fresh `production` channel.

## 6. Decision defaults: consequences the list did not state

- **W0=A**: wrong consequence (section 1). Recommend B.
- **SB=A**: the paid plan does not fix e-mail delivery (EO-02). It removes only the pause risk (EO-18).
- **D8=A** (prepaid): a drained balance is visible only through Sentry or the warm-up (EO-07). A small prepaid amount also keeps the org at a low usage tier (E1).
- **D7=A** (breaker OFF): during an OpenAI outage, compares whose parse is cached still run the paid search cascade before failing at the verdict. That was the 2026-09-07 pattern (CLAUDE.md SESSION 65 block). It is now bounded by `ENABLE_BRIGHTDATA_BUDGET_GATE=true`, so the risk is low, but the cost is not zero.
- **REPO=A** (public): keeps the hard-coded API host and the anonymous `/url/detect` path discoverable. That raises the weight of EO-01.
- **DNS=A**: iOS fetches the AASA when the app is installed. Attach the domain before the production build reaches reviewers or users, or universal links stay dead on those installs until the next update (low).
- **CAN=A**: no extra risk. The percent is JS, so a production-channel OTA can still change it.
- **GOO=A**: hiding the row leaves the Google `iosUrlScheme` (app.json:227) in the binary, which is harmless.

## 7. Rollback lever per risky step

| Step | Lever | Status |
|---|---|---|
| New OpenAI key (2) | Keep the old key until the canary passes (B6 is after 8) | listed |
| W0 DNS flag (if B) | Unset it; read per call | needs adding |
| Migration 043 (6) | `migrations/rollback/043_*.sql` (present). Deletions made after the apply cannot be recovered | listed implicitly |
| U8 / U3b / any backend merge | Railway redeploy of the previous SUCCESS deployment; the landing is redeployed from the previous commit | missing (EO-05) |
| Preview OTA (B15) | `eas update:republish` of group `e2bde9c9` to the `preview` branch | missing |
| Production binary in review | ASC "Remove from review". With manual release (EO-06), approval does not ship it | missing |
| After release | Production-channel OTA (JS only; never bump `expo.version`). The forced-update gate `APP_MIN_VERSION` / `APP_FORCE_UPDATE` (`app/api/version_routes.py:11-14`) works only once `APP_STORE_URL` is set. After main moves to 1.0.1, a 1.0.0 hotfix must be published from a 1.0.0 commit | partly listed |
| U13 | Unset `ENABLE_COMPARE_AUTH_REQUIRED` | documented in CLAUDE.md |
| qaren.app attach | Remove the custom domain | trivial |

## 8. Capacity and observability on launch day

- **Capacity for review traffic is adequate.** One process with `--limit-concurrency 512`. Retries `OPENAI_MAX_RETRIES=1` / `OPENAI_FALLBACK_MAX_RETRIES=0` are set on `web` (CLAUDE.md SESSION 70). Every OpenAI construction reads them (`openai_service.py:34-37`, `:63-76`). The limiter cannot 429 a reviewer, and U13 refusals cost nothing. The one real exposure is EO-01.
- **Not verified:** OpenAI tier and TPM (B1), Upstash plan quota, Railway plan limits.
- **Mobile signal before submission:** B14 tests the DSN and transport on the old binary. That is a valid proxy, because @sentry/react-native has been ~7.2.0 since 2026-05-16, before the 2026-07-04 build. B16 must repeat it on the new binary. A real compare after funding is the deterministic trigger of `comparison_wall_time` (whether it fires on a not-found Results visit is NOT VERIFIED, per the client finder).
- **Backend Sentry:** #285 groups one issue per log template. #311 (OBS) still leaks exception text in five arms. That is a privacy concern, not a launch gate.

## 9. NOT VERIFIED (by me)

- The EAS profile-to-environment default mapping; whether `eas submit --latest` filters by profile; the EAS SDK-54 default Xcode image; Apple's current upload SDK minimum.
- Supabase built-in e-mail limits and the inactivity-pause rule; Railway's restart-retry counter semantics.
- Which Railway services hold `OPENAI_API_KEY`; whether any Sentry alert rule exists; whether a 30-day price sentinel sits on any review pair.
- The DSA trader-status and agreements behaviour in App Store Connect (knowledge only, no web).
- The listener lines of `certificatePinning.ts` (not re-read).
- No tests were run (read-only critique).
