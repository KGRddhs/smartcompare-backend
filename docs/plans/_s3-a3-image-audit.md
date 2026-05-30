# Bundle E S3 A3 — image_url audit

**Filed:** 2026-05-30
**Owner:** be-images
**Status:** Pre-implementation audit per A3.1

## Where `image_url` lives today

```
app/models/product_schema.py:125      StructuredProduct.image_url: Optional[str] = None  (declared, not populated)
app/services/url_extraction_service.py:197   Amazon extractor → data["image_url"] (img#landingImage src/data-old-hires)
app/services/url_extraction_service.py:228   Noon JSON-LD → data["image_url"] (Product.image)
app/services/url_extraction_service.py:262   Generic JSON-LD → data["image_url"] (Product.image)
app/services/url_extraction_service.py:288   Generic fallback → data["image_url"] = meta.og_image
app/services/url_extraction_service.py:328   GPT URL-extraction prompt has "image_url" key
app/services/url_extraction_service.py:476   normalize_product_data() returns image_url
app/services/openai_service.py:182-183       "image_url" content type for GPT vision input (UNRELATED to product images)
app/services/serper_service.py:414-441       search_images(query, num_results=5) Tier 1 endpoint
```

**Where image_url is NOT today (the gap):**

- `app/services/structured_comparison_service.py` — Phase 1 fetches specs+price+reviews but never resolves an image_url for text-mode comparisons
- `app/services/response_builder.py:467` `build_comparison_response()` — emits products[*] dicts without image_url
- SSE stream — `specs` / `prices` / `reviews` event payloads carry no image_url
- `app/services/api_budget_service.py` — has `serper` counter (2200 lifetime) but no dedicated `serper_images` counter; image calls would starve price/spec budget

## Existing infrastructure to plumb (per design doc)

| Tier | Source | Status | Cost |
|------|--------|--------|------|
| 1.5 (piggyback) | url_extraction_service og:image / JSON-LD / Amazon img | EXISTS — wired into URL-mode only | FREE (already paid by curl_cffi) |
| 1 | serper_service.search_images(num_results=1) | EXISTS — never called from comparison pipeline | 1 Serper credit / call |
| 2 | firecrawl_service.scrape_page(url) | EXISTS — used by price tier 1.5a | 1 Firecrawl credit / call (existing breaker) |
| 2.5 | scrapedo_service.render_page(url) | EXISTS — used by price tier 1.5d | 1 Scrape.do credit / call (existing breaker) |
| 3 | openai_service GPT-4o-mini extraction from organic snippets | EXISTS as pattern, new prompt | ~$0.0005 / call |
| fallback | return None | NEW — frontend renders placeholder | $0 |

## Plumb plan (downstream tasks A3.2-A3.4)

1. **A3.2:** Create `app/services/image_service.py` with `get_product_image_url(product_name, *, region, page_scrape_image=None, organic_results=None) -> Optional[str]` (tier cascade orchestrator).
2. **A3.2:** Extend `app/services/api_budget_service.py` PROVIDER_CONFIGS with `serper_images` (default 500/day from env `SERPER_IMAGE_DAILY_BUDGET`). Add `try_consume_serper_image_credit(n) -> bool` (CHECK-AND-INCR atomic via redis_client.incrby).
3. **A3.3:** Plumb `get_product_image_url` into `structured_comparison_service.py:_fetch_product_data` Phase 1 (parallel with specs+price+reviews). Pass page-scrape image as Tier 1.5 piggyback when `_get_price` already retrieved it via `fetch_page_price`.
4. **A3.3:** Extend `response_builder.py:build_comparison_response` to include `image_url` in `overview.products[i]` AND on the top-level `products[i]` alias.
5. **A3.4:** Extend SSE `specs` event payload in `compare_from_text_streaming` to include `image_url` (no new event — piggyback specs since they fire together).
6. **A3.5:** Hand off PR to A2 peer-QA.

## Contract emitted to A2 / A4 (downstream FE lanes)

- Per-product key `image_url: string | null` at top level of each product entry in response payload (paths: `response.products[i].image_url`, `response.overview.products[i].image_url`)
- SSE `specs` event: `payload.products[i].image_url`
- **Tier provenance internal only** — per `feedback_no_backend_internals_in_reveals.md`, tier source is logged but never exposed to FE

## Memory-driven discipline carried forward

- `feedback_curl_test_vs_production_code.md` — grep BEFORE asserting "API needs fix"; for Serper Images, the existing `search_images` already sets Content-Type, so don't propose adding it
- `feedback_measure_before_optimize.md` — image pipeline cost target <$0.005/comparison; Tier 1.5 piggyback should cover most happy-path queries before paid tiers fire
- `feedback_nested_field_path_in_parsers.md` — verify `image_url` at TOP LEVEL of products entry (not nested in `metadata` or `media`); frontend parser will read `products[i].image_url`
- `project_bahrain_shopping_feed_gap.md` — Serper Images may have similar GCC coverage gap; default Serper Images call has NO `gl=` parameter so it returns universal results (safer than Shopping; no fallback retry needed initially)
- `project_upstash_redis_singlepoint_failure.md` — `try_consume_serper_image_credit` must fail-OPEN on Redis down (return True so image pipeline keeps trying Tier 1; existing `has_budget` pattern)

## Cost target

- Tier 1.5 piggyback: 0 incremental cost when Tier 1.5 already fired in price pipeline (most cold-cache comparisons)
- Tier 1 Serper Images: 1 credit (~$0.001) per product when piggyback empty; budget-capped at 500/day
- Tier 2/2.5: only fires when explicit URL provided — rare in text-mode (most comparisons)
- Tier 3 GPT: ~$0.0005 per product when all above failed
- **Worst case:** 2 products × ($0.001 Serper + $0.0005 GPT) = $0.003 incremental → well under $0.005/comparison cap

## Tests to author (A3.2 + A3.3)

1. `tests/test_image_service.py` — tier cascade unit tests (mocked external calls)
2. `tests/test_api_budget_service.py` — new `serper_images` counter cases
3. `tests/test_comparison_response_image_url.py` — response shape contract test (mocked orchestrator)

Target: ≥80% statement coverage on `app.services.image_service` + new `serper_images` paths in `app.services.api_budget_service`.
