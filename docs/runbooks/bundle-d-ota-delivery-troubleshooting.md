# Bundle D — OTA Delivery Troubleshooting Runbook

**Author:** native-ops
**Date drafted:** 2026-05-25
**Trigger:** "I shipped a JS fix to main + asked Frontend to publish via `eas update` — why is the device still running the old bundle?"
**Companion to:** `qaren-eas-deploy` skill (auto-loads on `eas update` / `eas build` mentions)

## Why this runbook exists

Bundle D's Phase 3 device-leg surfaced a class of failures NOT caught by Backend's smoke pack, Frontend's contract tests, or QA's gates: **OTA updates not reaching the installed `.ipa` on Ahmed's iPhone despite valid JS fixes being committed to `main`.** This runbook catalogues the diagnostic path + failure modes encountered during the Phase 3 incident (see § Last incident) so future Bundle E/F sessions can run the same checklist in under 5 minutes instead of an hour of guessing.

---

## 1. The "two-lever" reminder (read FIRST)

Per CLAUDE.md: *"Two-lever launch model: Backend deploys (Railway via `git push origin main`, ~90s) and mobile JS bundle deploys (EAS via `eas update`/`eas build`) are **independent**. Merging to main does NOT push frontend code to phones — phones run their last-bundled JS until an EAS update/build reaches them. New mobile features need BOTH levers fired."*

Decision tree:
```
Did the JS fix land on main?    →   yes   →   Did someone run `eas update --branch <channel>`?
                                                ↓
                                              no     →   STOP. Run eas update. That's the bug.
                                                ↓
                                              yes    →   Did the device cold-restart twice since the publish?
                                                          ↓
                                                        no     →   STOP. Tell user to kill + relaunch app twice.
                                                          ↓
                                                        yes    →   Continue to § 2 sanity checks.
```

### One-line verification

```bash
cd SmartCompareApp
eas update:list --branch preview --limit 3
```

Compare the newest update's `createdAt` timestamp to the commit timestamp of the JS fix. If the update is **older than the commit**, no publish happened — that's almost always the root cause.

---

## 2. Pre-update sanity checks (run BEFORE `eas update`)

Each check takes <30 seconds. Run all 5 before publishing if you've made any `app.json` / `eas.json` / `package.json` changes since the last build.

### 2.1 — `app.json` `expo.version` matches the build's appVersion

```bash
git show HEAD:SmartCompareApp/app.json | python -c "import sys,json; print(json.load(sys.stdin)['expo']['version'])"
# expected: "1.0.0" (or whatever the build was created against)

eas build:view <build-id> 2>&1 | grep -i "runtime version\|app version"
# expected: same value
```

**Why this matters:** with `runtimeVersion.policy: "appVersion"` (Bundle D's policy in `app.json:111-113` area), the OTA's runtimeVersion is auto-derived from `expo.version`. If someone bumped `expo.version` between build and update, the OTA's runtimeVersion won't match the build's runtimeVersion, and the device silently rejects the update.

### 2.2 — `eas.json` channel name matches `--branch` flag

```bash
python -c "import json; print(json.load(open('SmartCompareApp/eas.json'))['build']['preview']['channel'])"
# expected: "preview"

# Then verify the publish command matches:
eas update --branch preview ...    # ← --branch arg MUST match channel above
```

**Why this matters:** the `--branch` flag is the EAS Update channel name, NOT the git branch. Bundle D's `eas.json` maps `build.preview.channel: "preview"` (and `build.production.channel: "production"`). If FE runs `eas update --branch main` thinking it's a git branch, the preview-channel build won't receive it.

### 2.3 — `expo-updates` is installed

```bash
grep -E '"expo-updates"' SmartCompareApp/package.json
# expected: a line like "expo-updates": "~X.Y.Z"
```

**Why this matters:** an `.ipa` built without `expo-updates` listed in `package.json` deps has no client to poll for updates — `eas update` publishes to nothing. (Bundle D should always have it; this is a paranoia check.)

### 2.4 — `app.json` `updates.url` matches `extra.eas.projectId`

```bash
python -c "
import json
d = json.load(open('SmartCompareApp/app.json'))
url = d['expo'].get('updates', {}).get('url', '')
pid = d['expo'].get('extra', {}).get('eas', {}).get('projectId', '')
print(f'updates.url: {url}')
print(f'projectId:   {pid}')
assert pid in url, 'MISMATCH — updates.url must contain projectId'
print('MATCH')
"
```

**Why this matters:** EAS Updates resolves the update endpoint from `updates.url`. If the URL points at a different `projectId` than the build was registered against, the device never sees the update. (Bundle D's pair: `url: "https://u.expo.dev/387a4fcb-76f6-4857-a2fb-39482ca4bd40"` + `projectId: "387a4fcb-76f6-4857-a2fb-39482ca4bd40"`. They MUST stay in sync.)

### 2.5 — Same projectId across local + EAS dashboard

```bash
eas project:info
# expected: projectId matches app.json:extra.eas.projectId
```

**Why this matters:** rare but catastrophic — if someone re-ran `eas init` and accidentally created a NEW project, `app.json` may still point at the OLD one. Builds go to one, updates go to the other.

---

## 3. The 2-launch dance (Expo default behavior)

`expo-updates` checks for new bundles on **cold launch**, downloads them in the background, and activates the new bundle on **the NEXT cold launch**. This means:

- Launch 1 after publish: app uses OLD bundle, downloads NEW bundle.
- Launch 2 after publish: app uses NEW bundle.

A common false-negative: Ahmed publishes, opens app once, sees no change, assumes OTA failed. Reality: download happened, activation pending. Solution: full kill (swipe up from app switcher) + relaunch.

Reference: https://docs.expo.dev/eas-update/runtime-versions/

Can be overridden via `expo.updates.fallbackToCacheTimeout: 0` for instant activation, but that adds startup latency. Not recommended for Bundle D's TestFlight phase.

---

## 4. Diagnostic command cheatsheet

```bash
# Was an update published?
eas update:list --branch preview --limit 3
# Output columns: createdAt | platform | runtimeVersion | groupId | message
# Latest createdAt should be AFTER the fix commit timestamp.

# What runtimeVersion did the latest update ship to?
eas update:view <group-id>
# Confirms runtimeVersion + branch + commit + bundle URLs.

# What runtimeVersion is the installed .ipa expecting?
eas build:list --platform ios --limit 3
# Latest preview build's runtimeVersion column should MATCH the update's runtimeVersion.

# CDN sticky / device cached old manifest?
eas update --branch preview --clear-cache --message "force refresh"
# Forces a fresh manifest fetch on next cold launch.

# Full project health check before publishing
cd SmartCompareApp && npx expo-doctor
# Catches missing config plugins, version mismatches, deprecated APIs.

# What's the build's embedded channel?
# (open the .ipa via Xcode → IPA viewer → Info.plist → look for EXUpdatesRequestHeaders → expo-channel-name)
# OR easier: eas build:view <build-id> | grep -i channel
```

---

## 5. Diagnostic via Sentry + Supabase MCP

### 5.1 — Sentry release + runtime-version tags

When `@sentry/react-native` is configured correctly (Bundle D's commit `4558f9e` set this up), every captured exception carries:

```
tags:
  release:           com.qaren.app@1.0.0+<build_number>
  runtime-version:   1.0.0
  dist:              <ios-build-number>
```

If you see `tags[release]` is EMPTY on production crashes, that means the Sentry SDK isn't getting the release metadata — likely because:
1. Sentry plugin not in `app.json` plugins array (Bundle D added it; should be present)
2. `SENTRY_AUTH_TOKEN` EAS env not configured for the channel (A4 fixed this in commit `43cca75`)
3. Sentry SDK not initialized before first error (timing issue)

**Bundle E follow-up flag:** during today's Phase 3 incident, `tags[release]` was observed EMPTY on the `RNGoogleSignin` errors. Worth a separate audit to ensure Sentry release metadata flows correctly post-A4 enablement.

### 5.2 — Supabase auth logs (cite recipe from today's P0 device-leg investigation)

```python
# Via mcp__plugin_supabase_supabase__get_logs(project_id=qulajmyxdbdkchvecmvc, service=auth)
# Output is JSON-line stream; large enough to require slicing via tool-results file.

# Grep recipe for apple/google sign-in failures:
import re
src = open('<tool-results path>').read()
hits = re.findall(r'\{[^{}]{0,500}apple[^{}]{0,500}\}', src, re.IGNORECASE)
# Each hit shape:
#   {"component":"api","error":"<descriptive>","grant_type":"id_token",
#    "level":"info","method":"POST","msg":"<HTTP status: descriptive>",
#    "path":"/token","referer":"https://<backend-url>",
#    "remote_addr":"<ip>","request_id":"<uuid>","time":"<ISO8601>"}
```

**Interpreting Supabase auth error strings:**

| Error | Means | Action |
|---|---|---|
| `apple: invalid ID token` + `Unable to detect issuer` | iOS SDK returned malformed JWT; iss claim missing/wrong | Frontend — check iosClientId, audience config |
| `provider not enabled` | Supabase Auth provider toggle is OFF | Dashboard → Auth → Providers → flip Apple ON |
| `invalid audience` / `audience mismatch` | Service ID + Bundle ID audiences not both in Supabase "Client IDs" field | Dashboard → Auth → Providers → Apple → add both `app.qaren.signin,com.qaren.app` |
| `invalid token` (no issuer detail) | JWT signature failed validation | Check Apple Key (.p8) hasn't been rotated/revoked |

---

## 6. Failure modes catalogue (real Phase 3 incidents)

### 6.1 — "`eas update` never ran"

**Symptom:** Code committed to main hours/days ago. Device still on old bundle.

**Detection:**
```bash
eas update:list --branch preview --limit 3
# Latest createdAt is older than the fix commit.
```

**Fix:**
```bash
cd SmartCompareApp
eas update --branch preview --message "<commit subject>"
# Then user cold-restarts app twice.
```

**Root cause:** Someone merged to main and assumed CI/CD auto-publishes. Bundle D doesn't have an EAS GitHub Action — `eas update` is manual.

**Prevention:** Always pair a JS-only fix commit with the literal `eas update --branch preview` command in dispatcher relay AND in the commit body. Don't say "OTA ships next" — actually run the command.

### 6.2 — "Runtime version drift after app.json edit"

**Symptom:** Update published, device polls, but never activates the new bundle.

**Detection:**
```bash
eas update:view <update-group-id> | grep runtimeVersion
eas build:view <build-id>          | grep "Runtime version"
# Values DIFFER.
```

**Root cause:** With `runtimeVersion.policy: "appVersion"`, any change to `app.json` `expo.version` bumps the runtimeVersion. The new update targets the new version; old builds (still on the old runtimeVersion) silently ignore it. Conversely, an update published BEFORE an `expo.version` bump only reaches old-runtime builds.

**Fix options:**
- (a) Re-publish targeting the build's specific runtimeVersion:
  ```bash
  eas update --branch preview --runtime-version 1.0.0 --message "..."
  ```
- (b) Rebuild the `.ipa` so it embeds the new runtimeVersion + bundle natively.

**Prevention:** NEVER bump `expo.version` mid-Bundle. Reserve version bumps for the final Phase 4 close-out commit, AFTER all device-leg verification is GREEN.

### 6.3 — "CDN sticky"

**Symptom:** Published update visible in `eas update:list`, device pulled it (Sentry shows correct release), but the bundle content is the OLD one.

**Detection:** Hash the local bundle vs the served bundle — they differ.

**Fix:**
```bash
eas update --branch preview --clear-cache --message "force CDN refresh"
```

**Root cause:** Expo's CDN cached an older manifest entry. Rare but happens after rapid-fire updates within minutes.

### 6.4 — "Wrong --branch flag"

**Symptom:** Same as 6.1 (no update on the build's channel) but `eas update:list` shows recent activity on a different channel name.

**Detection:**
```bash
eas update:list --branch main         # FE accidentally published here
eas update:list --branch preview      # build's channel — empty post-fix
```

**Fix:** Re-publish with the correct `--branch <channel>` matching `eas.json` `build.<profile>.channel`.

**Prevention:** Cite the literal command in every "ship OTA" instruction. The CLAUDE.md `qaren-eas-deploy` skill's "Quick recall" line is: `cd SmartCompareApp && eas update --branch <channel> --message "..."` — copy-paste the `--branch preview` form, don't paraphrase.

---

## 7. Certificate pinning rotation watch (cross-reference)

Bundle D's `SmartCompareApp/src/services/certificatePinning.ts` pins Railway's TLS intermediate cert SPKI (Subject Public Key Info hash). When Railway rotates its intermediate cert (Let's Encrypt does this ~yearly + emergency-rotates on incident), the pinned SPKI no longer matches what the device sees → all HTTPS rejected → "Network Error" with no Sentry stack (the request never leaves the SSL stack).

**Cross-reference:** `docs/SECURITY_HARDENING_CONTEXT.md` should have the SPKI extraction recipe. If missing, here's the canonical openssl command:

```bash
# Get the current intermediate cert + its SPKI hash:
openssl s_client -connect web-production-58776.up.railway.app:443 -showcerts < /dev/null 2>/dev/null \
  | awk '/BEGIN CERTIFICATE/,/END CERTIFICATE/' \
  | openssl x509 -noout -pubkey \
  | openssl pkey -pubin -outform DER \
  | openssl dgst -sha256 -binary \
  | base64
# Output: <base64-encoded SHA-256 of SPKI> — this is what cert pinning needs.

# Current Let's Encrypt intermediates as of 2026-05-25:
# E5 = forward backup
# E7 = active (rotated from E8 ~mid-May 2026)
# E8 = legacy (still in chain as cross-signed)
```

Bundle D's commit `f6214c6` added E7 as the primary pin alongside E8 (cross-signed in chain) + E5 (forward backup). Future Bundle E should add an automated openssl-watcher cron that emails/Sentry-alerts when the active intermediate changes from any of the 3 pinned values, giving us a 30-day window to ship a new pin set before users break.

---

## 8. Recovery playbook

| Scenario | Action |
|---|---|
| JS-only fix committed but device still on old bundle, `eas update:list` empty | Run `eas update --branch preview --message "<commit subject>"` |
| JS-only fix committed, update published, device still on old bundle | Tell user to cold-restart app twice (§ 3 two-launch dance) |
| JS-only fix committed, update published, device cold-restarted, still old bundle | `eas update --branch preview --clear-cache` (§ 6.3 CDN sticky) |
| JS-only fix committed, update published, device cold-restarted + cache cleared, still old bundle | Check runtimeVersion mismatch (§ 6.2) — likely needs rebuild OR `--runtime-version <X>` flag |
| Native config change required (new plugin, new entitlement, new InfoPlist key) | Fresh `eas build --profile preview --platform ios` — OTA cannot update native code |
| Cert pinning fails (Network Error, no Sentry) | Update SPKI pins in `certificatePinning.ts` (§ 7) + `eas update --branch preview` (it's a JS file) |
| `expo-doctor` flags an issue mid-troubleshooting | Fix the doctor warning FIRST — symptoms cascade from config-level issues |
| All else fails | Tear down build chain: `eas build:cancel --all` → fix → `eas build --profile preview --platform ios` from scratch |

---

## 9. Last incident — Phase 3 device-leg postmortem (2026-05-25)

**Context:** Bundle D merged to main 2026-05-24 (`6ee3aa5`, 132 commits, 5-Opus team). Phase 3 EAS preview build kicked off by Ahmed 2026-05-24 evening after ITS export-compliance flag (`67ec30a`) was cherry-picked to main. Build completed + `.ipa` installed on Ahmed's iPhone overnight.

**Symptom (2026-05-25 morning):** All 3 auth methods (Google / Apple / Email) returned errors on the device. Sentry confirmed `RNGoogleSignin: failed to determine clientID — GoogleService-Info.plist was not found and iosClientId was not provided`.

**Root cause sequence:**
1. Frontend Bug 1 — `googleSignIn.configure()` passed only `webClientId` but iOS SDK requires both `webClientId` + `iosClientId`. Fix: derive `iosClientId` from existing `iosUrlScheme` in `app.json` (reverse the dot order).
2. Frontend Bug 2 — Cert pinning SPKI list pinned Let's Encrypt E8 (legacy) + E5 (backup) but NOT E7 (active intermediate that Railway rotated to ~mid-May 2026). All HTTPS to Railway rejected at the pinning layer → "Network Error" on Apple Sign-In + email auth. Verified via `openssl s_client` showing the active chain.

**Fix commit (13:52 UTC):** `f6214c6 fix(auth): iosClientId + LE E7 SPKI pin (P0 Phase 3 device-leg)` — touched `SmartCompareApp/src/services/{authService,certificatePinning}.ts`. JS-only, no native config change → eligible for OTA.

**The OTA delivery gap (11:35:20Z post-commit — wait, 2026-05-25 11:35 < 13:52 — the Sentry timestamp PRECEDES the fix; updated trace below):**

Sentry continued to fire `RNGoogleSignin` after the fix was committed. Investigation:
- runtimeVersion (`appVersion` policy, `expo.version: "1.0.0"`): UNCHANGED across the fix commit. **NOT a mismatch.**
- `app.json` + `eas.json` not touched in `f6214c6` or `510a8f2`. **NOT a config-drift issue.**
- projectId `387a4fcb-76f6-4857-a2fb-39482ca4bd40` consistent in both `app.json:extra.eas.projectId` and `app.json:updates.url`. **NOT a project mismatch.**

**Most likely root cause:** `eas update --branch preview` was never run after `f6214c6` committed to main. Backend's "Two-lever launch model" caveat (CLAUDE.md) bit us — merge ≠ ship to phones.

**Diagnostic commit:** `510a8f2 debug(bundle-d): Phase 3 OTA + Apple token RCA — diagnostic logging` added `[APPLE-DIAG]` logging in `authService.ts` to verify the OTA bundle is actually activating. If `[APPLE-DIAG]` line appears in Xcode device log, OTA worked; if not, OTA never reached the device.

**Verification ask post-fix-publish:**
```bash
cd SmartCompareApp
eas update:list --branch preview --limit 3
# Latest createdAt should be 2026-05-25T13:5X UTC or later (post-f6214c6)
```

**Lessons codified in this runbook:** § 1 (two-lever discipline), § 6.1 ("eas update never ran" most-common cause), § 8 (recovery playbook starts with empty-update-list check).

---

## 10. Bundle E pre-tester-invite gate proposal

This runbook should be a hard pre-flight checklist before ANY future TestFlight tester invite. Pair with QA's Bundle E gate proposal:

- [ ] § 2 sanity checks (5 of 5 GREEN) before kicking off the `.ipa` build
- [ ] After every JS-only fix commit, the literal `eas update --branch preview --message "..."` command is run AND `eas update:list` shows the publish within 5 min of commit
- [ ] Sentry tags[release] + tags[runtime-version] verified non-empty on a deliberate test-crash before declaring "Sentry observability GREEN"
- [ ] Cert pinning SPKI list verified against current Railway intermediate via openssl s_client within 24h of any device-build
- [ ] Cold-restart twice on the device after every OTA publish before declaring the publish "received"

If any of these were enforced today, the Phase 3 device-leg incident would have been caught in <5 min instead of consuming dispatcher cycles.

---

## 11. Related artifacts

- `qaren-eas-deploy` skill auto-loads on `eas update` / `eas build` mentions
- CLAUDE.md "Two-lever launch model" + "EAS Update infrastructure" sections
- `SmartCompareApp/eas.json` channel mapping
- `SmartCompareApp/app.json` `runtimeVersion.policy` + `updates.url` + `extra.eas.projectId`
- `SmartCompareApp/src/services/certificatePinning.ts` SPKI pins
- `docs/SECURITY_HARDENING_CONTEXT.md` (if exists — cert rotation watch)
- Bundle D incident: commits `f6214c6` (fix) + `510a8f2` (diagnostic)
- Backend gradient-curl recipe for parity-with-google in `docs/plans/bundle-d-native-ops-signoff.md` (Apple Sign-In Service ID verification fallback when direct dashboard access unavailable)
