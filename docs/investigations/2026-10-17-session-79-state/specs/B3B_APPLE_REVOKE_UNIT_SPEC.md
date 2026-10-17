# B3B unit spec (measured): Sign in with Apple token revocation on account deletion

- Unit: B3-B (backend, one PR, dark flag `ENABLE_APPLE_TOKEN_REVOCATION`). Worktree `C:\Users\SynAckITPC\Documents\AI\sc-s79-b3revoke`, branch `feature/s79-b3-apple-revoke`, base main `b965c63b` (`git rev-parse HEAD` = `b965c63bd2a59be8ad9c3d5d2e1cccd5702c19d5`, `git status --short` empty at the start and after every probe below).
- Evidence: audit finding P1 (and its refutation: P1 stands, severity medium; Apple's account-deletion page says apps offering Sign in with Apple "should" revoke tokens through the REST API; TN3194 describes the fallback for an app that holds no token) in `scratchpad/b3/audit_findings_for_b3.json`; ASC facts `scratchpad/audit/ASC_FACTS_2026-10-17.md` (bundle `com.qaren.app`, build 1.0.0 (2) rejected 2.1 Information Needed, repo public).
- Sister unit: B3-A (client, `sc-s79-b3client`) sends the Apple `authorizationCode` as `authorization_code` in the `POST /api/v1/auth/social-login` body. B3-B adds the backend field and everything behind it. No client file is touched here.
- Personal-data rule: no home address, phone number or personal email appears in this file or in anything the unit writes. Team ID, key ID and the .p8 are written only as synthetic test values (`TEAMID0000`, `KEYID00000`, a key generated in the test process); the real values live only in Railway.
- Every measurement below was taken read-only on the base tree or in throwaway processes under `<scratchpad>/b3b/` (probe scripts and their `.out` files; pytest only through the bounded runner). Nothing in the worktree was written except this file.

## 0. What the unit does (one paragraph)

Behind `ENABLE_APPLE_TOKEN_REVOCATION` (default OFF, read per call): when an Apple sign-in arrives with an `authorization_code`, the backend builds a short-lived ES256 client-secret JWT from four new variables, exchanges the code at `https://appleid.apple.com/auth/token`, checks that the returned identity is the one that just signed in, and upserts the Apple `refresh_token` into a new service-role-only table `public.apple_siwa_tokens` (migration 044). On `DELETE /api/v1/auth/account` it reads that token before the existing cascade, runs the unchanged cascade and cache purge, posts the token to `https://appleid.apple.com/auth/revoke` (at most two attempts), and then runs the unchanged auth-user delete, whose `ON DELETE CASCADE` removes the token row. Every Apple-side failure is logged by exception type or HTTP status and never fails the sign-in or the deletion. Flag OFF: no new call, no new table read or write, response bodies byte-identical.

## 1. Base state (measured at b965c63b)

### 1.1 The sign-in path

| what | where | measured fact |
|---|---|---|
| request model | `app/api/auth_routes.py:297-304` | `SocialLoginRequest(BaseModel)`: `provider: Literal["google","apple"]`, `id_token: str`, `nonce: Optional[str] = None`, `terms_accepted`, `terms_version` (`max_length=32`), `age_attested`. No `model_config`: probe `probe_typ_pydantic.out` prints `base model_config: {}`, and a body with `authorization_code` (string or `123`) validates with the field dropped (`dump keys` exclude it). So a B3-A client is harmless against the base backend. |
| route | `auth_routes.py:1147-1162` | `@router.post("/social-login")`, `@limiter.limit("10/minute")`. Body: `consent_from_fields(...)` -> `await sign_in_with_social(body.provider, body.id_token, body.nonce, consent=consent)` -> on `success` False raise 401 / consent 400 -> W3-3 block `if social_device_fingerprint_enabled(): _apply_social_device_fingerprint(request, (result.get("user") or {}).get("id"))` -> `return result`. |
| service | `app/services/auth_service.py:783-863` | `sign_in_with_social(provider, id_token, nonce=None, *, consent=None)`: `get_auth_client().auth.sign_in_with_id_token(credentials)`; then `get_admin_client()` selects / inserts the `users` row (new-user consent gate W3-16 returns before the insert); then the `preferences_completed` read; returns `{success, user{id,email,preferences_completed}, session{...}, message}` enriched by `_enrich_response_with_profile`. The Supabase calls are synchronous (no `run_db` here). Broad `except` -> `_categorize_auth_error(e, "social_login")`. |
| admin client | `auth_service.py:192-205` | `get_admin_client()` raises `ValueError` when `SUPABASE_URL` / `SUPABASE_SERVICE_KEY` are unset; memoised under `ENABLE_SUPABASE_CLIENT_REUSE`. |
| client deadline | `SmartCompareApp/src/services/fetchWithDeadline.ts:47` | `SOCIAL_LOGIN_TIMEOUT_MS = 25000` (Apple post at `authService.ts:1087`). Any exchange added to the route must stay well inside 25 s. |
| client code source | `smartcompare/SmartCompareApp/node_modules/expo-apple-authentication` 8.0.8 (= `package-lock.json:7073-7074`), `build/AppleAuthentication.types.d.ts:146-150` | `authorizationCode: string | null` ("A short-lived session token ... ephemeral and will change each session"). Build 2 never reads it (audit P1). Every Apple sign-in on a B3-A build carries a fresh code. |

### 1.2 The deletion path (exact order)

`auth_routes.py:1165-1181` `@router.delete("/account")`, `@limiter.limit("1/minute")`, `Depends(get_current_user)` -> `await delete_user_account(current_user["id"])` -> `{"success": True, "message": "Account and all associated data deleted"}`; any exception -> `logger.error("Account deletion failed for user %s: %s", id, type(e).__name__)` and `HTTPException(500, "Account deletion failed") from None`.

`auth_service.py:1008-1023` `delete_user_account(user_id)`, order measured and pinned by `tests/test_account_deletion_u8b.py::test_delete_order_is_cascade_then_purge_then_auth_delete` (events `["cascade"] + ["purge"]*5 + ["auth_delete"]`):
1. `await delete_user_data_cascade(user_id)` (`app/services/database_service.py:392-406`: `get_admin_supabase_client().rpc("delete_user_cascade", {"target_user_id": user_id}).execute()`; raises on error, nothing else runs);
2. `await _purge_deleted_user_caches(user_id)` (`auth_service.py:993-1005`, five Redis keys from `DELETED_USER_CACHE_KEY_TEMPLATES` at `:984`, fail-soft, WARNING by type);
3. `admin = get_admin_client(); admin.auth.admin.delete_user(user_id)` (raises -> propagates; retry safe because the cascade is idempotent).

The cascade (migration 043, applied 2026-10-10) keeps a de-identified `public.users` stub and sets `auth_provider` to NULL (`migrations/043_delete_user_cascade_full_erasure.sql`, users UPDATE). Live FK: `users_id_fkey FOREIGN KEY (id) REFERENCES auth.users(id) ON DELETE CASCADE` = branch A (`docs/investigations/2026-10-10-session-76-state/PRECHECK_043_GRID_2026-10-10.md:4`), so step 3 also deletes the stub.

There is no Apple call anywhere: `grep -rn "appleid" app/` is empty; the T7b scanner (below) finds no `app/services/*apple*` module (`probe_fence_t7b.out`).

### 1.3 Flag-reader idiom

`os.getenv("ENABLE_X", "false").strip().lower() in ("true", "1", "yes", "on")`, read per call, e.g. `auth_service.py:596-617` (`logout_upstream_revocation_enabled`), `auth_routes.py:384-406` (`social_device_fingerprint_enabled`). The new reader copies it verbatim.

### 1.4 Libraries (measured on the pinned venv, `probe_jwt_httpx.out`, `probe_typ_pydantic.out`)

- `requirements.txt:123` `pyjwt==2.15.1` ("via supabase-auth"); `:33` `cryptography==50.0.0` ("via pyjwt"); `:66` `httpx==0.28.1`. `requirements.in` names none of PyJWT / cryptography: both are transitive. `supabase_auth-2.31.0.dist-info/METADATA`: `Requires-Dist: pyjwt[crypto]>=2.12.0`. `app/` imports neither `jwt` nor `cryptography` today. The unit adds no dependency and does not edit requirements files (see Q8).
- PyJWT 2.15.1 `jwt.encode(claims, <PKCS#8 PEM str or EC key object>, algorithm="ES256", headers={"kid": K})` returns a `str`; default header `{"alg": "ES256", "kid": K, "typ": "JWT"}`; with `headers={"kid": K, "typ": None}` the header is exactly `{"alg": "ES256", "kid": K}` (`api_jws.py:160-167`: `if not header["typ"]: del header["typ"]`). Signature segment decodes to 64 bytes (raw r||s, the JOSE form Apple expects). A PEM whose newlines are the two characters `\` `n` -> `ValueError`; garbage -> `ValueError`; an RSA PEM for ES256 -> `InvalidKeyError`. `jwt.algorithms.has_crypto` True.
- httpx 0.28.1: `httpx.AsyncClient(transport=httpx.MockTransport(handler))` works with a sync or async handler; `transport=None` gives the default `AsyncHTTPTransport`; the handler sees `request.extensions["timeout"] == {"connect": 5.0, "read": 5.0, "write": 5.0, "pool": 5.0}` for `timeout=5.0` (`probe_ext.out`); `jwt.decode(t, options={"verify_signature": False})` returns the claims and raises `DecodeError` on a non-JWT; `post(url, data={...})` sends `application/x-www-form-urlencoded`; a handler raising `httpx.ConnectTimeout` propagates as `ConnectTimeout`. House pattern for outbound calls: `async with httpx.AsyncClient(timeout=X) as client:` (`push_service.py:156`, `exchange_rate_service.py:171`); tests patch `<module>.httpx.AsyncClient` (`tests/test_push_service.py:382`, `tests/test_brightdata_fallback.py:100`). B3-B uses an explicit `_TRANSPORT` seam instead (section 2.6) so no test patches the global httpx class.

### 1.5 How multi-line secrets are carried

None exists today: `grep -rn -i -E "PRIVATE_KEY|BEGIN |b64decode" app/` finds only JWT-segment and Basic-auth decoding (`auth_routes.py:811`, `auth_service.py:1093`, `main.py:512`), no secret read from base64 and no PEM. Env is loaded by `load_dotenv(override=True)` (`app/main.py:11`), which accepts a double-quoted multi-line value; Railway variables accept multi-line values. There is no house base64 pattern, so the reader accepts three forms (section 2.1, Q3).

### 1.6 Storage constraints (why a table, why `auth.users`, what the U8b fence says)

- `public.users` has RLS with `users_select USING (auth.uid() = id)` (`migrations/010_enable_rls.sql:17-18`): a token column on `users` would be readable by the user's own JWT through PostgREST, and a column-level REVOKE does not override a table-level grant. A separate table with RLS on, no policy and `REVOKE ALL ... FROM PUBLIC, anon, authenticated` is service-role only (the `031_eval_runs.sql:79-82` "NO policy, internal" posture).
- The U8b deletion fence (`tests/test_migration_043_delete_user_cascade.py:352-626`) parses every forward migration. Probe `probe_fence_t7b.out` (in memory, the real fence functions):
  - base: 12 user tables == `KNOWN_USER_TABLES`, 0 gaps;
  - with the proposed 044 (section 2.4): 13 tables, the new one `apple_siwa_tokens: {"user_id": "id"}` (an FK to `auth.users` is caught by `_REFS_USERS`), exactly ONE new gap `apple_siwa_tokens.user_id not deleted, not nulled, not KEEP-listed`; users columns unchanged (27); `refresh_token` is not classified personal by `PERSONAL_RX`;
  - with a `KEEP_TABLE_COLUMNS[("apple_siwa_tokens", "user_id")]` entry: 0 new gaps;
  - the rejected users-column variant gives `users.apple_refresh_token neither cleared nor KEEP-listed` (and would break the 27-column pin).
  So 044 necessarily changes two 043 pins (section 4.1, ruling Q1).
- Census helpers (`tests/_retro_r_mig_sql.py:126-135`) only parse `REVOKE/GRANT ... ON FUNCTION`; a table REVOKE is invisible to them. 044 creates no function, so the SECURITY DEFINER census (`test_migration_037_*`, `test_retro_w1_2d`) is untouched.
- `tests/test_migration_index_predicate_immutability.py:84-106` is parametrized over `migrations/*.sql`: 044 adds one node `test_index_predicates_are_immutable[044_apple_siwa_tokens.sql]` (044 creates no index, so it passes).

### 1.7 Legal manifest constraint

- T7b (`tests/test_legal_docs_u8.py:823-851, 1039-1058`) scans every `app/services/**/*.py` string constant (docstrings skipped) for `https?://host`; every external host must be covered by the `hosts` of a manifest row whose `module` lists that file. Probe: the endpoint literals scan to `{"appleid.apple.com"}`; today's `apple` row is `{"kind": "identity_provider", "module": ["SmartCompareApp/src/components/AppleSignInButton.tsx"], "hosts": ["expo-apple-authentication"], "gate_flag": null, "personal_data": true}` and does NOT cover it. A new service module holding the URLs is therefore RED on T7b until the `apple` row lists it.
- R22 (`tests/test_legal_s78.py:898-921`) freezes every row's `kind/module/hosts/gate_flag/personal_data` against `tests/fixtures/legal_s78.json` `manifest_base` (apple entry identical to the row above) and the row-id set. `gate_flag` must stay null (`test_t7_processor_manifest_schema` allows only the seven Q10 flags). So the unit amends the `apple` row and the R22 fixture together (section 4.1); adding a new row would also break the id set and `PUBLIC_NAME_IDS`.
- Privacy policy `app/legal/privacy_policy.md:76`: "Apple: only if you use Sign in with Apple. Apple shares your email address, or a private relay address, with us." Nothing says the server keeps an Apple token. Text changes go through the legal machinery and are out of scope (Q9).

### 1.8 Guards the new code must not trip

- Pre-commit hook `.githooks/pre-commit:177-179, 213-216` refuses any added line matching `-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----`, `\bsk-[A-Za-z0-9_-]{20,}` and (step 4a) a JWT shape `eyJ[A-Za-z0-9_-]{7,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}`; `tests/test_secret_scan_static.py:69` pins that line. So no source or test may contain a PEM header with `PRIVATE KEY-----` or a literal JWT: the PEM check in code uses the prefix `-----BEGIN` only, test keys and test JWTs are generated at run time.
- `tests/test_sentry_channels_u8d_unit.py:773-918` (R8 AST pin over `app/**/*.py`): an ERROR / exception / critical log call OUTSIDE an except arm may only take constants, `type(x).__name__` or the names `user_id/comparison_id/key/label`. Every new log line is INFO or WARNING (section 2.7), which the scan ignores; none uses `exc_info`.
- `tests/_env_safety.py:108-132` `CREDENTIALS_UNSET` ("Sourced from a grep of `os.getenv("...")` across `app/` and `scripts/`; re-run that grep when adding an integration"). `APPLE_SIWA_PRIVATE_KEY` is a new credential: add it (section 3, Q8b). `test_helper_covers_the_whole_contract` only checks a superset, so adding is green.
- `tests/.pre_impl_failures.txt:79-80` already lists `tests/test_auth_interceptor.py::test_sign_in_with_social_exception` and `::test_social_login_user_insert_fails_gracefully` (the two base failures of the comm set, section 1.10).
- No test pins the OpenAPI schema of `/social-login` (`grep -i social` over `tests/test_m13_21_openapi_gated.py`, `tests/_route_introspection.py`, `tests/test_route_introspection.py`: empty), so the new optional field changes no pin.

### 1.9 Line endings

Every existing file the unit edits is `i/lf w/crlf` (`git ls-files --eol`: `CLAUDE.md`, `app/api/auth_routes.py`, `app/services/auth_service.py`, `app/legal/processors.json`, `tests/fixtures/legal_s78.json`, `tests/test_migration_043_delete_user_cascade.py`, `tests/_env_safety.py`, and the format references `migrations/038_users_consent_capture.sql`, `migrations/rollback/031_eval_runs.sql`). Use the Edit tool on existing files; write new files with CRLF like their neighbours; `git diff --stat` must show content lines only.

### 1.10 Base pass state (bounded runner, one process at a time, flag unset)

The comm set (section 7) at base, 124 files in five chunks:

```
chunk 00 (files 1-25 of comm_files.txt, test_429_contract .. test_category_selection)
  2 failed, 547 passed, 34 deselected
  [pyt] tag=b3b-base-c00 start=2026-10-17 06:34:34 end=2026-10-17 06:35:06 elapsed=32s bound=1200s status=FAIL rc=1
  FAILED tests/test_auth_interceptor.py::test_sign_in_with_social_exception
  FAILED tests/test_auth_interceptor.py::test_social_login_user_insert_fails_gracefully
    (both listed in tests/.pre_impl_failures.txt:79-80, i.e. known reds deselected by CI)
chunk 01 (files 26-50)   954 passed, 1 skipped, 21 deselected
  [pyt] tag=b3b-base-c01 start=2026-10-17 06:35:20 end=2026-10-17 06:40:20 elapsed=300s bound=1200s status=OK rc=0
chunk 02 (files 51-75)   673 passed, 10 deselected
  [pyt] tag=b3b-base-c02 start=2026-10-17 06:40:33 end=2026-10-17 06:42:42 elapsed=129s bound=1200s status=OK rc=0
chunk 03 (files 76-100)  TIMEOUT inside tests/test_precommit_hook_phase_b.py (38 nodes in about 19 min)
  [pyt] tag=b3b-base-c03 start=2026-10-17 06:42:55 end=2026-10-17 07:02:58 elapsed=1204s bound=1200s status=TIMEOUT rc=124
chunk 03b (chunk 03 minus test_precommit_hook_phase_b.py, 24 files)
  860 passed, 3 skipped, 1 xfailed, 2 errors
  [pyt] tag=b3b-base-c03b start=2026-10-17 07:03:34 end=2026-10-17 07:09:17 elapsed=343s bound=1200s status=FAIL rc=1
  ERROR tests/test_prompt_truth.py::test_truth_on_prefix_static_and_cacheable
  ERROR tests/test_prompt_truth.py::test_render_digests_match_base_except_the_fence
    (the file's own network guard caught a tiktoken download, getaddrinfo
     openaipublic.blob.core.windows.net: a cold tiktoken cache on this box;
     not in .pre_impl_failures.txt; independent of every file B3B touches)
chunk 04 (files 101-124) 1443 passed
  [pyt] tag=b3b-base-c04 start=2026-10-17 07:10:02 end=2026-10-17 07:14:38 elapsed=276s bound=1200s status=OK rc=0
tests/test_precommit_hook_phase_b.py: NOT MEASURED (the c03 TIMEOUT line above; it was
  not re-run alone because one run of it alone exceeds the budget left on this box;
  it exercises .githooks/pre-commit, which B3B does not modify)
```

Per-file base counts for the files the unit edits or pins (counted from the progress lines of the chunk logs; deselected live nodes excluded):

| file | base | role |
|---|---|---|
| `tests/test_account_deletion_u8b.py` | 10 passed | flag-OFF deletion order pins (4.2) |
| `tests/test_account_deletion.py` | 21 passed | route success / failure |
| `tests/test_account_deletion_u8b_fix_pins.py` | 10 passed | log hygiene pins |
| `tests/test_account_deletion_u8c_sentry_chain.py` | 24 passed | 500 chain |
| `tests/test_social_login_device_fingerprint.py` | 15 passed | social-login harness, flag-OFF body pins |
| `tests/test_social_login_smoke.py` | 6 passed | social-login smoke |
| `tests/test_auth_interceptor.py` | 115 passed, 2 failed (the two pre-impl reds) | sign_in_with_social |
| `tests/test_auth_error_log_hygiene.py` | 69 passed | auth log rules |
| `tests/test_consent_capture_w3_16.py` | 17 passed | social-login consent |
| `tests/test_migration_043_delete_user_cascade.py` | 51 passed | E1-E3 change here |
| `tests/test_migration_index_predicate_immutability.py` | 42 passed | +1 node for 044 |
| `tests/test_migration_037_security_definer_grants.py` | 21 passed | census, untouched |
| `tests/test_retro_w1_2b.py` / `_2c.py` / `_2d.py` | 14 / 14 / 16 passed | census, untouched |
| `tests/test_legal_docs_u8.py` | 47 passed | T7b covers the new module after step 5 |
| `tests/test_legal_s78.py` | 29 passed | E4 changes here (fixture) |
| `tests/test_legal_disclosure_s77.py` / `_u8_d3c.py` / `_u8_polish.py` | 31 / 22 / 69 passed | manifest readers |
| `tests/test_conftest_env_safety.py` | 24 passed, 1 skipped | step 7 |
| `tests/test_sentry_channels_u8d_unit.py` / `tests/test_sentry_channels_u8d.py` | 141 / 131 passed | R8 AST pin |
| `tests/test_secret_scan_static.py` | 31 passed | hook pattern pin |
| `tests/test_security_regression.py` | 104 passed | named in the brief |
| `tests/test_u3c_store_false_pin.py` / `test_prompt_fence.py` / `test_start_command.py` / `test_sqlfluff_config.py` | 31 / 61 / 8 / 11 passed | source-scanning pins |

Netguard / hermeticity per chunk: c00 `[netguard] blocked 16 attempt(s) from 12 node(s)`, `[hermeticity] sentinel checked 549 test(s)`; c01 23 from 21, 955; c02 4 from 4, 673; c03b 29 from 12, 863; c04 13 from 7, 1443 (the existing ratchet baseline; B3B adds no egress: every new Apple call goes through `httpx.MockTransport`). Logs: `<scratchpad>/b3b/base_c0*.log`; the base FAILED/ERROR set is exactly the four ids above.

## 2. Contract

### 2.1 Flag and configuration (new module `app/services/apple_siwa_service.py`)

- `apple_token_revocation_enabled() -> bool`: the 1.3 idiom over `ENABLE_APPLE_TOKEN_REVOCATION`, default `"false"`, read per call, never cached.
- `SIWA_ENV_NAMES = ("APPLE_SIWA_TEAM_ID", "APPLE_SIWA_KEY_ID", "APPLE_SIWA_PRIVATE_KEY", "APPLE_SIWA_CLIENT_ID")`, read per call by `_siwa_config()`, each `.strip()`ped. Any missing or empty -> return `None` and log once per call `logger.warning("[SIWA] config missing: %s", ",".join(missing_names))` (names only, never a value). `APPLE_SIWA_CLIENT_ID` has no default (Q4): for the native app the owner sets it to the bundle id `com.qaren.app` (`SmartCompareApp/app.json:21`).
- `_normalise_private_key(raw) -> str` accepts: (a) a PEM with real newlines (the .p8 file pasted as is); (b) a PEM whose newlines arrived as the two characters `\n` (single-line editors): if the text starts with `-----BEGIN` and holds no real newline, replace each literal `\n` with a newline; (c) the base64 of the whole .p8 file (no `-----BEGIN` prefix): `base64.b64decode(raw, validate=True)`, decoded as ASCII, which must then start with `-----BEGIN`. Anything else raises `ValueError` (caught by the caller). The code never contains the string `PRIVATE KEY-----` (1.8).

### 2.2 Client secret

`build_client_secret(config, now=None) -> str`: `now = int(_now())` when not given (`_now = time.time`, a module seam); claims exactly `{"iss": TEAM_ID, "iat": now, "exp": now + CLIENT_SECRET_TTL_SECONDS, "aud": "https://appleid.apple.com", "sub": CLIENT_ID}` with `CLIENT_SECRET_TTL_SECONDS = 300` (Apple's ceiling is 15,777,000 s, six months; a fresh 5-minute secret per call means a leaked one dies quickly); `jwt.encode(claims, <normalised PEM>, algorithm="ES256", headers={"kid": KEY_ID, "typ": None})`, header exactly `{"alg": "ES256", "kid": KEY_ID}` (Apple's documented header; Q12). Any exception from normalising or signing propagates to the caller, which logs `"[SIWA] client secret build failed: %s"` with `type(exc).__name__` and abandons the Apple step.

### 2.3 Exchange on social-login

- Model: `SocialLoginRequest` gains `authorization_code: Optional[str] = None` and a `field_validator("authorization_code", mode="before")` that returns the value when it is a `str` and `None` otherwise (Q11). No `max_length`. Effect: every body the base accepted is still accepted with the same response (a 5,000-character code, an integer, a list: all 200 at base, all 200 at head).
- Route, after the W3-3 block and before the unchanged `return result`:
  ```python
  if apple_token_revocation_enabled() and body.provider == "apple" and body.authorization_code:
      await store_apple_refresh_token(
          (result.get("user") or {}).get("id"), body.authorization_code, body.id_token
      )
  ```
  `store_apple_refresh_token` lives in `auth_service` (it owns the admin client) and NEVER raises; `result` is not read for anything else and is returned unchanged, so the response body is byte-equal in both flag states.
- `auth_service.store_apple_refresh_token(user_id, authorization_code, id_token) -> bool` (True only when a row was written), all inside one broad `try` (`except Exception as exc: logger.warning("[SIWA] store failed: %s", type(exc).__name__); return False`):
  1. `user_id` falsy -> return False (no call);
  2. `tokens = await apple_siwa_service.exchange_authorization_code(authorization_code)`; `None` -> return False;
  3. identity check: `sub` of `tokens["id_token"]` must equal `sub` of the request `id_token`, both read with `jwt.decode(t, options={"verify_signature": False})` (the request token was verified by Supabase a moment earlier; the response token came from Apple over TLS); missing / unequal / undecodable -> `logger.warning("[SIWA] exchange sub mismatch; not stored")`, return False (Q5);
  4. `await run_db(lambda: get_admin_client().table("apple_siwa_tokens").upsert({"user_id": user_id, "refresh_token": tokens["refresh_token"], "updated_at": <UTC ISO now>}, on_conflict="user_id").execute())`; return True.
- `apple_siwa_service.exchange_authorization_code(code) -> Optional[dict]`, never raises: config (`None` -> return None); client secret (2.2); one POST, no retry, to `APPLE_TOKEN_URL = "https://appleid.apple.com/auth/token"` with form fields exactly `client_id`, `client_secret`, `code`, `grant_type=authorization_code` (no `redirect_uri`: the native flow sends none; stated limit L3); client `httpx.AsyncClient(timeout=_HTTP_TIMEOUT, transport=_TRANSPORT)`, `_HTTP_TIMEOUT = 5.0`, `_TRANSPORT = None` in production. Status 200 with a JSON object holding a non-empty string `refresh_token` and a string `id_token` -> return the dict and `logger.info("[SIWA] exchange status=%d", 200)`. Any other status -> `logger.warning("[SIWA] exchange status=%d", status)`, None. 200 without the fields or with a non-JSON body -> `logger.warning("[SIWA] exchange response unusable")`, None. Exception -> `logger.warning("[SIWA] exchange failed: %s", type(exc).__name__)`, None.
- Every Apple sign-in with a code re-exchanges and upserts, so the stored token is the newest one.

### 2.4 Storage: migration 044 (+ rollback), house format

`migrations/044_apple_siwa_tokens.sql`: a header comment in the 038 / 031 style (purpose, "MERGING THIS CHANGES NOTHING IN PRODUCTION", apply order "apply 044 BEFORE flipping ENABLE_APPLE_TOKEN_REVOCATION: flag ON without the table makes every store and read fail soft, so revocation silently never happens", "service-role only: RLS on, no policy, REVOKE from PUBLIC/anon/authenticated", "rows leave with the auth user: FK to auth.users ON DELETE CASCADE", "Rollback: migrations/rollback/044_apple_siwa_tokens.sql"), then exactly:

```sql
BEGIN;

CREATE TABLE IF NOT EXISTS public.apple_siwa_tokens (
  user_id uuid PRIMARY KEY REFERENCES auth.users (id) ON DELETE CASCADE,
  refresh_token text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE public.apple_siwa_tokens ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE public.apple_siwa_tokens FROM PUBLIC, anon, authenticated;

COMMENT ON TABLE public.apple_siwa_tokens IS
  '<one or two sentences: the Apple refresh token kept only so account deletion can revoke it; written and read by the service role only; removed with the auth user>';

COMMENT ON COLUMN public.apple_siwa_tokens.refresh_token IS
  '<Apple refresh token from the authorization-code exchange; never logged; posted to appleid.apple.com/auth/revoke on account deletion>';

COMMIT;
```

No index (the primary key serves the one lookup), no policy, no function, no other table touched, no GRANT (the service role bypasses RLS and holds the default privileges). `migrations/rollback/044_apple_siwa_tokens.sql`: header "flip ENABLE_APPLE_TOKEN_REVOCATION off first; destructive: the stored tokens are lost and those users can no longer be revoked from the server", then `BEGIN; DROP TABLE IF EXISTS public.apple_siwa_tokens; COMMIT;` and nothing else. 039 stays reserved. The CLAUDE.md "Dated apply record" (CLAUDE.md:92) gains "044 (`apple_siwa_tokens`, B3-B) written, NOT applied".

Why `auth.users` and not `public.users` (Q2): the row must leave exactly when the account ends. The auth delete is the last step of `delete_user_account`; an FK to `auth.users` removes the row on that step in either users-FK branch, while an FK to `public.users` relies on branch A (live today, but the fence exists precisely because branch B was possible).

### 2.5 Revocation on account deletion

`auth_service.delete_user_account(user_id)` at head (flag ON shown; every new line is skipped when the flag is OFF):

```python
from app.services.database_service import delete_user_data_cascade
siwa_token = None
if apple_siwa_service.apple_token_revocation_enabled():
    siwa_token = await _read_apple_refresh_token(user_id)      # never raises
await delete_user_data_cascade(user_id)                         # unchanged; raises -> nothing else runs
await _purge_deleted_user_caches(user_id)                       # unchanged
if siwa_token:
    await apple_siwa_service.revoke_refresh_token(siwa_token)   # never raises
admin = get_admin_client()                                      # unchanged
admin.auth.admin.delete_user(user_id)                           # unchanged; its FK cascade removes the token row
return True
```

- `_read_apple_refresh_token(user_id) -> Optional[str]`: `await run_db(lambda: get_admin_client().table("apple_siwa_tokens").select("refresh_token").eq("user_id", user_id).limit(1).execute())`; the first row's `refresh_token` when it is a non-empty `str` (anything else, a test `MagicMock` included, counts as no token), else None; no row -> `logger.info("[SIWA] no stored token; revoke skipped")`; any exception (including `get_admin_client`'s `ValueError`) -> `logger.warning("[SIWA] token read failed: %s", type(exc).__name__)`, None. `.single()` is not used (it raises on zero rows).
- Placement (Q6): the read comes first, so the token is in memory before anything is erased; the revoke comes after the cascade (a failed cascade means the account is not deleted, so nothing is revoked) and BEFORE the auth delete (if the process dies between revoke and auth delete, the row and the auth user survive and a retry revokes again; revoke-after-auth-delete would lose the token row on the FK cascade if the revoke never ran).
- `apple_siwa_service.revoke_refresh_token(token) -> bool`, never raises: config (None -> False); client secret (built once, reused for the retry; TTL 300 s); POST to `APPLE_REVOKE_URL = "https://appleid.apple.com/auth/revoke"` with form fields exactly `client_id`, `client_secret`, `token`, `token_type_hint=refresh_token`, same client construction and 5 s timeout as 2.3. At most two attempts: the second runs only when the first raised `httpx.HTTPError` or returned 429 or a status >= 500. Status 200 -> `logger.info("[SIWA] revoke attempt=%d status=%d", n, 200)`, True. Other status -> `logger.warning("[SIWA] revoke attempt=%d status=%d", n, status)`. Exception -> `logger.warning("[SIWA] revoke attempt=%d failed: %s", n, type(exc).__name__)`. No sleep between attempts (Q6b). Returns True only on a 200. Worst case adds about 10 s to a deletion; the client's axios timeout is 120 s (`SmartCompareApp/src/services/api.ts:31`) and the route is limited to 1/minute.
- The route, its response, its 500 path and its log line are unchanged.

### 2.6 Test seams (production values in brackets)

`apple_siwa_service._TRANSPORT` [None], `apple_siwa_service._now` [`time.time`], `apple_siwa_service._HTTP_TIMEOUT` [5.0], `CLIENT_SECRET_TTL_SECONDS` [300]. Tests set the env with `monkeypatch.setenv` / `delenv` and the transport with `monkeypatch.setattr(siwa, "_TRANSPORT", httpx.MockTransport(handler))`. No test patches `httpx.AsyncClient` globally for the flag-ON rows.

### 2.7 Logging rules (all `[SIWA]` lines)

INFO or WARNING only (never error / exception / critical, never `exc_info`), templates exactly as written in 2.1-2.5, arguments only constants, ints (attempt number, HTTP status), comma-joined variable NAMES and `type(exc).__name__`. Never logged: the authorization code, the refresh token, the client secret, the private key or any line of it, either id_token or its claims, Apple's response body (`error`, `error_description`), the email, the user id.

### 2.8 Flag-OFF identity (the unit's main invariant)

With `ENABLE_APPLE_TOKEN_REVOCATION` unset / `false` / `0` / empty:
- social-login: the same `sign_in_with_social` call with the same arguments, no `get_admin_client` / `get_admin_supabase_client` call added, no `apple_siwa_tokens` access, no httpx request, the same status and byte-identical body, for every body the base accepted (with or without `authorization_code`, any type);
- deletion: the exact U8b event list `["cascade"] + ["purge"]*5 + ["auth_delete"]`, `get_admin_client` called once (after the purge, as at base), no `.table(...)` on the admin client, no httpx request, the same return value and exceptions;
- the only new work is the env read of the flag.

### 2.9 Failure table (flag ON)

| failure | sign-in result | deletion result | log |
|---|---|---|---|
| a SIWA variable missing / empty | 200, body unchanged, nothing stored | deletion completes, no revoke | `[SIWA] config missing: <NAMES>` |
| key unparseable / wrong curve | same | same | `[SIWA] client secret build failed: ValueError` / `InvalidKeyError` |
| Apple 4xx / 5xx on exchange | same | n/a | `[SIWA] exchange status=<n>` |
| exchange timeout / transport | same | n/a | `[SIWA] exchange failed: <Type>` |
| 200 without refresh_token / non-JSON | same | n/a | `[SIWA] exchange response unusable` |
| sub mismatch | same | n/a | `[SIWA] exchange sub mismatch; not stored` |
| upsert raises (044 missing, RLS, network) | same | n/a | `[SIWA] store failed: <Type>` |
| token read raises | n/a | deletion completes, no revoke | `[SIWA] token read failed: <Type>` |
| no stored token | n/a | deletion completes, no revoke | `[SIWA] no stored token; revoke skipped` |
| revoke 429 / 5xx / transport, then success | n/a | completes | two attempt lines |
| revoke fails twice / 4xx | n/a | completes (auth delete still runs) | attempt line(s) |
| cascade raises | n/a | 500 as today; no purge, no revoke, no auth delete | the existing line |
| auth delete raises after a revoke | n/a | 500 as today; the retry reads the surviving row and revokes again | existing line + attempt line |

## 3. Change list, in the order GREEN applies it

Before the first edit: byte-copy (Python `shutil.copyfile`) every existing file below into `<scratchpad>/b3b_green_before/` with its sha256; restore only from those copies.

1. NEW `app/services/apple_siwa_service.py` (2.1, 2.2, 2.3 exchange, 2.5 revoke, 2.6 seams, 2.7 logs). Imports: stdlib, `httpx`, `jwt`. Nothing from `app.services.auth_service` (avoids an import cycle: auth_service imports this module).
2. `app/services/auth_service.py`: `from app.services import apple_siwa_service`; add `store_apple_refresh_token` and `_read_apple_refresh_token` next to the deletion helpers; amend `delete_user_account` exactly as 2.5 (docstring: the U8b order plus the two gated SIWA steps). `sign_in_with_social` is NOT changed.
3. `app/api/auth_routes.py`: the model field + validator (2.3); import `apple_token_revocation_enabled` from the new module and `store_apple_refresh_token` from auth_service (add to the existing import block at `:37-58`); the gated block in `social_login` (2.3) with a W3-3-style comment ("additive, default OFF, read per call; after the 401 raise; the body returned is unchanged in both flag states").
4. NEW `migrations/044_apple_siwa_tokens.sql` and `migrations/rollback/044_apple_siwa_tokens.sql` (2.4), CRLF like their neighbours.
5. `app/legal/processors.json` row `apple`: `module` -> `["SmartCompareApp/src/components/AppleSignInButton.tsx", "app/services/apple_siwa_service.py"]`, `hosts` -> `["expo-apple-authentication", "appleid.apple.com"]`; nothing else in the file. `tests/fixtures/legal_s78.json` `manifest_base.apple`: the same two values (R22 follows the manifest; ruling needed, Q9).
6. `tests/test_migration_043_delete_user_cascade.py`: `KNOWN_USER_TABLES` gains `"apple_siwa_tokens"`; `KEEP_TABLE_COLUMNS` gains `("apple_siwa_tokens", "user_id")` with a justification of at least 40 characters, e.g. "B3-B (044): the Apple refresh-token row is read before the cascade and revoked at Apple by delete_user_account; it is removed by its FK to auth.users ON DELETE CASCADE on the auth delete, not by the cascade (ruling Q1)". The docstring of `test_fence_sees_the_12_known_user_tables` and its name keep "12" or are renamed to 13 (GREEN renames to `..._13_...` and says so in the PR; ruling Q1).
7. `tests/_env_safety.py` `CREDENTIALS_UNSET`: add `"APPLE_SIWA_PRIVATE_KEY"` under a comment "Sign in with Apple .p8 (B3-B); absence = revocation inert" (Q8b).
8. NEW tests: `tests/test_s79_b3b_apple_revoke.py` (section 5.1) and `tests/test_migration_044_apple_siwa_tokens.py` (section 5.2), written by RED, frozen for GREEN.
9. `CLAUDE.md`: the flag row (section 8.1) in a new "SESSION 79 flag (B3-B)" block after the S78-TG block (`CLAUDE.md:465-467`), the four variables under "Optional" env vars, the 044 apply-record note (2.4).

No other file. No requirements change, no client file, no `.githooks` change, no edit to `tests/.pre_impl_failures.txt`.

## 4. Existing pins

### 4.1 Pins that change (deliberately), one row each

| # | test node | asserts today | new assertion | reason |
|---|---|---|---|---|
| E1 | `tests/test_migration_043_delete_user_cascade.py::test_fence_sees_the_12_known_user_tables` (`:1076-1083`, `KNOWN_USER_TABLES` at `:145`) | the fence finds exactly the 12 tables | exactly the 13 (`+ apple_siwa_tokens`) | 044 adds a user-referencing table (1.6) |
| E2 | `::test_cascade_erases_or_keeps_every_user_referencing_table` (`:1053-1062`) via `KEEP_TABLE_COLUMNS` (`:99-106`) | no table gap | unchanged assertion; the KEEP entry of step 6 absorbs the one new gap measured in 1.6 | the row leaves on the auth delete (FK), not in the cascade (Q1) |
| E3 | `::test_keep_allowlists_are_justified_and_not_stale` | KEEP entries >= 40 chars and present in the fence | unchanged assertion; the new entry satisfies it | guard on E2's justification |
| E4 | `tests/test_legal_s78.py::test_s78_r22_manifest_categories` via `tests/fixtures/legal_s78.json` `manifest_base.apple` | apple `module` / `hosts` equal the frozen S78 values | equal the step-5 values | T7b must cover the new module (1.7) |

### 4.2 Pins that must stay green and unedited (all green at base, section 1.10)

`tests/test_account_deletion_u8b.py` (all, in particular `test_delete_order_is_cascade_then_purge_then_auth_delete`, `test_cascade_failure_skips_purge_and_auth_delete`, `test_auth_delete_failure_propagates_after_the_cascade`, `test_delete_route_keeps_rate_limit_and_auth`: every one runs with the new flag unset, so they ARE the flag-OFF deletion pins), `test_account_deletion_u8b_fix_pins.py`, `test_account_deletion_u8c_sentry_chain.py`, `test_account_deletion.py`, `test_social_login_device_fingerprint.py`, `test_social_login_smoke.py`, `test_consent_capture_w3_16.py`, `test_auth_error_log_hygiene.py`, `test_legal_docs_u8.py` (T7, T7a, T7b, T7c go from "apple row lacks the new module" to covered; they are green at base because the module does not exist yet), `test_legal_docs_u8_d3c.py`, `test_legal_docs_u8_polish.py`, `test_legal_disclosure_s77.py`, `test_sentry_channels_u8d_unit.py` (R8), `test_secret_scan_static.py`, `test_conftest_env_safety.py`, `test_migration_index_predicate_immutability.py` (one more parametrized node), `test_migration_037_security_definer_grants.py`, `test_retro_w1_2b.py`, `test_retro_w1_2c.py`, `test_retro_w1_2d.py`, `test_security_regression.py`, and the rest of the comm set.

## 5. RED tests

### 5.1 `tests/test_s79_b3b_apple_revoke.py` (new; pure ASCII; hermetic)

Harness rules: nothing the unit creates is imported at module top (import inside each body, the U8b idiom), so each RED node fails on its own assertion or import inside the body. An autouse fixture `delenv`s `ENABLE_APPLE_TOKEN_REVOCATION` and the four `APPLE_SIWA_*` names, disables the slowapi limiter (copy of `test_social_login_device_fingerprint.py:65-72`) and asserts no netguard attempt. The EC P-256 key is generated per test session with `cryptography` and serialised to PKCS#8 PEM at run time; no PEM, JWT or key-shaped literal appears in the file (1.8). The request `id_token` and Apple's response `id_token` are built at run time with `jwt.encode` (a throwaway HS256 key; only the unverified `sub` matters). Apple is a `httpx.MockTransport` handler that records `(method, url, content-type, parse_qs(body), request.extensions["timeout"])` and replies from a per-test script. Social-login is driven through `TestClient(app)` with `app.api.auth_routes.sign_in_with_social` patched to an `AsyncMock` returning an Apple success dict (shape of `SUCCESS` at `test_social_login_device_fingerprint.py:46-60`, `message "Signed in with apple"`); the admin client is a recording fake on `app.services.auth_service.get_admin_client` whose `table(name)` returns chains that record `(name, method, args, kwargs)`; deletion uses the U8b fakes (`_admin_client(events)`, the cascade and `delete_cached` patched at the importing module, `ENABLE_ASYNC_REDIS_OFFLOAD` unset). Logs are captured by patching the module loggers with a `MagicMock` and rendering every call (the U8b `_rendered` idiom) plus `caplog` at DEBUG for the whole `app` tree. Sentinels are plain words built at run time.

| # | test | assertion | at base | after GREEN |
|---|---|---|---|---|
| R1 | `test_b3b_r1_flag_reader_per_call` (param: unset, `""`, `false`, `0`, `no`, `true`, `1`, `yes`, `on`, ` TRUE `) | `apple_token_revocation_enabled()` is True exactly for the truthy four (case / space-insensitive); flipping the env after import flips the result | RED: `ModuleNotFoundError: app.services.apple_siwa_service` | 2.1 |
| R2 | `test_b3b_r2_config_requires_all_four_names` (param: each name missing, each name `"  "`) | `_siwa_config()` is None; exactly one WARNING whose rendered text is `[SIWA] config missing: <NAME>` and contains none of the three other variables' sentinel values; all four set -> the four stripped values | RED: module absent | 2.1 |
| R3 | `test_b3b_r3_private_key_forms` (param: real-newline PEM, literal `\n` PEM, base64 of the PEM, garbage, an RSA PEM) | the first three produce a client secret that `jwt.decode(secret, public_key, algorithms=["ES256"], audience="https://appleid.apple.com")` verifies; garbage -> `ValueError`, RSA -> `InvalidKeyError` from `build_client_secret` | RED: module absent | 2.1, 2.2 |
| R4 | `test_b3b_r4_client_secret_shape` | with `now=1_700_000_000`: unverified header == `{"alg": "ES256", "kid": "KEYID00000"}` exactly; claims == `{"iss": "TEAMID0000", "iat": now, "exp": now + 300, "aud": "https://appleid.apple.com", "sub": "com.example.b3b"}` exactly; `0 < exp - iat <= 15_777_000`; signature verifies with the generated public key; the signature segment decodes to 64 bytes | RED: module absent | 2.2 |
| R5 | `test_b3b_r5_exchange_request_is_exact` | `exchange_authorization_code(code)` makes exactly one request: `POST https://appleid.apple.com/auth/token`, content-type `application/x-www-form-urlencoded`, form keys exactly `{client_id, client_secret, code, grant_type}`, `grant_type == "authorization_code"`, `client_id` == the configured id, `code` == the code, `client_secret` passes R4's checks; every value of `request.extensions["timeout"]` is `5.0`; returns the parsed dict | RED: module absent | 2.3 |
| R6 | `test_b3b_r6_social_login_apple_with_code_stores_the_token` | flag ON, config set, body `{provider: apple, id_token, nonce, authorization_code}`, Apple 200 with matching `sub`: status 200; body byte-equal to the same request with the flag unset; one exchange request; admin calls exactly `[("apple_siwa_tokens", "upsert", payload, {"on_conflict": "user_id"}), (…, "execute")]` with `payload.keys() == {"user_id", "refresh_token", "updated_at"}`, `user_id == UID`, `refresh_token ==` Apple's; `updated_at` parses as an aware UTC datetime | RED: zero exchange requests, zero upserts (field ignored, flag unread) | 2.3 |
| R7 | `test_b3b_r7_no_code_no_call` (param: field absent, `null`, `""`, `123`) | flag ON, apple: zero httpx requests, zero admin `table()` calls, body byte-equal to flag OFF | PIN (green at base: nothing happens) | kept |
| R8 | `test_b3b_r8_google_never_exchanges` | flag ON, provider google WITH an `authorization_code`: zero requests, zero `table()` calls, body unchanged | PIN | kept |
| R9 | `test_b3b_r9_exchange_failure_never_fails_sign_in` (param: Apple 400 `{"error": SENTINEL}`, 500, `ConnectTimeout`, 200 without `refresh_token`, 200 text body, one SIWA name missing, garbage key, upsert raising a PostgREST `APIError` whose `details` hold a sentinel) | status 200 and body byte-equal to flag OFF; exactly the WARNING template of 2.9 for that case is logged once; no upsert except in the upsert-raises case (one attempt); no sentinel, code, refresh token, client secret, PEM line or id_token in any captured record | RED: no WARNING line exists | 2.3, 2.7 |
| R10 | `test_b3b_r10_sub_mismatch_is_not_stored` (param: other `sub`, no `sub`, undecodable Apple `id_token`) | zero upserts; one WARNING `[SIWA] exchange sub mismatch; not stored`; 200, body unchanged | RED: no exchange happens, so the WARNING is absent | 2.3 |
| R11 | `test_b3b_r11_exchange_is_single_shot_and_bounded` | Apple 500 then 200 scripted: exactly ONE request (no retry on the sign-in path); the request timeout extension values are all 5.0 | RED: zero requests | 2.3 |
| R12 | `test_b3b_r12_delete_reads_then_cascade_purge_revoke_auth_delete` | flag ON, config set, stored token T: events == `["read_token", "cascade"] + ["purge"]*5 + ["revoke", "auth_delete"]`; the revoke request: `POST https://appleid.apple.com/auth/revoke`, form keys exactly `{client_id, client_secret, token, token_type_hint}`, `token == T`, `token_type_hint == "refresh_token"`, valid client secret; returns True | RED: events lack `read_token` and `revoke` | 2.5 |
| R13 | `test_b3b_r13_delete_without_a_stored_token` | flag ON, select returns `data=[]`: events == `["read_token", "cascade"] + ["purge"]*5 + ["auth_delete"]`; zero httpx requests; one INFO `[SIWA] no stored token; revoke skipped` | RED: no `read_token` | 2.5 |
| R14 | `test_b3b_r14_revoke_retry_policy` (param: `ConnectTimeout`->200, 500->200, 429->200, 400, 200, 503->503, `ReadTimeout`->`ReadTimeout`) | attempts == 2, 2, 2, 1, 1, 2, 2 respectively; the deletion returns True and `auth_delete` runs once in every case; log lines `[SIWA] revoke attempt=<n> status=<s>` / `failed: <Type>` only | RED: zero attempts | 2.5 |
| R15 | `test_b3b_r15_token_read_failure_never_blocks` (param: `table().select().execute()` raises `APIError` with a sentinel; `get_admin_client` raises `ValueError`) | events == `["cascade"] + ["purge"]*5 + ["auth_delete"]` after a failed read; zero requests; one WARNING `[SIWA] token read failed: <Type>` without the sentinel; returns True | RED: no WARNING | 2.5 |
| R16 | `test_b3b_r16_cascade_failure_revokes_nothing` | flag ON, stored token, cascade raises: the read happened (`events[0] == "read_token"`), then no purge, no revoke request, no auth delete; the exception propagates | RED: `read_token` absent | 2.5 |
| R17 | `test_b3b_r17_auth_delete_failure_after_revoke` | flag ON, stored token, auth delete raises: exactly one revoke attempt (200) happened before it; the exception propagates | RED: zero revoke attempts | 2.5 |
| R18 | `test_b3b_r18_siwa_logs_are_type_and_status_only` | across R6, R9, R12, R14 scenarios replayed in one test: at least one `[SIWA]` record exists (control); every `[SIWA]` record is INFO or WARNING, has no `exc_info`, and its rendered message matches one of the 2.7 templates (regex list); no record of any logger contains a sentinel (code, refresh token, client secret, each PEM body line, both id_tokens, Apple's error body) | RED: the control finds no `[SIWA]` record | 2.7 |
| R19 | `test_b3b_r19_flag_off_social_login_identity` (param: unset, `false`, `0`, `""`; bodies: apple+code, apple without code, google+code, apple + a 5,000-char code, apple + `authorization_code: 123`, apple + `["x"]`) | status 200; body == the recorded base body (a literal in the test, recorded by running this PIN at base); `sign_in_with_social` awaited once with `("apple"|"google", id_token, nonce, consent=<the consent_from_fields result>)`; zero calls to `auth_service.get_admin_client` and `auth_routes.get_admin_supabase_client`; zero httpx requests (a recording `httpx.AsyncClient.send` wrapper, restored by monkeypatch, plus the netguard) | PIN (green at base) | kept: 2.8 |
| R20 | `test_b3b_r20_flag_off_delete_identity` (param: unset, `false`, `0`, `""`) | events == `["cascade"] + ["purge"]*5 + ["auth_delete"]`; `get_admin_client` called exactly once and only after the purges; zero `admin.table(...)` calls; zero httpx requests; returns True | PIN | kept: 2.8 |
| R21 | `test_b3b_r21_social_login_request_contract` | `SocialLoginRequest` still rejects `provider: "facebook"` (422) and a missing `id_token` (422); at head `SocialLoginRequest.model_validate({..., "authorization_code": 123}).authorization_code is None` and a string is kept | RED: at base the model has no `authorization_code` attribute (the second half) | 2.3 |
| R22 | `test_b3b_r22_new_module_hosts_are_in_the_apple_manifest_row` | `app/services/apple_siwa_service.py` exists; the T7b scanner (loaded by path from `tests/test_legal_docs_u8.py`, the S77 `_load` idiom) finds exactly `{"appleid.apple.com"}` in it; the manifest `apple` row lists the module and a host covering it; `gate_flag` is null | RED: module absent, row lacks it | steps 1, 5 |
| R23 | `test_b3b_r23_no_secret_shapes_in_the_unit_files` | the added files (`app/services/apple_siwa_service.py`, both 044 files, this test file and `tests/test_migration_044_apple_siwa_tokens.py`) contain no match of the four hook patterns and the hook's JWT pattern (regexes copied from `.githooks/pre-commit:178` and its `JWT_RE`, built by concatenation so the test file itself never matches) and no `@gmail.com` / phone shape | RED: the module and migration files are absent (the test asserts they exist first) | steps 1, 4 |
| R24 | `test_b3b_r24_env_safety_clears_the_private_key` | `"APPLE_SIWA_PRIVATE_KEY" in tests._env_safety.CREDENTIALS_UNSET`, and after the conftest sanitizer ran it is unset in `os.environ` unless the test set it | RED: absent from the tuple | step 7 |

PIN rows: R7, R8, R19, R20 (green at base; their docstrings say PIN). Every other row is RED at base for the reason given. The RED agent proves each reason by running the file at base through the bounded runner and pasting the per-node outcome, records R19's base bodies into the test literally, and proves satisfiability on a throwaway detached worktree with a prototype of section 3 (the prototype is discarded; GREEN writes its own).

### 5.2 `tests/test_migration_044_apple_siwa_tokens.py` (new; pure text scans, the 042 / 031 pin style, helpers from `tests._retro_r_mig_sql`)

| # | test | assertion | at base |
|---|---|---|---|
| M1 | `test_044_and_rollback_exist_exactly_once_and_039_stays_reserved` | `migrations/044_*.sql` == `["044_apple_siwa_tokens.sql"]`, the same under `rollback/`; no `039_*` | RED: absent |
| M2 | `test_044_is_one_transaction` | comment-stripped statements: first `begin`, last `commit`, exactly one of each | RED |
| M3 | `test_044_creates_exactly_the_token_table` | one `CREATE TABLE IF NOT EXISTS public.apple_siwa_tokens` whose columns are exactly `user_id uuid primary key references auth.users (id) on delete cascade`, `refresh_token text not null`, `created_at timestamptz not null default now()`, `updated_at timestamptz not null default now()` (whitespace-normalised) | RED |
| M4 | `test_044_is_service_role_only` | `ALTER TABLE public.apple_siwa_tokens ENABLE ROW LEVEL SECURITY` present; no `CREATE POLICY`; `REVOKE ALL ON TABLE public.apple_siwa_tokens FROM PUBLIC, anon, authenticated` present; no `GRANT` to anon / authenticated / PUBLIC | RED |
| M5 | `test_044_touches_nothing_else` | no `CREATE ... FUNCTION`, `DROP`, `CREATE INDEX`, `ALTER TABLE` of any other table, `UPDATE`, `DELETE`, `INSERT`; every identifier after `TABLE` is `public.apple_siwa_tokens` | RED |
| M6 | `test_044_header_states_apply_order_and_rollback` | the comment lines mention `ENABLE_APPLE_TOKEN_REVOCATION`, "before", `rollback/044_apple_siwa_tokens.sql`, "service role", `auth.users` | RED |
| M7 | `test_044_rollback_drops_only_the_table_and_says_flag_off_first` | rollback: BEGIN / COMMIT, exactly one `DROP TABLE IF EXISTS public.apple_siwa_tokens`, nothing else; its header mentions `ENABLE_APPLE_TOKEN_REVOCATION` and "off" | RED |
| M8 | `test_044_passes_the_u8b_fence_with_the_keep_entry` | `fence_report(real_forward_files())` has no gaps, `fence_user_tables(...)["apple_siwa_tokens"] == {"user_id": "id"}` and the KEEP entry exists (imports the fence functions from the 043 test module inside the body) | RED: table absent from the fence |

## 6. Mutation table (each mutant applied to a byte copy, run through the bounded runner, restored and sha-checked)

| id | mutant | killed by |
|---|---|---|
| X1 | flag value read once at import | R1 (flip after import) |
| X2 | flag default `"true"` | R19, R20 |
| X3 | flag reader drops `"on"` / adds `"enabled"` | R1 |
| X4 | `kid` header removed | R4 |
| X5 | `typ` kept (`headers={"kid": K}`) | R4 |
| X6 | TTL 15,777,001 / TTL 3600 | R4 |
| X7 | `aud` without the scheme | R4, R5 |
| X8 | `iss` and `sub` swapped | R4 |
| X9 | literal-`\n` branch removed | R3 |
| X10 | base64 branch removed | R3 |
| X11 | exchange `grant_type` missing or `refresh_token` | R5 |
| X12 | exchange posts JSON instead of a form | R5 |
| X13 | exchange retried on 500 | R11 |
| X14 | exchange timeout 30 | R5, R11 |
| X15 | exchange exception not caught | R9 |
| X16 | sub check removed | R10 |
| X17 | store for any provider | R8 |
| X18 | store when the code is `""` | R7 |
| X19 | `insert` instead of `upsert(on_conflict="user_id")` | R6 |
| X20 | route returns a modified body (adds a key) | R6, R9 |
| X21 | store raises through the route | R9 (upsert-raises case) |
| X22 | read moved after the cascade | R12, R16 |
| X23 | revoke moved after the auth delete | R12, R17 |
| X24 | revoke moved before the cascade | R12, R16 |
| X25 | no retry | R14 |
| X26 | retry on 400 | R14 |
| X27 | three attempts | R14 |
| X28 | revoke exception propagates | R14 (`ReadTimeout` twice), R15 |
| X29 | `token_type_hint` missing / `access_token` | R12 |
| X30 | a SIWA line logs the token or `str(exc)` | R9, R18 |
| X31 | a SIWA line at ERROR / with `exc_info=True` | R18 (and `test_sentry_channels_u8d_unit` R8 when outside an except arm) |
| X32 | the read is not gated by the flag | R20 |
| X33 | the store is not gated by the flag | R19 |
| X34 | `authorization_code` declared with `max_length=1024` | R19 (5,000-char body) |
| X35 | the before-validator removed (`Optional[str]` alone) | R19 (`123` / `["x"]` bodies -> 422), R21 |
| X36 | 044 FK to `public.users` / without `ON DELETE CASCADE` | M3 |
| X37 | 044 adds a policy for `authenticated` | M4 |
| X38 | 044 REVOKE removed | M4 |
| X39 | KEEP entry removed from the 043 test | E2 (`test_cascade_erases_or_keeps_every_user_referencing_table`), M8 |
| X40 | apple manifest row loses the new module | `test_legal_docs_u8.py::test_t7b_external_hosts_and_clients_map_to_manifest`, R22 |
| X41 | `APPLE_SIWA_PRIVATE_KEY` dropped from `CREDENTIALS_UNSET` | R24 |

## 7. Comm set and gates for GREEN (cheapest first; every pytest through the bounded runner, one process at a time)

1. Syntax / lint on every changed `.py`: `<venv python> -m py_compile` and `-m ruff check --select E9,F63,F7,F82 --no-cache`. JSON: `json.loads` of `processors.json` and `legal_s78.json`. `git diff --stat` content lines only (CRLF kept).
2. Unit: `tests/test_s79_b3b_apple_revoke.py`, then `tests/test_migration_044_apple_siwa_tokens.py` (bound 600 each) -> all pass.
3. Deliberate-change pins (bound 600 each): `tests/test_migration_043_delete_user_cascade.py`, `tests/test_legal_s78.py`, `tests/test_legal_docs_u8.py`, `tests/test_conftest_env_safety.py`.
4. Flag-ON smoke of the existing deletion and social-login files (information, not a gate; the flag-OFF state is the gate): run `tests/test_account_deletion_u8b.py tests/test_social_login_device_fingerprint.py tests/test_social_login_smoke.py` once with `ENABLE_APPLE_TOKEN_REVOCATION=true` exported and no SIWA variables. Expected all green: the u8b fakes return a `MagicMock` from the `apple_siwa_tokens` select, which is not a `str`, so the read yields no token (`probe_ext.out`: the chained `MagicMock` value is not a `str`) and the event order is unchanged; the social-login files send no `authorization_code`. Paste the outcome either way.
5. Comm set, base vs head, `comm -13` of the sorted FAILED node ids must be empty. The set = the module-reference set for `auth_routes` / `auth_service` UNION the source-scanning pins (`test_model_config.py`, `test_model_config_enforced.py`, `test_prompt_fence.py`, `test_u3c_store_false_pin.py`, `test_start_command.py`, `test_migration_index_predicate_immutability.py`, `test_openai_key_log_hygiene_s69.py`, `test_sentry_channels_u8d_unit.py`) UNION every test that reads or globs `app/` by path UNION every test that globs `migrations/` UNION every reader of `processors.json` UNION `test_security_regression.py`, `test_conftest_env_safety.py`, `test_hermeticity_pins.py`, `test_secret_scan_static.py`, `test_precommit_hook_phase_b.py`, `test_retro_w1_2c.py` and the auth files (`test_auth_*`, `test_social_login_*`, `test_account_deletion*`): 124 files at base, listed in `<scratchpad>/b3b/comm_files.txt` with the reason per file in `comm_set.tsv` (computed by `comm_set.py`). GREEN re-runs `comm_set.py` at HEAD and adds the two new test files (126). Chunks of at most 25 files, bound 1200 each. `test_precommit_hook_phase_b.py` is slow (section 1.10: about 30 s per node on this box, it timed out a 25-file chunk): run it in a gate of its own, split as the S73 note says (`-k "not dash"` / `-k dash`), bound 1800, or record it NOT MEASURED with its `[pyt]` lines; the base FAILED/ERROR set to diff against is the four ids of 1.10.
6. Full-suite CI is the final arbiter for the `app.main` import path (one new import in `auth_routes`).
7. Personal-data and secret sweep of `git diff b965c63b` (Python, in memory, counts only): no added line matches the hook patterns, a `@gmail.com` address or a phone shape; the real Team ID / Key ID appear nowhere.

## 8. CLAUDE.md row and owner steps

### 8.1 The flag row (GREEN writes it; wording may be tightened, content may not)

- `ENABLE_APPLE_TOKEN_REVOCATION` (B3-B, `app/services/apple_siwa_service.py::apple_token_revocation_enabled`, read PER CALL; default OFF) + `APPLE_SIWA_TEAM_ID`, `APPLE_SIWA_KEY_ID`, `APPLE_SIWA_PRIVATE_KEY` (the .p8: PEM as is, PEM with literal `\n`, or base64 of the file), `APPLE_SIWA_CLIENT_ID` (`com.qaren.app`). **Effect ON:** an Apple sign-in that carries `authorization_code` (client B3-A, build 1.0.0 (3) and later) exchanges it at `appleid.apple.com/auth/token` with a 5-minute ES256 client secret and upserts the Apple refresh token into `public.apple_siwa_tokens` (migration 044, service-role only); account deletion reads that token first, runs the unchanged cascade and cache purge, posts it to `appleid.apple.com/auth/revoke` (two attempts at most, the second only after a transport error, 429 or 5xx), then runs the unchanged auth delete, whose FK cascade removes the row. Every Apple failure is logged at WARNING by type or HTTP status and never fails the sign-in or the deletion. **Flag OFF:** byte-identical (no new call, no table read or write, same bodies; pinned by R19 / R20 and the U8b order pin). **HARD PRECONDITIONS:** migration 044 applied; the four variables set on `web`. **Stated limits:** accounts that signed in with Apple before B3-A + this flag hold no token and cannot be revoked server-side (TN3194 fallback: the user removes the app under Settings > Apple ID > Sign in with Apple); a user who never signs in again after the flip has no token; Apple's acceptance of the client secret and the revoke semantics cannot be tested offline. **Canary:** the first Apple sign-in after the flip logs `[SIWA] exchange status=200` (no `store failed`); the first deletion of an Apple account logs `[SIWA] revoke attempt=1 status=200`, and the owner's test Apple ID no longer lists MYEZ under Sign in with Apple. **Rollback:** unset the flag (the table can stay; dropping it is `migrations/rollback/044_apple_siwa_tokens.sql`, flag off first).

### 8.2 Owner steps (in this order)

1. Apple Developer > Certificates, Identifiers & Profiles > Keys > "+" > name it, tick "Sign in with Apple" > Configure > Primary App ID `com.qaren.app` > Save > Continue > Register.
2. Download the `.p8` once (Apple never offers it again); note the Key ID shown on the key page and the Team ID (Membership details). Keep the file out of the repo and out of chat.
3. Apply migration 044 in the Supabase SQL editor (paste `migrations/044_apple_siwa_tokens.sql`), then check `SELECT relrowsecurity FROM pg_class WHERE oid = 'public.apple_siwa_tokens'::regclass;` = true and `SELECT has_table_privilege('authenticated', 'public.apple_siwa_tokens', 'SELECT');` = false.
4. Railway `web` service: set `APPLE_SIWA_TEAM_ID`, `APPLE_SIWA_KEY_ID`, `APPLE_SIWA_CLIENT_ID=com.qaren.app`, and `APPLE_SIWA_PRIVATE_KEY` (paste the .p8 text as a multi-line value, or its base64: `base64 -w0 AuthKey_<KEYID>.p8`). Never echo them in a terminal that is recorded.
5. After build 1.0.0 (3) (B3-A) is the build users sign in with: set `ENABLE_APPLE_TOKEN_REVOCATION=true`, then run the canary (8.1) with a test Apple ID: sign in with Apple, check the log line, delete the account, check the log line and Settings.

## 9. Stated limits

- L1 Existing Apple accounts: no token until they sign in again with a B3-A build while the flag is ON; their deletion skips the revoke (logged). The TN3194 route (privacy-policy instruction to revoke by hand) is the fallback for them and is a legal-text question (Q9).
- L2 Users who stay signed in (session refresh) never produce a new code, so L1 lasts as long as their session.
- L3 Offline only: no test reaches Apple. The exchange form (no `redirect_uri` for the native flow), the dropped `typ` header, the 200-on-revoke and the effect on the Settings list are taken from Apple's documentation and verified only by the canary.
- L4 The refresh token is stored in plain text in a service-role-only table (database encryption at rest only). Using it requires our .p8; app-level encryption is out of scope.
- L5 The integrity check compares unverified `sub` claims; it stops a code from another Apple ID being stored under this account, not a compromised device.
- L6 A deletion of an Apple account adds up to about 10 s (two 5 s attempts) when Apple is slow; the client timeout is 120 s.
- L7 If the auth delete fails after a successful revoke, the account survives with a revoked Apple link until the retry; the user signs in with Apple again only by re-authorising.
- L8 The `apple` manifest row now names a server module; privacy-policy wording about the stored token is unchanged (Q9).

## 10. Out of scope

Google token revocation on the server (the client calls `revokeAccess()`, audit P9); any client code (unit B3-A: sending `authorization_code`, re-auth flows); the Services ID / web flow; Apple server-to-server notifications (`consent-revoked`, `account-delete`) endpoint; backfilling tokens for existing users; encrypting the token at the application level; privacy-policy and ToS text; changes to the cascade function (`delete_user_cascade`).

## 11. Open questions for the orchestrator

- Q1 (fence, binding before RED): (A, recommended) keep the cascade untouched, FK to `auth.users ON DELETE CASCADE`, and record the table in the 043 fence as KEEP (`KNOWN_USER_TABLES` 12 -> 13, one KEEP entry, the "12" test renamed); or (B) 044 redefines `delete_user_cascade` to add `DELETE FROM public.apple_siwa_tokens WHERE user_id = target_user_id` (needs the 043 guard / assert / REVOKE machinery, re-touches the SECURITY DEFINER census, and couples the rollback: dropping the table before restoring the 043 body would make every deletion fail). A is smaller and its rollback is independent.
- Q2: FK target `auth.users` (recommended, branch-independent) or `public.users` (the 011 / 014 / 028 house pattern, relies on branch A).
- Q3: accept all three key forms (recommended) or PEM only.
- Q4: `APPLE_SIWA_CLIENT_ID` required (recommended, explicit) or defaulted to `com.qaren.app`.
- Q5: keep the `sub` integrity check (recommended) or store whatever Apple returns.
- Q6: revoke before the auth delete (recommended, crash-safe) or after it. Q6b: no sleep between the two attempts (recommended; the route is already slow-path).
- Q7: exchange inline with a 5 s bound (recommended; inside the 25 s client deadline, testable) or through `fire_and_forget`.
- Q8: PyJWT and cryptography are transitive pins (via supabase-auth); app code now imports `jwt` directly. Leave `requirements.in` as is (this unit may not edit it) or add `pyjwt[crypto]` there in a follow-up. Q8b: add `APPLE_SIWA_PRIVATE_KEY` to `CREDENTIALS_UNSET` (recommended, the file's own instruction).
- Q9: the processors.json `apple` row + the R22 fixture change in this unit (recommended; T7b forces it). Whether the privacy policy should say that a token is kept for revocation, and whether to add the TN3194 manual-revocation sentence for pre-B3 accounts, is an owner / counsel call through the legal machinery.
- Q10: confirm with B3-A that the body key is exactly `authorization_code` (snake_case like `id_token`), sent only for Apple and only when the native result has a non-null `authorizationCode`.
- Q11: the before-validator that maps a non-string `authorization_code` to None (recommended: keeps every base-accepted body accepted) or plain `Optional[str]` (an integer body would become 422 with the flag OFF).
- Q12: drop the `typ` header to match Apple's documented header (recommended) or keep PyJWT's default `typ: JWT`.
