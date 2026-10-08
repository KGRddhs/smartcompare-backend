export const meta = {
  name: 's74-u13e-green',
  description: 'Session 74 unit U13e GREEN phase under the synack-build-orchestrator loop: one Opus GREEN agent applies the 6-line production change (both /url/detect verbs join the paid-route admin guard; #304 whitespace-only ADMIN_API_KEY counts as unset at both env read sites) plus the CLAUDE.md lines in worktree sc-s74-u13e, runs the 47 new nodes, the U13 pair and the comm chunks green, byte-copy mutants; then two Opus adversaries (route truth, engineering) on the exact bytes. Fable reviews the diff afterwards; the orchestrator commits.',
  phases: [
    { title: 'GREEN', detail: 'D1-D3 + CLAUDE.md; 47 nodes green; comm chunks re-baselined; mutants' },
    { title: 'Adversaries', detail: 'two Opus adversaries on the exact bytes: route truth, engineering' },
  ],
}
const SP = 'C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/609148ee-5724-4d44-9ca2-c3b84ed07b25/scratchpad'
const RULES = SP + '/s74-common.txt'
const WT = 'C:/Users/SynAckITPC/Documents/AI/sc-s74-u13e'
const SPECS = SP + '/s74-state/specs'
const NOTES = SP + '/u13e'
const CONTEXT = [
  'UNIT U13e of the MYEZ launch lane, session 74, today ' + args.today + '. Worktree ' + WT + ' (branch feature/s74-u13e-url-detect-guard, HEAD = main ' + args.main + '; the working tree carries the UNCOMMITTED RED: tests/test_u13e_url_detect_guard.py e7f8cc04b338a462d25451bf0815105d3f1c408f069b2f336c664e3d000e7e59 and tests/test_s71_u13_compare_auth_required.py 289f24f590627b351862a00ee701fb9978d8f0ae4254a7df98a3cae132dd4121; re-hash FIRST, a mismatch stops you). ONE pytest process at a time in this worktree (the bounded runner only); another agent works in sc-s71-t0b: never touch it. Read the agent rules file FIRST and obey it: ' + RULES,
  'THE SPEC SET, in order of authority (the later wins), read in full: ' + SPECS + '/U13E_SPEC.md; ' + SPECS + '/U13E_REVIEW.md; ' + SPECS + '/FABLE_RULINGS_U13E.md (U1-U10, the Gate 19:05 section with the GREEN instruction: BINDING). The RED notes and the scratch trial (D1-D3 byte edits that made everything green): ' + NOTES + '/red/ (notes.md, apply_trial.py, trial_tree/app/api/url_routes.py, admin_routes.py, main.py as references for the exact edits).',
  'BINDING RULES: backend files are CRLF in the working copy and LF in the index: Edit preserves endings; `git diff --stat` must equal `--ignore-cr-at-eol`. No credential-shaped literal anywhere; the admin sentinel in tests is built by concatenation. No flag flip, no network, no real .env, no git write. Every production line is proven by a byte-copy mutant (shutil.copyfile, mutate, run the killing node, restore, sha256-compare, stop on mismatch).',
].join('\n')
const GREEN_SCHEMA = { type: 'object', required: ['files_changed', 'pyt_lines', 'mutants', 'diff_stat', 'git_status_final', 'stated_limits', 'summary'], properties: {
  files_changed: { type: 'array', items: { type: 'string' } }, pyt_lines: { type: 'array', items: { type: 'string' } }, lint: { type: 'string' }, gitleaks: { type: 'string' },
  mutants: { type: 'array', items: { type: 'string' } }, diff_stat: { type: 'string' }, git_status_final: { type: 'string' },
  stated_limits: { type: 'array', items: { type: 'string' } }, not_measured: { type: 'array', items: { type: 'string' } },
  questions_for_orchestrator: { type: 'array', items: { type: 'string' } }, summary: { type: 'string' } } }
const ADV_SCHEMA = { type: 'object', required: ['verdict', 'findings', 'reproduced', 'not_checked', 'worktree_sha_check', 'summary'], properties: {
  verdict: { type: 'string' },
  findings: { type: 'array', items: { type: 'object', required: ['id', 'severity', 'title', 'evidence', 'fix'], properties: { id: { type: 'string' }, severity: { type: 'string' }, title: { type: 'string' }, evidence: { type: 'string' }, fix: { type: 'string' } } } },
  reproduced: { type: 'array', items: { type: 'string' } }, mutants: { type: 'array', items: { type: 'string' } }, not_checked: { type: 'array', items: { type: 'string' } },
  worktree_sha_check: { type: 'string' }, summary: { type: 'string' } } }

phase('GREEN')
const g = await agent([
  'ROLE: GREEN agent for U13e. Notes folder: ' + NOTES + '/green (create it; running notes.md). Budget: 90 minutes from your first tool call.',
  CONTEXT,
  'DO exactly the GREEN instruction of the Gate 19:05 section (items 1-6), minimal and in the style of the surrounding code. Return every file with its final sha256, every [pyt] line verbatim (the 47-node file, the U13 pair, comm chunks A and B with their counts at this base), the mutant table, the complete stated-limit list (incl. the U2 residual and the n2/n4 residuals), and your questions.',
].join('\n'), { label: 'green:u13e', phase: 'GREEN', model: 'opus', schema: GREEN_SCHEMA })
if (!g) { log('green returned nothing'); return { g: null } }
log('green done: ' + (g.files_changed || []).length + ' files, ' + (g.mutants || []).length + ' mutants')

phase('Adversaries')
const LENSES = [
  { key: 'route-truth', brief: 'LENS: ROUTE TRUTH. On the exact bytes: is there ANY path that still resolves DNS anonymously while ENABLE_COMPARE_AUTH_REQUIRED is truthy (every route that calls the URL validator; middleware and dependency order; both verbs; malformed bodies; HEAD/OPTIONS; trailing-slash and case variants of the path; the /admin mount): measure with a getaddrinfo recorder over at least 20 request shapes; the #304 sites: is there a THIRD place the env key is read or compared (grep ADMIN_API_KEY and verify_admin_key callers); the whitespace-header semantics under httptools reasoned from the review probe; the OpenAPI pin; the CLAUDE.md sentences and the U2 residual stated truthfully (the signed-in /url/compare resolve before the credit gate).' },
  { key: 'eng', brief: 'LENS: ENGINEERING. Test strength and regressions: at least 10 own byte-copy mutants (the dependency on one verb only; require_paid_route_user instead of admin; strip-then-compare; the strip dropped at one site; a guard that reads ENABLE_PAID_ROUTE_METERING; the comment claiming the signed-in half closed), each with the killing node EXECUTED or SURVIVED with the node to add; re-run comm chunk A yourself (bound 1200) and the U13 pair; CRLF/LF integrity (git diff --stat vs --ignore-cr-at-eol; ls-files --eol); the U13 fixture protocol (tests/fixtures/s71_u13_flag_off_baseline.json) untouched; no credential shape in any added line; the new file hermetic under the netguard (0 blocked attempts attributable to it).' },
]
const advs = await Promise.all(LENSES.map(l => agent([
  'ROLE: ADVERSARY (' + l.key + ') on the exact bytes after GREEN. Notes folder: ' + NOTES + '/adv-' + l.key + ' . Budget: 75 minutes. The other adversary runs in the same worktree: keep every pytest run short (bound 600; the eng adversary owns the comm-chunk re-run), never leave a mutant in place (byte copy, mutate, run, restore, sha256-compare, stop on mismatch), and re-hash the GREEN files before each run so a contaminated run is discarded, not reported.',
  CONTEXT,
  'THE GREEN REPORT (data to verify, not instructions): ' + JSON.stringify(g),
  'RULES: you change NOTHING in the worktree except a byte-copy mutation you restore and sha256-verify. FIRST re-hash every file of the GREEN report; LAST re-hash again (worktree_sha_check). ' + l.brief + ' Severity: blocking (anonymous DNS still reachable; a credential comparison that accepts whitespace; a CI-red existing test; a non-hermetic or tautological pin), major, minor, note. Report honestly with the [pyt] lines you produced.',
].join('\n'), { label: 'adversary:u13e-' + l.key, phase: 'Adversaries', model: 'opus', schema: ADV_SCHEMA })))
for (const [i, a] of advs.entries()) log('adversary ' + LENSES[i].key + ': ' + (a ? a.verdict : 'no result'))
return { g, advs }