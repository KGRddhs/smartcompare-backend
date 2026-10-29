# S81-09 DEVICE-QUOTA-RIYADH -- unit spec (lane B backend, two dark flags)

- Unit: S81-09 DEVICE-QUOTA-RIYADH (PLAN_S81 M3; PLAN_S81.md :148 unit text, :102-104 design-panel grafts, :194 owner decision 2, :201 owner decision 5, :185 flip order). Spec writer: Opus 5.5 agent, 2026-10-29 11:10-12:40 AST.
- Flags: `ENABLE_DEVICE_DAILY_QUOTA` and `ENABLE_RIYADH_RESET` (new names, default OFF, read PER CALL with the house idiom; unset in production by construction).
- Worktree: C:/Users/SynAckITPC/Documents/AI/sc-s81-s09 (detached). Branch for GREEN: feature/s81-s09-device-quota-riyadh.
- Base: e7c81956f11749b1378aa449c4ac616c82bfe6a9 (= origin/main after #376). `git status --short` EMPTY before and after every probe (measured 11:17 and at the end).
- Evidence pointers: notes, the probe and its output under <scratchpad>/S81-09_spec/ (notes.md, probe_base_sequences.py, base_sequences.json sha256 94d779be1cbaa1cec1ec4f5c960a50494c27c0096528dcdf0306534869f99e43, base_a.log, base_b.log, comm_seed.txt), where <scratchpad> = C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/fe82d828-54b9-4af1-9c1d-685173488382/scratchpad. This file was written THROUGH THE SHELL (the harness refuses a subagent Write of a report .md).
- Binding inputs read in full: s81-common.txt, PLAN_S81.md, specs/S81_09_BRIEF.md, RULINGS_S81_08 (R-S08-2 / -13 / -14) + RULINGS_FIX1_S81_08 (F1-8 = Q8) + GATE_S81_08 (GC-2, GC-5), RULINGS_S81_05 (+FIX1, GATE GC-2), RULINGS_S81_08B, RULINGS_ST1 (R-ST1-3 / -5), RULINGS_S81_12 (R-S12-9, R-S12-14) + the S81-12 spec E24 / D5, DEFECT_LEDGER rows S81-05 / S81-08b / S81-08d / S81-09, PLAN_S80 section 0 contract freeze (refusals only through envelopes build 3 renders; new keys additive; never a bare 503).
- Sister units and contracts: S81-05 (merged #371; the leaf app/utils/request_context.py: device_fingerprint(), header_state(), device_key(); NO middleware change here), S81-04 (merged #372; llm_spend_breaker riyadh_day + _eval, the EVAL precedent), ST1 (merged #370; the ONE compute body _usage_status_body, the r25 digest pins), S81-08b (merged #375; lifetime inheritance), S81-08 (client, in flight: reads counted_scope / remaining.<axis> / resets_at / scope / retry_after_seconds), S81-12 (LEGAL-V3, HELD PR: the dormant device texts selected by DEVICE_QUOTA_RESET; E24 = D11 re-pinned at this unit's flip), S81-10 (lane A, known rebase on text_routes consume sites), S81-22 (never makes compare_request_id UNIQUE; not touched), S81-08d (after this unit).
- Personal-data rule: no real name, email, phone, account id, device id or address anywhere; every id, fingerprint and pepper in tests is synthetic and built at run time (uuid shapes like 00000000-0000-4000-8000-0000000000a1, fingerprints as "a" * 64 / "b" * 64, the pepper by concatenation); the exempt-list VALUE is never written to any file (name only).

## 0. What the unit does

Today (base) the freemium gate counts per ACCOUNT only, on UTC dates: `usage:daily:<uid>:<UTC date>` (cap 3), `usage:monthly:<uid>:<UTC month>` (cap 10 + referral bonus), plus a lifetime-free bypass for the first 3 comparisons ever. Nothing counts per device; the reset is 00:00 UTC (03:00 Bahrain).

Under `ENABLE_DEVICE_DAILY_QUOTA` (free tier, not exempt) the gate becomes owner decision 2 as grafted by the plan: 3 per DEVICE per day (the S81-05 HMAC device key of the request X-Device-Fingerprint) AND 3 per ACCOUNT per day, debited together by ONE Upstash Lua EVAL that checks the device first, with EXPIREAT the next reset + 1 h; the monthly cap, the referral-bonus extension and the lifetime-free bypass are retired for that path (a fresh account on a capped device gets nothing: the anti-farming point). Refusals stay the existing 429 USAGE_LIMIT envelope and gain three additive fields (retry_after -> the existing handler emits retry_after_seconds + Retry-After; resets_at and scope through a flag-gated allow-list). /usage/status gains remaining.device_daily, resets_at and counted_scope (R-S08-2, F1-8). A missing or garbage header (build 3) is account-only plus one constant metric line, never a 400. Premium and the env allow-list are exempt (the base path, byte-identical).

Under `ENABLE_RIYADH_RESET` ONE date helper moves every usage date key (daily, previous daily, monthly, previous monthly; the quota path and status alike) to the Asia/Riyadh calendar (fixed +03:00; owner decision 5); the quota path then resets at 00:00 Riyadh (21:00 UTC). Flag OFF: UTC keys byte for byte.

Both flags OFF (five spellings): every Redis call (method, key, args, TTL, order), every response body and every log line equal to base, pinned by a committed golden fixture recorded at base under the full configuration (B1 rule).

## 1. Base state (MEASURED at e7c81956)

### 1.1 usage_service.py (839 lines, CRLF, UTF-8 with non-ASCII in comments)

| Symbol | Line | Measured behaviour |
|---|---|---|
| `_DEVICE_FINGERPRINT_RE`, `anon_usage_gate_enabled`, `valid_device_fingerprint` | :23, :26, :37 | anon helpers; `.match` (accepts a trailing LF: pinned by test_s81_s05 p06); UNTOUCHED |
| `check_anon_usage_allowed` / `refund_anon_comparison_credit` | :45 / :130 | anon gate on `anon:<fp>` keys via `_atomic_consume_async` / `refund_comparison_credit`; UNTOUCHED (it inherits the date helper, 2.2) |
| `TIER_LIMITS` | :139-150 | free lifetime_free 3 / monthly 10 / daily 3; premium 0 / 70 / 10; UNCHANGED (legal parity pins) |
| `_daily_key` / `_monthly_key` | :153 / :158 | `datetime.now(timezone.utc).strftime("%Y-%m-%d")` / `"%Y-%m"` |
| `_previous_daily_key` / `_previous_monthly_key` | :163 / :171 | UTC yesterday / UTC last month (refund fallback windows) |
| `_get_redis_count` | :178 | GET, int, any error -> 0 |
| `_safe_expire` | :188 | EXPIRE; on failure WARNING `[usage] TTL set failed for %s: %s` (logs the KEY and the exception text) |
| `_ConsumeOutcome`, `_atomic_consume` | :202, :236 | INCRBY daily (EXPIRE 86400 when ==1; DECRBY + return 'daily_limit' when > cap), INCRBY monthly (EXPIRE 2764800 when ==1; DECRBY both when > cap); any exception -> WARNING `[usage] atomic consume failed for %s: %s -- fail-open` (user id + text) and None |
| `_atomic_consume_async`, `_get_redis_count_async`, `_bump_counters_async` | :293, :301, :308 | the #115 dispatch: `asyncio.to_thread` iff `_redis_offload_enabled()` (ENABLE_ASYNC_REDIS_OFFLOAD), else inline |
| `consume_comparison_credit(user_id, access_token)` | :332-431 | gather(tier info, active bonus) :351; lifetime-free branch :361 (bump both counters, no cap); else `_atomic_consume_async` :386; daily refusal re-reads monthly by GET :394; returns allowed/reason/tier/consumed/consumed_keys/remaining |
| `_refund_one_window` / `_refund_credit_sync` | :434 / :473 | GET-before-DECRBY floor at zero; with consumed_keys exact (daily, monthly), without them today + previous window (:485-486) |
| `refund_comparison_credit(user_id, consumed_keys=None)` | :489 | dispatch per ENABLE_ASYNC_REDIS_OFFLOAD; any error -> WARNING `[usage] refund failed for %s: %s` |
| `record_lifetime_comparison` | :509 | Supabase RPC increment_lifetime_comparisons (fire-and-forget by the routes) |
| `_get_user_tier_info`, `_maybe_reset_referral_bonus`, `_get_active_referral_bonus` | :520, :548, :589 | one users select (+ lazy bonus reset); one referral_redemptions select |
| `_usage_reads_offloop`, `check_usage_allowed`, `_usage_allowed_body` | :619, :653, :695 | ST1; `check_usage_allowed` has NO caller in app/ (grep: only usage_service itself) |
| `get_usage_status` / `_usage_status_body` | :774 / :801 | ST1 first statement `if usage_path_offloop_enabled():`; the ONE compute body (R-ST1-3); key order tier, used{daily,monthly,lifetime}, limits{daily,monthly,monthly_base,monthly_bonus,lifetime_free}, remaining{daily,monthly,lifetime_free} |

`to_thread` occurs 4 times in usage_service.py (pinned by test_s81_st1 r25a). None of the touched app files is in .github/black-clean-paths.txt (grep: only the S81-05 files are), so no black gate applies.

### 1.2 The consume / refund call graph (every caller; grep over app/ and scripts/)

| Route (file:line) | Consume | USAGE_LIMIT detail | Refund call(s) |
|---|---|---|---|
| POST /api/v1/text/compare (text_routes.py :578) | :619 `consume_comparison_credit(user["id"], user.get("access_token", ""))` | :621-629 {error, code, tier, remaining} | :677 `refund_comparison_credit(user["id"])` (before `_surface_comparison_failure`) |
| GET /api/v1/text/compare | :836 | :838-846 | :885 |
| GET /api/v1/text/compare/stream (event_generator closure) | :1023 | :1025-1033 | :1323 (had_error), :1354 (incomplete / client gone) |
| POST+GET /api/v1/url/compare (url_routes.py `_reserve_comparison_credit` :71, only under ENABLE_PAID_ROUTE_METERING :84) | :89 | :91-99 | :259 (exception), :273 (failure) |
| POST /api/v1/image/identify (image_routes.py, under ENABLE_PAID_ROUTE_METERING :323) | :324 | :327-336 | :301 inside the at-most-once closure `_refund_reserved_credit` :288 |
| GET /api/v1/usage/status (usage_routes.py :9-15) | -- | -- | -- (calls `get_usage_status(user_id=, access_token=)`) |
| anon gates (image :227-243, text :1407-1416) | `check_anon_usage_allowed(device_fp)` | anon details | `refund_anon_comparison_credit(device_fp, anon_consumed_keys)` (image) -- OUT OF SCOPE |

MEASURED FACT that shapes section 2.6: none of the seven authenticated refund calls passes `consumed_keys`; every one takes the no-keys fallback (`_refund_credit_sync(uid, None)`: today then previous window). The only consumed_keys carrier at base is the anon path in image_routes (:243 / :320).

The device fingerprint is read from the request in exactly two route places today, both for the anon gate: `valid_device_fingerprint(request.headers.get("x-device-fingerprint"))` once in image_routes.py (:228) and once in text_routes.py (pinned to count 1 each by test_s81_s05 p07); auth_routes reads `X-Device-Fingerprint` once (register / social).

### 1.3 The golden base: Redis call lists measured at base

Probe: probe_base_sequences.py (pinned venv, `-I`, cwd = the worktree, no network: `usage_service.redis_client` replaced by a recorder, `usage_service.datetime` by a frozen clock, the two Supabase helpers stubbed; the m18 FakeDatetime pattern). Clock 2026-10-29T20:30:00Z unless noted; D = `usage:daily:<uid>:2026-10-29`, M = `usage:monthly:<uid>:2026-10`. Output base_sequences.json (sha above).

| Scenario | Base Redis calls (in order) | Base result (abridged) |
|---|---|---|
| consume, free, lifetime 0 (lifetime-free branch) | incrby D 1; expire D 86400; incrby M 1; expire M 2764800 | allowed, consumed, keys {daily D, monthly M}, remaining {daily 3, monthly 10, lifetime_free 3} |
| consume, free, lifetime 5, counts 0 | incrby D 1; expire D 86400; incrby M 1; expire M 2764800 | allowed, remaining {2, 9, 0} |
| consume, free, D=3 (daily refusal) | incrby D 1; decrby D 1; get M | reason daily_limit, consumed False, remaining {0, 7, 0} |
| consume, free, M=10 (monthly refusal) | incrby D 1; expire D 86400; incrby M 1; decrby M 1; decrby D 1 | reason monthly_limit, remaining {3, 0, 0} |
| consume, premium, bonus 4 | as the free paid row | remaining {9, 73, 0}, tier premium |
| consume, redis_client None | none | allowed, consumed True, keys {D, M}, remaining {3, 10, 0} (fail-open; no log) |
| refund, no keys, D=1 M=1 | get D; decrby D 1; get M; decrby M 1 | -- |
| refund, no keys, at 2026-10-30T00:00:30Z (prev day) | get D(10-30); get D(10-29); decrby D(10-29) 1; get M; decrby M 1 | -- |
| refund, keys {D, M} | get D; decrby D 1; get M; decrby M 1 | -- |
| status free lifetime 1 (D=3 M=9) | get D; get M (ST1 OFF) | {"tier":"free","used":{"daily":3,"monthly":9,"lifetime":1},"limits":{"daily":3,"monthly":10,"monthly_base":10,"monthly_bonus":0,"lifetime_free":3},"remaining":{"daily":3,"monthly":10,"lifetime_free":2}} |
| status premium bonus 4 (D=5 M=20) | get D; get M | the ST1 BASE_ROUTE premium_bonus literal |

No log line from usage_service in any of these scenarios. Key helpers at 2026-10-29T20:59:59Z and at 21:00:00Z (UTC base): daily 2026-10-29, previous 2026-10-28, monthly 2026-10, previous 2026-09 (identical either side of 21:00 UTC: the base never resets at Riyadh midnight). ST1 already holds base literals for consume / refund / route bodies (tests/test_s81_st1_usage_path_offloop.py BASE_CONSUME_SEQ :738, BASE_REFUND_SEQ :979, BASE_ROUTE :996): the golden of this unit re-records the same scenarios under the S81-09 full configuration.

### 1.4 The USAGE_LIMIT envelope and the handler (app/middleware/error_handler.py, 286 lines)

- `STATUS_CODE_MAP` :24; `_URL_V2_PASSTHROUGH_CODES` :40 (a tuple; B4-R5 scoped allow-list); `_url_mode_v2_keys_enabled()` :43 (a local one-liner reading ENABLE_URL_MODE_V2: "the middleware never imports a service").
- `_is_structured_detail` :90; `_detail_retry_after` :110-126 (a positive int `retry_after` only; bool / str / float / <= 0 -> None).
- `http_exception_handler` :129-168: content = {success False, error, code, request_id} :149-154; the B4 block :157-163 (flag read FIRST, code in the tuple, str values only for `field` / `reason`); then `retry_after_seconds` + `Retry-After` header :164-167 for a 429 whose detail carries a usable `retry_after` (W1-9, UNFLAGGED). So a USAGE_LIMIT detail that gains `retry_after` (int) gets `retry_after_seconds` + `Retry-After` with NO handler change; `resets_at` / `scope` are dropped today (tier / remaining too).
- Base wire body of the authenticated USAGE_LIMIT 429: {"success": false, "error": "Comparison limit reached (daily_limit)", "code": "USAGE_LIMIT", "request_id": <id>}, no Retry-After.
- B4 pins over the handler: tests/test_s80_url_mode_v2.py `test_error_handler_passthrough_on` and `test_error_handler_four_key_body` (:1242-1282; a 400 mini app; scope = the three B4 codes): untouched by a USAGE_LIMIT-scoped block.

### 1.5 The S81-05 leaf (app/utils/request_context.py, 312 lines, stdlib only)

`request_context_headers_enabled()` :115 (ENABLE_REQUEST_CONTEXT_HEADERS); `HEADER_DEVICE_FINGERPRINT = b"x-device-fingerprint"` :77; `STATE_ABSENT/MALFORMED/OK` :85-87; `device_fingerprint()` :164 (None unless the middleware bound a valid value); `header_state(name)` :190 (constant strings, never raises; "absent" outside a bound request and whenever the middleware flag is OFF; GATE_S81_05 GC-2: an empty header is "malformed"); `device_key(fp)` :298 = HMAC-SHA256(DEVICE_KEY_PEPPER stripped, fp) 64 lower-case hex, None on an invalid fp or a missing / blank / non-UTF-8 pepper (ONE constant WARNING per process). The middleware (app/middleware/request_context.py :31-39) binds per HTTP request and resets in finally; a task created inside the request (fire_and_forget) keeps the snapshot taken at its creation. Pins: tests/test_s81_s05_request_context.py (p06 the anon readers, p07 the route header-read needles, p08 no dual-hash names, p19/p20 header_state). Leaf rule: "never logged anywhere: a header value, the pepper, a device key".

### 1.6 The EVAL precedent (app/services/llm_spend_breaker.py, S81-04)

`RIYADH_UTC_OFFSET_HOURS = 3` :132, `KEY_GRACE_SECONDS = 3600` :134; `RECORD_SCRIPT` / `RESERVE_SCRIPT` :166-179 (single-key Lua: `tonumber(redis.call('GET', KEYS[1]) or '0')`, INCRBYFLOAT, EXPIREAT ARGV); `riyadh_day(now)` :337-351 returns (Riyadh day YYYY-MM-DD, EXPIREAT epoch = next Riyadh midnight + 3600), docstring "S81-09 may move it to a shared helper"; `_eval(client, script, keys, args)` :971-977 = the two client shapes (upstash-redis 1.7.0 `eval(script, keys=, args=)` when `type(client).__module__` starts with "upstash_redis", else redis-py 8.1.0 `eval(script, numkeys, *keys, *args)`). Pins that forbid MOVING them: tests/test_s81_s04_spend_breaker.py r01 (:618, the leaf top-level import set `_APP_OK` :614; a new app import in the leaf goes red) and r05 (:738, `riyadh_day` read from the leaf). llm_spend_breaker imports cache_service, llm_pricing, openai_pricing, async_utils (none imports usage_service: no cycle).

### 1.7 Flag idiom, libraries, environment

- Idiom (measured in usage_service :29, text_routes :212, request_context :117, llm_spend_breaker :286): `os.getenv(NAME, "false").strip().lower() in ("true", "1", "yes", "on")`, read per call.
- zoneinfo on the pinned venv: `zoneinfo.ZoneInfo("Asia/Riyadh")` raises ZoneInfoNotFoundError (MEASURED; `tzdata` is in neither requirements.txt nor requirements-dev.txt; no app/ module uses zoneinfo). A fixed +03:00 offset needs no package.
- The production Redis client is `cache_service.redis_client` (upstash-redis REST, or redis-py on a redis:// URL); usage_service imports the NAME at module import (:14) and every usage test patches `usage_service.redis_client`.
- Production flag state (newest dated ledger lines, session-81 ledger :59 and the DEFECT_LEDGER S81-05 row): ENABLE_REQUEST_CONTEXT_HEADERS OFF on main ("flips in the post-approval window before S81-09"); DEVICE_KEY_PEPPER "the owner's to set by name": NO dated line records it set (UNKNOWN; an owner step). ENABLE_PAID_ROUTE_METERING ON in production (the brief; CLAUDE.md). ENABLE_ASYNC_REDIS_OFFLOAD / ENABLE_USAGE_PATH_OFFLOOP: no ON line found (design for both states).

### 1.8 Guards the new code must not trip (measured pins)

- tests/test_s81_st1_usage_path_offloop.py r25a (:1989): `get_usage_status` and `check_usage_allowed` keep `if usage_path_offloop_enabled():` as their FIRST statement; usage_service `to_thread` count == 4 (:2035); r25b (:2039-2045) AST digests of 28 functions incl. `_daily_key`, `_monthly_key`, `_previous_daily_key`, `_previous_monthly_key`, `consume_comparison_credit`, `refund_comparison_credit`, `_refund_credit_sync`, `TIER_LIMITS` (BASE_DIGESTS :1032); r27 the route bodies (BASE_ROUTE :996).
- tests/test_s81_s05_request_context.py p06 (:1572, anon readers unchanged), p07 (:1590, the route header-read needle count 1 in image_routes and text_routes; a route that reads the header itself goes red), p08.
- tests/test_legal_disclosure_s77.py D11 (:807-829, TIER_LIMITS free (3, 10, 3) == Terms s4 numbers); tests/test_register_benefits_parity_s69.py (TIER_LIMITS read by ast; the client register benefits state 3/day and 10/month).
- tests/test_s80_url_mode_v2.py R32 handler rows; tests/test_429_contract.py, tests/test_retro_w1_9.py, tests/test_retro_w1_9_429.py (the W1-9 retry_after contract).
- Line endings: every touched app file is CRLF in the working copy (`file`: usage_service.py, error_handler.py, text_routes.py "with CRLF line terminators"); the Edit tool keeps them; a whole-file diff is a defect. New code lines are ASCII.

### 1.9 Client fences that read backend files by path

Of the fourteen SmartCompareApp suites that join a repo-root path, none reads a file this unit touches: honestCounts.s69 names app/services/usage_service.py in a COMMENT only (:7) and reads client src (:63-64); landing.domain.s76 reads robots_eval.py; the others read app/services/{attribution,...} files not in this footprint. No junction is needed (the orchestrator may still run them at GREEN per the common rule, since the footprint touches app/; not required by any literal this unit moves).

### 1.10 Base pass state (bounded runner, the shared .venv-qaren)

- Set A (17 files: test_usage_service_internals, test_usage_tiers, test_usage_referral_bonus, test_usage_device_inheritance, test_m18_usage_symmetry, test_m13_37_freemium_atomic_consume, test_m18_preverdict_disconnect_refund, test_paid_route_metering, test_s81_st1_usage_path_offloop, test_s81_s05_request_context, test_legal_disclosure_s77, test_register_benefits_parity_s69, test_429_contract, test_retro_w1_9, test_retro_w1_9_429, test_error_middleware, test_image_identify_llm_unavailable_s69): 899 passed. `[pyt] tag=s09spec-base-a start=2026-10-29 11:35:34 end=2026-10-29 11:36:43 elapsed=69s bound=1200s status=OK rc=0`; `[hermeticity] sentinel checked 899 test(s)`; `[netguard] blocked 2 attempt(s) from 2 node(s)` (test_paid_route_metering camera_success / url_compare_saves_history: socket.create_connection neutralized.supabase.invalid:443, the sentinel host; base noise, record identically at head).
- Set B (10 files: test_s80_url_mode_v2, test_s81_s04_spend_breaker, test_s81_s08b_legacy_fingerprint, test_s81_s08b_gate_rows, test_text_routes_error_mapping, test_s81_s06_anthropic_router, test_cron_expire_bonuses, test_referral_expiry, test_retro_w2_1, test_shutdown_drain): 1352 passed. `[pyt] tag=s09spec-base-b start=2026-10-29 11:36:55 end=2026-10-29 11:40:01 elapsed=185s bound=1200s status=OK rc=0`; `[hermeticity] sentinel checked 1352 test(s)`; `[netguard] blocked 25 attempt(s) from 3 node(s)` (s04 r42 / p08 and text_routes_error_mapping timeout row: the same sentinel host; base noise).
- NOT MEASURED here: the full comm set (99-file seed, 7.3) as a base record (the RED records it, the S81-08b precedent).

## 2. Contract

### 2.1 Flags and knobs (names; defaults; clamps; all read per call in usage_service unless stated)

| Name | Kind | Default | Parse |
|---|---|---|---|
| `ENABLE_DEVICE_DAILY_QUOTA` | flag | OFF | house idiom; `device_daily_quota_enabled()`; error_handler reads the SAME name through its own local one-liner `_device_quota_keys_enabled()` (the B4 precedent: the middleware never imports a service) |
| `ENABLE_RIYADH_RESET` | flag | OFF | house idiom; `riyadh_reset_enabled()` |
| `DEVICE_DAILY_QUOTA_CAP` | knob | 3 | `device_daily_cap()`: strip; a decimal int (no sign, no bool) in 1..10; unset / blank / garbage / "2.5" / "true" / <= 0 -> 3; > 10 -> 10. Read per consume and per status |
| `DEVICE_QUOTA_EXEMPT_USER_IDS` | knob | empty | `_device_quota_exempt(user_id)`: split on commas and whitespace, strip, lower-case; keep only canonical uuid-shaped tokens (8-4-4-4-12 hex); at most the first 50 valid tokens; compared with `user_id.lower()`; unset / blank -> nobody. The value is never logged and never written to a file |
| `DEVICE_KEY_PEPPER` | S81-05 | -- | read by `request_context.device_key` per call (already in tests/_env_safety.CREDENTIALS_UNSET) |

The account-daily cap under the flag is `TIER_LIMITS["free"]["daily"]` (3, unchanged); `TIER_LIMITS` is not edited (the legal parity pins). Neither new knob is a credential, so tests/_env_safety.CREDENTIALS_UNSET is unchanged (DEVICE_KEY_PEPPER is already there, S81-05); the unit keeps no process memo, so tests/conftest.py needs no reset hook (the S78-SM precedent does not apply); the hermeticity sentinel and the netguard run unchanged over the RED file (no socket, no Supabase, no Upstash).

### 2.2 The ONE date helper (ENABLE_RIYADH_RESET)

`_usage_window(now=None) -> (day: date, next_reset: datetime)`: `now` defaults to `datetime.now(timezone.utc)` through the module global `datetime` (so the existing FakeDatetime patches of `usage_service.datetime` keep working); only real-datetime arithmetic on that value (never `datetime(...)` construction through the module global). Flag OFF: `day = now.date()`, `next_reset = now.replace(hour=0, minute=0, second=0, microsecond=0) + 1 day` (next UTC midnight). Flag ON: `local = now + 3 h`; `day = local.date()`; `next_reset = local.replace(hour=0, ...) + 1 day - 3 h` (the next 00:00 Asia/Riyadh as an aware UTC instant, i.e. 21:00 UTC). Next reset is STRICTLY after now (at exactly 21:00:00Z ON it is the following 21:00Z).

Users (all through the helper): `_daily_key(uid)` = "usage:daily:%s:%s" % (uid, day:%Y-%m-%d); `_previous_daily_key` = day - 1; `_monthly_key` = day:%Y-%m; `_previous_monthly_key` = (day.replace(day=1) - 1 day):%Y-%m; the quota path keys, EXPIREAT, retry_after, resets_at; the device status. Flag OFF strings are byte-identical to base (MEASURED key table 1.3). The anon gate inherits the helper through `_daily_key` / `_monthly_key` (one day definition; ENABLE_ANON_USAGE_GATE is OFF). Q3 answered: fixed +03:00 (no DST in Asia/Riyadh; zoneinfo MEASURED unavailable on the pinned venv); a drift pin (R30) proves `day` and `int(next_reset.timestamp()) + 3600` equal `llm_spend_breaker.riyadh_day(now)` under the flag, so the two Riyadh days can never diverge without a red row. riyadh_day is NOT moved (S81-04 r01 / r05).

### 2.3 Keys, TTLs and the device key

- Account daily: `usage:daily:<uid>:<day>` (the same string `_daily_key` returns). Device daily: `usage:device:<device_key>:<day>` where device_key = `request_context.device_key(device_fp)` (64 lower-case hex HMAC; the raw fingerprint never appears in a key, an argument or a log).
- Quota path TTL: `EXPIREAT next_reset_epoch + 3600` on BOTH keys at every successful debit (the Riyadh day + 1 h under RIYADH ON, the UTC day + 1 h under OFF: Q7). The base path keeps EXPIRE 86400 / 2764800 on first INCR (unchanged even under RIYADH ON: a Riyadh-dated key created at 23:59 local still outlives its day).
- No monthly key, no bonus read on the quota path.

### 2.4 The two Lua scripts (module constants, pinned as literals by the RED)

DEVICE_CONSUME_SCRIPT (KEYS = [account_daily] or [account_daily, device_daily]; ARGV = [account_cap, device_cap, expireat] as decimal strings):

```
local a = tonumber(redis.call('GET', KEYS[1]) or '0')
local d = 0
if #KEYS > 1 then
  d = tonumber(redis.call('GET', KEYS[2]) or '0')
  if d >= tonumber(ARGV[2]) then return {2, a, d} end
end
if a >= tonumber(ARGV[1]) then return {1, a, d} end
if #KEYS > 1 then
  d = redis.call('INCR', KEYS[2])
  redis.call('EXPIREAT', KEYS[2], ARGV[3])
end
a = redis.call('INCR', KEYS[1])
redis.call('EXPIREAT', KEYS[1], ARGV[3])
return {0, a, d}
```

Reply: a list of three ints [code, account_count, device_count]; code 0 = debited (counts after), 1 = account refused, 2 = device refused (counts unchanged, nothing written). The device is checked and incremented FIRST (graft :102). A refusal writes nothing, so no rollback write exists.

DEVICE_REFUND_SCRIPT (KEYS = the debited keys; no ARGV):

```
local out = {}
for i, k in ipairs(KEYS) do
  local v = tonumber(redis.call('GET', k) or '0')
  if v > 0 then out[i] = redis.call('DECR', k) else out[i] = -1 end
end
return out
```

Atomic floor-at-zero for both keys; never creates a key; no TTL write (the key keeps its EXPIREAT). Both scripts run through `llm_spend_breaker._eval(redis_client, script, keys, args)` (Q4: reuse the client-shape helper; imported as a module inside the flag-ON arm so flag OFF never imports it; the scripts are usage-local because their semantics differ from the spend lanes). Upstash multi-key EVAL is REASONED, not measured (Upstash databases are not clustered; a CROSSSLOT refusal would surface as the fail-open metric on the first canary compare: stated limit L4).

### 2.5 consume_comparison_credit(user_id, access_token, *, device_fp=None)

Signature: the keyword-only `device_fp` is added (graft :102). Every caller passes it ONLY under the flag through `**device_quota_kwargs()` (usage_service: `{}` when the flag is OFF, else `{"device_fp": request_context.device_fingerprint()}` read on the request path before any offload). Flag OFF the call is `consume_comparison_credit(uid, token)` exactly (pinned by a call recorder at all five sites).

Body: the base gather (tier info + active bonus, :351) runs first in both states (identical Supabase I/O); then `if device_daily_quota_enabled() and tier == "free" and not _device_quota_exempt(user_id): return await _consume_device_quota(user_id, device_fp)`; otherwise the base body from :354 runs unchanged (premium, the allow-list and flag OFF). The allow-list is read only when the flag is ON and the tier is free (short-circuit).

`_consume_device_quota` (free, not exempt), one clock read `now`:
1. `dk = request_context.device_key(device_fp)` when `device_fp` is truthy, else None. When `dk` is None: ONE INFO line `[USAGE-DEVICE] account-only header=%s` with `request_context.header_state(request_context.HEADER_DEVICE_FINGERPRINT)` (a constant: absent / malformed / ok; ok = a valid header the pepper could not key). Never a 400, never a response change (Q5).
2. `day, next_reset = _usage_window(now)`; keys per 2.3; `expireat = int(next_reset.timestamp()) + 3600`; `cap_a = TIER_LIMITS["free"]["daily"]`; `cap_d = device_daily_cap()`.
3. ONE EVAL of DEVICE_CONSUME_SCRIPT through the #115 dispatch (`asyncio.to_thread` iff ENABLE_ASYNC_REDIS_OFFLOAD; one new shared helper `_offload_dispatch_async(fn, *args)`).
4. Results (key order as base; `remaining.device_daily` LAST and only when `dk` exists; monthly reported as the non-binding base cap):

| Outcome | Return |
|---|---|
| code 0 | {"allowed": True, "reason": None, "tier": "free", "consumed": True, "consumed_keys": {"daily": A, "device_daily": DV (only with dk)}, "remaining": {"daily": max(0, cap_a - a), "monthly": 10, "lifetime_free": 0, "device_daily": max(0, cap_d - d)}} and the request-scoped debit stash is set (2.6) |
| code 1 | {"allowed": False, "reason": "daily_limit", "tier": "free", "consumed": False, "remaining": {"daily": 0, "monthly": 10, "lifetime_free": 0, "device_daily": ...}, "retry_after": R, "resets_at": S, "scope": "daily"} |
| code 2 | same with "reason": "device_daily_limit", "scope": "device_daily", remaining.daily = max(0, cap_a - a), remaining.device_daily = 0 |
| redis_client None | {"allowed": True, "reason": None, "tier": "free", "consumed": False, "remaining": {"daily": cap_a, "monthly": 10, "lifetime_free": 0}}; no log (base logs nothing here either); no stash |
| EVAL raises, or the reply is not a 3-int list | the same fail-open dict, ONE WARNING `[USAGE-DEVICE] consume fail-open type=%s` (the exception type name, or the constant BadReply); no stash (L3) |

R = `ceil((next_reset - now).total_seconds())`, in 1..86400 (int); S = `next_reset` rendered in the reset zone with `isoformat(timespec="seconds")`: RIYADH ON "YYYY-MM-DDT00:00:00+03:00", OFF "YYYY-MM-DDT00:00:00+00:00" (Q7). Both point at the same instant, so the client reading retry_after_seconds first (GC-2) and the one reading resets_at agree to the second. "monthly": 10 is `TIER_LIMITS["free"]["monthly"]`: the monthly axis is retired, reported as never binding (build 3 needs a number on both axes, 2.7). `consumed: False` on fail-open (nothing was debited, so the routes refund nothing; the base path keeps its consumed True).

### 2.6 Refund (the device key inside consumed_keys)

Measured: the seven authenticated refund calls pass no consumed_keys (1.2). Design (Q10, default): `_consume_device_quota` stores a request-scoped debit record in a module ContextVar `_DEVICE_DEBIT` (a small object holding user_id, the consumed_keys dict and a `refunded` latch; set only on code 0). `refund_comparison_credit(user_id, consumed_keys=None)` gains ONE first block: `keys = _device_refund_keys(user_id, consumed_keys)` where `_device_refund_keys` returns None when the flag is OFF (its FIRST statement; no ContextVar read OFF), the explicit keys when they carry "device_daily", else the stash when it exists, matches user_id and is not yet refunded (the latch is set on the loop, before any offload, so a second refund for the same debit is a no-op). With keys: ONE EVAL of DEVICE_REFUND_SCRIPT over [daily, device_daily (when present)] through `_offload_dispatch_async`; any error -> ONE WARNING `[USAGE-DEVICE] refund failed type=%s`; never raises. Without keys: the base body unchanged (premium, the allow-list, a fail-open consume, flag OFF).

Why not `_refund_credit_sync` (plan wording "taught the device key"): `_refund_one_window` race-compensates with `_safe_expire`, whose failure WARNING logs the Redis KEY (it would log the device key: S81-05 forbids it) and the exception text; the EVAL is atomic (no GET->DECR race) and logs a type name only; `_refund_credit_sync` and its ST1 BASE_REFUND_SEQ stay byte-identical. Exactness: the refund credits exactly the keys the consume debited (same day stamps), so a midnight crossing needs no fallback (the debited key lives until its reset + 1 h); the fallback with `_previous_daily_key` (Riyadh-yesterday under RIYADH ON) still serves the base path (premium / allow-list) and the RIYADH transition. A route that refunds a user that the stash does not name (none exists) falls to the base path. Context propagation (REASONED from the S81-05 leaf rule :49-53 and Starlette's StreamingResponse task group, proven on the real app by R16 incl. the stream had_error case and R34): fire_and_forget tasks copy the request context at creation; the stream finally runs in the response task created after the endpoint returned; both see the stash set by the awaited consume.

Alternative R1 (rejected by default, Q10): pass `consumed_keys` explicitly at the seven refund sites under the flag (+ `_reserve_comparison_credit` returning the keys): more route churn in lane A files, one mutant per site, same behaviour.

### 2.7 /usage/status under the flag (R-S08-2, R-S08-13, F1-8 = Q8)

usage_routes.py: `if device_daily_quota_enabled(): return await get_device_usage_status(user_id=..., access_token=..., device_fp=request_context.device_fingerprint())`, else today's call. `get_usage_status` stays byte-identical (its ST1 first statement is pinned by r25a). `get_device_usage_status(user_id, access_token, *, device_fp)`: allow-listed -> `return await get_usage_status(user_id, access_token)` (no other read first); else ONE tier read; tier != "free" -> `return await get_usage_status(...)` (the base body; premium pays one extra tier read: stated L7); free -> GET account daily and GET device daily (when a device key) via `_get_redis_count` (inline, or `run_redis_offloop_pool` when ENABLE_USAGE_PATH_OFFLOOP is ON, the ST1 placement); no bonus read, no monthly GET; body by the ONE compute body `_usage_status_body(user_info, 0, daily_used, 0, device=<window>)` whose keyword-only `device=None` keeps the base output byte-identical when None (R-ST1-3).

Free body under the flag (key order; values for lifetime 7, account 1 used, device 2 used, cap 3, RIYADH ON at 2026-10-29T20:30Z):

```
{"tier":"free","used":{"daily":1,"monthly":0,"lifetime":7},
 "limits":{"daily":3,"monthly":10,"monthly_base":10,"monthly_bonus":0,"lifetime_free":3},
 "remaining":{"daily":2,"monthly":10,"lifetime_free":0,"device_daily":1},
 "resets_at":"2026-10-30T00:00:00+03:00","counted_scope":"device_daily"}
```

Rules: `used.lifetime` = the stored lifetime_comparisons_used (R-S08-13: present; the retired count; S81-08b inheritance becomes a stored number only); `limits.lifetime_free` stays 3 (build 3 and S81-08 draw the pill denominator from it: equal to the default device cap, L5); `remaining.lifetime_free` 0 (the bypass is retired); monthly retired and non-binding: `used.monthly` 0, `limits.monthly_bonus` 0, `remaining.monthly` = 10 (build 3 `useComparisonCounter.ts:71-82` needs numbers on BOTH axes or it collapses to `used.lifetime < 3`, which would paywall every user past lifetime 3; a 0 would show the build-3 monthly sheet). `counted_scope` = "device_daily" when a device key exists and remaining.device_daily <= remaining.daily (ties name the device), "daily" otherwise and whenever there is no device key (then `remaining.device_daily` is ABSENT: the client reads the counted axis only). `resets_at` per 2.5. Premium / allow-listed: the base body, byte-identical, no new key.

### 2.8 The 429 detail and the handler allow-list (R-S08-14)

Routes: each of the five USAGE_LIMIT details gains `**usage_limit_extras(usage_check)` (usage_service: `{k: usage_check[k] for k in ("retry_after", "resets_at", "scope") if k in usage_check}`; base consume results never carry them, so OFF the dict is identical, key order included). The `retry_after` int reaches the wire through the EXISTING W1-9 block as `retry_after_seconds` + `Retry-After`. error_handler gains, after the B4 block and before the retry block: `if _device_quota_keys_enabled() and exc.status_code == 429 and _is_structured_detail(detail) and isinstance(detail.get("code"), str) and detail["code"] == "USAGE_LIMIT":` copy `resets_at` when a str, and `scope` when a str in `_USAGE_LIMIT_SCOPES = ("daily", "device_daily", "monthly", "lifetime")` (a tuple: never hash an arbitrary value). Wire body under the flag (device refusal at 20:30Z, RIYADH ON): {"success": false, "error": "Comparison limit reached (device_daily_limit)", "code": "USAGE_LIMIT", "request_id": <id>, "resets_at": "2026-10-30T00:00:00+03:00", "scope": "device_daily", "retry_after_seconds": 1800} + header `Retry-After: 1800`. The anon details carry none of the keys.

### 2.9 Log lines (constants, type names only; never a key, id, fingerprint, device key, count or pepper)

INFO `[USAGE-DEVICE] account-only header=<absent|malformed|ok>` (one per quota-path consume without a device key: the build-3 / missing-header metric); WARNING `[USAGE-DEVICE] consume fail-open type=<Name>` (the outage counter: one per failed EVAL); WARNING `[USAGE-DEVICE] refund failed type=<Name>`. ERROR is not used. The base lines stay unchanged on the base path.

### 2.10 Failure table

| Condition | Behaviour |
|---|---|
| EVAL raises (timeout, connection, script error, CROSSSLOT) / bad reply | allowed, consumed False, the fail-open WARNING; the comparison proceeds (L3: an outage lets a device exceed 3) |
| redis_client None | allowed, consumed False, no log |
| header absent / malformed / unkeyable (pepper unset) / ENABLE_REQUEST_CONTEXT_HEADERS OFF | account-only (KEYS = [account]) + the INFO metric; never a 400 |
| tier read fails | `_get_user_tier_info` returns the free default (base) -> the quota path (as base treats the user as free) |
| knob garbage | the default (3 / nobody exempt) |
| refund EVAL fails | WARNING, no retry, the device counter stays +1 for its day (best effort, base parity) |
| status GET fails | `_get_redis_count` -> 0 (base display fail-open) |
| flag flipped between consume and refund | ON -> OFF: the base fallback refunds the account windows, the device +1 stays until its reset (bounded); OFF -> ON: no stash -> base fallback (L6) |

### 2.11 The main invariant: flag-OFF identity

With both flags OFF under each of the five OFF spellings (unset, "false", "0", "off", "") and the FULL configuration present (ENABLE_REQUEST_CONTEXT_HEADERS=true with a valid X-Device-Fingerprint header bound, DEVICE_KEY_PEPPER, DEVICE_DAILY_QUOTA_CAP="7", DEVICE_QUOTA_EXEMPT_USER_IDS naming a DIFFERENT synthetic uid, ENABLE_PAID_ROUTE_METERING=true for the camera / url rows), every Redis call (method, key, args, TTL, order), every result dict, every status body, every route body and header and every usage_service log line equals the committed golden recorded at base; no EVAL is issued; no request_context accessor and no S81-09 knob is read on the consume / refund / status paths (recorders that RAISE prove it). RIYADH ON alone changes only the date part of the keys (and so when the counters reset); QUOTA ON alone keeps UTC dates.

### 2.12 Test seams [production values in brackets]

`usage_service.redis_client` [the cache_service client]; `usage_service.datetime` [datetime; the m18 FakeDatetime pattern]; `usage_service._get_user_tier_info` / `_get_active_referral_bonus` [Supabase]; `request_context` ContextVars bound with `bind_from_headers([(b"x-device-fingerprint", fp)])` or the real middleware through TestClient [the S81-05 middleware]; env DEVICE_KEY_PEPPER [the owner value; synthetic in tests, built at run time]; `usage_service.DEVICE_CONSUME_SCRIPT` / `DEVICE_REFUND_SCRIPT` [literals]; `llm_spend_breaker._eval` [real]. Fakes implement `eval(script, numkeys, *keys_and_args)` (redis-py shape) and, in one row, a class whose `__module__` starts with "upstash_redis" (`eval(script, keys=, args=)`), emulating both scripts in Python.

### 2.13 Answers to the brief questions (each measured; the orchestrator rules)

- Q1 premium device-capped? NO (default kept). Measured: TIER_LIMITS premium 10 / 70 (:145); owner decision 2 "the premium code path is kept exempt but unused"; PLAN :62 "the device cap exemption concerns admin / manual tiers only". Premium runs the base path byte-identical (consume, refund, status; pinned R25).
- Q2 exemption: premium AND the env allow-list `DEVICE_QUOTA_EXEMPT_USER_IDS` (names only). The review accounts are premium per the session-79 resume memory ("review accounts premium"); the allow-list covers a free demo or test account without a tier change. The eval harness calls with X-Admin-Key and no user, so it never reaches the consume (`require_paid_route_user` text_routes :312-333: an admin credential runs as an anonymous caller, no usage consumption; the consume needs `if user and user.get("id")` :618): exempt by construction (MEASURED in the code; stated).
- Q3 fixed +03:00 (zoneinfo MEASURED unavailable; S81-04 uses the same offset; drift pin R30).
- Q4 reuse `llm_spend_breaker._eval` (module import inside the flag-ON arm); `riyadh_day` stays in the leaf (moving it reddens S81-04 r01 / r05) and is tied by R30; the scripts are usage-local. Fallback if the orchestrator rejects a private import: a 4-line usage-local copy pinned equal by a row.
- Q5 `device_fp=None` (ContextVar None) = account-only + the INFO metric; the route never reads the header itself (S81-05 p07 keeps the needle counts at 1); precondition: ENABLE_REQUEST_CONTEXT_HEADERS ON first (section 8).
- Q6 monthly cap retired outright on the quota path (plan :102 "monthly cap dropped"); kept on the base path (premium, allow-list). The refuters' exposure note (10 -> 90 a month per device) is carried as L8.
- Q7 quota ON + RIYADH OFF: next UTC midnight from the same helper, resets_at "+00:00", EXPIREAT next UTC midnight + 1 h.
- Q8 (F1-8, binding): the status sends remaining.daily always and remaining.device_daily whenever a device key exists, with counted_scope naming the binding axis; pinned R19 / R20.

### 2.14 The RIYADH transition (a stated, bounded one-time effect; never a lost refund)

Between 00:00 and 21:00 UTC the Riyadh date equals the UTC date, so a flip in that window changes no key string at the flip instant; the first change happens at the next 21:00 UTC, when every account counter starts a fresh window 3 h earlier than before (in the user's favour, once). A flip between 21:00 and 24:00 UTC moves to tomorrow's key at once: at most one extra fresh window that night. A consume under OFF refunded under ON finds its UTC-dated key as Riyadh-yesterday (the base fallback walks today then `_previous_daily_key`, Riyadh-yesterday under ON): MEASURED design, pinned R18. Recommendation: flip ENABLE_RIYADH_RESET between 00:00 and 21:00 UTC (03:00-24:00 Riyadh). The monthly key follows the Riyadh calendar (a month boundary 3 h earlier). Rollback ON -> OFF between 21:00 and 24:00 UTC can refund the wrong UTC window once (L6).

## 3. Change list (in the order GREEN applies it)

0. Byte copies (shutil.copyfile) + sha256 of every file below before the first edit; the frozen RED file and the golden fixture are re-hashed first and never edited by GREEN.
1. app/services/usage_service.py (CRLF kept; new lines ASCII):
   a. imports: `import math`; `from contextvars import ContextVar`; `from app.utils import request_context as _request_context` (stdlib leaf; no cycle). `llm_spend_breaker` is imported as a module inside the flag-ON arm only.
   b. readers: `device_daily_quota_enabled()`, `riyadh_reset_enabled()`, `device_daily_cap()`, `_device_quota_exempt(user_id)` (2.1).
   c. `_usage_window(now=None)` (2.2) and the four key helpers rewritten through it (flag-OFF strings identical).
   d. `DEVICE_CONSUME_SCRIPT`, `DEVICE_REFUND_SCRIPT` (2.4); `_device_consume_sync(keys, args)`, `_device_refund_sync(keys)` (each one `_eval` call; the module global `redis_client` read per call); `_offload_dispatch_async(fn, *args)` (the #115 pattern, the ONE new `asyncio.to_thread`).
   e. `_DEVICE_DEBIT` ContextVar (default None) + its small holder class; `_device_refund_keys(user_id, consumed_keys)` (flag read first).
   f. `consume_comparison_credit(user_id, access_token, *, device_fp=None)`: the branch after the base gather (2.5); `_consume_device_quota(user_id, device_fp)`.
   g. `refund_comparison_credit`: the device block first (2.6); the base try body unchanged.
   h. `_usage_status_body(user_info, bonus, daily_used, monthly_used, *, device=None)` (base output unchanged for None); `get_device_usage_status(user_id, access_token, *, device_fp)` (2.7).
   i. `usage_limit_extras(usage_check)`, `device_quota_kwargs()` (2.5 / 2.8).
   UNCHANGED: TIER_LIMITS, the anon helpers, `_atomic_consume*`, `_bump_counters*`, `_refund_one_window`, `_refund_credit_sync`, `get_usage_status`, `check_usage_allowed`, `_usage_allowed_body`, `_usage_reads_offloop`, `record_lifetime_comparison`, `_get_user_tier_info`, `_get_active_referral_bonus`.
2. app/middleware/error_handler.py: `_device_quota_keys_enabled()` (local one-liner, ENABLE_DEVICE_DAILY_QUOTA), `_USAGE_LIMIT_SCOPES`, the pass-through block (2.8). Nothing else.
3. app/api/text_routes.py: the three consume calls (:619, :836, :1023) gain `**device_quota_kwargs()`; the three USAGE_LIMIT details (:621-629, :838-846, :1025-1033) gain `**usage_limit_extras(usage_check)`; two names added to the usage_service import block (:37-44). Refund sites UNCHANGED (2.6).
4. app/api/url_routes.py: `_reserve_comparison_credit` (:89, :91-99) the same two edits; import block (:56-60).
5. app/api/image_routes.py: the camera consume (:324-336) the same two edits; import block (:54-61). The anon gate untouched (p07 needle stays 1).
6. app/api/usage_routes.py: the flag branch to `get_device_usage_status` (2.7); imports `device_daily_quota_enabled`, `get_device_usage_status` and the leaf.
7. tests/test_s81_st1_usage_path_offloop.py: the deliberate pin changes E1-E2 only (4.1): the BASE_DIGESTS entries of the six edited functions re-recorded on the GREEN bytes and the r25a `to_thread` count 4 -> 5, each with a one-line comment naming S81-09.
8. CLAUDE.md: the S81-09 row after the S81-15 row (:517-520) and before `## Tests` (:522); CRLF kept (section 8).
9. The RED files (frozen, written by the RED agent): tests/test_s81_s09_device_quota.py and tests/fixtures/s81_s09_flag_off_golden.json.

No other file: no migration, no requirements*, no .env, no tests/.pre_impl_failures.txt, no client file, no processors.json (no new external host: the same Upstash client), no legal text (S81-12 / the flip runbook), no referral_service.py (Q9), no .github file.

## 4. Existing pins

### 4.1 Pins that change deliberately (E-rows)

| # | Pin (file:line) | Today | Change and reason |
|---|---|---|---|
| E1 | tests/test_s81_st1_usage_path_offloop.py r25b `test_r25b_frozen_digests` (:2039-2045), BASE_DIGESTS (:1032) rows `_daily_key`, `_monthly_key`, `_previous_daily_key`, `_previous_monthly_key`, `consume_comparison_credit`, `refund_comparison_credit` | AST digests of the base bodies (ST1's own no-edit guarantee) | re-record the six digests on the GREEN bytes (one comment naming S81-09); the 22 other rows stay. Flag-OFF behaviour of these functions is pinned by behaviour instead (the S81-09 golden P01-P03, P07 and ST1's own BASE_CONSUME_SEQ / BASE_REFUND_SEQ / BASE_ROUTE rows, which stay green unedited) |
| E2 | same file r25a (:2035) `len(_calls(us_tree, "to_thread")) == 4` | 4 | 5: the one `_offload_dispatch_async` (the #115 dispatch for the device EVALs, parity with `_atomic_consume_async`); R-ST1-1 was ST1's scope rule. The other r25a assertions (first statements of get_usage_status / check_usage_allowed, the pool GET count, no run_db_offloop) stay green unedited |
| E3 (at the FLIP, not in this PR) | tests/test_legal_disclosure_s77.py D11 (:807-829) and tests/test_register_benefits_parity_s69.py (:36-82) | Terms s4 numbers and the client register benefits == TIER_LIMITS free (3, 10, 3) | stay green at this unit's merge (TIER_LIMITS unchanged; DEVICE_QUOTA_RESET null keeps the base s4 text). The flip runbook (S81-12 spec E24 / D5) records DEVICE_QUOTA_RESET (a data-only re-fill) and re-pins D11 to the device constant (3 a day per device, `DEVICE_DAILY_QUOTA_CAP` default) in the SAME PR; the register-benefits copy (client, "10 a month") is re-worded by the client lane before that flip (Q11) |

No other existing pin is expected to move; any further measured move at GREEN is a new E-row with its probe, never a silent edit.

### 4.2 Pins that must stay green and unedited (measured green at base, 1.10)

- usage: tests/test_usage_service_internals.py, test_usage_tiers.py, test_usage_referral_bonus.py, test_usage_device_inheritance.py, test_m18_usage_symmetry.py (the FakeDatetime pattern the helper must honour), test_m13_37_freemium_atomic_consume.py, test_m18_preverdict_disconnect_refund.py, test_paid_route_metering.py (the camera / url gates under metering ON with the quota flag unset), test_s81_st1_usage_path_offloop.py (every row except E1 / E2), test_cron_expire_bonuses.py, test_referral_expiry.py, test_retro_w2_1.py, test_shutdown_drain.py.
- request context: tests/test_s81_s05_request_context.py (p06, p07 needle counts, p08, p19, p20), test_s81_s08b_legacy_fingerprint.py, test_s81_s08b_gate_rows.py.
- handler: tests/test_s80_url_mode_v2.py (R32 rows), test_429_contract.py, test_retro_w1_9.py, test_retro_w1_9_429.py, test_error_middleware.py, test_text_routes_error_mapping.py, test_image_identify_llm_unavailable_s69.py.
- breaker: tests/test_s81_s04_spend_breaker.py (r01 import set, r05 riyadh_day: nothing moves out of the leaf), test_s81_s06_anthropic_router.py.
- legal parity at merge: tests/test_legal_disclosure_s77.py, test_register_benefits_parity_s69.py.
- the rest of the comm set (7.3).

## 5. RED tests

### 5.0 Files and harness

- tests/test_s81_s09_device_quota.py (one file; hermetic; no network; every RED row fails at base on an AssertionError ONLY: missing symbols through `_need(module, name)` = getattr or `raise AssertionError`, never an ImportError / AttributeError / fixture error; every PIN row green at base WITH the full configuration of 2.11 and call recorders, so a not-gated mutant is killed).
- tests/fixtures/s81_s09_flag_off_golden.json (committed; recorded AT BASE by the RED agent with the file own recorder, never hand-written; the scenarios of 1.3 plus the five-route 429 envelopes, the status route bodies and the handler bodies; LF, ASCII, sorted keys; the RED report carries its sha256). The spec probe output (1.3) is the cross-check: the RED fixture must agree with it on every shared scenario.
- Harness rules: an autouse fixture imports app.main FIRST, then sets DEVICE_KEY_PEPPER with monkeypatch (DEVICE_KEY_PEPPER is in tests/_env_safety.CREDENTIALS_UNSET: the dotenv-guard hazard); the pepper and every fingerprint are built at run time; the FakeRedis records every call and emulates DEVICE_CONSUME_SCRIPT / DEVICE_REFUND_SCRIPT by comparing the script text to the module constants (an unknown script raises AssertionError inside the fake, so a mutated script is a red row, not a crash); the clock through the m18 FakeDatetime pattern (`usage_service.datetime`); the request ContextVars through `request_context.bind_from_headers` + `reset_request_context` for unit rows and through the real middleware (ENABLE_REQUEST_CONTEXT_HEADERS=true, TestClient(app.main.app)) for route rows, using the tests/test_paid_route_metering.py dependency-override and compare-stub harness; `fire_and_forget` drained before asserting refunds; five OFF spellings `[None, "false", "0", "off", ""]`; caplog at DEBUG for the usage_service and request_context loggers.
- Fixed instants: T0 = 2026-10-29T20:30:00Z (Riyadh 23:30), T1 = 20:59:59Z, T2 = 21:00:00Z, T3 = 21:00:30Z, T4 = 2026-10-31T21:00:00Z (month rollover), T5 = 2026-12-31T21:30:00Z (year rollover), T6 = 2026-10-29T20:30:00.400Z (ceil).

### 5.1 RED rows (fail at base on an AssertionError)

| # | Test | Assertion | Satisfied by |
|---|---|---|---|
| R01 | `test_r01_flag_readers_truth_table` | both readers exist; 13 spellings (None, "", "false", "0", "no", "off", "garbage", " FALSE ", "true", "1", "yes", "on", " TRUE ") -> the idiom; re-read per call | 3.1b |
| R02 | `test_r02_device_cap_knob` | unset->3, "5"->5, " 4 "->4, "0"->3, "-2"->3, "abc"->3, "2.5"->3, "true"->3, "99"->10, "10"->10; per call | 3.1b |
| R03 | `test_r03_exempt_list_parse` | two synthetic uuids (one upper-case) + "garbage" + ",," -> both exempt, garbage ignored, unset / blank -> nobody, the 51st valid token ignored | 3.1b |
| R04 | `test_r04_usage_window` | at T1, T2, T4, T5 with RIYADH ON: day and next_reset (21:00Z of the right day, strictly after now); OFF: UTC day and next UTC midnight | 3.1c |
| R05 | `test_r05_key_helpers_riyadh` | RIYADH ON at T2 on 2026-10-31 (T4): daily 2026-11-01, previous 2026-10-31, monthly 2026-11, previous 2026-10; at T1: 10-29 / 10-28 / 10 / 09; OFF at T2: the UTC strings | 3.1c |
| R06 | `test_r06_one_eval_per_consume` | quota ON, free, lifetime 0, header bound, pepper set: the recorder holds EXACTLY ONE call, an `eval` with DEVICE_CONSUME_SCRIPT, KEYS [acct, dev] (dev = "usage:device:" + HMAC hex + ":" + day), ARGV ["3", "3", str(expireat)]; no incrby / expire / get / decrby | 3.1d, 3.1f |
| R07 | `test_r07_expireat_value` | expireat == next_reset + 3600 under RIYADH ON (T0 -> 2026-10-29T22:00Z epoch) and OFF (2026-10-30T01:00Z epoch) | 3.1c-f |
| R08 | `test_r08_device_before_lifetime_free` | fresh account (lifetime 0), device counter 3, account 0: allowed False, reason device_daily_limit, scope device_daily, consumed False; the fake store unchanged (no INCR anywhere) | 3.1f |
| R09 | `test_r09_account_daily_refusal` | account 3, device 1: reason daily_limit, scope daily, remaining.device_daily 2; store unchanged | 3.1f |
| R10 | `test_r10_success_shape` | code 0: consumed_keys == {daily, device_daily} (no monthly), remaining == {daily, monthly 10, lifetime_free 0, device_daily} in that key order; counts in the store +1 each | 3.1f |
| R11 | `test_r11_retry_after_and_resets_at` | T0 ON: retry_after 1800, resets_at "2026-10-30T00:00:00+03:00"; T0 OFF: 12600 and "2026-10-30T00:00:00+00:00"; T2 ON: 86400; T6 ON: 1800 (ceil, not 1799); always int | 3.1f |
| R12 | `test_r12_post_compare_429_on_the_wire` | POST /api/v1/text/compare, quota ON, device capped, T0 RIYADH ON: status 429, body == {success False, error "Comparison limit reached (device_daily_limit)", code USAGE_LIMIT, request_id <any str>, resets_at, scope "device_daily", retry_after_seconds 1800}; header Retry-After "1800"; compare_from_text never called | 3.1, 3.2, 3.3 |
| R13 | `test_r13_every_consume_site_passes_device_fp` (parametrized: text POST, text GET, stream, url POST, url GET, image) | quota ON (metering ON for url / image): a recorder on `consume_comparison_credit` sees `device_fp == <bound fp>`; the 429 of each carries resets_at + scope + retry_after_seconds | 3.3-3.5 |
| R14 | `test_r14_handler_allow_list` | mini app, quota ON: USAGE_LIMIT 429 detail with resets_at / scope / retry_after 60 -> the three on the wire; scope "weekly" or 7 dropped; resets_at 5 dropped; a RATE_LIMITED / NOT_PRODUCT_PAGE 429 detail carrying the same keys keeps the base key set (+ retry_after_seconds only) | 3.2 |
| R15 | `test_r15_refund_decrements_both_keys_once` | quota ON: consume (code 0) then `refund_comparison_credit(uid)` with no keys -> ONE eval with DEVICE_REFUND_SCRIPT over [acct, dev]; both counters back to their pre-consume values; a second refund call makes no Redis call; a refund for ANOTHER uid in the same context makes no device call (base fallback only) | 3.1e, 3.1g |
| R16 | `test_r16_route_failure_refunds_both` (POST text, stream had_error, url failure, image vision failure) | quota ON, compare stub fails: after the drain both keys are back to their pre-request values and exactly one refund eval ran per request | 3.1g (no route refund edit) |
| R17 | `test_r17_refund_after_riyadh_midnight_is_exact` | consume at T1 (Riyadh day 10-29), refund at T3: the 10-29 keys are decremented; the 10-30 keys are never created | 3.1e-g |
| R18 | `test_r18_previous_daily_key_is_riyadh_yesterday` | RIYADH ON, quota OFF: a base consume at T1, refund with no keys at T3 -> get acct(10-30) (0), get acct(10-29), decrby acct(10-29); and a consume made under RIYADH OFF at 2026-10-29T22:00Z (UTC key 10-29) refunded under ON at 22:00:30Z finds the 10-29 key as Riyadh-yesterday | 3.1c |
| R19 | `test_r19_status_body_device` | quota ON, RIYADH ON, T0, header bound, lifetime 7, acct 1, dev 2: `GET /api/v1/usage/status` body == the 2.7 literal (key order included) | 3.1h, 3.6 |
| R20 | `test_r20_counted_scope` | dev < acct remaining -> device_daily; acct < dev -> daily; equal -> device_daily; header absent -> "daily" and NO remaining.device_daily key | 3.1h |
| R21 | `test_r21_status_reads_on_quota_path` | free quota path: exactly one tier read, GET acct, GET dev; no referral_redemptions read, no monthly GET (recorders) | 3.1h |
| R22 | `test_r22_no_header_is_account_only_plus_one_metric` | quota ON; cases: header absent, header "XYZ" (malformed), a valid header with DEVICE_KEY_PEPPER deleted, ENABLE_REQUEST_CONTEXT_HEADERS OFF: one eval with KEYS [acct] only; exactly ONE INFO record `[USAGE-DEVICE] account-only header=<absent / malformed / ok / absent>`; the route answers 200 (or 429 when the account is capped), never 400 / 422 | 3.1f |
| R23 | `test_r23_no_secret_in_any_log` | over R06, R15, R22, R26: caplog text contains none of: the fingerprint, the device key, either Redis key, the user id, the pepper | 3.1f, 3.1g |
| R24 | `test_r24_allow_list_runs_the_base_path` | quota ON, uid in DEVICE_QUOTA_EXEMPT_USER_IDS (upper-cased in the env), free lifetime 5: Redis calls == golden `consume_free_paid`; result == its golden; status == the golden free body; no eval | 3.1f, 3.1h |
| R25 | `test_r25_premium_is_not_device_capped` | quota ON, premium, device counter 99: calls and result == golden `consume_premium`; status == golden premium body (no new key) | 3.1f |
| R26 | `test_r26_fail_open_with_outage_metric` | eval raises ConnectionError: allowed True, consumed False, no consumed_keys, exactly ONE WARNING `[USAGE-DEVICE] consume fail-open type=ConnectionError`; a later refund makes no Redis call | 3.1f |
| R27 | `test_r27_bad_reply_fails_open` | eval returns "OK" / [0, 1] / None: the R26 dict, type=BadReply | 3.1f |
| R28 | `test_r28_upstash_client_shape` | a fake whose class `__module__` is "upstash_redis.fake" receives `eval(script, keys=[...], args=[...])` | 3.1d (reuse of _eval) |
| R29 | `test_r29_offload_dispatch` | ENABLE_ASYNC_REDIS_OFFLOAD ON: the consume eval and the refund eval run on a worker thread (thread ident differs from the loop thread); OFF: on the loop thread | 3.1d |
| R30 | `test_r30_riyadh_drift_pin` | RIYADH ON at T0..T5: `_usage_window(now)` day isoformat == `llm_spend_breaker.riyadh_day(now)[0]` and `int(next_reset.timestamp()) + 3600 == riyadh_day(now)[1]` | 3.1c |
| R31 | `test_r31_status_route_passes_device_fp` | quota ON: a recorder on `get_device_usage_status` receives device_fp == the bound fp | 3.6 |
| R32 | `test_r32_device_key_is_the_hmac` | dev key == "usage:device:" + hmac.new(pepper, fp, sha256).hexdigest() + ":" + day; the raw fp appears in no Redis key or argument | 3.1f |
| R33 | `test_r33_retired_monthly_and_bonus` | quota ON, monthly counter 10 (pre-flip), bonus 5, acct 0, dev 0: allowed; no monthly key touched; status limits.monthly_bonus 0 and remaining.monthly 10 | 3.1f, 3.1h |
| R34 | `test_r34_camera_consume_and_refund` | metering ON + quota ON: the image route consume carries device_fp; a vision-failure exit refunds both keys exactly once (the closure latch + the stash latch) | 3.5, 3.1g |
| R35 | `test_r35_scripts_are_pinned_literals` | the two module constants equal the 2.4 texts byte for byte | 3.1d |
| R36 | `test_r36_usage_limit_extras_helper` | `usage_limit_extras` returns {} for every golden base result and exactly the three keys for a quota refusal | 3.1i |

### 5.2 PIN rows (green at base, FULL configuration of 2.11, recorders that raise on any S81-09 read)

| # | Test | Assertion |
|---|---|---|
| P01 | `test_p01_golden_consume_flag_off` (five spellings per flag, incl. mixed spellings) | the six consume scenarios: calls, results and log lines == the golden fixture |
| P02 | `test_p02_golden_refund_flag_off` | the three refund scenarios == golden |
| P03 | `test_p03_golden_status_flag_off` | the three status bodies, function AND route, == golden (byte-equal JSON, key order) |
| P04 | `test_p04_route_429_envelope_flag_off` | the five route 429 bodies == {success, error, code, request_id}, no Retry-After, with the device header present |
| P05 | `test_p05_consume_call_shape_flag_off` | at the five sites consume is called with exactly (uid, token) and no kwargs; the status route calls `get_usage_status(user_id=, access_token=)` |
| P06 | `test_p06_handler_flag_off` | a USAGE_LIMIT 429 detail carrying resets_at / scope / retry_after 60 -> {success, error, code, request_id, retry_after_seconds} (W1-9 base) and no resets_at / scope |
| P07 | `test_p07_key_helpers_utc_flag_off` | the golden key table at T1, T2 and 2026-10-31T23:30Z under the five OFF spellings |
| P08 | `test_p08_no_eval_and_no_context_read_flag_off` | a FakeRedis whose eval raises and the request_context accessors / device_key / header_state patched to raise: the P01-P03 scenarios still equal golden |
| P09 | `test_p09_knobs_not_read_flag_off` | an os.getenv recorder: DEVICE_DAILY_QUOTA_CAP and DEVICE_QUOTA_EXEMPT_USER_IDS are never read on the consume / refund / status paths flag OFF |
| P10 | `test_p10_anon_gate_untouched_quota_on` | quota ON, ENABLE_ANON_USAGE_GATE ON, anonymous image identify: anon keys and the anon 429 detail as base (no extras) |
| P11 | `test_p11_riyadh_alone_changes_only_dates` | RIYADH ON, quota OFF at T0 (dates equal): calls == golden; at T2: the same call list with the 10-30 strings; no eval; status key set == base |
| P12 | `test_p12_tier_limits_literal` | `ast.literal_eval` of TIER_LIMITS == the base literal |
| P13 | `test_p13_check_usage_allowed_unchanged_quota_on` | quota ON: `check_usage_allowed` result and calls == its quota-OFF output (no caller; pinned as dead) |
| P14 | `test_p14_success_records_lifetime` | quota ON success through POST text compare: `record_lifetime_comparison` fired once (the lifetime counter keeps counting: R-S08-13 / S81-08b) |

Counts: 36 RED (R13 x6 and R16 x4 parametrized: 44 RED nodes before spelling parametrization), 14 PIN (P01 / P07 x five spellings per flag). Every PIN row runs under 2.11 configuration; P08 / P09 make the not-gated mutants killable.

## 6. Mutation table (each on a byte copy under .qa-mutation.lock, one exact-string edit that matches once, the killing rows via pyt.py -k at bound 600, restored, sha256-compared)

| M | Mutant (file) | Killed by |
|---|---|---|
| M01 | the quota path keeps the base lifetime-free branch BEFORE the device EVAL (usage_service) | R08 |
| M02 | two EVALs (device, then account) instead of one | R06 |
| M03 | EXPIRE 86400 instead of EXPIREAT in the consume script | R06 (script literal), R35, R07 |
| M04 | `_usage_window` ignores ENABLE_RIYADH_RESET (UTC under the flag) | R04, R05, R11, R30 |
| M05 | the refund skips the device key (KEYS = [acct] only) | R15, R16, R34 |
| M06 | the handler drops `scope` | R12, R13, R14 |
| M07 | the metric line carries the raw header value | R23 |
| M08 | a malformed header raises HTTPException(400) | R22 |
| M09 | the consume branch not gated (the quota path with the flag OFF) | P01, P05, P08 |
| M10 | the handler pass-through not gated | P06 |
| M11 | `scope` not checked against the value set | R14 |
| M12 | the allow-list ignored | R24 |
| M13 | premium device-capped | R25 |
| M14 | fail-open returns consumed True + keys | R26 |
| M15 | the stash not checked against the user id | R15 |
| M16 | the stash latch removed (refund twice decrements twice) | R15 |
| M17 | counted_scope tie -> daily | R20 |
| M18 | remaining.device_daily present without a device key | R20 |
| M19 | retry_after by int() truncation instead of ceil | R11 (T6) |
| M20 | resets_at rendered "+00:00" under RIYADH ON | R11, R19 |
| M21 | device key = the raw fingerprint (no HMAC) | R32, R06 |
| M22 | the monthly cap still consulted on the quota path | R33 |
| M23 | the status reads the bonus / the monthly counter on the quota path | R21, R33 |
| M24 | remaining.lifetime_free not zeroed on the quota path | R19 |
| M25 | `device_quota_kwargs` returns the kwarg with the flag OFF | P05 |
| M26 | a route reads `request.headers.get("x-device-fingerprint")` itself | test_s81_s05 p07 (existing), R22 (middleware OFF case) |
| M27 | knob clamp removed ("99" -> 99) | R02 |
| M28 | Riyadh offset 4 h | R04, R30 |
| M29 | the camera route does not pass device_fp | R13[image], R34 |
| M30 | the stream route does not pass device_fp | R13[stream] |
| M31 | `_eval` bypassed (redis-py shape only) | R28 |
| M32 | the device EVAL always inline (offload ignored) | R29 |
| M33 | the device checked AFTER the account inside the script (a capped device and a capped account reports scope daily) | R08 with acct 3 + dev 3 variant (reports device_daily) |
| M34 | the refund script decrements without the floor (DECR on 0) | R15 (a refund of a key at 0 leaves 0) |
| M35 | the status route not gated (device body flag OFF) | P03, P05 |
| M36 | `_previous_daily_key` UTC yesterday under RIYADH ON | R18 |
| M37 | the env knobs read flag OFF | P09 |
| M38 | the anon details gain the extras | P10 |

Equivalent candidates (report for a ruling, never weaken a row): reordering the two EXPIREAT calls inside the script (no observable difference); `math.ceil` vs `-(-x // 1)`.

## 7. Gates for GREEN (cheapest first)

7.1 `py_compile` + `ruff check --select E9,F63,F7,F82 --no-cache` on the six app files; `git diff --stat` shows no whole-file diff (CRLF kept); ASCII added lines; the added-line personal-data / key-shape sweep.
7.2 The RED file at the GREEN base before any edit = exactly the RED shape (36 RED tests / 44 nodes failing on AssertionError, PINs green); after GREEN: all green under the five OFF spellings per flag and ON; bound 600.
7.3 The pin set 4.2 + E1 / E2 re-pinned (bound 1200, chunks <= 25 files).
7.4 The comm set = module and symbol reference grep (usage_service, error_handler, request_context, llm_spend_breaker, text_routes, url_routes, image_routes, usage_routes, by module name and by `.py` path) UNION the standard source-scanning pins (test_model_config.py, test_model_config_enforced.py, test_prompt_fence.py, test_u3c_store_false_pin.py, test_start_command*.py, test_migration_index_predicate_immutability.py, test_openai_key_log_hygiene_s69.py, test_sentry_channels_u8d_unit.py and every app/ walker: rglob / glob / os.walk / scandir / listdir readers joined with an "app" segment) UNION the CLAUDE.md readers (tests/test_ci_gates.py, tests/test_behavior_dimension_translation.py; the unit edits CLAUDE.md) MINUS test_precommit_hook*.py. Measured seed at base: 99 files (<scratchpad>/S81-09_spec/comm_seed.txt); the RED re-derives it at its base and records the BASE RUN (NOT MEASURED here); chunks <= 25 files, bound 1200, base and head, `comm -13` of the sorted FAILED node ids EMPTY. No migration / processors / legal text changes, so those readers are not added; the SmartCompareApp-scanning backend tests join only if the orchestrator rules the status contract client-visible (it is additive; R-S08-2 already pins the client side in S81-08); the fourteen client fences need no run (1.9).
7.5 The mutation table (section 6) by the adversaries on the GREEN bytes (GREEN does not re-run it).

## 8. CLAUDE.md row (house format, names only; placed after the S81-15 row :517-520, before `## Tests` :522; the S81-12 / S81-08 rows that land first are a known anchor union at rebase)

Proposed text (GREEN writes it verbatim, adjusting only file:line cites measured on its bytes):

**SESSION 81 flags (S81-09 DEVICE-QUOTA-RIYADH, 2026-10-29; both default OFF, read PER CALL; new names, so unset in production by construction (Railway not read); the PLAN_S81 M3 unit (:148, the grafts :102-104, owner decisions 2 and 5); spec `.qa-s80/S81-09_UNIT_SPEC.md` of the unit worktree with its adversarial review and the rulings / RED gate in `docs/investigations/2026-10-22-session-81-state/specs/`):**
- `ENABLE_RIYADH_RESET` (`app/services/usage_service.py::riyadh_reset_enabled`, read by the one date helper `_usage_window`). **Effect ON:** every usage date key (`usage:daily:` / `usage:monthly:`, the previous-window refund fallbacks, the anon keys, the quota path and its status) follows the Asia/Riyadh calendar (fixed +03:00, no DST; zoneinfo is not on the pinned venv), so the daily counters reset at 00:00 Riyadh (21:00 UTC). **Flag OFF:** the UTC keys byte for byte. Flip between 00:00 and 21:00 UTC: no key string changes at the flip instant; the next 21:00 UTC opens one fresh window 3 h early, once; refunds across the flip find the old key as Riyadh-yesterday.
- `ENABLE_DEVICE_DAILY_QUOTA` + knobs `DEVICE_DAILY_QUOTA_CAP` (default 3, clamped 1..10, garbage -> 3) and `DEVICE_QUOTA_EXEMPT_USER_IDS` (user ids, comma separated, names only; default nobody) + `DEVICE_KEY_PEPPER` (S81-05). **Effect ON (free tier, not allow-listed):** ONE Upstash Lua EVAL per consume (`DEVICE_CONSUME_SCRIPT`) checks and debits `usage:device:<HMAC device key>:<day>` (3 a day, shared by every account on the device) and `usage:daily:<uid>:<day>` (3 a day) together, the device first, EXPIREAT the next reset + 1 h; the monthly cap, the referral-bonus extension and the lifetime-free bypass are retired on that path (the lifetime counter keeps counting as a stored number); a refusal is the existing 429 USAGE_LIMIT plus `retry_after_seconds` / `Retry-After`, `resets_at` (ISO, the next reset) and `scope` (`device_daily` / `daily`) through the flag-gated handler allow-list; a failed compare refunds both keys exactly once through `DEVICE_REFUND_SCRIPT` (the request-scoped debit stash); `/usage/status` adds `remaining.device_daily` (with a device key), `resets_at` and `counted_scope` and reports the retired monthly axis as never binding (used 0, bonus 0, remaining 10) and `remaining.lifetime_free` 0. A missing / malformed / unkeyable `X-Device-Fingerprint` (build 3, or ENABLE_REQUEST_CONTEXT_HEADERS OFF, or the pepper unset) = account-only plus ONE INFO `[USAGE-DEVICE] account-only header=<state>`, never a 400. Premium and the allow-list run the base path byte-identically. A Redis error fails OPEN (allowed, nothing debited) with ONE WARNING `[USAGE-DEVICE] consume fail-open type=<Name>` (the outage counter). **Flags OFF:** byte-identical (Redis calls, bodies, logs), pinned by `tests/fixtures/s81_s09_flag_off_golden.json` under the five OFF spellings with the full configuration (`tests/test_s81_s09_device_quota.py`).
- **Preconditions to flip (owner, names only, dated ledger lines):** (1) LEGAL-V3 (S81-12) merged and live (backend deployed AND landing redeployed); (2) the S81-08 OTA published after approval and propagated (two launches) and `ENABLE_REQUEST_CONTEXT_HEADERS` ON on web; (3) `DEVICE_KEY_PEPPER` set on web (a random text value of at least 64 hex characters; name only); (4) the review / demo account confirmed premium or listed in `DEVICE_QUOTA_EXEMPT_USER_IDS`; (5) the referral-reward pause (Q9) live; (6) `ENABLE_RIYADH_RESET` ON first in its own window; (7) then, in one window: the data-only re-fill recording `DEVICE_QUOTA_RESET` (+ D11 re-pinned) deployed, then `ENABLE_DEVICE_DAILY_QUOTA` ON. **Canary:** `/usage/status` from a test device (counted_scope, resets_at), one over-cap 429 carrying the three fields, the `account-only` INFO count falling as the OTA spreads, ZERO `consume fail-open` lines, ONE EVAL per compare in the Upstash command count. **Rollback:** unset the variable (per call; device counters expire on their own within a day).

### 8.1 Owner steps (names only, never values) and the order of the legal-parity pins

1. Set `DEVICE_KEY_PEPPER` on web (S81-05 owner item; no dated ledger line records it today: UNKNOWN). 2. Confirm by a names-only ledger line that the App Review demo account is premium, or set `DEVICE_QUOTA_EXEMPT_USER_IDS` on web. 3. After approval and after the S81-08 OTA has propagated: `ENABLE_REQUEST_CONTEXT_HEADERS=true` (its own window, S81-05 row). 4. `ENABLE_RIYADH_RESET=true` alone, between 00:00 and 21:00 UTC; canary: next day the account counters reset at 21:00 UTC. 5. LEGAL-V3 live; the referral pause live (Q9); then ONE window: the data-only re-fill recording `DEVICE_QUOTA_RESET` / `_AR` through the U8 machinery with `tests/test_legal_disclosure_s77.py` D11 re-pinned to the device constant in the same PR (S81-12 spec E24 / D5), deployed with the landing re-render; then `ENABLE_DEVICE_DAILY_QUOTA=true`; canary as in the row. 6. Notes for Review (1.0.1 or the next submission): the free limit is 3 comparisons a day per device. Order of the parity pins: at THIS unit's merge D11 and the register-benefits parity stay green unedited (TIER_LIMITS unchanged, DEVICE_QUOTA_RESET null); at step 5 D11 moves with the re-fill; the client register-benefits copy (10 a month) moves in a client unit before step 5 (Q11).

## 9. Stated limits

- L1 Upstash is a single point of failure: an outage fails OPEN (a device can exceed 3 that day), counted by the WARNING (base parity: the base consume also fails open).
- L2 The device axis binds only clients that send the header (every post-OTA build). Build-3 JS and header-less callers get 3 per ACCOUNT per day only (stricter than base on the month, looser than the device rule); a forged header (a fresh random 64-hex per request) evades the device axis but never the account axis; per-IP / per-device throttles are S81-24.
- L3 Fail-open debits nothing (consumed False); a compare that then fails is not refunded (nothing to refund).
- L4 Multi-key EVAL on Upstash is REASONED (not clustered), not measured on the live service; a refusal would show as the fail-open WARNING on the first canary compare.
- L5 The S81-08 pill denominator is `limits.lifetime_free` (3), equal to the default cap: `DEVICE_DAILY_QUOTA_CAP` must stay 3 until a client reads a device limit (Q12).
- L6 A flag flip between a consume and its refund leaves a device counter +1 for that day (bounded); an ENABLE_RIYADH_RESET rollback between 21:00 and 24:00 UTC can refund the wrong UTC window once.
- L7 A premium (or tier-read-failed) status under the flag pays one extra tier read (premium is unused today).
- L8 Dropping the monthly cap raises the per-device monthly exposure from 10 to about 90 compares (Serper / Bright Data spend, not only LLM; the refuters' note, PLAN :119); the S81-04 breaker caps the LLM spend.
- L9 The account-daily key is shared by both paths within a day: a mid-day flip keeps the day count (no reset at flip time).
- L10 Under the flag `users.lifetime_comparisons_used` (and the S81-08b inheritance of it) is a stored number with no entitlement effect.
- L11 `check_usage_allowed` (no caller) is unchanged and ignores the device rule.
- L12 Device counter keys are pseudonymous HMACs that expire about one hour after the reset; a pepper rotation restarts every device counter for that day.
- L13 Without a header the status names `counted_scope` "daily" even if the device is exhausted (the device is unknown); the next consume answers authoritatively.
- L14 An App Review tester who signs up a NEW free account on a device is device-capped like any user; only the demo account (premium / allow-listed) is exempt.
- L15 `remaining.monthly` 10 and `used.monthly` 0 under the flag are presentation values for earlier clients (the axis is retired), not a count.

## 10. Out of scope

The client rendering (S81-08 owns the pill and the sheet; it already reads counted_scope / remaining.<axis> / resets_at / scope / retry_after_seconds); the anon gate (`anon:<fp>`; it only inherits the date helper); migrations (Redis only, no SQL); the Terms and privacy text (S81-12; recording DEVICE_QUOTA_RESET is a flip-runbook data change); per-IP throttles (S81-24); the referral device lifetime cap; the referral-reward pause of R-S12-14 (Q9); SAME_DEVICE (S81-08d); the fragrance gate and its refusal budget (S81-10); compare_runs (S81-22); `check_usage_allowed`; any change to `record_lifetime_comparison`; the client register-benefits copy (Q11).

## 11. Open questions for the orchestrator (each with the spec default)

- Q9 (R-S12-14, binding ruling not carried by the brief): "S81-09 is the unit that stops granting [Loop-2 bonus comparisons and Deep Review credits] under ENABLE_DEVICE_DAILY_QUOTA". Measured grant sites at base: app/services/referral_service.py `try_trigger_loop2` :628 -> `_grant_loop2_rewards` :834-899 (step 1 a referral_redemptions row with loop2_comparisons_granted :851-861, step 2 the users bonus bump :863-874, step 3 a deep_review_credits row :877-879, step 4 lifetime_invites_consumed :881-897, which the dormant s9 text KEEPS), the Loop-1 deep_review_credits row in create_invite :339, the referrer push `_send_loop2_push` :914. Default: a separate small unit S81-09c REFERRAL-PAUSE that reads the SAME flag name per call (one flip moves both), skips steps 1-3 and the reward push, keeps step 4 and the invite redemption, and merges before the flip (precondition 5); reason: the brief binds scope to usage / handler / routes and the referral path has its own pins and copy. Alternative: fold the same gate into S81-09 (adds referral_service.py and its tests to the change list and the comm set).
- Q10 the refund carrier: the request-scoped debit stash (default, 2.6; no edit at the seven refund sites) or explicit consumed_keys at every refund site under the flag (R1).
- Q11 the client register-benefits copy states "10 a month" (pinned to TIER_LIMITS by tests/test_register_benefits_parity_s69.py): which client unit re-words it before the quota flip (S81-11 by default) and whether the parity pin then reads the device constant.
- Q12 an additive `limits.device_daily` on /usage/status so a client can render the device denominator (default: not now; L5 holds the knob at 3).
- Q13 the anon keys follow the Riyadh helper (default yes: one day definition; the anon gate is OFF in production).
- Q14 reuse of the private `llm_spend_breaker._eval` (default) vs a pinned 4-line local copy.
- Q15 the scope reported when BOTH axes are exhausted: device_daily (default: the script checks the device first).
- Q16 the account-only metric at INFO, one per quota-path consume (default; a WARNING would flood during the OTA spread).

## Not done in this spec

No code, test or fixture was written in the worktree (only this file under the gitignored .qa-s80/); no git write; no package manager; no secret or .env read; the comm set base record, the golden fixture and every RED row are the RED agent's (the probe of 1.3 is the cross-check); the live Upstash multi-key EVAL behaviour and the production states of DEVICE_KEY_PEPPER, ENABLE_ASYNC_REDIS_OFFLOAD and ENABLE_USAGE_PATH_OFFLOOP are NOT MEASURED (names only; the ledger has no dated line); the client fences were read, not run.
