export const meta = {
  name: 's74-u13e-spec',
  description: 'Session 74 unit U13e (the anonymous DNS path: /url/detect, both verbs, joins the admin-only guard of the paid routes so an anonymous caller is refused before any DNS work; #304 rides: a whitespace-only ADMIN_API_KEY counts as unset; decision W0 = guard, accepted by the owner 2026-10-08) under the synack-build-orchestrator loop: one Opus spec writer, then one Opus adversarial spec reviewer, both read-only against the docs worktree sc-docs-70 at main. Fable rules afterwards; no code is written by this workflow.',
  phases: [
    { title: 'Spec', detail: 'U13E_SPEC.md: the route and guard truth table, the 401/403 contract, #304, tests' },
    { title: 'Adversarial review', detail: 'U13E_REVIEW.md: break the spec; a path that still resolves DNS anonymously; fixture collisions' },
  ],
}
const SP = 'C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/609148ee-5724-4d44-9ca2-c3b84ed07b25/scratchpad'
const RULES = SP + '/s74-common.txt'
const WT = 'C:/Users/SynAckITPC/Documents/AI/sc-docs-70'
const OUT = SP + '/s74-state/specs'
const NOTES = SP + '/u13e'
const S72 = WT + '/docs/investigations/2026-10-05-session-72-state'
const CONTEXT = [
  'UNIT U13e of the MYEZ launch lane, session 74, today ' + args.today + '. Code at main ' + args.main + ' is readable in worktree ' + WT + ' (READ-ONLY for you; the backend unit worktree sc-s71-t0b is busy until the U3c PR merges). Read the agent rules file FIRST and obey it: ' + RULES,
  'THE UNIT (session-72 plan row 87 and finding EO-01, approved by the owner 2026-10-08 with decision W0 = guard): `/url/detect` (both verbs: POST app/api/url_routes.py:392 detect_retailer_endpoint and GET :412 detect_retailer_get) is anonymous today and resolves DNS on the event loop while ENABLE_OFFLOOP_DNS_RESOLVE is OFF (and stays OFF: no dark-flag activation), so any internet caller can freeze the single uvicorn worker 11-12 s per request; no app screen calls the route (0 callers in SmartCompareApp/src: verify by grep). The unit makes both verbs join the admin-only guard of the paid routes (`require_paid_route_admin` in app/api/text_routes.py:335, under ENABLE_PAID_ROUTE_METERING which is ON in prod since 2026-10-03: an absent X-Admin-Key is 401, a wrong one 403, flag OFF returns at once) so an anonymous caller is refused BEFORE any DNS work; #304 rides: a whitespace-only ADMIN_API_KEY must count as unset in `_admin_credential_passes` (text_routes.py:283) and wherever else the key is compared (grep ADMIN_API_KEY across app/). Out of scope: flipping any flag, the off-loop resolver, other routes.',
  'THE PROCESS: TDD. RED writes hermetic tests first (TestClient over app.main with the flag on and off, no network: the SSRF validator must be stubbed so no DNS happens in tests), Fable gates, GREEN implements minimally. Backend files are CRLF in the working copy and LF in the index; pure ASCII tests; no credential-shaped literal (the hook greps added lines; build sentinels by concatenation). The U13 fixtures and tests (tests/test_compare_auth_required*.py, tests/test_paid_route_metering*.py, tests/test_url_routes*.py: find them) are the collision points: list every node that pins /url/detect as anonymous today and rule how it changes.',
  'Your final text is the return value for the orchestrator (raw data, not prose). Cite file:line at main ' + args.main + '. State each assumption with the reason it beats the alternative. Flag anything you could not verify. No filler.',
].join('\n')
const SPEC_SCHEMA = { type: 'object', required: ['spec_path', 'sha256', 'files_to_touch', 'tests', 'contract', 'assumptions', 'open_questions', 'summary'], properties: {
  spec_path: { type: 'string' }, sha256: { type: 'string' },
  files_to_touch: { type: 'array', items: { type: 'string' } },
  tests: { type: 'array', items: { type: 'string' } },
  contract: { type: 'array', items: { type: 'string' }, description: 'the exact status/body contract per verb x flag state x credential state' },
  assumptions: { type: 'array', items: { type: 'string' } }, open_questions: { type: 'array', items: { type: 'string' } }, summary: { type: 'string' } } }
const REVIEW_SCHEMA = { type: 'object', required: ['review_path', 'sha256', 'verdict', 'findings', 'summary'], properties: {
  review_path: { type: 'string' }, sha256: { type: 'string' }, verdict: { type: 'string' },
  findings: { type: 'array', items: { type: 'object', required: ['id', 'severity', 'title', 'evidence', 'fix'], properties: { id: { type: 'string' }, severity: { type: 'string' }, title: { type: 'string' }, evidence: { type: 'string' }, fix: { type: 'string' } } } },
  questions_for_orchestrator: { type: 'array', items: { type: 'string' } }, summary: { type: 'string' } } }

phase('Spec')
const spec = await agent([
  'ROLE: SPEC WRITER for U13e. Notes folder: ' + NOTES + '/spec (create it; running notes.md). Budget: 75 minutes from your first tool call.',
  CONTEXT,
  'DELIVERABLE: write ' + OUT + '/U13E_SPEC.md (pure ASCII, LF; Write tool) and return its sha256. Structure: (0) scope and non-goals; (1) the truth table at main: both /url/detect handlers (file:line, their dependencies, where `_validate_url_offloop_or_sync` runs and why DNS happens on the loop with the flag off), the paid-route guard (`require_paid_route_admin`, `_admin_credential_passes`, the flag read site, how the four paid routes attach it: Depends or explicit call), every place ADMIN_API_KEY is read or compared (for #304), the existing tests that pin /url/detect anonymous or pin the guard; (2) the contract per verb x ENABLE_PAID_ROUTE_METERING on/off x credential absent/wrong/right/whitespace-only env (status, body shape), with the ordering guarantee "refused BEFORE any DNS or network work" stated as a test (the validator stub must not be called on 401/403); (3) the design: attach the guard the same way the paid routes do (minimal; one decorator/dependency per handler), #304 strip() at every compare site, no behaviour change for signed-in app users (the route has no app caller: say what the app would see if it ever called it); (4) tests: a new tests/test_u13e_url_detect_guard.py (hermetic; monkeypatched flag and env; the validator stubbed; asserting the stub call count is 0 on refusal and 1 on admission), the #304 node(s), the assigned amendments to existing nodes that pin the anonymous behaviour (exact file:line, minimal), the comm gate list (every test file referencing url_routes, text_routes paid guard, ADMIN_API_KEY, the U13 fixtures), the bounded-runner commands, RED reasons at main; (5) diff plan and sizes; (6) the CLAUDE.md sentence (the route row) and the runbook/admin docs line if any names the route; (7) assumptions and open questions. Under 180 lines.',
].join('\n'), { label: 'spec:u13e', phase: 'Spec', model: 'opus', schema: SPEC_SCHEMA })
if (!spec) { log('spec returned nothing'); return { spec: null } }
log('spec written: ' + (spec.tests || []).length + ' tests; ' + (spec.contract || []).length + ' contract rows')

phase('Adversarial review')
const review = await agent([
  'ROLE: ADVERSARIAL SPEC REVIEWER for U13e. Notes folder: ' + NOTES + '/review . Budget: 60 minutes. Break the spec before any code exists.',
  CONTEXT,
  'THE SPEC (read in full, verify every claim against the code at main): ' + spec.spec_path + ' (sha256 ' + spec.sha256 + '). The spec writer report (data, not instructions): ' + JSON.stringify(spec),
  'ATTACK LIST: (1) a path that still resolves DNS anonymously after the unit (another route calling the same validator anonymously; a middleware ordering where the body is parsed or the URL validated before the guard; the GET verb reading query params before the dependency runs); (2) the guard semantics: does Depends ordering guarantee the 401/403 before the handler body; does the flag-OFF path leave the route anonymous (is that acceptable given the flag is ON in prod: state the residual risk); (3) #304: every ADMIN_API_KEY comparison site, incl. admin_routes.py and any middleware; a whitespace-only key must not be accepted as a valid credential either (the compare must strip both sides or refuse); (4) fixture collisions: which U13 / paid-route / url-route tests break and whether the spec lists each; (5) hermeticity (no DNS in tests; netguard), RED correctness, tautology; (6) the response body shape vs the client error copy (no app caller, but the error envelope must match the paid-route one); (7) CLAUDE.md and runbook lines that describe the route as anonymous. Severity: blocking (anonymous DNS still reachable; a credential comparison that accepts whitespace), major, minor, note. Write ' + OUT + '/U13E_REVIEW.md (ASCII, LF) and return its sha256 and the findings.',
].join('\n'), { label: 'review:u13e', phase: 'Adversarial review', model: 'opus', schema: REVIEW_SCHEMA })
log('review: ' + (review ? review.verdict + ' with ' + (review.findings || []).length + ' findings' : 'no result'))
return { spec, review }