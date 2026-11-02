# S81-10 FRAGRANCE-ONLY-GATE: adversary report, lens CORRECTNESS (Opus 5.5; written through the shell)

- unit: S81-10 FRAGRANCE-ONLY-GATE (lane A backend, FOCUS; ENABLE_FRAGRANCE_ONLY_GATE default OFF, knobs REFUSAL_DAILY_BUDGET, FRAGRANCE_LEXICON_PATH)
- GREEN worktree C:/Users/SynAckITPC/Documents/AI/sc-s81-s10, branch feature/s81-s10-fragrance-only-gate, HEAD verified 0523a06fe25e4df3682b26a83daa72bf2f2ee543 at start (12:52) and end (13:35); git status --short EMPTY both times; never edited
- scratch worktree: <scratchpad>/S81-10_adv_correctness (git -c core.longpaths=true worktree add --detach ... 0523a06f); the five LF-in-the-GREEN-worktree files (category_gate.py, fragrance_lexicon.json, the two RED files, the gate rows) byte-aligned to the GREEN worktree (sha256 equal, git diff empty), so every run measured the exact GREEN bytes; removed at the end with git worktree remove --force
- frozen RED files (GREEN worktree, start and end): tests/test_s81_s10_fragrance_gate.py d988882a08ac3c57624b8d1ef89492b5a8d0d7ed203a73fa9cfb76fbadad12ac ; tests/fixtures/s81_s10_flag_off_golden.json 159fadb8544f4b44f7f20f7ab1d6a27b0fd6f603592e580607ecfc391e30eb1a ; the HEAD blobs hash to the same values
- verdict: NOT_READY (1 blocking, 0 major, 11 minors)

## BLOCKING
B1 (the frozen RED golden is wall-clock dependent; P01 x5 + R54 x5 are RED on ANY bytes since 2026-11-02T10:00Z, so the PR's CI is red). Golden scenario G10 (GET /api/v1/home/smart-pick, flag OFF) records the body text `"updated_at":"3d ago"`. home_routes._format_updated_at computes `datetime.now(timezone.utc) - created_at` and the RED's `_comparison_row("cmp-1", "electronics", "2026-10-29T10:00:00Z")` is a FIXED date with no clock freeze in `_run_golden`. Elapsed reached 4 days at 2026-11-02T10:00Z (13:00 AST, 13 minutes after GREEN's last green run at 12:47): from then on the body says "4d ago", and from 2026-11-05T10:00Z "Older". Measured on the exact GREEN bytes at 13:00 and 13:02: 10 failed (test_p01_flag_off_golden[unset,false,0,off,empty] and test_r54_off_calls_nothing_of_the_gate[same five]), all `AssertionError: ('G10', 'body', ...) '3d ago' vs '4d ago'`, ambient OFF and ambient ON alike. Not a GREEN-code defect (the same scenario fails at base from 13:00 on; the smart-pick OFF path is untouched), but the two strongest flag-OFF identity pins cannot go green and CI will fail the PR. The flag-OFF identity itself HOLDS: with home_routes._format_updated_at evaluated at the RED's record clock (2026-11-02T08:30Z; probe <scratchpad>/S81-10_adv/probes/test_zz_adv_probe_frozen_clock.py, which re-collects the frozen P01 / R54 functions unchanged) the ten nodes pass on the GREEN bytes. Needs an orchestrator ruling to amend the frozen RED (test-only, LC-2): build G10's (and R49's / P03's) created_at relative to the run clock (e.g. now - 3 d - 2 h, which keeps the golden's "3d ago" byte-identical) or freeze the formatter's clock inside _run_golden; then re-hash the RED file and keep the golden bytes.

## MAJOR
none.

## MINOR (documentation rulings / stated limits by LC-4)
- m1 (R-S10-8 coverage) the admin-key bypass is pinned on POST (P06) and the camera (test_gc6_admin_key_camera_bypasses_the_gate) only: mutants A02 (GET route's `not getattr(request.state, "paid_route_admin", False)` -> True) and A03 (the stream route's) SURVIVE the RED + gate rows. The code is correct on all four routes (read); GET /compare is the documented eval / probe route. One gate row each (admin key + a rule-1 query -> no 400, compare called without the kwarg) closes it.
- m2 (D3 unpinned; L3 wording) mutant A11 (D3 reverted: evidence proceeds before the no-chip resolver category) SURVIVES: no row pins GREEN's deviation D3. Measured: 'Gucci Dionysus' / 'Prada Galleria' explicit, A2b fashion: chip None -> refused fashion (1 A2b, the resolver's); chip fragrances -> proceed (0 A2b, GC-2). So the PR body L3 and the CLAUDE.md stated limit "a house-only non-fragrance pair is compared as a fragrance (GC-2)" hold only WITH a client chip; with no chip (every camera pair; text before S81-11) D3 refuses it. Reword L3 / the row and add one gate row.
- m3 (chip 'other' unpinned) mutant A12 (an 'other' chip treated as a real chip: a second A2b after the resolver's) SURVIVES. Measured correct today ('iPhone 15' / 'Galaxy S24', chip other, A2b electronics -> refused, exactly 1 A2b).
- m4 (a blind non-fragrance product beside a fragrance product proceeds on the explicit / vision path; not stated) per-product categories there are the name stubs (R-S10-6) and the lexicon's per-product hits are not consulted, while rule 1 scans the PAIR text (a form word in product A clears product B's 'bag' / 'watch'). Measured: 'Dior Sauvage EDT' / 'Apple iPhone 15 Pro' explicit, no chip: category_used fragrances, both fetches as fragrances, 0 A2b, 0 EVAL (compared and billed as a fragrance pair); post_resolve_refusal on 'Dior Sauvage EDT' / 'iPhone 15' -> proceed with or without a chip. The camera (a perfume + a phone / bag photo) is the likely path. Same class as GC-2 (no per-product classifier for a blind product) but L3 / L4 / GC-2 do not name it: state it, or rule a $0 per-product `scan([name]).non_fragrance` when the stub is 'other'.
- m5 (GC-1 x B1 cross-unit) the GC-1 rewrite changes category_used but not B1's per-product `product_categories` (captured after the gate block from the stubs). Measured: 'Kerastase Genesis Hair Mist' / 'Dior Sauvage EDT' -> category_used fragrances, product_categories ["haircare", "fragrances"]; result_gate.identity_coherence -> False -> reason category_conflict, i.e. with ENABLE_RESULT_STATUS_METADATA / ENABLE_RESULT_GATE ON (default OFF) a pair the gate made a fragrance pair is marked incoherent / abstained. State it or map the overridden product's entry to fragrances.
- m6 (stub collisions refuse genuine fragrances post-resolve) on the explicit / vision path a fragrance whose name carries a stub synonym is refused (refunded, counted): measured 'Clean Reserve Skin' ('skin' -> skincare) refused with chip None and with chip fragrances. L11 states only the $0 lexicon case; add the post-resolve stub case.
- m7 (q= path, no form override) R-S10-5 scopes the override to explicit / vision, so a q= hair-mist pair the parse labels haircare is refused post-consume (refunded). By ruling; not stated.
- m8 (coverage gaps, all SURVIVED, code correct by reading / probe): A14 retry_after ceil -> floor (R45 uses whole-second instants; probe: 21:00:00.5 -> 10800 with ceil); A17 vision_texts without the brand (the camera's house evidence unpinned: a brand-only house rescue like 'Jo Malone' + 'Peony & Blush Suede' would turn into a post-vision rule-1 refusal); A22 the camera budget exit's anon refund (unreachable with ENABLE_COMPARE_AUTH_REQUIRED ON); A29 the allow-list's case-insensitive match.
- m9 (prove-nothing assertions) test_gc1_form_override_compares_as_fragrances_sync's two asserts `CATEGORY_SPEC_SCHEMAS["fragrances"] != ...["haircare"]` and `CATEGORY_DIMENSIONS["fragrances"] != ...["haircare"]` are static facts true at any bytes; the row's substance is the fetch categories + the ctx (A05 / A13 kill it on those).
- m10 (category label) 'watch' is a fashion term and 'smartwatch' electronics, so "apple watch vs galaxy watch" is refused with category "fashion" (measured); a label-truth note for S81-11 if it renders copy by category.
- m11 (GC-5 reading, the gate's Q3) the same marked AR term twice is one term: measured "krim nivea vs krim dove" and "saa rolex vs saa omega" (Arabic) proceed past rule 1 to the post-resolve (consumed, then refunded) instead of a $0 refusal; two DIFFERENT terms refuse (krim + lushan -> skincare; krim + shampoo -> skincare, the first hit).

## Runs (every [pyt] line; one pytest at a time, foreground)
```
[pyt] tag=s10advc-red-off start=2026-11-02 13:00:04 end=2026-11-02 13:00:11 elapsed=7s bound=600s status=FAIL rc=1      (RED + gate rows, ambient OFF: 10 failed, 143 passed; the B1 ten)
  [hermeticity] sentinel checked 153 test(s) ; [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10advc-probe-frozen-off start=2026-11-02 13:01:39 end=2026-11-02 13:01:43 elapsed=4s bound=600s status=FAIL rc=2   (MY probe's collection error: it copied the RED module's __file__; fixed, not a result)
  [hermeticity] sentinel checked 0 test(s) ; [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10advc-probe-frozen-off2 start=2026-11-02 13:02:02 end=2026-11-02 13:02:06 elapsed=4s bound=600s status=OK rc=0     (P01 + R54 at the RED's record clock: 10 passed)
  [hermeticity] sentinel checked 10 test(s) ; [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10advc-red-on start=2026-11-02 13:02:14 end=2026-11-02 13:02:23 elapsed=8s bound=600s status=FAIL rc=1       (RED + gate rows + frozen probe, ambient ENABLE_FRAGRANCE_ONLY_GATE=true: 10 failed (the B1 ten), 153 passed)
  [hermeticity] sentinel checked 163 test(s) ; [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10advc-probe-sem start=2026-11-02 13:23:49 end=2026-11-02 13:23:52 elapsed=3s bound=600s status=OK rc=0       (semantics probe, records only: 5 passed)
  [hermeticity] sentinel checked 5 test(s) ; [netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s10advc-probe-gc1 start=2026-11-02 13:30:48 end=2026-11-02 13:30:52 elapsed=4s bound=600s status=OK rc=0       (GC-1 x B1 + mixed pair probe: 1 passed)
  [hermeticity] sentinel checked 1 test(s) ; [netguard] blocked 0 attempt(s) from 0 node(s)
```
RED + gate rows from the exact bytes, outside the ten time-bombed nodes: 130 RED-file nodes + 13 gate-row nodes green ambient OFF and ambient ON (153 = 130 + 13 + the 10 frozen-clock probe nodes in the ON run).

## Mutation table (76 runs on sha-verified byte copies in the scratch worktree; harness <scratchpad>/S81-10_adv/work/mut_harness.py; each run = the RED file + the gate rows + the frozen-clock probe with -k "not test_p01_flag_off_golden and not test_r54_off_calls_nothing_of_the_gate" (the B1 ten re-run as test_adv_p01_frozen / test_adv_r54_frozen); restore by shutil.copyfile + sha256 compare after every mutant; a full manifest of the 3,460 files (tracked + the probe) identical before and after; mutation lock created 13:06, removed after the last restore)
- the 43 spec / RED mutants (M01-M42 + M05b), re-cut against the GREEN code: 42 KILLED, each by its named row(s) (the first failing node is listed below); M26 SURVIVED = equivalent by ruling C7 (forwarding fragrance_gate=None to the impl); M22: my cut (the skip made unconditional) is killed by R26 / R30, the RED's direction (evidence never skips, M22b) by R26b; 0 INVALID, 0 NOT_APPLIED.
- 32 adversary extras (A01-A32: per-route bypass, GC-1 / GC-5 / GC-6, D3, the stream return, the camera exits, the handler validation, knob / reset edges): 24 KILLED, 8 SURVIVED (A02, A03, A11, A12, A14, A17, A22, A29 -> m1, m2, m3, m8).
```
id	file	verdict	failed	expected	check	first_failed
M01	app/api/text_routes.py	KILLED	5	test_r16	named-row-hit	test_r16_post_rule1_zero_cost
M02	app/services/structured_comparison_service.py	KILLED	9	test_r24	named-row-hit	test_r24_sync_post_resolve_refusal
M03	app/services/structured_comparison_service.py	KILLED	1	test_r25	named-row-hit	test_r25_stream_post_resolve_refusal
M04	app/api/text_routes.py	KILLED	5	test_r20	named-row-hit	test_r16_post_rule1_zero_cost
M05	app/services/category_gate.py	KILLED	5	test_r10	named-row-hit	test_r10_house_or_note_beside_a_category_word_defers[dior
M05b	app/services/category_gate.py	KILLED	3	test_r10,test_r13	named-row-hit	test_r10_house_or_note_beside_a_category_word_defers[dior
M06	app/services/category_gate.py	KILLED	1	test_r04	named-row-hit	test_r04_lexicon_reloads_without_restart
M07	app/services/category_gate.py	KILLED	1	test_r53	named-row-hit	test_r53_kb_seam_fails_open
M08	app/api/version_routes.py	KILLED	10	test_adv_p01_frozen,test_adv_r54_frozen	named-row-hit	test_adv_p01_frozen[0]
M09	app/services/category_gate.py	KILLED	2	test_r26,test_r28,test_r32	named-row-hit	test_r26_chip_is_not_trusted
M10	app/services/category_gate.py	KILLED	1	test_r24,test_r27	named-row-hit	test_r27_parser_other_proceeds[khamrah
M11	app/services/category_gate.py	KILLED	3	test_r43,test_r44	named-row-hit	test_r43_incr_script_static
M12	app/services/category_gate.py	KILLED	3	test_r43,test_r44	named-row-hit	test_r43_incr_script_static
M13	app/services/category_gate.py	KILLED	10	test_r21	named-row-hit	test_r20_budget_spent_never_billed[get-acct]
M14	app/services/category_gate.py	KILLED	14	test_r22,test_r52	named-row-hit	test_r19_rule2_proceeds_in_order
M15	app/middleware/error_handler.py	KILLED	5	test_p07	named-row-hit	test_p07_handler_flag_off_keeps_the_base_keys[0]
M16	app/middleware/error_handler.py	KILLED	1	test_r42	named-row-hit	test_r42_handler_sanitises
M17	app/api/home_routes.py	KILLED	6	test_r50	named-row-hit	test_r50_trending_filtered[bahrain]
M18	app/api/home_routes.py	KILLED	11	test_adv_p01_frozen,test_r49,test_adv_r54_frozen	named-row-hit	test_r49_smart_pick_filtered
M19	app/api/image_routes.py	KILLED	1	test_r38	named-row-hit	test_r38_camera_post_resolve_never_comparison_failed
M20	app/api/image_routes.py	KILLED	1	test_r37	named-row-hit	test_r37_camera_post_vision_rule1
M21	app/api/text_routes.py	KILLED	4	test_r16	named-row-hit	test_r16_post_rule1_zero_cost
M22	app/services/category_gate.py	KILLED	2	test_r26b	NAMED-ROW-MISSING	test_r26_chip_is_not_trusted
M23	app/services/category_gate.py	KILLED	1	test_r14,test_r08	named-row-hit	test_r14_arabic_normalisation
M24	app/services/category_gate.py	KILLED	2	test_r11	named-row-hit	test_r09_double_product_type_proceeds
M25	app/services/category_gate.py	KILLED	2	test_r02	named-row-hit	test_r02_budget_knob[1e3-100]
M26	app/services/structured_comparison_service.py	SURVIVED	0	-	n/a	
M27	app/api/text_routes.py	KILLED	2	test_r33	named-row-hit	test_r33_r34_route_refusal_refund_once[get-usage_refund.text.get]
M28	app/api/image_routes.py	KILLED	1	test_r36	named-row-hit	test_r36_camera_budget_spent
M29	app/services/structured_comparison_service.py	KILLED	4	test_r24	named-row-hit	test_r24_sync_post_resolve_refusal
M30	app/services/category_gate.py	KILLED	1	test_r15	named-row-hit	test_r15_case_separators_nfkc_and_accents
M31	app/services/category_gate.py	KILLED	3	test_r09,test_r11	named-row-hit	test_r09_double_product_type_proceeds
M32	app/api/image_routes.py	KILLED	1	test_r37	named-row-hit	test_r37_camera_post_vision_rule1
M33	app/services/category_gate.py	KILLED	8	test_r44,test_r24	named-row-hit	test_r24_sync_post_resolve_refusal
M34	app/services/structured_comparison_service.py	KILLED	6	test_p05	named-row-hit	test_p05_orchestrator_order_without_the_kwarg[on-pair-stream]
M35	app/api/home_routes.py	KILLED	16	test_adv_p01_frozen,test_r50,test_adv_r54_frozen	named-row-hit	test_r50_trending_filtered[bahrain]
M36	app/services/category_gate.py	KILLED	1	test_r32	named-row-hit	test_r32_mixed_pairs_refused_per_product
M37	app/services/category_gate.py	KILLED	7	test_r31	named-row-hit	test_r31_form_hit_overrides_the_name_detection[pair0]
M38	app/services/category_gate.py	KILLED	1	test_r26c	named-row-hit	test_r26c_no_chip_reuses_the_resolver_classifier
M39	app/services/category_gate.py	KILLED	1	test_r30	named-row-hit	test_r30_classifier_outage_proceeds_uncounted
M40	app/api/text_routes.py	KILLED	3	test_p06	named-row-hit	test_p06_admin_key_path_bypasses_the_gate
M41	app/services/category_gate.py	KILLED	2	test_r47,test_r48	named-row-hit	test_r47_budget_exempt_allow_list
M42	app/services/category_gate.py	KILLED	3	test_r20,test_r22	named-row-hit	test_r20_budget_spent_never_billed[get-dev]
A01	app/api/text_routes.py	KILLED	1	test_p06	named-row-hit	test_p06_admin_key_path_bypasses_the_gate
A02	app/api/text_routes.py	SURVIVED	0	-	n/a	
A03	app/api/text_routes.py	SURVIVED	0	-	n/a	
A04	app/api/image_routes.py	KILLED	1	-	n/a	test_gc6_admin_key_camera_bypasses_the_gate
A05	app/services/structured_comparison_service.py	KILLED	2	-	n/a	test_gc1_form_override_compares_as_fragrances_sync[pair0]
A06	app/services/structured_comparison_service.py	KILLED	2	-	n/a	test_gc1_form_override_compares_as_fragrances_stream[pair0]
A07	app/services/structured_comparison_service.py	KILLED	1	test_r25	named-row-hit	test_r25_stream_post_resolve_refusal
A08	app/services/category_gate.py	KILLED	1	-	n/a	test_gc5_marked_term_never_fires_rule1_alone
A09	app/services/category_gate.py	KILLED	2	-	n/a	test_gc5_marked_term_never_fires_rule1_alone
A10	app/services/category_gate.py	KILLED	1	-	n/a	test_gc1_override_helpers
A11	app/services/category_gate.py	SURVIVED	0	-	n/a	
A12	app/services/category_gate.py	SURVIVED	0	-	n/a	
A13	app/services/category_gate.py	KILLED	5	-	n/a	test_gc1_form_override_compares_as_fragrances_stream[pair0]
A14	app/services/category_gate.py	SURVIVED	0	test_r45	NAMED-ROW-MISSING	
A15	app/services/category_gate.py	KILLED	7	test_r44	named-row-hit	test_r24_sync_post_resolve_refusal
A16	app/services/category_gate.py	KILLED	1	-	n/a	test_gc5_marked_term_never_fires_rule1_alone
A17	app/services/category_gate.py	SURVIVED	0	-	n/a	
A18	app/services/category_gate.py	KILLED	19	test_r22	named-row-hit	test_r19_rule2_proceeds_in_order
A19	app/api/image_routes.py	KILLED	1	test_r40	named-row-hit	test_r40_camera_single_product_rule1
A20	app/api/image_routes.py	KILLED	1	test_r40	named-row-hit	test_r40_camera_single_product_rule1
A21	app/api/image_routes.py	KILLED	1	test_r40	named-row-hit	test_r40_camera_single_product_rule1
A22	app/api/image_routes.py	SURVIVED	0	-	n/a	
A23	app/api/image_routes.py	KILLED	1	test_r38	named-row-hit	test_r38_camera_post_resolve_never_comparison_failed
A24	app/middleware/error_handler.py	KILLED	1	test_r42	named-row-hit	test_r42_handler_sanitises
A25	app/middleware/error_handler.py	KILLED	1	test_r42	named-row-hit	test_r42_handler_sanitises
A26	app/middleware/error_handler.py	KILLED	1	test_r42	named-row-hit	test_r42_handler_sanitises
A27	app/api/home_routes.py	KILLED	6	test_r50	named-row-hit	test_r50_trending_filtered[bahrain]
A28	app/api/text_routes.py	KILLED	2	test_r33	named-row-hit	test_r33_r34_route_refusal_refund_once[get-usage_refund.text.get]
A29	app/services/category_gate.py	SURVIVED	0	test_r47	NAMED-ROW-MISSING	
A30	app/services/category_gate.py	KILLED	11	test_r48	named-row-hit	test_r20_budget_spent_never_billed[get-acct]
```
[pyt] lines (id verdict | summary | [pyt]):
```
M01 KILLED | 5 failed, 148 passed, 10 deselected, 11 warnings in 6.55s | [pyt] tag=s10advc-m01 start=2026-11-02 13:06:12 end=2026-11-02 13:06:19 elapsed=8s bound=600s status=FAIL rc=1
M02 KILLED | 9 failed, 144 passed, 10 deselected, 11 warnings in 7.06s | [pyt] tag=s10advc-m02 start=2026-11-02 13:06:20 end=2026-11-02 13:06:28 elapsed=8s bound=600s status=FAIL rc=1
M03 KILLED | 1 failed, 152 passed, 10 deselected, 11 warnings in 6.85s | [pyt] tag=s10advc-m03 start=2026-11-02 13:06:28 end=2026-11-02 13:06:36 elapsed=8s bound=600s status=FAIL rc=1
M04 KILLED | 5 failed, 148 passed, 10 deselected, 11 warnings in 7.11s | [pyt] tag=s10advc-m04 start=2026-11-02 13:06:36 end=2026-11-02 13:06:44 elapsed=8s bound=600s status=FAIL rc=1
M05 KILLED | 6 failed, 147 passed, 10 deselected, 11 warnings in 7.15s | [pyt] tag=s10advc-m05 start=2026-11-02 13:06:44 end=2026-11-02 13:06:52 elapsed=8s bound=600s status=FAIL rc=1
M05b KILLED | 4 failed, 149 passed, 10 deselected, 11 warnings in 6.77s | [pyt] tag=s10advc-m05b start=2026-11-02 13:06:53 end=2026-11-02 13:07:00 elapsed=8s bound=600s status=FAIL rc=1
M06 KILLED | 1 failed, 152 passed, 10 deselected, 11 warnings in 7.94s | [pyt] tag=s10advc-m06 start=2026-11-02 13:07:01 end=2026-11-02 13:07:10 elapsed=9s bound=600s status=FAIL rc=1
M07 KILLED | 1 failed, 152 passed, 10 deselected, 11 warnings in 12.94s | [pyt] tag=s10advc-m07 start=2026-11-02 13:07:10 end=2026-11-02 13:07:24 elapsed=14s bound=600s status=FAIL rc=1
M08 KILLED | 10 failed, 143 passed, 10 deselected, 11 warnings in 7.18s | [pyt] tag=s10advc-m08 start=2026-11-02 13:07:24 end=2026-11-02 13:07:32 elapsed=8s bound=600s status=FAIL rc=1
M09 KILLED | 2 failed, 151 passed, 10 deselected, 11 warnings in 7.96s | [pyt] tag=s10advc-m09 start=2026-11-02 13:07:32 end=2026-11-02 13:07:41 elapsed=9s bound=600s status=FAIL rc=1
M10 KILLED | 1 failed, 152 passed, 10 deselected, 11 warnings in 8.01s | [pyt] tag=s10advc-m10 start=2026-11-02 13:07:41 end=2026-11-02 13:07:50 elapsed=9s bound=600s status=FAIL rc=1
M11 KILLED | 3 failed, 150 passed, 10 deselected, 11 warnings in 11.70s | [pyt] tag=s10advc-m11 start=2026-11-02 13:07:51 end=2026-11-02 13:08:03 elapsed=13s bound=600s status=FAIL rc=1
M12 KILLED | 3 failed, 150 passed, 10 deselected, 11 warnings in 7.33s | [pyt] tag=s10advc-m12 start=2026-11-02 13:08:04 end=2026-11-02 13:08:12 elapsed=8s bound=600s status=FAIL rc=1
M13 KILLED | 10 failed, 143 passed, 10 deselected, 11 warnings in 7.00s | [pyt] tag=s10advc-m13 start=2026-11-02 13:08:12 end=2026-11-02 13:08:20 elapsed=8s bound=600s status=FAIL rc=1
M14 KILLED | 14 failed, 139 passed, 10 deselected, 11 warnings in 7.25s | [pyt] tag=s10advc-m14 start=2026-11-02 13:08:20 end=2026-11-02 13:08:29 elapsed=9s bound=600s status=FAIL rc=1
M15 KILLED | 5 failed, 148 passed, 10 deselected, 11 warnings in 6.71s | [pyt] tag=s10advc-m15 start=2026-11-02 13:08:30 end=2026-11-02 13:08:37 elapsed=8s bound=600s status=FAIL rc=1
M16 KILLED | 1 failed, 152 passed, 10 deselected, 11 warnings in 6.34s | [pyt] tag=s10advc-m16 start=2026-11-02 13:08:38 end=2026-11-02 13:08:45 elapsed=7s bound=600s status=FAIL rc=1
M17 KILLED | 6 failed, 147 passed, 10 deselected, 11 warnings in 6.68s | [pyt] tag=s10advc-m17 start=2026-11-02 13:08:45 end=2026-11-02 13:08:53 elapsed=8s bound=600s status=FAIL rc=1
M18 KILLED | 11 failed, 142 passed, 10 deselected, 11 warnings in 7.25s | [pyt] tag=s10advc-m18 start=2026-11-02 13:08:53 end=2026-11-02 13:09:02 elapsed=9s bound=600s status=FAIL rc=1
M19 KILLED | 1 failed, 152 passed, 10 deselected, 11 warnings in 6.58s | [pyt] tag=s10advc-m19 start=2026-11-02 13:09:02 end=2026-11-02 13:09:10 elapsed=8s bound=600s status=FAIL rc=1
M20 KILLED | 1 failed, 152 passed, 10 deselected, 11 warnings in 6.60s | [pyt] tag=s10advc-m20 start=2026-11-02 13:09:10 end=2026-11-02 13:09:18 elapsed=8s bound=600s status=FAIL rc=1
M21 KILLED | 4 failed, 149 passed, 10 deselected, 11 warnings in 6.61s | [pyt] tag=s10advc-m21 start=2026-11-02 13:09:18 end=2026-11-02 13:09:25 elapsed=8s bound=600s status=FAIL rc=1
M22 KILLED | 2 failed, 151 passed, 10 deselected, 11 warnings in 7.98s | [pyt] tag=s10advc-m22 start=2026-11-02 13:09:26 end=2026-11-02 13:09:36 elapsed=10s bound=600s status=FAIL rc=1
M23 KILLED | 1 failed, 152 passed, 10 deselected, 11 warnings in 6.63s | [pyt] tag=s10advc-m23 start=2026-11-02 13:09:36 end=2026-11-02 13:09:44 elapsed=8s bound=600s status=FAIL rc=1
M24 KILLED | 2 failed, 151 passed, 10 deselected, 11 warnings in 6.29s | [pyt] tag=s10advc-m24 start=2026-11-02 13:09:44 end=2026-11-02 13:09:51 elapsed=7s bound=600s status=FAIL rc=1
M25 KILLED | 2 failed, 151 passed, 10 deselected, 11 warnings in 6.67s | [pyt] tag=s10advc-m25 start=2026-11-02 13:09:51 end=2026-11-02 13:09:59 elapsed=8s bound=600s status=FAIL rc=1
M26 SURVIVED | 153 passed, 10 deselected, 11 warnings in 7.24s | [pyt] tag=s10advc-m26 start=2026-11-02 13:09:59 end=2026-11-02 13:10:07 elapsed=8s bound=600s status=OK rc=0
M27 KILLED | 2 failed, 151 passed, 10 deselected, 11 warnings in 6.39s | [pyt] tag=s10advc-m27 start=2026-11-02 13:10:07 end=2026-11-02 13:10:15 elapsed=7s bound=600s status=FAIL rc=1
M28 KILLED | 1 failed, 152 passed, 10 deselected, 11 warnings in 8.06s | [pyt] tag=s10advc-m28 start=2026-11-02 13:10:15 end=2026-11-02 13:10:24 elapsed=9s bound=600s status=FAIL rc=1
M29 KILLED | 4 failed, 149 passed, 10 deselected, 17 warnings in 7.84s | [pyt] tag=s10advc-m29 start=2026-11-02 13:10:24 end=2026-11-02 13:10:33 elapsed=9s bound=600s status=FAIL rc=1
M30 KILLED | 1 failed, 152 passed, 10 deselected, 11 warnings in 8.85s | [pyt] tag=s10advc-m30 start=2026-11-02 13:10:33 end=2026-11-02 13:10:43 elapsed=10s bound=600s status=FAIL rc=1
M31 KILLED | 3 failed, 150 passed, 10 deselected, 11 warnings in 7.60s | [pyt] tag=s10advc-m31 start=2026-11-02 13:10:43 end=2026-11-02 13:10:52 elapsed=9s bound=600s status=FAIL rc=1
M32 KILLED | 1 failed, 152 passed, 10 deselected, 11 warnings in 6.84s | [pyt] tag=s10advc-m32 start=2026-11-02 13:10:52 end=2026-11-02 13:11:00 elapsed=8s bound=600s status=FAIL rc=1
M33 KILLED | 8 failed, 145 passed, 10 deselected, 11 warnings in 9.10s | [pyt] tag=s10advc-m33 start=2026-11-02 13:11:00 end=2026-11-02 13:11:10 elapsed=10s bound=600s status=FAIL rc=1
M34 KILLED | 6 failed, 147 passed, 10 deselected, 11 warnings in 7.40s | [pyt] tag=s10advc-m34 start=2026-11-02 13:11:10 end=2026-11-02 13:11:19 elapsed=8s bound=600s status=FAIL rc=1
M35 KILLED | 16 failed, 137 passed, 10 deselected, 11 warnings in 8.81s | [pyt] tag=s10advc-m35 start=2026-11-02 13:11:19 end=2026-11-02 13:11:29 elapsed=10s bound=600s status=FAIL rc=1
M36 KILLED | 1 failed, 152 passed, 10 deselected, 11 warnings in 14.74s | [pyt] tag=s10advc-m36 start=2026-11-02 13:11:29 end=2026-11-02 13:11:46 elapsed=17s bound=600s status=FAIL rc=1
M37 KILLED | 7 failed, 146 passed, 10 deselected, 11 warnings in 6.60s | [pyt] tag=s10advc-m37 start=2026-11-02 13:11:46 end=2026-11-02 13:11:54 elapsed=8s bound=600s status=FAIL rc=1
M38 KILLED | 1 failed, 152 passed, 10 deselected, 11 warnings in 6.73s | [pyt] tag=s10advc-m38 start=2026-11-02 13:11:54 end=2026-11-02 13:12:02 elapsed=8s bound=600s status=FAIL rc=1
M39 KILLED | 1 failed, 152 passed, 10 deselected, 11 warnings in 6.80s | [pyt] tag=s10advc-m39 start=2026-11-02 13:12:02 end=2026-11-02 13:12:10 elapsed=8s bound=600s status=FAIL rc=1
M40 KILLED | 3 failed, 150 passed, 10 deselected, 11 warnings in 7.12s | [pyt] tag=s10advc-m40 start=2026-11-02 13:12:10 end=2026-11-02 13:12:18 elapsed=8s bound=600s status=FAIL rc=1
M41 KILLED | 2 failed, 151 passed, 10 deselected, 11 warnings in 6.50s | [pyt] tag=s10advc-m41 start=2026-11-02 13:12:18 end=2026-11-02 13:12:26 elapsed=7s bound=600s status=FAIL rc=1
M42 KILLED | 3 failed, 150 passed, 10 deselected, 11 warnings in 6.97s | [pyt] tag=s10advc-m42 start=2026-11-02 13:12:26 end=2026-11-02 13:12:34 elapsed=8s bound=600s status=FAIL rc=1
A01 KILLED | 1 failed, 152 passed, 10 deselected, 11 warnings in 6.09s | [pyt] tag=s10advc-a01 start=2026-11-02 13:12:43 end=2026-11-02 13:12:50 elapsed=7s bound=600s status=FAIL rc=1
A02 SURVIVED | 153 passed, 10 deselected, 11 warnings in 6.96s | [pyt] tag=s10advc-a02 start=2026-11-02 13:12:50 end=2026-11-02 13:12:58 elapsed=8s bound=600s status=OK rc=0
A03 SURVIVED | 153 passed, 10 deselected, 11 warnings in 6.73s | [pyt] tag=s10advc-a03 start=2026-11-02 13:12:58 end=2026-11-02 13:13:06 elapsed=8s bound=600s status=OK rc=0
A04 KILLED | 1 failed, 152 passed, 10 deselected, 11 warnings in 6.27s | [pyt] tag=s10advc-a04 start=2026-11-02 13:13:06 end=2026-11-02 13:13:13 elapsed=7s bound=600s status=FAIL rc=1
A05 KILLED | 2 failed, 151 passed, 10 deselected, 11 warnings in 6.26s | [pyt] tag=s10advc-a05 start=2026-11-02 13:13:14 end=2026-11-02 13:13:21 elapsed=7s bound=600s status=FAIL rc=1
A06 KILLED | 2 failed, 151 passed, 10 deselected, 11 warnings in 6.20s | [pyt] tag=s10advc-a06 start=2026-11-02 13:13:21 end=2026-11-02 13:13:28 elapsed=7s bound=600s status=FAIL rc=1
A07 KILLED | 1 failed, 152 passed, 10 deselected, 11 warnings in 6.49s | [pyt] tag=s10advc-a07 start=2026-11-02 13:13:28 end=2026-11-02 13:13:36 elapsed=7s bound=600s status=FAIL rc=1
A08 KILLED | 1 failed, 152 passed, 10 deselected, 11 warnings in 6.08s | [pyt] tag=s10advc-a08 start=2026-11-02 13:13:36 end=2026-11-02 13:13:43 elapsed=7s bound=600s status=FAIL rc=1
A09 KILLED | 2 failed, 151 passed, 10 deselected, 11 warnings in 7.37s | [pyt] tag=s10advc-a09 start=2026-11-02 13:13:43 end=2026-11-02 13:13:51 elapsed=8s bound=600s status=FAIL rc=1
A10 KILLED | 1 failed, 152 passed, 10 deselected, 11 warnings in 6.23s | [pyt] tag=s10advc-a10 start=2026-11-02 13:13:52 end=2026-11-02 13:13:59 elapsed=7s bound=600s status=FAIL rc=1
A11 SURVIVED | 153 passed, 10 deselected, 11 warnings in 5.64s | [pyt] tag=s10advc-a11 start=2026-11-02 13:13:59 end=2026-11-02 13:14:05 elapsed=7s bound=600s status=OK rc=0
A12 SURVIVED | 153 passed, 10 deselected, 11 warnings in 5.69s | [pyt] tag=s10advc-a12 start=2026-11-02 13:14:06 end=2026-11-02 13:14:12 elapsed=7s bound=600s status=OK rc=0
A13 KILLED | 5 failed, 148 passed, 10 deselected, 11 warnings in 6.17s | [pyt] tag=s10advc-a13 start=2026-11-02 13:14:12 end=2026-11-02 13:14:19 elapsed=7s bound=600s status=FAIL rc=1
A14 SURVIVED | 153 passed, 10 deselected, 11 warnings in 5.86s | [pyt] tag=s10advc-a14 start=2026-11-02 13:14:20 end=2026-11-02 13:14:26 elapsed=7s bound=600s status=OK rc=0
A15 KILLED | 7 failed, 146 passed, 10 deselected, 11 warnings in 6.66s | [pyt] tag=s10advc-a15 start=2026-11-02 13:14:27 end=2026-11-02 13:14:34 elapsed=8s bound=600s status=FAIL rc=1
A16 KILLED | 1 failed, 152 passed, 10 deselected, 11 warnings in 6.55s | [pyt] tag=s10advc-a16 start=2026-11-02 13:14:34 end=2026-11-02 13:14:42 elapsed=7s bound=600s status=FAIL rc=1
A17 SURVIVED | 153 passed, 10 deselected, 11 warnings in 5.70s | [pyt] tag=s10advc-a17 start=2026-11-02 13:14:42 end=2026-11-02 13:14:49 elapsed=7s bound=600s status=OK rc=0
A18 KILLED | 19 failed, 134 passed, 10 deselected, 11 warnings in 7.78s | [pyt] tag=s10advc-a18 start=2026-11-02 13:14:49 end=2026-11-02 13:14:57 elapsed=9s bound=600s status=FAIL rc=1
A19 KILLED | 1 failed, 152 passed, 10 deselected, 11 warnings in 6.21s | [pyt] tag=s10advc-a19 start=2026-11-02 13:14:58 end=2026-11-02 13:15:05 elapsed=7s bound=600s status=FAIL rc=1
A20 KILLED | 1 failed, 152 passed, 10 deselected, 11 warnings in 6.48s | [pyt] tag=s10advc-a20 start=2026-11-02 13:15:05 end=2026-11-02 13:15:12 elapsed=7s bound=600s status=FAIL rc=1
A21 KILLED | 1 failed, 152 passed, 10 deselected, 11 warnings in 6.36s | [pyt] tag=s10advc-a21 start=2026-11-02 13:15:13 end=2026-11-02 13:15:20 elapsed=7s bound=600s status=FAIL rc=1
A22 SURVIVED | 153 passed, 10 deselected, 11 warnings in 5.79s | [pyt] tag=s10advc-a22 start=2026-11-02 13:15:20 end=2026-11-02 13:15:27 elapsed=7s bound=600s status=OK rc=0
A23 KILLED | 1 failed, 152 passed, 10 deselected, 11 warnings in 6.27s | [pyt] tag=s10advc-a23 start=2026-11-02 13:15:27 end=2026-11-02 13:15:34 elapsed=7s bound=600s status=FAIL rc=1
A24 KILLED | 1 failed, 152 passed, 10 deselected, 11 warnings in 6.29s | [pyt] tag=s10advc-a24 start=2026-11-02 13:15:34 end=2026-11-02 13:15:41 elapsed=7s bound=600s status=FAIL rc=1
A25 KILLED | 1 failed, 152 passed, 10 deselected, 11 warnings in 6.18s | [pyt] tag=s10advc-a25 start=2026-11-02 13:15:42 end=2026-11-02 13:15:49 elapsed=7s bound=600s status=FAIL rc=1
A26 KILLED | 1 failed, 152 passed, 10 deselected, 11 warnings in 7.53s | [pyt] tag=s10advc-a26 start=2026-11-02 13:15:49 end=2026-11-02 13:15:57 elapsed=8s bound=600s status=FAIL rc=1
A27 KILLED | 6 failed, 147 passed, 10 deselected, 11 warnings in 6.82s | [pyt] tag=s10advc-a27 start=2026-11-02 13:15:57 end=2026-11-02 13:16:05 elapsed=8s bound=600s status=FAIL rc=1
A28 KILLED | 2 failed, 151 passed, 10 deselected, 11 warnings in 7.00s | [pyt] tag=s10advc-a28 start=2026-11-02 13:16:05 end=2026-11-02 13:16:13 elapsed=8s bound=600s status=FAIL rc=1
A29 SURVIVED | 153 passed, 10 deselected, 11 warnings in 5.57s | [pyt] tag=s10advc-a29 start=2026-11-02 13:16:13 end=2026-11-02 13:16:20 elapsed=6s bound=600s status=OK rc=0
A30 KILLED | 11 failed, 142 passed, 10 deselected, 11 warnings in 6.83s | [pyt] tag=s10advc-a30 start=2026-11-02 13:16:20 end=2026-11-02 13:16:28 elapsed=8s bound=600s status=FAIL rc=1
M22b KILLED | 1 failed, 152 passed, 10 deselected, 11 warnings in 6.09s | [pyt] tag=s10advc-m22b start=2026-11-02 13:33:06 end=2026-11-02 13:33:13 elapsed=7s bound=600s status=FAIL rc=1
A31 KILLED | 4 failed, 149 passed, 10 deselected, 11 warnings in 6.50s | [pyt] tag=s10advc-a31 start=2026-11-02 13:33:41 end=2026-11-02 13:33:49 elapsed=8s bound=600s status=FAIL rc=1
A32 KILLED | 4 failed, 149 passed, 10 deselected, 11 warnings in 6.67s | [pyt] tag=s10advc-a32 start=2026-11-02 13:33:49 end=2026-11-02 13:33:56 elapsed=8s bound=600s status=FAIL rc=1
```

## Runtime truth of the GREEN report / PR body / CLAUDE.md row (probed on the GREEN bytes)
- flag-OFF identity: HOLDS (P01 + R54 green at the record clock; by reading: every route reads the flag first and passes no kwarg OFF; scs keys on the kwarg; home / version / handler read the flag; the admin marker is set in both flag states but reaches no body or log). The golden itself is time-bombed (B1).
- rule 1 (production lexicon, 61 EN + AR queries probed): every refusal and proceed matched the documented semantics: house / note beside a type word defers (dior lipstick, gucci bag, jo malone ... blush); a single note too (rose lipstick: notes 1 -> no $0 refusal, R-S10-4 as ruled); concentration / form words clear the pair; NFKC (full-width EDP), Latin accents (Hermes / Chloe), hyphens, apostrophes (Penhaligon's), Arabic harakat, tatweel, hamza folds, the articles al / wal / bal, Arabic-Indic digits all normalise as claimed; the three marks behave as D1 says; L11's false refusal is real ("peony & blush suede vs wood sage & sea salt" -> refused makeup at $0; stated).
- the refusal budget: ONE MGET (upstash-redis 1.7.0 mget(*keys), redis 8.1.0 mget(keys, *args) measured on the venv: D5 TRUE); ONE EVAL through llm_spend_breaker._eval (module-sniffed client shape); EXPIREAT next reset + 3600; fail-open on no client / raising read / bad reply; exemption read only when spent (_get_user_tier_info(user_id) signature matches); knob probe: unset/''/0.5/-5/nan/inf/1e309/abc -> 10, ' 7 ' -> 7, '10.9' -> 10, 250 / 1e3 -> 100, 1 -> 1; retry_fields ceil + clamp 1..86400 (23:59:59.9 -> 1, 00:00 -> 86400); keys acct then dev; repr hides both ids.
- error-handler mapping (probed with real HTTPException details, four flag spellings): ON keeps category (canonical only), categories_live (all canonical, non-empty), scope (only refusal_daily), resets_at (str), and retry_after_seconds + Retry-After through W1-9 (no upper bound there); hostile values dropped; OFF only the base keys (a budget detail still gets W1-9's retry_after_seconds, base behaviour); an unhashable code is BAD_REQUEST in both states.
- billing R-A3: the $0 rule-1 and the budget 429 precede the preferences read and every consume on POST / GET / stream (M01 / M04 / M21 / A31 / A32 killed) and the camera budget precedes its consume and the vision call (M28); post-consume refusals refund through the existing arms exactly once (R33/R34, P08, R37-R40; M20 / M27 / M32 / A19-A23 killed) and count once (orchestrator EVAL; the camera arm does not re-count).
- contract freeze (PLAN section 0): OFF byte-identical; ON only additive keys / a new code; GC-1 changes values (category_used / category_switched / original_category), never keys or types.
- PR body: 22,976 bytes (<= 25,600); the [NATIVE READ] table equals the lexicon's 43 Arabic terms and 3 marks exactly (programmatic compare, in order); bytes > 127 in category_gate.py / the lexicon / the gate rows / the RED files = 0 at HEAD, CLAUDE.md 3,937 at base and HEAD.
- the compare entry callers: image, text POST / GET / stream are gated; /text/quick is admin-only; url_routes is S81-10b (stated).

## Prove-nothing / non-discriminating rows
- test_p01_flag_off_golden x5 and test_r54_off_calls_nothing_of_the_gate x5: fail on ANY bytes since 2026-11-02T10:00Z (B1), so at present they discriminate nothing.
- test_gc1_form_override_compares_as_fragrances_sync: two static asserts (m9).
- test_r45_reset_fields: whole-second instants only, ceil vs floor indistinguishable (A14).
- test_r47_budget_exempt_allow_list: lower-case ids only (A29).
- no RED / gate row pins the GET / stream admin bypass (A02 / A03), D3 (A11), the 'other' chip (A12), the camera's brand in vision_texts (A17), the camera budget exit's anon refund (A22).

## NOT MEASURED (by this lens)
- the comm set, the CI-order set, the hook files, the client fences, ruff / py_compile (the engineering / quota lenses; GREEN's records not re-run here).
- a live Upstash MGET / EVAL (no Lua runtime; the fakes emulate the script).
- the S81-09 seams against the merged S81-09 helpers (the rebase).

## Files written (notes folder only; never the GREEN worktree)
- <scratchpad>/S81-10_adv/correctness_REPORT.md (this file), notes.md, work/ (mut_harness.py, extra2.py, dry.py, manifest.py, manifest_before.tsv = manifest_after.tsv, mutation_table.tsv, mut_pyt_lines.txt, probe_semantics.json, probe_gc1.json, synonyms.json), logs/, mutA..mutD/ (per-mutant logs + mut_results.json), probes/ (the three probe test files, copies; they lived only in the removed scratch worktree)
