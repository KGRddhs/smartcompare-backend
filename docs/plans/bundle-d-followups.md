# Bundle D — v1.2 follow-ups

> Explicit deferral log for items punted from Bundle D scope. Each entry
> names the pinning commit + the design input needed to unblock. Future
> agents working on the v1.2 round read this before re-scoping.

---

## A.8.2 — Unify dimension provenance via CATEGORY_DIMENSIONS purist adapter

**Pinned by:** A.8.1 Reading 1 (commit `8dac7cc`).

**Current state (Bundle D, Reading 1):** electronics keeps the hand-coded
`_dim_dpi` / `_dim_popularity` / `_dim_build_quality` builders that
compute fresh values from raw `products[i]["specs"]` (DPI, review_count,
warranty_years) with category-specific `delta_text` ("460 DPI vs 415
DPI", "1500 reviews vs 1200", "1-year vs 2-year warranty"). The 8 other
categories (grocery / supplements / makeup / skincare / haircare /
fragrances / fashion / other) use a generic adapter
`_dim_from_category_lookup` that pulls scores from
`scoring_result["scores"]["product_i"][dim_key]` with `delta_text=""`.

**A.8.2 ask (Reading 2 of A.8.1):** delete the 3 hand-coded
electronics builders. Drive ALL 6 dims across all 9 categories from a
single source of truth: `CATEGORY_DIMENSIONS[category]` +
`scoring_result["scores"]`. Add a label-map + delta_text generator that
produces sensible category-typed prose deltas for every dim
(e.g., electronics `performance_score` → "Geekbench 2200 vs 1900",
supplements `dosage_score` → "20mg vs 10mg",
fragrances `longevity_score` → "8-hour wear vs 4-hour", etc.).

**Why deferred (Ahmed rule discipline):**
1. Bundle D scope is TestFlight ship in 2-3 days. Reading 1 fixes the
   immediate UX gap (non-electronics categories ship 6 dims instead of
   3) without disturbing the working electronics path.
2. Reading 2 requires **design input on the 9 categories × 6 dimensions
   = 54-cell copy grid** — what's the label for `evidence_score` in
   skincare? `cpw_score` in fashion? `serving_value_score` in grocery?
   That's not mechanical polish; it's product copywriting.
3. The "parallel provenance" inconsistency (electronics fresh-from-spec
   vs others scores-from-result) is a known live state, not new with
   Reading 1. Reading 1 IMPROVES the non-electronics path without
   making electronics worse.

**Unblockers needed before A.8.2 ships:**
- [ ] Ahmed-approved label map for all 54 cells (currently
  `app/services/scoring_service.py:_DIMENSION_LABELS` covers 54 keys
  with first-pass labels but copy is dispatcher-authored, not
  product-team-approved).
- [ ] Per-category delta_text generator design — how does
  `efficacy_score` for "300mg curcumin" vs "150mg curcumin" become
  natural prose? Likely needs per-category templates fed by which spec
  fields back each dim. The `_DIMENSION_SIGNAL_MAP` in
  `scoring_service.py:1204` already maps dim → signal type; a sibling
  `_DIMENSION_DELTA_TEMPLATE_MAP[category][dim_key]` could mechanize it.
- [ ] Test fixture set — 9 categories × representative product pair
  each, so trust validation can pass on regenerated delta_text.

**Cost estimate when unblocked:** ~90-120 min implementation + ~60-90 min
test fixture authoring. Single 4-Opus session with design as Ahmed-facing
agent.

**Acceptance once shipped:**
- Single `build_dimensions_v2` body, no per-category branching on
  `category == "electronics"`.
- `_dim_dpi` / `_dim_popularity` / `_dim_build_quality` deleted (or
  preserved only as test fixtures behind a v1.1-compat flag).
- All 9 categories return up to 6 dims with non-empty `delta_text`.
- 54-cell label coverage test still GREEN.

---

## v1.1 generic-adapter dims ship with empty delta_text

**Pinned by:** A.8.1 Reading 1 + A.8.2 above.

**Current state:** non-electronics dims from `_dim_from_category_lookup`
ship `delta_text=""`. Frontend renders the score numerically with no
prose delta.

**v1.2 ask:** Phase 2 of A.8.2 fills these dims with category-typed
prose. Sub-entry of A.8.2; this row is the FE-visible symptom that the
purist adapter is needed.

**Acceptance:** dims tab on a skincare / fragrance / supplement
comparison shows delta strings like "Stronger evidence base —
clinical-grade actives", not blank captions.

---

## NATIVE-OPS: App Store production icon regeneration (post-TestFlight)

**Pinned by:** Bundle D Task #32 close 2026-05-24 (Ahmed-approved
concentric-circles visual design adopted; CLAUDE.md "🚨 APP STORE
PRODUCTION SHIP-BLOCKERS" §1 captures the same finding).

**Current state (Bundle D, Reading 1):** Bundle D shipped the
Claude-Design concentric-circles icon design that Ahmed approved
visually. The PNG bytes at `SmartCompareApp/assets/{icon,splash-icon,
adaptive-icon}.png` are byte-identical (SHA-256-verified by native-ops
during Task #32) to Expo's `npx create-expo-app` template scaffolding.
Claude-Design's export bundler used the scaffold as base + applied
design tokens at render time but exported the raw scaffold PNG.

Files genuinely unique already:
- `SmartCompareApp/assets/logo-wordmark.png` (SHA-256
  `d99ce6bb5cfa05e8b4fa4fff307fd9db09c69db06897cabb302cabcd8172152c`,
  5318 bytes) — Claude-Design wordmark, Frontend consumes via
  QarenLogo. NOT subject to ICN-0001.

Files affected (3, all visually approved by Ahmed):
- `SmartCompareApp/assets/icon.png` — SHA-256 `74c64047eb557b13...`
- `SmartCompareApp/assets/splash-icon.png` — SHA-256
  `5f4c0a732b6325bf...`
- `SmartCompareApp/assets/adaptive-icon.png` — SHA-256
  `5f4c0a732b6325bf...` (byte-equal to splash-icon)

**Why deferred:** TestFlight internal testing (≤100 invited testers,
no Apple Review) accepts these icons fine. Apple's ICN-0001 ("App
uses placeholder content") gate fires only on App Store production
submission. Ahmed's Bundle D scope is "TestFlight ready" not "App
Store live" — so the byte-identity is a Bundle E / v1.2 concern, not
a Bundle D blocker.

**Reading 2 ask (pre App Store production submission):** regenerate
the 3 icons as bytes-different PNGs while preserving the
Ahmed-approved concentric-circles visual. Two approaches:

1. **Claude-Design re-export with bytes-different output** (preferred —
   Ahmed gets to verify visual still matches his preference):
   - Re-run the Claude-Design tool with a flag/setting that produces
     unique bytes for the same visual output
   - Effort: 5-10 min Ahmed-side, then native-ops re-runs the cp + commit

2. **`scripts/regen-icons.py` via PIL** (fallback if Ahmed doesn't want
   to re-engage Claude-Design):
   - Load the current `assets/icon.png`
   - Apply a near-imperceptible visual variation that breaks byte-identity:
     emerald `#10B981` accent on the outer ring (3-5px), OR a tiny
     wordmark watermark in a transparent corner pixel block (1-2%
     opacity), OR a hidden steganographic byte pattern that doesn't
     affect rendering
   - Re-save → new SHA-256 + same visual
   - Effort: ~30 lines of Pillow + 10-15 min author + Ahmed visual review

**Unblockers checklist:**
- [ ] Ahmed picks approach (1) Claude-Design re-export vs (2) PIL script
- [ ] If (1): Ahmed re-runs Claude-Design tool → ships new PNGs to
  `docs/claude-design-handoff/assets/` → native-ops cp + commit
- [ ] If (2): native-ops authors `scripts/regen-icons.py` → runs once
  → commits the 3 regenerated PNGs at the same dest paths

**Cost estimate when unblocked:** ~10 min once approach (1) re-export
or approach (2) script lands.

**Acceptance once shipped:**
- `sha256sum SmartCompareApp/assets/{icon,splash-icon,adaptive-icon}.png`
  returns 3 different hashes from the current `74c64047...` / `5f4c0a73...`
  / `5f4c0a73...` set
- Visual diff against current icons: ZERO perceptible change (Ahmed
  approves)
- Apple App Store submission ICN-0001 gate passes during the next
  `eas submit --profile production` attempt

**NOT a TestFlight blocker.** Phase 3 Task 3.N.2 ASC TestFlight upload
proceeds with the current byte-identical PNGs because Apple's
TestFlight review doesn't run ICN-0001.

---

## Notes on adding new entries

When you defer a Bundle D scope item to v1.2:
1. Add a `## <ID> — <one-line summary>` section here.
2. Cite the pinning commit SHA (`<incoming SHA>` style if not yet
   landed; concrete SHA after landing).
3. Document the current Reading 1 / minimal state.
4. Document what Reading 2 / full state requires.
5. List unblockers (design input, dependency, cost) as a checklist so
   future agents know what changed before they can pick it up.

Discipline check before adding: this file is for items genuinely
out-of-scope, not for "we ran out of time" — Ahmed rule #1 means we
ship 100%. If you're tempted to log something here mid-Bundle-D, ask
the dispatcher first whether it's a real scope question or just a
pacing issue.

---

## FRONTEND: HomeScreen 4 editorial sections (deferred from Bundle D)

Pinning commit: `<incoming SHA from HomeScreen integration>` (option (a) approved by team-lead 2026-05-24).

Claude-Design `HomeScreen.jsx` (commit `0b87415`, `docs/claude-design-handoff/ui_kits/mobile/HomeScreen.jsx`) ships 4 editorial sections below the compare card that Bundle D explicitly defers. Would expand scope ~50%, require new backend APIs + 30+ i18n keys + tests. Stubbed via `<View testID="home-editorial-stub" style={{ height: 0 }} />` in `src/screens/HomeScreen.tsx` at the render position where the sections would go — single React-tree-neutral marker so Bundle B preservation tests don't false-positive on "missing section" + future maintainer can grep `home-editorial-stub` to find the deferral point.

### Deferred sections (in render order)

1. **SmartPickCard** — Personalized winner story (Claude-Design source: HomeScreen.jsx:438-501).
   - Backend dep: new endpoint e.g., `GET /api/v1/home/smart-pick?user_id=<uid>` returning `{winner, runner_up, prices, reasoning}`. Pulls from `users.behavior_profile` + comparison history.
   - i18n: ~6 keys (`home.smartPick.title`, `.eyebrow`, `.updatedToday`, `.cta`, `.fallbackReasoning`, `.emptyState`).

2. **QuickCategories** — 4-tile grid Electronics/Skincare/Supplements/Makeup (Claude-Design source: HomeScreen.jsx:534-570).
   - Could ship cleanly with i18n only + existing `CategorySelector` route — **lowest Bundle E lift; consider promoting early.**
   - i18n: 1 eyebrow + 4 category labels (already in `home.categories.*` namespace; only need the section eyebrow `home.quickCategories.eyebrow`).
   - No backend dep.

3. **SavingsBanner** — Aggregate "X BHD saved, Y decisions sorted" stat (Claude-Design source: HomeScreen.jsx:573-605).
   - Backend dep: new endpoint aggregating user's comparisons + estimated price-savings deltas. Could be served from `users.preferences.savings_stat` cached server-side; nightly cron job.
   - i18n: ~4 keys (`home.savings.eyebrow`, `.amount`, `.context`, `.emptyState`).

4. **TrendingNearYou** — 3 trending product pairs by region (Claude-Design source: HomeScreen.jsx:608-651).
   - Backend dep: needs anonymized aggregation across `search_logs` + region-aware ranking. **Heaviest lift** — privacy review required for cross-user trend exposure.
   - i18n: ~3 keys (`home.trending.eyebrow`, `.viewCount`, `.emptyState`).

### Acceptance criteria for un-deferral (any bundle that promotes these)

- All 4 sections wired to real backend endpoints (no hardcoded data).
- i18n keys added to EN + AR with copy-policy gate passing (no scary vocab, no "Best Pick"/"Winner"/"Best for" per `.copy-policy.json`).
- Per-section preservation test added to `__tests__/HomeScreen.bundleB.contract.test.tsx`.
- Cross-QA + R16 device-leg verification at next EAS preview build.
- Bundle B contract still holds: `TwoInputShell` mounted, paste-split + mode-switch still fire, 8 analytics events (`compare_entry_view`, `paywall_banner_view`, `paywall_banner_tap`, `content_block`, `submit`, `paste_split`, `mode_autoswitch`, `ready`) still wired, paywall takeover on `!canCompare`, 1.2s min-display floor preserved, haptic vocabulary (chip:light / stage:light / winner:medium) intact.

### Cost estimate

- `QuickCategories`: ~2 hours (mostly i18n + reuse existing CategorySelector route)
- `SmartPickCard`: ~4-6 hours (backend endpoint + frontend wiring + behavior_profile read)
- `SavingsBanner`: ~4 hours (backend aggregation + frontend wiring)
- `TrendingNearYou`: ~8-10 hours (aggregation logic + region-aware ranking + privacy review)
- Total: **~18-22 hours**, likely a Bundle F or v1.1 deliverable. Recommend bundling all 4 in one PR so the editorial-content surface lands as a coherent block.

### Backend addendum 2026-05-23 — 3 of 4 endpoints ALREADY shipped

Bundle D Phase 2.5 reopen (per dispatcher "no deferral" direction) shipped
the 3 non-trivial backend endpoints. Tasks #71-#74. Frontend wiring of the
4 sections remains as the Bundle E followup; the backend dependency
is now unblocked for 3 of them:

- **SmartPickCard:** `GET /api/v1/home/smart-pick` shipped (auth required, 5min Redis cache, empty-state + cta_text_key contract).
- **SavingsBanner:** `GET /api/v1/home/savings` shipped (auth required, 5min Redis cache, `threshold_met` gate at count>=3).
- **TrendingNearYou:** `GET /api/v1/home/trending` shipped via **Approach A** (curated JSON at `data/trending_curated.json`, zero PII surface, 1h Redis per-region cache, auth-optional with `?region=` query). Approach B (search_logs k-anonymity) deferred — see entry below.
- **QuickCategories:** no backend dep — pure FE i18n work, can ship as soon as Frontend has bandwidth.

---

## BACKEND: `/home/trending` Approach B — k-anonymity search_logs aggregation

**Pinned by:** Bundle D Phase 2.5 `/home/trending` shipping with Approach A (curated JSON) — commit `<incoming SHA from 2.5.B closeout>`.

**Current state (Approach A, shipped Bundle D):** `data/trending_curated.json` is a hand-maintained per-region list. Admin updates weekly via PR. Zero PII surface. Frontend renders directly. ~6 trending pairs per region.

**Approach B ask (Bundle E or later):** dynamically aggregate `search_logs` to surface real trending queries with a k-anonymity privacy gate:

```sql
SELECT query_text, COUNT(DISTINCT user_id) AS unique_users
FROM search_logs
WHERE created_at >= now() - interval '7 days'
  AND region = $1
GROUP BY query_text
HAVING COUNT(DISTINCT user_id) >= 50  -- k-anonymity threshold
ORDER BY unique_users DESC
LIMIT 10
```

Plus a PII-regex pre-filter on `query_text` to reject any query containing email-shape, phone-shape, or free-text-personal-name patterns even if it clears the k≥50 gate.

**Why deferred from Bundle D:**
1. TestFlight scope = ≤100 testers (won't hit k=50 threshold per region for ~3 months post-launch). Approach B would return empty trending = worse UX than Approach A's curated list.
2. PII regex pre-filter needs a privacy review with Ahmed (what patterns? email yes/no/case-by-case? phone? brand-name + personal-name combinations?).
3. Approach A is genuinely sufficient for the editorial-section UX intent (give users 3-6 starter ideas) — k-anonymity adds operational complexity without proportional user-value gain in the TestFlight + soft-launch period.

**Unblockers checklist (before Bundle E ship):**
- [ ] Ahmed-approved PII regex set (suggest: email RFC pattern, phone E.164 international, free-text-name detector via spaCy NER or simple regex denylist).
- [ ] DAU > 500 in a single region (k=50 unique-users threshold becomes meaningful at ~10x DAU).
- [ ] Bundle E-or-later capacity for: aggregation SQL view, weekly cron to materialize results into a `trending_aggregated` table, fallback-to-curated when k-anonymity returns empty, admin dashboard to monitor PII-filter rejection rate.

**Acceptance once shipped:**
- New endpoint OR same `/home/trending` route with `?source=aggregated` flag.
- Returns the curated list (Approach A) when aggregated returns fewer than 3 entries that pass k-anonymity + PII filter.
- Per-day PII-filter rejection rate < 5% (if higher, the regex is too aggressive OR the upstream queries are too PII-heavy → product team intervention).
- Privacy review sign-off from Ahmed before any aggregated endpoint goes live in prod.

**Cost estimate when unblocked:** ~6-8 hours implementation + ~2-3 hours privacy review.

