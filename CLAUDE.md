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
- Backend: `pip install -r requirements.txt` (Railway uses this, NOT pyproject.toml)
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

**Active runtime:** **Bundle B Session 2 "Intelligence" shipped 2026-06-12 (main `5f137ec`).** Full-200 exit: **42.5% weighted (vs S1 21.0% — doubled)**; price .840 / specs .874 / winner .495 / factual .945; p95 29.9s inside cap; errors 46→11. Winner <0.60 carried to S3 (structural class = Bahrain data layer; SESSION_BUNDLES Session 61 ledger). LIVE since S2: verdict temperature=0, global+per-cat anti-patterns (exemplars measurement-emptied — APs carry the signal; content parked `data/verdict_exemplars.s3_parked.json`), unified verdict prompt, registry discovery overhaul (window 8, category-aware, liveness gate `scripts/verify_source_registry.py`), latency stack (fan_out 12s, price cap 15s, reviews-trim, 3 concurrency levers), Serper 80%-burn alert (no-expiry latch — rotation must DEL `budget:serper:burn_alert_fired:*` + reset counter), per-domain {registry,legacy} `/admin/costs` buckets, self-critique system (`ENABLE_SELF_CRITIQUE` OFF), review-consult (`ENABLE_REVIEW_SOURCE_CONSULT` OFF, passive|active), 8 dim rows, one-sided-MISSING suppression, missing-dim KPI dial in eval metadata. **OP ITEM RESOLVED 2026-06-12 (post-close-out):** the G6-tail degradation had TWO causes, both fixed via Railway CLI + Upstash REST — (1) `budget:serper:lifetime` was 5136 vs cap 2200 (counter is not key-scoped; carried 4 accounts of burn) → DEL'd, no `burn_alert_fired:*` sentinel existed; (2) **Railway `SERPER_API_KEY` was still the depleted `3d304e...`** — the dashboard edit to `0cda9843...` was staged but never applied (Railway queues var edits until "Deploy changes"); set via `railway variables --set` + `railway redeploy`. Verified: cold prices probe → `source_method=local_bhd, _cached=false`, counter reincrementing (10). Also: local `.env` Upstash creds pointed at a DELETED database (`faithful-eel-37884` NXDOMAIN globally — local runs were silently Redis-less, fail-open masked it) → synced to prod values. Serper key `0cda9843...` (rotated 2026-06-12, account fresh ~2,490). Eval runs: ALWAYS sandbox-disabled (box DNS blocks Supabase persistence otherwise) + `--concurrency 1`. S1 baseline row `4aee8e88` remains the anchor until an S2 row persists. **S3 "Sources" opens with `docs/plans/2026-06-12-bundle-b-s3-prep-notes.md`** (prereqs: Reddit OAuth + YouTube Data API key BEFORE planning; what-worked/what-didn't; ready-to-paste kickoff prompt) + Session 61 carry-over ledger (SESSION_BUNDLES.md). S2 housekeeping (worktrees + team dirs) done 2026-06-12.

**Active runtime (S3 "Sources" — accuracy + cache lever, 2026-06-14, main `e08ddba`):** Bundle B S3 shipped the genuine-BH price layer + wrong-scrape accuracy guards + the price-cache architecture. **Deployed:** `43e7711` (accuracy guards) + `e08ddba` (warmer cron, dormant). **Serper ROTATED** to `696e4e57…` (prior `05d552d7…` depleted mid-session → prod had degraded to `estimated`; free serper.dev accounts are a FINITE ~2,500 one-time credits; new key set via `railway variables --set` + push-redeploy; cold prod scrape now returns `converted_usd` = Serper live). **Accuracy guards (category-general, "no wrong scrapes", 35/35 tests):** `is_implausible_high_value_price` (reject <50 BHD for phone/laptop/console — kills accessory leaks like an 11.9 Galaxy "case") + a wrong-SKU converted-deviation guard (drop a cited price >2.5x/<0.4x off the parked `converted_fallback` ref — kills a 537 S24-Ultra phantom; NO ref → keep, preserving organic-beats-estimate). A blunt "require url" first attempt broke 5 tests (the contract allows no-url local_bhd) → reverted. **Price-cache PROVEN + warmer BUILT:** off-clock scrape (`PRICE_RACE_TIMEOUT=60`) → shared cache → live 15s-clock serves genuine instantly. `scripts/cron_warm_price_cache.py` (flag `ENABLE_PRICE_CACHE_WARMER` OFF, fail-closed; gold-set catalog; `WARMER_SUBSET` smoke20|full + `MAX_QUERIES_PER_RUN` + Redis rotation cursor `warmer:cursor`; 5/5 tests). **THE 70% TARGET:** engineering blocker (latency wall) SOLVED; reaching/sustaining it = Serper BUDGET (free 2,500/account is finite + shared with live traffic; continuous full-catalog warming needs PAID Serper). Activation = register Railway cron + flip flag (Ahmed). **Eval caveat:** `eval_runner` uses `nocache=true` (measures COLD scraping), so it will NOT reflect the warmer's cached genuine-share — a cache-reading eval variant is needed to measure the 70%. **Deploy-ops:** railway CLI works (`kinghaleem999@`, project `empowering-enthusiasm`/`web`/`production`) even when railway MCP is logged out; deploy commit at `environments.edges[].node.serviceInstances.edges[].node.latestDeployment.meta.commitHash`. PoC/verify scripts in `.qa-bias-rerun/`. Full S3 ledger: SESSION_BUNDLES Session 62; handoff: `memory/project_bundle_b_s3_state.md`. **Post-ship (2026-06-15, main `1e5a788`):** warmer PROVEN (genuine-share 17%→33% on the 1/category cache-read probe; remaining estimates are STRUCTURAL — no BH source for luxury fragrance/haircare/gadgets). Usage fixes: `6a80912` (backend `get_usage_status` display honors the lifetime-free path) + `1e5a788` (frontend `useComparisonCounter` hydrates from the backend instead of a local-only AsyncStorage counter that never reset — NEEDS an EAS push to reach phones). **KNOWN BUG: a fragrance comparison didn't load in-app** (reproduce + fix). Comprehensive next-session handoff + ready-to-paste prompt: `memory/project_bundle_b_s3_render_discovery_followup.md`. Usage-gate lesson: `memory/feedback_frontend_local_only_gate_no_backend_sync.md`.

**Active runtime (genuine-BH latency+warmer + S3.1, 2026-06-15, main `bce638f`):** RESOLVED the prior callout's "fragrance couldn't load" KNOWN BUG — it was a **30s `STREAM_HARD_CAP` timeout mis-surfaced as HTTP 400** (NOT matching/coverage/Serper; genuine prices were reachable). 5-Opus worktree team built it; dispatcher took over gate+merge+deploy when the team idled, then (after Ahmed flagged **89% of the weekly usage limit**) stood the re-spawned follow-on team down and finished the high-value items SOLO (~10× cheaper than a fleet). **SHIPPED:** (WS1) fail-fast graceful PARTIAL on hard-cap (`success:true`+`metadata.partial:true`); **`TIMEOUT`→HTTP 503** not 400 via `_surface_comparison_failure` in `text_routes.py` (structured detail preserves the code; contract `docs/contracts/d2-error-contract.md`); SSE keeps `STREAM_TIMEOUT`. (WS2) latency trim — free Shopify/Algolia direct-fetch overlap + `FAN_OUT_BUDGET_SECONDS` env (live 12s / warmer 35s); in-process trace 37.5s→22.5s, genuine BHD intact. (WS3) BH-locale/PDP discovery filter in `source_router.py` (drop noon bare-region + listing/category URLs; **OFFICIAL tier EXEMPT** from the PDP-drop — never drop apple.com/shop to a marketplace); Firecrawl/Scrapedo timeouts env-driven; **CF-walled luxury (sephora.bh/bolo.bh/boutiqaat) = STRUCTURAL gap** (`docs/investigations/2026-06-15-render-wall-bh-retailers.md`). (WS4) `data/warmer_catalog.json` 16 structural pairs, SEPARATE from gold. (WS5) variant/concentration precision + flagship-100ml convergence. (WS6/7) graceful FE timeout/partial UI + honest converted labels; EAS prep of `1e5a788`. **S3.1 follow-on:** B1 fragrance size-plausibility guard (`is_implausible_low_fragrance_price`, size-aware via WS5, designer-gated — kills cold-partial sample prices like Ombré 19.93 BHD); **eval genuine-share PARITY fix** — eval `GENUINE_BH_SOURCE_METHODS` was missing `page_scrape_jsonld`/`firecrawl_brand_domain`/`official_brand` vs backend `_GENUINE_BH_SOURCE_METHODS` so genuine prices dropped out of the KPI numerator → **true prod genuine-share is HIGHER than the quoted ~18.9%**; now pinned by `tests/test_eval_genuine_methods_parity.py`; **sonyworld.bh** genuine BHD source added (official Sony, Shopify); B3 test-infra hygiene (conftest event-loop + rate-limiter autouse fixtures — the in-suite-only failures were a detached-event-loop teardown under pytest-asyncio strict, NOT a SUPABASE_URL delenv). **GOTCHAS (durable):** Sentry's Starlette/FastAPI integration captures EVERY 5xx by default → the 400→503 change flooded Sentry; exclude deliberate transient 503 (TIMEOUT/FEATURE_DISABLED) via `failed_request_status_codes` + a `before_send` drop (`sentry_service.py`, `2c27c5e`). Eval baseline `4aee8e88` is `subset:"full"` (200) — the documented `smoke20` regression gate compares MISMATCHED subsets; a proper smoke20 `--persist` baseline is still needed. No-prod-write belongs in the harness scripts (blank UPSTASH/SUPABASE in-script AFTER imports — `load_dotenv(override=True)` defeats file-level blanking), NOT by blanking creds the MOCKED unit suite needs (`memory/feedback_no_prod_write_belongs_in_harness.md`). **PENDING Ahmed (the genuine-share win, zero Claude tokens):** register the Railway warmer cron + flip `ENABLE_PRICE_CACHE_WARMER` + `cd SmartCompareApp && eas update --branch preview` (`1e5a788`). **DEFERRED next fresh-budget session:** B2 proper smoke20 `--persist` baseline + A4 cache-reading eval variant (both need eval RUNS; A4 measures warmed share only post-activation). Handoff: `memory/project_genuine_bh_latency_warmer_bundle.md`; follow-on plan `docs/plans/2026-06-15-genuine-share-push-polish.md`. **ON-DEVICE TEST 2026-06-15 — the Tom Ford comparison LOADS (crash fixed ✓) but the RESULT quality is broken (6 bugs = "Thrust C", HIGH priority next session):** (C1) sample-grade prices — Ombré **25.19 BHD** vs genuine ~80; B1's designer floor of 25 BHD is TOO LOW → recalibrate to ≥~50-60/100ml + check source_method; (C2) inconsistent size basis (no-size vs "30 ML" — the WS5-deferred cross-product consistency); (C3) **"Build" dimension on a fragrance** — `CATEGORY_DIMENSIONS` must use scent dims (longevity/sillage/projection), not Build/Feature; (C4) product_1 specs all blank (—); (C5) raw `[2][3]` citation markers (`_clean_review_citations` not firing); (C6) "1.0 stars higher" vs an "N/A" rating. **Lesson: "loads without crashing" ≠ "correct" — verify RESULT content on-device, not just HTTP 200** (the timeout fix shipped clean but masked pre-existing fragrance content bugs that only surface once the page renders).

**Active runtime (fragrance-quality + personalization + results-redesign + CATEGORY-FAIRNESS standard, 2026-06-16/17, main `b7af94d`):** RESOLVED the prior callout's Thrust C (ALL 6 fragrance content bugs) + shipped the results-screen 1:1 redesign + a category-wide fairness standard. Solo-dispatcher + SEQUENTIAL subagents (no fleet — weekly budget was 91%+; sequential because parallel subagents race the git index + the FE needs the main tree's `node_modules`). **KEYSTONE (`115244b`):** `canonicalize_category()` (`extraction_service.py`, set = `frozenset(CATEGORY_SPEC_SCHEMAS.keys())` so it can't drift) applied at parse time + defensive guards at the 4 lowercase-keyed lookups (`scoring_service.compute_scores`/`build_dimensions_v2`, `extract_specs`, critical-field cascade). The LLM's `"Fragrances"` (capital F) was silently falling to `"other"` → C3 ("Build" dim not scent), C4 (generic spec schema → blank 2nd-product specs), AND degraded fragrance personalization (priorities reweighted generic dims) — ONE fix cleared all three. **CONTENT C1-C6 (`115244b`):** C5 `clean_review_citations` now strips bare `[N]` (not only `[snippet_N]`); C6 `_dim_reviews` treats a `rating_derived` synthetic rating as missing (no "stars higher" vs a displayed N/A). **PRICE-PENDING (C1):** `is_price_showable`/`make_pending_price` → `{amount:None, unavailable:True, reason: pending_genuine|size_mismatch|unit_mismatch}`; estimated/sample/non-genuine/unit-mismatched → pending (FE renders "Pricing lands in an upcoming update."); genuine-BH ∪ `converted_usd` still show. **COHORT proof line was HARD-DEAD** — FE read `result.cohort_summary` the backend NEVER emitted → now emitted `{peer_count, governorate}` from a REAL survey N (`cohort_priors.json` `cohort_match.n`), gated by `was_cohort_block_active`. **REVIEWS:** `build_retailer_quotes_from_reviews` (review_service) emits ≤3 per-source quotes from REAL organic snippets (domain + verbatim text) via the `[snippet_N]` map — NO AI-fabricated ratings (rating only when real). **FE 1:1 REDESIGN** (matches the design-handoff `ResultsScreen.jsx`; EAS `8b7d29c7` on `preview`): split dimension bars + "A · B" legend, dot confidence pills (high=emerald/med=amber), ★ uppercase TOP MATCH, value·CENTERED-label·value specs (REMOVED Show-differences toggle + Highlights block), per-source review quotes, ProsConsCol pros/cons, Accurate/Detailed/Fast feedback chips. **CATEGORY-FAIRNESS STANDARD (`780d243`+`b332043`+`b7af94d`):** central `CATEGORY_FAIRNESS` config (price_service) = per-category comparable unit both products must match for a fair compare — electronics→storage GB, fragrances→ml, supplements→count, grocery/makeup/skincare/haircare→weight/volume; fashion/other→None. `target_pair_value`→plan `{mode: honor_each|target|none, target, per_product}`: (1) BOTH values in user query→**honor each** (show both, verdict flags the diff, NO pend); (2) one mentioned OR one product fixed-size→target it + reconcile the other; (3) neither→common standard = largest value BOTH retained-candidate pools share (both priced same basis); (4) tolerance (discrete 5% / continuous 15%) → similar sizes pass through. `reconcile_pair_fairness` re-selects genuine prices from RETAINED `self._price_candidates` (no new API calls); fragrance ml is the original case (delegates to the byte-preserved `reconcile_pair_sizes`). Real fragrance size now captured from JSON-LD name/og:title/page-`<title>` (`extract_size_ml_any`, ml + fl-oz snapped to standard bottles) → fairness engages on TRUE sizes; flagship-100ml is last-resort-only. + LIKE-FOR-LIKE rule in `COMPARISON_SYSTEM` prompt (never "cheaper" across a different storage/size/count). **LIVE-VERIFIED (fresh prod `nocache`):** "iPhone 15 256GB vs Galaxy S24 128GB" → honors both (no pend); fragrance scent profile (family + top/heart/base notes + longevity/sillage/concentration) confirmed populated. **DURABLE GOTCHAS:** (a) verify FE against the ACTUAL design-handoff reference file (`ResultsScreen.jsx` inside the gzipped bundle), NOT a screenshot glance — I twice wrongly asserted "FE matches design" while the accordion BODIES diverged; (b) **stale Redis cache masks a deploy** — re-running the SAME query serves the pre-deploy cached result (prices 24h / specs+reviews 7d), so a "still broken" screenshot is usually stale cache not a failed deploy → verify with a FRESH/different pair or a `?nocache=true` prod curl; (c) the **Bash-tool cwd PERSISTS** into `SmartCompareApp` after a `cd` → repo-root-relative `tests/` paths miss + `python open()` defaults to cp1252 on prod JSON (use `encoding='utf-8'`); (d) design-handoff URL `api.anthropic.com/v1/design/h/<id>` is a >10MB gzipped tar (WebFetch fails on size) → `curl -o` then `tar -tzf`; reference UI kit at `.../ui_kits/mobile/ResultsScreen.jsx`; (e) `eas update` via PowerShell + absolute `Set-Location` (bash cwd issue); `eas update` is NOT Ahmed-only-interactive (only `eas login`/`eas build` are); (f) transient subagent API 500s recur — retry (the 3rd attempt succeeded); (g) Railway MCP + CLI both `invalid_grant` this session — verify deploys via a prod API probe, not Railway tooling. **PENDING / WHAT'S LEFT:** on-device verify the redesign + fairness (relaunch app TWICE for EAS two-launch + run FRESH comparisons); residual fragrance size blind spot (size only in a variant-widget/image → flagship default); still-DEFERRED B2 smoke20 `--persist` baseline + A4 cache-reading eval variant; warmer cron activation (`ENABLE_PRICE_CACHE_WARMER`, Ahmed). Handoff: `memory/project_fragrance_quality_personalization_redesign.md`; design `docs/plans/2026-06-16-fragrance-quality-personalization-results-redesign-design.md`.

**Active runtime (faithful-results + bundle-next polish, 2026-06-17, main `5219cac`):** 4-Opus team (Backend/Frontend/Test/QA; dispatcher = gate-not-do, see `memory/feedback_dispatcher_gate_not_do.md`). **MAIN bundle** (backend `3d870c8` + cleanup `42d17e4`, **EAS preview group `71044ff7`**): free-tier price cache (genuine-BH **7d** TTL / negative-cache **30d** / converted-estimated 24h, **cache-first-before-scrape gate**, hit-rate metadata on `response.metadata` + `/admin/costs`); wrong-cheap price guards (F1.2 — designer-fragrance/haircare sub-floor sample-leaks now PEND, not shown; e.g. Tobacco Vanille 28.2 BHD → pending); `category_profile` payload ×9 (canonicalized, symmetric, no-fab) + generic FE `CategoryProfile` (renders any `fields[]`, hides empty, 68 EN+AR `results.spec.<key>`); verdict fixes (runner-up `key_tradeoff` CAPTION un-suppressed — **that caption is the ONLY runner-up FE surface; NOTHING renders `overview.tradeoffs[]`** (only a type def) — F4.2 empty-tradeoffs fallback, F4.3 personalization weaving, F4.4 partial-path deterministic verdict); `review_praise` paraphrase (synthesized, NO `[N]`/domains, copy-policy-clean via the shared `SmartCompareApp/src/i18n/.copy-policy.json` fence, real-rating-only); fairness audit; FE prune-to-design (HeroRings card removed, lean chrome). **BUNDLE-NEXT** (backend `5999799`, **backend-only, NO EAS**): #15 per-category extraction-depth guidance in `_build_specs_prompt` (all 9 cats, in the DYNAMIC prompt section → OpenAI cache intact; prod makeup 2→6 / skincare 2→3 fields, no-fab) + #16 longevity scorer reconcile in `scoring_service` (bounded ordering swap ONLY when both products have a clear ≥1h hours-signal AND computed scores disagree; electronics-unaffected); #14 tradeoff-card DROPPED-MOOT. **Eval anchors (`eval_runs`, project qulajmyxdbdkchvecmvc):** smoke20 baseline `7a5fc55b` (pre-bundle, winner 0.40, cold 0% = price-pend-by-design) → **NEW anchor `54b603e8`** (post-#16, winner **0.50 (+10pp)**, specs 0.9875 / factual 1.0 HELD; use `--baseline-run-id 54b603e8` for future smoke20 gates); canonical free-unit baseline = **48** (+ a 3-test NETWORK_FLAKY_EXCLUDE). **DURABLE GOTCHAS:** (a) `eval_runner` is a PROD-HTTP harness → **the eval is POST-deploy** (can't measure un-deployed branch code; a pre-deploy eval measures prod-without-the-change = meaningless); (b) **worktrees DON'T inherit gitignored `.env`** (sibling-worktree `load_dotenv` walks UP, never reaches main's → partial-cred unit runs corrupt the baseline since services need creds to construct mocked clients; copy `.env` into each pytest-running worktree); (c) **Serper budget counter IS key-scoped** `budget:serper:<key8>:lifetime` (prior "not key-scoped" note was stale) — but prove headroom by RUNTIME evidence (a clean 20-query eval, 0 errors + specs held) not a local-Upstash read; (d) pre-authored tests importing UNMERGED symbols must be collection-safe (`importorskip`) else they abort whole-suite COLLECTION. **PENDING Ahmed (zero Claude tokens):** warmer cron + `ENABLE_PRICE_CACHE_WARMER` = the genuine-price lever (cold prices PEND by design until warmed; #16's full longevity effect also lands post-warmer); on-device walk (`.qa-discovery/AHMED_ONDEVICE_CHECKLIST.md`); 2 reversible judgment calls (CategoryProfile placement standalone-vs-accordion / fashion short-labels Closure-Care-Collection); optional richer structured "where the runner-up wins" CARD (flagged, not built). Handoff: `memory/project_faithful_results_shipped.md`.

**⚠️ CURRENT PROD STATE (2026-06-18 — READ FIRST):** walk-fixes SHIPPED (backend `2cb4439`, EAS group `3efa9d81`) from Ahmed's on-device walk — #20 FE results-organization (suppress `limited_data` dims + drop the price-derived 'value' dim on pricePending + single compact A·B bar legend + text-overflow fix) + #21 BE free KG/organic image tier (`image_service` Tier 1.5b `extract_image_from_search`, reads an image from the already-fetched unified Serper payload — $0, no Serper-Images budget, price-scrape-independent, strictly-additive). **🔑 THE SERPER KEY (`696e4e57…`) IS DEPLETED** (raw `/search` → 400 "Not enough credits") → **prod is DEGRADED** (no genuine specs/prices/images on a fresh compare) until rotated. **ROTATION = Ahmed's action** — new serper.dev key OR (recommended) PAID Serper (ends the recurring free ~2,500-one-time depletion + unlocks the warmer). Until rotation #21's fix is deployed but UNVERIFIABLE (every image tier needs the search). **Two new durable gotchas:** (1) **stale-cache-masks-the-fix** — re-running the SAME pair serves the 7d-specs/24h-price cache (a pre-fix payload), so a "still broken" screenshot is usually stale cache NOT a failed deploy → re-test a FRESH/different pair or `?nocache=true` (the walk's "missing specs/wrong dims/no scent profile" was exactly this; a fresh pull confirmed the fix works). (2) **Serper headroom is POINT-IN-TIME, not sustained** — a clean N-query eval proves credits-at-that-moment, NOT headroom for the subsequent cumulative burn; near the cap heed the `budget:serper:<key8>:lifetime` COUNTER + track cumulative session burn (this session depleted a near-cap key by over-trusting one clean eval + dismissing the canary). **What's left:** Serper rotation (THE blocker) → Backend's #21 image curl + Ahmed's FRESH-pair re-test + the 2 reversible judgment calls (CategoryProfile placement / fashion labels); warmer needs paid Serper; OFFERED-not-built = a deploy-version cache-bump (kills the stale-cache trap) + a richer "runner-up wins" tradeoffs CARD; the 4-Opus `faithful-results` team is still on STANDBY. Full handoff: `memory/project_faithful_results_shipped.md`.

**Workflows:** worktree-team (`git worktree add -b feature/<name> ../smartcompare-<name> main` → 4-Opus TeamCreate, **`mode: "bypassPermissions"` REQUIRED** else sandbox blocks Bash → cross-QA → merge `--no-ff`); subagent-driven (`Agent(isolation: "worktree")` x2 parallel for backend-only ~6-8 tasks, validated Session 50); plan-writing-via-4-Opus uses skeleton with `<!-- OWNED BY: name -->` anchors so 4 agents Edit one doc concurrently. **Arabic-as-default DROPPED** (Session 44).

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

## Environment Variables (Railway)
**Required:** `OPENAI_API_KEY`, `SERPER_API_KEY`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_KEY`, `UPSTASH_REDIS_URL`, `UPSTASH_REDIS_TOKEN`, `ADMIN_API_KEY`
**Optional:** `SENTRY_DSN` (backend + mobile share org `qaren-rr`, different DSNs), `LOG_LEVEL` (INFO), `CORS_ORIGINS`, `STREAM_HARD_CAP_SECONDS` (30.0 since 2026-06-09 B0-C Item 3 — was 25.0; outermost `asyncio.wait_for` on streaming + non-streaming `compare_from_text` per L2.7), `SCRAPING_MODE` (`hard`/`soft` — `soft` skips Firecrawl+Scrape.do for non-luxury URLs), `DEBUG_STAGE_TIMINGS` (true since Sprint A — opt-in `metadata.stage_timings_ms`)
**Price Scraping:** `FIRECRAWL_API_KEY`, `SCRAPEDO_API_TOKEN`, `ENABLE_FIRECRAWL` (true), `ENABLE_SCRAPEDO` (true), `ENABLE_PAGE_SCRAPE` (curl_cffi).
**Version Check:** `APP_MIN_VERSION`, `APP_LATEST_VERSION`, `APP_FORCE_UPDATE`.
**Feature Flags:** `ENABLE_COHORT_PERSONALIZATION` (ON since 2026-05-05), `ENABLE_REFERRAL_SYSTEM`, `ENABLE_HYBRID_MODEL_ROUTING` (**phantom** — env value cosmetic, zero code refs; see `docs/BUNDLE_C_PROD_STATE.md`), `ENABLE_REENGAGEMENT_PUSHES` (gates `evaluate_user` + cron, fail-CLOSED), `REENGAGEMENT_CANARY_PERCENT` (100; djb2 via `feature_bucket.hash_bucket`). All flags default OFF in code; flip in Railway during canary. `REAL_ACTION_MIN_SECONDS` (5).

Operational rollout sequence + canary monitoring guidance: see `docs/CONTEXT_SESSION_LOG.md`.

Railway MCP server is configured at project root (`.mcp.json`, stdio via `railway mcp`). Query env vars / deploys / logs from inside Claude Code via `mcp__railway__*` tools after a first-time `railway login` in a real terminal (interactive auth; cached in `%USERPROFILE%\.railway`).

## Tests

```bash
# Free unit tests (~$0)
python -m pytest tests/ -v -m "not (live_unit or live_db or integration)" --ignore=tests/test_integration.py

# Live unit tests (iHerb, Serper, GPT — ~$0.03)
python -m pytest tests/ -v -m "not (live_db or integration)"

# Integration tests (live Railway — ~$0.06)
python -m pytest tests/test_integration.py -v -m integration

# Full suite
python -m pytest tests/ -v --timeout=180
```

- `python -m py_compile <file>` for syntax checks; `npx tsc --noEmit` for frontend types.
- `conftest.py` auto-loads `.env` via python-dotenv.
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
- **Scrape.do timing out** on GCC luxury retailers (Ounass, Bloomingdales). Firecrawl is primary; Scrape.do is Tier 1.5d fallback only. Investigation `docs/investigations/2026-05-16-scrapedo-timeout-analysis.md` — recommendation: **accept current behavior** (graceful Tier 2 fallback).
- **Google Sign-In** — currently failing on EAS preview (Session 54). Apple + email/password GREEN. Awaiting Ahmed's `[GOOGLE-DIAG]` Xcode log + Railway `SOCIAL_LOGIN_TRACE` line to disambiguate iosClientId / Bundle-ID / token-shape failure mode. Backend diagnostic instrumentation kept in `auth_service.py` until resolved.

## Detailed Context
Index: `docs/CLAUDE_CODE_CONTEXT.md`. Key files: `CONTEXT_ARCHITECTURE.md`, `CONTEXT_SESSION_LOG.md`, `CONTEXT_REFERENCE.md`.
