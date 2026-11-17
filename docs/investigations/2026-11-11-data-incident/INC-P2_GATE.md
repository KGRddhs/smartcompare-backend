# GATE_INC_P2 - RED gate of INC-P2 PRICE-NOT-LOST (orchestrator S96-FIX, Claude Opus 5.5, 2026-11-16 23:55 local)

VERDICT: RED GATE PASSED. GREEN may start. Binding on GREEN and both adversaries; it amends the spec where they differ, after RULINGS_INC_P2.md sections A-I.

## 1. The frozen pair (P2R-35)
- tests/test_inc_p2_price_not_lost.py sha256 43d309db521ca62b7df79450e937a0eb44f54c839e8843a4514960dd0bae0dee (93,227 B; the 98,120 figure first given here was wrong, the sha256 always matched)
- tests/test_inc_p2_seam.py sha256 07d72b74a83b7a8d104354ac92dd6fe60b756cbae80219155bf28654e2b69b86 (48,765 B)
- Both are untracked in sc-inc-p2/tests, byte-identical to <SP>/INC-P2/red/am/. Re-hash them first and last; a wrong row is reported, never edited.
- At base b0ad2603: 408 RED (every one an AssertionError) / 87 PIN green. Prototype ON 495/495, OFF 495/495. The flag-OFF body digests (A34, 12 cells; B17, 24 cells) are unchanged.
- Mutants: B's set (RED_REPORT_B.md section 6), re-run where a killing row changed, plus N01-N09 and N07b. Final pass: 24 killed and 2 equivalent (N03, N07), with reasons in RED_AMEND_REPORT.md section 4.
- Reports: <SP>/INC-P2/red/RED_REPORT_B.md (the gated set) and <SP>/INC-P2/red/RED_AMEND_REPORT.md (the amendment). The prototype bytes are reference only: red/am/proto_apply_am.py and red/am/proto_ps_block_am.py.

## 2. What GREEN builds (the contract, in order of precedence)
1. RULINGS_INC_P2.md section H rules 1-4 (P2R-23..P2R-26), section I (P2R-29..P2R-35), then G, then A-F, then the spec and the review corrections.
2. Flag ENABLE_PRICE_NOT_LOST, read per call with the house idiom, as the FIRST statement of every gated predicate. With the flag OFF every response body, SSE event, cache row and log line that exists today is byte-identical. The only unflagged items are those the rulings name: log-only lines, each in its own try/except (P2R-10).
3. Rule 1: a typed side whose listing size equals its own typed size (or whose listing has no strict ml size, per P2R-29) is shown in both cells, whatever the other side and the token. A typed side whose listing has ANOTHER strict size is never shown and never offsize-held, in either cell, whatever ENABLE_EXACT_PRICE_GATE says (P2R-34; A08 gate_off cells).
4. Rule 2: only an UNTYPED side whose listing size differs from the other side's shown price is gated on the X-Client-Capabilities token price_size. Without the token it stays pending with flag OFF's dict plus price.offsize_listing. With the token it is shown with price.size_ml / price.per_ml.
5. Rule 3 (mixed pair) and rule 4 (no side shown with the flag OFF is lost; P2R-31 for A30).
6. Frozen wire names: price.size_ml, price.per_ml, price.offsize_listing, metadata.pair_price_sizes, the token price_size. size_ml, per_ml and pair_price_sizes go to every app. offsize_listing goes only to a side held without the token.
7. Change list: app/services/price_service.py, app/services/response_builder.py, app/services/structured_comparison_service.py, app/api/text_routes.py (D1: keyword price_size_cap on compare_from_text / compare_from_text_streaming at the three phone call sites), plus CLAUDE.md (the flag row). Any other file is a deviation you report. NEVER edit app/services/image_relevance.py, app/services/image_service.py or SCS Phase 1 (about lines 6030-6450 at b0ad2603; the main lane owns them). If a hunk you need sits in that range, stop and report it.
8. PRICE_OUTCOME (one line per side): cap=, reconcile=, shown=, marketplace=0|1, retailer=, origin=, miss= / miss_rule= (P2R-7, P2R-11, P2R-21). The body never reads the ledger (L05).

## 3. Where GREEN builds (one deviation from the template, ruled here)
- Make the branch from origin/main fd983471f3949178ebbbd6d56070d571b37fec93, not from b0ad2603: `git -C <worktree> checkout -b fix/inc-p2-price-not-lost fd983471f3949178ebbbd6d56070d571b37fec93`. This is your ONE branch command. The two untracked RED files carry over. Between b0ad2603 and fd983471 the only changes are #411 INC-I2e: .github/black-clean-paths.txt, CLAUDE.md, app/services/image_relevance.py and a new test file. None of them is on the change list except CLAUDE.md, so no later rebase round is needed.
- BEFORE any edit, run the frozen pair once at fd983471 (tag inc-p2-green-base). It must show 408 AssertionError failures / 87 passed. Any other count: stop and report.
- Base failures for the comm set: <SP>/INC-P2/red/b_base_comm_failed.txt and b_comm_reasons.tsv, recorded at b0ad2603. A branch-only-new failure is re-run in a detached scratch worktree at fd983471 to tell main's change from yours; never stash or reset the real worktree.
- Add your CLAUDE.md row AFTER the INC-I2e block that #411 added, before `## Tests`. Keep CRLF if the file has it. Run the two CLAUDE.md readers (tests/test_ci_gates.py, tests/test_behavior_dimension_translation.py) and every reader of .github/black-clean-paths.txt. If an edited file is listed there, run black --check on it.
- The fourteen client fences (common brief, comm-set rule) run once by path from <worktree>/SmartCompareApp. The node_modules junction is already in place (made by the orchestrator; never delete it and never recurse into it). Probe for a running jest first (H5 b) and use gate.py --wait-only.
- Commit trailer: "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>". Commit only the change-list files plus the two frozen RED files. No push, no PR.

## 4. The PR body (draft at <SP>/INC-P2_green/PR_BODY.md, under 25 KB)
- Title: "fix(price): INC-P2 price-not-lost - each side priced at its own bottle size, dark behind ENABLE_PRICE_NOT_LOST".
- Say "merged, NOT yet proven" and include a PROOF ON THE PHONE section from RULINGS section E as amended by G and H. The T3-01 pair "Ted Baker M 30ml" vs "Dior Sauvage 100 ML Edp" shows both amounts on every app.
- A FLIP NOTE section: the flag, the canary log lines (filter on plain words: PRICE_OUTCOME, then cap=0 / reconcile=offsize_held / marketplace=1 / miss=timed_out), the rollback (the flag false), and what a phone without the token draws: the same as today for an untyped side at a different size (pending), both amounts for typed pairs, and two amounts with no size and limited_data bars in the A30 case (P2R-31).
- Stated limits: D3-D9 (P2R-28), P2R-31, P2R-32 (marketplace prices outside P2-10), D8 narrowed (the moderation-window partial is not driven), and that the status plumbing for refused / no_price_parsed is deferred to INC-P3.
- The defect -> RED node map, the comm-set figures with every [pyt] line, and the template's final "Generated with [Claude Code](https://claude.com/claude-code)" line with its robot emoji (the only non-ASCII allowed, in the PR body only).

## 5. Adversary duties beyond the template
- correctness: re-apply on the GREEN bytes N01, N02, N04, N06, N07b, N08, N09 and at least ten of B's mutants, including M03, M14, M36, M44, M59 and M65. Probe the A30 and mixed-pair wire states against RED_AMEND_REPORT.md section 4 "Measured wire states". Prove flag-OFF identity on the A34 / B17 digests.
- engineering and client truth: everything in the template's engineering duties, plus: for each wire state (shown with size, held with offsize_listing, pending), read what the store bundle 683f56c0 and the OTA bundle 82172383 actually draw, using `git -C <worktree> show <sha>:SmartCompareApp/...` (no new keys rendered; limited_data dims dropped). Check that no key outside section 2 item 6 reaches the wire, and that the private _p2 keys are stripped everywhere (REST, the stream complete and prices events, the tail partial, History rows, the cache).

## 6. ADDENDUM 2026-11-16 23:55 local: main moved to 2e7a1229 (#412 INC-C1a SIZE-LABEL, the client half of this contract)
- origin/main = 2e7a1229b78d1630efcb6593cfd0db76bd72c71d (parents fd983471 and 866668c4): 13 SmartCompareApp files plus tests/test_s81_12_legal_v3.py. No backend app/ file. GREEN stays on fd983471. The orchestrator rebases onto 2e7a1229 after the adversaries and re-runs the fourteen client fences and the comm set's readers of the moved files on the rebased bytes.
- Checked by the orchestrator at 2e7a1229, and matching the frozen RED byte for byte:
  - requestContext.ts:38 CLIENT_CAPABILITIES = ['price_size'], sent as X-Client-Capabilities joined with ',';
  - types.ts:74-76 price.size_ml / price.per_ml;
  - types.ts:315 metadata.pair_price_sizes {mode: 'same_size' | 'different_sizes' | 'unknown', sizes_ml: [n | null, n | null]};
  - ResultsContent.tsx:215-250 draws "<price> . <size> ml" only for an integer size_ml in 1..9999 on a shown price, a per-ml line only when per_ml > 0 and finite, and the different-sizes note only when mode == 'different_sizes' with both prices shown.
- The fourth app update (published by the relay) DECLARES the token, so with the flag ON that app is in the cap1 cell. Older bundles (store 683f56c0, OTA 82172383) are in cap0.
- Adversary "engineering and client truth": read what 2e7a1229's ResultsContent draws for each wire state, in addition to the two older bundles. Report as a MAJOR any key, mode string or type that the server emits differently from these lines.

## 7. ADDENDUM 2026-11-16 23:59 local (ORCH-P2-C, RULINGS section J): the PR body's FLIP NOTE adds the marketplace count filter (the plain words PRICE_OUTCOME and marketplace=1), the P2R-31 sentence ("a phone without the app update can show two prices for different bottle sizes with no size drawn, and no price comparison is made"), and a table of phone pairs with what the owner should see, for a phone on the fourth app update (it sends price_size) and for one without it. No marketplace-hide code in this unit.

## 8. ADDENDUM (relay note, 2026-11-16 23:51 AST): the fourth app update is LIVE
- Update group c5a02157-ca43-4b1d-9255-4574d97ed573, runtime 1.0.0, built from main 2e7a1229, live for iOS and Android since 23:46 AST.
- The flip note's phone table names the cell plainly:
  - A phone cold-started twice after 23:46 sends X-Client-Capabilities: price_size (cap1) and draws size_ml, per_ml and the different-sizes note.
  - A phone that has not is the tokenless cell (cap0).
- The proof says which cell each screenshot came from.

## 9. ADDENDUM (relay note, 2026-11-17 00:57 AST): main = 5cd93c6aaa4e80e4b0ab36a43e6fa1f657d797c9 (#413 INC-I2a PICTURE-NOT-CUT, dark ENABLE_IMAGE_LATE_BIND)
- This target replaces 2e7a1229 for the orchestrator's rebase before the PR.
- Files moved: app/services/image_service.py, app/services/structured_comparison_service.py (+229 / -20), CLAUDE.md, .github/black-clean-paths.txt, and a new test plus its fixture.
- The collision file is SCS. These are #413's regions:
  - three module functions after _timed_task;
  - one __init__ state line beside _compare_deadline;
  - one line in each per-run reset beside _partial_product_data;
  - a drain call at the three hard-cap arms;
  - a bind call just before "Step 5: Build complete response" in both paths;
  - three methods before _fetch_product_data;
  - inside _fetch_product_data: the picture task, the except BaseException arm, the result loop, the timing loop and the page-image block.
- After the rebase, re-run:
  - the frozen pair;
  - the comm set, including tests/test_inc_i2a_picture_not_cut.py, the CLAUDE.md readers and the black-clean readers;
  - the fourteen client fences.
- Every hand-resolved hunk is listed in the gate line to the relay.

## 10. ADDENDUM (relay note, 2026-11-17 05:58 AST): main = 6473769eb50cdb65fbdbd732792fe5f535a16ef0 (#416 INC-I2b GUARD-WORDS, three switches off)
- This target replaces 5cd93c6a. Fix round 1 (wf_8184f71a-8a9) was launched against 5cd93c6a and is NOT messaged (never SendMessage a workflow agent).
- After fix round 1 and its re-verifier come back SOUND, the orchestrator rebases the branch once more onto 6473769e itself, before the push.
- Collision files: app/services/structured_comparison_service.py (+74 from #416) has these regions:
  - a helper after _product_display_identity;
  - a resolver hook near _resolve_explicit_pair;
  - the late chooser;
  - the two relevance_kwargs calls in _fetch_product_data;
  - a thumbnail block after the page-image block.
- CLAUDE.md is also a collision file. woocommerce_service.py is not on the P2 change list, so no hunk is expected there; any conflict there is a deviation.
- After that rebase, re-run:
  - the frozen pair;
  - the comm set, plus the I2a test and the five new #416 test files;
  - the CLAUDE.md readers, the black-clean readers and the fourteen client fences.
- Every hand-resolved hunk from both rebases goes in the PR line.
