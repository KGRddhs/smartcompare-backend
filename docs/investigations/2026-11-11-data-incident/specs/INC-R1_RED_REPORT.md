# INC-R1 RESOLVE-OR-ASK: RED report (RED round; Opus 5.5 RED agent of the S95-FIX lane; 2026-11-14)

Unit INC-R1 (flag ENABLE_PRODUCT_RESOLVER). Base 731bcddf531a7e123963246168ca19f262859337. Real worktree C:/Users/SynAckITPC/Documents/AI/sc-inc-r1 (only the two new RED files added). Spec .qa-s80/INC-R1_UNIT_SPEC.md (sha256 0676c198...), review .qa-s80/INC-R1_SPEC_REVIEW.md (sha256 97afb2e6...), rulings <SP>/INC-R1/RULINGS_INC_R1.md (R1-R1..R1-R31; binding), brief <SP>/INC-R1/INC_R1_BRIEF.md. Every pytest ran through <SP>/harness/gate.py (never the runner directly), one at a time. Nothing here says a production problem is fixed: the unit is not built; once merged it is 'merged, NOT yet proven' until the phone proof (spec 8b as amended by R1-R24 / R1-R26) runs (H6). A hermetic measurement is not the production proof.

## 0. Files written (the only change in the real worktree)

- tests/test_inc_r1_resolver.py: 65761 bytes, sha256 e47fa219e60d673c9d0aaa042e517ddb48d507a13622bde944633690fc6ade70, bytes > 127: 0, CR: 0, black 26.5.1 --check clean, ruff E9/F63/F7/F82 clean
- tests/test_inc_r1_seam.py: 49828 bytes, sha256 9c30052f0cc3f9aa7a2058e70f5feafafe7c1d2a20f12264ea106178ab6a539f, bytes > 127: 0, CR: 0, black 26.5.1 --check clean, ruff E9/F63/F7/F82 clean
- Frozen copies: <SP>/INC-R1/frozen/ (same bytes). Working notes: <SP>/INC-R1/red/notes.md; every log under <SP>/INC-R1/red/.

## 1. Base-state runs (spec 1.10 B1-B8 + the review's deferred rows; ALONE at the base, real worktree, before any new file existed)

    === inc-r1-base-erows rc=1
    [gate] tag=inc-r1-base-erows waiting: another lane's run is live
    [gate] tag=inc-r1-base-erows waiting: another lane is queued
    [gate] tag=inc-r1-base-erows waiting: another lane took the slot
    [gate] tag=inc-r1-base-erows waited=389s (another lane is queued, another lane took the slot, another lane's run is live)
    ===== 1 failed, 692 passed, 2 deselected, 17 warnings in 72.92s (0:01:12) =====
    [pyt] tag=inc-r1-base-erows start=2026-11-14 21:36:21 end=2026-11-14 21:37:36 elapsed=74s bound=1200s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\fce5ef8e-45c1-47d7-9da1-42b27fb2581e\scratchpad\INC-R1\red\inc-r1-base-erows.log

    === inc-r1-base-llm rc=1
    [gate] tag=inc-r1-base-llm waiting: another lane is queued
    [gate] tag=inc-r1-base-llm waiting: another lane took the slot
    [gate] tag=inc-r1-base-llm waited=121s (another lane is queued, another lane took the slot)
    ===== 981 passed, 2 skipped, 1 xfailed, 137 warnings, 2 errors in 43.73s ======
    [hermeticity] sentinel checked 984 test(s)
    [netguard] blocked 24 attempt(s) from 2 node(s)
    [pyt] tag=inc-r1-base-llm start=2026-11-14 21:39:38 end=2026-11-14 21:40:23 elapsed=45s bound=1200s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\fce5ef8e-45c1-47d7-9da1-42b27fb2581e\scratchpad\INC-R1\red\inc-r1-base-llm.log

    === inc-r1-base-routes rc=1
    [gate] tag=inc-r1-base-routes waiting: another lane is queued
    [gate] tag=inc-r1-base-routes waited=47s (another lane is queued)
    ================ 1 failed, 1098 passed, 17 warnings in 25.83s =================
    [pyt] tag=inc-r1-base-routes start=2026-11-14 21:41:12 end=2026-11-14 21:41:39 elapsed=27s bound=1200s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\fce5ef8e-45c1-47d7-9da1-42b27fb2581e\scratchpad\INC-R1\red\inc-r1-base-routes.log

    === inc-r1-base-claude rc=1
    ================= 1 failed, 696 passed, 17 warnings in 57.84s =================
    [hermeticity] sentinel checked 697 test(s)
    [netguard] blocked 24 attempt(s) from 2 node(s)
    [pyt] tag=inc-r1-base-claude start=2026-11-14 21:41:46 end=2026-11-14 21:42:46 elapsed=59s bound=1200s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\fce5ef8e-45c1-47d7-9da1-42b27fb2581e\scratchpad\INC-R1\red\inc-r1-base-claude.log

    === inc-r1-base-erows2 rc=0
    ====================== 167 passed, 15 warnings in 26.45s ======================
    [hermeticity] sentinel checked 167 test(s)
    [netguard] blocked 0 attempt(s) from 0 node(s)
    [pyt] tag=inc-r1-base-erows2 start=2026-11-14 21:42:52 end=2026-11-14 21:43:20 elapsed=28s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\fce5ef8e-45c1-47d7-9da1-42b27fb2581e\scratchpad\INC-R1\red\inc-r1-base-erows2.log

    === inc-r1-base-state rc=1
    ================= 1 failed, 354 passed, 15 warnings in 13.67s =================
    [hermeticity] sentinel checked 355 test(s)
    [netguard] blocked 0 attempt(s) from 0 node(s)
    [pyt] tag=inc-r1-base-state start=2026-11-14 21:43:27 end=2026-11-14 21:43:41 elapsed=15s bound=1200s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\fce5ef8e-45c1-47d7-9da1-42b27fb2581e\scratchpad\INC-R1\red\inc-r1-base-state.log

- B1 / B4 failure: tests/test_s81_s07_meas_harness.py::test_r35_fixtures (assert b'\r' not in raw: the fixtures are CRLF in this core.autocrlf=true working copy; environmental; also in INC-I1's 731bcddf base record). B2: the two known cold-tiktoken tests/test_prompt_truth.py ERROR nodes. B3 / state: tests/test_s81_s10_fragrance_gate.py::test_r06_production_lexicon_content (known base failure). erows2 (s22b + MON1 x3): green. FY25 green at the base.
- B7 (the cold import, the exact spec command; the box was under load): app.services.price_service cumulative 1,251,432 us (self 148,001 us), extraction_service cumulative 895,494 us (<SP>/INC-R1/red/importtime_ps.txt). No .env exists on the dotenv search path (existence checked only).
- B8: black 26.5.1 --check --diff app/services/llm_router.py tests/test_s81_s06_router_gate_rows.py: '2 files would be left unchanged', rc 0.

## 2. Step 4: the RED gate at the base (real worktree; the frozen bytes)

    === inc-r1-red-base rc=1
    [pyt] tag=inc-r1-red-base status=BUSY rc=126 waited=0s (this lane's pytest mutex is held by pid 23096; NOT started)
    [gate] tag=inc-r1-red-base waiting: another lane is queued
    [gate] tag=inc-r1-red-base waiting: another lane took the slot
    [gate] tag=inc-r1-red-base waiting: another lane's run is live
    [gate] tag=inc-r1-red-base waited=137s (another lane is queued, another lane took the slot, another lane's run is live)
    ================ 195 failed, 51 passed, 17 warnings in 13.98s =================
    [pyt] tag=inc-r1-red-base start=2026-11-14 22:49:44 end=2026-11-14 22:49:59 elapsed=15s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\fce5ef8e-45c1-47d7-9da1-42b27fb2581e\scratchpad\INC-R1\red\inc-r1-red-base.log

    === inc-r1-red-base2 rc=1
    ================ 195 failed, 51 passed, 17 warnings in 13.08s =================
    [pyt] tag=inc-r1-red-base2 start=2026-11-15 00:03:16 end=2026-11-15 00:03:30 elapsed=14s bound=600s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\fce5ef8e-45c1-47d7-9da1-42b27fb2581e\scratchpad\INC-R1\red\inc-r1-red-base2.log

- inc-r1-red-base ran the first freeze (resolver 95ee2041...); one sentinel line was then rebuilt by concatenation (the added-line sweep flags the joined @gmail literal of R31's forbidden list; same runtime value) and inc-r1-red-base2 ran the FROZEN bytes (resolver e47fa219...): the two runs have the identical node set and identical per-node states.

- 51 passed / 195 failed; failure classes ['AssertionError'] (every failure an AssertionError: True). The 51 passing nodes are exactly the PIN set.
- [netguard] at the base: 7 RED seam nodes that run the BASE compare with a user id (R05, R07, R08, R09, R20 x3) attempted the conftest's neutralized Supabase sentinel host (blocked, not a network call); on the prototype 0 attempts.

## 3. Row maps (state at the base / on the prototype)

### tests/test_inc_r1_resolver.py

| test | class | nodes | at base | prototype | docstring |
|---|---|---|---|---|---|
| test_r01_module_symbols_constants | RED | 1 | base 1 failed / 0 passed AssertionError | proto 1 passed / 0 failed | R01: the module exists with every 2.2 symbol and the 2.2 literals. |
| test_r02_flag_reader | RED | 14 | base 14 failed / 0 passed AssertionError | proto 14 passed / 0 failed | R02: the house idiom, read per call. |
| test_r03_timeout_knob | RED | 9 | base 9 failed / 0 passed AssertionError | proto 9 passed / 0 failed | R03: PRODUCT_RESOLVER_TIMEOUT_SECONDS with the _float_knob semantics. |
| test_r04_ask_knob | RED | 11 | base 11 failed / 0 passed AssertionError | proto 11 passed / 0 failed | R04 / R1-R28: '0', 'false', 'no', 'off' (case-insensitive, stripped) = resolve-only. |
| test_r05_lines_file | RED | 1 | base 1 failed / 0 passed AssertionError | proto 1 passed / 0 failed | R05 / R1-R19: the 12 seed lines, ASCII, version 1; no community-database name. |
| test_r06_extractor_parity_and_sizes | RED | 1 | base 1 failed / 0 passed AssertionError | proto 1 passed / 0 failed | R06: the phrase labels equal extract_concentration; sizes and the base concentration. |
| test_r06b_span_based_size | RED | 6 | base 6 failed / 0 passed AssertionError | proto 6 passed / 0 failed | R06b / R1-R5: size removal is span-based on the raw text (_SIZE_ML_RE, _SIZE_OZ_RE). |
| test_r06c_digit_outside_a_size_span_is_kept | RED | 1 | base 1 failed / 0 passed AssertionError | proto 1 passed / 0 failed | R06b / R1-R5: a digit token outside a size span is never removed (a residual). |
| test_r07_owner_pair_lexicon | RED | 1 | base 1 failed / 0 passed AssertionError | proto 1 passed / 0 failed | R07: the owner's pair resolves on the lexicon arm (Tyger has the pair context). |
| test_r08_golden_set | RED | 10 | base 10 failed / 0 passed AssertionError | proto 10 passed / 0 failed | R08: each golden name resolves high / lexicon to its canonical product. |
| test_r09_house_words_and_osa | RED | 9 | base 9 failed / 0 passed AssertionError | proto 9 passed / 0 failed | R09 / R1-R13: house words, the alias groups and the OSA edit rule (Blue -> Bleu). |
| test_r10_edit_rule_misses | RED | 3 | base 3 failed / 0 passed AssertionError | proto 3 passed / 0 failed | R10: Tygar at 2 > 1 misses; digits are exact; nothing matched -> low. |
| test_r10b_single_token_fuzzy_needs_pair_context | RED | 8 | base 8 failed / 0 passed AssertionError | proto 8 passed / 0 failed | R10b / R1-R8: a single-token line at distance > 0 with no typed house is HIGH only with a pair fragrance context (the other side resolved, the chip, a concentration / form word); otherwise MEDIUM. "Euros" with a resolved partner is the documented false positiv |
| test_r11_residual_not_high | RED | 3 | base 3 failed / 0 passed AssertionError | proto 3 passed / 0 failed | R11: a residual word (her stays one: R1-R4) leaves the side unresolved, medium, with the matched line among the candidates. |
| test_r11b_qualifiers_dropped_from_the_residual | RED | 5 | base 5 failed / 0 passed AssertionError | proto 5 passed / 0 failed | R11b / R1-R4: the qualifier set is dropped from the residual. |
| test_r11c_distinct_product_words_stay | RED | 2 | base 2 failed / 0 passed AssertionError | proto 2 passed / 0 failed | R1-R4: femme / women stay residual words (pour only before homme is a qualifier). |
| test_r11d_qualifiers_never_removed_before_the_line_search | RED | 1 | base 1 failed / 0 passed AssertionError | proto 1 passed / 0 failed | R1-R4: a line whose own name holds a qualifier word still matches its tokens. |
| test_r12_flankers | RED | 1 | base 1 failed / 0 passed AssertionError | proto 1 passed / 0 failed | R12: flanker words match EXACTLY (an edit-distance flanker is a residual). |
| test_r13_house_conflict | RED | 1 | base 1 failed / 0 passed AssertionError | proto 1 passed / 0 failed | R13: a typed house inconsistent with the line is unresolved, the line a candidate. |
| test_r14_house_only_nothing_and_non_fragrance | RED | 1 | base 1 failed / 0 passed AssertionError | proto 1 passed / 0 failed | R14 / R1-R3 (a): a house hit is a fragrance signal only with no non-fragrance term. |
| test_r15_arabic_never_lexicon_high | RED | 1 | base 1 failed / 0 passed AssertionError | proto 1 passed / 0 failed | R15 / SL1: the lexicon's Arabic Dior matches as a house hint; no Arabic line alias. |
| test_r16_router_site_no_format | RED | 1 | base 1 failed / 0 passed AssertionError | proto 1 passed / 0 failed | R16 / R1-R7: SITES['resolve'] = SiteSpec('text', 384, None, True); the base rows kept. |
| test_p16_base_site_rows_unchanged | PIN | 1 | base 0 failed / 1 passed  | proto 1 passed / 0 failed | PIN (R1-R2 / R1-R7): the sixteen base SITES rows keep role, cap, JSON and schema. |
| test_r17_claude_request_shape | RED | 1 | base 1 failed / 0 passed AssertionError | proto 1 passed / 0 failed | R17 / R1-R7: one create; the role model, cap 384, thinking disabled, effort low and NO format; the system text + the JSON-only line; the M4 user content. |
| test_r18_prompt_digest | RED | 1 | base 1 failed / 0 passed AssertionError | proto 1 passed / 0 failed | R18: the prompt bytes are pinned (base64 sha256). |
| test_r19_hostile_name_fenced | RED | 1 | base 1 failed / 0 passed AssertionError | proto 1 passed / 0 failed | R19: a typed region tag is neutralized; the content carries exactly two of each tag. |
| test_r20_call_count | RED | 1 | base 1 failed / 0 passed AssertionError | proto 1 passed / 0 failed | R20: the owner's pair and every golden pair make no call; MODEL_PAIR makes one. |
| test_r21_guard | RED | 13 | base 13 failed / 0 passed AssertionError | proto 13 passed / 0 failed | R21 (2.5 as amended): the model side is accepted only through the deterministic guard; a lexicon-resolved partner keeps its lexicon result whatever the model says for it. |
| test_r21b_guard_line_holds_its_house_word | RED | 1 | base 1 failed / 0 passed AssertionError | proto 1 passed / 0 failed | R21 g7: with a seam lines file lacking Bleu de Chanel the model answer is accepted; the line's own house word sits inside the window, the leading one is a house token. |
| test_r22_decision | RED | 21 | base 21 failed / 0 passed AssertionError | proto 21 passed / 0 failed | R22 (2.6 as amended by R1-R3, R1-R6, R1-R15): resolved / partial / ask / passthrough; the ASK knob is read only when an ask would otherwise result (d14). |
| test_r23_wall | RED | 1 | base 1 failed / 0 passed AssertionError | proto 1 passed / 0 failed | R23: the wall cuts the call: partial (no ask), ONE WARNING by type, nothing cached. |
| test_r24_failure_classes | RED | 6 | base 6 failed / 0 passed AssertionError | proto 6 passed / 0 failed | R24: any exception of the call = no usable verdict (no ask), ONE WARNING by class. |
| test_r24b_malformed_answers | RED | 4 | base 4 failed / 0 passed AssertionError | proto 4 passed / 0 failed | R24: a malformed or truncated answer: ONE WARNING 'model answer malformed', usage kept. |
| test_r25_never_raises | RED | 1 | base 1 failed / 0 passed AssertionError | proto 1 passed / 0 failed | R25: an unexpected exception inside the resolver -> passthrough, ONE WARNING by type; an unreadable lines file -> ONE WARNING per file state, the houses still match. |
| test_r26_cache | RED | 1 | base 1 failed / 0 passed AssertionError | proto 1 passed / 0 failed | R26 (2.4 K as amended by R1-R6 / R1-R16): one call for repeats; a consent-3 answer never serves a consent-2 request (which makes no call at all); the TTL; malformed answers are not cached; ordered sides; the [RESOLVE] line carries cached=0 / cached=1. |
| test_r26b_cache_size | RED | 1 | base 1 failed / 0 passed AssertionError | proto 1 passed / 0 failed | R26 (4): at most 2,000 entries, the least recently used evicted. |
| test_r27_resolve_line | RED | 1 | base 1 failed / 0 passed AssertionError | proto 1 passed / 0 failed | R27 (2.9 + R1-R16 + C-14): ONE INFO [RESOLVE] line per call; resolved names only; an unresolved side logs '-' and its typed text appears in no record; single-line values; a brand accepted only through the typed-token clause logs '-'; no ERROR, no exc_info. |
| test_r28_no_call_unless_the_text_role_decides_anthropic | RED | 3 | base 3 failed / 0 passed AssertionError | proto 3 passed / 0 failed | R28 / R1-R6: below consent 3 (or with the text role OFF) the model arm is SKIPPED: no route call, no Anthropic or OpenAI create, no ask; unresolved names run as today. |
| test_r29_usage | RED | 1 | base 1 failed / 0 passed AssertionError | proto 1 passed / 0 failed | R29 / C-6: the answer's usage (zero cache tokens); a cache hit and a raised call: None. |
| test_r31_module_hygiene | RED | 1 | base 1 failed / 0 passed AssertionError | proto 1 passed / 0 failed | R31 (+ C-16): ASCII; none of the guarded strings; no ERROR log or exc_info; the module-top imports; exactly ONE routed call in the literal disambiguate form. |
| test_r32_candidates_validator_good | RED | 1 | base 1 failed / 0 passed AssertionError | proto 1 passed / 0 failed | R32: two lists of <= 4 well-formed items -> an equal fresh copy. |
| test_r32_candidates_validator_bad | RED | 8 | base 8 failed / 0 passed AssertionError | proto 8 passed / 0 failed | R32: any malformed shape -> None (the key is dropped whole). |
| test_r34_no_doubled_concentration | RED | 1 | base 1 failed / 0 passed AssertionError | proto 1 passed / 0 failed | R34 / C-4: a model line that carries the typed concentration word is not doubled. |
| test_r35_typed_concentration_outside_the_line | RED | 3 | base 3 failed / 0 passed AssertionError | proto 3 passed / 0 failed | R35 / R1-R11: a typed concentration outside the line's concentrations is MEDIUM. |
| test_r36_apply_resolution | RED | 1 | base 1 failed / 0 passed AssertionError | proto 1 passed / 0 failed | R36 (2.7): the canonical rewrite; True iff both sides resolved; an unresolved side's dict is untouched; no key added or removed. |
| test_r37_refusal_result_and_extras | RED | 1 | base 1 failed / 0 passed AssertionError | proto 1 passed / 0 failed | R37 (2.8): the refusal dict in the gate_refusal_body key order + candidates last; http_detail_extras reads the flag FIRST. |

### tests/test_inc_r1_seam.py

| test | class | nodes | at base | prototype | docstring |
|---|---|---|---|---|---|
| test_p01_flag_off_identity | PIN | 28 | base 0 failed / 28 passed  | proto 28 passed / 0 failed | P01 (2.12 + C-3): every OFF value with the FULL configuration and every recorder: the Step-1 dicts, the base parser_path, no call, no knob read, no lines-file open, no [RESOLVE] record, and the FY digest equal to the base literal. |
| test_p02_fy25_digests_with_unit_config | PIN | 1 | base 0 failed / 1 passed  | proto 1 passed / 0 failed | P02: the nine FY25 scenarios with the unit's knobs set and the flag 'false' keep the recorded digests (the names are exported for the scenario AND restored by monkeypatch). |
| test_r03_owner_pair_rewritten | RED | 2 | base 2 failed / 0 passed AssertionError | proto 2 passed / 0 failed | R03: the owner's pair is rewritten before any fetch; every search uses the canonical string; no model call; the canonical brand reaches the payload; no private key leaks. |
| test_r04_pair_category | RED | 4 | base 4 failed / 0 passed AssertionError | proto 4 passed / 0 failed | R04 (R1-8 / P5; C-1 by kind): a resolved pair is fragrances with NO classifier call, through parser_path=True; the stamp alone would give skincare for 'Second Skin'. |
| test_r05_sync_ask_before_any_fetch | RED | 1 | base 1 failed / 0 passed AssertionError | proto 1 passed / 0 failed | R05 (2.8): a fragrance-intended pair with an unresolved side is refused BEFORE the pair category, the profile task, the KB task and any fetch; the resolver's usage is tracked. |
| test_r06_stream_ask_error_event | RED | 1 | base 1 failed / 0 passed AssertionError | proto 1 passed / 0 failed | R06 (R1-7c): the stream refusal is a terminal `error` event, never a terminal payload. |
| test_r07_get_route_ask | RED | 1 | base 1 failed / 0 passed AssertionError | proto 1 passed / 0 failed | R07 (+ R1-R9): GET: a coded 400 with the additive reason and candidates; ONE consume, ONE refund WITH the consume's keys, no lifetime, no history, one failure row. |
| test_r08_post_route_ask | RED | 1 | base 1 failed / 0 passed AssertionError | proto 1 passed / 0 failed | R08 (+ R1-R9): the POST twin. |
| test_r09_stream_route_ask | RED | 1 | base 1 failed / 0 passed AssertionError | proto 1 passed / 0 failed | R09 (+ R1-R9): one `event: error` frame carrying the refusal dict plus request_id; no terminal payload; ONE refund with the consume's keys; no lifetime, no history. |
| test_r10_envelope_pin | PIN | 2 | base 0 failed / 2 passed  | proto 2 passed / 0 failed | R10 PIN cases: the base envelope with the FULL configuration and the flag OFF. |
| test_r10_envelope_red | RED | 2 | base 2 failed / 0 passed AssertionError | proto 2 passed / 0 failed | R10 RED cases (R1-R18): under the flag the ask's reason and validated candidates pass. |
| test_r10_envelope_bad_candidates_dropped | PIN | 6 | base 0 failed / 6 passed  | proto 6 passed / 0 failed | R10 PIN: a malformed candidates value never reaches the wire (dropped whole). |
| test_r10_envelope_other_codes | PIN | 2 | base 0 failed / 2 passed  | proto 2 passed / 0 failed | R10 PIN: another code carrying the same keys gets no reason / candidates from INC-R1. |
| test_r10_envelope_no_flag_read_without_the_marker | PIN | 3 | base 0 failed / 3 passed  | proto 3 passed / 0 failed | R10 PIN (R1-R18 / RC-2): the envelope reads ENABLE_PRODUCT_RESOLVER only after the refusal marker matches: never for a string detail or another code. |
| test_r11_builder_flag_mix | MIXED | 5 | base 2 failed / 3 passed AssertionError | proto 5 passed / 0 failed | R11 (R1-R18): the 400 builder; PIN cases green at the base, RED cases under the flag. |
| test_r12_consent2_owner_still_rewritten | RED | 1 | base 1 failed / 0 passed AssertionError | proto 1 passed / 0 failed | R12 RED half (R1-R6): below consent 3 the deterministic arm still rewrites the owner's pair, with no call. |
| test_r12b_consent2_model_pair_as_today | PIN | 1 | base 0 failed / 1 passed  | proto 1 passed / 0 failed | R12 PIN half (R1-R6): consent 2, TEXT / PRE_V3 / the egress stop ON: an unseeded pair makes no route call and no create and runs exactly as today (a success, no 400). |
| test_r13_model_arm_through_the_seam | RED | 2 | base 2 failed / 0 passed AssertionError | proto 2 passed / 0 failed | R13 (C-1 by kind; R1-R23): the model arm resolves an unseeded pair (no concentration typed, no seed entry -> none); its usage is one more tracked call. |
| test_r13b_model_arm_in_the_llm_ledger | RED | 1 | base 1 failed / 0 passed AssertionError | proto 1 passed / 0 failed | R13: with ENABLE_LLM_LEDGER_V2 ON the payload's metadata.llm counts the resolve call. |
| test_r14_partial_on_timeout | RED | 1 | base 1 failed / 0 passed AssertionError | proto 1 passed / 0 failed | R14 (R1-7d / R1-R7): a cut call is no verdict: no refusal; the lexicon side is rewritten, the other runs as typed; the [RESOLVE] line says partial. |
| test_r15_kb_first_serve_sees_identity | MIXED | 2 | base 1 failed / 1 passed AssertionError | proto 2 passed / 0 failed | R15: with ENABLE_KB_FIRST_SERVE ON the card read receives the rewritten dicts (a KB id can be minted); flag OFF (PIN) the base dicts (brand '', no id). |
| test_r16_other_entries_untouched | PIN | 3 | base 0 failed / 3 passed  | proto 3 passed / 0 failed | R16 PIN (R1-1, R1-R22): the q= path, the camera's vision path and the flagged q= pre-split never reach the resolver; their Step-1 dicts equal the base. |
| test_r17_claude_md_block_and_pointer | RED | 1 | base 1 failed / 0 passed AssertionError | proto 1 passed / 0 failed | R17 (+ R1-R12): the INC-R1 block after the S81-07c block and before '## Tests', and the pointer sentence in the '**Feature Flags:**' line after the S81-07c sentence. |
| test_r18_black_allowlist | RED | 1 | base 1 failed / 0 passed AssertionError | proto 1 passed / 0 failed | R18 (R1-R17): the resolver and both RED files are on the BLOCKING black allowlist. |
| test_r19_hook_is_total | RED | 2 | base 2 failed / 0 passed AssertionError | proto 2 passed / 0 failed | R19 (C-7): an exception in apply_resolution or refusal_result never reaches the orchestrator: the hook falls back to the base dicts, ONE WARNING naming the type only. |
| test_r20_refusal_budget | RED | 3 | base 3 failed / 0 passed AssertionError | proto 3 passed / 0 failed | R20 (R1-R10): with ENABLE_FRAGRANCE_ONLY_GATE ON an ask is counted on the S81-10 refusal budget exactly as S81-20 counts its refusals (spent keeps the credit); OFF nothing is read or counted. |
| test_r21_hook_passes_the_chip | RED | 2 | base 2 failed / 0 passed AssertionError | proto 2 passed / 0 failed | R21 (R1-R8 through the seam): the hook hands the request's chip to the resolver: with the Fragrances chip a fuzzy single-token line resolves next to an unresolved partner. |

## 4. Step 5: the prototype (thrown away; detached scratch worktree <SP>/INC-R1/INC-R1_scratch at the base)

Applied by <SP>/INC-R1/red/tools/apply_proto.py from <SP>/INC-R1/red/proto/product_resolver.py: the NEW app/services/product_resolver.py and data/fragrance_lines.json (the spec 2.2 bytes), llm_router SITES['resolve'] = SiteSpec('text', 384, None, True) (route() untouched), the two SCS hooks (total, falling back to the base dicts) + parser_path, text_routes (_surface_comparison_failure extras, the _resolver_ask_exit / _resolver_stream_settle twins of the S81-20 exit with the consume's keys and the refusal budget), error_handler (the marker first, then the flag), the CLAUDE.md block + Feature Flags pointer, the three black-allowlist entries. The E-rows (E1-E6) were not prototyped (they are GREEN's and do not touch the unit files).

    === inc-r1-proto-on3 rc=0
    ====================== 246 passed, 15 warnings in 15.28s ======================
    [hermeticity] sentinel checked 246 test(s)
    [netguard] blocked 0 attempt(s) from 0 node(s)
    [pyt] tag=inc-r1-proto-on3 start=2026-11-15 00:05:10 end=2026-11-15 00:05:26 elapsed=16s bound=600s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\fce5ef8e-45c1-47d7-9da1-42b27fb2581e\scratchpad\INC-R1\red\inc-r1-proto-on3.log

    === inc-r1-proto-off3 rc=0
    ====================== 246 passed, 15 warnings in 14.92s ======================
    [hermeticity] sentinel checked 246 test(s)
    [netguard] blocked 0 attempt(s) from 0 node(s)
    [pyt] tag=inc-r1-proto-off3 start=2026-11-15 00:05:33 end=2026-11-15 00:05:49 elapsed=16s bound=600s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\fce5ef8e-45c1-47d7-9da1-42b27fb2581e\scratchpad\INC-R1\red\inc-r1-proto-off3.log

- ON (ENABLE_PRODUCT_RESOLVER=true exported to the runner): 246 passed / 0 failed. OFF (nothing exported): 246 passed / 0 failed. Every row sets or deletes the flag itself (autouse fixture), so the ambient value cannot move a result; the flag-OFF byte identity is carried by P01 (28 nodes, the base literals and digests) and P02 (the nine FY25 digests) on the prototype.
- Earlier prototype runs: inc-r1-proto-on / -off on the first freeze: 246 passed each ([pyt] tag=inc-r1-proto-on start=2026-11-14 22:58:27 end=2026-11-14 22:58:43 elapsed=16s bound=600s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\fce5ef8e-45c1-47d7-9da1-42b27fb2581e\scratchpad\INC-R1\red\inc-r1-proto-on.log / [pyt] tag=inc-r1-proto-off start=2026-11-14 23:00:43 end=2026-11-14 23:00:59 elapsed=16s bound=600s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\fce5ef8e-45c1-47d7-9da1-42b27fb2581e\scratchpad\INC-R1\red\inc-r1-proto-off.log). inc-r1-proto-on2 / -off2 are INVALID (my setup error: the re-created scratch lacked data/fragrance_lines.json, which apply_proto.py does not write; 144 passed / 102 failed, 4 of them FileNotFoundError from the seam file's LINES_PATH reader) and are superseded by -on3 / -off3 on the same prototype bytes (every prototype file sha256-checked against <SP>/INC-R1/red/proto_built).
- Spec items the prototype showed need care: see section 7 (deviations) items on R1-R8, R1-R11 vs D7, 'pen', and the base `_debug_capture` key.

## 5. Step 6: the mutation table (scratch worktree; byte copies; one gate.py run of BOTH unit files per mutant; restore + sha256 verify)

Pass 1 (the pre-final test bytes, stopped after M07 to free the box; kept as a cross-check): M01 KILLED (46), M02 KILLED (15), M03 KILLED (14), M04 KILLED (2), M04b KILLED (2), M05 KILLED (2), M06 KILLED (6), M07 KILLED (2)

Pass 2 (authoritative; the test bytes of the first freeze: resolver 95ee2041..., seam 9c30052f...; the frozen resolver e47fa219... differs by ONE line, the R31 forbidden-list sentinel built by concatenation with the same runtime value, so no row's behaviour moved):

| id | file | mutant | expected killer | result | failing nodes (first) |
|---|---|---|---|---|---|
| M01 | app/services/product_resolver.py | product_resolver_enabled returns True whatever the env | P01, R02 | KILLED (46) | test_r02_flag_reader['true'], test_r02_flag_reader['1'], test_r02_flag_reader['yes'], test_r02_flag_reader['on'] |
| M02 | app/services/structured_comparison_service.py | the sync hook not gated | P01[rest] | KILLED (15) | test_p01_flag_off_identity[None-rest-gold4], test_p01_flag_off_identity[None-rest-owner], test_p01_flag_off_identity[''-rest-gold4], test_p01_flag_off_identity[''-rest-owner] |
| M03 | app/services/structured_comparison_service.py | the stream hook not gated | P01[stream] | KILLED (14) | test_p01_flag_off_identity[None-stream-gold4], test_p01_flag_off_identity[None-stream-owner], test_p01_flag_off_identity[''-stream-gold4], test_p01_flag_off_identity[''-stream-owner] |
| M04 | app/services/structured_comparison_service.py | the sync pair category without the resolver's parser_path | R04[rest-second_skin] | KILLED (2) | test_r04_pair_category[rest-owner], test_r04_pair_category[rest-second_skin] |
| M04b | app/services/structured_comparison_service.py | the stream twin (C-1) | R04[stream-second_skin] | KILLED (2) | test_r04_pair_category[stream-owner], test_r04_pair_category[stream-second_skin] |
| M05 | app/services/structured_comparison_service.py | the sync rewrite result not kept | R04 | KILLED (2) | test_r04_pair_category[rest-owner], test_r04_pair_category[rest-second_skin] |
| M06 | app/services/structured_comparison_service.py | the sync ask does not return | R05, R07, R08 | KILLED (6) | test_r05_sync_ask_before_any_fetch, test_r07_get_route_ask, test_r08_post_route_ask, test_r20_refusal_budget[off] |
| M07 | app/services/structured_comparison_service.py | the stream ask as a terminal payload | R06, R09 | KILLED (2) | test_r06_stream_ask_error_event, test_r09_stream_route_ask |
| M08 | app/services/structured_comparison_service.py | the sync resolver usage not tracked | R05, R13[rest] | KILLED (2) | test_r05_sync_ask_before_any_fetch, test_r13_model_arm_through_the_seam[rest] |
| M08b | app/services/structured_comparison_service.py | the stream resolver usage not tracked (C-1) | R13[stream] | KILLED (3) | test_r06_stream_ask_error_event, test_r09_stream_route_ask, test_r13_model_arm_through_the_seam[stream] |
| M09 | app/services/product_resolver.py | apply_resolution stops writing brand | R03, R36 | KILLED (10) | test_r36_apply_resolution, test_r03_owner_pair_rewritten[rest], test_r03_owner_pair_rewritten[stream], test_r12_consent2_owner_still_rewritten |
| M10 | app/services/product_resolver.py | the search_query drops the concentration | R03, R36 | KILLED (7) | test_r36_apply_resolution, test_r03_owner_pair_rewritten[rest], test_r03_owner_pair_rewritten[stream], test_r12_consent2_owner_still_rewritten |
| M11 | app/services/product_resolver.py | the category stamp removed | R04, R36 | KILLED (5) | test_r36_apply_resolution, test_r04_pair_category[rest-owner], test_r04_pair_category[rest-second_skin], test_r04_pair_category[stream-owner] |
| M12 | app/services/product_resolver.py | the long-token threshold 2 -> 1 | R09 Svauage | KILLED (1) | test_r09_house_words_and_osa[Svauage EDP] |
| M13 | app/services/product_resolver.py | the short-token threshold 1 -> 2 | R10 Tiger | KILLED (2) | test_r10_edit_rule_misses[Tiger], test_r17_claude_request_shape |
| M14 | app/services/product_resolver.py | the digit-exact branch removed | R10 Baccarat Rouge 541 | KILLED (1) | test_r10_edit_rule_misses[Baccarat Rouge 541] |
| M15 | app/services/product_resolver.py | the residual test removed | R11 | KILLED (8) | test_r06c_digit_outside_a_size_span_is_kept, test_r11_residual_not_high[Dior Sauvage Eau Forte], test_r11_residual_not_high[Creed Aventus for Her], test_r11_residual_not_high[YSL Libre Intense] |
| M16 | app/services/product_resolver.py | flankers matched by the edit rule | R12 old | KILLED (1) | test_r12_flankers |
| M17 | app/services/product_resolver.py | the house-consistency test removed | R13 | KILLED (1) | test_r13_house_conflict |
| M18 | app/services/product_resolver.py | guard (a) removed | R21 g2 | KILLED (1) | test_r21_guard[g2] |
| M19 | app/services/product_resolver.py | guard (b) accepts medium | R21 g3 | KILLED (1) | test_r21_guard[g3] |
| M20 | app/services/product_resolver.py | guard (c) removed | R21 g4 | KILLED (1) | test_r21_guard[g8b] |
| M21 | app/services/product_resolver.py | guard (d) removed | R21 g6, g11 | KILLED (3) | test_r21_guard[g6], test_r21_guard[g11], test_r22_decision[d9] |
| M22 | app/services/product_resolver.py | the Arabic-script test inverted | R21 g6, g8 | KILLED (4) | test_r21_guard[g6], test_r21_guard[g8], test_r21_guard[g11], test_r22_decision[d9] |
| M23 | app/services/product_resolver.py | an ask considered without a verdict | R22 d10, R14 | KILLED (26) | test_r10b_single_token_fuzzy_needs_pair_context[Tyger|iPhone 15|None], test_r10b_single_token_fuzzy_needs_pair_context[Tyger|iPhone 15|fragrances], test_r10b_single_token_fuzzy_needs_pair_context[Tyger EDP|iPhone 15|None], test_r10b_single_token_fuzzy_needs_pair_context[Tyger perfume|iPhone 15|None] |
| M24 | app/services/product_resolver.py | the ASK knob ignored | R22 d4 | KILLED (6) | test_r22_decision[d3], test_r22_decision[d4], test_r22_decision[d6], test_r22_decision[d7] |
| M25 | app/services/product_resolver.py | the R1-R3 (d) skip removed | R22 d12, d13 | KILLED (2) | test_r22_decision[d12], test_r22_decision[d13] |
| M26 | app/services/product_resolver.py | the wall removed (a bare await) | R23 | KILLED (18) | test_r22_decision[d2], test_r22_decision[d3], test_r22_decision[d4], test_r22_decision[d5] |
| M28 | app/services/product_resolver.py | a timed-out / raised call stored in the cache | R23 (second call) | KILLED (1) | test_r23_wall |
| M28b | app/services/product_resolver.py | a malformed answer stored in the cache | R26 (5) | KILLED (1) | test_r26_cache |
| M29 | app/services/product_resolver.py | a typed name logged in a [RESOLVE] line | R27 | KILLED (2) | test_r27_resolve_line, test_r14_partial_on_timeout |
| M30 | app/services/product_resolver.py | the never-raise guard of resolve_pair removed | R25 | KILLED (1) | test_r25_never_raises |
| M31 | app/services/product_resolver.py | refusal_result puts candidates before reason | R05, R37 | KILLED (4) | test_r37_refusal_result_and_extras, test_r05_sync_ask_before_any_fetch, test_r06_stream_ask_error_event, test_r09_stream_route_ask |
| M32 | app/services/product_resolver.py | the model answer overrides a lexicon-resolved side | R21, R22 d2 | KILLED (18) | test_r21_guard[g1], test_r21_guard[g2], test_r21_guard[g3], test_r21_guard[g4] |
| M33 | app/services/product_resolver.py | http_detail_extras without its flag test | R11 pin_pr_off | KILLED (3) | test_r37_refusal_result_and_extras, test_r11_builder_flag_mix[pin_pr_off], test_r11_builder_flag_mix[pin_rg_on_pr_off] |
| M34 | app/services/llm_router.py | the resolve cap 384 -> 256 | R16, R17 | KILLED (2) | test_r16_router_site_no_format, test_r17_claude_request_shape |
| M35 | app/services/llm_router.py | the resolve site with a closed schema (R1-R7) | R16, R17 | KILLED (2) | test_r16_router_site_no_format, test_r17_claude_request_shape |
| M37 | app/middleware/error_handler.py | the envelope block not gated | R10 pin cases | KILLED (2) | test_r10_envelope_pin[pin_rg_off_pr_off], test_r10_envelope_pin[pin_rg_on_pr_off] |
| M38 | app/middleware/error_handler.py | _resolver_candidates accepts five items | R10 five_items | KILLED (1) | test_r10_envelope_bad_candidates_dropped[five_items] |
| M39 | app/middleware/error_handler.py | setdefault -> assignment (EQUIVALENT by the spec) | equivalent | SURVIVED (0) |  |
| M40 | app/services/product_resolver.py | R1-R3 (a): a house hit is a fragrance despite a non-fragrance term | R14, R22 d15b | KILLED (2) | test_r14_house_only_nothing_and_non_fragrance, test_r22_decision[d15b] |
| M41 | app/services/product_resolver.py | R1-R3 (b): the deterministic signal overrides the model's verdict | R22 d16, d17 | KILLED (2) | test_r22_decision[d16], test_r22_decision[d17] |
| M42 | app/services/product_resolver.py | R1-R3 (d): the non-fragrance chip skip removed | R22 d13 | KILLED (1) | test_r22_decision[d13] |
| M43 | app/services/product_resolver.py | R1-R3 (d): the keyword-classify skip removed | R22 d12 | KILLED (1) | test_r22_decision[d12] |
| M44 | app/services/product_resolver.py | R1-R4: the qualifier drop removed | R11b | KILLED (6) | test_r11b_qualifiers_dropped_from_the_residual[Dior Sauvage for men], test_r11b_qualifiers_dropped_from_the_residual[Bleu de Chanel pour homme], test_r11b_qualifiers_dropped_from_the_residual[Dior Sauvage EDP 100ml tester], test_r11b_qualifiers_dropped_from_the_residual[Creed Aventus original] |
| M45 | app/services/product_resolver.py | R1-R4: qualifiers removed before the line search | R11d | KILLED (2) | test_r11b_qualifiers_dropped_from_the_residual[Bleu de Chanel pour homme], test_r11d_qualifiers_never_removed_before_the_line_search |
| M46 | app/services/product_resolver.py | R1-R4: her treated as a qualifier | R11 for Her | KILLED (1) | test_r11_residual_not_high[Creed Aventus for Her] |
| M47 | app/services/product_resolver.py | R1-R4: qualifiers not allowed outside the guard-(d) window | R21 g12 | KILLED (1) | test_r21_guard[g12] |
| M48 | app/services/product_resolver.py | R1-R5: a bare digit token removed | R06c, R08 BR540 | KILLED (7) | test_r06b_span_based_size[Baccarat Rouge 540 70 ml], test_r06b_span_based_size[Baccarat Rouge 540 Extrait 70ml], test_r06b_span_based_size[MFK Baccarat Rouge 540 Extrait 70ml], test_r06b_span_based_size[Baccarat Rouge 540] |
| M49 | app/services/product_resolver.py | R1-R6: the model arm not gated on decide('text') == 'anthropic' | R28, R26 (2), R12b | KILLED (11) | test_r10b_single_token_fuzzy_needs_pair_context[Tyger|iPhone 15|None], test_r10b_single_token_fuzzy_needs_pair_context[Tyger|iPhone 15|fragrances], test_r10b_single_token_fuzzy_needs_pair_context[Tyger EDP|iPhone 15|None], test_r10b_single_token_fuzzy_needs_pair_context[Tyger perfume|iPhone 15|None] |
| M51 | app/services/product_resolver.py | R1-R8: a single-token fuzzy line high without context | R10b | KILLED (3) | test_r10b_single_token_fuzzy_needs_pair_context[Tyger|iPhone 15|None], test_r10b_single_token_fuzzy_needs_pair_context[Sausage|iPhone 15|None], test_r10b_single_token_fuzzy_needs_pair_context[Euros|iPhone 15|None] |
| M52 | app/services/product_resolver.py | R1-R8: the chip is not a context | R10b chip | KILLED (3) | test_r10b_single_token_fuzzy_needs_pair_context[Tyger|iPhone 15|fragrances], test_r21_hook_passes_the_chip[rest], test_r21_hook_passes_the_chip[stream] |
| M52b | app/services/product_resolver.py | R1-R8: the resolved partner is not a context | R07, R10b owner | KILLED (7) | test_r07_owner_pair_lexicon, test_r10b_single_token_fuzzy_needs_pair_context[stronger with you|Tyger|None], test_r20_call_count, test_r27_resolve_line |
| M53 | app/api/text_routes.py | R1-R9: the sync ask refund without the keys | R07, R08 | KILLED (4) | test_r07_get_route_ask, test_r08_post_route_ask, test_r20_refusal_budget[off], test_r20_refusal_budget[on_open] |
| M53b | app/api/text_routes.py | R1-R9: the stream ask refund without the keys | R09 | KILLED (1) | test_r09_stream_route_ask |
| M53c | app/api/text_routes.py | R1-R9: the GET ask through the generic failure arm | R07, R20 | KILLED (4) | test_r07_get_route_ask, test_r20_refusal_budget[off], test_r20_refusal_budget[on_open], test_r20_refusal_budget[on_spent] |
| M54 | app/api/text_routes.py | R1-R10: the ask not counted on the refusal budget | R20 on_open | KILLED (1) | test_r20_refusal_budget[on_open] |
| M54b | app/api/text_routes.py | R1-R10: a spent budget still refunds | R20 on_spent | KILLED (1) | test_r20_refusal_budget[on_spent] |
| M55 | app/services/product_resolver.py | R1-R11: a typed concentration outside the line resolves high | R35 | KILLED (2) | test_r35_typed_concentration_outside_the_line[Lattafa Khamrah EDT], test_r35_typed_concentration_outside_the_line[Creed Aventus EDT] |
| M56 | app/services/product_resolver.py | R1-R15: a rejected high is_fragrance true no longer asks | R22 d9 | KILLED (1) | test_r22_decision[d9] |
| M57 | app/services/product_resolver.py | R1-R16: cached always 0 | R26 | KILLED (1) | test_r26_cache |
| M58 | app/middleware/error_handler.py | R1-R18 (RC-2): the envelope reads the flag first | R10 no_flag_read | KILLED (3) | test_r10_envelope_no_flag_read_without_the_marker[string_404], test_r10_envelope_no_flag_read_without_the_marker[timeout_503], test_r10_envelope_no_flag_read_without_the_marker[usage_429] |
| M59 | app/services/product_resolver.py | R1-R23: the model's concentration used when none is typed | R21 g1, R13 | KILLED (5) | test_r21_guard[g1], test_r21_guard[g8], test_r21_guard[g9], test_r13_model_arm_through_the_seam[rest] |
| M59b | app/services/product_resolver.py | R1-R23: the seed line's base not used | R21 g8 | KILLED (1) | test_r21_guard[g8] |
| M60 | app/services/product_resolver.py | C-2: candidate concentrations not normalized | R21 g11, g13 | KILLED (2) | test_r21_guard[g11], test_r21_guard[g13] |
| M61 | app/services/product_resolver.py | C-4: the concentration doubled | R34 | KILLED (1) | test_r34_no_doubled_concentration |
| M62 | app/services/structured_comparison_service.py | C-7: the sync hook not total | R19 | KILLED (2) | test_r19_hook_is_total[apply_raises], test_r19_hook_is_total[refusal_raises] |
| M63 | app/services/product_resolver.py | C-14: a typed-token brand logged | R27 | KILLED (1) | test_r27_resolve_line |
| M64 | app/services/structured_comparison_service.py | C-7: the hook does not restore the base dicts | R19 apply_raises | KILLED (1) | test_r19_hook_is_total[apply_raises] |
| M69 | app/services/structured_comparison_service.py | C-3: a knob read before the flag | P01 knob reads | KILLED (14) | test_p01_flag_off_identity[None-rest-gold4], test_p01_flag_off_identity[None-rest-owner], test_p01_flag_off_identity[''-rest-gold4], test_p01_flag_off_identity[''-rest-owner] |
| M70 | app/services/structured_comparison_service.py | C-3: the lines file opened before the flag | P01 lines opens | KILLED (14) | test_p01_flag_off_identity[None-rest-gold4], test_p01_flag_off_identity[None-rest-owner], test_p01_flag_off_identity[''-rest-gold4], test_p01_flag_off_identity[''-rest-owner] |
| M71 | app/services/structured_comparison_service.py | R1-R8: the sync hook drops the chip | R21[rest] (seam) | KILLED (1) | test_r21_hook_passes_the_chip[rest] |
| M71b | app/services/structured_comparison_service.py | R1-R8: the stream hook drops the chip | R21[stream] (seam) | KILLED (1) | test_r21_hook_passes_the_chip[stream] |
| M72 | app/services/product_resolver.py | 2.1: the wall knob read when no call is dispatched | R22 (TIMEOUT read only with a call) | KILLED (5) | test_r22_decision[d1], test_r22_decision[d12], test_r22_decision[d13], test_r22_decision[d18] |

- 74 mutants run, 73 KILLED, 1 SURVIVED; every restore sha256-verified: True. M27 (the cache key without the provider decision) is equivalent by design under R1-R6 (not run); M39 is the spec's own equivalent.

## 6. Step 7: the comm set at the base (real worktree)

- List: <SP>/INC-R1/red/comm_list.txt (499 files); per-file reasons: <SP>/INC-R1/red/comm_reasons.tsv; classes: <SP>/INC-R1/red/comm_set.json (the spec's comm_set.py rule re-run, plus E6's importers (test_s81_s22b) and C-11 / C-12: tests/test_inc_mon1_gate_rows.py joins; minus the four tests/test_precommit_hook*.py; no NETWORK_FLAKY_EXCLUDE set exists).
- Totals: {'passed': 25162, 'failed': 25, 'error': 2, 'skipped': 88}; FAILED / ERROR ids: 27.

    [pyt] tag=inc-r1-base-c01 start=2026-11-14 22:23:07 end=2026-11-14 22:23:43 elapsed=36s bound=1200s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\fce5ef8e-45c1-47d7-9da1-42b27fb2581e\scratchpad\INC-R1\red\inc-r1-base-c01.log
    [pyt] tag=inc-r1-base-c02 start=2026-11-14 22:23:50 end=2026-11-14 22:24:29 elapsed=39s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\fce5ef8e-45c1-47d7-9da1-42b27fb2581e\scratchpad\INC-R1\red\inc-r1-base-c02.log
    [pyt] tag=inc-r1-base-c03 start=2026-11-14 22:24:36 end=2026-11-14 22:25:35 elapsed=59s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\fce5ef8e-45c1-47d7-9da1-42b27fb2581e\scratchpad\INC-R1\red\inc-r1-base-c03.log
    [pyt] tag=inc-r1-base-c04 start=2026-11-14 22:25:42 end=2026-11-14 22:25:56 elapsed=14s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\fce5ef8e-45c1-47d7-9da1-42b27fb2581e\scratchpad\INC-R1\red\inc-r1-base-c04.log
    [pyt] tag=inc-r1-base-c05 start=2026-11-14 22:26:35 end=2026-11-14 22:27:36 elapsed=61s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\fce5ef8e-45c1-47d7-9da1-42b27fb2581e\scratchpad\INC-R1\red\inc-r1-base-c05.log
    [pyt] tag=inc-r1-base-c06 start=2026-11-14 22:27:43 end=2026-11-14 22:29:06 elapsed=83s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\fce5ef8e-45c1-47d7-9da1-42b27fb2581e\scratchpad\INC-R1\red\inc-r1-base-c06.log
    [pyt] tag=inc-r1-base-c07 start=2026-11-14 22:29:12 end=2026-11-14 22:29:50 elapsed=38s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\fce5ef8e-45c1-47d7-9da1-42b27fb2581e\scratchpad\INC-R1\red\inc-r1-base-c07.log
    [pyt] tag=inc-r1-base-c08 start=2026-11-14 22:30:13 end=2026-11-14 22:30:29 elapsed=16s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\fce5ef8e-45c1-47d7-9da1-42b27fb2581e\scratchpad\INC-R1\red\inc-r1-base-c08.log
    [pyt] tag=inc-r1-base-c09 start=2026-11-14 22:30:52 end=2026-11-14 22:31:21 elapsed=29s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\fce5ef8e-45c1-47d7-9da1-42b27fb2581e\scratchpad\INC-R1\red\inc-r1-base-c09.log
    [pyt] tag=inc-r1-base-c10 start=2026-11-14 22:31:44 end=2026-11-14 22:32:21 elapsed=37s bound=1200s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\fce5ef8e-45c1-47d7-9da1-42b27fb2581e\scratchpad\INC-R1\red\inc-r1-base-c10.log
    [pyt] tag=inc-r1-base-c11 start=2026-11-14 22:36:25 end=2026-11-14 22:36:56 elapsed=31s bound=1200s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\fce5ef8e-45c1-47d7-9da1-42b27fb2581e\scratchpad\INC-R1\red\inc-r1-base-c11.log
    [pyt] tag=inc-r1-base-c12 start=2026-11-14 22:40:44 end=2026-11-14 22:43:23 elapsed=159s bound=1200s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\fce5ef8e-45c1-47d7-9da1-42b27fb2581e\scratchpad\INC-R1\red\inc-r1-base-c12.log
    [pyt] tag=inc-r1-base-c13 start=2026-11-14 22:46:55 end=2026-11-14 22:48:26 elapsed=91s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\fce5ef8e-45c1-47d7-9da1-42b27fb2581e\scratchpad\INC-R1\red\inc-r1-base-c13.log
    [pyt] tag=inc-r1-base-c14 start=2026-11-14 22:53:17 end=2026-11-14 22:54:25 elapsed=67s bound=1200s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\fce5ef8e-45c1-47d7-9da1-42b27fb2581e\scratchpad\INC-R1\red\inc-r1-base-c14.log
    [pyt] tag=inc-r1-base-c15 start=2026-11-14 22:58:44 end=2026-11-14 23:00:39 elapsed=115s bound=1200s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\fce5ef8e-45c1-47d7-9da1-42b27fb2581e\scratchpad\INC-R1\red\inc-r1-base-c15.log
    [pyt] tag=inc-r1-base-c16 start=2026-11-14 23:01:02 end=2026-11-14 23:01:54 elapsed=52s bound=1200s status=FAIL rc=1 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\fce5ef8e-45c1-47d7-9da1-42b27fb2581e\scratchpad\INC-R1\red\inc-r1-base-c16.log
    [pyt] tag=inc-r1-base-c17 start=2026-11-14 23:02:17 end=2026-11-14 23:03:23 elapsed=66s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\fce5ef8e-45c1-47d7-9da1-42b27fb2581e\scratchpad\INC-R1\red\inc-r1-base-c17.log
    [pyt] tag=inc-r1-base-c18 start=2026-11-14 23:03:46 end=2026-11-14 23:04:40 elapsed=54s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\fce5ef8e-45c1-47d7-9da1-42b27fb2581e\scratchpad\INC-R1\red\inc-r1-base-c18.log
    [pyt] tag=inc-r1-base-c19 start=2026-11-14 23:04:47 end=2026-11-14 23:05:34 elapsed=47s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\fce5ef8e-45c1-47d7-9da1-42b27fb2581e\scratchpad\INC-R1\red\inc-r1-base-c19.log
    [pyt] tag=inc-r1-base-c20 start=2026-11-14 23:05:41 end=2026-11-14 23:06:15 elapsed=35s bound=1200s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\fce5ef8e-45c1-47d7-9da1-42b27fb2581e\scratchpad\INC-R1\red\inc-r1-base-c20.log

- Base record stored (LC-6): <SP>/harness/base_records/731bcddf531a7e123963246168ca19f262859337/8c08a677ae410947faebd4e43a40a92206272715e4a8e86d675c84692c667deb.{txt,files,header.txt,pyt.log} (27 ids).
- Cross-check vs INC-I1's 731bcddf record 5e2f0266... (710 files, 28 ids): every INC-I1 id inside the 460 shared files is among mine; mine adds ONE id, tests/test_retro_w0_4.py::test_cpu_bound_parse_keeps_the_max_loop_gap_bounded_under_flag[scs._fetch_page_price] (174 ms > the 150 ms bound under box contention), re-run ALONE at the base: 9 passed (a LOAD FLAKE; [pyt] tag=inc-r1-base-w04-rerun start=2026-11-14 23:12:11 end=2026-11-14 23:12:17 elapsed=6s bound=600s status=OK rc=0).
- Every other id is a pre-existing base failure: the two cold-tiktoken test_prompt_truth ERROR nodes and test_s81_s10_fragrance_gate.py::test_r06_production_lexicon_content (spec 1.10), and the CRLF self-checks of this core.autocrlf=true box, test_auth_interceptor x2, test_page_scraping x2, test_s81_d22c p1 golden x5 (all in INC-I1's record).

FAILED / ERROR ids at the base:

- failed tests/test_auth_interceptor.py::test_sign_in_with_social_exception (inc-r1-base-c01)
- failed tests/test_auth_interceptor.py::test_social_login_user_insert_fails_gracefully (inc-r1-base-c01)
- failed tests/test_page_scraping.py::TestFetchPagePriceJsonLD::test_jsonld_nested_offers_picks_lowest (inc-r1-base-c10)
- failed tests/test_page_scraping.py::TestFetchPagePriceOpenGraph::test_og_meta_extraction (inc-r1-base-c10)
- error tests/test_prompt_truth.py::test_truth_on_prefix_static_and_cacheable (inc-r1-base-c11)
- error tests/test_prompt_truth.py::test_render_digests_match_base_except_the_fence (inc-r1-base-c11)
- failed tests/test_retro_w0_4.py::test_cpu_bound_parse_keeps_the_max_loop_gap_bounded_under_flag[scs._fetch_page_price] (inc-r1-base-c12)
- failed tests/test_s81_d16_operator_ingest.py::test_r10_runbook_names_only (inc-r1-base-c14)
- failed tests/test_s81_d17_coverage.py::test_r9_railway_config_and_hygiene (inc-r1-base-c14)
- failed tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[unset] (inc-r1-base-c14)
- failed tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[empty] (inc-r1-base-c14)
- failed tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[false] (inc-r1-base-c14)
- failed tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[pad0] (inc-r1-base-c14)
- failed tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[OFF] (inc-r1-base-c14)
- failed tests/test_s81_s07_meas_harness.py::test_r35_fixtures (inc-r1-base-c15)
- failed tests/test_s81_s10_fragrance_gate.py::test_r06_production_lexicon_content (inc-r1-base-c15)
- failed tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[kb_seed_common] (inc-r1-base-c15)
- failed tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[seed_kb_batch] (inc-r1-base-c15)
- failed tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[seed_kb_brands_wikidata] (inc-r1-base-c15)
- failed tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[cron_feed_walker] (inc-r1-base-c15)
- failed tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[cron_pdp_discovery] (inc-r1-base-c15)
- failed tests/test_s81_s18b_store_label.py::test_r2_table_shape (inc-r1-base-c15)
- failed tests/test_s81_s19_gap_queue.py::test_r15_hygiene (inc-r1-base-c15)
- failed tests/test_s81_s22_compare_runs.py::test_b02_one_transaction_ascii_lf (inc-r1-base-c16)
- failed tests/test_s81_s22_judge.py::test_j01_script_exists_and_off_first (inc-r1-base-c16)
- failed tests/test_s81_s24_auth_throttle.py::test_r92_hygiene (inc-r1-base-c16)
- failed tests/test_s81_s24_auth_throttle.py::test_p83_red_file_setenv_hygiene (inc-r1-base-c16)

## 7. Deviations from the spec (as amended)

- R1-R2 applied: llm_router.route stays byte-equal; the spec rows R30 / P30b, the R16 NO_ESCALATION_SITES and '17 sites' docstring assertions and mutant M36 are dropped; R16 instead pins SITES['resolve'] and the 16 base rows unchanged (P16).
- R1-R7 applied: SITES['resolve'] = SiteSpec('text', 384, None, True): R16 asserts output_schema None; R17 asserts output_config == {'effort': 'low'} (no format) and system == RESOLVE_SYSTEM_PROMPT + blank line + llm_router.JSON_ONLY_INSTRUCTION; the spec R01 equality CONCENTRATIONS == llm_router.RESOLVE_CONCENTRATIONS[:-1] is dropped (no router schema, R1-R29); mutant M35 is re-cut to 'the resolve row carries a schema'.
- R1-R6 applied: R26 (2) now pins that the consent-2 call makes NO create at all and is not served the consent-3 cache entry (the spec said one OpenAI create); R28 pins no route call at consent 2 / text role OFF / PRE_V3 OFF (the spec pinned ONE WARNING class=OpenAIEgressStoppedError, which cannot exist once the call is skipped); R12b (seam) pins the same through the compare.
- R1-R8 makes the deterministic arm pair-aware while the spec signature is resolve_lexicon(name): every context-dependent case (Tyger, Sausage, Euros, the chip, the resolved partner) is pinned through resolve_pair (R07, R10b) and through the hook (seam R21); resolve_lexicon(name) is asserted only for names whose result needs no pair context (exact or residual names, and a fuzzy single token next to its own concentration word, 'Svauage EDP'). The prototype added a keyword context=False.
- R1-R15 applied: R22 d9 (both sides rejected by guard (d), is_fragrance true high, no chip) is ASK (the spec pinned passthrough).
- R1-R23 applied: R21 g1 concentration None (the spec had EDP) and seam R13 variant None / search_query without a concentration (the spec had EDP); R21 g8 pins EDT from the seed line's base with the model answering none.
- R1-R9 applied on all three routes: R07 / R08 / R09 pin ONE refund carrying the consume's keys (the spec pinned keys None and the generic labels usage_refund.text.get / .post / text_stream and the failure row's error_message == ASK_MESSAGE); the RED does not pin a refund label nor the failure row's error_message, because the _result_gate_exit form's twin is GREEN's to name.
- spec R03 'no key starting with _ in products, overview.products or any SSE event': measured at the base, the products carry `_debug_capture` with the flag OFF; R03 pins the flag-ON private-key set equal to the flag-OFF one and no `_explicit`.
- spec R12 case 'stronger with you parfum' (-> line Stronger With You, concentration Parfum) is NOT frozen: R1-R11 (a typed concentration outside the line's concentrations is MEDIUM) collides with D7 (a concentration-word flanker is carried as the concentration): Stronger With You lists concentrations ['EDT'] and 'Parfum' only as a flanker. Open question Q2.
- R1-R3 (a) lists 'pen' among the non-fragrance terms; data/fragrance_lexicon.json has no 'pen' (fashion has bag / coat / jacket / watch / shoes): R14 pins 'Montblanc pen' is_fragrance False, so GREEN needs a resolver-local term (the prototype carries EXTRA_NON_FRAGRANCE = {pen, pens}). Open question Q3.
- R1-R18 / RC-2 applied: the envelope reads ENABLE_PRODUCT_RESOLVER only after the refusal marker (code INSUFFICIENT_DATA + reason placeholder_identity) matches: R10 no-flag-read PIN rows (a string 404, a TIMEOUT 503, a USAGE_LIMIT 429); the spec's C6 put the flag read FIRST.
- R1-R16: the position of cached=<0|1> in the [RESOLVE] line is not ruled; R26 / R27 accept it anywhere and match the 2.9 template on the rest.
- P01 digests are pinned as base64 of the FY sha256 (H7 / the added-line sweep), recorded at the base twice (equal): rest/owner q7i69NY9..., stream/owner lfcvKz4n..., rest/gold4 ZI7G6Lsc..., stream/gold4 OHSHsAHY... .
- R1-R10 applied as a new seam row R20 (gate OFF: refunded with keys, nothing read or counted; gate ON with an open budget: counted once; gate ON with a spent budget: the credit kept, not counted), the exact S81-20 semantics.
- C-7 applied as seam R19: an exception in apply_resolution (after it mutated a dict) or in refusal_result falls back to the base Step-1 dicts with ONE WARNING naming the type; the exception text appears in no record.
- Rows added beyond the spec numbering: resolver R06b / R06c (R1-R5), R10b (R1-R8), R11b / R11c / R11d (R1-R4), R21b (g7 with the seam lines file), R26b (the 2,000-entry LRU), R34 (C-4), R35 (R1-R11), R36 (apply_resolution), R37 (refusal_result / http_detail_extras), P16 (the base SITES rows); seam R12b, R13b (the ledger), R19 (C-7), R20 (R1-R10), R21 (the hook passes the chip); the spec's R10 / R11 / R15 PIN cases are split into named PIN functions.
- R22 d14 is folded into every R22 case (the ASK knob read iff an ask would result) and R22 also pins the TIMEOUT knob read iff a call is dispatched (spec 2.1).
- spec 1.10 B6 says the base comm set is 498 files: with C-12 (tests/test_inc_mon1_gate_rows.py) it is 499; no NETWORK_FLAKY_EXCLUDE set exists on this lane.
- Base noise not named in spec 1.10: tests/test_s81_s07_meas_harness.py::test_r35_fixtures fails at the base on this box (the fixtures are CRLF in a core.autocrlf=true working copy); it is in INC-I1's 731bcddf base record too.
- spec M27 (the cache key without the provider decision) is EQUIVALENT in the ruled design: R1-R6 makes decide('text') == 'anthropic' the gate of the whole model arm, so the cache is never read for another provider (the gate itself is mutant M49, killed); not run, reported for a ruling.

## 8. Questions for the gate (recommended answer first)

- Q1 (R1-R26 vs R1-R6): check 4 of the phone proof names 'the OpenAIEgressStoppedError class WARNING' as primary backing, but R1-R6 skips the call below consent 3, so that WARNING cannot appear for the resolve site. Recommended: the check-4 backing is the [RESOLVE] line with no llm side and outcome passthrough (plus no api.anthropic.com line in a quiet window).
- Q2 (R1-R11 vs D7): 'stronger with you parfum': HIGH (Parfum is a listed flanker carried as the concentration) or MEDIUM (outside the line's concentrations)? Recommended: HIGH, by reading R1-R11 as 'outside the line's concentrations and its concentration-word flankers' (the product exists); the RED froze neither.
- Q3 (R1-R3 (a) 'pen'): confirm a resolver-local non-fragrance term list (pen, pens) beside category_gate.scan, as the RED pins, rather than editing the lexicon (data/fragrance_lexicon.json is S81-10's, out of scope).
- Q4 (M27): rule the cache-key mutant equivalent under R1-R6 (the decide gate precedes the cache).
- Q5 (M39): the spec's own equivalent (setdefault vs assignment of reason in the envelope) stays equivalent; confirm.

## 9. Restore check and NOT MEASURED

    real worktree HEAD 731bcddf531a7e123963246168ca19f262859337 (== base 731bcddf531a7e123963246168ca19f262859337)
    sha256 of all 3595 tracked files at the end == at the start (manifest_before.json vs manifest_after2.json): 0 differing
    git status --short:
      ?? tests/test_inc_r1_resolver.py
      ?? tests/test_inc_r1_seam.py
    the scratch worktree <SP>/INC-R1/INC-R1_scratch was created three times (the prototype + mutation passes; the re-freeze checks) and removed each time with git worktree remove --force (rc 0); git worktree list no longer shows it; it never held a node_modules junction
    mutation lock <scratch>/.qa-mutation.lock removed (by the driver after pass 2; by hand after the stopped pass 1)
    no INC-R1 pytest / runner / driver process alive (Win32_Process scan); leftover monitor grep / tail processes of this agent were stopped

- NOT MEASURED in this round: the resolve site's live latency (unmeasurable hermetically, SL8); the head comm set, the CI-order set and the fourteen client fences (GREEN's gates G5-G7).

