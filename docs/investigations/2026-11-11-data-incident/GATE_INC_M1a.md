# GATE INC-M1a RESOLVER FOLD (S96-FIX, 2026-11-17 13:12 AST)

## 1. Verdict: RED GATE PASSED
- Frozen file: tests/test_inc_m1a_resolver_fold.py, sha256 63fc6a67b082317f3346d702a97d1880e2ca4dca8c9df66314b212d7cef0cfd3, 49,076 B.
- At base 7f672cfe:
  - 62 RED, every one an AssertionError; 66 PIN.
  - [pyt] inc-m1a-red-base1 rc=1.
  - hermeticity 128; netguard 0.
- Prototype: ON 128/0, OFF 66/0 (pin rows).
- Mutants: 13 of 13 killed (MA1-MA9, plus MA10-MA13 added).
- Comm set: 156 files in 7 chunks. The base failures are the 16 ids in the RED report: 15 in the INC-R1 record, plus the e27 timing flake.
- Report: <SP>/INC-M1a_RED_REPORT.md.

## 2. Base for GREEN
- The branch fix/inc-m1a-resolver-fold was fast-forwarded to main 9bc13109 (the #419 merge) before GREEN. #419 touches no resolver file.
- The frozen file stays byte-identical and untracked until the GREEN commit.

## 3. Rulings (binding on GREEN and the adversary)
- **M1R-8 Deliberate pin changes (the E-rows).** GREEN may edit ONLY these frozen INC-R1 rows, and only as far as M1a's purpose requires:
  - test_inc_r1_resolver.py::test_r05_lines_file: the line count and the new optional field.
  - test_r11_residual_not_high: the [Creed Aventus for Her] and [YSL Libre Intense] cases. They are now seeded flankers, so they resolve to the flanker, not to the base at high.
  - test_r15_arabic_never_lexicon_high: narrow it, never delete it.
    - Arabic typed text may resolve high/lexicon ONLY through an exact seeded data row: the house and the line both from data/fragrance_lines.json aliases.
    - Add, or keep, a case that an UNSEEDED Arabic name (for example an Arabic Lattafa Khamrah, or an Arabic line not in the file) is still never lexicon-high.
  - test_r21_guard[g8] and [g8b]: GREEN states in its report what each guard asserts and why the change is the minimum.
  - Each change goes in the PR's "Deliberate pin changes" table with a before/after line.
  - Any other existing failing row is a STOP: report it, do not edit.
- **M1R-9 The link key moves (S97's file, read only).** url_extraction_service._link_key reads resolve_lexicon and _typed_concentration, under ENABLE_URL_LINK_RESULT. The new data rows and the Arabic phrases change its key for page names naming Y, Hawas, a flanker, Libre EDT or Arabic text.
  - This is deliberate and correct: one key.
  - The PR states it, and so does the relay's note for S97.
  - PIN-0 keeps every other line unchanged.
  - url_extraction_service.py is NOT edited.
- **M1R-10 Arabic phrases through the lexicon seam.** The Arabic concentration phrases are read through category_gate.load_lexicon (the FRAGRANCE_LEXICON_PATH seam), never from a fixed path. AR-5d pins it. CONCENTRATION_PHRASES, GENERIC_WORDS and QUALIFIER_WORDS stay byte-identical (PIN-0).
- **M1R-11 Open questions ruled:**
  - (a) "Libre Le Parfum" and "YSL Y Le Parfum" stay medium (a stated limit). No row, and GREEN does not add a rule for them.
  - (b) "YSL Y Elixir" resolves to the Elixir flanker through the existing concentration-flanker rule. This is accepted (consistent with Stronger With You Parfum) and stated.
  - (c) NO new accessor in M1a. Spec 1.2.1's accessor is for later readers. M1b adds exactly the accessor it reads, with its own rows.
  - (d) The single-letter alias "y": the adversary probes typed tokens of 1-2 letters, and Latin and Arabic short words, for a false high resolution. If one is found, it is a fix round.
- **M1R-12 CRLF.** The repo files keep their line endings as checked out (autocrlf). The lines file is written as ASCII JSON with the repo's existing ending.

## 4. What GREEN builds
- The spec section 1.2, as the prototype did:
  - data/fragrance_lines.json: the Arabic aliases (escapes; explicit YA), Y, Hawas plus the lexicon's Arabic Rasasi, the flankers, Libre [EDT, EDP], single_concentration on Aventus, Layton, Khamrah and Hawas.
  - product_resolver.py:
    - the validator's bool check;
    - the Arabic phrases via load_lexicon with a small word map and YA variants, used by _typed_concentration and _strip_concentrations;
    - a generic-word flanker matched before the generic drop.
  - The E-rows per M1R-8.
  - CLAUDE.md: the INC-R1 block gains the M1a rows. This includes a sentence that the one home for Arabic brand and line spellings is data/fragrance_lines.json, with M1R-9's link-key note.
- Gates:
  - the unit file with ENABLE_PRODUCT_RESOLVER ON and OFF;
  - the comm set at HEAD vs the base list (branch-only-NEW must be EMPTY);
  - the existing resolver suites;
  - the CLAUDE.md readers by import graph;
  - the fourteen client fences once.
- The whole-tree one-process run is NOT required: no conftest or process-state change. If GREEN touches any module-level state, it runs it.
- Chain: ONE correctness adversary (the relay's word, 13:00). Its lens includes M1R-11(d) and the flag mix ENABLE_PRODUCT_RESOLVER x ENABLE_ANTHROPIC_TEXT x consent 2/3 x ENABLE_URL_LINK_RESULT.
