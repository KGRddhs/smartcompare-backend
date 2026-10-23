# S81-04 SPEND-BREAKER: per-Asia/Riyadh-day USD caps on every LLM dispatch (dark, ENABLE_LLM_SPEND_BREAKER)

Lane B, PLAN_S81 M1, build order 6. Base `e1878dd8` (origin/main with #370 ST1). Spec `.qa-s80/S81-04_UNIT_SPEC.md` as amended by its adversarial review, `RULINGS_S81_04` (R-S04-1..R-S04-11) and the RED gate `GATE_S81_04` (GC-1..GC-14), all in `docs/investigations/2026-10-22-session-81-state/specs/`. Every flag is OFF in production; this flag is a new name (unset by construction).

## What the flag does

`ENABLE_LLM_SPEND_BREAKER` (read per call, the first statement of every gated branch) turns on a LAST-RESORT spend bound, not an abuse control (R-S04-8 / R-S04-11; about 140 compares a day at the 3 USD live default):

- New leaf `app/services/llm_spend_breaker.py`: four lanes (live, escalation, search, offclock), one Upstash key per lane and Riyadh day `llm_spend:<lane>:<YYYY-MM-DD>` (UTC+3 fixed, EXPIREAT next Riyadh midnight + 1 h), caps from `LLM_SPEND_CAP_{LIVE,ESCALATION,SEARCH,OFFCLOCK}_USD` (3.00 / 1.00 / 0.50 / 2.00).
- `guarded_llm_create` ADMITS every OpenAI chat completion on the chokepoint lane (`LLM_SPEND_CHOKEPOINT_LANE`, default live) BEFORE the W1-3 admission, from an upper bound priced by S81-03 `llm_pricing.price_call` (UTF-8 bytes as tokens + overheads + `response_format` / `tools` JSON bytes; image parts 1,445 tokens OpenAI / 4,784 Anthropic; `max_tokens` or 16,384); an unpriced model is bounded at the most expensive row of its provider; spent + bound > cap raises the existing `LLMUnavailableError` before any dispatch.
- A served response is RECORDED non-awaited (durable `fire_and_forget` task) with ONE Lua EVAL (INCRBYFLOAT + EXPIREAT) of its list price, or of the admitted bound when the model is unpriced or the response has no usage (GC-4); a raising / cancelled create records nothing.
- The lane total is memoised per process (`LLM_SPEND_MEMO_SECONDS`, 5 s) with this process's in-flight record deltas; every Redis command runs on a dedicated `llm-spend` pool of 4 under `LLM_SPEND_REDIS_TIMEOUT_SECONDS` (0.5 s); no client = no hop; every Redis problem fails OPEN.
- Both compare entries return the existing `LLM_UNAVAILABLE` envelope (REST coded 503 + refund, SSE `error` + refund) before any paid provider when spent + `LLM_SPEND_ENTRY_RESERVE_USD` (0.10) >= cap on live.
- `/health` gains `llm_spend` {lane: {exhausted, day}} + `llm_spend_fail_open` once the breaker ran in the process (no amounts); `GET /api/v1/admin/costs` gains `spend_breaker` (the amounts) only ON.
- `reserve` / `settle` for the batch / search / cron submitters (R-S04-5) and the dispatch contract for S81-06 / S81-16 / S81-21 / S81-22 in the leaf docstring.

Flag OFF: byte-identical on every response body and stored row (no admit, no record, no Lua, no thread hop, no task, no health key, no admin key).

## Defect / ruling ids -> RED node ids

All in `tests/test_s81_s04_spend_breaker.py` (241 nodes at HEAD: 225 RED-at-base + 16 PIN; every RED fails at the base on an AssertionError only, measured 219 / 16 on the frozen bytes at `e1878dd8`, GC-2).

| Id | What | Node(s) |
|---|---|---|
| spec 2.1 / 2.2 | the leaf, the import rule, the flag idiom, lanes, knob parsing, the Riyadh day, unknown lanes | r01, r02 (13), r03, r04 (44), r04b (33), r04c (7), r05 (4), r06 |
| spec 2.2 / R-S04-9 / R-S04-10 | prompt / image / output bounds, `price_call` bounds | r07 (10), r07b (8), r08 (6), r09 (5) |
| R-S04-3 (B2) / GC-3 / GC-4 | the conservative bound of an unpriced call, the sanitised admit bound, the admitted bound recorded (unpriced, no usage) | r09b (5), r19, r19b (5), r29, r29b, r30 (amended by GC-4), r45 |
| spec 2.2 | admit: one GET, the existing refusal class + WARNING, strict boundary, missing key, per-call cap, day roll | r10 (4), r10b (4, kills M28), r11, r12, r13, r20, r21 |
| spec 2.2 / 2.6 / GC-9 | record: one Lua EVAL with `%.10f` + EXPIREAT, invalid amounts, the redis-py shape, the pinned Lua texts | r14 (4), r15 (7), r16, r44 |
| spec 2.3 | fail-open + the rate-limited WARNING, bad stored value | r17, r18 (4) |
| R-S04-2 (B1) | the dedicated `llm-spend` pool, the bounded read, no client = no hop, the durable record task | r22, r22b, r22c |
| R-S04-4 / R-A3 / GC-6 | the entry reserve (REST + SSE, orchestrator and route level: coded 503 / SSE error, refund once, no history row, no lifetime bump), the one exhausted predicate | r23 (6), r31, r31b, r32, r32b, r32c (2), r46 (4) |
| spec 2.4 / R-S04-6 | the chokepoint: get -> create -> eval, refusal before the W1-3 admission (no probe spent), the W1-3 tail, raising / cancelled records nothing, the bound from kwargs, the lane knob | r24, r25 (2), r26, r27 (2), r28 (4), r28b (2), r37 |
| R-S04-7 / GC-5 | /health {exhausted, day} + `llm_spend_fail_open` (no amounts, no Redis command, per-call), a raising snapshot, the admin amounts | r33, r34, r34b, r35, r36, r36b |
| R-S04-1 | the memo (fresh / stale / knob), the local delta counted at once | r39, r39b |
| R-S04-5 | reserve (two parallel 1.5 USD reserves vs 2.00 admit exactly one), settle, reserve fail-open | r40, r40b, r40c |
| R-S04-10 (P08) | ON with headroom: one EVAL per create, at most N + 1 reads; field-equal bodies OFF vs ON | r42, p08 |
| R-S04-11 / GC-7 | the CLAUDE.md row tokens | r38 |
| R-S04-8 (E2) | FY25 `UNIT_ENV` names the flag | r43 |
| B1 rule (PIN, green at base) | flag OFF under the FULL configuration (8 spellings), W1-3 ON + spend OFF, REST / SSE entries on an exhausted lane, /health, PROVIDER_CONFIGS, credential names, admin | p01 (8), p02, p03, p04, p05, p06, p07, p09 |

## Deliberate pin changes (spec 4.1)

| # | Pin | Change | Reason |
|---|---|---|---|
| E1 | `tests/test_s81_s03_llm_ledger_v2.py::test_k1_guarded_llm_create_untouched` (`K1_GUARDED_AST_SHA`) | re-recorded to `844692b2f` + `c86027a87add39de447c47b48e6c234a2d8d10e21d8a218c730bb9f` (CPython 3.12.9) with the reason in the comment; docstring names S81-04 | GC-8 / R-S03-10: the two insertions in `guarded_llm_create` (the admit before the W1-3 admission, the record after each served tail). U3c pins untouched and green. |
| E2 | `tests/test_s75_fanout_identity.py` `UNIT_ENV` | `ENABLE_LLM_SPEND_BREAKER` appended | R-S04-8: a developer `.env` must not move the FY25 digests. |
| RED | `tests/test_s81_s04_spend_breaker.py` | gate-named edits only: R30 amended (GC-4), the fakes accept only the pinned Lua texts + `RECORD_SCRIPT_PIN` / `RESERVE_SCRIPT_PIN` (GC-9), new rows r44 (GC-9), r45 (GC-3), r46 x4 (GC-6) | GATE_S81_04 |

## Gates

| Gate | Result | [pyt] |
|---|---|---|
| GC-2: the frozen RED file at `e1878dd8` | 219 failed (AssertionError only) / 16 passed | `[pyt] tag=s04g-base-red start=2026-10-23 17:54:28 end=2026-10-23 17:55:42 elapsed=74s bound=600s status=FAIL rc=1` |
| unit file, flag unset | 241 passed | `[pyt] tag=s04g-unit-off1 start=2026-10-23 18:18:40 end=2026-10-23 18:18:47 elapsed=7s bound=600s status=OK rc=0` |
| unit file, flag exported ON | 241 passed | `[pyt] tag=s04g-unit-on1 start=2026-10-23 18:19:07 end=2026-10-23 18:19:14 elapsed=7s bound=600s status=OK rc=0` |
| GC-12 mutation table on the GREEN bytes (43 RED rows + 6 gate-row mutants + 2 design mutants) | 49 KILLED, 2 SURVIVED (M50 / M51, GREEN-design, reported for a ruling) | per mutant in the GREEN report |
| CI-order set: the 23 spec-4.2 pin files (U3c, K1, FY25, W4-13, T23, CLAUDE.md readers, health pins) + the unit file | 1745 passed | `[pyt] tag=s04g-ci-order start=2026-10-23 18:33:46 end=2026-10-23 18:35:49 elapsed=124s bound=1200s status=OK rc=0` |
| FY25 nine digests, flag exported ON | 1 passed | `[pyt] tag=s04g-fy25-on start=2026-10-23 18:36:28 end=2026-10-23 18:36:33 elapsed=5s bound=600s status=OK rc=0` |
| GC-10 netguard ratchet on the unit report | rc=0, p08 / r42 sentinel-only WARNINGs; baseline untouched | `[pyt] tag=s04g-unit-ng start=2026-10-23 18:36:45 end=2026-10-23 18:36:55 elapsed=10s bound=600s status=OK rc=0` |
| hook `-k black` nodes | 4 passed | `[pyt] tag=s04g-hook-black start=2026-10-23 18:37:30 end=2026-10-23 18:40:56 elapsed=206s bound=1200s status=OK rc=0` |
| GC-1 comm set, 335 files, 14 chunks, base (scratch worktree of `e1878dd8`) and head | base 7 failed nodes, head 6 failed nodes; **branch-only-NEW EMPTY** (the 4 `.pre_impl_failures.txt` rows + the 2 cold-tiktoken ERRORs on both sides; one ST1 timing row base-only) | 28 [pyt] lines in the GREEN report section 4 |
| pin set with the flag exported ON (limit 15) | 34 failed / 1711 passed (13 /health superset pins, 21 S81-03 OFF recorder pins) | `[pyt] tag=s04g-ci-order-on start=2026-10-23 19:33:50 end=2026-10-23 19:35:08 elapsed=78s bound=1200s status=FAIL rc=1` |

Lint: `ruff check --select E9,F63,F7,F82` clean on the 8 changed python files (+ F401 / F841 clean on the leaf and the unit file), `py_compile` clean, the pre-commit hook passed both commits; 0 bytes > 127 added; CRLF kept on every edited CRLF file, new files LF.

## Stated limits

The full list is the CLAUDE.md row (limits 1-15). The load-bearing ones:

1. FAIL-OPEN on every Redis problem (no client, an error, a command slower than `LLM_SPEND_REDIS_TIMEOUT_SECONDS`, a bad stored value): admitted, not recorded, one rate-limited WARNING + the `llm_spend_fail_open` counter. During an Upstash outage there is NO code-side bound (the Console workspace limit is the outer bound), and a failure memoises nothing, so each due read waits up to the timeout before failing open (open question Q1).
2. Read-admit, not reserve, on the live lane: concurrent in-flight calls can overshoot a cap by their own bounds; another process's spend is seen when this process's memo expires (5 s); the record lands after the response.
3. A compare that starts under the entry reserve and crosses the cap mid-way degrades as on any LLM failure (parse failure / deterministic verdict), not as `LLM_UNAVAILABLE`; URL mode and the camera have no entry check (S81-04b).
4. One `live` lane for every user: an exhausted lane refuses every compare until 00:00 Asia/Riyadh (a last-resort cap; S81-09 / S81-24 are the abuse controls, flipped after the breaker).
5. Every refusal reaches the callers' existing exc_info ERROR logs (`extraction_service` parse / verdict, `image_routes` vision, `url_extraction_service`) = Sentry events once a lane is exhausted (S81-04c). Measured in the mutation logs: `ERROR app.services.extraction_service:...:2772 Comparison generation error: llm spend cap reached for lane live; dispatch suppressed`.
6. The OpenAI image bound 1,445 is the 4o rule (R-S04-9); a vision model billed at more tokens per tile is under-bounded at admit (the record uses the served usage; Q2).
7. Upstash's acceptance of the two Lua scripts (the repo's first) is measured only at the canary.

## Owner steps (names only)

1. Nothing to set for the defaults; any of `LLM_SPEND_CAP_LIVE_USD`, `LLM_SPEND_CAP_ESCALATION_USD`, `LLM_SPEND_CAP_SEARCH_USD`, `LLM_SPEND_CAP_OFFCLOCK_USD`, `LLM_SPEND_ENTRY_RESERVE_USD`, `LLM_SPEND_MEMO_SECONDS`, `LLM_SPEND_REDIS_TIMEOUT_SECONDS`, `LLM_SPEND_CHOKEPOINT_LANE` on `web` only if a default is wrong (the caps are the owner's open ruling).
2. On `price-warmer`, set `LLM_SPEND_CHOKEPOINT_LANE=offclock` BEFORE the flag (R-S04-6), or never set the flag there.
3. Keep the Console workspace limit (decision 8) as the outer bound.
4. Activation precondition: with OpenAI serving, check daily compares x about 0.021 USD against the live cap; confirm every `OPENAI_MODEL_*` role id resolves to a priced row.
5. Flip after approval in the plan's flip order ("ledger, breaker, request context ON"), BEFORE any Anthropic flag (R-S03-9); one canary window with the owner's explicit yes (canary list in the CLAUDE.md row). Rollback: unset the variable.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
