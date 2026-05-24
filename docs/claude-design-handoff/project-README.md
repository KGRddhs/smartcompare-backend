# Qaren Design System

> The visual + content system for **Qaren** — a mobile-first product comparison app for GCC shoppers. Compare two products via scan, link, or text; the app returns a personalized verdict based on your priorities and the answers of hundreds of cohort peers.

This is the **design system** repo. Use it to build well-branded screens, prototypes, mocks, and slides that look like real Qaren. Everything here mirrors the production app's theme tokens (`SmartCompareApp/src/theme/`) 1:1.

---

## Index

| File / folder | What's inside |
|---|---|
| `colors_and_type.css` | CSS custom properties for colors, spacing, radii, motion, and a full semantic type scale. Copy into any HTML artifact. |
| `fonts/` | **Geist** (EN — Regular / SemiBold / Bold) as local TTFs + OFL license. Cairo (AR) is loaded from Google Fonts at runtime. |
| `assets/` | Logo wordmark, app icon, screenshot references for the home / profile / edit-profile / onboarding screens. |
| `preview/` | Design System tab cards — one specimen per concept (colors, type, components, etc.). |
| `ui_kits/mobile/` | Pixel-perfect React recreations of the core mobile screens — Home, Results, Profile, Onboarding, Edit Profile. |
| `SKILL.md` | Agent skill metadata so this can be loaded as a Claude Skill. |

**Source code references** (read-only, attached to this workspace):
- `AI/smartcompare/SmartCompareApp/` — Expo / React Native app (this is the source of truth for theme tokens, screens, components, copy)
- `AI/smartcompare/backend/` — FastAPI backend (cohort, scoring, identification)
- GitHub: <https://github.com/KGRddhs/smartcompare-backend> — same codebase, public mirror. Explore for backend / API endpoints if needed.

---

## The product in one paragraph

You're trying to decide between two products. You open Qaren, pick a category (electronics, makeup, grocery, supplements…), and you give it the two products three ways: **scan** with the camera, **paste two links**, or just **type** the names. Qaren reads specs, prices, and reviews from 25+ GCC retailers; weights them against the **priorities** and **budget tier** you set during onboarding; and shows a side-by-side verdict — "Top match" plus a runner-up. The personalization is grounded in a cohort of ~400 real GCC shoppers, not a global average.

**Free tier:** ~3 comparisons/day. Friend invites unlock bonus comparisons. Premium (coming soon) goes to 70/month.

---

## Visual DNA — at a glance

> **Look:** iOS-native, not Dribbble. Plain navigation. Normal empty states. One clear primary action per screen. **One drop of emerald.**

| Property | Value |
|---|---|
| Background | `#FFFFFF` solid white. No gradient backgrounds anywhere. |
| Body type | **Geist** (replaced Inter in Phase 1). AR uses **Cairo**. |
| Text | `#0A0A0B` near-black for primary; `#6B7280` slate for secondary. |
| Primary CTA | **Black** (`#0A0A0B`) pill-rounded button — _not_ emerald. |
| Accent | **Emerald** (`#10B981`) — earns its place. Used only for: winner card border, success tick, toggle-on, "vs" pill text, active category chip, last-free counter pill. |
| Radii | 12 (button) · 16 (card) · 24 (hero card) · 999 (chip) |
| Shadow system | Exactly one: `0 1px 3px rgba(0,0,0,.08)` on cards. No stacking. |
| Icon set | Custom mono SVG family for brand/mode icons. **Lucide** (filled-or-stroke) for everything else. 16–24 px, mono color matching adjacent text. |
| Hover/press | iOS-native `activeOpacity: 0.7`. No "scale on press" tricks. |
| Layout | Single-column. Native tab bar (Qaren · History · Profile). Bottom-sheet for ephemeral flows (Share, Demographics). |

See **VISUAL FOUNDATIONS** below for the full breakdown.

---

## CONTENT FUNDAMENTALS — how Qaren talks

The copy is governed by a strict policy stored at `AI/smartcompare/SmartCompareApp/src/i18n/.copy-policy.json` and enforced by a CI test. Two big constraints drive every line of copy:

### Rule 1 — No absolute superlatives, no first-person endorsements

Qaren is a comparison tool, not a personal shopper. It cannot say _"this is the best"_, _"we recommend"_, _"winner"_, or _"choose this"_ — those phrases have legal and trust implications.

| Banned | Use instead |
|---|---|
| "Best Pick" / "Best Choice" / "Smart Pick" / "Winner" | **"Top match"** |
| "Best for…" | **"Ideal for…"** |
| "Why we picked this" | **"Why this fits you"** |
| "We recommend X" | **"Tuned to your priorities"** / **"Weighted for your preferences"** |
| "Excellent" | (silently dropped — let the data speak) |

### Rule 2 — Never frame the app as scary (Build Principle #4)

No "failed", no "couldn't", no red borders on errors, no shake animations. Errors are **gentle nudges to retry**. Always assume the user is fine and the system just needs another beat.

**Real examples from `en.json`:**

> ❌ "Failed to save. Please try again."
> ✅ **"Hold on — saving didn't go through. Tap to retry."**

> ❌ "Photo unreadable. Try again with better lighting."
> ✅ **"Snap that one more time — sharper focus this round."**

> ❌ "Couldn't find a match for your query."
> ✅ **"Sharper match coming up — try with brand or model."**

> ❌ "You have reached the maximum number of products."
> ✅ **"That's enough for now"** / "Compare up to 2 products at a time."

### Voice + tone

- **You** address the user, not "the user". Never "I" / "we" except for explicit promises ("We never share your name").
- **Sentence case** for everything. No title case on buttons. ("Compare", "Save", "See options" — not "See Options".)
- **Period at the end of titles** that read like sentences ("Compare anything.") — but never on labels or buttons.
- **"—" em-dashes** are the Qaren tic. They join two beats in a sentence ("Hold on — saving didn't go through. Tap to retry.") This is a deliberate voice anchor.
- **Numerals stay numeric** ("3 quick taps", "2 of 3 free", "1 anytime", "+5 comparisons if they sign up"). Never spelled out.
- **Quiet superlatives** are fine — "sharper", "smarter", "simpler". Banned only when comparative against another product.
- **GCC-grounded.** Refer to the region by name (Bahrain, GCC, governorates). Currency in BHD by default. Refer to peers as "GCC shoppers" not "users".

### Emoji policy

Mostly no. The codebase uses emoji in **exactly three places** and they are always carefully chosen:

- 🎁 — referral confirmations / lifetime-cap toast ("Thanks for gifting Qaren to 3 friends 🎁")
- ✦ — match-quality headline accent ("✦ Strong match")
- ✓ / ✗ — render as SVG icons (Lucide `Check` / `X`), never as emoji glyphs.

No emoji in primary copy, no emoji in CTAs, no emoji in section headers.

### Voice examples (full lines from the live app)

| Surface | EN Copy |
|---|---|
| Home hero | _Compare anything._ |
| Home empty (scan mode) | _Tap to scan products_  ·  _1 of 2_ |
| Onboarding s3 | _Stop guessing. Start knowing._  ·  _Side-by-side comparisons across 25+ retailers — picked for you._ |
| Onboarding s12 | _388 GCC shoppers helped train this._ |
| Demographics | _Tell us about you._  ·  _Want recommendations tuned to people like you? 3 quick taps._ |
| Privacy toggle | _Help improve AI quality._  ·  _Share your queries to make Qaren smarter. We never share your name, age, or identity._ |
| Notifs master | _Smart Decision Notifications_  ·  _We send up to 1 helpful notification per week — no price-drop spam._ |
| Paywall | _You've used your free comparisons. Unlock unlimited compares with a friend code or premium._ |
| Common error | _Hold on — give it another tap._ |

The vibe: **calm, direct, GCC-aware, never panicked, never breathless**. Read more in `AI/smartcompare/SmartCompareApp/src/i18n/en.json` (the source).

---

## VISUAL FOUNDATIONS

### Color

- **Surface** is always pure white (`#FFFFFF`). Cards step down to `#F8F8FA` — a 3% off-white, never a gradient. No tinted whites.
- **Text hierarchy is done in weight, not size, where possible.** `#0A0A0B` primary, `#6B7280` slate secondary, `#9CA3AF` placeholder. The slate is intentional — it's warmer than pure gray and reads as friendly on iOS.
- **Borders are one of two:** `#E5E7EB` light (cards, inputs at rest) and `#D1D5DB` medium (switch off-track, dividers on the off-white surface).
- **Emerald (`#10B981`) is reserved.** It must mean something. The places it appears in the live app, in full:
  1. The "vs" pill text color (`#059669` dark on `#ECFDF5` light fill).
  2. The Q-logo's accent dot (a single 2-pixel circle).
  3. Active category chip fill ("Electronics" selected).
  4. Toggle-row "on" track + thumb.
  5. Active tab icon + label (Qaren / History / Profile in the tab bar).
  6. Winner card border (`#10B981` 2px) + tint (`#ECFDF5` background).
  7. Last-free comparison counter pill (when down to 1 left).
  8. Compare CTA's glow shadow when both inputs validate ("ready" celebration).
  9. The dedicated "Reveal my verdict" CTA on the invitee landing — and **only there**.
- **Editorial dark (`#1A1A1A`)** is a Bundle C addition for Top-tier/Luxury budget picker cards. Never used as full fill — only as a 1px hairline border.
- **Destructive (`#EF4444`)** for delete-account label + invalid input border. Used sparingly.
- **No bluish-purple gradients. No emoji cards. No left-border accent stripes.** These are the AI-app tropes Qaren explicitly avoids.

### Type

- **EN: Geist** (SIL OFL, local TTF). Three weights ship: 400 / 600 / 700. Geist replaced Inter in the Phase 1 visual swap.
- **AR: Cairo** (Google Fonts, 400 / 600 / 700). Arabic line-height multiplies by **1.13×** because Cairo's letterforms run taller.
- **The eyebrow type style (`11px / 600 / +0.10em tracking / uppercase`) is AR-aware** — `text-transform: uppercase` is dropped on Arabic because it mangles "مقابل" ("versus").
- **The scale is short, on purpose.** Eight stops: `small (11)`, `eyebrow (11 upper)`, `caption (13)`, `body (16)`, `bodyEmphasis (16/600)`, `title (20/600)`, `display (28/700)`, `hero (36/700)`. There is no `subtitle`, no `body-lg`, no `body-sm`. If a screen seems to need one, push the design back to one of these eight.

### Spacing

- **8-pt grid** with two half-stops: 4, 8, 12, 16, 20, 24, 32, 48. `16` is the workhorse — most card padding, most gap-between-rows.
- **Horizontal page padding is `20px`** (the `spacing.lg` token). Tab bar content respects it. Headers respect it. Section dividers run edge-to-edge inside `20px` insets.
- **Min touch target is 44pt**, enforced via `minHeight: 44` on every chip, button, toggle, and icon button (WCAG 2.5.5).
- **No nested cards.** A card may contain rows, but never another card.

### Background, imagery, gradients

- Solid white for every base surface. **Zero use of gradients as page backgrounds.**
- The only background tint allowed is `#F8F8FA` (cards) or `#ECFDF5` (the winner card / "vs" pill / last-free pill).
- No full-bleed photography. No hand-drawn illustrations. No repeating patterns. No textures. No grain.
- Product photos in results are square 1:1, rendered with `borderRadius: 16` to match cards.
- The single "art" moment in the app is the **LoadingRings** illustration that plays during the 1.2s comparison min-display floor — a concentric set of emerald arcs sweeping in. Treat it as a brand animation, not an illustration system.

### Animation + motion

The motion language is defined in `theme/motion.ts`. Five primitives:

- **Screen transitions** — 320ms slide, `cubic-bezier(0.32, 0.72, 0, 1)`. Mirrors automatically in RTL.
- **Chip springs** — `damping: 14, stiffness: 200`. Used on mode-chip activation + the "ready" celebration on the two-input shell (circles scale `1.0 → 1.12 → 1.0`).
- **Progress springs** — `damping: 18, stiffness: 120`. Slower, used for progress bars and the winner-card reveal (`0.96 → 1.0`).
- **Tab icon springs** — `damping: 12, stiffness: 180`. Just enough to feel tactile.
- **Variable easing** for the theatrical loading bar — fast → slow → snap.

Rules:
- **No shake, no wobble, no jitter** — Build Principle #4 forbids "panic" animations.
- **No bounce on errors.** Errors are silent state changes.
- **Haptics only on positive events.** Light haptic on chip select + stage tick; medium on winner reveal. Never on errors.

### Hover + press states

- **Press: `activeOpacity: 0.7`** — the iOS-native default. Applied via `TouchableOpacity` on every button, chip, row.
- **No scale-on-press.** Native iOS doesn't do it, so Qaren doesn't either.
- **Hover doesn't really exist** on mobile, but the web previews here use `:hover { opacity: 0.85 }` as the rough equivalent.
- **Focused input** swaps the border from `1px #E5E7EB` to `2px #0A0A0B`. No glow, no color change, no shadow.
- **CTA "ready" state** (both two-input boxes validated) is the one exception — the black CTA gains an emerald shadow-glow (`0 0 12px rgba(16,185,129,.45)`).

### Borders, shadows, capsules

- **Borders are 1px**, two colors only (light `#E5E7EB`, medium `#D1D5DB`). The winner card is the only place a 2px border appears.
- **Exactly one shadow recipe exists:** `0 1px 3px rgba(0,0,0,0.08)`. Used on cards and only cards.
- **No inner shadows.** No double-layer shadows.
- **Capsules over protection-gradients.** When text needs to sit on imagery, Qaren uses a solid capsule pill (`bg-secondary`, hairline border), not a gradient overlay. There are no protection gradients in the app.
- **Transparency + blur:** used only on the loading overlay — `rgba(0,0,0,0.8)` solid-tint capsule that floats above content. No `backdrop-filter: blur()` anywhere in the live screens.

### Layout rules

- Single-column, edge-padded by `spacing.lg = 20px`.
- **Native iOS tab bar** at the bottom (Home / History / Profile). Tab labels are mandatory; icon-only is forbidden.
- **Sticky bottom CTA on action screens** (Edit Profile, Onboarding) — the primary button sits above the home indicator with a hairline divider, never floating.
- **Bottom sheets** for ephemeral flows (Share, Demographics, ConfidenceDetails) — full-width, rounded top corners `radius-hero (24px)`.
- **Section headers** are eyebrow-style (`11px / 600 / uppercase / +1.1px tracking`) and live in the page padding, not inside the cards they label.
- **Cards group rows.** Toggles, list items, and stat rows live inside cards. Standalone rows are reserved for the main interactive elements of a screen.

### Corner radii — the recipe

- `12px` buttons (primary, secondary, mode chip rest)
- `16px` cards, inputs, scan placeholder, paywall banner
- `24px` hero cards, bottom-sheet top corners
- `999px` (full pill) — every chip, the "vs" pill, counter pills
- **Never `4px` / `8px` radii.** Anything smaller than 12px feels "websitey".

---

## ICONOGRAPHY

Qaren ships a **mixed icon system**: custom mono SVGs for brand-critical glyphs, **Lucide** for everything else. There is no icon font and no PNG sprite.

### What's custom (in `AI/smartcompare/SmartCompareApp/src/icons/`)

- **`QaranIcon.tsx`** — the brand mark. A magnifier (Q-as-ring) with a small dot on the handle tip. Used in headers next to the wordmark. Built in `24x24`, stroke-based, mono-color so it inherits whatever the surface needs.
- **`QarenLogo.tsx`** (in `src/components/`) — a richer 32×32 version with the emerald accent dot at top-right of the ring. This is the "Bundle A signal-color one-drop" rule made literal. Used on Splash and Home headers.
- **`UtilityIcons.tsx`** — six filled-mono utility icons hand-drawn to a strict style contract: filled paths, no strokes, rounded geometry, `#0A0A0B` default. `BackIcon`, `CloseIcon`, `SearchIcon`, `BellIcon`, `SettingsIcon`, `PlusIcon`. `BackIcon` mirrors in RTL via the `flipForRTL` helper.
- **`ModeIcons.tsx`** — the three input-mode icons in the home rail: `ScanIcon` (viewfinder corners + center dot), `LinkIcon` (interlocking chain at 45°), `TypeIcon` (T on a baseline tick). Same filled-mono contract.

### What's Lucide

The other ~30 icons in the app pull from `lucide-react-native` with **per-icon imports** for tree-shaking. Examples seen in the code:

- Home / categories: `Smartphone`, `ShoppingCart`, `Pill`, `Brush`, `Sparkles`, `Scissors`, `Flower`, `ShoppingBag`, `Package`, `Camera`
- Results: `Trophy`, `Star`, `ExternalLink`, `Shield`, `AlertCircle`, `Award`, `Gift`, `Battery`, `Monitor`, `Zap`, `HardDrive`, `DollarSign`, `Info`, `ChevronUp`, `ChevronDown`
- Profile: `Globe`, `Sliders`, `Bell`, `FileText`, `ScrollText`, `MessageCircle`, `LogOut`, `Lock`, `Shield`
- Two-input shell: `Check`, `X`
- Tab bar: `Home`, `Clock`, `User`

**Style contract for Lucide:** `strokeWidth: 2` (default), size `14 / 16 / 20 / 24` matched to adjacent text size. Color always inherits from `text.primary`, `text.secondary`, or `accent` — never a one-off color.

### When to use what

- **Brand surface (logo, app icon, splash)** → custom `QarenLogo` / `QaranIcon`.
- **Mode rail at bottom of Home** → custom `ModeIcons` only.
- **Navigation chrome (back, close, settings, bell, plus)** → custom `UtilityIcons` (the filled mono set).
- **Everything inside cards + lists** → Lucide stroked icons.

### In the web previews (this repo)

Web previews load **Lucide via CDN** (`https://unpkg.com/lucide-static@latest/...`) to substitute for `lucide-react-native`. The custom brand glyphs are inlined as SVG inside the component JSX so they survive offline. **Substitution flag for the user**: a couple of the more exotic Lucide glyphs (`Brush` for makeup, `Sparkles` for skincare) may render slightly differently than the native React Native version at small sizes — visually equivalent but pixel-different. If pixel-perfect is needed, swap them for static SVG copies.

### Emoji / unicode as icons

Used in only three places: 🎁 (referral), ✦ (match-quality headline), and 🎉 / ✨ are deliberately **not** used anywhere. Unicode arrows (`↑`, `↓`) are used in the personalization chip ("Weighted ↑ Price ↓ Brand"). Otherwise icons are SVG.

---

## Building with this system

1. Drop `colors_and_type.css` into your `<head>`. Every variable starts with `--qaren-` so it won't collide.
2. Pull components from `ui_kits/mobile/` and drop them into a React + Babel HTML scaffold.
3. Use the iOS frame starter (`copy_starter_component` with `ios_frame.jsx`) to wrap mobile screens.
4. Lean on the type scale + spacing tokens. **Do not invent new values.** If a token doesn't exist for what you need, the design is probably wrong.
5. When in doubt about copy, read `AI/smartcompare/SmartCompareApp/src/i18n/en.json` and grep for similar surfaces.
6. To explore more of the source code or the API surface, read the backend at <https://github.com/KGRddhs/smartcompare-backend>.

---

## Cal AI inspiration — what to borrow, what to ignore

Cal AI shares a lot of Qaren's DNA: pure white surface, big bold sans-serif display, black-on-select pills, plain iOS tab bar, calm copy. The places it goes further — and that Qaren should consider — are below. None of these change the brand rules above; they refine specific surfaces.

**Borrow:**

- **Icon-in-circle prefix on option rows.** Cal AI's onboarding options sit on big light-gray pills with a 36px white circle on the leading edge that holds the relevant glyph. Qaren's onboarding (Priorities, Lifestyle, Brand) currently uses plain text rows — adopt this pattern to give each option visual identity without changing the layout. See `preview/option-rows.html`.
- **Optional warm wash on hero surfaces.** Cal AI uses a barely-there peach + lavender radial wash on the background of splash + onboarding screens (~5–10% opacity, top corners only). Qaren can do the same on Splash and the first onboarding step **only** — never on Home, Results, History, Profile. See `preview/warm-wash.html`.
- **Floating "+" FAB on Home.** Cal AI overlays a black circular FAB on top of the tab bar for "log a meal". Qaren could do the same for "start a new compare" once Home accumulates enough state to need a quicker entry — not on day one.
- **Streak / celebration modal pattern.** Cal AI's "🔥 1 Day streak" sheet is a great template for Qaren's referral confirmations and "you saved your call" moments. Solid playful illustration, big number, a weekday strip with checkmarks, one black CTA. **Do NOT copy the flame emoji or the streak gamification** — Qaren's product is about good decisions, not daily-habit nagging. Borrow the layout, not the metaphor.
- **Big display headlines with bold weights** (Geist already covers this — Cal AI just reminds us to commit to the size: 28–32px questions, not 20px).

**Ignore — these are anti-patterns for Qaren:**

- **Streak gamification + reminder spam.** Qaren explicitly promises "up to 1 helpful notification per week — no price-drop spam". Streaks would break that promise.
- **Categorical color charts** (Cal AI's red protein / orange carbs / blue fat). Qaren's data is comparative ("A vs B"), not categorical, so categorical color coding doesn't apply. If a future Qaren surface ever needs to color-tag categories (electronics, makeup, etc.), revisit and pick a 4–5 color set that respects emerald-as-signal.
- **Aggressive paywall copy** ("80% OFF FOREVER", sparkle glyphs, scratched-out prices). Qaren's paywall is calm and informational — "Unlock unlimited compares with a friend code or premium."
- **Drawn brand illustrations** (Cal AI's hand-holding-heart, clapping hands). Qaren is a comparison tool, not a wellness app — illustrations would read as decorative. Stick to functional UI.

The icon family in Cal AI (filled-mono apple, viewfinder corners, plain stroke icons for tabs) is essentially the same recipe Qaren already uses. Keep going on the custom mono SVGs in `src/icons/` — Cal AI is proof that this approach scales.

---

## Known gaps + caveats

- **No real product imagery** ships with the design system. Use solid placeholder rectangles (rounded 16px, `#F8F8FA` fill, with a generic Lucide icon centered) until product images are wired in.
- **Cairo (AR) is web-fonts-only** in previews — the native app loads it via `@expo-google-fonts/cairo`. If the previewer is offline, Arabic text falls back to system Arabic.
- **The `editorial-dark` color** is implemented in tokens but barely used in the surface designs included here — it's reserved for the upcoming Top-tier budget picker in Bundle C, which doesn't have a high-fidelity screen in this kit.
- **No marketing website** exists yet. The only UI kit in this repo is the mobile app. If a marketing site comes later, it inherits the same color + type + voice rules but layout would be re-derived.
