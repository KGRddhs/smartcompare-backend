# Scraper bake-off — measured, not researched (2026-08-25)

Nine real product pages from `data/bh_gcc_sources.json`, fetched once each by every contender, with
**every contender's HTML judged by this repo's own `extract_price_from_html` / `extract_jsonld_price`.**
The question was "did we get a PRICE", not "did we get HTML". Zero Serper; one attempt per
(contender, target); no retries.

This exists because prior desk research reached a conclusion and desk research is not evidence.

## Scoreboard

| Contender | Priced | Fetched | Cost / speed |
|---|---|---|---|
| **curl_cffi** (incumbent) | **4 / 9** | 7 / 9 | $0, median 0.70s |
| Scrape.do | 4 / 9 | 6 / 9 | 35 credits, 9–50× slower |
| crawl4ai 0.9.2 default | 4 / 9 | 7 / 9 | full browser tier |
| crawl4ai 0.9.2 undetected (patchright) | 4 / 9 | 7 / 9 | **byte-identical to default** |
| Firecrawl (as wired) | **0 / 9** | 5 / 9 | 6 credits burned |
| Zyte | 0 / 10 | 0 / 10 | account suspended (403) |

## Two findings that change decisions

### 1. `curl_cffi` read sephora.me — the site Zyte was procured for → #93

HTTP 200, 2.58 MB, **zero `_abck` / AkamaiGHost markers**, JSON-LD `priceCurrency BHD, price 77,
InStock` — the identical **77.000 BHD** Zyte was feasibility-proven on in June — in **1.39s, free**.
On the same target in the same run, plain Playwright, crawl4ai default, and crawl4ai+patchright
**all** returned 403 / 331 bytes.

**Not actionable yet: one sample, one non-GCC IP, stochastic anti-bot.** The repo's own lesson runs
both ways — 9 of 11 "failures" in the Phase-1 promotion were one unlucky sample; one lucky sample is
not a capability. #93 specifies 20+ samples over 24h from Railway egress, judged through the
production adapter.

### 2. Firecrawl's 0/9 is a bug in THIS repo → #92 (P1)

`app/services/firecrawl_service.py` hardcodes `formats: ["html"]` — Firecrawl's *cleaned* HTML.
Every successful fetch returned **0 `<script>` tags and 0 `ld+json` blocks**. The extractor reads
`ld+json`. So the integration **cannot return a price on any page, ever, by construction**, while
billing 1 credit per page.

Controlled probe, same URL, `formats: ["rawHtml"]`: 615 KB, 158 scripts, 5 ld+json,
**1.400 BHD — and 5.4× faster** (2.49s vs 13.48s).

Firecrawl was also the least reliable fetcher on the panel: HTTP 500 on **both** controls curl
cracks free (bolo, boutiqaat), 408 on sephora and eros, an empty 200 on ubuy, and **HTTP 200 +
billed on a real 404** — it does not surface upstream 404s, so a dead registry row looks like a
successful render.

## Verdicts on the tools that were recommended

**crawl4ai — rejected on measurement.** Its patchright "undetected" mode — the specific reason it is
recommended for hard sites — was **byte-for-byte identical to default on all nine targets** and
contributed exactly zero, including both walled ones. It beat plain Playwright on 1 of 9 (ubuy), and
the entire cause was its default User-Agent (Playwright advertises `HeadlessChrome`). Copying two
lines of UA + `sec-ch-ua` into bare Playwright reproduced the win **and returned the correct 16.0
BHD**, where crawl4ai under-rendered the page into a confident-wrong "6.02 BHD" — the exact failure
class this codebase exists to prevent. Adopting it buys a UA default for ~190 MB of dependency and a
measured wrong-price regression.

**Scrape.do — a narrow keeper.** One genuine win in nine: `eros.ae`, an HTTP 491 Link11 WAF that
blocks curl, Playwright and crawl4ai alike — 8.6s, 5 credits, AED 3898.99. The other three duplicate
free curl results at 9–50× the latency, and two of those (19.8s, 23.0s) **exceed the 15s live
request clock**, so production could not have used them on-clock anyway. 26 of its 35 credits went
to duplicating free results. It belongs behind a narrow "curl returned a WAF block" trigger, not in
a general fan-out.

**Zyte — unmeasurable.** All calls returned HTTP 403 in ~1s; the body reads `"Account Suspended…
If you have reached your spending limit, increasing your spending limit will immediately lift your
account suspension."` The key authenticates; the account is suspended. Sequence any revival **after**
#93 — if curl holds sephora, that spend solves a solved problem.

## Registry data is wrong on 4 of the 9 rows → #94

- `matalanme.com` and `xcite.com` are flagged **`render-only`** but plain curl reads them in under a
  second (1.400 BHD / 229.900 KWD). They have been escalating to the **paid** render wave for pages
  that are free. The other 14 `render-only` rows deserve the same check.
- `bfab.com`'s `sample_url` 308-redirects to a category listing, not a PDP.
- `letoile.ae`'s `sample_url` is a dead 404.

## Two smaller defects surfaced

- **bolo.bh**: curl fetches it fine (200, correct PDP title) but its JSON-LD Offer publishes
  `price "0.00"` with the real value in a non-schema JS blob. The extractor correctly refuses 0.00.
  That is an adapter gap, not a scraping gap.
- **xcite.com**: the PDP renders `itemprop=price 229.9` + `priceCurrency KWD`, and
  `_extract_microdata_price` returns it in isolation, but `extract_price_from_html` returns `None`
  because `_page_identity_ok` rejects under the `electronics` category across four query-name
  variants. This zeroes every contender equally — an over-rejection worth its own look.

## Bottom line

The community advice does not survive measurement. The incumbent free path ties or beats every paid
and open-source contender, including on the one target the render tier was bought for. **The
registry needs a cleanup pass more than the stack needs a vendor**, and Firecrawl's score is
self-inflicted by a one-word bug that should be fixed before any buy/keep decision is made about it.
