---
name: Bundle D Risk Ledger
description: Master R1-R24 list + preventive control + status tracker for Bundle D (dispatcher-owned)
type: project
---

# Bundle D Risk Ledger (R1-R24)

| # | Risk | Preventive control | Owner | Status |
|---|---|---|---|---|
| R1 | `/admin/*` static auth gate (audit C2) regression — `app/main.py` middleware order load-bearing | Backend snapshots middleware → edit → diff → reject reorder; PR sub-commit isolates middleware changes | Backend | PENDING |
| R2 | CSP scoping — admin pages allow `'unsafe-inline'` + `cdn.jsdelivr.net`, rest strict `default-src 'none'` | No inline scripts on non-admin pages; reject any diff that broadens CSP allow-list | Backend | PENDING |
| R3 | `schema_version=2` filter excludes legacy v1 rows — History detail fail may be working-as-designed | Backend's FIRST action on history detail = query Supabase for failing comparison's `schema_version`; if v1 → backfill + relax filter, NOT new screen code | Backend | PENDING |
| R4 | Apple Sign-In three-leg dependency (Service ID → .p8 → Supabase provider → backend test) | Native/Ops posts "Apple 3-leg checkpoint" comment with all 4 green before Frontend wires the button | Native/Ops | PENDING |
| R5 | `expo-apple-authentication` is a config plugin — first EAS build fails if `app.json` plugin block missing | Native/Ops commits `app.json` plugin block FIRST in own commit BEFORE triggering any EAS build | Native/Ops | ADDRESSED |
| R6 | Bundle ID conflict (`com.qaren.app` may be taken in ASC) | Native/Ops research bundle ID availability FIRST; fallback ladder `app.qaren` → `com.qaren.app` → `bh.qaren.app` ready; escalate to Ahmed before proceeding | Native/Ops | PENDING |
| R7 | EAS production build signing — first build needs Apple Distribution cert + provisioning profile | Native/Ops sets up Apple Dev Portal provisioning profile FIRST; EAS auto-manages signing if `eas.json` ios.credentials configured | Native/Ops | PENDING |
| R8 | App Store Connect 30-min upload+processing window | Phase 3 timing budgets this explicitly; tester invite waits until processing complete | Native/Ops | PENDING |
| R9 | Refresh-token mutex must be module-scope singleton | Frontend PR comment includes code excerpt showing singleton `Promise` cached at module scope, not function scope | Frontend | PENDING |
| R10 | HomeScreen Claude-Design output integration — token conflicts with existing `src/theme/index.ts` | Frontend extends theme, doesn't replace; tokens applied additively; cross-QA verifies no breaking theme change | Frontend | PENDING |
| R11 | `profile.name` i18n naming — `profile.title`/`profile.editProfile` exist; new key conflicts? | Frontend agent picks "Name" / "الاسم" as default; if Ahmed wants different (e.g., "Display name"), agent asks before commit | Frontend | PENDING |
| R12 | Reengagement flag flip ON during TestFlight may spam testers if cron has bug | Backend confirms cron stable + payload-safe BEFORE flipping; Phase 4 dispatcher action only after Ahmed acknowledges | Backend | PENDING |
| R13 | App Privacy Nutrition Labels — Apple still asks for these even for internal TestFlight | Native/Ops drafts based on observed data flows; Ahmed approves answers before ASC submission | Native/Ops | PENDING |
| R14 | Apple "Sign in with Apple" entitlement must exist in BOTH Apple Dev Portal + `eas.json` `ios.entitlements` | Native/Ops anchor includes literal entitlements snippet to paste; checklist verifies both locations | Native/Ops | PENDING |
| R15 | 24 `_fire_and_forget` audit sites — false positives (some legitimate plain `create_task` sites) | Backend judges per site; PR comment lists each site with decision (WRAP / SKIP-with-reason) | Backend | PENDING |
| R16 | HomeScreen redesign may REMOVE TwoInputShell behavior | Frontend acceptance test = full Bundle B PR #6 EN+AR walkthrough on new design; ZERO regressions on TwoInputShell contract | Frontend | PENDING |
| R17 | Camera help button i18n — new copy must pass scary-vocab gate | Frontend uses approved vocabulary; copy-policy test (`.copy-policy.json`) catches violations | Frontend | PENDING |
| R18 | Profile toggle wiring — Reengagement subs endpoint may not exist | Backend FIRST action = grep for `reengagement_subscriptions` table + endpoint; if missing, Backend creates BEFORE Frontend wires UI | Backend | PENDING |
| R19 | Force-update env vars dangerous — `APP_FORCE_UPDATE=true` boots all old-version users | Sequence: `APP_MIN_VERSION` = TestFlight build version FIRST; flip `APP_FORCE_UPDATE=true` only AFTER all testers on new build | Backend | PENDING |
| R20 | C13 `delete_user_cascade` SQL changes must not break existing cascade flow | Backend writes migration 025 with rollback file; tests delete flow end-to-end on staging Supabase before prod apply | Backend | PENDING |
| R21 | C14 Sentry query-string scrub — `_before_send` regex must not eat legitimate non-PII URL data | Backend writes targeted regex (matches `?q=`, `?query=`, `?email=` patterns; preserves `?nocache=true`, `?token=` already handled); test pack verifies | Backend | PENDING |
| R22 | C15 legal-doc rebrand — risk of breaking existing in-app rendering if markdown structure shifts | Backend rewrites brand strings only, preserves heading/paragraph structure; FE LegalScreen renders unchanged | Backend | PENDING |
| R23 | C17 `ai_sharing_enabled` default flip OFF — existing users with ON should NOT be reset | Frontend default applies to NEW users only; existing `users.preferences.ai_sharing_enabled = true` rows untouched; verified via SQL spot-check | Frontend | PENDING |
| R24 | Landing page hosting (O1-O3) — DNS propagation delay could leave qaren.app offline mid-cutover | Native/Ops sets up hosting + tests via direct hostname FIRST; DNS cutover only after green; TTL set low (300s) for fast revert | Native/Ops | PENDING |

## Status legend
- **PENDING** — not yet addressed
- **ADDRESSED** — control ran successfully (cite test cmd output or commit SHA)
- **N/A** — risk doesn't apply this bundle (cite reason)
- **ACCEPTED** — risk acknowledged + explicit Ahmed approval (cite PR comment URL)

## Bundle-merge gate

Dispatcher MUST verify: **zero R# in PENDING** before merging Bundle D PR.

## Update protocol

When an agent addresses a risk:
1. Edit this file: change PENDING → ADDRESSED in the agent's row.
2. Add a citation in a new section below the table (commit SHA or test output excerpt).
3. Commit with message format `risk(bundle-d): R<N> addressed by <agent> via <method>`.

## Risk citations (append-only)

<!-- agents append entries here as risks are addressed -->
<!-- format: ### R<N> — ADDRESSED <YYYY-MM-DD> by <agent>
       Method: <one-line summary>
       Citation: <commit SHA or test output excerpt or PR comment URL>
-->

### R5 — ADDRESSED 2026-05-23 by native-ops
Method: `expo-apple-authentication` plugin entry already at `SmartCompareApp/app.json:86` from pre-bundle-D state; `ios.usesAppleSignIn: true` already at line 19. Verified via direct read + JSON parse (10 plugins total post-commit `70a34b3`). Per Expo SDK 54 docs (via Context7 `/expo/expo`), the plugin auto-injects `com.apple.developer.applesignin: ["Default"]` entitlement during EAS prebuild — no manual `ios.entitlements` block needed in app.json. NOTE: R14's "BOTH" gate is split: (a) Apple Dev Portal App ID "Sign In with Apple" capability — still PENDING on Ahmed during ASC bundle claim Task 1.N.1; (b) app.json plugin block — ADDRESSED.
Citation: `SmartCompareApp/app.json:86` plugin entry pre-existing; expo-notifications plugin landed alongside in own commit `70a34b3` (separation discipline preserved).

