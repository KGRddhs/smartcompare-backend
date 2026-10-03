export const meta = {
  name: 's71-u13-pins',
  description: 'Session 71 U13 supplementary pins (ruling UF2) under the synack-build-orchestrator loop: one Opus agent writes tests/test_s71_u13_pins.py and proves each pin kills its mutant, one Opus adversary tries to show a pin is vacuous or order-dependent, fix round. No app code changes. The orchestrator gates the file before any commit.',
  phases: [
    { title: 'Pins', detail: 'write the supplementary pin file, bounded gates, mutant kills', model: 'opus' },
    { title: 'Adversary', detail: 'vacuity, isolation, ordering, independent mutant kills', model: 'opus' },
    { title: 'Fix', detail: 'apply surviving findings', model: 'opus' },
  ],
}
const SP = 'C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/3ffde5dd-0e09-4243-bf73-02955e287dff/scratchpad'
const RULES = SP + '/s70-common.txt'
const WT = 'C:/Users/SynAckITPC/Documents/AI/sc-s71-u13'
const SPEC = WT + '/docs/investigations/2026-10-03-session-71-state/U13_COMPARE_AUTH_SPEC.md'
const NOTES = SP + '/u13'
const NEWFILE = 'tests/test_s71_u13_pins.py'

const FROZEN = [
  'app/api/text_routes.py 22799ae4e484eaae',
  'app/api/url_routes.py 1b230fa61e3da229',
  'app/api/image_routes.py 06a08b8d63fbbfff',
  'scripts/eval_runner.py 7f29c6f6da1e6cf2',
  'scripts/run_validation_matrix.py a2d6b25c85031780',
  'scripts/bias_matrix_probe.py 22c6808c8b060fa7',
  'scripts/bundle_d_prod_smoke.py 499e71d71d81049c',
  'docs/investigations/2026-09-29-session-69-state/verify_after_credits.py c33e6e4c1c4e0201',
  'tests/test_s71_u13_compare_auth_required.py eac1369c3492206b',
  'tests/test_s71_u13_harness_auth.py eb33a12da8fb5017',
  'tests/fixtures/s71_u13_flag_off_baseline.json fa72e28fc4b0cd00',
].join('; ')

const CONTEXT = [
  'BACKEND UNIT U13 of the MYEZ Apple launch lane (repo smartcompare; FastAPI in app/ - the DEPLOYED backend; never edit backend/app/). Worktree ' + WT + ' (branch feature/s71-u13-compare-auth-required, HEAD = main ca604e0a, the unit is UNCOMMITTED on disk). Today is 2026-10-03 (session 71).',
  'Read the agent rules file FIRST and obey it: ' + RULES,
  'THE SPEC IS AUTHORITATIVE: ' + SPEC + '. Read it in full once. Its LAST section, "## Orchestrator rulings after the adversaries (BINDING ...)" (UF1-UF6), defines this task: ruling UF2 orders ONE new test file, ' + NEWFILE + ', with the pins P1-P4.',
  'STATE: GREEN is implemented, two adversaries returned SOUND, the fix agent applied UF1. These files are FROZEN at these sha256 prefixes and you change NONE of them (mutations are byte copies restored by sha256): ' + FROZEN + '. The spec file itself is not edited either. The ONLY file this task creates in the worktree is ' + NEWFILE + ' (LF line endings, pure ASCII, no sk- shaped string).',
  'How the existing tests work (reuse the conventions, do not import private helpers across test modules unless they are importable without side effects - copy the small pattern you need instead): tests/test_s71_u13_compare_auth_required.py installs stubs at the ROUTE module import names (_install_stubs), sets or deletes EVERY flag a node depends on (_flags, including ADMIN_API_KEY which other modules set at collection), mocks auth_routes.verify_token as an AsyncMock keyed on bearer sentinels, sends a fixed X-Request-ID, imports no app.* at module top, and looks routes up through tests/_route_introspection. tests/test_s71_u13_harness_auth.py loads the harness scripts by path and captures the request keywords (see H06 for run_validation_matrix). Earlier notes with measurements: ' + NOTES + '/green/notes.md, ' + NOTES + '/adv-security, ' + NOTES + '/adv-regression, ' + NOTES + '/fix (verify_findings_probe.py and redirect_probe.py show working probe code for every pin).',
  'The 25-file pin set (CI order) is listed in ' + NOTES + '/green/g3_files.txt; the mutation helper pattern is in ' + NOTES + '/green/mutate.py.',
].join('\n')

const WORK_SCHEMA = { type: 'object', required: ['files_changed', 'gates', 'mutants', 'deviations', 'git_status_final', 'residual_risk', 'summary'], properties: {
  files_changed: { type: 'array', items: { type: 'string' }, description: '"<path> <sha256>" final bytes, plus the frozen files re-hashed' },
  gates: { type: 'array', items: { type: 'string' }, description: 'verbatim [pyt] lines and summary lines' },
  mutants: { type: 'array', items: { type: 'string' }, description: 'one line per mutant: name, what changed, file, the killing node ids, the [pyt] line, restore sha EQUAL' },
  deviations: { type: 'array', items: { type: 'string' } },
  git_status_final: { type: 'string' }, residual_risk: { type: 'string' }, summary: { type: 'string' } } }
const ADV_SCHEMA = { type: 'object', required: ['verdict', 'defects', 'minors', 'worktree_left_byte_identical', 'summary'], properties: {
  verdict: { type: 'string', enum: ['SOUND', 'DEFECTIVE'] }, defects: { type: 'array', items: { type: 'string' } },
  minors: { type: 'array', items: { type: 'string' } },
  worktree_left_byte_identical: { type: 'boolean' }, summary: { type: 'string' } } }

phase('Pins')
const pins = await agent([
  'ROLE: PINS agent (test author). Write ' + NEWFILE + ' implementing P1-P4 of ruling UF2 exactly, with the pin id (P1..P4) in every node name. The code under test is already correct, so every node must PASS at HEAD; the proof that a pin is not vacuous is its mutant: for each of the mutants MF (text_routes.verify_admin_key replaced by a case-insensitive prefix match), MA (replaced by a plain == compare), XA (the flag check of require_paid_route_user moved below the _admin_credential_passes call), XB (the same in require_paid_route_admin), MR (the ADMIN_REQUIRED reason logged as NO_CREDENTIAL), ML (the "?" fallback of _paid_route_label changed to the concrete request path) and MD (allow_redirects removed from run_validation_matrix.run_query) take a byte copy, mutate the file on disk, run the new file through the bounded runner, it MUST FAIL with at least one node of the pin that targets it, restore from the byte copy, sha256 EQUAL to the frozen prefix. If a mutant survives, strengthen the pin, never the code.',
  CONTEXT,
  'Design constraints: hermetic (no network: the run must print no [netguard] line naming a node of the new file); every node sets or deletes every flag it reads (ENABLE_COMPARE_AUTH_REQUIRED, ENABLE_PAID_ROUTE_METERING, ENABLE_ANON_USAGE_GATE, ENABLE_STRICT_OPTIONAL_AUTH, ENABLE_CAMERA_FAILURE_ENVELOPE, ADMIN_API_KEY, HARNESS_SEND_ADMIN_KEY) through monkeypatch so the file passes alone, after the two RED files, and inside the 25-file CI-order set; no module-level app.* import; no dependence on test order; sentinels are plain words; the spy in P2 must not change behaviour when the flag is ON in other nodes (monkeypatch scope = the node). For P1 the case-flipped variant must really differ from the sentinel (choose a sentinel with letters). For P3 capture log records with caplog at INFO on the text_routes logger and assert on the formatted message; assert no record contains the header value. Keep the file small and readable (target under 350 lines).',
  'Gates, bounded runner, ONE pytest at a time, cheapest first: (a) py_compile + ruff on the new file; (b) the new file alone: all passed, no [netguard] node of this file; (c) the two RED files + the new file in one process: 159 + your node count passed; (d) the 25-file pin set + the new file in CI order (the new file sorts directly after tests/test_s71_u13_harness_auth.py): 879 + your node count passed; (e) the seven mutants; (f) hygiene: the new file is LF and pure ASCII (Python check over the bytes), no sk- shaped string, git status shows exactly one new untracked path more than before, every frozen file re-hashed EQUAL.',
  'Notes: ' + NOTES + '/pins (create it; running notes from the first measurement). Return files_changed (the new file with its full sha256 and the eleven frozen prefixes re-checked), gates, mutants, deviations, git status, residual risk, summary. Budget: 75 minutes from your first tool call.',
].join('\n'), { label: 'u13:pins', phase: 'Pins', model: 'opus', schema: WORK_SCHEMA })

phase('Adversary')
const adv = await agent([
  'ROLE: ADVERSARY for a test-only change. Try to REFUTE that ' + NEWFILE + ' pins what ruling UF2 says it pins. Read-only except byte-copy mutations restored by sha256; leave the worktree byte-identical (hash the new file and the eleven frozen files at start and at end).',
  CONTEXT,
  'Pins report: ' + JSON.stringify(pins ? { files: pins.files_changed, gates: pins.gates, mutants: pins.mutants, deviations: pins.deviations, residual_risk: pins.residual_risk } : {}),
  'Checks: (1) read the new file line by line against P1-P4: a pin that asserts less than the ruling says is a defect; an assertion that can never fail (a tautology, a spy that is never installed where the code looks it up, a caplog that listens on the wrong logger, a status compared with itself) is a defect. (2) run the file alone, twice, then after the two RED files, then inside the 25-file CI-order set, then with -p no:randomly removed is NOT available (the runner forces it) so instead run it with the node order reversed (pass the node ids in reverse on the command line): all passed each time, no [netguard] node of this file. (3) run it with ADMIN_API_KEY, ENABLE_COMPARE_AUTH_REQUIRED=true and HARNESS_SEND_ADMIN_KEY=1 exported in the runner environment, and again with all three unset: identical results (the nodes must own their flags). (4) re-run the seven mutants yourself (byte copy, mutate, run the new file only, restore, sha256 equal) and add three of your own that the ruling implies: the 403 of a wrong admin key turned into a 401; _admin_credential_passes returning True for an empty header when ADMIN_API_KEY is empty; the guard calling verify_admin_key twice. Report every survivor with the node that should have caught it. (5) confirm no file other than the new test file differs from the frozen prefixes and that the new file is LF, ASCII and has no sk- shaped string.',
  'Notes: ' + NOTES + '/pins-adv (create it). Verdict SOUND only if you found no serious defect. Return verdict, defects (each with the line, the measurement and a failure scenario), minors, the byte-identical flag, summary. Budget: 60 minutes from your first tool call.',
].join('\n'), { label: 'u13:pins-adv', phase: 'Adversary', model: 'opus', schema: ADV_SCHEMA })

const findings = adv ? (adv.defects || []).map(d => 'DEFECT: ' + d).concat((adv.minors || []).map(m => 'MINOR: ' + m)) : []
let fix = null
if (findings.length) {
  phase('Fix')
  fix = await agent([
    'ROLE: FIX agent for a test-only change. Apply every DEFECT and every MINOR you verify is real, by editing ONLY ' + NEWFILE + ' (reject a finding only with a refuting measurement; a finding that would need an app, script, spec or frozen-test change is NOT applied: report it for the orchestrator). First re-hash the eleven frozen files: if one differs, restore it from the byte copy in the adversary notes folder (never git checkout --) and report it. Afterwards re-run gates (a)-(f) of the pins brief, including all seven mutants plus any mutant an applied finding names.',
    CONTEXT,
    'Pins report files: ' + JSON.stringify(pins ? pins.files_changed : []),
    'Findings:\n' + findings.join('\n') + '\nNotes: ' + NOTES + '/pins-fix (create it).',
    'Return files_changed with final sha256, gates, mutants, deviations (incl. rejected findings with the refuting measurement and findings left for the orchestrator), git status, residual risk, summary. Budget: 60 minutes from your first tool call.',
  ].join('\n'), { label: 'u13:pins-fix', phase: 'Fix', model: 'opus', schema: WORK_SCHEMA })
}
return { pins, adversary: adv, fix }
