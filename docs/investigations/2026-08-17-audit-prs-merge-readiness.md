# Scraping-audit PRs #36–#41 — merge-readiness pass (2026-08-17)

All six still sit on base `c1b9578`, which is current `main`, so none has drifted. All six report
`mergeable=true`. CI is `unstable`, which is expected — this repo gates on the comm diff, not CI
(`tests/test_value_math.py` is RED by design).

## Conflict analysis — clean

Four of the six touch `app/services/price_service.py` (#36, #38, #39, #40), so conflict risk was
the open question.

- **Pairwise** (`git merge-tree` across all price_service pairs): **6/6 clean**.
- **N-way**: merging all six sequentially into a scratch worktree off `c1b9578` produced **zero
  conflicts** (12 commits landed).

So merge order is not forced by conflicts. Files touched:

| PR | files |
|---|---|
| #36 gents/ladies gender leak | `price_service.py` |
| #37 Bright Data budget gate | `api_budget_service.py`, `brightdata_service.py` |
| #38 microdata currency+node | `price_service.py` |
| #39 cache-write accuracy guards | `price_service.py` |
| #40 variant-min decant guard | `price_service.py`, `woocommerce_service.py` |
| #41 async Redis offload | `cache_service.py`, `structured_comparison_service.py` |

## ⚠️ The finding that matters: three of these are NOT dormant

The handoff describes all six as "flag-gated, flag-OFF byte-identical". That is true but
**misleading**, because three are gated by flags that are **already ON in production**. Verified
against the live Railway env and the code defaults:

| PR | gate | prod state | effect on merge+deploy |
|---|---|---|---|
| #36 | `ENABLE_VARIANT_DESCRIPTOR_AXES` | `true` on Railway | **LIVE immediately** |
| #38 | `ENABLE_EXACT_PRICE_GATE` | unset → code default `"true"` | **LIVE immediately** |
| #39 | `ENABLE_EXACT_PRICE_GATE` | unset → code default `"true"` | **LIVE immediately** |
| #37 | `ENABLE_BRIGHTDATA_BUDGET_GATE` (new) | unset → OFF | dormant |
| #40 | `ENABLE_VARIANT_MIN_PRICE_GUARD` (new) | unset → OFF | dormant |
| #41 | `ENABLE_ASYNC_REDIS_OFFLOAD` (new) | unset → OFF | dormant |

Evidence: `exact_gate_enabled()` is `os.getenv("ENABLE_EXACT_PRICE_GATE", "true")` —
default-ON, and the var is absent from Railway `web`, so it runs ON. `ENABLE_VARIANT_DESCRIPTOR_AXES=true`
is set explicitly on `web`.

"Flag-OFF byte-identical" for #36/#38/#39 means *if you disable the exact-price gate or the
descriptor axes* — which nobody will do, since those are the core correctness gates. Rolling back
one of these three means disabling a correctness gate wholesale, not a targeted revert.

## Recommended sequence

**Dormant first — safe to land now, even with prod compares down:**
1. **#37** Bright Data budget gate — independent files, new flag, currently the only *unbounded*
   paid path under Serper depletion. Landing it dormant removes the risk of a surprise bill.
2. **#41** async Redis offload — independent files, new flag.
3. **#40** variant-min decant guard — new flag, and hard-requires the exact gate.

**Live-on-merge — hold until prod compares work again:**
4. **#39**, **#38**, **#36** — each changes production behaviour the moment Railway deploys. There
   is currently no way to observe the effect or make an evidence-based rollback decision, because
   every compare returns `BAD_REQUEST` at product identification (OpenAI credit exhaustion). Land
   these one at a time, with a warmed cache-read verification between each, once the LLM is
   restored.

Note #39 also changes `should_cache_price`, so a bad merge poisons the 7d price cache rather than
just returning a bad response — the strongest argument for landing it only when it can be verified.

## Still required before any merge

`/code-review ultra <PR#>` per the repo's own convention — user-triggered and billed, so it cannot
be run from an agent session. The six were built and self-reviewed in one session; the handoff
explicitly recommends an independent external review before merge
([[feedback-coverage-driven-review]]).
