# Bundle E S3 — Lane A1 element-order checklist

> **Contract with peer-QA (A4):** Every REWRITE must satisfy element order top-down per JSX source of truth. Marks below are the pre-rewrite (current-state) audit.
>
> Legend: ✓ present + correct order · ↕ present but wrong order · ✗ missing · 💀 in `.tsx` but NOT in JSX (DELETE list)

---

## HomeScreen (JSX 1-717)

JSX source: `docs/claude-design-handoff/ui_kits/mobile/HomeScreen.jsx`
Current TSX: `SmartCompareApp/src/screens/HomeScreen.tsx` (1099 lines)

### Top-down JSX element order
1. **Container** [JSX:661-672] — `paddingTop: 50` (status-bar inset), bg.primary, column flex
2. **Header** [JSX:674-683] — `headerLeft` (QarenLogo 24px + "Qaren" word 700/20) + `HeaderCounter` (right-pill counter `{free}/{total} free · +{bonus}`)
3. **Hero copy** [JSX:685-691] — `<p>` "Compare anything." 600/16
4. **CategoryStrip** [JSX:693, 391-432] — horizontal scroll of 5 cats (Electronics/Grocery/Supplements/Makeup/Skincare) with stroke icons + emerald-active fill
5. **`<main>` scroll body** [JSX:695-709]
   1. **CompareCard** [JSX:163-220]
      - **ModeSegment** [JSX:111-160] — pill-container (radius 999, border, 4px padding) housing 3 tabs (Scan/Link/Type) with black-fill active state
      - **Body** [JSX:179-197] — `<ScanBody>` OR `<TwoInputBody>` based on `mode`
      - **Compare CTA** [JSX:199-217] — full-width 48px-tall black button at bottom; label "Open camera" (scan) / "Compare" (link/type); emerald glow when valid; opacity 0.5 when invalid
   2. **SmartPickCard** [JSX:438-501] — eyebrow "Smart pick of the day" + editorial card (category pill + updated chip + 2 PickTiles flanking center "vs" + reason text + "See full verdict" CTA)
   3. **QuickCategories** [JSX:534-570] — eyebrow "Jump back in" + 2×2 grid of 4 cat tiles
   4. **SavingsBanner** [JSX:573-605] — dark inverse bg, "~240 BHD shopped smarter" hero
   5. **TrendingNearYou** [JSX:608-651] — eyebrow "Trending in Capital" + 3-row list (tag pill + "A vs B" + count ↗)
6. **TabBar** [JSX:711, 352-388] — 3-icon bottom nav (Qaren/History/Profile, active = home, emerald accent)

### Current TSX audit (element-by-element)
| # | JSX element | Status | Notes |
|---|-------------|--------|-------|
| 1 | Container/SafeAreaView | ✓ | TSX:570 uses `SafeAreaView` (RN equivalent) |
| 2a | QarenLogo 28 + "Qaren" word | ✓ | TSX:573-574 (`size={28}` vs JSX 24 — token-acceptable drift) |
| 2b | HeaderCounter pill | ✓ | TSX:576-622 — last-free emerald accent variant present |
| 3 | "Compare anything." hero | ✓ | TSX:625 — `t('home.hero')` |
| 4 | CategoryStrip | ✓ | TSX:627-632 — uses `CategorySelector` component |
| 5.1a | ModeSegment (pill container w/ radius 999) | ↕ | TSX:644-686 renders 3 ModeChip components on a `modeChipRail` with `gap`; JSX wraps in a single pill container (`borderRadius: 999`, `padding: 4`, inline gap). Currently each chip has its own border + radius; JSX wants ONE outer container border + 4 inner pill tabs. |
| 5.1b | ScanBody / TwoInputBody | ✓ | TSX:411-553 `renderCenterArea()` |
| 5.1c | **Compare CTA button** (full-width, black, bottom of CompareCard) | ✗ | **MISSING**. TWoInputShell may have its own internal submit, but the JSX has a single primary black CTA INSIDE the CompareCard at the bottom — label changes with mode. |
| 5.2 | SmartPickCard | ✓ | TSX:701-715 via `HomeEditorialSections` wrapper |
| 5.3 | QuickCategories | ✓ | via wrapper |
| 5.4 | SavingsBanner | ✓ | via wrapper |
| 5.5 | TrendingNearYou | ✓ | via wrapper |
| 6 | TabBar | n/a | Lives in `App.tsx` (bottom-tab navigator); not part of HomeScreen render. |

### REWRITE actions (JSX line cites)
- **REWRITE ModeSegment** [JSX:111-160]: collapse 3 individual `ModeChip` cards on a flex-row rail into ONE pill-shape container (`borderRadius: 999`, `padding: 4`, `gap: 4`, border `colors.border.light`, bg `colors.bg.primary`). Each tab is a flex:1 inner pill (radius 999, height 36) that fills with `colors.cta.primary` + onPrimary text when active, transparent + text.secondary otherwise. Drop the per-chip `borderColor` + `borderWidth` (the container owns the border now).
- **ADD Compare CTA button** [JSX:199-217]: full-width, 48px-tall, `cta.primary` background, `cta.onPrimary` text, 600/16. Label: `home.cta.openCamera` when `inputMode === 'scan'`, `home.cta.compare` otherwise. Disabled (opacity 0.5) when no valid pair (text mode: both inputs ≥ 2 chars; scan: always allowed; url: both URLs non-empty). Emerald glow shadow when valid. On press: route to scan (camera) or call existing `handleTextCompare`/`handleUrlCompare`. **The CTA replaces the implicit "submit on TwoInputShell button" — JSX has the CTA INSIDE CompareCard, not inside TwoInputShell.**
- **REWRITE HomeEditorialSections render**: the wrapper currently uses an internal ScrollView (`testID="home-editorial-scroll"`). Per JSX the 4 sections live as flat siblings inside the main `<main>` ScrollView. Either keep the wrapper but drop its inner ScrollView, or inline the 4 sections directly. Element order: SmartPickCard → QuickCategories → SavingsBanner → TrendingNearYou.

### DELETE list (TSX elements not in JSX)
- 💀 `void serverOnline` line + the `setServerOnline` plumbing (TSX:107, 195-202, 556-557) — JSX has no health-state UI. Keep `healthCheck()` call for analytics-side telemetry but drop the screen-level state.
- 💀 `home-editorial-stub` 0-height marker view (TSX:699). JSX has no stub.
- 💀 Loading overlay (TSX:718-723) — JSX has none. The screen navigates immediately to Results via `navigateToResultsWithFloor` so overlay never lasts long enough to matter. **KEEP** as a guard — it's a non-JSX-conflicting safety net for slow responses. Audit-note: NOT a DELETE candidate.

---

## ProfileScreen (JSX 1-323)

JSX source: `docs/claude-design-handoff/ui_kits/mobile/ProfileScreen.jsx`
Current TSX: `SmartCompareApp/src/screens/ProfileScreen.tsx` (869 lines, header already cites "Bundle E F-S1.5c REWRITE")

### Top-down JSX element order
1. **Container** [JSX:301-308] — column flex, `paddingTop: 50`, bg.primary
2. **`<main>` scroll** [JSX:309-317] — overflow scroll, flex:1, paddingBottom 12
   1. **ProfileHeaderRow** [JSX:34-51] — Qaren logo (28) + name (700/18) + region subtitle (400/12 "Capital · GCC") + settings icon (36px circle bg.secondary)
   2. **EditorialHeadline** [JSX:53-55] — RETURNS NULL (intentional). Skip rendering.
   3. **RecentDecisions** [JSX:122-161] — eyebrow "Recent decisions" + "See all" link + horizontal scroll of 3 MiniVsCard items
   4. **PrioritiesInline** [JSX:163-200] — "What shapes your matches" heading + 3 weighted bars (label + bar + %) + "Tune my priorities" black CTA
   5. **MonthStrip** [JSX:202-221] — 3-tile stat strip (decisions / BHD saved subtle (emerald num) / bonus credits)
   6. **FlatSettings** [JSX:251-275] — ONE bordered card with 4 eyebrow groups: ACCOUNT / PRIVACY & NOTIFICATIONS / HELP / DANGER ZONE
3. **TabBarP5** [JSX:318, 278-298] — bottom 3-icon nav

### Current TSX audit
| # | JSX element | Status | Notes |
|---|-------------|--------|-------|
| 1 | Container/SafeAreaView | ✓ | TSX:402 |
| 2.1 | ProfileHeaderRow | ✓ | TSX:331-352 — Q logo + name + `regionSubtitle` ("{governorate} · GCC") + 36px settings circle. **Matches JSX top-down.** |
| 2.2 | EditorialHeadline (null) | ✓ | Correctly omitted. |
| 2.3 | RecentDecisionsRow | ✓ | TSX:411-417 — silent-hides, see-all routes, empty-card routes Home. |
| 2.4 | PrioritiesInline | ✓ | TSX:420 — sum-100 backend (Path A R2) feeds 3 bars + Tune CTA. |
| 2.5 | MonthStrip | ✓ | TSX:423 — 3-tile decisions/BHD/bonus. |
| 2.6 | FlatSettings | ✓ | TSX:426-590 — one bordered card containing all 4 eyebrow groups. |
| 3 | TabBar | n/a | Lives in `App.tsx` (bottom-tab navigator). |

### REWRITE actions
**ProfileScreen.tsx already largely satisfies the JSX top-down structure.** The shipped F-S1.5c REWRITE (header comment cites JSX:36-322) brought it into shape. S3 deltas are minor surgical tightening:
- **Tighten eyebrow visual** [JSX:239-250 vs TSX:711-726]: JSX uses padding 10/16, hairline top+bottom borders, `bg.primary` background (eyebrows visually break the bordered card). TSX matches. ✓
- **Verify "See all" routes to History tab** [JSX:145-150]: TSX:415 → `navigation.navigate('HistoryTab')`. ✓
- **Bonus visual fidelity probe (cite-JSX)**: MonthStrip middle tile's `n` color uses `accentDark` (subtle), borders use `border.light`, padding 14, radius 16. TSX checks at `ProfileEditorialSections` — verify subtype-card tokens align.
- **Add per-row testIDs for peer-QA grep**: the SettingsRows already carry `profile-row-edit`/`profile-row-language`/etc. testIDs. Ensure each new test pin asserts presence + parent eyebrow.

### DELETE list (no live DELETEs; already executed in F-S1.5c)
Per the existing TSX header comment, F-S1.5c already deleted:
- 💀 brandTitleRow + screenTitle "Profile" h1
- 💀 StyleProfileCard at top-level (data moved into header)
- 💀 ReferralStatusCard
- 💀 Standalone Account-card avatar block
- 💀 B6 Upgrade card with Sparkles icon (now a row inside ACCOUNT eyebrow group)
- 💀 4 standalone sectionLabel + Card blocks

S3 audit confirms none of these have crept back into the file. No new DELETEs required.

### Risk callouts
- The inline `ProfileHeaderRow` / `SettingsEyebrow` / `SettingsRow` are defined inside the parent component (TSX:331-399). RN will re-create their React components on every parent re-render. Acceptable cost given they're simple, but flag for refactor if profiling shows churn.
- `useFocusEffect` fires loadUser + loadCohortProfile + loadPreferences in parallel on every focus. Network thrash risk if user thrashes tabs. NOT a S3 fix candidate.

---

## EditProfileScreen (JSX 1-233)

JSX source: `docs/claude-design-handoff/ui_kits/mobile/EditProfileScreen.jsx`
Current TSX: `SmartCompareApp/src/screens/EditProfileScreen.tsx` (384 lines)

### Top-down JSX element order
1. **Container** [JSX:160-166] — column flex, `paddingTop: 50`, bg.primary
2. **EpHeader** [JSX:23-43] — back-chevron 18px + centered title "Edit Profile" 700/17 + 36×36 spacer for symmetry
3. **`<main>` scroll** [JSX:169-207]
   1. **AvatarBlock** [JSX:45-63] — 96×96 circle bg.secondary + 36/700 initial + "Photo upload coming soon" caption
   2. **EyebrowHeader "Account"** [JSX:65-74, 172] — eyebrow 600/11 uppercase, ls 1.1, paddingInline 20
   3. **FormCard** [JSX:76-87, 173-185] — bordered card with 2 stacked `<Field>`s (Display name + Email read-only)
   4. **NavRow "Edit style profile"** [JSX:122-148, 187-191] — star icon (36px circle) + label + sub "Update priorities, budget, and brand stance" + chevron-right (no card wrap, just inline row)
   5. **EyebrowHeader "Account actions"** [JSX:193]
   6. **Delete card** [JSX:194-206] — bordered card containing ONE NavRow with trash icon + "Delete account" destructive (no chevron because destructive)
4. **Sticky Save CTA** [JSX:210-228] — bottom-fixed `<div>` with top border + bg.primary + paddingTop 12 + paddingBottom 16, hosting full-width black 52px-tall pill button. Disabled state opacity 0.4, label "Save".

### Current TSX audit
| # | JSX element | Status | Notes |
|---|-------------|--------|-------|
| 1 | Container/SafeAreaView | ✓ | TSX:138 |
| 2 | EpHeader (back + centered title + symmetric spacer) | ✓ | TSX:139-150 (chevron 24 vs JSX 18 — minor token drift) |
| 3.1 | AvatarBlock (96×96 + caption) | ✓ | TSX:154-159 with 96-bumped avatar per existing Bundle D fix |
| 3.2 | Eyebrow "Account" | ↕ | TSX:162 uses `sectionLabel` (typography.eyebrow). JSX uses a custom `EyebrowHeader` 600/11 with `paddingInline: 20` + `marginBottom: 8` + `marginTop: 12`. Visual end-state similar; minor spacing tweak. |
| 3.3 | FormCard (2 Fields stacked: Display name + Email read-only) | ↕ | TSX:163-199 wraps both in `styles.card` — visual ≈ JSX FormCard. Apple relay masking already shipped. |
| 3.4 | NavRow "Edit style profile" (icon-circle + label + sub + chevron) | ↕ | TSX:201-209 renders `linkRow` but is missing: (a) the 36×36 icon-circle with star glyph, (b) the sub-text "Update priorities, budget, and brand stance". |
| 3.5 | Eyebrow "Account actions" | ✗ | **MISSING**. TSX uses `dangerLabel` eyebrow for "Danger zone" but that's a different label. JSX explicitly uses "Account actions" as the eyebrow above the Delete card. |
| 3.6 | Delete card (bordered, single NavRow with trash icon, destructive) | ↕ | TSX:228-242 — destructive `dangerRow` is NOT wrapped in a bordered card and is missing the trash icon. |
| 4 | Sticky Save CTA (bottom-fixed, full-width black 52px pill) | ↕ | **TSX:213-225 places the Save CTA INSIDE the ScrollView**, not pinned to the bottom. JSX uses an absolute/sticky footer outside the scroll. UX impact: on long screens the Save button scrolls out of view. |

### REWRITE actions
- **REWRITE Save CTA placement** [JSX:210-228]: move the Save `<TouchableOpacity>` OUT of the `<ScrollView>` into a sibling `<View>` at the SafeAreaView level (after the ScrollView, before SafeAreaView closes). Style: top hairline border, bg.primary background, paddingHorizontal lg, paddingTop md, paddingBottom md. Button: full-width, 52px tall, radius 999 (pill), bg cta.primary, color cta.onPrimary, opacity 0.4 when disabled.
- **REWRITE eyebrow label** [JSX:193]: split the existing "Danger zone" into "Account actions" wrapping a bordered card with ONE destructive NavRow. Remove the standalone Save CTA from the mid-scroll position (covered above).
- **ADD NavRow icon + sub** [JSX:122-148, 187-191]: the "Edit style profile" linkRow needs:
  - 36×36 icon-circle on the left (bg.primary background, lucide `Star` icon, color `text.primary`)
  - Sub-line below the label: "Update priorities, budget, and brand stance" (400/12 text.secondary)
  - Right-side chevron stays
- **WRAP Delete in bordered card** [JSX:194-206]: the destructive row should sit inside a `bg.secondary` card with border `border.light` and radius 16. The destructive row itself gets the trash icon (lucide `Trash2`) in the 36×36 icon-circle pattern.

### DELETE list (TSX elements not in JSX)
- 💀 Inline `errorText` rendered between linkRow and Save (TSX:211). JSX has no inline error here. **KEEP** as a UX guard — error states are JSX-implicit, not JSX-forbidden. Audit-note: NOT a DELETE candidate.

### Risk callouts
- The Save CTA is the load-bearing UX change. Tests must assert it's at the SafeAreaView level (sibling to ScrollView), NOT inside scroll content.
- The icon-circle pattern recurs across NavRow + Delete card. Consider a small file-local `IconCircle({ icon })` recipe to keep DRY without churn.

---

## Acceptance contract with A4

When peer-QA reviews:
1. Read the JSX line ranges cited above
2. Check element order in the post-REWRITE `.tsx` matches the JSX top-down list
3. Grep the post-REWRITE `.tsx` for stale `home-editorial-stub` / `void serverOnline` / inline `errorText` mid-scroll Save / "Danger zone" eyebrow label — verify the DELETE list executed
4. Run the bundled `*.bundleE.s3.test.tsx` files; verify each test name maps to a checklist row above
5. Run `npx jest --coverage --collectCoverageFrom='src/screens/{HomeScreen,ProfileScreen,EditProfileScreen}.tsx'` — verify ≥ 80% on all three
6. If any checklist row is unimplemented or wrong, SendMessage to A1 with the specific row number + JSX line cite

End of A1.1 checklist.
