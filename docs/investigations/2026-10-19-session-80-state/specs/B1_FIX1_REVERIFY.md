# B1 fix round 1 RE-VERIFIER (correctness lens): RESULT-STATUS + TELEMETRY (ENABLE_RESULT_STATUS_METADATA)

Agent: b1-reverify-correctness. Window 2026-10-20 08:30 - 10:40 AST (the 90-minute budget was exceeded by
the D1-10 hook run and a loaded box; see "Budget"). Unit worktree
C:/Users/SynAckITPC/Documents/AI/sc-s80-b1 (never edited), branch feature/s80-b1-result-status, HEAD
dacc919e897ebdd539f835686f2f077ebe29e289 verified at the start (and at the end, below); `git status --short`
empty. Every probe, mutant and gate ran in my own detached scratch worktree <scratchpad>/B1_fix1_adv at
dacc919e (`git worktree add --detach`), sha-verified before and after, removed at the end. No .env read,
no production / Railway / Supabase / Sentry / network access; every pytest through pyt.py, one at a time.
Rulings applied: RULINGS_FIX1_B1 (binding, the "Re-verifier" section), s80-common.txt, PLAN_S80 sections 0-1,
RULINGS_R0, RULINGS_BATCH1 (B1), GATE_B1, B1_ADV_correctness.md, B1_ADV_engineering.md.

## Verdict: SOUND (0 blocking, 0 major, 5 minor; the D1-10 hook files measured 31 of 327 nodes, the rest NOT MEASURED, see Hook files)

## RED files (re-hashed; equal to the new frozen set)

| file | sha256 (committed blob, LF) | note |
|---|---|---|
| tests/test_s80_b1.py | 71a50e8e2e8b643e954eeaabaafcb10b73b3e285bd4a0136d42180b35425a1fc | unit worktree file and `git show HEAD:` equal; diff vs 2bbd58a9 = exactly `-import os`, `-...get_current_user, get_optional_user` -> `get_current_user` (F1-7), 12 nodes appended (hunk at the end only); every other row byte-identical |
| tests/test_s80_b1_feedback.py | 0bd1117880ac96cee0aee35832814ae7eee620b6bef09bba7b0513648ea59ab3 | unchanged |

The scratch checkout writes both files CRLF (core.autocrlf); the LF-normalised bytes equal the shas above.
App files in the unit worktree equal the fix report's table: result_gate.py d5912230..., sentry_service.py
a49bc683..., profile_routes.py 750b689d..., CLAUDE.md 806f8448...; structured_comparison_service.py
7533fa10... (unchanged since GREEN).

## What the fix round claims, checked against the bytes

- F1-1 (MAJ-1 / MAJ-E1): `result_gate.stamped_product_categories` reads `metadata.product_categories` (a
  2-list; non-str -> None; anything else -> None), the same filter the builder applies before it stamps
  (`response_builder.py` stamp block: `_b1_cats = [c if isinstance(c, str) else None ...]`, stamped only for a
  2-list). `capture_result_status` assesses with it; `telemetry_tags`' no-assessment fallback uses it too. So the
  stamp and the message are computed by the same `assess_result` over the same categories; I checked that nothing
  between the stamp and the emitter changes an assess input: `_strip_inference_markers` (runs after the stamp)
  removes only `*inference_source*` keys and the value `model_knowledge`, never a `_field_confidence` marker in
  MODEL_KNOWLEDGE_MARKERS; the routes add metadata keys only. HOLDS. Rows f1_1a/b/c/d + f1_4 pin it on the
  emitter, text POST + GET, camera and stream exits (killed RV1, RV2, RV3).
- F1-2 (MAJ-2 / MAJ-E2): `profile_routes` imports `home_routes._result_status_supported` (no duplicate; the
  f1_2 row pins identity) and the three extractors return (None, None) for a stamped non-supported row; callers:
  `/profile/recent-decisions` `continue`s on a missing name (row skipped), `/profile/monthly-stats` skips the row
  (decisions_count and savings both drop). Only one other importer of the helpers exists (none; history_routes
  only mentions `_safe_image_url` in a docstring). No import cycle (home_routes imports no profile module).
  HOLDS (killed RV4, RV5, RV6).
- F1-3: `MODEL_KNOWLEDGE_MARKERS = {tier3_synthesis, training_data}` used only by `_tier3_fields` ->
  `real_spec_rows` (the AUDITABLE spec fact). `training_data` is what `scs._clean_specs` lifts from a
  `<field>_source == "training"` marker; `smart_fallback` / `tier2_fallback` / `snippet` / other values keep
  counting (pinned in f1_3). The LITERAL reading (`literal_spec_items` over the prose) never reads markers.
  `section_status` and `_corroborated` use the one-side count (markers not excluded) -- unchanged and outside the
  ruling (it names the AUDITABLE fact only). HOLDS (killed RV7 drop, RV8 over-exclusion).
- F1-4 / X18s: no hunk; the stream capture precedes the write-back at scs ~:4921; rows f1_1d and f1_4 kill the
  swap (RV9). HOLDS.
- F1-5: `_finite` = `_num(v) and v == v and v not in (inf, -inf)` (the P11 import pin forbids `math`); used by
  `_bucket`, `telemetry_extras`, `stamp_camera_stage_timings`; the emitter now passes the raw `elapsed_ms` to
  those helpers (identical for finite ints; a non-finite or str elapsed is an absent wall and the message still
  goes out). HOLDS (killed RV10, RV11 nan-only, RV12 int() fallback).
- F1-6: `PARTIAL_STAGES = {gather, post_gather, scoring, verdict}`. Independent grep of app/: the ONLY writer of
  `metadata.partial_stage` is `scs._build_partial_response` (:3814) with `_partial_stage()` returning exactly those
  four constants (:3685-3699); text_routes :478 only reads it. A partial body with an unknown str omits the tag; a
  non-partial body or a non-str stage keeps `none`. HOLDS (killed RV13 whitelist dropped, RV14 set drift, RV15
  unknown -> none, RV16 = M11).
- F1-7: exactly the two F401 imports removed; ruff blocking tier clean on the RED file.

## Mutation run (fix bytes, scratch worktree; `.qa-mutation.lock` created and removed; each mutant on a
## byte copy, one exact edit matching once (CRLF-aware), the rows via pyt.py -k (bound 600), restored from the
## copy and sha256-compared: 17 runs, 17 restores ok; scratch tree `sha256sum -c` OK and `git status` empty after)

16 mutants, 16 KILLED, every killing failure an AssertionError (RV6's first form raised AttributeError on the
row's "garbage" metadata because MY mutant was not total; re-run in a total form, killed by AssertionError only).

| id | fix | mutant | killing rows | [pyt] |
|---|---|---|---|---|
| RV1 | F1-1 | emitter drops the stamped categories (`assess_result(result)`) | f1_1a, f1_1b, f1_1c, f1_1d, f1_4 | `[pyt] tag=b1rv-mut-RV1 start=2026-10-20 08:55:02 end=2026-10-20 08:57:13 elapsed=130s bound=600s status=FAIL rc=1` |
| RV2 | F1-1 | the reader keeps non-str elements (`list(cats)`) | f1_1a | `[pyt] tag=b1rv-mut-RV2 start=2026-10-20 08:57:19 end=2026-10-20 08:59:21 elapsed=122s bound=600s status=FAIL rc=1` |
| RV3 | F1-1 | `telemetry_tags` fallback drops the categories | f1_1a | `[pyt] tag=b1rv-mut-RV3 start=2026-10-20 08:59:33 end=2026-10-20 09:00:56 elapsed=82s bound=600s status=FAIL rc=1` |
| RV4 | F1-2 | names-site skip removed | f1_2[names], f1_2b | `[pyt] tag=b1rv-mut-RV4 start=2026-10-20 09:01:32 end=2026-10-20 09:01:58 elapsed=26s bound=600s status=FAIL rc=1` |
| RV5 | F1-2 | images-site skip keyed on `metadata.winner_index is None` (X30 class) | f1_2[images] | `[pyt] tag=b1rv-mut-RV5 start=2026-10-20 09:01:58 end=2026-10-20 09:02:19 elapsed=20s bound=600s status=FAIL rc=1` |
| RV6 | F1-2 | savings-site skips only `unsupported_category` (total form) | f1_2[prices], f1_2b | `[pyt] tag=b1rv-mut-RV6 start=2026-10-20 09:03:07 end=2026-10-20 09:03:42 elapsed=36s bound=600s status=FAIL rc=1` |
| RV7 | F1-3 | `training_data` counts again | f1_3 | `[pyt] tag=b1rv-mut-RV7 start=2026-10-20 09:03:44 end=2026-10-20 09:04:05 elapsed=22s bound=600s status=FAIL rc=1` |
| RV8 | F1-3 | over-exclusion: `smart_fallback` treated as model knowledge | f1_3 | `[pyt] tag=b1rv-mut-RV8 start=2026-10-20 09:04:06 end=2026-10-20 09:04:28 elapsed=22s bound=600s status=FAIL rc=1` |
| RV9 | F1-4 | stream twin captures the categories AFTER the write-back (X18s) | f1_1d, f1_4 (not r15 / r16) | `[pyt] tag=b1rv-mut-RV9 start=2026-10-20 09:04:50 end=2026-10-20 09:04:56 elapsed=6s bound=600s status=FAIL rc=1` |
| RV10 | F1-5 | finite guard removed (`return _num(value)`) | f1_5 | `[pyt] tag=b1rv-mut-RV10 start=2026-10-20 09:04:57 end=2026-10-20 09:05:03 elapsed=6s bound=600s status=FAIL rc=1` |
| RV11 | F1-5 | only the nan half removed | f1_5 | `[pyt] tag=b1rv-mut-RV11 start=2026-10-20 09:05:04 end=2026-10-20 09:05:09 elapsed=5s bound=600s status=FAIL rc=1` |
| RV12 | F1-5 | emitter fallback back to `int(elapsed_ms)` | f1_5 | `[pyt] tag=b1rv-mut-RV12 start=2026-10-20 09:05:27 end=2026-10-20 09:05:33 elapsed=6s bound=600s status=FAIL rc=1` |
| RV13 | F1-6 | whitelist dropped (any str stage) | f1_6 | `[pyt] tag=b1rv-mut-RV13 start=2026-10-20 09:05:33 end=2026-10-20 09:06:18 elapsed=45s bound=600s status=FAIL rc=1` |
| RV14 | F1-6 | `PARTIAL_STAGES` drifts (verdict missing) | f1_6 | `[pyt] tag=b1rv-mut-RV14 start=2026-10-20 09:06:20 end=2026-10-20 09:07:38 elapsed=78s bound=600s status=FAIL rc=1` |
| RV15 | F1-6 | unknown stage -> `none` instead of omitted | f1_6 | `[pyt] tag=b1rv-mut-RV15 start=2026-10-20 09:07:40 end=2026-10-20 09:08:36 elapsed=56s bound=600s status=FAIL rc=1` |
| RV16 | M11 | `partial_stage` tag ignores `metadata.partial` (the GREEN survivor the PR body now calls killed) | f1_6 | `[pyt] tag=b1rv-mut-RV16 start=2026-10-20 09:58:29 end=2026-10-20 09:58:39 elapsed=10s bound=600s status=FAIL rc=1` |

(RV6 first, non-total form: `[pyt] tag=b1rv-mut-RV6 start=2026-10-20 09:02:19 end=2026-10-20 09:02:25 elapsed=6s bound=600s status=FAIL rc=1`, killed by f1_2b AssertionError plus my mutant's AttributeError on the garbage row; superseded by the total form above.)
Not re-applied this round: the spec section-6 table and the previous adversary's 42 (killed or accepted at
GREEN; the fix round changed no code they target except the four F1 sites above); the X19 hand mutant (D1-3
records the correctness adversary's measurement; not re-measured).

## Gates ([pyt] lines verbatim; scratch worktree at dacc919e; flag unset unless marked)

```
unit files (both) 226 passed, flag unset
[pyt] tag=b1rv-unit-off start=2026-10-20 08:47:26 end=2026-10-20 08:50:41 elapsed=194s bound=600s status=OK rc=0
  [hermeticity] sentinel checked 226 test(s)  [netguard] blocked 0 attempt(s) from 0 node(s)
unit files (both) 226 passed, flag ON exported on the runner call
[pyt] tag=b1rv-unit-on start=2026-10-20 08:51:17 end=2026-10-20 08:52:02 elapsed=45s bound=600s status=OK rc=0
  [hermeticity] sentinel checked 226 test(s)  [netguard] blocked 0 attempt(s) from 0 node(s)
CI-order set (the fix agent's 23 files, alphabetical, one process; includes the identity pins, the two CLAUDE.md
readers, test_profile_routes.py, test_profile_priorities_normalize.py, test_w4_12_display_contract.py) 1306 passed
[pyt] tag=b1rv-ci-order start=2026-10-20 09:17:07 end=2026-10-20 09:29:02 elapsed=715s bound=1200s status=OK rc=0
  [hermeticity] sentinel checked 1306 test(s)  [netguard] blocked 16 attempt(s) from 4 node(s) (test_paid_route_metering x2
  sentinel neutralized.supabase.invalid:443, test_stage_timings x2 egress api.openai.com:443 = the baseline class)
the CLAUDE.md row's local-.env hazard (two pins), flag unset: 2 passed
[pyt] tag=b1rv-hazard-off start=2026-10-20 09:30:59 end=2026-10-20 09:31:39 elapsed=39s bound=600s status=OK rc=0
same two, flag ON exported: 2 failed, both `AssertionError ... {'supported': True}` (exact overview.winner dict)
[pyt] tag=b1rv-hazard-on start=2026-10-20 09:31:40 end=2026-10-20 09:31:58 elapsed=18s bound=600s status=FAIL rc=1
```
Comm set (re-derived: module / symbol / route references to profile_routes, sentry_service, result_gate,
response_builder, structured_comparison_service, home_routes and every symbol the round touched, plus the
source-scanning pins, app-walking tests and the CLAUDE.md readers: 269 files, every one already in the fix
agent's 305 except 2 (`tests/test_price_fallback_may_decline.py` "training_data", `tests/test_spec_parity.py`
`_field_confidence`); run = the union, 307 files, minus the four hook files; `tests/_env_safety.py` absent from
both lists (D1-8)), 13 chunks of <= 25 files, bound 1200, the four NETWORK_FLAKY_EXCLUDE ids deselected:
```
comm-00 798 passed                      [pyt] tag=b1rv-comm-00 start=2026-10-20 09:32:18 end=2026-10-20 09:33:07 elapsed=48s bound=1200s status=OK rc=0
comm-01 4 failed, 1009 passed, 4 skip   [pyt] tag=b1rv-comm-01 start=2026-10-20 09:33:07 end=2026-10-20 09:39:06 elapsed=358s bound=1200s status=FAIL rc=1
comm-02 503 passed, 1 skip              [pyt] tag=b1rv-comm-02 start=2026-10-20 09:44:32 end=2026-10-20 09:46:36 elapsed=124s bound=1200s status=OK rc=0
comm-03 2985 passed                     [pyt] tag=b1rv-comm-03 start=2026-10-20 09:46:42 end=2026-10-20 09:57:19 elapsed=637s bound=1200s status=OK rc=0
comm-04 612 passed                      [pyt] tag=b1rv-comm-04 start=2026-10-20 09:58:59 end=2026-10-20 09:59:47 elapsed=48s bound=1200s status=OK rc=0
comm-05 454 passed                      [pyt] tag=b1rv-comm-05 start=2026-10-20 09:59:47 end=2026-10-20 10:00:16 elapsed=29s bound=1200s status=OK rc=0
comm-06 4 failed, 576 passed            [pyt] tag=b1rv-comm-06 start=2026-10-20 10:00:26 end=2026-10-20 10:01:03 elapsed=37s bound=1200s status=FAIL rc=1
comm-07 340 passed, 2 skip, 1 xfail, 2 errors [pyt] tag=b1rv-comm-07 start=2026-10-20 10:01:04 end=2026-10-20 10:01:35 elapsed=31s bound=1200s status=FAIL rc=1
comm-08 1476 passed                     [pyt] tag=b1rv-comm-08 start=2026-10-20 10:01:47 end=2026-10-20 10:04:46 elapsed=179s bound=1200s status=OK rc=0
comm-09 1390 passed, 1 xfail            [pyt] tag=b1rv-comm-09 start=2026-10-20 10:04:48 end=2026-10-20 10:06:39 elapsed=110s bound=1200s status=OK rc=0
comm-10 343 passed, 2 skip              [pyt] tag=b1rv-comm-10 start=2026-10-20 10:06:48 end=2026-10-20 10:07:39 elapsed=51s bound=1200s status=OK rc=0
comm-11 1168 passed, 35 xfail           [pyt] tag=b1rv-comm-11 start=2026-10-20 10:07:42 end=2026-10-20 10:09:41 elapsed=119s bound=1200s status=OK rc=0
comm-12 97 passed                       [pyt] tag=b1rv-comm-12 start=2026-10-20 10:09:41 end=2026-10-20 10:11:12 elapsed=90s bound=1200s status=OK rc=0
```
Per chunk `[hermeticity] sentinel checked` = the node count (798 / 1017 / 503 / 2985 / 612 / 454 / 580 / 343 /
1476 / 1391 / 344 / 1203 / 97); `[netguard] blocked` 34/7, 31/13, 9/3, 79/44, 13/2, 8/2, 149/19, 99/12, 24/3,
19/9, 115/40, 82/35, 12/4 (attempts / nodes); the ratchet script was not run (per-chunk lines only).
FAILED / ERROR set (10 ids): the seven `tests/.pre_impl_failures.txt` rows (test_camera_vision.py::
TestIdentifyProductsMocked x3, test_page_scraping.py x2, test_personalization_bundle_c.py x2), the two
cold-tiktoken `tests/test_prompt_truth.py` ERRORs (the environmental class the common brief names; GREEN measured
them alike at base), and ONE load flake: `tests/test_conftest_env_safety.py::
test_live_opt_in_restores_the_environment_end_to_end` (its child pytest hit its own `--timeout=45` inside
`import openai` while the box spawned at 2.4-4.9 s per `node -e 0`); re-run ALONE it passed:
```
test_conftest_env_safety.py alone 24 passed, 1 skipped
[pyt] tag=b1rv-envsafety-alone start=2026-10-20 09:40:13 end=2026-10-20 09:43:49 elapsed=216s bound=600s status=OK rc=0
  [hermeticity] sentinel checked 25 test(s)  [netguard] blocked 0 attempt(s) from 0 node(s)
```
-> branch-only-NEW (vs GREEN's 9 and the base) = EMPTY. The fix agent's flag-ON comm run (information) is
not repeated; its two extra nodes are the hazard pins I re-measured above.

Hook files (D1-10; run ALONE at the end, nothing else of mine running; the box at 2.3 s per `node -e 0`):
```
tests/test_precommit_hook.py -k "not dash": 31 passed
[pyt] tag=b1rv-hook1-notdash start=2026-10-20 10:15:55 end=2026-10-20 10:34:54 elapsed=1139s bound=1800s status=OK rc=0
  [hermeticity] sentinel checked 31 test(s)  [netguard] blocked 0 attempt(s) from 0 node(s)
```
Measured cost: 37 s per hook node (1139 s / 31; the CLAUDE.md idle figure is about 1 s). The remaining 296
nodes (test_precommit_hook.py dash 31, test_precommit_hook_phase_b.py 114, test_precommit_hook_phase_b_round2.py
121, test_precommit_hook_round2.py 30) need about 3 h at that rate: the 1800-s bound admits about 48 nodes per
call, so every phase_b call would TIMEOUT twice by arithmetic. I did NOT spend two predetermined 30-minute
TIMEOUTs per call: those 296 nodes are reported NOT MEASURED (deviation from D1-10's literal two-TIMEOUT
procedure, stated). Context: the fix round edits no `.githooks` file and no hook test; the fix commit itself
passed the hook (fix report); the engineering adversary measured 213 of the 327 nodes green at GREEN.

Non-pytest: ruff 0.16.5 `--select E9,F63,F7,F82 --no-cache` on the four changed .py (`All checks passed!`);
`py_compile` clean; `git diff --check 2bbd58a9 HEAD` clean; added-line sweep (379 lines): 0 bytes > 127, 0 sk- /
AKIA / xox / JWT / PEM / credentialed-URL / +973 / 8-digit runs (one regex false positive: `+@pytest.mark...`).
Every `test_b1_*` name or prefix the PR body cites (67) resolves to a defined test function (63 defined).

## CLAUDE.md row (:473-475) and PR body: sentence by sentence

Verified true against the bytes: the module inventory (incl. `stamped_product_categories`); the AUDITABLE
definition incl. the F1-3 model-knowledge clause; the stamped keys; `metadata.winner_index = None` on
non-supported bodies; Home + the three profile readers skip by `result_status` through ONE unflagged reader
imported by profile_routes, unstamped rows as today, stamped rows stay skipped after a rollback; the tag list and
grammar; the bucket / extras representation and F1-5; "the assessment is recomputed from the body with the
STAMPED product_categories ... while partial, partial_stage (whitelisted) and the elapsed_ms fallback are read
from metadata" (D1-2, now literally true); non-success never emits; synchronous try/except; the camera timing
rule; the sampler (1.0 on the four paths regardless of parent under the flag; parent else the live client rate;
init keeps `traces_sample_rate=0.1` and sets no `sample_rate`; the RN client `tracesSampleRate: 0.1`,
SmartCompareApp/src/services/sentry.ts:274, so "drops 90 % of parents" holds) (D1-4); "every new key is ignored
by build 3 except ... History row ..." (D1-6); six `perf_counter` reads on the camera route (image_routes.py
:315/:317/:375/:377/:459/:461) (D1-5); the `/home/savings` legacy-path limit (migrations/036 :56 / :69 key on
`full_response ->> 'winner_index'`; home_routes.py :235 the flag fork) (D1-1); both quotas in the limits and owner
step 3 (D1-4); the local-.env hazard pins (re-measured above); rollback. PR body: D1-3 (X19 killer named as
`test_b1_r9_builder_stamps_lane1_supported[...]` via `section_status['price']`, not R8), D1-7
(`test_b1_p5a_init_sentry_kwargs_kept` cited and defined), D1-8 (`tests/_env_safety.py` dropped), D1-9 (X22a /
M16 / M9 one sentence each; M11 killed, re-measured as RV16; X18s pinned, RV9), the Fix round 1 section, the new
RED shas, owner step 3 with both quotas. The 4-byte robot emoji on the attribution line is the only byte > 127
(required line).

Minor wording findings (none changes behaviour; listed under MINOR).

## MINOR

1. CLAUDE.md row and PR body, D1-5 sentence: "the only OFF-state work is the flag read ..., and the sampler's
   flag read plus client-option lookup" omits the UNFLAGGED `_result_status_supported` call that runs per stored
   row in BOTH states on `/home/savings` (legacy path), `/home/smart-pick` and, since F1-2, the three profile
   readers (one dict lookup per row; an unstamped row returns True, so behaviour is unchanged). The sentence follows
   D1-5's list verbatim; suggest "... plus the unflagged per-row `result_status` reader on Home and Profile".
2. CLAUDE.md row: "`partial_stage` ... `none` when the body is not a partial" is incomplete: a partial body
   whose `partial_stage` is absent or not a str also tags `none` (fix report deviation 6; the only writer always
   stamps a str, so unreachable in production). Wording.
3. PR body "Gates" section (GREEN era): headed "base = 81df2b64, HEAD = 2bbd58a9" and "RED frozen:
   tests/test_s80_b1.py sha256 88130f32...35dfb"; the current frozen sha (71a50e8e...) appears only in the "Fix
   round 1" section. Suggest titling the first block "GREEN gates (2bbd58a9)" so a reader does not take the old
   sha as current.
4. Stated-limit gap (F1-2 consequence, not in the row or the PR body): `/profile/recent-decisions` selects
   `.limit(3)` rows BEFORE the skip, so after the flip a user whose three newest comparisons are all stamped
   non-supported gets `empty_state: true` with `cta_text_key: profile.recent_decisions.empty_cta` ("run your first
   comparison" copy) although history exists; a mix shows fewer than three cards. Same mechanics as the
   pre-existing skip of malformed rows; build 3 renders it after the flip. Suggest one stated-limit sentence (or
   a C1 / B2 item: over-fetch, then trim to three).
5. (Carried, orchestrator) the fix commit's trailer reads `Co-Authored-By: Claude Opus 5.5` (fix report
   deviation 1) while the session's brief names Fable; this re-verifier also ran on Opus 5.5 (claude-opus-5-5).
   Recorded for the model check; no effect on the bytes.

## Previous round: every MAJOR and MINOR closed or recorded

| finding | status |
|---|---|
| correctness MAJ-1 / engineering MAJ-E1 (telemetry contradicts the stamp on a conflict body) | CLOSED: F1-1 code + f1_1a/b/c/d, f1_4; RV1-RV3 killed |
| correctness MAJ-2 / engineering MAJ-E2 (B1-R11 Q7 profile skip not implemented) | CLOSED: F1-2 code + f1_2[x3], f1_2b; RV4-RV6 killed (residual UX note: MINOR 4) |
| correctness min-1 / eng minor 2 (/home/savings aggregate path) | RECORDED (D1-1) in the row and PR body; verified against migrations/036 |
| correctness min-2 / eng minor 4 ("never read from metadata") | CLOSED (D1-2): row, PR body and the emitter docstring rewritten; true now |
| correctness min-3 (X19 killer is R9, not R8) | RECORDED (D1-3) in the PR body stated limits; not re-measured |
| correctness min-4 (training_data is model knowledge) | CLOSED: F1-3 + f1_3; RV7 / RV8 killed |
| correctness min-5 / eng minor 1 (unsampled parents; error-event quota) | RECORDED (D1-4): row limits + PR body + owner step 3 name both quotas |
| correctness min-6 (survivors X18s, X22a, M16, M11, M9) | X18s CLOSED (F1-4, RV9); M11 CLOSED (RV16 killed); X22a / M16 / M9 RECORDED as accepted (D1-9) |
| correctness min-7 (LF-committed result_gate.py checks out CRLF) | information only (confirmed: scratch checkout CRLF, blob LF) |
| eng minor 3 (OFF-state work wording) | CLOSED (D1-5) with a residual omission: MINOR 1 |
| eng minor 5 ("build 3 ignores every new key") | CLOSED (D1-6) |
| eng minor 6 (non-finite walls raise) | CLOSED: F1-5 + f1_5; RV10-RV12 killed |
| eng minor 7 (partial_stage pass-through) | CLOSED: F1-6 + f1_6; RV13-RV15 killed |
| eng minor 8 (`test_b1_p5a` node name) | CLOSED (D1-7) |
| eng minor 9 (unused imports in the RED file) | CLOSED (F1-7) |
| eng minor 10 (`tests/_env_safety.py` in the comm list) | CLOSED (D1-8) |
| eng hook TIMEOUT (D1-10) | PARTLY MEASURED: 31 / 327 nodes passed (b1rv-hook1-notdash); 296 NOT MEASURED (37 s per node on this box; see Hook files) |
| eng NOT MEASURED flag-ON comm chunks | measured by the fix agent (two hazard pins only); the two re-measured here ON / OFF |

## NOT MEASURED

- The spec section-6 mutant table and the X19 hand mutant were not re-applied (the round's own sites are covered by
  RV1-RV16).
- scripts/netguard_ratchet.py over a QAREN_NETGUARD_REPORT (per-chunk netguard lines only).
- The flag-ON comm set (the fix agent ran it; only its two hazard nodes re-measured).
- Frequency of `training_data` markers in production rows (F1-3's effect size; the PR body notes the
  `now_vs_solgar` fixture carries 2).
- 296 of the 327 pre-commit hook nodes (Hook files above).

## Budget

Started 08:30; the 90-minute budget ended at 10:00 with the comm set mid-run (the box spawned at 2.4-4.9 s per
`node -e 0` for long stretches: the unit OFF run took 194 s vs 32 s idle, the CI-order set 715 s vs 50 s). I
finished the comm set and ran the D1-10 hook files because the rulings assign them to this agent by name.

## End state

- Unit worktree sc-s80-b1 (10:37): HEAD dacc919e897ebdd539f835686f2f077ebe29e289, `git status --short` empty,
  RED shas 71a50e8e... / 0bd11178... (equal to the new frozen set), no .qa-mutation.lock; never edited.
- Scratch worktree <scratchpad>/B1_fix1_adv: `sha256sum -c` OK on the six hashed files and `git status --short`
  empty after the last mutant and the last gate; removed with `git worktree remove --force` (rc 0); `git worktree
  list` carries no B1_fix1_adv entry; the directory is gone; it never held a node_modules junction.
- No pytest of mine alive (process command lines matched on my tags: 0). No .env read, copied or printed.
- Files written (ASCII, LF, under <scratchpad>/B1_fix1/): this report; reverify/notes.md, reverify/mutate_rv.py,
  reverify/gates_rv.py, reverify/comm_derive_rv.py, reverify/comm_files_rv.txt, reverify/comm_extra_rv.tsv,
  reverify/scratch_pre.sha, reverify/added_lines.txt, reverify/pr_cited.txt, reverify/defined.txt,
  reverify/claude_md_b1_diff.txt, reverify/mutants_*.json, reverify/bytecopy/*, reverify/logs/*,
  reverify/gates/* (logs, json, SUMMARY.txt).
