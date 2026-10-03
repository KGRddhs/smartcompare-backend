# MYEZ research digest: U4b, OAI/obs, U4c, U3b, U8, U10

Read-only research, 2026-10-03. The specs are anchored at `94c097cd`. origin/main is now `5ed4f459`.

Each bullet gives a claim and then its source.

Precedence: this digest never overrides a BINDING review correction or orchestrator ruling. Where the research contradicts a spec, see "Corrections to the existing specs"; the orchestrator rules on those.

Abbreviations:
- `SA/` = `C:/Users/SynAckITPC/Documents/AI/sc-docs-70/docs/investigations/2026-09-30-session-70-state/`
- `nm/` = `SmartCompareApp/node_modules/`
- `venv/` = `C:/Users/SynAckITPC/Documents/AI/.venv-qaren/Lib/site-packages/`
- `py312/` = the CPython 3.12.9 `Lib/`
- `cli/` = `nm/@expo/cli/build/src/` (version 54.0.24)

Topic notes, with full evidence, live under `scratchpad/research/`:
- `repo-patterns/notes.md`
- `expo-sdk54-u4b/NOTES.md`
- `openai-asyncio-sentry-oai/NOTES.md`
- `rn-expo-u4c-mark/notes.md`
- `legal-u8-review-guidelines/NOTES.md`
- `eas-submit-u10-u3b/NOTES.md`

Tooling notes:
- context7 was available. It was used for the jest 29.7 virtual-mock rules, the Expo docs and the EAS docs.
- Legal texts were fetched live from the official pages.
- help.openai.com returned 403, so that article was read through the r.jina.ai text proxy.

---

## Repo conventions every unit must satisfy

### Patterns to follow
- **Rebase before you build.** Rebase onto origin/main `5ed4f459` and re-anchor every line reference. That commit is #278 (pyjwt 2.15.1 and urllib3 2.8.0; only `requirements*.txt` changed), and it clears the dependency-audit red. Docs PR #277 is open and mergeable. Source: `git ls-remote origin`; `gh api .../commits/7cae05e8`, `.../pulls/277`.
- **Required checks.** Exactly five are required: backend-lint, dependency-audit, frontend-typecheck, backend-tests and frontend-tests. `strict=false`. channel-freshness is NOT required. Source: `gh api repos/KGRddhs/smartcompare-backend/branches/main/protection/required_status_checks`.
- **Spec shape.**
  - The spec contains, in order: Base SHA with rev-parse proof, measured facts, Flags, R-requirements, and a RED table (with RED/PIN counts and mutation spot-checks).
  - Then: gates cheapest-first (versions and `[pyt]` lines pasted), stated limits, stop conditions and open questions.
  - It ends with "Review corrections (BINDING)" and then "Orchestrator rulings (BINDING)". Rulings override the review, which overrides the body.
  - Agents never edit the spec. A spec never reaches RED unreviewed.
  - Source: `SA/U4B_ICONS_DEPS_SPEC.md:11-24,389-600`; `SA/OAI_OBS_SPEC.md:283-500`; `CLAUDE.md:550(1)-(2),593`.
- **backend-tests**, in order:
  - The lock check. Edit a `.in` file and run `uv pip compile`; never hand-edit a lock.
  - `py_compile`, then the tiktoken cache warm-up.
  - ONE alphabetical process with `-m 'not (live_unit or live_db or integration)'`, `--timeout=60` and `--cov-fail-under=83`, deselecting the 11 nodes listed in `tests/.pre_impl_failures.txt:79-89`.
  - The netguard ratchet.
  - Report the result as "green with 11 known nodes deselected".
  - Source: `.github/workflows/ci.yml:39-133`; `CLAUDE.md:73-79,485`.
- **backend-lint.**
  - ruff==0.16.5 runs `--select E9,F63,F7,F82 --no-cache` over `app/ scripts/ tests/`.
  - `black==26.5.1 --check` blocks only for the paths in `.github/black-clean-paths.txt`. The list includes `app/services/prompt_personalities.py`, and `tests/test_ci_gates.py:324` verifies the list.
  - Source: `ci.yml:157-178`.
- **dependency-audit** is REQUIRED. `pip-audit -r requirements.txt --strict` blocks; `npm audit` is report-only. Source: `ci.yml:213-228`.
- **Hermetic default tier.**
  - conftest runs in this order: `load_dotenv(override=True)`, then the credential strip (placeholder keys and `*.invalid` hosts), then the netguard, all before any `app.*` import.
  - `_hermeticity` turns module-identity leaks into ERRORs.
  - Mock every network and LLM leg a test can reach.
  - Source: `tests/conftest.py:16,28-41`; `tests/_env_safety.py:110-157`; `tests/_netguard.py:7-62`; `tests/_hermeticity.py:1-31`.
- **Netguard ratchet.** A NEW test node with egress makes CI exit 1. The baseline is only ever generated with `--write`. Unit gate: no `[netguard]` line names a new node. Source: `scripts/netguard_ratchet.py:12-18,116-137`.
- **Zero-regression comm gate.**
  - Build the file set as the UNION of:
    - a module-reference grep over every module the unit touches;
    - the hand-added path scanners;
    - the unit's own new test files.
  - Run the set at BASE (in a detached scratch worktree) and at HEAD, in chunks of at most 25 files with a 1200 s bound.
  - `comm -13` the sorted FAILED **and ERROR** ids; the branch-only-new list must be EMPTY.
  - Also run the unit's CI-order set in ONE process.
  - Source: `CLAUDE.md:567,570(3),799-826,843-845`.
- **Bounded runner for every pytest.**
  - Command: `PYTHONIOENCODING=utf-8 <venv python> pyt.py --bound S --tag T --log F --cwd W -- <args>`.
  - Bounds: 600 s for a unit, pin or mutant run; 1200 s for a CI-order set or a comm chunk; 1800 s ceiling.
  - One pytest at a time. Paste the final `[pyt]` line.
  - A TIMEOUT is a measurement failure: re-run once, then report NOT MEASURED.
  - Use the venv `.venv-qaren` (on-lock 2026-10-03).
  - Source: `main:docs/investigations/2026-09-26-session-68-state/harness-2026-09-27/pyt.py:1-17,83-100`; `SA/scripts/s70-common.txt`.
- **pytest-asyncio 1.4.0 runs in STRICT mode.** Every async test needs `@pytest.mark.asyncio`, and every async fixture needs `@pytest_asyncio.fixture`. Source: `venv/pytest_asyncio/plugin.py:126-128,845-866`; `pyproject.toml:38-46`.
- **Backend test style.**
  - A module docstring names the spec and its R/T ids.
  - File name: `tests/test_s70_<topic>.py`.
  - Names the unit creates are imported INSIDE test bodies.
  - Sentinels are never sk-shaped.
  - Use `monkeypatch.setattr`/`delenv`, and `TestClient(app)` for routes.
  - Source: `tests/test_openai_key_log_hygiene_s69.py:1-45`; OAI review C3.
- **Mutation check for every fix.** Remove the fix and confirm the test reddens. Restore from a Python byte copy and compare sha256; never use `git checkout --`. Source: `CLAUDE.md:847`; `s70-common.txt`.
- **Line endings.**
  - `core.autocrlf=true`, there is no `.gitattributes`, and text files are `i/lf w/crlf`.
  - Edit with the Edit tool. A programmatic rewrite is re-derived from `git show HEAD:<path>`.
  - A whole-file diff in `git diff --stat` is a defect.
  - Generated text is written with `newline='\n'` and compared parsed, not as bytes.
  - Source: `git ls-files --eol`; `CLAUDE.md:322`; U4B RQ12.
- **The pre-commit hook** (`.githooks`) runs:
  - `py_compile` and the ruff tier;
  - black on allowlisted files;
  - a secret scan (`\bsk-[A-Za-z0-9_-]{20,}`, AKIA, xox, PEM private keys);
  - a refusal of any staged `.env`;
  - sqlfluff on migrations.
  - Source: `.githooks/pre-commit:14-86`.
- **Client CI.**
  - Steps: `npm ci`, the FULL `npx jest --ci`, eslint on `src/**/*.{ts,tsx}` (tests are not linted), `tsc --noEmit` (which covers `__tests__`), and the Expo drift step.
  - ts-jest uses `isolatedModules`, so a type error in a test passes jest and fails tsc.
  - Source: `ci.yml:230-310`; `SmartCompareApp/tsconfig.json:1-7`; `jest.config.js:11`.
- **Jest config.**
  - ts-jest preset, node environment, testMatch `**/__tests__/**/*.test.ts(x)`.
  - There are 20 `moduleNameMapper` shims; a new native or ESM import needs a shim.
  - `setup.ts` sets `__DEV__=false`, mocks aiConsent to `'granted'` and silences `console.warn`/`console.error`.
  - Source: `jest.config.js:2-79`; `__tests__/setup.ts:11-44`.
- **Copy assertions.**
  - The react-i18next mock returns the KEY and ignores `defaultValue`, so assert against the real `en.json`/`ar.json`. Keys are flat; EN has 1000 and AR has 1000.
  - These fences run in the full suite: `i18n.test.ts`, `no-missing-referenced-keys`, `no-deleted-keys`, `pluralFamilies.fence.w311`, `brand.myez.s69` and `copy-policy.test.ts` (with `.copy-policy.json`).
  - ESLint (screens and components only) enforces `i18next/no-literal-string`, literal a11y/placeholder/title/label attributes, `setError()` and `Alert.alert()`.
  - Source: `__mocks__/react-i18next.ts:1-43`; `__tests__/i18n.test.ts:4-50`; `eslint.config.js:38-113`; `CLAUDE.md:260,546`.
- **Client harness.**
  - Run the tools by path under `timeout`:
    - `timeout -k 15 600 node node_modules/jest/bin/jest.js --ci <paths>`;
    - the full suite under `-k 15 1500`;
    - `node node_modules/typescript/bin/tsc --noEmit`;
    - eslint on `git diff --name-only --relative`.
  - Print the versions first, and check that `@babel/core` and `.bin/jest` exist.
  - Run the FULL jest suite after any rebase.
  - Never `jest -u`; a `.snap` in the diff is a defect unless a ruling names it.
  - Source: `s70-common.txt`; `CLAUDE.md:322,522,549`; memory `feedback-rebased-client-unit-run-full-jest-before-pr`.
- **Mobile-touching units also run the backend tests that read the app.** 17 backend tests read SmartCompareApp, for example `test_events_allowlist_superset`, `test_ci_gates` and `test_security_regression`. A `ci.yml` edit also runs `test_ci_gates`, `test_channel_freshness` and `test_hermeticity_pins` through `pyt.py`. Source: `grep -rl SmartCompareApp tests/`; `CLAUDE.md:845`; U4B correction 8.
- **Flags.**
  - The reader is `<name>_enabled()`, reading the env per call with the truthy set `('1','true','yes','on')`. Default OFF.
  - Flag-OFF is byte-identical and pinned. Numeric knobs reject inf and nan.
  - "Unset in prod" is measured by the orchestrator, from variable NAMES only.
  - CLAUDE.md flag rows are written at merge by the orchestrator. Nothing flips without Ahmed.
  - Source: `app/services/extraction_service.py:1111-1113`; `CLAUDE.md:336,340,602,608`.
- **Commits and PRs.**
  - Commit message: `fix|feat(<area>): <what> (session NN Ux, audit <ids>)`, plus the Co-Authored-By trailer.
  - PR body: What changes / Process / Gates / Follow-ups, then the footer. Flagged units add a Flag row and an Activation gate.
  - Only the orchestrator commits, with `git commit -m msg -- <paths>`.
  - Source: `gh api pulls/252,258,274`; `CLAUDE.md:28`.
- **Agent rules.**
  - Run commands as `( cd <abs> && ... )`. Create files with Write/Edit.
  - Never commit, push, checkout, stash, reset, rebase or clean. The only git write allowed is a detached scratch worktree, and never one that needs `node_modules`.
  - No installs unless the spec assigns them (U4B RQ7). No network, Railway or `.env`.
  - Budgets: 2 h for green/fix agents, 90 min for red/adversary agents.
  - List every written file with its sha256.
  - Source: `s70-common.txt`.
- **Docs.**
  - SESSION blocks are records: append a dated `**SESSION NN CORRECTION (date):**` line, never rewrite.
  - Run `date` before writing any date.
  - Agents never edit CLAUDE.md.
  - Source: s69 `NEXT_SESSION_PROMPT.md` §6; `CLAUDE.md:522`.

### Pitfalls
- **Filename-keyword gate sets ship regressions.** One wave's set had 54 files and an empty failure set while the real regression sat elsewhere. Separately, an `importlib.reload` in a new test broke a by-name importer only in full-suite order. Source: `CLAUDE.md:799-826,844`.
- **`scripts/regression_gate_diff.py` cannot be the comm gate.** It counts only `FAILED ` lines, so ERRORs are invisible, and it exits 4 when the env is off-lock (undocumented). Source: `scripts/regression_gate_diff.py:20-23,90-122,284-290`.
- **Two RED-file traps.** A top-level import of a not-yet-created name makes the RED file a collection ERROR at base. A check placed after a failing assert never runs, so split it into its own PIN. Source: OAI review C3.
- **conftest sets flags ON.** It setdefaults `ENABLE_COHORT_PERSONALIZATION=true` and `ENABLE_REFERRAL_SYSTEM=true`, so a default-OFF assertion needs `monkeypatch.delenv`. The clone (which has `.env`) and a worktree differ. Never copy `.env` anywhere. Source: `tests/conftest.py:16,47,52`; `CLAUDE.md:281(c),(e),570(5)`.
- **CI order is not local order.** CI runs one alphabetical process at `--timeout=60`; local gates run chunks at `--timeout=120`. Cross-file pollution (#183, #185, #186) shows only in CI order. Source: `ci.yml:116-125`; `CLAUDE.md:567`.
- **Virtual mocks leak.** `jest.mock(path, factory, {virtual: true})` on an EXISTING module leaks into later files on the same worker; that is how #274 went CI-red. Reproduce with `--runInBand` in the worker's file order. Source: `CLAUDE.md:522`; context7 `/jestjs/jest` v29.7.0 JestObjectAPI.
- **Junction hazard.**
  - `git worktree remove --force` follows a `node_modules` junction and guts the shared install. Unlink it first with `cmd /c rmdir`, then verify `@babel/core`.
  - With `.bin` missing, `npx tsc` once fell through to a global TS 6.0.2 and printed a false green.
  - Source: `CLAUDE.md:322,520,549`; memory `feedback-junction-worktree-removal-hazard`.
- **Never `git checkout -- <file>` on uncommitted unit work.** It reverts to BASE and wipes the unit. Killed agents have left mutants on disk at least four times. The partial U4b and OAI RED files are UNVERIFIED (sha prefixes in RQ9 and OR2). Source: `CLAUDE.md:528,559,570(1),585`.
- **Node and npm differ from CI.** Locally Node 24.11.1 / npm 11.6.2; CI uses Node 20 / npm 10. CI's `npm ci` is the lockfile proof. Run `npm ls` before any `eas update`. Source: `node --version`; `ci.yml:203,237,284`; `CLAUDE.md:569`.
- **tsc type-checks `__tests__` but jest does not.** For example, `UNSAFE_getAllByType('TextInput')` passes jest and fails tsc with TS2345. Trust only the tsc exit code, never IDE diagnostics. Source: `jest.config.js:11`; `CLAUDE.md:68,306`.
- **setup.ts hides console output and grants consent.** A test that expects either needs an explicit spy, or `jest.requireActual` / a per-file `jest.unmock`, never a virtual mock. Source: `__tests__/setup.ts:18-44`.
- **eslint still excludes only the old brand.** `wordsExclude` lists `^Qaren$` and the old Arabic name, not the new Arabic brand, so an Arabic brand literal in JSX text is flagged. Source: `eslint.config.js:20-28`.
- **Known client flake.** `HistoryScreen.mobileJank.m21` failed 1 run in 3 at base; re-run it once alone before it counts. Full-suite baseline at `94c097cd`: 351/354 suites, 3428 passed, 15 skipped, 15 todo, 44 snapshots. Source: U4B §1.17, RQ11.
- **Windows and encoding.**
  - Parallel Bash calls share one shell; use subshells with absolute paths.
  - Pass `encoding='utf-8'` and set `PYTHONIOENCODING`.
  - Backticks inside double quotes execute, and unquoted heredocs mangle backslashes.
  - Workflow args arrive as a JSON string.
  - Use `--relative` for eslint paths.
  - A very long single Bash command fails with ENAMETOOLONG (measured while writing this digest); write large files with Write.
  - Source: `CLAUDE.md:281(h),488,520,522,550(3),570(4)`.
- **Local-vs-lock drift has misled before** (fastapi, sentry-sdk, uvicorn). Say which version each number came from, and re-check after the rebase onto `5ed4f459`. Source: `CLAUDE.md:487,848`.
- **Never dump prod secrets.** No Railway MCP or `railway variables`, no printed env values, no `cat .env`; variable NAMES only. Source: `CLAUDE.md:32,583`; memory `feedback-never-dump-prod-secrets-into-transcripts`.
- **Merging ships nothing to phones.** The store binary runs the JS it was built with. Install native deps with `npx expo install`. Source: `CLAUDE.md:70,81,94-97`.

---

## U4b: icons, SDK-54 patch bumps, gesture-handler removal

### Patterns to follow
- **Two expected-version maps.**
  - ONLINE uses the installed map, overridden by the remote `versions/latest`.
  - `EXPO_OFFLINE=1` uses only the installed `expo/bundledNativeModules.json`.
  - The cached API (2026-09-30) matches the spec's targets: expo ~54.0.37, expo-updates ~29.0.20, expo-font ~14.0.12, expo-localization ~17.0.9, expo-screen-capture ~8.0.10, react-native-svg 15.12.1, eslint-config-expo ~10.0.0.
  - Source: `cli/start/doctor/dependencies/getVersionedPackages.js:63-107`, `bundledNativeModules.js:82-97`; `~/.expo/versions-cache`.
- **What `--check` compares.** It checks the INSTALLED version, not the package.json range. For `expo` it flags only "behind" (`semver.ltr`); other packages use `semver.satisfies` with prereleases included. `--json` exits 1 on drift without ever prompting. Source: `cli/start/doctor/dependencies/validateDependenciesVersions.js:157-161,241-254`; `cli/install/checkPackages.js:118-136`; `cli/install/resolveOptions.js:25-26`.
- **`expo.install.exclude` is honoured by `--check`.** It logs "Skipped checking dependencies: ..." (suppressed under `--json`). A `name@x.y.z` entry stays excluded only while Expo's suggested range equals x.y.z. That is information only, because it conflicts with k3's exact pin. Source: `cli/install/checkPackages.js:94-96`; `validateDependenciesVersions.js:163-199`; expo sdk-54 `docs/pages/more/expo-cli.mdx`.
- **P3 is a two-stage install.** `npx expo install expo@~54.0.37 <rest>` installs expo, then respawns `npx expo install <rest>` under the NEW CLI (via cross-spawn, so `npx.cmd` works on Windows). It warns if port 8081 is busy and rejects `--check`/`--fix` (BAD_ARGS). Source: `cli/install/installAsync.js:113-187`; `cli/install/installExpoPackage.js:73-131`.
- **P4 saves the intended range.** `npm install --save-dev eslint-config-expo@~10.0.0` writes `"~10.0.0"`. `npx expo install eslint-config-expo` without `--dev` would add a duplicate under `dependencies`. Source: npm 11 `@npmcli/arborist/lib/arborist/reify.js` ~1300-1320; `nm/@expo/package-manager/build/node/NpmPackageManager.js:39-51,117-131`.
- **The installs leave app.json unchanged.** expo-updates is an auto-plugin; expo-font and expo-localization are already listed; expo-screen-capture has no `app.plugin.js`. Source: `@expo/prebuild-config getAutoPlugins()`; `cli/install/applyPlugins.js`.
- **runtimeVersion follows expo.version.** The appVersion policy uses `expo.version` (`'1.0.0'`). appVersionSource `remote` manages only buildNumber. So RQ2 (keep 1.0.0) keeps OTA runtime 1.0.0. Source: `nm/@expo/config-plugins/build/utils/Updates.js:96-98,146-148`; docs.expo.dev/build-reference/app-versions and /eas-update/runtime-versions.
- **expo-updates 29.0.17 to 29.0.20 changes only the native client and CLI.** Changes: key-file permissions, the iOS script phase, and rejection of asset keys containing a path separator. There is no manifest-format change, so a post-U4b OTA stays loadable by 29.0.17. Source: `CHANGELOG.md:3-40` in the expo-updates-29.0.20 tarball.
- **Correction 14 dates are now sourced.** 54.0.34 = 2026-04-27, .35 = 05-28, .36 = 07-15, .37 = 08-17. 54.0.37 fixes Android expo-fetch chunk ordering, which matters for SSE. Source: `raw.githubusercontent.com/expo/expo/sdk-54/packages/expo/CHANGELOG.md`.
- **Support for corrections 4(b) and 5.** @expo/cli 54.0.25-27 has no export-bundle-format change, and @expo/prebuild-config 54.0.9 has no icon or splash change. Source: the sdk-54 CHANGELOGs of `@expo/cli` and `@expo/prebuild-config`.
- **Optional native-surface evidence for the PR body.**
  - Run `EXPO_OFFLINE=1 node node_modules/@expo/fingerprint/bin/cli.js fingerprint:generate --platform ios` before P0 and after P8, then `fingerprint:diff`. Same box only.
  - Base: rc 0, 118 sources, hash `45995f02...`.
  - react-native-gesture-handler is an `rncoreAutolinkingIos` source, so it is linked in the 1.0.0 binary. Dropping its unimported JS dependency is OTA-safe.
  - Source: `nm/@expo/fingerprint` 0.15.5 `cli/build/cli.js:54-57`; `research/expo-sdk54-u4b/fingerprint_base_ios.json`.
- **No OTA changes the launcher icon or the native splash.** `icon.png`, `splash-icon.png` and `adaptive-icon.png` only reach native files through prebuild. Source: docs.expo.dev/eas-update/optimize-assets; `withIosIcons.js:47-57,140-153`.
- **How the iOS icon is generated.** One 1024 universal icon, resizeMode `cover`, `removeTransparency` except for dark, background `#ffffff`. Alpha is flattened on both the sharp and the jimp paths, so ITMS-90717 cannot be reached. The image cache is keyed by the source sha256. Source: `@expo/prebuild-config` 54.0.8 `withIosIcons.js:181-201`; `@expo/image-utils` 0.8.14 `Image.js:63-83`, `jimp.js:150-180`, `Cache.js:18-32`.
- **The legacy root `splash` key.** iOS uses imageWidth 200 with a 414x736 scaleAspectFit view; Android uses 200 dp in a 288 dp canvas. This holds only while expo-splash-screen is absent; its default imageWidth is 100. Source: `getIosSplashConfig.js:52-61`, `InterfaceBuilder.js:75-120`, `getAndroidSplashConfig.js:43-55`.
- **iOS caches the old splash** "for a day or two". Do the first device check on a fresh install. Source: `github.com/expo/expo/blob/sdk-54/packages/expo-splash-screen/README.md`.
- **Apple icon rules justify real MYEZ art.** The icon is 1024x1024, square, with no transparency (ITMS-90717). Guideline 2.1(a) bans placeholder content, 2.3.8 requires the icons to match, and 4.2.6 rejects template apps. Source: the HIG app-icons JSON; docs.expo.dev/develop/user-interface/app-icons; App Review Guidelines; developer.apple.com/forums/thread/93717; expo/expo#1086.
- **RQ1 confirmed.** eslint-config-expo 10.x is the SDK-54 line and 55.x the SDK-55 line. The installed 55.0.1 and 10.0.0 differ only in `package.json`. Keep the nested `globals` 16.5.0 in P8. Source: diff of the tarballs; sdk-55 `bundledNativeModules.json`.
- **R11 stands.** react-navigation 7's native-stack and bottom-tabs do not peer on RNGH; only the JS Stack navigator needs it. The app has 0 references to it. Source: `nm/@react-navigation/*/package.json`; reactnavigation.org/docs/stack-navigator.

### Pitfalls
- **`expo install --check` can rewrite package.json.** In an interactive TTY with `CI` unset, it asks "Fix dependencies?" with Yes as the default; Enter rewrites `package.json` and the lock. CI (`CI=true`) and agent Bash (no TTY) are safe. For local or orchestrator runs use `CI=1 npx expo install --check` or `--json`. Source: `cli/install/checkPackages.js:137-154`; `cli/utils/interactive.js`; `cli/utils/prompts.js:91-97`.
- **The report-only online step can pass offline.**
  - An HTTP non-OK response turns the step red.
  - A NETWORK failure instead calls `disableNetwork()`, which sets `EXPO_OFFLINE=1`; the check falls back silently and can pass.
  - Treat a run as online-verified only if its log lacks "Dependency validation is unreliable in offline-mode" and "Networking has been disabled".
  - Source: `cli/api/getVersions.js:22-24`; `getVersionedPackages.js:82-107`; `cli/api/rest/client.js:128-134`; `cli/api/settings.js:27-31`.
- **The offline gate has blind spots.** It cannot see `expo` itself: `bundledNativeModules.json` has 119 keys and no `expo`. Nor does it check the remote-only relatedPackages (babel-preset-expo, typescript, jest, @types/*). k1/k2 cover expo; correction 11's P8 check is the only guard for babel-preset-expo. Source: `node -e require('expo/bundledNativeModules.json')`; `getVersionedPackages.js:44-61`.
- **P3 rewrites package.json itself.** The versioned `npx expo install` writes LF, 2-space indent and a trailing newline, re-sorts dependencies with `localeCompare('en')`, then runs `npm install`.
  - The working copy flips from CRLF to LF. `git diff --stat` stays content-only under autocrlf, but the raw-byte sha changes.
  - P1's Edit-tool insertion survives, because key order is kept.
  - Source: `@expo/package-manager` 1.10.5 `NpmPackageManager.js:30-38,117-131`; `@expo/json-file` 10.0.14 `JsonFile.js:44-53,248-269`.
- **The store icon is not byte-identical to the repo file.** Prebuild re-encodes it, so the store AppIcon is pixel-equivalent to `icon.png` but not byte-identical. Source: `withIosIcons.js:181-201`; `@expo/image-utils Image.js:63-120`.
- **Android issues, accepted under RQ5 (file a follow-up).**
  - The legacy `ic_launcher` and `ic_launcher_round` are built from `adaptive-icon.png`, because the code uses `foregroundImage ?? icon`.
  - The prototype ink is 42.8x46.5 dp, below the 48 dp guidance.
  - The Android 16 QPR2 auto-themed icon (no monochrome layer) is untested.
  - Source: `withAndroidIcons.js:87-110,140-200,351-370`; developer.android.com adaptive-icon guide.
- **Fingerprints are sensitive to platform and package manager.** Use them only as a same-box diagnostic, and never switch the runtime policy to `fingerprint` in U4b. Source: expo/eas-cli#4137 (reported, not measured).
- **P3 also calls React Native Directory** (the new-arch check; it fails soft). Set `EXPO_NO_NEW_ARCH_COMPAT_CHECK=1` to keep network scope to the npm registry and the Expo API. Source: `cli/install/installAsync.js:124-127`; `cli/install/utils/checkPackagesCompatibility.js:27-54`.
- **`web.favicon` is web-only.** react-native-web is absent, so the favicon never reaches iOS, Android or an OTA. It is cosmetic, not a launch item. Source: `cli/export/favicon.js`; `cli/start/server/middleware/FaviconMiddleware.js`.

---

## OAI/obs: #265, #268, the Sentry empty-message fix and the gather fix

### Patterns to follow
- **openai 3.3.1 runs on httpx2 2.12.0, not httpx 0.28.1.** httpx 0.28.1 is used only by app code (Serper, extraction and url services). The spec's §0 empty-text table therefore applies to the Serper sites; the SDK wraps its own httpx2 errors. Source: `venv/openai-3.3.1.dist-info/METADATA:26`; `venv/openai/_base_client.py:37`; `venv/openai/_exceptions.py:6`.
- **SDK retry behaviour.**
  - The default `max_retries` is 2, which means 3 attempts.
  - Retried: timeouts (raised as APITimeoutError), other transport errors (raised as APIConnectionError), and status 408/409/429/>=500, unless the response has `x-should-retry: false` or Retry-After > 120 s.
  - Backoff is `0.5*2^n*(0.75..1)`, capped at 8 s. CancelledError is not caught.
  - With `OPENAI_MAX_RETRIES=1` live, `/url/*` goes from 3 attempts to 2. Put that line in the C7 PR body.
  - Source: `venv/openai/_constants.py:7-13`; `_base_client.py:413-416,801-866,1686-1747,1804-1806`.
- **`with_options` is an alias of `copy()`.** It returns a new client that shares the connection pool and leaves the parent unchanged. That is the right shape for the fallback at `extraction_service.py:2682` and for the R2.4 test. Source: `venv/openai/_client.py:1352-1461`.
- **openai exception text is never empty but loses the type.** The texts are `'Request timed out.'`, `'Connection error.'` and `"Error code: 429 - {...}"`. APITimeoutError is NOT a `builtins.TimeoutError`. exc_summary will render `'APITimeoutError: Request timed out.'`. Source: `venv/openai/_exceptions.py:34-112`; `_base_client.py:432-441`.
- **Why the httpx text is empty (confirmed in installed source).** `anyio.fail_after` raises a bare TimeoutError, httpcore re-raises it with `to_exc(exc) from exc`, and httpx does `mapped_exc(str(exc))`, which gives `ReadTimeout('')`. Source: `venv/anyio/_core/_tasks.py:154`; `venv/httpcore/_backends/anyio.py:24-32`; `venv/httpcore/_exceptions.py:8-15`; `venv/httpx/_transports/default.py:115-118`.
- **The gather mechanism, reproduced on 3.12.9.**
  - `_done_callback` sets the outer exception whenever `_cancel_requested` is set. The outer ends FINISHED, not cancelled.
  - When unretrieved, it reports "exception was never retrieved" on logger `asyncio` at ERROR, with exc_info.
  - Source: `py312/asyncio/tasks.py:716-728,767-818`; `py312/asyncio/futures.py:91-105,205-218,263-284`; `py312/asyncio/base_events.py:1785-1833`.
- **The R4 fix shape works.**
  - A done-callback `if not f.cancelled(): f.exception()` removes the report, and a later awaiter still gets CancelledError.
  - `add_done_callback` on a future that is already done runs through `call_soon`, i.e. on the next loop iteration.
  - Source: `py312/asyncio/futures.py:220-232`; `probe_asyncio.out` scenarios D and E.
- **sentry-sdk 2.68.1 logging behaviour.** Breadcrumbs start at INFO and events at ERROR. A record without exc_info becomes a message-only event with `logentry {message: template, formatted, params}`. WARNING and INFO records produce no event. Source: `venv/sentry_sdk/integrations/logging.py:26-27,121-142,264-335`; `venv/sentry_sdk/client.py:831-837`; `app/services/sentry_service.py:298-330`.
- **Server grouping is now VERIFIED, not recalled.**
  - Relay's `normalize_logentry` runs first, then `message_v1` groups on `message or formatted`.
  - Result: one issue per %-template.
  - Source: getsentry/relay `relay-event-normalization/src/logentry.rs`; getsentry/sentry `src/sentry/grouping/strategies/message.py`; docs.sentry.io/concepts/data-management/event-grouping.
- **Why there are five asyncio issues.** The "never retrieved" events carry an exception, so they group by exception and stack. That gives the five issues 1K, 1J, Y, 1N and 17. Source: `venv/sentry_sdk/integrations/logging.py:280-285`.
- **Post-deploy check for item 1 needs no OpenAI call.** The SDK logs the INFO line `'Retrying request to %s in %f seconds'` on logger `openai._base_client`, and it reaches Railway stdout. Source: `_base_client.py:1804`; `app/main.py:15`; `app/middleware/logging_config.py:31-50`.

### Pitfalls
- **The R2.4 rationale is wrong on 3.12.9.**
  - `wait_for(timeout>0)` runs the coroutine in the SAME task (`async with timeouts.timeout`), so a contextvar would reach the caller. Only `timeout <= 0` or a pre-wrapped future creates a new task.
  - The return-value carrier is still the right design. Do not copy the wrong rationale into code comments or the PR body.
  - Source: `py312/asyncio/tasks.py:472-503`; `probe_waitfor_ctx.out`.
- **The attached CancelledError comes from `children[-1]`**, the leaked loop variable, not from the last-finished child. If that child had completed normally, the error is fresh and has NO traceback. Tests should assert only on `context['message']`. Source: `py312/asyncio/tasks.py:796,813-818`; `py312/asyncio/futures.py:126-144`.
- **The C9 title check is too narrow.** Sentry updates a group's title from EACH event, so the title will show the latest type (e.g. `Search error: ConnectError`). Check for `<prefix><TypeName>` and one accumulating issue. Source: getsentry/sentry `src/sentry/event_manager.py` (`_process_existing_aggregate`), `src/sentry/eventtypes/base.py`.
- **One issue per template holds only while events carry no stack or exception.** Do NOT add `exc_info=True` at the 8 CHANGE sites. `attach_stacktrace=True` or a project fingerprint rule would also regroup the events. Source: `venv/sentry_sdk/client.py:831-837`; Sentry event-grouping docs.
- **Complimentary-token tier trap.**
  - Tier 1-2 orgs get only 250K/day for the gpt-4o group; Tier 3-5 get 1M.
  - The allowance is shared across the large-model group and across projects. Overage is billed at list price. The counter resets at 00:00 UTC.
  - Runbook §6 must state the tier dependency, and Ahmed reads the tier and enrolment before choosing `DAILY_4O_CAP`.
  - Source: help.openai.com/en/articles/10306912 (via proxy); `app/services/model_router_service.py:35-75`.
- **Exhausted credits still cost retries.** A 429 `insufficient_quota` is retried unless the response says `x-should-retry:false`. A Retry-After of 120 s or less makes the SDK sleep, and that sleep counts against outer `wait_for` deadlines (ENABLE_FULL_STREAM_DEADLINE). Source: `_base_client.py:801-866,1761-1770`; `_constants.py:13`.
- **respx and `httpx.MockTransport` do NOT intercept openai 3.x.**
  - Mock at `guarded_llm_create` / `chat.completions.create`, or pass `http_client=httpx2.AsyncClient(transport=httpx2.MockTransport(...))` with `max_retries=0`. Otherwise the test runs real backoff (about 0.5 s, then about 1 s).
  - Unmocked SDK calls trip the netguard.
  - Source: `METADATA:388-390`; `_base_client.py:1734-1747`.
- **Never repr or log the inner client.** `repr(client._client.timeout)` raises TypeError, although the legacy `httpx.Timeout` kwarg is safe for requests. Do not "fix" the timeout in this unit. Source: `_base_client.py:610-616,1470-1475`; `venv/openai/_httpx2.py` (`normalize_httpx_timeout`).
- **The 429-fallback trigger over-matches.** It is a substring test on `'429'`/`'rate'`/`'quota'`, and `'rate'` matches "generate" and "accurate". So `model_downgraded` can mark a non-429 failure. This is pre-existing; state it in §7 limits rather than fixing it here. Source: `app/services/extraction_service.py:2657-2668`.
- **The R4 callback retrieves ANY exception.** Its precondition is that every entry is a gather with `return_exceptions=True`. State that in the helper's docstring. Source: `py312/asyncio/tasks.py:767-790`.
- **C11 test-harness trap (reproduced).** A held reference defers `__del__`. Drop every reference, spin the loop, then `gc.collect()` INSIDE the handler scope. Source: `py312/asyncio/futures.py:91-105`.
- **Follow-up candidate (out of scope).** Quiet the `httpx2`/`httpcore2` loggers, which log every request at INFO. Source: `venv/httpx2/_client.py:110,1085,1923`; `app/middleware/logging_config.py:47-50`.

---

## U4c: the in-app MYEZ mark (replaces the QarenLogo SVG)

### Patterns to follow
- **Use RN's built-in `<Image>`, not expo-image.** expo-image is absent and native, so adding it needs a new build and breaks OTA under RQ2. Source: `SmartCompareApp/package.json`; `nm/expo/bundledNativeModules.json:49`; `app.json` runtimeVersion.
- **Load the PNG with a static `require`.** Write `require('../../assets/brand/myez-mark.png')` at module scope, never a dynamic path. Use `require`, not `import`: an import fails tsc with TS2307 because there is no `*.png` declaration. Source: RN docs `images.md`; `src/theme/fonts.ts:44-46`; `research/rn-expo-u4c-mark/tsprobe`; `nm/eslint-config-expo/flat/utils/typescript.js:84-96`.
- **Ship three scales.** @1x/@2x/@3x = 128/256/384 px RGBA. Metro picks the smallest scale at or above the device PixelRatio; the intrinsic size is the @1x pixel size. Source: metro `src/node-haste/lib/AssetPaths.js`, `src/Assets.js:173-180`; `nm/react-native/Libraries/Image/AssetUtils.js:16-30`.
- **Set size and resizeMode explicitly.** `style={{width: size, height: size}}` and `resizeMode='contain'` (the default is `'cover'`). Source: `Image.ios.js:133-142`; `Image.android.js:209-210`.
- **A required PNG ships by EAS Update.** app.json has no `assetPatternsToBeBundled`, and every scale is listed in `metadata.json` (measured). U4c is the first app-owned PNG the JS requires. Source: expo sdk-54 `eas-update/how-it-works.mdx`, `asset-selection.mdx`; `nm/@expo/metro-config/build/transform-worker/getAssets.js:45-53`; `SmartCompareApp/dist/metadata.json`.
- **No RTL flip.** RN never flips image sources. Do not use `rtlFlip` or `DirectionalIcon`. Source: RN blog 2016-08-19 (right-to-left support); `src/utils/rtl.ts:8-9`; `src/icons/index.ts:30-31`.
- **Hide the mark from accessibility, as QarenLogo does.** Set `accessible={false}`, `accessibilityElementsHidden` and `importantForAccessibility='no-hide-descendants'`. If a site should announce the brand, use `accessibilityLabel={t('app.name')}`; eslint rejects a literal label. Source: `src/components/QarenLogo.tsx:39-40`; `nm/react-native/Libraries/Image/Image.d.ts:147-150`.
- **What jest sees.** The PNG maps to `__mocks__/fileStub.ts`, so `require` returns `{__esModule: true, default: 0}`.
  - Assert the host `'Image'`, width/height, resizeMode and the a11y props.
  - Compare `source` with `toBe(require(samePath))`, never `toBe(0)`.
  - Source: `jest.config.js` moduleNameMapper; `__mocks__/fileStub.ts`; `__mocks__/react-native.ts:16-17`.
- **Cheapest path: keep the existing module.**
  - Keep `src/components/QarenLogo.tsx` with its path, default export and testIDs (`loading-rings-logo`, `welcome-qicon`, `mock-qaren-logo`).
  - Then only the 2 LoadingRings snapshots change.
  - Source: `__tests__/hero/__snapshots__/LoadingRings.test.tsx.snap:113,274`; `__tests__/components/hero/LoadingRings.test.tsx:21`.
- **Derive the PNGs deterministically from the U4b master.**
  - Use U4B §4.3 step 3 (inverse composite), then crop, pad and LANCZOS-resize.
  - Either extend `scripts/render_myez_icons.py` or add a sibling script with manifest entries and `--check`.
  - A prototype already reproduces the output deterministically.
  - Source: `SA/U4B_ICONS_DEPS_SPEC.md` §4.1-4.5; `scratchpad/u4c/proto_mark.py`.
- **Sizes at each site.** Splash 128, Step01Welcome 40, Home 28, Profile 28, History 24. LoadingRings uses `round(size*0.22)`: 70 at its default 320 and 26 at ResultsScreen's 120. Source: `SplashScreen.tsx:112`; `Step01Welcome.tsx:76`; `HomeScreen.tsx:900`; `ProfileScreen.tsx:355`; `HistoryScreen.tsx:939`; `LoadingRings.tsx:130,212`; `ResultsScreen.tsx:742`.

### Pitfalls
- **`tintColor` recolours every opaque pixel**, including the emerald dot. Drop the `color` prop rather than mapping it to tintColor. No src caller passes it; only QarenLogo.test case 5 tests it. Source: RN `image.md` (tintColor); grep of `<QarenLogo` in src.
- **Renaming or deleting `QarenLogo.tsx` breaks 11 suites at load.** A non-virtual `jest.mock` on an unresolvable path throws. `HomeScreen.cancelCompare.a4.test.tsx:211` also waits on the testID `'mock-qaren-logo'`. Source: `nm/jest-resolve/build/resolver.js:578-621`.
- **The launch screen to SplashScreen hand-off jumps.**
  - The native launch screen shows the mark centred at full opacity.
  - SplashScreen starts the mark at opacity 0 and scale 0.8, inside a stack with the wordmark and tagline, so the mark moves.
  - Apple's HIG asks for a launch screen that is nearly identical to the first screen.
  - Fix: start the mark at the launch size and position, at opacity 1, and animate only the text (needs a design ruling).
  - Source: Apple HIG "Launching"; `App.tsx:345-347`; `SplashScreen.tsx:42-43,60-63,111-114`.
- **The brand shows twice.** The mark spells MYEZ, and the English headers also render `t('app.name')` next to it (Home, Splash). Source: `HomeScreen.tsx:900-901`; `SplashScreen.tsx:112-113`.
- **The RN jest mock has no `useWindowDimensions`.** Use `Dimensions.get('window')` (mocked as 390x844), or extend the mock. Source: `__mocks__/react-native.ts:72-75,175`.
- **Do not route the PNG through react-native-svg.** The repo's svg mock lacks `Image`, `SvgXml` and `SvgUri`. Source: `__mocks__/react-native-svg.ts`.
- **The cut-out is exact only over white.** It is fine on `#FFFFFF` and `#F8F8FA`, but fringes on any dark or tinted background. Source: U4B §4.3 step 3, §7; `src/theme/index.ts:5-6`.
- **Snapshots versus the never-`-u` rule.** `jest --ci` never writes snapshots, and the repo forbids `jest -u`. The U4c spec must either explicitly authorise ONE `-u` on `LoadingRings.test.tsx` with a reviewed diff (the Svg subtree becomes Image), or rewrite those assertions. Source: `nm/jest-cli/build/args.js:150-155`; `s70-common.txt`.
- **The reviewer and the screenshots see the embedded JS.** An update applies on the next launch, so land U4c BEFORE the production build and the screenshots (Guideline 2.3). Source: `nm/expo-updates/ios/EXUpdates/UpdatesConfig.swift:236-249`; expo sdk-54 `updates.mdx`; U4B review Q4.
- **Device checks.** Check the hand-off on a fresh install (the iOS storyboard cache). On Windows, Metro may need a restart after new images are added. Source: U4B correction 7; RN docs `images.md`.

---

## U3b: AI consent and data sharing (waits on D3)

### Patterns to follow
- **The app sends no identifying OpenAI parameters.** An AST scan of 17 `create`/`guarded_llm_create` sites found no `store`, `metadata`, `user`, `safety_identifier`, `prompt_cache_key` or `service_tier`. Source: `research/openai-asyncio-sentry-oai/scan_llm_kwargs.out`; `app/services/model_config.py`.
- **OpenAI's data controls.**
  - API data is not used for training unless the org opts in.
  - Sharing can cover "all projects or only selected ones".
  - Abuse-monitoring logs are kept for up to 30 days.
  - ZDR is arranged through sales; under ZDR, `store` is treated as false, and ZDR orgs cannot opt in to sharing.
  - Source: developers.openai.com/api/docs/guides/your-data; help.openai.com 10306912 (via proxy).
- **Consent copy must stay consistent with the policy.**
  - `aiConsent.body` (en.json:695) says preferences, budget, country, language and area go to OpenAI.
  - Onboarding is at en.json:564-568.
  - `profile.aiSharing.subtitle` (en.json:417) disappears under D3 = A.
  - Source: `SmartCompareApp/src/i18n/en.json`.
- **Bump `AI_CONSENT_VERSION` to 2** if the consent purpose or text changes (needed under D3 = B). Source: KSA IR Art 11(1)(e); legal notes.
- **U3b changes JS and backend, so it must be on main before `eas build --profile production`.** Source: `nm/expo-updates/ios/EXUpdates/UpdatesConfig.swift:236-249` (launchWaitMs defaults to 0); `app.json` (no `fallbackToCacheTimeout`).

### Pitfalls
- **D3 = B (keep data sharing) collides with three rule sets.**
  - Apple 5.1.2(i) and (ii) limit sharing to improving the app or serving advertising, and bar repurposing without new consent.
  - KSA IR Art 11(1)(e) requires a separate consent for each purpose.
  - Bahrain PDPL Art 3(2) limits use to the original purpose.
  - If B is chosen, sharing needs its own opt-in (unset means off), not bundled with the processing consent, plus `AI_CONSENT_VERSION` 2.
  - D3 = A is the low-risk path.
  - Source: App Review 5.1.2; KSA IR Art 11(1)(e); Bahrain PDPL Art 3(2).
- **A second non-sharing key (option B) works only under "selected projects".** The private key's project must not be one of the selected projects. Source: help.openai.com 10306912.
- **Consent cannot be withdrawn in the app.** `aiConsent.ts:88-92` clears it only on account deletion, and D3 = A removes the only toggle. Apple 5.1.1(ii), Bahrain Order 48/2022 Art 6 and KSA IR Art 12(2) require withdrawal as easy as giving consent. Add a withdraw control. Source: `SmartCompareApp/src/services/aiConsent.ts:88-92`; `U3_AI_CONSENT_SPEC.md` (the word "withdraw" appears nowhere).
- **Consent is stored on the device only.** KSA IR Art 11(1)(d) requires a verifiable record (time and means), and Bahrain Order 48 Art 4 requires written or electronic explicit consent. Add a server-side consent record. Source: `U3_AI_CONSENT_SPEC.md` R3; KSA IR Art 11(1)(d).
- **Minors.** Consent requires full legal capacity (Bahrain Art 24(1)(a); KSA IR Art 11(1)(c)), but the app admits users from 13. Prefer contract necessity as the basis for core processing; counsel decides. Source: Bahrain PDPL Art 4, 13, 24; KSA PDPL Art 6; KSA IR Art 11, 13.
- **Chat Completions storage default is unclear.**
  - One OpenAI guide says completions are "stored by default for new accounts" (send `store: false`); the your-data table says "None". U3b should decide `store=False` explicitly.
  - Never send `metadata` or `user`. If an end-user id is ever needed, use a hashed `safety_identifier`.
  - Source: developers.openai.com/api/docs/guides/responses-vs-chat-completions; the your-data page; `venv/openai/types/chat/completion_create_params.py:135-143,254-262,303-310,361-368`.
- **Test trap.** setup.ts grants consent globally. Map it back with `jest.requireActual` or a per-file `jest.unmock`, never a virtual mock. Source: `__tests__/setup.ts:18-44`; `CLAUDE.md:522`.
- **There is no "fix it by OTA during review".** A production OTA needs a second cold start before it shows. Source: `UpdatesConfig.swift:236-249`; `CLAUDE.md:296`.

---

## U8: privacy policy and terms redraft

The redraft waits on eight inputs:
- I1: the controller
- I2: the CR number
- I3: the postal address
- I4: the emails
- I5: the response time
- I6: the effective date
- I7: D3
- I8: lawyer review and the Beta label

### Patterns to follow (the MUST list)
- **M1, controller identity (I1-I3).**
  - Give the full legal name, field of activity and postal address. The policy's "we" must be the App Store seller, the ASC copyright holder and the IP owner.
  - Gaps: `app/legal/privacy_policy.md:11`, `landing/privacy.html:199` and `landing/ar/privacy.html:193` say "Qaren operates"; `terms_of_service.md:41,56` name Qaren as owner and party; there is no address anywhere.
  - Source: Bahrain PDPL Art 17(1)(a); KSA PDPL Art 13(3); KSA IR Art 4(1)(a); App Review 1.5, 5.2.1; ASC "Copyright" field.
- **M2, contact (I3, I4, D14).**
  - Give a monitored privacy email and a postal address. The Support URL must lead to real contact details. Publish the objection procedure.
  - Gaps: `privacy_policy.md:92-93` gives an email only; `landing/support.html:196-207` has no name or address.
  - Source: the ASC Support URL definition; KSA IR Art 4(1)(a), 10; Bahrain Order 48/2022 Art 7.
- **M3, a full data inventory.**
  - Keep it consistent with `docs/privacy-data-inventory.md` (13 rows, equal to app.json) and with the ASC label.
  - Items: email; name and the Apple full-name scope; photos; typed products; link page text; search history; user ID; the fingerprint hash; the Expo push token; interaction events (which feed behavior_profile); Sentry data; demographics and preferences; Contact-Us messages; consent records.
  - Gaps: `privacy_policy.md:16-23,30-36`.
  - Source: App Review 5.1.1(i); DPLA 3.3.3(C); KSA PDPL Art 12; Bahrain PDPL Art 17(1)(b).
- **M4, legal basis.** Give a legal basis per purpose, say which fields are mandatory and which optional, and say what happens if a user does not provide them (I8, I1). Source: KSA PDPL Art 13(1),(2),(5); KSA IR Art 4(1)(c),(g); Bahrain PDPL Art 4, 17(1)(c)(2).
- **M5, processors.**
  - Name every processor and its purpose, and add an equal-protection sentence.
  - Gap: `privacy_policy.md:41` omits Expo push, Google and Apple sign-in, Bright Data, Firecrawl, Scrape.do, Cloudflare and the YouTube Data API.
  - Written processor contracts are Ahmed's to arrange.
  - Source: App Review 5.1.1(i); Bahrain PDPL Art 8(3), 17(1)(c)(1); KSA PDPL Art 8, 13(4); KSA IR Art 17.
- **M6, a third-party AI section (I7).**
  - Match the shipped copy (en.json:695, 564-568). Say what goes to OpenAI and what does not, that permission is asked before first use, that there is no training unless the org opts in, and that abuse logs are kept up to 30 days.
  - Replace §11 (`privacy_policy.md:80-88`).
  - Source: App Review 5.1.2(i) (developer.apple.com/news/?id=ey6d8onl, 2025-11-13); OpenAI your-data page.
- **M7, cross-border transfers.**
  - Name the destinations and the transfer basis: OpenAI is in the US, the Sentry client ingests in Germany (`*.ingest.de.sentry.io`), and the other regions are unknown.
  - Bahrain Order 42/2022 lists the US (row 80) and Germany (row 27) as adequate.
  - Gap: `privacy_policy.md:72-74`.
  - Source: KSA PDPL Art 13(4), 29; KSA Transfer Regulation v2.0 Art 2(2); Bahrain PDPL Art 12-13; Order 42/2022.
- **M8, retention.**
  - Give retention per category, including what survives deletion (admin_audit_log, OpenAI abuse logs, Sentry, backups) and how long deletion takes.
  - Gaps: `privacy_policy.md:44-49`; `terms_of_service.md:65`.
  - Source: App Review 5.1.1(i); Apple's account-deletion page; KSA IR Art 4(1)(d); KSA PDPL Art 18; Bahrain PDPL Art 3(5).
- **M9, rights.**
  - List the rights with their deadlines, and the complaint routes: Bahrain's PDPA, and Saudi Arabia's SDAIA (90-day window).
  - Gap: `privacy_policy.md:51-58`.
  - Source: Bahrain PDPL Art 18-25; KSA PDPL Art 4, 34; KSA IR Art 3, 37.
- **M10, withdrawal.**
  - Describe a real withdrawal mechanism.
  - Gaps: "Stop using the App" (`privacy_policy.md:58`) does not count, and `:88` promises a toggle that routes nothing.
  - Source: App Review 5.1.1(i),(ii); Bahrain PDPL Art 24(3), Order 48/2022 Art 6; KSA PDPL Art 5(2); KSA IR Art 12(2).
- **M11, account deletion.**
  - Give the path (Profile gear, then EditProfile, then Delete account), what is kept and what deleted, and the timing.
  - Sign in with Apple tokens should be revoked (U11).
  - Gap: `privacy_policy.md:56`.
  - Source: App Review 5.1.1(v); Apple's account-deletion page.
- **M12, re-engagement pushes (D10).**
  - Disclose them and the opt-out.
  - Gap: today only `terms_of_service.md:89-91` describes them.
  - Source: Bahrain PDPL Art 17(1)(c)(4), 19-20; KSA PDPL Art 25; KSA IR Art 28-29.
- **M13, age (I8).**
  - The age statement must match the 13+ rating and the sign-up attestation, and say how users without full legal capacity are handled.
  - Gap: `privacy_policy.md:68-70` covers under-13s only.
  - Source: App Review 5.1.4; Bahrain PDPL Art 24; KSA IR Art 11(1)(c), 13.
- **M14, security.**
  - Describe the security measures and commit to notifying users of a breach.
  - Gap: `privacy_policy.md:60-66` has no breach commitment.
  - Source: App Review 1.6; DPLA 3.3.3(C); KSA PDPL Art 20; KSA IR Art 24 (72 h to SDAIA); Bahrain PDPL Art 8.
- **M15, publication.**
  - Remove every DRAFT and legal-counsel line:
    - `privacy_policy.md:5,7,95`;
    - `terms_of_service.md:5,7,98`;
    - landing `privacy.html:195-196,288` and `terms.html:184-185,275`;
    - landing `ar/privacy.html:189-190,282` and `ar/terms.html:175-176,266`.
  - The effective date is the publication date (I6).
  - Bump these together: `legal_routes.py:30,47`, `consent.ts:12`, `consent_service.py:31` and `tests/test_consent_capture_w3_16.py:39`. `test_b12` at `:531-545` pins them.
  - Source: App Review 2.1(a); KSA IR Art 4(6).
- **M16, reachability.**
  - The policy must be easy to reach in the app, and its URL must be in ASC (it can be localised EN/AR).
  - Gap: `LegalScreen.tsx:32-35,53` always loads English; add a language parameter.
  - Source: App Review 5.1.1(i); ASC "Manage app privacy"; DPLA 3.3.3(C).
- **M17, Terms of Service.**
  - Name the real counterparty with contact details, and make the IP owner the publisher.
  - Drop the subscription promise (`:85`). Make the deletion clause accurate (`:65`). Align governing law with the controller's location (`:73-79`).
  - If the Terms are ever uploaded as a custom EULA, they must carry Apple's minimum EULA terms.
  - Source: App Review 5.2.1, 2.3.1(a); the DPLA minimum EULA terms; ASC App Information "License Agreement".

### Pitfalls
- **A 30-day response time (I5) breaks Bahrain's deadlines.** Bahrain requires 15 working days for access (Art 18) and 10 working days for objection, rectification, blocking and erasure (Art 20, 21, 23). KSA allows 30 days plus 30 (IR Art 3). One SLA can satisfy both only at 10 working days or less for correction, erasure and objection, and 15 or less for access. Source: pdp.gov.bh `regulations.pdf`; SDAIA Implementing Regulation.
- **A "Beta" or "early access" label (I8, decisions row 15) conflicts with App Review 2.2.** Betas belong in TestFlight. Source: App Review Guidelines 2.2.
- **Today's deletion promises are untrue.**
  - `delete_user_cascade` keeps `admin_audit_log` and the users row.
  - It does not null `demographics_profile`, `display_name`, `email` or the consent columns.
  - Sign in with Apple tokens are never revoked.
  - Source: `migrations/025_delete_user_cascade_completeness.sql:28-66`; `013_demographics_cohort.sql:19`; `app/services/auth_service.py:980-988`.
- **Bahrain prior notification.** Bahrain Art 14(1) requires notice to the PDPA before automated processing, unless a Data Protection Guardian is appointed (Order 44/2022). This applies if the controller is in, or does business in, Bahrain (Art 2(2)). It is the controller's duty. Source: Bahrain PDPL Art 2(2), 10, 14; Order 44/2022 Art 2.
- **ASC URL changes release with the next app version.** Settle the privacy URL and domain (D14) before submission. Source: developer.apple.com/help/app-store-connect/manage-app-information/manage-app-privacy.
- **The in-app policy has three weaknesses.**
  - It is English only.
  - It depends on the backend being up.
  - Offline, it shows the cached copy, which may be the DRAFT.
  - Add language selection and a bundled or landing-URL fallback.
  - Source: `LegalScreen.tsx:32-62`; App Review 5.1.1(i).
- **The documents must match each other and the app copy** (en.json:417, 564-568, 695). Today §11 cites the PDPL for an opt-out the code does not honour, and `landing/ar/privacy.html:273` contains garbled Arabic, which needs the AR native review (D11). Source: those lines; App Review 5.1.1(i), 5.1.2(i).
- **KSA PDPL applies wherever the controller is.** Art 2(1) covers KSA residents' data, and the listing targets Saudi users. If the KSA storefront is on, the KSA elements are needed. Source: KSA PDPL Art 2(1); `APP_STORE_LAUNCH_RUNBOOK.md:312`.
- **A KSA DPO may be required.** It is mandatory only in the IR Art 32 cases, but behavioural tracking counts as "regular and systematic monitoring", and behavior_profile could trigger a DPO and an impact assessment. Counsel decides. Source: KSA IR Art 25, 32; SDAIA DPO Rules Art 5.
- **Cite the right source for token revocation.** Guideline 5.1.1(v) does not mention it; the requirement comes from Apple's account-deletion page, and it says "should". Source: App Review 5.1.1(v); developer.apple.com/support/offering-account-deletion-in-your-app.

---

## U10: eas.json `submit.production` (plus U11, Sign in with Apple revocation)

### Patterns to follow
- **Option A (recommended): the key stored on EAS.**
  - The block is `"submit":{"production":{"ios":{"ascAppId":"<digits as a QUOTED string>","appleTeamId":"8K562M549D"}}}`, with no `ascApiKey*` fields, so the key comes from EAS.
  - It passes both schemas of the installed eas-json.
  - Source: `@expo/eas-json/build/submit/schema.js:23-65`; `eas-cli/build/submit/ios/IosSubmitCommand.js:101-126`; docs.expo.dev/app-signing/security; `validate_submit.js` case A.
- **Option B: a local .p8 key.** Set all three `ascApiKeyPath`, `ascApiKeyIssuerId` and `ascApiKeyId`, or none. These three are `$ENV`-expanded, so commit `"$ASC_API_KEY_PATH"` and the like, never an absolute path. Source: `eas-json submit/resolver.js:68-79`, `types.js:15-19`; `AscApiKeySource.js:78-89`; case E.
- **The real validity gate is the RESOLVED submit schema** (`EasJsonUtils.getSubmitProfileAsync(accessor,'ios','production')`). It enforces:
  - ascAppId matches `/^\d+$/` and is a string;
  - appleTeamId matches `/^[\dA-Z]{10}$/`;
  - the key id is uppercase;
  - the issuer is a UUID.
  - Source: `@expo/eas-json/build/utils.js:73-86`; `submit/schema.js:39-65`.
- **Where to find ascAppId.** ASC > App Information > General Information > "Apple ID". Once it is set, `eas submit` skips app creation. Source: docs.expo.dev/submit/ios; docs.expo.dev/eas/json.
- **Pre-submit order.**
  1. The Account Holder signs the latest DPLA. The Paid Apps agreement is needed only for a paid app or IAP.
  2. Create the app record for `com.qaren.app`.
  3. An Admin creates a Team ASC key. The .p8 downloads only once; record the Key ID and Issuer ID.
  4. Commit U10 and validate it with the resolved schema.
  5. Run `eas credentials -p ios` for production.
  6. Confirm the EAS `production` environment holds the build secrets.
  7. Run `eas build -p ios --profile production` from a main that has every reviewer-visible change.
  8. Run `eas submit -p ios --profile production --id <build id>`.
  9. Do a TestFlight internal smoke test on that exact binary.
  10. Complete the ASC metadata, privacy, age rating, review notes and demo account, then Submit for Review.

  Source: ASC help "Add a new app", "Sign and update agreements"; expo/fyi `creating-asc-api-key.md`; docs.expo.dev/submit/ios, /deploy/submit-to-app-stores.
- **Ahmed can run builds without Hussain's Apple ID.** Set `EXPO_ASC_API_KEY_PATH`, `EXPO_ASC_KEY_ID`, `EXPO_ASC_ISSUER_ID`, `EXPO_APPLE_TEAM_ID=8K562M549D` and `EXPO_APPLE_TEAM_TYPE=INDIVIDUAL`. Source: docs.expo.dev/build/building-on-ci; `eas-cli/build/credentials/ios/appstore/resolveCredentials.js:31-111`.
- **Remote versioning.** EAS bumps only the buildNumber; the version stays `expo.version` 1.0.0. `autoIncrement:'version'` is rejected. Source: docs.expo.dev/build-reference/app-versions; `eas-cli/build/build/ios/build.js:71-73`; `build/ios/version.js:206-271`.
- **Channels and hotfixes.**
  - The first production build creates channel `production`, linked to branch `production`.
  - Hotfix with `eas update --branch production --environment production`. Without `--environment`, no EAS variables are loaded, only local `.env`; the flag also forces a cache clear.
  - An update applies only on an exact platform and runtime match.
  - Source: `eas-cli/build/build/runBuildAndSubmit.js:261-285`; `update/utils.js:252-264`; `commands/update/index.js:190-196,532`.
- **Prefer `eas submit --id <build id>` over `--latest`.** `--latest` takes any store build, including one still in progress. Use the profile's `groups` and `--what-to-test` for TestFlight. Source: `eas-cli/build/submit/utils/builds.js:6-29`; `commands/submit.js:15-70`.
- **TestFlight.**
  - EAS only uploads; the build appears after about 10-15 minutes and is never submitted for review automatically.
  - Internal testing: up to 100 ASC users, no Beta App Review.
  - External testing: up to 10,000 testers; the first build is reviewed.
  - Builds last 90 days. Ahmed needs an ASC role on Hussain's team to be a tester.
  - Source: docs.expo.dev/deploy/submit-to-app-stores; ASC TestFlight overview and "Add internal testers".
- **The toolchain is met.** Apple has required Xcode 26 and the iOS 26 SDK since 2026-04-28. The EAS SDK-54 image is `macos-sequoia-15.6-xcode-26.0`, and there is no image override. Source: developer.apple.com/news/upcoming-requirements; docs.expo.dev/build-reference/infrastructure.
- **U11 revocation flow.**
  - Exchange the `authorizationCode` (single-use, valid 5 minutes) at `/auth/token`.
  - At deletion, POST `/auth/revoke` with:
    - `client_id = com.qaren.app`;
    - the token and `token_type_hint`;
    - `client_secret`, an ES256 JWT: kid = the SIWA key, iss = the Team ID, aud = `https://appleid.apple.com`, sub = the client_id, exp at most 6 months ahead.
  - expo-apple-authentication 8.0.8 already returns `authorizationCode`.
  - Source: Apple DocC revoke-tokens, generate-and-validate-tokens, creating-a-client-secret; `nm/expo-apple-authentication/build/AppleAuthentication.types.d.ts:145-150`.

### Pitfalls
- **A placeholder ascAppId passes every cheap check.** `"<numeric Apple ID>"` passes JSON parse, the top-level schema and `eas config`, and fails only at submit. An unquoted number fails with "must be a string", and a lowercase team id fails too. Source: `validate_submit.js` cases C, D, F; `submit/schema.js:51-57`.
- **`EXPO_APPLE_APP_SPECIFIC_PASSWORD` in the environment silently overrides every ASC key source.** Keep it unset. Source: `IosSubmitCommand.js:77-100`.
- **The first submit must be interactive.** A partial `ascApiKey*` triple throws in `--non-interactive`, and so does a missing EAS-stored key. Run the first submit or `eas credentials` interactively in a real terminal (Ahmed). Source: `IosSubmitCommand.js:113-125`; `SetUpAscApiKey.js:33-41`.
- **A missing ascAppId lets submit create the app itself.** It logs into Hussain's Apple ID and creates the app named "MYEZ" (not the planned "MYEZ - Compare Smart"), en-US, with an auto-generated SKU. Create the record by hand first. Source: `eas-cli/build/submit/ios/AppProduce.js:13-68`.
- **A production build can fail where every preview passed.**
  - EAS variables are per environment, so a preview-only `SENTRY_AUTH_TOKEN` is missing from the store build.
  - The @sentry/react-native 7.2.0 Xcode phase then exits 1, unless `SENTRY_DISABLE_AUTO_UPLOAD` or `SENTRY_ALLOW_FAILURE` is set.
  - Source: `eas-cli/build/build/evaluateConfigWithEnvVarsAsync.js:24-68`; `nm/@sentry/react-native/scripts/sentry-xcode.sh:49-75`.
- **The store build and the 2026-07-04 preview binaries share runtime 1.0.0, with different native code.**
  - Channels keep production OTAs away from the preview fleet.
  - But a preview OTA from a post-U4b main lands on the old binaries; follow U4B Q2 and correction 4.
  - Bump `expo.version` for every native change from the first production build on.
  - Source: `Updates.js:96-98`; `SA/U4B_ICONS_DEPS_SPEC.md:462-469,508`.
- **Never override the build image.** Apple rejects builds made with Xcode older than 26. Source: developer.apple.com/news/upcoming-requirements.
- **Remote build numbers.**
  - Under remote versioning, an `ios.buildNumber` in app.json is ignored with a warning, but it still shows in expo-constants.
  - The remote build number is shared per bundle id across preview and production.
  - The first initialisation reads `'1'` and does not increment it; the docs say 2, but the installed source wins.
  - Source: `remoteVersionSource.js:71-73`; `build/ios/version.js:206-243`.
- **U11 cannot work with today's sign-in.**
  - The app discards the authorizationCode: `authService.ts:1033-1080` posts only `id_token` and nonce.
  - Backend deletion only cascades and calls `admin.delete_user` (`auth_service.py:980-986`). Supabase does not revoke Apple tokens (supabase/auth#1308).
  - Either exchange the code at sign-in and store the refresh token encrypted server-side, or re-authenticate with Apple at deletion.
- **eas-cli is far behind.** 18.8.1 is installed and npm latest is 24.10.0, but the submit schema is identical, so the U10 block does not depend on the version. Upgrading is a package install and Ahmed's call. Source: registry.npmjs.org/eas-cli; eas-cli main `packages/eas-json/src/submit/schema.ts`.

---

## Corrections to the existing specs

### U4B_ICONS_DEPS_SPEC.md (`SA/`)
1. **`:196-200` (§1.13 CI comment; P5 and G3 lean on it).**
   - Spec: "`expo install --check` exits 1 on drift and never writes".
   - Correction: true only when `CI` is set or stdout is not a TTY. In an interactive terminal it prompts "Fix dependencies?" (default Yes) and rewrites `package.json` and the lock.
   - Action: orchestrator and manual runs use `CI=1 ... --check` or `--json`, and the rewritten CI comment must not repeat the claim.
   - Source: `cli/install/checkPackages.js:137-154`; `cli/utils/interactive.js`; `cli/utils/prompts.js:91-97`.
2. **`:552` (Q3 review).**
   - Spec: "a blocking online step ... goes red on an Expo API outage".
   - Correction: true only for HTTP errors. A network-level failure sets `EXPO_OFFLINE` and passes with a warning.
   - Action: the report-only step counts as online-verified only if its log lacks the offline warnings.
   - Source: `cli/api/rest/client.js:128-134`; `cli/api/settings.js:27-31`; `getVersionedPackages.js:82-107`.
3. **`:554`, and k5 at `:414` ("the in-jest twin").**
   - Spec: "The offline step ... still catches every drift a repo change can introduce".
   - Correction: true only for native modules. The offline map has no `expo` key and none of the relatedPackages (babel-preset-expo, typescript, jest, @types/*).
   - Action: k1/k2 guard expo; correction 11's P8 check is the only guard for babel-preset-expo.
   - Source: `nm/expo/bundledNativeModules.json` (119 keys); `getVersionedPackages.js:44-61`.
4. **`:581` (RQ12).**
   - Spec: "every edit goes through the Edit tool".
   - Correction: this cannot hold for `package.json`. P3's `npx expo install` rewrites the file (LF, 2-space indent, re-sorted dependencies) and runs `npm install`.
   - Action: P1's Edit survives. Gate R12/G10 on the parsed JSON plus content-line `git diff --stat`, not on raw bytes.
   - Source: `@expo/package-manager` 1.10.5 `NpmPackageManager.js:30-38,117-131`; `@expo/json-file` 10.0.14 `JsonFile.js:44-53,248-269`.
5. **`:160` (§1.11).**
   - Spec: "the repo asset is exactly what the App Store gets".
   - Correction: prebuild re-encodes the icon, so the store file is pixel-equivalent but not byte-identical. Reword it in the PR body.
   - Source: `withIosIcons.js:181-201`; `@expo/image-utils Image.js:63-120`.
6. **R3 `:255-259` and b6 `:399` (favicon).**
   - Correction: `web.favicon` is web-only, because react-native-web is absent from the app, so the favicon never ships to iOS, Android or an OTA. Keep the test, but do not present it as a launch item.
   - Source: `cli/export/favicon.js`; `cli/start/server/middleware/FaviconMiddleware.js`.
7. **`:576` (RQ7 network scope). An addition, not a contradiction.**
   - P3 also contacts React Native Directory. Set `EXPO_NO_NEW_ARCH_COMPAT_CHECK=1` if the scope must be only the npm registry and the Expo API.
   - Source: `cli/install/installAsync.js:124-127`.

### OAI_OBS_SPEC.md (`SA/`)
1. **`:101` (R2.4 "Why a contextvar would not work").**
   - Spec: `wait_for` "is a new task with a COPIED context".
   - Correction: false on 3.12.9 when timeout > 0; the coroutine runs in the same task.
   - Action: R2.4 is unchanged, but correct the rationale and keep it out of code comments and the PR body.
   - Source: `py312/asyncio/tasks.py:472-503`; `probe_waitfor_ctx.out`.
2. **`:238` (item 4 mechanism).**
   - Spec: "the last finished child task's own cancellation".
   - Correction: it is `children[-1]`, the leaked loop variable. If that child completed normally, the error is fresh and has NO traceback.
   - Action: tests assert only on `context['message']`.
   - Source: `py312/asyncio/tasks.py:796,813-818`; `probe_asyncio.out` A and B.
3. **`:450` (C9).**
   - Spec: grouping is "recalled, not measured".
   - Update: now VERIFIED from the Relay and Sentry source and docs (template grouping holds).
   - Source: relay `logentry.rs`; sentry `grouping/strategies/message.py`.
4. **`:451` (C9 post-deploy check).**
   - Spec: "confirm that its title reads `Search error: ReadTimeout`".
   - Correction: the group title updates on every event.
   - Action: check `<prefix><TypeName>` and a single accumulating issue.
   - Source: sentry `event_manager.py` (`_process_existing_aggregate`); `eventtypes/base.py`.
5. **`:440` C6(a) and `:156` R2.9.**
   - Spec: assumes "a 1M/day complimentary gpt-4o allowance".
   - Correction: the allowance is 1M only for Tier 3-5 orgs; Tier 1-2 get 250K/day, shared across the large-model group and projects.
   - Action: runbook §6 states that the tier and the enrolment are unmeasured and Ahmed's to read.
   - Source: help.openai.com 10306912 (via proxy).
6. **§0 `:26-33` (scope clarification, not a reversal).**
   - The empty-text table holds for httpx 0.28.1 (the Serper and Upstash sites). The openai SDK sites raise typed, non-empty openai errors over httpx2.
   - Action: SDK-path tests mock at `guarded_llm_create`/`create`, or use an httpx2 MockTransport with `max_retries=0`, never respx or `httpx.MockTransport`.
   - Source: `venv/openai-3.3.1.dist-info/METADATA:26,388-390`.
7. **§7 stated limits (an addition).**
   - Add the pre-existing `'rate'` substring over-match in the 429-fallback trigger, which can set `model_downgraded` after a non-429 failure.
   - Source: `app/services/extraction_service.py:2657-2668`.

### Other docs the research contradicts (outside the two specs)
- **Runbook §4, row U10.** Its gate ("`eas config` / JSON parse passes") is insufficient; validate with the resolved submit schema. Source: `validate_submit.js` C, D, F.
- **Runbook §5.** The literal `ascApiKeyPath` example should use the `$ENV` form or the EAS-stored key. Source: `eas-json types.js:15-19`.
- **Audit LL-7.** It says ASC URLs are editable later without a new binary, but URL changes release with the next app version. Source: ASC "Manage app privacy".
- **Decisions row 15 and input I8.** A "Beta / early access" label conflicts with App Review 2.2.
- **Input I5.** A 30-day SLA breaks Bahrain PDPL Art 18, 20, 21 and 23.
- **Runbook row on react-navigation and RNGH.** It is wrong; R11 already overrules it. Source: `nm/@react-navigation/*/package.json`.

---

## Open questions / could not verify

**Repo / harness**
- Is adding every new `.py` file to `black-clean-paths.txt` binding? The header says "should", and only RQ6 binds it, for the U4b renderer.
- The pre-commit hook calls the PATH python, ruff and black, not the venv. Whether the global ruff is 0.16.5 and black 26.5.1 was not checked; a missing ruff gives only a WARNING.
- A unit's effect on the 83% coverage floor was not measured.
- Do the rebased comm gates need a fresh BASE run at `5ed4f459`? That is the orchestrator's call.
- `pyt.py`'s ERROR-line parsing was read but not exercised. Do any of U3b/U8 touch `prompt_personalities.py`, which is black-allowlisted?

**U4b**
- During P3, will npm REPLACE babel-preset-expo 54.0.10 with 54.0.12 or NEST it under expo? Correction 11's P8 check decides.
- Which @expo/prebuild-config does P3 resolve, 54.0.8 or 54.0.9?
- Do EAS workers generate icons with sharp or jimp? Pixel output across the two was not compared.
- The App Store Connect no-alpha rule is sourced from ITMS-90717 reports; the HIG was read through its JSON endpoint.
- The online drift checks (P5, G3 online) and expo-doctor (G4) were not run. The expectations come from API responses cached on 2026-09-29/30.
- The fingerprint was measured at base, in the clone only.

**OAI/obs**
- Does OpenAI send `x-should-retry:false` or Retry-After on a 429 `insufficient_quota`? That needs a live call, which is forbidden.
- What are the org's usage tier, its data-sharing enrolment and the sharing scope? These are in the dashboard and are Ahmed's to read.
- Does traffic to the alias `gpt-4o` count toward complimentary tokens? The article lists only dated snapshots.
- Does the Sentry project `qaren-rr/python-fastapi` have custom fingerprint or grouping rules? Checking needs Sentry access through /mcp.
- The help.openai.com article was read through the r.jina.ai proxy, and its model lists were not cross-checked.

**U4c**
- How is the native launch screen hidden without expo-splash-screen? Is there a blank frame? A device check on a fresh install is needed.
- Design rulings owed:
  - Keep `t('app.name')` next to the mark?
  - Start the Splash mark at the launch size, at opacity 1?
  - Accept the master's 32 px ink offset (about 3 pt)?
- Keep the `QarenLogo.tsx` path, or rename it and update the 11 mocks? Put the asset in `assets/brand/` or `assets/`?
- Does a vector source (SVG or Figma) of the mark exist?
- Sharpness at 24-28 pt was not measured; it needs a device screenshot.
- `EXPO_OFFLINE=1 npx expo export --dump-assetmap` was not run with the new assets.
- Ruling owed: may U4c run a single-file `jest -u`?

**U3b**
- Chat Completions storage default and retention for this org: the two OpenAI pages disagree. Check in the dashboard.
- The exact label of the OpenAI data-sharing control was not verified.
- The design of the server-side consent record is open.

**U8**
- Where the controller is (D5) sets the home law and decides the ToS governing-law clause.
- Hosting regions for Supabase, Railway, Upstash and the scraping and search vendors must be read from the dashboards.
- Is the `public.users` row removed when the auth user is deleted? The DDL and its FK are not in the repo.
- Age of full legal capacity: Bahrain 21 per a secondary source (CRIN), not verified on a primary source; KSA not checked.
- The SDAIA adequacy list was not found, so whether the US is on it is unknown.
- Which App Store territories will be enabled is unset.
- OpenAI moderations-endpoint retention is not in the extracted table.
- Do re-engagement pushes count as advertising under KSA Art 25 / IR Art 28? That is D10.
- Has a Bahrain PDPA notification been filed, or a guardian appointed?
- No Apple primary page states that the policy text itself must describe third-party AI. That requirement is derived from 5.1.2(i), 5.1.1(i) and DPLA 3.3.3(C).

**U10 / U11**
- Is the remote iOS buildNumber for `com.qaren.app` already initialised? The check is `eas build:version:get -p ios`; that is Ahmed's or the orchestrator's, and Claude never touches EAS.
- Does the App ID `com.qaren.app` exist on team 8K562M549D with Sign in with Apple, Push and Associated Domains enabled?
- Does the EAS `production` environment hold `SENTRY_AUTH_TOKEN` (or ALLOW_FAILURE / DISABLE_AUTO_UPLOAD) and the `EXPO_PUBLIC_*` variables? Check names only.
- What is the minimum ASC key role for EAS Submit? Admin per Expo; App Manager is unverified.
- Is `ios.infoPlist.ITSAppUsesNonExemptEncryption:false` equivalent to `ios.config.usesNonExemptEncryption`?
- U11 design: store the refresh token at sign-in, or re-authenticate at deletion? A product and legal call for Ahmed.
