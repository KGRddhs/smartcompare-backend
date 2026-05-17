# Bucket A Bugs Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix 4 user-visible bugs (history empty / camera Compare silent / asymmetric specs / currency SGD-as-BHD) so the app stops feeling broken, without regressing the post-D1 wall-time baseline.

**Architecture:** All 4 fixes are independent and can ship in parallel commits. Bug 4 (currency) is pure backend data + helper additions. Bug 1 (history) and Bug 2 (camera) extend `ResultsScreen.tsx`'s mount-time useEffect to detect new param shapes (`comparison_id`, `vision_products`) and fetch/identify on demand. Bug 3 (asymmetric specs) rewrites the contradictory extraction prompt + adds field-confidence tracking + adds smart-fallback Serper queries that run in **parallel** with the existing Phase 2 reviews+rating gather (zero added wall time within a 3s cap).

**Tech Stack:** Python 3.12 / FastAPI / asyncio / pytest (backend). React Native + Expo / TypeScript / React Navigation 7 (frontend). Railway auto-deploys on `git push origin main`. Upstash Redis for cache.

**Design source:** `docs/plans/2026-05-17-bucket-a-bugs-design.md` (committed `da67530`).

---

## Sequencing rationale

Bug 4 first (trivial, builds Railway confidence after each push). Then Bug 1 (small, frontend-only, well-defined). Then Bug 2 (medium frontend, mirrors Bug 1's mount-detection pattern). Then Bug 3 (medium backend, last so the spec-parity fixture at `tests/fixtures/comparison_baseline_d2.json` proves nothing else regressed).

---

# Bug 4 — Currency (SGD-as-BHD + missing source currencies)

## Task 4.1: Add missing source currencies to FALLBACK_RATES

**Files:**
- Modify: `app/services/exchange_rate_service.py:18-28`
- Test: `tests/test_exchange_rate_service.py` (create if missing)

**Step 1: Write the failing test**

Check if file exists; if not, create it. Then either way, add this test:

```python
"""Exchange rate service — fallback rates cover all source currencies seen in scraped data."""
import pytest

from app.services.exchange_rate_service import FALLBACK_RATES, _fallback_rate


REQUIRED_SOURCE_CURRENCIES = ["USD", "EUR", "GBP", "SGD", "JPY", "CNY", "INR"]
GCC_TARGET_CURRENCIES = ["BHD", "SAR", "AED", "KWD", "QAR", "OMR"]


def test_fallback_rates_cover_all_source_currencies():
    """Every currency we've seen in scraped data must have a fallback rate."""
    missing = [c for c in REQUIRED_SOURCE_CURRENCIES if c not in FALLBACK_RATES]
    assert not missing, f"FALLBACK_RATES missing source currencies: {missing}"


def test_fallback_rates_cover_all_gcc_targets():
    """All 6 GCC region currencies must be in the table."""
    missing = [c for c in GCC_TARGET_CURRENCIES if c not in FALLBACK_RATES]
    assert not missing, f"FALLBACK_RATES missing GCC target currencies: {missing}"


def test_sgd_to_bhd_in_reasonable_range():
    """SGD→BHD rate must be ~0.27-0.30 (1 SGD ≈ 0.28 BHD as of 2026-05)."""
    rate = _fallback_rate("SGD", "BHD")
    assert 0.25 <= rate <= 0.32, f"SGD→BHD rate {rate} outside plausible band"


def test_jpy_to_bhd_in_reasonable_range():
    """JPY→BHD rate must be ~0.002-0.003."""
    rate = _fallback_rate("JPY", "BHD")
    assert 0.002 <= rate <= 0.004, f"JPY→BHD rate {rate} outside plausible band"
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_exchange_rate_service.py -v --timeout=10`
Expected: `test_fallback_rates_cover_all_source_currencies FAILED — missing: ['SGD', 'JPY', 'CNY', 'INR']`. The other tests also fail with rate=1.0.

**Step 3: Add missing currencies to FALLBACK_RATES**

In `app/services/exchange_rate_service.py`, find the `FALLBACK_RATES` dict at line 18. Add these entries (alphabetically sorted alongside existing):

```python
FALLBACK_RATES: Dict[str, float] = {
    "USD": 0.376,
    "EUR": 0.41,
    "GBP": 0.475,
    "SGD": 0.282,    # NEW — 1 SGD = 0.282 BHD (as of 2026-05)
    "JPY": 0.0025,   # NEW
    "CNY": 0.052,    # NEW
    "INR": 0.0045,   # NEW
    "SAR": 0.1003,
    "AED": 0.1024,
    "KWD": 1.23,
    "QAR": 0.1033,
    "OMR": 0.977,
    "BHD": 1.0,
}
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_exchange_rate_service.py -v --timeout=10`
Expected: `4 passed`.

**Step 5: Commit**

```bash
git add app/services/exchange_rate_service.py tests/test_exchange_rate_service.py
git commit -m "$(cat <<'EOF'
fix(currency): add SGD/JPY/CNY/INR to FALLBACK_RATES (Bucket A bug 4)

LV/Gucci luxury bench surfaced prices of 2998/3050 BHD that were
actually SGD values from Farfetch Singapore (log: 'SGD 2998.0 ->
BHD 2998.0' — rate of 1.0 because SGD was missing from the
fallback rate table). Adding SGD + 3 other commonly-scraped
currencies (JPY, CNY, INR) closes the silent-conversion-failure
hole for non-listed sources.

Tests: tests/test_exchange_rate_service.py — 4 new tests asserting
required source currencies + GCC target currencies are all present,
plus plausibility-band checks for SGD and JPY rates.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 4.2: Region-aware currency conversion + strict-fail when rate missing

**Files:**
- Modify: `app/services/price_service.py:203-211` (`_convert_to_bhd` helper)
- Add: `app/services/exchange_rate_service.py` — `REGION_TO_CURRENCY` constant + `get_region_currency` helper
- Test: `tests/test_price_service.py` (add tests, file may already exist)

**Step 1: Write the failing tests**

In `tests/test_price_service.py` (create if missing or append):

```python
"""Bucket A bug 4 — region-aware conversion + strict-fail on missing rate."""
import pytest
from unittest.mock import patch

from app.services.exchange_rate_service import get_region_currency, REGION_TO_CURRENCY


def test_region_to_currency_covers_all_gcc_regions():
    """All 6 GCC regions must map to their native currency."""
    expected = {
        "bahrain": "BHD",
        "saudi_arabia": "SAR",
        "uae": "AED",
        "kuwait": "KWD",
        "qatar": "QAR",
        "oman": "OMR",
    }
    for region, currency in expected.items():
        assert REGION_TO_CURRENCY[region] == currency, \
            f"{region} should map to {currency}, got {REGION_TO_CURRENCY.get(region)}"


def test_get_region_currency_defaults_to_bhd_on_unknown():
    """Unknown region falls back to BHD (Bahrain-first behaviour)."""
    assert get_region_currency("antarctica") == "BHD"
    assert get_region_currency(None) == "BHD"
    assert get_region_currency("") == "BHD"


def test_get_region_currency_returns_native_for_known():
    """Known region returns the GCC-native currency."""
    assert get_region_currency("bahrain") == "BHD"
    assert get_region_currency("uae") == "AED"
    assert get_region_currency("saudi_arabia") == "SAR"
```

**Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_price_service.py -v -k "region_currency" --timeout=10`
Expected: 3 tests FAIL with `ImportError: cannot import name 'get_region_currency'` or similar.

**Step 3: Add the helper + constant to exchange_rate_service.py**

In `app/services/exchange_rate_service.py`, add AFTER `FALLBACK_RATES`:

```python
# Maps backend region codes to their native currency.
# Used by price pipeline to display prices in the user's region currency.
REGION_TO_CURRENCY: Dict[str, str] = {
    "bahrain": "BHD",
    "saudi_arabia": "SAR",
    "uae": "AED",
    "kuwait": "KWD",
    "qatar": "QAR",
    "oman": "OMR",
}


def get_region_currency(region: Optional[str]) -> str:
    """Return native currency for a GCC region. Defaults to BHD."""
    if not region:
        return "BHD"
    return REGION_TO_CURRENCY.get(region.lower(), "BHD")
```

**Step 4: Run the region-currency tests — expect PASS**

Run: `python -m pytest tests/test_price_service.py -v -k "region_currency" --timeout=10`
Expected: `3 passed`.

**Step 5: Write the strict-fail conversion test**

Add to `tests/test_price_service.py`:

```python
from app.services.price_service import _convert_to_bhd


def test_convert_to_bhd_unknown_currency_logs_warning(caplog):
    """Unknown currency must log a warning, not silently return same number."""
    import logging
    caplog.set_level(logging.WARNING)

    # XYZ is not in any rate table — should fall back to 1.0 BUT log warning
    result = _convert_to_bhd(1000.0, "XYZ")

    # The existing behaviour returns 1.0 silently; new behaviour must warn
    warned = any("XYZ" in record.message and "no rate" in record.message.lower()
                 for record in caplog.records)
    assert warned, f"Expected WARNING about missing XYZ rate. Records: {[r.message for r in caplog.records]}"


def test_convert_to_bhd_sgd_converts_correctly():
    """SGD must convert to ~28% of input value when going to BHD."""
    result = _convert_to_bhd(1000.0, "SGD")
    assert 270 <= result <= 295, \
        f"SGD 1000 → BHD should be ~282, got {result}"
```

**Step 6: Run the convert tests — expect SGD test to PASS (from Task 4.1) and warning test to FAIL**

Run: `python -m pytest tests/test_price_service.py -v -k "convert_to_bhd" --timeout=10`
Expected: `test_convert_to_bhd_sgd_converts_correctly PASSED` (rate added in Task 4.1), `test_convert_to_bhd_unknown_currency_logs_warning FAILED` (no warning yet).

**Step 7: Add warning + use FALLBACK_RATES from exchange_rate_service in `_convert_to_bhd`**

In `app/services/price_service.py:203-211`, REPLACE the function body:

```python
def _convert_to_bhd(amount: float, currency: str) -> float:
    """Convert amount to BHD using the central FALLBACK_RATES table.

    Logs a warning if the currency is not in the rate table — this prevents
    the silent-failure mode where unknown currencies were multiplied by 1.0
    and labelled BHD (e.g. SGD values displayed as BHD on luxury queries).
    """
    if not currency:
        return amount
    from app.services.exchange_rate_service import FALLBACK_RATES
    currency_upper = currency.upper()
    if currency_upper not in FALLBACK_RATES:
        logger.warning(
            f"[CURRENCY] No rate for {currency_upper}->BHD, returning amount unchanged. "
            f"Add {currency_upper} to FALLBACK_RATES to enable conversion."
        )
        return amount
    return amount * FALLBACK_RATES[currency_upper]
```

**Step 8: Run convert tests — expect PASS**

Run: `python -m pytest tests/test_price_service.py -v -k "convert_to_bhd" --timeout=10`
Expected: `2 passed`.

**Step 9: Run broader price_service tests for regressions**

Run: `python -m pytest tests/test_price_service.py -v --timeout=30 2>&1 | tail -10`
Expected: all pre-existing tests still pass (or matching same pre-existing failure count).

**Step 10: Commit**

```bash
git add app/services/exchange_rate_service.py app/services/price_service.py tests/test_price_service.py
git commit -m "$(cat <<'EOF'
fix(currency): region-aware conversion + warn on unknown currency (Bucket A bug 4)

Adds get_region_currency() + REGION_TO_CURRENCY mapping in
exchange_rate_service.py so price pipeline can target the user's
region native currency (BHD/SAR/AED/KWD/QAR/OMR) instead of
hardcoded BHD. Bahrain stays default for unknown regions.

Replaces price_service._convert_to_bhd's local hardcoded rates dict
with a lookup into the central exchange_rate_service.FALLBACK_RATES
table (single source of truth — fixes Task 4.1's currencies
automatically propagating). Unknown currencies now log a WARNING
instead of silently returning amount unchanged.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

# Bug 1 — History "No comparison loaded"

## Task 1.1: Backend — confirm /api/v1/comparisons/{id} returns full payload

**Files:**
- Read only: `app/api/history_routes.py`

**Step 1: Inspect the existing GET-by-id endpoint**

Run:
```bash
grep -nE "^@router|^async def" app/api/history_routes.py | head -30
```

Expected: an endpoint like `@router.get("/{comparison_id}")` exists. Read that endpoint and confirm:
- It accepts a comparison_id path param
- It returns the full payload including `specs`, `reviews`, `scoring`, `metadata` keys (NOT a summary)
- Ownership check (user can only retrieve their own comparisons) is in place
- Returns 404 on not found, 403 on someone else's comparison

If the endpoint already returns full payload: no backend changes needed for Bug 1 → proceed to Task 1.2.

If the endpoint is missing or returns summary only: add a new task here to add/expand it. Document what's missing.

**Step 2: (only if backend changes needed)** Add a test in `tests/test_history_routes.py` asserting GET-by-id returns full payload (≥6 top-level keys including `specs`, `scoring`, `metadata`). Skip this step if backend was already correct.

---

## Task 1.2: Frontend — add `getComparison(id)` to api.ts

**Files:**
- Modify: `SmartCompareApp/src/services/api.ts` (after line 187, near other history functions)

**Step 1: Add the API method**

Insert AFTER the existing `deleteComparison` function (around line 187):

```typescript
/**
 * Get a single comparison by ID with full payload.
 * Used by ResultsScreen when navigated from History with only an ID
 * (history list endpoint returns summary only — full_response is
 * fetched lazily on tap).
 */
export async function getComparison(comparisonId: string) {
  const response = await api.get(`/api/v1/comparisons/${comparisonId}`);
  return response.data;
}
```

**Step 2: Verify TypeScript compiles**

Run from `SmartCompareApp/`:
```bash
npx tsc --noEmit 2>&1 | tail -10
```

Expected: no new TypeScript errors. (Ignore any pre-existing errors — see CLAUDE.md note about LSP unreliability; the `tsc` exit code is the ground truth.)

**Step 3: Commit**

```bash
git add SmartCompareApp/src/services/api.ts
git commit -m "feat(api): add getComparison(id) for lazy history payload fetch (Bucket A bug 1)

Pairs with the upcoming ResultsScreen useEffect that detects
route.params.comparison_id and fetches the full payload on mount.
History list endpoint is intentionally summary-only for perf;
this enables the per-item drill-down without bloating the list.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 1.3: Frontend — HistoryScreen passes comparison_id instead of (null) full_response

**Files:**
- Modify: `SmartCompareApp/src/screens/HistoryScreen.tsx:133-135`

**Step 1: Update the navigation call**

Find lines 133-135 (the `viewAsResult` function):

```typescript
const viewAsResult = (item: HistoryItem) => {
  navigation.navigate('Results', { result: item.full_response });
};
```

Replace with:

```typescript
const viewAsResult = (item: HistoryItem) => {
  // Bucket A bug 1: list endpoint returns summary only — item.full_response
  // is always null. Pass comparison_id so ResultsScreen can fetch the full
  // payload via getComparison(id) on mount.
  navigation.navigate('Results', { comparison_id: item.id });
};
```

**Step 2: Update the navigator types to allow `comparison_id` param**

Find the `RootStackParamList` type (likely in `SmartCompareApp/App.tsx` or `src/types/navigation.ts`). Search for it:

```bash
grep -rn "Results:" SmartCompareApp/src/ SmartCompareApp/App.tsx | grep -v node_modules | head -5
```

Locate the `Results:` entry in `RootStackParamList`. It probably looks like:
```typescript
Results: { result?: ComparisonResult; vision_products?: string[] };
```

Add `comparison_id?: string` so it becomes:
```typescript
Results: { result?: ComparisonResult; vision_products?: string[]; comparison_id?: string };
```

**Step 3: Verify TypeScript compiles**

Run from `SmartCompareApp/`:
```bash
npx tsc --noEmit 2>&1 | tail -10
```

Expected: no new errors. If errors appear, the `RootStackParamList` location was wrong — search again and update the right type.

**Step 4: Commit**

```bash
git add SmartCompareApp/src/screens/HistoryScreen.tsx SmartCompareApp/App.tsx SmartCompareApp/src/types/navigation.ts 2>/dev/null
git commit -m "fix(history): pass comparison_id instead of null full_response (Bucket A bug 1)

History list endpoint returns summary fields only (intentional, for perf).
Passing item.full_response (always null) to ResultsScreen produced the
'No comparison loaded' empty state on every tap. Pass comparison_id
instead so Results can lazy-fetch via getComparison(id) on mount.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 1.4: Frontend — ResultsScreen detects `comparison_id`, fetches on mount, shows loading

**Files:**
- Modify: `SmartCompareApp/src/screens/ResultsScreen.tsx:97-135` (around the existing useEffect and result destructure)

**Step 1: Replace the const `result` destructure with stateful + fetcher**

Find around line 102:
```typescript
const result = route?.params?.result;
```

Replace with:

```typescript
// Bucket A bug 1 + bug 2: result may not be in route.params — it might
// need to be fetched (history tap → comparison_id) or generated
// (camera tap → vision_products). Use local state so async loads can
// flow into the same render path.
const [result, setResult] = useState(route?.params?.result ?? null);
const [loadingResult, setLoadingResult] = useState(!route?.params?.result && !!(route?.params?.comparison_id || route?.params?.vision_products));
const [loadError, setLoadError] = useState<string | null>(null);
const minDisplayUntil = useRef<number>(Date.now() + 1200); // 1.2s brand-moment floor
```

**Step 2: Add the useEffect to fetch from comparison_id**

Insert after the existing usage useEffect (around line 132):

```typescript
useEffect(() => {
  // Bucket A bug 1: history tap path — fetch full comparison by ID.
  const comparisonId = route?.params?.comparison_id;
  if (!comparisonId || result) return;

  let cancelled = false;
  (async () => {
    try {
      const { getComparison } = await import('../services/api');
      const data = await getComparison(comparisonId);
      // Respect the 1.2s brand-moment floor — wait if fetch was too fast.
      const remaining = minDisplayUntil.current - Date.now();
      if (remaining > 0) {
        await new Promise((resolve) => setTimeout(resolve, remaining));
      }
      if (!cancelled) {
        setResult(data);
        setLoadingResult(false);
      }
    } catch (err: any) {
      if (cancelled) return;
      if (err?.response?.status === 404) {
        setLoadError('not_found');
      } else if (err?.response?.status === 401) {
        // Auth interceptor handles redirect — no-op here.
      } else {
        setLoadError('generic');
      }
      setLoadingResult(false);
    }
  })();

  return () => {
    cancelled = true;
  };
}, [route?.params?.comparison_id, result]);
```

**Step 3: Add loading-state JSX before the `if (!result)` empty-state branch**

Find line 381 (`if (!result)`). Insert BEFORE that block:

```typescript
// Bucket A bug 1: show theatrical loading while fetching from comparison_id.
// Use existing LoadingRings + skeleton infrastructure per Qaren UX redesign.
if (loadingResult) {
  return (
    <View style={styles.container} testID="results-loading-state">
      <View style={styles.header}>
        <TouchableOpacity onPress={() => navigation.goBack()} style={styles.headerButton}>
          <ArrowLeft size={24} color={colors.text.primary} />
        </TouchableOpacity>
        <View style={{ flex: 1 }} />
        <View style={styles.headerButton} />
      </View>
      <View style={styles.loadingContainer}>
        <LoadingRings size={80} />
        <Text style={styles.loadingText}>{t('results.loading.fromHistory')}</Text>
      </View>
    </View>
  );
}
```

**Note:** if `LoadingRings` isn't already imported, add `import { LoadingRings } from '../components/LoadingRings';` (path may vary — search `LoadingRings` in `SmartCompareApp/src/components/`). If `styles.loadingContainer` and `styles.loadingText` don't exist, add them at the bottom of the file's StyleSheet block:

```typescript
loadingContainer: { flex: 1, justifyContent: 'center', alignItems: 'center', gap: 16 },
loadingText: { fontSize: 16, color: colors.text.secondary, textAlign: 'center', paddingHorizontal: 24 },
```

Add `results.loading.fromHistory: "Loading your comparison..."` (en) and `results.loading.fromHistory: "جارٍ تحميل المقارنة..."` (ar) to the i18n files in `SmartCompareApp/src/i18n/`.

**Step 4: Update the existing `if (!result)` empty state to also handle `loadError`**

Replace the existing line 381 condition:
```typescript
if (!result) {
```

With:
```typescript
if (!result || loadError) {
```

Inside the empty-state JSX, conditionally show a more specific message when `loadError === 'not_found'`:

```typescript
<Text style={styles.emptyStateTitle}>
  {loadError === 'not_found'
    ? t('results.emptyState.notFound')
    : t('results.emptyState.title')}
</Text>
```

Add the i18n key `results.emptyState.notFound: "Comparison not found"` (en) / `"المقارنة غير موجودة"` (ar).

**Step 5: Verify TypeScript + run any existing ResultsScreen tests**

Run from `SmartCompareApp/`:
```bash
npx tsc --noEmit 2>&1 | tail -10
```
Expected: no new errors.

Run from project root:
```bash
cd SmartCompareApp && npm test -- --testPathPattern=ResultsScreen 2>&1 | tail -20
```

Expected: existing tests pass (some may not exist; that's fine — no jest config required).

**Step 6: Commit**

```bash
git add SmartCompareApp/src/screens/ResultsScreen.tsx SmartCompareApp/src/i18n/
git commit -m "$(cat <<'EOF'
fix(history): lazy-fetch full payload when navigated with comparison_id (Bucket A bug 1)

ResultsScreen now handles three navigation cases:
- route.params.result present → render directly (existing path)
- route.params.comparison_id present → fetch via getComparison(id),
  show LoadingRings + theatrical 1.2s brand-moment floor, then render
- neither present → empty state with Back-to-History CTA

Adds loadingContainer + loadingText styles and two i18n keys
(results.loading.fromHistory, results.emptyState.notFound).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 1.5: Verify history bug fixed end-to-end

**Step 1: Run full TypeScript check**

Run from `SmartCompareApp/`:
```bash
npx tsc --noEmit
echo "exit=$?"
```
Expected: `exit=0`.

**Step 2: Push to Railway**

```bash
git push origin main
```

**Step 3: Wait for Railway healthy**

```bash
for i in 1 2 3 4 5 6; do
  echo "--- attempt $i ---"
  sleep 20
  curl -sS -w "\nHTTP=%{http_code}\n" https://web-production-58776.up.railway.app/health
done
```

Expected: 200 within 2 min.

**Step 4: Manual frontend verification (Ahmed via Expo dev or installed build)**

- Open app → Profile tab → see history list with previous comparisons
- Tap any history item → see LoadingRings briefly → see comparison render fully
- If a tap shows "Comparison not found", the backend `/api/v1/comparisons/{id}` may have ownership issues — investigate but don't rollback (likely a test-data artifact)

If manual works: Bug 1 done. If broken: rollback `git revert HEAD~2..HEAD` + investigate the failing case.

---

# Bug 2 — Camera Compare button doesn't fire

## Task 2.1: ResultsScreen detects `vision_products`, calls identify+compare on mount

**Files:**
- Modify: `SmartCompareApp/src/screens/ResultsScreen.tsx` (extend the same useEffect added in Task 1.4)

**Step 1: Extend the useEffect from Task 1.4 to also handle vision_products**

Add a second useEffect AFTER the comparison_id useEffect (or extend the same one):

```typescript
useEffect(() => {
  // Bucket A bug 2: camera tap path — vision_products is an array of photo
  // URIs from the camera screen. Call identifyFromImages which returns
  // either a full ComparisonResult (action="comparison") or an error.
  const visionProducts = route?.params?.vision_products;
  if (!visionProducts || visionProducts.length < 2 || result) return;

  let cancelled = false;
  (async () => {
    try {
      const { identifyFromImages } = await import('../services/api');
      const data = await identifyFromImages(visionProducts, 'bahrain');

      if (data.action === 'comparison') {
        const remaining = minDisplayUntil.current - Date.now();
        if (remaining > 0) {
          await new Promise((resolve) => setTimeout(resolve, remaining));
        }
        if (!cancelled) {
          // The /image/identify endpoint returns the comparison result
          // directly at top level when action="comparison". Adapt to the
          // shape ResultsScreen expects.
          setResult((data as any).result || data);
          setLoadingResult(false);
        }
      } else if (data.action === 'need_second_product') {
        if (!cancelled) {
          setLoadError('need_more_photos');
          setLoadingResult(false);
        }
      } else {
        if (!cancelled) {
          setLoadError('vision_failed');
          setLoadingResult(false);
        }
      }
    } catch (err: any) {
      if (cancelled) return;
      setLoadError('vision_failed');
      setLoadingResult(false);
    }
  })();

  return () => {
    cancelled = true;
  };
}, [route?.params?.vision_products, result]);
```

**Step 2: Update the loading-state JSX from Task 1.4 to differentiate by source**

Change the `loadingText` rendering:

```typescript
<Text style={styles.loadingText}>
  {route?.params?.vision_products
    ? t('results.loading.fromCamera')
    : t('results.loading.fromHistory')}
</Text>
```

Add i18n key `results.loading.fromCamera: "Identifying your products..."` (en) / `"جارٍ التعرف على المنتجات..."` (ar).

**Step 3: Update the empty-state JSX to handle vision-specific errors**

```typescript
<Text style={styles.emptyStateTitle}>
  {loadError === 'not_found'
    ? t('results.emptyState.notFound')
    : loadError === 'need_more_photos'
    ? t('results.emptyState.needMorePhotos')
    : loadError === 'vision_failed'
    ? t('results.emptyState.visionFailed')
    : t('results.emptyState.title')}
</Text>
```

Add i18n keys:
- `results.emptyState.needMorePhotos: "We only spotted one product. Try again with both items clearly in frame."`
- `results.emptyState.visionFailed: "Couldn't identify the products. Try a clearer photo with better lighting."`
- Arabic translations equivalent.

**Step 4: Verify TypeScript**

Run from `SmartCompareApp/`:
```bash
npx tsc --noEmit 2>&1 | tail -10
```
Expected: no new errors.

**Step 5: Commit**

```bash
git add SmartCompareApp/src/screens/ResultsScreen.tsx SmartCompareApp/src/i18n/
git commit -m "$(cat <<'EOF'
fix(camera): wire vision_products param to identify+compare on mount (Bucket A bug 2)

Camera screen passes vision_products: [uri0, uri1] via React Nav,
but ResultsScreen was never wired to consume them — photos were
silently discarded, Compare button felt broken.

ResultsScreen useEffect now detects vision_products, calls
identifyFromImages() via the existing /api/v1/image/identify
endpoint, and renders the same LoadingRings + theatrical 1.2s
brand-moment as the history-fetch path (consistent UX). Error
states for need_more_photos / vision_failed get user-readable
empty-state messages instead of silent failure.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2.2: Push + verify camera flow end-to-end

**Step 1: Push to Railway**

```bash
git push origin main
```

(Frontend-only change, but pushing keeps mobile-bundle-source in sync. For tester verification, run `eas update --branch preview --message "Bug 2: camera Compare wired"` from `SmartCompareApp/` after the commit lands.)

**Step 2: Manual frontend verification (Ahmed via Expo dev or installed build after eas update)**

- Open app → Camera mode → capture 2 distinct products
- Tap Compare → see instant navigation to Results → see "Identifying your products..." loading → see comparison render with both products

If only 1 product is captured: tapping Compare should not fire (existing `bothFilled` gate). Verify this is still respected.

If broken: rollback `git revert HEAD` + investigate.

---

# Bug 3 — Asymmetric specs (last because of complexity + spec-parity gate)

## Task 3.1: Rewrite extraction prompt to be unambiguous about schema fields

**Files:**
- Modify: `app/services/extraction_service.py:204-221` (system prompt CRITICAL RULES block)
- Test: `tests/test_extraction_prompt.py` (create)

**Step 1: Write the failing test**

Create `tests/test_extraction_prompt.py`:

```python
"""Bucket A bug 3 — extraction prompt forces schema fields, no contradiction."""
import pytest
from app.services.extraction_service import _build_specs_prompt, CATEGORY_SPEC_SCHEMAS


def test_prompt_does_not_say_omit_irrelevant_for_schema_fields():
    """The 'Omit irrelevant fields' instruction must be qualified to apply
    ONLY to non-schema fields, not schema-listed fields. Schema-listed fields
    are BY DEFINITION relevant — that's why they're in the schema."""
    p = _build_specs_prompt(
        brand="Samsung", name="Galaxy S25 Ultra", variant=None,
        category="electronics", search_context="snippet content here",
    )
    system = p["system"]

    # Old prompt had the bare phrase "Omit irrelevant fields rather than
    # writing N/A or null." — this is the contradiction that lets GPT skip
    # schema fields. Must be removed or qualified.
    assert "Omit irrelevant fields rather than writing N/A" not in system, \
        "Unqualified 'Omit irrelevant' instruction still in prompt — will let GPT omit schema fields"


def test_prompt_explicitly_requires_schema_fields():
    """Prompt must explicitly say schema fields MUST be attempted (not omitted)."""
    p = _build_specs_prompt(
        brand="Samsung", name="Galaxy S25 Ultra", variant=None,
        category="electronics", search_context="snippets",
    )
    system = p["system"]

    # Must contain a clear directive that schema fields are required
    assertions_pass = (
        "MUST attempt" in system
        or "must provide" in system.lower()
        or "required schema field" in system.lower()
    )
    assert assertions_pass, "Prompt missing explicit must-attempt directive for schema fields"


def test_prompt_allows_training_data_fallback_for_schema():
    """Prompt must allow training-data fallback when snippets are thin."""
    p = _build_specs_prompt(
        brand="Samsung", name="Galaxy S25 Ultra", variant=None,
        category="electronics", search_context="thin snippet",
    )
    system = p["system"]

    assertions_pass = (
        "training data" in system.lower()
        or "your knowledge" in system.lower()
        or "well-known products, you KNOW" in system
    )
    assert assertions_pass, "Prompt missing training-data fallback permission"


def test_prompt_field_source_marker_still_required():
    """Each spec field must still come with a _source marker (snippet_N or training)."""
    p = _build_specs_prompt(
        brand="Samsung", name="Galaxy S25 Ultra", variant=None,
        category="electronics", search_context="snippets",
    )
    system = p["system"]
    assert "_source" in system, "Prompt missing _source marker requirement"
```

**Step 2: Run tests — expect 1 FAIL (assertion 1 — "Omit irrelevant" is still in prompt)**

Run: `python -m pytest tests/test_extraction_prompt.py -v --timeout=10`
Expected: `test_prompt_does_not_say_omit_irrelevant_for_schema_fields FAILED`. Others may pass already.

**Step 3: Rewrite the contradictory section in extraction_service.py**

In `app/services/extraction_service.py`, find lines 204-221 (the `CRITICAL RULES:` block starting at line 204). Replace lines 209-210:

```python
- Only include fields that are GENUINELY RELEVANT to this specific product. Omit irrelevant fields rather than writing N/A or null.
- For well-known products, you KNOW the specs -- do NOT return null for fields that clearly apply
```

With:

```python
- For fields explicitly listed in the schema above (e.g. front_camera, water_resistance, processor), you MUST attempt to provide a value. These fields are required for the category and cannot be omitted.
- Use snippets as your primary source. If snippets don't mention a required schema field, fall back to your training data (you know specs for well-known products like phones, supplements, fragrances).
- Only return null for a schema field if you genuinely don't know AND snippets are silent on it.
- You MAY omit fields that are NOT in the schema (e.g. niche specs the schema doesn't list); only schema fields are required.
```

**Step 4: Run tests — expect all PASS**

Run: `python -m pytest tests/test_extraction_prompt.py -v --timeout=10`
Expected: `4 passed`.

**Step 5: Run broader extraction tests for regressions**

Run: `python -m pytest tests/ -k "extraction" --timeout=30 -v 2>&1 | tail -10`
Expected: no new failures vs the Session 47/48 baseline.

**Step 6: Commit**

```bash
git add app/services/extraction_service.py tests/test_extraction_prompt.py
git commit -m "$(cat <<'EOF'
fix(extraction): force schema fields, allow training-data fallback (Bucket A bug 3a)

Resolves the contradictory extraction prompt that caused asymmetric
specs in comparisons (iPhone 17 had Front Camera + Water Resistance,
Galaxy S25 Ultra showed N/A for the same public-knowledge fields).

Old prompt: template forced all schema keys to null (line 188) but
system said 'Omit irrelevant fields rather than writing N/A' (line 209)
— GPT obeyed the system instruction and skipped fields when Serper
snippets were thin (newer products have fewer indexed reviews).

New prompt: schema-listed fields are BY DEFINITION relevant — GPT
MUST attempt them. Snippets first, training-data fallback (with
_source='training' marker) second. null only allowed when GPT
genuinely doesn't know AND snippets are silent. Non-schema fields
may still be omitted.

Tests: tests/test_extraction_prompt.py — 4 new tests asserting the
contradictory phrase is gone + must-attempt directive is present +
training-data fallback is allowed + _source markers still required.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3.2: Add `_field_confidence` tracking (snippet vs training_data)

**Files:**
- Modify: `app/services/structured_comparison_service.py` (around `_clean_specs` and `_fetch_product_data`)
- Test: extend `tests/test_extraction_prompt.py`

**Step 1: Write the failing test**

Add to `tests/test_extraction_prompt.py`:

```python
def test_clean_specs_extracts_field_confidence_from_source_markers():
    """When GPT returns each spec key + a _source marker, _clean_specs
    must extract those markers into a _field_confidence dict and remove
    the _source siblings from the final spec output."""
    from app.services.structured_comparison_service import StructuredComparisonService

    svc = StructuredComparisonService()
    raw_specs = {
        "ram": "12 GB",
        "ram_source": "snippet_3",
        "front_camera": "12 MP f/2.2",
        "front_camera_source": "training",
        "water_resistance": "IP68",
        "water_resistance_source": "snippet_5",
    }
    cleaned = svc._clean_specs(raw_specs)

    # _field_confidence stamped from _source markers
    confidence = cleaned.get("_field_confidence", {})
    assert confidence.get("ram") == "snippet", f"ram confidence wrong: {confidence}"
    assert confidence.get("front_camera") == "training_data", f"front_camera confidence wrong: {confidence}"
    assert confidence.get("water_resistance") == "snippet", f"water_resistance confidence wrong: {confidence}"

    # _source sibling keys stripped from output
    assert "ram_source" not in cleaned
    assert "front_camera_source" not in cleaned
    assert "water_resistance_source" not in cleaned

    # Actual values preserved
    assert cleaned.get("ram") == "12 GB"
    assert cleaned.get("front_camera") == "12 MP f/2.2"
    assert cleaned.get("water_resistance") == "IP68"
```

**Step 2: Run test — expect FAIL**

Run: `python -m pytest tests/test_extraction_prompt.py::test_clean_specs_extracts_field_confidence_from_source_markers -v --timeout=10`
Expected: FAIL — `_field_confidence` is missing or `_source` keys leak through.

**Step 3: Update `_clean_specs` in structured_comparison_service.py**

Search for the existing `_clean_specs` method:
```bash
grep -n "def _clean_specs" app/services/structured_comparison_service.py
```

Read the existing implementation. Add field-confidence extraction at the top:

```python
def _clean_specs(self, specs: Dict[str, Any]) -> Dict[str, Any]:
    """Clean spec dict: extract _source markers into _field_confidence,
    strip null/None values from display output."""
    if not isinstance(specs, dict):
        return specs

    # Extract _source markers into _field_confidence dict
    field_confidence = {}
    cleaned_keys = list(specs.keys())
    for key in cleaned_keys:
        if key.endswith("_source"):
            base_key = key[:-len("_source")]
            source_value = specs[key]
            if isinstance(source_value, str):
                if source_value.startswith("snippet"):
                    field_confidence[base_key] = "snippet"
                elif source_value == "training":
                    field_confidence[base_key] = "training_data"
                else:
                    field_confidence[base_key] = source_value

    # Build cleaned dict: drop _source siblings, drop null values
    cleaned = {}
    for key, value in specs.items():
        if key.endswith("_source"):
            continue
        if value is None:
            continue
        cleaned[key] = value

    if field_confidence:
        cleaned["_field_confidence"] = field_confidence

    return cleaned
```

**Step 4: Run test — expect PASS**

Run: `python -m pytest tests/test_extraction_prompt.py -v --timeout=10`
Expected: all 5 tests pass.

**Step 5: Run broader regression**

Run: `python -m pytest tests/test_fan_out_integration.py tests/test_stage_timings.py -v --timeout=60 2>&1 | tail -10`
Expected: 14 passed (12 + 2). Anything related to specs handling stays green.

**Step 6: Commit**

```bash
git add app/services/structured_comparison_service.py tests/test_extraction_prompt.py
git commit -m "$(cat <<'EOF'
feat(extraction): track per-field confidence (snippet vs training_data) (Bucket A bug 3b)

Extends _clean_specs to extract GPT's _source markers (e.g.
ram_source='snippet_3', front_camera_source='training') into a
_field_confidence dict on each product. Frontend can show a subtle
ℹ️ tooltip on training-data values so users know which specs came
from current search results vs general product knowledge.

Strips the _source sibling keys from final display output so the
UI doesn't render them as standalone spec rows.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3.3: Smart-fallback Serper queries for STILL-missing critical schema fields

**Files:**
- Modify: `app/services/structured_comparison_service.py::_fetch_product_data` (around line 970-1010 — Phase 2 section)
- Modify: `app/services/extraction_service.py` (add a `CRITICAL_SCHEMA_FIELDS` constant)
- Test: `tests/test_smart_fallback.py` (create)

**Step 1: Add CRITICAL_SCHEMA_FIELDS constant in extraction_service.py**

After `CATEGORY_SPEC_SCHEMAS` definition (around line 90), add:

```python
# Critical schema fields per category — the ones we'll run a smart-fallback
# Serper query for if GPT returns null after the primary extraction.
# Cap is enforced in structured_comparison_service to keep the parallel
# fallback within the Phase 2 wall-time budget (3s, asyncio.wait_for).
CRITICAL_SCHEMA_FIELDS: Dict[str, List[str]] = {
    "electronics": ["front_camera", "rear_camera", "processor", "ram", "battery", "water_resistance"],
    "supplements": ["count", "dosage", "form"],
    "fragrances": ["concentration", "longevity", "sillage"],
    "fashion": ["material", "origin"],
    "skincare": ["volume_ml", "ingredients"],
    "haircare": ["volume_ml", "ingredients"],
    "makeup": ["volume_ml", "shade_range"],
    "grocery": ["weight_g", "ingredients"],
    "other": [],
}
```

**Step 2: Write the failing test**

Create `tests/test_smart_fallback.py`:

```python
"""Bucket A bug 3c — smart-fallback for missing critical schema fields runs in parallel."""
import asyncio
import pytest
from unittest.mock import AsyncMock, patch

from app.services.structured_comparison_service import (
    StructuredComparisonService, get_comparison_service,
)


@pytest.mark.asyncio
async def test_smart_fallback_runs_in_parallel_with_phase_2():
    """The smart-fallback Serper queries must run concurrently with
    Phase 2 (reviews+rating). Total wall time should be max(phase2, fallback),
    not sum — within the 3s cap."""

    async def slow_search_web(*args, **kwargs):
        await asyncio.sleep(1.5)  # Fallback Serper query
        return {"organic": [{"snippet": "Galaxy S25 Ultra front camera: 12 MP"}]}

    async def slow_get_reviews(*args, **kwargs):
        await asyncio.sleep(2.0)  # Phase 2 reviews
        return {"summary": "test", "pros": [], "cons": []}

    async def fast_get_rating(*args, **kwargs):
        await asyncio.sleep(0.5)
        return {"rating": 4.5, "review_count": 100, "rating_verified": False, "rating_source": None}

    with patch.object(
        StructuredComparisonService, "_get_reviews", new=slow_get_reviews,
    ), patch.object(
        StructuredComparisonService, "_get_verified_rating", new=fast_get_rating,
    ), patch.object(
        StructuredComparisonService, "_get_specs",
        new=AsyncMock(return_value={"ram": "12 GB", "_field_confidence": {"ram": "snippet"}}),
    ), patch.object(
        StructuredComparisonService, "_get_price",
        new=AsyncMock(return_value={"amount": 100, "currency": "BHD", "source_method": "local_bhd"}),
    ), patch(
        "app.services.structured_comparison_service.search_web", new=slow_search_web,
    ):
        svc = get_comparison_service()
        product_info = {
            "brand": "Samsung",
            "name": "Galaxy S25 Ultra",
            "variant": None,
            "category": "electronics",
            "search_query": "Samsung Galaxy S25 Ultra",
        }

        start = asyncio.get_event_loop().time()
        result = await svc._fetch_product_data(
            product_info, region="bahrain",
            include_specs=True, include_reviews=True, nocache=True,
        )
        elapsed = asyncio.get_event_loop().time() - start

        # Parallel: max(phase2=2.0, fallback=1.5) = 2.0s
        # Sequential: 2.0 + 1.5 = 3.5s
        assert elapsed < 2.8, f"Smart-fallback ran sequentially with Phase 2 (took {elapsed:.2f}s, expected <2.8s for parallel)"


@pytest.mark.asyncio
async def test_smart_fallback_capped_at_3_seconds():
    """If fallback Serper query exceeds 3s cap, it gets cancelled gracefully."""

    async def slow_search_web(*args, **kwargs):
        await asyncio.sleep(5.0)  # Way too slow
        return {"organic": []}

    with patch.object(
        StructuredComparisonService, "_get_specs",
        new=AsyncMock(return_value={"ram": "12 GB"}),  # Missing front_camera etc
    ), patch.object(
        StructuredComparisonService, "_get_price",
        new=AsyncMock(return_value={"amount": 100, "currency": "BHD", "source_method": "local_bhd"}),
    ), patch.object(
        StructuredComparisonService, "_get_reviews",
        new=AsyncMock(return_value={"summary": "ok", "pros": [], "cons": []}),
    ), patch.object(
        StructuredComparisonService, "_get_verified_rating",
        new=AsyncMock(return_value={"rating": 4.5, "review_count": 100, "rating_verified": False, "rating_source": None}),
    ), patch(
        "app.services.structured_comparison_service.search_web", new=slow_search_web,
    ):
        svc = get_comparison_service()
        product_info = {
            "brand": "Samsung",
            "name": "Galaxy S25 Ultra",
            "variant": None,
            "category": "electronics",
            "search_query": "Samsung Galaxy S25 Ultra",
        }

        start = asyncio.get_event_loop().time()
        result = await svc._fetch_product_data(
            product_info, region="bahrain",
            include_specs=True, include_reviews=True, nocache=True,
        )
        elapsed = asyncio.get_event_loop().time() - start

        # Must complete despite slow fallback — within 3.5s (3s cap + buffer)
        assert elapsed < 3.5, f"Smart-fallback did not respect 3s cap (took {elapsed:.2f}s)"
```

**Step 3: Run tests — expect FAIL (smart-fallback doesn't exist yet)**

Run: `python -m pytest tests/test_smart_fallback.py -v --timeout=15`
Expected: both fail — likely with `AssertionError` on elapsed time being too high (sequential) or tests just measuring Phase 2 alone (no fallback runs at all).

**Step 4: Implement smart-fallback in `_fetch_product_data`**

In `app/services/structured_comparison_service.py`, find the Phase 2 block (around line 973-990). Add the fallback logic to run in parallel with Phase 2's gather:

```python
# Phase 2: reviews + verified rating (parallel) + smart-fallback for missing critical specs
retailer_ratings = collect_retailer_ratings(full_name, self._shopping_items_cache)

phase2_tasks = []
phase2_keys = []

if include_reviews:
    phase2_tasks.append(self._get_reviews(
        brand, name, variant, search_query, nocache,
        category=category, retailer_ratings=retailer_ratings,
        search_results=unified_search
    ))
    phase2_keys.append("reviews")

phase2_tasks.append(self._get_verified_rating(full_name))
phase2_keys.append("_rating_data")

# Smart-fallback: identify critical schema fields still null after primary extraction
from app.services.extraction_service import CRITICAL_SCHEMA_FIELDS
critical_fields = CRITICAL_SCHEMA_FIELDS.get(category, [])
specs_so_far = result.get("specs") or {}
missing_critical = [f for f in critical_fields
                    if specs_so_far.get(f) in (None, "", "N/A")][:2]  # Cap at 2 per product

fallback_task = None
if missing_critical:
    fallback_task = asyncio.create_task(
        self._smart_fallback_extract(brand, name, variant, category, missing_critical)
    )
    phase2_tasks.append(fallback_task)
    phase2_keys.append("_smart_fallback")

phase2_results = await asyncio.gather(*phase2_tasks, return_exceptions=True)

# Apply smart-fallback results if present
if fallback_task is not None:
    fallback_idx = phase2_keys.index("_smart_fallback")
    fallback_result = phase2_results[fallback_idx]
    if not isinstance(fallback_result, Exception) and fallback_result:
        # Merge filled fields into specs
        result_specs = result.get("specs") or {}
        for field, value in fallback_result.items():
            if value and not result_specs.get(field):
                result_specs[field] = value
                # Mark these as fallback-sourced
                fc = result_specs.setdefault("_field_confidence", {})
                fc[field] = "smart_fallback"
        result["specs"] = result_specs

# Existing rating + review result handling continues below...
```

Then add the `_smart_fallback_extract` method to the class:

```python
async def _smart_fallback_extract(
    self, brand: str, name: str, variant: Optional[str], category: str,
    missing_fields: List[str],
) -> Dict[str, Any]:
    """Run a targeted Serper query for missing critical schema fields,
    then extract just those fields via a small GPT call.

    Capped at 3s by asyncio.wait_for to keep within Phase 2 wall-time
    budget. Returns dict of {field: value} for fields successfully
    filled; empty dict on timeout / failure.
    """
    if not missing_fields:
        return {}

    try:
        # Build a focused query for the missing fields
        fields_text = " ".join(missing_fields).replace("_", " ")
        full_name = f"{brand} {name} {variant or ''}".strip()
        query = f"{full_name} {fields_text} specifications"

        async def _do_extract():
            from app.services.serper_service import search_web
            from app.services.openai_service import extract_specs_targeted

            search_results = await search_web(query, num_results=5)
            self._track_serper_cost()

            # Build a focused context from snippets
            snippets = []
            for hit in (search_results.get("organic") or [])[:5]:
                snippet = hit.get("snippet", "")
                if snippet:
                    snippets.append(snippet)
            context = "\n".join(snippets[:5])

            if not context:
                return {}

            # Small targeted GPT call to extract just the missing fields
            return await extract_specs_targeted(
                brand=brand, name=name, variant=variant,
                category=category, fields=missing_fields,
                context=context,
            )

        return await asyncio.wait_for(_do_extract(), timeout=3.0)

    except asyncio.TimeoutError:
        logger.info(f"[SMART_FALLBACK] Timeout for {brand} {name} fields {missing_fields}")
        return {}
    except Exception as e:
        logger.warning(f"[SMART_FALLBACK] Error for {brand} {name}: {e}")
        return {}
```

**Step 5: Add `extract_specs_targeted` to openai_service.py**

In `app/services/openai_service.py`, add:

```python
async def extract_specs_targeted(
    brand: str, name: str, variant: Optional[str],
    category: str, fields: List[str], context: str,
) -> Dict[str, Any]:
    """Extract a small set of specified fields from a focused context.

    Used by smart-fallback when primary spec extraction left critical
    fields null. Returns dict of {field: value} for fields it could fill.
    """
    if not fields:
        return {}

    fields_json = ",\n    ".join(f'"{f}": null' for f in fields)
    full_name = f"{brand} {name} {variant or ''}".strip()

    system = f"""Extract these specific fields for {full_name} from the snippets below.
Return ONLY valid JSON with these exact keys:
{{
    {fields_json}
}}

Rules:
- For each field, give a single short value (e.g. '12 MP', 'IP68', 'Snapdragon 8 Gen 3')
- If you cannot find or know the value, return null for that field
- Use your training data as a fallback when snippets are silent"""

    user = f"SNIPPETS:\n{context}\n\nReturn JSON for: {fields}"

    try:
        client = get_openai_client()
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=200,
        )
        import json
        content = response.choices[0].message.content
        result = json.loads(content) if content else {}
        # Filter to only requested fields
        return {k: v for k, v in result.items() if k in fields and v is not None}
    except Exception as e:
        logger.warning(f"[EXTRACT_TARGETED] Failed: {e}")
        return {}
```

**Step 6: Run tests — expect PASS**

Run: `python -m pytest tests/test_smart_fallback.py -v --timeout=15`
Expected: `2 passed`.

**Step 7: Run broader regression**

Run: `python -m pytest tests/test_fan_out_integration.py tests/test_stage_timings.py tests/test_extraction_prompt.py -v --timeout=60 2>&1 | tail -10`
Expected: all green.

**Step 8: Commit**

```bash
git add app/services/structured_comparison_service.py app/services/extraction_service.py app/services/openai_service.py tests/test_smart_fallback.py
git commit -m "$(cat <<'EOF'
feat(extraction): smart-fallback Serper for critical specs, runs parallel to Phase 2 (Bucket A bug 3c)

Identifies critical schema fields still null after primary extraction
(per-category list in extraction_service.CRITICAL_SCHEMA_FIELDS, max 2
per product) and runs a targeted Serper query + small GPT extract for
just those fields. Fills the result.specs dict before scoring.

Wall-time: runs IN PARALLEL with Phase 2 reviews+rating gather via
asyncio.gather, capped at 3s via asyncio.wait_for. Phase 2 already
takes ~3.3s p50 — fallback completes within that window in the typical
case, adding zero wall time. Worst case: 3s cap fires, gap stays
unfilled this run, gets cached on next.

Tests: tests/test_smart_fallback.py — 2 tests assert parallel execution
(max not sum) + cap enforcement (≤3.5s under 5s slow fallback).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3.4: Spec-parity regression test against baseline fixture

**Files:**
- Test: `tests/test_spec_parity.py` (create)

**Step 1: Write the test**

```python
"""Bucket A bug 3 — spec parity regression test against pre-D1 baseline."""
import json
import os
import pytest


BASELINE_PATH = "tests/fixtures/comparison_baseline_d2.json"


@pytest.fixture(scope="module")
def baseline():
    with open(BASELINE_PATH) as f:
        return json.load(f)


def _extract_spec_keys(comparison_dict, product_index):
    """Get the set of non-null spec keys for a product, filtering out
    'N/A' and empty strings (those are 'GPT didn't know' signals)."""
    products = comparison_dict.get("products") or (comparison_dict.get("specs") or {}).get("products", [])
    if len(products) <= product_index:
        return set()
    specs = products[product_index].get("specs") or {}
    valid_keys = set()
    for k, v in specs.items():
        if k.startswith("_"):
            continue  # internal fields like _field_confidence
        if v in (None, "", "N/A"):
            continue
        valid_keys.add(k)
    return valid_keys


def test_baseline_iphone_has_minimum_keys(baseline):
    """Baseline iPhone 17 should have at least 6 spec keys with real values."""
    keys = _extract_spec_keys(baseline, 0)
    assert len(keys) >= 6, f"iPhone baseline too thin: {keys}"


def test_baseline_s25_has_minimum_keys(baseline):
    """Baseline Galaxy S25 Ultra should have at least 6 spec keys with real values."""
    keys = _extract_spec_keys(baseline, 1)
    assert len(keys) >= 6, f"S25 baseline too thin: {keys}"


@pytest.mark.live_unit
def test_post_fix_iphone_vs_s25_has_critical_specs():
    """Post-Bucket-A live bench: both products should have front_camera AND
    water_resistance populated (the bug-3 fix). Skipped unless RUN_LIVE_BENCH=1.

    Run manually after deploying Bucket A:
    RUN_LIVE_BENCH=1 pytest tests/test_spec_parity.py::test_post_fix_iphone_vs_s25_has_critical_specs -v
    """
    if os.environ.get("RUN_LIVE_BENCH") != "1":
        pytest.skip("Set RUN_LIVE_BENCH=1 to run live bench")

    import httpx
    response = httpx.get(
        "https://web-production-58776.up.railway.app/api/v1/text/compare",
        params={"q": "iPhone 17 vs Galaxy S25 Ultra", "region": "bahrain", "nocache": "true"},
        timeout=60,
    )
    assert response.status_code == 200
    data = response.json()

    products = data.get("products") or (data.get("specs") or {}).get("products", [])
    assert len(products) == 2, "Expected 2 products"

    for i, p in enumerate(products):
        specs = p.get("specs") or {}
        front_cam = specs.get("front_camera")
        water = specs.get("water_resistance")
        assert front_cam not in (None, "", "N/A"), \
            f"Product {i} ({p.get('name')}) missing front_camera: {specs}"
        assert water not in (None, "", "N/A"), \
            f"Product {i} ({p.get('name')}) missing water_resistance: {specs}"
```

**Step 2: Run the offline tests — should PASS against current fixture**

Run: `python -m pytest tests/test_spec_parity.py -v --timeout=10`
Expected: `2 passed, 1 skipped` (live test skipped).

**Step 3: Commit**

```bash
git add tests/test_spec_parity.py
git commit -m "test(spec-parity): regression check for asymmetric specs bug (Bucket A bug 3)

Two offline tests assert baseline fixture has ≥6 spec keys per product
(can't regress baseline if it's already too thin). One live bench test
(skipped by default, RUN_LIVE_BENCH=1 to enable) asserts post-Bucket-A
deploy returns both products with front_camera + water_resistance —
the specific symptoms the user reported.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 3.5: Push Bug 3 + run live bench verification

**Step 1: Push to Railway**

```bash
git push origin main
```

**Step 2: Wait for Railway healthy**

```bash
for i in 1 2 3 4 5 6; do
  echo "--- attempt $i ---"
  sleep 20
  curl -sS -w "\nHTTP=%{http_code}\n" https://web-production-58776.up.railway.app/health
done
```

**Step 3: Run the live spec-parity test**

```bash
RUN_LIVE_BENCH=1 python -m pytest tests/test_spec_parity.py::test_post_fix_iphone_vs_s25_has_critical_specs -v --timeout=90
```

Expected: PASS — both iPhone and S25 have front_camera + water_resistance populated.

If FAIL with "missing front_camera": smart-fallback didn't fire OR Serper query returned nothing useful. Investigate:
- Check Railway logs for `[SMART_FALLBACK]` entries
- Run the comparison manually via curl with stage timings on (DEBUG_STAGE_TIMINGS=true) and inspect the response
- If fallback fires but returns empty, the targeted GPT call's prompt may need tuning

**Step 4: Run a cold mainstream bench to verify wall-time didn't regress**

```bash
curl -sS -o /tmp/post_bucket_a.json \
  -w "TIME=%{time_total}s STATUS=%{http_code}\n" \
  "https://web-production-58776.up.railway.app/api/v1/text/compare?q=iPhone+17+vs+Galaxy+S25+Ultra&region=bahrain&nocache=true" \
  --max-time 60
```

Expected: TIME under ~25s (was 19.3s pre-Bucket-A per Phase 2A data — allow +5s tolerance for smart-fallback parallel overhead).

If TIME exceeds 25s: smart-fallback is running sequentially or Serper is rate-limited. Investigate before proceeding to D2.

---

# Combined Bucket A verification

## Task A.6: Full regression sweep + manual UX verification

**Step 1: Run the unit test suite for regressions**

Run: `python -m pytest tests/ -m "not (live_unit or live_db or integration)" --ignore=tests/test_integration.py --timeout=15 --tb=no -q 2>&1 | tail -10`

Expected: same ≤17 baseline failure count, no NEW failures.

**Step 2: Push frontend changes via EAS Update**

From `SmartCompareApp/`:
```bash
eas update --branch preview --message "Bucket A: history + camera + asymmetric specs + currency fixes"
```

Wait for update to land (~30s).

**Step 3: Manual UX verification (Ahmed)**

Open app:
1. **History tap:** see LoadingRings → comparison renders fully ✓
2. **Camera capture 2 products → Compare:** see "Identifying products" → comparison renders ✓
3. **iPhone vs S25 Ultra compare:** both products show Front Camera + Water Resistance values ✓
4. **Luxury bag compare (LV/Gucci):** prices in plausible BHD range, not 3000+ BHD ✓

If all 4 verifications pass: **Bucket A SHIPPED.** Update task list, hand back to user.

If any fail: targeted rollback for that bug + investigate, do NOT mass-revert.

---

## Final reporting checkpoint

After Bucket A ships, hand back to user with:

```
Bucket A SHIPPED. Status:
- Bug 4 (currency): fixed at <commit>. SGD/JPY/CNY/INR now convert correctly.
- Bug 1 (history): fixed at <commit>. Tap-to-Results works with lazy fetch + LoadingRings.
- Bug 2 (camera): fixed at <commit>. Capture+Compare flows through identify+stream.
- Bug 3 (asymmetric specs): fixed at <commit>. Smart-fallback fills missing critical fields in parallel with Phase 2.

Wall-time impact: cold mainstream ~<X>s (was 19s pre-A). Within target.

Next: brainstorm D2 Section 3 design (prompt caching + combine specs+reviews) using Phase 2A data already on disk.
```

---

## Rollback playbook

Per fix:
- **Bug 4:** `git revert <bug4-commit>` → currency goes back to silent 1.0 (same as today).
- **Bug 1:** `git revert <bug1-commits>` → history shows empty state again (same as today).
- **Bug 2:** `git revert <bug2-commits>` → camera Compare silent again (same as today).
- **Bug 3:** `git revert <bug3-commits>` → asymmetric specs return + wall-time goes back to pre-A baseline. Highest risk if smart-fallback is misbehaving.

For ANY rollback: `git push origin main` triggers Railway redeploy; verify `/health` 200 + targeted bench to confirm pre-deploy behavior restored. For frontend rollbacks, also need `eas update --branch preview` with the reverted commit.
