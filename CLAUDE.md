# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Purpose

SmartCompare (app brand: **Qaren / قارن**) — Intelligent product comparison engine for the GCC market (Bahrain, Saudi Arabia, UAE, Kuwait, Qatar, Oman). Goal: if users still go to Google or ChatGPT after using us, we failed.

## 🚨 APP STORE PRODUCTION SHIP-BLOCKERS (read EVERY session)

These items DO NOT block TestFlight internal testing (≤100 invited testers) — those ship fine today. But they WILL block Apple App Store public-production submission and Apple's automated review will reject the build until both are resolved. Claude Code must remind Ahmed at the start of any Bundle/PR that targets App Store production.

1. **App icon ICN-0001 byte-identity** — `SmartCompareApp/assets/{icon,splash-icon,adaptive-icon}.png` are byte-identical to Expo's `npx create-expo-app` template scaffolding (SHA-256-verified by Bundle D native-ops 2026-05-24). Ahmed approved the concentric-circles design — the bytes need to differ. **Fix:** regenerate same visual as a unique render (Claude-Design re-export OR `scripts/` PIL/Cairo script with emerald `#10B981` accent / Qaren wordmark). Tracked in `docs/plans/bundle-d-followups.md`.

2. **Full legal-doc redraft** — current `app/legal/{privacy_policy,terms_of_service}.md` had brand strings rebranded (Bundle D R22) but the content is the pre-Bundle-D draft with names swapped — NOT a Qaren-jurisdiction redraft. 15 legal decisions still pending per `docs/plans/2026-05-16-tos-decisions-pending.md` (entity name, GCC jurisdiction, DPO contact, PDPL clauses, breach timeline, etc.). Apple may push back on jurisdictional mismatch (generic US-style template, no PDPL specifics). **Fix:** complete the 15 decisions + draft Qaren-specific clauses + republish via `legal_routes.py` + regen `landing/{privacy,terms}.html`.

**Routine before App Store production submission:** icon byte-different ✓, legal docs Qaren-jurisdiction-redrafted ✓, `pip-audit --strict` clean ✓ (BLOCKING in CI since #120) + `npm audit --audit-level=high` triaged — **MEASURED 2026-09-01: 43 vulnerabilities (1 low, 20 moderate, 21 high, 1 critical), exit 1**, so this is NOT clean today and the CI step stays reporting-only until the direct offenders (axios ships to devices) are bumped ✓, QA static audit grep pack re-run ✓, ASC Privacy Nutrition Labels verified against current data flows ✓. **TestFlight internal ships freely without these — they're App Store production gates only.**

## Operating Principles

1. **Quality first, then optimize.** Confidence not false certainty.
2. **Don't fetch what you already have, don't call twice when once is enough, don't guess when you can verify.** API calls cost money.
3. **Plan → Approve → Implement → Test.** Read `docs/CLAUDE_CODE_CONTEXT.md` before major changes.
4. **Multi-file features (3+ files, FE+BE):** use parallel 4-Opus TeamCreate (backend, frontend, test, qa).
5. **After major features:** update CLAUDE.md, MEMORY.md, `docs/CONTEXT_SESSION_LOG.md`.
6. **Path-restricted commits in team sessions:** `git commit -m "msg" -- <paths>` — NOT `git commit -- <paths> -m "msg"` (the `--` is a path separator).
7. **Push before deleting branches.** `git push` before `git branch -d`. Orphaned commits are recoverable via `git cherry-pick` from reflog within ~30 days but invisible to teammates.
8. **Multi-agent stalls: escalate after 30 min OR 3 silent nudges.** 4-Opus teams stop processing inbox while staying "available". If silent >30 min with uncommitted state despite `SendMessage` nudges → dispatcher takeover. Earlier trigger: if 3+ consecutive nudges produce zero tool-call evidence (no commit, grep, file read), spawn replacement OR take over directly via dispatcher session. Direct takeover is faster when user explicitly authorizes. Pattern surfaced Session 47 + reinforced Bundle E S2 2026-05-30 (frontend-v2 stalled across #40/#42/#43/#44; direct dispatcher edit+commit+OTA closed multiple rounds).
9. **Team comms (Bundle B S1): ACK-every-ruling from session START** — teammates check inbox between EVERY task and ACK dispatcher rulings before proceeding (2 of 5 agents built past unread corrections; diagnostic tell: a close-out that re-asks an answered question). Announce multi-turn runs ("suite going, ~10 min") before going quiet. Dispatcher verifies contested "complete" claims against the actual commit (`git show`), never the report. Before strike-counting an idle agent: fetch their branch + check WIP mtimes — idle can mean working.

## Critical: Two app/ Directories

- **`app/`** (root) — The DEPLOYED backend. Railway runs `uvicorn app.main:app` from root.
- **`backend/app/`** — Older/alternate version. NOT deployed. Do NOT edit.
- Always edit files in root `app/` for changes to take effect.

## Commands

### Backend
```bash
# Run locally
uvicorn app.main:app --reload --port 8000

# Syntax check a file
python -m py_compile app/services/structured_comparison_service.py

# Test endpoint (production)
curl https://web-production-58776.up.railway.app/health
curl "https://web-production-58776.up.railway.app/api/v1/text/compare?q=iPhone+15+vs+Galaxy+S24&nocache=true"

# Deploy: push to main, Railway auto-deploys in ~90s
git push origin main
```

### Frontend (React Native / Expo)
```bash
cd SmartCompareApp
npx expo start                    # Dev server (use --clear after dep changes)
npx tsc --noEmit                  # TypeScript check (ground truth — see below)
npx expo install --check          # Verify deps match SDK version
npx expo-doctor                   # Full project health check
eas update --branch <channel>     # OTA push of JS bundle to existing builds
eas build --profile <profile>     # Fresh native build for testers / App Store
```
IDE/LSP TS diagnostics on Windows are unreliable (`typescript-lsp` plugin bug, see MEMORY.md). Trust ONLY `npx tsc --noEmit` exit code — ignore stale "Cannot find module" / "JSX flag not set" errors from system-reminders unless `tsc` actually fails.

**Two-lever launch model:** Backend deploys (Railway via `git push origin main`, ~90s) and mobile JS bundle deploys (EAS via `eas update`/`eas build`) are **independent**. Merging to main does NOT push frontend code to phones — phones run their last-bundled JS until an EAS update/build reaches them. New mobile features need BOTH levers fired.

### Dependencies
- Backend: **`requirements.txt` is a GENERATED lock — never hand-edit it.** Declare deps in `requirements.in` (runtime) or `requirements-dev.in` (test/lint tooling), then recompile:
  ```bash
  uv pip compile requirements.in     -o requirements.txt     --universal --python-version 3.12
  uv pip compile requirements-dev.in -o requirements-dev.txt -c requirements.txt --universal --python-version 3.12
  ```
  The dev lock is compiled with `-c requirements.txt` so the two locks can never disagree on a shared transitive.
  `--universal` is required: it emits platform markers (e.g. `uvloop ; sys_platform != 'win32'`) so a lock compiled on Windows still installs correctly on Railway's Linux. Install with `pip install -r requirements.txt -r requirements-dev.txt`. Railway/Nixpacks installs `requirements.txt` (NOT pyproject.toml). CI's **Lock is current** step recompiles and diffs, so a `.in` edit without a recompile fails the build.
- Frontend: `npm install` in `SmartCompareApp/`
- **Expo native deps:** use `npx expo install <pkg>` (not `npm install`). JS/native version mismatch causes cryptic `NativeWorklets` / `HostFunction` crashes in Expo Go.

### Migrations
Supabase DDL (`migrations/*.sql`): preferred path is **Supabase MCP** (`mcp__plugin_supabase_supabase__apply_migration`) — tracks migration history table. Fallback: [SQL Editor](https://supabase.com/dashboard/project/qulajmyxdbdkchvecmvc/sql/new). **Gotcha:** SQL Editor wraps multi-statement scripts in one transaction, so a failing view rolls back the ALTER TABLE before it — always verify schema after apply (`information_schema.columns`). Before `CREATE TABLE IF NOT EXISTS`, check existing schema — stale tables with different columns cause silent index/policy failures.

Applied 010–032 (all via MCP since 013; 027–032 = Bundle B B.1, dispatcher-applied 2026-06-10). Files in `migrations/*.sql`; rollbacks in `migrations/rollback/*.sql`. **Index predicates must be IMMUTABLE** — no `now()`/`CURRENT_*` in `CREATE INDEX ... WHERE` (passes syntax, fails at apply with 42P17; static guard `tests/test_migration_index_predicate_immutability.py` catches it; 028's canon composite is `idx_pwe_workflow_time`, never recreate `idx_pwe_recent`). When dispatcher corrects DDL at apply, re-align the repo SQL+rollback to the APPLIED schema immediately (verify live `pg_indexes` first). Load-bearing: **020** `comparisons.schema_version` (v1=legacy/hidden, v2=renderable; default 2 — gates history list/get filter). **021** `users.device_fingerprint_hash` + partial idx (anti-farming; matches `^[a-f0-9]{64}$`). **023** (Bundle B/C/D) drops `weekly_invites_used`, adds `lifetime_invites_consumed INT` — referral cap **3 LIFETIME per device**. **024** adds `'top_tier'` to `users.preferences.budget` CHECK enum (5-tier; backwards-compat).

## Architecture

### Backend (FastAPI + Python 3.12)

**Entry:** `app/main.py` — env vars, middleware stack, 14 routers in `app/api/`:
- `/text/*` → `text_routes.py` → `structured_comparison_service.py` (primary + SSE, rate-limited)
- `/image/*` → `image_routes.py` → GPT-4o-mini vision → auto-compare (HEIC detection)
- `/url/*` → `url_routes.py` (single URL, SSRF-protected, 10/min)
- `/auth/*` → `auth_routes.py` → Supabase Auth (login, register, refresh, profile, email, password, social, deletion, demographics, cohort-profile). Per-route rate limits.
- `/comparisons/*` → `history_routes.py` (auth required)
- `/share/*` → `share_routes.py` (POST auth, GET public strips personalization)
- `/feedback`, `/events` → `feedback_routes.py` (auth-optional, fire-and-forget). `FeedbackRequest`: 4 fields only (`useful, comparison_id, mattered_most, change_suggestion`); ContactUsScreen prefixes `[Bug] Subject\n\nBody` for grep.
- `/referrals/*` → `referral_routes.py` (gated `ENABLE_REFERRAL_SYSTEM`)
- `/admin/*` → `admin_routes.py` (X-Admin-Key, `hmac.compare_digest`, 30/min)
- `/legal/*` → `legal_routes.py` (no auth, markdown files)
- `/app/*` → `version_routes.py` (force-update from env vars)
- `/usage/*` → `usage_routes.py` (freemium tier)

**Middleware stack** (outermost → innermost): RequestID → SecurityHeaders (HSTS, CSP, X-Frame-Options) → ErrorHandler → CORS → slowapi rate limiter

**Unified error format:** `{ success: false, error: "msg", code: "ERROR_CODE", request_id: "uuid" }`. Codes: `AUTH_REQUIRED`, `FORBIDDEN`, `NOT_FOUND`, `RATE_LIMITED`, `VALIDATION_ERROR`, `INTERNAL_ERROR`. Frontend `parseApiError()` handles both `.error` (new) and `.detail` (legacy FastAPI).

**Core service:** `app/services/structured_comparison_service.py` (~1,500 lines, orchestrator only)
- `StructuredComparisonService` — **per-request instances** via `get_comparison_service()` (NOT singleton — concurrency safety).
- `compare_from_text(query, region, vision_products?, selected_category?, user_id?)` — main entry.
- `compare_from_text_streaming(...)` — async SSE: specs→prices→reviews→scores→verdict→complete.
- **Pre-fetch:** Unified Serper search (1 call) shared by specs + reviews, cache-gated.
- **Phase 1:** specs + price parallel (specs reuses unified search).
- **Phase 2:** reviews + rating parallel (reviews reuses search; Phase 1 shopping feeds ratings).
- **Scoring** deterministic (`scoring_service.py`, $0): value badges, tradeoff pairs, confidence.
- **Behavioral profile:** fetched before scoring, updated fire-and-forget post-response.
- `_shopping_items_cache` populated in price search, cleared per-request.
- **Response keys:** `overview`, `specs`, `reviews`, `scoring`, `personalization`, `metadata`. BC aliases: `products`, `comparison`, `winner_index`, `recommendation`, `key_differences`.

**Decomposed modules** (extracted from monolith):
- `price_service.py` — pricing tiers, currency conversion, page scraping, iHerb, pharmacy JSON-LD
- `rating_service.py` — Tiered rating extraction, Google consensus, retailer classification
- `review_service.py` — Review fetching, content cleaning, citation replacement
- `fact_check_service.py` — Citation verification, cross-validation, confidence computation
- `response_builder.py` — `build_comparison_response()` for sync + streaming paths

**Price pipeline (3 tiers + page scraping + pharmacy JSON-LD):**
1. Serper Shopping (structured)
2. GPT-4o-mini extraction from organic results (Tier 3 sanity-checked)
3. GPT training-data estimate (`estimated: true`)

- **Page scrape** (`_fetch_page_price` → curl_cffi + JSON-LD/OG/microdata): Tier 1.5 cascade + supplements. Flag `ENABLE_PAGE_SCRAPE`.
- **Firecrawl** (Tier 1.5a, SPA pages, **30s timeout** — luxury SPAs >15s). **Scrape.do** (Tier 1.5d, residential proxies, only when curl fetched HTML w/ no price).
- **`curl_cffi` `impersonate="chrome"` defeats most Cloudflare/TLS-fingerprint walls** — a page that looks `render_required` is often just a TLS wall, NOT a true SPA; and the platform JSON API (`/products.json`, `/wp-json/wc/store/products`, Algolia, Unbxd, Hybris OCC `/occ/v2`, Adobe-Commerce GraphQL) is usually reachable even when the HTML PDP is walled. Probe the API endpoint before declaring a render-tier gap. (Proven 2026-06-25 BH/GCC discovery: cracked noon/extra/al-dawaa/nahdi/panda/sharafdg + the genuine-BHD supplement giants sporter/drnutrition.)
- **`GET /api/v1/text/prices/{product}` takes NO `nocache` param + NO category** → it serves stale cache and never engages category-gated adapters (nasser/bolo/boutiqaat). To verify a genuine-BH adapter end-to-end, use `compare?q=…&nocache=true` (resolves the category + honors nocache) — the bare prices endpoint will falsely show `estimated`.
- **API budget** (`api_budget_service.py`): Firecrawl 450/lifetime, Scrape.do 900/mo, Serper 2200/lifetime. 3 failures → 10min cooldown. Fail-open on Redis down.
- **Gate 0:** `_validate_price_query` + `_validate_scrape_url` reject garbage queries / search-category pages before burning credits.
- **Philosophy:** "MOST AUTHORITATIVE" not "lowest". Priority: official brand > authorized retailers > marketplaces. Counterfeits filtered (DHgate/AliExpress/Temu/Wish). `OFFICIAL_BRAND_DOMAINS` (25+) sorted first.
- `source_method` enum: `local_bhd | converted_usd | page_scrape | page_scrape_rendered | firecrawl | scrapedo_rendered | estimated`. `price_method_mismatch` flag set when products differ.
- **Supplements:** iHerb scrape → Bahrain pharmacy JSON-LD → Serper+GPT → Tier 3.

**Rating pipeline:** Tier 1 (Serper Shopping, trusted retailers) → Tier 2 (known retailers incl. luxury/fashion) → Tier 3 (eBay if review_count > 1000) → Fallback (GPT, unverified). Consensus: 3+ identical → Google product aggregate. iHerb ratings extracted during price scrape (zero extra calls). All ratings displayed without verified/unverified badges.

**URL sourcing:** Serper Shopping `link` primary, `_build_retailer_url()` fallback. Frontend `openRatingSource()` uses `rating_source.url` first.

**Supplement-specific:**
- Serper Shopping returns ZERO for supplements — iHerb direct scrape via `curl_cffi` instead.
- Non-iHerb brands (HealthAid, Vitabiotics): `_fetch_pharmacy_price()` → `site:bn.boots.com` → JSON-LD. Brand match space-insensitive. bolo.bh NOT indexed by Google (Vue SPA); bn.boots.com IS.
- **Bahrain Drug Database:** 655 products in `bahrain_approved_drugs`. `find_matching_drugs()` full-text search injected into spec prompt (supplements only).
- **Supabase gotcha:** `text_search()` needs `options={"type": "plain", "config": "english"}` (NOT kwargs); `.limit()` BEFORE `.text_search()` in chain.

**Key services** (in `app/services/`):
- `extraction_service.py` — GPT prompts, `CATEGORY_SPEC_SCHEMAS` (9 categories), structured verdict + review_summary. Injects personality + trust rules.
- `scoring_service.py` — Deterministic scoring ($0). 6 dims via `CATEGORY_DIMENSIONS`. Personalization caps ±30/10/5%.
- `prompt_personalities.py` — Per-category "language" via `build_personality_prompt(category)`.
- `trust_validation_service.py` — Cross-checks GPT claims vs deterministic scores.
- `behavior_service.py` — Decay-weighted profiles (30-day half-life): affinity, price range, dim sensitivity.
- `cache_service.py` — `_redis_get/_set/_incr/_expire` helpers. `api_budget_service` uses `redis_client.incrby/incrbyfloat` directly for atomicity.
- `api_budget_service.py` — Credit tracking + circuit breakers (Firecrawl/Scrape.do/Serper).
- `exchange_rate_service.py` — Daily rates from frankfurter.app, Redis-cached 24h, GCC fallbacks. `get_rate(from, to="BHD")`.
- `firecrawl_service.py` / `scrapedo_service.py` — JS rendering wrappers.
- `database_service.py` — **Dual Supabase client**: `get_user_supabase_client(token)` (anon+JWT, RLS) vs `get_admin_supabase_client()` (service-role). User-facing DB fns accept `access_token`. `get_supabase_client()` is deprecated alias for admin.
- `usage_service.py` — Freemium tier. Free 3 lifetime + 10/mo + 3/day; Premium 70/mo + 10/day. Redis + Supabase. **Device-bound (Migration 021):** `X-Device-Fingerprint` → SHA-256 at `users.device_fingerprint_hash`; free counters inherit on re-signup (anti-farming).
- `audit_service.py` — Fire-and-forget security events to `admin_audit_log` (login/lockout/usage_limit/injection_attempt).
- `product_data_service.py` — L2 DB cache: specs 30d, prices 24h (append-history), reviews 14d. Redis miss → DB → API.
- `cohort_service.py` — Singleton over `data/cohort_priors.json` (built from gitignored `data/surveys/` CSVs via `scripts/build_cohorts.py`). Hierarchical fallback exact → governorate → language → age → population.
- `model_router_service.py` — `get_model(priority="high")` returns `gpt-4o` below 80% of `DAILY_4O_CAP`, else mini. Atomic INCRBY per UTC date. 429 retries to mini once. Used by verdict; specs/prices/reviews stay on mini.
- `referral_service.py` — Smart Decision Referrals: `link_invite_to_user`, `try_trigger_loop2`, code gen.
- `abuse_detection_service.py` — `evaluate_invite()` priority SAME_DEVICE > DISPOSABLE_EMAIL > BELOW_REAL_ACTION_THRESHOLD (`elapsed_seconds` proxy, `REAL_ACTION_MIN_SECONDS` env default 5s).
- `push_service.py` — Expo Push (`qaren://profile/referrals`).
- `reengagement_service.py` — Daily cron `scripts/cron_reengagement.py`. 3 detectors (decision_insight/cohort_curiosity/decision_retrospective), 7-day per-user cap. Gated by `ENABLE_REENGAGEMENT_PUSHES` + `REENGAGEMENT_CANARY_PERCENT` via `feature_bucket.hash_bucket`.
- Other: `serper_service`, `feedback_service`, `drug_database_service`, `openai_service`, `sentry_service`, `analytics_service`, `auth_service`, `url_extraction_service`.

**Security** (`app/utils/`): `url_validator.py` — SSRF: resolves hostnames, blocks private/loopback/link-local IPs, allows only http/https.

**Middleware** (`app/middleware/`): request_id, security headers (HSTS, CSP, X-Frame-Options, nosniff), rate_limiter (slowapi, 10/min on compare), error_handler (Sentry capture + `before_send` JWT/key scrubbing), logging_config (structured JSON).

### Frontend (React Native + Expo)

**Location:** `SmartCompareApp/`. **App name:** Qaren (قارن). Bilingual EN/AR + full RTL.

**Navigation:** Bottom tabs (Home/History/Profile) via `@react-navigation/bottom-tabs`. Results as modal. Auth stack (Login/Register/ForgotPassword). Splash → Onboarding → Auth → Main in `App.tsx`. Paywall registered as `Stack.Screen` with `presentation: 'transparentModal'` (audit 2026-05-22 — was Modal-only; `navigation.navigate('Paywall')` was silent no-op).

**Design system:** `src/theme/index.ts` (emerald #10B981, Geist+Cairo). Components: Button, Card, Chip, SkeletonLoader, ProgressBar. i18n: `src/i18n/` (180+ keys EN/AR). (IconButton + ComparisonCounter were listed here but had zero render references — deleted as dead code 2026-09-01, M13-64.)

**Services:**
- `api.ts` — Axios → Railway (120s timeout). SSE via `streamComparison()` (fetch+ReadableStream, fallback to non-streaming). JPEG transcoding pre-upload.
- `authService.ts` — Supabase + social. **`verifyAuth()` returns `User | null`** (NOT boolean). Tokens in `expo-secure-store` (NOT AsyncStorage). OAuth nonces via `expo-crypto`. All `console.log` wrapped in `__DEV__`.
- `certificatePinning.ts` — Railway SSL pinning (LE intermediate SPKI). Init once from `api.ts`. EAS dev build only (no-op in Expo Go). Rotation in `docs/SECURITY_HARDENING_CONTEXT.md`.
- `sentry.ts` — `@sentry/react-native@8.11.1`. Mirrors backend `before_send` scrub (JWT/OpenAI/Firecrawl/Bearer/headers). DSN → `qaren-rr/react-native`. Sourcemap upload deferred (`SENTRY_AUTH_TOKEN` + plugin config).

### External APIs (use wisely — every call costs money)
- **OpenAI GPT-4o-mini** — Spec/price/review extraction, product identification. Combine calls.
- **Serper** — Google Search + Shopping API ($0.001/call). Don't search for what you already have. Key `0cda9843...` (rotated 2026-06-12; predecessor `3d304e...` depleted during S2 G6 tail — its Railway dashboard edit was never applied, fixed via CLI); cached = free, only `nocache=true` burns credits. **Rotation playbook:** new free account at serper.dev → set Railway env (CLI `railway variables --set`) + explicit `railway redeploy` + sync LOCAL `.env` and worktree copies in the same pass (local was found 2 rotations stale) → verify liveness via `GET /api/v1/text/prices/<product>` (NEVER a full compare — it rides the 30s cap edge and can't discriminate key-dead from slow-run) → **reset `budget:serper:lifetime` AND `DEL budget:serper:burn_alert_fired:*`** (S2 G1 `3125a07`: the 80%-burn alert sentinel is a no-expiry latch — a counter-only reset leaves the alert permanently suppressed for the new key; also note the counter is NOT key-scoped, so an unreset counter carries pre-rotation burn) → resolve the Sentry Search-error issues with a root-cause comment. Budget caution: escalation-heavy cold queries burn ~10-15 credits each post-B.0 (bahrain discovery adds a call per product); a full 200-query eval ≈ 600–1,000 credits.
- **Supabase** — PostgreSQL + Auth. Tables: users, comparisons, search_logs, product_* (specs/prices/reviews), comparison_feedback, user_events, user_usage, admin_audit_log, referral_invites/redemptions, bahrain_approved_drugs. Full schema in `migrations/010-026`.
- **Upstash Redis** — Response caching (prices 24h, specs/reviews 7d).

## Important Patterns

### Fact-checking (zero-cost cross-validation)
Every product has `fact_check` (`overall_confidence`: high/medium/low). Spec citations verified vs snippets; review sentiment vs Serper (0.8 tol); price vs Shopping median (30%). Zero extra API calls. **Ratings are NEVER AI-generated** — GPT prompt forbids generating `source_ratings`.

### `product.price` is an object, not a number
Backend returns `{ amount, currency, retailer, url, estimated }`. Frontend must access `product.price.amount`.

### GCC_REGIONS keys (extraction_service.py)
`bahrain`, `saudi_arabia` (NOT `saudi`), `uae`, `kuwait`, `qatar`, `oman`.

### Per-request service instances
`get_comparison_service()` returns a NEW instance per call (not singleton). Fresh `total_cost`, `api_calls`, `_shopping_items_cache` — no manual reset.

### Cost budget + caching
Target **$0.01/comparison** via unified search (1 Serper call shared by specs+reviews in `_fetch_product_data`). Track with `self.total_cost` / `_track_cost`. **Two-layer cache:** L1 Redis (specs/reviews 7d, prices 24h) → L2 DB via `product_data_service.py` (specs 30d, prices 24h, reviews 14d) → API. `?nocache=true` bypasses both. Camera passes `vision_products` directly, skipping `parse_product_query()`.

### Deterministic scoring + Prompt personalities + Personalization
See skill: `qaren-scoring` (auto-loads when `scoring_service.py`, dimension scores, value badges, personalization caps ±30/10/5%, behavior_service, or `scoring_v2` contract are mentioned). Key recall: 9 categories × 6 dimensions via `CATEGORY_DIMENSIONS`; price tiers budget/mid/premium/luxury; three-layer personalization (explicit ±30% → behavioral ±10% → session ±5%); `scoring_method` enum: `category_weighted` / `personalized` / `behavioral` / `cohort` / `default` / `invitee_quiz` (`cohort` = cohort priors moved the weights; `default` = `_empty_result`, fewer than 2 products). Rollback V1: `docs/ROLLBACK_SCORING_V1.md`.

### Auth + security hardening
- **RLS active** on all user-data tables (Migration 010). Cascade delete via `delete_user_cascade()` SECURITY DEFINER → `.rpc()`.
- **Tokens:** `expo-secure-store` (Keychain/Keystore). Logout revokes via Redis blacklist `revoked:{sha256(token)}` 1h TTL. `verify_token()` checks blacklist before Supabase.
- **`verify_token` returns `{id, email, access_token}`** — pass `current_user["access_token"]` to `get_user_supabase_client()` for user-scoped queries. **Never log `current_user` dict** — only `current_user["id"]`.
- **`X-Device-Fingerprint`** must match `^[a-f0-9]{64}$` (SHA-256 hex). Invalid silently dropped at `auth_routes.py`; same regex on `referral_routes.py` Pydantic field.
- **`/admin/*` static** dashboards gated by `_AdminAuthenticatedStaticFiles` in `main.py` — `X-Admin-Key` header OR HTTP Basic auth password.
- **Account deletion** cascades atomically (App Store req, 1/min). **Password:** 10+ chars, 1 upper/lower/digit. **Email change** requires current password.
- **Admin** 30/min. **History** uses `hmac.compare_digest` + merged 404/403. **Swagger** disabled in prod. **SQL LIKE** escaped. **Sentry `before_send`** scrubs JWT/API keys/query strings.
- **CSP** (`middleware/security.py`): strict `default-src 'none'` except `/admin/*` static (gets `'unsafe-inline'` + cdn.jsdelivr.net for Chart.js).
- **Login response:** `POST /auth/login` returns `{success, user, session, ...}` — access token at `session.access_token`, NOT top-level.
- **Regression tests:** `tests/test_security_regression.py` (~98 tests) — DO NOT delete or skip.

### SSE streaming
`GET /api/v1/text/compare/stream` → 10 SSE events with `progress` field (10/20/50/80). Frontend uses fetch+ReadableStream (not EventSource) with fallback to non-streaming.

### Feedback and event tracking
`POST /api/v1/feedback` + `POST /api/v1/events` (batch). Both auth-optional, fire-and-forget. Tables: `comparison_feedback` + `user_events` with RLS.

### Cohort personalization (Phase 1 LIVE)
See skill: `qaren-cohort` (auto-loads when `/api/v1/auth/demographics`, `cohort_priors.json`, `build_cohorts.py`, or `ENABLE_COHORT_PERSONALIZATION` are mentioned). Critical inline: flag is **ON in production**, code default `false`. Privacy invariant — NO raw age/gender/identity in prompt, only country/language/governorate thin context. Cohort match is **exact-case** — values must match `cohort_priors.json` keys exactly (`age_group: "25-34"`, `gender: "Male"/"Female"`, etc.). `VALID_PRIORITIES` extended with 6 cohort enums; `VALID_BRAND_ATTITUDE` adds `trust_known_brands`.

### Category selection (soft validation)
9 categories: Electronics, Grocery, Supplements, Makeup, Skincare, Haircare, Fragrances, Fashion, Other. `selected_category` is a hint — backend AI makes final call via `PRODUCT_PARSER_PROMPT`. Mismatch → `category_switched: true` + frontend info banner. Each category has dedicated spec schema in `CATEGORY_SPEC_SCHEMAS` (`extraction_service.py`).

### Sharing + History
22-char URL-safe token (`token_urlsafe(16)`) in `comparisons.share_token` (TEXT post-migration 017). Public access strips personalization. History: paginated, searchable, ownership-checked. On 401, clears session + redirects to auth. `create_share_token` raises `ShareTokenError` on persistence failure (loud-fail). **schema_version gate (Migration 020):** `save_comparison` only writes when `_validate_renderable(payload)` passes; sets `schema_version=2` + denormalized `product_names`. History list/count/get filter on `schema_version=2` — v1 rows invisible (use `include_legacy=True` for DELETE cleanup only).

### Qaren UX Redesign (merged 2026-05-07 — PR #2 ee91a87)
Cal-AI-Lite 17-step onboarding + black/emerald hybrid identity (emerald = signal color: winner reveal, success ticks, cohort accents — NOT primary CTA). `CANARY_NEW_ONBOARDING_PERCENT` in `SmartCompareApp/src/config/features.ts`; **currently 100**. Drop to 10 via EAS Update before App Store soft-launch, ramp 10→50→100 (NOT a Railway env var). Plan: `docs/plans/2026-05-06-qaren-ux-redesign{,.design}.md`.
- **Bucketing** (`featureBucket.ts`): djb2 over stable id (device-id pre-signup, user.id post). `hashBucket(id, percent)` pure — monotonic ramp invariant tested.
- **Theme + motion** in `SmartCompareApp/src/theme/{index.ts,motion.ts}`. Geist (EN) + Cairo (AR). `arabicLineHeightMultiplier = 1.7/1.5`. Haptic vocab {chip:light, stage:light, winner:medium} — **NO error/warning/heavy** (Build Principle #4: never scary).
- **17-step onboarding** (`src/screens/onboarding/`): OnboardingFlow + 17 steps. Cohort-key strings **exact-case** ('Capital', '25-34', 'Male'/'Female') matching `cohort_priors.json`. Step 14 theatrical loading 3.2s min. **Step 16 skipped when `isAuthenticated`** (F-S2.step16-skip task #42, 2026-05-29) — App.tsx already gates the Onboarding stack on `isAuthenticated === true`, so NewOnboardingHost hard-codes `isAuthenticated={true}` and the orchestrator's traversal skips Step 16 ("Save your advisor — Sign in") in production. The 17-step sequence (Step 16 present) is preserved when `isAuthenticated={false}` for any future anonymous-flow call site.
- **Hero illustrations** (SVG + Reanimated, **ZERO Lottie**): PhoneMockup, CohortBarChart, LoadingRings, RevealBurst. StageChecklist haptic ONLY on transition INTO done. (ConcentricMotif + StreamingProductCard were listed here but had zero render references — the stage-gated-SSE `StreamingProductCard` and `ResultsLoadingView` were pruned from the render path in Faithful-results Phase 2.1; both deleted as dead code 2026-09-01, M13-64.)
- **Results redesign:** section titles "Why we picked this" / "Where the runner-up wins" / "What's next?". CohortBadge inline below verdict.
- **Bonus expiry (Migration 018):** 3-day default. `cron_expire_bonuses.py` gated by `ENABLE_BONUS_EXPIRY_PUSHES`, 1000-row LIMIT, 24h-before push. **Entitlement computed from `get_user_active_bonus_count()` live rows, NEVER from stale INT counter** (counter is analytics/display only). Bundle B/C/D extends to 7d for new redemptions.
- **Attribution endpoint (Migration 019):** `POST /auth/attribution` (auth, 30/min). Pydantic Literal['friend','instagram','tiktok','app_store','google','other'] + DB CHECK mirror.
- **Min-display floor 1.2s** on Home→Results (cached responses still loading 1.2s so brand moment lands). Tracked via `loadingStartedAtRef` + `navigateToResultsWithFloor`.
- **Onboarding analytics:** `onboarding_started` on mount; `onboarding_step_completed` BEFORE setStep (payload reflects FINISHED step); `onboarding_completed` on Step 17.
- **Copy contract:** ZERO scary copy. Forbidden EN: `couldn't`, `try again`, `Failed to`. Forbidden AR: `تعذر`, `فشل`. Approved vocab in design doc §6.

### Smart Decision Referrals
See skill: `qaren-referrals` (auto-loads when `/api/v1/referrals/*` routes, invite codes (QR-XXXXXX), Loop 1/Loop 2, redemption chain, or `referral_invites`/`referral_redemptions` tables are mentioned). Critical inline: gated by `ENABLE_REFERRAL_SYSTEM` (default OFF in code, flipped in Railway). Bundle B/C/D moved cap to **3 LIFETIME per device** with fail-OPEN on DB error. Code redemption is **register-only** — `RegisterRequest.invite_code` accepts `^QR-[A-HJ-NP-Z2-9]{6}$`. Re-engagement gated by `ENABLE_REENGAGEMENT_PUSHES`.

### Bundle history (sessions 44-59)
Full bundle narrative (Session 44 onwards, including Bundle B/C/D ships + hot-fix sweeps + Path A + Sprint A Backend Comparison Engine Overhaul) lives in `docs/SESSION_BUNDLES.md`. CLAUDE.md keeps only the load-bearing prod-state callouts below.

**[STATUS 2026-05-22 — Bundle C in prod]** `ENABLE_BUNDLE_C_SCORING=false` in Railway; code default also `false`. Flag gates ONE site (`scoring_service.py:944`) — `None vs MISSING_SCORE=50` swap. In prod, missing signals get `MISSING_SCORE=50`, so A.4.9 silent dim omission never fires. The other ~95% of Bundle C (A.3.x/A.4.5/A.4.7/A.5.x/A.6.x/A.7.x/A.9.x/A.10.x, frontend §B) is unconditional and live. Canonical: **`docs/BUNDLE_C_PROD_STATE.md`**. Discipline before trusting "shipped/always-on" claims: `memory/feedback_docs_vs_railway_env_drift.md`.

**2026-06/07 ARC -- ARCHIVED 2026-08-30.** Seven Active-runtime blocks (all SHIPPED, all folded into prod) were moved VERBATIM into `docs/SESSION_BUNDLES.md`, section "2026-06/07 arc (archived from CLAUDE.md 2026-08-30)". Nothing was deleted. One pointer line per moved block, oldest first:
- Earlier 2026-06 bundles -- Bundle B S2 `5f137ec`, S3 `e08ddba`, genuine-BH latency+warmer `bce638f`/`2c27c5e`, fragrance-quality + CATEGORY-FAIRNESS `b7af94d`, faithful-results `5219cac`/`5999799`, walk-fixes `9172e62`, catfix `698006a`, fragrance-content-quality `2244ad4` (all in prod `b207bfa`) -> `docs/SESSION_BUNDLES.md` "2026-06 bundles roll-up".
- BH source-intelligence SHIPPED + the 400-source genuine-price DISCOVERY CATALOG (2026-06-25, main `e6afbcd`; catalog on `feature/bh-gcc-source-catalog`) -> same file, "2026-06-25".
- BH/GCC genuine-price source build + Zyte luxury render-tier (SHIPPED + ACTIVATED 2026-06-26, main `23b0f6b`, build `2e005e7`) -> "2026-06-26".
- Key rotation + all-category genuine-price fixes + THE CORRECTNESS REFRAME (2026-06-27, main `b207bfa` via PR #8) -> "2026-06-27".
- genuine-price CORRECTNESS structural redesign (2026-06-28, `feature/genuine-price-correctness` HEAD `7fb4127`, PR #9) + its ready-to-paste next-session prompt -> "2026-06-28".
- Electronics cellular cache-key parity (SHIPPED main `de9f420` via PR #14, 2026-07-01) -> "2026-07-01".
- Pre-launch price-discovery arc + scraper-fleet audit + "WARMER IS THE LEVER" (SHIPPED 2026-07-06/07, main `473f7cc`, PRs #26-30) + its ready-to-paste prompt -> "2026-07-06/07".

What that arc left behind is NOT in the archive - it is here: every flag it introduced is in **Environment Variables -> Feature Flags**; its durable process rules are in **Recurring durable gotchas** and **Ultracode Workflow-tool waves** just below; its eval anchor is in **Tests**.

**Recurring durable gotchas (load-bearing across the 2026-06 bundles):** (a) the eval (`eval_runner`) is a PROD-HTTP harness → it is POST-DEPLOY; a pre-deploy eval measures prod-without-the-change = meaningless. (b) **stale Redis cache masks a fix** — re-running the SAME pair serves the 7d-specs/24h-price cached pre-fix payload, so a "still broken" screenshot is usually stale cache, NOT a failed deploy → re-test a FRESH/different pair or `?nocache=true`. (c) worktrees DON'T inherit the gitignored `.env` (sibling `load_dotenv` walks UP, never reaching main's) → copy `.env` into each pytest-running worktree. (d) Serper headroom is POINT-IN-TIME, not sustained — heed the `budget:serper:<key8>:lifetime` counter, not one clean eval. (e) stale OS-scope `SUPABASE_*`/Upstash env can SHADOW `.env` (`load_dotenv()` no-override) → breaks local eval persist; `unset` + restart Claude Code. Sentry-5xx-on-status-change → [[feedback-sentry-5xx-capture-on-status-surface-change]]; no-prod-write-in-harness → [[feedback-no-prod-write-belongs-in-harness]]. (f) **`gh` GraphQL returns HTTP 401** with the git-credential `gho_` token (so `gh pr merge` + `gh pr view --json` fail) — use REST: `gh api repos/<o>/<r>/pulls/N`, `--method PUT .../merge`, `--method PATCH .../pulls/N` (token via `GH_TOKEN=$(printf 'protocol=https\\nhost=github.com\\n\\n'|git credential fill|sed -n 's/^password=//p')`). (g) **comm-gate harness:** `git worktree add --detach <dir> origin/main` + copy `.env` in + run the free-unit suite both sides + `comm -13` the sorted FAILED node-id sets → `branch-only-NEW` must be empty; the 46-line prod baseline is cached at `.qa-correctness/main-baseline-failed.txt`; `test_wrong_cheap_price_guard::TestSupplementNonCFPath` is NETWORK-flaky (live bolo.bh) → re-run a branch-only-new fail against main to tell flake from regression. (h) **Windows console cp1252** chokes on `→`/emoji in `print()` — dump workflow/JSON output to a UTF-8 file + `Read` it, never `print()` non-ASCII. (i) drop top docs commits + replay code commits onto a new main: `git rebase --onto origin/main <old-base> <top-code-commit>` then force-move the branch ref.

**Workflows:** worktree-team (`git worktree add -b feature/<name> ../smartcompare-<name> main` → 4-Opus TeamCreate, **`mode: "bypassPermissions"` REQUIRED** else sandbox blocks Bash → cross-QA → merge `--no-ff`); subagent-driven (`Agent(isolation: "worktree")` x2 parallel for backend-only ~6-8 tasks, validated Session 50); plan-writing-via-4-Opus uses skeleton with `<!-- OWNED BY: name -->` anchors so 4 agents Edit one doc concurrently. **Arabic-as-default DROPPED** (Session 44).

**Ultracode Workflow-tool waves (validated 2026-06-22 — fragrance-content-quality was planned + built + shipped via the `Workflow` tool, NOT TeamCreate):** PLAN = an adversarial gap-detection Workflow (parallel finders by lens → verify EACH finding against real code [~⅓ are no-ops] → synth) over a fact-checked SEED. EXECUTE = ONE Workflow per wave: **sequential implement agents** (race-free — exactly ONE writer on the shared tree at a time; per-task path-restricted commit) → **parallel adversarial reviewers**. Hard-won rules: (a) NEVER run the full test/jest suite inside an IMPLEMENT task (it ground ~35 min on a clean tree) — only the single REGRESSION reviewer runs it, and a temp-`main`-worktree `comm` of the sorted FAILED-test sets (`branch-only-NEW == []`) is the authoritative zero-regression gate (NOT per-task `git stash`, which is what caused the 35-min grind). (b) THROTTLE the verify/review fan-out — go SEQUENTIAL (≤2-3 concurrent); a server-side 529/rate-limit burst wipes the whole phase, and it gets MORE aggressive late in a long session (this session a 7-wide AND a 6-batch fan-out were both wiped instantly). Recover with `Workflow({scriptPath, resumeFromRunId})` after trimming the offending phase to sequential (the cached sweep replays instantly, only failed agents re-run); if it keeps failing, the dispatcher gates it directly (read code + grep) instead of fighting the limit. (c) The DISPATCHER GATES every wave — re-derive each reviewer finding against the real code: it caught real gate-fixes the TDD agents missed (a stale test pinning a removed value; FE praise-grammar gaps; an unscrubbed BC `comparison` alias) AND rejected false-flags (an order-flaky algolia test; a "gap" the backend already covered) — gate every reviewer finding ([[feedback-verify-llm-reviewer-findings]]). Two more hard-won rules (BH/GCC discovery, 2026-06-25): (d) the rate-limit burst RESETS in a fresh session and WORSENS with session age — run heavy/wide fan-out (discovery sweeps, large reviews) in a FRESH session, and batch ≤4 concurrent late in a long one (an 18-wide launch was wiped in 22s; batched-4 survived; web-research finders are inherently slow at ~1-2.5h/round, so a fresh session's gentler throttle matters). (e) Unescaped backticks INSIDE a backtick-delimited template-literal agent prompt break the Workflow script parse — build multi-line prompts with `array.join('\n')`, not nested backticks (cost two failed launches this session). (f) **COVERAGE-DRIVEN > hypothesis-driven for CORRECTNESS reviews (load-bearing, 2026-06-28):** a review workflow whose prompt LISTS the cases to probe only CONFIRMS the prompter + inherits the blind spots — TWO such dispatcher-gated review workflows greenlit a genuine-price fix that an external review then REPRODUCED leaks in; a 3rd **coverage-driven** sweep (agents ENUMERATE ≥12 REAL products/category × EVERY axis × BOTH directions [leak + over-rejection], reproduce through the RUNTIME function the orchestrator calls) then found **42 findings (10 CRIT)** the hypothesis reviews missed. So: make agents GENERATE the test space from domain knowledge (if you can list the cases, you've already found them — the value is the cases you DIDN'T think of); after a fix, re-run the COVERAGE sweep, not the hypothesis review (the fix's own over-rejection is the next blind spot). Reusable harness `.qa-correctness/review_coverage.mjs`; [[feedback-coverage-driven-review]] sharpens [[feedback-green-gate-not-correctness]] ([[feedback-verify-llm-reviewer-findings]]).

### Audit conventions (2026-05-22)
- **`_fire_and_forget(coro, label)`** in `structured_comparison_service.py` — use for new fire-and-forget tasks; adds done-callback that logs WARNING on exception. Plain `asyncio.create_task()` swallows exceptions and drops audit/personalization writes.
- **`INSUFFICIENT_DATA` error code** — `compare_from_text` + streaming return early when both products' Phase 1 specs+price are `None`. Prevents fake product_0 winner from all-MISSING_SCORE tie-break. Frontend i18n-substitutes the user-facing message.
- **`WINNER_INDEX_MISMATCH` WARNING log** in `response_builder.py` — fires when GPT-emitted `comparison["winner_index"]` disagrees with deterministic scoring. Deterministic wins; log audits frequency only.

### EAS Update infrastructure
See skill: `qaren-eas-deploy` (auto-loads when `eas update`, `eas build`, channel names, `runtimeVersion.policy`, or `expo.version` bumps are mentioned). Quick recall: OTA via `cd SmartCompareApp && eas update --branch <channel> --message "..."` — free, lands on next app open. Rebuild required for native module / app.json plugin changes. `appVersionSource: "remote"`. Interactive Expo commands (`eas login`, `eas build`) need a real terminal — Ahmed runs these directly.

**Expo Updates two-launch propagation** — first relaunch downloads the new bundle in background while running the cached one; SECOND relaunch actually runs the new bundle. When the user says "fix didn't work" on a freshly-OTA'd bundle, ALWAYS suspect propagation first: force-close → wait 30s → reopen → see Home → force-close → reopen. ALSO: when `eas update` output shows `<sha>*` (trailing asterisk), the worktree had uncommitted changes past the message-claimed commit — `git log` before claiming OTA fired the named SHA. Bundle E S2 hit this ~4 times across rounds; root cause is always one of two-launch-propagation, asterisk-SHA-drift, OR cache.

### Conditional step skip in multi-step flows
Use a `stepSequence` array + `indexOf+1` traversal pattern rather than `step++` arithmetic when some steps are conditionally skipped. Preserves canonical step numbers for testIDs/analytics while letting iteration hop. Example: Step 16 skip when `isAuthenticated` in OnboardingFlow.tsx — `FULL_STEP_SEQUENCE=[1..17]` vs `AUTHED_STEP_SEQUENCE=[1..15,17]`; `handleNext = setStep(seq[seq.indexOf(step)+1])`. Pin both branches in tests.

### "Needs organization" device feedback
When the user says a screen "needs organization" without specifics, swap-the-render-order is usually the first fix to try (Bundle E Step 17 push card moved BELOW headline+subtitle vs above — single JSX-tree reorder, zero style churn, resolved the complaint). Spacing reductions on shared paddings/gaps are the second lever for "doesn't fit on screen" reports.

### Sync-render pattern for `useFocusEffect`-gated screens (2026-05-30)
Screens that fetch on focus crash `act()`-wrapped Jest renders with "Can't access .root on unmounted test renderer." Fix: mock `useFocusEffect` as pass-through `React.useEffect` + use plain `render()` + `waitFor()` (no `act()` wrapping). Pattern lives in `SmartCompareApp/__tests__/{Edit,}ProfileScreen.bundleE.s3.integration.test.tsx`. Brought HomeScreen 35→82%, Profile 0→82%, EditProfile 0→97% coverage. Also: `UNSAFE_getAllByType` requires `Component` refs not strings (`UNSAFE_getAllByType(TextInput)` not `UNSAFE_getAllByType('TextInput')`); Jest accepts strings at runtime but `tsc` rejects with TS2345.

### Product image pipeline (2026-05-30, live in prod)
Backend `app/services/image_service.py` mirrors price-pipeline tier cascade for `products[i].image_url`: Tier 1.5 piggyback page-scrape `og:image` (FREE) → Tier 1 Serper Images (`search_images`, paid, gated by `serper_image_calls_today` 500/day in `api_budget_service`) → Tier 2 Firecrawl rendered → Tier 2.5 Scrape.do residential → Tier 3 GPT-4o-mini from organic → `None` (frontend renders placeholder). Surfaces: `response.products[i].image_url`, `response.overview.products[i].image_url`, SSE `specs` event payload, `/home/smart-pick` `winner_image_url`+`runner_up_image_url`. Frontend rendering via `SmartCompareApp/src/components/primitives/ProductImage.tsx` (4-state fallback: url/null/undefined/onError → placeholder).

### Luxury brand detection
`_is_luxury_brand()` + `COUNTERFEIT_KEYWORDS` filter across ALL categories. Tier 1.5 cascade: official brand → authorized retailers → GCC retailers (9 domains).

### Review + spec quality
Reviews: `_clean_review_content()` strips garbage (min 8 words), fixes sentiment misclassification, then `_clean_review_citations()` replaces `[snippet_N]` with domain attributions. Specs: GPT omits irrelevant fields (not "N/A"). Frontend filters nulls. Scoring applies `CATEGORY_MIN_COVERAGE` penalty.

### Cache-bust on mutating endpoints (2026-06-03)
DELETE/PUT endpoints that invalidate per-user view-caches MUST bust dependent keys AFTER mutation succeeds. Pattern: `history_routes.py:remove_comparison` busts `home:smart_pick:{user_id}` + `profile_recent:{user_id}` via `delete_cached`. Test invariants required: `*_busts_*` + `*_failure_does_not_bust` + `*_forbidden_does_not_bust`. Frontend `useEffect([])` consumers still need `useFocusEffect` swap for per-focus refresh — Redis bust only fixes cold-restart/TTL paths (SmartPickCard same-session staleness remains as Bundle F item).

### Worktree paths
`git worktree add ../foo` resolves relative to shell CWD, not repo root. Wave 1 ended up as siblings (`../smartcompare-foo`), Wave 2 nested under main repo (`smartcompare/smartcompare-foo`). Use ABSOLUTE paths in `git worktree add` + verify via `git worktree list` before agent dispatch.

### Sentry MCP search-issues syntax (2026-06-03)
`lastSeen:-2h` / `lastSeen:+2h` / `age:-2h` all reject with "Invalid date: >=..." (server prepends comparison op). Use bare `is:unresolved` (default 14d window) or ISO 8601 dates. Same syntax bug across multiple param forms.

### claude.ai/design design-system sync (`/design-sync`)
"Qaren Design System" project `c57eb43f-cabf-47bc-b980-ff4956512b26` holds **hand-authored WEB JSX references** (`ui_kits/mobile/*.jsx` → `window.Qaren<Screen>`, previewed by `*.html` via babel-standalone + the existing `ios-frame.jsx`) that MIRROR the RN screens — it is **NOT a converter target** (RN can't render in a browser). Re-sync = diff the RN screen vs its `.jsx` reference and hand-integrate; do NOT run the converter on `SmartCompareApp/`. Local anchor: `design-sync.config.json` + `.design-sync/NOTES.md` (page→source map). Validate edited refs with `@babel/parser` `{sourceType:'script',plugins:['jsx']}` run from `SmartCompareApp/` (esbuild not installed). **Results page is category-driven** (ONE shell, 9 categories): per-category structure source = `scoring_service.CATEGORY_DIMENSIONS`+weights (hero bars = top-4 by weight) / `extraction_service.CATEGORY_SPEC_SCHEMAS`+`build_category_profile` (**"At a glance" + Specs render populated fields in SCHEMA ORDER**) / `price_service.CATEGORY_FAIRNESS` (fashion/other = None → no like-for-like basis caption). Full handoff: `memory/project_design_sync_qaren.md`.

## Environment Variables (Railway)
**Required:** `OPENAI_API_KEY`, `SERPER_API_KEY`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_KEY`, `UPSTASH_REDIS_URL`, `UPSTASH_REDIS_TOKEN`, `ADMIN_API_KEY`
**Optional:** `SENTRY_DSN` (backend + mobile share org `qaren-rr`, different DSNs), `LOG_LEVEL` (INFO), `CORS_ORIGINS`, `STREAM_HARD_CAP_SECONDS` (30.0 since 2026-06-09 B0-C Item 3 — was 25.0; on the NON-streaming `compare_from_text` it is the outermost `asyncio.wait_for` per L2.7, but on the STREAMING path it wraps ONLY Phase 1 (the two `_fetch_product_data` calls) — the post-Phase-1 verdict/critique/moderation tail runs UNBOUNDED past it (M13-04). `ENABLE_FULL_STREAM_DEADLINE` (default OFF) extends the cap over that tail via a residual-budget `wait_for`, yielding the best-available PARTIAL on expiry; flag OFF = today's unbounded tail), `SCRAPING_MODE` (`hard`/`soft` — `soft` skips Firecrawl+Scrape.do for non-luxury URLs), `DEBUG_STAGE_TIMINGS` (true since Sprint A — opt-in `metadata.stage_timings_ms`)
**Price Scraping:** `FIRECRAWL_API_KEY`, `SCRAPEDO_API_TOKEN` (DEAD 2026-06-26 — prod==local==401, rotate), `ENABLE_FIRECRAWL` (true), `ENABLE_SCRAPEDO` (true), `ENABLE_PAGE_SCRAPE` (curl_cffi), `ZYTE_API_KEY` (Zyte API render — cracks Akamai+BH-geo for luxury; used ONLY by the off-clock seed, NOT the live path).
**Serper spend controls (#60):** `SERPER_LIFETIME_LIMIT` — **UNSET by default, and unset means the spend gate is INERT** (live Serper calls are metered but never blocked). The packaged `2200` in `PROVIDER_CONFIGS` is a **FREE-tier** number (2,500 one-time credits minus a 300 buffer) and prod runs a **PAID** key, so arming a gate at it would take all six Serper entry points — price, specs, reviews, images, the 4-way discovery fan-out — plus the price-cache warmer dark the moment the lifetime counter crossed it. That is the failure mode `scripts/cron_warm_price_cache.py:118-131` refuses to reproduce. **To actually bound spend, set `SERPER_LIFETIME_LIMIT` to the live key's REAL ceiling** — the gate then arms there, `get_remaining`/the 80%-burn alert/the `budget warning` threshold all scale with it, and a budget-out degrades to the same benign empty shape a missing key produces (Bright Data where enabled → Tier 1.5/2/3 → a pend or estimate, never a relaxed price). `SERPER_LIFETIME_LIMIT=0` is the explicit off switch. Every process logs one INFO line on its first gate check (`[BUDGET] serper spend gate ENGAGED/INERT …`) so the effective ceiling is never implicit. Other knobs: `SERPER_GATE_CACHE_TTL` (60s — how long a gate decision is memoised; the check is a BLOCKING Upstash round trip, so this keeps it off the asyncio event loop, `<=0` disables the memo), `SERPER_ROTATION_DEADLINE` (14.0s — wall-clock bound on the multi-key rotation loop, unconditional since #60, must stay strictly under the 15s `_PRICE_RACE_TIMEOUT`; `<=0` **disables the deadline**, it never means "make zero calls"), `SERPER_SHOPPING_PRIMARY_COUNTRIES` (empty — the GCC `gl=<country>` shopping primary is a known-empty leg and is no longer purchased; set e.g. `bh,ae` to buy it again if a real feed appears).
**Version Check:** `APP_MIN_VERSION`, `APP_LATEST_VERSION`, `APP_FORCE_UPDATE`.
**Feature Flags:** `ENABLE_COHORT_PERSONALIZATION` (ON since 2026-05-05), `ENABLE_REFERRAL_SYSTEM`, `ENABLE_HYBRID_MODEL_ROUTING` (**phantom** — env value cosmetic, zero code refs; see `docs/BUNDLE_C_PROD_STATE.md`), `ENABLE_REENGAGEMENT_PUSHES` (gates `evaluate_user` + cron, fail-CLOSED), `REENGAGEMENT_CANARY_PERCENT` (100; djb2 via `feature_bucket.hash_bucket`), `ENABLE_BH_GCC_CATALOG_SOURCES` (**ON in prod since 2026-06-26** — loads the 274 liveness-gated BH/GCC catalog rows from `data/bh_gcc_sources.json`; default OFF→registry==literals), `ENABLE_ZYTE_RENDER` (default OFF — the slow Zyte luxury-render fires ONLY off-clock via `scripts/seed_zyte_luxury.py`, NEVER on the 15s live path; live serves cache-first), `ENABLE_PRICE_CACHE_WARMER` (OFF — the off-clock `cron_warm_price_cache.py` warmer = the genuine-share lever, needs paid Serper; knobs `WARMER_SUBSET`/`MAX_QUERIES_PER_RUN`/`PRICE_RACE_TIMEOUT`), `ENABLE_SITEMAP_INDEX` (OFF — bolo/boutiqaat off-clock sitemap-index cron; inert until set), `ENABLE_SELF_CRITIQUE` (OFF — verdict self-critique pass), `ENABLE_REVIEW_SOURCE_CONSULT` (OFF — passive|active review-source consult). All flags default OFF in code; flip in Railway during canary. `REAL_ACTION_MIN_SECONDS` (5). `ENABLE_EXACT_PRICE_GATE` (default ON, IN PROD — the exact-SKU correctness gate; flag-OFF byte-identical; the brand-implied match is gated by it). **2026-07-06/07 price-discovery arc (PRs #26-30):** `ENABLE_EARLY_SPECS_STASH` (default ON — hard-cap PARTIAL salvage), `ENABLE_FAIRNESS_IGNORE_ESTIMATE` (default ON — fairness skips an estimate side so a genuine price isn't pended), `ENABLE_BRIGHTDATA_FALLBACK`+`BRIGHTDATA_API_KEY`+`BRIGHTDATA_ZONE` (default OFF/unset — dormant Bright Data SERP fallback for Serper depletion; zone `serp_api1`; validate the mapper from the first-call `[brightdata] parsed OK …` log). Warmer is the genuine-price VISIBILITY lever (cold compares mask the fixes via the degraded 15s race — activate `ENABLE_PRICE_CACHE_WARMER` + the `/railway.warmer.json` config-file).

**Wave M0/M5/M6/M7 flags (fragrance capture, branch `feature/m7-specs`, 2026-08-30).** Every one is read PER CALL via `os.getenv` (the `price_service.exact_gate_enabled` idiom — never cached at import, so Railway flips them without a restart) and flag-OFF is byte-identical to the pre-wave commit. Default OFF unless marked.
- *M0 (repairs):* `ENABLE_FIRECRAWL_RAW_HTML` (**default ON** — requests Firecrawl `rawHtml` + reads upstream status instead of Firecrawl-CLEANED html; default-ON because it repairs a measured 0/9 path, nothing to preserve; precondition: `FIRECRAWL_API_KEY` only). `ENABLE_SPECS_NO_FABRICATION` (OFF — stops the specs prompt inventing uncited fields AND, since D1, stops all three smart-fallback/Tier-2/Tier-3 refill tiers re-filling what the guard omitted; **precondition: a WORKING SEARCH LAYER (Serper is 403 today) *and* D1's cascade closure `a6901b7`** — flip LAST, since with search dead it trades invented specs for empty ones).
- *M5 (new price/review capture — all ship dark, all fire only where today's path returns nothing):* `ENABLE_RSC_FLIGHT_PRICE` (Next.js RSC-flight payload price rung, `293a46a`); `ENABLE_EXTRACTOR_FIXES_2608` (three zero-fetch residual fixes — doubled-quote JSON-LD block, lowercase keys, alias lookup; no network, safest first flip, `3781d2f`); `ENABLE_MAGENTO_GQL_ADAPTER` (Magento `url_key` GraphQL + jomashop Apollo persisted-query price on Cloudflare-walled HTML PDPs, `e14e3aa`+`efb3972`); `ENABLE_SALLA_SLUG_RESOLVE` (cross-country dead-slug recovery via the Salla search API, `30195e6`); `ENABLE_YOTPO_REVIEWS` (Yotpo public review+ratings enrichment, ~35 scorecard pages, `0d7fcad`). Preconditions: none beyond a canary compare on a matching host.
- *M6 (discovery/selection):* `ENABLE_NORMALIZE_WORDS_EMPTY_FIX` (drops phantom empty tokens GLOBALLY in `normalize_words` — **global matcher impact, canary it ALONE**; the measured sitemap hits recover without it via Part B, `3c5fb49`); `ENABLE_SITEMAP_MATCH_V2` (relaxed word-overlap sitemap matcher, local empty-token drop, fail-closed "return None never a wrong URL" preserved; precondition: `ENABLE_SITEMAP_INDEX` — the channel is inert otherwise); `ENABLE_SITEMAP_PDP_MARKERS_V2` (generalized `_is_pdp_url` in the OFF-CLOCK builder only; precondition: `ENABLE_SITEMAP_INDEX` **and a re-run of `build_sitemap_index`** — an existing index does not gain PDPs retroactively, `f411d07`); `ENABLE_FRAGRANCE_GLASS_EXEMPTION` (lifts the ACCESSORY "glass" over-rejection for the fragrance category — repairs a measured-0% variant but changes a shipping selection outcome, so dark, `c516057`); `ENABLE_JUDGEME_HTML_REVIEWS` (judge.me server-HTML reviews, ~39 pages / 27-of-34 Gulf, `ddead8d`).
- *M7 (seed-then-flip — both stores ship EMPTY on purpose, so the flag alone is INERT):* `ENABLE_SPEC_SPINE` (consults the local fragrance spec spine before the LLM specs prompt and passes `skip_fields`; precondition: `data/spec_spine.json` seeded by `scripts/seed_spec_spine.py` off-clock, plus migration `035_spec_spine.sql` if DB-backed — **unapplied**, `3f4fd12`); `ENABLE_SEARCH_DESCRIPTOR` (per-host search-URL template for discovery; precondition **SEEDED 2026-08-31**: `data/search_descriptors.json` populated with 95 resolved fragrance hosts (47 usable `{q}` templates; robots-allowed rows only) via `scripts/resolve_search_descriptors.py` and folded onto the registry — runbook step (6) is now a pure flag-flip for this flag, `dc64c69`).
- *M9 (selection + channel hardening, merged main `1377c25`):* `ENABLE_NOT_A_PDP_FILTER` (classifies homepage/search-redirects, offsite redirects, CollectionPage-without-Product and title-anchored error shells as NOT-A-PDP at selection time — never priced, never counted as render candidates; fail-open on anything ambiguous, `fbfe245`). The Magento-GQL E3 hardening (content-type gate, numeric-id `url_key` rejection, 400=schema-miss, store-view currency reconciliation) rides the existing `ENABLE_MAGENTO_GQL_ADAPTER` (`1377c25`).
- *M10 (currency-truth + capture-honesty + UCP channel):* `ENABLE_VISIBLE_TEXT_CURRENCY` (the adjacency-anchored visible-text currency rung in `_page_currency_evidence` — an ISO code counts only when price-adjacent, denylist {TOP, ALL, TRY} needs microdata corroboration, abstains on multiple codes; fixes the faces.ae bare-brand 9.8x ask-currency stamp: corpus-proven EXACTLY one row changes OFF→ON, `9edf356`. **Currency-LABEL change — flip ALONE.**); `ENABLE_WALL_SIGNATURE_ANCHOR` (anchors the ambiguous wall phrases in `classify_capture` to title/heading/interstitial context — kills the om.swissarabian access-denied-in-JS-comment false positive with zero false negatives over the true-wall cohort, `a350bee`); `ENABLE_UCP_JSON_PRICE` (the free Shopify `/products/{handle}.json` price channel on UCP hosts — trusts the endpoint's own per-variant `price_currency` over the registry (32/32 measured correct), MAJOR-unit decimals so no minor-unit division, `bb909ea`). A3's multiplicity-discriminator POLICY is pinned prose-only (`2ca58f4`) — query-size wins → request context → pend; never smallest-wins; no behaviour change shipped.

**Wave M13-W1 flags (front-door hardening — auth / rate-limit / paid-work gating, branch `feature/m14-wave1-closeout` from `674034e`, 2026-08-31).** M13 review Wave 1 landed findings `M13-01, M13-02, M13-03, M13-21, M13-25, M13-26, M13-28, M13-29`. Six are unflagged pure corrections (M13-21 openapi_url 404 in prod; M13-25 POST+GET body/query max_length; M13-26 image error-envelope; M13-28 referral limiter + Path/Query patterns, rides existing `ENABLE_REFERRAL_SYSTEM`; M13-29 UUID-validate `comparison_id` on BOTH /feedback and /events; M13-03 admin-dep on GET /text/price-kpi). Three NEW flags, all default OFF, all read PER CALL via `os.getenv` so flag-OFF is byte-identical to `674034e`:
- `ENABLE_DEFAULT_RATE_LIMITS` (default OFF) — gates the registration of `SlowAPIMiddleware` and thus the blanket `default_limits` (ANON_LIMIT=10/min) on the 21 previously-undecorated routes. **Effect ON:** every undecorated route gets a 10/min default. **Why dark:** under the shipped proxy-IP key the default is keyed on the shared Railway edge-proxy IP = ONE deployment-wide bucket per URL path, which 429s the hot app-open reads (`/app/version`, `/usage/status`, `/auth/me`, `/auth/verify`) and infra (`/health`, `/`, `/favicon.ico`) for every user. **PRECONDITION: flip ONLY together with a verified `ENABLE_PROXY_AWARE_RATELIMIT`** so the key is per-client, never the shared proxy IP. The credential-route brute-force protection (explicit `@limiter.limit("5/min")` + account-lockout on PUT /auth/{email,password}) is decorator-driven and is LIVE regardless of this flag.
- `ENABLE_PROXY_AWARE_RATELIMIT` (default OFF) — swaps the limiter `key_func` (and the shared `audit_client_ip` used at the 5 auth audit sites) from `get_remote_address` (the Railway edge-proxy TCP peer) to an X-Forwarded-For-derived client IP. **Effect ON:** distinct clients get distinct limiter keys / audit IPs. **HARD PRECONDITION before activation:** the current reader takes the *leftmost* XFF entry, which on Railway is attacker-controlled (the trusted edge appends the real peer to the RIGHT of any client-supplied XFF), so ON-as-written lets an attacker forge limiter keys and `admin_audit_log.ip_address`. The correct anchor depends on Railway's real proxy topology (hop count) and CANNOT be verified without live egress — prefer running uvicorn with `--proxy-headers --forwarded-allow-ips=<trusted edge>` (or read the hop the trusted edge appended, i.e. rightmost-after-trusted). Do NOT flip until this is verified against Railway's edge.
- `ENABLE_ANON_USAGE_GATE` (default OFF) — extends the freemium daily+monthly gate to ANONYMOUS callers on `/text/quick` and `/image/identify`, keyed on the regex-validated `X-Device-Fingerprint` header (`anon:{fp}` Redis counters, fail-open). **Effect ON:** an anonymous device over its free daily/monthly cap gets 429 `USAGE_LIMIT`. **Note:** an absent/garbage fingerprint no-ops the gate (metered clients only); the `@limiter.limit("10/minute")` decorator remains the backstop.

**Wave M13-W2 flags (currency truth — stop shipping a wrong number labelled genuine, branch `feature/m15-wave2-closeout` from `5ee72e8`, 2026-09-01).** M13 review Wave 2 landed findings `M13-07, M13-08, M13-09, M13-10, M13-11, M13-12, M13-38, M13-39, M13-40, M13-44`. **Flag-OFF byte-identity gate PROVEN:** `scripts/verify_flag_byte_identity.py` over `_proof` (414 pages / 1,656 calls) prints the SAME `OVERALL SHA256 cfd13914b43c12a623f0165a0367703b6cd52f6de75c557a3a725cf5db813de7` at `5ee72e8` and at the closeout HEAD with all five wave flags forced OFF. Every new flag is read PER CALL via `os.getenv` (never at import) and default OFF. Four NEW flags:
- `ENABLE_SHOPPING_STRICT_CURRENCY` (default OFF, M13-09) — the strict-label pend on the Serper-shopping tier (`extract_price_from_shopping`), the one price tier the BLOCKER-4 currency wave never covered. **Effect ON:** a candidate whose visible price carries a NON-target currency `detect_currency` cannot resolve PENDS instead of stamping the raw foreign amount with the target currency (the `1,399 د.إ` → 1399 BHD 9.8x-over-genuine bug), plus the `'$' in 'R$'` collision (BRL read as USD) pends. **Dispatcher over-rejection fix applied this closeout (`_GCC_SYMBOL_RESIDUE`):** a TARGET-currency price in its own Arabic glyph (`250 ر.س` on a SAR ask, `1,399 د.إ` on an AED ask) is GENUINE and must ship, not pend — the residue is resolved against a separator-stripped GCC glyph mirror BEFORE the non-ASCII catch-all, so target glyphs ship (flag ON == flag OFF) while foreign glyphs still pend. **Precondition:** flip WITH/AFTER `ENABLE_EXTENDED_FALLBACK_RATES` — the ASCII-ISO foreign residue (`TRY`/`PLN`/`CAD`/`JOD`…) only resolves to a pend once the extended table is on; with M13-09 ON and M13-38 OFF a `TRY 5050` shopping row still ships mislabelled.
- `ENABLE_REGION_CURRENCY_GUARD` (default OFF, M13-11) — the pend for a price whose currency ≠ the request region's currency (region currency via `exchange_rate_service.get_region_currency`). Applied at **TWO** places since M18 CD-interactions-02: a PRE-SCORING in-place pass `price_service.apply_region_currency_guard(product_data, region)` invoked by BOTH orchestrator paths (`structured_comparison_service`, immediately after `reconcile_pair_fairness` — sync before `compute_scores`, streaming before the `specs`/`prices` yields and `compute_scores`), plus the original `response_builder` price-pending chokepoint, kept as the idempotent backstop for direct `build_comparison_response` callers (share / history rebuilds, tests). **Effect ON:** a BHD price served to a `saudi_arabia` request pends (`amount None`, `unavailable True`, `guard_rejected=region_currency_mismatch` in metadata) — and, because the pend now lands BEFORE scoring, `winner_index` / `dimension_winners` / the LLM verdict take the honest missing-data path instead of being decided by the mismatched amount, and the SSE `prices` event carries the pending shape instead of flashing a foreign-currency amount the final `complete` then retracts. A same-region price, an already-pending price (`size_mismatch` / `unit_mismatch`) and a price with no currency label all pass untouched. The pre-scoring pass stashes its reason on the PRODUCT dict as `_region_guard_rejected` (never on the price — `public_price_view` only strips `_`-keys when `ENABLE_EXACT_PRICE_GATE` is ON) and `response_builder` harvests it before its `unavailable` early-continue, so `metadata.guard_rejected` survives the upstream pend. **The highest-blast-radius change in the wave — canary it LAST, alone.** **Precondition:** flip WITH/AFTER `ENABLE_LONGEST_HOST_MATCH` — with the host-match OFF, `ksa`/`om.swissarabian.com` mislabel their own SAR/OMR as USD, so the guard would wrongly pend those correct storefront prices in a Saudi/Oman region.
- `ENABLE_LONGEST_HOST_MATCH` (default OFF, M13-12) — one shared `_registry_row_for_host(host, where=, registry=)` longest-domain-wins resolver replacing every per-call `SOURCE_REGISTRY` suffix scan (`source_router.match_registry_apex`/`registry_tier`, `shopify_pdp_service`, `search_descriptor_service`). **Effect ON:** a currency/descriptor lookup resolves to the row with the LONGEST matching domain (exact match outright), fixing the 2-of-319 registry currency self-mismatches (`ksa.swissarabian.com` SAR, `om.swissarabian.com` OMR — both stamped USD OFF) and the 2-of-95 descriptor rows. Flag OFF = first-suffix-match, byte-identical.
- `ENABLE_EXTENDED_FALLBACK_RATES` (default OFF, M13-38) — widens `FALLBACK_RATES` with 10 corpus currencies (`TRY/PLN/CAD/JOD/SEK/DKK/CHF/EGP/NOK/AUD`) behind `effective_fallback_rates()`; `_convert_to_bhd` + `_normalize_currency_code` read the effective table. **Effect ON:** a `TRY 5050` price converts (≈47.47 BHD) instead of pending the dead rung. **Why dark:** the `_proof` corpus carries TRY/PLN/CAD/JOD pages that pend today, so widening the base dict unflagged would break flag-OFF byte-identity. Rates are approximate 2026 figures (the exact number is not load-bearing). Did NOT flip `ENABLE_RSC_FLIGHT_PRICE`.

`ENABLE_JSONLD_FIRST` (Wave-1, **default ON**) is REUSED — per the Wave-2 spec — for three currency changes, so **M13-07/M13-08/M13-40 are NOT dark: they ship LIVE the moment this deploys** (the byte-identity gate forces the flag OFF and does NOT exercise their production path). Independently corpus-verified at the prod default (JSONLD_FIRST ON, the four new flags OFF, base-vs-HEAD over the 414-page corpus): 0 LOST captures, ~94 NEW foreign-currency JSON-LD captures, provenance-only relabels at the same amount, and only 3 amount changes — all M13-40 preferring the authoritative JSON-LD Offer over a deviant OG fallback (e.g. `alhajisoman` OG 3.0 OMR anomaly → JSON-LD 30.0 OMR = 2.93→29.31 BHD, a 10x correction; `numberc` OG 22 KWD WAS-price → JSON-LD 12.10 KWD). Zero corpus regressions, but **watch the WooCommerce/foreign-offer capture on the first deploy, not at a later flag flip.** M13-07 = WooCommerce `converted_usd` relabel; M13-08 = parse the WooCommerce amount under the resolved `_wc_label` (de-DE `1.234` EUR → 505.94 BHD, NOT 0.51); M13-40 = a third `extract_price_from_html` pass accepting a foreign-currency JSON-LD Offer (45.00 EUR → 18.45 BHD `converted_usd`).

**Deliberately UNFLAGGED** (pure defect fixes, no behavioural fork, flag-OFF-equivalent for legitimate traffic): M13-10 (the tier1_shopping re-selection stash now parses `parse_price_string(price_str, detect_currency(price_str), display_text=True)` like the main path — `BHD 12,500` → 12.5 on both, not 12500.0); M13-44 (coerce a null `original_currency` to `''` at the three `.upper()` sites + `sanitize_gpt_price` — no `AttributeError`, degrade to Tier 3); **M13-39** (`_fallback_rate`/`get_rate` return `None` for an unknown currency instead of a silent rate of `1.0`; `get_rate` is now `Optional[float]`). **M13-39 decision (justified):** did NOT delete the `get_rate`/`_fetch_rates`/`_lookup_rate`/`_fallback_rate` cluster — two live test files import it (deletion = NEW import failures) and it has ZERO production callers (`_convert_to_bhd` uses `effective_fallback_rates()` directly, never `get_rate`), so the `1.0`→`None` change is confined to a dead function pair and cannot reach the extract path (confirmed by the identical flag-OFF gate SHA); 4 stale tests updated to the `None` contract.

**ACTIVATION coupling (Wave-2):** the four currency flags are canaried TOGETHER as a family, but with two hard orderings — (a) `ENABLE_EXTENDED_FALLBACK_RATES` with/before `ENABLE_SHOPPING_STRICT_CURRENCY` (else TRY/PLN/CAD ASCII-ISO shopping rows still ship mislabelled), (b) `ENABLE_LONGEST_HOST_MATCH` with/before `ENABLE_REGION_CURRENCY_GUARD` (else the guard pends correct swissarabian SAR/OMR prices), (c) **the M18 CD-interactions-02 pre-scoring pass must be MERGED before the region-guard flip** — before it, the guard pended only the FINAL projection, so a final-payload-only canary reads CLEAN (the payload shows `price: pending`) while the winner, the dimension winners and the LLM verdict are still decided by the mismatched amount and the SSE `prices` event still flashes it mid-stream. A canary for this flag must therefore inspect the `scores` event / `winner_index` and the mid-stream `prices` event, not just the `complete` payload — and **`ENABLE_REGION_CURRENCY_GUARD` goes LAST, in its own window** (highest blast radius: in any non-Bahrain region it pends every non-region-currency price). Remember M13-07/08/40 are already live on deploy via default-ON `ENABLE_JSONLD_FIRST`; the only kill-switch for them is disabling the whole Wave-1 JSON-LD reorder.

**ACTIVATION-ORDER runbook (when validation begins — one canary compare per step, never batch across steps):** (1) `ENABLE_EXTRACTOR_FIXES_2608` + the three M5 price adapters (`ENABLE_RSC_FLIGHT_PRICE`, `ENABLE_MAGENTO_GQL_ADAPTER`, `ENABLE_SALLA_SLUG_RESOLVE`) together — all additive rungs on no-price residuals. (2) `ENABLE_YOTPO_REVIEWS` + `ENABLE_JUDGEME_HTML_REVIEWS` — enrichment only; watch latency, not correctness. (3) The sitemap trio together with `ENABLE_SITEMAP_INDEX`: flip `ENABLE_SITEMAP_PDP_MARKERS_V2` → **rebuild the index** → then `ENABLE_SITEMAP_MATCH_V2`; never `MATCH_V2` against a stale index. (4) `ENABLE_FRAGRANCE_GLASS_EXEMPTION` alone (fragrance selection outcome changes). (5) `ENABLE_NORMALIZE_WORDS_EMPTY_FIX` **alone in its own window** — global matcher blast radius; nothing else may move with it. (6) Seed first, then flip `ENABLE_SPEC_SPINE` and `ENABLE_SEARCH_DESCRIPTOR`. (7) `ENABLE_SPECS_NO_FABRICATION` **LAST**, only after search restoration + D1. **M9/M10 insertions:** `ENABLE_NOT_A_PDP_FILTER` + `ENABLE_WALL_SIGNATURE_ANCHOR` + `ENABLE_UCP_JSON_PRICE` join step (1)'s additive-capture family; `ENABLE_VISIBLE_TEXT_CURRENCY` gets its OWN window between steps (4) and (5) — it is a currency-LABEL change and must never move with another flag.

**M20 winner-truth completion (issues `#99` + `#110`, on top of the concurrent PRs #122/#124, 2026-09-01).** PR #122 shipped `#99` PARTIALLY and that half-fix was LIVE: `_names_the_loser()` gated the loser-prose drop on case-insensitive containment of the loser's **FULL name**, and only that. **MEASURED against the shipped `build_comparison_response` on a mismatch row: 4 of 5 realistic phrasings shipped the loser's praise verbatim** into `overview.winner.reason` -> the top-level `recommendation`, Home `verdict_short`, History and the **Share text** (pronoun "It offers a noticeably richer flavour"; short name "Budget Pickle wins on everyday value." — which still NAMES the loser beside the winner's name; brand fragment; subject-free praise). It is STRUCTURAL, not unlucky: `extraction_service` caps `winner_reason` at 20 words (`:953`, `:983`) while a full product name runs 5-6, so the prompt pushes the model AWAY from the one string the check looked for — and because the declaration is also dropped, a dangling "It" re-points at the SHIPPED winner, silently converting praise-of-the-loser into fabricated praise-of-the-winner. **Fix: drop `winner_reason` AND `key_tradeoff` UNCONDITIONALLY whenever the deterministic winner overrode GPT's** — on a mismatch that prose exists to justify the product we did NOT pick, so containment was the wrong question entirely; `_names_the_loser` is deleted. Re-measured after the fix: **0 leaking fields across all 5 phrasings**, and the AGREEMENT path keeps GPT's prose byte-identical (pinned both ways, plus a parametrized 5-phrasing pin so this cannot regress to a containment check). Also landed: a non-int `winner_index` normalization (`comparison` is raw model JSON — `ComparisonResult` is never applied to it, so a JSON `null` or quoted `'0'` read as a genuine disagreement and destroyed prose that already named the right product).
- `ENABLE_WINNER_PROSE_RECONCILE` (default OFF, `#110`) — the UNFLAGGED safety layer above makes name/index truthful everywhere the payload exposes a winner (`overview.winner.name`, the BC `comparison.winner_index`, and the **SSE `verdict` event's `product_index` + name**, which previously flipped mid-stream against `complete`). This flag adds the optional layer on top: it REPLACES the dropped strings with a deterministic template instead of leaving the qualitative fallback. **Effect ON:** user-facing verdict COPY changes on the core surface (and on Home `verdict_short`, a second copy surface) — so it is dark and canaried ALONE. Flag OFF = the safety layer only.

**Wave M13-W3 flags (event-loop & deadline integrity, branch `feature/m16-wave3-closeout` from `e22258e`, 2026-09-01).** M13 review Wave 3 landed findings `M13-04, M13-05, M13-06, M13-30, M13-31, M13-32, M13-33, M13-34, M13-35, M13-37`. **Flag-OFF byte-identity gate PROVEN:** `scripts/verify_flag_byte_identity.py` over `_proof` (414 pages / 1,656 calls) prints the SAME `OVERALL SHA256 298f2ced4dd4bc313ae871b97ba7d64bedfe16d94dea182a9c7b53c358b87630` at `e22258e` and at the closeout HEAD with all four wave flags forced OFF (`ENABLE_SYNC_DB_OFFLOAD`, `ENABLE_SERPER_BREAKER`, `ENABLE_FULL_STREAM_DEADLINE`, `ENABLE_ASYNC_REDIS_OFFLOAD`). The extraction path (`price_service`/`platform_router`/`shopify_pdp_service`/`exchange_rate_service`/`source_router`/`scoring_service`) is byte-identically UNTOUCHED (empty diff), so the corpus SHA cannot move. Every new flag is read PER CALL via `os.getenv` (never at import) and default OFF. Four dark offloads:
- `ENABLE_SYNC_DB_OFFLOAD` (default OFF, M13-05) — `app/utils/db_offload.run_db(call)` moves the REQUEST-PATH HOT SET of blocking Supabase `.execute()` off the loop via `asyncio.to_thread`. **Effect ON:** one user's blocking DB RTT no longer stalls every other coroutine on single-worker uvicorn. **Hot set (9 sites):** `database_service.{get_user_by_id,get_user_comparisons,save_comparison}`, `usage_service.{_get_user_tier_info,_get_active_referral_bonus,record_comparison(increment rpc),record_lifetime_comparison(rpc)}`, `auth_service.verify_token`, `audit_service.log_audit_event`. **Flag OFF:** `run_db` is an `async def` with no `await` on the inline branch → byte-identical to a direct `.execute()`. **Precondition:** none; canary alone. **Deferred (named, NOT wrapped):** off-path/cron/script sync-Supabase sites, `usage_service._maybe_reset_referral_bonus`, `structured_comparison_service._persist_genuine_price` set_cached, and the fire-and-forget-but-still-loop-stalling `database_service.log_search` + `feedback_service.save_comparison_and_track_cohort` (highest-frequency request-path writes — wrap in a later wave).
- `ENABLE_ASYNC_REDIS_OFFLOAD` (**pre-existing, default UNCHANGED OFF**, EXTENDED by M13-06) — now also mirrors 10 request-path `set_cached` WRITES (`_cache_set_async`) and batches the firecrawl+scrapedo render-gate reads (`is_circuit_closed`+`has_budget`) via `_provider_gate_ok_async` (deliberately NOT memoised — a breaker trip must short-circuit the next render candidate). **Flag OFF:** both inline, byte-identical. **⛔ HARD PRECONDITION before any canary of THIS flag:** `is_circuit_closed`'s half-open counter (`api_budget_service.py`, M13-31) is a NON-atomic Redis GET→incr→SET. Flag OFF it is safe (inline-sync, no loop yield, so concurrent render-gate checks serialise). Flag ON wraps it in `asyncio.to_thread`, so concurrent fan-out threads run the RMW in parallel, several read `half_open_calls=0`, and MULTIPLE render probes are admitted in the breaker's half-open window (paid render spend leak). RESOLVE FIRST: make `half_open_calls` an atomic Redis INCR (M13-37 already uses INCRBY for exactly this counter class — mirror it) OR exclude the provider render gate from the offload.
- `ENABLE_SERPER_BREAKER` (default OFF, M13-32) — breaker-gated wrapper over renamed `_serper_post_impl`. **Effect ON:** an OPEN `serper` breaker short-circuits the POST (returns None → benign-empty, same shape as budget-out), records failure on timeout/5xx/403 and success on 200; breaker read memoised on `SERPER_GATE_CACHE_TTL`, invalidated on each record so a trip engages next call. A benign budget-out/no-key None-return records NOTHING (`if response is not None` guard) so it never trips on a wrong signal. **Flag OFF:** `_serper_post` delegates directly, byte-identical. **Precondition:** none.
- `ENABLE_FULL_STREAM_DEADLINE` (default OFF, M13-04) — bounds the post-Phase-1 streaming verdict tail. **Effect ON:** deadline at generator entry; verdict + self-critique + moderation each run under a residual-budget `asyncio.wait_for` (residual floors at 0.05s), yielding the best-available PARTIAL on expiry. **Flag OFF:** each awaits directly (today's unbounded tail — byte-identical). **Precondition:** none, but pairing it ON with the streaming route bounds the M13-35 early-disconnect amplification below.

**M18 CD-interactions-01 flag (SSE pre-verdict disconnect, `app/api/text_routes.py`, 2026-09-01).** The W3 x W3 interaction above (M13-35 drain defeating the M13-37 refund) is fixed in two halves, shipped differently on purpose - shipping both unflagged would leave a canary unable to tell an accounting change from a latency/spend change, and shipping both dark would leave the live credit burn in place behind a flag nobody has flipped.
- *Half A - accounting, deliberately UNFLAGGED* (same category as M13-10/M13-44: a pure defect correction with no result fork for legitimate completed traffic). `event_generator` now latches `complete_after_client_gone` on the FIRST `complete`/`settle_complete` event and the metering branch reads `if complete_response and not had_error and not complete_after_client_gone`. **Effect:** a client that leaves BEFORE the final payload falls through to the existing `else` and refunds via `usage_refund.text_stream.incomplete` - no `log_search` success row, no `save_comparison`, no `record_lifetime_comparison`, net quota effect zero as it was pre-W3. A client that leaves AFTER the verdict/`settle_complete` still meters and persists exactly once (M13-35's case, pinned). `elif had_error` still wins when an `error` event was also seen, so exactly one refund fires, never two. `usage_consumed is False` and anonymous callers refund on no path.
- `ENABLE_PREVERDICT_DISCONNECT_ABORT` (**default OFF**) - *Half B, resource.* **Effect ON:** a PRE-verdict disconnect also stops driving the orchestrator - the bound generator is `aclose()`d and the loop breaks - so the verdict/critique/moderation OpenAI tail is not paid for a comparison nobody will read. The explicit `aclose()` is load-bearing: a bare `break` out of an `async for` does NOT close the generator, CPython finalizes it later and non-deterministically, so the orchestrator's `finally` (and M13-30's `_get_price` prefetch cancellation) would not run at the break. **Flag OFF:** the `break` never fires and nothing is ever closed - the route makes exactly the same calls on the generator as it did at `dd4c849`, so the M13-35 drain is unchanged. Read PER CALL via `os.getenv` (`text_routes.preverdict_disconnect_abort_enabled`). **Canary precondition: none**; pairing with `ENABLE_FULL_STREAM_DEADLINE` is complementary, not required. Deliberately out of scope: no `success=False` "abandoned" `log_search` row on the aborted path (it would move the KPI failure-rate series; pre-wave this path logged nothing) - raise separately if the analytics gap matters.

`ADAPTER_EXECUTOR_MAX_WORKERS` (env knob, NOT a feature flag, default 40, M13-34) sizes the named `qaren-worker` `ThreadPoolExecutor` installed as the loop default at startup (`main.py` on_event). UNFLAGGED, always-on: it replaces CPython's host-dependent default pool (`min(32, cpu+4)`) for every `to_thread`/`run_in_executor(None)` site. Benign — on realistic hosts the ceiling only rises or holds (prod ~32→40, small box ~6→40), so it can only keep/improve capture; the corpus gate is (correctly) insensitive to it.

**Six UNFLAGGED invariant-tightening fixes (land with a pin; no happy-path result fork):** M13-31 (count the half-open probe so exactly ONE is admitted — fires only on the breaker OPEN→HALF_OPEN degraded path; CLOSED/no-state returns before it), M13-33 (`review_service` L2 persist → `fire_and_forget` so an RLS/schema/5xx failure is logged, not swallowed — adds logging only), M13-30 (`_get_price` body wrapped in try/finally so an outer cancel cancels the ~18 prefetch tasks — pure whitespace re-indent, `git diff -w` shows only try/finally/comment, idempotent cleanup), M13-34 (one adapter inner-timeout clamp + sized executor — see the two deviations below), M13-35 (SSE post-verdict metering moved into a `finally` + drain-not-abandon on disconnect so a client dropping after the verdict still meters/persists), M13-37 (atomic freemium consume at the gate closing the quota TOCTOU). **M13-37 closeout fix (dispatcher-applied, `feature/m16-wave3-closeout`):** the failure-path refund now fires BEFORE `_surface_comparison_failure` in POST+GET — that call RAISES for TIMEOUT/INSUFFICIENT_DATA/generic, so a refund after it was unreachable dead code that burned a daily credit on every cold-path timeout — plus a symmetric `else`-refund in the streaming `finally`. **CORRECTED 2026-09-01 (M18 CD-interactions-01):** that `else`-refund covers a mid-stream raise and a cancel (the `finally` runs on CancelledError/GeneratorExit too) but it did NOT cover a real pre-verdict client disconnect, which is what the original note claimed. M13-35's drain-not-abandon means a disconnect at second 2 still runs the generator to completion, so `complete_response` ends up set, the `finally` takes the METERING branch, and the `else` (which requires `complete_response` absent) is unreachable - a network blip burned one of the 3 daily / 10 monthly / 3 lifetime free comparisons for a result the user never received, where pre-wave a dropped connection was free. Fixed unflagged by the `complete_after_client_gone` latch in `text_routes.event_generator` (see the M18 entry under **Feature Flags**); a POST-verdict drop still meters, which is M13-35's deliberate behaviour and is pinned.

**Two UNFLAGGED behavioral deviations M13-34 introduces (byte-identity gate cannot see timing; canary-watch):** (a) adapter inner timeout clamped 10s→9s for woo/salla/occ/magento/rest_json — a source responding in the 9.0–10.0s window now returns None where base returned a price (defensible parked-thread prevention; the 15s race + other tiers backstop; `ENABLE_BH_GCC_CATALOG_SOURCES` ON can fire these on the live path). (b) Bright Data inner SERP timeout clamped 20s→9s — a fallback result arriving in the 9–15s window (previously deliverable inside the 15s `_PRICE_RACE_TIMEOUT`) is now cut at 9s (rarely-firing paid Serper-depletion fallback; untestable without paid spend). Both are canary-watch items, NOT the "no result change" the implementer note claimed.

**M13-35 resource note:** drain-not-abandon runs the full Phase-2 OpenAI tail server-side even when the client disconnects BEFORE the verdict, and that tail is default-UNBOUNDED (`ENABLE_FULL_STREAM_DEADLINE` default OFF). An early connect-then-drop now amplifies into a full server-side compare where it previously self-cancelled. **CORRECTED 2026-09-01 (M18 CD-interactions-01) - this was NOT a pure resource trade-off.** The same drain also silently BURNED A USER CREDIT on every pre-verdict drop (it defeated the M13-37 refund, see the correction at the M13-37 bullet above), so the "if the amplification matters" framing understated it. The accounting half is now fixed UNFLAGGED; the resource half - stopping the drain so the default-unbounded OpenAI tail is not paid for - ships dark behind `ENABLE_PREVERDICT_DISCONNECT_ABORT` (default OFF), so **until that flag is flipped the amplification described here is still live**. `ENABLE_FULL_STREAM_DEADLINE` remains complementary, not required.

Operational rollout sequence + canary monitoring guidance: see `docs/CONTEXT_SESSION_LOG.md`. M11 closeout references: robots-unreadable policy ruling `docs/policies/2026-08-31-robots-unreadable-ruling.md`; Ahmed's unblock pack (OpenAI canary GO, Firecrawl top-up + Redis latch, affiliate signups) `docs/runbooks/2026-08-31-ahmed-unblock-pack.md`.

Railway MCP server is configured at project root (`.mcp.json`, stdio via `railway mcp`). Query env vars / deploys / logs from inside Claude Code via `mcp__railway__*` tools after a first-time `railway login` in a real terminal (interactive auth; cached in `%USERPROFILE%\.railway`).

## Tests

```bash
# Free unit tests (~$0)
python -m pytest tests/ -v -m "not (live_unit or live_db or integration)" --ignore=tests/test_integration.py

# Live unit tests (iHerb, Serper, GPT — ~$0.03)
LIVE=1 python -m pytest tests/ -v -m "not (live_db or integration)"

# Integration tests (live Railway — ~$0.06)
LIVE=1 python -m pytest tests/test_integration.py -v -m integration

# Full suite
LIVE=1 python -m pytest tests/ -v --timeout=180
```

- `python -m py_compile <file>` for syntax checks; `npx tsc --noEmit` for frontend types.
- `conftest.py` auto-loads `.env` via python-dotenv, then STRIPS the
  credential-bearing names from it (issue #48) so the default tier runs
  credential-free, same as CI. **`LIVE=1` is what restores them** — the
  `live_unit` / `live_db` / `integration` markers no longer opt in on their
  own, so `-m live_db` without `LIVE=1` skips every selected test instead of
  running it. PowerShell: `$env:LIVE=1; python -m pytest ...`. See
  `tests/_env_safety.py`.
- ~557 test files (`test_<feature>.py`, roughly one per service; ~15,900 free-tier nodes collected — M13-124 corrected the stale "~100" figure 2026-09-01). 80%+ coverage target for new features.
- No regressions: all existing tests must pass before merging.
- **Eval gate (Bundle B B.6):** pre-merge `python -m scripts.eval_runner --subset smoke20 --mode regression --baseline-run-id 4aee8e88-da97-41b3-974b-3e75c2c9c10e` (S1 baseline = 21.0%). Measurement runs ALWAYS `--concurrency 1` (walls are load-sensitive); full-200 needs `--allow-full` + dispatcher GO (~600-1,000 Serper credits). Runbooks: `docs/runbooks/qaren-eval.md` + `qaren-gold-set.md`.
- **Eval anchor (hoisted 2026-08-30 out of the archived 2026-06-17 faithful-results bullet; this is the ONE intentional duplicate - the source bullet is verbatim in `docs/SESSION_BUNDLES.md`):** **Eval anchor = the FULL UUID `54b603e8-4eab-41c9-a34d-a5e391446559` (smoke20 winner 0.50). Gates MUST pass the full UUID (`--baseline-run-id 54b603e8-4eab-41c9-a34d-a5e391446559`) — the short `54b603e8` 400s `invalid input syntax for type uuid` → a FALSE "GATE FAIL" (NOT a regression). COLD smoke20 shows `pass_rate=0`/`price=0` BY DESIGN (the baseline row itself does too — 30s cap) → judge by the axis AVGS (winner/specs/factual), never pass_rate. `python -m scripts.eval_runner` does NOT auto-load `.env` (only pytest's conftest does) → `set -a; source .env; set +a` (or `load_dotenv(override=True)`) first, else the baseline fetch fails "SUPABASE_URL must be set". free-unit baseline RE-CAPTURED to **14** real nodes (M13-17, 2026-09-01 — `tests/.pre_impl_failures.txt`; the old "48" was a stale, credential-captured snapshot padded with 35 xfail'd value_math nodes, so it reported false regressions on a clean credential-free clone) + the two `NETWORK_FLAKY_EXCLUDE` GET-hangers the gate drops on both sides.**
- **Known RED-by-design:** `tests/test_value_math.py` (**35** TDD stubs for unimplemented Bundle C v1.1 value-math A.6.x fns — recounted 2026-08-25, the old "24" was stale) — not a regression. Contained by a module-level `pytest.mark.xfail(strict=False)` since #49, so they no longer redden the build; `ci.yml` runs with `-rxX` so the day they XPASS the marker gets removed. Gate batches must exclude network-dependent "free" tests (e.g. `test_rate_limiting_complete.py` does a real GET).
- **The dev machine can run a DIFFERENT fastapi/starlette than `requirements.txt` pins** (observed 2026-09-01: local `fastapi 0.115.0` / `starlette 0.38.6` vs lock `fastapi==0.141.1` / `starlette==1.6.0` — the lock is what CI and Railway install), so a framework-introspection test can pass locally and fail only in CI. **Framework introspection must therefore be DUCK-TYPED, never shape-assuming:** on 0.141 an `app.routes` entry can be an `_IncludedRouter` with no `.path` (naive `r.path` raises `AttributeError`; the getattr-defended `getattr(r, "path", "")` silently sees ZERO routes and reports a FALSE "not mounted"). Shared walker + positive control: **`tests/_route_introspection.py`** (M19) — use it, do not re-flatten to `for r in app.routes`. Re-sync a stale local env with `pip install -r requirements.txt -r requirements-dev.txt`.
- **Windows codec trap:** always pass `encoding='utf-8'` to `subprocess.run`/`open`/`read_text` — `text=True` alone decodes cp1252 and manufactures mojibake from clean UTF-8 (bit 3 independent tools on 2026-06-10). Byte-compare BOTH sides before reporting any non-ASCII diff.

### Dependency Scanning (pre-deploy)
```bash
pip-audit -r requirements.txt --strict
cd SmartCompareApp && npm audit --audit-level=high
```

## Pre-launch (App Store / Google Play)

ToS/Privacy fact base, code-side blockers (delete cascade, expo-notifications plugin, Sentry URL scrubbing, ToS clickwrap + 13+ gate, `ai_sharing_enabled` default), stale legal docs, and the 25-item DECISIONS REQUIRED block: see `docs/plans/2026-05-06-tos-fact-base.md` and `docs/plans/2026-05-06-tos-evidence/`. Stale legal markdown at `app/legal/{privacy_policy,terms_of_service}.md` is served live but says "SmartCompare" / `@smartcompare.app` — REPLACE, do not patch.

**Age policy (locked):** 13+ general audience including teens. Apple **12+**, Google Play **Teen**. Do NOT enroll in Apple "Kids" or Google "Designed for Families".

**Canary phasing:** With <10 testers pre-launch, set new-feature canary % to 100 — lower % statistically hash-buckets a small tester set out of the feature being tested. Drop to 10 only at App Store soft-launch, then ramp 10→50→100 per `docs/runbooks/qaren-canary-onboarding.md`.

## Active runtime (full-repo audit — 7 PRs MERGED, CI 176 -> 15 failures, 2026-08-25)

**STATUS 2026-08-25 — merged to main `b83bf7b` and deployed.** Seven PRs landed: #82 (#46 dep lock),
#88 (#48 credential neutralisation), #86 (#49 CI gates), #85 (docs), #84 (#59 subtype specs),
#83 (#58 model config *Step 1 only*), #87 (#60 Serper gate). **`backend-tests` went from 176 failed /
9,359 passed to 15 failed / 9,653 passed**, and `backend-lint` / `dependency-audit` /
`frontend-typecheck` are all green. The remaining 15 are tracked in **#89** with root causes already
diagnosed — read it before touching them. Full handoff:
`docs/investigations/2026-08-25-audit-wave1-handoff.md`.

**NOTHING MERGED IS ACTIVE UNTIL ENV VARS ARE SET — all three ship deliberately inert:**
`SERPER_LIFETIME_LIMIT` arms the Serper budget gate (unset = no-op);
`OPENAI_MODEL_VERDICT` / `OPENAI_MODEL_VISION` flip the models (**smoke-test first** — GPT-5 rejects
`temperature=0`, needs `max_completion_tokens`, and bills invisible reasoning tokens against that
budget, so a naive flip can return empty verdicts); `--cov-fail-under` is **83** in `ci.yml` (since
`d48bc19`; the old "deliberately 60 vs a measured 78" note was stale — M13-79 corrected 2026-09-01),
a real floor — re-ratchet upward after the #89 failures are fixed.

**TWO LIVE BLOCKERS (observed directly 2026-08-25):** Serper returns **403 Unauthorized** on every
`/search`; OpenAI returns **429**. Nothing in the product works properly until both are restored.

**SCRAPER TOOLING — MEASURED bake-off 2026-08-25 (not desk research).** 9 real registry targets, every
contender judged by the repo's OWN `extract_price_from_html`. Scoreboard (priced/9): **curl_cffi 4,
Scrape.do 4, crawl4ai default 4, crawl4ai+patchright 4, Firecrawl 0, Zyte 0 (account suspended).**
Full write-up: `docs/investigations/2026-08-25-scraper-bakeoff.md`.
- **`curl_cffi` READ sephora.me** — 200, zero `_abck`, JSON-LD **77.000 BHD**, 1.39s, free: the exact
  price Zyte was procured for, while plain Playwright AND crawl4ai AND crawl4ai+patchright all got 403.
  **ONE sample — not actionable.** #93 specifies 20+ samples over 24h from Railway egress before
  retiring the Zyte tier. Do not rewire sephora on the strength of one lucky fetch.
- **Firecrawl's 0/9 is OUR bug (#92, P1):** `firecrawl_service.py` hardcodes `formats:["html"]` =
  Firecrawl's CLEANED html, which returns **0 script tags / 0 ld+json**. The extractor reads ld+json,
  so the integration **cannot return a price on any page, ever**, while billing 1 credit each. With
  `formats:["rawHtml"]` the same URL yields 1.400 BHD and is 5.4x faster. Firecrawl also 500s on both
  controls curl cracks free, and returns **HTTP 200 + bills on a real 404**.
- **crawl4ai — rejected on measurement.** Its patchright "undetected" mode was **byte-identical to
  default on all 9 targets** and contributed zero, including both walled ones. It beat plain
  Playwright on 1 of 9, purely via its default User-Agent — and crawl4ai under-rendered that page
  into a confident-wrong "6.02 BHD" where bare Playwright returned the correct 16.0.
- **Scrape.do — narrow keeper**, behind a "curl returned a WAF block" trigger only. Its single real
  win was eros.ae (Link11 491, blocks curl+Playwright+crawl4ai). The other 3 duplicated free curl
  results at 9-50x latency, two of them EXCEEDING the 15s live clock.
- **Registry is wrong on 4 of 9 rows (#94):** `matalanme` + `xcite` are flagged `render-only` but
  plain curl reads them in <1s, so they have been escalating to PAID render for free pages; `bfab`'s
  sample_url is a category page; `letoile`'s is a 404. The registry needs a cleanup pass more than
  the stack needs a vendor.


A full audit of `main c630436` produced **GitHub issues #46–#81** (12 P1, 23 P2, 1 P3), each self-contained with verified `file:line`. Three are implemented and pushed, **no PRs opened, nothing merged, nothing deployed**: `fix/46-dependency-lock` (`d6c52ab`), `fix/58-model-config` (`b9e962e`), `fix/59-subtype-specs` (`48daac6`). Each passed the repo comm gate against `origin/main` with **branch-only-NEW == []**.

**Three findings that change how you work in this repo — full detail in `docs/investigations/2026-08-24-audit-implementation-handoff.md`:**

1. **CI has been RED on main since at least 2026-07-07** (176 failed / 9,359 passed on `c630436`). Causes: a missing `pillow` dev dependency (fixed on `fix/46`) and the RED-by-design `tests/test_value_math.py` stubs that CI never excluded (still open — **#49**). "Tests green" has not been a real merge gate; do not treat a green local run as proof until #49 lands.
2. **`pytest tests/` hangs — the default suite makes LIVE network calls.** `magento_graphql_service.py:275` and `noon_service.py:170` fetch real retailer sites in executor threads that the pytest timeout cannot kill (this is **#70** reproducing in-suite), and with `.env` present Serper 403s and OpenAI 429s stall the retries (**#48**). Run targeted file sets, excluding adapter/network-heavy files.
3. **`app/config.py` is a trap, not merely dead.** It declares seven REQUIRED pydantic fields and instantiates `Settings()` at import (`:55`), so importing it raises `ValidationError` wherever those env vars are absent. Never put new config there — `app/services/model_config.py` is the pattern to copy (env reads, safe defaults, zero required credentials). Related: `openai_service.py:20` builds `AsyncOpenAI` at module import, and every current openai release rejects keyless construction, so `import app.main` fails without `OPENAI_API_KEY` (verified across 2.54.0/3.2.0/3.3.1 — pre-existing, not a pinning artifact).

**Model ids are now config, not code** (#58): `OPENAI_MODEL_{VERDICT,STANDARD,VISION,CRITIC,MODERATION}`, resolved per call, logged once at startup as `[models] …`. Defaults are unchanged (`gpt-4o` / `gpt-4o-mini`). **Do NOT flip to a GPT-5 id without a live smoke test** — GPT-5 rejects `temperature=0` outright (the verdict's determinism A/B depends on it), requires `max_completion_tokens`, and counts invisible reasoning tokens against that same budget so a straight `1000` carry-over can return empty content. The shims (`sampling_kwargs`, `token_limit_kwargs`) prevent the 400s; they cannot restore determinism.

## Active runtime (M5-M7 fragrance capture waves — branch `feature/m7-specs`, NOT merged/NOT pushed, 2026-08-30)

Base `origin/main ddead8d` (= M0 + M5 + M6 already on main). Branch adds M7 `a6901b7` (D1 spec-refill cascade closure) → `3f4fd12` (D2 spec spine, dark, store empty + migration `035` unapplied) → `dc64c69` (D3 per-host search descriptor, dark, store empty) → this docs commit (D4). Every flag in the wave is enumerated with its default/gate/precondition in **Environment Variables → Wave M0/M5/M6/M7 flags** above; flip order in the **ACTIVATION-ORDER runbook** there.
- **Gate evidence (one line):** per-file pytest, `-m "not (live_unit or live_db or integration)"` — M5+M6 units **159 passed**, M7 D1+D2+D3 units **66 passed**, 0 failed; each unit's tests assert its own flag-OFF byte-identity, and no flag in the wave is read at import.
- **Nothing in this wave is live.** M0/M5/M6 are on main but every flag except `ENABLE_FIRECRAWL_RAW_HTML` is default OFF, and the two M7 stores (`data/spec_spine.json`, `data/search_descriptors.json`) ship EMPTY — activation is a *seed-then-flip*, not a flip. Blockers unchanged: Serper 403, OpenAI 429, no paid signups, fragrantica/parfumo never fetched.
- **Research artifacts (outside the repo, session scratchpad):** spec-spine sourcing + GTIN/crosslink measurement in `…/scratchpad/research/B5/`; discovery channel + match-rate panel (`REPORT.md`, `matchrate_table.json`, `panel30.json`) in `…/scratchpad/research/B8/`. Corpora stay read-only under `_proof/html` + `_proof/global/`; committed fixtures carry `SOURCES.json` provenance.
- **TRIM DONE 2026-08-30 (this was the PENDING TRIM):** the 2026-06/07 arc (7 blocks) and the SUPERSEDED 2026-08-25/26 branch narrative were moved VERBATIM into `docs/SESSION_BUNDLES.md`, with a one-line pointer left here per moved block. Nothing was deleted; the load-bearing halves of the 2026-08-25/26 block (only-price-is-scraped, the three killed assumptions, the Fragrantica/Parfumo prohibition, the scraper roster, the module-reference gate, the measurement traps, the corpora, the one-IP caveat) stayed in CLAUDE.md.

## Active runtime (M13 wave-3 event-loop & deadline integrity — CLOSEOUT VERIFIED, branch `feature/m16-wave3-closeout` from `e22258e`, 2026-09-01)

M13 review Wave 3 (event-loop lane) closeout. 10 findings implemented on `feature/m16-wave3-eventloop` (`c8531b4..04bd226`), integrated onto `feature/m16-wave3-closeout` from `e22258e`, plus the dispatcher must-fix + this docs commit. Six unflagged invariant fixes + four default-OFF dark offloads — all enumerated with default/effect/precondition in **Environment Variables → Wave M13-W3 flags**. **Nothing is flipped; activation is a canary.** Blockers unchanged: Serper 403, OpenAI 429, no paid signups.
- **Gates (all PASS):** (1) flag-OFF byte-identity — `scripts/verify_flag_byte_identity.py` over `_proof` (414 pages / 1,656 calls) prints identical `OVERALL SHA256 298f2ced…` at base `e22258e` and closeout HEAD with the four wave flags forced OFF; the extraction path is empty-diff so the corpus SHA cannot move. (2) comm — free-tier direct-blast-radius set at base + HEAD, `branch-only-NEW == []` (the only base failures are pre-existing baseline nodes failing IDENTICALLY at `e22258e`); tree-wide collection clean both sides (no import regression). (3) hygiene — ruff blocking tier `E9,F63,F7,F82` clean, `py_compile` clean, every new flag default OFF + read per-call, sized executor bounded (default 40, `qaren-worker`).
- **Dispatcher must-fix applied (M13-37):** the gate-reserved freemium credit was NOT refunded on the common cold-path failures (TIMEOUT/INSUFFICIENT_DATA/generic) because `_surface_comparison_failure` RAISES before the refund — unreachable dead code that burned a daily credit per timed-out cold compare. Fixed in POST+GET (refund BEFORE the surface call) + a symmetric streaming `else`-refund. The reviewer's other findings (M13-31/M13-06 non-atomic half-open, M13-34 clamps, M13-35 drain amplification) are `must_fix:false` — recorded as canary preconditions/watch items above, NOT code-changed this wave.

## Active runtime (M13 wave-4 client gates + CI floor — CLOSEOUT VERIFIED, branch `feature/m17-wave4-closeout` from `c762acf`, 2026-09-01)

M13 review Wave 4 (client-gates + CI-floor lane) closeout. 8 findings implemented on `feature/m17-wave4-client` (`2c0985c..4f5e308`, 7 conventional commits off `c762acf`), fast-forwarded onto `feature/m17-wave4-closeout` + this docs commit. **This wave is FRONTEND (SmartCompareApp/) + CI (.github/workflows) + i18n + the backend regression BASELINE only — NO backend price-path/app code changed, so the flag-OFF byte-identity gate does NOT apply.** Everything ships unflagged (client-side + CI; RN has no per-call env flag). Blockers unchanged: Serper 403, OpenAI 429, no paid signups.
- **Findings (8):** M13-13 (HomeScreen gallery fallback now passes picked photos through to `Results` via `vision_products`, under-2 pick shows a visible Alert), M13-14 (compare gate derived from the fetched `UsageStatus` with the hardcoded `used<3` as the safe fallback — a missing field/offline hydrate degrades to today's behaviour, never MORE permissive; **the derisking IS the safe fallback, no flag**), M13-15 (**63** referenced-but-missing t() keys added to BOTH en.json + ar.json + a jest referenced-key fence; the review's "64+1 dynamic" was re-derived from scratch to 63 — the 3 `referrals.bonus.expiresIn*` bases are i18next-plural-resolved and the `results.spec.*` family is a runtime template, both correctly fence-excluded), M13-16 (the FIRST frontend CI job — `frontend-tests`: `npm ci` → `jest --ci` → `eslint src` → `tsc --noEmit`, each **non-blocking** `continue-on-error`; ratchet each to blocking once its CI red count is measured), M13-17 (re-captured `tests/.pre_impl_failures.txt` 48→**14**, made the committed file the gate's ONLY default), M13-54 (ScanCameraScreen renders the full permission pad + wires `requestPermission`; Home "Open camera" CTA gated on `cameraPermissionGranted`), M13-55 (Google id_token head dropped from `diagHead`/user-facing strings + console `__DEV__`-guarded + inline babel console-strip in prod — flips backend `test_no_bare_console_log_in_auth` fail→pass), M13-64 (deleted **13** zero-render-reference dead components ~2,057 LOC + their 17 tests; CLAUDE.md design-system + hero lists corrected above). Also closes review-doc M13-74 (DEFAULT_BASELINE absolute-path bug, folded into the M13-17 commit).
- **Gates (all PASS):** (1) dispatcher-gate — no reviewer finding was `must_fix`; the two BLOCK conditions independently re-derived clean: dead-component deletion has ZERO dangling imports/JSX/`jest.mock` in the surviving tree (the one positive contract `Screens.bundleD.contract.test.ts:159` passes via its `cohortDisplay` alternative), and the i18n referenced-key fence reproduces **0 missing** in en AND ar (426 static refs, plural-aware). (2) comm (backend) — full free-tier suite at HEAD (`-m "not (live_unit or live_db or integration)"`, documented excludes, `--timeout=60`): **13 failed / 15,731 passed**, and all 13 failures are pre-existing baseline nodes in files the wave never touched (auth/camera/page_scraping/personalization/referral/supplement/extraction/backend_cleanup) → **`branch-only-NEW == []`**; the newly-PASSING `test_no_bare_console_log_in_auth` (M13-55) is correctly dropped from the re-captured baseline. (3) frontend-static — CI YAML parses, job non-blocking, `test`/`test:ci`/`typecheck` scripts present, `package-lock.json` unchanged so `npm ci` stays in sync, jest.config `testMatch` covers all 4 new test files, en/ar set-equal at **861==861**. (4) hygiene — ruff blocking tier `E9,F63,F7,F82` clean + `py_compile` clean on all 4 changed `.py`. **UNVERIFIABLE without `node_modules` (out of scope):** the actual jest red count, `tsc --noEmit` error count and eslint result — which is exactly why the CI job lands non-blocking to MEASURE them on a runner. One cosmetic leftover removed in the docs commit: the orphan snapshot `__tests__/hero/__snapshots__/ConcentricMotif.test.tsx.snap` (its test was deleted).

## Active runtime (wave-3 global hardening + fix wave — ✅ MERGED TO MAIN `6205a7c` + DEPLOYED, 2026-08-30)

**The fragrance branch below is MERGED** (FF `8adaefb..4c7abf6`, 22 commits, then `6205a7c` tooling), deployed to Railway, `/health` 200. Everything the archived 2026-08-25/26 branch block (now in `docs/SESSION_BUNDLES.md`) records as "on the branch" is now IN PROD. What shipped on top of it, this session:

- **Wave-3 unit 7** (`7c586ab`, `ENABLE_JSONLD_FIRST` default ON): JSON-LD→microdata→OG→Woo cascade, hardened microdata (parse_money, ISO label, converted_usd relabel, real availability), visible-text cross-check + 10x/100x per-unit decoy guard, capture outcomes (`ok/walled/empty_shell/no_structured_price/ambiguous_price`) via `outcome_out`.
- **The 4 gates ran, failed twice, and the FIX WAVE closed them** (Opus implementers, Fable review): `6610623` currency-evidence hierarchy (`_currency_label_for` rungs: own token → page evidence [`_page_currency_evidence`: OG metas + any JSON-LD priceCurrency] → expected-if-MISSING → raw-junk-so-strict-pends; fixes niche-beauty 195-"BHD" and samawa.ae 9.77x, preserves sharafdg); `1ac1455` OG-agreement guard on promoted microdata (2% band `_MICRODATA_OG_TOLERANCE`, fail-open ×4; kills the nazih.qa rail-price regression; corpus co-fire 28 pages, disagreement = microdata wrong); `704d6c0` all 12 red pins adjudicated STALE (call-order tests replace source-line-order); `4c7abf6` `CAPTURE_AMBIGUOUS_PRICE` on multiplicity pends.
- **Final gate state (all evidence in the 2026-08-30 session scratchpad):** flag-OFF byte-identity vs `8adaefb` = SHA256-identical over 1,656 calls, re-proven AFTER every fix commit; test estate 0 failed both flag modes (374/374 formerly-red files; 5,536 nodes/config); corpus 143 explained moves vs base, six P0 amounts exact, qatar 33.06, nazih 10 QAR/1.03 BHD, samawa 27.75 BHD. 11 flags total (incl. `ENABLE_PLATFORM_VERDICT`); `ENABLE_SHOPIFY_PDP_JSON` + `ENABLE_WIDE_SIGNAL_TEXT` default OFF, rest ON.
- **Tooling (Step 2, `6205a7c`):** ruff blocking tier `E9,F63,F7,F82` (repo-wide clean, BLOCKING in CI backend-lint, pinned 0.16.5 in the dev lock) + committed `.githooks/pre-commit` (staged py_compile, ruff, black-allowlist mirror, credential/.env guard, sqlfluff-if-installed on migrations) — **activate per clone: `git config core.hooksPath .githooks`** (set in this repo). Fixed `requires-python "^3.12"`→`">=3.12,<4.0"` (caret = invalid PEP 440, broke all standards tooling).
- **Capture-completeness scorecard (414 cached pages, pre-LLM, artifact `https://claude.ai/code/artifact/ac6ad7e5-5871-4139-b596-b691b47adeb7`):** scraping owns price 84%/identity 77%/image 82%/size 81%/concentration 82%/gender 67% of captured pages; notes pyramid 38% + longevity 32% = spec-DB/licensing lane; ratings 30%; review text 15% server-side, 38% widget-no-text (adapter buy order: Bazaarvoice 48 pgs, judge.me 39 [27/34 Gulf], Yotpo 35; Trustpilot 47 = shop badges, skip); renderer buys ~16% of global.
- **Follow-up units (recorded, not blocking):** faces.ae-class visible-text currency rung for `_page_currency_evidence` (own flag + corpus before/after); `classify_capture` "access denied" false-positive on om.swissarabian.com (needs title/heading anchoring, 1/414); scentsplit decants price = AHMED product decision; multiplicity discriminator (VariantDescriptor); sqlfluff config pass. Serper 403 + OpenAI 429 STILL DEAD (user chose scraper-variety over key rotation for now); Railway-egress re-measure precondition stands.

## Fragrance/global scrape-validation findings (2026-08-25/26) -- STILL LOAD-BEARING; branch narrative archived

**Branch narrative ARCHIVED 2026-08-30.** The `feature/fragrance-hybrid-capture` branch state, its flag-OFF byte-identity proof, and the P0 currency-mismatch write-up (`price_service.py:8818`; 21 of 92 Gulf pages lost their price, 6 shipped an inflated list price) were moved VERBATIM into `docs/SESSION_BUNDLES.md`, section "2026-08-25/26 fragrance data-provenance branch (archived from CLAUDE.md 2026-08-30)". That wave is MERGED (`6205a7c`) and its live state is the block immediately above. Everything below stays here because it is still load-bearing.

**THE FINDING THAT REFRAMES THE PRODUCT: only PRICE is scraped.** `extract_specs`
(`extraction_service.py:1147`) and `extract_reviews` (`:1356`) are OpenAI calls whose only substantive
input is a Serper snippet digest (`organic[:5]`, truncated to 3000/2500 chars,
`structured_comparison_service.py:6945`). All 13 adapter/renderer modules contain `specs` ZERO times and
`aggregateRating|reviewCount|ratingValue` ZERO times; `reviewBody` appears ZERO times in `app/`. The
prompt at `extraction_service.py:515-516` **orders** the model to fall back to training data, and the
output is cached 7 days. Reviews are properly guarded and go EMPTY instead; only SPECS are fabricated.
`derive_rating_from_scores` (`response_builder.py:160-163`) ships a **constant 3.6** rating when there
is no data at all.

**GLOBAL VALIDATION (328 pages / 163 hosts / 26 countries) KILLED THREE ASSUMPTIONS:**
1. The GCC currency rule ("dot=decimal, comma=thousands") scores **1% in EU-South**, 56% in DACH,
   65.6% corpus-wide, and every failure is a silent 100x-1000x. **Locale does not fix it** (douglas.ch
   prints the product price with a dot and the shipping banner with a comma in one document). The rule
   that works is structural last-separator **+ the ISO-4217 minor unit**: 371/371 = **100%**, all six
   regions. But the real answer is architectural: **take the price from JSON-LD, always** — 353 of 360
   JSON-LD values are already machine-normalised with zero comma-decimals, while OG is 11% deviant and
   must never be `float()`ed directly.
2. **Parsing was never the hard part — SELECTION is.** Even at 100% parse accuracy the first
   price-shaped number on a page is right only **41%** of the time (UK **13%**). Median price-shaped
   tokens per PDP: Gulf 2, UK 6, US 8, max 17. The decoys are legally mandated (Grundpreis, per-litre
   unit price, EU Omnibus 30-day-lowest, BNPL). `notino.co.uk` renders the per-litre price under the
   **same `data-testid`** as the product price, 8 characters apart, at exactly 10x.
3. **`product:sale_price:amount` is GULF-ONLY** — 7 occurrences in 328 pages, all 7 Salla/Zid, ZERO
   across 206 non-Gulf pages. The rule must be scoped to those platforms, not left generic.

Also: `detect_platform` returns **"unknown" on 43%** of usable pages and `nextjs` is not a platform (it
fires across five backends; `sephora.me` is SFCC underneath). The extractor returns **no price on 14 of
28** large international retailers (`ProductGroup`+`hasVariant` 9, `@graph`-wrapped 4, empty `offers` 1).
Ratings double outside Bahrain (38% vs 16%) but review **bodies do not** (12% vs 8.7%) because 50% of
pages load a widget and 85% of those ship zero text server-side. **GDPR/CMP walls gate 0 of 247 pages**
on raw HTTP, and `valueAddedTaxIncluded` appears on 2 of 247 — do not build a VAT branch.

**⛔ DO NOT PROPOSE SCRAPING FRAGRANTICA OR PARFUMO.** Both `robots.txt` disallow Claude agents by name —
Fragrantica names `ClaudeBot`, `Claude-SearchBot` **and `Claude-User`** (user-initiated fetches), each
`Disallow: /`. Reading only the `User-agent: *` group sees `ai-input=yes` and reaches the wrong
conclusion. Both then actively defended against our crawling mid-session: Fragrantica went 12/12 to
`403 cf-mitigated`, and **Parfumo began serving decoy pages** — correct `<title>`, but the notes,
accords, year, longevity and perfumer of a different perfume, with invented note names. 35/35
mismatched. **Any Parfumo-derived figure after 2026-08-25 23:07 is fiction.** A fragrance spec database
needs a licensing conversation or a commercial provider.

**SCRAPER ROSTER — no new vendor key is needed.** Free `curl_cffi impersonate=chrome` prices **84%** of
the 94 live Gulf fragrance sources with ZERO genuine WAF walls, and 75% of rows globally. Rejected on
measurement: playwright (7/12 vs free curl's 11/12; its 403s are self-inflicted by the HeadlessChrome
UA), **patchright (byte-for-byte identical to plain playwright on 12/12)**, primp (zero adds on 12/12),
**Firecrawl `json`/LLM mode (FABRICATES — returned review bodies occurring 0 times in the page and
`launch_year "2026"`)**, vendor geo (our egress IS Bahrain; `geoCode=bh` costs 10 credits for identical
bytes), markdown output (drops JSON-LD to 0 on every vendor), Common Crawl (1/12), Bing/DDG, Wikidata
(0/8 for notes), judge.me API (per-merchant token, unbuyable), YouTube (`search.list` = 100 units ->
~49 comparisons/day). **Size-aware Shopify variants are dead: 0 of 999 fragrance products have two
distinct ml variants** — size lives in `tags` and `body_html`, which the adapter already receives.

### ⛔ THE ZERO-REGRESSION GATE IS MODULE-REFERENCE-BASED. NEVER FILENAME-KEYWORD-BASED.

**Selecting the gate's test files by FILENAME KEYWORD would have shipped this wave green with a
deterministic regression in it.** Matching test filenames against the changed modules' names yielded
**54 files and an EMPTY branch-only failure set**. The real regression —
`tests/test_correctness_coverage_review_findings.py::test_H_jsonld_flag_off_carries_name_not_brand`,
which passes at `8adaefb` and fails at `02d5d33` in the SHIPPED default configuration, 2/2
deterministic — sat in a file whose NAME references nothing that changed. It was only reachable via the
**93 files that grep-REFERENCE the changed modules** (`price_service`, `shopify_pdp_service`,
`platform_router`).

So: **build the gate's file set by grepping the test tree for imports/references to every module the
branch touches, then run that set at BASE and at HEAD and `comm` the failures.** A filename-keyword
set is not a subset shortcut — it is a different, much smaller, and systematically wrong set. This is
now a standing rule, not a one-off observation: the miss is confirmed, and the test it missed is the
one this wave had to adjudicate (see the `H — THE JSON-LD CANDIDATE DICT UNDER ROLLBACK` block in that
file).

**MEASUREMENT TRAPS — these produced wrong conclusions in this very session:**
- **An empty `product_name` makes the JSON-LD branch unreachable** (`brand=""` -> every Product dropped
  at `price_service.py:8757`). A sweep passing `""` manufactures a fake failure cohort and understates
  free-curl capture as 72% when it is 84%.
- **`ENABLE_EXACT_PRICE_GATE=true` masks extraction bugs** — the gate rejects most cached pages so
  everything returns `None`. Use `false` to isolate extraction, `true` for shipped behaviour, and always
  say which.
- **Substring block-detection is worthless**: `<script id="captcha-bootstrap">` ships on every Shopify
  page. It fired on 80 of 94 pages with ZERO correct fires. Order any verdict ladder capture-FIRST.
- Ratio tests cannot tell a sale price from a list price after conversion — pin exact expected values.

**Zero-network corpora for any future work** (git-excluded, in the `sc-scraper-proof` worktree):
`_proof/html/` 92 Gulf PDPs + `_proof/sweep2_curl_cffi.jsonl`; `_proof/global/corpus.json` +
`_proof/global/html/` 429 global pages. Re-running the whole Gulf scorecard is
`python _proof/sweep2.py curl_cffi 6 BHD`, ~100s, no network.

**EVERY NUMBER ABOVE CAME FROM ONE BAHRAIN RESIDENTIAL IP.** Railway egress is a datacenter ASN
elsewhere. Re-measure host reachability and Shopify-Markets currency behaviour (it 302'd `/en-om` and
`/en-ae` to `/en-bh` for us) FROM RAILWAY before trusting a capacity number or retiring a paid fallback.

## Known Remaining Bugs (deferred)
- **✅ KEYS ROTATED 2026-06-27 (prod un-degraded):** `SERPER_API_KEY` PAID `7de9c750…`, `SCRAPEDO_API_TOKEN` `963772…`, new Zyte acct `e3374b…` — all set on Railway + local `.env`, prod verified live. (Was: all 3 dead 2026-06-26.) Full keys ONLY in gitignored `.env`. See the archived 2026-06-27 entry in `docs/SESSION_BUNDLES.md`.
- **Scrape.do timing out** on GCC luxury retailers (Ounass, Bloomingdales). Firecrawl is primary; Scrape.do is Tier 1.5d fallback only. Investigation `docs/investigations/2026-05-16-scrapedo-timeout-analysis.md` — recommendation: **accept current behavior** (graceful Tier 2 fallback).
- **Google Sign-In** — currently failing on EAS preview (Session 54). Apple + email/password GREEN. Awaiting Ahmed's `[GOOGLE-DIAG]` Xcode log + Railway `SOCIAL_LOGIN_TRACE` line to disambiguate iosClientId / Bundle-ID / token-shape failure mode. Backend diagnostic instrumentation kept in `auth_service.py` until resolved.

## Detailed Context
Index: `docs/CLAUDE_CODE_CONTEXT.md`. Key files: `CONTEXT_ARCHITECTURE.md`, `CONTEXT_SESSION_LOG.md`, `CONTEXT_REFERENCE.md`.
