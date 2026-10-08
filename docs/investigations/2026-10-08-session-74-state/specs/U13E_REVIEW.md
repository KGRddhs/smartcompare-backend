# U13E REVIEW - adversarial review of U13E_SPEC.md

Reviewer: Opus adversary, session 74, 2026-10-08 18:07-18:25 AST. Spec sha256 c8cd1e6db5c1ab623b02ca4236c61c5a9d995100ee60d59bba1cfd044d09a549 (re-hashed, matches).
Code read in sc-docs-70 (HEAD 49883e84 = 3b24d182 + docs). Measurements in a DETACHED scratch worktree at 3b24d182 under the review notes folder, removed afterwards (`git worktree remove --force`); sc-docs-70 `git status` clean.

## Verdict
SOUND. No blocking finding. Proceed to RED after the amendments below (M1 is a statement/docs change, not a code change; m2 adds one PIN node).
- With `ENABLE_COMPARE_AUTH_REQUIRED` truthy, no anonymous request shape reaches DNS on `/url/detect` (22 shapes x 3 truthy spellings, real validator, `socket.getaddrinfo` recorder: dns [] on every non-admin row).
- No whitespace-only credential is accepted after D2/D3 (12 whitespace env shapes, supplied == env -> 403; `/admin/*` -> 503).
- The two existing nodes that flip are exactly U13 T05 and T22b (12-file collision set + 5 unlisted introspection files run on the patched copy).

## Base re-anchor (supersedes spec AS1)
- `2ed4b839` RESOLVES now: it is the #334 merge. `git diff --stat dfbda511 2ed4b839 -- app tests CLAUDE.md` is EMPTY, so every spec citation holds at 2ed4b839.
- origin/main has since moved to `3b24d182` (#335 U3c). `2ed4b839..3b24d182` changes app/services/{api_budget,push,referral}_service.py, four tests/fixtures files, and CLAUDE.md lines 265, 517 and 647, each as a 1-for-1 line replacement. CLAUDE.md:528 keeps its number and text. app/api, app/main.py, app/middleware and app/utils are byte-identical dfbda511..3b24d182.
- Every measurement below is at 3b24d182.

## Measurements (all bounded-runner, hermetic)
| tag | what | result |
|---|---|---|
| u13e-adv-base2 | probe at base | `[pyt] tag=u13e-adv-base2 elapsed=4s status=OK rc=0` |
| u13e-adv-patched | probe with spec D1+D2+D3 applied | `[pyt] tag=u13e-adv-patched elapsed=4s status=OK rc=0` |
| u13e-adv-p6 | signed-in residual probe (patched) | `[pyt] tag=u13e-adv-p6 elapsed=4s status=OK rc=0` |
| u13e-adv-coll | 12 files: U13 x3, rate_limiting, admin_key_scrub, security_hardening, security_regression, m13_21_openapi, paid_route_metering, cost_dashboard, route_introspection, endpoint_shapes (patched) | `[pyt] tag=u13e-adv-coll elapsed=18s status=FAIL rc=1`: 2 failed = T05 + T22b exactly, 488 passed, 1 deselected |
| u13e-adv-extra | test_backend_cleanup, test_arabic_verdict_output_w414, test_s70_url_client_retries, test_url_validator_offloop(_hops) (patched; three are not in the spec's comm list) | `[pyt] tag=u13e-adv-extra elapsed=22s status=OK rc=0` (266 passed) |
| parser_probe.py | h11 0.16.0 / httptools 0.8.0 header parse (no socket) | see m3 |
(The first base run, u13e-adv-base, FAILED on a probe bug: an unstubbed extract leg and a bytes host in the recorder. Both were fixed, the probe was rerun, and that run is not evidence.)

Attack results:
- **(1) Anonymous DNS after the unit.**
  - With AUTH on, every anonymous, bearer, Basic, empty-key, wrong-key or whitespace-key request is 401 or 403 with zero resolves: GET, POST, form body, text/plain body, `{}`, no `url`, a repeated `url`. HEAD gives 405, a trailing slash 307, `/URL/` 404, a CORS preflight 400, malformed JSON 422; none of them resolves.
  - `url_router` is included once (`main.py:375`). No other anonymous route calls `_validate_url_offloop_or_sync`, `validate_external_url` or `getaddrinfo`. The other callers are `url_routes` :296/:317 (admin), :359/:381 (user), and the services `price_service.py:14843`, `url_extraction_service.py:115`, `shopify_pdp_service.py:319`, which are reached only behind the U13 guards.
  - `/url/retailers` makes no DNS call.
  - No middleware validates URLs: grep over app/middleware and main.py finds none.
- **(2) Guard semantics.**
  - The route-level `dependencies=[...]` runs before query/body validation (GET without url gives 401, not 422), before the handler body (validator 0) and before the slowapi decorator (25 anonymous calls give 25x401 and no 429; the admin call after them gives 200).
  - Only JSON decoding comes first (malformed JSON stays 422, with no DNS).
  - Flag OFF (unset, or a non-truthy spelling such as `enabled`): detect stays anonymous and resolves on the loop. That matches base exactly. See the residual-risk section.
- **(3) #304.**
  - The only env read sites are `admin_routes.py:53` and `main.py:418`.
  - Compare sites: `admin_routes.py:54-57`, `main.py:439-441` and `:461-464`. `text_routes.py:296` and `:1522` reach the env through `verify_admin_key`; there are 22 `Depends(verify_admin_key)` sites (19 in admin_routes, 3 in text_routes).
  - Base: 12 whitespace env shapes (3 spaces, tab, LF, CRLF, VT, FF, FS, NEL, NBSP, EM SPACE, IDEOGRAPHIC SPACE) with the same supplied value gave True. The /admin static mount gave 200 with a Basic password equal to the env and 401 with no credential.
  - Patched: the same inputs give 403, and the static mount gives 503 for both.
  - Header and env values never get stripped before the compare (raw compare).
- **(4) Collisions.** The spec's list is complete:
  - T05 (`must_exist` :567 plus the skip set :582) and T22b (:938-944) are the only nodes that pin detect.
  - `test_rate_limiting_complete.py:50-64,:108-145` runs with the flag unset and passes.
  - `tests/fixtures/s71_u13_flag_off_baseline.json` holds no detect operation (grep).
  - The full OpenAPI document is byte-identical between base and patched, so no OpenAPI pin can move.
  - T05 counts: `checked` is 73 without AM1 and 71 with it. On the patched copy without AM1, the offenders are exactly the two detect verbs.
  - AM2's `stubs.calls == {}` is valid: `_Stubs.calls` is a dict (U13 file :208).
- **(5) Hermeticity.**
  - E09's design works: the real validator plus a module-level `socket.getaddrinfo` patch records exactly one host on the admin row and none on the 401 row.
  - The netguard (`tests/_netguard.py:205-208`) is restored by monkeypatch; the hermeticity sentinel stayed clean.
- **(6) Envelope.**
  - 401 comes from `_refuse_paid_route` (`text_routes.py:274-280`, detail :233): `{"success":false,"error":"Sign in to continue.","code":"AUTH_REQUIRED","request_id"}`.
  - 403 is `{"success":false,"error":"Invalid admin key","code":"FORBIDDEN","request_id"}` (`error_handler.py:26,:113-143`).
  - Both match the ten paid routes byte for byte, because they come from the same functions.
- **(7) Docs.** See m4 and m5.

## Findings

### M1 (major): EO-01 stays reachable by any signed-in caller; the spec never says so
- **Evidence:** test p6, patched, AUTH on, METERING on, bearer accepted by a stubbed `verify_token`.
  - GET and POST `/api/v1/url/compare` with an unresolvable host each return 400 `BAD_REQUEST` "URL blocked by security policy".
  - `socket.getaddrinfo` is called (once per verb), and `consume_comparison_credit` is called 0 times.
  - The code path: `compare_urls` and `compare_urls_get` run `_validate_url_offloop_or_sync` BEFORE the credit gate on purpose (`url_routes.py:357-360`, `:381-382`). With `ENABLE_OFFLOOP_DNS_RESOLVE` OFF that is the inline sync resolve (`url_validator.py:535-537`, `:355`).
  - `POST /api/v1/auth/register` is anonymous (`auth_routes.py:571`).
- **Consequence:** after U13e, the single-worker freeze of 11-12 s per request (CLAUDE.md:414) narrows from "any internet caller" to "any caller with a free account, at zero credit cost". The per-IP 10/min limiter is not a bound (#299).
- **The spec's own text is accurate:** "anonymous" in D1 and in the CLAUDE.md sentence. But the plan row (IMPLEMENTATION_PLAN_S72.md:34, "U13e (or decision W0)") and the owner's W0=A choice treat U13e as the EO-01 fix.
- **Fix (no code change in this unit):**
  - (a) Add a residual-risk line to spec section 0/7: "U13e closes the anonymous half of EO-01 only; a signed-in caller still reaches the on-loop resolve through POST/GET /url/compare before any credit is reserved; only ENABLE_OFFLOOP_DNS_RESOLVE (W0 option B) closes it."
  - (b) Append the same clause to the CLAUDE.md:528 sentence in section 6.
  - (c) The orchestrator surfaces it to the owner in the session-74 checkpoint as an input to W0.

### m1 (minor): AS1 is stale
- `2ed4b839` resolves and equals dfbda511 for app/, tests/ and CLAUDE.md. Main is now `3b24d182`; the deltas are listed in the Base re-anchor section above.
- **Fix:**
  - Replace AS1 with: "Citations valid at 2ed4b839 and 3b24d182; CLAUDE.md:528 unchanged."
  - The GREEN agent re-runs the two comm-chunk baselines at the unit worktree's actual base (sc-s71-t0b must first be fast-forwarded past #335, per ledger.md:62). The pass counts are expected to be unchanged, because no comm-list file changed. That expectation is not measured.

### m2 (minor): the AS3 design choice (raw compare against the unstripped env) is not pinned
- Every W-node uses an exact env or a whitespace-only env. A GREEN that writes `expected = os.getenv(...).strip()` and compares the stripped value passes all 46 nodes and both AMs. Mutant reasoned from the node list, not run.
- **Fix:** add a PIN node, for example `W07`:
  - Set `ENV = " " + ADMIN + " "`.
  - `verify_admin_key(ADMIN)` must raise 403.
  - `verify_admin_key(" " + ADMIN + " ")` must return True.
  - The node passes at base and after GREEN, and kills the env-strip mutant. That makes 47 nodes, 26 RED and 21 PIN.
- **Also correct AS3's rationale.** Over real HTTP a padded env can never be matched: both parsers strip leading OWS (see m3), so raw compare fails CLOSED (the admin is locked out). Strip-both would make a padded env usable. Neither choice admits an attacker. Fail-closed is the real reason to keep raw compare, not "newly admit a header".

### m3 (minor): Q4 is now VERIFIED; update spec section 1.3 and Q4
- Production runs `uvicorn app.main:app` with no `--http` flag (Procfile, `railway.json:7`). uvicorn 0.52.4 `--http auto` selects `HttpToolsProtocol` whenever httptools imports (`uvicorn/protocols/http/auto.py`), and `httptools==0.8.0` is pinned (requirements.txt:64).
- Measured parse of `X-Admin-Key:` followed by "   " or a tab: b'' under httptools 0.8.0, and b'' under h11 0.16.0.
- So the X-Admin-Key half of #304 cannot be reached over HTTP: the value arrives empty, giving 401 on the paid guard and 403 on `verify_admin_key`.
- The Basic-password half on `/admin/*` (`main.py:445-466`) is the real base exposure when ADMIN_API_KEY is whitespace-only: the spaces travel inside base64. The live key is 64 chars per CLAUDE.md:528, so there is no live exposure. The live value is NOT VERIFIED, as the rules forbid reading it.
- W03 and C7 remain valid server-logic tests (TestClient delivers the spaces).
- A side fact for any future strip debate: httptools keeps trailing spaces ("abc   " -> b'abc   '), while h11 strips them.

### m4 (minor): a CLAUDE.md:528 merge collision with BE-HARNESS
- `FABLE_RULINGS_BE_HARNESS.md:21` (Q4) updates "the CLAUDE.md:528 harness line in THIS unit". U13e section 6 edits two phrases of the same physical line, a single-line paragraph, so the second PR to merge conflicts on it.
- **Fix:** the spec states the rule: whichever merges second rebases and re-applies its phrase edits by text match, never by line diff. The orchestrator sequences the two PRs.

### m5 (minor): docs that still describe detect as anonymous are not all addressed
- **CLAUDE.md:517** (session-72 readiness block) still says "`GET/POST /api/v1/url/detect` is anonymous and resolves DNS on the event loop". U3c set the precedent on this same line by annotating its findings "(both fixed by U3c)".
  - **Fix:** annotate it "(anonymous half closed by U13e while ENABLE_COMPARE_AUTH_REQUIRED is on; see M1)".
- **CLAUDE.md:528**, the **Rollback** sentence: "unset the flag ... reopens anonymous paid compares".
  - **Fix:** append "and the anonymous on-loop DNS path of /url/detect".
- **CLAUDE.md:414** describes "every unauthenticated `/api/v1/url/*` handler" in the past tense. It can stay; optional.
- **U13_ACTIVATION_RUNBOOK_AHMED.md:27** and **U13_COMPARE_AUTH_SPEC.md:423** are session-71 records; the spec leaves them, and I agree. The session-74 checkpoint must record the new re-probe expectation: detect returns 401.

### m6 (minor): spec Q3 is inaccurate
- `test_rate_limiting_complete.py` detect nodes do NOT resolve example.com for real. `tests/_netguard.py:205-208` raises `NetworkBlocked` on any non-IP name, and the run reports `[egress] socket.getaddrinfo example.com:None` under "[netguard] blocked 96 attempt(s)". The validator's `except Exception` turns that into False, so the result is 400.
- No egress, so no issue is needed for egress.
- **Fix:** reword Q3, or drop it.

### n1 (note): first-import dotenv re-injection (latent, not live)
- `app/main.py:11` and `url_extraction_service.py:6` call `load_dotenv(override=True)` at first import. The spec's file imports app inside tests (by design), so a flag present in a reachable `.env` would be re-set AFTER the autouse delenv, for the first node of a process.
- Existence check only, nothing read: no `.env` exists in sc-s71-t0b, sc-docs-70 or any parent directory. One exists only in the smartcompare clone. CI has none.
- **Fix:** one line in the autouse fixture, `import app.main` BEFORE the delenv loop. The U13 file has the same latent pattern; do not change it in this unit.

### n2 (note): refusals bypass the limiter and log one INFO line each
- Measured: 25 anonymous calls gave 26 `[paid-auth]` lines (25 refusals plus 1 admin acceptance), no 429, and 0 key values at DEBUG.
- An anonymous flood on detect now writes unbounded INFO lines. At base the 20/min per-IP decorator capped handler work, though per-IP is weak behind the Railway edge.
- Admin-key guessing on detect is unthrottled (#299). The key is 64 chars.
- The ten U13 routes already behave this way. Accept, and list it in the residuals.

### n3 (note): no detect-only rollback
- Merging is activation (the flag is already ON, as Q5 says).
- The only runtime lever is unsetting ENABLE_COMPARE_AUTH_REQUIRED. That also reopens the ten paid routes, and it accepts only {1,true,yes,on}: `enabled` was measured as OFF.
- Reverting detect alone takes a code revert.
- Live flag state on `web` is NOT VERIFIED here (CLAUDE.md:528 records it ON since 2026-10-03 14:23; the rules forbid Railway reads).

### n4 (note): invisible non-whitespace keys still count as configured
- A key made only of a zero-width space (U+200B) is not whitespace under `str.strip`; measured: still accepted when supplied equal.
- #304 is literally about whitespace, so this is out of scope. A minimum-length rule (for example `len(expected.strip()) < 32` counts as unset) would close all low-entropy keys. It would be a separate ruling, not this unit.

### n5 (note): decision provenance wording
- LAUNCH_PUNCH_LIST.md:309-312 defines W0=A as "keep the load flags OFF".
- IMPLEMENTATION_PLAN_S72.md:140 reframes W0 as guard/flag/open, with no letters.
- The authority for building U13e is DECISIONS_ACCEPTED_2026-10-08.md:13 (UNITS: all) plus W0=A (the DNS flag stays dark). The spec's "W0=A = guard" merges the two, but the outcome is consistent. Cosmetic.

### n6 (note): E13 could pin more
- The whole OpenAPI document is byte-identical before and after the patch (measured). E13 checks only the parameter names and security. Optional: compare the two detect operation objects whole against a value captured in-test with the guard removed. Not required.

### n7 (note): stale docstrings (Q2)
- The `compare_auth_required_enabled` docstring (`text_routes.py:246-251`) and the `require_paid_route_admin` docstring (:336) still say "four routes". I agree with the Q2 default (leave text_routes.py untouched).
- The new url_routes comment should say it extends the admin set (six verbs).

## Answers to the spec's open questions
- **Q1:** AS2 CONFIRMED. The guard reads `compare_auth_required_enabled` (`text_routes.py:242-260`, :340), not the metering flag. E10 kills a metering-keyed mutant.
- **Q2:** leave (see n7).
- **Q3:** no issue is needed (m6).
- **Q4:** VERIFIED (m3).
- **Q5:** correct. Add n3 to the checkpoint.
- **Base question:** answered in the Base re-anchor section.

## Residual risk after U13e (for the spec and the checkpoint)
1. A signed-in free account still freezes the single worker through /url/compare (M1).
2. Flag OFF (rollback, or a non-truthy spelling) reopens anonymous on-loop DNS on detect, extract and compare (measured).
3. Refusals are unthrottled and logged at INFO (n2).
4. ENABLE_OFFLOOP_DNS_RESOLVE OFF is unchanged by design (W0=A).

## Assumptions
- A1: 3b24d182 is the right measurement base, rather than dfbda511. It is current main, the unit worktree will be fast-forwarded to it or past it, and the files under test are byte-identical to dfbda511.
- A2: TestClient plus a recorder on `socket.getaddrinfo` is sufficient evidence of "no DNS before the guard", without a live uvicorn. The validator's only resolve is `socket.getaddrinfo` (`url_validator.py:355`; the off-loop branch :448 also goes through it), and the route stack under TestClient is the production ASGI stack minus the HTTP parser. The parser half was measured separately (m3).
- A3: M1 is major, not blocking. Other routes are explicitly out of scope and the owner chose W0=A, but the owner's decision needs the correct residual.

## Not verified
- Live flag values and the length of ADMIN_API_KEY on Railway (rules).
- Whether Supabase "Confirm email" is on (it affects how cheap M1's account is; SMTP=OPEN).
- External monitors calling /url/detect (Q5, from the spec; not re-checked).
- The env-strip mutant of m2 (reasoned from the node list, not run).
- Comm-chunk counts at 3b24d182 (I ran 17 files, not the 45).

## Files written by this review (sha256 in the return value)
- this file
- u13e/review/notes.md
- u13e/review/parser_probe.py
- u13e/review/adv_probe_copy.py
- u13e/review/trial_patch.diff
- u13e/review/out/base.p{1..5}.json, u13e/review/out/patched.p{1..6}.json (p6 was run on the patched copy only)
- u13e/review/*.log
