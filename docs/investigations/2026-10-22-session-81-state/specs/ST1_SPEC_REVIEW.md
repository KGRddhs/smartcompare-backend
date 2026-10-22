# ST1 LOOP-STALL adversarial spec review

- Unit: ST1 LOOP-STALL, flag `ENABLE_USAGE_PATH_OFFLOOP`, worktree `sc-s81-st1` (detached at 95cf6f864b4e70980ca191daa064c0118e223c13, `git status --short` empty before and after; only this gitignored file written there).
- Spec reviewed: `.qa-s80/ST1_UNIT_SPEC.md`, sha256 e4830eb33bebf69eec1c0fccccec28eca2bdd28a4e1e8059a49b242f71317656 (re-hashed at 23:07, match).
- Reviewer: Opus 5.5 adversary, 2026-10-22 23:07-23:50 AST. Notes and raw probe output: `<scratchpad>/ST1_ADV/` (`notes.md`, `adv_out.jsonl`, `*.log`). Scratch copy with a prototype of the spec's design: `<scratchpad>/ST1_ADV/w/` (app, tests, data, scripts copied from the worktree; the 4 prototype app files and the 3 probe tests removed after the runs).
- Personal-data rule: synthetic ids only (`u-synthetic-1`); no value of any credential read or printed.

## Verdict

APPROVE_WITH_CHANGES. The base measurements hold (every AST digest, file:line, caller count, CRLF, the S77 inventory reasoning, the satisfiability of R5/R6/R7/R15/R22/R27, all re-measured below). Two MAJOR defects must be ruled or corrected before the RED phase: (MAJ-1) the awaited reviews L1 write in the shared FIFO pool inside the 10 s Phase-1 reviews cap is a new failure mode under ON that the spec presents as neutral; (MAJ-2) the blocking twins' query chains are unpinned (a twin that drops the `consumed_at IS NULL` filter and `.single()` survives every RED row as specified, measured). The binding unit text says "through `run_db`"; the spec ships a flag-free twin instead (Q1), which needs an explicit Fable ruling, not only a recommendation.

## Measured confirmations (no correction needed)

- AST digests (`sha256(ast.dump(node))[:16]`, base working copy): all 27 literals of spec 2.7 recomputed and equal (`consume_comparison_credit` cfe716e23081b31c ... `sync_db_offload_enabled` 8cf14184edf5ed67).
- `usage_service.py:712-758` / `:618-682` / `:519-544` / `:547-585` / `:588-615` / `:177-184` / `:331-430` as cited; `get_usage_status` has one caller (`usage_routes.py:12`), `check_usage_allowed` zero in `app/` and `scripts/`; `run_db` `db_offload.py:35-40`, `run_redis_offloop` `redis_offloop.py:98-111`, leaf pin `test_s77_redis_offloop.py:2072-2085`, RO17 pin `:2050-2066`, inventory `_HELPER = "run_redis_offloop"` exact-name match `:1839`, `:1846-1850`.
- `review_service.py` :682 / :693 / :726 / :733-737 / :753-754 / :767-768 / :811 / :832 / :873 / :913 / :952, `clean_review_citations` :158, `build_retailer_quotes_from_reviews` :269: as cited. Reviews Phase-1 cap 10.0 s (`structured_comparison_service.py:5784`).
- A9.json: 0 hits for "8.4", `run_db`, `redis_offloop` (the spec's correction of the brief is right); the figures are in R9.json and session-80 prod_evidence.json (health_check p95 8,372 ms ~49 sampled, usage_status p50 4,164 ms, Upstash p50 289 / p95 1,537 ms, trace 5915a2b6).
- Production state: `ENABLE_PRICE_PATH_REDIS_OFFLOOP` SET on web 2026-10-11 22:50 (session-77 ledger line 53), `ENABLE_SUPABASE_CLIENT_REUSE=false` 23:12 (line 60); no later ledger line (sessions 78-81) touches either, `ENABLE_SYNC_DB_OFFLOAD` / `ENABLE_ASYNC_REDIS_OFFLOAD` never set.
- Prototype of the spec's design (sections 2.1-2.4, written into the scratch copy only):
  - S77 inventory, RO17 and the leaf pin stay green with the flag unset: the 4.2 set (25 files) 667 passed.
  - R5/R6/R7 satisfiable: OP 0.15 s, every op off the loop thread (DB on `asyncio_*`, GETs on `redis-offloop_*`), heartbeat max gap 0.016 s, wall 0.152 s, all four ops overlapping, in both `ENABLE_SYNC_DB_OFFLOAD` states.
  - R15 satisfiable: cancel mid-gather -> `CancelledError`, no `[USAGE-OFFLOOP]` record, no op on the loop thread.
  - R22 satisfiable: 1-worker pool, cancel while the write is queued -> cancelled, the write lands after the blocker is released, `save_reviews` ran (scheduled before the await).
  - R27: `/api/v1/usage/status` bytes identical ON vs OFF (`free_paid_window`).
- D03 overlap: D03 5244f716 hunk `@@ -20,4 +20,6 @@` of `review_service.py` has line 20 (the `run_redis_offloop` import that ST1 edits) in its context = the textual rebase the spec names; D03's CLAUDE.md insert is after :478, ST1's after :477 (adjacent, the second named rebase). B4 0aac07f1 touches no ST1 app file.

## Refuted claims (measured truth, file:line at 95cf6f86)

1. Spec 1.1: "`dependencies=[Depends(require_paid_route_user)]` :577 -> `@limiter.limit("10/minute")` :578 (the brief's :578/:579 are :577/:578 at base)". Measured: `text_routes.py:577` is blank, `:578` is `@router.post("/compare", dependencies=[Depends(require_paid_route_user)])`, `:579` is `@limiter.limit("10/minute")` (worktree and `git show HEAD:` agree). The brief was right; the "correction" is wrong.
2. Spec 2.8 row "reviews race cancels during the awaited L1 write ... `CancelledError` propagates as at the race" (and 2.4 "writes durable and awaited") presented as neutral. Measured (probe D, prototype, pool 4 workers, four 1.0 s jobs submitted to the shared pool during the extraction as the catalog GETs do, `wait_for` cap 0.5 s standing in for the 10 s cap): flag OFF returns the reviews in 0.001 s with the S77 flag OFF and ON; ST1 ON times out at 0.505-0.512 s in both S77 states, so the extracted reviews are missing from that response (the write still lands, the L2 save ran). At base the inline write has no suspension point, so the race can never fire there. S77 RO19 measured FIFO waits of 0.5-3.4 s for small reads under 1-3 cold compares, on top of the L1 READ wait that production already pays (S77 ON); the reviews leg is "4-5 s + headroom" against 10 s. This is a new ON-state failure mode, absent from 2.8 as a degradation, from section 9 and from the canary list (MAJ-1).
3. Spec 5 R16 / 2.3 "the same select string, byte for byte" as the twins' pin. Measured: with the probe's permissive fakes (section 1.6 fakes, which the RED reuses), a twin mutant that drops `.is_("consumed_at", "null")` from `_active_bonus_blocking` AND `.single()` from `_tier_info_blocking` passes R16 as specified (2 passed, `st1adv-r16-mut`). No other row observes the query chain, so these mutants (a consumed redemption counted = an inflated displayed cap; a list `data` = AttributeError -> free fallback = a false paywall for premium users) survive the whole RED file (MAJ-2).
4. Spec 2.8 row "thread / pool submit raises -> one WARNING ..., then the base inline body: same response, loop blocked for that call". Incomplete: the gather children already dispatched keep running. Measured (probe C): a synchronous raise at the `run_db_offloop` call -> 4 inline ops; an asynchronous raise -> 6 ops (the two pool GETs ran off the loop, then all four reads again inline), i.e. duplicate Upstash GETs and Supabase reads, and with a past `reset_at` a possible second users UPDATE. R14's "the fallback ops ran on the main thread" depends on which patch form the RED author picks.
5. Spec 6 M17 "killed by R16, R8 (`free_reset_past`)". R8 cannot kill it: the reset changes only `referral_bonus_comparisons_this_month` / `referral_bonus_reset_at`, and `get_usage_status` returns neither (`monthly_bonus` is the redemptions sum, `usage_service.py:722,750`). Only R16 (and an op-multiset assertion in R5, which as written checks only "every recorded op is NOT on the main thread" and so passes vacuously when the UPDATE is not issued) can kill it.
6. Spec 5 R18 "RED (main when S77 OFF)": the `[s77=on]` node is GREEN at base (the S77 flag already dispatches the L1 read to the pool, `review_service.py:682`); it is a PIN node inside a RED row and would fail the RED gate's "RED fails at base" check.
7. Spec 1.6 literals and R8 "same key order via `list(d)`": the 1.6 literals are printed in sorted-key order. Base order (measured route bytes): `{"tier":"free","used":{"daily":2,"monthly":7,"lifetime":5},"limits":{"daily":3,"monthly":10,"monthly_base":10,"monthly_bonus":0,"lifetime_free":3},"remaining":{"daily":1,"monthly":3,"lifetime_free":0}}`.
8. Spec 2.4 "(mutant M16)" for the save-scheduled-after-the-await case: the table's M16 is the log-format mutant; the save-after-await mutant is M25.
9. Spec 4.2 / L8 "tests that patch the async helpers `_get_user_tier_info` / `_get_active_referral_bonus` to drive `get_usage_status` / `check_usage_allowed` go red" with the flag exported. Measured on the prototype with `ENABLE_USAGE_PATH_OFFLOOP=true` on the runner call: the 4.2 set -> exactly 5 red, all in `test_s77_redis_offloop.py` (`test_s6_reviews_l1_read_placement[off]`, `test_s6_reviews_l2_promotion_set_stays_inline[off]`, `test_s6_post_extraction_write_stays_inline_on`, `test_off_call_shapes_exact[S6]`, `test_off_no_new_suspension_on_hit_paths[s6_l1_hit-off]`); `test_m13_01_slowapi_middleware.py`, `test_retro_w1_9.py`, `test_home_routes.py` green ON. No usage test red. (Not a defect; the stated hazard is narrower than written.)
10. Spec L11 "two concurrent first reads after a past `reset_at` can both UPDATE, the same class as `ENABLE_SYNC_DB_OFFLOAD` ON at base". True of the code, but production runs with sync offload OFF, where the loop serialises the two calls. Measured (probe G, two concurrent `get_usage_status` on a past reset): OFF 1 UPDATE, ON 2. It is a new production behaviour (harmless: the INT counter is display-only per `usage_service.py:591-593`), and the limit must say so.
11. Spec 8.1 "Problem" sentence frames `/health` p95 8.4 s and `usage_status` p50 4.2 s as the usage path's defect. The cited trace 5915a2b6 shows `usage_status` 4,266 ms with child http spans under 0.8 s: the route is mostly a VICTIM of other loop blockers. ST1 removes the usage path's own loop occupancy (3-4 Supabase RTs + 2 GETs per call; the auth half stays, L2) and the reviews writes; it does not close the 8.4 s on its own. The row and the canary must not read a /health p95 drop as ST1's expected effect.

## Blocking issues (resolve before the RED phase)

- B1 = MAJ-1, the awaited reviews L1 write under pool load (refuted claim 2). Fable rules one of: (a) keep the awaited design, add a stated limit ("under pool load the reviews leg can exceed the 10 s Phase-1 cap at the write; the reviews persist (durable) but are missing from that response"), a canary item (reviews-leg timeout count and `_timed_task("reviews")` timing before/after), and a RED/PIN row that pins the documented behaviour; (b) recommended: dispatch the baseline write as a durable pool job WITHOUT awaiting it, on a snapshot taken on the loop (`copy.deepcopy(reviews)` before dispatch, because `reviews` is mutated afterwards at :750, :766 and :772 and a pool-thread `json.dumps` of a dict mutated on the loop can raise "dictionary changed size during iteration" and lose the write), keep the handle, and have each re-cache write await the previous handle before dispatching its own snapshot (FIFO order of the three writes kept; zero added wait when consult and YouTube are OFF, the CLAUDE.md :341 state for `ENABLE_REVIEW_SOURCE_CONSULT`); the L2 save stays scheduled first; R19/R21/R22/M24/M25 rewritten and a new row "busy pool + cap -> reviews returned under ON"; (c) leave the three post-extraction writes inline (S77 stated limit 1 kept) and move only the L1 read under ST1 (smallest diff; the brief's "L1 get/set off the loop" then becomes "get" only).
- B2 = MAJ-2, twin query chains (refuted claim 3). The RED fakes record per query the table, the full method chain WITH arguments (select string, `eq`/`gt`/`is_` args, `single`, update payload keys); R16 asserts the twin's chain == the async helper's chain for every state, and R5/R10 assert the exact op multiset per state. Add mutants M30 (drop the `is_` filter) and M31 (drop `.single()`), both killed by R16.
- B3 = Q1. The binding unit text (PLAN_S81 M1: "Supabase reads through `run_db`") and the plan's flip order ("`ENABLE_SYNC_DB_OFFLOAD` + ST1" in one window) conflict with the brief ("ST1's flag is independent and flips in its own window") and with the spec's flag-free `run_db_offloop`. The spec may not resolve a binding-text conflict by recommendation; a Fable ruling records which text wins.

## Corrections (non-blocking, apply in the RED author's brief)

1. R27 also asserts OFF `resp.content` == a base byte literal recorded at base (refuted claim 7 gives `free_paid_window`; record `premium_bonus` at base the same way); ON == OFF alone ties nothing to base (B1 rule: flag-OFF base bodies as literals).
2. R25 adds the OFF-tail digest: `sha256("\n".join(ast.dump(s) for s in fn.body[2:]))[:16]` at head == the base `fn.body[1:]` value: `get_usage_status` a6c1bf0a9952e9bc, `check_usage_allowed` 2ccc3c8b7bbd0659 (measured at base; the prototype's `body[2:]` matches both). This pins "the base body runs unchanged below the flag check" directly; `get_usage_status` / `check_usage_allowed` are otherwise the only edited usage functions with no digest.
3. R12 / R13 compare the OFF sequence and thread placement to the base-recorded 1.6 rows (literals), not only ON == OFF (an unconditional consume mutant keeps ON == OFF; only the R25 digest would catch it).
4. R14 fixes the patch form (raise synchronously at the call) and asserts the exact op list; a second node with an asynchronous raise documents the duplicate GETs; add the duplicate-read sentence to 2.8 and to section 9.
5. R18 `[s77=on]` relabelled PIN; the 21 RED / 11 PIN counts restated by node at the RED gate.
6. Section 1.6 literals restated in base key order (or R8 asserts key order against the route-bytes literal).
7. 2.4 "(mutant M16)" -> M25; delete the 1.1 text_routes "correction".
8. L11 restated as a production behaviour change (1 vs 2 UPDATEs measured), harmless because the counter is display-only.
9. 8.1 Problem sentence: usage_status is a victim of other loop blockers; ST1 removes its own occupancy; no /health p95 expectation in the canary, only "loop_lag_max_60s_ms not worse" plus the usage path metrics.
10. L8 replaced by the measured 5 S77 nodes (GREEN re-measures at HEAD in one runner call with the flag exported).
11. Autouse fixture: add `ENABLE_YOUTUBE_SOURCE` (the name the code reads, `review_service.py:1062`); the base probe deleted `ENABLE_YOUTUBE_REVIEW_SIGNAL`, which no code reads. Harmless while the consult fakes are patched, wrong as a hermeticity list.
12. M17's killer list: R16 only (plus the op-multiset R5 of correction B2).

## Contract risks

- MAJ-1 above: missing reviews in a response under pool load (ON only).
- The twins duplicate `_get_user_tier_info` / `_get_active_referral_bonus` and the two compute bodies duplicate the base bodies: S81-09 (device remaining + `resets_at` on `/usage/status`, the Riyadh date-key helper) must change both copies; R8/R16 catch drift only for the tested states. Q4.
- First production use of the shared admin Supabase client from `qaren-worker` threads concurrently with the loop thread (`ENABLE_SYNC_DB_OFFLOAD` has never been ON in production); the Redis half is already proven in production by S77 (pool threads on the shared Upstash client). Not measured on the pinned httpx 0.28.1 / postgrest 2.31.0 (Q7).
- Duplicate reads after a mid-gather dispatch failure (refuted claim 4).
- `/usage/status` latency under load can rise (FIFO behind catalog GETs, spec L3); the loop is freed but the Home/Paywall mount may not get faster.
- Not introduced by ST1, noted for the plan: the reviews L1 key (`get_reviews_cache_key(brand, name, variant)`) has no language or category axis; ST1 only moves its writes.
- Billing (R-A3): no ST1 path consumes, refunds, bumps the lifetime counter or writes history; consume/refund digests pinned. No refusal shape reaches build 3 (no new code, no new status, no 503). No camera-envelope interaction (image routes untouched).
- Sequencing: B4 (0aac07f1) edits comm-set tests (`test_paid_route_metering.py`, `test_retro_w2_1.py`, `test_prompt_fence.py`, `test_model_config_enforced.py`, `tests/w4_11_prompt_digest_recorder.py`); if B4 or D03 merges first, ST1's base comm-set run must be redone on the new main.

## Pin collisions

None in the brief's classes: T23 OpenAPI (route and its signature untouched, no response_model), FY25 digests (`test_s75_fanout_identity.py` fakes `svc._get_reviews`, so `review_service.get_reviews` never runs there), w4_11 prompt digests (no prompt), `test_retro_w2_1` URL pins, the W4-13 ledger fixture (consume/refund untouched), copy-policy fences (no copy). Section 4.1 = none is confirmed for CI (flag unset). With the flag exported only the 5 S77 nodes of refuted claim 9 go red (L8).

## Questions for the orchestrator

1. Q1: flag-free `run_db_offloop` (spec, matches the brief's "independent") or `run_db` (binding unit text, flips with `ENABLE_SYNC_DB_OFFLOAD`)? Record the winner in the rulings.
2. MAJ-1: option (a), (b) or (c)? Recommended (b).
3. Lanes: ST1 is lane A but edits `usage_service.py` (a lane-B file in the plan's lane list) and `review_service.py` (D03, lane B). Confirm no lane-B unit edits `usage_service.py` before ST1 merges, and that the S81-09 spec is cut after ST1 merges (two bodies, the twins, `_usage_reads_offloop` for the device GET).
4. Q4: keep the pure-insertion design (two compute copies) or let the base tail call `_usage_status_body` / `_usage_allowed_body` (one compute; OFF behaviour identical, pinned by the R8 literals + R9 order; the OFF-tail digest of correction 2 is then dropped)?
5. Q7: measure the concurrent use of one admin Supabase client from N threads on the pinned versions (local loopback stub) before GREEN, or carry it as a canary item?
6. M29 (keys computed inside the thread job) is reported equivalent by the spec; rule it.
7. The task asks probe copies to be deleted; the common brief forbids any recursive delete. The 4 prototype app files and 3 probe tests were removed one by one; the remaining scratch tree `<scratchpad>/ST1_ADV/w/` (base bytes, no junction, no .env) is left for the orchestrator to remove.

## Runs (bounded runner, one process at a time)

- `[pyt] tag=st1adv-probe start=2026-10-22 23:30:52 end=2026-10-22 23:31:09 elapsed=17s bound=600s status=OK rc=0` (12 passed; `[hermeticity] sentinel checked 12 test(s)`; `[netguard] blocked 0 attempt(s) from 0 node(s)`)
- `[pyt] tag=st1adv-pins-off start=2026-10-22 23:31:51 end=2026-10-22 23:32:37 elapsed=46s bound=1200s status=FAIL rc=1` (659 passed, 5 failed + 3 errors, all FileNotFoundError for scripts/, railway.json, Procfile missing from the first scratch copy; superseded by pins-off2)
- `[pyt] tag=st1adv-pins-on start=2026-10-22 23:33:14 end=2026-10-22 23:34:05 elapsed=51s bound=1200s status=FAIL rc=1` (flag exported ON: 662 passed, 5 failed = the S77 nodes of refuted claim 9)
- `[pyt] tag=st1adv-extra-on start=2026-10-22 23:34:34 end=2026-10-22 23:34:47 elapsed=12s bound=600s status=OK rc=0` (74 passed; `[netguard] blocked 2 attempt(s) from 2 node(s)`, the two `test_m13_01_slowapi_middleware.py` lockout sentinel nodes `neutralized.supabase.invalid:443`)
- `[pyt] tag=st1adv-route start=2026-10-22 23:36:08 end=2026-10-22 23:36:14 elapsed=6s bound=600s status=OK rc=0` (2 passed)
- `[pyt] tag=st1adv-r16-proto start=2026-10-22 23:37:32 end=2026-10-22 23:37:36 elapsed=3s bound=600s status=OK rc=0` (2 passed)
- `[pyt] tag=st1adv-r16-mut start=2026-10-22 23:37:38 end=2026-10-22 23:37:47 elapsed=9s bound=600s status=OK rc=0` (2 passed on the mutant = survivor; the file restored from its byte copy, sha256 prefix de2ca3220e7fe020 both)
- `[pyt] tag=st1adv-pins-off2 start=2026-10-22 23:44:26 end=2026-10-22 23:45:10 elapsed=44s bound=1200s status=OK rc=0` (flag unset: 667 passed; `[hermeticity] sentinel checked 667 test(s)`; `[netguard] blocked 2 attempt(s) from 2 node(s)`)

## NOT MEASURED

- The comm set (119 files) on the prototype, base or ON (the spec's base chunks were read, not re-run).
- The concurrent-client thread-safety of supabase 2.31.0 / httpx 0.28.1 (Q7).
- Real Upstash FIFO waits under ST1 ON (only RO19's S77 figures cited; probe D uses synthetic 1.0 s jobs).
- A RED file (not written by this role).
