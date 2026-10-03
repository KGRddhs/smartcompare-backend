export const meta = {
  name: 's70-u4b-icons-deps',
  description: 'Session 70 U4b: MYEZ app icons from the master PNG + Expo SDK 54 patch bumps + gesture-handler removal + CI drift ratchet; spec, adversarial spec review, red, green, two adversaries, fix',
  phases: [
    { title: 'Spec', detail: 'measure and write the U4b spec' },
    { title: 'Review', detail: 'adversarial spec review, binding corrections' },
    { title: 'Red', detail: 'failing tests only' },
    { title: 'Green', detail: 'installs, icons, removal, CI ratchet, full gates' },
    { title: 'Adversary', detail: 'app-review lens + engineering lens' },
    { title: 'Fix', detail: 'apply surviving findings' },
  ],
}
const SP = 'C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/e2415927-6e3a-4d40-81fc-edeec632886a/scratchpad'
const RULES = SP + '/s70-common.txt'
const WT = 'C:/Users/SynAckITPC/Documents/AI/sc-s70-u4b'
const APPDIR = WT + '/SmartCompareApp'
const STATE = WT + '/docs/investigations/2026-09-30-session-70-state'
const SPEC = STATE + '/U4B_ICONS_DEPS_SPEC.md'
const MASTER = 'C:/Users/SynAckITPC/Downloads/MYEZ-icon-white-2048.png'
const NOTES = SP + '/u4b'
const BASE = '94c097cd'

const CONTEXT = [
  'UNIT U4b of the MYEZ (Arabic brand in the catalogs) Apple App Store launch lane, repo smartcompare (React Native / Expo SDK 54 app in SmartCompareApp/, FastAPI backend in app/). Identifiers stay qaren (bundle id com.qaren.app, slug qaren, scheme qaren://).',
  'Worktree: ' + WT + ' (branch feature/s70-u4b-icons-deps, base ' + BASE + ' = main). It has its OWN real node_modules (npm ci, NOT a junction) so it is isolated from every other worktree.',
  'Read the agent rules file FIRST and obey it: ' + RULES,
  'Scope of U4b (from docs/investigations/2026-09-29-session-69-state/APP_STORE_LAUNCH_RUNBOOK.md section 4 row U4 and NEXT_SESSION_PROMPT.md section 4):',
  '  (1) Expo SDK 54 patch bumps that `npx expo install --check` reports: measured in this worktree on 2026-09-30: expo 54.0.34 -> ~54.0.37, expo-font 14.0.11 -> ~14.0.12, expo-localization 17.0.8 -> ~17.0.9, expo-screen-capture 8.0.9 -> ~8.0.10, expo-updates 29.0.17 -> ~29.0.20; react-native-svg 15.15.5 (expected 15.12.1, runbook says EXCLUDE via expo.install.exclude); eslint-config-expo 55.0.1 (expected ~10.0.0, NOT in the runbook - the spec must decide exclude vs align, with evidence).',
  '  (2) Uninstall react-native-gesture-handler (package.json has ~2.28.0; W3-7 found it an orphan) and delete its PENDING_REMOVAL entry and the d3 todo that tracks it (find them).',
  '  (3) Real brand app icons from the ORIGINAL master ' + MASTER + ' (2048x2048 RGBA, white rounded tile with transparent corners, black MY/EZ wordmark and an emerald dot). Ahmed chose this file (decision D4). Commit the master into the repo (suggested docs/brand/myez-icon-master-2048.png) and a deterministic render script; produce SmartCompareApp/assets/icon.png (iOS: 1024x1024, OPAQUE, no alpha channel, full-bleed square - iOS applies the mask; flatten the transparent corners onto the tile white), adaptive-icon.png (Android adaptive FOREGROUND: transparent background, the mark scaled into the 66% safe zone, plus app.json android.adaptiveIcon.backgroundColor set to the tile white), splash-icon.png (transparent background, wordmark only, sized for the expo-splash-screen config in app.json) and favicon.png if app.json references it. Check app.json for every other icon field (notification icon, ios dark/tinted variants) and decide. The three launcher files must differ from each other and from the recorded template SHA-256s.',
  '  (4) Flip ICON_ART_SUPPLIED to true at SmartCompareApp/__tests__/config/nativeBundle.w37.test.ts:251 and delete the b3-todo line; extend that describe block with pixel-level pins (icon.png is 1024x1024 with no alpha; the adaptive foreground has alpha; they are not the grey concentric-circles template). jest has no PNG decoder unless one is installed - measure what is available (e.g. read the IHDR chunk bytes directly: width, height, colour type) rather than adding a dependency.',
  '  (5) Ratchet the CI step "Expo dependency drift (non-blocking)" in .github/workflows/ci.yml to blocking (drop continue-on-error, rename) once `npx expo install --check` reads clean in this worktree.',
  '  (6) The OTA hazard: runtimeVersion.policy is appVersion and expo.version is 1.0.0; the testers run preview build 773a9375 (built from 6042506d with expo-updates 29.0.17). After these native patch bumps, a later `eas update --branch preview` would ship JS built against the new expo packages to that old binary. The spec must measure what the bumped packages change natively (read their CHANGELOGs in node_modules after a dry look at npm view, or diff the installed vs target package contents if available) and recommend: bump expo.version (e.g. 1.0.1) in this unit, or keep 1.0.0 and record a rule that the next preview BUILD must precede any further OTA. Do not decide silently - state the evidence and the recommendation; the orchestrator rules.',
  'Out of scope: any backend change, legal docs, the eas.json submit block, any other dependency.',
  'Store-build facts: NATIVE changes reach users only through `eas build --profile production`; the production channel has never received an update.',
].join('\n')

const SPEC_SCHEMA = { type: 'object', required: ['spec_path', 'spec_sha256', 'base_sha', 'open_questions', 'summary'], properties: {
  spec_path: { type: 'string' }, spec_sha256: { type: 'string' }, base_sha: { type: 'string' },
  open_questions: { type: 'array', items: { type: 'string' } }, summary: { type: 'string' } } }
const REVIEW_SCHEMA = { type: 'object', required: ['verdict', 'corrections', 'spec_sha256_after', 'summary'], properties: {
  verdict: { type: 'string', enum: ['APPROVED', 'APPROVED_WITH_CORRECTIONS', 'REJECTED'] },
  corrections: { type: 'array', items: { type: 'string' } }, spec_sha256_after: { type: 'string' }, summary: { type: 'string' } } }
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

phase('Spec')
const spec = await agent([
  'ROLE: spec writer (read-and-measure only; you may run npx expo install --check, npx expo config --type introspect, node scripts and python PIL reads, but NO installs and NO edits outside the spec file and your notes folder ' + NOTES + ').',
  CONTEXT,
  'TASK: measure everything the unit touches at base ' + BASE + ' and write the spec to ' + SPEC + ' (create the folder). Required sections: Base SHA; Measured facts (each with the command and its output excerpt: the drift list, every file that names react-native-gesture-handler or PENDING_REMOVAL anywhere in the repo incl. tests, jest config, babel config, docs; every icon/splash/favicon/notification field in app.json; the nativeBundle.w37 launcher-art block; the CI step; the master PNG facts: size, mode, the bounding box of the non-white ink, the tile corner radius); Requirements R1..Rn (exact files and exact expected results); the exact package-manager commands the GREEN agent runs in this isolated worktree; the render script design (path, inputs, deterministic outputs, how to re-run); the RED test list (name, file, assertion, why it fails at base); Gates (FULL jest, tsc, eslint on changed files, npx expo install --check clean, npx expo-doctor, npx expo config --type introspect showing the icon paths); Stated limits; Open questions for the orchestrator (the eslint-config-expo decision, the expo.version decision with evidence).',
  'Return the spec path, its sha256, the base sha, your open questions and a short summary.',
].join('\n'), { label: 'u4b:spec', phase: 'Spec', schema: SPEC_SCHEMA })

phase('Review')
const review = await agent([
  'ROLE: ADVERSARIAL spec reviewer. Your job is to REFUTE claims in the spec, not to confirm them. Read-and-measure only (no installs, no edits except appending to the spec file).',
  CONTEXT,
  'The spec is ' + SPEC + ' (sha256 reported by its writer: ' + (spec ? spec.spec_sha256 : 'unknown') + '). Re-measure EVERY factual claim (drift list, every gesture-handler reference, app.json fields, the test block, the master PNG geometry, the Android adaptive safe zone maths, iOS icon rules: 1024x1024 opaque no alpha). Look for what the spec MISSED: another file importing gesture-handler (react-navigation stack needs it; which navigators does the app use?), jest mocks or setup referencing it, a snapshot that embeds icon bytes, the splash plugin config (expo-splash-screen plugin block vs expo.splash), iOS 18 dark/tinted icon expectations, Android monochrome icon, notification icon, the favicon, and whether the OTA hazard recommendation is backed by evidence.',
  'Writer open questions: ' + JSON.stringify(spec ? spec.open_questions : []),
  'Append a section "## Review corrections (BINDING - supersede the body)" to the spec with numbered corrections, each with its measurement. Answer the writer open questions with a RECOMMENDATION each (the orchestrator will confirm). Return verdict, corrections, the spec sha256 after your edit, and a summary.',
].join('\n'), { label: 'u4b:spec-review', phase: 'Review', schema: REVIEW_SCHEMA })

phase('Red')
const red = await agent([
  'ROLE: RED agent (tests only). Write the failing tests the spec lists (as corrected by its BINDING review section) and nothing else - no source, asset, package or CI edits. Run each new/edited test file with jest by path and show it fails FOR THE RIGHT REASON (paste the failure lines). Run the untouched rest of the affected suites to show they still pass.',
  CONTEXT,
  'Spec: ' + SPEC + ' (read the BINDING corrections at the end). Review verdict: ' + (review ? review.verdict : 'unknown') + '.',
  'Notes folder: ' + NOTES + '. Return files changed with sha256, gates (verbatim red lines), deviations, git status, residual risk, summary.',
].join('\n'), { label: 'u4b:red', phase: 'Red', schema: WORK_SCHEMA })

phase('Green')
const green = await agent([
  'ROLE: GREEN agent. Make the red tests pass by implementing the spec (as corrected). SPECIAL PERMISSION FOR THIS UNIT ONLY: this worktree has its own isolated node_modules, so you MAY run the package-manager commands the spec names (npx expo install ..., npm uninstall react-native-gesture-handler) inside ' + APPDIR + ' ONLY, and they will edit package.json and package-lock.json. Never run them anywhere else, never npm ci/install at the repo root or in the clone.',
  CONTEXT,
  'Spec: ' + SPEC + '. Red report: ' + JSON.stringify(red ? { files: red.files_changed, gates: red.gates } : {}),
  'Copy the master PNG into the repo path the spec names (read-only source ' + MASTER + '; never modify it). Write the render script, run it, commit nothing (the orchestrator commits). After the code change run, in this order: jest by path on the new tests; tsc; eslint on the changed TS files; npx expo install --check (must be clean apart from the ruled exclusions); npx expo-doctor (report every line); npx expo config --type introspect (paste the icon/splash lines); then the FULL jest suite ONCE (timeout -k 15 1500). Look at the three rendered PNGs yourself (Read the image files) and describe them. Record every gate verbatim.',
  'Notes folder: ' + NOTES + '. Return files changed with final sha256, gates, deviations, git status, residual risk, summary.',
].join('\n'), { label: 'u4b:green', phase: 'Green', schema: WORK_SCHEMA })

phase('Adversary')
const lenses = [
  { key: 'app-review', text: 'App Review / store-asset lens: would Apple accept these icons (1024 opaque, no alpha, no transparency, not a placeholder, legible at 60px - downscale it and look), is the Android adaptive foreground inside the safe zone (measure the ink bbox against the 66dp circle), does the splash render centred on the configured background, are dark/tinted/monochrome variants handled or explicitly out of scope, does anything user-visible still carry the old art (favicon, notification icon, landing), and does the expo.version decision protect testers from an OTA/native mismatch.' },
  { key: 'engineering', text: 'Engineering lens: are the package bumps exactly the SDK 54 expected versions, is the lockfile consistent (npm ls clean, no unexpected transitive churn - diff package-lock.json and count changed packages), is react-native-gesture-handler gone from every code path, mock, config and doc it was named in, do the new tests actually fail when the fix is removed (MUTATE: revert one icon to the template bytes from git show ' + BASE + ':SmartCompareApp/assets/icon.png via a byte copy, and put ICON_ART_SUPPLIED back to false, one at a time, restore by sha), is the render script deterministic (run it twice into your notes folder and compare sha256), is the CI step change correct YAML and truly blocking, and did the FULL jest run really pass (re-run it once).' },
]
const advs = await parallel(lenses.map(l => () => agent([
  'ROLE: ADVERSARY (' + l.key + '). Try to REFUTE that U4b is correct and complete. Read-only except byte-copy mutations you restore by sha256; leave the worktree byte-identical (record the sha256 of every changed file at start and at end).',
  CONTEXT,
  'Spec: ' + SPEC + '. Green report: ' + JSON.stringify(green ? { files: green.files_changed, gates: green.gates, deviations: green.deviations_from_spec } : {}),
  l.text,
  'Notes folder: ' + NOTES + '/adv-' + l.key + '. Verdict SOUND only if you found no serious defect. Return verdict, defects (serious), minors, sha lists, byte-identical flag, summary.',
].join('\n'), { label: 'u4b:adv-' + l.key, phase: 'Adversary', schema: ADV_SCHEMA })))

const findings = advs.filter(Boolean).flatMap(a => (a.defects || []).map(d => 'DEFECT: ' + d).concat((a.minors || []).map(m => 'MINOR: ' + m)))
let fix = null
if (findings.length) {
  phase('Fix')
  fix = await agent([
    'ROLE: FIX agent. Apply every DEFECT below and every MINOR you can verify is real (reject a finding only with a measurement that refutes it). Same special package permission as the green agent (this isolated worktree only), same gates afterwards: jest by path on every touched test, tsc, eslint on changed files, npx expo install --check, then the FULL jest suite once.',
    CONTEXT,
    'Spec: ' + SPEC + '. Findings:\n' + findings.join('\n'),
    'Notes folder: ' + NOTES + '/fix. Return files changed with final sha256, gates, deviations (incl. every rejected finding with its refuting measurement), git status, residual risk, summary.',
  ].join('\n'), { label: 'u4b:fix', phase: 'Fix', schema: WORK_SCHEMA })
}
return { spec, review, red, green, adversaries: advs, fix }
