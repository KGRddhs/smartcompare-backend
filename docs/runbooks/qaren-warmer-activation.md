# Qaren Price-Cache Warmer — Activation Runbook

The price-cache warmer (`scripts/cron_warm_price_cache.py`) is the **genuine-BH-share lever**. It scrapes genuine Bahrain (BHD) prices **off-clock** (raised `PRICE_RACE_TIMEOUT` + `FAN_OUT_BUDGET_SECONDS=35`) and writes them into the **shared** Upstash price cache (24h TTL). Live `/text/compare` requests run the real 15s clock and **read** the cache, so a warmed product is served **genuine + instant** — no timeout, no fall to `converted_usd`.

Authored by be-sourcing, Genuine-BH latency+warmer bundle WS4 (2026-06-15).

> The warmer ships **dormant** (`ENABLE_PRICE_CACHE_WARMER` unset → fail-closed skip). Activation is an **Ahmed / dispatcher decision** — the script registers nothing.

---

## What it warms

- The **gold-truth set** (`data/validation_gold_truth.json`), subset-selected by `WARMER_SUBSET` (`smoke20` default ≈ 20 queries, or `full` ≈ 200).
- PLUS the **structural warmer-only catalog** (`data/warmer_catalog.json`) — luxury fragrance / premium haircare / gadget pairs whose genuine BH price is **reachable but slow** to scrape (they blow the 15s live clock). This includes the bundle repro **Tom Ford Ombré Leather vs Tobacco Vanille**. The catalog is **always** folded in (regardless of subset), de-duped by query string, kept **separate** from gold so it never shifts the eval baseline (run `4aee8e88…`).

A `warmer:cursor` rotation cursor in Redis advances `MAX_QUERIES_PER_RUN` each run, so successive runs cover different products and the whole set stays warm over N runs.

---

## Activation steps (Railway)

1. **Register a Railway cron service** pointing at the worker, command:
   ```
   python -m scripts.cron_warm_price_cache
   ```
   Schedule: `0 */12 * * *` (every 12h — beats the 24h cache TTL so a warmed price never expires before the next run). For a smaller free-Serper budget, `0 6 * * *` (daily) is fine; pick the cadence that fits the plan (see budget below).

2. **Set the flag** on that cron service: `ENABLE_PRICE_CACHE_WARMER=true`.

3. **Confirm the shared-cache env** is identical to the live web service: `UPSTASH_REDIS_URL` + `UPSTASH_REDIS_TOKEN` (the warmer MUST write to the SAME Redis the live service reads, or warming is a no-op). Same `SERPER_API_KEY`, `OPENAI_API_KEY`, `FIRECRAWL_API_KEY`, `SCRAPEDO_API_TOKEN` as live.

4. **Size the run** to the Serper plan (below): `MAX_QUERIES_PER_RUN` + `WARMER_SUBSET`.

---

## Off-clock budget (already exported by the script — no env needed)

The script sets these BEFORE importing the comparison/scraper services (so they take effect):

| Var | Warmer value | Live value | Why |
|---|---|---|---|
| `PRICE_RACE_TIMEOUT` | `60` | `15` | let the slow genuine curl/JSON-LD scrape finish |
| `STREAM_HARD_CAP_SECONDS` | `150` | `30` | no request-cap on an off-clock run |
| `FAN_OUT_BUDGET_SECONDS` | `35` | `12` | let the curl+render wave finish a luxury SPA |
| `FIRECRAWL_TIMEOUT` | `45` (setdefault) | `30` | render budget for a slow SPA |
| `SCRAPEDO_TIMEOUT` | `35` (setdefault) | `15` | residential-proxy render budget |

Override any via `WARMER_*` (e.g. `WARMER_FAN_OUT_BUDGET`, `WARMER_PRICE_RACE_TIMEOUT`). The live web service is **unaffected** — these are warmer-process-only.

> **Render-wall caveat (WS3 finding):** Cloudflare-protected BH retailers (**bolo.bh, boutiqaat, sephora.bh**) return a "you have been blocked" interstitial regardless of budget — a 35s budget does **not** defeat a bot-wall. Their genuine prices are **STRUCTURAL gaps**, not a code gap; the warmer will leave those products on `converted_usd`/`estimated`. Genuine wins come from the **curl-extractable** BH sources (alhajisbahrain.com, bahrain.ounass.com, lulu /en-bh/, sharafdg, microless, …).

---

## Serper budget sizing (the real constraint)

Each query warms **2 products** at ≈ **10–30 Serper credits** (cold escalation-heavy luxury is at the high end). `MAX_QUERIES_PER_RUN` (default **25**) HARD-bounds the spend per run (~250–750 credits).

Free serper.dev keys are a **finite ~2,500 one-time** allotment, **shared with live traffic**. So:

- **Free key, sustainable:** `WARMER_SUBSET=smoke20` (≈20 gold) + 10 catalog = ~30 queries, `MAX_QUERIES_PER_RUN=25`, **daily** ≈ 250–750 credits/run → exhausts a fresh free key in days if run alongside live. Practical free-tier cadence: a **manual / pre-eval** warm, not an always-on daily.
- **Continuous full-catalog warming needs PAID Serper.** `WARMER_SUBSET=full` (200) + catalog at `0 */12 * * *` is ~600–1,000 credits/run × 2/day — only viable on a paid Serper plan. **This is an Ahmed business decision, not a code blocker.** The warmer scales cleanly with whatever plan is set — raise `MAX_QUERIES_PER_RUN` once the budget allows.

Monitor burn at `/admin/costs` (Serper bucket) — the warmer shares the live counter. Rotation playbook for a depleted key: CLAUDE.md § External APIs / Serper.

---

## Verify a warm landed (no prod-cache write from a dispatcher session)

Prod-cache writes are classifier-blocked for the dispatcher — the warm runs on Railway. To CHECK a warmed pair is genuine + cached (read-only):

```bash
# cache-READ genuine-share probe (reads the shared cache; writes nothing)
python .qa-bias-rerun/_genuine_share_probe.py
```

Expect the Tom Ford pair (and the other catalog pairs) to read GENUINE BHD from cache on a normal 15s-clock request after a warm run. A cache MISS for a warmed pair means the warm didn't land (check Serper budget / breaker state / the WS3 render-wall caveat).

> **Eval caveat:** `eval_runner` uses `nocache=true` (it measures COLD scraping), so it will **not** reflect the warmer's cached genuine-share. Use the cache-read probe above to measure the 70% dial, not the eval.

---

## Rollback

Unset `ENABLE_PRICE_CACHE_WARMER` (or set to anything other than a truthy value) → the next run fail-closed skips. Cached entries expire on their own 24h TTL. No code change needed.
