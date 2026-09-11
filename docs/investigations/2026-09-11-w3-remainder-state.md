# W3 remainder — ten reviewed specs, six units part-built, state saved 2026-09-11

Second session (the peer of "SESSION 65 main"). Base for every unit: `b63a8368`.
Main at save time: `19ec866a`. **Nothing from this lane is merged and nothing is
ready to merge.** Every unit is spec-complete and adversarially reviewed; six carry
partial red/green work preserved on `wip/s65d-<unit>-partial` branches.

## Lane split with the other session (agreed by message, held all day)

| owner | units |
|---|---|
| SESSION 65 main | W3-2, W1-5, W1-6 (merged #155/#156/#157), all of W4 (#158 merged, W4-1 in rework, sc-w4-2/3/4/9/10 spec-writing) |
| this lane | the W3 remainder: W3-3, W3-4, W3-6, W3-7, W3-9, W3-11b/c/d, W3-13, W3-14, W3-15, W3-16 |

Standing conventions, both sessions: PRs only; rebase on `origin/main` immediately
before merge; message the other session before merging anything touching a file it
owns; `CLAUDE.md` only in small dedicated docs PRs; **migration 038 belongs to this
lane (W3-16), 039+ to the other**; neither session edits
`tests/.pre_impl_failures.txt` without telling the other first. Files owned by the
other session and untouched here: `text_routes.py`, `feedback_service.py`,
`rate_limiter.py`, `main.py`, `async_utils.py`, `Procfile`, `railway.json`,
`price_service.py`, `structured_comparison_service.py`, `text_sanitize.py`.

## Where the work is

Ten worktrees, each `feature/s65-w3-*` at `b63a8368`, each with a
`SmartCompareApp/node_modules` junction into the shared clone (**unlink with
`[System.IO.Directory]::Delete(<link>, $false)` before ever removing one**) and the
reviewed spec at `<worktree>/.qa-w3b/<KEY>_UNIT_SPEC.md` (gitignored on the feature
branch; force-added on the wip branch so it survives).

| unit | worktree | spec | partial work preserved at |
|---|---|---|---|
| W3-3 device fingerprint | `sc-w3-fp` | 492 L + 16 rulings | `wip/s65d-W3-3-partial` — red done **and green started** (authService, ShareBottomSheet, deviceFingerprint, auth_routes all modified) |
| W3-4 unauth reset | `sc-w3-reset` | 366 L + 12 rulings | `wip/s65d-W3-4-partial` — red done (3 new suites, 4 existing adjusted) |
| W3-6 password reset | `sc-w3-pwreset` | 385 L + 14 rulings | `wip/s65d-W3-6-partial` — red done (5 client suites + 1 backend) |
| W3-15 push tap targets | `sc-w3-push` | 433 L + 2 ruling passes | `wip/s65d-W3-15-partial` — **green well advanced** (`src/navigation/linking.ts`, `src/services/pushNavigation.ts`, App.tsx, types.ts) |
| W3-9 lucide fence | `sc-w3-lucide` | 658 L + 13 rulings | `wip/s65d-W3-9-partial` — red done (test-only unit) |
| W3-13 channel freshness | `sc-w3-ci` | 745 L + 2 ruling passes | `wip/s65d-W3-13-partial` — **green well advanced** (`scripts/check_channel_freshness.py`, ci.yml, runbook, gates) |
| W3-14 error copy | `sc-w3-copy` | 1116 L + 20 rulings | none — clean, never started |
| W3-11b/c/d Arabic pack | `sc-w3-ar` | 769 L + 14 rulings | none — clean, never started |
| W3-16 consent capture | `sc-w3-consent` | 632 L + 15 rulings | none — clean, never started |
| W3-7 native bundle | `sc-w3-native` | 424 L + 18 rulings | none — clean, never started |

All ten reviews returned **APPROVED_WITH_RULINGS, `ready_for_red: true`**. W3-13 and
W3-15 carry two rulings sections; the second is labelled as superseding.

**To resume:** each worktree is still dirty with exactly the work in its wip branch,
so a resumed agent needs no restore. If a worktree is ever cleaned, recover with
`git checkout wip/s65d-<unit>-partial -- .` **never** a bare `git checkout` (that
reverts to base and has already destroyed a unit once in this campaign).

## Measured findings that change the plan

1. **W3-9 is already fixed on main and should be closed, not built.** B1 (`e3d9adb5`,
   in #138) added an inline babel plugin that rewrites every `lucide-react-native`
   barrel import to `dist/esm/icons/<name>.mjs` at build time: 3,832 → 2,192 modules,
   68 distinct icon files. The 35 remaining barrel imports **are the intended source
   form** — the plan's "34 barrel imports, ban them with eslint" test would be wrong at
   HEAD, and the bare barrel is the only form Metro, jest and tsc all resolve. What is
   left is optional test-only fence hardening: `require()`, dynamic `import()`,
   `import =` and `.js`/`.jsx` sources are not fenced, and any of them silently
   re-adds all 1,703 icon modules with CI green. **Phones still run the pre-B1 bundle**
   until `eas update --branch preview --clear-cache`.
2. **W3-15: `@react-navigation/*` ships ESM only (no `lib/commonjs`), so its real
   router has never executed under jest** — every suite that touched the package mocked
   it. Testing real deep-link resolution needs a narrow `babel-jest` transform for
   `node_modules/@react-navigation/**/*.js` plus the package added to
   `transformIgnorePatterns`. That is a shared-config change: the full-suite comparison
   against the recorded baseline is the proof it is safe.
3. **W3-15, the defect itself:** the backend emits four deep links
   (`qaren://profile/referrals`, `qaren://comparison/{id}?banner=insight`,
   `?banner=retrospective`, `qaren://cohort/divergence`); the client linking config
   registers only `c/:share_token`, `q/:share_token`, `r/:code`, and the app has **zero**
   notification-response listeners. Cold start delivers a tap twice (iOS
   `EmitterModule.swift:40-46` and Android `NotificationsEmitter.kt:70-83` both set
   `lastResponse` and emit), so the handler must dedupe by notification identifier.
4. **W3-7: deleting `RECORD_AUDIO` from `app.json` is behaviourally inert** and
   `recordAudioAndroid: false` is inert too — measured by running the installed
   plugins. The permission is contributed by the expo-camera/expo-image-picker plugin
   config, so the microphone opt-out is what does the work; the `app.json` line is a
   source-shape pin only. The icon test stays red until Ahmed supplies artwork, so it
   ships as `test.todo`, never a red CI.
5. **W3-14: the spec's "`{"ai_sharing_enabled":"yes"}` → 422" premise is false.**
   Measured on the installed pydantic 2.7.0 through the repo's own handlers, `"yes"`
   and `"on"` both return 200 with `True`. The 429 client half is largely already green
   since A11 (`74d041cb`) and #152; the client should read `retry_after_seconds` only.
6. **W3-13: the `preview` channel is 33 first-parent commits behind main** (measured).
   The CI job needs an `EXPO_TOKEN` repo secret Ahmed must add, and must **skip
   cleanly** without it (every fork PR, and this repo today); `secrets` is not usable in
   a job-level `if`, so it goes through an env-var step. The durable half is a Python
   script unit-tested over a fake eas payload and fake git ancestry — no network.
7. **W3-11: ESLint's Node API cannot run under jest here** (`A dynamic import callback
   was invoked without --experimental-vm-modules`), so the lint-rule tests must
   `spawnSync` the CLI. `ar.json` digit census: 79 Arabic-Indic digit characters against
   338 ASCII — the plan's "32 vs 21" was wrong.
8. **W3-16: there is no ToS acceptance or age gate anywhere** in client or backend
   (zero hits). It needs migration **038** (unapplied on merge, like 033–037) and the
   backend rejection must sit behind a default-OFF flag, because phones on `97b5f15`
   and on the pending OTA send nothing.
9. **W3-3: the share/referral backend half is already done** (`referral_routes.py`
   validates the 64-hex hash and `referral_service.py` persists it); only the client
   half and the social-login half are missing. Social sign-in sends
   `{"Content-Type": "application/json"}` and nothing else.

## Process findings

- **The adversarial spec review is the highest-yield stage in this pipeline.** Ten
  reviewers refuted 5–13 measured claims each in specs written by an equally careful
  writer, including four cases where the plan's own red test would have been wrong at
  HEAD (W3-9 wholesale, W3-7 twice, W3-14's 422). Never let a spec reach a red phase
  unreviewed.
- Every spec review re-measured the base SHA and found the spec's anchor stale within
  hours, because the other session was merging all day. Specs must carry a base SHA and
  reviews must re-anchor.
- Generating a JavaScript workflow script from a Python heredoc put a bare apostrophe
  inside a single-quoted JS string and the run was rejected twice. Build script text
  with double-quoted JS strings, and syntax-check before launching.

## What is owed, and by whom

**Ahmed (unchanged and still blocking):** `ENABLE_BRIGHTDATA_BUDGET_GATE=true` →
`eas update --branch preview --clear-cache` (the OTA is what puts every merged client
fix, B1's bundle included, on a phone) → rotate `ADMIN_API_KEY` → apply migrations
`035 → 036 → 037` and verify the anon `delete_user_cascade` RPC returns `42501`.
New: add the `EXPO_TOKEN` repo secret for W3-13; `railway login` (the MCP token
expired, so prod flag state is currently inferred, not read); W3-10's retailer-link
product call; W3-7's icon artwork; W3-16's age-gate shape.

**This lane, next session:** resume the four workflows named below; W3-9 likely closes
as already-green rather than shipping code. One PR per unit, rebased on `origin/main`,
message the other session before each merge.

Run ids (same-session resume only, then re-launch fresh):
`wf_8516ba9b-e9f` (W3-3, W3-4, W3-6, W3-15), `wf_e067bc4b-10d` (W3-9, W3-13),
`wf_d9ba64f2-3c4` (W3-14), `wf_29a219f1-bff` (W3-11bcd, W3-16, W3-7).
Baseline for the gates, measured at `ed75dc70` and still valid (every merge since is
backend-only): tsc 5.9.3 clean; jest 281 suites passed / 3 skipped, 2,752 tests, 44
snapshots.
