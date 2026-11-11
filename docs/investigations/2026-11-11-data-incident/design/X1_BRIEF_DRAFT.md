# INC-X1 SIZE-FAIRNESS - BRIEF DRAFT v2 (2026-11-11)

Unit: INC-X1 (incident report item 4, fix row X1, record/incident/INCIDENT_AND_DATA_PLAN_2026-11-11.md:100). Role: the finalizer. Round class: READ-ONLY. Nothing was run: no pytest, jest, tsc, eslint, network, package manager, git write, production probe or .env read. Inputs: X1_MEASURE.md (v1), X1_SKEPTIC.md (its review), the orchestrator's four binding decisions for v2, the owner's N5 / N5b ruling of 2026-11-11 as the orchestrator relayed it, and a re-measurement in this run of the plain exports (backend and OTA client at main a74caba7 = live OTA f1e20c39; store binary client 683f56c0). Every file:line below was re-read in this run. Nothing here says a production problem is fixed: X1 is not built, and once merged it is "merged, NOT yet proven" until the owner's phone shows it (H6).

Short names: PS = app/services/price_service.py, SCS = app/services/structured_comparison_service.py, RB = app/services/response_builder.py, SS = app/services/scoring_service.py, ES = app/services/extraction_service.py, KI = app/services/kb_ingest.py, RG = app/services/result_gate.py, HR = app/api/home_routes.py, SR = app/services/source_router.py, IR = the incident report, T1 = record/incident/T1_trace.md, G3 = record/s81/specs/S81_G3_UNIT_SPEC.md. Client paths are under SmartCompareApp/src/ and carry `@a74caba7` (OTA) or `@683f56c0` (store binary).

The owner's ruling (N5 / N5b, 2026-11-11, relayed by the orchestrator): the chosen option reads "Show each found price with its bottle size and a per-ml line. When the two sizes differ, make no cheaper claim." The option "Compare per ml" was not chosen. This brief builds that ruling, which is design (a) of X1_MEASURE.md section 5.1 as corrected by X1_SKEPTIC.md. The record copy still lists N5 as open (IR:93); the ledger line that records the ruling is not in the record copy (UNVERIFIED there; the relay records it).

## 0. What the unit does

Today, when the pair's two perfumes are found at different bottle sizes, the fairness rule replaces the off-size price with an empty "pending" price and throws the found listing away (`_mark_size_pending`, PS:2402-2417; `make_pending_price`, PS:2005-2018). The phone then shows "No confirmed price yet." for a perfume a Bahrain store did list (T1:117 Layton 85.000 BHD alibaksh.com; T1:129 YSL Libre 39.000 BHD fragrancebh.com).

X1 keeps that pending price exactly as it is. Behind a new dark flag it carries the found listing in a NEW additive key, `price.offsize_listing` (amount in BHD, its own bottle size, store, link, title, method), and gives the partner's price its own bottle size. It adds a per-100-ml figure on both sides only when BOTH listings are genuine Bahrain listings whose own titles state exactly one ml size. It changes no score, no verdict, no savings figure and no winner, and nothing on the page says "cheaper". In the same unit it closes a dormant defect: with ENABLE_FIELD_STATUS_METADATA on, the OTA bundle would label a size-pended price, and its size, "Not listed by the stores we can read yet", which is false for a perfume a store listed.

| Half | What | Where it lands | When the phone sees it |
|---|---|---|---|
| X1-S (server) | the stash, the pop, the projection, the eligibility test, the D05 entry, the telemetry | main, dark behind the flag (the D05 part unflagged, section 1) | never by itself: neither live bundle reads the new key |
| X1-C (client) | a pure reader and a price-card branch: "85.000 BHD . 125 ml", a different-size caption, a per-100-ml caption when the row carries one | main, only after the owner approves the price-card design (shared with X4) and reads every new Arabic string | only after the owner publishes that OTA and the phone takes it; the store binary also takes runtime 1.0.0 OTAs |

The new key's name is `offsize_listing`. It does not collide with the D20 provenance kind `'listed'` (`services/fieldStatusView.ts:21`, `:69 @a74caba7`, rendered at `components/results/ResultsContent.tsx:168-174 @a74caba7`). A grep of both export trees in this run finds no `offsize`, `size_fair`, `SIZE_FAIR` or `ENABLE_SIZE_FAIR` token. The name holds no gitleaks keyword (H7).

## 1. The flag ruling

| Item | Ruling |
|---|---|
| New flag | `ENABLE_SIZE_FAIR_OFFSIZE_LISTING`, default OFF, read per call with the house truthy reader (the pattern of `frag_reconcile_fix_enabled`, PS:4905-4923), never cached at import. Unused in both exports (grep this run); no gitleaks keyword. |
| What it gates | the stash in `_mark_size_pending` (R-X1-1), the projection of `price.offsize_listing` and the partner's `size_ml` / `per_100ml` (R-X1-4 to R-X1-7), the `winner_evidence` correction (R-X1-9), `metadata.size_fair` and the `[SIZE_FAIR]` log line (R-X1-13). |
| Flag OFF | byte-identical to a74caba7: product dicts, every body key, the saved row, the SSE events, the verdict prompt and the logs. Pinned (P1). |
| Unflagged part 1 | the by-name pop of the stash key in RB on every call (R-X1-3): a no-op when the key is absent, as RB:2267 already does for `_shopping_listing_count`. It keeps a stash made under ON from shipping if the flag reads OFF later in the same request. |
| Unflagged part 2, classed as a production bug fix that ships unflagged (H1) | the D05 `other_size` entry for a size pend (R-X1-10 to R-X1-12). It runs only when ENABLE_FIELD_STATUS_METADATA or ENABLE_KB_INGEST is ON (`_kb_ingest_tail` returns at once when both are OFF, SCS:3948-3951), and both are OFF on web (H2), so production stays byte-identical. Gating it on the X1 flag instead would let a D05 flip before an X1 flip print the false line (orchestrator binding 3). |
| Production today | byte-identical: the X1 flag is OFF and both D05 flags are OFF (H2). |
| Flip | the owner's, in one canary window, after the flip pause lifts (H2: all flips paused until the OpenAI credential works). The flip alone changes nothing on either phone bundle (section 4). |

## 2. Scope rulings

Each row: one sentence of rule, then its reason with the measured lines.

### 2.1 Server: where the data is kept and where it is shown

| Id | Rule | Reason |
|---|---|---|
| R-X1-1 | Flag ON, `_mark_size_pending` takes a keyword `target_ml` (the target-None call at PS:2353 passes None; PS:2392, PS:2395 and PS:2398 pass `target`) and, before it replaces each price, stores `{"price": <deep copy of the found price dict>, "target_ml": <float or None>}` on the PRODUCT dict under `_offsize_listing_src`, while the pending price it writes stays byte-identical to today (PS:2409-2417). | The found price is otherwise discarded (PS:2408-2413). A product-level `_` key is stripped from the verdict payload (ES:2506-2510) before `json.dumps` (ES:2631-2635), and the SSE events read named keys only (SCS:5379-5390 specs, SCS:5407-5435 prices, SCS:5442 reviews, SCS:5478-5483 first_paint, SCS:5510-5516 scores, SCS:5633 verdict). |
| R-X1-2 | Nothing else changes before the builder: the reconcile outcome, `compute_scores`, every SSE event, the prescoring guard and `generate_comparison` see exactly today's price dicts with the flag ON. | Orchestrator binding (2): the verdict prompt bytes are unchanged with the flag ON. v1 broke this by filling `price.size` inside `_mark_size_pending` (X1_SKEPTIC 2.1), because ES:2528-2532 copies `price.size` into the prompt's pending dict; v2 never fills `price.size`. |
| R-X1-3 | `build_comparison_response` pops `_offsize_listing_src` by name from every product dict on every call, flag ON or OFF, in a new step placed right after the price chokepoint's try/except ends (RB:1764-1765) and before the W4-7 confidence block (RB:1767); the flag-ON projection (R-X1-4) reads the popped value. | The legacy `products` alias ships the raw product dicts (RB:2259-2268). This one function builds the sync body (SCS:4783), the stream body (SCS:5676) and every partial body: `_build_partial_response` (SCS:3798, its builder call SCS:3880) is the only partial builder that carries products, and its three callers are the sync timeout (SCS:4210), the stream tail deadline (SCS:5012) and the stream hard cap (SCS:5270). The two STREAM_TIMEOUT bodies carry no products (SCS:5029-5037, SCS:5293-5301). So one pop covers every path, including a sync partial built from `self._partial_product_data`, the same list the reconcile mutates (SCS:4551, SCS:4586-4590). |
| R-X1-4 | Flag ON, the step writes `price.offsize_listing` into the product's pending price dict only when the stash passes E1-E6 (2.2); the overview (RB:1951) and the legacy alias (RB:2263-2264) then both carry it through `public_price_view`, which strips only top-level `guard_rejected` and `_` keys (PS:9371-9387). | Projecting after the verdict call keeps the prompt unchanged. Writing before RB:1951 lets one write reach both projections, the saved row and the D05 reader (which reads the same `product_data` list after the builder, SCS:4878-4881, SCS:5797-5800). `_build_scoring_v2` (called at RB:2079) and the factual verdict read only `price.amount` (SS:3171-3175, SS:3240-3248, RB:842-852, RB:873-880), so the new key moves no bar and no sentence. |
| R-X1-5 | The step runs in its own try/except that logs one WARNING and leaves the body as today on any failure; the pop happens before anything that can raise. | The chokepoint's own rule: price handling must never crash the response (RB:1764-1765). |

### 2.2 Server: which listing may be shown

| Id | Rule | Reason |
|---|---|---|
| R-X1-6 | The stash is eligible only when ALL of E1-E6 hold; otherwise no `offsize_listing` is written and the side shows exactly today's pending price. | Orchestrator binding (1): a converted or parked price is never eligible, and a size printed beside a price must be the listing's own. |

| # | Test (on the stashed found price) | Why, with the measured lines |
|---|---|---|
| E1 | `amount` is a finite number > 0 and `currency` is "BHD". | Only a Bahrain shelf price is shown as one. Currency alone is not enough: a Woo hit in a foreign currency is converted and stamped `currency: "BHD"` with `converted_usd` (woocommerce_service.py:251-276), so E2 is also needed. |
| E2 | `estimated` is not True and `_is_genuine_bh_candidate(price)` is True: the method (or `raw_data.source_method`) is in `_GENUINE_BH_SOURCE_METHODS`, neither contains "converted" or "estimated", and the retailer is not a registry `global`-tier domain. | PS:17090-17124. v1 tested set membership only and so admitted a global-tier site stamped with a genuine method (X1_SKEPTIC 2.5). The two writers of the parked price store only converted prices (SCS:7804-7814 selects among "converted" methods; SCS:7997-8003 parks only `converted_usd`), and the miss path returns that parked dict (SCS:7039-7045), so E2 refuses every parked price, as binding (1) requires. `registry_tier` does no blocking I/O: it reads the in-memory registry (SR:764-794, SR:707-732, SR:667-677; with the DB registry flag ON, merchant_registry.py:235-248 reads cached state and may only schedule a background refresh). |
| E3 | `is_price_showable(full_name, <a COPY of the price>, category_used, enforce_correctness=True)` is True. | The same identity, sample, floor and PDP gate every shown price passes (RB:1739; ES:2522-2524). The predicate writes `title` and `guard_rejected` into its argument (PS:1917, PS:1920, PS:1953, PS:1965), so it runs on a copy. |
| E4 | The listing's OWN `title` (a string) holds exactly one distinct ml size under a strict parse: an integer 1..9999, then optional space or hyphen, then "ml" (case-insensitive, word end), NOT preceded by a digit, "." or ","; a second distinct ml value fails. Never read from `price.size`, `raw_data.size`, the product name, specs or a default. | `_SIZE_ML_RE` (PS:4073) has no left boundary, so "7.5ml" reads as 5; the Serper candidate `size` is the lexicographic first of a STRING set (PS:10588-10589: "50ml / 100ml" gives "100ml"); `effective_pair_size_ml` reads the name first and falls back to the 100 ml default (PS:2021-2045, PS:2077-2095); binding (1) names the listing's own title. |
| E5 | `target_ml` is not None and the E4 size differs from it. | A title at the target means the pend came from another field (the name, PS:2027-2030); refusing keeps the shown size the reason for the pend. The target-None branch (PS:2348-2354) is the legacy non-fragrance comparison. |
| E6 | When the builder runs, the side's price is still the pending dict with `unavailable` True and `reason` "size_mismatch". | Only the incident class is in scope; any other pend keeps its own reason (RB:1711-1716). |

Inferred from the code, not measured on the data: the Layton and Libre titles carried at least one ml token other than 100. Reason: a fragrance target of 100 ml needs both names designer-recognized or the reconcile-fix flag ON (PS:2134-2148), and either condition makes an unsized product resolve to 100 ml and NOT pend (PS:2087-2094, PS:2364); the names carry no ml token, both pending dicts carry no `size` (T1:117, T1:129), the C1 specs were `{}` (T1:123), and a Woo hit carries `title` but no `size` key (woocommerce_service.py:270-279). So the only field left is the title. Whether a title held TWO tokens (E4 refuses) stays UNVERIFIED until Q1.

### 2.3 Server: the contract

| Id | Rule | Reason |
|---|---|---|
| R-X1-7 | `price.offsize_listing` has exactly the keys in the table below; `per_100ml` on it, and `size_ml` plus `per_100ml` on the PARTNER's price, appear together or not at all, and only when the partner's own listing also passes E1-E4 on its own title (an on-basis partner whose single title size equals `target_ml`, or a partner that is itself an eligible off-size listing). | Binding (1): no per-ml figure unless BOTH listings are genuine Bahrain listings that state exactly one ml size in their own title. v1 let the partner's size come from the 100 ml default or a converted price (X1_SKEPTIC 2.5; PS:2087-2094; `reselect_to_target_size` admits converted candidates, PS:2179). |
| R-X1-8 | With the flag ON, `price.amount` stays null, `unavailable` stays true, `reason` stays "size_mismatch", the existing optional `price.size` is NOT filled, product-level `best_price` and `retailer` stay null, and `overview.winner`, `scoring.*`, `scoring_v2.dimensions`, the factual verdict, the value badge, the confidence legs and Home / Profile savings are unchanged. | The owner's ruling ("make no cheaper claim") and binding (1). A null amount keeps every consumer quiet with no client change: scoring (SS:1768-1778, SS:330-331), the factual price fact (RB:873-880), Home savings and the smart pick (HR:284-290, HR:571-574), and both bundles' `pricePending`, which hides the price and value bars and the price pill (`ResultsContent.tsx:212 @a74caba7`; `:159 @683f56c0`). |
| R-X1-9 | Flag ON, the builder drops the exact string "has a confirmed Bahrain price while the other relies on an indicative figure" from `scoring_v2.winner_evidence` (RB:1328-1331) when the runner-up's price is a size pend; `scoring_result` itself is not touched. | That sentence (SS:1006-1008) is false for a size pend; `winner_evidence` ships only through `scoring_v2` (RB:1346) and no bundle reads it (grep of both trees), so this is a saved-row truth correction that moves no score or winner. |

| Key | Type | Present when | Meaning |
|---|---|---|---|
| `price.offsize_listing` | object | the side is a size pend and the stash passes E1-E6 | a real Bahrain listing found for a different bottle size than the pair's comparison size |
| `.amount` | number, 3 dp | always in the object | the listing's shelf price in BHD |
| `.currency` | "BHD" | always | |
| `.size_ml` | integer | always | the bottle size from the listing's own title (E4) |
| `.retailer` | string or null | always | the store, as on today's price dicts |
| `.url` | string or null | always | the product page |
| `.title` | string | always | the listing title (IR:100 asks for the title and size in the row) |
| `.source_method` | string | always | the genuine method (E2) |
| `.per_100ml` | number, 3 dp | only under R-X1-7 | round(amount / size_ml * 100, 3) |
| partner `price.size_ml` | integer | only under R-X1-7 | the partner's own title size |
| partner `price.per_100ml` | number, 3 dp | only under R-X1-7 | the partner's amount per 100 ml |

The object is a fresh dict of exactly these keys: no `_` key, no `_cached`, no `guard_rejected`, no `raw_data`, no `in_stock`. Every new key is additive; no key either bundle reads is removed, renamed or retyped (record/s80/contract_freeze.json lists only price.amount, price.currency, price.source_method and price.unavailable under price). The display unit stays a client choice (O3): the server carries the per-100-ml number only.

### 2.4 Server: the dormant D05 defect, the telemetry, the footprint

| Id | Rule | Reason |
|---|---|---|
| R-X1-10 | In `_status_one` (KI:165-248), a price with `unavailable` True and `reason` "size_mismatch" gets the price entry `{"state": "other_size", "source": <normalized host of offsize_listing.url, else null>, "reason": "size_mismatch", "as_of": null, "rung": null}` in place of `unknown / no_price`; this amends the closed S81-17 D05 vocabulary (G3:283-291) by one state, and the amendment is this unit's ruling. | KI:193-206 maps every non-showable price to `unknown / no_price`; the OTA turns a price entry of state `unknown` on an `unavailable` price into "Not listed by the stores we can read yet" (`fieldStatusView.ts:52`, `:58`; `ResultsContent.tsx:367-374 @a74caba7`; `en.json:705`), which is false when a store listed the perfume at another size. Any state other than `unknown` gives kind `none`, which renders today's pending line (`fieldStatusView.ts:58`). v1's fresh / stale would count a null amount as a known price (X1_SKEPTIC G3). The host as `source` keeps the vocabulary's own rule: no name, URL or free text (KI:253-257). |
| R-X1-11 | For the same size pend, the size entry is `known / listing` when `offsize_listing.size_ml` is present or today's `_size_ml(price)` reads one (KI:147-152, KI:210-211); otherwise today's rule runs, and an `unknown` outcome it would give becomes `{"state": "other_size", "source": null, "reason": "size_mismatch"}`. | The Specs body prints "Size: Not listed by the stores we can read yet" for a size entry of state `unknown` with no spec row (`components/results/ResultsAccordion.tsx:135-153 @a74caba7`), the same false sentence for a perfume that was listed; C1 Layton had empty specs (T1:123), so it would print. |
| R-X1-12 | `run_job` treats `other_size` exactly like `unknown` when it writes `kb_gaps` rows (KI:476-481), so the KB ingest output is unchanged. | A size pend is still a missing on-basis price; the seeder's demand signal must not drop. `build_job` copies only `_PRICE_KEYS` (KI:264-267, KI:288), so the KB never ingests the off-size offer (stated limit SL7). |
| R-X1-13 | Flag ON, the body gains `metadata.size_fair`: one entry per size-pended side, `{"product_index": 0 or 1, "outcome": "offsize_listing" or "pended", "reason": null or one closed code, "listing_cached": true, false or null, "per_100ml": true or false}`, and the log gets one INFO line per size-pended side: `[SIZE_FAIR] product_index=<i> outcome=<outcome> reason=<code or none> listing_ml=<int or none> target_ml=<int or none> host=<host or none> cached=<true, false or none>`. | The proof needs a saved-row key and a log line that name the outcome (section 4). `listing_cached` comes from the stash's `_cached` (True on a price-cache hit, SCS:7105-7107; False on a fresh direct hit, SCS:7871): the pending dict drops `_cached`, so `metadata.cache_hit` (RB:49-80) can never say it for a pended side. Closed reason codes: no_stash, no_target, not_bhd, not_genuine, converted, global_tier, estimated, not_showable, no_title, no_title_size, multi_size_title, size_equals_target, not_size_pend, error. The line carries no product name, no query text and no URL path (the U8d practice, as SCS:5282-5285 does for a query). |
| R-X1-14 | The PIN rows of 3.2 are part of the unit's RED. | H1 and H6: flag-OFF identity and the unchanged verdict prompt are proven by a test, never asserted. |
| R-X1-15 | The server footprint is PS (the flag reader, the stash, a pure eligibility helper and the strict title parser), RB (the pop, the projection, `winner_evidence`, `metadata.size_fair`, the log line) and KI (R-X1-10 to R-X1-12); no edit to ES, SCS, SS, HR or the URL path. | H1: keep off the LLMUnavailableError log statements S81-04c edits in ES, image_routes.py and url_extraction_service.py; SCS needs no edit because the builder is shared by every path (R-X1-3). |
| R-X1-16 | The non-fragrance `unit_mismatch` path (`_mark_unit_pending`, PS:3164-3180) and the URL compare path (url_extraction_service.py, which never calls the reconcile or `make_pending_price`: grep this run) are untouched. | Out of the incident class; ENABLE_FRAGRANCE_ONLY_GATE is OFF, so other categories still flow and must stay byte-identical. |

### 2.5 Client half (X1-C) and the paths X1 does not change

| Id | Rule | Reason |
|---|---|---|
| R-X1-17 | X1-C adds a pure reader `services/sizeFairView.ts` that returns a view only when `price.unavailable === true`, `price.reason === 'size_mismatch'` and `price.offsize_listing` has a finite `amount` > 0, `currency` "BHD" and an integer `size_ml` in 1..9999; anything else returns null and the card renders exactly as today. | The client must not trust a malformed body; a null view is today's rendering, so old rows in History and Share (no new key) render unchanged. Neither bundle reads `price.reason` or `price.size` today (X1_SKEPTIC section 1, confirmed). |
| R-X1-18 | In the hero price slot (`ResultsContent.tsx:367-386 @a74caba7`), a non-null view takes precedence over `prov.kind === 'unknown'` and renders: line 1 the amount through the app's price formatter (`utils/formatNumber.ts:96`) followed by the bottle size; a caption with the different-size sentence; and, only when `offsize_listing.per_100ml` is present, a per-100-ml caption. The partner adds its size and per-100-ml caption only when its `price.size_ml` and `price.per_100ml` are present. | The owner's ruling: each found price with its bottle size, a per-ml line, no cheaper claim; binding (1) limits the per-ml line. `pricePending` (`:212`) stays true, so the price and value bars and the price pill stay hidden and nothing on the page says "cheaper". |
| R-X1-19 | Every number in the new strings (the amount, the ml size, the "100", the per-100-ml figure) goes through the app digit policy (`utils/formatNumber.ts`; `applyDigitSystem`, imported as `fieldStatusView.ts:6` does). | X1_SKEPTIC G4: v1 routed only the amount. |
| R-X1-20 | `types/types.ts` `ProductPrice` (`:60-73 @a74caba7`, today without `size` or `reason`) gains the optional `size?`, `reason?`, `size_ml?`, `per_100ml?` and `offsize_listing?` fields; tests live under `__tests__/inc_x1/`. | Typed reads, no `any`. |
| R-X1-21 | X1-C is designed as part of the X4 price card ("price with size", IR:103), merges to main only after the owner approves that design and reads every new Arabic string, and ships in the first OTA after that approval; it is not in Friday's SECOND OTA unless the owner rules it in. | One price-card design and one Arabic read for X1 and X4 (X1_SKEPTIC G5); IR:103 (X4 cannot make the SECOND OTA). The feedback card (unit CL3) is another session's existing section and is not touched; an OTA from a main that carries CL3 needs ENABLE_FEEDBACK_V2 ON first (IR:103). |
| R-X1-22 | The partial bodies change only by the pop: the partial builder never calls the reconcile (the only callers are SCS:4587 and SCS:5340), and the stream partials build from `self._partial_product_data or self._early_specs_buffer_list()` (SCS:3821), while the stream never sets `_partial_product_data` (it is set only at SCS:4551 and reset at SCS:5065), so a stream partial can carry two sticker prices at different sizes, as today. | Pre-existing (X1_SKEPTIC 2.3, confirmed and extended to the tail-deadline partial, SCS:5012); widening X1 into the timeout paths is a separate unit. A partial body carries `metadata.partial: true` (SCS:3909) and is never proof (section 4). |

Draft strings for X1-C (the owner's native read decides the Arabic; nothing below is final):

| Key | English | Arabic (DRAFT) |
|---|---|---|
| `results.price.offsize.withSize` | `{{price}} . {{size}} ml` | `{{price}} . {{size}} مل` |
| `results.price.offsize.per100` | `{{price}} per {{base}} ml` | `{{price}} لكل {{base}} مل` |
| `results.price.offsize.caption` | `Different bottle size: prices not compared` | `حجم عبوة مختلف، لذلك لم نقارن السعرين` |

The English strings contain none of the words the copy rule forbids (`services/sourceMethod.ts:13-15 @a74caba7`: no "estimated", "reference price" or "indicative"), and none duplicates a key (the only size key today is `results.spec.size`, `en.json:796 @a74caba7`). The separator glyph and the display unit (O3) are spec choices the owner confirms with the design.

## 3. Questions the spec answers by measurement

### 3.1 Open measurements (the spec states each answer with file:line before RED)

| # | Question | How to measure |
|---|---|---|
| Q1 | Do the Layton and Libre listing titles carry exactly one ml token (E4), and which size? | One replay comparison's price-candidate log lines (IR:175), or a fixture captured from the adapters' saved responses. If a title holds two tokens or none, E4 refuses and the phone proof for that pair cannot pass (section 4 says so). |
| Q2 | Does any reader outside app/ (scripts/, the eval runner, the admin pages) count `field_status` states, so the new `other_size` state changes a metric? | git grep at the base sha for `field_status` outside app/ (the export holds only app/ and the client src; UNVERIFIED here). Inside app/ the readers are KI and compare_runs.py:297-305 (stores the list as is); inside the OTA client, `fieldStatusView.ts:37-38`, `:52` and `ResultsAccordion.tsx:147` test only `state === 'unknown'`. |
| Q3 | Which existing tests pin `_mark_size_pending`'s signature, the D05 vocabulary (S81-11, S81-17; G3:351 pins "the 2.2 vocabulary only") or the `winner_evidence` list? | git grep of tests/ and the client `__tests__/` at the base sha; each pin that moves needs a ruling in the spec, never a weakening. |
| Q4 | Does any reader between the reconcile and the builder iterate a product dict's keys, so an extra `_` key changes its output? | Read `compute_scores`, `apply_value_badges`, `compute_confidence`, `validate_verdict`, `verdict_comparison_quality` and `_display_product_names` (their calls at SCS:4604-4757). A grep of RB, SCS and SS in this run found no `product.items()` / `pd.items()` iteration; it is not exhaustive. |
| Q5 | Does a Woo variable product's title carry the bottle size, or only its variation? | Read woocommerce_service.py around the title build (the candidate at :270-279) and one saved adapter response; a title without the size gives reason `no_title_size` (stated limit SL3). |

Answered in this run (no longer open): the tier lookup has no blocking I/O (E2's cite); no SSE event dumps a whole product dict (R-X1-1's cite); there is no whole-response cache on the compare path (`get_comparison_cache` / `set_comparison_cache` at cache_service.py:777 and :783 have no caller in app/; `metadata.cached` is `from_cache = not nocache`, SCS:4755, SCS:5506, RB:2104, a "may be cached" mark, not a hit); the genuine price-cache TTL is 7 days by default and env-overridable (PS:157, `price_cache_ttl` PS:204-216), and its production value is not probed (H2); the client shows no OTA update id anywhere (grep of src: `expo-updates` is required only for reloads, `hooks/useLanguage.ts:66`, `i18n/rtlBootstrap.ts:36`).

### 3.2 PIN rows (all in RED; each that asserts new behaviour must fail on the base sha)

| Pin | Asserts |
|---|---|
| P1 | Flag OFF: the sync and stream bodies for the C1, C2 and C3 fixtures are byte-identical to the base sha, and no product dict ever carries `_offsize_listing_src`. |
| P2 | Flag ON vs OFF on the C1 and C2 fixtures: the user message handed to the verdict LLM by `generate_comparison` is byte-identical (captured through the existing LLM stub; no network). |
| P3 | Flag ON vs OFF: `scoring.*`, `overview.winner`, `scoring_v2.dimensions`, `scoring_v2.factual_verdict`, every `value_badge`, `overview.confidence` and every SSE payload before `complete` are identical. |
| P4 | Flag ON: no body (sync, stream, sync partial after the reconcile, stream tail-deadline partial, stream hard-cap partial) carries `_offsize_listing_src` at any depth. |
| P5 | Flag ON, C1 fixture (Layton title with one 125 ml token; Aventus title with one "100ml"): `products[1].price` = today's pending dict + `offsize_listing` with its eight keys and `per_100ml` 68.0; `products[0].price.size_ml` 100 and `per_100ml` 133.46; the overview and the legacy alias carry equal objects; `metadata.size_fair` has one entry, outcome `offsize_listing`. |
| P6 | Flag ON, each of E1-E6 failing alone (a converted_usd price, a parked price, a global-tier retailer, estimated, a non-showable title, no title, an Arabic-only title, "7.5ml", "50ml / 100ml", a title at 100 ml, a non-size pend): no `offsize_listing`, the matching closed reason code, the side exactly as today. |
| P7 | Flag ON, partner title without an ml token, with two tokens, or converted: `offsize_listing` present WITHOUT `per_100ml`, and no `size_ml` / `per_100ml` on the partner. |
| P8 | D05 flags ON, X1 flag OFF and ON: a size pend's price entry is `other_size`, never `unknown`; its size entry is never `unknown`; the `kb_gaps` rows equal the base sha's. A non-size pend keeps `unknown / no_price`. |
| P9 | Flag ON: `winner_evidence` loses only the price-provenance string, and only when the runner-up is a size pend. |
| P10 | The `[SIZE_FAIR]` line carries no product name, no query text and no URL path. |
| P11 | Client: the reader returns null for every malformed body; a body with no new key renders exactly as today; the new branch wins over `prov.kind === 'unknown'`; every number passes the digit policy; `pricePending` stays true; no rendered string contains "cheaper", "less" or a percent. |

DEFERRED TO RED (nothing was run this round): `python <SP>/harness/pyt.py --bound 900 --tag inc-x1-red --log <notes>/inc-x1-red.log --cwd C:/Users/SynAckITPC/Documents/AI/sc-inc-x1 -- tests/test_inc_x1_size_fair.py -q`; then, after the H5 jest probe, `npx jest __tests__/inc_x1 --runInBand` in that worktree's SmartCompareApp/. The file names are proposals.

## 4. PROOF ON THE PHONE

This restates IR:100 for the ruled design. Under it `price.amount` stays null by construction, so the record's backing "products[1].price.amount not null" can never pass; and the record's rule (c) (IR:162: no `size_mismatch` marker in the log) can never pass either, because the reason stays `size_mismatch`. Both are replaced below. A green suite is not proof (H6 (d)).

When it CAN pass: only after ALL of: X1-S merged and deployed; the flip pause lifted (H2, after the OpenAI credential works); the owner flipped `ENABLE_SIZE_FAIR_OFFSIZE_LISTING` on web in its own window; X1-C merged and published in an OTA the owner approved; the phone took that OTA (close and reopen the app twice, as N3). Before that OTA the phone shows today's "لا يوجد سعر مؤكد بعد." for Layton with the flag ON or OFF, on both bundles, so a screenshot taken before the OTA proves nothing and must not be offered. The app shows no OTA update id (3.1), so the bundle is identified by the new line itself: only X1-C can draw a size beside a pending price.

The pairs (Arabic UI, the golden set IR:140-145): pair 1 Creed Aventus EDP vs Parfums de Marly Layton EDP (Layton is the off-size side); pair 2 Lancome La Vie Est Belle EDP vs YSL Libre EDP (Libre); pair 3 Armani Acqua di Gio Profumo vs Versace Eros EDP as the NEGATIVE control. Repeat each as typed before. The free tier allows 3 comparisons a day and 10 a month (IR:83), so pairs 1-3 fit one day and the owner's N6 choice (IR:94) decides any repeat.

What must be visible (pair 1; pair 2 the same for Libre):

| On the Layton card | Must show | Must NOT show |
|---|---|---|
| price line | the amount and its size, for example "85.000 د.ب . 125 مل", digits in the app's digit system | "لا يوجد سعر مؤكد بعد." or "غير مذكور بعد لدى المتاجر التي نتابعها" |
| caption | the different-size sentence | any "cheaper", "less" or "better value" text |
| per-100-ml caption | only if the saved row carries `per_100ml` (S8) | a per-100-ml figure when the row has none |
| the page | no price bar, no value bar, no price pill (as today) | a price or value bar, a percent difference |

The backing in the saved row (`comparisons.full_response`, written by database_service.py:471-486; open the row by its id and record the id and its UTC `created_at`):

| # | Key | Must hold |
|---|---|---|
| S1 | `metadata.partial` | absent or false (a partial body is never evidence, R-X1-22) |
| S2 | `overview.products[1].price` | `amount` null, `unavailable` true, `reason` "size_mismatch" (unchanged meaning) |
| S3 | `overview.products[1].price.offsize_listing` | present; `amount` equals the number on the screenshot; `currency` "BHD"; `size_ml` equals the size on the screenshot and is not 100 |
| S4 | `offsize_listing.title` | contains exactly one ml token under E4's strict parse, and it equals `size_ml` |
| S5 | `offsize_listing.url` host and `.source_method` | the host is a Bahrain store (pair 1 expected alibaksh.com, T1:32) and the method is in the genuine set (expected woo_store_api) |
| S6 | `products[1].price.offsize_listing` (the legacy alias) | equal to S3's object; `products[1]` has no `_offsize_listing_src` key |
| S7 | `metadata.size_fair` | exactly one entry: `product_index` 1, `outcome` "offsize_listing", `reason` null |
| S8 | `per_100ml` | present on Layton's object only if `overview.products[0].price.title` holds exactly one ml token; if present it equals round(amount / size_ml * 100, 3), and `overview.products[0].price.size_ml` and `per_100ml` are present and equal the partner's title size and its arithmetic |
| S9 | `scoring_v2.winner_evidence` | does not contain "has a confirmed Bahrain price while the other relies on an indicative figure" when Layton is the runner-up |

The backing in the deploy log for that request's minutes (read-only, the relay's usual log read):

| # | Line | Must hold |
|---|---|---|
| L1 | `[SIZE_FAIR] product_index=1 outcome=offsize_listing ...` (R-X1-13) | present once; its `host` equals S5's host; its `listing_ml` equals S3's `size_ml` |
| L2 | `[PRICE] BH adapter direct hit for ... via <host> (<method>, ...)` (SCS:7872-7877) | present for Layton with the same host when `metadata.size_fair[0].listing_cached` is false; when it is true the price came from the price cache (7 days by default, PS:157) and the line is legitimately absent, so S4 and S5 carry the identity check alone |
| L3 | `fairness reconciliation skipped` (SCS:4592 sync, SCS:5345 stream) and `[SIZE_FAIR] ... outcome=error` | absent (these replace the record's `size_mismatch` marker for X1) |

Negative control (pair 3): the Armani card still shows "لا يوجد سعر مؤكد بعد."; the row has no `offsize_listing` for Armani; if the parked 40 ml price was pended again, `metadata.size_fair` for Armani says `outcome` "pended" with `reason` "converted". Anything else fails the proof.

Why it cannot pass falsely: the screenshot numbers must equal S3 exactly; the size must come from the listing's own title with one token (S4), so a default, a name-derived size, "7.5ml" or a gift-set title cannot reach the screen; the store must be a genuine Bahrain store (S5), so a converted or parked price cannot; a partial body is refused (S1); the per-100-ml line must be backed by the partner's own title (S8); the old bundles cannot draw the new line, so a pre-OTA screenshot looks like today. A wrong product whose title passes the shipped identity gate (the Versace "for Women" class, T1:59) is NOT caught by X1: that is X10's job (IR:109) and stated limit SL6.

Reporting: each claim records the row id, the UTC time and the OTA it ran on; a pair that cannot pass because its title holds two tokens or none (Q1) is reported as "not provable on this pair", never as a pass; the result is "proven on pairs X, Y", never "fixed". The completeness score (IR:147) does not move under X1 unless O4 rules otherwise.

## 5. Owner steps

| # | Step | Blocks |
|---|---|---|
| O1 | N5 / N5b: RULED 2026-11-11 ("Show each found price with its bottle size and a per-ml line. When the two sizes differ, make no cheaper claim."). No owner action; the relay records the ruling in the ledger, since IR:93 still lists it open. | nothing |
| O2 | Hear this fact, which the ruling keeps: the winner stays as today, and today's C1 winner came partly from Layton's blanked price (wear_value 75 vs a 50 default, margin 1.4, T1:176). Optional (a2): when one side is a size pend, treat the price signal as missing for BOTH sides in scoring, so a blank cannot win; it changes scores and possibly winners on both live bundles and needs its own flag and ruling. X1 does not build it. | nothing in X1 |
| O3 | Confirm the display unit of the "per-ml line": per 100 ml (default; it reads like a bottle price and the server carries it) or per 1 ml (the client divides by 100). Decided with the price-card design (O6). | X1-C only |
| O4 | Confirm the comparison basis stays the 100 ml flagship default (PS:1439) for every house, including one whose flagship is another size (Layton, LIKELY 125 ml, IR:175); changing it is a separate unit. Also rule whether the completeness score (IR:147) gives a point for an `offsize_listing`; default no (a price on another size is not a comparable price), so X1 does not move the daily golden-set score. | the score only |
| O5 | Approve the class of the unflagged D05 part (section 1): it is dormant today and ships without its own flag. | the RED |
| O6 | Approve the price-card design (one design with X4) and read every new Arabic string (2.5 drafts). | X1-C merge |
| O7 | Flip `ENABLE_SIZE_FAIR_OFFSIZE_LISTING` on web in one canary window after the pause lifts; the relay sets it on your yes. Rollback is unsetting it: there is no whole-response cache on the compare path (3.1), so the next comparison is built without the key; rows saved while it was ON keep the key, and the new client reads it. | the proof |
| O8 | Approve and publish the OTA carrying X1-C; take it on the phone (close and reopen twice). | the proof |
| O9 | Run section 4 and send the screenshots with the row ids; the N6 quota choice (IR:94) decides any repeat. | the claim "proven on pairs X, Y" |

## 6. Stated limits

| # | Limit | Where |
|---|---|---|
| SL1 | The server half changes NOTHING on either phone; the store binary and the OTA bundle ignore the new key until X1-C ships. | R-X1-8; section 4 |
| SL2 | The winner, scores and Home savings stay exactly as today, including a winner that comes from the blanked price (C1). | R-X1-8; T1:176; O2 |
| SL3 | A listing whose title states its size in oz only, in Arabic only, with two ml sizes, or not at all (a Woo variation, Q5) stays pended as today (E4); an oz-to-ml converter exists (PS:4099-4101) but is not used. | E4 |
| SL4 | A price served from the L2 database cache as a title-less legacy row stays pended as today (reason `no_title`). | SCS:7109-7128; E4 |
| SL5 | Partial (timeout) bodies are unchanged beyond the pop and can still show two sticker prices at different sizes. | R-X1-22 |
| SL6 | A wrong product whose title passes the shipped identity gate is shown with its size; the identity guard is X10's (IR:109). | E3 |
| SL7 | The KB does not ingest the off-size offer (`_PRICE_KEYS`, KI:264-267). | R-X1-12 |
| SL8 | The completeness score does not count an off-size listing unless O4 rules otherwise. | IR:147 |
| SL9 | If the tier lookup raises, the retailer is treated as not global (PS:17122-17123), as for every genuine price today. | E2 |
| SL10 | A hermetic test is not the production proof; the claim waits for section 4. | H6 |
| SL11 | The converted-price label printed twice on the card (`ResultsContent.tsx:204` and `:392-400 @a74caba7`) is a separate cosmetic defect, not X1's. | X1_MEASURE 3.2 |
| SL12 | Only a size-pended pair gains sizes; a normal pair's prices still show no bottle size until X4's price card. | R-X1-7; IR:103 |

## 7. Out of scope

Per-ml comparison (closed, appendix A) and (a2); changing the 100 ml basis; oz parsing; reconciling the partial paths; the X4 page as a whole (only its price card is shared); the X10 identity guard; the non-fragrance `unit_mismatch` path; the URL compare path; Home and Profile savings; the CL3 feedback card (another session's unit, an existing section); any edit to the LLMUnavailableError log statements (S81-04c); any flag flip, variable or production read by a build agent.

## Appendix A. Design (b) delta: CLOSED

1. Closed: the owner did not choose "Compare per ml" on 2026-11-11, so nothing of design (b) is specced or built; reopening it needs a new ruling and a new brief (this unit's keys would stay valid under it).
2. It would have fed each side's per-100-ml figure into the price signal in place of `price.amount` (SS:1768-1778), so the off-size side would get a price score where today it has none (`MISSING_SCORE`, SS:2457-2459) and the lone priced side no longer takes the 75 a single price gets (SS:2465-2467).
3. Today's C1 winner, Aventus, won by margin 1.4 only because Aventus alone had a price (wear_value 75 vs a 50 default, T1:176); with Layton at 68.000 and Aventus at 133.460 BHD per 100 ml (lower is better, SS:2469-2470) that edge would vanish and the winner would likely have moved to Layton (not computed; the value signal stays missing while specs are empty, SS:330-331, T1:172).
4. Both live bundles would have crowned that new winner the moment the flag flipped, while still showing "No confirmed price yet." for it with no visible reason, because the compare request carries no bundle or version signal (X1_MEASURE 5.2).
5. That silent winner change on both live apps is why the ruled design keeps every score and winner as today (R-X1-8).

## Appendix B. Disposition of X1_SKEPTIC.md

| Skeptic item | Disposition | Where in this brief |
|---|---|---|
| 1 citations (designer helper starts at PS:2098) | confirmed: `_is_designer_fragrance_name` is at PS:2098 | - |
| 2.1 the size fill breaks the prompt invariant; the KB variant side effect | APPLIED: `price.size` is never filled; the stash is a product `_` key; the projection is in the builder after the verdict; P2 pins the prompt; the KB variant effect goes with it | R-X1-1, R-X1-2, R-X1-4, P2 |
| 2.2 Serper size lexicographic; "7.5ml" reads 5 | APPLIED, refined: only the Serper candidate `size` is lexicographic (PS:10588-10589, not 10587-10588); `_candidate_size_ml` and `effective_pair_size_ml` take a numeric min (PS:2166, PS:2083); E4 re-parses the title strictly | E4 |
| 2.3 the partial path never reconciles | APPLIED as a stated limit, extended to the stream tail-deadline partial (SCS:5012); the pop covers all three partial callers; a partial body is never proof | R-X1-3, R-X1-22, S1, P4 |
| 2.4 (b) "computed value" | APPLIED: appendix A says the value signal stays missing; no winner computed | Appendix A |
| 2.5 partner size from a default; converted or global-tier sides | APPLIED: per-ml only between two own-title, genuine, non-global listings | E2, E4, R-X1-7, P7 |
| 2.6 the default keeps winning; `winner_evidence` | APPLIED: stated to the owner (O2) with (a2) offered; the false evidence string is dropped | R-X1-9, O2, SL2 |
| 2.7 proof cannot pass (amount, rule (c), score) | APPLIED: S1-S9 and L1-L3 replace them; O4 rules the score | section 4, O4 |
| 2.7 cache: a pre-flip body served for the TTL; cite `cache_hit: false` | REJECTED: there is no whole-response cache on the compare path (`set_comparison_cache` / `get_comparison_cache`, cache_service.py:783 / :777, have no caller in app/, grep this run), so a flip or rollback acts on the next comparison; `metadata.cache_hit` is the per-price marker (RB:49-80) and is always false for a pended side, since the pending dict has no `_cached` (PS:2010-2018), so it proves nothing. The real cache effect is the price cache (SCS:7100-7107), handled by `listing_cached` and L2 | R-X1-13, L2 |
| 2.7 a proof that passes falsely | APPLIED | section 4, "Why it cannot pass falsely" |
| G1 Home smart pick | confirmed (HR:571-574 skips a null amount); no change | R-X1-8 |
| G2 `listed` collides with D20 | APPLIED: the key is `offsize_listing` | section 0 |
| G3 fresh / stale for a pend | APPLIED: new state `other_size`, ruled as an amendment of the closed D05 vocabulary; gaps unchanged | R-X1-10 to R-X1-12 |
| G4 digit policy | APPLIED | R-X1-19 |
| G5 overlap with X4 | APPLIED | R-X1-21, O6 |
| G6 store-binary claims | confirmed (`pricePending` at `ResultsContent.tsx:159 @683f56c0`; no fieldStatusView there) | - |
| G7 copy policy | confirmed (`services/sourceMethod.ts:13-15`, which also bars two Arabic words the drafts avoid); the Arabic goes to the owner | 2.5 |
| 3 owner questions hide facts | superseded by the ruling; the facts the ruling keeps are stated in O2-O4 | section 5 |

Also corrected from X1_MEASURE.md: "the Redis/L1 response cache stores whole bodies (T1: `cached: true`)" is wrong: `metadata.cached` is `from_cache = not nocache` (SCS:4755, SCS:5506; RB:2104), a "may be cached" mark, not a cache hit. And from the stopped v2 draft: the quota cite is IR:83 (not IR:162); the Serper size cite is PS:10588-10589; the parked price is converted by its two writers (SCS:7804-7814, SCS:7997-8003), not by the docstring alone.

## UNVERIFIED in this round

The titles' ml tokens (Q1); readers of `field_status` outside app/ (Q2); the test pins that move (Q3); key iteration in the scoring and verdict readers (Q4, partial grep only); Woo variation titles (Q5); the Arabic wording; the production value of `GENUINE_PRICE_CACHE_TTL_SECONDS` and of ENABLE_FRAGRANCE_SIZE_RECONCILE_FIX (never probed, H2; X1 depends on neither); the ledger line recording the N5 / N5b ruling (not in the record copy).
