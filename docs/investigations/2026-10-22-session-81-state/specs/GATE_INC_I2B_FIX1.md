# INC-I2b FIX-1 gate (S96 orchestrator, 2026-11-17 about 05:00 AST)

The GREEN head is aec760b5, on fix/inc-i2b-guard-words-shop-tier (not pushed).
- ADV-2 (the shop tier and production) returned SOUND with six MINORs.
- ADV-1 (the words) returned NOT_READY with two MAJORs and five MINORs. See adv_a1/INC_I2B_ADV_A1_REPORT.md and adv_a1/probes/words_out.txt.

Both MAJORs refuse a RIGHT picture while W is ON, the state the flip is meant to reach. They are fixed in this round. Every MINOR becomes a stated limit, except FX-4 (a cheap doc fix).

## FX-1 (F-A1-1): a marketing "Intense" is not a flanker
Today `_conc_scan` marks any intense as free unless the next token is fragrance or perfume. That refuses "... 100ml - Long Lasting, Intense Scent", "... Intense Long Lasting Fragrance for Men", "... 100ml Intense and Long Lasting", "Lattafa Khamrah ... Sweet, Intense & Long Lasting" and "Dior Sauvage EDT 100ml, Intense Woody Scent".

**The rule:** a free intense counts only in a POSITIONAL slot. That is, the intense is the flanker word of the name: it is not a phrase suffix (those are folded already), and the next token (after fold_numero) is one of:
- (a) the end of the tokens;
- (b) the first token of any CONC_PHRASES phrase;
- (c) a size token (digits with or without a ml / oz unit, in whatever form the tokenizer gives, e.g. 100ml, 100 ml, 3.4 oz);
- (d) one of the closed words: spray, for, pour, men, women, homme, femme, edition, by.

Everything else (an adjective, a conjunction or a noun after it) is generic. Keep INTENSE_GENERIC_NEXT as it is, or retire it, whichever keeps the code smaller; the positional test decides.

**Constraints:**
- Every frozen RED row stays green with the frozen file unchanged (sha c206cfd2...). That includes E4 ("YSL Libre Intense EDP 90ml" refused: intense before EDP is slot b), the "Dior Homme Intense" rows, E4b and E11 ("Dior Sauvage Intense Eau de Parfum" at A).
- If a frozen row needs a refusal that the positional rule does not give, STOP and report it as blocked with the row id. Never edit the frozen file.

## FX-2 (F-A1-2): an Intense typed together with a concentration matches either word order
"Intense EDP" reads {EDP} plus a free intense, while "Eau de Parfum Intense" reads {EDP Intense}, so a typed "Valentino Born in Roma Intense EDP" refuses "... Eau de Parfum Intense 100ml".

**The rule:** in rule 2(b), when `INTENSE_WORDS & ident.query_words` is not empty, strip a trailing " Intense" from every label on BOTH sides before the disjoint test. Include the "Parfum Intense" phrase label, which becomes "Parfum". Without a typed intense, 2(b) is unchanged: a typed EDP still refuses "EDP Intense" (I-9).

## FX-3: the new rows (RED first)
A new file tests/test_inc_i2b_fix1.py: hermetic, ASCII, in the RED file's style, with `_verdict`-style helpers copied rather than imported if the RED file does not export them. Rows:
- **X1..X5:** the five F-A1-1 titles (typed and bare as in the report), with W ON: accepted (None).
- **X6..X11:** the six F-A1-2 pairs, with W ON: accepted.
- **X12 (a control that must stay refused):**
  - typed "Dior Homme EDP" vs "Dior Homme Intense Eau de Parfum 100ml" -> concentration;
  - bare "Dior Homme" vs "Dior Homme Intense 100ml" -> concentration;
  - typed "Dior Homme EDP" vs "Dior Homme Eau de Parfum Intense 100ml" -> concentration (no typed intense, so no stripping).
- **X13:** typed "Born in Roma Intense EDP" vs "Valentino Born in Roma EDT 100ml" -> still refused (EDT vs EDP after stripping).

Run the file at aec760b5 BEFORE the fix: X1..X11 must FAIL on AssertionError; X12 and X13 (controls) pass at both.

## FX-4: the docs, with no code
Update the CLAUDE.md line that lists the old GUARD_SET (about line 728) to the current GUARD_SET text.

## Gates
- **Tests to run:** the RED file, the addenda, tests/test_inc_i2a_picture_not_cut.py, the fix1 file, test_ci_gates, test_behavior_dimension_translation, test_inc_r1_seam. Add every test file that imports or source-scans app/services/image_relevance.py, image_service.PICK_GUARD_RULES or the CLAUDE.md image rules (find them with grep). Compare against the base records in harness/base_records/5cd93c6a.../: new failures = failing at the head but not at base.
  - Do NOT re-run the whole 499-file union: only image_relevance.py and CLAUDE.md change in this round (and the moved pin in the I2a test file).
- **PICK_GUARD_RULES** moves (the function bytes change). Recompute it after black, update the literal and the E22 moved pin in tests/test_inc_i2a_picture_not_cut.py, and confirm E19 passes. Run the digest determinism check in three fresh interpreters (PYTHONHASHSEED 0, random, 777).
- **Re-measure the corpus** (the frozen corpus fixture, S ON typed and untyped) with the RED report's method, and report the false accepts and false refuses before (65 -> 7 typed, 27 untyped; false refuses 22) and after. Accept only if false refuses go DOWN or stay the same and false accepts rise by at most 3. Also re-run ADV-1's probes/words.py over probes/cases.json at the new head, and list every row whose verdict changed.
- **Lint:** black on the allowlist, and ruff E9,F63,F7,F82 on the touched .py files. Add the fix1 file to .github/black-clean-paths.txt.
- **Commit:** a NEW commit on the same branch, never an amend, never --no-verify, never a push.
  - Subject: "fix(images): INC-I2b FIX-1 a marketing Intense is not a flanker; a typed Intense matches either word order".
  - A body of 2-4 lines plus the trailer `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
  - Stage by name only.

## The re-verifier (one, the ADV-1 lens, on the delta)
- Confirm F-A1-1 and F-A1-2 are fixed, through probes beyond the X rows: other marketing adjectives; "Intense" at the end, before a size, and before Spray / pour homme; Arabic titles unchanged.
- Confirm no NEW false refuse on probes/cases.json, and list each new false accept with a judgement.
- Confirm the digest is determined, and that the OFF identity is unchanged (W unset gives _check_base).
- SOUND / NOT_READY. A MINOR becomes a stated limit.

## The stated limits added to the PR body by this gate
- F-A1-3 (I-14 needs a known brand), F-A1-4 (Parfum de Marly), F-A1-5 (the residual words), F-A1-6 (the Arabic form and concentration words, with the corrected wording), F-A1-7 (the helpers not hashed, L10).
- A2-1..A2-6 (the W flip moves the pick names again; the merge resets the L cache reading; IMG_SHOP lines prove a candidate, and IMG_LATE bind lines prove a shown picture; the plain-word filters; key names come from the shop JSON; the first src only).
