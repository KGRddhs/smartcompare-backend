export const meta = {
  name: 's68-red-auth198',
  description: 'Session 68 unit 3 RED phase on Opus 5.5: issue #198 - auth_service logs expected client 401s at ERROR with str(e); measure the pinned SDK error shapes and the Sentry logging default, write tests/test_auth_error_log_hygiene.py, prove right-reason reds, record the CI-order pin set at HEAD',
  phases: [
    { title: 'Red', detail: 'measure at 61585c58, write the caplog reds and pins, base run of the CI-order set', model: 'claude-opus-5-5' },
  ],
}
const MODEL = 'claude-opus-5-5'
const DIR = 'C:/Users/SynAckITPC/Documents/AI/sc-auth-198'
const SPEC = DIR + '/.qa-s68/AUTH_198_SPEC.md'
const MYSP = 'C:/Users/SynAckITPC/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/b1819d0c-d9c5-466a-ba0d-b82774c624db/scratchpad'
const COMMON_PATH = MYSP + '/s68-common.txt'

const ISSUE = `ISSUE #198 (open): Expected auth 401s are logged at ERROR and shipped to Sentry as error events. Evidence (2026-09-24 14:07:22 UTC, release 6da0c6f8, Sentry project python-fastapi): issue 'Auth error in refresh: Refresh token is not valid', logger app.services.auth_service, transaction app.api.auth_routes.refresh, browser curl 8.17.0. That event was an orchestrator probe (POST /api/v1/auth/refresh with a deliberately invalid refresh token). The route answered 401 correctly; no user was involved. Sentry still raised a new error-level issue and notified the project members. Root cause: app/services/auth_service.py:243 - the generic branch of the shared auth error handler does logger.error(f'Auth error in {context}: {e}') for EVERY context. For refresh (and login), an invalid or expired token / wrong credentials is an expected, client-caused 401, not an application error, so ERROR is the wrong level and every such request becomes a Sentry event. Second angle on the same line (the R-W0/R-AUTH rule): the line interpolates the RAW exception text ({e}). The retro wave ruled that an auth-path SDK exception can carry a credential as its argument, and the [auth] WARNING lines added by W1-4/R-AUTH log the exception TYPE only for that reason. This ERROR line predates the rule and ships str(e) to Sentry. Proposed unit (test-first): (1) per-context level: for the expected-client classes log at WARNING with the exception TYPE and a stable reason code, no str(e); keep ERROR for unexpected classes only (type + redacted message); (2) pin with caplog: a refresh with an invalid token produces no ERROR record and no str(e); an unexpected exception still produces ERROR; (3) Sentry: confirm the logging integration's event level so WARNING stays a breadcrumb; (4) canary: after deploy, one invalid-refresh probe must create NO new Sentry issue. Not urgent; log hygiene and a small credential-exposure surface.`

const RED_SCHEMA = {
  type: 'object',
  required: ['unit', 'base_sha_confirmed', 'files_written', 'red_count', 'pin_count', 'failures_are_right_reason', 'failure_evidence', 'pins_evidence', 'sdk_measurements', 'baseline_red_nodes_before', 'ci_order_set_base_run', 'measurements', 'spec_disagreements', 'questions_for_fable', 'git_status_final', 'scratch_cleanup'],
  properties: {
    unit: { type: 'string' },
    base_sha_confirmed: { type: 'boolean' },
    files_written: { type: 'array', items: { type: 'string' }, description: '"<path> <sha256>" per file' },
    red_count: { type: 'integer' },
    pin_count: { type: 'integer' },
    failures_are_right_reason: { type: 'boolean' },
    failure_evidence: { type: 'string', description: 'verbatim summary for the new file at HEAD + one sentence per RED row naming the absent behaviour (e.g. the ERROR record carrying the message)' },
    pins_evidence: { type: 'string' },
    sdk_measurements: { type: 'string', description: 'installed supabase / supabase_auth (gotrue) / sentry_sdk versions; the AuthApiError class path and constructor signature; the exact error message + code + status the pinned SDK raises for an invalid refresh token, invalid credentials, unconfirmed email and an existing user (measured by constructing the SDK exceptions the way the SDK does, or by reading its source in the venv - NO network); the LoggingIntegration default event_level in the installed sentry_sdk (read its source)' },
    baseline_red_nodes_before: { type: 'string', description: 'the two tests/test_auth_interceptor.py nodes from tests/.pre_impl_failures.txt run at HEAD: verbatim failure lines (the B4-BE-DIAG reason)' },
    ci_order_set_base_run: { type: 'string', description: '.qa-s68/ci_order_set.txt (sorted) and its ONE-process run at HEAD WITHOUT the new file: summary + every failing node id, marked whether in tests/.pre_impl_failures.txt' },
    measurements: { type: 'array', items: { type: 'string' } },
    spec_disagreements: { type: 'array', items: { type: 'string' } },
    questions_for_fable: { type: 'array', items: { type: 'string' } },
    git_status_final: { type: 'string' },
    scratch_cleanup: { type: 'string' },
  },
}

const prompt = `You are running the RED phase of unit #198 (auth_service log hygiene) for the myez/Qaren backend. Worktree: ${DIR} (branch fix/198-auth-401-log-level at 61585c58 = origin/main). Spec (authoritative): ${SPEC}. Shared rules: read ${COMMON_PATH} in full FIRST and obey every line.

THE ISSUE (verbatim from GitHub):
${ISSUE}

CODE TO READ FIRST: app/services/auth_service.py lines ~150-260 (_TRANSIENT_AUTH_ERROR_TERMS, _upstream_unavailable_result, _categorize_auth_error, _is_transient_upstream_status and the type classifier _is_transient_refresh_error), refresh_session (~428-482), every _categorize_auth_error( call site (register 375, login 426, refresh 480, social_login 803, change_password 821, update_email 839, update_profile 851, password_reset 979, and ~1084), app/api/auth_routes.py refresh route (how the dict maps to 401/503), app/services/sentry_service.py (init_sentry: integrations list, before_send), tests/test_auth_refresh_and_revocation.py and tests/test_retro_r_auth_fixer_pins.py (their caplog patterns - copy the style), tests/test_auth_interceptor.py (the two baseline-red nodes named in tests/.pre_impl_failures.txt), tests/.pre_impl_failures.txt.

YOUR TASK, in order:
0. Confirm HEAD 61585c58 and a clean tree; else STOP.
1. MEASURE (paste every result): the installed supabase / supabase_auth (or gotrue) / sentry_sdk versions in the pinned venv; the AuthApiError class (import path, constructor signature, .status/.code attributes) and the exact message/code/status shapes the pinned SDK produces for an invalid refresh token, invalid credentials, email not confirmed and an existing user (read the SDK's error construction in site-packages - NO network); the installed sentry_sdk LoggingIntegration default event_level (read its source); at HEAD, through a pytest probe under the guard: _categorize_auth_error(AuthApiError('Invalid Refresh Token: Refresh Token Not Found', 400, 'refresh_token_not_found'), 'refresh') emits ONE ERROR record carrying the message (paste the record), and the returned dict; the same for a RuntimeError('boom secret=abc'); the /auth/refresh route with get_auth_client stubbed to raise -> the status code and body at HEAD. Also list the exact dict returned by every branch of _categorize_auth_error at HEAD (these are the byte-identity anchors for T2/T5).
2. WRITE tests/test_auth_error_log_hygiene.py exactly per the spec's section 2 (T1-T9; T10 rows are the green's mutation table, document them in a module docstring). caplog at DEBUG on 'app.services.auth_service'; the module imported after conftest (normal test imports); construct exceptions with the real SDK class where importable, with a plain-Exception fallback that still exercises the message path; no network; every RED fails on an assertion naming the absent behaviour (an ERROR record present / the message present), never on a setup error.
3. RUN the new file; paste the summary; every RED row red, every PIN row green. Run the two baseline-red tests/test_auth_interceptor.py nodes alone at HEAD and paste their failure lines (the pin: they must fail for the B4-BE-DIAG reason before and after the green).
4. DERIVE ${DIR}/.qa-s68/ci_order_set.txt (sorted): the new file, every tests/test_auth*.py, tests/test_retro_r_auth_fixer_pins.py, tests/test_retro_w1_4_server.py, tests/test_retro_w1_4_logout_expired.py, tests/test_password_reset_deep_link.py, tests/test_sentry_service.py and every tests/*.py that greps 'Auth error in' or '_categorize_auth_error' or 'auth_service'. Run it MINUS the new file in ONE process at HEAD under the guard, --timeout=60, CI's deselects from tests/.pre_impl_failures.txt; paste the summary and every failing node id (marked whether in the baseline file).
5. Report per the schema. Leave ONLY tests/test_auth_error_log_hygiene.py (new) and the gitignored .qa-s68/ files changed; 'git status --short' verbatim. Never commit.`

log('unit 3 RED: #198 in ' + DIR)
const red = await agent(prompt, { label: 'red:auth-198', phase: 'Red', model: MODEL, effort: 'high', schema: RED_SCHEMA })
return { unit: 'auth-198', red }
