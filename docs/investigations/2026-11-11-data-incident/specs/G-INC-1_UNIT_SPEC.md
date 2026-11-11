# G-INC-1 group spec: INC-X9 COHORT-LINE-RETIRE + INC-X10 LISTING-MATCH-GUARD + INC-X8 PHASE2-CACHED-RATING + INC-X2a IMAGE-TIER-TIMING

- Group: G-INC-1 (one LC-9 SAFE group of four units: one branch, one RED round, one GREEN, one adversary, one PR). Lane: S92-FIX incident lane (orchestrator Claude Fable 5.2; this spec by an Opus 5.5 spec agent, READ-ONLY round, 2026-11-11).
- Flag rulings (per unit, from the brief): INC-X9 UNFLAGGED (production bug fix, R-X9-2; owner ruling O1 pending, default unflagged). INC-X2a UNFLAGGED log-only (R-A1, R-X2a-2). INC-X10 DARK behind the NEW `ENABLE_LISTING_MATCH_GUARD`. INC-X8 DARK behind the NEW `ENABLE_PHASE2_CACHED_RATING`. Both new flags default OFF, read per call, flag-OFF byte-identical and pinned.
- Worktree: `C:/Users/SynAckITPC/Documents/AI/sc-inc-g1` (detached). Branch GREEN creates: `fix/inc-g1-result-truth`.
- Base sha (full): `a74caba7e3ff66b12e94178c912197c845ccbd14` (worktree HEAD == base, measured). `git status --short`: EMPTY before every probe and after (only this gitignored `.qa-s80/` file is new; `.gitignore:72` `.qa-*/`, measured with `git check-ignore`).
- Measurement location: `<SP>/G-INC-1/spec/` (SP = C:/Users/SYNACK~1/AppData/Local/Temp/claude/cde30765822f13ce/db84aee4-7211-4eaf-8fea-00a7c4310b9b/scratchpad). Every file:line below was read at the base sha through `git show a74caba7:<path>` in this run. Abbreviations: scs = app/services/structured_comparison_service.py (9,972 lines), ps = app/services/price_service.py (17,277 lines), rs = app/services/rating_service.py (333 lines), img = app/services/image_service.py (295 lines), RB = app/services/response_builder.py (2,387 lines). The four app files are `i/lf w/crlf` (`git ls-files --eol`): the Edit tool keeps CRLF; a whole-file diff is a defect.
- THIS ROUND WAS READ-ONLY (H5 c): no pytest, jest, tsc or eslint ran. Every run is written with its exact command and marked DEFERRED TO RED. A claim derived by reading code, not by running it, is marked BY READING; a claim nothing could settle is marked NOT MEASURED.
- Evidence pointers: brief `<SP>/record/inc/G_INC_1_BRIEF.md`; incident report `<SP>/record/incident/INCIDENT_AND_DATA_PLAN_2026-11-11.md` (root causes 4, 5, 6, 9; fixes X8, X9, X10, X2; section 4); `<SP>/record/incident/T1_trace.md:59,159` (the Eros listing trace); `<SP>/record/inc/RULINGS_INC_R0.md`; `<SP>/record/inc/DEFECT_LEDGER_INCIDENT.md`; `<SP>/record/s81/PLAN_S81.md:174,212` (S81-11; the cohort copy ruling); `<SP>/record/s81/ledger.md:316` (the dated 2026-11-07 flag read); `<SP>/record/s80/contract_freeze.json` (cohort_summary listed as a client-read key with the personalization.cohort fallback, basis "measured"); house template `<SP>/record/s79/S78_F8_UNIT_SPEC.md`.
- Sister units and contracts: S91's S81-04c edits ONLY the log statements of the LLMUnavailableError arms in app/services/extraction_service.py, app/api/image_routes.py, app/services/url_extraction_service.py: this group touches none of those files (img is image_service.py, not image_routes.py). S81-04c / CL3 may add CLAUDE.md text: a union at the final replay. MON1 (FOCUS, alone) and INC-X2 (designed from INC-X2a's lines) follow. X11 is not a build unit (R0-3).
- Personal-data rule: the repo is public. No personal value in any file, test, fixture, log line or report; synthetic values only (the region words "Capital" / "Northern" the existing tests already use). Every log line this group adds carries constants, closed-set words and ints only (no product name, URL, query text or governorate). No credential-shaped literal; no new env name is a credential (CREDENTIALS_UNSET unchanged).

---------------------------------------------------------------------------------------------------

## 0. The group

### 0.1 What the group does

- INC-X9 COHORT-LINE-RETIRE (unflagged): the text / streaming / camera compare responses (all built at the three `build_comparison_response` call sites, scs:3880 partial, :4783 sync, :5676 streaming) stop carrying the root block `cohort_summary` {peer_count, governorate}. The store binary (JS 683f56c0) renders its "N+ shoppers in <governorate> leaned the same way." box only from that block (or a `personalization.cohort` fallback the backend never sends), so the box disappears from the store app on the next response. N was the sign-up survey group size, not agreement on the pair (root cause 9). The change: `_build_cohort_summary` returns None as its first statement, so the existing omit path becomes the only path.
- INC-X10 LISTING-MATCH-GUARD (dark, `ENABLE_LISTING_MATCH_GUARD`): a small in-repo table of fragrance LINES that have an opposite-gender sibling, each with its default (unmarked) side. Flag ON + category fragrances + a QUERY that states no gender word + a query naming a table line + a CANDIDATE title that states exactly one gender other than the line's default side = a gender mismatch (the existing "gender" axis word). Wired into the selection axis core (every price adapter's `_selection_match`, `select_best`, `should_cache_price`) and into the backstop extras (cache-read `_cache_price_identity_ok`, display `is_price_showable`), so a poisoned 7-day genuine cache entry is dropped too. Targets the wrong-product price of root cause 4.
- INC-X8 PHASE2-CACHED-RATING (dark, `ENABLE_PHASE2_CACHED_RATING`): when ENABLE_PHASE2_RESIDUAL_GUARD skips Phase 2 for a product, the product still gets the rating its in-memory shopping rows hold: the SAME pure function the normal Phase-2 rating tries first (`extract_rating_from_shopping`, rs:127) under the SAME acceptance rule as `get_verified_rating`'s free tier (rs:285-291), so the keys and the verification marker are exactly those of a normal hit. No network, no LLM, no await. The smart-fallback refill stays skipped (root cause 6).
- INC-X2a IMAGE-TIER-TIMING (unflagged, log-only): `get_product_image_url` (img:222-295) logs one INFO line per tier it reaches (constant tier name, closed-set outcome, elapsed ms) and one INFO line when the 5 s race cancels it (the tier in flight, that tier's ms, the call's total ms). Same awaits, order, return values and exceptions; the cancellation handler has no await and re-raises. It is the measurement INC-X2 is designed from (root cause 5).

### 0.2 The branch and the order GREEN applies the change list

Branch `fix/inc-g1-result-truth` from a74caba7 (replayed onto the then-main at the final round). GREEN applies, in order: (1) the INC-X9 hunk in scs; (2) the INC-X8 hunks in scs; (3) the INC-X10 hunks in ps; (4) the INC-X2a hunks in img; (5) the INC-X9 E-rows in tests/test_cohort_summary_orchestrator.py; (6) CLAUDE.md (one group block + the :341 sentence + the :260 sentence in place). The four RED files arrive frozen from the RED round.

### 0.3 Files two units share

| File | Units | Hunks (disjoint) | Order |
|---|---|---|---|
| app/services/structured_comparison_service.py | INC-X9, INC-X8 | X9: top of the `_build_cohort_summary` body (scs:5869-5914). X8: two module helpers after `_phase2_min_residual_seconds` (scs:1892-1894) + one block between the Phase-2 result loop and `result["rating"] = ...` (scs:6698-6709) | X9 then X8; every Edit is anchored on an exact unique string, so the order moves no anchor |
| CLAUDE.md | all four | one block after the S81-G10 owner-steps bullet (CLAUDE.md:635, before `## Tests` :637); one sentence appended to the :341 Feature Flags clause; the :260 Results-redesign sentence edited in place (X9) | one GREEN edit per location |

No other file is shared. ps (X10) and img (X2a) are single-unit files. No unit touches extraction_service.py, image_routes.py or url_extraction_service.py (R-G1-2).

### 0.4 Flag rulings and change list per unit (summary; detail in each unit's section 3)

| Unit | Flag | Files | New names |
|---|---|---|---|
| INC-X9 | none (unflagged bug fix) | scs (1 statement + docstring lines), tests/test_cohort_summary_orchestrator.py (3 E-rows), CLAUDE.md | none |
| INC-X10 | `ENABLE_LISTING_MATCH_GUARD` (OFF) | ps (table, reader, predicate, 2 hook lines), CLAUDE.md | `_GENDER_FLIP_LINES`, `listing_match_guard_enabled()`, `_vd_gender_line_flip(q, c)` |
| INC-X8 | `ENABLE_PHASE2_CACHED_RATING` (OFF) | scs (2 helpers + 1 block), CLAUDE.md | `_phase2_cached_rating_enabled()`, `_phase2_cached_rating(full_name, cache)`, log `[L2.6] phase 2 cached rating outcome=%s product=%d` |
| INC-X2a | none (log-only, R-A1) | img (imports, tier bookkeeping, 1 except arm), CLAUDE.md | logs `[IMG_TIER] tier=%s outcome=%s ms=%d`, `[IMG_TIER] cancelled tier=%s tier_ms=%d total_ms=%d` |

All new names were grepped at base: zero hits (`git grep "IMG_TIER\|phase 2 cached\|ENABLE_LISTING_MATCH_GUARD\|ENABLE_PHASE2_CACHED_RATING\|_GENDER_LINE" a74caba7`).

---------------------------------------------------------------------------------------------------

## Unit INC-X9 COHORT-LINE-RETIRE (unflagged; RED file tests/test_inc_x9_cohort_line_retire.py)

### X9.0 What the unit does

New responses (text REST, streaming `complete`, camera through `compare_from_text`, the hard-cap partial) no longer carry `cohort_summary`; new saved rows (`comparisons.full_response`) therefore lack it; the store binary stops showing the cohort box. Nothing else changes (proved by PIN rows P9-2 / P9-3 over full builder responses).

### X9.1 Base state (measured)

| What | Where | Measured fact |
|---|---|---|
| The helper | scs:5867-5914 `_build_cohort_summary` (staticmethod) | Docstring :5872-5891; body `try:` :5892; returns None for no profile (:5893-5894), `was_cohort_block_active` False (:5897-5898), n not a positive int (:5900-5902), governorate in `_COHORT_GOV_SKIP` (:5904-5909); else `{"peer_count": n, "governorate": gov}` (:5910); except -> DEBUG + None (:5911-5914). |
| Skip set | scs:5863-5865 `_COHORT_GOV_SKIP` | Holds non-ASCII (Arabic) literals; the unit does NOT touch it. |
| Call site partial | scs:3917 (inside `_build_partial_response` scs:3798, builder call :3880) | `cohort_summary=self._build_cohort_summary(ctx.get("demographics_profile")),` |
| Call site sync | scs:4806 (builder call :4783) | `cohort_summary=self._build_cohort_summary(demographics_profile),` |
| Call site streaming | scs:5698 (builder call :5676) | same text as :4806 |
| Builder parameter | RB:1484 `cohort_summary: Optional[Dict[str, Any]] = None` | docstring RB:1507-1513 |
| Builder attach | RB:2192-2212 | `if isinstance(cohort_summary, dict):` re-validates peer_count int > 0 (not bool) and a non-blank str governorate, then sets `result["cohort_summary"]`; otherwise the key is absent. None -> absent. |
| Builder callers | `git grep "build_comparison_response("` | only scs:3880, :4783, :5676 (no route or script builds a response itself). |
| `personalization` block | RB:2084-2093 | keys personalized / factors / personalized_insights / applied_shifts: NO `cohort` key, so the client's `personalization.cohort` fallback never fires. |
| Other readers in app/ | `git grep -i "cohort_summary\|peer_count" a74caba7 -- app scripts` | only RB and scs above; scripts/: none. `metadata.cohort_injected` (scs:4833, :5725) reads `was_cohort_block_active` directly, not the helper: unchanged. |
| Whole-response cache | cache_service.py:777/783 `get/set_comparison_cache` | defined, ZERO callers in app/ (grep): no cached response can replay the block. |
| Saved rows | history_routes.py:138-166 | `GET /{comparison_id}` returns `full_response` as saved: rows saved before the deploy keep the block (stated limit L-X9-2). |
| Referral landing | referral_service.py:488 `"cohort_match": None` | a literal None; the referral payload is NOT fed by `_build_cohort_summary` (R-X9-3 measurement: no finding). |
| Production flags | ledger.md:316 (2026-11-07 dated read) | ENABLE_COHORT_PERSONALIZATION ON on web; so at base every user with a matched cohort gets the block (the incident rows: peer_count 53, governorate Northern). |
| Client store binary 683f56c0 | ResultsScreen.tsx:988-1006 `resolveCohortPeerCount` / `resolveCohortGovernorate`; ResultsContent.tsx:533-544 the slot; CohortBadge.tsx:39-86 | `summary = result.cohort_summary ?? result.personalization?.cohort ?? null`; `if (!summary) return 0` / `return ''`. CohortBadge: `if (peerCount <= 0 \|\| !governorate) return null;` (CohortBadge.tsx:62, after its hooks). The slot `<View style={styles.cohortSlot} testID="results-cohort-badge-slot">` (marginBottom spacing.base, ResultsContent.tsx:791-793) stays rendered and empty, exactly as today for a user without a matched cohort. ABSENT PATH PROVEN BY READING (R-G1-1). |
| Client OTA f1e20c39 / a74caba7 | `git grep "cohort_summary" a74caba7 -- SmartCompareApp/src` | zero hits: the update never reads the block (S81-11 deleted CohortBadge). |
| Contract freeze | contract_freeze.json (findings, ResultsScreen entry) | lists `cohort_summary.{peer_count\|peers_count\|peers, governorate} with personalization.cohort fallback` as a client-read key. H1 allows removing a frozen key only when the unit's rulings say so in words: R-X9-1 / R-X9-2 do. |
| Flag reader idiom | scs:1852-1853 `_flag_on(name)` | not used by X9 (unflagged). |
| Libraries | none new | python 3.12.9 venv (`.venv-qaren/pyvenv.cfg`), CI python 3.12 (ci.yml:24). |
| Guards | `.github/black-clean-paths.txt` | scs is NOT on the black allowlist; ruff blocking tier E9,F63,F7,F82 only (ci.yml, .githooks/pre-commit:88): an unreachable statement after an early return is not flagged by those codes (BY READING the ruff selection). |

X9.1.9 Smallest change, chosen and why. Option A (CHOSEN): insert `return None` as the first statement of the `_build_cohort_summary` body (before `try:` at scs:5892) and add an INC-X9 paragraph to its docstring. One statement; the three call sites, the builder (R-X9-3: it keeps accepting a dict and None) and the wiring pin `test_all_three_build_sites_pass_cohort_summary` stay byte-identical; revert = delete one line. Option B (rejected): pass `cohort_summary=None` at the three call sites: three hunks instead of one, the wiring pin flips (an extra E-row), and the helper becomes dead but still tested. The body after the early return is left in place, unreachable, so the gating code stays readable for any future honest agreement count (question Q-X9-a to the orchestrator: delete the unreachable body instead).

X9.1.10 Base pass state of the files the unit touches (DEFERRED TO RED; exact commands):
```
PYTHONIOENCODING=utf-8 C:/Users/SynAckITPC/Documents/AI/.venv-qaren/Scripts/python.exe <SP>/harness/pyt.py --bound 600 --tag inc-x9-base --log <SP>/G-INC-1/red/x9_base.log --cwd C:/Users/SynAckITPC/Documents/AI/sc-inc-g1 -- tests/test_cohort_summary_orchestrator.py tests/test_response_builder_cohort_summary.py tests/test_extraction_cohort_prompt.py tests/test_cohort_personalization_load.py
```
Expected (BY READING): all green at base (16 nodes in the orchestrator file incl. the wiring guard + 10 in the builder file, counted by reading). NOT MEASURED in this round.

### X9.2 Contract

- Flags / knobs: none new. ENABLE_COHORT_PERSONALIZATION and the verdict-prompt cohort block (`was_cohort_block_active`, extraction_service) are untouched (R-X9-3).
- Keys: REMOVED from new responses: root `cohort_summary` (an optional block; frozen-contract removal ruled in words by R-X9-1 / R-X9-2). No key added, renamed or retyped. `metadata.cohort_injected` unchanged.
- Log lines: none added. The helper's DEBUG `cohort_summary build skipped: %s` (scs:5913) becomes unreachable.
- Failure table: the helper cannot raise (it returns before `try:`); a builder given None omits the key (RB:2200). No new error envelope, never a bare 503.
- DEPLOY-VISIBLE DELTA (the main invariant, exact): (1) every new text / streaming / camera / partial response lacks root `cohort_summary` where base would have sent it (users whose persisted `demographics_profile.cohort_match` passes `was_cohort_block_active`, with ENABLE_COHORT_PERSONALIZATION ON on web); (2) every comparison saved after the deploy lacks it in `full_response`; (3) the store binary (683f56c0) shows no cohort box on those results (the empty slot keeps its margin, as for an unmatched user today); (4) nothing else: every other key and value of the response is identical to base (P9-2 / P9-3), the OTA bundle shows no difference (it never read the block). Response size shrinks by the block's bytes.
- Test seams: the helper is a staticmethod called as `StructuredComparisonService._build_cohort_summary(profile)` [production: called via `self.` at the three sites]; conftest sets `ENABLE_COHORT_PERSONALIZATION=true` by default (tests/conftest.py:47) [production: ON].

### X9.3 Change list (GREEN, in order)

1. Byte copies of scs and tests/test_cohort_summary_orchestrator.py into `<SP>/G-INC-1/green/` (sha256 recorded).
2. scs `_build_cohort_summary`: append to its docstring one paragraph "INC-X9 (2026-11-11, unflagged): the cohort line is retired: N was the survey group size, not agreement on the pair; this helper returns None first, so no response carries cohort_summary (the builder keeps accepting a dict)." and insert `return None` as the first statement of the body, before `try:`. Pure ASCII.
3. tests/test_cohort_summary_orchestrator.py: the three E-rows of X9.4.1 (assertion lines only; test names unchanged).
4. CLAUDE.md: the X9 row of the group block (section 12.6) and the :260 sentence in place.
No other file.

### X9.4 Existing pins

#### X9.4.1 Pins that change deliberately (E-rows; a presence pin becomes an absence pin with the same subject, none weakened)

| E | File::test | Base assertion | New assertion | Reason |
|---|---|---|---|---|
| E9-1 | tests/test_cohort_summary_orchestrator.py::test_returns_peer_count_and_governorate_when_resolved | `out == {"peer_count": 19, "governorate": "Capital"}` | `out is None` (same fully resolved profile, flag ON) | R-X9-1: a resolved cohort no longer yields a block |
| E9-2 | ...::test_peer_count_sourced_from_cohort_match_n | `out["peer_count"] == 27` | `out is None` (n=27 never surfaces) | same |
| E9-3 | ...::test_broadened_governorate_quality_still_emits | `out is not None` + governorate | `out is None` | same |

Grep at base: `git grep -c "cohort_summary\|_build_cohort_summary\|peer_count" a74caba7 -- 'tests/*'` = only tests/test_cohort_summary_orchestrator.py (17 lines) and tests/test_response_builder_cohort_summary.py (43 lines); no fixture / golden JSON pins the key; no SmartCompareApp/__tests__ suite reads it (only comments, ResultsScreen.test.tsx:109); the fourteen client fences read no scs literal.

#### X9.4.2 Pins that stay green unedited

tests/test_cohort_summary_orchestrator.py (the 11 None rows + the flag-off row + `test_all_three_build_sites_pass_cohort_summary`, whose source strings at scs:3917 / 4806 / 5698 are untouched), tests/test_response_builder_cohort_summary.py (all 10: the builder still attaches a valid dict and omits None), tests/test_extraction_cohort_prompt.py, tests/test_cohort_personalization_load.py, every partial-path test (tests/test_partial_response_no_fabricated_scores.py, test_compare_timeout_graceful.py, test_cost_meter_s74.py, test_s75_fanout_starve.py, test_s78_*.py, test_s81_s11b / s18b ...: none asserts the block).

### X9.5 RED tests (tests/test_inc_x9_cohort_line_retire.py; hermetic; conftest ENABLE_COHORT_PERSONALIZATION=true)

| # | Test | Assertion | At base | Satisfied by |
|---|---|---|---|---|
| R9-1 | test_r9_1_resolved_cohort_yields_none | `_build_cohort_summary(profile)` is None for a profile that passes `was_cohort_block_active` (match_quality exact, confidence medium, cohort_key set, n=53, governorate "Northern"), flag "true" | dict -> AssertionError | X9.3 step 2 |
| R9-2 | test_r9_2_none_for_padded_flag_and_broadened | same with the flag "  TRUE " and quality broadened_governorate | dict -> AssertionError | step 2 |
| R9-3 | test_r9_3_partial_response_has_no_block | `_build_partial_response(elapsed_seconds=1.0)` with `_partial_build_ctx` holding that profile (state seeded as tests/test_partial_response_no_fabricated_scores.py does) -> `"cohort_summary" not in result` | present -> AssertionError | step 2 (the partial call site, scs:3917) |
| P9-1 | test_p9_1_prompt_cohort_gate_untouched | `extraction_service.was_cohort_block_active(profile)` is True with the flag ON and False with "false" | green | R-X9-3 |
| P9-2 | test_p9_2_scored_response_identical_but_the_key | builder over two products WITH a scoring_result (overview / scoring_v2 shape): `resp(dict)` minus `cohort_summary` == `resp(None)`, after removing the volatile keys the row measures by building `resp(None)` twice (any key whose value differs between two identical builds; asserted to be a subset of a named set the RED agent records, e.g. a timestamp) | green | proves "nothing else" |
| P9-3 | test_p9_3_legacy_response_identical_but_the_key | the same with `scoring_result=None` (the legacy GPT-index shape) | green | same |
| P9-4 | test_p9_4_builder_still_accepts_dict_and_none | `resp(valid dict)["cohort_summary"]` equals the dict; `resp(None)` has no key | green | R-X9-3 |
| P9-5 | test_p9_5_call_sites_unchanged | `inspect.getsource(scs)` contains the three call-site strings with the counts the wiring guard asserts (2 + 1) and `was_cohort_block_active(` with the count the RED agent measures at base (3 by grep at a74caba7: :5898 + the two metadata sites :4833 / :5725) | green | footprint pin |

R9-3 caveat: if the partial ctx cannot be seeded hermetically from the named test's pattern, the RED agent drops R9-3 and says so (the helper rows and P9-5 still cover the three sites, which all call the one helper).

### X9.6 Mutation table (on byte copies of the GREEN scs; restore + sha256 compare; pyt.py -k, bound 600)

| M | Mutation (exact string edit, matches once) | Killed by |
|---|---|---|
| M9-1 | delete the inserted `return None` | R9-1, R9-2, R9-3 |
| M9-2 | `return None` -> `return {}` | R9-1 (`is None`) |
| M9-3 | move the early return below the `was_cohort_block_active` check (`if not was_cohort_block_active(...): return None` then `return None`) | equivalent at the response level (both return None for every input); reported as an equivalent survivor for a ruling (it leaves the predicate reachable). Not counted as killed. |
| M9-4 | at the streaming call site scs:5698 replace the helper call with `{"peer_count": 1, "governorate": "Capital"}` | P9-5 (source strings) |

### X9.7 Comm set and gates

The group's comm set and CI-order set (section 12.1 / 12.2) cover X9. X9-specific cheapest-first gates at GREEN: (1) py_compile + ruff E9,F63,F7,F82 on scs and the E-row file; (2) the RED file + the E-row file + tests/test_response_builder_cohort_summary.py (bound 600); (3) the CI-order set; (4) the comm set chunks.

### X9.8 CLAUDE.md row and owner steps

Row text (inside the group block, section 12.6): "INC-X9 COHORT-LINE-RETIRE (no flag; an unflagged production bug fix, R-X9-2): `_build_cohort_summary` returns None first, so no text / streaming / camera / partial response carries `cohort_summary` (the store binary 683f56c0 rendered '+N shoppers in <governorate>' from it, N = the sign-up survey group size, not agreement on the pair); the builder keeps accepting a dict; `metadata.cohort_injected`, ENABLE_COHORT_PERSONALIZATION and the verdict-prompt cohort block are unchanged. Stated limits: L-X9-1..L-X9-3." The :260 sentence gains: "the server stopped sending cohort_summary (INC-X9, 2026-11-1x)". Owner steps (names only): none to flip; the merge window (R0-6) is the step.

### X9.8b PROOF ON THE PHONE

- Pair: repeat any golden pair on the STORE binary (not the update), e.g. golden pair 4 (Dior Sauvage EDP vs Chanel Bleu de Chanel EDP, never compared) or pair 3, from the owner's account (its demographics produce a matched cohort: the incident rows carried peer_count 53).
- Visible: no "+53 shoppers in Northern..." box under the verdict.
- Backing: the new row (`comparisons.full_response`) has no `cohort_summary` key; before = the three incident rows 441e7b7d, 5b369372, e2320ca7 (peer_count 53, governorate Northern).
- NOT provable in production: that no user anywhere sees the box (a History re-open of a row saved before the deploy still shows it on the store binary, L-X9-2); the OTA bundle shows nothing either way.

### X9.9 Stated limits

- L-X9-1: an unreachable gate body remains after the early return (deliberate, Q-X9-a).
- L-X9-2: rows saved before the deploy keep `cohort_summary`; History detail (history_routes.py:138-166) returns them as saved, so the store binary still shows the box when an OLD result is re-opened. Rewriting saved rows is out of scope.
- L-X9-3: the store binary keeps the empty slot View with its bottom margin (unchanged from an unmatched user today).

### X9.10 Out of scope

ENABLE_COHORT_PERSONALIZATION, the verdict prompt's cohort block, `demographics_profile`, the digit-free survey lines, the referral landing payload (always `cohort_match: None`), the builder, saved rows, any client file.

### X9.11 Open questions and answers to the brief

- Q-X9-a (orchestrator): keep the unreachable body (smallest diff, chosen) or delete it with `_COHORT_GOV_SKIP` (a larger diff touching non-ASCII literals)?
- Brief R-X9-1 (smallest change): the top-of-predicate return, X9.1.9.
- Brief R-X9-3 (referral): referral_service.py:488 sends a literal `cohort_match: None`; the ReferralLanding badge at 683f56c0 reads `resolution.cohort_match` (ReferralLandingScreen.tsx:140-144), never `cohort_summary`: no finding.
- Brief R-G1-4 (every reader of cohort_summary): app/ = RB:1484-1513, RB:2192-2212, scs:3917 / 4806 / 5698 / 5867-5914; scripts/ = none; tests/ = the two files above; SmartCompareApp/src at a74caba7 = none; at 683f56c0 = ResultsScreen.tsx:980-1006; SmartCompareApp/__tests__ = a comment only; docs/ = historical journals and CONTEXT_SESSION_LOG / SESSION_BUNDLES prose (no contract file); CLAUDE.md:260 and :577 (prose).

---------------------------------------------------------------------------------------------------

## Unit INC-X10 LISTING-MATCH-GUARD (dark: ENABLE_LISTING_MATCH_GUARD; RED file tests/test_inc_x10_listing_match_guard.py)

### X10.0 What the unit does

Under the new flag, a price candidate whose title states the opposite gender of a known gender-flip fragrance line, for a query that names that line and states no gender, is rejected on every price-selection gate and on the cache-read / display backstop. A rejected listing leaves the product on its existing paths (another candidate, the cascade, or no confirmed price); no new response key.

### X10.1 Base state (measured)

X10.1.1 The incident path (R-X10-1 trace, BY READING; the log facts from T1_trace.md:59 / :159):

| Step | Where | Fact |
|---|---|---|
| Adapter fan-out | scs:7730-7764 (`_new_adapter_specs` loop) | Woo adapters ran `fn(s.domain, full_name, currency)` per host; T1: woo hits 28.0 alibaksh, 25.0 fragrancebh, 33.0 theperfumesclub (titles of the 28.0 and 33.0 hits NOT in the log: NOT MEASURED). |
| Adapter gate | woocommerce_service.py:159 `_category` = resolved or `_infer_category_from_query(product_name)`; :226 `_selection_match(product_name, title, _category, ...)`; :290 `select_best(candidates, product_name, _category, drop_out_of_stock=False)` | scs calls the adapter WITHOUT `resolved_category`, so the adapter's category is inferred from "Versace Eros EDP" (whether it infers "fragrances" is NOT MEASURED; BY READING EDP is a fragrance token). |
| Cross-adapter pick | scs:7765-7837 | genuine-only filter, then `best = select_best(genuine_observed, full_name, category, stable_tiebreak=_genuine_priority_enabled())` (scs:7820-7826); ENABLE_GENUINE_PRICE_PRIORITY is OFF on web (ledger.md:316) so stable_tiebreak False. |
| The acceptance | ps:8572-8668 `select_best` -> ps:8637 `_selection_match(query_name, title, category, candidate_brand=brand)` -> ps:8291-8331 -> `descriptor_verdict(..., SELECTION)` ps:7967-7995 (selection steps ps:7898-7964) -> `_descriptor_axis_mismatch` ps:7813-7895 (strict_extras) -> gender branch ps:7886-7888 `_vd_gender_mismatch(q, c) or _vd_feminine_query_unconfirmed(q, c)` | q = "Versace Eros EDP": strict gender None, pronoun gender None. c = "Versace Eros for Women EDP 100ml": strict gender "women". `_vd_gender_mismatch` ps:7785-7795 needs BOTH stated -> False; `_vd_feminine_query_unconfirmed` ps:7798-7802 needs q.gender == "women" -> False. Identity: "for" / "women" are padding and gender words are stripped from identity (`_FRAGRANCE_PADDING_TOKENS` ps:5648-5661, `_GENDER_IDENTITY_STRIP` ps:5679); concentration EDP equal; size one-sided -> `_descriptor_selection_verdict` accepts (subset holds, no variant-add token). So `_selection_match` returns True: the incident title passes every token rule. |
| Rank | ps:8655-8668 `_sort_key` = (in_stock is False, -authority, -precision, amount) | the 25.0 listing won; with equal authority and precision the LAST key (amount) picks the cheapest = 25.0 (the authority of the three hosts via `score_source` NOT MEASURED). There is no score: the gate is boolean, the rank is the tuple above. |
| Write-through | scs:7864-7867 `should_cache_price(full_name, best, category)` (ps:9288, uses the same `_selection_match`, ps:9296) then `_cache_price_and_clear_sentinel` + `_save_price_to_db` | a genuine price is cached for GENUINE_PRICE_CACHE_TTL = 7 days (ps:157, env GENUINE_PRICE_CACHE_TTL_SECONDS; ps:204-219 `price_cache_ttl`) and saved to L2; so the wrong price can be re-served for up to 7 days (plus the L2 row) unless a READ check rejects it. |
| Cache read | scs:1237-1265 `_cache_price_identity_ok` -> ps:8455-8494 `backstop_identity_verdict` -> ps:8374-8433 `_descriptor_backstop_axes_verdict` (only when `variant_descriptor_axes_enabled()`, ON on web) | the backstop gender check is both-stated only (ps:8409-8411): the cached women's listing passes the read check today. |
| The documented leak | ps:5741-5760 `_feminine_query_unconfirmed` docstring | the base code names this exact class ("Versace Eros" -> "Eros Pour Femme") as "a real but UNFIXABLE-by-tokens leak": a symmetric token rule over-rejects women's-base lines ("Black Opium" -> "Black Opium For Women"). The golden corpus pins it: tests/data/variant_descriptor_golden_corpus.json vd-0000 (query "Versace Eros", title "Versace Eros Pour Femme Eau de Parfum 100ml": every selection_match True, backstop_ok True). |

X10.1.2 Every existing gender / flanker rule and the flag that gates it (production state from ledger.md:316, 2026-11-07; unset = default):

| Rule | Where | Gate | Prod |
|---|---|---|---|
| Whole descriptor chain (selection, exact, backstop) | ps:4370-4374 `exact_gate_enabled` | ENABLE_EXACT_PRICE_GATE, default ON (not-in-false-set idiom) | unset = ON |
| Gender CONTRADICTION (both sides stated, differ) at selection | ps:7785-7795, hooked ps:7886-7888 (fragrance/beauty + fashion) | exact gate | ON |
| Pronoun gender (him/her/gents/ladies) in the contradiction | ps:5703-5728 (`_PRONOUN_*_TOKENS` :5703-5704, `_pronoun_gender_of` :5707) | ENABLE_VARIANT_DESCRIPTOR_AXES (ps:6833-6851) | ON |
| Femme-query asymmetry (women query vs unconfirmed candidate) | ps:7798-7802 | exact gate | ON |
| Backstop gender contradiction (cache read + display) | ps:8409-8411 | ENABLE_VARIANT_DESCRIPTOR_AXES | ON |
| Backstop flanker ADD (elixir / supreme / absolu / intense / extreme) | ps:8433-8434, set ps:7164-7166 | ENABLE_VARIANT_DESCRIPTOR_AXES | ON |
| Fragrance padding (gender words, for / pour, spray...) stripped from identity | ps:5648-5661, ps:5679 | exact gate | ON |
| Identity subset + variant-add superset | ps:7953-7964 | exact gate | ON |
| `price_service.py` mentions "flanker" 57 times (grep -c -i) | comments + the rules above | | |

X10.1.3 The truth table (R-X10-2 rows binding; rows marked ADDED are this spec's; base verdicts BY READING, each confirmed at RED by its PIN / RED status). Column "q gender word" = any of the strict or pronoun gender tokens in the query.

| # | Query | Candidate title | q gender word | Base `_selection_match` | Required under flag ON | Why |
|---|---|---|---|---|---|---|
| T1 | Versace Eros EDP | Versace Eros for Women EDP 100ml | no | True | REJECT | line versace+eros, default men; c states women |
| T2 | Versace Eros EDP | Versace Eros Pour Femme EDP 100ml | no | True | REJECT | same |
| T3 | Bleu de Chanel | Bleu de Chanel Pour Homme EDP 100ml | no | True | ACCEPT | not a table line |
| T4 | Dior Sauvage EDP | Sauvage Eau de Parfum for Men 100ml (candidate_brand Dior) | no | True | ACCEPT | not a table line |
| T5 | Lancome La Vie Est Belle EDP | La Vie Est Belle Eau de Parfum for Women 100ml (brand Lancome) | no | True | ACCEPT | not a table line |
| T6 | YSL Libre EDP | Libre Eau de Parfum Women 90ml (brand YSL) | no | True | ACCEPT | not a table line |
| T7 | Creed Aventus | Creed Aventus for Men 100ml | no | True | ACCEPT | line creed+aventus, default men; c men |
| T8 | Creed Aventus for Her | Creed Aventus for Her Eau de Parfum 75ml | yes (her) | True | ACCEPT | query states a gender: the rule is inert |
| T9 ADDED | Versace Eros EDP | Versace Eros Pour Homme EDP 100ml | no | True | ACCEPT | c = default side |
| T10 ADDED | Versace Eros EDP | Versace Eros EDP 100ml | no | True | ACCEPT | c states no gender |
| T11 ADDED | Versace Eros EDP | Versace Eros EDP for Men and Women 100ml | no | True (BY READING; RED confirms) | ACCEPT | both genders = no side |
| T12 ADDED | Creed Aventus | Creed Aventus for Her EDP 75ml | no | True | REJECT | pronoun "her" names the women's sibling |
| T13 ADDED | Dolce & Gabbana Light Blue EDT | Dolce & Gabbana Light Blue Pour Homme EDT 125ml | no | True | REJECT | line light+blue+dolce+gabbana, default women |
| T14 ADDED | Dolce & Gabbana Light Blue EDT | Dolce & Gabbana Light Blue Eau de Toilette for Women 100ml | no | True | ACCEPT | c = default side |
| T15 ADDED | Versace Eros Pour Femme EDP | Versace Eros Pour Femme EDP 100ml for Women | yes | True | ACCEPT | inert (query states a gender) |
| T16 ADDED | Versace Eros EDP | Versace Eros for Women EDP 100ml, category None | no | True | ACCEPT (flag ON) | the rule is fragrance-category only |

The table shows the brief's point: a one-sided marker alone cannot decide (T5 / T6 / T14 accept women-marked titles; T1 / T2 must reject one). The rule needs line knowledge.

X10.1.4 Design choice (R-X10-3): option (b), the in-repo table, consulted only for a one-sided marker against an unmarked query. Option (a) (candidate-set evidence: a one-sided marked candidate loses to an unmarked / same-side candidate of the same request) is REJECTED as insufficient and wider: it cannot reject T1 when the women's listing is the only candidate (a single adapter hit, or the 7-day cached entry read alone), it re-ranks every women's-base line (T5 / T6 / T14 lose to any unmarked listing on authority ties), and it has no reach into the cache-read / display backstop. (c) adds (a)'s risks for no table row (b) misses. Pure functions, no network, no LLM, no dependency, no host; price selection only (the user's typed identity, the product name and the descriptor extraction are untouched).
| T17 ADDED | Versace Dylan Blue | Versace Dylan Blue Pour Femme Eau de Parfum 100ml | no | True | REJECT | line versace+dylan+blue, default men |
| T18 ADDED | Dolce & Gabbana Light Blue EDT | Dolce & Gabbana Light Blue EDT for Men and Women 100ml | no | True (BY READING) | ACCEPT | both genders = no side (kills M10-8) |

Line facts (default side per line) are general product knowledge, not measured in the repo: [OWNER / ORCHESTRATOR READ] Versace Eros = men (Eros Pour Femme is the sibling), Versace Dylan Blue = men (Dylan Blue Pour Femme), Creed Aventus = men (Aventus for Her), Dolce & Gabbana Light Blue = women (Light Blue Pour Homme). The table ships with exactly these four lines, each covered by a RED and a PIN row; extending it is a later data change (Q-X10-a).

X10.1.5 Flag idiom and descriptor facts: house idiom `os.getenv("ENABLE_X", "false").strip().lower() in ("true", "1", "yes", "on")` (variant_descriptor_axes_enabled ps:6851-6852 uses it); scs `_flag_on` scs:1852-1853. The VariantDescriptor (ps:7265-7340, frozen dataclass) carries `fold_tokens` (ps:7339: `re.findall([a-z0-9]+, _fold_identity(capped))`, every word of the capped text), `gender` (strict, ps:7316) and `gender_pronoun` (flag-gated, ps:7317). Descriptors are memoized (`_extract_variant_descriptor_cached`, an lru_cache cleared by the autouse conftest fixture, tests/conftest.py:149-167): the new predicate reads only descriptor fields and the env, never extraction, so the memo stays valid across flag values. `_vd_*` helpers take descriptors and are defined after the dataclass (ps:7785+); module annotations are evaluated at def time in ps (no `from __future__ import annotations` in ps, grep), so the new predicate goes after ps:7802, not near ps:5731.

X10.1.10 Base pass state (DEFERRED TO RED):
```
PYTHONIOENCODING=utf-8 C:/Users/SynAckITPC/Documents/AI/.venv-qaren/Scripts/python.exe <SP>/harness/pyt.py --bound 600 --tag inc-x10-base --log <SP>/G-INC-1/red/x10_base.log --cwd C:/Users/SynAckITPC/Documents/AI/sc-inc-g1 -- tests/test_variant_descriptor_golden.py tests/test_variant_descriptor_backstop_axes.py tests/test_variant_descriptor_unit.py tests/test_gender_contradiction_fix.py tests/test_gender_gents_ladies_leak.py tests/test_correctness_review_pr9_fixes.py tests/test_exact_gate_flag_off_parity.py tests/test_wrong_cheap_price_guard.py
```
NOT MEASURED in this round.

### X10.2 Contract

- Flag: `ENABLE_LISTING_MATCH_GUARD` (default OFF; read per call as the FIRST statement of `_vd_gender_line_flip`; any value outside true/1/yes/on after strip().lower() is OFF). Requires the exact gate (when ENABLE_EXACT_PRICE_GATE is off, `_selection_match` / `backstop_identity_verdict` return before any descriptor is built, ps:8316-8317 / ps:8478-8482, so the predicate is never reached). The backstop hook additionally needs ENABLE_VARIANT_DESCRIPTOR_AXES (ON on web).
- New names in ps (after `_vd_feminine_query_unconfirmed`, ps:7798-7802): `_GENDER_FLIP_LINES: Tuple[Tuple[FrozenSet[str], str], ...]` (the four lines above, words lower-case as `fold_tokens` yields them); `_GENDER_LINE_MEN_WORDS = _GENDER_MEN_TOKENS | _PRONOUN_MEN_TOKENS`; `_GENDER_LINE_WOMEN_WORDS = _GENDER_WOMEN_TOKENS | _PRONOUN_WOMEN_TOKENS`; `listing_match_guard_enabled() -> bool`; `_vd_gender_line_flip(q: VariantDescriptor, c: VariantDescriptor) -> bool`:
```
def _vd_gender_line_flip(q, c):
    if not listing_match_guard_enabled():
        return False
    q_words = q.fold_tokens
    if q_words & (_GENDER_LINE_MEN_WORDS | _GENDER_LINE_WOMEN_WORDS):
        return False            # the query states a gender: the base axes decide
    c_men = bool(c.fold_tokens & _GENDER_LINE_MEN_WORDS)
    c_women = bool(c.fold_tokens & _GENDER_LINE_WOMEN_WORDS)
    if c_men == c_women:
        return False            # no side, or both (unisex wording)
    c_side = "men" if c_men else "women"
    for line_words, default_side in _GENDER_FLIP_LINES:
        if line_words <= q_words:
            return c_side != default_side
    return False
```
- Hooks (two statements, same reason word as the existing gender axis, so no new reason / guard_rejected value): (H1) in `_descriptor_axis_mismatch`, right after the existing gender block ps:7886-7888, inside `if strict_extras:`: `if cat == "fragrances" and _vd_gender_line_flip(q, c): return "gender"`. (H2) in `_descriptor_backstop_axes_verdict`, right after ps:8409-8411: `if cat == "fragrances" and _vd_gender_line_flip(q, c): return "gender"`.
- Reach of H1 (BY READING, `git grep "_selection_match("`): the selection gate of algolia, magento, noon, occ, rest_json, salla, shopify_pdp, unbxd, woocommerce adapters, ps internal callers (incl. `select_best` ps:8637, `should_cache_price` ps:9296), scripts/eval_runner.py; EXACT mode (`is_exact_match` ps:8023, no app caller). Reach of H2: `backstop_identity_verdict` -> scs `_cache_price_identity_ok` (cache read) and ps `is_price_showable` (display, ps:1877).
- Log lines: none added (the existing `[PRICE] cache_read_rejected (not_exact:gender)` INFO at scs:1266-1267 fires for a rejected cached entry: an existing line and format, which already carries the query and title it has always carried).
- Keys: none added (R-X10-5). A rejected candidate is simply not eligible; downstream is the existing path: another eligible candidate, else `select_best` None -> `_guard_rejected_this_request` + seeding + the cascade (scs:7827-7837), else the existing pending price / fallbacks.
- Failure table: the predicate is pure set arithmetic on frozensets; it cannot raise for a valid descriptor (both descriptors are built by the existing extraction before the hook runs).
- Flag-OFF identity: H1 / H2 evaluate `cat == "fragrances"` then call the predicate, which returns False after one env read; every verdict, reason, rank, cache write and log line is byte-identical to base (P10-2 with the full configuration and a table recorder).
- Deploy-visible delta with every flag at default: none (one env read per fragrance candidate evaluation; no output change).
- Test seams: env per call (monkeypatch.setenv) [prod unset]; `_GENDER_FLIP_LINES` is a module constant a PIN replaces with a recording iterable [prod: the tuple].

### X10.3 Change list (GREEN, in order)

1. Byte copy of ps into `<SP>/G-INC-1/green/` (sha256 recorded).
2. ps, after `_vd_feminine_query_unconfirmed` (ps:7798-7802): the comment block (INC-X10, the documented Eros leak, the four lines, why a table), `_GENDER_FLIP_LINES`, `_GENDER_LINE_MEN_WORDS`, `_GENDER_LINE_WOMEN_WORDS`, `listing_match_guard_enabled()`, `_vd_gender_line_flip(q, c)` exactly as X10.2. Pure ASCII.
3. ps H1: inside `_descriptor_axis_mismatch`, after the existing `return "gender"` at ps:7888, the two-line hook.
4. ps H2: inside `_descriptor_backstop_axes_verdict`, after the existing `return "gender"` at ps:8411 (outside its `if cat in ...` block, at the same indent as that `if`), the two-line hook.
5. CLAUDE.md: the X10 row (section 12.6) and the :341 sentence.
No other file. (The `_feminine_query_unconfirmed` docstring at ps:5741-5760 is NOT edited: it describes the base token rule, still true flag-OFF.)

### X10.4 Existing pins

X10.4.1 Pins that change deliberately: NONE (the flag defaults OFF; no existing test sets ENABLE_LISTING_MATCH_GUARD: grep at base = 0 hits).

X10.4.2 Pins that stay green unedited (flag OFF in their env): tests/test_variant_descriptor_golden.py (the corpus incl. vd-0000 "Versace Eros" -> "Eros Pour Femme" accepted; its env comes from the corpus `_meta.env`, test_variant_descriptor_golden.py:57-60), tests/test_variant_descriptor_backstop_axes.py, test_variant_descriptor_unit.py, test_gender_contradiction_fix.py, test_gender_gents_ladies_leak.py, test_correctness_review_pr9_fixes.py (pins the asymmetric Eros leak flag-OFF), test_correctness_coverage_review_findings.py, test_correctness_coverage_sweep_fixes.py, test_correctness_runtime_leaks.py, test_exact_gate_flag_off_parity.py, test_wrong_cheap_price_guard.py, test_variant_precision.py, test_matcher_folds_wave_a.py, every adapter suite (woocommerce / algolia / magento / occ / salla / noon / unbxd / rest_json / shopify_pdp), tests/test_w4_7_confidence_single_computation.py::test_b12_listing_count_replay_emits_no_log_record (the predicate logs nothing).

### X10.5 RED tests (tests/test_inc_x10_listing_match_guard.py; hermetic, pure functions; every row sets ENABLE_EXACT_PRICE_GATE=true and ENABLE_VARIANT_DESCRIPTOR_AXES=true [prod: ON / ON] and deletes ENABLE_GENUINE_PRICE_PRIORITY [prod: OFF]; candidate_brand as in the truth table)

| # | Test | Assertion (flag "true" unless stated) | At base | Satisfied by |
|---|---|---|---|---|
| R10-1 | test_r10_1_eros_for_women_rejected | `_selection_match(T1)` is False | True -> AssertionError | steps 2-3 |
| R10-2 | test_r10_2_eros_pour_femme_rejected | `_selection_match(T2)` is False | True | 2-3 |
| R10-3 | test_r10_3_aventus_for_her_pronoun_rejected | T12 False | True | 2-3 (pronoun side) |
| R10-4 | test_r10_4_light_blue_pour_homme_rejected | T13 False | True | 2-3 (women-default line) |
| R10-5 | test_r10_5_dylan_blue_pour_femme_rejected | T17 False | True | 2-3 |
| R10-6 | test_r10_6_select_best_skips_the_womens_listing | `select_best` over the incident-shaped set (three in-stock candidates on ONE synthetic host `https://shop.example/p/<n>` so authority ties: T1 title at 25.0, "Versace Eros EDP 100ml" at 28.0, "Versace Eros Pour Homme EDP 100ml" at 33.0; query "Versace Eros EDP", category fragrances) returns the 28.0 candidate | the 25.0 women's listing (cheapest on a tie) -> AssertionError | 2-3 |
| R10-7 | test_r10_7_only_the_womens_listing_gives_no_price | `select_best([T1 candidate], ...)` is None | the candidate | 2-3 (R-X10-5 no-price path) |
| R10-8 | test_r10_8_backstop_rejects_on_read_and_display | `backstop_identity_verdict("Versace Eros EDP", T1 title, "fragrances") == (False, "not_exact:gender")` | (True, None) | 2, 4 |
| R10-9 | test_r10_9_poisoned_cache_entry_rejected | `scs._cache_price_identity_ok({"title": T1 title, "amount": 25.0}, "Versace", "Eros EDP", "fragrances")` is False | True | 2, 4 |
| R10-10 | test_r10_10_should_cache_refuses_the_womens_listing | `should_cache_price("Versace Eros EDP", {T1 candidate dict, genuine source_method}, "fragrances")` is False | True BY READING (ps:9288-9330 runs `_selection_match`); the RED agent confirms base True on the fixture or drops the row and reports | 2-3 |
| P10-1 | test_p10_1_keep_rows_accept_flag_on (parametrized T3-T11, T14-T16, T18) | `_selection_match(row)` is True with the flag ON | green | the table must not over-reject |
| P10-2 | test_p10_2_flag_off_identity_full_config (flag values unset / "false" / " FALSE " / "0" / "garbage") | with the FULL configuration (exact gate ON, variant axes ON, genuine priority deleted) and `ps._GENDER_FLIP_LINES` replaced by a recording iterable: every truth-table row's `_selection_match` equals its base value, `select_best(R10-6 set)` returns the 25.0 candidate, `backstop_identity_verdict(T1) == (True, None)`, `_cache_price_identity_ok(T1 entry)` True, and the recorder saw ZERO iterations | green | the flag read is the predicate's first statement |
| P10-3 | test_p10_3_flag_reader_hygiene | `listing_match_guard_enabled()`: "true", " TRUE ", "1", "yes", "on" -> True; unset, "", "false", "0", "no", "garbage" -> False. Read via `getattr(ps, "listing_match_guard_enabled", None)`; absent at base -> the row asserts `callable(...)` FIRST (AssertionError at base, so this row is RED, not PIN) | RED (AssertionError) | 2 |
| P10-4 | test_p10_4_rule_is_fragrance_scoped | flag ON: `_selection_match(T1 query, T1 title, None, ...)` and with category "fashion" equal their flag-OFF values (True) | green | `cat == "fragrances"` in H1 / H2 |
| P10-5 | test_p10_5_gendered_query_never_consults_the_table | flag ON, recording table: T8 and T15 verdicts True and the recorder saw ZERO iterations | green at base (no table; the RED agent writes it so the recorder is installed with `monkeypatch.setattr(ps, "_GENDER_FLIP_LINES", rec, raising=False)`) | the query-gender guard |
| P10-6 | test_p10_6_no_new_key_on_the_winner | flag ON, R10-6 set: the returned dict `is` one of the input candidate objects and its key set equals that candidate's key set | green | R-X10-5 |

P10-3 is RED (counted with the REDs). Counts: RED 11 (R10-1..R10-10 + P10-3), PIN 5 (P10-1, P10-2, P10-4, P10-5, P10-6).

### X10.6 Mutation table (byte copies of the GREEN ps; restore + sha256; pyt.py -k, bound 600)

| M | Mutation | Killed by |
|---|---|---|
| M10-1 | delete the predicate's flag check (`if not listing_match_guard_enabled(): return False`) | P10-2 (verdicts + recorder) |
| M10-2 | `return c_side != default_side` -> `return c_side == default_side` | R10-1, P10-1 (T7, T9, T14) |
| M10-3 | delete the query-gender-word guard | P10-1 (T8: the "her" query names the aventus line; c women != men -> rejected), P10-5 |
| M10-4 | `_GENDER_LINE_WOMEN_WORDS = _GENDER_WOMEN_TOKENS` (drop the pronouns) | R10-3 |
| M10-5 | delete hook H1 | R10-1..R10-7, R10-10 |
| M10-6 | delete hook H2 | R10-8, R10-9 |
| M10-7 | H1 `cat == "fragrances" and ` removed | P10-4 |
| M10-8 | `if c_men == c_women: return False` -> `if not (c_men or c_women): return False` | P10-1 (T18: both genders read as men, women-default line -> rejected) |
| M10-9 | flag reader `in ("true", "1", "yes", "on")` -> `== "true"` | P10-3 |

### X10.7 Comm set and gates

Section 12. X10 cheapest-first: py_compile + ruff on ps; the RED file; the X10.1.10 set; the golden corpus test alone (it runs the whole corpus, the most sensitive pin); the CI-order set; the comm chunks.

### X10.8 CLAUDE.md row and owner steps

Row: "INC-X10 LISTING-MATCH-GUARD (`ENABLE_LISTING_MATCH_GUARD`, default OFF, read per call): a four-line in-repo table `_GENDER_FLIP_LINES` (Versace Eros / Versace Dylan Blue / Creed Aventus = men default; Dolce & Gabbana Light Blue = women default) lets `_vd_gender_line_flip` reject, for fragrances only, a listing that states the opposite gender of a table line when the query names the line and states no gender ('Versace Eros EDP' vs 'Versace Eros for Women EDP 100ml', the incident row e2320ca7); hooked at the selection axis core (every adapter gate, select_best, should_cache_price) and the backstop extras (cache read, display), reason word 'gender'; no new key. OFF byte-identical (pinned). Stated limits L-X10-1..L-X10-5." Owner steps (names only): the flip of ENABLE_LISTING_MATCH_GUARD on web in its own canary window (after the flip freeze lifts, in the order the owner rules); ENABLE_EXACT_PRICE_GATE and ENABLE_VARIANT_DESCRIPTOR_AXES must stay ON (both are today).

### X10.8b PROOF ON THE PHONE (after its flip window)

- Pair: Armani Acqua di Gio Profumo vs Versace Eros EDP (golden pair 3), store app or update.
- Visible: the Versace price is from a men's (or unmarked) Eros EDP listing, or Versace shows no confirmed price.
- Backing: `products[1].price.title` of the new row names no women's / Pour Femme marker; the deploy log for those minutes may carry `[PRICE] cache_read_rejected (not_exact:gender)` if the 7-day cached entry was still live (the line already exists).
- Measured before / after (hermetic, R10-6): before = the 25.0 women's listing wins a three-way authority tie; after = the 28.0 unmarked listing. This is a fixture built from the incident title, NOT the production proof: the titles of the 28.0 / 33.0 hits of 2026-11-11 were never logged, so production may land on "no confirmed price" instead.
- NOT provable in production: that no other line leaks (the table has four lines); the adapter-level category inference (woocommerce_service.py:159) is not observable from the row.

### X10.9 Stated limits

- L-X10-1: the table has four lines; any other gender-flip line (and a query naming a line without its brand words, e.g. "Light Blue EDT" or "D&G Light Blue") keeps the base behaviour (fail-open to today).
- L-X10-2: a query that states any gender word (strict or pronoun) is left to the base axes (inert by design, T8 / T15).
- L-X10-3: the line default sides are product knowledge marked [OWNER / ORCHESTRATOR READ], not measured in the repo.
- L-X10-4: rows / L2 prices saved before the flip are not rewritten; the cache-read backstop drops a poisoned L1 entry on read (R10-9), and an L2 row promoted to L1 passes the same read check (BY READING; the promotion path was not traced in this round: NOT MEASURED).
- L-X10-5: the production effect is unproven until the phone repeat; whether the adapter-level gate sees category "fragrances" (inferred, woocommerce_service.py:159) is NOT MEASURED; `select_best` in scs receives the orchestrator category either way.

### X10.10 Out of scope

Size fairness (X1); the identity the user typed; descriptor extraction; any non-fragrance category; the femme asymmetry; the golden corpus file; a symmetric token rule (the base comment's rejected design).

### X10.11 Open questions and answers to the brief

- Q-X10-a (orchestrator): ship the four-line table as is, or Eros only (the incident line) with the other three as a later data unit? The spec ships four because each is a RED + PIN row and the mechanism is the same.
- Q-X10-b (orchestrator): H2 widens the guard to the cache read and the display (needed so the 7-day cached wrong price cannot outlive the flip). If the orchestrator rules "selection only" literally, drop step 4, R10-8, R10-9 and M10-6, and state the 7-day limit.
- Brief R-X10-1: the accepting function is `_selection_match` (ps:8291-8331) via `_descriptor_axis_mismatch` (ps:7813-7895, gender at :7886-7888) and `_descriptor_selection_verdict` (ps:7898-7964), called by the woo adapter (woocommerce_service.py:226, :290) and by scs's cross-adapter `select_best` (scs:7820-7826 -> ps:8637); there is no score, the gate is boolean; the rank among accepted candidates is (in_stock, -authority, -precision, amount), and 25.0 was the cheapest of the three hits. Every gender / flanker rule and its flag: X10.1.2. The truth table: X10.1.3.
- Brief R-G1-4 matcher trace: X10.1.1.

---------------------------------------------------------------------------------------------------

## Unit INC-X8 PHASE2-CACHED-RATING (dark: ENABLE_PHASE2_CACHED_RATING; RED file tests/test_inc_x8_phase2_cached_rating.py)

### X8.0 What the unit does

Flag ON: a product whose Phase 2 the residual guard skipped gets `rating`, `review_count`, `rating_verified`, `rating_source` from its in-memory shopping rows when those rows hold an acceptable rating (the free tier of `get_verified_rating`); otherwise the base default dict. One INFO line per such product. No network, LLM, await or new key.

### X8.1 Base state (measured)

| What | Where | Fact |
|---|---|---|
| Rows read before the skip | scs:6469-6481 | `retailer_ratings = collect_retailer_ratings(full_name, view)`; with ENABLE_FACTCHECK_SHOPPING_KEY (factcheck_shopping_key_enabled) ON the view is `_fc_view = {full_name: self._shopping_items_cache.get(_fc_key, [])}`, else `_fc_view = None` and the whole cache. |
| The skip | scs:6484-6503 | `_phase2_skip = False` (:6491); `if _flag_on("ENABLE_PHASE2_RESIDUAL_GUARD"):` deadline `self._compare_deadline`; `_residual < _phase2_min_residual_seconds()` (scs:1892-1894, `_float_knob("PHASE2_MIN_RESIDUAL_SECONDS", 8.0)`) -> `_phase2_skip = True`, `self._phase2_skipped = True`, INFO `[L2.6] phase 2 skipped residual=%.1fs product=%d` (slot or 0). |
| Rating task | scs:6517-6535 | `_rating_with_cap()` = `wait_for(self._get_verified_rating(full_name[, cache_view=_fc_view]), _PHASE2_RATING_TIMEOUT)` (scs:2054 = 4.0); appended only `if not _phase2_skip and not _kb_full` (scs:6533). |
| Refill | scs:6558-6562 | smart fallback also gated by `not _phase2_skip and not _kb_full`. |
| Result loop | scs:6698-6712 | `rating_data` = default dict; replaced by the `_rating_data` task result; then the four keys are written from `rating_data` (:6709-6712); `_kb_full` overrides rating / review_count (:6713-6715). |
| After | scs:6717-6757 | ENABLE_JSONLD_RATING branch, else `_apply_gpt_review_aggregate_fallback(result)` (:6743; fills ONLY when `result["rating"] is None`, scs:575-589); `reviews.verified_rating` injection when `rating_data.get("rating")` (:6746-6752); expert_pros / cons from rating_data. |
| Wrapper | scs:9176-9181 `_get_verified_rating` | `get_verified_rating(full_name, self._shopping_items_cache if cache_view is None else cache_view, track_serper_cost_fn=...)`. |
| Who fills the rows | `_get_price` (scs:7060): Tier-1 shopping writes `self._shopping_items_cache[full_name] = shopping_items` (scs:7919-7920), supplements `[]` (:7885), iHerb a one-row rating (:8766) | Tier 1 runs BEFORE the BH adapter consume (the consume is awaited at scs:8289, after the Tier-1 block scs:7880-7920), so a product priced by an adapter direct hit (Versace in e2320ca7) still had its Tier-1 rows in memory, unless the genuine-priority clamp emptied them (scs:7905-7914). Whether the 2026-11-11 rows carried a usable rating: NOT MEASURED (rows are not saved). Keys: `_get_price`'s `full_name` vs `_fetch_product_data`'s `full_name` are the same string BY READING (both brand+name+variant), which the existing Phase-2 call already relies on. |
| Entry resets | scs:3349, 4299, 4941 | `self._shopping_items_cache = {}` per instance / entry. |

X8.1.2 The tiers of `get_verified_rating` (rs:273-333) and its callee (R-X8-1):

| Tier | Where | Network / LLM | Returns |
|---|---|---|---|
| 0 free reuse | rs:285-291 `shopping_items_cache.get(full_name, [])` -> `extract_rating_from_shopping(full_name, rows)`; accepted iff `result and result.get("rating") and result.get("rating_source", {}).get("confidence") != "low"` | NONE (pure, synchronous; rs:127-270 loops the rows: `normalize_words`, `is_accessory`, `strict_title_match`, `numbers_match` from ps, `_rating_source_denied` (D03, flag-gated deny list), `get_rating_tier`, `datetime.now()` for `retrieved_at`) | consensus (>= 3 sellers same rating+count, rs:203-228): `rating_verified` True, source `Google Shopping (product aggregate)`, extract_method `google_shopping_consensus`, confidence high; tier1 / tier2 (rs:231-268): verified True, `<source> via Google Shopping`, extract_method `google_shopping`, confidence high / medium; tier3 (>1000 reviews marketplace): verified False, confidence low (REJECTED by the acceptance rule); else the empty dict |
| 1 US shopping search | rs:293-333 | NETWORK: `httpx.AsyncClient(timeout=10.0)` POST google.serper.dev/shopping gl=us (1 credit), `record_usage("serper")` | `extract_rating_from_shopping` over the US rows (any confidence) or empty |
| LLM | none in rs | the GPT review-aggregate estimate is a separate scs fallback (`_apply_gpt_review_aggregate_fallback`, rating_derived, count nulled) | |

`retailer_ratings` (computed before the skip, rs:86-124) is a per-source list `{source, rating, review_count}` used by `verify_review_sentiment`; it does NOT carry the chosen rating, the tier choice or `rating_source`, so it cannot fill the result keys by itself (R-X8-1 answer). The unit therefore calls the tier-0 function itself.

X8.1.3 Production flags (ledger.md:316): ENABLE_PHASE2_RESIDUAL_GUARD ON; PHASE2_MIN_RESIDUAL_SECONDS not in the printed knob list -> unset -> 8.0 (BY READING the line, which printed numeric knobs that were set); ENABLE_FACTCHECK_SHOPPING_KEY not listed ON (assumed OFF; the unit handles both views); ENABLE_JSONLD_RATING OFF (S81 flags OFF); ENABLE_KB_FIRST_SERVE OFF (so `_kb_full` False in production).

X8.1.10 Base pass state (DEFERRED TO RED):
```
PYTHONIOENCODING=utf-8 C:/Users/SynAckITPC/Documents/AI/.venv-qaren/Scripts/python.exe <SP>/harness/pyt.py --bound 600 --tag inc-x8-base --log <SP>/G-INC-1/red/x8_base.log --cwd C:/Users/SynAckITPC/Documents/AI/sc-inc-g1 -- tests/test_s75_fanout_starve.py tests/test_s78_tier_fill_residual_guard.py tests/test_s75_fanout_identity.py tests/test_s81_s18_kb_first_serve.py
```
NOT MEASURED in this round.

### X8.2 Contract

- Flag: `ENABLE_PHASE2_CACHED_RATING` (default OFF, read per call by `_phase2_cached_rating_enabled()` = `_flag_on("ENABLE_PHASE2_CACHED_RATING")`, the FIRST conjunct of the new block's condition). It acts only when ENABLE_PHASE2_RESIDUAL_GUARD skipped Phase 2 for this product (`_phase2_skip` True) and `_kb_full` is False. Knobs: none new (PHASE2_MIN_RESIDUAL_SECONDS, `_PHASE2_RATING_TIMEOUT` unchanged).
- New module helpers in scs, right after `_phase2_min_residual_seconds` (scs:1892-1894):
```
def _phase2_cached_rating_enabled() -> bool:
    return _flag_on("ENABLE_PHASE2_CACHED_RATING")

def _phase2_cached_rating(full_name, cache):
    """INC-X8: the free tier of get_verified_rating (rs:285-291), nothing else."""
    empty = {"rating": None, "review_count": None, "rating_verified": False, "rating_source": None}
    rows = cache.get(full_name, []) if isinstance(cache, dict) else []
    if not rows:
        return empty
    found = extract_rating_from_shopping(full_name, rows)
    if found and found.get("rating") and (found.get("rating_source") or {}).get("confidence") != "low":
        return found
    return empty
```
- The block, inserted between the Phase-2 result loop (ends scs:6707) and `result["rating"] = rating_data.get("rating")` (scs:6709):
```
        if _phase2_cached_rating_enabled() and _phase2_skip and not _kb_full:
            try:
                rating_data = _phase2_cached_rating(
                    full_name, self._shopping_items_cache if _fc_view is None else _fc_view)
                _x8_outcome = "hit" if rating_data.get("rating") else "miss"
            except Exception as _x8_err:  # noqa: BLE001 -- a rating must never break the product
                rating_data = {"rating": None, "review_count": None, "rating_verified": False, "rating_source": None}
                _x8_outcome = "error:" + type(_x8_err).__name__
            logger.info("[L2.6] phase 2 cached rating outcome=%s product=%d",
                        _x8_outcome, partial_slot if partial_slot is not None else 0)
```
  (The INFO sits outside the except arm: the house rule allows ERROR only inside except arms; this is INFO with a closed-set word + a type name + an int.)
- Result keys: the same four keys the loop writes (scs:6709-6712); a hit carries exactly what a normal tier-0 hit carries (same function, same acceptance), incl. `rating_source.extract_method` "google_shopping" / "google_shopping_consensus" and `rating_verified` True; `reviews.verified_rating` is injected by the existing scs:6746-6752 code when reviews is a dict. No new key.
- Log line (new): `[L2.6] phase 2 cached rating outcome=<hit|miss|error:TypeName> product=<int>` at most once per product per compare, only with the flag ON and Phase 2 skipped. Prefix chosen so the T18 pin's `prefix="[L2.6] phase 2 skipped"` filter (tests/test_s75_fanout_starve.py:876) never counts it.
- Failure table: rows not a dict / missing -> empty -> base behaviour; `extract_rating_from_shopping` raising (not expected; caught) -> empty + `outcome=error:<Type>`; tier3-only rows -> empty (confidence low, as in `get_verified_rating`).
- No await, no network, no LLM: the added work is one synchronous pass over the product's in-memory shopping rows (one Serper response, already parsed; the same pass `get_verified_rating` makes first on the normal path; the row cap was not measured).
- Flag-OFF identity: the condition's first conjunct is the env read; OFF -> the block is skipped; the skip block, the gather, the loop and everything after are byte-identical (P8-1 with the guard ON, knob 8, a 2 s residual, rows holding a tier-1 rating, a call recorder on `_get_verified_rating` and on `scs.extract_rating_from_shopping`).
- Deploy-visible delta with every flag at default: none (one env read per product).
- Test seams: `svc._compare_deadline` [prod: monotonic deadline set at entry]; `svc._shopping_items_cache` filled by a `_get_price` stub as `_get_price` does [prod: Tier-1 rows]; env per call [prod: guard ON, cached-rating flag unset].

### X8.3 Change list (GREEN, in order; after the X9 hunk in the same file)

1. Byte copy of scs (taken once for X9 + X8).
2. scs: the two helpers after `_phase2_min_residual_seconds` (scs:1892-1894), exactly as X8.2 (no new import: `extract_rating_from_shopping` is already imported at scs:1537-1545).
3. scs: the block between scs:6707 and scs:6709, exactly as X8.2.
4. CLAUDE.md: the X8 row and the :341 sentence.
No other file.

### X8.4 Existing pins

X8.4.1 deliberate changes: NONE (flag default OFF; grep at base: no test sets ENABLE_PHASE2_CACHED_RATING).
X8.4.2 stay green unedited: tests/test_s75_fanout_starve.py (T18 skip / runs / off, FY4 resets, the knob hygiene rows; T18 patches `scs.collect_retailer_ratings` and `_get_verified_rating` and never sets the new flag), tests/test_s78_tier_fill_residual_guard.py, tests/test_s75_fanout_identity.py, tests/test_s81_s18_kb_first_serve.py (H6), tests/test_s81_d14_live_robots.py and tests/test_s81_s17_kb_ingest.py (they name the guard), tests/test_s78_all_timeout_cap_as_timeout.py, every `_fetch_product_data` driver (test_partial_specs_stash_on_price_timeout.py, test_comparison_response_image_url.py, ...).

### X8.5 RED tests (tests/test_inc_x8_phase2_cached_rating.py; hermetic; the driver = the s75 `_phase_mocks` pattern (tests/test_s75_fanout_starve.py:235-271; `_NoRead` :226-232) re-implemented in the RED file, except that the `_get_price` stub writes `svc._shopping_items_cache[full_name] = ROWS` and `extract_rating_from_shopping` is NOT patched; every row runs `_fetch_product_data(dict(PRODUCT), "bahrain", True, True, nocache=True)` under `asyncio.wait_for(..., 20.0)`)

ROWS = synthetic Serper shopping rows whose titles match the product name (the RED agent builds them so that P8-0 holds), e.g. three rows with source "Amazon.com" / "Noon" / "Sephora" (RATING_TIER_1 words, rs:32-36), rating 4.6, ratingCount 1200. TIER3_ROWS = rows on "eBay" with > 1000 reviews only.

| # | Test | Assertion | At base | Satisfied by |
|---|---|---|---|---|
| P8-0 | test_p8_0_fixture_is_a_tier0_hit | `extract_rating_from_shopping(full_name, ROWS)` has rating 4.6, review_count 1200, confidence high, extract_method google_shopping; with TIER3_ROWS confidence low | green | fixture sanity (the REDs fail for the right reason) |
| R8-1 | test_r8_1_skipped_product_gets_the_in_memory_rating | guard ON, knob "8", deadline now+2.0, X8 flag "true": result rating 4.6, review_count 1200, rating_verified True, rating_source.extract_method "google_shopping", rating_source.confidence "high"; the `_get_verified_rating` recorder saw 0 calls; exactly one `[L2.6] phase 2 skipped` and one `[L2.6] phase 2 cached rating outcome=hit product=` record | rating None (the GPT-aggregate fallback has no reviews) -> AssertionError | X8.3 steps 2-3 |
| R8-2 | test_r8_2_padded_flag_value | same with " TRUE " | AssertionError | step 2 (`_flag_on` strip/lower) |
| R8-3 | test_r8_3_tier3_rows_give_no_rating_and_a_miss_line | X8 ON, TIER3_ROWS: rating None, rating_verified False, one `outcome=miss` record | no outcome line -> AssertionError | acceptance rule |
| R8-4 | test_r8_4_extractor_error_is_contained | X8 ON, `scs.extract_rating_from_shopping` patched to raise RuntimeError: `_fetch_product_data` returns, rating None, one `outcome=error:RuntimeError` record | no line -> AssertionError | the try / except |
| R8-5 | test_r8_5_factcheck_view_is_used | X8 ON + ENABLE_FACTCHECK_SHOPPING_KEY "true": rows written under `_shopping_cache_key_or(...)` (the W4-7 key) still yield the 4.6 hit | AssertionError | `_fc_view` branch |
| P8-1 | test_p8_1_flag_off_identity_full_config (unset / "false" / " FALSE " / "0" / "garbage") | guard ON, knob 8, deadline now+2, ROWS present: rating None, `_get_verified_rating` 0 calls, a recorder wrapping `scs.extract_rating_from_shopping` 0 calls, no `phase 2 cached rating` record, exactly the T18 skip record | green | first-conjunct flag read |
| P8-2 | test_p8_2_not_skipped_runs_phase2_as_today | X8 ON, deadline now+100 (no skip), the `_get_verified_rating` stub returns rating 3.9 / count 77: result rating 3.9 / 77, stub called once, extract recorder 0 calls, no cached-rating record | green | `_phase2_skip` conjunct |
| P8-3 | test_p8_3_guard_off_never_reads | X8 ON, guard unset, `svc._compare_deadline = _NoRead()` (the s75 stand-in that raises on any read): Phase 2 runs (stub called once), no cached-rating record | green | the X8 block reads no deadline |
| P8-4 | test_p8_4_refill_stays_skipped | X8 ON, skip, missing critical specs: the `_smart_fallback_extract` recorder saw 0 calls | green | R-X8-2 |
| P8-5 | test_p8_5_no_new_keys | X8 ON hit vs a normal Phase-2 tier-0 hit produced by the REAL `get_verified_rating` with the same ROWS (no skip; SERPER_API_KEY deleted so tier 1 cannot run): the two results have the same key set and equal rating / review_count / rating_verified / rating_source minus `retrieved_at` | green at base for the normal half; the skip half is RED-gated, so the row is RED (AssertionError at base on the skip half) | same function, same marker |

Counts: RED 6 (R8-1..R8-5, P8-5), PIN 5 (P8-0..P8-4).

Driver notes for the RED agent: read the `full_name` formula `_fetch_product_data` uses (scs:5962+) and key ROWS by it (and by `_shopping_cache_key_or(brand, name, variant, full_name)` for R8-5); `rating_service.SERPER_API_KEY` is a module constant read at import (rs:29) and is None under the conftest sanitizer: P8-5 asserts that before relying on it.

### X8.6 Mutation table (byte copies of the GREEN scs; restore + sha256; pyt.py -k, bound 600)

| M | Mutation | Killed by |
|---|---|---|
| M8-1 | drop `_phase2_cached_rating_enabled() and ` | P8-1 |
| M8-2 | drop ` and _phase2_skip` | P8-2 (the in-memory 4.6 replaces the Phase-2 3.9) |
| M8-3 | acceptance `!= "low"` removed (accept any confidence) | R8-3 |
| M8-4 | replace the helper call with `await self._get_verified_rating(full_name)` | R8-1 (recorder 0 calls) |
| M8-5 | remove the try / except (call bare) | R8-4 (the RuntimeError escapes) |
| M8-6 | always pass `self._shopping_items_cache` (ignore `_fc_view`) | R8-5 |
| M8-7 | drop ` and not _kb_full` | NOT killed by the rows above (needs a KB full-hit fixture); reported as a survivor for a ruling: in production `_kb_full` is False (ENABLE_KB_FIRST_SERVE OFF) and the S81-18 override at scs:6713-6715 rewrites rating / review_count after the block anyway |

### X8.7 Comm set and gates

Section 12. X8 cheapest-first: py_compile + ruff on scs; the RED file; tests/test_s75_fanout_starve.py alone (the T18 / FY rows are the closest pins); the X8.1.10 set; the CI-order set; the comm chunks.

### X8.8 CLAUDE.md row and owner steps

Row: "INC-X8 PHASE2-CACHED-RATING (`ENABLE_PHASE2_CACHED_RATING`, default OFF, read per call): when ENABLE_PHASE2_RESIDUAL_GUARD skips Phase 2 for a product, `_phase2_cached_rating` gives it the rating its in-memory shopping rows hold (the free tier of `get_verified_rating`: `extract_rating_from_shopping` + the not-low acceptance; same keys, same `rating_source` marker), with one INFO `[L2.6] phase 2 cached rating outcome=<hit|miss|error:T> product=<n>`; no network, LLM or await; the smart-fallback refill stays skipped; ENABLE_JSONLD_RATING untouched. OFF byte-identical (pinned). Stated limits L-X8-1..L-X8-3." Owner steps (names only): the flip of ENABLE_PHASE2_CACHED_RATING on web in its own canary window; it only acts while ENABLE_PHASE2_RESIDUAL_GUARD is ON (it is).

### X8.8b PROOF ON THE PHONE (after its flip window)

- Pair: Creed Aventus EDP vs Parfums de Marly Layton EDP (golden pair 1).
- Visible: Reviews shows a star average with a count for both products.
- Backing: the new row has `products[i].rating_source` and `rating_count` / `review_count` filled for both; the deploy log for those minutes shows `[L2.6] phase 2 cached rating outcome=hit` for any product whose Phase 2 was skipped (or no `phase 2 skipped` line at all, in which case Phase 2 ran normally and this unit did nothing for that product).
- Measured before / after (hermetic): R8-1 before = rating None with the skip, after = 4.6 / 1200 verified. A hermetic measurement is NOT the production proof.
- NOT provable in production / uncertain: the effect exists only if those products' Tier-1 shopping rows carry a rating from a tier-1 / tier-2 / consensus source; the rows of 2026-11-11 were not saved, so whether this unit would have filled ratings for the four skipped products is unknown.

### X8.9 Stated limits

- L-X8-1: the US shopping search tier (one Serper credit, network) stays skipped under the guard: products whose Bahrain rows hold no tier-1 / tier-2 rating keep no verified rating.
- L-X8-2: the effect in production is uncertain (rows may hold no rating; the genuine-priority clamp can empty them).
- L-X8-3: M8-7 survives the hermetic rows (KB full-hit path not fixtured; inert in production).

### X8.10 Out of scope

ENABLE_JSONLD_RATING and its reader (skeptic 2 item 2), the guard threshold PHASE2_MIN_RESIDUAL_SECONDS, `_PHASE2_RATING_TIMEOUT`, the smart-fallback refill, the GPT review-aggregate fallback, `retailer_ratings`.

### X8.11 Open questions and answers to the brief

- Q-X8-a (orchestrator): accept M8-7 as a stated limit, or require a KB full-hit fixture row?
- Brief R-X8-1: tier table X8.1.2: tier 0 reads only the in-memory rows (pure, sync); tier 1 is one network call (Serper shopping gl=us); no tier calls an LLM; `retailer_ratings` cannot fill the result (no `rating_source`, no tier choice).

---------------------------------------------------------------------------------------------------

## Unit INC-X2a IMAGE-TIER-TIMING (unflagged, log-only under R-A1; RED file tests/test_inc_x2a_image_tier_timing.py)

### X2a.0 What the unit does

Adds per-tier timing lines and a cancellation line to `get_product_image_url`. Nothing else.

### X2a.1 Base state (measured)

| What | Where | Fact |
|---|---|---|
| The race | scs:6026-6043 `_PHASE1_TIMEOUTS["image_url"] = 5.0`; scs:6269-6283 the task: `asyncio.wait_for(_timed_task("image_url", kb_serve.served(...) if (_kb and _kb["image_url"]) else get_product_image_url(full_name, region=region, page_scrape_image=None, organic_results=..., search_payload=unified_search), stage_timings), timeout=5.0)` | the coroutine is created after the unified search returned (it is an argument), so the 5 s clock starts when the gather schedules it (scs:6285-6286). |
| Timeout line | scs:6317-6320 | WARNING `[L2.6] Phase 1 race timeout for %s (limit %.1fs)` |
| `_timed_task` | scs:1417-1428 | `t = perf_counter()` at first run, `finally: timings[label_ms] = ...`: `image_url_ms` = start -> the moment the cancelled coroutine finished unwinding. The incident rows' 5,300-6,997 ms for a 5,000 ms cap = 0.3-2.0 s between the deadline and the end of the unwind. |
| KB tier | scs:6270 | a KB image is served by scs (S81-18 H5) INSTEAD of calling `get_product_image_url`, only with ENABLE_KB_FIRST_SERVE (OFF in prod). There is NO KB tier inside img (the brief's "KB" tier is this scs branch). |
| Tier 1.5 piggyback | img:249-252 | sync; production always passes `page_scrape_image=None` (scs:6272), so it never hits on the race path; INFO only on hit. |
| Tier 1.5b search payload | img:254-261 `extract_image_from_search` (img:83-127) | sync, pure; INFO only on hit. |
| Tier 1 budget gate | img:263-264 `try_consume_serper_image_credit(1)` (api_budget_service.py:1187-1230) | SYNCHRONOUS Redis `incrby` (+ `expire` / `decrby`) on the event loop; no log on grant. |
| Tier 1 Serper Images | img:265-280 `await search_images(name, num_results=1)` (serper_service.py:1201-1240: `_active_serper_key`, `_serper_budget_ok`, `async with httpx.AsyncClient(timeout=_serper_timeout())`, `_serper_post`, `_record_usage_async`) | INFO only on hit; `except Exception` -> WARNING with the repr. |
| Tier 3 LLM pick | img:282-291 `await extract_image_via_gpt(name, organic_results)` (img:154-215, routed via `_llm_router.route("image_tier3", ...)`) | INFO only on hit; the callee catches its own errors (WARNING) and returns None. |
| Final | img:293-295 | INFO `[image] All tiers exhausted ...` |
| Why no line was logged for comparisons 2 and 3 (BY READING) | | every existing line is a hit line, an exception line or the final line; a call cancelled while awaiting `search_images` (or blocked in the sync budget gate, then cancelled at the next await) logs NOTHING. That matches the log (no `[image]` line). Which tier was in flight is exactly what the unit measures. |
| Cancellation points | | a CancelledError can land only at an await: inside `search_images` (incl. the `async with` client exit) or inside `extract_image_via_gpt`; the sync tiers and the Redis gate cannot be interrupted, so a slow gate delays the cancellation to the next await. Python 3.12 `asyncio.wait_for` cancels the inner task and waits for it to finish before raising TimeoutError (BY READING CPython 3.12 semantics; NOT re-measured on the pinned venv in this read-only round). |
| Imports | img:33-46 | `from __future__ import annotations`, json, logging, typing; no `asyncio`, no `time` yet. |
| Callers | `git grep get_product_image_url` | only scs:1591 (import) / scs:6270. |
| Source scanners of img | tests/test_model_config_enforced.py:26,136-158 (create-site census), tests/test_prompt_fence.py:809 and tests/w4_11_prompt_digest_recorder.py:91 (the Tier-3 prompt digest), tests/test_s81_s06_anthropic_router.py:47,2513 (route census: `extract_image_via_gpt` -> ["image_tier3"]), tests/test_s81_d03_deny_and_guards.py:150,2129, tests/test_s81_s22b_self_critique_retire.py:93, tests/fixtures/legal_s78.json:284 (processor module path) | the unit edits only `get_product_image_url`: no prompt, no create site, no route call, no model literal, no host. |
| Log assertions on img | `git grep caplog` over tests/test_image_service*.py, test_image_knowledge_graph_tier.py: none; no test asserts an empty caplog around an image call (the two `caplog.records == []` pins are tests/test_s78_serper_key_memo.py:615 and tests/test_w4_7_confidence_single_computation.py:700, neither reaches img) | |

X2a.1.10 Base pass state (DEFERRED TO RED):
```
PYTHONIOENCODING=utf-8 C:/Users/SynAckITPC/Documents/AI/.venv-qaren/Scripts/python.exe <SP>/harness/pyt.py --bound 600 --tag inc-x2a-base --log <SP>/G-INC-1/red/x2a_base.log --cwd C:/Users/SynAckITPC/Documents/AI/sc-inc-g1 -- tests/test_image_service.py tests/test_image_service_edges.py tests/test_image_service_longtail.py tests/test_image_knowledge_graph_tier.py tests/test_comparison_response_image_url.py tests/test_model_config_enforced.py tests/test_prompt_fence.py
```
NOT MEASURED in this round.

### X2a.2 Contract

- Flag: none (log-only, R-A1 / R-X2a-2). Knobs: none.
- Imports added to img: `import asyncio`, `import time` (stdlib).
- New module names in img (above `get_product_image_url`): `_log_img_tier(tier: str, outcome: str, t0: float) -> None` = `logger.info("[IMG_TIER] tier=%s outcome=%s ms=%d", tier, outcome, int((time.perf_counter() - t0) * 1000))`.
- Tier names (constants, closed): `piggyback` (Tier 1.5), `search_payload` (Tier 1.5b), `serper_budget` (the sync Redis credit gate), `serper_images` (Tier 1), `llm_pick` (Tier 3). Outcomes (closed): `hit`, `miss`, `skipped` (the tier's input absent: no page image, `search_payload` None, budget denied for `serper_images`, no organic results for `llm_pick`), `error:<ExceptionClassName>` (only where the base code already catches: the Tier-1 and Tier-3 `except Exception` arms). `serper_budget`: `hit` = granted, `miss` = denied.
- New lines (INFO, logger `app.services.image_service`): `[IMG_TIER] tier=<name> outcome=<outcome> ms=<int>` once per tier reached; `[IMG_TIER] cancelled tier=<name of the tier in flight> tier_ms=<int> total_ms=<int>` once if the call is cancelled. No product name, URL, query or payload text.
- Shape of the change inside `get_product_image_url` (after the empty-name return at img:245-247, which logs nothing): `_t_call = time.perf_counter()`; `_inflight = ["piggyback", _t_call]`; the whole tier cascade (img:249-295) moves inside `try:` with, before each tier, `_inflight[0] = <tier>; _inflight[1] = time.perf_counter()`; after each tier's existing decision, one `_log_img_tier(...)` call placed BEFORE the existing `[image]` hit line / return; `if try_consume_serper_image_credit(1):` becomes `_granted = try_consume_serper_image_credit(1)` + `_log_img_tier("serper_budget", "hit" if _granted else "miss", ...)` + `if _granted:` (the same single call, same order); then
```
    except asyncio.CancelledError:
        logger.info("[IMG_TIER] cancelled tier=%s tier_ms=%d total_ms=%d",
                    _inflight[0], int((time.perf_counter() - _inflight[1]) * 1000),
                    int((time.perf_counter() - _t_call) * 1000))
        raise
```
  The handler contains no await and ends with a bare `raise`. Existing `except Exception` arms do not catch CancelledError (BaseException in 3.12), so they are unchanged.
- The deadline gap (R-X2a-1 third line): measurable WITHOUT touching the race as `total_ms - 5000` on the cancelled line (the cap is the scs constant 5.0); it includes the unwind of the awaited call (e.g. the `async with httpx.AsyncClient` exit inside `search_images`); separating delivery from unwind would need a line inside serper_service, which is out of footprint (L-X2a-2). The row's `stage_timings.image_url_ms` (scs `_timed_task`) is written right after, so the relay can compare both.
- No behaviour change: the same calls in the same order with the same arguments, the same return values, the same exceptions, the same existing log lines (text unchanged).
- Failure table: `time.perf_counter` cannot fail; the logging calls are INFO with %-args (a logging error is handled by the logging module, not raised).
- Log volume (exact upper bound): a call that runs to the end logs 5 tier lines; a call that hits at tier k logs k lines (piggyback is always `skipped` in production because scs passes `page_scrape_image=None`); a cancelled call logs the lines of the tiers it finished + 1 cancelled line (at most 4 + 1). Two products per comparison -> at most 10 `[IMG_TIER]` lines per comparison; zero when a KB image is served (ENABLE_KB_FIRST_SERVE, OFF).
- DEPLOY-VISIBLE DELTA (the main invariant, exact): new INFO lines with the two `[IMG_TIER]` prefixes in the web service log (at most 10 per comparison); nothing else (responses, timings, Serper / LLM calls, Redis counters, existing lines all unchanged).
- Test seams: `image_service.search_images`, `image_service.try_consume_serper_image_credit`, `image_service.extract_image_via_gpt` are module attributes looked up at call time (the existing image tests patch them the same way) [prod: the real functions].

### X2a.3 Change list (GREEN, in order)

1. Byte copy of img.
2. img: the two stdlib imports after `import logging` (img:36).
3. img: `_log_img_tier` above `get_product_image_url` (between the end of `extract_image_via_gpt`, img:215, and the "Orchestrator" banner).
4. img: the bookkeeping, the per-tier lines and the CancelledError arm inside `get_product_image_url` exactly as X2a.2 (re-indentation of img:249-295 by four spaces inside the `try:` is expected; no other line of the file changes).
5. CLAUDE.md: the X2a row.
No other file.

### X2a.4 Existing pins

X2a.4.1 deliberate changes: NONE (no test asserts the absence of image_service INFO records, measured above).
X2a.4.2 stay green unedited: tests/test_image_service.py, test_image_service_edges.py, test_image_service_longtail.py, test_image_knowledge_graph_tier.py, test_comparison_response_image_url.py, test_model_config_enforced.py, test_prompt_fence.py (+ tests/w4_11_prompt_digest_recorder.py), test_s81_s06_anthropic_router.py (the route census: no route call added), test_s81_d03_deny_and_guards.py, test_s81_s22b_self_critique_retire.py, tests/test_openai_key_log_hygiene_s69.py and tests/test_sentry_channels_u8d_unit.py (log hygiene scanners: the new lines are INFO with %s / %d and no exception text).

### X2a.5 RED tests (tests/test_inc_x2a_image_tier_timing.py; hermetic; the three tier callables patched on the module with call recorders; caplog at INFO on `app.services.image_service`; the product name is a sentinel built at run time)

Regex TIER = `^\[IMG_TIER\] tier=(piggyback|search_payload|serper_budget|serper_images|llm_pick) outcome=(hit|miss|skipped|error:[A-Za-z_][A-Za-z0-9_]*) ms=\d+$`; CANCEL = `^\[IMG_TIER\] cancelled tier=(serper_images|llm_pick) tier_ms=\d+ total_ms=\d+$`.

| # | Test | Assertion | At base | Satisfied by |
|---|---|---|---|---|
| R2-1 | test_r2_1_search_payload_hit_lines | payload with a knowledgeGraph image: `[IMG_TIER]` records == [piggyback skipped, search_payload hit] in order, each matching TIER | no records -> AssertionError | step 4 |
| R2-2 | test_r2_2_serper_hit_lines | payload None, budget granted, search_images returns one image: [piggyback skipped, search_payload skipped, serper_budget hit, serper_images hit] | AssertionError | 4 |
| R2-3 | test_r2_3_all_miss_lines | budget granted, empty images, organic results, gpt returns None: [... serper_images miss, llm_pick miss] (5 records) | AssertionError | 4 |
| R2-4 | test_r2_4_error_and_denied_outcomes | (a) search_images raises RuntimeError -> `serper_images outcome=error:RuntimeError`; (b) budget denied -> `serper_budget outcome=miss` then `serper_images outcome=skipped` | AssertionError | 4 |
| R2-5 | test_r2_5_cancel_line_names_the_tier_in_flight | search_images stub awaits a never-set Event; `asyncio.wait_for(get_product_image_url(...), 0.2)`: exactly one CANCEL record, tier serper_images, tier_ms <= total_ms (ints) | AssertionError | 4 (handler) |
| R2-6 | test_r2_6_lines_carry_no_name_or_url | over R2-1..R2-5's paths: at least one `[IMG_TIER]` record exists, every one matches TIER or CANCEL, and none contains the sentinel name, "http" or the payload text | no record -> AssertionError | 3-4 |
| R2-7 | test_r2_7_handler_has_no_await_and_reraises | ast over img source: `get_product_image_url` has an `except asyncio.CancelledError` handler (asserted first), its body contains no `Await` node and its last statement is a bare `Raise` | no handler -> AssertionError | 4 |
| P2-1 | test_p2_1_kg_hit_calls_nothing_paid | R2-1 path: budget / search / gpt recorders 0 calls; return value equals the KG URL | green | no behaviour change |
| P2-2 | test_p2_2_serper_hit_call_order | R2-2 path: budget called once with (1,), search once with (name,) / {num_results: 1}, gpt 0; return = the image URL stripped | green | |
| P2-3 | test_p2_3_all_miss_call_order | R2-3 path: budget, search, gpt each once in that order; return None; the existing `[image] All tiers exhausted` record present | green | |
| P2-4 | test_p2_4_budget_denied | search 0 calls, gpt 1 call | green | |
| P2-5 | test_p2_5_search_raises_still_tries_gpt | search raises RuntimeError: the existing WARNING `[image] Tier 1 Serper Images raised` present, gpt called once | green | |
| P2-6 | test_p2_6_cancel_propagates | R2-5 path: the caller gets `asyncio.TimeoutError`; the stub recorded a CancelledError; gpt 0 calls | green | the bare raise |
| P2-7 | test_p2_7_empty_name | `get_product_image_url("  ")` is None, 0 calls, no `[IMG_TIER]` record | green | |

Counts: RED 7, PIN 7.

### X2a.6 Mutation table (byte copies of the GREEN img; restore + sha256; pyt.py -k, bound 600)

| M | Mutation | Killed by |
|---|---|---|
| M2-1 | delete the bare `raise` in the CancelledError arm | P2-6 (3.12 `wait_for` then returns None instead of raising TimeoutError, BY READING `asyncio.timeouts`; confirmed at RED), R2-7 |
| M2-2 | add `name[:60]` to the tier line arguments (`"... ms=%d %s"`) | R2-6 |
| M2-3 | move the Tier-1 block above Tier 1.5b | P2-1 (budget / search called on a KG hit), R2-1 |
| M2-4 | cancelled line reads a constant tier ("piggyback") | R2-5 |
| M2-5 | insert `await asyncio.sleep(0)` in the handler before `raise` | R2-7 |
| M2-6 | log `serper_budget` outcome "hit" unconditionally | R2-4 (b) |

### X2a.7 Comm set and gates

Section 12. X2a cheapest-first: py_compile + ruff on img; the RED file; the X2a.1.10 set; the CI-order set; the comm chunks.

### X2a.8 CLAUDE.md row and owner steps

Row: "INC-X2a IMAGE-TIER-TIMING (no flag; log-only under R-A1): `get_product_image_url` logs `[IMG_TIER] tier=<piggyback|search_payload|serper_budget|serper_images|llm_pick> outcome=<hit|miss|skipped|error:T> ms=<n>` per tier reached and `[IMG_TIER] cancelled tier=<t> tier_ms=<n> total_ms=<n>` when the 5 s Phase-1 race cancels it (no name, URL or query; at most 10 lines per comparison); the same calls, order, returns and exceptions (the handler has no await and re-raises). It is the measurement INC-X2 (photo budget) is designed from. Stated limits L-X2a-1..L-X2a-3." Owner steps: none; the relay reads the lines (8b).

### X2a.8b PROOF (a measurement; nothing on the phone)

- Three production comparisons after the deploy (any pairs; golden pairs 2 and 3 reproduced the image timeouts). The relay filters the deploy log for the prefixes `[IMG_TIER] tier=` and `[IMG_TIER] cancelled tier=` together with `[L2.6] Phase 1 race timeout for image_url`, and reads the rows' `stage_timings_ms.image_url_ms`.
- Acceptance: the lines appear for the three comparisons; for every image race timeout there is a `cancelled` line naming the tier in flight; `total_ms - 5000` gives the late-cancellation gap (compare with `image_url_ms`).
- R-X2a-3 read-back for the PR body: the exact prefixes above.
- NOT provable: why a tier was slow (Serper latency vs a blocked loop vs the sync Redis gate); the lines bound it, INC-X2 decides.

### X2a.9 Stated limits

- L-X2a-1: the piggyback tier is always `skipped` on the race path (scs passes None); it is logged for a complete tier record.
- L-X2a-2: the cancelled line's `total_ms` includes the unwind of the awaited call; delivery vs unwind cannot be split without a line inside serper_service (out of footprint).
- L-X2a-3: a sync tier (the Redis credit gate) cannot be interrupted, so a call cancelled during it reports the NEXT await's tier; a long `serper_budget` ms on a finished line exposes it.

### X2a.10 Out of scope

The race limit, the image tiers' order or logic, serper_service, api_budget_service, the KB image branch in scs, INC-X2 itself.

### X2a.11 Answers to the brief

- R-G1-4 (tier and cancellation points): X2a.1 (tiers img:249-295; cancellation only at `await search_images` img:266 or `await extract_image_via_gpt` img:285; the KB "tier" is the scs branch scs:6270 under ENABLE_KB_FIRST_SERVE).
- R-X2a-2 (log volume): at most 10 `[IMG_TIER]` lines per comparison, X2a.2.

---------------------------------------------------------------------------------------------------

## 12. The group: comm set, CI-order set, footprint, shared-file plan, PR plan, SAFE check

### 12.1 Comm set (the union rule; computed at base by git grep / git show, NOT run)

Method (scripts kept at `<SP>/G-INC-1/spec/closure.py` and `union.py`): (1) the app import closure to a FIXPOINT of the three edited modules (scs, ps, img) over every app/*.py (a module joins when its text names a closure member by dotted path, by `from <pkg> import <leaf>`, or by file path): 82 app modules, app.main INCLUDED (so every app.main / TestClient user joins); (2) every tests/test_*.py whose text names a closure member or uses app.main / TestClient: 680 files; (3) UNION the source-scanning readers of app/ not already in (rglob / os.walk / scandir / listdir / glob / getsource / ast.parse / read_text / read_bytes / open / __file__ / "app" path segments): 53 more; (4) UNION the named pins (test_model_config.py, test_model_config_enforced.py, test_prompt_fence.py, test_u3c_store_false_pin.py, test_start_command*.py, test_migration_index_predicate_immutability.py, test_openai_key_log_hygiene_s69.py, test_sentry_channels_u8d_unit.py) and the CLAUDE.md readers by the import graph (test_ci_gates.py, test_behavior_dimension_translation.py, test_s81_s04_spend_breaker.py, test_s81_s08b_legacy_fingerprint.py, test_s81_s08b_gate_rows.py, test_s81_s23_bypass_retire.py + the CLAUDE.md text readers found by grep: test_channel_freshness.py, test_cohort_personalization_load.py, test_eval_cache_read_mode.py, test_eval_kpi_baseline.py, test_retro_w1_2d.py); (5) UNION the SmartCompareApp-scanning backend tests (27 files by `git grep -l SmartCompareApp -- 'tests/*.py'`: all already in, except the two pre-commit files); (6) MINUS the four tests/test_precommit_hook*.py. Result at base: 732 files, list `<SP>/G-INC-1/spec/comm_set.txt`, sha256 `04a6d9c49c625d263cadd0aac9d190202db7e73a2416555eda5cfbc02a00ffe2`. At head add the four RED files (and the gate-rows file if the gate adds one): 736 (737). No edited test-support helper (the unit edits no non-test_*.py under tests/), so no helper importer joins beyond the closure.
- Base record: none stored for a74caba7 with this set; the LC-6 / GC-9 per-file reuse of the stored 90d4ed74 / f4461556 records does not apply to any member that names scs / ps / img or is an app.main user (most of the set): compute the base record ONCE at a74caba7 for this set-hash and store it under `<SP>/harness/base_records/a74caba7e3ff66b12e94178c912197c845ccbd14/<set-sha256>.txt`. Chunks of at most 25 files, bound 1200, base and head, `comm -13` of the sorted FAILED node-id sets EMPTY.
- The fourteen backend-scanning client jest fences: none reads a literal this group moves (measured: they read docs/, scripts/render_*.py, scripts/cron_expire_bonuses.py, app/services/extraction_service.py, app/services/referral_service.py, privacy-data-inventory; the scs / ps / RB / scoring mentions in SmartCompareApp/__tests__ are comments). The rule still runs them by path at GREEN and at the rebase (the footprint touches app/): DEFERRED, with the H5 jest probe first.
- Walkers of tests/ that will read the NEW RED files (grep for test-file globs): tests/test_hermeticity_pins.py, tests/test_ci_gates.py, tests/test_scoring_rubric_truth.py (all in the set). The RED agent writes the four files to their rules (no network, no real env writes outside monkeypatch, markers as the hermeticity pins require) and runs these three after writing.

### 12.2 CI-order set (one process, sorted = CI's alphabetical order, bound 1200; DEFERRED)

```
PYTHONIOENCODING=utf-8 C:/Users/SynAckITPC/Documents/AI/.venv-qaren/Scripts/python.exe <SP>/harness/pyt.py --bound 1200 --tag inc-g1-ciorder --log <SP>/G-INC-1/green/ciorder.log --cwd C:/Users/SynAckITPC/Documents/AI/sc-inc-g1 -- tests/test_cohort_summary_orchestrator.py tests/test_comparison_response_image_url.py tests/test_correctness_review_pr9_fixes.py tests/test_exact_gate_flag_off_parity.py tests/test_gender_contradiction_fix.py tests/test_gender_gents_ladies_leak.py tests/test_hermeticity_pins.py tests/test_image_knowledge_graph_tier.py tests/test_image_service.py tests/test_image_service_edges.py tests/test_image_service_longtail.py tests/test_inc_x10_listing_match_guard.py tests/test_inc_x2a_image_tier_timing.py tests/test_inc_x8_phase2_cached_rating.py tests/test_inc_x9_cohort_line_retire.py tests/test_response_builder_cohort_summary.py tests/test_s75_fanout_starve.py tests/test_s78_tier_fill_residual_guard.py tests/test_s81_s18_kb_first_serve.py tests/test_variant_descriptor_backstop_axes.py tests/test_variant_descriptor_golden.py tests/test_variant_descriptor_unit.py
```
The group touches neither /health nor app.main's lifespan, so the P73 "lifespan user first" rule does not apply.

### 12.3 Combined footprint (head vs base)

| File | Unit | Kind |
|---|---|---|
| app/services/structured_comparison_service.py | X9, X8 | edit (1 statement + docstring; 2 helpers + 1 block) |
| app/services/price_service.py | X10 | edit (table, reader, predicate; 2 hooks) |
| app/services/image_service.py | X2a | edit (2 imports, 1 helper, bookkeeping + 1 except arm; re-indent of img:249-295) |
| tests/test_cohort_summary_orchestrator.py | X9 | E-rows E9-1..E9-3 |
| tests/test_inc_x9_cohort_line_retire.py, tests/test_inc_x10_listing_match_guard.py, tests/test_inc_x8_phase2_cached_rating.py, tests/test_inc_x2a_image_tier_timing.py | RED | new, frozen |
| CLAUDE.md | all | one block + :341 sentence + :260 in place |

No migration, no scripts/, no .github/, no app/legal/, no SmartCompareApp/, no requirements, no processors.json row (no new host), no CREDENTIALS_UNSET entry. Estimated diff: about 150 added lines in app/ plus the img re-indent (about 45 lines shown as changed).

### 12.4 Shared-file plan

scs carries X9 and X8 in disjoint hunks (scs:5867-5914 vs scs:1892-1894 and scs:6707-6709), applied X9 then X8 on one byte copy; the mutation harness mutates them one at a time on that copy (one lock, `<worktree>/.qa-mutation.lock`). CLAUDE.md: one block for the group. At the final replay onto the then-main: S81-04c touches none of the group's app files; a CLAUDE.md union after the newest block in merge order; scs hunks re-anchored by string if S91 moved line numbers.

### 12.5 PR plan

One PR `fix/inc-g1-result-truth` -> main, body <= 25,600 B (LC-3): summary; one short section per unit (what, flag, E-rows, counts, stated limits, PROOF ON THE PHONE with "merged, NOT yet proven" wording, H6); the deploy-visible delta (X9 + X2a only); the measured before / after for X10 (R10-6) and X8 (R8-1) with the sentence that a hermetic measurement is not the production proof; the X2a read-back prefixes; owner steps (two flips, each its own window, after the flip freeze). Mutation tables and gate logs go to specs/ files (filed by the orchestrator). Merge only on the relay's "merge window open" (R0-6); it redeploys web.

### 12.6 CLAUDE.md (text, anchor)

- Anchor: a new block after the S81-G10 owner-steps bullet (CLAUDE.md:635 at base) and before `## Tests` (:637), with one blank line before its heading. Heading: "**INCIDENT LANE units (G-INC-1 RESULT-TRUTH: INC-X9 COHORT-LINE-RETIRE + INC-X10 LISTING-MATCH-GUARD + INC-X8 PHASE2-CACHED-RATING + INC-X2a IMAGE-TIER-TIMING, 2026-11-1x; the S92-FIX incident lane, one LC-9 SAFE group; spec .qa-s80/G-INC-1_UNIT_SPEC.md):**" then the four rows of X9.8 / X10.8 / X8.8 / X2a.8, then "- **Owner steps (names only; a dated ledger line per step):** X9 / X2a: none (deploy-visible at the merge: no cohort_summary; new [IMG_TIER] lines). X10: the ENABLE_LISTING_MATCH_GUARD flip on web in its own canary window. X8: the ENABLE_PHASE2_CACHED_RATING flip on web in its own canary window. Both after the flip freeze lifts (N1 proven), in the order the owner rules. Every unit is MERGED, NOT yet proven until the phone proof (H6)."
- :341 Feature Flags clause: append after the S81-G10 sentence: "G-INC-1 adds `ENABLE_LISTING_MATCH_GUARD` (INC-X10) and `ENABLE_PHASE2_CACHED_RATING` (INC-X8), both default OFF and read per call; INC-X9 and INC-X2a are unflagged: the rows of the **INCIDENT LANE units (G-INC-1 ...)** block."
- :260 (Results redesign) in place: "... the inline CohortBadge below the verdict was deleted by S81-11; the digit-free survey lines are kept; since INC-X9 the server no longer sends `cohort_summary`, so the store binary shows no cohort line either)."
- CLAUDE.md readers (in the comm set): test_ci_gates.py, test_behavior_dimension_translation.py, test_s81_s04_spend_breaker.py, test_s81_s08b_legacy_fingerprint.py, test_s81_s08b_gate_rows.py, test_s81_s23_bypass_retire.py and the text readers of 12.1 (4). The block is pure ASCII (no em dash; bytes > 127 checked after the edit).

### 12.7 SAFE check (R-G1-1)

| Surface | Touched? | Evidence |
|---|---|---|
| auth / tokens / sessions | no | footprint 12.3 |
| quota / billing / refunds | no | no usage_service / route / Lua edit |
| legal or privacy text | no | no app/legal, docs/privacy-data-inventory, processors.json edit; X9 sends LESS user-derived data (the governorate word leaves the response); no consent copy changes |
| consent path | no | |
| security middleware | no | |
| migrations | no | |
| Redis / Lua scripts | no | X2a logs around the existing sync Redis credit gate, does not change it |
| App-Review-visible client surface | INDIRECTLY (X9) | no client file changes; X9 changes what the LIVE store binary displays by omitting an optional block the binary handles as absent (the absent path proven by reading 683f56c0: ResultsScreen.tsx:988-1006 returns 0 / '' -> CohortBadge.tsx:62 returns null; the empty slot is today's unmatched-user layout). Listed in focus_surfaces_found for the orchestrator's classification; this spec judges it SAFE under R-G1-1 because the brief names exactly this effect and the owner ruled the badge removed (PLAN_S81.md:212). |
| secrets / key handling | no | |

### 12.8 Counts (group)

RED rows 3 (X9) + 11 (X10) + 6 (X8) + 7 (X2a) = 27. PIN rows 5 (X9) + 5 (X10) + 5 (X8) + 7 (X2a) = 22. Mutants 4 (X9, 1 equivalent) + 9 (X10) + 7 (X8, 1 survivor) + 6 (X2a) = 26. E-rows 3. Comm set 732 at base (736 at head with the four RED files).

### 12.9 Group open questions for the orchestrator

- Q-G-1: X9's owner ruling O1 is pending; the spec ships X9 unflagged (the brief's default). If O1 lands "flag it", X9 moves out of the unflagged class (a new flag + PIN rows) and the deploy-visible delta becomes X2a only.
- Q-G-2: the "both shapes (legacy and overview)" of R-X9-2 are read here as a builder response WITH a scoring result (overview / scoring_v2) and WITHOUT one (the legacy GPT-index shape), P9-2 / P9-3. If the orchestrator meant another pair, the RED agent adds it.
- Q-X9-a, Q-X10-a, Q-X10-b, Q-X8-a: in the unit sections.

---------------------------------------------------------------------------------------------------

## Not done in this spec

- No pytest, jest, tsc or eslint ran (READ-ONLY round, H5 c, R-G1-3): every base pass state (X9.1.10, X10.1.10, X8.1.10, X2a.1.10), the comm-set base record, the CI-order set and the client fences are DEFERRED TO RED / GREEN with the commands above.
- Every matcher verdict in the X10 truth table is BY READING; the RED agent confirms each base value (a KEEP row that is not True at base, or a REJECT row that is not True at base, stops the RED agent for a ruling).
- Not measured: the titles of the 28.0 / 33.0 Eros hits of 2026-11-11; the woo adapter's inferred category for "Versace Eros EDP"; the authority of the three hosts; whether the 2026-11-11 Tier-1 rows held usable ratings; the L2 -> L1 price promotion read path; CPython 3.12 `wait_for` behaviour on the pinned venv (by reading only).
- No CLAUDE.md, source or test file was edited; no scratch worktree was created; the only file written in the worktree is this gitignored spec.
