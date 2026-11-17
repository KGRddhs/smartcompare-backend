# INC-M1a ADVERSARY (correctness, flag-mix and engineering checks folded in) - Claude Opus 5.5, 2026-11-17 14:18 AST

Unit: INC-M1a RESOLVER FOLD. Worktree C:/Users/SynAckITPC/Documents/AI/sc-inc-m1a, branch fix/inc-m1a-resolver-fold.
HEAD verified 06deda559bc1bdebf249edf3b23c072e5b37956b at start and end (one commit on 9bc13109).
RED file tests/test_inc_m1a_resolver_fold.py sha256 63fc6a67... at start and end; the committed blob has the same sha (index LF, no CR, 0 bytes > 127).
Scratch worktree <SP>/INC-M1a_adv_correctness (detached at 06deda55) was sha-verified after every mutant and removed at the end. The unit worktree was never edited.

## VERDICT: NOT_READY (1 blocking, 1 major)

### B1 (BLOCKING): the D5 one-character rule also tightens the INC-R1 model-arm guard, outside the spec
- The change: `_token_distance` now matches a one-character token only exactly. This was GREEN deviation 1, not in the spec.
- Where it reaches: `_token_distance` is shared by `_best_window`, which the model-arm guard (d) `_line_within_typed` also calls.
- What breaks: a one-letter token in a MODEL-answered line no longer fuzzy-matches the typed word.
  - Measured with `accept_model_side` and a high-confidence fragrance answer (probe_accept.txt):

    | typed | model line | base | HEAD |
    |---|---|---|---|
    | "Chanel No 5" | "N(deg)5" | llm/high (Chanel, N(deg)5) | refused (source none, medium) |
    | "Chanel No 5 Eau de Parfum" | "N(deg)5" | llm/high, EDP | refused |
    | "Hermes Terre de Hermes" | "Terre d'Hermes" | llm/high | refused |
    | "Dior Bois de Argent" | "Bois d'Argent" | llm/high | refused |

  - The model line's normalised tokens are n/5, terre/d/hermes, bois/d/argent.
  - The guard probe (probe_guard.txt) also flips "Prada Le Homme" / "L'Homme", "Issey Miyake L Eau De Issey" / "L'Eau d'Issey" and "Chanel No 5 L'Eau" / "N(deg)5 L'Eau" from True to False.
- Consequence: under ENABLE_PRODUCT_RESOLVER ON + ENABLE_ANTHROPIC_TEXT ON + consent 3, with PRODUCT_RESOLVER_ASK at its default ON:
  - the side is unresolved and the model answer is usable and fragrance-intended;
  - so `_outcome` returns OUTCOME_ASK;
  - the user gets the 400 "We need clearer names" refusal for Chanel No 5 where base gave a comparison.
- This is a regression of INC-R1 behaviour that PIN-1 / spec 1.3 do not allow (only the listed rows change on purpose). No row pins the base behaviour, so all 294 rows pass.
- Fix (suggested): keep the one-character exact rule in the lexicon arm's D5 line search only, for example a keyword on `_best_window` passed from `_lexicon_side`. Leave `_line_within_typed` on the base rule. Pin both sides in rows (see M1).

### M1 (MAJOR): the one-character fix for M1R-11 (d) is unpinned (mutant X1 survives)
- Mutant X1 reverts `if alias_token.isdigit() or len(alias_token) == 1:` to the base `if alias_token.isdigit():`. Result: unit file + test_inc_r1_resolver.py 294 passed (X1 SURVIVED).
- With X1 applied (probe_x1.txt), each of these resolves HIGH to (Yves Saint Laurent, Y, EDT): "YSL L'Homme", "Yves Saint Laurent L'Homme", "YSL B", "YSL by", "YSL X", "YSL 1", "YSL Ya", "YSL Yo".
  - That is a wrong product, the exact M1R-11 (d) false high the gate calls a fix round.
- The GREEN bytes fix it, but nothing stops a later edit from silently undoing it.
- The frozen RED file cannot take the row, and M1R-8 limits the E-rows. The orchestrator rules where the pin goes, for example a new tests/test_inc_m1a_gate_rows.py:
  - rows that the short-token set stays medium;
  - rows that the B1 model-arm cases are accepted.

## Gates run by this adversary (exact bytes; one pytest at a time; PYT_VIA_GATE=1, box by BOX_GO)
- Unit ON and OFF: tests/test_inc_m1a_resolver_fold.py + tests/test_inc_r1_resolver.py, with ENABLE_PRODUCT_RESOLVER exported true / false. 294 passed each.
  - [pyt] tag=m1a-advc-unit-on start=2026-11-17 13:51:28 end=2026-11-17 13:51:41 elapsed=13s bound=600s status=OK rc=0 log=...\INC-M1a_adv\unit_on.log
  - [pyt] tag=m1a-advc-unit-off start=2026-11-17 13:52:08 end=2026-11-17 13:52:19 elapsed=11s bound=600s status=OK rc=0 log=...\INC-M1a_adv\unit_off.log
- CI-order set: the whole GREEN comm list (156) + the unit file, in ONE alphabetical process.
  - Summary: 13 failed, 11551 passed, 42 skipped, 15 deselected, 37 xfailed, 2 errors in 481.50s.
  - 15 failing ids, every one in the base list (INC-M1a/comm/base_failed_ids.txt, 16 ids). Branch-only-NEW: EMPTY. Same 15 as GREEN.
  - [pyt] tag=m1a-advc-ciorder start=2026-11-17 14:01:48 end=2026-11-17 14:09:54 elapsed=486s bound=1200s status=FAIL rc=1 log=...\INC-M1a_adv\ciorder.log
- Hook test files (excluded from the GREEN comm set and tree run): tests/test_precommit_hook{,_phase_b,_phase_b_round2,_round2}.py. 324 passed, 3 skipped.
  - [pyt] tag=m1a-advc-hooks start=2026-11-17 14:10:07 end=2026-11-17 14:15:21 elapsed=314s bound=1200s status=OK rc=0 log=...\INC-M1a_adv\hooks.log
- Collect-only of the RED file: 128 ids. The per-test counts equal the PR body's (ar5 9, seed1 17, pin0 identity 8, link key 13, pin1 25 / 6, seed2 5 + 2).
  - [pyt] tag=m1a-advc-collect start=2026-11-17 14:16:49 end=2026-11-17 14:16:52 elapsed=4s bound=600s status=OK rc=0 log=...\INC-M1a_adv\collect.log
- Mutants: 22 runs; per-run [pyt] lines are in mut_<id>.log and mutation_results.json. Every one ran at bound 600 s for about 11 s.
- ruff E9,F63,F7,F82 clean on the three .py files. The default ruff set flags 2 findings in test_inc_r1_resolver.py (SIM905 :527, B009 :1446); both are present at base. py_compile is clean.
- The lines file loads 14 lines.
- Blobs: LF, no CR. 0 bytes > 127 in product_resolver.py, fragrance_lines.json, test_inc_r1_resolver.py and the RED file. CLAUDE.md has 3904 non-ASCII bytes at base and at HEAD (the new row is ASCII).

## Mutation table (GREEN bytes, byte copies, restored and sha-verified: resolver 88c3276b..., data 24ad79b5...)
| id | mutant | result |
|---|---|---|
| MA1 | drop the Arabic Sauvage line alias | KILLED 34 failed |
| MA2 | drop the YA Bleu de Chanel alias | KILLED 2 failed (the data rows, M1R-3) |
| MA3 | Arabic phrases WAW particle only | KILLED 4 |
| MA4 | every Arabic phrase -> EDT | KILLED 7 |
| MA5 | no generic-word flanker (`flanker = None`) | KILLED 2 |
| MA6 | validator bool check removed | KILLED 5 |
| MA7 | Arabic Dior alias as raw UTF-8 | KILLED 188 |
| MA8 | apply_resolution keeps the typed search_query | KILLED 22 |
| MA9 | Libre concentrations [EDP] | KILLED 2 |
| MA10 | the D2 strip ignores the Arabic phrases | KILLED 9 |
| MA11 | typed concentration ignores the Arabic phrases | KILLED 7 |
| MA12 | single_concentration also on Sauvage | KILLED 1 |
| MA13 | drop the Arabic Chanel house alias | KILLED 2 |
| X1 | one-character exact rule reverted | SURVIVED (M1) |
| X2 | `_phrases_for` without the `_has_arabic` guard | SURVIVED (equivalent: Arabic phrases never match Latin tokens; load_lexicon is already read by `_index`) |
| X3 | drop the Arabic Rasasi house alias | KILLED 1 |
| X4 | single_concentration dropped from Layton | KILLED 1 |
| X5 | Arabic phrases sorted shortest first | KILLED 6 |
| X6 | Y base EDP | KILLED 2 |
| X7 | Aventus flanker Cologne dropped | KILLED 4 |
| X8 | `_generic_flanker` does not mark positions used | SURVIVED (inert on the seed: Cologne has no core position) |
| X9 | `_generic_flanker` without the generic-word filter | SURVIVED (equivalent on the seed: D7 already matched the non-generic flankers) |

## Runtime truth of the claims (probes on the HEAD bytes: probe1_head.txt, probe_link.txt)

### Spec 1.2 behaviour: TRUE
- The Arabic pair resolves high/lexicon, with the WAW and the YA spellings.
- The Arabic EDP / EDT / Parfum phrases resolve, with the WAW and the YA particle.
- YSL Y, Rasasi Hawas, and the Cologne / for Her / Ice / Qahwa / Dukhan / Absolu / Intense flankers resolve to the line WITH the flanker.
- "YSL Libre EDT" resolves high EDT.
- "YSL Y Elixir" resolves to (YSL, Y, Elixir, flanker Elixir).
- "Libre Le Parfum" / "YSL Y Le Parfum" stay medium.
- An unseeded Arabic line stays medium.
- "Dior Sauvage Tester" is unchanged (high, the tester qualifier).

### Flag-OFF identity, contract freeze, error handler, R-A3: TRUE
- With ENABLE_PRODUCT_RESOLVER OFF the hook is skipped (PIN-0 green ON and OFF).
- The diff touches no exit, `is_ask_refusal`, `http_detail_extras`, error_handler, text_routes, billing / refund path or response key. R-A3 is untouched.
- Response shapes are unchanged: a candidates item is still {brand, line, concentration}, and flanker candidates already existed for Stronger With You.

### The link key (M1R-9): TRUE, and it moves with the PR flag OFF
- With ENABLE_PRODUCT_RESOLVER OFF, `_link_key` still calls resolve_lexicon and reads the lines file.
- Under ENABLE_URL_LINK_RESULT, the /url response's product.link_key, brand and variant move for:
  - "Yves Saint Laurent Y Eau de Parfum 100ml" -> resolved Y EDP;
  - Hawas;
  - Aventus Cologne.
- "YSL L'Homme" stays unresolved.
- M1R-9 rules this deliberate. Both flags are OFF on web (H13 (c); INC-U1 merged with its switch off).

### Flag mix ENABLE_PRODUCT_RESOLVER x ENABLE_ANTHROPIC_TEXT x consent 2/3 x ENABLE_URL_LINK_RESULT
- PR OFF: no change, except the link key under URL_LINK ON (M1R-9).
- PR ON, consent 2: seeded Arabic and flanker sides resolve in the lexicon arm (no call).
- PR ON, consent 3 + TEXT ON: the same sides make no call and spend nothing. BUT B1: model-answered lines with a one-letter token are now refused, and that becomes ASK.

### Other checks
- M1R-10: TRUE. CONCENTRATION_PHRASES / GENERIC_WORDS / QUALIFIER_WORDS are byte-identical, and the phrases are read via load_lexicon.
- M1R-11 (c): TRUE. No new public accessor.
- M1R-12: TRUE. Line endings are as checked out (index LF, worktree CRLF by autocrlf).

### Short-token probe, M1R-11 (d) (probe1_head.txt)
Every "YSL <letter>" and every bare letter stays medium/low, except:
- "y" / "Y" / "YSL y";
- "Y EDP" / "Y 100ml" / "Y EDT 100 ml" / "Y Elixir": these resolve to YSL Y high (minor m4).
- Two-letter tokens (Ya, Yo, Yy, by) stay medium/low.
- The Arabic conjunction waw before or after the seeded names stays medium.

## Comm set re-derived (union rule at HEAD)
- Method: git grep over tests/ for product_resolver / fragrance_lines / resolve_lexicon / _typed_concentration / link key / the two flags, the lexicon readers, the CLAUDE.md readers and the glob / walk / ls-files walkers. 102 files.
- Not in GREEN's 156:
  - the RED file (run as the unit);
  - the four pre-commit hook files (deliberately excluded; run here: green);
  - tests/test_sqlfluff_config.py (walks migrations/*.sql only: not a comm file; it also ran in GREEN's whole-tree process).
- No missing comm file.
- Client fences: NOT MEASURED by GREEN. No SmartCompareApp test reads product_resolver.py, fragrance_lines.json or CLAUDE.md content (git grep), so this stays a stated limit.

## Minors (documentation rulings for the orchestrator)
- m1: The CLAUDE.md row ("with that flag OFF nothing changes on any response") and the PR body ("the resolver is not called"; "reads no lines file") over-claim.
  - With ENABLE_URL_LINK_RESULT ON, `_link_key` resolves through the new data with ENABLE_PRODUCT_RESOLVER OFF.
  - Suggested wording: "with ENABLE_PRODUCT_RESOLVER OFF nothing changes, except the INC-U1 link key under ENABLE_URL_LINK_RESULT (M1R-9)".
- m2: The CLAUDE.md row says the one-character rule is for the line Y only. It omits the model-arm guard (moot once B1 is fixed).
- m3: The PR body line "Existing resolver suites ... 699 passed:" ends without its [pyt] line.
- m4: A bare typed "Y" / "Y EDP" / "Y 100ml" / "Y Elixir" resolves to YSL Y high with no house.
  - This is GREEN's open question 1, and it is consistent with the base exact single-token rule (Eros, Libre).
  - Owner / orchestrator ruling; stated in the row and the body.
- m5: A typed name with two flanker words keeps the first match and drops the generic one: "Creed Aventus Cologne for Her" -> Aventus for Her; "Creed Aventus Absolu Cologne" -> Aventus Absolu. An edge; state it or leave it.
- m6: The mixed-script page name "Dior" + Arabic Dior Sauvage leaves the duplicate Arabic house as a residual (link key unresolved). It is not in scope.

## Prove-nothing rows / inert code
- The `_has_arabic` guard of `_phrases_for` (X2). No row can observe it: Arabic phrases never match Latin tokens. The claim "a Latin name reads exactly the base table and no lexicon" is not pinned.
- `_generic_flanker`'s used-position bookkeeping and its generic-word filter (X8, X9) are inert on the seeded data.
- The PIN rows pass at base by design (pins, not proofs).

Report files (all under <SP>/INC-M1a_adv/):
- logs: unit_on.log, unit_off.log, ciorder.log, ciorder_ids.txt, hooks.log, collect.log, mut_*.log;
- mutation data and scripts: mutation_results.json, mutants.py;
- probes: probe1.py / probe1_head.txt, probe_x1.py / probe_x1.txt, probe_guard.py / probe_guard.txt, probe_accept.py / probe_accept.txt, probe_link.py / probe_link.txt;
- comm-set re-derivation: rederived_raw.txt, missing_from_green.txt.
