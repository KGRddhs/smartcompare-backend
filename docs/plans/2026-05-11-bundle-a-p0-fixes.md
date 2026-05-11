# Bundle A — Pre-launch P0 Fixes — Implementation Plan

> **For Claude:** This plan is executed by a **4-Opus TeamCreate**, NOT a single sequential agent. Each agent has exclusive file ownership and follows TDD per task. Cross-QA is BLOCKING — team does NOT disassemble until every deliverable has been reviewed by a different agent and approved.
>
> **Required design doc:** `docs/plans/2026-05-11-bundle-a-p0-fixes-design.md` (615 lines, read it first).
>
> **Required reference skills (per agent):**
> - `superpowers:test-driven-development` — RED → GREEN → REFACTOR cycle, no exceptions
> - `superpowers:verification-before-completion` — never claim "done" without command output proving it
> - `superpowers:prove-it-works` — every bug fix must include a reproducer test that fails BEFORE the fix
> - `superpowers:receiving-code-review` — when QA sends work back, verify rigorously, don't capitulate or stonewall

**Goal:** Ship Bundle A — 7 sections of pre-launch P0 fixes — to mobile testers via EAS Update with zero render crashes, working Profile handlers, working word-of-mouth referral, and device-bound free tier, in one cleanly-merged PR.

**Architecture:** Backend extends existing FastAPI routes + 2 small Supabase migrations. Frontend adds 4 new screens + 5 new components + a device fingerprint service, replacing dead nav handlers. No new external services. Cross-QA gate enforces correctness before disassembly.

**Tech Stack:** FastAPI · Supabase Postgres · Upstash Redis · React Native (Expo SDK 51+) · Reanimated · i18next · expo-secure-store · expo-crypto · pytest · jest · slowapi

---

## Pre-flight (team coordinator does these BEFORE spawning agents)

### Pre-flight 0.1 — Worktree setup

```bash
git status                                # confirm clean main
git checkout main && git pull
git worktree add -b feature/bundle-a-p0 ../smartcompare-bundle-a main
cd ../smartcompare-bundle-a
```

All agent work happens in `../smartcompare-bundle-a`. Original tree stays untouched.

### Pre-flight 0.2 — Install new frontend dependency

```bash
cd SmartCompareApp
npx expo install react-native-markdown-display
npx expo-doctor                           # must pass; if not, stop and investigate
git add package.json package-lock.json
git commit -m "chore(deps): add react-native-markdown-display for LegalScreen"
```

### Pre-flight 0.3 — Confirm Railway env vars (NO code change here, just verify)

Open Railway dashboard for `web-production-58776`:
- `ENABLE_REFERRAL_SYSTEM` — must be `true`. If not set, set it to `true` now.
- `SENTRY_DSN` — paste DSN from Sentry free-tier signup (https://sentry.io/signup/). If not signed up yet, do that now.

Both are config-only. The plan assumes they're set before the team starts.

### Pre-flight 0.4 — Spawn the team

Use `TeamCreate` with this exact composition. **All four agents are Opus** — no Sonnet, no Haiku.

```
TeamCreate({
  team_name: "bundle-a-opus",
  agents: [
    { name: "backend-opus", model: "opus", role: "backend + migrations + backend tests" },
    { name: "frontend-opus", model: "opus", role: "screens + components + services" },
    { name: "i18n-opus", model: "opus", role: "i18n strings + leftover-EN sweep + eslint rule" },
    { name: "qa-opus", model: "opus", role: "jest tests + cross-QA + manual QA checklist" },
  ],
  mode: "bypassPermissions",
  worktree: "../smartcompare-bundle-a"
})
```

Each agent receives this **base instruction block**:

> You own ONLY the files listed under your name in Section 0.5 of this plan. Do NOT touch files owned by other agents — that causes merge conflicts (Session 35 lesson). Path-restricted commits per CLAUDE.md operating principle 6: `git commit -m "msg" -- <paths>` (the `--` is a path separator; `-m` must come BEFORE it).
>
> Follow TDD: write the failing test, run it to confirm RED, write minimal implementation, run it to confirm GREEN, commit. No exceptions.
>
> When you finish a task, post a TaskList update. When you have no current task AND are waiting for QA on your last submission, you MUST EITHER write red-green tests against the bundle's new code to push coverage toward 80%, OR poll TaskList every 5 minutes for re-assignment. Do NOT pick up another agent's owned files. Do NOT go idle.
>
> If QA sends your work back with specific reasons, follow `superpowers:receiving-code-review`: verify the claim rigorously, fix only what's actually wrong, push back with evidence if you disagree. Do not blindly capitulate.

### Pre-flight 0.5 — File ownership matrix

| Path glob | Owner |
|---|---|
| `app/**/*.py` (except tests) | backend-opus |
| `migrations/020_*.sql`, `migrations/021_*.sql` | backend-opus |
| `tests/test_*.py` for backend | backend-opus |
| `SmartCompareApp/src/screens/**` | frontend-opus |
| `SmartCompareApp/src/components/**` (except __tests__) | frontend-opus |
| `SmartCompareApp/src/services/**` | frontend-opus |
| `SmartCompareApp/src/utils/**` | frontend-opus |
| `SmartCompareApp/src/i18n/**` | i18n-opus |
| `SmartCompareApp/.eslintrc*` (i18n rule) | i18n-opus |
| `SmartCompareApp/src/**/__tests__/**` (jest tests) | qa-opus |
| `CLAUDE.md`, `MEMORY.md`, `docs/CONTEXT_SESSION_LOG.md` | team coordinator only (post-merge) |

---

## Phase 1 — Backend foundations (backend-opus owns; ~10 tasks)

### Task 1.1: Migration 020 — schema_version on comparisons

**Files:**
- Create: `migrations/020_comparisons_schema_version.sql`

**Step 1: Write the migration file**

```sql
-- migrations/020_comparisons_schema_version.sql
-- Add schema_version to comparisons table.
-- v1 = legacy rows (pre-structured-response). Hidden from history list.
-- v2 = full structured response. Renderable in ResultsScreen.
-- Bumped on every breaking shape change to the ResultsScreen contract.

ALTER TABLE comparisons
  ADD COLUMN IF NOT EXISTS schema_version INT NOT NULL DEFAULT 1;

-- Future inserts default to v2 (after this ALTER).
ALTER TABLE comparisons
  ALTER COLUMN schema_version SET DEFAULT 2;

-- Index for fast "list user's v2 history newest-first"
CREATE INDEX IF NOT EXISTS idx_comparisons_user_schema
  ON comparisons (user_id, schema_version, created_at DESC);

COMMENT ON COLUMN comparisons.schema_version IS
  'v1 = legacy pre-structured-response (hidden from history). v2 = full structured response, renderable.';
```

**Step 2: Apply via Supabase MCP**

Use `mcp__plugin_supabase_supabase__apply_migration` with the SQL above. NOT SQL Editor (per CLAUDE.md — MCP tracks migration history, SQL Editor wraps multi-statement scripts in one transaction and silently rolls back on view bugs).

Expected: migration tracked in `supabase_migrations.schema_migrations`. Verify:

```bash
curl -X POST "https://qulajmyxdbdkchvecmvc.supabase.co/rest/v1/rpc/exec_sql" \
  -H "apikey: $SUPABASE_SERVICE_KEY" \
  -H "Authorization: Bearer $SUPABASE_SERVICE_KEY" \
  -d '{"query": "SELECT column_name FROM information_schema.columns WHERE table_name=\"comparisons\" AND column_name=\"schema_version\""}'
# Expected: returns row { "column_name": "schema_version" }
```

**Step 3: Commit**

```bash
git add migrations/020_comparisons_schema_version.sql
git commit -m "feat(db): migration 020 — comparisons.schema_version for renderability gate" -- migrations/020_comparisons_schema_version.sql
```

---

### Task 1.2: Migration 021 — device_fingerprint_hash on users

**Files:**
- Create: `migrations/021_device_fingerprint_users.sql`

**Step 1: Write the migration**

```sql
-- migrations/021_device_fingerprint_users.sql
-- Free-tier counter inheritance via device fingerprint to prevent
-- freebie-farming via re-signup. See Bundle A design §1.5.

ALTER TABLE users
  ADD COLUMN IF NOT EXISTS device_fingerprint_hash TEXT;

CREATE INDEX IF NOT EXISTS idx_users_device_fp
  ON users(device_fingerprint_hash)
  WHERE device_fingerprint_hash IS NOT NULL;

COMMENT ON COLUMN users.device_fingerprint_hash IS
  'SHA-256 hash of expo-application bundle id + expo-device osBuildId + SecureStore-pinned nonce. Used to lock free-tier counter across re-signups on same device.';
```

**Step 2: Apply via Supabase MCP**

Same as Task 1.1 — use `apply_migration` tool. Verify column exists.

**Step 3: Commit**

```bash
git add migrations/021_device_fingerprint_users.sql
git commit -m "feat(db): migration 021 — users.device_fingerprint_hash for freebie-farming prevention" -- migrations/021_device_fingerprint_users.sql
```

---

### Task 1.3: `_validate_renderable` helper in database_service

**Files:**
- Modify: `app/services/database_service.py`
- Test: `tests/test_database_service.py`

**Step 1: Write the failing test**

Add to `tests/test_database_service.py`:

```python
from app.services.database_service import _validate_renderable


class TestValidateRenderable:
    def test_passes_new_format_with_overview(self):
        payload = {
            "overview": {"products": [{"name": "A"}, {"name": "B"}]},
            "metadata": {"query": "A vs B"},
        }
        assert _validate_renderable(payload) is True

    def test_passes_legacy_alias_format(self):
        payload = {
            "products": [{"name": "A"}, {"name": "B"}],
            "metadata": {"query": "A vs B"},
        }
        assert _validate_renderable(payload) is True

    def test_fails_when_fewer_than_two_products(self):
        payload = {
            "overview": {"products": [{"name": "A"}]},
            "metadata": {"query": "solo"},
        }
        assert _validate_renderable(payload) is False

    def test_fails_when_product_name_missing(self):
        payload = {
            "overview": {"products": [{"name": "A"}, {}]},
            "metadata": {"query": "broken"},
        }
        assert _validate_renderable(payload) is False

    def test_fails_when_query_missing(self):
        payload = {
            "overview": {"products": [{"name": "A"}, {"name": "B"}]},
            "metadata": {},
        }
        assert _validate_renderable(payload) is False

    def test_fails_when_payload_empty(self):
        assert _validate_renderable({}) is False
```

**Step 2: Run, confirm RED**

```bash
python -m pytest tests/test_database_service.py::TestValidateRenderable -v
# Expected: ImportError or AttributeError — _validate_renderable doesn't exist yet
```

**Step 3: Implement minimal helper**

Add to `app/services/database_service.py` (top of module, after imports):

```python
def _validate_renderable(payload: dict) -> bool:
    """Return True iff payload has the minimum keys ResultsScreen needs.

    Used by save_comparison() to gate which rows reach the history table —
    only renderable rows are persisted. See Bundle A design §5.2.
    """
    if not isinstance(payload, dict):
        return False
    products = (
        payload.get("overview", {}).get("products")
        or payload.get("products")
        or []
    )
    if len(products) < 2:
        return False
    if not all(isinstance(p, dict) and p.get("name") for p in products[:2]):
        return False
    query = payload.get("metadata", {}).get("query")
    return bool(query)
```

**Step 4: Run, confirm GREEN**

```bash
python -m pytest tests/test_database_service.py::TestValidateRenderable -v
# Expected: 6 passed
```

**Step 5: Commit**

```bash
git add app/services/database_service.py tests/test_database_service.py
git commit -m "feat(db): add _validate_renderable helper for comparison persistence gate" -- app/services/database_service.py tests/test_database_service.py
```

---

### Task 1.4: `save_comparison` gates on validator + sets schema_version=2 + populates product_names

**Files:**
- Modify: `app/services/database_service.py` (existing `save_comparison`)
- Test: `tests/test_database_service.py`

**Step 1: Locate `save_comparison`** — `grep -n "def save_comparison" app/services/database_service.py` and read the function body.

**Step 2: Write failing tests**

Add to `tests/test_database_service.py`:

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.database_service import save_comparison


@pytest.mark.asyncio
async def test_save_comparison_skips_when_not_renderable(caplog):
    payload = {"products": []}  # invalid
    with patch("app.services.database_service.get_admin_supabase_client") as m:
        await save_comparison(user_id="u1", query="q", full_response=payload)
        m.assert_not_called()  # never reached the DB
    assert any("comparison_renderable=false" in r.message or "skip" in r.message.lower()
               for r in caplog.records)


@pytest.mark.asyncio
async def test_save_comparison_populates_product_names_and_v2():
    payload = {
        "overview": {"products": [{"name": "iPhone 15"}, {"name": "Galaxy S24"}]},
        "metadata": {"query": "iPhone vs Galaxy"},
    }
    mock_table = MagicMock()
    mock_table.insert.return_value.execute = AsyncMock(return_value=MagicMock(data=[{"id": "c1"}]))
    mock_client = MagicMock()
    mock_client.table.return_value = mock_table
    with patch("app.services.database_service.get_admin_supabase_client", return_value=mock_client):
        await save_comparison(user_id="u1", query="iPhone vs Galaxy", full_response=payload)

    insert_arg = mock_table.insert.call_args[0][0]
    assert insert_arg["schema_version"] == 2
    assert insert_arg["product_names"] == ["iPhone 15", "Galaxy S24"]
    assert insert_arg["full_response"] == payload
```

**Step 3: Run, confirm RED**

```bash
python -m pytest tests/test_database_service.py::test_save_comparison_skips_when_not_renderable tests/test_database_service.py::test_save_comparison_populates_product_names_and_v2 -v
# Expected: 2 failed
```

**Step 4: Modify `save_comparison`**

In `app/services/database_service.py`, find the `save_comparison` function. Replace its body so the first lines after the docstring are:

```python
    if not _validate_renderable(full_response):
        logger.warning(
            "save_comparison: skipping unrenderable payload "
            f"(user_id={user_id}, comparison_renderable=false)"
        )
        # Sentry breadcrumb tag (no-op if Sentry not configured)
        try:
            import sentry_sdk
            sentry_sdk.set_tag("comparison_renderable", "false")
            sentry_sdk.add_breadcrumb(
                category="comparison.save",
                message="skipped unrenderable payload",
                level="warning",
            )
        except Exception:
            pass
        return None

    products = (
        full_response.get("overview", {}).get("products")
        or full_response.get("products")
        or []
    )
    product_names = [p["name"] for p in products[:2]]
```

Then, in the dict that gets passed to `.insert(...)`, ADD:

```python
        "schema_version": 2,
        "product_names": product_names,
```

(Keep the existing `full_response`, `user_id`, `query` fields.)

**Step 5: Run, confirm GREEN**

```bash
python -m pytest tests/test_database_service.py -v -k "save_comparison"
# Expected: all passing including the 2 new ones
```

**Step 6: Commit**

```bash
git add app/services/database_service.py tests/test_database_service.py
git commit -m "feat(db): save_comparison gates on _validate_renderable, sets schema_version=2 + product_names" -- app/services/database_service.py tests/test_database_service.py
```

---

### Task 1.5: History list filters schema_version=2

**Files:**
- Modify: `app/api/history_routes.py:43-49` (the `get_user_comparisons` call)
- Modify: `app/services/database_service.py::get_user_comparisons`
- Test: `tests/test_history_routes.py`

**Step 1: Write the failing tests**

Add to `tests/test_history_routes.py`:

```python
@pytest.mark.asyncio
async def test_list_hides_v1_rows(authed_client, seed_user_with_v1_and_v2_comparisons):
    response = await authed_client.get("/api/v1/comparisons/history")
    assert response.status_code == 200
    data = response.json()
    # seed fixture creates 2 v1 rows and 3 v2 rows
    assert data["total"] == 3
    assert len(data["comparisons"]) == 3
    # None of the returned ids match the v1 seed ids
    v1_ids = seed_user_with_v1_and_v2_comparisons["v1_ids"]
    for c in data["comparisons"]:
        assert c["id"] not in v1_ids


@pytest.mark.asyncio
async def test_get_returns_404_for_v1_row(authed_client, seed_user_with_v1_and_v2_comparisons):
    v1_id = seed_user_with_v1_and_v2_comparisons["v1_ids"][0]
    response = await authed_client.get(f"/api/v1/comparisons/{v1_id}")
    assert response.status_code == 404
```

**Step 2: Add the fixture** in `tests/conftest.py` (if `seed_user_with_v1_and_v2_comparisons` doesn't exist):

```python
@pytest.fixture
async def seed_user_with_v1_and_v2_comparisons(test_user, admin_supabase):
    """Insert 2 v1 + 3 v2 comparisons for the test user."""
    v1_rows = [
        {"user_id": test_user["id"], "query": f"old-{i}", "full_response": {"products": []},
         "schema_version": 1, "product_names": []}
        for i in range(2)
    ]
    v2_rows = [
        {"user_id": test_user["id"], "query": f"new-{i}",
         "full_response": {"overview": {"products": [{"name": "A"}, {"name": "B"}]},
                           "metadata": {"query": f"new-{i}"}},
         "schema_version": 2, "product_names": ["A", "B"]}
        for i in range(3)
    ]
    res_v1 = admin_supabase.table("comparisons").insert(v1_rows).execute()
    res_v2 = admin_supabase.table("comparisons").insert(v2_rows).execute()
    yield {
        "v1_ids": [r["id"] for r in res_v1.data],
        "v2_ids": [r["id"] for r in res_v2.data],
    }
    # Cleanup
    admin_supabase.table("comparisons").delete().eq("user_id", test_user["id"]).execute()
```

**Step 3: Run, confirm RED**

```bash
python -m pytest tests/test_history_routes.py -v -k "v1"
# Expected: both fail
```

**Step 4: Modify `get_user_comparisons`** in `app/services/database_service.py`. Find the `.select(...)` query and add:

```python
        .eq("schema_version", 2)
```

After `.eq("user_id", user_id)`. Same for `get_user_comparison_count`.

**Step 5: Modify `get_comparison_by_id`** — after fetching, check `if row.get("schema_version", 1) < 2: return None`. The route layer already returns 404 on None.

**Step 6: Run, confirm GREEN**

```bash
python -m pytest tests/test_history_routes.py -v
# Expected: all passing
```

**Step 7: Commit**

```bash
git add app/api/history_routes.py app/services/database_service.py tests/test_history_routes.py tests/conftest.py
git commit -m "feat(api): history endpoints filter schema_version=2 (hide unrenderable v1 rows)" -- app/api/history_routes.py app/services/database_service.py tests/test_history_routes.py tests/conftest.py
```

---

### Task 1.6: Register accepts `invite_code` AND `device_fingerprint_hash`

**Files:**
- Modify: `app/api/auth_routes.py` (Pydantic `RegisterRequest` + `register` handler)
- Modify: `app/services/referral_service.py` (add `resolve_code_to_invite_id` helper)
- Test: `tests/test_auth_routes.py`

**Step 1: Read existing `register` handler** — `grep -n "def register\|class RegisterRequest" app/api/auth_routes.py`

**Step 2: Write failing tests**

Add to `tests/test_auth_routes.py`:

```python
@pytest.mark.asyncio
async def test_register_with_invite_code_resolves_to_invite_id(client, existing_referrer):
    # existing_referrer fixture: a user with referral_code='QR-TESTAB'
    response = await client.post("/api/v1/auth/register", json={
        "email": "newuser@example.com",
        "password": "ValidP@ss123",
        "invite_code": "QR-TESTAB",
    })
    assert response.status_code in (200, 201)
    # Verify a referral_invites row was created
    invites = admin_supabase.table("referral_invites") \
        .select("*").eq("invitee_id", response.json()["user"]["id"]).execute()
    assert len(invites.data) == 1
    assert invites.data[0]["source"] == "code_redeem"


@pytest.mark.asyncio
async def test_register_invalid_invite_code_format_returns_400(client):
    response = await client.post("/api/v1/auth/register", json={
        "email": "u@example.com",
        "password": "ValidP@ss123",
        "invite_code": "notvalid",
    })
    assert response.status_code == 400
    assert response.json()["code"] == "INVITE_CODE_INVALID"


@pytest.mark.asyncio
async def test_register_unknown_invite_code_returns_404(client):
    response = await client.post("/api/v1/auth/register", json={
        "email": "u@example.com",
        "password": "ValidP@ss123",
        "invite_code": "QR-ZZZZZZ",
    })
    assert response.status_code == 404
    assert response.json()["code"] == "INVITE_CODE_NOT_FOUND"


@pytest.mark.asyncio
async def test_register_inherits_device_lifetime_counter(client, existing_user_with_3_used):
    # existing_user_with_3_used fixture: user with device_fingerprint_hash='deadbeef'
    # and lifetime_comparisons_used=3
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "second@example.com", "password": "ValidP@ss123"},
        headers={"X-Device-Fingerprint": "deadbeef"},
    )
    assert response.status_code in (200, 201)
    new_id = response.json()["user"]["id"]
    row = admin_supabase.table("users").select("lifetime_comparisons_used").eq("id", new_id).single().execute()
    assert row.data["lifetime_comparisons_used"] == 3


@pytest.mark.asyncio
async def test_register_without_fingerprint_starts_at_zero(client):
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "fresh@example.com", "password": "ValidP@ss123"},
    )
    assert response.status_code in (200, 201)
    new_id = response.json()["user"]["id"]
    row = admin_supabase.table("users").select("lifetime_comparisons_used").eq("id", new_id).single().execute()
    assert row.data["lifetime_comparisons_used"] == 0
```

**Step 3: Run, confirm RED**

```bash
python -m pytest tests/test_auth_routes.py -v -k "invite_code or device_lifetime or without_fingerprint"
# Expected: 5 failures
```

**Step 4: Extend Pydantic model**

In `app/api/auth_routes.py`, find `class RegisterRequest`. Add:

```python
import re
from pydantic import field_validator

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: Optional[str] = None
    invite_id: Optional[str] = None        # existing — kept for deep-link path
    invite_code: Optional[str] = None      # NEW — Bundle A §1.1

    @field_validator("invite_code")
    @classmethod
    def validate_code_format(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return None
        if not re.match(r"^QR-[A-HJ-NP-Z2-9]{6}$", v):
            raise ValueError("INVITE_CODE_INVALID")
        return v
```

Note: alphabet `[A-HJ-NP-Z2-9]` matches the generator's unambiguous set (no `I`/`O`/`0`/`1`/`L`).

**Step 5: Add resolver in `referral_service.py`**

Add to `app/services/referral_service.py`:

```python
async def resolve_code_to_invite_id(invite_code: str, invitee_id: str) -> Optional[str]:
    """Resolve a QR-XXXXXX code to a fresh referral_invites.id.

    Returns None if the code doesn't match any user's referral_code.
    Caller is responsible for self-referral and abuse checks.
    """
    client = get_admin_supabase_client()
    referrer = client.table("users") \
        .select("id, referral_code") \
        .eq("referral_code", invite_code) \
        .maybe_single() \
        .execute()
    if not referrer.data:
        return None
    if referrer.data["id"] == invitee_id:
        return None  # self-referral
    invite_row = client.table("referral_invites").insert({
        "inviter_id": referrer.data["id"],
        "invitee_id": invitee_id,
        "source": "code_redeem",
    }).execute()
    return invite_row.data[0]["id"] if invite_row.data else None
```

**Step 6: Modify `register` handler**

In `app/api/auth_routes.py::register`, after the user is created in Supabase Auth and the public.users row is inserted, add:

```python
    fp = request.headers.get("X-Device-Fingerprint")
    inherited_lifetime = 0
    if fp:
        prior_query = admin_supabase.table("users") \
            .select("lifetime_comparisons_used") \
            .eq("device_fingerprint_hash", fp) \
            .order("lifetime_comparisons_used", desc=True) \
            .limit(1) \
            .execute()
        if prior_query.data:
            inherited_lifetime = prior_query.data[0].get("lifetime_comparisons_used", 0)

    # Persist fingerprint + inherited counter on the new user row
    admin_supabase.table("users").update({
        "device_fingerprint_hash": fp,
        "lifetime_comparisons_used": inherited_lifetime,
    }).eq("id", new_user_id).execute()

    # Resolve invite_code → invite_id if provided
    resolved_invite_id = body.invite_id
    if body.invite_code and not resolved_invite_id:
        resolved_invite_id = await referral_service.resolve_code_to_invite_id(
            body.invite_code, new_user_id,
        )
        if resolved_invite_id is None:
            raise HTTPException(
                status_code=404,
                detail={"error": "Invite code not found", "code": "INVITE_CODE_NOT_FOUND"},
            )

    if resolved_invite_id:
        try:
            await referral_service.link_invite_to_user(new_user_id, resolved_invite_id)
        except Exception as exc:
            logger.warning(f"link_invite_to_user failed (silent): {exc}")
```

Also handle the `ValueError("INVITE_CODE_INVALID")` from Pydantic — the error_handler middleware should map this to 400. If it doesn't, add explicit try/except around the body parsing.

**Step 7: Run, confirm GREEN**

```bash
python -m pytest tests/test_auth_routes.py -v -k "invite_code or device_lifetime or without_fingerprint"
# Expected: all 5 passing
```

**Step 8: Commit**

```bash
git add app/api/auth_routes.py app/services/referral_service.py tests/test_auth_routes.py
git commit -m "feat(auth): register accepts invite_code + device_fingerprint_hash header for §1.1/§1.5" -- app/api/auth_routes.py app/services/referral_service.py tests/test_auth_routes.py
```

---

### Task 1.7: Security regression suite still passes

**Step 1: Run the security regression**

```bash
python -m pytest tests/test_security_regression.py -v
# Expected: all ~98 tests pass
```

If anything fails — STOP. Either:
- The new code added a regression → fix the implementation, not the test
- The test fixture is stale → escalate to qa-opus to investigate

**Step 2: No commit if all green** — continue to next task.

---

### Task 1.8: Audit-log invite_code redemptions (defense-in-depth)

**Files:**
- Modify: `app/services/audit_service.py` (or add a new event type)
- Test: `tests/test_audit_service.py`

**Step 1: Write failing test**

```python
@pytest.mark.asyncio
async def test_invite_code_redemption_audit_logged(client, existing_referrer, caplog):
    response = await client.post("/api/v1/auth/register", json={
        "email": "audit@example.com",
        "password": "ValidP@ss123",
        "invite_code": "QR-TESTAB",
    })
    assert response.status_code in (200, 201)
    # Audit row should exist
    rows = admin_supabase.table("admin_audit_log") \
        .select("*").eq("event_type", "invite_code_redeemed").execute()
    assert len(rows.data) >= 1
    assert rows.data[-1]["details"]["invite_code"] == "QR-TESTAB"
```

**Step 2: Run RED, implement, GREEN, commit.**

In `audit_service.py`, add a new event type constant `INVITE_CODE_REDEEMED = "invite_code_redeemed"`. In `auth_routes.py::register` after successful `link_invite_to_user`, fire-and-forget call to `audit_service.log_event(...)` with the redeemed code in `details`.

---

### Task 1.9: backend-opus idle work — coverage tests

If backend-opus finishes 1.1–1.8 before frontend-opus needs anything, write additional red-green tests targeting:
- `app/services/usage_service.py::check_usage_allowed` — confirm inherited `lifetime_comparisons_used` correctly blocks the free tier
- `app/services/referral_service.py::resolve_code_to_invite_id` — edge cases (case sensitivity, expired invites, deleted referrers)
- `app/api/history_routes.py::delete_comparison` — confirm v1 rows can still be deleted (no schema_version filter on DELETE)

Target backend module coverage ≥80% on changed files.

---

### Task 1.10: backend-opus submits work for cross-QA

Post in TaskList: "backend-opus phase 1 complete. Files touched: [list]. Awaiting QA review by qa-opus + frontend-opus."

---

## Phase 2 — Frontend services + screens (frontend-opus owns; ~14 tasks)

### Task 2.1: Device fingerprint service

**Files:**
- Create: `SmartCompareApp/src/services/deviceFingerprint.ts`
- Test (owner: qa-opus, but stub here): `SmartCompareApp/src/services/__tests__/deviceFingerprint.test.ts`

**Step 1: Write the service**

```ts
// SmartCompareApp/src/services/deviceFingerprint.ts
//
// Generates a SHA-256 hash that's stable across launches but resets on
// uninstall — used by the backend to lock free-tier counters across
// re-signups on the same physical device. See Bundle A design §1.5.

import * as Application from 'expo-application';
import * as Device from 'expo-device';
import * as SecureStore from 'expo-secure-store';
import * as Crypto from 'expo-crypto';

const NONCE_KEY = 'device_fp_nonce';

let cached: string | null = null;
let inflight: Promise<string> | null = null;

export async function getDeviceFingerprint(): Promise<string> {
  if (cached) return cached;
  if (inflight) return inflight;

  inflight = (async () => {
    let nonce = await SecureStore.getItemAsync(NONCE_KEY);
    if (!nonce) {
      nonce = Crypto.randomUUID();
      await SecureStore.setItemAsync(NONCE_KEY, nonce);
    }
    const raw = [
      Application.applicationId ?? '',
      Device.osBuildId ?? Device.osInternalBuildId ?? '',
      nonce,
    ].join('|');
    const hash = await Crypto.digestStringAsync(
      Crypto.CryptoDigestAlgorithm.SHA256,
      raw,
    );
    cached = hash;
    inflight = null;
    return hash;
  })();

  return inflight;
}

// Test-only escape hatch
export function _resetCacheForTests() {
  cached = null;
  inflight = null;
}
```

**Step 2: Commit**

```bash
git add SmartCompareApp/src/services/deviceFingerprint.ts
git commit -m "feat(fp): device fingerprint service for free-tier inheritance" -- SmartCompareApp/src/services/deviceFingerprint.ts
```

(Test is written by qa-opus in Phase 5.)

---

### Task 2.2: authService.register sends X-Device-Fingerprint header + invite_code

**Files:**
- Modify: `SmartCompareApp/src/services/authService.ts`

**Step 1: Find existing `register` function**

```bash
grep -n "register\|invite_id" SmartCompareApp/src/services/authService.ts | head -20
```

**Step 2: Modify the function signature + body**

Add `inviteCode?: string` parameter. Add fingerprint header. Pseudocode:

```ts
import { getDeviceFingerprint } from './deviceFingerprint';

export async function register(
  email: string,
  password: string,
  options?: { name?: string; inviteId?: string; inviteCode?: string },
): Promise<RegisterResult> {
  const fingerprint = await getDeviceFingerprint();
  const response = await apiClient.post(
    '/api/v1/auth/register',
    {
      email,
      password,
      ...(options?.name ? { name: options.name } : {}),
      ...(options?.inviteId ? { invite_id: options.inviteId } : {}),
      ...(options?.inviteCode ? { invite_code: options.inviteCode } : {}),
    },
    { headers: { 'X-Device-Fingerprint': fingerprint } },
  );
  // ... existing token-handling
}
```

Keep all existing error handling. Update the type definitions for `RegisterResult` and the `register` signature.

**Step 3: Commit**

```bash
git add SmartCompareApp/src/services/authService.ts
git commit -m "feat(auth): register sends invite_code + X-Device-Fingerprint header" -- SmartCompareApp/src/services/authService.ts
```

---

### Task 2.3: RegisterScreen accepts invite code (typed or deep-link)

**Files:**
- Modify: `SmartCompareApp/src/screens/RegisterScreen.tsx`

**Step 1: Read current screen**

```bash
grep -n "invite_id\|InputCode\|TextInput" SmartCompareApp/src/screens/RegisterScreen.tsx | head -20
```

**Step 2: Add controlled input + pre-fill logic**

In RegisterScreen:

```tsx
const inviteIdFromDeepLink = route?.params?.invite_id;
const inviteCodeFromDeepLink = route?.params?.code;

const [inviteCode, setInviteCode] = useState<string>(
  inviteCodeFromDeepLink ?? ''
);
const [inviteCodeLocked, setInviteCodeLocked] = useState<boolean>(
  !!inviteCodeFromDeepLink,
);
const [inviteCodeError, setInviteCodeError] = useState<string>('');

const inviteCodeRegex = /^QR-[A-HJ-NP-Z2-9]{6}$/;

const validateInviteCode = (val: string) => {
  if (!val) return true; // optional
  return inviteCodeRegex.test(val);
};
```

Render below the password field, above Sign Up:

```tsx
<View style={styles.inviteRow}>
  <TextInput
    style={[styles.input, inviteCodeError && styles.inputError]}
    placeholder={t('register.inviteCode.placeholder')}
    value={inviteCode}
    onChangeText={(v) => {
      setInviteCode(v.toUpperCase().replace(/[^A-Z0-9-]/g, ''));
      setInviteCodeError('');
    }}
    editable={!inviteCodeLocked}
    autoCapitalize="characters"
    autoCorrect={false}
    maxLength={9}
    accessibilityLabel={t('register.inviteCode.accessibility')}
  />
  {inviteCodeLocked && (
    <TouchableOpacity onPress={() => { setInviteCode(''); setInviteCodeLocked(false); }}>
      <X size={16} color={colors.text.secondary} />
    </TouchableOpacity>
  )}
</View>
{inviteCodeError ? <Text style={styles.errorText}>{inviteCodeError}</Text> : null}
```

In the submit handler:

```tsx
if (inviteCode && !validateInviteCode(inviteCode)) {
  setInviteCodeError(t('register.inviteCode.invalid'));
  return;
}
// ...
await register(email, password, {
  inviteId: inviteIdFromDeepLink,
  inviteCode: inviteCode || undefined,
});
```

**Step 3: Commit**

```bash
git add SmartCompareApp/src/screens/RegisterScreen.tsx
git commit -m "feat(auth): RegisterScreen accepts invite code (typed or deep-link)" -- SmartCompareApp/src/screens/RegisterScreen.tsx
```

---

### Task 2.4: Deep link route `qaren://redeem?code=...` opens Register

**Files:**
- Modify: `SmartCompareApp/src/navigation/linking.ts` (or wherever linking config lives — check `App.tsx` first)
- Modify: `app.json` (universal link allowlist)

**Step 1: Find linking config**

```bash
grep -rn "Linking\|prefixes\|qaren://" SmartCompareApp/src/navigation SmartCompareApp/App.tsx SmartCompareApp/app.json | head -20
```

**Step 2: Add the `/redeem` deep-link pattern**

In linking config, ensure:

```ts
const linking = {
  prefixes: ['qaren://', 'https://qaren.app'],
  config: {
    screens: {
      // ... existing
      Register: {
        path: 'redeem',
        parse: {
          code: (c: string) => c.toUpperCase(),
        },
      },
      // ... rest
    },
  },
};
```

In `app.json`, the `associatedDomains` for iOS and `intentFilters` for Android should already include `qaren.app`. Verify they cover `https://qaren.app/r/*`. If not, add.

**Step 3: Commit**

```bash
git add SmartCompareApp/src/navigation/linking.ts SmartCompareApp/app.json
git commit -m "feat(link): qaren.app/r/CODE deep links to Register with pre-filled code" -- SmartCompareApp/src/navigation/linking.ts SmartCompareApp/app.json
```

---

### Task 2.5: Share message + Copy button use new copy

**Files:**
- Modify: `SmartCompareApp/src/services/referralService.ts` (or wherever the share string is constructed)
- Modify: `SmartCompareApp/src/components/ShareBottomSheet.tsx`
- Modify: `SmartCompareApp/src/components/ReferralStatusCard.tsx`

**Step 1: Add new i18n keys (request i18n-opus to add these)**

Tell i18n-opus to add:

```json
"referrals": {
  "share": {
    "messageWithLink": "I overthink every purchase. Qaren ends the debate in 30 seconds. Try it: {{link}} (or use code {{code}} in the app)",
    "messageWithLinkAR": "أفكر زيادة قبل أي شراء. قارن يحسم الجدال في 30 ثانية. جربه: {{link}} (أو استخدم رمز {{code}} داخل التطبيق)"
  }
}
```

**Step 2: Modify `ShareBottomSheet.tsx`** — the function that builds the share message. Replace existing string with:

```tsx
const message = t('referrals.share.messageWithLink', {
  link: shareLink,
  code: referralCode,
});
```

Pass `message` to `Share.share({ message })` and to the Copy intent.

**Step 3: Modify `ReferralStatusCard.tsx`** Copy handler. Replace `Clipboard.setStringAsync(referralCode)` with:

```tsx
const link = `https://qaren.app/r/${referralCode}`;
const fullMessage = t('referrals.share.messageWithLink', { link, code: referralCode });
await Clipboard.setStringAsync(fullMessage);
Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
// existing toast logic
```

**Step 4: Commit**

```bash
git add SmartCompareApp/src/components/ShareBottomSheet.tsx SmartCompareApp/src/components/ReferralStatusCard.tsx SmartCompareApp/src/services/referralService.ts
git commit -m "feat(referral): share + copy use new debate-ending message with link + code" -- SmartCompareApp/src/components/ShareBottomSheet.tsx SmartCompareApp/src/components/ReferralStatusCard.tsx SmartCompareApp/src/services/referralService.ts
```

---

### Task 2.6: ToggleRow component

**Files:**
- Create: `SmartCompareApp/src/components/ToggleRow.tsx`

**Step 1: Write the component**

```tsx
// SmartCompareApp/src/components/ToggleRow.tsx
import React, { ReactNode } from 'react';
import { View, Text, Switch, TouchableOpacity, StyleSheet } from 'react-native';
import * as Haptics from 'expo-haptics';
import { colors, spacing, typography } from '../theme';

export interface ToggleRowProps {
  icon?: ReactNode;
  label: string;
  subtitle?: string;
  value: boolean;
  onValueChange: (v: boolean) => void;
  disabled?: boolean;
  accessibilityLabel?: string;
}

export default function ToggleRow({
  icon, label, subtitle, value, onValueChange, disabled, accessibilityLabel,
}: ToggleRowProps) {
  const handlePress = () => {
    if (disabled) return;
    Haptics.selectionAsync();
    onValueChange(!value);
  };
  return (
    <TouchableOpacity
      onPress={handlePress}
      activeOpacity={0.7}
      disabled={disabled}
      accessibilityRole="switch"
      accessibilityState={{ checked: value, disabled }}
      accessibilityLabel={accessibilityLabel ?? label}
    >
      <View style={styles.row}>
        {icon ? <View style={styles.icon}>{icon}</View> : null}
        <View style={styles.text}>
          <Text style={styles.label}>{label}</Text>
          {subtitle ? <Text style={styles.subtitle}>{subtitle}</Text> : null}
        </View>
        <Switch
          value={value}
          onValueChange={(v) => { Haptics.selectionAsync(); onValueChange(v); }}
          disabled={disabled}
          trackColor={{ false: colors.border.medium, true: colors.accent }}
          thumbColor="#FFFFFF"
        />
      </View>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.md,
  },
  icon: { marginRight: spacing.sm },
  text: { flex: 1 },
  label: { ...typography.body, color: colors.text.primary },
  subtitle: { ...typography.caption, color: colors.text.secondary, marginTop: 2 },
});
```

**Step 2: Commit**

```bash
git add SmartCompareApp/src/components/ToggleRow.tsx
git commit -m "feat(component): ToggleRow — row-tappable switch with haptic" -- SmartCompareApp/src/components/ToggleRow.tsx
```

---

### Task 2.7: ProfileScreen — swap inline switches for ToggleRow, wire Support handlers, relocate Edit + Delete

**Files:**
- Modify: `SmartCompareApp/src/screens/ProfileScreen.tsx`

**Step 1: Replace the 5 inline switch rows with `<ToggleRow ... />` instances**

For each of:
- "Help improve AI quality" (~line 393–408)
- "Smart Decision Notifications" master (~line 413–428)
- 3 sub-toggles (~line 432–471)

Replace the entire `<View style={privacyRow}>` block + caption with:

```tsx
<ToggleRow
  icon={<Shield size={18} color={colors.text.secondary} />}
  label={t('profile.aiSharing.title')}
  subtitle={t('profile.aiSharing.subtitle')}
  value={aiSharingEnabled}
  onValueChange={handleAiSharingToggle}
  disabled={aiSharingSaving || preferences === null}
/>
```

For each sub-toggle (Insights, Cohort, Retrospective), pass the corresponding handler.

**Step 2: Wire Support card handlers**

Replace at lines 485, 491, 497:

```tsx
() => navigation.navigate('Legal', { doc: 'privacy' })
() => navigation.navigate('Legal', { doc: 'terms' })
() => navigation.navigate('ContactUs')
```

**Step 3: Replace Preferences handler** (line 379)

```tsx
() => navigation.navigate('EditPreferences')
```

**Step 4: Replace Edit Profile inline rename** (lines ~316–351)

Remove `editingName` state, the inline TextInput, the inline save handler. Replace the green "Edit Profile" link with:

```tsx
<TouchableOpacity onPress={() => navigation.navigate('EditProfile')}>
  <Text style={styles.editLink}>{t('profile.editProfile')}</Text>
</TouchableOpacity>
```

**Step 5: Delete the Danger card** (lines 502–517) — relocated to EditProfile.

**Step 6: Commit**

```bash
git add SmartCompareApp/src/screens/ProfileScreen.tsx
git commit -m "feat(profile): swap switches to ToggleRow, wire Support nav, relocate Edit + Delete" -- SmartCompareApp/src/screens/ProfileScreen.tsx
```

---

### Task 2.8: LegalScreen

**Files:**
- Create: `SmartCompareApp/src/screens/LegalScreen.tsx`

**Step 1: Write the screen**

```tsx
// SmartCompareApp/src/screens/LegalScreen.tsx
//
// Renders /api/v1/legal/{privacy_policy,terms_of_service} markdown.
// CONTENT note: backend MD files at app/legal/*.md are stale ("SmartCompare").
// Content rewrite owned by docs/plans/2026-05-06-tos-fact-base.md.

import React, { useEffect, useState } from 'react';
import { View, Text, ScrollView, ActivityIndicator, StyleSheet, TouchableOpacity, SafeAreaView } from 'react-native';
import Markdown from 'react-native-markdown-display';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { useTranslation } from 'react-i18next';
import { ChevronLeft } from 'lucide-react-native';
import { colors, spacing, typography } from '../theme';
import { apiClient } from '../services/api';

type LegalDoc = 'privacy' | 'terms';

export default function LegalScreen({ route, navigation }: any) {
  const { doc } = route.params as { doc: LegalDoc };
  const { t } = useTranslation();
  const [content, setContent] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const endpoint = doc === 'privacy' ? '/api/v1/legal/privacy_policy' : '/api/v1/legal/terms_of_service';
  const cacheKey = `legal_cache_${doc}`;

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.get(endpoint);
      const md = res.data?.content ?? '';
      setContent(md);
      await AsyncStorage.setItem(cacheKey, md);
    } catch (e) {
      const cached = await AsyncStorage.getItem(cacheKey);
      if (cached) {
        setContent(cached);
        setError(t('legal.offline.banner'));
      } else {
        setError(t('legal.error.title'));
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [doc]);

  const title = doc === 'privacy' ? t('profile.privacy') : t('profile.terms');

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => navigation.goBack()}>
          <ChevronLeft size={24} color={colors.text.primary} />
        </TouchableOpacity>
        <Text style={styles.title}>{title}</Text>
        <View style={{ width: 24 }} />
      </View>
      {loading && !content && (
        <View style={styles.center}><ActivityIndicator size="large" color={colors.accent} /></View>
      )}
      {error && !content && (
        <View style={styles.center}>
          <Text style={styles.errorText}>{error}</Text>
          <TouchableOpacity onPress={load} style={styles.retryBtn}>
            <Text style={styles.retryText}>{t('legal.error.retry')}</Text>
          </TouchableOpacity>
        </View>
      )}
      {content && (
        <ScrollView contentContainerStyle={styles.scroll}>
          {error && <Text style={styles.offlineBanner}>{error}</Text>}
          <Markdown style={markdownStyles}>{content}</Markdown>
        </ScrollView>
      )}
    </SafeAreaView>
  );
}

const markdownStyles = {
  heading1: { ...typography.title, color: colors.text.primary, marginTop: spacing.lg, marginBottom: spacing.sm },
  heading2: { ...typography.bodyEmphasis, color: colors.text.primary, marginTop: spacing.md, marginBottom: spacing.xs },
  body: { ...typography.body, color: colors.text.primary, lineHeight: 22 },
  link: { color: colors.accent },
  list_item: { marginVertical: spacing.xs },
};

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg.primary },
  header: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
    paddingHorizontal: spacing.md, paddingVertical: spacing.sm,
    borderBottomWidth: 1, borderBottomColor: colors.border.light,
  },
  title: { ...typography.bodyEmphasis, color: colors.text.primary },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: spacing.lg },
  scroll: { padding: spacing.md },
  errorText: { ...typography.body, color: colors.text.secondary, textAlign: 'center', marginBottom: spacing.md },
  retryBtn: { paddingHorizontal: spacing.lg, paddingVertical: spacing.sm, backgroundColor: colors.accent, borderRadius: 8 },
  retryText: { color: '#FFF', ...typography.bodyEmphasis },
  offlineBanner: {
    backgroundColor: colors.bg.subtle, color: colors.text.secondary,
    padding: spacing.sm, marginBottom: spacing.md, borderRadius: 6,
  },
});
```

**Step 2: Register route in App.tsx / main navigator** — `<Stack.Screen name="Legal" component={LegalScreen} />`

**Step 3: Commit**

```bash
git add SmartCompareApp/src/screens/LegalScreen.tsx SmartCompareApp/App.tsx
git commit -m "feat(legal): LegalScreen renders /api/v1/legal/* markdown with offline cache" -- SmartCompareApp/src/screens/LegalScreen.tsx SmartCompareApp/App.tsx
```

---

### Task 2.9: ContactUsScreen

**Files:**
- Create: `SmartCompareApp/src/screens/ContactUsScreen.tsx`

**Step 1: Write the screen**

```tsx
// SmartCompareApp/src/screens/ContactUsScreen.tsx
import React, { useState } from 'react';
import { View, Text, TextInput, TouchableOpacity, StyleSheet, ScrollView, SafeAreaView, KeyboardAvoidingView, Platform, Linking, ActivityIndicator } from 'react-native';
import { useTranslation } from 'react-i18next';
import { ChevronLeft } from 'lucide-react-native';
import { colors, spacing, typography, radii } from '../theme';
import { apiClient } from '../services/api';

type Category = 'bug' | 'suggestion' | 'business' | 'other';
const CATEGORIES: Category[] = ['bug', 'suggestion', 'business', 'other'];

export default function ContactUsScreen({ navigation }: any) {
  const { t } = useTranslation();
  const [category, setCategory] = useState<Category>('bug');
  const [subject, setSubject] = useState('');
  const [message, setMessage] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [lastSubmitAt, setLastSubmitAt] = useState(0);

  const canSubmit = message.trim().length >= 10 && !submitting;

  const submit = async () => {
    if (Date.now() - lastSubmitAt < 30000) {
      setError(t('contact.error.rateLimit'));
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await apiClient.post('/api/v1/feedback', {
        feedback_type: `contact_us_${category}`,
        message: subject ? `${subject}\n\n${message}` : message,
      });
      setSuccess(true);
      setLastSubmitAt(Date.now());
    } catch (e: any) {
      setError(t('contact.error.generic'));
    } finally {
      setSubmitting(false);
    }
  };

  if (success) {
    return (
      <SafeAreaView style={styles.container}>
        <Header navigation={navigation} title={t('contact.title')} />
        <View style={styles.center}>
          <Text style={styles.successTitle}>{t('contact.success.title')}</Text>
          <Text style={styles.successBody}>{t('contact.success.body')}</Text>
          <TouchableOpacity
            onPress={() => { setSuccess(false); setSubject(''); setMessage(''); }}
            style={styles.btn}
          >
            <Text style={styles.btnText}>{t('contact.submit.again')}</Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={{ flex: 1 }}>
        <Header navigation={navigation} title={t('contact.title')} />
        <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
          <Text style={styles.label}>{t('contact.category.label')}</Text>
          <View style={styles.categoryRow}>
            {CATEGORIES.map((c) => (
              <TouchableOpacity
                key={c}
                onPress={() => setCategory(c)}
                style={[styles.categoryChip, category === c && styles.categoryChipActive]}
              >
                <Text style={[styles.categoryText, category === c && styles.categoryTextActive]}>
                  {t(`contact.category.${c}`)}
                </Text>
              </TouchableOpacity>
            ))}
          </View>
          <TextInput
            style={styles.input}
            placeholder={t('contact.subject.placeholder')}
            placeholderTextColor={colors.text.placeholder}
            value={subject}
            onChangeText={setSubject}
            maxLength={120}
          />
          <TextInput
            style={[styles.input, styles.textarea]}
            placeholder={t('contact.message.placeholder')}
            placeholderTextColor={colors.text.placeholder}
            value={message}
            onChangeText={setMessage}
            multiline
            maxLength={2000}
            numberOfLines={6}
          />
          {error ? <Text style={styles.errorText}>{error}</Text> : null}
          <TouchableOpacity
            onPress={submit}
            disabled={!canSubmit}
            style={[styles.btn, !canSubmit && styles.btnDisabled]}
          >
            {submitting ? <ActivityIndicator color="#FFF" /> :
              <Text style={styles.btnText}>{t('contact.submit')}</Text>}
          </TouchableOpacity>
          <TouchableOpacity
            onPress={() => Linking.openURL('mailto:support@qaren.app?subject=Qaren%20Support')}
            style={styles.emailFallback}
          >
            <Text style={styles.emailFallbackText}>{t('contact.email.fallback')}</Text>
          </TouchableOpacity>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

function Header({ navigation, title }: any) {
  return (
    <View style={styles.header}>
      <TouchableOpacity onPress={() => navigation.goBack()}>
        <ChevronLeft size={24} color={colors.text.primary} />
      </TouchableOpacity>
      <Text style={styles.title}>{title}</Text>
      <View style={{ width: 24 }} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg.primary },
  header: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
    paddingHorizontal: spacing.md, paddingVertical: spacing.sm,
    borderBottomWidth: 1, borderBottomColor: colors.border.light,
  },
  title: { ...typography.bodyEmphasis, color: colors.text.primary },
  scroll: { padding: spacing.md },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: spacing.lg },
  label: { ...typography.caption, color: colors.text.secondary, marginBottom: spacing.sm, textTransform: 'uppercase' },
  categoryRow: { flexDirection: 'row', gap: spacing.sm, marginBottom: spacing.md, flexWrap: 'wrap' },
  categoryChip: {
    paddingHorizontal: spacing.md, paddingVertical: spacing.sm,
    backgroundColor: colors.bg.subtle, borderRadius: radii.pill,
  },
  categoryChipActive: { backgroundColor: colors.accent },
  categoryText: { ...typography.bodyEmphasis, color: colors.text.primary },
  categoryTextActive: { color: '#FFF' },
  input: {
    backgroundColor: colors.bg.subtle, padding: spacing.md, borderRadius: 12,
    marginBottom: spacing.md, ...typography.body, color: colors.text.primary,
  },
  textarea: { minHeight: 120, textAlignVertical: 'top' },
  btn: {
    backgroundColor: colors.cta.primary, padding: spacing.md, borderRadius: radii.pill,
    alignItems: 'center', marginTop: spacing.sm,
  },
  btnDisabled: { opacity: 0.4 },
  btnText: { color: '#FFF', ...typography.bodyEmphasis },
  emailFallback: { alignItems: 'center', padding: spacing.lg },
  emailFallbackText: { ...typography.body, color: colors.accent },
  errorText: { ...typography.caption, color: colors.destructive, marginBottom: spacing.sm },
  successTitle: { ...typography.title, color: colors.text.primary, marginBottom: spacing.md, textAlign: 'center' },
  successBody: { ...typography.body, color: colors.text.secondary, marginBottom: spacing.lg, textAlign: 'center' },
});
```

**Step 2: Register route in App.tsx** — `<Stack.Screen name="ContactUs" component={ContactUsScreen} />`

**Step 3: Commit**

```bash
git add SmartCompareApp/src/screens/ContactUsScreen.tsx SmartCompareApp/App.tsx
git commit -m "feat(support): ContactUsScreen form posts to /feedback with category routing" -- SmartCompareApp/src/screens/ContactUsScreen.tsx SmartCompareApp/App.tsx
```

---

### Task 2.10: EditProfileScreen

**Files:**
- Create: `SmartCompareApp/src/screens/EditProfileScreen.tsx`

Build a screen with:
- Header (back + title)
- Avatar circle (non-tappable, "Photo upload coming soon")
- Display name input + Save button
- Email read-only text row
- "Edit style profile →" row → opens existing cohort modal (extract handler from ProfileScreen or pass via navigation params)
- Danger card: "Delete account" red row with confirm flow (extracted from ProfileScreen)

Use existing `PUT /api/v1/auth/profile` for name. Use existing `delete_user_cascade()` for delete. Use existing cohort modal for demographics.

Register route in App.tsx. Commit.

---

### Task 2.11: PrioritiesPicker, BudgetPicker, LifestylePicker, BrandAttitudePicker components

**Files:**
- Create: `SmartCompareApp/src/components/PrioritiesPicker.tsx` — extract from `Step08Priorities.tsx`
- Create: `SmartCompareApp/src/components/BudgetPicker.tsx` — extract from `Step09Budget.tsx`
- Create: `SmartCompareApp/src/components/LifestylePicker.tsx` — NEW; 11 toggle chips
- Create: `SmartCompareApp/src/components/BrandAttitudePicker.tsx` — extract from `Step10BrandAttitude.tsx`

Each takes `value` + `onChange` props. Stateless. Reusable from onboarding AND EditPreferencesFlow.

Refactor the onboarding steps to USE these new components (so we don't duplicate). One commit per extracted component.

---

### Task 2.12: EditPreferencesFlow orchestrator

**Files:**
- Create: `SmartCompareApp/src/screens/EditPreferencesFlow.tsx`

```tsx
// SmartCompareApp/src/screens/EditPreferencesFlow.tsx
// B2 sequential 4-page preferences edit (per Bundle A design §2).

import React, { useEffect, useState } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, SafeAreaView, ActivityIndicator } from 'react-native';
import { useTranslation } from 'react-i18next';
import { ChevronLeft, X } from 'lucide-react-native';
import * as Haptics from 'expo-haptics';
import { colors, spacing, typography, radii } from '../theme';
import PrioritiesPicker from '../components/PrioritiesPicker';
import BudgetPicker from '../components/BudgetPicker';
import LifestylePicker from '../components/LifestylePicker';
import BrandAttitudePicker from '../components/BrandAttitudePicker';
import { getPreferences, savePreferences } from '../services/api';
import type { UserPreferences } from '../types';

export default function EditPreferencesFlow({ navigation }: any) {
  const { t } = useTranslation();
  const [pageIndex, setPageIndex] = useState(0);
  const [prefs, setPrefs] = useState<UserPreferences | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const p = await getPreferences();
        setPrefs(p ?? {
          priorities: [], budget: 'mid', lifestyle: [], brand_attitude: 'open',
          ai_sharing_enabled: true, notifications_enabled: true, notification_types: {},
        });
      } catch {
        setError(t('common.error.generic'));
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const next = () => { Haptics.selectionAsync(); setPageIndex((i) => Math.min(i + 1, 3)); };
  const back = () => {
    if (pageIndex === 0) navigation.goBack();
    else { Haptics.selectionAsync(); setPageIndex((i) => i - 1); }
  };

  const save = async () => {
    if (!prefs) return;
    setSaving(true);
    setError(null);
    try {
      const result = await savePreferences(prefs);
      if (result.success) {
        Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
        navigation.goBack();
      } else {
        setError(t('preferences.error.saveFailed'));
      }
    } catch {
      setError(t('common.error.generic'));
    } finally {
      setSaving(false);
    }
  };

  if (loading || !prefs) {
    return <SafeAreaView style={styles.container}><View style={styles.center}><ActivityIndicator size="large" color={colors.accent} /></View></SafeAreaView>;
  }

  const isLast = pageIndex === 3;
  const titles = ['priorities', 'budget', 'lifestyle', 'brand'];
  const pageTitle = t(`preferences.${titles[pageIndex]}.title`);

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={back}>
          {pageIndex === 0 ? <X size={24} color={colors.text.primary} /> : <ChevronLeft size={24} color={colors.text.primary} />}
        </TouchableOpacity>
        <Text style={styles.pageDots}>{`${pageIndex + 1} / 4`}</Text>
        <View style={{ width: 24 }} />
      </View>
      <View style={styles.body}>
        <Text style={styles.pageTitle}>{pageTitle}</Text>
        {pageIndex === 0 && <PrioritiesPicker value={prefs.priorities ?? []} onChange={(v) => setPrefs({ ...prefs, priorities: v })} />}
        {pageIndex === 1 && <BudgetPicker value={prefs.budget ?? 'mid'} onChange={(v) => setPrefs({ ...prefs, budget: v })} />}
        {pageIndex === 2 && <LifestylePicker value={prefs.lifestyle ?? []} onChange={(v) => setPrefs({ ...prefs, lifestyle: v })} />}
        {pageIndex === 3 && <BrandAttitudePicker value={prefs.brand_attitude ?? 'open'} onChange={(v) => setPrefs({ ...prefs, brand_attitude: v })} />}
      </View>
      {error ? <Text style={styles.errorText}>{error}</Text> : null}
      <View style={styles.footer}>
        <TouchableOpacity
          onPress={isLast ? save : next}
          disabled={saving}
          style={[styles.btn, saving && styles.btnDisabled]}
        >
          {saving ? <ActivityIndicator color="#FFF" /> :
            <Text style={styles.btnText}>{isLast ? t('preferences.flow.save') : t('preferences.flow.continue')}</Text>}
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.bg.primary },
  header: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
    paddingHorizontal: spacing.md, paddingVertical: spacing.sm,
    borderBottomWidth: 1, borderBottomColor: colors.border.light,
  },
  pageDots: { ...typography.caption, color: colors.text.secondary },
  body: { flex: 1, padding: spacing.lg },
  pageTitle: { ...typography.title, color: colors.text.primary, marginBottom: spacing.lg },
  footer: { padding: spacing.md, borderTopWidth: 1, borderTopColor: colors.border.light },
  btn: { backgroundColor: colors.cta.primary, padding: spacing.md, borderRadius: radii.pill, alignItems: 'center' },
  btnDisabled: { opacity: 0.4 },
  btnText: { color: '#FFF', ...typography.bodyEmphasis },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  errorText: { ...typography.caption, color: colors.destructive, padding: spacing.md, textAlign: 'center' },
});
```

Register route `<Stack.Screen name="EditPreferences" component={EditPreferencesFlow} />` in App.tsx. Commit.

---

### Task 2.13: ResultsScreen defensive guards + empty state

**Files:**
- Modify: `SmartCompareApp/src/screens/ResultsScreen.tsx`

**Step 1: Add a helper at top of component**

```tsx
const products = (result?.overview?.products ?? result?.products ?? []) as any[];

if (products.length < 2) {
  return <EmptyResultState navigation={navigation} />;
}
```

`EmptyResultState` is a small inline component showing a friendly message + "Go home" button.

**Step 2: Patch every other reference**

For lines 325, 335, 373, 706, 709 — replace `result.specs?.products`, `result.reviews?.products`, `result.overview!.products[i]` with safe variants:

```tsx
const specsProducts = isNewFormat ? (result?.specs?.products ?? []) : products;
const overviewProduct = isNewFormat ? result?.overview?.products?.[index] ?? null : null;
```

**Step 3: Commit**

```bash
git add SmartCompareApp/src/screens/ResultsScreen.tsx
git commit -m "fix(results): defensive guards + empty state — kill 'products of undefined' crash" -- SmartCompareApp/src/screens/ResultsScreen.tsx
```

---

### Task 2.14: HistoryScreen uses product_names from list endpoint

**Files:**
- Modify: `SmartCompareApp/src/screens/HistoryScreen.tsx`

**Step 1: Delete the broken full_response lookup at line 173**

**Step 2: Rewrite the title rendering at line 187**

```tsx
const formatTitle = (item: HistoryItem) => {
  const names = item.product_names ?? [];
  if (names.length >= 2) {
    const title = `${names[0]} vs ${names[1]}`;
    return title.length > 40 ? title.slice(0, 37) + '…' : title;
  }
  return item.query?.trim() || t('history.row.untitled');
};

// in render:
<Text style={styles.cardQuery} numberOfLines={1}>{formatTitle(item)}</Text>
```

**Step 3: Commit**

```bash
git add SmartCompareApp/src/screens/HistoryScreen.tsx
git commit -m "fix(history): render real product_names from list endpoint summary" -- SmartCompareApp/src/screens/HistoryScreen.tsx
```

---

## Phase 3 — i18n strings + leftover-EN sweep (i18n-opus owns; ~6 tasks)

### Task 3.1: Add all new i18n keys (EN + AR)

**Files:**
- Modify: `SmartCompareApp/src/i18n/en.json`
- Modify: `SmartCompareApp/src/i18n/ar.json`

Add the full set:

```json
{
  "register.inviteCode.placeholder": { "en": "Have an invite code? (optional)", "ar": "عندك رمز دعوة؟ (اختياري)" },
  "register.inviteCode.accessibility": { "en": "Invite code", "ar": "رمز الدعوة" },
  "register.inviteCode.invalid": { "en": "Code format is QR- followed by 6 characters", "ar": "صيغة الرمز QR- متبوع بـ 6 خانات" },

  "referrals.share.messageWithLink": {
    "en": "I overthink every purchase. Qaren ends the debate in 30 seconds. Try it: {{link}} (or use code {{code}} in the app)",
    "ar": "أفكر زيادة قبل أي شراء. قارن يحسم الجدال في 30 ثانية. جربه: {{link}} (أو استخدم رمز {{code}} داخل التطبيق)"
  },

  "profile.changePassword": { "en": "Change Password", "ar": "تغيير كلمة المرور" },
  "profile.editProfile": { "en": "Edit Profile", "ar": "تعديل الملف" },

  "history.row.untitled": { "en": "Untitled comparison", "ar": "مقارنة بدون عنوان" },

  "legal.loading": { "en": "Loading…", "ar": "جارٍ التحميل…" },
  "legal.error.title": { "en": "Couldn't load right now.", "ar": "تعذّر التحميل الآن." },
  "legal.error.retry": { "en": "Try again", "ar": "حاول مجددًا" },
  "legal.offline.banner": { "en": "Showing offline copy", "ar": "العرض من النسخة المحفوظة" },

  "contact.title": { "en": "Contact Us", "ar": "اتصل بنا" },
  "contact.category.label": { "en": "Category", "ar": "الفئة" },
  "contact.category.bug": { "en": "Bug", "ar": "خلل" },
  "contact.category.suggestion": { "en": "Suggestion", "ar": "اقتراح" },
  "contact.category.business": { "en": "Business Inquiry", "ar": "استفسار تجاري" },
  "contact.category.other": { "en": "Other", "ar": "أخرى" },
  "contact.subject.placeholder": { "en": "Subject (optional)", "ar": "الموضوع (اختياري)" },
  "contact.message.placeholder": { "en": "Tell us what's on your mind…", "ar": "اكتب لنا اللي ببالك…" },
  "contact.submit": { "en": "Send", "ar": "إرسال" },
  "contact.submit.again": { "en": "Send another", "ar": "إرسال رسالة أخرى" },
  "contact.success.title": { "en": "Thanks — we read every message.", "ar": "شكرًا — نقرأ كل رسالة." },
  "contact.success.body": { "en": "We'll reply within 2 business days if a response is needed.", "ar": "نرد خلال يومي عمل لو الرسالة تحتاج رد." },
  "contact.error.generic": { "en": "Hold on — that didn't go through. Tap to retry.", "ar": "ثوانٍ — الإرسال ما تم. اضغط مرة ثانية." },
  "contact.error.rateLimit": { "en": "Give it a moment before sending again.", "ar": "خذ لحظة قبل إرسال رسالة جديدة." },
  "contact.email.fallback": { "en": "Or email us directly →", "ar": "أو راسلنا بالإيميل →" },

  "preferences.priorities.title": { "en": "What matters most to you?", "ar": "وش أهم شي بالنسبة لك؟" },
  "preferences.budget.title": { "en": "What's your usual budget?", "ar": "وش ميزانيتك عادة؟" },
  "preferences.lifestyle.title": { "en": "What describes you?", "ar": "وش يوصفك؟" },
  "preferences.brand.title": { "en": "How do you feel about brands?", "ar": "وش رأيك في العلامات التجارية؟" },
  "preferences.flow.continue": { "en": "Continue", "ar": "متابعة" },
  "preferences.flow.save": { "en": "Save", "ar": "حفظ" },
  "preferences.error.saveFailed": { "en": "Hold on — saving didn't go through. Tap to retry.", "ar": "ثوانٍ — الحفظ ما تم. اضغط مرة ثانية." },

  "preferences.lifestyle.fitness": { "en": "Fitness-focused", "ar": "مهتم باللياقة" },
  "preferences.lifestyle.budget_conscious": { "en": "Budget-conscious", "ar": "حريص على الميزانية" },
  "preferences.lifestyle.tech_enthusiast": { "en": "Tech enthusiast", "ar": "محب للتقنية" },
  "preferences.lifestyle.eco_conscious": { "en": "Eco-conscious", "ar": "صديق للبيئة" },
  "preferences.lifestyle.luxury_lover": { "en": "Luxury lover", "ar": "محب للفخامة" },
  "preferences.lifestyle.minimalist": { "en": "Minimalist", "ar": "بساطة" },
  "preferences.lifestyle.family_focused": { "en": "Family-focused", "ar": "حياة عائلية" },
  "preferences.lifestyle.frequent_traveler": { "en": "Frequent traveler", "ar": "كثير السفر" },
  "preferences.lifestyle.home_cook": { "en": "Home cook", "ar": "أطبخ في البيت" },
  "preferences.lifestyle.outdoors": { "en": "Outdoor enthusiast", "ar": "محب للطلعات" },
  "preferences.lifestyle.creative": { "en": "Creative / hobbyist", "ar": "صاحب هواية" },

  "editProfile.title": { "en": "Edit Profile", "ar": "تعديل الملف" },
  "editProfile.avatar.placeholder": { "en": "Photo upload coming soon", "ar": "إضافة الصورة قريبًا" },
  "editProfile.section.account": { "en": "Account", "ar": "الحساب" },
  "editProfile.editStyleProfile": { "en": "Edit style profile", "ar": "تعديل ملف التفضيلات" },
  "editProfile.dangerZone": { "en": "Account actions", "ar": "إجراءات الحساب" },
  "editProfile.deleteAccount": { "en": "Delete account", "ar": "حذف الحساب" },

  "common.error.generic": { "en": "Hold on — something didn't go through.", "ar": "ثوانٍ — في شي ما تم." }
}
```

Add all keys to BOTH `en.json` AND `ar.json` in their proper nested locations. NO scary copy — all phrasing follows CLAUDE.md "approved vocabulary."

**Step 2: Run jest to confirm no missing translation key warnings**

```bash
cd SmartCompareApp
npm test -- --silent 2>&1 | grep -i "missing\|undefined translation"
# Expected: no output
```

**Step 3: Commit**

```bash
git add SmartCompareApp/src/i18n/en.json SmartCompareApp/src/i18n/ar.json
git commit -m "feat(i18n): add Bundle A strings (register/referral/profile/contact/preferences/editProfile)" -- SmartCompareApp/src/i18n/en.json SmartCompareApp/src/i18n/ar.json
```

---

### Task 3.2: Localized date + relative time helpers

**Files:**
- Create: `SmartCompareApp/src/utils/formatDate.ts`

```ts
// SmartCompareApp/src/utils/formatDate.ts
//
// Locale-aware date + relative-time formatting. Used by HistoryScreen
// and anywhere else with timestamps.

export function formatDate(d: Date | string | number, language: 'en' | 'ar'): string {
  const date = d instanceof Date ? d : new Date(d);
  const locale = language === 'ar' ? 'ar-SA' : 'en-US';
  return date.toLocaleDateString(locale, { month: 'short', day: 'numeric' });
}

export function formatTimeAgo(d: Date | string | number, language: 'en' | 'ar'): string {
  const date = d instanceof Date ? d : new Date(d);
  const diffMs = Date.now() - date.getTime();
  const diffMin = Math.floor(diffMs / 60_000);
  const diffHr = Math.floor(diffMs / 3_600_000);
  const diffDay = Math.floor(diffMs / 86_400_000);

  if (language === 'ar') {
    if (diffMin < 1) return 'الآن';
    if (diffMin < 60) return `منذ ${diffMin} دقيقة`;
    if (diffHr < 24) return `منذ ${diffHr} ساعة`;
    if (diffDay < 7) return `منذ ${diffDay} يوم`;
    return formatDate(date, 'ar');
  }
  if (diffMin < 1) return 'just now';
  if (diffMin < 60) return `${diffMin}m ago`;
  if (diffHr < 24) return `${diffHr}h ago`;
  if (diffDay < 7) return `${diffDay}d ago`;
  return formatDate(date, 'en');
}
```

Replace all current `formatTimeAgo` usage in HistoryScreen + anywhere else found via grep. Commit.

---

### Task 3.3: Leftover-EN grep audit + conversion

```bash
cd SmartCompareApp
grep -rn '"[A-Z][a-z]' src/screens src/components \
  | grep -v 'colors\.\|styles\.\|typography\.\|spacing\.\|radii\.\|importStatement\|import\|require\|console\.' \
  | grep -v '__tests__'
```

For every hit (excluding obvious code constants), wrap with `t(...)`. Add corresponding keys to `en.json` + `ar.json`. Commit in chunks of ~10 strings.

---

### Task 3.4: ESLint rule (regression prevention)

Add `eslint-plugin-i18next` to dev deps:

```bash
cd SmartCompareApp
npm install --save-dev eslint-plugin-i18next
```

Update `.eslintrc.js`:

```js
{
  plugins: ['i18next'],
  rules: {
    'i18next/no-literal-string': ['error', {
      markupOnly: true,
      ignoreAttribute: ['testID', 'accessibilityLabel'],
    }],
  },
  overrides: [
    { files: ['**/__tests__/**', '**/*.test.*'], rules: { 'i18next/no-literal-string': 'off' } },
  ],
}
```

Run `npm run lint` and fix any new findings (likely will surface another batch — convert each to `t(...)` calls). Commit.

---

### Task 3.5: i18n-opus idle work

While waiting for QA: run an Arabic mode visual smoke pass against the design copy rules in CLAUDE.md ("Copy contract: ZERO scary copy"). Flag any new strings that match the forbidden vocabulary list (`couldn't / failed to / try again / locked / تعذر / فشل / حاول`) and rewrite to approved alternatives.

---

### Task 3.6: i18n-opus submits work for cross-QA

Post in TaskList: "i18n-opus phase 3 complete. Awaiting review."

---

## Phase 4 — Jest tests + cross-QA (qa-opus owns; ~10 tasks)

### Task 4.1: deviceFingerprint test

**Files:**
- Create: `SmartCompareApp/src/services/__tests__/deviceFingerprint.test.ts`

```ts
import { getDeviceFingerprint, _resetCacheForTests } from '../deviceFingerprint';
import * as SecureStore from 'expo-secure-store';

jest.mock('expo-application', () => ({ applicationId: 'app.qaren.test' }));
jest.mock('expo-device', () => ({ osBuildId: 'iPhone15,2/21D' }));
jest.mock('expo-secure-store');
jest.mock('expo-crypto', () => ({
  digestStringAsync: jest.fn().mockResolvedValue('hashedvalue'),
  randomUUID: jest.fn(() => 'fixed-uuid'),
  CryptoDigestAlgorithm: { SHA256: 'SHA256' },
}));

describe('deviceFingerprint', () => {
  beforeEach(() => {
    _resetCacheForTests();
    jest.clearAllMocks();
  });

  it('creates and persists a nonce on first call', async () => {
    (SecureStore.getItemAsync as jest.Mock).mockResolvedValue(null);
    await getDeviceFingerprint();
    expect(SecureStore.setItemAsync).toHaveBeenCalledWith('device_fp_nonce', 'fixed-uuid');
  });

  it('reuses existing nonce on subsequent calls', async () => {
    (SecureStore.getItemAsync as jest.Mock).mockResolvedValue('persisted-nonce');
    await getDeviceFingerprint();
    expect(SecureStore.setItemAsync).not.toHaveBeenCalled();
  });

  it('returns same hash across calls (cached)', async () => {
    (SecureStore.getItemAsync as jest.Mock).mockResolvedValue('persisted-nonce');
    const a = await getDeviceFingerprint();
    const b = await getDeviceFingerprint();
    expect(a).toBe(b);
  });
});
```

Run RED, then frontend code already exists, then GREEN. Commit.

---

### Task 4.2: HistoryScreen renders product_names

**Files:**
- Create or update: `SmartCompareApp/src/screens/__tests__/HistoryScreen.test.tsx`

Test cases:
- renders `"iPhone 15 vs Galaxy S24"` when both product_names present
- falls back to `item.query` when product_names empty
- shows `t('history.row.untitled')` when both names + query empty
- truncates to 40 chars with ellipsis

Run RED, GREEN (HistoryScreen already implemented), commit.

---

### Task 4.3: ResultsScreen empty state + guards

**Files:**
- Update: `SmartCompareApp/src/screens/__tests__/ResultsScreen.test.tsx`

Test cases:
- renders normally with new format (`result.overview.products` shape)
- renders normally with legacy alias format (`result.products` shape)
- shows EmptyResultState when products.length < 2
- does NOT crash when result is undefined
- does NOT crash when result.overview is undefined
- does NOT crash when result.specs is undefined

Run RED, GREEN, commit.

---

### Task 4.4: ToggleRow component

**Files:**
- Create: `SmartCompareApp/src/components/__tests__/ToggleRow.test.tsx`

Test cases:
- tapping anywhere on the row flips the switch (fireEvent.press on the row, not the switch)
- haptic fires on toggle
- disabled row doesn't respond to taps

Commit.

---

### Task 4.5: ContactUsScreen flow

Test cases:
- can't submit with empty message
- can't submit with <10 char message
- selecting category updates state
- submit posts to `/feedback` with `contact_us_{category}` prefix
- success state replaces form
- "Send another" returns to form
- rate-limit guard prevents 2 submissions within 30s

Commit.

---

### Task 4.6: LegalScreen flow

Test cases:
- fetches markdown from correct endpoint based on `doc` prop
- renders markdown
- shows skeleton during loading
- shows error + retry button on fetch fail
- offline cache (AsyncStorage) serves on network error after first successful load
- "Try again" button triggers re-fetch

Commit.

---

### Task 4.7: EditPreferencesFlow

Test cases:
- pre-fills all 4 pages with values from `getPreferences()`
- Continue advances pageIndex
- Back decrements pageIndex (or closes on page 1)
- page 4 button label is "Save"
- Save calls `savePreferences` exactly once with merged payload
- Cancel discards changes (no save call)
- shows error inline if save fails

Commit.

---

### Task 4.8: RegisterScreen invite code field

Test cases:
- typed code validates format on submit
- invalid format shows error, blocks submit
- code from `route.params.code` pre-fills + locks the field
- clear icon unlocks the field
- valid code is sent in register payload

Commit.

---

### Task 4.9: ProfileScreen — all ToggleRow rows work

Snapshot test in EN + AR locales. Verify each ToggleRow toggles correctly. Verify nav handlers call `navigation.navigate('Legal'|'ContactUs'|'EditPreferences'|'EditProfile')`.

Commit.

---

### Task 4.10: qa-opus cross-review pass

For EVERY commit on this branch authored by another agent:
1. Read the diff (`git show <hash>`)
2. Verify the test file exists, has at least one failing-then-passing trajectory in commit history
3. Verify the implementation matches the design doc Section it claims to implement
4. Run the tests locally
5. If any check fails → post a "send-back" review in TaskList with specific reasons (file:line, what's wrong, what design clause is violated)

Send-back protocol: do NOT approve subpar work to keep the schedule. Genuine fixes only.

---

## Phase 5 — Integration tests + final cross-QA gate (qa-opus owns; ~4 tasks)

### Task 5.1: Backend full test suite

```bash
cd $WORKTREE
python -m pytest tests/ -v -m "not (live_unit or live_db or integration)" --timeout=180 --cov=app --cov-report=term-missing
# Expected: all pass, coverage on Bundle A files ≥80%
```

Capture coverage report; flag any new file under 80% to its owner for more tests.

---

### Task 5.2: Security regression — MUST stay 100%

```bash
python -m pytest tests/test_security_regression.py -v
# Expected: ~98 tests, 100% pass
```

If anything fails → SEND BACK to the file owner with the test name and stacktrace. No exceptions to security regression discipline.

---

### Task 5.3: Frontend tsc + jest + lint

```bash
cd SmartCompareApp
npx tsc --noEmit
# Expected: 0 errors. Trust ONLY this — ignore stale LSP diagnostics per CLAUDE.md.

npm test -- --coverage
# Expected: all pass, ≥80% coverage on Bundle A files

npm run lint
# Expected: 0 errors (i18n rule active)

npx expo-doctor
# Expected: all green
```

---

### Task 5.4: Cross-QA disassembly gate

Before posting "team can disassemble," qa-opus verifies ALL of:

1. ✅ All 7 design sections implemented (check each task in this plan is committed)
2. ✅ All gates from §7.1 of design doc pass (run them again)
3. ✅ Every commit on this branch authored by an agent has been reviewed by a DIFFERENT agent (check `git log --author` vs review comments)
4. ✅ No outstanding "send-back" reviews in TaskList
5. ✅ Migrations 020 + 021 applied successfully via Supabase MCP (verified by querying information_schema)
6. ✅ Railway env vars set: `ENABLE_REFERRAL_SYSTEM=true`, `SENTRY_DSN=*`

If any item fails → identify the owning agent → assign them the fix → DO NOT disassemble.

If all green → post: "Bundle A ready for manual QA + merge. Disassembling team."

---

## Phase 6 — Manual QA + merge (team coordinator, post-disassembly)

### Task 6.1: EAS dev build smoke test

```bash
cd SmartCompareApp
eas build --profile development --platform ios
# or eas build --profile development --platform android
# Wait for build, install on physical device
```

Run all 12 manual QA items from design §7.2 on the device. NOT Expo Go — Expo Go is what's making the phone hot and feels slow.

Record results in `docs/CONTEXT_SESSION_LOG.md` (Session 44 entry).

### Task 6.2: Apply migrations to production Supabase

```bash
# Via Supabase MCP — preferred
mcp__plugin_supabase_supabase__apply_migration({name: "020_comparisons_schema_version", query: "..."})
mcp__plugin_supabase_supabase__apply_migration({name: "021_device_fingerprint_users", query: "..."})
```

Verify via:

```bash
curl 'https://qulajmyxdbdkchvecmvc.supabase.co/rest/v1/comparisons?select=schema_version&limit=1' \
  -H "apikey: $SUPABASE_ANON_KEY"
# Expected: returns at least one row with schema_version field
```

### Task 6.3: Deploy backend

```bash
git checkout main
git merge feature/bundle-a-p0 --no-ff -m "Merge Bundle A — P0 pre-launch fixes (#PR)"
git push origin main
# Railway auto-deploys backend in ~90s
sleep 100
curl https://web-production-58776.up.railway.app/health
# Expected: {"status":"ok"}
```

### Task 6.4: Deploy frontend JS bundle

```bash
cd SmartCompareApp
eas update --branch preview --message "Bundle A — P0 pre-launch fixes"
```

Smoke-test on a real device (EAS dev build) — confirm all 12 manual QA items pass against the live deployment.

If green for 24 hours of tester use:

```bash
eas update --branch production --message "Bundle A — P0 pre-launch fixes"
```

### Task 6.5: Post-merge context sweep

Update:
- `CLAUDE.md` — note Bundle A merged, list new screens/services/migrations
- `MEMORY.md` — Session 44 learnings (anything surprising)
- `docs/CONTEXT_SESSION_LOG.md` — full Session 44 entry with QA results, lessons learned

Commit on main:

```bash
git add CLAUDE.md MEMORY.md docs/CONTEXT_SESSION_LOG.md
git commit -m "docs: Bundle A merge — context sweep + Session 44 log"
git push origin main
```

### Task 6.6: Clean up worktree

```bash
cd C:\Users\SynAckITPC\Documents\ai\smartcompare
git worktree remove ../smartcompare-bundle-a
git branch -d feature/bundle-a-p0
# OR if pushed: git push origin --delete feature/bundle-a-p0
```

Per CLAUDE.md operating principle 7: **push before deleting branches.**

---

## Coordination cadence (team coordinator monitors)

- Every 15–20 min: read TaskList, identify any agent silent >30 min, prompt them
- Every 1 hour: post a team-wide status to TaskList
- On any "send-back" review: route to owning agent, expect ack within 15 min, fix or pushback with evidence within 1 hour
- On any QA failure: triage with all 4 agents, decide owner

---

## Done definition

Bundle A is DONE when:

1. All commits in this plan are merged to `main`
2. All migrations applied to production Supabase
3. All 12 manual QA items pass on a real device running the latest `eas update --branch production`
4. No Sentry errors with rate > 0.5% over 24 hours of tester use
5. CLAUDE.md + MEMORY.md + CONTEXT_SESSION_LOG.md updated

After 24-72 hours of tester stability, the next bundle's brainstorm starts: **Bundle B (Arabic deep clean)**.
