## What

Session 70 unit **U4b** (spec `docs/investigations/2026-09-30-session-70-state/U4B_ICONS_DEPS_SPEC.md`, rulings RQ1–RQ21). It closes App Store ship-blocker #1 (ICN-0001, placeholder launcher art) and the dependency hygiene the launch runbook deferred to this unit.

- **Launcher art.** `icon.png`, `adaptive-icon.png`, `splash-icon.png` and `favicon.png` are rendered from Ahmed's master (`docs/brand/myez-icon-master-2048.png`, decision D4) by `scripts/render_myez_icons.py`. The renderer pins the master's SHA-256, is deterministic (two runs are byte-identical), writes `docs/brand/myez-icons.manifest.json`, and has a `--check` mode that writes nothing. `ICON_ART_SUPPLIED` is now `true`, so the art pins run.
- **SDK-54 patch bumps.** `expo ~54.0.37`, `expo-font ~14.0.12`, `expo-localization ~17.0.9`, `expo-screen-capture ~8.0.10`, `expo-updates ~29.0.20`, `babel-preset-expo ~54.0.12`. `eslint-config-expo` is aligned to `~10.0.0` (the SDK-54 line; `^55` was the SDK-55 config).
- **`react-native-gesture-handler` removed.** A walk of all installed manifests found only devDependency edges, no `@react-navigation` dependency or peer. The runbook row that said otherwise is corrected.
- **`expo.install.exclude = ["react-native-svg"]`**, on purpose: the installed 15.15.5 is kept.
- **CI.** The single non-blocking drift step becomes a BLOCKING `Expo dependency drift (lockfile)` step (`EXPO_OFFLINE=1`, deterministic) and a report-only `Expo SDK patch drift (report-only)` step. The comment above them states the offline blind spots and the silent offline fallback of the online step.
- **`expo.version` stays `1.0.0`.** `app.json` is not edited.

## This is a native change

The icons, the removed native module and the expo native patch versions reach devices only through a new `eas build`. Nothing here changes `src/**`.

Rule for OTAs after this merge (spec review correction 4, verbatim):

> Before the first `eas update --branch preview` from a main that contains U4b: (a) `npm ls` shows exactly the version set recorded in the U4b PR body; (b) diff `@expo/cli` `build/src/export/**` (the code `eas update` runs; not diffed in §1.3, see §7) between 54.0.24 and the installed version, or smoke-test that OTA on one tester device before announcing it; (c) any later expo-package bump repeats (a)–(b) or bumps `expo.version`. From the first production build on, every native change bumps `expo.version`.

Version set for clause (a), one installed copy each:

| package | version |
|---|---|
| expo | 54.0.37 |
| expo-font | 14.0.12 |
| expo-localization | 17.0.9 |
| expo-screen-capture | 8.0.10 |
| expo-updates | 29.0.20 |
| expo-file-system | 19.0.24 |
| expo-constants | 18.0.14 |
| babel-preset-expo | 54.0.12 |
| @expo/metro-config | 54.0.17 |
| @expo/cli | 54.0.27 |
| @expo/prebuild-config | 54.0.9 |
| eslint-config-expo | 10.0.0 |
| react-native-svg | 15.15.5 (excluded from the check) |

## Gates (measured on the committed bytes)

| gate | result |
|---|---|
| W3-7 config suite alone | 58 passed / 58 |
| FULL jest | 351 suites passed, 3 skipped; 3,448 tests passed; 44 snapshots; no `.snap` in the diff |
| tsc 5.9.3 (project compiler by path) | 0 errors |
| eslint | changed files clean; `src` 148 warnings, byte-identical to base |
| `EXPO_OFFLINE=1 npx expo install --check` | rc 0 |
| `CI=1 npx expo install --check` (online, orchestrator) | rc 0, "Dependencies are up to date", no file written |
| `npx expo-doctor` (orchestrator) | 18/18 checks passed |
| duplicate native modules (iOS + Android) | 0 |
| `expo-modules-autolinking verify` | OK |
| renderer `--check` | rc 0, four outputs pixel-equal, manifest equal |
| iOS `export:embed` | OK, 2,214 modules, no gesture-handler strings |
| backend files that scan `SmartCompareApp/` | 178 passed |
| `npm ci --dry-run` on npm 10.9.9 | lock accepted |
| lock vs HEAD | 20 removed / 17 added / 47 changed, every row explained in the spec's P8 list |

One new transitive package appears in the lock: `agent-cli-detector 0.1.7`, a dependency of `@expo/cli 54.0.27` (Expo's own repo, no install script, build-time only, not in the app bundle).

## Process

RED (Opus) → orchestrator gate on spec + tests → GREEN (Opus) → two Opus adversaries → fix → orchestrator diff review.

- App Review adversary: SOUND. Icon legible at 60, 40 and 29 px; adaptive mark inside the 66 dp safe circle; no alpha or `tRNS` on the App Store icon (both mutants killed).
- Engineering adversary: one defect, a duplicate `expo-constants` (root 18.0.13 linked natively beside a nested 18.0.14). Fixed with `CI=1 npm update expo-constants`; the lock now has one 18.0.14 copy. 13 of 14 test mutants were killed and the survivor is an equivalent mutant.
- The RED test file was frozen after the gate. Its only later change is the removal of a stale name suffix on two tests (ruling RQ19).

## Wording and limits

- The App Store icon is **pixel-equivalent** to `assets/icon.png`, not byte-identical. Prebuild re-encodes it.
- The favicon is web-only. It is not a launch item.
- The transparent renders (adaptive, splash) are correct only over `#ffffff`, which is what `app.json` declares for both backgrounds.
- Not pinned by jest: the splash mark's position (a mutant that moved the mark to a corner with a matching manifest passed). The renderer's `--check` catches it and is not in CI yet.
- Out of scope by ruling RQ5, one follow-up issue: `ios.icon` dark and tinted variants, the `expo-notifications` icon, `android.adaptiveIcon.monochromeImage`, Android legacy-splash sizing.
- Out of scope by ruling RQ4: the in-app glyph still renders the old Q-ring (`QarenLogo`). That is unit U4c, OTA-capable, before the review build.
- A phone that had the old build installed can show the cached launch screen until the app is reinstalled. The launch runbook gets that note in the docs PR.
- `@expo/json-file` resolves at three versions inside the Expo toolchain. That is build-tool layout, not a native duplicate.

## After merge

- CLAUDE.md blocker #1 is updated in the session-71 docs PR.
- Follow-up issues: U4c; the RQ5 icon variants; a CI step for `python scripts/render_myez_icons.py --check` with a splash-position pin.
- The store build must be cut from a main that contains this PR.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
