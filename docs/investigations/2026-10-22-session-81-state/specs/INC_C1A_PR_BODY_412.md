## INC-C1a SIZE-LABEL (client, over the air; declares `price_size`)

**What.** The result page's two product cards draw the bottle size and a per-ml line beside a shown price, from the additive server keys of the data lane's INC-P2 PRICE-NOT-LOST (dark `ENABLE_PRICE_NOT_LOST`):
- `price.size_ml`: int, set only when the price's own listing names exactly one size.
- `price.per_ml`: in the price's own currency.
- `metadata.pair_price_sizes.mode`: `same_size`, `different_sizes` or `unknown`.

The app also declares the capability token `price_size` (`CLIENT_CAPABILITIES`, so `X-Client-Capabilities: price_size` rides every request that builds context headers). With that token INC-P2 places a price for a different bottle size in `price.amount`, instead of leaving that side pending. Without this unit the owner would still see "No confirmed price yet" on one side after the INC-P2 switch opens.

**How.**
- **Size label:** a shown price (finite amount, not `unavailable`) with a valid `size_ml` (an integer 1..9999) renders `results.price.withSize`: "58.110 BHD · 100 ml" in English and "{{price}} · {{size}} مل" in Arabic. `{{price}}` is today's whole formatted price, converted label included.
- **Per-ml line:** shown under the price only when the server sends `per_ml` > 0, using `results.price.perMl` ("0.5811 BHD per ml"). It has the currency's minor unit + 1 digits, through a new optional 4th `fractionDigits` parameter of `formatNumber.formatPrice`; every 3-argument caller is byte-identical. The client never computes per ml itself.
- **Different sizes:** when the mode is `different_sizes` and both prices are shown, one neutral caption: "Different bottle sizes, so we do not compare the prices." The client makes no cheaper claim of its own (it makes none today either; the server owns the bars and the verdict).
- **Without the keys:** a body without them renders today's text exactly (P1 golden). A card on the S81-11 honest line never shows a size.
- **`price_asof` is NOT declared:** that switches a server behaviour, and the dated wording belongs to INC-C1.

**Files.**
- 6 src files: `ResultsContent.tsx`, `requestContext.ts`, `types.ts`, `formatNumber.ts`, `en.json` and `ar.json` (3 keys each).
- The new RED file `SmartCompareApp/__tests__/c1a/sizeLabel.c1a.test.tsx` (9 tests).
- 6 moved-pin test files.
- `tests/test_s81_12_legal_v3.py`: the re-record of the i18n key count and name hash, ruling CC-8.

**Bundle rule:** no package, lock or `app.json` change; `app.json` stays 1.0.0.

### Server effect today
None on main fd983471. The only server reader of `X-Client-Capabilities` is `kb_serve.client_price_asof`, which looks for `price_asof`. INC-P2 will read `price_size` by the orchestrator's ruling of 2026-11-16 20:50. The header now also rides the camera upload and its 401 retry.

### Gates
- **RED** (wf_05274256-05f): C1-C7 fail at base on assertions; P1-P2 pass; the prototype passes 9 of 9; mutants MC1-MC8 are killed; the restore of the base files is proven.
- **GREEN** (wf_4e8febf5-21a, then GREEN-2 wf_369c08f5-a91): commit 2abcbf44.
  - The 18 moved pins are edited without weakening any assertion. Exact header objects gain `x-client-capabilities: price_size`, B9 asserts `['price_size']`, and the two catalog leaf counts go 1011 -> 1014.
  - The legal-v3 pin is re-recorded (CC-8): the 1014 keys minus the three new ones hash to exactly the recorded base.
  - The nine backend fences that read client files pass 303 of 303.
  - The full jest suite, both `--runInBand` pair orders with `requestHeaders.s81_08`, tsc (0 errors), eslint (0 errors, no new warning) and the pre-commit hook all pass. The full suite fails only the 4 accepted nativeBundle.w37 nodes.
- **Main merged in:** fd983471 (#411, backend files only, no overlap), merge commit 866668c4. The full jest suite re-run on the merged head: 4,081 tests, only the 4 accepted nodes fail.
- **ONE ADVERSARY** (SAFE by LC-1): **SOUND**. MIN-1..MIN-4 are stated limits L-6..L-9 below.

### Stated limits
- L-1 a converted price's per-ml line carries no converted marker of its own; the price line and the caption above it carry it.
- L-2 the converted label still appears twice on a card (price line and caption), as today. That is T7-08, for INC-C1.
- L-3 a size above 9999 ml or a non-integer size is not drawn; sizes are not grouped ("1000 ml").
- L-4 not pinned: the per-ml line's order against the provenance line, and the position of the different-sizes caption.
- L-5 nothing changes on the phone until the server sends the keys (INC-P2 with `ENABLE_PRICE_NOT_LOST` on). The header goes out from the first launch of the update.
- L-6 (MIN-1) a zero or negative amount counts as shown, so it would draw a size if the server sent one. INC-P2 stamps `size_ml` only on an amount > 0.
- L-7 (MIN-2) the copy.s11 docblock still says 1,011 leaves (a comment only).
- L-8 (MIN-3) handled: main fd983471 was merged in and the full jest suite re-run.
- L-9 (MIN-4) the frozen RED file carries two `import/first` lint warnings (the S81-11 suite pattern; outside CI's lint scope).

### Owner steps
1. Merge on the orchestrator's dated word at 7 of 7.
2. The orchestrator publishes the over-the-air update with its own agents (runtime 1.0.0; the bundle is exactly the six src files over the current update). This lane publishes nothing.

### Proof on the phone (merged, NOT yet proven until then)
After the update's second cold start and with `ENABLE_PRICE_NOT_LOST` on: a pair found at different bottle sizes (for example Ted Baker M 30ml vs Dior Sauvage 100 ML Edp) shows BOTH prices, each with its size and a per-ml line, plus the line "Different bottle sizes, so we do not compare the prices." Before INC-P2 is on, the page looks exactly as today.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
