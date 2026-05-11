# Qaren ToS Fact Base — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` (or `superpowers:subagent-driven-development` if executing in this session) to work through this plan task-by-task.

**Goal:** Produce `c:\Users\SynAckITPC\Downloads\qaren_ai_tos_answers_english.md` — a single self-contained fact base answering all 365 sub-questions in `qaren_ai_tos_questions_english.md`, with file:line evidence, ready for a downstream AI to draft the App Store / Google Play Terms of Service and Privacy Policy.

**Architecture:** 4 parallel forensic agents (1 Opus + 3 Sonnet) produce structured fact reports for backend, frontend, database+infra, and existing-legal+store-config domains. Main session (Opus) does cross-validation, personally verifies 5 high-risk facts, then synthesizes the final markdown deliverable section-by-section with incremental saves.

**Tech Stack:** N/A — analysis task. Reads Python (FastAPI), TypeScript (React Native + Expo), SQL (Supabase migrations), Markdown (existing legal docs), JSON (app.json, package.json).

**Design doc:** `docs/plans/2026-05-06-tos-fact-base-design.md`

**Constraints (legal material — zero mistakes):**
- Every code-derived claim must have a `file:line` reference.
- No fabricated values for legal entity, address, email, registration numbers — strict "Undecided".
- No legal interpretation — PDPL articles cited factually only.
- No invention — agents that can't determine something from code mark "Cannot determine from code" rather than guess.

---

## Phase 1 — Parallel forensic agents (Tasks 1-4)

Tasks 1-4 are dispatched **simultaneously in a single message** with multiple Agent tool uses. None depends on the others. Total wall-clock ~30-40 minutes.

---

### Task 1: Dispatch Agent A — Backend forensics (Opus)

**Why Opus:** Data-flow tracing (what data leaves Bahrain, what reaches OpenAI/Sentry/Serper) is the highest-stakes legal-accuracy work in the doc.

**Tool:** `Agent`
**`subagent_type`:** `general-purpose`
**`model`:** `opus`
**`description`:** `Backend forensics for ToS fact base`
**`isolation`:** none (read-only analysis, no edits)

**Prompt (paste into Agent prompt parameter):**

```
You are doing forensic analysis of the Qaren backend (FastAPI on Railway) for a legal fact base that will be used by another AI to draft the App Store / Google Play Privacy Policy and Terms of Service.

GOAL: Produce a structured fact report covering every piece of data the backend handles, every external API call, every storage write, and every retention boundary.

HARD RULES:
1. Every claim must include a file:line reference. No claim without evidence.
2. If you can't determine something from code, write "Cannot determine from code" — never guess.
3. No legal interpretation — just facts.
4. Use exact field names from the code, not paraphrased.

FILES TO READ (read all, don't skip):
- app/main.py — middleware stack, router registration, env vars
- app/api/*.py — all 13 route files (text, image, url, auth, history, share, feedback, admin, legal, version, usage, referral, image)
- app/services/*.py — all services. Key ones: structured_comparison_service, extraction_service, openai_service, serper_service, database_service, audit_service, usage_service, behavior_service, cohort_service, referral_service, feedback_service, push_token_service (if exists), sentry_service, firecrawl_service, scrapedo_service, model_router_service, api_budget_service
- app/middleware/*.py — security headers, request_id, error_handler, rate_limiter, logging_config
- app/utils/*.py — url_validator, sanitizer
- app/legal/privacy_policy.md (READ — this is what we currently say; flag staleness against actual code)
- app/legal/terms_of_service.md (READ — same)

PRODUCE 6 SECTIONS:

# SECTION 1: API endpoints inventory
Every route registered, with: HTTP method, path, auth requirement (none/auth-required/admin-key), rate limit, file:line of the handler, what user input it accepts, what it returns. Group by router.

# SECTION 2: External API calls — what data leaves the backend
For each external service (OpenAI, Serper, Supabase, Upstash Redis, Sentry, Firecrawl, Scrape.do, frankfurter.app, Apple/Google identity providers via Supabase), enumerate:
- The exact code call site (file:line)
- What payload fields are sent
- What's returned
- Whether the call is cached (and TTL)
- Whether the user-identifiable data is included or stripped before sending

CRITICAL: Trace the OpenAI prompt construction in extraction_service.py, structured_comparison_service.py. List every variable that ends up inside system/user messages. The CLAUDE.md privacy invariant says "no raw demographics in prompts" — VERIFY this in code, do not just trust it. Show the relevant lines.

CRITICAL: Trace Sentry's before_send scrubber (sentry_service.py and main.py wiring). List exactly which fields are scrubbed and which pass through.

# SECTION 3: Data the backend stores
For every Supabase table written-to and every Redis key set, enumerate:
- Table/key name
- Code path that writes (file:line)
- Field names being written
- TTL or retention semantics (Redis EXPIRE; Supabase columns with cleanup logic; "indefinite" if none)

# SECTION 4: Authentication, sessions, and security posture
- Token storage on backend (Redis blacklist for revoked tokens?)
- JWT verification flow (file:line)
- Session token TTL
- Rate-limiter rules per route (slowapi decorators)
- Account deletion mechanism — read delete_user_cascade SECURITY DEFINER function and the route that calls it. List exactly what gets deleted.
- Brute-force lockout mechanism
- HTTPS enforcement (HSTS headers in security middleware)
- CSP rules
- Admin authentication (X-Admin-Key + hmac.compare_digest)
- API key storage (env var only, never in code)

# SECTION 5: Logging
- What gets logged at each level (file:line of each log call in services + middleware)
- Where logs go (stdout → Railway → ?)
- Whether IP, user_id, email, or other identifiers appear in logs
- Whether prompts/outputs are logged

# SECTION 6: Existing legal docs vs. code
Read app/legal/privacy_policy.md and app/legal/terms_of_service.md. List every claim made in those docs and mark each:
- ✅ Confirmed by code
- ⚠️ Stale (code has changed since)
- ❌ Contradicted by code
Cite the file:line that confirms or contradicts.

OUTPUT FORMAT: Plain markdown, structured under the 6 section headings above. Use bullet lists with file:line citations. Aim for ~3000-4500 words total. Be exhaustive within those sections — this is the highest-stakes report.
```

**Verification (when agent returns):**
- Confirm 6 sections present.
- Confirm every bullet has a file:line citation OR explicitly says "Cannot determine from code".
- Spot-check 5 random citations against actual files.

---

### Task 2: Dispatch Agent B — Frontend forensics (Sonnet)

**Why Sonnet:** Mostly enumeration of permissions, SDKs, screen behavior. Low reasoning load when given an explicit checklist.

**Tool:** `Agent`
**`subagent_type`:** `general-purpose`
**`model`:** `sonnet`
**`description`:** `Frontend forensics for ToS fact base`
**`isolation`:** none

**Prompt:**

```
You are doing forensic analysis of the Qaren React Native + Expo frontend (located in SmartCompareApp/) for a legal fact base that will be used by another AI to draft the App Store / Google Play Privacy Policy and Terms of Service.

GOAL: Produce a structured fact report covering every screen, every permission, every storage write, every user-input field, every SDK.

HARD RULES:
1. Every claim must include a file:line reference. No claim without evidence.
2. If you can't determine something from code, write "Cannot determine from code" — never guess.
3. Use exact field names and exact permission strings from app.json.

FILES TO READ:
- SmartCompareApp/app.json (entire file — extract permission usage strings verbatim)
- SmartCompareApp/package.json (every dependency — see Section 5 below)
- SmartCompareApp/App.tsx (root navigation tree)
- SmartCompareApp/index.ts (entry point)
- SmartCompareApp/src/screens/*.tsx (every screen — enumerate)
- SmartCompareApp/src/services/*.ts (api.ts, authService.ts, certificatePinning.ts, pushTokenService.ts if exists, others)
- SmartCompareApp/src/i18n/*.ts (just check what languages: 'en', 'ar')
- SmartCompareApp/src/theme/*.ts (just confirm colors/fonts — for app description)

PRODUCE 6 SECTIONS:

# SECTION 1: Screens inventory
For every screen file in src/screens/, list:
- Screen name and file:line of the export
- One-sentence purpose
- Whether it requires auth
- What user inputs it captures (form fields, camera, image picker)
- What it sends to the backend (which API endpoint)

# SECTION 2: Permissions declared in app.json
Enumerate every permission plugin in app.json with:
- Plugin name
- iOS Info.plist usage string (verbatim from app.json)
- Android equivalent (if explicit; otherwise note "Expo default for this plugin")
- The screen(s) that actually trigger the permission request

Specifically note absence of: location, microphone, contacts, calendar, bluetooth, advertising-id-related permissions.

# SECTION 3: Local storage
For every storage write/read in the app, list:
- Mechanism (expo-secure-store / AsyncStorage)
- Key name
- What is stored (token / user object / preferences / cache)
- File:line of the write

CRITICAL: Verify per CLAUDE.md security pattern that auth tokens go to expo-secure-store, NOT AsyncStorage. Show the file:line.

# SECTION 4: Network calls
- Base URL of the backend (api.ts)
- Whether HTTPS is enforced (URL scheme + cert pinning)
- Cert pinning configuration (certificatePinning.ts — list pinned hashes verbatim)
- Whether any direct third-party calls are made from the app (i.e., not through our backend) — this includes Google Sign-In SDK, Apple Sign-In SDK, expo-notifications push token registration. For each: where the call is made, what data is sent, what's returned.

# SECTION 5: Frontend SDKs (every package.json dependency)
For each dependency in package.json (skip dev dependencies and pure UI libs like vector-icons / svg / paper / blur), state:
- Package name + version
- Purpose in this app
- Does it transmit data off-device? If yes, where? What data?

Be explicit about ABSENCE: confirm the app does NOT include Firebase, Crashlytics, Sentry frontend SDK, Mixpanel, Amplitude, AppsFlyer, Adjust, Meta SDK, Google Ads SDK, OneSignal, RevenueCat, Stripe, Tap, BenefitPay, AppCheck, attribution libs.

# SECTION 6: Onboarding & data captured at signup
- OnboardingScreen.tsx flow — list each step and what data the user provides
- Optional vs required at each step
- Where the data is sent (which API endpoint)
- How preferences are saved (file:line)

OUTPUT FORMAT: Plain markdown, structured under the 6 section headings. Bullet lists with file:line citations. Aim for ~2000-3000 words total.
```

**Verification:**
- Confirm 6 sections.
- Confirm every cited file path actually exists (spot-check 3).
- Confirm Section 5 explicitly enumerates the absence list.

---

### Task 3: Dispatch Agent C — Database + infra forensics (Sonnet)

**Why Sonnet:** Schema enumeration from migrations is structured factual work.

**Tool:** `Agent`
**`subagent_type`:** `general-purpose`
**`model`:** `sonnet`
**`description`:** `Database and infra forensics for ToS fact base`
**`isolation`:** none

**Prompt:**

```
You are doing forensic analysis of the Qaren database (Supabase project qulajmyxdbdkchvecmvc) and infrastructure (Railway, Upstash Redis, Supabase, OpenAI, Serper, Sentry, Firecrawl, Scrape.do) for a legal fact base.

GOAL: Produce a structured fact report on the database schema, RLS policies, retention, hosting regions, and security posture.

HARD RULES:
1. Every claim must reference a migration file:line, a CLAUDE.md section, or be marked "Cannot determine from code".
2. Hosting region claims must come from public provider documentation OR be marked "Public default — verify in provider dashboard".
3. No invention.

FILES TO READ:
- migrations/*.sql (all 12 files: 001, 002, add_share_token, 010, 011, 012, 013, 014, 015, 016, 017)
- CLAUDE.md (sections on database, environment variables, services)
- MEMORY.md
- app/services/database_service.py (just for the dual-client pattern and table list)

PRODUCE 5 SECTIONS:

# SECTION 1: Tables, columns, and what each holds
For every table touched by any migration, produce a final-state schema:
- Table name
- Column names + types
- Whether each column holds personal data and (one phrase) what kind (email, IP, name, free-text query, demographic, etc.)
- Whether RLS is enabled on the table (check migrations 010, 011, 014, 017 explicitly for ENABLE ROW LEVEL SECURITY statements)
- The RLS policies that exist on it (verbatim from CREATE POLICY)
- Foreign keys / cascades

Tables to cover (cross-check with database_service.py): users, comparisons, search_logs, products, bahrain_approved_drugs, comparison_feedback, user_events, user_usage, admin_audit_log, product_specs, product_prices, product_reviews, demographics-related views (vw_cohort_*), referral_invites, referral_redemptions, push_token-related (migration 015).

# SECTION 2: Retention semantics per data type
For each kind of stored data, state retention:
- Comparison history — how long? (read code for cleanup or "indefinite")
- Search logs — same
- User_events / analytics events — same
- admin_audit_log — same
- product_specs / product_prices / product_reviews (L2 cache: 30d / 24h / 14d per CLAUDE.md — VERIFY in code)
- Redis keys (TTLs) — verify against cache_service.py and api_budget_service.py
- Sentry events — public provider default (state "public default 30 days unless plan modifies; verify in Sentry dashboard")

# SECTION 3: Hosting regions (cross-border data flow)
For each external service, list:
- Provider
- Hosting region (cite source — Supabase project setting, Railway region, Upstash region, OpenAI's policy URL on data residency)
- Whether the user data leaves Bahrain
- Whether public provider docs claim "data not used for training" (OpenAI API: yes by default since 2023; Anthropic: yes; verify and cite)

CRITICAL: Be honest about defaults — if the Supabase project region is not visibly recorded in the repo, mark "Cannot determine from code; verify in Supabase dashboard project settings". Do the same for Railway region and Upstash region.

# SECTION 4: Security posture summary (factual, no interpretation)
- HTTPS-only (HSTS header — cite middleware/security.py)
- Token revocation mechanism (cache_service.py — Redis blacklist)
- Cert pinning (frontend — already covered by Agent B; just note it exists)
- Rate limiting (slowapi — list the routes and rate limits)
- Brute-force lockout (audit_service.py — 5 failures → 15 min Redis lock)
- Admin auth (X-Admin-Key + hmac.compare_digest, rate limited 30/min)
- Password rules (10+ chars, 1 upper, 1 lower, 1 digit — cite source)
- Encryption at rest (Supabase default — state "managed by Supabase; AES-256 per Supabase public docs")
- Encryption in transit (TLS 1.2+ via Railway/Cloudflare — state public default)

# SECTION 5: Account deletion mechanism
Read migration 010 (or wherever the function is defined) for delete_user_cascade SECURITY DEFINER function. List every table that gets deleted from. Cross-check the auth_routes.py delete-account endpoint that calls it.

OUTPUT FORMAT: Plain markdown under 5 sections. Aim for ~2000-2500 words.
```

**Verification:**
- Confirm 5 sections.
- Spot-check that hosting-region claims are either cited or explicitly marked "verify in dashboard".
- Confirm RLS policies are quoted verbatim, not paraphrased.

---

### Task 4: Dispatch Agent D — Existing legal + store config audit (Sonnet)

**Why Sonnet:** Comparing existing docs against an explicit checklist is structured work.

**Tool:** `Agent`
**`subagent_type`:** `general-purpose`
**`model`:** `sonnet`
**`description`:** `Existing legal docs and store config audit`
**`isolation`:** none

**Prompt:**

```
You are auditing the EXISTING privacy policy and terms of service for the Qaren app, plus the App Store / Google Play configuration in app.json. You will not write new legal text — you will produce a fact report on what's there now and what's missing or stale.

GOAL: Identify exactly what the current legal docs claim, what they don't address, and how they line up with the app.json store config.

HARD RULES:
1. Quote, don't paraphrase, when summarizing what the existing docs say.
2. Cite file:line for every claim.
3. Use the question file `c:\Users\SynAckITPC\Downloads\qaren_ai_tos_questions_english.md` as the comprehensive coverage checklist.

FILES TO READ:
- app/legal/privacy_policy.md (existing privacy policy — read in full)
- app/legal/terms_of_service.md (existing terms — read in full)
- SmartCompareApp/app.json (store-relevant config: name, slug, bundleIdentifier, package, plugins with usage strings, supportsTablet, usesAppleSignIn)
- c:\Users\SynAckITPC\Downloads\qaren_ai_tos_questions_english.md (the 22-section question checklist — use as coverage map)

PRODUCE 4 SECTIONS:

# SECTION 1: Privacy policy — what it covers
Walk through privacy_policy.md and list every topic it addresses (data types, retention, third parties, user rights, contact info, children, cross-border, etc.). Quote directly when stating what it claims. Note the last-updated date.

# SECTION 2: Privacy policy — what it does NOT cover (gaps vs. the question checklist)
Cross-reference the existing privacy policy against the 22-section question file (sections 4, 5, 7, 8, 10, 14, 15, 16, 17 are most relevant). List every question that the existing policy does NOT answer. Be specific.

# SECTION 3: Terms of service — what it covers vs. gaps
Same treatment for terms_of_service.md. Most relevant question sections: 6 (AI), 11 (notifications), 12 (payments), 13 (UGC), 17 (product/store links), 19 (legal texts).

# SECTION 4: app.json store config snapshot
Inventory:
- App name (display) and slug
- iOS bundleIdentifier
- Android package
- supportsTablet (iOS)
- usesAppleSignIn (iOS)
- Permissions plugins with usage strings (verbatim)
- Build properties (e.g., networkInspector for iOS)
- Anything else a reviewer would see

OUTPUT FORMAT: Plain markdown under 4 sections. Aim for ~1500-2500 words. Be specific and quote the existing docs verbatim where you make claims about them.
```

**Verification:**
- Confirm 4 sections.
- Confirm Section 1 contains direct quotes from privacy_policy.md.
- Confirm Section 2 maps gaps to specific question numbers in the checklist file.

---

### Task 5: Wait for all 4 agent reports

Tasks 1-4 dispatch in parallel; main session waits. Once all 4 complete, proceed.

---

## Phase 2 — Cross-validation pass (Tasks 6-7, main session, Opus)

### Task 6: Cross-reference the 4 agent reports

**Goal:** Find inconsistencies between agent reports before synthesis. If Agent A says "field X is sent to OpenAI" and Agent C says "field X is stored in column Y", confirm they refer to the same thing.

**Steps:**

**Step 6.1:** Open the 4 agent reports in scratch space.

**Step 6.2:** Build a data-flow matrix in scratch (do not save):

| Field name | Captured by frontend at | Stored in DB column | Sent to OpenAI? | Sent to Sentry? | Logged? |

Source rows from Agents A, B, C. Reconcile differences.

**Step 6.3:** Reconcile: for any row where two agents disagree, read the relevant file myself and resolve. Note the resolved fact.

**Step 6.4:** Reconcile permission strings: Agent B's app.json strings must match what Agent A claims about the camera/image-picker route handlers' input.

**Verification:** Matrix has no `?` cells; every cell is either filled or marked "N/A".

---

### Task 7: Personally verify the 5 high-risk facts

The 5 facts I will verify by reading code myself, not delegated:

**Fact 1: What data appears in OpenAI prompts.** Read `app/services/extraction_service.py` `_build_preferences_prompt` and `build_personality_prompt` callsites and the verdict prompt construction. Confirm: does the prompt include any `email` / `phone` / `user_id` / `gender` / raw `age` / raw `governorate` text? CLAUDE.md privacy invariant says no — verify.
- Run: `Read` tool on `app/services/extraction_service.py` (full file)
- Run: `Grep` for `email`, `phone`, `user_id`, `gender`, `age_group` inside the file with `-n`

**Fact 2: What data appears in Sentry events post-scrub.** Read the Sentry `before_send` scrubber.
- Run: `Grep` for `before_send` across `app/`
- Read the function; confirm scrub list includes JWT, API keys; note what's NOT scrubbed (e.g., user_id, IP)

**Fact 3: What is logged at all.** Spot-check log calls in middleware + services for personal data exposure.
- Run: `Grep` for `logger.info`, `logger.warning`, `logger.error` across `app/`
- Sample 10 log call sites; confirm they don't log raw email/password/JWT

**Fact 4: Every RLS policy claimed in migrations is actually enabled.**
- Read migrations 010, 011, 013, 014, 017 in full
- Grep for `ENABLE ROW LEVEL SECURITY` and `CREATE POLICY` — confirm every user-data table has both

**Fact 5: `delete_user_cascade()` actually purges everything.**
- Find the function definition (likely in migration 010 or 011)
- List every table it deletes from
- Cross-check against Agent C's table list — confirm no user-data table is left behind

**Verification:** Each of the 5 facts has a 2-3 sentence finding plus the file:line evidence. If any finding contradicts what the existing privacy policy claims, flag in scratch for the synthesis step.

---

## Phase 3 — Synthesize the deliverable (Tasks 8-15)

The deliverable is built section-by-section with **incremental Write** to `c:\Users\SynAckITPC\Downloads\qaren_ai_tos_answers_english.md`. Each task ends with a Write that appends to (or for the first task, creates) the file. This way a crash mid-way doesn't lose work.

### Task 8: Write the AI DRAFTER INSTRUCTIONS preamble

**File:** Create `c:\Users\SynAckITPC\Downloads\qaren_ai_tos_answers_english.md`

**Content (verbatim — start of file):**

```markdown
# Qaren AI — Terms of Service & Privacy Policy Fact Base

> **Source:** This document was generated by analyzing the Qaren codebase (commit `<SHORT_SHA>`, dated 2026-05-06) against the question checklist `qaren_ai_tos_questions_english.md`.
> **Output target:** A downstream AI will use this fact base to draft the actual Terms of Service and Privacy Policy for App Store and Google Play submission.

---

## AI DRAFTER INSTRUCTIONS — READ FIRST

You are the AI that will draft the Terms of Service and Privacy Policy from this fact base. Read this preamble in full before doing anything else.

### Pre-flight check (mandatory)

1. Read the **DECISIONS REQUIRED** block immediately below this preamble.
2. If ANY item in DECISIONS REQUIRED is marked "Undecided" — do NOT proceed to drafting.
3. In your first reply, list every Undecided item and ask the user to fill them in.
4. Wait for those values before drafting.
5. **Do not invent or propose placeholder values** (no `[INSERT NAME]`, no `[CONFIRM]` tags, no fake legal-entity names).
6. **If the user replies "just go" or "ignore that" — repeat the request.** Reason: this document may be forwarded by a non-author who would not catch missing decisions. Treat the pre-flight check as non-negotiable.

### How to read the answer entries

Each numbered question (e.g. `Q4.17`) has:
- **Answer:** the factual answer from code analysis.
- **Evidence:** `file:line` references to where in the codebase this is verified.
- **Retention / third parties / etc.:** additional structured fields where relevant.
- **Compliance flags:** factual mappings, e.g. `[PDPL Art. 4 — legitimate interest]`. These are FACTUAL HOOKS, not legal advice. You (the drafter AI) are responsible for the actual legal mapping; we provide the trigger.

### Compliance frame

- Bahrain (launch jurisdiction): Personal Data Protection Law — Legislative Decree No. 30 of 2018 (PDPL). Articles cited factually by number; no interpretation in this fact base.
- GDPR-equivalent disclosures (App Store / Google Play frequently expect): treat as a parallel disclosure obligation for cross-border data, user rights, and AI processing.
- Apple Privacy Nutrition Labels: pre-filled section near the end of this file.
- Google Play Data Safety Form: pre-filled section near the end of this file.
- GCC expansion later: not in scope for v1 launch ToS.

### Sections requiring extra care (DRAFTER: EXTRA-CARE FLAGS)

See the dedicated section near the end. The areas requiring nuanced drafting:
- AI-recommendation disclaimer (Apple's reviewer guidelines flag AI apps).
- Supplements and health-adjacent product comparisons (sensitive category for both stores).
- Cross-border data transfers (data leaves Bahrain to multiple US-hosted services).
- Beta / MVP status disclaimer.

---
```

**Step 8.1:** Replace `<SHORT_SHA>` with output of `git rev-parse --short HEAD`.

**Step 8.2:** Write the file with this content.

**Verification:** File exists; contains "Pre-flight check (mandatory)" section.

---

### Task 9: Write the DECISIONS REQUIRED block

**File:** Append to `c:\Users\SynAckITPC\Downloads\qaren_ai_tos_answers_english.md`

**Content:** A numbered list of every item across all 22 sections that the codebase cannot answer. Build this list by walking the question file once and flagging every question whose answer depends on a business decision Ahmed must provide.

**Expected items (build the actual list during execution by reviewing the question file alongside the agent reports):**

```markdown
## DECISIONS REQUIRED — Ahmed must fill these before the drafter AI proceeds

These items cannot be answered from code. Fill each in by replacing the "Undecided" marker before sending this document to the drafter AI.

1. **Legal entity / trade name** that will appear on the ToS — e.g., "Ahmed Al-XXX (sole proprietor)" or a registered LLC. — Undecided
2. **Commercial registration number** (CR), if applicable — Undecided
3. **Official address** for legal notices in Bahrain — Undecided
4. **Official support email** (e.g., support@qaren.app) — Undecided
5. **Official privacy email** (e.g., privacy@qaren.app) — Undecided
6. **Privacy / deletion request response SLA** (e.g., 30 days) — Undecided
7. **Apple Developer Program account holder** (individual vs. entity) and account email — Undecided
8. **Google Play Console account holder** and account email — Undecided
9. **Public-facing website URL** (e.g., https://qaren.app) — Undecided
10. **Public privacy policy URL** (where Apple/Google will fetch) — Undecided
11. **Public terms of service URL** — Undecided
12. **Public account-deletion URL or in-app path** — Undecided (in-app path EXISTS — see Q3.10)
13. **ToS effective date** for the published version — Undecided
14. **Lawyer review status** — user stated no lawyer is involved — confirm this remains the case before publishing
15. **Beta vs. production launch label** for the App Store / Play listing copy — Undecided
16. **(any other gaps surfaced during synthesis)**

---
```

**Step 9.1:** Compile the actual list during execution by walking the question file and the agent reports together.

**Step 9.2:** Append to the answer file.

**Verification:** Block ends with `---`; every item has "Undecided" or a clear instruction.

---

### Task 10: Synthesize answers for question Sections 1-7

**File:** Append to the answer file.

**Sections covered:** General App Status (1), App Description (2), Accounts (3), Data Collected (4), Onboarding (5), AI (6), Sensitive Data (7).

**Format per question:**

```markdown
### Q4.17: IP address?

**Answer:** Yes — collected for rate limiting and security audit logging.

**Evidence:**
- `app/middleware/rate_limiter.py:<LINE>` — slowapi key_func extracts `request.client.host`.
- `app/services/audit_service.py:<LINE>` — `login_attempt` and `lockout` events store IP in `admin_audit_log.ip_address`.

**Retention:** Rate-limit counters in Redis with 60s TTL. `admin_audit_log` rows in Supabase — no automatic purge in code (retention indefinite until manual cleanup).

**Sent to third parties:** No — stays on Railway and Supabase + Upstash.

**Compliance flags:** `[PDPL Art. 4 — legitimate interest, security]` `[Apple Privacy Label: Identifiers → IP Address — linked to user]` `[Google Play Data Safety: Personal info → IP address]`
```

**Step 10.1:** Walk the question file sections 1-7 in order.

**Step 10.2:** For each numbered sub-question, write the entry using the format above. Use evidence from agent reports + my own verification.

**Step 10.3:** For questions answered by an "Undecided" decision, the entry references the DECISIONS REQUIRED number.

**Step 10.4:** Append to the answer file.

**Verification:** Every sub-question in sections 1-7 of the input file has a corresponding entry. No `[CONFIRM]` tags. No fake names.

---

### Task 11: Synthesize answers for question Sections 8-14

Same pattern. Covers: SDKs (8), Permissions (9), Analytics (10), Notifications (11), Payments (12), UGC (13), Minors (14).

Section 8 (SDKs) is the longest — for each SDK in our actual stack (OpenAI, Serper, Supabase, Upstash, Sentry, Firecrawl, Scrape.do, frankfurter.app, Apple/Google identity, Expo modules, expo-secure-store, expo-notifications, react-native-ssl-public-key-pinning, etc.), answer the 5 standard questions per SDK from the question file:
- Why do we use it?
- What data does it receive?
- Does the data leave Bahrain?
- Is the service mandatory for the app to function?
- Can it be disabled?

Section 9 (Permissions) — quote the iOS usage string verbatim from app.json for each, and confirm Android does NOT request location/contacts/microphone.

Section 10 (Analytics) — confirm absence of Firebase Analytics / GA / Mixpanel / Amplitude on the frontend; describe the backend event tracking via `user_events` table (events posted via /api/v1/events) and what data each event contains.

Section 12 (Payments) — list freemium tiers from `usage_service.py`; confirm no Stripe / Apple IAP / Google Play Billing / RevenueCat is wired in code yet; flag this as Undecided for launch monetization.

Section 14 (Minors) — confirm whether DOB is collected (it isn't); state the app's stance per existing legal docs.

**Verification:** Every sub-question has an entry; SDK section gives the 5-field treatment per SDK.

---

### Task 12: Synthesize answers for question Sections 15-22

Covers: Storage/Retention/Deletion (15), Security (16), Product/Store Links (17), App Store/Play Config (18), Legal Texts (19), Support/Legal Entity (20), Items We Need (21), Critical Questions (22).

Section 15 — pull retention numbers from Agent C's report.

Section 16 — security posture from Agent C + my Fact 4-5 verifications.

Section 17 — explain that the app shows external store links (Amazon, Noon, Carrefour, etc.) but does NOT execute purchases; clarify the "no responsibility for the product or store" position; note absence of affiliate links currently (referral_routes.py is invitee/referrer between users, NOT retailer affiliate revenue).

Section 18 — pull from Agent D's app.json snapshot + DECISIONS REQUIRED.

Section 19 — explain where privacy/terms appear in the app (legal_routes endpoints; ProfileScreen link if present — Agent B should have noted this).

Section 20 — almost entirely DECISIONS REQUIRED references.

Section 21 — for each requested file/screenshot, point to the source-of-truth location in the repo and let Ahmed decide whether to attach.

Section 22 — Critical Questions: pull short Yes/No answers from across all earlier entries. This is a summary cheat-sheet for the drafter AI.

**Verification:** Every sub-question has an entry; Section 22 provides crisp Yes/No answers with cross-references to fuller entries above.

---

### Task 13: Write the APPLE PRIVACY NUTRITION LABELS section

**File:** Append.

**Content:** Pre-filled form fields ready for App Store Connect.

```markdown
## APPLE PRIVACY NUTRITION LABELS

Paste these into App Store Connect → App Privacy.

### Data Types Collected

For each, fill: **Linked to User** (yes/no), **Used for Tracking** (always **No** for Qaren — see DRAFTER: EXTRA-CARE FLAGS), **Purpose**.

#### Contact Info
- **Email Address** — Linked to User: Yes — Tracking: No — Purposes: App Functionality, Authentication
- **Name** — Linked to User: Yes — Tracking: No — Purposes: App Functionality (display name in profile)

#### Identifiers
- **User ID** (Supabase UUID) — Linked to User: Yes — Tracking: No — Purposes: App Functionality
- **Device ID** — Not collected
- **Advertising ID** — Not collected

#### User Content
- **Photos or Videos** (when user submits a product photo) — Linked to User: Yes — Tracking: No — Purposes: App Functionality (vision-based product identification)
- **Other User Content** (free-text product queries, comparison feedback) — Linked to User: Yes — Tracking: No — Purposes: App Functionality, Product Personalization

#### Usage Data
- **Product Interaction** (comparisons run, products viewed) — Linked to User: Yes — Tracking: No — Purposes: App Functionality, Analytics, Product Personalization

#### Diagnostics
- **Crash Data** (Sentry, backend only) — Linked to User: No (Sentry before_send scrubs identifiers — verify final list during synthesis) — Tracking: No — Purposes: App Functionality

#### Sensitive Info — none collected.
#### Health & Fitness — none collected.
#### Financial Info — none collected.
#### Location — none collected (no precise or coarse location request).
#### Contacts — none collected.
#### Browsing/Search History — Search queries are stored but classified above under User Content.

### Do you or your third-party partners use data to track users? **No**

(Verify the Sentry, Supabase, Upstash, OpenAI subprocessor positions before publishing.)
```

**Step 13.1:** Build this from agent reports + my Fact 1-2 verifications. Adjust "Linked to User" flags based on actual code.

**Verification:** Every Data Type has Linked-to-User and Tracking columns filled.

---

### Task 14: Write the GOOGLE PLAY DATA SAFETY FORM section

**File:** Append.

```markdown
## GOOGLE PLAY DATA SAFETY FORM

Paste into Play Console → App content → Data safety.

### 1. Data collection and security

- **Is all of the user data collected by your app encrypted in transit?** Yes (HTTPS + cert pinning — see Q16.1).
- **Do you provide a way for users to request that their data is deleted?** Yes (in-app account deletion — see Q3.8).

### 2. Data types

For each: **Collected** (yes/no), **Shared with third parties** (yes/no), **Optional** (yes/no), **Purpose**, **Ephemeral** (no — data is persisted).

#### Personal info
- **Name** — Collected: Yes — Shared: No — Optional: Yes (only if user fills name field at signup) — Purpose: Account management, App functionality
- **Email address** — Collected: Yes — Shared: No (sent to Supabase Auth — Supabase is our processor, not a third-party recipient for the purposes of this form) — Optional: No — Purpose: Account management
- **User IDs** (Supabase UUID) — Collected: Yes — Shared: No — Optional: No — Purpose: Account management
- **Address, Phone, Race/ethnicity, Political/religious/sexual orientation, Other** — none collected.

#### Photos & Videos
- **Photos** — Collected: Yes (only when user uploads a product photo) — Shared: Yes (sent to OpenAI for vision processing) — Optional: Yes — Purpose: App functionality
- **Videos** — none collected.

#### App activity
- **App interactions** (comparisons, products viewed, searches) — Collected: Yes — Shared: No — Optional: No — Purpose: App functionality, Analytics, Personalization
- **In-app search history** — Collected: Yes — Shared: No — Optional: No — Purpose: App functionality, Personalization
- **Other user-generated content** (feedback comments) — Collected: Yes — Shared: No — Optional: Yes — Purpose: App functionality

#### Device or other IDs
- **Device or other IDs** — none collected.

#### Diagnostics
- **Crash logs** (Sentry, backend only) — Collected: Yes — Shared: Yes (Sentry processes them) — Optional: No — Purpose: App functionality
- **Diagnostics, Performance** — none beyond crash logs.

#### Location
- **Approximate or precise location** — none collected. (We use Cloudflare CF-IPCountry header to derive country at the edge for personalization but do NOT geolocate the user — see Q4.6.)

#### Financial info, Health & fitness, Messages, Audio files, Files & docs, Calendar, Contacts — none collected.

### 3. Encryption

- **Encrypted in transit:** Yes
- **Encrypted at rest:** Yes (managed by Supabase + Upstash + Railway providers)

### 4. Data deletion

- **In-app deletion:** Yes — see Q3.8 for the path.
- **Web deletion:** Undecided — see DECISIONS REQUIRED.
```

**Verification:** Every category has answers; the Personal info / App activity / Photos sections match the inventory in question Section 4.

---

### Task 15: Write CROSS-BORDER DATA TRANSFER MAP and DRAFTER: EXTRA-CARE FLAGS

**File:** Append.

```markdown
## CROSS-BORDER DATA TRANSFER MAP

| Provider | Hosting region | Data received | Subprocessor doc URL | Notes |
|---|---|---|---|---|
| Supabase | <FILL FROM AGENT C OR MARK "verify in dashboard"> | Email, name, password hash, all user content tables | https://supabase.com/legal/dpa | Primary database. Encrypted at rest (AES-256 per public docs). |
| Railway | <FILL OR MARK> | Backend logs (request IDs, IPs) | https://railway.com/legal/dpa | Application host. |
| Upstash Redis | <FILL OR MARK> | Cache keys (TTL ≤24h), rate-limit counters, token revocation hashes | https://upstash.com/legal/dpa | No personal content; operational metadata only. |
| OpenAI | US | Free-text product queries, product spec extraction prompts, vision API uploads of product photos | https://openai.com/policies/data-processing-addendum | API tier — public policy says "data not used to train models for API customers". |
| Serper | US | Search queries (product names, retailer URLs) | https://serper.dev | Aggregated Google Search results — query content is the search payload. |
| Sentry | EU or US (<FILL FROM CONFIG>) | Backend exception traces (post-scrub: no JWT, no API keys; user_id may pass through — verify) | https://sentry.io/legal/dpa | Errors only, not all events. |
| Firecrawl | US | Public retailer URLs only (no user data) | https://firecrawl.dev | Scrapes public product pages on our behalf. |
| Scrape.do | US/Turkey-based provider (<FILL>) | Public retailer URLs only | https://scrape.do | Same. |
| frankfurter.app | EU | Currency code pairs (no user data) | (free public API) | Daily exchange rates, no PII. |
| Apple (Sign-in / Push) | US | Email, full name (only on first SIWA), APNs device token | (Apple developer agreement) | iOS only. |
| Google (Sign-in / FCM) | US | Email, full name, profile photo URL | (Google developer agreement) | Android only. |

> **PDPL Art. 11-13 — cross-border transfer:** All personal data leaves Bahrain. The drafter AI must include a clear cross-border transfer disclosure citing each provider above and the legal basis (user consent at signup + legitimate interest for security/service operation).

---

## DRAFTER: EXTRA-CARE FLAGS

The drafter AI must NOT gloss over these areas. Each requires careful, explicit drafting.

### A. AI-recommendation disclaimer
The app's core function is AI-generated product comparisons (verdicts, scoring, personalized recommendations). Apple's App Review Guidelines (4.7, 5.1.1) and Google Play's AI policy require:
- Clear in-app disclosure that recommendations are AI-generated and not professional advice.
- A user-facing feedback / report mechanism (we have one — see Q6.14).
- No medical / legal / financial guarantees.

The ToS MUST include an "AI-generated content" clause stating: recommendations are informational, not guarantees; the user is responsible for purchase decisions; Qaren is not liable for product quality, safety, or third-party retailer behavior.

### B. Supplements / health-adjacent comparisons
The app compares supplements category (iHerb scraping, Bahrain Drug Database, etc. — see CLAUDE.md). The ToS MUST include:
- A "not medical advice" disclaimer.
- A direction to consult a healthcare professional before consuming supplements.
- A statement that Qaren does not verify medical safety claims of products.

This is a sensitive category for Apple (Health & Fitness adjacent) and Google.

### C. Cross-border data transfer language
All user data leaves Bahrain (see Cross-Border Data Transfer Map above). The Privacy Policy MUST:
- Enumerate the third-party processors.
- State the legal basis for each transfer (PDPL Art. 11-13 — user consent + legitimate interest for service operation).
- Provide the user the right to object (PDPL Art. 6).

### D. Beta / MVP launch disclaimer
Per the question file, the app status is launch-stage. The ToS should include:
- Service-availability language (no uptime guarantee).
- Right to modify/discontinue features.
- The Privacy Policy and ToS may be updated; users notified via in-app prompt.

### E. Account deletion specifics
Verify the in-app deletion path before publishing. From code: tap Profile → Account → Delete account → confirm. The deletion is irreversible and atomic via `delete_user_cascade()` (see Q3.9). The Privacy Policy MUST state: "Once deleted, your account and all associated data cannot be recovered." Do not promise restoration.

### F. Children & minors
The app does not collect date of birth and does not target minors, but does NOT have an age gate. The ToS should include a 13+ minimum age statement (Apple/Google standard) and a parental consent path for under-18 if required by local law.

### G. Free-tier limits
The app has freemium tiers (Free: 3 lifetime + 10/month + 3/day; Premium: 70/month + 10/day — see Q12.X). The ToS should disclose the limits and the right to modify them.

---

## DOCUMENT END

Generated 2026-05-06 by Claude (Opus 4.7). Cross-validated against codebase commit `<SHORT_SHA>`. For questions about this fact base — not the resulting Privacy Policy / ToS — return to the Claude session that produced it.
```

**Verification:** All extra-care areas have a clear "MUST" sentence; transfer map has every provider; document ends with `## DOCUMENT END`.

---

## Phase 4 — Final QA (Tasks 16-17)

### Task 16: Line-by-line cross-check against the question file

**Steps:**

**Step 16.1:** Open the answer file and the question file side-by-side.

**Step 16.2:** Walk question file sections 1-22 in order. For each numbered sub-question, locate the corresponding entry in the answer file. Confirm:
- Entry exists.
- Entry has an Answer line.
- Entry has Evidence (or explicit "Cannot determine from code" or "Undecided").
- No `[CONFIRM]` tags anywhere.
- No fake legal entity names.

**Step 16.3:** If any question is missing — write the missing entry now, before declaring done.

**Step 16.4:** Confirm DECISIONS REQUIRED block at top references match every "Undecided — see DECISIONS REQUIRED #N" reference inline.

**Verification:** Every sub-question (estimated 365 across 22 sections) has an answer entry.

---

### Task 17: Hand-off summary to user

**Steps:**

**Step 17.1:** Output a short summary message to the user listing:
- Where the deliverable lives.
- The DECISIONS REQUIRED count (e.g., "16 items need your input").
- The DRAFTER: EXTRA-CARE FLAGS the user should know about.
- Any items the analysis flagged as stale in the existing privacy/terms docs that should be reconciled.

**Step 17.2:** Offer next steps:
- Fill the DECISIONS REQUIRED block.
- Hand the doc to the drafter AI of choice.
- (Optional) ask Claude to also produce updated `privacy_policy.md` / `terms_of_service.md` for the in-app endpoints once the drafter AI returns the public ToS.

**Verification:** User has a clear, short next-steps list.

---

## Out-of-scope reminders (do NOT do these)

- Do not draft the actual Terms of Service or Privacy Policy. The downstream AI does that.
- Do not commit changes unless Ahmed asks (per CLAUDE.md).
- Do not update `app/legal/privacy_policy.md` or `app/legal/terms_of_service.md` based on this analysis — those updates wait until the drafter AI produces the new public versions and Ahmed approves them.
- Do not edit `app.json` permission strings, even if Agent D suggests improvements.
- Do not produce Arabic translations.

---

## Risks & mitigations

| Risk | Mitigation |
|---|---|
| Agent invents a fact without evidence | Hard rule in every prompt: every claim needs file:line; verification step rejects unevidenced claims. |
| Sonnet agent miscounts permissions or misses an SDK | Each Sonnet prompt includes an explicit ABSENCE-LIST checklist; agent must confirm each absence. |
| Hosting regions claimed without verification | Prompt explicitly tells agents to mark "verify in dashboard" rather than guess. Cross-Border Map preserves these markers in deliverable. |
| Synthesis loses fidelity (paraphrases evidence away) | Direct quotes preserved for legal text claims; file:line preserved verbatim. |
| Crash mid-synthesis loses work | Tasks 8-15 each Write incrementally to the deliverable file. |
| The drafter AI ignores the pre-flight check | Hard rule + repeat-on-"just go" instruction in preamble. Cofounder safety stated explicitly. |
| Stale existing privacy_policy.md misleads the synthesis | Agent D produces a stale-vs-current diff; synthesis uses code as ground truth, not existing docs. |

---

## Acceptance

The plan is complete when:
- All 17 tasks are checked off in the executing session.
- The deliverable file exists at `c:\Users\SynAckITPC\Downloads\qaren_ai_tos_answers_english.md`.
- Final QA confirms every numbered question in the input file has an entry.
- Hand-off summary delivered to user.
