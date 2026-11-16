# INC-P2 PRICE-NOT-LOST - RED REPORT B (the second RED agent, Opus 5.5, 2026-11-16)

Status: RED round done in my scratch only. The real worktree sc-inc-p2 was never written by me; it holds Agent A's two test files (read only here for the diff). Rulings applied: RULINGS_INC_P2.md P2R-1..P2R-22 (sha256 17ad8c76..., section G included), the brief's ADDENDA 1-2, the review's corrections. Base b0ad260363e0cf0074e4ee596b140d073466e92a. No commit, no push, no PR. Proof standard (H6): nothing here proves a production fix; the proof is the owner's phone after the relay's flip.

## 1. Files (mine, untracked, outside the repo)
- red/test_inc_p2_price_not_lost.py  sha256 43cec7b7f10711b84323867ea96720715aa426bd91b3620469b5ddeab496af23  bytes 64103  >127: 0  CR: 0
- red/test_inc_p2_seam.py  sha256 0f3831dad167792c76ad931eb469686514646170098615eb54113ac13a875437  bytes 39016  >127: 0  CR: 0
- prototype helpers (thrown away): red/proto_ps_block.py, red/proto_apply.py; mutants red/mutants.py, driver red/mutdrive.py, results red/bmut_results.json, per-mutant junit red/bmut/*.xml
- comm list red/comm_list.txt (738 files, sha256 94b5fbf18f29a1e340701e9f4e9238dd061045b9599929c74d9c3de9da545fa6), chunks red/chunk_01..30.txt, reasons red/b_comm_reasons.tsv, failed ids red/b_base_comm_failed.txt

## 2. Base runs DEFERRED TO RED by the spec (1.10 B-1, B-2, B-4), alone, through gate.py
    [gate] tag=inc-p2-base-direct waited=110s (another lane's run is live)
    [pyt] tag=inc-p2-base-direct start=2026-11-16 20:43:01 end=2026-11-16 20:43:19 elapsed=18s bound=1200s status=OK rc=0
    [pyt] tag=inc-p2-base-direct start=2026-11-16 20:43:01 end=2026-11-16 20:43:19 elapsed=18s bound=1200s status=OK rc=0
    [gate] tag=inc-p2-base-ident waited=69s (another lane is queued, another lane's run is live)
    [pyt] tag=inc-p2-base-ident start=2026-11-16 20:44:29 end=2026-11-16 20:45:05 elapsed=36s bound=1200s status=OK rc=0
    [pyt] tag=inc-p2-base-ident start=2026-11-16 20:44:29 end=2026-11-16 20:45:05 elapsed=36s bound=1200s status=OK rc=0
    [gate] tag=inc-p2-base-logcount waited=26s (another lane is queued)
    [pyt] tag=inc-p2-base-logcount start=2026-11-16 20:45:33 end=2026-11-16 20:45:49 elapsed=16s bound=600s status=OK rc=0
    [pyt] tag=inc-p2-base-logcount start=2026-11-16 20:45:33 end=2026-11-16 20:45:49 elapsed=16s bound=600s status=OK rc=0
B-1 414 passed; B-2 and B-4 status OK (no failure). B-4 (R-13 / spec 4.1 O8): no log-count test counts the new lines at the base: no E1. B-5 (client jest fences) NOT RUN: no jest in this round (no junction in my scratch; the fences read no literal this unit moves).

## 3. The unit files at the base (scratch worktree INC-P2_scratch at the base bytes + my two files)
    [gate] tag=inc-p2-b-base waited=53s (another lane is queued, another lane took the slot)
    [pyt] tag=inc-p2-b-base start=2026-11-16 21:15:51 end=2026-11-16 21:16:01 elapsed=10s bound=600s status=FAIL rc=1
    [pyt] tag=inc-p2-b-base start=2026-11-16 21:15:51 end=2026-11-16 21:16:01 elapsed=10s bound=600s status=FAIL rc=1
    [pyt] tag=inc-p2-b-base2 start=2026-11-16 22:10:21 end=2026-11-16 22:10:32 elapsed=11s bound=600s status=FAIL rc=1
    [pyt] tag=inc-p2-b-base2 start=2026-11-16 22:10:21 end=2026-11-16 22:10:32 elapsed=11s bound=600s status=FAIL rc=1
Final file set (inc-p2-b-base2): 172 failed, 76 passed (248 nodes). First run (inc-p2-b-base, before the five gap rows): 164 failed, 72 passed. Every failure is an AssertionError (junit read: 0 non-assertion failures, 0 errors). The 72 passes are exactly the PIN rows / PIN cells (A08, A11[fix1], A13[fix1], A14, A16, A22, A24, A25, A29, A33 PIN, A34 x12, F1 x3, F3 x2, G2, H4 x2, B07 x2, B11, B17 x24, B22[None], R03, A48 x4).

## 4. Prototype (scratch worktree INC-P2_proto = base + red/proto_apply.py; thrown away)
    [gate] tag=inc-p2-b-proto-on waited=47s (another lane is queued)
    [pyt] tag=inc-p2-b-proto-on start=2026-11-16 21:13:25 end=2026-11-16 21:13:33 elapsed=7s bound=600s status=OK rc=0
    [pyt] tag=inc-p2-b-proto-on start=2026-11-16 21:13:25 end=2026-11-16 21:13:33 elapsed=7s bound=600s status=OK rc=0
    [pyt] tag=inc-p2-b-proto-off start=2026-11-16 21:14:11 end=2026-11-16 21:14:16 elapsed=6s bound=600s status=OK rc=0
    [pyt] tag=inc-p2-b-proto-off start=2026-11-16 21:14:11 end=2026-11-16 21:14:16 elapsed=6s bound=600s status=OK rc=0
    [pyt] tag=inc-p2-b-proto-on2 start=2026-11-16 22:10:39 end=2026-11-16 22:10:45 elapsed=6s bound=600s status=OK rc=0
    [pyt] tag=inc-p2-b-proto-on2 start=2026-11-16 22:10:39 end=2026-11-16 22:10:45 elapsed=6s bound=600s status=OK rc=0
    [pyt] tag=inc-p2-b-proto-off2 start=2026-11-16 22:10:51 end=2026-11-16 22:10:57 elapsed=6s bound=600s status=OK rc=0
    [pyt] tag=inc-p2-b-proto-off2 start=2026-11-16 22:10:51 end=2026-11-16 22:10:57 elapsed=6s bound=600s status=OK rc=0
ON (ENABLE_PRICE_NOT_LOST=true in the runner env; every row still sets its own flags): 236 passed, then 248 passed with the gap rows. OFF: 236 passed, then 248 passed. Flag-OFF byte identity: A34 (12 cells) and B17 (24 cells: rest + stream, 3 pairs, fix0/fix1, token absent/present) equal the base digests recorded from the base bytes.

Prototype design the rows pin (the contract GREEN builds to; everything else is free): PS price_not_lost_enabled, typed_size_ml, listing_size_ml, is_auction_marketplace_seller, p2_filter_marketplace_rows, price_cache_refusal_reason (log-only), client_price_size(request) (the token reader, flag read first, never ENABLE_KB_FIRST_SERVE), price_size_cap_bind / price_size_cap (the request ContextVar), price_trace_bind / price_trace_product / price_trace_note / price_miss_note / price_miss_summary (the miss ledger), p2_wire_price (B18 patches it), private product keys _p2_shown_price / _p2_reselected; SCS compare_from_text(..., price_size_cap=False) and compare_from_text_streaming(..., price_size_cap=False) binding the capability for the request (outer context, so the timeout partial sees it), SCS._p2_park_reseller(full_name, shop_best, shop_results, currency) called right after `shopify_fallback = shop_best`; TR passes price_size_cap=True at the GET, POST and stream compare calls when client_price_size(request). Wire: cap present -> the held side's found price with size_ml / per_ml; cap absent -> flag OFF's pending dict + price.offsize_listing {amount, currency, size_ml, per_ml, retailer, url, title[:120], source_method}. PRICE_OUTCOME fields: slot product shown amount currency size_ml method retailer marketplace origin race race_ms reconcile pend_reason display_rule miss miss_host miss_status miss_rule fam rejected cache_write cap (+ host); values carry no spaces (product and retailer have spaces folded to '_').

## 5. AMENDED ROWS (row | added / rewritten / dropped | ruling). [G] = a section G capability cell (cap1 token present / cap0 token absent).
| row | change | ruling |
|---|---|---|
| A04 / A05 | rewritten: x fix0/fix1 x res0/res1 x [G] cap1/cap0; cap0 asserts flag OFF's dict + offsize_listing | P2R-8, P2R-18/19/21, C-3 |
| A06, A07, A09, A10, A12, A13, A15, A17-A19 | rewritten: fix cell named; A07/A09/A10/A15/A18/A19 x [G] cap cells | P2R-8, P2R-21, C-3 |
| A08 | rewritten: PIN; a typed side's off-size listing stays pending (C1 not_exact) in both [G] cells, no 50 ml amount, no offsize_listing | P2R-3 |
| A11 | rewritten: fix0 cell RED, fix1 cell PIN | P2R-8, R-7 |
| A13 | rewritten: fix0 RED, fix1 PIN (today already picks 100) | measured |
| A14, A16, A22 | rewritten: PIN with both flag values; A22 in both [G] cells | B1 rule, P2R-20 |
| A20, A21 | rewritten: marker / stamp read with the [G] token present | P2R-22 field names |
| A31, A32 | rewritten: the P2R-11 / P2R-7 / P2R-21 field list (slot ... cap), product cut to 60, no personal field | P2R-7, P2R-11, P2-19 |
| A33 | rewritten: PIN half on should_cache_price (exact gate ON and OFF) + RED half on the log-only reason | P2R-4 |
| A34 | rewritten: x fix cells x [G] token present/absent with the flag OFF; base digests recorded (base64) | P2-19, P2R-21 |
| A35 | added: typed 30 with a size-less listing vs 100 (limited_data) x fix x [G] | P2R-2 |
| A36 | added: '50ml / 100ml' vs 100 (limited_data) x [G] | P2R-2 |
| A37 | added: p2_filter_marketplace_rows gated (same object flag OFF) | C-5 a |
| A38 | added: PRICE_OUTCOME cap=price_size|none, reconcile=both_shown|offsize_held x [G] | P2R-21 |
| A39, A40, A41 | added: raising logger at PRICE_OUTCOME, raising field builder, raising trace note | P2R-10, C-6 |
| A17b | added: the projected dict keeps the size annotation byte for byte | mutant M12 gap |
| A42 | added: a KB-served side is never marked for the cache write | P2R-5 (spec M31) |
| A43 | added: offsize_listing title cut to 120 | P2R-19 |
| A44 | added: PRICE_OUTCOME marketplace=1 and the seller name | P2R-7 |
| F1 | added: PIN proving a 10 ml travel spray at 8 / 10 / 12 BHD passes the plausibility floor at the base | P2R-12 |
| F2, F4 | added: the floor re-selects or pends (pending_genuine), never shown, never an offsize_listing; floor words travel / miniature / mini / atomiser / atomizer x [G] | P2R-12, P2R-20 |
| F3 | added: PIN, a typed 10ml keeps its 10 ml price | P2R-12 |
| H1-H3 | added: the header reader (absent, other tokens, ' Price_Size ', a list, upper, too long), flag OFF reads no header, KB flag irrelevant, the ContextVar scope | P2R-18, P2R-21 |
| H4 | added: PIN, flag OFF with the token present = today | P2R-21 |
| L1-L5 | added: the miss ledger (closest-to-success order, host / status / rule / family / two titles cut to 60, unbound no-op, survives a cancel, Shopping numbers_match recorded, floor rule on PRICE_OUTCOME) | P2R-11, P2-20 |
| G1 / G2 | added: Rasasi Hawas gender row under the flag (RED) / flag OFF unchanged (PIN) | P2R-13 |
| B01, B02, B14 | rewritten: x [G] cells; B14 = 16 ON cells (2 pairs x fix x res x [G]) + the exact-gate-OFF cell | P2R-21 |
| B03 | rewritten: the partial built after the full build on the same dicts, both [G] cells; also prints PRICE_OUTCOME (hard-cap partial) | X1-R1, P2R-11 |
| B04 / B05 | rewritten: one row x res0/res1; the write carries _seen_at; run 2 reads it from L1 and logs PRICE_CACHE_HIT | P2R-5, P2R-6 |
| B06 | rewritten: url-less re-selection -> PRICE_CACHE_SKIP reason=no_url; a converted re-selection reads the key and never overwrites a genuine entry | P2R-4, P2R-5, C-10 |
| B08 | rewritten: age_s=120 and age_s=unknown | C-2 |
| B09-B11b | rewritten: through SCS._p2_park_reseller + a source read of the call site; B10 adds the listing-URL park replacement | P2R-9 |
| B12 | rewritten: source read that the adapter converted park passes p2_filter_marketplace_rows (predicate in A37) | C-5 a |
| B13 | dropped (folded into B12 + A28 + A30): the 23:04 shape needs the real Tier-1 / adapter path; its two seams are those rows | C-5 a |
| B14 KB cell | dropped: a KB-served pipeline cell needs the S81-18 harness; covered by A42 (no cache mark) and stated | stated limit |
| B17 | rewritten: 24 cells (3 pairs x fix x rest/stream x [G] presence) with base digests; no cache write; only the three P2-11 kinds | P2-19 |
| B19, B20 | added: raising logger at PRICE_CACHE_HIT (price kept) / PRICE_CACHE_SKIP (never raises); should_cache_price stays the patched gate | P2R-4, P2R-10 |
| B21 | added: source read, the direct-hit write keeps `if should_cache_price(` and logs site=direct_hit | C-5 b |
| B22, B23 | added: _seen_at on a persisted write (kept when present; PIN flag OFF) and on an L2 -> L1 promotion (now - age) | P2R-6 |
| B24 | added: a race miss records timed_out in the ledger | P2R-11 |
| A45 | added: Dior typed 100 vs untyped Bleu 150 with NO 100 ml candidate: never pended by the flag, x fix x [G] | mutant M05 gap |
| A46 | added: common {50, 125} without 100 -> 125 | mutant M08 gap |
| A47 | added: a two-digit fl oz number on the product side is ignored | mutant M22 gap |
| A33c | added: no title and no url -> no_title (the gate's order) | mutant M35 gap |
| A48 | added: PIN, typed 30 with a size-less listing vs a 30 ml partner is comparable (no projection, no offsize, not limited_data), both flag values | P2R-2, mutant M42 gap |
| R01-R03 | added: the phone's GET route with the header absent / other / mixed case / list, POST with the token, PIN flag OFF with the token | P2R-18, P2R-21 |

## 6. Mutation table (66 mutants on the prototype bytes; byte copy, one exact edit, both unit files, restore, sha256 compare)
| M | mutant | result | killers (first rows) |
|---|---|---|---|
| M01 | reader not gated | KILLED (72) | test_a01_flag_reader, test_a04_a05_ted_dior_own_typed_sizes, test_a09_ysl_lancome_different_sizes, test_a10_baccarat_70, test_a15_legacy_branch_both_shown, test_a25_numbers_match_flag_off |
| M02 | no strip/lower | KILLED (2) | test_a01_flag_reader |
| M03 | typed target = min of both (combined query) | KILLED (6) | test_a06_own_typed_size_reselection, test_a19_both_projected_when_today_pends_nothing |
| M04 | typed size reads the price title first | KILLED (26) | test_a02_typed_size_both_modes, test_a06_own_typed_size_reselection, test_a07_one_side_typed, test_a11_common_100_kept, test_a12_common_50, test_a13_100_preferred |
| M05 | typed branch pends when no candidate | KILLED (4) | test_a45_untyped_side_without_typed_size_candidate |
| M06 | no-common branch pends both | KILLED (29) | test_a09_ysl_lancome_different_sizes, test_a10_baccarat_70, test_a15_legacy_branch_both_shown, test_a20_marker_modes, test_a21_size_and_per_ml_stamp, test_a30_reselection_skips_marketplaces |
| M07 | common target max always | KILLED (2) | test_a13_100_preferred |
| M08 | common target min | KILLED (2) | test_a46_largest_common_without_100 |
| M09 | untyped side ignores the typed side | KILLED (4) | test_a07_one_side_typed |
| M10 | projection skipped | KILLED (53) | test_a04_a05_ted_dior_own_typed_sizes, test_a09_ysl_lancome_different_sizes, test_a10_baccarat_70, test_a15_legacy_branch_both_shown, test_a17_projection_equals_flag_off_inputs, test_a17b_projection_keeps_the_size_annotation |
| M11 | projection index 0 only | KILLED (31) | test_a04_a05_ted_dior_own_typed_sizes, test_a10_baccarat_70, test_a15_legacy_branch_both_shown, test_a17_projection_equals_flag_off_inputs, test_a17b_projection_keeps_the_size_annotation, test_a19_both_projected_when_today_pends_nothing |
| M12 | fresh pending dict | KILLED (2) | test_a17b_projection_keeps_the_size_annotation |
| M13 | both-projected fallback removed | KILLED (4) | test_a19_both_projected_when_today_pends_nothing |
| M14 | overview restore removed | KILLED (78) | test_a04_a05_ted_dior_own_typed_sizes, test_a07_one_side_typed, test_a09_ysl_lancome_different_sizes, test_a10_baccarat_70, test_a15_legacy_branch_both_shown, test_a18_consumers_see_no_comparison |
| M15 | alias copies removed | KILLED (37) | test_a04_a05_ted_dior_own_typed_sizes, test_a09_ysl_lancome_different_sizes, test_a10_baccarat_70, test_a15_legacy_branch_both_shown, test_a35_typed_30_sizeless_listing_vs_100, test_a36_two_size_listing_vs_100 |
| M16 | restore mutates pd in place | KILLED (6) | test_a18_consumers_see_no_comparison, test_a35_typed_30_sizeless_listing_vs_100, test_a36_two_size_listing_vs_100, test_b03_partial_build_equals_full |
| M17 | restore skips is_price_showable | KILLED (8) | test_a08_typed_off_size_listing_stays_pending, test_a22_restore_runs_chokepoint_checks |
| M18 | per_ml 2 places | KILLED (11) | test_a04_a05_ted_dior_own_typed_sizes, test_a09_ysl_lancome_different_sizes, test_a10_baccarat_70, test_a21_size_and_per_ml_stamp, test_a35_typed_30_sizeless_listing_vs_100 |
| M19 | listing size allows several tokens | KILLED (4) | test_a03_listing_size_strict, test_a21_size_and_per_ml_stamp, test_a36_two_size_listing_vs_100 |
| M20 | numbers_match strips every number | KILLED (2) | test_a24_numbers_match_other_numbers_kept, test_l4_shopping_filters_recorded |
| M21 | numbers_match strip not gated | KILLED (2) | test_a25_numbers_match_flag_off, test_a26_every_caller_follows |
| M22 | size token without oz | KILLED (1) | test_a47_numbers_match_fl_oz_two_digits |
| M23 | predicate on the retailer only | KILLED (1) | test_a27_marketplace_predicate |
| M24 | predicate by substring | KILLED (1) | test_a27_marketplace_predicate |
| M25 | Tier-1 skip not gated | KILLED (1) | test_a29_tier1_pick_flag_off |
| M26 | V2 candidates not filtered | KILLED (1) | test_a30_reselection_skips_marketplaces |
| M27 | reseller replaces a genuine park | KILLED (1) | test_b10_genuine_park_kept |
| M28 | reseller not seeded | KILLED (3) | test_b09_reseller_parked_and_served, test_b10_genuine_park_kept |
| M29 | legacy cache key | KILLED (2) | test_b04_b05_cache_reselected_and_read_back |
| M30 | write without the identity gate | KILLED (1) | test_b06_never_cache_refused_or_converted_over_genuine |
| M31 | KB re-selection marked for the cache | KILLED (1) | test_a42_kb_reselection_not_marked |
| M32 | PRICE_OUTCOME behind the flag | KILLED (7) | test_a31_price_outcome_flag_off, test_a32_price_outcome_no_path_no_personal, test_a39_price_outcome_raising_logger, test_a44_price_outcome_marketplace_field, test_b16_price_outcome_both_routes |
| M33 | full URL logged | KILLED (1) | test_a32_price_outcome_no_path_no_personal |
| M34 | PRICE_CACHE_HIT missing on L1 | KILLED (3) | test_b04_b05_cache_reselected_and_read_back, test_b19_cache_hit_logger_raising |
| M35 | refusal reason order | KILLED (1) | test_a33c_refusal_reason_order |
| M36 | SSE restore removed | KILLED (4) | test_b02_stream_complete_and_prices |
| M37 | partial builds skip the step | KILLED (2) | test_b03_partial_build_equals_full |
| M38 | wire exception not caught | KILLED (1) | test_b18_wire_failure_ships_flag_off_body |
| M39 | marker different_sizes for one null + 100 | KILLED (1) | test_a20_marker_modes |
| M40 | C-5a converted-park filter not gated | KILLED (1) | test_a37_filter_marketplace_rows |
| M41 | C-5b no SKIP at direct_hit | KILLED (1) | test_b21_direct_hit_site_uses_skip_line |
| M42 | C-5c comparability strict only | KILLED (2) | test_a48_typed_size_makes_a_sizeless_listing_comparable |
| M43 | C-5d trace note unguarded | KILLED (1) | test_a41_trace_note_raising |
| M44 | header case-sensitive | KILLED (3) | test_h1_header_reader, test_r01_get_route_header |
| M45 | header read with the flag OFF | KILLED (1) | test_h2_header_reader_switch_off |
| M46 | capability ignored (always restore) | KILLED (32) | test_a04_a05_ted_dior_own_typed_sizes, test_a09_ysl_lancome_different_sizes, test_a10_baccarat_70, test_a15_legacy_branch_both_shown, test_a19_both_projected_when_today_pends_nothing, test_a35_typed_30_sizeless_listing_vs_100 |
| M47 | offsize_listing missing | KILLED (35) | test_a04_a05_ted_dior_own_typed_sizes, test_a09_ysl_lancome_different_sizes, test_a10_baccarat_70, test_a15_legacy_branch_both_shown, test_a18_consumers_see_no_comparison, test_a19_both_projected_when_today_pends_nothing |
| M48 | offsize title not cut | KILLED (1) | test_a43_offsize_title_cut |
| M49 | floor removed | KILLED (13) | test_f2_floor_reselects_or_pends, test_f4_floor_words_and_common_size, test_l5_floor_pend_is_recorded |
| M50 | floor ignores the typed size | KILLED (1) | test_f3_typed_10ml_keeps_10ml |
| M51 | ledger order | KILLED (1) | test_l1_closest_to_success_wins |
| M52 | no timed_out note | KILLED (1) | test_b24_race_miss_notes_timed_out |
| M53 | no numbers_match note | KILLED (1) | test_l4_shopping_filters_recorded |
| M54 | marketplace field always 0 | KILLED (1) | test_a44_price_outcome_marketplace_field |
| M55 | _seen_at overwritten | KILLED (1) | test_b22_seen_at |
| M56 | _seen_at not gated | KILLED (1) | test_b22_seen_at |
| M57 | converted overwrites genuine | KILLED (1) | test_b06_never_cache_refused_or_converted_over_genuine |
| M58 | gender row not gated | KILLED (1) | test_g2_rasasi_hawas_flag_off |
| M59 | cap field always none | KILLED (3) | test_a38_price_outcome_cap_and_reconcile, test_b16_price_outcome_both_routes |
| M60 | CACHE_HIT unguarded | KILLED (1) | test_b19_cache_hit_logger_raising |
| M61 | CACHE_SKIP unguarded | KILLED (1) | test_b20_cache_skip_persist_and_raising |
| M62 | PRICE_OUTCOME unguarded | KILLED (2) | test_a39_price_outcome_raising_logger, test_a40_price_outcome_raising_formatter |
| M63 | C-2 age 0 for unknown | KILLED (1) | test_b08_cache_hit_l2 |
| M64 | P2R-4 gate replaced by the reason | KILLED (1) | test_b20_cache_skip_persist_and_raising |
| M65 | GET route does not pass the token | KILLED (2) | test_r01_get_route_header |
| M66 | floor words ignored | KILLED (5) | test_f4_floor_words_and_common_size |

Totals: 66 KILLED, 0 SURVIVED, 66 run of 66 (final). First pass: 61 KILLED, 5 SURVIVED (M05, M08, M22, M35, M42); each got a killing row (A45, A46, A47, A33c, A48) and was re-run on the final file set: all five KILLED. Equivalent survivors: none. Spec M01-M39 map to my M01-M39 (M03 / M05 / M12 / M16 / M37 re-expressed on the prototype's shape); M40-M43 are the four C-5 gaps (a: converted-park filter not gated; b: no SKIP at direct_hit; c: strict-only comparability; d: unguarded trace note); M44-M66 cover the new rulings (section G token reader / cap / offsize, floor, ledger, seen_at, P2R-5 converted-over-genuine, the gender row, each guarded log line, C-2, P2R-4, the GET route token).

Kill type (house rule: KILLED = an assertion failure): every kill is an AssertionError EXCEPT five mutants whose only kill is the injected fault escaping, which is the defect those rows exist to catch: M38 (B18: the unguarded wire raises, the body is lost, KeyError 'overview'), M43 (A41: the unguarded trace note raises out of the reconcile), M60 (B19: RuntimeError out of _get_price), M61 (B20: RuntimeError out of _persist_genuine_price), M62 (A39 / A40: the injected error out of build_comparison_response). M01 also has one such node (A40) beside 71 assertion kills. For the gate: accept these as KILLED (an escaped exception is the failure) or rule a wrapper row that asserts `not raises`; recommended accept.

## 7. Comm set at the base (REAL worktree sc-inc-p2, base bytes, read-only runs)

Set: the spec's union list comm_set_full.txt (753, sha256 b6545390...) minus the 12 non-test helpers and minus the three tests/test_precommit_hook*.py files it carried (the fourth, test_precommit_hook_round2.py, was not in it) = 738 test files, red/comm_list.txt (sha256 94b5fbf18f29a1e340701e9f4e9238dd061045b9599929c74d9c3de9da545fa6). Every CLAUDE.md reader of R-8 is a member (test_ci_gates, test_behavior_dimension_translation, test_inc_r1_seam, test_s81_s04_spend_breaker, test_s81_s07_meas_harness, test_s81_s08b_legacy_fingerprint, test_s81_s08b_gate_rows, test_s81_s23_bypass_retire), and so are R-5's test_m18_offload_sweep_residual.py and test_negcache_genuine_invalidation.py. No NETWORK_FLAKY_EXCLUDE list exists on this lane. Per-file reasons: red/b_comm_reasons.tsv. The change list's new TR edit (D1) adds no member: text_routes importers are already in (app.main / TestClient users).

30 chunks of at most 25 files, bound 1200, one at a time through gate.py (tags inc-p2-base-c01..c30); 0 TIMEOUT, 0 BUSY:
    [pyt] tag=inc-p2-base-c01 start=2026-11-16 20:45:55 end=2026-11-16 20:46:27 elapsed=32s bound=1200s status=OK rc=0
    [pyt] tag=inc-p2-base-c02 start=2026-11-16 20:46:34 end=2026-11-16 20:46:59 elapsed=25s bound=1200s status=FAIL rc=1
    [pyt] tag=inc-p2-base-c03 start=2026-11-16 20:47:06 end=2026-11-16 20:47:31 elapsed=25s bound=1200s status=OK rc=0
    [pyt] tag=inc-p2-base-c04 start=2026-11-16 20:47:38 end=2026-11-16 20:48:29 elapsed=52s bound=1200s status=OK rc=0
    [pyt] tag=inc-p2-base-c05 start=2026-11-16 20:48:36 end=2026-11-16 20:49:06 elapsed=30s bound=1200s status=OK rc=0
    [pyt] tag=inc-p2-base-c06 start=2026-11-16 20:49:13 end=2026-11-16 20:49:26 elapsed=14s bound=1200s status=OK rc=0
    [pyt] tag=inc-p2-base-c07 start=2026-11-16 20:49:33 end=2026-11-16 20:49:51 elapsed=18s bound=1200s status=OK rc=0
    [pyt] tag=inc-p2-base-c08 start=2026-11-16 20:50:24 end=2026-11-16 20:50:57 elapsed=33s bound=1200s status=OK rc=0
    [pyt] tag=inc-p2-base-c09 start=2026-11-16 20:51:17 end=2026-11-16 20:52:26 elapsed=69s bound=1200s status=OK rc=0
    [pyt] tag=inc-p2-base-c10 start=2026-11-16 20:52:33 end=2026-11-16 20:53:18 elapsed=45s bound=1200s status=OK rc=0
    [pyt] tag=inc-p2-base-c11 start=2026-11-16 20:53:24 end=2026-11-16 20:54:02 elapsed=37s bound=1200s status=OK rc=0
    [pyt] tag=inc-p2-base-c12 start=2026-11-16 20:54:09 end=2026-11-16 20:54:24 elapsed=15s bound=1200s status=OK rc=0
    [pyt] tag=inc-p2-base-c13 start=2026-11-16 20:54:31 end=2026-11-16 20:54:44 elapsed=13s bound=1200s status=OK rc=0
    [pyt] tag=inc-p2-base-c14 start=2026-11-16 20:54:50 end=2026-11-16 20:55:22 elapsed=31s bound=1200s status=OK rc=0
    [pyt] tag=inc-p2-base-c15 start=2026-11-16 20:56:00 end=2026-11-16 20:56:34 elapsed=34s bound=1200s status=FAIL rc=1
    [pyt] tag=inc-p2-base-c16 start=2026-11-16 20:56:40 end=2026-11-16 20:57:05 elapsed=25s bound=1200s status=OK rc=0
    [pyt] tag=inc-p2-base-c17 start=2026-11-16 20:57:12 end=2026-11-16 20:57:31 elapsed=19s bound=1200s status=FAIL rc=1
    [pyt] tag=inc-p2-base-c18 start=2026-11-16 20:57:37 end=2026-11-16 20:57:51 elapsed=13s bound=1200s status=OK rc=0
    [pyt] tag=inc-p2-base-c19 start=2026-11-16 20:57:57 end=2026-11-16 21:01:03 elapsed=185s bound=1200s status=OK rc=0
    [pyt] tag=inc-p2-base-c20 start=2026-11-16 21:01:34 end=2026-11-16 21:03:10 elapsed=96s bound=1200s status=OK rc=0
    [pyt] tag=inc-p2-base-c21 start=2026-11-16 21:03:50 end=2026-11-16 21:05:46 elapsed=116s bound=1200s status=FAIL rc=1
    [pyt] tag=inc-p2-base-c22 start=2026-11-16 21:09:44 end=2026-11-16 21:10:47 elapsed=64s bound=1200s status=FAIL rc=1
    [pyt] tag=inc-p2-base-c23 start=2026-11-16 21:16:28 end=2026-11-16 21:17:09 elapsed=41s bound=1200s status=FAIL rc=1
    [pyt] tag=inc-p2-base-c24 start=2026-11-16 21:19:46 end=2026-11-16 21:20:21 elapsed=35s bound=1200s status=OK rc=0
    [pyt] tag=inc-p2-base-c25 start=2026-11-16 21:20:46 end=2026-11-16 21:21:32 elapsed=45s bound=1200s status=OK rc=0
    [pyt] tag=inc-p2-base-c26 start=2026-11-16 21:22:40 end=2026-11-16 21:23:20 elapsed=40s bound=1200s status=OK rc=0
    [pyt] tag=inc-p2-base-c27 start=2026-11-16 21:24:45 end=2026-11-16 21:25:20 elapsed=35s bound=1200s status=OK rc=0
    [pyt] tag=inc-p2-base-c28 start=2026-11-16 21:27:21 end=2026-11-16 21:27:48 elapsed=27s bound=1200s status=OK rc=0
    [pyt] tag=inc-p2-base-c29 start=2026-11-16 21:28:46 end=2026-11-16 21:29:19 elapsed=33s bound=1200s status=OK rc=0
    [pyt] tag=inc-p2-base-c30 start=2026-11-16 21:29:45 end=2026-11-16 21:29:52 elapsed=7s bound=1200s status=OK rc=0

Totals: passed 29634, failed 26, errors 2, skipped 52, deselected 85. FAILED / ERROR ids (28), all pre-existing base noise: the 731bcddf INC-R1 record set (cold tiktoken prompt_truth x2, CRLF / hygiene / golden rows, the auth_interceptor and page_scraping rows) plus test_personalization_bundle_c.py x2, which are in the 731bcddf INC-I1 710-file record too (chunk-order dependent). The INC-R1 record's load flake test_retro_w0_4 [scs._fetch_page_price] passed here. List: red/b_base_comm_failed.txt.
- tests/test_auth_interceptor.py::test_sign_in_with_social_exception
- tests/test_auth_interceptor.py::test_social_login_user_insert_fails_gracefully
- tests/test_page_scraping.py::TestFetchPagePriceJsonLD::test_jsonld_nested_offers_picks_lowest
- tests/test_page_scraping.py::TestFetchPagePriceOpenGraph::test_og_meta_extraction
- tests/test_personalization_bundle_c.py::test_applied_shifts_list_is_default_empty_when_no_priorities
- tests/test_personalization_bundle_c.py::test_full_response_payload_audit_no_magnitude_keys
- tests/test_prompt_truth.py::test_render_digests_match_base_except_the_fence
- tests/test_prompt_truth.py::test_truth_on_prefix_static_and_cacheable
- tests/test_s81_d16_operator_ingest.py::test_r10_runbook_names_only
- tests/test_s81_d17_coverage.py::test_r9_railway_config_and_hygiene
- tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[OFF]
- tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[empty]
- tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[false]
- tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[pad0]
- tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[unset]
- tests/test_s81_s07_meas_harness.py::test_r35_fixtures
- tests/test_s81_s10_fragrance_gate.py::test_r06_production_lexicon_content
- tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[cron_feed_walker]
- tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[cron_pdp_discovery]
- tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[kb_seed_common]
- tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[seed_kb_batch]
- tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[seed_kb_brands_wikidata]
- tests/test_s81_s18b_store_label.py::test_r2_table_shape
- tests/test_s81_s19_gap_queue.py::test_r15_hygiene
- tests/test_s81_s22_compare_runs.py::test_b02_one_transaction_ascii_lf
- tests/test_s81_s22_judge.py::test_j01_script_exists_and_off_first
- tests/test_s81_s24_auth_throttle.py::test_p83_red_file_setenv_hygiene
- tests/test_s81_s24_auth_throttle.py::test_r92_hygiene

Restore check: sha256 of all 3606 tracked files of sc-inc-p2 equal before and after my round (snapshot 6f4017d2...); HEAD b0ad2603; git status shows only Agent A's two untracked test files. My two scratch worktrees (INC-P2_scratch, INC-P2_proto) were removed with git worktree remove --force; git worktree list no longer names them; no mutation lock left; no pytest of mine alive. The queue driver red/qdrive.py ends with this agent: Agent A must start its own if it still queues jobs.

## 8. What today's app bundles draw for a different-sizes pair (P2-6, section E as amended by section G)

Plain words: neither live bundle (the store binary JS 683f56c0 and the newest client code on main) reads price.size, size_ml, per_ml, offsize_listing or the pair marker, and neither computes a "cheaper" claim from the two amounts (its only such code, getPriceDiff, is dead). Today, for a different-sizes pair such as "Ted Baker M 30ml" vs "Dior Sauvage 100 ML Edp", the phone draws one amount and "No confirmed price yet" for the other side, and hides the price and value bars and the price pill. After the flip, a phone that does NOT send the price_size token draws exactly that same screen (the held side stays pending; its listing travels in price.offsize_listing, which these bundles ignore). Only an app update that sends price_size (the main lane's OTA) shows both amounts, and no bundle draws the size until that update draws size_ml. (Spec 1.5 measurement, not re-run here; offsize_listing is a new name with no reader in SmartCompareApp/src at the base.)

## 9. deploy_visible_delta in plain words (P2R-14)

With ENABLE_PRICE_NOT_LOST unset, a deploy changes only log lines and an internal ledger: (1) one PRICE_OUTCOME INFO line per product per response build (two per compare, four when a moderation-window partial is also built), names and numbers only; (2) one PRICE_CACHE_HIT line per price served from L1 or L2 (age unknown on L1, and on L2 when the age flag is off); (3) one PRICE_CACHE_SKIP line each time the cache gate refuses a write at the persist and the adapter direct-hit sites, which were silent before; (4) an in-memory per-request miss ledger and trace, never written to a body, a cache or a prompt. The Rasasi Hawas gender row is gated (the reader takes a flag-gated extra tuple in one line), so it is NOT a flag-OFF delta. No response byte, status, cache write, DB row or prompt byte changes with the flag OFF (A34, B07, B17, B22[None], H4 and R03 pin it).

## 10. Deviations and questions for the gate

- D1 (P2R-18 vs P2-12 file ownership): section G needs the request token on the service, so the change list gains app/api/text_routes.py (three call sites: GET, POST, stream) and a new keyword price_size_cap on compare_from_text / compare_from_text_streaming. The other compare_from_text call in text_routes.py (about :1691) and the image / URL routes do not pass it (stated limit: those surfaces never show a held side's amount).
- D2 (section G when flag OFF pends nothing, A19): when the flag keeps a typed size that today's code re-selects away (Ted 30 / Dior 100 with a Dior 30 ml candidate), BOTH sides are projected, so a phone without the token sees two pending lines plus two offsize listings, where today it showed both at 30 ml (a Dior bottle the user did not type). Recommended: accept. Alternative: without the token keep today's re-selection in that case.
- D3 (P2R-6): the L1 write keeps underscore keys (cache_service.set_cached stores json.dumps of the dict), so _seen_at is used. public_price_view strips it only with the exact gate ON: with ENABLE_EXACT_PRICE_GATE=false a cached _seen_at reaches the wire (stated limit). get_cached_price hands the caller no fetched_at; the promotion derives _seen_at = now - _l2_age_seconds, which exists only with ENABLE_L2_PROMOTION_REMAINING_TTL on; otherwise a promotion carries no _seen_at (stated limit).
- D4 (P2R-12, "Mini" inside a line name): no fragrance line or lexicon entry carries the word (git grep of data/fragrance_lines.json and data/fragrance_lexicon.json: none; the only "Mini" hits are non-fragrance gold-truth rows), so no PIN row was written; F4 covers the five words as whole words.
- D5 (P2R-13): the gender table IS read per call inside _vd_gender_line_flip; a one-line flag-gated extra tuple works, so the row ships under the flag (G1 RED, G2 PIN). It acts only with ENABLE_LISTING_MATCH_GUARD on (its own flag).
- D6 (P2R-11 refused / no_price_parsed): the ledger takes them (L1), but no row drives the ADAPTER DROP / Shopify status / FETCH-FAIL sites; the prototype noted timed_out (race miss), numbers_match and marketplace (Shopping) and floor (reconcile) only. Stated limit until INC-P3, as the ruling allows.
- D7 (B05 resolver ON): the resolver cell replaces _resolve_explicit_pair with the apply_resolution Step-1 shape (no LLM); product_resolver itself is not exercised.
- D8 (spec B03 stream partials): the two stream tail partials and the gather-time partial are not driven (they are built from the early buffer, before the reconcile); B03 covers the sync partial built after the full build. Stated.
- D9 (B17 digests): the flag-OFF digests drop the FY25 volatile keys (elapsed, timestamps, request_id) before hashing; recorded twice at the base, stable.
- D10 (coordination): a second RED agent (A) ran in parallel in the same folder and queue; my tags were renamed inc-p2-b-* / inc-p2-bmut-* after a tag collision with A's inc-p2-mut-* tags; one of my mutants (M01) was applied to MY prototype worktree for about a minute while no run of mine read it; it was restored from the byte copy and the prototype runs inc-p2-b-proto-on / -off ran after the restore.
- Review question 8 (flip before INC-C1): answered by section G: a phone without the token draws today's screen.

## 11. Diff of my row set against Agent A's files in sc-inc-p2/tests (read only; A's files as of 21:04, sha256 prefixes 5799cc81 / d67677e2)

- Only in mine: every section G row (A's files have 0 hits for client_price_size, price_size_cap and offsize_listing): H1-H4 (header reader, switch-off, ContextVar, flag-OFF-with-token PIN); R01-R03 (the phone's GET route with the header cells, POST with the token, flag OFF with the token); the [G] cap1 / cap0 cells on A04/A05, A07, A08, A09, A10, A15, A18, A19, A22, A35, A36, F2, B01, B02, B03, B14, B15, and token-present cells on A34 and B17; A38 (cap=, offsize_held); A37 (the converted-park filter gated); A40 (raising field builder); A17b (size annotation byte identity); A42 (a KB side is not marked); A43 (offsize title cut); B21 (direct-hit gate kept, site=direct_hit); B23 (_seen_at on a promotion); B24 (timed_out note); A13 split fix0 RED / fix1 PIN.
- Only in A's: b00 (harness-is-the-fragrance-path PIN), b03s (stream tail partial stamps the size), b06d (cache write bounded and swallowed), b09b as its own row (mine is inside B10), b11w (helpers wired, source read; mine B11b / B21), b12p (filter flag-OFF PIN; mine is A37's flag-OFF half), b13 (a marketplace price is never shown), b14k (KB-served cell), b16t (timed_out and parked origin on PRICE_OUTCOME), f01 (two travel sprays never shown), f03 (floor on the both-shown path), f05 (floor word whole-word PIN), l05 (the outcome reads the ledger, the body does not), s03 (flag-OFF cache writes byte identical; mine B22[None] + B07), a33 exact-gate-OFF no-reason row (mine: A33 PIN exact gate OFF half), p7 marketplace outcome (mine A44).
- Same intent, other names: A's n01 / n02 = my A35 / A36; g01 / g02 = G1 / G2; x01..x04 = A39 / A41 / B19 / B20; l01..l04, l06 = L1, L4 (+ marketplace), L3, L5.

## Not done in this round

No jest (B-5 fences), no tsc / eslint. No write to the real worktree; Agent A's files untouched. The KB-served pipeline cell and the stream tail / gather partials are not driven (D8). Nothing here is a phone proof: any fix is "merged, NOT yet proven" until the owner's phone shows it.
