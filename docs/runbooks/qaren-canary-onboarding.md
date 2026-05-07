# Qaren UX Redesign — Canary Rollout Runbook

**Owner:** backend (canary mechanic) + test-qa (metrics)
**Scope:** ramp `ENABLE_NEW_ONBOARDING` from 10% → 50% → 100% over 7-10 days.
**Last revised:** 2026-05-07.

This runbook is the single source of truth for the Phase 5 onboarding
canary. Task 47 (10%) landed — see commit history. Task 48 covers the
50% and 100% ramps; this document is the spec the on-call (Ahmed or
delegate) follows when each window opens.

---

## 1. Pre-flight metrics — gates between ramps

Each ramp step (10→50, 50→100) only proceeds when ALL of the following
are green for the prior window. Any RED gate → stop, investigate, or
rollback.

### 1.1 Crash-free sessions

| Source | Threshold | Notes |
|---|---|---|
| Sentry — new-flow users (`flow_variant=new`) | ≥ 99.5% crash-free | Compare AGAINST `flow_variant=legacy` cohort. |
| Sentry — net delta vs. legacy | ≤ +0.3% absolute regression | Small regressions can be canary noise; >0.3% means new flow is materially worse. |

Query (Sentry → Discover):
```
event.type:error environment:production tags[flow_variant]:new
```
Compare to identical query with `flow_variant:legacy`.

### 1.2 Onboarding completion rate

| Metric | Target |
|---|---|
| Started → Completed (new flow) | ≥ 75% |
| Started → Completed (delta vs. legacy) | ≤ -5% absolute |

SQL (Supabase SQL Editor — `user_events` table):
```sql
WITH starts AS (
  SELECT user_id, MIN(created_at) AS started_at
  FROM user_events
  WHERE event_type = 'onboarding_started'
    AND event_data->>'flow_variant' = 'new'
    AND created_at >= now() - interval '48 hours'
  GROUP BY user_id
),
completes AS (
  SELECT user_id, MIN(created_at) AS completed_at
  FROM user_events
  WHERE event_type = 'onboarding_completed'
    AND event_data->>'flow_variant' = 'new'
    AND created_at >= now() - interval '48 hours'
  GROUP BY user_id
)
SELECT
  COUNT(starts.user_id) AS starts,
  COUNT(completes.user_id) AS completes,
  ROUND(100.0 * COUNT(completes.user_id) / NULLIF(COUNT(starts.user_id), 0), 1)
    AS completion_pct
FROM starts
LEFT JOIN completes USING (user_id);
```

Run twice — once with `flow_variant = 'new'`, once with `'legacy'`.

### 1.3 Drop-off heatmap per step

Any single step with ≥ 40% drop-off needs investigation before
ramping further. The 17 steps are numbered in
`SmartCompareApp/src/screens/onboarding/types.ts`.

```sql
SELECT
  (event_data->>'step_number')::int AS step,
  COUNT(DISTINCT user_id) AS users_completed_step
FROM user_events
WHERE event_type = 'onboarding_step_completed'
  AND event_data->>'flow_variant' = 'new'
  AND created_at >= now() - interval '48 hours'
GROUP BY step
ORDER BY step;
```

Compute per-step drop = (users_completed_step[N] - users_completed_step[N+1]) / users_completed_step[N].

### 1.4 First-comparison conversion (sign-up → compare)

| Metric | Target |
|---|---|
| Signed up → completed first comparison within 24h | ≥ 85% |
| Median time-to-first-compare (sign-up → compare) | ≤ 4 minutes |

```sql
SELECT
  COUNT(DISTINCT u.id) AS signups,
  COUNT(DISTINCT c.user_id) AS first_comparers,
  ROUND(100.0 * COUNT(DISTINCT c.user_id) / NULLIF(COUNT(DISTINCT u.id), 0), 1) AS conversion_pct
FROM users u
LEFT JOIN comparisons c ON c.user_id = u.id
  AND c.created_at <= u.created_at + interval '24 hours'
WHERE u.created_at >= now() - interval '48 hours'
  -- Filter to canary cohort if attribution column populated:
  AND (u.attribution_source IS NOT NULL OR u.created_at >= '<canary_start_ts>');
```

### 1.5 Loop 2 referral path

If `ENABLE_REFERRAL_SYSTEM=true` is co-launched with new onboarding,
also verify (per design 4e):

| Metric | Target |
|---|---|
| Loop 1 share-tap rate (% of comparison sessions that share) | ≥ 15% |
| Loop 2 trigger rate (invitee first compare → referrer credit) | ≥ 35% |
| Bonus claim rate (% of bonus credits used before 3-day expiry) | ≥ 60% |

Admin dashboards already expose these — see CLAUDE.md
"Smart Decision Referrals" section, links:
- `/admin/referrals.html` (X-Admin-Key required)
- `/admin/costs.html`

---

## 2. EAS Update procedure — bumping `CANARY_NEW_ONBOARDING_PERCENT`

The flag is a frontend build-time const. Ramping does NOT require an
app-store re-release. EAS Update pushes a new JS bundle to existing
installed app versions.

### 2.1 Bump 10 → 50

```bash
cd SmartCompareApp

# 1. Update the const
# Edit SmartCompareApp/src/config/features.ts:
#   export const CANARY_NEW_ONBOARDING_PERCENT = 50;

# 2. Run pre-flight checks
npx tsc --noEmit
npx jest --testPathPattern='config/(features|featureBucket)\.test\.ts'

# 3. Commit (path-restricted)
git commit -m "chore(canary): bump ENABLE_NEW_ONBOARDING to 50%" \
  -- SmartCompareApp/src/config/features.ts

# 4. Push to main (Railway auto-deploys backend; frontend is EAS Update)
git push origin main

# 5. Push EAS Update — frontend bundle to live users
eas update --branch production \
  --message "Canary onboarding ramp 10% → 50%"

# 6. Verify update is live
eas update:list --branch production --limit 5
```

Wait 72 hours post-update before evaluating Section 1 metrics for the
50→100 decision.

### 2.2 Bump 50 → 100

Same procedure with `CANARY_NEW_ONBOARDING_PERCENT = 100`. Commit
message: `chore(canary): bump ENABLE_NEW_ONBOARDING to 100%`.

After 7 days at 100% with green metrics, proceed to legacy-removal
cleanup (Section 6).

---

## 3. Rollback procedure

Any RED gate in Section 1, OR a P0 user-facing regression report, OR
a Sentry crash spike → rollback within 1 hour.

### 3.1 Immediate rollback (set percent to 0)

```bash
cd SmartCompareApp

# Edit features.ts: CANARY_NEW_ONBOARDING_PERCENT = 0
git commit -m "revert(canary): rollback ENABLE_NEW_ONBOARDING to 0% (incident: <reason>)" \
  -- SmartCompareApp/src/config/features.ts

git push origin main

eas update --branch production \
  --message "ROLLBACK — canary onboarding to 0%"

# Verify users on the new flow flip back to legacy on next app open
eas update:list --branch production --limit 5
```

Users already mid-onboarding on the new flow will FINISH on the new
flow (orchestrator step state persists in AsyncStorage). New starts
go to the legacy 6-step flow. This is intentional — we don't want to
strand users mid-flow with a different UI on next launch.

### 3.2 Investigation checklist post-rollback

1. Snapshot Sentry incident timeline + error fingerprints
2. Snapshot the SQL queries from Section 1 at rollback timestamp
3. Capture user reports / App Store reviews for the rollback window
4. File a TaskCreate with `incident:canary-onboarding` label, reference
   the rollback commit
5. Decide: fix-and-retry (next ramp window 7+ days later), reduce
   scope (e.g. ramp to 25% instead of 50%), or abandon (revert App.tsx
   to legacy-only path)

---

## 4. Monitoring dashboards — what to watch during each ramp window

| Dashboard | URL / Path | What to look for |
|---|---|---|
| Sentry — Crashes | `sentry.io/organizations/<org>/issues/?project=qaren-mobile` | New issue spikes after EAS Update timestamp; group by `flow_variant` tag |
| Supabase — Onboarding analytics | SQL Editor + queries from Section 1 | Step-by-step drop-off, completion rate delta |
| Admin referral metrics | `/admin/referrals.html` (admin key) | Loop 1/2 trigger rates, abuse flags |
| Admin cost dashboard | `/admin/costs.html` (admin key) | OpenAI/Serper spike from new-flow users (should be near-zero — onboarding doesn't hit those APIs) |
| Railway logs | Railway dashboard → app → Logs | 5xx rate, p95 latency on `/api/v1/auth/*` (signup/preferences/demographics endpoints) |
| App Store / Play Console reviews | Both stores' review tabs | New 1-2 star reviews mentioning "onboarding", "stuck", "can't start" |

Set Sentry alert: **>10 errors/min sustained over 5 min on
`flow_variant:new`** → Slack ping. (Check existing Sentry alerts —
may already be configured at org level.)

---

## 5. Decision tree — what to do when metrics shift

```
                  Metrics review at end of window
                            │
         ┌──────────────────┼──────────────────┐
         │                  │                  │
   ALL GREEN          1-2 amber           1+ RED gate
         │                  │                  │
   Ramp to next       Investigate      ROLLBACK (Section 3)
   percent (Sec 2)         │                  │
                           │            Post-mortem +
                  ┌────────┼────────┐   incident task
                  │        │        │
                Step 14    Loop 2   Crash
                drop-off   conv     spike
                  │        │        │
                Investigate Investigate Investigate
                  │        │        │
              Decide:    Decide:   Decide:
              fix and    backend   rollback
              re-ramp    issue?    immediately
              OR hold    Frontend? if >0.3%
              at current Both?
              percent
```

Specific scenarios:

- **Step 14 (theatrical loading) drop-off ≥ 40%:** the 3.2s minimum
  display floor may feel too long. Inspect Sentry for any error during
  the loading phase. If clean, hold the ramp and consider reducing
  the floor to 2.5s (separate task, not a canary blocker).
- **Step 16 (sign-in) drop-off ≥ 50%:** force-sign-in vs. previous
  skip-allowed flow. Expected to be higher than legacy. If the
  drop-off is materially worse than the legacy "Account" step,
  investigate sign-in provider success rates (Apple/Google/email).
- **Loop 2 trigger rate < 35% but everything else green:** likely a
  share-cap or invite-link routing issue in the referral system flag,
  not the onboarding canary. Section 5.1 below.

### 5.1 Coordinating backend feature flags

Three independent backend env-var flags can be flipped during canary
WITHOUT redeploying frontend:

| Flag | Mechanism | Default | Flip via |
|---|---|---|---|
| `ENABLE_REFERRAL_SYSTEM` | Railway env var | OFF | Railway dashboard → app → Variables → set `true` |
| `ENABLE_BONUS_EXPIRY_PUSHES` | Railway env var | OFF | Same as above |
| `ENABLE_COHORT_PERSONALIZATION` | Railway env var | ON in Railway since 2026-05-05 | Same — keep ON unless cohort priors break |

Backend flags propagate to live workers within ~30s of save (Railway
restarts the worker on env-var change). Confirm propagation by
hitting `/api/v1/referrals/status` (returns 503 when
`ENABLE_REFERRAL_SYSTEM` is OFF, 200 when ON).

**Recommended sequence for full Phase 4 + Phase 5 launch:**

1. New onboarding canary 10% live (Task 47 — done)
2. Backend `ENABLE_REFERRAL_SYSTEM=true` (Railway flip; backend gates
   already in place)
3. Frontend ramp 10 → 50 (Section 2.1) — co-monitor Loop 2 trigger rate
4. Backend `ENABLE_BONUS_EXPIRY_PUSHES=true` (Railway flip; sets up
   the daily cron to start firing 24h reminder pushes)
5. Frontend ramp 50 → 100 (Section 2.2)
6. Hold 7 days → cleanup (Section 6)

---

## 6. Cleanup — after 7 days at 100%

When metrics have been green at `CANARY_NEW_ONBOARDING_PERCENT = 100`
for 7 consecutive days:

```bash
# 1. Remove the legacy OnboardingScreen import + ternary in App.tsx
# (NewOnboardingHost becomes the unconditional onboarding entry)

# 2. Remove the canary const + bucket lookup in features.ts (or set
#    ENABLE_NEW_ONBOARDING to a hard-coded `true` and add a // TODO
#    to fully remove next major release).

# 3. Remove the legacy `flow_variant=legacy` analytics mirror (Task #60)
#    once we've confirmed no remaining users are on legacy after 14 days

# 4. Update CLAUDE.md
#    - Remove "Phase 5 canary" notes
#    - Update onboarding architecture section to reference the new flow only
#    - Update MEMORY.md with the canary outcome (completion rate delta,
#      any incidents, lessons learned)

# 5. Update docs/CONTEXT_SESSION_LOG.md with the canary timeline
#    (start ts, ramp ts, completion ts, peak metrics)

# 6. Path-restricted commit per cleanup chunk
git commit -m "cleanup(canary): remove legacy onboarding path post-100%-rollout" \
  -- SmartCompareApp/App.tsx \
     SmartCompareApp/src/config/features.ts \
     SmartCompareApp/src/screens/OnboardingScreen.tsx \
     CLAUDE.md MEMORY.md docs/CONTEXT_SESSION_LOG.md
```

---

## 7. Open question — physical-device push verification

Task 42 deferred physical-device push notification verification to a
"Phase 5 device session." Loop 2 push (`send_loop2_push`) and the new
24h reminder push (`scripts/cron_expire_bonuses.py`) only fire after
real users complete real flows on real devices. The canary IS the
verification window — first Loop 2 fire on the canary cohort either
delivers a push (verified) or it doesn't (incident).

Physical-device verification ahead of canary is best-effort:

1. Sender side: install dev build on physical iPhone + Android
2. Sender shares from Results → invitee link
3. Open invitee link on a SECOND physical device → register fresh user
4. Invitee runs first comparison
5. Sender device should receive Loop 2 push within 30s
6. Verify push title/body match the gift-framing copy from
   `_loop2_copy()` (`"Your friend just compared something"` / Arabic
   equivalent)

Skip this if device access isn't available. Flag any push failures
during canary as a P0 — incident task and rollback if not fixable
within 4 hours.

---

## 8. Quick reference — key files + commands

| Concern | File / Command |
|---|---|
| Canary percent constant | `SmartCompareApp/src/config/features.ts` line ~30 |
| Bucket helper | `SmartCompareApp/src/config/featureBucket.ts` |
| EAS Update | `cd SmartCompareApp && eas update --branch production --message "..."` |
| Rollback to 0 | Same as ramp; commit + push EAS Update |
| Backend flag flip | Railway dashboard → Variables → save |
| Onboarding events | `event_type` in `('onboarding_started','onboarding_step_completed','onboarding_completed')` |
| Sentry filter | `tags[flow_variant]:new` |
| Loop 2 trigger | `app/services/referral_service.py::try_trigger_loop2` |
| Cron entrypoint | `scripts/cron_expire_bonuses.py` (gated by `ENABLE_BONUS_EXPIRY_PUSHES`) |
