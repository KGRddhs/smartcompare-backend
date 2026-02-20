# Fix Rating & Price Links — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Use actual product page URLs from Serper Shopping `link` field for both rating source and price links, falling back to retailer search URLs when unavailable.

**Architecture:** The Serper Shopping API already returns a `link` field containing the direct retailer product page URL. This data flows through `_shopping_items_cache` but is currently discarded. We pass it through the price and rating extraction pipelines and fix the frontend to use it.

**Tech Stack:** Python (FastAPI backend), TypeScript (React Native frontend)

---

### Task 1: Backend — Use Serper `link` in price extraction

**Files:**
- Modify: `app/services/structured_comparison_service.py:1046`

**Step 1: Edit price candidate URL**

In `_extract_price_from_shopping()`, change line 1046 from:
```python
"url": self._build_retailer_url(retailer, product_name),
```
to:
```python
"url": item.get("link") or self._build_retailer_url(retailer, product_name),
```

This uses the Serper Shopping direct product URL when available, falling back to the retailer search page.

**Step 2: Syntax check**

Run: `python -m py_compile app/services/structured_comparison_service.py`
Expected: No output (clean compile)

**Step 3: Commit**

```bash
git add app/services/structured_comparison_service.py
git commit -m "Use Serper Shopping link for price URLs (fallback to search page)"
```

---

### Task 2: Backend — Use Serper `link` in rating extraction

**Files:**
- Modify: `app/services/structured_comparison_service.py:1601-1607, 1645, 1691`

**Step 1: Add `link` to rating candidates**

In `_extract_rating_from_shopping()`, change the candidate dict at line 1601 from:
```python
            candidate = {
                "rating": rating_val,
                "review_count": review_count,
                "source": source,
                "title": title,
                "match_score": match_score,
            }
```
to:
```python
            candidate = {
                "rating": rating_val,
                "review_count": review_count,
                "source": source,
                "link": item.get("link"),
                "title": title,
                "match_score": match_score,
            }
```

**Step 2: Use `link` in consensus rating URL**

At line 1645, change:
```python
                        "url": self._build_retailer_url(best["source"], product_name),
```
to:
```python
                        "url": best.get("link") or self._build_retailer_url(best["source"], product_name),
```

**Step 3: Use `link` in tiered rating URL**

At line 1691, change:
```python
                "url": self._build_retailer_url(best["source"], product_name),
```
to:
```python
                "url": best.get("link") or self._build_retailer_url(best["source"], product_name),
```

**Step 4: Syntax check**

Run: `python -m py_compile app/services/structured_comparison_service.py`
Expected: No output (clean compile)

**Step 5: Commit**

```bash
git add app/services/structured_comparison_service.py
git commit -m "Use Serper Shopping link for rating source URLs (fallback to search page)"
```

---

### Task 3: Frontend — Fix `openRatingSource()` to use backend URL

**Files:**
- Modify: `SmartCompareApp/src/screens/ResultsScreen.tsx:182-192`

**Step 1: Fix `openRatingSource`**

Change lines 182-192 from:
```tsx
  const openRatingSource = (source: RatingSource | null | undefined, product?: Product) => {
    // Build a clean Google Shopping search URL instead of using the
    // internal redirect URL which crashes Chrome on Android
    const productName = product?.full_name || product?.name || '';
    if (productName) {
      const query = encodeURIComponent(productName);
      Linking.openURL(`https://www.google.com/search?q=${query}&tbm=shop`);
    } else if (source?.url) {
      Linking.openURL(source.url);
    }
  };
```
to:
```tsx
  const openRatingSource = (source: RatingSource | null | undefined, product?: Product) => {
    // Prefer actual product page URL from backend (Serper Shopping link)
    // Fall back to Google Shopping search if no URL available
    if (source?.url) {
      Linking.openURL(source.url);
    } else {
      const productName = product?.full_name || product?.name || '';
      if (productName) {
        const query = encodeURIComponent(productName);
        Linking.openURL(`https://www.google.com/search?q=${query}&tbm=shop`);
      }
    }
  };
```

**Step 2: Add missing extract methods to `getMethodLabel` and `getConfidenceColor`**

Change `getConfidenceColor` (lines 236-241) from:
```tsx
    const getConfidenceColor = () => {
      if (rating_source?.extract_method === 'google_shopping') return '#4CAF50'; // High
      if (rating_source?.extract_method === 'json_ld') return '#4CAF50'; // High
      if (rating_source?.extract_method === 'microdata') return '#4CAF50'; // High
      return '#FFC107'; // Medium
    };
```
to:
```tsx
    const getConfidenceColor = () => {
      if (rating_source?.extract_method === 'google_shopping') return '#4CAF50';
      if (rating_source?.extract_method === 'google_shopping_consensus') return '#4CAF50';
      if (rating_source?.extract_method === 'json_ld') return '#4CAF50';
      if (rating_source?.extract_method === 'microdata') return '#4CAF50';
      if (rating_source?.extract_method === 'gpt_review_aggregate') return '#9E9E9E';
      return '#FFC107';
    };
```

Change `getMethodLabel` (lines 243-252) from:
```tsx
    const getMethodLabel = () => {
      switch (rating_source?.extract_method) {
        case 'google_shopping': return 'Verified';
        case 'json_ld': return 'Verified';
        case 'microdata': return 'Verified';
        case 'meta_tags': return 'Extracted';
        case 'css_selector': return 'Parsed';
        default: return 'Verified';
      }
    };
```
to:
```tsx
    const getMethodLabel = () => {
      switch (rating_source?.extract_method) {
        case 'google_shopping': return 'Verified';
        case 'google_shopping_consensus': return 'Verified';
        case 'json_ld': return 'Verified';
        case 'microdata': return 'Verified';
        case 'meta_tags': return 'Extracted';
        case 'css_selector': return 'Parsed';
        case 'gpt_review_aggregate': return 'Unverified';
        default: return 'Verified';
      }
    };
```

**Step 3: TypeScript check**

Run: `cd SmartCompareApp && npx tsc --noEmit`
Expected: Pre-existing errors only (7 as of Feb 18), no new errors

**Step 4: Commit**

```bash
git add SmartCompareApp/src/screens/ResultsScreen.tsx
git commit -m "Fix rating links: use backend URL instead of Google Shopping search"
```

---

### Task 4: Fix MEMORY.md — Correct Serper Shopping `link` documentation

**Files:**
- Modify: `C:\Users\SynAckITPC\.claude\projects\C--Users-SynAckITPC-Documents-AI-smartcompare\memory\MEMORY.md`

**Step 1: Update the Key APIs section**

Change:
```
- Serper Shopping: returns `rating`, `ratingCount` per item — `link` field is Google redirect, NOT retailer URL
```
to:
```
- Serper Shopping: returns `rating`, `ratingCount` per item — `link` field is direct retailer product page URL (NOT a Google redirect)
```

**Step 2: Commit** (skip — memory files are not in git)

---

### Task 5: Deploy and verify

**Step 1: Push to Railway**

```bash
git push origin main
```
Wait ~90s for Railway auto-deploy.

**Step 2: Health check**

Run: `curl https://smartcompare-backend-production.up.railway.app/health`
Expected: `{"status":"healthy"}`

**Step 3: Test supplement comparison**

Run: `curl -s "https://smartcompare-backend-production.up.railway.app/api/v1/text/compare?q=NOW+D3+vs+HealthAid+D3&nocache=true" -o response_links_verify.json`

Inspect with `extract_links.py`. Verify:
- NOW D3 price URL: should be an iHerb product page (already working) or Serper Shopping product URL
- NOW D3 rating URL: should be a Walmart/Amazon product page URL (not `walmart.com/search?q=...`)
- HealthAid D3: may still have null URLs (limited shopping data) — acceptable

**Step 4: Test electronics comparison**

Run: `curl -s "https://smartcompare-backend-production.up.railway.app/api/v1/text/compare?q=iPhone+16+vs+Galaxy+S25&nocache=true" -o response_links_verify2.json`

Verify:
- iPhone 16 price URL: should be a direct product page URL (not `sharafdg.com/search?q=...`)
- iPhone 16 rating URL: should be a direct product page URL (not `apple.com/shop/buy?fh=...`)
- Galaxy S25 price URL: should have a direct URL (not Google Shopping search)
- Galaxy S25 rating URL: should be a direct product page URL (not `bestbuy.com/site/searchpage.jsp?st=...`)

**Step 5: Verify fallback behavior**

Check that products with no Serper Shopping `link` (e.g., HealthAid D3 from fruugo.com) still get a retailer search URL or Google Shopping fallback — not null.

---

### Task 6: Cleanup

**Step 1: Remove temp files**

Delete `extract_links.py`, `response_links_test.json`, `response_links_elec.json`, `response_links_verify.json`, `response_links_verify2.json`.
