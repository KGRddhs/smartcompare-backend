export const meta = {
  name: 's71-u4b-green',
  description: 'Session 71 U4b GREEN under the synack-build-orchestrator loop (Opus agents; the Fable orchestrator already gated the RED tests): installs, MYEZ launcher art, gesture-handler removal, CI ratchet, offline gates, full jest; two Opus adversaries; fix round. The orchestrator reviews the diff before any commit.',
  phases: [
    { title: 'Green', detail: 'implement to green: installs, icons, removal, CI split, gates', model: 'opus' },
    { title: 'Adversary', detail: 'app-review lens + engineering lens, mutation checks', model: 'opus' },
    { title: 'Fix', detail: 'apply surviving findings', model: 'opus' },
  ],
}
const SP = 'C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/3ffde5dd-0e09-4243-bf73-02955e287dff/scratchpad'
const RULES = SP + '/s70-common.txt'
const WT = 'C:/Users/SynAckITPC/Documents/AI/sc-s70-u4b'
const APPDIR = WT + '/SmartCompareApp'
const SPEC = WT + '/docs/investigations/2026-09-30-session-70-state/U4B_ICONS_DEPS_SPEC.md'
const MASTER = 'C:/Users/SynAckITPC/Downloads/MYEZ-icon-white-2048.png'
const NOTES = SP + '/u4b'
const HEADSHA = '4bd5a09f'

const CONTEXT = [
  'UNIT U4b of the MYEZ (Arabic brand in the catalogs) Apple App Store launch lane, repo smartcompare (React Native / Expo SDK 54 app in SmartCompareApp/, FastAPI backend in app/). Identifiers stay qaren (bundle id com.qaren.app, slug qaren, scheme qaren://).',
  'Worktree: ' + WT + ' (branch feature/s70-u4b-icons-deps, HEAD = main ' + HEADSHA + '). It has its OWN real node_modules (npm ci, NOT a junction) so it is isolated from every other worktree. Today is 2026-10-03 (session 71).',
  'Read the agent rules file FIRST and obey it: ' + RULES,
  'THE SPEC IS AUTHORITATIVE: ' + SPEC + '. Read it IN FULL. It ends with THREE binding sections that supersede its body, later ones winning: "## Review corrections (BINDING - supersede the body)" (fourteen corrections), "## Orchestrator rulings (BINDING - session 71 ...)" (RQ1-RQ12) and "## Orchestrator rulings - session 71 addendum (BINDING ...)" (RQ13-RQ21). Settled: Q1 ALIGN eslint-config-expo to ~10.0.0 (exclude list exactly ["react-native-svg"]); Q2 KEEP expo.version 1.0.0 (app.json untouched); Q3 = B split CI (blocking "Expo dependency drift (lockfile)" with EXPO_OFFLINE=1 + report-only "Expo SDK patch drift (report-only)"); Q4 U4c is a separate unit (no src/** edits here); Q5 follow-ups; Q6 scripts/render_myez_icons.py + the black allowlist line; RQ7 who runs what; RQ8 the nine resolved versions; RQ13-RQ19 the research corrections (CI comment wording, package.json judged as parsed JSON, EXPO_NO_NEW_ARCH_COMPAT_CHECK=1 on P3, b1/b2 name suffix trim); RQ20 the base moved to ' + HEADSHA + ' with every anchor intact; RQ21 the RED is COMPLETE, reviewed and FROZEN.',
  'THE RED TESTS ALREADY EXIST AND PASSED THE ORCHESTRATOR REVIEW: ' + APPDIR + '/__tests__/config/nativeBundle.w37.test.ts (sha256 prefix 9225b3964b485e8e, tracked, modified) and ' + APPDIR + '/__tests__/helpers/pngDecode.ts (004cebe9b34fd20f, new). At HEAD the file runs 19 failed / 39 passed / 58 total. Do not rewrite them (RQ21).',
  'Out of scope: any backend change, legal docs, the eas.json submit block, any other dependency, src/**, app.json.',
].join('\n')

const WORK_SCHEMA = { type: 'object', required: ['files_changed', 'gates', 'deviations_from_spec', 'git_status_final', 'residual_risk', 'summary'], properties: {
  files_changed: { type: 'array', items: { type: 'string' }, description: '"<path> <sha256>" final bytes' },
  gates: { type: 'array', items: { type: 'string' }, description: 'each gate with its verbatim summary line' },
  deviations_from_spec: { type: 'array', items: { type: 'string' } }, git_status_final: { type: 'string' },
  residual_risk: { type: 'string' }, summary: { type: 'string' } } }
const ADV_SCHEMA = { type: 'object', required: ['verdict', 'defects', 'minors', 'files_sha256_at_start', 'worktree_left_byte_identical', 'summary'], properties: {
  verdict: { type: 'string', enum: ['SOUND', 'DEFECTIVE'] },
  defects: { type: 'array', items: { type: 'string' }, description: 'serious findings, each with file:line, the measurement and a failure scenario' },
  minors: { type: 'array', items: { type: 'string' } },
  files_sha256_at_start: { type: 'array', items: { type: 'string' } }, worktree_left_byte_identical: { type: 'boolean' }, summary: { type: 'string' } } }

phase('Green')
const green = await agent([
  'ROLE: GREEN agent (implementation). Make the 19 red tests pass by implementing the spec as corrected and ruled, with the minimal code that satisfies it, then refactor only while staying green. SPECIAL PERMISSION FOR THIS UNIT ONLY (ruling RQ7): this worktree has its own isolated node_modules, so you MAY run the package-manager commands the spec names - P2 `npm uninstall react-native-gesture-handler`, P3 `EXPO_NO_NEW_ARCH_COMPAT_CHECK=1 npx expo install expo@~54.0.37 expo-font expo-localization expo-screen-capture expo-updates` (RQ17), P4 `npm install --save-dev eslint-config-expo@~10.0.0` - inside ' + APPDIR + ' ONLY (they need the npm registry and the Expo versions API; that traffic is allowed for them). Never run them anywhere else, never npm ci/install at the repo root or in the clone. The ONLINE `expo install --check` and `npx expo-doctor` are NOT yours (the orchestrator runs them after you): you run P5-OFFLINE `EXPO_OFFLINE=1 npx --no-install expo install --check` (exit 0) and G5 as `EXPO_OFFLINE=1 npx --no-install expo config --type introspect --json`.',
  CONTEXT,
  'Order of work: (0) re-hash the two RED files and confirm the prefixes above; run the W3-7 file once to confirm 19 failed / 39 passed. (1) P0 snapshot (byte copies + sha256 of package.json, package-lock.json, app.json into your notes folder) and measure the BASE eslint warning count now: `node node_modules/eslint/bin/eslint.js "src/**/*.{ts,tsx}"` (record errors and warnings). (2) P1 the expo.install.exclude key (Edit tool). (3) P2, P3, P4. (4) P6 and ruling RQ8: print the installed version of expo, expo-font, expo-localization, expo-screen-capture, expo-updates, expo-file-system, expo-constants, babel-preset-expo, @expo/metro-config, @expo/cli, @expo/prebuild-config, eslint-config-expo - if any of the nine named in RQ8 differs from the ruled list, STOP and report; if @expo/prebuild-config moved off 54.0.8, do correction 5\'s grep and paste the lines. (5) P7 (app.json sha unchanged). (6) P8 (lock key diff vs R7, incl. correction 11: exactly one babel-preset-expo copy at >= 54.0.12 - bump the declared range to ~54.0.12 only if npm nested a second copy). (7) Copy the master into docs/brand/myez-icon-master-2048.png (shutil.copyfile from ' + MASTER + '; never modify the source). (8) Write scripts/render_myez_icons.py per section 4 and corrections 9-10 (black-clean under the pinned black 26.5.1, manifest written with newline="\\n", --check compares the manifest as parsed JSON); run it (G2, twice, sha-compare; then --check). (9) The W3-7 test: only RQ19 (trim the b1/b2 name suffix). (10) ci.yml per rulings RQ3 + RQ13-RQ15 (the two steps with the ruled names and run strings, the comment block explaining offline vs online, the offline-fallback caveat and the blind spots; it must not claim the command never writes; no other line changes). (11) The runbook line (R11) and the black allowlist line (correction 9).',
  'Gates, cheapest first, printing each tool version: G1 (py_compile + ruff E9,F63,F7,F82 + black --check on the renderer, pinned venv); G2; G3-offline; G5-offline (paste the icon / splash / adaptiveIcon / favicon / runtime / CFBundle lines); G6 (the W3-7 file alone: expected 58 passed, 58 total, 0 skipped, 0 todo); G8 (tsc --noEmit by path; eslint on the changed *.ts files from `git diff --name-only --relative` run inside SmartCompareApp; and eslint "src/**/*.{ts,tsx}" with the warning count compared with the base count from step 1); G9 (P7/P8 re-printed, `npm ls --all` exit 0); G11 (the three backend YAML-reading tests through the bounded runner: tests/test_ci_gates.py tests/test_channel_freshness.py tests/test_hermeticity_pins.py, bound 600 - paste the [pyt] line); then G7 the FULL jest suite ONCE (timeout -k 15 1500; expected 3 skipped / 351 passed suites, 13 skipped / 13 todo / 3448 passed / 3474 tests, 44 snapshots, no .snap in the diff; the known HistoryScreen.mobileJank.m21 flake is re-run once alone if it reds); finally G10 per RQ16 (git status --short equals R12\'s list as ruled: no app.json; plus .github/black-clean-paths.txt; the spec file shows as modified only because the orchestrator appended the addendum - you never edit it; package.json judged on parsed JSON + content-line diff; no whole-file rewrite of any other CRLF text file). Look at the four rendered PNGs yourself (Read the image files) and describe them. Commit nothing (the orchestrator reviews the diff and commits).',
  'Notes folder: ' + NOTES + '/green (create it; keep running notes from the first measurement). Return files changed with final sha256, gates (verbatim), deviations, git status, residual risk, summary (include the nine resolved versions and the eslint warning counts base vs after).',
].join('\n'), { label: 'u4b:green', phase: 'Green', model: 'opus', schema: WORK_SCHEMA })

phase('Adversary')
const lenses = [
  { key: 'app-review', text: 'App Review / store-asset lens: would Apple accept these icons (icon.png 1024 opaque RGB, no alpha, no tRNS, not a placeholder, legible at 60 px - downscale it yourself with Pillow in your notes folder and look at it), is the Android adaptive foreground inside the safe zone (measure the alpha>0 bbox and the max radius against 1024*33/108), does the splash render centred over #ffffff at ~30 % width (and is the Android legacy 200 dp sizing of correction 6 stated as accepted), are dark/tinted/monochrome variants explicitly out of scope (RQ5), does anything user-visible still carry the old art in files this unit owns (the JS QarenLogo is unit U4c by ruling RQ4 - not a defect here), does e1\'s comment carry correction 4\'s executable rule verbatim with expo.version still 1.0.0, does the ci.yml comment obey RQ13-RQ15, and does the GREEN report contain the nine resolved versions of ruling RQ8.' },
  { key: 'engineering', text: 'Engineering lens: are the package bumps exactly the ruled versions (RQ8), is the lockfile consistent (`npm ls --all` exit 0; diff package-lock.json packages keys against the P0 snapshot the GREEN agent left in its notes folder and count every changed key; exactly one babel-preset-expo at >= 54.0.12 - correction 11), is react-native-gesture-handler gone from package.json, the lock, node_modules and the W3-7 test (and NOT from the historical docs the spec lists as untouched), is eslint-config-expo at 10.0.x with the eslint warning count unchanged, do the tests actually fail when the fix is removed (MUTATE one at a time via byte copies, restore by sha256: (i) icon.png back to the template bytes from `git -C ' + WT + ' show HEAD:SmartCompareApp/assets/icon.png`; (ii) ICON_ART_SUPPLIED back to false; (iii) delete the "expo" key from package.json; (iv) put continue-on-error: true back on the lockfile step; (v) corrupt one Paeth byte in the helper), is the render script deterministic (run it with --out-dir into your notes folder twice and compare sha256; run --check), is the ci.yml change correct YAML with the ruled step names and exactly one blocking + one report-only step (run the three backend YAML-reading tests through the bounded runner yourself), is the black allowlist line present and the renderer black-clean, and did the FULL jest run really pass (re-run it once yourself with timeout -k 15 1500 and paste the summary).' },
]
const advs = await parallel(lenses.map(l => () => agent([
  'ROLE: ADVERSARY (' + l.key + '). Try to REFUTE that U4b is correct and complete against the spec as corrected and ruled. Read-only except byte-copy mutations you restore by sha256; leave the worktree byte-identical (record the sha256 of every changed file at start and at end). Do not run package-manager commands. One mutation harness at a time: before each mutation check `git -C ' + WT + ' status --short` and the sha of the file you are about to mutate, because the other adversary works in the same worktree - if a file is not at the sha the GREEN report lists, wait 60 s and re-check (the other adversary may be mid-mutation) before reading any gate result.',
  CONTEXT,
  'Green report: ' + JSON.stringify(green ? { files: green.files_changed, gates: green.gates, deviations: green.deviations_from_spec, residual_risk: green.residual_risk } : {}),
  l.text,
  'Notes folder: ' + NOTES + '/adv-' + l.key + ' (create it). Verdict SOUND only if you found no serious defect. Return verdict, defects (serious), minors, sha lists, byte-identical flag, summary.',
].join('\n'), { label: 'u4b:adv-' + l.key, phase: 'Adversary', model: 'opus', schema: ADV_SCHEMA })))

const findings = advs.filter(Boolean).flatMap(a => (a.defects || []).map(d => 'DEFECT: ' + d).concat((a.minors || []).map(m => 'MINOR: ' + m)))
let fix = null
if (findings.length) {
  phase('Fix')
  fix = await agent([
    'ROLE: FIX agent. Apply every DEFECT below and every MINOR you can verify is real (reject a finding only with a measurement that refutes it). Same special package permission as the GREEN agent (this isolated worktree only, ruling RQ7), same gates afterwards: jest by path on every touched test file, tsc, eslint on changed files, EXPO_OFFLINE=1 npx --no-install expo install --check, the renderer --check if any asset or the script changed, G11 through the bounded runner if ci.yml changed, then the FULL jest suite once. First re-hash every file the GREEN report lists: a killed adversary can leave a mutant on disk - if a file differs from the GREEN sha and you did not change it, restore it from the adversary\'s byte copy in its notes folder (never git checkout --) and report it.',
    CONTEXT,
    'Green report files: ' + JSON.stringify(green ? green.files_changed : []),
    'Findings:\n' + findings.join('\n'),
    'Notes folder: ' + NOTES + '/fix (create it). Return files changed with final sha256, gates, deviations (incl. every rejected finding with its refuting measurement), git status, residual risk, summary.',
  ].join('\n'), { label: 'u4b:fix', phase: 'Fix', model: 'opus', schema: WORK_SCHEMA })
}
return { green, adversaries: advs, fix }
