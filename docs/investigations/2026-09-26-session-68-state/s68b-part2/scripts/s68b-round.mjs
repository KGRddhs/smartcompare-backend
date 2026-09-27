export const meta = {
  name: 's68b-round',
  description: 'Session 68b bounded round on Opus 5.5: an optional targeted FIX (apply new Fable rulings with pins, every gate through the bounded pytest runner) then an independent ADVERSARY on the exact bytes; bounded re-fix rounds. Args: key, dir, spec, rulings, newRulings, latestReport, latestKey, unitFiles, flag, states, pricePath, corpusFlags, corpusOff, extra, startAt (fix|adversary), round, maxFixRounds',
  phases: [
    { title: 'Fix', detail: 'apply the rulings minimally with load-bearing pins; re-run every gate through pyt.py', model: 'claude-opus-5-5' },
    { title: 'Adversary', detail: 'independent re-review on the exact bytes, bounded', model: 'claude-opus-5-5' },
  ],
}
const MODEL = 'claude-opus-5-5'
const A = (typeof args === 'string') ? JSON.parse(args) : (args || {})
const KEY = A.key
const DIR = A.dir
const SPEC = A.spec
const RULINGS = A.rulings || ''
const NEW = A.newRulings || ''
const LATEST = A.latestReport
const LATEST_KEY = A.latestKey || null
const UNIT_FILES = (A.unitFiles || []).join(' ')
const FLAG = A.flag || null
const STATES = A.states || (FLAG ? 'the flag UNSET and ' + FLAG + '=true' : 'the unflagged state')
const PRICE_PATH = !!A.pricePath
const CORPUS_FLAGS = A.corpusFlags || FLAG || ''
const CORPUS_OFF = A.corpusOff || ''
const EXTRA = A.extra || ''
const START_AT = A.startAt || 'fix'
const ROUND = typeof A.round === 'number' ? A.round : 1
const MAX_FIX = typeof A.maxFixRounds === 'number' ? A.maxFixRounds : 1
const SP = 'C:/Users/SynAckITPC/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/0a2845de-abfe-4bca-b433-df4ce9787ab5/scratchpad'
const COMMON_PATH = SP + '/s68b-common.txt'
if (!KEY || !DIR || !SPEC || !LATEST) { throw new Error('args.key, dir, spec, latestReport are required') }
if (START_AT === 'fix' && !NEW) { throw new Error('args.newRulings is required when startAt is fix') }

const FIX_SCHEMA = {
  type: 'object',
  required: ['unit', 'files_changed', 'all_unit_tests_pass', 'test_evidence', 'lint_clean', 'mutation_checks', 'comm_gate', 'ci_order_run', 'byte_identity', 'pr_text', 'deviations_from_spec', 'git_status_final', 'residual_risk', 'scratch_cleanup', 'gates_not_measured', 'wall_clock'],
  properties: {
    unit: { type: 'string' },
    files_changed: { type: 'array', items: { type: 'string' }, description: '"<path> <sha256>" of every file written or edited (final bytes) and of every unit file left as found' },
    all_unit_tests_pass: { type: 'boolean' },
    test_evidence: { type: 'string', description: 'verbatim summary lines per state, each with its [netguard] line and its [pyt] line' },
    lint_clean: { type: 'boolean' },
    mutation_checks: { type: 'array', items: { type: 'string' } },
    comm_gate: { type: 'string' },
    ci_order_run: { type: 'string' },
    byte_identity: { type: 'string' },
    pr_text: { type: 'string', description: 'the FULL corrected PR body (not a delta)' },
    deviations_from_spec: { type: 'array', items: { type: 'string' } },
    git_status_final: { type: 'string' },
    residual_risk: { type: 'string' },
    scratch_cleanup: { type: 'string' },
    gates_not_measured: { type: 'array', items: { type: 'string' }, description: 'every gate you could not measure inside the bounds/budget, with the [pyt] lines that show it; empty when everything was measured' },
    wall_clock: { type: 'string', description: 'your first and last tool-call times and the total, from [pyt]/date stamps' },
  },
}
const ADV_SCHEMA = {
  type: 'object',
  required: ['unit', 'verdict', 'defects', 'tests_that_prove_nothing', 'worktree_left_byte_identical', 'files_sha256_at_start', 'summary', 'gates_not_measured', 'wall_clock'],
  properties: {
    unit: { type: 'string' },
    verdict: { type: 'string', enum: ['SOUND', 'DEFECTIVE'] },
    defects: { type: 'array', items: { type: 'object', required: ['severity', 'location', 'claim', 'why_it_matters', 'reproduced'], properties: {
      severity: { type: 'string', enum: ['blocking', 'major', 'minor'] }, location: { type: 'string' }, claim: { type: 'string' }, why_it_matters: { type: 'string' }, reproduced: { type: 'boolean' } } } },
    tests_that_prove_nothing: { type: 'array', items: { type: 'string' } },
    worktree_left_byte_identical: { type: 'boolean' },
    files_sha256_at_start: { type: 'array', items: { type: 'string' } },
    summary: { type: 'string' },
    gates_not_measured: { type: 'array', items: { type: 'string' } },
    wall_clock: { type: 'string' },
  },
}

const corpusLine = PRICE_PATH
  ? 'Byte-identity gate (price path): scripts/verify_flag_byte_identity.py --proof-root C:/Users/SynAckITPC/Documents/AI/sc-w0-load/_proof --flags ' + CORPUS_FLAGS + ' must print the recorded OFF digests (' + CORPUS_OFF + '); then --flags-on ' + CORPUS_FLAGS + ' --compare must be equal with 0 differing records.'
  : 'No corpus gate for this unit; re-prove the flag-OFF / unflagged identity the spec and rulings name.'
const latestLine = LATEST_KEY
  ? 'The latest completed agent report is the JSON object under key "' + LATEST_KEY + '" in ' + LATEST
  : 'The latest completed agent report is at ' + LATEST
const guardLine = 'The bounded runner picks the network guard for this worktree by itself (plugin when tests/conftest.py does not wire tests/_netguard.py); state in your report which one applied.'

const fixPrompt = `You are the FIXER for unit ${KEY}, round ${ROUND}, in worktree ${DIR}. Spec: ${SPEC}. Shared rules: read ${COMMON_PATH} in full FIRST and obey every line (every pytest run through the bounded runner; your budget is 2 hours). Standing Fable rulings (binding): ${RULINGS}
${latestLine} - READ IT IN FULL FIRST and confirm the worktree's files carry exactly the shas it reports (or the shas the resume note below names) before you change anything; a mismatch = STOP and report it.
NEW FABLE RULINGS to apply now (binding; they amend the earlier rulings where they conflict):
${NEW}
${EXTRA}

For each new ruling: implement it MINIMALLY inside the unit's design; add or adjust load-bearing pins mutation-checked from byte snapshots (sha256-verified restores); keep every earlier pin green or adjust ONLY the pins the new rulings explicitly move. Then re-run through the bounded runner: the unit files (${UNIT_FILES}) in ${STATES}; ruff --select E9,F63,F7,F82 + py_compile on every edited module; the CI-order set in ONE process per state; the comm gate the spec/rulings define, in chunks of at most 25 files, one at a time. ${corpusLine} ${guardLine} Rewrite pr_text in FULL to reflect the final state (correct every wording error the adversary named). Never commit; leave only intended changes; report git status --short verbatim and the final sha256 of every file you wrote. Order the gates cheapest first; anything the budget does not fit goes in gates_not_measured with its [pyt] lines.`

const advPrompt = (fixRef, round) => `You are an ADVERSARIAL reviewer for unit ${KEY} (re-review round ${round}). Worktree: ${DIR}. Spec: ${SPEC}. Shared rules: read ${COMMON_PATH} in full FIRST and obey every line (every pytest run through the bounded runner; your budget is 90 minutes - cheapest checks first). Standing rulings: ${RULINGS}
${NEW ? 'NEW rulings the fixer had to apply:\n' + NEW : ''}
${fixRef}
${EXTRA}

Assume the work is wrong until checked. 0. FIRST record the sha256 of every file in the diff as found and compare with the report's (a mismatch is blocking - a killed agent can leave a mutant on disk); then re-run the unit files (${UNIT_FILES}) in ${STATES} through the bounded runner. 1. Verify each ruling is implemented as written and pinned (re-run the reported mutations from byte snapshots with sha-verified restores; try mutations the fixer did not). 2. Verify nothing outside the rulings moved (git diff hunk by hunk; CRLF hygiene; module globals resolved at call time; ${FLAG ? 'every fork under the per-call flag read, OFF byte-identical' : 'the unflagged identity the spec names'}). 3. Verify the CI-order and comm claims: the CI-order set in ONE process (at least the unset state, then the flag state(s) as the budget allows) and a sample of at least 25 comm-set files in CI order${PRICE_PATH ? '; verify the corpus JSONs (re-run OFF if missing)' : ''}. ${guardLine} 4. Check pr_text against the code for every factual claim. 5. Leave the worktree byte-identical (sha256 before and after, reported); reproduced:true only for what you ran; do not fix anything; anything the budget did not fit goes in gates_not_measured. If sound, say SOUND.`

const serious = (a) => (a && a.defects ? a.defects.filter((d) => d.severity !== 'minor') : [])
const rounds = []
let latest = null
let round = ROUND
if (START_AT === 'fix') {
  log('FIX round ' + round + ' for ' + KEY)
  latest = await agent(fixPrompt, { label: 'fix:' + KEY + '-r' + round, phase: 'Fix', model: MODEL, effort: 'high', schema: FIX_SCHEMA })
  if (!latest) return { unit: KEY, rounds, final_verdict: 'fixer died' }
}
const fixRefFor = (obj) => obj
  ? 'The fixer reported:\n' + JSON.stringify(obj, null, 1)
  : latestLine + ' - READ IT IN FULL FIRST; it is the report you are refuting (its label may name an earlier round number; the resume note says which round it really is).'
let adv = await agent(advPrompt(fixRefFor(latest), round), { label: 'adversary:' + KEY + '-r' + round, phase: 'Adversary', model: MODEL, effort: 'high', schema: ADV_SCHEMA })
rounds.push({ round, fix: latest, adversary: adv })
let n = 0
while (adv && (serious(adv).length || (adv.tests_that_prove_nothing || []).length) && n < MAX_FIX) {
  n += 1
  round += 1
  log('re-FIX round ' + round + ' for ' + KEY + ': ' + serious(adv).length + ' serious defect(s), ' + (adv.tests_that_prove_nothing || []).length + ' prove-nothing row(s)')
  const fixN = await agent(fixPrompt + '\n\nPREVIOUS RE-ADVERSARY FINDINGS to close as well (re-derive each from code; dispute with a measurement if wrong):\n' + JSON.stringify({ defects: adv.defects, tests_that_prove_nothing: adv.tests_that_prove_nothing }, null, 1), { label: 'fix:' + KEY + '-r' + round, phase: 'Fix', model: MODEL, effort: 'high', schema: FIX_SCHEMA })
  if (fixN) latest = fixN
  adv = await agent(advPrompt(fixRefFor(latest), round), { label: 'adversary:' + KEY + '-r' + round, phase: 'Adversary', model: MODEL, effort: 'high', schema: ADV_SCHEMA })
  rounds.push({ round, fix: fixN, adversary: adv })
}
const verdict = !adv ? 'adversary died' : (serious(adv).length ? 'DEFECTIVE' : ((adv.tests_that_prove_nothing || []).length ? 'SOUND with prove-nothing rows left' : 'SOUND'))
log('verdict ' + KEY + ': ' + verdict)
return { unit: KEY, latest, rounds, final_verdict: verdict }
