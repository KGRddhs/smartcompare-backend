# GATE INC-I2b GUARD-WORDS + SHOP-IMAGE-TIER (S96 orchestrator, 2026-11-17 about 02:55 AST)

The AMEND+RED run wf_4a1ec0cc-8c8 (two Opus 5.5 agents, model verified, 650,437 tokens, 83 min) is ACCEPTED.
- **The contract:** spec V2 s96/i2b/spec/INC_I2B_UNIT_SPEC_V2.md (31,995 bytes) together with RULINGS_INC_I2B.md I-1..I-19 and this gate.
- **FROZEN files:**
  - tests/test_inc_i2b_guard_words_shop_image.py, sha256 c206cfd2dd4601bac2d7938f1f3d86a122599b186a6fca47d4d3ef8154feb06a (54,314 bytes, ASCII).
  - tests/fixtures/inc_i2b_flag_off_golden.json, sha256 73e94432da4236d6d4d183a63c78277fdfa08f4e0dfc55f6594086a6f45cd9b8.
  - tests/fixtures/inc_i2b_guard_words_corpus.json, sha256 510d42d756d6e6ed621636698dc3a6d826b3fc21622ff12971bd6a02a137e18a.
- **At base:** 22 E nodes fail, all on AssertionError; 6 P nodes pass.
- **At the prototype:** 28 of 28 pass, and with the I2a file, 95 pass. All 32 mutants are killed.
- **Comm set** (321 files, sha 80ec8352...): adds no new failure. The base record is at harness/base_records/5cd93c6a....
- **Corpus, S ON typed:** false accepts 65 -> 7, false refuses 22 -> 22, so no right picture is newly refused. Untyped (the resolver default case): 65 -> 27.
- **PICK_GUARD_RULES** a9bdcc90 (computed after black).
- **Moved pins** in tests/test_inc_i2a_picture_not_cut.py: E22 (the widened GUARD_SET text and the new value) and the BIND regex gaining `shopping`.
- **The orchestrator reviewed proto.diff.** The SCS hunks:
  - `_typed_image_text`;
  - the carrier in the INC-R1 hook, only with G and W ON;
  - `typed=` at the three relevance_kwargs sites;
  - the bind's `shop_thumb` last resort;
  - the B block, read first.

  The WOO hunk: the id(candidate) -> prod map and the winner stamp, guarded by `best is not None and _relevance.shop_page_image_enabled()`, with no image_service import while A is OFF. It is the contract.
- **Production changed during the round:** ENABLE_IMAGE_LATE_BIND is ON on web since 02:45 (the orchestrator's switch). So L ON is today's production state in every walk row, and L9 is real: the merge moves every imgpick name, which costs one paid miss per product once.

## Rulings on the open questions
- GB-1 (OQ-A) "Set of 1" stays REFUSED (form). Stated limit L14.
- GB-2 (OQ-B) CONFIRMED: the typed concentration labels sit on the cache axis.
- GB-3 (OQ-C) CONFIRMED: the q= parser variant counts as typed (it is user text). Already L4.
- GB-4 (OQ-D) CONFIRMED, on one condition: the `_typed_name` carrier must never reach a response body, a stream event, a History or compare_runs save, a cache key other than the imgpick axis, an LLM prompt, or any log line. GREEN measures it (G-3 row AX-4); a leak is a MAJOR finding, fixed by popping the key once the image calls are made.
- GB-5 (E11 vs I-9) CONFIRMED: A refuses only a free-standing intense; "... Eau de Parfum Intense" is the EDP Intense label and is stamped (A never applies 2(b); L5).
- GB-6 (P5 strict count) GREEN adds AX-5 to the addenda file: the A reader is read exactly once per match call that has a winner. It must fail at base on an assertion (count 0 != 1).
- GB-7 (E13, the E8 L ON half) GREEN adds AX-6 (E13 caps: L OFF, the Phase-1 cap skips the B block; L ON, the drain keeps the base outcome) and AX-7 (the late get_cached name carries the w axis) to the addenda file. Each must fail at base on an assertion.

## The orchestrator's 02:50 asks (Arabic-script names), see s96/i2b/ARABIC_PROBE.md
- GB-8 The unit changes nothing for an Arabic-script typed name; the addenda pin that. Arabic text is built from code points with `chr(0x...)` (never a backslash-u escape written through a tool), so the file stays ASCII.
  - AX-1: the two placeholders "ديور سوفاج EDP" and "بلو دو شانيل EDP" typed, R OFF: per candidate, the check() reason is the same with W unset and W ON, over the eight probe titles of ARABIC_PROBE.md (both brands Latin, Arabic, empty).
  - AX-2: the post-INC-M1 identity (Latin brand and line; Arabic product_name) accepts the Latin titles with W ON.
  - AX-3: an Arabic title carrying an Arabic gift word alone is not refused by W.
  - AX-1..AX-3 pass at base and at the head.

## GREEN (one agent) does
- G-1 The worktree is at base 5cd93c6a plus the three frozen untracked files. While it is still at base:
  - write tests/test_inc_i2b_addenda.py (AX-1..AX-7; hermetic, ASCII, the RED file's fakes and fixture style, getattr for missing symbols);
  - run it at base: AX-5..AX-7 fail on AssertionError, AX-1..AX-3 pass;
  - AX-4 (the leak row: G, W and R ON, one sync and one stream compare through the INC-R1 seam fakes; no `_typed_name` in the response, the events, the save payloads or the captured prompt, and no typed text in any IMG_ line) may pass at base trivially; that is acceptable.
  - Also run the base record of the comm-set members that are not yet in harness/base_records/5cd93c6a... (G-4).
- G-2 Apply the prototype: copy red/proto_bytes/* to their paths, and apply the CLAUDE.md and I2a test hunks of red/proto.diff. Verify that every resulting file equals the proto.diff post-image (the blob hash in its index line); lint latitude only. Black-format and ruff stay clean; PICK_GUARD_RULES must equal the digest of the final bytes (E19, E22).
- G-3 If AX-4 shows a leak, pop the key after the image calls (GB-4) and record it as a deviation.
- G-4 Comm set: the UNION of s96/i2b/red/commset.txt (321) and s96/i2a/red/commset.txt (467; it carries the structured_comparison_service seed this round's set lacked), plus the two new test files, minus test_precommit_hook*.py: 497+ files. Rules:
  - The base record for members missing from the cached 5cd93c6a record is run at base in G-1, before G-2.
  - new failures = failing at head but not at base.
  - A timing-only failure is re-run once alone.
  - Spawn-time 0xC0000142 failures are re-run alone.
- G-5 The client jest fences that read repo files outside SmartCompareApp (the same list as INC-I2a GREEN: s96/i2a/green/fence_find.out plus the seven named in s96/i2a/wf_green2.js). The 4 nativeBundle.w37 drift nodes are an accepted base failure. NOT the full suite.
- G-6 .github/black-clean-paths.txt gains the RED file and the addenda file. Check `ruff --select E9,F63,F7,F82` on the touched .py files and black --check on the allowlisted files.
- G-7 COMMIT on fix/inc-i2b-guard-words-shop-tier:
  - Subject: "fix(images): INC-I2b GUARD-WORDS refuse the wrong form and concentration, add the shop-photo and Shopping-thumbnail tiers (dark ENABLE_IMAGE_GUARD_WORDS, ENABLE_SHOP_PAGE_IMAGE, ENABLE_SHOPPING_THUMB_IMAGE)".
  - A body of 3-6 lines and the trailer `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
  - Stage by name: the four app files, CLAUDE.md, .github/black-clean-paths.txt, tests/test_inc_i2a_picture_not_cut.py, the RED file, the addenda file and the two fixtures.
  - Never --no-verify, never push.
- G-8 Then `git fetch origin main`. If origin/main is not 5cd93c6a, merge it (--no-ff --no-edit); on a conflict, abort the merge and report blocked. At the head, re-run the RED file, the addenda, tests/test_inc_i2a_picture_not_cut.py, test_ci_gates, test_behavior_dimension_translation and test_inc_r1_seam.

## The adversaries (two, I-1), in parallel on the committed head
- **ADV-1, THE WORDS:**
  - the false-refuse / false-accept corpus and fresh probes beyond the RED rows: real-shaped shop titles, Arabic and French spellings, Intense / Elixir / Extrait / Parfum, gift / set / travel / mini / refill / body forms;
  - the concentration rule under R OFF and R ON (typed vs defaulted, the carrier, the q= path);
  - the widened GUARD_SET determinism across processes (PYTHONHASHSEED 0 vs random) and the cache axis;
  - the Arabic rows against ARABIC_PROBE.md.
- **ADV-2, THE SHOP TIER AND PRODUCTION:**
  - the WOO stamp (select_best identity: does it return the candidate object or a copy? id-map lifetime, OOS winner, raising extraction);
  - the B thumb tier and its owner-policy gate;
  - the inline override and the late chooser order (override, job, fallback, shopping);
  - the `_typed_name` leak paths by reading every consumer of the products list;
  - the log lines against the plain-word filter rule; the OFF byte identity of every edited region;
  - the flag-mix walk of spec section 4 against today's production: G ON, S ON, L ON (since 02:45), R OFF and R ON, W/A/B each OFF and ON.

Each returns a verdict, SOUND or NOT_READY. Findings are BLOCKING, MAJOR or MINOR; a MINOR becomes a stated limit (LC-4).

## Stated limits (the PR body)
- L1..L13 as spec V2 section 9.
- L14: "Set of 1" is refused (GB-1).
- L15: an Arabic-script typed name still gets no picture: the guard needs the typed script in the title, and the image search goes out in Arabic. INC-M1 (data lane) brings the Latin identity; after it, Arabic-only titles still refuse at brand (ARABIC_PROBE.md).
- L16: an IMG_RELEVANCE `reason=` is the LAST rejected candidate's reason, not every candidate's.
