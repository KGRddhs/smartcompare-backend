export const meta = {
  name: 's71-step6-review',
  description: 'Session 71 Step 6 structured code review (Opus): security, performance, complexity and dead-code reviewers over every source file merged today (base 4bd5a09f to main 1974e217 plus the two open PRs), two adversarial refuters per high or medium finding, then one prioritised action plan with issue bodies for the orchestrator to file.',
  phases: [
    { title: 'Review', detail: 'four lenses over the merged diff', model: 'opus' },
    { title: 'Verify', detail: 'two refuters per high/medium finding', model: 'opus' },
    { title: 'Plan', detail: 'one prioritised action plan + issue bodies', model: 'opus' },
  ],
}
const SP = 'C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/3ffde5dd-0e09-4243-bf73-02955e287dff/scratchpad'
const RULES = SP + '/s70-common.txt'
const BE = 'C:/Users/SynAckITPC/Documents/AI/sc-s71-u13'
const FE = 'C:/Users/SynAckITPC/Documents/AI/sc-s70-u4b'
const HOOK = 'C:/Users/SynAckITPC/Documents/AI/sc-s71-t0b'
const NOTES = SP + '/step6'
const BASE = '4bd5a09f'
const HEAD = '1974e217'

const CONTEXT = [
  'STEP 6 STRUCTURED CODE REVIEW of the MYEZ launch lane, session 71 (repo smartcompare: FastAPI backend in app/, the DEPLOYED one, never backend/app/; React Native / Expo SDK 54 app in SmartCompareApp/; the POSIX pre-commit hook in .githooks/). Today is 2026-10-03. Everything merged since the session base ' + BASE + ' is on main ' + HEAD + ': #279 U4b (launcher icons from a committed master via scripts/render_myez_icons.py, SDK-54 bumps, a CI drift split), #285 OAI/observability (app/services/log_scrub.py safe_exc / exc_summary, model_router_service.daily_4o_cap, the prefetch CancelledError retrieval, url_extraction max_retries), #288 U4c (QarenLogo = one Image of the bundled mark; the splash aligned with the native launch screen; src/utils/splashMarkLayout.ts), #290 U8b (migration 043 full-erasure account deletion, the per-user Redis cache purge, type-only deletion logs), #297 U13 (ENABLE_COMPARE_AUTH_REQUIRED: the guards require_paid_route_user / require_paid_route_admin in text_routes attached through router dependencies on ten paid routes; the harness scripts send X-Admin-Key only under HARNESS_SEND_ADMIN_KEY; ACTIVE in production since 14:23), #307 U4d (the reveal badge mark, the auth-screen marks, QaranIcon deleted), #310 U8c (the deletion route raises its 500 from None). Two PRs are open and will merge: #312 T0b Phase A (the hardened hook: JWT / credentialed-URL branches, the awk .env value pass, staged-blob checks, nested .env, skill frontmatter; worktree ' + HOOK + ') and #313 U13c (the camera 401 refresh-and-retry in identifyFromImages and the camera sign-in state; worktree ' + FE + ', branch feature/s71-u13c-camera-401).',
  'WHERE TO READ: backend and scripts in ' + BE + ' (branch main-review = main ' + HEAD + '); client in ' + FE + ' (main + #313); the hook in ' + HOOK + '. The changed non-test source files are listed in ' + NOTES + '/changed_src.txt; the diff is `git -C ' + BE + ' diff ' + BASE + ' ' + HEAD + ' -- <path>`. READ-ONLY: never write, create or delete a file in any worktree; no git writes; no installs; backend pytest only through the bounded runner (' + RULES + ' has the exact command) and only read-only subsets; client jest only as a subset by path from ' + FE + '/SmartCompareApp under coreutils timeout; never a real database, Railway, Supabase, Sentry, OpenAI, EAS or the network; never print a credential (the worktrees hold no .env; never look for one).',
  'Read the agent rules file FIRST and obey it: ' + RULES + '.',
  'REVIEW RULES (the skill): cite specific locations (file plus function or line); flag anything uncertain rather than guessing; state assumptions and why each beats the alternative; be concise, no filler, no restating code; a review finding is never a licence to add scope (the PRD out-of-scope list is binding); every finding carries a severity (critical / high / medium / low), the problem in one sentence, a failure scenario with concrete input and state, and the concrete fix. Prefer findings that a test or a measurement can confirm; a finding that merely restates a documented, ruled limit of a unit (the specs in docs/investigations/2026-10-03-session-71-state/ record them) is labelled as such and ranked low.',
].join('\n')

const FINDINGS_SCHEMA = { type: 'object', required: ['findings', 'healthy', 'summary'], properties: {
  findings: { type: 'array', items: { type: 'object', required: ['id', 'severity', 'file', 'location', 'problem', 'failure_scenario', 'fix', 'measurement'], properties: {
    id: { type: 'string' }, severity: { type: 'string', enum: ['critical', 'high', 'medium', 'low'] }, file: { type: 'string' }, location: { type: 'string' },
    problem: { type: 'string' }, failure_scenario: { type: 'string' }, fix: { type: 'string' }, measurement: { type: 'string', description: 'the command or probe and its output excerpt, or "reasoned, not measured"' } } } },
  healthy: { type: 'array', items: { type: 'string' }, description: 'areas read and found fine, one line each' },
  summary: { type: 'string' } } }
const VERDICT_SCHEMA = { type: 'object', required: ['refuted', 'severity_after', 'measurement', 'reason'], properties: {
  refuted: { type: 'boolean' }, severity_after: { type: 'string', enum: ['critical', 'high', 'medium', 'low', 'none'] }, measurement: { type: 'string' }, reason: { type: 'string' } } }
const PLAN_SCHEMA = { type: 'object', required: ['plan', 'issues_markdown', 'summary'], properties: {
  plan: { type: 'array', items: { type: 'string' }, description: 'ordered by severity, highest first: "<severity> | <file:location> | <problem> | <fix>"' },
  issues_markdown: { type: 'string', description: 'issue bodies in the === TITLE: / === LABELS: bundle format, one block per accepted finding or group' },
  summary: { type: 'string' } } }

const LENSES = [
  { key: 'security', text: 'SECURITY lens. Vulnerabilities in the merged code, each rated. Look at: the U13 guards (ordering vs. the slowapi wrapper, header parsing, the admin credential path, timing, the stream route, the OpenAPI surface, what still runs before a refusal), the harness scripts (where X-Admin-Key travels: redirects, logs, argv, error messages), migration 043 (SECURITY DEFINER, search_path, the REVOKE/GRANT state, the probe, the rollback), the account-deletion backend path (ordering, the purge, what can leak to logs or Sentry: read app/services/log_scrub.py and the deletion route), the Sentry scrubbing of the OAI unit, the hook (any way a value reaches argv, a temp file or output; any bypass of the new branches; fail-open paths), the camera retry (token handling, a second refresh path, the deadline), the icon renderer (path handling). Severity by exploitability and impact; state the attacker and the precondition.' },
  { key: 'performance', text: 'PERFORMANCE lens. Inefficiencies, redundant work and operations that scale badly with data or load in the merged code: the guards on every paid request (what they add per call, DNS or Supabase calls, the per-call env reads), the deletion cascade (table scans, missing indexes for the new DELETEs on the four 014/028/029 tables and the detach UPDATEs on user_events / comparison_feedback by comparison_id: read the migrations that created those tables for indexes), the Redis purge on the event loop (five synchronous DELs with the offload flag unset), exc_summary on hot error paths, the model router cap read per call, the hook (process spawns per commit, the built-in .env parse cost, the awk pass, batching), the splash layout maths at render, the camera retry (a second full multipart upload after a 401: cost and whether the body is parsed server-side before the guard), the icon renderer. Measure where a subset test or a timing probe can (bounded runner); otherwise reason from the code and say so.' },
  { key: 'complexity', text: 'COMPLEXITY lens. Code that should be simplified, better abstracted or made more testable: duplicated helpers (the five copies of _harness_auth_headers across the scripts; the guard reason constants; the detach logic in 043), long functions touched by these units (text_routes guards vs. the existing admin verification; identifyFromImages after the retry; ResultsScreen state branching; delete_user_account ordering), fragile couplings (tests that pin exact line text of the hook; the awk program as a shell string; module-scope requires), naming and comment accuracy where a comment now contradicts the code. Each finding names the simpler shape and what test would keep it honest; rank by maintenance risk, not taste.' },
  { key: 'dead-code', text: 'DEAD CODE lens. Unused or unreachable code safe to remove after these merges: exports with no importer (the icons barrel after QaranIcon; QarenLogo props; splashMarkLayout constants), flags or env reads nobody consumes, helpers left behind by the OAI unit (old log helpers replaced by exc_summary), the U13 harness branches never taken, migration SQL comments or guard checks that cannot fire, hook lines made unreachable by the new order (the old four-branch ++ filter vs. the new awk filter), tests that duplicate each other across the frozen RED files (report, do not delete). Prove each with a grep or import census (command and output); never guess from names.' },
]

phase('Review')
const reviews = await parallel(LENSES.map(l => () => agent([
  'ROLE: REVIEWER (' + l.key + '). Read every changed source file in ' + NOTES + '/changed_src.txt that your lens applies to, with its diff against ' + BASE + ', plus the two open PR worktrees named above. Keep running notes under ' + NOTES + '/review-' + l.key + ' (create it). Measure what can be measured in read-only subsets; never modify a worktree.',
  CONTEXT,
  l.text,
  'Return findings (each with a short id like ' + l.key.toUpperCase().slice(0, 3) + '-1, severity, file, location, the problem in one sentence, a concrete failure scenario, the concrete fix, and the measurement or "reasoned, not measured"), the healthy list, and a summary. Budget: 90 minutes from your first tool call.',
].join('\n'), { label: 'step6:' + l.key, phase: 'Review', model: 'opus', schema: FINDINGS_SCHEMA })))

const all = reviews.filter(Boolean).flatMap(r => r.findings || [])
const toVerify = all.filter(f => f.severity === 'critical' || f.severity === 'high' || f.severity === 'medium')
const lows = all.filter(f => f.severity === 'low')
log('findings: ' + all.length + ' total, ' + toVerify.length + ' to verify, ' + lows.length + ' low (listed unverified)')

phase('Verify')
const verified = await pipeline(toVerify, f => parallel(['reproduce', 'impact'].map(lens => () => agent([
  'ROLE: REFUTER (' + lens + ' lens). Try to REFUTE this review finding; default to refuted=true when you cannot confirm it with a measurement or a precise code reading. Read-only, same rules as the reviewers. The reproduce lens asks: does the failure scenario really happen on the code as merged (read the exact lines, run a read-only subset or a scratch probe under your notes folder)? The impact lens asks: given the deployed configuration (flags default OFF except the three activated today; one Railway replica; the specs and their recorded limits in docs/investigations/2026-10-03-session-71-state/), is the severity right, or is this a documented, ruled limit?',
  CONTEXT,
  'FINDING: ' + JSON.stringify(f),
  'Notes under ' + NOTES + '/verify (create it; one file per finding id and lens). Return refuted (boolean), severity_after, the measurement, the reason. Budget: 30 minutes from your first tool call.',
].join('\n'), { label: 'verify:' + f.id + ':' + lens, phase: 'Verify', model: 'opus', schema: VERDICT_SCHEMA }))).then(votes => {
  const vs = votes.filter(Boolean)
  const survives = vs.length > 0 && vs.every(v => !v.refuted)
  const sev = survives ? (vs.map(v => v.severity_after).includes('critical') ? 'critical' : vs.map(v => v.severity_after).includes('high') ? 'high' : vs.map(v => v.severity_after).includes('medium') ? 'medium' : 'low') : 'none'
  return { finding: f, votes: vs, survives, severity_after: sev }
}))

const confirmed = verified.filter(Boolean).filter(v => v.survives)
const killed = verified.filter(Boolean).filter(v => !v.survives)
log('verified: ' + confirmed.length + ' confirmed, ' + killed.length + ' refuted')

phase('Plan')
const plan = await agent([
  'ROLE: SYNTHESIS. Produce the Step 6 prioritised action plan from the CONFIRMED findings (highest severity first), then the low findings (unverified, marked as such), then one line per refuted finding with the refuting reason (so the orchestrator can see what was ruled out). For each plan line: severity, file:location, the problem in one sentence, the concrete fix. Group findings that belong to one unit of work. Then write issue bodies in the bundle format "=== TITLE: <title>\\n=== LABELS: a,b\\n<markdown body>" for every confirmed finding or group (each body self-contained: context, failure scenario, measurement, fix, acceptance), and NO issue for refuted or documented-limit items. Be concise; no restating code.',
  CONTEXT,
  'CONFIRMED: ' + JSON.stringify(confirmed.map(c => ({ finding: c.finding, severity_after: c.severity_after, votes: c.votes }))),
  'LOW (unverified): ' + JSON.stringify(lows),
  'REFUTED: ' + JSON.stringify(killed.map(k => ({ id: k.finding.id, file: k.finding.file, problem: k.finding.problem, reasons: k.votes.map(v => v.reason) }))),
  'HEALTHY (from the reviewers): ' + JSON.stringify(reviews.filter(Boolean).flatMap(r => r.healthy || [])),
  'Write the plan also to ' + NOTES + '/STEP6_ACTION_PLAN.md (the full plan, the refuted list, the healthy list). Return plan, issues_markdown, summary. Budget: 45 minutes.',
].join('\n'), { label: 'step6:plan', phase: 'Plan', model: 'opus', schema: PLAN_SCHEMA })

return { counts: { total: all.length, verified: toVerify.length, confirmed: confirmed.length, refuted: killed.length, low: lows.length }, plan, confirmed, killed, lows }
