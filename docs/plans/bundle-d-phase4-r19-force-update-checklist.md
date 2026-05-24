# Phase 4 R19 — force-update env vars sequencing checklist

> Bundle D risk **R19**: "Force-update env vars dangerous —
> `APP_FORCE_UPDATE=true` boots all old-version users."
>
> Control per `BUNDLE_D_RISK_LEDGER.md`: "Sequence: `APP_MIN_VERSION` =
> TestFlight build version FIRST; flip `APP_FORCE_UPDATE=true` only
> AFTER all testers on new build."

## Why this checklist exists

`APP_FORCE_UPDATE=true` is a one-line env-var flip that **immediately
boots every user on a version below `APP_MIN_VERSION`** out of the app
with a force-update screen. If `APP_MIN_VERSION` is wrong (e.g. set
higher than what testers actually have installed), every tester is
locked out at once — TestFlight rollback is slow.

This checklist sequences the env vars so the dangerous flip happens
LAST, only after the safe-by-default state is confirmed live.

---

## Stage 0 — Baseline grep (3 min)

```bash
cd <repo-root>

# Endpoint that the mobile app polls
grep -n "@router\|APP_MIN_VERSION\|APP_LATEST_VERSION\|APP_FORCE_UPDATE" \
  app/api/version_routes.py
# Expected (current main):
#   line 11: os.getenv("APP_MIN_VERSION", "1.0.0")
#   line 12: os.getenv("APP_LATEST_VERSION", "1.0.0")
#   line 13: os.getenv("APP_FORCE_UPDATE", "false").lower() == "true"
#   line 19: @router.get("/version")

# Mobile-side consumer (frontend lane should have this wired)
grep -rn "force_update\|min_version\|latest_version" SmartCompareApp/src/
# Expected: at least one component reading the response shape
```

If any of these are missing → STOP and flag dispatcher; the wiring
isn't in place yet.

---

## Stage 1 — Confirm TestFlight build version (~3 min)

The Phase 3 EAS production build (`Task 3.N.1`) sets a concrete
`expo.version` in `SmartCompareApp/app.json`. Read it before setting any
Railway env var.

```bash
grep -A 2 '"version":' SmartCompareApp/app.json | head -5
# Expected: "version": "1.0.0" (or whatever Phase 3 settles on)
```

**Lock that exact string in a scratch var** — every subsequent step
references it. Mismatch = lockout risk.

```bash
TF_VERSION="1.0.0"  # COPY FROM app.json — do not eyeball
```

---

## Stage 2 — Set APP_LATEST_VERSION + APP_MIN_VERSION (~30 sec)

Both vars get the same string. `APP_LATEST_VERSION` is informational
(the app shows "update available" UI when its installed version is
older); `APP_MIN_VERSION` is the lower bound that — combined with
`APP_FORCE_UPDATE=true` — gates app entry.

**Safe-by-default ordering:** set these BEFORE `APP_FORCE_UPDATE` is
flipped to true, so even if the wrong values land, no one is locked out
(force_update still false → app shows soft "update available" UX, not
a lockout screen).

```
mcp__railway__set_variables
  service: <backend service id>
  variables: {
    "APP_LATEST_VERSION": "1.0.0",   # ← replace with TF_VERSION
    "APP_MIN_VERSION":   "1.0.0",    # ← replace with TF_VERSION
    "APP_FORCE_UPDATE":  "false"     # explicit (current default, but lock it)
  }
```

Railway auto-redeploys (~90s).

### Rollback recipe (Stage 2)
```
mcp__railway__set_variables
  service: <backend service id>
  variables: {
    "APP_LATEST_VERSION": "1.0.0",
    "APP_MIN_VERSION":   "0.0.0",    # rolls min back to a no-op floor
    "APP_FORCE_UPDATE":  "false"
  }
```

---

## Stage 3 — Verify via curl that values surface (~30 sec)

```bash
curl -sS https://web-production-58776.up.railway.app/api/v1/app/version | jq
```

**Pass criteria:**
```json
{
  "min_version":   "<TF_VERSION>",
  "latest_version": "<TF_VERSION>",
  "force_update":  false
}
```

`force_update: false` is the load-bearing assertion. If it's `true` here,
Stage 4 is wrong order — STOP and reset Stage 2.

---

## Stage 4 — Wait for "all testers on latest" signal (manual)

This stage has no automation. Dispatcher waits until Ahmed confirms
(via PR comment, message, or out-of-band) that **every tester has
installed the new TestFlight build**.

Useful signals (none authoritative — Ahmed remains the gate):
- TestFlight install count in App Store Connect = invite count.
- Mobile in-app analytics show 100% of MAU on the new version
  (`analytics_service` events with `app_version=<TF_VERSION>`).
- Tester slack/email confirmation.

**Do NOT proceed to Stage 5 without explicit Ahmed ack.** The R19
control text is unambiguous: "only AFTER all testers on new build."

---

## Stage 5 — Flip APP_FORCE_UPDATE=true (~30 sec, IRREVERSIBLE for old-version users)

```
mcp__railway__set_variables
  service: <backend service id>
  variables: {"APP_FORCE_UPDATE": "true"}
```

Railway redeploys ~90s. The mobile app's `/api/v1/app/version` poll
returns `force_update: true` on its next call; clients on
`installed_version < APP_MIN_VERSION` show the force-update screen.

### Immediate post-flip verification

```bash
# Re-curl to confirm
curl -sS https://web-production-58776.up.railway.app/api/v1/app/version | jq
# Expected: force_update: true
```

```
mcp__railway__list_variables
  service: <backend service id>
  # Expected: APP_FORCE_UPDATE=true
```

---

## Rollback recipe (Stage 5 — if a tester somehow falls through and gets locked out)

```
mcp__railway__set_variables
  service: <backend service id>
  variables: {"APP_FORCE_UPDATE": "false"}
```

Railway redeploys ~90s. The blocked tester's NEXT poll returns
`force_update: false` and the app unblocks. No data loss; no app reinstall
needed.

### If a wider rollback is needed (lockout cascade)
```
mcp__railway__set_variables
  service: <backend service id>
  variables: {
    "APP_FORCE_UPDATE": "false",
    "APP_MIN_VERSION":  "0.0.0"  # any installed version satisfies floor
  }
```

---

## Common failure modes + how this sequence avoids them

| Failure mode | What goes wrong | How this checklist prevents it |
|---|---|---|
| `APP_MIN_VERSION` ahead of any installed TestFlight build | Every tester locked out on next /version poll | Stage 1 locks TF_VERSION from `app.json`; Stage 5 only fires after Ahmed confirms all installs |
| `APP_FORCE_UPDATE=true` set before `APP_MIN_VERSION` is set | `MIN_VERSION` defaults to `"1.0.0"` in code; everyone < 1.0.0 is locked out (currently zero users, but the default is a footgun) | Stage 2 explicitly sets MIN+LATEST BEFORE the force flip is even considered |
| Typo in version string (e.g. `1.0.0` vs `1.0.0 ` with trailing space) | Mobile app's version-compare fails open / fails closed depending on impl | Stage 3 curl verifies the exact value the API returns matches expectation |
| Stage 4 "all on latest" assumed without verification | Some testers still on a sideloaded older build get locked out | Stage 4 is an explicit human-in-the-loop gate; Ahmed ack required |

---

## Owner

Dispatcher executes Stages 2+3+5+post-verification.
Backend agent runs Stage 0+1 (greps + version lookup).
Ahmed gates Stage 4 → 5 transition.

Last revised: 2026-05-23.
