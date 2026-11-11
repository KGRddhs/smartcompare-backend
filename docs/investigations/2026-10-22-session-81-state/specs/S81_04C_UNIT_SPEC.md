# S81-04c REFUSAL-LOG-HYGIENE - UNIT SPEC

- Unit: S81-04c REFUSAL-LOG-HYGIENE (FOCUS; R-04C-10). Class: log-only under R-A1 (b) (R-S04-10, R-04C-1).
- Flag: NONE. No new flag, no knob, no new env name (R-04C-8). The invariant that replaces flag-OFF identity is section 2.4.
- Worktree: C:/Users/SynAckITPC/Documents/AI/sc-s81-s04c (detached at the base, read-only for the spec writer).
- Branch (GREEN creates it): feature/s81-refusal-log-hygiene
- Base sha (every measurement): a74caba7e3ff66b12e94178c912197c845ccbd14 (origin/main, #398 S81-G10).
- git status --short: empty before the first probe and after the last (only the gitignored `.qa-s80/` holds this spec and the probe file `.qa-s80/s04c_probe/test_s04c_base_probe.py`, deleted at the end of this run).
- Measurement location: <scratchpad>/S81-04c/ (probe_base.json, probe_base.log, base_a.log, base_b.log, probe_sentry.py/.out, comm_set_candidates.txt).
- Evidence pointers: specs/S81_04C_BRIEF.md (R-04C-1..11, Q1-Q6; binding), specs/S81_G11_BRIEF.md (the S90 classification), specs/RULINGS_S81_04.md R-S04-10, specs/RULINGS_S81_06.md R-S06-2 / R-S06-3 / R-S06-12 (GC-3), PLAN_S80.md section 0 (contract freeze) + section 1 (R-A1, R-A13, R-A15), DEFECT_LEDGER row S81-04c, session-81 ledger lines 316 (the dated flag read) and 415-420 (the 2026-11-10 relay / ops lines).
- Sister units / contracts: S81-04 SPEND-BREAKER (the `[SPEND]` refusal lines, the canary; CLAUDE.md:495 limit (9)); S81-06 ANTHROPIC-ROUTER (the role-ON WARNING-by-type branches, GC-3, the frozen G03c pin this unit re-pins as E1; G10 / G10b; G13 the AST census); W1-3 (ENABLE_LLM_PREFLIGHT_BREAKER, the api_budget_service raise); B3 (ENABLE_VISION_IDENTITY_V2, the no-content raise); S69 U7 (the camera 503 mapping); W4-9 / S70 OAI_OBS (the constant `error` markers and the exc_summary templates, pinned by tests/test_w49_extraction_catch_redaction.py and tests/test_s70_exc_summary_logs.py, both stay green); U8d (Sentry LoggingIntegration level ERROR). Known rebase: S81-12 draft PR #378 (HELD) unions CLAUDE.md and tests/test_s81_s06_anthropic_router.py (this unit does not edit that file; disjoint CLAUDE.md hunks).
- Personal-data rule: no personal value in any file, test, fixture or log line; synthetic values only (`s04c-...` user ids, `example.test` addresses, run-time-built strings). The repo is public.

## 0 What the unit does

`api_budget_service.LLMUnavailableError` (api_budget_service.py:706) is the typed "no dispatch / no content" outcome of the LLM chokepoint. With every role flag OFF (production) the request-path except arms that catch it log it at ERROR (four with the exception text, two of them with `exc_info=True`): one Sentry event per refused dispatch (sentry-sdk 2.68.1, `LoggingIntegration(level=logging.ERROR)`, Q3). S81-04c makes every request-path except arm the census (1.3) proves reachable by a class member log ONE WARNING `"<the arm's existing prefix>: %s", type(e).__name__` (no `exc_info`, no exception text, the subclass's own name) in every flag state, and changes nothing else: return values, re-raises, refunds and their order, status mapping, envelopes, SSE frames, the `any_role_enabled()` read count and order, and every log record of a non-class exception stay byte-identical.

The census widens the brief's four arms by four: the specs, price, price-fallback (training-data) and reviews arms of extraction_service catch a class member on the same W1-3 / spend path and log ERROR with the text in EVERY flag state (measured, 1.3). R-04C-2 puts them in scope ("every other arm the census proves reachable ... that logs at ERROR"); because they have no role-ON branch at base, their change applies in the role-ON state too (question Q-A in section 11 lets the orchestrator carve them out; every row for them is tagged group B so the carve-out is mechanical).

## 1 Base state (MEASURED at a74caba7)

### 1.1 The class and its raise sites (R-04C-2 (a))

| Raise site | Line | Gate (read per call) | Own log line BEFORE the raise | Reaches |
|---|---|---|---|---|
| `api_budget_service.guarded_llm_create` W1-3 denial | :1009-1011 (`raise LLMUnavailableError("openai circuit breaker denied admission \u2014 dispatch suppressed")`, the message holds an em dash U+2014) | `llm_preflight_breaker_enabled()` :715-721 (`ENABLE_LLM_PREFLIGHT_BREAKER`) | NONE at the denial (`_openai_dispatch_admission` :799-827 returns (False, False, False) silently on OPEN-in-cooldown; `is_circuit_closed` :526-590 returns False silently on a spent half-open slot) | every dispatch site through `_llm_router.route(...)` (15 sites) |
| `llm_spend_breaker._refuse_dispatch` | :1050 (`REFUSAL_MESSAGE % lane`, :183) | `spend_breaker_enabled()` (`ENABLE_LLM_SPEND_BREAKER`) via `admit_openai_dispatch` at api_budget_service.py:997-1001 | `[SPEND] lane=%s cap reached (...) -- dispatch refused` WARNING :1043-1049 | every dispatch site |
| `llm_spend_breaker.reserve` | :1229 | the same flag (scripts + the router's spend admit) | `[SPEND] ... -- reservation refused` WARNING :1223-1228 | scripts/cron_compare_judge.py, scripts/seed_kb_batch.py, llm_router._spend_admit (role ON) |
| `openai_service._identify_products_v2` no content | :508 | `vision_identity_v2_enabled()` (`ENABLE_VISION_IDENTITY_V2`) | `[VISION_V2] no content: finish_reason=%s refused=%s` WARNING :503-506 | the camera arm only |
| `llm_router` subclasses (defined :235-:274: ConsentUpdateRequiredError, AnthropicNotConfiguredError, AnthropicShapeError, AnthropicDispatchError, AnthropicRefusalError, AnthropicBreakerOpenError) | raises :588, :600, :671-:731, :942, :958, :1001, :1021, :1100, :1112, :1134 | a role flag ON only (`route()` with the role OFF is the exact base call, :1086-1090) | `[ROUTER] ...` INFO at :1094-1099 for the consent refusal | the four role-ON arms |
| `image_routes` camera gate | :386 (`raise _llm_router.ConsentUpdateRequiredError()`) | `camera_refuses_for_consent()` (a role flag ON only) | none | the camera arm |

scripts/: `cron_compare_judge.py:678` and `:737` and `seed_kb_batch.py:518` catch the reserve refusal and count it / `_say(...)` it; none logs the class at ERROR -> unchanged (R-04C-2).

### 1.2 The dispatch census (15 routed sites; G13's frozen key set) and the arm each class member reaches with every role flag OFF

| # | Site key | Dispatch | Except arm (file:line) | Level / exc_info / form at base | Delivered | Class reachable in prod code (path) |
|---|---|---|---|---|---|---|
| 1 | classify | extraction_service.py:1404 | :1417-1421 | WARNING, f-string with `{e}` | `"other"` | yes (W1-3 / spend); WARNING already -> OUT (not ERROR), listed in 9 L5 |
| 2 | parse | :1544 | :1570-1577 | role OFF: ERROR + exc_info, `f"Product parsing error: {e}"` (:1576); role ON + class: WARNING by type (:1573-1574) | `({"products": [], "error": PARSE_PRODUCT_QUERY_ERROR}, zero usage)` | yes -> IN (arm A1) |
| 3 | specs | :1607 | :1738-1740 | ERROR, `"Specs extraction error: %s", exc_summary(e)` (type + scrubbed text), no exc_info, EVERY flag state | `({"brand", "model", "error": str(e)}, zero usage)` | yes -> IN (arm B1, group B) |
| 4 | price | :1766 | :1790-1792 | ERROR, `"Price extraction error: %s", exc_summary(e)`, every flag state | `({"amount": None, "currency", "error": str(e)}, zero)` | yes -> IN (B2) |
| 5 | price_training | :1815 | :1845-1847 | ERROR, `"Price fallback error: %s", exc_summary(e)`, every flag state | as B2 | yes -> IN (B3) |
| 6 | reviews | :1877 | :1902-1904 | ERROR + exc_info, `f"Reviews extraction error: {e}"`, every flag state | `({"average_rating": None, "error": REVIEWS_EXTRACTION_ERROR}, zero)` | yes -> IN (B4) |
| 7 | verdict | :2680 | inner :2697 (re-raises a non-429 error: the class message holds no "429" / "rate" / "quota", measured), outer :2810-2820 | role OFF: ERROR + exc_info `f"Comparison generation error: {e}"` (:2819); role ON + class: WARNING by type + `raise` (:2816-2818) | OFF: `({"winner_index": 0, "error": COMPARISON_GENERATION_ERROR}, zero)`; ON: re-raised | yes -> IN (A2) |
| 8 | verdict_fallback | :2722 | inside the inner except; any raise lands in the same outer arm :2810 | as #7 | as #7 | yes (a 429 then a W1-3 trip) -> covered by A2 |
| 9 | image_tier3 | image_service.py:187 | :195-197 | WARNING `"[image] Tier 3 GPT extraction failed: %r", e` | `None` | yes; WARNING -> OUT (9 L5) |
| 10 | vision_v2 | openai_service.py:477 | none in `_identify_products_v2` for the class (only `asyncio.TimeoutError` :487 logs + re-raises) | - | propagates | yes -> camera arm A3 |
| 11 | vision_v1 | :649 | none (`json.JSONDecodeError` only, :665) | - | propagates | yes -> A3 |
| 12 | specs_targeted | :768 | :787-789 | WARNING f-string `{e}` | fallback dict | yes; WARNING -> OUT (9 L5) |
| 13 | specs_synthesized | :843 | :860-862 | WARNING f-string `{e}` | fallback dict | yes; OUT (9 L5) |
| 14 | disambiguate | :905 | :954-956 | WARNING f-string `{e}` | fail-closed dict | yes; OUT (9 L5) |
| 15 | url_extract | url_extraction_service.py:960 | :983-994 | role OFF: ERROR by type `"AI extraction error: %s", type(e).__name__` (:993); role ON + class: WARNING by type + `raise` (:988-990) | OFF: `{"error": str(e)}`; ON: re-raised | yes -> IN (A4) |

Camera arm A3: image_routes.py:390-413: role ON + class WARNING by type (:393-394), else `logger.error(f"[IMAGE] Vision call failed: {e}")` (:396, the exception text, no exc_info); then `_refund_reserved_credit("usage_refund.image.vision_exception")` (:398) and `_refund_anon_credit("usage_refund.image.anon.vision_exception")` (:399) (the two latches are mutually exclusive per request: the authed reserve vs the anon debit, :232-254 / :300-337); then `HTTPException(503, {"code": "LLM_UNAVAILABLE", "error": LLM_UNAVAILABLE_FRIENDLY_MESSAGE})` for the class or a transient OpenAI error (:408-412), else the 500 literal (:413).

Caller arms that could see a class member AFTER a site (R-04C-2 "every chokepoint caller"):

| Arm | Line | Form | Reachable by a class member with every role flag OFF? |
|---|---|---|---|
| scs `_compare_from_text_impl` | structured_comparison_service.py:4894-4912 | role ON + class: WARNING by type :4897-4898; else ERROR + exc_info `f"Comparison error: {e}"` :4901 | NO: every site above swallows the class with role flags OFF (parse :1577, specs/price/training/reviews, verdict :2820, classify, tier3, targeted/synth/disambiguate); no dispatch runs before the impl's `try` (:4397; pre-try awaits :4312-4396 none); the vision sites are camera-only. Reached only through a patched seam (G10b patches `_parse_with_budget`). Unchanged. |
| scs streaming | :5805-5813 | as above, `"Streaming comparison error"` :5813 | NO (same argument; `try` at :5096). Unchanged. |
| scs `compare_from_text` wrapper | :4198-4204 | no log; flags OFF re-raise | NO (the impl swallows first). Unchanged. |
| image_routes post-identify compare | :787-788 ERROR + exc_info `"[IMAGE] Comparison failed after identification: {e}"` | NO (compare_from_text cannot raise the class with flags OFF, above). Unchanged. |
| url_extraction_service.compare_from_urls | :1391-1396 / :1466-1471 | no log | NO with flags OFF ("site 15 swallows it", :1393-1394; generate_comparison swallows, :1468-1470). Unchanged. |

### 1.3 The arms measured (the base probe, [pyt] tag=s04c-spec-probe elapsed=10s status=OK rc=0; 50 passed; [netguard] blocked 0; [hermeticity] sentinel checked 50)

Probe: `.qa-s80/s04c_probe/test_s04c_base_probe.py` run as `pyt.py --bound 600 --tag s04c-spec-probe --cwd <worktree> -- -p tests.conftest .qa-s80/s04c_probe/test_s04c_base_probe.py`; each arm driven through its REAL function with the REAL `guarded_llm_create`; kinds: `w13_denial` (ENABLE_LLM_PREFLIGHT_BREAKER=true + `_openai_dispatch_admission` patched to `(False, False, False)`: the production raise at :1009), `subclass` (a test-local `class _S04cSubRefusal(LLMUnavailableError)` raised by the fake `create`), `runtime_error` (a plain `RuntimeError`); "roleON" = `ENABLE_ANTHROPIC_CRITIC=true` + `ENABLE_OPENAI_PRE_V3=true` (any_role_enabled() True, every site still OpenAI); `any_role_enabled` wrapped by a recorder (R = a read, T/F its value). Records of the arm's logger only:

| Arm | kind / state | Sequence at base | Delivered at base |
|---|---|---|---|
| A1 parse | w13 OFF | R(F), ERROR exc_info `Product parsing error: openai circuit breaker denied admission \u2014 dispatch suppressed` | `({'products': [], 'error': 'product parsing unavailable'}, {'prompt_tokens': 0, 'completion_tokens': 0})` |
| A1 | w13 ON | R(T), WARNING `Product parsing error: LLMUnavailableError` | same tuple |
| A1 | subclass OFF / ON | R(F) ERROR exc_info `...: synthetic sub refusal text` / R(T) WARNING `...: _S04cSubRefusal` | same tuple |
| A1 | runtime OFF / ON | R ERROR exc_info `Product parsing error: synthetic plain failure text` (both states) | same tuple |
| A2 verdict | w13 OFF | R(F), ERROR exc_info `Comparison generation error: openai circuit breaker ...` | `({'winner_index': 0, 'error': 'verdict generation unavailable'}, zero)` |
| A2 | w13 ON | R(T), WARNING `Comparison generation error: LLMUnavailableError` | raised LLMUnavailableError |
| A2 | runtime OFF / ON | R ERROR exc_info `Comparison generation error: synthetic plain failure text` | the base dict (both) |
| A4 url | w13 OFF | R(F), ERROR `AI extraction error: LLMUnavailableError` (no exc_info) | `{'error': 'openai circuit breaker denied admission \u2014 dispatch suppressed'}` |
| A4 | w13 ON | R(T), WARNING `AI extraction error: LLMUnavailableError` | raised |
| A4 | runtime OFF / ON | R ERROR `AI extraction error: RuntimeError` | `{'error': 'synthetic plain failure text'}` |
| A3 camera (authed, metering ON) | w13 OFF | R(F) (bind_request_scope :453), R(F) (the arm), ERROR `[IMAGE] Vision call failed: openai circuit breaker ...` | 503, refunds `[(uid, None)]`, labels `['usage_refund.image.vision_exception']` |
| A3 | w13 ON | R(T), R(T), WARNING `[IMAGE] Vision call failed: LLMUnavailableError` | 503, same refund / label |
| A3 | v2_no_content OFF | R(F), R(F), ERROR `[IMAGE] Vision call failed: vision returned no content` | 503, same |
| A3 | subclass OFF / ON | ERROR `...: synthetic sub refusal text` / WARNING `...: _S04cSubRefusal` | 503 |
| A3 | runtime OFF / ON | ERROR `[IMAGE] Vision call failed: synthetic plain failure text` | 500, same refund / label |
| B1 specs | w13 OFF AND ON | NO read, ERROR `Specs extraction error: LLMUnavailableError: openai circuit breaker ...` (no exc_info) | `({'brand': 'Apple', 'model': 'iPhone 17', 'error': 'openai circuit breaker denied admission \u2014 dispatch suppressed'}, zero)` |
| B1 | subclass both | ERROR `Specs extraction error: _S04cSubRefusal: synthetic sub refusal text` | error = the text |
| B1 | runtime both | ERROR `Specs extraction error: RuntimeError: synthetic plain failure text` | error = the text |
| B2 price / B3 price_training | as B1 with `Price extraction error: ` / `Price fallback error: ` | NO read | `({'amount': None, 'currency': 'BHD', 'error': <str(e)>}, zero)` |
| B4 reviews | every kind, both states | NO read, ERROR exc_info `Reviews extraction error: <str(e)>` | `({'average_rating': None, 'error': 'reviews extraction unavailable'}, zero)` |

### 1.4 The flag-reader idiom and the module aliases

`llm_router.any_role_enabled()` (:329-332) = `any(_on(n) for n in ROLE_FLAGS.values())`, `_on` the house idiom (:312-313) read per call; extraction_service reaches it as `_llm_router.any_role_enabled()` (import :31), the class as `_llm_breaker.LLMUnavailableError` (`_llm_breaker` = api_budget_service, :30); url_extraction_service the same aliases; image_routes imports `LLMUnavailableError` from api_budget_service (:48-49) and `_llm_router` (:43). A recorder patching `llm_router.any_role_enabled` intercepts every caller (module attribute lookup at call time; llm_router's own `bind_request_scope` hits it too, hence the camera's two reads).

### 1.5 Libraries on the pinned venv

sentry-sdk 2.68.1 (requirements.txt:155; `sentry_sdk.VERSION` printed by the probe); Python 3.12 (.venv-qaren). No dependency change.

### 1.6 Sentry reach (Q3, MEASURED on 2.68.1, <scratchpad>/S81-04c/probe_sentry.py, run with `python -I`, a capturing Transport subclass, `default_integrations=False`, a synthetic DSN on an invalid host, no network)

`LoggingIntegration(level=logging.ERROR)` (sentry_service.py:738; comment :734-737) built `_handler.level == 40` and `_breadcrumb_handler.level == 40`. A WARNING record (`log.warning("Product parsing error: %s", ...)`) produced 0 events and NO breadcrumb (the marker event's breadcrumbs list held only the ERROR line); an ERROR record with exc_info produced 1 event (`level error`, `exception` present, `logentry.message` = the f-string text) and 1 breadcrumb. So: WARNING = neither an event nor a breadcrumb; ERROR (with or without exc_info) = an event. The camera's 503 itself is not a Sentry event either (`failed_request_status_codes = range(500,600) - {503}`, :724-733); the camera 500 is.

### 1.7 Guards the new code must not trip

- tests/test_s81_s06_router_gate_rows.py::test_g13_every_llm_site_dispatches_through_the_router (AST census of app/: 15 routed keys, no direct guarded call): no dispatch moves.
- tests/test_sentry_channels_u8d_unit.py R8 rows (in-except ERROR templates by prefix; the outside-except ERROR scan over scs + image_routes): the new calls are WARNING inside except arms; the kept ERROR calls keep their templates.
- tests/test_s70_exc_summary_logs.py (the three exc_summary templates, `record.msg` constant, no exc_info, return byte-identity) and tests/test_w49_extraction_catch_redaction.py (exc_info kept on the parse / verdict / reviews catches for a plain `Exception`): both drive NON-class exceptions -> must stay green unedited (they are R-04C-5 supporters).
- The verdict-fallback matcher: no message changes (R-04C-8).
- ruff blocking tier E9,F63,F7,F82; py_compile; the gitleaks keyword rule (no new constant named with key / token / secret / ...).
- Pure ASCII in every added line (the em dash of the W1-3 message is never typed into a test literal: build it with `chr(0x2014)` or match by type name).

### 1.8 Line endings

app/services/extraction_service.py, app/api/image_routes.py, app/services/url_extraction_service.py: `git ls-files --eol` = `i/lf w/crlf` (core.autocrlf). Edit with the Edit tool (preserves CRLF); a whole-file `git diff --stat` is a defect. None is in `.github/black-clean-paths.txt` (63 entries; measured).

### 1.9 The production state (R-A15)

The newest dated flag read is ledger line 316 (2026-11-07 06:22): ENABLE_LLM_PREFLIGHT_BREAKER, ENABLE_VISION_IDENTITY_V2, ENABLE_LLM_SPEND_BREAKER and every role flag unset on web; flips filed since: item 32 only (ENABLE_LEGACY_FINGERPRINT_READER). The judge service sets ENABLE_LLM_SPEND_BREAKER but imports none of the three edited modules. So no class member reaches any arm in production today; the change is inert there until one of those flags flips (the CLAUDE.md rows of section 8 state the level for that flip).

### 1.10 Base pass state of the files the unit touches (bounded runner)

| Set | [pyt] line | Result |
|---|---|---|
| A: test_s81_s06_router_gate_rows, test_s70_exc_summary_logs, test_w49_extraction_catch_redaction, test_image_identify_llm_unavailable_s69, test_s80_b3_vision_identity_v2, test_s80_url_mode_v2, test_s81_s06_anthropic_router, test_s81_s04_spend_breaker, test_text_error_envelope_no_raw_exception | `[pyt] tag=s04c-spec-base-a start=2026-11-11 17:36:13 end=2026-11-11 17:37:22 elapsed=69s bound=1200s status=OK rc=0` | 1383 passed, 0 failed; `[hermeticity] sentinel checked 1383 test(s)`; `[netguard] blocked 46 attempt(s) from 24 node(s)` (all `socket.create_connection neutralized.supabase.invalid:443` sentinels in test_text_error_envelope_no_raw_exception, base noise) |
| B: the CLAUDE.md readers (test_ci_gates, test_behavior_dimension_translation, test_s81_s08b_gate_rows, test_s81_s08b_legacy_fingerprint, test_s81_s23_bypass_retire; test_s81_s04_spend_breaker ran in A) + source pins test_sentry_channels_u8d_unit, test_openai_key_log_hygiene_s69, test_model_config, test_model_config_enforced, test_prompt_fence | `[pyt] tag=s04c-spec-base-b start=2026-11-11 17:37:29 end=2026-11-11 17:38:08 elapsed=39s bound=1200s status=OK rc=0` | 490 passed; `[hermeticity] sentinel checked 490 test(s)`; `[netguard] blocked 0 attempt(s) from 0 node(s)` |

## 2 Contract

### 2.1 Flag and knobs

None. No env name is read that base does not read; `any_role_enabled()` is read at each arm exactly as at base (A1 / A2 / A4: once per arm entry, before the log call; A3: the arm's one read, after the scope bind's read; B1-B4: zero reads) for every exception class and both flag states (R-04C-4).

### 2.2 The log contract per arm in scope (the only behavioural change)

For `e` an instance of `api_budget_service.LLMUnavailableError` (`isinstance`, so every subclass matches; R-04C-6), in EVERY flag state: exactly ONE record on the arm's module logger, `levelno == logging.WARNING`, `exc_info is None`, `record.msg` the constant template, `record.args == (type(e).__name__,)`, `getMessage()` exactly:

| Arm | Message | Logger |
|---|---|---|
| A1 parse | `Product parsing error: <TypeName>` | app.services.extraction_service |
| A2 verdict | `Comparison generation error: <TypeName>` | app.services.extraction_service |
| A3 camera | `[IMAGE] Vision call failed: <TypeName>` | app.api.image_routes |
| A4 url | `AI extraction error: <TypeName>` | app.services.url_extraction_service |
| B1 specs | `Specs extraction error: <TypeName>` | extraction_service |
| B2 price | `Price extraction error: <TypeName>` | extraction_service |
| B3 price fallback | `Price fallback error: <TypeName>` | extraction_service |
| B4 reviews | `Reviews extraction error: <TypeName>` | extraction_service |

No new key, no new field, no response change: the contract freeze (PLAN_S80 section 0; runs/research/contract_freeze.json) is untouched; the refusal still travels only through the envelopes build 3 renders (the camera coded 503 LLM_UNAVAILABLE; the degraded text deliveries); no bare 503 is added.

### 2.3 Failure table (both flag states unless stated)

| Input at the arm | Base | After S81-04c |
|---|---|---|
| class member, role flags OFF, A1 | ERROR + exc_info + text | WARNING by type; same tuple delivered |
| class member, role ON, A1 / A2 / A3 / A4 | WARNING by type (+ raise at A2 / A4) | unchanged (byte-identical) |
| class member, role OFF, A2 | ERROR + exc_info + text; the base dict | WARNING by type; the base dict (NO raise) |
| class member, role OFF, A3 | ERROR + text; the refund; 503 | WARNING by type; the same refund (label, count, order); 503 |
| class member, role OFF, A4 | ERROR by type; `{"error": str(e)}` | WARNING by type; `{"error": str(e)}` (unchanged return) |
| class member, any state, B1-B3 | ERROR `<prefix>Type: text` | WARNING by type; the dict with `"error": str(e)` unchanged |
| class member, any state, B4 | ERROR + exc_info + text | WARNING by type; the constant dict unchanged |
| non-class (RuntimeError, an SDK error, TimeoutError, ...), any arm, any state | the base record | byte-identical (level, exc_info, message, template) |
| a raise inside the logging call | n/a | not possible: constant template + `type(e).__name__` |

### 2.4 The main invariant (replaces flag-OFF identity)

In every flag state: every response body, status, SSE frame, refund (call, label, count, order), ledger row, raise / return flow, getenv read count and order, and every log record of a NON-class exception are byte-identical to base; only the class member's record at the eight arms changes (A1-A4 in the role-flags-OFF state only; B1-B4 in both states).

### 2.5 Test seams (production values in brackets)

- The class source: ENABLE_LLM_PREFLIGHT_BREAKER=true [unset on web] + `monkeypatch.setattr(api_budget_service, "_openai_dispatch_admission", lambda: (False, False, False))` [the real breaker]; the spend path: ENABLE_LLM_SPEND_BREAKER=true [unset on web] + `admit_openai_dispatch` patched to an async function calling the real `llm_spend_breaker._refuse_dispatch("live", 1.0, 0.1)` [the Upstash admit]; the V2 path: ENABLE_VISION_IDENTITY_V2=true [unset] + a fake vision reply with `content=None, refusal=<str>`.
- The client: `es.get_client` / `urlsvc.get_client` / `openai_service.client` replaced by a recording fake whose `create` raises [AsyncOpenAI].
- The read recorder: `monkeypatch.setattr(llm_router, "any_role_enabled", <wrapper calling the real one and appending ("read", value) to an event list>)`; a logging.Handler on the arm's logger appending ("log", levelname, bool(exc_info), getMessage(), msg) to the SAME list (the order check).
- The camera: `limiter.enabled=False`, ENABLE_PAID_ROUTE_METERING=true [the prod state is the owner's; read per call], `get_optional_user` override with a synthetic user, `consume_comparison_credit` / `refund_comparison_credit` recorders on usage_service and image_routes, `image_routes.fire_and_forget` wrapped to record `label` then delegate; the anon arm: ENABLE_ANON_USAGE_GATE=true + no user + `x-device-fingerprint` = sha256 hex of a synthetic string + `check_anon_usage_allowed` patched to `{"allowed": True, "consumed": True, "consumed_keys": {...}}` + `refund_anon_comparison_credit` recorder.
- The role-ON state: ENABLE_ANTHROPIC_CRITIC=true + ENABLE_OPENAI_PRE_V3=true (any_role_enabled() True; no site routes to Claude; nothing refuses: critic decides "openai" through PRE_V3 with no consent header).
- FULL configuration for every PIN (ruling B1): the S81-06 knob set (ANTHROPIC_API_KEY synthetic, built at run time; ANTHROPIC_MAX_RETRIES, ANTHROPIC_MODEL_*, ANTHROPIC_CALL_DEADLINE_SECONDS, ANTHROPIC_CLASSIFY_LLM_TIMEOUT, ANTHROPIC_VISION_TIMEOUT_SECONDS, ANTHROPIC_TAIL_RESERVE_SECONDS), ENABLE_SONNET_ESCALATION=true, ENABLE_OPENAI_PRE_V3=true, ENABLE_REQUEST_CONTEXT_HEADERS=true, every role flag in each PIN_OFF spelling (None, "", "false", "0", "off", " FALSE ") for the OFF rows, plus the class source flag of the row.

## 3 Change list (in the order GREEN applies it)

0. Byte copies (shutil.copyfile) of the three app files, the E1 test file and CLAUDE.md; sha256 recorded.
1. `app/services/extraction_service.py`, arm A1 (:1570-1577): replace the comment :1571-1572 with
   `# S81-06 (GC-3 / R-S06-12) + S81-04c (R-04C-1): an LLMUnavailableError (or a subclass)`
   `# logs ONE WARNING by type in every flag state (never an exc_info ERROR); the`
   `# any_role_enabled() read stays the arm's first statement (R-04C-4).`
   and insert, between the existing WARNING line :1574 and `else:` :1575:
   `        elif isinstance(e, _llm_breaker.LLMUnavailableError):`
   `            logger.warning("Product parsing error: %s", type(e).__name__)`
   (the :1573-1574 lines and the :1575-1577 lines stay byte-identical).
2. Same file, arm B1 specs (:1738-1739): `except Exception as e:` keeps; the body becomes
   `        if isinstance(e, _llm_breaker.LLMUnavailableError):  # S81-04c (R-04C-1): by type, no text`
   `            logger.warning("Specs extraction error: %s", type(e).__name__)`
   `        else:`
   `            logger.error("Specs extraction error: %s", exc_summary(e))`
   then the unchanged return :1740.
3. Arm B2 price (:1790-1791): the same shape with `"Price extraction error: %s"`.
4. Arm B3 price fallback (:1845-1846): the same shape with `"Price fallback error: %s"`.
5. Arm B4 reviews (:1902-1903): the same shape; the else keeps `logger.error(f"Reviews extraction error: {e}", exc_info=True)` byte-identical.
6. Arm A2 verdict (:2810-2820): the comment :2811-2814 gains `S81-04c: role flags OFF the class logs the same WARNING by type and keeps the base delivery.`; after the unchanged `raise` :2818 the line `logger.error(f"Comparison generation error: {e}", exc_info=True)` :2819 becomes
   `        if isinstance(e, _llm_breaker.LLMUnavailableError):`
   `            logger.warning("Comparison generation error: %s", type(e).__name__)`
   `        else:`
   `            logger.error(f"Comparison generation error: {e}", exc_info=True)`
   and the return :2820 is unchanged.
7. `app/api/image_routes.py`, arm A3 (:390-396): the comment :391-392 ("flags OFF the base line, byte-unchanged") becomes `# S81-06 (GC-3) + S81-04c (R-04C-1): an LLMUnavailableError (or a subclass) logs at WARNING by type in every flag state; any other exception keeps the base ERROR line.`; insert between :394 and `else:` :395:
   `        elif isinstance(e, LLMUnavailableError):`
   `            logger.warning("[IMAGE] Vision call failed: %s", type(e).__name__)`
   Nothing else in the arm moves (both refunds :398-399 in order, the 503 / 500 mapping :408-413).
8. `app/services/url_extraction_service.py`, arm A4 (:983-994): after the unchanged `raise` :990, the comment :991-992 keeps and gains `S81-04c: the class logs at WARNING by type in every flag state.`; the line :993 becomes
   `        if isinstance(e, _llm_breaker.LLMUnavailableError):`
   `            logger.warning("AI extraction error: %s", type(e).__name__)`
   `        else:`
   `            logger.error("AI extraction error: %s", type(e).__name__)`
   and `return {"error": str(e)}` :994 unchanged.
9. `tests/test_s81_s06_router_gate_rows.py` E1 (section 4.1).
10. CLAUDE.md (section 8), last.
11. NEW (RED round, frozen): `tests/test_s81_s04c_refusal_log_hygiene.py` (section 5). GREEN does not edit it.

No other file. (No migration, no client file, no processors.json, no legal text, no requirements, no scripts/ file, no `LLMUnavailableError` / breaker message change.)

Statement-form note (R-04C-4): A1 and A3 keep the S81-06 `if any_role_enabled() and isinstance(...)` line byte-identical and add an `elif isinstance(...)` with the same WARNING call, so the one read stays first and unconditional for every class; the duplicated WARNING body is deliberate (a collapsed `if isinstance(e, ...)` would drop the read, and a bare unused read is worse). The report-only local ruff rule SIM114 may flag it; the CI blocking tier (E9,F63,F7,F82) does not. A2 / A4 keep their read in the existing `if` (which re-raises) and branch on the class after it. B1-B4 add no read (base reads none).

## 4 Existing pins

### 4.1 Deliberate changes (E-rows)

| E | Node (old id) | Change | Reason |
|---|---|---|---|
| E1 | `tests/test_s81_s06_router_gate_rows.py::test_g03c_flag_off_parse_site_keeps_the_base_error_line` (:176-195) | renamed `test_g03c_flag_off_parse_site_refusal_warns_by_type`; docstring: `GC-3 + S81-04c E1 (FULL config): role flags OFF, an LLMUnavailableError at the parse site logs ONE WARNING by type (no exc_info, no exception text) and delivers the base parse-error tuple (R-04C-7).`; body: the same `_full_config` + `run_site("parse", oai_exc=abs_.LLMUnavailableError("openai breaker open"))`, then `assert len(recs) == 1 and recs[0].levelno == logging.WARNING and recs[0].exc_info is None, recs`, `assert recs[0].getMessage() == "Product parsing error: LLMUnavailableError"`, and NEW `assert out == ({"products": [], "error": es.PARSE_PRODUCT_QUERY_ERROR}, {"prompt_tokens": 0, "completion_tokens": 0})` (out from the `_capture` tuple; never weakens a delivery assertion). | R-04C-7: the frozen S81-06 flags-OFF identity of this line is what this unit changes. |

Measured "stays green" (no edit), with the reason:

| File / node | Why it stays green |
|---|---|
| tests/test_s81_s06_router_gate_rows.py G03a / G03b / G03d | role ON: the WARNING-by-type lines are byte-unchanged |
| tests/test_s81_s06_router_gate_rows.py G10 / G10b | the scs arm :4901 is unchanged (out of scope, 1.2) |
| tests/test_s81_s06_router_gate_rows.py G13 | no dispatch site moves |
| tests/test_s81_s06_anthropic_router.py P17 (:1138), P09c (:1336), R17 / R17b / R09c, P17b | delivery-only assertions; deliveries unchanged |
| tests/test_s80_b3_vision_identity_v2.py P8 (:1504-1539, ALLOWED_ERROR_PREFIXES :1498) | asserts only that watched-logger ERRORs START with the allowed prefixes; the route_refusal scenario's ERROR becomes a WARNING (fewer ERRORs); no row asserts an ERROR for the class at the camera arm (grep: the prefix appears only at :1498) |
| tests/test_s80_url_mode_v2.py :2775 | a ValueError row (non-class): `["AI extraction error: ValueError"]` at ERROR unchanged |
| tests/test_s70_exc_summary_logs.py (the three extract_* rows) | TimeoutError / RuntimeError (non-class) |
| tests/test_w49_extraction_catch_redaction.py 04 / 04c / r2c / r2e | `Exception(<429 text>)` (non-class): exc_info ERROR unchanged |
| tests/test_text_error_envelope_no_raw_exception.py test_03 | the scs arm with a non-class exception |
| tests/test_image_identify_llm_unavailable_s69.py | delivery (503 envelope, one refund) only; no caplog |
| tests/test_s81_s04_spend_breaker.py (caplog rows filter `[SPEND]` / `fail-open` / `negative` / `unpriced` / `late record`); R38 (CLAUDE.md row tokens) | no arm text read; R38's tokens survive the limit-(9) rewrite (section 8 keeps every token) |
| tests/test_s81_s16_kb_seed.py, tests/test_s81_s22_judge.py | scripts arms, unchanged |
| tests/test_sentry_channels_u8d_unit.py R8 rows | ERROR templates of other lines; the new calls are WARNING inside except arms |

### 4.2 Pins that must stay green and unedited

Every file of 1.10 sets A and B except the E1 node; the comm set of section 7.

## 5 RED tests

File: `tests/test_s81_s04c_refusal_log_hygiene.py` (hermetic; imports `app.main` first (the dotenv guard), then the modules; self-contained harness modelled on the base probe and on tests/test_image_identify_llm_unavailable_s69.py; does NOT import the S81-06 RED module; synthetic values built at run time; pure ASCII; the em dash only as `chr(0x2014)` if ever needed). RED = fails at base on an AssertionError only (the record exists at base at ERROR, so a level / exc_info / message equality fails as an AssertionError); PIN = green at base, FULL configuration (2.5) + the read / log recorder.

| # | Test | Assertion | At base | Satisfied by |
|---|---|---|---|---|
| R1 | `test_r1_class_refusal_warns_by_type_role_off[arm]` arm in {parse, verdict, url_extract, specs, price, price_training, reviews} (7) | W1-3 denial, every role flag OFF (FULL config, each arm once with PIN_OFF value None): the arm's logger records == `[("WARNING", False, "<prefix>: LLMUnavailableError", "<prefix>: %s")]`, and `"dispatch suppressed" not in getMessage()` | RED (ERROR, exc_info for parse / verdict / reviews, text in 6 of 7) | changes 1-6, 8 |
| R2 | `test_r2_camera_refusal_warns_by_type_role_off` | the same on /api/v1/image/identify (authed, metering ON): image_routes records with prefix `[IMAGE] Vision call failed` == `[("WARNING", False, "[IMAGE] Vision call failed: LLMUnavailableError")]` | RED (ERROR with the text) | change 7 |
| R3 | `test_r3_subclass_prints_its_own_name[arm]` 8 arms | role OFF, `_S04cSubRefusal("synthetic sub refusal text")` raised by the fake create: one WARNING `<prefix>: _S04cSubRefusal`, exc_info None, `"synthetic sub" not in getMessage()` | RED (8/8 ERROR at base for role OFF) | isinstance (not `type(e) is`) |
| R4 | `test_r4_group_b_role_on_warns_by_type[arm]` arm in {specs, price, price_training, reviews} | role ON (CRITIC + PRE_V3), W1-3 denial: one WARNING by type | RED (ERROR in both states at base) | changes 2-5 |
| R5 | `test_r5_vision_v2_no_content_warns_by_type` | ENABLE_VISION_IDENTITY_V2=true, refusal reply: image_routes record == WARNING `[IMAGE] Vision call failed: LLMUnavailableError`; the `[VISION_V2] no content` WARNING precedes it; status 503 | RED | change 7 |
| R6 | `test_r6_spend_refusal_warns_by_type_after_the_spend_line` | ENABLE_LLM_SPEND_BREAKER=true + the patched admit calling the real `_refuse_dispatch`: at the parse arm the record sequence over both loggers is `[SPEND] lane=live cap reached ... dispatch refused` (WARNING) then `Product parsing error: LLMUnavailableError` (WARNING), no ERROR record anywhere in the run | RED | change 1 |
| R7 | `test_r7_no_sentry_event_for_a_refusal` | a subprocess (the S81-06 `_sentry_child` pattern: env without ENABLE_*, a synthetic SENTRY_DSN built at run time, `sentry_sdk.init` wrapped to inject a capturing Transport; `app.services.sentry_service.init_sentry()` called) drives the parse arm with the W1-3 denial and prints `RESULT {"events": n}`; asserts n == 0 (bound 240 s) | RED (n == 1) | change 1 |
| P1 | `test_p1_non_class_record_byte_identical[arm,state]` 8 arms x {roleOFF (each PIN_OFF spelling at parse, None elsewhere), roleON} | `RuntimeError("synthetic plain failure text")`: the arm's records == the base literal of 1.3 (level, exc_info bool, getMessage, msg template); camera 500 | PIN | the else branches |
| P2 | `test_p2_delivery_identity[arm,state]` 8 arms x 2 states, class (W1-3) | delivered value == the base literal of 1.3 (A2 / A4 role ON: raised, type LLMUnavailableError; role OFF: the base dict, NOT raised); B1-B3 `error` == the W1-3 message (built with `chr(0x2014)`) | PIN | R-04C-3 |
| P3 | `test_p3_any_role_read_sequence[arm,kind,state]` 8 arms x {class, RuntimeError} x 2 states | the ordered event list: A1 / A2 / A4 exactly `[("read", v), ("log", ...)]` (one read, BEFORE the record); B1-B4 zero reads; A3 exactly two reads and the second precedes the arm's record | PIN | R-04C-4 |
| P4 | `test_p4_camera_refunds_and_status[kind,state]` kind in {w13, runtime}, both states | authed: consumes == [uid], refunds == [(uid, None)], fire_and_forget labels == `["usage_refund.image.vision_exception"]`; status 503 + `{"code": "LLM_UNAVAILABLE"}` fields (class) / 500 + the literal (runtime) | PIN | R-04C-3 |
| P5 | `test_p5_camera_anon_refund` | anon (ENABLE_ANON_USAGE_GATE=true, metering ON, synthetic fingerprint), W1-3 denial: the anon refund recorder called once with the consumed keys, labels == `["usage_refund.image.anon.vision_exception"]`, status 503 | PIN | R-04C-3 |
| P6 | `test_p6_role_on_class_rows_unchanged[arm]` A1-A4 | role ON + W1-3: the S81-06 WARNING by type + the role-ON delivery (A2 / A4 raise; A3 503) | PIN | unchanged lines |

Count: RED 7 + 1 + 8 + 4 + 1 + 1 + 1 = 23 nodes (7 row ids); PIN 1 + ... (P1 21 with the parse spellings, P2 16, P3 32, P4 4, P5 1, P6 4 = 78 nodes, 6 row ids). Fixtures: built from this brief (the B-1 eval_regression.json scenarios do not apply: no tester scenario exercises a refusal path).

## 6 Mutation table (each on a byte copy, an exact-string edit matching once, restored and sha-checked; KILLED = an assertion failure)

| M | Mutant | Killing rows |
|---|---|---|
| M1 | A1 new branch level -> `logger.error` | R1[parse], R3[parse], R6, R7 |
| M2 | A2 level -> error | R1[verdict], R3[verdict] |
| M3 | A3 level -> error | R2, R3[camera], R5 |
| M4 | A4 level -> error | R1[url_extract], R3[url_extract] |
| M5-M8 | B1-B4 level -> error | R1 / R4 for that arm |
| M9 | A1 WARNING keeps `exc_info=True` | R1[parse], R3[parse] |
| M10 | B4 WARNING keeps `exc_info=True` | R1[reviews] |
| M11 | A3 message `f"[IMAGE] Vision call failed: {e}"` at WARNING | R2, R3[camera] |
| M12 | B1 message `exc_summary(e)` at WARNING | R1[specs] |
| M13 | A1 class check widened to `isinstance(e, Exception)` | P1[parse,*] |
| M14 | B2 class check widened to Exception | P1[price,*] |
| M15 | A2 class check narrowed to `type(e) is _llm_breaker.LLMUnavailableError` | R3[verdict] |
| M16 | A3 narrowed to `type(e) is LLMUnavailableError` | R3[camera] |
| M17 | A2 `raise` added under the new role-OFF class branch | P2[verdict,roleOFF] |
| M18 | A4 `raise` added under the new role-OFF class branch | P2[url_extract,roleOFF] |
| M19 | A3 `_refund_reserved_credit(...)` call deleted | P4[*] |
| M20 | A3 `_refund_anon_credit(...)` call deleted | P5 |
| M21 | A3 the two refund calls swapped | EQUIVALENT (the latches are mutually exclusive per request: only one fires, 1.2); reported for a ruling, not a gap |
| M22 | A1 form collapsed to `if isinstance(e, X)` (the read dropped) | P3[parse,*] |
| M23 | B1 gains an `_llm_router.any_role_enabled()` read | P3[specs,*] |
| M24 | A2 new branch placed BEFORE the role-ON `if` (role ON no longer raises) | P6[verdict], P2[verdict,roleON] |
| M25 | A3 503 mapping keyed on the new branch only (`elif` arm returns 503, runtime path 503) | P4[runtime,*] |

## 7 Comm set and gates for GREEN (cheapest first)

1. py_compile + ruff `--select E9,F63,F7,F82 --no-cache` on the three app files, the E1 file and the RED file; bytes > 127 = 0 on every edited / added line; `git diff --stat` shows no whole-file diff; the gitleaks keyword rule on any new constant name.
2. The RED file + tests/test_s81_s06_router_gate_rows.py (bound 600): every RED green, every PIN green.
3. The mutation table (bound 600 per mutant, the lock file, byte copies).
4. The comm set, base vs head, chunks of <= 25 files (bound 1200 each), `comm -13` of the sorted FAILED node ids EMPTY. Derivation (fixpoint in both directions, utf-8-sig parse): (a) module / symbol reference grep over tests/*.py for `extraction_service|image_routes|url_extraction_service|LLMUnavailableError|any_role_enabled|test_s81_s06_router_gate_rows`; (b) every app.main / TestClient user (image_routes is a router of app.main); (c) the source-scanning pins (glob / rglob / listdir / scandir / inspect.getsource / ast.parse / `__file__` parent readers) plus the named pins tests/test_model_config.py, test_model_config_enforced.py, test_prompt_fence.py, test_u3c_store_false_pin.py, test_start_command*.py, test_migration_index_predicate_immutability.py, test_openai_key_log_hygiene_s69.py, test_sentry_channels_u8d_unit.py; (d) the CLAUDE.md readers by the import graph: test_ci_gates.py, test_behavior_dimension_translation.py, test_s81_s04_spend_breaker.py, test_s81_s08b_legacy_fingerprint.py, test_s81_s08b_gate_rows.py, test_s81_s23_bypass_retire.py; MINUS the test_precommit_hook*.py files; PLUS the new RED file. Measured at a74caba7: 368 candidate files (list <scratchpad>/S81-04c/comm_set_candidates.txt, sha256 79f7bc7e3a135b0c608b319c6d8f97db09c5920792db20a60201b13c86567462); the SmartCompareApp-scanning tests are NOT added (no client-visible byte changes). The base record: none stored at a74caba7; the RED stores it LAST under GC-9 per-file reuse of the 90d4ed74 record (1f35353b..., 727 members) ONLY for members whose bytes are unchanged through a74caba7, that name none of extraction_service / image_routes / url_extraction_service / llm_router / api_budget_service / CLAUDE.md and are no app.main / TestClient users and no glob / dir walkers (the #398 MOVING MAIN exclusions apply on top).
5. The fourteen client fences BY PATH at GREEN (the unit edits CLAUDE.md and app/).
6. The final round: the FULL jest once (LC-7; the baseline 4,030 passed + the four w37 drift nodes + 13 pending + 13 todo).
7. The corpus gate: NOT re-measured (no prompt, no rendered payload, no extraction path changes; the unit touches log calls only).

## 8 CLAUDE.md (GREEN's last step, in place, dated <merge date>; principle 5) and owner steps

Sentences (line numbers at a74caba7 of the worktree CLAUDE.md; GREEN locates each by its quoted first words):

(a) :495, the S81-04 row, stated limit (9), currently `(9) every refusal reaches the callers' existing exc_info ERROR logs (`extraction_service` parse and verdict, `image_routes` vision, `url_extraction_service`): Sentry events from the moment a lane is exhausted (follow-up S81-04c downgrades them for `LLMUnavailableError`);` -> `(9) (rewritten <date>, S81-04c) a refusal reaches the callers' except arms (`extraction_service` parse, specs, price, price fallback, reviews and verdict, `image_routes` vision, `url_extraction_service`), and each logs ONE WARNING by type (`<prefix>: LLMUnavailableError`, no exc_info, no exception text) in every flag state: not a Sentry event (LoggingIntegration level ERROR, sentry-sdk 2.68.1), so the breaker's own `[SPEND]` lines and the coded 503 count are the refusal signal;` (every R38 token of the row is outside this clause and kept).
(b) the ENABLE_LLM_SPEND_BREAKER canary sentence (:495, `**Canary (the owner's explicit yes, one window):**`): MEASURED, it counts the `[SPEND]` lines, the short-circuit / fail-open / late-record counts and the LLM_UNAVAILABLE 503 count, never the limit-(9) Sentry events -> NO edit.
(c) :853 the ENABLE_LLM_PREFLIGHT_BREAKER (W1-3) row: append ONE sentence before the U3c sentence: `Since S81-04c (<date>) a denial that reaches a dispatch site's except arm logs that arm at WARNING by type (`<prefix>: LLMUnavailableError`), never an ERROR, so a denial raises no Sentry event; the denial itself logs no line (`_openai_dispatch_admission`), the trip logs one `[CIRCUIT] openai breaker TRIPPED` WARNING and the compare-entry short-circuit one `[CIRCUIT] openai breaker OPEN` WARNING.`
(d) :477 the ENABLE_VISION_IDENTITY_V2 row: append ONE sentence before `**Rollback:**`: `Since S81-04c (<date>) the no-content outcome logs the camera arm `[IMAGE] Vision call failed: LLMUnavailableError` at WARNING (after the `[VISION_V2] no content` WARNING): no Sentry event; the coded 503 and the refund are unchanged.` (the existing "on a V2 expiry the route's ... line has an empty tail" clause stays true: a TimeoutError is not the class).
(e) :508 the S81-06 row, the clause `the four dispatch-level refusal log sites (parse, verdict, camera vision, url extract) log at WARNING by type,` -> `the four dispatch-level refusal log sites (parse, verdict, camera vision, url extract) log at WARNING by type (in every flag state since S81-04c, <date>, which also covers the specs / price / price-fallback / reviews arms),`. MEASURED: no CLAUDE.md sentence says "flags OFF the base line"; that phrase lives in the code comments (image_routes.py:391-392, extraction_service.py:1571-1572 region), rewritten by changes 1 and 7.
(f) the :341 pointer clause, after the S81-G10 sentence (`... the rows of the **SESSION 81 units (S81-G10 FOLLOWUPS, ...)** block.`): add `S81-04c REFUSAL-LOG-HYGIENE adds no flag (log-only under R-A1 (b)): the **SESSION 81 unit (S81-04c REFUSAL-LOG-HYGIENE, ...)** block.`
(g) the lagging rows (each with its ledger source):
  - :550 `... writes `kb_brands` (migration 052, written NOT applied; service role only)` -> `(migration 052, applied 2026-11-06; 300 rows imported 2026-11-10 by the owner's one-off APPLY, session-81 ledger line 417; service role only)`.
  - :628 the S81-G9 owner steps: `S81-16c: after the merge, the owner-approved DRY run (...), then `ENABLE_KB_BRANDS=apply` the same way, then the kb_brands count; no live Wikidata request before the merge. D17c: re-read the totals line of the next scheduled kb-coverage runs (`not_built`, `redis`).` -> `S81-16c: DONE 2026-11-10 (DRY 02:48 and APPLY 02:49 through railway run, 300 rows written, the 42 over-cap brands not written at the KB_BRANDS_MAX default; session-81 ledger line 417). D17c: DONE 2026-11-10 (the 2026-11-09 01:22Z run's totals read not_built=0 redis=1; ledger line 418).`
  - :635 the S81-G10 owner steps: `D-S22-J1: after the merge, ONE judge DRY run (the service exists, no schedule) re-reads step 0 (no `errors.APIError`, the resume read answers 200);` -> `D-S22-J1: DONE 2026-11-10 (one judge DRY run after #398: step 0 answered 200, no errors.APIError, no 400; ledger line 419);`.
  - Store state: MEASURED with the regex `(?i)(pending developer|not live|approv|releas|first install|reaches install|waits on the production)` over the whole file: NO sentence states 1.0.0 (3) as approved-not-released (the hits are flip preconditions such as :592 / :595 / :609 "after App Review approval", met 2026-11-07, and the dated SESSION 77 block :686). No store-state edit; question Q-D.
(h) NEW block after the S81-G10 owner-steps bullet (:635), one blank line, before `## Tests`:
`**SESSION 81 unit (S81-04c REFUSAL-LOG-HYGIENE, <date>; NO flag: log-only under R-A1 (b), R-S04-10 / R-04C-1):**`
`- An `api_budget_service.LLMUnavailableError` (or any subclass) that reaches a request-path except arm logs ONE WARNING by type (`<prefix>: <TypeName>`, no exc_info, no exception text) in every flag state at: `extraction_service` parse (`Product parsing error`), specs, price, price fallback, reviews and verdict (`Comparison generation error`), `image_routes` camera vision (`[IMAGE] Vision call failed`) and `url_extraction_service` AI extraction (`AI extraction error`). Every delivery is byte-identical (the parse / verdict / url / specs / price / reviews return values, the role-ON re-raises, both camera refunds and the 503 / 500 mapping), every non-class exception keeps its ERROR record, `any_role_enabled()` is read as at base. Sentry (2.68.1, LoggingIntegration level ERROR): a WARNING is neither an event nor a breadcrumb, so a refusal raises no Sentry event; the signal is the raiser's own line (`[SPEND] ... refused`, `[VISION_V2] no content`) and the coded 503 count; a W1-3 denial logs nothing at the denial (the trip's `[CIRCUIT] ... TRIPPED` WARNING once). Unchanged and out of reach with role flags OFF: the scs `Comparison error` / `Streaming comparison error` arms and `[IMAGE] Comparison failed after identification`. Pins: `tests/test_s81_s04c_refusal_log_hygiene.py` + E1 (`test_g03c_flag_off_parse_site_refusal_warns_by_type`). Stated limits L1-L6 (spec S81-04c section 9).`
`- **Owner steps (names only):** none to flip. The S81-04 breaker canary counts the `[SPEND]` lines and the coded 503s; a refusal no longer raises a Sentry event at the arms.`

Owner steps (names only): none.

## 9 Stated limits

- L1 A W1-3 denial logs no line at the denial itself (`_openai_dispatch_admission` :822-824, `is_circuit_closed` :545-583); after this unit the operator sees, per refused dispatch, the arm's WARNING by type only, plus one `[CIRCUIT] openai breaker TRIPPED` WARNING per trip (:609) and the compare-entry `[CIRCUIT] openai breaker OPEN` WARNING (scs :4152-4157, which carries `query=%r`, a separate pre-existing hygiene item). No Sentry signal of an OPEN breaker exists after the unit (before it, one existed only by accident of the ERROR arms). Q2.
- L2 B1-B3 still RETURN `{"error": str(e)}` (the class message, incl. the U+2014 em dash) and A4 `{"error": str(e)}`; the W4-9 / S70 contracts keep those values byte-identical (out of scope, R-04C-3 / R-04C-8); whether a degraded specs / price dict's `error` reaches a body is not re-measured here.
- L3 A1 / A3 carry a duplicated WARNING body (the `elif`), deliberate for R-04C-4 (3, statement-form note); SIM114 (report-only) may flag it.
- L4 Group B changes the role-ON record too (base ERROR in both states); an AnthropicDispatchError at a specs / price / reviews site logs WARNING by type after the unit (the S81-06 role-ON contract made no claim about these four arms).
- L5 Out of scope by level: the WARNING arms that print the exception text (classify :1420 f-string, image tier-3 :196 `%r`, specs_targeted :788, specs_synthesized :861, disambiguate :955) keep the class text at WARNING (no Sentry event; a hygiene follow-up, proposed id S81-04e).
- L6 M21 (the two camera refunds swapped) is an equivalent mutant: one request fires one latch.

## 10 Out of scope (R-04C-8)

No new flag / knob / log line at a raise site; no Sentry configuration change; no change to `LLMUnavailableError`, its subclasses or any breaker / refusal message; no delivery change (the scs :4901 / :5813 and image_routes :788 arms are unreachable by the class with role flags OFF, 1.2, and stay byte-unchanged; G10b reaches :4901 only through a patched seam); no client file, migration, legal text, processors.json row, requirements or scripts/ change; the scripts/ refusal handlers (cron_compare_judge.py:678 / :737, seed_kb_batch.py:518) log no ERROR and stay unchanged.

## 11 Open questions for the orchestrator (with the measured answers to Q1-Q6)

- Q1 (answered): the arm table is 1.2 + 1.3. Production reachability per flag state, every role flag OFF: W1-3 ON -> A1, A2, A4 and B1-B4 (every routed site) and A3 (vision V1 / V2); vision V2 ON -> A3 only; spend breaker ON -> the same set as W1-3 (each after its own `[SPEND]` WARNING); a role flag ON -> A1-A4 already WARNING by type (the subclasses + the consent gate), B1-B4 at ERROR at base. Today (ledger line 316 + item 32): none of those flags is set on web, so no arm fires in production.
- Q2 (answered, L1): a W1-3 denial logs NO line of its own; after the unit an operator sees the arm's WARNING by type, the trip WARNING once and, at the next compare entry, the OPEN short-circuit WARNING. It is a hole only for Sentry-based alerting, which never had an intended signal for an open breaker; the CLAUDE.md W1-3 row states it (8 (c)).
- Q3 (answered, 1.6): measured on sentry-sdk 2.68.1: WARNING = neither an event nor a breadcrumb; ERROR = an event + a breadcrumb; sentry_service.py:724-738.
- Q4 (answered, 4.1): one E-row (E1); every other reader stays green, each with its reason; no global "no WARNING" assertion reads the class at an arm.
- Q5 (answered, 8): the exact sentences; the CLAUDE.md readers pin none of them (test_s81_s04_spend_breaker R38's tokens are outside the rewritten clause).
- Q6 (answered): no source-scanning pin reads the changed statements: G13 reads routed dispatch calls only; the u8d R8 scans read ERROR calls by other prefixes and outside-except ERROR calls; no pin counts `logger.error(` or the `any_role_enabled() and isinstance` form (grep over tests/ for those forms: none).
- Q-A (ruling needed): group B (B1-B4) is in scope by the R-04C-2 census rule and changes the role-ON record as well (L4). Confirm, or carve it out (drop changes 2-5, R1 for those arms, R4, P*-rows for B, M5-M8, M10, M12, M14, M23; then a stated limit names the four ERROR arms and follow-up S81-04e takes them).
- Q-B (ruling needed): the A1 / A3 statement form: the `elif` duplicate (proposed; S81-06 lines byte-identical, the read unconditional and first) vs a named unused read `_role_on = _llm_router.any_role_enabled()` followed by `if isinstance(...)`.
- Q-C (follow-up id proposed): S81-04e = the text-bearing WARNING arms of L5 and, optionally, the `query=%r` in the W1-3 short-circuit WARNING (scs :4152-4157).
- Q-D: no CLAUDE.md sentence states the store as approved-not-released at a74caba7 (8 (g)); the met "after App Review approval" preconditions (:520, :534, :592, :595, :609) are left as written unless the orchestrator wants them dated.
- Q-E: R7 (the Sentry subprocess row) costs about 10-30 s; keep it RED (observability lens) or demote it to a PIN of the unchanged ERROR side only.

Not done in this spec: no app/ or tests/ file edited; no RED file written; no base record stored; no mutation run; no comm-set run (the candidate list only); the probe file under `.qa-s80/s04c_probe/` was removed after measurement.
