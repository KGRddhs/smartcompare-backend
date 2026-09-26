# FABLE RULINGS #198 (session 68, 2026-09-26) — red gate R1-R10, post-adversary R11-R13 (re-created in the state folder from the orchestrator's copy)

RED GATE: PASSED (20 right-reason reds, 15 pins, prototype 35/35 green with all seven T10 mutants killed; the two B4-BE-DIAG baseline nodes red before and after for their own reason only).

R1 the ONE colliding pin `tests/test_password_reset_deep_link.py::test_a_failure_after_the_gate_is_scrubbed_and_does_not_burn_the_token` may be rewritten to the type-only contract (exactly one ERROR `Auth error in password_recovery: Exception`, `"policy rejected" not in caplog.text`); lines 560-564 verbatim; docstring updated.
R2 `complete_password_recovery` re-wraps as `Exception(str(e))`, dropping `.status`/`.code`: OUT of scope, stated limit + follow-up (filed as #203).
R3 the expected-client tuple = message fragments only, measured gotrue wordings, every entry pinned, no code matching; "token is expired" not "token has expired"; the three early-return wordings omitted.
R4 status rule: int, not bool, 400 <= s < 500, s != 429.
R5 log lines carry ONLY the type name and status, never `str(e)`, never `exc_info`.
R6 T4/T9 as the red adjusted them. R7 no LoggingIntegration / event_level override anywhere. R8 the two B4 baseline nodes stay red for the B4 reason only.
R9 unit files = the hygiene test + the deep-link file; the comm gate == the one-process CI-order run over the 27-file set; mutation table = the seven T10 rows + f-string-into-args + WARNING-with-str(e) + the R1 pin reverted.
R10 pr_text contents (log contract, Sentry consequence, canary, SDK strings table, R1 rewrite, R2 limit, kept B4 response, Closes #198).

POST-ADVERSARY (the r0 adversary's two design consequences of R4/R5 were NOT accepted as stated limits):
R11 server-side 4xx stay ERROR: `_is_expected_client_auth_error` returns False BEFORE the status rule when the type is `AuthSessionMissingError` or the message contains a `_SERVER_SIDE_AUTH_ERROR_TERMS` entry ("invalid api key", "no api key found", "not allowed", "not_admin", "is disabled", "are disabled"); every entry pinned; the carve-out precedes both the status rule and the expected-client fragments (the r2 adversary's two survivors A1/A2 closed by the round-3 pin).
R12 both log lines PRE-FORMATTED from context + type (+ status) with no record args, so Sentry's logentry.message differs per (context, type) and each pair is its own issue.
R13 pr_text corrections: 30 mutants + the new rows; "every SDK exception carries .status" is FALSE on supabase-auth 2.31.0 (`UserDoesntExist`, `AuthUnknownError`); the follow-up log-site list re-verified; the canary excludes a wrong-API-key probe (it pages by design).
