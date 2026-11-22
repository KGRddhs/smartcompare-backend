## INC-M1b MATCHER FOLD (`ENABLE_MATCH_FOLD`, default OFF, read per call)

This is the matcher half of INC-M1. The sources:
- the spec, INC_M1_SPEC.md section 2, as amended by RULINGS_INC_M1b M1bR-1..M1bR-14 and the RED gate GATE_INC_M1b G-1..G-7;
- the relay rulings ORCH-M1B-A and ORCH-M1B-B;
- three narrowing rounds:
  - FIX1 (FX1-1..FX1-7, FA-1..FA-6, the RED2 gate R2-1..R2-6, ORCH-M1B-C, ORCH-M1B-D);
  - FIX2 (ORCH-M1B-E, FX3-1..FX3-5, RG-1..RG-5, FG2-1..FG2-4);
  - FIX3, the last (ORCH-M1B-F, FX4-1, RG4-1..RG4-5, FG3-1..FG3-4).

Every change sits behind the NEW flag `ENABLE_MATCH_FOLD`. It is default OFF and read per call; with it OFF every verdict is unchanged.

**Merged, NOT yet proven.** A hermetic accept count is not the production proof. The switch stays off after the merge, under the HARD FLIP RULE (section 11).

### 1. What the flag does (ON; SELECTION mode and fragrances only)

The category is the one after the `_selection_match` "other" re-inference. EXACT (`is_exact_match`), BACKSTOP (`_backstop_identity_ok`, `is_price_showable`) and every other category are unchanged.

1. **Brand alias fold** (`_m1b_fold_cores`, in `_descriptor_selection_verdict`).
   - A group of `_BRAND_ALIAS_GROUPS` (unchanged), or of the private `_M1B_EXTRA_ALIAS_GROUPS` (MFK, Maison Francis Kurkdjian, Francis Kurkdjian), folds only when the QUERY core holds one of its members.
   - Every member then present on a side becomes one canonical token.
   - The house-only guard refuses the fold when the folded query core holds house tokens only, unless the query names a seeded line whose whole name is among the title's words.
2. **Houseless distinctive line.** A title may omit the house of a seeded line the query names when:
   - it carries every token of a distinctive alias form of that line;
   - and it carries no word of that house's alias group.
3. **Single-concentration default** (`_vd_candidate_missing_query_axis`, SELECTION only). A title with no concentration counts as the query's for the `single_concentration` lines (Aventus, Layton, Khamrah, Hawas) when:
   - the query's concentration is the line's one concentration;
   - and the title names no flanker of the line.
4. **Narrowing guards.** Each one refuses rules 1 to 3 for a pair, so the base verdict stands. None can add an accept.
   - M1bR-14, FA-1, FA-3, FX3-3 and FX4-1 (`_m1b_excluded`, `_m1b_concentration_phrases`):
     - the existing sample, floor and form predicates, the 30 ml floor (unless the size is typed), and `is_counterfeit_listing`;
     - a pack count other than the query's;
     - a `_FORM_NOISE_TOKENS` word other than spray that the query lacks;
     - and (FX4-1) a concentration-phrase flanker named on one side only: Eau Fraiche, Le Parfum, a bare Parfum beside another concentration label, or Eau de Cologne.
   - FX1-2 (`_m1b_brand_other_house`, `_m1b_brand_other_line`): the listing's own brand field names another house, by the whole-form test of R2-1.
   - FX1-4, FX2 and FX3-1 (`_m1b_gender_ok`): a title stating a gender the query does not state is refused. A query holding a women pronoun (`_M1B_WOMEN_PRONOUNS`) needs a candidate that states a women word.
   - FX3-2 (`_m1b_gender_side`, the fold only): a query that states a gender side folds only onto a candidate that states the same side.
   - FX1-3 (`_m1b_query_names_flanker`) and FX3-4 (`_m1b_title_names_flanker`): a flanker named by the query, or named by the title but not the query, takes no rule.
   - FA-4 and FX3-5 (`_m1b_fold_refused`): no fold when the query names two houses, including a seeded house alias whose words are all among the query's raw words.

The seeded lines come only from the read-only `product_resolver.seeded_line_profiles()`:
- immutable `SeededLineProfile` records, built per call from the lines `_load_lines` cached;
- no memo of their own, and no file, model, network or spend call;
- read lazily, up to twice per verdict.

With the flag OFF, no new code runs and the accessor is never read (the 32 fold-OFF walk rows prove it).

### 2. The three narrowing rounds

- **FIX1** closed:
  - B1: the store's brand field let another house look houseless;
  - B2: a "for Her" query got the base line;
  - M1: the houseless rule had no gender condition;
  - 59 flag-mix wrong pairs.
  - It also added the brand matrix: every brand-taking entry, with no brand, a same-house brand and an other-house brand.
- **FIX2** closed:
  - B-1: a women-pronoun query took the men's line;
  - B-2: a gender-stating query folded onto the other twin's gender-free title (819 pairs over 12 twin lines);
  - B-3: pack counts;
  - B-4: Y flanker titles;
  - and FG-3.
- **FIX3** closed:
  - B-EF: a flanker named by "Eau Fraiche" taken for the base line, as in "Yves Saint Laurent Y EDT", the resolver's own query for a typed "YSL Y", against "YSL Y Eau Fraiche EDT 100ml";
  - the real-line m-b, as in "Yves Saint Laurent L'Homme" against "YSL L'Homme Le Parfum Eau de Parfum 100ml".
  - After FIX3, only class (a) blocks (THE FINAL EXIT): a widening, a broken OFF identity, a red frozen row, or B-EF and m-b not closed.

### 3. Files

- `app/services/price_service.py`, the INC-M1b block only:
  - the GREEN names: `match_fold_enabled`, `_m1b_core_words`, `_m1b_raw_words`, `_m1b_compile_groups`, `_m1b_fold`, `_m1b_profiles`, `_m1b_named_lines`, `_m1b_house_words`, `_m1b_distinctive_forms`, `_m1b_fold_cores`, `_m1b_concentration_default`, `_m1b_excluded`, and the constants `_M1B_CANON_PREFIX`, `_M1B_FOLD_GROUPS`, `_M1B_EXTRA_ALIAS_GROUPS`;
  - the FIX1 helpers: `_m1b_query_names_flanker`, `_m1b_line_house_forms`, `_m1b_brand_other_house`, `_m1b_brand_other_line`, `_m1b_gender_ok`, `_m1b_seeded_house_beside`, `_m1b_fold_refused`, and `_M1B_FORM_NOISE_KEPT`;
  - the FIX2 helpers: `_m1b_title_names_flanker`, `_m1b_gender_side`, and `_M1B_WOMEN_PRONOUNS`;
  - the FIX3 helper: `_m1b_concentration_phrases`.
  - No memo beyond the two bounded tokenizer memos (GG-3).
  - Four base functions gain the gated step and keep their flag-OFF behaviour: `_descriptor_selection_verdict`, `descriptor_verdict`, `_descriptor_axis_mismatch` and `_vd_candidate_missing_query_axis`.
- `app/services/product_resolver.py`: the read-only `seeded_line_profiles()` accessor and `SeededLineProfile`.
- `CLAUDE.md`: the flag pointer on the Feature Flags line, and the INC-M1b block (guards, limits, the ROLLOUT and HARD FLIP RULES).
- `tests/test_inc_m1b_match_fold.py` (428 rows, LF; sha256 90ec2b3f...):
  - frozen at the RED gate with 175 rows;
  - rows added only at RED2 (198), RED3 (34) and RED4 (21; 215 lines added, 0 deleted);
  - plus the two relay-ruled stated-limit commits.
- No other file.
- Rebased onto main a999d509 (#424 to #427):
  - the INC-M1b patch is identical in content;
  - #427's price_service hunks (lines 15138 to 15617) touch no matcher hunk;
  - the CLAUDE.md conflicts are resolved with both sides kept.

### 4. The RED file at the FIX2 code and at HEAD

| tree | result |
|---|---|
| FIX2 rebased (47c2b985), RED4 rows in | 11 failed (exactly the 9 new GUARD and 2 E2E rows, AssertionError only), 416 passed, 1 xfailed |
| HEAD (FIX3) | 427 passed, 1 xfailed (the Lacoste stated limit, Q3) |
| HEAD, `ENABLE_MATCH_FOLD=true` exported | 427 passed, 1 xfailed |

```
[pyt] tag=inc-m1b-fix3-red-at-47c2b985 start=2026-11-22 02:47:59 end=2026-11-22 02:48:39 elapsed=39s bound=600s status=FAIL rc=1 | 11 failed, 416 passed, 1 xfailed
[pyt] tag=inc-m1b-fix3-head start=2026-11-22 02:48:40 end=2026-11-22 02:49:18 elapsed=38s bound=600s status=OK rc=0 | 427 passed, 1 xfailed, 1 warning in 37.52s
[pyt] tag=inc-m1b-fix3-head-envon start=2026-11-22 02:49:19 end=2026-11-22 02:50:05 elapsed=46s status=OK rc=0 | 427 passed, 1 xfailed
```

### 5. Flag OFF identity

- HEAD against main a999d509, every value byte-identical: 160,768 values (ALL digest 19c4a859b907328b on both trees). They cover the brand matrix, the RED2 and RED3 pairs, both flag-mix probe sets, the fg3 set and the twin space.
- The flag-OFF bits of the round-3 sets are equal: concflank, twins2, fb4hunt, B2, ef, p3, p3big and the Le-line set.
- The 32 fold-OFF walk rows pass.

### 5b. The final re-verification (one Opus re-verifier on a7b26001, under THE FINAL EXIT): SOUND

- No class (a) finding.
- No widening against FIX2: 0 of 10,607,758 flag-ON cells.
- Flag OFF identical to main a999d509: the offid space with the brand dimension (283,020 pairs x 12 fields, digest 984363bea35855d1 on both trees), the 160,768 values above, and the RED4 rows (1,260 values).
- The RED file at HEAD: 427 passed, 1 xfailed, also with the flag exported. At main: 78 failed (AssertionError only), 350 passed.
- Cost over nine rounds: typed 2.51x to 2.63x, resolved 2.59x to 2.95x.
- Its minors are in sections 6 and 10 and in the CLAUDE.md block (doc commit 71859cd9).

### 6. Probe counts (flag ON against OFF at HEAD; R4 truth)

| set | new accepted-wrong at FIX1 | at FIX2 | at HEAD |
|---|---|---|---|
| walk pairs | 0 | 0 | 0 |
| brand matrix, 30 mixes | 0 (387 at 9ef39f6c) | 0 | 0 |
| first flag-mix probe set | 1 | 1 | 1 (Lacoste, Q3) |
| probe set 2 / fg3 | 38 / 13 | 0 / 1 | 0 / 1 (Lacoste) |
| twin space | 819 | 0 | 0 |
| Eau Fraiche set (ef) | 255 | 255 | 0 |
| concentration flankers on real lines (concflank) | 1,104 (strict; plain 1,125) | 1,032 | 60 (limit 0) |
| FG-1 space part (b) / reprobe B2 / p3 / fb4hunt | 345 / 76 / 148 / 16 | 45 / 18 / 3 / 16 | 0 / 0 / 0 / 0 |

- **No widening:** HEAD accepts nothing the FIX2 code (85098c45) rejects. FIX2 accepted nothing FIX1 rejects. Both counts are 0 on every set.
- **Right accepts lost (the ruled costs, all back to the base verdict that production gives today):**
  - FIX2: 2,036 on FIX2's sets; the round-3 re-verifier measured 77 more on p3 and 93 on p3big (GFOLD, PRONW, and YFLANK 2: "Yves Saint Laurent Y Parfum" vs "YSL Y Le Parfum 100ml"), real corpus titles among them (limits 18 and 19);
  - FIX3: 44 pairs on Le-named lines (limit 21).
- **Right gains kept:** the walk 53 of 53; the first set 30 of 30; fg3 10 of 10; probe set 2 36 of 39; the twin space 1,134 of 1,827.

### 7. Mutants

- **FIX1 code, 38 mutants:** 35 killed; MB1 and MB3 are equivalent; MB5 survives (limit 16).
- **FIX2 code, 20 mutants:** 17 killed; FX2m_only is equivalent; FB4 survives (limit 20).
- **FIX3 code, 12 mutants: 9 killed**, each on an AssertionError:
  - FX4-1's parts (i), (ii) and (iii), and the symmetry;
  - OWN_HIM and OWN_S1 (the RED4 pins);
  - M_PRONW, M_GFOLD and M_FA4RAW.
- **Survivors:**
  - FB4 (limit 20) and MB5 (limit 16), all right;
  - M_IV, part (iv) Eau de Cologne: a test gap (limit 22).

### 8. Comm set, CLAUDE.md readers, client fences, lint

- **Comm list** re-derived at HEAD: 347 files, including the test files of #424 to #427.
  - FIX3 ran chunks 07, 09 and 13, the #424 to #427 set (641 passed) and the six CLAUDE.md readers (510 passed).
  - branch-only-new against main a999d509 is EMPTY; the 2 known cold-cache test_prompt_truth ERRORs appear on both trees.
  - FIX1 ran the full list: branch-only-new EMPTY.
- **Client fences:** the 20-suite union by path. Only the 4 accepted `config/nativeBundle.w37` drift nodes fail.
- **Lint:** ruff E9/F63/F7/F82 is clean; default ruff equals the base set; py_compile is OK; the hook passed.

### 9. Cost (gate A1)

Best of 5 warm passes over the 248 walk pairs, three rounds:
- `_selection_match`: typed 2.61x to 2.65x, resolved 2.68x to 2.77x (the FIX2 code on the same box in the same minute: 2.52x and 2.75x);
- the ten walk checks: 1.06x to 1.11x;
- no added accessor read.

### 10. Stated limits (each with its example)

0. FIRST, by ruling ORCH-M1B-G: the descriptor-identity remainder of m-b. m-b counts as closed at the descriptor's resolution, and what is left is a stated limit.
    - The descriptor keeps the raw words as a set with no word order. A wrong title whose descriptor is byte-equal to a right title's is accepted as that right title.
    - Examples: "Giorgio Armani Code" vs "Armani Code Parfum Eau de Parfum 100ml" (the same descriptor as "Armani Code Eau de Parfum 100ml"); "Jean Paul Gaultier Le Male Le Parfum" vs "JPG Le Male Parfum 100ml".
    - Measured: 60 cells per mix left on the real-line set (from 1,032), 72 on the Le-line set (from 432). Every other set is 0.
    - The FIX2 code accepted them too; production rejects them today. INC-M1c (word order in the descriptor).
    - The final re-verifier re-measured the same counts and found, for each of the 132 pairs, a right twin with an equal descriptor.
1. Size omission (M1bR-6): "DIOR Sauvage Eau de Parfum Spray" under a sized query stays rejected.
2. House-only queries (M1bR-4): "Dior Homme EDP" vs "Christian Dior Homme EDP 100ml" keeps the base verdict.
3. A group named by the title alone is not folded: "Libre EDP" vs "YSL Libre EDP 90ml" stays rejected.
4. Non-distinctive lines (Libre, Y, Eros, Tygar alone, Hawas) take no houseless rule.
5. Minis, travel sizes, testers, samples, gift sets, refills, body and hair products, other pack counts and dupes take none of the rules.
6. A typed-size travel spray across a spelling difference is not recovered: "Christian Dior Sauvage EDP 10ml Travel Spray" under "Dior Sauvage EDP 10ml".
7. G-2 and R2-4: a title stating the line's own gender under a gender-free query takes no rule: "Rasasi Hawas for Men 100ml".
8. The restated-gender titles keep the base verdict:
   - "YSL Y EDP 60ml for Men" and "YSL Libre Eau de Parfum for Women 3 oz";
   - also "YSL Y Le Parfum 100ml for Men" under the Y Le Parfum queries.
9. Q3: "Lacoste L.12.12 Montblanc EDT 100ml" under "Lacoste L.12.12 Blanc EDT" is still accepted. "YSL Mon Paris EDP 90ml" is not gained.
10. GG-2 and m1: the accessor serves the lines `_load_lines` last validated (an edit is seen at the next load, a reset or a restart).
11. m3: the counterfeit check reads sorted words, so its phrase keywords cannot match there.
12. One-member house titles and two-letter spellings:
    - a word naming a house by one alias-group member counts as that house. Example: the WooCommerce path picks "La Vie Est Belle EDP 100ml" with the store brand "Paris Corner" under "Lancome La Vie Est Belle EDP";
    - CK, CH, TF, MJ and DG never fold.
13. A flanker is "named" when every word of its phrase is a word of the text. This can only refuse more often.
14. Arabic-typed queries name no line; every Arabic corpus title is unchanged.
15. The owner's two identity cases (ORCH-M1B-A) are INC-M1c.
16. FG-1 (MB5): "Creed Aventus Her EDP" vs "Creed Aventus for Her 75ml" keeps the base verdict. Over 2,728,800 pairs per mix, MB5 accepts 1,330: 1,260 right, 70 unclear, 0 wrong.
17. m-b and B-EF (concentration-phrase flankers): closed by FX4-1 (ef 255 to 0, Eau de Cologne included; FG-1 (b) 45 to 0; B2 18 to 0; p3 3 to 0; fb4hunt 16 to 0). What is left is limit 0.
18. FX3-2 cost: a query that states a gender side no longer gains a gender-free title in another house spelling.
    - "Giorgio Armani Acqua di Gio Pour Homme EDT" vs "Armani Acqua di Gio EDT 100ml";
    - also on real corpus titles: "Dior Sauvage EDP for Men" vs "Christian Dior Sauvage EDP 60ml".
    - Measured: 318. INC-M1c.
19. FX3-1 cost: a women-pronoun query takes no rule for a title stating no women word, also on women's and unisex lines.
    - "Dolce Gabbana Light Blue Her EDT" vs "D&G Light Blue EDT 100ml";
    - "Lattafa Khamrah for Him and Her EDP" vs "Khamrah EDP 100ml".
    - Measured: 1,718 on synthetic sets. INC-M1c.
20. FB4 (FG2-1): with FX3-1, PRONW refuses the frozen "for Her" rows first, so the mutant without FX1-3 survives.
    - Its extra accepts are all right: 290 per mix over the FG-1 space ("Creed Aventus for Her EDP" vs "Creed Aventus Women 75ml") and 312 on the flanker-query set.
    - On the B2 set the count is 0, where FX4-1 now refuses "Emporio Armani Stronger With You Parfum EDT" vs "Stronger With You EDT 100ml".
    - FX1-3 stays.
21. FX4-1 cost: Le Parfum is read as both words present, so a line whose name holds "le" (Le Male, Le Beau, Le Gemme Tygar) beside a spelled-out Eau de Parfum names it.
    - Example: "Jean Paul Gaultier Le Male EDP" vs "JPG Le Male Eau de Parfum 100ml" keeps the base verdict.
    - Measured: 44 lost. The walk keeps its 53 gains.
22. Test gaps:
    - no RED row pins FX4-1 part (iv), Eau de Cologne; the mutant without it re-opens 15 ef pairs per mix ("Versace Eros" vs "Gianni Versace Eros Eau de Cologne 100ml");
    - no row pins part (iii)'s Eau de Parfum exception either: the mutant without it passes the RED file and refuses "Dior Sauvage EDP" vs "Christian Dior Sauvage Eau de Parfum EDP 100ml" (a right accept at HEAD); no measured set holds such a title.

### 11. ROLLOUT RULE, HARD FLIP RULE, proof on the phone

- **ROLLOUT RULE (FA-5):** flip `ENABLE_MATCH_FOLD` together with `ENABLE_PRICE_NOT_LOST` ON only after PC1 closes the scs:8235 converted-park overwrite, or with `ENABLE_GENUINE_PRICE_PRIORITY` ON.
- **HARD FLIP RULE (ORCH-M1B-E 5):** `ENABLE_MATCH_FOLD` stays off after the merge. It is put to the owner only:
  - after a real-title evidence round (the flag on against off on stored real titles, with no more wrong accepts on than off);
  - and with the stated limits above on the owner's page.
  - and not before the descriptor-identity remainder (limit 0) is closed, or the real-title evidence round shows none of it (ORCH-M1B-G).
  - Each step gets a dated ledger line, names only.
- **Nothing to set at the merge:** the flag is OFF on web (not set), and the merge changes no verdict.
- **Proof on the phone,** after the flip, by the relay with the owner at the phone:
  - compare **YSL Libre EDP vs MFK Baccarat Rouge 540 EDP**, then **Creed Aventus vs Lattafa Khamrah**;
  - no mini, travel, tester, multipack, hair, other-house, other-gender or flanker listing may be the shown price.
- **Rollback:** unset `ENABLE_MATCH_FOLD` (read per call, immediate for new responses).
- Until the phone shows it: merged, NOT yet proven.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
