# FIX1_RULINGS_INC_P2 - fix round 1 of INC-P2 (orchestrator S96-FIX, Claude Opus 5.5, 2026-11-17)

These rulings answer the two NOT_READY adversary reports on GREEN head 8abc5115fa3b98dafb9afa0ae7ee506aa33267da (branch fix/inc-p2-price-not-lost, built on fd983471):
- <SP>/INC-P2_adv/correctness_REPORT.md (MAJOR-1..3, m1-m8)
- <SP>/INC-P2_adv/engineeringandclienttruth_REPORT.md (MAJ-1..3, m1-m8)

GREEN's report is <SP>/INC-P2_green/INC-P2_GREEN_REPORT.md. Neither adversary found a blocking issue. Every MAJOR below is fixed in this round. This round also rebases onto the new main.

## Procedure for the fix agent (in order)

### 0. REBASE (the one rebase this round allows)
- Check that `git -C <worktree> status --short` is empty and that HEAD is 8abc5115.
- Run `git -C <worktree> fetch origin main`, then `git -C <worktree> rebase 5cd93c6aaa4e80e4b0ab36a43e6fa1f657d797c9`. Main moved twice since fd983471:
  - #412 INC-C1a (2e7a1229): SmartCompareApp files plus tests/test_s81_12_legal_v3.py.
  - #413 INC-I2a PICTURE-NOT-CUT (5cd93c6a): app/services/image_service.py, app/services/structured_comparison_service.py (+229 / -20), CLAUDE.md, .github/black-clean-paths.txt, tests/test_inc_i2a_picture_not_cut.py and its golden fixture. It sits dark behind ENABLE_IMAGE_LATE_BIND.
- #413's SCS regions:
  - three module functions after _timed_task;
  - an __init__ line beside _compare_deadline;
  - one line in each per-run reset beside _partial_product_data;
  - a drain call at the three hard-cap arms;
  - a bind call just before "Step 5: Build complete response" in both paths;
  - three methods before _fetch_product_data;
  - inside _fetch_product_data: the picture task, the except BaseException arm, the result loop, the timing loop and the page-image block.
- Resolve every conflict by keeping BOTH sides. You never edit a line #413 owns beyond placing your hunk next to it. The main lane owns image_relevance.py, image_service.py and SCS Phase 1, so never change their logic.
- Your CLAUDE.md block goes AFTER the blocks #413 added, before `## Tests`.
- If a conflict cannot be solved by keeping both sides, run `git rebase --abort` and stop with a report.
- List EVERY hand-resolved hunk (file, line range, what each side held, how you joined them) in the report section "Rebase".
- At the rebased head, run before any other change:
  - the frozen pair with the flag ON and OFF (495 / 495 each);
  - tests/test_inc_i2a_picture_not_cut.py (it must pass as on main);
  - tests/test_s81_12_legal_v3.py.

### 1. RED step
- Append rows to the two RED files, or to a NEW file tests/test_inc_p2_fix1.py if that is cleaner. Every existing row stays byte-identical.
- Each new RED row must fail at the rebased HEAD on an AssertionError only. Each new PIN row passes.
- Record the new sha256 values. Rows by fix: listed under F1-F7.

### 2. GREEN step
- Smallest hunks. The flag is the first statement of every gated predicate.
- Flag OFF stays byte-identical on every body, event, cache row and log line that exists today (except the readers' skip in F4, which is keyed on a stored marker that a flag-OFF body never carries).

### 3. Documentation (D1-D6 below)
- Apply these to the CLAUDE.md block and to the PR body <SP>/INC-P2_green/PR_BODY.md. Write the new body to <SP>/INC-P2_fix1/PR_BODY.md, under 25 KB.

### 4. Gates
- the unit files ON and OFF;
- the CI-order set;
- the comm set by the union rule at the final head (F5);
- the fourteen client fences once (the node_modules junction exists; never delete it);
- ruff and py_compile;
- black --check on any edited file listed in .github/black-clean-paths.txt;
- the hook test files ALONE.

### 5. Commit
- ONE commit on the branch, with the trailer "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>". No push.

## Fixes

F1 (corr MAJOR-1 = eng MAJ-2: private keys leak on a wire fault)
- Rule: no key starting with "_p2" ever reaches a body, SSE event, History row or cache value, in any cell and on any fault path. Strip them in the response_builder fallback branch (the branch that ships product_data when _p2_wire_prices returns None) and on every other path that copies product dicts to the wire. With the flag OFF no such key exists, so the strip is a no-op there.
- RED rows (B18 class, extended): with the flag ON and p2_wire_price raising, in cap0 and cap1, none of these carries a _p2 key or the hidden listing url:
  - the overview;
  - the legacy products alias;
  - the stream complete event and the prices event;
  - the body passed to the History persist (drive it if reachable; otherwise state it).
- A further row covers the same check with the flag turned OFF between the reconcile and the build.

F2 (corr MAJOR-2: an unflagged evaluation outside its guard)
- Rule: every unflagged trace or log line evaluates ALL of its arguments inside its own try/except. Compute the price-trace key inside the guard. Audit every unflagged line GREEN added for the same shape and list each one in the report.
- PIN row: with the flag OFF and a truthy non-str variant, an L1 hit returns the cached price exactly as at the base. Measure it at 5cd93c6a in a scratch worktree too.

F3 (corr MAJOR-3: P2-7 writes a partner-dictated size under a shared key)
- Rule (it narrows P2R-5): the P2-7 cache write stores a re-selected price ONLY when one of these holds:
  - (a) the side has a TYPED size, the re-selected listing is at that size, AND the text the cache key is built from (brand + name + variant) carries that same size (extract_size_ml_any on it equals the size);
  - (b) the side is UNTYPED and the re-selected listing is exactly 100 ml, the basis a bare-name key already means with the flag OFF.
- A size dictated by the partner side is never written under a key that does not carry it.
- Measure and state which of (a) is reachable with ENABLE_PRODUCT_RESOLVER off and on.
- RED rows:
  - "Ted Baker M 30ml" vs "Sauvage EDP" writes nothing under Sauvage's key.
  - The next "Sauvage EDP" vs "Bleu de Chanel EDP" then shows the base state with the flag OFF (the rollback) and the flag ON (both cells).
  - A cross-pair walk: run every fixture pair with the flag ON, then run every fixture pair again with the flag OFF reading the same cache. Every flag-OFF body equals its no-prior-write base body.
- Docs: correct the rollback sentence. Entries written under the flag live up to the TTL (7 days). They are only own-size or 100 ml entries, which the flag-OFF path reads as a genuine price for that key. Name the purge option.

F4 (eng MAJ-1: the saved-history savings readers add savings across bottle sizes)
- Rule: add app/api/home_routes.py and app/api/profile_routes.py to the change list. In each, _extract_winner_loser_prices returns (None, None), so the row is skipped, when full_response.metadata.pair_price_sizes is a dict whose mode is present and is not "same_size".
- This is NOT flag-gated, on purpose. A row stored during a flag window must stay skipped after a rollback. A body stored with the flag OFF never carries the marker, so every existing row is read exactly as today.
- RED rows:
  - Both extractors on stored flag-ON bodies of T3-01, in cap0 and cap1: skipped.
  - Same for YSL / Lancome in cap1 and the mixed pair: skipped.
  - A same_size pair: counted, with the same amounts as the base.
  - A body without the marker: counted exactly as at the base (PIN).
- A walk row: every flag-ON fixture body that shows both amounts at different or unknown sizes carries metadata.pair_price_sizes with mode != "same_size". The skip then covers every cross-size case. Also show that the persisted History body carries the marker (text_routes persists `result`).
- The SQL RPC home_savings_aggregate (migration 036; it reads only when ENABLE_HOME_SAVINGS_AGGREGATE is on): NO migration in this unit. This is a FLIP PRECONDITION stated in the flip note: ENABLE_HOME_SAVINGS_AGGREGATE stays OFF while ENABLE_PRICE_NOT_LOST is on, until a later migration adds the same filter. The orchestrator reports this to the relay.

F5 (eng MAJ-3: the comm set is missing members)
- Add to the union:
  - tests/test_migration_index_predicate_immutability.py;
  - tests/test_s81_s09_gate_rows.py;
  - the eight importers of scripts/eval_runner.py (test_cron_eval_nightly, test_eval_gate, test_eval_grading, test_eval_kpi_gate_verdict, test_eval_persistence, test_eval_runner, test_kpi_metric, test_s71_u13_harness_auth);
  - every reader and importer of home_routes / profile_routes;
  - tests/test_inc_i2a_picture_not_cut.py plus every file #413 and #412 touched that the union rule reaches.
- Re-derive the set from the import graph, not only a literal grep. Run it at the final head.
- branch-only-new is computed against the base record. A new failure is re-run at 5cd93c6a in a scratch worktree.
- Correct the PR body figures.

F6 (surviving mutants: add killing rows)
- X01: a 25 ml listing is under the P2R-12 floor, a 30 ml one is not.
- X04 = E09: no size_ml / per_ml stamp on a shown price without a url (X1-R12).
- X05: the restore's region-currency guard.
- E06: PRICE_OUTCOME prints cap=none with the flag OFF and the token present.
- E12: the legacy alias mirrors best_price / retailer of a restored side.
- Re-apply each of these as a mutant after GREEN and report it KILLED.

F7 (log truth, cheap)
- corr m4: PRICE_OUTCOME reads the miss-ledger notes under the SAME key they are written under. Add a row for the variant-in-name shape and the brand-repeated-in-name shape.
- corr m5: a floor pend logs reconcile=floor, not reselect.
- Both are log-only.

## Rulings on GREEN's questions and the minors
- GREEN Q1: answered by GATE sections 6-8 (D1 below).
- GREEN Q2 (test_s80_b1 p8 transient): ACCEPTED. It passed alone and in a chunk re-run, and home_routes reads none of the edited code. Re-check it in F5's run, now that home_routes is edited.
- GREEN Q3 (W4-7 replay duplicates rejected counts) and Q4 (PRICE_OUTCOME on share / history rebuilds, reconcile=unknown): stated limits, log only.
- corr m2: a stated limit. The 1.0 s wait_for bounds the write only with ENABLE_ASYNC_REDIS_OFFLOAD on, which is absent in production. The synchronous Upstash call is bounded by its own client timeout.
- eng m6: a stated limit, about 4 s worst case per compare under the flag.
- eng m4 (the P2R-11 rules not noted: select_best, showable, implausible_low, concentration, out_of_stock): a stated limit named in the D6 bullet.
- eng m5 (id() reuse in the parked / recovered sets): a stated limit, log only.
- eng m8: when one side's size is unknown and the other is known and not 100, pair_price_sizes says different_sizes and 2e7a1229 draws its note. State it.
- corr m7 = eng m7: the gate's byte count is corrected by the orchestrator (93,227 B).

## Documentation
- D1. The PROOF table, per GATE sections 6-8:
  - The fourth app update (group c5a02157, from 2e7a1229, live since 2026-11-16 23:46 AST) SENDS price_size, so a phone cold-started twice after that is cap1. Any other phone is cap0.
  - Each pair row gives what the owner sees in cap1 and in cap0.
  - Pairs: T3-01 "Ted Baker M 30ml" vs "Dior Sauvage 100 ML Edp"; the untyped different-size YSL / Lancome pair of R01 (use the fixture's own names); a mixed pair; "Sauvage EDP" vs "Bleu de Chanel EDP"; and the BR540 row.
  - Each screenshot names its cell.
- D2. The FLIP NOTE carries:
  - the flag;
  - the canary filters, plain words with no bracket: PRICE_OUTCOME, cap=0, reconcile=offsize_held, marketplace=1 (the ORCH-P2-C count), miss=timed_out;
  - the rollback, as corrected by F3;
  - the F4 precondition;
  - this P2R-37 sentence, VERBATIM: "A phone without the app update can show two prices for different bottle sizes with no size drawn, and no price comparison is made."
- D3. Correct the overstated claims (corr m3, eng m2). "Never pended for size" is false for a typed off-size side and a tokenless untyped side. "Every price-comparing consumer gets the flag-OFF inputs" is false in the rule-4 projections (A19 / A30) and was false for the savings readers before F4. "The private keys never reach the wire" now holds by F1: say so with the row ids.
- D4. The comm-set figures from F5's run. The title stays "fix(price): INC-P2 price-not-lost - each side priced at its own bottle size, dark behind ENABLE_PRICE_NOT_LOST".
- D5. CLAUDE.md block: the same corrections, the two new files on the change list, the F4 precondition, and the rollback as F3 corrects it.
- D6. Stated limits: D3-D9 (P2R-28), P2R-31, P2R-36 (marketplace: count first), corr m2, eng m4 / m5 / m6 / m8, GREEN Q3 / Q4, and D8 narrowed.

## Re-verifier (correctness lens, one agent; the leaner chain)
- Verify HEAD and that the branch sits on 5cd93c6a (`git merge-base --is-ancestor 5cd93c6a HEAD`).
- Re-hash the RED files. Run the unit files ON and OFF.
- Read every hand-resolved rebase hunk against both parents. Report any line of #413 that changed as a MAJOR.
- Apply at least eight mutants: at least one per fix F1, F2, F3, F4 and F7, plus X01, X04, X05, E06 and E12 re-applied. All must be killed.
- Run the CI-order set, the comm chunks that hold the home_routes / profile_routes readers, the SCS importers and tests/test_inc_i2a_picture_not_cut.py, the hook test files ALONE, and the fourteen client fences once.
- Check the CLAUDE.md block and the PR body sentence by sentence against the bytes.
- Confirm every MAJOR and MINOR of both adversary reports is closed or recorded.

## D7 (relay, 2026-11-17 01:55 AST; accepted rulings F1-F7 / D1-D6)
The FLIP NOTE carries a short table: behaviour | the switch state it needs | production today (names only, from the relay's read). Rows:
- the Hawas gender row: needs ENABLE_LISTING_MATCH_GUARD on; not set on web (default off), so it is INERT today;
- _seen_at on the wire: needs ENABLE_EXACT_PRICE_GATE false; not set on web (default ON), so _seen_at does NOT reach the wire today;
- the 1.0 s bound on the cache write: needs ENABLE_ASYNC_REDIS_OFFLOAD on; not set on web (default off);
- the KB-served cell: needs ENABLE_KB_FIRST_SERVE on; not set on web;
- the resolver interplay: needs ENABLE_PRODUCT_RESOLVER; not set on web;
- the F4 hard rule: ENABLE_HOME_SAVINGS_AGGREGATE is not set on web, and it must never open while ENABLE_PRICE_NOT_LOST is on until a migration adds the same filter to home_savings_aggregate.
