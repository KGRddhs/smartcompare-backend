# INC-H2 STORED-ROW GUARDS: the smart pick never shows a cross-size or non-BHD pair (spec, orchestrator S96-FIX, 2026-11-17 ~08:50 AST)

Class: SMALL. One adversary per the leaner chain; correctness lens. The relay holds the ENABLE_PRICE_NOT_LOST window until part A is on main.

## Defect (ORCH-H2)
`app/api/home_routes.py::_select_smart_pick` (main bd0500a3, :538) admits a stored comparison when both prices have an `amount` (:573-576). There is no size test and no currency test.
- With ENABLE_PRICE_NOT_LOST on, a row stamped `metadata.pair_price_sizes.mode` = `different_sizes` or `unknown` can become the Home smart pick. Its card then shows two prices for different bottles as `winner_price_bhd` / `runner_up_price_bhd`.
- Today, a stored row with a non-BHD price is shown under a `_bhd` field.
- The savings reader `_extract_winner_loser_prices` (:167) already refuses non-BHD (:190), and with #418 F4 it refuses the marker too. The smart pick should follow the same rule.

## Base
Branch from main after #418 merges; the helper `_pair_price_sizes_differ` (#418 F4) is on main then. If #418 has not merged when RED starts, RED works on #418's head 8bb97fe0 in a scratch worktree and GREEN rebases. Do not copy the helper.

## Part A, the marker skip. UNFLAGGED, ruled like F4.
- In `_select_smart_pick`, right after the `_result_status_supported` skip, add: `if _pair_price_sizes_differ(full): continue`.
- It is inert today, because no row carries the stamp while the flag is OFF. Once rows carry the stamp, it keeps them out after a rollback.
- It is the flip precondition for ENABLE_PRICE_NOT_LOST.

## Part B, the currency skip. FLAGGED: ENABLE_SMART_PICK_BHD_ONLY, default OFF.
- Read per call with the house idiom, as the first statement of its predicate.
- Flag ON: skip the row unless BOTH `products[w].price.currency` and `products[l].price.currency` == "BHD". This is the exact rule at :190, with no normalisation, so missing or lowercase currency is skipped exactly as the savings reader skips it.
- Flag OFF: byte-identical to today.
- It is flagged because it changes what users see today: a legacy row without a currency may stop being the pick.

## Out of scope
- (b) the curl_fetch_html_same_site log line is DROPPED. The owner said 03:35 that S97 no longer needs it; adding it would cost a comm set over price_service readers, so it is not free.
- The RPC home_savings_aggregate (036) stays a flip precondition of P2, and is not this unit.
- No client change.

## Change list
- app/api/home_routes.py: part A, part B and the flag reader.
- CLAUDE.md: the flag row and a short unit block after the INC-P2 block.
- tests/test_inc_h2_smart_pick_guard.py (RED).
- Any other file is a deviation.

## RED rows (hermetic: build `comparisons` dicts and call `_select_smart_pick` directly, plus one route row through the Home endpoint with the DB reader mocked)
- A1 [different_sizes, unknown]: a stamped row is the only candidate, so the result is None. RED.
- A2: a stamped row is newest and an unstamped older row exists. The older row is picked, with the reason matching that row. RED.
- A3 [same_size]: a stamped same_size row is picked as today. PIN.
- A4: a marker without `mode`, a non-dict marker, or a non-dict metadata is picked as today. PIN.
- A5: the marker skip holds with the flag OFF and ON, and with ENABLE_PRICE_NOT_LOST unset. RED.
- B1 [flag ON x (USD/BHD, BHD/USD, missing/BHD, "bhd"/BHD)]: the row is skipped. RED.
- B2 [flag OFF x the same cells]: picked as today. PIN; flag-OFF body digests over 6 fixtures.
- B3: flag ON with BHD/BHD is picked as today. PIN.
- B4: flag ON, the newest row is USD and an older row is BHD/BHD: the older row is picked. RED.
- R1 (route): GET the Home smart-pick route with the reader returning [stamped different_sizes row, clean row]. The payload names the clean row. RED.
- R2 (route): with the flag OFF and no stamp, the payload is byte-identical to a frozen golden. PIN.
- Mutants, at least 8: drop A; invert the mode test; read the flag outside the predicate; currency OR instead of AND; casefold the currency; skip before the status test (order); a default-ON flag; a missing-currency pass.

## Comm set
- Every importer and reader of home_routes: tests that grep `_select_smart_pick`, `smart_pick`, `home_routes`.
- The CLAUDE.md readers (test_ci_gates.py, test_behavior_dimension_translation.py).
- The black-clean readers, if home_routes is listed.
- The INC-P2 trio (it shares `_pair_price_sizes_differ`).
- The fourteen client fences once, by path.

## Flip note (for the PR)
- Part A needs no flip. It goes live on merge and is inert until P2 stamps rows.
- ENABLE_SMART_PICK_BHD_ONLY gets its own window. The canary is the Home card on the owner's phone: the pick is unchanged for a BHD history.
- Rollback: set the flag false.
