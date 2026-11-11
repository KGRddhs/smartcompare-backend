export const meta = {
  name: 'inc-unit-spec',
  description: 'Incident fix lane: per unit a spec writer (measured at base) then an adversarial spec reviewer; returns both for the orchestrator rulings',
  phases: [
    { title: 'Spec', detail: 'one spec writer per unit, measured at base, writes <worktree>/.qa-s80/<ID>_UNIT_SPEC.md' },
    { title: 'Review', detail: 'one adversarial reviewer per unit, re-measures, writes <ID>_SPEC_REVIEW.md' },
  ],
}

// args: { units: [{id, title, worktree, branch, flag, defects, brief, redFiles, webResearch}], common, report, plan, r0, defectLedger, record, baseSha, pyt, scratch, readOnly, review }
const A = args
const READ_ONLY = A.readOnly
  ? 'THIS ROUND IS READ-ONLY (header rule H5 c): the box slot for gate-heavy rounds is not granted. Run NO pytest, NO jest, NO tsc and NO eslint, and create no scratch worktree that needs node_modules. Measure with git show, git grep and file reads at the base sha. Every run the template asks for (section 1.10, any probe that needs the test runner) is written down with its exact runner command and marked DEFERRED TO RED.'
  : 'Bounded runner: python "' + A.pyt + '" (read its --help first; every pytest goes through it, one process at a time; it waits by itself for the box slot, header rule H5; paste the [pyt] line with every summary).'
const RULES = [
  'Common brief (read it FIRST and again before reporting; its header H0-H7 overrides the older text below it): ' + A.common,
  'The verified incident report (the root causes, the fix plan and the PROOF ON THE PHONE per fix; binding input): ' + A.report,
  'Plan of record of the session-81 lane, PLAN_S81 (its Standing constraints, the VERIFY-stage corrections, the Fable rulings F1-F4 and the owner decisions 1-12 stay binding on every unit): ' + A.plan,
  'Lane rulings R0 of the incident lane (the classification, the flag rulings, the proof standard, the box rules): ' + A.r0,
  'Unit ledger of the incident lane: ' + A.defectLedger + '. The record copy of every docs file (read docs there, never from a docs checkout): ' + A.record,
  'Base sha for every measurement: ' + A.baseSha + '. ' + READ_ONLY,
  'You never run git write commands (no add/commit/checkout/switch/stash/reset/rebase/merge/clean) in any existing worktree; probes that need an editable copy use a scratch copy under your notes folder (' + A.scratch + ') and are deleted afterwards. You never read or print .env or any secret value; variable NAMES only. Production flag state comes only from the dated ledger lines in the record copy (header H2). No personal values in any file. Pure ASCII and LF in every file you write; check bytes > 127 after each write. Write the spec / review file THROUGH THE SHELL (python or a quoted heredoc), never with the Write tool.',
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
    deploy_visible_delta: { type: 'array', items: { type: 'string' } },
    red_rows: { type: 'integer' },
    pin_rows: { type: 'integer' },
    mutants: { type: 'integer' },
    comm_set_size: { type: 'integer' },
    deliberate_pin_changes: { type: 'array', items: { type: 'string' } },
    stated_limits: { type: 'array', items: { type: 'string' } },
    focus_surfaces_found: { type: 'array', items: { type: 'string' } },
    answers_to_brief_questions: { type: 'array', items: { type: 'string' } },
    open_questions: { type: 'array', items: { type: 'string' } },
    deferred_to_red: { type: 'array', items: { type: 'string' } },
    pyt_lines: { type: 'array', items: { type: 'string' } },
  },
  required: ['unit', 'spec_path', 'spec_sha256', 'summary', 'change_list', 'deploy_visible_delta', 'red_rows', 'pin_rows', 'mutants', 'comm_set_size', 'answers_to_brief_questions', 'open_questions'],
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

function web(u) {
  return u.webResearch
    ? 'WEB RESEARCH GRANT (this agent only, read-only, OFFICIAL documentation of the named vendors only): ' + u.webResearch + ' Cite each URL; never send any project value, credential or personal value in a request.'
    : 'No web access is granted in this round: measure library behaviour on the pinned versions in the venv and the lock files.'
}

function specPrompt(u) {
  return [
    'You are the SPEC WRITER for unit ' + u.id + ': ' + u.title + '.',
    RULES,
    'Worktree to measure (read-only for you; detached at the base sha): ' + u.worktree + '. Branch GREEN will create: ' + u.branch + '. Flag ruling: ' + u.flag + ' Units / defects closed: ' + u.defects + '. RED file names: ' + u.redFiles + '.',
    'Unit brief from the orchestrator (authoritative; read it in full ONCE at the start and again before reporting; its numbered rulings bind you and its questions Q1..Qn are answered by measurement in your section 11 and in answers_to_brief_questions): ' + u.brief,
    web(u),
    'Write the spec to ' + u.worktree + '/.qa-s80/' + u.id + '_UNIT_SPEC.md (the .qa-*/ directory is gitignored). Use the house template of the two worked examples in the record copy (s79/B3B_APPLE_REVOKE_UNIT_SPEC.md, s79/S78_F8_UNIT_SPEC.md): header (unit id, the flag ruling, worktree, branch, base sha full, git status --short empty, evidence pointers, sister units and contracts, the personal-data rule); 0 what the unit does; 1 base state MEASURED (the exact code paths with file:line, the flag-reader idiom, libraries on the pinned venv, guards the new code must not trip, line endings, and 1.10 the base pass state of the files you will touch); 2 contract (flags and knobs; every new key, path, log line and event with its type; the failure table; the flag-OFF identity and, for a part ruled unflagged, the EXACT deploy-visible delta as the main invariant; test seams with production values in brackets); 3 change list in the order GREEN applies it (opens with byte copies, closes with "No other file"); 4 existing pins (4.1 pins that change deliberately, one E-row each with the reason; 4.2 pins that must stay green and unedited); 5 RED tests (hermetic; every row a RED that fails at base on an AssertionError only or a PIN that is green at base and runs WITH the full configuration and call recorders so a not-gated mutant is killed); 6 mutation table (each mutant on a byte copy, restored and sha-checked; name the row that kills it); 7 comm set and gates for GREEN (the union rule of the common brief incl. the source-scanning pins, the module-path / glob / path-segment readers, the importer closure to a fixpoint incl. app/main.py users, the CLAUDE.md readers, the fourteen backend-scanning client jest fences if any literal they read moves; the CI-order set), cheapest first; 8 the CLAUDE.md block text, its anchor, and the owner steps (names only); 8b PROOF ON THE PHONE (header H6: the pair or the read to repeat, what must be visible, the backing row or log check, and what is NOT provable in production); 9 stated limits; 10 out of scope; 11 open questions for the orchestrator and the answers to the brief questions. Close with "Not done in this spec".',
    'Contract freeze: re-read PLAN_S80 section 0 and contract_freeze.json (record copy, s80/) before writing section 2; new keys are additive; never a bare 503 (the error-handler mapping turns a codeless 503 into FEATURE_DISABLED).',
    'Measure, do not assume: every file:line you cite was read at the base sha in this run. Flag anything you could not verify instead of guessing; state each assumption with the reason it beats the alternative. Return the structured output; the spec file is the deliverable. deploy_visible_delta lists, in plain words, everything that changes in production when this unit is deployed with every flag at its default.',
  ].join('\n\n')
}

function reviewPrompt(u, spec) {
  return [
    'You are the ADVERSARIAL SPEC REVIEWER for unit ' + u.id + ': ' + u.title + '. Your job is to REFUTE the spec: default to doubt.',
    RULES,
    'Worktree (read-only): ' + u.worktree + '. The spec: ' + spec.spec_path + ' (sha256 ' + spec.spec_sha256 + '; re-hash it first). Flag ruling: ' + u.flag + ' Units / defects: ' + u.defects + '. The unit brief (authoritative over the spec where they differ; a spec that widens a ruling is a finding): ' + u.brief,
    web(u),
    'Re-measure EVERY file:line the spec cites at the base sha and run your own probes in a scratch copy under your notes folder, never in the worktree. Check these defect classes: vacuous PIN rows (a config check preceding every observable action makes a no-call PIN unable to kill a not-gated mutant); mutants no RED row can kill; comm-set files missing (symbol-only importers, patch-string references, the source-scanning pins, module-path readers, SmartCompareApp-scanning tests, app/main.py users); flag-OFF byte identity not actually pinned; for a part ruled UNFLAGGED: any production-visible change beyond the deploy_visible_delta the spec states (a changed response key, a changed status code, a changed log level on an existing line, an added await or I/O on the request path, a changed exception object or traceback, a /health body change before any outcome was recorded); a response key removed, renamed or retyped for the store binary (683f56c0) or the OTA bundle (f1e20c39); a new public path that meets a middleware, a rate limiter or an allowlist the spec did not measure; a background task that can outlive shutdown or delay the drain; a credential, key prefix, header, URL or exception text that can reach a log line, an event, a tag or the /health body; an alert that fires per call instead of per state change, or twice for one change; pin collisions (the OpenAPI snapshot pins, prompt-digest pins, the source-scanning pins on the dispatch chokepoints, the /health readers, copy-policy fences) not listed in section 4.1; the error-handler code mapping (a codeless 503 becomes FEATURE_DISABLED); an overlap with the statements S81-04c edits (header H1); a stated limit that is actually a defect; a PROOF ON THE PHONE section that could pass while the production problem remains.',
    'Write the review to ' + u.worktree + '/.qa-s80/' + u.id + '_SPEC_REVIEW.md: verdict, refuted claims (each with the measured truth and file:line), corrections, blocking issues, contract risks, pin collisions, and numbered questions for the orchestrator. Return the structured output.',
  ].join('\n\n')
}

phase('Spec')
const out = await pipeline(
  A.units,
  u => agent(specPrompt(u), { label: 'spec:' + u.id, phase: 'Spec', schema: SPEC_SCHEMA }),
  (spec, u) => (spec && A.review !== false)
    ? agent(reviewPrompt(u, spec), { label: 'review:' + u.id, phase: 'Review', schema: REVIEW_SCHEMA }).then(review => ({ unit: u.id, spec, review }))
    : { unit: u.id, spec: spec || null, review: null },
)
const done = out.filter(Boolean)
log('units with a spec: ' + done.filter(d => d.spec).length + '/' + A.units.length + '; with a review: ' + done.filter(d => d.review).length)
return done
