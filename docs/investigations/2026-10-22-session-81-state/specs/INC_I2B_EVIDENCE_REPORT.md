I could not write `INC_I2B_EVIDENCE_REPORT.md`: the harness refused the .md write. I did not route around that, so the full report is below; the data files are in `C:/Users/SynAckITPC/AppData/Local/Temp/claude/cde30765822f13ce/3604e246-b00b-4f41-8d06-0ea8ac377e8e/scratchpad/s96/i2b/evidence/`.

# INC-I2b evidence round on real shop titles

## Verdict
- **No new false refuse pattern at 478a3ad8.** Over 6,800 right pairs, nothing is refused at FIX-1 that base accepts. This holds in both identity shapes and in the raw-title control (ESTABLISHED for these pairs and these label rules).
- **One right title was found by reading the labels: "CARTIER L ENVOL EDT 80ML NON REFILL".** Base accepts it; aec760b5 and 478a3ad8 refuse it with `form`. W reads "refill" but not the "NON" before it. It is one title, so by the decision rule it is a stated limit, not a defect.
- **F-A1-2 (the Intense word order) is reproduced by 58 real titles at aec760b5.** All 58 are accepted at 478a3ad8.
- **F-A1-1 (a marketing Intense) is reproduced by no real title.** All 81 titles that contain "intense" use it as a name word or as a concentration suffix, never as an adjective.
- **What FIX-1 gives up compared with GREEN:** 8 wrong pairs in the roff shape (4 titles) and 12 in the kb shape (7 titles). GREEN refused them; FIX-1 and base accept them. These are the RV1-1 and RV1-2 classes, now seen on real titles.
- **Defect proposals: none.**

## Method
- **Code points.** I made three trees with `git archive <sha> app | tar -x`, under `evidence/trees/`. The worktree was not touched; its HEAD stayed 478a3ad8.
  - Cross-check: ADV-1's `words.py` over `cases.json` on the 478a3ad8 tree reproduces `fix1/words_after.txt` byte for byte.
- **The probe (`run_point.py`).**
  - It runs with `-I -X utf8 -B`, from outside the trees.
  - It deletes every ENABLE_* variable from its own environment, then sets G, S and W in `os.environ` inside the process, before the import. Nothing was set in a shell.
  - A socket guard blocks any connection. There were 0 network attempts in every run.
  - The call is `check(identity(q, rel), (title,), ("https://<shop host>/",))`. No listing URL was used anywhere.
- **Two identity shapes.**
  - roff is today's production dict with R OFF: brand "", line = the typed text, typed = the typed text.
  - kb is a known-brand dict: brand, the derived line, typed = the query.
- **Controls.**
  - With W OFF, 478a3ad8 and aec760b5 give exactly the base verdicts: 0 differences over 9,009 pairs and both shapes.
  - On raw titles (HTML entities kept) the W results are the same. Base refuses 26 more roff pairs and 4 more kb pairs on name, because of the entity tokens.

## How the pairs were labelled
The rules are coded in `build_pairs.py`.
- **Titles:** HTML-unescaped twice, cp1252 mojibake repaired, newlines turned into spaces.
- **Brands:** 215 field spellings fold to 173 canonical keys, with 37 merged groups.
  - Spellings are folded (case, accents, "&" becomes "and", noise words dropped). Keys that match with spaces removed, or have a difflib ratio of 0.92 or more, are merged, plus a short manual merge list.
  - Vendor names standing as brands (Golden Collections, NICHE, Mass-Market, Online Warehouse, Give Me Gourmand, Oud) get their real brand from the title.
  - A trailing "by <known brand>" in the title overrides the field brand. That changed 35 products.
  - The brand text in a query is the title's own spelling when the title has one.
- **Concentration:** the `concentration` field, otherwise a phrase in the title. "Intense" directly after a phrase belongs to the label. When the field and the title disagree, the product is UNSURE.
- **Form:** my own regular expressions, independent of the guard's FORM_WORDS: tester, set, oil, refill, mini, body, other.
- **Line:** the title with the brand, concentration, generic perfume words, form, size, codes, packaging and audience words removed. "Intense" stays in the line as a flanker word.
- **Self pairs (truth RIGHT), each against the product's own title:**
  - typed "brand line conc", bare "brand line", line_only, line_only_typed;
  - typed_swap: the Intense moved to the other side of the concentration (the F-A1-2 order).
  - A title with a set, body, mini, oil, refill, tester or other form is a "wrong-form self row". It is kept out of the false-refuse count and reported apart.
- **self_x pairs (truth RIGHT):** the same product as written by another shop.
- **Cross pairs (truth WRONG):**
  - cross_conc: same line, a different concentration, typed query;
  - cross_form: a bottle query against a form listing of the same line;
  - cross_l1: flanker pairs, counted apart.
- **Arabic titles:** the title as typed, without audience words; roff shape only.

## Counts
| Item | Count |
|---|---|
| Products used | 2,388 of 2,408 (2,381 distinct titles) |
| Arabic titles | 162 |
| Right pairs | 6,800 (self 6,272, self_x 341, Arabic 187) |
| Wrong-form self rows | 1,086 |
| Cross pairs | 1,077 (concentration 123, form 199, flanker 755) |
| UNSURE | 46 |

W only acts after the base passes. Base accepts 5,125 right pairs in roff (1,310 titles) and 5,492 in kb (1,431 titles).

## Results per code point
**roff shape**

| Point | False refuses (of 6,800) | By reason | False accepts (of 1,077) | By pattern |
|---|---|---|---|---|
| 5cd93c6a | 1,675 | name 859, fragrance_word 816 | 792 | concentration 116; set 48, oil 26, mini 4, tester 56; flanker +intense 68; flanker other 474 |
| aec760b5 | 1,729 | name 859, fragrance_word 816, concentration 54 | 409 | set 3, tester 47; flanker +intense 4; flanker other 355 |
| 478a3ad8 | 1,675 | name 859, fragrance_word 816 | 417 | set 3, tester 47; flanker +intense 12; flanker other 355 |

**kb shape**

| Point | False refuses (of 6,613) | By reason | False accepts (of 1,077) | By pattern |
|---|---|---|---|---|
| 5cd93c6a | 1,121 | brand 1,097, fragrance_word 24 | 947 | concentration 119; set 86, oil 52, mini 4, tester 56; flanker +intense 73; flanker other 557 |
| aec760b5 | 1,179 | brand 1,097, fragrance_word 24, concentration 58 | 475 | set 3, tester 47; flanker +intense 4; flanker other 421 |
| 478a3ad8 | 1,121 | brand 1,097, fragrance_word 24 | 487 | concentration 2; set 3, tester 47; flanker +intense 14; flanker other 421 |

- FIX-1 removes every refusal that GREEN added and adds none.
- Wrong-form self rows accepted (roff): 738 at base, 198 at GREEN, 200 at FIX-1. At FIX-1, 133 of those are testers, 61 are sets with no set word, and 6 are other.
- In roff, W at FIX-1 refuses 296 cross pairs on concentration and 79 on form that base accepted.

## The 58 real titles that reproduce F-A1-2
All 58 were refused with `concentration` at aec760b5 and are accepted at 478a3ad8. Each comes from a query with the Intense in the other order, for example "Calvin Klein Eternity EDP Intense" against the title "Calvin Klein Eternity Intense ... EDP". The 4 Jo Malone and Hugo Man titles are kb-only.

9PM Elixir (Afnan, Parfum Intense); Supremacy Not Only Intense (edP; Extrait); Aigner No 1 Intense (edT); Aigner No.1 Intense (EDT); Club De Nuit Intense Man (edP 200ml); Club De Nuit Intense (edT 105ml); Club de Nuit Intense (Parfum 150ml); Bentley Infinite Intense; Bentley Momentum Intense; Bentley Intense; Jacques Bogart Silver Scent Intense; Boss Alive Intense; Hugo Man Intense EDP 125ml; Burberry Her Intense EDP; Calvin Klein Eternity Women Intense 2022; CK Eternity Aromatic Essence Intense Parfum; CK Eternity Intense (Women EDP); CK Eternity Intense (Men EDT); CK Euphoria Intense (Women EDP); CK Euphoria Intense (Men EDT); CK Women Intense; Dior Homme Intense edP; Tiffany Rose Gold Intense; Tiffany & Co. Intense EDP; D&G Q Intense; D&G The Only One Intense; D&G The One Intense; Davidoff Cool Water Intense For Her; Davidoff The Game Intense; Ferragamo Intense Leather EDP 50ml; Ferragamo Pour Homme Oud Intense; Floris Cherry Blossom Intense; JPG Ultra Male Intense; JPG Scandal by Night Intense; Givenchy L Interdit Absolu edP Intense; Gucci Bloom Intense; Gucci Flora Gorgeous Gardenia edP Intense; Gucci Guilty Pour Femme Intense; Gucci Guilty PH Intense; Mon Guerlain edP Intense; Drakkar Intense; Terre D'Hermes Eau Intense Vetiver; L'Eau D'Issey Intense; Jo Malone Dark Amber & Ginger Lily Intense; Jo Malone Jasmine Sambac & Marigold Intense; Jo Malone Tuberose Angelica Intense; Lacoste L'homme Intense; Lattafa Teriaq Intense; YSL HOM INTENSE EDP; YSL Libre Intense; MANCERA INTENSE CEDRAT BOISE EDP; Mancera Red Tobacco Intense; Mercedes-Benz Intense; Montale Intense Cafe; Trussardi Courtyards of Castello Sforzesco EDP Intense; Trussardi Le Opere Di Palazzo Reale EDP Intense; VALENTINO UOMO EDP 50ML INTENSE 16.

The full titles are in `major2_titles.txt`.

## What FIX-1 gives up compared with GREEN
- **roff, 8 pairs, 4 titles:** Tiffany Rose Gold Intense Natural Spray EDP; Floris Cherry Blossom Intense Unisex EDP; Gucci Bloom Intense Natural Spray EDP; MANCERA INTENSE CEDRAT BOISE EDP. FIX-1 reads the Intense as generic because the word after it (natural, unisex, cedrat) is not on its list of words that can follow a flanker Intense.
- **kb adds 4 pairs:** MANCERA INTENSE RED TOBACCO (2 pairs), and 2 RV1-1 rows. In the RV1-1 rows a typed "Mon Guerlain EDP Intense" or "Gucci Flora Gorgeous Gardenia EDP Intense" accepts the plain EDP bottle.
- **Option, not a defect:** add "natural" and "unisex" to that list of following words.
  - Measured on a scratch copy of the tree, it refuses 6 more wrong pairs per shape (the Tiffany, Gucci Bloom and Floris titles).
  - It refuses no new right pair in 9,009, and changes no verdict on ADV-1's `cases.json`.
  - I did not re-run the frozen corpus. The change would also move PICK_GUARD_RULES, so the E19 / E22 pins would need updating. This one is for the orchestrator to decide.

## Wrong pictures W still accepts at 478a3ad8, top patterns
1. Tester listings: 180 pairs (47 cross, 133 self). W has no tester word, and whether a tester picture is wrong is arguable.
2. Bundles written as "+"-joined contents with no set word: 28, e.g. "The Woods Collection Natural Bloom EDP 100ml + 5ml".
3. Self rows where the form word is in the query, so W skips it: 17 (Dr. Vranjes "2 refills", "Fragrance Mist").
4. "(100ml + 15ml + Funnel)" bundles: 15.
5. "with Cufflinks" (Club De Nuit 2024 Limited Edition): 5.
6. "Bukhoor Elixir EDP": 4. This one is my label error; the EDP is the right product.
7. "Intense Natural Spray" flankers: 4.
8. "Le Parfum Intense ... edP" read as Parfum Intense plus EDP, so a typed EDP still accepts it: 3. GREEN behaves the same.
9. "Intense Unisex": 2.
10. "Intense Cedrat Boise" (Intense before the name): 2.
11. A shoe titled "Clarks Cologne ... Boots": 2.
12. "Intensely" (not the word intense): 1.
13. kb only: All Over Spray body sprays, 34.
14. kb only: oud chips sold by grams or tola, 40.
15. kb only: bukhoor, 6.
16. kb only: dehn oil, 4.
17. kb only: air freshener, 4.
18. kb only: "Intense Red Tobacco", 2.
19. kb only: the RV1-1 sibling, 2.
20. kb only: a form word typed in the line (mist), 3.

Flankers that differ by other words are counted apart, outside what W was built for: 355 roff and 421 kb pairs remain, from 474 and 557 at base.

## Arabic titles
- 162 titles give 187 self pairs.
- The verdicts are identical at all three points: 175 refused with `fragrance_word` and 12 accepted.
- Base refuses most of them because the title has no perfume word. W changes no Arabic verdict.

## Hand check
60 pairs (30 self, 30 cross), drawn with a fixed random seed; judgements in `handcheck.json`.
- **Self:** 28 correct, 2 UNSURE ("Taif Lighter" and "Fourage Oud" may not be perfumes), 0 errors.
- **Cross:** 27 correct, 1 UNSURE ("CK One (White)"), 2 errors. Both are flanker-pair mistakes: a title cut short ("...EXTRAORDINAIRE E") and a product-code fragment ("TMF").
- **Label error rate:** 2 of 60 (3.3%) definite, plus 3 of 60 (5%) UNSURE.
- **Wider reviews:**
  - I read all 247 wrong-form titles that W refuses. That found one label error (the Cartier NON REFILL bottle) and 2 UNSURE ("1 Perfume Set").
  - I read all 16 right-labelled titles that contain a FORM_WORDS word. 11 are really body or home products my rules missed (hand wash, body wash, lotion, mist, incense burner). These cannot hide a refusal, but they would have been missed wrong pictures had they been labelled wrong.
- The flanker labels are the least accurate.

## Stated limits
1. "CARTIER L ENVOL EDT 80ML NON REFILL" is refused `form` with W ON; isolated.
2. No tester word: 180 tester rows are accepted.
3. Missing words, so wrong pictures pass: "+" bundles, Funnel bundles, Cufflinks, GIFTBOX written as one word, All Over Spray, oud chips by grams or tola, dehn, bukhoor, air freshener, a shoe titled "Cologne".
4. FIX-1's position rule: Intense followed by Natural Spray, Unisex or a name word reads as generic (4 titles). The option above recovers 3 of them.
5. RV1-1 on real titles: 2 kb pairs.
6. "Le Parfum Intense ... edP" is accepted for a typed EDP; GREEN does the same.
7. W has no effect on the Arabic titles in this export.
8. Limits of the method:
   - The self queries are built from the title's own words, so a form word that is part of the name is always typed and exempted. Only line_only models a user typing a shorter name.
   - Two identity shapes, and no resolver was run.
   - Only `check()` and `words_reason_for` were tested; no Serper, no shop-tier stamping, no cache.
   - These are KB shop titles, which rarely carry marketing words; Serper image titles were not tested.
   - The label error rates above apply to every number.

The full brand alias map is in `alias_map.txt` and `brand_alias_map.json`. All paths below are under `C:/Users/SynAckITPC/AppData/Local/Temp/claude/cde30765822f13ce/3604e246-b00b-4f41-8d06-0ea8ac377e8e/scratchpad/s96/i2b/evidence/`:
- `pairs.jsonl`
- `products.jsonl`
- `verdicts/`
- `analysis_on.json`
- `tables.txt`
- `fa_patterns_roff.json`
- `fa_patterns_kb.json`
- `handcheck.json`
- `major2_titles.txt`
- `alias_map.txt`