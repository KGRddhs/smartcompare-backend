## Summary

PC1 PARK-KEEP-GENUINE, an incident data-lane unit. It sits behind the existing switch `ENABLE_PRICE_NOT_LOST`, which is **OFF on web**. No new switch, env name, log line or response key.

- **G1: keep the genuine park.** Under the switch, a converted-only adapter yield that arrives after a genuine house hit never replaces the genuine park on the request.
  - Code: `structured_comparison_service._pc1_genuine_park`, read as the third condition at the converted park of `_consume_adapter_prefetch`.
  - Without it, the cap miss returns the converted row instead of the house's own price.
- **J: the typed-size variant.** Under the same switch, with `ENABLE_EXACT_PRICE_GATE` on (its default) and `ENABLE_VARIANT_MIN_PRICE_GUARD` off:
  - J1: the Shopify matcher prices the variant of the typed size with the variant guard's own binder (`price_service._pc1_typed_variant_bind`). A product with no variant of the typed size gives no hit.
  - J2: the size label is sorted as numbers (`_pc1_size_fix_enabled`).
  - The owner confirmed the size fix inside this unit.
- **Switch OFF: byte-identical**, walked cell by cell (see Evidence). Nothing live changes at the merge.
- A merged PC1 is "merged, NOT yet proven" until the owner's phone shows the case in the switch's own window.

## L10 (stated limit, named first): variant titles without an ml or oz word

Some shops' variant titles carry no ml or oz word: a bare "30" / "100", "Small" / "Large", "Travel Size" / "Full Size", "cc", "millilitres", or the Arabic unit word.

- The binder then reads every variant's size from the product title, so J1 binds the first variant, and its price can be shown at the typed size.
- Main does exactly the same, and so does the variant guard's own path. Both adversaries measured this, so it is **not a regression**.
- G1 and the unit-bearing case (each variant's own title states its size in ml or oz) are fixed by this PR.
- The guard for L10 is unit **PC1b**, the first unit after this one, with its failing rows first. It binds only a variant whose own title states the size (or a single-price product); otherwise the product gives no hit, a lost price and never a wrong one.
- The `CLAUDE.md` sentence now states this (commit C5).

The owner question, corrected:

> When a shop sells one perfume in several bottle sizes, the price of the first size it lists can today appear under the size you typed. This fix stops that when the shop names each bottle's size in ml or oz, and it switches on together with the price-not-lost switch. For shops that list sizes without a unit (for example "Small" and "Large"), the follow-up PC1b stops it.

## Commits (5, on main 88c8410e)

| | commit | what |
|---|---|---|
| C1 | 43204941 | test: the G1 RED rows |
| C2 | 9fde11ed | fix: G1, `_pc1_genuine_park` and the third condition |
| C3 | 54dca1f1 | fix: J1 and J2 with their rows (the size fix as one commit) |
| C4 | 1a129ae3 | test: R07b, a listing-url park is still replaced (a G1 mutation row) |
| C5 | d4570eb4 | docs: the CLAUDE.md sentence states L10 |

To drop the size fix: `git revert` C5, then C3. This was measured on this branch. The code and `CLAUDE.md` come back exactly as at C2, and the only other difference is C4's 19 test lines.

## Evidence

- **RED.**
  - `tests/test_pc1_park_keep_genuine.py`, 51 nodes.
  - The head's RED file at the old base fails 9 nodes with AssertionError only: R04, R15, R15b, R15c, R16, and R19 x4.
  - At the head, all 51 pass.
- **GREEN.**
  - The 21 spec suites (the touched behaviour): 1161 passed on both sides.
  - The switch-OFF walk: 0 of 100 cells differ.
  - Every mutant of the mutation table is killed, after rows were added.
  - The revert of the size fix gives the G1-only code.
- **Two adversaries (Opus 5.5).**
  - **Correctness: SOUND**, 0 blocking, 0 major, 7 minor.
    - Its own switch-OFF walk was IDENTICAL to main: 60 of 60 task cells, 16 of 16 matcher cells, 16 of 16 pair cells, 2 of 2 cross-call cells. With `ENABLE_EXACT_PRICE_GATE=false`: 16 of 16 and 4 of 4. Both `ENABLE_GENUINE_PRICE_PRIORITY` states.
    - 12 mutants of its own: the RED file kills 9; the walk separates the other 3.
    - The revert of C3 gives C2 plus C4.
  - **Wrong-price**: one major, F1, which the relay ruled to stated limit L10 above, and 6 minors, which are stated limits below.
    - G1 closes the reported order in all 24 switch-ON cells walked; main loses 2.
    - J1 binds the typed size for unit-bearing variant titles ("30 ML", "30ml", "1 oz").
- **Rebase onto main 88c8410e**: clean. The code diff's patch-id is unchanged and the RED file's blob is unchanged.
- **Reruns at d4570eb4, every `ENABLE_*` removed:**
  - the PC1 file: 51 passed (80 s);
  - the 21 spec suites: 1161 passed (46 s);
  - the six `CLAUDE.md` readers: 510 passed (22 s).
- **The comm set is the seven CI checks** (relay ruling).

## Stated limits

- **L1.** A hermetic replay is not the production proof. Every row is "merged, NOT yet proven" until the phone shows it.
- **L2.** The house page's stock flag and variant titles of 18 Nov were not read: the shop answered 429. "Default Title" stands for its one variant.
- **L3.** One competing seller of 18 Nov is not in the records. Its row pins both answers.
- **L4.** `_fetch_product_data` is not driven. The cap is replayed by `asyncio.wait_for` and the handler's own call.
- **L5.** The converted search-link row's link and title in the replay are synthetic (inferred).
- **L6.** `listing_size_ml` reads the title's strict ml token first, so J2 does not change the compared size when the title states one.
  - An untyped title that states another size than its first variant stays mislabelled; the variant guard closes it.
  - For an untyped query on a multi-variant product titled at one size, the first variant's price is shown with that size (main and head alike).
- **L7.** J1's "no readable size anywhere -> the first variant" branch is not pinned.
- **L8.** An out-of-stock genuine park is kept over an in-stock converted yield (P2's own order, confirmed by reading).
- **L9.** WooCommerce variable products are not covered by J; the variant guard covers them.
- **L10.** Variant titles without an ml or oz word (above).
- **L11.** The park is keyed by `full_name` only, and `GET /text/prices/{product}` runs the regions on one service instance.
  - With the switch ON, one region's genuine park can withhold another region's converted answer on that endpoint.
  - It is a lost price, not a wrong one, and the shipped client does not call that endpoint. A park-write-only guard is measured as equivalent on every same-call path, for PC1b.
- **L12.** J2 is a heuristic label: the numeric minimum of the title's and the first variant's sizes.
  - It fixes the small-first order and mislabels the large-first order for an untyped query.
  - The client-visible `size_ml` does not move; the reach is the price dict's `size` field.
- **L13.** `_pc1_genuine_park` is a strict subset of the complement of the P2 replaceable test, not its exact complement. The two agree on every park reachable at the third condition (2,204 park shapes probed).
- **L14.** The RED set has no row with an explicit OFF value and no row for J's exact-gate rollback. Two mutants survive the RED file, and an adversary's walk catches both. The rows go to PC1b's RED.
- **L15.** C3's test file is the gated file plus insertions (R15c, R17b, an ounce fixture), not byte-identical to it; C4 is test-only.
- **L16.** The UCP JSON PDP adapter (`ENABLE_UCP_JSON_PRICE`, default off) is not covered by J.
- **L17.** Pre-existing, not in this diff: `shop_best` is the lowest Shopify amount across sources. When that is a converted row, `_p2_park_reseller` returns before it parks, and the house's genuine row of the same request is lost. A P2 follow-up unit.
- The spec's own "L10, nothing was run" is void: everything above was run.

## Owner steps

None at the merge. `ENABLE_PRICE_NOT_LOST` stays OFF on web. Its window is the owner's: one switch per window, with the owner at the phone and the spec's stop rule (any side shown with a converted method, or at a size other than the typed one: switch off).

🤖 Generated with [Claude Code](https://claude.com/claude-code)
