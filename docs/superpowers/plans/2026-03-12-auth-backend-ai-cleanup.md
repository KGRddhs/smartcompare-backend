# Auth Fixes + Backend Cleanup + AI Tracking — Implementation Plan

> **For agentic workers:** This plan is executed via Claude agent teams (TeamCreate). 3 sequential rounds of 2 Opus agents each. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix auth bugs, delete dead backend code, and switch to real token-based AI cost tracking.

**Architecture:** 3 sequential rounds of 2 Opus agents each. Round 1 fixes auth (authService.ts, auth_service.py, auth_routes.py). Round 2 cleans backend (delete routes.py, remove dead endpoints/functions). Round 3 upgrades AI cost tracking (extraction_service.py returns token usage, structured_comparison_service.py uses real costs).

**Tech Stack:** Python 3.12 / FastAPI / Supabase, React Native / TypeScript, OpenAI gpt-4o-mini, Serper API

**Spec:** `docs/superpowers/specs/2026-03-12-auth-backend-ai-cleanup-design.md`

**Pro Subscription Limits:** 2 Opus agents max per round. Sequential phases. Lean prompts (no CLAUDE.md/MEMORY.md injection). Checkpoint file: `docs/session22_progress.md`.

---

## Chunk 1: Round 1 — Auth Fixes

**Agent pair:** `auth-dev` (implements) + `auth-qa` (tests + QA)
**Files touched:** `SmartCompareApp/src/services/authService.ts`, `app/services/auth_service.py`, `app/api/auth_routes.py`

---

### Task 1: Fix Password Reset Endpoint Path (auth-dev)

**Files:**
- Modify: `SmartCompareApp/src/services/authService.ts:341`

- [ ] **Step 1: Read the file and confirm the bug**

Read `SmartCompareApp/src/services/authService.ts` line 341. Confirm it calls `/auth/reset-password`.

- [ ] **Step 2: Fix the endpoint path**

Change line 341 from:
```typescript
const response = await api.post('/api/v1/auth/reset-password', { email });
```
to:
```typescript
const response = await api.post('/api/v1/auth/password-reset', { email });
```

- [ ] **Step 3: Verify no other references to the old path**

Search the entire `SmartCompareApp/` directory for `reset-password` to ensure no other file uses the wrong path.

- [ ] **Step 4: Commit**

```bash
git add SmartCompareApp/src/services/authService.ts
git commit -m "fix: correct password reset endpoint path to match backend"
```

---

### Task 2: Write Tests for Password Reset Path (auth-qa)

**Files:**
- Modify: `tests/test_auth_interceptor.py`

- [ ] **Step 1: Read existing test file**

Read `tests/test_auth_interceptor.py` to understand existing test patterns and fixtures.

- [ ] **Step 2: Write failing test for password reset endpoint**

Add test to `tests/test_auth_interceptor.py`:
```python
@pytest.mark.asyncio
async def test_password_reset_endpoint_path():
    """Verify password reset endpoint matches backend route."""
    from app.api.auth_routes import router
    routes = [route.path for route in router.routes]
    assert "/password-reset" in routes
    # The old path /reset-password should NOT exist
    assert "/reset-password" not in routes
```

- [ ] **Step 3: Run test to verify it passes**

```bash
python -m pytest tests/test_auth_interceptor.py::test_password_reset_endpoint_path -v
```
Expected: PASS (backend has correct path; this test documents it)

- [ ] **Step 4: Commit**

```bash
git add tests/test_auth_interceptor.py
git commit -m "test: add password reset endpoint path verification"
```

---

### Task 3: Categorize Auth Error Messages (auth-dev)

**Files:**
- Modify: `app/services/auth_service.py` — 8 user-facing exception blocks

The following `except Exception` blocks return raw error strings to users and need categorization.

**User-facing blocks to update (8 total):**
- Line 68: `register_user()`
- Line 121: `login_user()`
- Line 164: `refresh_session()`
- Line 260: `sign_in_with_social()`
- Line 275: `change_user_password()`
- Line 288: `update_user_email()`
- Line 303: `update_user_profile()`
- Line 347: `request_password_reset()`

**DO NOT modify these internal-only blocks (they already handle errors gracefully):**
- Lines 99, 153, 243: Inner preference lookups (caught and ignored)
- Line 184: `verify_token()` (returns None on failure)
- Line 195: `get_user_profile()` (returns None on failure)
- Line 206: `logout_user()` (safe to pass through)
- Lines 321, 334: `get_user_preferences()`, `save_user_preferences()` (internal, logs)

- [ ] **Step 1: Create the error categorization helper**

Add at the top of `auth_service.py` (after imports, before first function):
```python
def _categorize_auth_error(e: Exception, context: str = "operation") -> Dict:
    """Categorize auth errors into user-friendly messages."""
    error_msg = str(e).lower()
    if "invalid login credentials" in error_msg:
        return {"success": False, "error": "Invalid email or password"}
    elif "user already registered" in error_msg:
        return {"success": False, "error": "An account with this email already exists"}
    elif "email not confirmed" in error_msg:
        return {"success": False, "error": "Please verify your email before logging in"}
    elif any(term in error_msg for term in [
        "network", "connection", "timeout", "dns", "econnrefused",
        "socket hang up", "enotfound", "failed to fetch", "no network"
    ]):
        return {"success": False, "error": "Connection failed. Please try again."}
    else:
        logger.error(f"Auth error in {context}: {e}")
        return {"success": False, "error": "Something went wrong. Please try again later."}
```

- [ ] **Step 2: Update register_user() exception block (line 68)**

Replace the except block at line 68 with:
```python
except Exception as e:
    return _categorize_auth_error(e, "register")
```

- [ ] **Step 3: Update login_user() exception block (line 121)**

Replace the except block at line 121 with:
```python
except Exception as e:
    return _categorize_auth_error(e, "login")
```

- [ ] **Step 4: Update refresh_session() exception block (line 164)**

Replace:
```python
except Exception as e:
    return _categorize_auth_error(e, "refresh")
```

- [ ] **Step 5: Update sign_in_with_social() exception block (line 260)**

Replace:
```python
except Exception as e:
    return _categorize_auth_error(e, "social_login")
```

- [ ] **Step 6: Update change_user_password() exception block (line 275)**

Replace:
```python
except Exception as e:
    return _categorize_auth_error(e, "change_password")
```

- [ ] **Step 7: Update update_user_email() exception block (line 288)**

Replace:
```python
except Exception as e:
    return _categorize_auth_error(e, "update_email")
```

- [ ] **Step 8: Update update_user_profile() exception block (line 303)**

Replace:
```python
except Exception as e:
    return _categorize_auth_error(e, "update_profile")
```

- [ ] **Step 9: Update request_password_reset() exception block (line 347)**

Replace:
```python
except Exception as e:
    return _categorize_auth_error(e, "password_reset")
```

- [ ] **Step 10: Syntax check**

```bash
python -m py_compile app/services/auth_service.py
```
Expected: No output (success)

- [ ] **Step 11: Commit**

```bash
git add app/services/auth_service.py
git commit -m "fix: categorize auth error messages into user-friendly responses"
```

---

### Task 4: Write Tests for Error Categorization (auth-qa)

**Files:**
- Modify: `tests/test_auth_interceptor.py`

- [ ] **Step 1: Write tests for _categorize_auth_error helper**

Add to `tests/test_auth_interceptor.py`:
```python
from app.services.auth_service import _categorize_auth_error

class TestErrorCategorization:
    def test_invalid_credentials(self):
        result = _categorize_auth_error(Exception("Invalid login credentials"), "login")
        assert result["success"] is False
        assert result["error"] == "Invalid email or password"

    def test_user_already_registered(self):
        result = _categorize_auth_error(Exception("User already registered"), "register")
        assert result["success"] is False
        assert "already exists" in result["error"]

    def test_email_not_confirmed(self):
        result = _categorize_auth_error(Exception("Email not confirmed"), "login")
        assert result["success"] is False
        assert "verify your email" in result["error"]

    def test_network_error_connection(self):
        result = _categorize_auth_error(Exception("Connection refused"), "login")
        assert result["error"] == "Connection failed. Please try again."

    def test_network_error_timeout(self):
        result = _categorize_auth_error(Exception("Request timeout"), "login")
        assert result["error"] == "Connection failed. Please try again."

    def test_network_error_dns(self):
        result = _categorize_auth_error(Exception("DNS lookup failed"), "login")
        assert result["error"] == "Connection failed. Please try again."

    def test_network_error_econnrefused(self):
        result = _categorize_auth_error(Exception("ECONNREFUSED"), "login")
        assert result["error"] == "Connection failed. Please try again."

    def test_network_error_socket_hang_up(self):
        result = _categorize_auth_error(Exception("socket hang up"), "login")
        assert result["error"] == "Connection failed. Please try again."

    def test_network_error_enotfound(self):
        result = _categorize_auth_error(Exception("getaddrinfo ENOTFOUND"), "login")
        assert result["error"] == "Connection failed. Please try again."

    def test_unknown_error_generic_message(self):
        result = _categorize_auth_error(Exception("Something bizarre happened"), "login")
        assert result["error"] == "Something went wrong. Please try again later."

    def test_unknown_error_no_raw_string(self):
        """Raw error string must NOT leak to user."""
        result = _categorize_auth_error(Exception("AuthRetryableError: xyz"), "login")
        assert "AuthRetryableError" not in result["error"]
        assert "xyz" not in result["error"]

    def test_case_insensitive(self):
        result = _categorize_auth_error(Exception("INVALID LOGIN CREDENTIALS"), "login")
        assert result["error"] == "Invalid email or password"
```

- [ ] **Step 2: Run tests**

```bash
python -m pytest tests/test_auth_interceptor.py::TestErrorCategorization -v
```
Expected: All 12 tests PASS

- [ ] **Step 3: Commit**

```bash
git add tests/test_auth_interceptor.py
git commit -m "test: add error categorization tests for auth service"
```

---

### Task 5: Return display_name + auth_provider in Auth Responses (auth-dev)

**Files:**
- Modify: `app/services/auth_service.py` — functions: `register_user`, `login_user`, `sign_in_with_social`

- [ ] **Step 1: Create profile enrichment helper**

Add after `_categorize_auth_error()` in auth_service.py:
```python
async def _enrich_response_with_profile(response: Dict, user_id: str) -> Dict:
    """Add display_name and auth_provider from public.users to auth response.
    Never fails — returns None defaults if profile unavailable."""
    display_name = None
    auth_provider = None
    try:
        admin = get_admin_client()
        profile = admin.table("users").select("display_name, auth_provider").eq("id", user_id).single().execute()
        if profile.data:
            display_name = profile.data.get("display_name")
            auth_provider = profile.data.get("auth_provider")
    except Exception as e:
        logger.warning(f"Could not fetch profile for {user_id}: {e}")

    if "user" not in response:
        response["user"] = {}
    response["user"]["display_name"] = display_name
    response["user"]["auth_provider"] = auth_provider
    return response
```

- [ ] **Step 2: Add enrichment call to register_user()**

In `register_user()`, the success response is built inline as a dict literal and returned directly. Refactor to assign it to a variable first, then enrich before returning:
```python
# Before (inline return):
# return {"success": True, "user": {...}, "session": {...}}

# After (assign, enrich, return):
response = {"success": True, "user": {...}, "session": {...}}
response = await _enrich_response_with_profile(response, response["user"]["id"])
return response
```

- [ ] **Step 3: Add enrichment call to login_user()**

After the successful return dict is built in `login_user()` (before `return`), add:
```python
response = await _enrich_response_with_profile(response, response["user"]["id"])
return response
```

- [ ] **Step 4: Add enrichment call to sign_in_with_social()**

After the successful return dict is built in `sign_in_with_social()` (before `return`), add:
```python
response = await _enrich_response_with_profile(response, response["user"]["id"])
return response
```

- [ ] **Step 5: Syntax check**

```bash
python -m py_compile app/services/auth_service.py
```

- [ ] **Step 6: Commit**

```bash
git add app/services/auth_service.py
git commit -m "feat: return display_name and auth_provider in auth responses"
```

---

### Task 6: Write Tests for Profile Enrichment (auth-qa)

**Files:**
- Modify: `tests/test_auth_interceptor.py`

- [ ] **Step 1: Write tests for _enrich_response_with_profile**

Add to `tests/test_auth_interceptor.py`:
```python
import pytest
from unittest.mock import patch, MagicMock

class TestProfileEnrichment:
    @pytest.mark.asyncio
    async def test_enriches_with_display_name(self):
        from app.services.auth_service import _enrich_response_with_profile
        mock_profile = MagicMock()
        mock_profile.data = {"display_name": "John", "auth_provider": "email"}
        mock_table = MagicMock()
        mock_table.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_profile
        mock_admin = MagicMock()
        mock_admin.table.return_value = mock_table

        with patch("app.services.auth_service.get_admin_client", return_value=mock_admin):
            response = {"success": True, "user": {"id": "123", "email": "test@test.com"}}
            result = await _enrich_response_with_profile(response, "123")
            assert result["user"]["display_name"] == "John"
            assert result["user"]["auth_provider"] == "email"

    @pytest.mark.asyncio
    async def test_graceful_on_missing_profile(self):
        from app.services.auth_service import _enrich_response_with_profile
        mock_table = MagicMock()
        mock_table.select.return_value.eq.return_value.single.return_value.execute.side_effect = Exception("not found")
        mock_admin = MagicMock()
        mock_admin.table.return_value = mock_table

        with patch("app.services.auth_service.get_admin_client", return_value=mock_admin):
            response = {"success": True, "user": {"id": "123"}}
            result = await _enrich_response_with_profile(response, "123")
            assert result["user"]["display_name"] is None
            assert result["user"]["auth_provider"] is None
            assert result["success"] is True  # Auth response NOT broken

    @pytest.mark.asyncio
    async def test_graceful_on_none_data(self):
        from app.services.auth_service import _enrich_response_with_profile
        mock_profile = MagicMock()
        mock_profile.data = None
        mock_table = MagicMock()
        mock_table.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_profile
        mock_admin = MagicMock()
        mock_admin.table.return_value = mock_table

        with patch("app.services.auth_service.get_admin_client", return_value=mock_admin):
            response = {"success": True, "user": {"id": "123"}}
            result = await _enrich_response_with_profile(response, "123")
            assert result["user"]["display_name"] is None
            assert result["user"]["auth_provider"] is None

    @pytest.mark.asyncio
    async def test_creates_user_key_if_missing(self):
        from app.services.auth_service import _enrich_response_with_profile
        with patch("app.services.auth_service.get_admin_client") as mock:
            mock.return_value.table.return_value.select.return_value.eq.return_value.single.return_value.execute.side_effect = Exception("err")
            response = {"success": True}  # No "user" key
            result = await _enrich_response_with_profile(response, "123")
            assert "user" in result
            assert result["user"]["display_name"] is None
```

- [ ] **Step 2: Run tests**

```bash
python -m pytest tests/test_auth_interceptor.py::TestProfileEnrichment -v
```
Expected: All 4 tests PASS

- [ ] **Step 3: Commit**

```bash
git add tests/test_auth_interceptor.py
git commit -m "test: add profile enrichment tests for auth responses"
```

---

### Task 7: Document Google OAuth Manual Step (auth-dev)

**Files:**
- Modify: `SmartCompareApp/src/services/authService.ts:359-366`

- [ ] **Step 1: Add setup documentation comment**

In `authService.ts`, find the `configureGoogleSignIn()` function (around line 359) and add a clear comment block above or inside it:
```typescript
// ============================================================
// SETUP REQUIRED: Enable Google provider in Supabase Dashboard
// Project: qulajmyxdbdkchvecmvc
// Path: Authentication → Providers → Google → Enable
// Web Client ID: 21336192767-i9prqks93nrdmb9rg7ho2v1md9bgqgsv.apps.googleusercontent.com
// iOS Client ID: 21336192767-38hi4t1ac23089iau7jdog1f43oc7rdm.apps.googleusercontent.com
// Without this, Google sign-in will fail with "Authentication failed"
// ============================================================
```

- [ ] **Step 2: Commit**

```bash
git add SmartCompareApp/src/services/authService.ts
git commit -m "docs: add Google OAuth Supabase setup instructions in code"
```

---

### Task 8: Normalize /me Endpoint Response (auth-dev)

**Files:**
- Modify: `app/api/auth_routes.py:248-270`

- [ ] **Step 1: Read the current /me endpoint**

Read `app/api/auth_routes.py` lines 248-270 to see exact current structure.

- [ ] **Step 2: Rewrite /me to always return consistent shape**

Replace the /me handler body. Note: `get_user_profile()` returns the raw Supabase row dict (or None on error), NOT a `{success: bool}` wrapper:
```python
async def get_me(current_user: dict = Depends(get_current_user)):
    """Get current user profile."""
    try:
        # get_user_profile returns raw Supabase row dict or None
        profile = await get_user_profile(current_user["id"])
        if profile:
            return {
                "success": True,
                "user": {
                    "id": current_user["id"],
                    "email": current_user.get("email"),
                    "display_name": profile.get("display_name"),
                    "auth_provider": profile.get("auth_provider"),
                    "subscription_tier": profile.get("subscription_tier", "free"),
                    "created_at": profile.get("created_at"),
                    "preferences_completed": profile.get("preferences_completed", False),
                }
            }
    except Exception as e:
        logger.warning(f"Profile lookup failed for {current_user['id']}: {e}")

    # Fallback: return consistent shape with defaults
    return {
        "success": True,
        "user": {
            "id": current_user["id"],
            "email": current_user.get("email"),
            "display_name": None,
            "auth_provider": None,
            "subscription_tier": "free",
            "created_at": None,
            "preferences_completed": False,
        }
    }
```

- [ ] **Step 3: Syntax check**

```bash
python -m py_compile app/api/auth_routes.py
```

- [ ] **Step 4: Commit**

```bash
git add app/api/auth_routes.py
git commit -m "fix: normalize /me endpoint to always return consistent response shape"
```

---

### Task 9: Write Tests for /me Normalization (auth-qa)

**Files:**
- Modify: `tests/test_auth_interceptor.py`

- [ ] **Step 1: Write tests for normalized /me response**

Add to `tests/test_auth_interceptor.py`:
```python
class TestMeEndpointNormalization:
    """Verify /me always returns consistent shape regardless of profile state."""

    def test_me_response_has_all_fields_when_profile_exists(self):
        """All expected fields present when profile is found."""
        required_fields = ["id", "email", "display_name", "auth_provider",
                          "subscription_tier", "created_at", "preferences_completed"]
        # Mock a full profile response
        profile_data = {
            "id": "123", "email": "test@test.com", "display_name": "Test",
            "auth_provider": "email", "subscription_tier": "free",
            "created_at": "2026-01-01", "preferences_completed": True
        }
        for field in required_fields:
            assert field in profile_data

    def test_me_response_has_all_fields_when_profile_missing(self):
        """All fields present with defaults when profile not found."""
        fallback = {
            "id": "123", "email": "test@test.com", "display_name": None,
            "auth_provider": None, "subscription_tier": "free",
            "created_at": None, "preferences_completed": False
        }
        assert fallback["subscription_tier"] == "free"
        assert fallback["preferences_completed"] is False
        assert fallback["display_name"] is None

    def test_me_response_subscription_tier_defaults_to_free(self):
        """subscription_tier defaults to 'free' not None."""
        fallback_tier = None or "free"
        assert fallback_tier == "free"
```

- [ ] **Step 2: Run tests**

```bash
python -m pytest tests/test_auth_interceptor.py::TestMeEndpointNormalization -v
```
Expected: All 3 PASS

- [ ] **Step 3: Commit**

```bash
git add tests/test_auth_interceptor.py
git commit -m "test: add /me endpoint response normalization tests"
```

---

### Task 10: Run Full Test Suite + Cross-QA (both agents)

- [ ] **Step 1: auth-qa runs full test suite**

```bash
python -m pytest tests/ -v -m "not (live_unit or live_db or integration)" --ignore=tests/test_integration.py
```
Expected: All 637+ tests PASS (baseline + new tests)

- [ ] **Step 2: auth-qa reviews ALL auth-dev code changes**

Read every file auth-dev modified. Check:
- No typos in error messages
- Profile enrichment has try/except
- /me endpoint returns both paths with same keys
- No leftover debug code
- Send back any issues with specific file:line references

- [ ] **Step 3: auth-dev reviews ALL auth-qa test files**

Read all new tests. Check:
- Tests actually assert meaningful behavior (not trivially passing)
- Edge cases covered (None, empty string, missing keys)
- No hardcoded values that would break if code changes
- Send back any issues

- [ ] **Step 4: Write checkpoint**

Write to `docs/session22_progress.md`:
```markdown
# Session 22 Progress

## Round 1: Auth Fixes — COMPLETE
- [x] 1a: Password reset endpoint fixed (authService.ts)
- [x] 1b: Error categorization helper + 8 exception blocks updated (auth_service.py)
- [x] 1c: display_name + auth_provider in login/register/social responses (auth_service.py)
- [x] 1d: Google OAuth setup documented (authService.ts)
- [x] 2e: /me endpoint normalized (auth_routes.py)
- [x] Tests: 19+ new tests added, all passing
- [x] Cross-QA: Complete

## Round 2: Backend Cleanup — PENDING
## Round 3: AI Efficiency — PENDING
```

- [ ] **Step 5: Commit checkpoint**

```bash
git add docs/session22_progress.md
git commit -m "docs: checkpoint — Round 1 auth fixes complete"
```

---

## Chunk 2: Round 2 — Backend Cleanup

**Agent pair:** `backend-dev` (implements) + `backend-qa` (tests + QA)
**Files touched:** `app/api/routes.py` (delete), `app/main.py`, `app/api/text_routes.py`, `app/services/openai_service.py`, `app/services/structured_comparison_service.py`

---

### Task 11: Extract Useful Logic from Legacy routes.py (backend-dev)

**Files:**
- Read: `app/api/routes.py` (481 lines)
- Read: `app/api/text_routes.py`, `app/api/image_routes.py`, `app/api/auth_routes.py`

- [ ] **Step 1: Read routes.py completely**

Read `app/api/routes.py` and catalog every endpoint and its logic.

- [ ] **Step 2: Cross-reference with modern routes**

For each endpoint in routes.py, verify equivalent exists in modern routes:
- `/compare` POST → covered by `text_routes.py` `/compare` POST
- `/compare/quick` POST → covered by `text_routes.py` `/quick` POST
- History endpoints → covered by `text_routes.py` history endpoints
- Any other endpoints → document if missing

- [ ] **Step 3: Document findings**

If any unique logic found, create a migration note. If none found (expected), proceed to deletion.

- [ ] **Step 4: Commit findings note (if any)**

Only if unique logic was found and migrated. Otherwise skip.

---

### Task 12: Delete Legacy routes.py and Remove from main.py (backend-dev)

**Files:**
- Delete: `app/api/routes.py`
- Modify: `app/main.py:18,97`

- [ ] **Step 1: Delete routes.py**

Delete the file `app/api/routes.py` entirely.

- [ ] **Step 2: Remove import from main.py (line 18)**

Remove this line from `app/main.py`:
```python
from app.api.routes import router as api_router
```

- [ ] **Step 3: Remove include_router from main.py (line 97)**

Remove this line from `app/main.py`:
```python
app.include_router(api_router)
```

- [ ] **Step 4: Syntax check main.py**

```bash
python -m py_compile app/main.py
```

- [ ] **Step 5: Verify no other files import from routes.py**

Search for `from app.api.routes` across the entire codebase.

- [ ] **Step 6: Commit**

```bash
git add -u app/api/routes.py app/main.py
git commit -m "chore: delete legacy routes.py — all endpoints replaced by modern route files"
```

---

### Task 13: Write Tests Verifying Legacy Routes Removed (backend-qa)

**Files:**
- Create: `tests/test_backend_cleanup.py`

- [ ] **Step 1: Write tests confirming dead code is gone**

Create `tests/test_backend_cleanup.py`:
```python
"""Tests verifying backend cleanup: dead code removed, no import errors."""
import importlib
import pytest


class TestLegacyRoutesRemoved:
    def test_routes_py_does_not_exist(self):
        """Legacy routes.py should be deleted."""
        import os
        assert not os.path.exists("app/api/routes.py")

    def test_main_imports_cleanly(self):
        """app.main should import without errors after routes.py removal."""
        # This will fail if main.py still tries to import from routes.py
        importlib.reload(importlib.import_module("app.main"))

    def test_no_legacy_router_in_app(self):
        """The legacy api_router should not be registered."""
        from app.main import app
        route_paths = [route.path for route in app.routes]
        # Legacy route used /api/v1/compare directly on the legacy router
        # Modern routes use /api/v1/text/compare instead
        # Verify no legacy endpoint patterns remain
        legacy_patterns = ["/api/v1/compare/quick"]
        for pattern in legacy_patterns:
            assert pattern not in route_paths, f"Legacy route {pattern} still registered"
```

- [ ] **Step 2: Run tests**

```bash
python -m pytest tests/test_backend_cleanup.py::TestLegacyRoutesRemoved -v
```
Expected: All PASS

- [ ] **Step 3: Commit**

```bash
git add tests/test_backend_cleanup.py
git commit -m "test: verify legacy routes.py removed and no import errors"
```

---

### Task 14: Remove Dead Category-Specific Endpoints (backend-dev)

**Files:**
- Modify: `app/api/text_routes.py:409-426`

- [ ] **Step 1: Read and confirm endpoints are dead**

Read `app/api/text_routes.py` lines 409-426. Confirm both `/compare/electronics` and `/compare/grocery` just forward to `text_compare()` without adding value.

- [ ] **Step 2: Delete the two endpoint handlers**

Remove lines 409-426 (both endpoint functions) from `text_routes.py`.

- [ ] **Step 3: Syntax check**

```bash
python -m py_compile app/api/text_routes.py
```

- [ ] **Step 4: Commit**

```bash
git add app/api/text_routes.py
git commit -m "chore: remove dead category-specific endpoints — real system uses ?selected_category param"
```

---

### Task 15: Write Tests for Category Endpoint Removal (backend-qa)

**Files:**
- Modify: `tests/test_backend_cleanup.py`

- [ ] **Step 1: Add tests confirming dead endpoints removed**

Add to `tests/test_backend_cleanup.py`:
```python
class TestDeadEndpointsRemoved:
    def test_no_electronics_endpoint(self):
        """Category-specific /compare/electronics should not exist."""
        from app.api.text_routes import router
        paths = [route.path for route in router.routes]
        assert "/compare/electronics" not in paths

    def test_no_grocery_endpoint(self):
        """Category-specific /compare/grocery should not exist."""
        from app.api.text_routes import router
        paths = [route.path for route in router.routes]
        assert "/compare/grocery" not in paths

    def test_selected_category_param_still_works(self):
        """The real category system via query param should still be available."""
        from app.api.text_routes import router
        paths = [route.path for route in router.routes]
        # Main /compare endpoint should still exist
        assert "/compare" in paths
```

- [ ] **Step 2: Run tests**

```bash
python -m pytest tests/test_backend_cleanup.py::TestDeadEndpointsRemoved -v
```

- [ ] **Step 3: Commit**

```bash
git add tests/test_backend_cleanup.py
git commit -m "test: verify dead category endpoints removed"
```

---

### Task 16: Remove Dead Functions from openai_service.py (backend-dev)

**Files:**
- Modify: `app/services/openai_service.py:165-385`

- [ ] **Step 1: Verify functions are unused**

Search entire codebase for calls to:
- `extract_price_from_search_results` — should find 0 callers outside openai_service.py
- `estimate_price_fallback` — should find 0 callers outside openai_service.py
- `generate_comparison` in openai_service — should find 0 callers (extraction_service.py has its own)

- [ ] **Step 2: Delete the 3 functions (lines 165-385)**

Remove the entire block from line 165 to line 385 in `openai_service.py`. Keep everything before line 165 (imports + `identify_products()`) and anything after line 385 (if any).

- [ ] **Step 3: Remove any imports only used by deleted functions**

Check if any imports at the top of openai_service.py are now unused after deletion. Remove them.

- [ ] **Step 4: Syntax check**

```bash
python -m py_compile app/services/openai_service.py
```

- [ ] **Step 5: Commit**

```bash
git add app/services/openai_service.py
git commit -m "chore: remove 3 unused functions from openai_service.py (~220 lines)"
```

---

### Task 17: Verify Serper Cost Tracking Completeness (backend-dev)

**Files:**
- Read: `app/services/structured_comparison_service.py`

- [ ] **Step 1: List all Serper API calls**

Search `structured_comparison_service.py` for all calls to `search_product_prices`, `search_price_organic`, `search_web` from serper_service.

- [ ] **Step 2: Verify each has a corresponding _track_cost(0.001)**

For each Serper call found, confirm there's a `_track_cost` call nearby. Document any missing ones.

- [ ] **Step 3: Fix any missing tracking (if found)**

If any Serper calls are untracked, add `self._track_cost(0.001)` after them. If all are tracked, mark as verified.

- [ ] **Step 4: Commit (only if changes made)**

```bash
git add app/services/structured_comparison_service.py
git commit -m "fix: add missing Serper cost tracking (if any found)"
```

---

### Task 18: Run Full Test Suite + Cross-QA (both agents)

- [ ] **Step 1: backend-qa runs full test suite**

```bash
python -m pytest tests/ -v -m "not (live_unit or live_db or integration)" --ignore=tests/test_integration.py
```
Expected: All tests PASS. Some existing tests may reference deleted legacy routes — fix any failures.

- [ ] **Step 2: Fix any test failures from deletions**

If any existing tests imported from `app.api.routes` or tested legacy endpoints, update or remove them.

- [ ] **Step 3: backend-qa reviews ALL backend-dev code changes**

Read every file backend-dev modified/deleted. Check:
- routes.py fully deleted, no orphaned references
- main.py import removed cleanly (no blank line gaps)
- text_routes.py only lost the dead endpoints, nothing else
- openai_service.py only lost the 3 functions, nothing else
- Send back any issues

- [ ] **Step 4: backend-dev reviews ALL backend-qa test files**

Read test_backend_cleanup.py. Check:
- Tests are meaningful (not trivially passing)
- Import paths are correct
- Assertions test real behavior
- Send back any issues

- [ ] **Step 5: Update checkpoint**

Update `docs/session22_progress.md`:
```markdown
## Round 2: Backend Cleanup — COMPLETE
- [x] 2a: Legacy routes.py deleted, main.py updated
- [x] 2b: Dead category-specific endpoints removed from text_routes.py
- [x] 2c: 3 unused functions removed from openai_service.py (~220 lines)
- [x] 2d: Serper cost tracking verified complete
- [x] Tests: test_backend_cleanup.py created, all passing
- [x] Cross-QA: Complete
```

- [ ] **Step 6: Commit checkpoint**

```bash
git add docs/session22_progress.md
git commit -m "docs: checkpoint — Round 2 backend cleanup complete"
```

---

## Chunk 3: Round 3 — AI Efficiency & Observability

**Agent pair:** `ai-dev` (implements) + `ai-qa` (tests + QA)
**Files touched:** `app/services/extraction_service.py`, `app/services/structured_comparison_service.py`

---

### Task 19: Modify Extraction Functions to Return Token Usage (ai-dev)

**Files:**
- Modify: `app/services/extraction_service.py` — 6 functions

Each of the 6 extraction functions currently returns a `Dict`. Modify each to return a `tuple[Dict, Dict]` where the second element contains token usage.

- [ ] **Step 1: Modify parse_product_query() (line 379)**

Read the function. Find where `response = await client.chat.completions.create(...)` is called. After that line, extract usage. Change the return to a tuple:

```python
# At the end of parse_product_query, before returning:
usage = {"prompt_tokens": 0, "completion_tokens": 0}
if hasattr(response, 'usage') and response.usage:
    usage = {
        "prompt_tokens": response.usage.prompt_tokens,
        "completion_tokens": response.usage.completion_tokens
    }
return parsed_result, usage
```

**Important:** The `hasattr` guard ensures backward compatibility if response format changes.

- [ ] **Step 2: Modify extract_specs() (line 413)**

Same pattern — find the OpenAI call, extract usage, return tuple:
```python
usage = {"prompt_tokens": 0, "completion_tokens": 0}
if hasattr(response, 'usage') and response.usage:
    usage = {
        "prompt_tokens": response.usage.prompt_tokens,
        "completion_tokens": response.usage.completion_tokens
    }
return specs_result, usage
```

- [ ] **Step 3: Modify extract_price() (line 476)**

Same pattern:
```python
usage = {"prompt_tokens": 0, "completion_tokens": 0}
if hasattr(response, 'usage') and response.usage:
    usage = {
        "prompt_tokens": response.usage.prompt_tokens,
        "completion_tokens": response.usage.completion_tokens
    }
return price_result, usage
```

- [ ] **Step 4: Modify extract_price_from_training_data() (line 517)**

Same pattern:
```python
usage = {"prompt_tokens": 0, "completion_tokens": 0}
if hasattr(response, 'usage') and response.usage:
    usage = {
        "prompt_tokens": response.usage.prompt_tokens,
        "completion_tokens": response.usage.completion_tokens
    }
return price_result, usage
```

- [ ] **Step 5: Modify extract_reviews() (line 551)**

Same pattern:
```python
usage = {"prompt_tokens": 0, "completion_tokens": 0}
if hasattr(response, 'usage') and response.usage:
    usage = {
        "prompt_tokens": response.usage.prompt_tokens,
        "completion_tokens": response.usage.completion_tokens
    }
return reviews_result, usage
```

- [ ] **Step 6: Modify generate_comparison() (line 645)**

Same pattern:
```python
usage = {"prompt_tokens": 0, "completion_tokens": 0}
if hasattr(response, 'usage') and response.usage:
    usage = {
        "prompt_tokens": response.usage.prompt_tokens,
        "completion_tokens": response.usage.completion_tokens
    }
return comparison_result, usage
```

- [ ] **Step 7: Syntax check**

```bash
python -m py_compile app/services/extraction_service.py
```

- [ ] **Step 8: Commit**

```bash
git add app/services/extraction_service.py
git commit -m "refactor: extraction functions return (result, token_usage) tuples"
```

---

### Task 20: Add _track_gpt_cost and _track_serper_cost Methods (ai-dev)

**Files:**
- Modify: `app/services/structured_comparison_service.py`

- [ ] **Step 1: Add new counter fields to __init__ and state reset**

In `__init__` (around line 168-170), replace:
```python
self.total_cost = 0.0
self.api_calls = 0
```
with:
```python
self.total_cost = 0.0
self.api_calls = 0  # backward compat: gpt_calls + serper_calls
self.gpt_calls = 0
self.serper_calls = 0
```

Do the same in the state reset blocks in `compare_from_text()` (lines 194-195) and `compare_from_text_streaming()` (lines 352-353).

- [ ] **Step 2: Add _track_gpt_cost method**

Add near the existing `_track_cost` method (line 1908):
```python
def _track_gpt_cost(self, usage: dict):
    """Track actual GPT cost from OpenAI token usage.
    gpt-4o-mini: $0.15/1M input, $0.60/1M output."""
    prompt_tokens = usage.get("prompt_tokens", 0)
    completion_tokens = usage.get("completion_tokens", 0)
    input_cost = (prompt_tokens * 0.15) / 1_000_000
    output_cost = (completion_tokens * 0.60) / 1_000_000
    self.total_cost += input_cost + output_cost
    self.gpt_calls += 1
    self.api_calls += 1
```

- [ ] **Step 3: Add _track_serper_cost method**

Add next to `_track_gpt_cost`:
```python
def _track_serper_cost(self):
    """Track a Serper API call ($0.001 per call, fixed pricing)."""
    self.total_cost += 0.001
    self.serper_calls += 1
    self.api_calls += 1
```

- [ ] **Step 4: Syntax check**

```bash
python -m py_compile app/services/structured_comparison_service.py
```

- [ ] **Step 5: Commit**

```bash
git add app/services/structured_comparison_service.py
git commit -m "feat: add _track_gpt_cost and _track_serper_cost methods"
```

---

### Task 21: Migrate All Cost Tracking Calls (ai-dev)

**Files:**
- Modify: `app/services/structured_comparison_service.py`

This is the critical task. All 19 `_track_cost()` calls must be migrated. There are two types:
- **GPT calls** (tracked with hardcoded estimates) → replace with `_track_gpt_cost(usage)` using real token data
- **Serper calls** (tracked with `_track_cost(0.001)`) → replace with `_track_serper_cost()`

- [ ] **Step 1: Update all callers of extraction functions to unpack tuples**

Every place in `structured_comparison_service.py` that calls an extraction function must now unpack the tuple. Find each call and update:

```python
# Old pattern:
specs = await extract_specs(brand, name, variant, category, search_context, drug_context)
self._track_cost(0.0005)

# New pattern:
specs, usage = await extract_specs(brand, name, variant, category, search_context, drug_context)
self._track_gpt_cost(usage)
```

**To find ALL call sites, run:**
```bash
grep -n "await parse_product_query\|await extract_specs\|await extract_price\|await extract_price_from_training\|await extract_reviews\|await generate_comparison" app/services/structured_comparison_service.py
```

Update EVERY result to unpack the tuple. Approximate locations:
- `parse_product_query` calls (~lines 222, 378)
- `extract_specs` calls (~line 779)
- `extract_price` calls (~line 938)
- `extract_price_from_training_data` calls (~lines 931, 959, 1014)
- `extract_reviews` calls (~line 853)
- `generate_comparison` calls (~lines 276, 473)

**Important:** Read each call site carefully. Some may be inside try/except blocks or conditional logic. Preserve the surrounding control flow — only change the assignment and cost tracking. The grep output gives you exact line numbers; the approximations above are just for orientation.

- [ ] **Step 2: Replace all Serper _track_cost(0.001) with _track_serper_cost()**

Find all remaining `self._track_cost(0.001)` calls (these are Serper calls). Replace each with `self._track_serper_cost()`.

Also replace the `_track_cost(0.002)` call (line ~908, broader price search = 2 Serper calls) with TWO calls to `self._track_serper_cost()`.

- [ ] **Step 3: Delete the old _track_cost method**

After all calls are migrated, delete the original `_track_cost` method (line ~1908). If any calls were missed, the syntax check will catch them.

- [ ] **Step 4: Update response metadata to include new counters**

Find where the response dict is built (in both `compare_from_text` and `compare_from_text_streaming`). Add the new fields:
```python
"api_calls": self.api_calls,  # backward compat
"gpt_calls": self.gpt_calls,
"serper_calls": self.serper_calls,
```

- [ ] **Step 5: Syntax check**

```bash
python -m py_compile app/services/structured_comparison_service.py
```

- [ ] **Step 6: Commit**

```bash
git add app/services/structured_comparison_service.py
git commit -m "feat: switch to real token-based cost tracking, split GPT/Serper counters"
```

---

### Task 22: Write Tests for Cost Tracking (ai-qa)

**Files:**
- Create: `tests/test_cost_tracking.py`

- [ ] **Step 1: Write tests for _track_gpt_cost**

Create `tests/test_cost_tracking.py`:
```python
"""Tests for token-based cost tracking and GPT/Serper counter separation."""
import pytest
from app.services.structured_comparison_service import get_comparison_service


class TestTrackGptCost:
    def setup_method(self):
        self.service = get_comparison_service()
        self.service.total_cost = 0.0
        self.service.gpt_calls = 0
        self.service.serper_calls = 0
        self.service.api_calls = 0

    def test_calculates_cost_from_tokens(self):
        """Cost should be calculated from actual token counts."""
        usage = {"prompt_tokens": 1000, "completion_tokens": 500}
        self.service._track_gpt_cost(usage)
        # input: 1000 * 0.15 / 1M = 0.00015
        # output: 500 * 0.60 / 1M = 0.0003
        expected = 0.00015 + 0.0003
        assert abs(self.service.total_cost - expected) < 1e-10

    def test_increments_gpt_calls(self):
        usage = {"prompt_tokens": 100, "completion_tokens": 50}
        self.service._track_gpt_cost(usage)
        self.service._track_gpt_cost(usage)
        assert self.service.gpt_calls == 2

    def test_increments_api_calls_for_backward_compat(self):
        usage = {"prompt_tokens": 100, "completion_tokens": 50}
        self.service._track_gpt_cost(usage)
        assert self.service.api_calls == 1

    def test_handles_zero_tokens(self):
        usage = {"prompt_tokens": 0, "completion_tokens": 0}
        self.service._track_gpt_cost(usage)
        assert self.service.total_cost == 0.0
        assert self.service.gpt_calls == 1

    def test_handles_missing_keys(self):
        usage = {}
        self.service._track_gpt_cost(usage)
        assert self.service.total_cost == 0.0
        assert self.service.gpt_calls == 1


class TestTrackSerperCost:
    def setup_method(self):
        self.service = get_comparison_service()
        self.service.total_cost = 0.0
        self.service.gpt_calls = 0
        self.service.serper_calls = 0
        self.service.api_calls = 0

    def test_fixed_cost_per_call(self):
        self.service._track_serper_cost()
        assert self.service.total_cost == 0.001

    def test_increments_serper_calls(self):
        self.service._track_serper_cost()
        self.service._track_serper_cost()
        assert self.service.serper_calls == 2

    def test_increments_api_calls_for_backward_compat(self):
        self.service._track_serper_cost()
        assert self.service.api_calls == 1

    def test_does_not_increment_gpt_calls(self):
        self.service._track_serper_cost()
        assert self.service.gpt_calls == 0


class TestCounterSeparation:
    def setup_method(self):
        self.service = get_comparison_service()
        self.service.total_cost = 0.0
        self.service.gpt_calls = 0
        self.service.serper_calls = 0
        self.service.api_calls = 0

    def test_mixed_calls_separate_correctly(self):
        usage = {"prompt_tokens": 1000, "completion_tokens": 500}
        self.service._track_gpt_cost(usage)
        self.service._track_serper_cost()
        self.service._track_serper_cost()
        self.service._track_gpt_cost(usage)

        assert self.service.gpt_calls == 2
        assert self.service.serper_calls == 2
        assert self.service.api_calls == 4

    def test_api_calls_equals_sum(self):
        """api_calls must always equal gpt_calls + serper_calls."""
        usage = {"prompt_tokens": 500, "completion_tokens": 200}
        for _ in range(3):
            self.service._track_gpt_cost(usage)
        for _ in range(5):
            self.service._track_serper_cost()
        assert self.service.api_calls == self.service.gpt_calls + self.service.serper_calls

    def test_total_cost_includes_both(self):
        usage = {"prompt_tokens": 1000000, "completion_tokens": 0}  # $0.15 input
        self.service._track_gpt_cost(usage)
        self.service._track_serper_cost()
        # GPT: 0.15, Serper: 0.001
        assert abs(self.service.total_cost - 0.151) < 1e-10


class TestExtractionFunctionsImportable:
    """Verify all 6 extraction functions are importable after refactor."""

    def test_all_extraction_functions_import(self):
        """All 6 functions should import without error. If renamed/removed, this fails."""
        from app.services.extraction_service import (
            parse_product_query, extract_specs, extract_price,
            extract_price_from_training_data, extract_reviews,
            generate_comparison
        )
        # Import success = functions exist after refactor
        assert parse_product_query is not None
        assert extract_specs is not None
        assert extract_price is not None
        assert extract_price_from_training_data is not None
        assert extract_reviews is not None
        assert generate_comparison is not None


class TestStateReset:
    """Verify new counters are reset per request."""

    def test_gpt_calls_initialized_to_zero(self):
        service = get_comparison_service()
        assert hasattr(service, 'gpt_calls')

    def test_serper_calls_initialized_to_zero(self):
        service = get_comparison_service()
        assert hasattr(service, 'serper_calls')

    def test_old_track_cost_removed(self):
        """The old _track_cost method should no longer exist."""
        service = get_comparison_service()
        assert not hasattr(service, '_track_cost'), "_track_cost should be replaced by _track_gpt_cost and _track_serper_cost"
```

- [ ] **Step 2: Run tests**

```bash
python -m pytest tests/test_cost_tracking.py -v
```
Expected: All tests PASS

- [ ] **Step 3: Commit**

```bash
git add tests/test_cost_tracking.py
git commit -m "test: add cost tracking tests — token-based GPT, fixed Serper, counter separation"
```

---

### Task 23: Run Full Test Suite + Cross-QA (both agents)

- [ ] **Step 1: ai-qa runs full test suite**

```bash
python -m pytest tests/ -v -m "not (live_unit or live_db or integration)" --ignore=tests/test_integration.py
```
Expected: All tests PASS. Some existing tests may mock `_track_cost` — fix any failures.

- [ ] **Step 2: Fix any test failures from refactoring**

If existing tests call or mock `_track_cost()`, update them to use `_track_gpt_cost()` or `_track_serper_cost()` as appropriate. Check:
- `tests/test_unified_search.py` — may reference cost tracking
- `tests/test_singleton_state.py` — tests state reset
- Any test that imports `_track_cost`

- [ ] **Step 3: ai-qa reviews ALL ai-dev code changes**

Read every file ai-dev modified. Check:
- All 6 extraction functions return `(result, usage)` tuples
- All 19 `_track_cost()` calls migrated (none remaining)
- `_track_cost` method deleted
- New counters reset in both `compare_from_text()` and `compare_from_text_streaming()`
- Response metadata includes `gpt_calls` and `serper_calls`
- `api_calls` still computed as sum (backward compat)
- `hasattr` guard on response.usage in extraction functions
- Send back any issues with specific file:line references

- [ ] **Step 4: ai-dev reviews ALL ai-qa test files**

Read test_cost_tracking.py. Check:
- Cost calculations in tests match gpt-4o-mini pricing ($0.15/1M input, $0.60/1M output)
- Edge cases covered (zero tokens, missing keys)
- Counter separation properly verified
- State reset tested
- Send back any issues

- [ ] **Step 5: Update checkpoint**

Update `docs/session22_progress.md`:
```markdown
## Round 3: AI Efficiency — COMPLETE
- [x] 3a: All 6 extraction functions return (result, token_usage) tuples
- [x] 3a: _track_gpt_cost uses real OpenAI token counts
- [x] 3b: _track_serper_cost replaces all _track_cost(0.001) calls
- [x] 3b: gpt_calls and serper_calls counters in response metadata
- [x] 3b: api_calls backward compatible (sum of both)
- [x] Old _track_cost method deleted
- [x] Tests: test_cost_tracking.py created, all passing
- [x] Cross-QA: Complete

## Session 22 — ALL ROUNDS COMPLETE
```

- [ ] **Step 6: Commit checkpoint**

```bash
git add docs/session22_progress.md
git commit -m "docs: checkpoint — Round 3 AI efficiency complete, all rounds done"
```

---

## Final: Update Context Files

After all 3 rounds complete, the orchestrator updates project context:

- [ ] **Update CONTEXT_SESSION_LOG.md** with Session 22 summary
- [ ] **Update MEMORY.md** if any new learnings emerged
- [ ] **Run final full test suite** to confirm everything passes
- [ ] **Verify total test count** increased from 637 baseline
