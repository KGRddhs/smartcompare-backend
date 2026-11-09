# S81-G11 brief: the classification (no launch)

Written 2026-11-09 by the session-90 orchestrator; orchestrator Opus 5.5 by the owner's start of the relay's S90 card. Scope of the session: the group G11 only = S81-04c + S81-24c, each classified here before any launch. The session's rule: a unit is SAFE only if it is small, adds no flag, touches no migration and no quota / consent / legal / auth-contract surface, and changes nothing a user or an operator alert would see in production today; any doubt = FOCUS.

Everything below was measured at origin/main a74caba7e3ff66b12e94178c912197c845ccbd14 with `git -C <clone> show a74caba7:<path>` and `git -C <clone> grep ... a74caba7` (no worktree, no checkout, no CLAUDE.md injection). Line numbers are at a74caba7.

## S81-04c: CLASSIFIED FOCUS (not run; the Fable session)

The DEFECT_LEDGER row (R-S04-10): downgrade the exc_info ERROR logs that an LLMUnavailableError refusal hits in extraction_service / image_routes / url_extraction_service; log hygiene, R-A1 (b), no flag.

### The four log arms

| Arm | Every role flag OFF (production today) | Any role flag ON (S81-06 GC-3, already WARNING by type) |
|---|---|---|
| extraction_service.parse_product_query | `:1576` `logger.error(f"Product parsing error: {e}", exc_info=True)`, then the parse-error dict | `:1573-1574` WARNING by type |
| extraction_service.generate_comparison (verdict) | `:2819` `logger.error(f"Comparison generation error: {e}", exc_info=True)`, then the error dict (the base delivery) | `:2816-2818` WARNING by type + re-raise (R-S06-2, the coded 503 LLM_UNAVAILABLE) |
| image_routes camera vision arm (non-delivery exit 1 of 6, both refunds, then 503 / 500) | `:396` `logger.error(f"[IMAGE] Vision call failed: {e}")` (the exception text, no exc_info) | `:393-394` WARNING by type |
| url_extraction_service AI extraction | `:993` `logger.error("AI extraction error: %s", type(e).__name__)` (by type, no exc_info), then `{"error": str(e)}` | `:988-990` WARNING by type + re-raise (R-S06-3) |

### Q1: can the downgraded lines fire in production while ENABLE_LLM_SPEND_BREAKER is unset?

Every raise site of LLMUnavailableError and its subclasses in app/:
- `app/services/api_budget_service.py:1009` (guarded_llm_create: the W1-3 preflight denial), only under `ENABLE_LLM_PREFLIGHT_BREAKER`; reaches all four arms (every arm dispatches through guarded_llm_create via `_llm_router.route`).
- `app/services/llm_spend_breaker.py:1050` / `:1229` (the S81-04 refusal, `REFUSAL_MESSAGE` at `:183`), only under `ENABLE_LLM_SPEND_BREAKER`; each logs its own `[SPEND] ... dispatch refused` / `reservation refused` WARNING first.
- `app/services/openai_service.py:508` (`_identify_products_v2`: "vision returned no content"), only under `ENABLE_VISION_IDENTITY_V2`; reaches the camera arm.
- `app/services/llm_router.py` (the S81-06 subclasses) and `app/api/image_routes.py:386` (ConsentUpdateRequiredError), only under a role flag; `route()` with the role flag OFF is the exact base call (`llm_router.py:1086-1090`).

So without the spend flag, an LLMUnavailableError reaches the role-flags-OFF arm of all four lines through ENABLE_LLM_PREFLIGHT_BREAKER and of the camera line through ENABLE_VISION_IDENTITY_V2. Production: neither flag is in the web ON list of the dated 2026-11-07 06:22 values read (ledger line 316; every S81 flag unset there) and the only web flip filed since is item 32 (ENABLE_LEGACY_FINGERPRINT_READER, 2026-11-07 09:00). The judge service sets ENABLE_LLM_SPEND_BREAKER=true, but scripts/cron_compare_judge.py imports none of the three modules (its lazy app imports: result_gate, prompt_sanitizer, llm_spend_breaker, llm_router, model_config, llm_pricing, api_budget_service). ANSWER: not today, by the dated record; yes the moment either non-S81 flag flips. The class-keyed downgrade the row defines is NOT confined to the spend breaker, and its inertness today rests on a dated read, not on the code.

### Q2: does any alerting key on them?

In the repo, no: the four texts appear only at their sites, in the retired backend/ copy, in docs, and in three test files (tests/test_s81_s06_router_gate_rows.py G03a-G03d; tests/test_s80_b3_vision_identity_v2.py:1498 ALLOWED_ERROR_PREFIXES; tests/test_s80_url_mode_v2.py:2775, a ValueError row). The S81-04 canary (CLAUDE.md, the ENABLE_LLM_SPEND_BREAKER row) counts the breaker's own [SPEND] lines and the 503 count; the W1-3 and vision-V2 rows count none of the four. But every one of the four lines is a Sentry event by construction: `sentry_service.init_sentry` passes `LoggingIntegration(level=logging.ERROR)` and keeps the SDK's default event level ERROR (a WARNING is neither an event nor a breadcrumb). The Sentry project's alert rules live outside the repo: NOT establishable from the code.

### Further doubts

1. The unit reverses a frozen PIN that the two-adversary S81-06 chain set on purpose: `tests/test_s81_s06_router_gate_rows.py::test_g03c_flag_off_parse_site_keeps_the_base_error_line` (role flags OFF, the FULL config, an LLMUnavailableError at the parse arm keeps the exc_info ERROR line, bytes unchanged).
2. The verdict and url arms sit directly after the S81-06 consent / dispatch non-delivery re-raise; the camera arm sits inside the refund exit (a quota-path block).
3. A spend-only cut that is inert by construction while the flag is unset needs a design the row does not make: a refusal predicate or subclass in llm_spend_breaker.py / api_budget_service.py, or an arm gated on `spend_breaker_enabled()` that couples the W1-3 / vision-V2 refusals to the spend flag. A class-wide downgrade later would supersede it.

### Classification

FOCUS by the doubt rule (Q1 reaches beyond the spend breaker through two non-S81 production flags; Q2 cannot be closed from the code; doubts 1-3). Not run. For the Fable session, names only, no ruling here: option (1) the class-wide downgrade per R-S04-10: the role-flags-OFF branch of all four arms logs a WARNING by type, deliveries / refunds / status mapping byte-identical, G03c re-pinned as an E-row, CLAUDE.md's S81-04 stated limit (9) rewritten in place and the W1-3 / vision-V2 rows gaining the sentence; option (2) a spend-only cut (G03c stays green: the S06 FULL config sets no spend flag). Tests that name the class beside a log assertion (the E-row candidates): tests/test_s80_b3_vision_identity_v2.py, tests/test_s81_s04_spend_breaker.py, tests/test_s81_s06_anthropic_router.py, tests/test_s81_s06_router_gate_rows.py, tests/test_s81_s16_kb_seed.py, tests/test_s81_s22_judge.py. Still recommended before the owner's ENABLE_LLM_SPEND_BREAKER canary.

## S81-24c: test-only (SAFE by LC-1), NOT LAUNCHED

The unit: retire the string-presence limiter tests that S81-24's AST pins now cover, keeping any assertion no AST pin covers (R-S24-10). It has no DEFECT_LEDGER row before this brief; the row is added with this classification.

What the AST pins cover: `tests/test_s81_s24_auth_throttle.py::test_p80_decorator_table_ast` (the fifteen decorated auth_routes.py routes with their rates, the six undecorated routes, and `_EXPIRED_LOGOUT_BUDGET = parse_rate_limit('10/minute')`) and `::test_p81_decorator_order_ast` (the limiter decorator directly after the router decorator on all fifteen). By the S81-24 spec's 4.2 list (anchors at daf86d32, not re-measured at a74caba7), the auth_routes string assertions they cover sit in test_account_deletion_u8b.py (delete_account), test_attribution_endpoint.py (/attribution), test_auth_demographics.py, test_password_reset_deep_link.py (password_recovery), test_retro_w1_9.py (the attribution rate) and test_security_regression.py (the auth substrings and demographics). The admin and text_compare rows of test_security_regression.py are not covered and stay. The rest of the eighteen files hold runtime, patch or comment uses, not string-presence tests.

RULING: it does not merit its own PR. It is a dedup of about eight assertions in about six test files. It changes nothing in production, and nothing waits on it (S81-24b is BLOCKED on the spoof probe; S81-24d is FOCUS). It also removes redundant guards on an auth surface. A full SAFE chain for it alone costs about 2M agent tokens with the weekly allowance at 86 pct. It folds into S81-24b's chain, where the same decorators and the m13_02 pin move. Not run.

## Outcome

G11 closes without a launch: no worktree, no workflow, no PR; origin/main stays a74caba7. NEXT_SESSION_PROMPT_S91.md puts S81-04c first in the Fable session's queue, with this file as its brief input.
