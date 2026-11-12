# S94 first report: the two NO-GO causes, the fix ruled for each, the road to run 2 (2026-11-12 19:15)

From S94 (local_8c207f06, main lane, Opus 5.5). Sources: run 1 raw records (`text/spend.jsonl`, `text/results.json`, `moderation/spend.jsonl` under `C:/Users/SynAckITPC/MYEZ-meas/s81-07-run1`), the code at main `c6ebbd2e` (git plumbing only), the relay's `S81_07_NOGO_ANALYSIS_2026-11-12.md` (a reading aid; every figure below is recomputed from the raw ledger). Nothing was run against the API and nothing in production was read or changed. No bar is relaxed anywhere below.

## 1. VERDICT: A6 22 of 120 = 0.1833 against 0.10

**Reading (confirmed).** The prompt carries the deterministic result only as qualitative text ("Score winner: <name> (narrow lead)") plus one soft sentence, "Your verdict MUST be consistent with the scores above" (`app/services/extraction_service.py:2601-2613`). The model still chooses `winner_index` itself. In this set the scorer's lead is always value per wear; the prices behind it are hidden from the model (non-showable price, pending shape, `extraction_service.py:2647`); Haiku then picks the higher-rated product (21 of 54 calls where the scorer's winner has the lower rating). This is a production prompt-contract defect, not only a fixture artefact: production hides a pending price the same way. So the fix must hold on the SAME hard set.

**Ruled fix (production design, unflagged): the deterministic winner is GIVEN and the model only explains it.**
- `generate_comparison` gains `score_winner_index` (0 or 1). The two production call sites pass `scoring_result["winner_index"]` (the same value `reconcile_winner_prose` already enforces).
- Inside the existing Verdict Requirements block (only when a scores summary is present) ONE fixed line: the winner is PRODUCT N+1; set `winner_index` to N; never re-decide it from ratings, review counts or prices; explain its scored advantage and put the other product's strongest point in KEY TRADEOFF. No product name is added to the system text (the index and the position label only).
- Prompt byte-identical when the index is absent or invalid, or when the scores summary is empty (the URL-extraction caller is unchanged).
- The harness passes the same argument production passes, for request parity only: A6 the case's scorer winner (the field the gold was generated from), A1 the higher synthetic score.
- UNCHANGED: the gold, the 60 cases x 2 repeats, the metric, the bar 0.10, the A6 sentence, `reconcile_winner_prose` (stays the guard).
- Not chosen: a fixture-only fix (showable prices) would measure an easier set and leave the pending-price blind spot in production; Sonnet for the role costs about 20x per call, p95 8.3 s, and its adherence is unmeasured; showing a non-showable price to the model risks it reaching the prose.
- Honest consequence (a stated limit): when the index matches, the FULL Claude verdict shows (reason, tradeoff, value context, best-for, pros and cons). A6 checks the index only, not whether the prose leans toward the other product.

## 2. TEXT: image_tier3 p95 2.609 s against 2.5

**Reading: the cause is the request shape, the closed `json_schema` output format on image_tier3 (R-S06-1 option a), not the box and not the distance.**
- First-use grammar compile (documented: a new schema pays a one-time compile, then a 24-hour cache). Round r00: both image_tier3 calls 3.187 s and 2.297 s while the no-schema calls of the SAME concurrent group were normal (price 0.891 / 0.907 s, specs 2.187 / 2.141 s). The first disambiguate call (schema) 1.969 s against its median 1.110 s. The first moderation call (schema) 3.390 s against its median 1.203 s.
- Steady per-call overhead of the schema path: image_tier3 (596 input / 9 output tokens, schema) p50 1.219 s against price in the same concurrent group (1,689 / 59, no schema) p50 1.125 s; disambiguate (438 / 20, schema, sequential) p50 1.110 s against specs_targeted (969 / 16, no schema) 0.875 s; moderation (479 / 23, schema) p50 1.203 s against classify (152 / 6) 0.829 s. About +0.25 to +0.35 s at p50, and a fatter tail on every schema site.
- Box load: not supported. The slow image calls of r08 (2.609 s) and r15 (2.859 s) had normal neighbours in their own concurrent groups (1.0 to 2.1 s); a client stall hits the group.
- Network distance: about 0.27 s per call from this PC (count_tokens p50 0.266 s). Production web runs in GCP asia-southeast1 (ops memory 2026-08-31), a distance of the same order: not a cause, not corrected.
- Prompt size (596 tokens), max_tokens (256 for a 9-token answer) and the model (Haiku): not causes.

**Ruled fix (code, unflagged):** image_tier3 moves from R-S06-1 (a) to (b): no output format, the JSON-only line and the Claude-branch fence strip, exactly the path of the eleven prose-JSON sites. The parser already enforces the contract (`json.loads`, `_is_valid_image_url`, null gives the placeholder); the schema protects nothing more. It removes the compile on a rarely reached tier (tier 3 runs only after three tiers miss, so its grammar cache would often be cold in production) and the per-call overhead. The bar stays 2.5 s; image_tier3 then faces the JSON bars (site 0.9, pooled 0.98) instead of the schema-accept bar. Disambiguate and moderation keep their schemas (no bar fails; stated). Expected: like a no-schema 9-token call in the concurrent group, p50 about 0.95 s, p95 about 1.6 to 2.2 s.

## 3. One unit, one PR: S81-07c CLAUDE-ROLE-FIX (part V = verdict, part T = image_tier3)

Chain: spec plus one reviewer, my rulings, RED, my gate, GREEN with the comm set (the source-scanning pins plus the fourteen client jest fences, since literals move in `app/` and `scripts/`), ONE adversary (leaner chain: a small unit), the PR, CI 7 of 7, your merge word. Worktree `sc-s81-s07c` at `c6ebbd2e`, re-anchored to each moved main you pass me. My gates run through pyt.py; the incident lane's gate.py yields to them and mine wait for its live pytest.

## 4. Honest estimate to run 2

- The PR ready for your merge word: about 6 to 8 hours from now (about 01:30 to 03:30 Friday 2026-11-13) if no round comes back NOT_READY; one fix round adds about 2 hours.
- Run 2 = the TEXT stage only, a NEW folder `C:/Users/SynAckITPC/MYEZ-meas/s81-07-run2`, from a fresh detached worktree at the merged main: about 35 minutes and about 0.60 USD (the total then about 1.21 of 15). MODERATION stands from run 1: S81-07c does not touch its code (stated in both reports); re-running a GO role adds spend and a spurious-failure chance (its false-positive bar is 0).
- Stated clean conditions: no pytest or jest of any lane during the run (both build lanes hold), the same PC, key and harness; run 1 and run 2 reported side by side.
- Likelihood: VERDICT within 0.10: high (I expect 0 to 3 of 120). image_tier3 within 2.5 s: likely, not certain (about 80 to 85 percent: the p95 of 40 samples is decided by the third-largest). If run 2 still misses, I ask for no run 3: the next step is the owner's call on the printed data.
- A flip must run the measured code: S81-07c merged AND deployed on web before `ENABLE_ANTHROPIC_TEXT` or `ENABLE_ANTHROPIC_VERDICT`.

## 5. Item (d): the two knob proposals and the zero cache-read share

- `ANTHROPIC_CLASSIFY_LLM_TIMEOUT` 4.0 to 2.0: ruled NO change now (a stated limit). The proposal is p99 x 1.25 over 20 samples (that p99 is the max, 1.312 s); a p99 needs about 1,000 samples. Re-derive from the production ledger (V2 is ON) once 1,000 classify rows exist after the TEXT flip. No owner line is needed for keeping the default.
- `ANTHROPIC_TAIL_RESERVE_SECONDS` 6.5 to 8.5: the knob is read only when `ENABLE_TIER_FILL_RESIDUAL_GUARD` is ON and the verdict decides anthropic (`structured_comparison_service.py:1920-1935`). QUESTION: is that guard ON on web? OFF: the knob is inert, a stated limit. ON: I recommend the owner's dated line 8.5 at the VERDICT flip window (4 of 20 run-1 tail spans above 6.5 s: 6.531, 6.718, 6.797, 7.062), re-derived from run 2's spans first (the verdict prompt grows by one line).
- cache-read share 0.0: a fact of the code, not a fault of the run: no request sets `cache_control` (none in `app/` or `scripts/`). Haiku 5.5 caches prefixes of 512 tokens or more, so verdict, specs, reviews, price and parse would qualify. A cost and first-token lever on no bar (p50 0.004 USD per compare); ruled a stated limit with a forward unit after the flips (it changes every site's request and needs its own measurement). Not in S81-07c.

## 6. Now

Starting the spec and the worktree. Nothing blocks me; the guard question in section 5 only affects the tail-reserve recommendation.
