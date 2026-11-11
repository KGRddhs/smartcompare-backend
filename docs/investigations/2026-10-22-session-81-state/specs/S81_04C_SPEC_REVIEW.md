# S81-04c REFUSAL-LOG-HYGIENE - ADVERSARIAL SPEC REVIEW (lens 1: correctness / refutation)

- Spec: .qa-s80/S81-04c_UNIT_SPEC.md, sha256 5d052c5a3171d2a28e261f00fdcaf926060bf4ec580293c2915ffb45e74ff4d2 (re-hashed first: match).
- Base: a74caba7e3ff66b12e94178c912197c845ccbd14 (worktree HEAD verified; git status clean apart from the gitignored .qa-s80/).
- Method: every cited file:line re-read at the base with read-only commands; no pytest was needed for the findings below (no app or test file edited, no scratch copy kept).

## Verdict: APPROVE_WITH_CHANGES

The design holds: option (1) as ruled, the census (15 routed sites, re-counted by grep of `_llm_router.route(` over app/: exactly 15 keys, no direct `guarded_llm_create` caller), the eight arms, the read-order argument, the delivery identity, the refund latches and the Sentry measurement all re-measure true. No blocking design defect. Five corrections are needed before RED is frozen (C1-C5); two of them would otherwise produce a false RED/PIN or a CI red at GREEN.

## Re-measured TRUE (spot list)

- extraction_service arms: A1 :1570-1577, B1 :1738-1740, B2 :1790-1792, B3 :1845-1847, B4 :1902-1904, A2 :2810-2820 (inner :2697, the matcher :2702-2706 re-raises at :2736 `else: raise`). Bytes as quoted.
- url_extraction_service A4 :983 / :988-990 / :993-994; image_routes A3 :390-413 (refunds :398-399, 503 / 500 :408-413).
- LLMUnavailableError :706 is a RuntimeError subclass; raise sites api_budget_service :1009, llm_spend_breaker :1050 / :1229, openai_service :508, image_routes :386, llm_router subclasses as listed. No other `raise ...LLMUnavailableError` in app/.
- The two camera refund latches are mutually exclusive: `_refund_anon_credit` needs `anon_credit_refundable`, set only under `anon_usage_gate_enabled() and not user` (image_routes.py:239-254); `_refund_reserved_credit` needs `usage_user_id` (:296, :311). M21 is a true equivalent mutant.
- The verdict 429 matcher (:2702-2706) does not match either production message: W1-3 "openai circuit breaker denied admission <U+2014> dispatch suppressed", spend `REFUSAL_MESSAGE` "llm spend cap reached for lane %s; dispatch suppressed" (llm_spend_breaker.py:183). So A2 receives the class unchanged.
- Production state: ledger line 316 (2026-11-07 06:22) lists none of ENABLE_LLM_PREFLIGHT_BREAKER / ENABLE_VISION_IDENTITY_V2 / ENABLE_LLM_SPEND_BREAKER / any ENABLE_ANTHROPIC_* on web; no later dated line flips one (348, 366 = the judge service, 409, 413 re-checked). The judge imports api_budget_service / llm_router / llm_spend_breaker but none of the three edited modules.
- Ledger 417 / 418 / 419 support every lagging-row replacement of section 8 (g) (300 rows, over_cap_brands 42, not_built=0 redis=1, step 0 answered 200).
- sentry_service.py:738 `LoggingIntegration(level=logging.ERROR)`; sentry-sdk==2.68.1 at requirements.txt:155.
- u8d R8 scans: the in-except template rows name other prefixes; the outside-except scan uses the ExceptHandler ancestry (`_inside_except`), so an `else:` nested in the handler stays "inside". test_s70 source-scanning rows check only the import identity of exc_summary. No pin counts `logger.error(` or the `any_role_enabled() and isinstance` form.
- tests reading the changed prefixes: only test_s70_exc_summary_logs, test_s80_b3_vision_identity_v2, test_s80_url_mode_v2 and test_s81_s06_router_gate_rows (grep over tests/). The wider set that combines a class source with an ERROR assertion (s10 :2098, s20 :1187, s16b, s22, text_error_envelope test_03) asserts on other paths / non-class exceptions; none reads an arm in scope for a class member.

## Refuted claims

1. Section 1.8 "None is in .github/black-clean-paths.txt" is true for the three app files but the unit ALSO edits tests/test_s81_s06_router_gate_rows.py (E1), which IS on that list (.github/black-clean-paths.txt:63) and is checked by the BLOCKING `black --check` step of .github/workflows/ci.yml:172-188 (black==26.5.1, requirements-dev.txt:3). Section 7 gate 1 omits it: an E1 body written as in 4.1 (long `assert ... and ... and ...` lines) can turn CI red.
2. Section 4.1 E1: "`assert out == ({"products": [], ...}, {...})` (out from the `_capture` tuple)". `_capture` returns `("ok", value)` (tests/test_s81_s06_anthropic_router.py:321-328) and `run_site` returns `(oai, res)` (the `return oai, res` of run_site, :573 onward). So the `_capture` value is `(oai_calls, (parse_dict, usage))`, not the parse tuple; the assertion as literally written fails at GREEN. It must unpack `st, (oai, res) = _run(_capture(run_site(...)))` and assert `st == "ok"` and `res == (...)`.
3. Section 9 L1 / section 11 Q2 cite only the sync compare-entry short-circuit WARNING (structured_comparison_service.py:4152-4157). The streaming entry has its own twin at :4964 (`[CIRCUIT] openai breaker OPEN -- short-circuiting streaming ...`). The statement "an operator sees ... the compare-entry OPEN WARNING" is incomplete, and the proposed S81-04e `query=%r` follow-up must name both lines.
4. Section 8 (g) "Store state: ... NO sentence states 1.0.0 (3) as approved-not-released" is true for that regex, but R-04C-9 (f) also names "the first OTA reaches installs". CLAUDE.md:195 (the `api.ts` bullet) says S81-08 "reached phones with the first production OTA, 2026-11-07 16:10 AST": false as dated (the store version was Pending Developer Release until the owner's release 2026-11-10 ~02:35, ledger lines 415-416; no store install ran it on 2026-11-07). The spec's regex had no `reached phones` term, so it missed this lagging sentence. CLAUDE.md:592 ("App Review approval of the build in review") is a second stale store-state phrase (a met precondition worded as present tense); Q-D covers it only implicitly.

## Corrections (required before RED is frozen)

- C1 (refuted 1): section 7 gate 1 adds `black==26.5.1 --check tests/test_s81_s06_router_gate_rows.py` (the CI step's exact form) at GREEN and at every rebase; section 1.7 lists the ratchet as a guard; section 4.1 lists it as a pin collision of E1.
- C2 (refuted 2): rewrite the E1 body with the explicit unpack (`st, (oai, res) = ...; assert st == "ok"; assert res == ({"products": [], "error": es.PARSE_PRODUCT_QUERY_ERROR}, {"prompt_tokens": 0, "completion_tokens": 0})`). Keep the existing record assertions; never weaken.
- C3 (R7 vacuity): as written, R7 at HEAD passes on `n == 0` also when the child's Sentry transport never fires (init_sentry returned early, a before_send drop, a DSN parse change). Add a positive control in the SAME child run: after the parse arm, `logging.getLogger("s04c.marker").error("s04c marker")` and assert exactly one event whose message is the marker and zero events whose message starts with "Product parsing error". Count by prefix, not the total (an unrelated ERROR in the child must not turn the row red at GREEN). R7 then cannot pass vacuously and cannot fail on noise. Also note the 1.6 probe ran with `default_integrations=False`, not the real init; R7 (real `init_sentry()`) is what proves the production path, so keep it (answer to Q-E: keep it RED with the control).
- C4 (synthetic message text): every synthetic exception text used at the verdict arm (R3 / P1 / P2 / P3 rows) must avoid the substrings "429", "rate" and "quota" (case-insensitive) because the verdict matcher (:2702-2706) would then run the fallback dispatch, adding a second create call and a second class raise / record order the rows do not model. The current texts ("synthetic sub refusal text", "synthetic plain failure text") are clean; state the constraint so RED does not pick e.g. "generated" / "separate" / "accurate" (all contain "rate").
- C5 (P3 / P4 exact counts under the FULL config): the 1.3 probe does not state that it ran under the FULL configuration of 2.5 (ENABLE_REQUEST_CONTEXT_HEADERS=true, ENABLE_SONNET_ESCALATION=true, the ANTHROPIC_* knobs). P3 hard-codes "A3 exactly two reads" and "A1/A2/A4 exactly one". Either (a) RED re-measures the sequences under the FULL config at the base and freezes the measured literals (preferred), or (b) P3 asserts equality with a base-recorded sequence captured by the same harness. A PIN that is red at base under FULL config is a RED defect.

## Blocking issues

None in the design. C1 and C2 are must-fix before GREEN (CI red / a failing E-row otherwise); C3 before RED is frozen.

## Contract risks

- None to the build-3 contract: no key, status, envelope or SSE frame changes; the camera coded 503 (`LLM_UNAVAILABLE`) and the 500 literal are untouched; no codeless 503 is added (the error-handler mapping is not involved).
- Billing (R-A3): unchanged. The camera vision arm refunds at most once per request through the latches; P4 / P5 pin it. Note P5 pins the anon arm in a non-production state: ENABLE_COMPARE_AUTH_REQUIRED is ON on web (ledger 316) and `require_paid_route_user` (image_routes.py:205) refuses an anonymous camera call before the arm; the row is still valid as a pin of the code path, state it as such.
- ENABLE_CAMERA_FAILURE_ENVELOPE is ON on web (ledger 316); it acts only after the compare (image_routes.py:728, :773), not in the vision arm, so no interaction; the FULL config may add it for production fidelity (optional).
- L2 (B1-B3 return `{"error": str(e)}` with the em-dash message): pre-existing and out of scope, but "not re-measured" is not a stated limit; either measure whether a degraded specs / price dict's `error` reaches a response body at the base, or give it a follow-up id (it is a raw-exception-text-in-body question, the U8d class).

## Pin collisions

- .github/black-clean-paths.txt:63 (tests/test_s81_s06_router_gate_rows.py, BLOCKING black --check in ci.yml) - not in section 4.1 (C1).
- T23 OpenAPI, FY25 digests, w4_11 prompt-render digests, test_retro_w2_1 URL pins, the W4-13 ledger fixture, the copy-policy fences: no collision (log statements only; no prompt, route, schema, URL or copy byte moves).
- tests/test_s80_b3_vision_identity_v2.py:1498-1539 ALLOWED_ERROR_PREFIXES: stays green (fewer ERROR records), as the spec says.
- tests/test_s80_url_mode_v2.py:2772-2778: a ValueError row, unchanged, as the spec says.

## Questions for the orchestrator

1. Q-A (group B): the R-04C-2 census rule puts B1-B4 in scope; this reviewer found no reason to carve them out (they are the same W1-3 / spend path, and their base ERROR is a Sentry event in every flag state). Confirm group B, accepting L4 (the role-ON record also changes at those four arms).
2. Q-B (statement form): the `elif` duplicate keeps the S81-06 lines byte-identical and the read first and unconditional; the alternative (a named unused read) changes those lines. This reviewer prefers the `elif` (ruled form + SIM114 report-only).
3. Rule C3: keep R7 RED with the positive-control marker and prefix counting (proposed), or demote it.
4. R-04C-9 (f): rewrite CLAUDE.md:195 ("reached phones with the first production OTA, 2026-11-07") with the dated truth from ledger 416 (released 2026-11-10 ~02:35; the OTA reaches a new install on its second launch), and date the met "after App Review approval" / "the build in review" preconditions (:592 and the Q-D list)? Neither is in the spec's edit list.
5. L2: measure at base whether a B1-B3 `{"error": str(e)}` reaches a response body, or assign a follow-up id; which?
6. Should the S81-04e follow-up (Q-C) cover both compare-entry OPEN WARNINGs (scs :4152-4157 and :4964)?
