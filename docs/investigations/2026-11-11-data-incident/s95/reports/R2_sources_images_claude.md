# R2 - Lawful Gulf data sources, picture checks, structured extraction with Claude

S95-FIX, read-only research agent, 2026-11-14. Code cited at 731bcddf (plain export). Web pages fetched 2026-11-14. E = ESTABLISHED (read in code or docs), L = LIKELY (inference). Nothing here says a production problem is fixed. Legal points are a technical reading of public terms, not legal advice: the owner (and counsel) make the terms rulings.

## 0. How this ties to the 2026-11-13 "Tyger" failure

- E: the Blake-poem picture came from image Tier 1. It sends the bare typed name to Serper Images with `num_results=1` and returns `images[0].imageUrl` after only a URL-shape and deny-host check (app/services/image_service.py:283-311, :57-68). It runs no relevance or product-photo test.
- E: the page-image override (the image from the accepted offer's page) runs only when a price was accepted: `result["price"].get("image_url")` (app/services/structured_comparison_service.py:6406-6429). "Tyger" had zero price candidates, so the Serper picture stood.
- E: with ENABLE_IMAGE_PIPELINE_V2 on, a page image must be https, raster, public, not deny-listed, and on the page's own host, a platform CDN (`cdn.shopify.com`, `cdn.salla.sa`, `cdn.salla.network`, `media.zid.store`) or a brand domain (app/services/jsonld_widen.py:79, :156-193). With it off, any http(s) URL passes (:423-429). The flag is not in the brief's list, so both branches are possible.
- L: noon serves images from its own CDN, a host that is not a noon.com subdomain. If V2 is on, a noon JSON-LD image would be refused, which could explain the grey placeholder on the 29.320 BHD noon card. Check this against a log line.

## (a) Lawful sources of fragrance data and prices for the Gulf

| Source | What it gives | Terms / robots position | Cost |
|---|---|---|---|
| schema.org Product/Offer JSON-LD on the retailer's product page | name, brand, image, gtin8/12/13/14, sku; Offer price, priceCurrency, availability, url. Size usually only in the name or variant | E: Google's merchant-listing guide nests the Offer inside the Product via `offers`, wants one offer per landing page for matching, and says the image should link to the product's main image. Fetching it is ordinary crawling, so robots.txt (RFC 9309) and the site's terms apply per host | One GET per page; free |
| WooCommerce Store API `/wp-json/wc/store/v1/products` | name, prices (with currency minor unit), images, sku, attributes, stock | E: WooCommerce documents it as unauthenticated, exposing no sensitive or customer data, and stable since WC 6.4. `per_page` max 100. Already used: app/services/woocommerce_service.py:6-8, :85, gated by the live robots check at :342-359 | Free |
| Shopify `/products/{handle}.js` (Ajax API) | variants (max 250), prices in presentment currency, images, barcode if set | E: documented by Shopify for Shopify-hosted themes; no hard rate limit, subject to abuse prevention. E: Shopify's docs do not document `/products.json`. A community answer says it is not meant to replace the Admin APIs. Prefer the documented `.js` or the page JSON-LD | Free |
| Salla (KSA; some GCC stores) | full catalogue through the Merchant API (`api.salla.dev/admin/v2`) | E: needs a Partner Portal app and each merchant's OAuth consent (token 14 days, refreshable). There is no public cross-store catalogue API. Public store pages carry JSON-LD (images on `cdn.salla.sa`, already allow-listed) | Free API; needs merchant opt-in |
| Zid (KSA) | products, stock, reviews through the Merchant API | E: partner account, app credentials, OAuth per store, app review for public apps. There is no public cross-store API | Free; merchant opt-in |
| Amazon.ae / Amazon.sa: Creators API (replaces PA-API 5) | ASIN, title, images, offers/price, browse nodes, detail URL | E: PA-API 5 is deprecated in favour of the Creators API. Amazon gives different dates (30 April and 15 May 2026), both past. AE and SA are supported marketplaces, each needing its own Associates account. Access needs at least 10 qualifying sales in the past 30 days. Prices may be shown only from the API or Amazon-served links. L (third-party summary of policy): a date/time stamp must sit beside the price | Free; it gates on sales, so a new app cannot start with it |
| noon | no affiliate product feed or API found. noon's API Platform is for sellers | L: no lawful bulk feed for a comparison site. Its product pages carry JSON-LD (today's BH adapter reads it: "page_scrape_jsonld" in the quoted log). Robots and terms must be read per host | n/a |
| ArabClicks (GCC affiliate network: UAE, KSA, KW, BH, OM) | affiliate links; no public product-feed documentation found | L: ask the network whether advertiser feeds are available to publishers | Commission model |
| Admitad (Mitgo) | advertiser product feeds (XML, CSV, Google Merchant or YML formats) for programmes that join | E: feeds come per advertiser programme after approval. L: which GCC beauty retailers publish feeds is unknown; check in the dashboard | Free to publishers |
| Brand feeds / brand sites | official images, notes, sizes, GTIN; seldom Gulf prices | Direct agreement, or JSON-LD on the brand site (brand domains already allowed for images, jsonld_widen.py:164) | Free or by agreement |
| Google Shopping results through a SERP API (Serper today) | titles, prices, merchant, thumbnail, region by `gl` | E: Serper's terms call it B2B, "web-scraped data", with no Google affiliation, and forbid hiding the source. Google's terms forbid automated access. Google sued SerpApi in December 2025 (blog.google); reports on the case's status disagree. L: a legal risk sits upstream of Serper; it is not removed by Serper's terms | About USD 0.3-1 per 1k queries (Serper pricing page, not re-read) |
| RFC 9309 robots rules | n/a | E: the standard. A cached robots.txt should not be used for more than 24 h; parsers must handle at least 500 KiB. Already implemented (app/services/robots_registry.py:1-30: 24 h re-read, named agent, redirects followed by hand, SSRF checks) | n/a |

**Recommendation (a).** Display a price only when it came from a first-party offer page (JSON-LD, WooCommerce Store API or Shopify `.js`) on a merchant whose robots.txt allows the fetch. Show the source link and a "checked at" time. Use Serper or Google results only to **discover** merchant URLs, never as the displayed price or picture (this is a policy choice for the owner). Apply for Admitad and ArabClicks feeds and for Amazon AE/SA Creators API access, which opens only after 10 sales in 30 days. Salla and Zid catalogues need merchant opt-in, so they are a partnership track, not a crawl.

## (b) Checking that a picture belongs to the product

| Layer | Method | Cost / latency | Licence |
|---|---|---|---|
| 1 | **Same-page rule**: take the image only from the accepted offer's own JSON-LD or og:image (exists: structured_comparison_service.py:6406-6429) | free, 0 ms | n/a |
| 2 | **Cheap guards** before any image is shown: https and raster type; a host allow list (exists, jsonld_widen.py:79/156-193; add each vetted retailer's own CDN); a deny list (fimgs.net already); aspect 0.5-2.0; minimum 200 px; reject when the Serper image's title or source page lacks the brand or any name token; never query Serper Images with a bare name (send "brand + name + perfume") | free, under 5 ms after a HEAD or range GET | n/a |
| 3 | **Perceptual hash reuse**: store the pHash/dHash of each verified image per canonical product. A new candidate within Hamming distance ~8 of a verified hash is accepted without a model call | about 5-20 ms CPU per image | imagehash: BSD-2-Clause (GitHub API). Meta PDQ (facebook/ThreatExchange): GitHub reports NOASSERTION, so read the repo's licence file |
| 4 | **Claude vision yes/no** (Haiku 5.5): "Is this a photo of <brand> <name> <conc> bottle or box? Answer one word." Strict schema `{match: yes|no|unsure}` | E: image tokens = ceil(w/28) x ceil(h/28); a 448x448 image = 256 tokens; 1000x1000 = 1,296. At USD 0.10 / 0.50 per MTok, a ~450-token call costs about USD 0.00005; at 1000 px about USD 0.00015. L: about 0.5-1.5 s with thinking low or off | Anthropic API terms. E: the vision role is already wired to claude-haiku-5-5 (app/services/model_config.py:219) with ENABLE_ANTHROPIC_VISION OFF |
| alt | CLIP / SigLIP text-image similarity, self-hosted | L: about 100-300 ms per image on CPU for ViT-B; adds PyTorch (hundreds of MB) to the web image; similarity is weak at telling EDT from EDP or flankers apart. It catches "poem page against a perfume bottle" well | openai/CLIP: MIT. OpenCLIP code: MIT-style licence text (GitHub reports NOASSERTION; weights carry their training-set terms). SigLIP (google-research/big_vision): Apache-2.0 |

**Recommendation (b), layered.** Layer 1, then 2, then 3. Only an image that passes 1-2 but has no hash match goes to layer 4, and only when the flag is on and the time budget allows; otherwise show the placeholder. Never show a Tier 1 image that skipped layers 2-4. Expected spend is under USD 0.0002 per product, and nothing for products already verified. CLIP or SigLIP is a fallback only if Claude vision stays off; its infrastructure cost outweighs the API price.

## (c) Structured extraction with Claude (official docs, fetched 2026-11-14)

**Models and prices (E, pricing page and models overview).**

| Model id | Input | Output | 5 m cache write | 1 h write | Cache read | Batch in/out |
|---|---|---|---|---|---|---|
| `claude-haiku-5-5` (prompts up to 100k tokens) | $0.10/MTok | $0.50 | $0.125 | $0.20 | $0.01 | $0.05 / $0.25 |
| `claude-haiku-5-5` (prompts over 100k) | $0.50 | $2.50 | $0.625 | $1.00 | $0.05 | $0.25 / $1.25 |
| `claude-sonnet-5-5` | $2.00 | $10.00 | $2.50 | $4.00 | $0.10 (0.05x) | 50 % off |

E: Haiku 5.5 is "Fastest" and meant for "classification, extraction, and routing"; Sonnet 5.5 is "Fast". Both have a 1M context and 128K output. The code's price table matches (app/services/llm_pricing.py:38-48, as of 2026-10-22).

**Structured outputs / strict tool use (E).** `output_config.format` takes a JSON schema; `strict: true` on a tool guarantees schema-valid input. The first use of a schema adds grammar-compile latency; the compiled grammar is cached 24 h from last use. Limits: 20 strict tools, 24 optional parameters, 16 union-type parameters per request. Enum casing is not guaranteed, so compare case-insensitively. `stop_reason: refusal` or `max_tokens` can break the schema. **Incompatible with citations**: the API returns 400 when citations are enabled with `output_config.format`. It works with Batches (50 % off) and with streaming.

**Web search tool (E).** Supported on Haiku 5.5, Sonnet 5.5, Opus 5.5 and others. Versions: `web_search_20250305` (basic), `_20260209` (dynamic filtering through code execution, which is free with it), `_20260318` (adds `response_inclusion`). Claude decides when to search; the API runs the searches, possibly several per request, and the answer carries citations (always on: url, title, `cited_text` of 150 characters or fewer, which are not billed). Parameters: `max_uses` (failed searches count), `allowed_domains` **or** `blocked_domains`, never both (400 if both; bare domains, optional path), `user_location` {city, region, country (ISO alpha-2; an unsupported code is a 400), timezone}. Price: **USD 10 per 1,000 searches** plus result tokens as input, in this turn and every later turn. An admin can disable it in the Console, and a request then fails with 400. Dynamic filtering is not ZDR-eligible.
L: since citations are always on, check with a test call whether web search plus `output_config.format` in one request returns a 400. A safe design is two calls: search, then extract, or a strict "record" tool.

**Web fetch tool (E).** No charge beyond tokens. It fetches only URLs already in the conversation (user text, tool results, earlier search or fetch results). It does not run JavaScript. It returns PDFs as documents. `max_content_tokens` truncates. Results may come from Anthropic's cache (`use_cache: false` on `_20260309` or later). Fetches are refused (`url_not_allowed`) by domain rules, org settings or **robots.txt**. Domain lists work as for search. The docs warn about exfiltration when untrusted input meets sensitive data.

**Prompt caching (E).** The minimum cacheable prefix is 512 tokens on Haiku 5.5 and Sonnet 5.5. TTL is 5 min by default (a write costs 1.25x) or `ttl: "1h"` (2x). A read costs 0.1x (Haiku), 0.05x (Sonnet 5.5), and a read refreshes the TTL. Up to 4 breakpoints; automatic caching is available with a top-level `cache_control`. Changing `output_config.format` invalidates the cache.

**Message Batches (E).** 50 % off all tokens; most batches finish in under 1 h, and a batch expires at 24 h (expired requests are not billed). Up to 100,000 requests or 256 MB per batch; results kept 29 days. Server tools (web search, web fetch) and structured outputs work inside batches. L: whether the 50 % applies to the USD 10/1k search fee is not stated; assume it does not.

**Latency for a 4-8 s budget (E, reduce-latency page and skill notes).** Pick Haiku, keep prompts and outputs short, set a tight `max_tokens`, stream, and cache the static system prompt. E: Haiku 5.5 thinks by default (adaptive, effort `medium`). Set `output_config.effort: "low"`, or disable thinking (allowed at effort high or below), for extraction. Warm each schema once (24 h grammar cache). L: a Haiku extraction over about 3k input tokens and 300 output tokens should finish in about 1-2 s. Each web search adds roughly 1-3 s and a fetch more (L, no official figure), so a live call with 2 or more searches risks the budget. The current serper_shopping step alone already takes about 10 s (quoted log).

### Fit and expected cost per product

| Use | Fit | Design | Expected cost per product (L, from the official prices) |
|---|---|---|---|
| (1) Live comparison path | Haiku 5.5 + structured output **over pages the backend already fetched** (JSON-LD or Woo/Shopify JSON trimmed to about 2-4k tokens), effort low, cached system prompt; plus the vision yes/no for unverified images | no server web search on the live path; at most one `web_fetch` of a known merchant URL if time allows | about USD 0.0005-0.001 extraction + about 0.0001 image = **about USD 0.001**. One web search would add USD 0.01 plus tokens and seconds |
| (2) Offline catalog builder | Batches + web search (`allowed_domains` = the vetted merchant list from kb_merchants, which keeps out banned sites) + web fetch, then a second strict-schema extraction call; Haiku for bulk, Sonnet 5.5 for hard or ambiguous names ("Tyger" -> Bvlgari Tygar) | 1-3 searches, 1-2 fetches, about 15-25k input tokens, about 1k output | Haiku: about USD 0.001 tokens (batch) + USD 0.01-0.03 searches = **about USD 0.012-0.032**. Sonnet 5.5: about USD 0.02-0.03 tokens (batch) + searches = **about USD 0.03-0.06**. For 5,000 products: about USD 60-160 (Haiku) or 150-300 (Sonnet) |

The search fee dominates offline spend, so cut it: search once per canonical product, then fetch known URLs (fetch is free beyond tokens), and re-fetch prices on a schedule without a search.

## Cautions

1. The Amazon Creators API sales gate (10 in 30 days) blocks a new app; the PA-API cut-off dates have passed.
2. The Serper / Google Shopping licence chain is unsettled (Google v SerpApi); showing scraped Shopping prices is the owner's legal call.
3. A web search with `allowed_domains` ignores sites outside the list, and `blocked_domains` cannot be combined with it, so keep banned sites out of the allow list.
4. Citations and `output_config.format` conflict; test web search plus structured output before relying on one call.
5. `user_location.country` "BH" support is not confirmed in the docs (an unsupported code returns 400); test it.
6. Dynamic filtering (web_search/fetch `_20260209`+) is not ZDR-eligible.
7. The noon image host may fail the V2 image allow list (L); verify before adding hosts.

## Sources
- https://platform.claude.com/docs/en/about-claude/pricing.md
- https://platform.claude.com/docs/en/about-claude/models/overview.md
- https://platform.claude.com/docs/en/build-with-claude/structured-outputs.md
- https://platform.claude.com/docs/en/agents-and-tools/tool-use/web-search-tool.md
- https://platform.claude.com/docs/en/agents-and-tools/tool-use/web-fetch-tool.md
- https://platform.claude.com/docs/en/build-with-claude/prompt-caching.md
- https://platform.claude.com/docs/en/build-with-claude/batch-processing.md
- https://platform.claude.com/docs/en/build-with-claude/vision.md
- https://platform.claude.com/docs/en/test-and-evaluate/strengthen-guardrails/reduce-latency.md
- https://developers.google.com/search/docs/appearance/structured-data/merchant-listing
- https://developer.woocommerce.com/docs/apis/store-api/
- https://shopify.dev/docs/api/ajax/reference/product
- https://community.shopify.com/c/technical-q-a/how-to-paginate-or-get-a-list-of-all-products-using-domain-com/td-p/1490029
- https://docs.salla.dev ; https://docs.zid.sa/ ; https://help-partner.zid.sa/en/articles/8716995-integration-and-development-cycle
- https://affiliate-program.amazon.com/creatorsapi/docs/en-us/paapiv5-deprecation ; .../locale-reference/united-arab-emirates ; .../locale-reference/saudi-arabia ; .../concepts/best-programming-practices ; https://webservices.amazon.com/paapi5/documentation/
- https://support.noon.partners/portal/en/kb/articles/noon-api-platform
- https://arabclicks.com/about/ ; https://campaignme.com/arabclicks-performance-based-affiliate-marketing-network-launches-in-gcc/
- https://support.mitgo.com/hc/en-us/articles/360019922878
- https://serper.dev/terms ; https://blog.google/innovation-and-ai/technology/safety-security/serpapi-lawsuit/
- https://datatracker.ietf.org/doc/html/rfc9309 ; https://developers.google.com/search/reference/robots_txt
- https://api.github.com/repos/openai/CLIP (MIT) ; .../mlfoundations/open_clip (LICENSE file MIT-style) ; .../google-research/big_vision (Apache-2.0) ; .../JohannesBuchner/imagehash (BSD-2-Clause) ; .../facebook/ThreatExchange (NOASSERTION)
