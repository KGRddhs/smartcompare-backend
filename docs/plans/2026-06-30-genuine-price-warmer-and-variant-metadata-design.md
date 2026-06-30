# Genuine-price: warmer activation + structured variant metadata — DESIGN

**Status:** design approved 2026-06-30 (brainstorm). Next step: `writing-plans` → implementation plan for a next-session ultracode TEAM.
**Precondition:** PR #9 (exact-SKU correctness gate) is SHIPPED to main `cdaf5c5` + deployed. `ENABLE_EXACT_PRICE_GATE` ON; flag-OFF byte-identical to `b207bfa`.

## 1. Why this work / what's still open

The exact-SKU correctness gate ships *correctness* — a price that shows is the exact requested SKU — but this session proved the gate is invisible to users on the common path:

- **Cold compares resolve NO genuine price.** `price` axis = **0.0 across the ENTIRE persisted eval history** (06-10, 06-17 ×2, 06-29 ×2). Cold compares ride the 30s `STREAM_HARD_CAP`; genuine curl/render loses the race → pending. So on a cold query the user sees a price-pending line, not a genuine BHD price.
- **The WARMER is the only lever** that puts genuine prices on the cold/cache-served path, but it stays PAUSED — and it previously **poisoned the cache** with wrong prices (the pre-PR9 manual warm). The exact-SKU gate + fail-closed `should_cache_price` now guard that, which is what makes re-activation thinkable.
- **The KPI that should gate the warmer can't be measured today:** cold-cap pends prices (KPI ~0), the CLAUDE.md baseline anchor `54b603e8` is a TRUNCATED uuid the eval literally can't fetch (`uuid ~~` errors; full id `54b603e8-4eab-41c9-a34d-a5e391446559`), and the smoke20 winner axis is ±0.10 run-to-run noise (the SAME pre-PR code gave winner 0.40 AND 0.50 hours apart on 06-17) — too noisy for a single-run gate.
- **~9 residual leaks are token-indistinguishable** (gender flanker, one-sided SPF, same-token concentration flanker `Sauvage→Elixir`, cross-unit g↔ml, makeup one-sided formula, supplement acronyms ZMA/Cal-Mag). Every token fix re-introduces a WORSE over-rejection of correct products — proven repeatedly. They need structured metadata, not string matching.
- **A titleless price (URL, no title)** is SHOWN by `is_price_showable` but is NOT cached (`should_cache_price` needs a title) and scores not-usable in the KPI — an inconsistency between display and cache/KPI discipline.

## 2. Approved approach

**Two sequential ultracode WAVES in the next session**, each using the proven epic pattern:
`recon → TDD implement (sequential writers, race-free, path-restricted commits) → adversarial COVERAGE-DRIVEN sweep (enumerate the space + reproduce through the runtime — the method that caught what 14 hypothesis reviews missed) → dispatcher gates every finding → comm gate (branch-only-NEW == [] vs main)`.

**Wave 1 must pass its gate before Wave 2 starts.** Rejected alternatives: one mega-wave (the warmer's prod-cache writes must not interleave with matcher edits); metadata-first (lower user impact; warmer-first was chosen).

## 3. Wave 1 — warmer + measurement (terminal state: AUTO-ACTIVATE iff the gate passes)

**Reframe (the load-bearing insight):** because the warmer AUTO-ACTIVATES on its gate, Wave 1 is not "turn on the warmer" — it is "**build a gate trustworthy enough to hand it the prod-cache-write decision.**" The warmer flip is the *reward* for a green gate; any red leg ends Wave 1 with the warmer still OFF + a precise diagnosis. The warmer poisoned the cache before *precisely because* no trustworthy gate existed.

**Recon (do first):** map `cron_warm_price_cache.py` + knobs (`WARMER_SUBSET` / `MAX_QUERIES_PER_RUN` / `PRICE_RACE_TIMEOUT`); `build_size_aware_price_cache_key` / `_identity_cache_token`; the `/price-kpi` + `usable_exact_genuine_for_product` path; current cache cleanliness.

### Gate leg 1 — a reliable `usable_exact_genuine` KPI
- Measure **per-category, WARMED** (`/price-kpi` with `--read-cache`) on a **30–50-product/category truth set** (exact SKU ∧ native BHD ∧ in-stock ∧ valid PDP ∧ valid URL). It is a BINARY per-product check → far less noisy than the winner axis.
- Resolve the chicken-and-egg: **warm a per-category sample → measure the KPI on that warmed sample → ≥85%/category unlocks the full warmer.**
- Retire the truncated `54b603e8` anchor; pin a FRESH multi-run baseline; correct the CLAUDE.md gate command to the full UUID. (The smoke20 winner gate is too noisy — do NOT use it as the warmer gate; use the binary KPI.)

### Gate leg 2 — cache-key PARITY (the silent killer)
- The warmed key MUST match the live query's parse, or every warm is a guaranteed cache MISS (warmed "Eau de Toilette 100ml" ≠ live "EDT" → miss → the warmer changes NOTHING on-device).
- Fix: derive the cache key from the **RESOLVED-match identity** (concentration / size / variant axes via `_identity_cache_token`), not the raw query string.
- Ship a PARITY TEST: warm phrasing A → read phrasings B/C of the same SKU → all HIT.

### Gate leg 3 — fresh-purge precondition
- Assert a clean cache before warming (no pre-existing wrong entry survives). Re-verify the earlier purge (18 Redis + 211 DB rows) held.

### Folded-in items
- **Titleless-price decision (#4):** make display and cache/KPI consistent — either the warmer guarantees a title on cached prices (so they're SKU-verifiable), OR display pends titleless prices (fail-closed). Recommend the latter unless it over-rejects a measurable share.
- **Serper budget guard:** the warmer burns paid Serper continuously — bound it (`MAX_QUERIES_PER_RUN` + a budget circuit) and ESTIMATE the cost before activation.

### Auto-activation rule
Flip `ENABLE_PRICE_CACHE_WARMER` ON **iff** per-category KPI ≥ 85% ∧ cache-parity proven ∧ fresh-purge confirmed. Else: warmer OFF + diagnosis.

## 4. Wave 2 — structured variant metadata (close the residuals)

The ~9 residuals are token-indistinguishable; compare a structured **`VariantDescriptor`**, not strings. **Chosen source = option C:**
- **Formalize the existing axis extractors** (concentration / size / storage / gender / SPF / count / strength / form / flavour / finish …) into ONE `VariantDescriptor` per side.
- The matcher compares STRUCTURED fields, not token sets — so a gender/SPF/concentration mismatch is decided on the field, with correct asymmetry baked into the descriptor comparison.
- Resolve the genuinely-ambiguous cases (men's-base vs femme-flanker; flagship vs flanker concentration like `Sauvage` vs `Sauvage Elixir`) with a **small curated reference + a NARROW LLM hint ONLY where axes truly can't decide** — reserve the LLM for the handful tokens can't settle, not the common path.
- Cross-unit g↔ml: the descriptor carries a typed size {value, unit-class}; comparison fails-closed across incomparable unit classes (already the current behavior) but a same-number density-1 tolerance can be re-evaluated with the typed field.

Wave 2's recon must go DEEP on each residual + where its metadata comes from before any TDD. The coverage sweep stays the verifier (the fix's own over-rejection is the next blind spot — re-sweep after every fix).

## 5. Success criteria
- **Wave 1:** the warmer is either (a) AUTO-ACTIVATED with a green per-category KPI (≥85%) + proven cache-parity + clean cache, so cold/cache-served compares now show genuine BHD prices; or (b) OFF with a precise per-leg diagnosis. Comm zero-regression; flag-OFF parity preserved.
- **Wave 2:** the residual leaks close via the `VariantDescriptor` WITHOUT re-introducing over-rejection (coverage-sweep-verified); the pinned token-tradeoffs in `tests/test_correctness_coverage_sweep_fixes.py` flip from xfail/held to fixed where the descriptor decides them.

## 6. Risks
- The warmer writing to the SHARED prod cache (poisoning) — mitigated by the gate-first design + fail-closed `should_cache_price` + the exact-SKU gate.
- Local `_get_price`/seed/warm with `nocache=True` STILL WRITES to the shared Upstash + DB (nocache bypasses the READ, not the WRITE) → local testing pollutes prod cache. The team must run warm/KPI against an isolated cache or accept + purge.
- Serper budget blowout from the warmer — the budget guard is a leg-1 requirement.
- Wave 2 over-engineering — keep the LLM hint NARROW (axes decide the common path).
