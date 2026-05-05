# Smart Decision Referral System — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.
>
> **Execution mode (per Ahmed):** TeamCreate with 4 parallel persistent Opus agents. NOT subagent-driven (fresh-per-task) and NOT serial. Each agent owns a track. Mutual QA is mandatory before disband.

**Goal:** Build a virality-optimized referral system with dual-loop rewards (Loop 1 immediate Deep Review credit on share; Loop 2 deferred +5 comparisons on invitee conversion), 3-type re-engagement push system, hybrid model routing (gpt-4o for verdict + gpt-4o-mini elsewhere with daily cap fallback), and admin cost/referral dashboards. Cut C — Maximum impact v1.

**Architecture:** 4 new Supabase tables + user-column extension; 5 new backend services; 1 new model-routing service; 4 new frontend screens/components; 2 new admin dashboards; cron-driven re-engagement detector. Feature-flagged rollout. Reuses Session 41 cohort tables for re-engagement.

**Tech Stack:** FastAPI (Python 3.12), Supabase (Postgres + Auth + RLS), Upstash Redis, OpenAI (gpt-4o + gpt-4o-mini, data-sharing enrolled), Serper, React Native + Expo (TypeScript), Expo Push, Chart.js (admin dashboards), pytest (≥80% coverage gate).

**Source design:** `docs/superpowers/specs/2026-05-05-smart-referral-system-design.md` (commit `6c1a5d0`)

---

## Team Configuration (TeamCreate)

**4 Opus-only agents (NO Sonnet, NO Haiku), bypassPermissions mode:**

| Agent | Lane | Responsible for |
|---|---|---|
| `backend-referral` | Backend track (B-tasks) | Migration, services, endpoints, cron |
| `frontend-referral` | Frontend track (F-tasks) | RN screens, components, i18n, deep links |
| `test-referral` | Test track (T-tasks) | All test files, coverage gate, security regression |
| `qa-referral` | QA track (Q-tasks) | Cross-review every other agent's PRs; smoke + canary |

**Team rules (enforced by qa-referral):**
1. 100% complete before disband
2. Mutual QA mandatory — qa-referral reviews all merges; backend/frontend/test cross-QA each other on lane boundaries
3. No idle agents — when waiting on a dependency, write red-green tests for upcoming feature OR review pending QA
4. Path-restricted commits: `git commit -- <paths>` to avoid sweeping teammates' staged files
5. Explicit lane assignment — do not freelance outside your lane
6. Acceptance: all 10 criteria in design doc Section 14 met

---

## Pre-Flight (before any task)

Each agent reads:
1. `docs/superpowers/specs/2026-05-05-smart-referral-system-design.md` (full spec)
2. `CLAUDE.md` (project conventions)
3. `MEMORY.md` (session learnings, especially git-staging-in-team)

Each agent confirms in TeamChat: "Read spec + CLAUDE.md. Ready to start lane: <lane name>."

---

## Phase 1 — Foundation (P1)

### Task B1.1 — Apply migration 014 via Supabase MCP

**Owner:** `backend-referral`
**Phase:** P1
**Depends on:** —
**Files:**
- Create: `migrations/014_referral_system.sql`

**Step 1: Write the migration**

```sql
-- 014_referral_system.sql
-- Smart Decision Referral System schema

-- 1. Extend users table
ALTER TABLE users ADD COLUMN IF NOT EXISTS referral_code TEXT UNIQUE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS referral_bonus_comparisons_this_month INT DEFAULT 0 NOT NULL;
ALTER TABLE users ADD COLUMN IF NOT EXISTS referral_bonus_reset_at TIMESTAMPTZ
    DEFAULT date_trunc('month', now()) + interval '1 month';
CREATE INDEX IF NOT EXISTS idx_users_referral_code ON users(referral_code);

-- 2. referral_invites
CREATE TABLE IF NOT EXISTS referral_invites (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  referrer_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  comparison_id UUID NOT NULL REFERENCES comparisons(id) ON DELETE CASCADE,
  share_target TEXT NOT NULL CHECK (share_target IN ('whatsapp','copy','x','telegram','snapchat','other')),
  device_fingerprint_hash TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  first_viewed_at TIMESTAMPTZ,
  redeemed_at TIMESTAMPTZ,
  redeemed_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  invitee_first_comparison_id UUID REFERENCES comparisons(id) ON DELETE SET NULL,
  flagged_reason TEXT
);
CREATE INDEX IF NOT EXISTS idx_referral_invites_referrer_created ON referral_invites(referrer_user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_referral_invites_comparison ON referral_invites(comparison_id);
CREATE INDEX IF NOT EXISTS idx_referral_invites_redeemed_by ON referral_invites(redeemed_by_user_id);

-- 3. referral_redemptions
CREATE TABLE IF NOT EXISTS referral_redemptions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  invite_id UUID NOT NULL UNIQUE REFERENCES referral_invites(id) ON DELETE CASCADE,
  referrer_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  invitee_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  loop2_comparisons_granted INT NOT NULL DEFAULT 5,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_referral_redemptions_referrer ON referral_redemptions(referrer_user_id, created_at DESC);

-- 4. deep_review_credits
CREATE TABLE IF NOT EXISTS deep_review_credits (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  source TEXT NOT NULL CHECK (source IN ('share_loop1','invitee_signup','manual')),
  granted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at TIMESTAMPTZ NOT NULL DEFAULT now() + interval '30 days',
  consumed_at TIMESTAMPTZ,
  consumed_in_comparison_id UUID REFERENCES comparisons(id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_deep_review_credits_user_available
  ON deep_review_credits(user_id, expires_at)
  WHERE consumed_at IS NULL;

-- 5. re_engagement_events
CREATE TABLE IF NOT EXISTS re_engagement_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  event_type TEXT NOT NULL CHECK (event_type IN ('decision_insight','cohort_curiosity','decision_retrospective')),
  comparison_id UUID REFERENCES comparisons(id) ON DELETE SET NULL,
  triggered_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  delivered_at TIMESTAMPTZ,
  opened_at TIMESTAMPTZ,
  content_payload JSONB
);
CREATE INDEX IF NOT EXISTS idx_re_engagement_user_triggered ON re_engagement_events(user_id, triggered_at DESC);

-- 6. RLS policies
ALTER TABLE referral_invites ENABLE ROW LEVEL SECURITY;
ALTER TABLE referral_redemptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE deep_review_credits ENABLE ROW LEVEL SECURITY;
ALTER TABLE re_engagement_events ENABLE ROW LEVEL SECURITY;

CREATE POLICY referral_invites_select_own ON referral_invites FOR SELECT TO authenticated
  USING (referrer_user_id = auth.uid() OR redeemed_by_user_id = auth.uid());
CREATE POLICY referral_redemptions_select_own ON referral_redemptions FOR SELECT TO authenticated
  USING (referrer_user_id = auth.uid() OR invitee_user_id = auth.uid());
CREATE POLICY deep_review_credits_select_own ON deep_review_credits FOR SELECT TO authenticated
  USING (user_id = auth.uid());
CREATE POLICY re_engagement_events_select_own ON re_engagement_events FOR SELECT TO authenticated
  USING (user_id = auth.uid());

-- 7. Public RPC for invitee landing
CREATE OR REPLACE FUNCTION resolve_referral_code(p_code TEXT)
RETURNS TABLE(referrer_user_id UUID, display_name TEXT)
LANGUAGE sql SECURITY DEFINER STABLE AS $$
  SELECT id, COALESCE(name, 'A friend') FROM users WHERE referral_code = p_code LIMIT 1;
$$;
GRANT EXECUTE ON FUNCTION resolve_referral_code(TEXT) TO anon, authenticated;
```

**Step 2: Apply via Supabase MCP**

Run: `mcp__plugin_supabase_supabase__apply_migration` with `name: "014_referral_system"` and `query: <contents of file>`.

Expected: success response from MCP. NOT via SQL Editor (per Session 41 learning — view-bug rollback risk).

**Step 3: Verify schema**

Run: `mcp__plugin_supabase_supabase__execute_sql` with:
```sql
SELECT table_name, column_name, data_type FROM information_schema.columns
WHERE table_name IN ('referral_invites','referral_redemptions','deep_review_credits','re_engagement_events')
ORDER BY table_name, ordinal_position;
```
Expected: all 4 tables present with correct columns.

**Step 4: Commit**

```bash
git add migrations/014_referral_system.sql
git commit -- migrations/014_referral_system.sql -m "feat(referral): migration 014 - referral system schema

4 new tables (referral_invites, referral_redemptions, deep_review_credits,
re_engagement_events) + users column extension. RLS enforced. Public
resolve_referral_code RPC for invitee landing.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task B1.2 — Referral code generation service

**Owner:** `backend-referral`
**Phase:** P1
**Depends on:** B1.1
**Files:**
- Create: `app/services/referral_service.py` (initial skeleton)
- Test: `tests/test_referral_service.py` (initial test file)

**Step 1: Write failing test**

```python
# tests/test_referral_service.py
import pytest
from app.services.referral_service import generate_referral_code, ReferralService

class TestReferralCodeGeneration:
    def test_code_format_is_qr_dash_six_chars(self):
        code = generate_referral_code()
        assert code.startswith("QR-")
        assert len(code) == 9  # "QR-" + 6 chars
        assert code[3:].isalnum()

    def test_code_excludes_ambiguous_chars(self):
        for _ in range(100):
            code = generate_referral_code()
            for ch in code[3:]:
                assert ch not in "0O1Il"

    def test_code_is_uppercase(self):
        code = generate_referral_code()
        assert code == code.upper()

    def test_codes_are_unique_across_calls(self):
        codes = {generate_referral_code() for _ in range(1000)}
        assert len(codes) > 990  # allow tiny collision tolerance
```

**Step 2: Run test to verify failure**

Run: `python -m pytest tests/test_referral_service.py::TestReferralCodeGeneration -v`
Expected: FAIL with `ImportError: cannot import name 'generate_referral_code'`.

**Step 3: Implement**

```python
# app/services/referral_service.py
"""
Referral system service.
Handles invite creation, code generation, weekly cap calculation, Loop 1/2 triggers.
"""
import secrets
from typing import Optional
from app.services.database_service import get_user_supabase_client, get_admin_supabase_client

_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # excludes 0/O/1/I/L

def generate_referral_code() -> str:
    """Generate an 8-char referral code: QR-XXXXXX from unambiguous alphabet."""
    body = "".join(secrets.choice(_CODE_ALPHABET) for _ in range(6))
    return f"QR-{body}"

class ReferralService:
    """Owns referral lifecycle: code provisioning, share/invite creation, redemption."""

    def __init__(self, access_token: Optional[str] = None):
        self.client = get_user_supabase_client(access_token) if access_token else get_admin_supabase_client()

    async def ensure_code_for_user(self, user_id: str) -> str:
        """Idempotently assign a referral code to a user. Retries on collision."""
        # Read existing
        result = self.client.table("users").select("referral_code").eq("id", user_id).single().execute()
        existing = result.data.get("referral_code") if result.data else None
        if existing:
            return existing

        # Generate + insert with retry on unique-violation
        for _ in range(5):
            code = generate_referral_code()
            try:
                self.client.table("users").update({"referral_code": code}).eq("id", user_id).execute()
                return code
            except Exception as e:
                if "duplicate key" not in str(e).lower():
                    raise
        raise RuntimeError("Failed to generate unique referral code after 5 attempts")
```

**Step 4: Run test to verify pass**

Run: `python -m pytest tests/test_referral_service.py::TestReferralCodeGeneration -v`
Expected: 4 PASSED.

**Step 5: Commit**

```bash
git add app/services/referral_service.py tests/test_referral_service.py
git commit -- app/services/referral_service.py tests/test_referral_service.py -m "feat(referral): code generation service (QR-XXXXXX format)

8-char alphanumeric codes from ambiguity-free alphabet (no 0/O/1/I/L).
4 unit tests. ensure_code_for_user is idempotent with collision retry.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task B1.3 — T&C markdown updates

**Owner:** `backend-referral`
**Phase:** P1
**Depends on:** —  (parallelizable with B1.1)
**Files:**
- Modify: `app/static/legal/terms.md` (or wherever existing T&C lives — verify in `app/api/legal_routes.py`)
- Modify: `app/static/legal/privacy.md`
- Modify: `SmartCompareApp/src/i18n/en/legal.ts` (or similar)
- Modify: `SmartCompareApp/src/i18n/ar/legal.ts`

**Step 1: Locate existing legal markdown**

Run: `grep -rln "privacy_policy\|terms_of_service" app/static/`
Expected: paths to existing markdown files. Read them.

**Step 2: Append 3 new sections per design doc Section 6** (full text in design doc — paste verbatim):
- AI Quality Improvement Program (Privacy Policy)
- Smart Decision Referrals (Terms)
- Smart Decision Notifications (Terms)

Use the EN copy from design Section 6.1, 6.2, 6.3. AR translation done by `frontend-referral` in F1.5.

**Step 3: No tests needed** (markdown content). QA-referral spot-checks rendering in F1.5.

**Step 4: Commit**

```bash
git add app/static/legal/
git commit -- app/static/legal/ -m "docs(legal): T&C + Privacy Policy updates for AI sharing + referrals + push notifications

Three new sections per design Section 6 (AI Quality Improvement Program,
Smart Decision Referrals, Smart Decision Notifications). PDPL-compliant
disclosure with opt-out language.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task B1.4 — AI sharing privacy toggle (backend)

**Owner:** `backend-referral`
**Phase:** P1
**Depends on:** —  (parallelizable)
**Files:**
- Modify: `app/api/auth_routes.py` (extend preferences PUT)
- Modify: `app/services/structured_comparison_service.py` (route OpenAI calls based on toggle)
- Test: `tests/test_auth_ai_sharing_toggle.py` (new file)

**Step 1: Write failing test**

```python
# tests/test_auth_ai_sharing_toggle.py
import pytest
from unittest.mock import patch, MagicMock

class TestAISharingToggle:
    def test_default_is_sharing_enabled(self, authed_client):
        r = authed_client.get("/api/v1/auth/profile")
        assert r.status_code == 200
        # Default ON if not set
        ai_sharing = r.json()["user"]["preferences"].get("ai_sharing_enabled", True)
        assert ai_sharing is True

    def test_user_can_disable_ai_sharing(self, authed_client):
        r = authed_client.put("/api/v1/auth/preferences", json={"ai_sharing_enabled": False})
        assert r.status_code == 200
        r2 = authed_client.get("/api/v1/auth/profile")
        assert r2.json()["user"]["preferences"]["ai_sharing_enabled"] is False

    def test_disabled_user_uses_non_shared_endpoint(self):
        # When ai_sharing_enabled=False, OpenAI calls must NOT go to data-sharing project
        with patch("app.services.openai_service.get_client") as mock_client:
            from app.services.openai_service import select_client_for_user
            select_client_for_user(user_prefs={"ai_sharing_enabled": False})
            mock_client.assert_called_with(use_shared_project=False)
```

**Step 2: Run test to verify failure**

Run: `python -m pytest tests/test_auth_ai_sharing_toggle.py -v`
Expected: FAIL on the third test (function `select_client_for_user` doesn't exist yet) and possibly first two depending on existing preferences PUT.

**Step 3: Implement**

In `app/services/openai_service.py` add:
```python
def select_client_for_user(user_prefs: dict | None = None):
    """Returns the OpenAI client. If user opted out of AI sharing, use non-shared project."""
    if user_prefs and user_prefs.get("ai_sharing_enabled") is False:
        return get_client(use_shared_project=False)
    return get_client(use_shared_project=True)  # default ON
```

Extend `auth_routes.py::PUT /preferences` to accept `ai_sharing_enabled: bool` field.

**Step 4: Run test to verify pass**

Run: `python -m pytest tests/test_auth_ai_sharing_toggle.py -v`
Expected: 3 PASSED.

**Step 5: Commit**

```bash
git add app/services/openai_service.py app/api/auth_routes.py tests/test_auth_ai_sharing_toggle.py
git commit -- app/services/openai_service.py app/api/auth_routes.py tests/test_auth_ai_sharing_toggle.py \
  -m "feat(privacy): per-user AI sharing toggle (PDPL opt-out)

Default ON. When OFF, user's OpenAI calls route to non-shared project at
standard pricing. Frontend exposes toggle in Profile (F1.5).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task F1.5 — Frontend: AI sharing toggle in Profile

**Owner:** `frontend-referral`
**Phase:** P1
**Depends on:** B1.4
**Files:**
- Modify: `SmartCompareApp/src/screens/ProfileScreen.tsx`
- Modify: `SmartCompareApp/src/services/api.ts` (add updatePreferences if not present)
- Modify: `SmartCompareApp/src/i18n/en/profile.ts`, `ar/profile.ts`

**Step 1: Add toggle UI**

In ProfileScreen, under a "Privacy" section, add a toggle bound to `preferences.ai_sharing_enabled`. On change, call `api.updatePreferences({ai_sharing_enabled: value})`.

EN copy: "Help improve AI quality" / Subtitle: "Share your queries to make Qaren smarter. We never share your name, age, or identity."
AR copy: "ساعد في تحسين الذكاء الاصطناعي" / Subtitle: "شارك استفساراتك لتحسين قارن. لا نشارك اسمك أو عمرك أو هويتك."

**Step 2: Add translation keys** to both i18n files.

**Step 3: Manual test** (Expo Go or dev build): toggle off → on → check Profile screen → verify backend received update via Network log.

**Step 4: Commit**

```bash
git add SmartCompareApp/src/screens/ProfileScreen.tsx \
        SmartCompareApp/src/services/api.ts \
        SmartCompareApp/src/i18n/
git commit -- SmartCompareApp/src/screens/ProfileScreen.tsx \
              SmartCompareApp/src/services/api.ts \
              SmartCompareApp/src/i18n/ \
  -m "feat(privacy): AI sharing toggle in Profile screen

PDPL opt-out per design Section 6.1. Default ON. Bilingual copy.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Phase 2 — Referrer Flow (P2)

### Task B2.1 — POST /api/v1/referrals/share endpoint

**Owner:** `backend-referral`
**Phase:** P2
**Depends on:** B1.1, B1.2
**Files:**
- Create: `app/api/referral_routes.py`
- Modify: `app/main.py` (register router)
- Modify: `app/services/referral_service.py` (add `create_invite`)
- Test: `tests/test_referral_service.py` (extend)

**Step 1: Write failing test**

```python
# tests/test_referral_service.py (extension)
class TestCreateInvite:
    @pytest.mark.live_db
    async def test_create_invite_returns_record_with_share_token_and_link(self, authed_client, sample_comparison):
        r = authed_client.post("/api/v1/referrals/share", json={
            "comparison_id": sample_comparison["id"],
            "share_target": "whatsapp",
            "device_fingerprint_hash": "abc123",
        })
        assert r.status_code == 201
        body = r.json()
        assert body["success"] is True
        assert "invite_id" in body
        assert "share_link" in body
        assert "ref=" in body["share_link"]
        assert "QR-" in body["share_link"]

    @pytest.mark.live_db
    async def test_create_invite_grants_loop1_credit(self, authed_client, sample_comparison, db_admin):
        r = authed_client.post("/api/v1/referrals/share", json={
            "comparison_id": sample_comparison["id"],
            "share_target": "whatsapp",
        })
        user_id = r.json()["referrer_user_id"]
        credits = db_admin.table("deep_review_credits").select("*") \
            .eq("user_id", user_id).eq("source", "share_loop1") \
            .execute().data
        assert len(credits) >= 1

    @pytest.mark.live_db
    async def test_create_invite_enforces_3_per_week_cap(self, authed_client, sample_comparison):
        for _ in range(3):
            r = authed_client.post("/api/v1/referrals/share", json={
                "comparison_id": sample_comparison["id"],
                "share_target": "whatsapp",
            })
            assert r.status_code == 201
        r4 = authed_client.post("/api/v1/referrals/share", json={
            "comparison_id": sample_comparison["id"],
            "share_target": "whatsapp",
        })
        assert r4.status_code == 429
        assert r4.json()["code"] == "WEEKLY_INVITE_CAP"
```

**Step 2: Run test to verify failure**

Run: `python -m pytest tests/test_referral_service.py::TestCreateInvite -v -m live_db`
Expected: FAIL — endpoint doesn't exist (404).

**Step 3: Implement**

```python
# app/api/referral_routes.py
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Optional
from app.services.referral_service import ReferralService
from app.utils.auth_deps import get_current_user
from app.middleware.rate_limiter import limiter

router = APIRouter(prefix="/api/v1/referrals", tags=["referrals"])

class ShareRequest(BaseModel):
    comparison_id: str
    share_target: str  # 'whatsapp' | 'copy' | 'x' | 'telegram' | 'snapchat' | 'other'
    device_fingerprint_hash: Optional[str] = None

@router.post("/share", status_code=201)
@limiter.limit("10/minute")
async def share_comparison(request: Request, body: ShareRequest, user=Depends(get_current_user)):
    service = ReferralService(access_token=user.access_token)
    try:
        result = await service.create_invite(
            referrer_user_id=user.id,
            comparison_id=body.comparison_id,
            share_target=body.share_target,
            device_fingerprint_hash=body.device_fingerprint_hash,
        )
        return {"success": True, **result}
    except WeeklyInviteCapExceeded:
        raise HTTPException(status_code=429, detail={"code": "WEEKLY_INVITE_CAP", "error": "3-per-week cap reached"})
```

Extend `referral_service.py`:
```python
class WeeklyInviteCapExceeded(Exception): pass

class ReferralService:
    # ... existing ...

    async def create_invite(self, referrer_user_id, comparison_id, share_target, device_fingerprint_hash=None):
        # 1. Check weekly cap
        from datetime import datetime, timedelta
        seven_days_ago = (datetime.utcnow() - timedelta(days=7)).isoformat()
        recent = self.client.table("referral_invites").select("id", count="exact") \
            .eq("referrer_user_id", referrer_user_id) \
            .gte("created_at", seven_days_ago).execute()
        if recent.count >= 3:
            raise WeeklyInviteCapExceeded()

        # 2. Ensure code
        code = await self.ensure_code_for_user(referrer_user_id)

        # 3. Verify comparison ownership
        comp = self.client.table("comparisons").select("id, user_id, share_token") \
            .eq("id", comparison_id).single().execute()
        if not comp.data or comp.data["user_id"] != referrer_user_id:
            raise ValueError("Comparison not owned by user")
        share_token = comp.data["share_token"]

        # 4. Insert invite
        invite = self.client.table("referral_invites").insert({
            "referrer_user_id": referrer_user_id,
            "comparison_id": comparison_id,
            "share_target": share_target,
            "device_fingerprint_hash": device_fingerprint_hash,
        }).execute()

        # 5. Loop 1: grant Deep Review credit
        self.client.table("deep_review_credits").insert({
            "user_id": referrer_user_id,
            "source": "share_loop1",
        }).execute()

        # 6. Build share link
        from app.config import APP_BASE_URL
        share_link = f"{APP_BASE_URL}/c/{share_token}?ref={code}"

        return {
            "invite_id": invite.data[0]["id"],
            "referrer_user_id": referrer_user_id,
            "share_link": share_link,
            "weekly_invites_used": recent.count + 1,
            "weekly_invites_remaining": 2 - recent.count,
        }
```

In `app/main.py` add:
```python
from app.api import referral_routes
app.include_router(referral_routes.router)
```

**Step 4: Run test to verify pass**

Run: `python -m pytest tests/test_referral_service.py::TestCreateInvite -v -m live_db`
Expected: 3 PASSED.

**Step 5: Commit**

```bash
git add app/api/referral_routes.py app/services/referral_service.py app/main.py tests/test_referral_service.py
git commit -- app/api/referral_routes.py app/services/referral_service.py app/main.py tests/test_referral_service.py \
  -m "feat(referral): POST /api/v1/referrals/share endpoint

Loop 1 trigger fires immediately (Deep Review credit granted). Weekly cap
of 3 invites enforced. Returns share_link with ?ref=QR-XXXXXX. Rate-limited
10/min.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task B2.2 — GET /api/v1/referrals/status endpoint

**Owner:** `backend-referral`
**Phase:** P2
**Depends on:** B2.1
**Files:**
- Modify: `app/api/referral_routes.py`
- Modify: `app/services/referral_service.py`
- Test: `tests/test_referral_service.py` (extend)

**Test acceptance:**
- Returns `{ weekly_invites_used, weekly_invites_remaining, monthly_bonus_comparisons, deep_review_credits_available, total_lifetime_redemptions, referral_code }`.
- Returns valid code even for first-time user (lazy-creates).
- Counts only NON-expired credits (where `consumed_at IS NULL AND expires_at > now()`).

**Pattern:** same TDD steps as B2.1. Test first → implement → commit.

**Commit message:** `feat(referral): GET /api/v1/referrals/status — weekly cap + bonus + credits state`

---

### Task F2.3 — ShareBottomSheet component

**Owner:** `frontend-referral`
**Phase:** P2
**Depends on:** B2.1
**Files:**
- Create: `SmartCompareApp/src/components/ShareBottomSheet.tsx`
- Create: `SmartCompareApp/src/services/referralService.ts`
- Modify: `SmartCompareApp/src/i18n/en/referrals.ts`, `ar/referrals.ts` (new files)

**Component requirements (per design 3.2-3.3):**
- Bottom-sheet UI (use existing react-native modal pattern — see `OnboardingScreen` or similar).
- Privacy toggles: name (default ON), result (default ON), reasons (default ON), budget (locked OFF, displayed as disabled).
- Pre-filled message rendering (auto-localized via i18n + product names interpolated).
- 5 share targets as buttons: WhatsApp / Copy / X / Telegram / Snapchat.
- On any target tap: call `referralService.createShare({comparison_id, share_target, device_fingerprint_hash})` → use returned `share_link` with the platform's share intent.
- After share: show Loop 1 toast (separate task F2.5) and dismiss sheet.

**Test (Jest/RN):**
- Renders 5 share targets.
- "Show my budget" toggle is disabled by default and cannot be toggled on.
- Tapping a target invokes `Linking.openURL` with the appropriate scheme.

**Pattern:** TDD with React Native testing library. Mock `Linking` and `referralService.createShare`.

**Commit message:** `feat(referral): ShareBottomSheet component with privacy toggles`

---

### Task F2.4 — Result-aware share CTA on ResultsScreen

**Owner:** `frontend-referral`
**Phase:** P2
**Depends on:** F2.3
**Files:**
- Modify: `SmartCompareApp/src/screens/ResultsScreen.tsx`
- Modify: `SmartCompareApp/src/i18n/{en,ar}/referrals.ts`

**Logic (per design 3.1):**
- After `comparison` loads, compute CTA variant:
  - `strong` if `confidence_score >= 0.75 && winner_margin >= 0.15`
  - `close` if `winner_margin < 0.08`
  - `saved` if user previously tapped Save on this comparison (check from history state)
  - else `default`
- Render emerald-accent share button below the verdict, with the variant's copy.
- On tap: open ShareBottomSheet with `comparison_id`.

**Test:**
- All 4 CTA variants render correct copy in EN.
- All 4 CTA variants render correct copy in AR with RTL alignment.

**Commit message:** `feat(referral): result-aware share CTA on ResultsScreen (PDF #14)`

---

### Task F2.5 — Loop 1 toast + weekly counter

**Owner:** `frontend-referral`
**Phase:** P2
**Depends on:** F2.3, B2.2
**Files:**
- Modify: `SmartCompareApp/src/components/ShareBottomSheet.tsx` (add toast)
- Modify: `SmartCompareApp/src/screens/ProfileScreen.tsx` (referral status card)
- Create: `SmartCompareApp/src/components/ReferralStatusCard.tsx`

**Logic:**
- After successful share API call, show toast: "🎁 Your next comparison goes 2× deeper on reviews. 2 of 3 gifts this week."
- ReferralStatusCard in Profile reads from `GET /referrals/status` and shows: code, weekly used/remaining, lifetime redemptions, available Deep Review credits.

**Commit message:** `feat(referral): Loop 1 toast + ReferralStatusCard in Profile`

---

### Task T2.6 — Test track for Phase 2

**Owner:** `test-referral`
**Phase:** P2 (parallel with B/F tasks)
**Depends on:** B2.1
**Files:**
- Modify: `tests/test_referral_service.py` (additional edge cases)
- Create: `tests/test_referral_routes.py` (HTTP-level tests)

**Coverage targets for P2:**
- Weekly cap: 3 invites pass, 4th rejected
- Comparison-ownership check: user A cannot create invite from user B's comparison
- Disposable share-target rejected (e.g., `share_target: "facebook"` not in CHECK constraint)
- Concurrent invite creation: race condition does not allow 4 parallel inserts to bypass cap
- Loop 1 credit grant: exactly 1 credit per share, source='share_loop1'

**Coverage gate: 80%+ on `app/services/referral_service.py` and `app/api/referral_routes.py` after P2.**

**Commit message:** `test(referral): edge cases for weekly cap, ownership, race conditions`

---

## Phase 3 — Invitee Flow (P3)

### Task B3.1 — GET /api/v1/referrals/invite/{token} endpoint

**Owner:** `backend-referral`
**Phase:** P3
**Depends on:** B2.1
**Files:**
- Modify: `app/api/referral_routes.py`
- Modify: `app/services/referral_service.py`
- Test: `tests/test_referral_routes.py`

**Endpoint behavior:**
- Path: `/api/v1/referrals/invite/{share_token}?ref={referral_code}` (auth-OPTIONAL)
- Resolve `share_token` → comparison; resolve `ref` → referrer (via `resolve_referral_code` RPC)
- Return:
  ```json
  {
    "referrer_display_name": "Ahmed",
    "comparison": { /* sanitized: products, winner, NOT preferences/budget */ },
    "cohort_match": null | { match_quality, language, governorate },
    "invite_id": "uuid"  // creates a new invite-view record on first call
  }
  ```
- Set `referral_invites.first_viewed_at = now()` on first resolution per device.
- Strip personalization from comparison (reuse existing `share_routes.py` logic).

**Test:**
- Anon user can resolve a valid token+ref; returns referrer display name.
- Invalid ref → 404.
- Comparison personalization (preferences, budget) NOT in response.

**Commit message:** `feat(referral): GET /referrals/invite/{token} — invitee landing resolution`

---

### Task F3.2 — ReferralLandingScreen (web + deep link)

**Owner:** `frontend-referral`
**Phase:** P3
**Depends on:** B3.1
**Files:**
- Create: `SmartCompareApp/src/screens/ReferralLandingScreen.tsx`
- Modify: `SmartCompareApp/App.tsx` (deep link handler)
- Modify: `SmartCompareApp/src/i18n/{en,ar}/referrals.ts`

**Component requirements (per design 3.5):**
- Renders curiosity copy: "Ahmed was torn between [A] and [B] — picked [B]. Your answer doesn't have to be his. Answer 4 questions, get yours."
- Shows the comparison preview (products + winner) but NOT referrer's preferences.
- Single CTA: **Start my comparison** → navigates to `InviteeQuizScreen`.
- NO signup gate (PDF #6).

**Deep link handler in App.tsx:**
- Listen for URLs matching `/c/{token}?ref={code}` → push to `ReferralLandingScreen` with params.
- Web fallback for users without app: render same screen as React web component (Expo Router or static HTML if simpler).

**Commit message:** `feat(referral): ReferralLandingScreen + deep link handler`

---

### Task F3.3 — InviteeQuizScreen (4 questions, reuses onboarding)

**Owner:** `frontend-referral`
**Phase:** P3
**Depends on:** F3.2
**Files:**
- Create: `SmartCompareApp/src/screens/InviteeQuizScreen.tsx`

**Component requirements (per design 3.6):**
- 4 questions (one per screen for PDF #6 gradual commitment):
  1. Priority — single-select from 8 dimensions (extend with cohort options if `cohort_match.match_quality !== null`)
  2. Budget tier — single-select (budget / mid / premium)
  3. Brand attitude — single-select (`trust_known_brands` / `open_to_emerging` / `value_first`)
  4. Non-negotiable — free text or category-specific preset list
- Progress indicator (1/4, 2/4...).
- After Q4: POST quiz answers + comparison_id → backend re-runs scoring with these prefs (no LLM call needed if comparison cached) → return personalized result.
- Render personalized result: WHO matches, dimension winners, optional "differs from referrer's pick" callout.

**Backend support (small):** `POST /api/v1/referrals/invite/{token}/quiz` accepts the 4 answers, returns the personalized comparison view. Reuses scoring_service deterministic re-scoring (zero LLM cost).

**Commit message:** `feat(referral): InviteeQuizScreen — 4Q quiz with personalized result`

---

### Task B3.4 — POST /referrals/invite/{token}/quiz endpoint

**Owner:** `backend-referral`
**Phase:** P3
**Depends on:** B3.1
**Files:**
- Modify: `app/api/referral_routes.py`
- Modify: `app/services/scoring_service.py` (add `rescore_with_overrides` if not present)

**Behavior:**
- Auth-optional (anon invitees pre-signup).
- Accepts `{priority, budget, brand_attitude, non_negotiable}`.
- Looks up cached comparison; re-runs scoring with these as overrides.
- Returns same shape as `/api/v1/text/compare` response, but with `personalization.scoring_method = "invitee_quiz"`.

**Test:**
- Anon user can submit quiz, gets personalized result.
- Quiz answers don't persist (no PII storage pre-signup).

**Commit message:** `feat(referral): POST /referrals/invite/{token}/quiz — anon personalized rescoring`

---

### Task F3.5 — Soft signup CTA + redemption tracking

**Owner:** `frontend-referral`
**Phase:** P3
**Depends on:** F3.3
**Files:**
- Modify: `SmartCompareApp/src/screens/InviteeQuizScreen.tsx` (post-result CTA)
- Modify: `SmartCompareApp/src/screens/RegisterScreen.tsx` (capture invite_id during signup)
- Modify: `SmartCompareApp/src/services/authService.ts` (pass invite_id on registration)

**Logic:**
- After quiz result renders, show CTA: *"This is your result. Save it and get a free Deep Review credit since you came from a friend."*
- Tap → RegisterScreen with `invite_id` param (carried via React Navigation).
- On successful signup → backend links `referral_invites.redeemed_by_user_id = new_user_id` (NOT the Loop 2 fire yet — that happens on first comparison).
- After signup → user lands in HomeScreen, recent comparison is in history.

**Backend:** extend `auth_routes.py::POST /register` to accept optional `invite_id`; if present, update the invite row.

**Commit message:** `feat(referral): soft signup CTA + invite_id captured on registration`

---

### Task T3.6 — Test track for P3

**Owner:** `test-referral`
**Phase:** P3 (parallel)
**Files:**
- Extend: `tests/test_referral_routes.py`
- Create: `tests/test_invitee_quiz.py`

**Coverage targets:**
- Anon resolution of valid invite token.
- Personalization stripped from invitee view (no `preferences`, no `budget`).
- Quiz endpoint: no PII stored pre-signup.
- Signup with `invite_id` correctly links the row.
- 80%+ coverage on new endpoints.

**Commit message:** `test(referral): invitee flow coverage`

---

## Phase 4 — Loop 2 + Anti-Abuse (P4)

### Task B4.1 — AbuseDetectionService

**Owner:** `backend-referral`
**Phase:** P4
**Depends on:** B1.1
**Files:**
- Create: `app/services/abuse_detection_service.py`
- Create: `app/utils/disposable_email_blocklist.py` (or pull from PyPI: `disposable-email-domains` package)
- Test: `tests/test_abuse_detection.py`

**Class API:**
```python
class AbuseDetectionService:
    def is_same_device(self, referrer_id: str, invitee_device_hash: str) -> bool: ...
    def is_disposable_email(self, email: str) -> bool: ...
    def passes_real_action_gate(self, comparison_id: str) -> bool: ...
    def evaluate_invite(self, invite: dict, invitee: dict) -> AbuseEvaluation:
        """Returns {passed: bool, flagged_reason: str|None}"""
```

**Test cases:**
- Same device hash on referrer and invitee → flagged `SAME_DEVICE`
- Email from `mailinator.com` → flagged `DISPOSABLE_EMAIL`
- Comparison with `(result_viewed_at - started_at) < 30s` → flagged `BELOW_REAL_ACTION_THRESHOLD`
- All checks pass → `passed: True, flagged_reason: None`

**Commit message:** `feat(referral): AbuseDetectionService (device+email+real-action gates)`

---

### Task B4.2 — Loop 2 trigger in comparison post-hook

**Owner:** `backend-referral`
**Phase:** P4
**Depends on:** B4.1, B3.5
**Files:**
- Modify: `app/services/structured_comparison_service.py` (post-comparison hook)
- Modify: `app/services/referral_service.py` (add `try_trigger_loop2`)
- Test: `tests/test_referral_loop2.py`

**Behavior:**
- After every signed-in user's comparison completes, check:
  - Is this the user's first comparison after signup? (count comparisons by user_id; if exactly 1)
  - Is there an unredeemed `referral_invites` row with `redeemed_by_user_id = this_user`?
- If yes → run AbuseDetectionService.evaluate_invite. If passes:
  - Insert `referral_redemptions` row
  - Increment referrer's `referral_bonus_comparisons_this_month` by 5 (or 10 if Premium)
  - Insert `deep_review_credits` for invitee (`source='invitee_signup'`)
  - Update invite: `redeemed_at = now()`, `invitee_first_comparison_id = comparison_id`
  - Send push to referrer (B4.4)
- If fails → update invite `flagged_reason`; audit log `referral_*` event.

**Test:**
- Happy path: invitee → first real comparison → referrer gets +5
- Same-device fraud: referrer's device == invitee's device → no Loop 2 fire, audit log entry
- Sub-30s comparison: no Loop 2 fire
- Disposable email: no Loop 2 fire
- Race: invitee runs 2 comparisons rapidly — only first triggers Loop 2

**Commit message:** `feat(referral): Loop 2 trigger with anti-abuse evaluation`

---

### Task B4.3 — Bonus comparison crediting in usage_service

**Owner:** `backend-referral`
**Phase:** P4
**Depends on:** B1.1
**Files:**
- Modify: `app/services/usage_service.py`
- Modify: `tests/test_usage_service.py`

**Change `check_usage_allowed()`:**
- Read `users.referral_bonus_comparisons_this_month`, `referral_bonus_reset_at`.
- If `reset_at < now()`: reset counter to 0, set new reset_at.
- Effective monthly cap = base_cap (10 Free / 70 Premium) + bonus.
- Daily cap unchanged.

**Test:**
- Free user with 0 bonus: cap = 10/month
- Free user with 15 bonus: cap = 25/month
- Premium user with 30 bonus: cap = 100/month
- Lazy reset: month rolls over → counter = 0

**Commit message:** `feat(referral): bonus comparisons extend monthly cap in usage_service`

---

### Task B4.4 — Push to referrer on Loop 2 fire

**Owner:** `backend-referral`
**Phase:** P4
**Depends on:** B4.2
**Files:**
- Modify: `app/services/referral_service.py`
- Create: `app/services/push_service.py` (if not exists; wraps Expo Push API)
- Test: `tests/test_push_service.py`

**Push payload (per design 3.8):**
- Title: localized (EN/AR per referrer's preference)
- Body: localized invitee name + +5 (or +10) comparisons
- Deep link: `qaren://profile/referrals` (opens ReferralStatusCard in Profile)

**Test:**
- Mock Expo Push API; verify correct payload + recipient token.
- AR localization for AR-preferring referrer.

**Commit message:** `feat(referral): push notification on Loop 2 fire`

---

### Task F4.5 — Frontend: weekly counter + bonus display

**Owner:** `frontend-referral`
**Phase:** P4
**Depends on:** B2.2 (status endpoint)
**Files:**
- Modify: `SmartCompareApp/src/components/ReferralStatusCard.tsx`

**Display:**
- "3 of 3 gifts this week" (refreshed via pull-to-refresh)
- "Bonus this month: 5 of 15 used"
- "Lifetime: 12 friends helped"
- Code with copy-to-clipboard
- Premium upsell line if Free: "Premium gets +10 per invite (vs +5)"

**Commit message:** `feat(referral): ReferralStatusCard expanded with weekly + bonus + lifetime`

---

## Phase 5 — Re-Engagement Push System (P5)

### Task B5.1 — Daily cron infrastructure

**Owner:** `backend-referral`
**Phase:** P5 (parallel with P3-P4)
**Depends on:** B1.1
**Files:**
- Create: `scripts/cron_reengagement.py` (entry point)
- Modify: `railway.json` or equivalent (schedule: daily 0300 UTC = 0600 GCC)
- Test: `tests/test_cron_reengagement.py`

**Behavior:**
- Iterate users where `notifications_enabled` AND `last_comparison_at >= now() - interval '60 days'`.
- For each user, call `ReengagementService.evaluate(user)`.
- Cap to 1000 users per cron run; cursor-paginate.

**Commit message:** `feat(reengagement): daily cron entrypoint`

---

### Task B5.2 — ReengagementService selector + 3 detectors

**Owner:** `backend-referral`
**Phase:** P5
**Depends on:** B5.1
**Files:**
- Create: `app/services/reengagement_service.py`
- Test: `tests/test_reengagement_service.py`

**Class API:**
```python
class ReengagementService:
    async def evaluate(self, user: dict) -> Optional[PushPayload]:
        if self._recent_push(user, days=7):
            return None
        return (
            await self._check_decision_insight(user)
            or await self._check_cohort_curiosity(user)
            or await self._check_decision_retrospective(user)
        )

    async def _check_decision_insight(self, user) -> Optional[PushPayload]: ...
    async def _check_cohort_curiosity(self, user) -> Optional[PushPayload]: ...
    async def _check_decision_retrospective(self, user) -> Optional[PushPayload]: ...
```

**Detector logic (per design 3.9):**

`_check_decision_insight`:
- For each saved product in user's history (top-3 most recent), call cached review fetch + sentiment compute.
- Compare to last sentiment snapshot (stored in `re_engagement_events.content_payload` of prior insight push, if any).
- If shifted ≥10% → return PushPayload.
- COST GUARD: only check products in top-100 most-saved globally (precomputed daily query).

`_check_cohort_curiosity`:
- Query: in user's governorate, ≥5 users ran same comparison in last 7d, ≥40% picked differently than user.
- Reuses Session 41 cohort tables.

`_check_decision_retrospective`:
- Find user's comparisons created exactly 14d ago (±1d window) with no prior retrospective sent.

**Test (mocked Supabase + Redis):**
- Selector picks insight first when both insight and curiosity are eligible.
- Selector returns None when no detector fires.
- 7-day cap honored.

**Commit message:** `feat(reengagement): selector + 3 detectors`

---

### Task B5.3 — Push dispatcher + delivery tracking

**Owner:** `backend-referral`
**Phase:** P5
**Depends on:** B5.2, B4.4
**Files:**
- Modify: `app/services/reengagement_service.py`
- Modify: `app/services/push_service.py` (extend for re-engagement payloads)

**Behavior:**
- For each PushPayload returned by `evaluate`:
  - Insert `re_engagement_events` row (status=triggered)
  - Send via Expo Push
  - Update row with `delivered_at`
- Frontend handler updates `opened_at` when user taps the push (deep link captures event_id).

**Commit message:** `feat(reengagement): push dispatcher + delivery/open tracking`

---

### Task F5.4 — Notification settings UI + deep link handlers

**Owner:** `frontend-referral`
**Phase:** P5
**Depends on:** B5.3
**Files:**
- Modify: `SmartCompareApp/src/screens/ProfileScreen.tsx` (Notifications section)
- Modify: `SmartCompareApp/App.tsx` (deep link handlers for 3 push types)
- Modify: `SmartCompareApp/src/i18n/{en,ar}/notifications.ts`

**UI:**
- Master toggle: "Smart Decision Notifications" (default ON).
- Sub-toggles (only visible if master ON):
  - Decision Insights
  - Cohort Updates
  - Decision Retrospectives
- All persist via `PUT /api/v1/auth/preferences` `{notifications: {...}}`.

**Deep links:**
- Decision Insight → ResultsScreen for the comparison_id with banner "New reviews — re-checked"
- Cohort Curiosity → ResultsScreen with "Cohort divergence" overlay
- Decision Retrospective → modal asking "Did you buy [Product]? How's it going?" → if "yes/great" → option to share decision (re-enter referral loop)

**Commit message:** `feat(reengagement): notification settings + deep link handlers`

---

### Task T5.5 — Test track for P5

**Owner:** `test-referral`
**Phase:** P5
**Files:**
- Create: `tests/test_reengagement_service.py` (full coverage)
- Create: `tests/test_cron_reengagement.py`

**Coverage targets:**
- All 3 detectors (happy + non-fire paths)
- Selector logic (priority order)
- 7-day cap honored
- Pagination cursor in cron
- Top-100 cost guard for decision_insight

**Commit message:** `test(reengagement): full coverage P5`

---

## Phase 6 — Admin Dashboards (P6)

### Task B6.1 — Admin endpoints for referral metrics

**Owner:** `backend-referral`
**Phase:** P6
**Depends on:** B2.x, B4.x
**Files:**
- Modify: `app/api/admin_routes.py`

**Endpoints (X-Admin-Key auth, rate-limited 30/min):**
- `GET /api/v1/admin/referrals/metrics` — invites, redemptions, conversion rate, active referrers (this week, this month, lifetime)
- `GET /api/v1/admin/referrals/viral` — K-coefficient over 12-week trailing window
- `GET /api/v1/admin/referrals/cohort_uplift` — referred-vs-organic retention/comparisons/Premium-conversion
- `GET /api/v1/admin/referrals/abuse` — flagged invites by reason

**Commit message:** `feat(admin): referrals metrics endpoints`

---

### Task B6.2 — Admin endpoints for cost dashboard

**Owner:** `backend-referral`
**Phase:** P6
**Depends on:** —
**Files:**
- Modify: `app/api/admin_routes.py`
- Create: `app/services/cost_dashboard_service.py`

**Endpoints:**
- `GET /api/v1/admin/costs/subscriptions` — list of recurring subs with cost
- `GET /api/v1/admin/costs/api` — current month spend per API (live OpenAI Usage API where possible, Redis counters for Serper/Firecrawl/Scrapedo)
- `GET /api/v1/admin/costs/function_map` — static service-to-function map
- `GET /api/v1/admin/costs/gauges` — current cap utilization (4o tokens, mini tokens, Firecrawl lifetime, Scrapedo monthly)

**Commit message:** `feat(admin): cost dashboard endpoints`

---

### Task F6.3 — /admin/referrals.html dashboard

**Owner:** `frontend-referral`
**Phase:** P6
**Depends on:** B6.1
**Files:**
- Create: `app/static/admin/referrals.html`
- Modify: `app/middleware/security.py` (extend CSP allowlist for new admin page; per Session 41 CSP scoping pattern)

**Mirrors `/admin/cohort.html`** (Chart.js v4.4.1 with SRI hash, X-Admin-Key prompt, light theme).

**Sections:**
- Conversion funnel (sent → viewed → redeemed)
- 12-week K-coefficient trendline
- Cohort uplift bar chart (referred vs organic)
- Abuse log table

**Commit message:** `feat(admin): /admin/referrals.html dashboard`

---

### Task F6.4 — /admin/costs.html dashboard

**Owner:** `frontend-referral`
**Phase:** P6
**Depends on:** B6.2
**Files:**
- Create: `app/static/admin/costs.html`
- Modify: `app/middleware/security.py` (CSP)

**Panels (per design 5.5):**
- A. Monthly Subscriptions table
- B. API Costs This Month (Chart.js daily burn-rate line)
- C. Service Function Map table
- D. Cap Utilization Gauges

**Commit message:** `feat(admin): /admin/costs.html dashboard`

---

## Phase 7 — Cross-Cutting: Hybrid Model Routing

This phase ships **independently** of the referral system from day 1. Can be built parallel to P1-P3 by `backend-referral` between dependencies.

### Task BX.1 — ModelRouterService

**Owner:** `backend-referral`
**Phase:** P-cross
**Depends on:** —
**Files:**
- Create: `app/services/model_router_service.py`
- Test: `tests/test_model_router.py`

**Class API:**
```python
class ModelRouterService:
    """Selects gpt-4o vs gpt-4o-mini based on daily token usage."""

    DAILY_4O_CAP = 1_000_000  # tokens; verify exact value at deploy
    SWITCH_THRESHOLD = 0.80   # switch verdict to mini at 80% of cap

    async def get_model(self, priority: str = "standard") -> str:
        """priority: 'high' (verdict) | 'standard' (everything else)"""
        if priority == "standard":
            return "gpt-4o-mini"
        # priority == 'high' — check 4o cap
        used_today = await self._get_4o_usage_today()
        if used_today / self.DAILY_4O_CAP >= self.SWITCH_THRESHOLD:
            return "gpt-4o-mini"
        return "gpt-4o"

    async def record_usage(self, model: str, tokens_used: int):
        """Atomic Redis increment of daily counter."""
        if model == "gpt-4o":
            await self._increment_4o_usage(tokens_used)
```

**Atomic Redis counter:**
- Key: `openai:4o:tokens:{YYYY-MM-DD}` (UTC)
- TTL: 36 hours (so reset is automatic)
- Use `INCRBY` (atomic) per `api_budget_service.py` pattern.

**Test:**
- `get_model('standard')` always returns mini.
- `get_model('high')` returns 4o below threshold, mini at/above.
- `record_usage` atomically increments.
- Race: 2 concurrent calls at 99% of cap don't both succeed on 4o.

**Commit message:** `feat(model_router): hybrid per-call routing service`

---

### Task BX.2 — Integrate ModelRouter into structured_comparison_service

**Owner:** `backend-referral`
**Phase:** P-cross
**Depends on:** BX.1
**Files:**
- Modify: `app/services/structured_comparison_service.py`
- Modify: `app/services/extraction_service.py` (verdict generation accepts model param)

**Integration:**
- All non-verdict LLM calls hardcode `model="gpt-4o-mini"`.
- Verdict generation calls `model_router.get_model(priority="high")`.
- After each call, call `model_router.record_usage(model_used, response.usage.total_tokens)`.
- On 429 from gpt-4o (cap exceeded mid-call), retry with mini and audit-log.

**Test (live unit, $0.03 budget):**
- At low daily volume, verdict uses gpt-4o.
- After simulated cap, verdict falls back to mini.
- 429 retry path works.

**Commit message:** `feat(model_router): hybrid routing integrated into comparison flow`

---

## Phase 8 — QA + Rollout (P7)

### Task Q8.1 — End-to-end smoke tests (real flows)

**Owner:** `qa-referral`
**Phase:** P7
**Depends on:** ALL above
**Files:**
- Create: `tests/test_referral_e2e.py`

**Smoke scenarios:**
1. User A shares comparison → invite created, Loop 1 credit granted, share link contains `?ref=`
2. Anon user opens invite link → quiz → personal result → no auth required to this point
3. Anon user signs up → invite redeemed_by linked
4. Invitee runs first real comparison >30s → Loop 2 fires: redemption row, +5 to A, push to A
5. Invitee uses Deep Review credit on next comparison → review section has 8-10 snippets
6. Re-engagement cron in dry-run mode generates expected push payloads for test users
7. Admin dashboards load with real data

**Run on staging environment first; production canary after.**

**Commit message:** `test(referral): E2E smoke scenarios`

---

### Task Q8.2 — Security regression extension

**Owner:** `test-referral` (with qa-referral cross-review)
**Phase:** P7
**Depends on:** ALL
**Files:**
- Modify: `tests/test_security_regression.py`

**New cases (additive — do NOT break existing 57):**
- Anonymous user cannot list other users' invites
- Invitee cannot read referrer's preferences from invite resolution
- Disposable email signup is logged but not rewarded
- Same-device referral is logged but not rewarded
- Admin endpoints reject without X-Admin-Key
- RLS prevents user A from reading user B's referral_invites
- Quiz endpoint stores no PII pre-signup

**Final test count target: ≥75 (from current 57).**

**Commit message:** `test(security): referral regression cases (extends 57 → 75+)`

---

### Task Q8.3 — Production canary rollout

**Owner:** `qa-referral`
**Phase:** P7
**Depends on:** Q8.1, Q8.2 GREEN
**Files:**
- Modify: Railway env vars (manual via dashboard or CLI)

**Steps:**
1. Set `ENABLE_HYBRID_MODEL_ROUTING=true` in Railway (no user-facing change). Monitor for 24h: cap utilization, 429 rate, comparison quality regression.
2. Set `ENABLE_REFERRAL_SYSTEM=true` for 5% of users (use existing user_id-hash gate per cohort flag pattern, OR all-or-nothing if no per-user gate is ready).
3. Monitor 48h: invite insert rate, Loop 1 toast frequency, abuse-flag rate, no errors.
4. Flip to 100%.
5. After 1 week stable: set `ENABLE_REENGAGEMENT_PUSHES=true`. Monitor push CTR and unsubscribe rate.

**Acceptance criteria checklist:** all 10 from design Section 14.

**Commit message:** `chore(rollout): canary 5% → 100% → reengagement enabled`

---

### Task Q8.4 — Update CLAUDE.md, MEMORY.md, CONTEXT_SESSION_LOG.md

**Owner:** `qa-referral`
**Phase:** P7
**Depends on:** All shipped
**Files:**
- Modify: `CLAUDE.md` (add referral system section)
- Modify: `MEMORY.md` (Session 42 entry with gotchas)
- Modify: `docs/CONTEXT_SESSION_LOG.md` (full session record)

**CLAUDE.md target ≤300 lines** (currently ~285). Be surgical.

**MEMORY.md entry:** session learnings, especially anything surprising (model routing edge cases, push delivery, abuse-detection accuracy).

**Commit message:** `docs: Session 42 — Smart Referral System LIVE`

---

## Disband Criteria

The team disbands ONLY when ALL of the following are TRUE:

- [ ] Migration 014 applied via Supabase MCP, schema verified
- [ ] All 7 phases shipped, feature-flags ON in Railway
- [ ] `python -m pytest tests/ -v -m "not (live_unit or live_db or integration)"` passes (all unit tests)
- [ ] `python -m pytest tests/test_security_regression.py -v` passes (75+ tests)
- [ ] Coverage ≥80% on new files (verify with `pytest --cov=app/services/referral_service --cov=app/services/abuse_detection_service --cov=app/services/reengagement_service --cov=app/services/model_router_service`)
- [ ] E2E smoke (Q8.1) passes on staging
- [ ] Production canary 48h stable, 0 abuse-flag false-positives in spot check
- [ ] Admin dashboards (`/admin/referrals.html`, `/admin/costs.html`) render with real data
- [ ] CLAUDE.md/MEMORY.md updated
- [ ] Mutual QA sign-off from all 4 agents — each has reviewed at least one other agent's work

When all checked: `qa-referral` posts the disband message in TeamChat.

---

## Post-Disband: v1.1 Backlog (NOT in scope, do not start)

- Vanity referral codes (Premium-gated)
- Soft phone verification (if abuse data shows need)
- A/B testing share copy
- Graph-cycle detection for collusion
- Continuous in-app survey collection (re-feed cohort priors)
