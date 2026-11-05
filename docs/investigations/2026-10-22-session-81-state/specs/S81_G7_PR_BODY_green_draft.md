# S81-G7 FOLLOWUPS: D16b OPERATOR-INGEST-DATES + D17b COVERAGE-PAGING + D22c PROFILE-SELECT + VARHINT-RETIRE + D22d LEARNING-HARDENING

Base 6869a3e655805afd3adbba43f99578dd79585934; HEAD 4b0f3b9c9192c3c6c69c883c0c4a60461aca9ec5 (branch feature/s81-g7-followups; one commit through the hook). A SAFE group of four units under LC-9 (R-G7-1): no migration, no client file, no auth / quota / legal / consent / security-middleware / Lua surface. ONE new flag, ENABLE_BEHAVIOR_PROFILE_REBUILD (default OFF, read per call); the other units ride existing dark flags; D22c (2) is an unflagged dead-code deletion (R-A1). Every flag is unset in production: nothing changes until an owner flip. Rulings specs/RULINGS_S81_G7.md (R-G7-1..12), RED gate specs/GATE_S81_G7.md (GC-1..GC-8).

## D16b OPERATOR-INGEST-DATES (rides ENABLE_OPERATOR_INGEST / ENABLE_KB_FIRST_SERVE / ENABLE_KB_COVERAGE_ROLLUP)
- `kb_serve.FUTURE_SKEW_SECONDS = 300` (R-G7-4) and one rule `kb_serve.beyond_skew(moment, now)` (exactly now + 300 s accepted, now + 301 s refused).
- `kb_operator.OperatorIngest` gains a `captured_at` field validator (naive read as UTC, clock = the `_now` seam): a future capture fails body validation with the existing 422 VALIDATION_ERROR (no new code, zero client calls). Flag OFF: the dependency 404 comes first (P1 with a future body).
- `kb_serve.classify`: a `last_seen` beyond the skew is treated like an unreadable one (skipped), so it never shadows a genuine offer. `cron_kb_coverage._past` does the same for the fresh share and both age medians.
- RED tests/test_s81_d16b_operator_dates.py: 8 RED + 4 PIN (P1 x4 spellings).

## D17b COVERAGE-PAGING (rides ENABLE_KB_COVERAGE_ROLLUP)
- `cron_kb_coverage._paged` orders every page by `PAGE_ORDER_COLUMN = "id"` (R-G7-5; every paged relation, the kb_offers_latest view included, carries id).
- The host pipeline uses the live_robots form `getattr(pipe, "exec", None) or getattr(pipe, "execute")` (upstash-redis 1.7.0: exec runs, its one-argument execute only queues; redis-py 8.1.0: execute).
- RED tests/test_s81_d17b_coverage_paging.py: 3 RED + 3 PIN (report + upsert bytes for a table under 500 rows unchanged).

## D22c PROFILE-SELECT (1) + VARHINT-RETIRE (2)
- (1) NEW `ENABLE_BEHAVIOR_PROFILE_REBUILD` (R-G7-2 / R-G7-3), read per call by `structured_comparison_service.behavior_profile_rebuild_enabled()` as the first statement of `_update_behavior_profile`. ON: comparisons select `category_used:full_response->>category_used, products:full_response->products, created_at`, user_events select `event_type, metadata:event_data`; `_profile_rows_v2` normalises a non-list products to [] and a non-dict metadata to {}. OFF: the same two base select strings and the same except arm, pinned by the golden tests/fixtures/s81_d22c_flag_off_golden.json (three scenarios x five OFF spellings). The `behavior_profile_update` label and both call sites unchanged.
- (2) `price_service._VARHINT_LEARNED_PATH`, `_varhint_append_learned`, its one call and data/variant_hint_learned.json (git rm) deleted; the Redis verdict cache stays the only store; the comment and docstring rewritten.
- RED tests/test_s81_d22c_profile_select.py (5 RED + P1 x5, P2-P4) and tests/test_s81_d22c_varhint_retire.py (4 RED + P5).

## D22d LEARNING-HARDENING (rides ENABLE_LEARNING_JOB)
- `cron_learning._read_by`: id-ordered pages of PAGE_SIZE per 100-value chunk until a short page, never past the cap (R-G7-7; closes L14).
- An unclean kb_feedback field name counts once per row in `dropped_deidentify` (still maps to `other`); kb_gaps names are not counted (R-G7-8). Plumbed through the internal `dropped_fields` of `_gather`; report and metric names unchanged.
- `_render` escapes C0 / C1 controls as \xNN and U+2028 / U+2029 as \uNNNN (a backslash is not doubled; D22d-M7 equivalent by R-G7-9) at the three render sites (the markdown exemplar line, the exemplar and eval_case log lines); the JSON report keeps raw names.
- RED tests/test_s81_d22d_learning_hardening.py: 6 RED + 5 PIN (P5 x6 spellings).

## Deliberate pin changes (E-rows)
| E | file | change | reason |
|---|---|---|---|
| E1 | tests/test_variant_llm_hint_b3b.py | the `no_learned_write` fixture deleted and removed from its 13 signatures | it patched the deleted `_varhint_append_learned` (R-G7-6); V4 replaces its intent (no data/ write) |
| E2 | tests/test_s81_g5_gate_rows.py | GR6 `dropped_deidentify == 0` -> `== 6` + the docstring sentence | D22d counts the six unclean field-name rows (R-G7-7) |

## Counts and gates
- RED nodes: 60 (26 RED, AssertionError-only at base, + 34 PIN). At HEAD 60 / 60 with the flag unset and 60 / 60 with ENABLE_BEHAVIOR_PROFILE_REBUILD=true in the runner env only.
- Mutants (RED round, byte copies): 31 applied, 30 KILLED, D22d-M7 EQUIVALENT by R-G7-9. Table: specs/S81_G7_RED_REPORT.md (S81-G7_red/mutations_final.json).
- The 14 touched pin files: 946 passed + the 3 known env CRLF nodes (d16 r10, d17 r9, s19 r15). CI-order set: 1161 passed + the same 3.
- Corpus gate (`scripts/verify_flag_byte_identity.py --flags ENABLE_VARIANT_LLM_HINT,ENABLE_BEHAVIOR_PROFILE_REBUILD`, n=414, calls=1656): base d2e16d30076129b526be97c2b783150390333337f694c206e69ea891d0b263cf (RED, GC-4) == HEAD d2e16d30076129b526be97c2b783150390333337f694c206e69ea891d0b263cf.
- Comm set: the 691-file set (sha256 ab9758ed...) + 4 GREEN re-derivation members (substring hits on `_render*`, all green at HEAD) + the 5 RED files: 28 chunks of <= 25 (bound 1200) + tests/test_secret_scan_static.py alone (31 passed). Base record REUSED (LC-6): base_records/6869a3e6.../ab9758ed....txt (17 environmental nodes). HEAD FAILED set = the same 17; comm -13 EMPTY.
- Fourteen backend-scanning client fences by path through the junction (jest 29.7.0, node v24.11.1): 13 / 14 suites, 236 passed, 4 failed = exactly the four config/nativeBundle.w37 drift nodes. The full jest runs once in the final round (LC-7).
- ruff --select E9,F63,F7,F82 + py_compile clean on the eight edited Python files; the six frozen files byte-identical to GC-1 before and after the commit; no whole-file diff; added text pure ASCII; no 64-hex literal, no keyword-named constant, no personal value.
- Gate lines: S81-G7_green/GATE_LINES.txt; logs under S81-G7_green/ (units_off.log, units_on.log, pins.log, ciorder.log, comm/, fences.log, gate_head.log).

## Stated limits
- L-D16b-1: a capture up to 5 min ahead passes and serves as fresh with that as_of. L-D16b-2: rows already stored with a future last_seen stay (classify ignores them until the date passes; the enrich worker still sorts them last). L-D16b-3: no lower bound on captured_at.
- L-D17b-1: an id sort on every page read. L-D17b-2: the outer ORDER BY id re-sorts the kb_offers_latest view per page.
- L-D22c-1: after the flip the scoring label becomes `behavioral` for profiled returning users (and the S81-18 would-hit line stops for them) while no weight moves until a client emits tab_switch. L-D22c-2: the ON comparisons select reads the products JSON subtree of up to 50 rows (fire-and-forget). L-D22c-3: a malformed dwell_ms still lands in the except arm. L-D22c-4: the live column set comes from the 2026-09-06 measured record, not re-probed. L-D22c-5: promotion into data/variant_hint_reference.json stays manual from the Redis cache.
- L-D22d-1: one extra request per 500 spec rows of a chunk (bounded by LEARNING_MAX_ROWS). L-D22d-2: kb_gaps field names are screened but not counted. L-D22d-3: a literal backslash-x typed in a stored name renders like an escaped control (the JSON report disambiguates).

## Owner steps (names only)
- Nothing to flip for D16b / D17b / D22d or D22c (2). After the merge re-read the next kb-coverage and learning DRY run logs.
- ENABLE_BEHAVIOR_PROFILE_REBUILD=true on web only after App Review approval and the owner's yes, alone in its own canary window; watch the `behavioral` scoring label share and the `Failed to update behavior profile` WARNING rate (expected to fall to 0); a dated ledger line; rollback = unset (per call).

## [NATIVE READ]
EMPTY (no client copy).

CLAUDE.md: ONE S81-G7 block after the S81-G5 block (five rows + the owner steps) and the :341 Feature Flags pointer clause; CRLF kept. The final round unions it after the S81-11 / S81-20 blocks.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
