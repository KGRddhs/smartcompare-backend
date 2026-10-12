# S77 unit REDIS-OFFLOOP: price-path Upstash calls off the event loop

Branch `feature/s77-redis-offloop`, worktree `sc-s77-catalog`, base main `7b224c5a`. All file:line refs are at `7b224c5a`.
Flag: `ENABLE_PRICE_PATH_REDIS_OFFLOOP` (default OFF, read PER CALL). Knob: `REDIS_OFFLOOP_MAX_WORKERS` (default 16, read ONCE when the pool is built).

## 0. Why (measured, session 77 ledger)

- One cold compare blocks the loop 6.5-16.2 s (`/health loop_lag_max_60s_ms`); session baseline b0 (every load flag OFF): max lag 16190 ms, /health misses 14, warm-up 1/3 ready.
- Cached Shopify catalogs (`shopify_catalog:<domain>`) are 0.3-2.4 MB each (23 MB over 40 keys); one GET of the largest takes 0.9-2.2 s; a small Upstash call takes ~180 ms on a fresh connection. Network to Serper is fine (2-16 ms).
- Verified diagnosis (wf_c47dbd71): `price_service._fetch_shopify_catalog` does a synchronous `get_cached` before any await, so 18-36 catalog GETs per compare run back to back on the loop. No existing flag covers them (they call `get_cached`/`set_cached` directly, not `scs._cache_get_async`).

## 1. Site table (IN scope)

All call shapes below are today's exact shapes; they MUST stay positional and unchanged on the OFF path.

| id | file:line | sync call(s) | enclosing fn (async?) | caller chain (proves async) | calls / compare | fix |
|---|---|---|---|---|---|---|
| S1a | price_service.py:15159 | `get_cached(cache_key)` (`shopify_catalog:<domain>`, 0.3-2.4 MB) | `_fetch_shopify_catalog` :15146 (async) | `fetch_shopify_price` :15555 (async, `await` at :15567) <- scs bahrain prefetch gather :6888-6902, shopify_gcc spec :6883 via `_timeout_none` :6974-6990, escalation fallback scs:7508 | 2 x (bahrain Shopify + gcc-Shopify sources): electronics 18, fragrances 36, makeup 28, other 28, skincare 26, haircare 22, grocery 10, fashion 8, supplements 12 (diagnosis recount, ENABLE_BH_GCC_CATALOG_SOURCES on) | `cached = await run_redis_offloop(get_cached, cache_key)` |
| S1b | price_service.py:15166-15167 (calls :15180, :15185, :15191, :15194) | `set_cached(cache_key, _SHOPIFY_NEG_SENTINEL, _SHOPIFY_NEG_TTL)` | closure `_negcache` inside S1a | same | 0 on hit; 1 per failed source on miss | `async def _negcache(): await run_redis_offloop(set_cached, cache_key, _SHOPIFY_NEG_SENTINEL, _SHOPIFY_NEG_TTL, durable=True)`; each of the 4 call sites becomes `await _negcache()` |
| S1c | price_service.py:15204 | `set_cached(cache_key, data, _SHOPIFY_CATALOG_TTL)` (multi-MB `json.dumps` + upload) | `_fetch_shopify_catalog` | same | 0 on hit; 1 per fetched catalog on miss | `await run_redis_offloop(set_cached, cache_key, data, _SHOPIFY_CATALOG_TTL, durable=True)` |
| S2 | price_service.py:15800 and :15915 | `resolve_pdp_via_sitemap("bolo.bh", product_name)` / `("boutiqaat.com", product_name)`: a SYNC function (sitemap_discovery_service.py:855-903) doing 1 meta GET (:872) + up to `_MAX_BUCKET_PROBES`=3 bucket GETs (:885) + `_match_sitemap_slug` CPU | `fetch_bolo_price` :15783 / `fetch_boutiqaat_price` :15897 (async) | scs `_sitemap_fetch_coro` :211 <- `_timeout_none` lazy factory :6938 (prefetch) / :7069 (consume fallback) | per product: fragrances 1, makeup 2, skincare 2, haircare 1, supplements 1, else 0 sources; each 1-4 GETs -> 0-16 / compare | run the WHOLE sync function in the pool: `pdp_url = await run_redis_offloop(resolve_pdp_via_sitemap, "bolo.bh", product_name)` (same for boutiqaat). Keep the function-local `from ... import resolve_pdp_via_sitemap` (tests patch the source module attribute; the local import reads it at call time) |
| S3 | algolia_service.py:228, :234-235 (calls :251, :269, :278), :281 | `get_cached(cache_key)`; `set_cached(cache_key, {"_algolia_neg": True}, _CONFIG_CACHE_TTL)`; `set_cached(cache_key, cfg, _CONFIG_CACHE_TTL)` | `_harvest_config` :220 (async) | `fetch_algolia_price` :743 (async, `await` at :769) <- scs algolia prefetch gather (scs `_prefetched_direct["algolia"]`) | only harvest-config stores reach it (every store in `ALGOLIA_EXPLICIT_STORES` :88 returns at :766-767 first); at 7b224c5a that is goldenscent.com (catalog row, bahrain, fragrances/makeup/skincare/haircare) -> 2 GETs per beauty compare, + 1 SET per product on miss | identical pattern to S1: GET awaited non-durable; `_negcache` becomes async + durable; the cfg SET durable |
| S4a | structured_comparison_service.py:6586 and :6598 | `get_negative_cache(negative_cache_key(cache_key))`; on a stamped-sentinel hit `sitemap_domains_now_built(cold_domains)` (1 meta GET per stamped domain) | `StructuredComparisonService._get_price` :6458 (async) | `_fetch_product_data` -> `_get_price`, started at scs:4116-4126 right after parse | 2 GETs / compare (skipped on `price_nocache`), + 0-2 meta GETs | `neg = await run_redis_offloop(get_negative_cache, negative_cache_key(cache_key))` (the key expression is evaluated on the loop, as today); `if cold_domains and await run_redis_offloop(sitemap_domains_now_built, cold_domains):` |
| S4b | structured_comparison_service.py:8436 and :8513-8526 | `self._record_negative_price_cache(...)` (SYNC method :9127): `sitemap_unbuilt_domains(category)` meta GETs + `set_negative_cache` SET; the :8513 call also evaluates the argument `sitemap_discovery_is_cold(category)` (meta GETs when `ENABLE_SITEMAP_INDEX` is on) | `_get_price` (async) | same as S4a; Tier-3 / converted terminal | 0-2 SETs + 0-4 meta GETs / compare (estimate terminals only, i.e. exactly the failing compares) | wrap the WHOLE call, arguments included, in a zero-arg lambda: `await run_redis_offloop(lambda: self._record_negative_price_cache(cache_key, converted_fallback), durable=True)` and likewise for :8513 with its four keyword arguments unchanged inside the lambda. The method itself stays SYNC and unchanged (tests call it directly) |
| S6 | review_service.py:678 and :689 | `get_cached(cache_key)` (L1 read, skipped on nocache); `set_cached(cache_key, db_reviews, REVIEWS_CACHE_TTL)` (L2-hit promotion) | `get_reviews` :662 (async) | scs `_get_reviews` :8547 -> `_get_reviews_standalone`; started as a Phase-1 task at scs:5720-5725 under `asyncio.wait_for` | 2 GETs / compare (+ 1 SET per product on an L2 hit) | `cached = (await run_redis_offloop(get_cached, cache_key)) if not nocache else None`; `await run_redis_offloop(set_cached, cache_key, db_reviews, REVIEWS_CACHE_TTL, durable=True)` |

Total moved per cold compare: S1 18-36 large GETs (+ misses' SETs), S2 0-16, S3 0-2, S4a 2-4, S4b 0-6, S6 2. The S1 share is the measured dominant cost.

## 2. Sites OUT of scope (each with the reason)

- Breaker gates and recorders on the adapter path: `is_circuit_closed` at algolia_service.py:757, noon_service.py:486, unbxd_service.py:233; `record_success`/`record_failure` (algolia :316/:319/:361/:365/:371/:787, noon :175/:412/:415/:505/:508, unbxd :203/:206/:212). Not mechanical: `record_*` is a GET->modify->SET on the breaker blob (api_budget_service.py:588-624) and `is_circuit_closed` writes the half-open mirror (:563-579); threading the gate while the recorders stay on the loop is exactly the interleaving the wedge note at api_budget_service.py:567-579 analyses for the render providers only. A breaker change needs its own review. Cost: 1-3 small GETs per source.
- noon / unbxd have NO config cache (only the breaker calls above), so nothing else of "site 3" exists there.
- nasser 401 breaker `_nasser_breaker_tripped` price_service.py:16029-16038 (+ INCR/EXPIRE/DELETE :16041-16058): breaker class, same reason.
- Serper per-key exhausted GET/SET serper_service.py:127-156: zero calls with a single key (`_active_serper_key` :158-186 returns before any Redis read when `len(keys) <= 1`); with SERPER_API_KEYS >= 2 it sits inside the rotation loop shared by 7 call sites (:540, :646, :862, :975, :1088, :1120, :1165). Whether prod has >= 2 keys is UNVERIFIED (not probed). Follow-up unit if it does.
- review_service.py:722, :750, :764 (post-extraction L1 writes): :722 must stay inline. The F3/G2 comment at :712-717 requires the L1 write and the `fire_and_forget(save_reviews...)` L2 write to happen before the first cancellable await; a new await at :722 would let the 10 s reviews `wait_for` cancel between them and lose the L2 save. :750/:764 are post-consult, outside the burst; kept with :722 for one ordering rule. `fetch_retailer_quotes` :791 (:807/:869) has no caller in app/ at 7b224c5a.
- `_varhint_read_verdict_cache` / `_write` price_service.py:9054-9077: called from inside the sync candidate matcher, not mechanical.
- Tier-1.5 counters (cache_service.py:240-268), image credit, rating `record_usage`, Bright Data gate, model_router, render `record_*`: not catalog/config/negcache reads; mostly INCR/RMW; belong to a later sweep.
- Every site already dispatched by `ENABLE_ASYNC_REDIS_OFFLOAD` (scs `_cache_get_async`/`_cache_set_async`/`_cache_delete_async`/`_provider_gate_ok_async` scs:1093-1187, serper_service.py:36-47, review_service.py:23-32, usage/auth/home/feedback dispatchers): untouched, semantics unchanged.
- Supabase sites (ENABLE_SYNC_DB_OFFLOAD / ENABLE_SUPABASE_CLIENT_REUSE).
- Shrinking cached catalogs, an in-process catalog memo / single-flight (the same domain's catalog is GET twice per compare, once per product), TTL or key changes.
- CPU that stays on the loop: `_match_shopify_product` over a cached catalog (:15570, up to 250 products), `resp.json()` of a fresh catalog (:15188) on a miss. Neither is Redis I/O.

## 3. Helper contract (new leaf module `app/utils/redis_offloop.py`)

Placement: a NEW leaf module beside `app/utils/db_offload.py` and `app/utils/executor.py`, importing only stdlib (`asyncio`, `concurrent.futures`, `contextvars`, `functools`, `logging`, `os`, `threading`). `cache_service.py` is NOT edited:
(1) the design note at cache_service.py:666-668 (and scs:1098-1101) requires the dispatch to call the CALLER's module-level name so a test patching `price_service.get_cached`, `review_service.get_cached`, `algolia_service.get_cached` or `scs.get_negative_cache` still intercepts both branches. A wrapper inside cache_service would call `cache_service.get_cached` and bypass those patches (tests/test_shopify_discovery_l13.py:238-239 and :276-277 patch `ps.get_cached`/`ps.set_cached` with positional lambdas). The helper therefore takes the callable as its first argument, evaluated by the caller from its own namespace;
(2) cache_service is imported almost everywhere, a larger comm radius for no gain.

```python
def redis_offloop_enabled() -> bool:
    return os.getenv("ENABLE_PRICE_PATH_REDIS_OFFLOOP", "").strip().lower() in (
        "true", "1", "yes", "on",
    )

def redis_offloop_max_workers() -> int:
    # REDIS_OFFLOOP_MAX_WORKERS: int(value.strip()) clamped 1..32; unset, empty,
    # unparsable, '8.5', 'inf', 'nan' -> 16 (the price_parse_max_workers idiom,
    # price_service.py:4365-4375).

_REDIS_OFFLOOP_POOL = None          # built lazily under a threading.Lock, double-checked
_REDIS_OFFLOOP_POOL_LOCK = threading.Lock()

def _get_redis_offloop_pool() -> ThreadPoolExecutor:
    # ThreadPoolExecutor(max_workers=redis_offloop_max_workers(),
    #                    thread_name_prefix="redis-offloop")
    # logs once: "[REDIS-OFFLOOP] pool built workers=%d"

def redis_offloop_pool_stats() -> Optional[dict]:
    # None until built; else {"workers": pool._max_workers, "queued": pool._work_queue.qsize()}
    # in a try/except returning None on attribute drift. Pure read, no I/O.
    # Not wired into /health in this unit (main.py untouched).

async def run_redis_offloop(fn, *args, durable: bool = False):
    if not redis_offloop_enabled():
        return fn(*args)                       # OFF: inline, no await, no yield
    loop = asyncio.get_running_loop()
    ctx = contextvars.copy_context()
    fut = loop.run_in_executor(_get_redis_offloop_pool(),
                               functools.partial(ctx.run, fn, *args))
    if durable:
        fut.add_done_callback(_retrieve_quietly)   # cancelled() or exception(), never raises
        return await asyncio.shield(fut)
    return await fut
```

Rules:
- `fn` receives `*args` only, never keyword arguments (every in-scope shape is positional; S4b passes a zero-arg lambda).
- OFF branch: `fn(*args)` with no `await`, so `await run_redis_offloop(...)` runs to completion with no suspension. Same calls, same order, same args, same values, same TTLs, same thread. No pool is ever built while OFF.
- ON branch: ONE executor hop per call. No retries, no memo, no batching, no timeout added.
- Exceptions: whatever `fn` raises propagates unchanged (`run_in_executor` re-raises the original exception object in the awaiting coroutine). `get_cached` and `set_cached` are fail-open today (cache_service.py:173-198 catch every Exception in `_redis_get`/`_redis_set`; `set_cached` :650-656 also catches `json.dumps` errors). `get_cached` :639-647 catches only `JSONDecodeError` from `json.loads`, so a non-str payload (a `TypeError`) propagates in BOTH branches. `resolve_pdp_via_sitemap` catches per GET (sitemap_discovery_service.py:870-889); `_record_negative_price_cache` catches everything (scs:9204-9205). Parity is by construction; the tests pin it.
- `durable=True` (every WRITE: S1b, S1c, S3 sets, S4b, S6 :689). Once dispatched, the write runs even if the awaiting coroutine is cancelled (`asyncio.shield`). This matches OFF, where a reached inline SET cannot be interrupted. Without the shield, a cancel would also cancel a not-yet-started executor job and drop the write. `_retrieve_quietly` retrieves the inner future's result so asyncio never logs "Future exception was never retrieved".
- `durable=False` (every READ: S1a, S2, S3 GET, S4a, S6 :678). An outer cancel cancels a job still queued in the pool, so no wasted multi-MB GET. A job already running keeps its thread until the GET returns and the result is discarded.
- `contextvars`: `copy_context().run` gives the `asyncio.to_thread` semantics (copied context). Example: `price_service._resolved_category_ctx` :1455. None of the in-scope functions reads a ContextVar today (S2's `_match_sitemap_slug` reads env flags only), so this is parity insurance, pinned by one test.

### Executor decision: a dedicated pool, not `asyncio.to_thread`

`asyncio.to_thread` uses the loop default executor. In prod that is the named `qaren-worker` pool (executor.py:45-65), sized by ADAPTER_EXECUTOR_MAX_WORKERS=96 and shared with the adapter curl fan-out (about 30 blocking fetches of up to 9 s per BH_GCC compare, executor.py:14-22). A dedicated `redis-offloop` pool (default 16) is better here:
1. **Starvation isolation.** With ENABLE_UPSTASH_BOUNDED_TRANSPORT OFF (prod), the SDK client is `httpx.Client(timeout=None)` with `rest_retries=1` and a `time.sleep(3)` between attempts (upstash_redis 1.7.0 `http.py:54`, `:68-82`). A stalled Upstash would park every thread it reaches with no ceiling. On the shared pool, 36 catalog GETs could take 36 of the 96 adapter threads. On a dedicated pool, at most 16 park, and the adapter fan-out keeps all 96. This is the same reasoning as the `dns-resolve` pool (CLAUDE.md:414) and the `price-parse` pool (CLAUDE.md:417).
2. **Connection reuse.** The SDK client uses httpx DEFAULT_LIMITS: max_connections=100, max_keepalive_connections=20 (httpx 0.28.1 `_config.py:247`; the SDK passes no limits). With 16 concurrent workers or fewer, connections come from the 20-slot keepalive pool. Above 20, each extra concurrent call opens and later discards a TLS connection (~180 ms measured fresh-connection cost). The clamp ceiling of 32 is deliberate; raising past 20 is a measured decision, not a default.
3. **Demand fit.** 18-36 GETs per compare over 16 workers takes 2-3 waves. Under OFF they are fully serial and block the loop.
4. **Observability.** The thread names identify these calls in a stack dump, and `redis_offloop_pool_stats()` exposes the queue depth.

No `asyncio.Semaphore` sits in front of the pool (unlike price-parse). Writes must be submitted at once so `shield` can protect them. Reads queued in the executor are cancellable through `run_in_executor`'s future chaining. So a semaphore would add nothing but a second queue.

### Thread safety of the shared SDK client (verified against the installed source)

- `.venv-qaren/Lib/site-packages/upstash_redis` 1.7.0, `httpx` 0.28.1, `httpcore` 1.0.9.
- `httpx.Client` is safe to share across threads: the httpcore `ConnectionPool` guards its state with `_optional_thread_lock = ThreadLock()` (httpcore/_sync/connection_pool.py:12, :126). Each Upstash command is a stateless REST POST (`SyncHttpClient.execute`, http.py:56-95).
- Shared mutable state in the SDK: `Redis.execute` (client.py:137-147) writes `self._headers["Upstash-Sync-Token"]` on EVERY call (read_your_writes defaults True, client.py:42, :133-135) and passes the same dict to `httpx.post`. `_update_sync_token` (:129-131) is last-writer-wins.
  - (a) The FIRST command of the process ADDS the key, a dict size change. A concurrent thread iterating the dict (httpx `Headers.__init__`, `_models.py:154`) can then raise `RuntimeError: dictionary changed size during iteration`. This happens once per process at most. `_redis_get`/`_redis_set` catch it, so it degrades to one fail-open miss or one skipped SET.
  - (b) After that, only the VALUE changes, so there is no size change and no error. The token is a consistency hint, and a slightly older token only weakens read-your-writes for that call.
  - This is the same exposure `ENABLE_ASYNC_REDIS_OFFLOAD` already accepts (scs:1099-1101 docstring). Stated as a limit, no mitigation in this unit.
- The redis:// branch (cache_service.py:139-152, redis-py) is thread-safe by its connection pool. Prod is the REST branch.

### Composition with ENABLE_ASYNC_REDIS_OFFLOAD

The two flags gate DISJOINT call sites. No in-scope site is dispatched by `_redis_offload_enabled()` today, and the new helper never reads `ENABLE_ASYNC_REDIS_OFFLOAD`. So there is no double dispatch and no nesting: the helper is `async` and is only ever awaited on the loop, never from inside a worker thread. All four combinations are valid:
- ASYNC_REDIS ON + new OFF: the in-scope sites stay inline on the loop.
- new ON + ASYNC_REDIS OFF: the in-scope sites run in `redis-offloop` threads; the ASYNC_REDIS sites stay inline.
- both ON: each set uses its own executor (`qaren-worker` for ASYNC_REDIS, `redis-offloop` for this flag). Both share the ONE SDK client and its 20-keepalive connection pool, which is the only coupling.

### Ordering, idempotence, cancellation

- Ordering inside a coroutine is unchanged: every dispatch is awaited before the next statement. Examples:
  - S1: GET -> (miss) curl -> currency -> SET.
  - S4b at :8436: `_persist_genuine_price` -> negcache write -> `converted_fallback["_cached"] = False`. The stored value still lacks `_cached`, as today.
- Across compares, ordering is unchanged in kind: two compares writing the same `nogenuine:`/`shopify_catalog:` key are last-writer-wins today in loop order, and under ON in thread-completion order. Every in-scope write is a full-value `setex` overwrite, so idempotent. The two S4b sites are different terminals of one `_get_price` call (converted vs Tier-3), and at most one runs per resolution.
- Cancellation (ON):
  - An outer cancel during an awaited READ discards the result. A queued read never runs; a running one finishes in its thread.
  - An outer cancel during an awaited durable WRITE raises `CancelledError` in the caller while the SET still lands. That equals OFF, where the inline SET had already landed.
  - New ON-only consequence: the per-source `_timeout_none(..., _ADAPTER_TIMEOUT=10.0)` (scs:233) and the reviews `wait_for` can now fire WHILE a GET is queued or in flight. Under OFF they could only fire after the blocking call. A source that under OFF finished while freezing the worker can now be dropped as a TIMEOUT. This is a canary item (section 7).
  - A cancelled running thread is never interrupted. With BOUNDED_TRANSPORT OFF, a stalled Upstash keeps that pool thread parked with no ceiling. Pool threads are non-daemon, so a parked call can also delay process shutdown.
- S4b closure: the lambda reads `price`/`converted_fallback` and the flag locals in the worker thread while the coroutine is suspended at the shield. A mutation of the SAME dict by another task during that window could race `json.dumps`. Inspection found no such writer. GREEN must confirm by grep: every holder of the dict after `_persist_genuine_price` returns. A race would surface as `set_cached`'s caught "Cache set error" and a skipped sentinel, never as a raise. The OFF path stays a direct inline call.

## 4. Edits (exact)

- NEW `app/utils/redis_offloop.py`: section 3.
- `app/services/price_service.py`:
  - Add `from app.utils.redis_offloop import run_redis_offloop` beside the cache import at :33.
  - S1a/S1b/S1c in `_fetch_shopify_catalog` :15146-15205: `_negcache` becomes `async def`; its 4 call sites :15180/:15185/:15191/:15194 become `await _negcache()`.
  - S2 at :15800 and :15915.
  - Nothing else in this file changes.
- `app/services/algolia_service.py`: import; S3 in `_harvest_config` :220-282 (`_negcache` async; call sites :251/:269/:278 awaited).
- `app/services/structured_comparison_service.py`: import; S4a :6586 and :6598; S4b :8436 and :8513-8526.
- `app/services/review_service.py`: import; S6 :678 and :689 only.
- `CLAUDE.md`: the flag row in section 6 (orchestrator or GREEN; prose only).
- NO change to cache_service.py, sitemap_discovery_service.py, api_budget_service.py, main.py, executor.py, requirements*.

## 5. Flag reader (repo idiom)

`os.getenv("ENABLE_PRICE_PATH_REDIS_OFFLOOP", "").strip().lower() in ("true", "1", "yes", "on")`, the set used by `_redis_offload_enabled` (cache_service.py:669-671), `sync_db_offload_enabled` (db_offload.py:29-32) and `price_parse_offload_enabled` (price_service.py:4317-4319). It is read on every `run_redis_offloop` call, never cached, never at import.

## 6. CLAUDE.md flag row (add after the ENABLE_ASYNC_REDIS_OFFLOAD row, CLAUDE.md:384)

- `ENABLE_PRICE_PATH_REDIS_OFFLOOP` (default OFF, S77 REDIS-OFFLOOP, read PER CALL) + knob `REDIS_OFFLOOP_MAX_WORKERS` (default 16, clamped 1..32, unparsable or non-finite -> 16, read ONCE when the pool is built, so a change needs a restart).
  - **Problem (measured 2026-10-11):** the cached Shopify catalogs (`shopify_catalog:<domain>`, 0.3-2.4 MB each, a GET of the largest 0.9-2.2 s) were read synchronously on the event loop by `price_service._fetch_shopify_catalog`, 18-36 times per cold compare, with no flag covering them. One cold compare froze the loop 6.5-16.2 s.
  - **Effect ON:** `app/utils/redis_offloop.run_redis_offloop(fn, *args, durable=...)` runs these calls as one job each on a DEDICATED `redis-offloop` `ThreadPoolExecutor`, in a copied contextvars context: the Shopify catalog GET plus its negcache and catalog SETs, the bolo/boutiqaat `resolve_pdp_via_sitemap` lookup (meta + bucket GETs + slug match), the Algolia harvest-config GET/SETs, the `nogenuine:` sentinel read (+ `sitemap_domains_now_built`) and both sentinel writes in `_get_price`, and the reviews L1 read + L2-promotion write. Writes are `asyncio.shield`ed, so a dispatched SET always lands even when the caller is cancelled, as it does inline. Reads queued behind a full pool are dropped on cancel.
  - **Why not the shared `qaren-worker` pool:** with ENABLE_UPSTASH_BOUNDED_TRANSPORT OFF the SDK's `httpx.Client(timeout=None)` can park a thread with no ceiling. The dedicated pool bounds that to 16 threads and never touches the adapter fan-out's 96. 16 also stays under the SDK client's 20 keepalive connections.
  - **Flag OFF:** the helper's branch has no `await`: the same calls, order, args, keys, values and TTLs, on the loop thread, byte-identical, and no pool is built.
  - **Composes with ENABLE_ASYNC_REDIS_OFFLOAD:** disjoint call sites, separate executors, no double dispatch.
  - **Left on the loop (stated limits):** the adapter breaker gates/recorders (Algolia/noon/unbxd/nasser, a RMW breaker review is owed); the Serper exhausted-key read (inert with one key); `review_service` post-extraction writes (the F3 ordering); `_match_shopify_product` and fresh-catalog `resp.json()` CPU; the GIL-held `json.loads`/base64 decode of a multi-MB payload (about 10-20 ms each, residual jitter); the duplicate per-product GET of the same catalog (no memo).
  - **Canary-watch:**
    - `/health loop_lag_max_60s_ms` against the session baseline (b0: 16190 ms).
    - Warm-up READY count.
    - Per-category price-source count: a 10 s adapter timeout can now fire while a catalog GET waits in the pool.
    - The `Redis GET error` / `Cache set error` rate.
    - `[REDIS-OFFLOOP] pool built workers=16` once per process.
    - Railway drain time (non-daemon threads).
  - **Rollback:** unset the variable. The next call is inline and the pool idles.

## 7. Activation and canary plan

1. Merge with the flag unset. The deploy itself is a no-op for behaviour; ENABLE_OFFLOOP_DNS_RESOLVE and ENABLE_PRICE_PARSE_OFFLOAD stay as set on web (2026-10-11 19:16 / 19:24).
2. Run a pre-flip canary on the new deploy with the flag OFF (`scripts/canary_step.sh`, 3 cold app-shaped pairs, /health polled ~1.5 s) = `b_pre`. This captures the post-DNS/PARSE state and deploy noise.
3. The orchestrator sets `ENABLE_PRICE_PATH_REDIS_OFFLOOP=true` on web. It is read per call, so no restart is needed.
4. Re-run the same canary = `c1`. Use at least one pair from a catalog-heavy category (fragrances / makeup / other).
5. PASS when ALL of the following hold, judged RELATIVE to `b_pre` and b0 (b0: max lag 16190 ms, /health misses 14, 1/3 ready):
   - (a) Max `loop_lag_max_60s_ms` falls substantially. Target <= 50% of `b_pre`, and below b0 by >= 8000 ms. Expected inference, UNVERIFIED: the 18-36 multi-MB GETs leave the loop; the residual is breakers, the ASYNC_REDIS-class sites (still OFF), Supabase and client construction.
   - (b) /health misses <= `b_pre`.
   - (c) READY count >= `b_pre` (and >= b0's 1/3).
   - (d) No category loses price sources against `b_pre`: compare the per-source result/timeout counts in the logs, in particular shopify_gcc and sitemap `_timeout_none` TIMEOUT lines.
   - (e) `Redis GET error` / `Cache set error` / `Future exception was never retrieved` lines are not above `b_pre`.
   - (f) `[REDIS-OFFLOOP] pool built workers=16` appears exactly once.
6. On any regression in (b)-(e): unset the variable (next call inline), record it, stop.
7. The flip is subject to the owner's 19:10 approval scope. That approval covered flags "the verified diagnosis marks safe". This is a new code flag, so confirm it is in scope (open question).
8. Pool-size changes (`REDIS_OFFLOOP_MAX_WORKERS`) need a restart and their own window.

## 8. TEST LIST for the RED agent

File: `tests/test_s77_redis_offloop.py` (one file, free tier: no network, no credentials, never `LIVE=1`).

Fixtures:
- An autouse fixture deletes `ENABLE_PRICE_PATH_REDIS_OFFLOOP`, `REDIS_OFFLOOP_MAX_WORKERS` and `ENABLE_ASYNC_REDIS_OFFLOAD`.
- It drops any `redis-offloop` pool by TYPE and thread-name prefix (copy `_reset_parse_pools`, tests/test_retro_w0_4.py:194-210), before and after each test.
- Copy the heartbeat / gap-meter helper from tests/test_price_parse_offload.py:147-165 (and the gap meter in test_retro_w0_4.py).
- Every fake records `(name, args, kwargs, threading.current_thread())`.
- `ps.ENABLE_PAGE_SCRAPE` is monkeypatched True where a site needs it.
- curl_cffi is never reached: patch `curl_cffi.requests.get` (copy tests/test_shopify_discovery_l13.py:250-260) or use cache hits.

Async tests use `@pytest.mark.asyncio`. "Main" means `threading.main_thread()`, the loop thread under pytest-asyncio; the assertion style is that of tests/test_m18_offload_sweep_residual.py:1-12.

### A. Flag reader and knob (pure)
1. `test_flag_reader_rows` (parametrised): the flag is True for `true`, `TRUE`, ` True `, `1`, `yes`, `on`, `ON`. It is False for unset, `""`, `"  "`, `false`, `0`, `no`, `off`, `garbage`, `enabled`. This pins the exact truthy set and the strip/lower.
2. `test_flag_read_per_call`: flip the env between two `run_redis_offloop` calls in one test; the first call runs on main and the second in a `redis-offloop` thread (and back).
3. `test_max_workers_rows` (parametrised): unset -> 16, `8` -> 8, ` 8 ` -> 8, `0` -> 1, `-3` -> 1, `999` -> 32, `abc` -> 16, `8.5` -> 16, `inf` -> 16, `nan` -> 16.
4. `test_pool_never_built_when_off`: N OFF calls leave `redis_offloop._REDIS_OFFLOOP_POOL is None` and `redis_offloop_pool_stats() is None`.
5. `test_pool_built_once_named_and_sized`: two ON calls build exactly one pool. Its `_thread_name_prefix` is `redis-offloop`, `_max_workers` is 16, and the log line `[REDIS-OFFLOOP] pool built workers=16` is emitted once (caplog).
6. `test_pool_is_not_the_default_executor`: under ON with a default executor installed via `app.utils.executor.install_default_executor`, the fake's thread name starts with `redis-offloop`, not `qaren-worker`.

### B. Helper semantics
7. `test_off_inline_no_yield`: OFF, `coro = run_redis_offloop(fake, 1, 2)`; `coro.send(None)` raises `StopIteration` with the fake's value. This pins no suspension point. ON: the first `send(None)` does NOT raise StopIteration (it suspends); close the coroutine.
8. `test_args_positional_no_kwargs`: in both branches the fake receives exactly `(1, 2)` and `{}`.
9. `test_exception_identity_both_branches`: the fake raises `RuntimeError("boom")`. In both branches the same exception type and message propagate to the awaiter. ON: the exception object raised is the one the fake created.
10. `test_contextvars_copied_on`: set a test ContextVar in the caller; under ON the fake reads the same value in its thread; a `.set()` inside the fake does not leak back to the caller.
11. `test_durable_write_lands_after_cancel`:
    - ON with a fake `set` that sleeps 0.3 s and then records completion; start `run_redis_offloop(fake, durable=True)` in a task and cancel it after 0.05 s.
    - The task raises `CancelledError`; within 1 s the fake has completed exactly once.
    - Pin: no "Future exception was never retrieved" in caplog when the fake raises after the cancel (repeat with a raising fake and `gc.collect()`).
12. `test_queued_read_dropped_on_cancel`:
    - ON with `REDIS_OFFLOOP_MAX_WORKERS=1` set before the first ON call (fresh pool). Job 1 holds the only worker on a `threading.Event`.
    - Job 2 (non-durable read) is awaited in a task, then cancelled; set the event; wait for job 1.
    - Job 2's fake was NEVER called.
13. `test_composes_with_async_redis_offload` (parametrised over the 4 flag combinations), on S1a via `_fetch_shopify_catalog` hit:
    - (new OFF, ASYNC_REDIS ON) -> the fake runs on main.
    - (new ON, either) -> the fake runs once, in a `redis-offloop` thread (not `qaren-worker`, not nested).
    - (both OFF) -> main.

### C. Thread placement per site, ON vs OFF (each parametrised `flag in (False, True)`)
Assert: the fake ran on main when OFF and in a `redis-offloop` thread when ON; the call count is identical in both branches.
14. `test_s1a_catalog_get_placement`: `ps.get_cached` fake returns a catalog dict; `await ps._fetch_shopify_catalog("store.example")`.
15. `test_s1b_negcache_set_placement`: `ps.get_cached` -> None, curl fake -> HTTP 404. The `ps.set_cached` fake records thread and args. Repeat for each of the four failure branches (exception, non-200, non-JSON, no `products`), a parametrised row each.
16. `test_s1c_catalog_set_placement`: miss, then curl 200 with `{"products": [...]}`, `_fetch_shopify_currency` patched to `AsyncMock(return_value="BHD")`. Check the set's thread and args.
17. `test_s2_sitemap_resolve_placement` (parametrised bolo / boutiqaat): patch `app.services.sitemap_discovery_service.resolve_pdp_via_sitemap` (the module attribute, as tests/test_bolo_adapter.py:199-206 does) with a fake that records its thread and returns None. Call `ps.fetch_bolo_price(...)` / `ps.fetch_boutiqaat_price(...)`.
18. `test_s2_inner_gets_run_in_same_worker`: patch `sitemap_discovery_service.get_cached` (meta present, one bucket). Under ON, the meta and bucket GETs all run in ONE `redis-offloop` thread (the whole function hops once); under OFF, all on main.
19. `test_s3_algolia_config_get_placement` and `test_s3_algolia_config_sets_placement`: the same pattern on `algolia_service._harvest_config` with `algolia_service.get_cached`/`set_cached` fakes. Sets: neg on landing HTTP 404, cfg on success (patch `extract_algolia_config`).
20. `test_s4a_negcache_read_placement`: drive `svc._get_price(...)` to the negcache read, reusing the `_get_price` harness of tests/test_negcache_outage_and_converted_fallback.py (around :180-250). The `scs.get_negative_cache` fake returns a sentinel. Also a row whose sentinel carries `_sitemap_cold_domains`, with a `scs.sitemap_domains_now_built` fake recording its thread.
21. `test_s4b_negcache_write_placement` (parametrised converted terminal :8436 / Tier-3 terminal :8513), same harness. The `scs.set_negative_cache` fake and a `scs.sitemap_discovery_is_cold` fake both record threads: under ON both run in the same `redis-offloop` thread, because the argument is evaluated inside the lambda.
22. `test_s6_reviews_l1_read_placement` and `test_s6_reviews_l2_promotion_set_placement`:
    - Call `review_service.get_reviews(...)` with the `review_service.get_cached` fake hitting (read).
    - Then with the fake missing and `app.services.product_data_service.get_cached_reviews` patched to `AsyncMock(return_value={...})` (promotion set).
23. `test_s6_post_extraction_write_stays_inline_on`: with the flag ON, drive `get_reviews` past extraction (patch `search_web`, `extract_reviews`, `fire_and_forget`, `consult_review_sources`, `consult_youtube_source`). The `set_cached` call at :722 runs on main. This pins the F3 exclusion.

### D. Heartbeat (the measured symptom)
24. `test_heartbeat_single_slow_catalog_get`: the `ps.get_cached` fake does `time.sleep(0.4)` and returns a catalog. Run `_fetch_shopify_catalog` alongside a 20 ms heartbeat. ON: ticks >= 10 during the call. OFF: ticks <= 1. Both values are printed in the assertion message.
25. `test_heartbeat_fanout_18_catalog_gets`: 18 concurrent `_fetch_shopify_catalog` calls (distinct domains), fake sleep 0.1 s each. OFF: the max heartbeat gap is >= 1.5 s (serial on the loop). ON: the max gap is < 0.3 s, and the wall time is < 0.6 s (two waves of 16).
26. `test_heartbeat_sitemap_resolve`: the `resolve_pdp_via_sitemap` fake sleeps 0.3 s. ON: ticks >= 8. OFF: ticks <= 1.

### E. ON == OFF result parity (each site: hit / negative / miss)
Run the same scenario twice (OFF, ON) with identical fakes; the return values AND the recorded call lists `[(name, args, kwargs)]` are equal.
27. `test_parity_s1`: hit (catalog dict -> same dict), negative (sentinel -> None, no set), miss (404 -> None plus one neg set with `("shopify_catalog:store.example", {"_shopify_neg": True}, 1800)`), miss-success (-> the data with `_store_currency`, plus one set with TTL 21600).
28. `test_parity_s2`: index cold (meta None -> None), meta present + bucket match (-> the URL, same GET key sequence), meta present + no match (-> None after exactly 3 bucket GETs).
29. `test_parity_s3`: config hit, neg sentinel, miss -> neg set, miss -> cfg set.
30. `test_parity_s4a`: sentinel absent (cascade continues), sentinel served (same served dict, `_cache_source == "negative"`, marker popped), sentinel with cold domains now built (invalidated, falls through).
31. `test_parity_s4b`: the captured `(key, value, ttl)` of `set_negative_cache` is identical ON vs OFF for: the 30-day default, a `transient_discovery` 24 h cap, and a stamped `_sitemap_cold_domains`.
32. `test_parity_s6`: L1 hit (`_cached` True), L2 promotion (same set args, `_cache_source == "db"`), nocache (no GET at all in either branch).

### F. Flag-OFF call-shape pins (base identity)
33. `test_off_call_shapes_exact` (parametrised over S1a/S1b/S1c/S2/S3/S4a/S4b/S6): with the flag unset, the recorded call list (name, positional args, kwargs == {}, thread is main) equals a literal expected list written in the test from 7b224c5a's code. Same order, keys, values, TTLs: 21600 and 1800 for Shopify, 86400 for the Algolia config, REVIEWS_CACHE_TTL for reviews.
34. `test_off_no_new_suspension_on_hit_paths`: OFF, the coroutines of `_fetch_shopify_catalog` (hit and negative), `_harvest_config` (hit), `fetch_bolo_price` (resolve -> None) and `get_reviews` (L1 hit) each complete on the FIRST `send(None)` (StopIteration). These paths have no await today and must still have none. ON: the same coroutines suspend on the first send.
35. `test_existing_positional_lambda_patches_still_work`: patch `ps.get_cached = lambda k: store.get(k)` and `ps.set_cached = lambda k, v, ttl=0: store.__setitem__(k, v)` (the tests/test_shopify_discovery_l13.py:238-239 shape). The M2 negcache round-trip returns None twice, and curl is called once, under BOTH flag values.

### G. Exception parity
36. `test_exception_parity_s1_get`: the `ps.get_cached` fake raises `TypeError` (the non-str-payload case `get_cached` does not catch). `_fetch_shopify_catalog` raises `TypeError` under both flags.
37. `test_exception_parity_s2`: the inner `sitemap_discovery_service.get_cached` raises. `fetch_bolo_price` returns None under both (the in-function fail-open).
38. `test_exception_parity_set_failopen`: `cache_service.redis_client` is patched to an object whose `setex`/`get` raise `ConnectionError`. Using the REAL `get_cached`/`set_cached`, S1 miss returns None and the neg set returns quietly under both flags; caplog shows the same `Redis SET error` count in both.
39. `test_exception_parity_s4b`: the `scs.set_negative_cache` fake raises. `_get_price` returns the same price under both flags (`_record_negative_price_cache` swallows).

### H. Source pins (cheap AST, same style as tests/test_m18_offload_sweep_residual.py:345-349)
40. `test_source_every_in_scope_site_routes_through_helper`: AST over the five touched app files.
    - Inside `_fetch_shopify_catalog`, `_harvest_config`, `fetch_bolo_price`, `fetch_boutiqaat_price`, `get_reviews` (only the :678/:689 sites) and `StructuredComparisonService._get_price` (the four sites), every call to `get_cached`/`set_cached`/`get_negative_cache`/`sitemap_domains_now_built`/`resolve_pdp_via_sitemap`/`_record_negative_price_cache` is an argument of (or inside a lambda passed to) `run_redis_offloop`. Exception: get_reviews' post-extraction `set_cached` sites, which must be direct calls (count 3).
    - Every write site passes `durable=True`, and no read site does.
41. `test_redis_offloop_module_is_a_leaf`: `app/utils/redis_offloop.py` imports no `app.*` module (AST).

Expected RED state at base: every test that imports `app.utils.redis_offloop` fails on ImportError (A, B, C-ON, D-ON, H). The OFF rows of C/E/F/G pass at base only if written against today's code. RED must record which node IDs are expected-pass at base, so GREEN cannot weaken them.

## 9. Gates for GREEN / the adversary

- `tests/test_s77_redis_offloop.py` all green under flag unset AND with `ENABLE_PRICE_PATH_REDIS_OFFLOOP=true` exported to the runner (the tests set the flag themselves; the exported run proves no leak), bound 600.
- Comm set at base 7b224c5a and HEAD, flag unset, plus HEAD with the flag exported true. `branch-only-NEW == []`. Chunks of at most 25 files, bound 1200 each. Recipe (run in the worktree, Git Bash):

```
A=$(grep -rlE "price_service|structured_comparison_service|sitemap_discovery_service|algolia_service|review_service|redis_offloop" tests --include='test_*.py' | sort -u)
B=$(grep -rlE "read_text|read_bytes|ast\.parse|\.glob\(|rglob|os\.walk" tests --include='test_*.py' | xargs grep -lE "\"app\"|'app'|app/" | sort -u)
C="tests/test_model_config.py tests/test_model_config_enforced.py tests/test_prompt_fence.py tests/test_prompt_truth.py tests/test_hermeticity_pins.py tests/test_retro_w0_4.py tests/test_retro_w0_4_efg.py tests/test_m18_offload_sweep_residual.py tests/test_async_redis_offload.py tests/test_m13_34_adapter_timeouts.py tests/test_s75_fanout_starve.py tests/test_secret_scan_static.py tests/test_s77_redis_offloop.py"
printf "%s\n" $A $B $C | sort -u      # 356 files at 7b224c5a before the new test file
```
  - Split out `tests/test_precommit_hook*.py` into their own runner call (bound 1200, `-k` subsets).
  - The set is about half the suite. Running the full free-tier suite in CI order at base and head (bound 1800 per chunk) is an acceptable substitute if cheaper to orchestrate.
- Corpus byte-identity: price_service is on the extraction-path list (CLAUDE.md:382), so `scripts/verify_flag_byte_identity.py --proof-root C:/Users/SynAckITPC/Documents/AI/sc-scraper-proof/_proof --flags ENABLE_PRICE_PATH_REDIS_OFFLOOP` must print the base OVERALL sha at HEAD OFF. `--flags-on ENABLE_PRICE_PATH_REDIS_OFFLOOP --compare <off results>` must show 0 differing records. The corpus does not reach the edited functions, so this is a no-move confirmation.
- Hygiene:
  - ruff `E9,F63,F7,F82` and py_compile on the 5 app files + the test.
  - `git diff --stat` shows no whole-file CRLF churn.
  - The test file is pure ASCII (count bytes > 127 == 0).
  - No credential-shaped literal.
- Mutation probes for the adversary (byte-copy, restore, sha-verify):
  - (m1) drop `durable=True` at S1c -> test 11/40 red;
  - (m2) make the OFF branch `await asyncio.sleep(0)` -> tests 7/34 red;
  - (m3) swap the pool for `asyncio.to_thread` -> tests 5/6/13 red;
  - (m4) evaluate `sitemap_discovery_is_cold` outside the lambda -> test 21 red;
  - (m5) move review_service :722 through the helper -> tests 23/40 red;
  - (m6) read the flag once at import -> test 2 red.

## 10. Stated limits

1. Loop residual: the breaker gates/recorders, nasser breaker, Serper exhausted-key read (multi-key only), tier-15 counters, image credit, rating/BD/model_router Upstash calls and every ENABLE_ASYNC_REDIS_OFFLOAD-class site stay on the loop while those flags are OFF. So do Supabase (other flags) and per-call `httpx.AsyncClient` construction. The canary will not reach the absolute `loop_lag < 1000 ms` bar (READINESS_BACKEND.md:199); judge it relatively.
2. The GIL: `json.loads` and the SDK base64 decode of a 2.4 MB payload run in the worker while holding the GIL (about 4 ms/MB measured for json.loads). Loop jitter of roughly 10-20 ms per large GET remains; 16 concurrent large GETs can still produce a visible lag spike, far below today's serial stall.
3. CPU kept on the loop: `_match_shopify_product` per cached catalog (5-30 ms each, UNVERIFIED) and `resp.json()` of a fresh catalog on a miss.
4. Bandwidth: 18-36 multi-MB GETs per compare still transfer about 10-25 MB from Upstash; going off-loop does not make them cheaper. The duplicate per-product GET of the same catalog and the catalog sizes are the real cost levers (out of scope: memo / single-flight, slimmer catalogs).
5. Capture risk ON: adapter `_timeout_none` (10 s) and race timers can now expire while a GET waits in the 16-wide pool. A catalog that under OFF arrived (while freezing everything) can be dropped as TIMEOUT. Canary item (d).
6. Stalls: with ENABLE_UPSTASH_BOUNDED_TRANSPORT OFF a stalled Upstash parks pool threads without a ceiling. Up to 16 park, later reads queue behind them, and shutdown can be delayed (non-daemon threads). It is contained to this pool; under OFF the same stall freezes the whole worker. BOUNDED_TRANSPORT (restart) is the real fix and stays the documented last W0 step.
7. SDK header sharing (section 3): a once-per-process first-command race degrades to one fail-open miss; the sync token is last-writer-wins.
8. No /health field for the new pool in this unit (main.py untouched); `redis_offloop_pool_stats()` exists for a follow-up wiring.
