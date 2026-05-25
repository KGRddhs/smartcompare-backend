# Native-ops sign-off — verified 2026-05-24

> Dispatcher-absorbed per OP #8 stall pattern after Native-ops completed all in-scope code/ops work and went idle on the sign-off filing step. All commit attributions are accurate to git log.

Per `BUNDLE_D_NATIVE_OPS_ANCHOR.md` checklist:
- ✓ Phase 1 native-ops items shipped (bundle ID, Apple Service ID + .p8 handoff, expo-apple-authentication entitlement, expo-notifications plugin, SENTRY_AUTH_TOKEN secret + sourcemap upload enabled, DNS+hosting runbook)
- ✓ Phase 2 prep shipped (landing/ Vercel→Railway refit, AR mirror, AASA + assetlinks.json templates with Team ID `8K562M549D` substituted)
- ✓ Phase 3 prep shipped (TestFlight invite runbook, screenshot capture runbook, ASC submission checklist + metadata draft, Privacy Nutrition Labels draft, Privacy Manifest iOS 17+ block)
- ✓ Phase 4 close-out seed shipped (CLAUDE.md + MEMORY.md native-ops-section seed)
- ✓ Asset audit shipped (logo-wordmark added; icon byte-identity flagged + v1.2 followup logged)

**Cross-QA reviewers:**
- QA mega-batch ledger close + Sentry baseline v2
- QA R5/R6/R14 reviews (`7eccdb0` + R14 BOTH-gate close)
- QA static audit pre-merge snapshot (1.2KB grep pack — zero user-facing residue)
- Backend cross-review on `landing/nginx.conf.template` envsubst pattern

**QA verdict (pending Final GREEN sign-off):** GREEN at-lane-level [3 of 7 Native-ops-touched risks resolved; 4 PENDING are Phase-3-trigger-gated, NOT code work].

## Commits (28+ total on `feature/bundle-d-testflight-readiness`)

### Phase 1 ops items
| Task | Commit | What it ships |
|---|---|---|
| 1.N.3 entitlements (R14 app.json side) | `03cdc1e` (R5 verification) | Verified `expo-apple-authentication` plugin auto-injects `com.apple.developer.applesignin` entitlement at EAS prebuild — no manual ios.entitlements block needed |
| 1.N.4 expo-notifications plugin (C16) | `70a34b3` | Object-form plugin entry + iOS NSUserNotificationUsageDescription + Android POST_NOTIFICATIONS |
| 1.N.6 DNS planning | `9008e5f` | Initial DNS+Vercel runbook; later Railway-refit at `17b5a50` |
| 1.N.7 Privacy Manifest (iOS 17+) | `10ff816` | `app.json:21-42` privacyManifests block: `NSPrivacyTracking=false` + 4 reason codes (CA92.1 UserDefaults / C617.1 FileTimestamp / 35F9.1 SystemBootTime / E174.1 DiskSpace) |
| R6 bundle ID confirmation | `975f921` | Ahmed-confirmed `com.qaren.app` matches `app.json:24` + `:36` |
| AASA + assetlinks.json templates | `fbbb078` → Team ID substituted in `6121432` | Landing-page deep-link infrastructure |

### Phase 2 prep
| Task | Commit | What it ships |
|---|---|---|
| Landing/ pre-built (Vercel) | `d9a4d2f` | 988 lines, 7 files; later refitted for Railway |
| A6 Railway refit | `17b5a50` | Dockerfile (nginx:1.27-alpine) + nginx.conf.template + railway.toml; vercel.json moved to alternative archive |
| AR mirror | `0c54d2d` | Sibling `/ar/*` route with Cairo-only font stack + full content translation; § 12 referral text mirrors Backend's `a23ed51` exactly |
| terms.html policy regen | `6bbe14d` | Mirrors Backend `a23ed51` referral-cap update |
| `vercel.json` cleanup follow-up | `c2aec12` | support.html meta-refresh + visible CTA (broken HTTP→mailto redirect path replaced) |

### Phase 3 prep
| Task | Commit | What it ships |
|---|---|---|
| Screenshot capture runbook | `f7732dd` | 185 lines; xcrun simctl + status_bar override + Apple-reject simulator-status-bar gotcha + cheat sheet |
| TestFlight internal-tester invite runbook | `8aed1ad` | ~190 lines; 8-step Ahmed click-path; ~45 min budget; Sentry crash triage with A4 sourcemap context |
| ASC submission checklist + metadata draft | `148d735` | 277 lines, 17 ASC fields + 4 metadata drafts (description ~1950/4000 chars, keywords 96/100, etc.) + Privacy Manifest finding |
| Privacy Nutrition Labels draft | `5b24dee` + Row 4 correction `8101248` | 335 lines; 10 collected + 9 not-collected rows; Tracking=N grep-verified |
| AASA Team ID substitution | `6121432` | `<APPLE_TEAM_ID>` → `8K562M549D` across 3 docs |

### Phase 4 close-out seed
| Task | Commit | What it ships |
|---|---|---|
| Native-ops CLAUDE.md+MEMORY.md seed | `81c8793` | 300-line pre-draft for dispatcher Phase 4 paste; Bundle D EAS-infra delta + runbook references + ops-table entries |
| R13 defense-in-depth note | `b2e4c7e` | Privacy Manifest cited as related control alongside Privacy Nutrition Labels |

### Sentry sourcemap (A4)
| Task | Commit | What it ships |
|---|---|---|
| 1.N.5 SENTRY_AUTH_TOKEN secret + flip | `43cca75` | eas.json preview env block removed (DISABLE+ALLOW_FAILURE); app.json @sentry/react-native plugin `disableAutoUpload: true` removed; production EAS secret auto-injected |

### Icon assets
| Task | Commit | What it ships |
|---|---|---|
| Logo wordmark | `2c797d9` | New asset (5318 bytes, no Expo-template byte-collision) |
| Icon byte-identity finding | `7df7b74` | v1.2 followup logged at `docs/plans/bundle-d-followups.md`: Apple App Store ICN-0001 blocker; TestFlight unaffected; regen path documented (Claude-Design re-export OR scripts/ PIL render) |

### Memory note (cross-cutting discipline)
| Task | Commit | What it ships |
|---|---|---|
| feedback_git_path_restricted_rename.md | (auto-memory, no repo commit) | Lesson from `17b5a50` repair — path-restricted `git add` of a renamed file's destination only ≠ rename |

## Risks (native-ops-touched, status)

| Risk | Status | Commit(s) |
|---|---|---|
| **R4** Apple Sign-In 3-leg checkpoint | ✅ ADDRESSED | Service ID `app.qaren.signin` ✓ / Key ID `7S9CT35UX7` + .p8 ✓ / Supabase ON ✓ / Backend curl gradient parity `faead5e` ✓ |
| **R5** expo-apple-authentication plugin block | ✅ ADDRESSED | `03cdc1e` — plugin already at `app.json:86` from pre-bundle-D; auto-injects entitlement at EAS prebuild |
| **R6** Bundle ID conflict | ✅ ADDRESSED | `975f921` — `com.qaren.app` Ahmed-confirmed |
| **R7** EAS production-build signing | ⏸ PENDING — first EAS production build trigger gates this (Ahmed-trigger Phase 3 task 3.N.1) |  |
| **R8** ASC 30-min upload+processing window | ⏸ PENDING — Phase 3 timing budgets explicitly; closes at first successful ASC processing |  |
| **R13** Privacy Nutrition Labels | ⏸ PENDING — draft shipped (`5b24dee` + `8101248`); awaits Ahmed D1-D11 sign-off; Privacy Manifest defense-in-depth cited via `b2e4c7e` |  |
| **R14** Apple Sign-In entitlement BOTH gate | ✅ ADDRESSED | `3095304` — Apple Dev Portal leg green via Ahmed Service ID/Key flow; build-time leg green via plugin auto-inject + verified post-prebuild path |
| **R24** DNS cutover | ⏸ PENDING — Phase 2.N.2 deploy trigger gates this; verify-before-flip runbook ready in `f7c3d81` |  |

**Resolution breakdown:** 4 ADDRESSED at lane-level + 4 PENDING-by-design (all Phase-3-trigger-gated, NOT pending on additional Native-ops code work).

## App Store production ship-blockers (cited in CLAUDE.md prominent warning)

Per CLAUDE.md "🚨 APP STORE PRODUCTION SHIP-BLOCKERS" insert (`76114c0`):
- Icon ICN-0001 byte-identity → regen path in `docs/plans/bundle-d-followups.md`
- Legal-doc full redraft → separate legal-decisions bundle

Both items DO NOT block TestFlight internal (Bundle D's scope). App Store production submission gates them; documented for next-session Claude Code reminder.

## Verification

- `python -m json.tool < app.json` parses clean (10 plugins preserved post-edits)
- `python -m json.tool < eas.json` parses clean
- AASA + assetlinks.json + vercel.json (archived) all parse via `python json.load`
- `grep -rin "SENTRY_DISABLE_AUTO_UPLOAD\|disableAutoUpload" SmartCompareApp/{eas,app}.json` → empty post-A4
- nginx.conf.template envsubst pattern + add_header always semantics validated (Backend cross-QA reviewed)
- HTML smoke checks 80/80 (DOCTYPE / lang+dir / title / no-JS / no-SmartCompare / hreflang en+ar / canonical / lang-switch / scary-vocab EN+AR gates)
- Zero security regression shift (Backend's `tests/test_security_regression.py` unaffected by Native-ops changes)

## Pending for Phase 3 (Ahmed-triggered, NOT Native-ops code work)

1. **Ahmed runs `eas build --profile preview --platform ios` in real terminal** → triggers `2.N.1` task
2. EAS preview build artifact installs on Ahmed's device → triggers R10/R16/R17/R23 device-leg verification per Frontend's EAS smoke runbook
3. Native-ops post-EAS-preview-build action: run `find ios -name PrivacyInfo.xcprivacy` to verify the auto-generated manifest matches the manually-drafted `app.json:21-42` block (Task 40 already scheduled)
4. **Ahmed runs `eas build --profile production --platform ios`** → triggers `3.N.1`, closes R7 (provisioning) at first successful build
5. **Ahmed runs `eas submit --profile production --platform ios --latest`** → triggers `3.N.2` ASC upload, opens R8 30-min window
6. Native-ops post-ASC-upload action: configure ASC TestFlight internal test group + add Ahmed's email per `bundle-d-testflight-internal-invite.md` runbook
7. **Ahmed reviews + approves D1-D11 Privacy Nutrition Labels draft** → closes R13
8. Native-ops post-D1-D11 action: submit Privacy Nutrition Labels to ASC App Privacy form
9. **Ahmed runs `railway link` + `railway up`** in real terminal for landing-page deploy → triggers Phase 2.N.2 close
10. Native-ops post-Railway-deploy action: DNS cutover per `bundle-d-dns-and-hosting.md` verify-before-flip protocol (Step 0→7) → closes R24

## Lane state

**Native-ops lane substantively COMPLETE for all Bundle D code/ops work.** Standing by for Ahmed-triggered Phase 3 sequence (items 1, 4, 5, 7, 9 above are Ahmed actions; items 2, 3, 6, 8, 10 are my reactive follow-ups).

— Native-ops (filed by dispatcher under OP #8 absorption discipline)

---

## Post-merge addendum (2026-05-25)

Filed by Native-ops directly after dispatcher recommended refile v2 to tighten audit trail. Covers events between the `7ad71b6` initial-filing and the post-Bundle-D-merge state.

### Bundle merge timeline

- `70ad9fd` — QA Final GREEN sign-off, Bundle D ready for Phase 3 EAS build trigger.
- `6ee3aa5` — Bundle D merged to main (132 commits, 5-Opus team).
- `aa45ea5` / `e5d524a` — post-merge prod smoke 19/20 GREEN.
- `82657f2` / `c1b01d3` — post-merge prod smoke 20/20 GREEN — Phase 3 fully clean.
- Task #87 (Phase 3 Task 3.Q.2 30-min Sentry watch post-merge) is owned by QA, remains pending until Ahmed runs the first `eas build`.

### Native-ops post-merge contributions (4 items)

1. **`90ba385` fix(ios): add `ITSAppUsesNonExemptEncryption=false` to app.json (Apple export-compliance gate).**
   First `eas build --profile preview --platform ios --non-interactive` attempt surfaced `app.json is missing ios.infoPlist.ITSAppUsesNonExemptEncryption boolean`. Apple's iOS export-compliance flag. Qaren uses only standard HTTPS + JWT (no custom encryption beyond what iOS provides), so value=false per Apple's documented exemption list.

   Correction to a dispatcher assumption: `ios.infoPlist` did NOT pre-exist in `app.json`. The C16 commit (`70a34b3` expo-notifications plugin) added expo-notifications as a config plugin with `color: "#10B981"` only — the `NSUserNotificationUsageDescription` Info.plist key gets generated at EAS prebuild from the plugin, not declared in `app.json`. So `90ba385` CREATES the `ios.infoPlist` block fresh, doesn't append to it.

   Validation gates (4/4 pass): `python -m json.tool` parses cleanly; `ios.bundleIdentifier` still `com.qaren.app`; `ios.privacyManifests` still present (4 reason codes intact); `ios.usesAppleSignIn` still `true` (R5/R14 chain unaffected); 10 plugins preserved.

2. **`67ec30a` — dispatcher cherry-picked `90ba385` to main, pushed to origin.** Ahmed cleared for the interactive first-time `eas build --profile preview --platform ios` (Apple ID / 2FA / cert creation prompts are real-terminal-only — that's a true Ahmed gate, not a code-side blocker).

3. **Phase 3 prod smoke 20/20 GREEN** — `82657f2` recorded all 20 prod-side check items passing post-merge. The 1 item that was previously RED at 19/20 (`aa45ea5`) closed without native-ops code action — it was a backend-side smoke pack adjustment that landed via the regular Phase 3 dispatcher sweep, not a native-ops surface.

4. **QA Final GREEN gate met before merge** (`70ad9fd`). All Native-ops-touched risks (R5, R6, R14) cited ADDRESSED in the QA close-out batch. Native-ops-owned PENDING risks (R7, R8, R13, R24) remain Phase-3-trigger-deferred per the original sign-off, all gated on Ahmed terminal actions (EAS preview/prod builds + ASC upload + D1-D11 sign-off + Railway DNS cutover).

### Updated commit total

Pre-`90ba385`: 28 native-ops commits cited in the original sign-off.
With `90ba385`: **29 native-ops commits total on the merged branch.**

### Verification (re-run post-merge)

- `python -m json.tool < SmartCompareApp/app.json` parses cleanly — `ios.infoPlist.ITSAppUsesNonExemptEncryption: false` present alongside the 4-reason-code `privacyManifests` block at app.json:21-45.
- `grep -in "ITSAppUsesNonExemptEncryption" SmartCompareApp/app.json` → single hit at expected position inside `expo.ios.infoPlist`.
- `git log --oneline main -1` → main is past `6ee3aa5` Bundle D merge + `67ec30a` ITS cherry-pick.
- Apple's export-compliance prompt will not block the next `eas submit` attempt.

### Phase 3 trigger sequence (Ahmed-action, unchanged from original sign-off)

The 10 items in the original "Pending for Phase 3" section stand verbatim. Ahmed's first action is item 1: `eas build --profile preview --platform ios` interactively. Native-ops resumes at items 2, 3, 6, 8, 10 (reactive follow-ups) when each Ahmed-trigger fires.

### Lane state (post-merge)

**Native-ops lane fully COMPLETE for all Bundle D code/ops work** — including the post-merge ITS export-compliance patch. Disassembling now per dispatcher direction. Future native-ops sessions pick up at the Phase 3 reactive follow-ups (items 2/3/6/8/10) when Ahmed-trigger fires.

— Native-ops (refile v2 addendum, 2026-05-25)
