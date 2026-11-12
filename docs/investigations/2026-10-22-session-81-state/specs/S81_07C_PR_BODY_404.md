# S81-07c CLAUDE-ROLE-FIX: the verdict is given the scorer's winner; image_tier3 drops its closed schema (NO flag)

The unit commit `1da03aff` (on main `c6ebbd2e`) plus the merge commit `57f70df5` that brings in the moved main `5fcb7a71` (#403 S81-12d; CLAUDE.md conflict resolved by union, no sentence of either side dropped; `extraction_service.py` auto-merged, the two changes are disjoint) (9 files, +690 / -23; 625 of the insertions are the frozen RED file). No flag, no knob, no fixture, no bar and no `A6_SENTENCE` change (GATE_S81_07C GC-11). SAFE by LC-1 (no auth, quota, legal, consent, middleware, migration, Redis, client or key-handling surface): one adversary.

## What changed and why (run 1 of S81-07, 2026-11-12 17:51-18:24, code at c6ebbd2e)

**V, the verdict winner contract**
- Run 1: VERDICT NO-GO on one bar: A6 winner mismatch 22 / 120 = 0.1833 against the 0.10 bar.
- Cause: the prompt carried the scorer's winner only as text ("Score winner: <name> (narrow lead)"); with the price behind the value lead hidden, Haiku re-decided `winner_index` and followed the star rating (21 of 54 calls where the scorer's winner had the lower rating).
- Fix: `extraction_service.generate_comparison` gains a LAST parameter `score_winner_index: Optional[int] = None`. An int 0 or 1 (`type(x) is int`, so never a bool) with a non-empty `scores_summary` appends the constant `_FIXED_WINNER_BLOCK` (`## Fixed Winner`: PRODUCT <index + 1> is the winner, set `winner_index` to <index>, never re-decide it, name what the other product does better in key_tradeoff) right after the scores block and before the preferences / cohort block. Any other value, or no summary, leaves the system text byte-identical. The block names no product (an int and a position label only).
- Callers: both production calls in `structured_comparison_service.py` (REST and streaming) pass `score_winner_index=scoring_result.get("winner_index")`, the index `response_builder.reconcile_winner_prose` already enforces (no default 0: an absent index invents no winner). The URL-mode caller (`url_extraction_service`) passes none and is unchanged. `reconcile_winner_prose` stays the guard.

**T, the image_tier3 request shape**
- Run 1: TEXT NO-GO on one bar: `p95_s.image_tier3` 2.609 s against the 2.5 s bar.
- Cause: the closed `json_schema` output format on the site: round r00's two schema calls took 3.187 / 2.297 s beside normal no-schema neighbours (a first-use grammar compile), then about +0.25 to +0.35 s at p50 on every schema site.
- Fix: `llm_router.SITES["image_tier3"] = SiteSpec("text", 256, None, True)`, R-S06-1 option (b): no `output_config.format` (`output_config == {"effort": "low"}`), the JSON-only system line, the Claude-branch fence strip in `_normalise`: the path of the eleven prose-JSON sites. `IMAGE_TIER3_SCHEMA` is deleted; the SITES comment says why. `image_service` is not edited: its Tier-3 parser already strips a fence, runs `json.loads`, checks `_is_valid_image_url` and returns None on any failure. vision_v1, vision_v2, disambiguate and moderation keep their schemas.

**Harness, request parity only** (`scripts/meas_claude_gate.py`): the A6 builder passes each gold case's `gold_winner_index` (the production scorer's index, the value production passes); the A1 verdict builder passes 1 (the higher of its two synthetic scores, 75 > 72). The gold bytes, the 60 cases x 2 repeats, the A6 scoring, `evaluate_role`, every bar and the A1 round order are unchanged (pinned by V11).

**CLAUDE.md (GC-6, CRLF kept, bytes > 127 unchanged at 3,904)**: the Feature Flags pointer clause gains the S81-07c sentence after the S81-07 one; the S81-06 router row is rewritten in place (image_tier3 leaves the closed-schema list and joins the no-format list, "eleven" becomes "twelve"); the new block `SESSION 81 follow-up unit (S81-07c CLAUDE-ROLE-FIX, ...)` sits after the S81-07 block and before `## Tests` (the S81-07 rows read the LAST line containing `SESSION 81 unit (S81-07` as their block, so the heading says "follow-up unit").

## Precondition (the only road to a flip)

Run 2 of S81-07 (a NEW output folder, the TEXT stage) on the merged code is the precondition of the `ENABLE_ANTHROPIC_TEXT` and `ENABLE_ANTHROPIC_VERDICT` flips; MODERATION stands from run 1 (code untouched). A flip must run the measured code: S81-07c merged AND deployed on web before either flip. Nothing in production changes at the merge: no `ENABLE_ANTHROPIC_*` is set on web and no live model reads either request today.

## RED rows -> contract (frozen `tests/test_s81_s07c_role_fix.py`, sha256 `a197e2f2...4597509`, 17 nodes; GC-3)

| row | asserts | at base c6ebbd2e | HEAD |
|---|---|---|---|
| V01 | `score_winner_index` is the LAST parameter, default None | RED (10 == 11 params) | green |
| V02 | the block bytes for index 0 / 1, exactly once; the constant equals the V3 bytes | RED | green |
| V03 | removing the block gives exactly the no-keyword system text (with / without preferences, weird / weak quality, the independent-winner + Arabic directive combination) | RED | green |
| V04 | the block follows the cross-tier sentence and precedes the preferences block (and closes the text without preferences) | RED | green |
| V05 | None, True, False, 2, -1, "0", 0.0: byte-identical to the no-keyword call, no exception | RED by signature | green |
| V06 | `scores_summary` None and "" with index 0 and 1: byte-identical | RED by signature | green |
| V07 | `to_claude_request("verdict", ...)["system"]` keeps the block; the JSON-only line still ends it | RED | green |
| V08 | AST: exactly two scs calls, each `score_winner_index=scoring_result.get("winner_index")` | RED | green |
| V09 | AST: the URL caller passes no `score_winner_index` | PIN | green |
| V10 | offline plan: every A6 request (60 cases x 2) carries its case's block; the A1 verdict request carries index 1 | RED (120 of 120 without) | green |
| V11 | gold sha256 (LF), `A6_SENTENCE`, the TEXT / VERDICT bars, REPS_MAX, the plan's gold read, `evaluate_role` on synthetic metrics | PIN | green |
| T01 | `SITES["image_tier3"]`: schema None, expects_json True, role text, 256 tokens | RED | green |
| T02 | the Claude request: no format, `{"effort": "low"}`, thinking disabled, 256, system == `JSON_ONLY_INSTRUCTION` | RED | green |
| T03 | `IMAGE_TIER3_SCHEMA` is gone | RED | green |
| T04 | Claude branch, mocked client: a lower-case and an upper-case `json` code fence -> the URL; null -> None; prose -> None; an extra key -> the URL | RED (base [URL, None, None, None, URL]) | green |
| T05 | harness A1 metrics: image_tier3 under json_n / json_valid with schema_n 0; disambiguate keeps schema_n | RED ((2, 2) != (0, 0)) | green |
| T06 | disambiguate, vision_v1, vision_v2 (by hash), moderation schemas and every other SITES row equal their base literals | PIN | green |

Every RED row fails at base on an AssertionError only (`s07c-r-red-base2`: 14 failed, 3 passed; re-run by GREEN `s07c-g-red0-base`: the same split).

## Deliberate pin changes (E-rows, GATE_S81_07C GC-1 / GC-2; the committed hunks are byte-identical to the RED prototype's)

| E | file / row | change (the new truth, no weakening) |
|---|---|---|
| E1 | `tests/test_s81_s06_anthropic_router.py` R02c | image_tier3 `output_schema is None` and `expects_json is True` (was `== IMAGE_TIER3_SCHEMA`); docstring names S81-07c T1 / T2 |
| E2 | the same file, R01 | the exported-name list drops `IMAGE_TIER3_SCHEMA` |
| E4a | `tests/test_s81_s07_meas_harness.py` R87 | the schema pin moves to disambiguate (20, 20); image_tier3 (schema_n, json_n, json_valid) = (0, 40, 40) |
| E4b | the same file, `_decision_run` | the scripted 400 moves from k == 7 (image_tier3) to k == 15 (the round's disambiguate call), so R88 keeps its `schema_accept_min` cell |
| E4c | the same file, R88 | disambiguate (20, 19); image_tier3 (schema_n, json_n) = (0, 40) |
| E5 | `tests/test_s81_s22b_self_critique_retire.py:79` SITES_BASE | image_tier3's fourth field ("schema is None") False -> True (GC-1: the spec's stay-green line was the orchestrator's error) |

E3 (the s06 per-site request rows) was DROPPED: measured green, they read the schema from SITES live.

## Gates (HEAD 1da03aff on base c6ebbd2e; every pytest through the bounded runner behind the lane's slot wait, one at a time; not production proof)

- RED gate at base (`s07c-r-red-base2`): 14 failed on AssertionError only, 3 PIN passed; GREEN re-ran it (`s07c-g-red0-base`): the same split. On the branch (`s07c-g-red1-head`): 17 passed.
- E-row files alone (GREEN): `test_s81_s06_anthropic_router.py` 333 passed; `test_s81_s07_meas_harness.py` 186 passed + `test_r35_fixtures` (the known CRLF base node, failed at base too); `test_s81_s22b_self_critique_retire.py` 19 passed.
- Spec 4.2 stay-green files alone (GREEN): `test_prompt_truth.py` (31 passed + the 2 known ERROR nodes), `test_prompt_fence.py` 61, `test_model_config_enforced.py` 25, the w4_11 recorder importers (`test_price_fallback_may_decline.py` 17, `test_s80_url_mode_v2.py` 456), the reconcile suite (`test_winner_prose_reconciliation.py` 18, `test_tradeoffs_dedup_parity.py` 43, `test_w4_12_display_contract.py` 111) and the seven `test_response_builder_*` files (68): all passed.
- Lint: ruff `E9,F63,F7,F82` and py_compile on the 8 python files: clean; black --check on `llm_router.py` (on `.github/black-clean-paths.txt`): unchanged; the pre-commit hook (secret guards, gitleaks) passed.
- Offline dry run of the harness TEXT stage (GC-7, the credential names unset): rc 0, stdout and stderr 0 bytes; the plan holds 622 calls (= the base plan); an audit-hook probe of the same call saw 0 non-loopback socket events and 0 credential reads.
- Mutation table on the real code (a detached scratch worktree of 1da03aff; byte copy, one exact-string edit matching once, the killing rows via -k, bound 600, restore with a sha256 MATCH each time): 18 of 18 KILLED by an AssertionError: M01-M16 (spec 6) and GC-9's M17 (`score_winner_index in (0, 1)` -> `>= 0`, killed by V05 at index 2) and M18 (the `_normalise` strip condition `is None` -> `is not None`, killed by T04). Table and logs: S81_07C_GATES_REPORT.md.
- Comm set by the union rule: 365 members (290 files referencing the four changed modules or their symbols, the named source-scanning pins, 157 app / scripts source readers, the 7 CLAUDE.md readers, the importers of the w4_11 recorder and the rubric generators; minus the precommit hook files). HEAD in W, 15 chunks: 17658 passed, 24 failed / error nodes (all in the base record), 30 skipped, 43 deselected, 37 xfailed. Base record at c6ebbd2e (GC-8: the RED round's base runs reused per file for 91 members, 273 members run at base in a detached scratch worktree; stored as `harness/base_records/c6ebbd2e.../aa393545...`): 24 failed / error node ids, identical to the HEAD set (this box: the CRLF-working-copy hygiene rows of earlier units, the cold tiktoken cache, d22c P1 x5, s10 R06, d16 R10, s18b R2 and two page-scraping parser rows). Branch-only-new: EMPTY.
- The fourteen backend-scanning client fences (by path from SmartCompareApp through the junction, one `jest --ci`): 13 suites green; `config/nativeBundle.w37` red on its four accepted drift nodes only (d5, k2, k4, k5: client dependency state of package.json / the lock / the shared node_modules, which this unit does not touch); 236 of 240 tests passed (`[jest] tag=s07c-gates-fences ... rc=1`, jest 29.7.0).
- The full jest suite: not required (LC-7 / GC-10: no client file in the unit).

## Stated limits

Spec section 9 (L3 as corrected by GC-5):
- L1 A6 checks `winner_index` only: whether the prose leans toward the other product is not measured; `reconcile_winner_prose` still guards an index mismatch.
- L2 With a matching index the FULL Claude verdict shows (reason, tradeoff, value context, best-for, pros and cons); before this unit about one A6 call in five showed the fallback line instead.
- L3 Escalation is gated by `ENABLE_SONNET_ESCALATION` (`llm_router.escalation_allowed`), unset on web today: with it OFF a JSON failure at image_tier3 returns the placeholder only. The consequence of this change (the compare's one escalation spent inside the 5.0 s image leg) exists only once that flag is ON. The measured JSON validity of trivial outputs is high; run 2 prints image_tier3's json_valid.
- L4 disambiguate and moderation keep their schemas (the same measured overhead; no bar fails).
- L5 No request sets `cache_control` (run 1 cache-read share 0.0): a forward unit after the flips.
- L6 The production scorer can rest a value lead on a price the card shows as pending; the block tells the model the winner but the model cannot cite that price (WS-C C1 stays): a forward note.
- L7 The harness A1 verdict summary is synthetic, not production-shaped (pre-existing).

Added by the rounds:
- L8 The new block's heading reads `SESSION 81 follow-up unit (S81-07c ...)`: `tests/test_s81_s07_meas_harness.py` takes the LAST line containing `SESSION 81 unit (S81-07` as the S81-07 block (R76 / R96), so a later block must not reuse that phrase.
- L9 Known base failures on this box, identical at base and HEAD and not regressions: `test_s81_s07_meas_harness.py::test_r35_fixtures` (the CRLF working copy), the two `test_prompt_truth.py` ERROR nodes (a cold tiktoken cache), `test_s81_d22c_profile_select.py::test_p1_flag_off_golden` x5, `test_s81_s10_fragrance_gate.py::test_r06_production_lexicon_content`, plus 13 hygiene / parser rows of earlier units (d16 R10, d17 R9, s16 R27 x5, s18b R2, s19 R15, s22 B02, s22 judge J01, s24 P83 / R92 and two `test_page_scraping.py` rows): the comm set's 24 failed / error nodes are the same set at base and HEAD. CI is the arbiter.
- L10 The comm-set base record reuses the RED round's base runs at c6ebbd2e per file (GC-8, 91 members); those ran in other chunk groupings than the HEAD chunks.
- L11 The offline dry run's worst case for the TEXT stage rose from 1.44 USD (the S81-07 record) to 1.459691 USD (622 calls, unchanged): the verdict requests carry the block. Run 2's worst case stays far under the test workspace's spend limit (at most 15 USD).
- L12 The base count of the network-guard egress attempts of `tests/test_winner_prose_reconciliation.py` was not read (its base log line is truncated); at HEAD 12 attempts from the four `test_sse_*` nodes, where `generate_comparison` is an AsyncMock that accepts the new keyword; the file passes.

Added by the adversary (SOUND, 0 blocking, 0 major; minors are stated limits by LC-4):
- L13 (m1) A valid-JSON reply at image_tier3 that is not an object (null, a string, a list, a number) raises AttributeError at `image_service.py:214` (`parsed.get`); `get_product_image_url` catches it, so the user sees the placeholder exactly as for a miss, and the log line says `outcome=error:AttributeError` instead of `miss`. New on the Claude branch (the closed schema forced an object). Forward note: one isinstance check in a later unit.
- L14 (m2) Three regression pins are missing: the block on a compare with a demographics profile, on a non-fragrance category, and on the 429 `verdict_fallback` request. The adversary's probes found the code correct on all three paths (648 prompt combinations; the fallback carries the same system text). Forward: a test-only gate-rows file.
- L15 (m3) The model's behaviour with the block under quality `weird` (beside "Do NOT force a winner_declaration") and with `ENABLE_GPT_WINNER` ON (the log-only independent-winner diagnostic) is not measured: run 2's A6 sends normal quality with every prompt flag off.

## Merge of the moved main

Main moved to `5fcb7a71` (#403 S81-12d OPENAI-EGRESS-STOP) during the GREEN round. Merge commit `57f70df5` (parents `1da03aff`, `5fcb7a71`): `git diff 5fcb7a71 HEAD` holds exactly this unit's nine files; `git diff 1da03aff HEAD` exactly #403's thirteen. The CLAUDE.md conflict (the Feature Flags pointer clause and the two blocks after the S81-07 block) is resolved by union in merge order, S81-12d first; a line-by-line proof shows every line of both sides present except the one line each side rewrote in place. Gates on the merged bytes (merge round, one Opus agent): the RED file 17 passed; the E-row files and the three `tests/test_s81_s12d_*.py` files and `tests/test_s81_s03_llm_ledger_v2.py` green (s07 `test_r35_fixtures` = the known CRLF box node); the comm set 368 members (the 365 plus the three S81-12d files), base record at `5fcb7a71` stored (147 members reused per file from the `c6ebbd2e` record under a stricter rule, 220 run at base), 24 known box failures identical at base and HEAD, branch-only-new EMPTY; the fourteen client fences green (nativeBundle.w37 on its four accepted drift nodes only); the offline dry run 622 calls at HEAD and at base.

## CI round

First run at `57f70df5`: six of seven green; `backend-tests` 1 failed of 30,313 (`tests/test_retro_w0_1.py::test_red_late_start_healthy_host_is_not_blacklisted`: `assert verdict is False`, a thread-and-sleep timing test of the URL validator's DNS pool, a module this unit does not touch; its race lost on the runner). The job was re-run once, unchanged code.

## Owner steps (names only)

None to merge or flip. Run 2 is run by the relay's ops session with the owner's key file (no agent opens it); every `ENABLE_ANTHROPIC_*` flip stays the owner's, one canary window each, after run 2 reads GO on the merged and deployed code.

? Generated with [Claude Code](https://claude.com/claude-code)
