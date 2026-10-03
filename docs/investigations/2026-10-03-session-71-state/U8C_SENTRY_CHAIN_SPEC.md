# U8c: the account-deletion 500 sends no chained exception text to Sentry (issue #292)

Spec writer: Opus (read-and-measure only), session 71, 2026-10-03 13:05-14:00 AST.
Scratch evidence: `<SP>/u8c/` where `<SP>` = `C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/3ffde5dd-0e09-4243-bf73-02955e287dff/scratchpad`
(notes.md, test_probe_u8c.py, summ.py, survey.py, survey.txt, survey.json, u8c_swap_plugin.py, probe_*.json and *.log, pins_*.log).
`<V>` = `C:/Users/SynAckITPC/Documents/AI/.venv-qaren/Scripts/python.exe`, `<W>` = `C:/Users/SynAckITPC/Documents/AI/sc-s71-u8b`.
No file in `<W>` was written. Every route variant below was measured by swapping the handler's `__code__` in memory inside a pytest process. The swap is restored afterwards, and the worktree's bytes and status were unchanged at the end.

## 1. Base

```
$ git -C <W> rev-parse HEAD            -> b90b5f07950833f6e66f751b9358fbd6fcfff507
$ git -C <W> status --porcelain        -> (empty)   [re-checked 13:33: 0 lines]
$ git -C <W> branch --show-current     -> feature/s71-u8c-sentry-chain
$ git -C <W> log --oneline -2          -> b90b5f07 Merge PR #297 (U13) / 62c74a0d Merge PR #290 (U8b)
$ <V> -c "import sentry_sdk,fastapi,starlette,httpx,sys; ..."
  -> 2.68.1 0.141.1 1.6.0 0.28.1 3.12.9
$ sha256(app/api/auth_routes.py) = 6773bf0b6eaf5c661a1b6a3bf94485fa1a88d47cdb0c8eda7153f8b6dca577fd
  (working copy CRLF: crlf 1624 / lf 1624; git ls-files --eol -> i/lf w/crlf)
```

## 2. Measured facts

### 2(a) The deletion route handler (`app/api/auth_routes.py`, `delete_account`, L1165-1181)

`sed -n 1165,1181p app/api/auth_routes.py`:
```python
@router.delete("/account")
@limiter.limit("1/minute")
async def delete_account(
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    """Delete user account and all associated data (App Store requirement)."""
    try:
        await delete_user_account(current_user["id"])
        return {"success": True, "message": "Account and all associated data deleted"}
    except Exception as e:
        # U8b: the exception TYPE only -- str(e) of a PostgREST APIError carries
        # the failing row (the user's personal data).
        logger.error(
            "Account deletion failed for user %s: %s", current_user["id"], type(e).__name__
        )
        raise HTTPException(status_code=500, detail="Account deletion failed")
```
L1181 bytes are `b'        raise HTTPException(status_code=500, detail="Account deletion failed")\r'`. It has no `from` clause, so Python sets `HTTPException.__context__ = e` and `__suppress_context__ = False`.
The callee is `app/services/auth_service.py::delete_user_account` (L1008-1023). It runs the cascade RPC (`delete_user_data_cascade`), then `_purge_deleted_user_caches` (fail-soft), then `get_admin_client().auth.admin.delete_user(user_id)`, and nothing catches an exception it raises.

### 2(b) How Sentry is wired, and what a 5xx raised inside an except arm produces at HEAD

`app/services/sentry_service.py::init_sentry` (L281-334), called at import in `app/main.py:42-43`:
- `integrations=[FastApiIntegration(transaction_style="endpoint", failed_request_status_codes=_captured_5xx), StarletteIntegration(same)]`, where `_captured_5xx = frozenset(range(500,600)) - {503}`.
- The SDK default `LoggingIntegration` is not passed explicitly, so the defaults apply: INFO and above become breadcrumbs and ERROR and above become events. This is measured below: the route's `logger.error` becomes its own event plus a breadcrumb.
- `send_default_pii=False`, `include_local_variables=False`, `traces_sample_rate=0.1`, `before_send=_before_send`, `before_send_transaction=_before_send_transaction`, `before_breadcrumb=_strip_tokens_from_breadcrumb`.
- `_before_send` (L191-265) rewrites `exception.values[].value` only through `_scrub_string`. That function applies `_SENSITIVE_PATTERNS` (JWT, `sk-proj-`, `fc-`, hex{32,}, `Bearer x`). It has no email pattern, and it does not query-scrub exception values. The query-string scrub applies only to `request.url` and `request.query_string`.
- `app/main.py:160` sends `HTTPException` to `app/middleware/error_handler.py::http_exception_handler` through Starlette's ExceptionMiddleware. The SDK patches that middleware and captures an `HTTPException` whose status is in the set. `ErrorHandlerMiddleware` (error_handler.py L230-261, which logs `f"Unhandled ...: {exc}"` with `exc_info=True`) is never reached for an HTTPException. The measured evidence: the body carries `code: SERVER_ERROR` from `http_exception_handler`, not "Internal server error", and no `Unhandled` log record appears.
- The SDK walks the chain on the pinned version. `sentry_sdk/utils.py` L798 (`walk_exception_chain`) and L880-925 (`exceptions_from_error`) follow `__cause__` when `__suppress_context__` is set and `__context__` otherwise. `raise ... from None` therefore leaves `__cause__=None` with `__suppress_context__=True`, so nothing is chained.
- On the pinned SDK the exception `value` is `.message` when the object has one (APIError, AuthApiError) and `str(e)` otherwise (httpx, RuntimeError). This is measured below.

**Probe** (`<SP>/u8c/test_probe_u8c.py`). It drives the REAL app (`from app.main import app` with `SENTRY_DSN=https://pub@o1.ingest.example.invalid/1` and `sentry_sdk.init` wrapped to inject an in-memory `Transport`; the probe asserts that the client's transport is the in-memory one) through `TestClient(raise_server_exceptions=False).delete("/api/v1/auth/account")`. It patches only `verify_token`, `get_admin_supabase_client` (cascade RPC), `get_admin_client` (auth delete), `cache_service.redis_client` and `limiter.enabled=False`. Every logger is set to DEBUG with one root capture handler. Sentinels: `SENT`=a plain word, `EMAIL`=`...@example.invalid`, `HOST`=`u8cproj.supabase.example.invalid`, shown below only as `<SENT>/<EMAIL>/<HOST>`.
```
$ PROBE_VARIANT=head PROBE_OUT=<SP>/u8c/probe_head.json PYTHONIOENCODING=utf-8 <V> <SP>/harness/pyt.py --bound 600 --tag u8c-probe-head --log <SP>/u8c/probe_head.log --cwd <W> -- <SP>/u8c/test_probe_u8c.py -q
[pyt] tag=u8c-probe-head start=2026-10-03 13:11:44 end=2026-10-03 13:12:17 elapsed=33s bound=600s status=OK rc=0
$ <V> <SP>/u8c/summ.py <SP>/u8c/probe_head.json   (excerpt)
== a_httpx_connecterror_url status=500 body={"success": false, "error": "Account deletion failed", "code": "SERVER_ERROR"} admin_del=1 rpc=1
   log app.api.auth_routes ERROR exc_info=False leak=False msg=Account deletion failed for user user-u8c-probe: ConnectError
   sentry event level=error logger=app.api.auth_routes leak_anywhere=False
      logentry={"message": "Account deletion failed for user %s: %s", "formatted": "...user-u8c-probe: ConnectError", "params": [...]}
   sentry event level=error logger=None leak_anywhere=True leak_keys=['exception']
      exception type=ConnectError value=connect failed for https://<HOST>/auth/v1/admin/users/<SENT>?email=<EMAIL> mech=starlette
      exception type=HTTPException value=Account deletion failed mech=starlette
      crumb app.api.auth_routes error Account deletion failed for user user-u8c-probe: ConnectError
   sentry item=sessions leak=False
== b_authapierror  ... HTTPException event: exception type=AuthApiError value=User <SENT> <EMAIL> not allowed ; type=HTTPException
== c_runtimeerror_email (cascade raises) ... 3 events: database_service log event (type-only), auth_routes log event (type-only),
      HTTPException event: exception type=RuntimeError value=boom for <SENT> <EMAIL> ; type=HTTPException
== d_apierror (cascade raises APIError message "m <SENT>", details "d <EMAIL>") ... HTTPException event:
      exception type=APIError value=m <SENT>   (details/hint absent: .message only) ; type=HTTPException
== e_success status=200 ... only a 'sessions' item
```
Across all five scenarios: **0 leaking log records and 0 records with exc_info** (U8b holds). The only leak is `exception.values[0]`, the chained `__context__`, on the Starlette HTTPException event. `leak_keys` = `['exception']`, so the stacktrace, request, breadcrumbs and extra are clean. With traces on (`PROBE_TRACES=1.0`, tag `u8c-probe-traces-head`, 68s OK rc=0), the `transaction` items carry no sentinel either.

### 2(c) What `raise ... from None` changes, and other places the original exception could surface

The probe was re-run with the handler's code swapped in memory (`_swap()` in the probe: `inspect.getsource`, the one line replaced, compiled into the module globals, assigned to `delete_account.__wrapped__.__code__`, restored in `finally`):

| variant (PROBE_VARIANT) | [pyt] line | status/body/route log line | HTTPException event `exception.values` | sentinel anywhere in envelopes |
|---|---|---|---|---|
| `fix_from_none` (L1181 + ` from None`) | tag=u8c-probe-fix_from_none 32s OK rc=0 | identical to HEAD | `[HTTPException "Account deletion failed"]` | **none** (a/b/c/d) |
| `mut_from_e` | tag=u8c-probe-mut_from_e 85s OK rc=0 | identical | `[<orig>, HTTPException]` | exception (= HEAD) |
| `mut_new_exc_embeds_str` (`from RuntimeError(str(e))`) | tag=u8c-probe-mut_new_exc_embeds_str 79s OK rc=0 | identical | `[RuntimeError <text>, HTTPException]`; for APIError, `str(e)` is the dict repr **including details `d <EMAIL>`** | exception |
| `mut_fstring_log_plus_from_none` | tag=u8c-probe-mut_fstring_log_plus_from_none 64s OK rc=0 | log line carries text | `[HTTPException]` | route log event `logentry` + **breadcrumbs of the HTTPException event** |
| `mut_capture_suppressed_return_json` (return a hand-built 500 JSONResponse) | tag=u8c-probe-mut_capture_suppressed_return_json 47s OK rc=0 | **identical** status/body/log | **no HTTPException event at all** | none |
| `mut_raise_outside_except` (flag in except, raise after the try) | tag=u8c-probe-mut_raise_outside_except 52s OK rc=0 | identical | `[HTTPException]` | none (an EQUIVALENT of the fix) |
| `fix_from_none`, traces 1.0 | tag=u8c-probe-traces-fix_from_none 49s OK rc=0 | identical | `[HTTPException]` | none, transactions included |

Other places the original exception could surface after the fix (measured on the variant runs):
- The log records emitted come only from the loggers `app.api.auth_routes`, `app.services.database_service`, `asyncio` and `httpx2`. 0 records carry `exc_info`, and no starlette, fastapi or uvicorn logger emits anything. ServerErrorMiddleware and ErrorHandlerMiddleware are not reached because the HTTPException is handled.
- The uvicorn access log is NOT exercised under TestClient. By its format it carries only the client address, method, path and status: an inference, not a measurement.
- The remaining Sentry carriers of the error are the two type-only log events (`app.api.auth_routes`, plus `app.services.database_service` on cascade failures). The 500 stays visible in Sentry as a single-value HTTPException event.

### 2(d) Survey: every `raise HTTPException(...)` inside an `except` arm in app/api/*.py

`<V> <SP>/u8c/survey.py <W> <SP>/u8c/survey.json > <SP>/u8c/survey.txt` is an AST walk. A raise counts when it sits lexically in an `ExceptHandler` body, and the walk resets at nested def or lambda. Result: `rows 10, by_status {'500': 6, '503': 1, '429': 1, '400': 1, '403': 1}, with_cause 0`. Other raises in except arms: 1 (`feedback_routes.py:26 _validate_optional_uuid`, a pydantic `ValueError`, which becomes a 422). Out of 69 `raise HTTPException` lines in 15 files. Only 5xx except 503 reaches Sentry through the integration (2b), so the 503, 429, 400 and 403 rows cannot ship the chain.

| file:line | handler (route) | caught | status | what the chained text can carry | does the text already reach Sentry another way? | verdict |
|---|---|---|---|---|---|---|
| auth_routes.py:1181 | `delete_account` (DELETE /account) | `Exception` | 500 | httpx: str with URL/query; AuthApiError `.message`; RuntimeError str; APIError `.message` (measured 2b) | no: U8b made both log lines type-only (measured) | **IN-UNIT** |
| auth_routes.py:1319 | `update_push_token` (PUT /push-token) | `Exception` | 500 | PostgREST APIError `.message` / httpx str from `users.update(expo_push_token)` (inferred) | **yes**: `logger.warning(f"push token update failed for {id}: {exc}")` (L1318), a WARNING, so a breadcrumb on the same 500 event carrying `str(APIError)` = dict repr incl. details (shape measured in the `mut_fstring_log` row) | follow-up (needs the type-only log AND `from None` together) |
| auth_routes.py:1404 | `update_reengagement_subs` (PUT /reengagement-subs) | `Exception` | 500 | same (users select+update preferences) | **yes**: WARNING `"%s: %s: %r", user_id, type, exc`, giving a breadcrumb with `repr(exc)` | follow-up (same) |
| auth_routes.py:1474 | `update_preference_toggles` (PUT /preference-toggles) | `Exception` | 500 | same | **yes**: same WARNING `%r` | follow-up (same) |
| image_routes.py:318 | `identify_and_compare` (POST /identify) | `Exception` | 500 | OpenAI SDK errors (`Error code: 4xx - {...}`), parse errors; no user PII expected, and a key in a 401 message is masked plus scrubbed by the `sk-proj-` pattern (inferred) | **yes**: `logger.error(f"[IMAGE] Vision call failed: {e}")` (L301), its own ERROR event | follow-up / low (de-chaining alone changes nothing) |
| image_routes.py:314 | same | `Exception` | 503 | same | 503 is dropped by the integration set and `_before_send` | fine |
| share_routes.py:37 | `share_comparison` (POST /share/{id}) | `ShareTokenError` | 500 | `ShareTokenError(f"...: {exc}") from exc` (database_service.py L600/L648): `str(APIError)` incl. details, e.g. a 23505 `Key (share_token)=(...)` (a share-link capability token) | **yes**: the service logs `exc` with `exc_info=True` at ERROR (`create_share_token`, L596-599 and L638-641), and the route logs `f"Share token creation failed: {exc}"` at ERROR (L36) | follow-up (service + route logs + chain; bigger than one line) |
| referral_routes.py:218 | `share_comparison` (POST /share) | `WeeklyInviteCapExceeded` | 429 | n/a (4xx not captured) | n/a | fine |
| referral_routes.py:226 | same | `ValueError` | 400 | `str(exc)` goes into the **response body** (not Sentry) | n/a | fine for this unit (a body-content question, not the chain) |
| share_routes.py:31 | `share_comparison` | `PermissionError` | 403 | n/a | n/a | fine |

Survey limit: implicit chaining also happens when the raise sits in a helper CALLED from an except arm (`__context__` is runtime state). The AST walk sees only the lexical case.

### 2(e) Existing tests that pin the deletion route, and which would notice the change

`grep -n "def test_\|__context__\|__cause__\|sentry\|from None" ...` finds no existing test that reads `__context__`, `__cause__` or a Sentry event for this route.
- `tests/test_account_deletion_u8b.py::test_delete_route_failure_logs_no_exception_text` and `tests/test_account_deletion_u8b_fix_pins.py::{test_delete_route_failure_log_requests_no_traceback, test_delete_route_failure_formatted_log_record_carries_no_row_details}`: status 500, `"Account deletion failed"` in body, no sentinel in the response or the log. They are blind to the chain.
- `tests/test_account_deletion.py::TestAccountDeletion::{test_delete_account_requires_auth, _success, _failure, _response_message}`: status and message only.
- `tests/test_delete_user_cascade.py`: static SQL of migration 025, unrelated to the route.
- `tests/test_sentry_service.py` and `tests/test_sentry_503_suppression.py`: unit tests of `_before_send` and the 503 set. They never drive a route.
- `tests/test_retro_w1_1.py::TestW11bEndToEnd` is the REPO IDIOM for "real init_sentry() + in-memory transport + real app" (a child process via `subprocess.run([sys.executable, "-c", _CHILD])` with a socket guard and `neutralize_credentials()`). It covers admin-key headers, not this route.

Measured:
```
$ <V> <SP>/harness/pyt.py --bound 1200 --tag u8c-pins-head --log <SP>/u8c/pins_head.log --cwd <W> -- tests/test_account_deletion_u8b.py tests/test_account_deletion_u8b_fix_pins.py tests/test_account_deletion.py tests/test_delete_user_cascade.py tests/test_sentry_503_suppression.py tests/test_sentry_service.py tests/test_security_regression.py -q
188 passed, 10 warnings in 52.12s ; [netguard] blocked 12 attempt(s) from 6 node(s) (pre-existing test_security_regression nodes, as U8b recorded)
[pyt] tag=u8c-pins-head start=2026-10-03 13:26:56 end=2026-10-03 13:27:59 elapsed=63s bound=1200s status=OK rc=0
$ PYTHONPATH=<SP>/u8c ... pyt.py --bound 1200 --tag u8c-pins-fixswap ... -- -p u8c_swap_plugin -s <same 7 files> -q     (handler swapped to `from None`)
188 passed, 10 warnings in 68.78s ; [pyt] tag=u8c-pins-fixswap start=2026-10-03 13:28:21 end=2026-10-03 13:29:39 elapsed=77s bound=1200s status=OK rc=0
$ U8C_SWAP=capture_suppressed PYTHONPATH=<SP>/u8c ... pyt.py --bound 600 --tag u8c-u8b-under-mu5 ... -- -p u8c_swap_plugin -s tests/test_account_deletion_u8b.py tests/test_account_deletion_u8b_fix_pins.py tests/test_account_deletion.py -q
41 passed, 8 warnings in 22.07s ; [pyt] tag=u8c-u8b-under-mu5 start=2026-10-03 13:31:50 end=2026-10-03 13:32:21 elapsed=31s status=OK rc=0
```
Provenance notes on these runs:
- An earlier run under the same tag (13:30:35, 49s OK) actually ran the `from None` swap, because a heredoc edit of the plugin failed. That run reads `41 passed` and its log was renamed to `<SP>/u8c/u8b_under_fix_from_none.log`; it is the G2 fix measurement for those three files.
- In the MU5 run, the plugin asserts `"JSONResponse(status_code=500" in src` before swapping. The swapped code's compile label stays `<u8c-fix-from-none>` in both modes; it is cosmetic.
**No existing test notices the fix, and none notices MU1/MU2/MU3 or MU5.** MU4 (the f-string log) is already killed by U8b's own pins (U8b adversary M12r KILLED, adv-backend notes 11:36).

## 3. Requirements

- **R1** In `delete_account`, the 500 raised from the `except Exception as e` arm carries no chained exception: `__cause__ is None` and `__suppress_context__ is True`. Prescribed form: append ` from None` to L1181. Equivalent forms (the raise moved after the try behind a flag) are acceptable only by ruling (Q2).
- **R2** For each failure shape (httpx.ConnectError whose message has a URL with an `email=` query, AuthApiError whose message has an email, RuntimeError whose message has an email; APIError per Q5), driven through the real app with the real `init_sentry()` and an in-memory transport, **no envelope item of any type** (event, transaction, sessions) contains the email, the sentinel word or the URL host.
- **R3** The 500 stays visible in Sentry. Exactly one captured event has an `exception`, and its `exception.values` is exactly one entry: `type == "HTTPException"`, `value == "Account deletion failed"`.
- **R4** Status, envelope and log line stay identical to U8b. Status 500. Body without `request_id` == `{"success": false, "error": "Account deletion failed", "code": "SERVER_ERROR"}`, and `request_id` is present. Exactly one Sentry event has `logger == "app.api.auth_routes"`, and its `logentry.formatted == "Account deletion failed for user <uid>: <TypeName>"`.
- **R5** The success path is unchanged (200, same body). The order cascade, then purge, then auth delete is unchanged (U8b pins).
- **R6** Nothing else changes: no other route, no logging change, no `sentry_service.py` change, no scrubber pattern (#286), nothing under SmartCompareApp/ or backend/app/.
- **R7** The pin is hermetic. It uses no network (a socket guard in the child plus an assertion that no attempts happened), a dummy DSN, no real credential, `neutralize_credentials()` in the child, and no sentinel in argv (ArgvIntegration copies sys.argv into events, per the comment at test_retro_w1_1.py L388). It installs no global Sentry client in the pytest process.

## 4. Files

Touch (2):
- `app/api/auth_routes.py`: ONE line, L1181 `raise HTTPException(status_code=500, detail="Account deletion failed")` becomes `... from None`. An optional comment of at most 2 lines above it, naming U8c/#292, is allowed. Use the Edit tool (CRLF preserved). `git diff --stat` must show only 1-3 changed lines.
- `tests/test_account_deletion_u8c_sentry_chain.py`: NEW.

MUST NOT change: `tests/test_account_deletion_u8b.py`, `tests/test_account_deletion_u8b_fix_pins.py`, `tests/test_account_deletion.py`, `tests/test_delete_user_cascade.py`, `tests/test_sentry_*.py`, `tests/test_retro_w1_1.py`, `app/services/{sentry_service,auth_service,database_service,cache_service}.py`, `app/middleware/error_handler.py`, `app/main.py`, every other `app/api/*.py` (the survey's follow-ups), `backend/app/**`, `SmartCompareApp/**`, `requirements*.txt`, `tests/.pre_impl_failures.txt`, migrations.

## 5. Tests (`tests/test_account_deletion_u8c_sentry_chain.py`)

Structure (the W1-1b idiom). A module-scoped fixture runs ONE child process: `subprocess.run([sys.executable, "-c", _CHILD], cwd=REPO_ROOT, env=<os.environ minus SENTRY_DSN, PYTHONIOENCODING=utf-8>, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=540)`. The child:
1. installs the socket guard, runs `neutralize_credentials(); install_dotenv_guard()`;
2. wraps `sentry_sdk.init` to inject an in-memory `Transport` (collects `(item.type, item.get_bytes())`) and to force `traces_sample_rate=1.0`;
3. sets `SENTRY_DSN` to a dummy `https://public@o0.ingest.example.invalid/1`, imports `app.main`, calls `init_sentry()` explicitly if needed, and asserts that `get_client().options["transport"]` is the memory transport (or prints `{"fatal":...}`);
4. per scenario, under `patch("app.api.auth_routes.verify_token", ...)`, `patch("app.services.database_service.get_admin_supabase_client")`, `patch("app.services.auth_service.get_admin_client")`, `patch("app.services.cache_service.redis_client", MagicMock())` and `patch("app.middleware.rate_limiter.limiter.enabled", False)`, it calls `TestClient(app, raise_server_exceptions=False).delete("/api/v1/auth/account", headers={"Authorization": "Bearer u8c-token"})` and then `sentry_sdk.flush()`. It records status, body, `admin.delete_user.call_count`, `rpc.call_count`, and per item the type, the raw text, the parsed `exception.values[{type,value}]`, `logger` and `logentry.formatted`;
5. prints `RESULT <json>` with the leak check done in the child: a boolean per item for each sentinel, so the sentinels never travel through the parent's assertion messages verbatim.

The scenarios are the shapes from 2(b): `httpx` (auth delete raises `httpx.ConnectError("connect failed for https://<host>.example.invalid/auth/v1/admin/users/<SENT>?email=<EMAIL>")`), `authapi` (`AuthApiError("User <SENT> <EMAIL> not allowed", 403, "not_admin")`), `runtime` (cascade RPC `execute` raises `RuntimeError("boom for <SENT> <EMAIL>")`), plus `apierror` if Q5 is ruled yes (`APIError({"message": "m <SENT>", "code": "P0001", "hint": None, "details": "d <EMAIL>"})`). The sentinels are plain words plus `@example.invalid`: no hex32, JWT, `sk-` or `Bearer`-followed token (those would be scrubbed or rejected by pre-commit). Each test is parametrized over the scenario ids, and the class gets `@pytest.mark.timeout(600)`.

RED (fail at b90b5f07 for the right reason; measured shapes in 2b):
- `test_no_envelope_item_carries_the_chained_exception_text[httpx|authapi|runtime(|apierror)]` (R2): every item's leak flags are false. At base: True on the `event` item whose `exception.values[0]` is the original exception (measured 2b).
- `test_the_500_event_carries_only_the_http_exception[...]` (R1/R3): exactly one event with `exception`, and its `[(type, value)] == [("HTTPException", "Account deletion failed")]`. At base: `[("ConnectError"|"AuthApiError"|"RuntimeError"|"APIError", <text>), ("HTTPException", ...)]` (measured).

PIN (green at base and after):
- `test_status_and_envelope_unchanged[...]` (R4): 500; body minus request_id equals the measured dict; `request_id` present.
- `test_route_log_event_is_type_only[...]` (R4): exactly one event with `logger == "app.api.auth_routes"`, with `logentry.formatted == f"Account deletion failed for user {USER_ID}: {TypeName}"`.
- `test_the_failure_really_happened_where_intended[...]`: `httpx`/`authapi` give rpc 1 and admin delete 1; `runtime` gives rpc 1 and admin delete 0. This proves the sentinel was raised on the path under test.
- `test_success_path_unchanged`: 200 and the success body; no event with `exception`.
- `test_child_made_no_network_attempt`: the guard log is empty.
- `test_child_really_used_the_real_init_sentry`: no `fatal`; the transport is the memory one (the W1-1b guard).

Named mutants (each applied by byte-copy, then replace, then pyt 600, then restore and sha-compare, as in the U8b adversary `mutate.py`; kill set = the new file. Behaviour measured in 2c):
- **MU1** ` from None` removed (= base). The probe shows the leak, so it is KILLED by both RED tests.
- **MU2** `from e`. The probe shows the leak (same as base), so it is KILLED by both RED tests.
- **MU3** `from RuntimeError(str(e))` (a new exception embedding `str(e)`). The probe shows `[RuntimeError <text>, HTTPException]`, so it is KILLED by both RED tests.
- **MU4** the log line restored to `logger.error(f"Account deletion failed for user {current_user['id']}: {e}")` with `from None` kept. The probe shows a leak in the route log event's logentry and in the 500 event's breadcrumbs, so it is KILLED by the no-leak test and the type-only log pin (and by U8b M12r).
- **MU5** capture suppressed instead of de-chained: `return JSONResponse(status_code=500, content={...same envelope...})`. The probe shows zero HTTPException events with status, body and log identical, and the U8b and account-deletion files SURVIVE it (41 passed, measured). It is KILLED only by `test_the_500_event_carries_only_the_http_exception`.
- **MU6** the status changed to 503 (dropped by `_before_send`). It is KILLED by the status pin and by the U8b status asserts. Inferred, not probed.
- Not a mutant: the raise moved after the try behind a flag. It is measured EQUIVALENT to the fix (2c), so the behavioural pin passes it by design (Q2).

## 6. GREEN gates (one pytest process at a time, all through pyt.py)

- G0 (RED proof, before the source edit): `PYTHONIOENCODING=utf-8 <V> <SP>/harness/pyt.py --bound 600 --tag u8c-red --log <log> --cwd <W> -- tests/test_account_deletion_u8c_sentry_chain.py -rA`. Expect FAIL, with ONLY the two RED tests failing and their failure text naming the original exception type. The PIN tests pass.
- G1: the same file after the edit. Expect OK, all passed, `[netguard] blocked 0`.
- G2: `... --bound 600 --tag u8c-u8b -- tests/test_account_deletion_u8b.py tests/test_account_deletion_u8b_fix_pins.py tests/test_account_deletion.py tests/test_delete_user_cascade.py`. All pass (41 measured for the first three under the swapped fix, plus test_delete_user_cascade).
- G3: `... --bound 600 --tag u8c-sentry -- tests/test_sentry_503_suppression.py tests/test_sentry_service.py tests/test_observability.py tests/test_retro_w1_1.py`. All pass. Baseline at HEAD: `93 passed, 9 warnings in 71.85s`, `[netguard] blocked 0`, `[pyt] tag=u8c-g3-head start=2026-10-03 13:36:46 end=2026-10-03 13:38:03 elapsed=76s bound=600s status=OK rc=0`.
- G4: `... --bound 1200 --tag u8c-secreg -- tests/test_security_regression.py`. All pass. The 12 netguard attempts from 6 nodes are pre-existing (measured at HEAD).
- G5 mutants MU1-MU5: `... --bound 600` each on the new file, killed as stated. Every restore must be sha-equal.
- G6: `<V> -m ruff check --select E9,F63,F7,F82 --no-cache app/api/auth_routes.py tests/test_account_deletion_u8c_sentry_chain.py` gives "All checks passed!". `<V> -m py_compile <same two>` gives rc 0.
- G7 hygiene:
  - `git -C <W> diff --stat` shows exactly 2 paths. auth_routes.py shows 1-3 lines, with no whole-file CRLF churn (`git diff --ignore-cr-at-eol --stat` equals `git diff --stat`).
  - The new file is ASCII. `grep -n "sk-" <new file>` finds nothing.
  - No other file in `git status --porcelain`.
- The module-reference comm gate is NOT required. Measured: one route line changes, no import or module-level symbol changes, and every existing pin file passes under the swapped fix (188/188).

## 7. Risks and stated limits

- Debuggability trade: after the fix, Sentry shows only `HTTPException: Account deletion failed` plus the type-only log events (`...: ConnectError` and `...: APIError (sqlstate=23514)` from database_service). The stack of the original failure is gone from Sentry. This is intended (#292). The type name and SQLSTATE remain for triage.
- The child-process fixture costs one app import (the probe took ~30-80 s for 5 scenarios on this box; the variance is the box). That is the reason for the 600 s class timeout and the 540 s subprocess timeout.
- The probe measured the in-memory swapped code, not the edited file. The GREEN agent's G1 measures the real edit.
- Not measured: the uvicorn access log (inferred method, path and status only); real Supabase/GoTrue exception text (the sentinels are synthetic shapes). Implicit chaining through helpers called from except arms was not surveyed (2d limit).
- The survey's five other 500 sites already ship their exception text to Sentry through their own log lines or `exc_info`. `from None` alone does nothing for them (2d). They need log + chain fixes together: follow-up scope.

## 8. Open questions, with recommendations

- **Q1** Survey follow-ups (`auth_routes.py` L1319/L1404/L1474, `image_routes.py` L318, `share_routes.py` L37 plus `database_service.create_share_token`). **Recommend: NOT in this unit.** File ONE follow-up issue ("type-only logs + `from None` for the remaining 5xx except arms"), grouped as: the auth_routes trio (same shape as U8b+U8c), share (service `exc_info=True` + `str(APIError)` in `ShareTokenError` text, possibly a share-link token from a 23505), and image (low: OpenAI text, no user PII expected).
- **Q2** Prescribe `from None` literally, or accept any de-chaining form? **Recommend:** prescribe ` from None` on L1181 (one token, explicit). Keep the pin behavioural so the flag-after-try equivalent would also pass. Add no AST/static assertion on the line.
- **Q3** Should the pin assert the route's Sentry log event (`logger == app.api.auth_routes`, type-only formatted text)? **Recommend: yes.** It is the only pin of the U8b log line in the Sentry channel, and it is stable: exactly one such event per failure, measured.
- **Q4** Child process or in-process `init_sentry`? **Recommend: child process** (the W1-1b idiom). The SDK integrations patch Starlette globally, and an in-process client would leak into later tests in the same worker.
- **Q5** Add APIError as a fourth scenario? **Recommend: yes.** It is cheap, and at base it is RED for a `.message` containing the sentinel (measured: `value=m <SENT>`). It also guards MU3, which for APIError leaks `details` (measured).
- **Q6** Force `traces_sample_rate=1.0` in the child? **Recommend: yes.** It makes the item set deterministic (the prod value of 0.1 is random) and puts the transaction item inside the no-leak sweep (measured clean at head and fix).
- **Q7** A repo-wide ratchet ("no 5xx HTTPException raised in an except arm without `from None`")? **Recommend: no, not in U8c.** It would fail on the five follow-up sites today. Consider it in the follow-up, with an allowlist.

## Review corrections (BINDING - supersede the body)

Adversarial reviewer: Opus, read-and-measure only, session 71, 2026-10-03 13:40-14:10 AST. Evidence lives in `<SP>/u8c/review/` (notes.md, test_adv_u8c_child.py, summ_adv.py, adv_all.json / adv_all_summary.txt, adv_run2.json / adv_run2_summary.txt, adv_survey.py / adv_survey.txt / adv_survey.json, adv_survey2.py / adv_survey2.txt, adv_swap_plugin.py, u8b_debug.log, u8b_warnexc.log, adv_child*.log). No file in `<W>` was written. Re-checked at 14:01: `git -C <W> status --porcelain | wc -l` gives 0, and the auth_routes.py sha256 is still 6773bf0b...

**Re-measured and CONFIRMED (the body stands on these points):**
- HEAD b90b5f07, the branch, a clean tree, and the versions (sentry 2.68.1, fastapi 0.141.1, starlette 1.6.0, httpx 0.28.1, Python 3.12.9). L1181 has no `from`.
- The SDK walks the chain only through `__suppress_context__`: `sentry_sdk/utils.py` L798-801 and L881-925.
- The integration patches only the `ExceptionMiddleware` handlers (`integrations/starlette.py` L289-322 and L448). `http_exception_handler` does not log (error_handler.py L113-143). `enable_logs` is unset (default False). The LoggingIntegration defaults are INFO for breadcrumbs and ERROR for events. `_SENSITIVE_PATTERNS` has no email pattern.
- My own probe used the spec's child-process design: `subprocess -c`, the socket guard, `neutralize_credentials(); install_dotenv_guard()`, the memory transport, traces 1.0, and init AFTER the app import. Run: `[pyt] tag=u8c-adv-child elapsed=44s status=OK rc=0` and `[pyt] tag=u8c-adv-child2b elapsed=22s status=OK rc=0`, with `_network_attempts []`.
  - HEAD, httpx: `exc=[ConnectError 'connect failed for https://<HOST>/...<SENT>?email=<EMAIL>' (starlette), HTTPException 'Account deletion failed']`, `leak_keys=['exception']`. authapi and runtime have the same shape. apierror: `[APIError 'm <SENT>', HTTPException]`; only the sentinel word leaks, because `details` never reaches Sentry.
  - `from None`, all 4 failure scenarios: the single exception event is `[HTTPException 'Account deletion failed' (starlette)]`. No item (event, transaction or sessions) carries any flag. There is exactly one `app.api.auth_routes` log event, `Account deletion failed for user <uid>: <Type>`. Status 500, the body is identical, `request_id` is present, and the rpc and admin_del counts are as stated in section 5. The success path gives `[transaction, sessions]` with no flag.
  - The log records after the fix come from `app.api.auth_routes` ERROR (plus `app.services.database_service` ERROR for runtime and apierror), `asyncio` and `httpx2`. 0 records leak and 0 carry `exc_info`. No starlette, fastapi, uvicorn or error_handler record appears.
- Survey: my own AST walk over ALL of `app/**` (`adv_survey.py`). It does not reset at nested defs, it records `from` clauses, and it follows same-module helper calls. `adv_survey2.py` adds cross-module 5xx helpers called from except arms. Result: 69 `raise HTTPException` in total. There are exactly the writer's 10 raise-in-except rows (six 500s, plus 503, 429, 400 and 403), with 0 `from` clauses and 0 inside nested defs. 12 functions raise a 5xx HTTPException, and NONE is called from an except arm. The only helper called from an except arm is `auth_routes.py:459 _reject_or_anonymous` (401). The log lines at the five follow-up sites are verified as the writer quotes them. The section 2(d) "Survey limit" and the section 7 line "Implicit chaining through helpers ... was not surveyed" are therefore superseded: helper chaining was measured and none was found.

**Corrections:**

1. **`from None` works ONLY because the 500 stays an `HTTPException` that `ExceptionMiddleware` handles. A plain exception re-acquires its chain.** `starlette/middleware/base.py` L168 (BaseHTTPMiddleware, which `ErrorHandlerMiddleware` subclasses) does `raise app_exc from app_exc.__cause__ or app_exc.__context__`, so a suppressed `__context__` becomes `__cause__`. Measured with the variant `raise RuntimeError("Account deletion failed") from None`: body `{"error": "Internal server error"}`, and the ErrorHandlerMiddleware log event carries `exc=[ConnectError '...<SENT>?email=<EMAIL>' (mechanism logging), RuntimeError 'Account deletion failed']`, so it LEAKS. A bare `raise` leaks in both `logentry` (`Unhandled ConnectError: <text>`) and `exception`. Binding consequences:
   - R1 now reads: "the raised object is `fastapi.HTTPException(status_code=500, detail="Account deletion failed")` raised `from None`".
   - The ONLY equivalent accepted under Q2 is one that still raises that HTTPException inside the route, for example after the try. Converting it to a plain exception, re-raising, or returning a JSONResponse is NOT equivalent. MU5 already covers the JSONResponse case. The R3 and R4 pins catch the plain-exception and re-raise cases, because the body changes to "Internal server error" and the exception type changes.

2. **The child fixture's import order is fixed to the measured W1-1b order.** Section 5 step 3 ("sets SENTRY_DSN ..., imports app.main, calls init_sentry() explicitly if needed") is ambiguous: with the DSN set before the import AND an explicit call, the SDK initialises twice. Prescribed order:
   1. wrap `sentry_sdk.init`;
   2. `import app.main` with `SENTRY_DSN` unset (the import-time `init_sentry()` is a no-op);
   3. set the dummy DSN in `os.environ`;
   4. call `init_sentry()` exactly once;
   5. assert `get_client().options["transport"] is _MemoryTransport`, else print `{"fatal": ...}`.
   Measured to work: StarletteIntegration captures still apply, because the middleware stack is built lazily at the first request.

3. **Log-record capture in the child: a root handler installed BEFORE `import app.main` captures nothing.** `configure_logging()` (main.py L15, then `app/middleware/logging_config.py` L35-44) clears the root handlers. Measured: my first run recorded 0 records, and the second run, with the handler re-attached after the import, recorded them. The section 5 tests assert through Sentry log events, which is fine. If the GREEN agent adds any log-record assertion in the child, it MUST attach the handler after the import, or the assertion is vacuous.

4. **Sentinel hygiene and a negative control (R2/R7).**
   - The sentinel word, the email and the host must not be substrings of USER_ID, the bearer token, the worktree path (which contains `u8b`/`u8c`), module or file names, or the route path.
   - None of them may match a `_SENSITIVE_PATTERNS` regex, which would scrub it and make the result falsely GREEN.
   - `test_success_path_unchanged` additionally asserts that every item's leak flags are False. This shows the sweep is not tripped by harness text, so a RED result has the right cause. Measured: the success items at HEAD carry no flag.

5. **The APIError scenario (Q5) gets its RED signal ONLY from the sentinel word in `.message`.** Measured at HEAD, apierror flags only `sent`; `details`/email never reach Sentry (`get_error_message` = `.message or .detail or str(e)`, utils.py L655-660). So the sentinel word MUST be in `message`, and the no-leak assertion is "every flag False", never "no email" alone. For httpx, authapi and runtime, the flags at HEAD are sent+email(+host).

6. **The kill set is the new file PLUS the two U8b files.** Two measured log mutants never reach Sentry, so the U8c file alone cannot kill them:
   - `logger.debug("...: %s", e)` + `from None`. Sentry is clean, because DEBUG is below the INFO breadcrumb level. It is KILLED by U8b: `[pyt] tag=u8c-adv-u8b-debug elapsed=56s status=FAIL rc=1`, 2 failed / 39 passed (`test_delete_route_failure_logs_no_exception_text`, `test_delete_route_failure_formatted_log_record_carries_no_row_details`).
   - `logger.warning("...", exc_info=True)` + `from None`. Sentry is clean, because the breadcrumb carries only the message. It is KILLED by U8b: `[pyt] tag=u8c-adv-u8b-warnexc elapsed=76s status=FAIL rc=1`, 2 failed / 39 passed (`test_delete_route_failure_log_requests_no_traceback`, `..._formatted_log_record_carries_no_row_details`).
   G5 lists them as "killed by the U8b pins (measured by the reviewer)". The GREEN agent need not re-run them.

7. **Two cheap named mutants are added to G5. Both are measured as leaking, and both are killed only by the design choices in this spec:**
   - **MU7**: `_h = HTTPException(500, "Account deletion failed"); _h.add_note(str(e)); raise _h from None`. Sentry appends `__notes__` to the value (utils.py L666-668), giving the measured value `'Account deletion failed\n<text>'`. It is KILLED by the R3 exact-value assertion and by the sweep.
   - **MU8**: `sentry_sdk.set_extra("deletion_error", str(e))` + `from None`. It leaks in `event.extra` AND in the `transaction` item (measured). It is KILLED only because the sweep covers EVERY item with traces 1.0 (Q6).
   - Also measured: `logger.error("...", exc_info=True)` + `from None` produces a SECOND exception-bearing event (mechanism logging, `[ConnectError <text>]`). It is killed by R3 ("exactly one event has `exception`") and by the sweep, and by U8b MD2.
   - `logger.info("...: %s", e)` + `from None` leaks through the HTTPException event's breadcrumbs, and the sweep kills it.

8. **Additions to the follow-up issue (Q1):**
   - (a) The `ErrorHandlerMiddleware` class. It logs `f"Unhandled {type(exc).__name__}: {exc}"` with `exc_info=True` (error_handler.py L237-247). Every plain exception that escapes ANY route therefore ships its text and its whole chain to Sentry. Measured via a bare `raise`: `leak_keys=['exception','logentry']`. Per correction 1, `from None` cannot help on that path. This is likely a wider exposure than the five sites. It belongs in the follow-up, and it is a logging change, so it stays out of U8c.
   - (b) The follow-up must state correction 1: de-chaining works only for an HTTPException handled in-route.
   - (c) `share_routes` / `database_service.create_share_token` as the writer described. A 23505 on the third attempt reaches the `exc_info=True` ERROR log (L634-641).

9. **Scope and hygiene are unchanged.** It is still exactly 2 files. The route edit is 1-3 lines (Edit tool, CRLF). No other change.

**Answers to the writer's open questions (RECOMMENDATIONS):**
- **Q1** AGREE: none of the five other sites belongs in U8c. File ONE follow-up issue with: the auth_routes trio (type-only log + `from None`); share (service `exc_info` + `ShareTokenError(f"...{exc}")` + route f-string log + chain); image (low); PLUS correction 8(a) (`ErrorHandlerMiddleware`'s f-string + `exc_info`); and the correction 1 caveat.
- **Q2** AGREE with an amendment: prescribe ` from None` on L1181 literally, and keep the pin behavioural with no AST assertion. The only accepted equivalent still raises the same HTTPException inside the route (correction 1).
- **Q3** AGREE: yes. Assert exactly one event with `logger == "app.api.auth_routes"` and `logentry.formatted == "Account deletion failed for user <uid>: <TypeName>"`. This was re-measured for all four failure shapes at HEAD and with the fix.
- **Q4** AGREE: a child process, in the import order of correction 2. The `-c` source is not in argv (`sys.argv == ['-c']`), so literal sentinels in the child source are safe from ArgvIntegration. Measured: at HEAD the only flagged key is `exception`.
- **Q5** AGREE: yes, with the sentinel word in `.message` (correction 5).
- **Q6** AGREE: yes. MU8 (correction 7) is measured to leak into the transaction item, so traces 1.0 is load-bearing, not just deterministic.
- **Q7** AGREE: no ratchet in U8c. In the follow-up, an AST ratchet "5xx `HTTPException` raised lexically in an except arm must have `from None`" with an allowlist is sound: measured, there are no helper or nested-def cases today. It cannot see the `ErrorHandlerMiddleware` path (correction 8a), so it is not a complete guard.

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

## Orchestrator gate on the RED tests (BINDING - supersedes everything above where they differ; 2026-10-03 16:09)

Gate: **PASS.** tests/test_account_deletion_u8c_sentry_chain.py (sha256 233a3807faa668b7...; LF, ASCII, sentinels built at run time on the .example TLD) is FROZEN from here on. At HEAD b90b5f07: 8 RED (red1 x4 shapes: an envelope item carries the chained text; red2 x4: the 500 event lists the original exception before the HTTPException) each for the stated reason, 16 PIN green (status/envelope, the type-only route log event, the failure really happened, the success path with every flag False, no network, the real init_sentry, the sentinel control through the real scrubber); satisfiable (24 passed under an in-memory from-None swap that reaches the child); six mutants KILLED on in-memory swaps (MU2, MU3, MU4, MU5, MU7, MU8); the equivalent of UR2 (the HTTPException raised after the try) passes.

- **UG1.** GREEN edits ONE line of app/api/auth_routes.py: the deletion route's `raise HTTPException(status_code=500, detail="Account deletion failed")` gains ` from None` (CRLF kept, Edit tool). Nothing else changes.
- **UG2 (gates).** The new file alone (24 passed, netguard 0); the kill set in one process (the new file + tests/test_account_deletion_u8b.py + tests/test_account_deletion_u8b_fix_pins.py + tests/test_account_deletion.py: 65 passed); tests/test_delete_user_cascade.py, tests/test_sentry_503_suppression.py, tests/test_sentry_service.py, tests/test_observability.py, tests/test_retro_w1_1.py, tests/test_security_regression.py in one process; py_compile + ruff on the edited file; the spec G5 byte-copy mutants MU1-MU8 on the EDITED file (restore by sha256); git diff --stat = one file, one line.
- **UG3.** No comm gate: one line in one route module; the kill set and the Sentry files cover the module reference set.
- **UG4 (follow-up at merge).** The five other except-arm 5xx sites and the ErrorHandlerMiddleware exc_info line become one issue (UR1).
