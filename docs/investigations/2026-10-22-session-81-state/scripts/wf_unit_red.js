export const meta = {
  name: 's80-unit-red',
  description: 'Per unit: one Fable RED agent writes the hermetic tests, proves every row fails at base for the right reason, prototypes ON/OFF, runs the mutation table and the base comm set, restores and reports',
  phases: [{ title: 'RED', detail: 'one RED agent per unit, sequential pytest through the bounded runner' }],
}

// args: { units: [{id, title, worktree, flag, specPath, reviewPath, rulingsSection, notMeasured: [files]}], common, plan, r0, rulings, baseSha, pyt, scratch }
const A = args
const RULES = [
  'Common brief (read first and again before reporting): ' + A.common,
  'Plan (sections 0 and 1 binding): ' + A.plan + ' . R0 rulings: ' + A.r0 + ' . Batch rulings (your unit section is binding; it amends the spec and the review): ' + A.rulings,
  'Base sha: ' + A.baseSha + ' . Bounded runner: python "' + A.pyt + '" --bound <s> --tag <tag> --log <file> --cwd <worktree> -- <pytest args> (read its --help first). Bounds: a unit file / a pin file / one mutant run 600 s; a CI-order set or a comm chunk of at most 25 files 1200 s; ceiling 1800 s. ONE pytest process at a time on this box. Paste every [pyt] summary line into the report. A TIMEOUT is a measurement failure: re-run that gate once alone, then report NOT MEASURED.',
  'You never run git write commands in an existing worktree. Probes, the prototype and every mutant live in YOUR OWN detached scratch worktree made with `git worktree add --detach <scratchpad>/<unit>_scratch <base sha>` and removed with `git worktree remove --force` at the end (sha-verify the real worktree before and after). You never read or print .env or any secret value (names only). Production flag state comes only from the newest dated ledger line. Pure ASCII and LF in every file you write; check bytes > 127 after each write; the pre-commit hook refuses sk-/JWT/PEM/credentialed-URL shapes, so build any such sentinel by concatenation at run time.',
].join('\n')

const RED_SCHEMA = {
  type: 'object',
  properties: {
    unit: { type: 'string' },
    test_files: { type: 'array', items: { type: 'object', properties: { path: { type: 'string' }, sha256: { type: 'string' }, bytes: { type: 'integer' } }, required: ['path', 'sha256'] } },
    base_run: { type: 'object', properties: { failed: { type: 'integer' }, passed: { type: 'integer' }, every_failure_is_assertion_error: { type: 'boolean' }, failed_node_ids: { type: 'array', items: { type: 'string' } }, pyt_line: { type: 'string' } }, required: ['failed', 'passed', 'every_failure_is_assertion_error', 'failed_node_ids', 'pyt_line'] },
    not_measured_alone: { type: 'array', items: { type: 'string' } },
    prototype: { type: 'object', properties: { on_passed: { type: 'integer' }, on_failed: { type: 'integer' }, off_passed: { type: 'integer' }, off_failed: { type: 'integer' }, pyt_lines: { type: 'array', items: { type: 'string' } }, notes: { type: 'string' } }, required: ['on_passed', 'on_failed', 'off_passed', 'off_failed', 'pyt_lines'] },
    mutants: { type: 'array', items: { type: 'object', properties: { id: { type: 'string' }, description: { type: 'string' }, killed_by: { type: 'string' }, survived: { type: 'boolean' }, equivalent_by_ruling: { type: 'boolean' } }, required: ['id', 'description', 'survived'] } },
    comm_set: { type: 'object', properties: { files: { type: 'integer' }, chunks: { type: 'integer' }, base_failures: { type: 'array', items: { type: 'string' } }, pyt_lines: { type: 'array', items: { type: 'string' } }, list_path: { type: 'string' } }, required: ['files', 'chunks', 'base_failures', 'pyt_lines'] },
    restore_check: { type: 'object', properties: { worktree_clean_except_new_tests: { type: 'boolean' }, scratch_removed: { type: 'boolean' }, note: { type: 'string' } }, required: ['worktree_clean_except_new_tests', 'scratch_removed'] },
    deviations_from_spec: { type: 'array', items: { type: 'string' } },
    open_questions: { type: 'array', items: { type: 'string' } },
    report_path: { type: 'string' },
  },
  required: ['unit', 'test_files', 'base_run', 'prototype', 'mutants', 'comm_set', 'restore_check', 'deviations_from_spec', 'open_questions'],
}

function redPrompt(u) {
  return [
    'You are the RED agent for unit ' + u.id + ': ' + u.title + '. Flag: ' + u.flag + '. Worktree (the real one, at the base sha; you may ADD new test files there and nothing else): ' + u.worktree + '.',
    RULES,
    'The spec: ' + u.specPath + ' ; its adversarial review: ' + u.reviewPath + ' ; the orchestrator rulings section for this unit in the batch rulings file: ' + u.rulingsSection + '. Where the three disagree, the rulings win, then the review corrections, then the spec.',
    'Procedure, in order. (1) Read the common brief, the spec, the review and the rulings in full; keep notes.md in your scratchpad from the first measurement. (2) Run ALONE at base, through the runner, each file the review listed as not measured: ' + (u.notMeasured || []).join(', ') + ' ; record the [pyt] lines. (3) Write ONLY the new test file(s) named in spec section 5 (as amended), pure ASCII, LF, hermetic (no network, no .env, no real credentials; patch targets per the spec and runs/research/eval_regression.json). Every RED row must fail at base with an AssertionError ONLY (missing symbols are asserted through getattr/find_spec helpers, never raised as ImportError/AttributeError); every PIN row must be green at base and must run WITH full configuration and call recorders so a gated mutant is killable (ruling B1 class). Set or delete every flag the row depends on explicitly (never rely on the ambient env). (4) Run the unit file at base through the runner: record failed/passed, the failed node ids, and confirm every failure is an AssertionError (read the log). (5) PROTOTYPE in your scratch worktree: implement the change list quickly (it is thrown away), run the unit file with the flag ON (all RED rows green, PIN rows green) and OFF (PIN rows green, flag-OFF byte identity), paste both [pyt] lines; note anything the spec got wrong. (6) MUTATION TABLE: for each mutant in spec section 6 (as amended) apply it to a byte copy of the prototype in the scratch worktree, run the unit file, record the killing row or SURVIVED (and whether a ruling calls it equivalent), restore the file and sha-verify. (7) COMM SET at base in the REAL worktree: build the file list with the union rule (module and symbol reference grep for every module the change list touches; UNION the source-scanning pins named in the common brief; UNION the CLAUDE.md readers; UNION the SmartCompareApp-scanning tests when the change is client-visible; EXCLUDE the four test_precommit_hook*.py files and the NETWORK_FLAKY_EXCLUDE set), write the list and a per-file reason TSV to your scratchpad, run it in chunks of at most 25 files (bound 1200) one at a time, record the failures (expected: only the pre-existing base failures the spec section 1.10 names). (8) RESTORE CHECK: sha256 of every tracked file in the real worktree equals the base except your new test files; remove the scratch worktree; no orphan pytest. (9) Write the full RED report to <scratchpad>/' + u.id + '_RED_REPORT.md (every [pyt] line, the mutation table, the comm list path) and return the structured output. Never edit an existing test or source file in the real worktree; a wrong spec row is reported as a deviation, not silently changed.',
  ].join('\n\n')
}

phase('RED')
const out = await parallel(A.units.map(u => () =>
  agent(redPrompt(u), { label: 'red:' + u.id, phase: 'RED', schema: RED_SCHEMA }).then(r => ({ unit: u.id, red: r }))
))
const done = out.filter(Boolean)
log('RED reports: ' + done.filter(d => d.red).length + '/' + A.units.length)
return done
