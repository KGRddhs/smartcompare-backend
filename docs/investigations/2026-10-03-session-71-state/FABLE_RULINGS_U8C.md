
## Orchestrator rulings (BINDING - supersede the review corrections and the body; 2026-10-03 14:44)

Review verdict APPROVED_WITH_CORRECTIONS; corrections C1-C9 are accepted as written and bind the RED and GREEN agents. Rulings on the open questions:

- **UR1 (Q1, C8).** Scope stays at two files: the one-line ` from None` on the deletion route and the new test file. The five other except-arm 5xx sites (push-token, reengagement-subs, preference-toggles, image_routes, share_routes + database_service.create_share_token) and the ErrorHandlerMiddleware f-string with exc_info become ONE follow-up issue filed by the orchestrator at merge, each site needing the type-only log fix and the chain drop together.
- **UR2 (Q2, C1).** R1 prescribes `raise HTTPException(status_code=500, detail="Account deletion failed") from None` inside the route; the pin is behavioural (no AST assertion on the line); the only accepted equivalent still raises that HTTPException inside the route (a plain exception escaping to ErrorHandlerMiddleware re-chains, measured).
- **UR3 (Q3).** Yes: the pin asserts the one route log event in the Sentry channel (logger app.api.auth_routes, logentry formatted `Account deletion failed for user <uid>: <TypeName>`), exactly one per failure.
- **UR4 (Q4, C2, C3).** The real init_sentry runs in a CHILD process per the W1-1b idiom in the measured order (wrap sentry_sdk.init, import app.main with SENTRY_DSN unset, set the dummy DSN, init_sentry() exactly once, assert the memory transport); any log-record assertion attaches after the app import.
- **UR5 (Q5, C5).** APIError is the fourth scenario; the sentinel sits in .message; every leak flag is asserted False.
- **UR6 (Q6).** traces_sample_rate=1.0 in the child; the no-leak sweep covers every envelope item (events, transactions, breadcrumbs, extra, sessions).
- **UR7 (Q7).** No repo-wide from-None ratchet in this unit; the follow-up issue may add one with an allowlist.
- **UR8 (C4).** Sentinel hygiene as corrected; test_success_path_unchanged asserts every flag False as the negative control.
- **UR9 (C6, C7).** The kill set is the new file plus the two U8b files; mutants MU1-MU8 as corrected (MU7 add_note, MU8 set_extra) must each be killed, the two Sentry-clean mutants by the U8b pins.
- **UR10 (files, process).** RED writes only tests/test_account_deletion_u8c_sentry_chain.py (LF, ASCII, no credential-shaped literal, sentinels built at runtime where a shape matters). GREEN edits only app/api/auth_routes.py (the one line; CRLF, Edit tool). Base = main b90b5f07 (the branch feature/s71-u8c-sentry-chain in sc-s71-u8b); the two U8b test files and the U8b fix-pins file stay frozen.
