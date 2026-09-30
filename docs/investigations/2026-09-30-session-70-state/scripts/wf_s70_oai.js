export const meta = {
  name: 's70-oai-obs',
  description: 'Session 70 backend unit: #265 url_extraction retry ceiling, #268 4o-cap downgrade visibility, and the two Sentry-found defects (empty-message error logs, never-retrieved gather future); spec, adversarial review, red, green, two adversaries, fix',
  phases: [
    { title: 'Spec', detail: 'measure and write the spec' },
    { title: 'Review', detail: 'adversarial spec review' },
    { title: 'Red', detail: 'failing tests only' },
    { title: 'Green', detail: 'implementation + bounded gates + comm gate' },
    { title: 'Adversary', detail: 'correctness lens + regression lens' },
    { title: 'Fix', detail: 'apply surviving findings' },
  ],
}
const SP = 'C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/e2415927-6e3a-4d40-81fc-edeec632886a/scratchpad'
const RULES = SP + '/s70-common.txt'
const WT = 'C:/Users/SynAckITPC/Documents/AI/sc-s70-oai'
const SPEC = WT + '/docs/investigations/2026-09-30-session-70-state/OAI_OBS_SPEC.md'
const NOTES = SP + '/oai'
const BASE = '94c097cd'

const CONTEXT = [
  'BACKEND UNIT of the MYEZ launch lane (repo smartcompare; FastAPI in app/ - the DEPLOYED backend; never edit backend/app/). Worktree ' + WT + ' (branch feature/s70-openai-companions, base ' + BASE + ' = main). No node_modules needed.',
  'Read the agent rules file FIRST and obey it: ' + RULES,
  'Context: production OpenAI credits are exhausted today; Ahmed tops up; Railway web now carries OPENAI_MAX_RETRIES=1 and OPENAI_FALLBACK_MAX_RETRIES=0 (set 2026-09-30). The decision memo is docs/investigations/2026-09-29-session-69-state/LLM_PROVIDER_DECISION.md. All four items ship UNFLAGGED (they are logging, a retry ceiling and additive metadata) unless the spec shows a behaviour fork for legitimate traffic, in which case STOP and report.',
  'ITEMS:',
  ' (1) GitHub issue #265: app/services/url_extraction_service.py get_client (lines ~29-37) builds AsyncOpenAI without max_retries, so OPENAI_MAX_RETRIES does not cover /api/v1/url/compare. Fix: pass max_retries=model_config.openai_max_retries() exactly like extraction_service.get_client (:60-80) and openai_service; pin with a construction-kwargs test (env unset -> 2, OPENAI_MAX_RETRIES=1 -> 1). Check the lazy-client caching semantics match the siblings.',
  ' (2) GitHub issue #268: app/services/model_router_service.py get_model(priority=high) silently returns gpt-4o-mini once 4o usage reaches SWITCH_THRESHOLD (0.80) of DAILY_4O_CAP (class constant 1_000_000). Fix: ONE INFO log line per downgrade decision ("[MODEL_ROUTER] 4o cap reached: routing verdict to <mini model>" with used/cap numbers, no secrets); DAILY_4O_CAP read PER CALL from the env var DAILY_4O_CAP (garbage, non-positive and non-finite values fall back to 1_000_000 - float() accepts inf/nan, reject them); an ADDITIVE response marker metadata.model_downgraded (true only when the verdict actually ran on the downgraded model; measure where the verdict model is chosen and where response metadata is built, sync AND streaming paths; if threading it is invasive, STOP and propose the smallest honest site). Also update docs/runbooks/2026-09-02-openai-tpm-launch-sizing.md with a DAILY_4O_CAP sizing note for ~200 verdicts/day (docs only; no env change - that is Ahmed). A Redis-down read counting as 0 (always 4o) stays as is and is documented.',
  ' (3) Sentry (read 2026-09-30, org qaren-rr, project python-fastapi): issues PYTHON-FASTAPI-N "Search error: " (11 events) and PYTHON-FASTAPI-14 "Serper shopping call error (gl=us): " (4 events) carry an EMPTY message because str(e) is empty for timeouts; sites app/services/serper_service.py:665 and :825, and the same pattern at app/services/extraction_service.py:1711 ("Specs extraction error: {e}"). Fix: log the exception TYPE plus the scrubbed text (reuse an existing scrubber such as structured_comparison_service._safe_exc or the W4-9 helpers if importable without a cycle; never log a key, a credentialed URL or a query string). Enumerate every other logger.error/exception f"...{e}" site in serper_service.py and extraction_service.py and apply the same rule only where the message could be empty; list them in the spec. Keep the Sentry grouping stable where possible (message prefix unchanged).',
  ' (4) Sentry issues PYTHON-FASTAPI-1K/1J/Y/1N/17 (about 16 events): asyncio logs "_GatheringFuture exception was never retrieved / future: <_GatheringFuture finished exception=CancelledError()>" with the in-app frames structured_comparison_service.py:278 _timeout_none <- occ_service.py:285 fetch_occ_rest_price. Find the asyncio.gather (around structured_comparison_service.py:6579-6660, the prefetch / fan-out that R-W18 and M13-30 touched) whose future is cancelled or abandoned without its exception being retrieved, and fix it so the exception is retrieved (e.g. a done-callback that calls .exception() on cancelled/finished gathers, or awaiting the cancelled gather under suppress(CancelledError)) WITHOUT changing any return value, timing bound or cancellation semantics. Reproduce the warning in a test first (asyncio loop exception handler / caplog of the asyncio logger capturing "exception was never retrieved"), then prove it is gone.',
  'Gates for the unit (all through the bounded runner): the new test files; every existing test file that references the changed modules (build the set by grepping tests/ for each changed module name - MODULE-REFERENCE, never filename keywords) run at BASE (a detached scratch worktree at ' + BASE + ' under your notes folder) and at HEAD in chunks of <= 25 files, then comm the sorted FAILED node ids - branch-only-NEW must be empty; ruff E9,F63,F7,F82 + py_compile on changed files; tests/test_security_regression.py must stay green.',
].join('\n')

const SPEC_SCHEMA = { type: 'object', required: ['spec_path', 'spec_sha256', 'open_questions', 'stop_conditions_hit', 'summary'], properties: {
  spec_path: { type: 'string' }, spec_sha256: { type: 'string' }, open_questions: { type: 'array', items: { type: 'string' } },
  stop_conditions_hit: { type: 'array', items: { type: 'string' } }, summary: { type: 'string' } } }
const REVIEW_SCHEMA = { type: 'object', required: ['verdict', 'corrections', 'spec_sha256_after', 'summary'], properties: {
  verdict: { type: 'string', enum: ['APPROVED', 'APPROVED_WITH_CORRECTIONS', 'REJECTED'] },
  corrections: { type: 'array', items: { type: 'string' } }, spec_sha256_after: { type: 'string' }, summary: { type: 'string' } } }
const WORK_SCHEMA = { type: 'object', required: ['files_changed', 'gates', 'comm_gate', 'deviations_from_spec', 'git_status_final', 'residual_risk', 'pr_text', 'summary'], properties: {
  files_changed: { type: 'array', items: { type: 'string' } }, gates: { type: 'array', items: { type: 'string' } },
  comm_gate: { type: 'string' }, deviations_from_spec: { type: 'array', items: { type: 'string' } },
  git_status_final: { type: 'string' }, residual_risk: { type: 'string' }, pr_text: { type: 'string' }, summary: { type: 'string' } } }
const ADV_SCHEMA = { type: 'object', required: ['verdict', 'defects', 'minors', 'files_sha256_at_start', 'worktree_left_byte_identical', 'summary'], properties: {
  verdict: { type: 'string', enum: ['SOUND', 'DEFECTIVE'] }, defects: { type: 'array', items: { type: 'string' } },
  minors: { type: 'array', items: { type: 'string' } }, files_sha256_at_start: { type: 'array', items: { type: 'string' } },
  worktree_left_byte_identical: { type: 'boolean' }, summary: { type: 'string' } } }

phase('Spec')
const spec = await agent([
  'ROLE: spec writer (read-and-measure only; write only the spec file and notes in ' + NOTES + ').',
  CONTEXT,
  'Write ' + SPEC + ' (create the folder): Base SHA; measured facts with file:line and excerpts for all four items (the exact call sites, the verdict-model choice site, the response-metadata build sites on the sync and streaming paths, the gather site that leaks the future and WHY it leaks, the log sites and what str(e) yields for asyncio.TimeoutError / httpx.ReadTimeout / openai.APITimeoutError on the pinned versions - MEASURE with the venv python, do not recall); requirements R1..Rn; the RED test list; gates; stated limits; stop conditions hit (if any item would change a return value or a user-visible response beyond the additive marker). Return path, sha256, open questions, stop conditions, summary.',
].join('\n'), { label: 'oai:spec', phase: 'Spec', schema: SPEC_SCHEMA })

phase('Review')
const review = await agent([
  'ROLE: ADVERSARIAL spec reviewer - refute, do not confirm. Read-and-measure only; append a section "## Review corrections (BINDING - supersede the body)" to the spec.',
  CONTEXT,
  'Spec ' + SPEC + ' (writer sha ' + (spec ? spec.spec_sha256 : '?') + '). Re-measure every claim. Hunt for: another AsyncOpenAI construction without max_retries (grep the whole app/), a second place that picks the verdict model (streaming vs sync), a caller that relies on DAILY_4O_CAP being a class attribute (tests monkeypatching it), a log-format change that would split existing Sentry groups or leak a secret, and whether the gather fix could swallow a real exception or change cancellation timing. Writer open questions: ' + JSON.stringify(spec ? spec.open_questions : []) + ' - answer each with a recommendation.',
  'Return verdict, corrections, spec sha after, summary.',
].join('\n'), { label: 'oai:spec-review', phase: 'Review', schema: REVIEW_SCHEMA })

phase('Red')
const red = await agent([
  'ROLE: RED agent (tests only; no app/ edits). Write the failing tests the spec lists (as corrected). Run them through the bounded runner and show each fails for the right reason; run the existing tests of the touched modules to show they pass at HEAD.',
  CONTEXT, 'Spec: ' + SPEC + '. Review verdict: ' + (review ? review.verdict : '?') + '. Notes: ' + NOTES + '/red.',
  'Return files changed with sha256, gates (verbatim [pyt] lines), comm_gate "n/a for red", deviations, git status, residual risk, pr_text "", summary.',
].join('\n'), { label: 'oai:red', phase: 'Red', schema: WORK_SCHEMA })

phase('Green')
const green = await agent([
  'ROLE: GREEN agent. Implement the spec (as corrected) until the red tests pass; then run every gate in CONTEXT including the base-vs-head module-reference comm gate. Mutation check: for each of the four items, revert your fix via a byte copy and confirm at least one new test reddens, then restore by sha256.',
  CONTEXT, 'Spec: ' + SPEC + '. Red report: ' + JSON.stringify(red ? { files: red.files_changed, gates: red.gates } : {}) + '. Notes: ' + NOTES + '/green.',
  'Return files changed with final sha256, gates, comm_gate (the sets, sizes and the comm -13 result), deviations, git status, residual risk, a full PR body (pr_text) ending with the line: Generated with Claude Code, and a summary.',
].join('\n'), { label: 'oai:green', phase: 'Green', schema: WORK_SCHEMA })

phase('Adversary')
const lenses = [
  { key: 'correctness', text: 'Correctness + security lens: does each item do exactly what the issue asks on BOTH the sync and streaming paths; can any new log line carry a key, a bearer token, a credentialed URL or user PII; is DAILY_4O_CAP parsing total (empty, garbage, 0, negative, inf, nan, 1e309); is metadata.model_downgraded true only when the verdict really ran on mini; does the gather fix retrieve the exception in every branch without changing a return value.' },
  { key: 'regression', text: 'Regression lens: re-run the green agent comm gate yourself (base detached worktree vs head, module-reference set, chunks of 25) and compare; mutate each fix away (byte copy, restore by sha) and confirm a test reddens; check Sentry grouping (message prefixes) and that tests/test_security_regression.py stays green.' },
]
const advs = await parallel(lenses.map(l => () => agent([
  'ROLE: ADVERSARY (' + l.key + '). Try to REFUTE that the unit is correct. Read-only except byte-copy mutations restored by sha256; leave the worktree byte-identical.',
  CONTEXT, 'Spec: ' + SPEC + '. Green report: ' + JSON.stringify(green ? { files: green.files_changed, gates: green.gates, comm: green.comm_gate, deviations: green.deviations_from_spec } : {}),
  l.text, 'Notes: ' + NOTES + '/adv-' + l.key + '. Return verdict, defects, minors, sha lists, byte-identical flag, summary.',
].join('\n'), { label: 'oai:adv-' + l.key, phase: 'Adversary', schema: ADV_SCHEMA })))

const findings = advs.filter(Boolean).flatMap(a => (a.defects || []).map(d => 'DEFECT: ' + d).concat((a.minors || []).map(m => 'MINOR: ' + m)))
let fix = null
if (findings.length) {
  phase('Fix')
  fix = await agent([
    'ROLE: FIX agent. Apply every DEFECT and every MINOR you verify is real (reject one only with a refuting measurement). Re-run the unit tests, the touched-module pin files and ruff/py_compile afterwards; re-run the comm gate only if you changed app/ code.',
    CONTEXT, 'Spec: ' + SPEC + '. Findings:\n' + findings.join('\n') + '\nNotes: ' + NOTES + '/fix.',
    'Return files changed with final sha256, gates, comm_gate, deviations (incl. rejected findings with the refuting measurement), git status, residual risk, the updated full pr_text, summary.',
  ].join('\n'), { label: 'oai:fix', phase: 'Fix', schema: WORK_SCHEMA })
}
return { spec, review, red, green, adversaries: advs, fix }
