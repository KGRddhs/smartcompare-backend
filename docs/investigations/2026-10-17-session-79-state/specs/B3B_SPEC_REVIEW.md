# B3B spec review (adversarial): Sign in with Apple token revocation

- Spec under review: `.qa-s79/B3B_APPLE_REVOKE_UNIT_SPEC.md`, sha256 `9a49e17cc306a84c1a78291106d89c24e06ad65c715ea4927da33e290090978e` (re-hashed at the start of the review, equal to the brief).
- Worktree `sc-s79-b3revoke` at main `b965c63b`; `git status --short` empty before and after every probe (all probes ran from `<scratchpad>/b3b_review/probes/`; nothing was written in the worktree except this file, under the gitignored `.qa-s79/`).
- Reviewer budget: 07:17:45 -> about 07:50 AST. Probes and their `.out` files: `<scratchpad>/b3b_review/probes/` (p1 timeout, p2/p3 PyJWT key forms, p4 fence, p5 exp, sql/ lint). Running notes: `<scratchpad>/b3b_review/notes.txt`.
- No personal data, no credential, no network: every key and token below was generated in-process.

## 0. Verdict

**APPROVE_WITH_RULINGS.** The spec is measured with care and almost every pointer re-measured equal at `b965c63b`. Three items are blocking because they would make RED rows wrong or vacuous (section 4: B1 the flag-OFF / no-op PIN rows cannot kill the store mutants they claim; B2 R4 cannot verify its own token; B3 the "5 s bound" is not a bound and the rows that claim to prove it cannot). One operational ruling decides whether the change helps the build-3 review at all (R-OPS: the flag must be ON before build 3 is submitted, not after).

## 1. Claims re-measured and CONFIRMED (file:line at b965c63b)

| spec claim | re-measurement |
|---|---|
| 1.1 `SocialLoginRequest` `auth_routes.py:297-304`, no `model_config` | `:297-303` (six fields, no config); the AttributionRequest above it has `extra: ignore`, this one does not; extra keys are dropped (spec probe `probe_typ_pydantic.out`, re-read) |
| 1.1 route `:1147-1162`, W3-3 block after the 401 raise | `:1147-1162` exactly: consent -> `sign_in_with_social` -> 400/401 raises -> W3-3 -> `return result` |
| 1.1 `sign_in_with_social` `auth_service.py:783-863`, sync Supabase calls, broad except | confirmed (`:783`, `sign_in_with_id_token` at `:812`, `_categorize_auth_error` at `:863`) |
| 1.1 `get_admin_client` `:192-205` raises ValueError | confirmed |
| 1.1 client `SOCIAL_LOGIN_TIMEOUT_MS = 25000` | `fetchWithDeadline.ts:47` confirmed; deletion goes through `api.delete` (`EditProfileScreen.tsx:139`) on the 120 s axios default (`api.ts:31`) |
| 1.1 `authorizationCode: string \| null` | clone `expo-apple-authentication/build/AppleAuthentication.types.d.ts:150` confirmed |
| 1.2 deletion order cascade -> 5 purges -> auth delete | `auth_service.py:1008-1023` confirmed; the ONLY server deletion path (`grep delete_user_account\|delete_user(` over `app/ scripts/`: one route caller `auth_routes.py:1173`, one `admin.auth.admin.delete_user` at `:1022`) |
| 1.2 auth delete is a hard delete, so an FK cascade fires | pinned `supabase_auth 2.31.0` `_sync/gotrue_admin_api.py:184` `delete_user(self, id, should_soft_delete=False)` |
| 1.3 flag idiom | `auth_service.py:596`, `auth_routes.py:384` confirmed |
| 1.4 pins | `requirements.txt:33` cryptography 50.0.0 (via pyjwt), `:66` httpx 0.28.1, `:123` pyjwt 2.15.1; `requirements.in` names neither |
| 1.4 PyJWT behaviour | probe p2/p3 on the pinned venv: `headers={"kid":K,"typ":None}` -> header exactly `{"alg":"ES256","kid":K}`; signature 64 bytes; literal-`\n` PEM -> `ValueError`; garbage and empty -> `ValueError`; RSA PEM -> `InvalidKeyError` (NOT a ValueError subclass); `jwt.decode(..., verify_signature False)` of garbage -> `DecodeError` |
| 1.5 no PEM / base64 secret in app/; `load_dotenv(override=True)` | `app/main.py:11` confirmed |
| 1.6 fence: 12 -> 13 tables, one new gap, KEEP closes it, `refresh_token` not personal | independent probe p4 (real fence functions loaded by path, 044 appended in memory): base gaps `[]`; head without KEEP `['apple_siwa_tokens.user_id not deleted, not nulled, not KEEP-listed']`; with KEEP `[]`; 13 tables == KNOWN + 1; `_classify(refresh_token)` None. `_REFS_USERS` (`:383`) matches `REFERENCES auth.users (id)` |
| 1.6 `010_enable_rls.sql:17-18`, `031_eval_runs.sql:79-82` no-policy posture | confirmed |
| 1.7 T7b / R22 / apple row | `test_legal_docs_u8.py:823-851, 1039-1058`; `test_legal_s78.py:898-921`; apple row `{"kind":"identity_provider","module":["SmartCompareApp/src/components/AppleSignInButton.tsx"],"hosts":["expo-apple-authentication"],"gate_flag":null,...}`; T7c (`:1061-1073`) still passes with the amended row (the SmartCompareApp module keeps the needle); T7 (`:975-977`) requires every module path to exist |
| 1.8 hook patterns, `test_secret_scan_static.py:69` | `.githooks/pre-commit:177-178` (step 4 grep), `JWT_RE` / `CREDURL_RE` at `:189-190`, the backstop grep at `:213-214`; confirmed |
| 1.8 R8 AST pin scans ERROR levels only | `test_sentry_channels_u8d_unit.py:776` `_ERROR_LEVELS = {"error","exception","critical"}` |
| 1.8 `.pre_impl_failures.txt:79-80` | confirmed |
| 1.8 "no test pins the OpenAPI of /social-login" | holds, but the measurement was incomplete: `tests/fixtures/s71_u13_flag_off_baseline.json:1466` DOES contain the `SocialLoginRequest` component; `test_s71_u13_compare_auth_required.py:948-996` (T23) compares only the `$ref` closure of the ten paid routes, so the new property cannot redden it |
| 1.10 base counts | `[pyt] tag=b3b-rev-base1 start=2026-10-17 07:35:47 end=2026-10-17 07:36:07 elapsed=20s bound=600s status=OK rc=0`: `123 passed` = u8b 10, 043 51, legal_s78 29, sqlfluff_config 11, domain_s76 7, social fingerprint 15 (the spec's per-file numbers); `[netguard] blocked 0 attempt(s) from 0 node(s)`, `[hermeticity] sentinel checked 123 test(s)` |
| 2.4 the 044 / rollback text passes the repo linter | not claimed by the spec but measured: the spec's exact DDL with the comment placeholders filled, `sqlfluff 4.3.0 lint --config <worktree>/.sqlfluff` -> rc 0 for both files; positive control (lower-case keywords) rc 1 (CP01). `tests/test_sqlfluff_config.py::test_sqlfluff_lints_the_migration_corpus_clean` lints all of `migrations/` and is NOT skipped on this box (sqlfluff installed), so it is a live gate for 044 |
| Q10 field name | B3-A spec (`sc-s79-b3client/.qa-s79/B3A_CLIENT_UNIT_SPEC.md:202-203`, rows R48-R50): `authorization_code`, apple only, only a non-empty string; absent / null / '' keep today's bytes. Resolved |

## 2. Claims REFUTED

1. **"`_HTTP_TIMEOUT = 5.0`" as a bound (2.3, Q7 "inside the 25 s client deadline, testable"; L6 "worst case adds about 10 s ... two 5 s attempts").** `httpx.Timeout(5.0)` is four PER-PHASE timeouts (connect, write, read, pool), and the read timeout applies to each socket read, so one attempt can last about 15 s (connect + write + read phases) and a slow-drip response longer still; two revoke attempts can approach 30 s or more. The rows that claim to pin it cannot see it either: probe p1, `httpx.AsyncClient(timeout=0.2, transport=httpx.MockTransport(handler))` with a handler that sleeps 1.5 s returns `200` after `1.51 s` (`MockTransport` enforces no timeout). R5 / R11 / X14 pin only the configured value in `request.extensions["timeout"]`, never elapsed time.
2. **Mutation table: X33 "store not gated by the flag" killed by R19; X17 "store for any provider" killed by R8; X18 "store when the code is ''" killed by R7.** By the spec's own contract (2.3 step 2, 2.1) the store's first outbound or DB action is behind `_siwa_config()`, and the autouse fixture `delenv`s all four `APPLE_SIWA_*` names. With no config, each of these mutants returns before any httpx request and before any `get_admin_client` call, so every assertion of R7 / R8 / R19 (zero requests, zero `table()` calls, same body) stays green: the three mutants survive. (X32 IS killed by R20, because the read reaches `get_admin_client` before any config check.)
3. **R4 "with `now=1_700_000_000` ... signature verifies with the generated public key".** Probe p5: `jwt.decode(token, pub, algorithms=["ES256"], audience="https://appleid.apple.com")` on that token raises `ExpiredSignatureError` (exp = 2023-11-14 + 300 s). A correct implementation would fail R4 forever. It verifies with `options={"verify_exp": False}` (still `InvalidSignatureError` with a wrong key, measured).
4. **8.2 step 5 "After build 1.0.0 (3) (B3-A) is the build users sign in with: set `ENABLE_APPLE_TOKEN_REVOCATION=true`".** Build 3 is the build App Review tests. With that order the reviewer signs in with Apple on build 3 while the flag is OFF, nothing is stored, and an account deletion during review revokes nothing: the unit would not help the very review it exists for. The flag is harmless with build-2 clients (they send no code, R7), so it can and should be ON before build 3 is submitted.
5. **The comm set "every file the unit's edits can affect".** CLAUDE.md is an edited file, but `comm_set.py` has no "reads CLAUDE.md" rule. Of the 34 test files that mention CLAUDE.md, 22 are outside the set and exactly one opens it: `tests/test_behavior_dimension_translation.py:226-233` (`test_every_emitted_scoring_method_is_documented` reads every CLAUDE.md line containing both `scoring_method` and `enum`). Low risk (the new row will not contain both words), but it belongs in the set.

## 3. Missing test rows (each with the mutant it kills)

| new id | row | kills |
|---|---|---|
| R7/R8/R19/R20 amendment (B1) | set all four `APPLE_SIWA_*` with a run-time key and replace `httpx.AsyncClient.send` with a recorder that returns a canned `httpx.Response(599)` and never calls the original (works at base: env + httpx only, no import of the new module); assert zero recorded sends AND zero `[SIWA]` records AND no new WARNING | X17, X18, X33 (and X2 on the sign-in side) |
| R25 | flag ON, config set, `sign_in_with_social` returns `success False` (401 path) and `code TERMS_ACCEPTANCE_REQUIRED` (400 path), body carries a code: status/body unchanged, zero exchange requests, zero `table()` calls | store moved above the success / consent checks |
| R26 | `store_apple_refresh_token(None or "", code, id_token)` direct: returns False, zero requests, zero admin calls | the falsy-user-id guard removed |
| R27 (if B3 adopted) | exchange: async handler awaiting `asyncio.sleep(30)`, total-bound seam patched to 0.2 s: returns None within 1 s, one WARNING `[SIWA] exchange failed: TimeoutError`, sign-in 200 body unchanged; revoke: same per attempt, two attempts, deletion completes | total bound removed / per-phase only |
| R28 | two exchanges (or revokes) with `_now` advanced by 301 s: the two `client_secret`s carry different `iat` / `exp` (no secret reused past its TTL) | a "cache the client secret" optimisation, which would make every Apple call after the first 5 minutes fail with `invalid_client` |
| R6 amendment | Apple's scripted 200 carries `access_token`, `refresh_token`, `id_token` with three DISTINCT run-time values; assert the stored value is the refresh token | stores the access token / the id_token |
| R18 amendment | the sentinel list also holds the user id and the email of the mocked sign-in (2.7 says both are never logged) | a `[SIWA]` line carrying the user id |
| R29 | `jwt.algorithms.has_crypto is True`; `requirements.txt` pins `pyjwt==` and `cryptography==` lines (regex) | a lock recompile that drops the transitive pins (Q8) turning every exchange into a logged `NotImplementedError` |
| R3 param | the base64 form wrapped at 76 columns (GNU `base64` default) and the PEM with its newlines replaced by spaces: both build a valid secret (p3: wrapped base64 + `validate=True` -> `binascii.Error`; whitespace-stripped first -> decodes to `-----BEGIN`; space-joined PEM is accepted by cryptography as is) | base64 decode without whitespace stripping |
| R13 param | the select returns a row whose `refresh_token` is `""` / `None`: no revoke request, the INFO `no stored token` line | revoke posted with an empty token |
| M9 | `tests/test_sqlfluff_config.py::test_sqlfluff_lints_the_migration_corpus_clean` named in gate 3 (it lints 044 and its rollback; measured green for the spec's text) | a 044 that breaks CP01 / LT05 |

Fakes note for R12-R17: the U8b `_admin_client(events)` (`test_account_deletion_u8b.py:69-80`) is a bare MagicMock that records only `auth_delete`; RED needs its own admin fake whose `table("apple_siwa_tokens").select(...).eq(...).limit(1).execute()` appends `read_token` and returns `data=[{"refresh_token": T}]` (or `[]`).

## 4. Blocking items (would make RED tests wrong or vacuous)

- **B1** R7, R8, R19 (and R20 for symmetry) as written cannot kill X17 / X18 / X33 (section 2.2). Ruling RV-1 fixes their content before RED writes them.
- **B2** R4 (and R3 if it verifies a fixed-`now` token) must verify with `options={"verify_exp": False}` or with `now = int(time.time())`; as written R4 is RED at head forever (probe p5).
- **B3** the exchange / revoke "bound": decide RV-2 before RED, because it changes R5 / R11 / R14 and adds R27; without it the spec's latency promise to the 25 s client deadline is unpinned and false in the worst case (section 2.1).

## 5. Proposed rulings

- **RV-1 (B1, binding for RED):** every no-op / flag-OFF PIN row (R7, R8, R19, R20) runs with all four SIWA variables set (a key generated in the test, synthetic ids) and a base-safe recorder replacing `httpx.AsyncClient.send` (returns a canned response, never reaches the network); each asserts zero recorded sends, zero admin `table()` calls and zero `[SIWA]` records. Fix the mutation table: X17 -> R8, X18 -> R7, X33 -> R19, each under this setup. *Why:* by contract the config check precedes every observable action, so without config the gates are untested.
- **RV-2 (B3):** inline exchange (Q7 stays inline: deterministic and testable) but each Apple call runs under a TOTAL bound, `asyncio.wait_for(..., _CALL_DEADLINE)` with `_CALL_DEADLINE = 6.0` (a module seam), keeping `httpx` `timeout=5.0` inside it; a `TimeoutError` from the bound is logged as `exchange failed: TimeoutError` / `revoke attempt=n failed: TimeoutError` and, for the revoke, counts as retryable like an `httpx.HTTPError`. Add R27; restate L6 as "at most about 12 s (two 6 s attempts)" and the sign-in cost as "at most about 6 s". *Why:* per-phase timeouts and MockTransport make the current 5 s promise unprovable and false; the client gives social-login 25 s in total and Supabase's sync sign-in already spends part of it on the event loop.
- **RV-3 (B2):** R4 verifies the signature with `options={"verify_exp": False}` and separately asserts `exp - iat == 300`; R3 uses the real clock. *Why:* probe p5.
- **RV-4 (operations, App Review):** rewrite 8.2: steps 1-4 (key, .p8, apply 044, four variables) and then the flag flip happen BEFORE build 3 is submitted (the flag is a no-op for build-2 clients, R7); then the canary runs on the TestFlight install of build 3 with a test Apple ID: sign in with Apple -> `[SIWA] exchange status=200` and no `store failed`; delete the account -> `[SIWA] revoke attempt=1 status=200`; Settings > Apple ID > Sign in with Apple no longer lists MYEZ; signing in with Apple again shows Apple's name / email sheet again (the TN3194 tell that the link was cut). Only then submit. *Why:* section 2.4; the reviewer's own Apple deletion is the one that matters.
- **RV-5:** add one positive INFO line after a successful upsert, `[SIWA] stored`, (no ids) to the 2.7 template list and R6 / R18, so the canary reads a presence, not an absence. *Why:* today the only success evidence is the exchange line plus a missing failure line.
- **RV-6 (044 privileges):** add to the owner postcheck `SELECT has_table_privilege('service_role','public.apple_siwa_tokens','INSERT'), has_table_privilege('service_role','public.apple_siwa_tokens','SELECT'), has_table_privilege('anon','public.apple_siwa_tokens','SELECT');` = true, true, false. Orchestrator's choice whether 044 also carries an explicit `GRANT SELECT, INSERT, UPDATE ON TABLE public.apple_siwa_tokens TO service_role;` (the 037 precedent: Supabase grants come from explicit default privileges, and 037 re-granted service_role explicitly); if adopted, M4 / M5 change from "no GRANT" to "exactly one GRANT, to service_role". *Why:* the spec's "the service role holds the default privileges" is unmeasured, and a missing privilege fails soft: every store logs `store failed: APIError` and revocation silently never happens.
- **RV-7 (comm set):** add `tests/test_behavior_dimension_translation.py` and a "reads CLAUDE.md" rule to `comm_set.py` (GREEN re-runs it at HEAD); name `test_sqlfluff_config.py` and `test_domain_s76.py` in gate 3 as live gates for the new files. *Why:* section 2.5; sqlfluff is installed and lints 044; `test_domain_s76.py:35-36,128-132` T5 fails on any `qaren.app` under `app/` except the exact identifier `com.qaren.app` (`KEEP_IDENTIFIER = \bcom\.qaren\.app\b`), so the new module's comments may name the bundle id only in that exact form.
- **RV-8 (Q8):** keep the unit off the requirements files (the harness forbids the lock edit, and a `.in` edit without a recompile reddens CI's "Lock is current"), add R29 now, and open the `pyjwt[crypto]` declaration as a follow-up. *Why:* app code now imports `jwt` directly while the pin exists only "via supabase-auth".
- **RV-9 (Q3 detail):** the base64 branch strips all whitespace before `b64decode(..., validate=True)`; R3 gains the wrapped and space-joined params. The owner step offers the Windows form too (`[Convert]::ToBase64String([IO.File]::ReadAllBytes('AuthKey_<KEYID>.p8'))` in PowerShell, or Git Bash `base64 -w0`). *Why:* probe p3.
- **RV-10 (test hygiene for the CI secret scan):** no string literal in the new test file is assigned to a name containing `token`, `secret` or `key` unless it is built at run time or is a low-entropy word; RED pastes a local gitleaks run if the binary is present, else states it absent. *Why:* the CI `secret-scan` job fails on any gitleaks finding and its default `generic-api-key` rule keys on those names; R23 covers only the hook's regexes.
- **RV-11 (stated limits to add):** (a) the OpenAPI schema gains the optional `authorization_code` property in both flag states (an unflagged schema change; `/docs` is off in production, T23 unaffected); (b) a rollback to flag OFF while rows exist: later deletions skip the revoke and the FK cascade then drops those rows, so the links stay at Apple for those users; (c) development clients with another bundle id (Expo Go `host.exp.Exponent`) produce codes the exchange rejects (`exchange status=400`), harmless; (d) TN3194 step 3 (the credential-revoked server notification) stays out of scope.
- **RV-12 (re-authentication at deletion, orchestrator's call, not this unit):** the audit's own P1 fix (`audit_findings_for_b3.json`, P1 "fix") is re-authenticating with Apple in `handleDeleteAccount` and sending a fresh code in the DELETE body. The spec's store-at-sign-in design covers every account that signs in with Apple on build 3+ while the flag is ON, which before public release is every real user; L1 / L2 (TestFlight testers who signed in earlier and never sign in again) remain. A follow-up B3-C (backend: `DELETE /auth/account` accepts an optional `authorization_code`, exchanges and revokes inline when no row exists; client: B3-A2 re-auth) closes them; not required for build 3 if RV-4 holds.
- **Q1 -> A** (cascade untouched, FK to `auth.users ON DELETE CASCADE`, KEEP entry, rename the 12-test to 13): measured equal by probe p4; B would re-open the SECURITY DEFINER machinery for nothing.
- **Q2 -> auth.users.** Branch-independent; the RI cascade runs as the referencing table's owner and bypasses RLS, so GoTrue's delete removes the row.
- **Q3 -> all three forms** (plus RV-9).
- **Q4 -> required, no default.** An explicit value is checkable in the canary; a default hides a misconfiguration.
- **Q5 -> keep the `sub` check.** It is the only thing tying the stored token to the signed-in account.
- **Q6 -> revoke after the cascade, before the auth delete; Q6b -> no sleep.** Crash-safe ordering as argued in 2.5.
- **Q7 -> inline with RV-2's total bound.** Not `fire_and_forget`: testability and the 5-minute code life favour inline once the bound is real.
- **Q8 -> RV-8.  Q8b -> add `APPLE_SIWA_PRIVATE_KEY`** (the file's own instruction; `test_helper_covers_the_whole_contract` checks a superset).
- **Q9 -> amend the `apple` row and the R22 fixture together in this unit** (a new row would break the R22 id set and `PUBLIC_NAME_IDS`); no policy text in this unit. Owner / counsel item for the next legal change: one sentence that MYEZ keeps a token Apple issues so it can end the Apple link when the account is deleted (`privacy_policy.md:23` today says only that the sign-in method is recorded). App Privacy needs no change: `UserID` is already declared (`docs/privacy-data-inventory.md:36`).
- **Q10 -> resolved** by the B3-A spec (section 1).
- **Q11 -> the before-validator.** It keeps every base-accepted body accepted (flag-OFF identity, X35).
- **Q12 -> drop `typ`.** Matches Apple's documented header; measured in p2.

## 6. App Review angle

- No UI, no copy (the copy policy is untouched), no new permission, no HIG surface. The new rejection risk is only latency: an Apple sign-in now waits for Apple's token endpoint; RV-2 caps it.
- The benefit exists only if RV-4's order holds (flag ON before submission) and the canary proves it on the build the reviewer gets.
- Failure modes are invisible to a reviewer (WARNING lines only), so a mis-set key cannot cause a rejection, but it also silently voids the fix: the canary is mandatory, not optional.
- Privacy: the stored refresh token is a new server-side record tied to the account; it is not a new App Privacy data type (UserID declared); the policy wording is Q9.

## 7. Comm set check

- The CLAUDE.md-named source-scanning pins are all in `comm_files.txt` (`test_model_config.py`, `test_model_config_enforced.py`, `test_prompt_fence.py`, `test_u3c_store_false_pin.py`, `test_start_command.py`, `test_migration_index_predicate_immutability.py`, `test_openai_key_log_hygiene_s69.py`, `test_sentry_channels_u8d_unit.py`), plus `test_security_regression.py`, `test_hermeticity_pins.py`, `test_secret_scan_static.py`, `test_precommit_hook_phase_b.py`.
- All 19 tests that walk `app/` (rglob / glob / os.walk with an `app` path) are in the set; the 5 out-of-set tests that read a single `app/` file read files this unit does not touch.
- Missing: `tests/test_behavior_dimension_translation.py` (RV-7).
- The SmartCompareApp-scanning rule applies to client units; this unit touches no client file. Backend tests reading client files that matter here (`test_legal_docs_u8.py` T7c) are in the set.

## 8. Measurements pasted

```
[pyt] tag=b3b-rev-base1 start=2026-10-17 07:35:47 end=2026-10-17 07:36:07 elapsed=20s bound=600s status=OK rc=0
  123 passed, 10 warnings; [hermeticity] sentinel checked 123 test(s); [netguard] blocked 0 attempt(s) from 0 node(s)
p1  mock slow handler: status 200 elapsed 1.51 timeout NOT enforced by MockTransport; Timeout(5.0) = Timeout(timeout=5.0)
p3  literal-backslash-n PEM -> ValueError; validate=True wrapped -> Error (binascii, a ValueError);
    validate=True after whitespace strip: True; indented PEM: ACCEPTED; space-joined PEM: ACCEPTED
p2  header with typ None {'alg':'ES256','kid':'K'}; sig bytes 64; CRLF PEM ok; RSA -> InvalidKeyError (ValueError? False); P-384 -> InvalidKeyError
p4  base gaps: []; head gaps (no KEEP): ['apple_siwa_tokens.user_id not deleted, not nulled, not KEEP-listed'];
    head gaps (with KEEP): []; user tables at head: 13 == KNOWN+1: True; classify refresh_token None
p5  default decode at now=1.7e9 -> ExpiredSignatureError; verify_exp False -> True; wrong key -> InvalidSignatureError
sql rc044=0 (044 + rollback, sqlfluff 4.3.0, repo .sqlfluff); rcctrl=1 (CP01 positive control)
```
