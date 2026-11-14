# INC-I1 PICTURE-MUST-MATCH: RED report (RED round; Opus 5.5 RED agent of the S95-FIX lane; 2026-11-14)

- Unit: INC-I1 PICTURE-MUST-MATCH. Flag `ENABLE_IMAGE_RELEVANCE_GUARD` (new, default OFF, read per call); knob `IMAGE_RELEVANCE_CANDIDATES`.
- Real worktree: `C:/Users/SynAckITPC/Documents/AI/sc-inc-i1` (detached, HEAD = base `731bcddf531a7e123963246168ca19f262859337`). Only two NEW files were added there; no git write ran in it (the one git write of this round: the detached scratch worktree `<SP>/INC-I1/INC-I1_scratch`, created at the base and removed with `git worktree remove --force` after the mutation run).
- Inputs read in full at the start and again before this report: the common brief `<SP>/wf/inc-common.txt` (H0-H12 + the session-81 rules); the spec `.qa-s80/INC-I1_UNIT_SPEC.md` sha256 `5539e84481bf3094b86d32554877f0a1063e597c89ecc5a153b5cda2e6c9d3c4` (110,532 B; byte-equal to the assembled `<SP>/INC-I1/spec/part1..4.txt`, read there); the review `.qa-s80/INC-I1_SPEC_REVIEW.md` sha256 `5b1df569ab750ca4883d363462e5e4e00bede20d16c890862a41936914380710` (36,841 B; copied by `red/wtcp.py` and read from the copy); the rulings `<SP>/INC-I1/RULINGS_INC_I1.md` (I1-R1..I1-R21, binding; precedence rulings > review corrections > spec). PLAN_S81 / RULINGS_INC_R0 were not re-read beyond what the spec and review cite (the rulings file settles every point this round needed).
- Notes kept from the first measurement: `<SP>/INC-I1/red/notes.md`. Every pytest ran through `<SP>/harness/gate.py` (the runner was never called directly; no wait inside a runner); one pytest at a time (sequential drivers `red/seqrun.py`, `red/proto/mutdrv.py`).
- Production flag state used (names only): common brief H12 (c) (newest dated relay lines): `ENABLE_DATA_GUARDS_V2` and `ENABLE_IMAGE_PIPELINE_V2` OFF on web; `ENABLE_IMAGE_RELEVANCE_GUARD` is a new, unset name. Every row sets or deletes each flag it depends on (autouse delenv + per-row setenv).

## 0. Files written (the only change in the real worktree)

| Path | sha256 | bytes | notes |
|---|---|---|---|
| tests/test_inc_i1_picture_must_match.py (file A) | `e34614401f70599fdbd83da477b2cb19268863dee49b3a416eed4a77f9f5a08f` | 50539 | pure ASCII, LF, black 26.5.1 clean, ruff E9/F63/F7/F82 clean, no 8-digit run, no credential shape (the OPENAI placeholder is concatenated as in the X2a file), banned hosts concatenated at run time |
| tests/test_inc_i1_noon_and_wiring.py (file B) | `96153bd679ca30ee37d0232b90df9ec0f86b48be02089a2270663836a148dfb0` | 17086 | same checks |

`git status --short` of the real worktree at the end:
```
?? tests/test_inc_i1_noon_and_wiring.py
?? tests/test_inc_i1_picture_must_match.py
```

## 1. Base-state runs of spec 1.10 (DEFERRED TO RED; run ALONE at base, before any new file existed)

```
[pyt] tag=inc-i1-base-img start=2026-11-14 20:37:18 end=2026-11-14 20:37:26 elapsed=9s bound=600s status=OK rc=0   (112 passed; [hermeticity] sentinel checked 112 test(s); [netguard] blocked 3 attempt(s) from 1 node(s): tests/test_comparison_response_image_url.py::TestOrchestratorWiring::test_organic_results_passed_to_image_service [egress] socket.getaddrinfo api.openai.com:443; [gate] waited=58s)
[pyt] tag=inc-i1-base-pins start=2026-11-14 20:37:33 end=2026-11-14 20:38:00 elapsed=27s bound=1200s status=OK rc=0  (972 passed; [hermeticity] 972; [netguard] blocked 0)
[pyt] tag=inc-i1-base-scan start=2026-11-14 20:44:35 end=2026-11-14 20:45:01 elapsed=26s bound=1200s status=OK rc=0  (371 passed; [hermeticity] 371; [netguard] blocked 0; [gate] waited=394s)
```
FAILED / ERROR set at base for the three sets: EMPTY. The one netguard block is base noise of an existing node that passes and is listed in the committed `tests/.network_attempt_baseline.txt` (line 30, class egress). Commands exactly as spec 1.10 (logs `<SP>/INC-I1/red/base_img.log`, `base_pins.log`, `base_scan.log`).

## 2. The RED files: row map (spec 5 as amended by the rulings and the review)

File A `tests/test_inc_i1_picture_must_match.py` (the leaf + the cascade):

| Row | Test (nodes) | Source | At base |
|---|---|---|---|
| A-R01 | test_r01_flag_reader_table | spec 2.1 | RED (leaf missing) |
| A-R02 | test_r02_knob_table | spec 2.1 as amended by I1-R7 ("0" / "-3" / "0.5" -> 1, "11" / "15" -> 10, "" / "abc" / "inf" / "-inf" / "nan" -> 5, "7.9" -> 7) | RED |
| A-R03 | test_r03_relevance_truth_table (55 nodes) | spec 2.2 T1-T19 (+T10r reversed), T20 -> None and T21 (I1-R2), T18b / T18c (spec 2.2 item 5 "sauvage.example never proves the line"), X1 / X1t / X2 / X2t / X3 / X4 (I1-R3), X4t / X11 / X11t and U-sp-ml|oz|fl|g|gm / U-at-ml|oz|fl|g|gm (I1-R4 c, spaced and attached), X6 (I1-R4 a), X7 / X8 (I1-R4 b), X9 / X10 / X12 (review, I1-R20), E1 (an empty significant-token line never passes), P-0..P-4 (I1-R12 plurals incl. the Arabic plural) | RED |
| A-R04 | test_r04_image_query | spec 2.2 item 6 | RED |
| A-R05 | test_r05_first_https_raster | spec 2.2 item 7 (+ a non-public `*.example.test` host) | RED |
| A-R06 | test_r06_leaf_import_shape | spec 5.2 widened by I1-R1 (deny_hosts allowed at module level) + pure ASCII | RED |
| A-R07 | test_r07_alias_reuse | spec 2.2 item 2, I1-R18 | RED |
| A-R08 | test_r08_tyger_poem_rejected_at_tier1 | spec 5.2 | RED (keyword missing) |
| A-R09 | test_r09_kg_poem_rejected_tier1_bottle_accepted | spec 5.2 | RED |
| A-R10 | test_r10_walk_order_and_knob | spec 5.2 | RED |
| A-R11 | test_r11_https_on_every_tier | spec 5.2 (the c-case line asserted: reason scheme) | RED |
| A-R12 | test_r12_search_payload_each_item_tested | spec 5.2 | RED |
| A-R13 | test_r13_tier3_precondition_and_pick | spec 5.2 (the a-case line asserted: tier=none outcome=none candidates=0 reason=none, spec 2.2 item 8 + 2.6) | RED |
| A-R14 | test_r14_one_line_closed_grammar | spec 5.2, the regex gains `denied` (I1-R1); paths of A-R08..A-R13 + a deny path + a KG-type path | RED |
| A-R15 | test_r15_cancel_under_the_flag | spec 5.2 | RED |
| A-R16 | test_r16_flag_off_with_relevance_is_the_base_call [None, false, 0, garbage] | spec 5.2 (knob patched to record-and-raise) | RED |
| A-R17 | test_r17_denied_candidate_rejected_on_every_tier [9: serper_frag, serper_image_url, serper_link, serper_source, serper_domain, kg_image_url, organic_link, images_source, piggyback] | I1-R1 (DG OFF, reason denied, every tier and channel) | RED |
| A-R18 | test_r18_fragrantica_item_rejected_in_both_guard_states [None, true] | I1-R1 (the X5 shape passes the relevance test; DG OFF and ON) | RED |
| A-R19 | test_r19_denied_organic_never_opens_tier3 [None, true] | I1-R1 | RED |
| A-R20 | test_r20_kg_type_serves_the_fragrance_word_only | I1-R5 (Sauvage/Perfume accepted; The Tyger/Poem fragrance_word; type never the line; type never the brand) | RED |
| A-R21 | test_r21_tier3_pick_needs_a_raster_path_and_is_no_page | I1-R10 (svg and extension-less picks rejected; a pick equal to an organic link rejected; a raster path with a query accepted) | RED |
| A-R22 | test_r22_tier3_reads_organic_first_ten | I1-R20 (organic[:10] for the precondition and the related-host test) | RED |
| A-R23 | test_r23_tier3_related_but_failing_item_reason | review C-2 / R-8 e (I1-R20) | RED |
| A-R24 | test_r24_brand_from_source_link_or_domain | I1-3 brand channels at Tier 1 + review C-2 (images-block domain) | RED |
| A-R25 | test_r25_kg_https_preference_and_snake_key | review C-2 / R-8 b, c | RED |
| A-P01 | test_p01_base_call_full_config | spec F2 | PIN (green) |
| A-P02 | test_p02_flag_on_without_identity_is_the_base_call | spec F3 | PIN |
| A-P03 | test_p03_base_search_payload_function_untouched | spec F4 (+ a banned-link organic item still returned by the base function) | PIN |
| A-P04 | test_p04_shared_validator_untouched | spec F4 (+ the validator keeps a banned image host with DG OFF and denies it with DG ON) | PIN |

File B `tests/test_inc_i1_noon_and_wiring.py` (noon, the scs wiring, the override):

| Row | Test (nodes) | Source | At base |
|---|---|---|---|
| B-R01 | test_r01_noon_copies_the_first_https_raster | spec 5.3 (+ the request sequence equal ON vs OFF) | RED |
| B-R02 | test_r02_noon_image_shapes [4] | spec 5.3 | RED |
| B-R03 | test_r03_scs_passes_the_identity_under_the_flag | spec 5.3 + the q=-shaped Dior product (I1-R20 / C-2) | RED |
| B-R04 | test_r04_override_requires_https_under_the_flag | I1-R14 (http page image refused under the flag, DG OFF and ON; an https noon image still replaces) | RED |
| B-P01 | test_p01_noon_flag_off_full_config [None, false] | spec F5 with N1 (I1-R20 / C-4) | PIN |
| B-P02 | test_p02_scs_flag_off_exact_call [None, false] | spec F1 | PIN |
| B-P03 | test_p03_scs_camera_product_never_gets_the_identity | spec F1 / I1-1 | PIN |
| B-P04 | test_p04_override_branches_for_a_noon_image | spec 1.4 / Q4 | PIN |
| B-P05 | test_p05_noon_image_rejects [7: svg, ip_host, none, missing, http_only, non_public_host, denied_host] | spec 5.3 + review R-2 (kills M25 / M26) | PIN |
| B-P06 | test_p06_override_flag_off_keeps_the_base_branches [None, false] | I1-R14, the OFF side | PIN |

Counts: RED 29 test functions = 99 nodes (file A 92, file B 7); PIN 10 functions = 19 nodes (file A 4, file B 15); 118 nodes in all.

## 3. Step 4: the RED gate at base (real worktree)

```
[pyt] tag=inc-i1-red-base start=2026-11-14 20:50:00 end=2026-11-14 20:50:06 elapsed=6s bound=600s status=FAIL rc=1      (first bytes: 97 failed, 19 passed; [hermeticity] 116; [netguard] blocked 0)
[pyt] tag=inc-i1-red-base-2 start=2026-11-14 21:10:23 end=2026-11-14 21:10:29 elapsed=6s bound=600s status=FAIL rc=1    (FINAL bytes: 99 failed, 19 passed; [hermeticity] sentinel checked 118 test(s); [netguard] blocked 0 attempt(s) from 0 node(s))
```
- The re-run is ordered by the rule (file A changed after the first run: T18b / T18c added because M11 survived the I1-R4 a registrable-label rule on paper); the frozen bytes are those of run 2.
- Run 2 failure census (log `<SP>/INC-I1/red/mut/red_base_2.log`, ids `<SP>/INC-I1/red/red_base_2_failed.txt`): 99 `E   AssertionError` lines and no other exception type: 61 "INC-I1 not built: app/services/image_relevance.py is missing" (the find_spec helper), 31 "INC-I1 not built: get_product_image_url has no `relevance` keyword" (the inspect.signature helper), 7 file-B value assertions (B-R01, B-R02 x4, B-R03, B-R04). 0 test_p* node failed; the 19 passed nodes are exactly the PIN nodes. No ImportError / TypeError / KeyError / setup error; collection clean.

## 4. Step 5: the prototype (thrown away; detached scratch worktree at the base)

Built from the change list as amended (`<SP>/INC-I1/red/proto/apply_proto.py` + `proto/image_relevance.py`; the diff kept as `proto/proto.diff`: img +99 / -5, noon +5, scs +5, content lines only, CRLF kept): the leaf with the rulings (deny_hosts at module level and the deny on every tier I1-R1; fragrance word for fragrances / other I1-R2; every line token when the brand is empty I1-R3; registrable host label, subset alias rule, number + unit I1-R4; the KG type as fragrance-only text I1-R5; knob 1..10 I1-R7; Tier-3 raster path + not an organic link I1-R10; plurals I1-R12; organic[:10] I1-R20); img (import, four helpers, the keyword, the `_rel` setup, the four tier guards, the `finally` line); scs (import, the kwargs line, the I1-R14 https condition in the override); noon (import, the JSON-LD image block). CLAUDE.md and the black list were not applied (no unit row reads them).

```
[pyt] tag=inc-i1-proto-on start=2026-11-14 20:58:40 end=2026-11-14 20:58:44 elapsed=4s bound=600s status=OK rc=0      (first bytes, ENABLE_IMAGE_RELEVANCE_GUARD=true exported: 116 passed; netguard 0)
[pyt] tag=inc-i1-proto-off start=2026-11-14 21:03:41 end=2026-11-14 21:03:52 elapsed=11s bound=1200s status=OK rc=0    (first bytes, flag=false exported, the unit files + the seven base-img files + test_noon_adapter.py in CI order: 261 passed; netguard: only the known base node above)
[pyt] tag=inc-i1-proto-on-2 start=2026-11-14 21:10:36 end=2026-11-14 21:10:40 elapsed=4s bound=600s status=OK rc=0    (FINAL bytes, flag=true exported: 118 passed; netguard 0)
[pyt] tag=inc-i1-proto-off-2 start=2026-11-14 21:10:47 end=2026-11-14 21:10:50 elapsed=4s bound=600s status=OK rc=0   (FINAL bytes, flag=false exported: 118 passed; netguard 0)
```
Every row sets its own flags, so the ON and OFF runs are equal by design (the ambient env cannot leak into a row). Flag-OFF byte identity at the prototype: the existing image / noon pins (112 + the noon adapter file) stayed green with the prototype in place (proto-off), and the OFF PIN rows A-P01 / A-R16 / B-P01 / B-P02 / B-P06 hold.

What the spec (as amended) leaves open or got wrong, found while building the prototype:
- P-1 spec 2.2 `check(ident, texts, hosts)` has no input for the I1-R1 deny (image URL, link / domain host, source) nor for the I1-R5 KG type. The prototype added keyword parameters (`accept(..., sources=, fragrance_texts=)`, `check(..., fragrance_texts=)`) and put the deny in `accept` / `accept_scheme` / `organic_passes` / `accept_pick`. The rows test the deny and the type through the cascade only, so GREEN may place them anywhere; A-R03 still calls `check(ident, texts, hosts)` with three arguments.
- P-2 spec 2.2 `accept_scheme` (the piggyback) tests the scheme only; I1-R1 says "every tier", so the piggyback image URL is deny-tested too (row A-R17[piggyback]).
- P-3 spec SIZE_TOKEN `(?:ml|oz|g|gm)` lacks `fl`; I1-R4 c names fl (row U-at-fl). The unit token `gm` (spaced) is not in NAME_EXCLUDE: harmless for the rows (they never rely on it).
- P-4 spec M11's killer T18 (`sauvage.dior.com`) no longer kills M11 once host tokens are the registrable label (I1-R4 a gives {dior}); T18b / T18c (`sauvage.example`, the spec's own 2.2 example) were added.
- P-5 I1-R10 names no reason word for a non-raster pick or a pick equal to an organic link; the prototype logs `scheme`; the rows assert only `outcome=rejected candidates=1` and the closed grammar (Q-1).
- P-6 I1-R14 adds one scs line in the override (the change list's "No other scs line" no longer holds: scs = the import, the kwargs line and the https condition).
- P-7 the scs harness must also patch `_smart_fallback_extract` (a fragrance product with missing critical fields reaches the LLM leg; the base node test_organic_results_passed_to_image_service shows that leg attempting api.openai.com); file B patches it and its rows make no network attempt.
- P-8 spec A-R13 (a) and A-R19 lines: organic results read for the Tier-3 precondition are not candidates, so the line is `tier=none outcome=none candidates=0 reason=none` (spec 2.2 item 8, 2.6); the rows assert it.

## 5. Step 6: the mutation table (scratch worktree; byte copies of the prototype; one gate.py run of BOTH unit files per mutant; restore + sha256 verify after each)

Result: 66 KILLED, 0 SURVIVED, 0 ERROR; every killing failure an AssertionError (338 `E   AssertionError` lines over the 66 runs, no other exception type); no equivalent mutant needs a ruling. Driver `<SP>/INC-I1/red/proto/mutdrv.py`, raw `proto/mut_results.jsonl`, digest `proto/mut_digest.json`, logs `red/mut/<id>.log`.

| Id | File | Mutant | Result | Killing rows (A = file A, B = file B; R = RED row, P = PIN row) | Restore sha |
|---|---|---|---|---|---|
| M01 | image_relevance.py | guard_enabled returns True always | KILLED | A-R01, A-R16[0], A-R16[None], A-R16[false], A-R16[garbage], B-P01[None], B-P01[false], B-P02[None], B-P02[false], B-P06[None], B-P06[false], B-R01 | ok |
| M02 | image_service.py | img _rel setup without guard_enabled() | KILLED | A-R16[0], A-R16[None], A-R16[false], A-R16[garbage] | ok |
| M03 | image_relevance.py | relevance_kwargs without its flag check | KILLED | B-P02[None], B-P02[false] | ok |
| M04 | image_relevance.py | relevance_kwargs without the is_vision exclusion | KILLED | B-P03 | ok |
| M05 | image_service.py | img _rel setup without relevance is not None | KILLED | A-P02 | ok |
| M06 | image_relevance.py | check: brand test removed | KILLED | A-R03[T16], A-R03[T7], A-R03[X10], A-R03[X6], A-R03[X7], A-R03[X8], A-R13, A-R20, A-R22, A-R24 | ok |
| M07 | image_relevance.py | check: line test removed (both arms) | KILLED | A-R03[E1], A-R03[T12], A-R03[T13], A-R03[T14], A-R03[T15], A-R03[T18], A-R03[T18b], A-R03[T18c], A-R03[T8], A-R03[T9], A-R03[U-at-fl], A-R03[U-at-g], A-R03[U-at-gm], A-R03[U-at-ml], A-R03[U-at-oz], A-R03[U-sp-fl], A-R03[U-sp-g], A-R03[U-sp-gm], A-R03[U-sp-ml], A-R03[U-sp-oz], A-R03[X11], A-R03[X1], A-R03[X2], A-R03[X3], A-R03[X4], A-R03[X9], A-R12, A-R13, A-R20, A-R22, A-R23 | ok |
| M08 | image_relevance.py | check: fragrance-word test removed | KILLED | A-R03[T17], A-R03[T1], A-R03[T21], A-R03[T2], A-R03[X12], A-R08, A-R20 | ok |
| M09 | image_relevance.py | alias expansion removed | KILLED | A-R03[T3], A-R09 | ok |
| M10 | image_relevance.py | text side: cg.normalize -> str.lower().split() | KILLED | A-R03[T10r] | ok |
| M11 | image_relevance.py | host tokens joined into the line test (both arms) | KILLED | A-R03[T18b], A-R03[T18c] | ok |
| M12 | image_relevance.py | brand_joined dropped | KILLED | A-R03[T19] | ok |
| M13 | image_relevance.py | placeholder-brand fold removed | KILLED | A-R03[T17] | ok |
| M14 | image_service.py | Tier 1 query = bare name under the guard | KILLED | A-R08, A-R09 | ok |
| M15 | image_service.py | Tier 1 num_results=1 under the guard | KILLED | A-R08, A-R09, A-R10 | ok |
| M16 | image_service.py | Tier 1 walk ignores the knob cap | KILLED | A-R10 | ok |
| M17 | image_service.py | Tier 1 takes the first valid image without the test | KILLED | A-R08, A-R09, A-R10, A-R17[serper_domain], A-R17[serper_frag], A-R17[serper_image_url], A-R17[serper_link], A-R17[serper_source], A-R18[None], A-R18[true], A-R24 | ok |
| M18 | image_relevance.py | scheme test removed from accept / accept_pick | KILLED | A-R10, A-R11 | ok |
| M18b | image_relevance.py | scheme test removed from accept_scheme (piggyback) | KILLED | A-R11 | ok |
| M19 | image_service.py | Tier 1.5b calls the base extract under the guard | KILLED | A-R09, A-R11, A-R12, A-R17[images_source], A-R17[kg_image_url], A-R17[organic_link], A-R20, A-R24, A-R25 | ok |
| M20 | image_service.py | Tier-3 precondition removed | KILLED | A-R08, A-R13, A-R19[None], A-R19[true], A-R22 | ok |
| M21 | image_relevance.py | accept_pick without the related-host check | KILLED | A-R13, A-R22, A-R23 | ok |
| M22 | image_service.py | the line logs the product name as product= | KILLED | A-R08, A-R09, A-R10, A-R11, A-R12, A-R13, A-R14, A-R15, A-R17[images_source], A-R17[kg_image_url], A-R17[organic_link], A-R17[piggyback], A-R17[serper_domain], A-R17[serper_frag], A-R17[serper_image_url], A-R17[serper_link], A-R17[serper_source], A-R18[None], A-R18[true], A-R19[None], A-R19[true], A-R20, A-R21, A-R22, A-R23, A-R24, A-R25 | ok |
| M23 | image_service.py | an extra [IMG_RELEVANCE] line in the Tier-1 tier | KILLED | A-R08, A-R10, A-R11, A-R14, A-R17[serper_domain], A-R17[serper_frag], A-R17[serper_image_url], A-R17[serper_link], A-R17[serper_source], A-R18[None], A-R18[true], A-R24 | ok |
| M24 | noon_service.py | noon block without its flag check | KILLED | B-P01[None], B-P01[false], B-R01 | ok |
| M25 | image_relevance.py | first_https_raster returns the first URL unfiltered | KILLED | A-R05, B-P05[denied_host], B-P05[http_only], B-P05[ip_host], B-P05[non_public_host], B-P05[svg], B-R02[http_then_https] | ok |
| M26 | image_relevance.py | first_https_raster bare https prefix instead of allowed_image_url | KILLED | A-R05, B-P05[denied_host], B-P05[ip_host], B-P05[non_public_host], B-P05[svg] | ok |
| M27 | image_relevance.py | knob without the upper clamp | KILLED | A-R02 | ok |
| M28 | image_relevance.py | STOP_WORDS emptied (review X9) | KILLED | A-R03[X9] | ok |
| M29 | image_relevance.py | BRAND_NOISE emptied (review X10) | KILLED | A-R03[X10] | ok |
| M30 | image_relevance.py | SIZE_TOKEN exclusion removed (review X11) | KILLED | A-R03[U-at-fl], A-R03[U-at-g], A-R03[U-at-gm], A-R03[U-at-ml], A-R03[U-at-oz], A-R03[X11t] | ok |
| M31 | structured_comparison_service.py | scs passes brand '' always (review C-2 / R-8 a) | KILLED | B-R03 | ok |
| M32 | image_service.py | _first_image without its https preference (C-2 / R-8 b) | KILLED | A-R25 | ok |
| M33 | image_service.py | snake_case knowledge_graph dropped under the guard (C-2 / R-8 c) | KILLED | A-R25 | ok |
| M34 | image_service.py | images-block hosts (link, domain) ignored (C-2 / R-8 d) | KILLED | A-R24 | ok |
| M35 | image_relevance.py | accept_pick: the first related item's reason branch (C-2 / R-8 e) | KILLED | A-R23 | ok |
| M36 | image_service.py | Tier 1 hosts ignore the domain | KILLED | A-R17[serper_domain], A-R24 | ok |
| M37 | image_service.py | Tier 1 source text ignored | KILLED | A-R24 | ok |
| M38 | image_relevance.py | I1-R1: deny removed from accept | KILLED | A-R17[images_source], A-R17[kg_image_url], A-R17[organic_link], A-R17[serper_domain], A-R17[serper_frag], A-R17[serper_image_url], A-R17[serper_link], A-R17[serper_source], A-R18[None], A-R18[true] | ok |
| M39 | image_relevance.py | I1-R1: image-URL deny removed from accept | KILLED | A-R17[kg_image_url], A-R17[serper_image_url] | ok |
| M40 | image_relevance.py | I1-R1: link / domain host deny removed from accept | KILLED | A-R17[organic_link], A-R17[serper_domain], A-R17[serper_link] | ok |
| M41 | image_relevance.py | I1-R1: source deny removed from accept | KILLED | A-R17[images_source], A-R17[serper_source] | ok |
| M42 | image_relevance.py | I1-R1: a denied organic item may open Tier 3 | KILLED | A-R19[None], A-R19[true] | ok |
| M43 | image_relevance.py | I1-R1: piggyback deny removed | KILLED | A-R17[piggyback] | ok |
| M44 | image_relevance.py | I1-R2: fragrance word for every category (literal I1-3) | KILLED | A-R03[T20] | ok |
| M45 | image_relevance.py | I1-R2: fragrance word not required for other | KILLED | A-R03[T21] | ok |
| M46 | image_relevance.py | I1-R3: brand empty needs one line token, not every | KILLED | A-R03[X1], A-R03[X2], A-R03[X3] | ok |
| M47 | image_relevance.py | I1-R3: an empty line token set passes | KILLED | A-R03[E1] | ok |
| M48 | image_relevance.py | I1-R4 a: every host label (TLD, www) is a token | KILLED | A-R03[X6] | ok |
| M49 | image_relevance.py | I1-R4 b: alias group expands on intersection | KILLED | A-R03[X7], A-R03[X8] | ok |
| M50 | image_relevance.py | I1-R4 c: a spaced number + unit stays a line token | KILLED | A-R03[U-sp-fl], A-R03[U-sp-g], A-R03[U-sp-gm], A-R03[U-sp-ml], A-R03[U-sp-oz], A-R03[X4t] | ok |
| M51 | image_relevance.py | I1-R4 c: an attached number + fl stays a line token | KILLED | A-R03[U-at-fl] | ok |
| M52 | image_service.py | I1-R5: the KG type ignored | KILLED | A-R20 | ok |
| M53 | image_service.py | I1-R5: the KG type joins the brand / line texts | KILLED | A-R20 | ok |
| M54 | image_relevance.py | I1-R7: knob below 1 falls back to 5 | KILLED | A-R02 | ok |
| M55 | image_relevance.py | I1-R10: Tier-3 raster-path test removed | KILLED | A-R21 | ok |
| M56 | image_relevance.py | I1-R10: a pick equal to an organic link accepted | KILLED | A-R21 | ok |
| M57 | image_relevance.py | I1-R12: plurals removed from the fragrance words | KILLED | A-R03[P-0], A-R03[P-1], A-R03[P-2], A-R03[P-3], A-R03[P-4] | ok |
| M58 | structured_comparison_service.py | I1-R14: the override https condition removed | KILLED | B-R04 | ok |
| M59 | structured_comparison_service.py | I1-R14: the override https condition without the flag | KILLED | B-P06[None], B-P06[false] | ok |
| M60 | image_relevance.py | I1-R20: Tier 3 reads organic[:20] | KILLED | A-R22 | ok |
| M61 | image_relevance.py | I1-R18: the local bvlgari group dropped | KILLED | A-R03[T3], A-R07, A-R09 | ok |
| M65 | image_relevance.py | query: perfume for every category | KILLED | A-R04 | ok |
| M66 | image_service.py | Tier-3 call changed under the guard | KILLED | A-R13 | ok |
| M67 | image_relevance.py | relevance_kwargs drops the slot | KILLED | B-R03 | ok |
| M68 | image_relevance.py | first_https_raster takes the last, not the first | KILLED | A-R05, B-R01 | ok |

Every [pyt] line of the driver (the first three are the final-bytes base re-run and the two prototype baselines; log paths elided, logs under `<SP>/INC-I1/red/mut/`):

```
[pyt] tag=inc-i1-red-base-2 start=2026-11-14 21:10:23 end=2026-11-14 21:10:29 elapsed=6s bound=600s status=FAIL rc=1   99 failed, 19 passed, 1 warning in 5.56s
[pyt] tag=inc-i1-proto-on-2 start=2026-11-14 21:10:36 end=2026-11-14 21:10:40 elapsed=4s bound=600s status=OK rc=0   118 passed, 1 warning in 2.99s
[pyt] tag=inc-i1-proto-off-2 start=2026-11-14 21:10:47 end=2026-11-14 21:10:50 elapsed=4s bound=600s status=OK rc=0   118 passed, 1 warning in 3.04s
[pyt] tag=inc-i1-mut-m01 start=2026-11-14 21:10:57 end=2026-11-14 21:11:02 elapsed=5s bound=600s status=FAIL rc=1   12 failed, 106 passed, 1 warning in 3.83s
[pyt] tag=inc-i1-mut-m02 start=2026-11-14 21:11:09 end=2026-11-14 21:11:13 elapsed=5s bound=600s status=FAIL rc=1   4 failed, 114 passed, 1 warning in 3.79s
[pyt] tag=inc-i1-mut-m03 start=2026-11-14 21:11:20 end=2026-11-14 21:11:25 elapsed=5s bound=600s status=FAIL rc=1   2 failed, 116 passed, 1 warning in 3.83s
[pyt] tag=inc-i1-mut-m04 start=2026-11-14 21:11:32 end=2026-11-14 21:11:36 elapsed=5s bound=600s status=FAIL rc=1   1 failed, 117 passed, 1 warning in 3.90s
[pyt] tag=inc-i1-mut-m05 start=2026-11-14 21:11:43 end=2026-11-14 21:11:48 elapsed=4s bound=600s status=FAIL rc=1   1 failed, 117 passed, 1 warning in 3.71s
[pyt] tag=inc-i1-mut-m06 start=2026-11-14 21:11:54 end=2026-11-14 21:11:59 elapsed=4s bound=600s status=FAIL rc=1   10 failed, 108 passed, 1 warning in 3.73s
[pyt] tag=inc-i1-mut-m07 start=2026-11-14 21:12:06 end=2026-11-14 21:12:10 elapsed=5s bound=600s status=FAIL rc=1   31 failed, 87 passed, 1 warning in 4.08s
[pyt] tag=inc-i1-mut-m08 start=2026-11-14 21:12:17 end=2026-11-14 21:12:22 elapsed=4s bound=600s status=FAIL rc=1   7 failed, 111 passed, 1 warning in 3.72s
[pyt] tag=inc-i1-mut-m09 start=2026-11-14 21:12:28 end=2026-11-14 21:12:33 elapsed=4s bound=600s status=FAIL rc=1   2 failed, 116 passed, 1 warning in 3.59s
[pyt] tag=inc-i1-mut-m10 start=2026-11-14 21:12:40 end=2026-11-14 21:12:44 elapsed=5s bound=600s status=FAIL rc=1   1 failed, 117 passed, 1 warning in 3.77s
[pyt] tag=inc-i1-mut-m11 start=2026-11-14 21:12:51 end=2026-11-14 21:12:55 elapsed=5s bound=600s status=FAIL rc=1   2 failed, 116 passed, 1 warning in 3.72s
[pyt] tag=inc-i1-mut-m12 start=2026-11-14 21:13:02 end=2026-11-14 21:13:07 elapsed=5s bound=600s status=FAIL rc=1   1 failed, 117 passed, 1 warning in 3.82s
[pyt] tag=inc-i1-mut-m13 start=2026-11-14 21:13:14 end=2026-11-14 21:13:18 elapsed=5s bound=600s status=FAIL rc=1   1 failed, 117 passed, 1 warning in 3.74s
[pyt] tag=inc-i1-mut-m14 start=2026-11-14 21:13:25 end=2026-11-14 21:13:30 elapsed=4s bound=600s status=FAIL rc=1   2 failed, 116 passed, 1 warning in 3.61s
[pyt] tag=inc-i1-mut-m15 start=2026-11-14 21:13:36 end=2026-11-14 21:13:41 elapsed=4s bound=600s status=FAIL rc=1   3 failed, 115 passed, 1 warning in 3.74s
[pyt] tag=inc-i1-mut-m16 start=2026-11-14 21:14:19 end=2026-11-14 21:14:23 elapsed=4s bound=600s status=FAIL rc=1   1 failed, 117 passed, 1 warning in 3.59s
[pyt] tag=inc-i1-mut-m17 start=2026-11-14 21:14:46 end=2026-11-14 21:14:51 elapsed=5s bound=600s status=FAIL rc=1   11 failed, 107 passed, 1 warning in 3.86s
[pyt] tag=inc-i1-mut-m18 start=2026-11-14 21:15:08 end=2026-11-14 21:15:13 elapsed=4s bound=600s status=FAIL rc=1   2 failed, 116 passed, 1 warning in 3.70s
[pyt] tag=inc-i1-mut-m18b start=2026-11-14 21:15:19 end=2026-11-14 21:15:24 elapsed=4s bound=600s status=FAIL rc=1   1 failed, 117 passed, 1 warning in 3.63s
[pyt] tag=inc-i1-mut-m19 start=2026-11-14 21:15:31 end=2026-11-14 21:15:35 elapsed=4s bound=600s status=FAIL rc=1   9 failed, 109 passed, 1 warning in 3.72s
[pyt] tag=inc-i1-mut-m20 start=2026-11-14 21:15:42 end=2026-11-14 21:15:46 elapsed=5s bound=600s status=FAIL rc=1   5 failed, 113 passed, 1 warning in 3.77s
[pyt] tag=inc-i1-mut-m21 start=2026-11-14 21:15:53 end=2026-11-14 21:15:58 elapsed=4s bound=600s status=FAIL rc=1   3 failed, 115 passed, 1 warning in 3.64s
[pyt] tag=inc-i1-mut-m22 start=2026-11-14 21:16:04 end=2026-11-14 21:16:09 elapsed=5s bound=600s status=FAIL rc=1   27 failed, 91 passed, 1 warning in 4.16s
[pyt] tag=inc-i1-mut-m23 start=2026-11-14 21:16:16 end=2026-11-14 21:16:21 elapsed=5s bound=600s status=FAIL rc=1   12 failed, 106 passed, 1 warning in 3.81s
[pyt] tag=inc-i1-mut-m24 start=2026-11-14 21:16:28 end=2026-11-14 21:16:32 elapsed=4s bound=600s status=FAIL rc=1   3 failed, 115 passed, 1 warning in 3.65s
[pyt] tag=inc-i1-mut-m25 start=2026-11-14 21:16:39 end=2026-11-14 21:16:44 elapsed=4s bound=600s status=FAIL rc=1   7 failed, 111 passed, 1 warning in 3.70s
[pyt] tag=inc-i1-mut-m26 start=2026-11-14 21:16:50 end=2026-11-14 21:16:55 elapsed=4s bound=600s status=FAIL rc=1   5 failed, 113 passed, 1 warning in 3.58s
[pyt] tag=inc-i1-mut-m27 start=2026-11-14 21:17:02 end=2026-11-14 21:17:06 elapsed=4s bound=600s status=FAIL rc=1   1 failed, 117 passed, 1 warning in 3.64s
[pyt] tag=inc-i1-mut-m28 start=2026-11-14 21:17:13 end=2026-11-14 21:17:17 elapsed=4s bound=600s status=FAIL rc=1   1 failed, 117 passed, 1 warning in 3.58s
[pyt] tag=inc-i1-mut-m29 start=2026-11-14 21:17:24 end=2026-11-14 21:17:28 elapsed=4s bound=600s status=FAIL rc=1   1 failed, 117 passed, 1 warning in 3.63s
[pyt] tag=inc-i1-mut-m30 start=2026-11-14 21:17:35 end=2026-11-14 21:17:39 elapsed=4s bound=600s status=FAIL rc=1   6 failed, 112 passed, 1 warning in 3.68s
[pyt] tag=inc-i1-mut-m31 start=2026-11-14 21:17:46 end=2026-11-14 21:17:51 elapsed=4s bound=600s status=FAIL rc=1   1 failed, 117 passed, 1 warning in 3.72s
[pyt] tag=inc-i1-mut-m32 start=2026-11-14 21:17:58 end=2026-11-14 21:18:02 elapsed=4s bound=600s status=FAIL rc=1   1 failed, 117 passed, 1 warning in 3.73s
[pyt] tag=inc-i1-mut-m33 start=2026-11-14 21:18:09 end=2026-11-14 21:18:13 elapsed=5s bound=600s status=FAIL rc=1   1 failed, 117 passed, 1 warning in 3.81s
[pyt] tag=inc-i1-mut-m34 start=2026-11-14 21:18:20 end=2026-11-14 21:18:25 elapsed=5s bound=600s status=FAIL rc=1   1 failed, 117 passed, 1 warning in 3.85s
[pyt] tag=inc-i1-mut-m35 start=2026-11-14 21:18:32 end=2026-11-14 21:18:36 elapsed=5s bound=600s status=FAIL rc=1   1 failed, 117 passed, 1 warning in 3.85s
[pyt] tag=inc-i1-mut-m36 start=2026-11-14 21:18:43 end=2026-11-14 21:18:48 elapsed=5s bound=600s status=FAIL rc=1   2 failed, 116 passed, 1 warning in 3.77s
[pyt] tag=inc-i1-mut-m37 start=2026-11-14 21:18:55 end=2026-11-14 21:18:59 elapsed=4s bound=600s status=FAIL rc=1   1 failed, 117 passed, 1 warning in 3.71s
[pyt] tag=inc-i1-mut-m38 start=2026-11-14 21:19:06 end=2026-11-14 21:19:11 elapsed=5s bound=600s status=FAIL rc=1   10 failed, 108 passed, 1 warning in 3.87s
[pyt] tag=inc-i1-mut-m39 start=2026-11-14 21:19:17 end=2026-11-14 21:19:22 elapsed=5s bound=600s status=FAIL rc=1   2 failed, 116 passed, 1 warning in 3.79s
[pyt] tag=inc-i1-mut-m40 start=2026-11-14 21:19:29 end=2026-11-14 21:19:33 elapsed=4s bound=600s status=FAIL rc=1   3 failed, 115 passed, 1 warning in 3.76s
[pyt] tag=inc-i1-mut-m41 start=2026-11-14 21:19:40 end=2026-11-14 21:19:44 elapsed=4s bound=600s status=FAIL rc=1   2 failed, 116 passed, 1 warning in 3.77s
[pyt] tag=inc-i1-mut-m42 start=2026-11-14 21:19:51 end=2026-11-14 21:19:56 elapsed=4s bound=600s status=FAIL rc=1   2 failed, 116 passed, 1 warning in 3.73s
[pyt] tag=inc-i1-mut-m43 start=2026-11-14 21:20:03 end=2026-11-14 21:20:07 elapsed=5s bound=600s status=FAIL rc=1   1 failed, 117 passed, 1 warning in 3.77s
[pyt] tag=inc-i1-mut-m44 start=2026-11-14 21:20:14 end=2026-11-14 21:20:18 elapsed=4s bound=600s status=FAIL rc=1   1 failed, 117 passed, 1 warning in 3.71s
[pyt] tag=inc-i1-mut-m45 start=2026-11-14 21:20:25 end=2026-11-14 21:20:30 elapsed=4s bound=600s status=FAIL rc=1   1 failed, 117 passed, 1 warning in 3.73s
[pyt] tag=inc-i1-mut-m46 start=2026-11-14 21:20:37 end=2026-11-14 21:20:41 elapsed=4s bound=600s status=FAIL rc=1   3 failed, 115 passed, 1 warning in 3.79s
[pyt] tag=inc-i1-mut-m47 start=2026-11-14 21:20:48 end=2026-11-14 21:20:52 elapsed=4s bound=600s status=FAIL rc=1   1 failed, 117 passed, 1 warning in 3.73s
[pyt] tag=inc-i1-mut-m48 start=2026-11-14 21:20:59 end=2026-11-14 21:21:04 elapsed=4s bound=600s status=FAIL rc=1   1 failed, 117 passed, 1 warning in 3.71s
[pyt] tag=inc-i1-mut-m49 start=2026-11-14 21:21:10 end=2026-11-14 21:21:15 elapsed=4s bound=600s status=FAIL rc=1   2 failed, 116 passed, 1 warning in 3.70s
[pyt] tag=inc-i1-mut-m50 start=2026-11-14 21:21:22 end=2026-11-14 21:21:26 elapsed=4s bound=600s status=FAIL rc=1   6 failed, 112 passed, 1 warning in 3.75s
[pyt] tag=inc-i1-mut-m51 start=2026-11-14 21:21:33 end=2026-11-14 21:21:37 elapsed=4s bound=600s status=FAIL rc=1   1 failed, 117 passed, 1 warning in 3.73s
[pyt] tag=inc-i1-mut-m52 start=2026-11-14 21:21:44 end=2026-11-14 21:21:49 elapsed=4s bound=600s status=FAIL rc=1   1 failed, 117 passed, 1 warning in 3.67s
[pyt] tag=inc-i1-mut-m53 start=2026-11-14 21:21:55 end=2026-11-14 21:22:00 elapsed=4s bound=600s status=FAIL rc=1   1 failed, 117 passed, 1 warning in 3.69s
[pyt] tag=inc-i1-mut-m54 start=2026-11-14 21:22:07 end=2026-11-14 21:22:11 elapsed=4s bound=600s status=FAIL rc=1   1 failed, 117 passed, 1 warning in 3.75s
[pyt] tag=inc-i1-mut-m55 start=2026-11-14 21:22:18 end=2026-11-14 21:22:22 elapsed=4s bound=600s status=FAIL rc=1   1 failed, 117 passed, 1 warning in 3.69s
[pyt] tag=inc-i1-mut-m56 start=2026-11-14 21:22:29 end=2026-11-14 21:22:34 elapsed=4s bound=600s status=FAIL rc=1   1 failed, 117 passed, 1 warning in 3.74s
[pyt] tag=inc-i1-mut-m57 start=2026-11-14 21:22:40 end=2026-11-14 21:22:45 elapsed=5s bound=600s status=FAIL rc=1   5 failed, 113 passed, 1 warning in 3.83s
[pyt] tag=inc-i1-mut-m58 start=2026-11-14 21:22:52 end=2026-11-14 21:22:56 elapsed=4s bound=600s status=FAIL rc=1   1 failed, 117 passed, 1 warning in 3.69s
[pyt] tag=inc-i1-mut-m59 start=2026-11-14 21:23:03 end=2026-11-14 21:23:08 elapsed=4s bound=600s status=FAIL rc=1   2 failed, 116 passed, 1 warning in 3.70s
[pyt] tag=inc-i1-mut-m60 start=2026-11-14 21:23:15 end=2026-11-14 21:23:19 elapsed=4s bound=600s status=FAIL rc=1   1 failed, 117 passed, 1 warning in 3.75s
[pyt] tag=inc-i1-mut-m61 start=2026-11-14 21:23:26 end=2026-11-14 21:23:30 elapsed=4s bound=600s status=FAIL rc=1   3 failed, 115 passed, 1 warning in 3.76s
[pyt] tag=inc-i1-mut-m65 start=2026-11-14 21:23:37 end=2026-11-14 21:23:42 elapsed=4s bound=600s status=FAIL rc=1   1 failed, 117 passed, 1 warning in 3.69s
[pyt] tag=inc-i1-mut-m66 start=2026-11-14 21:23:48 end=2026-11-14 21:23:53 elapsed=4s bound=600s status=FAIL rc=1   1 failed, 117 passed, 1 warning in 3.72s
[pyt] tag=inc-i1-mut-m67 start=2026-11-14 21:24:00 end=2026-11-14 21:24:04 elapsed=4s bound=600s status=FAIL rc=1   1 failed, 117 passed, 1 warning in 3.79s
[pyt] tag=inc-i1-mut-m68 start=2026-11-14 21:24:11 end=2026-11-14 21:24:15 elapsed=5s bound=600s status=FAIL rc=1   2 failed, 116 passed, 1 warning in 3.80s
```

## 6. Step 7: the comm set at base (REAL worktree)

- List: `<SP>/INC-I1/red/comm/comm_set.txt` (710 files) recomputed with the spec's `<SP>/INC-I1/spec/comm.py` (git reads only): sha256 `5e2f0266d1a562fcdc79629d26cbfbc7b5a52e6fabd501bdecbf7a24296410ba`, byte-equal to the spec's list. Union: the app import closure of img / noon / scs (84 modules incl. app/main.py) -> 695 test files naming a closure member or using app.main / TestClient; + 7 app-source readers; + 6 named source-scanning pins / CLAUDE.md readers (text + import graph, 44 readers in all); + 4 SmartCompareApp-scanning tests; MINUS the test_precommit_hook*.py files (2 were in the union; all four excluded). NETWORK_FLAKY_EXCLUDE: no such list exists in the lane record or the repo code (docs mention it only; the MON1 precedent): none excluded. The rulings add no edited module (deny_hosts is imported by the leaf, not edited), so the list stands; at head add the two RED files (712).
- Per-file reasons: `<SP>/INC-I1/red/comm/comm_reasons.tsv` (file, reason: edited-module / closure / app.main-TestClient / app-source-reader / named-source-pin / claude-md-reader / smartcompare-scan). Chunk map: `<SP>/INC-I1/red/comm/chunks.txt` (29 chunks of <= 25).
- Run: 29 chunks, bound 1200 each, tags inc-i1-comm-base-01..29, one at a time through gate.py (driver `red/seqrun.py`, output `red/comm/comm_out.txt`, logs `red/comm/comm_base_NN.log`). The two RED files were present (untracked) in the real worktree during the run (not members); the readers that walk tests/ (tests/test_ci_gates.py, tests/test_hermeticity_pins.py) therefore saw them (spec 5.1).

| Chunk | Files | Status | Summary | netguard | FAILED / ERROR ids |
|---|---|---|---|---|---|
| inc-i1-comm-base-01 | 25 | OK | 783 passed, 15 warnings in 31.12s | blocked 22 attempt(s) from 5 node(s) | - |
| inc-i1-comm-base-02 | 25 | FAIL | 2 failed, 548 passed, 39 warnings in 24.47s | blocked 19 attempt(s) from 8 node(s) | tests/test_auth_interceptor.py::test_sign_in_with_social_exception<br>tests/test_auth_interceptor.py::test_social_login_user_insert_fails_gracefully |
| inc-i1-comm-base-03 | 25 | OK | 461 passed, 1 deselected, 15 warnings in 24.21s | blocked 17 attempt(s) from 4 node(s) | - |
| inc-i1-comm-base-04 | 25 | OK | 1788 passed, 1 skipped, 7 deselected, 17 warnings in 62.25s (0:01:02) | blocked 13 attempt(s) from 8 node(s) | - |
| inc-i1-comm-base-05 | 25 | OK | 656 passed, 1 xfailed, 15 warnings in 13.83s | blocked 1 attempt(s) from 1 node(s) | - |
| inc-i1-comm-base-06 | 25 | OK | 422 passed, 9 deselected, 17 warnings in 12.12s | blocked 1 attempt(s) from 0 node(s) | - |
| inc-i1-comm-base-07 | 25 | OK | 394 passed, 2 skipped, 1 warning in 18.77s | blocked 27 attempt(s) from 9 node(s) | - |
| inc-i1-comm-base-08 | 25 | OK | 2013 passed, 15 warnings in 37.89s | blocked 34 attempt(s) from 12 node(s) | - |
| inc-i1-comm-base-09 | 25 | OK | 1400 passed, 1 skipped, 5 deselected, 22 warnings in 58.53s | blocked 29 attempt(s) from 28 node(s) | - |
| inc-i1-comm-base-10 | 25 | OK | 627 passed, 1 xfailed, 17 warnings in 50.99s | blocked 13 attempt(s) from 2 node(s) | - |
| inc-i1-comm-base-11 | 25 | OK | 463 passed, 16 warnings in 24.91s | blocked 2 attempt(s) from 2 node(s) | - |
| inc-i1-comm-base-12 | 25 | OK | 176 passed, 17 warnings in 11.41s | blocked 1 attempt(s) from 1 node(s) | - |
| inc-i1-comm-base-13 | 25 | OK | 574 passed, 1 skipped, 10 deselected, 1 warning in 18.67s | blocked 0 attempt(s) from 0 node(s) | - |
| inc-i1-comm-base-14 | 25 | FAIL | 2 failed, 3721 passed, 22 skipped, 18 warnings in 25.61s | blocked 130 attempt(s) from 9 node(s) | tests/test_page_scraping.py::TestFetchPagePriceJsonLD::test_jsonld_nested_offers_picks_lowest<br>tests/test_page_scraping.py::TestFetchPagePriceOpenGraph::test_og_meta_extraction |
| inc-i1-comm-base-15 | 25 | FAIL | 2 failed, 744 passed, 3 skipped, 5 deselected, 23 warnings in 35.89s | blocked 42 attempt(s) from 13 node(s) | tests/test_personalization_bundle_c.py::test_applied_shifts_list_is_default_empty_when_no_priorities<br>tests/test_personalization_bundle_c.py::test_full_response_payload_audit_no_magnitude_keys |
| inc-i1-comm-base-16 | 25 | FAIL | 404 passed, 3 skipped, 9 deselected, 1 xfailed, 17 warnings, 2 errors in 26.09s | blocked 98 attempt(s) from 10 node(s) | tests/test_prompt_truth.py::test_render_digests_match_base_except_the_fence<br>tests/test_prompt_truth.py::test_truth_on_prefix_static_and_cacheable |
| inc-i1-comm-base-17 | 25 | OK | 320 passed, 1 skipped, 1 deselected, 17 warnings in 12.06s | blocked 12 attempt(s) from 6 node(s) | - |
| inc-i1-comm-base-18 | 25 | OK | 862 passed, 373 warnings in 164.76s (0:02:44) | blocked 20 attempt(s) from 1 node(s) | - |
| inc-i1-comm-base-19 | 25 | OK | 1439 passed, 17 warnings in 81.79s (0:01:21) | blocked 4 attempt(s) from 2 node(s) | - |
| inc-i1-comm-base-20 | 25 | FAIL | 7 failed, 2214 passed, 16 warnings in 53.45s | blocked 0 attempt(s) from 0 node(s) | tests/test_s81_d16_operator_ingest.py::test_r10_runbook_names_only<br>tests/test_s81_d17_coverage.py::test_r9_railway_config_and_hygiene<br>tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[OFF]<br>tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[empty]<br>tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[false]<br>tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[pad0]<br>tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[unset] |
| inc-i1-comm-base-21 | 25 | FAIL | 7 failed, 2541 passed, 137 warnings in 126.98s (0:02:06) | blocked 24 attempt(s) from 2 node(s) | tests/test_s81_s07_meas_harness.py::test_r35_fixtures<br>tests/test_s81_s10_fragrance_gate.py::test_r06_production_lexicon_content<br>tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[cron_feed_walker]<br>tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[cron_pdp_discovery]<br>tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[kb_seed_common]<br>tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[seed_kb_batch]<br>tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[seed_kb_brands_wikidata] |
| inc-i1-comm-base-22 | 25 | FAIL | 6 failed, 1687 passed, 49 warnings in 49.88s | blocked 24 attempt(s) from 9 node(s) | tests/test_s81_s18b_store_label.py::test_r2_table_shape<br>tests/test_s81_s19_gap_queue.py::test_r15_hygiene<br>tests/test_s81_s22_compare_runs.py::test_b02_one_transaction_ascii_lf<br>tests/test_s81_s22_judge.py::test_j01_script_exists_and_off_first<br>tests/test_s81_s24_auth_throttle.py::test_p83_red_file_setenv_hygiene<br>tests/test_s81_s24_auth_throttle.py::test_r92_hygiene |
| inc-i1-comm-base-23 | 25 | OK | 1118 passed, 1 xfailed, 17 warnings in 36.33s | blocked 13 attempt(s) from 7 node(s) | - |
| inc-i1-comm-base-24 | 25 | OK | 657 passed, 1 skipped, 2 deselected, 16 warnings in 44.91s | blocked 14 attempt(s) from 4 node(s) | - |
| inc-i1-comm-base-25 | 25 | OK | 456 passed, 7 skipped, 8 deselected, 24 warnings in 40.85s | blocked 79 attempt(s) from 21 node(s) | - |
| inc-i1-comm-base-26 | 25 | OK | 561 passed, 4 deselected, 17 warnings in 34.47s | blocked 102 attempt(s) from 45 node(s) | - |
| inc-i1-comm-base-27 | 25 | OK | 382 passed, 4 deselected, 35 xfailed, 14 warnings in 25.89s | blocked 0 attempt(s) from 0 node(s) | - |
| inc-i1-comm-base-28 | 25 | OK | 1249 passed, 10 skipped, 17 warnings in 32.75s | blocked 20 attempt(s) from 12 node(s) | - |
| inc-i1-comm-base-29 | 10 | OK | 169 passed, 1 warning in 5.46s | blocked 0 attempt(s) from 0 node(s) | - |

- Failed / error ids at base: 28 (`<SP>/INC-I1/red/comm/base_failed.txt`):

```
tests/test_auth_interceptor.py::test_sign_in_with_social_exception
tests/test_auth_interceptor.py::test_social_login_user_insert_fails_gracefully
tests/test_page_scraping.py::TestFetchPagePriceJsonLD::test_jsonld_nested_offers_picks_lowest
tests/test_page_scraping.py::TestFetchPagePriceOpenGraph::test_og_meta_extraction
tests/test_personalization_bundle_c.py::test_applied_shifts_list_is_default_empty_when_no_priorities
tests/test_personalization_bundle_c.py::test_full_response_payload_audit_no_magnitude_keys
tests/test_prompt_truth.py::test_render_digests_match_base_except_the_fence
tests/test_prompt_truth.py::test_truth_on_prefix_static_and_cacheable
tests/test_s81_d16_operator_ingest.py::test_r10_runbook_names_only
tests/test_s81_d17_coverage.py::test_r9_railway_config_and_hygiene
tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[OFF]
tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[empty]
tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[false]
tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[pad0]
tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[unset]
tests/test_s81_s07_meas_harness.py::test_r35_fixtures
tests/test_s81_s10_fragrance_gate.py::test_r06_production_lexicon_content
tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[cron_feed_walker]
tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[cron_pdp_discovery]
tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[kb_seed_common]
tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[seed_kb_batch]
tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[seed_kb_brands_wikidata]
tests/test_s81_s18b_store_label.py::test_r2_table_shape
tests/test_s81_s19_gap_queue.py::test_r15_hygiene
tests/test_s81_s22_compare_runs.py::test_b02_one_transaction_ascii_lf
tests/test_s81_s22_judge.py::test_j01_script_exists_and_off_first
tests/test_s81_s24_auth_throttle.py::test_p83_red_file_setenv_hygiene
tests/test_s81_s24_auth_throttle.py::test_r92_hygiene
```

- Against the stored MON1 head record (cccfb855, 773 members, 27 ids, the same box): ids failing here and NOT in that record: ['tests/test_s81_s07_meas_harness.py::test_r35_fixtures']; ids of that record whose file is a member here but which did not fail here: none.
- Every chunk status: OK or FAIL (no TIMEOUT). BUSY rc=126 refusals that gate.py retried by itself (the chunk then ran in full): ["[pyt] tag=inc-i1-comm-base-17 status=BUSY rc=126 waited=0s (this lane's pytest mutex is held by pid 27940; NOT started)", "[pyt] tag=inc-i1-comm-base-27 status=BUSY rc=126 waited=0s (this lane's pytest mutex is held by pid 42760; NOT started)"].
- The readers that walk tests/ ran with the two RED files present: tests/test_ci_gates.py in inc-i1-comm-base-04, tests/test_hermeticity_pins.py in inc-i1-comm-base-09; neither id is in the failed set: True.
- Base record stored (LC-6): `<SP>/harness/base_records/731bcddf531a7e123963246168ca19f262859337/5e2f0266d1a562fcdc79629d26cbfbc7b5a52e6fabd501bdecbf7a24296410ba.txt` (+ `.files`, `.header.txt`, `.pyt.log`).

Every chunk [pyt] line (log paths elided; logs `<SP>/INC-I1/red/comm/comm_base_NN.log`):

```
[pyt] tag=inc-i1-comm-base-01 start=2026-11-14 21:25:12 end=2026-11-14 21:25:44 elapsed=32s bound=1200s status=OK rc=0
[pyt] tag=inc-i1-comm-base-02 start=2026-11-14 21:25:51 end=2026-11-14 21:26:17 elapsed=26s bound=1200s status=FAIL rc=1
[pyt] tag=inc-i1-comm-base-03 start=2026-11-14 21:26:24 end=2026-11-14 21:26:49 elapsed=25s bound=1200s status=OK rc=0
[pyt] tag=inc-i1-comm-base-04 start=2026-11-14 21:26:56 end=2026-11-14 21:27:59 elapsed=63s bound=1200s status=OK rc=0
[pyt] tag=inc-i1-comm-base-05 start=2026-11-14 21:28:06 end=2026-11-14 21:28:21 elapsed=15s bound=1200s status=OK rc=0
[pyt] tag=inc-i1-comm-base-06 start=2026-11-14 21:28:28 end=2026-11-14 21:28:41 elapsed=13s bound=1200s status=OK rc=0
[pyt] tag=inc-i1-comm-base-07 start=2026-11-14 21:28:47 end=2026-11-14 21:29:07 elapsed=20s bound=1200s status=OK rc=0
[pyt] tag=inc-i1-comm-base-08 start=2026-11-14 21:29:14 end=2026-11-14 21:29:53 elapsed=39s bound=1200s status=OK rc=0
[pyt] tag=inc-i1-comm-base-09 start=2026-11-14 21:30:00 end=2026-11-14 21:31:00 elapsed=60s bound=1200s status=OK rc=0
[pyt] tag=inc-i1-comm-base-10 start=2026-11-14 21:31:59 end=2026-11-14 21:32:51 elapsed=52s bound=1200s status=OK rc=0
[pyt] tag=inc-i1-comm-base-11 start=2026-11-14 21:32:58 end=2026-11-14 21:33:24 elapsed=26s bound=1200s status=OK rc=0
[pyt] tag=inc-i1-comm-base-12 start=2026-11-14 21:33:31 end=2026-11-14 21:33:43 elapsed=12s bound=1200s status=OK rc=0
[pyt] tag=inc-i1-comm-base-13 start=2026-11-14 21:33:50 end=2026-11-14 21:34:09 elapsed=19s bound=1200s status=OK rc=0
[pyt] tag=inc-i1-comm-base-14 start=2026-11-14 21:34:16 end=2026-11-14 21:34:43 elapsed=27s bound=1200s status=FAIL rc=1
[pyt] tag=inc-i1-comm-base-15 start=2026-11-14 21:34:50 end=2026-11-14 21:35:27 elapsed=37s bound=1200s status=FAIL rc=1
[pyt] tag=inc-i1-comm-base-16 start=2026-11-14 21:38:48 end=2026-11-14 21:39:15 elapsed=27s bound=1200s status=FAIL rc=1
[pyt] tag=inc-i1-comm-base-17 start=2026-11-14 21:44:07 end=2026-11-14 21:44:20 elapsed=13s bound=1200s status=OK rc=0
[pyt] tag=inc-i1-comm-base-18 start=2026-11-14 21:44:26 end=2026-11-14 21:47:13 elapsed=167s bound=1200s status=OK rc=0
[pyt] tag=inc-i1-comm-base-19 start=2026-11-14 21:47:20 end=2026-11-14 21:48:43 elapsed=83s bound=1200s status=OK rc=0
[pyt] tag=inc-i1-comm-base-20 start=2026-11-14 21:48:50 end=2026-11-14 21:49:45 elapsed=55s bound=1200s status=FAIL rc=1
[pyt] tag=inc-i1-comm-base-21 start=2026-11-14 21:49:52 end=2026-11-14 21:52:01 elapsed=129s bound=1200s status=FAIL rc=1
[pyt] tag=inc-i1-comm-base-22 start=2026-11-14 21:52:08 end=2026-11-14 21:52:59 elapsed=51s bound=1200s status=FAIL rc=1
[pyt] tag=inc-i1-comm-base-23 start=2026-11-14 21:53:06 end=2026-11-14 21:53:44 elapsed=38s bound=1200s status=OK rc=0
[pyt] tag=inc-i1-comm-base-24 start=2026-11-14 21:53:51 end=2026-11-14 21:54:36 elapsed=46s bound=1200s status=OK rc=0
[pyt] tag=inc-i1-comm-base-25 start=2026-11-14 21:54:43 end=2026-11-14 21:55:25 elapsed=42s bound=1200s status=OK rc=0
[pyt] tag=inc-i1-comm-base-26 start=2026-11-14 21:55:32 end=2026-11-14 21:56:08 elapsed=36s bound=1200s status=OK rc=0
[pyt] tag=inc-i1-comm-base-27 start=2026-11-14 21:56:31 end=2026-11-14 21:56:57 elapsed=27s bound=1200s status=OK rc=0
[pyt] tag=inc-i1-comm-base-28 start=2026-11-14 21:57:04 end=2026-11-14 21:57:38 elapsed=34s bound=1200s status=OK rc=0
[pyt] tag=inc-i1-comm-base-29 start=2026-11-14 21:57:45 end=2026-11-14 21:57:51 elapsed=6s bound=1200s status=OK rc=0
```


## 7. Step 8: restore check

- HEAD `731bcddf531a7e123963246168ca19f262859337` (== base: True); tracked paths in the base tree: 3595; regular files hashed through the clean filter (`git hash-object --stdin-paths`): 3595; index vs base-tree mismatches: none; working-file blob vs base blob mismatches: none; untracked: ['tests/test_inc_i1_noon_and_wiring.py', 'tests/test_inc_i1_picture_must_match.py'] (only the two RED files: True); other status lines: none. Script `<SP>/INC-I1/red/restore_check.py`, output `restore_check.json`.
- Scratch worktree `<SP>/INC-I1/INC-I1_scratch`: removed with `git worktree remove --force` after the mutation run (the mutation lock was created and removed by the driver; every mutated file was restored from its byte copy and sha-verified, ALL_RESTORED); `git worktree list` no longer lists it; no node_modules junction existed there.
- Orphan check: none: no live python.exe process carries an inc-i1 tag, the scratch path, the sc-inc-i1 cwd, seqrun or mutdrv (Get-CimInstance probe filtered on python.exe at 2026-11-14 21:59:12; every driver of this round exited rc 0)


## 8. Deviations from the spec (as amended)

- D-1 Rows beyond spec section 5, each derived from a ruling or a review correction the rulings accept (I1-R20): A-R17..A-R25, B-R04, B-P06; truth-table rows T18b, T18c, T21, X1..X12 (as listed), E1, P-0..P-4, U-sp-*, U-at-*; T20 -> None (I1-R2). RED nodes 99 / PIN nodes 19 instead of the spec's 19 / 9 rows.
- D-2 A-R02 follows I1-R7 (below 1 -> 1); the spec's L-I1-17 is superseded. A-R03 plurals follow I1-R12; the spec's L-I1-7 is superseded.
- D-3 Sentinel hosts: every candidate image is on a public `*.example.com` / `*.example.org` / `*.example.net` host (the spec's example POEM used `poem.example.test`), so no implementation-side host rule can change a reason word; the non-public case is tested only where the spec names it (first_https_raster, the noon rejects).
- D-4 The review's X5 title text was replaced by a synthetic one ("Tygar Bvlgari cologne for men") so no file carries text resembling a banned site's page copy (H12 g); the denial is carried by the source / link / domain / image host as I1-R1 lists.
- D-5 The noon fixtures use a synthetic SKU `NZT1A` and seller `Synth-Seller` (no 8-digit run) with the measured `f.nooncdn.com` host and `/p/pzsku/...jpg?width=1200` shape (spec 5.1).
- D-6 Mutation ids: the spec's M01-M27 + M18b (piggyback scheme); the review items as M28-M37 (X9 / X10 / X11, the C-2 / R-8 a-e items and two Tier-1 channel mutants: the ruling's "M28-M33" range is too short for the review's eight items); the ruling mutants M38-M61 and M65-M68. 66 in all.
- D-7 The scratch worktree path is `<SP>/INC-I1/INC-I1_scratch` (spec 7: "under <SP>/INC-I1/"), not `<SP>/INC-I1_scratch`.
- D-8 A-R15 uses the spec's 0.05 s bound; A-R16 patches the knob with a recorder that raises (and asserts no read) instead of a bare raise.
- D-9 The prototype CLAUDE.md / black-list edits were not built (no unit row reads them); the black-allowlist reader (tests/test_ci_gates.py) cannot be satisfied at RED (the list is GREEN's file): the two RED files are black --check clean (26.5.1) so the I1-R17 listing will pass.

## 9. Questions for the gate (recommended answer first)

- Q-1 I1-R10: which reason word for a Tier-3 pick refused for its path (no raster extension) or for equalling an organic link? Recommended `scheme` (a URL-shape reason, no grammar change); the rows accept any closed word.
- Q-2 Row E1: with an empty brand, a line with no significant token (e.g. "Eau de Parfum") is rejected (reason name), reading I1-3's "at least one" as still binding under I1-R3's "every". Confirm (recommended yes: otherwise any perfume picture passes).
- Q-3 I1-R2 for an empty or non-string `category` in `relevance` (production canonicalizes None to "other", so scs never sends ""): not pinned. Recommended: treat it as other (fragrance word required).
- Q-4 I1-R14 for a camera product's page image: not pinned (the rows drive text products). I1-1 / L-I1-14 keep the camera path unchanged; recommended: GREEN keeps the https condition for text products only, or the gate rules it applies to all products.
- Q-5 The deny reason when a candidate is BOTH denied and fails the relevance test: not pinned (the rows use items that pass the relevance test, as I1-R1 words them).
- Q-6 Class: still SAFE (I1-R9); the deny now sits inside the guard for both DG states, which the RED rows pin (A-R17..A-R19).

## 10. NOT MEASURED in this round (stated)

- The provider facts the spec lists (Serper Images `source` / `link` / `domain` shapes beyond the documented names, billing for num 5, KG `type` values for perfumes, the golden pairs' KG titles): no network (spec, review). The rows use the field names as the spec defines them.
- GREEN-round gates: the CI-order set, the head runs of the 1.10 sets, the fourteen client fences, the head comm set (712 files), the added-line sweep of the diff.
- No production claim: every result here is hermetic; nothing is fixed until the owner's phone proof (H6, I1-R8).

## 11. Appendix: the comm-set driver output (seqrun.py: [gate] / [pyt] / [netguard] / [hermeticity] lines, the pytest summary and the FAILED / ERROR ids per chunk)

```
=== job inc-i1-comm-base-01 rc=0 wall=39s
[pyt] --- summary lines ---
[netguard] blocked 22 attempt(s) from 5 node(s)
[netguard]   tests/test_adapter_prefetch_hook.py::TestNonSupplementAdapterHook::test_adapter_miss_falls_through_to_discovery [egress] socket.getaddrinfo api.openai.com:443
[netguard]   tests/test_adapter_prefetch_hook.py::TestAdapterCancellationNoOrphan::test_lazy_factory_contract_holds_on_adapter_miss_cancel_path [egress] socket.getaddrinfo api.openai.com:443
[netguard]   tests/test_algolia_catalog_stores.py::test_oman_sharafdg_price_zero_returns_none [egress] curl_cffi.Session.request https://oman.sharafdg.com/
[netguard]   tests/test_algolia_tier2_wiring.py::TestAlgoliaTier2CallSite::test_genuine_algolia_hit_short_circuits [egress] curl_cffi.Session.request https://www.footlocker.com.bh/configs.json
[netguard]   tests/test_algolia_tier2_wiring.py::TestAlgoliaTier2CallSite::test_algolia_miss_falls_through [egress] curl_cffi.Session.request https://www.footlocker.com.bh/configs.json
[pyt] tag=inc-i1-comm-base-01 start=2026-11-14 21:25:12 end=2026-11-14 21:25:44 elapsed=32s bound=1200s status=OK rc=0 log=<SP>\INC-I1\red\comm\comm_base_01.log
SUMMARY ====================== 783 passed, 15 warnings in 31.12s ======================
=== job inc-i1-comm-base-02 rc=1 wall=32s
[pyt] --- summary lines ---
[netguard]   tests/test_auth_interceptor.py::test_refresh_session_includes_user_data [sentinel] socket.create_connection neutralized.supabase.invalid:443
[netguard]   tests/test_auth_routes_invite_fingerprint.py::test_register_invite_code_valid_format_accepted [sentinel] socket.create_connection neutralized.supabase.invalid:443
[netguard]   tests/test_auth_routes_invite_fingerprint.py::test_register_resolves_code_then_links_invite [sentinel] socket.create_connection neutralized.supabase.invalid:443
[netguard]   tests/test_bh_gcc_cascade_wiring.py::TestNewAdapterCascadeWiring::test_woo_genuine_hit_short_circuits [sentinel] socket.create_connection neutralized.supabase.invalid:443
[netguard]   tests/test_bh_gcc_cascade_wiring.py::TestNewAdapterCascadeWiring::test_converted_adapter_hit_does_NOT_short_circuit [egress] socket.getaddrinfo api.openai.com:443
[netguard]   tests/test_bh_gcc_cascade_wiring.py::TestNewAdapterCascadeWiring::test_new_adapter_miss_falls_through [egress] socket.getaddrinfo api.openai.com:443
[pyt] --- FAILED/ERROR ids (4) ---
[pyt] tag=inc-i1-comm-base-02 start=2026-11-14 21:25:51 end=2026-11-14 21:26:17 elapsed=26s bound=1200s status=FAIL rc=1 log=<SP>\INC-I1\red\comm\comm_base_02.log
SUMMARY ================= 2 failed, 548 passed, 39 warnings in 24.47s =================
FAILED tests/test_auth_interceptor.py::test_sign_in_with_social_exception
FAILED tests/test_auth_interceptor.py::test_social_login_user_insert_fails_gracefully
=== job inc-i1-comm-base-03 rc=0 wall=32s
[pyt] --- summary lines ---
[hermeticity] sentinel checked 461 test(s)
[netguard] blocked 17 attempt(s) from 4 node(s)
[netguard]   tests/test_cascade_parallel.py::test_discovery_prefetch_starts_concurrently_with_shopping [egress] curl_cffi.Session.request https://search.unbxd.io/72883ca2a4420a7c7ca07cefda404539/ss-unbxd-auk-extra-bahrain-en-prod11541714990628/search?q=Apple+iPhone+15&rows=20
[netguard]   tests/test_cascade_parallel.py::test_prefetch_SKIPPED_when_algolia_sources_exist [egress] curl_cffi.Session.request https://www.footlocker.com.bh/configs.json
[netguard]   tests/test_cascade_parallel.py::test_prefetch_FIRES_for_shopify_category_with_lulu_discovery[grocery] [egress] socket.getaddrinfo api.openai.com:443
[netguard]   tests/test_cascade_parallel.py::test_prefetch_FIRES_for_shopify_category_with_lulu_discovery[electronics] [egress] curl_cffi.Session.request https://shopalmoayyed.com/products.json?limit=250
[pyt] tag=inc-i1-comm-base-03 start=2026-11-14 21:26:24 end=2026-11-14 21:26:49 elapsed=25s bound=1200s status=OK rc=0 log=<SP>\INC-I1\red\comm\comm_base_03.log
SUMMARY =============== 461 passed, 1 deselected, 15 warnings in 24.21s ===============
=== job inc-i1-comm-base-04 rc=0 wall=70s
[pyt] --- summary lines ---
[netguard]   tests/test_category_selection.py::TestAPIParameter::test_api_passes_selected_category_to_service [sentinel] socket.create_connection neutralized.supabase.invalid:443
[netguard]   tests/test_category_selection.py::TestAPIParameter::test_api_accepts_invalid_category_without_422 [sentinel] socket.create_connection neutralized.supabase.invalid:443
[netguard]   tests/test_category_selection.py::TestCategorySwitchingResponse::test_category_switching_response_fields [sentinel] socket.create_connection neutralized.supabase.invalid:443
[netguard]   tests/test_category_selection.py::TestCategorySwitchingResponse::test_no_switch_response_fields [sentinel] socket.create_connection neutralized.supabase.invalid:443
[netguard]   tests/test_category_selection.py::TestCategorySwitchingResponse::test_each_new_category_in_response [sentinel] socket.create_connection neutralized.supabase.invalid:443
[netguard]   tests/test_comparison_response_image_url.py::TestOrchestratorWiring::test_organic_results_passed_to_image_service [egress] socket.getaddrinfo api.openai.com:443
[pyt] tag=inc-i1-comm-base-04 start=2026-11-14 21:26:56 end=2026-11-14 21:27:59 elapsed=63s bound=1200s status=OK rc=0 log=<SP>\INC-I1\red\comm\comm_base_04.log
SUMMARY ==== 1788 passed, 1 skipped, 7 deselected, 17 warnings in 62.25s (0:01:02) ====
=== job inc-i1-comm-base-05 rc=0 wall=21s
[pyt] --- summary lines ---
[hermeticity] sentinel checked 657 test(s)
[netguard] blocked 1 attempt(s) from 1 node(s)
[netguard]   tests/test_converted_price_before_estimate_t1.py::test_tier2_organic_NO_retailer_is_not_phantom_local_bhd [egress] curl_cffi.Session.request https://www.footlocker.com.bh/configs.json
[pyt] tag=inc-i1-comm-base-05 start=2026-11-14 21:28:06 end=2026-11-14 21:28:21 elapsed=15s bound=1200s status=OK rc=0 log=<SP>\INC-I1\red\comm\comm_base_05.log
SUMMARY ================ 656 passed, 1 xfailed, 15 warnings in 13.83s =================
=== job inc-i1-comm-base-06 rc=0 wall=19s
[pyt] --- summary lines ---
[hermeticity] sentinel checked 422 test(s)
[netguard] blocked 1 attempt(s) from 0 node(s)
[netguard]   <collection>: 1 attempt(s) outside any test, e.g. socket.create_connection neutralized.supabase.invalid:443
[pyt] tag=inc-i1-comm-base-06 start=2026-11-14 21:28:28 end=2026-11-14 21:28:41 elapsed=13s bound=1200s status=OK rc=0 log=<SP>\INC-I1\red\comm\comm_base_06.log
SUMMARY =============== 422 passed, 9 deselected, 17 warnings in 12.12s ===============
=== job inc-i1-comm-base-07 rc=0 wall=26s
[pyt] --- summary lines ---
[netguard]   tests/test_explicit_pair_integration_mocked.py::test_explicit_pair_category_switched_surfaces_on_response_e2e [egress] socket.getaddrinfo api.openai.com:443
[netguard]   tests/test_fan_out_integration.py::TestFanOutHighestRankWinner::test_fan_out_returns_highest_rank_winner [egress] curl_cffi.Session.request https://02X7U6O3SI-dsn.algolia.net/1/indexes/enterprise_magento_en_bh_products/query
[netguard]   tests/test_fan_out_integration.py::TestPendingScrapersCancelledOnConfirmation::test_pending_scrapers_cancelled_on_confirmation [egress] curl_cffi.Session.request https://02X7U6O3SI-dsn.algolia.net/1/indexes/enterprise_magento_en_bh_products/query
[netguard]   tests/test_fan_out_integration.py::TestCounterfeitDomainFiltered::test_counterfeit_domain_filtered_even_when_first [egress] curl_cffi.Session.request https://02X7U6O3SI-dsn.algolia.net/1/indexes/enterprise_magento_en_bh_products/query
[netguard]   tests/test_fan_out_integration.py::TestScrapingModeSoftSkipsFirecrawl::test_scrapingmode_soft_skips_firecrawl_for_non_luxury [egress] curl_cffi.Session.request https://02X7U6O3SI-dsn.algolia.net/1/indexes/enterprise_magento_en_bh_products/query
[netguard]   tests/test_fan_out_integration.py::TestFallthroughToTier2WhenAllScrapersFail::test_fan_out_falls_through_to_tier2_when_all_scrapers_fail [egress] curl_cffi.Session.request https://02X7U6O3SI-dsn.algolia.net/1/indexes/enterprise_magento_en_bh_products/query
[pyt] tag=inc-i1-comm-base-07 start=2026-11-14 21:28:47 end=2026-11-14 21:29:07 elapsed=20s bound=1200s status=OK rc=0 log=<SP>\INC-I1\red\comm\comm_base_07.log
SUMMARY ================= 394 passed, 2 skipped, 1 warning in 18.77s ==================
=== job inc-i1-comm-base-08 rc=0 wall=45s
[pyt] --- summary lines ---
[netguard]   tests/test_flush_live_price_key.py::test_flag_on_a_misguessed_chip_still_deletes_the_live_key [egress] socket.getaddrinfo api.openai.com:443
[netguard]   tests/test_flush_live_price_key.py::test_flag_on_rung_two_deletes_the_key_the_raw_query_still_carries [egress] socket.getaddrinfo api.openai.com:443
[netguard]   tests/test_flush_live_price_key.py::test_flag_on_a_failing_l1_delete_makes_success_false_and_names_the_key [egress] socket.getaddrinfo api.openai.com:443
[netguard]   tests/test_flush_live_price_key.py::test_flag_on_a_failing_sentinel_delete_also_fails_success [egress] socket.getaddrinfo api.openai.com:443
[netguard]   tests/test_genuine_price_priority.py::TestFlagOffByteIdentity::test_flag_off_timeout_returns_parked_converted [egress] socket.getaddrinfo api.openai.com:443
[netguard]   tests/test_genuine_price_priority.py::TestRaceMissGenuineRecovery::test_fetch_product_data_race_miss_recovers_genuine_end_to_end [egress] socket.getaddrinfo api.openai.com:443
[pyt] tag=inc-i1-comm-base-08 start=2026-11-14 21:29:14 end=2026-11-14 21:29:53 elapsed=39s bound=1200s status=OK rc=0 log=<SP>\INC-I1\red\comm\comm_base_08.log
SUMMARY ===================== 2013 passed, 15 warnings in 37.89s ======================
=== job inc-i1-comm-base-09 rc=0 wall=66s
[pyt] --- summary lines ---
[netguard]   tests/test_http_400_cap_cut_mapping.py::TestCapCutMapsTo503::test_post_compare_timeout_maps_to_http_503 [sentinel] socket.create_connection neutralized.supabase.invalid:443
[netguard]   tests/test_http_400_cap_cut_mapping.py::TestCapCutMapsTo503::test_timeout_copy_has_no_forbidden_vocab [sentinel] socket.create_connection neutralized.supabase.invalid:443
[netguard]   tests/test_http_400_cap_cut_mapping.py::TestCapCutMapsTo503::test_insufficient_data_maps_to_http_400 [sentinel] socket.create_connection neutralized.supabase.invalid:443
[netguard]   tests/test_http_400_cap_cut_mapping.py::TestCapCutMapsTo503::test_content_unavailable_is_200_body [sentinel] socket.create_connection neutralized.supabase.invalid:443
[netguard]   tests/test_http_400_cap_cut_mapping.py::TestCapCutMapsTo503::test_partial_success_is_200 [sentinel] socket.create_connection neutralized.supabase.invalid:443
[netguard]   tests/test_http_400_cap_cut_mapping.py::TestCapCutMapsTo503::test_success_result_is_200 [sentinel] socket.create_connection neutralized.supabase.invalid:443
[pyt] tag=inc-i1-comm-base-09 start=2026-11-14 21:30:00 end=2026-11-14 21:31:00 elapsed=60s bound=1200s status=OK rc=0 log=<SP>\INC-I1\red\comm\comm_base_09.log
SUMMARY ========= 1400 passed, 1 skipped, 5 deselected, 22 warnings in 58.53s =========
=== job inc-i1-comm-base-10 rc=0 wall=111s
[gate] tag=inc-i1-comm-base-10 waiting: another lane is queued
[gate] tag=inc-i1-comm-base-10 waited=58s (another lane is queued)
[pyt] --- summary lines ---
[hermeticity] sentinel checked 628 test(s)
[netguard] blocked 13 attempt(s) from 2 node(s)
[netguard]   tests/test_latency_stack_i56.py::test_profile_fetch_concurrent_with_product_gather_sync [egress,sentinel] socket.getaddrinfo api.openai.com:443
[netguard]   tests/test_latency_stack_i56.py::test_profile_fetch_concurrent_with_product_gather_streaming [egress] socket.getaddrinfo api.openai.com:443
[pyt] tag=inc-i1-comm-base-10 start=2026-11-14 21:31:59 end=2026-11-14 21:32:51 elapsed=52s bound=1200s status=OK rc=0 log=<SP>\INC-I1\red\comm\comm_base_10.log
SUMMARY ================ 627 passed, 1 xfailed, 17 warnings in 50.99s =================
=== job inc-i1-comm-base-11 rc=0 wall=32s
[pyt] --- summary lines ---
[hermeticity] sentinel checked 463 test(s)
[netguard] blocked 2 attempt(s) from 2 node(s)
[netguard]   tests/test_m13_01_slowapi_middleware.py::test_change_password_respects_account_lockout [sentinel] socket.create_connection neutralized.supabase.invalid:443
[netguard]   tests/test_m13_01_slowapi_middleware.py::test_update_email_respects_account_lockout [sentinel] socket.create_connection neutralized.supabase.invalid:443
[pyt] tag=inc-i1-comm-base-11 start=2026-11-14 21:32:58 end=2026-11-14 21:33:24 elapsed=26s bound=1200s status=OK rc=0 log=<SP>\INC-I1\red\comm\comm_base_11.log
SUMMARY ====================== 463 passed, 16 warnings in 24.91s ======================
=== job inc-i1-comm-base-12 rc=0 wall=19s
[pyt] --- summary lines ---
[hermeticity] sentinel checked 176 test(s)
[netguard] blocked 1 attempt(s) from 1 node(s)
[netguard]   tests/test_m13_26_image_error_envelope.py::test_internal_error_is_not_leaked_to_client [sentinel] socket.create_connection neutralized.supabase.invalid:443
[pyt] tag=inc-i1-comm-base-12 start=2026-11-14 21:33:31 end=2026-11-14 21:33:43 elapsed=12s bound=1200s status=OK rc=0 log=<SP>\INC-I1\red\comm\comm_base_12.log
SUMMARY ====================== 176 passed, 17 warnings in 11.41s ======================
=== job inc-i1-comm-base-13 rc=0 wall=26s
[pyt] --- summary lines ---
[hermeticity] sentinel checked 575 test(s)
[netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=inc-i1-comm-base-13 start=2026-11-14 21:33:50 end=2026-11-14 21:34:09 elapsed=19s bound=1200s status=OK rc=0 log=<SP>\INC-I1\red\comm\comm_base_13.log
SUMMARY ========== 574 passed, 1 skipped, 10 deselected, 1 warning in 18.67s ==========
=== job inc-i1-comm-base-14 rc=1 wall=34s
[pyt] --- summary lines ---
[netguard]   tests/test_openai_breaker.py::test_breaker_read_raising_still_runs_the_compare [egress,sentinel] socket.create_connection neutralized.supabase.invalid:443
[netguard]   tests/test_openai_breaker.py::test_streaming_breaker_read_raising_still_runs_the_compare [egress,sentinel] socket.create_connection neutralized.supabase.invalid:443
[netguard]   tests/test_openai_breaker.py::test_flag_off_compare_never_short_circuits [egress,sentinel] socket.create_connection neutralized.supabase.invalid:443
[netguard]   tests/test_openai_breaker.py::test_flag_off_streaming_never_short_circuits [egress,sentinel] socket.create_connection neutralized.supabase.invalid:443
[netguard]   tests/test_paid_route_metering.py::test_camera_success_consumes_once_and_never_refunds [sentinel] socket.create_connection neutralized.supabase.invalid:443
[netguard]   tests/test_paid_route_metering.py::test_url_compare_saves_history_with_input_type_url [sentinel] socket.create_connection neutralized.supabase.invalid:443
[pyt] --- FAILED/ERROR ids (2) ---
[pyt] tag=inc-i1-comm-base-14 start=2026-11-14 21:34:16 end=2026-11-14 21:34:43 elapsed=27s bound=1200s status=FAIL rc=1 log=<SP>\INC-I1\red\comm\comm_base_14.log
SUMMARY ========== 2 failed, 3721 passed, 22 skipped, 18 warnings in 25.61s ===========
FAILED tests/test_page_scraping.py::TestFetchPagePriceJsonLD::test_jsonld_nested_offers_picks_lowest
FAILED tests/test_page_scraping.py::TestFetchPagePriceOpenGraph::test_og_meta_extraction
=== job inc-i1-comm-base-15 rc=1 wall=43s
[pyt] --- summary lines ---
[netguard]   tests/test_personalization.py::TestComparisonServicePersonalization::test_personalization_factors_include_lifestyle [egress] socket.getaddrinfo api.openai.com:443
[netguard]   tests/test_personalization.py::TestComparisonServicePersonalization::test_personalization_factors_empty_without_prefs [egress] socket.getaddrinfo api.openai.com:443
[netguard]   tests/test_personalization.py::TestComparisonServicePersonalization::test_personalized_false_with_empty_dict [egress] socket.getaddrinfo api.openai.com:443
[netguard]   tests/test_price_cache_bust_probe.py::TestPriceReadBypass::test_bust_skips_price_redis_read [egress] curl_cffi.Session.request https://shopalmoayyed.com/products.json?limit=250
[netguard]   tests/test_price_cache_bust_probe.py::TestPriceReadBypass::test_specs_reviews_cache_untouched_by_price_bust [egress] curl_cffi.Session.request https://shopalmoayyed.com/products.json?limit=250
[netguard]   tests/test_price_fallback.py::TestAllTiersFail::test_all_tiers_fail_returns_none_amount [egress] curl_cffi.Session.request https://www.footlocker.com.bh/configs.json
[pyt] --- FAILED/ERROR ids (2) ---
[pyt] tag=inc-i1-comm-base-15 start=2026-11-14 21:34:50 end=2026-11-14 21:35:27 elapsed=37s bound=1200s status=FAIL rc=1 log=<SP>\INC-I1\red\comm\comm_base_15.log
SUMMARY ==== 2 failed, 744 passed, 3 skipped, 5 deselected, 23 warnings in 35.89s =====
FAILED tests/test_personalization_bundle_c.py::test_applied_shifts_list_is_default_empty_when_no_priorities
FAILED tests/test_personalization_bundle_c.py::test_full_response_payload_audit_no_magnitude_keys
=== job inc-i1-comm-base-16 rc=1 wall=228s
[gate] tag=inc-i1-comm-base-16 waiting: another lane is queued
[gate] tag=inc-i1-comm-base-16 waiting: another lane took the slot
[gate] tag=inc-i1-comm-base-16 waited=200s (another lane is queued, another lane took the slot)
[pyt] --- summary lines ---
[netguard]   tests/test_rate_limiting_complete.py::TestRateLimitCoverage::test_url_detect_post_rate_limited [egress] socket.getaddrinfo example.com:None
[netguard]   tests/test_rate_limiting_complete.py::TestRateLimitCoverage::test_url_detect_get_rate_limited [egress] socket.getaddrinfo example.com:None
[netguard]   tests/test_rate_limiting_complete.py::TestRateLimitCoverage::test_share_view_rate_limited [sentinel] socket.create_connection neutralized.supabase.invalid:443
[netguard]   tests/test_rate_limiting_complete.py::TestRateLimitCoverage::test_auth_refresh_rate_limited [sentinel] socket.create_connection neutralized.supabase.invalid:443
[netguard]   tests/test_rate_limiting_complete.py::TestInputValidationGaps::test_history_search_max_length [sentinel] socket.create_connection neutralized.supabase.invalid:443
[netguard]   tests/test_rating_provenance.py::test_sse_reviews_event_nulls_derived_rating [egress] socket.getaddrinfo api.openai.com:443
[pyt] --- FAILED/ERROR ids (2) ---
[pyt] tag=inc-i1-comm-base-16 start=2026-11-14 21:38:48 end=2026-11-14 21:39:15 elapsed=27s bound=1200s status=FAIL rc=1 log=<SP>\INC-I1\red\comm\comm_base_16.log
SUMMARY = 404 passed, 3 skipped, 9 deselected, 1 xfailed, 17 warnings, 2 errors in 26.09s =
ERROR tests/test_prompt_truth.py::test_render_digests_match_base_except_the_fence
ERROR tests/test_prompt_truth.py::test_truth_on_prefix_static_and_cacheable
=== job inc-i1-comm-base-17 rc=0 wall=304s
[gate] tag=inc-i1-comm-base-17 waiting: another lane is queued
[gate] tag=inc-i1-comm-base-17 waiting: another lane took the slot
[gate] tag=inc-i1-comm-base-17 waited=116s (another lane is queued, another lane took the slot)
[pyt] tag=inc-i1-comm-base-17 status=BUSY rc=126 waited=0s (this lane's pytest mutex is held by pid 27940; NOT started)
[gate] tag=inc-i1-comm-base-17 waiting: another lane's run is live
[gate] tag=inc-i1-comm-base-17 waiting: another lane took the slot
[gate] tag=inc-i1-comm-base-17 waiting: another lane is queued
[gate] tag=inc-i1-comm-base-17 waited=163s (another lane is queued, another lane took the slot, another lane's run is live)
[pyt] --- summary lines ---
[netguard]   tests/test_referral_e2e.py::test_e2e_admin_referrals_dashboard_returns_metrics [sentinel] socket.create_connection neutralized.supabase.invalid:443
[netguard]   tests/test_referral_lifetime_cap.py::TestLifetimeCapEnforcement::test_rejects_at_3_on_device [sentinel] socket.create_connection neutralized.supabase.invalid:443
[netguard]   tests/test_referral_loop2.py::TestLoop2HappyPath::test_first_comparison_after_signup_grants_bonus [sentinel] socket.create_connection neutralized.supabase.invalid:443
[netguard]   tests/test_referral_loop2.py::TestLoop2HappyPath::test_premium_referrer_grants_10_not_5 [sentinel] socket.create_connection neutralized.supabase.invalid:443
[netguard]   tests/test_referral_routes.py::TestGetReferralInvite::test_route_is_registered [sentinel] socket.create_connection neutralized.supabase.invalid:443
[netguard]   tests/test_referral_routes.py::TestPostInviteQuiz::test_route_is_registered [sentinel] socket.create_connection neutralized.supabase.invalid:443
[pyt] tag=inc-i1-comm-base-17 start=2026-11-14 21:44:07 end=2026-11-14 21:44:20 elapsed=13s bound=1200s status=OK rc=0 log=<SP>\INC-I1\red\comm\comm_base_17.log
SUMMARY ========= 320 passed, 1 skipped, 1 deselected, 17 warnings in 12.06s ==========
=== job inc-i1-comm-base-18 rc=0 wall=173s
[pyt] --- summary lines ---
[hermeticity] sentinel checked 862 test(s)
[netguard] blocked 20 attempt(s) from 1 node(s)
[netguard]   tests/test_retro_w1_3.py::test_pin_flag_off_both_compare_entries_never_read_the_openai_breaker [egress] curl_cffi.Session.request https://shopalmoayyed.com/products.json?limit=250
[pyt] tag=inc-i1-comm-base-18 start=2026-11-14 21:44:26 end=2026-11-14 21:47:13 elapsed=167s bound=1200s status=OK rc=0 log=<SP>\INC-I1\red\comm\comm_base_18.log
SUMMARY ================ 862 passed, 373 warnings in 164.76s (0:02:44) ================
=== job inc-i1-comm-base-19 rc=0 wall=90s
[pyt] --- summary lines ---
[hermeticity] sentinel checked 1439 test(s)
[netguard] blocked 4 attempt(s) from 2 node(s)
[netguard]   tests/test_s78_all_timeout_cap_as_timeout.py::test_F15_route_end_to_end[on] [sentinel] socket.create_connection neutralized.supabase.invalid:443
[netguard]   tests/test_s78_all_timeout_cap_as_timeout.py::test_F15_route_end_to_end[off] [sentinel] socket.create_connection neutralized.supabase.invalid:443
[pyt] tag=inc-i1-comm-base-19 start=2026-11-14 21:47:20 end=2026-11-14 21:48:43 elapsed=83s bound=1200s status=OK rc=0 log=<SP>\INC-I1\red\comm\comm_base_19.log
SUMMARY ================ 1439 passed, 17 warnings in 81.79s (0:01:21) =================
=== job inc-i1-comm-base-20 rc=1 wall=61s
[pyt] --- summary lines ---
[hermeticity] sentinel checked 2221 test(s)
[netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] --- FAILED/ERROR ids (7) ---
[pyt] tag=inc-i1-comm-base-20 start=2026-11-14 21:48:50 end=2026-11-14 21:49:45 elapsed=55s bound=1200s status=FAIL rc=1 log=<SP>\INC-I1\red\comm\comm_base_20.log
SUMMARY ================ 7 failed, 2214 passed, 16 warnings in 53.45s =================
FAILED tests/test_s81_d16_operator_ingest.py::test_r10_runbook_names_only
FAILED tests/test_s81_d17_coverage.py::test_r9_railway_config_and_hygiene
FAILED tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[OFF]
FAILED tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[empty]
FAILED tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[false]
FAILED tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[pad0]
FAILED tests/test_s81_d22c_profile_select.py::test_p1_flag_off_golden[unset]
=== job inc-i1-comm-base-21 rc=1 wall=135s
[pyt] --- summary lines ---
[hermeticity] sentinel checked 2548 test(s)
[netguard] blocked 24 attempt(s) from 2 node(s)
[netguard]   tests/test_s81_s04_spend_breaker.py::test_r42_on_with_headroom_accounts_every_create [sentinel] socket.create_connection neutralized.supabase.invalid:443
[netguard]   tests/test_s81_s04_spend_breaker.py::test_p08_on_with_headroom_changes_no_response_field [sentinel] socket.create_connection neutralized.supabase.invalid:443
[pyt] --- FAILED/ERROR ids (7) ---
[pyt] tag=inc-i1-comm-base-21 start=2026-11-14 21:49:52 end=2026-11-14 21:52:01 elapsed=129s bound=1200s status=FAIL rc=1 log=<SP>\INC-I1\red\comm\comm_base_21.log
SUMMARY ========== 7 failed, 2541 passed, 137 warnings in 126.98s (0:02:06) ===========
FAILED tests/test_s81_s07_meas_harness.py::test_r35_fixtures
FAILED tests/test_s81_s10_fragrance_gate.py::test_r06_production_lexicon_content
FAILED tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[cron_feed_walker]
FAILED tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[cron_pdp_discovery]
FAILED tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[kb_seed_common]
FAILED tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[seed_kb_batch]
FAILED tests/test_s81_s16_kb_seed.py::test_s16_r27_hygiene_of_g2_files[seed_kb_brands_wikidata]
=== job inc-i1-comm-base-22 rc=1 wall=58s
[pyt] --- summary lines ---
[netguard]   tests/test_s81_s20_result_gate.py::test_r26_category_conflict_both_flags [sentinel] socket.create_connection neutralized.supabase.invalid:443
[netguard]   tests/test_s81_s20_result_gate.py::test_r27_supported_real_orchestrator_stamp [sentinel] socket.create_connection neutralized.supabase.invalid:443
[netguard]   tests/test_s81_s20_result_gate.py::test_r31_fragrance_gate_counts_result_gate_refusal [sentinel] socket.create_connection neutralized.supabase.invalid:443
[netguard]   tests/test_s81_s20_result_gate.py::test_r33_g3_tail_no_evidence [sentinel] socket.create_connection neutralized.supabase.invalid:443
[netguard]   tests/test_s81_s20_result_gate.py::test_r34_g3_tail_identity_classes[conflict] [sentinel] socket.create_connection neutralized.supabase.invalid:443
[netguard]   tests/test_s81_s20_result_gate.py::test_r34_g3_tail_identity_classes[same] [sentinel] socket.create_connection neutralized.supabase.invalid:443
[pyt] --- FAILED/ERROR ids (6) ---
[pyt] tag=inc-i1-comm-base-22 start=2026-11-14 21:52:08 end=2026-11-14 21:52:59 elapsed=51s bound=1200s status=FAIL rc=1 log=<SP>\INC-I1\red\comm\comm_base_22.log
SUMMARY ================ 6 failed, 1687 passed, 49 warnings in 49.88s =================
FAILED tests/test_s81_s18b_store_label.py::test_r2_table_shape
FAILED tests/test_s81_s19_gap_queue.py::test_r15_hygiene
FAILED tests/test_s81_s22_compare_runs.py::test_b02_one_transaction_ascii_lf
FAILED tests/test_s81_s22_judge.py::test_j01_script_exists_and_off_first
FAILED tests/test_s81_s24_auth_throttle.py::test_p83_red_file_setenv_hygiene
FAILED tests/test_s81_s24_auth_throttle.py::test_r92_hygiene
=== job inc-i1-comm-base-23 rc=0 wall=44s
[pyt] --- summary lines ---
[netguard]   tests/test_security_regression.py::TestQueryMaxLength::test_normal_length_query_accepted [egress,sentinel] socket.getaddrinfo api.openai.com:443
[netguard]   tests/test_security_regression.py::TestDemographicsEndpointAuth::test_put_demographics_invalid_token_returns_401 [sentinel] socket.create_connection neutralized.supabase.invalid:443
[netguard]   tests/test_security_regression.py::TestReferralQuizNoAuthAndNoPII::test_quiz_endpoint_anon_path_exists [sentinel] socket.create_connection neutralized.supabase.invalid:443
[netguard]   tests/test_security_regression.py::TestBundleBContentSafety::test_dual_shape_product_a_b_hits_sanitizer [egress,sentinel] socket.getaddrinfo api.openai.com:443
[netguard]   tests/test_security_regression.py::TestBundleBContentSafety::test_content_safety_query_prefilter_blocks_weapons [sentinel] socket.create_connection neutralized.supabase.invalid:443
[netguard]   tests/test_security_regression.py::TestBundleBContentSafety::test_camera_vision_moderation_blocks_explicit_capture [sentinel] socket.create_connection neutralized.supabase.invalid:443
[pyt] tag=inc-i1-comm-base-23 start=2026-11-14 21:53:06 end=2026-11-14 21:53:44 elapsed=38s bound=1200s status=OK rc=0 log=<SP>\INC-I1\red\comm\comm_base_23.log
SUMMARY ================ 1118 passed, 1 xfailed, 17 warnings in 36.33s ================
=== job inc-i1-comm-base-24 rc=0 wall=52s
[pyt] --- summary lines ---
[hermeticity] sentinel checked 657 test(s)
[netguard] blocked 14 attempt(s) from 4 node(s)
[netguard]   tests/test_share_routes.py::test_view_shared_no_auth_needed [sentinel] socket.create_connection neutralized.supabase.invalid:443
[netguard]   tests/test_shopify_cascade_wiring_l13.py::test_shopify_not_called_for_category_without_shopify_source [egress] socket.getaddrinfo api.openai.com:443
[netguard]   tests/test_singleton_state.py::TestStateReset::test_shopping_cache_cleared_on_new_request [egress] socket.getaddrinfo api.openai.com:443
[netguard]   tests/test_smart_fallback.py::test_smart_fallback_overwrites_NA_string [egress,sentinel] socket.getaddrinfo api.openai.com:443
[pyt] tag=inc-i1-comm-base-24 start=2026-11-14 21:53:51 end=2026-11-14 21:54:36 elapsed=46s bound=1200s status=OK rc=0 log=<SP>\INC-I1\red\comm\comm_base_24.log
SUMMARY ========= 657 passed, 1 skipped, 2 deselected, 16 warnings in 44.91s ==========
=== job inc-i1-comm-base-25 rc=0 wall=48s
[pyt] --- summary lines ---
[netguard]   tests/test_streaming.py::TestNewResponseStructure::test_overview_products_have_value_badge [egress] socket.getaddrinfo api.openai.com:443
[netguard]   tests/test_streaming.py::TestNewResponseStructure::test_reviews_have_review_summary [egress] socket.getaddrinfo api.openai.com:443
[netguard]   tests/test_streaming.py::TestNewResponseStructure::test_verdict_event_has_structured_winner [egress] socket.getaddrinfo api.openai.com:443
[netguard]   tests/test_streaming.py::TestNewResponseStructure::test_scores_event_has_confidence [egress] socket.getaddrinfo api.openai.com:443
[netguard]   tests/test_supplement_branch_genuine.py::TestCategoryGateTrustsConcreteCategory::test_electronics_routes_through_non_supplement_branch [egress] curl_cffi.Session.request https://shopalmoayyed.com/products.json?limit=250
[netguard]   tests/test_supplement_branch_genuine.py::TestCatalogSupplementSourceAttribution::test_cde2_attributes_catalog_supplement_domain_when_flag_on [egress] curl_cffi.Session.request https://musclepumpqa.com/wp-json/wc/store/products
[pyt] tag=inc-i1-comm-base-25 start=2026-11-14 21:54:43 end=2026-11-14 21:55:25 elapsed=42s bound=1200s status=OK rc=0 log=<SP>\INC-I1\red\comm\comm_base_25.log
SUMMARY ========= 456 passed, 7 skipped, 8 deselected, 24 warnings in 40.85s ==========
=== job inc-i1-comm-base-26 rc=0 wall=42s
[pyt] --- summary lines ---
[netguard]   tests/test_two_input_shape.py::TestOptionalFieldsPreserved::test_pair_shape_defaults_preserved [sentinel] socket.create_connection neutralized.supabase.invalid:443
[netguard]   tests/test_two_input_shape.py::TestContentSafetyInterception::test_pair_shape_blocked_query_returns_content_unavailable [sentinel] socket.create_connection neutralized.supabase.invalid:443
[netguard]   tests/test_two_input_shape.py::TestContentSafetyInterception::test_pair_shape_clean_passes_l1 [sentinel] socket.create_connection neutralized.supabase.invalid:443
[netguard]   tests/test_two_input_shape.py::TestContentSafetyInterception::test_legacy_query_blocked_by_l1_same_path [sentinel] socket.create_connection neutralized.supabase.invalid:443
[netguard]   tests/test_two_input_shape.py::TestGetEndpointDualShape::test_get_endpoint_accepts_query_shape [sentinel] socket.create_connection neutralized.supabase.invalid:443
[netguard]   ... 5 more node(s) in the report
[pyt] tag=inc-i1-comm-base-26 start=2026-11-14 21:55:32 end=2026-11-14 21:56:08 elapsed=36s bound=1200s status=OK rc=0 log=<SP>\INC-I1\red\comm\comm_base_26.log
SUMMARY =============== 561 passed, 4 deselected, 17 warnings in 34.47s ===============
=== job inc-i1-comm-base-27 rc=0 wall=49s
[pyt] tag=inc-i1-comm-base-27 status=BUSY rc=126 waited=0s (this lane's pytest mutex is held by pid 42760; NOT started)
[pyt] --- summary lines ---
[hermeticity] sentinel checked 417 test(s)
[netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=inc-i1-comm-base-27 start=2026-11-14 21:56:31 end=2026-11-14 21:56:57 elapsed=27s bound=1200s status=OK rc=0 log=<SP>\INC-I1\red\comm\comm_base_27.log
SUMMARY ========= 382 passed, 4 deselected, 35 xfailed, 14 warnings in 25.89s =========
=== job inc-i1-comm-base-28 rc=0 wall=40s
[pyt] --- summary lines ---
[netguard]   tests/test_w49_extraction_catch_redaction.py::test_r2c_persisted_row_carries_no_raw_text [sentinel] socket.create_connection neutralized.supabase.invalid:443
[netguard]   tests/test_w49_extraction_catch_redaction.py::test_r2c_share_payload_carries_no_raw_text [sentinel] socket.create_connection neutralized.supabase.invalid:443
[netguard]   tests/test_winner_prose_reconciliation.py::test_sse_verdict_event_uses_deterministic_winner_index [egress] socket.getaddrinfo api.openai.com:443
[netguard]   tests/test_winner_prose_reconciliation.py::test_sse_verdict_and_complete_agree_on_winner [egress] socket.getaddrinfo api.openai.com:443
[netguard]   tests/test_winner_prose_reconciliation.py::test_sse_flag_off_verdict_event_uses_deterministic_index [egress] socket.getaddrinfo api.openai.com:443
[netguard]   tests/test_winner_prose_reconciliation.py::test_sse_flag_off_verdict_and_complete_agree_on_the_reason [egress] socket.getaddrinfo api.openai.com:443
[pyt] tag=inc-i1-comm-base-28 start=2026-11-14 21:57:04 end=2026-11-14 21:57:38 elapsed=34s bound=1200s status=OK rc=0 log=<SP>\INC-I1\red\comm\comm_base_28.log
SUMMARY =============== 1249 passed, 10 skipped, 17 warnings in 32.75s ================
=== job inc-i1-comm-base-29 rc=0 wall=12s
[pyt] --- summary lines ---
[hermeticity] sentinel checked 169 test(s)
[netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=inc-i1-comm-base-29 start=2026-11-14 21:57:45 end=2026-11-14 21:57:51 elapsed=6s bound=1200s status=OK rc=0 log=<SP>\INC-I1\red\comm\comm_base_29.log
SUMMARY ======================= 169 passed, 1 warning in 5.46s ========================
=== ALL DONE
```
