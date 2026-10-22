export const meta = {
  name: 's80-unit-spec',
  description: 'Per unit: spec writer (measured at base) then adversarial spec reviewer (agents run on the pinned model); returns both for the orchestrator rulings',
  phases: [
    { title: 'Spec', detail: 'one spec writer per unit, measured at base, writes <worktree>/.qa-s80/<ID>_UNIT_SPEC.md' },
    { title: 'Review', detail: 'one adversarial reviewer per unit, re-measures, writes <ID>_SPEC_REVIEW.md' },
  ],
}

// args: { units: [{id, title, worktree, flag, defects, brief}], common, plan, r0, defectLedger, baseSha, pyt, scratch }
const A = args
const RULES = [
  'Common brief (read it FIRST and again before reporting): ' + A.common,
  'Plan of record PLAN_S81 (Standing constraints, the VERIFY-stage corrections, Fable rulings F1-F4 and the unit text under Milestones are binding; owner decisions 1-12 are rulings): ' + A.plan,
  'R0 rulings (measured answers that gate this unit): ' + A.r0,
  'Defect ledger (the MYEZ ids this unit closes): ' + A.defectLedger,
  'Base sha for every measurement: ' + A.baseSha + '. Bounded runner: python "' + A.pyt + '" (read its --help first; every pytest goes through it, one process at a time, paste the [pyt] line with every summary).',
  'You never run git write commands (no add/commit/checkout/switch/stash/reset/rebase/merge/clean) in any existing worktree; probes that need an editable copy use a scratch copy under your scratchpad (' + A.scratch + ') and are deleted afterwards. You never read or print .env or any secret value; variable NAMES only. Production flag state comes only from the newest dated ledger line (docs/investigations/2026-10-22-session-81-state/ledger.md on the docs checkout, then the session-80 ledger). No personal values in any file. Pure ASCII and LF in every file you write; check bytes > 127 after each write.',
].join('\n')

const SPEC_SCHEMA = {
  type: 'object',
  properties: {
    unit: { type: 'string' },
    spec_path: { type: 'string' },
    spec_sha256: { type: 'string' },
    summary: { type: 'string' },
    base_measurements: { type: 'array', items: { type: 'string' } },
    change_list: { type: 'array', items: { type: 'string' } },
    red_rows: { type: 'integer' },
    pin_rows: { type: 'integer' },
    mutants: { type: 'integer' },
    comm_set_size: { type: 'integer' },
    deliberate_pin_changes: { type: 'array', items: { type: 'string' } },
    stated_limits: { type: 'array', items: { type: 'string' } },
    open_questions: { type: 'array', items: { type: 'string' } },
    pyt_lines: { type: 'array', items: { type: 'string' } },
  },
  required: ['unit', 'spec_path', 'spec_sha256', 'summary', 'change_list', 'red_rows', 'pin_rows', 'mutants', 'comm_set_size', 'open_questions'],
}

const REVIEW_SCHEMA = {
  type: 'object',
  properties: {
    unit: { type: 'string' },
    review_path: { type: 'string' },
    verdict: { type: 'string', enum: ['APPROVE', 'APPROVE_WITH_CHANGES', 'BLOCK'] },
    refuted_claims: { type: 'array', items: { type: 'string' } },
    corrections: { type: 'array', items: { type: 'string' } },
    blocking: { type: 'array', items: { type: 'string' } },
    contract_risks: { type: 'array', items: { type: 'string' } },
    pin_collisions: { type: 'array', items: { type: 'string' } },
    questions_for_orchestrator: { type: 'array', items: { type: 'string' } },
    pyt_lines: { type: 'array', items: { type: 'string' } },
  },
  required: ['unit', 'review_path', 'verdict', 'refuted_claims', 'corrections', 'blocking', 'questions_for_orchestrator'],
}

function specPrompt(u) {
  return [
    'You are the SPEC WRITER for unit ' + u.id + ': ' + u.title + '.',
    RULES,
    'Worktree to measure (read-only for you; detached at the base sha): ' + u.worktree + '. Dark flag: ' + u.flag + ' (default OFF, read per call with the house idiom; flag OFF must be byte-identical). Defects closed: ' + u.defects + '.',
    'Unit brief from the orchestrator: ' + u.brief,
    'Write the spec to ' + u.worktree + '\\.qa-s80\\' + u.id + '_UNIT_SPEC.md (the .qa-*/ directory is gitignored). Use the house template measured in the harness digest and the B3-B / S78-F8 worked examples (docs checkout: docs/investigations/2026-10-17-session-79-state/specs/B3B_APPLE_REVOKE_UNIT_SPEC.md, S78_F8_UNIT_SPEC.md): header (unit id, flag, worktree, branch feature/s81-<slug>, base sha full, git status --short empty, evidence pointers, sister units and contracts, the personal-data rule); 0 what the unit does; 1 base state MEASURED (the exact code paths with file:line, the flag-reader idiom, libraries on the pinned venv, guards the new code must not trip, line endings, and 1.10 the base pass state of the files you will touch, each run through the bounded runner with its [pyt] line); 2 contract (flag and knobs; every new key and its type; failure table; flag-OFF identity as the main invariant; test seams with production values in brackets); 3 change list in the order GREEN applies it; 4 existing pins (4.1 pins that change deliberately, one row each with the reason; 4.2 pins that must stay green and unedited); 5 RED tests (file names tests/test_s81_<unit>.py, hermetic, every row a RED that fails at base on an AssertionError only or a PIN that is green at base and runs WITH full configuration and call recorders so gated mutants are killable; fixtures built from the unit brief and, where a tester scenario applies, from the session-80 runs/research/eval_regression.json (sc-docs-70/docs/investigations/2026-10-19-session-80-state/)); 6 mutation table (each mutant on a byte copy, restored and sha-checked; name the row that kills it); 7 comm set and gates for GREEN (module and symbol reference grep UNION the source-scanning pins UNION the CLAUDE.md readers UNION the SmartCompareApp-scanning tests when client-visible, cheapest first); 8 the CLAUDE.md flag row text and owner steps; 9 stated limits; 10 out of scope; 11 open questions for the orchestrator.',
    'Contract freeze: re-read PLAN_S80 section 0 and its runs/research/contract_freeze.json (sc-docs-70/docs/investigations/2026-10-19-session-80-state/) before writing section 2; a refusal travels only through the envelopes build 3 renders; new keys are additive; never a bare 503.',
    'Measure, do not assume: every file:line you cite was read at the base sha in this run. Return the structured output; the spec file is the deliverable.',
  ].join('\n\n')
}

function reviewPrompt(u, spec) {
  return [
    'You are the ADVERSARIAL SPEC REVIEWER for unit ' + u.id + ': ' + u.title + '. Your job is to REFUTE the spec: default to doubt.',
    RULES,
    'Worktree (read-only): ' + u.worktree + '. The spec: ' + spec.spec_path + ' (sha256 ' + spec.spec_sha256 + '; re-hash it first). Flag: ' + u.flag + '. Defects: ' + u.defects + '.',
    'Re-measure EVERY file:line the spec cites at the base sha and run your own probes in a scratch copy under your scratchpad, never in the worktree. Check these defect classes found in session 79: vacuous PIN rows (a config check preceding every observable action makes a no-call PIN unable to kill a not-gated mutant); mutants no RED row can kill; comm-set files missing (symbol-only importers, patch-string references, the source-scanning pins, SmartCompareApp-scanning tests); flag-OFF byte identity not actually pinned; a response key removed, renamed or retyped; a refusal that would reach build 3 through a shape it cannot render (PLAN section 0); billing (R-A3): any abstain that still consumes a credit, bumps the lifetime counter or writes a history row; pin collisions (T23 OpenAPI, FY25 digests, w4_11 prompt digests, test_retro_w2_1 URL pins, the W4-13 ledger fixture, copy-policy fences) not listed in section 4.1; the camera failure envelope interaction; cache keys without a category or language axis; the error-handler code mapping (a codeless 503 becomes FEATURE_DISABLED); a stated limit that is actually a defect.',
    'Write the review to ' + u.worktree + '\\.qa-s80\\' + u.id + '_SPEC_REVIEW.md: verdict, refuted claims (each with the measured truth and file:line), corrections, blocking issues, contract risks, pin collisions, and numbered questions for the orchestrator. Return the structured output.',
  ].join('\n\n')
}

phase('Spec')
const out = await pipeline(
  A.units,
  u => agent(specPrompt(u), { label: 'spec:' + u.id, phase: 'Spec', schema: SPEC_SCHEMA }),
  (spec, u) => spec ? agent(reviewPrompt(u, spec), { label: 'review:' + u.id, phase: 'Review', schema: REVIEW_SCHEMA }).then(review => ({ unit: u.id, spec, review })) : { unit: u.id, spec: null, review: null },
)
const done = out.filter(Boolean)
log('units with spec+review: ' + done.filter(d => d.spec && d.review).length + '/' + A.units.length)
return done
