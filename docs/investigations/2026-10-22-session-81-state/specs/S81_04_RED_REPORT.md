# S81-04 SPEND-BREAKER: RED report (RED agent, Opus 5.5)

| Header | Value |
|---|---|
| Unit | S81-04 SPEND-BREAKER, flag `ENABLE_LLM_SPEND_BREAKER` (lane B) |
| Base | `dfc6502f791cdccbf0a620041f66888a734015d3` (= origin/main after #369 S81-03; `git rev-parse HEAD` of the real worktree) |
| Real worktree | `C:/Users/SynAckITPC/Documents/AI/sc-s81-s04` (only `tests/test_s81_s04_spend_breaker.py` added) |
| Scratch worktree | `<scratchpad>/S04_red/s04_scratch` (detached at the base; prototype + mutants; removed at the end) |
| Notes | `<scratchpad>/S04_red/notes.md`; logs `<scratchpad>/S04_red/*.log`, mutant logs `<scratchpad>/S04_red/mut_logs/` |
| Precedence applied | RULINGS_S81_04 > review corrections > spec |
| Box load | `node -e 0` = 2.2 s at 16:13, 7.8 s at 16:57 (slow-spawn pathology; sibling gates); pytest collection alone 20-60 s per call |

## 1. The RED file

`tests/test_s81_s04_spend_breaker.py`, 77,837 bytes, sha256 `8e4b0e536ee9e54b5a12506fb293e7f12e101543a807af5df87f12e86e7cedd4`, pure ASCII (0 bytes > 127), LF (0 CRLF), no 8-digit run, `py_compile` + `ruff --select E9,F63,F7,F82,F401,F841` clean. 69 test functions, 235 nodes: 58 RED functions (219 nodes) + 11 PIN functions (16 nodes).

Hermetic: imports `app.main` first; fakes on `cache_service.redis_client` (FakeUpstash `__module__ = upstash_redis.client`, FakeRedisPy `redis.client`, RaisingRedis with a run-time sentinel); the leaf's `_utcnow` / `_monotonic` seams frozen; every compare-driven row stubs `StructuredComparisonService._get_price` because the W1-3 harness's only egress is the price fan-out (measured with `QAREN_NETGUARD_REPORT`: algolia / unbxd / shopify `products.json` / noon via curl_cffi); 10-digit expectations and epochs built at run time; synthetic model ids built by concatenation; the autouse fixture deletes the flag, `ENABLE_LLM_PREFLIGHT_BREAKER`, the W1-3 TTL and all eight S81-04 knobs, and resets the leaf state before and after every test (no /health key leaks into a later file).

### RED-defined leaf API (the contract GREEN implements; derived from spec 2.2 + rulings; flagged for the gate)

`app/services/llm_spend_breaker.py`: `FLAG`, `LANE_LIVE/ESCALATION/SEARCH/OFFCLOCK`, `LANES` (== `llm_pricing.SPEND_LANES`), `DEFAULT_CAPS_USD`, `CAP_ENV`, `RIYADH_UTC_OFFSET_HOURS = 3`, `KEY_PREFIX = "llm_spend"`, `OPENAI_IMAGE_PART_TOKEN_BOUND = 1445`, `ANTHROPIC_IMAGE_TOKEN_CAP = 4784`, `RECORD_SCRIPT`, `RESERVE_SCRIPT`; `spend_breaker_enabled()`, `cap_usd(lane)`, `memo_seconds()` (`LLM_SPEND_MEMO_SECONDS`, 5.0), `redis_timeout_seconds()` (`LLM_SPEND_REDIS_TIMEOUT_SECONDS`, 0.5), `entry_reserve_usd()` (`LLM_SPEND_ENTRY_RESERVE_USD`, 0.10), `chokepoint_lane()` (`LLM_SPEND_CHOKEPOINT_LANE`, live; strip/lower, outside LANES -> live); `riyadh_day(now)`, `spend_key(lane, day)`; `prompt_token_upper_bound(messages, response_format=None, tools=None, provider="openai")`, `anthropic_image_token_bound(w, h)`, `output_token_bound(max_tokens, max_completion_tokens)`, `upper_bound_usd(provider, model, prompt, max_out, searches=0)`, `conservative_bound_usd(provider, prompt, out, searches=0)` (OpenAI -> the gpt-4o row, every other provider -> the Sonnet row, derived from the price tables, no model literal in the leaf); `admit(lane, ub)` / `async admit_async(lane, ub)` (memo-aware; sanitised bound), `async entry_refuses_async(lane)`, `record(lane, actual, admitted_usd=None)` / `record_soon(lane, actual, admitted_usd=None)` (an invalid actual records the admitted bound, B2), `reserve(lane, ub)` / `settle(lane, ub, actual)` (R-S04-5), `async admit_openai_dispatch(model, messages, max_tokens, max_completion_tokens, response_format=None, tools=None)` (returns an opaque ticket), `record_openai_response_soon(ticket, model, response)`, `spend_snapshot()` (/health), `admin_snapshot()` (admin amounts incl. `memo_age_seconds`), `_get_llm_spend_pool()` (4 workers, thread prefix `llm-spend`), seams `_utcnow`, `_monotonic`, `_client`, `_reset_spend_breaker_state()`. Wiring: abs imports `from app.services import llm_spend_breaker as _llm_spend_breaker`, the admit block reads six `kwargs.get(...)` values (model, messages, max_tokens, max_completion_tokens, response_format, tools) BEFORE `_openai_dispatch_admission()`, two `record_openai_response_soon` calls; scs: two `spend_breaker_enabled() and await entry_refuses_async(LANE_LIVE)` entry checks; `app.main.llm_spend_health_snapshot`; admin `/api/v1/admin/costs` `spend_breaker` only ON; FY25 `UNIT_ENV` names the flag (E2); CLAUDE.md row tokens (R38).

### Row map (RED unless marked PIN)

| Row | Nodes | Asserts | Ruling |
|---|---|---|---|
| R01 import rule | 1 | leaf exists; top-level imports stdlib + cache_service / llm_pricing / openai_pricing / async_utils only; no `._LEDGER`; no model-id literal; api_budget_service never top-level | spec R01 |
| R02 flag idiom | 13 | the 13 values, re-read per call | spec |
| R03 lanes + knob names | 1 | LANES == SPEND_LANES, defaults, CAP_ENV, the four new knob readers and their env names | R-S04-1/2/4/6 |
| R04 / R04b / R04c knob parse | 44 / 33 / 7 | cap and memo / timeout / reserve: unset, blank, garbage, inf, -inf, nan, 0, -1 -> default; chokepoint lane validated | spec, rulings |
| R05 Riyadh day | 4 | day + EXPIREAT next Riyadh midnight + 1 h; spend_key | spec |
| R06 unknown lane | 1 | ValueError for admit / record / cap / key / reserve / settle; zero commands | spec |
| R07 / R07b prompt + image bound | 10 / 8 | text, Arabic UTF-8, image part 1,445 whatever the URL size, None, unknown part, response_format bytes, tools bytes, anthropic image 4,784; ceil(w/28) x ceil(h/28) capped 4,784, invalid dims -> cap | R-S04-9, R-S04-10 |
| R08 output bound | 6 | | spec |
| R09 / R09b bounds | 5 / 5 | S81-03 price_call literals; conservative per-provider bound (gpt-4o / Sonnet) never None | R-S04-3 |
| R10 / R10b admit | 4 / 4 | one GET; per-lane cap inside admit (kills M28) | R-S04-10 |
| R11-R13 | 3 | refusal = the exact LLMUnavailableError, no 429/rate/quota, exact WARNING with cents; strict `>`; missing key = 0 | spec |
| R14-R16 record | 4 + 7 + 1 | one Lua EVAL, args `%.10f` + EXPIREAT, admin observation from the EVAL result; invalid amounts (incl. True) no command; redis-py positional shape | spec, R-S04-10 |
| R17 / R18 fail-open | 1 / 4 | RedisUnconfigured / ConnectionError, one WARNING per 60 s, sentinel text never logged; bad stored value -> ValueError fail-open | spec |
| R19 / R19b unpriced + sanitise | 1 / 5 | unpriced model -> conservative bound (gpt-4o rates) + one rate-limited WARNING; None / NaN / negative / str / bool bound -> conservative, never TypeError, never zero | R-S04-3, R-S04-10 |
| R20 / R21 | 2 | cap per call; day roll moves the key | spec |
| R22 / R22b / R22c | 3 | GET + EVAL on the `llm-spend` pool (4 workers), durable task in `_BACKGROUND_TASKS`; a stalled read admits inside the bound naming TimeoutError (knob per call); no client -> zero ThreadPoolExecutor submits | R-S04-2 |
| R23 entry reserve | 6 | spent + reserve >= cap (cap-0.05 refuses, cap-0.15 admits, knob per call, exact equality 2.50 + 0.5) one GET on the pool, WARNING without query | R-S04-4 |
| R24-R30 chokepoint | 1+2+1+2+4+2+1+1+1 | order [get, create, eval]; refusal precedes the W1-3 admission and never spends the probe; record on the W1-3 tail; raising / cancelled create records nothing; bound from kwargs incl. response_format; chokepoint lane knob; unpriced records the ADMITTED bound; Anthropic-shaped unpriced record = positive INCRBYFLOAT of the admitted bound; usage-less response records nothing | R-S04-3/6/10 |
| R31 / R31b / R32 / R32b | 4 | REST + SSE entry refuse at cap-0.05 with zero fan-out, admit at cap-0.15 | R-S04-4 |
| R32c route proof | 2 | POST /compare 503 coded LLM_UNAVAILABLE; SSE `event: error` LLM_UNAVAILABLE; refund once, no save, no lifetime | R-S04-4, R-A3, review corr. 15 |
| R33 / R34 / R34b / R35 / R36 | 5 | /health = `{lane: {exhausted, day}}` + `llm_spend_fail_open`, no amounts, zero Redis commands; exhausted per call; fail-open counter; raising snapshot -> no key; static wiring | R-S04-7 |
| R36b admin amounts | 1 | `/api/v1/admin/costs` `spend_breaker.live` {spent_usd, cap_usd, day, memo_age_seconds} ON | R-S04-7 |
| R37 static wiring | 1 | abs import + admit args (6 kwargs.get) + 2 records + admit before the W1-3 admission; scs 2 guarded entry checks | spec R37 amended |
| R38 CLAUDE.md row | 1 | the eight knob names, key shape, /health, llm_spend_fail_open, spend_breaker, fail-open, last-resort, S81-09, S81-24 | R-S04-11 |
| R39 / R39b memo | 2 | fresh -> no GET, stale -> one GET, knob per call; the local delta counted at once (before the EVAL lands) | R-S04-1 |
| R40 / R40b / R40c reserve-settle | 3 | two parallel 1.5 reserves vs 2.00 admit exactly one (RESERVE_SCRIPT, args ub/cap/expireat); settle INCRBYFLOAT(actual - ub), none for None / exact; reserve fail-open | R-S04-5 |
| R42 ON accounting | 1 | real chokepoint through the W1-3 compare harness: EVAL count == create count, 1 <= GET <= N + 1 | R-S04-10 (P08 accounting half) |
| R43 FY25 UNIT_ENV | 1 | the flag is in UNIT_ENV (E2) | R-S04-8 |
| P01 PIN | 8 | flag OFF (8 spellings) under FULL config (all knobs set, every lane seeded 99.0): create kwargs + store False, same response, zero fake commands, zero submits / fire_and_forget / to_thread, base ledger entry literal | B1 rule |
| P02-P07, P09 PIN | 7 | W1-3 ON + spend OFF no spend key; REST / SSE entries proceed on an exhausted lane; /health no key; PROVIDER_CONFIGS unchanged; no credential name; admin no `spend_breaker` OFF | B1 rule |
| P08 PIN | 1 | ON-with-headroom vs OFF through the real W1-3 compare harness: field-equal bodies minus the FY25 volatile set, equal sorted create kwargs, equal create counts and fan-out counts | R-S04-10 |

## 2. Runs (every one through pyt.py, one at a time)

| Run | Result | [pyt] line |
|---|---|---|
| probe: W1-3 flag-off compare + stream at base (egress census) | 2 passed | `[pyt] tag=s04red-probe-ng start=2026-10-23 16:24:30 end=2026-10-23 16:24:38 elapsed=8s bound=600s status=OK rc=0`; netguard report: curl_cffi to algolia / unbxd / shopify products.json / noon + supabase sentinel |
| RED file at base (first bytes, 233 nodes) | 217 failed / 16 passed, all 217 `E AssertionError` | `[pyt] tag=s04red-base-unit start=2026-10-23 16:41:22 end=2026-10-23 16:42:06 elapsed=44s bound=600s status=FAIL rc=1` |
| prototype, flag unset (233) | 233 passed | `[pyt] tag=s04red-proto-off start=2026-10-23 16:47:48 end=2026-10-23 16:48:18 elapsed=31s bound=600s status=OK rc=0` |
| prototype, ENABLE_LLM_SPEND_BREAKER=true exported (233) | 233 passed | `[pyt] tag=s04red-proto-on start=2026-10-23 16:49:22 end=2026-10-23 16:49:38 elapsed=16s bound=600s status=OK rc=0` |
| RED file at base, FINAL bytes (235 nodes) | **219 failed / 16 passed; 219 `E AssertionError`, no other exception class** | `[pyt] tag=s04red-base-unit-final start=2026-10-23 17:30:08 end=2026-10-23 17:32:01 elapsed=113s bound=600s status=FAIL rc=1`; `[hermeticity] sentinel checked 235 test(s)`; `[netguard] blocked 16 attempt(s) from 1 node(s)` (P08, sentinel only: neutralized.supabase.invalid L2 saves) |
| prototype FINAL, flag unset | **235 passed** | `[pyt] tag=s04red-proto-off-final start=2026-10-23 17:33:25 end=2026-10-23 17:34:42 elapsed=78s bound=600s status=OK rc=0` |
| prototype FINAL, flag exported ON | **235 passed** | `[pyt] tag=s04red-proto-on-final start=2026-10-23 17:34:46 end=2026-10-23 17:35:48 elapsed=62s bound=600s status=OK rc=0`; netguard: P08 + R42 sentinel only |
| comm chunk 01 at base: the 23 pin files (spec 4.2 + K1 + CLAUDE.md readers + health readers) | **1504 passed, 0 failed** | `[pyt] tag=s04red-comm-pins-base start=2026-10-23 17:36:39 end=2026-10-23 17:38:49 elapsed=129s bound=1200s status=OK rc=0`; `[hermeticity] sentinel checked 1504 test(s)`; `[netguard] blocked 141 attempt(s) from 7 node(s)` (the pre-existing test_openai_breaker / test_retro_w1_3 baseline nodes) |
| 43 mutant runs | 43 KILLED | logs `<scratchpad>/S04_red/mut_logs/M*.log`, rows `mutants.json` (M01-M05 partial first run) + `mutants2.json` |

Base PIN nodes green (16): P01 x8, P02, P03, P04, P05, P06, P07, P08, P09. Failed ids: `<scratchpad>/S04_red/base_unit_final.log` (summary) and `base_failed_ids.txt`.

Prototype (thrown away; diff kept at `<scratchpad>/S04_red/proto/prototype.diff`, leaf at `proto/llm_spend_breaker.py`, applier `proto/apply_proto.py`): the RED is satisfiable with exactly the spec's change list as amended (new leaf; abs import + admit block before `_openai_dispatch_admission()` + two `record_openai_response_soon`; two scs entry checks; `app.main.llm_spend_health_snapshot`; the admin `spend_breaker` block inside `api_costs`; FY25 UNIT_ENV; a CLAUDE.md row). Not run on the prototype: the 4.2 pin set, U3c, K1 (K1 goes red on any edit of guarded_llm_create by design: E1).

## 3. Mutation table (scratch worktree, byte copy -> one exact edit -> pyt.py -k -> restore -> sha256 verified by the harness; `.qa-mutation.lock` created and removed)

| # | Mutant | Status | Killing row(s) |
|---|---|---|---|
| M01 | chokepoint admit not gated by the flag | KILLED | P01 (all 8) |
| M02 | REST entry flag operand -> True | KILLED | P03 |
| M03 | stream entry flag operand -> True | KILLED | P04 |
| M04 | admit `>` -> `>=` | KILLED | R12 |
| M05 | entry `>=` -> `>` | KILLED | R23[2.50-0.5] |
| M06 | spend admit moved after the W1-3 admission (W1-3-ON branch) | KILLED | R25[True], R37 |
| M07 | record_soon -> inline record on the loop | KILLED | R22 |
| M08 | image part counted as json bytes | KILLED | R07 |
| M09 | EXPIREAT removed from RECORD_SCRIPT | KILLED | R14 |
| M10 | knob parse without isfinite | KILLED | R04[inf] |
| M11 | fail-open warn limiter removed | KILLED | R17 |
| M12 | Riyadh offset 0 | KILLED | R05 |
| M13 | refusal raises RuntimeError | KILLED | R11 |
| M14 | refusal message carries "rate" | KILLED | R11 |
| M15 | a raising create records the bound | KILLED | R27[rate_limit] |
| M16 | snapshot keys before the breaker ran | KILLED | P05 |
| M17 | snapshot re-reads Redis | KILLED | R33 |
| M18 | output bound 0 | KILLED | R08 |
| M19 | flag reader without strip/lower | KILLED | R02 |
| M20 | admit reads the live key for every lane | KILLED | R10 |
| M21 | record args repr() | KILLED | R14 |
| M22 | record only on the W1-3-OFF tail | KILLED | R26 |
| M23 | unpriced bound treated as a refusal | KILLED | R19, R29 |
| M24 | PROVIDER_CONFIGS `llm` row | KILLED | P06 |
| M25 | /health key unconditional from main | KILLED | P05 |
| M26 | _eval always the upstash shape | KILLED | R16 |
| M27 | entry read inline on the loop | KILLED | R23 |
| M28 | live cap used for every lane inside admit (ruling M28) | KILLED | R10b |
| M29 | memo never stale (ruling) | KILLED | R39 |
| M30 | read bound removed (ruling) | KILLED | R22b |
| M31 | default executor instead of the llm-spend pool (ruling) | KILLED | R22, R23 |
| M32 | unpriced records the legacy estimate (ruling "records zero") | KILLED | R29 |
| M33 | reserve without the check (ruling) | KILLED | R40 |
| M34 | amounts on /health (ruling) | KILLED | R33 |
| M35 | local delta not added to the memo | KILLED | R39b |
| M36 | no-client short-circuit removed (hop first) | KILLED | R22c |
| M37 | entry reserve ignored | KILLED | R23, R31 |
| M38 | chokepoint lane knob ignored | KILLED | R28b |
| M39 | admit bound not sanitised | KILLED | R19b |
| M40 | settle sign reversed | KILLED | R40b |
| M41 | bool accepted as an amount | KILLED | R15[True] |
| M42 | admin block written with the flag OFF | KILLED | P09 |
| M43 | fail-open counter not counted | KILLED | R34b |

43 mutants, 43 KILLED, 0 survivors, 0 equivalents. Every kill is an assertion failure in the named row (pyt -k runs; logs in mut_logs).

## 4. Comm set

List: `<scratchpad>/S04_red/comm_final.txt` (334 files) with per-file reasons `<scratchpad>/S04_red/comm_final_reasons.tsv`, built by `<scratchpad>/S04_red/build_comm.py` (module / symbol reference grep for structured_comparison_service, api_budget_service, guarded_llm_create, LLMUnavailableError, llm_spend, llm_pricing, openai_pricing, admin_routes, /api/v1/admin/costs, app.main, /health, health_check, _module_snapshot, compare_from_text, LLM_UNAVAILABLE; UNION the source readers (a file reader AND an app/ path or module `__file__` or .github or CLAUDE.md); UNION the importers of the edited test modules (test_s75_fanout_identity UNIT_ENV: test_s78_all_timeout_cap_as_timeout, test_s78_tier_fill_residual_guard, test_s80_b1; test_s81_s03_llm_ledger_v2; test_openai_breaker); UNION the named pins + CLAUDE.md readers + health readers; UNION the spec's 314-file set; MINUS the four test_precommit_hook files). NETWORK_FLAKY_EXCLUDE node ids (scripts/regression_gate_diff.py:56-65) are to be deselected on both sides. tests/conftest.py does not read app/ source (scanned).

MEASURED at base: chunk 01 = the 23 pin files (list `comm_chunk01_pins.txt`): 1504 passed, 0 failed. **NOT MEASURED at base: the remaining 311 files (13 chunks)**: the agent budget (90 min) was spent by 17:29 and the box was in the slow-spawn state (`node -e 0` 2.2-7.8 s; pytest collection 20-60 s per call); GREEN runs base and head per spec section 7 anyway.

## 5. Deviations from the spec (each by ruling or recorded for the gate)

1. Image part bound 1,445 tokens (OpenAI) / 4,784 cap (Anthropic) instead of 50,000 (R-S04-9); R07 / R28 expectations follow.
2. R19 / R29 rewritten per R-S04-3: an unpriced model is admitted on the conservative bound (gpt-4o rates for OpenAI, Sonnet for Anthropic / other) and records the ADMITTED bound (spec: admit on the spent total, record 0.00027).
3. Entry threshold `spent + LLM_SPEND_ENTRY_RESERVE_USD >= cap` (R-S04-4); R31 / R32 seed cap - 0.05 (spec: 3.00); new admitted rows at cap - 0.15; the entry WARNING is asserted by prefix, cents tokens and suffix (a reserve_cents field is allowed).
4. /health shape `{lane: {exhausted, day}}` + `llm_spend_fail_open` (R-S04-7) instead of `{spent_usd, cap_usd, day}`; amounts on the admin row R36b; a fail-open counts as "the breaker ran".
5. Off-loop reads on the dedicated `llm-spend` pool of 4 (R-S04-2), not `asyncio.to_thread` / qaren-worker; R22 asserts the thread-name prefix and `_max_workers == 4`.
6. `admit_openai_dispatch` gains `response_format` and `tools` (R-S04-10) and returns an opaque ticket (lane, bound) instead of the lane, so the chokepoint can record the admitted bound; `record` / `record_soon` gain `admitted_usd=None`; `reserve` raises LLMUnavailableError on refusal and fails open; RESERVE_SCRIPT args = [ub, cap, expireat]. RED-defined API, for the gate.
7. P08 split: the identity half is PIN P08 (green at base); the accounting half ("N EVALs for N creates") is RED R42 (cannot be green at base).
8. P03 / P04 observe the entry via a `_compare_from_text_impl` stub / the L1 content-safety stub instead of the paid fan-out counter (same kill power: M02 / M03 killed; no egress, faster).
9. Every compare-driven row stubs `StructuredComparisonService._get_price` (the W1-3 harness's only egress measured): P08 / R42 are NEW sentinel-only netguard nodes (supabase.invalid L2 saves: a ratchet WARNING, exit 0), no egress-class node.
10. P01's base ledger literal is written as the rate expression (1000 x 0.15 + 200 x 0.60) / 1e6 with the base entry keys, equal to the base entry (green at base).
11. Rows added beyond spec 5 (rulings): R03 knob readers, R04b, R04c, R07b, R09b, R10b, R19b, R22b, R22c, R28b, R29b, R32c (route-level refund / no history / no lifetime), R34b, R36b, R39, R39b, R40, R40b, R40c, R42, R43 (E2), P09.
12. The comm-set rule follows the updated common brief (module-path readers); union with the spec's 314 = 334.
13. Step (2) of the brief ("files the review listed as not measured") lists no file; the spec's 1.10 NOT MEASURED trio (test_s81_s03_llm_ledger_v2, test_ci_gates, test_behavior_dimension_translation) ran in comm chunk 01: green.

## 6. Questions for the gate

- Q1 admit's fallback for a garbage bound (None / NaN / negative / str / bool): RED asserts only 0.001 < bound <= 3.0 (refuses at 2.999, admits at 0); the prototype uses the Sonnet-rate price of 16,384 output tokens (0.16384). Rule the constant (or the entry reserve)?
- Q2 R30 keeps the spec: a served response WITHOUT usage records nothing. R-S04-3's "never zero" could instead record the admitted bound for a usage-less served call (stream shape). Rule.
- Q3 "present only once the breaker has run": RED counts any fail-open (incl. `_client() is None`) as a run (R34b: `llm_spend: {}` + counter 1). Confirm.
- Q4 `exhausted` is asserted only far from the boundary (spent >= cap and spent + reserve >= cap both satisfy R34). Rule the exact predicate if it matters for the canary.
- Q5 R38 requires the CLAUDE.md row to contain `last-resort`, `S81-09`, `S81-24` (R-S04-11) and the eight knob names; confirm the wording constraint.
- Q6 E1 (the K1 re-record in tests/test_s81_s03_llm_ledger_v2.py) is not asserted here; K1 is green at base (comm chunk 01) and goes red on the GREEN edit by design.
- Q7 RESERVE_SCRIPT text is not pinned literally; the fakes accept a non-record script carrying INCRBYFLOAT, a `>` comparison and ARGV[2] (cap) with ARGV[3] the expiry.

## 7. Restore check

Real worktree: sha256 of all 3,417 tracked files identical before (15:59) and after (17:40) (`snap_before.json` == `snap_final.json`); `git status --short` = `?? tests/test_s81_s04_spend_breaker.py` only; HEAD dfc6502f. Scratch worktree removed (`git worktree remove --force`; `git worktree list` no longer shows it; it never held a node_modules junction); no `.qa-mutation.lock` left; no process with tag s04red alive; no `.env` anywhere in the notes folder. No git write in the real worktree; no file other than the new test file written there.
