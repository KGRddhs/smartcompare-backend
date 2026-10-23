# S81-04 SPEND-BREAKER: per-Asia/Riyadh-day USD caps on every dispatch through guarded_llm_create (dark, ENABLE_LLM_SPEND_BREAKER)

Lane B, PLAN_S81 M1, build order 6. Base `e1878dd8` (origin/main with #370 ST1; the rebase onto the moving main, now `98d85433` with S81-05, is the next step). Spec `.qa-s80/S81-04_UNIT_SPEC.md` as amended by its adversarial review, `RULINGS_S81_04` (R-S04-1..R-S04-11), the RED gate `GATE_S81_04` (GC-1..GC-14) and the fix-round rulings `RULINGS_FIX1_S81_04` (F1-1..F1-11), all in `docs/investigations/2026-10-22-session-81-state/specs/`. Every flag is OFF in production; this flag is a new name (unset by construction). Three commits on the base: `c4490e91` (feat), `b5f29e35` (docs, limit 15), and the fix-round-1 commit (the two adversaries on `b5f29e35`: correctness NOT_READY on one latent MAJOR, engineering SOUND).

## What the flag does

`ENABLE_LLM_SPEND_BREAKER` (read per call, the first statement of every gated branch) turns on a LAST-RESORT spend bound, not an abuse control (R-S04-8 / R-S04-11; about 140 compares a day at the 3 USD live default):

- New leaf `app/services/llm_spend_breaker.py`: four lanes (live, escalation, search, offclock), one Upstash key per lane and Riyadh day `llm_spend:<lane>:<YYYY-MM-DD>` (UTC+3 fixed, EXPIREAT next Riyadh midnight + 1 h), caps from `LLM_SPEND_CAP_{LIVE,ESCALATION,SEARCH,OFFCLOCK}_USD` (3.00 / 1.00 / 0.50 / 2.00).
- `guarded_llm_create` ADMITS every OpenAI chat completion on the chokepoint lane (`LLM_SPEND_CHOKEPOINT_LANE`, default live) BEFORE the W1-3 admission, from an upper bound priced by S81-03 `llm_pricing.price_call` (UTF-8 bytes as tokens + overheads + `response_format` / `tools` JSON bytes; the image part per MODEL (F1-7): 1,445 tokens for an id priced at the 4o rate row, `OPENAI_MINI_IMAGE_TOKENS_UPPER` = 37,000 for every other OpenAI id incl. the default vision model gpt-4o-mini (UNVERIFIED, for S81-07), 4,784 Anthropic, the largest for an unknown provider; `max_tokens` or 16,384); an unpriced model is bounded at the most expensive row of its provider; a garbage or ZERO bound takes the GC-3 fallback (F1-5: never a zero-cost admit); spent + bound > cap raises the existing `LLMUnavailableError` before any dispatch.
- A served response is RECORDED non-awaited (durable `fire_and_forget` task) with ONE Lua EVAL (INCRBYFLOAT + EXPIREAT) of its list price, or of the admitted bound when the model is unpriced or the response has no usage (GC-4); a raising / cancelled create records nothing.
- The lane total is memoised per process (`LLM_SPEND_MEMO_SECONDS`, 5 s) with this process's in-flight record deltas; concurrent readers of a lane share ONE in-flight GET (single flight, F1-4b), and a GET submitted before a record landed never lowers the memo below that record's total (F1-2). Every Redis command runs on a dedicated `llm-spend` pool of 4, bounded by `LLM_SPEND_REDIS_TIMEOUT_SECONDS` (0.5 s; async via `asyncio.wait_for`, sync via `future.result(timeout)`); no client = no hop; every Redis problem fails OPEN; a read failure or timeout opens a per-lane fail-open window as long as the memo window, inside which admit / entry / record fail open without a Redis hop, counted once per window (F1-4c).
- A shielded record that lands after its bound is counted in `llm_spend_late_records` with one INFO line, never as a fail-open (F1-4a); a sync record still queued at its bound is cancelled and its in-flight delta settled in a done-callback (F1-3).
- Both compare entries return the existing `LLM_UNAVAILABLE` envelope (REST coded 503 + refund, SSE `error` + refund) before any paid provider when spent + `LLM_SPEND_ENTRY_RESERVE_USD` (0.10) >= cap on the CHOKEPOINT lane (`chokepoint_lane()`, the lane the chokepoint charges, F1-6).
- `/health` gains `llm_spend` {lane: {exhausted, day}} + `llm_spend_fail_open` + `llm_spend_late_records` once the breaker ran in the process (no amounts); `GET /api/v1/admin/costs` gains `spend_breaker` (the amounts) only ON.
- `reserve(lane, ub)` returns a `ReserveTicket` (lane, bound_usd, the Riyadh day of the reserve, that day's EXPIREAT) and `settle(ticket, actual)` charges `actual - bound` to THE TICKET'S day and EXPIREAT, never the settle-time day (F1-1, the correctness MAJOR: a batch reserved at 23:50 Riyadh and settled at 02:00 left the new day's key at -1.1 and let reserves exceed the cap); the ticket is the binding contract for S81-16 / S81-21 / S81-22, stated in the leaf docstring with the rest of the dispatch contract. A negative stored total (only a pre-fix process wrote one) reads as 0 with one rate-limited WARNING per key.

Flag OFF: byte-identical on every response body and stored row (no admit, no record, no Lua, no thread hop, no task, no health key, no admin key) in a process where the flag was never ON; after a mid-process rollback `/health` keeps the `llm_spend*` keys until the restart (the snapshot reads `_STATE['ran']`, never the flag: the RO18 precedent).

## Defect / ruling ids -> node ids

All in `tests/test_s81_s04_spend_breaker.py` (267 nodes at HEAD). Measured on a scratch copy of the pre-fix bytes `b5f29e35` with the final unit file: 29 failed, every one an AssertionError (the 22 new F1 RED nodes + the 7 re-pinned nodes below), 238 passed (incl. the two new PIN rows r50 / r58). The GREEN measurement stands for the earlier rows (219 failed AssertionError-only / 16 passed on the frozen RED bytes at `e1878dd8`, GC-2).

| Id | What | Node(s) |
|---|---|---|
| spec 2.1 / 2.2 | the leaf, the import rule, the flag idiom, lanes, knob parsing, the Riyadh day, unknown lanes | r01, r02 (13), r03, r04 (44), r04b (33), r04c (7), r05 (4), r06 |
| spec 2.2 / R-S04-9 / R-S04-10 / F1-7 | prompt / image / output bounds (the image bound per model id), `price_call` bounds | r07 (12), r07b (8), r08 (6), r09 (5), r57 (8) |
| R-S04-3 (B2) / GC-3 / GC-4 / F1-5 | the conservative bound of an unpriced call, the sanitised admit bound (zero included), the admitted bound recorded | r09b (5), r19, r19b (5), r29, r29b, r30, r45, r55 (2) |
| spec 2.2 | admit: one GET, the existing refusal class + WARNING, strict boundary, missing key, per-call cap, day roll | r10 (4), r10b (4), r11, r12, r13, r20, r21 |
| spec 2.2 / 2.6 / GC-9 | record: one Lua EVAL with `%.10f` + EXPIREAT, invalid amounts, the redis-py shape, the pinned Lua texts | r14 (4), r15 (7), r16, r44 |
| spec 2.3 / F1-1 | fail-open + the rate-limited WARNING, bad stored value, the negative clamp | r17, r18 (3), r48 |
| R-S04-2 (B1) / F1-4 | the dedicated pool, the bounded read (async and sync), no client = no hop, the durable record task | r22, r22b, r22c, r58 |
| R-S04-4 / R-A3 / GC-6 / F1-6 | the entry reserve (REST + SSE; coded 503 / SSE error, refund once, no history row, no lifetime bump), the one exhausted predicate, the entry on the chokepoint lane | r23 (6), r31, r31b, r32, r32b, r32c (2), r46 (4), r56 (2) |
| spec 2.4 / R-S04-6 | the chokepoint: get -> create -> eval, refusal before the W1-3 admission, the W1-3 tail, raising / cancelled records nothing, the bound from kwargs (per model id), the lane knob | r24, r25 (2), r26, r27 (2), r28 (5), r28b (2), r37 |
| R-S04-7 / GC-5 / F1-4a | /health {exhausted, day} + the two counters (no amounts, no Redis command), a raising snapshot, the admin amounts | r33, r34, r34b, r35, r36, r36b, r52b |
| R-S04-1 / F1-2 | the memo (fresh / stale / knob), the local delta, a stale GET never undercounts a landed record, two overlapping records (each delta settled once, the base never down) | r39, r39b, r49, r50 |
| R-S04-5 / F1-1 | reserve (two parallel reserves admit exactly one), settle, reserve fail-open, the ticket across midnight, the zero actual and the non-ticket ValueError | r40, r40b, r40c, r47, r47b |
| F1-3 / F1-4 | the cancelled queued sync record, the late shielded record, single flight, the per-lane fail-open window, waiters of one failed GET counted once | r51, r52, r53, r54, r54b |
| R-S04-10 (P08) | ON with headroom: one EVAL per create, at most N + 1 reads; field-equal bodies OFF vs ON | r42, p08 |
| R-S04-11 / GC-7 | the CLAUDE.md row tokens (r38 extracts the row from its header to the next `**SESSION` header or EOF) | r38 |
| R-S04-8 (E2) | FY25 `UNIT_ENV` names the flag | r43 |
| B1 rule (PIN, green at base) | flag OFF under the FULL configuration (8 spellings), W1-3 ON + spend OFF, REST / SSE entries on an exhausted lane, /health, PROVIDER_CONFIGS, credential names, admin | p01 (8), p02, p03, p04, p05, p06, p07, p09 |

## Deliberate pin changes (spec 4.1)

| # | Pin | Change | Reason |
|---|---|---|---|
| E1 | `tests/test_s81_s03_llm_ledger_v2.py::test_k1_guarded_llm_create_untouched` (`K1_GUARDED_AST_SHA`) | re-recorded in `c4490e91` (CPython 3.12.9) with the reason in the comment; unchanged by the fix round (`guarded_llm_create` untouched) | GC-8 / R-S03-10. U3c pins untouched and green. |
| E2 | `tests/test_s75_fanout_identity.py` `UNIT_ENV` | `ENABLE_LLM_SPEND_BREAKER` appended | R-S04-8. |
| RED (GREEN) | `tests/test_s81_s04_spend_breaker.py` | R30 amended (GC-4), the fakes accept only the pinned Lua texts (GC-9), r44 / r45 / r46 | GATE_S81_04 |
| RED (fix 1) | `tests/test_s81_s04_spend_breaker.py` | re-pinned for the F1 API: r06 and r40b call `settle(ReserveTicket(...), actual)` (F1-1); r18 drops its `-1` case to r48 (F1-1 clamp); r07 image cases name their model id (+ `image_mini`, `image_nomodel`) and r28 carries a model per case (`image` = gpt-4o-mini 37,000, + `image_4o`) (F1-7); r33 allows `llm_spend_late_records` (F1-4); every other existing row byte-identical; new rows r47-r58 appended | RULINGS_FIX1_S81_04 |
| black | `.github/black-clean-paths.txt` | `app/services/llm_spend_breaker.py` joins the ratchet, the leaf black-formatted (26.5.1) in the same commit | F1-8, a deliberate ratchet change. `app/services/llm_pricing.py` does NOT join: measured not black-clean (black 26.5.1 would reformat it, 346 diff lines; the ruling's premise was not met), and reformatting S81-03's merged leaf is outside this unit (open question for the orchestrator). |

## Gates (fix-round-1 bytes)

| Gate | Result | [pyt] |
|---|---|---|
| RED step: the new rows on the pre-fix bytes in the worktree before any app edit | 28 failed (AssertionError only) / 237 passed | `[pyt] tag=s04f1-red start=2026-10-23 23:02:02 end=2026-10-23 23:02:20 elapsed=18s bound=600s status=FAIL rc=1` |
| the final unit file on a scratch copy of `b5f29e35` | 29 failed (AssertionError only) / 238 passed | `[pyt] tag=s04f1-prefix-red start=2026-10-23 23:42:04 end=2026-10-23 23:42:24 elapsed=20s bound=600s status=FAIL rc=1` |
| unit file, flag unset | 267 passed | `[pyt] tag=s04f1-unit-off4 start=2026-10-23 23:40:40 end=2026-10-23 23:40:49 elapsed=9s bound=600s status=OK rc=0` |
| unit file, flag exported ON | 267 passed | `[pyt] tag=s04f1-unit-on2 start=2026-10-24 00:11:22 end=2026-10-24 00:11:33 elapsed=11s bound=600s status=OK rc=0` |
| mutation table on the fix bytes (45 mutants: 20 re-runs over the touched functions (settle, reserve, the memo, `_read_spent`, `_valid_usd`, the reads, the record path, the snapshot) + 25 F1 mutants; the full unit file with `-x` per mutant; byte copy, exact edit, restore, sha256 compare) | 44 KILLED (42 by an AssertionError; M39 by a TypeError, M30 by the un-bounded read's LLMUnavailableError), 1 SURVIVED: M51 (the test-reset generation guard, ruled EQUIVALENT by F1-2); A02 and M50 (the adversary / GREEN survivors) KILLED by r50, M30s by r58 | per mutant in the fix report |
| CI-order set (24 files) in chunks of 8, flag unset | 219 + 478 + 1074 = 1771 passed | `[pyt] tag=s04f1-ci-off-1 ... status=OK`, `-2 ... status=OK`, `-3 ... status=OK` |
| the same set with the flag exported ON (limit 15) | 34 failed, the SAME 34 nodes as the GREEN (6 w04g /health, 7 S77 /health, 21 S81-03 OFF recorders); FY25, W4-13, T23, U3c, the CLAUDE.md readers and the unit file green ON | `[pyt] tag=s04f1-ci-on-2 ... status=FAIL`, `-3 ... status=FAIL` |
| hook `-k black` nodes (4 hook files; the leaf is now on the ratchet) | 4 passed, 323 deselected | `[pyt] tag=s04f1-hook-black start=2026-10-24 00:18:31 end=2026-10-24 00:22:45 elapsed=254s bound=1200s status=OK rc=0` |
| comm set (335 files, 14 chunks) at HEAD vs the GREEN base record | 6 failed nodes (the 4 `.pre_impl_failures.txt` rows + the 2 cold-tiktoken ERRORs); **branch-only-NEW EMPTY** | 14 `[pyt] tag=s04f1-comm-head-NN` lines in the fix report |

Lint: `ruff check --select E9,F63,F7,F82` clean on the 4 changed python files (+ F401 / F841 on the leaf and the unit file), `py_compile` clean, `black --check` clean on the leaf (the allowlist test `test_ci_gates::test_black_allowlist_entries_are_actually_clean` green); the added-line sweep found no personal value, 8-digit run or key shape; bytes > 127 in added lines: net 0 (the edited Feature Flags line of CLAUDE.md re-adds its 66 pre-existing bytes); CRLF kept on every edited CRLF file, the leaf and the unit file LF; the pre-commit hook ran on every commit.

## Stated limits

The full list is the CLAUDE.md row (limits 1-16). The load-bearing ones:

1. FAIL-OPEN on every Redis problem, with a per-lane fail-open window as long as the memo window after a read failure or timeout (counted once per window; a record inside a window is NOT recorded): a stalled Upstash costs at most one `LLM_SPEND_REDIS_TIMEOUT_SECONDS` wait per lane per window (before the window both adversaries measured every due read waiting the full bound: 3 admits + 1 entry check 2.02 s, 12 admits 6.06 s). During an Upstash outage there is NO code-side bound (the Console workspace limit is the outer bound). The herd thresholds on a healthy Upstash (engineering adversary, 0.18 s per command) are in the row; about 9+ queued EVALs can still push a due read past its bound.
2. Read-admit, not reserve, on the live lane: concurrent in-flight calls can overshoot a cap by their own bounds; another process's spend is seen at each own record EVAL and at each GET, a settle decrease only at a GET submitted after it (overcount, the safe direction).
3. A compare that crosses the cap mid-way has its later calls refused at the chokepoint: a refused verdict becomes a degraded, BILLED 200 through `generate_comparison`'s broad except; only the entry refusal is the refunded non-delivery (S81-06's R-S06-2 makes a mid-compare refusal a non-delivery under a role flag later). URL mode and the camera have no entry check (S81-04b).
4. One `live` lane for every user: an exhausted lane refuses every compare until 00:00 Asia/Riyadh (S81-09 / S81-24 are the abuse controls, flipped after the breaker).
5. Every refusal reaches the callers' existing exc_info ERROR logs = Sentry events once a lane is exhausted (S81-04c).
6. The gpt-4o-mini image bound (37,000) is UNVERIFIED by a web read (S81-07); over-bounding only refuses earlier near the cap.
7. Interpreter exit WAITS for queued shielded records on the non-daemon `llm-spend` threads (the warmer's last records land; exit blocks while Upstash is slow, the SDK transport unbounded while `ENABLE_UPSTASH_BOUNDED_TRANSPORT` is held).
8. `scripts/seed_spec_spine.py` and `scripts/shadow_experiments.py` dispatch outside `guarded_llm_create` and are not capped.
9. Upstash's acceptance of the two Lua scripts (the repo's first) is measured only at the canary.

## Owner steps (names only)

1. Nothing to set for the defaults; any of `LLM_SPEND_CAP_LIVE_USD`, `LLM_SPEND_CAP_ESCALATION_USD`, `LLM_SPEND_CAP_SEARCH_USD`, `LLM_SPEND_CAP_OFFCLOCK_USD`, `LLM_SPEND_ENTRY_RESERVE_USD`, `LLM_SPEND_MEMO_SECONDS`, `LLM_SPEND_REDIS_TIMEOUT_SECONDS`, `LLM_SPEND_CHOKEPOINT_LANE` on `web` only if a default is wrong (the caps are the owner's open ruling).
2. On `price-warmer`, set `LLM_SPEND_CHOKEPOINT_LANE=offclock` BEFORE the flag (R-S04-6), or never set the flag there.
3. Keep the Console workspace limit (decision 8) as the outer bound.
4. Activation precondition: with OpenAI serving, check daily compares x about 0.021 USD against the live cap; confirm every `OPENAI_MODEL_*` role id resolves to a priced row.
5. Flip after approval in the plan's flip order ("ledger, breaker, request context ON"), BEFORE any Anthropic flag (R-S03-9); one canary window with the owner's explicit yes (canary list in the CLAUDE.md row: `llm_spend_fail_open` flat after warm-up, `llm_spend_late_records` the slow-but-alive Upstash counter). Rollback: unset the variable (`/health` keeps the `llm_spend*` keys until the restart).

🤖 Generated with [Claude Code](https://claude.com/claude-code)
