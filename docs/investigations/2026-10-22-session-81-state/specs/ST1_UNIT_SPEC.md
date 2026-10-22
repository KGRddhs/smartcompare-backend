# ST1 unit spec (measured): LOOP-STALL, the usage reads and the reviews L1 calls off the event loop

- Unit: ST1 LOOP-STALL (PLAN_S81 M1, lane A; backend, one PR, dark flag `ENABLE_USAGE_PATH_OFFLOOP`). Worktree `C:\Users\SynAckITPC\Documents\AI\sc-s81-st1` (detached), branch to cut `feature/s81-loop-stall`, base `95cf6f864b4e70980ca191daa064c0118e223c13` (`git rev-parse HEAD` = base; `git status --short` empty at 22:10, after the probes at 22:36 and after this file, which is gitignored by `.gitignore:72 .qa-*/`).
- Evidence: PLAN_S81 M1 unit text (ST1) and the VERIFY correction "KB ingest and KB-first serve require `ENABLE_SYNC_DB_OFFLOAD` (with offload OFF every Supabase call blocks the single loop)"; the session-81 digest `runs/research/R9.json` and the session-80 `runs/research/prod_evidence.json` findings 8/9 (simple routes 2.6-8.4 s, `/health` p95 8.4 s, `usage_status` p50 4.16 s n=sampled, Upstash spans p50 289 ms / p95 1,537 ms, trace 5915a2b6: `usage_status` 4,266 ms with child http spans under 0.8 s = loop wait, not I/O); the speed-and-UX panel plan's ST1 text (`runs/panel/plan_speed-and-UX-first_fast_compa.json`); S77 rulings RO16/RO17 (`2026-10-11-session-77-state/specs/RULINGS_S77_OFFLOOP_FIX1.md`); the contract freeze (PLAN_S80 section 0, `runs/research/contract_freeze.json`); probes of this spec in `<scratchpad>/ST1/` (`test_probe_st1_base.py`, `probe_out.jsonl`, `probe_table.txt`, `comm_set.py`, `comm_set_full.txt`, every `base_*.log`).
- Correction to the brief's evidence pointer: `runs/research/A9.json` (session 81) is the compare-latency digest; it contains neither the 8.4 s `/health` figure nor the names `run_db` / `redis_offloop` (grep, 0 hits for both names; its only usage line is finding 1, "the paid-route auth guard, then get_user_preferences, then consume_comparison_credit (Supabase/Redis on the loop while ENABLE_SYNC_DB_OFFLOAD is OFF)"). The stall figures come from R9 + prod_evidence; the helper names come from the panel plan. Both names are VERIFIED below at base.
- Sister units and contracts: S81-09 DEVICE-QUOTA-RIYADH owns `consume_comparison_credit`, `_refund_credit_sync`, the quota keys and the date-key helper (ST1 changes none of them; pinned by digest, R25); S81-17 KB-INGEST needs `ENABLE_SYNC_DB_OFFLOAD` canaried ON (ST1 does not satisfy that precondition and does not claim to); S77 REDIS-OFFLOOP owns the `redis-offloop` pool that ST1 shares; D03 (sc-s81-d03, in flight) edits `review_service.clean_review_citations` and `build_retailer_quotes_from_reviews`: ST1 edits only the import block and `get_reviews` of that file = a known textual rebase (section 3); B4 (sc-s80-b4) touches no app file of this unit (its fix-round-3 comm set is built on `url_extraction_service` / `url_routes`, B4_FIX3_REPORT.md:109); B4, D03 and ST1 each add a CLAUDE.md flag row after the SESSION 80 rows (:476-477 at base), a second known textual rebase, resolved by keeping every row. MS1 SPEED-BASELINE comes before any latency claim.
- Personal-data rule: no real name, email, phone, device id or account id anywhere in this unit; every id in tests is synthetic (`u-synthetic-1`, built at run time where a shape matters); no credential name is read by the new code.
- Measurement location: `<scratchpad>` = `C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/fd8b3d1b-a491-48e3-953f-ca3a804fd9ca/scratchpad`. Every line number below is at base 95cf6f86 (worktree file == `git show HEAD:` file); resolve by symbol if it moves. `us` = `app/services/usage_service.py`, `rs` = `app/services/review_service.py`, `ro` = `app/utils/redis_offloop.py`, `dbo` = `app/utils/db_offload.py`.

## 0. What the unit does (one paragraph)

Behind `ENABLE_USAGE_PATH_OFFLOOP` (default OFF, read per call): `get_usage_status` (the `/api/v1/usage/status` handler body, called on every Home and Paywall mount by build 3) and `check_usage_allowed` run their two Supabase reads (users tier row incl. the lazy referral-bonus reset UPDATE, and the active referral_redemptions sum) as thread jobs on the loop's default executor and their two Upstash GETs (daily, monthly counters) as jobs on the shared `redis-offloop` pool, all four in ONE `asyncio.gather`, then compute the exact base response from the four values; `review_service.get_reviews` runs its L1 read and its three post-extraction L1 writes on the `redis-offloop` pool (writes durable and awaited, the L2 save scheduled before the first awaited write). The offload is independent of `ENABLE_SYNC_DB_OFFLOAD` and `ENABLE_PRICE_PATH_REDIS_OFFLOOP` (two new flag-free dispatch helpers in the existing leaf modules), so ST1's canary reads one flag. The L2-promotion write stays inline (RO17). Nothing else moves: `consume_comparison_credit`, `_refund_credit_sync`, every quota key, `/usage/status` and `/health` bodies are byte-identical in both flag states (no new key, no new code). Flag OFF: the base source runs unchanged below a one-line flag check.

## 1. Base state (measured at 95cf6f86)

### 1.1 The route and every caller

| what | where | measured fact |
|---|---|---|
| route | `app/api/usage_routes.py:9-15` | `@router.get("/status")`, `Depends(get_current_user)` (JWT verify: revocation GET + Supabase `auth.get_user`, both offloaded only under `ENABLE_ASYNC_REDIS_OFFLOAD` / `ENABLE_SYNC_DB_OFFLOAD`), then `return await get_usage_status(user_id=..., access_token=...)`. No rate-limit decorator. |
| `get_usage_status` callers | grep `app/ scripts/` | ONE: `usage_routes.py:12`. |
| `check_usage_allowed` callers | grep `app/ scripts/` | ZERO in `app/` and `scripts/` (the request path calls `consume_comparison_credit` at `text_routes.py:619, :836, :1023`, `url_routes.py:77`, `image_routes.py:321`; anonymous `check_anon_usage_allowed` at `text_routes.py:1407`, `image_routes.py:227`). Tests call it: `test_usage_tiers.py`, `test_usage_referral_bonus.py`, `test_usage_device_inheritance.py`, `test_referral_expiry.py`, `test_supabase_client_reuse.py`, `test_m13_37_freemium_atomic_consume.py`. |
| POST `/text/compare` order | `text_routes.py:577-638` | `dependencies=[Depends(require_paid_route_user)]` :577 -> `@limiter.limit("10/minute")` :578 -> `get_user_preferences` :604 -> `consume_comparison_credit` :619 -> `service.compare_from_text` :638 (the brief's :578/:579 are :577/:578 at base). ST1 changes nothing on this path. |
| client reads | `contract_freeze.json` finding "Non-compare endpoints read by build 3" | `useComparisonCounter.ts:178-183,225-246` reads `tier`, `used.lifetime`, `limits.lifetime_free`, `remaining.daily`, `remaining.monthly`, `remaining.lifetime_free`; `PaywallScreen.tsx:37-71` reads `remaining.*`, `used.daily/monthly`, `limits.daily/monthly`; an error returns null and the gate falls back to `used < 3`. `/health`: only `.status` is read (`api.ts:501`). |

### 1.2 The two functions (exact base order, `us`)

| function | lines | blocking ops in order (all on the loop thread at base with every flag OFF) |
|---|---|---|
| `get_usage_status(user_id, access_token)` | :712-758 | `_get_user_tier_info` :719 (= `get_admin_supabase_client()` :526, `run_db(users select ... .single().execute())` :527-530, `run_db(_maybe_reset_referral_bonus(...))` :537, which issues the users UPDATE :573-578 only when `referral_bonus_reset_at` is past); `_get_active_referral_bonus` :722 (`run_db(referral_redemptions select ... .execute())` :601-608); `_get_redis_count(_daily_key)` :726; `_get_redis_count(_monthly_key)` :727; pure compute :720-724, :735-758 (lifetime-free display rule :735-738, :754-756). |
| `check_usage_allowed(user_id, access_token)` | :618-682 | `_get_user_tier_info` :629; `_get_active_referral_bonus` :634; if `tier == "free" and lifetime_used < 3` return at :639-649 with NO Redis read; else `_get_redis_count` daily :652, monthly :653; compute :655-682. |
| helpers | `_get_user_tier_info` :519-544, `_maybe_reset_referral_bonus` :547-585, `_get_active_referral_bonus` :588-615, `_get_redis_count` :177-184, `_daily_key` :152-154, `_monthly_key` :157-159 | `_get_user_tier_info` falls back to `{"subscription_tier": "free", "lifetime_comparisons_used": 0, "referral_bonus_comparisons_this_month": 0}` on any exception and logs `logger.error(f"Failed to get user tier info: {e}")` (exception text, base); `_get_active_referral_bonus` returns 0 and logs a WARNING with `exc` text; `_get_redis_count` returns 0 on `redis_client is None` or any exception. |
| shared with consume | `consume_comparison_credit` :331-430 | gathers the SAME two async helpers (:350-352), then `_atomic_consume_async` / `_bump_counters_async` / `_get_redis_count_async` (ENABLE_ASYNC_REDIS_OFFLOAD dispatches :292-311). Out of scope; S81-09 owns it. |
| module imports | :7-16 | `asyncio`, `logging`, `os`, `re`, `datetime/timedelta/timezone`, `Optional`; `redis_client, _redis_offload_enabled` from `cache_service`; `get_admin_supabase_client` from `database_service`; `run_db` from `app.utils.db_offload`. No import of `app.utils.redis_offloop` today. |

### 1.3 The two dispatch helpers the brief names (VERIFIED) and the pools

| helper | where | gate at base | effect |
|---|---|---|---|
| `run_db(call)` | `dbo:35-40` | `sync_db_offload_enabled()` `dbo:29-32` = `os.getenv("ENABLE_SYNC_DB_OFFLOAD", "").strip().lower() in ("true","1","yes","on")`, per call | ON: `await asyncio.to_thread(call)` (the loop's default executor); OFF: `return call()` inline, no suspension. So "through run_db" alone moves nothing while `ENABLE_SYNC_DB_OFFLOAD` is OFF, and the usage reads ALREADY go through `run_db` at base (:527, :537, :601). |
| `run_redis_offloop(fn, *args, durable=False)` | `ro:98-111` | `redis_offloop_enabled()` `ro:45-48` = `ENABLE_PRICE_PATH_REDIS_OFFLOOP`, same idiom, per call | ON: one job on the lazily built `redis-offloop` pool (`_get_redis_offloop_pool` `ro:64-77`, `REDIS_OFFLOOP_MAX_WORKERS` default 16 clamp 1..32 read once at build, INFO `[REDIS-OFFLOOP] pool built workers=%d`), copied contextvars, `durable=True` = `add_done_callback(_retrieve_quietly)` + `asyncio.shield`; OFF: `fn(*args)` inline, no pool. Leaf module, stdlib imports only (pinned, `test_s77_redis_offloop.py:2072-2085`). |
| `_redis_offload_enabled()` | `cache_service.py:659-671` | `ENABLE_ASYNC_REDIS_OFFLOAD` | used by the consume-path dispatches and `rs._has_budget_async` (:24-33); NOT by `get_usage_status` / `check_usage_allowed`, which call `_get_redis_count` directly (measured, 1.6). |
| default executor | `app/utils/executor.py:34, :51-62`; `main.py:179-182` | none | `qaren-worker` `ThreadPoolExecutor`, default 96 workers (`ADAPTER_EXECUTOR_MAX_WORKERS`, web sets 96 per the module docstring), installed at startup; `asyncio.to_thread` runs there (shared with the adapter fan-out). |
| admin client | `database_service.py:239-272` | `ENABLE_SUPABASE_CLIENT_REUSE` | memoised singleton in BOTH flag states (OFF: first call builds with bare `create_client`, lock-free, "two threads can both build" is today's benign race); so client construction is a once-per-process cost, not per call. |

### 1.4 review_service: every synchronous Upstash call (`rs`)

| site | line | base dispatch | in ST1 |
|---|---|---|---|
| `get_reviews` L1 read | :682 `cached = (await run_redis_offloop(get_cached, cache_key)) if not nocache else None` | pool under `ENABLE_PRICE_PATH_REDIS_OFFLOOP`, else inline | YES: pool under ST1 regardless of the S77 flag |
| `get_reviews` L2-promotion write | :693 `set_cached(cache_key, db_reviews, REVIEWS_CACHE_TTL)` (first statement of `if db_reviews:` :692) | inline in every state (RO17, pinned `test_s77_redis_offloop.py:2050-2066`) | NO: stays inline (RO17 reorder class; open question Q2) |
| `get_reviews` post-extraction write | :726, then `fire_and_forget(save_reviews(...), label="save_reviews.l2")` :733-736, `extraction_persisted = True` :737 | inline in every state (S77 stated limit 1, "the F3 ordering") | YES: durable awaited pool job, L2 save scheduled first |
| `get_reviews` consult re-cache | :754 (inside `if extraction_persisted:` :753, inside the try :744-756) | inline | YES (durable awaited) |
| `get_reviews` YouTube re-cache | :768 (inside `if extraction_persisted:` :767, try :763-770) | inline | YES (durable awaited) |
| `fetch_retailer_quotes` | :811 get, :873 set | inline | NO: zero production callers (its own comment at :832, "this fetcher has ZERO production callers (dormant") |
| `fetch_review_source_snippets` | :913 get, :952 set | inline | NO: runs only in `ENABLE_REVIEW_SOURCE_CONSULT=active` (default OFF) |
| `_has_budget_async` | :24-33 | `ENABLE_ASYNC_REDIS_OFFLOAD` | NO (its own flag) |

`get_reviews` signature :663-674 (`brand, name, variant, search_query, nocache=False, category="other", retailer_ratings=None, search_results=None, track_serper_cost_fn=None, track_gpt_cost_fn=None`); L2 read `product_data_service.get_cached_reviews` :367-386 (`run_db` + `.single()`, the R0-7 406-on-miss, out of scope); `REVIEWS_CACHE_TTL = 7 * 24 * 60 * 60` :42. D03's hunks are in `clean_review_citations` (:158) and `build_retailer_quotes_from_reviews` (:269); `rs` sha256 at base `ab6979ec...` equals D03's recorded base sha for this file (`D03_GREEN_REPORT.md:19`).

### 1.5 Production flag state (newest dated ledger lines; Railway not read)

- `ENABLE_PRICE_PATH_REDIS_OFFLOOP`: ON on web since 2026-10-11 22:50 (session-77 ledger line 53, "SET on web by the orchestrator (owner yes 22:41)"); no later line unsets it. So in production the `redis-offloop` pool exists in every process after its first price-path Upstash call, and the reviews L1 READ is already off the loop; the usage reads and the reviews WRITES are not.
- `ENABLE_SYNC_DB_OFFLOAD`, `ENABLE_ASYNC_REDIS_OFFLOAD`: no ledger line ever set either -> OFF (CLAUDE.md:383-384 default OFF). Therefore in production `get_usage_status` blocks the loop for 3 Supabase round trips (4 with the lazy reset) + 2 Upstash GETs per call.
- `ENABLE_SUPABASE_CLIENT_REUSE`: rolled back after canary s3 (session-77 ledger line 60 + CLAUDE.md SESSION 77 block); `ENABLE_UPSTASH_BOUNDED_TRANSPORT`: held (ledger line 58). ST1 is designed for both states of all four.
- `ENABLE_USAGE_PATH_OFFLOOP`: a new name, unset in production by construction.

### 1.6 The probe (hermetic, base bytes, `test_probe_st1_base.py`, 54 nodes)

Fakes record `(op, threading.current_thread().name)` and `time.sleep(0.08)` per blocking op; a heartbeat coroutine (5 ms sleep) records the largest gap; client/redis fakes patched on `us`; `asyncio.run` per node; conftest loaded with `-p tests.conftest`. `[pyt] tag=st1-base-probe start=2026-10-22 22:35:37 end=2026-10-22 22:36:29 elapsed=52s bound=600s status=OK rc=0` (54 passed; `[hermeticity] sentinel checked 54 test(s)`, `[netguard] blocked 0 attempt(s) from 0 node(s)`).

| function / state | flags | event order (`@T` = off the main thread) | loop freeze (max gap) |
|---|---|---|---|
| `get_usage_status`, any non-reset state | none | `db:users:select, db:referral_redemptions:select, redis:get:daily, redis:get:monthly` | 0.328 s (= 4 x 0.08, one contiguous freeze) |
| same | `ENABLE_SYNC_DB_OFFLOAD` | `db:users:select@T, db:referral_redemptions:select@T, redis:get:daily, redis:get:monthly` | 0.157-0.172 s (the two GETs) |
| same | `ENABLE_ASYNC_REDIS_OFFLOAD` or `ENABLE_PRICE_PATH_REDIS_OFFLOOP` | identical to none (neither flag reaches these GETs) | 0.312-0.329 s |
| `get_usage_status`, `free_reset_past` | none | `db:users:select, db:users:update, db:referral_redemptions:select, redis:get:daily, redis:get:monthly` | 0.406 s |
| `check_usage_allowed`, `free_lifetime` | none | `db:users:select, db:referral_redemptions:select` (no GET) | 0.157 s |
| `check_usage_allowed`, other states | none | as `get_usage_status` | 0.312-0.407 s |
| `consume_comparison_credit`, `free_paid_window` | none | `db:users:select, db:referral_redemptions:select, redis:incrby:daily, redis:expire:daily, redis:incrby:monthly, redis:expire:monthly` | 0.328 s |
| `consume_comparison_credit`, `free_reset_past` | `ENABLE_SYNC_DB_OFFLOAD` | `db:users:select@T, db:referral_redemptions:select@T, db:users:update@T, ...` (the gather interleaves the two helpers once they yield) | 0.328 s |
| `get_reviews` L1 hit | S77 OFF / ON | `l1:get` / `l1:get@T` | 0.078 / 0.016 s |
| `get_reviews` L1 miss, L2 hit | S77 OFF / ON | `l1:get, l2:get, l1:set:604800` / `l1:get@T, l2:get, l1:set:604800` | 0.234 / 0.156 s |
| `get_reviews` miss, extraction | S77 OFF / ON | `l1:get, l2:get, l1:set:604800, l2:save` / `l1:get@T, l2:get, l1:set:604800, l2:save` | 0.250 / 0.156 s |

Flag-OFF base bodies (state `none`; literals for the PIN rows; key format `usage:daily:<id>:<YYYY-MM-DD>` / `usage:monthly:<id>:<YYYY-MM>`):
- `get_usage_status` `free_paid_window` (users `{tier free, lifetime 5, bonus 0}`, redemptions `[]`, daily "2", monthly "7"): `{"limits": {"daily": 3, "lifetime_free": 3, "monthly": 10, "monthly_base": 10, "monthly_bonus": 0}, "remaining": {"daily": 1, "lifetime_free": 0, "monthly": 3}, "tier": "free", "used": {"daily": 2, "lifetime": 5, "monthly": 7}}`
- `free_lifetime` (lifetime 1, daily "3", monthly "9"): `remaining {"daily": 3, "lifetime_free": 2, "monthly": 10}`, `used {"daily": 3, "lifetime": 1, "monthly": 9}` (the display rule: counters reported, allowance full).
- `premium_bonus` (premium, lifetime 100, redemptions `[{"loop2_comparisons_granted": 4}]`, daily "5", monthly "20"): `limits {"daily": 10, "lifetime_free": 0, "monthly": 74, "monthly_base": 70, "monthly_bonus": 4}`, `remaining {"daily": 5, "lifetime_free": 0, "monthly": 54}`.
- `free_reset_past` (lifetime 9, bonus 5, reset_at 2020-01-01, daily "1", monthly "1"): `remaining {"daily": 2, "lifetime_free": 0, "monthly": 9}` and one users UPDATE.
- `check_usage_allowed`: `free_paid_window` `{"allowed": true, "reason": null, "remaining": {"daily": 1, "lifetime_free": 0, "monthly": 3}, "tier": "free"}`; `free_lifetime` `{"allowed": true, "reason": null, "remaining": {"daily": 3, "lifetime_free": 2, "monthly": 10}, "tier": "free"}`; `premium_bonus` `remaining {"daily": 5, "lifetime_free": 0, "monthly": 54}`.

The probe is the method the RED file uses: thread identity per op (the M13-05 / M18 #115 assertion style, `tests/test_m18_offload_sweep_residual.py:1-15`) plus a heartbeat freeze bound; both are hermetic and need no timing assumption beyond "an op sleeps N ms".

### 1.7 Idiom, libraries, line endings

- Flag idiom in both leaf modules: `os.getenv("<NAME>", "").strip().lower() in ("true", "1", "yes", "on")` (`ro:45-48`, `dbo:29-32`), equivalent to the house `os.getenv(..., "false")` form; ST1 copies the leaf-module form.
- Pinned venv `C:/Users/SynAckITPC/Documents/AI/.venv-qaren` (`pip list`): Python 3.12.9, pytest 9.1.1, pytest-asyncio 1.4.0 (mode STRICT, measured in `base_probe.log`, so async tests need `@pytest.mark.asyncio`), fastapi 0.141.1, starlette 1.6.0, httpx 0.28.1, supabase 2.31.0, postgrest 2.31.0, upstash-redis 1.7.0. No new dependency.
- Line endings: the working copy of `us` (758/758 CRLF), `rs` (1094/1094), `ro` (111/111), `dbo` (40/40) and `CLAUDE.md` (940/940) is CRLF, the index LF (`core.autocrlf=true`); edit with the Edit tool (preserves CRLF); a whole-file `git diff --stat` is a defect.
- Non-ASCII already present (bytes > 127): `us` 105, `rs` 251, `dbo` 9, `ro` 0 (em dashes in comments). Every ADDED line is pure ASCII (gate: count bytes > 127 on the added lines of `git diff`); `ro` stays at 0.
- Base sha256 prefixes: `us` e00584ad..., `rs` ab6979ec..., `ro` 31d36e39..., `dbo` a61545c8....

### 1.8 Guards the new code must not trip

- S77 AST inventory `test_s77_redis_offloop.py::test_source_every_in_scope_site_routes_through_helper[get_reviews]` (`_SITE_FUNCS` :1901-1925, the test :1926-1943): exactly one `run_redis_offloop` dispatch `("get_cached", False)` in `get_reviews` and exactly four direct `set_cached` CALLS outside it (`_HELPER = "run_redis_offloop"` :1839, `_WRAPPED` :1840-1843). ST1 keeps both: the base read stays in the OFF branch, the four base `set_cached` calls stay (promotion + the three OFF-branch writes), and the ON branches pass `set_cached` / `get_cached` as NAMES to differently named helpers (a Name is not a Call, so `_direct_wrapped_calls` does not count it).
- RO17 pin `:2050-2066`: the first statement of the `if db_reviews:` block is the direct `set_cached` call. Kept.
- `ro` stdlib-only pin `:2072-2085`. ST1's additions in `ro` import nothing new.
- M18 #115 thread pins on `_get_user_tier_info` (`test_m18_offload_sweep_residual.py:585-624`, 2 executes, threads per `ENABLE_SYNC_DB_OFFLOAD`) and on consume (:440-477): untouched helpers, green.
- `/health` pure-dict pin `test_health_loop_lag.py:190-212` (no `await`, no I/O in the handler) and the additive pin :173-187: `app/main.py` is NOT edited.
- `test_retro_w0_4_efg.py:1512-1516` resets `_REDIS_OFFLOOP_POOL` itself; ST1's RED file drops every `redis-offloop` pool before and after each node (the S77 `_drop_offloop_pools` idiom `:131-158`) so no pool leaks into a later node's `/health`.
- The source scanners in the comm set (section 7): no new model literal, no new external host (no `processors.json` / T7b change), no `.execute()` outside a dispatch on the request path that a scanner counts (the M18 product_data scan :344-357 covers only `product_data_service.py`).
- No credential-bearing name: nothing joins `tests/_env_safety.CREDENTIALS_UNSET`.

### 1.9 Brief items settled by measurement

1. `tests/test_usage_service_internals.py` (109 lines) has NO call-order pin: it pins `_get_redis_count` fail-open (:15-46) and `_maybe_reset_referral_bonus` branches (:49-109), both untouched. It stays green and unedited (4.2), not a 4.1 row.
2. `tests/test_health_loop_lag.py` (478 lines) has NO log-shape pin: it pins the `/health` keys, the recorder and the heartbeat task. ST1 does not edit `app/main.py`; the file stays green and unedited.
3. `check_usage_allowed` has zero production callers (1.1); its ON path is shipped for parity with the plan text and is pinned, but it changes no production behaviour.
4. `run_db` and `run_redis_offloop` are gated by two OTHER flags (1.3); routing through them would make ST1 a no-op for the DB half while `ENABLE_SYNC_DB_OFFLOAD` is OFF and would tie the Redis half to the S77 flag. The brief says "ST1's flag is independent", so the spec adds flag-free twins in the same two modules (2.2). Q1 offers the dependent alternative.
5. The loop-lag heartbeat route-name logging and partial `stage_timings_ms` (panel plan ST1 text) are NOT in PLAN_S81's ST1 unit text nor in the brief's change list: out of scope (section 10, Q4).

### 1.10 Base pass state (bounded runner, one process at a time, every ST1 name unset)

- Pin files of the touched code, one set: `test_usage_service_internals, test_usage_tiers, test_usage_referral_bonus, test_usage_device_inheritance, test_referral_expiry, test_m13_37_freemium_atomic_consume, test_supabase_client_reuse, test_m18_usage_symmetry, test_m13_05_sync_db_offload, test_m18_offload_sweep_residual, test_async_redis_offload, test_health_loop_lag, test_m13_33_review_fire_and_forget, test_youtube_flag_and_cache, test_youtube_reviews_race, test_review_source_consult, test_retailer_quotes, test_paid_route_metering, test_category_review_terms, test_retro_w1_7_w1_10, test_health_brand_s69`: 227 passed. `[pyt] tag=st1-base-pinsA start=2026-10-22 22:30:50 end=2026-10-22 22:31:42 elapsed=52s bound=1200s status=OK rc=0`; `[hermeticity] sentinel checked 227 test(s)`; `[netguard] blocked 2 attempt(s) from 2 node(s)` (both `test_paid_route_metering.py` sentinel `neutralized.supabase.invalid:443`, the placeholder host, baseline).
- `test_s77_redis_offloop.py test_decomposed_services.py test_s75_fanout_starve.py`: 319 passed. `[pyt] tag=st1-base-s77 start=2026-10-22 22:32:06 end=2026-10-22 22:32:53 elapsed=47s bound=600s status=OK rc=0`; `[hermeticity] sentinel checked 319 test(s)`; `[netguard] blocked 0 attempt(s) from 0 node(s)`.
- The probe (1.6): 54 passed, `status=OK rc=0`.
- Comm set at base (119 files, five chunks of at most 24, section 7.2 item 4): 5,108 passed, 25 skipped, 12 deselected, 1 xfailed, 2 ERROR (the known cold-tiktoken `test_prompt_truth.py` pair, box noise); no FAILED node.

## 2. Contract

### 2.1 Flag

`ENABLE_USAGE_PATH_OFFLOOP`, reader `app/utils/redis_offloop.py::usage_path_offloop_enabled()` (the leaf both consumers already can import; no new import edge into a service module):

```python
def usage_path_offloop_enabled() -> bool:
    """S81 ST1 ENABLE_USAGE_PATH_OFFLOOP - read PER CALL (default OFF)."""
    return os.getenv("ENABLE_USAGE_PATH_OFFLOOP", "").strip().lower() in (
        "true", "1", "yes", "on",
    )
```

Read per call: as the FIRST statement of `get_usage_status` and `check_usage_allowed` (after the docstring), and ONCE per `get_reviews` call into a local (`offloop`), right after `cache_key` is computed, so one reviews call never mixes states. No knob. The shared `REDIS_OFFLOOP_MAX_WORKERS` (read once at pool build) sizes the pool for both units. No new env name besides the flag; nothing reads a credential.

### 2.2 New dispatch helpers (flag-free; the caller owns the gate)

`app/utils/redis_offloop.py` (after `run_redis_offloop`, which stays byte-unchanged; stdlib only):

```python
async def run_redis_offloop_pool(fn, *args, durable: bool = False):
    """S81 ST1: ONE job on the shared redis-offloop pool WHATEVER
    ENABLE_PRICE_PATH_REDIS_OFFLOOP says (the caller reads its own flag).
    Same mechanics as the ON branch of run_redis_offloop: copied contextvars,
    durable writes shielded and quietly retrieved."""
    loop = asyncio.get_running_loop()
    ctx = contextvars.copy_context()
    fut = loop.run_in_executor(
        _get_redis_offloop_pool(), functools.partial(ctx.run, fn, *args),
    )
    if durable:
        fut.add_done_callback(_retrieve_quietly)
        return await asyncio.shield(fut)
    return await fut
```

`app/utils/db_offload.py` (after `run_db`, which stays byte-unchanged):

```python
async def run_db_offloop(call: Callable[[], T]) -> T:
    """S81 ST1: always asyncio.to_thread (the loop's default qaren-worker
    executor) WHATEVER ENABLE_SYNC_DB_OFFLOAD says (the caller owns the gate)."""
    return await asyncio.to_thread(call)
```

### 2.3 usage_service under the flag

New blocking twins (sync; run only inside a thread job; they reference the module globals `get_admin_supabase_client`, `_maybe_reset_referral_bonus`, `datetime`, `timezone` at call time so every existing test patch on `us` intercepts them):

- `_tier_info_blocking(user_id) -> dict`: `client = get_admin_supabase_client()`; `result = client.table("users").select("subscription_tier, lifetime_comparisons_used, referral_bonus_comparisons_this_month, referral_bonus_reset_at").eq("id", user_id).single().execute()` (the same select string, byte for byte, as :528-529); `data = result.data or {}`; `return _maybe_reset_referral_bonus(client, user_id, data)`; `except Exception as e`: `logger.error("[USAGE-OFFLOOP] tier info read failed type=%s", type(e).__name__)` and return the same three-key fallback dict as :540-544.
- `_active_bonus_blocking(user_id) -> int`: the :599-610 query (`referral_redemptions`, `select("loop2_comparisons_granted")`, `eq("referrer_user_id", user_id)`, `gt("expires_at", now_iso)`, `is_("consumed_at", "null")`) executed directly; the same sum; `except Exception as e`: `logger.warning("[USAGE-OFFLOOP] referral bonus read failed type=%s", type(e).__name__)`, return 0 (fail-open low, never an inflated cap).
- `_usage_reads_offloop(user_id)` (async): `daily_key = _daily_key(user_id)`, `monthly_key = _monthly_key(user_id)` computed on the loop BEFORE dispatch; then ONE `asyncio.gather(run_db_offloop(lambda: _tier_info_blocking(user_id)), run_db_offloop(lambda: _active_bonus_blocking(user_id)), run_redis_offloop_pool(_get_redis_count, daily_key), run_redis_offloop_pool(_get_redis_count, monthly_key))` returning `(user_info, bonus, daily_used, monthly_used)`. No `return_exceptions` (each job already swallows its own errors).
- `_usage_status_body(user_info, bonus, daily_used, monthly_used) -> dict` and `_usage_allowed_body(user_info, bonus, daily_used, monthly_used) -> dict`: pure; the base compute of :720-724 + :735-758 and of :630-682 respectively, line for line (the lifetime-free display rule and the lifetime-free early return included; `check_usage_allowed`'s ON path therefore READS the two counters even on the lifetime-free path, where base reads none, and ignores them exactly as base would).
- Fork at the top of each public function (pure insertion; the base body below it is byte-unchanged):

```python
    if usage_path_offloop_enabled():
        try:
            return _usage_status_body(*(await _usage_reads_offloop(user_id)))
        except Exception as exc:  # noqa: BLE001 - dispatch failure: fall back inline
            logger.warning(
                "[USAGE-OFFLOOP] dispatch failed fn=get_usage_status type=%s -- inline fallback",
                type(exc).__name__,
            )
```

(`check_usage_allowed`: `_usage_allowed_body`, `fn=check_usage_allowed`.) `asyncio.CancelledError` is a `BaseException` and propagates (no fallback, no log). Imports: two NEW lines after :16, `from app.utils.db_offload import run_db_offloop` and `from app.utils.redis_offloop import run_redis_offloop_pool, usage_path_offloop_enabled` (the :16 line stays byte-unchanged).

### 2.4 review_service.get_reviews under the flag

- Import line :20 becomes `from app.utils.redis_offloop import run_redis_offloop, run_redis_offloop_pool, usage_path_offloop_enabled` (the known D03 rebase if D03 touched the block; resolve by union).
- After :677 `cache_key = get_reviews_cache_key(...)`: `offloop = usage_path_offloop_enabled()  # S81 ST1: one read per call`.
- :682 becomes `if offloop: cached = (await run_redis_offloop_pool(get_cached, cache_key)) if not nocache else None` / `else:` the base line verbatim.
- :689-697 (L2 block incl. the promotion write :693): byte-unchanged (RO17).
- :724-737: `if offloop:` -> `from app.services.product_data_service import save_reviews`; `fire_and_forget(save_reviews(cache_key, brand, name, variant, reviews), label="save_reviews.l2")`; `await _reviews_l1_set_offloop(cache_key, reviews)` / `else:` the base lines :726-736 verbatim; `extraction_persisted = True` after both branches (as :737).
- :753-754 and :767-768: `if extraction_persisted:` -> `if offloop: await _reviews_l1_set_offloop(cache_key, reviews)` / `else: set_cached(cache_key, reviews, REVIEWS_CACHE_TTL)` (base verbatim).
- New module helper (placed before `get_reviews`, not inside D03's two functions):

```python
async def _reviews_l1_set_offloop(cache_key: str, reviews: dict) -> None:
    """S81 ST1: one reviews L1 write as a DURABLE redis-offloop job (lands even
    when the reviews race cancels the caller mid-await). A dispatch failure is
    logged by type and swallowed, as the inline set_cached swallows its own."""
    try:
        await run_redis_offloop_pool(
            set_cached, cache_key, reviews, REVIEWS_CACHE_TTL, durable=True,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("[USAGE-OFFLOOP] reviews L1 write dispatch failed type=%s", type(exc).__name__)
```

Why the L2 save is scheduled BEFORE the awaited write under ON: at base the inline SET and the `fire_and_forget` both complete before any cancellation can be delivered (no suspension point); under ON the awaited SET is a suspension point, and a reviews-race cancel there would skip a save scheduled after it (mutant M16). The two writes go to different stores and have no order dependency.

### 2.5 Response and contract (freeze compliance)

- `/api/v1/usage/status`: the same dict, key order included, in both flag states (the body helpers build the dicts in the base key order); no new key, no new status code, no new error code. A dispatch failure returns the base inline result. Build 3 sees no change (contract_freeze RULE 4: no new code; never a bare 503: ST1 raises nothing new).
- `check_usage_allowed`: same dict in both states.
- `get_reviews`: same returned dict (`_cached`, `_cache_source` keys as base) in both states.
- `/health`: no new key, `app/main.py` not edited. The existing `redis_offloop_pool` `{workers, queued}` key (RO18, present only once the pool exists) appears after the first ST1 dispatch in a process where the S77 flag is OFF; in production it is already present (S77 flag ON). Additive by construction, the existing shape.
- No quota key, no TTL, no refund, no consume change; `consumed_keys` unchanged.

### 2.6 Log templates (ON only; constants and type names, never a value, a key or an id)

| template | level | where |
|---|---|---|
| `[USAGE-OFFLOOP] dispatch failed fn=get_usage_status type=%s -- inline fallback` | WARNING | the `get_usage_status` fork's `except Exception` |
| `[USAGE-OFFLOOP] dispatch failed fn=check_usage_allowed type=%s -- inline fallback` | WARNING | the `check_usage_allowed` fork |
| `[USAGE-OFFLOOP] tier info read failed type=%s` | ERROR | `_tier_info_blocking` except arm (base logs the exception TEXT at :539; the twin logs the type only) |
| `[USAGE-OFFLOOP] referral bonus read failed type=%s` | WARNING | `_active_bonus_blocking` except arm |
| `[USAGE-OFFLOOP] reviews L1 write dispatch failed type=%s` | WARNING | `_reviews_l1_set_offloop` except arm |

The pool's own `[REDIS-OFFLOOP] pool built workers=%d` INFO line (once per process) can now be emitted by an ST1 dispatch.

### 2.7 Flag-OFF identity (the unit's main invariant)

With `ENABLE_USAGE_PATH_OFFLOOP` unset / `""` / `false` / `0` / `off` / `no` / garbage: `get_usage_status`, `check_usage_allowed` and `get_reviews` make the same calls in the same order with the same arguments on the same threads as base, return the same dicts, emit no new log line, build no pool and call no new helper; the only extra work is one `os.getenv` per call. Pinned in every relevant combination of the other offload flags (R9, R9b, R23) with the full ST1 configuration present (`REDIS_OFFLOOP_MAX_WORKERS=4`, both S77 states, both `ENABLE_SYNC_DB_OFFLOAD` states) and a call/thread recorder, so a not-gated mutant is killed. `consume_comparison_credit`, `_refund_credit_sync`, every key helper, `_get_user_tier_info`, `_get_active_referral_bonus`, `_get_redis_count`, `run_db`, `run_redis_offloop` and the S77 reader/pool functions are byte-unchanged (AST digests at base, R25):

| function | sha256(ast.dump) prefix at base |
|---|---|
| `us.consume_comparison_credit` | cfe716e23081b31c |
| `us._refund_credit_sync` / `_refund_one_window` / `refund_comparison_credit` | 2c8fa5760fcd214b / 7eecf1d072cce151 / 65eabb2733f9b964 |
| `us._atomic_consume` / `_bump_counters` / `check_anon_usage_allowed` | 7469c96124b0ce4e / 3ea0760e673e0827 / 839ed95509d4647b |
| `us._daily_key` / `_monthly_key` / `_previous_daily_key` / `_previous_monthly_key` | 3f76488c05edf55d / 63ff3c9e84fbd1cb / b3c3dd2e05cb059e / 885f6947965d9c86 |
| `us._get_user_tier_info` / `_get_active_referral_bonus` / `_maybe_reset_referral_bonus` / `_get_redis_count` | d08df410b0f254c5 / 75adcbc5b9ed1239 / 0e220a05bfef8cc6 / 14f06465a31c293c |
| `us.record_lifetime_comparison` / `TIER_LIMITS` (assign) | f8ae429cbd5ba91f / bc58e3b46850bbc2 |
| `ro.run_redis_offloop` / `redis_offloop_enabled` / `_get_redis_offloop_pool` / `redis_offloop_pool_stats` / `redis_offloop_max_workers` | b0303fb209a3edf7 / 3f12c97d92e65263 / 25597d3c06b06dfc / db3008ab19c321b2 / 35b8ab2d83bd3d1c |
| `dbo.run_db` / `sync_db_offload_enabled` | a193babb9590f520 / 8cf14184edf5ed67 |

(Digest = `hashlib.sha256(ast.dump(node).encode()).hexdigest()` over the top-level node of that name in `ast.parse(<file text>)`; line-number independent; recomputed by the RED author at base and asserted as literals.)

### 2.8 Failure table (flag ON)

| event | base (OFF) | ON |
|---|---|---|
| Supabase tier read raises | ERROR with text, fallback dict | ERROR with type only, same fallback dict, same response |
| referral bonus read raises | WARNING with text, 0 | WARNING with type only, 0 |
| `redis_client is None` / GET raises | 0 | 0 (same function, in a pool thread) |
| thread / pool submit raises (`RuntimeError`: shutdown, thread exhaustion) | n/a | one WARNING `dispatch failed ... type=RuntimeError`, then the base inline body: same response, loop blocked for that call |
| a body helper raises (a defect) | n/a | same WARNING, base inline body (R14 asserts the WARNING never fires on the happy path) |
| request cancelled during the gather | n/a (no suspension) | `CancelledError` propagates; jobs already running finish in their threads (a running read cannot be cancelled; a queued `run_in_executor` read is dropped); the lazy reset UPDATE may or may not land (it lands at most once per reset window, idempotent) |
| Upstash / Supabase stall | the loop freezes until the client returns (no timeout with the bounded transport OFF) | one pool / qaren-worker thread parks; the request waits as long; the loop keeps turning (no new timeout in ST1) |
| reviews L1 write dispatch fails | n/a | WARNING by type, swallowed; the L2 save already scheduled; the reviews leg succeeds |
| reviews race cancels during the awaited L1 write | n/a | the write lands (shield), the L2 save was scheduled before the await, `CancelledError` propagates as at the race |
| reviews L1 read dispatch fails | n/a | raises, as `run_redis_offloop` ON does today (S77 stated limit 12) |

### 2.9 Test seams (production values in brackets)

- `us.get_admin_supabase_client` [memoised admin client], `us.redis_client` [the Upstash SDK client], `us._get_redis_count`, `us._maybe_reset_referral_bonus`, `us._tier_info_blocking`, `us._active_bonus_blocking`, `us.run_db_offloop` [`asyncio.to_thread`], `us.run_redis_offloop_pool` [the shared pool], `rs.get_cached` / `rs.set_cached` [cache_service], `rs.run_redis_offloop_pool`, `app.services.product_data_service.get_cached_reviews` / `save_reviews` [Supabase L2], `rs.extract_reviews`, `rs.consult_review_sources`, `rs.consult_youtube_source`.
- `REDIS_OFFLOOP_MAX_WORKERS` [unset -> 16; tests use 4, and 1 for the queued-cancel row].
- Pools: `ro._REDIS_OFFLOOP_POOL` [built lazily]; tests drop every `redis-offloop` pool before and after each node.

## 3. Change list, in the order GREEN applies it

0. Byte copies of the four app files and `CLAUDE.md` (Python `shutil.copyfile` into `<scratchpad>/ST1/green_copies/`, sha256 recorded). Cut `feature/s81-loop-stall` (orchestrator). The RED file `tests/test_s81_st1_usage_path_offloop.py` is frozen (sha recorded at the RED gate) and is not edited by GREEN.
1. `app/utils/redis_offloop.py`: add `usage_path_offloop_enabled()` and `run_redis_offloop_pool()` after `run_redis_offloop` (2.1, 2.2). Docstring of the module: one added sentence naming ST1's two functions. Stdlib only.
2. `app/utils/db_offload.py`: add `run_db_offloop()` after `run_db` (2.2).
3. `app/services/usage_service.py`: two import lines after :16; `_tier_info_blocking`, `_active_bonus_blocking`, `_usage_reads_offloop`, `_usage_status_body`, `_usage_allowed_body` inserted after `_get_active_referral_bonus` (:615) and before `check_usage_allowed` (:618); the fork at the top of `check_usage_allowed` and `get_usage_status` (2.3). No other line of the file changes (diff = pure insertion).
4. `app/services/review_service.py`: the import line :20, `_reviews_l1_set_offloop` before `get_reviews`, and the `get_reviews` hunks of 2.4. Nothing in `clean_review_citations`, `build_retailer_quotes_from_reviews`, `fetch_retailer_quotes`, `fetch_review_source_snippets` or the consult functions. Known rebase with D03: the import block and nothing else.
5. `CLAUDE.md`: the new SESSION 81 flag row after :477 (section 8.1, before `## Tests` :479) and the two in-place rewrites of 8.2 (:383 and :385).
6. Lint/syntax/bytes gates (7.1), then the RED file, then the pin and comm gates.

No other file. Explicitly untouched: `app/main.py`, `app/api/usage_routes.py`, `app/api/text_routes.py`, `app/api/image_routes.py`, `app/api/url_routes.py`, `app/services/cache_service.py`, `app/services/database_service.py`, `app/services/product_data_service.py`, `app/utils/executor.py`, `tests/conftest.py`, `tests/_env_safety.py`, `tests/.pre_impl_failures.txt`, every existing test, `requirements*`, `app/legal/processors.json`.

## 4. Existing pins

### 4.1 Pins that change deliberately

None. Measured reasons for the two the brief named: `test_usage_service_internals.py` pins only `_get_redis_count` and `_maybe_reset_referral_bonus`, which ST1 does not edit (1.9.1); `test_health_loop_lag.py` pins `/health` keys and the heartbeat, and ST1 does not edit `app/main.py` (1.9.2). The S77 AST inventory and the RO17 pin stay green by the design of 1.8 (the base calls stay in the OFF branches; ST1 dispatches through differently named helpers and gets its own inventory pin, R25). If GREEN finds any existing node red at HEAD with the flag unset, it stops and reports; no pin is edited without an orchestrator ruling.

### 4.2 Pins that must stay green and unedited (all green at base, 1.10)

`tests/test_usage_service_internals.py`, `test_usage_tiers.py`, `test_usage_referral_bonus.py`, `test_usage_device_inheritance.py`, `test_referral_expiry.py`, `test_m13_37_freemium_atomic_consume.py`, `test_supabase_client_reuse.py`, `test_m18_usage_symmetry.py`, `test_m13_05_sync_db_offload.py`, `test_m18_offload_sweep_residual.py`, `test_async_redis_offload.py`, `test_health_loop_lag.py`, `test_health_brand_s69.py`, `test_retro_w1_7_w1_10.py`, `test_m13_33_review_fire_and_forget.py`, `test_youtube_flag_and_cache.py`, `test_youtube_reviews_race.py`, `test_review_source_consult.py`, `test_retailer_quotes.py`, `test_category_review_terms.py`, `test_decomposed_services.py`, `test_s75_fanout_starve.py`, `test_s77_redis_offloop.py` (incl. `[get_reviews]` of the inventory, RO17, the stdlib-only pin, the F3/G2 exclusion :1206-1220), `test_paid_route_metering.py` (both flag states of `ENABLE_PAID_ROUTE_METERING`, as the brief asks), `test_retro_w0_4_efg.py`, and every file of the comm set (section 7).

Local-env hazard (stated limit L8): with `ENABLE_USAGE_PATH_OFFLOOP` exported into the process, S77 rows that assert the reviews L1 read runs inline with the S77 flag OFF, and any test that patches the async helpers `_get_user_tier_info` / `_get_active_referral_bonus` to drive `get_usage_status` / `check_usage_allowed`, go red. CI runs with the flag unset. GREEN measures the set once with the flag exported (one runner call, env on that call only) and lists the red nodes in the report; none is edited.

## 5. RED tests

One new file `tests/test_s81_st1_usage_path_offloop.py` (pure ASCII; hermetic; fakes only; no network; `@pytest.mark.asyncio` STRICT). Autouse fixture: delete `ENABLE_USAGE_PATH_OFFLOOP`, `ENABLE_SYNC_DB_OFFLOAD`, `ENABLE_ASYNC_REDIS_OFFLOAD`, `ENABLE_PRICE_PATH_REDIS_OFFLOOP`, `ENABLE_SUPABASE_CLIENT_REUSE`, `ENABLE_REVIEW_SOURCE_CONSULT`, `ENABLE_UNIFIED_SEARCH_BOUND`, `REDIS_OFFLOOP_MAX_WORKERS`; drop every `redis-offloop` pool (by type + thread-name prefix, the S77 idiom) before and after. Missing symbols are read through a `_require(module, name)` helper that raises `AssertionError("ST1 not implemented: <name>")`; patches of new symbols use `monkeypatch.setattr(..., raising=False)`; so every RED row fails at base on an AssertionError only. Recorder = the probe's fakes (1.6): `(op, thread name)` per op, `time.sleep(OP)` per op (`OP = 0.15` s for the freeze rows, 0 elsewhere), heartbeat every 5 ms. Full configuration on every PIN row: `REDIS_OFFLOOP_MAX_WORKERS=4` set, the other offload flags in the parametrized combination, the recorder installed. States (S): `free_paid_window`, `free_lifetime` (lifetime 1 with daily "3" monthly "9", the display rule), `premium_bonus`, `free_reset_past`, `free_daily_exhausted` (daily "3"), `free_monthly_exhausted` (daily "1" monthly "10"), `premium_over` (daily "12" monthly "80": the `max(0, ...)` floors), `redis_none` (`redis_client = None`), `tier_raises` (client `.table` raises `RuntimeError` built at run time), `bonus_raises`, `unknown_tier` (`"gold"` -> free limits). Combos (C): ST1 ON x `ENABLE_SYNC_DB_OFFLOAD` {off, on} x `ENABLE_PRICE_PATH_REDIS_OFFLOOP` {off, on} x `ENABLE_ASYNC_REDIS_OFFLOAD` {off, on} = 8.

| # | test | assertion | at base | satisfied by |
|---|---|---|---|---|
| R1 | `test_helpers_exist` | `ro.usage_path_offloop_enabled`, `ro.run_redis_offloop_pool`, `dbo.run_db_offloop` exist and the two dispatchers are coroutine functions | RED (missing) | 2.1, 2.2 |
| R2 | `test_flag_reader_truth_table[value]` | unset, `""`, `"false"`, `"0"`, `"off"`, `"no"`, `"garbage"`, `"truee"` -> False; `"true"`, `"TRUE"`, `" true "`, `"1"`, `"yes"`, `"on"`, `" On "` -> True | RED | 2.1 |
| R3 | `test_pool_dispatch_is_independent_of_the_s77_flag` | with the S77 flag OFF: `run_redis_offloop_pool(fn)` runs `fn` on a thread whose name starts `redis-offloop`, builds exactly one pool (second call reuses it), copies a ContextVar set by the caller, and with `durable=True` a write whose caller is cancelled while queued behind a 1-worker blocker still runs | RED | 2.2 |
| R4 | `test_db_dispatch_is_independent_of_sync_db_offload` | with `ENABLE_SYNC_DB_OFFLOAD` OFF, `run_db_offloop(call)` runs `call` off the main thread and returns its value | RED | 2.2 |
| R5 | `test_usage_status_on_runs_every_blocking_op_off_the_loop[C x S]` | ST1 ON: every recorded op of `get_usage_status` (users select, reset update when due, redemptions select, both GETs) is NOT on the main thread; the GETs run on `redis-offloop` threads, the DB ops on non-`redis-offloop` threads | RED (all on main at base) | 2.3 |
| R6 | `test_usage_status_on_does_not_freeze_the_loop[S4]` | ST1 ON, OP 0.15 s, four ops: heartbeat max gap < 0.09 s (base 0.6 s; measured 0.328 s at OP 0.08) | RED | 2.3 |
| R7 | `test_usage_status_on_reads_in_one_gather` | ST1 ON, OP 0.15 s: wall < 0.45 s (serial base 0.6 s) and the four ops' start times overlap (all four started before any finished) | RED | 2.3 |
| R8 | `test_usage_status_on_equals_off[S]` | `get_usage_status` dict ON == OFF (same values, same key order via `list(d)` recursively) for every S; and OFF == the 1.6 literals for the four probe states | PIN (ON is inert at base) | 2.3 body helper |
| R9 | `test_usage_status_off_is_the_base_call_sequence[S x sync x s77]` | ST1 OFF (`unset`, `"false"`, `"0"`, `"off"`, `""` rotate across nodes), full config: recorded op sequence and thread placement equal the 1.6 rows for that combination; no `redis-offloop` pool built when the S77 flag is OFF; `us.run_db_offloop` / `us.run_redis_offloop_pool` spies (installed `raising=False`) never called; no `[USAGE-OFFLOOP]` record | PIN | 2.7 |
| R9b | `test_check_usage_allowed_off_is_the_base_call_sequence[S]` | the same for `check_usage_allowed`, incl. ZERO GETs on `free_lifetime` | PIN | 2.7 |
| R10 | `test_check_usage_allowed_on_off_loop_and_equal[C x S]` | ST1 ON: every op off the main thread; result == OFF result | RED (placement half) | 2.3 |
| R11 | `test_check_usage_allowed_on_reads_counters_on_the_lifetime_free_path` | ST1 ON, `free_lifetime`: exactly two GETs recorded (daily, monthly keys) and the result equals OFF (the counters are ignored) | RED (0 GETs at base) | 2.3 one gather |
| R12 | `test_consume_is_unchanged_by_the_flag[other flags x S]` | `consume_comparison_credit` op sequence, threads and returned dict (incl. `consumed_keys` literal shape `usage:daily:<id>:<YYYY-MM-DD>`) are identical with ST1 ON and OFF in each combination of the other three flags | PIN | 2.7 |
| R13 | `test_refund_is_unchanged_by_the_flag` | `refund_comparison_credit(uid, consumed_keys)` and the legacy no-keys form: the same GET/DECRBY/INCRBY sequence on the same thread with ST1 ON and OFF | PIN | 2.7 |
| R14 | `test_dispatch_failure_falls_back_inline[fn]` | ST1 ON, `us.run_db_offloop` patched (raising=False) to raise `RuntimeError`: result == OFF result; exactly one WARNING record whose `getMessage()` == `"[USAGE-OFFLOOP] dispatch failed fn=<fn> type=RuntimeError -- inline fallback"`; the fallback ops ran on the main thread; on the happy path (R5 nodes) no `[USAGE-OFFLOOP]` record at all | RED | 2.3 fork |
| R15 | `test_cancel_propagates_without_fallback` | ST1 ON, fakes block on a `threading.Event` (timeout 1 s); cancel the task once an op has started: `CancelledError` raised, no WARNING, no inline op recorded on the main thread; release the Event | RED (base runs inline and returns a dict) | 2.3 |
| R16 | `test_blocking_twins_match_the_async_helpers[S]` | `_tier_info_blocking(uid)` == `await _get_user_tier_info(uid)` and `_active_bonus_blocking(uid)` == `await _get_active_referral_bonus(uid)` (sync offload OFF) for every S incl. the raising clients and the past reset (both issue the UPDATE once) | RED (twins missing) | 2.3 |
| R17 | `test_twin_logs_carry_type_names_only` | a client raising `RuntimeError(<run-time synthetic text>)`: the twin's record message contains `type=RuntimeError` and not the synthetic text; level ERROR (tier) / WARNING (bonus) | RED | 2.6 |
| R18 | `test_reviews_l1_read_on_runs_on_the_pool[s77]` | ST1 ON, L1 hit, both S77 states: `get_cached` on a `redis-offloop` thread; returned dict == OFF (`_cached` True) | RED (main when S77 OFF) | 2.4 |
| R19 | `test_reviews_post_extraction_write_on_runs_on_the_pool[s77]` | ST1 ON, L1+L2 miss: the 604800-TTL `set_cached` on a `redis-offloop` thread; `save_reviews` ran once with `(cache_key, brand, name, variant, reviews)`; returned dict == OFF | RED | 2.4 |
| R20 | `test_reviews_l2_promotion_write_stays_inline` | ST1 ON, L2 hit, both S77 states: the promotion `set_cached` on the main thread, args `(cache_key, db_reviews, 604800)` | PIN (RO17) | 2.4 |
| R21 | `test_reviews_recache_writes_on_run_in_order` | ST1 ON, consult fake returns one quote and YouTube fake one signal: three `set_cached` calls, all on `redis-offloop` threads, in order baseline -> with `review_source_quotes` -> with `youtube_review_signal` (assert each recorded payload's keys) | RED | 2.4 |
| R22 | `test_reviews_cancel_mid_write_lands_and_saves` | ST1 ON, `REDIS_OFFLOOP_MAX_WORKERS=1`, a blocker job occupies the pool, cancel `get_reviews` while its post-extraction write is queued: `CancelledError` raised, the write lands after the blocker is released, `save_reviews` was scheduled and ran | RED | 2.4 (durable + save first) |
| R23 | `test_reviews_off_is_the_base_sequence[path x s77]` | ST1 OFF (rotating OFF spellings), full config: event order and thread placement equal the 1.6 V rows for l1_hit / l2_hit / miss; `run_redis_offloop_pool` spy never called; with S77 OFF no pool built | PIN | 2.7 |
| R24 | `test_reviews_nocache_reads_no_l1[on/off]` | `nocache=True`: no `get_cached` call in either state | PIN | 2.4 |
| R25 | `test_source_inventory_and_frozen_digests` | AST of `rs.get_reviews`: exactly one `run_redis_offloop(get_cached, ...)` (not durable), exactly one `run_redis_offloop_pool(get_cached, ...)` (not durable), exactly three `_reviews_l1_set_offloop(...)` calls, four direct `set_cached` calls, the `if db_reviews:` block opens with the direct `set_cached`; `_reviews_l1_set_offloop` holds one `run_redis_offloop_pool(set_cached, ..., durable=True)`; AST of `us`: `get_usage_status` / `check_usage_allowed` first body statement after the docstring is an `If` whose test is a call to `usage_path_offloop_enabled`; every 2.7 digest equals its literal | RED (inventory half) / PIN (digests) | 2.3, 2.4, 2.7 |
| R26 | `test_health_shows_the_existing_pool_key_after_an_on_read` | S77 OFF, ST1 ON, one `get_usage_status` call: `/health` (direct handler call) carries `redis_offloop_pool` with int `workers` == 4 and int `queued`; `status`/`message` unchanged; with ST1 OFF the key is absent | RED (ON half) | 2.5 |
| R27 | `test_usage_route_body_is_identical[on/off]` | `TestClient(app)` GET `/api/v1/usage/status` with `get_current_user` overridden to a synthetic user: HTTP 200 and `resp.content` byte-identical ON vs OFF for `free_paid_window` and `premium_bonus` | PIN | 2.5 |
| R28 | `test_flag_is_read_per_call` | one process: ON call (ops off main) then the env unset, next call inline on main, then ON again off main | RED | 2.1 |
| R29 | `test_on_path_never_calls_the_consume_shared_async_helpers` | ST1 ON: `us._get_user_tier_info` / `us._get_active_referral_bonus` replaced by spies that fail the test if awaited; `get_usage_status` and `check_usage_allowed` complete | RED (base awaits them) | 2.3 |
| R30 | `test_get_keys_are_the_date_keys` | ST1 ON and OFF: the two GET keys are exactly `_daily_key(uid)`, `_monthly_key(uid)` | PIN | 2.3 |

Counts: 30 row functions; RED = R1-R7, R10, R11, R14-R19, R21, R22, R25 (inventory half), R26, R28, R29 (21 rows); PIN = R8, R9, R9b, R12, R13, R20, R23, R24, R25 (digest half), R27, R30 (11 rows; R25 counted in both). Parametrized node count is the RED author's to report (about 200).

Tester scenario mapping (`eval_regression.json`): ST1 is a platform-floor unit with no tester-visible output change; no tester row applies. The scenarios it serves are the slow Home/Paywall mounts behind MYEZ-015 (the stall class in prod_evidence finding 8), measured only by MS1 + the canary.

## 6. Mutation table (each on a byte copy of GREEN's file, one exact-string edit matching once, the killing rows via `pyt.py -k`, bound 600, restore from the copy, sha256 compare, `.qa-mutation.lock` held)

| id | file | mutation | killed by |
|---|---|---|---|
| M1 | `ro` | `usage_path_offloop_enabled` returns True always (not gated) | R9, R9b, R23 |
| M2 | `ro` | returns False always | R5, R18, R28 |
| M3 | `ro` | drop `.strip().lower()` | R2 (`" true "`, `"TRUE"`, `" On "`) |
| M4 | `ro` | `run_redis_offloop_pool` delegates to `run_redis_offloop` (S77-gated) | R3, R5 (S77 off combos), R18 |
| M5 | `ro` | `run_redis_offloop_pool` drops `ctx.run` (no context copy) | R3 |
| M6 | `ro` | `durable` branch drops `asyncio.shield` | R22 |
| M7 | `dbo` | `run_db_offloop` calls `run_db` (sync-gated) | R4, R5 (sync off combos) |
| M8 | `us` | `_usage_reads_offloop` tier read via `run_db` | R5 (sync off) |
| M9 | `us` | the two GETs via `_get_redis_count_async` | R5 (async off) |
| M10 | `us` | four sequential awaits instead of one gather | R7 |
| M11 | `us` | `_usage_status_body` drops the lifetime-free display rule | R8 (`free_lifetime`) |
| M12 | `us` | `_usage_status_body` monthly cap without bonus | R8 (`premium_bonus`) |
| M13 | `us` | `_usage_allowed_body` daily check `>` instead of `>=` | R10 (`free_daily_exhausted`) |
| M14 | `us` | fork `except BaseException` | R15 |
| M15 | `us` | fork without try/except | R14 |
| M16 | `us` | fork log `%s` of `exc` instead of `type(exc).__name__` | R14 (exact message) |
| M17 | `us` | `_tier_info_blocking` skips `_maybe_reset_referral_bonus` | R16, R8 (`free_reset_past`) |
| M18 | `us` | twin logs the exception text | R17 |
| M19 | `us` | ON path awaits `_get_user_tier_info` instead of the twin | R29, R5 (sync off) |
| M20 | `us` | flag read hoisted to a module constant | R28 |
| M21 | `us` | `consume_comparison_credit` gathers via `_usage_reads_offloop` | R12, R25 digest |
| M22 | `us` | `check_usage_allowed` ON returns `_usage_status_body(...)` | R10 |
| M23 | `rs` | promotion write moved to `_reviews_l1_set_offloop` | R20, R25 |
| M24 | `rs` | post-extraction write `durable=False` | R22 |
| M25 | `rs` | `fire_and_forget(save_reviews)` after the awaited write | R22 |
| M26 | `rs` | ON read ignores `nocache` | R24 |
| M27 | `rs` | `_reviews_l1_set_offloop` without try/except | a row driving a raising dispatch: add to R19 as `[dispatch_raises]` (the leg returns the dict, WARNING recorded) |
| M28 | `rs` | `offloop` read twice (second read before the writes) | R28 variant `[mid_call_flip]`: flag flipped between read and write inside a fake extract; all ops follow the first read |
| M29 | `us` | keys computed inside the thread job | expected EQUIVALENT (same keys; only the clock instant moves); report it for a ruling |

## 7. Comm set and gates for GREEN (cheapest first; every pytest through `pyt.py`, one process at a time)

### 7.1 Static gates

1. `py_compile` on the four app files and the RED file; `ruff check --select E9,F63,F7,F82 --no-cache` on the same.
2. `git diff --stat`: four app files + `CLAUDE.md` only, insertion-sized (no whole-file diff); `git diff` added lines: zero bytes > 127 (Python byte count) and a clean run of the common brief's added-line personal-data and key-shape sweep (mail-provider domains, the Bahrain dialling prefix, 8-digit runs, credential shapes).
3. The RED file unchanged (sha from the RED gate).

### 7.2 Runner gates

1. The RED file: bound 600, all green at HEAD (ON and OFF rows are inside the file; one call).
2. The 4.2 pin files in two calls (bound 1200): green, the same netguard lines as base.
3. CI-order set (one process, alphabetical, bound 1200): the RED file + the 4.2 files.
4. Comm set (119 files = module/symbol reference grep for `usage_service`, `review_service`, `redis_offloop`, `db_offload`, `get_usage_status`, `check_usage_allowed`, `get_reviews`, `run_db`, `run_redis_offloop`, `_get_redis_count`, `_get_user_tier_info`, `_get_active_referral_bonus`, `get_reviews_cache_key`, `REVIEWS_CACHE_TTL`, `usage_status`, the reader/pool names, UNION health importers (`/health`, `loop_lag`, `health_check`, `redis_offloop_pool`, `adapter_executor`), UNION the source-scanning pins (the named list + every test reading `app/` by path, 80 files), UNION `test_paid_route_metering.py`, UNION the CLAUDE.md readers `test_ci_gates.py`, `test_behavior_dimension_translation.py`; MINUS the four `test_precommit_hook*.py`; no SmartCompareApp scanner: no client-visible change; list `<scratchpad>/ST1/comm_set_full.txt`, sha256 prefix d906a267f735b6bc, builder `comm_set.py`), five chunks `chunk_00..04` of at most 24, bound 1200 each, base and head, `comm -13` of the sorted FAILED node ids EMPTY. Base chunk results so far:
   - `chunk_00`: 691 passed. `[pyt] tag=st1-base-comm00 start=2026-10-22 22:41:52 end=2026-10-22 22:43:30 elapsed=98s bound=1200s status=OK rc=0`; `[hermeticity] sentinel checked 691 test(s)`; `[netguard] blocked 4 attempt(s) from 2 node(s)` (`test_comparison_response_image_url.py::TestOrchestratorWiring::test_organic_results_passed_to_image_service` egress `api.openai.com:443`; `test_cron_reengagement.py::TestCronPagination::test_dispatch_called_when_payload_returned` sentinel `neutralized.supabase.invalid:443`; both baseline-class).
   - `chunk_01`: 991 passed. `[pyt] tag=st1-base-comm01 start=2026-10-22 22:43:37 end=2026-10-22 22:49:41 elapsed=364s bound=1200s status=OK rc=0`; `[hermeticity] sentinel checked 991 test(s)`; `[netguard] blocked 55 attempt(s) from 34 node(s)` (the ratchet-baseline egress nodes of `test_flush_live_price_key`, `test_genuine_price_priority`, `test_hermeticity_pins` (by design), `test_m13_01_slowapi_middleware`).
   - `chunk_02`: 618 passed, 23 skipped, 6 deselected, 1 xfailed, 2 errors = the known cold-tiktoken pair `tests/test_prompt_truth.py::test_truth_on_prefix_static_and_cacheable` and `::test_render_digests_match_base_except_the_fence` (box noise; record identically at head). `[pyt] tag=st1-base-comm02 start=2026-10-22 22:56:53 end=2026-10-22 22:57:20 elapsed=27s bound=1200s status=FAIL rc=1`; `[hermeticity] sentinel checked 621 test(s)`; `[netguard] blocked 2 attempt(s) from 2 node(s)` (the two `test_paid_route_metering.py` sentinel nodes of 1.10).
   - `chunk_03`: 1876 passed. `[pyt] tag=st1-base-comm03 start=2026-10-22 22:57:24 end=2026-10-22 23:00:40 elapsed=196s bound=1200s status=OK rc=0`; `[hermeticity] sentinel checked 1876 test(s)`; `[netguard] blocked 13 attempt(s) from 7 node(s)` (`test_security_hardening.py::TestSSRFProtection::test_exception_during_validation_blocked` egress `example.com`, and six `test_security_regression.py` nodes, egress/sentinel `api.openai.com:443` / `neutralized.supabase.invalid:443`; ratchet baseline).
   - `chunk_04`: 932 passed, 2 skipped, 6 deselected. `[pyt] tag=st1-base-comm04 start=2026-10-22 23:01:20 end=2026-10-22 23:02:04 elapsed=44s bound=1200s status=OK rc=0`; `[hermeticity] sentinel checked 933 test(s)`; `[netguard] blocked 7 attempt(s) from 2 node(s)`.
   - Base FAILED/ERROR node set over the whole comm set: exactly the two `test_prompt_truth.py` ERROR nodes above. GREEN's head set must equal it (`comm -13` empty).
5. Local-env hazard measurement (4.2 last paragraph): the 4.2 pin files once with `ENABLE_USAGE_PATH_OFFLOOP=true` exported on that one runner call; list the red nodes; edit none.
6. Mutation run (section 6), `.qa-mutation.lock`, bound 600 per mutant.

## 8. CLAUDE.md row and owner steps

### 8.1 The flag row (GREEN writes it after :477; wording may be tightened, content may not)

**SESSION 81 flag (ST1 LOOP-STALL, 2026-10-22; default OFF, read PER CALL; a new name, so unset in production by construction (Railway not read); spec `.qa-s80/ST1_UNIT_SPEC.md` of the unit worktree):**
- `ENABLE_USAGE_PATH_OFFLOOP` (ST1, reader `app/utils/redis_offloop.py::usage_path_offloop_enabled`; dispatchers `run_redis_offloop_pool` (the shared `redis-offloop` pool, whatever `ENABLE_PRICE_PATH_REDIS_OFFLOOP` says) and `app/utils/db_offload.py::run_db_offloop` (`asyncio.to_thread`, whatever `ENABLE_SYNC_DB_OFFLOAD` says)). **Problem (measured at 95cf6f86):** `usage_service.get_usage_status` (the `/usage/status` body, read on every Home and Paywall mount) ran its 3-4 Supabase round trips (users tier row, the lazy referral-bonus reset UPDATE when due, the active referral_redemptions sum) and 2 Upstash GETs serially ON the event loop whenever `ENABLE_SYNC_DB_OFFLOAD` is OFF (production), and neither `ENABLE_ASYNC_REDIS_OFFLOAD` nor the S77 flag reaches those GETs; production showed `/health` p95 8.4 s and `usage_status` p50 4.2 s with child I/O under 0.8 s (session-80 prod_evidence findings 8/9); `review_service.get_reviews` wrote its reviews L1 inline after every cold extraction. **Effect ON:** `get_usage_status` and `check_usage_allowed` (zero production callers) run the two Supabase reads as thread jobs (blocking twins `_tier_info_blocking` / `_active_bonus_blocking`, client build and lazy reset included) and the two GETs on the `redis-offloop` pool in ONE gather, then build the base response from the four values (pure `_usage_status_body` / `_usage_allowed_body`); `get_reviews` runs the L1 read and the three post-extraction L1 writes on the pool (writes durable and awaited, the L2 save scheduled before the first awaited write, a write dispatch failure logged by type and swallowed). A dispatch failure in the usage fork logs one WARNING `[USAGE-OFFLOOP] dispatch failed fn=<fn> type=<Type> -- inline fallback` and runs the base inline body (same response). **Flag OFF:** byte-identical (the base bodies run below a one-line flag check; pinned by `tests/test_s81_st1_usage_path_offloop.py` R9/R9b/R12/R13/R23/R25 with the full configuration and a call/thread recorder); `consume_comparison_credit`, `_refund_credit_sync`, every quota key and the S77 reader/pool are unchanged in both states (AST digests). No new response key, no new code; `/health` gains nothing (its existing `redis_offloop_pool` key appears once the pool exists). **Stated limits:** (1) the L2-promotion write stays inline (RO17 reorder class); (2) the auth half of `/usage/status` (revocation GET + `auth.get_user`) and the L2 reviews read stay on the loop until `ENABLE_ASYNC_REDIS_OFFLOAD` / `ENABLE_SYNC_DB_OFFLOAD`; (3) ONE FIFO pool: usage GETs and reviews writes queue behind `shopify_catalog` GETs under cold-compare load (S77 limit 3; measured FIFO waits 0.5-3.4 s for small reads), so the loop is freed but `/usage/status` latency may not drop under load; (4) Supabase twins run on the shared `qaren-worker` executor (96), beside the adapter fan-out; (5) a stalled Upstash/Supabase parks a thread for the client's own timeout (no new timeout); (6) `check_usage_allowed` ON reads both counters on the lifetime-free path (two extra GETs; no caller); (7) the twins log exception TYPES where the async helpers log text; (8) never set the flag in a local `.env`: S77 rows that pin the inline reviews read with the S77 flag OFF and tests that patch the async usage helpers go red (CI runs it unset); (9) fail-open on a Redis outage is unchanged (zero counts). **Precondition:** none to flip; ST1 is independent of `ENABLE_SYNC_DB_OFFLOAD`, which stays the precondition for every KB write (S81-17) and is canaried ON after approval in its own window; ST1 flips after approval, in its own window, after MS1 is recorded. **Canary:** `/health loop_lag_max_60s_ms` and p95, `usage_status` p50/p95 (Sentry), `redis_offloop_pool.queued` between compares (RO20), the `[USAGE-OFFLOOP]` WARNING count (expect 0), `[REDIS-OFFLOOP] pool built` once per process, the Upstash daily command count (unchanged expected). **Rollback:** unset the variable (per call, immediate).

### 8.2 In-place rewrites (principle 5; dated 2026-10-22)

- `CLAUDE.md:383` (`ENABLE_SYNC_DB_OFFLOAD` row), the sentence "Still deliberately left: off-path/cron/script sync-Supabase sites (off-clock by design), `usage_service.get_usage_status`/`check_usage_allowed`, `review_service` L1 get/set, and the behaviour-profile RPC (needs migration 037)." becomes "... off-path/cron/script sync-Supabase sites (off-clock by design) and the behaviour-profile RPC (needs migration 037); `usage_service.get_usage_status`/`check_usage_allowed` and the `review_service` L1 read + post-extraction writes moved under their own dark flag `ENABLE_USAGE_PATH_OFFLOOP` (ST1, 2026-10-22; see the SESSION 81 row)."
- `CLAUDE.md:385` (`ENABLE_PRICE_PATH_REDIS_OFFLOOP` row) stated limit (1): "the `review_service` post-extraction writes (the F3 ordering)" gains "(moved off the loop under `ENABLE_USAGE_PATH_OFFLOOP`, ST1)"; nothing else in the row changes.

### 8.3 Owner steps (names only)

1. After approval, MS1 recorded (Sentry 14 d `/health` and `usage_status` p50/p95, `loop_lag_max_60s_ms`).
2. Set `ENABLE_USAGE_PATH_OFFLOOP=true` on `web` (the owner's explicit yes, one change in the window); `price-warmer` needs nothing.
3. Watch the canary list of 8.1 for 48 h; rollback = unset.

## 9. Stated limits

L1 the L2-promotion write stays inline (RO17; Q2). L2 `/usage/status` auth half and the L2 reviews read stay on the loop (other flags). L3 one FIFO pool shared with the S77 catalog GETs (queue waits under load; Q3). L4 the Supabase twins share `qaren-worker` (96) with the adapter fan-out. L5 no new timeout: a stall parks a thread. L6 `check_usage_allowed` ON reads both counters on the lifetime-free path (no production caller). L7 twin logs carry the type, not the text (an observability change vs base, deliberate). L8 local-env hazard (4.2). L9 fail-open on Redis outage unchanged. L10 a dispatch failure falls back to the inline base path, which blocks the loop for that call. L11 a cancelled request can leave a running read or the lazy reset UPDATE finishing in its thread (idempotent within a reset window; two concurrent first reads after a past `reset_at` can both UPDATE, the same class as `ENABLE_SYNC_DB_OFFLOAD` ON at base). L12 the ON path computes the two date keys BEFORE the reads (base computes them after the Supabase reads, a few hundred ms later), so a call that straddles UTC midnight can read the old day's counter where base would read the new day's; the window is the read latency and only the displayed `used` / `remaining` move for that one call; no quota key changes (the date helper is unchanged; S81-09 owns the Riyadh change and must update both `get_usage_status` paths and `_usage_status_body`, a known rebase). L13 no latency claim without MS1; the probe proves loop freedom with fakes only. L14 the `[REDIS-OFFLOOP] pool built` line can now come from an ST1 dispatch.

## 10. Out of scope

`consume_comparison_credit`, `_refund_credit_sync`, any quota key or TTL (S81-09); the auth dependency of `/usage/status`; the L2 `product_data_service` reads (D1 / R0-7); `fetch_retailer_quotes` and `fetch_review_source_snippets` (dormant / flag-gated OFF); `_has_budget_async` (its own flag); a heartbeat log of in-flight route names when lag > 1 s and partial `stage_timings_ms` under `DEBUG_STAGE_TIMINGS` (in the panel plan's ST1 text, not in PLAN_S81 or the brief; Q4); a `/health` field for usage-path waits; a timeout on the usage reads; any client change.

## 11. Open questions for the orchestrator

- Q1 Independence. The spec makes ST1 independent of `ENABLE_SYNC_DB_OFFLOAD` and `ENABLE_PRICE_PATH_REDIS_OFFLOOP` with two flag-free twins (`run_db_offloop`, `run_redis_offloop_pool`), because routing through the existing `run_db` moves nothing while `ENABLE_SYNC_DB_OFFLOAD` is OFF and the brief says "ST1's flag is independent". Alternative: route the DB half through `run_db` (ST1 then only gathers the reads and moves the GETs; the DB half needs `ENABLE_SYNC_DB_OFFLOAD` ON first, the panel plan's "canary ENABLE_SYNC_DB_OFFLOAD alone first, then this flag"). Recommended: the spec's design.
- Q2 The L2-promotion write. RO17 kept it inline for the S77 pool (a durable FIFO job could land after a concurrent fresh write and leave the L2 copy in L1). The spec keeps it inline under ST1 too (one SET on the loop per L1-miss + L2-hit). Rule whether ST1 should move it anyway (accepting the reorder class) or keep RO17.
- Q3 The pool. The plan names the shared `redis-offloop` pool; under cold-compare load the usage GETs wait behind catalog GETs (S77 measured 0.5-3.4 s). Options: keep (spec), or a small dedicated lane (`usage-offloop`, 4 workers) in the same leaf module. Recommended: keep for ST1, re-read `redis_offloop_pool.queued` in the canary, open a lane unit if waits show.
- Q4 Scope additions from the panel plan (heartbeat in-flight route names, partial `stage_timings_ms`): confirm they belong to another unit (MS1 or a B1 telemetry follow-up), not ST1.
- Q5 Pin count. The spec moves NO existing pin (4.1 empty) where the brief expected two to move; confirm that the measured reading (1.9) is accepted.

## Not done in this spec

No code, no RED file, no CLAUDE.md edit; no mutation run; the ON-state satisfiability prototype of section 5 was not built (the RED author builds it in place with byte copies); no production, Railway or Supabase read; the panel scope items of Q4 not designed; the local-env hazard list of 4.2 not measured (GREEN measures it).
