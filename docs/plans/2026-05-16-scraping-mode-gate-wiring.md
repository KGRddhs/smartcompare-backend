# SCRAPING_MODE Gate Wiring Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make `SCRAPING_MODE=soft` actually short-circuit Firecrawl + Scrape.do for non-luxury URLs, completing the half-built wiring from Bundle E Task 2.4.

**Architecture:** Apply the existing (already-tested) `firecrawl_service.should_fan_out(url, mode)` URL classifier as a guard at the two live scraper call sites inside `_fetch_product_price` in `structured_comparison_service.py`. No pipeline refactor — just two `and` clauses added to existing if-conditions. Soft mode then skips Firecrawl/Scrape.do for non-luxury URLs even when they leak into the luxury cascade (e.g., Amazon UAE results inside Tier 1.5b).

**Tech Stack:** Python 3.12 + FastAPI + pytest + monkeypatch + asyncio.

**Scope boundary:** This plan does **NOT** deliver the larger Bundle E "scatter-gather fan-out" refactor (Tasks 2.1–2.3, 2.5 of `docs/plans/2026-05-13-results-quality-overhaul.md`). Those tasks would replace the entire sequential Tier 1 → 1.5 → 2 → 3 cascade with a parallel-race coordinator using the already-defined `fan_out_price_lookup()`. The latency win from that refactor is real (~10-15s on cold-cache comparisons), but it's a 2-3 day effort and out of scope here. This plan delivers credit conservation only — measured wins: ~0-3 saved Firecrawl/Scrape.do calls per ambiguous-domain luxury comparison. Latency impact is small (~2-5s per saved Firecrawl 30s timeout on flaky pages).

**Why ship this small piece anyway:**
1. Closes a half-built feature (gate function exists, never called) — reduces "dead code in main" debt
2. Makes `SCRAPING_MODE=soft` a real lever for App Store launch credit budgeting
3. ~50 lines + 4 tests — couple-hour task, not blocking on Bundle E refactor

---

## Context

`firecrawl_service.should_fan_out(url, mode)` was added in Bundle E (Session 47). It reads `SCRAPING_MODE` env var and returns `True` for hard mode (default) or for luxury-domain URLs in soft mode. It is **defined in `app/services/firecrawl_service.py:165` but called from nowhere in `app/`**. Verify before starting:

```bash
grep -rn "should_fan_out" app/
```

Expected output: only one match, the definition at `firecrawl_service.py:165`. If any other call sites exist, stop and re-read this plan against actual state.

The two call sites where Firecrawl + Scrape.do fire today inside `_fetch_product_price()`:

| Line | Service | Current guard | Add |
|---|---|---|---|
| `structured_comparison_service.py:1119` | Firecrawl | `firecrawl_service.is_available() and is_circuit_closed("firecrawl") and has_budget("firecrawl")` | `and should_fan_out(page_url)` |
| `structured_comparison_service.py:1222-1240` (per-URL loop) | Scrape.do | Inside loop, after `validate_scrape_url(retry_url)` | `if not should_fan_out(retry_url): continue` |

The whole Tier 1.5 block is already brand-gated by `is_luxury_brand(full_name) and ENABLE_PAGE_SCRAPE` at line 1102, so non-luxury products never reach these scrapers regardless. The gate adds URL-level precision *inside* the luxury cascade.

---

## Task 1: Wire `should_fan_out()` into Firecrawl call site

**Files:**
- Modify: `app/services/structured_comparison_service.py:1119`
- Test: `tests/test_scraping_mode_integration.py` (new)

**Step 1.1: Write the failing test**

Create `tests/test_scraping_mode_integration.py`:

```python
"""Integration tests for SCRAPING_MODE gate at live scraper call sites.

Plan: docs/plans/2026-05-16-scraping-mode-gate-wiring.md
"""

import os
from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_firecrawl_skipped_for_non_luxury_url_in_soft_mode(monkeypatch):
    """In soft mode, Firecrawl must NOT fire for non-luxury URLs even
    inside the luxury Tier 1.5a cascade."""
    monkeypatch.setenv("SCRAPING_MODE", "soft")
    monkeypatch.setenv("ENABLE_PAGE_SCRAPE", "true")

    # Force the Tier 1.5a path: luxury BRAND name, but Serper returns a
    # non-luxury retailer URL (e.g., amazon.ae) as the organic result.
    with patch("app.services.structured_comparison_service.search_web", new=AsyncMock(
        return_value={"organic": [{"link": "https://www.amazon.ae/dp/B0CHX1W1XY"}]}
    )), patch("app.services.firecrawl_service.is_available", return_value=True), \
         patch("app.services.firecrawl_service.scrape_page_with_status", new=AsyncMock()) as mock_fc, \
         patch("app.services.structured_comparison_service.is_circuit_closed", return_value=True), \
         patch("app.services.structured_comparison_service.has_budget", return_value=True), \
         patch("app.services.structured_comparison_service.is_luxury_brand", return_value=True), \
         patch("app.services.structured_comparison_service.get_official_domain", return_value="amazon.ae"), \
         patch("app.services.structured_comparison_service.fetch_page_price", new=AsyncMock(return_value=None)), \
         patch("app.services.structured_comparison_service.fetch_shopping_data", new=AsyncMock(return_value=[])), \
         patch("app.services.structured_comparison_service.get_cached", return_value=None):

        from app.services.structured_comparison_service import get_comparison_service
        svc = get_comparison_service()
        svc._shopping_items_cache = {}
        # Brand=Gucci forces is_luxury_brand=True; URL is non-luxury (amazon.ae).
        await svc._fetch_product_price(
            brand="Gucci", name="Marmont Bag", variant=None,
            full_name="Gucci Marmont Bag", region="bahrain",
        )

    mock_fc.assert_not_called(), "Firecrawl must not fire for amazon.ae in soft mode"


@pytest.mark.asyncio
async def test_firecrawl_fires_for_luxury_url_in_soft_mode(monkeypatch):
    """In soft mode, Firecrawl MUST fire for luxury URLs (gucci.com)."""
    monkeypatch.setenv("SCRAPING_MODE", "soft")
    monkeypatch.setenv("ENABLE_PAGE_SCRAPE", "true")

    with patch("app.services.structured_comparison_service.search_web", new=AsyncMock(
        return_value={"organic": [{"link": "https://www.gucci.com/us/en/pr/marmont"}]}
    )), patch("app.services.firecrawl_service.is_available", return_value=True), \
         patch("app.services.firecrawl_service.scrape_page_with_status", new=AsyncMock(return_value=(None, 200))) as mock_fc, \
         patch("app.services.structured_comparison_service.is_circuit_closed", return_value=True), \
         patch("app.services.structured_comparison_service.has_budget", return_value=True), \
         patch("app.services.structured_comparison_service.is_luxury_brand", return_value=True), \
         patch("app.services.structured_comparison_service.get_official_domain", return_value="gucci.com"), \
         patch("app.services.structured_comparison_service.fetch_page_price", new=AsyncMock(return_value=None)), \
         patch("app.services.structured_comparison_service.fetch_shopping_data", new=AsyncMock(return_value=[])), \
         patch("app.services.structured_comparison_service.get_cached", return_value=None):

        from app.services.structured_comparison_service import get_comparison_service
        svc = get_comparison_service()
        svc._shopping_items_cache = {}
        await svc._fetch_product_price(
            brand="Gucci", name="Marmont Bag", variant=None,
            full_name="Gucci Marmont Bag", region="bahrain",
        )

    mock_fc.assert_called_once(), "Firecrawl must fire for gucci.com in soft mode"
```

**Step 1.2: Verify it fails**

```bash
python -m pytest tests/test_scraping_mode_integration.py::test_firecrawl_skipped_for_non_luxury_url_in_soft_mode -v
```

Expected: **FAIL** with `AssertionError: Firecrawl must not fire for amazon.ae in soft mode` (because the gate isn't wired yet — Firecrawl fires today regardless of URL).

**Step 1.3: Add `should_fan_out` import**

In `app/services/structured_comparison_service.py`, find the existing `from app.services import firecrawl_service, scrapedo_service` import (line 43). No new import needed — `firecrawl_service.should_fan_out` is already accessible via the module import.

**Step 1.4: Add the gate at line 1119**

Replace:

```python
if firecrawl_service.is_available() and is_circuit_closed("firecrawl") and has_budget("firecrawl"):
```

With:

```python
if (firecrawl_service.is_available()
        and firecrawl_service.should_fan_out(page_url)
        and is_circuit_closed("firecrawl")
        and has_budget("firecrawl")):
```

**Step 1.5: Verify Task 1 tests pass**

```bash
python -m pytest tests/test_scraping_mode_integration.py -v -k firecrawl
```

Expected: both `test_firecrawl_skipped_for_non_luxury_url_in_soft_mode` and `test_firecrawl_fires_for_luxury_url_in_soft_mode` → **PASS**.

**Step 1.6: Run regression suite**

```bash
python -m pytest tests/test_scraping_mode.py tests/test_structured_comparison.py tests/test_price_service.py -v
```

Expected: no new failures relative to the pre-edit baseline. (Pre-existing flaky tests stay pre-existing.)

**Step 1.7: Commit**

```bash
git add app/services/structured_comparison_service.py tests/test_scraping_mode_integration.py docs/plans/2026-05-16-scraping-mode-gate-wiring.md
git commit -m "feat(scraping): gate Firecrawl by SCRAPING_MODE soft/hard at Tier 1.5a call site

Completes half of Bundle E Task 2.4 — wires the existing
firecrawl_service.should_fan_out(url) classifier into the live
Tier 1.5a Firecrawl call in _fetch_product_price. Non-luxury URLs
inside the luxury cascade now skip Firecrawl in SCRAPING_MODE=soft.

Default mode unchanged (hard = fan out everything).

Scrape.do call site gated next (Task 2 of plan)."
```

---

## Task 2: Wire `should_fan_out()` into Scrape.do call site

**Files:**
- Modify: `app/services/structured_comparison_service.py:1222` (inside the per-URL loop)
- Test: `tests/test_scraping_mode_integration.py` (extend)

**Step 2.1: Write the failing test**

Append to `tests/test_scraping_mode_integration.py`:

```python
@pytest.mark.asyncio
async def test_scrapedo_skipped_for_non_luxury_url_in_soft_mode(monkeypatch):
    """In soft mode, Scrape.do (Tier 1.5d) must NOT fire for non-luxury
    URLs even when curl scraping left them in failed_curl_urls."""
    monkeypatch.setenv("SCRAPING_MODE", "soft")
    monkeypatch.setenv("ENABLE_PAGE_SCRAPE", "true")

    # _got_html signal triggers Scrape.do retry; URL is non-luxury.
    failed_curl_html_marker = {"_got_html": True, "amount": None}

    with patch("app.services.structured_comparison_service.search_web", new=AsyncMock(
        return_value={"organic": [{"link": "https://www.amazon.ae/dp/B0CHX1W1XY"}]}
    )), patch("app.services.scrapedo_service.is_available", return_value=True), \
         patch("app.services.scrapedo_service.render_page_with_status", new=AsyncMock()) as mock_sd, \
         patch("app.services.structured_comparison_service.is_circuit_closed", return_value=True), \
         patch("app.services.structured_comparison_service.has_budget", return_value=True), \
         patch("app.services.structured_comparison_service.is_luxury_brand", return_value=True), \
         patch("app.services.structured_comparison_service.get_official_domain", return_value=None), \
         patch("app.services.structured_comparison_service.fetch_page_price",
               new=AsyncMock(return_value=failed_curl_html_marker)), \
         patch("app.services.structured_comparison_service.fetch_shopping_data", new=AsyncMock(return_value=[])), \
         patch("app.services.structured_comparison_service.get_cached", return_value=None):

        from app.services.structured_comparison_service import get_comparison_service
        svc = get_comparison_service()
        svc._shopping_items_cache = {}
        await svc._fetch_product_price(
            brand="Gucci", name="Marmont Bag", variant=None,
            full_name="Gucci Marmont Bag", region="bahrain",
        )

    mock_sd.assert_not_called(), "Scrape.do must not fire for amazon.ae in soft mode"
```

**Step 2.2: Verify it fails**

```bash
python -m pytest tests/test_scraping_mode_integration.py::test_scrapedo_skipped_for_non_luxury_url_in_soft_mode -v
```

Expected: **FAIL** with `AssertionError: Scrape.do must not fire for amazon.ae in soft mode`.

**Step 2.3: Add the gate inside the per-URL loop**

In `app/services/structured_comparison_service.py`, find the Scrape.do retry loop starting around line 1222:

```python
for retry_url in sorted_urls[:2]:
    if not validate_scrape_url(retry_url):
        continue
    retry_domain = urlparse(retry_url).netloc.replace("www.", "")
    html, status = await scrapedo_service.render_page_with_status(retry_url)
```

Insert one line **after** the `validate_scrape_url` check and **before** the `render_page_with_status` call:

```python
for retry_url in sorted_urls[:2]:
    if not validate_scrape_url(retry_url):
        continue
    if not firecrawl_service.should_fan_out(retry_url):
        continue
    retry_domain = urlparse(retry_url).netloc.replace("www.", "")
    html, status = await scrapedo_service.render_page_with_status(retry_url)
```

(Yes, the gate function lives in `firecrawl_service` but applies to both Firecrawl and Scrape.do — its name is about classification, not vendor. Bundle E's design line 451 + 452 both reference the same classifier.)

**Step 2.4: Verify Task 2 test passes**

```bash
python -m pytest tests/test_scraping_mode_integration.py::test_scrapedo_skipped_for_non_luxury_url_in_soft_mode -v
```

Expected: **PASS**.

**Step 2.5: Run regression suite**

```bash
python -m pytest tests/test_scraping_mode.py tests/test_scraping_mode_integration.py tests/test_structured_comparison.py tests/test_price_service.py -v
```

Expected: all pass.

**Step 2.6: Commit**

```bash
git add app/services/structured_comparison_service.py tests/test_scraping_mode_integration.py
git commit -m "feat(scraping): gate Scrape.do by SCRAPING_MODE soft/hard at Tier 1.5d call site

Completes Bundle E Task 2.4 gate wiring. Scrape.do per-URL retry loop
now skips non-luxury URLs in SCRAPING_MODE=soft (e.g., Amazon UAE
results that leak into the luxury cascade).

Default mode unchanged (hard = retry every failed_curl_url)."
```

---

## Task 3: Update CLAUDE.md to reflect that SCRAPING_MODE is now functional

**Files:**
- Modify: `CLAUDE.md` (the Bundle F priority breadcrumb)

**Step 3.1: Find the Bundle F priority line**

```bash
grep -n "SCRAPING_MODE=soft" CLAUDE.md
```

Expected: one match, line says `Bundle F headline priority is **`SCRAPING_MODE=soft` on Railway**...`

**Step 3.2: Edit the breadcrumb**

Replace the existing Bundle F sentence (single line) with a one-line note saying the gate is wired but the full scatter-gather refactor (Bundle E Task 2.1-2.3) is still outstanding. Specifically:

Before:
```
Bundle F headline priority is **`SCRAPING_MODE=soft` on Railway** (drops cold-cache non-luxury comparison from ~51s → ~10-15s).
```

After:
```
`SCRAPING_MODE=soft` gate is wired (skips Firecrawl/Scrape.do for non-luxury URLs inside Tier 1.5). Bundle F priority remains the scatter-gather pipeline refactor (Bundle E Tasks 2.1-2.3) — only that delivers the ~51s → ~10-15s cold-cache win.
```

**Step 3.3: Commit**

```bash
git add CLAUDE.md
git commit -m "docs(claude.md): note SCRAPING_MODE gate is wired; Bundle F still owes scatter-gather"
```

---

## Task 4: Verify on Railway preview environment

**Step 4.1: Push the branch**

```bash
git push origin main
```

Railway auto-deploys in ~90s.

**Step 4.2: Wait for deploy to succeed**

```bash
until [ "$(railway status --json | python -c 'import sys,json; print(json.load(sys.stdin)["environments"]["edges"][0]["node"]["serviceInstances"]["edges"][0]["node"]["latestDeployment"]["status"])')" = "SUCCESS" ]; do sleep 10; done
```

**Step 4.3: Set SCRAPING_MODE=soft as a one-shot env override on the next request**

The gate function reads `os.environ.get("SCRAPING_MODE", "hard")` at request time, not at boot. So we can flip it via Railway and the very next request picks it up:

```bash
railway variables --set SCRAPING_MODE=soft
```

Railway will redeploy because env-var changes redeploy by default. Wait again:

```bash
until [ "$(railway status --json | python -c 'import sys,json; print(json.load(sys.stdin)["environments"]["edges"][0]["node"]["serviceInstances"]["edges"][0]["node"]["latestDeployment"]["status"])')" = "SUCCESS" ]; do sleep 10; done
```

**Step 4.4: Run a luxury cold-cache comparison and confirm logs**

```bash
curl -s -o /dev/null -w "%{time_total}s HTTP %{http_code}\n" \
  "https://web-production-58776.up.railway.app/api/v1/text/compare?q=Gucci+Marmont+vs+Prada+Galleria&nocache=true" -m 120
railway logs --deployment | grep -iE "firecrawl|scrapedo|tier.1\.5" | tail -30
```

Expected: Firecrawl and Scrape.do log lines appear only for `gucci.com` / `prada.com` / `ounass.*` / `bloomingdales.*` URLs. No Firecrawl/Scrape.do log lines for amazon, namshi, noon, etc.

**Step 4.5: Run a non-luxury comparison as a control**

```bash
curl -s -o /dev/null -w "%{time_total}s HTTP %{http_code}\n" \
  "https://web-production-58776.up.railway.app/api/v1/text/compare?q=iPhone+15+vs+Galaxy+S24&nocache=true" -m 120
railway logs --deployment | grep -iE "firecrawl|scrapedo" | tail -10
```

Expected: zero Firecrawl/Scrape.do log lines (Tier 1.5 already brand-gated; soft mode doesn't change this case).

**Step 4.6: Decide on production rollout**

If both comparisons succeed and return reasonable prices for both products, leave `SCRAPING_MODE=soft` set. If either degrades (luxury price quality drops, or comparison fails), roll back:

```bash
railway variables --set SCRAPING_MODE=hard
```

---

## Notes on the larger Bundle E refactor (out of scope here)

`fan_out_price_lookup()` exists in `app/services/price_service.py:980` but no call site exists. It implements the parallel-race coordinator with cancel-on-confirmed-price semantics that the design doc calls for. To actually deliver the ~51s → ~10-15s cold-cache latency win, the next plan should:

1. **Refactor `_fetch_product_price`** in `structured_comparison_service.py` to build a `scrapers: List[Callable]` list (curl, page-scrape, Firecrawl, Scrape.do, GPT estimate) and hand it to `fan_out_price_lookup`.
2. **Replace the sequential Tier 1 → 1.5 → 2 → 3 cascade** with a single parallel-race block per product.
3. **Add settle-window logic** in `compare_from_text_streaming`: emit `first_paint` SSE at 13s with whatever's settled, continue running scrapers up to 25s hard cap, emit `settle_update` / `confidence_upgrade` events as better prices arrive.
4. **New SSE event types** wired through `text_routes.py` and frontend `streamComparison()`.

That refactor was Bundle E Task 2.1-2.3 + 2.5 — dispatcher-absorbed but never finished (per CLAUDE.md Session 47 note). Estimate: 2-3 days with the same TDD discipline. Reference: `docs/plans/2026-05-13-results-quality-overhaul.md` (already written) + `docs/plans/2026-05-13-results-quality-overhaul-design.md` (design § Decision 8).

---

## Done criteria

- [ ] Task 1 + Task 2 tests pass: `python -m pytest tests/test_scraping_mode_integration.py -v`
- [ ] No regressions: `python -m pytest tests/ -m "not (live_unit or live_db or integration)" --ignore=tests/test_integration.py`
- [ ] CLAUDE.md breadcrumb updated
- [ ] Production verified: `SCRAPING_MODE=soft` set on Railway, luxury vs non-luxury comparisons both succeed, log lines confirm the gate is firing
- [ ] If anything degrades: roll back to `SCRAPING_MODE=hard` and document the failure mode in a new plan
