export const meta = {
  name: 's68-w4-red',
  description: 'Session 68 W4 unit RED phase on Opus 5.5: from a measured, adversarially reviewed spec + Fable rulings, re-anchor at the worktree HEAD, write the red tests exactly as ruled, prove every RED/PIN/KILL row, prototype satisfiability in a detached scratch worktree, record the comm and CI-order sets. Args: key, dir, spec, review (same file), rulings, extra, client',
  phases: [
    { title: 'Red', detail: 'measure at HEAD, write the tests, prove right-reason reds, prototype, record sets', model: 'claude-opus-5-5' },
  ],
}
const MODEL = 'claude-opus-5-5'
const A = args || {}
const KEY = A.key
const DIR = A.dir
const SPEC = A.spec
const RULINGS = A.rulings
const EXTRA = A.extra || ''
const CLIENT = !!A.client
const MYSP = 'C:/Users/SynAckITPC/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/b1819d0c-d9c5-466a-ba0d-b82774c624db/scratchpad'
const COMMON_PATH = MYSP + '/s68-common.txt'
if (!KEY || !DIR || !SPEC || !RULINGS) { throw new Error('args.key, dir, spec, rulings are required') }

const RED_SCHEMA = {
  type: 'object',
  required: ['unit', 'head_sha', 'base_sha_confirmed', 'anchors_redone', 'files_written', 'red_count', 'pin_count', 'kill_count', 'failures_are_right_reason', 'failure_evidence', 'pins_evidence', 'kill_evidence', 'prototype', 'comm_set', 'ci_order_set_base_run', 'preserve_run', 'measurements', 'spec_disagreements', 'questions_for_fable', 'git_status_final', 'scratch_cleanup'],
  properties: {
    unit: { type: 'string' },
    head_sha: { type: 'string', description: 'the worktree HEAD you measured against (the spec base may be older; every anchor is re-located here)' },
    base_sha_confirmed: { type: 'boolean', description: 'git status --short empty at start except the gitignored .qa-s68/' },
    anchors_redone: { type: 'array', items: { type: 'string' }, description: 'spec anchor -> symbol -> line at HEAD; note any drift since the spec base' },
    files_written: { type: 'array', items: { type: 'string' }, description: '"<path> <sha256>" per file (final bytes)' },
    red_count: { type: 'integer' },
    pin_count: { type: 'integer' },
    kill_count: { type: 'integer' },
    failures_are_right_reason: { type: 'boolean' },
    failure_evidence: { type: 'string', description: 'verbatim summary lines per flag state + one sentence per RED row naming the genuine absent behaviour' },
    pins_evidence: { type: 'string', description: 'every PIN green at HEAD: node names + summary' },
    kill_evidence: { type: 'string', description: 'per KILL/hardening row: the mutant applied, the red node names, the sha256-verified restore' },
    prototype: { type: 'string', description: 'satisfiability prototype in a detached scratch worktree: diff stat, unit files green in every flag state, the patch saved under .qa-s68/, worktree removed; any row the design cannot satisfy' },
    comm_set: { type: 'string', description: 'the recorded comm set path, derivation rule, size; the BASE failed-id file if a base run was made' },
    ci_order_set_base_run: { type: 'string', description: '.qa-s68/ci_order_set.txt (sorted) + its ONE-process run at HEAD WITHOUT the new files: summary + failing ids marked vs tests/.pre_impl_failures.txt' },
    preserve_run: { type: 'string', description: 'the Preserve files at HEAD: summary line' },
    measurements: { type: 'array', items: { type: 'string' } },
    spec_disagreements: { type: 'array', items: { type: 'string' }, description: 'spec/review/ruling claims found WRONG when tested at HEAD, with the measurement' },
    questions_for_fable: { type: 'array', items: { type: 'string' } },
    git_status_final: { type: 'string' },
    scratch_cleanup: { type: 'string' },
  },
}

const clientNote = CLIENT
  ? ' CLIENT UNIT: SmartCompareApp/node_modules is a JUNCTION into the shared clone - run jest/tsc/eslint by PATH from SmartCompareApp (node node_modules/jest/bin/jest.js --ci, node node_modules/typescript/bin/tsc --noEmit, node node_modules/eslint/bin/eslint.js) and print the versions; NEVER run npm install/ci/uninstall/prune/dedupe; never remove or recreate the junction; jest snapshots are never updated (-u forbidden).'
  : ''

const prompt = `You are running the RED phase of W4 unit ${KEY} (myez/Qaren). Worktree: ${DIR} (its HEAD is the current origin/main; the spec was measured at an older base - re-anchor everything by symbol at HEAD and report drift). Shared rules: read ${COMMON_PATH} in full FIRST and obey every line.${clientNote}

AUTHORITATIVE DOCUMENTS, in precedence order (highest first):
1. ${RULINGS} - Fable's binding rulings; they override everything below where they differ.
2. The section "# ADVERSARIAL SPEC REVIEW (2026-09-26, session 68)" appended at the END of ${SPEC} - its refuted claims and corrections are binding unless a ruling says otherwise.
3. The spec body of ${SPEC} (measured at its base SHA).
The sibling files in the same folder (.qa-s68/specs/${KEY.replace('-', '_').toUpperCase()}_* - comm sets, base-failed lists, probes, fixtures, render digests) are the measurer's artefacts: read and reuse them, verify before trusting.
${EXTRA}

YOUR TASK, in order:
0. Confirm 'git status --short' is empty (the .qa-s68/ folder is gitignored). Record HEAD. Re-locate every anchor the spec and review cite by symbol at HEAD; if a later merge changed the behaviour a red claim rests on, RE-MEASURE the claim (paste) and record it in spec_disagreements.
1. RE-MEASURE at HEAD every red claim the rulings keep (the real functions through pytest probes under the guard; jest for client claims): each HOLDS / CHANGED / REFUTED with the pasted value. Where a ruling changed the design (e.g. a new rule, threshold or flag), measure the HEAD behaviour the new red will assert against.
2. WRITE the tests exactly as the spec's test list stands after the review's corrections and the rulings: the named files, the named test ids, docstrings stating RED / PIN / KILL and the reason; every RED fails at HEAD on an assertion naming the absent behaviour (a missing symbol is asserted for inside the test body - never a collection-time ImportError/AttributeError); every PIN is green at HEAD; every KILL row is green at HEAD and red under its named mutant (build it from a byte snapshot, run, restore, sha256-verify). Own autouse fixtures per the repo pattern (zero-network guard incl. curl_cffi.requests.get, flag/env reset, and any cache/singleton reset the spec names). New symbols are imported INSIDE test bodies.
3. RUN the new files in every flag state the spec names; paste the summaries; run every existing file the spec's Preserve list names (paste). Run the flag-OFF pins with every relevant flag exported ON too where the review asked for it.
4. SATISFIABILITY PROTOTYPE: in a detached scratch worktree at HEAD under your scratchpad, implement the ruled design MINIMALLY, copy the new tests in, run the unit files in every flag state (all green - paste), ruff + py_compile; save 'git diff' of the app/ (and client src/) changes to ${DIR}/.qa-s68/proto_${KEY}.patch (gitignored; the green may READ it); run the spec's byte-identity / equality gate ONCE on the prototype if it is cheap (< 10 minutes) and paste the digests, else say so; remove the scratch worktree (git worktree remove --force; confirm with git worktree list). Any red row the design cannot satisfy: STOP the prototype, keep the tests, report the row.
5. DERIVE and write ${DIR}/.qa-s68/comm_set.txt (the spec's comm rule as amended by the review - the UNION, sorted) and ${DIR}/.qa-s68/ci_order_set.txt (the spec's CI-order pin set as amended, plus the new files, sorted alphabetically). Run the CI-order set MINUS the new files in ONE process at HEAD under the guard (--timeout=60, CI's deselects from tests/.pre_impl_failures.txt); paste the summary and every failing id marked vs the baseline file. Do NOT run the whole comm set (the green does); if the spec's base-failed list exists, re-verify its failing ids still fail at HEAD alone (paste).
6. Report per the schema. Leave the worktree with ONLY the new/edited test files (and fixtures the spec names) changed plus the gitignored .qa-s68/ files; 'git status --short' verbatim; never commit; no scratch worktree left; no .env anywhere under your scratchpad.`

log('W4 RED ' + KEY + ' in ' + DIR)
const red = await agent(prompt, { label: 'red:' + KEY, phase: 'Red', model: MODEL, effort: 'high', schema: RED_SCHEMA })
return { unit: KEY, red }
