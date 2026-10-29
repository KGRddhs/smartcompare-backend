export const meta = {
  name: 's81-group-spec',
  description: 'One spec writer for a GROUP of SAFE units (owner ruling LC-9: one spec, one section per unit, measured at base, no adversarial spec reviewer: the orchestrator reviews it, LC-8); returns the structured output for the orchestrator rulings',
  phases: [
    { title: 'Spec', detail: 'one spec writer per group, measured at base, writes <worktree>/.qa-s80/<GROUP>_UNIT_SPEC.md' },
  ],
}

// args: { groups: [{id, title, worktree, units, flags, brief}], common, plan, r0, defectLedger, baseSha, pyt, scratch }
const A = args
const RULES = [
  'Common brief (read it FIRST and again before reporting; the OWNER RULING sections LC-1..LC-9 at its end govern this group chain): ' + A.common,
  'Plan of record PLAN_S81 (Standing constraints, the VERIFY-stage corrections, Fable rulings F1-F4 and the unit text under Milestones are binding; owner decisions 1-12 are rulings): ' + A.plan,
  'R0 rulings (measured answers that gate these units): ' + A.r0,
  'Defect ledger (the MYEZ ids these units close): ' + A.defectLedger,
  'Base sha for every measurement: ' + A.baseSha + '. Bounded runner: python "' + A.pyt + '" (read its --help first; every pytest goes through it, one process at a time, paste the [pyt] line with every summary; the box is loaded, so measure with greps and reads first and run only the pin files you must).',
  'You never run git write commands (no add/commit/checkout/switch/stash/reset/rebase/merge/clean) in any existing worktree; probes that need an editable copy use a scratch copy under your scratchpad (' + A.scratch + ') and are deleted afterwards. You never read or print .env or any secret value; variable NAMES only. Production flag state comes only from the newest dated ledger line (docs/investigations/2026-10-22-session-81-state/ledger.md on the docs checkout). No personal values in any file. Pure ASCII and LF in every file you write; check bytes > 127 after each write.',
].join('\n')

const SPEC_SCHEMA = {
  type: 'object',
  properties: {
    group: { type: 'string' },
    units_covered: { type: 'array', items: { type: 'string' } },
    spec_path: { type: 'string' },
    spec_sha256: { type: 'string' },
    summary: { type: 'string' },
    base_measurements: { type: 'array', items: { type: 'string' } },
    change_list: { type: 'array', items: { type: 'string' } },
    red_files: { type: 'array', items: { type: 'string' } },
    red_rows: { type: 'integer' },
    pin_rows: { type: 'integer' },
    mutants: { type: 'integer' },
    comm_set_size: { type: 'integer' },
    deliberate_pin_changes: { type: 'array', items: { type: 'string' } },
    stated_limits: { type: 'array', items: { type: 'string' } },
    focus_surfaces_found: { type: 'array', items: { type: 'string' } },
    open_questions: { type: 'array', items: { type: 'string' } },
    pyt_lines: { type: 'array', items: { type: 'string' } },
  },
  required: ['group', 'units_covered', 'spec_path', 'spec_sha256', 'summary', 'change_list', 'red_files', 'red_rows', 'pin_rows', 'mutants', 'comm_set_size', 'focus_surfaces_found', 'open_questions'],
}

function specPrompt(g) {
  return [
    'You are the SPEC WRITER for the SAFE-unit GROUP ' + g.id + ': ' + g.title + '. Units in this group: ' + g.units + '. Flags (one or more per unit, every one default OFF and read per call): ' + g.flags + '.',
    RULES,
    'Worktree to measure (read-only for you; detached at the base sha): ' + g.worktree + '.',
    'Group brief from the orchestrator (read it in full first): ' + g.brief,
    'Write ONE spec to ' + g.worktree + '\\.qa-s80\\' + g.id + '_UNIT_SPEC.md (the .qa-*/ directory is gitignored): section 0 = the group (the one branch, the units, every flag, the change list per unit, the files two units share and the order GREEN applies them); then, FOR EACH UNIT, the house sections 1-11 under a heading "## Unit <id>" with the house template measured in the harness digest and the worked examples (docs checkout: docs/investigations/2026-10-17-session-79-state/specs/B3B_APPLE_REVOKE_UNIT_SPEC.md, S78_F8_UNIT_SPEC.md): 1 base state MEASURED (file:line, the flag-reader idiom, libraries on the pinned venv, guards, line endings, 1.10 the base pass state of the files the unit touches through the bounded runner); 2 contract (flags and knobs, every new key and type, failure table, flag-OFF identity as the main invariant, seams); 3 change list; 4 existing pins (4.1 deliberate changes with reasons, 4.2 must stay green); 5 RED tests (its own file tests/test_s81_<unit>_*.py, hermetic, RED rows failing at base on an AssertionError only, PIN rows green at base with full configuration and call recorders); 6 mutation table; 7 comm set by the union rule (module and symbol reference grep UNION the source-scanning pins UNION the module-path / glob / path-segment readers UNION the SmartCompareApp-scanning backend tests UNION every importer of an edited module, app/main.py included; name the fourteen backend-scanning client jest fences that must run by path if any literal they read moves); 8 the CLAUDE.md row text and owner steps; 9 stated limits; 10 out of scope; 11 open questions. Then section 12 = the group: the combined comm set and CI-order set, the combined footprint, the shared-file plan, the PR plan (one PR, body at most 25 KB with one short section per unit), and the SAFE check: name every surface the group touches among auth / tokens / sessions, quota / billing / refunds, legal or privacy text, the consent path, security middleware, migrations, Redis / Lua scripts, the App-Review-visible client surface, secrets or key handling; a unit that touches one is FOCUS and must be named in focus_surfaces_found so the orchestrator can pull it out of the group.',
    'Contract freeze: re-read PLAN_S80 section 0 and its runs/research/contract_freeze.json (sc-docs-70/docs/investigations/2026-10-19-session-80-state/) before writing section 2; new keys are additive; never a bare 503.',
    'Measure, do not assume: every file:line you cite was read at the base sha in this run. Return the structured output; the spec file is the deliverable.',
  ].join('\n\n')
}

phase('Spec')
const out = await pipeline(
  A.groups,
  g => agent(specPrompt(g), { label: 'spec:' + g.id, phase: 'Spec', schema: SPEC_SCHEMA }).then(spec => ({ group: g.id, spec })),
)
const done = out.filter(Boolean)
log('groups with a spec: ' + done.filter(d => d.spec).length + '/' + A.groups.length)
return done
