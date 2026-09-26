Session 68 unit 3 (issue #198). Unflagged by ruling (log hygiene, the R-AUTH type-only rule). Process: spec -> red (20 reds / 15 pins) -> Fable gate -> green -> adversary -> fix -> re-adversary -> Fable post-adversary rulings R11-R13 (server-side 4xx stay ERROR; pre-formatted lines so Sentry groups per context+type) -> fix -> re-adversary (SOUND) -> Fable diff review -> one squashed commit rebased onto origin/main 61585c58; ship checks: ruff E9,F63,F7,F82 + py_compile clean, CI-order set 27 files 772 passed / 2 deselected / 0 failed.

## #198 -- expected client auth failures stop logging at ERROR, server-side auth failures stay ERROR, and no auth log line carries the exception text

### Defect
`app/services/auth_service.py::_categorize_auth_error`'s generic branch ran `logger.error(f"Auth error in {context}: {e}")` for every exception that reached it. That had two consequences.
1. An expected client verdict became an ERROR record: an invalid or expired refresh token, a bad JWT, bad input. Sentry's auto-enabled LoggingIntegration turns an ERROR record into an error EVENT. The 2026-09-24 invalid-refresh probe (`POST /api/v1/auth/refresh` with a garbage token, which correctly answers 401) opened a Sentry issue.
2. The record carried `str(e)`. On the auth path an SDK exception can carry a credential: `UserDoesntExist(access_token)`'s `str()` IS the bearer. That text went to the logs and, at ERROR, to Sentry.

### Design (spec section 1 as amended by rulings R3/R4/R5, then R11/R12)
`_is_expected_client_auth_error(e)` decides client verdict vs application error. It checks four things in this order.
1. **R11 carve-out, first:** return False (application error) when `type(e).__name__ == "AuthSessionMissingError"`. The SDK raises that when OUR code calls it without a session, which is a programming state.
2. **Still the carve-out:** return False when `str(e).lower()` contains an entry of `_SERVER_SIDE_AUTH_ERROR_TERMS = ("invalid api key", "no api key found", "not allowed", "not_admin", "is disabled", "are disabled")`. These cover Kong's 401 on a wrong or missing Supabase key, gotrue's 403 not_admin, and gotrue config states such as signups, email logins or linking disabled. The carve-out runs before BOTH the status rule and the fragment fallback, whatever the status.
3. **Status rule:** an int, non-bool `.status` decides alone: `400 <= status < 500 and status != 429`.
4. **Fragment fallback:** only an exception with no int status reaches `_EXPECTED_CLIENT_AUTH_ERROR_TERMS`. Its entries are lower-case fragments of gotrue wordings measured on the pinned supabase-auth 2.31.0: "invalid refresh token", "refresh token not found", "already used", "invalid jwt", "token is expired", "invalid token", "user not found", "already been registered", "new password should be different", "password should be at least". The three early-return wordings are omitted because they return before the generic branch.

Every entry of both tuples has its own pinning rows.

Every RETURNED dict is byte-identical to base in every branch. That includes the social_login `[B4-BE-DIAG] supabase_error=<str(e)[:300]> exc_type=<Type>` RESPONSE, which is kept until Google Sign-In is resolved. Its two red-by-choice `tests/test_auth_interceptor.py` baseline nodes still fail for that reason only.

### Log contract (the generic branch only)
- **Expected client failure:** ONE `WARNING [auth] <context> rejected upstream: <Type> status=<status>`. The status prints `None` when the exception has none.
- **Anything else:** ONE `ERROR Auth error in <context>: <Type>`. The base prefix is kept so the line stays grep-stable.
- **Type only:** never `str(e)`, never `exc_info`, never `stack_info`, never `extra=`.
- **What counts as "anything else":** a server-side credential/config failure (R11) is an ERROR whatever its status. That covers a status-401/403/422 AuthApiError carrying a carve-out term, AuthSessionMissingError (status 400), and a status-less re-wrapped exception whose text carries both a carve-out term and an expected-client fragment. A plain expected 400/401 is still a WARNING.
- **R12 grouping contract:** both lines are PRE-FORMATTED from context + exception type (+ status) with NO record args: `logger.error("Auth error in " + context + ": " + type(e).__name__)` and `logger.warning("[auth] " + context + " rejected upstream: " + type(e).__name__ + " status=" + str(getattr(e, "status", None)))`. Neither piece derives from `str(e)`. Pinned: `record.args` is falsy, `record.msg == record.getMessage()`, and distinct (context, type) pairs give distinct messages.
- **Unchanged:** the message-matched early returns and the transient branch log nothing, as at base. `refresh_session`'s transient WARNING is unchanged.

### Flag row
UNFLAGGED by ruling. This is log hygiene with no legitimate reader of the old line (the R-AUTH type-only rule). Default = effect ON = the only state. There are no knobs, and OFF-identity does not apply. The identity proof is that every returned dict is pinned to the literal base dicts and the diff is function-local.

### Sentry consequence (measured on sentry-sdk 2.68.1)
- **Levels.** `LoggingIntegration` is in `_DEFAULT_INTEGRATIONS` (auto-enabled), with `DEFAULT_LEVEL = INFO` (breadcrumb) and `DEFAULT_EVENT_LEVEL = ERROR` (event). `app/services/sentry_service.py` passes no LoggingIntegration, no event_level and no default/disabled-integrations override; T8 pins that at source level. So the WARNING is a breadcrumb and the ERROR is an event.
- **Grouping (R12).** With no record args, Sentry's `logentry.message` IS the pre-formatted line, so each (context, type) pair is its own issue. This was measured with a loopback DSN and a `before_send` that captured and returned None, so nothing was sent and the drop transport saw zero envelopes. `update_profile/RuntimeError`, `login/KeyError`, `login/RuntimeError` and `login/AuthApiError` produced four distinct `logentry.message` values, each with `params: []`. The expected-client WARNING appeared only as a breadcrumb. A new class of unexpected auth failure therefore opens a NEW issue, and a new-issue alert fires for it. Grouping itself is Sentry server behaviour; what was measured is the SDK payload.
- **Extras and stack_info.** The LoggingIntegration ships a record's `extra=` attributes (`event["extra"]` / breadcrumb `data`). For a record with `stack_info`, it attaches a stacktrace that carries frame locals only when `include_local_variables` is on. `init_sentry` sets it off (`sentry_service.py:324`), so in this app that stacktrace carries no locals. T3 still reads `extra=` attributes and `stack_info` and asserts `stack_info is None`. So `extra={...: str(e)}` or `stack_info=True` on either line reddens T3.

### Measured SDK strings (supabase-auth 2.31.0, `helpers.handle_exception` over in-memory HTTPStatusErrors)
| gotrue/Kong body | str(e) | status | code | logged as |
|---|---|---|---|---|
| refresh token not found | Invalid Refresh Token: Refresh Token Not Found | 400 | refresh_token_not_found | WARNING |
| refresh already used | Invalid Refresh Token: Already Used | 400 | refresh_token_already_used | WARNING |
| legacy invalid_grant | Invalid Refresh Token: Refresh Token Not Found | 400 | None | WARNING |
| bad credentials | Invalid login credentials | 400 | invalid_credentials | early return |
| unconfirmed | Email not confirmed | 400 | email_not_confirmed | early return |
| existing user | User already registered / A user with this email address has already been registered | 422 | user_already_exists / email_exists | early return / WARNING |
| expired JWT | invalid JWT: unable to parse or verify signature, token has invalid claims: token is expired | 401 | bad_jwt | WARNING |
| same password | New password should be different from the old password. | 422 | same_password | WARNING |
| rate limit | Request rate limit reached | 429 | over_request_rate_limit | ERROR (transient WARNING in refresh_session) |
| Kong wrong key | Invalid API key | 401 | None | ERROR (R11) |
| Kong missing key | No API key found in request | 401 | None | ERROR (R11) |
| admin 403 | User not allowed | 403 | not_admin | ERROR (R11, via "not allowed") |
| signups off | Signups not allowed for this instance | 422 | signup_disabled | ERROR (R11) |
| email logins off | Email logins are disabled | 422 | email_provider_disabled | ERROR (R11) |
| anonymous off | Anonymous sign-ins are disabled | 422 | anonymous_provider_disabled | ERROR (R11) |
| manual linking off | Manual linking is disabled | 422 | manual_linking_disabled | ERROR (R11) |

- **The code is never in the text.** `str(e)` is the message only. So the `"not_admin"` carve-out entry matches no text the pinned SDK produces: the real 403 not_admin maps to "User not allowed", which the "not allowed" entry catches. The entry is kept because R11 lists it, and its row (a synthetic "Forbidden (code=not_admin)") proves the entry is live, not that it matches a real wording.
- **Correction to earlier rounds:** NOT every SDK exception carries `.status`. `supabase_auth.errors.UserDoesntExist` and `AuthUnknownError` carry none; in the measured probe `hasattr(e, "status")` was False for both. The fragment tuple therefore decides them. Their texts match no fragment, so both log `ERROR Auth error in refresh: UserDoesntExist` / `... AuthUnknownError`, type-only, and their argument (for UserDoesntExist, the bearer) reaches no record. `AuthSessionMissingError` does carry `status=400` and is caught by the R11 type check before the status rule.

### R1 pin rewrite (the one collision)
`tests/test_password_reset_deep_link.py::test_a_failure_after_the_gate_is_scrubbed_and_does_not_burn_the_token` asserted the OLD contract (`"policy rejected" in caplog.text`). It now asserts exactly one ERROR `Auth error in password_recovery: Exception` and `"policy rejected" not in caplog.text`. The token-absent, payload-absent and revoke-not-called lines are verbatim, and the docstring is updated. Reverting the pin reddens it (mutation-checked).

### Gates (measured)
- **Unit files** (`tests/test_auth_error_log_hygiene.py`, 69 nodes, plus `tests/test_password_reset_deep_link.py`, 42 nodes): 111 passed, netguard 0. Also 111 passed with every adjacent auth flag forced ON.
- **CI-order = comm set:** 27 files, one process, CI deselects, --timeout=60. Result: 772 passed / 2 deselected / 0 failed. Base was 703 / 2 / 0; +69 is the new file. Netguard shows 42 pre-existing blocked attempts, unchanged from base (the hermeticity unit's business).
- **Mutation table:** 55 rows from byte snapshots with sha256-verified restores, all killed:
  - the 30 earlier rows: the seven T10 rows, an f-string carrying str(e) into the args, a WARNING including str(e), the R1 pin reverted, ERROR/WARNING `extra=str(e)` and `stack_info=True`, the four status-boundary rows, status-OR-tuple, the bool exclusion dropped, and each of the 10 expected-client entries removed;
  - 15 R11/R12 rows: carve-out removed, the session check alone, the term check alone, carve-out after the status rule, term tuple emptied, each of the 6 carve-out terms removed, both / ERROR-only / WARNING-only lines reverted to a %-template with args, and str(e) appended;
  - 10 round-3 rows. Two are the re-adversary's former survivors, now killed by one status-less row per carve-out term whose text also carries "invalid token": the carve-out consulted only for int-status exceptions, and the fragments winning for status-less exceptions. The others: session check after the status rule, startswith, no lower(), WARNING without status, ERROR without context, logger.exception, WARNING at INFO, and a dict record arg.
- **B4 baseline nodes:** red before and after, for the B4-BE-DIAG reason only.
- **Hygiene:** ruff E9,F63,F7,F82 clean; py_compile clean; CRLF throughout.

### Canary (orchestrator or Ahmed, after deploy)
Send ONE invalid-refresh probe against prod: `POST /api/v1/auth/refresh` with a NON-EMPTY garbage refresh token. Expected results:
- it answers 401 with the unchanged body `{success:false, code:AUTH_REQUIRED, error:"Something went wrong. Please try again later.", request_id}`;
- it creates NO new Sentry issue;
- it leaves one `[auth] refresh rejected upstream: AuthApiError status=400` WARNING in the Railway log.

Two probes are NOT part of the canary.
- A deliberately wrong-API-key probe would page, by design: it is the R11 server-side class and logs an ERROR event.
- An EMPTY-string refresh token makes the SDK raise AuthSessionMissingError before any network call. That maps to `ERROR Auth error in refresh: AuthSessionMissingError` under R11, the same level as at base (measured through the route: 401 AUTH_REQUIRED plus that one ERROR record).

### Stated limits
1. **R2 (out of scope):** `complete_password_recovery`'s outer catch (auth_service.py:1144-1146) re-wraps as `Exception(str(e).replace(access_token, ...))`, dropping `.status`/`.code`. On that path, classification uses the texts only: the carve-out terms first, then the expected-client fragments. Anything else logs `ERROR Auth error in password_recovery: Exception`, and the type is always `Exception`.
2. **Broad carve-out matching.** The carve-out is substring matching, deliberately broad as ruled. A future gotrue client-verdict wording that happens to contain a carve-out term would log ERROR. That fails toward visibility, not silence.
3. **Empty refresh tokens.** An empty-string refresh token from a client (for example a client bug) creates a Sentry ERROR event via AuthSessionMissingError, as it did at base.
4. **What the pins can see.** The T3 pins read a record's message, template, args, exc_info/exc_text, stack_info and `extra=` attributes. They cannot see a handler-side enrichment added later, such as a logging Filter that copies exception text onto records.

### Follow-ups
1. (R2) Preserve the original type/status in `complete_password_recovery`'s re-wrap. This is a small unit of its own.
2. Other auth_service.py log sites still carry exception text. Line numbers were re-verified on the final bytes:
   - ERROR (Sentry events): :592 `Error getting user profile: {e}`; :931 `get_user_preferences failed ...: {e}`; :971 `save_user_preferences failed ...: %s: %r` with `e` (the exception repr).
   - WARNING: :377 `Could not fetch profile ...: {e}`; :461, :515 and :844 `preferences_completed lookup failed: %s` e; :581 `Token verification failed: {e}`; :754 `Failed to revoke token in Redis ...: {e}`.
   - Token-SCRUBBED `str(e)` WARNINGs: :718 (logout upstream leg); :1113 and :1119 (password recovery).

   One type-only sweep unit covers all of these.
3. **Monitoring after a Supabase key change:** a wrong key is now a Sentry issue again (`Auth error in login: AuthApiError`). Still verify that a real login succeeds after any rotation.

### CLAUDE.md corrections for the docs PR
- Record the #198 log contract in the session block: the two pre-formatted line shapes, the type-only rule, and the R11 server-side carve-out. State that expected client 4xx are breadcrumbs while each (context, type) ERROR pair is its own Sentry issue.
- The W1-4 row's "a failed upstream leg is logged at WARNING naming the leg and the exception type" is incomplete. The non-expired logout leg (:718) also logs the token-scrubbed `str(e)` (follow-up 2).

Closes #198

🤖 Generated with [Claude Code](https://claude.com/claude-code)

---
Closes #198

🤖 Generated with [Claude Code](https://claude.com/claude-code)
