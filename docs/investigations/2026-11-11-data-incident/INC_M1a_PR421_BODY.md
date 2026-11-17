# INC-M1a RESOLVER FOLD: Arabic typed names, seed rows, Arabic concentration phrases

Rides `ENABLE_PRODUCT_RESOLVER` (OFF on web). **No new flag.** With ENABLE_PRODUCT_RESOLVER OFF nothing changes, except the INC-U1 link key (product.link_key, brand and variant in the /url response) when ENABLE_URL_LINK_RESULT is ON (M1R-9; both OFF on web) (PIN-0, the 8 base digests). Merged, NOT yet proven: the proof is the owner's phone (below). INC-M1b MATCHER FOLD must also merge before the flag opens (M1R-1).

## What it does (only when ENABLE_PRODUCT_RESOLVER is ON)
- `data/fragrance_lines.json` is the ONE home for Arabic brand and line spellings (JSON escapes; the loader refuses any byte > 127): the Arabic Dior / Sauvage and Chanel / Bleu de Chanel house and line aliases, the Bleu particle with the WAW and the YA spelling as two explicit rows (M1R-3). An Arabic typed pair resolves high/lexicon and `apply_resolution` writes exactly the Latin twin's dicts: same search query, price cache key and picture query; no model call, no spend.
- The resolver's typed concentration and its D2 strip read the Arabic concentration phrases of `data/fragrance_lexicon.json` through `category_gate.load_lexicon` (the FRAGRANCE_LEXICON_PATH seam, M1R-10), each also with the YA particle, mapped to the Latin labels of `CONCENTRATION_PHRASES`, and only for Arabic tokens (a Latin name reads exactly the base table). `price_service.extract_concentration` is unchanged; `CONCENTRATION_PHRASES`, `GENERIC_WORDS`, `QUALIFIER_WORDS` are byte-identical.
- Seed data (M1R-4): YSL `Y` (EDT / EDP, base EDT, flankers Le Parfum / Elixir), Rasasi `Hawas` (EDP, flankers Ice / for Her, the lexicon's Arabic Rasasi as a house alias), flankers on Libre (Intense, Le Parfum), Khamrah (Qahwa, Dukhan), Aventus (for Her, Absolu, Cologne), Libre concentrations EDT / EDP (base EDP kept), the optional bool `single_concentration` on Aventus, Layton, Khamrah and Hawas only (the validator refuses a non-bool; INC-M1b reads it).
- A flanker made of a generic word (Cologne) is matched before the generic-word drop, so `Creed Aventus Cologne` resolves to the line WITH the flanker (the Stronger With You representation), never the base at high. A one-character alias token (the line Y) matches only exactly, in the lexicon arm's D5 line search only (`_lexicon_side` passes `exact_single=True` to `_best_window` / `_token_distance`); the INC-R1 model-arm guard (d) `_line_within_typed` and every other caller keep the base D5 rule (fix round 1, FX1).
- No edit to image_relevance.py, image_service.py, price_service.py, url_extraction_service.py or any client file.

## Defects -> RED node ids (tests/test_inc_m1a_resolver_fold.py, frozen, sha256 63fc6a67...)
| defect / spec row | node ids |
|---|---|
| Arabic typed names fold to the Latin identity (the one home) | test_ar0_arabic_aliases_in_the_lines_file, test_ar0b_lines_file_ascii_and_loads, test_ar0c_loader_reads_fourteen_lines |
| AR-1 resolve and rewrite as Latin | test_ar1_arabic_pair_resolves_and_rewrites_as_latin[arA_arB|arA_arBya|arA_latB|arB_latA|arBya_latA] |
| AR-2 seam queries equal the Latin twin (sync + stream, 4 flag mixes) | test_ar2_seam_queries_equal_the_latin_twin[rest|stream x waw|ya x text_off|text_on_c2|text_on_c3|text_on_c3_words] |
| AR-3 price accept sets | test_ar3_arabic_accept_sets_equal_the_golden[arA|arB|arBya] (+ PIN test_ar3_pin_latin_*) |
| AR-4 picture identity | test_ar4_picture_identity_equals_the_latin_twin[waw|ya x words_off|words_on] (+ PIN test_ar4_pin_latin_picture_counts) |
| AR-5 Arabic concentration phrases (WAW, YA, plain alef) | test_ar5_arabic_concentration_phrase_resolves[9 ids]; PIN ar5b / ar5c / ar5d (the lexicon seam) |
| SEED-1 seed rows and flankers | test_seed1_data_rows, test_seed1_typed_names_resolve[17 ids] |
| SEED-2 validator | test_seed2_validator_rejects_non_boolean[1|0|str_true|blank|null] (+ PIN accepts bool) |
| PIN-0 flag-OFF identity and the non-hook readers | test_pin0_flag_off_identity[8], test_pin0_constants_*, test_pin0_resolver_word_tables_unchanged, test_pin0_non_hook_readers_unchanged, test_pin0_link_key_unchanged_for_the_base_lines[13] |
| Fix round 1 SR (short tokens, M1R-11 (d), adversary M1) | tests/test_inc_m1a_gate_rows.py::test_sr1_short_token_never_resolves_to_line_y[10 names x on/off], test_sr2_exact_y_resolves_to_line_y[6 names x on/off] |
| Fix round 1 MG (the model-arm guard, adversary B1) | tests/test_inc_m1a_gate_rows.py::test_mg1_guard_accepts_as_at_base[15], test_mg2_guard_refuses_as_at_base[5], test_mg3_accept_model_side_as_at_base[9], test_mg4_accept_model_side_refuses_as_at_base[5], test_mg5_model_arm_pair_resolves_as_at_base[9], test_mg6_model_arm_pair_refused_as_at_base[2], test_mg7_answer_payload_is_ascii_json |
| PIN-1 the existing lines | test_pin1_existing_lines_unchanged[25], test_pin1_changed_lines_keep_their_side[6], test_pin1_arabic_outside_the_seed_unchanged |

RED gate: 62 RED (AssertionError only) + 66 PIN at base 7f672cfe; 13 of 13 mutants killed (MA1-MA13); report INC-M1a_RED_REPORT.md.

## Fix round 1 (FIX1_RULINGS_INC_M1a; adversary verdict NOT_READY: B1 blocking, M1 major)
- **B1 (FX1):** the GREEN one-character exact rule lived in the shared `_token_distance`, so it also tightened the INC-R1 model-arm guard (d): a high-confidence model answer such as Chanel N-degree-5, Terre d'Hermes, Bois d'Argent, L'Homme or L'Eau d'Issey was refused, and the pair asked. Now a keyword `exact_single` (default False = the base rule) is passed only by the lexicon arm's D5 line search; `_line_within_typed` calls `_best_window` exactly as at base 9bc13109.
- **M1 (FX2):** the new pin file `tests/test_inc_m1a_gate_rows.py` (78 rows, pure ASCII, hermetic, flags set explicitly; the frozen RED file stays byte-identical, sha256 63fc6a67...). SR: 10 short-token names (YSL L'Homme, Yves Saint Laurent L'Homme, YSL B / by / X / 1 / Ya / Yo, YSL + a one-letter Arabic YA / WAW) never resolve to (Yves Saint Laurent, Y) and stay medium / source none; 6 exact spellings (Y, Y EDP, YSL Y, Saint Laurent Y, YSL Y EDP, YSL Y Elixir) resolve high/lexicon (golden probe_short_after.txt); each with the flag ON and OFF. MG: the guard and `accept_model_side` accept the base accepts and refuse the base refusals; the end-to-end rows run `resolve_pair` through the r21 seam (the flag ON, ENABLE_ANTHROPIC_TEXT ON, consent 3, the fake SDK): accepted -> outcome resolved; a line outside the typed text -> outcome ask.
- **Proof, in the rulings' order:** (1) at 06deda55 the 27 MG accept rows FAIL (AssertionError only, 27 of 27) and the 51 other rows (every SR row, the MG refusals, the accepts true under both rules) PASS; (2) mutant X1 (the D1 rule reverted) on a byte copy of the 06deda55 bytes: the 20 SR-not rows FAIL (AssertionError); (3) after FX1 all 78 rows pass; (4) mutant M4 (the exact rule also in `_line_within_typed`, the 06deda55 behaviour) fails the 27 MG accept rows. Also killed: M5 (the rule global again) 27 MG rows; X1L (`_lexicon_side` drops `exact_single=True`) and X1P (`_best_window` stops passing it) 20 SR rows each. Every mutant restored and sha-verified.
- **Minors (FX3):** m1 the flag-OFF wording (above, the CLAUDE.md row and the flag mixes); m2 the CLAUDE.md row says the rule is the lexicon arm's only; m3 the [pyt] line under the resolver suites; m4-m7 stated limits (below).

## Deliberate pin changes (E-rows, M1R-8)
| id | node | before | after |
|---|---|---|---|
| E1 | `tests/test_inc_r1_resolver.py::test_r05_lines_file` | 12 lines; pairs == SEED_PAIRS; flankers == [] except Stronger With You | 14 lines; pairs == SEED_PAIRS | {(Yves Saint Laurent, Y), (Rasasi, Hawas)}; flankers of Libre / Khamrah / Aventus / Y / Hawas as seeded (M1A_FLANKERS), [] elsewhere; single_concentration, when present, is a bool |
| E2 | `tests/test_inc_r1_resolver.py::test_r11_residual_not_high` | ids Dior Sauvage Eau Forte / Creed Aventus for Her / YSL Libre Intense stay medium | ids Dior Sauvage Eau Forte / Creed Aventus for Women / YSL Libre Absolu Platine stay medium (the two seeded flankers now resolve to the flanker line, pinned by SEED-1) |
| E3 | `tests/test_inc_r1_resolver.py::test_r15_arabic_never_lexicon_high` | Arabic Dior + Arabic Sauvage: medium, house hint only | Arabic Dior Sauvage resolves high/lexicon ONLY through the seeded aliases (the data row is asserted); Arabic Dior + an unseeded Arabic line (Fahrenheit) and Arabic Khamrah Lattafa stay medium / source none / is_fragrance True |
| E4 | `tests/test_inc_r1_resolver.py::test_r21_guard[g8]` | name AR[0] (Arabic Dior Sauvage), model (Dior, Sauvage) accepted -> (Dior, Sauvage, EDT) | name AR_UNSEEDED (Arabic Khamrah Lattafa), model (Lattafa, Khamrah) accepted -> (Lattafa, Khamrah, EDP) |
| E5 | `tests/test_inc_r1_resolver.py::test_r21_guard[g8b]` | name AR[0], model (Acme House, Sauvage) refused | name AR_UNSEEDED, model (Acme House, Khamrah) refused |

E4 / E5 assert, before and after, that for an Arabic typed name the model side is accepted only when its brand is a known house (guard (c); no Latin line check for Arabic). The change is the minimum: AR[0] now resolves in the lexicon arm, so it never reaches the model; only the input name (an unseeded Arabic name) and the model's line move with it.

## Gates (fix round 1, HEAD e60a656c6a8979b7370bd69bb231afe8ed1866b1, base 9bc13109)
- The unit file + the new pin file + tests/test_inc_r1_resolver.py, ENABLE_PRODUCT_RESOLVER exported ON and OFF: 372 passed each (294 + the 78 new rows):
  - `[pyt] tag=inc-m1a-fix1-unit-true start=2026-11-17 14:25:36 end=2026-11-17 14:25:48 elapsed=11s bound=600s status=OK rc=0 log=C:\Users\SynAckITPC\AppData\Local\Temp\claude\cde30765822f13ce\e8bbde46-f2b1-4f83-9479-dcdff600313a\scratchpad\INC-M1a_fix1\unit_true.log`
  - `[pyt] tag=inc-m1a-fix1-unit-false start=2026-11-17 14:25:49 end=2026-11-17 14:26:01 elapsed=12s bound=600s status=OK rc=0 log=C:\Users\SynAckITPC\AppData\Local\Temp\claude\cde30765822f13ce\e8bbde46-f2b1-4f83-9479-dcdff600313a\scratchpad\INC-M1a_fix1\unit_false.log`
- RED step at 06deda55 (the new pin file before FX1): 27 failed (every one an AssertionError), 51 passed:
  - `[pyt] tag=inc-m1a-fix1-red-head start=2026-11-17 14:24:10 end=2026-11-17 14:24:14 elapsed=4s bound=600s status=FAIL rc=1 log=C:\Users\SynAckITPC\AppData\Local\Temp\claude\cde30765822f13ce\e8bbde46-f2b1-4f83-9479-dcdff600313a\scratchpad\INC-M1a_fix1\red_head.log`
- Mutants (bound 600 each, -k test_sr or test_mg on the pin file): X1 on the 06deda55 bytes 20 failed; M4 27 failed; M5 27 failed; X1L 20 failed; X1P 20 failed:
  - `[pyt] tag=inc-m1a-fix1-mut-X1_head start=2026-11-17 14:24:36 end=2026-11-17 14:24:40 elapsed=4s bound=600s status=FAIL rc=1 log=C:\Users\SynAckITPC\AppData\Local\Temp\claude\cde30765822f13ce\e8bbde46-f2b1-4f83-9479-dcdff600313a\scratchpad\INC-M1a_fix1\mut_X1_head.log`
  - `[pyt] tag=inc-m1a-fix1-mut-M4 start=2026-11-17 14:26:13 end=2026-11-17 14:26:17 elapsed=4s bound=600s status=FAIL rc=1 log=C:\Users\SynAckITPC\AppData\Local\Temp\claude\cde30765822f13ce\e8bbde46-f2b1-4f83-9479-dcdff600313a\scratchpad\INC-M1a_fix1\mut_M4.log`
  - `[pyt] tag=inc-m1a-fix1-mut-M5 start=2026-11-17 14:26:18 end=2026-11-17 14:26:22 elapsed=4s bound=600s status=FAIL rc=1 log=C:\Users\SynAckITPC\AppData\Local\Temp\claude\cde30765822f13ce\e8bbde46-f2b1-4f83-9479-dcdff600313a\scratchpad\INC-M1a_fix1\mut_M5.log`
  - `[pyt] tag=inc-m1a-fix1-mut-X1L start=2026-11-17 14:26:23 end=2026-11-17 14:26:27 elapsed=4s bound=600s status=FAIL rc=1 log=C:\Users\SynAckITPC\AppData\Local\Temp\claude\cde30765822f13ce\e8bbde46-f2b1-4f83-9479-dcdff600313a\scratchpad\INC-M1a_fix1\mut_X1L.log`
  - `[pyt] tag=inc-m1a-fix1-mut-X1P start=2026-11-17 14:26:28 end=2026-11-17 14:26:32 elapsed=4s bound=600s status=FAIL rc=1 log=C:\Users\SynAckITPC\AppData\Local\Temp\claude\cde30765822f13ce\e8bbde46-f2b1-4f83-9479-dcdff600313a\scratchpad\INC-M1a_fix1\mut_X1P.log`
- Existing resolver suites (INC-R1 resolver + seam, INC-U1 link result + gate rows, S81-10 gate, INC-I2b guard words + addenda): 1 failed = `test_s81_s10_fragrance_gate.py::test_r06_production_lexicon_content` (the CRLF working copy; in the base record), 699 passed:
  - `[pyt] tag=inc-m1a-fix1-resolver7 start=2026-11-17 14:27:34 end=2026-11-17 14:28:03 elapsed=29s bound=1200s status=FAIL rc=1 log=C:\Users\SynAckITPC\AppData\Local\Temp\claude\cde30765822f13ce\e8bbde46-f2b1-4f83-9479-dcdff600313a\scratchpad\INC-M1a_fix1\resolver7.log`
  - (GREEN's run of the same 7 suites at 06deda55, tag inc-m1a-green-pins, gave the same 1 failed / 699 passed; its log carries no closing [pyt] line.)
- Comm set at the fix-round head: the same 156 files in 7 chunks (the new pin file ran as the unit above). HEAD failures 15, every one in the base list (16 ids; the base-only id is the e27 timing flake, passed here); **branch-only-NEW: EMPTY**:
  - `[pyt] tag=inc-m1a-fix1-comm-c01 start=2026-11-17 14:28:10 end=2026-11-17 14:28:42 elapsed=32s bound=1200s status=OK rc=0 log=C:\Users\SynAckITPC\AppData\Local\Temp\claude\cde30765822f13ce\e8bbde46-f2b1-4f83-9479-dcdff600313a\scratchpad\INC-M1a_fix1\comm\head_c01.log`
  - `[pyt] tag=inc-m1a-fix1-comm-c02 start=2026-11-17 14:28:42 end=2026-11-17 14:30:51 elapsed=128s bound=1200s status=OK rc=0 log=C:\Users\SynAckITPC\AppData\Local\Temp\claude\cde30765822f13ce\e8bbde46-f2b1-4f83-9479-dcdff600313a\scratchpad\INC-M1a_fix1\comm\head_c02.log`
  - `[pyt] tag=inc-m1a-fix1-comm-c03 start=2026-11-17 14:30:52 end=2026-11-17 14:31:39 elapsed=48s bound=1200s status=OK rc=0 log=C:\Users\SynAckITPC\AppData\Local\Temp\claude\cde30765822f13ce\e8bbde46-f2b1-4f83-9479-dcdff600313a\scratchpad\INC-M1a_fix1\comm\head_c03.log`
  - `[pyt] tag=inc-m1a-fix1-comm-c04 start=2026-11-17 14:31:45 end=2026-11-17 14:33:27 elapsed=102s bound=1200s status=FAIL rc=1 log=C:\Users\SynAckITPC\AppData\Local\Temp\claude\cde30765822f13ce\e8bbde46-f2b1-4f83-9479-dcdff600313a\scratchpad\INC-M1a_fix1\comm\head_c04.log`
  - `[pyt] tag=inc-m1a-fix1-comm-c05 start=2026-11-17 14:33:28 end=2026-11-17 14:35:19 elapsed=111s bound=1200s status=FAIL rc=1 log=C:\Users\SynAckITPC\AppData\Local\Temp\claude\cde30765822f13ce\e8bbde46-f2b1-4f83-9479-dcdff600313a\scratchpad\INC-M1a_fix1\comm\head_c05.log`
  - `[pyt] tag=inc-m1a-fix1-comm-c06 start=2026-11-17 14:35:26 end=2026-11-17 14:36:18 elapsed=52s bound=1200s status=OK rc=0 log=C:\Users\SynAckITPC\AppData\Local\Temp\claude\cde30765822f13ce\e8bbde46-f2b1-4f83-9479-dcdff600313a\scratchpad\INC-M1a_fix1\comm\head_c06.log`
  - `[pyt] tag=inc-m1a-fix1-comm-c07 start=2026-11-17 14:36:19 end=2026-11-17 14:36:36 elapsed=17s bound=1200s status=OK rc=0 log=C:\Users\SynAckITPC\AppData\Local\Temp\claude\cde30765822f13ce\e8bbde46-f2b1-4f83-9479-dcdff600313a\scratchpad\INC-M1a_fix1\comm\head_c07.log`
- The whole-tree one-process run is NOT re-run (the fix adds no module-level state); GREEN's record at 06deda55: 20 failed, 32057 passed, 56 skipped, 124 deselected, 39 xfailed, 2 errors; failures not in the whole-tree base record: NONE (tag inc-m1a-green-tree).
- The client fences (15 suites from fence_list.txt), once, by path from SmartCompareApp through the orchestrator's node_modules junction (jest 29.7.0): 15 suites, 4 failed / 246 passed; the 4 failures are the accepted `config/nativeBundle.w37` drift nodes (d5, k2, k4, k5); every other suite passes:
  - `[jest] tag=inc-m1a-fix1-fences start=2026-11-17 14:36:46 end=2026-11-17 14:36:53 rc=1`
- ruff E9,F63,F7,F82 clean; py_compile clean; black 26.5.1 --check clean on `app/services/product_resolver.py` (allowlisted); every changed file pure ASCII except CLAUDE.md (3904 non-ASCII bytes before and after; the row is ASCII); CRLF working copies kept (product_resolver.py, CLAUDE.md); the new pin file is LF.

## Flag mixes (the adversary's lens)
ENABLE_PRODUCT_RESOLVER OFF: with ENABLE_PRODUCT_RESOLVER OFF nothing changes, except the INC-U1 link key (product.link_key, brand and variant in the /url response) when ENABLE_URL_LINK_RESULT is ON (M1R-9; both OFF on web) (PIN-0 digests for the Arabic and the Latin pair, sync and stream, unset and false; no resolver hook on the compare routes). ON with ENABLE_ANTHROPIC_TEXT OFF / ON at consent 2 / ON at consent 3 / ON + ENABLE_IMAGE_GUARD_WORDS: AR-2 shows the same queries as the Latin twin in all four; the seeded Arabic sides resolve in the lexicon arm, so the model arm is not reached for them. ON at consent 3 with TEXT ON: the model-arm guard is the base guard again (MG rows), so a model-answered Chanel N-degree-5 / Terre d'Hermes side resolves as at base instead of asking. ENABLE_URL_LINK_RESULT ON: the link key moves for the new rows only (M1R-9).

## Re-verifier (fix round 1)
- Verdict at head e60a656c: **SOUND**, 0 blocking, 0 major, 4 minor (n1-n4, stated below). B1 closed both ways (lexicon exactness kept, model guard at the base rule; mutants R1-R3 killed), M1 pinned (X1 killed by the SR rows).

## Stated limits
- The Arabic ml word is not read (neither extract_sizes_ml nor the resolver): an Arabic-typed size is lost (spec 1.4).
- Arabic names outside the two Arabic-seeded lines still need the model arm (ENABLE_PRODUCT_RESOLVER + ENABLE_ANTHROPIC_TEXT + consent 3 + the spend admit).
- Arabic-script listing titles and Arabic pictures: parity only; an Arabic-only title is refused exactly as under a Latin typed name.
- The phone shows the resolved Latin name (Dior Sauvage EDP) for an Arabic-typed name (the resolver's existing display).
- Testers unchanged (owner question 1 of R4).
- M1R-11 (a): Libre Le Parfum and YSL Y Le Parfum stay medium (parfum is stripped as a concentration before the flanker search).
- M1R-11 (b): YSL Y Elixir resolves to (YSL, Y, Elixir, flanker Elixir) through the concentration-flanker rule, as Stronger With You Parfum does.
- A one-character alias token now matches only exactly in the lexicon arm's D5 line search: it closes the M1R-11 (d) false highs measured on the prototype data (YSL L'Homme, YSL B, YSL by, YSL X, YSL 1, YSL Ya / Yo and one-letter Arabic tokens all resolved to YSL Y EDT high; pinned by the SR rows); no base alias has a one-character token, so the 12 base lines are unchanged (PIN-1). The model-arm guard keeps the base rule (FX1).
- With the model arm reachable, a high-confidence model answer of the line Y (Yves Saint Laurent) for YSL L'Homme / YSL B / YSL by / YSL Ya passes the base guard (d) and is accepted as (YSL, Y, EDT) (probe_model_y.txt): the base guard does so for any one-letter model line (FX1 orders the base rule there); it needs the model to name the wrong line with high confidence.
- m4: a bare typed Y (or Y EDP, Y 100ml, Y Elixir) resolves to YSL Y high (an exact alias, no house typed), as the base exact single-token rule does for Eros or Libre; an owner question for the resolver window.
- m5: a typed name with two flanker words keeps the first match: Creed Aventus Cologne for Her -> Aventus for Her; Creed Aventus Absolu Cologne -> Aventus Absolu.
- m6: the mixed-script page name Dior + Arabic Dior Sauvage leaves the duplicate Arabic house as a residual (link key unresolved); out of scope.
- m7: inert code on the seeded data: the `_has_arabic` guard of `_phrases_for` (an equivalent mutant: Arabic phrases never match Latin tokens) and `_generic_flanker`'s used-position bookkeeping and generic-word filter (no row can observe them on the 14 lines).
- The INC-U1 link key (url_extraction_service._link_key, under ENABLE_URL_LINK_RESULT, S97's file, not edited) moves with the data for page names naming Y, Hawas, a flanker, Libre EDT or Arabic text (M1R-9: deliberate, one key); PIN-0 pins the 12 base lines' page keys.
- An Arabic Elixir word is not in the lexicon, so it is not read; the lexicon is the one home (no second table).
- Re-verifier n1: under exact_single a two-letter alias token is also matched exactly in the lexicon arm; no row pins that a two-letter alias token (de / la / di / le) still matches within one edit (a gap already in INC-R1's suite).
- Re-verifier n3: the model-arm one-letter limit above holds for any one-letter line (for example 'Mugler B Men' and A*Men); base behaviour, measured.
- tests/test_inc_m1a_gate_rows.py (the fix-round pin file) is not black-formatted and not on the black allowlist (kept byte-identical to its RED sha).

## PROOF ON THE PHONE (owner; not done here)
After INC-M1b merges and the relay flips ENABLE_PRODUCT_RESOLVER ON on web: on the phone type the Arabic Dior Sauvage EDP and the Arabic Bleu de Chanel EDP (the WAW and the YA spelling) as a pair, then the Latin pair Dior Sauvage EDP / Bleu de Chanel EDP. Visible: the same Latin names, the same prices and the same pictures for both pairs. Backing check: the [RESOLVE] log line shows a=lexicon/high b=lexicon/high with no model call, and the saved comparison rows carry the Latin brand / name / search query. A hermetic gate is not the production proof.

## Owner steps (names only)
None to merge. The ENABLE_PRODUCT_RESOLVER flip stays the relay's, in its own window, after INC-M1b; rollback = set it false.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
