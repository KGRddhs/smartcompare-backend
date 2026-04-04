# Security Hardening Design — Qaren (SmartCompare)

> **Audit date:** April 4, 2026
> **Scope:** Full-stack security audit and hardening — backend, frontend, database, supply chain, mobile platform
> **Threat model:** Defense-in-depth against opportunistic attackers, motivated individuals, and insider threats
> **Deployment status:** Pre-release (not in stores)

---

## Executive Summary

5-agent deep audit identified **4 critical, 5 high, 10 medium, 5 low** findings. Supply chain is clean (no malware, no eval, no backdoors, .env never committed to git). Strong foundational security exists (SSRF, security headers, rate limiting, password validation, input sanitization). Three architectural gaps are release blockers: (1) service-role key used for all DB ops bypassing RLS, (2) zero RLS policies exist, (3) auth tokens stored in plaintext AsyncStorage.

## Attack Surface Map

```
ATTACKER → APK Decompile | Network MITM | Stolen Device | Auth Abuse | Admin Brute-force
    │
    ▼
FRONTEND (React Native / Expo)
  ├── C3: Tokens in AsyncStorage (PLAINTEXT) ← CRITICAL
  ├── H3: Google Client ID hardcoded in comments
  ├── H2: Google OAuth no nonce (replay)
  ├── L5: Apple nonce uses Math.random()
  ├── M6: Debug console.log leaks auth state
  └── M9: Login accepts 6-char passwords (backend requires 10)
    │ HTTPS (no cert pinning — Phase 2)
    ▼
BACKEND (FastAPI on Railway)
  ├── C4: Admin endpoints: ZERO rate limiting ← CRITICAL
  ├── H1: Email change no password required
  ├── H4: Logout no token revocation
  ├── M1: History 404 vs 403 leaks existence
  ├── M2: Image endpoint leaks str(e) in errors
  ├── M3: Image endpoint returns raw_response
  ├── M4: Query params no max_length (DoS)
  └── M10: Preferences returns str(e) on error
    │ Service-role key (BYPASSES ALL RLS)
    ▼
SUPABASE (PostgreSQL)
  ├── C1: Service-role key for ALL user operations ← CRITICAL
  ├── C2: ZERO RLS policies on any table ← CRITICAL
  ├── H5: Share token 48-bit entropy (weak)
  └── M8: Cascade delete not atomic
```

## Verified Findings

### CRITICAL (Release Blockers)

#### C1: Service-role key used for ALL database operations
- **Files:** `app/services/database_service.py:14`, `app/services/auth_service.py:23-27,55,84,133,186,231,264,313,326,336,348,367`
- **Evidence:** `SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")` — every query bypasses RLS
- **Risk:** Any backend bug, SSRF bypass, or injection = full database read/write
- **Fix:** Split into user client (anon key + JWT, RLS enforced) and admin client (service-role, restricted to admin-only ops)

#### C2: Zero RLS policies on any user-data table
- **Files:** `migrations/*.sql` — no `ENABLE ROW LEVEL SECURITY` or `CREATE POLICY` anywhere
- **Evidence:** Grep across all .sql files returns zero matches
- **Risk:** Even after fixing C1, no policies exist to enforce row-level access
- **Fix:** New migration enabling RLS on all 6 user-data tables with least-privilege policies

#### C3: Auth tokens stored in AsyncStorage (plaintext)
- **Files:** `SmartCompareApp/src/services/authService.ts:6,64-65,268,280,291`
- **Evidence:** `expo-secure-store` is installed (package.json line 32, app.json line 33) but never imported. All token ops use `AsyncStorage`.
- **Risk:** Rooted Android device = tokens readable from unencrypted SQLite
- **Fix:** Migrate token storage to `expo-secure-store` (Keychain on iOS, Keystore on Android)

#### C4: Admin endpoints have zero rate limiting
- **Files:** `app/api/admin_routes.py:31-112` — 6 endpoints, none have `@limiter.limit()`
- **Evidence:** Confirmed: no rate limit decorator on any admin route
- **Risk:** Admin API key brute-force at unlimited speed
- **Fix:** Add `@limiter.limit("30/minute")` to all admin endpoints

### HIGH

#### H1: Email change requires no password verification
- **Files:** `app/api/auth_routes.py:356-363`, `app/services/auth_service.py:323-330`
- **Evidence:** `update_user_email(user_id, new_email)` — no password param
- **Fix:** Add `current_password` to `UpdateEmailRequest`, verify via login attempt before update

#### H2: Google OAuth has no nonce (replay attack)
- **Files:** `SmartCompareApp/src/services/authService.ts:381-397`
- **Evidence:** Sends `{provider: 'google', id_token: idToken}` with no nonce. Apple flow at line 448 correctly uses nonce.
- **Fix:** Generate nonce with `expo-crypto.getRandomBytes()`, hash with SHA256, send raw nonce to backend

#### H3: Google Client ID hardcoded in source comments
- **Files:** `SmartCompareApp/src/services/authService.ts:362-367`
- **Evidence:** Comment block exposes both Web and iOS Client IDs. The `webClientId` in `configure()` (line 373) is expected per Google docs, but comments are unnecessary.
- **Fix:** Delete comment block (lines 362-367). Keep `webClientId` in `configure()`.

#### H4: Logout doesn't invalidate tokens server-side
- **Files:** `app/services/auth_service.py:239-246`
- **Evidence:** `client.auth.sign_out()` called without token — global operation, no server-side blacklist
- **Fix:** On logout, hash token and store in Redis with TTL matching token expiry. Check blacklist in `verify_token()`.

#### H5: Share token weak entropy (48 bits)
- **Files:** `app/services/database_service.py:252`
- **Evidence:** `secrets.token_urlsafe(6)` = ~48 bits = brute-forceable in hours
- **Fix:** `secrets.token_urlsafe(16)` = 128 bits = ~22 chars

### MEDIUM

#### M1: History routes leak existence via 404 vs 403
- **Files:** `app/api/history_routes.py:67-71,95-99`
- **Fix:** Single 404 for both missing and unauthorized. Use `hmac.compare_digest` for ownership.

#### M2: Image endpoint leaks `str(e)` in 500 errors
- **Files:** `app/api/image_routes.py:109`
- **Fix:** Generic message: `"Image analysis failed. Please try again."`

#### M3: Image endpoint returns `raw_response` to client
- **Files:** `app/api/image_routes.py:117`
- **Fix:** Remove `raw_response` from client response, log server-side only.

#### M4: Query params have no max_length
- **Files:** `app/api/text_routes.py:140,217,381,416`
- **Fix:** `q: str = Query(..., max_length=500)` on all endpoints.

#### M5: Rate limiter is in-memory only (documented, acceptable for single instance)
- **Files:** `app/middleware/rate_limiter.py:22-23`
- **Status:** Accepted for now. Revisit when scaling to 2+ instances.

#### M6: Debug console.logs leak auth state
- **Files:** `authService.ts:79,83,120,124`, `api.ts:29`
- **Fix:** Wrap with `if (__DEV__)` guards.

#### M7: CORS allows credentials with localhost origins
- **Files:** `app/main.py:71-76`
- **Status:** Acceptable for dev. Add env-based origin list for production.

#### M8: Cascade delete is not atomic
- **Files:** `app/services/database_service.py:94-112`
- **Fix:** Postgres function `delete_user_cascade(user_id)` called via `.rpc()`.

#### M9: Login screen accepts 6-char passwords
- **Files:** `SmartCompareApp/src/screens/LoginScreen.tsx:99`
- **Fix:** Match backend requirement: 10+ chars, 1 upper, 1 lower, 1 digit.

#### M10: `get_user_preferences` returns `str(e)` on error
- **Files:** `app/services/auth_service.py:361`
- **Fix:** Generic error message.

### LOW

#### L1: No Sentry breadcrumb sanitization
- **Files:** `app/middleware/error_handler.py:113-114`
- **Fix:** Add `before_send` hook to strip JWT patterns and API keys from Sentry events.

#### L2: Timing-unsafe comparison in ownership checks
- **Files:** `app/api/history_routes.py:70,98`, `app/services/database_service.py:242`
- **Fix:** Use `hmac.compare_digest()` (folded into M1 fix).

#### L3: No screenshot protection on auth screens
- **Files:** LoginScreen, RegisterScreen, ForgotPasswordScreen
- **Fix:** Add `expo-screen-capture` `preventScreenCaptureAsync()` on auth screens.

#### L4: Frontend URL validation only checks prefix
- **Files:** `SmartCompareApp/src/screens/HomeScreen.tsx:~270`
- **Fix:** Use `new URL()` constructor for proper validation. Backend SSRF validator is primary gate.

#### L5: Apple nonce uses `Math.random()` (not crypto-secure)
- **Files:** `SmartCompareApp/src/services/authService.ts:448`
- **Fix:** Replace with `expo-crypto.getRandomBytes()` + hex encoding.

### VERIFIED SECURE (No Changes Needed)

- SSRF protection (`url_validator.py`) — blocks private/loopback/link-local
- Security headers — HSTS, CSP, X-Frame-Options, nosniff, Permissions-Policy
- Admin key timing-safe — `hmac.compare_digest()` in `admin_routes.py:26`
- Password strength — 10+ chars with complexity in `auth_routes.py:38-48`
- Email enumeration prevention — always returns success
- Pydantic model whitelisting — no mass assignment
- LIKE wildcard escaping — `database_service.py:183`
- Image upload validation — magic bytes, MIME, 10MB limit
- UUID path params — FastAPI auto-validates
- Swagger docs disabled in prod — checks `RAILWAY_ENVIRONMENT`
- Account deletion cascade — correct order, rate limited 1/min
- Share personalization stripping — removes personal fields
- Supply chain — clean (no eval, no backdoors, no malicious deps)
- Git history — .env never committed (verified via `git log -p -S`)
- Unified error format — no stack traces in responses (except image endpoint M2)

---

## Fix Architecture

### Phase 1: Release Blockers + High (Must complete)

#### Layer 1: Database Fortress (C1, C2, H5, M8)

**Migration `010_enable_rls.sql`:**
```sql
-- Enable RLS on all user-data tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE comparisons ENABLE ROW LEVEL SECURITY;
ALTER TABLE search_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE comparison_feedback ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_events ENABLE ROW LEVEL SECURITY;

-- users: read/update own row only
CREATE POLICY users_select ON users FOR SELECT USING (auth.uid() = id);
CREATE POLICY users_update ON users FOR UPDATE USING (auth.uid() = id);
CREATE POLICY users_insert ON users FOR INSERT WITH CHECK (auth.uid() = id);

-- comparisons: own rows + shared via token
CREATE POLICY comparisons_select ON comparisons FOR SELECT
  USING (auth.uid() = user_id OR share_token IS NOT NULL);
CREATE POLICY comparisons_insert ON comparisons FOR INSERT
  WITH CHECK (auth.uid() = user_id);
CREATE POLICY comparisons_delete ON comparisons FOR DELETE
  USING (auth.uid() = user_id);

-- search_logs: own rows
CREATE POLICY search_logs_insert ON search_logs FOR INSERT
  WITH CHECK (auth.uid() = user_id OR user_id IS NULL);
CREATE POLICY search_logs_select ON search_logs FOR SELECT
  USING (auth.uid() = user_id);

-- comparison_feedback: own rows
CREATE POLICY feedback_insert ON comparison_feedback FOR INSERT
  WITH CHECK (auth.uid() = user_id OR user_id IS NULL);
CREATE POLICY feedback_select ON comparison_feedback FOR SELECT
  USING (auth.uid() = user_id);

-- user_events: own rows
CREATE POLICY events_insert ON user_events FOR INSERT
  WITH CHECK (auth.uid() = user_id OR user_id IS NULL);
CREATE POLICY events_select ON user_events FOR SELECT
  USING (auth.uid() = user_id);

-- bahrain_approved_drugs: read-only for all authenticated
CREATE POLICY drugs_select ON bahrain_approved_drugs FOR SELECT
  USING (auth.role() = 'authenticated' OR auth.role() = 'anon');

-- Atomic cascade delete function
CREATE OR REPLACE FUNCTION delete_user_cascade(target_user_id UUID)
RETURNS void AS $$
BEGIN
  DELETE FROM user_events WHERE user_id = target_user_id;
  DELETE FROM comparison_feedback WHERE user_id = target_user_id;
  DELETE FROM comparisons WHERE user_id = target_user_id;
  DELETE FROM search_logs WHERE user_id = target_user_id;
  UPDATE users SET preferences = NULL, behavior_profile = NULL,
    preferences_completed = false WHERE id = target_user_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

**Refactor `database_service.py`:**
- Add `get_user_client(access_token)` → creates client with anon key, sets `Authorization: Bearer {jwt}` header
- All user-facing queries use user client (RLS enforced)
- `get_admin_client()` restricted to: health check, admin analytics, anonymous inserts (search_logs without user_id)
- Thread access_token from `get_current_user` → route handler → service functions

**Refactor `auth_service.py`:**
- User reads (profile, preferences) → user client with JWT
- Admin-only ops (create user row on register, delete user, admin password change) → admin client
- Pass access_token through auth routes

**Share token:** `secrets.token_urlsafe(16)` (128 bits)

**Cascade delete:** Call `delete_user_cascade` via `.rpc()` instead of sequential deletes

#### Layer 2: Auth Hardening (H1, H2, H4, L5, M9)

**Email change requires password:**
- Add `current_password: str` to `UpdateEmailRequest`
- In `update_user_email()`: verify password via `sign_in_with_password()` before calling admin API
- On failure: return "Current password is incorrect"

**Google OAuth nonce:**
- In `signInWithGoogle()`: generate 32 random bytes via `expo-crypto.getRandomBytes(32)`
- Convert to hex string, hash with SHA256
- Send raw nonce in request body: `{provider: 'google', id_token, nonce: rawNonce}`
- Backend already passes nonce to `sign_in_with_id_token()` if present (auth_service.py:255-256)

**Apple nonce fix:**
- Replace `Math.random().toString(36).substring(2, 15)` with `expo-crypto.getRandomBytes(32)` → hex

**Token revocation:**
- On logout: `redis_client.setex(f"revoked:{sha256(token)}", ttl_seconds, "1")`
- In `verify_token()`: check `redis_client.get(f"revoked:{sha256(token)}")` — if found, return None
- TTL matches Supabase JWT expiry (default 3600s) — self-cleaning
- Use existing `cache_service.redis_client`

**Login password validation:**
- `LoginScreen.tsx:99`: change from `password.length < 6` to match backend policy (10+ chars, upper, lower, digit)

#### Layer 3: Frontend Token Security (C3, H3, M6)

**Migrate to expo-secure-store:**
```typescript
import * as SecureStore from 'expo-secure-store';

async function saveToken(token: string): Promise<void> {
  await SecureStore.setItemAsync(TOKEN_STORAGE_KEY, token);
}

export async function getToken(): Promise<string | null> {
  return await SecureStore.getItemAsync(TOKEN_STORAGE_KEY);
}

export async function clearSession(): Promise<void> {
  await SecureStore.deleteItemAsync(TOKEN_STORAGE_KEY);
  await SecureStore.deleteItemAsync(REFRESH_TOKEN_KEY);
  await AsyncStorage.removeItem(USER_STORAGE_KEY); // user profile stays in AsyncStorage (non-secret)
}
```
- Also migrate refresh token storage
- Keep user profile data in AsyncStorage (not secret — just email/display_name)

**Remove Client ID comments:** Delete lines 362-367 in `authService.ts`

**Debug log guards:** Wrap all `console.log/warn/error` in `authService.ts` and `api.ts` with `if (__DEV__)`

#### Layer 4: API Hardening (C4, M1, M2, M3, M4, M10)

**Admin rate limiting:** Add `@limiter.limit("30/minute")` to all 6 admin routes

**History route hardening:**
```python
# Single 404 for both missing and unauthorized
if not comparison or not hmac.compare_digest(
    str(comparison.get("user_id", "")),
    current_user["id"]
):
    raise HTTPException(status_code=404, detail="Comparison not found")
```

**Image endpoint sanitization:**
- Line 109: `detail="Image analysis failed. Please try again."`
- Line 117: Remove `raw_response` from response dict

**Query max_length:** `q: str = Query(..., max_length=500)` on lines 140, 217, 381, 416

**Preference error sanitization:** Replace `str(e)` with `"Failed to load preferences"` in `auth_service.py:361`

### Phase 2: Defense-in-Depth (Complete after Phase 1)

#### Layer 5: Sentry Sanitization (L1)
- Add `before_send` hook in `sentry_service.py` that strips JWT patterns (`eyJ...`), API key patterns (`sk-...`, `fc-...`), and `Authorization` headers from all Sentry events and breadcrumbs

#### Layer 6: Frontend Hardening (L3, L4, L5 — already covered above)
- Screenshot protection on auth screens using `expo-screen-capture`
- URL validation with `new URL()` constructor in `HomeScreen.tsx`
- (L5 Apple nonce already in Phase 1)

#### Layer 7: CORS Environment Config (M7)
- Move `ALLOWED_ORIGINS` to env var `CORS_ORIGINS` (comma-separated)
- Production: only Railway URL
- Dev: add localhost origins
- Fallback to current hardcoded list if env var not set

#### Layer 8: Certificate Pinning Prep
- Add `react-native-ssl-pinning` or equivalent to package.json
- Create pinning config for Railway's TLS certificate
- Wrap API calls to use pinned fetch
- Note: Only testable with EAS dev build, not Expo Go

### Phase 3: Security Tests (80%+ coverage target)

**New file: `tests/test_security_regression.py`**
Tests that MUST pass and cannot be removed:

1. **RLS enforcement:** User A cannot read User B's comparisons via API
2. **RLS enforcement:** User A cannot delete User B's comparisons
3. **Admin rate limiting:** Verify 429 after burst of 31 requests
4. **Token blacklist:** Token rejected after logout
5. **Email change requires password:** 400 without current_password
6. **Email change wrong password:** 400 with wrong password
7. **Share token length:** New tokens are ≥ 22 chars (128-bit)
8. **Image endpoint:** Error response contains no exception details
9. **Image endpoint:** No `raw_response` in error output
10. **History endpoint:** Returns 404 for both missing AND unauthorized comparison IDs
11. **Query length:** 501-char query rejected with 422
12. **Admin key brute-force:** Rate limited after 30 attempts
13. **Cascade delete atomic:** All-or-nothing (mock partial failure)
14. **Password validation consistency:** Login screen rejects weak passwords (frontend grep test)
15. **No debug logs in production:** No bare `console.log` without `__DEV__` in auth/api files (grep test)
16. **No service-role in frontend:** No `SUPABASE_SERVICE_KEY` string in SmartCompareApp/ (grep test)
17. **Preference error sanitization:** Error response contains no Python exception text
18. **Nonce present in Google OAuth:** Request body includes nonce field

**New file: `tests/test_rls_policies.py`**
Tests that verify RLS policies work correctly (requires test Supabase setup):

1. Anon key + user JWT: can read own comparisons
2. Anon key + user JWT: cannot read other user's comparisons
3. Anon key + user JWT: can insert own comparison
4. Anon key + user JWT: cannot insert comparison with different user_id
5. Anon key + user JWT: can delete own comparison
6. Anon key + user JWT: cannot delete other user's comparison
7. Service-role: can read all (for admin analytics)
8. Shared comparisons: accessible without auth via share_token

---

## Team Execution Plan

### Team Structure (4 Opus agents)

| Agent | Domain | Files Owned (non-overlapping) |
|-------|--------|------------------------------|
| **backend-security** | Database + API hardening | `database_service.py`, `auth_service.py`, `admin_routes.py`, `history_routes.py`, `image_routes.py`, `text_routes.py`, `share_routes.py`, `rate_limiter.py`, `error_handler.py`, `sentry_service.py`, `main.py`, `migrations/010_enable_rls.sql` |
| **frontend-security** | Token migration + client fixes | `authService.ts`, `api.ts`, `LoginScreen.tsx`, `HomeScreen.tsx`, `RegisterScreen.tsx`, `ForgotPasswordScreen.tsx`, `ProfileScreen.tsx` |
| **test-security** | Security regression tests | `tests/test_security_regression.py`, `tests/test_rls_policies.py` |
| **qa-security** | Cross-QA all work | Reviews all changes, runs full test suite, verifies no regressions |

### Execution Rules

1. **No file conflicts:** Each agent owns specific files. No two agents edit the same file.
2. **Cross-QA:** After completing work, each agent QAs another's work:
   - backend-security QAs → frontend-security
   - frontend-security QAs → test-security
   - test-security QAs → backend-security
   - qa-security QAs → all agents
3. **Send back if subpar:** If QA finds issues, work goes back to the author with specific feedback.
4. **Idle agents write tests:** If waiting for QA results, write red-green tests targeting 80% coverage.
5. **All work verified before team dissolution.**
6. **All Opus agents, no Sonnet/Haiku.**

### Task Ordering

**Phase 1 (Critical + High):**
1. backend-security: RLS migration + database_service refactor + auth_service refactor (C1, C2, H5, M8)
2. backend-security: API hardening — admin rate limits, history routes, image sanitization, query length (C4, M1, M2, M3, M4, M10)
3. backend-security: Auth hardening — email change password, token revocation, preference error sanitization (H1, H4)
4. frontend-security: SecureStore migration (C3)
5. frontend-security: Google nonce + Apple nonce fix + Client ID comment removal (H2, H3, L5)
6. frontend-security: Debug log guards + login password validation (M6, M9)
7. test-security: Security regression tests for Phase 1 (all 18 test cases)
8. qa-security: Cross-QA all Phase 1 work + run full test suite

**Phase 2 (Medium + Low):**
9. backend-security: Sentry sanitization + CORS env config (L1, M7)
10. frontend-security: Screenshot protection + URL validation (L3, L4)
11. test-security: Phase 2 regression tests
12. qa-security: Final cross-QA + full test suite

### Dependencies
- Tasks 2, 3 depend on Task 1 (database refactor must land first)
- Tasks 5, 6 are independent of backend work
- Task 7 depends on Tasks 1-6 (tests validate all fixes)
- Task 8 depends on Task 7
- Phase 2 depends on Phase 1 QA passing

---

## Residual Risks (After All Fixes)

| Risk | Mitigation Applied | Residual Level |
|------|-------------------|----------------|
| Supabase JWT signing key compromise | Supabase manages rotation | Accept — vendor responsibility |
| Railway env var leak | Railway encrypts at rest + TLS | Accept — platform responsibility |
| Token theft via device malware (even with SecureStore) | Hardware-backed Keychain/Keystore | Low — requires root/jailbreak |
| MITM without cert pinning (Phase 2 adds prep) | HTTPS + HSTS enforced | Low — attacker needs compromised CA |
| In-memory rate limit bypass (multi-instance) | Single Railway instance | Revisit at scale |
| Supabase RLS misconfiguration | Tests verify policies | Low — test regression guards |

## Release Checklist

- [ ] All Critical findings (C1-C4) fixed and tested
- [ ] All High findings (H1-H5) fixed and tested
- [ ] All Medium findings (M1-M10) fixed and tested
- [ ] All Low findings (L1-L5) fixed and tested
- [ ] RLS migration applied to Supabase
- [ ] `test_security_regression.py` passes (18 test cases)
- [ ] Full existing test suite passes (1560+ tests, 0 regressions)
- [ ] Cross-QA completed by all agents
- [ ] API keys rotated (best practice — .env was never committed)
- [ ] No `SUPABASE_SERVICE_KEY` in frontend code (grep verified)
- [ ] No bare `console.log` without `__DEV__` in auth/api services
