## What changes when `ENABLE_PRICE_NOT_LOST` is ON

The switch is OFF on web today, so nothing changes at the merge. If the owner opens it, PC1b changes exactly one answer, against PC1 as merged in #430.

**What changes:**
- **No hit at the typed size.** Some Shopify products have variant titles with no ml or oz word: a bare "30" / "100", "Small" / "Large", "Travel Size" / "Full Size", "30 cc", "30 millilitres", or the Arabic unit word. If such a product's variants carry different prices, it now gives **no hit** at a typed size.
  - Today, PC1's typed-size bind reads every such variant's size from the product title, binds the first variant, and that bottle's price is shown at the typed size.
- **The answer falls to the next source of the same request:** a sibling listing titled at the typed size, or a converted adapter row (PC1's no-genuine-park path), else pending.
  - On a cap miss with a converted-only 100 ml yield, the race miss now returns that converted row instead of the wrong bottle's own-shop price.
  - The converted row's own size binding decides whether it is the right bottle. A WooCommerce variable product can still yield its price-range minimum (PC1's L9).

**What does not change:**
- single-variant products, which includes the house pages;
- products whose variants all carry one price;
- variant titles that state ml or oz;
- queries without a size (PC1's stated limit L6 stays);
- the `ENABLE_VARIANT_MIN_PRICE_GUARD` path, which keeps the same gap (stated limit);
- the exact gate off.

**The cost.** Lost prices from that product, plus one changed answer on a cap miss (the first item below):
- **Typed bottle listed first.** The largest class: a unit-less two-price product whose typed bottle is listed first ("100" / "30", "Large" / "Small"), where today's answer is right by luck.
  - It now gives no hit.
  - On a cap miss with a converted yield, the converted row of another store is shown instead of the house's right own-shop price.
- **Unit-less variant before the exact one.** A unit-less variant listed before the exact "100ml" variant loses the exact variant's price too.
- **Option surcharge.** Two unit-less variants with an option surcharge ("Default Title" / "Gift Wrapped") give no hit.
- **Mixed product.** "30ml" / "Large", titled at the typed 100 ml, loses the "Large" price.
- **Format-only differences.** Prices that differ only in format ("10.000" / "10.00", or a float 10.0 beside "10.000") count as different.
- **Raw price strings.** The prices are compared as raw strings. So a zero, unparseable or unavailable sibling price ("Small" 10.000 / "Large" 0) counts as different, and that product gives no hit.
- **Another currency.** A unit-less store in another currency loses its first-variant converted price at the typed size, which was the wrong bottle.

## Summary

PC1b closes PC1's stated limit L10 (the incident data lane, S98-FIX).

- A new predicate, `price_service._pc1b_title_only_bind(variant, variants)`. It is True when two things hold:
  - the variant that PC1's J1 bound has no ml or oz size in its own title;
  - the product's variants carry more than one distinct price.
- It is called only in PC1's J1 branch, right after the binder's None check, and when True the product gives no hit.
- It reads no switch and no state, logs nothing, and on any fault returns False (PC1's bind is kept).
- No new switch, env name, log line, response key, cache write or network call. Switch OFF: byte-identical.
- The `CLAUDE.md` PC1 sentence states the rule (one line).
- A merged PC1b is "merged, NOT yet proven" until the owner's phone shows it in the switch's own window.

## Commits (4, on main 7e2e317c)

| | commit | what |
|---|---|---|
| C1 | e120439c | test: the RED rows (W1 x6, W2 x8 with the listing guard unset and on, W3 x2; PINs M5a x2, M5b x2, P1) |
| C2 | 1cace592 | test: the VG-path PIN row (the guard stays off the variant guard's own path), shown passing at base |
| C3 | 4d5b0380 | fix: the guard and the `CLAUDE.md` line |
| C4 | 3e838683 | test: the adversary's AR rows (ruling ORCH-PC1B-A). AR1 pins the switch-OFF answer on the guard's own shapes; AR2 and AR3 pin a unit-less bound variant that is not variants[0] |

## Evidence

- **RED at base:** 72 nodes. Exactly the 16 W nodes fail, with AssertionError only; 56 pass.
- **Before the guard,** with the VG PIN added: 16 failed and 57 passed (the VG PIN passes).
- **GREEN at the head:**
  - the PC1 file: 73 passed;
  - the 21 spec suites of PC1 (the touched behaviour): 1161 passed;
  - the six `CLAUDE.md` readers: 510 passed.
- **Mutants:**
  - Killed:
    - no guard;
    - no distinct-price condition (killed by P1 and every switch-ON row on a single-variant house product);
    - the product title read instead of the variant's own title;
    - the guard inverted;
    - the guard also on the variant guard's path (killed only by C2's PIN).
  - Equivalent by the fault rule, with evidence: the guard placed before the None check.
- **The switch-OFF walk** (336 cells a side, `ENABLE_LISTING_MATCH_GUARD` unset and on in every family, since it is on in production):
  - every switch-OFF and exact-off cell is identical to main;
  - with the switch ON, 20 of 84 cells change, only on unit-less multi-price shapes, 0 unexpected.
- **Revert:** reverting C3 gives C2 exactly.
- **One adversary** (Opus 5.5, the wrong-price lens plus the correctness duties): SOUND, with 0 blocking, 0 major and 7 minor findings (stated limits below). Of its 11 mutants of the guard, the unit's rows kill 5; 3 are equivalent or benign; 3 survived the unit's rows and are now caught by C4's AR rows.
- **Rebase and reruns at 4d5b0380 (C3):** no rebase was needed, because main is still 7e2e317c. The head is byte-identical to the GREEN bytes (the C2..C3 patch hash matches). The GREEN runs on those bytes: the PC1 file 73 passed, the 21 suites 1161 passed, the six readers 510 passed. The adversary's own run of the PC1 file at the head: 73 passed.
- **At the C4 head 3e838683:** the PC1 file 82 passed.
- **The comm set is the seven CI checks** (relay ruling).

## Stated limits

- **L-a.** The `ENABLE_VARIANT_MIN_PRICE_GUARD` path keeps the gap (its own switch, off on web).
- **L-b.** The lost-price costs above.
- **L-c.** Queries without a size on a unit-less multi-price product still price the first variant, labelled with the title's size: PC1's L6, unchanged.
- **L-d.** WooCommerce variable products and the UCP JSON PDP adapter are not covered (as PC1).
- **L-e.** A hermetic replay is not the production proof.
- **L-f.** The one-variant exemption is pre-existing and equal on main. A single unit-less variant that names another size ("30", "Tester", "Travel Size") under a title at the typed size still binds at that size. Unit-bearing tester, gift-set and "3.04 oz" first variants still bind, as before.
- **Closed by C4 (adversary minor m3).** A guard that reads the first variant's title, or fires only for variants[0], fails AR2 and AR3: measured on a scratch copy, 3 failed (AR2, AR3 cap0 and cap1), AssertionError only.
- **Closed by C4 (adversary minor m4).** A guard leaking into main's switch-OFF variants[0] branch fails AR1: measured on a scratch copy, 6 failed (AR1 x6), AssertionError only.
- **L-i.** "More than one distinct price" in `CLAUDE.md` and the docstring means more than one distinct raw price string over every dict variant (see the costs).

## Owner steps

None at the merge. `ENABLE_PRICE_NOT_LOST` stays OFF on web; its window is the owner's.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
