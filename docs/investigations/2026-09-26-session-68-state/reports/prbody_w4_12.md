## W4-12 - display contract: one spelling, one margin, one verdict

This PR addresses PO-VERDICT-TRUTH-03, -04, -06 (margin half), -07, -08, -09 and -14. All seven are P2 and were measured.

Binding inputs, in order:
- the spec `.qa-s68/specs/W4_12_UNIT_SPEC.md` and its adversarial review
- Fable rulings F1-F7 and K1-K12
- red-gate rulings R1-R7
- post-adversary rulings R8-R11 (fix round 1)
- rulings R13-R15 (fix round 2)
- rulings R16-R18 (fix round 3)
- rulings R19-R20 (fix round 4)
- rulings R21-R22 (fix round 5)

This PR contains all five fix rounds.

### Defects (measured at base)
- **-03: SSE verdict frame is raw.** The SSE `verdict` frame shipped the raw GPT verdict. On a leaky verdict, 8 of the 10 fields it shares with `complete` differed, and 8 fields carried score internals ("scores 73.8 overall", "+5 pts").
- **-04: Reviews alias is raw.** The BC `products[i].reviews.review_summary` alias re-shipped the raw summary, although the canonical projection scrubs it. That alias is persisted and is served by the unauthenticated `GET /share/{token}`.
  - The RENDERED `review_praise` was built from the raw summary on both surfaces.
  - The mechanism is real, but the recorded data has no affected rows: 0 of 46 stored summaries and 0 of 8 praise lines.
- **-07: Doubled brand.**
  - `/home/smart-pick` doubled the brand on 12 of 22 eligible corpus rows (`TOM FORD TOM FORD SOLEIL NEIGE 100ML`).
  - `/profile/recent-decisions` doubled it on 16 of 26 rows.
- **-08: Caption is the name, or the wrong name.** `verdict_short` was the winner's own name on 20 of 26 rows, and named ONLY THE LOSER on 2 rows.
- **-09: Silent scrub.** The verdict scrub silently replaced 17 of 23 recorded reasons, with zero telemetry.
- **-14 / -06: Two margins.** Every payload carried two margins, and all 23 corpus rows disagree (33.4 vs 16; on a tie, 0.0 vs a nudge-fabricated 1). In streaming, the verdict frame said 6 while `scoring_v2` said 3.

### Design

**The verdict scrub helper**

`response_builder.scrub_verdict_prose(comparison, product_names, winner_index) -> bool` is the SIB-4 block moved out of `build_comparison_response`, plus the winner-text write-back:
- `winner_reason` becomes either the scrubbed text or the qualitative fallback for `product_names[winner_index]`. That index is the RECONCILED winner (R9).
- `key_tradeoff` and `winner_declaration` are rewritten only when the key is already present. The helper never creates either key (R10).

**When a scrub is counted (R2 + R8 + R14)**

The helper decides from the INCOMING `winner_reason` only. A scrub counts when all three hold:
- the text is non-empty;
- `strip_score_internals` empties it;
- the text is NOT our own, meaning it is neither of:
  - the qualitative fallback for the RECONCILED winner;
  - the reconcile's deterministic replacement ("... edges ahead / leads on the overall picture.").

Both of those texts come from one source, `_deterministic_winner_reasons`, which `deterministic_verdict_fields` also uses; its output is unchanged.

The exclusion is keyed on the reconciled winner, not on product 0. A pin reverses the Graco pair (Graco is product 1 and the reconciled winner; GPT picked 0 with a clean reason), with reconcile both off and on. The expected result is no metadata key, no log line, and Graco's fallback as the served reason. A mutant that builds the exclusion from `product_names[0]` turns that pin red.

**Logging**

When a scrub is counted, the helper logs ONE `[VERDICT_SCRUB]` WARNING with the winner name and the first 200 chars of the dropped GPT text. It logs no query and no user id.
- The fallback write-back is never counted or logged. That holds even when the winner's own display name trips the strip (e.g. "5-Point Harness").
- So a request produces exactly ONE line when a scrub is counted.
- A partial strip is not counted.
- A reason that the reconcile already replaced is not counted.

**Call sites and telemetry**
- **Streaming order.** `compare_from_text_streaming` calls the helper right after `reconcile_winner_prose` and before `_verdict_winner_name` and the yield. That order is pinned: the SSE mismatch pin fails if the scrub runs first.
- **Builder's second call.** The builder calls the helper again on the same dict. That call changes no text, because `strip_score_internals` is idempotent (R-idempotence pin), and it counts nothing (R8).
- **Metadata.** `metadata.verdict_scrubbed: true` is present only when a scrub was counted; it is never `false`. It is set via `_metadata_override` on the stream, and after the metadata merge in the builder.

**Reviews**
- `_safe_review_praise` builds the praise from `scrub_review_summary(...)` (F2).
- The alias `review_summary` is rebuilt as a NEW dict after the alias praise line, so the caller's reviews dict is never mutated.
- `retailer_quotes` stay verbatim, because they are third-party snippets (pin B4).
- Placing the alias rebuild after the praise line is a code-order CONVENTION only; it is not load-bearing (R1).

**Display names**
- `home_routes:527/:528` and `profile_routes:102/:103` use `dedup_brand_name`. When the name does not already carry the brand, the result is identical to the old concatenation.
- `home_routes:456` (priority_match) is untouched.

**Loser guard (UNFLAGGED; it judges the TRUNCATED `verdict_short`, the text the user sees)**

`home_routes._names_only_the_loser` checks whether a caption names the loser and not the winner. It matches casefolded word tokens.
- **Shared forms are evidence for NEITHER side (R19).** Each product has two name forms: the bare name and the brand-deduped display name. A form whose token form is also a token form of the other product is SHARED and is dropped from both sides' evidence. Examples: the bare "Air Fryer" of Ninja and Philips, or "Air Fryer" vs "Air-Fryer". Only the DISTINGUISHING forms (here "Ninja Air Fryer" / "Philips Air Fryer") can name a product.
- **Shared forms are still masked and credit no one (R21).** The longest-first masking pass masks EVERY form, shared and distinguishing. A match inside a masked shared form credits no one. So when two products DISPLAY the same name, a caption naming that display name is kept, even though one product's shorter bare name sits inside it. Examples: brand "" + "Philips Air Fryer XL" vs "Philips" + "Air Fryer XL"; Tom Ford "Tom Ford Soleil Neige" vs Tom Ford "Soleil Neige".
- **Whole tokens (R11 / R17).** A form matches only with no letter or digit on EITHER side:
  - a loser named "Air" does not match inside "Airy" (trailing boundary);
  - it does not match at the tail of "Repair" either (leading boundary, pinned: winner "Air Max 90", loser "Air", caption "Repair kit wins the day" -> KEPT).
- **Plus signs (R13 + R17).** A "+" (or the fullwidth U+FF0B) GLUED to the preceding letter or digit becomes the token "plus" BEFORE punctuation is dropped. So "Galaxy S25+" -> "galaxy s25 plus", and it never collapses into "Galaxy S25". A free-standing " + " in prose stays punctuation. Pinned: winner "iPad", loser "iPad Plus", caption "iPad + keyboard bundle wins" -> KEPT, because it does not name the loser.
- **Longest first (K10).** All forms of both products are masked longest first.
- **Winner named means kept.** Any caption that names a distinguishing winner form is kept.
- **Loser only means dropped.** A caption that names only a distinguishing loser form becomes None, and the card renders the `reason_key` copy.

The four ruled Galaxy cases are pinned, plus fullwidth-plus twins:

| winner | loser | caption | result |
|---|---|---|---|
| Galaxy S25+ | Galaxy S25 | Galaxy S25 Plus | KEPT |
| Galaxy S25+ | Galaxy S25 | Galaxy S25 | DROPPED |
| Galaxy S25 | Galaxy S25+ | Galaxy S25+ | DROPPED |
| Galaxy S25 | Galaxy S25+ | Samsung Galaxy S25+ wins | DROPPED |

K10 cases still hold: "Galaxy S25 Ultra" on a "Galaxy S25" winner's tile is dropped; "iPhone 15 Pro edges the iPhone 15" is kept.

The R19 cases are pinned:

| winner | loser | caption | result |
|---|---|---|---|
| Ninja "Air Fryer" | Philips "Air-Fryer" | Philips Air Fryer wins | DROPPED |
| Philips "Air-Fryer" | Ninja "Air Fryer" | Ninja Air Fryer wins | DROPPED |
| Ninja "Air Fryer" | Philips "Air-Fryer" | Philips Air Fryer beats every other air fryer | DROPPED |
| Ninja "Air Fryer" | Philips "Air-Fryer" | Air Fryer wins on crisp | KEPT (names neither distinguishing form) |
| "!!!" | "???" | ??? wins | KEPT (a punctuation-only name is never evidence) |
| Ninja "Air Fryer" | Philips "Air Fryer" | Philips' Air Fryer is quieter / Philips(TM) Air Fryer (trademark sign) / Philips-Air Fryer wins | DROPPED |

The R21 and R22 cases are pinned:

| winner | loser | caption | result |
|---|---|---|---|
| "" "Philips Air Fryer XL" | Philips "Air Fryer XL" | Philips Air Fryer XL wins | KEPT, both pair directions (R21: same display name) |
| Tom Ford "Tom Ford Soleil Neige" | Tom Ford "Soleil Neige" | Tom Ford Soleil Neige | KEPT, both pair directions (R21) |
| "" "Air Fryer" | Philips "Air-Fryer" | Philips Air Fryer wins | DROPPED (R22 i: the winner has no distinguishing form) |
| Philips "Air-Fryer" | "" "Air Fryer" | Philips Air Fryer wins / Air Fryer wins on crisp | KEPT (R22 ii: the loser has no distinguishing form) |

- **Safety net (R13; trigger R19; both halves of the trigger pinned by R22).** It runs ONLY when no distinguishing token form remains on EITHER side: identical names, or names differing only by punctuation (pinned synthetic case: Sony "WH-1000XM5" vs Sony "WH 1000XM5").
  - There the guard compares the whitespace-normalised, punctuation-KEPT forms (bare and display name), again distinguishing forms only, with the same whole-token masking (shared raw forms masked too). A punctuation-only difference therefore never turns the guard off silently: "WH 1000XM5" on the "WH-1000XM5" winner's tile is DROPPED, "WH-1000XM5" is KEPT.
  - When only ONE side has no distinguishing form, the guard stays on the token path (R22 rows above).
  - Two products whose names are identical in every form leave no evidence, so a caption naming that name is kept (pinned).
  - A form whose token form is empty (a name made only of punctuation) is never evidence, so the guard stays off for such names (pinned).
  - This replaces fix round 3's separate `_names_collide` trigger. The Philips rows and the WH rows are the pins that prove the fold.
- **Documented conservative drop (R11).** Winner "Sauvage Elixir", loser "Sauvage", caption "The Elixir concentration of Sauvage": the caption is dropped. The winner's name is not contiguous in it, so it names only the loser as a whole name. It joins measured corpus rows 12 and 13 in rendering the reason_key copy.

**The margin flag**
- New symbols: `response_builder.single_verdict_margin_enabled()`, `_calibrated_gap()`, and `_build_scoring_v2(..., single_margin=False)`.
- `build_comparison_response(..., _single_margin: Optional[bool] = None)` is a PRIVATE kwarg (R4; see its docstring). With None, the builder reads the env once per build. scs reads the flag ONCE per stream and routes the value in (K12).
- The overview margin is overridden only when `scoring_v2` is a non-empty dict.

### Flags (both default OFF, read per call, `.strip().lower() in ("1","true","yes","on")`)
| flag | effect ON | OFF |
|---|---|---|
| `ENABLE_SINGLE_VERDICT_MARGIN` | The PRE-nudge calibrated gap (an exact tie gives 0) goes into `overview.winner.margin`, `scoring_v2.win_margin` and the SSE verdict `winner.margin`. scs reads it ONCE per stream and routes it into the builder. The nudged `overall_score` pair is unchanged. The `scores` SSE event keeps the RAW margin. If `scoring_v2` is `{}` or `None`, the raw overview margin is kept. | Byte-identical (gate 3) |
| `ENABLE_SMART_PICK_VERDICT_CAPTION` | The Home `verdict_short` source is `scoring_v2.factual_verdict.line1`, then `strip_score_internals(overview.winner.reason)`, then None. Order: the tautology guard runs first (a caption equal to the winner's name -> None), then truncation (`_truncate_verdict_short`), then the unflagged loser guard on the TRUNCATED `verdict_short`. Changes the caption on 19 of 22 eligible corpus rows. | Today's declaration, truncated, then the same unflagged loser guard |

There are no knobs.

**Stated deviation from spec 4.4 (accepted by R15).** Spec 4.4 ordered guard-then-truncate. The code truncates first and runs the loser guard on the truncated text, because the guard must judge the text the user actually sees. The two orders can differ only for a caption longer than 140 characters. The longest measured stored declaration is 40 characters, against the 140-character target.

**Canary plan**
- **Margin flag:** the canary series is the `cta_variant` property on `share*` events. That is analytics only; no phone renders either margin. Flipping it together with the mobile CTA-threshold OTA is a RECOMMENDATION, not a precondition (K2).
- **Caption flag:** canary it ALONE. The change becomes visible within the 5-minute `home:smart_pick:{uid}` TTL.

### What changes for callers with BOTH flags OFF (unflagged, by ruling F4)
- **SSE verdict frame.** It is scrubbed and equals `complete` on the shared fields. It also moves on clean-but-irregular input: whitespace is normalised, and an absent reason becomes the qualitative fallback. No phone consumes this frame (`onVerdict` is unregistered and SSE is off).
- **Reviews.** The alias `review_summary` and `review_praise` are scrubbed on both surfaces.
- **Display names.** Smart-pick and recent-decisions names are deduped (12 of 22 and 16 of 26 corpus rows). This becomes visible within the 5-minute Redis TTL.
- **Loser guard.** A `verdict_short` that names only the loser becomes None: 2 of 26 rows. The rules, all described above:
  - evidence is distinguishing name forms only, so shared forms count for neither side;
  - every form, shared ones included, is masked longest first, and a shared form credits no one;
  - matching is whole-token on both edges;
  - a glued "+" is a token;
  - the punctuation-kept safety net applies only when no distinguishing form remains on either side.
- **Telemetry.** `metadata.verdict_scrubbed` is an additive key, with one `[VERDICT_SCRUB]` line per request when a scrub is counted.

### OWNED intra-payload fact under the margin flag (K2/F1)
With the margin flag ON, `scoring_v2.win_margin` (pre-nudge) differs from `|overall_score.product_a - product_b|` (post-nudge). This happens:
- on nudged or tied rows: 4 of 23 corpus rows (three exact ties plus row 4);
- on W4-4's fabricated 70/69 block.

**W4-12b** closes it: honest tie scores, with phones reading `winner_idx` first.

### Scrub-rate publication
The `[VERDICT_SCRUB]` WARNING volume will be the first live measurement of the scrub rate (17 of 23 on the historical corpus).
- It counts only GPT text that the strip EMPTIED.
- It never counts our own fallback or deterministic text for the reconciled winner (R8/R14).
- It never counts a reason the reconcile replaced.
- A partial strip is not counted (R2).
- The published rate must EXCLUDE W4-4 honest partials (`metadata.partial = true`), whose reason is blanked afterwards. Otherwise it overstates the GPT leak rate.

### K1 collateral (R5): the only edits to existing tests
`monkeypatch.delenv` of the NEW flag was added to exactly these 23 nodes, all of which pin the flag-OFF world. Each line is load-bearing: removing it reddens exactly its nodes.

- `ENABLE_SINGLE_VERDICT_MARGIN` (22):
  - `tests/test_partial_response_no_fabricated_scores.py::test_05a_pin_flag_off_builder_is_unchanged[None|''|false|0|no|off]`
  - `::test_05b_pin_flag_off_post_gather_partial_is_unchanged[None|''|false|0|no|off]`
  - `::test_05c_pin_flag_off_early_partial_is_unchanged[None|''|false|0|no|off]`
  - `::test_15_pin_non_partial_absent_overall_keeps_calibrated_block[None|true]`
  - `tests/test_prescoring_showable_guard.py::test_10b_pin_flag_off_end_to_end_numbers_hold[unset|false]`
- `ENABLE_SMART_PICK_VERDICT_CAPTION` (1):
  - `tests/test_home_routes.py::TestHomeSmartPick::test_extension_fields_present_when_data_available`. This method gained a `monkeypatch` parameter plus one line.

### Gates (measured)

**Unit file** `tests/test_w4_12_display_contract.py`: 111 nodes. All pass in each of unset / margin ON / caption ON, with `[netguard] blocked 0` each time. The file is pure ASCII: 0 non-ASCII bytes, measured. The fullwidth plus and the trademark sign are written as Python unicode escapes (U+FF0B, U+2122) (R18).
- Red phase: 34 RED and 32 PIN. At base the file was 34 failed / 32 passed.
- Fix round 1: 14 PIN/KILL nodes (R8 x4, R9 x2, R10 x3, R11 x5).
- Fix round 2: 13 PIN/KILL nodes:
  - R13: plus token x1, Galaxy/fullwidth cases x6, synthetic collision x3, identical names x1;
  - R14: reversed Graco pair x2.
- Fix round 3: 6 nodes:
  - R16: collision-definition premise pin x1, Ninja/Philips shared-name rows x3;
  - R17: prose plus x1, leading whole-token boundary x1.
- Fix round 4: +5 nodes net (6 added, 1 replaced):
  - the R16 `_names_collide` premise pin is replaced by an R19 premise pin (WH pair token-identical; Ninja/Philips share only "air fryer");
  - R19 (a) x2 (both directions), (a2) x1 (loser display name plus a lone shared stem), (b) x1, (c) x1.
- Fix round 5: +7 nodes:
  - R21 x4 (the two identical-display-name pairs, both directions; two rows are red-first, two are PIN);
  - R22 (i) x1 (winner without a distinguishing form, loser-only caption -> DROPPED);
  - R22 (ii) x2 (loser without a distinguishing form, a winner-only caption and a caption naming neither -> KEPT).
  - R22 (iii), both sides empty, stays pinned by the WH rows.

**Mutation tables.** Every restore was sha256-verified.
- Green table: 46 rows (9 HEAD + 34 prototype + 3 R5), 46/46 killed on the green bytes. Re-run on the final bytes: 44/44 runnable rows killed. 2 green-era guard anchors no longer exist and are covered by their re-anchored twins (m13r, m14r).
- Fix round 1: 13/13 killed on its bytes.
- Fix round 2: 10/10 killed on its bytes.
- Fix round 3: 23/23 killed on its bytes.
- Fix round 4: 28 rows, 27 killed, 1 equivalent survivor, on its bytes.
- Fix round 5, on the final bytes, each row against the 13-file CI-order set in one process: 38 rows, 36 killed, 2 equivalent survivors. The 38 are:
  - the new R21 rows;
  - the three R22 predicate mutants (run verbatim from the round-4 adversary's harness);
  - the R19 rows (re-anchored where R21 moved the two call lines);
  - the round-3 rows, the fix-round-2 rows and the kept fix-round-1 rows.
  - The five superseded fix-round-1 guard rows (R11a/R11b/m12r/m13r/m14r of round 1) were NOT re-run; their round-2 re-anchored twins were.

What each mutant turns red:
- **R21 red-first.** The whole-file swap to the fix-round-4 `home_routes` (shared forms left out of the masking pass) turns the two identical-display-name rows red. So do the surgical mutants (the shared forms masked by no one, or not passed on the token path).
- **R22.**
  - `if loser_only and winner_only:` turns all three R22 rows red.
  - `if loser_only:` turns both R22 (ii) rows red.
  - `if winner_only:` turns the R22 (i) row red.
- **R19 rows.** Each of these turns its row(s) red:
  - shared forms credited to the winner: the (a2) row;
  - shared forms credited to the loser only: the (b) row, the identical-names row and the R21 rows;
  - punctuation-only forms counted in the fallback: the (c) row;
  - the broad trigger: the 3 Philips rows, (a), (a2) and the R22 rows;
  - dropping the punctuation-kept fallback: both WH-1000XM5 loser rows.
- **Plus signs and boundaries.** Mapping every "+" to "plus" turns the iPad row red. Removing the lookbehind (A2) turns the Repair row red. Removing the lookahead turns the Airy row red.
- **Equivalent survivors.**
  - The fix-round-2 "shared form credited to the loser only" row inside `_names_only_in` (R11b) survives. Callers pass disjoint distinguishing sets, so no form reaches that function from both sides.
  - Dropping the shared raw forms from the fallback's masking pass survives. In the fallback every token form is shared; a probe over 48 x 48 = 2,304 ordered product pairs, of which 400 are token-identical (352 excluding self-pairs), found no input where it changes the result; the round-5 adversary's own in-memory probe (64,676 guard calls, 1,072 on the raw path) found 0 differences.
- **Dropping the "+" -> "plus" mapping** turns 5 nodes red. Ruled Galaxy cases 3 and 4 stay green under that mutant, because the safety net still drops them. This deviation from R13's predicted red set was accepted by R16.

**Gate 3 payload equality** (128 records):
- base == base2: 128/128 identical.
- head vs base: 48 records differ, only at the enumerated deltas as amended by R2. `verdict_scrubbed` appears on exactly the 17 emptied corpus rows and on none of the leaky SSE complete frames.
- Margin ON adds margin fields only (39 records). Caption ON adds `verdict_short` on 19 of 22 eligible rows only.
- The fix-round-5 dumps are byte-identical to the accepted dumps (base 929d87b8, head 4e2fd8b2, margin 37270990, caption 7e16c477). The delta listings are byte-identical record by record.
- The corpus has none of these pairs: a shared-stem cross-brand pair, a prose-plus pair, a punctuation-variant pair, or an identical-display-name pair.

**Comm gate** (CI selector + deselects, --timeout=60, guarded):
- base: 207 test files, 5441 passed / 0 failed.
- head (fix round 4, 9 chunks of at most 25 files): 208 test files, 5548 passed / 0 failed.
- `comm -13` is empty.
- It was not re-run for fix round 5, which changes only `home_routes.py` and the unit file.

**CI-order set** (13 files, one process per state, including `test_prescoring_showable_guard.py` per K1): 496 passed / 0 failed in each of the three states.

**Preserve** (71 files, unset): 1361 passed, 0 failed.

**Lint and diff:**
- ruff E9,F63,F7,F82 and py_compile are clean.
- `git diff --stat -- app/` touches only response_builder.py, structured_comparison_service.py, home_routes.py and profile_routes.py (311+/33-).
- There is no whole-file diff, and all four files are 100% CRLF.
- The F401 `HTTPException` in home_routes is pre-existing.

**Harness notes:**
- Every run used `-p qaren_netguard`, because the hermeticity unit has not merged.
- The corpus harness is irrelevant: no price module moves.

### Stated limits
1. The corpus is 27 rows from before 2026-06-22. Today's scrub rate is unknown until the WARNING runs in production.
2. The alias leak and the praise leak have ZERO recorded instances (0/46, 0/8). This change is defence for a persisted, publicly shared body.
3. "No SSE consumer" is proven for the phones only.
4. `search_logs` product-name strings (`text_routes`) still use the raw concat. They are analytics only.
5. **Caption-flag residual.** A pre-#99 stored reason can praise the loser by pronoun, and the loser guard checks names only. 1 of 26 rows uses the reason source.
6. The other two builder call sites in scs (the sync path and the early partial) read the margin env themselves. They emit no verdict frame, so no split between frame and payload is possible there.
7. Stored rows are not rewritten. The 17 leaking stored `overview.winner.reason` values stay in `full_response`.
8. **Loser guard is deliberately conservative.** R21 masks SHARED forms before shorter forms and credits them to no one, so a caption that names a shared form TOGETHER with a loser-distinguishing form is DROPPED where round 4 kept it (e.g. winner Philips 'Air Fryer' / loser Sony 'Philips Air Fryer' with the caption 'Philips Air Fryer beats the Sony Philips Air Fryer'; the doubled-brand shape winner Tom Ford 'Soleil Neige' / loser 'Tom Ford Tom Ford Soleil Neige'): the round-5 adversary's synthetic probe of the final bytes against the round-4 bytes found 172 such (pair, caption) rows, all of the nested-name / doubled-brand shape. The drop is conservative (the reason_key copy renders instead) and never the #99 direction; a caption naming ONLY shared forms is still kept.
   - Evidence is DISTINGUISHING forms only (R19). A name form whose token form is also a token form of the other product counts for neither side: a bare stem two brands share, an identical model name, "Air Fryer" vs "Air-Fryer", or an identical display name split differently between brand and name.
   - Shared forms are MASKED and credit no one (R21). So a caption naming only a shared form is kept, whichever product it was written about. That includes two products that display the same name ("Philips Air Fryer XL" as brand "" or as brand "Philips"): a caption naming that display name is kept.
   - A caption that names the loser only through its brand beside the shared stem, non-contiguously ("Philips makes the quieter air fryer"), is kept too.
   - A caption that names the loser by its whole name, while mentioning the winner only non-contiguously, is dropped (the Sauvage case above).
   - Matching is whole-token on BOTH edges: "Air" matches neither inside "Airy" nor at the tail of "Repair".
   - A "+" becomes the token "plus" only when glued to the preceding letter or digit ("S25+", "S25" + U+FF0B). A free-standing " + " in prose stays punctuation, so "iPad + keyboard bundle wins" on the iPad tile is kept.
   - The punctuation-kept safety net runs only when NO distinguishing form remains on EITHER side (identical names, or names differing only by punctuation such as "WH-1000XM5" vs "WH 1000XM5"). When only one side lacks a distinguishing form, the token path decides. In the safety net, a caption that writes the colliding name with punctuation different from both products (e.g. "WH/1000XM5") matches neither form and is kept.
   - Two products whose names are identical in every form cannot be told apart, so a caption naming that name is kept. A name made only of punctuation is never evidence, so the guard is off for it.
9. When the winner's display name trips `strip_score_internals` (e.g. "Graco 4Ever 5-Point Harness Seat"), the qualitative fallback that names it is scrubbed too. The shipped reason is still that fallback, the same as at base, and it is not counted (R8/R14). The false positive itself is W4-12g.

### Follow-ups (one issue, six rows, file after merge: F3 + R8)
- **W4-12b: honest tie SCORES.** First ship an OTA in which the client reads `scoring_v2.overall_score.winner_idx` first (ResultsScreen.tsx:765-771). Then the backend drops the nudge or ships `tie: true` behind its own flag. This also closes the owned margin/score inconsistency above.
- **W4-12c: `priority_match` is dead.** Dict-shaped dimension winners are compared to a string at home_routes:456, and the branch is reached on 0 of 22 rows. Revive it against both spellings behind its own flag, and rewrite `tests/test_home_routes.py:302-341/:375-429` to the production shape.
- **W4-12d: `price_tiers` keys still use the raw doubled spelling** (scoring_service.py:1544). Dedup them together with both readers (response_builder `value_match` / tier readers). They are unrendered.
- **W4-12e: stale YouTube signal.** A stale `youtube_review_signal` ships on the BC alias while `ENABLE_YOUTUBE_SOURCE` is OFF.
- **W4-12f: camera doubled brand.** The camera path's `"Identified: {brand} {name}"` doubles the brand (image_routes.py:376).
- **W4-12g: strip false positive.** `strip_score_internals` fires on product names that look like score fragments ("5-Point Harness", `\d+-point`). It empties a sentence that merely names such a product, including our own fallback. This is pre-existing at base and outside this unit (`text_sanitize.py` is untouched).
- **Mobile lane:**
  - Retune the CTA thresholds to the calibrated scale (>= 8 strong / < 4 close agrees with the raw rule on 22 of 23 rows).
  - Derive `presentationWinnerIndex` from `winner_idx`.
  - Fall the share text back to `factual_verdict.line1` when `metadata.verdict_scrubbed` is set.

### Product calls for DECISIONS_AHMED (F5)
1. Should we keep paying gpt-4o (priority=high) for a verdict sentence that FactualVerdict out-renders on 23 of 23 fresh payloads, so that Results cannot show it?
2. Should we backfill the 17 stored score-leaking `overview.winner.reason` values that the unauthenticated `GET /share/{token}` serves verbatim? This is a migration decision.

### CLAUDE.md corrections for the docs PR
- Add a SESSION 68 flags block with the two rows above: effect ON (including the caption order: tautology guard -> truncation -> loser guard), OFF identity, canary line, and the margin-flag intra-payload fact.
- Add an Active-runtime entry under "what changed for callers with every flag OFF", listing the five unflagged changes. For the loser guard, include:
  - distinguishing-forms-only evidence (R19);
  - shared forms masked and crediting no one (R21);
  - whole-token matching on both edges;
  - the glued-"+" token;
  - the punctuation-kept safety net when no distinguishing form remains on either side.
- Record `[VERDICT_SCRUB]` as a canary log line: one line per request when a scrub is counted, and our own fallback or deterministic text for the reconciled winner never counted. State that its published rate excludes honest partials.

### Rebase note
This unit shares `response_builder.py` and `structured_comparison_service.py` with **W4-7** (not started). Whichever lands second rebases, then re-runs the union of both units' CI-order sets in one process per flag state.

Issues: PO-VERDICT-TRUTH-03/-04/-06/-07/-08/-09/-14 (docs/investigations/2026-09-06-full-review-verified.json).

🤖 Generated with [Claude Code](https://claude.com/claude-code)

🤖 Generated with [Claude Code](https://claude.com/claude-code)
