export const meta = {
  name: 's74-client-truth-red',
  description: 'Session 74 unit CLIENT-TRUTH RED phase under the synack-build-orchestrator loop: one Opus RED agent writes the six new jest test files, the sentry.test.ts appends and the ruled assigned amendments into worktree sc-s74-ct (real node_modules through a junction), proves every RED node red for its stated reason with the project jest, keeps the fences green, runs the full suite once, touches no production file. Fable gates afterwards.',
  phases: [ { title: 'RED', detail: 'client tests first; red for the right reason at main dfbda511' } ],
}
const SP = 'C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/609148ee-5724-4d44-9ca2-c3b84ed07b25/scratchpad'
const RULES = SP + '/s74-common.txt'
const WT = 'C:/Users/SynAckITPC/Documents/AI/sc-s74-ct'
const SPECS = SP + '/s74-state/specs'
const NOTES = SP + '/client-truth'
const SCHEMA = { type: 'object', required: ['files_written', 'jest_lines', 'git_status', 'red_reasons', 'summary'], properties: {
  files_written: { type: 'array', items: { type: 'string' }, description: '"<path> <sha256>" for every file written or edited, final bytes on disk' },
  jest_lines: { type: 'array', items: { type: 'string' }, description: 'the jest "Tests:" / "Test Suites:" / "Snapshots:" summary lines of every run, verbatim, with the command and the elapsed time' },
  eslint: { type: 'string' },
  git_status: { type: 'string' },
  red_reasons: { type: 'array', items: { type: 'string' }, description: 'per node: red or green at base and the assertion message that proves the reason' },
  native_review_list: { type: 'array', items: { type: 'string' }, description: 'every Arabic expectation the tests encode, with the key and the \\u form' },
  not_measured: { type: 'array', items: { type: 'string' } },
  questions_for_orchestrator: { type: 'array', items: { type: 'string' } },
  summary: { type: 'string' } } }

phase('RED')
const red = await agent([
  'ROLE: RED agent for unit CLIENT-TRUTH. Notes folder: ' + NOTES + '/red (create it; running notes.md from the first measurement). Budget: 2 hours from your first tool call.',
  'Worktree ' + WT + ' (branch feature/s74-client-truth = main ' + args.main + ', clean; SmartCompareApp/node_modules is a JUNCTION to sc-s70-u4b: real tools, jest 29.7.0, tsc 5.9.3; ONE jest process at a time, never in the background, never touch sc-s70-u4b). You MAY write under SmartCompareApp/__tests__/, SmartCompareApp/src/**/__tests__/ and SmartCompareApp/__mocks__/ of this worktree only, plus the exact assigned amendments; NO production file, NO git command (the orchestrator commits). Read the agent rules file FIRST and obey it: ' + RULES,
  'THE SPEC SET, in order of authority (the later wins), read in full: ' + SPECS + '/CLIENT_TRUTH_SPEC.md; ' + SPECS + '/CLIENT_TRUTH_REVIEW.md; ' + SPECS + '/FABLE_RULINGS_CLIENT_TRUTH.md (BINDING: CT1-CT18, the RED instruction at its end). The spec writer notes: ' + NOTES + '/spec/ ; the reviewer notes: ' + NOTES + '/review/ (probe outputs, harness references).',
  'DO: (1) write the new test files under SmartCompareApp/__tests__/clientTruth/ (shareTruth.s74, copyTruth.s74, medicalNote.s74, registerNoClipboard.s74, deviceData.s74, privacyManifest.s74) and append the sentry nodes (CT-Y1..Y5, CT11, CT12) to SmartCompareApp/src/services/__tests__/sentry.test.ts, exactly per the spec as amended by the rulings (CT1 reward-line pin; CT2 hide-at-cap node + LIFETIME_CAP read; CT3 prePrompt node; CT4 signupCtaSoft no-digit node; CT6 the three trigger arms + perfume and electronics negatives; CT7 generic error node; CT11 allowlist nodes; CT12 message/extra scrub node; CT14 the two extra plural nodes; CT17 digit class). Pure ASCII, LF; Arabic expectations as \\u escapes; any sentinel built at runtime by concatenation; no credential-shaped literal (the hook greps added lines for JWT and sk- shapes). (2) apply the CT15 assigned amendments with the Edit tool, minimal lines, endings preserved (check `git ls-files --eol` first): ShareBottomSheet.redesign.test.tsx :27-31/:57-62, RegisterScreen.deferredCode.test.tsx the four clipboard nodes, sentry.test.ts :119 only (CT9), __mocks__/react-i18next.ts:12, InviteeQuizScreen.redesign.test.tsx :84-86 + docblock :8. (3) from ' + WT + '/SmartCompareApp print the tool versions, then run: `timeout -k 15 600 node node_modules/jest/bin/jest.js --ci __tests__/clientTruth src/services/__tests__/sentry.test.ts` (every RED node fails for its stated reason: quote the assertion message; GUARD nodes pass; a node failing for a setup/import/mock reason is a defect you fix before reporting); the fence set from the spec plus the CT8 additions (green); then the FULL suite once: `timeout -k 15 1500 node node_modules/jest/bin/jest.js --ci` (only the CT nodes and the amended nodes may be red; 0 snapshots written; paste the summary). (4) `timeout -k 15 600 node node_modules/eslint/bin/eslint.js` on every new or edited test file (0 errors). (5) `git status --porcelain` and `git diff --stat` (tiny diffs on the amended files; no whole-file diff). Return every file with its sha256, every jest summary line verbatim, the native review list, and your questions.',
].join('\n'), { label: 'red:client-truth', phase: 'RED', model: 'opus', schema: SCHEMA })
log('red: ' + (red ? (red.jest_lines || []).length + ' jest lines' : 'no result'))
return { red }