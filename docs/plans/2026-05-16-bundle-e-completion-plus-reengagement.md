# Bundle E Completion + Re-engagement Push — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Execute Phase 0 in the parent session, then dispatch the 4-Opus team for Phases 1-4, then return to the parent for Phase 5.

**Goal:** Close out the unfinished half of Bundle E (scatter-gather price pipeline + frontend rebuild) AND wire re-engagement push gating with `flip-and-watch` rollout pre-launch.

**Architecture:** Existing Bundle E design and per-task scaffolding live in `docs/plans/2026-05-13-results-quality-overhaul-design.md` and `docs/plans/2026-05-13-results-quality-overhaul.md`. This plan **does not duplicate** those task definitions — it references them by section and owns only the integration tasks + new re-engagement work. Read both Bundle E docs before starting Phase 1.

**Tech Stack:** Python 3.12 + FastAPI + asyncio + pytest (backend), React Native + Expo SDK 54 + Reanimated + react-native-svg + jest (frontend), Upstash Redis, Supabase Postgres, OpenAI / Serper / Firecrawl / Scrape.do.

**Design doc:** `docs/plans/2026-05-16-bundle-e-completion-plus-reengagement-design.md`

**Team:** 4 Opus agents via TeamCreate (`bypassPermissions`). Per-agent code names: `backend-opus`, `frontend-opus`, `test-opus`, `qa-opus`. Cardinal rules — all Opus, ship 100% complete, cross-QA before disband, 30-min stall → dispatcher absorbs, path-restricted commits.

---

## Phase 0 — Parent session: setup before team dispatch

### Task 0.1: Audit existing Bundle E state in main

**Files:** read-only

**Step 0.1.1:** `grep -rn "fan_out_price_lookup\|should_fan_out" app/` → confirm Tasks 2.2 + 2.4 scaffolding exists.
**Step 0.1.2:** `grep -rn "first_paint\|settle_update\|settle_complete\|confidence_upgrade" app/api/text_routes.py` → confirm SSE event types NOT yet wired (Task 2.5 unfinished).
**Step 0.1.3:** `grep -rn "scoring_v2\|dimensions" app/services/response_builder.py` → confirm scoring V2 contract DID land per Session 47.
**Step 0.1.4:** Record findings in a 3-line PR description for the team.

### Task 0.2: Clean up stale worktrees from prior dispatches

```bash
git worktree list | grep agent- | awk '{print $1}' | xargs -I{} git worktree remove --force {} 2>/dev/null
git worktree prune
git branch | grep worktree-agent- | xargs -I{} git branch -D {} 2>/dev/null
```

Verify: `git worktree list` shows only main + the active `smartcompare-bundle-e` workspace.

### Task 0.3: Create the team worktree

```bash
git worktree add -b feature/bundle-e-complete ../smartcompare-bundle-e-complete main
cd ../smartcompare-bundle-e-complete && git status   # confirm clean
```

### Task 0.4: Dispatch 4-Opus team via TeamCreate

Create the team with 4 members. Task ownership assignments are in the **Team task matrix** section below. Use these dispatch params for every member:

```typescript
TeamCreate({
  name: "bundle-e-completion-team",
  members: [
    { name: "backend-opus", subagent_type: "general-purpose", model: "opus", mode: "bypassPermissions" },
    { name: "frontend-opus", subagent_type: "general-purpose", model: "opus", mode: "bypassPermissions" },
    { name: "test-opus", subagent_type: "general-purpose", model: "opus", mode: "bypassPermissions" },
    { name: "qa-opus", subagent_type: "general-purpose", model: "opus", mode: "bypassPermissions" },
  ],
  worktreeRoot: "../smartcompare-bundle-e-complete",
})
```

Each member's prompt MUST include:
- Link to this plan + the design doc + the canonical 2026-05-13 Bundle E plan
- Cardinal rules from CLAUDE.md "Agent Team Pattern (Session 26+)"
- Path-restricted-commit reminder (`git commit -m "msg" -- <paths>`)
- 30-min silent-stall escalation (parent absorbs if no SendMessage progress)
- TDD discipline
- Specific tasks from the matrix below

---

## Team task matrix

| Phase | Task # | Owner | Cross-QA by | Source of bite-sized steps |
|---|---|---|---|---|
| **1: Backend Bundle E** | 2.1 quality_ranker | backend-opus | test-opus | `docs/plans/2026-05-13-results-quality-overhaul.md` § Task 2.1 |
| | 2.2 fan_out_price_lookup verify | backend-opus | test-opus | same § Task 2.2 — already scaffolded, verify + add tests |
| | 2.3 compare_from_text_streaming → scatter-gather | backend-opus | qa-opus | same § Task 2.3 (the missing integration) |
| | 2.5 new SSE event types | backend-opus | qa-opus | same § Task 2.5 |
| **2: Backend re-engagement** | RE-1 flag-gate evaluate_user | backend-opus | test-opus | NEW — see "Phase 2" below |
| | RE-2 canary helper + Python djb2 bucket | backend-opus | test-opus | NEW — see "Phase 2" below |
| | RE-3 cross-language bucket parity test | test-opus | backend-opus | NEW — see "Phase 2" below |
| **3: Frontend Bundle E** | 3.1-3.8 rings + bars + copy lint + SSE handlers | frontend-opus | qa-opus | `docs/plans/2026-05-13-results-quality-overhaul.md` § Phase 3 (Tasks 3.1-3.8) |
| **4: Cross-QA** | 4.1-4.4 integration + perf + regression + final sign-off | qa-opus | dispatcher | `docs/plans/2026-05-13-results-quality-overhaul.md` § Phase 4 + new perf criteria in design doc |

---

## Phase 2 — NEW backend tasks (re-engagement)

### Task RE-1: Flag-gate `evaluate_user()`

**Files:**
- Modify: `app/services/reengagement_service.py`
- Test: `tests/test_reengagement_service.py` (extend)

**Step RE-1.1: Write the failing test**

Append to `tests/test_reengagement_service.py`:

```python
@pytest.mark.asyncio
async def test_evaluate_user_returns_empty_when_flag_off(monkeypatch):
    monkeypatch.delenv("ENABLE_REENGAGEMENT_PUSHES", raising=False)
    from app.services.reengagement_service import evaluate_user
    result = await evaluate_user(user_id="...", db=fake_db_with_eligible_user())
    assert result == [], "flag off must produce zero push payloads"

@pytest.mark.asyncio
async def test_evaluate_user_runs_when_flag_on(monkeypatch):
    monkeypatch.setenv("ENABLE_REENGAGEMENT_PUSHES", "true")
    from app.services.reengagement_service import evaluate_user
    result = await evaluate_user(user_id="...", db=fake_db_with_eligible_user())
    assert len(result) > 0, "flag on + eligible user must produce at least one payload"
```

**Step RE-1.2: Run test, verify it FAILS**

```bash
python -m pytest tests/test_reengagement_service.py -v -k "flag_off or flag_on" --timeout=30
```
Expected: FAIL (flag not checked yet).

**Step RE-1.3: Implement flag gate**

At the top of `evaluate_user()` in `app/services/reengagement_service.py`:

```python
import os
if os.getenv("ENABLE_REENGAGEMENT_PUSHES", "").lower() not in ("true", "1", "yes"):
    return []
```

**Step RE-1.4: Run test, verify it PASSES**

```bash
python -m pytest tests/test_reengagement_service.py -v -k "flag_off or flag_on" --timeout=30
```

**Step RE-1.5: Mirror the gate in the cron**

`scripts/cron_reengagement.py` — at top of main loop:
```python
if os.getenv("ENABLE_REENGAGEMENT_PUSHES", "").lower() not in ("true", "1", "yes"):
    logger.info("ENABLE_REENGAGEMENT_PUSHES not set — skipping reengagement run")
    return
```

**Step RE-1.6: Commit (path-restricted)**

```bash
git add app/services/reengagement_service.py scripts/cron_reengagement.py tests/test_reengagement_service.py
git commit -m "feat(reengagement): gate by ENABLE_REENGAGEMENT_PUSHES flag" -- app/services/reengagement_service.py scripts/cron_reengagement.py tests/test_reengagement_service.py
```

### Task RE-2: Canary helper + Python djb2 bucket

**Files:**
- Create: `app/utils/feature_bucket.py`
- Modify: `app/services/reengagement_service.py`
- Test: `tests/test_feature_bucket.py`

**Step RE-2.1: Read the frontend implementation**

```bash
cat SmartCompareApp/src/services/featureBucket.ts
```
Note: it MUST be a djb2 hash (per CLAUDE.md "Bucketing (`featureBucket.ts` + App.tsx): djb2 hash on stable id"). Read the exact implementation — Python port must match byte-for-byte on identical inputs.

**Step RE-2.2: Write failing tests**

`tests/test_feature_bucket.py`:

```python
import pytest
from app.utils.feature_bucket import hash_bucket

# Known inputs from frontend featureBucket.ts spec test fixtures.
@pytest.mark.parametrize("user_id,percent,expected", [
    # (user_id, percent, expected_in_bucket) — filled in from frontend test fixtures
])
def test_hash_bucket_matches_frontend(user_id, percent, expected):
    assert hash_bucket(user_id, percent) == expected

def test_monotonic_ramp():
    """If percent grows, in-bucket users only grow (never shrink)."""
    ids = [f"user-{i}" for i in range(1000)]
    in_10 = {u for u in ids if hash_bucket(u, 10)}
    in_50 = {u for u in ids if hash_bucket(u, 50)}
    in_100 = {u for u in ids if hash_bucket(u, 100)}
    assert in_10 <= in_50 <= in_100
```

**Step RE-2.3: Verify it FAILS**

```bash
python -m pytest tests/test_feature_bucket.py -v
```

**Step RE-2.4: Implement `app/utils/feature_bucket.py`**

```python
def _djb2(s: str) -> int:
    h = 5381
    for c in s:
        h = ((h * 33) ^ ord(c)) & 0xFFFFFFFF
    return h

def hash_bucket(stable_id: str, percent: int) -> bool:
    if percent <= 0:
        return False
    if percent >= 100:
        return True
    return (_djb2(stable_id) % 100) < percent
```

**Step RE-2.5: Verify GREEN**

```bash
python -m pytest tests/test_feature_bucket.py -v
```

**Step RE-2.6: Wire into reengagement_service**

In `evaluate_user()` after the flag gate:
```python
canary_pct = int(os.getenv("REENGAGEMENT_CANARY_PERCENT", "100"))
if not hash_bucket(str(user_id), canary_pct):
    return []
```

**Step RE-2.7: Add canary test**

```python
@pytest.mark.asyncio
async def test_canary_zero_percent_blocks_all(monkeypatch):
    monkeypatch.setenv("ENABLE_REENGAGEMENT_PUSHES", "true")
    monkeypatch.setenv("REENGAGEMENT_CANARY_PERCENT", "0")
    from app.services.reengagement_service import evaluate_user
    result = await evaluate_user(user_id="user-1", db=fake_db_with_eligible_user())
    assert result == []
```

**Step RE-2.8: Verify all reengagement tests PASS**

```bash
python -m pytest tests/test_reengagement_service.py tests/test_feature_bucket.py -v
```

**Step RE-2.9: Commit (path-restricted)**

```bash
git add app/utils/feature_bucket.py app/services/reengagement_service.py tests/test_feature_bucket.py tests/test_reengagement_service.py
git commit -m "feat(reengagement): add canary helper (Python djb2 mirror of featureBucket.ts)" -- app/utils/feature_bucket.py app/services/reengagement_service.py tests/test_feature_bucket.py tests/test_reengagement_service.py
```

### Task RE-3: Cross-language bucket parity test (owned by test-opus)

**Goal:** Verify Python `hash_bucket()` and TypeScript `hashBucket()` produce identical assignments for the same `(stable_id, percent)` pairs.

**Step RE-3.1:** Generate a fixture file `tests/fixtures/featurebucket_parity.json` listing 100 random `(stable_id, percent)` pairs + the TypeScript result for each (run via a one-off node script).

**Step RE-3.2:** Write `tests/test_feature_bucket_parity.py` that loads the fixture and asserts Python output matches TS output for every pair.

**Step RE-3.3:** Verify the test passes. If any disagreement, fix the Python implementation until parity holds.

---

## Phase 5 — Parent session: integration + deploy

### Task 5.1: Pull team's branches back

```bash
cd ../smartcompare-bundle-e-complete
git log --oneline main..feature/bundle-e-complete | head -30
```
Confirm all team commits are present.

### Task 5.2: Run full regression suite

```bash
python -m pytest tests/ -m "not (live_unit or live_db or integration)" --ignore=tests/test_integration.py -x --timeout=60
cd SmartCompareApp && npx tsc --noEmit && npm test
```
Both must pass clean before merging.

### Task 5.3: Open PR for cross-review

```bash
gh pr create --title "Bundle E completion + re-engagement push canary infra" --body "$(cat <<'EOF'
## Summary
- Bundle E scatter-gather pricing pipeline + frontend rings/bars/copy
- Re-engagement push flag gate + Python canary helper (djb2 parity with frontend)

## Test plan
- [x] backend pytest passes (no new failures)
- [x] frontend tsc clean + jest passes
- [x] perf bench: cold-cache <15s p95 non-luxury, <25s p95 luxury
- [ ] manual: 4-category comparison (electronics/grocery/supplements/fashion) on Railway preview
- [ ] manual: flip ENABLE_REENGAGEMENT_PUSHES=true in Railway preview, verify Sentry quiet for 30 min

Design: docs/plans/2026-05-16-bundle-e-completion-plus-reengagement-design.md
Implementation: docs/plans/2026-05-16-bundle-e-completion-plus-reengagement.md
EOF
)"
```

### Task 5.4: Railway preview validation

After PR approval + merge to main:
1. Wait for Railway auto-deploy (~90s)
2. Run cold-cache comparison: `curl ".../api/v1/text/compare?q=...&nocache=true"`
3. Verify response time + scoring shape
4. Check Sentry — no new issues
5. If all green, flip `ENABLE_REENGAGEMENT_PUSHES=true` on Railway
6. Watch Sentry + push-receipt errors for 30 min before considering rollout complete

### Task 5.5: EAS Update for frontend bundle

After Railway is green:
```bash
cd SmartCompareApp && eas update --branch preview --message "Bundle E complete: rings + bars + scatter-gather"
```
(User runs this — interactive auth.)

### Task 5.6: Update CLAUDE.md + memory

- Mark Bundle F priority done (`SCRAPING_MODE=soft` is now superseded by Task 2.3)
- Note re-engagement is live
- Update Session log in `docs/CONTEXT_SESSION_LOG.md`

---

## Done criteria

- [ ] All team tasks complete; qa-opus signs off
- [ ] Full regression suite passes
- [ ] Performance success criteria from design doc § Success criteria met
- [ ] PR merged to main
- [ ] EAS update pushed to preview channel
- [ ] Re-engagement flag flipped on Railway, Sentry watched for 30 min
- [ ] Stale agent worktrees cleaned up
