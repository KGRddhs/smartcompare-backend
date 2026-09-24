## W4-10: dimension_winners labels, the verdict prompt's leaders and tier lines, and tradeoffs agree with the display spelling again (CR-DELTA-CORRECTNESS-07(a))

### Live effect on the main path (read this first)
From this deploy on, the verdict system prompt, `overview.tradeoffs` and `overview.winner.key_tradeoff` change on both the sync and SSE paths for three input classes. This was measured BASE b63a8368 vs HEAD through the real `compute_scores`, `_display_product_names`, `compute_tradeoff_pairs`, `deterministic_verdict_fields` and `build_scores_summary`.
1. **Brand-repeating pairs:** the product's `name` already starts with its `brand` (`Xerjoff` / `Xerjoff Naxos`, `TOM FORD` / `TOM FORD OUD WOOD`, Arabic brand repeats, brand == name). **Every camera (vision) compare with a non-empty brand is in this class by construction:** `_product_display_identity` (`scs:1174-1176`) builds the vision name as `dedup_brand_name(brand, name)`, and `scs:4876` stores that as the product_data `name`, so it always starts with the brand, and the raw `f"{brand} {name}"` at `:1554` then doubled it.
2. **None-brand pairs:** labels go from `None Naxos` to `Naxos`.
3. **Whitespace-padded names:** labels go from `Xerjoff   Naxos` to `Xerjoff Naxos`.

For compares in these classes: the `Dimension leaders:` line uses the same spelling as `Score winner:` (for example `presentation=Xerjoff Xerjoff Naxos` becomes `presentation=Xerjoff Naxos`); the tier lines show the real tier (`mid` / `premium`) instead of `price tier: unknown`; `tradeoffs` goes from `[]` to one pair; and `key_tradeoff` goes from `''` to deterministic prose such as `Erba Pura stays competitive on longevity.`

Byte-identical (pinned and measured): the non-repeating CONTROL pair, the empty-brand shape and the `Apple` / `Applesauce` shape. A plain text compare whose `name` does not repeat the brand and has no None/padding gets an unchanged prompt; this is pinned against the b63a8368 literal.

The same prompt also feeds the self-critique regen and `pain_workflow_context`, so the LLM's `winner_reason` / `key_tradeoff` prose may shift on these pairs. That cannot be measured offline. Every measured change is a repair in the intended direction.

**Canary / KPI owner: expect verdict-prompt and `key_tradeoff` traffic to move on the camera path.** This covers every branded vision compare, not just a fragrance-house subset, plus None-brand and whitespace-padded text pairs.

Shadow A/B baselines captured before this fix are not comparable for any of the three classes. The offline shadow prompt now spells names the way production does, including the `str(x or '')` coercion of a None brand from an L2 row.

### Defect
M21-W3 `7fb0b0d4` (PR #129, merge `eb331cb7`) moved the display half of the name spelling onto `text_sanitize.dedup_brand_name`. That half covers `_display_product_names` and `winner_evidence`. It left `compute_scores`' internal `product_names` on the raw `f"{brand} {name}".strip()`. `compute_tradeoff_pairs` joins the two halves by string equality. So for every brand-repeating pair:
- `tradeoffs == []`, and the deterministic `key_tradeoff` is empty.
- On the unflagged hard-cap partial path, the runner-up caption ships blank.
- The persisted and SSE `dimension_winners` carry the doubled brand.
- `build_scores_summary` looks the tier up by the deduped name in the raw-keyed `price_tiers` map, so the tier reads `unknown`.

Before `7fb0b0d4` both halves built the identical f-string. This PR restores that equality.

### Design (unflagged, per R1)
1. `scoring_service.compute_scores`: `product_names = [dedup_brand_name(str(p.get('brand') or ''), str(p.get('name') or '')) for p in products_data]`, using a function-local import like its two siblings. The `str(x or "")` coercion follows ruling R4: a direct caller passing a non-str brand or name on a tied pair must not newly raise.
2. `scoring_service.build_scores_summary` (R3): the tier comes from `price_tiers_by_index[product_i]`. The legacy `price_tiers.get(name)` lookup is the fallback and `unknown` is the last resort.
3. `scripts/shadow_experiments._compute_scores_summary_offline` (R2): names are built with the identical `text_sanitize.dedup_brand_name` call, plus the same coercion. It deliberately does **not** import `structured_comparison_service`. That module constructs AsyncOpenAI at import time, which would make the documented-offline `prepare` need `OPENAI_API_KEY`. Without the key, its broad except would swallow the error and write `scores_summary=""` for every input.

The `price_tiers` **keys stay raw**. No phone reads them and the fix does not need them. `response_builder`'s raw-key readers keep matching.

### Flag row
| name | default | effect ON | composition | activation order |
|---|---|---|---|---|
| none (unflagged regression fix, R1) | n/a | n/a: live on deploy | Independent of `ENABLE_WINNER_PROSE_RECONCILE`. This fix is a **precondition** for flipping that flag; flipping it today would ship a blank `key_tradeoff` on every brand-repeating pair. | Merged after W4-1 (#173): its scs anchors after `:1214` shifted by +5, and there was no textual conflict. |

### Client impact (phones at 97b5f15)
- No component reads `dimension_winners`, `price_tiers` or `tradeoffs`; they appear only in `types.ts:253-254/:351-352`.
- `key_tradeoff` is rendered via `ResultsContent.tsx:155 → :388 → RunnerUpWinsCard.tsx:88-95`. It self-hides when empty or when the text matches `SCORE_INTERNALS_RE`, and the new deterministic prose ("X stays competitive on longevity.") does not match that pattern.
- No new key, no removed key, no type change. `eas update` is **not** required.
- No jest/tsc gate was run: zero client files changed and there is zero contract change.

### KPI / canary lines
- **Hard-cap partials on brand-repeating, None-brand and whitespace-padded pairs (every branded camera compare included):** `overview.winner.key_tradeoff` goes from `""` to prose, and `overview.tradeoffs` goes from `[]` to one pair.
- **Persisted `scoring.dimension_winners` labels:** rows written after this merge carry the deduped spelling; rows written before carry the raw one. No reader joins on these labels.
- **Watch** verdict prose drift on the camera path first, because every branded vision compare is brand-repeating by construction. Then watch brand-repeating text pairs.

### Honest limits
1. The SSE generator was not driven end to end. The fix is producer-side, so it cannot depend on which path runs, and `test_streaming` is in the comm set.
2. `_partial_product_names`' fallback (`scs:~3187`, bare `name`, used only on a cancel during Phase-1) is still a third spelling. It is out of scope.
3. Parity does not guarantee a non-empty pair: an all-tie winner legitimately yields `[]`.
4. The persisted corpus is mixed, as above, and there is no backfill.
5. `compute_scores` still raises `AttributeError` on a non-str brand or name for a **non-degenerate** pair. That happens earlier, at `_product_name_for_evidence` `:914`, is pre-existing, and is out of scope. The coercion only stops the new `:1554` site from adding a raise where the raw f-string had none.
6. The shadow names coerce non-str input where production's `_display_product_names` would raise. The two diverge only on inputs production cannot score.
7. The None-brand and whitespace-padded before/after values above come from the re-adversary's BASE-vs-HEAD probe; the camera construction claim was re-verified in code (`scs:1174-1176`, `:4876`).

### Follow-ups
- (a) `home_routes._select_smart_pick` `priority_match`: when it is repaired, compare against `dedup_brand_name(...)` and handle the mixed old/new persisted corpus. The branch is dead today (dict compared to str).
- (b) `tests/test_home_routes.py:311` and `:400-428` pin a str-valued `dimension_winners` shape that production never writes. This is test debt.
- (c) Follow-up 07a2 (`price tier: unknown`) is **closed** by this unit (R3).
- (d) Pre-existing test debt found by the Preserve run, not touched here: four SSE tests in `tests/test_winner_prose_reconciliation.py` (`test_sse_verdict_event_uses_deterministic_winner_index`, `test_sse_verdict_and_complete_agree_on_winner`, `test_sse_flag_off_verdict_event_uses_deterministic_index`, `test_sse_flag_off_verdict_and_complete_agree_on_the_reason`) attempt a live `openai.moderations.create` to api.openai.com through `content_safety_service.moderate_output` (`scs:4686`); without a network block that call can hang a run in the TLS handshake. Mock `moderate_output` or add a socket guard to that file.

### Gates
- `tests/test_tradeoffs_dedup_parity.py`: 43/43 in the default env and with every scoring flag ON. Core invariants are parametrised all_off/all_on. It adds pin R2-e, `test_shadow_offline_none_brand_names_read_like_production`, and an autouse socket guard that fails a test on any non-loopback connect/getaddrinfo, even a swallowed one (positive control measured: two swallowed attempts go ERROR at teardown, loopback is allowed).
- Preserve-8 (scoring_service, winner_prose_reconciliation, m21_brand_dedup, home_routes, shadow_experiments, fragrance_content_quality, value_badge_category_dims, category_dimensions) plus the unit file: 476 passed (433 + 43), run on the pinned venv behind a process-wide network block (see follow-up (d): 12 blocked `getaddrinfo('api.openai.com')` attempts from the four pre-existing SSE tests, zero from this unit).
- Comm gate: the 78-file module-reference set plus the unit file at HEAD gives 0 failures. BASE b63a8368 also gives 0. `comm -13` is empty.
- Byte-identity corpus gate: N/A. The unit is unflagged and not on the price path. The identical, empty comm failure sets and the CONTROL-literal pins are the identity proof.
- ruff E9/F63/F7/F82 is clean; py_compile is clean.
- Mutation table: 18 mutations, each restored from a byte snapshot and sha-verified (`.qa-w4/W4-10-MUTATIONS.txt`):
  - argument swap: 20 red
  - keys-deduped: 3
  - R2-without-R3: 7
  - only-:1554: 7
  - only-R3: 19
  - no-shadow: 3
  - no-coercion: 3
  - str-only (compute_scores labels without `or ''`): 2 (`none_brand_labels_match_winner_evidence_spelling` plus R2-e)
  - shadow str-only (shadow names without `or ''`): 1 (R2-e)
  - R3 index-only: 1
  - R3 name-first: 1
  - shadow imports scs: 2
  - shadow no-coercion: 1
  - revert-:1554: 19
  - display-in-label: 15 (caption repaired, persisted label still wrong, which is the R6 point)
  - casefold as the spec wrote it: 19
  - dedup-at-call-only: 0 (no other reader)
  - module-scope import: 0 (a review item)
- Pins 7 (every row except `dimension_winners`), 9 and 10 (every row except `apple_applesauce`) are Preserve decoration per R6, kept and labelled.
- Post-rebase verification on main (W4-1 #173 and the W3 merges landed since b63a8368): the unit file re-run on the rebased tree, ruff + py_compile on the two changed modules.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
