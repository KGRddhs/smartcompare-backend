# INC-X1 v2 - VERIFIER REVIEW of X1_BRIEF_DRAFT.md (read-only round, 2026-11-11)

Role: verifier. Round class: READ-ONLY. Nothing was run: no pytest, jest, tsc, eslint, network, package manager, git command, production probe or .env read. Every file:line below was re-read in this run from the plain exports (backend and OTA client at a74caba7, store client 683f56c0) and the record copy. Short names follow the brief (PS, SCS, RB, SS, ES, KI, SR, IR, T1, G3). The deliverable under review is X1_BRIEF_DRAFT.md only. The finalizer did not touch PAGE_DESIGN_V2.md, and X1 has no owner-facing file and no HTML mock, so checks (4) and (5) do not apply. Nothing here says a production problem is fixed.

Verdict: NOT READY, with two small text corrections (V1, V2). The rest of the brief holds up: the stash-and-pop placement, the prompt invariant, E1-E6 except the parked case, the contract table, the D05 price entry and the proof structure re-measure true.

## 1. Findings that block

| # | Finding | Evidence (this run) | Correction |
|---|---|---|---|
| V1 | FALSE premise behind binding (1). E2's reason (brief line 57) and the closing note (line 265) say the two writers of the parked price store only converted prices, so E2 refuses every parked price. There are FOUR writers. SCS:8018 parks a GENUINE Tier-1 price whose url is a listing url (gated by `_park_listing_url_tier1_enabled`, SCS:7990). SCS:8744 parks any showable supplement-stage price, and SCS:8859 feeds it a page-scrape price, a method in the genuine set (PS:17066). E2 (`_is_genuine_bh_candidate`, PS:17106-17124) passes both. E3 refuses a listing url only when `exact_gate_enabled()` is on (PS:1951, PS:1964-1966). So "a converted or parked price is never eligible" is not guaranteed by E1-E6 as written. | SCS:7814, 8003, 8018, 8744 (grep of `_parked_price[`); SCS:7990-7996; SCS:8737-8746, 8859; PS:1951-1966; PS:17065-17087 | Either add an E7 that refuses a parked price by identity (this needs a marker on the parked dict, which touches SCS and so R-X1-15), or rule in words why a parked genuine PDP price may be shown. Fix the two sentences either way. |
| V2 | Internal contradiction in the D05 part. R-X1-11 makes a size pend's size entry `known / listing` when `offsize_listing.size_ml` is present. `run_job` writes a `kb_gaps` row only for a field whose state is `unknown` (KI:477-481), and `size` is a D05 field (KI:60-61). So with the X1 flag ON the size gap row disappears. That contradicts R-X1-12 (the KB ingest output is unchanged) and P8 (the kb_gaps rows equal the base sha's, flag OFF and ON). It also labels the product with another bottle's size, which conflicts with PAGE_DESIGN_V2's binding (2): a size is the product's only from the typed name or a price accepted at the pair's basis. | KI:60-61, KI:209-217, KI:476-481; brief lines 94, 95, 147 | For a size pend, give the size entry `other_size` (reason size_mismatch) whenever today's rule would not already say known; never `known / listing` from `offsize_listing`. Then R-X1-12 and P8 hold as written. |

## 2. Skeptic items (X1_SKEPTIC.md): disposition checked

| Item | Brief's disposition | Check in this run |
|---|---|---|
| 2.1 prompt invariant, KB variant side effect | applied | holds: the stash is a product-level `_` key, stripped at ES:2506-2510 before json.dumps at ES:2631-2638, the only prompt dump of a product dict in app/ (grep); `price.size` is never filled, so the KB variant row (from `_size_ml(price)`, KI:147-152) is unchanged |
| 2.2 lexicographic size, "7.5ml" | applied, refined | holds: PS:10588-10589; PS:4073 has no left boundary; PS:2083 and PS:2166 take a numeric min |
| 2.3 partial path never reconciles | stated limit; the pop covers all partials | holds: only callers SCS:4587, SCS:5340; partial builder SCS:3798, its builder call SCS:3880; callers SCS:4210, 5012, 5270; the STREAM_TIMEOUT bodies carry no products (SCS:5029-5037, 5293-5301). Minor: `_partial_product_data` is also reset at SCS:4363 and initialised at SCS:3382, not only at SCS:5065 (R-X1-22 wording) |
| 2.4 (b) value signal | applied | holds: SS:330-331 |
| 2.5 partner default, converted, global tier | applied | holds: E2 has the `_is_genuine_bh_candidate` semantics (PS:17106-17124); R-X1-7 requires the partner's own title |
| 2.6 the blank wins; winner_evidence | applied | holds: the string at SS:1008, carried at RB:1328-1346; no reader in either client tree (grep) |
| 2.7 amount and rule (c) | applied (S1-S9, L1-L3) | holds |
| 2.7 cache | rejected | the rejection survives: `get_comparison_cache` / `set_comparison_cache` (cache_service.py:777, :783) have no caller in app/; `metadata.cached` is `not nocache` (SCS:4755, 5506; RB:2104). Wording slip: `cache_hit` is a response-level "any product" flag (RB:55, RB:71-77), not a per-price marker; the conclusion still holds |
| 2.7 a proof that passes falsely | applied | holds, except V1 (a parked genuine price can still reach S3-S5) |
| G1-G7, section 3 | applied or confirmed | holds: HR:571-574; fieldStatusView.ts:21, :52, :58; ResultsContent.tsx:212 @a74caba7 and :159 @683f56c0; en.json:149/705/796 and ar.json:146/702 @a74caba7; sourceMethod.ts:13-15 |

No skeptic item is left unaddressed. Item 2.7 "cannot pass falsely" is applied incompletely, through V1.

## 3. New or changed claims re-measured

True at the cited lines: PS:157, 1439, 2005-2018, 2021-2045, 2076-2097, 2134-2148, 2340-2417, 4905-4923, 9371-9387, 17090-17124; RB:49-80, 842-852, 873-881, 1328-1346, 1700-1767, 1945-1951, 2079, 2259-2268; SCS:3821, 3909, 3946-3951, 4586-4594, 5339-5345, 5379-5435, 5478-5483, 5510-5516, 5633, 7036-7045, 7100-7128, 7866-7878; SS:1006-1008, 1766-1779, 2457-2470, 3171-3175, 3240-3248; KI:147-152, 165-248, 251-260, 264-288; woocommerce_service.py:251-279; SR:764-794; database_service.py:471-486; types.ts:60-73, formatNumber.ts:96, fieldStatusView.ts:6 and ResultsAccordion.tsx:135-153 @a74caba7; T1:32, 59, 117, 123, 129, 172, 176; IR:83, 93, 94, 100, 103, 109, 140-148, 162, 175; G3:283-291, 351. A grep of both export trees finds no `offsize`, `size_fair` or `SIZE_FAIR` token.

False: V1 (the parked-price writers). Imprecise but harmless: the R-X1-22 reset line and the `cache_hit` wording (section 2).

## 4. Binding decisions of the finalizer prompt

| Binding | Followed? |
|---|---|
| (1) design (a); amount null; a new key not colliding with 'listed'; scores, verdict, savings, winner unchanged; per-ml only between two genuine one-size-title Bahrain listings; converted or parked never eligible; a five-line (b) appendix | yes, except "parked never eligible" (V1) |
| (2) projection in RB after the verdict, from a product stash popped by name on every path; the prompt pinned | yes (R-X1-1 to R-X1-5, P2, P4) |
| (3) the dormant D05 defect closed in the same unit | yes for the price line; the size entry needs V2 |
| (4) the proof restated; saved-row keys and log lines named; visible only after the client OTA | yes (section 4). Gap: IR:162 also requires each proof to include at least one of pairs 4-5 the first time it runs (the W4 canary used pairs 1-3). Section 4 names only pairs 1-3. Add pair 4 or 5 as a second negative control; with 3 comparisons a day (IR:83) that means a second day or the N6 choice |

## 5. Cross-document conflicts for the orchestrator

| # | Conflict | Where |
|---|---|---|
| C1 | Unit of the per-ml line. The brief carries `per_100ml` and keeps O3 open with "per 100 ml" as the default. PAGE_DESIGN_V2 treats "per ml" as ruled and calls a per-100-ml print an unruled wording change. The owner's words say "a per-ml line". One of the two must change. | brief R-X1-7, O3; wf/v2p/06.md:12, wf/v2p/12.md:34 |
| C2 | String keys. The brief drafts `results.price.offsize.withSize / .per100 / .caption`; PAGE_DESIGN_V2 replaces them with `results.price.withSize`, `results.price.perMl`, `results.price.differentSizes`. The brief's own R-X1-21 asks for one price card and one Arabic read. | brief lines 112-118; wf/v2p/06.md:13 |
| C3 | Sizes on every shown price. PAGE_DESIGN_V2 (E-X1-a) wants `size_ml` / `per_100ml` on every Bahrain price whose own title passes E4. The brief limits them to size-pended pairs (SL12). | brief R-X1-7, SL12; wf/v2p/06.md:11 |
| C4 | Proof marker. PAGE_DESIGN_V2 asks each claim to cite `cache_hit: false`; the brief rejects that with a sound reason. Align the page document to the brief. | brief appendix B 2.7; wf/v2p/11.md:19 |

## 6. Hygiene

UTF-8, LF only, ASCII except Arabic. No credential shape and no personal value. The word "fixed" appears only in negations (brief lines 3 and 197). No date is promised to the owner.

## UNVERIFIED in this round

The production state of ENABLE_EXACT_PRICE_GATE and of the listing-url park flag (it decides how far V1 reaches; never probed, H2). Whether the supplement stage can run on a pair that carries a size target. Everything the brief itself lists as UNVERIFIED (Q1-Q5, the Arabic wording, the ledger line for the N5 / N5b ruling).
