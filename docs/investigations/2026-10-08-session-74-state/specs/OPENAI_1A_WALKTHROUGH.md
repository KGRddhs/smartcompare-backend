# OpenAI task 1a: Ahmed's walkthrough (session 74, 2026-10-08)

Sources: four reader and four skeptic reports on official OpenAI pages, read 2026-10-08 12:48-13:25 AST. Only skeptic-confirmed or skeptic-corrected claims are stated as facts; [n] points to section E.
"Ledger" means the orchestrator's dashboard readings in `s74-state/ledger.md` (12:47-13:12). "OA" means `specs/FABLE_RULINGS_S74_OPENAI.md`. Neither is OpenAI documentation.
platform.openai.com/docs now redirects to developers.openai.com/api/docs [2]. Keys are named only by the variable NAME `OPENAI_API_KEY`; no key value goes into chat or into the shared Claude browser pane.

## A. What Ahmed does, in order

Precheck, already read (ledger 12:52): credit balance -$0.03; October spend $0.00 of the $120 organization limit; usage tier "Build".
So the cause fits 429 `credit_balance_exhausted` [7], not a spend limit and not the $500 Build usage limit. The error.code inside the Sentry events was not read.

1. Buy credits. Settings -> Organization -> Billing (https://platform.openai.com/settings/organization/billing) [7] -> "Buy credits" or "Add to credit balance", whichever appears [1][3] -> amount.
   Then open the Payment method selector and pick the saved card -> confirm. Ledger 13:12: without that pick the form failed with "Payment method is required" and nothing was charged.
   - Decision D8 (amount). Since 2026-10-06 the tier depends only on total credit purchases: Build $5, Launch $100, Grow $500, with no waiting period [2][4].
   - Prior purchases (ledger): three $5.50 invoices, so about $15-16.50.
     - $25 (OA1): about $40 in total -> Build.
     - $50: about $65 in total -> Build. This holds whether or not pre-2026-10-06 purchases count, because both totals stay under $100.
     - $100: meets the "$100 in total credit purchases" Launch threshold on its own [2], if the account's undisclosed trust-tier maximum balance accepts it [1].
   - Build: gpt-4o 5,000 RPM / 450,000 TPM; gpt-4o-mini 5,000 RPM / 2,000,000 TPM; $500/month approved usage limit [2][5][6].
   - Launch: gpt-4o 10,000 RPM / 2,000,000 TPM; gpt-4o-mini 10,000 RPM / 10,000,000 TPM; $5,000/month [2][5][6].
   - Build already exceeds what one web worker needs. The Build limit that can bite is the $500/month usage limit, whose 429 `organization_usage_limit_exceeded` credits do not fix [9].
   - Minimum purchase is $5 [1]. Credits expire 1 year after purchase and are not refundable except where the law requires [1][24]. The -$0.03 negative balance is deducted from this purchase [1].
   - Decision auto-recharge (yes/no). If the dialog shows "Use auto-reload", set it to match the decision. It is ON by default during first-time setup [1].
     - Yes: set the balance threshold, the balance to restore to, and an optional monthly reload limit; the minimum recharge is $5 [1]. A failed recharge sends an email, and usage stops once the balance runs out [1].
     - No (current state; OA1): at $0 every compare fails with 429 `credit_balance_exhausted` [7]. The cutoff can lag, and the overrun shows as a negative balance [1]. Read the balance daily during review week.
   - Wait a few minutes; the docs give no exact delay for the balance to update [1]. Check the new balance on the Billing page yourself [24].
   - READING: "paid $N, balance $M".
2. Tier and per-model limits. Settings -> Organization -> Limits (https://platform.openai.com/settings/organization/limits) -> the "Usage Tiers" section (tier name) and "Rate limits" [2].
   - Do not click "Upgrade tier"; the docs do not say what it does [2].
   - Ledger 12:52: "Models in use" listed only omni-moderation-2024-09-26. If the gpt-4o or gpt-4o-mini rows are missing, send "not listed"; Claude re-reads them after the canary.
   - READING: tier name, plus RPM and TPM for gpt-4o and for gpt-4o-mini (four numbers).
3. Spend limit and alerts. Settings -> Organization -> Limits -> "Spend" -> "Edit spend limit" -> "Monthly spend limit" -> optional "Enforce a hard limit" -> "Save" [9].
   - The project twin is Project settings -> "Limits" -> "Spend", with the same labels [9]. Its "Add budget alert" dialog takes a percent of the budget (medium) [10].
   - Ledger 12:52: a $120/month organization limit already exists, with alerts at 80 % ($96) and 100 % ($120). Add a 50 % ($60) alert (OA4; the orchestrator may add it instead).
   - A spend alert only notifies; traffic continues [9]. Organization and project owners always receive the alert messages (medium) [10].
   - Decision hard limit (on/off). ON returns 429 `organization_spend_limit_exceeded` at $120, the same outage shape as today [9].
     Enforcement is not instantaneous. The limit clears when raised or removed, or at the next monthly cycle, and alerts stay active alongside it [9].
   - READING: "limit $120, hard limit on/off, alerts at 50/80/100 %".
4. Data sharing. Settings -> Organization -> Data controls -> Sharing (the dashboard label from the ledger; the help article says only "organization settings page") [15].
   - There are three settings: model feedback; evaluation and fine-tuning data; "Share inputs and outputs with OpenAI" [15].
   - Inputs/outputs sharing is disabled by default for every organization, and only org owners can change it. When "Enabled", the inputs and outputs of enabled projects are shared with OpenAI (medium, search-index text) [15].
   - Ledger 12:56: all three read "Enabled for all projects", with "You're enrolled for complimentary daily tokens". Decision D3: OA2 keeps sharing ON and discloses it (section D).
   - READING: the state of each of the three settings, and whether the "enrolled" line shows.
5. Chat Completions storage default. Settings -> Organization -> Data controls -> Data retention -> "API call logging" [16].
   - The API lists four values: disabled, enabled_per_call, enabled_for_all_projects, enabled_for_selected_projects. No page defines them or names a default [25].
   - Do not click "Audit logging" -> Enable: once on, it cannot be turned off in settings, only through Support [16].
   - Ledger 12:56: the value is "Enabled per call", and the page text says Chat Completions are logged only when a call sends store=true. OA3 keeps it.
   - READING: "store default: no" for "Enabled per call" or "Disabled"; "yes" for either "Enabled for ..." value.
     This mapping is inferred: the cookbook calls the organization switch "on by default" logging [26].
6. New key, in YOUR OWN browser window and never the shared pane (OA5). Settings -> Organization -> API keys (https://platform.openai.com/settings/organization/api-keys) [20] -> create a key in "Default project", the only project (ledger 12:52).
   - If the dialog offers permissions, chat completions are covered by the "Model capabilities" row at level "Request" [19]. That nothing more is needed is inferred (medium).
   - Set an expiration date; OpenAI strongly recommends it [18].
   - Never use an Admin key: it cannot call non-admin endpoints [21]. The full value is shown only once [27].
   - Owner type: a user-owned project key. Reason: Ahmed is org owner, and that role holds Model capabilities [19]. A service-account key's revoke path is not covered by the project-key API [28].
   - Put the key into Railway on every service that holds `OPENAI_API_KEY` (web and any worker), from your own terminal or the Railway dashboard. Keys stay server-side, never in the Expo client [32].
   - A new key alone does not clear the 429, because the prepaid balance belongs to the organization [7].
   - READING: "new key in place: OPENAI_API_KEY" (the NAME only).
7. Tell Claude "1-6 done". Claude runs section B.
8. After the canary PASSES, revoke the three old Active keys on the API keys page. Ledger 12:52 lists them as created 2026-02-04; 2026-02-08 (production); and 2026-02-09, last used 2026-09-07 by an unknown consumer. Identify that consumer before revoking (OA5).
   - Revocation takes effect within a few seconds [20]. After that the key gets 401 "Invalid Authentication" [7]. The API has no restore method for a deleted key [29].
   - Never archive "Default project": an archived project cannot be used, updated or restored [22].
   - READING: "old keys revoked: 3".

## B. What Claude does after

1. After READING 1, wait a few minutes [1], then re-read Billing (balance above $0) and Usage. Usage dates are in UTC [23].
2. After READING 6, run the canary from Ahmed's terminal or the orchestrator's (OA6):
   `railway run -s web -- env HARNESS_SEND_ADMIN_KEY=1 python docs/investigations/2026-09-29-session-69-state/verify_after_credits.py`
   It runs 3 uncached compares and 1 stream. X-Admin-Key comes from the ADMIN_API_KEY variable and is never typed or printed.
3. Read the JSON by hand against the runbook A1.8 rule until BE-HARNESS lands, because the current script can pass on a degraded 200.
4. Decode any failure by error.code, not error.type: all billing 429s can carry `insufficient_quota` [7][8].
   - 429 `credit_balance_exhausted`: the balance is not visible yet, or the purchase did not land. Re-read Billing.
   - 429 `organization_usage_limit_exceeded`: request a higher approved usage limit on the Limits page [9].
   - 429 `organization_spend_limit_exceeded` or `project_spend_limit_exceeded`: raise or remove that limit [9].
   - 429 `slow_down`: a rate signal, not billing. Follow Retry-After and ramp up [7].
   - 401 "Invalid Authentication" has three possible causes: the key lacks Model capabilities = Request; a revoked or locally cached old key is in use; or "IP not authorized" under an IP allowlist [7].
   - Never loop retries on a billing error. Retrying does not restore access [8], and failed requests count toward per-minute limits [8].
5. Funding restores the aliases `gpt-4o` and `gpt-4o-mini`. Only the gpt-4o-2024-05-13 snapshot shuts down, on 2026-10-23 [11].
   `app/services/model_config.py:44-53` uses the aliases. An env override pinning that snapshot was not checked.
6. Re-read Limits for the gpt-4o and gpt-4o-mini rows after the first successful calls (the step 2 fallback).
7. After READING 8, re-run the same canary. A PASS proves no service still holds a revoked key; a 401 means one does [7].

## C. Corrections to AHMED_TASKS_TO_SUBMIT.md section 1a (lines 14-24, identical at main dfbda511)

1. L16 "Settings -> Billing: add prepaid credit." -> "Settings -> Organization -> Billing: Buy credits (or Add to credit balance), then pick the saved card in the Payment method selector." [7][1]
2. L16 "(recommended $100, minimum $50; ...)" -> keep as MYEZ budgeting and add: "OpenAI's own minimum is $5; credits expire after 1 year and are not refundable." [1][24]
3. L16 "Fund EARLY: a small prepayment in submission week can leave the account on the lowest rate tier (not verified against OpenAI's current tier rules)." ->
   "Since 2026-10-06 the tier depends only on total credit purchases (Build $5, Launch $100, Grow $500), with no waiting period.
   Under $100 in total stays Build, whose limits exceed the app's need. The Build constraint that can bite is the $500/month usage limit." [2][4][5][6]
4. L17 "Settings -> Limits: read the usage tier and the TPM / RPM for the model in use; send me the tier name only." ->
   "Settings -> Organization -> Limits: send the Usage Tiers name and the Rate limits RPM/TPM for gpt-4o and gpt-4o-mini." [2]
5. L18 "Project -> Budget: set a monthly budget with alerts at 50 % and 80 %." ->
   "Settings -> Organization -> Limits -> Spend -> Edit spend limit. The $120 limit with 80 % and 100 % alerts already exists (ledger): add a 50 % alert and decide Enforce a hard limit (on = 429 at the cap)." [9]
6. L19 "Data controls: turn organisation data sharing OFF (decision D3 = A, recommended)." -> superseded by OA2 (the owner's decision; the docs do not contradict the sentence):
   "Data controls -> Sharing: keep all three settings Enabled for all projects (D3 = B, disclosed) and send their state." [15]
7. L19 "Read whether Chat Completions storage is on by default for the project and tell me yes/no" ->
   "Read Settings -> Organization -> Data controls -> Data retention -> API call logging. It is an organization setting that can be scoped to selected projects. Send its value; Enabled per call = no." [16][25]
8. L22 "After the canary passes: revoke the OLD key (API keys page)." ->
   "Revoke the three old Active keys (ledger) after identifying who uses the 2026-02-09 key. Revocation takes effect within seconds, and a deleted key cannot be restored." [20][29]
9. L24 "Sentry `python-fastapi` has shown the 429 `credit_balance_exhausted` family since 2026-10-03; no compare has reached a provider since." ->
   "Sentry python-fastapi recorded 361 OpenAI 429 quota events (330 on 2026-10-02 and 31 on 2026-10-03, UTC) and none since, because U13 gates every compare.
   The events' error.code is unread; the -$0.03 balance fits credit_balance_exhausted." [7]

## D. Facts for the privacy policy (U8) and U3c

- Training: since 2023-03-01, API data is not used to train OpenAI models unless the organization opts in to share data [12].
- This organization has opted in: all three Sharing settings read "Enabled for all projects" (ledger 12:56), and OA2 keeps them on.
  The U8 sentence "we have not opted in" is therefore false for this organization, and the policy must disclose sharing (OA2).
- Sharing scope: when "Enabled", the inputs and outputs of enabled projects are shared with OpenAI. It can cover all projects or selected projects, and can be turned off at any time (medium) [15].
- Feedback: rating a response with thumbs up or down can let the whole conversation be used, even after opting out (medium) [30]. Do not rate compare text in the Playground.
- Retention: abuse-monitoring logs are kept for up to 30 days for all API usage. They are kept longer only when the law requires it, or to protect the services or third parties [12].
- Zero Data Retention and Modified Abuse Monitoring remove content from those logs, but both need OpenAI's prior approval [12].
- store default: the chat.completions reference shows no default for store [14].
  The migration guide says "Chat completions are stored by default for new accounts" but never defines "new accounts" (medium) [13]. This organization's "API call logging" reads "Enabled per call" (ledger 12:56).
- openai==3.3.1 omits store when the caller does not pass it, so today the server-side default applies (pinned SDK source, completions.py:120,281).
- A stored completion can be listed only if it was stored with store=true [31]. No page states how long stored completions are kept.
- U3c pins store=False in guarded_llm_create (app/services/api_budget_service.py:951; create calls at :967 and :974). That covers all 15 chat call sites in 5 files and disables storage for every chat call [13].
- client.moderations.create at content_safety_service.py:252 bypasses guarded_llm_create; store does not apply to it.
- U3c does not change the 30-day abuse-monitoring logs [12].
- U3c does not change prompt caching. For gpt-4o and gpt-4o-mini the cache is in memory: about 5-10 minutes of inactivity, up to one hour. The 24h default covers only the listed gpt-5.x and gpt-4.1 models [17].
- U3c does not change data sharing: no official page says store=False exempts a call from the Sharing setting (inference).
- Whether store=False keeps a call off the Logs page when logging is "Enabled for all projects" is not documented.

## Not verifiable from the public docs: read it in the dashboard

- Complimentary daily tokens (D10-D12): eligibility, caps, the positive-balance rule, and whether the bare aliases count. Ledger 13:05 records a pane read: Build 250K/day for the gpt-4o group and 2.5M/day for the gpt-4o-mini group.
  Read: Data controls -> Sharing (banner), and Usage -> chat completions grouped by service tier ("data sharing incentive tier").
- Maximum purchase and maximum balance under the "trust tier" [1]: read the Buy credits dialog.
- Auto-reload default threshold and restore-to amount: read the "Use auto-reload" fields.
- How fast the tier is recalculated after a purchase: read Settings -> Organization -> Limits -> Usage Tiers once the balance updates.
- Organization-level alert unit (dollars or percent) and its button label: read Settings -> Organization -> Limits -> Spend.
- Create-key dialog labels (All / Restricted / Read Only, the permission rows) and the default owner type: read the API keys page -> create dialog.
- Default model allow/deny list of "Default project": read the project's Limits -> "Model Usage" and confirm gpt-4o and gpt-4o-mini are allowed.
- IP allowlist: no documented path. Check only if the canary returns 401 "IP not authorized" [7].
- Legacy user-key deactivation on 2026-10-22: only a community post mentions it (low). Check email and the dashboard banners. The ledger shows project keys on "Default project".
- Service-account keys recommended for production (K5): no official sentence found.
- Enterprise privacy page wording (D3): unreadable (403). Cite the your-data guide [12] instead.

## E. Sources (official pages, read 2026-10-08)

[1] https://help.openai.com/en/articles/8264644-setting-up-and-managing-prepaid-api-billing (updated about 2026-09-15)
[2] https://developers.openai.com/api/docs/guides/rate-limits
[3] https://help.openai.com/en/articles/6614457-troubleshooting-api-usage-and-spend-limits (updated 2026-10-07)
[4] https://developers.openai.com/api/docs/changelog (entry Oct 6, 2026)
[5] https://developers.openai.com/api/docs/models/gpt-4o
[6] https://developers.openai.com/api/docs/models/gpt-4o-mini
[7] https://developers.openai.com/api/docs/guides/error-codes
[8] https://help.openai.com/en/articles/5955604-troubleshooting-api-rate-limits-and-429-errors (updated 2026-10-07)
[9] https://developers.openai.com/api/docs/guides/spend-limits
[10] https://help.openai.com/en/articles/9186755-managing-projects-in-the-api-platform (updated last month)
[11] https://developers.openai.com/api/docs/deprecations
[12] https://developers.openai.com/api/docs/guides/your-data
[13] https://developers.openai.com/api/docs/guides/migrate-to-responses
[14] https://developers.openai.com/api/reference/python/resources/chat/subresources/completions/methods/create
[15] https://help.openai.com/en/articles/10306912-sharing-feedback-evaluation-and-fine-tuning-data-and-api-inputs-and-outputs-with-openai
[16] https://help.openai.com/en/articles/9687866-admin-and-audit-logs-api-for-the-api-platform
[17] https://developers.openai.com/api/docs/guides/prompt-caching
[18] https://developers.openai.com/api/docs/guides/production-best-practices
[19] https://developers.openai.com/api/docs/guides/rbac
[20] https://developers.openai.com/api/docs/api-reference/authentication
[21] https://developers.openai.com/api/docs/guides/admin-apis
[22] https://developers.openai.com/api/docs/guides/terraform/projects-and-access.md
[23] https://help.openai.com/en/articles/10478918-reviewing-api-usage-and-costs
[24] https://openai.com/policies/service-credit-terms/ (updated January 1, 2026)
[25] https://developers.openai.com/api/reference/python/resources/admin/subresources/organization/subresources/audit_logs/methods/list.md
[26] https://developers.openai.com/cookbook/examples/evaluation/use-cases/completion-monitoring
[27] https://developers.openai.com/api/docs/guides/terraform/service-accounts
[28] https://developers.openai.com/api/reference/go/resources/admin/subresources/organization/subresources/projects/subresources/service_accounts
[29] https://developers.openai.com/api/reference/go/resources/admin/subresources/organization/subresources/projects/subresources/api_keys/methods/delete
[30] https://help.openai.com/en/articles/5722486-how-your-data-is-used-to-improve-model-performance
[31] https://developers.openai.com/api/reference/python/resources/chat/subresources/completions/methods/list
[32] https://developers.openai.com/api/reference/overview
