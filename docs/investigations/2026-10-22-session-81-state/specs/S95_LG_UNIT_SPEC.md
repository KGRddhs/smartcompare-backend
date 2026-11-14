# S95-LG URL-WINNER-GUARD: unit spec (session 95 main lane, 2026-11-14)

- Unit: S95-LG. Flag: NEW `ENABLE_URL_WINNER_GUARD` (default OFF, read per call with the house idiom as the FIRST statement of `url_winner_guard_enabled()`; the relay flips it on web in its own window after the merge).
- Class: SAFE by LC-1 (orchestrator ruling): one backend module (`app/services/url_extraction_service.py`) on the link-compare verdict path; no FOCUS surface (no auth, quota, refund, legal text, consent, middleware, migration, Redis or client byte). One adversary; the orchestrator's own spec review (LC-8).
- Worktree: to be made from the clone at the then-current origin/main (731bcddf at writing), branch `feature/s95-url-winner-guard`. Measurement location: `<scratch>/s95lg/<round>/`. The repository is PUBLIC: synthetic product names only.
- Why: under ENABLE_ANTHROPIC_VERDICT (ON on web since 2026-11-14 18:13) a LINK comparison's winner is the model's own pick. The text path gives the model the deterministic scorer's winner (S81-07c `_FIXED_WINNER_BLOCK`) and then reconciles the prose (`reconcile_winner_prose`); the link path does neither (S95 brief ADDENDUM 1, "LINK MODE WITHOUT A GUARD"). This unit gives link mode the same two steps, dark.

## 0. WHAT

Under the flag ON, `compare_from_urls` scores the two extracted products with the deterministic scorer, passes the scores summary and the scorer's winner index to `generate_comparison`, and after a delivered verdict runs `reconcile_winner_prose` on the verdict dict. So the shipped `winner_index` is the scorer's, and no winner-facing string names the loser. Flag OFF: byte-identical to base.

## 1. BASE STATE (731bcddf; the RED round re-measures every line)

| file:line | fact |
|---|---|
| app/services/url_extraction_service.py:1347 | `async def compare_from_urls(...)` |
| :1383-1384 | local imports of `get_comparison_service` and `generate_comparison` |
| :1440-1452 | `_resolve_pair_category(products, selected_category, parser_path=True)`, the S81-10b fragrance decision, then the write-back loop `for _p in products: _p["category"] = category_used` |
| :1466-1469 | `comparison, _usage = await generate_comparison(products[0], products[1], region, category=category_used)` (no scores summary, no winner index, no comparison quality) |
| :1470-1476 | `except _llm_breaker.LLMUnavailableError`: re-raised with every role OFF, else `_llm_unavailable_url_result("verdict")` |
| :1488-1497 | a truthy `comparison["error"]` -> the coded LLM_UNAVAILABLE non-delivery |
| :1499-1503 | `url_mode_v2` -> `_v2_verdict_fill(comparison, products)` (reads `comparison["winner_index"]`); else the raw recommendation / key_differences |
| :1505-1514 | the delivered dict: `success, products, comparison, winner_index (comparison.get("winner_index", 0)), recommendation, key_differences, category_used, source_urls` (the FROZEN keys) |
| app/services/extraction_service.py:2568-2580 | `generate_comparison(product1, product2, region, concern="value", user_preferences=None, scores_summary=None, category="other", demographics_profile=None, comparison_quality="normal", output_lang=None, score_winner_index=None)`; the fixed block is appended only for an int 0 / 1 with a non-empty summary |
| app/services/scoring_service.py:1357 / :3017 / :3111 | `ScoringService.compute_scores(products_data, preferences=None, ...)`, `build_scores_summary(scoring_result, product_names)`, `get_scoring_service()`; `compute_scores` reads `price.amount`, `specs`, the reviews and `category`, which `normalize_product_data` (url_extraction_service.py:1202) provides |
| app/services/scoring_service.py `compute_tradeoff_pairs` | `(dimension_winners, product_names, winner_index, scores=...)` as the text path calls it (structured_comparison_service.py:5621-5625) |
| app/services/response_builder.py:248 | `reconcile_winner_prose(comparison, scoring_result, product_names, tradeoffs) -> int`: a None scorer winner returns the model's; on a mismatch it re-indexes `comparison["winner_index"]`, drops the three model verdict strings and logs ONE `WINNER_INDEX_MISMATCH` warning; idempotent |
| app/services/structured_comparison_service.py:1271 | `_display_product_names(product_data)` (the text path's names for the summary and the reconcile) |

## 2. CONTRACT

- `url_winner_guard_enabled()`: `os.getenv("ENABLE_URL_WINNER_GUARD", "false").strip().lower() in ("true", "1", "yes", "on")`, read once per `compare_from_urls` call, after the two-product check and the category / fragrance decisions (a refused or failed extraction never reads it), before the verdict call.
- ON, the scorer step (after the write-back loop, before the verdict call), inside ONE `try` / `except Exception`: `scoring_service = get_scoring_service()`; `scoring_result = scoring_service.compute_scores(products)`; `product_names = _display_product_names(products)`; `scores_summary = scoring_service.build_scores_summary(scoring_result, product_names)`. Any exception: ONE `logger.warning("[URL_GUARD] scorer failed type=%s", type(exc).__name__)` and the rest of the call runs exactly as base (unguarded). No preferences, no behaviour profile, no cohort (link mode has none today).
- ON with a scorer result: `generate_comparison(products[0], products[1], region, category=category_used, scores_summary=scores_summary, score_winner_index=scoring_result.get("winner_index"))`. OFF, or ON after a scorer failure: the base call, exactly (no new keyword present).
- ON with a scorer result, after the error check (a non-delivery never reconciles): `tradeoffs = scoring_service.compute_tradeoff_pairs(scoring_result.get("dimension_winners", {}), product_names, scoring_result.get("winner_index", 0), scores=scoring_result.get("scores"))`; `reconcile_winner_prose(comparison, scoring_result, product_names, tradeoffs)` (in place), inside its own `try` / `except Exception` with ONE warning `[URL_GUARD] reconcile failed type=%s`; then the base tail (the V2 fill reads the reconciled dict).
- The delivered dict keeps exactly the frozen keys; `winner_index` stays `comparison.get("winner_index", 0)`.
- Logs carry constants and type names only (never a product name, URL or value); the existing `WINNER_INDEX_MISMATCH` line of the reconcile is unchanged.
- Failure table: scorer raises -> unguarded base; reconcile raises -> the verdict as the model wrote it; the verdict raises or returns an error -> the base non-delivery (no scorer effect); scorer winner None -> the model's winner (the reconcile's legacy branch).

## 3. CHANGE LIST (byte copies first)
1. `app/services/url_extraction_service.py`: the predicate `url_winner_guard_enabled()` beside `url_mode_v2_enabled()` (:116), and the two guarded steps inside `compare_from_urls` per section 2, with local imports (`get_scoring_service` from `app.services.scoring_service`, `reconcile_winner_prose` from `app.services.response_builder`, `_display_product_names` from `app.services.structured_comparison_service`) inside the ON branches only.
2. The RED file `tests/test_s95_lg_url_winner_guard.py` (the RED round; frozen after).
3. `CLAUDE.md`: one block `SESSION 81 follow-up unit (S95-LG URL-WINNER-GUARD)` after the last block before `## Tests` (the flag, ON / OFF effect, the canary, the rollback, the stated limits); the CLAUDE.md readers join the comm set.
4. No other file.

## 4. EXISTING PINS
- 4.1 Deliberate changes: none expected (OFF is byte-identical). The RED round measures every test naming `compare_from_urls`, `url_extraction_service` or `generate_comparison` at a prototype of the change list (the S94 lesson; the S95-LOGO miss) and lists any that move.
- 4.2 Stay green: tests/test_url_compare_category.py, test_s80_url_mode_v2.py, test_s81_s10b_links_gate.py, test_s81_s06_anthropic_router.py, test_s81_s06_router_gate_rows.py, test_s81_s20_result_gate.py, test_retro_w2_1.py, test_paid_route_metering.py, the S71 U13 compare-requires-sign-in test file, test_w4_13_measurement_truth.py (with the fixtures s71_u13_flag_off_baseline.json and s81_s10b_flag_off_golden.json), the reconcile pins (tests/test_response_builder_winner_card_consistency.py and every test naming reconcile_winner_prose), and the source-scanning pins of the union rule.

## 5. RED TESTS (`tests/test_s95_lg_url_winner_guard.py`; hermetic: `extract_from_url`, `_resolve_pair_category`, the fragrance decision and `generate_comparison` patched; the real scorer and the real reconcile)

| # | test | assertion | at base | satisfied by |
|---|---|---|---|---|
| G1 | ON; products where the scorer picks index 1; the patched verdict returns winner_index 0 with a declaration and reason naming product 0 | delivered `winner_index` 1; `comparison["winner_index"]` 1; the model's declaration and reason are gone; one WINNER_INDEX_MISMATCH record | FAIL | 3.1 |
| G2 | ON | the verdict call received a non-empty str `scores_summary` and `score_winner_index` equal to the scorer's int | FAIL | 3.1 |
| G3 | ON, the scorer patched to raise | delivered as base (the model's winner), the verdict call has no new keyword, exactly one `[URL_GUARD] scorer failed type=` warning naming the type | FAIL | 3.1 |
| G4 | ON, the verdict returns `{"winner_index": 0, "error": "x"}` | the coded LLM_UNAVAILABLE result, and the reconcile is never called (a recorder) | FAIL (no guard to skip: measure; may be a PIN) | 3.1 |
| G5 | ON with url_mode_v2 | the V2 recommendation names the scorer's winner | FAIL | 3.1 |
| G6 | the predicate | `url_winner_guard_enabled` exists (read through getattr) and the spellings TRUE / " on " / 1 / yes read ON, "" / false / 0 / off / garbage read OFF | FAIL | 3.1 |
| P1 | OFF with the full configuration (B1 rule: ENABLE_URL_MODE_V2 both states, every role flag name set, a call recorder on the scorer that raises if reached) | the verdict call's args equal base exactly; the scorer and the reconcile are never reached; the delivered dict equals the base golden recorded as a literal | PASS | stays |
| P2 | OFF, the verdict disagreeing with what the scorer would pick | the model's winner ships (base) | PASS | stays |

Rows fail at base on an AssertionError only (missing symbols through getattr / find_spec helpers). Prove the file at base, then on an in-place prototype of the change list (byte copies, restore, sha-compare), and run every 4.2 file at the prototype.

## 6. MUTATION TABLE
M1 drop the score_winner_index keyword (G2); M2 drop the reconcile (G1, G5); M3 reconcile before the error check (G4); M4 the predicate always True (P1); M5 log the product name in the warning (a caplog row on G3 must assert constants only); M6 swallow the scorer error silently (G3).

## 7. GATES
The RED file; the 4.2 set; the comm set by the union rule (module and symbol references of url_extraction_service, compare_from_urls, generate_comparison, reconcile_winner_prose, compute_scores, build_scores_summary, compute_tradeoff_pairs, _display_product_names; the source-scanning pins; the CLAUDE.md readers by the import graph; the backend-scanning client fences only if a client-read literal moves: none expected) at base and HEAD through pyt.py in chunks of at most 25 files; ruff E9/F63/F7/F82 and py_compile on the edited module.

## 8. CLAUDE.md ROW + owner steps
The block of 3.3. Relay window: set ENABLE_URL_WINNER_GUARD=true on web; canary on real link compares: the count of WINNER_INDEX_MISMATCH lines on the url path, zero `[URL_GUARD] scorer failed`, no rise in 4xx / 5xx on /api/v1/url/compare, the declaration names the shipped winner. Rollback: unset (per call).

## 9. STATED LIMITS
- L-1: link products carry fewer fields than the text path's (no rating breadth, sparse specs), so the scorer's winner on a link pair rests on less evidence; a scorer tie or no winner leaves the model's pick.
- L-2: no preferences, behaviour or cohort input in link mode (as base).
- L-3: `ENABLE_WINNER_PROSE_RECONCILE` (OFF) governs the template restore inside the reconcile exactly as on the text path.
- L-4: link verdicts are not covered by the S81-07 measurement harness.

## 10. OUT OF SCOPE
The text path, the client, the result gate, moderation (S81-07m), the data pipeline (S95-FIX).

## 11. OPEN QUESTIONS
Q1 for the RED round: is the scorer pure and fast on link products (no network, no Redis)? Measure it; if it reads Redis or the network, STOP and report.
Not done in this spec: no code, no test, no run.
