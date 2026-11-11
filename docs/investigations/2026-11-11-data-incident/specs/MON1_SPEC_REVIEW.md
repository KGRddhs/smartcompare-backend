# MON1 SPEC REVIEW (adversarial; READ-ONLY round, H5 c)

- Unit: MON1 LLM-CREDENTIAL-HEALTH. Spec .qa-s80/MON1_UNIT_SPEC.md, sha256 99c538c897e1995422291d26f59ddd83d8df6205cae93277a4d6ba3b96bf5037 (re-hashed at the start: match).
- Base a74caba7e3ff66b12e94178c912197c845ccbd14; worktree HEAD == base; `git status --short` empty before and after. No pytest / jest / tsc / eslint ran. Measurements: git show / git grep at the base sha, reads of the pinned SDKs in .venv-qaren, and the official vendor docs named below (read-only; no project value, credential or personal value sent).
- Reviewer: Opus 5.5 adversarial spec reviewer, 2026-11-11. The unit stays "merged, NOT yet proven" whatever this review says (H6).

## VERDICT: APPROVE_WITH_CHANGES

Re-measured and HOLDING: the dispatch census (exactly three SDK call statements in app/: api_budget_service.py:1002 / :1013, llm_router.py:969, content_safety_service.py:259; no embeddings / responses / files / audio; the probe's models.retrieve is not a U3c or Anthropic Messages surface, test_u3c_store_false_pin.py:36-43, :233-246); the hook statements H1-H8 against the base bytes (api_budget_service.py:957-1056, llm_router.py:921-1022, content_safety_service.py:234-270); the gating invariants (the hooks add no breaker write); the /health idiom (main.py:313-323, :626-648); the drain arithmetic and handler order (main.py:357-460); the limiter census mechanism (test_retro_w1_9.py:424-436 computes reachability through slowapi _should_exempt, so @limiter.exempt keeps the set at three); the codeless-503 mapping (error_handler.py:24-35 applies only to raised HTTPExceptions; ErrorHandlerMiddleware :337-368 passes a returned JSONResponse untouched); the one E-row (K1, test_s81_s03_llm_ledger_v2.py:193, :2484-2492); the S81-04c footprint (no hook in extraction_service.py, image_routes.py or url_extraction_service.py); the CLAUDE.md anchor (record CLAUDE_md_a74caba7.txt:630 S81-G10 block, :637 `## Tests`).

Four defects (B1-B4) must be folded into the orchestrator's rulings before the RED round freezes rows on them. None needs a redesign; all are spec edits.

## 1. Refuted claims (measured truth, file:line or URL)

R1 (spec 1.8, 2.2 `classify`, row L02, limit L-4): "Out of credit: OpenAI answers 429 with error.code == insufficient_quota ... quota = RateLimitError AND code == insufficient_quota" and "OpenAI's org-level hard limit is assumed to surface as insufficient_quota". REFUTED by OpenAI's official error-codes page (https://developers.openai.com/api/docs/guides/error-codes, read 2026-11-11): the out-of-credit 429 is "429 - Credit balance exhausted" with code `credit_balance_exhausted`; for billing errors the page says to inspect error.code and that the broader error.type "can still be" insufficient_quota. The enforced limits are separate 429 codes: `organization_spend_limit_exceeded`, `project_spend_limit_exceeded`, `organization_usage_limit_exceeded`. The pinned SDK exposes both structured attributes: openai/_exceptions.py:72-74 (openai 3.3.1 in .venv-qaren) sets `code`, `param` AND `type` from the error body. As specified, the leaf classifies the most likely real out-of-credit answer (the class this project hit in session 69) as None: no quota state, no alert, /health/llm 200.

R2 (spec 2.5 "No exception text, no request data, no extras"; brief R-MON1-6 "No exception text, no request data"): SE01 / SE03 measure the event in a child process OUTSIDE any request. In production every hook fires INSIDE a request (guarded_llm_create, guarded_anthropic_create, moderate_output; the Serper selection runs in to_thread workers that copy the context). The pinned sentry-sdk Starlette integration adds a request event processor to the request scope (sentry_sdk/integrations/starlette.py:555-573 and :641-659), so a capture_message from a hook carries `request` (method, path, the query string, the allowlisted headers), the transaction name and any scope tag set earlier in the request (app/services/database_service.py:462 sets `comparison_renderable`). `_before_send` scrubs those regions (sentry_service.py:447-487; _QUERY_STRING_PII_PARAMS :53-55 covers q / query / url / url1 / url2 / product_a / product_b) but does not remove them. The claim is false for the production path and no row measures it.

R3 (spec 2.9 "ON: ... 2xx -> note_success(p, 'probe')"; 11.1 Q8 "no tight limit applies" read as "the probe sees the credential state"): a metadata call cannot observe the QUOTA state. Anthropic documents the tier spend cap as a 429 rate_limit_error "On the Messages API" (https://platform.claude.com/docs/en/api/rate-limits, "Reaching your spend cap"); OpenAI's billing codes (R1) are request errors of the billed endpoints; neither vendor documents the Models endpoint as subject to them. A models.retrieve 2xx while the account is out of credit is the expected outcome, and 2.9 maps it to note_success: the probe flips a dispatch-observed `quota` to `ok`, fires the info recovery event, turns /health/llm 200, and the per-process latch (2.5) then suppresses the next quota event. With the probe ON the active part ERASES the alarm the passive part raised.

R4 (spec 2.9 / P04 / L-8: a probe 401 means a dead credential): OpenAI's official page lists under "401 - Invalid Authentication" the cause that the key "does not have the required permissions for the endpoint you are calling" (same URL as R1). A RESTRICTED key without the Models permission (the owner is about to create a new key, N1) answers the probe with 401 while chat completions succeed: the probe marks `rejected` (error event, /health/llm 503), the next compare marks `ok` (recovery event), and the state flaps every interval. Not covered by 9 L-3 (which names only a model-specific 403 on dispatch).

R5 (spec 5 P01 "one probe_once-guarded tick through the tick helper"; MU15 "probe flag gate removed -> P01"): the 2.9 contract defines NO tick helper. The flag is read inline in run_forever; probe_once reads no flag. P01 either calls probe_once (it then dispatches with the flag OFF: never a green PIN of OFF) or drives run_forever (sleeps patched, a cancel: not stated). MU15 has no target statement. The row is unbuildable from the contract.

R6 (spec 8b PP5 "it shows the path up (200) while the credential works"): /health/llm answers 200 {"openai": "unknown"} whenever the process holds no outcome (2.6 row 1, M01). With the probe OFF (its default until the O3 window), about two comparisons a week, and the state reset by every deploy / restart (9 L-1), the monitor reads 200 for most of any week even with a DEAD credential. PP5 passes while the production problem remains; a plain "alert on non-200" monitor is not an alarm for this incident class while the probe is OFF.

R7 (spec 5 HE05 "one marked through the Redis fake ... marked_exhausted 1"): 2.8 counts `_serper_exhausted_logged` (serper_service.py:92), which only `_mark_serper_key_exhausted` writes (:235-241). A flag set directly in the Redis fake leaves the set empty: the contract yields 0 where the row expects 1. The set is also never cleared between tests (conftest.py:183-201 resets the budget memo and the key-state memo only; the 3.5 fixture does not clear it), so a prefix marked by an earlier test leaks into the count (order-dependent row).

R8 (spec 1.9 presented as the complete guard table for main.py): MISSING tests/test_backend_cleanup.py:61-77, which asserts `"comparison_service" not in inspect.getsource(app.main)` and `"from app.api.routes" not in ...`. A new main.py comment or docstring that names structured_comparison_service (natural beside the monitor route or the probe start handler) reddens it. Green while GREEN avoids the substring; it belongs in 1.9 and 4.2.

R9 (spec 5 P10 "shutdown names ... in order"): the row does not say how the names are read. tests/test_shutdown_drain.py:689-715 documents that the local fastapi / starlette (0.115.0 / 0.38.6) and the CI pins (0.141.1 / 1.6.0) differ and reads app.router.on_shutdown duck-typed with a source fallback. P10 must reuse that shape or it is a local-vs-CI coin flip.

## 2. Blocking issues (fold into the rulings before RED)

B1 The OpenAI quota classifier (R1). Rule: quota = an openai APIStatusError with status 429 AND (`code` in {credit_balance_exhausted, insufficient_quota, organization_spend_limit_exceeded, project_spend_limit_exceeded, organization_usage_limit_exceeded} OR `type` == "insufficient_quota"), read through getattr, never message text. L02 gains one parametrised case per code plus the type-only case; a plain RateLimitError (code rate_limit_exceeded or slow_down, type rate_limit_error) stays None; MU07 is re-pointed (removing the type branch must be killed separately). 1.8 and L-4 are rewritten with the URL. The set is a frozenset constant in the leaf; its NAME avoids the scanner keywords.

B2 The probe must never clear a state it cannot observe (R3). Rule: a probe 2xx proves authentication only. It may move `rejected` -> `ok` (only when the rejected state's source is probe or its last_status is 401) and leaves `quota` (and a dispatch-sourced 403) untouched; a probe-sourced `ok` never fires the recovery event while a dispatch-sourced quota is held. New RED rows: P13 (dispatch quota, then a probe 2xx: state stays quota, zero recovery calls, /health/llm stays 503) and P14 (dispatch 401, then a probe 2xx: ok + one recovery call). A mutant "probe success clears quota" must be killed by P13.

B3 The probe's 401 on a permission-restricted key (R4). Two acceptable rulings: (a) an owner precondition on the O3 window, stated in 8.3 step 3 and in the CLAUDE.md block: the web key must carry the Models read permission (or All), checked in the OpenAI console before the flip; PP4 then reads "zero rejected transitions with source probe while compares succeed"; or (b) a probe-sourced `rejected` does not override a dispatch-sourced `ok` younger than one interval and is logged as L4 outcome `rejected_probe_only` without an event. The spec must pick one and add the stated limit; (a) is cheaper and keeps the recorder simple.

B4 The P01 / MU15 seam (R5). Add to 2.9 `async def tick()`: its FIRST statement `if not probe_enabled(): return {}`, then `return await probe_once()`; run_forever calls tick() inside its try. P01 calls tick() with the FULL configuration (both keys, every role flag ON, the interval set) and the client recorders; MU15 deletes tick's first statement. P09 keeps driving run_forever with the sleep recorder.

## 3. Corrections (not blocking; fold into the spec text)

C1 (R2) Either (i) emit the alert in a scope that carries no request data (measure on sentry-sdk 2.68.1: a forked isolation scope that is cleared before capture_message, or a new scope with no request processor) and add SE04: a TestClient request to a stub route whose handler calls note_failure with a real AuthenticationError; exactly one event, no `request` key, no request-scoped tag; or (ii) rule that the scrubbed request region is acceptable and rewrite 2.5 to say so (the brief then needs an amendment: it says "no request data"). (i) matches the brief.

C2 (R6) PP5 and 8.3 step 2: the uptime monitor is a KEYWORD monitor on GET /health/llm that alerts on a non-200 OR on a body without `"openai": "ok"`, and it is adopted in the probe's window (after O3), not before; before O3 the alarm is the Sentry event only. PP5 then requires the body to read ok, not unknown. Owner step: GET, never HEAD (L-7; a default HEAD monitor reads 405 as down).

C3 (R7) HE05 marks through `serper_service._mark_serper_key_exhausted(k)` (with the Redis fake), uses run-time-unique first-8 prefixes per test, and S01 / S02 do the same; or the 3.5 fixture also snapshots and restores `_serper_exhausted_logged` (never a plain clear: S05 pins once-per-process WARNING semantics). State the choice.

C4 (R8) Add tests/test_backend_cleanup.py:61-77 to 1.9 and 4.2: no new main.py text may contain the substrings "comparison_service" or "from app.api.routes".

C5 (R9) P10 reads the shutdown names through the test_shutdown_drain.py:689-715 helper shape (on_shutdown when exposed, else the decorated-def order in app/main.py).

C6 Alert-rule semantics (owner step 8.3 step 1, PP2, PP3). The fixed fingerprint [kind, provider, state] puts every rejected event of every process into ONE Sentry issue. A rule whose trigger is "a new issue is created" fires once in the issue's life; the next outage (a later deploy, a later key) is silent unless the issue was resolved (regression). The owner step must name the trigger: the issue-frequency condition (more than 0 events in 5 minutes) with an action interval, or "resolve after recovery" so the regression trigger fires. PP3 adds: after a redeploy with the credential still dead, a SECOND notification arrives.

C7 The per-process latch (2.5) means rejected -> ok -> rejected inside one process is SILENT the second time (L08 pins it). With Railway restarting the process on every merge this is bounded, but it is a stated limit the spec does not name; add it as L-12 (or rule a per-transition event bounded by a cool-down instead).

C8 Anthropic's prepaid-credit case: the Messages API answers a too-low credit balance as a 400 invalid_request_error (message text only; https://platform.claude.com/docs/en/api/errors lists 402 billing_error as payment-information trouble and the user-set spend limit as a 400). MON1 classifies neither (correctly, no message text). L-4 should name the credit-balance 400 alongside the spend limit.

C9 OpenAI's 401 headings also include "IP not authorized" and "You must be a member of an organization" (same URL); and 403 is documented only for "Country, region, or territory not supported". Both map to `rejected` under the brief's class rule; the CLAUDE.md row should say `rejected` means "the provider refuses this credential from this host", not only "the key is revoked", so the owner's first check is the console and the host region, not a key rotation.

C10 1.1 cites the census comment at :938-956 as naming "content_safety_service:152" and "image_service:173"; the moderation call is at :259 at base (git grep). Comment-only staleness: if GREEN appends to that comment (3.3 "optionally"), it rewrites the two stale line numbers in place (CLAUDE.md principle 5) or leaves the comment alone; the K1 digest is unaffected either way (comments are not in ast.dump).

## 4. Contract risks (deploy-visible delta of the UNFLAGGED part)

- The 2.11 list is otherwise complete: no client-read key changes, no status code changes on an existing path, no log level changes on an existing line, no added await or I/O on the request path (one lock + one dict write per outcome; the Serper hook adds no Redis command: the reads are the existing `_is_serper_key_exhausted` calls), H1's bare `raise` re-raises the same exception object with its traceback (no new frame), /health unchanged until an outcome is recorded. Store binary 683f56c0 / OTA f1e20c39 read only `status` of /health (SmartCompareApp/src/services/api.ts:531-534 per the spec; not re-measured here because no client file moves).
- NEW public surfaces: /health gains `llm_credential` and `serper_keys` and the new GET /health/llm; both are unauthenticated and disclose "the AI credential is rejected / out of quota" to anyone (the brightdata_auth precedent, main.py:333-337, is the same class and was ruled deliberate). Record the disclosure in the CLAUDE.md row.
- With today's dead credential, merging before N1 makes EVERY deploy and restart emit one error event on its first compare: the owner is paged per deploy until N1 (intended, PP3; say it in the READY TO MERGE delta).
- R2: the alert event carries the scrubbed request region unless C1 (i) is taken.
- The probe (DARK) has the R3 / R4 hazards until B2 / B3 are ruled; no production effect while the flag is unset.

## 5. Pin collisions not in spec 4.1 / 1.9

- tests/test_backend_cleanup.py:61-77: main.py source must not contain "comparison_service" / "from app.api.routes" (R8, C4). No E-row if GREEN avoids the substrings.
- tests/test_shutdown_drain.py:689-743 and tests/test_retro_w1_7_w1_10.py:277-288: the shutdown-name readers (listed in 1.9 for the order; P10 must reuse the duck-typed reader, C5).
- tests/test_retro_w1_7_w1_10.py:111-125: the autouse fixture snapshots every app.main global whose name starts with `_loop_lag` (the spec already forbids the prefix; keep `_llm_probe_task` as named).
- No other collision found: the U3c SDK surface, the Anthropic Messages surface, G13 direct-guarded-call walker (test_s81_s06_router_gate_rows.py:843-856), the U8d R8 ERROR-call walker (test_sentry_channels_u8d_unit.py:830-844), the 5xx-HTTPException detail walker (:1003-1022: the monitor returns a JSONResponse, never an HTTPException), the LoggingIntegration census (test_auth_error_log_hygiene.py:565-583), the legal services scanner (test_legal_docs_u8.py:829-856), the _LEDGER walker (test_s81_s03_llm_ledger_v2.py:507-523) and the curl cap walker read nothing the new modules add, provided the contract's no-URL / no-constructor / no-logger.error rules hold.

## 6. Defect-class checklist (the task's list)

- Vacuous PIN rows: P01 as written (R5, B4). G02 / G03 / S04 / S05 / HE02 run with the full configuration per 5's preamble: not vacuous.
- Mutants no row kills: MU15 (no target, R5); a "probe success clears quota" mutant (B2) and a "quota by type ignored" mutant (B1) have no row today.
- Comm set: the conftest edit makes it the whole tree (7.2); correct and sufficient.
- Flag-OFF identity of the probe: pinned only after B4 (P01 through tick()).
- Unflagged delta beyond 2.11: none beyond R2 (request region on the event) and the disclosure note.
- Response keys removed / renamed / retyped: none.
- New path meeting middleware / limiter / allowlist: measured and holds (RequestID HOP list is an exact match, request_id.py:14 / :80; SlowAPIASGI absent in production and the route exempt; no auth allowlist exists in app/middleware).
- Background task outliving shutdown: no (cancelled before the drain; not in _BACKGROUND_TASKS).
- Credential / prefix / exception text reaching a log, event, tag or /health: none in the new lines; the pre-existing moderation WARNING with exception text (content_safety_service.py:269) stays (L-6).
- Alert per call vs per change: per change, latched (C7 names the silent re-failure).
- Codeless 503: avoided (explicit code in a returned JSONResponse).
- S81-04c overlap: none.
- Stated limit that is a defect: L-4's "assumed to surface as insufficient_quota" (R1, B1).
- PROOF ON THE PHONE that passes while the problem remains: PP5 (R6, C2); PP2 proves only the rule, not that a second outage pages (C6).

## 7. Q8 (R-MON1-10) re-read of the official documentation, 2026-11-11

- Anthropic rate limits (https://platform.claude.com/docs/en/api/rate-limits): limits are stated for the Messages API, Message Batches, Managed Agents, the Files API and fast mode; the Models API is not listed; the spend cap is enforced on the Messages API. Anthropic errors (https://platform.claude.com/docs/en/api/errors): 401 authentication_error, 402 billing_error, 403 permission_error, 429 rate_limit_error (also the tier spend cap), 400 for a user-set spend limit.
- OpenAI rate limits (https://developers.openai.com/api/docs/guides/rate-limits): GET /v1/models appears only as a troubleshooting step; no limit or price is stated for it. OpenAI error codes (https://developers.openai.com/api/docs/guides/error-codes): the billing / spend / usage 429 codes of R1; the restricted-permission 401 of R4.
- Conclusion unchanged on cost (no price is stated for either metadata endpoint; 96 calls a day per provider is far below any stated limit; LIKELY, not ESTABLISHED; PP4 checks the console). Changed on coverage: the metadata call detects an authentication failure only, never a quota or spend-cap state (R3, B2).

## 8. Questions for the orchestrator

1. B1: adopt the five-code set plus the type check as the OpenAI quota rule (and freeze it in L02)?
2. B2: a probe success clears only `rejected` (401-sourced or probe-sourced), never `quota` or a dispatch-sourced 403: rule it?
3. B3: (a) the owner precondition "the key carries the Models read permission" on the O3 window, or (b) the recorder rule that a probe-only 401 never overrides a fresh dispatch ok?
4. C1: clear the request region from the alert event (a measured scope recipe + SE04), or amend the brief to accept the scrubbed region?
5. C2: the uptime monitor (O2) only from the probe window, as a keyword monitor on `"openai": "ok"`? Until then the Sentry event is the only alarm.
6. C6: which Sentry rule trigger does the owner set (issue frequency with an action interval, or resolve-on-recovery with the regression trigger)? It decides whether a second outage pages.
7. C7: keep the per-process latch with the silent re-failure as a stated limit, or a per-transition event with a cool-down?
8. The incident report's S7 row asks for "one manual trigger of the alert sender" as part of the proof; the brief's section 4 and the spec replace it with the Sentry rule's own test notification (PP2), which never exercises the app's sender or the tag match. Is an owner-run trigger wanted (for example an X-Admin-Key-gated admin route that calls capture_credential_alert once; a new route, so a FOCUS addition), or does PP3 / a hermetic SE row suffice?
9. OQ-4 of the spec (UNIT_ENV of the FY25 identity node): agree with leaving ENABLE_LLM_CREDENTIAL_PROBE out (it is read only by the lifespan task)?

## 9. Not done in this review

- No test, gate, mutant or probe ran (READ-ONLY round). The sentry-sdk request-processor finding (R2) is by reading the pinned source; SE04 measures it.
- The vendors' statements on the Models endpoint are by omission (no page says "free" in words); R3 / R4 rest on what the pages say about the billed endpoints and the 401 cause list, not on a live account.
- No scratch worktree or scratch copy was created; the only file written in the worktree is this review (under the gitignored .qa-s80/).
