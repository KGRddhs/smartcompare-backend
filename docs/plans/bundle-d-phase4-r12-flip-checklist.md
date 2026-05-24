# Phase 4 R12 — reengagement-flag-flip checklist

> Bundle D risk **R12**: "Reengagement flag flip ON during TestFlight may
> spam testers if cron has bug." Dispatcher action — flip
> `ENABLE_REENGAGEMENT_PUSHES=true` in Railway.
>
> Control per `BUNDLE_D_RISK_LEDGER.md`: "Backend confirms cron stable +
> payload-safe BEFORE flipping; Phase 4 dispatcher action only after
> Ahmed acknowledges."

## Why this checklist exists

Pre-stages every verification step + every rollback recipe so dispatcher
can execute the flip in **one bounded session** (10–15 min) without
hunting for queries or commands. Builds Ahmed-ack signal into the
sequence, not as an afterthought.

---

## Stage 0 — Baseline grep (5 min)

Confirm the runtime gate is still wired the way the checklist assumes.
If any of these greps return zero, **STOP** and re-spec the flip.

```bash
# Cron entrypoint exists
ls -la scripts/cron_reengagement.py

# Service-side kill-switch still gates evaluate()
grep -n "_flag_on" app/services/reengagement_service.py
# Expected: line 32 def, line 95 check at top of evaluate()

# Env var name unchanged
grep -n "ENABLE_REENGAGEMENT_PUSHES" app/services/reengagement_service.py
# Expected: line 39 inside _flag_on() reading os.getenv()

# Cron payload-shape contract
grep -n "send_reengagement_push\|re_engagement_events" \
  app/services/{reengagement_service,push_service}.py
# Expected: cron writes a re_engagement_events row before dispatching Expo Push
```

---

## Stage 1 — "Cron stable" verification (~5 min)

**Definition:** the last 7 calendar days of `cron_reengagement.py`
invocations in Railway logs exit cleanly (no uncaught exception, no
process-level error), AND the per-run summary log line at
`cron_reengagement.py:154` appears every day.

### Railway log query (via Railway MCP — re-auth first if needed)

```
mcp__railway__get_logs
  service: <backend service id>
  query: '"[cron_reengagement]" AND ("evaluated" OR "ERROR")'
  since: 7d
  limit: 100
```

### Pass criteria
- ✅ At least 7 distinct daily summary lines like
  `[cron_reengagement] evaluated=N pushes_dispatched=M skipped=K`.
- ✅ Zero `ERROR`-level lines from `[cron_reengagement]` prefix in last 7d.
- ✅ No `dispatch failed for <user_id>` warnings that escalated into
  exception-level errors (warnings are tolerable — push provider hiccups
  are normal; cron-level crashes are not).

### Fail criteria → STOP
- Any `Traceback` line attributed to `cron_reengagement.py`.
- Days missing the summary line (cron didn't fire).
- > 5% of evaluated users producing `evaluate failed for <id>` warnings.

### Why this gate
The cron has `_flag_on()=False` today so it short-circuits at
`reengagement_service.py:95` after fetching eligible users. We're
verifying the eligible-user fetch + the iteration loop are healthy
BEFORE flipping the gate; the actual `evaluate()` body has been
exercised by unit tests but not at scale.

---

## Stage 2 — "Payload-safe" verification (~5 min)

**Definition:** dry-run `evaluate()` against the last 10 eligible users
produces only the 3 expected detector types
(`decision_insight` / `cohort_curiosity` / `decision_retrospective`)
with no untyped events, no missing required fields, no None values in
the deep-link slot.

### Local dry-run with prod data

```bash
cd <repo-root>
python -c "
import asyncio, json
from app.services.database_service import get_admin_supabase_client
from app.services.reengagement_service import ReengagementService

async def dry_run():
    client = get_admin_supabase_client()
    # Pull the 10 most-recently-active users who would be cron-eligible
    users = client.table('users').select(
        'id, preferences, last_comparison_at, notifications_enabled'
    ).eq('notifications_enabled', True).order(
        'last_comparison_at', desc=True
    ).limit(10).execute().data or []
    svc = ReengagementService()
    # IMPORTANT: bypass _flag_on for dry-run — patch it temporarily
    import app.services.reengagement_service as svc_mod
    svc_mod._flag_on = lambda: True
    for u in users:
        result = await svc.evaluate(u)
        print(json.dumps({
            'user_id': u['id'][:8],
            'event_type': result.get('event_type') if result else None,
            'has_title': bool(result and result.get('title')),
            'has_body': bool(result and result.get('body')),
            'has_deep_link': bool(result and result.get('deep_link_url')),
        }))

asyncio.run(dry_run())
"
```

### Pass criteria
- Every row's `event_type` is in `{decision_insight, cohort_curiosity, decision_retrospective, None}`.
  (`None` = legitimate "no detector fired today" outcome — expected for
  most users; design intent is ≤1 push per user per 7 days.)
- Every non-None result has `has_title=True`, `has_body=True`,
  `has_deep_link=True`.
- Zero exception traceback lines in the script output.

### Fail criteria → STOP
- Any `event_type` outside the 3-name whitelist.
- Any non-None result missing title/body/deep_link.
- Script crashes mid-loop (catch + log per-user, but if ALL fail =
  systemic issue).

---

## Stage 3 — Ahmed acknowledgement gate

Post the Stage 1 + Stage 2 evidence as a PR comment on the Bundle D
merge PR, then wait for Ahmed to reply with **"first cron tick safe"**
(or equivalent). This is the human-in-the-loop gate the R12 control
explicitly requires.

### Comment template

```markdown
## R12 Phase 4 pre-flight — cron stable + payload-safe ✅

**Stage 1 (cron stable):**
- 7/7 daily summary lines present in Railway logs (2026-MM-DD to 2026-MM-DD)
- Zero `ERROR`-level lines from `[cron_reengagement]` prefix
- Per-day eligible-user counts: <table>

**Stage 2 (payload-safe):**
- 10 users sampled, all event_types in {decision_insight, cohort_curiosity, decision_retrospective, None}
- All non-None results carry title + body + deep_link
- Dry-run output: <attach gist>

**Ready to flip `ENABLE_REENGAGEMENT_PUSHES=true` on dispatcher ack.**
```

**WAIT** for Ahmed reply before proceeding to Stage 4.

---

## Stage 4 — Flip via Railway MCP (~30 sec)

```
mcp__railway__set_variables
  service: <backend service id>
  variables: {"ENABLE_REENGAGEMENT_PUSHES": "true"}
```

Railway auto-redeploys (~90s). The cron's next scheduled tick
(03:00 UTC per `scripts/cron_reengagement.py:1` design 3.9) will be
the first ENABLED run.

### Immediate post-flip verification

```bash
mcp__railway__list_variables
  service: <backend service id>
  # Expected: ENABLE_REENGAGEMENT_PUSHES=true
```

---

## Stage 5 — 24-hour observation window

After the first cron tick fires (next 03:00 UTC), watch the following
for 24 hours:

### Sentry MCP watch
```
mcp__plugin_sentry_sentry__search_issues
  organizationSlug: qaren-rr
  query: "is:unresolved firstSeen:-24h reengagement"
  limit: 25
```
**Pass:** zero new issue types attributed to `reengagement_service` /
`push_service` / `cron_reengagement`.

### Admin SQL: per-user 7d push count
```sql
SELECT user_id, COUNT(*) AS pushes_last_7d
FROM re_engagement_events
WHERE triggered_at >= now() - interval '7 days'
GROUP BY user_id
HAVING COUNT(*) > 1
LIMIT 50;
```
**Pass:** zero rows. The 7-day per-user cap at
`reengagement_service._recent_push` should prevent any user from
receiving > 1 push in 7d.

### Subscription respect SQL
```sql
SELECT u.id,
  u.preferences->'notification_types' AS subs,
  e.event_type
FROM re_engagement_events e
JOIN users u ON u.id = e.user_id
WHERE e.triggered_at >= now() - interval '24 hours'
LIMIT 50;
```
**Pass:** for every row, the `event_type` corresponds to a sub-toggle
that is NOT explicitly `false` in the user's `notification_types`
(missing key = treated as ON per design).

---

## Rollback recipe (~30 sec)

If ANY of Stage 5 fails or Ahmed reports spam:

```
mcp__railway__set_variables
  service: <backend service id>
  variables: {"ENABLE_REENGAGEMENT_PUSHES": "false"}
```

Cron will short-circuit at `_flag_on()=False` on the very next tick.
No pushes leak; no data fixes needed (re_engagement_events rows from
the bad window stay as audit evidence).

### Then file a post-mortem
- Sentry issue link(s)
- Affected user count from the failure-mode SQL
- Root cause hypothesis
- Re-flip plan with additional gate

---

## Owner

Dispatcher executes Stages 4+5 (Railway MCP + Sentry watch).
Backend agent runs Stages 0-3 (greps + dry-run + PR comment).
Ahmed gates Stage 3 → 4 transition.

Last revised: 2026-05-23.
