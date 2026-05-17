# Bucket A Bugs — Deploy Checklist

**Trigger:** After all 10 Bucket A commits are pushed to `origin/main` and Railway redeploys.
**Plan reference:** `docs/plans/2026-05-17-bucket-a-bugs.md`
**Design reference:** `docs/plans/2026-05-17-bucket-a-bugs-design.md`
**Author:** qa-opus, 2026-05-17
**Approver:** team-lead

---

## Commits landing on `main` (qa-opus approved, in chronological order)

```
feea3fe  fix(currency): add SGD/JPY/CNY/INR to FALLBACK_RATES               (Bug 4 Task 4.1)
4923d37  test(spec-parity): regression check for asymmetric specs bug       (Bug 3 Task 3.4 prep)
8051579  feat(api): add getComparison(id) for lazy history payload fetch    (Bug 1 Task 1.2)
8b5e5d8  fix(history): pass comparison_id instead of null full_response     (Bug 1 Task 1.3)
91a4035  test(currency): extra coverage for case-insensitivity + boundary   (test-opus extra coverage)
8331322  fix(currency): region-aware conversion + warn on unknown currency  (Bug 4 Task 4.2)
b1f18d7  fix(extraction): force schema fields, allow training-data fallback (Bug 3 Task 3.1)
94f8958  fix(history): lazy-fetch full payload when navigated w/ comparison_id (Bug 1 Task 1.4)
fa62aaf  fix(camera): wire vision_products param to identify+compare        (Bug 2 Task 2.1)
0e2167e  feat(extraction): track per-field confidence (snippet vs training_data) (Bug 3 Task 3.2)
4791ca0  feat(extraction): smart-fallback Serper for critical specs in parallel  (Bug 3 Task 3.3)
```

Verify locally before pushing:
```bash
git log --oneline origin/main..HEAD    # should show exactly these 11 commits (10 fix/feat + 1 test)
```

---

## Test gates passed pre-push

| File | Tests | Status |
|------|-------|--------|
| `tests/test_exchange_rate_service.py` | 33/33 | PASS |
| `tests/test_price_service.py` | 5/5 | PASS |
| `tests/test_price_fallback.py` | 11/11 | PASS (USD→BHD adjusted 0.377→0.376) |
| `tests/test_error_paths.py::TestConvertToBhd` | 5/5 | PASS (USD→BHD adjusted) |
| `tests/test_currency_coverage.py` | 20/20 | PASS |
| `tests/test_extraction_prompt.py` | 12/12 | PASS (5 new) |
| `tests/test_smart_fallback.py` | 2/2 | PASS (parallel + cap) |
| `tests/test_fan_out_integration.py` | 12/12 | PASS (no regression) |
| `tests/test_stage_timings.py` | 2/2 | PASS |
| `tests/test_spec_parity.py` | 2 passed + 1 skipped | PASS (live test RUN_LIVE_BENCH-gated) |
| `npx tsc --noEmit` (SmartCompareApp) | exit 0 | PASS |

---

## Step 0 — Preconditions

```bash
cd C:/Users/SynAckITPC/Documents/AI/smartcompare

git status --short                                # should be clean
git rev-parse --abbrev-ref HEAD                   # should print "main"
git log --oneline origin/main..HEAD               # 11 commits as listed above

curl -s https://web-production-58776.up.railway.app/health
# expect: {"status":"healthy"}
```

If any precondition fails, stop and investigate before pushing.

---

## Step 1 — Push to Railway

```bash
cd C:/Users/SynAckITPC/Documents/AI/smartcompare
git push origin main
```

Railway auto-deploys in ~90s.

---

## Step 2 — Wait for Railway healthy

```bash
for i in 1 2 3 4 5 6; do
  echo "--- attempt $i ---"
  sleep 20
  curl -sS -w "\nHTTP=%{http_code}\n" https://web-production-58776.up.railway.app/health
done
```

Expect 200 within 2 min.

---

## Step 3 — Live bench (Railway, immediately after deploy healthy)

### 3a — Spec-parity live test

```bash
cd C:/Users/SynAckITPC/Documents/AI/smartcompare
RUN_LIVE_BENCH=1 python -m pytest tests/test_spec_parity.py::test_post_fix_iphone_vs_s25_has_critical_specs -v --timeout=90
```

Expect: PASS — both iPhone 17 and Galaxy S25 Ultra return non-null `front_camera` + `water_resistance`.

Failure modes:
- "missing front_camera": smart-fallback didn't fire OR Serper returned nothing useful. Check Railway logs for `[SMART_FALLBACK]` entries.
- Timeout (>90s): scatter-gather or smart-fallback running sequentially. Inspect `DEBUG_STAGE_TIMINGS=true` response.

### 3b — Cold mainstream wall-time bench (must not regress)

```bash
curl -sS -o /tmp/post_bucket_a.json \
  -w "TIME=%{time_total}s STATUS=%{http_code}\n" \
  "https://web-production-58776.up.railway.app/api/v1/text/compare?q=iPhone+17+vs+Galaxy+S25+Ultra&region=bahrain&nocache=true" \
  --max-time 60
```

Expect: TIME ≤ 25s (was 19.3s pre-Bucket-A; +5s tolerance for smart-fallback parallel overhead).
If TIME > 25s: smart-fallback may be sequential or Serper rate-limited. Investigate before frontend deploy.

### 3c — Luxury bag currency bench (Bug 4 direct regression test)

```bash
curl -sS -o /tmp/lv_check.json \
  -w "TIME=%{time_total}s STATUS=%{http_code}\n" \
  "https://web-production-58776.up.railway.app/api/v1/text/compare?q=Louis+Vuitton+Neverfull+vs+Gucci+Marmont&region=bahrain&nocache=true" \
  --max-time 60

python -c "
import json
with open('/tmp/lv_check.json') as f:
    d = json.load(f)
products = d.get('products') or (d.get('specs') or {}).get('products', [])
for p in products:
    price = p.get('price', {})
    amt = price.get('amount')
    curr = price.get('currency', 'unknown')
    print(f'{p.get(\"name\")}: {amt} {curr}')
"
```

Expect: BHD amounts in plausible range (~1000-3000 BHD for typical luxury handbags), NOT 2998+ BHD which would be SGD-mislabeled.

---

## Step 4 — Ship frontend via EAS Update

```bash
cd C:/Users/SynAckITPC/Documents/AI/smartcompare/SmartCompareApp
eas update --branch preview --message "Bucket A: history + camera + asymmetric specs + currency fixes"
```

Phones on the `preview` channel pick up the new JS bundle on next app cold-start. Record the new EAS Update group ID for CLAUDE.md Bundle history.

---

## Step 5 — Manual UX verification (Ahmed, on installed build after eas update)

Test all 4 bug fixes end-to-end:

### 5a — Bug 1 (history)
1. Open app → Profile → History tab → see list of previous comparisons
2. Tap any history item
3. **Expect:** brief LoadingRings (~1.2s) → comparison renders fully with all sections
4. Tap a deleted/invalid comparison ID (if available)
5. **Expect:** "Comparison not found" empty state with "Back to history" CTA

#### 5a-races — Bug 1 mount-time race scenarios (from test-opus review of 94f8958)

These can't be jest-tested cleanly, so verify manually:

1. **Back button mid-fetch.** History → tap item → press Back during LoadingRings. Expect: no crash, no setState-on-unmounted warning. (`cancelled` flag should prevent setResult.)
2. **Tap same history item twice in quick succession.** Re-mount with same comparison_id. Expect: no broken state; second fetch either runs again or hits cache — both are acceptable.
3. **Deleted comparison_id.** ID pointing at a row deleted from DB → backend 404 → loadError='not_found' → "Comparison not found" empty state. Expect: no crash.
4. **401 mid-fetch (expired token).** Axios interceptor handles refresh/redirect. Expect: `loadingResult` stays true until redirect; no flash of empty state.
5. **Network drop mid-fetch.** Airplane mode toggled after tap. Expect: error caught, `loadError='generic'`, default empty-state title shows; no crash.
6. **Cached/fast fetch — 1.2s brand-moment floor.** Tap a comparison the backend will serve from cache instantly. Expect: LoadingRings still displays for full ~1.2s before render (brand moment lands).
7. **route.params undefined entirely.** Deep-link / stale rehydration with no params at all. Expect: empty state immediately, no loading flash. (Pre-Bundle E defensive path.)
8. **Both `result` AND `comparison_id` in params** (defensive). Initial useState reads `result` first; useEffect early-returns when result is truthy. Expect: renders directly, no spurious fetch. (Lower priority — would only matter if a future caller sets both.)

### 5b — Bug 2 (camera)
1. Home → Camera mode → capture 2 distinct products clearly in frame
2. Tap Compare
3. **Expect:** instant nav to Results → "Identifying your products" (`نتعرّف على منتجاتك`) → comparison renders
4. Capture only 1 product → Compare button should NOT fire (existing `bothFilled` gate)
5. Test failure case: capture 1 product clearly + 1 blurry → tap Compare
6. **Expect:** "We spotted one product. Bring both items into the frame for a side-by-side." empty state (no scary "Try again" / "Failed" copy)

### 5c — Bug 3 (asymmetric specs)
1. Home → search "iPhone 17 vs Galaxy S25 Ultra"
2. Compare
3. **Expect:** BOTH products show non-empty values for Front Camera + Water Resistance (not "N/A", not hidden)
4. Bonus: training-data values may show a subtle indicator (frontend rendering of `_field_confidence` is a follow-up — current commit only stamps the data on the backend)

### 5d — Bug 4 (currency)
1. Home → search "Louis Vuitton Neverfull vs Gucci Marmont" (or similar luxury bags)
2. Compare
3. **Expect:** prices labeled BHD in plausible range (~1000-3000 BHD), NOT 2998+ BHD
4. If you see 2998+ BHD: backend logs should now show `[CURRENCY] No rate for XYZ->BHD` warning instead of silent pass-through

---

## Step 6 — Sentry sweep (1h post-deploy)

Open https://qaren-rr.sentry.io/issues/ — confirm no NEW error classes appearing in the last 1h with tag `release=<post-bucket-a-build>`.

Watch list:
- `extract_specs_targeted` failures (new code path)
- `_smart_fallback_extract` exceptions (new code path)
- `getComparison(id)` 401/404 from ResultsScreen
- `identifyFromImages` failures from ResultsScreen
- `[CURRENCY]` WARNING entries — if any new currency code appears, add to FALLBACK_RATES in a follow-up commit

---

## Rollback triggers

Roll back ANY single bug fix independently — do NOT mass-revert.

### Bug 4 (currency) — feea3fe + 8331322 + 91a4035
**Symptom:** currency conversion produces wildly wrong amounts (e.g. 100 USD now displays as 0.0001 BHD instead of 37.6).
**Action:** `git revert 8331322 91a4035 feea3fe && git push origin main`
**Impact:** currency goes back to silent 1.0 multiplier (same as pre-fix); no data corruption.

### Bug 1 (history) — 8051579 + 8b5e5d8 + 94f8958
**Symptom:** history tap shows persistent loading spinner OR 401 redirect loop OR crash.
**Action:** `git revert 94f8958 8b5e5d8 8051579 && git push origin main` + `eas update --branch preview --message "rollback Bug 1"`
**Impact:** history goes back to "No comparison loaded" empty state (same as pre-fix); no data loss.

### Bug 2 (camera) — fa62aaf
**Symptom:** camera Compare crashes OR loops forever on identifying.
**Action:** `git revert fa62aaf && git push origin main` + `eas update --branch preview --message "rollback Bug 2"`
**Impact:** camera Compare silent again (same as pre-fix).

### Bug 3 (asymmetric specs) — b1f18d7 + 0e2167e + 4791ca0
**Symptom — highest risk:** comparison wall-time exceeds 30s consistently OR specs become MORE asymmetric OR Serper credits draining unexpectedly.
**Action:** `git revert 4791ca0 0e2167e b1f18d7 && git push origin main`
**Impact:** specs go back to asymmetric (same as pre-fix); wall time returns to ~19s baseline.

### Spec-parity test (4923d37) and extra coverage (91a4035)
Test-only commits. Safe to leave even after a revert of related production code — tests just describe expected behavior.

---

## Post-deploy checklist updates

- [ ] Update CLAUDE.md "Bundle history" section with Bucket A commit list + EAS Update group ID
- [ ] Update `MEMORY.md` Pending follow-ups: remove "Bucket A bugs" if added; add note on `_field_confidence` rendering as a frontend follow-up (training_data indicator)
- [ ] Mention Bucket A as the post-D1 baseline in `docs/SESSION_BUNDLES.md` for the next-up D2 Section 3 work
- [ ] Note Serper credit burn rate change in MEMORY.md (smart-fallback adds up to 2 extra queries per comparison when critical fields are missing)
