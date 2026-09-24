## W4-3: score the price you are willing to show (`ENABLE_PRESCORING_SHOWABLE_GUARD`, default OFF)

Finding `PO-RECORDED-MEASURED-04`. Backend only. There is no client change and no new client-read key.

### Defect
The correctness predicate that decides what the user may SEE, `is_price_showable(..., enforce_correctness=True)`, ran only at the response chokepoint in `response_builder.build_comparison_response`. That is AFTER `compute_scores` picked `winner_index` / `dimension_winners` / `win_margin` from the raw amount, and AFTER the verdict was handed the product data. So the payload shipped `price: unavailable` beside a 24.6-point win and a 49.0-point value-dimension margin, both decided by the hidden price. #113 fixed this shape for the currency half; the correctness half never got a pre-scoring pass.

### Design (mirrors #113)
- `price_service.prescoring_showable_guard_enabled()`: per-call `os.getenv`, truthy set `true/1/yes/on`, never memoised.
- `price_service.apply_prescoring_showable_guard(product_data)`: a pure in-place pass. Rows it leaves alone:
  - non-dict prices
  - already-pending prices (they keep `size_mismatch` / `unit_mismatch` and their own size)

  For every other row it takes the name as `full_name or name` and the category as `category or _infer_category_from_query(name)`, exactly as the chokepoint does, and delegates the WHOLE predicate to `is_price_showable(..., enforce_correctness=True)`. There is no source-method test of its own, so W4-1's `converted_usd` rows stay showable. A non-showable row is pended with `make_pending_price(currency=own, reason="pending_genuine", size=own)`, and `best_price` and `retailer` are nulled. The reason is stashed on the PRODUCT as `_prescoring_showable_rejected`, falling back to `not_showable` (R6).
- Both orchestrator twins (`compare_from_text` and `compare_from_text_streaming`) call the guard after `reconcile_pair_fairness` and BEFORE `apply_region_currency_guard` (R4, measured: showable-first gives BHD + `non_pdp_url`; region-first gives SAR + `region_currency_mismatch`). That is before the `specs`/`prices` yields and before `compute_scores`. `compute_scores` has only these two callers in `app/`, so no path skips the guard.
- In `response_builder`, a flag-gated harvest of the stash runs before the `unavailable` early-continue, so `metadata.guard_rejected` survives the upstream pend. Under the flag, the chokepoint's own append is idempotent on `(product_index, reason)` (R3: stash plus unpended price counts once).
- The chokepoint stays in place as the backstop for the direct/partial builder callers.

### Flag
| flag | default | effect ON | composition | activation order |
|---|---|---|---|---|
| `ENABLE_PRESCORING_SHOWABLE_GUARD` | OFF (per call, live-flippable) | A price the payload would show as unavailable is pended BEFORE scoring and the verdict. Winner, dimension winners, `scoring_v2`, `overview.confidence`, `value_badge` and the verdict input then read the same price the user sees. `metadata.guard_rejected` gains the new reason `not_showable`. | Needs `ENABLE_EXACT_PRICE_GATE` ON (the prod default); with it OFF only the pre-gate half of the predicate applies. Independent of W4-1/W4-2 code paths. | Own window, AFTER W4-1 (`ENABLE_SHOPPING_CURRENCY_TRUTH`) and W4-2 (`ENABLE_SHOPPING_DISCOVERY_URL_SPLIT`), so the pend set moves once (W4-2 un-pends google rows this guard would pend). `ENABLE_REGION_CURRENCY_GUARD` stays LAST. Follow-up `PO-RECORDED-MEASURED-04b` must land BEFORE this flag flips. |

### What the phones see (97b5f15, sync REST); these are result forks, which is why the flag exists
`scoring_v2` is the main results surface the phones render, and it CHANGES when the flag is ON. Measured through the real builder on this unit's own fixtures, `[a, b, winner_idx, win_margin]`:
- both prices behind a google link: `[84,72,0,12]` -> `[82,70,0,12]`
- one-sided, numeric specs: `[84,72,0,12]` -> `[82,73,0,9]`
- one-sided, spec-poor: `[84,76,0,8]` -> `[76,81,1,5]`, **the crown flips**

The review's figures (82/68 -> 79/66; spec-poor one-sided 75/68 -> 70/72 with the crown flipping) come from the reviewer's own fixture. The direction and the flip reproduce here; the magnitudes are input-dependent.

Other effects, all measured:
- Every pended product takes the **-4 price-authority overall penalty**: a pended price has no `source_method`, so it reads as `estimated`. This is most of the overall drop (R7a).
- **Manufactured cross-tier (R7b), pinned as CURRENT behaviour.** Scoring recomputes `price_tiers` after the guard and defaults a `None` price to `mid`. When both raw prices share a non-mid tier (pinned fixture: electronics 900 / 1800 BHD, both `luxury`), pending one manufactures `is_cross_tier`. That cuts the honest, SHOWABLE product's value score 40.5 -> 15.6, while crowning it value winner at the lower score. It reproduces only when both raw prices share a non-mid tier. Follow-up `PO-RECORDED-MEASURED-04b` (exclude a missing-price tier from `is_cross_tier`) is sequenced BEFORE this flag flips.
- A pended product's `breakdown.value_score` becomes its spec score rather than a sentinel, so pending an EXPENSIVE price raises it (R7c).
- **`overview.confidence` changes under the flag (R7d, on the surface the ruling actually names).** `overview.confidence` is computed by `scoring_service.compute_confidence(product_data)` in the orchestrator BEFORE the builder, so at HEAD it reads the raw price and under the flag it reads the pended price: the price leg of the confidence pills and `overview.confidence.overall` move for a pended product. `scoring_v2.confidence_details.price.method` already reads `estimated` for pended rows at HEAD (the chokepoint pends before `_build_scoring_v2`), so that sub-surface does not move; the top-level `overview.confidence` does. Found by the round-1 re-adversary and measured through the real functions.
- **`value_badge` changes under the flag.** `scoring_service.apply_value_badges(product_data, scoring_result)` runs after the guard in both twins. Measured on the one-sided spec-poor fixture through the real `apply_value_badges` and builder: flag OFF gives `['great_value', 'premium_price']`; flag ON gives `['fair_price', 'great_value']`. The product whose price is pended (and shows no figure) carries a `fair_price` badge, and the showable product flips from `premium_price` to `great_value`. `overview.products[i].value_badge` carries the change; on the both-google fixture the badges also move. The phones render `value_badge`. Found by the round-1 re-adversary; recorded as a canary item, not reworded in this unit (a badge for a product with no visible price is follow-up material for the FE copy row).
- The one-sided evidence line "relies on an indicative figure" is not literally honest for a card that shows no figure. It is stated here, not reworded in this unit.
- Verdict raw-price channel (R7e): with the flag ON, `best_price` is `None` in the verdict payload (pinned by `test_r7e`). Flag OFF still leaks it. The UNFLAGGED one-line follow-up is to null `best_price` in `_verdict_safe_product` whenever the price pends. `_verdict_safe_product` strips `_`-keys, so the stash never reaches the LLM prompt.
- The SSE `prices` event is byte-identical in both states (pinned by `test_09`, a no-change regression pin by construction). The SSE projection now stamps `guard_rejected` onto the real price dict at HEAD, which is harmless.
- **Disclosed leak (shared with #113):** the legacy BC `products` alias ships the raw product dicts wholesale. With the flag ON, `/products[i]/_prescoring_showable_rejected` appears there, exactly as #113's `_region_guard_rejected` does. It never appears in `overview.products[i]`, and with the flag OFF it is never set. The value is redundant with `metadata.guard_rejected`, and the 97b5f15 client ignores it. Pinned as current behaviour (`test_18`). Follow-up: scrub both `_`-stash keys from the BC alias. This corrects the spec's "no new response key" claim.

### KPI / canary
- `usable_exact_genuine` does NOT move from W4-3 alone: the displayed price is identical in both states (R9).
- Canary = `scoring_v2.overall_score` / `winner_idx`, the SSE `scores` event, `overview.confidence.overall` and `overview.products[i].value_badge`, split by `metadata.guard_rejected` reason.
- `not_showable` (estimated / sample / low-floor rows, which the predicate rejects before stamping) is a NEW reason and is counted separately from the url/identity reasons. The warmer log at `scripts/cron_warm_price_cache.py:246` will see it. Record the prod share of estimated rows on the first canary day.
- Do not canary on the final payload alone.

### Honest limits
- The corpus byte-identity harness is blind to this unit. It calls only `extract_price_from_html`, so it was run as a formality: base -> head -> base2 `results` arrays are equal on all 1656 records (canonical sha `a1b3460c28579fab` on all three; n_records 414, non_none 825). It would print the same digest on an always-ON tree.
- The flag-OFF proof is the unit pins (`test_10a/10b/10c/18`, which a reader that ignores the env reddens: 14 nodes) plus the Preserve suite and the per-call reader.
- The `not _prescoring_guard_on or` clause in the chokepoint's idempotent append has no pin of its own: making the append idempotent in every flag state is an equivalent mutant in practice (with the flag OFF the harvest is gated, so no duplicate entry can exist before the append). Behaviour coverage is complete; the clause's byte-identity justification is untested by construction.
- The LLM verdict text is not re-run for cached or partial paths.
- `win_margin == 0.0` can leave the index-0 tie-break when both prices are unshowable and there is no spec signal (`PO-VERDICT-TRUTH-02`).
- No live request was exercised; everything is offline and mocked.
- Round-1 history: the first green agent's mutation driver died mid-table and left `prescoring_showable_guard_enabled()` as `return True` on disk. The fix round restored the per-call reader from the recorded body (never `git checkout`), re-ran every gate on the final bytes, and the re-adversary rebuilt the green in a scratch copy to confirm the worktree matched it byte for byte before reviewing. The two scratch worktrees that driver left were removed by the orchestrator.

### Follow-ups
- `PO-RECORDED-MEASURED-04b`: exclude a missing-price tier from `is_cross_tier`, BEFORE the flip.
- `PO-RECORDED-MEASURED-04c`: the existing 321-file comm set makes 376 non-loopback attempts from 111 pre-existing nodes at base (367 from 108 at head), all fail-open. A repo-wide test netguard is its own unit, not this one.
- Unflagged `_verdict_safe_product`: null `best_price` whenever the price pends.
- Scrub `_region_guard_rejected` and `_prescoring_showable_rejected` from the BC `products` alias.
- FE copy row: a `value_badge` and a confidence pill for a product whose price is pended (see the two disclosures above).
- CLAUDE.md flag row at merge time, modelled on `ENABLE_REGION_CURRENCY_GUARD` (docs PR).

### Gates
- **Unit file:** 50/50 with the flag unset and 50/50 with `ENABLE_PRESCORING_SHOWABLE_GUARD=true` (the ruling's 47 plus three pins the fix round added: the per-call reader after an import-time flip, and the two flag-OFF E2E numbers).
- **Preserve, green in both flag states:** m18 14, m13_region 4, price_showable 19, m13_04 2, and exact_gate_flag_off_parity + kpi_metric + correctness_runtime_leaks + fragrance_content_quality = 117 (156 total, re-run by the re-adversary on the final bytes).
- **Mutation table:** 22 rows in the fix round, all killed, restored and sha-verified (`.qa-w4/W4-3-MUTATIONS.txt`), including the always-ON reader (`reader_true`: 14 red, re-run by the re-adversary from a byte snapshot), both call sites, order, harvest, idempotency, fallback, category, name, size, currency, and the W4-1 source-method mutation. The re-adversary added four more, all killed: `builder_flag_true` (10c), `skip_unstamped` (07[not_showable], r6), `reason_leak` (06 x5, 17), `stream_after_region` (r4 stream).
- **Comm gate:** HEAD over the 321-file set + the unit file, with the 180 s timeout, the 11 baseline deselects and the 4 `NETWORK_FLAKY_EXCLUDE` ids, under a scratch netguard plugin. 4528 + 7006 passed, 0 failed. `comm -13` against the recorded base is empty. One asymmetry found and closed: the base run's deselect file had CRLF on the four NETWORK_FLAKY lines, so the base did not deselect them; three of them are in the set and passed at base, and were re-run at HEAD without the deselect: 3 passed.
- **Lint:** `ruff --select E9,F63,F7,F82` clean; `py_compile` clean.
- **Post-rebase verification on main** (W4-1 #173 shifted the orchestrator anchors by +5; the call sites are located by symbol): the unit file re-run in both flag states on the rebased tree, plus the W4-1 and region-guard neighbours (`test_shopping_currency_truth`, `test_m18_region_guard_prescoring`, `test_m13_region_currency_guard`, `test_price_showable`), ruff + py_compile.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
