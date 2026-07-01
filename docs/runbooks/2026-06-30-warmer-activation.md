# Warmer activation runbook — the GATED terminal step of Wave 1

**Owner:** Ahmed (interactive terminal — needs `railway login` + a healthy PAID Serper key).
**Precondition:** the Wave-1 code (branch `feature/genuine-price-warmer`) is merged + deployed. That branch ships the gate machinery (per-category KPI verdict, Serper-budget guard, DB-title persistence, cache-key parity pins) but leaves `ENABLE_PRICE_CACHE_WARMER` **OFF**. This runbook is the "flip it iff the gate is green" step Claude cannot do (no Railway auth in a non-interactive session).

> **Why this is a manual gate, not auto-code:** the warmer WRITES genuine BHD prices into the SHARED prod cache and BURNS paid Serper. It previously poisoned the cache when no correctness gate existed. The exact-SKU gate (PR #9) + fail-closed `should_cache_price` now guard the write; this runbook is the human confirmation that the WARMED per-category KPI clears ≥85% before we let the cron write continuously.

---

## Step 0 — Serper health (do NOT skip)

The warmer burns paid Serper continuously. Confirm the key is healthy + has headroom:

```bash
# 1. Confirm the paid key is SET on Railway (presence only — do NOT echo the value).
railway variables --service web | grep -qi '^SERPER_API_KEY=' && echo 'SERPER_API_KEY set' || echo 'MISSING'

# 2. Liveness — a bare prices endpoint (NEVER a full compare; that rides the 30s cap).
curl "https://web-production-58776.up.railway.app/api/v1/text/prices/iPhone%2015%20128GB"
#   -> regional_prices.bahrain.amount a real BHD number == key alive. A 400 "Not enough
#      credits" (or all-pending) == DEPLETED -> rotate first.

# 3. Headroom — the warmer's pre-run guard is a TIER-INDEPENDENT per-run credit cap
#    (WARMER_MAX_SERPER_CREDITS_PER_RUN default 900, at ~WARMER_SERPER_CREDITS_PER_QUERY
#    default 30 credits/query -> 900/30=30 affordable, so the default MAX_QUERIES_PER_RUN=25
#    window is NOT trimmed). It deliberately does NOT consult api_budget_service's lifetime
#    counter, so it can never mis-fire on a healthy paid key. A smoke20 warm (~20 queries
#    x2 products) ~= 400-600 credits.
```

**If depleted:** rotate per the CLAUDE.md playbook (new key → `railway variables --set` + `railway redeploy` + sync local `.env` + reset `budget:serper:<key8>:lifetime` + DEL `budget:serper:burn_alert_fired:*`) BEFORE proceeding.

## Step 1 — (optional but recommended) make the warm DURABLE: migration 033 + title flag

Without this, a warmed price is genuine+title in Redis L1 but rehydrates title-less from the DB after the L1 TTL (→ not usable_exact_genuine long-term). Applying it makes the warm durably SKU-verifiable.

```
# Apply 033 (Supabase MCP apply_migration, or the SQL editor):
#   migrations/033_product_prices_title.sql   (ADD COLUMN IF NOT EXISTS title TEXT)
# THEN (order matters — column first, flag second):
railway variables --service web --set ENABLE_PRICE_TITLE_PERSIST=true
railway redeploy --service web
```
Verify the column exists (`information_schema.columns` where table='product_prices' and column='title') before flipping the flag. Rollback: flip the flag OFF, then `migrations/rollback/033_product_prices_title.sql`.

## Step 2 — fresh cache (measurement hygiene)

The 18 wrong keys + 211 DB rows were purged during PR #9. Re-verify nothing wrong survives for the KPI truth queries. **GOTCHA:** any `_get_price`/warm with `nocache=True` STILL WRITES the shared Upstash + `product_prices` (nocache bypasses the READ, not the WRITE). So the warm + the `/price-kpi` measurement below BOTH write to prod cache — that is the warmer's intended effect, and the exact-SKU gate ensures only correct SKUs are cached. If you want a clean-room measurement instead, point `SUPABASE_*`/`UPSTASH_*` at an isolated project for the warm+KPI, then the prod cache is untouched.

## Step 3 — warm a bounded per-category sample (off-clock budgets)

The warmer runs the gold + `warmer_catalog` queries with the off-clock timeouts (`WARMER_PRICE_RACE_TIMEOUT=60`, `WARMER_STREAM_HARD_CAP=150`) so the slow genuine curl finishes. Bound the spend:

```bash
# LOCAL manual warm (writes to the SHARED prod cache — that's the point):
ENABLE_PRICE_CACHE_WARMER=true WARMER_SUBSET=smoke20 MAX_QUERIES_PER_RUN=20 \
  python -m scripts.cron_warm_price_cache
#  -> logs: genuine=… converted=… none=… | genuine-share=…% ; the pre-run Serper
#     guard trims the window if headroom is low; the per-query circuit stops on exhaustion.
```

To warm the KPI TRUTH set specifically (electronics/fashion/fragrances today — expand the truth set for more categories), warm those exact queries so the L1 key matches the KPI read (same parser output = same cache key; see the cache-key parity residual — phrase the warm queries the way the KPI queries are phrased).

## Step 4 — measure the WARMED per-category KPI

```bash
# POST-warm, read-cache (nocache=false) so it serves the warmed prices:
python -m scripts.eval_runner --kpi usable_exact_genuine --read-cache \
  --base-url https://web-production-58776.up.railway.app --concurrency 1
```
Read the JSON `gate` block:
```json
"gate": { "threshold": 0.85, "pass": true|false, "failing": {…}, "measured_categories": […] }
```
- `pass: true` (every measured category ≥0.85, at least one measured) → the gate is GREEN.
- `pass: false` → note the `failing` categories; the warmer stays OFF. Diagnose per category (was it a genuine-source gap, a cache-key miss, or a titleless L2 rehydrate?).

Save the JSON to `docs/investigations/2026-06-30-warmer-kpi-result.md`.

## Step 5 — AUTO-ACTIVATION decision

Flip the warmer ON **iff ALL** hold:
1. per-category KPI `gate.pass == true` (≥85%/category, Step 4),
2. cache-key parity respected (warm queries phrased like live/KPI queries — Task-4 pins),
3. the cache is clean (Step 2),
4. the branch comm gate is green (branch-only-NEW failures == []).

```bash
# Register the cron (dispatcher decision) + flip the flag:
railway variables --service web --set ENABLE_PRICE_CACHE_WARMER=true
# Railway cron service:  schedule 0 */12 * * *   command  python -m scripts.cron_warm_price_cache
#   (12h beats the 24h L1 TTL). Size MAX_QUERIES_PER_RUN / WARMER_SUBSET to the Serper plan.
railway redeploy --service web
```

**Any red leg → leave `ENABLE_PRICE_CACHE_WARMER` OFF + write the per-leg diagnosis. Do not start Wave 2 until Wave 1's gate is green (or consciously deferred).**

## Serper cost estimate (for budgeting)

- One warm query ≈ 2 products × ~10–30 credits = ~20–60 credits.
- A smoke20 warm (20 queries) ≈ 400–1,200 credits per run.
- The cron at 12h cadence with `MAX_QUERIES_PER_RUN=25` ≈ ~500–1,500 credits / run × 2 runs/day.
- **Spend knobs:** `MAX_QUERIES_PER_RUN` (count cap, default 25) is the hard bound; `WARMER_MAX_SERPER_CREDITS_PER_RUN` (per-run credit ceiling, default 900; `<=0` disables) trims the window to `WARMER_MAX_SERPER_CREDITS_PER_RUN / WARMER_SERPER_CREDITS_PER_QUERY` (default 900/30 = 30) queries, layered UNDER the count cap. At defaults the credit cap (30) exceeds the count cap (25) so it never trims — lower `WARMER_MAX_SERPER_CREDITS_PER_RUN` to bound a run below 25 queries.
- Free Serper (~2,500 one-time) affords ~2–5 runs; **sustained warming needs the paid plan.** The tier-independent per-run credit cap bounds each run and a truly-depleted account simply rejects calls (handled gracefully by `_warm_one`), so a low balance degrades coverage rather than blowing the budget.
