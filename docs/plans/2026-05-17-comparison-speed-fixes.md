# Comparison Speed Fixes Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Ship the parked scatter-gather branch (D1, fixes luxury 85s → ≤30s with real prices) and run a data-driven diagnosis of the mainstream 30s GPT-extraction bottleneck (D2 Phase 2A) so the D2 fix can be designed against actual numbers.

**Architecture:** D1 is a clean two-commit cherry-pick from `experiment/scatter-gather-2026-05-16` onto `main`. The wiring change is isolated to `app/services/structured_comparison_service.py::_get_price()` Tier 1.5 block — replaces sequential cascade with `fan_out_price_lookup()` parallel race. The race primitive (`fan_out_price_lookup`) already lives on `main` in `app/services/price_service.py:980` from earlier Bundle E work; the branch just calls it. D2 Phase 2A is an additive `time.perf_counter()` instrumentation layer in `_fetch_product_data()`, gated by `DEBUG_STAGE_TIMINGS=true` env var, emitting `metadata.stage_timings_ms`. After 2A data lands, Phases 2B–2D get written into this plan as an addendum (data-driven; cannot be specified blind).

**Tech Stack:** Python 3.12, FastAPI, asyncio, Railway (auto-deploys on `git push origin main`), pytest, Upstash Redis (cache + budget), Serper / Firecrawl / Scrape.do (price providers).

**Design source:** `docs/plans/2026-05-17-comparison-speed-fixes-design.md` (committed `7b8ab03`).

---

## Pre-flight: baseline snapshot for regression detection

Before D1 ships, capture a fresh baseline so we can prove D1 didn't slow mainstream and didn't break quality. This is the reference point for both D1 verification AND D2's spec parity test.

### Task 0.1: Capture cold-cache mainstream baseline (iPhone 17 vs Galaxy S25 Ultra)

**Files:**
- Create: `tests/fixtures/comparison_baseline_d2.json` (will become the D2 spec parity fixture)

**Step 1: Run cold-cache bench against Railway**

Run:
```bash
curl -sS -o tests/fixtures/comparison_baseline_d2.json \
  -w "TIME=%{time_total}s STATUS=%{http_code} SIZE=%{size_download}\n" \
  "https://web-production-58776.up.railway.app/api/v1/text/compare?q=iPhone+17+vs+Galaxy+S25+Ultra&region=bahrain&nocache=true" \
  --max-time 90
```

Expected: STATUS=200, SIZE>10000, TIME between 25-40s.

**Step 2: Verify baseline structure**

Run:
```bash
python -c "
import json
d = json.load(open('tests/fixtures/comparison_baseline_d2.json'))
prods = d.get('products') or (d.get('specs') or {}).get('products', [])
assert len(prods) == 2, f'expected 2 products, got {len(prods)}'
for p in prods:
    s = p.get('specs') or {}
    print(f\"  {p.get('name','?')[:40]}: {len(s)} spec keys\")
print('OK')
"
```

Expected: prints both products with ≥6 spec keys each, ends with `OK`.

**Step 3: Commit the baseline fixture**

```bash
git add tests/fixtures/comparison_baseline_d2.json
git commit -m "test(fixtures): pre-D1 cold-cache baseline for spec-parity regression checks

Reference response for iPhone 17 vs Galaxy S25 Ultra captured against
Railway production immediately before D1 (scatter-gather) ships. Used
by Phase 2C spec parity test to assert D2 doesn't drop any fields."
```

---

## Phase 1: D1 — cherry-pick scatter-gather onto main

### Task 1.1: Dry-run the cherry-pick to detect conflicts

**Files:**
- Read only: `app/services/structured_comparison_service.py`

**Step 1: Attempt cherry-pick without committing**

Run:
```bash
git cherry-pick --no-commit 9bf5b44 88adf85
```

Expected outcomes:
- **Clean:** no conflicts, files staged. Verify with `git status` — should show `M app/services/structured_comparison_service.py` and `?? tests/test_fan_out_integration.py` (or `A tests/test_fan_out_integration.py` since `--no-commit` keeps it staged as new).
- **Conflict:** ask user to confirm three-way merge strategy before continuing. STOP this plan, get user input.

**Step 2: If clean, abort the dry-run and re-do as a real cherry-pick**

Run:
```bash
git reset --hard HEAD  # discard the dry-run staging
git cherry-pick 9bf5b44 88adf85
```

Expected: two new commits appended to `main` — `test(fan_out): RED tests...` and `feat(comparison): wire fan_out_price_lookup...`.

Verify:
```bash
git log --oneline -3
```

Expected: top three lines should be the cherry-picked feat commit, the cherry-picked test commit, and `7b8ab03 docs(plans): comparison speed fixes design`.

---

### Task 1.2: Verify py_compile is clean

**Step 1: Compile-check the modified orchestrator**

Run:
```bash
python -m py_compile app/services/structured_comparison_service.py
echo "exit=$?"
```

Expected: `exit=0`, no output above.

**Step 2: Compile-check the new test file**

Run:
```bash
python -m py_compile tests/test_fan_out_integration.py
echo "exit=$?"
```

Expected: `exit=0`.

If either fails: STOP, investigate import errors. Most likely cause = a function signature mismatch between the branch and current `price_service.py`. Read both diff sides and reconcile.

---

### Task 1.3: Run the 12 fan_out integration tests

**Step 1: Run the targeted test file**

Run:
```bash
python -m pytest tests/test_fan_out_integration.py -v --timeout=60
```

Expected: `12 passed` in under 30s. The tests don't hit network — all scrapers + Serper are patched.

If any fail: do NOT push to Railway. Investigate failures one at a time. Most common: `AttributeError` on a price_service helper that's been renamed/removed since the branch was created. Reconcile against current `app/services/price_service.py`.

---

### Task 1.4: Run the broader free unit suite for regressions

**Step 1: Run all unit tests except live/integration**

Run:
```bash
python -m pytest tests/ -v -m "not (live_unit or live_db or integration)" --ignore=tests/test_integration.py --timeout=120 2>&1 | tail -40
```

Expected: ≤17 pre-existing failures (matches Session 47/48 baseline — `test_personalization`, `test_share_routes`, `test_push_token_endpoint`). NO new failures introduced by the cherry-pick.

**Step 2: Capture failure list for comparison**

If the failure count exceeds 17, OR a different test name fails compared to known baseline, STOP. The cherry-pick has introduced a regression. Investigate before pushing.

Compare against known baseline:
```bash
python -m pytest tests/ -m "not (live_unit or live_db or integration)" --ignore=tests/test_integration.py --tb=no -q 2>&1 | grep -E "^FAILED|^[0-9]+ failed" | head -25
```

Expected failing tests (from Session 47/48 baseline):
- `test_personalization::test_*` (2-3 mock state contamination)
- `test_share_routes::test_strips_personalization`
- Anything in `test_push_token_endpoint`

If the failing set is a strict subset of the above, proceed. Otherwise STOP.

---

### Task 1.5: Push D1 to Railway

**Step 1: Confirm clean working tree before push**

Run:
```bash
git status --short
```

Expected: only `M .claude/settings.local.json` and `?? .claude/worktrees/` (pre-existing noise) — NO unrelated staged changes.

**Step 2: Push**

Run:
```bash
git push origin main
```

Expected: push succeeds. Railway webhook fires.

**Step 3: Watch Railway deploy until healthy**

Run:
```bash
railway logs --service web 2>&1 | head -50
```

Expected (within ~90s): line containing `INFO: Uvicorn running on http://0.0.0.0` and `INFO:     Application startup complete`.

If deploy fails (red status in `railway logs`), revert immediately:
```bash
git revert HEAD~1..HEAD --no-edit
git push origin main
```

---

### Task 1.6: Post-deploy verification bench (luxury query)

**Step 1: Wait for Railway to fully stabilize**

Run:
```bash
curl -sS https://web-production-58776.up.railway.app/health
```

Expected: `{"status":"healthy"}` or similar 200 response. If 503, wait 30s and retry up to 3 times.

**Step 2: Cold-cache bench LV Neverfull vs Gucci Marmont**

Run:
```bash
curl -sS -o /tmp/d1_verify.json \
  -w "TIME=%{time_total}s STATUS=%{http_code}\n" \
  "https://web-production-58776.up.railway.app/api/v1/text/compare?q=Louis+Vuitton+Neverfull+MM+vs+Gucci+GG+Marmont&region=bahrain&nocache=true" \
  --max-time 60
```

Expected: STATUS=200, TIME under 45s (was 85s pre-D1).

**Step 3: Assert price source_method is NOT estimated**

Run:
```bash
python -c "
import json
d = json.load(open('/tmp/d1_verify.json'))
prods = d.get('products') or (d.get('specs') or {}).get('products', [])
assert len(prods) == 2, f'expected 2 products, got {len(prods)}'
fails = []
for p in prods:
    pr = p.get('price') or {}
    sm = pr.get('source_method', '?')
    nm = p.get('name', '?')
    print(f'  {nm[:40]}: source_method={sm} amount={pr.get(\"amount\")}')
    if sm == 'estimated':
        fails.append(f'{nm}: still estimated (D1 not effective)')
    expected_good = {'firecrawl_brand_domain', 'page_scrape_jsonld', 'page_scrape',
                     'scrapedo_rendered', 'local_bhd', 'converted_usd', 'firecrawl'}
    if sm not in expected_good:
        fails.append(f'{nm}: unexpected source_method={sm}')
if fails:
    raise SystemExit('FAIL:\n  ' + '\n  '.join(fails))
print('PASS — D1 produces real prices on luxury query')
"
```

Expected: prints both products with non-`estimated` source_methods, ends with `PASS`.

If FAIL with `still estimated`: D1 wired correctly but scrapers themselves return nothing. Two possibilities — (a) URL discovery from Serper failed for these specific products (try a different luxury query — Hermès Birkin vs Chanel Flap), (b) Firecrawl/Scrape.do are blocked on `.lv.com` / `.gucci.com`. Either is a Bucket A diagnostic, NOT a D1 rollback trigger. Log finding, move on.

If FAIL with `unexpected source_method`: investigate the unknown method. Could be a new tier added since the branch was written. Update the expected_good set after confirming legitimacy.

**Step 4: Update task tracker**

Mark task `#3` (D1) status=completed in the active task list. Record the LV bench wall-time as the new luxury baseline.

---

## Phase 2A: D2 diagnosis — stage-level timing instrumentation

### Task 2A.1: Add `time.perf_counter()` markers to `_fetch_product_data()`

**Files:**
- Modify: `app/services/structured_comparison_service.py` — around line 884 (`async def _fetch_product_data`)

**Step 1: Write the test for the new metadata field**

Create new file `tests/test_stage_timings.py`:

```python
"""DEBUG_STAGE_TIMINGS env flag adds per-stage timing to metadata."""
import os
import pytest
from unittest.mock import AsyncMock, patch

from app.services.structured_comparison_service import (
    get_comparison_service,
    StructuredComparisonService,
)


@pytest.mark.asyncio
async def test_stage_timings_present_when_flag_on(monkeypatch):
    """When DEBUG_STAGE_TIMINGS=true, response metadata includes
    stage_timings_ms with the expected keys per product."""
    monkeypatch.setenv("DEBUG_STAGE_TIMINGS", "true")

    # Patch the network-going helpers so the test is offline
    with patch.object(
        StructuredComparisonService, "_get_specs",
        new=AsyncMock(return_value={"ram": "8 GB"}),
    ), patch.object(
        StructuredComparisonService, "_get_price",
        new=AsyncMock(return_value={"amount": 100, "currency": "BHD", "source_method": "local_bhd"}),
    ), patch.object(
        StructuredComparisonService, "_get_reviews",
        new=AsyncMock(return_value={"summary": "test", "pros": [], "cons": []}),
    ), patch.object(
        StructuredComparisonService, "_get_verified_rating",
        new=AsyncMock(return_value={"rating": 4.5, "review_count": 100}),
    ), patch(
        "app.services.structured_comparison_service.search_web",
        new=AsyncMock(return_value={"organic": []}),
    ), patch(
        "app.services.structured_comparison_service.parse_product_query",
        new=AsyncMock(return_value=[
            {"brand": "Apple", "name": "iPhone 17", "variant": None, "category": "electronics"},
            {"brand": "Samsung", "name": "Galaxy S25 Ultra", "variant": None, "category": "electronics"},
        ]),
    ):
        svc = get_comparison_service()
        response = await svc.compare_from_text(
            query="iPhone 17 vs Galaxy S25 Ultra",
            region="bahrain",
        )

    metadata = response.get("metadata") or {}
    timings = metadata.get("stage_timings_ms")
    assert timings is not None, "stage_timings_ms missing when flag enabled"
    assert isinstance(timings, dict), f"expected dict, got {type(timings)}"

    # Per-product timing keys (list-of-dicts, one per product)
    products_timings = timings.get("per_product")
    assert isinstance(products_timings, list), "per_product missing"
    assert len(products_timings) == 2, f"expected 2 products, got {len(products_timings)}"

    expected_keys = {"unified_search_ms", "specs_ms", "price_ms",
                     "reviews_ms", "rating_ms"}
    for i, p in enumerate(products_timings):
        missing = expected_keys - set(p.keys())
        assert not missing, f"product {i} missing keys: {missing}"
        for k in expected_keys:
            assert isinstance(p[k], (int, float)), f"product {i} {k} is not numeric"
            assert p[k] >= 0, f"product {i} {k} is negative"

    # Top-level orchestrator timings
    expected_top = {"total_ms", "scoring_ms", "verdict_ms", "response_build_ms"}
    missing_top = expected_top - set(timings.keys())
    assert not missing_top, f"orchestrator-level keys missing: {missing_top}"


@pytest.mark.asyncio
async def test_stage_timings_absent_when_flag_off(monkeypatch):
    """When DEBUG_STAGE_TIMINGS is unset or false, metadata.stage_timings_ms
    must NOT be present (zero observability surface in prod)."""
    monkeypatch.delenv("DEBUG_STAGE_TIMINGS", raising=False)

    with patch.object(
        StructuredComparisonService, "_get_specs",
        new=AsyncMock(return_value={"ram": "8 GB"}),
    ), patch.object(
        StructuredComparisonService, "_get_price",
        new=AsyncMock(return_value={"amount": 100, "currency": "BHD", "source_method": "local_bhd"}),
    ), patch.object(
        StructuredComparisonService, "_get_reviews",
        new=AsyncMock(return_value={"summary": "test", "pros": [], "cons": []}),
    ), patch.object(
        StructuredComparisonService, "_get_verified_rating",
        new=AsyncMock(return_value={"rating": 4.5, "review_count": 100}),
    ), patch(
        "app.services.structured_comparison_service.search_web",
        new=AsyncMock(return_value={"organic": []}),
    ), patch(
        "app.services.structured_comparison_service.parse_product_query",
        new=AsyncMock(return_value=[
            {"brand": "Apple", "name": "iPhone 17", "variant": None, "category": "electronics"},
            {"brand": "Samsung", "name": "Galaxy S25 Ultra", "variant": None, "category": "electronics"},
        ]),
    ):
        svc = get_comparison_service()
        response = await svc.compare_from_text(
            query="iPhone 17 vs Galaxy S25 Ultra",
            region="bahrain",
        )

    metadata = response.get("metadata") or {}
    assert "stage_timings_ms" not in metadata, \
        "stage_timings_ms leaked into prod response (flag was off)"
```

**Step 2: Run the test — expect FAIL**

Run:
```bash
python -m pytest tests/test_stage_timings.py -v --timeout=30
```

Expected: both tests FAIL with `AssertionError: stage_timings_ms missing` and `AssertionError` on the second (or PASS since the field doesn't exist yet — first asserts presence, second asserts absence, so flag-off should pass and flag-on should fail).

Expected exact: `test_stage_timings_present_when_flag_on FAILED`, `test_stage_timings_absent_when_flag_off PASSED`.

**Step 3: Implement the instrumentation**

Modify `app/services/structured_comparison_service.py`:

First, add a top-level helper near the imports (around line 80, after existing imports):

```python
import os
_DEBUG_STAGE_TIMINGS = None

def _debug_timings_enabled() -> bool:
    """Cached env var lookup. Read once per process to avoid os.environ
    hits in the hot path. Process restart picks up env changes."""
    global _DEBUG_STAGE_TIMINGS
    if _DEBUG_STAGE_TIMINGS is None:
        _DEBUG_STAGE_TIMINGS = os.environ.get("DEBUG_STAGE_TIMINGS", "false").lower() == "true"
    return _DEBUG_STAGE_TIMINGS
```

Then in `_fetch_product_data()` (around line 884), wrap each stage with `time.perf_counter()`:

```python
async def _fetch_product_data(
    self, product_info: Dict, region: str, include_specs: bool, include_reviews: bool, nocache: bool = False
) -> Dict[str, Any]:
    """Fetch all data for a single product."""
    brand = product_info.get("brand", "")
    # ... (existing setup unchanged) ...

    stage_timings = {} if _debug_timings_enabled() else None

    # === Unified web search ===
    unified_search = None
    if include_specs or include_reviews:
        # ... (existing cache checks) ...
        if (include_specs and not specs_hit) or (include_reviews and not reviews_hit):
            t0 = time.perf_counter() if stage_timings is not None else None
            unified_search = await search_web(
                f"{search_query} specifications reviews price", num_results=10
            )
            if stage_timings is not None:
                stage_timings["unified_search_ms"] = round((time.perf_counter() - t0) * 1000, 1)
            self._track_serper_cost()

    if stage_timings is not None and "unified_search_ms" not in stage_timings:
        stage_timings["unified_search_ms"] = 0.0  # cache hit, no Serper call

    # === Phase 1: specs + price (parallel) ===
    # ... existing phase1 setup ...

    t1 = time.perf_counter() if stage_timings is not None else None
    phase1_results = await asyncio.gather(*phase1_tasks, return_exceptions=True)
    if stage_timings is not None:
        phase1_elapsed_ms = round((time.perf_counter() - t1) * 1000, 1)
        # Attribute the longer of the two to its key — they run in parallel,
        # so total phase1 time = max(specs, price). Record both as the same
        # value (the wall time) since we can't measure them independently
        # without breaking the gather.
        if "specs" in phase1_keys:
            stage_timings["specs_ms"] = phase1_elapsed_ms
        stage_timings["price_ms"] = phase1_elapsed_ms

    # ... existing phase1 result handling ...

    # === Phase 2: reviews + rating (parallel) ===
    # ... existing phase2 setup ...

    t2 = time.perf_counter() if stage_timings is not None else None
    phase2_results = await asyncio.gather(*phase2_tasks, return_exceptions=True)
    if stage_timings is not None:
        phase2_elapsed_ms = round((time.perf_counter() - t2) * 1000, 1)
        if "reviews" in phase2_keys:
            stage_timings["reviews_ms"] = phase2_elapsed_ms
        stage_timings["rating_ms"] = phase2_elapsed_ms

    # ... existing fact-check / response shaping ...

    if stage_timings is not None:
        result["_stage_timings_ms"] = stage_timings

    return result
```

Then in `compare_from_text()` (around line 400), accumulate per-product timings into the final metadata:

```python
async def compare_from_text(
    self, query: str, region: str = "bahrain", ...
) -> Dict[str, Any]:
    start_time = datetime.now()
    orchestrator_timings = {} if _debug_timings_enabled() else None

    # ... existing query parse ...

    # Step 2: Fetch data for each product (parallel)
    t_fetch = time.perf_counter() if orchestrator_timings is not None else None
    product_data = await asyncio.gather(
        *(self._fetch_product_data(p, region, True, True, nocache) for p in products),
        return_exceptions=False,
    )
    # ... (existing behavior_profile/demographics fetch in parallel) ...

    # Step 3: Compute deterministic scores
    t_score = time.perf_counter() if orchestrator_timings is not None else None
    scores = scoring_service.compute_scores(product_data, ...)
    if orchestrator_timings is not None:
        orchestrator_timings["scoring_ms"] = round((time.perf_counter() - t_score) * 1000, 1)

    # Step 4: Generate verdict
    t_verdict = time.perf_counter() if orchestrator_timings is not None else None
    verdict = await extraction_service.generate_verdict(...)
    if orchestrator_timings is not None:
        orchestrator_timings["verdict_ms"] = round((time.perf_counter() - t_verdict) * 1000, 1)

    # Step 5: Build response
    t_build = time.perf_counter() if orchestrator_timings is not None else None
    response = build_comparison_response(...)
    if orchestrator_timings is not None:
        orchestrator_timings["response_build_ms"] = round((time.perf_counter() - t_build) * 1000, 1)
        orchestrator_timings["total_ms"] = round(
            (datetime.now() - start_time).total_seconds() * 1000, 1
        )
        per_product = []
        for p in product_data:
            t = p.pop("_stage_timings_ms", None)
            if t:
                per_product.append(t)
        orchestrator_timings["per_product"] = per_product
        response.setdefault("metadata", {})["stage_timings_ms"] = orchestrator_timings

    return response
```

**NOTE:** the exact line numbers will shift as you read the file — search for the `# Step 3:` / `# Step 4:` / `# Step 5:` comment markers (already exist in the file per `grep -nE "# Step" app/services/structured_comparison_service.py`) and wrap each step block.

**Step 4: Run the new tests — expect PASS**

Run:
```bash
python -m pytest tests/test_stage_timings.py -v --timeout=30
```

Expected: `2 passed`.

**Step 5: Run the broader unit suite for regressions**

Run:
```bash
python -m pytest tests/ -v -m "not (live_unit or live_db or integration)" --ignore=tests/test_integration.py --timeout=120 2>&1 | tail -10
```

Expected: same failure count as Task 1.4 baseline (≤17 known pre-existing). NO new failures.

**Step 6: Commit**

```bash
git add app/services/structured_comparison_service.py tests/test_stage_timings.py
git commit -m "feat(observability): DEBUG_STAGE_TIMINGS env-gated per-stage timing

Adds time.perf_counter() markers around the cold-cache pipeline stages
in _fetch_product_data() + compare_from_text(). When DEBUG_STAGE_TIMINGS=true,
response includes metadata.stage_timings_ms with per_product (unified_search_ms,
specs_ms, price_ms, reviews_ms, rating_ms) + orchestrator (scoring_ms,
verdict_ms, response_build_ms, total_ms).

Flag is read once at module-init via _debug_timings_enabled() cached call —
zero overhead in prod with flag off. Two tests assert presence with flag
on + strict absence with flag off (no observability leak).

Phase 2A of docs/plans/2026-05-17-comparison-speed-fixes-design.md."
```

---

### Task 2A.2: Deploy instrumentation, enable flag temporarily, bench

**Step 1: Push to Railway**

Run:
```bash
git push origin main
```

Wait for deploy. Verify:
```bash
curl -sS https://web-production-58776.up.railway.app/health
```

Expected: 200 OK.

**Step 2: Enable the flag via Railway CLI**

Run:
```bash
railway variables set DEBUG_STAGE_TIMINGS=true --service web
```

Expected: variable set message; Railway redeploys (~90s). Wait for `/health` to return 200 again.

**Step 3: Run 3 cold mainstream benches with timings**

Run each in series (NOT parallel — sequential gives cleaner timing):

```bash
for q in "iPhone+17+vs+Galaxy+S25+Ultra" "Centrum+Adults+vs+One+A+Day+Men" "Garnier+Micellar+Water+vs+Bioderma+Sensibio"; do
  echo "=== $q ==="
  curl -sS -o /tmp/timed_$RANDOM.json \
    -w "TIME=%{time_total}s\n" \
    "https://web-production-58776.up.railway.app/api/v1/text/compare?q=$q&region=bahrain&nocache=true" \
    --max-time 60
done
```

Save the output files. Will need them in Step 4.

**Step 4: Extract and report stage timings**

Run:
```bash
python -c "
import json, glob
files = sorted(glob.glob('/tmp/timed_*.json'))
print(f'{len(files)} bench files\n')
all_timings = []
for f in files:
    d = json.load(open(f))
    t = (d.get('metadata') or {}).get('stage_timings_ms') or {}
    if not t:
        print(f'{f}: NO TIMINGS (flag not effective?)'); continue
    print(f'--- {f} ---')
    print(f'  total_ms     = {t.get(\"total_ms\")}')
    print(f'  scoring_ms   = {t.get(\"scoring_ms\")}')
    print(f'  verdict_ms   = {t.get(\"verdict_ms\")}')
    print(f'  build_ms     = {t.get(\"response_build_ms\")}')
    for i, p in enumerate(t.get('per_product', [])):
        print(f'  product {i}: search={p.get(\"unified_search_ms\")} specs={p.get(\"specs_ms\")} price={p.get(\"price_ms\")} reviews={p.get(\"reviews_ms\")} rating={p.get(\"rating_ms\")}')
    all_timings.append(t)
print('\n=== p50 / p95 across 3 benches ===')
import statistics
def stats(key, items):
    vals = [x.get(key, 0) for x in items if x.get(key)]
    if not vals: return f'{key}: NONE'
    return f'{key}: p50={statistics.median(vals):.0f} max={max(vals):.0f}'
for k in ['total_ms', 'scoring_ms', 'verdict_ms', 'response_build_ms']:
    print('  ' + stats(k, all_timings))
"
```

Expected: prints 3 benches' breakdowns + a summary. The largest per-stage value is the D2 target.

**Step 5: Disable the flag (prod must NOT keep timing overhead)**

Run:
```bash
railway variables set DEBUG_STAGE_TIMINGS=false --service web
```

Wait for redeploy. Confirm:
```bash
curl -sS "https://web-production-58776.up.railway.app/api/v1/text/compare?q=iPhone+vs+Pixel&nocache=true" \
  --max-time 60 | python -c "
import json, sys
d = json.load(sys.stdin)
t = (d.get('metadata') or {}).get('stage_timings_ms')
assert t is None, f'stage_timings_ms still in response after flag off: {t}'
print('PASS — instrumentation correctly gated off')
"
```

Expected: `PASS — instrumentation correctly gated off`. If timings still present, the env var cache isn't being read at process restart — investigate `_debug_timings_enabled()` (likely needs to NOT cache, or Railway didn't redeploy).

**Step 6: Save the diagnostic data into the design doc**

Append a new section "## Phase 2A Diagnostic Results" to `docs/plans/2026-05-17-comparison-speed-fixes-design.md` with the per-stage p50/max numbers from Step 4.

Commit:
```bash
git add docs/plans/2026-05-17-comparison-speed-fixes-design.md
git commit -m "docs(plans): Phase 2A diagnostic data — per-stage cold-cache timings"
```

---

## ⏸️ STOP — Hand back to user with Phase 2A data

At this point, D1 has shipped and D2 has hard numbers. Before continuing, present the Phase 2A data to the user and brainstorm Section 3 (which fix to apply). DO NOT pick a fix unilaterally.

Suggested handback message:

> "D1 shipped at `<commit hash>`. LV vs Gucci now <X>s with real prices (was 85s, all `estimated`).
>
> Phase 2A data:
> - Mainstream cold p50 total: <X>s
> - Specs stage: <X>s
> - Reviews stage: <X>s
> - Verdict (gpt-4o): <X>s
> - Other: <X>s
>
> The bottleneck is **<stage>**. Three options for Section 3:
> 1. <data-appropriate option 1>
> 2. <data-appropriate option 2>
> 3. <data-appropriate option 3>
>
> Which?"

User picks → continue with Phase 2B/2C/2D as a follow-up plan appended here.

---

## Phases 2B / 2C / 2D — TBD (data-driven, written after Phase 2A)

These phases will be filled in as an addendum to this plan after Phase 2A returns numbers and the user approves Section 3 of the design doc. Stubs:

- **2B (design):** Pick ONE intervention from data-appropriate candidates, lock implementation contract.
- **2C (implement + test):** Write quality-regression tests against `tests/fixtures/comparison_baseline_d2.json` BEFORE writing the fix:
  - Spec key parity test (100%): no key in baseline may be absent post-fix.
  - Hard-spec value match: RAM, storage, battery mAh, processor — must equal baseline exactly.
  - Schema validation: response must validate against `CATEGORY_SPEC_SCHEMAS[category]`.
  - Review citation count: ±2 of baseline per product.
  - Scoring dimension presence: same dimension names returned.
  Then implement the fix to make all gates green. Then bench: 3 cold mainstream avg ≤20s, p95 ≤25s.
- **2D (verify + ship):** Push, wait for healthy, re-bench 5 cold queries (3 mainstream + 1 luxury + 1 supplement), assert combined Bucket D success criteria, rollback on any failure.

---

## Rollback playbook (applies to every deploy in this plan)

If any post-deploy bench or test fails:

```bash
git revert HEAD --no-edit
git push origin main
```

Wait for Railway redeploy. Verify `/health`. Re-run the failing bench to confirm pre-deploy behavior is restored.

If the failure is in Phase 2A (instrumentation), the env flag override is the lighter rollback:
```bash
railway variables set DEBUG_STAGE_TIMINGS=false --service web
```

If only the test suite went red post-commit but pre-push, no rollback needed — just `git reset --hard HEAD~1` locally and fix forward.
