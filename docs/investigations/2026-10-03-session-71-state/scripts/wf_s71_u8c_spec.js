export const meta = {
  name: 's71-u8c-spec',
  description: 'Session 71 U8c spec (read-and-measure, Opus): issue #292, the deletion route raises HTTPException inside its except arm so the Sentry Starlette integration carries the chained exception text (email, URL); measure every such site in app/api, specify the raise-from-None fix and its Sentry in-memory-transport pin, then an adversarial spec review',
  phases: [
    { title: 'Spec', detail: 'measure the chained-exception leak on the deletion route and survey the other except-raise sites; write the spec', model: 'opus' },
    { title: 'Review', detail: 'adversarial spec review, binding corrections', model: 'opus' },
  ],
}
const SP = 'C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/3ffde5dd-0e09-4243-bf73-02955e287dff/scratchpad'
const RULES = SP + '/s70-common.txt'
const WT = 'C:/Users/SynAckITPC/Documents/AI/sc-s71-u8b'
const NOTES = SP + '/u8c'
const SPEC = NOTES + '/U8C_SENTRY_CHAIN_SPEC.md'
const BASE = 'b90b5f07'
const U8B_NOTES = SP + '/u8b/adv-backend'

const CONTEXT = [
  'BACKEND UNIT U8c of the MYEZ Apple launch lane (repo smartcompare; FastAPI in app/ - the DEPLOYED backend; never edit backend/app/). Worktree ' + WT + ' (branch feature/s71-u8c-sentry-chain, HEAD = main ' + BASE + ', clean). Today is 2026-10-03 (session 71). GitHub issue #292: DELETE /auth/account (app/api/auth_routes.py, the delete_account handler) raises HTTPException(500) INSIDE its except arm, so the Sentry Starlette/FastAPI integration captures the 5xx with the original exception chained as __context__; the U8b backend adversary measured with init_sentry() and an in-memory transport that for httpx.ConnectError, AuthApiError and RuntimeError the chained text (URL, email) reaches the Sentry event, while a PostgREST APIError sends only .message. U8b (PR #290, merged) made the LOG lines type-only but froze that raise line (R7).',
  'WHERE YOU MEASURE: the worktree above, READ-AND-MEASURE only: never write, create or delete a file inside it (no git writes, no pip, no pytest outside the bounded runner). Write ONLY under ' + NOTES + ' (create it): the spec ' + SPEC + ', a running notes.md from the first measurement on, scratch probes. The U8b adversary left a working Sentry in-memory-transport probe and notes in ' + U8B_NOTES + ' (notes.md, probe_head.json; read them, re-measure what you rely on).',
  'Read the agent rules file FIRST and obey it: ' + RULES + '. Every pytest run goes through the bounded runner; never touch the network, Railway, Supabase, Sentry or any credential (Sentry is exercised ONLY through init_sentry with an in-memory transport and a dummy DSN, never a real DSN).',
  'SCOPE RULES (binding): the unit is SMALL. Required: the deletion route raises from None (or the equivalent that drops the chain) so the Sentry event carries no chained exception text, with a pin that drives the real route under TestClient with init_sentry and an in-memory transport for the three exception shapes (httpx.ConnectError with a URL, AuthApiError, RuntimeError with an email) and asserts the event JSON contains neither the email nor the URL and that the status / envelope / log line of U8b stay identical (the U8b tests tests/test_account_deletion_u8b.py and tests/test_account_deletion_u8b_fix_pins.py stay green and unedited). Survey: list EVERY `raise HTTPException(...)` inside an `except` arm in app/api/*.py whose chained exception can plausibly carry personal data or a credential (an email, a token, a URL with a query, a user id is fine), with the measured or inferred text shape; recommend which (if any) belong in THIS unit and which are follow-ups; the orchestrator rules. Out of scope: logging changes (U8b did them), the Sentry before_send scrubber (#286 covers patterns), anything under SmartCompareApp/.',
].join('\n')

const SPEC_SCHEMA = { type: 'object', required: ['spec_path', 'spec_sha256', 'base_sha', 'open_questions', 'summary'], properties: {
  spec_path: { type: 'string' }, spec_sha256: { type: 'string' }, base_sha: { type: 'string' },
  open_questions: { type: 'array', items: { type: 'string' } }, summary: { type: 'string' } } }
const REVIEW_SCHEMA = { type: 'object', required: ['verdict', 'corrections', 'spec_sha256_after', 'summary'], properties: {
  verdict: { type: 'string', enum: ['APPROVED', 'APPROVED_WITH_CORRECTIONS', 'REJECTED'] },
  corrections: { type: 'array', items: { type: 'string' } }, spec_sha256_after: { type: 'string' }, summary: { type: 'string' } } }

phase('Spec')
const spec = await agent([
  'ROLE: spec writer (read-and-measure only). You are an Opus implementation-planning agent; the Fable orchestrator will rule on your open questions and gate the spec before any test is written.',
  CONTEXT,
  'TASK: measure and write the spec to ' + SPEC + '. Every factual claim carries the command you ran and an output excerpt; line numbers are anchors, also name the symbol. REQUIRED SECTIONS: 1. Base (git rev-parse HEAD, status clean). 2. Measured facts: (a) the deletion route handler in full (the try/except, the log line U8b wrote, the raise); (b) how the Sentry integration is wired (app/services/sentry_service.py or wherever init_sentry lives: integrations, before_send, send_default_pii, the logging integration levels) and what a 5xx inside an except arm produces: re-run the in-memory-transport probe from the U8b adversary for the three shapes at HEAD and paste the relevant event fields (exception.values[].type / value, breadcrumbs, logentry) with the sentinel shown as a shape only; (c) what `raise ... from None` changes (measure: the event after the change on a scratch COPY of the route driven through a scratch app, or by monkeypatching the handler in a scratch test) and whether FastAPI / Starlette still logs the original exception elsewhere (the ServerErrorMiddleware, uvicorn access log); (d) the survey of every `raise HTTPException` inside an except arm across app/api/*.py (a Python AST walk), with for each: file:line, the handler, the exception types caught, what text they can carry, your verdict (in-unit / follow-up / fine) with the reason; (e) the existing tests that pin the deletion route (U8b files, tests/test_account_deletion.py, test_delete_user_cascade.py, the Sentry tests tests/test_sentry_*.py) and which of them would notice the change. 3. Requirements R1..Rn (numbered, testable). 4. Files to touch and files that MUST NOT change. 5. Test list: RED tests (file, name, what each asserts, why red at base for the right reason), PIN tests, and at least four named mutants (the from None removed; the chain replaced by a new exception that embeds str(e); the log line restored to f-string; the Sentry capture suppressed instead of de-chained). 6. GREEN gates with exact commands (the new file; the U8b files; tests/test_sentry_*.py; tests/test_security_regression.py; the module-reference comm gate is NOT required for a one-line route change unless you measure that more than one module changes; ruff + py_compile; hygiene). 7. Risks and stated limits. 8. Open questions with RECOMMENDATIONS.',
  'Keep the spec precise and concise. Return the spec path, its sha256, the base sha, your open questions and a short summary. Budget: 60 minutes from your first tool call.',
].join('\n'), { label: 'u8c:spec', phase: 'Spec', schema: SPEC_SCHEMA, model: 'opus' })

phase('Review')
const review = await agent([
  'ROLE: ADVERSARIAL spec reviewer (Opus). Your job is to REFUTE claims in the spec, not to confirm them. Read-and-measure only: the same rules as the writer; your ONLY write outside your scratch notes is APPENDING one section to the spec file. Keep your notes under ' + NOTES + '/review (create it).',
  CONTEXT,
  'The spec is ' + SPEC + ' (sha256 reported by its writer: ' + (spec ? spec.spec_sha256 : 'unknown - the writer returned nothing; if the file is missing or incomplete, say REJECTED and list what is missing') + ').',
  'Re-measure EVERY factual claim with your own commands: the Sentry wiring and the event shapes at HEAD (your own in-memory-transport probe); whether `from None` really drops the chain for the Starlette integration (the integration may read __cause__ AND __context__; measure both; also measure what the ASGI ServerErrorMiddleware / exception handler path captures when the HTTPException is 500 vs when a plain exception escapes); whether the chained text could still arrive through a breadcrumb or the logging integration (U8b made the log line type-only, but the uvicorn error log or another logger may still format str(e)); the survey completeness (your own AST walk; did the writer miss `raise HTTPException` in a nested function, a helper, a dependency, or `raise HTTPException(...) from e`); the RED tests (would each really fail at base for the stated reason; would a PIN fail at base; mutants the list would not kill, e.g. a handler that logs str(e) at DEBUG, or a from None that is paired with a new exception message embedding the email).',
  'Writer open questions: ' + JSON.stringify(spec ? spec.open_questions : []),
  'Append a section titled exactly "## Review corrections (BINDING - supersede the body)" to the spec with numbered corrections, each with its measurement (command and output excerpt). Answer each writer open question with a RECOMMENDATION. Return the verdict, the corrections as short strings, the spec sha256 after your edit, and a summary. Budget: 60 minutes from your first tool call.',
].join('\n'), { label: 'u8c:spec-review', phase: 'Review', schema: REVIEW_SCHEMA, model: 'opus' })

return { spec, review }
