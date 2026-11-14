# S95-FIX log reads, 2026-11-14 (read-only relay reader)

Source: Railway get-logs (deploy stream) and describe-service on the web service 7ab6a780-e4df-4f72-97c2-b95992b96312, production environment dbe6371f-fc3a-42cb-abea-e633557ae1ad. The reader made no other calls: no list-variables, no value reads, no changes. Railway reported the current deployment as 21a01677 (created 2026-11-14 15:13 UTC). The logs it returned for 2026-11-13 come from the service's earlier deployments.
Redaction: no key-like or token-like text appeared in any returned line. No IP addresses appeared. Times are Railway receive times in UTC. Where the app's own timestamp differs by more than 1 s, it is given in brackets.

## 1. Calls made

| # | Window (UTC) | Filter | Returned |
|---|---|---|---|
| 1 | 2026-11-13 21:19:40 to 21:20:15 | IMG_TIER | 8 |
| 2 | same | PRICE_FILTER_TRACE | 1 |
| 3 | same | NOON | 2 |
| 4 | same | GL_FALLBACK_TRACE | 2 |
| 5 | same | race timeout | 4 |
| 6 | same | Specs extraction | 0 |
| 7 | same | Redis GET error | 0 |
| 8 | same | (none) | 45 |
| 9 | 21:18:40 to 21:21:15 (+1 min each side) | Specs extraction | 0 |
| 10 | 21:18:40 to 21:21:15 (+1 min each side) | Redis GET error | 0 |
| 11 | 21:18:40 to 21:21:15 (+1 min each side) | anthropic | 5 |
| 12 | 01:36:20 to 01:36:45 (old-consent run) | PRICE | 8 |
| 13 | same | Chanel | 9 |
| 14 | same | (none) | 38 |
| 15 | 01:35:20 to 01:37:45 (+1 min each side) | PRICE | 42 |
| 16 | 01:42:00 to 01:42:30 (new-account run) | PRICE | 0 |
| 17 | same | Chanel | 3 |
| 18 | same | (none) | 27 |
| 19 | 01:41:00 to 01:43:30 (+1 min each side) | PRICE | 0 |
| 20 | 01:41:00 to 01:43:30 (+1 min each side) | Chanel | 3 (the same 3 as call 17) |
| 21 | describe-service, web | - | variable names only |

Section 7 also asked for `GL_FALLBACK_TRACE` and `race timeout`, so calls 4 and 5 were added to the workflow's list. Section 7 also asked "which five calls went to api.anthropic.com", so call 11 was made.

## 2. "stronger with you" vs "Tyger" (2026-11-13 21:19:40 to 21:20:15, unfiltered: 45 lines, all shown in order, trimmed)

| Time | Sev | Message |
|---|---|---|
| 21:19:39.407 | info | HTTP Request: POST https://api.anthropic.com/v1/messages 200 OK (Anthropic call 1 of 5. It is 0.6 s before the window and came from call 11) |
| 21:19:42.815 | info | [MAGENTO] graphql HTTP 403 for klinq.com/graphql |
| 21:19:43.612 | info | [PRICE] Shopify catalog HTTP 401 for bh.azhaperfumes.com |
| 21:19:43.868 | info | [MAGENTO] graphql HTTP 403 for klinq.com/graphql |
| 21:19:43.883 | info | [PRICE] Shopify catalog HTTP 401 for bh.azhaperfumes.com |
| 21:19:46.969 | info | [PRICE] woo converted_usd: BHD 2.442 for 'stronger with you' (oudworlds.com) |
| 21:19:47.313 | info | [NOON] buy-box offers[0] accepted for N70208068V: 29.320 BHD (Luna) |
| 21:19:49.725 | info | [IMG_TIER] tier=piggyback outcome=skipped ms=0 |
| 21:19:49.725 | info | [IMG_TIER] tier=search_payload outcome=miss ms=0 |
| 21:19:49.929 | info | [IMG_TIER] tier=serper_budget outcome=hit ms=176 |
| 21:19:51.684 | info | [PRICE_SUBSTAGE] stronger with you stage=serper_shopping delta_ms=10155 cum_ms=10155 |
| 21:19:51.684 | info | [GL_FALLBACK_TRACE] query='stronger with you' region=bh shopping_region=us_fallback items=40 category=fragrances |
| 21:19:51.684 | info | [PRICE] Selected: Aura Fragrance (tier 0.5) at BHD 6.38 for 'stronger with you' (2 candidates; variant_rank=0.0 size=15ml conc=EDT) |
| 21:19:51.684 | info | [PRICE_SUBSTAGE] stronger with you stage=escalate_decision delta_ms=15 cum_ms=10170 |
| 21:19:52.445 | info | [PRICE] BH adapter direct hit for stronger with you: 29.320 BHD via noon.com (page_scrape_jsonld, zero Serper/render, genuine BHD) |
| 21:19:52.445 | info | [PRICE_SUBSTAGE] Tyger stage=serper_shopping delta_ms=9940 cum_ms=9940 |
| 21:19:52.445 | info | [GL_FALLBACK_TRACE] query='Tyger' region=bh shopping_region=us_fallback items=40 category=fragrances |
| 21:19:52.445 | info | [PRICE_FILTER_TRACE] zero candidates from 40 shopping items for 'Tyger', all rejected by counterfeit/accessory/min_price/strict_title_match/numbers_match/match_score filters. First 3 titles: 'Tyger Auto T2 Low Profile Soft Roll-up Truck Bed Tonneau Cov', 'Tyger Auto Tyger Fury Short Stubby Front Bumper Fit 07-18 Wr', 'Tyger Auto Tyger TG-CP8U3228 Tonneau Cover Cleaner & Protect' |
| 21:19:52.445 | info | [PRICE_SUBSTAGE] Tyger stage=escalate_decision delta_ms=10 cum_ms=9950 |
| 21:19:52.519 | info | Fetching reviews for: stronger with you (category: fragrances) |
| 21:19:55.242 | warn | [L2.6] unified search timeout (limit 12.0s) |
| 21:19:55.499 | info | [IMG_TIER] tier=piggyback outcome=skipped ms=0 |
| 21:19:55.499 | info | [IMG_TIER] tier=search_payload outcome=miss ms=0 |
| 21:19:55.692 | info | [IMG_TIER] tier=serper_budget outcome=hit ms=189 |
| 21:19:56.402 | info | [IMG_TIER] cancelled tier=serper_images tier_ms=6503 total_ms=6680 |
| 21:19:56.483 | info | Fetching reviews for: Tyger (category: fragrances) |
| 21:19:57.748 | info | HTTP Request: POST https://api.anthropic.com/v1/messages 200 OK (call 2 of 5) |
| 21:19:58.178 | info | HTTP Request: POST https://api.anthropic.com/v1/messages 200 OK (call 3 of 5) |
| 21:19:58.760 | info | [IMG_TIER] tier=serper_images outcome=hit ms=3018 |
| 21:19:58.760 | info | [image] Tier 1 Serper hit for 'Tyger' |
| 21:19:58.760 | warn | [L2.6] Phase 1 race timeout for price (limit 15.0s) |
| 21:19:58.760 | info | [L2.6] phase 2 skipped residual=9.5s product=1 |
| 21:20:00.174 | warn | [L2.6] Phase 1 race timeout for specs (limit 8.0s) |
| 21:20:00.174 | warn | [L2.6] Phase 1 race timeout for reviews (limit 10.0s) |
| 21:20:00.174 | warn | [L2.6] Phase 1 race timeout for image_url (limit 5.0s) |
| 21:20:00.517 | info | [L2.6] phase 2 skipped residual=7.7s product=0 |
| 21:20:02.760 | info | [TIER2_FALLBACK] timeout filling ['concentration', 'longevity'] for Tyger |
| 21:20:04.529 | info | [TIER2_FALLBACK] timeout filling ['concentration', 'longevity'] for stronger with you |
| 21:20:04.721 | info | HTTP Request: POST https://api.anthropic.com/v1/messages 200 OK (call 4 of 5) |
| 21:20:04.721 | warn | [EXTRACT_SYNTH] Failed: Expecting value: line 1 column 1 (char 0) (module openai_service) |
| 21:20:06.732 | info | HTTP Request: POST https://api.anthropic.com/v1/messages 200 OK (call 5 of 5) |
| 21:20:06.732 | warn | [EXTRACT_SYNTH] Failed: Expecting value: line 1 column 1 (char 0) (module openai_service) |
| 21:20:06.912 | warn | Comparison generation error: OpenAIEgressStoppedError |
| 21:20:06.912 | warn | PROS_POP_DIAGNOSTIC path=compare_from_text keys=['winner_index', 'error'] p0_pros_present=False p1_pros_present=False |
| 21:20:06.912 | warn | [content_safety] L3 moderation API failed (fail-open): openai dispatch stopped locally (ENABLE_OPENAI_EGRESS_STOP) |
| 21:20:07.024 | warn | Failed to update behavior profile: column comparisons.category_used does not exist (42703) |

What these lines show. These are a reading, not a code check:
- IMG_TIER. Two image runs, each logging piggyback skipped, then search_payload miss, then serper_budget hit. One serper_images tier was **cancelled at 6503 ms** at 21:19:56.40. The other was a **hit at 3018 ms** at 21:19:58.76, followed by "Tier 1 Serper hit for 'Tyger'". So the stronger-with-you image search was cancelled after about 6.5 s and Tyger's answered. Then "Phase 1 race timeout for image_url (limit 5.0s)" fired at 21:20:00.17. This settles the open point in report section 8: the stronger-with-you picture miss was a timeout or cancellation, not an empty or refused URL.
- Price. The Phase 1 price race timed out at 15 s at 21:19:58.76. This was after the noon direct hit for stronger with you (21:19:52.45) and after Tyger's zero-candidate trace.
- Specs and reviews. Both Phase 1 races timed out (specs at 8 s, reviews at 10 s) at 21:20:00.17. No "Specs extraction" line exists in the window or in the window widened by one minute. The two EXTRACT_SYNTH failures ("Expecting value", an empty or non-JSON body) each follow an Anthropic 200 OK by under 0.1 s.
- Anthropic. Five POSTs, all 200 OK, at 21:19:39.4, 21:19:57.7, 21:19:58.2, 21:20:04.7 and 21:20:06.7.
- Redis. No "Redis GET error" line in the window or in the window widened by one minute.

## 3. Bleu de Chanel price lines

### 3a. Old-consent run (01:36:20 to 01:36:45 unfiltered, 38 lines; PRICE widened to 01:35:20 to 01:37:45, 42 lines)

Before the window (from the widened PRICE call):
- 01:36:14.916 to 01:36:14.918 (app 01:36:12.76 to 01:36:13.60), info: 33 lines "[PRICE] Shopify catalog HTTP 403 for <host>". The hosts were bh.asgharali.com, en-bh.ajmal.com, goldencollections.net, bh.afnan.com, bh.taifalemarat.com, beautyandblends.com, bh.jashanmal.com, bahrain.naseem.com, perfumistaaloud.com, bh.mubkhar.com, bh.azhaperfumes.com, alhajisbahrain.com, rasasistore.com, ksa.swissarabian.com, ardalzaafaranshop.com, sa.ajmal.com, and gazzaz.com.sa. Each was hit twice, once per product, except gazzaz.com.sa, which was hit once.
- 01:36:17.077, info: [PRICE] woo woo_store_api: BHD 70.0 for 'Bleu de chanel EDP' (theperfumesclub.com)

The window, in order (unfiltered):

| Time | Sev | Message |
|---|---|---|
| 01:36:20.894 | info | [PRICE_SUBSTAGE] Sauvage EDP stage=serper_shopping delta_ms=9041 |
| 01:36:20.894 | info | [GL_FALLBACK_TRACE] query='Sauvage EDP' region=bh shopping_region=us_fallback items=40 category=fragrances |
| 01:36:20.913 | info | [PRICE] Selected: etnoirperfumes.com (tier 0.5) at BHD 5.64 for 'Sauvage EDP' (1 candidates; size=None conc=EDP) |
| 01:36:20.913 | info | [PRICE_SUBSTAGE] Sauvage EDP stage=escalate_decision cum_ms=9060 |
| 01:36:20.913 | info | [PRICE_SUBSTAGE] Bleu de chanel EDP stage=serper_shopping delta_ms=10161 |
| 01:36:20.913 | info | [GL_FALLBACK_TRACE] query='Bleu de chanel EDP' region=bh shopping_region=us_fallback items=40 category=fragrances |
| 01:36:20.932 | info | **[PRICE] Selected: CHANEL (tier 1.0) at BHD 50.76 for 'Bleu de chanel EDP' (11 candidates; variant_rank=1.0 size=None conc=EDP)** |
| 01:36:20.932 | info | [PRICE_SUBSTAGE] Bleu de chanel EDP stage=escalate_decision cum_ms=10179 |
| 01:36:21.131 | info | [ADAPTER DROP] jsonapi:nasserpharmacy.com: SLOW-MISS after 9.63s |
| 01:36:21.200 | info | Fetching reviews for: Bleu de chanel EDP (category: fragrances) |
| 01:36:21.200 | warn | Reviews extraction error: OpenAIEgressStoppedError |
| 01:36:21.482 | info | [ADAPTER DROP] jsonapi:nasserpharmacy.com: SLOW-MISS after 8.97s |
| 01:36:21.905 | warn | [L2.6] unified search timeout (limit 12.0s) |
| 01:36:23.155 | info | **[PRICE] BH adapter direct hit for Bleu de chanel EDP: 70.000 BHD via theperfumesclub.com (woo_store_api, zero Serper/render, genuine BHD)** |
| 01:36:24.018 | info | [PRICE] BH adapter direct hit for Sauvage EDP: 58.110 BHD via noon.com (page_scrape_jsonld, genuine BHD) |
| 01:36:24.271 | warn | Specs extraction error: OpenAIEgressStoppedError |
| 01:36:24.271 to 01:36:24.440 | info | [IMG_TIER] piggyback skipped / search_payload miss / serper_budget hit ms=174 |
| 01:36:25.725 | info | Fetching reviews for: Sauvage EDP (category: fragrances) |
| 01:36:25.725 | warn | Reviews extraction error: OpenAIEgressStoppedError |
| 01:36:27.982 | info | [IMG_TIER] tier=serper_images outcome=hit ms=8842, then [image] Tier 1 Serper hit for 'Bleu de chanel EDP' |
| 01:36:28.714 | info | [L2.6] phase 2 skipped residual=9.5s product=0 |
| 01:36:30.064 | info | [IMG_TIER] cancelled tier=serper_images tier_ms=5624 total_ms=5798 |
| 01:36:30.065 | warn | [L2.6] Phase 1 race timeout for image_url (limit 5.0s) |
| 01:36:30.412 | info | [L2.6] phase 2 skipped residual=7.8s product=1 |
| 01:36:32.691 | info | [TIER2_FALLBACK] timeout filling ['concentration', 'longevity'] for Bleu de chanel EDP |
| 01:36:32.953 | warn | [EXTRACT_SYNTH] Failed: openai dispatch stopped locally (ENABLE_OPENAI_EGRESS_STOP) |
| 01:36:34.001 | warn | [EXTRACT_TARGETED] Failed: openai dispatch stopped locally (ENABLE_OPENAI_EGRESS_STOP) |
| 01:36:34.605 | info | [TIER2_FALLBACK] timeout filling ['concentration', 'longevity'] for Sauvage EDP |
| 01:36:34.689 | warn | [EXTRACT_SYNTH] Failed: openai dispatch stopped locally (ENABLE_OPENAI_EGRESS_STOP) |
| 01:36:34.886 | warn | Comparison generation error: OpenAIEgressStoppedError |
| 01:36:34.886 | warn | PROS_POP_DIAGNOSTIC path=compare_from_text keys=['winner_index', 'error'] |
| 01:36:34.886 | warn | WINNER_INDEX_MISMATCH scoring=1 gpt=0 win_margin=3.9 scoring_name='Sauvage EDP' gpt_name='Bleu de chanel EDP', using deterministic scoring |
| 01:36:34.886 | warn | [OPENAI_EGRESS] dispatch stopped locally surface=moderations |
| 01:36:34.886 | warn | [content_safety] L3 moderation API failed (fail-open): openai dispatch stopped locally |
| 01:36:35.283 | warn | Failed to update behavior profile: column comparisons.category_used does not exist (42703) |

The Chanel filter (9 lines) returned only lines already listed above.

### 3b. New-account run (01:42:00 to 01:42:30 unfiltered, 27 lines; PRICE returned 0 lines, also 0 when widened to 01:41:00 to 01:43:30)

| Time | Sev | Message |
|---|---|---|
| 01:42:06.216 (app 01:42:02.754) | warn | [SPEND] breaker fail-open (TimeoutError), admitting and not recording |
| 01:42:07.919 to 01:42:08.129 | info | [IMG_TIER] piggyback skipped / search_payload miss / serper_budget hit ms=168 |
| 01:42:08.855 | info | Fetching reviews for: Bleu De Chanel EDP (category: fragrances) |
| 01:42:09.399 | warn | [CIRCUIT] anthropic breaker read failed (TimeoutError), failing open |
| 01:42:09.403 | warn | [CIRCUIT] anthropic breaker read failed (TimeoutError), failing open |
| 01:42:09.808 to 01:42:09.982 | info | [IMG_TIER] piggyback skipped / search_payload miss / serper_budget hit ms=169 |
| 01:42:10.661 | warn | [CIRCUIT] anthropic breaker read failed (TimeoutError), failing open |
| 01:42:10.792 | info | Fetching reviews for: Sauvage EDP (category: fragrances) |
| 01:42:12.817 | info | [IMG_TIER] tier=serper_images outcome=hit ms=4580, then [image] Tier 1 Serper hit for 'Bleu De Chanel EDP' |
| 01:42:12.817 | info | HTTP Request: POST https://api.anthropic.com/v1/messages 200 OK |
| 01:42:12.817 | warn | [LLM_CREDENTIAL] provider=anthropic state=ok status=none source=dispatch |
| 01:42:13.474 | info | HTTP Request: POST https://api.anthropic.com/v1/messages 200 OK |
| 01:42:13.682 | info | [IMG_TIER] tier=serper_images outcome=hit ms=3673, then [image] Tier 1 Serper hit for 'Sauvage EDP' |
| 01:42:13.881 | info | HTTP Request: POST https://api.anthropic.com/v1/messages 200 OK |
| 01:42:14.098 | info | HTTP Request: POST https://api.anthropic.com/v1/messages 200 OK |
| 01:42:19.498 | info | [RATING] cap 4.0s hit for 'Bleu De Chanel EDP', falling back to default (GPT-review-aggregate path owns the rating) |
| 01:42:20.579 | info | HTTP Request: POST https://api.anthropic.com/v1/messages 200 OK |
| 01:42:21.039 | warn | Comparison generation error: OpenAIEgressStoppedError |
| 01:42:21.039 | warn | PROS_POP_DIAGNOSTIC path=compare_from_text keys=['winner_index', 'error'] |
| 01:42:21.039 | warn | [content_safety] L3 moderation API failed (fail-open): openai dispatch stopped locally |
| 01:42:21.115 | warn | Failed to update behavior profile: column comparisons.category_used does not exist (42703) |

The new-account run logged no PRICE, PRICE_SUBSTAGE, GL_FALLBACK_TRACE, Shopify, woo or BH-adapter line for either product, not even with the window widened by one minute each side. The Chanel filter returned only the 3 lines shown above. This reads as the price stage not running a live search in this run, or not logging one. A cache hit or a different code path would both fit. That is a reading, not a code check.

## 4. The six switch names (names only; from describe-service variableNames on web)

| Name | On web |
|---|---|
| ENABLE_SERPER_KEY_STATE_MEMO | absent |
| ENABLE_UPSTASH_BOUNDED_TRANSPORT | absent |
| ENABLE_SPECS_NO_FABRICATION | absent |
| ENABLE_IMAGE_PIPELINE_V2 | absent |
| ENABLE_DATA_GUARDS_V2 | absent |
| ENABLE_SYNC_DB_OFFLOAD | absent |

## 5. What could not be found

- "Specs extraction" in the 21:19:40 to 21:20:15 window, also with one minute added each side: 0 lines. The only "Specs extraction" line found anywhere is in the old-consent run (01:36:24, OpenAIEgressStoppedError).
- "Redis GET error" in the 21:19 window, also with one minute added each side: 0 lines. (The new-account run does show Redis-side TimeoutErrors under other names: SPEND breaker fail-open and CIRCUIT anthropic breaker read failed.)
- The noon listing title, size and flanker for N70208068V. The log names only the offer id, the price and the seller (Luna).
- Any PRICE line for Bleu de Chanel in the new-account run (01:41:00 to 01:43:30): 0 lines.
- The value 91.780 BHD did not appear in either Bleu de Chanel window. The old-consent run shows the Serper pick CHANEL 50.76 BHD (size=None) and the Bahrain direct hit theperfumesclub.com 70.000 BHD. Where the 91.780 came from is not in these windows.
- The saved comparison rows (products[0].price.title, products[*].specs, products[1].price.reason) were outside this reader's tools (logs and describe-service only) and were not read.
