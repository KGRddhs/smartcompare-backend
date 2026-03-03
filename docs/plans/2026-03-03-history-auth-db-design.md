# Design: History, Auth & Database Improvements

**Date:** 2026-03-03
**Status:** Approved

## Problem

History is fundamentally broken — the text comparison endpoint (primary flow) never saves to the database. The `save_comparison()` function exists but is never called. Auth tokens are saved on the frontend but never sent on API requests. The database has 6 orphaned tables never wired into the active code path.

## Decisions

- **Auth:** Fix properly — axios interceptor, JWT on endpoints, real user identity
- **Storage:** Full JSONB blob — store the entire API response for perfect history reconstruction
- **DB strategy:** Pragmatic middle — full blob + search_logs + lightweight product dedup by exact name (no fuzzy matching)
- **Team:** 3 Opus agents (Auth + History + DB) with circular cross-QA

## Team Structure

### Agent 1: Auth Agent
**Scope:** Fix the auth pipeline end-to-end
- **QAs:** Agent 2 (History)
- **Idle work:** Write auth tests targeting 80% coverage

### Agent 2: History Agent
**Scope:** Make history work completely
- **QAs:** Agent 3 (DB)
- **Idle work:** Write history tests targeting 80% coverage

### Agent 3: DB Agent
**Scope:** Database schema improvements + analytics
- **QAs:** Agent 1 (Auth)
- **Idle work:** Write DB tests targeting 80% coverage

### QA Circle
```
Auth --QAs--> History --QAs--> DB --QAs--> Auth
```

### Dependency Graph
```
DB Agent ────────────────────> (parallel, no deps)
Auth Agent ──────────────────> History Agent uses get_current_user()
                               (History codes against interface while Auth implements)
```

## Section 1: Auth Pipeline

### Backend

1. **`text_routes.py`** — Add optional auth dependency via `get_current_user_optional()` that returns `User | None`. Anonymous users still get comparisons, just no history saved.

2. **`image_routes.py`** — Same optional auth dependency.

3. **`auth_routes.py`** — Add `get_current_user_optional()` variant of existing `get_current_user()`. Catches auth failures and returns `None` instead of 401.

### Frontend

4. **`api.ts`** — Add axios request interceptor to attach JWT from AsyncStorage on every request.

5. **`api.ts`** — Add axios response interceptor for 401s: attempt token refresh via `/api/v1/auth/refresh`, retry original request. On refresh failure, clear tokens.

No new tables or endpoints needed. Purely wires up existing code.

## Section 2: History Feature

### Backend

1. **`text_routes.py`** — After `compare_from_text()` succeeds, call `save_comparison()` with full response dict + user_id. Fire-and-forget — save failure must not break the comparison response.

2. **`image_routes.py`** — Same save logic after camera comparisons.

3. **`database_service.py`** — Update `save_comparison()`:
   - Accept `full_response: dict` (entire API response blob)
   - Accept `user_id: Optional[str]` (None for anonymous)
   - Accept `query: str` and `input_type: str` ("text" or "camera")
   - Write to updated `comparisons` table

4. **`routes.py`** — Update `GET /api/v1/comparisons/history` to use real auth instead of hardcoded dev user. Add optional `?search=` query param.

### Frontend

5. **`HistoryScreen.tsx`** — Update `HistoryItem` type to expect full response blob. Pass stored blob directly to `ResultsScreen` (no reconstruction needed — same shape as live response).

6. **`HistoryScreen.tsx`** — Add delete: swipe-to-delete or icon button. Backend: `DELETE /api/v1/comparisons/{id}` with auth check.

7. **`HistoryScreen.tsx`** — Add search/filter bar to filter history by product name.

## Section 3: Database Improvements

### Schema: `comparisons` table

Add columns:
- `full_response JSONB NOT NULL` — entire API response blob
- `query TEXT` — original search query
- `input_type TEXT DEFAULT 'text'` — "text" or "camera"
- `product_names TEXT[]` — product names array for indexing

Drop redundant columns: `products`, `winner_index`, `recommendation`, `key_differences`, `data_source`, `total_cost`, `image_urls` (all inside `full_response` now).

Add indexes:
- `GIN` on `product_names`
- `BTREE` on `(user_id, created_at DESC)`
- Full-text on `query`

### Wire up `search_logs`

- Add `log_search()` to `database_service.py` — writes on every comparison request (success or failure)
- Fields: `user_id`, `query`, `input_type`, `products_found`, `success`, `error_message`, `cost`, `duration_ms`
- Fire-and-forget, called from `text_routes.py` and `image_routes.py`

### Lightweight product dedup

- On each comparison, upsert to `products` by exact `canonical_name`
- Store `brand`, `category`, `last_seen_at`
- Add `product_ids UUID[]` to `comparisons` linking to product records
- Enables future analytics ("most compared products") without parsing JSONB

### Cleanup

- Remove dead functions in `database_service.py` for unused tables (`price_cache`, `daily_usage`) if confirmed dead
- Migration via SQL scripts applied through Supabase dashboard or MCP tool

## Section 4: Testing & QA

### Test targets (80% coverage for new code)

**Auth tests (~10):**
- `get_current_user_optional()`: valid token → User, no token → None, expired → None
- Axios interceptor: attaches token when present, skips when absent
- 401 triggers refresh, retries request; refresh failure clears tokens

**History tests (~15):**
- `save_comparison()`: stores full blob, handles None user_id
- Save failure doesn't break comparison response
- `GET /history`: returns only current user's, ordered by date DESC
- `DELETE /comparisons/{id}`: only own, 404 for others
- Search/filter by product name
- HistoryScreen passes blob to ResultsScreen without transformation

**DB tests (~12):**
- `log_search()`: correct fields, graceful failure
- `upsert_product()`: creates new, updates existing
- Product names index enables search
- `product_ids` links correctly
- Migrations are idempotent

### QA Protocol

- After completing their feature, each agent reads the other's code and runs their tests
- QA checks: correctness, error handling, no security holes (SQL injection, auth bypass), tests pass
- QA finds issues → sends work back with specific feedback
- All 3 agents must pass QA before team disbands
- Idle agents write additional tests to push toward 80% coverage
