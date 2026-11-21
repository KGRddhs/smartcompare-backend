# FIX1 RULINGS INC-I2c GUARD-RECALL (S98 orchestrator, 2026-11-21 15:42 AST) - PROPOSED, items marked RELAY need the relay's word

Inputs: the GREEN head 4ab14157 (on main 022b292e); adversary 1 (recall and precision) adv/a1/INC_I2C_ADV_A1_REPORT.md, verdict DEFECTS; adversary 2 (production and identity) adv/a2/INC_I2C_ADV_A2_REPORT.md, verdict DEFECTS. Both on Opus 5.5, no box (small probes only).

## GREEN runs (box 15:16-15:41)
- RED file at the head: 43 passed.
- Comm set, 286 files, one process: 20,591 passed, 21 failed, 2 errors. All classified as not this unit's: 15 CR-byte hygiene tests and 5 golden-file digests (the worktree checks out CRLF, core.autocrlf=true), 1 event-loop timing test (test_retro_w0_4, load), 2 teardown errors in test_prompt_truth (a blocked download from openaipublic). On LF copies of the head and of main the 13 failing files give the SAME result: 1,151 passed, the same 2 errors.
- Client jest suites that read repo files: 10 of 11 pass; nativeBundle.w37 fails 4 tests on the junction's older node_modules (it reads node_modules and the lock file; no file of this unit).

## Fixes (each edits the RECALL_SET, so PICK_RECALL_RULES is bumped; no ON name exists yet, so no cost)
- F1-1 (A2-D1, major) `_perfume_domains` tests the categories BEFORE `_host`, so only the fragrance-only rows are parsed (about 80 us, no flush of the urlsplit LRU). No memo (the leaf stays stateless). L15 restated with the measured cost.
- F1-2 (A1-D2, major, C13) R1 reads the TITLE (the first text) and the knowledge-graph types only, never the source text: "EDC Store" or an everyday-carry gear title on a source no longer rescues. 0 right lost in every shape.
- F1-3 (A1-D3, major, C9b) the Arabic toilette word counts for R1 only inside the eau-de-toilette phrase (right after U+062F 0648 or U+062F 064A): toilet paper and cleaners are no longer rescued. RELAY: one parametrized E1 case of the frozen RED file (the standalone toilette word) must change to the phrase form.
- F1-4 (A1-D1, major, F2) in the second look the R1 words are not significant line words: the remaining significant words (or the one-character tokens when none remain) must be covered, and R1 words do not count toward the R3 floor. Cuts 10 of the 20 wrong Arabic cross rows, 0 right lost.
- F1-5 (C-3, A1-C3) RELAY: the second look is skipped when every significant line word is an audience word or intense (men, women, man, woman, unisex, homme, femme, him, her, boys, girls, intense). Cuts 30 of the 50 ambiguous line-only acceptances, 0 right lost in every set and shape. My recommendation: adopt.
- F1-6 (A1-M2) the R-4 list gains only unambiguous home goods, each kept only if it refuses no right bottle in the sets: the Arabic gram units, and the pairs home spray, car freshener, fabric spray, wax melt(s). Roll-on, splash, all-over spray, sachet, wipes, sanitizer, gift card, pouch, travel case, empty bottle, clone wordings and flankers stay stated limits (several are perfume forms).
- F1-7 (A2-D3, A1-M3, A2-D4) `RelevanceCall.__new__(cls, *args, **kwargs)` (the constructor protocol is kept); its docstring states that copy and pickle re-read the switch (no consumer today).
- F1-8 wording (A2-D2, A2-D5, A2-D6, A1-M4): "no I/O once source_router is imported (the web process imports it at startup)"; "pick_cache_name's only caller runs under the guard"; the cost line says the ON axis also moves brand-known names (they pay the flip round; their verdicts cannot change). CLAUDE.md section, rule line and Feature Flags pointer brought to the fixed behaviour.
- F1-9 comm set gains tests/test_price_fallback_may_decline.py (A2-D7).

## Tests
- F1-10 RELAY: a NEW fix-round test file tests/test_inc_i2c_fix1.py (the RED file stays frozen apart from F1-3's one case): rows for F1-1..F1-6, plus the five gaps adversary 1 found (X1 a look-alike host "x" + SHOP is no perfume shop; X2 R1 through an adjacent-pair join; X3 R1 never from the source text; X4 R3 reads every host, not only the first; X5 a gram unit with no number does not count). RED first: each row fails at 4ab14157 on an AssertionError only, then passes after the fix.

## Left as stated limits
- The wrong-form +34 (own-name non-bottles typed by their full name): cutting them refuses 27 own-name non-perfume rows labelled right (0 bottles).
- After F1-4 and F1-5: 20 ambiguous two-word lines at oud shops and 10 generic homme Arabic rows remain, with no free cut.

## The binding OFF walk (RELAY: its size)
- Adversary 2 measured that the image layer reads none of ENABLE_SHOP_PAGE_IMAGE, ENABLE_SHOPPING_THUMB_IMAGE, ENABLE_PRODUCT_RESOLVER and ENABLE_IMAGE_LATE_BIND (env reads over 128 mixes); they reach it only through inputs.
- Proposal: the binding walk is W1 (G x S x W x the OFF spellings + the inert configs, 46 configs, the full I2b, XB, SB and NP-X sets, 70,769 cases) on main and on the final fix head, compared; W2 (every A, B, R, L mix) only as its 1-in-20 sample on the head. Estimated about 30 to 55 minutes per tree; the mutant run about 30 minutes. They run after the fix round, in their own box slots.

## RELAY RULING ORCH-I2C-FIX1 (the relay, 2026-11-21 15:42): APPROVED as proposed
- (a) C-3: adopt the audience-words skip (F1-5).
- (b) The frozen RED file changes in exactly ONE place: the E1 case of the standalone Arabic toilette word becomes the phrase form; nothing else; the relay checks the diff with git. The standalone word goes into the fix file as a row that must not be rescued.
- (c) tests/test_inc_i2c_fix1.py, RED first; the lane may build the fix once its rows fail for the right reasons at the lane's own gate; then one line to the relay with the counts.
- (d) The OFF walk: W1 in full on main and on the final head; the A, B, R and L mixes as a 1-in-20 sample, ON CONDITION that a source-scan pin proves the image layer reads none of those four switches. Mutants and walks in their own box slots after the fix round.
- (e) The wrong-form +34 and the remaining ambiguous rows: stated limits, in the PR body with examples per C-2.
- After the fix: ONE re-verifier on the fix diff, then the PR. Lines to the relay: at most eight short lines; detail in the lane files, named in the line.
