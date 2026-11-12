# G-INC-1 RESULT-TRUTH: INC-X9 + INC-X10 + INC-X8 + INC-X2a (incident fix lane, one SAFE group)

Four units from the 2026-11-11 production data-quality incident (MYEZ), built as one LC-9 SAFE group on one branch. Built on `a74caba7` (GREEN `a92b0ba3` + fix round 1 `dcdbf530`, reviewed SOUND), then REPLAYED in the final round onto origin/main `ea47cbfbe67d19da49b078169a5c4cf854555e68` (the merge of PR #378 LEGAL-V3, after PR #399 S81-04c): HEAD `b5e8624c8e4ff6c431cf3b80e727a9633d2ff744` (two commits). The replay conflicted in CLAUDE.md only; no application or test byte changed (the `app/` + `tests/` patch-id of the unit is identical before and after the replay). Every unit below is **merged, NOT yet proven** until the owner's phone shows it (the owner's proof standard: suites and gates are necessary, never the proof).

| Unit | Root cause | Flag | Deploy-visible at the merge |
|---|---|---|---|
| INC-X9 COHORT-LINE-RETIRE | 9 (false "+53 shoppers" line) | none (unflagged bug fix, owner ruling O1) | yes: new results carry no `cohort_summary` |
| INC-X10 LISTING-MATCH-GUARD | 4 (Versace women's listing priced the men's Eros) | `ENABLE_LISTING_MATCH_GUARD` (default OFF, read per call) | none |
| INC-X8 PHASE2-CACHED-RATING | 6 (residual guard dropped a rating already in memory) | `ENABLE_PHASE2_CACHED_RATING` (default OFF, read per call) | none |
| INC-X2a IMAGE-TIER-TIMING | 5 (unknown image tier in flight at the 5 s race) | none (log-only, R-A1) | yes: new INFO lines `[IMG_TIER] ...` |

## What the flags do

- `ENABLE_LISTING_MATCH_GUARD` (INC-X10): for fragrances only, a price listing whose title states exactly one gender other than the default side of a known gender-flip line is rejected when the query names that line and states no gender. Flag OFF: the predicate returns False after one env read, before reading any descriptor field or the table (pinned with the full configuration and a recording table).
- `ENABLE_PHASE2_CACHED_RATING` (INC-X8): when `ENABLE_PHASE2_RESIDUAL_GUARD` skips Phase 2 for a product (and it is no KB full hit), the product gets the rating its in-memory shopping rows already hold, through the same function and the same acceptance rule as the free tier of `get_verified_rating`. No network, no LLM, no await. Flag OFF: the block is skipped (the flag is the first conjunct).

## INC-X9 COHORT-LINE-RETIRE (unflagged)

- Change: `StructuredComparisonService._build_cohort_summary` keeps its signature and its three call sites; its body is a docstring stating the retirement and `return None` (R-G1-6: the unreachable gate body and `_COHORT_GOV_SKIP`, which had no other reader, are deleted). The builder keeps accepting a dict or None; `metadata.cohort_injected`, `ENABLE_COHORT_PERSONALIZATION` and the verdict-prompt cohort block are unchanged.
- Deploy-visible delta, exact: (1) new text / streaming / camera / partial responses lack root `cohort_summary` where base sent it; (2) comparisons saved after the deploy lack it in `full_response`; (3) the store binary (JS 683f56c0) shows no cohort box on those results: its absent path is its own existing path (ResultsScreen.tsx:988-1006 returns 0 / '' and CohortBadge.tsx:62 returns null), the empty slot keeps its margin as for an unmatched user today; (4) nothing else: every other key and value of a full response is identical (P9-2 scored shape, P9-3 legacy shape). The OTA bundle never read the block.
- Stated limits: rows saved before the deploy keep the block, so the store binary still shows the line when an OLD result is re-opened from History; removing it from old rows is an optional owner data step, not part of this unit. The empty slot View keeps its bottom margin.
- PROOF ON THE PHONE (no AI text needed): repeat any golden pair on the STORE binary (not the update), from the owner's account (its demographics produce a matched cohort). Visible: no "+53 shoppers in Northern ..." box under the verdict. Backing: the new `comparisons.full_response` row has no `cohort_summary` key; before = rows 441e7b7d, 5b369372, e2320ca7 (peer_count 53, governorate Northern).

## INC-X10 LISTING-MATCH-GUARD (dark)

- Change (app/services/price_service.py): the table `_GENDER_FLIP_LINES`, `listing_match_guard_enabled()`, `_vd_gender_line_flip(q, c)`; hook H1 in `_descriptor_axis_mismatch` (every adapter selection gate, `select_best`, `should_cache_price`) and hook H2 in `_descriptor_backstop_axes_verdict` (cache read `_cache_price_identity_ok`, display `is_price_showable`), reason word `gender`. No new key, no new log line; a rejected listing leaves the product on its existing paths (another candidate, the cascade, or no confirmed price).
- The four table lines, in plain words (the owner may veto any one; a new line later is a data-only follow-up with its rows):
  1. Versace Eros: the plain name means the men's perfume; a listing saying "for Women" / "Pour Femme" / "Her" is the different women's perfume and is rejected.
  2. Versace Dylan Blue: the plain name means the men's; a women's ("Pour Femme") listing is rejected.
  3. Creed Aventus: the plain name means the men's; an "Aventus for Her" listing is rejected (unless the query itself says "for Her").
  4. Dolce & Gabbana Light Blue: the plain name means the women's; a "Pour Homme" (men's) listing is rejected.
  The rule is inert when the query states any gender word, when the listing states no side or both sides, and outside the fragrance category.
- Measured before / after (hermetic, R10-6, a fixture built from the incident title on one synthetic host so authority ties): before = the 25.0 "Versace Eros for Women EDP 100ml" listing wins (cheapest on the tie); after (flag ON) = the 28.0 unmarked "Versace Eros EDP 100ml" listing. A hermetic measurement is not the production proof: the titles of the other two hits of 2026-11-11 were never logged, so production may land on "no confirmed price" instead.
- Stated limits: four lines only (any other line, or a query without the brand words, keeps today's behaviour); a gendered query is left to the base axes; the default sides are product knowledge, not measured in the repo; saved rows and L2 prices are not rewritten (the cache read drops a poisoned L1 entry); whether the woo adapter infers category fragrances for the query is not measured; the guard fails OPEN for a title whose gender words are not in the Latin token sets (an Arabic-only title keeps today's behaviour); it rejects a listing of the right product whose only gender word is a pronoun in marketing text of the other side (for example "gift for her" on a men's Eros listing). The base selection gate already rejects a title whose only gender word is a lone pronoun; the guard's own new rejection of that case happens at the cache read and at display.
- PROOF ON THE PHONE (after its flip window; no AI text needed): repeat Armani Acqua di Gio Profumo vs Versace Eros EDP. Visible: the Versace price comes from a men's (or unmarked) Eros EDP listing, or Versace shows no confirmed price. Backing: `products[1].price.title` of the new row names no women's / Pour Femme marker; the deploy log may show the existing `[PRICE] cache_read_rejected (not_exact:gender)` line if the 7-day cached entry was still live.

## INC-X8 PHASE2-CACHED-RATING (dark)

- Change (app/services/structured_comparison_service.py): `_phase2_cached_rating_enabled()`, `_phase2_cached_rating(full_name, cache)` and one block between the Phase-2 result loop and the four rating writes, logging `[L2.6] phase 2 cached rating outcome=<hit|miss|error:T> product=<n>` once per skipped product. Same result keys and the same `rating_source` marker as a normal tier-0 hit (P8-5); the smart-fallback refill stays skipped (P8-4); a KB full hit keeps the card rating (P8-6).
- Measured before / after (hermetic, R8-1): before = with the skip, rating None; after (flag ON) = 4.6 / 1200 verified, `extract_method` google_shopping, the `_get_verified_rating` recorder at 0 calls. A hermetic measurement is not the production proof: the effect exists only if those products' shopping rows carry a tier-1 / tier-2 / consensus rating, and the 2026-11-11 rows were not saved.
- Stated limits: the US shopping tier (one Serper credit, network) stays skipped under the guard; the production effect is uncertain.
- PROOF ON THE PHONE (after its flip window; no AI text needed): repeat Creed Aventus EDP vs Parfums de Marly Layton EDP. Visible: Reviews shows a star average with a count for both. Backing: the new row has `rating_source` and `review_count` filled for both; the deploy log shows `[L2.6] phase 2 cached rating outcome=hit` for any product whose Phase 2 was skipped (no `phase 2 skipped` line = Phase 2 ran normally and this unit did nothing for that product).

## INC-X2a IMAGE-TIER-TIMING (log-only)

- Change (app/services/image_service.py): `import asyncio`, `import time`, `_log_img_tier`, per-tier bookkeeping inside `get_product_image_url` and one `except asyncio.CancelledError` arm with no await that re-raises with a bare `raise`. The same calls in the same order, the same returns, the same exceptions, the same existing `[image]` lines (P2-1..P2-7). No product name, URL or query text in a line. At most 10 lines per comparison (5 per product; 0 when a KB image is served).
- Read-back for the relay (filter the deploy log after three phone comparisons): `[IMG_TIER] tier=` and `[IMG_TIER] cancelled tier=`, together with `[L2.6] Phase 1 race timeout for image_url`, plus each row's `stage_timings_ms.image_url_ms`. `total_ms - 5000` on a cancelled line is the late-cancellation gap (it includes the unwind of the awaited call).
- Lead for INC-X2 (not changed here): the Serper image credit gate `try_consume_serper_image_credit` is a synchronous Redis call on the event loop; a slow gate cannot be interrupted, so a cancel lands at the next await (a long `serper_budget` ms exposes it).
- Stated limits: piggyback is always `skipped` on the race path (scs passes None); delivery vs unwind cannot be split without a line inside serper_service.
- PROOF: none on the phone (a measurement); acceptance = the lines appear for three production comparisons, read by the relay.

## Defect ids -> RED nodes (all in the four frozen RED files)

| Id | RED / PIN nodes |
|---|---|
| INC-X9 | tests/test_inc_x9_cohort_line_retire.py: test_r9_1, test_r9_2, test_r9_3 (partial), test_r9_4 [text, stream, camera]; PIN test_p9_1..test_p9_5 |
| INC-X10 | tests/test_inc_x10_listing_match_guard.py: test_r10_1..test_r10_10, test_p10_3; PIN test_p10_1 (keep rows), test_p10_2 (flag-OFF identity, full config), test_p10_4, test_p10_5, test_p10_6 |
| INC-X8 | tests/test_inc_x8_phase2_cached_rating.py: test_r8_1 [true, padTRUE], test_r8_3, test_r8_4, test_r8_5, test_p8_5; PIN test_p8_0..test_p8_4, test_p8_6 (KB full hit) |
| INC-X2a | tests/test_inc_x2a_image_tier_timing.py: test_r2_1..test_r2_7; PIN test_p2_1..test_p2_7 |

| Gate rows (fix round 1) | tests/test_inc_g1_gate_rows.py: test_gr1 [makeup, skincare, haircare] (the guard is fragrance-scoped; kills A10-beautywide), test_gr2 (the llm_pick line says error:<class>; kills A2-llmerr) |

RED gate: 40 failed at base (AssertionError only), 44 PIN green; 25 mutants applied, none survived; 1 not applicable after R-G1-6 (the mutation table is filed in the session's specs folder). Fix round 1: the adversary's two surviving mutants (A10-beautywide, A2-llmerr) are KILLED by the gate rows, each on an AssertionError.

## Deliberate pin changes (spec 4.1)

| E | Test | Base assertion | New assertion |
|---|---|---|---|
| E9-1 | tests/test_cohort_summary_orchestrator.py::test_resolved_cohort_returns_none_since_inc_x9 (was test_returns_peer_count_and_governorate_when_resolved) | `out == {"peer_count": 19, "governorate": "Capital"}` | `out is None` (same profile) |
| E9-2 | ...::test_cohort_match_n_never_surfaces_since_inc_x9 (was test_peer_count_sourced_from_cohort_match_n) | `out["peer_count"] == 27` | `out is None` |
| E9-3 | ...::test_broadened_governorate_quality_returns_none_since_inc_x9 (was test_broadened_governorate_quality_still_emits) | `out is not None` + governorate | `out is None` |

No other existing test changes. No fixture, golden or client fence pins the block. The three E-rows were renamed in fix round 1 (F1-4) to say what they assert; their bodies are unchanged. Stated limit: the other rows of that file (the `returns_none` rows and test_flag_off_returns_none, test_non_int_n_does_not_crash) keep their names but no longer test a gate, because the helper now returns None for every input; a later cleanup may delete them.

Ruled pin-fix of a frozen RED file (fix round 1, F1-1): tests/test_inc_x10_listing_match_guard.py's autouse environment fixture now also deletes `WARMER_CONTEXT` (one added line plus a comment and a docstring clause; no assertion changed, no row removed), so every row states its whole environment.

## Gates

GREEN round. (The GREEN runner printed each [pyt] status line to its stdout, not to the log; each line below is rebuilt field for field from that run's record in the runner ledger harness/pyt_ledger.jsonl, in the runner's own format.)

- RED files, both flags ON: `[pyt] tag=inc-g1-green-on start=2026-11-11 22:36:19 end=2026-11-11 22:36:24 elapsed=5s bound=600s status=OK rc=0` (84 passed, 11 warnings in 4.52s).
- RED files, both flags unset: `[pyt] tag=inc-g1-green-off start=2026-11-11 22:36:33 end=2026-11-11 22:36:38 elapsed=5s bound=600s status=OK rc=0` (84 passed, 11 warnings in 4.35s); the flag-OFF identity rows alone: `[pyt] tag=inc-g1-green-offrows start=2026-11-11 22:36:40 end=2026-11-11 22:36:43 elapsed=4s bound=600s status=OK rc=0` (15 passed, 44 deselected, 11 warnings in 2.77s).
- Identity pins of spec 4.2 (the four units' base-pass sets, 23 files): `[pyt] tag=inc-g1-green-pins start=2026-11-11 22:36:53 end=2026-11-11 22:37:28 elapsed=35s bound=1200s status=OK rc=0` (649 passed, 1 deselected, 11 warnings in 33.80s; the one netguard node is pre-existing and green).
- CI-order set (spec 12.2, 22 files): `[pyt] tag=inc-g1-ciorder start=2026-11-11 23:01:32 end=2026-11-11 23:02:44 elapsed=72s bound=1200s status=OK rc=0` (706 passed, 16 warnings in 70.78s (0:01:10)).
- Comm set at HEAD: 736 files (the RED round's union list, re-derived, nothing new), 30 chunks of <= 25 (bound 1200), all `status=OK` or `FAIL` on the base-known nodes only. HEAD failures 32 ids; base record = the whole-tree record at a74caba7 (`harness/base_records/a74caba7.../23f5330f...`, 28 ids), reused per file (GC-7).
- branch-only-NEW = 5 ids, all `tests/test_inc_x10_listing_match_guard.py::test_p10_2_flag_off_identity_full_config[*]`: an ORDER DEPENDENCE of the frozen RED row, present at BASE too, NOT a regression: `tests/test_identity_stamps_wave_b.py` imports `scripts/measure_warmed_kpi.py`, which sets `WARMER_CONTEXT=1` at import and is not restored, so the warmer write veto makes `should_cache_price` refuse the women's listing and P10-2's base-value assertion fails. Measured at base a74caba7 in a scratch worktree with the same RED file: `[pyt] tag=inc-g1-p102-base-order start=2026-11-11 23:00:56 end=2026-11-11 23:01:01 elapsed=5s bound=600s status=FAIL rc=1`; at HEAD: `[pyt] tag=inc-g1-p102-head-order start=2026-11-11 23:01:03 end=2026-11-11 23:01:07 elapsed=4s bound=600s status=FAIL rc=1`; at base with WARMER_CONTEXT=1 alone: `[pyt] tag=inc-g1-p102-base-warm start=2026-11-11 23:01:08 end=2026-11-11 23:01:13 elapsed=4s bound=600s status=FAIL rc=1`. CI collects every module in one process, so CI would have shown this red. CLOSED in fix round 1 by the ruled pin-fix F1-1 (below).
- Client fences (15 suites by path through the live junction, jest 29.7.0): `[jest] tag=inc-g1-fences rc=1`: 246 passed, 4 failed = the four accepted `config/nativeBundle.w37` drift nodes (d5, k2, k4, k5).
- Lint: ruff E9,F63,F7,F82 clean on the four edited python files; the default ruff set reports the same counts at base and head (21 / 38 / 0 / 0); py_compile clean; the pre-commit hook passed.

Fix round 1 (rulings F1-1..F1-7; test and docs files only, no application file changed):
- Order reproduced at the GREEN head before the pin-fix (tests/test_identity_stamps_wave_b.py, then the X10 RED file): 5 failed = the five P10-2 nodes, 56 passed: `[pyt] tag=inc-g1-fix1-repro start=2026-11-11 23:25:38 end=2026-11-11 23:25:47 elapsed=9s bound=600s status=FAIL rc=1`
- The same order after the F1-1 pin-fix: 61 passed: `[pyt] tag=inc-g1-fix1-order-head start=2026-11-11 23:26:01 end=2026-11-11 23:26:05 elapsed=4s bound=600s status=OK rc=0`
- R10-10 at base a74caba7 (scratch worktree, the pin-fixed RED file, wave_b first, -k "r10_10 or p10_2"): R10-10 failed on an AssertionError (should_cache_price accepted the women's listing), the five P10-2 nodes passed; so R10-10 now proves the guard, not the leaked veto: `[pyt] tag=inc-g1-fix1-r1010-base start=2026-11-11 23:26:16 end=2026-11-11 23:26:22 elapsed=5s bound=600s status=FAIL rc=1`
- Gate rows at head: 4 passed: `[pyt] tag=inc-g1-fix1-gr-head start=2026-11-11 23:27:22 end=2026-11-11 23:27:26 elapsed=3s bound=600s status=OK rc=0`
- Mutant A10-beautywide (H1 scope widened to the four beauty categories), on a sha-verified byte copy in a scratch worktree: KILLED, GR1 3 failed on AssertionError: `[pyt] tag=inc-g1-fix1-mut-a10-beautywide start=2026-11-11 23:27:43 end=2026-11-11 23:27:48 elapsed=5s bound=600s status=FAIL rc=1`
- Mutant A2-llmerr (the llm_pick error outcome logged as miss): KILLED, GR2 failed on AssertionError: `[pyt] tag=inc-g1-fix1-mut-a2-llmerr start=2026-11-11 23:27:49 end=2026-11-11 23:27:53 elapsed=4s bound=600s status=FAIL rc=1`
- The four RED files + the gate rows, both flags ON: 88 passed: `[pyt] tag=inc-g1-fix1-on start=2026-11-11 23:28:09 end=2026-11-11 23:28:15 elapsed=5s bound=600s status=OK rc=0`
- The same, both flags unset: 88 passed: `[pyt] tag=inc-g1-fix1-off start=2026-11-11 23:28:16 end=2026-11-11 23:28:22 elapsed=6s bound=600s status=OK rc=0`
- CI-order set of spec 12.2 with tests/test_identity_stamps_wave_b.py first and the gate rows (24 files): 728 passed: `[pyt] tag=inc-g1-fix1-ciorder start=2026-11-11 23:28:32 end=2026-11-11 23:29:45 elapsed=74s bound=1200s status=OK rc=0`
- Comm chunk holding tests/test_cohort_summary_orchestrator.py (25 files): 1248 passed: `[pyt] tag=inc-g1-fix1-comm-03 start=2026-11-11 23:30:17 end=2026-11-11 23:31:08 elapsed=51s bound=1200s status=OK rc=0`
- Comm chunk holding wave_b, the four RED files and the gate rows (25 files): 353 passed, 1 skipped: `[pyt] tag=inc-g1-fix1-comm-09 start=2026-11-11 23:31:10 end=2026-11-11 23:31:24 elapsed=14s bound=1200s status=OK rc=0`
- The tests/ walkers (hermeticity pins, CI gates, scoring rubric truth) + the CLAUDE.md readers (behavior dimension translation, s81 spend breaker, s08b legacy fingerprint + gate rows, s23 bypass retire): 696 passed, 1 xfailed: `[pyt] tag=inc-g1-fix1-walkers start=2026-11-11 23:32:01 end=2026-11-11 23:33:02 elapsed=61s bound=1200s status=OK rc=0`
- Comm set: the head list gains tests/test_inc_g1_gate_rows.py (737 files); the two chunks above hold every changed test file; `comm -13` against the base record (28 ids) is EMPTY (0 failed ids at head in both chunks). Renamed nodes (new names for existing rows, green at head): the three E-rows of the table above.
- ruff E9,F63,F7,F82 and the default ruff set clean, py_compile clean on the three changed test files.
- Client fences: not re-run in fix round 1 (no application, script or client file changed); the GREEN fence run stands. The full jest suite is the final round's (LC-7).

## Final round: the replay onto ea47cbfb (rulings RB-G1F-1..7; one agent, no adversary, no re-verifier: LC-2)

- Replay: `git rebase origin/main` replayed GREEN and fix round 1 onto `ea47cbfb` (new shas `103f38d0`, `b5e8624c`). ONE conflict, CLAUDE.md, in the Feature Flags pointer clause (both sides inserted a sentence at the same anchor). Resolved as the UNION in merge order: the S81-04c sentence, the S81-12 LEGAL-V3 sentence, then this unit's sentence; no row or sentence of main dropped or reworded. The unit's block merged cleanly after the S81-12 LEGAL-V3 block, before `## Tests`; the second commit replayed without a conflict. `git diff --check` clean; no conflict marker in CLAUDE.md, app/ or tests/.
- Frozen files (sha256 of the git blob, identical before and after the replay): X9 `b2ef4d349021d3dca49016f34d576e707eddd92f74a77d04b872b330e1f69c5a`; X10 `8419549c2861055f93a33f8fcf66a1060bdf2ab1ace7b76a64a1281078f01a18` (the F1-1 pin-fix); X8 `8a2cc6d6dc9fcfbbdff10935240684abb100e84116ab9dab188917ce0673a861`; X2a `febb83de596fcb366ad59ff6a3957489bd3562a4ab6995275d4f0612884154eb`; gate rows `96858246713929bb04dbfaf91c08d367f806995b181979d15b86e721e6f16f5a`. No pin row is owed and no test file was edited in this round (RB-G1F-2), so no new mutant.
- The four RED files + the gate rows, both flags unset: 88 passed: `[pyt] tag=inc-g1-final-unit-off start=2026-11-12 09:15:13 end=2026-11-12 09:15:20 elapsed=7s bound=600s status=OK rc=0`; both flags exported: 88 passed: `[pyt] tag=inc-g1-final-unit-on start=2026-11-12 09:15:32 end=2026-11-12 09:15:39 elapsed=7s bound=600s status=OK rc=0`
- CI-order set (tests/test_identity_stamps_wave_b.py first, the 22 spec 12.2 files and the gate rows, 24 files), flags unset: 728 passed: `[pyt] tag=inc-g1-final-ciorder start=2026-11-12 09:16:22 end=2026-11-12 09:18:04 elapsed=102s bound=1200s status=OK rc=0`
- THE WHOLE FREE TIER (RB-G1F-4 (3), replaces the 737-file comm list): every tests/test_*.py at ea47cbfb minus the four tests/test_precommit_hook*.py = 765 files; BASE in a detached scratch worktree of ea47cbfb (removed, verified gone), 31 chunks of <= 25 (bound 1200), tags inc-g1-final-base-01..31: 25 OK + 6 FAIL, no TIMEOUT, 27 FAILED / ERROR ids (stored as harness/base_records/ea47cbfb.../68dbc2e1...). HEAD = the same 765 plus the unit's five test files = 770 files, 31 chunks, tags inc-g1-final-head-01..31: 25 OK + 6 FAIL, no TIMEOUT, 27 ids (harness/base_records/b5e8624c.../9a02556d...). `comm -13` (branch-only-new) is EMPTY; `comm -23` is empty too (the two id sets are identical); the cold-tiktoken pair of tests/test_prompt_truth.py is ERROR on both sides; the unit's five files have 0 failed ids. Totals: base 29,593 passed / 25 failed / 2 errors, head 29,684 passed / 25 failed / 2 errors. The R8 pair, tests/test_paid_route_metering.py and the CLAUDE.md readers (tests/test_ci_gates.py, tests/test_behavior_dimension_translation.py) are members of this pass.
- Hook files: tests/test_precommit_hook*.py were NOT run (RB-G1F-4 (3)): the unit touches no .githooks file (`git diff --stat origin/main...HEAD -- .githooks` is empty).
- Lint: ruff 0.16.5 `--select E9,F63,F7,F82 --no-cache` clean and py_compile clean on the nine touched python files; none of them is listed in .github/black-clean-paths.txt, so black --check has no member.
- FULL jest suite once (LC-7) at HEAD from SmartCompareApp through the junction, jest 29.7.0, after the H5 probe printed nothing: `[jest] tag=inc-g1-final-jest-full start=2026-11-12 10:01:55 end=2026-11-12 10:02:42 rc=1`: 412 suites (408 passed, 1 failed, 3 skipped); 4,039 passed, 4 failed, 13 skipped, 13 todo. The 4 failures are exactly the accepted config/nativeBundle.w37 drift nodes (d5, k2, k4, k5). The fourteen backend-scanning fences, read from that one run: brand/inAppMark.u4c, clientTruth/medicalNote.s74, clientTruth/privacyManifest.s74, clientTruth/shareTruth.s74, clipboardFallbackService, DimensionBars.perCategory, honestCounts.s69, landing.domain.s76, navigation/linking.w315, onboarding/step05Trust.s69, playInstallReferrerService, playInstallReferrerService.edges, ResultsScreen.timeout all passed; config/nativeBundle.w37 54 passed + the 4 accepted nodes.
- Stated limit of this round: the full jest run overlapped the head-side pytest chunks (one jest and one pytest at a time are separate slots under the box rule); the head id set still equals the base set.

## Owner steps (names only)

- INC-X9 / INC-X2a: nothing to flip; the merge window is the step (the merge redeploys web; it lands only on the relay's "merge window open", after the legal PR).
- INC-X10: flip `ENABLE_LISTING_MATCH_GUARD` on web in its own canary window, after the flip freeze lifts; `ENABLE_EXACT_PRICE_GATE` and `ENABLE_VARIANT_DESCRIPTOR_AXES` stay ON (both are today).
- INC-X8: flip `ENABLE_PHASE2_CACHED_RATING` on web in its own canary window; it acts only while `ENABLE_PHASE2_RESIDUAL_GUARD` is ON (it is).
- Optional, not part of this PR: remove `cohort_summary` from rows saved before the deploy.

Footprint (`git diff --stat origin/main...HEAD`, measured after the replay: exactly these ten files, no whole-file diff): app/services/structured_comparison_service.py, app/services/price_service.py, app/services/image_service.py, tests/test_cohort_summary_orchestrator.py, CLAUDE.md, the four RED files (the X10 file with the F1-1 pin-fix), tests/test_inc_g1_gate_rows.py. Off extraction_service.py, image_routes.py and url_extraction_service.py (the S81-04c / PR #399 arms). No migration, script, client, legal or requirements file.
