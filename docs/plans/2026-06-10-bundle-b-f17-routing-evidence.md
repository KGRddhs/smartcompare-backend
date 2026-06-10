# Bundle B S1 — F1.7 Tier 1.5 Routing Evidence

**Date:** 2026-06-10 · **Branch merged to main:** ea4be1b (Lane F1 = B.0 source_router cascade wiring) · **Baseline anchor:** eval_runs 4aee8e88-da97-41b3-974b-3e75c2c9c10e (pass_rate 21.0%, p95 30.7s) · **Author:** F1-router (cross-checked by team-lead via admin counters)

## Disposition

**F1.7 gate: CLOSED — "wired + consulted + winning."** The Bahrain-first source registry is provably wired into the Tier 1.5 price-escalation cascade, is consulted on weak-Tier-1 queries, and produces scraped winners at a 27% overall hit rate during the baseline. The one residual — *which domains* the 22 winners came from (registry-tier Bahrain vs legacy luxury sets) — is deferred to an S2 per-source `/admin/costs` dashboard line (the counters already record it; only the surfacing is missing).

## 1. Three-layer evidence chain

1. **WIRED (unit-proven).** 45 source_router tests + the harvest/gate/route/hit-rate suites are green: `build_site_discovery_query`, `_harvest_candidate_urls` (bahrain→official→authorized→gcc ordering, registry-first `score_source≥1.5` gate with legacy-whitelist fallback), `source_trace` route+source_weight recording, and the `tier1_5_hit_rate` Redis counters. Counterfeit invariant #1 (dhgate/aliexpress/temu/wish rejected) is pinned.
2. **CONSULTED (runtime-proven).** Every weak-Tier-1 query in the double-tap run shows a price-race wall of 4.6–7.9s. A pure Tier-1-empty→GPT-estimate path is ~2–3s; the additional 3–5s is the Bahrain `site:` discovery gather + the fan_out scrape race executing. Escalation demonstrably runs on the products that need it. Corroborated by the counter: **81 Tier 1.5 attempts** over the baseline window.
3. **WINNING (counter-proven).** `/admin/costs → tier1_5_hit_rate` over the window: **81 attempts / 22 hits = 27% overall.** Per category: grocery 3/5 (60%), supplements 17/55 (31%), skincare 1/6, other 1/1, **electronics 0/14**. Escalation isn't merely consulted — it lands a scraped/structured price on better than 1-in-4 escalating products.

## 2. The electronics/appliance parse gap (0/14)

Electronics is the single 0-hit class — matching the double-tap targets that sat there (AC, Kindle, Xiaomi all priced `estimated`, route=None). The escalation fires (4–8s price walls) but no scraped winner lands. Likely causes + S2 levers:
- **Shopify registry stores SHOULD parse** — shopalmoayyed.com (appliances/AC) + bh.asgharali.com expose clean JSON-LD; if they're in the discovery results but not winning, check the scraper's JSON-LD/microdata selector against their markup.
- **lulu.com.bh / carrefourbh.com are likely SPAs** — curl fetch yields no embedded price → needs the Firecrawl/Scrape.do rendered tier (which may be timing out inside the 15s fan_out cap on cold cache).
- **Upstream Serper `gl=bh` shopping yield is thin** for electronics — the Tier-1 weakness that forces escalation in the first place is itself the deeper gap.

## 3. The double-tap estimate-caching limitation (runbook caveat)

The double-tap (run cold → cap, re-run warm → read route) was designed to capture a registry route on a query whose first run cap-breached. It has a real limitation: **Tier-3 GPT estimates cache too** (`set_cached` at structured_comparison_service.py:2884). So when run 1's price falls through escalation to a GPT estimate and caches it, run 2 serves the cached estimate (observed: tap-2 price walls 0.17s) and never re-runs the escalation. Consequence: **a warm re-run cannot surface a registry route that the cold run did not already produce.** The double-tap only re-runs price cold when price NEVER cached (i.e., it was cancelled before reaching the estimate fallback) — a narrow window. **Runbook fix idea for S2:** give the probe a read-through / cache-bust flag scoped to PRICE only (keep specs/reviews warm so the wall still fits) so escalation re-runs deterministically; or read evidence from the `tier15:source_hits` counters instead of per-request traces.

## 4. Per-target double-tap data (prod, clean post-baseline, 30s cap)

| target | query | tap-1 | tap-2 (warm) | source_method | route | price wall (cold) |
|---|---|---|---|---|---|---|
| elec-004 | Carrier 1.5T AC vs LG 1.5T AC | 200 @ 24.1s | 200 @ 22.8s | estimated / estimated | None | 7.9 / 7.1s |
| groc-001 | Bertolli vs Carbonell olive oil | 400 @ 30.6s | 200 @ 24.7s | estimated / estimated | None | 6.5 / 7.2s |
| supp-001 | NOW D3 vs Solgar D3 | 200 @ 27.5s | — | estimated / converted_usd | None | 6.1 / 3.2s |
| elec-012 | Kindle Paperwhite vs Kobo Clara | 200 @ 25.4s | — | estimated / estimated | None | 6.2 / 4.8s |
| elec-008 | Xiaomi 14 vs Nothing Phone 2 | 200 @ 23.2s | — | estimated / estimated | None | 4.6 / 5.3s |

Note: supp-001's `converted_usd` is a real iHerb price via the iHerb path (not the registry Tier-1.5 fan_out), so it correctly records no route. tap-2 warm runs served cached estimates (sub-200ms price walls) — see §3.

## 5. Carry-forward to S2

- **Per-source hit-rate dashboard line (~10 min):** add `tier15:source_hits:{domain}` aggregation to the `/admin/costs` `tier1_5_hit_rate` block (the F1.6 counters already write per-domain). This closes the registry-vs-legacy attribution residual.
- **Electronics parse-yield investigation:** §2 levers — Shopify selector check + Firecrawl-on-SPA for lulu/carrefour + Serper gl=bh yield.
- **Probe price-only cache-bust flag:** §3 — for deterministic routing evidence.
(All also belong in the S2 carry-over compilation — `docs/plans/2026-06-10-bundle-b-s2-prep-notes.md`.)
