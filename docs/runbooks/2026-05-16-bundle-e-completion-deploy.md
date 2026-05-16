# Bundle E Completion + Re-engagement — Deploy Runbook

**Trigger:** After the `bundle-e-completion` 4-Opus team finishes and the `feature/bundle-e-complete` branch is merged to `main`.
**Plan reference:** `docs/plans/2026-05-16-bundle-e-completion-plus-reengagement.md` § Phase 5.
**Important:** Bundle E completion includes the **Sentry React Native SDK** (`@sentry/react-native` added to `app.json` plugins + native module). This means **a rebuild is required** for the Sentry SDK to activate on existing devices — OTA alone is not enough. Bundle E's frontend/JS-only pieces (rings, dimension bars, copy, SSE handlers) WILL ship via OTA.

Plan: ship JS via OTA first (testers see the new UI immediately), then trigger a rebuild in parallel so Sentry activates on the next install.

---

## Step 0 — Preconditions (do all of these before any deploy command)

```bash
cd C:/Users/SynAckITPC/Documents/AI/smartcompare

# Confirm we're on main and clean
git status --short    # should be clean (no M, no ??)
git rev-parse --abbrev-ref HEAD    # should print "main"

# Confirm the team branch is merged
git log --oneline main | head -10    # should show the Bundle E team's commits

# Backend health
curl -s https://web-production-58776.up.railway.app/health    # should return 200 {"status":"healthy"}

# Latest Sentry issues — should be empty or pre-existing only
# (run via Sentry MCP from Claude Code, or visit https://qaren-rr.sentry.io/issues/)
```

If any precondition fails, stop and fix before deploying.

---

## Step 1 — Ship JS-only changes via EAS Update (preview channel)

`cd SmartCompareApp` first — `eas update` resolves from the project's `eas.json` and `app.json`.

```bash
cd C:/Users/SynAckITPC/Documents/AI/smartcompare/SmartCompareApp
eas update --branch preview --message "Bundle E completion: scatter-gather pricing + radial rings + dimension bars + per-product value_context"
```

Expected output: a new EAS Update group ID + iOS/Android platform updates listed. Phones on the `preview` channel pick up the new JS bundle on next app cold-start.

Record the new group ID — it replaces `d540c1e6-c07c-46d7-ac69-5103dde1fb56` in CLAUDE.md's "Bundle history" section. Update CLAUDE.md after deploy.

**What this ships:**
- Scatter-gather price pipeline (backend already deployed via Railway when main was merged)
- Radial-ring hero card + dimension bars on Results screen
- New SSE event handlers (`first_paint`, `settle_update`, `settle_complete`, `confidence_upgrade`)
- Per-product `value_context` (backend already deployed; frontend already reads per-product per types.ts)
- Re-engagement push gating (backend already deployed — flag still OFF on Railway)

**What this does NOT ship (requires rebuild — see Step 3):**
- `@sentry/react-native` SDK — installed but not yet bundled into the native binary
- Any future native-module changes

---

## Step 2 — Smoke test from a tester device

Have at least one tester (or yourself) on the `preview` channel:
1. Force-quit the app
2. Cold-start — Expo client fetches the new JS bundle
3. Run a comparison (e.g., "iPhone 15 vs Galaxy S24")
4. Verify on Results screen:
   - Radial ring hero card appears with two scoring rings
   - Dimension bars render below with confidence color coding
   - "Why we picked this" / "Where the runner-up wins" / "What's next?" copy renders
   - No banned vocabulary visible ("couldn't", "try again", "Failed to", "تعذر", "فشل")
5. Try Arabic mode — same checks
6. Try a luxury query ("Gucci Marmont vs Prada Galleria") — Tier 1.5 still hits Firecrawl, prices render

If anything is broken, see Step 5 (Rollback).

---

## Step 3 — Trigger a rebuild to activate Sentry RN (interactive)

Sentry RN needs to be in the native binary, so a fresh `eas build` is required. **You run this — it needs an interactive terminal for Apple/Google credentials:**

```bash
cd C:/Users/SynAckITPC/Documents/AI/smartcompare/SmartCompareApp

# Android first (faster; no Apple Developer dependency)
eas build --profile preview --platform android

# iOS — only if Apple Developer subscription is active
eas build --profile preview --platform ios
```

Each takes 10-20 minutes on the EAS build cluster. After completion:
- Android: download the .apk from EAS dashboard, sideload onto tester devices (or distribute via Internal App Sharing)
- iOS: upload to TestFlight via EAS or transfer to App Store Connect

**iOS may be blocked** until the Apple Developer subscription is renewed/active. The `preview` profile doesn't push to App Store, but iOS code signing still requires a paid Apple Developer account. If blocked, skip iOS for now — Android testers get Sentry coverage; iOS waits.

---

## Step 4 — Flip the re-engagement push flag (after Step 2 smoke is green)

Per the team's RE-1/RE-2 work, the cron + service are gated by `ENABLE_REENGAGEMENT_PUSHES` (off by default).

```bash
cd C:/Users/SynAckITPC/Documents/AI/smartcompare    # back to repo root for railway CLI
railway variables --set ENABLE_REENGAGEMENT_PUSHES=true
# Railway auto-redeploys (~90s)
```

Watch Sentry for 30 minutes after the flip. If any spike in push-receipt errors or backend exceptions touching `reengagement_service` or `push_service`, flip back to `false`:

```bash
railway variables --set ENABLE_REENGAGEMENT_PUSHES=false
```

Per the design doc § G-1, **no canary % needed pre-launch** (<10 testers; statistically meaningless). The `REENGAGEMENT_CANARY_PERCENT` infra is wired (default 100) for post-launch ramp.

---

## Step 5 — Rollback procedure

### If Step 2 smoke fails (broken JS)

Revert the EAS Update — phones go back to the previous bundle on next cold-start:
```bash
cd SmartCompareApp
eas update:list --branch preview     # find the previous group ID
eas update:republish --branch preview --group <PREVIOUS_GROUP_ID> --message "Revert: Bundle E smoke test failed"
```

### If backend regression appears

Revert main and force-redeploy:
```bash
cd C:/Users/SynAckITPC/Documents/AI/smartcompare
git revert <MERGE_COMMIT_OF_BUNDLE_E>    # creates a new revert commit
git push origin main                      # Railway auto-deploys revert in ~90s
```

### If Step 3 rebuild fails

The OTA from Step 1 already shipped — no action needed for testers. Investigate the build error, fix, retry `eas build`.

### If Step 4 (re-engagement flag) causes Sentry spike

Flip flag back to false immediately (above). No code change needed — fail-CLOSED by design.

---

## Step 6 — Update CLAUDE.md after successful deploy

In `CLAUDE.md`, find the "Bundle history (sessions 44-47)" breadcrumb and update:
- "Bundle E EAS group `d540c1e6-...`" → new group ID from Step 1
- Bundle F priority is **DONE** (`SCRAPING_MODE=soft` superseded by scatter-gather refactor — remove that breadcrumb or note it as done)
- Add "Session 48 (2026-05-16): Bundle E completion + re-engagement gating shipped"

Commit:
```bash
git add CLAUDE.md
git commit -m "docs(claude.md): Session 48 — Bundle E completion + re-engagement live"
git push origin main
```

---

## Open follow-ups after this deploy

1. **Sourcemap upload** for Sentry RN — deferred from Session 48 (needs `SENTRY_AUTH_TOKEN` in EAS env + plugin config form `["@sentry/react-native", {url, organization, project}]`)
2. **EAS env secret for SENTRY_DSN** — currently hard-coded fallback in `sentry.ts` (write-only key, safe to commit but cleaner via env)
3. **iOS rebuild** — blocked on Apple Developer subscription
4. **App Store soft-launch prep (B)** — 15 legal decisions outstanding per `docs/plans/2026-05-16-tos-decisions-pending.md`
5. **Bundle E EAS group ID update** in CLAUDE.md (do this AFTER Step 1 completes and you have the new group ID)
