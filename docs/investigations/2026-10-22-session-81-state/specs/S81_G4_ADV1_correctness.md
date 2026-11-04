# S81-G4 KB-SERVE adversary report, correctness lens (one adversary, R-G4-1 + spec 12.6 folded in)

Written through the shell (python heredoc). Agent: Opus 5.5. Date 2026-11-04.

## Verdict: SOUND (no blocking, no major; 4 minors as stated-limit rulings; one carried PROCESS item)

## State verified
- Worktree sc-s81-g4: HEAD 0b19de5bcc1416111d48bc725359b95151a658ca, branch feature/s81-g4-kb-serve = base, 19 files staged, `git diff` (unstaged) empty: the GREEN bytes = the index.
- Every one of the 19 files re-hashed first and last against the GREEN report table: 19 / 19 equal (incl. the five FROZEN RED files at their GC-1 sha256).
- Scratch worktree <scratchpad>/S81-G4_adv_correctness made with `git worktree add --detach ... 0b19de5b`, the 19 GREEN files byte-copied in, sha-verified 19 / 19 before and after every mutant; removed with `git worktree remove --force` (no junction ever created there; the clone's node_modules/@babel/core still present). One `git worktree prune` (metadata of missing dirs only).

## CARRIED PROCESS ITEM (not counted in the verdict; orchestrator ruling owed)
The ONE commit is refused by the pre-commit gitleaks step on the FROZEN D16 RED file line 53 (the P2 OpenAPI path-set digest literal, GC-1). Not a GREEN-code defect. Until an E-row (RULINGS_FIX: an inline allow marker on line 53, or a renamed literal) or a prior .gitleaks.toml PR lands, the unit has no commit and cannot open a PR. This adversary judged the staged bytes; after any E-row the frozen sha moves and the D16 file must be re-run (one 600 s unit run suffices: no code depends on the line).

## Gates re-run on the exact GREEN bytes (one pytest at a time)
- [pyt] tag=g4adv-red-off start=2026-11-04 22:04:03 end=2026-11-04 22:04:17 elapsed=14s bound=600s status=OK rc=0 (642 passed; [hermeticity] 642; [netguard] blocked 0) - the four RED files + tests/test_s81_kb_schema.py, ambient OFF.
- [pyt] tag=g4adv-red-on start=2026-11-04 22:04:26 end=2026-11-04 22:04:38 elapsed=12s bound=600s status=OK rc=0 (642 passed; [netguard] 0) - the seven flags exported in ONE runner call (the two mode flags `true` = DRY).
- [pyt] tag=g4adv-ciorder-off start=2026-11-04 22:18:27 end=2026-11-04 22:19:23 elapsed=57s bound=1200s status=FAIL rc=1 (5 failed, 1422 passed; [hermeticity] 1427; [netguard] blocked 28 attempts from 10 nodes = the base figure) - the 11 EXISTING CI-order members OFF (R-G4-5); the 5 failures = the five r27 CRLF nodes of the base record.
- Three comm chunks of my choice, the venv interpreter, GREEN's chunk lists and deselects, vs the STORED base record base_records/0b19de5b.../90b85603...txt (REUSED, LC-6):
  - [pyt] tag=g4adv-comm-09 start=2026-11-04 22:20:08 end=2026-11-04 22:21:17 elapsed=69s bound=1200s status=OK rc=0 (head-only 0, base-only 0; the chunk holding test_legal_disclosure_s77, the d9 pin GREEN fixed)
  - [pyt] tag=g4adv-comm-13 start=2026-11-04 22:21:19 end=2026-11-04 22:21:57 elapsed=38s bound=1200s status=FAIL rc=1 (2 failed = the 2 base-record nodes of that chunk; head-only 0, base-only 0)
  - [pyt] tag=g4adv-comm-23 start=2026-11-04 22:22:05 end=2026-11-04 22:23:03 elapsed=58s bound=1200s status=OK rc=0 (head-only 0, base-only 0)
- GREEN's full comm failed set vs the stored record: `comm -13` EMPTY, `comm -23` EMPTY (14 = 14).
- Comm set re-derived independently: g4spec/comm.py over the scratch worktree (no stored set) UNION the RED's 661 = 665 files; `comm` against GREEN's comm_head_derived.txt: 0 adv-only, 0 green-only. No missing file.
- ruff 0.16.5 --select E9,F63,F7,F82 on the 4 new modules + the 5 edited app files + the test file: All checks passed; py_compile OK.
- Bytes: the 7 new files 0 bytes > 127, 0 CR; the 7 edited files 0 non-CRLF lines. `git diff --numstat`: CLAUDE.md 8/1, admin_routes 62/0, image_routes 4/0, text_routes 8/1, kb_ingest 3/2, scs 99/12, test_s81_kb_schema 9/1; every deleted line read and justified (each is the base statement re-emitted with the hook: the Feature Flags pointer line, include_pros_cons trailing comma, the _PRICE_KEYS tail, the C4 condition, the five live-leg coroutines, the two phase-2 conditions, the two tier guards, the P01_FUNCTIONS tail).
- Text constraints: no robots_registry text in the four new modules; no kb_merchants literal in the two app modules; no partner / merchant_registry in scs; no kb_service token in the two scripts; include_in_schema=False on both routes (P2 green ON and OFF); the capability header value is never logged.
- NOT re-run by this lens: the 14 client jest fences (no client file; GREEN 13 / 14 with the four w37 drift nodes), the hook test files (no .githooks change), the corpus gate (price_service.py not in the diff), the FULL jest (LC-7).

## Mutation (byte copies in the scratch worktree; restored + sha-verified after each; table <scratchpad>/S81-G4_adv/mutation_table.txt, logs <scratchpad>/S81-G4_adv/mut/)
All 42 ruled mutants re-derived on the GREEN bytes and re-applied: 42 / 42 KILLED on an assertion (S18-M1..M14, S19-M1..M12, D16-M1..M10, D17-M1..M6). My first S18-M10 form left a syntax error (38 collection errors: not a kill); its corrected form S18-M10r (`and True)`) is KILLED on an assertion. 11 extra adversary mutants:
| id | change | result |
|---|---|---|
| ADV-1 | metadata.kb_hit stamped unconditionally | KILLED |
| ADV-2 | accepts_asof always True at H1 | KILLED |
| ADV-3 | the H6 card rating / review_count write deleted | SURVIVED (minor m3) |
| ADV-4 | fetch_cards without the wait_for bound | KILLED |
| ADV-5 | the region == bahrain clause dropped | KILLED |
| ADV-6 | identity_confidence high not required for full | KILLED |
| ADV-7 | release deletes without the owner check | SURVIVED (minor m3) |
| ADV-8 | Redis None fetches without a lock | KILLED |
| ADV-9 | the verdict stub carries specs / price | SURVIVED (EQUIVALENT at this base: FIND1 / S18-M14b) |
| ADV-10 | _PRICE_KEYS loses _cache_source (C4 inert) | KILLED |

## Runtime probes (scripts in <scratchpad>/S81-G4_adv/probes/)
- classify + public_price_view (EXACT gate ON): fresh 2 d -> full / fresh, the public price carries as_of and no _-key; 10 d without the capability -> partial / stale_refused (live price leg); 10 d with price_asof -> full / asof; 40 d with price_asof -> stale_refused; rating 4.4 carried. The as_of rule holds with and without the header.
- Verdict key: the same cards with changed live specs / price -> the SAME key (R-G4-3 product-free); a changed quality -> a different key; flag OFF -> None.
- D16 OFF identity: a valid-JSON POST, an extra-key POST and a text/plain POST answer 404 {"detail":"Not Found"} on both /kb/ingest and the unregistered sibling; a MALFORMED-JSON POST answers 422 VALIDATION_ERROR on /kb/ingest vs 404 on the sibling (minor m1).

## R-G4-1 named checks
- kbenrich: namespace: grep of app/ + scripts/ finds it only in scripts/cron_kb_enrich.py; no collision. PASS.
- NX and EX in ONE set call (`set(key, run_id, nx=True, ex=lock_seconds())`). PASS (S19-M3 killed).
- Owner check: GET then DELETE only when the value equals this run's uuid; correct by reading, but UNPINNED (ADV-7 survived) and non-atomic at TTL expiry (stated S81-19-L4). PASS with minor m3.
- Redis None / raising = lock_unavailable, no fetch. PASS (S19-M4, ADV-8 killed).
- D17 never writes a kbh: key: only `pipeline().hgetall(...)` + exec. PASS.
- C4 guard moves no G3 row: test_s81_s17_kb_ingest + test_s81_g3_gate_rows green in the CI-order run OFF (C4 is unflagged). PASS.
- H1 await bounded by the knob: one wait_for over the gather (ADV-4 killed); a miss pays at most the bound. PASS.
- KB price through public_price_view: as_of on the wire, _cached / _cache_source stripped (probe). With ENABLE_EXACT_PRICE_GATE OFF the projection is the identity (base behaviour for every _cached price). PASS.
- metadata.kb_hit only under the flag (ADV-1 killed; the golden). PASS.
- Footprint: 19 files (12 new + 7 edited); the spec's 12.3 '13 new' names 12 files (GREEN's deviation note is right). PASS.

## Blocking: none.  Major: none.

## Minor (documentation rulings; LC-4 stated limits)
- m1 (D16-L1 widened) Flag OFF, POST /api/v1/admin/kb/ingest with a malformed JSON body answers 422 VALIDATION_ERROR (FastAPI decodes the body before solving dependencies), where an unregistered path answers 404. The spec 2.3 sentence 'neither the admin key, the body nor ...' and the CLAUDE.md G4 row 'answer exactly as an unregistered path' overstate it; nothing past the decode runs (no key, no client, no handler). Fix the CLAUDE.md row / PR stated limit wording to name the malformed-body 422 beside the 405.
- m2 (D16 + S81-18) a future `captured_at` in a D16 payload is accepted (build_offer_row checks first <= last only) and classify treats a future last_seen (negative age) as FRESH: probe 'future +300 d' -> full / fresh with as_of 2027-08-31 on the wire; the card's DISTINCT ON last_seen DESC then shadows every later genuine observation of that variant / merchant / market until the date passes. Operator-error only (the bookmarklet sets no captured_at). Recommended follow-up: refuse captured_at > now + a small skew in kb_operator.ingest and treat age < 0 as refused in classify.
- m3 (prove-nothing rows) two GREEN behaviours are correct by reading but pinned by no RED row: the H6 card rating / review_count write on a full hit (ADV-3 survived: the full-hit fixtures never assert result rating) and the S19 release owner check (ADV-7 survived). A GREEN-owned gate row is optional; stated here so no one cites the RED as their proof.
- m4 (D17) `_paged` reads tables with range() and no ORDER BY (kb_products, kb_variants, kb_images, kb_reviews, kb_specs, kb_gaps, search_logs); PostgREST paging without an order is not guaranteed stable, so a table above 500 rows can skip or repeat rows across pages (shares slightly off). The host pipeline uses `exec()` only, so on the redis:// fallback (redis-py `execute`) the host family is omitted with one WARNING (live_robots handles both). Stated limits D17-L5 / D17-L6.

## Claims checked against the bytes
- CLAUDE.md G4 block: every flag / knob name, default and clamp matches the code; the FULL / PARTIAL / MISS description matches H1-H6 (PARTIAL serves the price, an https image and COMPLETE specs only; reviews / rating only on FULL, as the spec says); the R-G4-2 / R-G4-3 / R-G4-6 / R-G4-7 sentences and the owner-steps line are present; CRLF kept; the Feature Flags pointer sentence present. One overstatement: m1.
- PR body (10,023 B <= 25,600): counts match the logs (642/673, 5+1535 CI-order with the four RED files, 14 = 14 comm); 'mutation table 42 / 42 KILLED at the RED prototype' is now also true at GREEN (this report). HEAD marked NOT COMMITTED (the carried item). D17-L4 '100,000 rows' = PAGE_SIZE 500 x MAX_PAGES 200: true.
- Flag-OFF identity: H0 / route reader / H8 one env read each (S18-M1, S18-M11 killed; the golden P1 green); billing (R-A3) untouched (no usage / quota path in the diff); the contract freeze holds (additive as_of and metadata.kb_hit only, both flag-gated; no removed or renamed response key).

## Final hygiene
The worktree sc-s81-g4 untouched by this lens (19 / 19 sha equal at the end, HEAD 0b19de5b); the scratch worktree removed; no pytest of this round left running.
