# D2 - Picture, specs, reviews, chips, bars and verdict line (server side)

Source: plain export of main 731bcddf. Every path:line is at 731bcddf. E = ESTABLISHED (read in the code, or a quoted relay log line), L = LIKELY (inference). Nothing here says a production problem is fixed.

## Summary

One pattern runs through all of this: **every stage passes "nothing found" downstream as if it were data**.
- The picture cascade accepts the first http(s) URL Serper returns. Nothing checks relevance.
- The specs extractor stamps "N/A" into all 11 fragrance fields.
- The fact-check counts those 11 N/A fields as 11 "citations", which makes the specs chip **High**.
- The same 11 "unverified" rows feed a reliability score. That score drives the **Versatility** bar and the line "leads on Versatility".
- The model's own sentence saying it found no review data is shown as the review text.

The upstream trigger is RESOLUTION: brand "" and the raw words "Tyger" and "stronger with you" are used as product names (E: `Fetching reviews for:  Tyger`, the double space is the empty brand in the f-string at app/services/review_service.py:765). That belongs to D1. The display faults below would mislead on any thin result, whatever the trigger.

## (a) The picture chain

Order, in app/services/image_service.py `get_product_image_url` (232-344):

| Tier | Code | What it checks |
|---|---|---|
| 1.5 piggyback | 264-268 | Always skipped in the race: the caller passes `page_scrape_image=None` (structured_comparison_service.py:6263) |
| 1.5b unified-search image | 274-281, `extract_image_from_search` 85-129 | Takes the first Knowledge Graph image, then the first organic image, then the first `images` item. Only checks `_is_valid_image_url` |
| 1 Serper Images | 286-314 | `search_images(name, num_results=1)` with the bare product name (295). It takes `images[0].imageUrl` (306-311) |
| 3 LLM pick | 317-333, prompt 136-153 | Routed as site `image_tier3` (text role, so Claude Haiku under ENABLE_ANTHROPIC_TEXT, llm_router.py:218). The prompt has no category |

**What accepted the Blake poem (E):** `_is_valid_image_url` (57-67) is the only gate on every tier. It checks only:
- that the value is a string starting with http:// or https://;
- when ENABLE_DATA_GUARDS_V2 is on, the deny list (`deny_hosts.py:87-89`: fragrantica, parfumo, basenotes, fimgs).

**There is no relevance check of any kind:** no title or brand token match, no category word, no aspect test, no product-photo test.
- The Serper Images result carries a title and a source, but `search_images` is asked for one result (295) and the title is never read.
- The query is the bare name ("Tyger"), with no "perfume" added. So Serper's top image for the word "Tyger" was the poem.
- The log order proves Tier 1.5b missed first (E: the relay quotes "[image] Tier 1 Serper hit for 'Tyger'", and 1.5b returns before Tier 1).

**The only image policy with a host allowlist** is `jsonld_widen.allowed_image_url` (jsonld_widen.py:170-193): https, public host, raster file extension, deny list, then a first-party / platform-CDN / brand-domain allowlist. It is applied only to the price-page override (structured_comparison_service.py:6417-6422, only when ENABLE_IMAGE_PIPELINE_V2 is on), never to the cascade.

**Why "stronger with you" got no picture:**
- (E) The noon adapter's price dict carries no `image_url`. `noon_service._confirm_pdp` (443-467) parses the PDP's Product JSON-LD (417), but it copies only the amount, currency, url, title, seller, brand and stock.
- So the after-race override (structured_comparison_service.py:6406-6429) had nothing to use, although the noon page carried a product image (L: Product JSON-LD normally has `image`).
- (L) The cascade itself returned None or ran out of time. The image race is capped at 5.0 s (structured_comparison_service.py:6033, 6271). Serper was answering in about 10 s (relay: `serper_shopping delta_ms` ~10,000; one of three keys exhausted), so the Serper Images call most likely hit the 5 s cap.
- The tier-timing lines would confirm this (see the log reads below).

**What G-INC-1 (#400) changed (E, from the git diff of a74caba7..731bcddf on image_service.py):** only INC-X2a timing logs.
- It added `_log_img_tier` (220-225), one `[IMG_TIER] tier=... outcome=... ms=...` line per tier, and a cancellation line (338-344).
- The tier order and acceptance logic are byte-for-byte unchanged.
- S81-07c (1da03aff) changed only the `image_tier3` router site (no output schema). No relevance gate was added.

## (b) Specs under ENABLE_ANTHROPIC_TEXT

**The chain:**
- `_get_specs` (structured_comparison_service.py:6831-6926): L1 Redis cache, then L2 DB, then the spine, then `extract_specs` over `_format_numbered_search_results(unified_search)` (6865-6870).
- The unified search query is `"{search_query} specifications reviews price"` (6139). For this run that is the raw words, since the brand is "".
- `extract_specs` (extraction_service.py:1584-1747) calls `_llm_router.route("specs", ...)` (1611). That is site `specs`, role `text`, Claude max_tokens 1536 (llm_router.py:212).
- The model is `anthropic_model("text")`, which defaults to claude-haiku-5-5 (model_config.py:218, 227-234; an env override is possible but was not read). Thinking is disabled and effort is low (llm_router.py:741-748).
- There is no JSON schema: the prompt itself asks for JSON, and the reply is parsed with `json.loads` (1627).
- The prompt allows falling back to training data (extraction_service.py:653, 660) and says to "return null if unknown" (661).

**How 11 dash rows were made (E):**
1. The fragrance schema has exactly 11 fields (extraction_service.py:213-227).
2. With ENABLE_SPECS_NO_FABRICATION off, every empty, null or "or null" field is stamped "N/A" (1706-1707). The output loop walks the full schema list (1679), so a reply of all nulls yields 11 "N/A" keys.
   - With the flag on, uncited fields are dropped instead (1692-1705), and no rows would appear.
   - The flag is not in the brief's list. 11 rows means it is most likely off (L).
3. `_clean_specs` stamps "N/A" again for empty values (structured_comparison_service.py:3551-3552).
4. The client builds the table from `products[i].specs`, not from the server rows:
   - `allSpecKeys` falls back to a "structural" key set when every value is N/A (ResultsAccordion.tsx:199-222);
   - rows where both sides are a dash are kept on purpose (596-599);
   - the header prints `${allSpecKeys.length} dimensions` (293-296), which gives "11 dimensions".
5. The server's `_build_specs_rows` skips only None or "" (response_builder.py:762). "N/A" rows therefore pass too, and they feed `winnerByField` only.

If one product's specs leg timed out (8.0 s cap, 6018) or errored, it becomes None or {}. The other product's 11 N/A keys still produce 11 all-dash rows. So the screen cannot tell "the model found nothing" from "it timed out" (L, both are possible here).

**Caching (E):** an all-N/A specs dict is cached for 7 days in L1 and 30 days in L2 (6913-6922), unless the unified search carried the timeout mark. A wrong-identity empty sheet therefore sticks.

**[TIER2_FALLBACK] (E):**
- `tier2_fill_non_negotiables` (767-866) runs, for each missing non-negotiable field (fragrances: concentration and longevity), one `search_web` call (822) and then one `extract_specs_targeted` LLM call (831), one after the other, under a 4.0 s wall (660, 858). The timeout log is at 861.
- With Serper at ~10 s, the search alone overruns 4 s, before Claude is even called. The timeout comes from Serper latency, not Claude latency (L).
- It is a silent no-op that adds about 4 s of wall time. Tier 3 (3.0 s, 883) follows.

## (c) Reviews

**The chain (E):**
- `get_reviews` logs at review_service.py:765. It builds the context from the top 10 unified-search organic results (`format_review_search_results` 650-675), with no variant or identity filter.
- It calls `extract_reviews` (extraction_service.py:1863-1920): site `reviews`, text role, Claude 1024 tokens (llm_router.py:215).
- The prompt is `REVIEWS_EXTRACTION_SYSTEM` (978-1030). It asks for `average_rating`, `total_reviews`, and `review_summary` {overall_sentiment, consensus (a required "2-3 sentence professional brief"), highlights[], review_volume, agreement_level}. It has **no "no data" field**.
- `_normalize_review_response` defaults the sentiment to "mixed" (1929).

**How "No review data was available ..." became the review text (E):**
- The model put its explanation into `review_summary.consensus`.
- The client shows `review_praise` (ResultsAccordion.tsx:414-420), built by `build_review_praise` (review_service.py:547-646).
- With no positive highlights, `build_review_praise` falls back to the consensus whenever the sentiment is not "negative" and the text is at least 12 characters (631-645). A "mixed" no-data sentence passes.
- Nothing marks it as no data. The result is also cached as a normal non-error review dict (792-809).

**The header (E):** the client sums `review_count` and averages whatever ratings exist, then always appends "reviews across both" (ResultsAccordion.tsx:171-195, 263-276).

## (d) The chips "Specs High" and "Reviews Low"

`compute_confidence` (scoring_service.py:1150-1253) works as follows.
- **Specs leg (E):** strong when `best_pct >= 40 or best_citations >= 8` (1207). `best_citations` comes from `_product_fact_check_pcts` (1089-1115). With ENABLE_CONFIDENCE_FACTCHECK_WIRING off, it returns `total = verified + likely + unverified + flagged` (1115).
- The fact-check map comes from `verify_spec_citations` (fact_check_service.py:204-263, through structured_comparison_service.py:6440). It scores every non-meta key, including "N/A" values: no `_source` gives "unverified" (219-220).
- So 11 N/A fields become `specs_unverified = 11` (fact_check_service.py:568), total = 11, which is at least 8. **The specs leg is "strong", and the client maps strong to High** (ConfidencePills.tsx:54-58).
- The exact input: 11 unverified N/A fields on at least one product. With the wiring flag on, citations = verified + likely = 0, which gives weak. That flag has a hard activation order (scoring_service.py:1044-1050).
- **Reviews leg (E):** `max_reviews >= 100` is strong and `>= 50` is acceptable (1181-1183). Neither product had a count, so the leg is weak and shows as Low.

## (e) The bars and the verdict line

**One "Versatility" bar:**
- Fragrance `versatility_score` is a proxy for **reliability** (scoring_service.py:2177).
- Reliability is the fact-check citation quality: `(verified*1 + likely*0.7 + unverified*0.3)/total`, +0.1 when `price_verified`, and +0.05 or -0.1 for review consistency (`_score_reliability`). It says nothing about how versatile a scent is.
- With 11 unverified rows, both products score about 0.3. Their per-product price or review adjustments differ (L: the "stronger with you" price earned the +0.1, giving about 40 vs 30). That escapes the tie-collapse (2251+) and the missing_data omission, because reliability is only "missing" when the total is 0 (1835-1839).
- The ENABLE_RELIABILITY_UNCHECKED_ABSENCE path would return None here, but the bar appeared, so the flag is likely off (L).
- `_dim_from_category_lookup` emits the bar with a hard-coded `confidence: "medium"` (3585) and the caption "More versatile" (3680-3681).
- All other fragrance dims had no signal on both sides and were dropped (3569-3571, 3907-3910).

**The verdict line (E):** `_build_factual_verdict` (response_builder.py:1134-1181).
- The price and rating candidates need both products, so they are None.
- `_top_dim_candidate` picks the only dim left, which gives "stronger with you leads on Versatility." (1097).
- Line 2 finds no runner-up dim, no two prices and no two ratings, so it falls back to the neutral "stays in the conversation as a close alternative." (1131).
- The priorities chip lists weight shifts from the user's preferences only (`_safe_compute_applied_shifts` 802-816). It never checks whether those dims exist in the result (L).

**The 2026-11-13 items:**

| Item | Cause | Conf. |
|---|---|---|
| A bar captioned "N/A vs Moderate projection" | `_compose_delta_text` tests `if sa and sb` (scoring_service.py:3673-3676), and the string "N/A" is truthy. The bar itself comes from the **review** proxy (2177), not from sillage | E |
| "8h vs 8h" with unequal bars | `_extract_hours` takes the first number, so "8" and "8-10 hours" both give 8.0, and the caption is `int(max) vs int(min)` (3660-3667). The bars come from the spec_secondary composite. The F4.1 reorder needs a gap of at least 1 h (2435) | E |
| "4.7 avg, 38,000 reviews across both" with one rating | The client averages only the rated product and still says "across both" (ResultsAccordion.tsx:171-195, 263-276). The count comes from a real rating provider (structured_comparison_service.py:6717), not the model, which is nulled at 597 | E (label), L (which source) |
| Sauvage "8" and "100" without units | The subtype prompt asks for `longevity_hrs` and `volume_ml`. The alias copy moves the bare number into `longevity` and `volume` and drops the unit carried in the key name (extraction_service.py:254-257, 1651-1668; stored by `str(val)` at 1712) | E (path), L (that this path fired) |
| One top note; "Oriental" for Sauvage EDP | The model's own output, partly from training data (prompt 653). Nothing checks it | L |
| Review text mixing in Elixir; stitched sentences | The context is the top 10 organic results with no flanker or concentration filter (review_service.py:650-668), and the prompt has no "this exact variant only" rule. The praise joins two highlight clauses with " and " inside a frame (621-629), which reads as stitched | E (mechanism), L (Elixir source) |

## (f) Root causes and smallest fixes

| ID | Root cause | Where | Class | Conf. |
|---|---|---|---|---|
| RC1 | A picture is accepted with no relevance check (URL scheme and deny list only), and the query is the bare name, num=1 | image_service.py:57-67, 295-311, 85-129 | SEARCH | E |
| RC2 | The noon adapter drops the PDP's JSON-LD image, so the price-page override has nothing to use | noon_service.py:443-467; structured_comparison_service.py:6406-6429 | DATA | E |
| RC3 | The 5 s image race against ~10 s Serper leaves "stronger with you" with a placeholder | structured_comparison_service.py:6033, 6271 | TIMEOUT | L |
| RC4 | An all-null spec reply becomes 11 "N/A" fields; the client's structural fallback renders them as "11 dimensions" of dashes; the empty sheet is cached | extraction_service.py:1706-1707; structured_comparison_service.py:3551, 6913; ResultsAccordion.tsx:206-222, 593-599 | DISPLAY | E |
| RC5 | "N/A" fields count as fact-check rows, so citations = 11 and Specs shows High | fact_check_service.py:213-220; scoring_service.py:1115, 1207 | DISPLAY | E |
| RC6 | The Versatility bar and the verdict line come from citation-reliability scores of N/A rows, shown with "medium" confidence | scoring_service.py:2177, `_score_reliability`, 3585; response_builder.py:1165, 1097 | DISPLAY | E (path), L (exact scores) |
| RC7 | The model's no-data sentence goes out as review praise, because the schema has no no-data signal | extraction_service.py:978-1000; review_service.py:631-645 | DISPLAY | E |
| RC8 | Tier 2 runs Serper plus an LLM call under a 4 s wall, which always times out when Serper is slow | structured_comparison_service.py:660, 822-861 | TIMEOUT | E |
| RC9 | Caption faults: "N/A" treated as a value, the first-number hours extraction, units dropped by the alias copy, "across both" | scoring_service.py:3673-3676, 3660-3667; extraction_service.py:1651-1668; ResultsAccordion.tsx:263-276 | DISPLAY | E |
| RC10 | No variant filter in the reviews context; two clauses stitched together | review_service.py:650-668, 621-629 | DATA | L |
| RC0 | Empty brand and raw words used as the product identity (D1) | review_service.py:765 (log) | RESOLUTION | E |

**Fixes.** Each server fix ships behind a dark flag in the house style. Per the rollout rule, walk every flag mix before a flip.

| ID | Fix | What the user sees | Size | Ships |
|---|---|---|---|---|
| F1 | **Picture relevance gate.** Query `"{brand} {name} {concentration} perfume"`, ask for num=5, and accept the first image whose `title` or `source` contains a significant name token plus a brand token (or a fragrance word: perfume, parfum, eau, edt, edp, cologne, fragrance). Apply the same test to the Knowledge Graph title and organic title in Tier 1.5b. Return None when the brand is empty and the identity is unresolved. Optionally reuse `jsonld_widen.allowed_image_url` as the host gate | A placeholder instead of a poem or a truck part | M | server deploy |
| F2 | Copy `product["image"]` (the first https raster) into the noon price dict as `image_url`. With ENABLE_IMAGE_PIPELINE_V2 on, check that noon's image CDN passes `_image_host_allowlisted` (state both branches) | The bottle photo next to the noon price | S | server deploy |
| F3 | **No N/A rows on the server.** Drop NA-token values when projecting `products[i].specs` into the response (or in `_clean_specs`), and skip both-NA rows in `_build_specs_rows` | No dash table. The client then shows the bare "dimensions" header; a client follow-up should hide the section | S | server deploy (+ an over-the-air update to hide the empty section and drop the structural fallback) |
| F4 | In `verify_spec_citations`, skip fields whose value is an NA token | Specs Low instead of High; the reliability total becomes 0, so the Versatility bar and "leads on Versatility" disappear. This changes reliability for every product with N/A fields: flag it and run the S81-07-style comparison | S | server deploy |
| F5 | Add `"has_review_data": bool` to the reviews schema. When it is false, or there are no highlights and the volume is "minimal", null the consensus and return no praise. Add a phrase guard ("no review data", "provided search results") as a belt | "No reviews found yet" instead of the model's apology | S | server deploy |
| F6 | Do not cache an all-N/A spec sheet or a no-data reviews dict at L1 or L2 | A later correct identity is not masked for 7 to 30 days | S | server deploy |
| F7 | Skip Tier 2 and Tier 3 when the brand is empty or the unified search was timed out or empty, or reuse the unified-search snippets instead of a new Serper call per field | About 4 s less wall time; no change to values | S | server deploy |
| F8 | Caption fixes: NA-token check in the projection caption; "Similar wear time" when the hours are equal; append the unit ("hours", "ml") to a bare number in the alias copy | No "N/A vs", no "8h vs 8h", units shown | S | server deploy |
| F9 | Show the rating with the rated product's name instead of "across both" when only one product has a rating | Honest header | S | over-the-air update |
| F10 | Reviews prompt rule: "only this exact concentration/flanker; ignore Elixir/Parfum/Intense pages unless named". Use one clause, not two joined | No Elixir mix-ins, no stitched sentences | M | server deploy |
| F11 | INC-X6 honest bars (planned): mark dims driven by reliability or popularity proxies as missing when their spec or review basis is empty; drop the hard-coded "medium" | No bar or verdict line built from nothing | M | server deploy |

**Recommended first batch:** F1, F4, F5 and F3. Together they remove every confident-looking empty section on this screen.
