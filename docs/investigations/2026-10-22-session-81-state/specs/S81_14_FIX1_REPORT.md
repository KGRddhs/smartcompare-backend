# S81-14 KB-SCHEMA -- fix round 1 report (Opus 5.5 fix agent, 2026-10-24 05:25 -> 07:45 AST)

- Unit S81-14 KB-SCHEMA (045 + 047 + the leaf kb_service + .sqlfluff; no flag). Worktree C:/Users/SynAckITPC/Documents/AI/sc-s81-s14, branch feature/s81-s14-kb-schema. Start: HEAD 0910e7d0eedac31711f4adbf77cb49c40e0c2179, `git status --short` empty, no lock. End: ONE commit **ee09729da43cb4a0769736c2ab04951a5fad51fd** (through the hook; not pushed, no rebase, no stash), `git status --short` empty, no lock, no pytest left, the PostgreSQL cluster stopped.
- Rulings applied: RULINGS_FIX1_S81_14 F1-1..F1-12 (all), over RULINGS_S81_14 / GATE_S81_14. Measurement base 98d85433 (GREEN's base comm record reused).
- An earlier fix agent of this round was interrupted; its drafts (S81-14_fix1/draft/, S81-14_fix1_interrupt/) never reached the worktree. They were read as reference only; every edit here was re-derived.
- Notes, byte copies, drafts, logs: <scratchpad>/S81-14_fix1/ (notes.md, before/ + before_SHA256SUMS.txt, new/, red_head.log, unit1.log, fix_mutants.py, fix_mutate.py, clauses.py, dryrun.py + dryrun_out.json, fix_mutation_results.jsonl, mut_table_fix1.md, mutlogs/, comm/, ci_order.log, lint/, pg/, commit_msg.txt, commit.out, PR_BODY.md).

## Files (sha256 of the bytes on disk at the end; LF unless noted)

| file | before | after | +/- (vs 0910e7d0) |
|---|---|---|---|
| app/services/kb_service.py | a9fbef3c... | f8a3197479f553a13a00de3bffe0abb47c43e5ce763d44e08fcef131ea9cdc02 | +136 / -19 |
| migrations/045_kb_core.sql | 987ba019... | 653b7b1fcd4b01107cc4b79af26e83d53f7514327a87a8ad59cb1fd15c8f3420 (24,030 B) | +25 / -15 |
| tests/test_s81_kb_schema.py (RED file) | 7b1db7e3... | ba8ef857f8e982c3367f728d7b6bbe42b7acd63c665ebdae83697ba098a2b4f1 (109,015 B) | +451 / -19 |
| CLAUDE.md (CRLF kept) | 2f788686... | 288745ecc9fbdd9857848743411741e967a0f27267963906f4da7d91cee9a08a | +9 / -9 (line 92 + the S81-14 row lines 494-502; 3,937 non-ASCII bytes before and after) |
| .qa-s80/APPLY_045_2_ONE_PASTE.sql | 987ba019... | 653b7b1f... (= 045, cmp) | deliverable |
| .qa-s80/APPLY_045_3_POSTCHECK.sql | 5bfe06ab... | b4631fdbad7ee4a8bcfe65303529061ad55e2fc1b988d967d154362a259674f2 | tie-break + all-digit checks, first-apply note |
| .qa-s80/APPLY_047_3_POSTCHECK.sql | 640458ad... | 238cb79d00e9adc14c27b5d738be92e7335e3474cff1f012229baf784d5e90b0 | TRUNCATE / REFERENCES / TRIGGER columns (F1-10) |
| .qa-s80/APPLY_045_1_PRECHECK, APPLY_047_1_PRECHECK, APPLY_047_2_ONE_PASTE | unchanged | aacb0a92..., 00cc7b8d..., abb6597e... | - |
| 047, both rollbacks, .sqlfluff | unchanged | abb6597e..., 4a7fcbab..., 0631c304..., c5e1b712... | - |

Every written file: 0 bytes > 127 (CLAUDE.md keeps its pre-existing ones; the PR body carries the attribution emoji only), no 8-digit run, the added-line sweep (@gmail, +973, 8-digit runs, sk-, eyJ, PEM, credentialed URL, AKIA, xox) empty. The six APPLY files are in .qa-s80/ for the orchestrator to copy.

## What changed (per ruling)

- F1-1: `kb_product_id` returns None when `_rg.product_is_placeholder({"brand", "name"})` (read at call time) is True: the identity OR the name alone. ('Dior','Unknown'), ('Dior','Unknown Product'), ('Dior','This Product'), ('Dior','Product'), ('Lattafa','Unknown') mint no id and never reach spine_key. The unused text_sanitize import is gone.
- F1-2: rows r13b (the whole view as compact text, no WHERE) and r14b (the whole card body as compact text, every correlation predicate, no in_stock / now() / interval / freshness filter).
- F1-3: `_registry_ok(value, host)`: keys within origin / order + the `source_router.Source` fields (`get_type_hints(_sr.Source)`, `from app.services import source_router as _sr` INSIDE the function), each present value typed (str, bool, int, float (int or finite float), Tuple[str, ...] (list / tuple of str), Optional[SearchDescriptor] (None or dict)), origin one of four, order an int >= 0 and unique, domain == host when present. An entry with no Source field is ACCEPTED (presence = S81-15's seed contract).
- F1-4: `(o.list_vs_sale = 'sale') DESC` before `o.id DESC` in the view, the card and the prune; the index is unchanged.
- F1-5: wording (strict subset) in the 045 header, the leaf docstring, the CLAUDE.md row and the PR body; the eleven belt-only refusal rows re-pointed to rule-only inputs (path tokens, hyphenated labels, a top-level label).
- F1-6: the half-tie / bounds rows (r30 and the accept / refuse rows); the RAW rating is bounded (`0 <= Decimal(str(raw)) <= 5`, so -0.001, 5.001, 5.005 are refused; 0, 5, 4.995 accepted and stored 0.00 / 5.00 / 5.00); all-digit hosts: `KB_HOST_TOP_LABEL_REGEX = "[a-z][a-z0-9-]*$"` in `_belted_host`, `_belted_url` (so canonical_offer_url too) and the merchant builder, and the 045 constraint `kb_merchants_host_top_label_letter CHECK (host ~ '[a-z][a-z0-9-]*$')`.
- F1-7: `REFUSAL_CLAUSES` names one clause per refusal row (191 rows, 115 clauses; r28e pins completeness); prove-nothing rows re-pointed (see deviations); the redundant `_belted_url(KB_OFFER_URL_REGEX, canonical_url, limit=None)` line of the offer builder dropped (canonical equality implies it) and the coverage day emitted as `str(day)` so each row has ONE refusing clause.
- F1-8: `_pg_text_ok` (NUL or an unencodable lone surrogate in any str, dict key or value, list member) as one guard line before each builder's checks (all builders except coverage, whose only text is the regex-bounded metric).
- F1-9: the five function REVOKEs `FROM PUBLIC, anon, authenticated, service_role`.
- F1-10: APPLY_047_3_POSTCHECK gains anon / authenticated TRUNCATE / REFERENCES / TRIGGER columns and public_any covers them too.
- F1-11 / F1-12: the CLAUDE.md row (may re-mint, the sample / plus / tester / vial / gift-set outcomes, rating-only sources, count-only rows, S81-18 freshness, market vocabulary, the import hazard, APPLY files copied at merge, the validator sentence, the black allowlist), the 045 header observation paragraph (pinned by r19b), the leaf docstring; the leaf stays off black-clean-paths.

## RED step (pre-fix bytes = the 0910e7d0 leaf and 045 with the new test file)

`[pyt] tag=s14f1-red-head start=2026-10-24 06:14:10 end=2026-10-24 06:14:30 elapsed=21s bound=600s status=FAIL rc=1` -- 62 failed / 403 passed of 465 nodes; `[hermeticity] sentinel checked 465 test(s)`; `[netguard] blocked 0 attempt(s) from 0 node(s)`. Every failure is an assertion (no `E   <Other>Error` line, no ERROR node). Breakdown:
- 63 new nodes: 53 RED (the F1-1 name arm x10, r13b, r14b, r19b, r21b, r25d, r28f, r28g, r30, and 36 new refusal rows minus rating_half_over), 10 PIN (green there; each kills a named mutant): r28e, 8 accept rows (registry_no_source_field, registry_typed_entries, host_digit_registrable_label, url_digit_registrable_label, rating_zero, rating_five, rating_rounds_to_five, amount_half_tie) and the refusal row rating_half_over (the pre-fix bytes already rounded 5.005 to 5.01).
- 9 existing nodes whose expectation the rulings change, red there: r04b[kb_merchants] (F1-6), r06[x5] (F1-9), r13, r14, r15 (F1-4 via OFFER_ORDER).
- 393 existing nodes green (incl. the 15 re-pointed rows and the renamed merchant_single_label).
- Note: the ruling's parenthesis expected the half-tie row red on the pre-fix bytes; it is green there (GREEN already rounds half up), so the half tie is a PIN that kills M65 (measured); the rating-bound part of r30 is the red part.

## GREEN step

`[pyt] tag=s14f1-unit start=2026-10-24 06:17:00 end=2026-10-24 06:17:12 elapsed=13s bound=600s status=OK rc=0` -- 465 passed; hermeticity 465; netguard 0. Adjacent flags exported for that call only (ENABLE_DATA_GUARDS_V2=true, ENABLE_EXACT_PRICE_GATE=false, ENABLE_NORMALIZE_WORDS_EMPTY_FIX=true): `[pyt] tag=s14f1-unit-envx start=2026-10-24 07:40:24 end=2026-10-24 07:40:36 elapsed=11s bound=600s status=OK rc=0` -- 465 passed.

## Mutation table (fix bytes; driver fix_mutate.py, own lock, every restore sha-verified)

- 92 / 92 KILLED, assertion failures only, 0 ERROR nodes, 9-179 s each (the box was loaded): the GREEN table (65: M1-M64, M37a/b; M38 and M40 re-derived on the new texts), M65, A1-A3, A5-A13, F11 (name arm), F13a (source_router at import), F13b (domain check), F14a-d (tie-break: view / card / prune / inverted), F16a-b (top-label constraint / constant), F18a-c (NUL / surrogate / jsonb keys), F19 (pre-050 REVOKE), F111 (header sentence). Killing rows per mutant: mut_table_fix1.md. Examples: `[pyt] tag=s14f1-m1 start=2026-10-24 06:21:11 end=2026-10-24 06:21:22 elapsed=10s bound=600s status=FAIL rc=1`; `[pyt] tag=s14f1-a13 ...status=FAIL rc=1` (r13b); `[pyt] tag=s14f1-f111 start=2026-10-24 07:19:38 end=2026-10-24 07:20:02 elapsed=24s bound=600s status=FAIL rc=1`. Every [pyt] line is in fix_mutation_results.jsonl.
- Worktree sha snapshot before / after the mutation runs (3,427 files): identical except CLAUDE.md, which I edited between the batches (no mutant touches it).
- F1-7 clause table (115 clause-only mutants, clauses.py): proved by the in-memory dry run (dryrun.py, dryrun_out.json): base bytes refuse all 191 refusal rows and accept all 22 accept rows; under each clause-only mutant every row naming that clause is ACCEPTED (0 survivors); collateral as expected for the shared helpers (url.top_label also frees url_digit_top_label; gaps.hint_shape also frees the two all-digit hint rows). The bounded-runner pass over the 115 clause mutants is NOT MEASURED (budget); the clause mutants that coincide with A1, A5, A6, A7, A8, A9 and F13b ran through pyt above and were KILLED.

## Comm set and CI-order (HEAD = ee09729d; base record = GREEN's 98d85433 run, 344 failures all in the new file)

- 67 files = GREEN's set (the fix references no new module from a test; CLAUDE.md readers and migration readers already in it), 4 chunks:
  - A `[pyt] tag=s14f1-head-A start=2026-10-24 07:22:07 end=2026-10-24 07:23:06 elapsed=59s bound=1200s status=OK rc=0` 627 passed, 10 deselected; netguard 12 from 6.
  - B1+B2 `[pyt] tag=s14f1-head-B12 start=2026-10-24 07:30:21 end=2026-10-24 07:32:15 elapsed=115s bound=1200s status=OK rc=0` 1113 passed; netguard 0.
  - B3+C1 `[pyt] tag=s14f1-head-B3C1 start=2026-10-24 07:23:20 end=2026-10-24 07:26:30 elapsed=191s bound=1200s status=OK rc=0` 1547 passed (both CLAUDE.md readers ran after the CLAUDE.md edit); netguard 34 from 25.
  - C2+D `[pyt] tag=s14f1-head-C2D start=2026-10-24 07:33:13 end=2026-10-24 07:34:22 elapsed=69s bound=1200s status=OK rc=0` 869 passed (806 + 63 new unit rows); netguard 28 from 10.
  - HEAD failures 0, so branch-only-new (`comm -13`) is EMPTY. Chunks A and B3+C1 ran before the commit, B1+B2 and C2+D after it (same bytes: the commit changed no file in the worktree).
- CI-order set (18 files): `[pyt] tag=s14f1-ci-order start=2026-10-24 07:35:12 end=2026-10-24 07:39:18 elapsed=246s bound=1200s status=OK rc=0` -- 1392 passed, 4 deselected; `[hermeticity] sentinel checked 1392 test(s)`; `[netguard] blocked 22 attempt(s) from 21 node(s)` (= GREEN).
- Scanners (all in the comm / CI-order sets, green): the 043 fence, the 037 SECURITY DEFINER census, the index-predicate immutability detector, w1_2b, w1_2c, sqlfluff config, secret-scan statics, T7, D03 R1i, the app/ and tests/ walkers.

## Other gates

- sqlfluff 4.3.0, repo .sqlfluff (limit 0), on the four SQL files: rc 0, "All Finished!", 0 bytes stderr; negative control (one lower-case `create index` in a copy) rc 1, CP01 at L291 P1/P8; the two edited APPLY files rc 0.
- ruff 0.16.5 `--select E9,F63,F7,F82 --no-cache` on the leaf and the test file: clean; full repo config on the leaf: clean; py_compile OK. The pre-commit hook on the commit: passed ("All checks passed!", "All Finished!").
- PostgreSQL 18.1 throwaway cluster (initdb builtin C.UTF-8 into <scratchpad>/S81-14_fix1/pg/data, 127.0.0.1:55491, one "listening on IPv4 address 127.0.0.1" line; stopped `pg_ctl -m fast stop`: "server stopped", status "no server running"; data dir LEFT for the orchestrator, no recursive delete): roles + 012 / 033 / 034; APPLY_047_1 and APPLY_045_1 PRECHECKs as expected; 045 rc 0 (77 tags), re-applied rc 0 (23 skip NOTICEs); APPLY_045_3_POSTCHECK part 1 NOTICE "every behaviour check passed" (incl. the tie-break and the all-digit refusal), grid `t t f t t f 10 t 0 t f f f 5 f t f 3 0`; probe (rolled back): 40 variants with list 50 + sale 30 at one instant -> view 40 sale / 0 list, card 40 / 0, kb_prune_offers(30, 1) = 40 and the 40 sales survive; 10.0.0.1 / shop.123 / 1.2.3.4 refused (check_violation), 4711.com accepted; the five kb function proacl `{postgres=X/postgres,service_role=X/postgres}`, client EXECUTE f, service_role t; 047 rc 0, APPLY_047_3_POSTCHECK 3 rows rls t, 0 policies, every anon / authenticated privilege incl. TRUNCATE / REFERENCES / TRIGGER f, public_any f, service_role S/I/U/D t; re-applied the same; rollback/047 rc 0 (the 8 policies back), 047 re-applied; rows inserted, rollback/045 rc 0, PRECHECK `t 0 0 t t t t`, 045 re-applied, POSTCHECK green with the same grid; negative controls on separate databases: a 045 without the view's sale key FAILS ("the tie-break serves 50.000, expected the sale 30") and a 045 without the top-label constraint FAILS ("kb_merchants accepted an all-digit host"). Measured caveat: the first tie-break check used random uuids and passed on the no-sale-key 045 by chance (a 50 % test); the POSTCHECK now inserts explicit ids (the list row carries the larger id), so it fails deterministically.

## Deviations

1. F1-6 all-digit host: the rule is "the TOP-LEVEL label carries a letter" (`[a-z][a-z0-9-]*$`), not literally "a letter in the registrable label". Reason: a regex cannot compute the registrable label (multi-label suffixes such as com.bh), and the registrable-label reading would refuse real hosts with a digit registrable label (4711.com, the 4711 cologne house; 163.com), while a WHATWG URL parser treats exactly a numeric LAST label as IPv4; every all-digit host is refused either way (pinned: 10.0.0.1, shop.123, 1.2.3.4 refused; 4711.com accepted). One 045 belt edit: a named constraint on kb_merchants (the host CHECK the adversary named); the leaf applies the rule to every host and URL host.
2. Existing RED-file rows edited (ruling-authorised): OFFER_ORDER (F1-4, r13 / r14 / r15), r06's revoke text (F1-9), EXPECTED_CONSTRAINTS[kb_merchants] (F1-6), r21's APP_OK += source_router (F1-3 needs the import; r21b pins that it is function-local), ACCEPTS[registry_entries] gains host="noon.com" (F1-3 domain == host would refuse it otherwise; its entries are byte-identical, so it "stays green" as ruled).
3. Refusal rows re-pointed (F1-5 / F1-7; each was refused by more than its named clause, so its clause-only mutant could not kill it): deny_not_bool (deny=1 -> 0), registry_nan (nan moved into a Source dict field, since an unknown key is now refused by the key clause), id_not_extending (an id of valid length with another prefix), merchant_upper -> RENAMED merchant_single_label (merchant_id "example": an upper-case merchant can never sit on a lower-case URL host, so that row could only ever be two-clause), url_upper_host ("https://WWW.shop.example/p"), offers url_denied, images url_denied / provenance_denied / provenance_denied_sub, specs source_denied, reviews source_url_denied, gaps hint_denied_host / hint_denied_url / hint_denied_name (belt-hit inputs -> rule-only path / hyphen / top-level tokens).
4. Two small leaf restructures for F1-7 with no behaviour change: the offer builder's redundant URL-regex line removed (equality with canonical_offer_url's output already implies it); the coverage builder emits `str(day)` (identical to `day.isoformat()` for a date).
5. The F1-7 clause table was proved in memory, not through the bounded runner (budget; see NOT MEASURED).
6. Budget: the round ran 2 h 20 min (05:25 -> 07:45); the box ran the mutation table at about 25 s per mutant (2x the GREEN pace).
7. Two mutation batches and one wait loop exceeded the tool's 600 s foreground limit and were moved to the background by the tool; no second pytest ran while they ran (only psql, sqlfluff, file edits).
8. The F14a negative control first passed by chance (random uuids); fixed in the POSTCHECK (explicit ids) and re-run: fails deterministically.

## Questions for the gate

- Q1 (deviation 1): accept the top-level-label reading of "all-digit host" (4711.com stays valid) or require a letter in the registrable label (refusing 4711.com / 163.com)?
- Q2: accept the in-memory proof of the 115 clause-only mutants, or run them through the bounded runner in the re-verifier (clauses.py + fix_mutate.py indices 92-206 are ready; about 50 min on the loaded box)?
- Q3: the renamed row merchant_upper -> merchant_single_label changes one node id; acceptable as a re-point?
- Q4: the card's tie-break key is an expression after `captured_at DESC`; `idx_kb_offers_latest` is unchanged (the planner sorts the tie key incrementally). The 60,000-offer plan was not re-measured this round.

## NOT MEASURED

- The bounded-runner pass of the 115 F1-7 clause-only mutants (in-memory dry run only; 7 of them ran through pyt as A1 / A5-A9 / F13b).
- The 60k-offer planner check of the card with the new tie-break key.
- The Supabase SQL editor itself; PostgreSQL 15 / 16 / 17.
- The four test_precommit_hook*.py files (excluded by rule; .githooks untouched).
- The base re-run of the comm set (GREEN's base record used, as ruled).

## End state

`git status --short`: empty. HEAD ee09729da43cb4a0769736c2ab04951a5fad51fd on feature/s81-s14-kb-schema (parent 0910e7d0). No .qa-mutation.lock. No pytest process with an s14f1 tag. PostgreSQL cluster stopped; its data dir <scratchpad>/S81-14_fix1/pg/data left in place. PR body: <scratchpad>/S81-14_fix1/PR_BODY.md. The six APPLY files in sc-s81-s14/.qa-s80/ (the orchestrator copies them to the state folder).
