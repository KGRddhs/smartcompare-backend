## S81-06 ANTHROPIC-ROUTER: the consent-gated Claude brain above guarded_llm_create (dark)

Flags (all NEW, default OFF, read per call): `ENABLE_ANTHROPIC_TEXT`, `ENABLE_ANTHROPIC_VISION`, `ENABLE_ANTHROPIC_VERDICT`, `ENABLE_ANTHROPIC_CRITIC`, `ENABLE_ANTHROPIC_MODERATION`, `ENABLE_SONNET_ESCALATION`, `ENABLE_OPENAI_PRE_V3`. Branch `feature/s81-s06-anthropic-router`, HEAD `ceecb04a1a4c9e58c62eebe07705148a979eb31e`, base `ea3aef15` (= #371 S81-05 + #372 S81-04).

### What it does
`app/services/llm_router.py` sits ABOVE `api_budget_service.guarded_llm_create` (unchanged; U3c and K1 untouched). Every one of the 16 chat sites calls `_llm_router.route("<site>", _llm_breaker.guarded_llm_create, client, <the unchanged kwargs>)`. Role flag OFF: the first statement returns the exact base call. Role flag ON: consent >= 3 -> Claude Haiku 5.5 through `guarded_anthropic_create` (key check, S81-04 spend admit, its own `circuit:anthropic` breaker off the loop, typed-exception classification, an inner deadline, the S81-03 llm ledger, refusal recorded before raising) returning an OpenAI-shaped result; consent absent / < 3 -> the exact OpenAI call while ENABLE_OPENAI_PRE_V3 is ON, else ConsentUpdateRequiredError. Both text entries, /url/compare (before the reserve) and the camera (before identify, for any reached role) refuse such a request with the existing coded 503 LLM_UNAVAILABLE. Under any role flag ON a verdict LLMUnavailableError is a non-delivery (REST, stream, URL, camera). Moderation on Claude fails CLOSED. One Sonnet escalation per compare. Full row in CLAUDE.md (SESSION 81 flags S81-06).

### Ruling / gate ids -> test nodes
| Ruling / gate id | What | RED / gate-row nodes |
|---|---|---|
| R-S06-1 / GC-6 | no open schema; closed schemas or no format + fence strip; vision v1 unwrap | R01, R02, R02b, R02c, R13b, R13c |
| R-S06-2 | verdict LLMUnavailableError = non-delivery under ANY role ON | R17, R17b, R17c, R17d, P17, P17b, G06b, G06c |
| R-S06-3 / GC-4 | /url/compare gate (both verbs, before the reserve); site 15 re-raise | R09b, R09c, P09c, G06a, G07 |
| R-S06-4 / GC-1 | preflight = AND over every decided provider (moderation when on Claude, critic when ENABLE_SELF_CRITIQUE) | R33 (5 cells), P05, G05 (7 cells) |
| R-S06-5 / GC-5 | entry gate scoped to entry roles; key-unset refuses at entry; camera gate before identify for ANY reached role | R07, R08, R08b, R08c, R08d, R09, R09d, R10, G08, G08b |
| R-S06-6 / GC-2 | moderation fails CLOSED (refusal / unavailable / malformed); fenced text; synthetic prompt | R29 (x5), R29b, R30, R30b, P03, G01 (x3) |
| R-S06-7 | key check -> spend admit -> breaker (to_thread, 0.5 s, fail-open) -> call -> record; explicit base_url / api_key; additive /health key | R18, R19, R20, R20b, R21, R22, R25, R25b, G04 |
| R-S06-8 | image blocks; Pillow downscale; 5 MB cap without Pillow | R11, R11b, R11c, R11d |
| R-S06-9 | timeout knobs only on the Claude branch | R32, P12 |
| R-S06-10 | disambiguate cost + enum; camera llm merge | R40, R10c, R14 |
| R-S06-11 | AnthropicIntegration(include_prompts=False), guarded; Sentry live | R34a, R34b (M34 KILLED here) |
| R-S06-12 / GC-3 | cache-key provider axis ON only; WARNING-by-type at the 4 refusal log sites | G02a (x6), G02b, G03a, G03b, G03c, G03d |
| R-S06-13 | anthropic==1.12.1 | R37, R16 (real SDK) |
| R-S06-14 | processors row at the END, gated, eighth fill-in flag | R36, R36b |
| R-S06-15 | escalation on refusal / schema failure at JSON sites | R26, R27 (x2), R27b, R28, R28b |
| flag-OFF identity | every site / entry / moderation / ledger / preflight / fallback / camera | P01 (x90), P02, P03, P04, P05, P06, P07, P08, P09, P09b, P09c, P10, P11, P12, P13, G02a, G03c, G06c, G08b, G09 |

### Deliberate pin changes (spec 4.1 + gate)
| # | Pin | Change | Reason |
|---|---|---|---|
| E1 | tests/test_model_config_enforced.py `_chat_sites` + M1 | callee also `llm_router.route`; floor 15 -> 16 | the 16 sites call the router |
| E2 | tests/test_model_config_enforced.py `_clean_env` | the seven flags cleared | a developer .env must not route a site |
| E3 | tests/test_u3c_store_false_pin.py u3c_03 | the census counts `route(...)` whose 2nd positional is `*.guarded_llm_create`; floors 16 sites / 33 spreads | same reason as E1; the denied-keyword and spread rules unchanged |
| E4 | tests/test_u3c_store_false_pin.py u3c_02 | the Anthropic Messages surface (.create/.stream/.parse/.count_tokens on .messages / .messages.batches / .beta.messages) allowed only inside `llm_router.guarded_anthropic_create`; 3 bypass + 1 legit self-check shapes | the second chokepoint |
| E5 | tests/test_model_config.py stray literals | pattern gains `claude-...`; ALLOWED gains `llm_pricing.py` (a price table) | Claude ids live only in model_config |
| E6 | tests/test_legal_docs_u8.py | CLIENT_CONSTRUCTORS gains `AsyncAnthropic`, `Anthropic`; the positive control gains llm_router.py (`AsyncAnthropic`, host api.anthropic.com) | T7b sees the new recipient |
| E7 | tests/fixtures/legal_s78.json | `manifest_base.anthropic` (R22 re-recorded) | the new processors row |
| E8 | tests/test_sentry_channels_u8d.py | `AnthropicIntegration` in BASE_INTEGRATIONS; child INIT `anthropic_include_prompts`; options row `("anthropic_include_prompts", False)` | R-S06-11 |
| E9 | tests/test_s81_s05_request_context.py P1 | `app/services/llm_router.py` allowed; exactly `from app.utils import request_context as _request_context`; attribute uses == {consent_version, header_state}; the `header_state` / `x-ai-consent-version` needles allowed there | R-S05-10: the first consumer |
| E10 | FY25 UNIT_ENV, tests/w4_11_prompt_digest_recorder.py FLAGS, tests/test_prompt_fence.py `_W411_FLAGS`, U13 CLEAN_ENV, tests/test_retro_w2_1.py `_clean_flags` | the seven names join each clear-list | a developer .env must not leak a flag into a digest pin |
| GC-7a | scripts/fill_in_legal.py + tests/test_legal_docs_u8.py SEVEN_FLAGS | eighth name `ENABLE_ANTHROPIC_TEXT` (the tuple keeps its name) | R-S06-14 |
| GC-7b | tests/fixtures/legal_fill_in_u8.json flags | `ENABLE_ANTHROPIC_TEXT: "off"` | the schema requires every SEVEN_FLAGS name; a new name is unset in production by construction |
| GC-7c | app/legal/processors.json | the anthropic row appended at the END (after retailers), gated by ENABLE_ANTHROPIC_TEXT, public_name false | R-S06-14 / R-S12-11 |
| -- | .github/black-clean-paths.txt | `app/services/llm_router.py`, `tests/test_s81_s06_router_gate_rows.py` | D03 / S81-05 precedent (the frozen RED file is not listed: not black-formatted and frozen) |

### GC-6: the per-site schema choice
| Site | Choice | Reason |
|---|---|---|
| classify | none (a word) | expects_json False |
| parse | (b) no format + JSON-only line + Claude-branch fence strip | the parser reads `products` with free per-product keys (brand/name/category/variant/search_query/...) and strips `_parse_*`; a closed schema would have to enumerate every prompt key |
| specs | (b) | the spec dict is category-dependent (CATEGORY_SPEC_SCHEMAS x 9 + citations); a call-time closed schema would forbid the citation / extra fields the prompt asks for |
| price | (b) | open price dict (amount, currency, retailer, url, ...); parser strips fences |
| price_training | (b) | open dict; the may-decline variant allows nulls |
| reviews | (b) | nested free dict (review_summary, sources, citations) |
| verdict / verdict_fallback | (b) | the widest prose-JSON: pros/cons/specs_comparison/personalized_insights with optional keys per flag; required keys vary by flag state |
| specs_targeted / specs_synthesized | (b) | the field set is the caller's `fields` list per call; json.loads without a fence strip at base -> the Claude-branch strip covers it |
| url_extract | (b) | open product dict; `is_product_page` only under URL_MODE_V2 |
| critique | (b) | five integer scores today but the parser tolerates extra keys; kept consistent with the verdict family (a closed schema can be a data PR after S81-07) |
| image_tier3 | (a) IMAGE_TIER3_SCHEMA | ruling-mandated |
| vision_v1 | (a) {"products": [...]} unwrapped to the array | ruling-mandated (the v1 parser needs an array) |
| vision_v2 | (a) the B3 V2 identity schema | ruling-mandated |
| disambiguate | (a) DISAMBIGUATE_SCHEMA enum true/false/unknown + confidence high/low | R-S06-10 |

### Gates (dedicated venv `.venv-s81-06`, anthropic 1.12.1; every pytest through the bounded runner)
- RED file at base ea3aef15: `[pyt] tag=s06g-red-at-base start=2026-10-24 10:00:21 end=2026-10-24 10:05:47 elapsed=326s bound=600s status=FAIL rc=1`: 229 failed (AssertionError only) / 112 passed; the one move vs the RED record is `test_r25b_real_spend_breaker_present` (a presence-only row, green once S81-04 merged); `[hermeticity] sentinel checked 341 test(s)`, `[netguard] blocked 0 attempt(s) from 0 node(s)`.
- RED file + gate rows at HEAD: `[pyt] tag=s06g-unit-final start=2026-10-24 12:04:06 end=2026-10-24 12:04:29 elapsed=23s bound=600s status=OK rc=0`: 374 passed (341 + 33); `[netguard] blocked 0 attempt(s) from 0 node(s)`.
- Pin set (25 files: E1-E10, U3c, K1 file, FY25, W4-13, T23/U13, legal D7/R9/T7a/T7b/R22, Sentry SR8): `[pyt] tag=s06g-pins-1 start=2026-10-24 11:23:33 end=2026-10-24 11:25:00 elapsed=87s bound=1200s status=OK rc=0`: 1627 passed; `[netguard] blocked 141 attempt(s) from 7 node(s)` (the test_openai_breaker sentinel class + the test_retro_w1_3 curl_cffi node, both baseline).
- CLAUDE.md readers + env safety alone: `[pyt] tag=s06g-readers-1 start=2026-10-24 12:02:39 end=2026-10-24 12:03:24 elapsed=45s bound=600s status=OK rc=0`: 103 passed, 1 skipped.
- CI-order set (24 files sorted): `[pyt] tag=s06g-ci-order start=2026-10-24 12:13:41 end=2026-10-24 12:16:48 elapsed=187s bound=1200s status=OK rc=0`: 2146 passed.
- Comm set at HEAD: 461 files (the RED 447 UNION 14 new reference / source-scanning files: the cache_service, /health, legal fixture and _env_safety readers; MINUS test_precommit_hook* and the two unit files), 19 chunks of <= 25, bound 1200:
- `[pyt] tag=s06g-comm-head-00 start=2026-10-24 11:28:18 end=2026-10-24 11:28:55 elapsed=37s bound=1200s status=OK rc=0`: 821 passed, 1 deselected; `[netguard] blocked 24 attempt(s) from 7 node(s)`
- `[pyt] tag=s06g-comm-head-01 start=2026-10-24 11:28:56 end=2026-10-24 11:29:52 elapsed=56s bound=1200s status=OK rc=0`: 597 passed, 31 deselected; `[netguard] blocked 30 attempt(s) from 7 node(s)`
- `[pyt] tag=s06g-comm-head-02 start=2026-10-24 11:29:54 end=2026-10-24 11:31:39 elapsed=106s bound=1200s status=FAIL rc=1`: 1 failed, 1604 passed, 1 skipped, 7 deselected; `[netguard] blocked 14 attempt(s) from 9 node(s)`
- `[pyt] tag=s06g-comm-head-03 start=2026-10-24 11:31:40 end=2026-10-24 11:32:10 elapsed=30s bound=1200s status=OK rc=0`: 425 passed, 9 deselected; `[netguard] blocked 2 attempt(s) from 1 node(s)`
- `[pyt] tag=s06g-comm-head-04 start=2026-10-24 11:32:11 end=2026-10-24 11:32:48 elapsed=37s bound=1200s status=OK rc=0`: 1464 passed, 2 skipped; `[netguard] blocked 27 attempt(s) from 9 node(s)`
- `[pyt] tag=s06g-comm-head-05 start=2026-10-24 11:32:52 end=2026-10-24 11:37:37 elapsed=285s bound=1200s status=OK rc=0`: 1947 passed, 1 skipped; `[netguard] blocked 63 attempt(s) from 40 node(s)`
- `[pyt] tag=s06g-comm-head-06 start=2026-10-24 11:40:20 end=2026-10-24 11:40:52 elapsed=32s bound=1200s status=OK rc=0`: 525 passed, 14 deselected; `[netguard] blocked 13 attempt(s) from 2 node(s)`
- `[pyt] tag=s06g-comm-head-07 start=2026-10-24 11:40:53 end=2026-10-24 11:41:30 elapsed=37s bound=1200s status=OK rc=0`: 398 passed; `[netguard] blocked 1 attempt(s) from 1 node(s)`
- `[pyt] tag=s06g-comm-head-08 start=2026-10-24 11:41:31 end=2026-10-24 11:41:57 elapsed=26s bound=1200s status=OK rc=0`: 525 passed, 1 skipped, 10 deselected; `[netguard] blocked 0 attempt(s) from 0 node(s)`
- `[pyt] tag=s06g-comm-head-09 start=2026-10-24 11:41:58 end=2026-10-24 11:42:52 elapsed=53s bound=1200s status=FAIL rc=1`: 2 failed, 3639 passed, 22 skipped; `[netguard] blocked 130 attempt(s) from 9 node(s)`
- `[pyt] tag=s06g-comm-head-10 start=2026-10-24 11:42:53 end=2026-10-24 11:44:08 elapsed=75s bound=1200s status=OK rc=0`: 636 passed, 3 skipped, 15 deselected; `[netguard] blocked 39 attempt(s) from 15 node(s)`
- `[pyt] tag=s06g-comm-head-11 start=2026-10-24 11:44:13 end=2026-10-24 11:46:22 elapsed=129s bound=1200s status=FAIL rc=1`: 793 passed, 5 skipped, 1 deselected, 1 xfailed, 2 errors; `[netguard] blocked 10 attempt(s) from 2 node(s)`
- `[pyt] tag=s06g-comm-head-12 start=2026-10-24 11:46:23 end=2026-10-24 11:48:19 elapsed=116s bound=1200s status=OK rc=0`: 884 passed; `[netguard] blocked 20 attempt(s) from 1 node(s)`
- `[pyt] tag=s06g-comm-head-13 start=2026-10-24 11:48:20 end=2026-10-24 11:52:05 elapsed=225s bound=1200s status=OK rc=0`: 3273 passed, 1 xfailed; `[netguard] blocked 29 attempt(s) from 5 node(s)`
- `[pyt] tag=s06g-comm-head-14 start=2026-10-24 11:54:38 end=2026-10-24 11:56:40 elapsed=121s bound=1200s status=OK rc=0`: 1097 passed; `[netguard] blocked 18 attempt(s) from 8 node(s)`
- `[pyt] tag=s06g-comm-head-15 start=2026-10-24 11:56:41 end=2026-10-24 11:58:08 elapsed=87s bound=1200s status=OK rc=0`: 520 passed, 8 skipped, 10 deselected; `[netguard] blocked 101 attempt(s) from 38 node(s)`
- `[pyt] tag=s06g-comm-head-16 start=2026-10-24 11:58:11 end=2026-10-24 11:59:57 elapsed=106s bound=1200s status=OK rc=0`: 548 passed, 8 deselected, 35 xfailed; `[netguard] blocked 84 attempt(s) from 29 node(s)`
- `[pyt] tag=s06g-comm-head-17 start=2026-10-24 12:00:44 end=2026-10-24 12:01:23 elapsed=40s bound=1200s status=OK rc=0`: 1183 passed, 9 skipped; `[netguard] blocked 8 attempt(s) from 8 node(s)`
- `[pyt] tag=s06g-comm-head-18 start=2026-10-24 12:01:24 end=2026-10-24 12:01:39 elapsed=15s bound=1200s status=OK rc=0`: 198 passed, 1 skipped; `[netguard] blocked 12 attempt(s) from 4 node(s)`
- HEAD failure set: test_page_scraping::TestFetchPagePriceJsonLD::test_jsonld_nested_offers_picks_lowest, ::TestFetchPagePriceOpenGraph::test_og_meta_extraction (accepted baseline), test_prompt_truth cold-tiktoken pair (accepted baseline, ERROR), test_ci_gates::test_black_allowlist_entries_are_actually_clean (caught by this run, FIXED: black on the three allowlisted edited files; green in the readers run and the CI-order run). branch-only-new = EMPTY against the accepted baselines. A full base comm record at ea3aef15 was NOT re-run (time budget; see the report).
- Mutants on GREEN bytes: MG1-MG8 (gate rows) 8/8 KILLED; M34 (include_prompts=True) KILLED on the real SDK (NOT MEASURED at RED).
- ruff E9/F63/F7/F82 clean, py_compile clean, black --check clean on the allowlisted files; added bytes pure ASCII (CLAUDE.md: two existing lines carrying em dashes were edited in place); the pre-commit hook passed.

### Stated limits
1. The consent version is the client's claim (a header); the server cannot verify the sheet was shown.
2. Haiku has no server fallback beyond ONE Sonnet escalation per compare; a refusal past the cap is the LLM_UNAVAILABLE non-delivery (refund through the existing `refund_comparison_credit(user_id)` call shape; the consumed_keys refund is S81-09's).
3. OpenAI moderation runs while ENABLE_ANTHROPIC_MODERATION is OFF; the OpenAI moderations endpoint is not in the preflight AND (not behind the W1-3 breaker, fails open at base).
4. The OpenAI free allowance ends with the switch.
5. No web search, streaming, Batch or prompt caching in this unit.
6. Structured-output acceptance of the closed schemas (incl. the V2 anyOf), of format + image blocks, and the no-format JSON validity of the eleven (b) sites are unmeasured offline (S81-07 before each flip).
7. Measured on 1.12.1: an explicit `api_key` stops the SDK's credential discovery and `base_url` is explicit, but the SDK still reads `ANTHROPIC_CUSTOM_HEADERS` (and `ANTHROPIC_WEBHOOK_SIGNING_KEY`) from the environment; never set those on web / price-warmer.
8. The anthropic breaker's Redis calls run through `asyncio.to_thread` (the default `qaren-worker` executor) under 0.5 s; the read-only preflight reads on the loop once per memo window (the W1-3 openai shape); a cross-process trip is seen up to LLM_BREAKER_CACHE_TTL late.
9. A mid-request role-flag flip is costed by the scope bound at entry.
10. Off-clock scripts / the warmer have no request context (consent None): never set a role flag on price-warmer.
11. Only the comparison cache key gains the provider axis (it has no production caller today; no verdict cache exists in app/); the specs / price / reviews L1/L2 caches carry Claude-extracted values across providers and rollbacks for their TTLs.
12. The engine-unavailable copy implies a transient outage for a stale-client refusal (S81-11 renders a reason).
13. APP_MIN_VERSION closes the pre-v3 window only with a 1.0.1 binary live.
14. A camera request can escalate once in vision and once in the compare (the compare rebinds its own scope).
15. Pillow is dev-only: production takes the 5,000,000-byte cap refusal for a larger image part.
16. The camera's Info.plist purpose strings (build 3) say photos go to OpenAI: the vision flip waits for the risk to be accepted or for 1.0.1.
17. Never set any of the seven flags in a local .env (the rows set them per test; CI runs them unset).

### Owner steps (names only)
1. Console: the MYEZ workspace, web search disabled, a spend limit; create `ANTHROPIC_API_KEY` on `web` by NAME (never on price-warmer; never ANTHROPIC_BASE_URL / ANTHROPIC_AUTH_TOKEN / ANTHROPIC_CUSTOM_HEADERS).
2. The orchestrator recompiles requirements.txt and requirements-dev.txt (anthropic==1.12.1 + docstring-parser) and runs pip-audit -r requirements.txt --strict before the PR.
3. After S81-12 + the consent v3 OTA: ENABLE_REQUEST_CONTEXT_HEADERS, ENABLE_LLM_LEDGER_V2, ENABLE_LLM_SPEND_BREAKER ON in their own windows.
4. Pre-v3 window: ENABLE_OPENAI_PRE_V3=true for the chosen window, then unset.
5. Flip order: ENABLE_ANTHROPIC_TEXT -> _VERDICT -> _CRITIC -> _MODERATION (after the 100-case parity set) -> _VISION last; one role per canary window on fresh fragrance pairs written into the ledger first; ENABLE_SONNET_ESCALATION after S81-07 confirms the between_tools shape.
6. Rollback: unset the variable (per call, immediate).

🤖 Generated with [Claude Code](https://claude.com/claude-code)
