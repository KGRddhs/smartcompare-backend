# S81-16b KB-BRANDS adversarial spec review (lens 1 correctness + lens 2 schema-and-data)

- Spec: .qa-s80/S81-16b_UNIT_SPEC.md sha256 34706e223d1885d0e11bc5b83dd539b0473bbc30b52ada1a0b0ef7304d43cda2 (re-hashed first; matches).
- Base: 0b19de5bcc1416111d48bc725359b95151a658ca (git rev-parse HEAD in the worktree); worktree `git status --short` EMPTY before and after.
- Probes: a DETACHED scratch worktree under <scratchpad>/s16b_rev/wt (added at 0b19de5b, removed with `git worktree remove --force`; `git worktree list` no longer shows it); logs in <scratchpad>/s16b_rev/.
- Verdict: APPROVE_WITH_CHANGES (one BLOCKING renumbering ruling, two RED-design blockers, corrections below). The flag choice (Q1), the builder, the RLS / REVOKE form, the rollback order and the CC0 / no-personal-data reasoning hold.

## Runs ([pyt] lines)

1. Base, the frozen rows the spec touches: `tests/test_s81_s16_kb_seed.py tests/test_s81_kb_schema.py -k "r23 or r24 or r02 or r27 or p01 or p02 or p07"` -> 5 failed, 42 passed (the five G2 R27 CRLF nodes, environmental, as the spec says).
   `[pyt] tag=s16b-rev-base1 start=2026-11-04 19:33:56 end=2026-11-04 19:34:04 elapsed=8s bound=600s status=FAIL rc=1`; `[hermeticity] sentinel checked 47 test(s)`; `[netguard] blocked 0 attempt(s) from 0 node(s)`.
2. Scratch worktree + the spec's proto 051 + rollback copied in (proto sha 946965cf... / c9225ca8..., verified), the 16 migration scanners (test_account_deletion_u8b (+ _fix_pins), 037, 041, 042, 043, 044, index-predicate, retro_w1_2b / 2c / 2d, s79_b3b_apple_revoke, s81_kb_schema, s81_s03_llm_ledger_v2, security_regression, sqlfluff_config) -> 1 failed, 1184 passed: `tests/test_s81_kb_schema.py::test_s14_r01_files_exist_once` AssertionError "051 belongs to another unit (R-S14-12)".
   `[pyt] tag=s16b-rev-mig-draft start=2026-11-04 19:36:11 end=2026-11-04 19:36:52 elapsed=40s bound=1200s status=FAIL rc=1` (the netguard lines come from test_security_regression's usual sentinel blocks, not this unit).
3. Same scratch + the census edit (kb_brands appended to KB_TABLES and KB_COLUMNS only) over test_s81_kb_schema, s17_kb_ingest, g3_gate_rows, s15_registry_robots, s16_kb_seed, g2_gate_rows, d14_live_robots -> 16 failed, 1091 passed: R01 (the 051 file) + R27 x10 (E1, as the spec predicts) + the five G2 R27 CRLF nodes. No other census reader breaks (confirms the spec's E1 scope).
   `[pyt] tag=s16b-rev-census start=2026-11-04 19:37:36 end=2026-11-04 19:38:20 elapsed=44s bound=1200s status=FAIL rc=1`; `[hermeticity] sentinel checked 1107 test(s)`.
4. Same scratch with the draft RENAMED to 052_kb_brands.sql (+ rollback): R01, the S03 H1 "050 once" row and the 042 reserved-number row -> 3 passed; `python -m sqlfluff lint --config .sqlfluff` on both 052 files -> "All Finished!".
   `[pyt] tag=s16b-rev-r01-052 start=2026-11-04 19:38:33 end=2026-11-04 19:38:38 elapsed=5s bound=600s status=OK rc=0`.
5. Read-only venv probe at base: `t043.PERSONAL_RX` matches none of the seven kb_brands columns; `kb._sql_match('^Q[1-9][0-9]{0,11}$')` Q1 True / Q01 False; `kb._str_len(' ', 1, 128)` True (a whitespace-only label passes the builder shape).

## Refuted claims (measured truth, file:line at 0b19de5b)

- RC1 (spec 1.4, 2.6, Q4: "051 is the next free number"): FALSE. RULINGS_S81_14 R-S14-12 (specs/RULINGS_S81_14.md) assigns "051 kb_ingest_compare RPC (S81-17); ... 052+ are assigned by the orchestrator on request, never taken by a unit on its own", and RULINGS_S81_G3 :6 / R-G3-7 / :57 keep S81-17b = "the kb_ingest_compare RPC (migration 051, FOCUS)". The pin is `tests/test_s81_kb_schema.py:516-517` (`for n in ("046", "048", "049", "051"): assert not list(MIG.glob(n + "_*.sql"))`): measured RED with the draft present (run 2). The spec's 1.10 draft probe ran the 043 fence and the index detector only and missed this node.
- RC2 (spec 4.1 / 4.2: E1 is the only test_s81_kb_schema.py change, "529 nodes, all but R27 unedited"): FALSE while the file is numbered 051 (R01 goes red, run 2). TRUE once renumbered to 052 (run 4).
- RC3 (spec header line 7 + 2.8: "kb_ingest.py ... consumes KB_BUILDER_KEYS for its own five tables"): app/services/kb_ingest.py names no KB_BUILDER_KEYS / KB_TABLES / KB_COLUMNS (grep: only KB_*_TABLE constants, KB_OFFER_UPSERT_SET, KB_OFFER_OBSERVATION_KEY and kb_leaf :117-119). Harmless (the census tuples have no consumer outside the tests and KbWriter._built, scripts/kb_seed_common.py:369), but the sentence is wrong.
- RC4 (spec 5.4: "K03 alone 27"): the K03 list of 5.2 holds 29 ids (qid 8, label_en 5, label_ar 3, host 9, source 2, updated_at 2). The prototype's "254-char host" is 257 chars (`proto/proto_builder.out` "len254": 257), so the 253 / 254 boundary is not the one probed.
- Verified TRUE (re-measured): brand script :1-147 (FLAG :26, SPARQL :32-33, derive_hosts :53-88 reaching the leaf only via common.kb_leaf :59, _run :91-126, main :129-140); kb_seed_common run_mode :67-79, int_knob :110-117, kb_leaf :142-144, write_report :157-162, KbWriter :360-440 (the offers / gaps update models :402-437); kb_service KB_TABLES :55-58, KB_COLUMNS :60-97, KB_BUILDER_KEYS :106-112, KB_OFFER_UPSERT_SET :154, the deny regex :166-178, _sql_match / _belted_host :181-200, kb_source_allowed :215-220, _str_len .. _ts_iso :339-354, _pg_text_ok :383-398; 045 guard :62-68, kb_set_updated_at :90-100 (NEW.updated_at := now()), triggers :341-349, RLS / REVOKE / GRANT :484-528; rollback/045 :24 DROP FUNCTION without CASCADE (L5 holds: 2BP01); P01 / P02 allowlists :331-351 and KB_RELATION_NAMES :55-66 (kb_brands not in it); R02 :398-424, R23 :991-1013, R24 :1016-1028, R27 :1092-1112, R28 startCommand :1119; the CLAUDE.md :547-551 source strings of 8.1 edits 1-3 each found once, byte-for-byte.

## Blocking issues

- BL1 (migration number; schema lens): 051 is reserved for S81-17b (R-S14-12, R-G3-7) and pinned by test_s14_r01 :516-517. The orchestrator assigns the number (R-S14-12: "052+ ... by the orchestrator on request"). Recommended: 052 (measured clean, run 4; R01 needs no E-row). Rename everywhere: both files, B01 / B08 / B09 / B10 / B11 names and header phrases ("rollback/052_kb_brands.sql"), the DO-block message, APPLY_052_1 / 2 / 3, PIN and M-row text, 8.1-8.4, the DEFECT_LEDGER draft, the PR body; keep "after 045" and "before any rollback of 045". The alternative (take 051, move S81-17b to 052) needs an R01 E-row plus RULINGS_S81_14 and RULINGS_S81_G3 amendments: wider, rejected.
- BL2 (S04 is tautological: the "mutants no RED row can kill" class): S04 asserts each written row equals `kb.build_brand_row(**row-minus-updated_at, updated_at=NOW)`, i.e. the row equals itself through the builder; it never checks VALUES against the bindings. Surviving mutants (none of S03-S11 pins them): (a) official_host chosen only from derive_hosts' NEW list (a brand whose site is an existing kb_merchants host gets None); (b) label_ar read from a wrong key when the S04 fixture has no S11-style sentinel; (c) qid_of returning the full IRI makes every row bad_qid and S04's "every write is kb_brands" passes vacuously on an EMPTY write list. Fix at RED: S04 asserts the exact expected row list as a LITERAL from its fixture (qid, label_en, label_ar, official_host, source, updated_at) and the exact upsert count; add an S06 case "site equals an existing kb_merchants host -> official_host kept"; mutants M31 (merchant-host exclusion leaks into the brand host) and M32 (label_ar never set).
- BL3 (S10's "update raises" case is vacuous as written): the s16 FakeClient returns every upserted row by default (tests/test_s81_s16_kb_seed.py:144-146), so KbWriter.brands makes NO update and a `fail` keyed on kind == "update" never fires. S10's update case must set `returned=lambda q, rows: []` (or a subset) so the update path runs.

## Corrections (in the spec / RULINGS before RED)

- C1 (B12 census form): B12 = AST string constants EQUAL to "kb_brands" (the P02 form, tests/test_s81_kb_schema.py:401-405), never a substring scan: the brand script's own constants "seed_kb_brands_wikidata" (:24, :42) and the spec's 2.2 log formats ("%s kb_brands write failed (%s)", "(apply writes kb_brands; ...)") contain the substring, so a substring B12 can never go green.
- C2 (S02 kills): S02 calls `main` WITHOUT `client=` (so the client-factory recorder sees M16), with an argv argparse refuses (the R02 `--corpus` idiom: a parse-before-OFF mutant exits) plus `--report <tmp>` with `open` recorded on that path.
- C3 (counters, 2.5): name the counter a usable-looking en label the builder refuses (129 chars, NUL, lone surrogate) bumps (`no_label_en` or `not_built`; both readings fit today) and pin it in S06. `counts.update(writer.counts)` OVERWRITES a derive-side `not_built` (dict.update of a Counter): distinct names or add. Put `counts.update(writer.counts)` in a `finally` so a mid-run failure still reports the batches already sent (the spec says "earlier batches stand" but the report would show none). `brand_updates` counts update ATTEMPTS (an operator row matches zero rows): name or state it.
- C4 (S03 fixture): include a brand with two sites carrying the same en / ar labels, so `with_label_en` / `with_label_ar` are pinned as DISTINCT-qid counts (a per-binding mutant survives otherwise), and an item without an ar label.
- C5 (K03): the boundary host exactly 254 chars (refused) with a 253-char twin in K02 (accepted); correct the node count (29 K03 ids).
- C6 (label quality; schema lens): `build_brand_row` accepts a whitespace-only label_en (`_str_len(' ', 1, 128)` True, probe 5) and the CHECK bounds only the length. The script strips; an operator path would not. Either refuse blank / padded labels in the builder and add CHECK clauses (label_en and label_ar) with K03 rows, or state it as a limit.
- C7 (owner steps, billing-adjacent): a Railway variable change re-deploys the service, and the kbseed startCommand is `python -m scripts.seed_kb_batch` (R28 :1119). Step 3 ("On the kbseed service: ENABLE_KB_BRANDS=true") must first confirm ENABLE_KB_SEED is unset there, else the variable change re-runs the PAID batch seeder in its current mode (bounded by KB_SEED_MAX_USD and the breaker, still a spend). Prefer the brand script as a one-off with the flag in that command's environment only.
- C8 (L7 tightened): PostgreSQL `INSERT ... ON CONFLICT DO NOTHING RETURNING` returns inserted rows only, and PostgREST ignore-duplicates maps to it; add to G9 the same insert twice (`RETURNING qid`: the second returns 0 rows) so the SQL half of R-G2-12 is measured locally; the PostgREST half stays the canary.
- C9 (wording): the header phrase "MERGING THIS CHANGES NOTHING IN PRODUCTION" is true of the table, but the PR merge re-runs the three G2 jobs (L6); B10 keeps the phrase, the PR body carries L6 beside it.
- C10 (POSTCHECK): add anon / authenticated UPDATE and DELETE = false columns (only SELECT / INSERT are checked today).

## Questions for the orchestrator

1. Assign the migration number (BL1): 052 recommended (measured clean), or rule 051 with an R01 E-row and an S81-17b renumbering.
2. Labels and Wikidata `mul` (L2 may be a defect rather than a limit): since the `mul` default-label rollout, brand / company items may carry their name only as a `mul` label. Add `OPTIONAL { ?brand rdfs:label ?label_mul . FILTER(LANG(?label_mul) = "mul") }` as the label_en fallback (counted `label_en_from_mul`), or keep L2 and let the DRY `with_label_en` count decide before APPLY? Offline-unverifiable either way; the fallback costs one OPTIONAL.
3. Truncation order (L8): ORDER BY ?brand sorts IRIs as strings while the cap keeps the lowest NUMERIC qids; accept, or `ORDER BY xsd:integer(STRAFTER(STR(?brand), "Q")) ?site` so both orders agree?
4. 11.1: the tighter `^Q[1-9][0-9]{0,11}$` is right (one item, one key); confirm.
5. 11.2 (the human exclusion in the shared query, L3): accept (the DRY host list loses human items' sites; no write depends on it).
6. 11.3 (the OFF line naming both flags keeps R02 unedited): acceptable; R02's brand nodes then prove only "ENABLE_KB_BRANDS unset -> OFF" and S02 carries the real B1 matrix. Confirm no EK3.
7. 11.6 (G9 local PostgreSQL 18): keep as a GREEN gate (FOCUS = the migration); NOT MEASURED -> the POSTCHECK grid is the owner's proof. PG18 stores NOT NULL as contype 'n'; the POSTCHECK counts contype 'c' only, so 6 holds on 15 / 17 / 18.
8. 11.7 (labels in --report): fine (CC0 brand names, humans excluded); confirm.
9. C6: builder refusal of blank / padded labels plus CHECK clauses, or a stated limit?

## Contract risks

- None on the request path: no app/ request module, no response key, no envelope, no billing / quota / history path (R-A3 n/a), no camera path, no cache key, no error-handler code (the only app/ edit is the leaf, whose importers are the three function-local P01 entries).
- Data: kb_brands joins KB_TABLES LAST; the 045 ten keep their order (PIN-3); KbWriter._built derives keys from KB_BUILDER_KEYS (no other consumer).
- Operational: the merge re-runs the three G2 Railway jobs (kb_seed_common is in all three watchPatterns, L6); a variable change on kbseed re-runs the batch seeder (C7).
- Known rebase: G4 KB-SERVE may touch kb_service.py / test_s81_kb_schema.py P01 / P02 (whichever merges second unions); the G4 brief names no migration, so no number clash there.

## Pin collisions (not in spec 4.1)

- tests/test_s81_kb_schema.py::test_s14_r01_files_exist_once (:508-517): RED with a 051 file (run 2); resolved by BL1 (052), else an E-row.
- None found with T23 OpenAPI, the FY25 / W4-13 identity digests (P06 :463-480 untouched), the w4_11 prompt digests, the test_retro_w2_1 URL pins, the copy-policy fences or the fourteen client fences (no literal they read moves); the other 15 migration scanners stay green with the draft (run 2).

## Not done in this review

No RED / GREEN / mutation run; the comm-set base record (LC-6) and G9 NOT MEASURED; the Wikidata ids and row counts are not measurable offline; nothing written in the worktree except this file.
