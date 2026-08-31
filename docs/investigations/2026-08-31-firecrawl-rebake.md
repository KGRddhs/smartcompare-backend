# #92 Firecrawl rawHtml LIVE re-bake — 2026-08-31

**VERDICT: LIVE RUN CONFIRMS the fixture validation of `ENABLE_FIRECRAWL_RAW_HTML` (default ON in prod).**
Every page where Firecrawl actually delivered the PDP priced from **rawHtml** through the repo's own
`extract_price_from_html` (5/5), and the **cleaned `html` format priced 0 of 10** fetched pages —
0 `<script>` tags and 0 `ld+json` blocks survived cleaning on all 10, exactly as the n=92 fixture
replay measured (rawHtml 86/92 vs cleaned 11/92, zero surviving ld+json). No target contradicts the
fixtures. The upstream-status short-circuit (the second half of #92) was also live-validated: ubuy's
upstream 403 is surfaced in `data.metadata.statusCode` and the shipped code correctly treats it as a
miss instead of handing a 1.4 KB "Blocked" shell to the extractor.

## Credits

| | |
|---|---|
| Before (GET /v1/team/credit-usage) | **2291** remaining |
| After | **2282** remaining |
| **Spent** | **9 credits** (hard cap was 15) |
| Attempts | 12 scrape calls (9 original bake-off targets + 3 #94-corrected retries); 10 returned FC HTTP 200, 2 returned FC 500 (unbilled). Endpoint delta says 9 of the 10 200s billed. |

## How targets were chosen

The definitive 9-target list was recovered **verbatim** from the original 2026-08-25 bake-off harness
(`bakeoff_fetch.py` TARGETS + `bakeoff_judge.py` NAMES, session-35022b5a scratchpad) — same URLs, same
currencies, same product names, same judge cascade (slug name -> page-derived name ->
brand-agnostic `extract_jsonld_price`). Three #94-corrected URLs were added inside budget because the
original bfab/letoile/ubuy sample URLs are known-broken (category 308 / dead slug / truncated paste).

## Request shape

Mirrors shipped `app/services/firecrawl_service.py`: `POST https://api.firecrawl.dev/v1/scrape`,
body `{"url", "formats", "waitFor": 5000}`, Bearer auth. Two recorded deviations:
`formats: ["rawHtml","html"]` in ONE call so the cleaned control rides the same billed scrape (never
two credits per target), and client timeout 45s = the repo's documented off-clock
`FIRECRAWL_TIMEOUT` the bake-off used (live default 30s; real latencies recorded). Judging used
`extract_price_from_html` under BOTH `ENABLE_EXACT_PRICE_GATE` modes; results below are the shipped
gate-ON numbers (gate-OFF changed no price outcome, only the matched-name rung on xcite/eros).

## Results — 9 original bake-off targets

| Target | FC HTTP | Upstream | rawHtml price | cleaned price | Rung | Verdict vs fixtures |
|---|---|---|---|---|---|---|
| matalanme (sarong) | 200 | 200 | **1.400 BHD** | — | ld+json (page_scrape) | **CONFIRM** — the exact URL+price of the #92 controlled probe |
| sephora (Oud Wood P1641048) | 200 | 200 | **77.000 BHD** | — | ld+json | **CONFIRM** — live Firecrawl now cracks Akamai (bake-off: 408); the exact 77 BHD Zyte was procured for |
| eros (Galaxy S26 Ultra) | 200 | 200 | **4856.19 AED** | — | ld+json/microdata | **CONFIRM** — bake-off: 408; now renders through the Link11 wall |
| xcite (iPhone 16 128GB) | 200 | 200 | **229.9 KWD** | — | microdata/ld+json | **CONFIRM** — and the bake-off's `_page_identity_ok` electronics over-rejection no longer fires (fixed by the merged extractor waves) |
| ubuy (truncated URL) | 200 | **403** | — (short-circuit) | — | n/a | **CONFIRM #92 half 2** — upstream 403 surfaced in metadata; shipped code returns miss on the billed error page |
| letoile (dead slug /p/5-1-30...) | 200 | 200 | — | — | n/a | ANOMALY (below) — Firecrawl egress is redirected to the letoile.ae HOMEPAGE (`metadata.url = https://letoile.ae/`); extractor rightly refuses |
| bfab (girls-gingham-dress) | 200 | 200 | — | — | n/a | Reproduces #94: 308 -> `/bh_en/kids` category listing (`metadata.url` proves it); no Product offer to price |
| bolo (Kensington K33272WW) | **500** | — | n/a | n/a | n/a | Reproduces bake-off: "All scraping engines failed"; unbilled. Free curl cracks this page |
| boutiqaat (Ghuyoum Alqassar) | **500** | — | n/a | n/a | n/a | Reproduces bake-off: same 500; unbilled. Free curl cracks this page |

## Results — #94-corrected retries

| Target | FC HTTP | Upstream | rawHtml price | cleaned price | Verdict |
|---|---|---|---|---|---|
| bfab_fix (navy-collegiate-cap) | 200 | 200 | **4.900 BHD** | — | **CONFIRM** — matches the 2026-08-30 curl probe exactly |
| letoile_fix (Lancome La Vie Est Belle PDP) | 200 | 200 | — | — | ANOMALY (below) — same homepage redirect as the dead slug; curl-from-Bahrain got the real PDP at 670 AED on 2026-08-30 |
| ubuy_fix (full product URL) | 200 | **403** | — (short-circuit) | — | ubuy walls Firecrawl egress outright ("Blocked" shell, windows-1252); short-circuit correct |

## Structural check (the cleaning contract)

Every fetched page, rawHtml vs cleaned: script tags 57-360 vs **0**; ld+json blocks 1-4 vs **0**;
microdata/og price markers present on xcite/eros rawHtml vs **0** cleaned. The fixture claim "zero
ld+json survives Firecrawl cleaning" held 10/10 live.

## Anomalies / findings to carry forward

1. **letoile.ae redirects Firecrawl's egress IP to the homepage for BOTH a dead slug and a valid
   PDP** (`metadata.url = https://letoile.ae/`, title "LETOILE - Online Beauty Store in UAE"), while
   Bahrain-residential curl gets the real PDP (670 AED, 5 ld+json, #94 probe). So the bake-off's
   "billed 200 on a dead URL" behaviour persists in a new shape the `statusCode >= 400`
   short-circuit CANNOT catch — it is genuinely a 200. This is exactly the M9
   `ENABLE_NOT_A_PDP_FILTER` territory (homepage/search-redirect classification), and one more
   datapoint for the standing "re-measure from Railway egress before trusting reachability" rule.
2. **ubuy.com.bh hard-walls Firecrawl egress** (upstream 403 "Blocked" shell) — bake-off-era it was
   an empty 200. The #92 short-circuit turns these into clean misses, but Firecrawl still bills the
   render; ubuy via Firecrawl is a pay-to-lose row.
3. **bolo.bh + boutiqaat.com still 500 inside Firecrawl** ("All scraping engines failed") — the
   bake-off reliability finding reproduces exactly on both control pages that free curl cracks.
4. **eros priced 4856.19 AED vs Scrape.do's 3898.99 six days earlier** — live price/variant drift,
   recorded as an observation only (extraction rung and currency are correct).
5. Billing: 10 FC-200 responses but endpoint delta = 9 credits — one 200 did not bill (both ubuy
   calls returned byte-identical 1370-byte bodies; likely a Firecrawl-side cache hit). The
   credit-usage endpoint, not the response count, is the authoritative spend number.

## Files

Raw artifacts live in the 2026-08-31 session scratchpad (`…/scratchpad/m11/firecrawl-rebake/`),
NOT committed (full HTML payloads). This report is the durable record; regenerate with the two
scripts below against any Firecrawl key.

- `manifest.json` — per-call FC status, upstream status, sizes, latencies, credit snapshots
- `credits_before.json` / `credits_after.json` — raw credit-usage responses
- `raw/<target>.json` — full Firecrawl responses (rawHtml + cleaned html payloads), 12 files
- `judged.json` — per-target x {rawHtml, cleaned} x {gateON, gateOFF} extractor results
- `fetch_rebake.py` / `judge_rebake.py` — the two phases (fetch = api.firecrawl.dev only; judge = zero network)
