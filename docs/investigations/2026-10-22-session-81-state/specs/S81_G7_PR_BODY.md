# S81-G7 FOLLOWUPS: D16b OPERATOR-INGEST-DATES + D17b COVERAGE-PAGING + D22c PROFILE-SELECT + VARHINT-RETIRE + D22d LEARNING-HARDENING

Base origin/main 05303c6f01348610fa7c813e6588c7cea4b89734 (post-#390); HEAD ce3ec2a7dcab4c96f436b551f7ab3dbc7bf6152e (branch feature/s81-g7-followups; 2 commits ahead: the replayed GREEN 4d73ebf8 (was 4b0f3b9c) and the final-round commit ce3ec2a7, both through the hook). A SAFE group of four units under LC-9 (R-G7-1): no migration, no client file, no auth / quota / legal / consent / security-middleware / Lua surface. ONE new flag, ENABLE_BEHAVIOR_PROFILE_REBUILD (default OFF, read per call); the other units ride existing dark flags; D22c (2) is an unflagged dead-code deletion (R-A1). Every flag is unset in production: nothing changes until an owner flip. Rulings specs/RULINGS_S81_G7.md (R-G7-1..12), RED gate specs/GATE_S81_G7.md (GC-1..GC-8), final round specs/RULINGS_REBASE_S81_G7.md (RB-G7-1..8). Reports: specs/S81_G7_RED_REPORT.md, specs/S81_G7_GREEN_REPORT.md, specs/S81_G7_ADV1_correctness.md (SOUND, 0 blocking / 0 major / 4 minors), the final-round REBASE_REPORT.md.

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

## Adversary minors (LC-4) and their dispositions
| id | finding | disposition |
|---|---|---|
| MIN-1 | no row drove `_read_by` across more than one 100-value chunk (ADV-O1 survived) | gate row G7-GR1 (RB-G7-1) + L-D22d-4 |
| MIN-2 | flag ON: a NULL full_response / missing category_used stores a "null" affinity key; v1 rows give [] products | stated limit L-D22c-6 (RB-G7-3); the spec's default-bucket sentence withdrawn (absent from the block and this body, grep-verified) |
| MIN-3 | the S81-G7 heading followed a list item with no blank line | fixed by the union: one blank line before the heading, after the S81-20 block (RB-G7-4) |
| MIN-4 | DEL escaping (ADV-O2) and the wrong-verdict-only counter (ADV-O4) unpinned | gate rows G7-GR2 / G7-GR3 (RB-G7-2) + L-D22d-4; ADV-O3 EQUIVALENT (OFF never reaches the normaliser) |

## Gate rows (NEW tests/test_s81_g7_gate_rows.py, sha256 dea4c5492bb5e858e120e080b70f651365cf2f87d5a9e1120aca4d121f2a1bd8; pure ASCII, LF)
| row | pins | mutant on a sha-verified byte copy of scripts/cron_learning.py | result |
|---|---|---|---|
| G7-GR1 | `_read_by` over 250 values: 3 IN chunks (100/100/50), 750 distinct rows, every request id-ordered; cap 700 -> 700 rows, `capped`, last range (0, 99) | ADV-O1 return after the first chunk | KILLED (AssertionError) |
| G7-GR2 | `_render` escapes DEL 0x7F as \x7f like 0x1F; a clean name unchanged | ADV-O2 DEL left raw | KILLED (AssertionError) |
| G7-GR3 | dropped count = wrong-verdict rows with an unclean field name only | ADV-O4 also count non-wrong unclean rows | KILLED (AssertionError) |
Restored after each mutant and sha-compared (6997e623... both ways) under .qa-mutation.lock (removed).

## Counts and gates (final round, at HEAD ce3ec2a7)
- The five RED files + the gate rows: 63 / 63 with the flag unset and 63 / 63 with ENABLE_BEHAVIOR_PROFILE_REBUILD=true in the runner env only. E1 / E2 files: 27 passed.
- The six frozen blobs at HEAD = GC-1 (6fd81d37 / 927dc060 / ff9b45da / 79a33372 / 15c5dc0f / 8c793a16). After the replay the unit's own diff is unchanged: `git diff 4b0f3b9c HEAD -- app scripts data tests` is exactly the #389/#390 delta 6869a3e6..05303c6f (patch-id equal), and every unit file's blob is identical.
- Mutants: RED round 31 applied, 30 KILLED, D22d-M7 EQUIVALENT (R-G7-9); adversary 34 on GREEN's bytes (survivors above); this round 3 / 3 KILLED.
- The 14 touched pin files: 946 passed + the 3 known env CRLF nodes (d16 r10, d17 r9, s19 r15). CI-order set (22 files incl. the gate rows): 1164 passed + the same 3. R8 pair 141 + 132 passed; test_paid_route_metering.py 21 / 21 with and without the flag; the six CLAUDE.md readers 510 passed.
- Corpus gate (`scripts/verify_flag_byte_identity.py --flags ENABLE_VARIANT_LLM_HINT,ENABLE_BEHAVIOR_PROFILE_REBUILD`, n=414, calls=1656): base 05303c6f d2e16d30076129b526be97c2b783150390333337f694c206e69ea891d0b263cf; HEAD d2e16d30076129b526be97c2b783150390333337f694c206e69ea891d0b263cf (equal; = GC-4).
- Comm set: 700 files at HEAD (GREEN's 699 + the gate-rows file) in 28 chunks of <= 25 (bound 1200; 6 chunks (01, 14, 16, 19, 20, 21) FAIL only on environmental nodes) + tests/test_secret_scan_static.py alone (31 passed): 26892 passed, 53 skipped, 39 xfailed, 17 FAILED/ERROR. Base record at 05303c6f (695 files present at base, set sha256 a0bfab95..., stored under harness/base_records/05303c6f.../) built by GC-9 per-file reuse: 501 files reused from the 6869a3e6 record ab9758ed... (unchanged since 6869a3e6, no reference to the six #390 modules, SmartCompareApp, CLAUDE.md or CLAUDE_MD, no glob walker), 194 run at 05303c6f in a removed junction-free scratch worktree (8 chunks + secret_scan alone); base FAILED set 17 = the same 17 environmental nodes (the cold-tiktoken pair tests/test_prompt_truth.py identical both sides). comm -13 EMPTY; comm -23 EMPTY.
- Fourteen backend-scanning client fences by path through the junction (jest 29.7.0, node v24.11.1): 13 / 14 suites, 236 passed, 4 failed = exactly the four config/nativeBundle.w37 drift nodes. FULL jest once (LC-7), figure from full.json: 410 suites, 3976 passed + 4 failed = the four config/nativeBundle.w37 drift nodes (d5, k2, k4, k5), 13 skipped, 13 todo (baseline 3,976 + the four).
- ruff 0.16.5 --select E9,F63,F7,F82 + py_compile clean on the 14 touched Python files; no whole-file diff; added text pure ASCII; no 64-hex literal, no keyword-named constant, no personal value.
- Hook test files: NOT MEASURED. The unit touches no .githooks file and the rulings do not rule the files out; run alone at the 1800 s ceiling, `-k "not dash"` (167 of 327 nodes) timed out: [pyt] tag=g7fin-hook-notdash elapsed=1804s status=TIMEOUT rc=124 (about 60 nodes reached, 3 F in tests/test_precommit_hook.py before the cut, unread); the re-run and the `-k dash` half did not fit the round's budget and were not run (the dash run was started by the driver and stopped at once by its own tag). The pre-commit hook itself ran green on both commits (ruff + gitleaks).
- Footprint vs origin/main: 17 paths = the 10 GREEN paths + the 6 frozen RED / golden files + the gate-rows file.

## Stated limits
- L-D16b-1: a capture up to 5 min ahead passes and serves as fresh with that as_of. L-D16b-2: rows already stored with a future last_seen stay (classify ignores them until the date passes; the enrich worker still sorts them last). L-D16b-3: no lower bound on captured_at.
- L-D17b-1: an id sort on every page read. L-D17b-2: the outer ORDER BY id re-sorts the kb_offers_latest view per page.
- L-D22c-6 (MIN-2, RB-G7-3; flip window): with the flag ON a comparison whose full_response is NULL or lacks category_used gives a None category key, stored in category_affinity as "null" (no app/ reader of category_affinity today); v1 rows (products under full_response.overview.products) give an empty products list through the alias.
- L-D22c-1: after the flip the scoring label becomes `behavioral` for profiled returning users (and the S81-18 would-hit line stops for them) while no weight moves until a client emits tab_switch. L-D22c-2: the ON comparisons select reads the products JSON subtree of up to 50 rows (fire-and-forget). L-D22c-3: a malformed dwell_ms still lands in the except arm. L-D22c-4: the live column set comes from the 2026-09-06 measured record, not re-probed. L-D22c-5: promotion into data/variant_hint_reference.json stays manual from the Redis cache.
- L-D22d-4 (MIN-1 / MIN-4, RB-G7-1 / RB-G7-2): the multi-chunk `_read_by`, the DEL escape and the wrong-verdict-only counter are pinned only by the GREEN-owned gate rows tests/test_s81_g7_gate_rows.py (G7-GR1..GR3), not by the frozen RED file.
- L-D22d-1: one extra request per 500 spec rows of a chunk (bounded by LEARNING_MAX_ROWS). L-D22d-2: kb_gaps field names are screened but not counted. L-D22d-3: a literal backslash-x typed in a stored name renders like an escaped control (the JSON report disambiguates).

## Owner steps (names only)
- Nothing to flip for D16b / D17b / D22d or D22c (2). After the merge re-read the next kb-coverage and learning DRY run logs.
- ENABLE_BEHAVIOR_PROFILE_REBUILD=true on web only after App Review approval and the owner's yes, alone in its own canary window; watch the `behavioral` scoring label share and the `Failed to update behavior profile` WARNING rate (expected to fall to 0); a dated ledger line; rollback = unset (per call).

## [NATIVE READ]
EMPTY (no client copy).

CLAUDE.md: the union kept main's S81-11 and S81-20 blocks, then ONE blank line and the S81-G7 block (five rows + the owner steps; L-D22c-6 and L-D22d-4 added in place); the :341 Feature Flags clause carries the S81-11, S81-20 and S81-G7 sentences in merge order; every other hunk of main kept; CRLF kept.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
