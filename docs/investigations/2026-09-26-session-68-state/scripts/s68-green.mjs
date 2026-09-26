export const meta = {
  name: 's68-green',
  description: 'Session 68 generic unit pipeline on Opus 5.5: Green (implement to the gated red under the Fable rulings, every gate) -> Adversary -> bounded Fix/re-Adversary rounds. Parameterised by args: key, dir, spec, redReport, rulings, unitFiles, flag, pricePath, corpusFlags, corpusOff, extra, maxFixRounds',
  phases: [
    { title: 'Green', detail: 'minimal implementation, every pin mutation-checked, comm + CI-order + byte-identity gates', model: 'claude-opus-5-5' },
    { title: 'Adversary', detail: 'independent attempt to refute on the exact bytes', model: 'claude-opus-5-5' },
    { title: 'Fix', detail: 'bounded fix rounds for blocking/major defects and prove-nothing rows, each followed by a re-adversary', model: 'claude-opus-5-5' },
  ],
}
const MODEL = 'claude-opus-5-5'
const A = args || {}
const KEY = A.key
const DIR = A.dir
const SPEC = A.spec
const RED = A.redReport
const RULINGS = A.rulings || ''
const UNIT_FILES = (A.unitFiles || []).join(' ')
const FLAG = A.flag || null
const PRICE_PATH = !!A.pricePath
const CORPUS_FLAGS = A.corpusFlags || FLAG || ''
const CORPUS_OFF = A.corpusOff || ''
const EXTRA = A.extra || ''
const MAX_FIX = typeof A.maxFixRounds === 'number' ? A.maxFixRounds : 2
const MYSP = 'C:/Users/SynAckITPC/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/b1819d0c-d9c5-466a-ba0d-b82774c624db/scratchpad'
const COMMON_PATH = MYSP + '/s68-common.txt'
if (!KEY || !DIR || !SPEC || !RED) { throw new Error('args.key, args.dir, args.spec, args.redReport are required') }

const GREEN_SCHEMA = {
  type: 'object',
  required: ['unit', 'files_changed', 'all_unit_tests_pass', 'test_evidence', 'lint_clean', 'mutation_checks', 'comm_gate', 'ci_order_run', 'byte_identity', 'measurements_run', 'pr_text', 'deviations_from_spec', 'git_status_final', 'residual_risk', 'scratch_cleanup'],
  properties: {
    unit: { type: 'string' },
    files_changed: { type: 'array', items: { type: 'string' }, description: '"<path> <sha256>" per file written or edited (final bytes)' },
    all_unit_tests_pass: { type: 'boolean', description: 'unit files green in every flag state the spec names' },
    test_evidence: { type: 'string', description: 'verbatim summary lines per flag state, with the [netguard] line' },
    lint_clean: { type: 'boolean' },
    mutation_checks: { type: 'array', items: { type: 'string' }, description: 'one per RED/PIN/KILL row and mutation-table row: the exact edit, the red node names observed, the sha256-verified restore' },
    comm_gate: { type: 'string', description: 'HEAD run over the recorded comm set (chunks, summary lines, netguard lines); every failure not in tests/.pre_impl_failures.txt re-run alone and at base per the spec; the final verdict' },
    ci_order_run: { type: 'string', description: 'the CI-order set (sorted) run in ONE process with the unit files: summary + failing ids vs the red report base run' },
    byte_identity: { type: 'string', description: 'price-path units: the corpus digests OFF (must equal the recorded ones) and the ON --compare result with wall times; other units: the flag-OFF / unflagged identity proof used' },
    measurements_run: { type: 'array', items: { type: 'string' } },
    pr_text: { type: 'string', description: 'ready-to-paste PR body: defect(s), design, flag row (default, effect ON, OFF identity, knobs), gates with their measured numbers, stated limits, follow-ups, CLAUDE.md corrections for the docs PR, issue references' },
    deviations_from_spec: { type: 'array', items: { type: 'string' } },
    git_status_final: { type: 'string' },
    residual_risk: { type: 'string' },
    scratch_cleanup: { type: 'string', description: 'git worktree list (no scratch worktree left) + no .env copy under the scratchpad' },
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
    files_sha256_at_start: { type: 'array', items: { type: 'string' }, description: '"<path> <sha256>" of every file in the diff as found at the start (and identical at the end)' },
    summary: { type: 'string' },
  },
}

const flagLine = FLAG
  ? 'Every new branch sits under a per-call reader of ' + FLAG + ' (default OFF); flag OFF executes the exact 61585c58 code paths and is byte-identical.'
  : 'This unit is unflagged by ruling; keep the change minimal and additive; prove the unflagged identity the spec names.'
const corpusLine = PRICE_PATH
  ? 'Byte-identity gate (price path): scripts/verify_flag_byte_identity.py --proof-root C:/Users/SynAckITPC/Documents/AI/sc-w0-load/_proof --flags ' + CORPUS_FLAGS + ' --out <scratch>/off.json must print the recorded OFF digests (' + CORPUS_OFF + '); then --flags-on ' + CORPUS_FLAGS + ' --compare <scratch>/off.json must report equal=True and 0 differing records; record both digests and wall times; if the OFF digest differs, STOP and report (do not rationalise). Never run _proof/sweep2.py.'
  : 'No corpus gate for this unit; the flag-OFF / unflagged identity proof is the one the spec names.'

const greenPrompt = `You are implementing the GREEN phase of unit ${KEY} (myez/Qaren backend). Worktree: ${DIR}. Spec (authoritative): ${SPEC}. Shared rules: read ${COMMON_PATH} in full FIRST and obey every line.
The RED phase report is at ${RED} - READ IT IN FULL FIRST (tests written, measured anchors, mutant survival, prototype notes, base run of the CI-order set).
FABLE GATE RULINGS for this unit (binding; they override the spec where they conflict):
${RULINGS || '(none beyond the spec)'}
${EXTRA}

STATE ON DISK: the red phase's test file(s) are UNCOMMITTED in the worktree (git status --short shows them); confirm FIRST that nothing else is modified; if anything unexpected is present, STOP and report.
YOUR TASK:
1. Implement EXACTLY the spec's design as amended by the rulings - minimal, no refactors, hunks function-local. ${flagLine} A prototype patch under .qa-s68/ (if the red left one) may be READ for its shape, never copied blindly - every line you write must be justified by a red or pin.
2. Run the unit files (${UNIT_FILES}) to green${FLAG ? ' with the flag UNSET and with ' + FLAG + '=true' : ''}; paste the summary lines with the [netguard] line.
3. MUTATION-CHECK every RED/PIN/KILL row and every mutation-table row in the spec (as amended) from byte snapshots with sha256-verified restores; record the exact edit, the red node names, the restore. A pin that survives removal of its fix must be rewritten (and reported).
4. Lint + py_compile on every edited module; CRLF hygiene (git diff --stat shows only the intended lines).
5. Comm gate HEAD over the recorded comm set (the spec says where it is and how failures are adjudicated: every failure not in tests/.pre_impl_failures.txt is re-run alone AND at base in a detached scratch worktree at 61585c58 - that file only - before it counts; a hung node is re-run alone before it counts). Chunk it; --timeout=60; CI's deselects.
6. CI-order run: the recorded .qa-s68/ci_order_set.txt (sorted alphabetically) INCLUDING the unit files, in ONE process; compare against the red report's base run; explain every difference.
7. ${corpusLine}
8. Write pr_text with every disclosure the spec and rulings require.
9. Leave the worktree with ONLY the intended files modified; never commit. Report git status --short verbatim, the final sha256 of every file you wrote, and the scratch cleanup.`

const advPrompt = (green, round) => `You are an ADVERSARIAL reviewer for unit ${KEY}. Your job is to REFUTE the work, not to bless it. Worktree: ${DIR}. Spec: ${SPEC}. Red report: ${RED}. Shared rules: read ${COMMON_PATH} in full FIRST. Fable gate rulings (binding):
${RULINGS || '(none beyond the spec)'}
${round > 0 ? 'RE-REVIEW ROUND ' + round + ': a fixer addressed the earlier defects. Verify each is closed by RE-RUNNING its mutation, then look again at everything the fix touched.' : ''}
The implementer reported:
${JSON.stringify(green, null, 1)}
${EXTRA}

Assume the implementation is wrong until checked.
0. FIRST re-run the unit files (${UNIT_FILES}) in every flag state the spec names and record the sha256 of every file in the diff as you find it - a killed agent can leave a mutant on disk; compare with the implementer's reported shas and report any mismatch as blocking.
1. Read the actual diff hunk by hunk (git diff; git status for new files) against the spec and rulings. ${FLAG ? 'Every new statement that forks behaviour must sit under a per-call read of ' + FLAG + '; flag OFF must be the exact 61585c58 path.' : 'The change must be minimal and additive; the unflagged identity the spec names must hold.'} CRLF hygiene (no whole-file diffs). Module globals resolved at call time, never aliased at import.
2. Re-run the reported mutation checks yourself from byte snapshots (never git checkout); try mutations the implementer did not; anything that survives removal of its fix goes in tests_that_prove_nothing. Leave the worktree byte-identical (sha256 before/after; report honestly).
3. Drive the unhappy paths through the REAL functions on the pinned venv (cancellation, exceptions inside offloaded blocks, boundary sizes, every accepted flag value, concurrency where the spec names it).
4. Verify the comm-gate and CI-order claims (re-run the unit files, the Preserve files and a SAMPLE of at least 25 comm-set files in CI order under the guard) and ${PRICE_PATH ? 'the byte-identity claim (read the gate JSONs and compare the results arrays yourself; re-run the OFF sweep if the JSONs are missing).' : 'the flag-OFF / unflagged identity claim through the real functions.'}
5. Report a defect as reproduced:true only if you ran something that demonstrated it. Do not pad; minors are minors. If sound, say SOUND. Do not fix anything.`

const fixPrompt = (adv) => `You are the FIXER for unit ${KEY} in worktree ${DIR}. Spec: ${SPEC}. Red report: ${RED}. Shared rules: read ${COMMON_PATH} in full FIRST. Fable gate rulings (binding):
${RULINGS || '(none beyond the spec)'}
The adversary found the defects and prove-nothing rows below. For each defect: re-derive it from code; if real, fix it MINIMALLY inside the spec's design as amended by the rulings, with a load-bearing pin mutation-checked from a byte snapshot; if you believe it is WRONG, do not fix it - dispute it in deviations_from_spec with a measurement. Fold every tests_that_prove_nothing row into a real pin or explain why it is a deliberate pin. Re-run the unit files (${UNIT_FILES}) in every flag state, ruff + py_compile, the CI-order set in one process, the comm gate HEAD run${PRICE_PATH ? ' and the byte-identity chain (OFF digests + ON --compare)' : ''}. Update pr_text. Never commit; leave only intended changes; report git status --short verbatim and the final sha256 of every file you wrote.
${EXTRA}
Defects:
${JSON.stringify(adv.defects, null, 1)}
tests_that_prove_nothing:
${JSON.stringify(adv.tests_that_prove_nothing, null, 1)}`

const serious = (a) => (a && a.defects ? a.defects.filter((d) => d.severity !== 'minor') : [])

log('GREEN ' + KEY + ' in ' + DIR)
const green = await agent(greenPrompt, { label: 'green:' + KEY, phase: 'Green', model: MODEL, effort: 'high', schema: GREEN_SCHEMA })
if (!green) return { unit: KEY, green: null, rounds: [], final_verdict: 'green died' }
const rounds = []
let latest = green
let adv = await agent(advPrompt(green, 0), { label: 'adversary:' + KEY + '-r0', phase: 'Adversary', model: MODEL, effort: 'high', schema: ADV_SCHEMA })
rounds.push({ round: 0, adversary: adv })
let n = 0
while (adv && (serious(adv).length || (adv.tests_that_prove_nothing || []).length) && n < MAX_FIX) {
  n += 1
  log('FIX round ' + n + ' for ' + KEY + ': ' + serious(adv).length + ' serious defect(s), ' + (adv.tests_that_prove_nothing || []).length + ' prove-nothing row(s)')
  const fix = await agent(fixPrompt(adv), { label: 'fix:' + KEY + '-r' + n, phase: 'Fix', model: MODEL, effort: 'high', schema: GREEN_SCHEMA })
  if (fix) latest = fix
  adv = await agent(advPrompt(latest, n), { label: 'adversary:' + KEY + '-r' + n, phase: 'Fix', model: MODEL, effort: 'high', schema: ADV_SCHEMA })
  rounds.push({ round: n, fix, adversary: adv })
}
const verdict = !adv ? 'adversary died' : (serious(adv).length ? 'DEFECTIVE after ' + n + ' fix round(s)' : ((adv.tests_that_prove_nothing || []).length ? 'SOUND with prove-nothing rows left' : 'SOUND'))
log('verdict ' + KEY + ': ' + verdict)
return { unit: KEY, green, latest, rounds, final_verdict: verdict }
