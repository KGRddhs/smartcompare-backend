## S81-14 KB-SCHEMA: migrations 045 + 047 and the pure leaf `kb_service` (no flag, inert)

Unit S81-14 of PLAN_S81 (M4, lane B). Branch `feature/s81-s14-kb-schema`, one commit `0910e7d0` on base `98d85433` (origin/main = e1878dd8 + #371 S81-05; no file shared with S81-05). Spec `.qa-s80/S81-14_UNIT_SPEC.md`, review `.qa-s80/S81-14_SPEC_REVIEW.md`, rulings `specs/RULINGS_S81_14.md` (R-S14-1..R-S14-16) as amended by the RED gate `specs/GATE_S81_14.md` (GC-1..GC-10), in `docs/investigations/2026-10-22-session-81-state/`.

### What the "flag" does

There is NO runtime flag. The unit adds no call site:

- `migrations/045_kb_core.sql` (+ rollback): ten service-role tables `kb_merchants`, `kb_products`, `kb_variants`, `kb_offers`, `kb_images`, `kb_specs`, `kb_reviews`, `kb_gaps`, `kb_feedback`, `kb_coverage_daily`; the view `kb_offers_latest` (security_invoker); five SECURITY INVOKER functions with a pinned search_path (`kb_gtin_check_digit_ok(text)`, `kb_set_updated_at()`, `kb_prune_offers(integer, integer)`, `kb_prune_feedback(integer)`, `kb_product_card(text, text DEFAULT 'en')`); three BEFORE UPDATE triggers (updated_at on kb_merchants / kb_products / kb_variants). RLS on, no policy, REVOKE ALL from PUBLIC, anon, authenticated and service_role, then one GRANT to service_role. Refuses PostgreSQL < 15. WRITTEN, NOT APPLIED.
- `migrations/047_012_revoke.sql` (+ rollback): the eight 012 policies on product_specs / product_prices / product_reviews dropped by name, every privilege revoked from PUBLIC, anon and authenticated, service_role re-granted SELECT / INSERT / UPDATE / DELETE. WRITTEN, NOT APPLIED. App code is unaffected: every 012 reader and writer uses the service-role client (pinned by P3).
- `app/services/kb_service.py`: a pure leaf (no I/O, log, clock, env read or flag; never raises): `kb_product_id`, `kb_variant_key`, `kb_source_allowed`, `canonical_offer_url`, `gtin_check_digit_ok`, the deny-belt helpers, the offer observation contract constants `KB_OFFER_OBSERVATION_KEY` / `KB_OFFER_UPSERT_SET`, and one row builder per table whose keys equal the 045 columns. No importer in app/ or scripts/ (P1); no kb_* relation literal outside the leaf (P2).
- `.sqlfluff`: `large_file_skip_byte_limit = 0` (R-S14-12): sqlfluff 4.3.0 silently skips a file above 20,000 bytes with exit 0 and 045 is 23,141 bytes; 0 lints every file (037 still lints; the 037 pin accepts 0).
- `CLAUDE.md`: the apply-record line gains "045 / 047 WRITTEN, NOT APPLIED"; the SESSION 81 S81-14 row follows the S81-05 row (anchor order B1, B3, B4, D03, S81-03, ST1, S81-05, S81-14) and names the `.sqlfluff` change.

Main invariant (NO-CALLER identity): every response, log line, Redis and Supabase call is byte-identical to base; the FY25 nine digests and the W4-13 45-scenario ledger run unedited and green (comm set).

### Defect / ruling ids -> RED node ids

| id | what | RED / PIN nodes (tests/test_s81_kb_schema.py) |
|---|---|---|
| M18 CD-db-rls-03, PLAN A2 | 012 policies let the anon key read / insert / update the L2 cache | test_s14_r17_047_statements, test_s14_r18_policy_census_closed, test_s14_r16_rollbacks, test_s14_r19_headers, test_s14_p03_012_clients_are_admin |
| BL1 / R-S14-1 (RF1, C1-C3, K1, K2) | latest offer / prune by last_seen, market axis, card DISTINCT ON without the view, the observation contract | test_s14_r13_view, test_s14_r14_card, test_s14_r15_prune_offers, test_s14_r12_indexes, test_s14_r04_columns[kb_offers], test_s14_r04b_table_constraints[kb_offers], test_s14_r28d_offer_observation_contract |
| BL2 / R-S14-2 (RF2, RF10, C16) | kb_merchants holds its first writer's data (registry, platform_confidence text, status / deny / blocked_reason, no deny CHECK), the updated_at trigger | test_s14_r04_columns[kb_merchants], test_s14_r04b_table_constraints[kb_merchants], test_s14_r09b_merchants_carry_no_deny_check, test_s14_r15d_updated_at_trigger_function, test_s14_r03_045_objects, test_s14_r28b_builders_accept, test_s14_r28c_merchant_builder_never_calls_the_deny_rule |
| BL3a / R-S14-3 | the juice id includes the concentration; SKU = juice + ml | test_s14_r22_kb_product_id, test_s14_r22b_kb_product_id_rules, test_s14_r23_kb_variant_key, test_s14_p04_spine_key_literals |
| BL3b / R-S14-4 (RF9, K6) | nullable pseudonymous device_key, partial one-vote index, kb_prune_feedback | test_s14_r04_columns[kb_feedback], test_s14_r04b_table_constraints[kb_feedback], test_s14_r12_indexes, test_s14_r15b_prune_feedback, test_s14_r19_headers, test_s14_r28b_builders_accept |
| BL4 / R-S14-10 (C4, C7, C10, C11) | pins that kill the schema mutants | test_s14_r04_columns, test_s14_r04b_table_constraints, test_s14_r15_prune_offers, test_s14_r15c_gtin_sql_body, test_s14_r22_kb_product_id (recorder) |
| R-S14-5 (RF3, RF4) | size 0 / > 5000 ml -> '-', decimal / gift-set limits pinned | test_s14_r23_kb_variant_key, test_s14_p04_spine_key_literals |
| R-S14-6 (RF5, C14, K7) | one deny rule, derived SQL belts, source_hint host / URL only | test_s14_r09_deny_label_belts, test_s14_r24_source_allowed, test_s14_r25c_regex_constants_equal_the_sql, test_s14_r28_builders_refuse |
| R-S14-7 (RF6, C8) | canonical_offer_url applies the 045 host regex, refuses userinfo / port / IDN | test_s14_r25_canonical_offer_url, test_s14_r25b_junk_never_raises |
| R-S14-8 (RF7, C12) | P1 / P2 exact names | test_s14_p01_no_importer_of_kb_service, test_s14_p02_no_kb_relation_literal_outside_the_leaf |
| R-S14-9 (RF8, C6) | placeholder identity mints no id | test_s14_r22b_kb_product_id_rules |
| R-S14-11 (C9, K4) | builders mirror every CHECK | test_s14_r27_builder_keys, test_s14_r28_builders_refuse, test_s14_r28b_builders_accept, test_s14_r29_leaf_never_raises_on_junk |
| R-S14-12 (C13) | sqlfluff lints every file | test_s14_r20_sqlfluff_lints_every_file, test_s14_p05_every_migration_is_linted_by_sqlfluff, test_s14_r20b_ascii |
| R-S14-13 (K3) | kb_specs.lang + card p_lang fallback | test_s14_r04_columns[kb_specs], test_s14_r04b_table_constraints[kb_specs], test_s14_r14_card |
| R-S14-14 (K8, C17) | ids under the production flag state; the dotenv order | test_s14_p04_spine_key_literals, test_s14_p08_flag_env_survives_the_dotenv_imports |
| R-S14-15 (Q1, Q6, Q8) | `audience`, the 050 grant form, 047 revokes ALL | test_s14_r05_service_role_only, test_s14_r06_functions, test_s14_r08_no_user_column_census, test_s14_p07_043_fence_and_census_green, test_s14_r17_047_statements |
| spec 2.4 / R21 | the leaf is pure | test_s14_r21_leaf_pure, test_s14_r01_files_exist_once, test_s14_r02_one_transaction, test_s14_r07_fks, test_s14_r10_reviews_source_and_no_text, test_s14_r11_concentration_enum, test_s14_r26_gtin, test_s14_p06_identity_nodes_untouched |

### Deliberate pin changes (spec 4.1)

| # | pin | change |
|---|---|---|
| none edited | - | no existing test is edited |
| gains node ids | `tests/test_migration_index_predicate_immutability.py::test_index_predicates_are_immutable` | two new parametrised ids `[045_kb_core.sql]`, `[047_012_revoke.sql]` (green): chunk A 625 -> 627 |
| later units | `test_s14_p01` / `test_s14_p02` | deliberate-change points for S81-15 (KB_MERCHANTS_TABLE), S81-17 and S81-18 |

### Gates (bounded runner; every [pyt] line)

- RED file at base 98d85433 (GC-6, first gate): `[pyt] tag=s14g-red-base start=2026-10-23 23:22:16 end=2026-10-23 23:22:37 elapsed=21s bound=600s status=FAIL rc=1` -- 344 failed (344 `E AssertionError` lines, no other exception class, no ERROR node), 58 passed; `[hermeticity] sentinel checked 402 test(s)`; `[netguard] blocked 0 attempt(s) from 0 node(s)`. The failed set equals the RED report's.
- Unit file at HEAD: `[pyt] tag=s14g-unit-head start=2026-10-23 23:42:37 end=2026-10-23 23:42:44 elapsed=8s bound=600s status=OK rc=0` -- 402 passed; with ENABLE_DATA_GUARDS_V2=true, ENABLE_EXACT_PRICE_GATE=false, ENABLE_NORMALIZE_WORDS_EMPTY_FIX=true exported for the runner call only: `[pyt] tag=s14g-unit-head-envx start=2026-10-23 23:43:03 end=2026-10-23 23:43:11 elapsed=8s bound=600s status=OK rc=0` -- 402 passed; at the commit: `[pyt] tag=s14g-unit-final start=2026-10-24 00:30:18 end=2026-10-24 00:30:38 elapsed=19s bound=600s status=OK rc=0` -- 402 passed.
- Mutation table on the GREEN bytes (GC-10): 65 / 65 KILLED (M1-M64 with M37a/b), AssertionError only, every restore sha-verified, the worktree sha-identical before / after (3,427 files), lock removed. Each run `status=FAIL rc=1`, 8-16 s (e.g. `[pyt] tag=s14g-m1 ...`). One GREEN-added mutant M65 (numeric rounding back to ROUND_HALF_EVEN) SURVIVES: `[pyt] tag=s14g-m65 start=2026-10-24 00:29:44 end=2026-10-24 00:29:52 elapsed=8s bound=600s status=OK rc=0` (no RED row sits on a half tie; a pin needs a test addition).
- Comm set (67 files = the RED's 66 + `tests/test_s81_s05_request_context.py`, which S81-05 added and which walks app/ and scripts/ as source), 7 chunks, base 98d85433 vs HEAD:
  - A base `[pyt] tag=s14g-base-A start=2026-10-23 23:26:31 end=2026-10-23 23:28:02 elapsed=91s bound=1200s status=OK rc=0` 625 passed / head `[pyt] tag=s14g-head-A start=2026-10-24 00:10:03 end=2026-10-24 00:10:39 elapsed=36s bound=1200s status=OK rc=0` 627 passed; netguard 12 from 6 both sides.
  - B1 base `[pyt] tag=s14g-base-B1 start=2026-10-23 23:29:05 end=2026-10-23 23:30:00 elapsed=55s bound=1200s status=OK rc=0` 377 / head `[pyt] tag=s14g-head-B1 start=2026-10-24 00:10:52 end=2026-10-24 00:11:11 elapsed=19s bound=1200s status=OK rc=0` 377.
  - B2 base `[pyt] tag=s14g-base-B2 start=2026-10-23 23:30:15 end=2026-10-23 23:31:33 elapsed=78s bound=1200s status=OK rc=0` 736 / head `[pyt] tag=s14g-head-B2 start=2026-10-24 00:11:24 end=2026-10-24 00:12:47 elapsed=83s bound=1200s status=OK rc=0` 736.
  - B3 base `[pyt] tag=s14g-base-B3 start=2026-10-23 23:32:14 end=2026-10-23 23:33:48 elapsed=94s bound=1200s status=OK rc=0` 645 / head `[pyt] tag=s14g-head-B3 start=2026-10-24 00:13:07 end=2026-10-24 00:14:43 elapsed=97s bound=1200s status=OK rc=0` 645; netguard 22 from 21 both sides.
  - D base `[pyt] tag=s14g-base-D start=2026-10-23 23:34:02 end=2026-10-23 23:34:09 elapsed=7s bound=1200s status=OK rc=0` 176 / head `[pyt] tag=s14g-head-D start=2026-10-24 00:14:58 end=2026-10-24 00:15:04 elapsed=6s bound=1200s status=OK rc=0` 176.
  - C1 base `[pyt] tag=s14g-base-C1 start=2026-10-23 23:34:38 end=2026-10-23 23:35:05 elapsed=27s bound=1200s status=OK rc=0` 902 / head `[pyt] tag=s14g-head-C1 start=2026-10-24 00:15:18 end=2026-10-24 00:15:48 elapsed=30s bound=1200s status=OK rc=0` 902; netguard 12 from 4 both sides.
  - C2 base `[pyt] tag=s14g-base-C2 start=2026-10-23 23:35:18 end=2026-10-23 23:36:40 elapsed=82s bound=1200s status=FAIL rc=1` 344 failed (exactly the RED file's ids) / 286 passed; head `[pyt] tag=s14g-head-C2 start=2026-10-24 00:16:11 end=2026-10-24 00:19:15 elapsed=184s bound=1200s status=OK rc=0` 630 passed; netguard 28 from 10 both sides.
  - Base failures 344 (all in the new file), HEAD failures 0: `comm -13` (branch-only-new) EMPTY.
- CI-order set (18 files, alphabetical: the unit file, the 043 / 044 / 037 / immutability / w1_2b / w1_2c / sqlfluff / secret-scan / D03 / T7 / S81-05 scanners, spine, FY25, W4-13 ledger, and the two CLAUDE.md readers after the CLAUDE.md edit): `[pyt] tag=s14g-ci-order start=2026-10-24 00:23:02 end=2026-10-24 00:26:02 elapsed=180s bound=1200s status=OK rc=0` -- 1329 passed, 4 deselected; `[hermeticity] sentinel checked 1329 test(s)`; `[netguard] blocked 22 attempt(s) from 21 node(s)`.
- sqlfluff 4.3.0 with the new `.sqlfluff` on the four SQL files: rc 0, "All Finished!", stderr empty (no Skipping line); negative control (one lower-case `create index` in a copy outside the repo) rc 1 with CP01 at L281. The six APPLY files lint rc 0 too.
- ruff `--select E9,F63,F7,F82` clean on the leaf and the test file; full repo ruff config clean on the leaf; `py_compile` OK; the pre-commit hook passed on the commit.
- PostgreSQL (GC-8), throwaway local 18.1 cluster on 127.0.0.1:55443 (stopped afterwards): 012 / 033 / 034 applied, then 045 applied, re-applied (NOTICE skips only), its POSTCHECK grid as expected with part 1 passing (A/B/A: the latest offer and the card serve 30.000 after B 25.000, the prune deletes B only), rolled back, re-applied, POSTCHECK again green; 047 applied, POSTCHECK grid as expected, re-applied, rolled back (the eight policies and the anon privileges return), re-applied; anon / authenticated refused on kb_* and on the three 012 tables, service_role upsert + DELETE allowed; one leaf-built row per table (12 rows incl. a denied host stored blocked in kb_merchants) accepted as service_role; the POSTCHECK FAILS ("kb_offers_latest serves 25.000, expected 30") on a 045 whose view ranks captured_at first.

### Stated limits

1. Inert until the owner applies 045 / 047 AND a later flagged unit (S81-15 / S81-16 / S81-17 / S81-18) writes or reads.
2. The SQL deny CHECKs are belts derived from sorted(DENY_LABELS); their edge cases differ from `deny_hosts.kb_source_allowed` in both directions (`notfragrantica.example` is accepted); the builders' call is the rule.
3. The GTIN check is format plus check digit only.
4. Ids inherit the price path's per-call flag reads (production: ENABLE_EXACT_PRICE_GATE ON, ENABLE_NORMALIZE_WORDS_EMPTY_FIX OFF): seeding and serving must run under the same state; a flip re-mints ids.
5. One-letter / alias-only names mint no id (S81-16 curated aliases); Emporio / Giorgio Armani share one brand axis.
6. Fragrance-only ids; decimal ml (0.5 ml, 7.5 ml -> 5) and gift sets (100 ml + 10 ml -> 10) mis-size (pinned); kb_variant_key maps > 5000 ml to '-' and so diverges from spine_key for 5001..9999 ml on purpose (GC-1).
7. kb_offers grows until kb_prune_offers runs (S81-19 / D17 schedule it).
8. Ratings on a 0..5 scale; the builders mirror numeric rounding (half away from zero).
9. kb_feedback.device_key is pseudonymous device data outside the 043 fence; deletion = S81-22's hook + kb_prune_feedback(365); a pepper rotation or the S81-08 id change gives one device two keys.
10. PostgreSQL 15+ (refused loudly below).
11. 047's rollback re-opens the anon write path (emergency only, with the PRECHECK relacl in hand).
12. The APPLY files are not pinned by a committed test; gate 3 of the adversaries checks them.
13. The registry entry validator checks origin, an int order >= 0 and JSON-serialisability, not the presence of every `Source` field (the RED row `registry_entries` accepts a partial entry).
14. `p_lang text DEFAULT 'en'` is read as the type "'en'" by `tests/_retro_r_mig_sql.arg_types` (harmless: no census filters that signature, GC-5).
15. The leaf is not on `.github/black-clean-paths.txt`; black would reformat it (the hook's black step does not cover it).

### Owner steps (names only)

1. `APPLY_045_1_PRECHECK.sql`, send the grid. 2. `APPLY_045_2_ONE_PASTE.sql` (byte-identical to 045). 3. `APPLY_045_3_POSTCHECK.sql`, send the grid (part 1 = the A/B/A and behaviour checks inside BEGIN ... ROLLBACK). Apply 045 before any kb_* writer flag flips. 4. `APPLY_047_1_PRECHECK.sql` (live pg_policies), send it; the orchestrator confirms the eight names. 5. `APPLY_047_2_ONE_PASTE.sql`. 6. `APPLY_047_3_POSTCHECK.sql`, send the grid. A dated ledger line per step.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
