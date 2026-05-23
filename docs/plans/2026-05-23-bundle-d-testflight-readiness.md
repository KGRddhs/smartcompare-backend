# Bundle D — TestFlight Readiness Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: This plan is executed by a 5-Opus `TeamCreate` (not a solo subagent). Dispatcher seeds the team in Phase 0; team agents read their lane anchor docs and execute their assigned tasks below. For execution discipline use `superpowers:executing-plans` mental model, but cross-agent coordination uses CLAUDE.md OP #4 (TeamCreate) and OP #8 (stall escalation).

**Goal:** Ship Qaren mobile app to Apple TestFlight (internal, ≤100 testers) with every reproducible Expo bug fixed, Bundle C v1.1 polish shipped, audit follow-up complete, ASC URLs hosted at `qaren.app`, PR #6 Bundle B simulator sign-off posted.

**Architecture:** Single mega-team (5 Opus agents: Backend, Frontend, Native/Ops, Test, QA) on branch `feature/bundle-d-testflight-readiness`. 4 phases (Setup → Foundation → Integration → TestFlight → Close-out). Defense-in-depth via 6 memory anchor docs + 8 leak-prevention control layers + 24-risk ledger. Cross-QA mandatory; send-back loop; 100%-complete-before-disassembly gate.

**Tech Stack:** FastAPI + Python 3.12 (backend) · React Native + Expo SDK + EAS Build (frontend) · Supabase Auth + Postgres + RLS · Apple Developer Portal + App Store Connect + TestFlight · Vercel/Netlify static hosting + Cloudflare DNS for `qaren.app` · Sentry RN + Sentry Python · Upstash Redis · Railway

**Reference design doc:** `docs/plans/2026-05-23-bundle-d-testflight-readiness-design.md` (commit `efee754`) — § 1-13. Read this BEFORE starting any task in this plan.

---

## Phase 0 — Dispatcher Setup (≈1hr, day 0)

### Task 0.1: Create worktree

**Owner:** Dispatcher

**Step 1:** Run
```bash
git -C /c/Users/SynAckITPC/Documents/ai/smartcompare worktree add -b feature/bundle-d-testflight-readiness ../smartcompare-bundle-d main
```

**Step 2:** Verify
```bash
git -C ../smartcompare-bundle-d branch --show-current
```
Expected: `feature/bundle-d-testflight-readiness`

**Step 3:** Confirm clean state
```bash
git -C ../smartcompare-bundle-d status
```
Expected: `nothing to commit, working tree clean`

---

### Task 0.2: Write 6 memory anchor docs

**Owner:** Dispatcher

**Files to create (in worktree):**
- `memory/BUNDLE_D_BACKEND_ANCHOR.md`
- `memory/BUNDLE_D_FRONTEND_ANCHOR.md`
- `memory/BUNDLE_D_NATIVE_OPS_ANCHOR.md`
- `memory/BUNDLE_D_TEST_ANCHOR.md`
- `memory/BUNDLE_D_QA_ANCHOR.md`
- `memory/BUNDLE_D_RISK_LEDGER.md`

**Template** (use for all 5 agent anchors; risk ledger has separate shape — see Task 0.3):

```markdown
---
name: Bundle D <Lane> Anchor
description: Per-lane scope + verification commands + risk subset for Bundle D team
type: project
---

# Lane: <Backend|Frontend|Native/Ops|Test|QA>

## My scope (N items)
1. [Task #X.Y from plan] — file:line + acceptance criterion + verification command
2. ...

## Memory facts I need (anti-hallucination)
- `verify_token` returns `{id, email, access_token}` per audit-r2 51385d3 — DO NOT log full `current_user` dict
- `/admin/*` CSP allows `'unsafe-inline'` + `cdn.jsdelivr.net`; rest of app strict
- `saved_comparisons.schema_version=2` filter excludes legacy v1 rows
- App name is "Qaren" (قارن). NEVER write "SmartCompare" to any user-facing string.
- Backend deploys via `git push origin main` → Railway ~90s. Frontend deploys via `eas update --branch preview`.
- Cohort match values are EXACT-CASE: `age_group: "25-34"`, `gender: "Male"/"Female"`.
- ENABLE_BUNDLE_C_SCORING=false in Railway today; do NOT assume the missing-signal swap is live.

## Pre-flight commands (run before starting)
- `git log --oneline -5` — confirm starting commit
- `git status` — confirm clean
- `<lane-specific health check>` — see anchor body

## Verification commands (run before "done")
- `<unit test cmd>`
- `<integration test cmd>`
- `<prod smoke cmd if applicable>`

## Risks I own (subset of R1-R24)
- See `BUNDLE_D_RISK_LEDGER.md` for full list. My subset:
- R<N>: <preventive control I run>

## Dependencies
- Blocked by: <other agent>:<task>
- Blocking: <other agent>:<task>

## Rollback recipe
- Revert: `git revert <commit>` → `git push origin main`
- DB: <migration_rollback_file.sql> if applicable
- Flag: <env var flip> if applicable
```

**Step 1:** Dispatcher fills each anchor with:
- Scope items from Plan § Phase 1-4 filtered to this lane
- Verification commands extracted from individual task steps
- Risks from the R1-R24 list filtered to this lane

**Step 2:** Commit all 6 anchors
```bash
cd ../smartcompare-bundle-d
git add memory/BUNDLE_D_*.md
git commit -m "docs(bundle-d): add 6 memory anchor docs for 5-Opus team"
```

---

### Task 0.3: Write BUNDLE_D_RISK_LEDGER.md

**Owner:** Dispatcher

**File:** `memory/BUNDLE_D_RISK_LEDGER.md`

**Structure** (one row per R1-R24 from design doc § 10):
```markdown
---
name: Bundle D Risk Ledger
description: Master R1-R24 list + preventive control + status tracker for Bundle D
type: project
---

# Risk ledger

| # | Risk | Preventive control | Owner | Status |
|---|---|---|---|---|
| R1 | <text> | <control> | Backend | PENDING |
| R2 | <text> | <control> | Backend | PENDING |
| ... | | | | |
| R24 | <text> | <control> | Native/Ops | PENDING |

## Status legend
- PENDING — not yet addressed
- ADDRESSED — control ran successfully (cite test cmd output or commit SHA)
- N/A — risk doesn't apply this bundle (cite reason)
- ACCEPTED — risk acknowledged + explicit Ahmed approval (cite PR comment URL)

## Bundle-merge gate
Dispatcher MUST verify: zero R# in PENDING before merging Bundle D PR.

## Update protocol
When an agent addresses a risk:
1. Edit this file: change PENDING → ADDRESSED in the agent's row
2. Add a citation in a new row below the table (commit SHA or test output excerpt)
3. Commit with message "risk(bundle-d): R<N> addressed by <agent> via <method>"
```

**Step 1:** Copy R1-R24 from design doc § 10 verbatim into the table.

**Step 2:** Commit
```bash
git add memory/BUNDLE_D_RISK_LEDGER.md
git commit -m "docs(bundle-d): R1-R24 risk ledger with PENDING status"
```

---

### Task 0.4: Spawn 5-Opus team

**Owner:** Dispatcher

**Step 1:** Use `TeamCreate` (per CLAUDE.md OP #4 pattern). Each agent gets:
- `subagent_type: general-purpose` (NOT specialized; need full toolset)
- `model: opus`
- `mode: bypassPermissions` (REQUIRED — sandbox blocks Bash otherwise; per CLAUDE.md)
- Prompt: read `memory/BUNDLE_D_<LANE>_ANCHOR.md`, execute assigned tasks, post sign-off when GREEN.

**Step 2:** Confirm 5 agents alive
```
TaskList | grep "in_progress.*bundle-d"
```
Expected: 5 entries (Backend, Frontend, Native/Ops, Test, QA).

**Step 3:** Dispatcher inbox-watcher starts polling every 30 min (per OP #8). Agents silent + uncommitted past 30 min → dispatcher absorbs task.

---

### Task 0.5: Ahmed runs `railway login`

**Owner:** Ahmed (manual)

**Step 1:** Ahmed opens a real terminal and runs:
```bash
railway login
```
Browser opens → log in → cached in `%USERPROFILE%\.railway`.

**Step 2:** Dispatcher confirms by retrying:
```
mcp__railway__list_projects
```
Expected: returns project list (not "Unauthorized").

**Step 3:** Backend agent reads current env vars
```
mcp__railway__list_variables
```
Used for Task 4.1 force-update env wiring check.

---

## Phase 1 — Foundation (parallel, day 1)

### Backend Lane (Phase 1)

#### Task 1.B.1: Legal endpoints load fail root-cause

**Files:**
- Read: `app/api/legal_routes.py`
- Read: `app/legal/privacy_policy.md`
- Read: `app/legal/terms_of_service.md`

**Step 1:** Reproduce failure
```bash
curl -i 'https://web-production-58776.up.railway.app/api/v1/legal/privacy_policy'
curl -i 'https://web-production-58776.up.railway.app/api/v1/legal/terms_of_service'
```
Expected (per screenshot): non-200 or timeout.

**Step 2:** Read endpoint code
```python
# app/api/legal_routes.py — observe path resolution + file I/O
```

**Step 3:** Root-cause hypothesis tree:
- (a) Working directory mismatch (Railway runs from root; markdown path may be relative)
- (b) File permissions
- (c) Rate-limiter exhausted
- (d) Middleware short-circuit

**Step 4:** Write failing test
```python
# tests/test_legal_routes.py
def test_privacy_policy_returns_200_with_markdown_body(client):
    response = client.get("/api/v1/legal/privacy_policy")
    assert response.status_code == 200
    assert "Qaren" in response.text or "Privacy" in response.text
```

**Step 5:** Run test
```bash
python -m pytest tests/test_legal_routes.py -v
```
Expected: FAIL (reproduces the bug).

**Step 6:** Fix the root cause based on Step 3 hypothesis tree. Most likely: use `pathlib.Path(__file__).parent.parent / "legal" / filename` not relative path.

**Step 7:** Run test
```bash
python -m pytest tests/test_legal_routes.py -v
```
Expected: PASS.

**Step 8:** Commit
```bash
git add app/api/legal_routes.py tests/test_legal_routes.py
git commit -m "fix(legal): resolve markdown path so privacy + terms endpoints return 200"
```

**Risk control:** R3 N/A here (R3 is history); no risk citation needed.

---

#### Task 1.B.2: Preferences save error fix

**Files:**
- Read: `app/api/auth_routes.py` (preferences endpoint)
- Reproduce: hit `/api/v1/auth/preferences` PUT from a TestFlight account

**Step 1:** Reproduce
```bash
curl -i -X PUT 'https://web-production-58776.up.railway.app/api/v1/auth/preferences' \
  -H 'Authorization: Bearer <ahmed_token>' \
  -H 'Content-Type: application/json' \
  -d '{"language": "en", "region": "bahrain", "budget": "mid"}'
```
Expected: non-200 (per screenshot "saving didn't go through").

**Step 2:** Read endpoint + decode the failure (likely RLS rejection because endpoint uses admin client when it should use user-scoped client per audit-r2 51385d3 H4 pattern).

**Step 3:** Write failing test
```python
def test_preferences_save_returns_200_with_user_client(client, auth_token):
    response = client.put(
        "/api/v1/auth/preferences",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={"language": "en", "region": "bahrain", "budget": "mid"},
    )
    assert response.status_code == 200
```

**Step 4:** Implement fix — likely change `get_admin_supabase_client()` → `get_user_supabase_client(current_user["access_token"])`.

**Step 5:** Run test (live; mark `@pytest.mark.live_db`)
```bash
python -m pytest tests/test_auth_routes.py::test_preferences_save_returns_200_with_user_client -v
```
Expected: PASS.

**Step 6:** Commit
```bash
git add app/api/auth_routes.py tests/test_auth_routes.py
git commit -m "fix(auth): preferences save uses user-scoped Supabase client per RLS"
```

**Risk control:** none new (this is the H4 pattern from audit-r2).

---

#### Task 1.B.3: Refresh-token rotation behavior audit

**Files:**
- Read: `app/api/auth_routes.py:refresh`

**Step 1:** Document current behavior
```bash
curl -X POST 'https://web-production-58776.up.railway.app/api/v1/auth/refresh' \
  -H 'Content-Type: application/json' \
  -d '{"refresh_token": "<token>"}'
# Repeat IMMEDIATELY with same token
curl -X POST 'https://web-production-58776.up.railway.app/api/v1/auth/refresh' \
  -H 'Content-Type: application/json' \
  -d '{"refresh_token": "<same_token>"}'
```
Expected per Sentry [PYTHON-FASTAPI-9]: second call returns 400 "Invalid Refresh Token: Already Used."

**Step 2:** Decision point:
- (a) Backend dedups concurrent refreshes with a Redis lock (5s TTL)
- (b) Backend documents behavior; frontend handles via mutex (Task 1.F.1)

**Recommended:** (b) — frontend mutex is sufficient. Backend stays single-responsibility. Backend's job here is just to confirm Supabase rotation is on (it is — Supabase default).

**Step 3:** No code change needed; add docstring note
```python
# app/api/auth_routes.py refresh endpoint
"""
Supabase rotates refresh tokens on use. Concurrent refresh attempts with the
same token will see the second call fail with 'Already Used.' Frontend
deduplication (api.ts mutex) prevents this; backend is single-token-single-use.
"""
```

**Step 4:** Commit
```bash
git add app/api/auth_routes.py
git commit -m "docs(auth): document refresh-token rotation; FE handles dedup"
```

**Risk control:** R9 (mutex must be singleton) is Frontend's; no BE risk new here.

---

#### Task 1.B.4: Supabase Auth Apple provider config

**Files:** Supabase dashboard (web), `migrations/` (no migration needed)

**Step 1:** Wait for Native/Ops Task 1.N.2 to deliver Apple Service ID + .p8 key.

**Step 2:** Supabase dashboard → Authentication → Providers → Apple → Enable.
- Service ID: from Native/Ops
- Team ID: from Native/Ops
- Key ID: from Native/Ops
- Private Key (.p8 contents): from Native/Ops

**Step 3:** Verify with curl
```bash
curl -X POST 'https://web-production-58776.up.railway.app/api/v1/auth/social/apple' \
  -H 'Content-Type: application/json' \
  -d '{"id_token": "<test_apple_id_token>"}'
```
Expected: 200 with `{user, session}` (not the [PYTHON-FASTAPI-A] "Provider not enabled" error).

**Step 4:** Update Apple 3-leg checkpoint in `BUNDLE_D_RISK_LEDGER.md` row R4 → ADDRESSED.

**Step 5:** Commit (no code change; checkpoint commit)
```bash
git commit --allow-empty -m "ops(auth): R4 checkpoint — Supabase Apple provider enabled + tested 200"
```

---

#### Task 1.B.5: C13 — `delete_user_cascade` cascade-completeness fix

**Files:**
- Create: `migrations/025_delete_user_cascade_completeness.sql`
- Create: `migrations/rollback/025_delete_user_cascade_completeness.sql`
- Existing function: Supabase SQL Editor → Database → Functions → `delete_user_cascade`

**Step 1:** Snapshot current function definition
```sql
-- Run in Supabase SQL Editor, save output to /tmp/delete_cascade_before.sql
SELECT pg_get_functiondef(oid) FROM pg_proc WHERE proname = 'delete_user_cascade';
```

**Step 2:** Identify missing cascade targets via FK audit:
```sql
SELECT tc.table_name, kcu.column_name
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY' AND kcu.referenced_table_name = 'users';
```
Expected hits (per design § 2 + Session 43 forensic): `user_usage`, `referral_invites`, `referral_redemptions`, `expo_push_tokens`, `behavior_profile` (JSON col on users, fine), `comparisons` (already in cascade).

**Step 3:** Write migration 025
```sql
-- migrations/025_delete_user_cascade_completeness.sql
CREATE OR REPLACE FUNCTION delete_user_cascade(user_id_to_delete UUID)
RETURNS void AS $$
BEGIN
  -- Existing deletes (preserve)
  DELETE FROM user_events WHERE user_id = user_id_to_delete;
  DELETE FROM comparison_feedback WHERE user_id = user_id_to_delete;
  DELETE FROM comparisons WHERE user_id = user_id_to_delete;
  DELETE FROM search_logs WHERE user_id = user_id_to_delete;

  -- NEW: cascade-completeness deletes
  DELETE FROM user_usage WHERE user_id = user_id_to_delete;
  DELETE FROM referral_redemptions WHERE invitee_user_id = user_id_to_delete OR inviter_user_id = user_id_to_delete;
  DELETE FROM referral_invites WHERE inviter_user_id = user_id_to_delete;
  DELETE FROM expo_push_tokens WHERE user_id = user_id_to_delete;
  -- admin_audit_log retained for security audit per Session 43 design decision

  -- Existing UPDATE (preserve)
  UPDATE users SET email = 'deleted_' || gen_random_uuid()::text || '@deleted.qaren.app',
                   deleted_at = NOW()
  WHERE id = user_id_to_delete;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

**Step 4:** Write rollback `migrations/rollback/025_delete_user_cascade_completeness.sql` — restore from /tmp/delete_cascade_before.sql snapshot.

**Step 5:** Write failing test
```python
# tests/test_delete_user_cascade.py
def test_delete_user_cascade_removes_user_usage_rows(admin_client, test_user_with_usage):
    user_id = test_user_with_usage["id"]
    admin_client.rpc("delete_user_cascade", {"user_id_to_delete": user_id}).execute()
    rows = admin_client.table("user_usage").select("*").eq("user_id", user_id).execute()
    assert len(rows.data) == 0
```

**Step 6:** Apply migration via Supabase MCP
```
mcp__plugin_supabase_supabase__apply_migration
  name: "025_delete_user_cascade_completeness"
  query: <SQL from Step 3>
```

**Step 7:** Run test
```bash
python -m pytest tests/test_delete_user_cascade.py -v -m live_db
```
Expected: PASS.

**Step 8:** Commit
```bash
git add migrations/025_delete_user_cascade_completeness.sql migrations/rollback/025_delete_user_cascade_completeness.sql tests/test_delete_user_cascade.py
git commit -m "fix(auth): C13 — delete_user_cascade covers user_usage + referrals + push_tokens"
```

**Risk control:** R20 — migration includes rollback file + tested before prod apply.

---

#### Task 1.B.6: C14 — Sentry query-string scrub

**Files:**
- Modify: `app/services/sentry_service.py`
- Test: `tests/test_sentry_service.py`

**Step 1:** Write failing test
```python
# tests/test_sentry_service.py
def test_before_send_scrubs_query_string_in_request_url():
    event = {
        "request": {
            "url": "https://api.qaren.app/api/v1/text/compare?q=user_email@gmail.com+vs+other&nocache=true",
        }
    }
    result = _before_send(event, hint=None)
    assert "user_email@gmail.com" not in result["request"]["url"]
    assert "?q=[REDACTED]" in result["request"]["url"] or "&q=[REDACTED]" in result["request"]["url"]
```

**Step 2:** Run test
```bash
python -m pytest tests/test_sentry_service.py::test_before_send_scrubs_query_string_in_request_url -v
```
Expected: FAIL.

**Step 3:** Implement scrub
```python
# app/services/sentry_service.py — extend _before_send
import re
_QUERY_SCRUB_KEYS = {"q", "query", "email", "search", "text"}

def _scrub_query_string(url: str) -> str:
    if "?" not in url:
        return url
    base, qs = url.split("?", 1)
    parts = qs.split("&")
    scrubbed_parts = []
    for part in parts:
        if "=" in part:
            key, val = part.split("=", 1)
            if key.lower() in _QUERY_SCRUB_KEYS:
                scrubbed_parts.append(f"{key}=[REDACTED]")
                continue
        scrubbed_parts.append(part)
    return f"{base}?{'&'.join(scrubbed_parts)}"

# In _before_send:
if "request" in event and "url" in event["request"]:
    event["request"]["url"] = _scrub_query_string(event["request"]["url"])
```

**Step 4:** Run test
```bash
python -m pytest tests/test_sentry_service.py -v
```
Expected: PASS + zero regressions on existing scrub tests.

**Step 5:** Commit
```bash
git add app/services/sentry_service.py tests/test_sentry_service.py
git commit -m "fix(sentry): C14 — scrub query-string in request URL before send"
```

**Risk control:** R21 — regex targets `?q=`/`?query=`/`?email=`/`?search=`/`?text=`, preserves `?nocache=true` etc. Test pack verifies.

---

#### Task 1.B.7: C15 — Legal-doc rebrand (SmartCompare → Qaren)

**Files:**
- Modify: `app/legal/privacy_policy.md`
- Modify: `app/legal/terms_of_service.md`

**Step 1:** Snapshot before
```bash
cp app/legal/privacy_policy.md /tmp/privacy_before.md
cp app/legal/terms_of_service.md /tmp/terms_before.md
```

**Step 2:** Replace brand strings (sed)
```bash
sed -i 's/SmartCompare/Qaren/g; s/@smartcompare\.app/@qaren.app/g' app/legal/privacy_policy.md app/legal/terms_of_service.md
```

**Step 3:** Manual review — open both files, confirm:
- All "SmartCompare" → "Qaren"
- All `@smartcompare.app` → `@qaren.app`
- Markdown structure intact (no broken headings)
- No reference to features that don't exist (e.g., data export — if it's promised, file follow-up issue)

**Step 4:** Verify in-app rendering unchanged
```bash
curl 'https://web-production-58776.up.railway.app/api/v1/legal/privacy_policy' | head -20
```
Expected: shows "Qaren" prominently, no "SmartCompare."

**Step 5:** Commit
```bash
git add app/legal/privacy_policy.md app/legal/terms_of_service.md
git commit -m "fix(legal): C15 — rebrand SmartCompare → Qaren in privacy + terms"
```

**Risk control:** R22 — sed preserves markdown structure; manual review confirms; LegalScreen renders unchanged.

---

### Frontend Lane (Phase 1)

#### Task 1.F.1: Refresh-token mutex (R9 — module-scope singleton)

**Files:**
- Modify: `SmartCompareApp/src/services/api.ts`
- Test: `SmartCompareApp/src/services/__tests__/api.refreshMutex.test.ts` (new)

**Step 1:** Write failing test
```typescript
// __tests__/api.refreshMutex.test.ts
import { __testRefreshDedup, __resetRefreshMutex } from '../api';

describe('refresh-token mutex', () => {
  beforeEach(() => __resetRefreshMutex());

  it('dedups concurrent refresh calls into one network request', async () => {
    let fetchCount = 0;
    const mockRefresh = jest.fn(async () => {
      fetchCount++;
      await new Promise(r => setTimeout(r, 50));
      return { access_token: 'new', refresh_token: 'newer' };
    });
    const [a, b, c] = await Promise.all([
      __testRefreshDedup(mockRefresh),
      __testRefreshDedup(mockRefresh),
      __testRefreshDedup(mockRefresh),
    ]);
    expect(fetchCount).toBe(1);
    expect(a).toEqual(b);
    expect(b).toEqual(c);
  });
});
```

**Step 2:** Run
```bash
cd SmartCompareApp && npx jest src/services/__tests__/api.refreshMutex.test.ts
```
Expected: FAIL.

**Step 3:** Implement module-scope singleton Promise
```typescript
// src/services/api.ts — at module top level
let _refreshPromise: Promise<RefreshResult> | null = null;

export function __resetRefreshMutex() { _refreshPromise = null; }

export async function __testRefreshDedup(fn: () => Promise<RefreshResult>): Promise<RefreshResult> {
  if (_refreshPromise) return _refreshPromise;
  _refreshPromise = fn().finally(() => { _refreshPromise = null; });
  return _refreshPromise;
}

// 401 interceptor uses __testRefreshDedup(actualRefreshCall)
```

**Step 4:** Run test
```bash
npx jest src/services/__tests__/api.refreshMutex.test.ts
```
Expected: PASS.

**Step 5:** Confirm full test suite still green
```bash
npx jest
```
Expected: 1011+ pass, 0 net new fail.

**Step 6:** Commit
```bash
git add src/services/api.ts src/services/__tests__/api.refreshMutex.test.ts
git commit -m "fix(api): R9/C16 — refresh-token mutex as module-scope singleton Promise"
```

**Risk control:** R9 ADDRESSED — PR comment includes the singleton code excerpt.

---

#### Task 1.F.2: EditProfile `profile.name` i18n key add

**Files:**
- Modify: `SmartCompareApp/src/i18n/en.json` (add `profile.name: "Name"`)
- Modify: `SmartCompareApp/src/i18n/ar.json` (add `profile.name: "الاسم"`)

**Step 1:** Add keys (alphabetical insertion)
```json
// en.json — between "profile.editProfile" and "profile.settings"
"profile.name": "Name",
```
```json
// ar.json
"profile.name": "الاسم",
```

**Step 2:** Verify reference still works
```bash
grep -n "profile\.name" src/screens/EditProfileScreen.tsx
# Expected: line 135 label, line 143 placeholder
```

**Step 3:** Run i18n consistency test
```bash
npx jest src/__tests__/i18n.test.ts
```
Expected: PASS — key counts match EN+AR.

**Step 4:** Run copy-policy gate
```bash
npx jest src/__tests__/copy-policy.test.ts
```
Expected: PASS — no scary vocab.

**Step 5:** Commit
```bash
git add src/i18n/en.json src/i18n/ar.json
git commit -m "fix(i18n): add missing profile.name key for EditProfileScreen"
```

**Risk control:** R11 — default "Name" / "الاسم" applied unless Ahmed objects in PR.

---

#### Task 1.F.3: "Edit style profile" navigate fix (decision + implementation)

**Files:**
- Read: `SmartCompareApp/App.tsx:301`
- Read: `SmartCompareApp/src/screens/EditProfileScreen.tsx` (the `navigation.navigate('Onboarding', { mode: 'edit', source: 'styleProfile' })` call)

**Step 1:** Decision tree
- **Option A**: register `Onboarding` permanently in post-onboarding stack with `initialParams.mode='full'`; pass `mode='edit'` for re-entry. Pro: minimal code. Con: navigator carries extra screen weight at all times.
- **Option B**: extract `StyleProfileScreen` as standalone modal that reuses the 4 Onboarding steps' UI. Pro: cleaner separation. Con: more code, duplication risk.

**Recommended:** Option A — minimal change, low risk.

**Step 2:** Write failing test
```typescript
// __tests__/App.navigation.test.tsx
it('navigates from EditProfile to Onboarding in edit mode', () => {
  const { getByTestId } = render(<App />);
  // ... simulate auth + reach EditProfile
  fireEvent.press(getByTestId('edit-style-profile-button'));
  expect(getByTestId('onboarding-screen-edit-mode')).toBeTruthy();
});
```

**Step 3:** Modify `App.tsx`
```typescript
// App.tsx — in the post-auth, post-needsPreferences branch (else block)
<Stack.Screen
  name="Onboarding"
  options={{ presentation: 'modal' }}
>
  {(props) =>
    features.ENABLE_NEW_ONBOARDING ? (
      <NewOnboardingHost
        mode={props.route.params?.mode ?? 'full'}
        onComplete={() => props.navigation.goBack()}
      />
    ) : (
      <OnboardingScreen {...props} onComplete={() => props.navigation.goBack()} />
    )
  }
</Stack.Screen>
```

**Step 4:** Modify `NewOnboardingHost` to accept `mode` prop and skip non-style steps when `mode==='edit'`.

**Step 5:** Run navigation test
```bash
npx jest src/__tests__/App.navigation.test.tsx
```
Expected: PASS.

**Step 6:** Run full suite
```bash
npx tsc --noEmit && npx jest
```
Expected: 0 tsc errors, 1011+ pass.

**Step 7:** Commit
```bash
git add App.tsx src/screens/onboarding/ src/__tests__/App.navigation.test.tsx
git commit -m "fix(nav): register Onboarding in post-auth stack with mode param for style edit"
```

---

#### Task 1.F.4: Camera help overlay

**Files:**
- Modify: `SmartCompareApp/src/screens/ScanCameraScreen.tsx`
- Add: `SmartCompareApp/src/components/CameraHelpOverlay.tsx`
- i18n: `src/i18n/en.json` + `ar.json`

**Step 1:** Add overlay copy
```json
// en.json
"camera.help.title": "How to scan",
"camera.help.step1": "Frame both products in the 1 and 2 boxes.",
"camera.help.step2": "Tap the shutter to capture.",
"camera.help.step3": "Wait a moment — Qaren reads the boxes and compares them.",
"camera.help.dismiss": "Got it",
```
```json
// ar.json
"camera.help.title": "كيف يعمل المسح",
"camera.help.step1": "ضع المنتجين في المربعين ١ و ٢.",
"camera.help.step2": "اضغط زر التصوير.",
"camera.help.step3": "انتظر لحظة — قارن يقرأ المربعين ويقارنهما.",
"camera.help.dismiss": "حسناً",
```

**Step 2:** Build `CameraHelpOverlay.tsx` as semi-transparent Modal with the 3 steps + dismiss button.

**Step 3:** Wire `?` button to toggle overlay state
```typescript
// ScanCameraScreen.tsx
const [helpVisible, setHelpVisible] = useState(false);
// ... <IconButton icon="help" onPress={() => setHelpVisible(true)} />
// <CameraHelpOverlay visible={helpVisible} onDismiss={() => setHelpVisible(false)} />
```

**Step 4:** Run copy-policy
```bash
npx jest src/__tests__/copy-policy.test.ts
```
Expected: PASS — no scary words.

**Step 5:** Commit
```bash
git add src/components/CameraHelpOverlay.tsx src/screens/ScanCameraScreen.tsx src/i18n/en.json src/i18n/ar.json
git commit -m "feat(camera): wire ? button to help overlay with 3-step instructions"
```

**Risk control:** R17 ADDRESSED — copy-policy test enforces no scary vocab.

---

#### Task 1.F.5: History detail fetch fix (depends on Backend Task 1.B.* schema_version investigation)

**Files:** Block on Backend confirming whether Ahmed's failing comparison is `schema_version=1` (R3).

**If schema_version=1 root cause:** Backend backfills + relaxes filter; Frontend has no code change beyond improved error message ("This comparison is from an older version — please run a fresh comparison from Home").

**If different root cause:** Frontend implements based on Backend's RCA finding.

**Step 1:** Wait on Backend RCA (max 30 min, then dispatcher escalates per OP #8).

**Step 2:** Implement per RCA. If just an error-message change:
```typescript
// src/screens/ResultsScreen.tsx — improve loadFromHistory failure copy
const errorCopy = response.status === 404
  ? t('history.error.notFound')  // "This comparison is from an older version — please run a fresh comparison from Home."
  : t('history.error.generic');  // existing "This one's not loading. Run a fresh comparison from Home."
```

**Step 3:** Add i18n keys + run copy-policy.

**Step 4:** Commit
```bash
git add src/screens/ResultsScreen.tsx src/i18n/en.json src/i18n/ar.json
git commit -m "fix(history): differentiate v1-legacy vs generic load failure copy"
```

---

#### Task 1.F.6: C17 — `ai_sharing_enabled` default OFF for new users

**Files:**
- Modify: `SmartCompareApp/src/screens/ProfileScreen.tsx:102`
- Possible: Backend onboarding default (BE Task TBD if applicable)

**Step 1:** Write failing test
```typescript
// __tests__/ProfileScreen.aiSharingDefault.test.tsx
it('new user with undefined ai_sharing_enabled sees toggle OFF', () => {
  const user = { id: 'x', preferences: {} };  // ai_sharing_enabled undefined
  const { getByTestId } = render(<ProfileScreen user={user} />);
  expect(getByTestId('ai-sharing-toggle').props.value).toBe(false);
});
```

**Step 2:** Run
```bash
npx jest __tests__/ProfileScreen.aiSharingDefault.test.tsx
```
Expected: FAIL (current default is true).

**Step 3:** Flip default
```typescript
// ProfileScreen.tsx:102 — change
const aiSharingEnabled = user?.preferences?.ai_sharing_enabled ?? false;  // was ?? true
```

**Step 4:** Verify existing users unaffected — existing rows with `ai_sharing_enabled: true` still see ON; only undefined → OFF.

**Step 5:** Run test
```bash
npx jest __tests__/ProfileScreen.aiSharingDefault.test.tsx
```
Expected: PASS.

**Step 6:** Commit
```bash
git add src/screens/ProfileScreen.tsx src/__tests__/ProfileScreen.aiSharingDefault.test.tsx
git commit -m "fix(privacy): C17 — ai_sharing_enabled defaults OFF per PDPL opt-IN"
```

**Risk control:** R23 ADDRESSED — only `undefined` → OFF; existing `true` rows untouched.

---

### Native/Ops Lane (Phase 1)

#### Task 1.N.1: Bundle ID claim research

**Files:** App Store Connect (web), `SmartCompareApp/app.json`

**Step 1:** Login to App Store Connect with Ahmed's Apple Dev account (Native/Ops pings Ahmed for Apple ID + password OR uses ASIA pre-shared credentials).

**Step 2:** Try claiming `app.qaren` (reverse-DNS of owned `qaren.app`):
- App Store Connect → My Apps → "+" → New App → Bundle ID: register `app.qaren`
- If taken → try `com.qaren.app`
- If taken → try `bh.qaren.app`
- If all 3 taken → escalate to Ahmed via PR comment for choice

**Step 3:** Once claimed, update `app.json`
```json
{
  "expo": {
    "ios": { "bundleIdentifier": "app.qaren" }
  }
}
```

**Step 4:** Commit
```bash
git add app.json
git commit -m "ops(ios): claim bundle ID app.qaren in App Store Connect"
```

**Risk control:** R6 ADDRESSED — fallback ladder traversed; Ahmed escalation only if all 3 taken.

---

#### Task 1.N.2: Apple Developer Portal Service ID + .p8

**Step 1:** Apple Dev Portal → Certificates, Identifiers & Profiles → Identifiers → New (Services IDs).
- Description: "Qaren Sign in with Apple"
- Identifier: `app.qaren.signin` (or matching scheme)
- Sign in with Apple: enabled, configured to primary App ID `app.qaren`
- Domains and Subdomains: `qaren.app`
- Return URLs: `https://web-production-58776.up.railway.app/api/v1/auth/social/apple/callback`

**Step 2:** Apple Dev Portal → Keys → New
- Key Name: "Qaren Sign in with Apple Key"
- Enable: Sign in with Apple, configured to primary App ID `app.qaren`
- Download .p8 file → save to local secrets vault (NOT in repo)

**Step 3:** Hand off Service ID + Team ID + Key ID + .p8 contents to Backend (Task 1.B.4) via secure channel (NOT PR comment).

**Step 4:** Update R4 risk row
- "Apple 3-leg checkpoint": Service ID ✓ (Step 1), .p8 ✓ (Step 2), Supabase ON ✓ (Backend confirms), backend curl 200 ✓ (Backend confirms)

**Step 5:** Commit (empty checkpoint commit)
```bash
git commit --allow-empty -m "ops(apple): R4 step 1+2 — Service ID created + .p8 downloaded"
```

---

#### Task 1.N.3: `expo-apple-authentication` install + plugin (R5)

**Files:**
- Modify: `SmartCompareApp/package.json`
- Modify: `SmartCompareApp/app.json`

**Step 1:** Install
```bash
cd SmartCompareApp && npx expo install expo-apple-authentication
```

**Step 2:** Add to `app.json` plugins
```json
{
  "expo": {
    "plugins": [
      "expo-apple-authentication"
    ],
    "ios": {
      "bundleIdentifier": "app.qaren",
      "usesAppleSignIn": true,
      "entitlements": {
        "com.apple.developer.applesignin": ["Default"]
      }
    }
  }
}
```

**Step 3:** Confirm package.json updated
```bash
grep expo-apple-authentication package.json
```

**Step 4:** Commit BEFORE any EAS build trigger (R5)
```bash
git add package.json app.json
git commit -m "ops(ios): install expo-apple-authentication + entitlement plugin"
```

**Risk control:** R5 ADDRESSED — plugin block committed before EAS build (R14 also implicitly: entitlement in `app.json`).

---

#### Task 1.N.4: C16 — `expo-notifications` plugin entry

**Files:** `SmartCompareApp/app.json`

**Step 1:** Verify already installed
```bash
grep expo-notifications package.json
```
If missing: `npx expo install expo-notifications`.

**Step 2:** Add plugin to `app.json`
```json
{
  "expo": {
    "plugins": [
      "expo-apple-authentication",
      [
        "expo-notifications",
        {
          "icon": "./assets/notification-icon.png",
          "color": "#10B981",
          "sounds": []
        }
      ]
    ],
    "ios": {
      "infoPlist": {
        "NSUserNotificationUsageDescription": "Qaren sends helpful comparison insights — no spam."
      }
    },
    "android": {
      "permissions": ["NOTIFICATIONS"]
    }
  }
}
```

**Step 3:** Commit
```bash
git add app.json
git commit -m "ops(notifications): C16 — add expo-notifications plugin with iOS + Android permissions"
```

---

#### Task 1.N.5: EAS secret `SENTRY_AUTH_TOKEN`

**Step 1:** Ahmed creates Sentry auth token
- Sentry → Settings → Account → Auth Tokens → New
- Scopes: `project:read`, `project:write`, `project:releases`
- Copy token

**Step 2:** Native/Ops creates EAS secret
```bash
cd SmartCompareApp && eas secret:create --scope project --name SENTRY_AUTH_TOKEN --value "<token>"
```

**Step 3:** Remove disable env from `eas.json`
```json
// eas.json — preview profile
{
  "preview": {
    "env": {
      // REMOVE: "SENTRY_DISABLE_AUTO_UPLOAD": "true",
      // REMOVE: "SENTRY_ALLOW_FAILURE": "true"
    }
  }
}
```

**Step 4:** Commit `eas.json` change
```bash
git add eas.json
git commit -m "ops(sentry): enable sourcemap upload on preview + production builds"
```

---

#### Task 1.N.6: DNS planning for `qaren.app`

**Step 1:** Pick hosting provider — recommend **Vercel** for static landing + subpages (fastest path, free tier OK).

**Step 2:** Document DNS plan in PR comment
- `qaren.app` A/AAAA → Vercel
- `qaren.app/privacy`, `/terms`, `/support` → Vercel serves static markdown→HTML
- `www.qaren.app` 301 → `qaren.app`
- TTL: 300s during cutover (per R24)

**Step 3:** No commit yet (DNS work happens in Phase 2 Task 2.N.1 after landing page placeholder is built).

---

### Test Lane (Phase 1)

#### Task 1.T.1: Red-green test scaffolds + pre-existing failure triage

**Step 1:** Inventory pre-existing RED tests
```bash
python -m pytest tests/ --collect-only -q 2>&1 | grep -E "(TestReengagementSubToggles|test_phase1_includes_reviews|test_comparison_quality_in_response_metadata_payload)"
```
Expected: 3 tests confirmed present.

**Step 2:** Run them in isolation to confirm RED today
```bash
python -m pytest tests/test_reengagement.py::TestReengagementSubToggles -v
python -m pytest tests/ -k "test_phase1_includes_reviews" -v
python -m pytest tests/ -k "test_comparison_quality_in_response_metadata_payload" -v
```
Expected: all 3 FAIL.

**Step 3:** Triage table in PR comment:
| Test | Bundle D owner | Expected to GREEN via |
|---|---|---|
| TestReengagementSubToggles | Backend (R18, Task 2.B.5) | Reengagement subs endpoint creation |
| test_phase1_includes_reviews | Test (existing) | Defer — D2 Intervention 1 follow-up (not in Bundle D scope) |
| test_comparison_quality_in_response_metadata_payload | Backend (Task 2.B.1) | B.0 response_builder kwarg refactor |

**Step 4:** Commit triage document
```bash
git add docs/plans/bundle-d-red-test-triage.md
git commit -m "docs(test): triage 3 pre-existing RED tests with Bundle D owners"
```

---

### QA Lane (Phase 1)

#### Task 1.Q.1: Cross-QA matrix template + Sentry baseline

**Step 1:** Create cross-QA matrix file `docs/plans/bundle-d-cross-qa-matrix.md`
```markdown
| Reviewer | Backend tasks | Frontend tasks | Native/Ops tasks |
|---|---|---|---|
| Backend | self | 1.F.1, 1.F.6 | — |
| Frontend | 1.B.2, 1.B.3 | self | 1.N.3, 1.N.4 |
| Native/Ops | 1.B.4 | 1.F.4 | self |
| QA | ALL | ALL | ALL |
```

**Step 2:** Capture Sentry MCP baseline
```
mcp__plugin_sentry_sentry__search_issues
  organizationSlug: "qaren-rr"
  query: "firstSeen:-30d"
  sort: "freq"
  limit: 50
```
Save output to `docs/plans/bundle-d-sentry-baseline-2026-05-23.txt`.

**Step 3:** Commit
```bash
git add docs/plans/bundle-d-cross-qa-matrix.md docs/plans/bundle-d-sentry-baseline-2026-05-23.txt
git commit -m "docs(qa): cross-QA matrix + Sentry baseline for Bundle D"
```

---

## Phase 2 — Integration (depends on Phase 1, day 1-2)

### Backend Lane (Phase 2)

#### Task 2.B.1: B.0 — response_builder kwarg refactor

**Files:** `app/services/response_builder.py`

**Step 1:** Find current positional signature
```bash
grep -n "def build_comparison_response" app/services/response_builder.py
```

**Step 2:** Refactor to keyword-only
```python
def build_comparison_response(
    *,
    products,
    comparison,
    scoring_result,
    metadata,
    personalization=None,
    # ... all other params keyword-only
):
    ...
```

**Step 3:** Update all call sites to use keyword args
```bash
grep -rn "build_comparison_response(" app/ | head -20
```
Update each to `build_comparison_response(products=..., comparison=...)` etc.

**Step 4:** Run targeted test
```bash
python -m pytest tests/ -k "test_comparison_quality_in_response_metadata_payload" -v
```
Expected: PASS (was RED pre-Bundle-D).

**Step 5:** Run full backend suite
```bash
python -m pytest tests/ --timeout=180
```
Expected: baseline ≥503 maintained.

**Step 6:** Commit
```bash
git add app/services/response_builder.py
git commit -m "refactor(response): B.0 — keyword-only signature, greens 3 RED tests"
```

---

#### Task 2.B.2 through 2.B.5: A.7.2, A.8.1, A.4.8, A.6.2-A.6.5

**Pattern repeats per item:**
- Read design doc § 2 entry for that item
- Write failing test that exercises the new behavior
- Implement minimal code
- Run test
- Run full suite
- Commit with `feat(scoring/extraction)` prefix

**Specific notes:**
- **A.7.2** (`response_builder.py`): when `source_method == 'estimated'`, set `price.note = None`. 5 lines + 1 test.
- **A.8.1** (`scoring_service.py`): replace `_dim_dpi`/`_popularity`/`_build_quality` with `CATEGORY_DIMENSIONS[category]` lookup. Refactor + test.
- **A.4.8** (`extraction_service.py`): add Tier 3 GPT-4o batched synthesis when Tier 2 returns blank for both products. Use existing `model_router.get_model(priority="high")`. New test + cost budget check.
- **A.6.2-A.6.5** (`scoring_service.py`): richer `delta_text` + cross-tier framing + `value_match` + `budget_mismatch` metadata. 4 sub-tasks, 4 commits.

---

#### Task 2.B.6: 24 `_fire_and_forget` audit sweep

**Step 1:** Inventory
```bash
grep -rn "asyncio\.create_task" app/api/ | grep -v _fire_and_forget
```

**Step 2:** For each site, decide:
- WRAP: wrap with `_fire_and_forget(coro, label="event_name")` from `app/services/structured_comparison_service.py`
- SKIP-with-reason: site is legitimately fire-and-forget where failure is acceptable (e.g., trivial analytics ping; failure logged at Sentry layer)

**Step 3:** PR comment lists each of 24 sites with decision.

**Step 4:** Run security regression
```bash
python -m pytest tests/test_security_regression.py -v
```
Expected: 100% pass.

**Step 5:** Commit
```bash
git add app/api/
git commit -m "fix(audit-r3): 24 fire-and-forget audit sites wrapped or judged"
```

**Risk control:** R15 ADDRESSED — PR comment per-site decision log.

---

#### Task 2.B.7: Reengagement subs endpoint (R18)

**Step 1:** Check if endpoint exists
```bash
grep -rn "reengagement-subs\|reengagement_subscriptions" app/api/
```

**Step 2a — if missing:** create `PUT /api/v1/auth/reengagement-subs` per design § 11 Default #6.

**Step 2b — if exists but broken:** fix.

**Step 3:** Write failing test
```python
def test_put_reengagement_subs_updates_all_three_flags(client, auth_token):
    resp = client.put(
        "/api/v1/auth/reengagement-subs",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={"decision_insights": False, "peer_decision_updates": True, "decision_retrospectives": False},
    )
    assert resp.status_code == 200
```

**Step 4:** Run test, implement, re-run, commit.

```bash
git add app/api/auth_routes.py tests/test_auth_routes.py
git commit -m "feat(auth): R18 — PUT reengagement-subs endpoint wires Profile toggles"
```

**Risk control:** R18 ADDRESSED — endpoint exists with 3 flags.

---

### Frontend Lane (Phase 2)

#### Task 2.F.1: Profile toggle optimistic UI + 5-toggle wiring audit

**Files:** `SmartCompareApp/src/screens/ProfileScreen.tsx`

**Step 1:** Write failing test (optimistic update before resolution)
```typescript
it('toggle state flips immediately even before API resolves', async () => {
  const mockApi = jest.fn(() => new Promise(r => setTimeout(() => r({ ok: true }), 200)));
  const { getByTestId } = render(<ProfileScreen apiCall={mockApi} />);
  const toggle = getByTestId('ai-sharing-toggle');
  expect(toggle.props.value).toBe(false);
  fireEvent.press(toggle);
  expect(toggle.props.value).toBe(true);  // instant
  // API hasn't resolved yet
});
```

**Step 2:** Implement
```typescript
const handleToggle = useCallback(async (newValue: boolean) => {
  setLocalValue(newValue);  // optimistic
  try {
    await api.updatePreferences({ ai_sharing_enabled: newValue });
  } catch (e) {
    setLocalValue(!newValue);  // rollback
    Alert.alert(t('profile.toggle.error.title'), t('profile.toggle.error.body'));
  }
}, []);
```

**Step 3:** Wire all 5 toggles end-to-end:
- AI sharing → `api.updatePreferences({ai_sharing_enabled})` (existing)
- Smart Decision Notifications (master) → cron-gated; UI toggle saves to `users.preferences.notifications_enabled`
- Decision Insights → `api.updateReengagementSubs({decision_insights})`
- Peer Decision Updates → `api.updateReengagementSubs({peer_decision_updates})`
- Decision Retrospectives → `api.updateReengagementSubs({decision_retrospectives})`

**Step 4:** Confirm 5 toggles save end-to-end via integration test (live API).

**Step 5:** Commit
```bash
git add src/screens/ProfileScreen.tsx src/services/api.ts
git commit -m "feat(profile): optimistic toggles + 5-toggle end-to-end wiring audit"
```

---

#### Task 2.F.2: HomeScreen Claude-Design refresh implementation

**Files:**
- Modify: `SmartCompareApp/src/screens/HomeScreen.tsx`
- Possibly: `SmartCompareApp/src/theme/index.ts` (token extension)
- Possibly: new components in `src/components/`

**Step 1:** Wait for Ahmed to provide Claude-Design output (tokens.json + example .tsx).

**Step 2:** Consume tokens additively
```typescript
// src/theme/index.ts — extend, don't replace
export const theme = {
  ...existingTokens,
  bundleD: claudeDesignTokens,  // additive
};
```

**Step 3:** Apply to HomeScreen sections per Claude-Design example .tsx.

**Step 4:** PRESERVE Bundle B contract (R16):
- TwoInputShell (don't remove)
- Paste auto-split (lines 447, 455)
- Mode auto-switch (line 462)
- Content moderation (line 221)
- All 8 analytics events still fire

**Step 5:** Write Bundle B contract preservation test
```typescript
it('preserves Bundle B contract: TwoInputShell paste-split fires after redesign', () => {
  // ... reuse existing Bundle B test from __tests__/HomeScreen.test.ts
});
```

**Step 6:** Run full PR #6 EN+AR walkthrough mental model:
- All 10 EN visual checks (from `memory/next-session-bundle-b-phase4-walkthroughs.md`)
- All 7 AR mirror checks

**Step 7:** Run jest + tsc
```bash
npx tsc --noEmit && npx jest
```
Expected: 1011+ pass, 0 tsc errors.

**Step 8:** Commit
```bash
git add src/screens/HomeScreen.tsx src/theme/index.ts src/components/
git commit -m "feat(home): Claude-Design refresh; preserves Bundle B TwoInputShell contract"
```

**Risk control:** R16 ADDRESSED — Bundle B contract preservation test passes.

---

### Native/Ops Lane (Phase 2)

#### Task 2.N.1: EAS preview build

**Step 1:** Verify all Phase 1 ops commits in place
```bash
git log --oneline | head -10
```
Expected: bundle ID, expo-apple-authentication, expo-notifications, sentry auth token all present.

**Step 2:** Trigger EAS preview build
```bash
cd SmartCompareApp && eas build --profile preview --platform ios --non-interactive
```
Wait ~15 min for build to complete.

**Step 3:** Verify build artifact URL
```bash
eas build:list --limit 1
```
Expected: status=finished, artifact .ipa URL ready.

**Step 4:** Install on Ahmed's device via TestFlight Internal OR EAS Internal Distribution
```bash
eas build:run <build-id>
```
OR Ahmed scans QR code.

**Step 5:** Smoke-test Google Sign-In + Apple Sign-In on the device.

**Step 6:** Commit (empty for record)
```bash
git commit --allow-empty -m "ops(eas): preview build green, Google + Apple Sign-In smoke 200"
```

---

#### Task 2.N.2: Landing page hosting setup

**Step 1:** Create Vercel project (or use existing) for `qaren.app`
- Native/Ops creates GitHub repo `qaren-landing` (or sub-folder in main repo)
- Repo serves:
  - `/index.html` — placeholder "Qaren — Coming soon to App Store / Google Play"
  - `/privacy.html` — markdown→HTML render of `app/legal/privacy_policy.md` (post-C15 rebrand)
  - `/terms.html` — same for terms_of_service.md
  - `/support` — 301 to `mailto:support@qaren.app`

**Step 2:** Vercel deploy + verify
```bash
curl -i 'https://<vercel-preview-url>/privacy.html'
```
Expected: 200 with Qaren-branded content.

**Step 3:** DNS cutover (TTL 300s per R24)
- Cloudflare DNS for qaren.app A/AAAA → Vercel

**Step 4:** Verify
```bash
curl -i 'https://qaren.app/privacy.html'
curl -i 'https://qaren.app/'
```
Expected: 200 + placeholder served.

**Step 5:** Commit hosting config
```bash
git add infra/landing/  # or wherever the Vercel repo lives
git commit -m "ops(landing): qaren.app placeholder + /privacy + /terms live"
```

**Risk control:** R24 ADDRESSED — DNS TTL 300s for fast revert.

---

## Phase 3 — TestFlight Pipeline (depends on Phase 2 EAS preview build, day 2)

### Native/Ops Lane (Phase 3)

#### Task 3.N.1: EAS production build

**Step 1:** Trigger
```bash
eas build --profile production --platform ios --non-interactive
```
Wait ~20 min.

**Step 2:** Verify artifact ready
```bash
eas build:list --limit 1 --profile production
```

---

#### Task 3.N.2: App Store Connect upload

**Step 1:** Submit via EAS Submit
```bash
eas submit --profile production --platform ios --latest
```

**Step 2:** Wait for Apple processing (~30 min per R8). Monitor in App Store Connect → My Apps → Qaren → TestFlight.

**Step 3:** Once "Ready to Test" status: configure internal test group, add Ahmed's email.

**Step 4:** Ahmed receives invite → installs TestFlight on iPhone → installs Qaren build → cold-starts.

---

#### Task 3.N.3: ASC Privacy Nutrition Labels submit

**Step 1:** Native/Ops drafts answers based on observed data flows:

| Category | Data | Linked to user? | Used for tracking? |
|---|---|---|---|
| Contact Info | Email | Yes | No |
| Identifiers | Device fingerprint (SHA-256), user ID | Yes | No |
| Usage Data | Product interactions, app analytics | Yes | No |
| User Content | Search queries (when `ai_sharing_enabled=true`) | Yes | No |
| Diagnostics | Crash logs, performance via Sentry | No | No |

**Step 2:** Post draft to PR for Ahmed approval (BLOCKING — wait for approval).

**Step 3:** Once approved, submit in App Store Connect → App Privacy.

**Step 4:** Commit
```bash
git commit --allow-empty -m "ops(asc): Privacy Nutrition Labels submitted per Ahmed approval"
```

---

### Backend Lane (Phase 3)

#### Task 3.B.1: Full prod-Railway curl smoke pack

**Step 1:** Run curl pack
```bash
# Auth
curl -i 'https://web-production-58776.up.railway.app/api/v1/auth/register' -X POST ...
curl -i 'https://web-production-58776.up.railway.app/api/v1/auth/login' -X POST ...

# Compare
curl -i 'https://web-production-58776.up.railway.app/api/v1/text/compare?q=iPhone+15+vs+Galaxy+S24'

# Legal (was C15-rebranded)
curl -i 'https://web-production-58776.up.railway.app/api/v1/legal/privacy_policy'
curl -i 'https://web-production-58776.up.railway.app/api/v1/legal/terms_of_service'

# Preferences
curl -i -X PUT 'https://web-production-58776.up.railway.app/api/v1/auth/preferences' ...

# History
curl -i 'https://web-production-58776.up.railway.app/api/v1/comparisons?limit=10' ...

# Social Apple
curl -i 'https://web-production-58776.up.railway.app/api/v1/auth/social/apple' -X POST ...
```

**Step 2:** All return 200 → record in PR comment.

---

### Frontend Lane (Phase 3)

#### Task 3.F.1: PR #6 Bundle B simulator sign-off

**Step 1:** Open `memory/next-session-bundle-b-phase4-walkthroughs.md` and `.pr-6-phase4-comment.md`.

**Step 2:** On the EAS preview build installed in Task 2.N.1, run:
- EN walkthrough A-L (10 visual checks)
- AR walkthrough M-P (7 RTL mirror checks)
- Haptic feel verification
- 4 screenshots (EN/AR × TwoInputShell/PaywallBanner)
- Analytics `[analytics]` console.log capture (all 8 events)

**Step 3:** Post the prepared sign-off comment on PR #6 with screenshots + analytics block attached.

**Step 4:** Commit (empty for record)
```bash
git commit --allow-empty -m "ops(pr-6): Bundle B Phase 4 sign-off posted with screenshots + analytics"
```

---

### Test Lane (Phase 3)

#### Task 3.T.1: Full test sweep

```bash
# Backend
python -m pytest tests/ --timeout=180 -v
# Frontend
cd SmartCompareApp && npx tsc --noEmit && npx jest
```

**Expected:**
- Backend: ≥503/503 (baseline) + new tests added
- Frontend: tsc 0 errors, jest 1011+ pass

---

### QA Lane (Phase 3)

#### Task 3.Q.1: Cross-review all Phase 2 work

Per cross-QA matrix from Task 1.Q.1. Send-back loop opens if any RED finding.

#### Task 3.Q.2: Sentry MCP 30-min watch post-deploy

```
mcp__plugin_sentry_sentry__search_issues
  organizationSlug: "qaren-rr"
  query: "firstSeen:-2h"
  sort: "date"
  limit: 30
```

Expected: ZERO new issue types over Phase-0 baseline (saved in `bundle-d-sentry-baseline-2026-05-23.txt`).

---

## Phase 4 — Close-Out (day 2-3)

### Task 4.B.1: Force-update env vars

**Step 1:** Via Railway MCP
```
mcp__railway__set_variables
  variables: {
    "APP_MIN_VERSION": "<TestFlight build version, e.g. 1.0.0>",
    "APP_LATEST_VERSION": "<same>",
    "APP_FORCE_UPDATE": "false"
  }
```

**Step 2:** Verify
```bash
curl 'https://web-production-58776.up.railway.app/api/v1/app/version'
```
Expected: returns the values above.

**Risk control:** R19 — `APP_FORCE_UPDATE` stays false until all testers on new build.

---

### Task 4.B.2: Reengagement flag flip (depends on Ahmed acknowledgment)

**Step 1:** Wait for Ahmed PR comment: "first cron tick is safe, flip ENABLE_REENGAGEMENT_PUSHES."

**Step 2:** Via Railway MCP
```
mcp__railway__set_variables
  variables: { "ENABLE_REENGAGEMENT_PUSHES": "true" }
```

**Risk control:** R12 ADDRESSED — flag flip gated on explicit Ahmed acknowledgment.

---

### Task 4.N.1: App icon + splash final audit

**Step 1:** Open `assets/icon.png` + `assets/splash.png` in image viewer.
**Step 2:** Confirm:
- No "SmartCompare" text
- Qaren wordmark or logo only
- iOS densities @1x/@2x/@3x present (or single 1024×1024 with auto-scaling)
- Android densities mdpi through xxxhdpi present
- EN+AR locales both render correctly

**Step 3:** If any density missing, regenerate via design assets.

**Step 4:** Commit any updates
```bash
git add assets/
git commit -m "ops(assets): final icon + splash audit, zero SmartCompare residue"
```

---

### Task 4.A.1 through 4.A.5: All-agent sign-off in PR

Each agent posts their own GREEN comment per design § 9 rubric. Format:

```markdown
## <Lane> sign-off — verified 2026-05-XX

Per `BUNDLE_D_<LANE>_ANCHOR.md` checklist:
- ✓ Item 1 — verified via <command>
- ✓ Item 2 — verified via <command>
- ...

Cross-QA reviewer: <QA agent name>
QA verdict: GREEN

Risks I own (status): R<N> ADDRESSED, R<M> ADDRESSED, ...
```

---

### Task 4.D.1: Dispatcher final merge

**Step 1:** Verify all 5 lane sign-offs present in PR.
**Step 2:** Verify `BUNDLE_D_RISK_LEDGER.md` — zero PENDING.
**Step 3:** Verify TestFlight build live + Ahmed installed + tested.
**Step 4:** Merge
```bash
git -C ../smartcompare checkout main
git -C ../smartcompare merge --no-ff feature/bundle-d-testflight-readiness -m "Merge Bundle D: TestFlight Readiness (59 items)"
git -C ../smartcompare push origin main
```
Wait Railway ~90s.

**Step 5:** Post-merge smoke
```bash
curl 'https://web-production-58776.up.railway.app/health'
```
Expected: 200.

**Step 6:** Update CLAUDE.md + MEMORY.md per OP #5
```bash
git -C ../smartcompare add CLAUDE.md MEMORY.md docs/SESSION_BUNDLES.md
git -C ../smartcompare commit -m "docs(bundle-d): session 53 close-out + CLAUDE.md state"
git -C ../smartcompare push origin main
```

**Step 7:** Disassemble team per Ahmed's contract rule #1.

---

## Sign-Off Checklists

### Pre-merge dispatcher checklist
- [ ] All 5 lane sign-offs GREEN in PR
- [ ] `BUNDLE_D_RISK_LEDGER.md` — zero PENDING
- [ ] TestFlight build live + Ahmed installed + smoke flow tested
- [ ] PR #6 Bundle B sign-off comment posted
- [ ] Sentry MCP 30-min watch: zero new issue types
- [ ] Supabase audit-log SQL pack: privacy invariants hold
- [ ] All pre-existing RED tests triaged (greened or explicitly deferred)
- [ ] All defaults applied per design § 11 (unless Ahmed override)

### Post-merge dispatcher checklist
- [ ] Railway redeploy verified green (curl /health 200)
- [ ] CLAUDE.md updated with Bundle D entry
- [ ] MEMORY.md updated (pending follow-ups moved to "Resolved")
- [ ] `docs/SESSION_BUNDLES.md` Bundle D entry added
- [ ] Team disassembled (all 5 agents shut down)
- [ ] Final "Bundle D verified" comment on PR with merge SHA + timestamp

---

## Reference

- Design doc: `docs/plans/2026-05-23-bundle-d-testflight-readiness-design.md` (commit `efee754`)
- Memory anchors: `memory/BUNDLE_D_*.md` (written in Task 0.2)
- Risk ledger: `memory/BUNDLE_D_RISK_LEDGER.md` (written in Task 0.3)
- PR #6 sign-off template: `.pr-6-phase4-comment.md`
- PR #6 simulator checklist: `memory/next-session-bundle-b-phase4-walkthroughs.md`
- CLAUDE.md operating principles: OP #4 (TeamCreate), OP #8 (stall escalation)
- Audit-r2 patterns memory: `memory/feedback_docs_vs_railway_env_drift.md`
