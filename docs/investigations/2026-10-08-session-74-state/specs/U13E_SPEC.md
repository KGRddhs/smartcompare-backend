# U13E SPEC - `/url/detect` joins the admin-only paid-route guard (+ #304)

Unit U13e, session 74, 2026-10-08. Sources: plan row `IMPLEMENTATION_PLAN_S72.md:87`, finding EO-01 (`readiness/CRITIQUE_ENG_OPS.md:60`), decision W0=A = guard (`2026-10-08-session-74-state/specs/DECISIONS_ACCEPTED_2026-10-08.md:9`, unit list :13), issue #304 (`readiness/ISSUE_TRIAGE.md:147`).
Base: the brief names main `2ed4b839`; that object exists in NO local worktree (sc-docs-70, smartcompare, sc-s71-t0b, sc-s74-ct, sc-s70-u4b) and origin/main here is `dfbda511`. `sc-docs-70` HEAD `415e0835` = dfbda511 + docs only (`git diff --stat dfbda511 415e0835 -- app tests CLAUDE.md` is empty). Every file:line below is at **dfbda511**. If 2ed4b839 moved app/ or tests/, re-anchor before RED.

## 0. Scope and non-goals
In: both `/api/v1/url/detect` verbs get `require_paid_route_admin` (same attachment as `/url/extract`); #304: a whitespace-only `ADMIN_API_KEY` counts as unset at both env read sites; two amended U13 nodes; one new test file; one CLAUDE.md sentence.
Out: flipping any flag (`ENABLE_OFFLOOP_DNS_RESOLVE` stays OFF, W0=A); the off-loop resolver; `url_validator.py`; other routes (`/url/retailers` stays open: static, no DNS); `text_routes.py` (guard code untouched); client; scripts; the non-hermetic DNS in `test_rate_limiting_complete.py:50-64` (Q3).

## 1. Truth table at dfbda511
**1.1 Handlers** (`app/api/url_routes.py`)
- POST: `:390 @router.post("/detect")` (no dependencies), `:391 @limiter.limit("20/minute")`, `:392 detect_retailer_endpoint(request, body: URLExtractRequest)` (model `:226-228`, `url: str`). `:398` `await _validate_url_offloop_or_sync(body.url)`; False -> `:399` 400 "URL blocked by security policy"; `:401` `detect_retailer` (`url_extraction_service.py:63-83`, pure string match, no I/O); 200 `{"url","retailer":{key,domain,name,region,currency},"supported"}`.
- GET: `:410 @router.get("/detect")`, `:411` limiter, `:412-415 detect_retailer_get(request, url: str = Query(...))`, `:417` validator, `:420` detect_retailer.
- Neither declares `get_optional_user` (no bearer resolution), usage, logging or persistence. Guard import already present (`:32`), `Depends` at `:8`.
- Why DNS runs on the loop: `url_validator.py:526-537 _validate_url_offloop_or_sync`: `offloop_dns_enabled()` (`:130`, env `:107`) OFF -> returns `validate_external_url(url)` inline with no await -> `:355 socket.getaddrinfo(hostname, None)`, synchronous and uncancellable on the event-loop thread; a black-holed host blocks the single uvicorn worker for the resolver timeout (11-12 s measured, CLAUDE.md:414). The validator runs BEFORE any work in both handlers, so the only way to refuse first is a dependency.
- Measured at base (scratch worktree, `[pyt] tag=u13e-probe elapsed=4s status=OK rc=0`): `ENABLE_COMPARE_AUTH_REQUIRED=true`, anonymous GET and POST -> 200, validator called 1; GET without `url` / POST `{}` -> 422; 25 anonymous GETs -> 20x200 then 5x429; detect dependant tree `[]`; OpenAPI GET params `["url"]`, POST no `parameters`.

**1.2 The guard** (`app/api/text_routes.py`)
- `require_paid_route_admin` `:335-346`: flag OFF -> `return None` at once (`:340-341`, no header read); `_admin_credential_passes(request)` True -> None (`:342-343`); any `Authorization` -> 401 reason `ADMIN_REQUIRED` (`:344-345`); else 401 `NO_CREDENTIAL` (`:346`). Never resolves a bearer.
- Flag read site: `compare_auth_required_enabled` `:242-260`, env **`ENABLE_COMPARE_AUTH_REQUIRED`**, per call, strip+lower in {1,true,yes,on}. NOT `ENABLE_PAID_ROUTE_METERING` (`paid_route_metering_enabled` `:179-212`), which the brief named. Both are ON on `web` since 2026-10-03 14:23 (CLAUDE.md:528), so the prod effect is the same; tests key on the real flag (A2).
- `_admin_credential_passes` `:283-307`: header `x-admin-key` (`:292`); empty/absent -> False (`:293-294`); else `verify_admin_key(supplied)` (`:296`), its 403 re-raised after the `ADMIN_KEY_INVALID` log (`:297-302`); pass logs `[paid-auth] admin credential accepted route=<METHOD template>` (`:303-306`). It never reads the env itself.
- `_refuse_paid_route` `:274-280` -> 401 detail `{"code":"AUTH_REQUIRED","error":"Sign in to continue."}` (`:233`); `error_handler.py:113-143` renders `{"success":false,"error","code","request_id"}`; a string 403 detail -> code `FORBIDDEN` (`error_handler.py:26`).
- Attachment = router decorator `dependencies=[Depends(...)]`, never an explicit call: admin `url_routes.py:273,:310` (`/url/extract`), `text_routes.py:1375` (`/text/quick`), `:1475` (`/text/prices/{product}`); user `url_routes.py:331,:368`, text/image twins (pinned by U13 T04 `test_s71_u13_compare_auth_required.py:537`).

**1.3 `ADMIN_API_KEY` read/compare sites in app/** (grep `ADMIN_API_KEY`, `compare_digest`, `x-admin-key`)
- `app/api/admin_routes.py:53-58 verify_admin_key`: `expected = os.getenv("ADMIN_API_KEY", "")`; `:54 if not expected or not hmac.compare_digest(...)` -> 403 "Invalid admin key". Consumers: `text_routes.py:296` (guard), `:1522` (`/text/prices` in-handler), 22 `Depends(verify_admin_key)` sites.
- `app/main.py:418-421 _AdminAuthenticatedStaticFiles` (mount `/admin`, `:475-481`): `:419 if not expected:` -> 503 "Admin not configured"; X-Admin-Key compare `:438-441`; Basic password compare `:461-464`.
- No other read (`database_service.py:735-750` compares `SEARCH_LOG_SYNTHETIC_TOKEN`, not the admin key; `history_routes.py:150,:188` compare share tokens).
- Measured at base: `verify_admin_key(v)` with ENV=v returns True for `"   "`, `"\t"`, `" \n "`; flag ON, ENV `"   "`, X-Admin-Key `"   "` on GET `/url/extract` -> 200 and the provider runs; `/admin/costs.html` with ENV `"   "`: Basic password `"   "` -> 200, X-Admin-Key `"   "` -> 200, no credential -> 401. TestClient delivers whitespace-only header values unchanged (fastapi 0.141.1 / starlette 1.6.0 / httpx 0.28.1, `probe_ws.py`). Over uvicorn/h11 an all-whitespace header probably arrives empty (OWS) - NOT VERIFIED; the Basic path carries the spaces inside base64 and is exploitable over real HTTP. Live key is 64 chars (CLAUDE.md:528): no live exposure.

**1.4 Existing nodes that pin `/url/detect` anonymous or the guard**
- `tests/test_s71_u13_compare_auth_required.py:554-588` T05: offenders loop (`:582` skips only `ALL_METHOD_PATHS`) fails once detect carries a `require_paid_route_*`; `:567` keeps both detect routes in `must_exist`; docstring `:556`. Measured on the trial GREEN: FAILS.
- same file `:938-944` T22b `test_T22b_url_detect_stays_anonymous` (flag ON anonymous GET == 200, validator 1). Trial: FAILS.
- `tests/test_rate_limiting_complete.py:50-64` (detect 429 after 20) and `:108-145` (detect SSRF 400/200): run with the flag unset -> guard returns at once; trial: PASS.
- U13 T04/T06/T17 fixture/T23 (ten routes only) and `test_s71_u13_pins.py` P1 `:189-243` (padded SUPPLIED key -> 403; unset/empty ENV + empty header -> 401), `test_admin_key_and_sentry_scrub.py:104-115`, `test_security_hardening.py:324-330` (empty ENV rejects): unaffected; trial: PASS. #304 strips the ENV only, so the P1 STRIP mutant stays killed.

## 2. Contract after GREEN (both verbs identical; POST body `{"url":u}`, GET `?url=u`)
AUTH = `ENABLE_COMPARE_AUTH_REQUIRED`; ENV = `ADMIN_API_KEY`; E(s,code,err) = status s, `{"success":false,"error":err,"code":code,"request_id":<X-Request-ID>}`; OK = 200 `{"url":u,"retailer":detect_retailer(u),"supported":bool}`; V = validator calls, R = detect_retailer calls.
| # | AUTH | ENV | credential | result | V/R | `[paid-auth]` log |
|---|---|---|---|---|---|---|
| C1 | on | k | none | E(401,AUTH_REQUIRED,"Sign in to continue.") | 0/0 | refused reason=NO_CREDENTIAL |
| C2 | on | k | X-Admin-Key "" | as C1 | 0/0 | NO_CREDENTIAL |
| C3 | on | k | Bearer only (valid or not) | as C1; verify_token never awaited | 0/0 | ADMIN_REQUIRED |
| C4 | on | k | wrong non-empty key | E(403,FORBIDDEN,"Invalid admin key") | 0/0 | ADMIN_KEY_INVALID |
| C5 | on | k | key k | V True -> OK (R=1); V False -> E(400,BAD_REQUEST,"URL blocked by security policy") (R=0) | 1/0-1 | admin credential accepted |
| C6 | on | unset, "", or whitespace-only | none or "" | as C1 | 0/0 | NO_CREDENTIAL |
| C7 | on | whitespace-only (#304) | any non-empty, incl. the same whitespace | as C4 (base: the equal value passed) | 0/0 | ADMIN_KEY_INVALID |
| C8 | on | unset or "" | any non-empty | as C4 (unchanged) | 0/0 | ADMIN_KEY_INVALID |
| C9 | off (unset/"false"/any non-truthy) | any | any | byte-identical to base: OK or 400; no header read | 1/0-1 | none |
| C10 | off, METERING on | k | none | as C9 (metering never gates detect) | 1/1 | none |
| C11 | on | k | none; GET without url / POST `{}` | as C1 (guard precedes 422; measured). Malformed JSON stays 422 (decode precedes dependencies) | 0/0 | NO_CREDENTIAL |
| C12 | on | k | 25 anonymous then key k | 25x401, never 429; then OK (refusals do not consume the 20/min bucket; admitted calls share it) | | |
Ordering guarantee (test E09): on every 401/403 row V=0, R=0 and `socket.getaddrinfo` is never called; on C5 exactly one resolve of the URL host.
#304 beyond detect (ENV whitespace-only): every `Depends(verify_admin_key)` route -> 403 for every header; the paid routes' admin path -> 403 for a non-empty header; `/admin/*` static -> 503 "Admin not configured" for every request (base: 401 without credential, 200 with a matching whitespace credential).
App: no caller (`grep -rn "/detect" SmartCompareApp/src` = 0; `HomeScreen.tsx:558` calls `/url/compare`). A future caller sending a bearer with AUTH on would get 401; the axios interceptor (`api.ts:221-243`) spends one `/auth/refresh`, retries, gets 401 again and rejects. A future app caller therefore needs a new ruling (switch to `require_paid_route_user`), not a client fix.

## 3. Design (measured on a scratch copy of dfbda511: every C-row above held)
- D1 `url_routes.py:390` -> `@router.post("/detect", dependencies=[Depends(require_paid_route_admin)])`; `:410` -> `@router.get("/detect", dependencies=[Depends(require_paid_route_admin)])`; a 3-line comment above `:390`: U13e (EO-01, W0 = guard): no app caller, not paid; admin-only under ENABLE_COMPARE_AUTH_REQUIRED so an anonymous caller is refused before the SSRF guard resolves DNS on the loop. No signature/body/import change; no new flag (rides the flag already ON, so merge = active on deploy).
- D2 `admin_routes.py:54` `if not expected or` -> `if not expected.strip() or`; the compare stays against the raw `expected`; the supplied value is never stripped. One docstring sentence: #304, a whitespace-only key (`str.strip` semantics) counts as unset.
- D3 `main.py:419` `if not expected:` -> `if not expected.strip():` (503). `_admin_credential_passes` (`text_routes.py:283`) inherits D2; `text_routes.py` is not touched.
- Line endings: the Edit tool preserves them; `git diff --stat` must show 2+1+1 changed regions, never a whole file.

## 4. Tests
**4.1 New `tests/test_u13e_url_detect_guard.py`** (hermetic, pure ASCII, byte-check after every write). No `app.*` import at module top; guards matched by `__name__` (RED = failure, never a collection error). Autouse fixture deletes `ENABLE_COMPARE_AUTH_REQUIRED`, `ENABLE_PAID_ROUTE_METERING`, `ENABLE_STRICT_OPTIONAL_AUTH`, `ENABLE_OFFLOOP_DNS_RESOLVE`, `ENABLE_PROXY_AWARE_RATELIMIT`, `HARNESS_SEND_ADMIN_KEY`, `ADMIN_API_KEY` and resets the limiter before and after. Fixed `X-Request-ID`. Sentinels by concatenation: `ADMIN = "u13e-admin-" + "sentinel"`, `WRONG = "u13e-wrong-" + "key"`; `URL = "https://u13e-one.example.invalid/p/1"`. Stubs: `url_routes._validate_url_offloop_or_sync` (counting async, configurable bool), `url_routes.detect_retailer` (counting wrapper over the real one), `auth_routes.verify_token` AsyncMock (asserted 0). `TestClient(app, raise_server_exceptions=False)`. `[verb]` = GET/POST.
| id | assertion | at base |
|---|---|---|
| E01[verb] | detect dependant tree: exactly one `require_paid_route_admin`, zero `require_paid_route_user` (`tests._route_introspection.find_route`) | RED (tree `[]`) |
| E02[verb] | C1 envelope exact; V=0, R=0, verify_token 0 | RED (200, V=1) |
| E03[verb] | C2 | RED |
| E04[verb] | C3; exactly one `[paid-auth] refused route=<VERB> /api/v1/url/detect reason=ADMIN_REQUIRED` | RED |
| E05[verb] | C4 envelope; V=0; reason ADMIN_KEY_INVALID | RED |
| E06[verb] | C5 with V True: status+body equal the AUTH-off anonymous response of the same request; V=1, R=1; one "admin credential accepted route=<VERB> /api/v1/url/detect" | RED (log) |
| E07[verb] | C5 with V False: 400 BAD_REQUEST envelope; V=1, R=0 | PIN |
| E08[verb x AUTH unset/"false" x none/wrong/key] | C9: 200, content equals the no-header request; V=1 each; a spy on `text_routes._admin_credential_passes` sees 0 calls | PIN (12) |
| E09[verb] | REAL validator; `socket.getaddrinfo` patched to a recorder answering 93.184.216.34; AUTH on: anonymous -> 401 and recorder `[]`; then key -> 200 and recorder `["u13e-one.example.invalid"]` | RED |
| E10 | C10 (GET) | PIN |
| E11[verb] | C11: GET without url / POST `{}` -> 401 AUTH_REQUIRED; V=0 | RED (422) |
| E12 | C12 (GET) | RED (20x200+5x429) |
| E13[verb] | fresh OpenAPI build (cached schema restored): GET param names == `["url"]`; POST has no `parameters`; no `security` | PIN |
| E14 | AUTH on, DEBUG on all loggers, wrong + right key: no record carries either value; >=1 `[paid-auth]` record | RED |
| W01[ENV "   " / "\t" / " \n "] | `verify_admin_key(ENV)` raises HTTPException 403 | RED (True) |
| W02 | ENV=ADMIN: `verify_admin_key(ADMIN)` True; `verify_admin_key(" " + ADMIN)` 403 | PIN |
| W03[GET /url/extract, GET /url/detect] | AUTH on, ENV "   ", X-Admin-Key "   " -> 403 FORBIDDEN; `extract_from_url`/R 0, V 0 | RED (200) |
| W04[Basic pw "   " / X-Admin-Key "   "] | ENV "   ": GET `/admin/costs.html` -> 503, text "Admin not configured" | RED (200) |
| W05a / W05b | ENV=ADMIN + X-Admin-Key ADMIN -> 200 / ENV "   " + no credential -> 503 | PIN / RED (401) |
| W06 | AUTH on, ENV "   ", no header, GET `/url/extract` -> 401 AUTH_REQUIRED | PIN |
Total 46 nodes: 26 RED, 20 PIN. W04/W05 need `app/static/admin/costs.html` (present).
**4.2 Amendments (the ONLY existing nodes that change; trial: chunk A 0 new failures, chunk B exactly these two)**
- AM1 `test_s71_u13_compare_auth_required.py` T05: add `U13E_ADMIN_ONLY = frozenset({"GET /api/v1/url/detect", "POST /api/v1/url/detect"})` after `:159`; `:582` -> `if f"{method} {entry.path}" in ALL_METHOD_PATHS | U13E_ADMIN_ONLY:`; docstring `:556` drop "/url/detect x2," and add "(/url/detect x2 is admin-only since U13e)". Keep `:567` (non-vacuity). `checked` 73 at base -> 71, still `>= 60`. Green at base and GREEN.
- AM2 same file T22b `:938-944`: rename `test_T22b_url_detect_admin_only_u13e`; flag ON anonymous GET -> `_assert_envelope(resp, 401, "AUTH_REQUIRED", AUTH_TEXT)`, `stubs.calls == {}`; docstring "PIN T22b (UR2 superseded by U13e, W0 = guard)". RED at base. No node-id list references T22b (grep: none).
**4.3 Comm gate** (45 existing files referencing url_routes, the paid guard, `ADMIN_API_KEY`, `verify_admin_key`, `/admin/`, the U13 fixture, route introspection or OpenAPI, + the new file)
- A (23): test_account_deletion_u8c_sentry_chain test_admin_key_and_sentry_scrub test_admin_referral_endpoints test_analytics test_b2_strict_optional_auth test_cache_hitrate_metadata test_comparison_id_echo test_conftest_env_safety test_cost_dashboard test_endpoint_shapes_vs_jsx test_explicit_pair_integration_mocked test_flush_live_price_key test_gitleaks_config test_http_400_cap_cut_mapping test_m13_03_paid_work_gating test_m13_21_openapi_gated test_paid_route_metering test_partial_specs_stash_on_price_timeout test_password_reset_deep_link test_price_kpi_endpoint test_rate_limiting_complete test_real_price_coverage_l15 test_referral_e2e
- B (22 + new): test_retro_w0_1 test_retro_w1_1 test_retro_w1_9 test_retro_w2_1 test_route_introspection test_s70_model_router_downgrade test_s71_u13_compare_auth_required test_s71_u13_harness_auth test_s71_u13_pins test_security_hardening test_security_regression test_sentry_channels_u8d test_serper_record_usage test_shutdown_drain test_text_error_envelope_no_raw_exception test_text_routes_error_mapping test_tier15_hit_rate_metric test_timeout_partial_integration test_url_validator_offloop test_url_validator_offloop_hops test_w49_extraction_catch_redaction test_w4_13_measurement_truth test_u13e_url_detect_guard
- Base dfbda511: A 443 passed, 2 skipped, 3 deselected (`[pyt] tag=u13e-base-commA elapsed=77s status=OK rc=0`); B 1138 passed (`[pyt] tag=u13e-base-commB elapsed=71s status=OK rc=0`). Trial GREEN: A identical (`u13e-trial-commA 76s OK`); B + rate_limiting + admin_key_scrub + security_hardening: 2 failed (T05, T22b), 1201 passed (`u13e-trial-commB 73s FAIL rc=1`).
**4.4 Commands** (`<wt>` = the backend unit worktree; `<n>` = the agent's notes folder; prefix `PYTHONIOENCODING=utf-8 C:/Users/SynAckITPC/Documents/AI/.venv-qaren/Scripts/python.exe <scratchpad>/harness/pyt.py`)
- RED/GREEN unit: `--bound 600 --tag u13e-unit --log <n>/unit.log --cwd <wt> -- tests/test_u13e_url_detect_guard.py`
- U13 pair: `--bound 600 --tag u13e-u13 --log <n>/u13.log --cwd <wt> -- tests/test_s71_u13_compare_auth_required.py tests/test_s71_u13_pins.py`
- comm: `--bound 1200 --tag u13e-commA|u13e-commB --log <n>/commA.log|commB.log --cwd <wt> -- <chunk>`
- lint: `<venv python> -m ruff check --select E9,F63,F7,F82 --no-cache app/api/url_routes.py app/api/admin_routes.py app/main.py tests/test_u13e_url_detect_guard.py tests/test_s71_u13_compare_auth_required.py` and `-m py_compile` on the same files.
- RED expectation: 26 failed / 20 passed in the new file + AM2 failing; no collection error.

## 5. Diff plan
`app/api/url_routes.py` +5 -2; `app/api/admin_routes.py` +3 -1; `app/main.py` +2 -1 (one comment line); `tests/test_u13e_url_detect_guard.py` new, about 330 lines; `tests/test_s71_u13_compare_auth_required.py` about +7 -6; `CLAUDE.md` 1 sentence edited (section 6). Production delta 6 changed lines. Size S.

## 6. Docs
- CLAUDE.md:528, replace "the four routes with no app caller (POST `/text/quick`, GET `/text/prices/{product}`, POST/GET `/url/extract`) need the admin credential only" with "the four routes with no app caller (POST `/text/quick`, GET `/text/prices/{product}`, POST/GET `/url/extract`) need the admin credential only, and since U13e (EO-01, W0 = guard) so do POST/GET `/url/detect` (not paid; this refuses the anonymous on-loop DNS path before the SSRF resolve; a whitespace-only `ADMIN_API_KEY` counts as unset, #304)"; and in the same row "re-probe anonymously (each paid route 401; `/url/detect`, `/url/retailers`, `/health`, `/legal/*` unchanged)" -> "re-probe anonymously (each paid route and `/url/detect` 401; `/url/retailers`, `/health`, `/legal/*` unchanged)".
- Runbook/admin docs: `U13_ACTIVATION_RUNBOOK_AHMED.md:27` and `U13_COMPARE_AUTH_SPEC.md:423` name `/url/detect` as "unchanged" but are session-71 records: not edited; the session-74 docs checkpoint records the new expectation. No `app/static/admin` page and no `scripts/` file names the route (grep: 0).

## 7. Assumptions and open questions
- AS1 Base dfbda511, because 2ed4b839 is not resolvable locally and 415e0835 (dfbda511 + docs) holds identical app/tests/CLAUDE.md; the alternative (guessing 2ed4b839's content) is unverifiable.
- AS2 The guard keys on `ENABLE_COMPARE_AUTH_REQUIRED` (attach the existing guard unchanged), not `ENABLE_PAID_ROUTE_METERING` as the brief says: re-keying would change the ten paid routes' contract (out of scope), and both flags are ON in prod, so the outcome the owner approved is identical. E10 pins that metering alone does not gate detect.
- AS3 #304 = "whitespace-only counts as unset", compare against the raw value: beats strip-then-compare, which would newly admit a header matching a padded env value (a behaviour change #304 does not ask for and P1 does not cover).
- AS4 Admin-only, not `require_paid_route_user`: W0=A text and no app caller; the admin guard never calls Supabase `verify_token`, so a bearer flood costs nothing.
- AS5 New file separate from the U13 file: the U13 file carries the T17 recorder/fixture protocol; isolating keeps the fixture untouched.
- Q1 (Fable) Confirm AS2.
- Q2 `require_paid_route_admin` docstring (`text_routes.py:336-339`) says "the four paid routes"; edit it (touches text_routes.py) or leave it to CLAUDE.md? Default: leave.
- Q3 `test_rate_limiting_complete.py:50-64` resolves example.com for real (netguard `[egress]` line at base): pre-existing, file an issue?
- Q4 NOT VERIFIED: whether uvicorn/h11 strips an all-whitespace header to empty in prod (affects only the X-Admin-Key half of #304; the Basic half is exploitable regardless).
- Q5 Merge activates the guard on deploy (flag already ON); any external monitor that calls `/url/detect` anonymously would start seeing 401 (none known: SentryUptimeBot probes `/`).
