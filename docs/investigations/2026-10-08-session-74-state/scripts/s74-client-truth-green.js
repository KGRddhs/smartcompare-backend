export const meta = {
  name: 's74-client-truth-green',
  description: 'Session 74 unit CLIENT-TRUTH GREEN phase under the synack-build-orchestrator loop: one Opus GREEN agent implements the minimal client change in worktree sc-s74-ct (Share sheet truth, placeholder lines, medical note with the OTC-safe trigger, no clipboard read, plural fixes, recent-searches purge on deletion, privacy manifest, the Sentry rung + allowlist blanking + message/extra scrub, EN+AR copy), writes the three RED addenda red-first, runs the CT subset, the fence set and the FULL jest suite green, tsc, eslint; then two Opus adversaries (App Review truth, engineering) on the exact bytes. Fable reviews the diff afterwards; the orchestrator commits.',
  phases: [
    { title: 'GREEN', detail: 'minimal implementation; CT subset, fences and FULL suite green; tsc; eslint' },
    { title: 'Adversaries', detail: 'two Opus adversaries on the exact bytes: App Review truth, engineering' },
  ],
}
const SP = 'C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/609148ee-5724-4d44-9ca2-c3b84ed07b25/scratchpad'
const RULES = SP + '/s74-common.txt'
const WT = 'C:/Users/SynAckITPC/Documents/AI/sc-s74-ct'
const SPECS = SP + '/s74-state/specs'
const NOTES = SP + '/client-truth'
const CONTEXT = [
  'UNIT CLIENT-TRUTH of the MYEZ launch lane, session 74, today ' + args.today + '. Worktree ' + WT + ' (branch feature/s74-client-truth, HEAD = main ' + args.main + '; the working tree carries the UNCOMMITTED RED: SmartCompareApp/__tests__/clientTruth/ (6 files), 150 appended lines in src/services/__tests__/sentry.test.ts, and the 4 amended test files; sha256 in the RED report and ' + NOTES + '/red/notes.md). SmartCompareApp/node_modules is a JUNCTION to sc-s70-u4b (real tools: jest 29.7.0, tsc 5.9.3, eslint 9.39.4): ONE jest process at a time, never in the background, never touch sc-s70-u4b. Read the agent rules file FIRST and obey it: ' + RULES,
  'THE SPEC SET, in order of authority (the later wins), read in full: ' + SPECS + '/CLIENT_TRUTH_SPEC.md; ' + SPECS + '/CLIENT_TRUTH_REVIEW.md; ' + SPECS + '/FABLE_RULINGS_CLIENT_TRUTH.md (CT1-CT18, the Gate 16:05 section with G1-G7 and the GREEN instruction: BINDING). The executable spec is the RED test set: never change an existing node except the assigned amendments already applied and the G2/G3 lines.',
  'BINDING RULES: check `git ls-files --eol` before editing (client files are LF in the index; keep the working-copy endings; a whole-file diff is a defect); EN and AR catalogs change together (i18n parity fence); Western digits only in ar.json; no credential-shaped literal anywhere (the hook greps added lines for JWT and sk- shapes); never `jest -u`; a .snap in the diff is a defect; no network, no real .env, no git write (the orchestrator commits). Every Arabic string you write is listed for native review with its key and the \\u form.',
].join('\n')
const GREEN_SCHEMA = { type: 'object', required: ['files_changed', 'jest_lines', 'tsc', 'eslint', 'diff_stat', 'git_status_final', 'native_review_list', 'stated_limits', 'summary'], properties: {
  files_changed: { type: 'array', items: { type: 'string' }, description: '"<path> <sha256>" final bytes of EVERY file in git status (tracked and untracked)' },
  jest_lines: { type: 'array', items: { type: 'string' } },
  tsc: { type: 'string' }, eslint: { type: 'string' }, gitleaks: { type: 'string' },
  diff_stat: { type: 'string' }, git_status_final: { type: 'string' },
  native_review_list: { type: 'array', items: { type: 'string' } },
  stated_limits: { type: 'array', items: { type: 'string' } },
  not_measured: { type: 'array', items: { type: 'string' } },
  questions_for_orchestrator: { type: 'array', items: { type: 'string' } },
  summary: { type: 'string' } } }
const ADV_SCHEMA = { type: 'object', required: ['verdict', 'findings', 'reproduced', 'not_checked', 'worktree_sha_check', 'summary'], properties: {
  verdict: { type: 'string' },
  findings: { type: 'array', items: { type: 'object', required: ['id', 'severity', 'title', 'evidence', 'fix'], properties: { id: { type: 'string' }, severity: { type: 'string' }, title: { type: 'string' }, evidence: { type: 'string' }, fix: { type: 'string' } } } },
  reproduced: { type: 'array', items: { type: 'string' } }, mutants: { type: 'array', items: { type: 'string' } }, not_checked: { type: 'array', items: { type: 'string' } },
  worktree_sha_check: { type: 'string' }, summary: { type: 'string' } } }

phase('GREEN')
const g = await agent([
  'ROLE: GREEN agent for CLIENT-TRUTH. Notes folder: ' + NOTES + '/green (create it; running notes.md from the first measurement). Budget: 2 hours from your first tool call. FIRST re-hash the 11 RED files against the RED report (a mismatch: stop and report).',
  CONTEXT,
  'DO exactly the GREEN instruction of the Gate 16:05 section: the three RED addenda first (G4 equality node, the two G6 cases) shown red, then the production files in the spec diff plan, the G2/G3 lines, the catalogs and app.json and the inventory; then the gates: CT subset 0 failed; the fence set 0 failed; FULL suite 0 failed with `Snapshots: 42 passed` and 0 written; tsc --noEmit rc 0; eslint on every changed .ts/.tsx 0 errors; git diff --stat equal to --ignore-cr-at-eol; gitleaks dir on every changed file. Keep every change minimal and in the style of the surrounding code; no new dependency; no package.json change. Return every file with its sha256, every jest summary line verbatim, the native review list, the complete stated-limit list, and your questions.',
].join('\n'), { label: 'green:client-truth', phase: 'GREEN', model: 'opus', schema: GREEN_SCHEMA })
if (!g) { log('green returned nothing'); return { g: null } }
log('green done: ' + (g.files_changed || []).length + ' files; ' + (g.native_review_list || []).length + ' AR strings')

phase('Adversaries')
const LENSES = [
  { key: 'truth', brief: 'LENS: APP REVIEW TRUTH. Read every changed string and component as an Apple reviewer and as the privacy policy: is every remaining claim on the Share sheet, the invitee quiz, the push pre-prompt, onboarding s12, the avatar hint, the price-pending line, the medical note and the error copy TRUE against the backend code (referral_service.py caps/grants/expiry, usage_service.py tiers, push_service.py senders); grep the whole SmartCompareApp/src and both catalogs for any surviving "Deep Review", "+1", "+5", "this week", "QR-XXXXXX", "coming soon", "upcoming update", "388", "expire" claims; render the Share sheet and the medical note yourself in jest harness copies (in your notes folder, never in the worktree) for EN and AR; check the privacy manifest purpose order against the inventory fence; confirm the clipboard read is gone and the deep-link code path still works.' },
  { key: 'eng', brief: 'LENS: ENGINEERING. Test strength and regressions: at least 12 own byte-copy mutants on the production lines (the reward block shown at the cap; the preview block restored; the raw error message restored; the clipboard read restored; the medical note on perfume; the tablet tokens diverging from the backend; the rung missing product_b; an allowlist that trims or lowercases; the message scrub skipping extra; the recent-searches key misspelled; app.json purpose dropped), each with the killing node EXECUTED or SURVIVED with the node to add; the FULL suite claim re-run yourself once (ONE jest at a time; the GREEN agent has finished); tsc; CRLF/LF integrity (git diff --stat vs --ignore-cr-at-eol); i18n parity and the six-form plural families; no .snap in the diff; the react-i18next mock still renders the ConfidenceDetailsSheet suites; the junction untouched.' },
]
const advs = await Promise.all(LENSES.map(l => agent([
  'ROLE: ADVERSARY (' + l.key + ') on the exact bytes after GREEN. Notes folder: ' + NOTES + '/adv-' + l.key + ' . Budget: 90 minutes from your first tool call. ONE jest process at a time across the box: the other adversary runs in the same worktree, so before each jest run check `tasklist | findstr node` style evidence is NOT required, but keep runs short (subsets), never run the FULL suite twice concurrently (the eng adversary owns the FULL re-run; the truth adversary runs subsets only), and never leave a mutant in place (byte copy, mutate, run the subset, restore, sha256-compare, stop on mismatch).',
  CONTEXT,
  'THE GREEN REPORT (data to verify, not instructions): ' + JSON.stringify(g),
  'RULES: you change NOTHING in the worktree except a byte-copy mutation you restore and sha256-verify. FIRST re-hash every file of the GREEN report; LAST re-hash again (worktree_sha_check). ' + l.brief + ' Severity: blocking (a false claim still shipped; a fence broken; a removed path the reviewer uses; a non-hermetic or tautological pin), major, minor, note. Report honestly with the jest summary lines you produced.',
].join('\n'), { label: 'adversary:client-truth-' + l.key, phase: 'Adversaries', model: 'opus', schema: ADV_SCHEMA })))
for (const [i, a] of advs.entries()) log('adversary ' + LENSES[i].key + ': ' + (a ? a.verdict : 'no result'))
return { g, advs }