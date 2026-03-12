# Design: Auth Fixes + Backend Cleanup + AI Efficiency

**Date:** 2026-03-12 (Session 22)
**Approach:** B — Bug Fixes + Cleanup (no new features)
**Execution:** 3 rounds of 2 Opus agents (sequential), Pro subscription limit-aware

---

## Problem Statement

Deep exploration of the SmartCompare codebase revealed:
- 3 auth bugs (password reset mismatch, missing data in responses, generic error messages)
- 1 critical dead route file (legacy routes.py crashes at runtime)
- Dead code in multiple files (unused endpoints, unused functions)
- Inaccurate AI cost tracking (hardcoded estimates off by 40-110% per call)

None of these are new features. All are fixes to existing broken/dead/inaccurate code.

---

## Section 1: Auth Fixes

### 1a. Password Reset Endpoint Mismatch

**Bug:** Frontend `authService.ts:~341` calls `/auth/reset-password` but backend endpoint is `/auth/password-reset`.

**Fix:**
- File: `SmartCompareApp/src/services/authService.ts`
- Change: `/auth/reset-password` → `/auth/password-reset`

**Test:** Unit test asserting the correct endpoint path is used.

### 1b. Categorize Auth Error Messages

**Problem:** `app/services/auth_service.py` catches `Exception` and passes raw Supabase error strings to users (e.g., "AuthError: Auth error occurred").

**Fix:** Wrap all `except Exception` blocks in auth_service.py with error categorization:
- Network/connection errors → "Connection failed. Please try again."
- Auth-specific errors (invalid credentials, expired token) → keep existing specific messages
- All other errors → "Something went wrong. Please try again later."

**Files:** `app/services/auth_service.py` — all functions that catch exceptions:
- `register_user()` (~line 68-74)
- `login_user()` (~line 121-125)
- `refresh_session()` (~line 160-165)
- `sign_in_with_social()` (~line 255-261)
- `change_user_password()` (~line 275-279)
- `update_user_email()` (~line 290-292)
- `update_user_profile()` (~line 302-304)
- `request_password_reset()` (~line 345-348)

**Pattern:**
```python
except Exception as e:
    error_msg = str(e).lower()
    if "invalid login credentials" in error_msg:
        return {"success": False, "error": "Invalid email or password"}
    elif any(term in error_msg for term in [
        "network", "connection", "timeout", "dns", "econnrefused",
        "socket hang up", "enotfound", "failed to fetch", "no network"
    ]):
        return {"success": False, "error": "Connection failed. Please try again."}
    else:
        logger.error(f"Auth error: {e}")
        return {"success": False, "error": "Something went wrong. Please try again later."}
```

### 1c. Return display_name + auth_provider in Auth Responses

**Problem:** Login/register/social responses don't include `display_name` or `auth_provider`. Frontend falls back to email prefix for display name.

**Fix:** In `auth_service.py`, after successful auth in `login_user()`, `register_user()`, and `sign_in_with_social()`, fetch user profile from `public.users` and include in response. Must be wrapped in try/except since profile may not exist yet (race condition on new registration):
```python
# After successful auth, fetch profile (graceful — never breaks auth response)
display_name = None
auth_provider = None
try:
    profile = admin.table("users").select("display_name, auth_provider").eq("id", user_id).single().execute()
    if profile.data:
        display_name = profile.data.get("display_name")
        auth_provider = profile.data.get("auth_provider")
except Exception as e:
    logger.warning(f"Could not fetch profile for {user_id}: {e}")

response["user"]["display_name"] = display_name
response["user"]["auth_provider"] = auth_provider
```

**Scope:** Only add fields to existing response — don't change response structure. Profile fetch failure must never break auth.

### 1d. Google OAuth — Document Manual Step

**Action:** Add code comment in `authService.ts` near Google sign-in config:
```typescript
// SETUP REQUIRED: Enable Google provider in Supabase Dashboard
// Project: qulajmyxdbdkchvecmvc → Authentication → Providers → Google
// Web Client ID: 21336192767-i9prqks93nrdmb9rg7ho2v1md9bgqgsv.apps.googleusercontent.com
```

**Manual step:** User will be notified during implementation to enable Google provider in Supabase Dashboard.

---

## Section 2: Backend Cleanup

### 2a. Legacy routes.py — Extract & Delete

**Problem:** `app/api/routes.py` imports dead services (`comparison_service`), all endpoints crash with TypeError at runtime. Documented as known bug.

**Steps:**
1. Scan routes.py for any logic NOT present in modern route files
2. If unique logic found → migrate to correct modern route file
3. Delete `app/api/routes.py`
4. Remove import + `app.include_router(router)` from `app/main.py` (~line 97-103)
5. Update/remove any tests referencing legacy route paths

**Expected finding:** No unique logic (all replaced by text_routes, image_routes, auth_routes). Straight deletion.

### 2b. Remove Dead Category-Specific Endpoints

**Problem:** `app/api/text_routes.py` lines ~409-426 define `/compare/electronics` and `/compare/grocery` endpoints that just call `text_compare()` without enforcing any category. Real category system uses `?selected_category=` query param.

**Fix:** Delete both endpoint handlers from `text_routes.py`.

### 2c. Remove Dead Functions from openai_service.py

**Problem:** `app/services/openai_service.py` lines ~165-385 contain 3 functions never called anywhere:
- `extract_price_from_search_results()`
- `estimate_price_fallback()`
- `generate_comparison()`

**Fix:** Delete all three functions. Keep `identify_products()` (active, used by image_routes).

### 2d. Verify Serper Cost Tracking Completeness

**Context:** The exploration agent flagged pharmacy targeted search (~line 1365 in `structured_comparison_service.py`) as missing cost tracking. Spec review found it IS already tracked.

**Action:** Backend-dev must verify all Serper calls in `structured_comparison_service.py` have corresponding `_track_cost()` calls. If any are genuinely missing, add them. If all are present, mark this as verified and move on. Do NOT add duplicate tracking — double-counting is worse than missing tracking.

**Note:** Section 3b will convert all `_track_cost(0.001)` Serper calls to `_track_serper_cost()` anyway.

### 2e. Normalize /me Endpoint Response

**Problem:** `app/api/auth_routes.py` `/me` endpoint (~lines 256-269) returns different response shapes depending on whether user profile exists in `public.users`.

**Fix:** Always return consistent shape (backward compatible — keep all existing fields):
```python
{
    "id": user_id,
    "email": email,
    "display_name": display_name or None,
    "auth_provider": auth_provider or None,
    "subscription_tier": subscription_tier or "free",
    "created_at": created_at or None,
    "preferences_completed": preferences_completed or False
}
```
When profile doesn't exist, use defaults (None/False/"free") instead of returning raw `current_user` dict. Keep `subscription_tier` and `created_at` for backward compatibility with frontend code that may depend on them.

---

## Section 3: AI Efficiency & Observability

### 3a. Actual Token-Based Cost Tracking

**Problem:** `structured_comparison_service.py` uses hardcoded cost approximations:
- `self._track_cost(0.0003)` for parsing (actual: $0.00012 — off by 60%)
- `self._track_cost(0.0005)` for specs (actual: $0.00070 — off by 40%)
- `self._track_cost(0.001)` for comparison (actual: $0.00165 — off by 65%)

Total happens to be accurate due to lucky cancellation, but individual tracking is misleading.

**Fix:**

1. Modify ALL 6 extraction functions in `extraction_service.py` to return token usage alongside results. Each returns a `(result, token_usage)` tuple:

**Functions to modify (all 5):**
- `parse_product_query()` — returns `(parsed_dict, usage)`
- `extract_specs()` — returns `(specs_dict, usage)`
- `extract_price()` — returns `(price_dict, usage)`
- `extract_price_from_training_data()` — returns `(price_dict, usage)`
- `extract_reviews()` — returns `(reviews_dict, usage)`
- `generate_comparison()` — returns `(comparison_dict, usage)`

**Pattern (apply to ALL functions above):**
```python
async def extract_specs(...) -> tuple[dict, dict]:
    response = await client.chat.completions.create(...)
    usage = {
        "prompt_tokens": response.usage.prompt_tokens,
        "completion_tokens": response.usage.completion_tokens
    }
    return parsed_result, usage
```

**Note:** Token usage from OpenAI's `response.usage` includes system prompt tokens — this is accurate for cost calculation purposes.

2. In `structured_comparison_service.py`, replace hardcoded costs:
```python
# Old:
specs = await extract_specs(...)
self._track_cost(0.0005)

# New:
specs, usage = await extract_specs(...)
self._track_gpt_cost(usage)
```

3. New helper method:
```python
def _track_gpt_cost(self, usage: dict):
    input_cost = (usage["prompt_tokens"] * 0.15) / 1_000_000
    output_cost = (usage["completion_tokens"] * 0.60) / 1_000_000
    self.total_cost += input_cost + output_cost
    self.gpt_calls += 1
```

**gpt-4o-mini pricing (as of Mar 2026):**
- Input: $0.15 per 1M tokens
- Output: $0.60 per 1M tokens

### 3b. Separate GPT vs Serper Call Counters

**Problem:** Single `self.api_calls` counter doesn't distinguish call types.

**Fix:**
1. In `structured_comparison_service.py`, replace `self.api_calls = 0` with:
```python
self.gpt_calls = 0
self.serper_calls = 0
```

2. `_track_gpt_cost()` increments `self.gpt_calls` (defined in Section 3a)

3. New `_track_serper_cost()` method replaces all Serper `_track_cost(0.001)` calls:
```python
def _track_serper_cost(self):
    """Track a Serper API call ($0.001 per call, fixed pricing)."""
    self.total_cost += 0.001
    self.serper_calls += 1
```

4. Find and replace ALL `self._track_cost(0.001)` calls in `structured_comparison_service.py` with `self._track_serper_cost()`. The old `_track_cost()` method can be deleted once all calls are migrated.

4. Response metadata includes both:
```python
"api_calls": self.gpt_calls + self.serper_calls,  # backward compat
"gpt_calls": self.gpt_calls,
"serper_calls": self.serper_calls,
```

5. Reset both in `compare_from_text()` alongside existing state reset.

---

## Execution Plan: 3 Rounds of 2 Opus Agents

### Why 2 Agents Per Round (Not 4)
- Pro subscription: 4 Opus agents spike to 60% token usage in 30 seconds → immediate pause
- Sessions 20-21 proved 2-agent sequential phases work within Pro limits
- Fresh context per round prevents bloat

### Round 1: Auth Fixes (Section 1)

| Agent | Role | Tasks |
|-------|------|-------|
| `auth-dev` | Implement 1a, 1b, 1c, 1d | Edit authService.ts, auth_service.py, auth_routes.py |
| `auth-qa` | Tests + QA | Write tests for password reset, error categorization, response fields. QA auth-dev's code. |

**Files touched:** authService.ts, auth_service.py, auth_routes.py
**Checkpoint:** Write to `docs/session22_progress.md` after completion
**Shutdown** both agents after QA passes

### Round 2: Backend Cleanup (Section 2)

| Agent | Role | Tasks |
|-------|------|-------|
| `backend-dev` | Implement 2a, 2b, 2c, 2d, 2e | Delete routes.py, edit text_routes.py, openai_service.py, structured_comparison_service.py, auth_routes.py |
| `backend-qa` | Tests + QA | Verify deletions don't break imports, test /me response normalization, verify cost tracking addition. QA backend-dev's code. |

**Files touched:** routes.py (delete), main.py, text_routes.py, openai_service.py, structured_comparison_service.py, auth_routes.py
**Checkpoint:** Update `docs/session22_progress.md`
**Shutdown** both agents after QA passes

### Round 3: AI Efficiency (Section 3)

| Agent | Role | Tasks |
|-------|------|-------|
| `ai-dev` | Implement 3a, 3b | Edit extraction_service.py, structured_comparison_service.py |
| `ai-qa` | Tests + QA | Write tests for token-based tracking, verify cost calculations, test counter separation. QA ai-dev's code. |

**Files touched:** extraction_service.py, structured_comparison_service.py
**Checkpoint:** Update `docs/session22_progress.md`
**Shutdown** both agents after QA passes

### Each Round's Workflow

```
1. dev implements all changes for the section
2. dev writes checkpoint to docs/session22_progress.md
3. qa writes red-green tests (80% coverage target on changed code)
4. qa reviews dev's code — sends back with specific issues if subpar
5. dev fixes any QA feedback
6. dev reviews qa's test files
7. Both confirm: all tests pass, no regressions
8. Orchestrator shuts down both agents
9. Orchestrator verifies completion, updates CONTEXT_SESSION_LOG.md
10. Spawn fresh pair for next round
```

### Context Management (Token Limit Prevention)

- **Lean prompts:** Each agent gets ONLY the file paths and change descriptions for their section
- **No CLAUDE.md/MEMORY.md injection:** Agents get targeted instructions, not full project context
- **Checkpoint file:** `docs/session22_progress.md` — agents write status after each sub-task
- **If limits hit mid-round:** Agent reads checkpoint on resume instead of re-deriving context
- **Sequential only:** Never 2 agents actively working simultaneously

### QA Rules

1. Features must be 100% complete before agent pair shuts down
2. Each member QAs the other's work (dev reviews tests, qa reviews implementation)
3. Subpar or missed work gets sent back with specific issues
4. Idle agents write red-green tests targeting 80% coverage on changed code
5. `docs/session22_progress.md` updated after each major sub-task completion

---

## Files Changed Summary

| File | Section | Change |
|------|---------|--------|
| `SmartCompareApp/src/services/authService.ts` | 1a, 1d | Fix endpoint path, add Google OAuth comment |
| `app/services/auth_service.py` | 1b, 1c | Error categorization, add display_name/auth_provider to responses |
| `app/api/auth_routes.py` | 2e | Normalize /me response |
| `app/api/routes.py` | 2a | DELETE entire file |
| `app/main.py` | 2a | Remove legacy router import + include |
| `app/api/text_routes.py` | 2b | Remove dead category endpoints |
| `app/services/openai_service.py` | 2c | Remove 3 dead functions |
| `app/services/structured_comparison_service.py` | 2d, 3a, 3b | Add missing tracking, token-based costs, split counters |
| `app/services/extraction_service.py` | 3a | Return token usage from GPT calls |
| `docs/session22_progress.md` | All | Checkpoint file (new) |
| `tests/test_auth_interceptor.py` | 1 | Update existing file — add tests for password reset path, error categorization, display_name/auth_provider in responses |
| `tests/test_backend_cleanup.py` | 2 | NEW file — tests for routes.py deletion (no import errors), /me normalization, dead code removal verification |
| `tests/test_cost_tracking.py` | 3 | NEW file — tests for token-based cost calculation, GPT vs Serper counter separation, backward-compat api_calls field |

---

## Out of Scope (Explicitly Deferred)

- Social account linking (new feature, not a fix)
- Email verification flow (Supabase config dependent)
- expo-secure-store for token encryption (new dependency)
- Budget alert system (new feature)
- Retry logic with exponential backoff (new feature)
- Apple Sign-In testing (needs $99/year subscription)
- Legacy comparison_service.py cleanup (dies with routes.py deletion)

---

## Success Criteria

1. Password reset works end-to-end (frontend → backend → email sent)
2. Auth errors show user-friendly messages, not raw Supabase strings
3. Login/register responses include display_name and auth_provider
4. Legacy routes.py deleted, no import errors
5. No dead endpoints or functions remain in touched files
6. AI cost tracking uses actual OpenAI token counts
7. GPT and Serper calls tracked separately in response metadata
8. All existing tests pass (637 baseline)
9. New tests achieve 80%+ coverage on changed code
10. `api_calls` backward compatible (sum of gpt_calls + serper_calls)
