## W4-4: a partial must not invent a score it never computed (PO-VERDICT-TRUTH-02) + `metadata.partial_stage`

### Defect
When the hard cap fires, `_build_partial_response` passes an empty `scoring_result` to `build_comparison_response`. The `, 50)` defaults in `_build_scoring_v2` then calibrate both products to 70. The collapse guard writes the loser down to 69, and `win_margin` becomes 1. None of these numbers came from data. On the client (`ResultsScreen.tsx:772-778` at HEAD, `:689-695` at the phones' `97b5f15`) that pair picks the crown by input order. It contradicts the product-derived dimension bars on the same screen: on the fixture, every dimension winner is product_1 while the crown is product_0. The payload is also persisted to `comparisons.full_response` and re-rendered by History. The cap-hit rate on organic traffic is about 15.4% (n=1,513).

### Design: a stage split under one flag (Fable R1)
`ENABLE_HONEST_PARTIAL_SCORING` defaults OFF and is read per call. The reader copies the `_gpt_winner_lever_enabled` idiom (`os.environ.get`, not memoised); test_12c pins a flip after import.
- **post-gather partial** (product data stashed, no scoring yet): `compute_scores` runs on the stash, using only the ctx `user_preferences` (pinned by test_03d; no behavior or cohort profile), with no LLM call and no network (pinned by test_03b). The result is a real `scoring_v2`, the real crown (Beta on the fixture, the product every dimension names), and the real bars, pills and runner-up card. The compute is local to the build and never written back to the stash (test_03e). If `compute_scores` raises, the partial falls back to the early-buffer shape below: `success:true`, never an error (test_14). The canary WARNING is logged exactly once with the exception type (test_14).
- **early-buffer-only partial**, or any partial whose scoring still lacks an `overall`: `scoring_v2: null`. The key is never popped, so the key set is stable across flag states (tests 1, 4 and 13 are the null-versus-pop pins). `overview.winner.reason`, `key_tradeoff`, `recommendation` and the persisted BC `comparison` alias (`winner_reason` / `key_tradeoff`) are blanked. Keys stay.
- **Scoped to partials** (red-gate Ruling 1): the null and the blanks apply only when `metadata.partial is True`. A non-partial build with an absent overall keeps today's calibrated block (test_15). Production's full builds (`:3825`, `:4598`) always pass `compute_scores` output anyway.
- `_build_scoring_v2`'s `len(product_data) < 2 → {}` guard still fires first (test 7). The `, 50)` defaults and the CALIBRATION-COLLAPSE guard are untouched; their diff is empty.

### `metadata.partial_stage`: UNFLAGGED and additive (R3/R4)
Values are `gather` (early buffer only), `post_gather` (product data, no scoring), `scoring` (scoring stashed, no verdict) and `verdict` (verdict stashed). `none` is never emitted. It records the stage the partial CARRIED. W4-13 adopts the same mapping.

**Latent limit (content, not only the label):** `compare_from_text_streaming` never assigns `_partial_product_data`, `_partial_scoring_result` or `_partial_comparison`. Its only touch is the None reset at `:4084`; the three assignments (`:3641`, `:3735`, `:3784`) are all on the sync path. So a streaming tail-deadline partial (`_emit_stream_deadline_partial`, reachable only with `ENABLE_FULL_STREAM_DEADLINE` ON) always reports `partial_stage: gather`. With `ENABLE_HONEST_PARTIAL_SCORING` also ON, it always takes the early-buffer branch: `scoring_v2: null` and a blank reason, `key_tradeoff` and `recommendation`. That happens even after `compute_scores` ran on that stream (`:4454`) and the SSE `scores` (`:4467`) and `verdict` (`:4592`) events already reached the client. The final `complete` payload therefore RETRACTS scores and a verdict the stream already showed. With this flag OFF, the same payload overwrites them with today's fabricated 70/69 instead. This does not reach users today: phones use REST (`ENABLE_EXPO_FETCH_SSE_DEFAULT=false` at 97b5f15 and HEAD) and both flags are OFF. Do not flip the two flags together until the SSE stash lands. The key is inert until W4-13 reads it in `log_search`. It persists into `comparisons.full_response` (History and public share), which is acceptable.

### Flag row
| flag | default | effect ON | composition | activation order |
|---|---|---|---|---|
| `ENABLE_HONEST_PARTIAL_SCORING` | OFF, per call | partial + post-gather ⇒ real deterministic scores/crown; partial + early buffer ⇒ `scoring_v2: null` and blank verdict prose | independent of every other flag EXCEPT `ENABLE_FULL_STREAM_DEADLINE`. That flag opens a streaming tail-deadline route to `_build_partial_response` which never carries a stash, so the pair retracts content (see Latent limit). `ENABLE_BUNDLE_C_SCORING` gates `scoring_service` only | safe on the 97b5f15 client (no crash; null and undefined are treated alike). Flip AFTER the FE copy row (below) is on phones, so an early-buffer partial reads as honest and not as an empty screen. **Precondition: do not flip `ENABLE_HONEST_PARTIAL_SCORING` together with `ENABLE_FULL_STREAM_DEADLINE` until the SSE stash lands (follow-up 2).** |

### What stops rendering on an early-buffer partial with the flag ON (97b5f15 anchors, HEAD in parentheses)
DimensionBars `:407` (`:423`); ConfidencePills `:464` (`:480`); RunnerUpWinsCard via `:387` (`:403`), which self-hides; FactualVerdict `:346` (`:362`), which falls to the now-blank verdict text; PersonalizationChip `:369` (`:385`), already self-hiding; the RevealBurst; and an empty legacy spacer at `:512` (`:528`). A post-gather partial keeps all of these, now fed by real scores.

### KPI / canary
Split the canary by `metadata.partial_stage` before claiming impact. GPT is the slow stage, so cap-during-verdict partials already carry real scores and the flag is inert for them. Watch `"[L2.7] compare_from_text hard-cap %.1fs hit"` and `"[stream] hard cap %.1fs hit"`, plus the new `[W4-4] partial compute_scores failed: <ExceptionType>` WARNING, which should be ~0. It logs the exception TYPE only, never `str(e)`, because a compute error can carry product or user text. test_14 pins it with caplog: exactly one WARNING on the scs logger, type name present, message text absent.

### Honest limits
- A personalised user's post-gather crown uses only explicit preferences. The behavior and cohort profiles are not applied, so it can differ from the finished run for that user.
- The early-buffer crown still follows input order (`winner_index` 0); only the prose and the fabricated scores are removed. Deciding what an early partial should SHOW needs the FE half and a product decision.
- Rows persisted before the flip keep 70/69 forever. Any backfill predicate is `metadata.partial = true AND scoring.scores == {}`.
- The two `STREAM_TIMEOUT` bodies (`success:false`, top-level `partial`) are untouched and carry neither `scoring_v2` nor `partial_stage`.
- The half-score rows in test 2 are defence-in-depth for the public builder; they cannot be reached through the orchestrator.
- Pre-existing, not W4-4: `test_explicit_pair_integration_mocked.py` (2 to 3 nodes depending on flag state) and `test_timeout_partial_integration.py` (TestStreamingTimeoutD2Contract, plus the route classes via a supabase `.invalid` host) attempt outbound DNS/HTTPS when unguarded. The OpenAI leg is `content_safety_service.moderate_output`. One such run hung in a TLS handshake with api.openai.com until pytest-timeout. They pass when the network is blocked, but they should get their own guard in a separate change.

### Follow-ups
1. FE copy row (its own OTA-gated mobile-wave row, R5): widen `results.partial.note` (`en.json:768` + `ar.json`) so it says the VERDICT is provisional, not only the prices.
2. Stash on the SSE path. Assign `_partial_product_data` / `_partial_scoring_result` / `_partial_comparison` in `compare_from_text_streaming` at the points that mirror `:3641` / `:3735` / `:3784`. Then a streaming tail-deadline partial carries the scores and verdict the stream already emitted instead of retracting them, and `partial_stage` is exact. This is the precondition for running `ENABLE_HONEST_PARTIAL_SCORING` alongside `ENABLE_FULL_STREAM_DEADLINE`.
3. Re-emit product-derived dimensions and confidence legs from a non-`scoring_v2` block for early partials (R1(c)).
4. CLAUDE.md flag row at merge time (docs PR).
5. A repo-wide test network guard for the pre-existing outbound tests named above.

### Gates
- Unit file `tests/test_partial_response_no_fabricated_scores.py`: 92/92, both with the ambient flag unset and inside the flag-ON Preserve run. Every test also sets its own flag state. Its autouse guard blocks non-loopback connect, connect_ex and getaddrinfo.
- Preserve set (36 files = the spec's section-3 union plus the unit file), run under a session-wide network guard: flag OFF 600 passed / 30 deselected, flag ON 600 passed / 30 deselected.
- Comm set, 204 files (spec grep union + 10 SmartCompareApp scanners + the new file), at HEAD with the 11 `.pre_impl_failures.txt` ids deselected. Flag OFF: 5761 passed / 0 failed; base 0 failed; `comm -13` empty. Flag ON (blast re-measure): 5760 passed / 1 failed. The failure, `test_openai_breaker::test_flag_off_compare_never_short_circuits`, is a load-timing flake: the Bright Data leg was missed in the price race, the file passed 18/18 three times in isolation with the flag ON, and a sibling node flaked the same way with the flag OFF in an earlier run. The polish's one-line log-argument change was not followed by a comm re-run; Preserve and the unit file were.
- ruff (E9,F63,F7,F82) and py_compile: clean.
- No corpus byte-identity gate: this is not a price-path unit. The identical empty failure sets are the flag-OFF proof.
- Mutations recorded in `.qa-w4/W4-4-MUTATIONS.txt`, each restored from a byte snapshot with a matching sha256. These include: preferences dropped (test_03d red), compute written back to the stash (test_03e red), return-None branch deleted (19 red), the `not scoring_result` guard (8 of 10 rows red); canary line replaced with `pass` (test_14 red, 1 failed / 91 passed); logging `str(e)` (test_14 red); logging at INFO (test_14 red).
- Post-rebase verification on main (W4-1 #173 shifted the scs anchors after `:1214` by +5, no textual conflict): the unit file re-run in both flag states on the rebased tree, plus the partial/calibration neighbours and the W4-1 scs neighbour, ruff + py_compile.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
