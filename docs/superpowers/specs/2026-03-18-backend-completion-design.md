# Backend Completion: History, Sharing, Errors, Auth Rate Limits

**Date:** 2026-03-18 (Session 24)
**Status:** Approved

## Problem

Session 22 deleted `routes.py` (485 lines dead code) but failed to migrate 3 history endpoints. The frontend `HistoryScreen.tsx` now hits 404s in production. Additionally, 5 other backend gaps exist: no sharing functionality, inconsistent error formats, no auth rate limiting, a URL multi-compare stub, and Google Sign-In not enabled in Supabase.

## Scope

6 fixes, 2 rounds of agent teams:

1. **History routes** — restore deleted endpoints in new `history_routes.py`
2. **Share routes** — new `share_routes.py` with public share links
3. **Unified error responses** — middleware to standardize all errors
4. **Auth rate limiting** — brute force protection on login/register
5. **URL multi-compare cleanup** — delete stub endpoint
6. **Google Sign-In** — Supabase Dashboard instructions (no code)

## Design

### 1. History Routes (`app/api/history_routes.py`)

New router registered in `main.py` under `/api/v1/comparisons` (matches existing frontend paths).

**Endpoints:**

| Method | Path | Auth | Rate Limit | Description |
|--------|------|------|------------|-------------|
| GET | `/api/v1/comparisons/history` | Required | 30/min | List user's comparisons (paginated) |
| GET | `/api/v1/comparisons/{id}` | Required | 30/min | Get single comparison with full_response |
| DELETE | `/api/v1/comparisons/{id}` | Required | 10/min | Delete comparison (ownership check) |

**GET /comparisons/history query params:**
- `search` (optional): filter by query text (ILIKE)
- `limit` (default 20, max 50): pagination
- `offset` (default 0): pagination offset

**GET /comparisons/history response** (list — NO `full_response` blob):
```json
{
  "success": true,
  "comparisons": [
    {
      "id": "uuid",
      "query": "iPhone 15 vs Galaxy S24",
      "product_names": ["iPhone 15", "Galaxy S24"],
      "input_type": "text",
      "created_at": "2026-03-18T10:30:00Z"
    }
  ],
  "total": 45,
  "limit": 20,
  "offset": 0
}
```

**GET /comparisons/{id} response** (single — includes `full_response`):
```json
{
  "success": true,
  "comparison": {
    "id": "uuid",
    "query": "...",
    "product_names": [...],
    "input_type": "text",
    "full_response": { /* full JSONB blob */ },
    "created_at": "..."
  }
}
```

**DELETE /comparisons/{id} response:**
```json
{ "success": true }
```

**Error scenarios:**
- 401: Missing/invalid auth token → `AUTH_REQUIRED`
- 404: Comparison not found → `NOT_FOUND`
- 403: Comparison belongs to another user → `FORBIDDEN`

**Implementation:** Calls existing `get_user_comparisons()`, `delete_comparison()` in `database_service.py`. Need to add `get_comparison_by_id()` function for single-comparison fetch.

**Auth:** Import `get_current_user()` from `auth_routes.py` (shared dependency). Field name is `full_response` (matches DB column and frontend HistoryScreen.tsx expectations).

### 2. Share Routes (`app/api/share_routes.py`)

New router registered in `main.py` under `/api/v1/share`.

**Endpoints:**

| Method | Path | Auth | Rate Limit | Description |
|--------|------|------|------------|-------------|
| POST | `/api/v1/share/{comparison_id}` | Required | 10/min | Generate share link for a comparison |
| GET | `/api/v1/share/{token}` | None | 30/min | View shared comparison (public) |

**Database change:** Add `share_token` column to `comparisons` table.
```sql
ALTER TABLE comparisons ADD COLUMN share_token VARCHAR(12) UNIQUE;
CREATE INDEX idx_comparisons_share_token ON comparisons(share_token) WHERE share_token IS NOT NULL;
```

**Share token:** 8-character URL-safe base64 string. Generated via `secrets.token_urlsafe(6)` (produces 8 chars). Idempotent — sharing same comparison twice returns same token. On collision (UNIQUE constraint), retry up to 3 times with new token.

**Ownership check (CRITICAL):** POST /share must verify `comparison.user_id == current_user.id`. Return 403 if not owner.

**POST /share/{comparison_id} response:**
```json
{
  "success": true,
  "share_token": "abc12xyz",
  "share_url": "https://web-production-58776.up.railway.app/api/v1/share/abc12xyz"
}
```

**GET /share/{token} response:**
```json
{
  "success": true,
  "comparison": {
    "query": "iPhone 15 vs Galaxy S24",
    "product_names": ["iPhone 15", "Galaxy S24"],
    "input_type": "text",
    "full_response": { /* full JSONB blob, user-specific fields stripped */ },
    "created_at": "..."
  }
}
```

**Stripped fields from `full_response`:** Remove `personalized`, `personalization_factors`, `personalization_prompt` keys if present. The `user_id` is never in `full_response` (it's a separate column).

**Error scenarios:**
- 401: Missing auth on POST → `AUTH_REQUIRED`
- 403: Comparison belongs to another user → `FORBIDDEN`
- 404: Comparison not found (POST) or invalid share token (GET) → `NOT_FOUND`

**Deleted comparison handling:** If a shared comparison is deleted, GET /share/{token} returns 404. No CASCADE — the `share_token` column is on the `comparisons` row itself, so deleting the row removes both.

**Database functions (in `database_service.py`):**
- `create_share_token(comparison_id, user_id)` — verifies ownership, generates token, stores, returns token (or existing if already shared). Retry on collision (max 3).
- `get_shared_comparison(share_token)` — fetches by token, no auth check, strips personalization fields

### 3. Unified Error Response Middleware

Modify existing `app/middleware/error_handler.py` to intercept all error types:

**Standard error response format:**
```json
{
  "success": false,
  "error": "Human-readable error message",
  "code": "ERROR_CODE",
  "request_id": "uuid"
}
```

**Error codes:**
| Code | HTTP Status | Source |
|------|-------------|--------|
| `AUTH_REQUIRED` | 401 | Missing/invalid token |
| `AUTH_FAILED` | 401 | Wrong credentials |
| `FORBIDDEN` | 403 | Not authorized for resource |
| `NOT_FOUND` | 404 | Resource doesn't exist |
| `VALIDATION_ERROR` | 422 | Invalid request body/params |
| `RATE_LIMITED` | 429 | Too many requests |
| `SERVER_ERROR` | 500 | Unhandled exception |

**Implementation:**
- Add `RequestValidationError` handler → `VALIDATION_ERROR`
- Add `HTTPException` handler → map status to code
- Existing global exception handler already returns 500 → add `code` field
- Replace slowapi's default 429 handler with unified handler → `RATE_LIMITED`
- Database connection failures → `SERVER_ERROR` (500)
- Invalid UUID format in path params → `VALIDATION_ERROR` (422)

**No changes to route code.** Routes keep raising `HTTPException` as before — the middleware transforms the response format. The slowapi custom handler in `main.py` should be replaced by the unified middleware.

### 4. Auth Rate Limiting

Add rate limits to `app/api/auth_routes.py` using existing `limiter` from `rate_limiter.py`:

| Endpoint | Rate Limit | Rationale |
|----------|-----------|-----------|
| POST `/login` | 5/minute | Brute force protection |
| POST `/register` | 3/minute | Spam prevention |
| POST `/social-login` | 10/minute | Higher since no password brute force risk |
| POST `/password-reset` | 3/minute | Email spam prevention |

**Key by:** IP address (default slowapi behavior). No auth token available for these endpoints.

### 5. URL Multi-Compare Cleanup

- Delete `/api/v1/url/compare/multi` endpoint from `url_routes.py`
- Remove associated request model if any
- Keep `/api/v1/url/compare` for 2-product comparison (unchanged)

### 6. Google Sign-In — Supabase Dashboard Instructions

No code changes. Manual steps for the user:

1. Go to https://supabase.com/dashboard → project `qulajmyxdbdkchvecmvc`
2. Authentication → Providers → Google → Enable
3. Enter Client ID: `21336192767-i9prqks93nrdmb9rg7ho2v1md9bgqgsv.apps.googleusercontent.com`
4. Enter Client Secret: (from Google Cloud Console → APIs & Services → Credentials → OAuth 2.0 Client)
5. Save

**Note:** The Client Secret is NOT stored in code — it's only needed in Supabase Dashboard. The user needs to retrieve it from Google Cloud Console.

## Files Changed

### New Files
- `app/api/history_routes.py` — 3 endpoints (~80 lines)
- `app/api/share_routes.py` — 2 endpoints (~70 lines)
- `tests/test_history_routes.py` — history endpoint tests
- `tests/test_share_routes.py` — share endpoint tests
- `tests/test_error_middleware.py` — error format tests

### Modified Files
- `app/main.py` — register 2 new routers
- `app/middleware/error_handler.py` — add HTTPException/validation handlers, error codes
- `app/api/auth_routes.py` — add rate limit decorators (4 endpoints)
- `app/api/url_routes.py` — delete `/compare/multi` endpoint
- `app/services/database_service.py` — add `get_comparison_by_id()`, `create_share_token()`, `get_shared_comparison()`

### Database Migration
```sql
-- Apply
ALTER TABLE comparisons ADD COLUMN share_token VARCHAR(12) UNIQUE;
CREATE INDEX idx_comparisons_share_token ON comparisons(share_token) WHERE share_token IS NOT NULL;

-- Rollback (if needed)
DROP INDEX IF EXISTS idx_comparisons_share_token;
ALTER TABLE comparisons DROP COLUMN IF EXISTS share_token;
```

**RLS:** The `comparisons` table should have RLS policies:
- SELECT: `auth.uid() = user_id` (own comparisons) OR `share_token IS NOT NULL` (shared, accessed via service role)
- INSERT: `auth.uid() = user_id`
- DELETE: `auth.uid() = user_id`
- Note: Share GET endpoint uses service role key to bypass RLS (public access by design).

## Agent Team Strategy

**Tool:** TeamCreate (Claude Agent Teams), NOT Task subagents.
**Agent model:** Opus (all agents).

### Round 1: Core Fixes
**Agent A (backend-core):**
- Create `history_routes.py` (3 endpoints)
- Add `get_comparison_by_id()` to `database_service.py`
- Register router in `main.py`
- Modify `error_handler.py` (unified error format)
- Add auth rate limits to `auth_routes.py`
- Delete URL multi-compare stub
- Syntax check all modified files

**Agent B (test-core):**
- Write `tests/test_history_routes.py` (target: 15+ tests)
- Write `tests/test_error_middleware.py` (target: 10+ tests)
- Write auth rate limit tests (add to existing `test_auth_interceptor.py`)
- Run full free test suite, fix any regressions
- QA Agent A's implementation files

**Cross-QA:** Each agent reviews the other's work. Agents write tests for idle time. Team dissolved only after both pass QA.

### Round 2: Sharing + Final QA
**Agent A (backend-share):**
- Create `share_routes.py` (2 endpoints)
- Add `create_share_token()`, `get_shared_comparison()` to `database_service.py`
- Register router in `main.py`
- Run SQL migration (via Supabase MCP or provide migration file)
- Syntax check all files

**Agent B (test-share):**
- Write `tests/test_share_routes.py` (target: 12+ tests)
- Run full free test suite
- QA Agent A's share implementation
- QA Round 1 work (verify history + errors + rate limits still clean)

**Cross-QA:** Same pattern. Team dissolved after full QA pass.

### Context Management (Pro Subscription)
- Fresh TeamCreate per round (no accumulated context)
- Each agent reads only files it needs (not full session history)
- After each round: update `docs/CONTEXT_SESSION_LOG.md` with what changed
- Agents use `bypassPermissions` mode
- 2 agents per round (not 4) — proven in Sessions 20-22

## Test Coverage Targets

| Component | Target Tests | Coverage |
|-----------|-------------|----------|
| History routes | 15+ | 80%+ |
| Share routes | 12+ | 80%+ |
| Error middleware | 10+ | 80%+ |
| Auth rate limits | 4+ | 100% (simple decorators) |
| URL cleanup | 2+ | Verify endpoint removed |
| **Total new tests** | **43+** | **80%+ overall** |

## Success Criteria

- [ ] `GET /api/v1/comparisons/history` returns user's comparisons (auth required)
- [ ] `GET /api/v1/comparisons/{id}` returns single comparison with `full_response` (ownership check)
- [ ] `DELETE /api/v1/comparisons/{id}` deletes with ownership check
- [ ] `POST /api/v1/share/{comparison_id}` generates share token (ownership check!)
- [ ] `GET /api/v1/share/{token}` returns comparison without auth (personalization stripped)
- [ ] All error responses follow `{ success, error, code, request_id }` format
- [ ] Login/register have rate limits
- [ ] URL multi-compare stub removed
- [ ] 43+ new tests, all passing
- [ ] Existing 717 tests still pass (no regressions)
- [ ] `python -m py_compile` passes on all modified files
- [ ] Share of another user's comparison returns 403
