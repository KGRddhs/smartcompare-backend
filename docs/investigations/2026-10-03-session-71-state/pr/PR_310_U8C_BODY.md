## U8c: account deletion 500 no longer ships the chained exception text to Sentry (#292)

### Problem
`DELETE /api/v1/auth/account` (`app/api/auth_routes.py::delete_account`) caught every failure and raised `HTTPException(500)` inside its `except` arm. Python therefore set `HTTPException.__context__` to the original exception. The Sentry Starlette integration captures 5xx HTTPExceptions and walks that chain, so the 500 event's `exception.values[0]` carried the original exception's text:
- an `httpx.ConnectError` message: URL, user path and `email=` query;
- an `AuthApiError` message (email);
- a `RuntimeError` message;
- an `APIError` `.message`.

U8b had already made both log lines type-only. The chain was the remaining channel.

### Fix (one line)
```python
raise HTTPException(status_code=500, detail="Account deletion failed") from None
```
`from None` sets `__suppress_context__ = True` with `__cause__ = None`, and the pinned SDK (sentry_sdk 2.68.1, `utils.py` L798-801 and L880-925) then emits a single-value exception. The 500 stays visible in Sentry as `HTTPException: Account deletion failed`, next to the type-only route log event (`Account deletion failed for user <uid>: <TypeName>`). Status, response envelope, log line and success path are unchanged.

Caveat (spec C1): this works only because the 500 stays an `HTTPException` handled by `ExceptionMiddleware`. A plain exception escaping to `ErrorHandlerMiddleware` gets its chain back (`BaseHTTPMiddleware` re-raises `from __cause__ or __context__`) and is logged there with `exc_info`.

### Tests
New file `tests/test_account_deletion_u8c_sentry_chain.py` (24 tests). It drives the real app and the real `init_sentry()` in a child process, with:
- an in-memory transport and `traces_sample_rate=1.0`;
- a socket guard, a dummy DSN and `neutralize_credentials()`.

It runs four failure shapes (httpx, authapi, runtime, apierror) and sweeps every envelope item (events, transactions, breadcrumbs, extra, sessions) for the sentinels. It pins:
- exactly one exception event, `[HTTPException 'Account deletion failed']`;
- the U8b status and envelope;
- the type-only route log event;
- that each failure happened where intended;
- the success path, with every leak flag False as a negative control;
- no network attempt;
- the real `init_sentry`.

At base b90b5f07: 8 RED (red1 x4, red2 x4) and 16 PIN green. After the fix: 24 passed.

### Gates (on the final bytes, auth_routes.py sha256 11bb6742...)
- New file alone: 24 passed, netguard 0. `[pyt] tag=u8c-fix-g1 elapsed=62s status=OK rc=0`
- Kill set (u8c + u8b + u8b_fix_pins + account_deletion): 65 passed, netguard 0. `[pyt] tag=u8c-fix-killset elapsed=91s status=OK rc=0`
- delete_user_cascade + sentry_503_suppression + sentry_service + observability + retro_w1_1 + security_regression: 210 passed. The 12 netguard attempts come from 6 nodes, all pre-existing and baselined. `[pyt] tag=u8c-fix-sentry-reg elapsed=126s status=OK rc=0`
- Byte-copy mutants on the edited file, every one KILLED, every restore sha-equal:
  - MU1 (base): 8 failed
  - MU2 `from e`: 8
  - MU3 `from RuntimeError(str(e))`: 8
  - MU4 f-string log: 10, including the U8b pins
  - MU5 hand-built JSONResponse: 4
  - MU6 status 503: 12
  - MU7 `add_note(str(e))`: 8
  - MU8 `set_extra(str(e))`: 4, caught through the transaction item
- Post-mutant kill set: 65 passed. `[pyt] tag=u8c-fix-killset-post-mut elapsed=86s status=OK rc=0`
- py_compile rc 0; ruff E9,F63,F7,F82: All checks passed.
- `git diff --stat`: 1 file, 1 insertion and 1 deletion, CRLF preserved.

### Follow-up (one issue, filed at merge, UG4)
Each site needs a type-only log and `from None` together:
- `auth_routes.py` L1319, L1404, L1474;
- `image_routes.py` L318;
- `share_routes.py` L37 with `database_service.create_share_token` (`exc_info` plus `ShareTokenError(f"...{exc}")`);
- `ErrorHandlerMiddleware`'s `f"Unhandled ...: {exc}"` with `exc_info=True`.

Added by the U8c adversary pass:
- `cache_service.delete_cached` (L682) logs `f"Cache delete error: {e}"` at ERROR, 5x per deletion through the U8b cache purge. The other f-string exception logs in `cache_service.py` have the same shape.
- The Sentry httpx integration records full request URLs, query included, in transaction spans (`parse_url(..., sanitize=False)`), and `_before_send_transaction` does not scrub spans.

An optional AST ratchet ("5xx HTTPException in an except arm must use `from None`", with an allowlist) can go in the same issue.

## Orchestrator review (session 71)
- Process: Opus spec (the leak measured at HEAD on the pinned sentry-sdk 2.68.1 with an in-memory transport; a survey of every raise-inside-except in app/api), Opus adversarial spec review (9 corrections: the fix works only because the 500 stays a FastAPI HTTPException handled in-route; the child fixture order; sentinel hygiene; the all-items sweep), orchestrator rulings UR1-UR10, Opus RED gated PASS (8 reds for the stated reason, 16 pins, satisfiable, six mutants killed on in-memory swaps), Opus GREEN (the one line; MU1-MU8 killed on the edited file), one Opus adversary (nine failure shapes in two logging modes, its own eight mutants, SOUND), fix round with no code change.
- The orchestrator read the one-line diff, fast-forwarded the branch to main `72b13bc5` and re-ran the kill set plus the Sentry files there (95 passed).
- Follow-up issue filed at merge (UR1 / UG4 and the adversary minors): the five other except-arm 5xx sites, the ErrorHandlerMiddleware exc_info line, the cache_service f-string exception logs (five ERROR events per deletion when Redis is down), and the unscrubbed httpx transaction spans.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
