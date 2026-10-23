# S81-04 unit spec: SPEND-BREAKER, per-Riyadh-day USD caps on every LLM dispatch

| Header | Value |
|---|---|
| Unit | S81-04 SPEND-BREAKER (PLAN_S81 M1, lane B; build order 6) |
| Flag | `ENABLE_LLM_SPEND_BREAKER` (new name, default OFF, read PER CALL with the house idiom) |
| Knobs (names only) | `LLM_SPEND_CAP_LIVE_USD`, `LLM_SPEND_CAP_ESCALATION_USD`, `LLM_SPEND_CAP_SEARCH_USD`, `LLM_SPEND_CAP_OFFCLOCK_USD` (defaults 3.00 / 1.00 / 0.50 / 2.00 USD; not secrets) |
| Worktree | `C:\Users\SynAckITPC\Documents\AI\sc-s81-s04` (detached at the base; read-only for the spec writer) |
| Branch | `feature/s81-s04-spend-breaker` (created by GREEN from the merged main that carries S81-03) |
| Base sha | `84c861f68ba3b23606c69ce2d1f78597e2f3037b` (= origin/main after #368 D03; `git rev-parse HEAD` == base) |
| git status --short | empty before and after every probe of this spec (measured 06:27 and at the end) |
| Measurement location | `C:\Users\SYNACK~1\AppData\Local\Temp\claude\C--Users-SynAckITPC-Documents-AI\fd8b3d1b-a491-48e3-953f-ca3a804fd9ca\scratchpad\S81-04\` (notes.md, base_pins.log, base_identity.log, comm_set.txt, build_comm.py, probe_prices.py, llm_pricing_0197ec1a.py, cost_table.txt) |
| Evidence pointers | `specs/S81_04_BRIEF.md`; PLAN_S81 M1 S81-04 + VERIFY "Ledger" bullet + Standing constraints; `specs/RULINGS_S81_03.md` R-S03-9, R-S03-10; `specs/GATE_S81_03.md` G-8; `runs/critic.json` cost_table (all under `sc-docs-70/docs/investigations/2026-10-22-session-81-state/`); PLAN_S80 section 0 + `runs/research/contract_freeze.json` (session-80 state folder); RULINGS_R0 R0-8 (session-80) |
| Sister units / contracts | DEPENDENCY S81-03 LLM-LEDGER-V2 (`feature/s81-s03-llm-ledger-v2` @ `0197ec1a`, on top of this base): the leaf `app/services/llm_pricing.py` and its `price_call`, `openai_usage_cost_usd`, `provider_of`, `SPEND_LANES`. GREEN starts only after S81-03 merges. Consumers of THIS unit's contract: S81-06 ROUTER (every Anthropic dispatch), S81-16 / S81-22 (batch submitters, crons), S81-21 (web_search lane), the Sonnet escalation unit (escalation lane), S81-09 DEVICE-QUOTA (may move the Riyadh day helper to a shared module). Known rebase hunks: CLAUDE.md flag-row anchor (shared with B4, D03, S81-03, ST1: union), `tests/test_s75_fanout_identity.py::UNIT_ENV` (S81-03 adds a name; this unit adds one), `tests/test_s81_s03_llm_ledger_v2.py` K1 literal (re-recorded here). ST1 (`ENABLE_USAGE_PATH_OFFLOOP`) touches usage_service / review_service only: no shared hunk. |
| Personal-data rule | No personal values anywhere (repo public): synthetic keys, synthetic model ids built at run time where a shape matters, no real names / emails / ids; no credential-shaped literal; no 8-digit run in a test (epochs are computed from `datetime` at run time, the K1 hash is split by concatenation as S81-03 does). Variable NAMES only. |

All line numbers are measured at `84c861f6` in this run (worktree file == `git show 84c861f6:` file; CRLF working copy, `core.autocrlf=true`). `abs` = `app/services/api_budget_service.py` (1,339 lines), `scs` = `app/services/structured_comparison_service.py` (9,758 lines), `main` = `app/main.py` (624 lines). Production flag state: the newest dated ledger line (session-81 ledger, ~06:40 2026-10-23) names no LLM-breaker flag; `ENABLE_LLM_SPEND_BREAKER` is a new name, so unset in production by construction; `ENABLE_LLM_PREFLIGHT_BREAKER` is not in any ledger line read, so it is UNKNOWN (R-A15): the spec designs for both states. `ENABLE_PRICE_PATH_REDIS_OFFLOOP` ON on web since 2026-10-11 and `ADAPTER_EXECUTOR_MAX_WORKERS=96` (CLAUDE.md S77 / FANOUT-STARVE rows) are cited, not probed.

-----------------------------------------------------------------------------------------------

## 0. What the unit does

A code-side daily spend bound for every LLM call, so a provider flip (S81-06 Anthropic, S81-16 batches, S81-21 search) or a cost bug cannot drain the credits; today the $400 console balance is the only outer bound (PLAN_S81 VERIFY standing risk). One new stdlib-plus-two-app-modules leaf `app/services/llm_spend_breaker.py` holds four lanes (live, escalation, search, offclock) with per-Asia/Riyadh-day USD caps. Before a dispatch a caller ADMITS with an UPPER BOUND (input at the model input rate + max output tokens at the output rate + searches at $0.01, priced through the S81-03 `price_call`): one Upstash GET of `llm_spend:<lane>:<riyadh_day>`; over cap = the EXISTING `LLMUnavailableError` (abs:702), so the coded `LLM_UNAVAILABLE` non-delivery, its refund and the client copy are unchanged. After a served response the caller RECORDS the actual list price: one atomic Upstash Lua EVAL (`INCRBYFLOAT` + `EXPIREAT` next Riyadh midnight + 1 h). Any Redis problem fails OPEN (a stated limit, one WARNING per process per minute). This unit wires it at `guarded_llm_create` (every OpenAI chat completion, lane live) and at the two compare entries (a read-only "lane exhausted" preflight that returns the existing `LLM_UNAVAILABLE` envelope before any paid provider work, the W1-3 placement), adds an additive `/health` object `llm_spend` present only once the breaker ran in the process, and states the contract every future Anthropic call and batch submitter follows. Flag OFF: no admit, no record, no Redis command, no thread hop, no health key; every response byte-identical.

-----------------------------------------------------------------------------------------------

## 1. Base state (MEASURED at 84c861f6)

### 1.1 The dispatch chokepoint `guarded_llm_create` (abs:954-1035)

| What | Where | Measured fact |
|---|---|---|
| Signature | abs:954 | `async def guarded_llm_create(client, **kwargs):` |
| U3c prologue | abs:980-983 | `kwargs["store"] = False` (980, the FIRST body statement); `eb = kwargs.get("extra_body")` (981); the `extra_body` store scrub (982-983). |
| W1-3 flag-OFF branch | abs:984-987 | `if not llm_preflight_breaker_enabled():` -> `response = await client.chat.completions.create(**kwargs)` (985) -> `record_openai_response(kwargs.get("model"), response)` (986) -> `return response` (987). |
| W1-3 flag-ON admission | abs:988-992 | `admitted, outcome_matters, probe = _openai_dispatch_admission()` (988); denied -> `raise LLMUnavailableError("openai circuit breaker denied admission <U+2014> dispatch suppressed")` (990-992). |
| W1-3 dispatch + accounting | abs:993-1031 | `create(**kwargs)` (994); `except asyncio.CancelledError` (995: probe release, re-raise), `except Exception` (transient -> `openai_record_failure`; probe -> success-or-release), `except BaseException` (probe release). |
| Served tail | abs:1032-1035 | `record_openai_response(kwargs.get("model"), response)` (1032); `if outcome_matters: openai_record_success()` (1033-1034); `return response` (1035). |
| Dispatch count | measured (ast) | exactly 2 `create` calls in the function (`ast.walk`, attr == "create"). |
| K1 hash | measured | `sha256(ast.dump(fn, include_attributes=False))` = `8fa87b616` + `45971d65a41d38cf70938f38d441d0b0a0d91a055b16d74b1b3a63d` on CPython 3.12.9 (venv) == the S81-03 `K1_GUARDED_AST_SHA` literal (`tests/test_s81_s03_llm_ledger_v2.py:169` on `0197ec1a`, row `test_k1_guarded_llm_create_untouched` :2417-2425, docstring "S81-04 re-records it deliberately, R-S03-10"). |
| Callers | measured (grep) | 15 dispatch sites through the module attribute `_llm_breaker.guarded_llm_create`: extraction_service :1385, :1525, :1583, :1742, :1791, :1847, :2643, :2685; openai_service :473 (vision), :638, :749, :824, :886; url_extraction_service :945; image_service :186; verdict_critique_service :174. Every one passes `token_limit_kwargs(...)` (max_tokens or max_completion_tokens) and a `messages` list; the vision sites send `{"type": "image_url", "image_url": {"url": "data:<mime>;base64,<...>", "detail": "auto"}}` parts (openai_service :451-452, :629-632). |
| Verdict fallback matcher | extraction_service:2661-2671 | `err_msg = str(primary_err).lower()`; falls back to the standard model iff `"429" in err_msg or "rate" in err_msg or "quota" in err_msg`. A refusal message must contain none of the three substrings (so a refused primary verdict never dispatches a second call). |

### 1.2 The breaker family the new leaf sits beside (abs)

| Symbol | Where | Measured fact |
|---|---|---|
| `PROVIDER_CONFIGS` | abs:37-95 | keys exactly `firecrawl`, `scrapedo`, `brightdata`, `serper`, `openai`, `youtube`; the `openai` row is a request-count row read by nothing (comment abs:63-75). No `llm` key (R-S03-9 reserves the name for the S81-03 admin block). |
| `has_budget` | abs:388-416 | fail-OPEN: `raw is None` -> True (abs:398-399, "No usage yet or Redis down"); `except Exception` -> WARNING + True (abs:414-416). The brief's ":390-392" is the pre-W0 line; measured here. |
| `serper_gate_allows` | abs:256-270 | fail-OPEN `except Exception` -> WARNING + True (abs:268-270). The brief's ":247-249" is the pre-W0 line. |
| `record_usage` | abs:485-510 | `redis_client.incrby` direct (abs:494-495, imported lazily from cache_service), `_redis_expire` for monthly; fail-open WARNING (abs:509-510). |
| `is_circuit_closed` | abs:522-585 | NOT read-only (half-open `_redis_incr` of the per-trip probe key, abs:563). |
| `LLMUnavailableError` | abs:702-709 | `class LLMUnavailableError(RuntimeError)`; docstring: message avoids "429"/"rate"/"quota". |
| `llm_preflight_breaker_enabled` | abs:712-717 | `os.getenv(_LLM_PREFLIGHT_FLAG, "").strip().lower() in ("true","1","yes","on")` (default `""`, not `"false"`). |
| `_openai_dispatch_admission` | abs:795-823 | returns `(admitted, outcome_matters, probe)`; a half-open admission spends the single probe slot (abs:819 -> `is_circuit_closed`). Any refusal placed AFTER this call would hold the probe and wedge the breaker: the spend admit must run BEFORE it. |
| Imports | abs:6-17 | `asyncio, collections.abc, json, os, time, logging, datetime`; `from app.services.cache_service import _redis_get, _redis_set, _redis_incr, _redis_expire`; `from app.services.openai_pricing import record_openai_response`. |

### 1.3 Upstash client and the "atomic Lua" precedent (measured, not assumed)

- `cache_service.redis_client = _build_redis_client()` (cache_service:166), module level. `https://` URL -> `upstash_redis.Redis(url=..., token=...)` (cache_service:88-135; `rest_retries=0` + a bounded transport under `ENABLE_UPSTASH_BOUNDED_TRANSPORT`); any other URL -> `redis.from_url(..., decode_responses=True)` (cache_service:141-158). Under the free test tier `UPSTASH_REDIS_URL` / `UPSTASH_REDIS_TOKEN` are in `tests/_env_safety.CREDENTIALS_UNSET` (:114-115), so `redis_client is None` in every test: every flag-ON row installs a fake client on `cache_service.redis_client`.
- Pinned versions on the venv (`pip show`): `upstash-redis 1.7.0`, `redis 8.1.0` (requirements.txt :187, :137).
- upstash-redis 1.7.0 `commands.py`: `eval(self, script, keys=None, args=None)` (:2639; builds `["EVAL", script, len(keys), *keys, *args]` :2677-2687); `incrbyfloat(key, increment)` (:4495); `expireat(key, unix_time_seconds, nx, xx, gt, lt)` (:757); `get(key)` (:4313). redis-py 8.1.0: `Redis.eval(script, numkeys, *keys_and_args)` (inspect.signature). The two call shapes DIFFER: the leaf dispatches on the client type (section 2.6).
- NO Lua exists in `app/` at base (`grep -rn "\.eval(" app/` = 0 hits). The brief's "atomic Lua pattern of usage_service._atomic_consume" is measured as: `_atomic_consume` (usage_service:235-282) is INCRBY -> check -> DECRBY rollback (no script), offloaded by `_atomic_consume_async` through `asyncio.to_thread` only under `ENABLE_ASYNC_REDIS_OFFLOAD` (usage_service:292-297). This unit therefore introduces the repo's FIRST Lua script; PLAN_S81's device-quota unit (S81-09) will be the second.
- Upstash latency fact cited (CLAUDE.md S78-SM row): an Upstash GET was 163-203 ms with TLS. A blocking GET inline on the loop at each of the ~8-14 LLM dispatches of a compare would freeze the loop 1.3-2.8 s per compare: every Redis command of this unit runs on a worker thread (section 2.5).

### 1.4 The non-delivery path the refusal travels

| Surface | Where | Measured fact |
|---|---|---|
| Copy | scs:1732-1734 | `LLM_UNAVAILABLE_FRIENDLY_MESSAGE` = "Still warming up the comparison engine <U+2014> give it another tap in a moment." |
| W1-3 preflight helper | scs:1755-1768 | `_llm_preflight_short_circuits()` = flag AND NOT `openai_preflight_allows_compare()` (read-only). |
| Envelope | scs:3972-3990 | `_llm_unavailable_envelope()` -> `{success: False, error: LLM_UNAVAILABLE_FRIENDLY_MESSAGE, code: "LLM_UNAVAILABLE", elapsed_seconds: 0.0, total_cost, api_calls}`. |
| REST entry | scs:3992 / 4032-4039 | `compare_from_text`; W1-3 short-circuit 4032-4038 (`return self._llm_unavailable_envelope()`), then `_t0 = time.time()` 4039, the hard-cap `wait_for` 4040+. |
| Stream entry | scs:4724 / 4762-4769 | `compare_from_text_streaming`; W1-3 short-circuit 4762-4769 (`yield ("error", self._llm_unavailable_envelope())`, `return`), placed before the L1 content-safety prefilter. |
| Route mapping | text_routes:522-545 | `_surface_comparison_failure`: `code in ("TIMEOUT", "LLM_UNAVAILABLE")` -> `HTTPException(503, detail={code, error})` (a CODED 503, never bare). |
| Refund | text_routes:677, :885 (POST/GET refund before the surface call, M13-37), :1172 / :1308-1323 (stream `had_error` -> refund) | unchanged. |
| Camera | image_routes:353-361 | `isinstance(e, LLMUnavailableError) or _openai_failure_is_transient(e)` on the vision call -> 503 `{code: LLM_UNAVAILABLE}` after the refunds (#258). A compare that returns the envelope reaches the camera failure envelope (ON in prod) carrying `LLM_UNAVAILABLE`, which build 3 maps to the outage copy (CLAUDE.md #258 `classifyUnsuccessfulCameraComparison`). |
| URL mode | url_extraction_service:945-971, :1343-1353 | `extract_with_ai` swallows any exception into `{"error": str(e)}` (:968-971); a verdict failure returns `{success: False, code: "LLM_UNAVAILABLE"}` (:1343-1353). |
| Build-3 contract | PLAN_S80 section 0 items 2-3 | `LLM_UNAVAILABLE` is one of the nine codes build 3 maps; never a bare 503. |

Consequence measured: a refusal raised at a call site deep in a compare is swallowed by that caller (e.g. `parse_product_query` returns `PARSE_PRODUCT_QUERY_ERROR`, extraction_service:1551-1553) and surfaces as a parse failure or a degraded result, not as `LLM_UNAVAILABLE`. The coded non-delivery the brief requires therefore needs the compare-entry preflight (change 4), exactly as W1-3 needed it; the call-site admit is the backstop.

### 1.5 /health (main)

| What | Where | Measured fact |
|---|---|---|
| Handler | main:598-619 | returns `{"status": "healthy", "message": "MYEZ API is running", **loop_lag_snapshot(), **price_parse_pool_snapshot(), **redis_offloop_pool_snapshot(), **adapter_executor_snapshot(), **brightdata_auth_health_snapshot()}` (spreads at 614-618). |
| Shape helper | main:302-312 | `_module_snapshot(module_name, fn_name)`: `getattr(sys.modules.get(module_name), fn_name, None)`; `{}` when absent or raising; `fn() or {}`. |
| RO18 precedent | main:285-299 | `redis_offloop_pool` key present only once the pool exists; no key, no null otherwise. |
| Purity pin | tests/test_health_loop_lag.py:190-212 | the handler source has no `await ` and none of `asyncio.sleep`, `requests.`, `httpx.`, `get_cached`, `execute(`. |
| Exact-key pin | tests/test_s77_redis_offloop.py:2210-2213, :2255, :2274, :2287 | `_BASE_HEALTH_KEYS` = {status, message, loop_lag_ms, loop_lag_max_ms, loop_lag_max_60s_ms, price_parse_pool, adapter_executor, brightdata_auth}; `set(body) <= _BASE_HEALTH_KEYS` (+ the pool key). The new key must stay absent unless the breaker ran IN THAT PROCESS, and the unit's own test file resets the leaf state in teardown so no later file sees it. |

### 1.6 The S81-03 leaf contract this unit consumes (read from `0197ec1a`, sha256 of the leaf bytes `504b9d5e...a18126`)

- `price_call(provider, model, *, input_tokens=0, output_tokens=0, cache_read_tokens=0, cache_write_5m_tokens=0, cache_write_1h_tokens=0, web_search_requests=0, batch=False) -> Optional[float]` (llm_pricing:171-212): None (never 0) for a count that is not a non-negative non-bool int, an id outside the exact rows, an unknown provider, an OpenAI call carrying a cache write / web search / batch, a Sonnet request above 200,000 prompt tokens. OpenAI delegates to `openai_pricing.list_price_usd(model, input + cache_read, output, cache_read)`; Anthropic adds `web_search_requests * 0.01` (WEB_SEARCH_USD_PER_REQUEST, :78).
- `openai_usage_cost_usd(model, usage) -> float` (llm_pricing:237-248): list price of a served OpenAI usage (cached at the cached rate); the base mini-rate estimate when the model is unpriced; 0.0 for a None usage.
- `provider_of(model)` (:156-164): "openai" for `gpt-` / `omni-moderation-`, "anthropic" for `claude-`, else None.
- `SPEND_LANES = ("live", "escalation", "search", "offclock")` (:120): the S81-03 migration 050 vocabulary == this unit's lanes.
- Probed on those bytes (probe_prices.py): `price_call("openai","gpt-4o-mini",input_tokens=4020,output_tokens=800)` = 0.001083; gpt-4o same counts = 0.01805; mini 50120/500 = 0.007818; gpt-4o 50120/500 = 0.1303; mini 16020/16384 = 0.0122334; `("openai","gpt-4o-mini",..., web_search_requests=1)` = None; `("anthropic","claude-haiku-5-5",input_tokens=1000,output_tokens=500,web_search_requests=2)` = 0.02035; sonnet 1000/500 = 0.007; an unpriced id = None; `openai_usage_cost_usd("gpt-4o-mini", usage 1000/200)` = 0.00027; the same on an unpriced id = 0.00027 (the legacy estimate); None usage = 0.0.
- Import rule of the S81-03 A1 row (`test_a1_leaf_exists_and_imports_only_stdlib_and_openai_pricing`, :425-462): it scans every `app/**/*.py` for an `ast.Attribute` named `_LEDGER`; the new leaf must never read `<module>._LEDGER`.
- Until S81-03 merges, `importlib.util.find_spec("app.services.llm_pricing")` is None at this base: RED rows that need it assert that probe first (AssertionError, never ImportError).

### 1.7 Lane sizing input (runs/critic.json cost_table)

Today: OpenAI at list price ~$0.021 per compare (gpt-4o verdict + mini workers) plus ~$0.003 Serper. Haiku-only ~$0.0037; Haiku workers + Sonnet verdict ~$0.0235; with 3 web searches ~$0.036-0.053. At the $3.00 live default the lane admits about 140 OpenAI-list-price compares per Riyadh day (the real OpenAI bill is lower because of the data-sharing allowance, CLAUDE.md D3); about 800 Haiku-only compares. This is an activation precondition (section 8): with OpenAI serving, the owner checks daily volume x $0.021 against the cap BEFORE the flip.

### 1.8 Flag-reader idiom and guards the new code must not trip

- House idiom: `os.getenv(FLAG, "false").strip().lower() in ("true", "1", "yes", "on")`, read per call (S81-03 `llm_ledger_v2_enabled` llm_pricing:151-153 is the template).
- `tests/test_u3c_store_false_pin.py`: T01 (:231-245) store assignment is body[0], one write; T01b (:248-280) no `kwargs.<m>()` except `.get`, no rebinding, writes into kwargs only in the prologue and only `store`/`extra_body`, each dispatch exactly `create(**kwargs)`; T01c (:283-310) every Load of `kwargs` is `kwargs.get(...)`, `kwargs[...]` or `create(**kwargs)`, and `dispatch == 2`. CONSEQUENCE: the new code passes `kwargs.get("model")`, `kwargs.get("messages")`, `kwargs.get("max_tokens")`, `kwargs.get("max_completion_tokens")` individually, never `kwargs`. T02 (:313-330): no OpenAI SDK surface outside the chokepoint under app/ (the leaf has none). T03 (:333-361): call-site census >= 15.
- `tests/test_model_config.py` stray model-id literal pin over app/: the leaf contains no model-id literal (not even in a comment); synthetic ids live in tests only, built at run time.
- `tests/test_s81_s03_llm_ledger_v2.py` A1 `_LEDGER` scan (1.6).
- No new credential name: the four cap knobs and the flag are not secrets; `tests/_env_safety.CREDENTIALS_UNSET` (:110-) is untouched.
- Log rule: every line carries constants, ints (cents) or type names only; no exception text, no query, no model id value; WARNING only (no ERROR outside an except arm; this unit logs no ERROR).
- Line endings: abs, scs, main, CLAUDE.md and every `tests/*.py` are CRLF in the working copy (`file`: "with CRLF line terminators"; abs has 1,339 CRLF); the index is LF. GREEN edits with the Edit tool (preserves CRLF); new files (`llm_spend_breaker.py`, the test file) are written LF and committed LF; `git diff --stat` must show no whole-file diff.

### 1.9 Pins measured at base that encode this region

`tests/test_u3c_store_false_pin.py`, `tests/test_openai_breaker.py` (helpers `_dict_breaker_redis` :97, `_patch_breaker_redis` :127, `_open_breaker_seed` :137, `_half_open_breaker_seed` :149, `_mock_openai_client` :181, `_arm_prod_search_config` :229, `_FanOutCounters` :244, `_run_compare` :313, `_run_stream` :322; entry rows :389-475), `tests/test_retro_w1_3.py`, `tests/test_api_budget_service.py`, `tests/test_m13_31_half_open_probe.py`, `tests/test_cost_meter_s74.py`, `tests/test_model_config_enforced.py`, `tests/test_image_identify_llm_unavailable_s69.py`, `tests/test_health_loop_lag.py`, `tests/test_retro_w1_7_w1_10.py`, `tests/test_health_brand_s69.py`, `tests/test_s77_redis_offloop.py`, `tests/test_s75_fanout_starve.py`, the FY25 node `tests/test_s75_fanout_identity.py::test_FY25_flag_off_compare_identity_matches_main` (UNIT_ENV :60-64), `tests/test_w4_13_flag_off_ledger.py`; on the S81-03 branch `tests/test_s81_s03_llm_ledger_v2.py` (K1).

### 1.10 Base pass state of the files this unit touches (bounded runner, base 84c861f6)

| Run | Files | Result | [pyt] line |
|---|---|---|---|
| s04-base-pins | test_u3c_store_false_pin, test_openai_breaker, test_retro_w1_3, test_api_budget_service, test_health_loop_lag, test_retro_w1_7_w1_10, test_image_identify_llm_unavailable_s69, test_model_config_enforced, test_cost_meter_s74, test_m13_31_half_open_probe | 289 passed, 13 warnings in 22.33 s | `[pyt] tag=s04-base-pins start=2026-10-23 06:39:23 end=2026-10-23 06:39:49 elapsed=26s bound=1200s status=OK rc=0` |
| | | `[hermeticity] sentinel checked 289 test(s)`; `[netguard] blocked 141 attempt(s) from 7 node(s)` (pre-existing: 6 test_openai_breaker nodes `socket.create_connection neutralized.supabase.invalid:443`, 1 test_retro_w1_3 node `curl_cffi.Session.request` to a shop host; all blocked, all in the ratchet baseline class) | |
| s04-base-identity | FY25 node, test_w4_13_flag_off_ledger, test_health_brand_s69, test_s77_redis_offloop, test_s75_fanout_starve | 271 passed, 10 warnings in 27.22 s | `[pyt] tag=s04-base-identity start=2026-10-23 06:40:25 end=2026-10-23 06:40:57 elapsed=32s bound=1200s status=OK rc=0` |
| | | `[hermeticity] sentinel checked 271 test(s)`; `[netguard] blocked 0 attempt(s) from 0 node(s)` | |

NOT MEASURED here: `tests/test_s81_s03_llm_ledger_v2.py` (absent at this base; it is measured by GREEN on the merged main before the K1 edit), the comm set at base (GREEN runs it at base and head, section 7), `tests/test_ci_gates.py` / `tests/test_behavior_dimension_translation.py` (CLAUDE.md readers; GREEN runs them base and head).

-----------------------------------------------------------------------------------------------

## 2. Contract

### 2.1 Flag and knobs (all read PER CALL, never at import)

| Name | Reader | Rule |
|---|---|---|
| `ENABLE_LLM_SPEND_BREAKER` | `llm_spend_breaker.spend_breaker_enabled()` | `os.getenv(FLAG, "false").strip().lower() in ("true", "1", "yes", "on")`; the FIRST statement of every gated branch, so OFF reads no other state. |
| `LLM_SPEND_CAP_<LANE>_USD` (LIVE, ESCALATION, SEARCH, OFFCLOCK) | `cap_usd(lane)` | `raw = os.getenv(name)`; unset / blank after strip / not a float / not finite (`inf`, `-inf`, `nan`) / `<= 0` -> the lane default; else `float(raw.strip())`. Defaults: live 3.00, escalation 1.00, search 0.50, offclock 2.00 (owner decision "Breaker caps [$3/$1/$0.50/$2 per Riyadh day]"). |

### 2.2 The leaf `app/services/llm_spend_breaker.py` (new; LF; pure ASCII)

Module imports (top level): stdlib (`asyncio`, `json`, `logging`, `math`, `os`, `threading`, `time`, `datetime`, `typing`); `from app.services import cache_service as _cache_service`; `from app.services import llm_pricing as _llm_pricing` (the S81-03 leaf, through the module attribute, ruling BL4); `from app.utils import async_utils as _async_utils`. `app.services.api_budget_service` is imported ONLY inside the refusal arm (`from app.services.api_budget_service import LLMUnavailableError`), because abs imports this leaf at its top (no import cycle; both modules are loaded when the arm runs). No model-id literal, no `._LEDGER` attribute, no OpenAI / Anthropic SDK surface.

| Symbol | Type / value | Contract |
|---|---|---|
| `FLAG` | `"ENABLE_LLM_SPEND_BREAKER"` | |
| `LANE_LIVE`, `LANE_ESCALATION`, `LANE_SEARCH`, `LANE_OFFCLOCK` | `"live"`, `"escalation"`, `"search"`, `"offclock"` | |
| `LANES` | `tuple` == `_llm_pricing.SPEND_LANES` | same order. |
| `DEFAULT_CAPS_USD` | `{"live": 3.0, "escalation": 1.0, "search": 0.5, "offclock": 2.0}` | |
| `CAP_ENV` | `{"live": "LLM_SPEND_CAP_LIVE_USD", "escalation": "LLM_SPEND_CAP_ESCALATION_USD", "search": "LLM_SPEND_CAP_SEARCH_USD", "offclock": "LLM_SPEND_CAP_OFFCLOCK_USD"}` | |
| `RIYADH_UTC_OFFSET_HOURS` | `3` | fixed, no DST (owner decision 5). |
| `KEY_PREFIX` | `"llm_spend"` | key `llm_spend:<lane>:<YYYY-MM-DD>`. |
| `OVERHEAD_TOKENS_PER_CALL` | `16` | |
| `OVERHEAD_TOKENS_PER_MESSAGE` | `4` | |
| `IMAGE_PART_TOKEN_BOUND` | `50000` | one image part, whatever its data-URL length (above OpenAI's high-detail maximum for the mini model; an ASSUMPTION from the published per-tile rule, re-verified by S81-07; the alternative, counting base64 bytes, prices one 1 MB photo at about $3.4 on gpt-4o and would refuse every camera call). |
| `DEFAULT_OUTPUT_TOKEN_BOUND` | `16384` | when neither max_tokens nor max_completion_tokens is a positive int. |
| `RECORD_SCRIPT` | `str` | exactly: `local v = redis.call('INCRBYFLOAT', KEYS[1], ARGV[1])` / `redis.call('EXPIREAT', KEYS[1], ARGV[2])` / `return v` (three lines, LF). INCRBYFLOAT returns a bulk string, returned unchanged (a Lua number would truncate to an integer). |
| `REFUSAL_MESSAGE` | `"llm spend cap reached for lane %s; dispatch suppressed"` | formatted with the lane; contains none of `429`, `rate`, `quota` (1.1 matcher). |
| `spend_breaker_enabled() -> bool` | 2.1 | |
| `cap_usd(lane) -> float` | 2.1 | `ValueError` for a lane outside `LANES` (a programming error, never fail-open). |
| `riyadh_day(now=None) -> Tuple[str, int]` | `(day, expireat)` | `now` = an aware UTC datetime (default `_utcnow()`); `day = (now + 3 h).date().isoformat()`; `expireat` = epoch seconds of (that day + 1 day at 00:00 Riyadh, i.e. 21:00 UTC of `day`) + 3600, an int. Module-local; S81-09 may move it to a shared helper (stated). |
| `spend_key(lane, day) -> str` | `"llm_spend:%s:%s"` | `ValueError` for an unknown lane. |
| `prompt_token_upper_bound(messages) -> int` | | `OVERHEAD_TOKENS_PER_CALL` + for each element of a list/tuple `messages`: `OVERHEAD_TOKENS_PER_MESSAGE` + content bound, where content `str` -> `len(content.encode("utf-8"))` (byte-level BPE: one token covers at least one byte); content list -> sum per part: a dict with `type == "text"` -> UTF-8 bytes of `part.get("text")` as str; `type in ("image_url", "input_image", "image")` -> `IMAGE_PART_TOKEN_BOUND`; any other part -> UTF-8 bytes of `json.dumps(part, default=str)`; content None -> 0; any other content -> UTF-8 bytes of `str(content)`. A non-list `messages` -> `OVERHEAD_TOKENS_PER_CALL`. Never raises. |
| `output_token_bound(max_tokens, max_completion_tokens) -> int` | | the first of the two that is an int, not a bool, `> 0`; else `DEFAULT_OUTPUT_TOKEN_BOUND`. |
| `upper_bound_usd(provider, model, prompt_tokens, max_tokens, web_search_max_uses=0) -> Optional[float]` | | `_llm_pricing.price_call(provider, model, input_tokens=prompt_tokens, output_tokens=max_tokens, web_search_requests=web_search_max_uses)` (sync, batch False); None when unpriced. |
| `admit(lane, upper_bound_usd) -> None` | sync, blocking (scripts, batch submitters, worker threads) | Flag NOT read here (callers gate). `ValueError` for an unknown lane before any command. Reads ONE command `GET llm_spend:<lane>:<day>` through `_client()`. spent = 0.0 for a missing key; a stored value that is not a finite float >= 0 -> fail-open (type `ValueError`). Refuses iff `spent + ub > cap_usd(lane)` (STRICT; `ub` None -> 0.0 plus the unpriced WARNING, so an unpriced call is refused only when the lane is already strictly over cap). Refusal: one WARNING `[SPEND] lane=%s cap reached (spent_cents=%d cap_cents=%d bound_cents=%d) -- dispatch refused` (cents = `int(round(x * 100))`; `math.ceil` is rejected: measured `0.07 * 100` = `7.000000000000001`, ceil 8) and `raise LLMUnavailableError(REFUSAL_MESSAGE % lane)` (the exact abs class). On every successful read the observation `(spent, day)` is stored for /health. Fail-open: `_client()` None, the GET raising, or a bad stored value -> return None (admitted) and the rate-limited fail-open WARNING. |
| `record(lane, actual_usd) -> None` | sync, blocking | `ValueError` for an unknown lane. `actual_usd` not an int/float, a bool, not finite, or `<= 0` -> return, no command. Else ONE command: the Lua `RECORD_SCRIPT` with `keys=[key]`, `args=[f"{actual_usd:.10f}", str(expireat)]` through `_eval(client, script, keys, args)`; the returned string parsed as float is stored as the observation. Fail-open on any exception or `_client()` None (no raise, rate-limited WARNING). |
| `async admit_async(lane, ub) -> None` | live path | `await asyncio.to_thread(admit, lane, ub)` (the loop's default executor = `qaren-worker`, 96 workers on web); the GET never runs on the loop thread; `LLMUnavailableError` propagates. |
| `record_soon(lane, actual_usd) -> Optional[asyncio.Task]` | live path, NON-awaited | when `record` would issue a command: `_async_utils.fire_and_forget(asyncio.to_thread(record, lane, actual_usd), "llm_spend.record")` and return the task (registered in `_BACKGROUND_TASKS`, so the W1-6 shutdown drain covers it; a request cancellation never cancels it); else None. |
| `async admit_openai_dispatch(model, messages, max_tokens, max_completion_tokens) -> str` | the chokepoint helper | `ub = upper_bound_usd(_llm_pricing.provider_of(model), model, prompt_token_upper_bound(messages), output_token_bound(max_tokens, max_completion_tokens))`; `await admit_async(LANE_LIVE, ub)`; returns `LANE_LIVE`. |
| `record_openai_response_soon(lane, model, response) -> Optional[asyncio.Task]` | | `actual = _llm_pricing.openai_usage_cost_usd(model, getattr(response, "usage", None))`; `return record_soon(lane, actual)`; never raises (any exception -> the fail-open WARNING, None). |
| `async entry_refuses_async(lane) -> bool` | compare-entry preflight | read-only: one GET off the loop; True iff the stored spent `>= cap_usd(lane)` (the lane is exhausted); then one WARNING `[SPEND] lane=%s cap reached (spent_cents=%d cap_cents=%d) -- short-circuiting the compare BEFORE the provider fan-out` (no query, unlike W1-3's line). Fail-open -> False. Stores the observation. |
| `spend_snapshot() -> Dict[str, Any]` | /health | `{}` until a lane has an observation in this process; else `{"llm_spend": {lane: {"spent_usd": round(spent, 6), "cap_usd": cap_usd(lane), "day": day} for each observed lane}}` (unobserved lanes omitted, no None anywhere). Pure: no Redis command, no thread, never raises (any exception -> `{}`). |
| `_utcnow()` | test seam [prod: `datetime.now(timezone.utc)`] | |
| `_monotonic()` | test seam [prod: `time.monotonic()`] | |
| `_client()` | test seam [prod: `_cache_service.redis_client`, read per call through the module attribute, never `from ... import redis_client` (the #183 / reload hazard)] | |
| `_FAILOPEN_WARN_INTERVAL_SECONDS` | test seam [prod: `60.0`] | |
| `_reset_spend_breaker_state()` | test-only | clears observations and both warn timestamps. |

### 2.3 Log templates (WARNING; constants, ints and type names only)

- `[SPEND] lane=%s cap reached (spent_cents=%d cap_cents=%d bound_cents=%d) -- dispatch refused`
- `[SPEND] lane=%s cap reached (spent_cents=%d cap_cents=%d) -- short-circuiting the compare BEFORE the provider fan-out`
- `[SPEND] breaker fail-open (%s) -- admitting and not recording` (`type(exc).__name__`, or `RedisUnconfigured` when `_client()` is None); at most one per process per `_FAILOPEN_WARN_INTERVAL_SECONDS` (the first is logged; later ones while `_monotonic() - last < interval` are dropped).
- `[SPEND] lane=%s upper bound unpriced -- admitting on the spent total` (logged by `admit` when the bound is None; the brief's "a WARNING by type" is read as "no value": a model id is configuration, not a constant, and `type(model).__name__` would always print `str`); rate-limited the same way on its own timestamp.

### 2.4 Chokepoint wiring (abs `guarded_llm_create`)

Inserted after the U3c prologue (after abs:983), before `if not llm_preflight_breaker_enabled():` (abs:984):

```
spend_lane = None
if _llm_spend_breaker.spend_breaker_enabled():
    spend_lane = await _llm_spend_breaker.admit_openai_dispatch(
        kwargs.get("model"), kwargs.get("messages"),
        kwargs.get("max_tokens"), kwargs.get("max_completion_tokens"),
    )
```

and, on BOTH served tails, right after `record_openai_response(kwargs.get("model"), response)` (abs:986 and abs:1032):

```
if spend_lane is not None:
    _llm_spend_breaker.record_openai_response_soon(spend_lane, kwargs.get("model"), response)
```

Import at the top of abs beside the openai_pricing import: `from app.services import llm_spend_breaker as _llm_spend_breaker` (module attribute, patchable). Invariants: the store assignment stays body[0]; exactly two `create(**kwargs)`; kwargs is only read through `.get`; the spend admit precedes `_openai_dispatch_admission()` (a refusal never holds the half-open probe); a raising or cancelled `create` records nothing; the W1-3 accounting is unchanged.

### 2.5 Compare-entry preflight (scs)

After the W1-3 block of `compare_from_text` (after scs:4038, before `_t0 = time.time()` at scs:4039):

```
if (_llm_spend_breaker.spend_breaker_enabled()
        and await _llm_spend_breaker.entry_refuses_async(_llm_spend_breaker.LANE_LIVE)):
    return self._llm_unavailable_envelope()
```

After the W1-3 block of `compare_from_text_streaming` (after scs:4769):

```
if (_llm_spend_breaker.spend_breaker_enabled()
        and await _llm_spend_breaker.entry_refuses_async(_llm_spend_breaker.LANE_LIVE)):
    yield ("error", self._llm_unavailable_envelope())
    return
```

Import in scs beside the abs import block (scs:68-75): `from app.services import llm_spend_breaker as _llm_spend_breaker`. Flag OFF: the `and` short-circuits before the await, so no coroutine is created and there is no new suspension point.

### 2.6 Client-shape dispatch (`_eval`)

`_eval(client, script, keys, args)`: when `type(client).__module__.split(".")[0] == "upstash_redis"` -> `client.eval(script, keys=list(keys), args=list(args))`; else (redis-py and anything else) -> `client.eval(script, len(keys), *keys, *args)`. The GET is `client.get(key)` on both (bytes decoded as utf-8 if `hasattr(result, "decode")`, the `_redis_get` rule).

### 2.7 /health (main)

New helper after `brightdata_auth_health_snapshot` (main:322-326): `def llm_spend_health_snapshot() -> dict: return _module_snapshot("app.services.llm_spend_breaker", "spend_snapshot")` with a docstring naming S81-04; the handler gains `**llm_spend_health_snapshot(),` after main:618. No `await`, no I/O (the purity pin).

### 2.8 The contract for every later LLM dispatch (stated here, binding on S81-06 / S81-16 / S81-21 / S81-22 / the escalation unit)

1. Gate: `if llm_spend_breaker.spend_breaker_enabled():` as the first statement of the gated branch.
2. Before the provider call: `await admit_async(lane, upper_bound_usd(provider, model, prompt_tokens, max_tokens, web_search_max_uses))` on the live path, `admit(...)` in scripts / cron / worker processes. Lane: `live` for a request-path Haiku/OpenAI call; `escalation` for a Sonnet escalation; `search` for a call carrying `web_search` (the whole call's bound, max_uses included); `offclock` for Batch submissions and crons (the bound of the whole batch, priced with `batch=True` through `price_call` by the submitter). `prompt_tokens` = `count_tokens` when the adapter has it, else `prompt_token_upper_bound(messages)`.
3. After a served response: `record_soon(lane, actual)` (live) or `record(lane, actual)` (off-clock), `actual` = `price_call(...)` over the served usage (Anthropic: input, cache read, the two cache writes, web_search_requests, batch). A refused call raises `LLMUnavailableError`; an Anthropic adapter maps it like its own breaker refusal (never a substring match).
4. A batch is admitted ONCE at submit with its full upper bound and recorded ONCE when its results land (the offclock key of the submit day receives the record of the result day only if the same Riyadh day; otherwise the result day's key; stated limit L7).
5. No PROVIDER_CONFIGS entry: the breaker is not a provider (R-S03-9 reserves `llm`).

### 2.9 Every new key and its type

| Key | Where | Type |
|---|---|---|
| `llm_spend` | /health top level | object, present only once a lane was observed in the process |
| `llm_spend.<lane>` | /health | object for an observed lane only (`live`, `escalation`, `search`, `offclock`) |
| `llm_spend.<lane>.spent_usd` | /health | float (6 decimals), the last value this process read or wrote for that lane |
| `llm_spend.<lane>.cap_usd` | /health | float, `cap_usd(lane)` at the /health call |
| `llm_spend.<lane>.day` | /health | str `YYYY-MM-DD`, the Riyadh day of the observation |
| `llm_spend:<lane>:<YYYY-MM-DD>` | Upstash | string float (INCRBYFLOAT), EXPIREAT next Riyadh midnight + 1 h |

No response key of any compare route is added, removed, renamed or retyped; the refusal travels only through the existing `LLM_UNAVAILABLE` envelope / SSE `error` event / camera 503.

### 2.10 Failure table

| Condition | Flag OFF | Flag ON |
|---|---|---|
| Any call | base | admit then dispatch then non-awaited record |
| Lane spent + ub <= cap | n/a | admitted |
| Lane spent + ub > cap | n/a | `LLMUnavailableError` before dispatch (no create, no W1-3 admission, no record) |
| Compare entry, lane spent >= cap | n/a | `LLM_UNAVAILABLE` envelope (REST 503 coded, refund) / SSE `error` (refund); zero provider calls |
| Compare entry, spent < cap but a later call over cap | n/a | that call refused at the chokepoint; its caller degrades as on any LLM failure (stated limit L3) |
| Redis unconfigured / GET raises / EVAL raises / bad stored value | n/a | fail-open: admitted, not recorded, one WARNING per minute (L1) |
| Unpriced model (ub None) | n/a | admitted unless spent > cap; one WARNING per minute |
| create raises / cancelled | base | no record (L4) |
| Response without usage (stream) | base | no record (actual 0.0) |
| Unknown lane | n/a | `ValueError` (programming error) |
| /health before any observation | no key | no key |
| /health snapshot raising | n/a | key absent, 200 |

### 2.11 Flag-OFF identity (the main invariant)

With the flag unset, `false`, `0`, `off`, `no`, `""`, `" FALSE "` or garbage, and the four cap knobs SET to synthetic values, a fake Upstash client seeded OVER cap on every lane installed on `cache_service.redis_client`, a `to_thread` spy and a background-task spy: `guarded_llm_create` issues exactly the base calls (one create with the caller kwargs plus `store=False`, one ledger record), zero Redis commands, zero thread hops, zero background tasks; both compare entries proceed to the provider fan-out; `/health` carries no `llm_spend` key; the FY25 nine digests and the W4-13 flag-OFF ledger are unchanged; `PROVIDER_CONFIGS` is unchanged. Flag ON with headroom changes no response byte either (the FY25 node is re-run with the flag exported ON for that one runner call: fail-open in the test tier, digests identical).

-----------------------------------------------------------------------------------------------

## 3. Change list (the order GREEN applies it)

0. Preconditions: S81-03 merged to main; cut `feature/s81-s04-spend-breaker` from that main; re-measure every anchor of section 1 by symbol; byte copies (Python `shutil.copyfile`) of every file edited below, sha256 recorded in the GREEN notes.
1. NEW `app/services/llm_spend_breaker.py` (section 2.2-2.6; LF; pure ASCII; no model-id literal; no `._LEDGER`).
2. `app/services/api_budget_service.py`: the module-attribute import (after abs:17); the two insertions of 2.4 inside `guarded_llm_create`; the docstring of `guarded_llm_create` gains one paragraph "S81-04 (ENABLE_LLM_SPEND_BREAKER) ..." stating admit-before-the-breaker-admission and record-after-the-ledger. Nothing else in the file (no PROVIDER_CONFIGS change).
3. `app/services/structured_comparison_service.py`: the import; the two entry preflights of 2.5; a short comment at each naming S81-04 and the W1-3 precedent.
4. `app/main.py`: `llm_spend_health_snapshot` + the one spread line (2.7).
5. `tests/test_s75_fanout_identity.py`: `UNIT_ENV` gains `"ENABLE_LLM_SPEND_BREAKER"` with the comment `# S81-04: a developer .env must not move the digests` (deliberate change E2; rebase-union with S81-03's line).
6. `tests/test_s81_s03_llm_ledger_v2.py`: `K1_GUARDED_AST_SHA` re-recorded to the new `ast.dump` hash of the final `guarded_llm_create` (measured with the exact expression of the row on CPython 3.12.9, written split by concatenation), docstring "(re-recorded by S81-04 for the spend-breaker admit/record, R-S03-10)" (deliberate change E1).
7. NEW `tests/test_s81_s04_spend_breaker.py` (the RED file, written by the RED agent; GREEN never edits a RED assertion).
8. `CLAUDE.md`: the flag row of section 8 inserted after the D03 row (CLAUDE.md:482-483 at base; after the S81-03 row once rebased), keeping every sibling row.
9. Gates (section 7); restore nothing (the byte copies are only for the mutation table).

No other file. (Not edited: `requirements*.txt` / `.in` (no dependency), `tests/conftest.py` (the unit file resets the leaf in its own teardown), `tests/_env_safety.py` (no credential), `app/api/*` (the route mapping and refunds already carry `LLM_UNAVAILABLE`), `processors.json` (no new host), migrations.)

-----------------------------------------------------------------------------------------------

## 4. Existing pins

### 4.1 Pins that change deliberately

| # | Pin | Change | Reason |
|---|---|---|---|
| E1 | `tests/test_s81_s03_llm_ledger_v2.py::test_k1_guarded_llm_create_untouched` (K1 literal :169, docstring :2418-2419 on `0197ec1a`) | literal re-recorded; docstring names S81-04 | R-S03-10: K1 is the deliberate cross-unit pin of guarded_llm_create; this unit adds the admit/record statements. The new hash is measured from the GREEN bytes and pasted split; the row must be green at head and red on any further edit of the function. |
| E2 | `tests/test_s75_fanout_identity.py` `UNIT_ENV` (:60-64) | `"ENABLE_LLM_SPEND_BREAKER"` appended | the R-S03-10 "trivial rebase for every later dark unit"; a developer `.env` carrying the flag must not move the FY25 digests (it would not today in the test tier because `redis_client` is None, but the clear-list is the house rule). |

### 4.2 Pins that must stay green and UNEDITED

`tests/test_u3c_store_false_pin.py` (T01 / T01b / T01c / T02 / T03 / T05-T09 / T18 / T19 / T22: the 2.4 code reads kwargs only through `.get`, writes no kwargs, keeps two dispatches), `tests/test_model_config_enforced.py` (>= 15 sites), `tests/test_model_config.py` (no model literal in app/), `tests/test_openai_breaker.py` (every W1-3 row, both flag states of `ENABLE_LLM_PREFLIGHT_BREAKER`, spend flag OFF), `tests/test_retro_w1_3.py`, `tests/test_m13_31_half_open_probe.py`, `tests/test_api_budget_service.py`, `tests/test_cost_meter_s74.py`, `tests/test_image_identify_llm_unavailable_s69.py`, `tests/test_health_loop_lag.py` (purity), `tests/test_retro_w1_7_w1_10.py`, `tests/test_health_brand_s69.py`, `tests/test_s77_redis_offloop.py` (`_BASE_HEALTH_KEYS`), `tests/test_s75_fanout_starve.py` (adapter_executor / brightdata_auth health), the FY25 node (both flag states), `tests/test_w4_13_flag_off_ledger.py`, `tests/test_prompt_fence.py` and the W4-11 digest fixture (no prompt moves), `tests/test_s71_u13_compare_auth_required.py` + its T23 fixture (no route parameter), `tests/test_s81_s03_llm_ledger_v2.py` every row except K1 (A1 `_LEDGER` scan included), `tests/test_s81_d03_deny_and_guards.py`.

-----------------------------------------------------------------------------------------------

## 5. RED tests: `tests/test_s81_s04_spend_breaker.py`

Hermetic (no network: the conftest guard; no real Redis: fakes on `cache_service.redis_client`; no sleep: `_utcnow` / `_monotonic` patched). Pure ASCII, LF. Helpers: `_leaf()` asserts `importlib.util.find_spec("app.services.llm_spend_breaker") is not None` then imports; `_pricing()` asserts `find_spec("app.services.llm_pricing") is not None`; `_need(name)` asserts the attribute exists (so every RED fails at base on an AssertionError, never ImportError / AttributeError). Fakes: `FakeUpstash` (class attribute `__module__ = "upstash_redis.client"`; `get(key)`; `eval(script, keys=None, args=None)` that emulates INCRBYFLOAT on an internal dict and returns the new value as a str; records `(op, key/script, keys, args, threading.get_ident())`), `FakeRedisPy` (`__module__ = "redis.client"`; `eval(script, numkeys, *keys_and_args)`), `RaisingRedis` (raises `ConnectionError(sentinel)` with a sentinel string built at run time). Every fake also implements `set`, `setex`, `incr`, `incrby`, `expire`, `delete` (recorded, unknown keys miss) because it is installed on `cache_service.redis_client`, the production read path of `_client()`, so other cache traffic of a compare reaches it; command-count assertions count only commands on a key starting with `llm_spend:` (an eval by its KEYS[1]) unless a row says otherwise. `FULL_CONFIG`: the four knobs `"3.25"`, `"1.5"`, `"0.75"`, `"2.5"` (for PIN rows) and a FakeUpstash seeded `"99.0"` on every lane key of today. The W1-3 harness (`_FanOutCounters`, `_mock_openai_client`, `_arm_prod_search_config`, `_run_compare`, `_run_stream`; test_openai_breaker.py:181-330) is COPIED into the file, not imported. Autouse fixture: `monkeypatch.delenv` the flag and the four knobs; teardown `_leaf()._reset_spend_breaker_state()` when the module exists (so no later file sees the /health key). Epoch expectations are computed with `datetime(...).timestamp()` in the test (no 8-digit literal). Synthetic model ids (`"gpt-" + "unpriced-test"`) are built at run time.

| # | Test | Assertion | At base | Satisfied by |
|---|---|---|---|---|
| R01 | `test_r01_leaf_exists_and_import_rule` | leaf exists; top-level imports only stdlib + `app.services.cache_service` + `app.services.llm_pricing` + `app.utils.async_utils` (as `from app.services import X` / `from app.utils import async_utils`); `api_budget_service` imported only inside a function; no `ast.Attribute` named `_LEDGER`; no string constant matching `^(gpt-|claude-|o[0-9])` | RED (find_spec None) | 2.2 |
| R02 | `test_r02_flag_reader_idiom[...]` (13) | `spend_breaker_enabled()` False for unset, `""`, `"false"`, `"0"`, `"no"`, `"off"`, `"garbage"`, `" FALSE "`; True for `"true"`, `"1"`, `"yes"`, `"on"`, `" TRUE "`; re-read after a flip in the same test | RED | 2.1 |
| R03 | `test_r03_lanes_and_defaults` | `LANES == ("live","escalation","search","offclock") == llm_pricing.SPEND_LANES`; `DEFAULT_CAPS_USD == {...}`; `CAP_ENV` names exact | RED | 2.2 |
| R04 | `test_r04_cap_knob_parse[lane-value]` (4 x 11) | per lane: unset, `""`, `"  "`, `"abc"`, `"inf"`, `"-inf"`, `"nan"`, `"0"`, `"-1"` -> the default; `"4.5"` -> 4.5; `" 7 "` -> 7.0; per call | RED | 2.1 |
| R05 | `test_r05_riyadh_day[instant]` (4) | 2026-10-22T20:59:59Z -> ("2026-10-22", epoch 2026-10-22T22:00:00Z); 2026-10-22T21:00:00Z -> ("2026-10-23", epoch 2026-10-23T22:00:00Z); 2026-12-31T21:30:00Z -> ("2027-01-01", epoch 2027-01-01T22:00:00Z); 2026-10-23T03:34:00Z -> ("2026-10-23", epoch 2026-10-23T22:00:00Z); `spend_key("live","2026-10-23") == "llm_spend:live:2026-10-23"` | RED | 2.2 |
| R06 | `test_r06_unknown_lane_is_a_value_error` | `admit("llm", 0.1)`, `record("llm", 0.1)`, `cap_usd("x")`, `spend_key("x", d)` raise ValueError; the fake saw zero commands | RED | 2.2 |
| R07 | `test_r07_prompt_token_upper_bound[case]` (6) | one user message `"x"*4000` -> 4020; Arabic text of 10 letters built from `chr(0x0627)` etc. -> 16 + 4 + 20; list content text 100 + one image part whose URL is `"data:image/jpeg;base64," + "A"*1_000_000` -> 50120 (independent of the URL length: the same with 10 chars); None messages -> 16; a message with content None -> 20; an unknown part `{"type":"x","v":1}` -> 16 + 4 + len(json.dumps(part)) | RED | 2.2 |
| R08 | `test_r08_output_token_bound[case]` (6) | (800, None) -> 800; (None, 1200) -> 1200; (None, None) -> 16384; (True, None) -> 16384; (0, None) -> 16384; ("800", None) -> 16384 | RED | 2.2 |
| R09 | `test_r09_upper_bound_literals[case]` (5) | needs `_pricing()`: openai mini 4020/800 -> approx 0.001083; gpt-4o 4020/800 -> approx 0.01805; anthropic haiku 1000/500 with 2 searches -> approx 0.02035; openai with 1 search -> None; synthetic unpriced id -> None | RED | 2.2 + S81-03 |
| R10 | `test_r10_admit_headroom_one_get[lane]` (4) | stored `"0.10"`, cap default, ub 0.1 -> returns None; commands == one `get` of `llm_spend:<lane>:<today>`; no eval | RED | 2.2 |
| R11 | `test_r11_admit_refuses_with_the_existing_class` | stored `"2.80"`, ub 0.30 -> `pytest.raises(api_budget_service.LLMUnavailableError)` with `type(exc) is LLMUnavailableError`; `str(exc).lower()` contains none of "429", "rate", "quota"; exactly one WARNING whose message == `[SPEND] lane=live cap reached (spent_cents=280 cap_cents=300 bound_cents=30) -- dispatch refused` (ints only); exactly one command (get) | RED | 2.2 |
| R12 | `test_r12_strict_boundary` | stored `"2.50"`, ub 0.50 -> admitted; stored `"2.51"`, ub 0.50 -> refused | RED | 2.2 |
| R13 | `test_r13_missing_key_is_zero` | no stored value: ub 2.99 admitted; ub 3.01 refused | RED | 2.2 |
| R14 | `test_r14_record_one_lua_eval[lane]` (4) | `record(lane, 0.00027)` -> exactly one `eval`; script == `RECORD_SCRIPT` and contains `INCRBYFLOAT` and `EXPIREAT`; keys == [today's key]; args == ["0.0002700000", str(expireat)]; the fake is configured to return `"1.25"` and that value (1.25) becomes the observation (`spend_snapshot()` lane `spent_usd`) | RED | 2.2, 2.6 |
| R15 | `test_r15_record_ignores_non_positive[value]` (6) | 0, -1, None, nan, inf, "x" -> zero commands | RED | 2.2 |
| R16 | `test_r16_redis_py_eval_shape` | FakeRedisPy receives `eval(RECORD_SCRIPT, 1, key, "0.5000000000", str(expireat))` positionally | RED | 2.6 |
| R17 | `test_r17_fail_open_and_rate_limited_warning` | `_client()` None: admit returns None, record no command, `entry_refuses_async` False; RaisingRedis: admit admitted, record returns None; three failures at `_monotonic` = 0, 59 and 60 s log exactly two `[SPEND] breaker fail-open (ConnectionError) -- admitting and not recording` WARNINGs (the first and the third); the run-time sentinel of the exception text appears nowhere in caplog | RED | 2.2, 2.3 |
| R18 | `test_r18_bad_stored_value_fails_open[value]` (4) | stored `"abc"`, `"nan"`, `"inf"`, `"-1"` -> admitted; one fail-open WARNING naming `ValueError` | RED | 2.2 |
| R19 | `test_r19_unpriced_bound` | `admit("live", None)`: stored `"2.99"` admitted with one WARNING `[SPEND] lane=live upper bound unpriced -- admitting on the spent total`; stored `"3.01"` refused (`LLMUnavailableError`); a second unpriced admit within 60 s (`_monotonic` patched) logs no second unpriced WARNING; `admit_openai_dispatch` with a synthetic unpriced id passes ub None to `admit_async` | RED | 2.2, 2.3 |
| R20 | `test_r20_cap_read_per_call` | stored `"2.0"`, ub 0.1: `LLM_SPEND_CAP_LIVE_USD="1.0"` refused, then `"5.0"` admitted | RED | 2.1 |
| R21 | `test_r21_day_roll_moves_the_key` | `_utcnow` at 20:59:59Z -> GET key day 2026-10-22; at 21:00:00Z -> 2026-10-23 | RED | 2.2 |
| R22 | `test_r22_redis_runs_off_the_loop_and_record_is_durable` | inside a running loop: `await admit_async("live", 0.1)` -> the fake's `get` thread ident != the loop thread ident; `task = record_soon("live", 0.2)` -> a Task present in `async_utils._BACKGROUND_TASKS` before it completes; after `await task` the `eval` thread ident != the loop thread ident; `record_soon("live", 0)` -> None | RED | 2.2 |
| R23 | `test_r23_entry_refuses_boundary` | inside a running loop: stored `"3.00"` -> True and exactly one WARNING whose message == `[SPEND] lane=live cap reached (spent_cents=300 cap_cents=300) -- short-circuiting the compare BEFORE the provider fan-out` (no query text); stored `"2.99"` -> False; one GET each, no eval; the GET ran on a thread other than the loop thread | RED | 2.2 |
| R24 | `test_r24_chokepoint_admit_dispatch_record_order` | flag ON, W1-3 OFF, stored `"0.5"`, fake client with usage 1000/200 on gpt-4o-mini: after awaiting the tasks the call left in `async_utils._BACKGROUND_TASKS`, a shared event list reads [get, create, eval]; create called once, sent kwargs equal the caller's plus `store=False`; the return value is the client's response object; the eval args[0] == "0.0002700000"; the openai_pricing ledger (bound with `start_openai_ledger()`) holds one entry | RED | 2.4 |
| R25 | `test_r25_chokepoint_refusal_precedes_the_breaker[w13]` (2: W1-3 OFF / ON with a half-open seed) | flag ON, stored `"2.99"`, gpt-4o + one message `"x"*4000` + max_tokens 800 (ub approx 0.01805): raises `LLMUnavailableError`; create await_count 0; no eval; with W1-3 ON: a spy on `api_budget_service._openai_dispatch_admission` records zero calls and the half-open probe key was never INCR'd | RED | 2.4 |
| R26 | `test_r26_both_flags_on_records_on_the_breaker_tail` | spend ON + W1-3 ON (closed breaker with a standing failure so `outcome_matters`): create once; `openai_record_success` called once; one spend eval after create | RED | 2.4 |
| R27 | `test_r27_raising_or_cancelled_create_records_nothing[exc]` (2) | flag ON, create raises a 429-class error / CancelledError: the same exception object propagates; zero eval; the W1-3 failure accounting identical to the spend-OFF run (W1-3 ON) | RED | 2.4 |
| R28 | `test_r28_chokepoint_bound_from_kwargs[case]` (3) | spy on `admit_async` captures (lane, ub): mini + "x"*4000 + max_tokens 800 -> ("live", approx 0.001083); mini + text 100 + a 1 MB data-URL image + max_tokens 500 -> approx 0.007818 and < 0.01; mini + "x"*4000 + max_completion_tokens 1200 -> approx 0.001323 | RED | 2.2, 2.4 |
| R29 | `test_r29_unpriced_model_records_the_legacy_estimate` | flag ON, synthetic unpriced id, stored `"2.9"`: admitted; eval args[0] == "0.0002700000" (usage 1000/200, the S81-03 `openai_usage_cost_usd` fallback) | RED | 2.2 |
| R30 | `test_r30_response_without_usage_records_nothing` | flag ON, response object without `usage` (stream shape): create once, zero eval | RED | 2.2 |
| R31 | `test_r31_rest_entry_short_circuits_before_fanout` | flag ON, stored `"3.00"` on live: `_run_compare()` -> fields `success` False, `code` "LLM_UNAVAILABLE", `error` == `LLM_UNAVAILABLE_FRIENDLY_MESSAGE`; `_FanOutCounters.calls` == all zero; create count 0; exactly one GET, zero eval | RED | 2.5 |
| R32 | `test_r32_stream_entry_short_circuits_before_fanout` | same through `_run_stream()`: the first event is `("error", {...code "LLM_UNAVAILABLE"...})`, no further event; fan-out zero | RED | 2.5 |
| R33 | `test_r33_health_object_after_admit` | flag ON, stored `"1.25"`, one admit on live: TestClient `/health` -> `body["llm_spend"] == {"live": {"spent_usd": 1.25, "cap_usd": 3.0, "day": today}}`; `set(body) - {"llm_spend"}` <= the S77 base set; status/message unchanged; the fake saw zero commands during the /health request | RED | 2.2, 2.7 |
| R34 | `test_r34_health_object_after_record_and_cap_per_call` | `LLM_SPEND_CAP_OFFCLOCK_USD="4"`, `record("offclock", 0.5)` with the fake returning `"2.5"` -> `{"offclock": {"spent_usd": 2.5, "cap_usd": 4.0, "day": today}}`; then the knob `"6"` -> cap_usd 6.0 on the next /health | RED | 2.7 |
| R35 | `test_r35_health_survives_a_raising_snapshot` | `spend_snapshot` monkeypatched to raise: /health 200, no `llm_spend` key | RED (needs the helper) | 2.7 |
| R36 | `test_r36_health_wiring_static` | `app.main.llm_spend_health_snapshot` exists; `inspect.getsource(app.main.health_check)` contains `llm_spend_health_snapshot()` | RED | 2.7 |
| R37 | `test_r37_chokepoint_wiring_static` | in abs: an `ImportFrom` `app.services` naming `llm_spend_breaker` as `_llm_spend_breaker`; inside `guarded_llm_create` exactly one call `_llm_spend_breaker.spend_breaker_enabled()`, one `_llm_spend_breaker.admit_openai_dispatch(...)` whose four args are `kwargs.get(...)` calls of "model", "messages", "max_tokens", "max_completion_tokens", two `_llm_spend_breaker.record_openai_response_soon(...)`; the admit statement index < the index of the statement containing `_openai_dispatch_admission()`; in scs: two `entry_refuses_async` calls, each in a BoolOp `and` whose first operand is `_llm_spend_breaker.spend_breaker_enabled()` | RED | 2.4, 2.5 |
| R38 | `test_r38_claude_md_row` | CLAUDE.md contains `ENABLE_LLM_SPEND_BREAKER`, the four `LLM_SPEND_CAP_*_USD` names, `llm_spend:<lane>:` and the words `fail-open` and `/health` within the row | RED | 8 |
| P01 | `test_p01_flag_off_chokepoint_identity[value]` (8: unset, "false", "0", "off", "", " FALSE ", "no", "garbage") | FULL_CONFIG; W1-3 OFF; `to_thread` and `fire_and_forget` spies; create called once with caller kwargs + `store=False` (dict equality); the return is the response object; FakeUpstash zero commands; zero `to_thread` / background tasks; one openai_pricing ledger entry equal field-by-field to a recorded base literal | PIN (green) | base behaviour |
| P02 | `test_p02_flag_off_with_w13_on_touches_no_spend_key` | FULL_CONFIG; W1-3 ON (closed, no streak): create once; no FakeUpstash command whose key starts with `llm_spend:` | PIN | base |
| P03 | `test_p03_flag_off_rest_entry_ignores_an_exhausted_lane` | FULL_CONFIG (every lane seeded `"99.0"`): `_run_compare()` reaches the fan-out (`calls["search_web"] > 0`) and `result.get("code") != "LLM_UNAVAILABLE"`; zero `llm_spend:` commands | PIN | base |
| P04 | `test_p04_flag_off_stream_entry_ignores_an_exhausted_lane` | same through `_run_stream()`: the first event is not an `LLM_UNAVAILABLE` error; fan-out > 0 | PIN | base |
| P05 | `test_p05_flag_off_health_has_no_spend_key` | FULL_CONFIG; after a P01-style call: `/health` has no `llm_spend`; `set(body)` <= the S77 base set; status/message exact | PIN | base |
| P06 | `test_p06_provider_configs_unchanged` | `set(PROVIDER_CONFIGS) == {"firecrawl","scrapedo","brightdata","serper","openai","youtube"}`; no key contains "llm"; `get_usage_summary()` keys unchanged (redis None) | PIN | R-S03-9 |
| P07 | `test_p07_no_new_credential_names` | no name in `CREDENTIALS_UNSET` / `CREDENTIAL_PLACEHOLDERS` starts with `LLM_SPEND` or equals `ENABLE_LLM_SPEND_BREAKER` | PIN | base |

Counts: 38 RED rows (about 136 nodes with the parametrizations) and 7 PIN rows (14 nodes). Every RED fails at base on an AssertionError (find_spec / `_need` probes, static AST asserts, the field asserts of R31/R32 against a compare that proceeds at base, R36/R37/R38 source asserts). The rows needing S81-03 (R03, R09, R24, R28, R29) also assert `_pricing()` first.

-----------------------------------------------------------------------------------------------

## 6. Mutation table (GREEN bytes; byte copy -> exact-string edit matching once -> killing rows via `pyt.py -k` bound 600 -> restore -> sha256 compare; `.qa-mutation.lock`)

| # | Mutant | Killing row(s) |
|---|---|---|
| M01 | chokepoint: drop `if _llm_spend_breaker.spend_breaker_enabled():` (always admit) | P01 |
| M02 | REST entry: drop the flag operand of the `and` | P03 |
| M03 | stream entry: drop the flag operand | P04 |
| M04 | `admit`: `spent + ub > cap` -> `>=` | R12 |
| M05 | `entry_refuses_async`: `spent >= cap` -> `>` | R23 |
| M06 | move the spend admit after `_openai_dispatch_admission()` on the W1-3-ON branch | R25[w13-on], R37 |
| M07 | `record_soon` -> a direct `record(...)` call on the loop thread | R22, R24 |
| M08 | image part counted as `len(json.dumps(part))` | R07, R28 |
| M09 | `EXPIREAT` line removed from `RECORD_SCRIPT` | R14 |
| M10 | cap parse without the `math.isfinite` check | R04 |
| M11 | fail-open warn limiter removed (warn every time) | R17 |
| M12 | `RIYADH_UTC_OFFSET_HOURS = 0` | R05, R21 |
| M13 | refusal raises `RuntimeError` instead of `LLMUnavailableError` | R11 |
| M14 | `REFUSAL_MESSAGE` "llm spend rate cap reached ..." | R11 |
| M15 | chokepoint records on the raising path (record before create) | R27, R24 |
| M16 | `spend_snapshot` returns `{"llm_spend": {}}` when nothing was observed | P05 |
| M17 | `spend_snapshot` re-reads Redis (calls `admit`'s GET) | R33 |
| M18 | `output_token_bound` returns 0 | R08, R28 |
| M19 | flag reader without `.strip().lower()` | R02 |
| M20 | `admit` reads the live key for every lane | R10 |
| M21 | record args with `repr(actual)` | R14 |
| M22 | record only on the W1-3-OFF tail | R26 |
| M23 | unpriced ub treated as a refusal | R19 |
| M24 | `PROVIDER_CONFIGS["llm"] = {...}` added | P06 |
| M25 | /health spread unconditional (`{"llm_spend": {}}` from main) | P05 |
| M26 | `_eval` always uses the upstash keyword shape | R16 |
| M27 | `entry_refuses_async` run inline (no `to_thread`) | R23 (the GET thread ident is asserted) |

Equivalent survivors are reported for a ruling, never silently dropped.

-----------------------------------------------------------------------------------------------

## 7. Comm set and gates for GREEN (cheapest first; every pytest through `pyt.py`, one at a time)

1. `py_compile` + `ruff check --select E9,F63,F7,F82 --no-cache` on `llm_spend_breaker.py`, abs, scs, main, the two edited tests and the new test; bytes > 127 count == 0 in the two new files and in the CLAUDE.md row; `git diff --stat` shows no whole-file diff (CRLF preserved).
2. Unit file at base (the merged main before GREEN; RED all AssertionError, PIN green) and at head (all green), bound 600, both with the flag unset in the environment.
3. Mutation run (section 6), bound 600 per mutant.
4. The 4.2 pin files in one CI-order call (sorted, bound 1200), at head.
5. `tests/test_s81_s03_llm_ledger_v2.py` at head (K1 green with the new literal; every other row green), bound 600.
6. Identity: the FY25 node and `tests/test_w4_13_flag_off_ledger.py` at head with the flag unset, then the FY25 node again with `ENABLE_LLM_SPEND_BREAKER=true` exported for that one runner call (digests identical: fail-open in the test tier).
7. Comm set: `comm_set.txt` in the notes folder = 314 files at base (module-reference grep for `structured_comparison_service|api_budget_service|guarded_llm_create|LLMUnavailableError|_llm_breaker|app\.main|from app import main|/health|health_check|llm_spend|llm_pricing`: 278; UNION the source-scanning tests (`rglob(`, `APP_DIR`, `app/services` paths): 68; UNION the named pins test_model_config, test_model_config_enforced, test_prompt_fence, test_u3c_store_false_pin, test_start_command, test_migration_index_predicate_immutability, test_openai_key_log_hygiene_s69, test_sentry_channels_u8d_unit, test_ci_gates, test_behavior_dimension_translation (the CLAUDE.md readers), test_w4_13_flag_off_ledger, test_s75_fanout_identity; MINUS the four test_precommit_hook files) UNION `tests/test_s81_s03_llm_ledger_v2.py` and the new unit file at head. The unit edits no test-support module and no SmartCompareApp file (no client-visible key), so no further union. Re-run the builder (`build_comm.py <worktree> <out>`) on the merged main before the run. Chunks of at most 25 files (13 chunks), bound 1200 each, base and head; `comm -13` of the sorted FAILED node-id sets must be EMPTY; a branch-only-new failure is re-run against base to tell a network flake from a regression; the two known tiktoken ERROR nodes of `test_prompt_truth.py` are recorded identically on both sides.
8. The pre-commit hook files are NOT run (the unit does not edit `.githooks`).

-----------------------------------------------------------------------------------------------

## 8. CLAUDE.md flag row (inserted after the D03 row, CLAUDE.md:482-483 at base; union with the S81-03 / B4 / ST1 rows at rebase) and owner steps

**SESSION 81 flag (S81-04 SPEND-BREAKER, 2026-10-23; default OFF, read PER CALL; a new name, so unset in production by construction (Railway not read); PLAN_S81 M1 S81-04, spec `.qa-s80/S81-04_UNIT_SPEC.md` of the unit worktree):**
- `ENABLE_LLM_SPEND_BREAKER` (S81-04, `app/services/llm_spend_breaker.py::spend_breaker_enabled`) + knobs `LLM_SPEND_CAP_LIVE_USD` / `LLM_SPEND_CAP_ESCALATION_USD` / `LLM_SPEND_CAP_SEARCH_USD` / `LLM_SPEND_CAP_OFFCLOCK_USD` (defaults 3.00 / 1.00 / 0.50 / 2.00 USD per Asia/Riyadh day, read per call; unset / blank / garbage / inf / nan / <= 0 -> the default; not secrets). **Effect ON:** every OpenAI chat completion through `guarded_llm_create` is ADMITTED on the `live` lane before dispatch from an UPPER BOUND priced by the S81-03 `llm_pricing.price_call` (prompt bytes as tokens + 4 per message + 16 per call, 50,000 tokens per image part whatever its data-URL size, `max_tokens` / `max_completion_tokens` or 16,384, $0.01 per search) with ONE Upstash GET of `llm_spend:<lane>:<YYYY-MM-DD>` (Riyadh day, UTC+3 fixed); `spent + bound > cap` raises the existing `LLMUnavailableError` before the W1-3 breaker admission (no half-open probe is held); a served response is RECORDED non-awaited with ONE atomic Lua EVAL (INCRBYFLOAT of the list price + EXPIREAT next Riyadh midnight + 1 h; the base mini-rate estimate for an unpriced model id); both compare entries return the existing `LLM_UNAVAILABLE` envelope (REST coded 503 + refund, SSE `error` + refund) BEFORE any paid provider when the live lane is already at or over its cap; every Redis command runs on a worker thread, never on the loop. `/health` gains `llm_spend` {lane: {spent_usd, cap_usd, day}} only once a lane was observed in this process (no key, no null otherwise; a pure dict read). Not a PROVIDER_CONFIGS provider (R-S03-9). Every later Anthropic call (S81-06), web_search call (S81-21, lane `search`), Sonnet escalation (lane `escalation`) and batch / cron submitter (S81-16 / S81-22, lane `offclock`, admitted once per batch with its whole bound) calls `admit` / `record` (section 2.8 of the spec). **Flag OFF:** byte-identical (no admit, no record, no Lua, no thread hop, no health key; pinned by `tests/test_s81_s04_spend_breaker.py` P01-P07 under the full configuration, the FY25 nine-digest node and the W4-13 ledger). **Stated limits:** (1) FAIL-OPEN: Redis unconfigured, a GET / EVAL error or a bad stored value admits and does not record (one `[SPEND] breaker fail-open` WARNING per process per minute); during an Upstash outage there is NO code-side bound and the Console workspace limit is the outer bound; (2) the bound over-estimates (bytes as tokens, max output, a fixed image bound), so a lane refuses a call a little BEFORE the true spend reaches the cap; (3) admit reads, it does not reserve: concurrent in-flight calls can overshoot a cap by their own bounds, and the record lands after the response (non-awaited), so a lane can end a day slightly above its cap; (4) a call that raises, is cancelled or streams without usage records nothing (a provider may still bill a timed-out request); (5) a compare that starts under the cap and crosses it mid-way has its later calls refused at the chokepoint and degrades as on any LLM failure (a parse failure, a deterministic verdict), not as `LLM_UNAVAILABLE`; URL mode and the camera have no entry preflight (their LLM refusals surface through today's URL extraction failure and the camera's coded 503); (6) an over-cap lane refuses every call of that lane until the Riyadh day rolls (00:00 Asia/Riyadh); the only override is the owner raising the cap name on web (read per call); (7) OpenAI calls count on `live` at the S81-03 list price, not the data-sharing-discounted bill; a batch result landing on a later Riyadh day records on that day's key; (8) each Redis command adds one Upstash round trip (163-203 ms measured with TLS) of WALL time to an admitted call (the admit is awaited on a thread; the record is not); (9) the Riyadh day helper is module-local (S81-09 may move it). **Activation precondition:** with OpenAI still serving, check the daily compare volume x about $0.021 (list price per compare, runs/critic.json) against `LLM_SPEND_CAP_LIVE_USD`; set the cap name on web first if the default would refuse real traffic. **Canary (the owner's explicit yes, one window):** `/health llm_spend.live.spent_usd` moving with traffic and `day` rolling at 00:00 Riyadh, the `[SPEND] ... dispatch refused` / `short-circuiting the compare` counts by lane, the `LLM_UNAVAILABLE` 503 count, the `[SPEND] breaker fail-open` count, `/health loop_lag_max_60s_ms` unchanged, client wall time per compare. **Rollback:** unset the variable (per call, immediate); the keys expire by themselves.

Owner steps (names only): (a) nothing to set for the defaults; set any of the four `LLM_SPEND_CAP_*_USD` names on web (and on `price-warmer` if its LLM calls should count) only if a default is wrong; (b) keep the Console workspace limit (decision 8: the $400 balance) as the outer bound; (c) flip `ENABLE_LLM_SPEND_BREAKER` after approval in the plan's flip order ("ledger, breaker, request context ON"), BEFORE any Anthropic flag (R-S03-9 names this unit a precondition for `ENABLE_ANTHROPIC_VERDICT`).

-----------------------------------------------------------------------------------------------

## 9. Stated limits

L1 fail-open on any Redis problem (no bound during an outage; the Console limit is the outer bound). L2 the upper bound over-estimates: bytes as tokens (about 4x for English text), max output, the 50,000-token image bound (an assumption from OpenAI's published tiling rule for the mini model, re-verified by S81-07). L3 admit-read, not reserve: concurrency overshoot bounded by the in-flight calls' bounds; the non-awaited record adds a small lag. L4 raising / cancelled / usage-less calls record nothing. L5 mid-compare crossing degrades rather than refusing; URL mode and the camera have no entry preflight (camera vision refusals are already the coded 503; URL extraction refusals become today's extraction-failure surface). L6 an over-cap lane stays closed until 00:00 Riyadh; the cap name is the only override. L7 OpenAI counts at list price on `live`; an unpriced model id records the base mini-rate estimate (S81-03 `openai_usage_cost_usd`), which under-counts an expensive unpriced id; a batch result on a later Riyadh day lands on that day's key. L8 one Upstash round trip of wall time per admitted call (thread-offloaded; about 4-5 sequential stages per compare, so about +0.7-1.0 s client wall per compare ON; the canary measures it; a per-process read memo is open question Q1). L9 the day helper is module-local. L10 `/health` shows the last value THIS process read or wrote (another replica's or the warmer's spend appears only after this process reads the key), and a process that only ever failed open shows no key (Q4). L11 the lane is chosen by the call site (every `guarded_llm_create` call is `live`, whichever Railway service runs it). L12 the first Lua script in the repo: Upstash's EVAL support is the documented REST command set; its acceptance with INCRBYFLOAT + EXPIREAT is measured only at the canary (no live call offline).

## 10. Out of scope

The Anthropic adapter and its wiring (S81-06; this spec only states the contract); the Batch submitter (S81-16 / S81-22); web_search (S81-21); the Sonnet escalation flag; a reservation (reserve-then-settle) admit; an entry preflight on `/url/compare` and `/image/identify`; a spend memo; an admin view of the lanes (S81-03's admin `llm` block may read the keys later); moving the day helper (S81-09); the monthly ceiling (decision 8: later, from the ledger); any client change; any migration.

## 11. Open questions for the orchestrator

- Q1 Admit latency vs the brief's "one atomic Upstash operation each": the spec follows the brief (one GET per admit, thread-offloaded, awaited; about +0.7-1.0 s wall per compare ON). Alternative: a per-process read memo (for example 5 s) plus the locally recorded deltas, which removes almost all admit round trips at the cost of a few seconds of cross-process staleness. Ruling wanted before RED.
- Q2 The compare-entry preflight (change 3 of section 3) is not in the brief's change list; it is what makes the refusal travel through the existing `LLM_UNAVAILABLE` envelope (1.4: a chokepoint refusal deep in a compare is swallowed by its caller). Confirm it, and whether `/url/compare` (B4 V2 territory) and `/image/identify` should get the same entry check in this unit or a follow-up.
- Q3 Entry threshold: `spent >= cap` (the lane exhausted). A stricter `spent + per-compare reserve > cap` would avoid most mid-compare crossings (L5) but needs a fourth knob or a constant; ruling wanted.
- Q4 /health in a pure fail-open process shows nothing; an additive `llm_spend_fail_open` counter key (outside the lane object) would make an Upstash outage visible on /health. Add it or leave the WARNING as the only signal?
- Q5 Unpriced OpenAI ids record the legacy mini-rate estimate (S81-03's `openai_usage_cost_usd`); recording the admitted upper bound instead would be conservative for an unpriced expensive id. Which?
- Q6 The 50,000-token image bound is an assumption (no web read in this run); S81-07's pricing read could pin it, or the vision sites could pass an explicit bound.
- Q7 Reading of the brief's "both through ONE atomic Upstash Lua (INCRBYFLOAT + EXPIREAT) per call": the spec makes `record` the Lua EVAL and `admit` a single GET (one atomic command; a read needs no script and no write). If the intent was an admit that RESERVES the bound inside a Lua (INCRBYFLOAT of the bound when it fits, then a settling INCRBYFLOAT of actual minus bound, plus a release on a raising or cancelled call), that closes L3 at the cost of a second write per call and a release path on every exception arm of `guarded_llm_create` (where U3c T01b forbids nothing but the W1-3 arms are already dense); ruling wanted before RED.
- Q8 The brief cites the fail-open precedent at abs ":247-249 / :390-392" and the text_routes refund at ":687 / :713"; at this base they are abs:268-270 (serper gate), abs:398-399 and :414-416 (has_budget), and text_routes:675-678 (POST) / :883-886 (GET) / :1308-1323 (stream). The spec cites the measured lines.

Not done in this spec: no code, no test file, no CLAUDE.md edit; no comm-set run at base (GREEN runs base and head); no live Upstash measurement; the S81-03 test file was read from `0197ec1a`, not run.
