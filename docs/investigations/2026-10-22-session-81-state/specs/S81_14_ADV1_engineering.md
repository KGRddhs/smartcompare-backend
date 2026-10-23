# S81-14 KB-SCHEMA -- engineering adversary report (Opus 5.5, 2026-10-24 01:37 -> 02:45 AST)

Unit: S81-14 KB-SCHEMA (045 + 047 + rollbacks, app/services/kb_service.py, .sqlfluff, CLAUDE.md). Lens: engineering.
Verdict: NOT_READY (1 MAJOR, 0 blocking; the rest minors / rulings).

## Identity checks
- Assigned worktree sc-s81-s14: HEAD 0910e7d0eedac31711f4adbf77cb49c40e0c2179 on feature/s81-s14-kb-schema (verified at start), `git status --short` empty. Never edited.
- RED file tests/test_s81_kb_schema.py sha256 7b1db7e3fedfeaea83a7f73f0b2b8fa27c06a8f3a6718f44ca748bfd1228367b at start and at end (assigned worktree, LF bytes = the blob).
- Scratch worktree <scratchpad>/S81-14_adv_engineering, `git worktree add --detach ... 0910e7d0`; removed at the end with `git worktree remove --force` (see End state).
- Blob sha256 (= GREEN report): kb_service a9fbef3c..., 045 987ba019..., 047 abb6597e..., rollback/045 4a7fcbab..., rollback/047 0631c304..., .sqlfluff blob e39a5299... (working copy CRLF c5e1b712...), CLAUDE.md working copy 2f788686....
- The scratch checkout is CRLF for the new files (core.autocrlf=true): 045 = 23,631 B there (23,141 B as committed). The GREEN worktree keeps them LF on disk (git status clean). Measured on the CRLF checkout too (below).

## Runs (every [pyt] line; all in <scratchpad>/S81-14_adv/)
- Unit file on the CRLF checkout: `[pyt] tag=s14e-unit-crlf start=2026-10-24 01:39:45 end=2026-10-24 01:39:53 elapsed=8s bound=600s status=OK rc=0` 402 passed; `[hermeticity] sentinel checked 402 test(s)`; `[netguard] blocked 0 attempt(s) from 0 node(s)`.
- CI-order set (GREEN's 18 files): `[pyt] tag=s14e-ci-order start=2026-10-24 01:54:44 end=2026-10-24 01:57:01 elapsed=137s bound=1200s status=OK rc=0` 1329 passed, 4 deselected; hermeticity 1329; netguard 22 from 21 (= GREEN).
- Comm chunk A (25 migration readers): `[pyt] tag=s14e-head-A start=2026-10-24 01:57:25 end=2026-10-24 01:58:29 elapsed=64s bound=1200s status=OK rc=0` 627 passed, 10 deselected; hermeticity 627; netguard 12 from 6 (= GREEN head).
- Comm chunks B1+B2 (16 source-scanning pins / walkers: test_model_config*, test_prompt_fence, U3c store pin, start_command, key-log hygiene, sentry channels, auth log hygiene, domain, legal x3, w0_4 x2, D03 R1i, shopify pdp, U3b): `[pyt] tag=s14e-head-B12 start=2026-10-24 01:58:50 end=2026-10-24 02:00:24 elapsed=94s bound=1200s status=OK rc=0` 1113 passed (= 377 + 736); netguard 0.
- Comm chunks B3+C1 (incl. both CLAUDE.md readers, hermeticity pins, spine, S81-03, identity importers): `[pyt] tag=s14e-head-B3C1 start=2026-10-24 02:00:51 end=2026-10-24 02:02:49 elapsed=118s bound=1200s status=OK rc=0` 1547 passed (= 645 + 902); netguard 34 from 25.
- Comm chunks C2+D (unit file, FY25, W4-13 ledger, w1_2c, secret-scan static, S81-05): `[pyt] tag=s14e-head-C2D start=2026-10-24 02:03:13 end=2026-10-24 02:04:16 elapsed=63s bound=1200s status=OK rc=0` 806 passed (= 630 + 176); netguard 28 from 10.
- So all 67 comm files at HEAD: 0 failed. GREEN's base record (98d85433) has 344 failures, all the new file's RED ids; branch-only-new EMPTY (no base re-run needed: HEAD fails nothing).
- Hook test files (lens duty; outside the comm rule): `[pyt] tag=s14e-hook-collect ... status=OK rc=0` 327 nodes collected; `[pyt] tag=s14e-hook-r1 start=2026-10-24 02:15:32 end=2026-10-24 02:35:39 elapsed=1207s bound=1200s status=TIMEOUT rc=124` (tests/test_precommit_hook.py + _round2.py, 92 nodes; 27 executed at about 45 s per node, 2 `F` whose tracebacks the kill cut off). NOT MEASURED: not re-run, because at the measured rate the 92-node pair needs about 70 min, over the 1800 s ceiling, so a re-run times out by construction. No hook test references sqlfluff, .sqlfluff, migrations/ or a .sql file (grep: 0 hits in all four files) and .githooks is untouched, so none can observe this unit.
- Probe (temporary test file copied into the scratch, run, removed; status clean after): `[pyt] tag=s14e-probe start=2026-10-24 02:38:45 end=2026-10-24 02:38:49 elapsed=4s bound=600s status=OK rc=0` (see MAJ-E1).
- Mutants: 17 lines in <scratchpad>/S81-14_adv/emut_results.jsonl (table below), each `[pyt] tag=s14e-e<n>`.

## Comm-set re-derivation (union rule, independent)
Scanner <scratchpad>/S81-14_adv/derive_comm.py over every tests/**/*.py at HEAD (309 files with any hit), then classified by hand:
- References to kb_service / kb_* names / 045 / 047: only the new file (the 045/047 numeric hits in test_scoring_value_math_v11 are price literals; test_s80_url_mode_v2 and test_s81_s03 are in the set).
- Migration-dir readers (glob over migrations/, rollback/, the _retro_r_mig_sql helper): all 25 of chunk A + test_s81_s03, test_s79_b3b, w1_2b/2c/2d, test_ci_gates, test_secret_scan_static, test_security_regression, test_legal_docs_u8, test_sqlfluff_config: all in GREEN's 67. The helper's other importers (test_account_deletion_u8b*.py) import only install_network_guard: not readers.
- .sqlfluff readers (5): test_ci_gates, test_retro_w1_2c, test_secret_scan_static, test_sqlfluff_config, the new file: all in.
- CLAUDE.md: 34 files mention it; only test_ci_gates, test_behavior_dimension_translation (and test_retro_w1_2d) read it; the rest are docstrings (checked line by line).
- app/ walkers (glob / rglob / os.walk / listdir / scandir / iterdir / pkgutil / ls-files): every walker over app/ or scripts/ is in the set; the other walkers enumerate fixtures, SmartCompareApp/src, _proof/, .claude skills or tmp dirs (test_events_allowlist_superset, test_jsonld_shape_ladder, test_multiplicity_discriminator_policy, test_not_a_pdp_filter, test_platform_router, test_skill_frontmatter, test_be_harness, test_variant_descriptor_golden, test_regression_gate_diff, test_conftest_env_safety): none sees the new leaf or migrations. Fixed-file AST readers (e.g. test_s81_st1_usage_path_offloop, test_s70_exc_summary_logs) read named unchanged modules.
- tests/ walkers that would see the new test file: test_hermeticity_pins, test_ci_gates (in set).
- No edited test-support helper; no client file; no .github / processors.json / legal change.
- Result: my derivation = GREEN's 67 files exactly (the RED's 66 + test_s81_s05_request_context.py); no missing file.

## Other gates
- gitleaks 8.30.1 (`gitleaks git --log-opts=98d85433..0910e7d0 --config <HEAD .gitleaks.toml> --redact --no-color --ignore-gitleaks-allow`): rc 0, "1 commits scanned", "no leaks found" (the CI secret-scan equivalent).
- Added-line sweep over the whole commit diff: 0 hits for @gmail, +973, 8+-digit runs, sk-, eyJ, PEM, credentialed URL, AKIA, xox. CLAUDE.md: the edited line 92 keeps its 30 pre-existing non-ASCII bytes (30 before, 30 after), the 9 added row lines 0; .sqlfluff +5 lines ASCII; no CR in any diff line; no whole-file diff (stat: .sqlfluff +5, CLAUDE.md +11 / -1, new files only otherwise); the one deleted line is the apply-record line it replaces.
- sqlfluff 4.3.0 (venv) with the HEAD .sqlfluff on the four SQL files (CRLF checkout): rc 0, "All Finished!", stderr 0 bytes. Negative control (045 copy with one `create index`): HEAD config rc 1, CP01 at L281 P1/P8; BASE (98d85433) config: rc 0 with "WARNING Length of file ... is 23631 bytes which is over the limit of 20000 bytes. Skipping" -> the .sqlfluff change is load-bearing. Only 037 (19,557 B) and 045 exceed 15 KB among migrations.
- ruff 0.16.5 `--select E9,F63,F7,F82 --no-cache` leaf + test file: All checks passed; full config on the leaf: All checks passed (the frozen test file has 180 report-tier findings: C408 x179, B007 x1); py_compile OK; black 26.5.1 --check: both files would be reformatted (neither is on .github/black-clean-paths.txt; CI's whole-repo black step is report-only).
- Imports of the leaf: stdlib (ipaddress, json, math, re, uuid, datetime, decimal, typing, urllib.parse) + by module attribute deny_hosts, price_service, result_gate, spec_spine_service, text_sanitize. Spec 2.4 listed three app modules; result_gate + text_sanitize are required by R-S14-9 and json / math / decimal by the GC-9 JSON / decimal-string builders; the frozen R21 allowlist accepts them. No import outside the rulings.
- APPLY files (GC-7, by hand): ONE_PASTE files byte-identical to 045 / 047 (cmp); 045 POSTCHECK has part 1 inside BEGIN ... ROLLBACK (the A/B/A offer check + behaviour checks, RAISE 'APPLY_045 POSTCHECK FAILED: ...') and the has_table_privilege grid; 047 POSTCHECK reads pg_policies + has_table_privilege for anon / authenticated / PUBLIC / service_role; rollback/047's eight CREATE POLICY lines equal migrations/012 lines 19-21, 41-42, 58-60 (schema-qualified).
- Single-query replay (NEW, closes part of GREEN's "Supabase editor" NOT MEASURED): throwaway cluster (PostgreSQL 18.1 binaries, initdb into <scratchpad>/S81-14_adv/pg/data, 127.0.0.1:55471 only: "listening on IPv4 address 127.0.0.1, port 55471"), GREEN's Supabase-like roles, 012 / 033 / 034 applied; then EACH APPLY file sent as ONE simple-query string (`psql -c "$(cat file)"`, the way the SQL editor sends a paste): 045_1 rc 0 grid t,0,0,t,t,t,t; 045_2 rc 0 (BEGIN ... 77 tags ... COMMIT); 045_3 rc 0, NOTICE "part 1: every behaviour check passed", BEGIN / DO / ROLLBACK, grid t,t,f,t,t,f,10,t,0,t,f,f,f,5,f,t,f,3,0 (= the expected grid); 045_2 again rc 0 (skip NOTICEs); 047_1 rc 0 (8 policies, stock relacl); 047_2 rc 0; 047_3 rc 0 grid: 3 rows, rls t, 0 policies, every anon / authenticated read f, public_any f, sr S/I/U/D t; 047_2 again rc 0; 11 kb_* relations. Stopped: "server stopped", status "no server running". The data dir is stopped, NOT deleted (the common brief forbids recursive deletes): the orchestrator removes <scratchpad>/S81-14_adv/pg/data (and GREEN's <scratchpad>/S81-14_green/pg/data, its deviation 4). The installed postgresql-x64-18 service was running throughout and was not touched.
- PLAN section 0 freeze: no client-visible change, no flag, no app/ or scripts/ importer (P1/P2 killed E9/E10 below): the build-3 contract is untouched.

## Mutants (engineering: the pins' strength; byte copy, exact single-line edit matching once, unit file via pyt bound 600, restore, sha256; lock <scratch>/.qa-mutation.lock held and removed; all 3,427 tracked files sha-identical before / after; git status clean)
| id | mutant | result | killing rows |
|---|---|---|---|
| E1 | .sqlfluff limit 0 -> 30000 (045 still linted) | KILLED | r20_sqlfluff_lints_every_file |
| E2 | KB_OFFER_UPSERT_SET gains amount (S81-17 contract) | KILLED | r28d |
| E3 | KB_OFFER_OBSERVATION_KEY order swapped | KILLED | r28d |
| E4 | 045 observation UNIQUE gains canonical_url | KILLED | r04b[kb_offers], r28d |
| E5 | view SELECT granted to anon | KILLED | r05[kb_offers_latest], r06 x5 |
| E6 | view REVOKE without anon | KILLED | r05[kb_offers_latest] |
| E7 | card EXECUTE granted to anon | KILLED | r06 x5 |
| E8 | registry origin check dropped | KILLED | r28[registry_bad_origin] |
| E9 | an app module carries the literal "kb_offers" | KILLED | p02 |
| E10 | a scripts/ module imports kb_service | KILLED | p01 |
| E11 | rollback/045 keeps kb_prune_feedback | KILLED | r16 |
| E12 | rollback/047 forgets reviews_update | KILLED | r16 |
| E13 | 045 header loses the GC-2 observation-upsert sentence | SURVIVED | none (header sentence unpinned) |
| E14 | 047 product_prices REVOKE keeps SELECT for anon | KILLED | r17 |
| E15 | CLAUDE.md apply record: 045/047 "APPLIED" (unit + both CLAUDE.md readers) | SURVIVED | none (docs unpinned) |
| E16 | device key regex accepts upper case | KILLED | r25c, r28[device_upper] |
| E17 | one-vote index drops product_id | KILLED | r12 |
All kills are AssertionError only, 0 ERROR nodes, 8-19 s each. 15 / 17 killed; the two survivors are documentation text (minors m1, m2).

## MAJOR
- MAJ-E1 (GC-4 cross-unit contract + CLAUDE.md row truth). GC-4 makes "the registry entry validator (origin in {literal, catalog, operator, discovery}, int order >= 0, every Source field)" THE contract S81-15's seed calls and its RED pins against. kb_service._registry_ok checks only list / dict shape, origin, an int order >= 0 and json.dumps(allow_nan=False); it validates no Source field. Measured (probe): build_merchant_row(host="shop.example", registry=...) returns a row for [{"origin": "literal", "order": 0}] (no Source field), for [{"origin": "literal", "order": 0, "tier": 5, "bogus": "x", "weight": "heavy"}] (wrong types, unknown key), for two entries with the same order 0, and for an entry whose domain is another host. Yet the CLAUDE.md S81-14 row (Merchants bullet) says the entries carry "the `Source` fields; `kb_service.build_merchant_row` validates them and S81-15's seed calls it, never a copy", which contradicts PR_BODY stated limit 13 and GREEN's own Q1. A check of PRESENT fields (keys within {origin, order} + dataclasses.fields(source_router.Source), each present value of its declared type) fits the frozen RED (its registry_entries accept row carries origin / order / domain only; every refuse row stays refused) but needs a sixth module import (source_router) and a ruling; requiring PRESENCE of the four required Source fields (domain, tier, categories, weight) contradicts the frozen accept row. Fix (orchestrator's choice): (a) rule GREEN's Q1 that Source-field presence / types are S81-15's contract, and rewrite the row sentence to "build_merchant_row validates origin, an int order >= 0 and JSON-serialisability only; the Source-field check is S81-15's" (and record it against GC-4 for the S81-15 RED); or (b) implement the present-field key / type check with a ruling for the import and a new pin (no RED row would kill its removal).

## Minors (rulings / documentation)
- m1 (E13): the GC-2 "045 header sentence" is not pinned; a header edit survives the whole file. Accept (comment-only) or pin it in a later RED.
- m2 (E15): the CLAUDE.md apply-record "WRITTEN, NOT APPLIED" text is unpinned (normal for docs rows; equivalent).
- m3 (GREEN Q3, agree): M65 (ROUND_HALF_EVEN) survives; no row sits on a half tie. A RED amendment (amount 0.0005 -> "0.001"; rating 5.005 refused) would pin it; or accept.
- m4: CLAUDE.md row "REVOKE ALL from PUBLIC, anon, authenticated AND service_role, then one GRANT ... the functions EXECUTE: the 050 form": the function REVOKEs omit service_role (045:479-483) and 050 has no function; wording only.
- m5: "a pure leaf (no I/O ...)" is true of its own code, but importing it imports price_service -> extraction_service (load_dotenv(override=True) at import) and the module-level clients; S81-15..S81-22 scripts that import the leaf inherit the dotenv-override hazard P8 pins. The row should name it.
- m6: the apply-record line says the APPLY files are "in the session-81 state folder"; they are in sc-s81-s14/.qa-s80/ until the orchestrator copies them (GC-7).
- m7 (GREEN Q2): keep the leaf off .github/black-clean-paths.txt (CI's repo-wide black is report-only; reformatting would invalidate the mutant edit texts). The frozen test file's 180 full-config ruff findings are report tier.
- m8: APPLY_047_3_POSTCHECK reads anon / authenticated SELECT / INSERT / UPDATE / DELETE but not TRUNCATE / REFERENCES / TRIGGER (only public_any covers TRUNCATE, for PUBLIC); 045's grid covers "any privilege". Harmless after REVOKE ALL; an extra column would make the grid complete.
- m9: GC-8 "deleted afterwards" conflicts with the no-recursive-delete rule: GREEN's and my scratch data dirs are stopped and left for the orchestrator.
- m10 (GREEN Q4): the POSTCHECK writes synthetic rows only inside BEGIN ... ROLLBACK; measured in single-query mode, kb_row_count 0 afterwards. Acceptable.

## Prove-nothing rows
- None identified within this lens (17 targeted mutants; 15 killed by named rows). Not audited: the strength of every one of the 402 rows.

## NOT MEASURED
- The four test_precommit_hook*.py files (TIMEOUT above; outside the comm rule; no sqlfluff / SQL reference).
- The Supabase SQL editor itself (emulated by single-query psql -c; its connection pooling / result display not measured).
- PostgreSQL 15 / 16 / 17 (only 18.1 binaries on the box).
- Base re-runs of my own: not needed (HEAD fails nothing in the 67-file set; GREEN's base record used).

## End state
- Scratch worktree removed (git worktree remove --force; git worktree list checked); assigned worktree untouched: HEAD 0910e7d0, status empty, RED sha 7b1db7e3... at the end.
- No .qa-mutation.lock; no pytest process with tag s14e / my scratch cwd left; my PostgreSQL cluster stopped ("no server running").
- Notes folder: <scratchpad>/S81-14_adv/ (notes.md, logs, emut.py, emut_results.jsonl, derive_comm.py, derive_hits.tsv, pg_single_query.sh, pg/ outputs, negctl/, gitleaks.out, this report).
