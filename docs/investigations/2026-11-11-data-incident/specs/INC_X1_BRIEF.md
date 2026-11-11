# INC-X1 SIZE-FAIRNESS - FILED BRIEF (2026-11-12)

Unit: INC-X1 (incident report item 4, fix row X1, record/incident/INCIDENT_AND_DATA_PLAN_2026-11-11.md:100). Filed by the brief finalizer from X1_BRIEF_DRAFT.md (v2), its verifier review X1_V2_VERIFY.md (NOT_READY on V1 and V2) and the orchestrator's binding corrections X1_BRIEF_CORRECTIONS.md (R-X1-C1 to R-X1-C5), with the string keys of PAGE_DESIGN_V2.md section 3 and table 6a. Every correction is applied in place below; nothing in an appendix overrides the body. Nothing here says a production problem is fixed: X1 is not built, and once merged it is "merged, NOT yet proven" until the owner's phone shows it (H6).

Base: 6b909e0a92067d6b3562eee325e4956c116441f7 (merge of #399, S81-04c), worktree C:/Users/SynAckITPC/Documents/AI/sc-inc-x1. Measured in this round with git and file reads only. Between a74caba7 (the draft's base) and 6b909e0a, `git diff` is empty for PS, SCS, RB, KI, SS, HR, source_router.py and the whole SmartCompareApp/ tree, so every cite into those files carries over unchanged and was re-read where a correction touches it; extraction_service.py moved by +16 lines in the range the brief cites (S81-04c hunks at 1568-1913), so its cites are restated at the new lines.

Short names: PS = app/services/price_service.py, SCS = app/services/structured_comparison_service.py, RB = app/services/response_builder.py, SS = app/services/scoring_service.py, ES = app/services/extraction_service.py, KI = app/services/kb_ingest.py, SR = app/services/source_router.py, HR = app/api/home_routes.py, IR = the incident report, T1 = record/incident/T1_trace.md, G3 = record/s81/specs/S81_G3_UNIT_SPEC.md, PD2 = record/inc/PAGE_DESIGN_V2.md. Client paths are under SmartCompareApp/src/ (identical at a74caba7 and 6b909e0a = the live OTA f1e20c39; the store binary is 683f56c0).

The owner's ruling (N5 / N5b, 2026-11-11): "Show each found price with its bottle size and a per-ml line. When the two sizes differ, make no cheaper claim." The option "Compare per ml" was not chosen. Production has no AI text until the first Claude text role is live, so nothing in this unit's proof reads AI text (section 4).

## 0. What the unit does

Today, when the pair's two perfumes are found at different bottle sizes, the fairness rule replaces the off-size price with an empty pending price and throws the found listing away (`_mark_size_pending`, PS:2402-2417, which calls `make_pending_price`, PS:2005-2018). The phone then shows the `results.price.pending` line ("No confirmed price yet.") for a perfume a Bahrain store did list (T1:117 Layton 85.000 BHD alibaksh.com; T1:129 YSL Libre 39.000 BHD fragrancebh.com).

X1 keeps that pending price exactly as it is. Behind a new dark flag it carries the found listing in a NEW additive key, `price.offsize_listing` (amount in BHD, the listing's own bottle size, store, link, title, method, and a per-ml figure), and gives the partner's price its own bottle size and per-ml figure when the partner's own listing qualifies. It changes no score, no verdict, no savings figure and no winner, and nothing on the page says "cheaper". In the same unit it removes one dormant false line: with ENABLE_FIELD_STATUS_METADATA on, the OTA bundle would label a size-pended PRICE "Not listed by the stores we can read yet" (`results.honest.notListed`), which is false for a perfume a store listed.

The unit has two halves. THE UNIT TO BUILD NOW is the server half; the client half is a separate client unit.

| Half | What | Lands | When the phone sees it |
|---|---|---|---|
| INC-X1 server (X1-S), built now | the stash, the pop, the eligibility test, the projection, the D05 price entry, `winner_evidence`, the telemetry | main, dark behind its flag (the pop and the D05 price entry unflagged, section 1) | never by itself: neither live bundle reads the new key |
| INC-X1 client (X1-C), a separate client unit | a pure reader and the price-card lines `results.price.withSize`, `results.price.perMl`, `results.price.differentSizes` | main, only with the result-page update (the X4 price card), after the owner approves that design and reads every new Arabic string | only after the owner publishes that OTA and the phone takes it |

Which rulings bind which half: R-X1-1 to R-X1-16 bind X1-S; R-X1-17 to R-X1-21 bind X1-C; R-X1-7 (the wire contract) and R-X1-8 (no cheaper claim) bind both. Class (the orchestrator corrections, CLASS line): X1-S is a dark data-pipeline unit; X1-C is App-Review-visible and ships with the result-page OTA.

The key's name `offsize_listing` does not collide with the D20 provenance kind `'listed'` (`services/fieldStatusView.ts:21`, `:69`); a grep of app/ and SmartCompareApp/src at 6b909e0a finds no `offsize`, `size_fair`, `SIZE_FAIR` or `per_ml` token. No new name holds a gitleaks keyword (H7).

## 1. The flag ruling (binds X1-S)

| Item | Ruling |
|---|---|
| New flag | `ENABLE_SIZE_FAIR_OFFSIZE_LISTING`, default OFF, read per call with the house truthy reader (the pattern of `frag_reconcile_fix_enabled`, PS:4905-4923), never cached at import. Unused at 6b909e0a; no gitleaks keyword. |
| What it gates | the stash in `_mark_size_pending` (R-X1-1), the projection of `price.offsize_listing` and of the partner's `size_ml` / `per_ml` (R-X1-4, R-X1-6, R-X1-7), the `winner_evidence` correction (R-X1-9), `metadata.size_fair` and the `[SIZE_FAIR]` log line (R-X1-12). |
| Flag OFF | byte-identical to 6b909e0a: product dicts, every body key, the saved row, the SSE events, the verdict prompt and the logs. Pinned (P1). |
| Unflagged part 1 | the by-name pop of the stash key in RB on every call (R-X1-3): a no-op when the key is absent, as RB:2267 already does for `_shopping_listing_count`. It keeps a stash made under ON from shipping if the flag reads OFF later in the same request. |
| Unflagged part 2, classed as a production bug fix that ships unflagged (H1) | the D05 PRICE entry `other_size` for a size pend (R-X1-10, R-X1-11). It runs only when ENABLE_FIELD_STATUS_METADATA or ENABLE_KB_INGEST is ON (`_kb_ingest_tail` returns at once when both are OFF, SCS:3946-3951), and both are OFF on web (H2), so production stays byte-identical. Gating it on the X1 flag would let a D05 flip before an X1 flip print the false price line. The D05 SIZE entry and the KB gap rows are NOT changed, flag ON or OFF (R-X1-C3, R-X1-11). |
| Production today | byte-identical: the X1 flag is OFF and both D05 flags are OFF (H2). |
| Flip | the owner's, in one canary window, after the flip pause lifts (H2: all flips paused until the OpenAI credential works). The flip alone changes nothing on either phone bundle (section 4). |

## 2. Scope rulings

Each row: one sentence of rule, then its reason with the measured lines. The tag after the id says which half it binds.

### 2.1 Server: where the data is kept and where it is shown

| Id | Rule | Reason |
|---|---|---|
| R-X1-1 [S] | Flag ON, `_mark_size_pending` takes a keyword `target_ml` (the target-None call at PS:2353 passes None; PS:2392, PS:2395 and PS:2398 pass `target`) and, before it replaces each price, stores `{"price": <deep copy of the found price dict>, "target_ml": <float or None>}` on the PRODUCT dict under `_offsize_listing_src`, while the pending price it writes stays byte-identical to today (PS:2409-2417). | The found price is otherwise discarded (PS:2408-2413). A product-level `_` key is stripped from the verdict payload (ES:2522-2526) before `json.dumps` (ES:2647-2654), and the SSE events read named keys only (SCS:5379-5390, 5407-5435, 5442, 5478-5483, 5510-5516, 5633). |
| R-X1-2 [S] | Nothing else changes before the builder: the reconcile outcome, `compute_scores`, every SSE event, the prescoring guard and `generate_comparison` see exactly today's price dicts with the flag ON. | The verdict prompt bytes stay unchanged with the flag ON: `_verdict_safe_product` copies `price.size` into the prompt's pending dict (ES:2544-2547), so X1 never fills `price.size`. |
| R-X1-3 [S] | `build_comparison_response` pops `_offsize_listing_src` by name from every product dict on every call, flag ON or OFF, in a new step placed right after the price chokepoint's try/except ends (RB:1764-1765) and before the W4-7 confidence block (RB:1767); the flag-ON projection reads the popped value. | The legacy `products` alias ships the raw product dicts (RB:2259-2268). This one function builds the sync body (SCS:4783), the stream body (SCS:5676) and every partial body: `_build_partial_response` (SCS:3798, its builder call SCS:3880) is the only partial builder that carries products, and its callers are the sync timeout (SCS:4210), the stream tail deadline (SCS:5012) and the stream hard cap (SCS:5270); the two STREAM_TIMEOUT bodies carry no products (SCS:5029-5037, SCS:5293-5301). So one pop covers every path, including a sync partial built from `self._partial_product_data`, the same list the reconcile mutates (set at SCS:4551; reconcile calls SCS:4587 and SCS:5340). |
| R-X1-4 [S] | Flag ON, the step writes `price.offsize_listing` into the product's pending price dict only when the stash passes E1-E7 (2.2); the overview (RB:1951) and the legacy alias (RB:2263-2264) both carry it through `public_price_view`, which strips only top-level `guard_rejected` and `_` keys (PS:9371-9387). | Projecting after the verdict call keeps the prompt unchanged. Writing before RB:1951 lets one write reach both projections, the saved row and the D05 reader (which reads the same `product_data` list after the builder, SCS:4878-4881, SCS:5797-5800). `_build_scoring_v2` (RB:2079) and the factual verdict read only `price.amount` (SS:3171-3175, SS:3240-3248, RB:842-852, RB:873-880), so the new key moves no bar and no sentence. |
| R-X1-5 [S] | The step runs in its own try/except that logs one WARNING and leaves the body as today on any failure; the pop happens before anything that can raise. | The chokepoint's own rule: price handling must never crash the response (RB:1764-1765). |

### 2.2 Server: which listing may be shown (R-X1-C2 applied)

| Id | Rule | Reason |
|---|---|---|
| R-X1-6 [S] | Eligibility is decided by the listing's OWN properties, parked or not: the stash is eligible only when ALL of E1-E7 hold, and a parked price that passes all of them is eligible while one that fails any is not; otherwise no `offsize_listing` is written and the side shows exactly today's pending price. | R-X1-C2. A size printed beside a price must be the listing's own, on a Bahrain product page, at a real Bahrain shelf price. An identity marker on the parked dict would need an SCS edit (R-X1-15) and would refuse a genuine product-page price for no reason of its own. |

| # | Test (on the stashed found price) | Why, with the measured lines |
|---|---|---|
| E1 | `amount` is a finite number > 0 and `currency` is "BHD". | Only a Bahrain shelf price is shown as one. Currency alone is not enough: a Woo hit in a foreign currency is converted and stamped `currency: "BHD"` with `converted_usd` (woocommerce_service.py:251-276), so E2 is also needed. |
| E2 | A genuine Bahrain method on a non-global domain, never converted, never estimated: `estimated` is not True and `_is_genuine_bh_candidate(price)` is True (the method or `raw_data.source_method` is in `_GENUINE_BH_SOURCE_METHODS`, PS:17065; neither contains "converted" or "estimated"; the retailer is not a registry `global`-tier domain; PS:17090-17124). | It refuses every converted price, whoever wrote it. `registry_tier` does no blocking I/O (SR:764-794). If the tier lookup raises, the retailer counts as not global (PS:17122-17123), as for every genuine price today (SL9). |
| E3 | `url` is a non-empty string and `_is_listing_url(url)` is False (PS:8541-8551, which calls `is_non_pdp_listing_url`, SR:1227: a `/c/`, `/category/`, `/search`, `/catalogsearch`, `/collections/` or `/collection/` path, or a search query key, is a listing unless a PDP marker such as `/products/` is present, SR:1200-1225), applied ALWAYS, whether or not ENABLE_EXACT_PRICE_GATE is on. | `is_price_showable` refuses a listing url only under `exact_gate_enabled()` (PS:1951, PS:1964-1966), so E4 alone would let a parked genuine listing-url price through with that gate OFF (verifier V1). A missing url is refused here because the proof checks the store's host (S5). |
| E4 | `is_price_showable(full_name, <a COPY of the price>, category_used, enforce_correctness=True)` is True. | The same identity, sample, floor and PDP gate every shown price passes (RB:1739; ES:2538-2540). The predicate writes `title` and `guard_rejected` into its argument (PS:1917, 1920, 1953, 1965), so it runs on a copy. |
| E5 | The listing's OWN `title` (a string) holds exactly one distinct ml size under a strict parse: an integer 1..9999, then optional space or hyphen, then "ml" (case-insensitive, word end), NOT preceded by a digit, "." or ","; a second distinct ml value fails. The size is re-parsed from the title, never read from `price.size`, `raw_data.size`, a candidate's `size` field, the product name, specs or a default. | `_SIZE_ML_RE` (PS:4073) has no left boundary, so "7.5ml" reads as 5; the Serper candidate `size` is the lexicographic first of a string set (PS:10588-10589: "50ml / 100ml" gives "100ml"); `effective_pair_size_ml` falls back to the 100 ml default (PS:2048-2097). |
| E6 | `target_ml` is not None and the E5 size differs from it. | A title at the target means the pend came from another field (the name, PS:2021-2045); the target-None branch (PS:2348-2354) is the legacy non-fragrance comparison. |
| E7 | When the builder runs, the side's price is still the pending dict with `unavailable` True and `reason` "size_mismatch". | Only the incident class is in scope; any other pend keeps its own reason (RB:1711-1716). |

The four writers of the parked price at 6b909e0a (the miss path returns the parked dict, SCS:7039-7045), and what E1-E7 do with each; the spec proves each with a RED row (P6):

| Writer | What it parks | Outcome under E1-E7 |
|---|---|---|
| SCS:7814 (exact-gate terminal, SCS:7804-7814) | the best "converted" price (`converted_fallback`) | refused by E2 (reason `converted`). The incident's Armani case is this class: a converted 40 ml fallback, never shown. |
| SCS:8003 (Tier-1, SCS:7997-8003) | a `converted_usd` Tier-1 price | refused by E2 (`converted`) |
| SCS:8018 (Tier-1 listing-url park, gated by `_park_listing_url_tier1_enabled`, SCS:2848, test at SCS:7990-7996; branch SCS:8004-8018) | a GENUINE Tier-1 price whose url is a listing url | refused by E3 (`listing_url`), with ENABLE_EXACT_PRICE_GATE ON or OFF |
| SCS:8744 (`_maybe_park_supplement`, SCS:8737-8747; callers SCS:8773, 8806, 8859 page scrape, 9002) | any supplement-stage price that passes `is_price_showable(full_name, price_obj)` | eligible ONLY if it passes E1-E7 on its own properties (a genuine page-scrape price on a Bahrain product page with a one-size title is eligible, and that is ruled correct: it is a real listing) |

Inferred from the code, not measured on the data: the Layton and Libre titles carried at least one ml token other than 100 (both names carry no ml token, both pending dicts carry no `size` (T1:117, T1:129), the specs were `{}` (T1:123), and a Woo hit carries `title` but no `size` key (woocommerce_service.py:270-279), so the title is the only field left). Whether a title held TWO tokens (E5 refuses) stays UNVERIFIED until Q1.

### 2.3 The contract (binds both halves; R-X1-C1 applied)

| Id | Rule | Reason |
|---|---|---|
| R-X1-7 [S+C] | `price.offsize_listing` has exactly the keys in the table below; its `per_ml`, and `size_ml` plus `per_ml` on an on-basis PARTNER's price, appear together or not at all, and only when the partner's own listing also qualifies: either an on-basis partner whose own price passes E1-E5 with a single title size equal to `target_ml`, or a partner that itself carries an `offsize_listing`. | The owner's ruling asks for a per-ml line, and a per-ml figure is shown only between two genuine Bahrain listings that state exactly one ml size in their own titles; a partner size from the 100 ml default or a converted price is never used (PS:2087-2094; `reselect_to_target_size` admits converted candidates, PS:2179). |
| R-X1-8 [S+C] | With the flag ON, `price.amount` stays null, `unavailable` stays true, `reason` stays "size_mismatch", the existing optional `price.size` is never filled or changed by X1, product-level `best_price` and `retailer` stay null, and `overview.winner`, `scoring.*`, `scoring_v2.dimensions`, the factual verdict, the value badge, the confidence legs and Home / Profile savings are unchanged; the client never prints a comparison between the two prices. | The owner's ruling: when the two sizes differ, make no cheaper claim. A null amount keeps every consumer quiet with no client change: scoring (SS:1768-1778, SS:330-331), the factual price fact (RB:873-880), Home savings and the smart pick (HR:284-290, HR:571-574), and both bundles' `pricePending`, which hides the price and value bars and the price pill (`ResultsContent.tsx:212`; `:159 @683f56c0`). |
| R-X1-9 [S] | Flag ON, the builder drops the exact string "has a confirmed Bahrain price while the other relies on an indicative figure" from `scoring_v2.winner_evidence` (RB:1328-1331) when the runner-up's price is a size pend; `scoring_result` itself is not touched. | That sentence (SS:1006-1008) is false for a size pend; `winner_evidence` ships only through `scoring_v2` (RB:1346) and no bundle reads it, so this is a saved-row truth correction that moves no score or winner. |

| Key | Type | Present when | Meaning |
|---|---|---|---|
| `price.offsize_listing` | object | the side is a size pend and the stash passes E1-E7 | a real Bahrain listing found for a different bottle size than the pair's comparison size |
| `.amount` | number, 3 dp | always in the object | the listing's shelf price in BHD |
| `.currency` | "BHD" | always | |
| `.size_ml` | integer | always | the bottle size from the listing's own title (E5) |
| `.retailer` | string or null | always | the store, as on today's price dicts |
| `.url` | string | always | the product page (E3) |
| `.title` | string | always | the listing title (IR:100 asks for the title and size in the row) |
| `.source_method` | string | always | the genuine method (E2) |
| `.per_ml` | number, 4 dp | only under R-X1-7 | round(amount / size_ml, 4), BHD per ml |
| partner `price.size_ml` | integer | only under R-X1-7, on an on-basis partner | the partner's own title size |
| partner `price.per_ml` | number, 4 dp | only under R-X1-7, on an on-basis partner | round(partner amount / partner size_ml, 4) |

The object is a fresh dict of exactly these keys: no `_` key, no `_cached`, no `guard_rejected`, no `raw_data`, no `in_stock`. The wire carries a per-ML number (R-X1-C1), never a per-100-ml figure; the client formats it. Every new key is additive; no key either bundle reads is removed, renamed or retyped (record/s80/contract_freeze.json lists only price.amount, price.currency, price.source_method and price.unavailable under price). PD2 case D (both sides carry an `offsize_listing`) is covered: each side's object carries its own `per_ml` because the partner carries an `offsize_listing`.

### 2.4 Server: the dormant D05 line, the telemetry, the footprint (R-X1-C3 applied)

| Id | Rule | Reason |
|---|---|---|
| R-X1-10 [S] | In `_status_one` (KI:165-248), a price with `unavailable` True and `reason` "size_mismatch" gets the PRICE entry `{"state": "other_size", "source": <normalized host of offsize_listing.url, else null>, "reason": "size_mismatch", "as_of": null, "rung": null}` in place of `unknown / no_price` (KI:203-207); this amends the closed S81-17 D05 vocabulary (G3:283-291) by one state, and the amendment is this unit's ruling. | The OTA turns a price entry of state `unknown` on an `unavailable` price into "Not listed by the stores we can read yet" (`fieldStatusView.ts:52`, `:58`; `ResultsContent.tsx:367-374`; `en.json:705`), false when a store listed the perfume at another size; any other state gives kind `none`, which renders today's pending line (`fieldStatusView.ts:58`). The host as `source` keeps the vocabulary's own rule: no name, URL or free text (KI:253-257). |
| R-X1-11 [S] | The D05 SIZE entry (KI:209-217) and the `kb_gaps` rows stay exactly as at 6b909e0a with the X1 flag ON and OFF: the off-size listing's size is not the product's size and lives only inside `offsize_listing`; to keep the gap rows unchanged, `run_job` treats a price entry of state `other_size` exactly like `unknown` when it writes `kb_gaps` rows (KI:476-486; a gap row carries field and host hint, no reason). | R-X1-C3 (it removes the verifier's V2 contradiction): a size describes the product only from the typed name or a price accepted at the pair's basis (PD2 section 3, B2); a size pend is still a missing on-basis price, so the seeder's demand signal must not drop. `build_job` copies only `_PRICE_KEYS` (KI:264-267, KI:288), so the KB never ingests the off-size offer (SL7). |
| R-X1-12 [S] | Flag ON, the body gains `metadata.size_fair`: one entry per size-pended side, `{"product_index": 0 or 1, "outcome": "offsize_listing" or "pended", "reason": null or one closed code, "listing_cached": true, false or null, "per_ml": true or false}`, and the log gets one INFO line per size-pended side: `[SIZE_FAIR] product_index=<i> outcome=<outcome> reason=<code or none> listing_ml=<int or none> target_ml=<int or none> host=<host or none> cached=<true, false or none>`. | The proof needs a saved-row key and a log line that name the outcome (section 4). `listing_cached` comes from the stash's `_cached` (True on a price-cache hit, SCS:7105-7107; False on a fresh direct hit, SCS:7871): the pending dict drops `_cached`, and `metadata.cache_hit` is a response-level "any product" flag (RB:55, RB:71-77), so it cannot say it for a pended side. Closed reason codes: no_stash, no_target, not_bhd, not_genuine, converted, global_tier, estimated, no_url, listing_url, not_showable, no_title, no_title_size, multi_size_title, size_equals_target, not_size_pend, error. The line carries no product name, no query text and no URL path (the U8d practice, as SCS:5282-5285 does for a query). |
| R-X1-13 [S] | The PIN rows of 3.2 are part of the unit's RED. | H1 and H6: flag-OFF identity and the unchanged verdict prompt are proven by a test, never asserted. |
| R-X1-14 [S] | The server footprint is PS (the flag reader, the stash, a pure eligibility helper and the strict title parser), RB (the pop, the projection, `winner_evidence`, `metadata.size_fair`, the log line) and KI (R-X1-10, R-X1-11); no edit to ES, SCS, SS, HR, SR or the URL path. | H1: keep off the LLMUnavailableError log statements S81-04c edited (now merged at 6b909e0a) in ES, image_routes.py and url_extraction_service.py; SCS needs no edit because the builder is shared by every path (R-X1-3) and E3 reads the listing-url test through PS (PS:8541). |
| R-X1-15 [S] | The non-fragrance `unit_mismatch` path (`_mark_unit_pending`, PS:3164-3180) and the URL compare path (url_extraction_service.py, which never calls the reconcile or `make_pending_price`) are untouched. | Out of the incident class; ENABLE_FRAGRANCE_ONLY_GATE is OFF, so other categories still flow and must stay byte-identical. |
| R-X1-16 [S] | The partial bodies change only by the pop: the partial builder never calls the reconcile (its only callers are SCS:4587 and SCS:5340), and the stream partials build from `self._partial_product_data or self._early_specs_buffer_list()` (SCS:3821), while `_partial_product_data` is initialised at SCS:3382, reset at SCS:4363 and SCS:5065 and set only at SCS:4551 (sync), so a stream partial can carry two sticker prices at different sizes, as today. | Pre-existing; widening X1 into the timeout paths is a separate unit. A partial body carries `metadata.partial: true` (SCS:3909) and is never proof (S1). |

### 2.5 Client half (X1-C, a separate client unit that ships with the result-page update)

| Id | Rule | Reason |
|---|---|---|
| R-X1-17 [C] | X1-C adds a pure reader `services/sizeFairView.ts` that returns a view only when `price.unavailable === true`, `price.reason === 'size_mismatch'` and `price.offsize_listing` has a finite `amount` > 0, `currency` "BHD" and an integer `size_ml` in 1..9999; anything else returns null and the card renders exactly as today. | The client must not trust a malformed body; a null view is today's rendering, so old rows in History and Share (no new key) render unchanged. Neither bundle reads `price.reason` or `price.size` today. |
| R-X1-18 [C] | In the hero price slot (`ResultsContent.tsx:367-386`), a non-null view takes precedence over `prov.kind === 'unknown'` and renders: the amount and the LISTING's size through `results.price.withSize`; the caption `results.price.differentSizes`; and, only when `offsize_listing.per_ml` is present, `results.price.perMl`. An on-basis partner adds `results.price.withSize` and `results.price.perMl` only when its `price.size_ml` and `price.per_ml` are present. | The owner's ruling (each found price with its bottle size and a per-ml line, no cheaper claim); one vocabulary with PD2 (table 6a, case B and D of section 3). `pricePending` (`:212`) stays true, so the price and value bars and the price pill stay hidden. |
| R-X1-19 [C] | Every number in the new lines (the amount, the ml size, the per-ml figure) goes through the app digit policy (`utils/formatNumber.ts`, price formatter `:96`; `applyDigitSystem`, imported as `fieldStatusView.ts:6` does); the per-ml figure is formatted from the wire's `per_ml`, never recomputed from a per-100-ml number. | One digit system on the card; R-X1-C1. |
| R-X1-20 [C] | `types/types.ts` `ProductPrice` (`:60-73`, today without `size` or `reason`) gains the optional `size?`, `reason?`, `size_ml?`, `per_ml?` and `offsize_listing?` fields; tests live under `__tests__/inc_x1/`. | Typed reads, no `any`. |
| R-X1-21 [C] | X1-C is built as part of the X4 price card (IR:103; PD2 section 3), uses only the keys `results.price.withSize`, `results.price.perMl` and `results.price.differentSizes` (PD2 table 6a; the draft keys `results.price.offsize.*` are withdrawn), merges to main only after the owner approves that design and reads every new Arabic string, and ships in the first OTA after that approval; it is not in Friday's SECOND OTA unless the owner rules it in. | One price-card design and one Arabic read for X1 and X4 (R-X1-C1). The feedback card (unit CL3) is another session's section and is not touched; an OTA from a main that carries CL3 needs ENABLE_FEEDBACK_V2 ON first (IR:103). |

The English lines (PD2 6a): `results.price.withSize` = "{{price}} - {{size}} ml" (the " - " stands for the app's middle dot in this ASCII file), `results.price.perMl` = "{{price}} per ml", `results.price.differentSizes` = "Different bottle sizes, so we do not compare the prices." The Arabic drafts live in PD2 table 6a and are the owner's native read. None contains a word the copy rule forbids (`services/sourceMethod.ts:13-15`; `src/i18n/.copy-policy.json`).

## 3. Questions the spec answers by measurement

### 3.1 Open measurements (the spec states each answer with file:line before RED)

| # | Question | How to measure |
|---|---|---|
| Q1 | Do the Layton and Libre listing titles carry exactly one ml token (E5), and which size? | One replay comparison's price-candidate log lines (IR:175), or a fixture captured from the adapters' saved responses. If a title holds two tokens or none, E5 refuses and the phone proof for that pair cannot pass (section 4 says so). |
| Q2 | Does any reader outside app/ (scripts/, the eval runner, the admin pages) count `field_status` states, so the new `other_size` price state changes a metric? | `git grep -n field_status 6b909e0a -- ':!app'`. Inside app/ the readers are KI and compare_runs.py:297-305 (stores the list as is); inside the client, `fieldStatusView.ts:37-38`, `:52` and `ResultsAccordion.tsx:147` test only `state === 'unknown'`. |
| Q3 | Which existing tests pin `_mark_size_pending`'s signature, the D05 vocabulary (S81-11, S81-17; G3:351 pins "the 2.2 vocabulary only"), the `kb_gaps` rule or the `winner_evidence` list? | git grep of tests/ and the client `__tests__/` at 6b909e0a; each pin that moves needs a ruling in the spec, never a weakening. |
| Q4 | Does any reader between the reconcile and the builder iterate a product dict's keys, so an extra `_` key changes its output? | Read `compute_scores`, `apply_value_badges`, `compute_confidence`, `validate_verdict`, `verdict_comparison_quality` and `_display_product_names` (their calls at SCS:4604-4757). |
| Q5 | Does a Woo variable product's title carry the bottle size, or only its variation? | Read woocommerce_service.py around the title build (the candidate at :270-279) and one saved adapter response; a title without the size gives reason `no_title_size` (SL3). |
| Q6 | For each writer of the parked price (SCS:7814, 8003, 8018, 8744 and the four callers of 8744 at SCS:8773, 8806, 8859, 9002), which `source_method`, url shape and title the parked dict carries, so each RED row in P6 uses a realistic dict. | Read each writer and the adapter that feeds it at 6b909e0a; state per writer which of E1-E7 refuses it, or that it is eligible. |

### 3.2 PIN rows (all in RED; each that asserts new behaviour must fail on the base sha)

| Pin | Asserts |
|---|---|
| P1 | Flag OFF: the sync and stream bodies for the C1, C2 and C3 fixtures are byte-identical to 6b909e0a, and no product dict ever carries `_offsize_listing_src`. |
| P2 | Flag ON vs OFF on the C1 and C2 fixtures: the user message handed to the verdict LLM by `generate_comparison` is byte-identical (captured through the existing LLM stub; no network). |
| P3 | Flag ON vs OFF: `scoring.*`, `overview.winner`, `scoring_v2.dimensions`, `scoring_v2.factual_verdict`, every `value_badge`, `overview.confidence` and every SSE payload before `complete` are identical. |
| P4 | Flag ON: no body (sync, stream, sync partial after the reconcile, stream tail-deadline partial, stream hard-cap partial) carries `_offsize_listing_src` at any depth. |
| P5 | Flag ON, C1 fixture (Layton title with one 125 ml token at 85.000; Aventus title with one "100ml" at 133.460): `products[1].price` = today's pending dict + `offsize_listing` with its eight keys and `per_ml` 0.68; `products[0].price.size_ml` 100 and `per_ml` 1.3346; the overview and the legacy alias carry equal objects; `metadata.size_fair` has one entry, outcome `offsize_listing`. |
| P6 | Flag ON, each of E1-E7 failing alone (a converted_usd price, a global-tier retailer, estimated, no url, a `/collections/` url, a non-showable title, no title, an Arabic-only title, "7.5ml", "50ml / 100ml", a title at 100 ml, a non-size pend): no `offsize_listing`, the matching closed reason code, the side exactly as today. Plus one row per parked-price writer: SCS:7814 and SCS:8003 dicts refused (`converted`; the Armani converted 40 ml fallback among them); the SCS:8018 genuine listing-url dict refused (`listing_url`) with ENABLE_EXACT_PRICE_GATE ON and again OFF; an SCS:8744 genuine page-scrape dict on a Bahrain product page with a one-size title ELIGIBLE. |
| P7 | Flag ON, partner title without an ml token, with two tokens, converted, or on a listing url: `offsize_listing` present WITHOUT `per_ml`, and no `size_ml` / `per_ml` on the partner. Both sides off-size and eligible (PD2 case D): each object carries its own `per_ml`. |
| P8 | D05 flags ON, X1 flag OFF and ON: a size pend's PRICE entry is `other_size`, never `unknown`; its SIZE entry equals 6b909e0a's for the same input; the `kb_gaps` rows equal 6b909e0a's. A non-size pend keeps `unknown / no_price`. |
| P9 | Flag ON: `winner_evidence` loses only the price-provenance string, and only when the runner-up is a size pend. |
| P10 | The `[SIZE_FAIR]` line carries no product name, no query text and no URL path; every reason code it prints is in the closed list. |
| P11 (X1-C, its own RED) | The reader returns null for every malformed body; a body with no new key renders exactly as today; the new branch wins over `prov.kind === 'unknown'`; every number passes the digit policy; `pricePending` stays true; the lines use only the three PD2 keys; no rendered string contains "cheaper", "less" or a percent. |

DEFERRED TO RED (nothing was run this round): `python <SP>/harness/pyt.py --bound 900 --tag inc-x1-red --log <notes>/inc-x1-red.log --cwd C:/Users/SynAckITPC/Documents/AI/sc-inc-x1 -- tests/test_inc_x1_size_fair.py -q`. For the client unit, after the H5 jest probe: `npx jest __tests__/inc_x1 --runInBand` in its worktree's SmartCompareApp/. The file names are proposals.

## 4. PROOF ON THE PHONE

This restates IR:100 for the ruled design. Under it `price.amount` stays null by construction, so the record's backing "products[1].price.amount not null" can never pass, and the record's rule (c) (IR:162: no `size_mismatch` marker in the log) can never pass either, because the reason stays `size_mismatch`. Both are replaced below. A green suite is not proof (H6 (d)).

No AI text is needed. Production has no AI text until the first Claude text role is live, so every check below reads deterministic output only: the price card lines, the saved row's price, metadata and `scoring_v2.winner_evidence` keys, and the deploy log. No check reads `winner_reason`, verdict prose, review summaries or pros and cons; a page with the AI write-up missing is a valid page for this proof.

When it CAN pass: only after ALL of: X1-S merged and deployed; the flip pause lifted (H2, after the OpenAI credential works); the owner flipped `ENABLE_SIZE_FAIR_OFFSIZE_LISTING` on web in its own window; X1-C merged with the result-page update and published in an OTA the owner approved; the phone took that OTA (close and reopen the app twice, as N3). Before that OTA the phone shows today's `results.price.pending` line for Layton with the flag ON or OFF, on both bundles, so a screenshot taken before the OTA proves nothing and must not be offered. The app shows no OTA update id, so the bundle is identified by the new line itself: only X1-C can draw a size beside a pending price.

The pairs (Arabic UI, the golden set IR:140-145), repeated as typed before:
- pair 1 Creed Aventus EDP vs Parfums de Marly Layton EDP (Layton is the off-size side; target);
- pair 2 Lancome La Vie Est Belle EDP vs YSL Libre EDP (Libre; target);
- pair 3 Armani Acqua di Gio Profumo vs Versace Eros EDP (NEGATIVE control);
- at least one of pair 4 Dior Sauvage EDP vs Chanel Bleu de Chanel EDP and pair 5 Maison Francis Kurkdjian Baccarat Rouge 540 EDP vs Lattafa Khamrah EDP, the first time the proof runs (R-X1-C4; IR:162: pairs 1-3 were used by the W4 canary).
The free tier allows 3 comparisons a day and 10 a month (IR:83). The first run is therefore two days unless the owner's N6 choice (IR:94) says otherwise: day one pair 1, pair 3 and pair 4 (or 5); day two pair 2.

What must be visible (pair 1; pair 2 the same for Libre):

| On the Layton card | Must show | Must NOT show |
|---|---|---|
| price line | the amount and the listing's size through `results.price.withSize` (for example 85.000 BHD and 125 ml), digits in the app's digit system | the `results.price.pending` line or the `results.honest.notListed` line |
| caption | `results.price.differentSizes` | any "cheaper", "less" or "better value" text |
| per-ml line | `results.price.perMl` only if the saved row carries `per_ml` (S8) | a per-ml figure when the row has none |
| the page | no price bar, no value bar, no price pill (as today) | a price or value bar, a percent difference |

The backing in the saved row (`comparisons.full_response`, written by database_service.py:471-486; open the row by its id and record the id and its UTC `created_at`):

| # | Key | Must hold |
|---|---|---|
| S1 | `metadata.partial` | absent or false (a partial body is never evidence, R-X1-16) |
| S2 | `overview.products[1].price` | `amount` null, `unavailable` true, `reason` "size_mismatch" |
| S3 | `overview.products[1].price.offsize_listing` | present; `amount` equals the number on the screenshot; `currency` "BHD"; `size_ml` equals the size on the screenshot and is not 100 |
| S4 | `offsize_listing.title` | contains exactly one ml token under E5's strict parse, and it equals `size_ml` |
| S5 | `offsize_listing.url` and `.source_method` | the host is a Bahrain store (pair 1 expected alibaksh.com, T1:32), the url is not a listing or collection address (E3), and the method is in the genuine set (expected woo_store_api) |
| S6 | `products[1].price.offsize_listing` (the legacy alias) | equal to S3's object; `products[1]` has no `_offsize_listing_src` key |
| S7 | `metadata.size_fair` | exactly one entry: `product_index` 1, `outcome` "offsize_listing", `reason` null |
| S8 | `per_ml` | present on Layton's object only if `overview.products[0].price.title` holds exactly one ml token; if present it equals round(amount / size_ml, 4), and `overview.products[0].price.size_ml` and `per_ml` are present and equal the partner's title size and its arithmetic |
| S9 | `scoring_v2.winner_evidence` | does not contain "has a confirmed Bahrain price while the other relies on an indicative figure" when Layton is the runner-up |

The backing in the deploy log for that request's minutes (read-only, the relay's usual log read):

| # | Line | Must hold |
|---|---|---|
| L1 | `[SIZE_FAIR] product_index=1 outcome=offsize_listing ...` (R-X1-12) | present once; its `host` equals S5's host; its `listing_ml` equals S3's `size_ml` |
| L2 | `[PRICE] BH adapter direct hit for ... via <host> (<method>, ...)` (SCS:7872-7877) | present for Layton with the same host when `metadata.size_fair[0].listing_cached` is false; when it is true the price came from the price cache (7 days by default, PS:157) and the line is legitimately absent, so S4 and S5 carry the identity check alone |
| L3 | `fairness reconciliation skipped` (SCS:4592 sync, SCS:5345 stream) and `[SIZE_FAIR] ... outcome=error` | absent (these replace the record's `size_mismatch` marker for X1) |

Negative control (pair 3): the Armani card still shows the `results.price.pending` line; the row has no `offsize_listing` for Armani; if the parked converted 40 ml price was pended again, `metadata.size_fair` for Armani says `outcome` "pended" with `reason` "converted". Anything else fails the proof.

Pair 4 or 5 (never compared before): whatever the stores return, the card and the row agree. If `metadata.size_fair` is absent, both cards render as on today's bundle apart from the result-page update, and no `offsize_listing` is in the row. If it is present, every side with outcome "offsize_listing" meets S2-S8 and L1, and every side with outcome "pended" shows the `results.price.pending` line with a closed reason code. No card shows a cheaper or percent claim between two different sizes. A pair 4 or 5 run with no size pend is reported as "control, no size pend", not as a pass of the X1 behaviour.

Why it cannot pass falsely: the screenshot numbers must equal S3 exactly; the size must come from the listing's own title with one token (S4), so a default, a name-derived size, "7.5ml" or a gift-set title cannot reach the screen; the store must be a genuine Bahrain product page (S5), so a converted price or a listing-url price, parked or not, cannot; a partial body is refused (S1); the per-ml line must be backed by the partner's own title (S8); the old bundles cannot draw the new line, so a pre-OTA screenshot looks like today. A wrong product whose title passes the shipped identity gate (the Versace "for Women" class, T1:59) is NOT caught by X1: that is X10's job (IR:109) and SL6.

Reporting: each claim records the row id, the UTC time and the OTA it ran on; a pair that cannot pass because its title holds two tokens or none (Q1) is reported as "not provable on this pair", never as a pass; the result is "proven on pairs X, Y", never "fixed". The completeness score (IR:147) does not move under X1 unless O3 rules otherwise.

## 5. Owner steps

| # | Step | Blocks |
|---|---|---|
| O1 | N5 / N5b: RULED 2026-11-11 ("Show each found price with its bottle size and a per-ml line. When the two sizes differ, make no cheaper claim."); the unit of the line is per ml (R-X1-C1). No owner action; the relay records the ruling in the ledger, since IR:93 still lists N5 open. | nothing |
| O2 | Hear this fact, which the ruling keeps: the winner stays as today, and today's C1 winner came partly from Layton's blanked price (wear_value 75 vs a 50 default, margin 1.4, T1:176). Optional (a2): when one side is a size pend, treat the price signal as missing for BOTH sides in scoring, so a blank cannot win; it changes scores and possibly winners on both live bundles and needs its own flag and ruling. X1 does not build it. | nothing in X1 |
| O3 | Confirm the comparison basis stays the 100 ml flagship default (PS:1439) for every house, including one whose flagship is another size (Layton, LIKELY 125 ml, IR:175); changing it is a separate unit. Also rule whether the completeness score (IR:147) gives a point for an `offsize_listing`; default no (a price on another size is not a comparable price). | the score only |
| O4 | Approve the class of the unflagged D05 price entry (section 1): it is dormant today and ships without its own flag. | the X1-S RED |
| O5 | Approve the price-card design (one design with X4) and read every new Arabic string (PD2 table 6a). | the X1-C merge |
| O6 | Flip `ENABLE_SIZE_FAIR_OFFSIZE_LISTING` on web in one canary window after the pause lifts; the relay sets it on your yes. Rollback is unsetting it: there is no whole-response cache on the compare path (`get_comparison_cache` / `set_comparison_cache`, cache_service.py:777 / :783, have no caller in app/), so the next comparison is built without the key; rows saved while it was ON keep the key, and the new client reads it. | the proof |
| O7 | Approve and publish the OTA carrying X1-C with the result-page update; take it on the phone (close and reopen twice). | the proof |
| O8 | Run section 4 (two days, or the N6 choice, IR:94) and send the screenshots with the row ids. | the claim "proven on pairs X, Y" |

## 6. Stated limits

| # | Limit | Where |
|---|---|---|
| SL1 | The server half changes NOTHING on either phone; the store binary and the OTA bundle ignore the new key until X1-C ships. | R-X1-8; section 4 |
| SL2 | The winner, scores and Home savings stay exactly as today, including a winner that comes from the blanked price (C1). | R-X1-8; T1:176; O2 |
| SL3 | A listing whose title states its size in oz only, in Arabic only, with two ml sizes, or not at all (a Woo variation, Q5) stays pended as today (E5); an oz-to-ml converter exists (PS:4099-4101) but is not used. | E5 |
| SL4 | A price served from the L2 database cache as a title-less legacy row stays pended as today (reason `no_title`). | SCS:7109-7128; E5 |
| SL5 | Partial (timeout) bodies are unchanged beyond the pop and can still show two sticker prices at different sizes. | R-X1-16 |
| SL6 | A wrong product whose title passes the shipped identity gate is shown with its size; the identity guard is X10's (IR:109). | E4 |
| SL7 | The KB does not ingest the off-size offer (`_PRICE_KEYS`, KI:264-267). | R-X1-11 |
| SL8 | The completeness score does not count an off-size listing unless O3 rules otherwise. | IR:147 |
| SL9 | If the tier lookup raises, the retailer is treated as not global (PS:17122-17123), as for every genuine price today. | E2 |
| SL10 | A hermetic test is not the production proof; the claim waits for section 4. | H6 |
| SL11 | The converted-price label printed twice on the card (`ResultsContent.tsx:204` and `:392-400`) is a separate cosmetic defect, not X1's. | X1_MEASURE 3.2 |
| SL12 | Only a size-pended pair gains sizes and per-ml figures; a pair with two basis prices still shows no bottle size or per-ml line (PD2 case A, item E-X1-a) until a later ruling widens the contract. | R-X1-7 |
| SL13 | The D05 SIZE entry is left exactly as at base (R-X1-C3): for a size pend whose found price had a `size` field, `_mark_size_pending` keeps it on the pending dict (PS:2412) and KI reads it as `known / listing` (KI:210-211), and with no size the Specs body can print "Size: Not listed by the stores we can read yet" (`ResultsAccordion.tsx:135-153`) once a D05 flag is ON. Both are pre-existing and dormant (D05 flags OFF); the product's size line belongs to the result page (PD2 section 3, B2). | R-X1-11 |
| SL14 | A genuine page-scrape price parked by the supplement stage (SCS:8744) is shown when it passes E1-E7: eligibility is by the listing's own properties, not by how it reached the product. | R-X1-6 |

## 7. Out of scope

Per-ml comparison (closed, appendix A) and (a2); changing the 100 ml basis; oz parsing; reconciling the partial paths; the X4 page as a whole (only its price card's three lines are X1-C), the X6 price bar states and the X7 key-differences rows (they read X1's keys; PD2 sections 3 and 5.1); per-ml on basis prices (E-X1-a); the D05 size entry; the X10 identity guard; the non-fragrance `unit_mismatch` path; the URL compare path; Home and Profile savings; the CL3 feedback card (another session's unit); any edit to the LLMUnavailableError log statements (S81-04c); any flag flip, variable or production read by a build agent.

## Appendix A. Design (b): CLOSED

1. Closed: the owner did not choose "Compare per ml" on 2026-11-11, so nothing of design (b) is specced or built; reopening it needs a new ruling and a new brief (this unit's keys would stay valid under it).
2. It would have fed each side's per-ml figure into the price signal in place of `price.amount` (SS:1768-1778), so the off-size side would get a price score where today it has none (`MISSING_SCORE`, SS:2457-2459) and the lone priced side no longer takes the 75 a single price gets (SS:2465-2467).
3. Today's C1 winner, Aventus, won by margin 1.4 only because Aventus alone had a price (T1:176); with Layton at 0.680 and Aventus at 1.3346 BHD per ml (lower is better, SS:2469-2470) that edge would vanish and the winner would likely have moved (not computed; the value signal stays missing while specs are empty, SS:330-331, T1:172).
4. Both live bundles would have crowned that new winner the moment the flag flipped, while still showing the pending line for it with no visible reason, because the compare request carries no bundle or version signal.
5. That silent winner change on both live apps is why the ruled design keeps every score and winner as today (R-X1-8).

## Appendix B. How the verifier's points and the corrections were applied

| Item | Applied as | Where |
|---|---|---|
| V1 (four writers of the parked price; "parked never eligible" was false) and R-X1-C2 | eligibility by the listing's own properties; new E3 (product page, always, gate or not); the four writers measured at 6b909e0a and pinned | R-X1-6, E1-E7, writers table, P6, SL14 |
| V2 (size entry vs gap rows) and R-X1-C3 | the D05 size entry and the gap rows unchanged ON and OFF; only the price entry changes | R-X1-10, R-X1-11, P8, SL13 |
| Conflicts C1 / C2 and R-X1-C1 | the wire carries `per_ml`; the client keys are PD2's three | 2.3, R-X1-18 to R-X1-21 |
| Section 4 gap and R-X1-C4 | pair 4 or 5 added the first time, with the negative control | section 4 |
| R-X1-C5 (minor citations) | `_partial_product_data` init SCS:3382 and resets SCS:4363, SCS:5065; `cache_hit` is a response-level flag (RB:55, RB:71-77) | R-X1-16, R-X1-12 |
| Conflict C3 (sizes on every price) | NOT settled by a correction; kept to size-pended pairs | SL12; open point |
| Conflict C4 (cite `cache_hit: false`) | the brief keeps `listing_cached` and L2; PD2 to align | open point |

## UNVERIFIED in this round

The titles' ml tokens (Q1); readers of `field_status` outside app/ (Q2); the test pins that move (Q3); key iteration in the scoring and verdict readers (Q4); Woo variation titles (Q5); the realistic parked dicts per writer (Q6); the Arabic wording; the production values of ENABLE_EXACT_PRICE_GATE, the listing-url park flag, `GENUINE_PRICE_CACHE_TTL_SECONDS` and ENABLE_FRAGRANCE_SIZE_RECONCILE_FIX (never probed, H2; E3 makes X1 independent of the first two); the ledger line recording the N5 / N5b ruling.

## This round

This finalize round, and the spec and review round that follows it, are READ-ONLY: no pytest, no jest, no tsc, no eslint, no network, no git write, no package manager, no production probe and no .env read; measurement is by git show, git grep and file reads at 6b909e0a only. The base pass state (the suite results at 6b909e0a for the comm set this unit touches) is NOT measured here and is DEFERRED TO RED, with the commands in 3.2.
