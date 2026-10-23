# S81-04 SPEND-BREAKER: adversary report, lens CORRECTNESS (Opus 5.5)

| Header | Value |
|---|---|
| Unit | S81-04 SPEND-BREAKER, `ENABLE_LLM_SPEND_BREAKER` (lane B) |
| HEAD verified | `b5f29e352bfbe786ab67728c921cf4ba9ef053c0` (sc-s81-s04, branch feature/s81-s04-spend-breaker, `git status` empty at start and end) |
| Base | `e1878dd836e721d7e8c6c53fe1aa3d2b9fadb83e` |
| RED file | `tests/test_s81_s04_spend_breaker.py` = `1e389248f2ce...56de1` at start and end; the frozen `8e4b0e53...edd4` (copy `S04_red/`) differs by exactly 5 hunks: GC-9 Lua pins + fakes narrowed, GC-4 R30 amended, new r44 (GC-9), r45 (GC-3), r46 x4 (GC-6). All gate-named (GATE_S81_04 GC-3/4/6/9); accepted. |
| Scratch | `<scratchpad>/S81-04_adv_correctness` (detached at b5f29e35; files sha-identical to the checkout before and after; removed, `git worktree list` clean), `<scratchpad>/S81-04_adv_base` (detached at e1878dd8 + the HEAD RED file; removed). Neither held a node_modules junction. No .env anywhere in the notes folder. |
| Verdict | **NOT_READY** (1 MAJOR, latent; 0 blocking) |

## 1. Runs (every pytest through pyt.py, one at a time)

| Run | Result | [pyt] |
|---|---|---|
| unit file, flag unset | 241 passed | `[pyt] tag=s04adc-unit-off start=2026-10-23 19:54:38 end=2026-10-23 19:54:45 elapsed=7s bound=600s status=OK rc=0` (`[hermeticity] sentinel checked 241 test(s)`, `[netguard] blocked 24 attempt(s) from 2 node(s)`: r42 + p08 sentinel only) |
| unit file, `ENABLE_LLM_SPEND_BREAKER=true` | 241 passed | `[pyt] tag=s04adc-unit-on start=2026-10-23 19:54:56 end=2026-10-23 19:55:03 elapsed=7s bound=600s status=OK rc=0` (`[hermeticity] sentinel checked 241 test(s)`, same netguard line) |
| HEAD RED file at the base e1878dd8 | 225 failed / 16 passed; 225 `E AssertionError`, no other class (PR body claim "225 RED-at-base + 16 PIN" true) | `[pyt] tag=s04adc-base-red start=2026-10-23 20:25:07 end=2026-10-23 20:25:37 elapsed=31s bound=600s status=FAIL rc=1` |
| GREEN CI-order set (24 files incl. the unit file), flag unset | 1745 passed | `[pyt] tag=s04adc-ci-order start=2026-10-23 20:18:56 end=2026-10-23 20:20:19 elapsed=84s bound=1200s status=OK rc=0` (`[hermeticity] sentinel checked 1745 test(s)`, `[netguard] blocked 165 attempt(s) from 9 node(s)`) |
| FY25 nine digests + W4-13 flag-OFF ledger + U3c pins, flag ON | 34 passed | `[pyt] tag=s04adc-fy25-on start=2026-10-23 20:20:46 end=2026-10-23 20:21:03 elapsed=17s bound=600s status=OK rc=0` |

## 2. Mutation table (my own byte-copy harness `mutate_adv.py`, the full unit file per mutant, `-x`; restore sha-verified every time; `.qa-mutation.lock` created and removed)

Spec-table mutants re-expressed by hand on the GREEN bytes (15):

| # | Mutant | Status | First killer | [pyt] |
|---|---|---|---|---|
| M01 | chokepoint admit not gated (`if True:`) | KILLED (assert) | test_r37_chokepoint_and_entry_wiring_static | `[pyt] tag=s04adc-m01 start=2026-10-23 20:05:09 end=2026-10-23 20:05:17 elapsed=7s bound=600s status=FAIL rc=1` |
| M02 | REST entry flag operand -> True | KILLED (assert) | test_r37 | `[pyt] tag=s04adc-m02 start=2026-10-23 20:05:19 end=2026-10-23 20:05:27 elapsed=8s bound=600s status=FAIL rc=1` |
| M04 | admit `>` -> `>=` | KILLED (the SUT raised LLMUnavailableError where the row admits) | test_r12_strict_boundary | `[pyt] tag=s04adc-m04 start=2026-10-23 20:05:28 end=2026-10-23 20:05:34 elapsed=7s bound=600s status=FAIL rc=1` |
| M05 | lane_exhausted `>=` -> `>` | KILLED (assert) | test_r23[2.50-0.5-True] | `[pyt] tag=s04adc-m05 start=2026-10-23 20:05:38 end=2026-10-23 20:05:49 elapsed=11s bound=600s status=FAIL rc=1` |
| M09 | EXPIREAT line removed from RECORD_SCRIPT | KILLED (assert) | test_r14[live] | `[pyt] tag=s04adc-m09 start=2026-10-23 20:05:51 end=2026-10-23 20:06:04 elapsed=13s bound=600s status=FAIL rc=1` |
| M12 | Riyadh offset 0 | KILLED (assert) | test_r03 | `[pyt] tag=s04adc-m12 start=2026-10-23 20:06:05 end=2026-10-23 20:06:11 elapsed=6s bound=600s status=FAIL rc=1` |
| M28 | live cap for every lane | KILLED (assert) | test_r04[None-None-escalation] | `[pyt] tag=s04adc-m28 start=2026-10-23 20:06:12 end=2026-10-23 20:06:18 elapsed=6s bound=600s status=FAIL rc=1` |
| M29 | memo never stale | KILLED (assert) | test_r39 | `[pyt] tag=s04adc-m29 start=2026-10-23 20:06:19 end=2026-10-23 20:06:34 elapsed=15s bound=600s status=FAIL rc=1` |
| M33 | RESERVE_SCRIPT without the check | KILLED (assert) | test_r40 | `[pyt] tag=s04adc-m33 start=2026-10-23 20:06:35 end=2026-10-23 20:06:44 elapsed=10s bound=600s status=FAIL rc=1` |
| M35 | local delta not added | KILLED (DID NOT RAISE) | test_r39b | `[pyt] tag=s04adc-m35 start=2026-10-23 20:06:47 end=2026-10-23 20:06:59 elapsed=12s bound=600s status=FAIL rc=1` |
| M37 | entry reserve ignored | KILLED (assert) | test_r23[2.95-None-True] | `[pyt] tag=s04adc-m37 start=2026-10-23 20:07:02 end=2026-10-23 20:07:12 elapsed=10s bound=600s status=FAIL rc=1` |
| M40 | settle sign reversed | KILLED (assert) | test_r40b | `[pyt] tag=s04adc-m40 start=2026-10-23 20:07:13 end=2026-10-23 20:07:22 elapsed=9s bound=600s status=FAIL rc=1` |
| M43 | fail-open counter += 0 | KILLED (assert) | test_r34b | `[pyt] tag=s04adc-m43 start=2026-10-23 20:07:23 end=2026-10-23 20:07:30 elapsed=8s bound=600s status=FAIL rc=1` |
| M49 | GC-4: a usage-less served response records nothing | KILLED (assert) | test_r30 | `[pyt] tag=s04adc-m49 start=2026-10-23 20:07:32 end=2026-10-23 20:07:40 elapsed=8s bound=600s status=FAIL rc=1` |
| M50 | in-flight delta never subtracted | **SURVIVED** (as GREEN reported) | - | `[pyt] tag=s04adc-m50 start=2026-10-23 20:07:41 end=2026-10-23 20:07:49 elapsed=8s bound=600s status=OK rc=0` |

Adversary mutants (20):

| # | Mutant | Status | First killer | [pyt] |
|---|---|---|---|---|
| A01 | entry fail-open (exception arm) returns True (fail-closed) | KILLED | test_r22b | `[pyt] tag=s04adc-a01 start=2026-10-23 20:09:28 end=2026-10-23 20:09:35 elapsed=7s bound=600s status=FAIL rc=1` |
| A01b | entry no-client arm returns True | KILLED (assert) | test_r17 | `[pyt] tag=s04adc-a01b start=2026-10-23 20:09:36 end=2026-10-23 20:09:42 elapsed=6s bound=600s status=FAIL rc=1` |
| A02 | `_observe_write_locked` base = total (no max: out-of-order EVAL totals can lower the base) | **SURVIVED** | - | `[pyt] tag=s04adc-a02 start=2026-10-23 20:09:43 end=2026-10-23 20:09:53 elapsed=9s bound=600s status=OK rc=0` |
| A03 | /health snapshot ignores the memo's day (exhausted for an earlier day) | **SURVIVED** | - | `[pyt] tag=s04adc-a03 start=2026-10-23 20:09:54 end=2026-10-23 20:10:05 elapsed=11s bound=600s status=OK rc=0` |
| A04 | /health snapshot ignores the in-flight deltas | **SURVIVED** | - | `[pyt] tag=s04adc-a04 start=2026-10-23 20:10:06 end=2026-10-23 20:10:13 elapsed=7s bound=600s status=OK rc=0` |
| A05 | admin snapshot ignores the in-flight deltas | **SURVIVED** | - | `[pyt] tag=s04adc-a05 start=2026-10-23 20:10:14 end=2026-10-23 20:10:21 elapsed=7s bound=600s status=OK rc=0` |
| A06 | `_record_amount` prefers the admitted bound over the actual | KILLED (assert) | test_r24 | `[pyt] tag=s04adc-a06 start=2026-10-23 20:10:22 end=2026-10-23 20:10:29 elapsed=7s bound=600s status=FAIL rc=1` |
| A07 | KEY_GRACE_SECONDS 0 | KILLED (assert) | test_r05 | `[pyt] tag=s04adc-a07 start=2026-10-23 20:10:30 end=2026-10-23 20:10:36 elapsed=6s bound=600s status=FAIL rc=1` |
| A08 | lane_exhausted uses the live cap for every lane | KILLED (assert) | test_r34 | `[pyt] tag=s04adc-a08 start=2026-10-23 20:10:37 end=2026-10-23 20:10:49 elapsed=12s bound=600s status=FAIL rc=1` |
| A09 | record durability shield removed (`awaitable = future`) | **SURVIVED** | - | `[pyt] tag=s04adc-a09 start=2026-10-23 20:10:50 end=2026-10-23 20:11:05 elapsed=16s bound=600s status=OK rc=0` |
| A10 | `_fail_open` does not mark the breaker as ran (GC-5) | KILLED (KeyError reading the absent /health key) | test_r34b | `[pyt] tag=s04adc-a10 start=2026-10-23 20:11:06 end=2026-10-23 20:11:13 elapsed=7s bound=600s status=FAIL rc=1` |
| A11 | stream entry refusal without `return` | KILLED (assert) | test_r32 | `[pyt] tag=s04adc-a11 start=2026-10-23 20:11:15 end=2026-10-23 20:11:44 elapsed=29s bound=600s status=FAIL rc=1` |
| A12 | settle skips negative deltas | KILLED | test_r40b | `[pyt] tag=s04adc-a12 start=2026-10-23 20:11:47 end=2026-10-23 20:12:17 elapsed=30s bound=600s status=FAIL rc=1` |
| A13 | output bound ignores max_tokens | KILLED (assert) | test_r08[args0-800] | `[pyt] tag=s04adc-a13 start=2026-10-23 20:12:20 end=2026-10-23 20:12:41 elapsed=21s bound=600s status=FAIL rc=1` |
| A19 | memo view ignores the day | KILLED (assert) | test_r21 | `[pyt] tag=s04adc-a19 start=2026-10-23 20:12:42 end=2026-10-23 20:12:49 elapsed=6s bound=600s status=FAIL rc=1` |
| A22 | conservative bound from the cheapest row | KILLED | test_r09b | `[pyt] tag=s04adc-a22 start=2026-10-23 20:12:50 end=2026-10-23 20:12:55 elapsed=6s bound=600s status=FAIL rc=1` |
| A23 | prompt bound drops `tools` | KILLED | test_r07[tools] | `[pyt] tag=s04adc-a23 start=2026-10-23 20:12:56 end=2026-10-23 20:13:04 elapsed=8s bound=600s status=FAIL rc=1` |
| A24 | prompt bound drops the extra message keys (GREEN deviation 8) | SURVIVED (more conservative than the spec; harmless) | - | `[pyt] tag=s04adc-a24 start=2026-10-23 20:13:05 end=2026-10-23 20:13:12 elapsed=7s bound=600s status=OK rc=0` |
| A25 | a zero bound is sanitised to the fallback | SURVIVED (harmless; see m7) | - | `[pyt] tag=s04adc-a25 start=2026-10-23 20:13:13 end=2026-10-23 20:13:21 elapsed=8s bound=600s status=OK rc=0` |
| A26 | chokepoint lane always live | KILLED (assert) | test_r03 | `[pyt] tag=s04adc-a26 start=2026-10-23 20:13:24 end=2026-10-23 20:13:55 elapsed=31s bound=600s status=FAIL rc=1` |

Counts: 35 mutants; 27 KILLED, 8 SURVIVED (M50, A02, A03, A04, A05, A09 = unpinned behaviour; A24, A25 = harmless). 14 of the 15 spec-table mutants KILLED (M50 is GREEN's own survivor).

## 3. Runtime probes (hermetic: a fake redis-py-shaped client, no network, no .env)

- `probe_settle.py` (the MAJOR): `reserve("offclock", 1.5)` at 23:50 Riyadh on 2026-10-23, `settle("offclock", 1.5, 0.4)` at 02:00 Riyadh on 2026-10-24 -> store `{'llm_spend:offclock:2026-10-23': '1.5', 'llm_spend:offclock:2026-10-24': '-1.1'}`; next-day `admit` -> GET -> `ValueError` (negative) -> fail-OPEN; next-day reserves of 1.5 against the 2.00 cap: `[True, True, 'refused', 'refused']` = 3.0 USD held on a 2.0 cap.
- `probe_race.py`: `record_soon("live", 0.5)` then `admit_async("live", 0.5)` with a stale memo, cap 1.6, stored 1.0: in the NATURAL loop ordering (no forced interleaving) the GET reads 1.0, the EVAL lands 1.5 and settles its in-flight delta, then `_observe_read` overwrites the base with 1.0: first admit ADMITTED (true 1.5 + 0.5 = 2.0 > 1.6), memo view 1.0 vs Redis 1.5, a second admit also ADMITTED. Float grid of `lane_exhausted` vs exact cents (4 caps x 50 reserves x boundary cents): 0 mismatches.
- `probe_pool.py`: (1) sync `record()` whose job is still QUEUED when the bound expires (pool of 4 saturated, timeout 0.1): `future.cancel()` drops the job, Redis stays 1.0, the in-flight entry `[0.5, 1]` is never settled, memo view 1.5, `admit(0.2)` against cap 1.6 REFUSED (true 1.2): a fail-open turned into a false refusal for the rest of the Riyadh day in that process. (2) the async `record_soon()` queued behind the same saturation lands after release (the shield works; Redis 1.5, in-flight empty) but `llm_spend_fail_open` counted 1. (3) a stalled GET: 3 admits + 1 entry check took 2.02 s, `fail_open=4`, memo `{}` (nothing memoised).

## 4. Findings

### MAJOR

1. `settle(lane, ub, actual)` (app/services/llm_spend_breaker.py `settle`, R-S04-5) applies its `actual - ub` delta to the key of the Riyadh day AT SETTLE TIME (`riyadh_day()` inside settle), not the day the reserve was taken on. A batch reserved before 00:00 Asia/Riyadh and settled after it drives the new day's key NEGATIVE (measured: -1.1): every GET-based admit / entry check on that lane then fails open (`_read_spent` ValueError) and the RESERVE Lua (`cur + ub > cap`) admits reserves beyond the cap by `ub - actual` (measured: 3.0 USD held against the 2.00 offclock cap), while the old day keeps the full reserved bound. The offclock lane exists for Batch submissions (S81-16 / S81-22), whose results routinely land hours after submission, so a cross-midnight settle is the normal case, not an edge. LATENT: no production caller of reserve / settle in this unit; but the leaf docstring states the reserve/settle contract as BINDING on S81-16 / S81-21 / S81-22 and the CLAUDE.md row advertises it, and R40 / R40b pin only a single-day timeline. Fix (small, keeps every row green): carry the reserve's day (a ticket, or `settle(..., day=)` / a returned day) and settle against that day's key and EXPIREAT; add a row (reserve at 23:50 Riyadh, settle at 02:00: the D key ends at `actual`, the D+1 key untouched) and a mutant (settle on today's key).

### MINOR (documentation rulings / follow-ups)

1. Memo undercount race (live path, flag ON): `_observe_read` replaces the base with a GET total read BEFORE a concurrent record EVAL that already landed and settled its in-flight delta, dropping that record from the memo until the next EVAL observation or the memo expiry (5 s). Reproduced in the natural ordering record_soon -> admit with a stale memo (the common sequential pattern after a call longer than 5 s). Magnitude about one call's actual cost, transient, the same order as the stated concurrency overshoot (limit 3). The GREEN report's design note "Overlap errs toward overcounting ..., never undercounting" is false. Fix option: in `_observe_read`, keep `max(entry.base, total)` when the same-day entry was written after the GET was submitted (a per-lane write sequence); a two-operation row would pin it.
2. Sync `record()` / `_run_bounded_sync`: a job still queued when the bound expires is cancelled and its in-flight delta is never settled (probe_pool 1): a permanent per-process overcount for the Riyadh day and false refusals, i.e. a fail-open event becomes fail-closed (R-S04-2 says every Redis problem fails open). Latent (no sync caller in this unit; the docstring binds scripts / workers / reserve-fail-open callers to `record`). Fix: settle the flight in a done-callback when the future is cancelled.
3. A shielded record that times out and lands later is still counted in `llm_spend_fail_open` and logged "admitting and not recording" (probe_pool 2): the canary item "`llm_spend_fail_open` 0" over-reads on a slow-but-alive Upstash.
4. Upstash stall cost (GREEN Q1, measured): a failed or timed-out read memoises nothing, so every due read (each chokepoint admit and the entry check) waits the full `LLM_SPEND_REDIS_TIMEOUT_SECONDS` (4 x 0.5 s = 2.02 s measured). Row limit (8) states only the healthy round trip; the stall cost belongs in the row (or the proposed fail-open window).
5. Mid-compare chokepoint refusal (row limit 5): generate_comparison's broad except (extraction_service.py ~:2772) turns the refusal into a degraded 200 (`comparison.error`, template winner), which the route METERS like any degraded result; PLAN M1 reads "over-cap = the existing LLM_UNAVAILABLE non-delivery with refund", which holds only for the entry refusal (R-S04-4 accepted the residual). The row should say the degraded compare is billed.
6. Vision bound (R-S04-9 premise; row limit 7 states the effect): the default vision model is gpt-4o-mini (model_config `_ROLE_DEFAULTS["vision"]`); from memory of OpenAI's vision cost table (UNVERIFIED, no web read) mini bills 2,833 base + 5,667 per tile, so the 1,445-token bound under-bounds a camera admit by up to about 0.007 USD per image. Records use the served usage.
7. `_sanitized_bound` docstring "never a zero-cost admit" is false: `_valid_usd` accepts 0, so `admit(lane, 0)` admits at zero (A25 survives). Not reachable through the chokepoint (priced bounds are > 0).
8. Two scripts dispatch chat completions outside the chokepoint (`scripts/seed_spec_spine.py:382`, `scripts/shadow_experiments.py:999`); the leaf's opening line "caps on every LLM dispatch" overstates (the row's "through guarded_llm_create" is accurate).
9. Row limit (3) wording: another process's spend is also seen at each of this process's own record EVALs (the EVAL returns the global total, and each EVAL refreshes the memo), and a process that records more often than every 5 s never GETs, so another process's settle decrease is never seen (overcount, safe direction).
10. The entry check hard-codes `LANE_LIVE` while the chokepoint charges `chokepoint_lane()`: they diverge if `LLM_SPEND_CHOKEPOINT_LANE` is ever set on `web` (owner step (b) names price-warmer only).
11. GC-3 wording vs code: a PRICED model with a missing max_tokens is bounded at its own rate x 16,384 (R08 / R28), the conservative per-provider rate applies only to a garbage bound and to an unpriced model (the RED report's Q1 scope). Consistent with the rows; the gate text says "garbage or missing max_tokens".

## 5. Prove-nothing rows / unpinned claims

- `test_r22_..._record_is_durable`: the "durable" half asserts only that the task is in `_BACKGROUND_TASKS`; removing the shield (A09) survives. A row that saturates the pool, times the record out, releases, and asserts the EVAL landed and the in-flight entry cleared would kill A09.
- `test_r14` / `test_r39b`: one record in flight only; M50 (in-flight never subtracted) survives; no row has two overlapping records or out-of-order EVAL totals (A02 survives).
- No row interleaves a stale-memo GET with a landing record (MINOR 1).
- `test_r33` / `test_r34` / `test_r36b`: the snapshots are never read with an in-flight delta (A04, A05 survive) or with an earlier-day memo (A03 survives; GREEN deviation 11 unpinned).
- `test_r40` / `test_r40b`: reserve / settle on one Riyadh day only (MAJOR 1).
- `test_r19b`: the zero bound is not a parameter (A25).
- `test_r07`: the extra-message-key bytes (GREEN deviation 8) are not pinned (A24, harmless).

## 6. Claims checked true against the code

- Flag-OFF identity: the chokepoint reads the flag before any admit and records only with a ticket; both entries short-circuit on the flag before the await; admin block ON-only; /health `{}` until the breaker ran (M01, M02, A11 killed; P01-P09 green; the CI-order set 1745 passed OFF; FY25 nine digests + W4-13 ledger + U3c green ON).
- Error-handler mapping: the entry refusal returns `_llm_unavailable_envelope()` (code LLM_UNAVAILABLE) -> text_routes `_surface_comparison_failure` -> HTTPException(503, {code, error}) (the 503 -> FEATURE_DISABLED default is overridden by the supplied code); SSE yields `error`; R32c proves 503 + one refund + no save + no lifetime bump on both surfaces.
- Billing R-A3 at the entry: refund once, no history row, no lifetime bump (R32c). Mid-compare: see MINOR 5.
- Contract freeze (PLAN section 0): flag OFF byte-identical; ON adds only additive /health keys, the admin-only `spend_breaker` block and refusals through the existing LLM_UNAVAILABLE envelope build 3 renders.
- The refusal text carries none of "429" / "rate" / "quota" (extraction_service.py:2669 fallback matcher), so a refused verdict dispatches no second call.
- Upstash shape measured on the pinned upstash-redis 1.7.0: `Redis.eval(self, script, keys=None, args=None)`, class module `upstash_redis.client` (the `_eval` dispatch matches); redis-py 8.1.0 positional shape used otherwise.
- The Riyadh day / EXPIREAT arithmetic (next Riyadh midnight = 21:00 UTC, + 3600 s) and the strict admit / inclusive entry predicates (GC-6, float grid 0 mismatches).
- `/health` exhausted and the entry check share `lane_exhausted` (GC-6); a fail-open counts as ran (GC-5, A10 killed).

## 7. NOT MEASURED

- Upstash's real EVAL acceptance and latency (no live call, canary item).
- The gpt-4o-mini image token rule (no web read; MINOR 6 is a recollection).
- The comm set, ruff / py_compile, the hook nodes (engineering lens).

## 8. Final state

- sc-s81-s04: HEAD `b5f29e35`, `git status --short` empty, RED file `1e389248...` unchanged, leaf `d3a7ae96...` unchanged; never edited.
- Both scratch worktrees removed; no mutation lock left; no pytest process of mine alive; no .env in `<scratchpad>/S81-04_adv/`.
- Notes and probes: `<scratchpad>/S81-04_adv/` (notes.md, probe_race.py / .out, probe_pool.py / .out, probe_settle.py / .out, mutate_adv.py, mut_M.json, mut_A.json, mut_logs/).
