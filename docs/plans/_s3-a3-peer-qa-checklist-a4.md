# A3 → A4 Wave 2 Peer-QA Checklist

**Reviewer:** be-images (A3)
**Reviewee:** fe-images-qa-anchor (A4)
**Per ring assignment:** A3 reviews A4 (cycle: A1←A4, A2←A1, A3←A2, A4←A3)
**Filed:** 2026-05-30 by A3 during merge-wait per team-lead idle directive

Mirrors the § Cross-QA 9-point pattern from `docs/plans/2026-05-30-bundle-e-s3.md` but specialized for image-rendering surfaces. Target: ≤10 minutes per surface after A4 hands off.

---

## Surfaces A4 ships (per § A4 scope)

1. **ResultsScreen / ResultsContent** — winner + runner-up image cards
2. **HistoryScreen** — per-row mini-VS card image slots (2 per row)
3. **HomeScreen SmartPick** — winner_image_url + runner_up_image_url
4. **ProductImage primitive** — the shared component A4 introduces (per `0b4f463`)

Plus the QA-hub role: A4 ALSO reviews A1 (per ring). A3 does NOT double-review A1; only A4 here.

---

## A3 contract A4 must consume correctly

```typescript
// /text/compare response
response.products[i].image_url: string | null              // legacy alias path
response.overview.products[i].image_url: string | null     // canonical path

// SSE specs event
yield ("specs", { products: [{ ..., image_url: string | null }, ...] })

// /home/smart-pick payload
smart_pick.winner_image_url: string | null
smart_pick.runner_up_image_url: string | null
```

Critical: **null** when all tiers exhausted. **NOT** undefined (FE may type-narrow on null specifically). **NOT** empty string.

---

## 9-point peer-QA checklist (one pass per surface)

### 1. JSX source-of-truth verification

Per § A2/A4 lane plans, A4 should cite JSX line numbers in commit messages.

- [ ] Open the JSX referenced in A4's commit (e.g. `docs/claude-design-handoff/ui_kits/mobile/ResultsScreen.jsx`)
- [ ] Confirm the image slot lives where A4 wired it — same parent container, same sibling order
- [ ] Confirm aspectRatio matches JSX's `style={{ aspectRatio: X }}` or `<img width=W height=H>` ratio
- [ ] If JSX shows specific image dimensions, A4's React Native `<Image>` should match within ±10%

### 2. ProductImage primitive single-source-of-truth

- [ ] Grep `<Image source` across `src/screens/{ResultsScreen,HistoryScreen,HomeScreen}.tsx` — A4 should be using `<ProductImage>` (their primitive from `0b4f463`), NOT raw `<Image>` directly
- [ ] If raw `<Image>` is used outside the primitive: complaint with file:line citation
- [ ] Verify the primitive is the ONLY component that handles the 3-state fallback (URL / null / onError)
- [ ] Confirm no duplicate placeholder primitive — A4 must reuse, not introduce a new one (per ring brief: "use existing placeholder primitive — DO NOT introduce new one")

### 3. Three-state fallback rendering (THE critical state machine)

For each consumer surface (Results / History / SmartPick), render-test or component-test must cover:

- [ ] `image_url: "https://example.com/x.jpg"` → renders `<Image source={{ uri: "https://example.com/x.jpg" }} ... />`
- [ ] `image_url: null` → renders placeholder primitive (NOT empty space, NOT broken icon)
- [ ] `image_url: undefined` (legacy / pre-A3 data) → renders placeholder primitive
- [ ] `<Image>` `onError` fires (broken URL, network failure) → renders placeholder primitive

All 4 cases must have explicit Jest test assertions OR the surface is rejected. Per `memory/feedback_snapshots_as_staleness_liability.md`: prefer explicit-value assertions over snapshot diffs for load-bearing fallback invariants.

### 4. DELETE list executed (no stale Bundle D image placeholders)

- [ ] Grep for `placeholder.png` / `ImagePlaceholder` / older placeholder primitive names — should be 0 hits OR only inside the new ProductImage primitive
- [ ] Grep for `// TODO: image` comments — should be 0 hits (they violate "no deferrals" rule)
- [ ] If a stale placeholder lingers: complaint, cite line

### 5. aspectRatio + sizing per surface

Per the JSX-driven sizing spec (counts TBD pending A4's element-order checklist):

- [ ] Results winner card image: aspectRatio matches `ResultsScreen.jsx` value
- [ ] Results runner-up card image: matches its JSX value
- [ ] History row image: 2 images per row, smaller aspect ratio than Results (per JSX)
- [ ] SmartPick card image: TBD per `HomeScreen.jsx` SmartPick block

If A4 hardcodes the same aspectRatio across all surfaces without JSX justification: complaint.

### 6. No new native deps (S3 rule § Shared constraints #7)

- [ ] Check `SmartCompareApp/package.json` diff — no additions
- [ ] Specifically reject: `react-native-fast-image`, `expo-image` upgrades, image-caching libs
- [ ] `<Image>` from `react-native` (already in tree) is the ONLY acceptable image renderer

### 7. No backend internals leak in error states

Per `memory/feedback_no_backend_internals_in_reveals.md`:

- [ ] Error state does NOT surface "Tier 1 Serper Images failed" or any backend tier provenance to the user
- [ ] Sentry breadcrumbs from `<Image>` onError do NOT include the failed URL's hostname (PII / retailer leak)
- [ ] Placeholder fallback uses neutral copy — never "Could not load image" (scary copy banned per § Shared #8)
- [ ] Accessibility label is generic ("Product image" / equivalent in AR), not URL-revealing

### 8. Scary-copy + RTL hygiene

- [ ] Grep new code for banned EN vocab: `couldn't`, `try again`, `Failed to` — 0 hits
- [ ] Grep new code for banned AR vocab: `تعذر`, `فشل` — 0 hits
- [ ] If alt-text / accessibilityLabel is i18n'd: verify keys in `src/i18n/en.json` + `src/i18n/ar.json` both exist
- [ ] RTL: ProductImage primitive's wrapper does NOT use absolute positioning that would mirror incorrectly in RTL — verify via Jest mock of `I18nManager.isRTL`

### 9. Tests + coverage

- [ ] `npx jest --coverage --collectCoverageFrom='src/components/ProductImage.tsx'` ≥ 80%
- [ ] `npx jest --coverage --collectCoverageFrom='src/components/results/ResultsContent.tsx'` ≥ 80%
- [ ] `npx tsc --noEmit` exits 0
- [ ] All A4 tests GREEN (run the test file names from A4's commit messages)
- [ ] No snapshot test that captures broken-image alt text (per `feedback_snapshots_as_staleness_liability.md`)

---

## Independent smoke (one quick pass at end)

Mock the comparison response with:
- product_0.image_url = "https://valid-url.example/test.jpg"
- product_1.image_url = null

Render ResultsContent → eyeball:
- [ ] Product 0 card shows the image (or placeholder if Jest can't load remote)
- [ ] Product 1 card shows ONLY placeholder (no broken-image icon)
- [ ] Both cards have IDENTICAL frame size (placeholder doesn't collapse vertically)
- [ ] No console warnings about missing Image dimensions

---

## SendMessage shape on PASS

```
A4 — peer-QA PASS for Wave 2 image rendering.

Checklist (from docs/plans/_s3-a3-peer-qa-checklist-a4.md):
1. JSX source-of-truth verified ✓
2. ProductImage primitive single-source verified ✓
3. Three-state fallback (URL / null / onError) verified ✓
4. DELETE list executed (0 stale placeholders) ✓
5. aspectRatio per surface verified ✓
6. No new native deps ✓
7. No backend internals leak in error states ✓
8. Scary-copy + RTL hygiene clean ✓
9. Tests + coverage ≥80%, tsc 0 ✓

Independent smoke: ResultsContent renders 1-real-1-null state correctly,
no frame collapse, no broken-image icon.

Cleared for dispatcher merge per ring assignment.
```

## SendMessage shape on COMPLAINT

```
A4 — peer-QA FEEDBACK — N items to address before clearance:

1. [Surface] [JSX line cite] — [specific issue + expected fix]
2. ...

Per ring: address + re-SendMessage with re-review request.
A3 will re-run checklist within 5 min of receipt.
```

---

## Decision log: what passes vs. what blocks

**Passes (issue + ship):**
- aspectRatio off by <10% from JSX
- Placeholder copy slightly different from i18n key suggestion
- Test coverage 78-79% if missing branches are defensive guards

**Blocks merge:**
- Three-state fallback missing any state (URL / null / onError)
- New native dep
- Scary-copy vocab hit
- Raw `<Image>` outside ProductImage primitive
- Backend internals (tier, retailer URL, exception text) in user-visible state
- Coverage <70% on new components
- tsc errors
- Snapshot test pinning a buggy state without explicit-value assertion accompanying
