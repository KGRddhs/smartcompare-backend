# INC-I2b GUARD-WORDS + SHOP-IMAGE-TIER: RED report (S96 main lane, 2026-11-17 01:50-02:52 AST)

Unit: INC-I2b, three dark flags ENABLE_IMAGE_GUARD_WORDS (W), ENABLE_SHOP_PAGE_IMAGE (A), ENABLE_SHOPPING_THUMB_IMAGE (B), default OFF; FOCUS (I-1). Worktree sc-s96-i2b, branch fix/inc-i2b-guard-words-shop-tier at main 5cd93c6a. Spec V2 + RULINGS I-1..I-19 read in full at start and before reporting.

## Files (new, untracked; sha256 over bytes on disk)
- tests/test_inc_i2b_guard_words_shop_image.py: c206cfd2dd4601bac2d7938f1f3d86a122599b186a6fca47d4d3ef8154feb06a, 54314 bytes, 0 non-ASCII, LF, black-clean, ruff clean
- tests/fixtures/inc_i2b_flag_off_golden.json: 73e94432da4236d6d4d183a63c78277fdfa08f4e0dfc55f6594086a6f45cd9b8 (recorded at base 5cd93c6a by a temp recorder, deleted)
- tests/fixtures/inc_i2b_guard_words_corpus.json: 510d42d756d6e6ed621636698dc3a6d826b3fc21622ff12971bd6a02a137e18a (the spec corpus, ASCII with escapes; the spec's expected_* keys dropped)
- notes: proto.diff (d4025fbb..., 147478 bytes, saved before restore), proto_apply.py, mutants.py, mutants.json, corpus_base.json, corpus_proto.json, commset.txt, comm_*_failed.txt

## Runs (netguard 0 on every RED run)
- base3 (final RED file): [pyt] tag=s96b-red-base3 elapsed=4s status=FAIL rc=1: 22 failed (every E row, AssertionError only, 0 other errors), 6 passed (P1 x2, P2, P3, P4, P5)
- proto2: [pyt] tag=s96b-red-proto2 elapsed=35s status=OK rc=0: 95 passed (RED 28 + test_inc_i2a_picture_not_cut.py 67 with the moved E22 / BIND)
- proto3 (final RED file): [pyt] tag=s96b-red-proto3 elapsed=4s status=OK rc=0: 28 passed
- proto1: E17 failed on a TEST bug ("https=2" contains "http"); the check became "://" / "http:" (no app change)
- comm set: 321 files, sha256(list) 80ec83522352be557ffae627b292ef8b1f49cc7b2b4730957856f0daa191ffbc, 13 chunks, bound 1200; base 24 FAILED/ERROR (environmental: test_page_scraping x2, test_prompt_truth x2, test_s81_d16, d17, d22c x5, s07, s10, s16 x5, s18b, s19, s22 x2, s24 x2); head (prototype) the same 24; comm -13 EMPTY, comm -23 EMPTY. Chunks 06/08/09/10 rc=1 at base and head (the same nodes), the rest OK. Base record: harness/base_records/5cd93c6a.../80ec8352....txt (+ .files.txt).
- moved pin: the base I2a file against the prototype ([pyt] tag=s96b-red-moved status=FAIL): 1 failed, 66 passed: test_e22_guard_version_in_the_name: "assert _guard_digest() == rules, image_relevance guard source changed: bump PICK_GUARD_RULES" -> '9940836e' == 'a9bdcc90'. No other node moved.
- lint at the prototype: ruff E9,F63,F7,F82 clean on the six touched .py files; full ruff clean on image_relevance.py and the RED file; black --check clean on image_relevance.py, the I2a test, the RED file (a py3.15 target warning prints; the check passes).

## Prototype (in place under .qa-mutation.lock, from byte copies, by spec V2 section 3)
IR: docstring; WORDS_FLAG_ENV, SHOP_PAGE_IMAGE_FLAG_ENV; FORM_WORDS, FORM_JOINS, INTENSE_WORDS, INTENSE_GENERIC_NEXT, CONC_PHRASES, CONC_CLASS, SHOPPING_TIER; REASONS + form, concentration; guard_words_enabled, shop_page_image_enabled; Identity.query_words / query_conc; identity (typed); check -> _check_base + new check; _conc_scan, _conc_labels, _words_reason, words_reason_for; RelevanceCall.accept_thumb; relevance_kwargs(typed=None). IMG: PICK_GUARD_RULES a9bdcc90, the axis, SHOPPING_THUMB_FLAG_ENV, shopping_thumb_enabled, stamp_shop_image, shopping_thumbnail, _log_shop_keys, _shape_keys. SCS: _typed_image_text, the INC-R1 carrier, typed= at both relevance_kwargs calls, the B block before the Fact-check, the shopping arm of _late_image_choose. WOO: the leaf import, _shop_prods, the guarded stamp on the winner. CLAUDE.md: three flag sentences + the section. I2a test: GUARD_SET V2 (moved E22), BIND + shopping.
Restore: every edited file byte-identical to base (git hash-object == HEAD blob, six files); lock deleted; git status --short = the three new files only.

## Mutants (RED file alone; KILLED = assertion failure; 0 non-assertion errors)
| id | result | killing rows |
|---|---|---|
| M1 | KILLED | test_e04_kept_and_refused, test_e19_guard_version_bumped |
| M2 | KILLED | test_e04_kept_and_refused, test_e19_guard_version_bumped |
| M3 | KILLED | test_e04_kept_and_refused, test_e04b_intense_after_a_phrase_is_its_label, test_e19_guard_version_bumped |
| M4 | KILLED | test_e01_corpus_s_on_typed_and_untyped, test_e02_corpus_s_off_and_no_concentration_queries, test_e03_corpus_per_class, test_e04b_intense_after_a_phrase_is_its_label, test_e04d_extrait_folds_and_brand_forms_exempt, test_e05_typed_concentration_seam, test_e09_woo_stamp_on_the_winner, test_e10_stamp_through_the_late_chooser, test_e11_stamp_refusals, test_e12_thumb_last_resort, test_e15_camera_product, test_e18_late_thumb_bound_never_stored, test_e19_guard_version_bumped |
| M5 | KILLED | test_e01_corpus_s_on_typed_and_untyped, test_e02_corpus_s_off_and_no_concentration_queries, test_e03_corpus_per_class, test_e11_stamp_refusals, test_e19_guard_version_bumped |
| M6 | KILLED | test_e04_kept_and_refused, test_e19_guard_version_bumped |
| M7 | KILLED | test_e07_words_flag_read_once_after_a_pass, test_e19_guard_version_bumped |
| M8 | KILLED | test_e08_cache_axis |
| M9 | KILLED | test_e19_guard_version_bumped |
| M10 | KILLED | test_e01_corpus_s_on_typed_and_untyped, test_e02_corpus_s_off_and_no_concentration_queries, test_e03_corpus_per_class, test_e05_typed_concentration_seam, test_e11_stamp_refusals, test_e19_guard_version_bumped |
| M11 | KILLED | test_e11_stamp_refusals |
| M12 | KILLED | test_e11_stamp_refusals |
| M13 | KILLED | test_e11_stamp_refusals, test_e14_shapes_and_failures |
| M14 | KILLED | test_e12_thumb_last_resort |
| M15 | KILLED | test_e12_thumb_last_resort, test_e19_guard_version_bumped |
| M16 | KILLED | test_e12_thumb_last_resort, test_e17_line_grammar |
| M17 | KILLED | test_e18_late_thumb_bound_never_stored |
| M18 | KILLED | test_p1_flag_off_golden[None], test_p1_flag_off_golden[false] |
| M19 | KILLED | test_e12_thumb_last_resort, test_e18_late_thumb_bound_never_stored |
| M20 | KILLED | test_e09_woo_stamp_on_the_winner, test_p5_shop_flag_unset_is_the_base_adapter |
| M21 | KILLED | test_e14_shapes_and_failures |
| M22 | KILLED | test_e04_kept_and_refused, test_e19_guard_version_bumped |
| M23 | KILLED | test_e04_kept_and_refused, test_e04c_bare_gift_and_travel_never_refuse, test_e19_guard_version_bumped |
| M24 | KILLED | test_e01_corpus_s_on_typed_and_untyped, test_e03_corpus_per_class, test_e04b_intense_after_a_phrase_is_its_label, test_e19_guard_version_bumped |
| M25 | KILLED | test_e12_thumb_last_resort, test_e18_late_thumb_bound_never_stored, test_e19_guard_version_bumped |
| M26 | KILLED | test_p5_shop_flag_unset_is_the_base_adapter |
| M27 | KILLED | test_e04d_extrait_folds_and_brand_forms_exempt, test_e19_guard_version_bumped |
| M28 | KILLED | test_e04d_extrait_folds_and_brand_forms_exempt, test_e19_guard_version_bumped |
| M29 | KILLED | test_e05b_carrier_only_with_w_on |
| M30 | KILLED | test_p4_relevance_dict_and_identity_build |
| M31 | KILLED | test_e08_cache_axis |
| M32 | KILLED | test_e12_thumb_last_resort |
| M33 | KILLED | test_e05_typed_concentration_seam |

M6 and M15 were first killed by E19 only; two behaviour assertions were added (E4: typed Parfum vs "Elixir Parfum" -> concentration; E12: a wrong-brand thumb -> rejected brand) and both re-ran KILLED by those rows. 33 / 33 KILLED. Every IR mutant inside GUARD_SET also fails E19 by construction.

## Corpus (false-accept / false-refuse; W unset vs W ON)
- S ON typed: FA 65 -> 7, FR 22 -> 22 (0 right newly refused); per class FA: body 17 -> 0, conc 20 -> 0, gift 9 -> 0, refill 6 -> 0, mini 5 -> 0, flanker 6 -> 5, twin 2 -> 2; FR base 3, base/ar 11, size 1, size/ar 1, tester 1, tester/ar 5 unchanged
- S ON untyped (the R ON default case): FA 65 -> 27, FR 22 -> 22
- S OFF typed: FA 59 -> 7, FR 25 -> 25; untyped FA 59 -> 23
- no-concentration queries (S ON and OFF, typed and untyped): FA 10 -> 1, FR 9 -> 9
- at base the W ON column equals the base column. The spec E1-E3 numbers reproduce in the real app.

## Deviations
- E13 (hard caps) NOT WRITTEN, NOT MEASURED.
- E8: the L ON get_cached half not written; the axis is proven on pick_cache_name.
- E11: "... Eau de Parfum Intense" is NOT a free intense under I-9; the row uses "Dior Sauvage Intense Eau de Parfum 100ml".
- E5: "no line holds the typed text" is asserted on [IMG_RELEVANCE] and IMG_SHOP lines only (the base "[image] Tier 1 Serper hit" line logs full_name = the typed text).
- P1 golden reduced: corpus verdicts, two cascade calls with lines, relevance dicts, the Woo dict, two _fetch_product_data runs (L OFF / ON); no sync / stream or R ON compare.
- P3 is one G OFF _fetch_product_data; P5 asserts the A reader count in (0, 1) (0 at base).
- GUARD_SET text: 22 sources then table lines, newline-joined (defined by the RED file and the moved E22).
- Comm seeds per the task prompt (no SCS module seed) plus spec symbols; the source-scanning list reused from the I2a derivation at fd983471; client jest fences not run.
- .github/black-clean-paths.txt not edited.

## Open questions
- OQ-A..OQ-D of the spec stand.
- E11 / I-9: confirm A refuses only a FREE intense.
- P5: pin the A reader at exactly one read per winner in GREEN.
