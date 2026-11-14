# RULINGS_INC_I1 (orchestrator S95-FIX, Claude Opus 5.5, 2026-11-14): rulings on .qa-s80/INC-I1_UNIT_SPEC.md (sha256 5539e84481bf...) and .qa-s80/INC-I1_SPEC_REVIEW.md (BLOCK, two blocking points). Binding on the RED and on GREEN

Precedence: this file, then the review's corrections, then the spec, then the rulings brief (specs/INC_I1_RULINGS_BRIEF.md) where they differ.

## A. The two blocking points

- I1-R1 (review B-1, Q-1) OPTION (a): under the guard every candidate whose image URL, link host, domain or source is denied by app/services/deny_hosts.py (is_denied_url / is_denied_source, the flag-free helpers; no host literal anywhere, per D03 r1i) is rejected on every tier, in every ENABLE_DATA_GUARDS_V2 state; a denied organic item never satisfies the Tier-3 precondition; the reason word is "denied". The leaf may import deny_hosts at module level (A-R06's import allowlist widens by that one module; the reason regex of A-R14 and I1-8 gains "denied"). RED rows: a Fragrantica-titled item that passes the relevance test is rejected with DG OFF and with DG ON; a denied organic item does not open Tier 3. Reason: H12 (g) and the binding VERIFY correction; the production mix is DG OFF.
- I1-R2 (review B-2, OQ-1, Q-2) The fragrance word is required (when the brand is empty) ONLY for products whose category is fragrances or other; any other category needs the line test alone. T20 becomes None; add the row brand '' / 'Tyger' / category other vs the poem title -> rejected with reason fragrance_word. Reason: the literal rule would blank every non-fragrance picture while the fragrance-only gate is off.

## B. The review's questions

- I1-R3 (Q-3) With an empty brand, EVERY significant line token must appear (not one). Reason: measured on the model, "Bleu de Chanel EDP" no longer accepts a Chanel No 5 picture, "stronger with you" no longer accepts "Because It's You", "Aventus 100 ml" no longer accepts Creed Viking, and the true golden and proof titles still pass. With a non-empty brand the brand test plus at least one significant line token stays (I1-3), with the alias subset rule of I1-R4.
- I1-R4 (Q-4, C-1) YES to all three precision fixes, each with its truth-table row: (a) host tokens are the registrable label(s) only (no TLD, no www); (b) an alias group expands only when the brand's kept tokens are a subset of that group; (c) a number directly followed by ml, oz, fl, g or gm (with or without a space) is not a line token.
- I1-R5 (Q-5, OQ-3) The knowledge graph's type text may satisfy the FRAGRANCE-WORD test only, never the brand or line test. Rows: {title 'Sauvage', type 'Perfume'} accepted; {title 'The Tyger', type 'Poem'} rejected with fragrance_word.
- I1-R6 (Q-6, OQ-10, CR-6) Recorded as a ruled interim deviation from the binding VERIFY 'Images' correction: the live path keeps the Serper tiers, narrowed by this guard; the end state (KB or retailer JSON-LD image only) is unchanged and belongs to the KB track.
- I1-R7 (Q-7, C-5) The knob clamps finite values to 1..10 (below 1 -> 1, above 10 -> 10); blank, garbage, inf and nan fall back to 5. Rows '0' -> 1, '-3' -> 1, '11' -> 10.
- I1-R8 (Q-8, C-3) PROOF ON THE PHONE is amended: (1) "Tyger": never the poem (the unit guarantees the test, not the placeholder; OQ-8); (2) each golden card shows the named product's own bottle, read by the owner, backed by each product's [IMG_RELEVANCE] tier= and any image race timeout line; (3) the noon picture is proven on a never-compared noon-won pair, or on the 2026-11-13 pair only after about 2026-11-20 21:19 UTC (the 7-day L1 and L2 price windows); the proof records the pair's resolved category and the account's consent version.
- I1-R9 (Q-9, OQ-11) Class SAFE, one adversary at GREEN, lens "correctness, including the deny-list guard of I1-R1 in both ENABLE_DATA_GUARDS_V2 states".
- I1-R10 (Q-10, C-10) A Tier-3 pick must have a raster path (the extension set the repository already uses); a page URL equal to an organic link is rejected.
- I1-R11 (Q-11) Moot under I1-R3 for an empty brand; the stop list stays as specified.

## C. The spec's open questions not settled above

- I1-R12 (OQ-2) YES: the plurals (perfumes, parfums, fragrances, colognes and the Arabic plural) are fragrance words.
- I1-R13 (OQ-4) Stated limit: with ENABLE_IMAGE_PIPELINE_V2 ON the noon image host is refused by D08's allowlist. Candidate follow-up INC-I1b (add the noon image CDN to IMAGE_CDN_HOSTS) before any V2 flip; filed in the ledger, not built here.
- I1-R14 (OQ-5) WIDENED: under ENABLE_IMAGE_RELEVANCE_GUARD the price-page override also requires https (one condition), so no http page image reaches the iPhone's grey tile. Reason: the same defect class as I1-5, one condition, inside the same flag.
- I1-R15 (OQ-6, C-7) Stated limit: Serper billing for num 5 is not measured hermetically; the relay reads the Serper dashboard counter delta of one comparison in the canary window, plus the [BUDGET] serper_images exhausted count, the [IMG_TIER] serper_images ms, the image race timeouts and the [IMG_RELEVANCE] reason mix.
- I1-R16 (OQ-7, OQ-13) The reason value for an accepted or empty line is "none"; the I1-8 grammar is kept (no extra field).
- I1-R17 (OQ-9) YES: the leaf and the RED files join .github/black-clean-paths.txt (the MON1 precedent).
- I1-R18 (OQ-12) The {bvlgari, bulgari} group is added LOCALLY in the leaf, never in price_service.
- I1-R19 (C-6) Owner steps: if ENABLE_PRICE_CACHE_WARMER is ever set true, ENABLE_IMAGE_RELEVANCE_GUARD joins price-warmer in that window; until then its 7-day noon cache writes carry no image_url (stated).
- I1-R20 (C-2, C-4, C-8, C-9, C-11, C-12, R-1 to R-10) Accepted as written: the mutation rows X9-X11 and M28-M33 join the table; B-P01 uses N1; RED file A imports app.services.price_service at module top; the Tier-3 organic list is organic[:10] to match the model's view; section 10 lists D1 F4's shopping and unified category word as out of scope (the ledger does not mark D1 F4 addressed); the row-text, line-number and pin-attribution fixes of R-2, R-3 and R-9.

## D. What happens next

- I1-R21 The RED round writes the RED files on the spec as amended by this file, proves each RED fails at base on an AssertionError only and each PIN is green at base, freezes the files with their sha256, and measures the base pass state of the files the unit touches (through harness/gate.py only). Then the orchestrator's gate, then GREEN with one adversary (I1-R9).
