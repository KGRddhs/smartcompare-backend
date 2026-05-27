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
8. **Multi-agent stalls: escalate after 30 min.** 4-Opus teams stop processing inbox while staying "available". If silent >30 min with uncommitted state despite `SendMessage` nudges → dispatcher takeover. Pattern surfaced Session 47.

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

Applied 010–026 (all via MCP since 013). Files in `migrations/*.sql`; rollbacks in `migrations/rollback/*.sql`. Load-bearing: **020** `comparisons.schema_version` (v1=legacy/hidden, v2=renderable; default 2 — gates history list/get filter). **021** `users.device_fingerprint_hash` + partial idx (anti-farming; matches `^[a-f0-9]{64}$`). **023** (Bundle B/C/D) drops `weekly_invites_used`, adds `lifetime_invites_consumed INT` — referral cap **3 LIFETIME per device**. **024** adds `'top_tier'` to `users.preferences.budget` CHECK enum (5-tier; backwards-compat).

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

**Navigation:** Bottom tabs (Home/History/Profile) via `@react-navigation/bottom-tabs`. Results as modal. Auth stack (Login/Register/ForgotPassword). Splash → Onboarding → Auth → Main in `App.tsx`. Paywall registered as `Stack.Screen` with `presentation: 'transparentModal'` (audit 2026-05-22 — was Modal-only; `navigation.navigate('Paywall')` was silent no-op). **RN-Navigation v7 caveat (Bundle E B4 hotfix 2026-05-26):** conditional `<Stack.Screen>` rendering with the **same `name`** in different branches (e.g. `needsPreferences ? <Onboarding-full> : <Onboarding-edit>`) makes RN treat them as the same route — navigator keeps old route active when the conditional flips and never swaps. Use **distinct names per branch** (`Onboarding` + `OnboardingEdit`). Caught after Step 17 Finish stuck-on-screen bug.

**Design system:** `src/theme/index.ts` (emerald #10B981, Geist+Cairo). Components: Button, Card, Chip, SkeletonLoader, ProgressBar, IconButton, ComparisonCounter. i18n: `src/i18n/` (180+ keys EN/AR).

**Services:**
- `api.ts` — Axios → Railway (120s timeout). SSE via `streamComparison()` (fetch+ReadableStream, fallback to non-streaming). JPEG transcoding pre-upload.
- `authService.ts` — Supabase + social. **`verifyAuth()` returns `User | null`** (NOT boolean). Tokens in `expo-secure-store` (NOT AsyncStorage). OAuth nonces via `expo-crypto`. All `console.log` wrapped in `__DEV__`.
- `certificatePinning.ts` — Railway SSL pinning (LE intermediate SPKI). Init once from `api.ts`. EAS dev build only (no-op in Expo Go). Rotation in `docs/SECURITY_HARDENING_CONTEXT.md`.
- `sentry.ts` — `@sentry/react-native@8.11.1`. Mirrors backend `before_send` scrub (JWT/OpenAI/Firecrawl/Bearer/headers). DSN → `qaren-rr/react-native`. Sourcemap upload deferred (`SENTRY_AUTH_TOKEN` + plugin config).

### External APIs (use wisely — every call costs money)
- **OpenAI GPT-4o-mini** — Spec/price/review extraction, product identification. Combine calls.
- **Serper** — Google Search + Shopping API ($0.001/call). Don't search for what you already have. ~2,500 credits remaining (rotated 2026-02-28); cached = free, only `nocache=true` burns credits. Rotate via new free account at serper.dev.
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
- **17-step onboarding** (`src/screens/onboarding/`): OnboardingFlow + 17 steps. Cohort-key strings **exact-case** ('Capital', '25-34', 'Male'/'Female') matching `cohort_priors.json`. Step 14 theatrical loading 3.2s min. Step 16 NO skip — forced sign-in.
- **Hero illustrations** (SVG + Reanimated, **ZERO Lottie**): PhoneMockup, CohortBarChart, ConcentricMotif, LoadingRings, RevealBurst. Stage-gated SSE on StreamingProductCard (init→title→specs→prices→reviews→verdict). StageChecklist haptic ONLY on transition INTO done.
- **Results redesign:** section titles "Why we picked this" / "Where the runner-up wins" / "What's next?". CohortBadge inline below verdict.
- **Bonus expiry (Migration 018):** 3-day default. `cron_expire_bonuses.py` gated by `ENABLE_BONUS_EXPIRY_PUSHES`, 1000-row LIMIT, 24h-before push. **Entitlement computed from `get_user_active_bonus_count()` live rows, NEVER from stale INT counter** (counter is analytics/display only). Bundle B/C/D extends to 7d for new redemptions.
- **Attribution endpoint (Migration 019):** `POST /auth/attribution` (auth, 30/min). Pydantic Literal['friend','instagram','tiktok','app_store','google','other'] + DB CHECK mirror.
- **Min-display floor 1.2s** on Home→Results (cached responses still loading 1.2s so brand moment lands). Tracked via `loadingStartedAtRef` + `navigateToResultsWithFloor`.
- **Onboarding analytics:** `onboarding_started` on mount; `onboarding_step_completed` BEFORE setStep (payload reflects FINISHED step); `onboarding_completed` on Step 17.
- **Copy contract:** ZERO scary copy. Forbidden EN: `couldn't`, `try again`, `Failed to`. Forbidden AR: `تعذر`, `فشل`. Approved vocab in design doc §6.

### Smart Decision Referrals
See skill: `qaren-referrals` (auto-loads when `/api/v1/referrals/*` routes, invite codes (QR-XXXXXX), Loop 1/Loop 2, redemption chain, or `referral_invites`/`referral_redemptions` tables are mentioned). Critical inline: gated by `ENABLE_REFERRAL_SYSTEM` (default OFF in code, flipped in Railway). Bundle B/C/D moved cap to **3 LIFETIME per device** with fail-OPEN on DB error. Code redemption is **register-only** — `RegisterRequest.invite_code` accepts `^QR-[A-HJ-NP-Z2-9]{6}$`. Re-engagement gated by `ENABLE_REENGAGEMENT_PUSHES`.

### Bundle history (sessions 44-54)
Full bundle narrative (Session 44 onwards, including Bundle B/C/D ships + hot-fix sweeps + Path A) lives in `docs/SESSION_BUNDLES.md`. CLAUDE.md keeps only the load-bearing prod-state callouts below.

**[STATUS 2026-05-22 — Bundle C in prod]** `ENABLE_BUNDLE_C_SCORING=false` in Railway; code default also `false`. Flag gates ONE site (`scoring_service.py:944`) — `None vs MISSING_SCORE=50` swap. In prod, missing signals get `MISSING_SCORE=50`, so A.4.9 silent dim omission never fires. The other ~95% of Bundle C (A.3.x/A.4.5/A.4.7/A.5.x/A.6.x/A.7.x/A.9.x/A.10.x, frontend §B) is unconditional and live. Canonical: **`docs/BUNDLE_C_PROD_STATE.md`**. Discipline before trusting "shipped/always-on" claims: `memory/feedback_docs_vs_railway_env_drift.md`.

**Active runtime:** Bundle D TestFlight Readiness merged 2026-05-25 (`6ee3aa5`) + Path A R1/R2 (`c0678d3`+`4aa9cff`). `STREAM_HARD_CAP_SECONDS=25.0`. `SCRAPING_MODE=soft` URL gate wired. Cold-cache wall: fragrances 15.4s / electronics 14.7s / supplements 10.4s; iPhone+Galaxy worst case 24.8s.

**[STATUS 2026-05-26 — Bundle E day-1 partial, S1 still NOT done]** S0 SEALED (5 hero SVGs + 12 primitives + motion tokens + RTL slide wrapper + `deriveTone` util; Q-S0 GREEN). Backend lane DONE (B3 normalize, `/home/trending` reshape `{tag,a,b,count}`, `/home/smart-pick` extend `{category,updated_at,winner_sub,runner_up_sub,verdict_short}`, endpoint shape contract test, cohort load smoke). **B4 RESOLVED via Supabase dashboard toggle** (see Known Bugs section). S1 8 screens composed + 5 follow-ups shipped after Ahmed device walkthrough surfaced 5 RED + 2 bugs — but the rework was PARTIAL: B1 names ✅, D1 HistoryStats ✅, B2 ScanBody spec-correct but UX-confusing (dashed buttons read as text inputs), **D2 ProfileScreen STRUCTURALLY WRONG** (frontend patched eyebrows onto Bundle D component instead of rewriting top-down per JSX — header/avatar at bottom not top, missing RecentDecisions marquee + MonthStrip, broken Priorities), D3 winner-card unverified, LoadingScreen variants NOT integrated. **Day-2 first task: F-S1.5c ProfileScreen FULL REWRITE top-down against `ProfileScreen.jsx` — NOT patch.** Then verify D3 + S2 KICKOFF (12 onboarding steps + LoadingScreen variants + RTL slides). Branch `feature/bundle-e-visual-fidelity` (worktree `../smartcompare-bundle-e-vf`); 25 commits ahead of main; latest `eas update` `019e6814-...` preview. Handoff: **`docs/plans/bundle-e-tomorrow-handoff.md`**. **Phrasing lesson for tomorrow's dispatcher**: use "REWRITE `<Screen>.tsx` top-down against `<Screen>.jsx`" not "compose" — see `memory/feedback_compose_vs_rewrite_phrasing.md`.

**Workflows:** worktree-team (`git worktree add -b feature/<name> ../smartcompare-<name> main` → 4-Opus TeamCreate, **`mode: "bypassPermissions"` REQUIRED** else sandbox blocks Bash → cross-QA → merge `--no-ff`); subagent-driven (`Agent(isolation: "worktree")` x2 parallel for backend-only ~6-8 tasks, validated Session 50); plan-writing-via-4-Opus uses skeleton with `<!-- OWNED BY: name -->` anchors so 4 agents Edit one doc concurrently. **Arabic-as-default DROPPED** (Session 44).

### Audit conventions (2026-05-22)
- **`_fire_and_forget(coro, label)`** in `structured_comparison_service.py` — use for new fire-and-forget tasks; adds done-callback that logs WARNING on exception. Plain `asyncio.create_task()` swallows exceptions and drops audit/personalization writes.
- **`INSUFFICIENT_DATA` error code** — `compare_from_text` + streaming return early when both products' Phase 1 specs+price are `None`. Prevents fake product_0 winner from all-MISSING_SCORE tie-break. Frontend i18n-substitutes the user-facing message.
- **`WINNER_INDEX_MISMATCH` WARNING log** in `response_builder.py` — fires when GPT-emitted `comparison["winner_index"]` disagrees with deterministic scoring. Deterministic wins; log audits frequency only.

### EAS Update infrastructure
See skill: `qaren-eas-deploy` (auto-loads when `eas update`, `eas build`, channel names, `runtimeVersion.policy`, or `expo.version` bumps are mentioned). Quick recall: OTA via `cd SmartCompareApp && eas update --branch <channel> --message "..."` — free, lands on next app open. Rebuild required for native module / app.json plugin changes. `appVersionSource: "remote"`. Interactive Expo commands (`eas login`, `eas build`) need a real terminal — Ahmed runs these directly.

### Luxury brand detection
`_is_luxury_brand()` + `COUNTERFEIT_KEYWORDS` filter across ALL categories. Tier 1.5 cascade: official brand → authorized retailers → GCC retailers (9 domains).

### Review + spec quality
Reviews: `_clean_review_content()` strips garbage (min 8 words), fixes sentiment misclassification, then `_clean_review_citations()` replaces `[snippet_N]` with domain attributions. Specs: GPT omits irrelevant fields (not "N/A"). Frontend filters nulls. Scoring applies `CATEGORY_MIN_COVERAGE` penalty.

## Environment Variables (Railway)
**Required:** `OPENAI_API_KEY`, `SERPER_API_KEY`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_KEY`, `UPSTASH_REDIS_URL`, `UPSTASH_REDIS_TOKEN`, `ADMIN_API_KEY`
**Optional:** `SENTRY_DSN` (backend + mobile share org `qaren-rr`, different DSNs), `LOG_LEVEL` (INFO), `CORS_ORIGINS`, `STREAM_HARD_CAP_SECONDS` (25.0 — outermost `asyncio.wait_for` on streaming), `SCRAPING_MODE` (`hard`/`soft` — `soft` skips Firecrawl+Scrape.do for non-luxury URLs), `DEBUG_STAGE_TIMINGS` (false — opt-in `metadata.stage_timings_ms`; zero prod overhead when off)
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
- **Google Sign-In** RESOLVED 2026-05-26 (Bundle E day-1). Fix: Supabase Dashboard → Auth → Providers → Google → enable **"Skip nonce checks"**. `@react-native-google-signin@16.1.2` iOS SDK auto-embeds a hashed nonce in id_tokens but doesn't expose the raw value to JS, so Supabase's `SHA-256(raw) === claim` parity check is impossible to satisfy from FE. Replay protection still holds via RS256 signature + aud check + short TTL. **Toggle is NOT in code — re-enable on Supabase project migration.** Also shipped: nav hotfix `2e1ceb7` (renamed duplicate post-auth `Onboarding` → `OnboardingEdit` to fix RN-Navigation v7 stuck-on-Step-17 bug). See `memory/project_supabase_google_skip_nonce.md`.

## Detailed Context
Index: `docs/CLAUDE_CODE_CONTEXT.md`. Key files: `CONTEXT_ARCHITECTURE.md`, `CONTEXT_SESSION_LOG.md`, `CONTEXT_REFERENCE.md`.
