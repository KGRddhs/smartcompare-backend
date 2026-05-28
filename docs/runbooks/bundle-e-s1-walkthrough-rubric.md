# Bundle E — S1 Device-Walkthrough Rubric

**Author:** qa lane (Bundle E team)
**Date drafted:** 2026-05-26
**Day-2 refresh:** 2026-05-28 (post-day-1-walkthrough RED items folded in)
**Audience:** Ahmed (device walker) + qa lane (sign-off recorder)
**Purpose:** Side-by-side scan rubric — Ahmed opens each of the 8 surfaces on EAS preview, then opens the matching `.jsx` reference + `.png` screenshot in this repo, then walks the checkpoint list below.

## Day-2 RED carry-over (must re-walk on next EAS preview)

These items surfaced in Ahmed's day-1 device walkthrough on 2026-05-26 and have day-2 fixes either shipped or in-flight. Mark each fresh PASS/RED on next walk.

- **B1 — TrendingNearYou product names** — SHIPPED day-1 `85afd0e` (frontend was reading wrong field per reshape). Re-walk Home § 1 row 8.
- **B2 — HomeScreen ScanBody affordance** — day-1 patch `80448ed` was spec-correct (dashed PreviewRow) but UX-confusing (dashed buttons read as text-input rows, not snap targets). Day-2 task F-S1.4d redesigns: camera icon size 28 (was 18), `flexDirection: 'column'` (icon stacked above text), minHeight 72-80px, "Tap to snap" 14px 500 + "Product A" 12px 400 caption. Re-walk Home § 1 — dashed area must read as a tappable card, not an input row.
- **D1 — HistoryHeroStats marquee** — SHIPPED day-1 `6d47b3f`. Re-walk History § 3 row 1 (HeroStats marquee).
- **D2 — ProfileScreen FULL REWRITE** — day-1 patch `3ad84b1` was a SURGICAL EDIT on Bundle D ProfileScreen (eyebrows grafted onto Bundle D cards). Structurally wrong: header/avatar at bottom not top, missing RecentDecisions marquee + MonthStrip, broken PrioritiesInline (235% sum instead of 100% normalized). Day-2 task F-S1.5c REWRITES top-down against JSX:36-322 — header first, RecentDecisions, PrioritiesInline (Path A R2 sum=100), MonthStrip, FlatSettings as ONE rounded card with eyebrow-grouped rows. Re-walk Profile § 4 element-by-element.
- **D3 — ResultsScreen winner-card emerald bg from first render** — SHIPPED day-1 `b10e945` (variant gate decoupled from `winnerRevealed`; Card.tsx winner variant paints accentLight bg + 2px accent border immediately). Theatrical scale-spring + Best Pick badge slide-in still gate on `winnerRevealed` 800ms. Re-walk Results § 2 row 2 — winner card must look emerald-tinted from FIRST paint, not after 800ms.

## Day-2 product decisions (NOT in JSX, supersede prior rubric language)

- **Discreet Upgrade row in Profile FlatSettings ACCOUNT group** — JSX:259 does NOT include Upgrade. Day-2 decision: add a single Upgrade SettingsRow under the ACCOUNT eyebrow (between Edit profile and Change password) routing to Paywall. No Sparkles icon, no callout banner, no card variant — same SettingsRow primitive as Edit profile / Change password. Rationale: Ahmed wants paywall reachable from Profile without restoring the dedicated Bundle D Upgrade card (which read too pushy).
- **Preferences row dropped from FlatSettings** — Bundle D had a `Preferences` SettingsRow surfacing a preference modal. Day-2 ruling (c): drop it entirely. EditProfile is the single gateway to all preference editing; the Preferences row was a duplicate entry point. Frontend ships removal + Jest assertion edit in the SAME commit. Verify on device: Edit profile row routes correctly + no `Preferences` row anywhere in ACCOUNT group.

## How to use

1. Install latest EAS preview build (`eas build:list --branch preview --limit 1` → grab artifact URL → install on iPhone). Cold-start app.
2. For each section: open `docs/claude-design-handoff/ui_kits/mobile/<File>.jsx` AND `docs/claude-design-handoff/screenshots/<name>.png` side-by-side.
3. Walk each `[ ]` checkpoint. Mark **PASS** (visual match) or **RED** (specific delta).
4. For RED items: take a device screenshot, capture the matching JSX line number, post to dispatcher thread.

**JSX-wins doctrine** — if the device matches the JSX but disagrees with this rubric's wording, JSX wins. See § 9 "Known JSX-vs-rubric clarifications" before flagging RED.

---

## 1. HomeScreen

Reference: `HomeScreen.jsx` + `screenshots/home.png`
Current code: `SmartCompareApp/src/screens/HomeScreen.tsx`

- [ ] **Header (jsx:674-683)** — QarenLogo 24px + "Qaren" wordmark left; HeaderCounter pill right.
- [ ] **HeaderCounter (jsx:324-349)** — single pill renders `2/3 free · +1`. Background = `accentLight` when `free === 1`, plain `bg.secondary` otherwise. Border emerald when `free === 1`. Tap routes to Paywall.
- [ ] **Headline (jsx:685-691)** — "Compare anything." 16px 600 weight, paddingInline 20.
- [ ] **CategoryStrip (jsx:391-432)** — 5 horizontally-scrollable pills (Electronics / Grocery / Supplements / Makeup / Skincare). Active pill = emerald bg + white text + Lucide stroke icon white. Inactive = `bg.secondary` + dark text + dark stroke icon.
- [ ] **CompareCard (jsx:163-220)** — `bg.secondary` card with `border.light` 1px border, radius `R.card`. ModeSegment at top (Scan / Link / Type) with active pill = `cta.primary` (black) bg + white text + 180ms cubic-bezier transition. Compare CTA at bottom: black, height 48, emerald glow shadow `0 0 12px rgba(16,185,129,0.45)` when both inputs valid.
- [ ] **ScanBody affordance (Bundle E day-2 redesign jsx:222-265)** — when ModeSegment = Scan: ① and ② numerals + two dashed-border preview AREAS (NOT input-row look) + center hairline + emerald vs pill + footer hint. **Day-2 fixes verify:** camera icon size 28px (NOT 18px), `flexDirection: 'column'` (icon STACKED above text, not inline), minHeight 72-80px on dashed area, text split into TWO Text nodes — "Tap to snap" (14px 500 primary) + "Product A" (12px 400 caption). Must READ as a tappable card target, not a text-input row. If it still reads as input, RED.
- [ ] **SmartPickCard (jsx:438-501)** — eyebrow "Smart pick of the day" uppercase 11px letter-spacing 1.1px. Card has `bg.secondary` + radius 20. Inside: category pill + "Updated today" emerald-dark text. Two PickTile (jsx:503-531) products side-by-side. Center absolute-positioned emerald vs pill (jsx:470-479) with 2px white border. **Winner tile** has emerald 2px outline + emerald check overlay top-right (jsx:516-523, 18px circle, 2px white border). "See full verdict" button = plain bg + black 1px border.
- [ ] **QuickCategories (jsx:534-570)** — eyebrow "Jump back in"; 2×2 grid; each tile has a 28px circle (radius 14) on the left with `accentDark` icon glyph, then label.
- [ ] **SavingsBanner (jsx:573-605)** — dark-inverse `bg.inverse` (`#0A0A0B`) + white text. **Top-right concentric arc decoration** at `insetBlockStart: -40` / `insetInlineEnd: -40`, 110×110 circle w/ `rgba(16,185,129,0.4)` 1.5px border. Accent dot (jsx:588-591) 7×7 emerald at top-right. Eyebrow "This month" / `~240 BHD shopped smarter` 22px 700 / "Across 8 decisions sorted with Qaren." subtitle.
- [ ] **TrendingNearYou (jsx:608-651)** — eyebrow "Trending in Capital". Each row: category pill (left), product line `{a} vs {b}` (center, **inline emerald `vs` text NOT center pill** — see § 9 clarification #1), tail count `142 ↗` (right, tabular-nums).
- [ ] **TabBar (jsx:352-388)** — bottom Qaren / History / Profile tabs. Active tab has emerald icon + emerald label, weight 600.

---

## 2. ResultsScreen

Reference: `ResultsScreen.jsx` + `screenshots/results.png`
Current code: `SmartCompareApp/src/screens/ResultsScreen.tsx`

- [ ] **TopMatchBadge eyebrow (jsx:24-37)** — small pill, `accentLight` bg + `accentDark` text + emerald star + "Top match" uppercase 11px letter-spacing 1.1px.
- [ ] **Hero ProductCard pair (jsx:39-66)** — two cards side-by-side. **Winner**: `accentLight` bg (`#ECFDF5`) + 2px emerald border (`#10B981`) **FROM FIRST RENDER, no 800ms theatrical-delay gate** (D3 fix `b10e945` — variant gate decoupled from `winnerRevealed`). Loser: `bg.secondary` bg + 1px `border.light`. Each card has square product placeholder (radius 14, tone color) + name (15px 600) + sub (12px 400 secondary) + price (18px 700 tabular-nums, marginTop auto). **The theatrical reveal MOMENT is the scale-spring animation + Best Pick badge slide-in** — those still gate on `winnerRevealed` 800ms. Visual hierarchy and theatrical moment are intentionally decoupled.
- [ ] **RevealBurst on winner-card mount (Bundle E NEW)** — particle confetti emits from center on first mount only (keyed on `comparison_id`); 6-8 emerald particles, parabolic fall, fade-out over 1.2s total. Badge scale-bounce (0 → 1.1 → 1.0 with `withSpring({ damping: 8, stiffness: 100 })`).
- [ ] **DimensionBar (jsx:68-82)** — label + leftLabel/rightLabel right-aligned. Bar = `border.light` track 8px tall, left fill = `text.secondary`, then 2px `bg.primary` gap, then `accent` right fill.
- [ ] **ConfidencePill (jsx:84-101)** — small pill, `bg.secondary` + `border.light` border, 8×8 dot (emerald=high, warning=medium, border.medium=low) + label text.
- [ ] **DetailsAccordion (jsx:105-200)** — eyebrow "Dig deeper". 3 sections: Reviews / Pros & Cons / Specs. Each header has 32×32 icon-circle (radius 16) + label (14px 600) + sub (12px 400 secondary) + chevron-down on right that rotates 180° over 220ms ease on expand. **Only one open at a time** (jsx:107 `setOpen((curr) => (curr === k ? null : k))`).
- [ ] **Feedback prompt** — 3-pill row "Was this helpful?" (👍 / 👎 / Skip) below DetailsAccordion. (Not in JSX — feature lands in `src/components/FeedbackCard.tsx`.)

---

## 3. HistoryScreen

Reference: `HistoryScreen.jsx` + `screenshots/history.png`
Current code: `SmartCompareApp/src/screens/HistoryScreen.tsx`

- [ ] **HeroStats marquee (jsx:60-109)** — eyebrow "✦ Your recent verdicts" emerald-dark 600 uppercase 1.1px letter-spacing. Display "27 decisions this month" 24px 700. Sub "~240 BHD shopped smarter" 13px 400 secondary. Marquee = horizontally-scrollable row of MarqueeCard (jsx:111-152), each 184px wide.
- [ ] **MarqueeCard (jsx:111-152)** — category pill (top-left) + ago text (top-right). Inside: two MqProduct (jsx:153-180) tiles side-by-side + **center absolute-positioned emerald vs pill** (jsx:132-141, accentLight bg + accentDark text + 2px `bg.secondary` border). Winner MqProduct has 2px emerald border + emerald check overlay top-right.
- [ ] **SearchField (jsx:183-200)** — decorative pill, 42px tall, `bg.secondary` bg + `border.light` border, radius 999, search icon + "Search comparisons…" placeholder.
- [ ] **HistoryRowV2 (jsx:251-305)** — `bg.primary` card, radius 18, 1px `border.light`. Top row: category pill (left) + ago (right). Middle: two ProductBlock (jsx:204-248) side-by-side with **center absolute-positioned emerald vs pill** (jsx:280-293, 26px tall, paddingInline 12, 2px `bg.primary` border, `0 1px 3px rgba(0,0,0,0.08)` shadow).
- [ ] **ProductBlock winner** — `accentLight` bg + 2px emerald border + **"Top match" eyebrow** (jsx:214-223) emerald-dark 9px uppercase letter-spacing 1px + emerald star icon.
- [ ] **Verdict line** (jsx:297-302) — 12px 500 below the products: "Picked Galaxy — camera + battery edged out Apple here." (text-wrap pretty).
- [ ] **DateGroupV2 (jsx:307-319)** — eyebrow heading per group ("Today" / "Yesterday" / "This Week" / "Older") above each cluster of HistoryRowV2.
- [ ] **Row tap** — tapping HistoryRowV2 routes to `ResultsScreen` with matching `comparison_id`. B5 unwrap fix (commit `4aa9cff`) verified — Results renders the full comparison, no infinite spinner.

---

## 4. ProfileScreen

Reference: `ProfileScreen.jsx` + `screenshots/profile.png`
Current code: `SmartCompareApp/src/screens/ProfileScreen.tsx`

**Element order MUST match JSX top-down (jsx:308-318):** ProfileHeaderRow → RecentDecisions → PrioritiesInline → MonthStrip → FlatSettings. NO "Profile" screen title above header. NO standalone Account-card with avatar + email between header and RecentDecisions. NO B6 Bundle D Upgrade card with Sparkles icon anywhere.

- [ ] **ProfileHeaderRow (jsx:34-50)** AT TOP — QarenLogo 28px + name (display_name fallback) 18px 700 + region subtitle 12px 400 secondary + Settings icon button (36×36 circle, `bg.secondary`, Lucide Settings 18px, onPress → EditProfile). Header row paddingInline 20, paddingTop 8, paddingBottom 18, gap 12. **Subtitle string:** `${cohortDisplay.governorate} · GCC` when `cohortDisplay.governorate` is populated (e.g. `Capital · GCC`), plain `'GCC'` fallback otherwise. Never render `· GCC` with a missing governorate prefix (must be either both halves or just `GCC`).
- [ ] **RecentDecisions (jsx:122-161)** IMMEDIATELY BELOW header — eyebrow "Recent decisions" uppercase 11px 600 letterSpacing 1.1px + "See all" link (`accentDark`) at right. Horizontally-scrollable row of MiniVsCard (jsx:58-91, 168px wide). Section marginBottom 24.
- [ ] **MiniVsCard** — two MiniProduct (jsx:93-120) side-by-side + **center absolute-positioned emerald vs pill** (jsx:71-83, 18px tall, paddingInline 6, 2px `bg.secondary` border). Winner MiniProduct has 2px emerald border + emerald check overlay top-right. Sub line "{a/b winner} · 2 hrs ago".
- [ ] **PrioritiesInline (jsx:163-199)** — `bg.secondary` card, radius 20. Title "What shapes your matches" 16px 600. 3 bars: label (76px wide), bar (flex 1, height 6, accent fill on `border.light` track), percentage (32px right-aligned tabular-nums). **Backend serves sum=100 normalized integers (Path A R2)** — bars render proportional, sum to 100%. JSX 235% sum was the bug Bundle E fixes. CTA "Tune my priorities" black, 44px tall, radius 22.
- [ ] **MonthStrip (jsx:202-221)** — 3 Stat tiles in a row. **Middle tile has `accentDark` color on the number** (subtle flag, jsx:217). "27 · Decisions this month" / "240 · BHD shopped smarter" / "+5 · Bonus credits".
- [ ] **FlatSettings (jsx:251-275)** — **ONE rounded `<View>` containing all eyebrows + rows** (NOT 4 separate Bundle D `styles.card` blocks with `styles.sectionLabel` floating above). Borders only between rows (`borderBlockEnd` per SettingsRow). Section marginInline 20, marginBottom 20, radius 18, `bg.secondary`, 1px `border.light`, `overflow: hidden`. Groups in order:
  - **ACCOUNT** eyebrow → Edit profile → **Upgrade (day-2 add, NOT in JSX — discreet row, plain label + ChevronRight, NO Sparkles, NO callout)** → Change password → Language (right slot: EN/عر toggle)
  - **PRIVACY & NOTIFICATIONS** eyebrow → AI sharing ToggleRow → Notifications master ToggleRow + 3 sub-toggles (when on)
  - **HELP** eyebrow → Privacy Policy → Terms of Service → Contact us
  - **DANGER ZONE** eyebrow → Log out (destructive=true, red label, `last=true` — NO bottom border)
- [ ] **SettingsEyebrow recipe (jsx:239-250)** — 10px font, weight 600, lineHeight 1.4 (~14), letterSpacing 1.1px, uppercase, placeholder color, `bg.primary` background, hairline `border.light` borders TOP AND BOTTOM, paddingBlock 10 paddingInline 16. Verify ALL 4 eyebrows render with this recipe — NOT as plain `styles.sectionLabel` text floating above a card.
- [ ] **DELETIONS verified** (Bundle D pieces gone): no "Profile" screen title above header, no `brandTitleRow`, no `StyleProfileCard` import/render, no `ReferralStatusCard` import/render, no standalone Account card with avatar+displayName+email, no B6 Bundle D Upgrade card with Sparkles icon (Sparkles import removed if no other use), no `styles.sectionLabel` for 4 floating eyebrows, **NO `Preferences` SettingsRow** (Bundle A § 3.2 explicit drop — EditProfile route is the gateway to all preference editing; Preferences row was a Bundle D duplicate entry point that's now dead code). Frontend MUST also update any Jest assertion that previously asserted a `'Preferences'` row exists, in the SAME commit as the row removal — otherwise tests will RED on the rewrite.

---

## 5. PaywallScreen

Reference: `PaywallScreen.jsx` + `screenshots/paywall.png`
Current code: `SmartCompareApp/src/screens/PaywallScreen.tsx`

- [ ] **Top close X** (jsx:185-193) — 36×36 circle button top-left, `bg.secondary` bg.
- [ ] **HeroVisual (jsx:27-70)** — 3 mini-vs pairs in a row. **Middle pair popped up 6px** (`translateY(-6px)`) with `0 4px 12px rgba(0,0,0,0.08)` shadow. Each pair: two 38×38 product squares + center absolute-positioned emerald mini vs pill (jsx:51-60, 16px tall, paddingInline 5, 1.5px `bg.secondary` border).
- [ ] **Headline + sub** (jsx:198-210) — "Keep deciding with confidence." 26px 700 with "confidence" in `accent`. Sub "Unlimited comparisons, deeper reviews, full price history." 14px 400 secondary, center-aligned, max-width 320.
- [ ] **SocialProof (jsx:72-105)** — 5 avatar dots (24×24, overlapping with `-8` margin-start), avatar colors `#FCD9D2 / #E6EEF9 / #FFF1DA / #FBE6E6 / #1B1C1F` w/ initials K/M/A/S/+. Then "Trusted by **5,000+** GCC shoppers" 12px 500. Then emerald rating pill `accentLight` bg + `accentDark` text + emerald star + "4.8" 11px 700.
- [ ] **PlanCardLarge Yearly (jsx:107-154)** — 92px tall, radius 18. **Selected**: 2px `cta.primary` (black) border. Eyebrow ribbon at top (`insetBlockStart: -10`, paddingInline 10, accent bg + white text 10px 700 1px letter-spacing) reads "3 days free · Best value". Radio left (22×22, 6px border when selected). Name "Yearly" + sub "10.8 BHD billed yearly · Save ~70%" + price "0.9 BHD/mo" right-aligned 18px 700.
- [ ] **PlanCardLarge Monthly (jsx:223-229)** — 1px `border.light` (not selected), no eyebrow. Sub "Billed monthly · Cancel anytime" + price "2.9 BHD".
- [ ] **Features section (jsx:232-240)** — `bg.secondary` rounded card, 4 FeatureLine rows. Each: 18×18 emerald-accentLight circle + `accentDark` check stroke 3.5 + label text 13px 500. Lines: "70 comparisons per month" / "Full price history across 25+ GCC retailers" / "Priority processing — results in under 8 seconds" / "Ad-free, always".
- [ ] **Trial timeline (jsx:243-252)** — dashed 1px `border.light` border. Eyebrow "How the trial works" uppercase 0.8px letter-spacing. 3 rows: "**Today** · Unlock everything immediately." (emerald-dark today) / "**In 2 days** · Gentle reminder before billing." / "**In 3 days** · Billing starts — cancel anytime."
- [ ] **Sticky CTA (jsx:255-282)** — top 1px `border.light` divider. Black button 56px tall, radius 999, "Start My 3-Day Free Trial" 17px 700 + `0 4px 12px rgba(0,0,0,0.12)` shadow. Below: emerald check `accentDark` stroke 2.4 + "No payment due now · Cancel anytime" 12px 500 center-aligned. Bottom: Terms · Privacy · Restore links 11px 500 placeholder color.

---

## 6. ScanCameraScreen

Reference: `ScanCameraScreen.jsx` + `screenshots/scan.png`
Current code: `SmartCompareApp/src/screens/ScanCameraScreen.tsx`

- [ ] **Full-bleed black bg** (jsx:109-117) — `#0A0A0B` background + radial gradient camera-feed sim `radial-gradient(60% 50% at 50% 45%, #2A2D33 0%, #14161A 70%, #0A0B0D 100%)`.
- [ ] **Scanline (jsx:118-122)** — thin emerald horizontal line at vertical 50%, `linear-gradient(90deg, transparent, rgba(16,185,129,0.45), transparent)`.
- [ ] **Reticle (jsx:24-45)** — 260×260px centered. 4 corner brackets, each 28×28, 3px white border (`rgba(255,255,255,0.9)`), inner radius 12 (start-start / start-end / end-start / end-end).
- [ ] **Top bar (jsx:127-137)** — Close X CircleBtn (left, 44px circle, glass-blur `rgba(255,255,255,0.15)` + `backdrop-filter: blur(12px)` + 1px `rgba(255,255,255,0.2)` border + X stroke 2). "1 of 2" CamPill (center, 36px tall, paddingInline 14, same glass-blur). Help CircleBtn (right, same glass).
- [ ] **Hint text (jsx:139-149)** — absolutely positioned at top 24%, center text: "Center the product" 16px 600 white / "Fit the whole product in the brackets" 13px 400 `rgba(255,255,255,0.65)`.
- [ ] **SlotThumb pair (jsx:153-157)** — sits at bottom above capture row (NOT directly below reticle — see § 9 clarification #4). Two SlotThumbs centered, gap 12. Filled (jsx:74-100): `tone` bg + 1.5px emerald border + product placeholder + emerald check overlay top-right (16×16, 2px `#0A0A0B` border). Empty: `rgba(255,255,255,0.1)` bg + 1.5px `rgba(255,255,255,0.3)` border + plus icon stroke 2.
- [ ] **Capture row (jsx:160-173)** — Gallery CircleBtn left (48px, glass-blur). 76×76 white shutter center (radius 38, 4px `rgba(255,255,255,0.4)` outer border, **inner 2px `#0A0A0B` inset shadow**). Flash CircleBtn right (48px, glass-blur).
- [ ] **Sticky disabled CTA (jsx:176-188)** — bottom button "Snap one more to compare", glass-blur bg, 52px tall, radius 999, `cursor: not-allowed`, opacity 0.6, until both slots filled.

---

## 7. SignIn (LoginScreen)

Reference: `AuthScreens.jsx` lines 86-150 + `screenshots/sign-in.png`
Current code: `SmartCompareApp/src/screens/LoginScreen.tsx`

- [ ] **Header back button (jsx:97-105)** — 36×36 transparent button top-left with chevron-left stroke 2.5.
- [ ] **Headline + sub (jsx:108-113)** — "Welcome back." 32px 700 letter-spacing -0.4px. "Your advisor and credits are waiting." 14px 400 secondary.
- [ ] **SocialRow (jsx:51-73)** — 3 buttons (Apple / Google / Email) in a row, each flex 1, 48px tall, radius 12, `bg.primary` bg + 1px `border.medium`, label 13px 600. Apple = filled Apple-logo path, Google = colored 4-section circle, Email = stroke envelope.
- [ ] **OrDivider (jsx:75-83)** — 1px `border.light` lines on both sides, "or" 11px uppercase placeholder text in middle.
- [ ] **AuthField pair (jsx:19-49)** — Email + Password. Each: label 12px 500 secondary top, then 48px input box with `bg.primary` + 1px `border.light` (or 2px `text.primary` when focused), input 16px 400.
- [ ] **Forgot password** (jsx:121-126) — right-aligned link (`alignSelf: 'flex-end'`), `accentDark` color, 12px 500.
- [ ] **Sticky black CTA (jsx:130-140)** — top 1px `border.light` divider. Black button "Sign in" 52px tall, radius 999, 16px 600.
- [ ] **B4 Google sign-in works (Bundle E NEW)** — taps "Continue with Google" → EAS preview routes user into Home tab without freeze. If `[GOOGLE-DIAG]` shows token-segs=3 + Railway shows matching `SOCIAL_LOGIN_TRACE provider=google token_segs=3` + Supabase returns valid session: PASS.

---

## 8. SaveAdvisor (Step16Account)

Reference: `AuthScreens.jsx` lines 152-226 + `screenshots/save-advisor.png`
Current code: `SmartCompareApp/src/screens/onboarding/Step16Account.tsx`

- [ ] **Progress bar (jsx:165-169)** — top progress at 94%, accent fill on `border.light` track. **NO back arrow** (forced step).
- [ ] **Hero icon (jsx:173-183)** — centered 72×72 `accentLight` circle with bookmark/save glyph (jsx:179-181 `path d="M19 21V5..."`) stroke 3 in `accentDark`. **NOT a check** — see § 9 clarification #3.
- [ ] **Headline + sub (jsx:185-193)** — "Save your advisor." 28px 700 center, letter-spacing -0.32px. Sub "So your match travels with you. Sync your profile across devices and never lose your decisions." 14px 400 center secondary.
- [ ] **SocialRow + OrDivider + AuthField** — same primitives as SignIn.
- [ ] **Terms/Privacy fine print** (jsx:199-205) — "By continuing, you agree to our Terms & Privacy Policy." 11px 400 placeholder center. Terms / Privacy underlined in `text.secondary`.
- [ ] **Sticky black CTA** (jsx:212-218) — "Save my advisor" 52px tall, radius 999, 16px 600.
- [ ] **NO skip link** (jsx:219 comment confirms) — verify there's no "Skip" / "Not now" / "Maybe later" button anywhere on this screen. **This is a forced step.**

---

## 9. Known JSX-vs-rubric clarifications (do NOT mark RED)

These 5 items are visual deltas where the JSX wins per design doc § 5 ("the JSX *is* the spec"). Confirm the device matches the JSX, NOT some prior reading of the rubric.

1. **TrendingNearYou** — inline emerald "vs" inside `{a} vs {b}` text string is correct (HomeScreen.jsx:639). NOT a center-positioned pill. Center-pill pattern is for product-BLOCK layouts only (HistoryRowV2, SmartPickCard, Paywall HeroVisual, Profile MiniVsCard, History MarqueeCard).
2. **PrioritiesInline (Profile)** — bars must sum to 100% (backend Path A R2 normalize). JSX hardcoded weights (0.95 / 0.78 / 0.62 = 235%) was the bug Bundle E fixes. Bars will look thinner than JSX; this is correct.
3. **SaveAdvisor hero glyph** — bookmark/save icon (AuthScreens.jsx:179-181 `M19 21V5...`), NOT a check.
4. **ScanCameraScreen SlotThumb position** — slots sit at screen bottom above capture row (JSX flex spacer at line 151), NOT directly below the reticle.
5. **LoadingScreen onboarding-mode stages** — 4 stages (Calibrating to your region / Mapping your priorities / Matching your peer cohort / Crafting your shopping advisor). Comparison-mode has 5 stages. JSX `ONBOARDING_STAGES` at line 47-52 is the spec.

---

## 10. Sign-off

After walkthrough complete:

- **Total checkpoints:** ~85 across 8 surfaces
- **PASS / RED counts:** ___ / ___
- **RED items list:** _(linked to device screenshots + JSX line refs)_
- **Defer to S3 sweep:** _(items qa lane decides are S3-recoverable instead of S1-blocking)_
- **Block S2 start?** Yes / No

QA lane records sign-off in dispatcher thread + updates Task #15 status.

---

## References

- Design doc: `docs/plans/2026-05-26-bundle-e-visual-fidelity-design.md` (§ 6 acceptance gates is authoritative)
- Executable plan: `docs/plans/bundle-e-visual-fidelity.md` (§ qa lane S1 gate)
- JSX references: `docs/claude-design-handoff/ui_kits/mobile/*.jsx`
- Screenshots: `docs/claude-design-handoff/screenshots/*.png`
- Bundle D lesson: `memory/feedback_agent_signoff_vs_device_walkthrough.md` (why this rubric exists)
- Rollback path: `docs/runbooks/bundle-e-rollback.md`
