"""Files the follow-up issues of the merged session-68b PRs (#207, #209, #212, #213).
Run from the scratchpad dir: python issues/file_issues.py [--dry]
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pr_rest import api, REPO  # noqa: E402

ISSUES = []

ISSUES.append(("W4-13b: the SSE stream still bills success:False terminals as delivered (log says failure, bill says delivered)", """
Follow-up of PR #209 (W4-13 measurement truth, main `58a86b3c`), stated limit **CD-wave-diffs-02**.

**What is wrong.** Under `ENABLE_SEARCH_LOG_TRUTH` the SSE stream now logs its `success:False` terminals (STREAM_TIMEOUT, INSUFFICIENT_DATA, the moderation refusal) as failures in `search_logs` - but the route's metering branch in `app/api/text_routes.py::event_generator` still treats a terminal event as a delivered comparison: the reserved credit is kept, `record_lifetime_comparison` runs and a history row is written. So with flag 1 ON the LOG says failure while the BILL says delivered (measured in the W4-13 ledger; before #209 both said "success", which was the original defect).

**Ask.** On a `success:False` terminal take the NON-delivery path the sync routes already take: refund through the existing usage-refund label, no `record_lifetime_comparison`, no `save_comparison`, `log_search success=False` with the terminal's code. Keep the M18 CD-interactions-01 semantics for the `complete_after_client_gone` latch (a client gone before the terminal still refunds exactly once; `elif had_error` still wins). Decide in the spec whether this rides `ENABLE_SEARCH_LOG_TRUTH` or its own default-OFF flag; the committed flag-OFF ledger fixture (the 45-scenario ledger under `tests/fixtures/`) must stay byte-identical.

**Acceptance.** One ledger scenario per terminal in the both-flags state (refund fired once, lifetime not recorded, no history row, log row `success=False`); the flag-OFF scenarios unchanged; the W4-13 unit files green in all four states.
"""))

ISSUES.append(("W4-13c: send the synthetic-traffic header from bias_matrix_probe, bundle_d_prod_smoke and run_validation_matrix", """
Follow-up of PR #209 (W4-13 measurement truth, main `58a86b3c`), stated limit **"Harness marker: only eval_runner marks its traffic"**.

**What is wrong.** #209 added `ENABLE_SEARCH_LOG_SYNTHETIC_MARKER` + `SEARCH_LOG_SYNTHETIC_TOKEN` (migration 042 adds the column): a request carrying the token is stored as synthetic and, under flag 2, the analytics readers exclude it. Only `scripts/eval_runner.py` sends the header. The three other harnesses that hit production still land as ORGANIC rows and keep polluting the series the readers report (the 2026-09 review measured 88.6% of `search_logs` as 13 probe strings): `scripts/bias_matrix_probe.py`, `scripts/bundle_d_prod_smoke.py`, `scripts/run_validation_matrix.py`.

**Ask.** Send the synthetic header from all three, reading the token from the environment (never printed, never defaulted); when the token is unset send nothing (today's request shape). Pin each script with a recorded-request test (header present iff the token is set).

**Also record at activation:** the NULL window - rows written between 2026-09-03 and the flag-2 flip are never classified and the readers count them as organic permanently; measure that window on the day flag 2 flips.
"""))

ISSUES.append(("PO-RECORDED-MEASURED-01c: the search_logs analytics readers have no .range() - the PostgREST row cap silently truncates aggregates", """
Follow-up of PR #209 (W4-13 measurement truth), stated limit **"The readers have no `.range()`"** (PO-RECORDED-MEASURED-01c).

**What is wrong.** The `search_logs` analytics readers (the `/admin/stats/*` readers, including `/admin/stats/popular`) issue unpaged PostgREST selects. PostgREST caps a response at its max-rows setting (1000 by default), so any aggregate over more rows is silently truncated - the flag-2 canary on `/admin/stats/popular` can pass or fail on truncation alone, and every "organic series" number is a lower bound nobody labelled.

**Ask.** Either page the readers with `.range()` until a short page comes back, or move the aggregate server-side as #116 did for `/home/savings` (an RPC with the cross-tenant guard pattern of migration 036). Pin with a fake client that returns exactly the cap on the first page and fewer on the second, and state the cap in each reader's docstring. Under `ENABLE_SYNC_DB_OFFLOAD` the paging loop must stay inside `run_db`.
"""))

ISSUES.append(("W4-13d: the sync CONTENT_UNAVAILABLE exits carry no total_cost (a paid moderation run logs cost 0.0)", """
Follow-up of PR #209 (W4-13 measurement truth), stated limit **D2** (named W4-13d here to avoid the "D2 surface helper" of #69).

**What is wrong.** The sync `CONTENT_UNAVAILABLE` exits in `app/services/structured_comparison_service.py` (the L1 prefilter and the `moderation_api` refusal) return no `total_cost`, so the truthful log row (T1 under `ENABLE_SEARCH_LOG_TRUTH`) records `cost 0.0` for a PAID moderation-API run. Related rows from the same measurement: `/url/compare` rows carry cost 0.0; the camera path's unsuccessful branch reads `metadata.total_cost`, which the orchestrator never writes there (it puts `total_cost` at the TOP level) - verify whether #209's camera row already fixed that before touching it.

**Ask.** Thread the real `total_cost` onto the moderation-refusal and CONTENT_UNAVAILABLE exits (the service already tracks it per request), read the top-level key on the camera path, and pin one row per exit (a paid moderation run logs a non-zero cost). No flag: these rows are cost-accounting truth with no legitimate reader of the zero.
"""))

ISSUES.append(("W4-6b: honest sentinel arithmetic under renorm (the #101 call), lift the tie/renorm coupling, N/A for renorm-excluded dimension winners (W4-7d)", """
Follow-up of PR #212 (W4-6a rubric truth, main `8433954c`; flags `ENABLE_VALUE_DIM_PARTIAL_SIGNAL` and `ENABLE_TIE_IS_NOT_MISSING`, the latter coupled OFF under `ENABLE_MISSING_DIM_RENORM`). **Blocked on Ahmed's #101 product call** (flag-ON, a measured-vs-missing pair reports `win_margin 0.0` - a 4.9-star product vs an unrated one reads as a dead heat).

**Rows left open by W4-6a (each measured in its PR body):**
- One-sided sentinels still carry `MISSING_SCORE=50` into the margin (#101). The three remaining N/A-contributor grid rows: fashion/other `one_missing_price`, supplements `both_no_price`.
- R11d: a margin computed against the WINNER's sentinel is not covered by the tradeoff guard (low severity).
- `excluded_dims` vs `missing_data` can disagree under renorm + V - renorm's own design (40 records under both R and RV in the red measurement); decide whether the display should reconcile them.
- Lift the `ENABLE_TIE_IS_NOT_MISSING` renorm coupling once the sentinel arithmetic is honest.
- **W4-7d** (ruled in W4-7 R11): under renorm a one-sided missing dimension ships `dimension_winners[dim] = {winner: <the only side with data>, margin: None}`, naming a product the "winner" of a dimension that does not score; the display contract should ship N/A. It belongs with this unit's display contract.

**Precondition before flipping either W4-6a flag (canary item):** confirm `RunnerUpWinsCard` renders its empty state for `tradeoffs: []` - `key_tradeoff` is empty on 140 of 169 records under T and 146 of 169 under V, against 78 of 169 flag-OFF; the phone contract has been "always a caption" since F4.2.
"""))

ISSUES.append(("W4-6c: a non-numeric merit discriminator for fashion/other (Ahmed DECISIONS item; xfail(strict) pin on main)", """
Follow-up of PR #212 (W4-6a rubric truth). **Ahmed's DECISIONS item** - a product design, not a bug fix.

**What is open.** W4-6a's rule (c) is not closed (ruling R4): two different `fashion` or `other` products still tie on the craft/function dimensions because those categories have no numeric spec fields to separate them. `tests/test_scoring_rubric_truth.py::test_spec_dim_can_separate_two_fashion_products` is `xfail(strict=True)` on main and turns green the day a discriminator exists.

**Ask.** Decide the merit source for fashion/other (a non-numeric merit table - material / craftsmanship / fit vocabulary from the specs prompt, or a reviews-derived signal), then build it behind its own default-OFF flag with the flag-OFF equality gate over the 167-record corpus; remove the xfail in the same PR.
"""))

ISSUES.append(("W4-12 follow-ups b-g + the mobile lane (honest tie scores, dead priority_match, doubled price_tiers keys, stale YouTube alias, camera doubled brand, strip false positive)", """
Follow-ups of PR #213 (W4-12 display contract, main `15e1fb89`; flags `ENABLE_SINGLE_VERDICT_MARGIN`, `ENABLE_SMART_PICK_VERDICT_CAPTION`; unflagged: the SSE verdict frame scrubbed, the alias review_summary and praise scrubbed, smart-pick/recent names deduped, the loser-only caption guard). One issue, six backend rows plus the mobile lane, each measured in the PR body.

- **W4-12b: honest tie SCORES.** First ship an OTA in which the client reads `scoring_v2.overall_score.winner_idx` first (`ResultsScreen.tsx:765-771`). Then the backend drops the tie nudge or ships `tie: true` behind its own flag. This also closes the owned margin/score inconsistency recorded in #213.
- **W4-12c: `priority_match` is dead.** Dict-shaped dimension winners are compared to a string at `home_routes.py:456`; the branch is reached on 0 of 22 rows. Revive it against both spellings behind its own flag and rewrite `tests/test_home_routes.py:302-341` and `:375-429` to the production shape (also recorded by W4-6a as R11b).
- **W4-12d: `price_tiers` keys still use the raw doubled spelling** (`scoring_service.py:1544`). Dedup them together with both readers (response_builder `value_match` / tier readers). They are unrendered today.
- **W4-12e: stale YouTube signal.** A stale `youtube_review_signal` ships on the BC alias while `ENABLE_YOUTUBE_SOURCE` is OFF.
- **W4-12f: camera doubled brand.** The camera path's `"Identified: {brand} {name}"` doubles the brand (`image_routes.py:376`).
- **W4-12g: strip false positive.** `strip_score_internals` fires on product names that look like score fragments ("5-Point Harness", any digit run followed by `-point`) and empties a sentence that merely names such a product, including our own fallback. Pre-existing at base; `text_sanitize.py` is untouched by #213.
- **Mobile lane:** retune the CTA thresholds to the calibrated scale (>= 8 strong / < 4 close agrees with the raw rule on 22 of 23 rows); derive `presentationWinnerIndex` from `winner_idx`; fall the share text back to `factual_verdict.line1` when `metadata.verdict_scrubbed` is set.
"""))

ISSUES.append(("tests: netguard follow-up nits from #207 (per-file guards, child-process report overwrite, thread-origin attribution, the RUNNER_TEMP pin, _price_service_globals)", """
Follow-ups of PR #207 (hermeticity: `tests/_netguard.py`, the teardown sentinel, the ratchet + baseline). The two large follow-ups are already filed (#210 reload identity, #211 the 90 egress-class baseline nodes); these are the small ones from the PR body, one checklist:

- [ ] **Per-file guards delegate to `NetworkBlocked`.** Several test files still carry their own autouse socket guards that raise a private exception; they should raise (or subclass) `tests._netguard.NetworkBlocked` so the process-wide report counts their attempts and the ratchet sees them.
- [ ] **A child pytest process overwrites the report mid-run.** A test in the CI-order set that spawns a child `pytest` inherits `QAREN_NETGUARD_REPORT` and overwrites the parent's report; the parent rewrites it at session end, so the final file is correct, but a crash between the two would leave the child's. The child should drop the variable (pop it from the subprocess env in the helper that spawns it).
- [ ] **Thread-origin attribution for the late-thread limit** (stated limit in #207): an attempt made from a non-main thread after the owning test finished is attributed to the next test or to none; record the spawning test id on the thread when the guard can see it.
- [ ] **Tighten the CI pin** `test_ci_runs_the_network_attempt_ratchet` (in `tests/test_hermeticity_pins.py`) to reject `$RUNNER_TEMP` / `${RUNNER_TEMP}` spellings on the TEST step's `env:` - GitHub Actions does not shell-expand `env:` values, so only `${{ runner.temp }}` is valid there; the pin currently accepts all three on either step.
- [ ] **Simplify `_price_service_globals`** in `tests/test_w49_extraction_catch_redaction.py` now that #185's cycle proof runs in a subprocess and an in-process pin checks `sys.modules` identity.
"""))


def main():
    dry = "--dry" in sys.argv
    for title, body in ISSUES:
        body = body.strip() + "\n"
        if dry:
            print("DRY", title, len(body))
            continue
        st, res = api("POST", f"/repos/{REPO}/issues", {"title": title, "body": body})
        if st != 201:
            print(f"FAILED status={st} {title[:60]} {str(res)[:200]}")
            continue
        print(f"created #{res['number']} {res['html_url']}")


if __name__ == "__main__":
    main()
