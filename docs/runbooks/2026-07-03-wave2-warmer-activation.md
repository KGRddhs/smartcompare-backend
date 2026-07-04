# Warmer activation — Ahmed-ready checklist (post Wave-2)

Wave-2 VariantDescriptor build is complete on `feature/genuine-price-kpi` (PR #16). All new behavior is behind default-OFF flags (flag-OFF byte-identical, comm-green). This checklist is the terminal warmer flip — the parts Claude cannot do (Railway auth is dead on this machine: both Railway MCP servers + the CLI return invalid_grant). It layers on `docs/runbooks/2026-06-30-warmer-activation.md` (the Wave-1 runbook).

## Preconditions now MET (Wave-2, PR #16, comm-green)
- [x] Backstop descriptor axes (gender-both-stated / femme-asym-dropped / flanker-ADD / generation-inline / prefixed-size / model-year) — close the cache-read/display backstop leaks (`ENABLE_VARIANT_DESCRIPTOR_AXES`).
- [x] DB-leg identity round-trip (title + in_stock + brand) — migrations 033+034 + `ENABLE_PRICE_TITLE_PERSIST`; DB→L1 promotion re-gate.
- [x] Verdict-scrub enforce_correctness parity.
- [x] The 2 warmer-writable poison classes CLOSED at cache-write (off-clock only): gender flanker + one-sided SPF, via the curated `data/variant_hint_reference.json` veto (+ off-clock LLM hint, `ENABLE_VARIANT_LLM_HINT`).
- [x] Warmed KPI 18/18 holds flag-ON (offline truth-row matrix; the veto never fires on a correct truth resolution).

## Ahmed steps (interactive terminal — `railway login` first)

### 1. Merge the PR stack
`#12` (warmer gate machinery) → `#13` (source-quality) → `#16` (this Wave-2 branch). **CI is RED-by-design** on every commit (`test_value_math` TDD stubs + `test_youtube` env) → gate on the comm-diff, NOT CI green. `mergeable_state: unstable` is expected, not blocked.
`#16`'s migration 033 is a verbatim cherry-pick of `#12`'s `e9de71a` — the 3-way merge is clean.

### 2. Apply migrations 033 + 034 (COLUMN BEFORE FLAG)
Via Supabase MCP `apply_migration` (project `qulajmyxdbdkchvecmvc`) or the SQL editor:
- `migrations/033_product_prices_title.sql`
- `migrations/034_product_prices_in_stock.sql`
Verify both columns exist (`information_schema.columns` where table='product_prices') before the flag. (Claude CAN do this — Supabase MCP is authenticated.)

### 3. Serper health (do NOT skip)
`curl "https://web-production-58776.up.railway.app/api/v1/text/prices/iPhone%2015%20128GB"` → a real BHD number = alive; 400 "Not enough credits" = rotate first (CLAUDE.md rotation playbook + reset `budget:serper:<key8>:lifetime` + DEL `budget:serper:burn_alert_fired:*`).

### 4. Set the Railway flags (migrations first, then flags)
```
railway variables --service web --set ENABLE_PRICE_TITLE_PERSIST=true
railway variables --service web --set ENABLE_VARIANT_DESCRIPTOR_AXES=true
railway variables --service web --set ENABLE_VARIANT_LLM_HINT=true   # optional; curated-ref works without it
railway redeploy --service web
```
(`ENABLE_BH_GCC_CATALOG_SOURCES=true` is already live.)

### 5. Fresh cache purge (measurement hygiene)
Per the Wave-1 runbook Step 2 — re-verify nothing wrong survives for the KPI truth queries.

### 6. (Optional) Wire the off-clock LLM hint into the cron
B3b deliberately deferred wiring `warmer_write_veto_async` + `_reset_varhint_run_state` into `cron_warm_price_cache.py`'s write loop (to keep the branch flag-OFF byte-identical). The SYNC curated-ref veto already fires in the warm context via the `WARMER_CONTEXT` env; only the async LLM fallback needs this wiring. Small follow-up before the first cron run if the LLM fallback is desired.

### 7. Measure the WARMED per-category KPI ×3, then flip the warmer
```
ENABLE_VARIANT_DESCRIPTOR_AXES=true ENABLE_BH_GCC_CATALOG_SOURCES=true \
  python -m scripts.measure_warmed_kpi   # x3, expect 18/18 (1.000/cat)
```
Then flip `ENABLE_PRICE_CACHE_WARMER=true` + register the cron (`0 */12 * * *`, `python -m scripts.cron_warm_price_cache`) per the Wave-1 runbook Step 5 — iff every per-category gate is ≥0.85 and the comm gate is green.

## Warmer-gate watch-item (pre-existing, not a Wave-2 regression)
kpi-elec-006 "Nintendo Switch 2": the extra.com colorway title ("…Light Blue and Light Red") fails `should_cache_price` via the census's xfail-pinned Switch-Light colorway over-rejection (flag-INDEPENDENT — identical flag-ON/OFF). **Session-3 measured electronics 6/6 with this present** (the warm caches Switch 2 via a noon/sharafdg source), so it does not block the gate in practice. IF a live warmed run shows electronics <6/6 (5/6 = 0.833 < 0.85 would fail the electronics gate), apply the durable fix — a **structured colorway axis** (read the unbxd/algolia color field) or a bounded flag-gated trailing-colorway-clause tolerance. Do NOT add color words to `_ELECTRONICS_PADDING` (the xfail warns this reopens the games/bundle leak).

## Residual risk line for the runbook
The 2 warmer-writable poison classes (gender flanker + one-sided SPF) are CLOSED at cache-write by the curated veto (fail-closed on curated-miss; off-clock LLM hint recovers coverage). Remaining accept-level residuals are all backstop-only + write-gate-protected + display-backstopped, below the no-CRIT/HIGH bar: generation count-noun long tail; "Galaxy Watch 4 Straps" (accessory-guarded); ReDoS 512-cap xfail. Determinism (`ENABLE_GENUINE_PRICE_PRIORITY`) stays DORMANT — needs a cold-live-variance tuning session.
