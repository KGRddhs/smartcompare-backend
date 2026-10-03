# OAI_OBS: OpenAI companions and observability (session 70 backend unit spec)

- **Base SHA:** `94c097cda4e3d63562c5e40e444f4965c4a0222d` (= main, the session-69 close merge #276)
- **Branch / worktree:** `feature/s70-openai-companions` in `C:/Users/SynAckITPC/Documents/AI/sc-s70-oai`
- **Backend:** `app/` only (the deployed backend). Never edit `backend/app/`.
- **Flags:** none. All four items ship UNFLAGGED: two logging changes, a retry ceiling, and one additive metadata key. No item changes a return value, a timing bound, a cancellation or a user-visible response beyond the additive key `metadata.model_downgraded` (see "Stop conditions").
- **Context:** production OpenAI credits are exhausted until Ahmed tops up. Railway `web` has carried `OPENAI_MAX_RETRIES=1` and `OPENAI_FALLBACK_MAX_RETRIES=0` since 2026-09-30. Decision memo: `docs/investigations/2026-09-29-session-69-state/LLM_PROVIDER_DECISION.md` (claims A-C11 and R-C14; companion items (a) = #265 and (f) = #268).
- **Spec agent:** read-and-measure only. The only source edits were experiments in a detached scratch worktree at the base SHA. Each was restored from a byte copy and sha-verified (see the "Probe evidence" section).

## 0. Measured environment (pinned venv `C:/Users/SynAckITPC/Documents/AI/.venv-qaren`)

| Package | Version (venv, measured) | Pin (requirements*.txt) |
|---|---|---|
| CPython | 3.12.9 | runtime |
| openai | 3.3.1 | `openai==3.3.1` |
| httpx | 0.28.1 | `httpx==0.28.1` |
| httpcore | 1.0.9 | (transitive) |
| pytest | 9.1.1 | `pytest==9.1.1` |
| sentry_sdk | 2.68.1 | (requirements.txt) |

**What `str(e)` yields on the pinned versions.** Measured by constructing and raising each exception through the real code paths; the script is `scratchpad/oai/measure_str.py` and its output is `measure_str.out`:

| Exception | How produced | `str(e)` | `repr(e)` |
|---|---|---|---|
| `asyncio.TimeoutError` | `asyncio.wait_for` expiry, and `asyncio.timeout` expiry | `''` | `TimeoutError()`. It IS `builtins.TimeoutError` (`asyncio.TimeoutError is TimeoutError` → True) |
| `httpx.ReadTimeout` | an `AsyncClient` over `MockTransport` raising it, and the real mapping `httpx._transports.default.map_httpcore_exceptions` over `httpcore.ReadTimeout(str(TimeoutError()))` | `''` | `ReadTimeout('')` |
| `httpx.ConnectTimeout` | same mapping | `''` | `ConnectTimeout('')` |
| `openai.APITimeoutError(request=...)` | direct | `'Request timed out.'` | |
| `openai.APIConnectionError(request=...)` | direct | `'Connection error.'` | |
| `asyncio.CancelledError()` | direct | `''` | |
| `httpx.HTTPStatusError` (429 via `raise_for_status`) | real | multi-line: `Client error '429 Too Many Requests' for url 'https://google.serper.dev/search'\nFor more information check: https://developer.mozilla.org/...` | |

Why a real httpx socket timeout has an empty text, from reading the source: httpcore `_backends/anyio.py:27` maps `{TimeoutError: ReadTimeout}` and `_exceptions.py:14` does `raise to_exc(exc) from exc` with `exc = TimeoutError()`, whose text is empty. httpx `default.py:117-118` then does `message = str(exc); raise mapped_exc(message) from exc`, which gives `ReadTimeout('')`. Every Serper transport timeout therefore reaches `logger.error(f"...{e}")` as an empty tail, which is the empty-message Sentry issues PYTHON-FASTAPI-N and PYTHON-FASTAPI-14.

---

## 1. Item 1: issue #265, `url_extraction_service.get_client` ignores `OPENAI_MAX_RETRIES`

### Facts

- `app/services/url_extraction_service.py:26-37` builds the client with no `max_retries`:
  ```python
  _client = None
  def get_client() -> AsyncOpenAI:
      global _client
      if _client is None:
          _client = AsyncOpenAI(
              api_key=os.getenv("OPENAI_API_KEY"),
              base_url=provider_base_url(),
              timeout=httpx.Timeout(120.0, connect=30.0),
          )
      return _client
  ```
  It is used at `:411` (`client = get_client()`, the `/api/v1/url/*` page-extraction LLM call).
- Sibling `app/services/extraction_service.py:57-80` does a function-local `from app.services.model_config import openai_max_retries` and passes `max_retries=openai_max_retries()` at FIRST construction. The lazy `_client` is cached for the life of the process.
- Sibling `app/services/openai_service.py:34-37` (the module client, built at import) and `:48-79` (the per-project `_client_cache`, lazy) also pass `max_retries=openai_max_retries()`. Across `app/`, `url_extraction_service.py:32` is the ONLY `AsyncOpenAI(` construction without it. Grep for `AsyncOpenAI(\|OpenAI(` measured it.
- `model_config.openai_max_retries()` (`model_config.py:184-189`) is `_resolve_retries("OPENAI_MAX_RETRIES", 2)`. Blank or malformed values fall back to 2 and negatives clamp to 0 (`:172-181`).
- **Caching semantics match.** Both lazy clients read the env ONCE, at first construction, and cache it in a module global. A Railway env change reaches them on the next restart or redeploy. The same holds for the per-project clients. The module client reads it at import.
- **Measured at BASE** (probe, see the evidence section): with the env unset, `max_retries == 2`, because the SDK default equals the knob default. With `OPENAI_MAX_RETRIES=1`, `max_retries == 2`, so the defect is real. A constructor spy shows the kwargs are `{api_key, base_url, timeout}` with no `max_retries`.

### Requirements

- **R1.1** `url_extraction_service.get_client` passes `max_retries=openai_max_retries()` to `AsyncOpenAI(...)`. Import it with a function-local `from app.services.model_config import openai_max_retries` inside the `if _client is None:` branch, exactly as `extraction_service.get_client` does. The other kwargs (`api_key`, `base_url`, `timeout`) are byte-identical.
- **R1.2** The caching semantics are unchanged. The module `_client` is built once (lazily) and there is no per-call re-read, the same as `extraction_service._client`.
- **R1.3** Docs only. In `docs/runbooks/2026-09-02-openai-tpm-launch-sizing.md` §3, the `OPENAI_MAX_RETRIES` table row changes from "all four AsyncOpenAI constructions (...)" to "all five" and adds `url_extraction_service.get_client` (#265).

---

## 2. Item 2: issue #268, the silent `DAILY_4O_CAP` downgrade

### Facts

- `app/services/model_router_service.py:35-64`:
  ```python
  DAILY_4O_CAP: int = 1_000_000
  SWITCH_THRESHOLD: float = 0.80
  ...
  async def get_model(self, priority: str = "standard") -> str:
      if priority != "high":
          return standard_model()
      used = await self._get_4o_usage_today()
      if used / self.DAILY_4O_CAP >= self.SWITCH_THRESHOLD:
          return standard_model()          # <- silent: no log, no marker
      return verdict_model()
  ```
- **Redis down.** `_get_4o_usage_today` (`:86-93`) returns 0 when the read fails. In practice `cache_service._redis_get` (`cache_service.py:173-184`) already swallows every Redis error and returns `None`, and `None` becomes 0. The verdict therefore stays on the verdict model (fail-open) and cap protection is lost until Redis returns. `_increment_4o_usage` (`:95-110`) is also best-effort. This stays as is (see R2.3).
- **Where the verdict model is chosen.** In `app/services/extraction_service.py:2524-2525`, inside `generate_comparison`: `from app.services.model_router_service import model_router` then `verdict_model = await model_router.get_model(priority="high")`. The local name `verdict_model` is a STRING that shadows `model_config.verdict_model`. The primary call is at `:2639-2656`. The 429/rate/quota fallback at `:2657-2695` reassigns `verdict_model = _fallback_model` (`:2672`) only when `verdict_model != standard_model()`. Usage is recorded at `:2697-2700`. The success path builds the usage dict at `:2750-2755` and returns at `:2756`. The failure path at `:2758-2760` returns `({"winner_index": 0, "error": COMPARISON_GENERATION_ERROR}, {"prompt_tokens": 0, "completion_tokens": 0})`.
  - When the router downgraded (`verdict_model == standard_model()`), a 429 on that call does not fall back (`:2664` is false) and re-raises into the failure path. So "the verdict ran on the downgraded model" happens exactly when the success path is reached with `verdict_model == standard_model() != model_config.verdict_model()`.
- **Other `get_model(priority="high")` caller.** `structured_comparison_service.py:905` is the Tier-3 spec synthesis (`_synth_call`), not the verdict. It does NOT call `record_usage`. The only `record_usage` caller is `extraction_service.py:2700`.
- **`generate_comparison` callers.**
  - Sync orchestrator: `structured_comparison_service.py:4045` (`comparison, usage = await generate_comparison(...)`, then `self._track_gpt_cost(usage)` at `:4056`).
  - Streaming orchestrator: `:4813` (`_verdict_coro`, awaited at `:4824` under `ENABLE_FULL_STREAM_DEADLINE` through `asyncio.wait_for`, which runs it in a NEW task, or directly at `:4830`; `_track_gpt_cost` at `:4833`).
  - Self-critique regeneration: `:8949` (inside `_apply_self_critique._regenerate`, flag `ENABLE_SELF_CRITIQUE`, default OFF).
  - `/api/v1/url/compare`: `url_extraction_service.py:643` (`comparison, _usage = ...`; usage discarded).
- **Where response metadata is built.**
  - Sync (`_compare_from_text_impl`): `_metadata_override: Dict[str, Any] = {}` at `:4145`. It gets `source_trace` at `:4154` and `_verdict_critique` at `:4162`, then goes to `build_comparison_response(..., metadata=_metadata_override or None, ...)` at `:4163-4187`.
  - Streaming (`compare_from_text_streaming`): `_metadata_override` at `:4954`, with `source_trace` `:4963`, `_verdict_critique` `:4971`, `verdict_scrubbed` `:4974` (the W4-12 precedent for an absent-unless-true telemetry key), then `build_comparison_response(...)` at `:4976-4999`. The result is yielded as `("settle_complete", complete_response)` and `("complete", complete_response)` at `:5089-5090`.
  - `response_builder.build_comparison_response` merges the override onto the auto-built block at `response_builder.py:2117-2118` (`if metadata: result["metadata"].update(metadata)`).
  - The routes do not filter metadata. There is no `response_model` on `text_routes` compare, and grep shows only `total_cost` reads. The client has no strict schema: grep `SmartCompareApp/src` finds no `z.object` or `.strict()` over the response.
  - The partial path `_build_partial_response` (`:3460-3591`, metadata literal at `:3570-3576`) is a third build site. It is out of scope (see "Stated limits").
- **Why a contextvar would not work.** On the streaming path with `ENABLE_FULL_STREAM_DEADLINE` on, the verdict coroutine runs inside `asyncio.wait_for`, which is a new task with a COPIED context, so a contextvar set inside `generate_comparison` would never reach the orchestrator. The return value (the usage dict) is the only carrier that crosses both paths without a signature change. That is why R2.4 uses it.
- **Orchestrator lifetime.** It is per request: `get_comparison_service()` (`:9146-9148`) returns a new `StructuredComparisonService()`, and `image_routes.py:434` builds one per request and calls `compare_from_text`. The per-run state is initialised in `__init__` (`_partial_comparison` at `:3150`) and reset at the start of each run (sync `:3788-3792`, streaming `:4394-4398`).
- **Admin gauge.** `app/api/admin_routes.py:877` reads `openai_4o_cap = ModelRouterService.DAILY_4O_CAP` (the class constant) for `GET /api/v1/admin/costs/gauges`. `tests/test_admin_referral_endpoints.py::TestCostsGauges` pins `pct == 50.0` for a Redis value of 500000.
- **`float()` on candidate env values** (measured):

  | Input | Result |
  |---|---|
  | `'1000000'`, `'1_000_000'`, `' 2000000 '`, `'2e6'` | finite |
  | `'1e309'`, `'inf'`, `'-inf'`, `'Infinity'` | ±inf |
  | `'nan'`, `'NaN'` | nan |
  | `'0'`, `'-5'`, `'0.5'` | finite |
  | `'2000000.9'` | 2000000.9 |
  | `'abc'`, `''`, `'1,000,000'`, `'0x10'` | ValueError |

  The inf and nan cases show that `float()` accepts non-finite text.
- `tests/test_model_router.py:36-42` pins `hasattr(ModelRouterService, "DAILY_4O_CAP")`, `isinstance(..., int)` and `SWITCH_THRESHOLD == 0.80`. Keep the class constant.
- **Measured at BASE** (probes): at 800,000 used, `get_model("high")` returns `gpt-4o-mini` and emits ZERO log records. `DAILY_4O_CAP=2000000` with 1,000,000 used still returns `gpt-4o-mini`, because the env is ignored. `generate_comparison` with the router patched to mini returns `usage == {'prompt_tokens': 80, 'completion_tokens': 20}`, with no marker. The sync body and the SSE `complete` event (deadline off and on) carry no `metadata.model_downgraded`, although the verdict succeeded.

### Requirements

- **R2.1 Cap resolver.** Add a public method `ModelRouterService.daily_4o_cap(self) -> int`. It reads `os.environ.get("DAILY_4O_CAP")` on EVERY call and never caches.
  - Unset or blank after `.strip()`: return `self.DAILY_4O_CAP`. The class constant stays `1_000_000`, an `int`.
  - Otherwise `v = float(raw.strip())`. On `ValueError`, or when `not math.isfinite(v)`, or when `v < 1`, return `self.DAILY_4O_CAP`.
  - Otherwise return `int(v)`.
  - `< 1` (not `<= 0`) is deliberate: a positive value below one token, such as `0.5`, would truncate to 0 and divide by zero. It is treated as garbage.
  - Never raises. No secrets are involved.
- **R2.2 One INFO line per downgrade decision.** In `get_model`, for `priority == "high"`: `cap = self.daily_4o_cap()`, then `if used / cap >= self.SWITCH_THRESHOLD:` log exactly ONE record on the module logger (`app.services.model_router_service`) at INFO, then return `standard_model()`:
  ```python
  logger.info(
      "[MODEL_ROUTER] 4o cap reached: routing verdict to %s (used=%d cap=%d threshold=%.2f)",
      <the standard model id returned>, used, cap, self.SWITCH_THRESHOLD,
  )
  ```
  There is no log below the threshold and no log for `priority != "high"`. For every input with `DAILY_4O_CAP` unset, the return values are identical to base.
- **R2.3** Redis-down behaviour is unchanged: a failed read counts as 0 and the verdict stays on the verdict model. State it in the `get_model` docstring. The module docstring already says it. Also state it in the runbook section (R2.9).
- **R2.4 Carrier in `generate_comparison`.** On the SUCCESS path only, after the usage dict is built (`extraction_service.py:2750-2755`) and before `return parsed, usage` (`:2756`), add `usage["model_downgraded"] = True` when `verdict_model == standard_model() and standard_model() != _configured_verdict_model()`. Here `verdict_model` is the local model id the successful call ran on, possibly reassigned by the 429 fallback at `:2672`. `_configured_verdict_model` is `model_config.verdict_model` imported under an alias, because the local string shadows the name.
  - The key is ABSENT otherwise.
  - The failure path (`:2758-2760`) is byte-identical: `{"prompt_tokens": 0, "completion_tokens": 0}` with no key.
  - `parsed` (the comparison dict) is never touched.
  - Decision recorded (see "Open questions" OQ1): the marker is set both for the cap downgrade and for the 429/rate/quota fallback. In both cases the verdict actually ran on the standard model instead of the configured verdict model.
- **R2.5 Orchestrator state.**
  - `self._verdict_model_downgraded: bool = False` is initialised in `__init__`, next to `_partial_comparison` (`:3150`).
  - It is reset to False at the start of each run: the sync block ending `:3792` and the streaming block ending `:4398`.
  - It is set immediately after the verdict's `_track_gpt_cost(usage)` on both paths (sync `:4056`, streaming `:4833`) as `isinstance(usage, dict) and usage.get("model_downgraded") is True`.
- **R2.6 Self-critique regen** (`ENABLE_SELF_CRITIQUE`, default OFF).
  - `_regenerate` (`:8937-8962`) stashes the regen usage's marker. Suggested name: `self._regen_model_downgraded`, reset at the top of `_apply_self_critique`.
  - After the outcome (`self._verdict_critique_outcome = outcome` at `:8995`): when `outcome.regenerated is True`, set `self._verdict_model_downgraded` to the regen's value, because the regen verdict is the one served.
  - The 8 s timeout (`:8982-8985`) and a failed or rejected regen keep the original's value.
- **R2.7 Metadata.** In BOTH `_metadata_override` assemblies (sync `:4145-4162`, streaming `:4954-4974`), add `if self._verdict_model_downgraded: _metadata_override["model_downgraded"] = True`.
  - The key is ABSENT when false. This follows the precedent of `verdict_scrubbed` and keeps a non-downgraded response byte-identical to base.
  - It reaches `$.metadata.model_downgraded` on the sync 200 body and on the SSE `settle_complete` and `complete` events.
- **R2.8 Admin gauge.** `admin_routes.py:877` changes to `openai_4o_cap = ModelRouterService().daily_4o_cap()`, so the dashboard shows the cap the router uses. With the env unset it is byte-identical to base, and `TestCostsGauges` stays green.
- **R2.9 Runbook note** (docs only; no env change, which is Ahmed's action). Add a new §6 "Daily gpt-4o cap (`DAILY_4O_CAP`, #268)" to `docs/runbooks/2026-09-02-openai-tpm-launch-sizing.md`, with every number labelled MODELLED:
  - **What the counter counts.** `response.usage.total_tokens` of each SUCCESSFUL verdict call that ran on the configured verdict model. `record_usage` filters on `model_config.verdict_model()`, at `model_router_service.py:74-75` and `extraction_service.py:2697-2700`. It does not count the Tier-3 synthesis call, which is routed by `get_model("high")` but never recorded. Keys roll over at UTC midnight.
  - **Per-verdict tokens.** The prompt is 5,498 to 5,942 tokens (the offline count already in this runbook's §2 correction). The completion is bounded by `max_tokens=1000`, and its real size is UNMEASURED. That gives roughly 5.5k to 6.9k counted tokens per verdict (MODELLED).
  - **Shipped default.** `1,000,000 × 0.80 = 800,000` counted tokens, reached at about 116 to 145 verdicts per UTC day. This matches the memo's R-C14.
  - **~200 verdicts/day.** 200 × ~6.9k ≈ 1.38M tokens needs `cap ≥ 1.38M / 0.80 ≈ 1.73M`. Suggested setting: `DAILY_4O_CAP=2000000`, which puts the threshold at 1.6M, about 232 to 290 verdicts per day (MODELLED). The value is read per call, so no restart is needed.
  - The daily dollar cost of the chosen cap must be read from OpenAI's pricing page when the value is set. It is not stated here.
  - If `ENABLE_SELF_CRITIQUE` is ever turned on, a regenerated verdict spends a second verdict-model call, so size the cap for it.
  - The cap is a daily spend guard and is TPM-blind (§2). It does not protect the per-minute wall.
  - Redis-down means the counter reads 0, so every verdict runs on the verdict model and cap protection is lost until Redis returns (R2.3).
  - Observability: the INFO line `[MODEL_ROUTER] 4o cap reached: ...` in the Railway logs, and `metadata.model_downgraded: true` on each affected response.

---

## 3. Item 3: empty-message Sentry issues (`str(e)` is empty for timeouts)

### Facts

- Sentry (org `qaren-rr`, project `python-fastapi`, read 2026-09-30 per the task): PYTHON-FASTAPI-N `"Search error: "` (11 events) and PYTHON-FASTAPI-14 `"Serper shopping call error (gl=us): "` (4 events). The tails are empty because the exceptions are httpx timeouts (measured in §0).
- The sites are f-strings, so the exception text is baked into `record.msg`:
  - `serper_service.py:664-665` (`search_web`, def `:609`): `except Exception as e: logger.error(f"Search error: {e}")`. The return is `{"organic": [], "error": str(e)}` (`:669`), or the Bright Data fallback.
  - `serper_service.py:824-826` (`_do_serper_shopping`, def `:771`): `logger.error(f"Serper shopping call error (gl={gl}): {e}")`, then `return {}`.
  - `extraction_service.py:1710-1712` (`extract_specs`, def `:1552`): `logger.error(f"Specs extraction error: {e}")`, then `return {"brand": brand, "model": name, "error": str(e)}, {zero usage}`.
- **Sentry mechanics** (measured in `sentry_sdk/integrations/logging.py:326-332` of 2.68.1): the event is `logentry = {"message": record.msg, "params": record.args}`. Default integrations are used, and `sentry_service.py:299-310` passes no `LoggingIntegration` override, so `logger.error` produces an event and INFO/WARNING do not. With a CONSTANT `%s` template, `record.msg` never contains exception text. UNMEASURED here (Sentry server behaviour, recalled): Sentry groups message-only events by `logentry.message`. Either way the formatted message keeps the exact old prefix.
- **Existing scrubber.** `structured_comparison_service._safe_exc` (`:300-341`, R-W18) strips URL userinfo, query and fragment from every `scheme://` token, collapses line breaks and truncates to 200 characters. It is used at `:291, :1980, :2059, :2152`, and pinned by `tests/test_retro_w1_8.py` (`:683-728`, `:753-768`, `:1326-1360`, all via `scs._safe_exc`). No test monkeypatches it.
- **It cannot be imported without a cycle.** `structured_comparison_service.py:24` does `from app.services.extraction_service import (...)` and `:41` does `from app.services.serper_service import ...`, both at module top. A module-level `from app.services.structured_comparison_service import _safe_exc` in either leaf would import a partially initialised `scs`, because `_safe_exc` is defined at `:330`, after those imports, which gives an ImportError cycle.
- `sentry_service.py` has stdlib-only top-level imports (`os, re, copy, logging`; `sentry_sdk` is imported lazily at `:289-291`). Its `_scrub_string` (`:94-98`, patterns `:16-22`: JWT, `sk-proj-…`, `fc-…`, 32+ hex, `Bearer …`) can therefore be imported by a leaf.
- W4-9 left no reusable scrubber function. It replaced response strings with constants and added `exc_info=True`.
- **Every `logger.error` / `logger.exception` site in the two modules** (grep, complete). "Can be empty?" is decided from the measured exception texts in §0:

  | Site | Function | Try body raises | Can the text be empty? | Action |
  |---|---|---|---|---|
  | `serper_service.py:665` | `search_web` | httpx | YES (ReadTimeout/ConnectTimeout → `''`) | CHANGE |
  | `serper_service.py:825` | `_do_serper_shopping` | httpx | YES | CHANGE |
  | `serper_service.py:1013` | `search_price_organic` | httpx | YES | CHANGE |
  | `serper_service.py:1096` | `search_videos` | httpx | YES | CHANGE |
  | `serper_service.py:1173` | `search_news` | httpx | YES | CHANGE |
  | `extraction_service.py:1711` | `extract_specs` | the openai SDK (transport failures map to `'Request timed out.'` / `'Connection error.'`) plus any bare exception | YES for a no-arg exception such as `TimeoutError()` (probe `p3_specs`); the type is lost in every case | CHANGE (named in the task) |
  | `extraction_service.py:1763` | `extract_price` | openai SDK | no measured empty path | unchanged (OQ3) |
  | `extraction_service.py:1818` | `extract_price_from_training_data` | openai SDK | no measured empty path | unchanged (OQ3) |
  | `extraction_service.py:1548` | `parse_product_query` | | has `exc_info=True`, so the event carries the exception type and traceback | unchanged |
  | `extraction_service.py:1869` | `extract_reviews` | | `exc_info=True` | unchanged |
  | `extraction_service.py:2759` | `generate_comparison` | | `exc_info=True` | unchanged |

  These are not `error`/`exception` sites, so they are out of scope and unchanged:
  - `extraction_service.py:1397` (WARNING, LLM)
  - `serper_service.py:276, :323, :338, :351` (WARNING, `%s` of e, Redis/breaker helpers)
  - `serper_service.py:667` and `:1015` (INFO `[brightdata] ... failed (%s)` with `str(e)[:60]`)

  WARNING and INFO are below Sentry's default event level.
- **Measured at BASE** (probes): `search_web` with `_serper_post` raising `ReadTimeout('')` logs exactly `"Search error: "` and returns `{"organic": [], "error": ""}`. `_do_serper_shopping(..., "us")` with `ConnectTimeout('')` logs `"Serper shopping call error (gl=us): "` and returns `{}`. `extract_specs` with `guarded_llm_create` raising `TimeoutError()` logs `"Specs extraction error: "` and returns `{"brand": "B", "model": "N", "error": ""}`.

### Requirements

- **R3.1 Leaf module `app/services/log_scrub.py`.** Its only imports are `re` and `from app.services.sentry_service import _scrub_string`.
  - It takes over the R-W18 scrubber from `structured_comparison_service.py:300-341`: the regexes, `_SAFE_EXC_MAX_CHARS = 200`, `_safe_exc_url`, and the function body as `safe_exc(exc)`. `safe_exc` output must be identical to base for every input; `tests/test_retro_w1_8.py` pins it. Keep the R-W18 comment block with the code.
  - `structured_comparison_service` replaces those definitions with `from app.services.log_scrub import safe_exc as _safe_exc`. The four call sites (`:291, :1980, :2059, :2152`) and `scs._safe_exc` in tests resolve unchanged.
  - Factoring the text-level steps into a private `_scrub_text(text)` helper is allowed.
- **R3.2 `exc_summary(exc: BaseException) -> str`** in `log_scrub`:
  - `name = type(exc).__name__`.
  - `text = str(exc)`, guarded: a broken `__str__` returns `f"<unprintable {name}>"`.
  - Then `text = _scrub_string(text)` on the FULL text, then the R-W18 URL scrub, the line-break collapse and the 200-character truncation, in that order, so a cut can never land inside a credential.
  - Return `name` when the scrubbed text is empty or whitespace, else `f"{name}: {text}"`.
  - Never raises. It never adds a URL, key or query string that was not already in `str(exc)`, and it removes URL userinfo, query and fragment as well as the sentry key shapes.
- **R3.3 The six CHANGE sites** switch to a CONSTANT `%`-template. The formatted prefix is byte-identical to today and the argument is `exc_summary(e)`:
  - `serper_service.py:665`: `logger.error("Search error: %s", exc_summary(e))`
  - `serper_service.py:825`: `logger.error("Serper shopping call error (gl=%s): %s", gl, exc_summary(e))`
  - `serper_service.py:1013`: `logger.error("Price organic search error: %s", exc_summary(e))`
  - `serper_service.py:1096`: `logger.error("Video search error: %s", exc_summary(e))`
  - `serper_service.py:1173`: `logger.error("News search error: %s", exc_summary(e))`
  - `extraction_service.py:1711`: `logger.error("Specs extraction error: %s", exc_summary(e))`

  Import `exc_summary` at module top (`from app.services.log_scrub import exc_summary`). The leaf has no cycle.

  **Every return value stays byte-identical**, including the `"error": str(e)` fields and the Bright Data fallbacks. The adjacent INFO lines stay unchanged.
- **R3.4 Grouping** (logging-side contract, testable): `record.msg` for each CHANGE site is the constant template and contains no exception text. The exception summary travels only in `record.args`.
  - For the shopping site, `gl` becomes a param. Future events for all gl values group under one template instead of one issue per gl. This is a deliberate trade and is stated in the limits.
  - The old issues N and 14 stop receiving events after deploy. Resolve them then.

---

## 4. Item 4: `_GatheringFuture exception was never retrieved` (PYTHON-FASTAPI-1K/1J/Y/1N/17)

### Facts

- **The mechanism** (CPython 3.12.9 `asyncio.tasks.gather._done_callback`, source read from the venv). When the OUTER `_GatheringFuture` had `cancel()` requested, the last child completion runs `if outer._cancel_requested: exc = fut._make_cancelled_error(); outer.set_exception(exc)`. This happens regardless of `return_exceptions=True`. The outer future therefore ends FINISHED-with-exception (`<_GatheringFuture finished exception=CancelledError()>`), NOT cancelled. When nothing calls `.result()`/`.exception()` on it, `Future.__del__` reports `"_GatheringFuture exception was never retrieved"` through `loop.call_exception_handler`, which logs at ERROR on the `asyncio` logger and becomes a Sentry event.
  - The attached `CancelledError` is the last finished child task's own cancellation, so its traceback holds that child's frames. Those are the Sentry in-app frames: `structured_comparison_service.py:278` (`result = await asyncio.wait_for(make_coro(), timeout)` in `_timeout_none`) and `occ_service.py:285` (`resp = await asyncio.to_thread(...)` in `fetch_occ_rest_price`).
- **The leak site** is `structured_comparison_service.py:6700-6707`, inside `_get_price`:
  ```python
  def _cancel_prefetched_direct():
      for _task in _prefetched_direct.values():
          if not _task.done():
              _task.cancel()
      _prefetched_direct.clear()        # <- last reference dropped, exception never retrieved
  ```
  - The futures are `asyncio.ensure_future(asyncio.gather(..., return_exceptions=True))`. `ensure_future` returns the `_GatheringFuture` itself. They are created at `:6595-6698`: shopify `:6601`, algolia `:6612`, sitemap `:6652`, jsonapi `:6662`, and one per `_new_adapter_specs` family at `:6681-6698` (woo, salla, **occ** `:6573`, magento_gql, unbxd, rest_json, noon, shopify_gcc). Each child is a `_timeout_none(...)` lazy-factory task for the sitemap, jsonapi and new families.
  - It is called from `_cancel_prefetched_discovery` (`:6510-6520`, last line) at the genuine Tier-1 short-circuit and no-escalation returns, and from the M13-30 `finally` (`:8236-8244`) on EVERY exit of `_get_price`, including an outer `wait_for` cancel.
- **Not leak sites** (read):
  - The consume paths `await asyncio.wait_for(_prefetched_direct.pop(k), timeout=...)` (`:6751-6753`, `:6789-6791`, `:6828-6830`, `:7198-7201`, `:7299-7303`). On timeout or outer cancel the awaiting task cancels the gather and then receives its result through `result()`, which retrieves the exception.
  - The inline `wait_for(asyncio.gather(...))` consumes, for the same reason.
  - `_profile_task` gathers (`:3912`, `:4517`), which are awaited by `_cancel_profile_task` (`:574-587`).
  - `price_service.fan_out_price_lookup` (`:16968+`), which uses `create_task` Tasks. A cancelled Task ends CANCELLED and is never reported. Its exceptions are read via `t.exception()` at `:17090`.
  - Discovery `search_web` prefetch Tasks, which are cancelled Tasks.
- **Measured at BASE** (probes, through the real `_get_price`, all network monkeypatched). The capture is `loop.set_exception_handler`, then `gc.collect()`.
  - (a) Genuine Tier-1 short-circuit, children cancelled BEFORE running.
  - (b) The same, with children IN FLIGHT (the shopping mock sleeps 0.05 s, and the occ child started exactly once).
  - (c) The M13-30 path: an outer `task.cancel()` while parked at the shopping await, with the occ child in flight.

  Each produced 3 reports `('_GatheringFuture exception was never retrieved', '<_GatheringFuture finished exception=CancelledError()>')`: the occ, sitemap (bolo) and jsonapi (nasser) gathers. That is the exact Sentry text.
- **Fix measured in the scratch worktree** (then restored, sha-verified): adding `_task.add_done_callback(lambda f: f.cancelled() or f.exception())` to every entry in `_cancel_prefetched_direct` turned (a), (b) and (c) green. The existing cancellation pins stayed green, 20 passed (see the evidence section): `tests/test_adapter_prefetch_hook.py` (the prefetch and cancellation classes) and `tests/test_m13_30_get_price_finally.py`.

### Requirements

- **R4.1** Add a module-level helper in `structured_comparison_service.py` near `_timeout_none`:
  ```python
  def _retrieve_prefetch_outcome(fut: "asyncio.Future") -> None:
      """Done-callback: mark a speculative prefetch gather's outcome retrieved.
      A cancel()-requested _GatheringFuture finishes with set_exception(CancelledError)
      (CPython gather, even with return_exceptions=True); nothing awaits it after
      _cancel_prefetched_direct drops it, so asyncio would report
      'exception was never retrieved' at GC. Logging-only: no await, no result change."""
      if not fut.cancelled():
          fut.exception()
  ```
- **R4.2** In `_cancel_prefetched_direct`, for EVERY entry: keep `if not _task.done(): _task.cancel()` exactly as it is, then `_task.add_done_callback(_retrieve_prefetch_outcome)`, then `_prefetched_direct.clear()` as today.
  - `add_done_callback` on an already-done future schedules the callback at once, which is harmless: `.exception()` returns `None` or the exception.
  - Nothing is awaited. Which futures are cancelled, and when, is unchanged, and so are `_get_price`'s return values and timing bounds.
- **R4.3** No other change. In particular `_timeout_none` keeps `except Exception`; its docstring forbids widening to `BaseException`, which would turn cancellation into `None`.

---

## 5. RED test list (new files; use `"test-dummy-key"` style sentinels, never an `sk-`-shaped string)

Probe evidence for every RED below is in "Probe evidence". The probe files are scratch copies in the spec agent's scratchpad, not in the repo. The real tests are written fresh in the unit worktree.

**`tests/test_s70_url_client_retries.py`** (item 1). Save and restore `url_extraction_service._client` through `monkeypatch.setattr(usvc, "_client", None)`.
- `test_url_client_default_max_retries_is_two`: PIN (green at base).
- `test_url_client_respects_openai_max_retries_env`: env `1` gives 1, env `0` gives 0. RED at base (measured 2).
- `test_url_client_passes_explicit_max_retries_kwarg`: `AsyncOpenAI` spy, env unset, `kw["max_retries"] == 2`. RED at base (key absent).
- `test_url_client_cached_after_first_construction`: a second `get_client()` returns the same object after an env change. PIN.

**`tests/test_s70_model_router_downgrade.py`** (item 2). `monkeypatch.delenv("DAILY_4O_CAP")` unless the test sets it. Patch `_get_4o_usage_today` per instance.
- `test_downgrade_logs_exactly_one_info_line`: 800,000 used. Exactly one INFO record containing `[MODEL_ROUTER] 4o cap reached: routing verdict to gpt-4o-mini`, `used=800000` and `cap=1000000`. RED.
- `test_no_router_log_below_threshold_or_standard_priority`: 799,999 used, plus `priority="standard"` at full cap. PIN.
- `test_daily_cap_env_read_per_call`: env `2000000` with 1,000,000 used gives `gpt-4o`. The same instance, env `1000000`, gives mini. RED.
- `test_daily_cap_garbage_falls_back[...]`: `"abc","0","-5","0.5","inf","-inf","nan","1e309","1,000,000","","   "`. At 800,000 used the result is mini, and at 799,999 it is `gpt-4o`. Also assert `daily_4o_cap() == 1_000_000` directly (RED on that half: the method is absent). The routing half is a PIN (measured green).
- `test_class_constants_unchanged`: `DAILY_4O_CAP == 1_000_000` and is an int, `SWITCH_THRESHOLD == 0.80`. PIN.
- `test_generate_comparison_marks_cap_downgrade`: router patched to `standard_model()`, create succeeds, so `usage["model_downgraded"] is True` and `"error" not in parsed`. RED.
- `test_generate_comparison_marks_429_fallback`: router returns `gpt-4o`, the first create raises `RuntimeError("429 rate limit exceeded")`, and the fallback succeeds through `client.with_options`. The marker is True. RED. Use the `with_options` mock shape from `tests/test_verdict_response_format.py:94-140`.
- `test_generate_comparison_no_marker_on_verdict_model`: router returns `gpt-4o`, success, key absent. PIN.
- `test_generate_comparison_failure_has_no_marker`: router returns mini and create raises `RuntimeError("429 ...")`. The result is `(..."error"...)` with usage `== {"prompt_tokens": 0, "completion_tokens": 0}` (exact). PIN.
- `test_sync_body_carries_model_downgraded`: `GET /api/v1/text/compare` with the W4-9 phone shape (`product_a`/`product_b`, fragrances, nocache). `_fetch_product_data` is stubbed, `guarded_llm_create` returns a valid verdict JSON response, `model_router.get_model` returns `standard_model()`, `record_usage` is an AsyncMock and L3 moderation is allowed. Expect `success is True`, no `comparison.error`, and `metadata.model_downgraded is True`. RED (measured: key absent, verdict succeeded).
- `test_sse_settle_and_complete_carry_model_downgraded[off|on]`: the same, on `/api/v1/text/compare/stream`, with `ENABLE_FULL_STREAM_DEADLINE` unset or `true`. Both the `settle_complete` and `complete` events carry it. RED (measured for `complete`).
- `test_no_marker_key_when_verdict_model_used[sync|sse]`: the router returns `verdict_model()`, and `"model_downgraded" not in metadata`. PIN.
- `test_self_critique_regen_marker`: `ENABLE_SELF_CRITIQUE=true`. The original ran on the verdict model, the regen ran on mini and `regenerated=True`, so the marker is True. With the regen rejected (error dict) the marker stays at the original's value. RED on the first half. Drive `_apply_self_critique` directly with `verdict_critique_service.critique_and_maybe_regenerate` patched to call `regenerate` and return a `CritiqueOutcome`.
- `test_admin_gauge_uses_env_cap`: `DAILY_4O_CAP=2000000` and Redis `"500000"` give `cap == 2000000` and `pct == 25.0`. RED. The unset case stays `pct == 50.0` (existing PIN `TestCostsGauges`).

Copy the minimal W4-9 harness into the new file: `_reset_rate_limiter`, `_default_flag_state`, `_serper_unconfigured`, `client`, `_sse`, `_fake_fetch`, `_PAIR_PARAMS`. See `tests/test_w49_extraction_catch_redaction.py:70-120, 190-265`. Do NOT import another test module.

**`tests/test_s70_exc_summary_logs.py`** (item 3)
- `test_exc_summary_shapes`: `ReadTimeout("")` gives `"ReadTimeout"` and `TimeoutError()` gives `"TimeoutError"`. `ValueError("bad")` gives `"ValueError: bad"`. `"a\nb"` collapses to one line. A 5,000-character text keeps at most 200 characters after `"Name: "`. A broken `__str__` returns `"<unprintable X>"` without raising. RED (the module is absent).
- `test_exc_summary_strips_credentials_and_query`: `RuntimeError("x https://user:hunter2@h.test/p?q=SECRET#frag y")` must not contain `hunter2`, `SECRET` or `frag`. `RuntimeError("Bearer abc.def.ghi")` becomes `Bearer [REDACTED]`. A 40-character lowercase hex token is redacted. RED (the module is absent).
- `test_safe_exc_reexport_is_identical`: `scs._safe_exc is log_scrub.safe_exc`. The existing `tests/test_retro_w1_8.py` `_safe_exc` pins stay green. RED.
- `test_site_logs_name_the_type[...]`, parametrised over the six CHANGE sites. For each, drive the real function with the transport or LLM call raising an empty-text exception (`httpx.ReadTimeout("")` / `httpx.ConnectTimeout("")` / `TimeoutError()`). Assert:
  - (i) exactly one ERROR record whose `getMessage()` equals `<old prefix><TypeName>`, for example `"Search error: ReadTimeout"` and `"Serper shopping call error (gl=us): ConnectTimeout"`;
  - (ii) `record.msg` is the constant template (`"Search error: %s"`, and so on) and contains no type name;
  - (iii) the RETURN VALUE equals the base value byte-for-byte, for example `{"organic": [], "error": ""}`, `{}`, and `({"brand": "B", "model": "N", "error": ""}, {"prompt_tokens": 0, "completion_tokens": 0})`.

  RED at base on (i)/(ii) (measured for `search_web`, shopping and `extract_specs`).

  Setup notes:
  - For `search_web`, patch `serper_service._active_serper_key` to return a dummy, `_serper_budget_ok` to return True, and `app.services.brightdata_service._brightdata_enabled` to return False. The latter is imported function-locally at `serper_service.py:629`.
  - The organic, video and news sites need the same key and budget stubs. Read each function's preamble.

**`tests/test_s70_prefetch_gather_retrieved.py`** (item 4). Use a helper that installs `loop.set_exception_handler` capturing contexts and restores the previous handler in `finally`. After the scenario: 20× `await asyncio.sleep(0)`, then `gc.collect()`, 5× `sleep(0)`, then `gc.collect()`. Assert that no context has `"never retrieved"` in `message`. Stub the cascade as in `tests/test_adapter_prefetch_hook.py::_stub_common` plus `get_occ_sources_for_category → [SimpleNamespace(domain="occ.test")]`, with `fetch_occ_rest_price`, `fetch_bolo_price` and `fetch_nasser_price` as sleeping coroutines. Make `search_web` HANG, not raise: a raising mock in a discovery prefetch Task produces an unrelated "Task exception was never retrieved" (measured).
- `test_mechanism_cancelled_gather_reports_unretrieved`: a pure-asyncio PIN documenting the CPython behaviour R4 relies on (measured green).
- `test_get_price_tier1_short_circuit_prerun_no_unretrieved_gather`: RED (measured, 3 reports).
- `test_get_price_tier1_short_circuit_inflight_no_unretrieved_gather`: the shopping mock sleeps 0.05 s and the occ child started exactly once. RED (measured, 3 reports).
- `test_get_price_outer_cancel_no_unretrieved_gather`: the M13-30 `finally` path. RED (measured, 3 reports).
- `test_prefetch_children_still_cancelled`: in the in-flight scenario the occ child receives `CancelledError`, so the cancellation semantics are unchanged. PIN.

---

## 6. Gates (all through the bounded runner `scratchpad/harness/pyt.py`; paste every `[pyt]` line)

1. **New test files at BASE and HEAD.** At BASE, copy them into a detached scratch worktree at `94c097cd`: every RED is red and every PIN is green. At HEAD everything is green. Bound 600 s.
2. **MODULE-REFERENCE comm gate.**
   - Build the set by module reference, never by filename keyword:
     ```
     grep -rlE "\b(url_extraction_service|model_router_service|model_router|extraction_service|structured_comparison_service|serper_service|admin_routes|log_scrub)\b" tests/ --include=*.py | grep -E "/test_[^/]*\.py$" | sort -u
     ```
     Measured at base: **245 files**, without `log_scrub`, which is new. Rebuild the set at HEAD; it adds the four new files.
   - Drop `admin_routes` from the pattern only if R2.8 is dropped by ruling.
   - Run the same list at BASE (a detached scratch worktree under your notes folder) and at HEAD, in chunks of ≤ 25 files, bound 1200 s per chunk.
   - `comm -13` the sorted FAILED/ERROR node ids (BASE vs HEAD). The branch-only-NEW set must be EMPTY.
3. `ruff check --select E9,F63,F7,F82 --no-cache` plus `python -m py_compile` on every changed `.py`:
   - `app/services/url_extraction_service.py`
   - `app/services/model_router_service.py`
   - `app/services/extraction_service.py`
   - `app/services/structured_comparison_service.py`
   - `app/services/serper_service.py`
   - `app/services/log_scrub.py`
   - `app/api/admin_routes.py`
   - the four new test files
4. `tests/test_security_regression.py` is green at HEAD. It is inside the 245-file set; also report it on its own line.
5. `git diff --stat`: no whole-file diffs. The working copy is CRLF and the index LF, so use the Edit tool.
6. Pre-existing noise, not a defect of this unit. It appears equally at BASE and HEAD:
   - `test_adapter_prefetch_hook.py::TestNonSupplementAdapterHook::test_adapter_miss_falls_through_to_discovery` and `::TestAdapterCancellationNoOrphan::test_lazy_factory_contract_holds_on_adapter_miss_cancel_path` show `[netguard] blocked ... getaddrinfo api.openai.com:443` but still pass.
   - That file's `boom_search` mocks log "Task exception was never retrieved".

## 7. Stated limits

- `metadata.model_downgraded` is carried ONLY on full sync and SSE responses built by `compare_from_text`, `compare_from_text_streaming` and the camera route through `compare_from_text`. It is NOT carried on:
  - partial responses (`_build_partial_response`, metadata literal `:3570-3576`);
  - `/api/v1/url/compare` (`url_extraction_service.py:643` discards usage).

  Where a stored response is re-served (history, share), the key describes the verdict stored in it.
- The marker is set for BOTH the cap downgrade and the 429/rate/quota fallback (OQ1). The two are told apart only in the logs: INFO `[MODEL_ROUTER] 4o cap reached` versus the existing WARNING `[model_router] ... rate-limited mid-call; falling back to ...` at `extraction_service.py:2667-2671`.
- The INFO line fires on every `get_model("high")` call past the threshold. That includes the Tier-3 synthesis call (`scs:905`), whose line also says "routing verdict" (OQ2). At about 200 verdicts per day past the threshold this is up to a few hundred INFO lines per day.
- `DAILY_4O_CAP` values below 1 fall back to the default. So do comma-grouped values (`1,000,000`), hex, inf and nan. Underscores (`1_000_000`) and exponent form (`2e6`) ARE accepted, because `float()` accepts them (measured).
- Item 3 grouping: the shopping site's `gl` moves into a parameter, so future events for all gl values share one Sentry issue. Existing issues N and 14 stop receiving events. Sentry's server-side grouping algorithm was not measured here.
- Item 3 does not add key redaction to the three unchanged LLM `logger.error` sites (`:1763`, `:1818`) or to the WARNING and INFO lines.
- The sizing numbers in R2.9 are MODELLED. The verdict completion size is unmeasured.
- The cap is TPM-blind.
- `exc_summary` scrubs with the existing sentry patterns plus the R-W18 URL scrub. A secret shape outside those patterns is not redacted, but the same text is already logged raw at base.

## 8. Stop conditions

- **Hit: none.** No item changes a return value, a timing bound, a cancellation or a user-visible response beyond the additive, absent-unless-true `metadata.model_downgraded`. Measured basis: the marker experiment kept `success`, the comparison and all other metadata keys. The gather fix awaits nothing. Every item-3 site keeps its return value.
- **Triggers for the implementer.** STOP and report if:
  - the carrier needs a change to `generate_comparison`'s return ARITY, or to any other caller's unpack;
  - any existing test asserts equality on a success-path usage dict from `generate_comparison` with the router patched to the standard model (grep found none, only failure-path equality at `test_w49...:325,379`);
  - moving `_safe_exc` changes any `test_retro_w1_8.py` result;
  - the gather fix needs an `await` in `_cancel_prefetched_direct`;
  - a CHANGE site's return value would differ.

## 9. Open questions

- **OQ1.** Should `model_downgraded` also cover the 429-fallback verdict? This spec says yes: the verdict actually ran on the standard model. The orchestrator may restrict it to the cap reason, by computing it at `:2525` before the fallback instead of at the success point.
- **OQ2.** The router log line is mandated to say "routing verdict". It also fires for the Tier-3 synthesis `get_model("high")` call (`scs:905`). The options are to accept that, or to add an optional `purpose="verdict"` kwarg, which would be a signature change touching the Tier-3 mocks in `tests/test_tier3_synth.py`.
- **OQ3.** Should `extract_price` (`:1763`) and `extract_price_from_training_data` (`:1818`) also adopt `exc_summary`? They have the same shape as `:1711` but no measured empty-text path; the task's only-where-empty rule leaves them unchanged.
- **OQ4.** Is R2.8 (the admin gauge reads the env cap) accepted as in scope? It is byte-identical with the env unset.
- **OQ5.** CLAUDE.md context files are merge-time orchestrator work:
  - add a `DAILY_4O_CAP` env-knob entry next to `OPENAI_MAX_RETRIES` (`CLAUDE.md:350`);
  - retire the "four of the five" correction (`CLAUDE.md:351`) once #265 ships;
  - update the `model_router_service.py` line (`CLAUDE.md:169`).
- **OQ6.** `DAILY_4O_CAP=2000000` is a MODELLED suggestion. The value and its cost are Ahmed's decision, and the env change is his action.

## 10. Probe evidence (spec agent, 2026-09-30; scratch worktree `scratchpad/oai/base` at `94c097cd`)

Probe files (scratch only, never committed): `tests/test_zz_oai_probe.py` and `tests/test_zz_oai_probe_pipeline.py`. They ran in the scratch worktree, which was removed after the runs (`git worktree remove --force`). Copies, the run logs and `modref_files.txt` are kept in the spec agent's scratchpad folder `oai/`.

| Run | `[pyt]` line (abridged) | Result |
|---|---|---|
| All probes at BASE | `tag=oai-probe-base5 elapsed=8s status=FAIL rc=1` | 11 failed, 15 passed. Each of the 11 is a RED-EXPECTED probe failing for the stated reason. All PINs green, including 10 garbage-cap params, both asyncio mechanism probes, the url client default and the carrier on `gpt-4o`. |
| Pipeline probes at BASE | `tag=oai-probe-pipe elapsed=7s status=FAIL rc=1` | 3 failed (sync, SSE off, SSE on). `metadata` lacks `model_downgraded` although `success` is true and the comparison has no error. |
| Gather-fix experiment (R4 shape) | `tag=oai-probe-fixexp2 elapsed=11s status=OK rc=0` | 20 passed: p4 ×4 plus the `test_adapter_prefetch_hook` prefetch and cancellation classes plus `test_m13_30`. |
| Marker experiment (R2.4 carrier, R2.5 set, R2.7 both override sites) | `tag=oai-probe-markerexp elapsed=8s status=OK rc=0` | 5 passed: sync, SSE off, SSE on, and the carrier ×2. |

After each experiment, `structured_comparison_service.py` (sha256 `f85a66c7…6edd`) and `extraction_service.py` (sha256 `58ecc775…69fe`) were restored from byte copies in the scratch worktree and sha-verified as MATCH. The unit worktree was never edited, except for this file.

## Review corrections (BINDING - supersede the body)

Adversarial spec review, 2026-09-30 03:35-04:00 AST, at base `94c097cd` (read-and-measure only; no source edit in any worktree). Every body claim below was re-measured; the ones not listed here stood. Measurements: `[pyt] tag=adv-oai-pins elapsed=30s status=OK rc=0` over the nine existing pin files the body relies on (`test_model_router`, `test_admin_referral_endpoints`, `test_m18_openai_tpm_sizing`, `test_llm_provider_base_url`, `test_retro_w1_8`, `test_tier3_synth`, `test_verdict_response_format`, `test_m13_30_get_price_finally`, `test_adapter_prefetch_hook`): 191 passed at base, with `[netguard] blocked 12 attempt(s) from 2 node(s)` (the two known `test_adapter_prefetch_hook` miss-path nodes, egress `api.openai.com:443`). A stdlib-plus-pinned-httpx probe (no `app.*` import, no network; `scratchpad/oaiadv/probe_pure.py`) reproduced the item-4 mechanism and the R4 fix (see C11), and the float/str tables.

**Confirmed, no correction:** only `url_extraction_service.py:32` lacks `max_retries` among the five `AsyncOpenAI(` sites in `app/` (`extraction_service:72`, `openai_service:34/:63/:72`, `url_extraction_service:32`; there is no sync `OpenAI(` and no other SDK client). `generate_comparison` (`extraction_service.py:2525`) is the ONLY verdict-model selection site, shared by the sync, streaming, self-critique and `/url/compare` callers; the only other `get_model("high")` is Tier-3 synthesis (`scs:905`), and `extract_specs_synthesized` has one caller. No test monkeypatches `DAILY_4O_CAP`: `tests/test_model_router.py` READS it seven times (:39, :41, :74, :87, :96, :105, :222), which stays valid with the env unset. No test asserts the old log texts of the CHANGE sites, and no test references `_SAFE_EXC_*` or `_safe_exc_url` (only `scs._safe_exc`). No test patches `asyncio.ensure_future` or `asyncio.gather` inside `scs`. All five prefetch gathers pass `return_exceptions=True` (`:6607`, `:6618`, `:6653`, `:6672`, `:6696`), so the outer future's ONLY possible exception is the cancel-requested `CancelledError`. The R4 callback therefore cannot swallow a real exception (child exceptions are already consumed as results; measured: a raising child inside a cancelled gather produces only the CancelledError report at base). It awaits nothing, and a later awaiter still receives `CancelledError` (measured). The JSON log formatter uses `record.getMessage()` (`app/middleware/logging_config.py:16`), so the %-template keeps the Railway line text.

- **C1 (item 3, consistency; answers OQ3 = YES).** `extract_price` (`:1763`) and `extract_price_from_training_data` (`:1818`) have the SAME try body as `extract_specs` (`:1711`): exactly one `_llm_breaker.guarded_llm_create` call (`:1579`, `:1738`, `:1787`; no other await) and then a JSON parse, with the same `except Exception as e: logger.error(f"...{e}")` shape. The body's only empty-text evidence for `:1711` is an injected no-arg `TimeoutError()` on that call, and that evidence applies to `:1763` and `:1818` identically. By the body's own criterion they are CHANGE sites:
  - `logger.error("Price extraction error: %s", exc_summary(e))`
  - `logger.error("Price fallback error: %s", exc_summary(e))`

  Their return values stay byte-identical (`"error": str(e)` is kept). There are now **8 CHANGE sites**. Add both to `test_site_logs_name_the_type` (the expected messages are `"Price extraction error: TimeoutError"` and `"Price fallback error: TimeoutError"`) and to the return-value pins (C3). Stated limit §7 bullet 6 is withdrawn for these two sites.
- **C2 (facts table §0/§3).** On the pinned httpx 0.28.1 / httpcore 1.0.9, the real `map_httpcore_exceptions` over an empty-text httpcore error gives `str(e) == ''` for `ReadTimeout`, `ConnectTimeout`, `WriteTimeout`, `PoolTimeout`, `ConnectError` AND `ReadError` (measured). So the five serper CHANGE sites can be empty for connection errors as well as timeouts. This changes no requirement.
- **C3 (RED/PIN hygiene at BASE, all four new files).**
  - No module-top import of anything this unit creates: `app.services.log_scrub`, `exc_summary`, `safe_exc`, `daily_4o_cap`, `_retrieve_prefetch_outcome`. Import or look them up INSIDE each test body. Otherwise a file is a collection ERROR at base, and gate 1 ("every PIN is green at base") cannot be shown.
  - Split item 3's return-value check (iii) out of `test_site_logs_name_the_type` into its own parametrised PIN, `test_site_return_value_unchanged[<8 sites>]`. As written, (iii) never executes at base, because (i) fails first.
- **C4 (netguard ratchet - a CI gate the body omits).** CI fails on any NEW test node that attempts egress (`scripts/netguard_ratchet.py`, `.github/workflows/ci.yml:133`, baseline `tests/.network_attempt_baseline.txt`). The two `test_adapter_prefetch_hook` miss-path nodes whose `_stub_common` the item-4 file copies ARE egress nodes (`api.openai.com:443`, measured above).
  - The item-4 scenarios must stub every LLM leg `_get_price` can reach (the Tier-2 / Tier-3 price LLM calls: `extract_price`, `extract_price_from_training_data`, and `extraction_service.get_client`), or stay on paths that return before those legs.
  - The item-2 pipeline tests must keep the W4-9 harness stubs. That harness's nodes are sentinel-class only.
  - **Added gate:** the HEAD run of the four new files prints NO `[netguard]` line that names a `tests/test_s70_` node.
- **C5 (comm set misses path-scanning tests).** The module-reference grep cannot select tests that walk `app/services/*.py` or `app/**/*.py` by path. Add these by name to BOTH sides of the comm gate:
  - `tests/test_model_config.py`. It is NOT in the 245-file set, and `TestNoStrayModelLiterals` fails on any quoted `"gpt-..."` literal in any `app/services/*.py`, for example in a new router docstring or log text, or in `log_scrub.py`.
  - `tests/test_auth_error_log_hygiene.py`. It walks `app/` and pins the Sentry `LoggingIntegration` defaults that item 3's reasoning depends on.
  - `tests/test_sentry_service.py` and `tests/test_observability.py`. They pin the `_scrub_string` / `before_send` behaviour that `exc_summary` reuses; `test_observability` also `importlib.reload`s `sentry_service`.
  - `tests/test_shopify_pdp_json.py` and `tests/test_retro_w1_2b.py` (app-wide text scans).

  Implementation: add `sentry_service|model_config` to the grep pattern. Measured at base, that selects 252 files (+7), which already include the first four files above. Then add `tests/test_shopify_pdp_json.py` and `tests/test_retro_w1_2b.py` by name, for 254 at base plus the four new files at HEAD.
- **C6 (R2.9 runbook §6: decision inputs the body omits; answers OQ6 together with the body).**
  - **(a) Paid tokens above the free allowance.** The router's own module docstring gives the cap's purpose: "never fall off the data-sharing free tier mid-day". A `DAILY_4O_CAP=2000000` cap at the 0.80 threshold lets up to 1.6M counted verdict tokens through per UTC day. That is beyond a 1M/day complimentary gpt-4o allowance, so the excess bills at list price. Whether the account is enrolled in data sharing at all is UNMEASURED. State both next to the pricing-page line.
  - **(b) The counter under-counts real gpt-4o spend.** The Tier-3 synthesis call (routed at `scs:905`; `max_tokens` 300 at `openai_service.py:411`; up to 2 per compare) runs on gpt-4o below the threshold and is never recorded. The cap bounds verdict tokens, not total gpt-4o tokens.
  - **(c) What "successful" means.** A counted call is a verdict API call that RETURNED a response on the configured verdict model. `record_usage` (`:2700`) runs before the JSON parse, so a response that later fails to parse is still counted.
  - **(d) Overshoot.** Increments land after each call, so concurrent in-flight verdicts can overshoot the threshold by about (concurrency x ~6.9k) tokens.
  - **(e) Operator trap.** `2,000,000` (commas) and `0x...` are rejected and SILENTLY fall back to 1,000,000. Write digits only (`2000000`; `2e6` and `2_000_000` are also accepted, measured). After setting the value, verify it with `GET /api/v1/admin/costs/gauges` → `openai_4o_today.cap` (R2.8 makes that field the live cap), or with the `cap=` field of the INFO line.
  - **(f) The INFO line also fires for Tier-3 synthesis** (C10), so line counts overstate downgraded verdicts. Count `metadata.model_downgraded` instead.
- **C7 (pre-merge env check - orchestrator only, variable NAMES only, never an agent).** This unit makes a previously INERT env name live on deploy. The last recorded `web` name list (`docs/investigations/2026-09-06-full-review-state/baseline/railway-web-vars.txt`, 2026-09-05) has no `DAILY_4O_CAP`, but it is 25 days old. Before merge, confirm that the name is absent on `web`, or that its value is intended. Also state in the PR body that `OPENAI_MAX_RETRIES=1` is already live on `web`, so item 1 changes `/url/*` page extraction from 3 attempts to 2 at deploy (intended).
- **C8 (R2.7 robustness).** At both metadata sites, read the flag as `getattr(self, "_verdict_model_downgraded", False)`. That is the idiom those two blocks already use for `_source_trace`, `_provider_attempts` and `_verdict_critique_outcome`. Tests build the service via `StructuredComparisonService.__new__` (`test_cascade_hardening.py:11`, `test_js_rendering.py:43/:101`, `test_page_scraping.py:132`, `test_luxury_price_tiers.py:10`, `test_retro_w0_4.py:526`); none reaches those blocks today, but the getattr costs nothing. R2.5's resets and sets are unchanged.
- **C9 (R3.4 / §7: the Sentry grouping scope is wider than issues N and 14).**
  - With f-strings, each distinct exception text was its own issue. From deploy on, EVERY existing issue fed by the 8 sites stops receiving events, not only N and 14. Examples are any `"Search error: Client error '403 Forbidden' ..."` issues from the Serper-403 period (CLAUDE.md's Serper rotation playbook says to "resolve the Sentry Search-error issues", plural) and every per-text `"Specs extraction error: ..."` issue. One issue per template then collects all exception types.
  - Grouping uses `logentry.message or logentry.formatted`, which is the template. That is recalled, not measured, as in the body.
  - After the first post-deploy timeout event, confirm that its title reads `Search error: ReadTimeout`. Then resolve all the old per-text issues of the 8 sites with a root-cause comment. An alert rule bound to an old issue id stops firing.
  - Measured in `sentry_sdk` 2.68.1 (`integrations/logging.py:326-332`): the event also carries `logentry.formatted = record.getMessage()`. `_before_send` walks `logentry` with `_scrub_dict` (strings and tuple params), so the summary and `gl` are scrubbed there as well. There is no new leak path: `exc_summary` only ever removes text that the old f-string logged raw.
- **C10 (OQ2 decision: accept the mandated wording, add NO `purpose` kwarg).** `tests/test_tier3_synth.py:96` pins `mock_get_model.assert_awaited_once_with(priority="high")`, so passing `purpose=` at `scs:905` would redden it. Document the Tier-3 emission in the runbook (C6(f)) and in §7.
- **C11 (item-4 capture harness caveat, measured).** In this review's probe, a leftover reference to the last `_GatheringFuture` (a `for` loop variable) deferred its `__del__` until AFTER the exception handler was restored. The report then escaped the capture to stderr, and the scenario read as clean although it leaked. The helper must drop every reference to a prefetch future and run the full sleep / `gc.collect()` sequence INSIDE the handler scope. Each RED must show at least 1 capture at base, which the body's probes did (3 per scenario).
- **Follow-ups (recorded, NOT in scope):**
  - `cache_service._redis_get` (`:183`) logs `logger.error(f"Redis GET error: {e}")`, the same empty-text shape (the Upstash REST client raises httpx errors). It also runs as blocking I/O inside the async `get_model`. Both are pre-existing.
  - The discovery prefetch Tasks (`_cancel_prefetched_discovery`) can still produce "Task exception was never retrieved" when a mocked `search_web` raises. In production `search_web` and `bd_search_web` never raise.

**Answers to the writer's open questions.**
- **OQ1: accept.** Mark both the cap downgrade and the 429 fallback: in both cases the verdict ran on the standard model, which is the task's definition. The reason is told apart in the logs.
- **OQ2: accept the mandated text, no kwarg** (C10).
- **OQ3: yes, binding** (C1).
- **OQ4: yes, R2.8 is in scope.** Without it the dashboard would show 1,000,000 while routing uses the env value. It is byte-identical with the env unset, and `TestCostsGauges` is green at base (measured).
- **OQ5: accept as merge-time orchestrator work**, with these additions:
  - `CLAUDE.md:350` still says "all four `AsyncOpenAI` constructions"; change it to five.
  - `CLAUDE.md:169` gains the INFO line, `metadata.model_downgraded` and the `DAILY_4O_CAP` env read.
  - The Serper rotation playbook's "resolve the Sentry Search-error issues" gains "(one template issue since session 70)".
- **OQ6: agree, it is Ahmed's decision and action**, with C6(a) and C6(b) in front of him.
- **OQ7 (Sentry server grouping unmeasured): accept.** The logging-side contract is the testable part. Add the post-deploy confirmation step in C9.

**Verdict: APPROVED_WITH_CORRECTIONS.** No stop condition is hit, and no item forks behaviour for legitimate traffic with the env unset. The changes at deploy are the intended `OPENAI_MAX_RETRIES=1` reaching `/url/*` and log text. The only response change is the additive, absent-unless-true key.

---

## Orchestrator rulings (BINDING — session 71, 2026-10-03; supersede the body AND settle every open question of the review section above)

Ruled by the session-71 orchestrator. Where a ruling and the body disagree, the ruling wins; where a ruling and the "Review corrections (BINDING)" section disagree, the ruling wins; everything in that review section not touched here stays binding as written (all eleven corrections C1–C11 apply, including C3's no-module-top-import rule, C4's netguard gate, C5's 254-file comm set, C8's `getattr`, and C11's capture-harness rule).

- **OQ1 — `metadata.model_downgraded` covers BOTH the cap downgrade and the 429/rate/quota fallback** (the review's answer). The key is a bare boolean `true`, present only when true; **no reason field is added**: the two causes are told apart in the logs (INFO `[MODEL_ROUTER] 4o cap reached …` vs the existing WARNING `[model_router] … rate-limited mid-call …`), and a second key would widen the response contract for no consumer.
- **OQ2 — accept the mandated line text; no `purpose` kwarg** (C10). The Tier-3 synthesis emission is documented in the runbook §6 (C6(f)) and in the spec's limits.
- **OQ3 — YES, binding (C1): EIGHT change sites** (the five serper sites, `extract_specs`, `extract_price` → `"Price extraction error: %s"`, `extract_price_from_training_data` → `"Price fallback error: %s"`), all with byte-identical return values and the split return-value PIN of C3.
- **OQ4 — YES, R2.8 is in scope** (`admin_routes` reads `ModelRouterService().daily_4o_cap()`; byte-identical with the env unset; `TestCostsGauges` stays green).
- **OQ5 — CLAUDE.md / context-file edits are the orchestrator's at merge** (the three lines the review lists plus the Serper rotation playbook line). Agents do not edit `CLAUDE.md`.
- **OQ6 — `DAILY_4O_CAP` sizing is Ahmed's decision and env action.** The runbook §6 (R2.9) carries C6(a)–(f) in front of him, every number labelled MODELLED; nothing is set on Railway by this unit.
- **OQ7 — accept** (Sentry server-side grouping unmeasured; the logging-side contract is the testable part; the post-deploy confirmation step of C9 goes into the PR body).
- **OR1 — C7 is the orchestrator's pre-merge step** (Railway `web` variable NAMES only; confirm `DAILY_4O_CAP` is absent or intended). No agent touches Railway.
- **OR2 — the partial RED files on disk are UNVERIFIED work of a RED agent that died at the session-70 usage limit.** At the start of session 71 they hash (sha256 prefixes) `tests/test_s70_exc_summary_logs.py` = `8e6c12f180e8c7ea…`, `tests/test_s70_model_router_downgrade.py` = `2d70b4484e580dbd…`, `tests/test_s70_url_client_retries.py` = `9368b8d1835ab441…` (all untracked); the fourth file `tests/test_s70_prefetch_gather_retrieved.py` does not exist yet. The RED agent re-hashes the three, reads them in full, checks them against C1/C3/C4/C11 (eight sites; no module-top imports of `log_scrub`/`exc_summary`/`safe_exc`/`daily_4o_cap`/`_retrieve_prefetch_outcome`; the split return-value PIN; the capture harness that drops every future reference inside the handler scope), finishes or rewrites them, writes the fourth, and proves every RED red and every PIN green at BASE (a detached scratch worktree at `94c097cd` under its scratchpad) and runs the four at HEAD through the bounded runner. It never assumes the dead agent's work is correct.
- **OR3 — spec copies.** This spec file exists at the same path on the docs branch `docs/session-70-checkpoint` (PR #277, bytes identical before this section was appended to both copies) and as an UNTRACKED copy in `sc-s70-oai`. No agent edits it. The orchestrator deletes the untracked copy (after a sha compare) immediately before rebasing the unit branch onto a main that carries it.
- **OR4 — follow-ups the review recorded** (`cache_service._redis_get` empty-text ERROR log + blocking I/O inside async `get_model`; discovery prefetch Tasks' "Task exception was never retrieved" under a raising mock) are filed as issues by the orchestrator at merge; they are NOT in scope.
- **OR5 — gates, made exact.** Gate 1 at BASE and HEAD, bound 600 s; the comm gate's pattern is `\b(url_extraction_service|model_router_service|model_router|extraction_service|structured_comparison_service|serper_service|admin_routes|log_scrub|sentry_service|model_config)\b` plus `tests/test_shopify_pdp_json.py` and `tests/test_retro_w1_2b.py` by name (254 files at base, +4 at HEAD), chunks of ≤ 25 files, bound 1200 s per chunk, `comm -13` of the sorted FAILED/ERROR node ids with the branch-only-NEW set EMPTY; ruff `E9,F63,F7,F82` + `py_compile` on every changed `.py`; `tests/test_security_regression.py` green at HEAD on its own line; the C4 netguard line (no `[netguard]` line naming a `tests/test_s70_` node at HEAD); `git diff --stat` with no whole-file rewrite (CRLF working copy, Edit tool only).
