# Agent C — Database & Infrastructure Forensics Report

**Model:** Sonnet | **Returned:** 2026-05-06
**Supabase project:** qulajmyxdbdkchvecmvc

---

# SECTION 1: Tables, Columns, and What Each Holds

## Table: `users`

Columns added across migrations 001 (implicit, pre-existing), 010_enable_rls.sql, 011_security_completion_freemium.sql, 013_demographics_cohort.sql, 014_referral_system.sql, 015_push_tokens.sql:

| Column | Type | Personal data? |
|---|---|---|
| id | UUID PK | Identifier — links to auth.users |
| email | TEXT | Yes — email address |
| display_name | TEXT | Yes — user's chosen name |
| preferences | JSONB | Yes — declared priorities, budget, lifestyle, brand attitude |
| behavior_profile | JSONB | Yes — behavioral inferences (decay-weighted comparison history) |
| preferences_completed | BOOLEAN | No |
| subscription_tier | TEXT | No (business metadata) |
| lifetime_comparisons_used | INT | No (usage counter) |
| demographics_profile | JSONB | Yes — age group, gender, governorate, language, country + cached cohort_match snapshot (migration 013:18-21) |
| demographics_dismissed_count | INT | No (UI state) |
| demographics_dismissed_at | TIMESTAMPTZ | No (UI state) |
| referral_code | TEXT UNIQUE | No |
| referral_bonus_comparisons_this_month | INT | No |
| referral_bonus_reset_at | TIMESTAMPTZ | No |
| expo_push_token | TEXT | Yes — device push notification token (migration 015:13) |
| notifications_enabled | BOOLEAN | No |
| last_comparison_at | TIMESTAMPTZ | No |

**RLS enabled:** Yes — `ALTER TABLE users ENABLE ROW LEVEL SECURITY;` (migration 010:8)

**RLS policies (verbatim):**
```sql
CREATE POLICY users_select ON users FOR SELECT
  USING (auth.uid() = id);
CREATE POLICY users_update ON users FOR UPDATE
  USING (auth.uid() = id);
CREATE POLICY users_insert ON users FOR INSERT
  WITH CHECK (auth.uid() = id);
```
(migration 010:17-22)

**Note on demographics_profile:** Migration 013:14-16 states: "users.demographics_profile lives on the same row that's already protected by the row-level security policies introduced in migration 010. No new policies needed."

---

## Table: `comparisons`

Columns from pre-existing base + migration 001 + add_share_token.sql + migration 017 (widened share_token):

| Column | Type | Personal data? |
|---|---|---|
| id | UUID PK | No |
| user_id | UUID FK → auth.users | Identifier |
| full_response | JSONB | Yes — complete comparison result including personalization data |
| query | TEXT | Yes — free-text product search query |
| input_type | TEXT | No |
| product_names | TEXT[] | No (product names, not user identity) |
| share_token | TEXT | No (generated token; migration 017:24 widened from VARCHAR(12) to TEXT) |
| created_at | TIMESTAMPTZ | No |

**RLS enabled:** Yes — `ALTER TABLE comparisons ENABLE ROW LEVEL SECURITY;` (migration 010:9)

**RLS policies (final state per migration 017:27-28 + migration 010:29-35):**

```sql
CREATE POLICY comparisons_select ON public.comparisons FOR SELECT
    USING ((auth.uid() = user_id) OR (share_token IS NOT NULL));

CREATE POLICY comparisons_insert ON comparisons FOR INSERT
  WITH CHECK (auth.uid() = user_id);
CREATE POLICY comparisons_delete ON comparisons FOR DELETE
  USING (auth.uid() = user_id);
CREATE POLICY comparisons_update ON comparisons FOR UPDATE
  USING (auth.uid() = user_id);
```

**Foreign key:** `user_id` references `auth.users`. Cascade delete via `delete_user_cascade` function (see Section 5).

---

## Table: `search_logs`

Created in migration 002:5-16.

| Column | Type | Personal data? |
|---|---|---|
| id | UUID PK | No |
| user_id | UUID → auth.users | Identifier (nullable — anonymous allowed) |
| query | TEXT NOT NULL | Yes — free-text search query |
| input_type | TEXT | No |
| products_found | JSONB | No (product names) |
| success | BOOLEAN | No |
| error_message | TEXT | No |
| cost | DECIMAL(10,6) | No |
| duration_ms | INTEGER | No |
| created_at | TIMESTAMPTZ | No |

**RLS enabled:** Yes — `ALTER TABLE search_logs ENABLE ROW LEVEL SECURITY;` (migration 010:10)

**RLS policies (verbatim):**
```sql
CREATE POLICY search_logs_insert ON search_logs FOR INSERT
  WITH CHECK (auth.uid() = user_id OR user_id IS NULL);
CREATE POLICY search_logs_select ON search_logs FOR SELECT
  USING (auth.uid() = user_id);
```
(migration 010:40-43)

---

## Table: `products`

Created in migration 002:37-46.

| Column | Type | Personal data? |
|---|---|---|
| id | UUID PK | No |
| canonical_name | TEXT UNIQUE NOT NULL | No |
| brand | TEXT | No |
| category | TEXT | No |
| variants | JSONB | No |
| created_at | TIMESTAMPTZ | No |
| updated_at | TIMESTAMPTZ | No |

**RLS enabled:** Not stated in any migration for this table. **Cannot determine from code** whether RLS was enabled outside the migration files.

**RLS policies:** None defined in any migration file.

---

## Table: `bahrain_approved_drugs`

Referenced in migration 010 only (not created there — pre-existing table).

**RLS enabled:** Cannot determine from migration files when it was enabled; migration 010 adds a policy to it, implying RLS was active. No explicit `ENABLE ROW LEVEL SECURITY` statement found for this table.

**RLS policies (verbatim):**
```sql
CREATE POLICY drugs_select ON bahrain_approved_drugs FOR SELECT
  USING (true);
```
(migration 010:64-65)

**Personal data:** No — contains 655 Bahrain-registered health product names.

---

## Table: `comparison_feedback`

Pre-existing (no CREATE TABLE in reviewed migrations).

| Column | Type | Personal data? |
|---|---|---|
| id | UUID PK | No |
| user_id | UUID (nullable) | Identifier |
| comparison_id | UUID | No |
| useful | BOOLEAN | No |
| created_at | TIMESTAMPTZ | No |

**RLS enabled:** Yes — `ALTER TABLE comparison_feedback ENABLE ROW LEVEL SECURITY;` (migration 010:11)

**RLS policies (verbatim):**
```sql
CREATE POLICY feedback_insert ON comparison_feedback FOR INSERT
  WITH CHECK (auth.uid() = user_id OR user_id IS NULL);
CREATE POLICY feedback_select ON comparison_feedback FOR SELECT
  USING (auth.uid() = user_id);
```
(migration 010:48-51)

---

## Table: `user_events`

Pre-existing (no CREATE TABLE in reviewed migrations).

| Column | Type | Personal data? |
|---|---|---|
| user_id | UUID (nullable) | Identifier |
| comparison_id | UUID | No |
| event_data | JSONB | Potentially — free-form event payload including `cohort_injected` flag |
| created_at | TIMESTAMPTZ | No |

**RLS enabled:** Yes — `ALTER TABLE user_events ENABLE ROW LEVEL SECURITY;` (migration 010:12)

**RLS policies (verbatim):**
```sql
CREATE POLICY events_insert ON user_events FOR INSERT
  WITH CHECK (auth.uid() = user_id OR user_id IS NULL);
CREATE POLICY events_select ON user_events FOR SELECT
  USING (auth.uid() = user_id);
```
(migration 010:56-59)

---

## Table: `user_usage`

Created in migration 011:8-16.

| Column | Type | Personal data? |
|---|---|---|
| id | UUID PK | No |
| user_id | UUID NOT NULL → users(id) ON DELETE CASCADE | Identifier |
| period | TEXT NOT NULL | No |
| comparison_count | INT | No |
| created_at | TIMESTAMPTZ | No |
| updated_at | TIMESTAMPTZ | No |

**RLS enabled:** Yes — `ALTER TABLE user_usage ENABLE ROW LEVEL SECURITY;` (migration 011:18)

**RLS policies (verbatim):**
```sql
CREATE POLICY usage_select ON user_usage FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY usage_insert ON user_usage FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY usage_update ON user_usage FOR UPDATE USING (auth.uid() = user_id);
```
(migration 011:19-21)

---

## Table: `admin_audit_log`

Created in migration 011:34-42.

| Column | Type | Personal data? |
|---|---|---|
| id | UUID PK | No |
| event_type | TEXT NOT NULL | No |
| user_id | UUID (nullable) | Identifier |
| ip_address | TEXT | Yes — IP address |
| endpoint | TEXT | No |
| details | JSONB | Potentially — free-form event context |
| created_at | TIMESTAMPTZ | No |

**RLS enabled:** Yes — `ALTER TABLE admin_audit_log ENABLE ROW LEVEL SECURITY;` (migration 011:44)

**RLS policies (verbatim):**
```sql
CREATE POLICY audit_insert ON admin_audit_log FOR INSERT WITH CHECK (true);
```
(migration 011:46) — No SELECT policy defined for ordinary roles. Comment: "Only service_role can read audit logs."

---

## Tables: `product_specs`, `product_prices`, `product_reviews`

Created in migration 012.

**product_specs** (migration 012:4-15):

| Column | Type | Personal data? |
|---|---|---|
| id | UUID PK | No |
| product_key | TEXT NOT NULL UNIQUE | No (md5 hash of brand+name+variant) |
| brand | TEXT NOT NULL | No |
| name | TEXT NOT NULL | No |
| variant | TEXT | No |
| category | TEXT | No |
| specs | JSONB NOT NULL | No |
| source | TEXT | No |
| fetched_at | TIMESTAMPTZ | No |

**RLS enabled:** Yes — `ALTER TABLE product_specs ENABLE ROW LEVEL SECURITY;` (migration 012:18)

**Policies:**
```sql
CREATE POLICY specs_select ON product_specs FOR SELECT USING (true);
CREATE POLICY specs_insert ON product_specs FOR INSERT WITH CHECK (true);
CREATE POLICY specs_update ON product_specs FOR UPDATE USING (true);
```
(migration 012:19-21)

**product_prices** (migration 012:23-37):

| Column | Type | Personal data? |
|---|---|---|
| id | UUID PK | No |
| product_key | TEXT NOT NULL | No |
| brand | TEXT NOT NULL | No |
| name | TEXT NOT NULL | No |
| variant | TEXT | No |
| region | TEXT NOT NULL | No |
| amount | NUMERIC | No |
| currency | TEXT | No |
| retailer | TEXT | No |
| url | TEXT | No |
| source_method | TEXT | No |
| estimated | BOOLEAN | No |
| fetched_at | TIMESTAMPTZ | No |

**RLS enabled:** Yes — `ALTER TABLE product_prices ENABLE ROW LEVEL SECURITY;` (migration 012:40)

**Policies:**
```sql
CREATE POLICY prices_select ON product_prices FOR SELECT USING (true);
CREATE POLICY prices_insert ON product_prices FOR INSERT WITH CHECK (true);
```
(migration 012:41-42)

**product_reviews** (migration 012:44-56):

| Column | Type | Personal data? |
|---|---|---|
| id | UUID PK | No |
| product_key | TEXT NOT NULL UNIQUE | No |
| brand | TEXT NOT NULL | No |
| name | TEXT NOT NULL | No |
| variant | TEXT | No |
| reviews | JSONB NOT NULL | No (scraped review content) |
| source | TEXT | No |
| fetched_at | TIMESTAMPTZ | No |

**RLS enabled:** Yes — `ALTER TABLE product_reviews ENABLE ROW LEVEL SECURITY;` (migration 012:57)

**Policies:**
```sql
CREATE POLICY reviews_select ON product_reviews FOR SELECT USING (true);
CREATE POLICY reviews_insert ON product_reviews FOR INSERT WITH CHECK (true);
CREATE POLICY reviews_update ON product_reviews FOR UPDATE USING (true);
```
(migration 012:58-60)

---

## Tables: `referral_invites`, `referral_redemptions`, `deep_review_credits`, `re_engagement_events`

Created in migration 014.

**referral_invites** (migration 014:18-30):

| Column | Type | Personal data? |
|---|---|---|
| id | UUID PK | No |
| referrer_user_id | UUID NOT NULL → users(id) ON DELETE CASCADE | Identifier |
| comparison_id | UUID NOT NULL → comparisons(id) ON DELETE CASCADE | No |
| share_target | TEXT NOT NULL (CHECK enum) | No |
| device_fingerprint_hash | TEXT | Potentially — hashed device identifier |
| created_at | TIMESTAMPTZ | No |
| first_viewed_at | TIMESTAMPTZ | No |
| redeemed_at | TIMESTAMPTZ | No |
| redeemed_by_user_id | UUID → users(id) ON DELETE SET NULL | Identifier |
| invitee_first_comparison_id | UUID → comparisons(id) ON DELETE SET NULL | No |
| flagged_reason | TEXT | No |
| privacy | JSONB NOT NULL (added migration 016) | No (user's own privacy toggle choices) |

**RLS enabled:** Yes — `ALTER TABLE referral_invites ENABLE ROW LEVEL SECURITY;` (migration 014:74)

**Policy:**
```sql
CREATE POLICY referral_invites_select_own ON referral_invites FOR SELECT TO authenticated
  USING (referrer_user_id = auth.uid() OR redeemed_by_user_id = auth.uid());
```
(migration 014:80-81)

**referral_redemptions** (migration 014:36-44):

| Column | Type | Personal data? |
|---|---|---|
| id | UUID PK | No |
| invite_id | UUID NOT NULL UNIQUE → referral_invites(id) ON DELETE CASCADE | No |
| referrer_user_id | UUID NOT NULL → users(id) ON DELETE CASCADE | Identifier |
| invitee_user_id | UUID NOT NULL → users(id) ON DELETE CASCADE | Identifier |
| loop2_comparisons_granted | INT NOT NULL | No |
| created_at | TIMESTAMPTZ | No |

**RLS enabled:** Yes — `ALTER TABLE referral_redemptions ENABLE ROW LEVEL SECURITY;` (migration 014:75)

**Policy:**
```sql
CREATE POLICY referral_redemptions_select_own ON referral_redemptions FOR SELECT TO authenticated
  USING (referrer_user_id = auth.uid() OR invitee_user_id = auth.uid());
```
(migration 014:84-85)

**deep_review_credits** (migration 014:47-55):

| Column | Type | Personal data? |
|---|---|---|
| id | UUID PK | No |
| user_id | UUID NOT NULL → users(id) ON DELETE CASCADE | Identifier |
| source | TEXT NOT NULL (CHECK enum) | No |
| granted_at | TIMESTAMPTZ | No |
| expires_at | TIMESTAMPTZ | No |
| consumed_at | TIMESTAMPTZ | No |
| consumed_in_comparison_id | UUID → comparisons(id) ON DELETE SET NULL | No |

**RLS enabled:** Yes — `ALTER TABLE deep_review_credits ENABLE ROW LEVEL SECURITY;` (migration 014:76)

**Policy:**
```sql
CREATE POLICY deep_review_credits_select_own ON deep_review_credits FOR SELECT TO authenticated
  USING (user_id = auth.uid());
```
(migration 014:88-89)

**re_engagement_events** (migration 014:61-70):

| Column | Type | Personal data? |
|---|---|---|
| id | UUID PK | No |
| user_id | UUID NOT NULL → users(id) ON DELETE CASCADE | Identifier |
| event_type | TEXT NOT NULL (CHECK enum) | No |
| comparison_id | UUID → comparisons(id) ON DELETE SET NULL | No |
| triggered_at | TIMESTAMPTZ | No |
| delivered_at | TIMESTAMPTZ | No |
| opened_at | TIMESTAMPTZ | No |
| content_payload | JSONB | Potentially — notification content sent to user |

**RLS enabled:** Yes — `ALTER TABLE re_engagement_events ENABLE ROW LEVEL SECURITY;` (migration 014:77)

**Policy:**
```sql
CREATE POLICY re_engagement_events_select_own ON re_engagement_events FOR SELECT TO authenticated
  USING (user_id = auth.uid());
```
(migration 014:92-93)

---

# SECTION 2: Retention Semantics Per Data Type

**Comparison history:** No automatic deletion in any migration or service file. No scheduled purge job exists in the repository. Retention is effectively **indefinite** until the user deletes a comparison via `DELETE /api/v1/comparisons/{id}` or account deletion triggers `delete_user_cascade`. Cannot determine from code whether Supabase project-level archival applies.

**Search logs:** No automatic deletion. Retention is effectively **indefinite**. The `delete_user_cascade` function deletes search_logs rows for a deleted user (migration 010:80), but no time-based purge is defined.

**User events / analytics events:** No automatic deletion. Retention is effectively **indefinite** until account deletion. `delete_user_cascade` deletes `user_events` rows for a deleted user (migration 010:77).

**admin_audit_log:** No automatic deletion or TTL. Retention is effectively **indefinite**. The `delete_user_cascade` function does **not** delete audit log rows — audit log rows referencing a deleted user_id will remain (nullable user_id column, no CASCADE defined).

**product_specs (L2 DB cache):** Freshness threshold `SPECS_DB_TTL = timedelta(days=30)` (`product_data_service.py:17`). Rows older than 30 days are treated as stale and bypassed, but are **not deleted** from the database — the table grows by upsert with `fetched_at` updates.

**product_prices (L2 DB cache):** Freshness threshold `PRICE_DB_TTL = timedelta(days=1)` (`product_data_service.py:18`). Prices are **appended** (not upserted) to build price history. No automatic deletion. The `fetched_at DESC` query returns only the newest row in practice, but all historical rows persist indefinitely.

**product_reviews (L2 DB cache):** Freshness threshold `REVIEWS_DB_TTL = timedelta(days=14)` (`product_data_service.py:19`). Rows older than 14 days are bypassed but not deleted.

**Redis keys (Upstash L1 cache):**
- Comparison results / price data: default TTL `CACHE_DURATION = 86400` seconds (24 hours), `cache_service.py:167`.
- Product specs / reviews: CLAUDE.md states 7-day Redis TTL.
- User daily usage counters: `key = f"usage:{user_id}:{today}"`, TTL 86400 seconds — `cache_service.py:259`.
- Monthly cost tracking: key `cost:{month}`, TTL `32 * 86400` seconds — `cache_service.py:315`.
- Token revocation blacklist: key `revoked:{sha256(token)}`, TTL 3600 seconds (1 hour) — `auth_service.py:271`.
- Login failure / lockout counters: TTL `LOCKOUT_WINDOW_SECONDS = 900` seconds (15 minutes) — `auth_service.py:15`.

**Sentry events:** Cannot determine from code. Public provider default is 30 days for error data on the free/team plan; verify in the Sentry project dashboard.

---

# SECTION 3: Hosting Regions and Cross-Border Data Flow

## Supabase (Database + Auth)
- **Project ID:** qulajmyxdbdkchvecmvc
- **Region:** Cannot determine from code. Set at creation in Supabase dashboard. Verify in: Supabase Dashboard > Project Settings > General > Region.
- **Data residency note:** Supabase project regions are AWS availability zones (e.g., ap-southeast-1, eu-west-1, us-east-1). User data including email, demographics, comparison queries, behavioral profiles travels to whichever region the project is in.
- **Training use:** Per Supabase public documentation (supabase.com/privacy), Supabase does not use customer database data for AI training.

## Railway (Backend hosting)
- **Deployed URL:** `web-production-58776.up.railway.app`
- **Region:** Public default for Railway is US West (Oregon). Cannot determine from code if changed. Verify in Railway Dashboard.
- **Data implication:** All API request/response data passes through Railway infrastructure (US West by default). Railway does not offer Bahrain or GCC regions.

## Upstash Redis (Cache)
- **Region:** Cannot determine from code. Selected at database creation. Verify in Upstash console.
- **Data held:** Cached comparison results (full product query text), user daily usage counters keyed by user_id, token revocation hashes (SHA-256 of JWT), login lockout state keyed by email address.

## OpenAI (GPT-4o-mini / GPT-4o)
- **Region:** OpenAI API infrastructure is US-based.
- **Data sent:** Product query text, search result snippets, product specifications, review content, user preference hints injected into prompts (cohort priors, priorities, budget — but explicitly not raw age/gender/identity per CLAUDE.md cohort personalization section).
- **Training use:** Per OpenAI API data usage policy (openai.com/policies/api-data-usage-policies): "OpenAI will not use data submitted by customers via our API to train or improve our models, unless you explicitly opt in."
- **Cross-border:** Yes — all OpenAI API calls leave Bahrain.

## Serper (Google Search API)
- **Region:** Cannot determine from code. Verify at serper.dev/privacy.
- **Data sent:** Product search queries.
- **Cross-border:** Yes.

## Firecrawl (Web scraping)
- **Region:** Cannot determine from code.
- **Data sent:** URLs of retailer product pages for scraping.

## Scrape.do (Web rendering fallback)
- **Region:** Cannot determine from code.
- **Data sent:** URLs for JavaScript-rendered page scraping.

## Sentry (Error tracking)
- **Region:** Sentry default is US; EU is an option. Cannot determine from code which region this project uses.
- **Data sent:** Error events with stack traces. JWT and API keys scrubbed via `before_send` hook. Error payloads may contain partial request context.

---

# SECTION 4: Security Posture Summary

**HTTPS / HSTS:** HSTS header in `app/middleware/security.py:19`: `"Strict-Transport-Security": "max-age=31536000; includeSubDomains"`. Added to every response. HTTPS enforcement managed by Railway/Cloudflare.

**Token revocation:** On logout, JWT hashed SHA-256 and stored in Redis as `revoked:{hash}` with 1-hour TTL (`auth_service.py:270-271`). Every `verify_token()` checks this blacklist before validating with Supabase (`auth_service.py:219-221`). Fail-open if Redis unavailable.

**Certificate pinning:** Frontend pins Let's Encrypt E8 and E5 intermediate SPKI hashes. No-op in Expo Go.

**Rate limiting (slowapi):** Applied via `@limiter.limit()` decorators:
- Text compare: 10/min (`text_routes.py:56, 154, 246, 355`); streaming: 20/min (`text_routes.py:388`)
- Image compare: 10/min (`image_routes.py:57`)
- URL routes: 10/min general, 20/min on some endpoints
- Auth — register: 3/min; login: 5/min; refresh: 10/min; social login: 3/min; resend verification: 10/min; account delete: 1/min; demographics: 5/min
- History: 30/min list, 20/min get/delete
- Share: 10/min create, 30/min get
- Feedback: 30/min, events: 60/min
- Referral share: 10/min
- Admin: 30/min on all routes

**Brute-force lockout:** `LOCKOUT_THRESHOLD = 5` and `LOCKOUT_WINDOW_SECONDS = 900` (15 minutes) — `auth_service.py:14-15`. After 5 failed login attempts, subsequent attempts rejected. Counter in Redis, 15-min TTL. Lockout check before Supabase auth call (`auth_routes.py:329-343`). Fail-open on Redis unavailability.

**Admin authentication:** `app/api/admin_routes.py:28-29`: `hmac.compare_digest(x_admin_key, expected)` using `ADMIN_API_KEY` env var. Timing-safe comparison. All admin endpoints have 30/min rate limit.

**Password rules:** `auth_routes.py:52-62` (`_validate_password_strength`): minimum 10 characters, ≥1 uppercase, ≥1 lowercase, ≥1 digit. Applied to registration and password change.

**Encryption at rest:** Managed by Supabase. Per Supabase public docs (supabase.com/docs/guides/platform/security): AES-256.

**Encryption in transit:** TLS at Railway/Cloudflare ingress. HSTS header `max-age=31536000; includeSubDomains`.

**Additional headers (`security.py`):**
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `X-XSS-Protection: 1; mode=block`
- `Permissions-Policy: camera=(), microphone=(), geolocation=()`
- `Content-Security-Policy: default-src 'none'; frame-ancestors 'none'` (for non-`/admin/` paths)

---

# SECTION 5: Account Deletion Mechanism

## `delete_user_cascade` Function

Defined in migration `010_enable_rls.sql:70-84`. Full verbatim:

```sql
CREATE OR REPLACE FUNCTION delete_user_cascade(target_user_id UUID)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  DELETE FROM user_events WHERE user_id = target_user_id;
  DELETE FROM comparison_feedback WHERE user_id = target_user_id;
  DELETE FROM comparisons WHERE user_id = target_user_id;
  DELETE FROM search_logs WHERE user_id = target_user_id;
  UPDATE users SET preferences = NULL, behavior_profile = NULL,
    preferences_completed = false WHERE id = target_user_id;
END;
$$;
```

**Tables deleted from / cleared:**
1. `user_events` — rows where `user_id = target_user_id` (deleted)
2. `comparison_feedback` — rows where `user_id = target_user_id` (deleted)
3. `comparisons` — rows where `user_id = target_user_id` (deleted)
4. `search_logs` — rows where `user_id = target_user_id` (deleted)
5. `users` — row is **not deleted**; only `preferences`, `behavior_profile` set to NULL and `preferences_completed` set to false (anonymized in place)

## ⚠️ CRITICAL FINDING — Tables NOT covered by `delete_user_cascade`:

- `admin_audit_log` — audit records with `user_id` matching the deleted user are not removed (nullable FK, no cascade defined in migration 011)
- `user_usage` — has `ON DELETE CASCADE` on its FK to `users(id)` (migration 011:11), but since `delete_user_cascade` UPDATEs (not deletes) the `users` row, this cascade does **not** fire. Rows remain.
- `referral_invites` — FK `ON DELETE CASCADE` to `users(id)` (migration 014:21) for `referrer_user_id`. Same issue — rows remain.
- `referral_redemptions`, `deep_review_credits`, `re_engagement_events` — all have `ON DELETE CASCADE` to `users(id)` but the update-not-delete pattern prevents firing.
- The `users` row itself with `email`, `display_name`, `expo_push_token`, `referral_code`, `demographics_profile`, `lifetime_comparisons_used`, `subscription_tier`, etc. is **not removed** — only certain JSONB columns are cleared.

## Invocation from `auth_routes.py`

Called from `database_service.py:121`:
```python
client.rpc("delete_user_cascade", {"target_user_id": user_id}).execute()
```
Uses the admin Supabase client (service-role key, bypasses RLS). The `SECURITY DEFINER` attribute means it runs with the privileges of the function owner, ensuring it can delete across all tables regardless of RLS policies.
