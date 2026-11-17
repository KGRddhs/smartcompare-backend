# INC-I2b FIX-1 report (S96 main lane, 2026-11-17 04:31-05:05 AST)

Gate FIX1_INC_I2B.md, the ADV-1 report and probes, the GREEN / RED reports, rulings I-9 / I-13 / I-14 and the common brief were read in full.

## Commit
- 478a3ad88c9c7f335d041ac1ab4fa962ecc21137 on fix/inc-i2b-guard-words-shop-tier, parent aec760b5; a NEW commit (no amend, no --no-verify, not pushed). The hook ran: ruff "All checks passed!", black "2 files would be left unchanged".
- Subject: fix(images): INC-I2b FIX-1 a marketing Intense is not a flanker; a typed Intense matches either word order. Body 4 lines + Co-Authored-By: Claude Opus 5.5.
- Staged by name: app/services/image_relevance.py, app/services/image_service.py, CLAUDE.md, .github/black-clean-paths.txt, tests/test_inc_i2b_fix1.py. git status --short after: empty.
- git fetch origin main: origin/main == 5cd93c6aaa4e80e4b0ab36a43e6fa1f657d797c9 (did not move): no merge; head = the fix commit.

## The change
- FX-1 (_conc_scan, else arm): a free-standing intense sets free only when the next token (after fold_numero) is the end, the first token of any CONC_PHRASES phrase, SIZE_TOKEN or an all-digit token (100ml / 100 ml / "3.4 oz" -> 3 4 oz), or one of spray, for, pour, men, women, homme, femme, edition, by. The closed words are an inline set literal INSIDE _conc_scan, so they are in the hashed GUARD_SET source (a new module table would not be: the frozen E19 table list cannot grow).
- INTENSE_GENERIC_NEXT is kept (the frozen E19 reads it through _need, so retiring it would fail E19) and is no longer read; its comment says so.
- FX-2 (_words_reason): when INTENSE_WORDS & query_words is not empty, a trailing " Intense" is removed from every label on both sides (title labels and query_conc) before the 2(b) disjoint test ("Parfum Intense" -> "Parfum"). Without a typed intense 2(b) is unchanged.
- Docstrings: the module docstring (flanker intense), _conc_scan and _words_reason updated.
- PICK_GUARD_RULES a9bdcc90 -> 7f9e0f4f (image_service.py:489), computed after black.
- FX-4: CLAUDE.md:728 rewritten to the current GUARD_SET (22 sources + the table / pattern text); "INC-I2b is next" dropped.

## Runs
- At aec760b5, before the fix (the final fix1 file): [pyt] tag=s96b-fix1-xbase4 start=2026-11-17 04:50:48 end=2026-11-17 04:50:51 elapsed=4s bound=600s status=FAIL rc=1: 11 failed (X1..X11, 11 x AssertionError, no other error type), 2 passed (X12, X13); [hermeticity] sentinel checked 13; [netguard] blocked 0.
  - Earlier base runs of drafts: xbase ([pyt] status=FAIL rc=1, 12 failed: the X12 bare row is refused at base with fragrance_word on the roff shape), xbase2 (12 failed: a test bug, _flags() did not unset W between rows), xbase3 (11 failed / 2 passed; its [pyt] status line was not captured). Both test bugs were fixed before xbase4; no app change in between.
- At the head (the committed bytes), 59 files, 3 chunks of <= 25, bound 1200 (gate set list sha256 114d9f9b...):
  - [pyt] tag=s96b-fix1-hd_00 start=2026-11-17 04:53:14 end=2026-11-17 04:55:31 elapsed=137s bound=1200s status=OK rc=0: 939 passed (incl. the RED file 28, addenda 10, I2a 67, fix1 13, test_ci_gates, test_behavior_dimension_translation, test_inc_r1_seam). No [hermeticity] / [netguard] summary line was printed for this chunk (it holds test_hermeticity_pins.py); the netguard lines printed are that file's own guard self-tests.
  - [pyt] tag=s96b-fix1-hd_01 start=2026-11-17 04:55:32 end=2026-11-17 04:58:52 elapsed=201s bound=1200s status=FAIL rc=1: 7 failed, 3444 passed; [hermeticity] sentinel checked 3451; [netguard] blocked 24 attempt(s) from 2 node(s) (two test_s81_s04_spend_breaker nodes, sentinel host neutralized.supabase.invalid; both nodes passed).
  - [pyt] tag=s96b-fix1-hd_02 start=2026-11-17 04:58:53 end=2026-11-17 04:59:26 elapsed=34s bound=1200s status=OK rc=0: 657 passed; hermeticity 657; netguard 0.
  - The 7 failures are all in the base union (harness/base_records/5cd93c6a.../80ec8352... + 2f256deb..., 26 ids): test_s81_s07_meas_harness::test_r35_fixtures, test_s81_s16_kb_seed::test_s16_r27_hygiene_of_g2_files x5, test_s81_s22_compare_runs::test_b02_one_transaction_ascii_lf. comm -23 (head minus base union): EMPTY, new_failures = []. LC-6: the base records were reused, no base re-run.
- Gate set: the named files; every test referencing image_relevance / image_service / imgpick; the CLAUDE.md readers carrying image text (test_s81_s04_spend_breaker, test_s81_s07_meas_harness); 35 app-walking tests (rglob / glob / os.walk / listdir over app or the repo root); the standard source-scanning pins (model_config, model_config_enforced, prompt_fence, u3c_store_false_pin, start_command, openai_key_log_hygiene_s69, migration_index_predicate_immutability, sentry_channels_u8d_unit). All 58 non-fix1 files are members of the GREEN 499 comm set.

## Digest
- probes/digest.py (ADV-1's, the I2a GUARD_SET text) in three fresh interpreters: PYTHONHASHSEED=0, random, 777 -> 7f9e0f4f (prefix 7f9e0f4f31243615) in all three, == the constant. E19 and E22 pass (hd_00).

## Corpus (the frozen corpus fixture, the RED method, flags patched in the probe process; probes/corpus.py)
| run | before FA base -> W | before FR | after FA base -> W | after FR | right newly refused |
|---|---|---|---|---|---|
| S ON typed | 65 -> 7 | 22 -> 22 | 65 -> 7 | 22 -> 22 | 0 |
| S ON untyped | 65 -> 27 | 22 -> 22 | 65 -> 27 | 22 -> 22 | 0 |
| S OFF typed | 59 -> 7 | 25 -> 25 | 59 -> 7 | 25 -> 25 | 0 |
| S OFF untyped | 59 -> 23 | 25 -> 25 | 59 -> 23 | 25 -> 25 | 0 |
| no-conc, S ON and OFF | 10 -> 1 | 9 -> 9 | 10 -> 1 | 9 -> 9 | 0 |
Acceptance: false refuses unchanged, false accepts +0: ACCEPTED.

## cases.json delta (ADV-1 probes/words.py over probes/cases.json, 179 rows)
- Before reproduces ADV-1's words_out.txt byte for byte. After: exactly 11 rows change, all FALSE_REFUSE(new) -> W=None (truth right): the five F-A1-1 titles and the six F-A1-2 pairs (words_out lines 6, 7, 8, 44, 60, 82, 84, 86, 87, 90, 91). No other verdict moved: no new false accept, no new false refuse.

## Slot probe (probes/slots.py -> slots_out.txt, slots_out2.txt)
- free=1: "Dior Homme Intense" at the end, before 100ml / 100 ml / 3 4 oz, Spray, pour Homme, for Men, EDP, Eau de Parfum, Elixir, by, Edition, Men.
- free=0 after a size: "Intense Scent / Fragrance / Perfume / Long Lasting / and Woody / Oud / Man".
- An intense directly after a phrase stays part of the phrase label (I-9, unchanged): "EDP Intense Scent" reads {EDP Intense}, so a typed EDP (no typed intense) still refuses it.

## Lint
- ruff --select E9,F63,F7,F82 on image_relevance.py, image_service.py and the fix1 file: All checks passed; full ruff on image_relevance.py + the fix1 file: clean; black --check over the 45 allowlisted files: unchanged (a py3.15 target warning prints); py_compile OK. fix1 file: 0 bytes > 127, LF.

## Files (sha256 on disk at 478a3ad8)
- b6dd686a237d3c20f59209b88030ddc0f0817603c1e42e89d550334631231bf2 app/services/image_relevance.py
- 6a3000ab43f6870623310aba0c104f66b41586d712adef97e9332e64976a0023 app/services/image_service.py
- 693ffc336e4d834a889f4b871fd54c29e53969e847832862690a49ff04d94b43 CLAUDE.md
- 3edc5d1c60255131509f538a20f99c6db3029b11ca8c38b3b4da66f169ecb439 .github/black-clean-paths.txt
- f3e81ed830da1b8c82deaa28d4038c474e3a87111364f53fa21aaa9ff91ea2d5 tests/test_inc_i2b_fix1.py
- unchanged: 323e944c... tests/test_inc_i2a_picture_not_cut.py, 5935d9e1... tests/test_inc_i2b_addenda.py
- frozen, re-checked at the end: c206cfd2... the RED file, 73e94432... the golden, 510d42d7... the corpus: unchanged.

## Deviations
- image_service.py changed (one line, the PICK_GUARD_RULES literal at :489): the literal lives there, not in the listed files.
- tests/test_inc_i2a_picture_not_cut.py NOT changed: E22 holds no digest literal (it compares the computed GUARD_SET digest with image_service.PICK_GUARD_RULES) and its GUARD_SET list is unchanged, so moving the literal moves E22.
- The X12 bare row uses the known-brand shape (brand Dior, line Homme): on the roff shape (brand "") its title carries no fragrance word and the base refuses it with fragrance_word. X13 asserts concentration on the known-brand shape and "not None" on the roff shape (there the base refuses at name, since "intense" is a line token).
- The closed words are inline in _conc_scan (hashed) rather than a module table (a new table could not join the frozen E19 text).
- INTENSE_GENERIC_NEXT kept but unread (the frozen E19 needs the name).

## Possible stated limits seen (for the re-verifier)
- A flanker written with a word outside the closed list (e.g. "Club de Nuit Intense Man") is generic for a bare query: a false accept, L1-like.
- An intense directly after a phrase followed by marketing words ("EDP Intense Scent") is the EDP Intense label (I-9): refused for a typed EDP without a typed intense.
