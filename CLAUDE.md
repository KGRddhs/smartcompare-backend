# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Purpose

SmartCompare (app brand: **Qaren / قارن**) — Intelligent product comparison engine for the GCC market (Bahrain, Saudi Arabia, UAE, Kuwait, Qatar, Oman). Goal: if users still go to Google or ChatGPT after using us, we failed.

## 🚨 APP STORE PRODUCTION SHIP-BLOCKERS (read EVERY session)

These items DO NOT block TestFlight internal testing (≤100 invited testers) — those ship fine today. But they WILL block Apple App Store public-production submission and Apple's automated review will reject the build until both are resolved. Claude Code must remind Ahmed at the start of any Bundle/PR that targets App Store production.

1. **App icon ICN-0001 byte-identity** — `SmartCompareApp/assets/{icon,splash-icon,adaptive-icon}.png` are byte-identical to Expo's `npx create-expo-app` template scaffolding (SHA-256-verified by Bundle D native-ops 2026-05-24). Ahmed approved the concentric-circles design — the bytes need to differ. **Fix:** regenerate same visual as a unique render (Claude-Design re-export OR `scripts/` PIL/Cairo script with emerald `#10B981` accent / Qaren wordmark). Tracked in `docs/plans/bundle-d-followups.md`.

2. **Full legal-doc redraft** — current `app/legal/{privacy_policy,terms_of_service}.md` had brand strings rebranded (Bundle D R22) but the content is the pre-Bundle-D draft with names swapped — NOT a Qaren-jurisdiction redraft. 15 legal decisions still pending per `docs/plans/2026-05-16-tos-decisions-pending.md` (entity name, GCC jurisdiction, DPO contact, PDPL clauses, breach timeline, etc.). Apple may push back on jurisdictional mismatch (generic US-style template, no PDPL specifics). **Fix:** complete the 15 decisions + draft Qaren-specific clauses + republish via `legal_routes.py` + regen `landing/{privacy,terms}.html`.

**Routine before App Store production submission:** icon byte-different ✓, legal docs Qaren-jurisdiction-redrafted ✓, `pip-audit --strict` + `npm audit --audit-level=high` clean ✓, QA static audit grep pack re-run ✓, ASC Privacy Nutrition Labels verified against current data flows ✓. **TestFlight internal ships freely without these — they're App Store production gates only.**

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

**Design system:** `src/theme/index.ts` (emerald #10B981, Geist+Cairo). Components: Button, Card, Chip, SkeletonLoader, ProgressBar, IconButton, ComparisonCounter. i18n: `src/i18n/` (180+ keys EN/AR).

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
See skill: `qaren-scoring` (auto-loads when `scoring_service.py`, dimension scores, value badges, personalization caps ±30/10/5%, behavior_service, or `scoring_v2` contract are mentioned). Key recall: 9 categories × 6 dimensions via `CATEGORY_DIMENSIONS`; price tiers budget/mid/premium/luxury; three-layer personalization (explicit ±30% → behavioral ±10% → session ±5%); `scoring_method` enum: `category_weighted` / `personalized` / `behavioral` / `invitee_quiz`. Rollback V1: `docs/ROLLBACK_SCORING_V1.md`.

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
- **Hero illustrations** (SVG + Reanimated, **ZERO Lottie**): PhoneMockup, CohortBarChart, ConcentricMotif, LoadingRings, RevealBurst. Stage-gated SSE on StreamingProductCard (init→title→specs→prices→reviews→verdict). StageChecklist haptic ONLY on transition INTO done.
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

**Earlier 2026-06 bundles (all SHIPPED + folded into prod `b207bfa`; full narrative in `docs/SESSION_BUNDLES.md` + the per-bundle `memory/project_*` handoffs):**
- **Bundle B S2 "Intelligence"** (06-12, `5f137ec`) — 42.5% weighted (2× S1); verdict temp=0, anti-patterns, registry-discovery overhaul, latency stack. [[project-bundle-b-s2-pickup]]
- **S3 "Sources"** (06-14, `e08ddba`) — genuine-BH price layer + wrong-scrape accuracy guards + the 2-layer price cache + `cron_warm_price_cache.py` (flag `ENABLE_PRICE_CACHE_WARMER` OFF, the genuine-share lever, needs paid Serper). [[project-bundle-b-s3-state]]
- **genuine-BH latency+warmer + S3.1** (06-15, `bce638f`/`2c27c5e`) — `TIMEOUT`→HTTP 503 graceful PARTIAL (`metadata.partial`), `FAN_OUT_BUDGET_SECONDS`, `is_implausible_low_fragrance_price`, eval genuine-method parity. [[project-genuine-bh-latency-warmer-bundle]]
- **fragrance-quality + results-redesign + CATEGORY-FAIRNESS** (06-16/17, `b7af94d`) — `canonicalize_category()` keystone; price-pending shape; `CATEGORY_FAIRNESS` per-category comparable unit + `reconcile_pair_fairness`; FE 1:1 redesign. [[project-fragrance-quality-personalization-redesign]]
- **faithful-results + bundle-next** (06-17, `5219cac`/`5999799`, EAS `71044ff7`) — 7d/30d price cache + cache-first gate; `category_profile` ×9; verdict/runner-up fixes. **Eval anchor = the FULL UUID `54b603e8-4eab-41c9-a34d-a5e391446559` (smoke20 winner 0.50). Gates MUST pass the full UUID (`--baseline-run-id 54b603e8-4eab-41c9-a34d-a5e391446559`) — the short `54b603e8` 400s `invalid input syntax for type uuid` → a FALSE "GATE FAIL" (NOT a regression). COLD smoke20 shows `pass_rate=0`/`price=0` BY DESIGN (the baseline row itself does too — 30s cap) → judge by the axis AVGS (winner/specs/factual), never pass_rate. `python -m scripts.eval_runner` does NOT auto-load `.env` (only pytest's conftest does) → `set -a; source .env; set +a` (or `load_dotenv(override=True)`) first, else the baseline fetch fails "SUPABASE_URL must be set". free-unit baseline 48 + 3 NETWORK_FLAKY_EXCLUDE.** [[project-faithful-results-shipped]]
- **walk-fixes + FE polish** (06-18, `9172e62`/EAS `96098d43`) — FE results-organization + free KG/organic image tier (`image_service` Tier 1.5b); `RunnerUpWinsCard`; Codex full-arc review → SF-1 (`converted_usd` no longer 30d-negative-cached = warmer prereq). [[project-faithful-results-shipped]]
- **catfix** (06-21, `698006a`) — resolve the pair category onto `products[i].category` BEFORE `_fetch_product_data` (`_resolve_pair_category`); on the q= parser path the LLM category is AUTHORITATIVE (a green smoke20 is NOT proof for the misroute class — unit-pin). [[project-catfix-shipped]]
- **fragrance-content-quality** (06-22, `2244ad4`) — score-leak eliminated at 3 sources + `app/services/text_sanitize.strip_score_internals` chokepoint backstop; `_verdict_safe_product` (GPT never sees a pending amount); form-aware review praise; fragrance subtype-key alias. [[project-fragrance-content-quality-shipped]]

**Recurring durable gotchas (load-bearing across the 2026-06 bundles):** (a) the eval (`eval_runner`) is a PROD-HTTP harness → it is POST-DEPLOY; a pre-deploy eval measures prod-without-the-change = meaningless. (b) **stale Redis cache masks a fix** — re-running the SAME pair serves the 7d-specs/24h-price cached pre-fix payload, so a "still broken" screenshot is usually stale cache, NOT a failed deploy → re-test a FRESH/different pair or `?nocache=true`. (c) worktrees DON'T inherit the gitignored `.env` (sibling `load_dotenv` walks UP, never reaching main's) → copy `.env` into each pytest-running worktree. (d) Serper headroom is POINT-IN-TIME, not sustained — heed the `budget:serper:<key8>:lifetime` counter, not one clean eval. (e) stale OS-scope `SUPABASE_*`/Upstash env can SHADOW `.env` (`load_dotenv()` no-override) → breaks local eval persist; `unset` + restart Claude Code. Sentry-5xx-on-status-change → [[feedback-sentry-5xx-capture-on-status-surface-change]]; no-prod-write-in-harness → [[feedback-no-prod-write-belongs-in-harness]]. (f) **`gh` GraphQL returns HTTP 401** with the git-credential `gho_` token (so `gh pr merge` + `gh pr view --json` fail) — use REST: `gh api repos/<o>/<r>/pulls/N`, `--method PUT .../merge`, `--method PATCH .../pulls/N` (token via `GH_TOKEN=$(printf 'protocol=https\\nhost=github.com\\n\\n'|git credential fill|sed -n 's/^password=//p')`). (g) **comm-gate harness:** `git worktree add --detach <dir> origin/main` + copy `.env` in + run the free-unit suite both sides + `comm -13` the sorted FAILED node-id sets → `branch-only-NEW` must be empty; the 46-line prod baseline is cached at `.qa-correctness/main-baseline-failed.txt`; `test_wrong_cheap_price_guard::TestSupplementNonCFPath` is NETWORK-flaky (live bolo.bh) → re-run a branch-only-new fail against main to tell flake from regression. (h) **Windows console cp1252** chokes on `→`/emoji in `print()` — dump workflow/JSON output to a UTF-8 file + `Read` it, never `print()` non-ASCII. (i) drop top docs commits + replay code commits onto a new main: `git rebase --onto origin/main <old-base> <top-code-commit>` then force-move the branch ref.

**Active runtime (BH source-intelligence SHIPPED + genuine-price DISCOVERY CATALOG, 2026-06-25) — SUPERSEDES the BRANCH-READY entry above (now SHIPPED):** (1) The 3 $0 genuine-BH adapters (nasserpharmacy `json_api` + bolo/boutiqaat `sitemap`) **SHIPPED to prod** — round-4 fixes (MEDIUM `_sitemap_cold_domains` served-copy leak `pop` + the H5/M4 test-discrimination strengthening, each verified fail-without-fix) + a 6-lens whole-branch review **Workflow** (replaced the desktop Codex re-review #4 → CLEAN, 0 merge blockers) → **SQUASH-merged to main `e6afbcd`** (single-parent; the literal nasser token in ancestor `b75c424` NEVER landed; tree token-free; never pushed the feature branch) → pushed main → deploys **INERT** (cron OFF + token gate = zero behavior change; post-deploy probe GREEN). **nasser ACTIVATED:** `NASSER_GUEST_TOKEN` re-scraped from the FE bundle + Ahmed set it on Railway + **prod-verified** (skincare compare → `nasserpharmacy.com` `local_bhd`, CeraVe 13.341 BHD). GOTCHA: `prices/{product}` takes NO `nocache` + NO category → can't verify a category-gated adapter (use a category-resolving `compare?…&nocache=true`). Remaining: delete the local-only `feature/bh-source-intelligence` after validation; `ENABLE_SITEMAP_INDEX` cron activation (bolo/boutiqaat inert until then). Handoff `memory/project_bh_source_intelligence_branch_ready.md`. (2) **GENUINE-PRICE DISCOVERY CATALOG — 4 ultracode `Workflow`-tool rounds (batched-4 after the 18-wide tripped the server rate-limit; the throttle worsens with session length → run the BUILD in a FRESH session) → 400 verified BH/GCC price sources** (380 $0-scrape, 152 genuine-BHD, 20 render-tier; BH 82 / KSA 64 / UAE 63 / OM 39 / QA 38 / KW 29). **Disproves the prior luxury-fragrance/grocery/supplements "structural gap"** — every category now has genuine-BHD $0 sources. The GCC long tail is **PLATFORM-STEREOTYPED** (each platform = one canonical $0 extraction); **`curl_cffi impersonate=chrome` defeats most CF/TLS walls** (cracked noon BHD / extra-Unbxd / al-dawaa-OCC / nahdi+danube-Algolia / panda-API / Alshaya-GraphQL family / sporter+drnutrition genuine-BHD supplements [the hardest category — SOLVED] / the Salla storefront API; the Salla bulk vein is mostly KSA/SAR, BH-native Salla is rare). Catalog **COMMITTED on branch `feature/bh-gcc-source-catalog`**: `data/bh_gcc_source_candidates{,_round2,_round3,_round4}.json` + 4 `docs/investigations/2026-06-25-bh-gcc-price-source-discovery{,-round2,-round3,-round4}.md` (per-platform scraper map + cracked-API endpoints + integration map). **NEXT (fresh ultracode session) = the BUILD:** 6 new adapter shapes (`fetch_salla_api_price` / `fetch_woocommerce_store_api_price` / `fetch_occ_rest_price` / `fetch_alshaya_graphql_price` / `fetch_algolia_price` / `fetch_unbxd_price`) + ~400 `Source(...)` rows + new genuine source-methods in `_GENUINE_BH_SOURCE_METHODS` (grants the 7d TTL) + `scripts/verify_source_registry.py` liveness gate before `status="live"`. **NO new architecture** — reuse the `source_router` registry + 2-layer price cache + the 2 off-clock crons; Shopify/Woo/Salla/API discovery is **Serper-FREE** = the warmer unblock (the genuine-share lever without a paid-Serper blowout). 20 render-tier (Akamai: sephora.me/namshi/Carrefour-MAF) DEFERRED to a Firecrawl/Scrape.do pass. Build plan `docs/plans/2026-06-25-bh-gcc-source-build-plan.md`; handoff `memory/project_bh_gcc_source_discovery.md`.

**Active runtime (BH/GCC genuine-price source build + Zyte luxury render-tier — SHIPPED + ACTIVATED 2026-06-26, main `23b0f6b`):** Two genuine-price expansions, both built+verified via ultracode Workflows (recon → per-wave TDD → 6-auditor adversarial verification). **(1) BH/GCC SOURCE BUILD (main `2e005e7`; flag `ENABLE_BH_GCC_CATALOG_SOURCES=true` LIVE on Railway):** integrated the 400-source discovery catalog → **6 new $0 direct-fetch adapters** (`woocommerce_service`/`salla_service`/`occ_service`/`magento_graphql_service`/`rest_json_service` + `algolia_service` EXTEND + `unbxd_service`) + a JSON→Source LOADER (`scripts/build_source_registry_data.py` consolidates the 4 catalogs → `data/bh_gcc_sources.json`; `source_router._load_catalog_rows` admits ONLY `status="live"` rows AND only when the flag is on → ships dormant) + 6 new per-mechanism selectors (bahrain+gcc, `priority_rank` top-K cap `BH_GCC_FANOUT_K`=6) + **6 new genuine methods** (`woo_store_api`/`salla_api`/`occ_rest_bhd`/`magento_graphql_bhd`/`rest_json_bhd` + `zyte_render_bhd`) in `_GENUINE_BH_SOURCE_METHODS` + the eval mirror (parity-pinned). Liveness gate `scripts/verify_bh_gcc_sources.py` (control-calibrated, mechanism-aware `sample_url` probe → **274 live, 94 BHD-genuine across ALL 9 categories** — disproves the old "structural gap"). **genuine-only short-circuit fix** in `_consume_adapter_prefetch` (a CONVERTED adapter hit must NOT short-circuit over a genuine the cascade would find — the new adapters can return converted, unlike the genuine-only nasser/bolo). Converted GCC→BHD stamps the literal `converted_usd`; bahrain tier ONLY when currency==BHD (F6 re-tier). **5/6 adapters live-wired — unbxd is DEAD-WIRED** (its only store extra.com is a literal; wiring it would break dormancy + add flag-OFF regressions → deferred; `test_live_data_file_routes_all_wired_mechanisms` guards against silent dead-wiring). Comm gate PASS flag-OFF (49==49); smoke20 ACCEPTED (winner 0.55≥0.50, factual 1.0, 0% estimates, genuine-share 100% of produced); prod-verified (`Sauvage 45.0 via woo_store_api @ theperfumesclub.com`). **(2) ZYTE LUXURY RENDER-TIER (sephora-only PROOF, dormant):** closes the luxury Western fragrance/beauty BHD gap (Tom Ford/Dior/YSL — Akamai-walled `sephora.me /bh-en`, curl/Scrape.do 403). **BREAKTHROUGH: Zyte API product/productList extraction + `geolocation:"BH"` CRACKS the Akamai wall + returns structured BHD** (the old "Scrape.do super never fired" = the cascade never REACHED it, NOT a wall-failure; Scrape.do's token is also dead). `app/services/zyte_service.py` — **THE FILS-FIX** (Zyte mis-parses BHD's 3-decimal "77.000 BHD" as `77000` → `÷1000 when >=1000`, FRAGRANCE/BEAUTY-scoped) + **brand-implied match** (sephora titles OMIT the brand → distinctive-token overlap≥0.5 + fewest-extra-tokens tiebreak; no-fab rejects a "Creed Aventus"→makeup result). `scs.py _get_price` Zyte tier gated **`ENABLE_ZYTE_RENDER` (default OFF → NEVER on the 15s live path; browserHtml render >90s = too slow → OFF-CLOCK seed only; caches at the method's own cache_key, live serves CACHE-FIRST)**. `scripts/seed_zyte_luxury.py` SEEDED **13 luxury BHD prices** (Tom Ford Oud Wood 158 / Black Orchid 81.5 / Tobacco Vanille 77 / Lost Cherry 100.5 / YSL Mon Paris·Black Opium 57 / YSL Libre 42.5 / Lancôme 49.5 / Versace Eros 52.75 / Armani 74 / Prada 59 / Valentino·CH 54.5) → **prod-VERIFIED** a cached compare serves `158.0/81.5 BHD via zyte_render_bhd @ sephora.me`. **No Railway env change needed** (live path reads cache only; `ZYTE_API_KEY`+`ENABLE_ZYTE_RENDER` live ONLY where the seed runs = local). **🔑 PENDING — NEXT FRESH ultracode SESSION (context near 1M; START FRESH):** (a) **Serper DEPLETED** (every `/search`+`/shopping` → 400 "Not enough credits") → degrades specs/reviews/images + non-Zyte prices → **GET A NEW SERPER ACCOUNT** (paid recommended — free is a finite ~2,500 one-time; rotate via `railway variables --set`+redeploy + reset `budget:serper:<key8>:lifetime` + DEL `budget:serper:burn_alert_fired:*`); Zyte prices unaffected (Serper-free). (b) **Scrape.do token DEAD** (prod==local==401) → ROTATE + **try Scrape.do as a render alternative to Zyte**. (c) **FIX Zyte failures**: Dior(Sauvage/MissDior)+MarcJacobs+V&R didn't strict-match sephora titles (7/20 pended) → per-brand match-tuning; concentration precision (Oud Wood matched Parfum 158 not the EDP 77 — fewest-extra penalizes "Eau de Parfum"); 2 transient Zyte empty-extracts (Mugler/Paco) → add retry. (d) THEN a **mobile-app comparison** after ALL addressed (ultracode). **DURABLE GOTCHAS:** Sentry MCP NOT connected this session → use `railway logs --service web` for prod errors (Railway CLI works post-`railway login`; `railway status` shows Service:None → pass `--service web`); VERIFY-THE-RESULT-NOT-A-GLANCE (I mis-parsed fragrance specs on a GUESSED field-path first — dump RAW JSON: fragrance specs ARE rich = `scent_family`/`notes_top`/`notes_heart`/`notes_base`/`longevity`/`sillage`, scoring dims = character/longevity/projection/versatility/wear_value/presentation, pros+cons present); `.env` vars are NOT `export`ed so `source .env` doesn't reach a child python → use `load_dotenv(dotenv_path="…/.env")` (find_dotenv() fails from a `python - <<PY` stdin script); a deploy to remote main = `git push origin <branch>:main` (FF, doesn't touch the working tree's unrelated uncommitted changes — safer than checkout+squash). Handoffs: `memory/project_bh_gcc_source_build.md`, `memory/project_zyte_render_tier.md`, `memory/project_bh_gcc_source_discovery.md`.

**Active runtime (key rotation + all-category genuine-price fixes SHIPPED + the CORRECTNESS reframe, 2026-06-27, main `b207bfa` via PR #8):** Rotated all 3 dead keys (Serper PAID `7de9c750…`, Scrape.do `963772…`, NEW Zyte acct `e3374b…`) on Railway + local `.env` → **prod un-degraded** (verified live). **A/B (`scripts/ab_render_providers.py`): Zyte STAYS the sephora render provider** — Scrape.do `super`+geoCode=bh DOES crack Akamai (Oud Wood PDP → 77) but **can't SEARCH** (only renders a given URL) → backup + Tier-1.5d only. **SHIPPED via PR #8 (`b207bfa`, comm-green, Sentry-clean, smoke20 winner 0.50/factual 1.0 held, cold genuine-share ~doubled to 33%):** (1) Zyte matcher hardening (`c50f05c` — hard `_identity_tokens` equality gate replacing loose overlap, concentration EDP/EDT-tie-by-`metadata.probability`, **diacritic NFKD fold** [Giò≡Gio], per-run account kill-switch on 401/402/403); (2) an all-category genuine-price loop (`135e21c`, built via an ultracode work-test-fix-improve Workflow that probed REAL Serper data) fixing 3 systemic drops: **matcher** (`strict_title_match` now concentration-collapses EDT≡"eau de toilette"; algolia `_overlap_score` concatenation-tolerant for "AIRFORCE"≡"air force 1"), **latency starvation** (concurrent gl=bh/gl=us in `serper_service`; `_pf_eligible` no longer suppressed by niche Shopify when a discovery-only BH source exists), and **199 dead-wired catalog rows** (`mechanism=''` had NO selector → `get_curl_pagescrape_sources_for_category` + supplement Stage-3 wiring, flag-gated). **🔑 THE CORRECTNESS REFRAME (load-bearing, Ahmed-caught):** "100% genuine" was PROVENANCE (`source_method∈genuine`), NOT correctness — the manual warm cached WRONG prices (S24 256GB→S24 FE; Bleu de Chanel EDP→EDT; Nike Dunk Low 18.5→ounass related/cheapest node; OOS counted live). **Purged 18 polluted keys (Redis 18 + DB 211 rows) + PAUSED warmer activation.** An ultracode gap-detection Workflow (`wf_cb44f270-ed6`) critiqued the fix plan → **75/76 gaps confirmed**: the cheapest-node bug lives at **3 tiers** (`extract_jsonld_price:3298` + cross-adapter `_consume_adapter_prefetch:4674` `min(…,key=amount)` + pair-fairness re-select) on EVERY path (woo `>=best:continue`, shopify `variants[0]`, magento/rest_json/shopping/algolia/microdata/OG); **OOS computed in ~9 extractors, enforced in 1 (occ)**; no exact gate (`strict_title_match` is a SUBSET check); cache-key collides EDP≡EDT/FE≡base (no concentration/variant axis, derived from request not resolved match); KPI unmeasurable as-scoped. **Fix shape (planned, NOT built): ONE shared exact-identity gate + ONE authority selector (never `min(amount)`) + fail-closed `is_price_showable` backstop (in_stock-False/invalid-URL/non-exact→PEND) + cache-key-from-resolved-identity** + a `usable_exact_genuine` KPI (exact SKU∧native BHD∧current PDP∧in-stock∧valid-URL / all requested) tested 30-50 products/category. **DURABLE GOTCHAS:** (a) a local `_get_price`/seed/warm with `nocache=True` STILL WRITES to the shared Upstash + `product_prices` DB (nocache bypasses the READ, not the WRITE) → local testing POLLUTES prod cache; price cache keys are HASHED `price:<12hex>` (reconstruct via `build_size_aware_price_cache_key(brand,name,variant,region,search_query)`, NOT pattern-scannable); the DB column is `product_key` (NOT cache_key) and APPENDS HISTORY (211 rows for 18 keys). (b) COLD compares hit the 30s `STREAM_HARD_CAP` → genuine curl loses → `converted_usd`/partial; `_get_price` in isolation (no compare cap) ≈ the WARMABLE ceiling (electronics/fashion/fragrances all 100% at a 60s cap); the WARMER (cache-served) is the only genuine-on-device path for cold — **but the warmed cache-key must match the live query's parse** (warmed "Eau de Toilette" ≠ live "EDT" → cache MISS; the cache-key-normalization gap). (c) **Sentry MCP** add: `claude mcp add --scope user --transport http sentry https://mcp.sentry.dev/mcp` then `/mcp` auth (org `qaren-rr`, backend project `python-fastapi`); `firstSeen:-2h`/`lastSeen:-2h` REJECT (server prepends `>=`) → use bare `is:unresolved`+`sort:new`+`period`, read timestamps. (d) **Railway**: after `railway login`, LINK the dir non-interactively `railway link --project empowering-enthusiasm --environment production --service web`; `railway status`/`variables`-read can flap "Problem processing request" while `whoami`/`list`/`variables --set` work → retry. (e) **deploy-classifier blocks** `git push origin …:main` AND destructive prod ops (Redis flush + DB delete) → needs explicit user auth / PR; open a PR with `gh` by reusing the git credential as `GH_TOKEN=$(printf 'protocol=https\\nhost=github.com\\n\\n'|git credential fill|sed -n 's/^password=//p')` (gh CLI itself was unauthenticated; token never printed). Handoff: `memory/project_genuine_price_correctness_plan.md`; plan `docs/plans/2026-06-27-genuine-price-correctness-build.md` + `.qa-correctness-gaps.json`.

**Active runtime (genuine-price CORRECTNESS — ✅ STRUCTURAL REDESIGN DONE on `feature/genuine-price-correctness`; PR #9 pushed + DO-NOT-MERGE pending an external review, 2026-06-28):** The subset `_selection_match` was replaced by **keystone v2** (general superset guard + per-category PADDING + contradiction/numeric axes: concentration/size/storage/RAM/chip-tier/count/strength/%/SPF/+plus/flavour/finish/material/fit/condition/inch/gender[asymmetric: a femme flanker must be confirmed, a homme/unisex query tolerates the base]/form), and — THE structural root cause — **the orchestrator-resolved category is now THREADED on EVERY price path**: the 3 extractors + ALL 8 genuine adapters (woo/salla/occ/magento/rest_json/unbxd/shopify/algolia) + a **per-task ContextVar** (`set_resolved_price_category` in `scs._get_price`) for the deep render/page-scrape chain + **`"other"` re-inference** at the TOP of `_selection_match` (guard runs for the KNOWN cats + explicit `other`; a truly-None category — direct-unit-call-only, prod always threads `canonicalize_category` ≥ `other` — stays subset-only). `select_best`=authority-not-cheapest; `should_cache_price` fail-closed; `is_price_showable(enforce_correctness)` the display chokepoint; a 512-char `_MATCH_INPUT_CAP` ReDoS guard. Rollback flag `ENABLE_EXACT_PRICE_GATE` (default ON; **flag-OFF VERIFIED byte-identical** to b207bfa/main via a golden compare). HEAD `7fb4127` (18 commits `12e031c..7fb4127`). **GATES: 14 adversarial review workflows** — 9 coverage-driven rounds (→ 0 CRIT/HIGH leak; keystone confirmed structurally sound), 3 independent reviews (→ 0 blockers; the last 0 leaks / 42 worst-case GCC listings at the airtight `select_best`+`should_cache_price`; the 2nd caught the algolia adapter gap), 1 comprehensive 8-lens (→ caught a **ReDoS** + a **flag-OFF rollback regression** + gender-leak + list-crash + cosmetic-key leaks, all fixed), 1 fix-verification (→ flag-OFF golden CLEAN + 1 **dual-colourway** HIGH fixed). **comm zero-regression** (branch-only-NEW==[] vs the 46-line `.qa-correctness/main-baseline-failed.txt`, ~8261 passed; the only 2 branch failures are documented shared-state flakes — `test_retailer_quotes`=serper-budget, `test_prices_endpoint_rate_limited`=rate-limiter-state — both PASS isolated / fail on main too). **RESIDUAL (documented, fail-closed-SAFE, below the no-CRIT/HIGH-leak bar):** the display-chokepoint + cache-read use the axis-only `_backstop_identity_ok` (defense-in-depth BEHIND the airtight write/selection gates → a **warmer-reactivation precondition**); cold descriptive-title over-rejection (~64%, correctness>coverage, KPI-gated); makeup one-sided finish-add; hyphen-vs-space (Omega-3≠Omega 3); apparel size-letter. **➡️ NEXT-SESSION REMAINING (in order):** (1) **`/code-review ultra 9`** — the independent external review the dispatcher CANNOT self-certify (user-triggered/billed; run on PR #9). GATE every finding against real code — reproduce through the runtime selector the orchestrator calls (`_selection_match`/`select_best`/`should_cache_price`/`is_price_showable`/the adapters), fix real blockers TDD-first, re-run the comm gate. (2) On a clean review → **merge PR #9** to main (Railway deploys ~90s). (3) **POST-MERGE** (the eval is a PROD-HTTP harness — ONLY after deploy): `python -m scripts.eval_runner --subset smoke20 --mode regression --baseline-run-id 54b603e8-4eab-41c9-a34d-a5e391446559` (winner ≥0.50, factual 1.0) + a flag-ON `compare?q=…&nocache=true` prod spot-check (returns the EXACT SKU, not a sibling) + the Serper-heavy COLD/WARMED `usable_exact_genuine` KPI (`--kpi usable_exact_genuine`, 30-50 products/cat). (4) **warmer** (`ENABLE_PRICE_CACHE_WARMER`) stays PAUSED until the KPI is ≥85%/category AND the cache-read/chokepoint backstop is hardened-to-full-matcher OR a fresh purge confirmed. **LESSON (load-bearing, 3×-confirmed): a green comm gate + self-review + even adversarial workflows LIE if HYPOTHESIS-driven — only a COVERAGE-driven sweep (enumerate the full space, both directions, reproduce through the runtime) + a DISTINCT-framing independent review falsifies; each of the 14 reviews found the SAME class (category must be threaded everywhere) in a NEW place (extractors → 7 adapters → algolia → the page-scrape chain → `other`).** [[feedback-coverage-driven-review]] [[feedback-green-gate-not-correctness]] [[feedback-verify-llm-reviewer-findings]] Handoff: `memory/project_genuine_price_correctness_plan.md`; PR https://github.com/KGRddhs/smartcompare-backend/pull/9.
**Ready-to-paste NEXT-SESSION prompt (genuine-price correctness — PR #9):**
```
PR #9 (feature/genuine-price-correctness) is the genuine-price CORRECTNESS structural redesign — DONE + pushed, 14
in-session review workflows green, comm-clean, flag-OFF byte-identical, DO-NOT-MERGE pending an external review.
(1) Run `/code-review ultra 9`. GATE every finding against the real code — reproduce each through the runtime selector
    the orchestrator calls (_selection_match / select_best / should_cache_price / is_price_showable / the adapters),
    fix real blockers TDD-first, then re-run the comm gate: worktree of origin/main + copy .env + run the free-unit
    suite both sides + `comm -13` the sorted FAILED sets — branch-only-NEW must be [] vs
    .qa-correctness/main-baseline-failed.txt (ignore the 2 known flakes: test_retailer_quotes, test_prices_endpoint_rate_limited).
(2) On a clean review, merge PR #9 to main (Railway auto-deploys ~90s).
(3) POST-MERGE (eval is prod-HTTP): `python -m scripts.eval_runner --subset smoke20 --mode regression --baseline-run-id
    54b603e8-4eab-41c9-a34d-a5e391446559`; a flag-ON `compare?q=…&nocache=true` prod spot-check (exact SKU, not a sibling); the COLD/WARMED
    `usable_exact_genuine` KPI (`--kpi usable_exact_genuine`).
(4) Keep ENABLE_PRICE_CACHE_WARMER PAUSED until KPI ≥85%/category AND the axis-only cache-read/display backstop is
    hardened to the full matcher OR a fresh purge confirmed.
Full context: memory/project_genuine_price_correctness_plan.md + the PR body.
```

**Active runtime (electronics cellular cache-key parity — SHIPPED main `de9f420` via PR #14, 2026-07-01; base = the PR #9 exact-SKU gate `cdaf5c5`):** `extract_weight_or_volume` mis-parsed a bare cellular `5G`/`4G`/`3G`/`2G` as a GRAM weight (`(5.0,"g")`), so `size_variant_token`/`_identity_cache_token` injected a phantom size token → a phone's base query and its genuine "…5G" PDP hashed to DIFFERENT price cache keys (a warm-vs-live warmer-parity MISS across electronics; pre-existing on main). Fix: `_CELLULAR_GEN_RE` (`\b[2-5]G\b`) + `_strip_cellular_generation(text, category)` strips the bare cellular token ONLY for electronics AND ONLY when `exact_gate_enabled()`; category via `_resolve_extractor_category`, but the INFERENCE fallback runs on the CELLULAR-STRIPPED text so a bare `[2-5]G` can't be the digit that self-promotes a brand-collision food ("Apple Sauce 3G", "Nothing Bundt Cake 2G") to electronics via `is_electronics_query`'s brand+digit rule (a coverage-review-caught regression) — supplement/grocery grams stay distinct ("Creatine 5G"≠"Creatine 10G"). `category` threaded `size_variant_token`→`_identity_cache_token`→`build_size_aware_price_cache_key` from `scs._get_price`. **flag-OFF (`ENABLE_EXACT_PRICE_GATE=false`) byte-identical to b207bfa; the matcher weight axis `_weights_volumes` is UNTOUCHED → correctness/display gate unchanged (a cache-key collision self-heals via `_cache_price_identity_ok`), so this is warmer-parity ONLY, never a wrong-price serve.** GATES: TDD `tests/test_cellular_generation_cache_key.py` (coverage-driven, both directions, adversarial G-embedded models Moto G54/Nokia G22 + brand-collision foods); a 3-framing coverage-driven review caught the brand-collision false-merge (fixed `b7c58db`, infer-on-stripped-text); comm zero-regression (branch-only-NEW == []); post-deploy smoke20 no-regression (axis AVGS = baseline, `nocache` bypasses the cache so the metrics are structurally invariant to a cache-key change). PRE-EXISTING (documented, NOT fixed — narrow, non-regressive): a sizeless+qualifierless electronics model with "5G" only in its NAME doesn't collapse (empty-token fallback hashes raw name; the obvious `_strip_identity_axes(name)` fix is UNSAFE — dose-merges 1000 IU≡5000 IU). UNBLOCKS the warmer's electronics cache-key parity. [[project-cellular-cache-key-parity]]

**Active runtime (pre-launch price-discovery arc + scraper-fleet audit + "WARMER IS THE LEVER" — SHIPPED 2026-07-06/07, main `473f7cc`; 5 PRs #26-30):** Fixed the local-brand ("Ajmal Aristocrat vs Rasasi Hawas") "This one's not loading" dead-end via 5 flag-gated, comm-green, coverage-reviewed PRs (all flag-OFF byte-identical). **PR #26 `102272d`** — (a) streaming/sync hard-cap now SALVAGES a `success:true` PARTIAL with specs (was a zero-product 503; `ENABLE_EARLY_SPECS_STASH` default-ON early identity+specs+price buffer + done-callbacks), (b) wired the 40 orphaned gcc `/products.json` Shopify rows (rasasistore/sa.ajmal/swissarabian) via `get_gcc_shopify_pagescrape_sources_for_category` → `fetch_shopify_price` (the literal plan's "curl-pagescrape from a domain" was a NO-OP — `fetch_page_price` needs a PDP URL). **PR #27 `eabc455`** — BRAND-IMPLIED matcher: own-brand stores OMIT their brand from titles (en-bh.ajmal lists "ARISTOCRAT HER EDP", not "Ajmal Aristocrat"); the 5 adapters that lacked `candidate_brand` (shopify[+shopify_gcc]/unbxd/salla/woo/rest_json) now derive the candidate's OWN brand (vendor/brandEn/brand.name/brands[]+pa_brand/per-store) via a shared crash-safe `normalize_candidate_brand` + thread it into strict_title_match+selection_primary_admits+_selection_match (mirrors magento/occ/noon/algolia which already had it). **PR #29 `473f7cc`** — FAIRNESS estimate-skip: a sizeless ESTIMATE was assigned the flagship-100ml default → "reached target" → PENDED the pair's GENUINE showable price (`_fairness_ignore_estimate_enabled` default-ON: skip fairness when either side is an estimate; converted_usd is NOT an estimate). **PR #28 `c070f1f` + #30 (open)** — Bright Data SERP fallback (dormant): `brightdata_service.py` (POST api.brightdata.com/request, Bearer, google.com/search?…&brd_json=1&gl=bh&hl=en, tbm=shop; defensive+self-logging mapper → Serper `{organic,shopping}` shape) wired into `serper_service.search_web`+`search_price_organic` when Serper absent/exhausted, gated `ENABLE_BRIGHTDATA_FALLBACK`+`BRIGHTDATA_API_KEY`+`BRIGHTDATA_ZONE`. **🔑 THE LOAD-BEARING FINDING: the fixes are CORRECT but MASKED on cold compares** — the depleted/degraded Serper makes the 15s live price race TIME OUT before the fast Serper-free adapters land, so a `nocache=true` prod compare STILL pends genuine prices (nocache bypasses the READ, not the write). **THE WARMER IS THE LEVER — prod-PROVEN 2026-07-07:** an off-clock warm (60s budget, WITH the fairness fix) resolves+caches the genuine price, and a LIVE cache-read compare then serves it (`Ajmal Aristocrat 21.5 BHD via noon.com, success:true, partial:None, cache_hit:true, 16s` — the dead-end is GONE). **🔬 SCRAPER-FLEET AUDIT (`.qa-correctness/scraper_audit.py`, 223 probes) + a 3-agent Serper-alternatives research Workflow:** (a) the free Serper key DEPLETES under normal traffic (recurring, not one-time — my own audit exhausted it mid-run); (b) NO SERP vendor recovers GCC Google *Shopping* (Google-side gap — SerpApi lists sa/ae only); Bright Data (5k/mo free, drop-in) is for the LONG-TAIL organic *discovery*, NOT the local houses (they're direct-adapter, Serper-free); (c) adapter scorecard: `magento_gql`+`unbxd` are fast genuine MVPs, `noon` genuine but SLOW (6-8s, eats the race), 0 exceptions/timeouts (reliable, just narrow). **DURABLE GOTCHAS:** (a) `api.brightdata.com` is TLS-blocked from the build machine (`WRONG_VERSION_NUMBER` on curl+httpx+PowerShell — a local proxy/inspection issue, NOT code; won't affect Railway) → CANNOT live-test Bright Data from here → PR #30 makes it SELF-LOG its response shape so the FIRST prod call validates the mapper. (b) VERIFY genuine-price fixes via a WARMED cache-read (`compare?q=…` no-nocache), NOT a `nocache=true` cold compare (cold ALWAYS pends on the degraded 15s race). (c) the exact-gate correctly REJECTS "Hawas For Him" for query "Rasasi Hawas" (fail-closed descriptive/gender-variant over-rejection) → falls to estimate → the PINNED correctness>coverage tradeoff needing structured VariantDescriptor metadata, NOT a token loosen [[feedback-token-failclose-needs-structured-metadata]]. (d) prod /compare is rate-limited 10/min — space out prod test compares. **➡️ NEXT ULTRACODE SESSION (the ready-to-paste prompt below):** activate the WARMER cron (the lever) + Bright Data (key provided) + run the eval/measurement workflows. Handoff `memory/project_price_discovery_coverage_launch.md`. [[feedback-coverage-driven-review]] [[project-warmer-cron-broken-kpi-snapshot]]
**Ready-to-paste NEXT-SESSION prompt (activate warmer + Bright Data + measure — ultracode):**
```
The pre-launch price-discovery arc SHIPPED (PRs #26-30, main 473f7cc): salvage+shopify_gcc, brand-implied matcher,
fairness estimate-skip, Bright Data fallback. All correct + prod-verified via a WARMED cache-read (Ajmal Aristocrat
21.5 shows), but MASKED on cold compares (degraded Serper 15s race times out). Full context:
memory/project_price_discovery_coverage_launch.md. Do, in order:
(1) ACTIVATE THE WARMER (the lever): Railway -> price-warmer service -> Settings -> Config-as-code -> set path to
    /railway.warmer.json (PR #23 fix; else it runs uvicorn); set ENABLE_PRICE_CACHE_WARMER=true; redeploy. VERIFY
    `[cron_warm] done` in `railway logs --service price-warmer` (empty logs = the config step didn't take). Confirm
    ENABLE_EXACT_PRICE_GATE is on/unset (the brand-implied fix is gated by it).
(2) ACTIVATE BRIGHT DATA: merge PR #30 first, then set ENABLE_BRIGHTDATA_FALLBACK=true, BRIGHTDATA_API_KEY (Ahmed's key),
    BRIGHTDATA_ZONE=serp_api1. On the first Serper-depleted discovery call read the `[brightdata] parsed OK top-keys=…
    org0_keys=…` (mapper correct) or `[brightdata] non-JSON …` (zone returns HTML -> switch the request to
    data_format:json) log line and tighten _map_bd_organic/_map_bd_shopping. Run tests/test_brightdata_fallback.py.
    NOTE api.brightdata.com is TLS-blocked from the build machine -> that prod log IS the validation.
(3) MEASURE (prod-HTTP, POST-warmer): re-run the failing pairs via a WARMED cache-read `compare?q=…` (no nocache) ->
    genuine BHD shows; smoke20 no-regression `--baseline-run-id 54b603e8-4eab-41c9-a34d-a5e391446559`; the
    usable_exact_genuine KPI (`--kpi usable_exact_genuine`) COLD vs WARMED to size the warmer/Bright-Data lift.
(4) BIGGER (separate, careful): structured VariantDescriptor metadata for the exact-gate over-rejection
    ("Hawas For Him" ≡ "Rasasi Hawas" — a pinned correctness tradeoff; a fail-close re-introduces worse over-rejection).
Use ultracode Workflows (recon -> TDD -> coverage-driven review -> comm gate flag-OFF-byte-identical); gate on the
comm-diff NOT CI (RED-by-design); run heavy/wide fan-out in a FRESH session (rate-limit worsens with session age).
```

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
**Optional:** `SENTRY_DSN` (backend + mobile share org `qaren-rr`, different DSNs), `LOG_LEVEL` (INFO), `CORS_ORIGINS`, `STREAM_HARD_CAP_SECONDS` (30.0 since 2026-06-09 B0-C Item 3 — was 25.0; outermost `asyncio.wait_for` on streaming + non-streaming `compare_from_text` per L2.7), `SCRAPING_MODE` (`hard`/`soft` — `soft` skips Firecrawl+Scrape.do for non-luxury URLs), `DEBUG_STAGE_TIMINGS` (true since Sprint A — opt-in `metadata.stage_timings_ms`)
**Price Scraping:** `FIRECRAWL_API_KEY`, `SCRAPEDO_API_TOKEN` (DEAD 2026-06-26 — prod==local==401, rotate), `ENABLE_FIRECRAWL` (true), `ENABLE_SCRAPEDO` (true), `ENABLE_PAGE_SCRAPE` (curl_cffi), `ZYTE_API_KEY` (Zyte API render — cracks Akamai+BH-geo for luxury; used ONLY by the off-clock seed, NOT the live path).
**Version Check:** `APP_MIN_VERSION`, `APP_LATEST_VERSION`, `APP_FORCE_UPDATE`.
**Feature Flags:** `ENABLE_COHORT_PERSONALIZATION` (ON since 2026-05-05), `ENABLE_REFERRAL_SYSTEM`, `ENABLE_HYBRID_MODEL_ROUTING` (**phantom** — env value cosmetic, zero code refs; see `docs/BUNDLE_C_PROD_STATE.md`), `ENABLE_REENGAGEMENT_PUSHES` (gates `evaluate_user` + cron, fail-CLOSED), `REENGAGEMENT_CANARY_PERCENT` (100; djb2 via `feature_bucket.hash_bucket`), `ENABLE_BH_GCC_CATALOG_SOURCES` (**ON in prod since 2026-06-26** — loads the 274 liveness-gated BH/GCC catalog rows from `data/bh_gcc_sources.json`; default OFF→registry==literals), `ENABLE_ZYTE_RENDER` (default OFF — the slow Zyte luxury-render fires ONLY off-clock via `scripts/seed_zyte_luxury.py`, NEVER on the 15s live path; live serves cache-first), `ENABLE_PRICE_CACHE_WARMER` (OFF — the off-clock `cron_warm_price_cache.py` warmer = the genuine-share lever, needs paid Serper; knobs `WARMER_SUBSET`/`MAX_QUERIES_PER_RUN`/`PRICE_RACE_TIMEOUT`), `ENABLE_SITEMAP_INDEX` (OFF — bolo/boutiqaat off-clock sitemap-index cron; inert until set), `ENABLE_SELF_CRITIQUE` (OFF — verdict self-critique pass), `ENABLE_REVIEW_SOURCE_CONSULT` (OFF — passive|active review-source consult). All flags default OFF in code; flip in Railway during canary. `REAL_ACTION_MIN_SECONDS` (5). `ENABLE_EXACT_PRICE_GATE` (default ON, IN PROD — the exact-SKU correctness gate; flag-OFF byte-identical; the brand-implied match is gated by it). **2026-07-06/07 price-discovery arc (PRs #26-30):** `ENABLE_EARLY_SPECS_STASH` (default ON — hard-cap PARTIAL salvage), `ENABLE_FAIRNESS_IGNORE_ESTIMATE` (default ON — fairness skips an estimate side so a genuine price isn't pended), `ENABLE_BRIGHTDATA_FALLBACK`+`BRIGHTDATA_API_KEY`+`BRIGHTDATA_ZONE` (default OFF/unset — dormant Bright Data SERP fallback for Serper depletion; zone `serp_api1`; validate the mapper from the first-call `[brightdata] parsed OK …` log). Warmer is the genuine-price VISIBILITY lever (cold compares mask the fixes via the degraded 15s race — activate `ENABLE_PRICE_CACHE_WARMER` + the `/railway.warmer.json` config-file).

Operational rollout sequence + canary monitoring guidance: see `docs/CONTEXT_SESSION_LOG.md`.

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
- ~100 test files (`test_<feature>.py`, one per service). 80%+ coverage target for new features.
- No regressions: all existing tests must pass before merging.
- **Eval gate (Bundle B B.6):** pre-merge `python -m scripts.eval_runner --subset smoke20 --mode regression --baseline-run-id 4aee8e88-da97-41b3-974b-3e75c2c9c10e` (S1 baseline = 21.0%). Measurement runs ALWAYS `--concurrency 1` (walls are load-sensitive); full-200 needs `--allow-full` + dispatcher GO (~600-1,000 Serper credits). Runbooks: `docs/runbooks/qaren-eval.md` + `qaren-gold-set.md`.
- **Known RED-by-design:** `tests/test_value_math.py` (24 TDD stubs for unimplemented Bundle C v1.1 fns) — not a regression. Gate batches must exclude network-dependent "free" tests (e.g. `test_rate_limiting_complete.py` does a real GET).
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

## Known Remaining Bugs (deferred)
- **✅ KEYS ROTATED 2026-06-27 (prod un-degraded):** `SERPER_API_KEY` PAID `7de9c750…`, `SCRAPEDO_API_TOKEN` `963772…`, new Zyte acct `e3374b…` — all set on Railway + local `.env`, prod verified live. (Was: all 3 dead 2026-06-26.) Full keys ONLY in gitignored `.env`. See the 2026-06-27 Active-runtime entry.
- **Scrape.do timing out** on GCC luxury retailers (Ounass, Bloomingdales). Firecrawl is primary; Scrape.do is Tier 1.5d fallback only. Investigation `docs/investigations/2026-05-16-scrapedo-timeout-analysis.md` — recommendation: **accept current behavior** (graceful Tier 2 fallback).
- **Google Sign-In** — currently failing on EAS preview (Session 54). Apple + email/password GREEN. Awaiting Ahmed's `[GOOGLE-DIAG]` Xcode log + Railway `SOCIAL_LOGIN_TRACE` line to disambiguate iosClientId / Bundle-ID / token-shape failure mode. Backend diagnostic instrumentation kept in `auth_service.py` until resolved.

## Detailed Context
Index: `docs/CLAUDE_CODE_CONTEXT.md`. Key files: `CONTEXT_ARCHITECTURE.md`, `CONTEXT_SESSION_LOG.md`, `CONTEXT_REFERENCE.md`.
