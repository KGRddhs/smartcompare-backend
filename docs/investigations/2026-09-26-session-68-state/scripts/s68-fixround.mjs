export const meta = {
  name: 's68-fixround',
  description: 'Session 68 targeted fix round on Opus 5.5 for a unit whose pipeline already ended SOUND: apply new Fable rulings (design corrections) with pins, then an independent re-adversary; one optional second fix round. Args: key, dir, spec, rulings, newRulings, latestReport, unitFiles, flag, pricePath, corpusFlags, corpusOff, extra',
  phases: [
    { title: 'Fix', detail: 'apply the new rulings minimally with load-bearing pins, re-run every gate', model: 'claude-opus-5-5' },
    { title: 'Adversary', detail: 'independent re-review on the exact bytes', model: 'claude-opus-5-5' },
  ],
}
const MODEL = 'claude-opus-5-5'
const A = args || {}
const KEY = A.key
const DIR = A.dir
const SPEC = A.spec
const RULINGS = A.rulings || ''
const NEW = A.newRulings || ''
const LATEST = A.latestReport
const UNIT_FILES = (A.unitFiles || []).join(' ')
const FLAG = A.flag || null
const PRICE_PATH = !!A.pricePath
const CORPUS_FLAGS = A.corpusFlags || FLAG || ''
const CORPUS_OFF = A.corpusOff || ''
const EXTRA = A.extra || ''
const MYSP = 'C:/Users/SynAckITPC/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/b1819d0c-d9c5-466a-ba0d-b82774c624db/scratchpad'
const COMMON_PATH = MYSP + '/s68-common.txt'
if (!KEY || !DIR || !SPEC || !LATEST || !NEW) { throw new Error('args.key, dir, spec, latestReport, newRulings are required') }

const FIX_SCHEMA = {
  type: 'object',
  required: ['unit', 'files_changed', 'all_unit_tests_pass', 'test_evidence', 'lint_clean', 'mutation_checks', 'comm_gate', 'ci_order_run', 'byte_identity', 'pr_text', 'deviations_from_spec', 'git_status_final', 'residual_risk', 'scratch_cleanup'],
  properties: {
    unit: { type: 'string' },
    files_changed: { type: 'array', items: { type: 'string' }, description: '"<path> <sha256>" of every file written or edited (final bytes) and of every unit file left as found' },
    all_unit_tests_pass: { type: 'boolean' },
    test_evidence: { type: 'string' },
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
  },
}
const ADV_SCHEMA = {
  type: 'object',
  required: ['unit', 'verdict', 'defects', 'tests_that_prove_nothing', 'worktree_left_byte_identical', 'files_sha256_at_start', 'summary'],
  properties: {
    unit: { type: 'string' },
    verdict: { type: 'string', enum: ['SOUND', 'DEFECTIVE'] },
    defects: { type: 'array', items: { type: 'object', required: ['severity', 'location', 'claim', 'why_it_matters', 'reproduced'], properties: {
      severity: { type: 'string', enum: ['blocking', 'major', 'minor'] }, location: { type: 'string' }, claim: { type: 'string' }, why_it_matters: { type: 'string' }, reproduced: { type: 'boolean' } } } },
    tests_that_prove_nothing: { type: 'array', items: { type: 'string' } },
    worktree_left_byte_identical: { type: 'boolean' },
    files_sha256_at_start: { type: 'array', items: { type: 'string' } },
    summary: { type: 'string' },
  },
}

const corpusLine = PRICE_PATH
  ? 'Byte-identity gate (price path): scripts/verify_flag_byte_identity.py --proof-root C:/Users/SynAckITPC/Documents/AI/sc-w0-load/_proof --flags ' + CORPUS_FLAGS + ' must print the recorded OFF digests (' + CORPUS_OFF + '); then --flags-on ' + CORPUS_FLAGS + ' --compare must be equal with 0 differing records.'
  : 'No corpus gate for this unit; re-prove the flag-OFF / unflagged identity the spec names.'

const fixPrompt = `You are the FIXER for unit ${KEY} in worktree ${DIR}. Spec: ${SPEC}. Shared rules: read ${COMMON_PATH} in full FIRST. Standing Fable rulings (binding): ${RULINGS}
The unit's pipeline ended SOUND; the latest implementer/fixer report (files, shas, pr_text, gates) is at ${LATEST} - READ IT IN FULL FIRST and confirm the worktree's files carry exactly the shas it reports before you change anything (a mismatch = STOP and report).
NEW FABLE RULINGS to apply now (binding; they amend the earlier rulings where they conflict):
${NEW}
${EXTRA}

For each new ruling: implement it MINIMALLY inside the unit's design; add or adjust load-bearing pins mutation-checked from byte snapshots (sha256-verified restores); keep every earlier pin green or adjust ONLY the pins the new rulings explicitly move. Then re-run: the unit files (${UNIT_FILES})${FLAG ? ' with the flag UNSET and with ' + FLAG + '=true' : ''}; ruff --select E9,F63,F7,F82 + py_compile on every edited module; the CI-order set in one process; the comm gate the spec/rulings define. ${corpusLine} Rewrite pr_text in FULL to reflect the final state (correct every wording error the adversary named). Never commit; leave only intended changes; report git status --short verbatim and the final sha256 of every file you wrote.`

const advPrompt = (fix, round) => `You are an ADVERSARIAL reviewer for unit ${KEY} (re-review round ${round} after a targeted fix). Worktree: ${DIR}. Spec: ${SPEC}. Shared rules: read ${COMMON_PATH} in full FIRST. Standing rulings: ${RULINGS}
NEW rulings the fixer had to apply:
${NEW}
The fixer reported:
${JSON.stringify(fix, null, 1)}
${EXTRA}

Assume the fix is wrong until checked. 0. Re-run the unit files (${UNIT_FILES}) first and record the sha256 of every file in the diff as found (compare with the fixer's; a mismatch is blocking). 1. Verify each new ruling is implemented as written and pinned (re-run the fixer's mutations from byte snapshots; try your own). 2. Verify nothing outside the rulings moved (git diff hunk by hunk; CRLF hygiene; module globals resolved at call time; ${FLAG ? 'every fork under the per-call flag read, OFF byte-identical' : 'the unflagged identity the spec names'}). 3. Verify the CI-order and comm claims by re-running the CI-order set (one process) and a sample of the comm set${PRICE_PATH ? '; verify the corpus JSONs (re-run OFF if missing)' : ''}. 4. Check pr_text against the code for every factual claim. 5. Leave the worktree byte-identical; reproduced:true only for what you ran; do not fix anything. If sound, say SOUND.`

const serious = (a) => (a && a.defects ? a.defects.filter((d) => d.severity !== 'minor') : [])
log('FIX ROUND ' + KEY)
const fix = await agent(fixPrompt, { label: 'fix:' + KEY + '-r2', phase: 'Fix', model: MODEL, effort: 'high', schema: FIX_SCHEMA })
if (!fix) return { unit: KEY, fix: null, final_verdict: 'fixer died' }
let adv = await agent(advPrompt(fix, 2), { label: 'adversary:' + KEY + '-r2', phase: 'Adversary', model: MODEL, effort: 'high', schema: ADV_SCHEMA })
let latest = fix
const rounds = [{ round: 2, fix, adversary: adv }]
if (adv && (serious(adv).length || (adv.tests_that_prove_nothing || []).length)) {
  log('one more fix round for ' + KEY)
  const fix3 = await agent(fixPrompt + '\n\nPREVIOUS RE-ADVERSARY FINDINGS to close as well:\n' + JSON.stringify({ defects: adv.defects, tests_that_prove_nothing: adv.tests_that_prove_nothing }, null, 1), { label: 'fix:' + KEY + '-r3', phase: 'Fix', model: MODEL, effort: 'high', schema: FIX_SCHEMA })
  if (fix3) latest = fix3
  adv = await agent(advPrompt(latest, 3), { label: 'adversary:' + KEY + '-r3', phase: 'Adversary', model: MODEL, effort: 'high', schema: ADV_SCHEMA })
  rounds.push({ round: 3, fix: fix3, adversary: adv })
}
const verdict = !adv ? 'adversary died' : (serious(adv).length ? 'DEFECTIVE' : ((adv.tests_that_prove_nothing || []).length ? 'SOUND with prove-nothing rows left' : 'SOUND'))
log('verdict ' + KEY + ': ' + verdict)
return { unit: KEY, latest, rounds, final_verdict: verdict }
