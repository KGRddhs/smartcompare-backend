# Qaren UX Redesign — Design Specification

**Date:** 2026-05-06
**Status:** Approved
**Brand:** Qaren (قارن)
**Tagline:** "Look closer. Decide smarter." / "انظر بدقة. قارن بذكاء."
**Logo:** Black rounded square + white Q-as-magnifying-glass

---

## Build Principles (Locked)

These principles override every individual decision below. When in doubt, fall back to these.

1. **Nothing generic.** No SaaS-emerald-gradient hero. No stock illustrations. No "people pointing at laptops." If a competitor app has it, we don't.
2. **Nothing AI-art.** No Midjourney exports as illustrations. No DALL-E hero images. No GPT-generated copy that sounds like every other app.
3. **Nothing vibecoded.** Every animation curve hand-tuned. Every icon proportioned on the same grid. Every copy line written, never templated. Reject "good enough."
4. **Nothing scary.** No copy that implies the app might not work. No "error", "failed", "couldn't", "try again later." Confident verbs only: *cross-checking, calibrating, locking in, pulling in, crafting*.
5. **No exit ramps during loading.** No Cancel button mid-compare. No "keep waiting?" modal. Silent retries; surface only when truly out of options — and even then, reframe as collaboration ("Sharper match when you add a brand").
6. **Cohort moat is the differentiator.** Surface "388 GCC shoppers helped train this" / "12 peers in {governorate}" wherever it earns its keep. The data IS our edge — show it.
7. **Bilingual EN + AR with full RTL.** Every animation mirrors. Every layout flips. Cairo line-height 1.7x.

---

## Section 1 — Visual System

### Color tokens (evolved from Session 36 redesign)

| Token | Value | Role |
|---|---|---|
| `bg.primary` | `#FFFFFF` | Main background (unchanged) |
| `bg.secondary` | `#F8F8FA` | Card / section background (unchanged) |
| `bg.inverse` | `#0A0A0B` | **NEW** — black surface for hero/onboarding moment screens, matches logo bg |
| `text.primary` | `#0A0A0B` | Slightly deeper than current `#1A1A1E`, matches logo |
| `text.onInverse` | `#FFFFFF` | **NEW** — text on black surfaces |
| `cta.primary` | `#0A0A0B` | **CHANGED** — black is now the primary CTA color (was emerald) |
| `cta.onPrimary` | `#FFFFFF` | White text on black CTAs |
| `accent` | `#10B981` | Emerald — kept, but reserved for *signature* moments only |
| `accent.dark` | `#059669` | **NEW** — pressed/active state |
| `accent.light` | `#ECFDF5` | Winner card background tint (unchanged) |
| `accent.glow` | `rgba(16,185,129,0.20)` | **NEW** — glow ring for winner reveal |
| `destructive` | `#EF4444` | Errors, delete confirmations |
| `warning` | `#F59E0B` | Tie / similar indicator |
| `border.light` | `#E5E7EB` | Card borders, dividers |
| `border.medium` | `#D1D5DB` | Input borders |

**Where each color earns its keep:**
- **Black** does the structural work — buttons, headers, nav chrome, type, the magnifier-Q mark in the app.
- **Emerald** is reserved strictly for: winner badge, success ticks, progress fill, active tab dot, cohort-match accents, glow ring on winner reveal, the **one-time** invitee "Reveal my verdict" CTA.
- **White + grays** = canvas.

This is the key shift from Session 36: emerald is no longer the primary CTA color; it is now a *signal* color.

### Typography — Geist (EN) + Cairo (AR)

Migrating from Inter to **Geist** for the EN voice. Cairo retained for AR.

| Token | Size | Weight | Tracking | Use |
|---|---|---|---|---|
| `hero` | 36pt | Bold | -0.02em | Onboarding question titles |
| `display` | 28pt | Bold | -0.01em | Screen titles |
| `title` | 20pt | SemiBold | 0 | Section headers |
| `body` | 16pt | Regular | 0 | Content |
| `bodyEmphasis` | 16pt | SemiBold | 0 | **NEW** — inline emphasis ("388 shoppers") |
| `caption` | 13pt | Regular | 0 | Metadata |
| `eyebrow` | 11pt | SemiBold | +0.10em | **NEW** — UPPERCASE labels ("STEP 4 OF 17") |
| `small` | 11pt | Regular | 0 | Fine print |

- Arabic line-height multiplier: 1.7x
- Only Regular + SemiBold + Bold weights loaded
- Geist via `expo-font`, ~150KB

### Spacing & radii

Unchanged from Session 36. Base unit 4px. Scale: 4, 8, 12, 16, 20, 24, 32, 48. Card radius 16px, button 12px, chip 999, input 12px. **NEW:** `radii.hero = 24` for hero/moment cards.

### Motion language

| Pattern | Spec | Used for |
|---|---|---|
| Screen transition | Slide horizontal, 320ms cubic-bezier(0.32, 0.72, 0, 1), RTL-mirrored | Onboarding step transitions |
| Chip select | Scale 0.95 → 1.04 → 1.0 spring + haptic light | All chip selections |
| Progress bar | Spring fill (damping 18, stiffness 120) — variable easing variant | Onboarding progress, freemium counter, Results stage bar |
| Counter tick | Number animates 0 → target over 800ms ease-out | "388 shoppers matched", BHD prices |
| Card slide-in | Stagger 80ms, slide 24px from below + fade | Results rendering |
| Winner pulse | Scale 1.0 → 1.02 → 1.0 + glow ring expand 0 → 24px alpha | Once when winner revealed |
| Cohort badge | Slide from right (LTR) / left (RTL) + fade, after winner pulse | Results screen |
| Camera detect | Viewfinder corners snap to detected product bbox, 200ms spring | Home camera card |
| Tab bar select | Selected icon scales 1.0 → 1.15 → 1.0 + emerald dot fades in | Bottom nav |

---

## Section 2 — 17-Screen Onboarding Flow

**Structure (Cal-AI psychology adapted to Qaren):** Welcome → Cohort data → Shopping prefs → Social proof → Theatrical reveal → Account.

| # | Screen | Purpose | Input |
|---|---|---|---|
| 1 | **Welcome** — Big black Q-logo, hero "Look closer. Decide smarter." / "انظر بدقة. قارن بذكاء." | Trust through brand confidence | Continue + "Already have an account? Sign in" |
| 2 | **Language** — "Choose your language / اختر لغتك" | Set RTL early so subsequent screens render correctly | English / العربية |
| 3 | **Value prop** — Phone mockup hero illustration (#1) showing two product cards with emerald winner badge. "Stop guessing. Start knowing." | Show value before asking anything | Continue |
| 4 | **Where you shop** — "Where are you shopping from?" 6 GCC flag cards. If Bahrain → conditional second question slides in: "Which area?" (Capital / Muharraq / Northern / Southern) | Cohort key #1 + GCC-native positioning | Single + conditional |
| 5 | **Trust bridge** — Pure typography + small filled lock icon (rotates 5° on mount, *Cal-AI weight: filled, geometric, chunky*). Hero copy: "Your data stays yours. We just compare." Three thin bullets: "Your data lives on your device", "We match anonymously — no name attached", "Skip anything — and edit later" | Pre-empt "why do you need this?" objection | Continue |
| 6 | **Age group** — "How old are you?" 5 cards: 18-24 / 25-34 / 35-44 / 45-54 / 55+ + "Prefer not to say" link | Cohort key #2 (exact format: `25-34`) | Single |
| 7 | **Gender** — "How do you identify?" 3 cards: Male / Female / Prefer not to say | Cohort key #3 | Single |
| 8 | **Priorities** — "What matters most when you buy?" up to 3 of 8 chips | Personalization signal — feeds scoring ±30% cap | Multi (1-3) |
| 9 | **Budget** — "Where do you usually shop?" 3 cards with BHD example ranges: Budget (<11) / Mid (11-57) / Premium (57-189) | Aligns with `_get_price_tier()` | Single |
| 10 | **Brand attitude** — "How do you choose between brands?" 3 cards: Brand-loyal / Function-first / Best of both | Final personalization key | Single |
| 11 | **Attribution** — "Where did you hear about us?" 6 stacked cards: Friend, Instagram, TikTok, App Store, Google, Other | Market-research signal currently uncaptured | Single |
| 12 | **Cohort social proof** — Hero illustration #2 (bar chart). "388 GCC shoppers helped train this." Three bullet stats animate one-by-one | Sunk-cost + trust + "I'm not alone" | Continue |
| 13 | **Anticipation** — "Time to build your shopping advisor" hero illustration #3 (concentric circles motif) | Build-up before the payoff | Build my advisor |
| 14 | **Theatrical loading** — Hero illustration #4 (Q-logo + 3 emerald glow rings expanding). Streaming text cycles word-by-word: "388 GCC shoppers helped train this" → "Calibrating to {governorate}… 47 matches" → "Tuning to your priorities: {top 2}" → "Crafting your shopping advisor". Progress bar fills 0→100% over **3.2 seconds minimum** even if API faster. Counter ticks "0 → 47 cohort peers." | Perceived effort = perceived value. The centerpiece "mind trick." | (auto-advances) |
| 15 | **Reveal** — "Your shopping advisor is ready" hero illustration #5 (radiating burst). 4 stat cards in 2x2 grid: Match quality, Top priority, Budget tier, Region peers count. Each card slide-staggers in. | The payoff the loading earned | Compare your first product (black CTA) |
| 16 | **Save your advisor** — Apple / Google / Email. **No skip link.** Forced sign-in. | Sunk cost makes drop-off lowest here. Account required for Loop 2 + cohort persistence + push notifications + Apple guideline 4.8 | Single (mandatory) |
| 17 | **Notifications** — "Be the first to know when prices drop" Compact mock notification preview. Allow / Not now | Asked AFTER value built, not at launch | Single |

**Skipped from current onboarding (intentional):**
- ❌ Lifestyle tags (low actionable signal vs. priorities)

**Intentionally absent (Cal AI has these, Qaren doesn't need):**
- ❌ Hard paywall close (freemium handles monetization)
- ❌ "Tried other apps?" (comparison space not crowded enough for switcher framing)
- ❌ Spin-the-wheel discount (gimmicky for B2C utility)
- ❌ "Rate us 4.8★" mid-flow (premature; do this after 3 successful comparisons)

**Architecture:**
- Single `OnboardingFlow` component owns step state; each step is a sub-component under `src/screens/onboarding/`
- 17 micro-segment progress bar at top
- Back arrow always available
- All chip selects use scale-bounce + haptic light pattern
- All slide transitions mirror RTL
- Backend endpoints already exist: `PUT /api/v1/auth/demographics` (screens 4, 6, 7), `PUT /api/v1/auth/preferences` (screens 8-10). Attribution endpoint needs to be added.

---

## Section 3 — Latency-Masking on Results

The Results screen waits 5-12 seconds for backend orchestration. SSE infrastructure already exists (`onStatus`, `onSpecs`, `onPrices`, `onReviews`, `onScores`, `onVerdict`). We dramatize the existing stages.

### The pattern

```
┌──────────────────────────────────┐
│  ‹                          ⓘ    │
│                                  │
│  iPhone 15 vs Galaxy S24         │ ← query echoed (instant trust)
│                                  │
│  ▓▓▓▓▓▓▓▓░░░░░░░░░  42%          │ ← variable-easing progress bar
│                                  │
│  ✓ Reading specs · 6 sources     │ ← completed (emerald check)
│  ⟳ Cross-checking 12 retailers   │
│     in 🇧🇭 Bahrain                 │ ← active (emerald spinner + region)
│  ○ Analyzing 200+ reviews         │ ← pending
│  ○ Calibrating to your priorities│
│  ○ Locking in your winner         │
│                                  │
│  ┌───────────┐  ┌───────────┐   │
│  │ iPhone 15 │  │ Galaxy S24│   │ ← ghost product cards
│  │ ░░░░░░░░  │  │ ░░░░░░░░  │   │   fill in progressively as
│  │ ░░░░      │  │ ░░░░      │   │   each SSE event arrives
│  └───────────┘  └───────────┘   │
└──────────────────────────────────┘
```

### Mind tricks layered in

| Trick | What it does |
|---|---|
| **Variable progress easing** | Bar moves fast 0→25% (0.6s), slow 25→60%, fast 60→90%, snap 90→100% (0.4s before reveal). Feels like real work even if backend is faster. |
| **Multi-stage checklist** | 5 explicit stages with ✓/⟳/○. Each ✓ fires haptic light. |
| **Streaming data preview** | Ghost cards become real product cards stage-by-stage: title fills first, then specs, then prices count up (BHD numbers tick), then star rating fades in. |
| **Cohort / region context copy** | Stage 2 copy injects user's `country` + `governorate`. Stage 4 copy injects priorities. |
| **Counter ticks on prices** | When prices arrive, BHD figures animate from 0 → real number over 800ms ease-out. Reads as "calculating" not "fetched." |
| **Min-display floor** | Even cached responses (~200ms) show loading for **1.2s minimum** so the brand moment lands. (Onboarding screen 14 was 3.2s; Results is shorter because it's repeat.) |
| **Live cohort tease** | If `scoring_method` ∈ {`personalized`, `behavioral`}, stage 4 copy: "47 shoppers in {governorate} also picked this." Subtle social proof during wait. |

### Stage-to-copy mapping (i18n keys)

| SSE event | EN | AR | Min duration |
|---|---|---|---|
| init | "Understanding your query" | "نفهم طلبك" | 0.3s |
| `specs` | "Reading specs from {n} sources" | "نقرأ المواصفات من {n} مصادر" | real time |
| `prices` | "Cross-checking {n} retailers in 🇧🇭 {country}" | "نتحقق من {n} متاجر في {country}" | real time |
| `reviews` | "Analyzing {n}+ reviews" | "نحلّل {n}+ مراجعة" | real time |
| `scores` | "Calibrating to your priorities · {top_2}" | "نضبط حسب أولوياتك · {…}" | **pad to 0.7s** |
| `verdict` | "Locking in your winner" | "نختار الأفضل لك" | real time + 0.3s |
| Stage 6 (8-15s overflow) | "Pulling in the latest from {n} retailers" | "نجلب آخر التحديثات من {n} متجراً" | — |
| Stage 7 (15-25s overflow) | "Calibrating the final ranking" | "نضبط الترتيب النهائي" | — |

### Failure handling — never scary

| Real condition | What user sees |
|---|---|
| Stalled 8-15s | Stage 6 quietly unfolds — feels like extra rigor |
| Stalled 15-25s | Stage 7 unfolds — same calm pacing |
| Stalled 25-45s | Tips carousel appears below stage list, rotating every 4s |
| Network drop mid-stream | **Silent auto-retry × 2.** UI keeps last completed stage. After 8s of failures → tiny pill "Reconnecting…" (no banner, no shake). Continues retrying. |
| 45s+ no response | Inline footer: "Try iPhone 15 vs Galaxy S24 — sharper with brand + model" |
| Backend 5xx | "Try with brand or model — sharper match every time" |
| Cache hit <200ms | 1.2s loading floor still shown |

### "Tips during deep waits" carousel

When loading exceeds 8s, a single line appears below the stage list, rotates every 4s:

| EN | AR |
|---|---|
| "73% of {country} shoppers your age prioritize {priority}." | "٧٣٪ من المتسوقين في {country} يعطون الأولوية لـ {priority}." |
| "Qaren cross-checks 25+ retailers — never just one." | "قارن يقارن أكثر من ٢٥ متجراً — وليس متجراً واحداً." |
| "We work for you — never paid by sellers." | "نعمل لصالحك — البائعون لا يدفعون لنا." |
| "47 cohort peers in {governorate} helped train this match." | "ساعد ٤٧ شخصاً مثلك في {governorate} على تدريب هذه المقارنة." |
| "Save any comparison to revisit later — even offline." | "احفظ أي مقارنة لمراجعتها لاحقاً — حتى دون إنترنت." |

### No exit ramps during loading

- No Cancel button. No "Keep waiting?" modal. Back arrow always available in header (natural escape) but no overt "give up" CTA.

### Reveal animation when `verdict` arrives

1. Last `○` flips to `✓` + haptic medium
2. Progress bar snaps to 100%, fades out
3. Stage list slides up off-screen (240ms)
4. Both product cards slide together to final positions (320ms stagger)
5. **Winner card pulses + emerald glow ring expands 0 → 24px**
6. Cohort badge slides in: "Like 12 shoppers in {governorate}"
7. Tradeoff pairs and "key differences" sections progressively reveal (80ms stagger)
8. Sticky "Save / Share" footer slides up

### Components

| Component | Status | Change |
|---|---|---|
| `SkeletonLoader` | exists | Extend with `variant="ghostCard"` |
| `ProgressBar` | exists | Add `variableEasing` prop |
| `StageChecklist` | **new** | 5-row list with ✓/⟳/○ states + i18n stage copy |
| `CounterTicker` | **new** | Animates 0 → target over N ms |
| `StreamingProductCard` | **new** | Wraps existing product card, supports per-field fill-in via SSE callbacks |
| `CohortBadge` | **new/extend** | Slide-from-side animation, RTL-aware |
| `LoadingTipsCarousel` | **new** | Rotating tips after 8s wait |

---

## Section 4 — Home + Results Redesign

### 4a. Home — camera-first card with 3-mode equal chips

```
┌────────────────────────────────────┐
│ Q  Hi, Ahmed             🔔  👤    │
│                                    │
│ Compare anything.                  │ ← compressed hero (16pt)
│                                    │
│ ┌──────────────────────────────┐   │
│ │ 🔍 What are you comparing?   │   │ ← search bar
│ └──────────────────────────────┘   │
│                                    │
│ ╔══════════════════════════════╗   │
│ ║                              ║   │
│ ║   [LIVE CAMERA VIEWFINDER]   ║   │ ← ~40% screen height
│ ║   white frame corners        ║   │   active by default
│ ║   detecting in real-time     ║   │   16px rounded corners
│ ║                              ║   │
│ ║   ⊙ tap to capture          ║   │
│ ╚══════════════════════════════╝   │
│                                    │
│ [📷 Scan]  [🔗 Link]  [✎ Type]    │ ← mode chips below viewfinder
│   ●         ○         ○            │   active dot under selected
│                                    │
│ Categories ───────                 │
│ [📱] [💄] [💊] [👗] [🛒] [→]       │ ← 9 chips horizontal scroll
│                                    │
│ ───────                            │
│ 2 free comparisons left this month │
│ ─ Home  History  Profile ───       │
└────────────────────────────────────┘
```

**Mode-tap behavior** (fixes the current "uneven" surfacing):
- **📷 Scan** (default) — viewfinder live, capture button at bottom
- **🔗 Link** tap → viewfinder card morphs (240ms cross-fade) into URL input field with optional 2nd URL slot. Camera releases.
- **✎ Type** tap → viewfinder card morphs into existing `SearchOverlay` inline, with recent searches as chips below.

Same physical card real-estate, three different states. RTL flips chip order.

### 4b. Results — winner-celebration post-reveal

```
┌────────────────────────────────────┐
│ ‹                       🔖   ↗     │
│                                    │
│ YOUR WINNER                        │ ← eyebrow
│ iPhone 15 Pro                      │ ← display 28pt Geist Bold
│ 295 BHD · ★ 4.7                    │
│                                    │
│  ┌─ subtle emerald glow ring ─┐   │
│  │    [product image]          │   │ ← winner card
│  │                             │   │
│  │   ✓ Best for you            │   │ ← emerald pill bottom-left
│  └─────────────────────────────┘   │
│                                    │
│  ┌──────────────────────────────┐  │
│  │ 🔍  12 shoppers in Capital   │  │ ← cohort badge
│  │     governorate also picked  │  │   (slides in after pulse)
│  │     this                     │  │
│  └──────────────────────────────┘  │
│                                    │
│ ──────                             │
│ Why we picked this                 │
│ Better camera and battery make     │
│ this the call for shoppers prio-   │ ← conversational verdict
│ ritizing photo + all-day use.      │
│                                    │
│ ──────                             │
│ Where the runner-up wins           │ ← honest counter-narrative
│                                    │   (renamed from "trade off"
│ ┌──────────────────────────────┐  │   per copy audit)
│ │ ↘ Cheaper price              │  │
│ │   Galaxy S24 saves 76 BHD    │  │
│ └──────────────────────────────┘  │
│ ┌──────────────────────────────┐  │
│ │ ↘ Smoother display           │  │
│ │   120Hz vs 60Hz              │  │
│ └──────────────────────────────┘  │
│                                    │
│ ──────                             │
│ Side by side          ▼            │ ← collapsible spec table
│ Reviews               ▼            │ ← collapsible
│ Where to buy          ─            │
│ [Apple BHR · 295 BHD] [Amazon...]  │
└────────────────────────────────────┘
│ [+ What's next?]   [💾]   [↗]      │ ← sticky footer
└────────────────────────────────────┘
```

**Key moves vs. current:**
1. Winner above the fold; loser below (current shows side-by-side equal weight)
2. Cohort badge inline — your differentiator surfaced, not buried
3. **"Where the runner-up wins"** is a NEW section — gives the loser its dignity, prevents "but maybe I should pick the other?" doubt by acknowledging it
4. Specs / Reviews collapsed by default — post-reveal feels like an answer, not a data dump
5. "Where to buy" as the practical close — retailer chips with prices in user's currency
6. Sticky footer with "What's next?" + Save + Share — re-engagement built in

### 4c. Bottom nav refresh

Selected icon: emerald + small emerald dot below + scale 1.0 → 1.15 → 1.0 spring + filled icon. Inactive: filled black 60% opacity. Tab bar bg white + 1px top border. RTL auto-mirrors tab order.

### 4d. Profile screen — surface cohort match prominently

Cohort match card moved to TOP of Profile (currently buried). Card shows match strength badge, peer count + governorate, progress bar to "Strong." Tap reveals: which priorities your peers share, what categories they buy, how to improve match.

### 4e. Referral redesign — engaging + revealing

**Share moment** (sender taps Share on Results):

Bottom sheet with **live preview** of what friend will see, **privacy toggles** updating preview in real-time, **gamified reward block** showing what sender unlocks (+1 Deep Review credit + promise of +5 if friend joins).

**Send confirmation:**
- Sheet collapses
- Toast slides down: "✦ Sent to Ahmed. We'll add 5 more if they sign up."
- Small emerald sparkle particle burst (tasteful, not Cal-AI-cheesy)

**Invitee landing** (`qaren.app/c/{token}?ref=QR-XXXXXX`) — partial blur with curiosity gap:

**Visible:**
- Product names + both product images side-by-side (no winner badge)
- Cohort badge ("12 shoppers in Capital agreed with Ahmed's pick")
- Some basic specs (release year, screen size)
- Sender opener ("Ahmed thought you'd like this")

**Gated until quiz or signup:**
- The winner ✓ + emerald glow
- The "Why we picked this" reasoning
- Personalized score

**Two CTAs:**

| Path | CTA | Result |
|---|---|---|
| Hot path (curious) | **"See how it scores for YOU"** (emerald — the one-time visual exception) | 4Q quiz → reveal personal score + winner + reasoning → soft signup CTA |
| Cool path (skim-readers) | "Just give me the app" (small text link) | Onboarding → signup → invitee credit applied → can revisit comparison anytime in History |

Both routes apply the invitee credit. Both end at signup. Hot path is the conversion lever; cool path keeps anyone not in the mood for a quiz.

**Why this beats no gate:** gate is on EMOTION (verdict + score), not INFORMATION (products + cohort). We're not hiding what they came for; we're inviting them to a moment.

**Why this beats full gate:** anyone who skims for 5 seconds gets enough context. No frustration.

### 4f. Bonus expiry mechanics

| Credit | Expiry | Reason |
|---|---|---|
| **3 base free comparisons** | None | Keeps freemium generosity. No "they took it back" reviews. |
| **2 invitee bonus comparisons** | **3 days from signup** | Drives invitee to first compare quickly → Loop 2 fires |
| **5 inviter bonus comparisons** | **3 days from issue** | Drives inviter back to compare again |
| **Deep Review credits** (Loop 1) | **3 days from issue** | Same urgency principle |

**Surfaced on Home:**
```
5 free comparisons available
• 3 anytime
• 2 from Ahmed (expires in 2d 14h) ◔
```

**Push notifications (gift-framing, never deadline-pressure):**
- 24h before expiry: "Don't forget — your 2 bonus comparisons from Ahmed expire tomorrow."
- 1h before expiry: "Last chance — your bonus expires in 1 hour."

**Loop 2 chain (existing backend, new frontend signaling):**
1. Friend taps link → invitee_id stored
2. Friend completes onboarding + signs up → `link_invite_to_user` fires
3. Friend gets **5 comparisons** at signup (3 + 2 invitee bonus) — surfaced as "5 free — 2 from Ahmed"
4. Friend hits Compare → completes first → `try_trigger_loop2` fires
5. AbuseDetectionService green-lights → **Ahmed gets +5 (Free) or +10 (Premium)** + Expo push: "Ahmed, your friend just compared — you got 5 bonus comparisons. They expire in 3 days."

### 4g. Copy audit — engaging never scary

Apply this table across all screens. Sweep for any "scary" copy missed during build.

| Where | OLD | NEW |
|---|---|---|
| Invitee landing | "Take 30s quiz to reveal" | "See how it scores for YOU" |
| Invitee landing | "🔒 Locked. Take quiz to unlock." | (no full gate — partial blur only) |
| Results section title | "What you trade off" | "Where the runner-up wins" |
| Results section title | "Why this won" | "Why we picked this" |
| Results footer CTA | "Compare another" | "What's next?" |
| Loading stalled 8s | "Cross-checking sources for accuracy" | "Pulling in the latest from {n} retailers" |
| Loading stalled 15s | "Locking in the most accurate match" | "Calibrating the final ranking" |
| Loading stalled 25s | "Sharper match when you add a brand" | "Try iPhone 15 vs Galaxy S24 — sharper with brand + model" |
| Backend 5xx | "We couldn't compare those right now" | "Try with brand or model — sharper match every time" |
| Onboarding screen 14 | "Reading priors from 388 shoppers" | "388 GCC shoppers helped train this" |
| Onboarding screen 14 | "Generating your shopping advisor" | "Crafting your shopping advisor" |
| Onboarding screen 16 | "One last step" | "Save your advisor" |
| Onboarding screen 17 | "Want price-drop alerts?" | "Be the first to know when prices drop" |
| Home empty state | (no copy) | "Compare anything. Decide smarter." |
| Home freemium counter | "1 of 3 free comparisons used" | "2 free comparisons left this month" |
| Profile cohort card | "Match strength: Strong" | "✦ Strong match — 47 peers in Capital" |
| Share send confirmation | "Shared! +1 credit" | "✦ Sent to Ahmed. We'll add 5 more if they sign up." |
| Tips carousel | "We're not paid by sellers." | "We work for you — never paid by sellers." |
| Trust bridge bullets | "Personal data on device" | "Your data lives on your device" |
| Trust bridge bullets | "Cohort match is anonymous" | "We match anonymously — no name attached" |
| Trust bridge bullets | "Skip anything anytime" | "Skip anything — and edit later" |

**Three principles:**
1. **"Try X" not "Get X"** — try is invitational
2. **Concrete numbers > abstract claims** — "388 GCC shoppers" beats "many shoppers"
3. **Active verbs the brand owns** — *crafting, calibrating, calling, picking, pulling in.* Avoid *generated, processed, finished, trying, waiting.*

---

## Section 5 — Icon Inventory + 5 Hero Illustrations

### 5a. Icon system

**Style:** Bold filled + 2-tone, geometric, Cal-AI-icon weight (filled, chunky, no outline thinness).

**28 custom icons to commission:**

| Category | Count | Icons |
|---|---|---|
| Brand mark | 1 | Q-magnifier (standalone) |
| Mode | 3 | Scan, Link, Type |
| Tabs | 3 | Home, History, Profile |
| Categories | 9 | Electronics, Makeup, Skincare, Haircare, Fragrances, Supplements, Grocery, Fashion, Other |
| Stages / Results | 5 | Specs, Prices, Reviews, Scoring, Verdict |
| Cohort / Personalization | 4 | Cohort, Priority, Budget, Brand-heart |
| Reward / Status | 3 | Sparkle ✦, Match-strength, Countdown ◔ |

**~15 Lucide icons retained** (utility): `ArrowLeft, ArrowRight, X, Plus, Check, Search, Bell, Settings, Eye, EyeOff, Lock, ChevronRight, ChevronDown, Filter, Trash2`.

### Icon spec contract

```
Style:        Filled mono + 2-tone (1 emerald accent permitted)
Stroke width: 0 (filled, no outlines)
Grid:         24x24 base, 1px keyline (rounded ends + corners)
Corner radius: 2px on letterforms, 4px on geometric panels
Color tokens: Primary fill #0A0A0B, accent #10B981, white #FFFFFF
Format:       SVG (single-path where possible, separate accent path)
Output:       React Native via react-native-svg, registered in src/icons/
RTL:          Most icons direction-agnostic. Direction-bearing ones get
              `flipForRTL` prop in the component.
```

### Code structure

```
src/icons/
├── QaranIcon.tsx          // Q-magnifier brand mark
├── ModeIcons.tsx          // Scan, Link, Type
├── TabIcons.tsx           // Home, History, Profile
├── CategoryIcons.tsx      // 9 category icons (lookup by slug)
├── StageIcons.tsx         // Specs, Prices, Reviews, Scoring, Verdict
├── CohortIcons.tsx        // Cohort, Priority, Budget, Brand-heart
├── RewardIcons.tsx        // Sparkle, MatchStrength, Countdown
└── index.ts               // re-exports + flipForRTL helper
```

### 5b. The 5 hero illustrations

| # | Where | What | Production |
|---|---|---|---|
| 1 | Onboarding screen 3 (value prop) | Stylized phone mockup at 3/4 angle showing real Qaren Results UI with two product cards + emerald winner badge + glow ring around winner. Phone in pure black gradient. | Figma → SVG export. Designer work. |
| 2 | Onboarding screen 12 (cohort proof) | Editorial bar chart, 4 vertical bars, emerald accent on user's matched bar. Below: ~20×20 dot grid (388 dots), 12 emerald-highlighted "your peers" dots. No characters. | **Hand-coded.** SVG + Reanimated. Bars rise stagger 80ms; dots fade left-to-right; "0 → 388" counter. |
| 3 | Onboarding screen 13 (anticipation) | 5 concentric circles, each rotating at different speeds (8s, 6s, 5s, 4s, 3s, counter-rotating). Center: small Q-logo. Subtle emerald gradient on innermost ring only. | **Hand-coded.** SVG + Reanimated. ~80 lines. |
| 4 | Onboarding screen 14 (theatrical loading — centerpiece) | Larger dramatic version of #3. Big Q-logo (~120px) at center. 3 emerald rings expand outward continuously (~2s each, fade as they expand). | **Hand-coded.** Reanimated 3 + react-native-svg. Gentle scale-pulse on logo + 3 rings staggered every 700ms. |
| 5 | Onboarding screen 15 (reveal) | Clean abstract burst — 8 thin lines radiating outward from center at 45° intervals, emerald. Below: Q-logo on white circular badge with subtle shadow. Above: emerald check ✓. No confetti, no particles. | **Hand-coded.** Lines extend 0 → 32px stagger 60ms; Q-badge scale 0.9 → 1.0 spring; check ✓ stroke-draw 0 → 100% + haptic medium. |

**Build savings:** illustrations #2-5 hand-coded as SVG + Reanimated components. No Lottie files, no JSON payloads, no designer round-trips, no marketplace assets. Bundle impact: ~zero.

---

## Section 6 — Implementation Phasing

### Phase 1 — Visual foundation (1 session)
**Goal:** existing app inherits new identity without flow changes.

| Work | Files |
|---|---|
| Theme tokens (black + emerald hybrid) | `src/theme/index.ts` |
| Geist font integration (EN) | `app.json` (Expo Font), `src/theme/fonts.ts` (new) |
| Typography tokens (`hero`, `bodyEmphasis`, `eyebrow`) | `src/theme/index.ts` |
| Black CTAs across existing buttons | `src/components/Button.tsx` |
| `src/icons/` infrastructure + Q-mark + 6 utility icons | new dir |
| Motion tokens (`variableEasing`, `springConfig`) | `src/theme/motion.ts` (new) |

**Risk:** low. **Test:** snapshot tests on existing screens in light + RTL.

### Phase 2 — Onboarding overhaul (1-2 sessions)
**Goal:** 17-screen Cal-AI-Lite onboarding live behind feature flag `ENABLE_NEW_ONBOARDING`.

| Work | Notes |
|---|---|
| 17 screen components | Sub-components under `src/screens/onboarding/` |
| `OnboardingFlow` orchestrator | Owns step state + progress bar + navigation |
| `CounterTicker`, `StageChecklist`, `ProgressBarVariableEasing` | Reusable across onboarding + Results |
| Hero illustration #1 (phone mockup) | Figma → SVG export, designer work |
| Hand-code illustrations #2-5 | React components using `react-native-svg` + Reanimated |
| Theatrical loading screen 14 (3.2s minimum) | Stage copy cycler + counter + progress |
| Force sign-in at screen 16 | Drop "skip" link, integrate Apple/Google/Email |
| Backend: attribution endpoint (`POST /api/v1/auth/attribution`) | Accepts `source` enum |
| All copy in i18n EN + AR | ~85 new keys |

**Risk:** medium. **Test:** completion rate ≥75%, drop-off heatmap per screen.

### Phase 3 — Home + Results redesign (1 session)
**Goal:** main surfaces match new identity.

| Work | Notes |
|---|---|
| Camera-first card layout (Home) | Refactor `HomeScreen.tsx` — viewfinder is 40% card, not background |
| 3-mode equal chips (Scan/Link/Type) | Mode-tap morphs card content |
| Stage checklist + ghost cards on Results | Replaces current skeleton — uses SSE callbacks already in `streamComparison` |
| Winner-celebration post-reveal | Refactor `ResultsScreen.tsx` |
| Cohort badge inline + slide-in animation | New `CohortBadge` component, RTL-aware |
| Streaming counter ticks on prices | `CounterTicker` from Phase 2 reused |
| All Lucide → custom icon migration | 28 custom icons swapped in |
| "What's next?" sticky footer | Replaces "Compare another" |

**Risk:** medium. **Test:** session-length, share-tap rate, retry rate.

### Phase 4 — Referral + bonus expiry (1 session)
**Goal:** Loop 2 funnel optimized for virality.

| Work | Notes |
|---|---|
| Partial-blur invitee landing | `ReferralLandingScreen.tsx` refactor |
| 4Q quiz reveal screen | `InviteeQuizScreen.tsx` — add personalized score animation |
| Updated share bottom sheet | `ShareBottomSheet.tsx` — live preview, gamified reward block |
| Backend: `expires_at` column on `referral_redemptions` + bonus credits | Migration 018 |
| Cron: expire bonuses, send 24h-before push | `scripts/cron_expire_bonuses.py` |
| Push notification copy (gift-framing) | EN + AR |
| Home countdown surface | "5 free — 2 from Ahmed (expires 2d 14h)" |

**Risk:** medium. **Test:** Loop 2 trigger rate ≥35%, inviter re-engagement rate.

### Phase 5 — Profile + polish (1 session)
**Goal:** close the loop, audit everything.

| Work | Notes |
|---|---|
| Cohort match card promoted to top of Profile | `ProfileScreen.tsx` refactor |
| Tips carousel during 8s+ waits | New `LoadingTipsCarousel`, 5 tips EN + AR |
| All 28 custom icons finalized | Round trip with designer for survivors |
| RTL audit | Run app entirely in Arabic, fix mirroring bugs |
| Accessibility audit | Touch targets 44pt min, contrast WCAG AA, screen reader labels |
| Copy audit applied globally | Sweep for any "scary" copy missed |
| Feature flag canary | `ENABLE_NEW_ONBOARDING`: 10% → 50% → 100% over 7 days |

**Risk:** low. **Test:** zero RTL/A11y regressions.

### Phase 6 (separate scope) — Web + landing pages
After app ships. Separate brainstorm + design doc:
- Marketing site (qaren.app)
- Public comparison viewer (web HTML, for `/c/{token}` opened on desktop)
- Referral landing web variant
- App Store listings refresh

---

## Section 7 — Team Execution Model

The implementation will be carried out by a **4-Opus agent team** spawned via TeamCreate. This is the same pattern used in Sessions 26, 35, 38, 41 — proven to ship complex multi-file features.

### Team composition

All members **claude-opus-4-7** (NOT Sonnet, NOT Haiku). Per user directive.

| Agent | Role | Primary scope |
|---|---|---|
| **frontend-visual** | Theme, fonts, motion, icons, hero illustrations | Phase 1 + Phase 5 polish; owns `src/theme/`, `src/icons/`, `src/components/illustrations/` |
| **frontend-flow** | Onboarding screens, Home, Results, Referral, Profile | Phases 2-4 frontend; owns `src/screens/`, `src/components/onboarding/`, route changes in `App.tsx` |
| **backend** | Attribution endpoint, expires_at migration, cron, push notifications | Phase 2 + Phase 4 backend; owns `app/api/auth_routes.py`, `app/services/referral_service.py`, `app/services/push_service.py`, `migrations/018_*.sql`, `scripts/cron_expire_bonuses.py` |
| **test-qa** | Red-green tests, cross-QA on every other agent's work, copy audit, RTL audit, accessibility audit | All phases; owns `tests/`, `SmartCompareApp/__tests__/` |

### Mandatory team rules (per user directive)

1. **Features must be 100% complete before team disassembles.** No "we'll fix that later." No partial commits at end.
2. **Cross-QA is mandatory.** Each agent must QA at least one other agent's work. If work is subpar or missed, it goes back. No agent leaves without QA pass on their work AND a QA review they performed on another agent's work.
3. **Idle agents write red-green tests.** When an agent finishes their primary task and is waiting on QA, they must write red-green tests targeting **80% coverage** on the new feature, OR wait actively for QA results. No idle waiting.
4. **Work must be delegated explicitly** — not "see what's left." TaskCreate with clear ownership; TaskUpdate with `owner` field; TaskList visible to all.
5. **Path-restricted commits.** All agents use `git commit -m "msg" -- <paths>` (NOT `git commit -- <paths> -m "msg"` — `-m` after `--` is parsed as a path; see CLAUDE.md). Prevents sweeping teammates' staged work.

### Required tools / skills / plugins

Each agent must use the following tools where applicable:

| Tool / Skill | Used by | When |
|---|---|---|
| **typescript-lsp** (via project config) | All frontend agents | Trust ONLY `npx tsc --noEmit` exit code as ground truth (per CLAUDE.md MEMORY note); ignore stale LSP errors |
| **context7 MCP** (`mcp__plugin_context7_context7__query-docs`) | All agents | Whenever touching a library version-sensitive (Reanimated 3, Expo Font, react-native-svg, expo-notifications). Don't guess from training data; fetch current docs. |
| **superpowers:code-reviewer** (or `code-review:code-review`) | test-qa agent | Every cross-QA pass on another agent's work |
| **superpowers:test-driven-development** | test-qa agent + idle agents | Red-green cycle — write failing test, confirm fail, write minimal code, confirm pass |
| **superpowers:verification-before-completion** | All agents | Before claiming any work done. Must run verification command + confirm output. Evidence > assertions. |
| **superpowers:systematic-debugging** | All agents | When bugs surface. Stop coding, diagnose, fix root cause. |
| **superpowers:dispatching-parallel-agents** | Team leader (orchestrator) | When tasks are independent — fire all in one message |
| **superpowers:prove-it-works** | test-qa agent | Bug fixes must reproduce the bug first, then verify fix |
| **figma:figma-implement-design** | frontend-visual agent | When implementing hero illustration #1 (phone mockup) from designer Figma file |
| **plugin_supabase_supabase__apply_migration** | backend agent | For migration 018 (expires_at). NOT SQL Editor (silent failures). Tracks in migration history table. |

### Workflow (per phase)

```
Team leader:
  1. spawn 4 agents (TeamCreate, all Opus, bypassPermissions mode)
  2. delegate primary tasks via TaskCreate with explicit owner
  3. agents work in parallel on non-overlapping files
  4. as each agent completes primary task:
     a. mark TaskUpdate status=completed
     b. immediately claim a QA task (review another agent's work)
     c. if no QA available, write red-green tests targeting 80%
     d. wait for incoming QA on own work
  5. QA pass criteria:
     a. npx tsc --noEmit clean
     b. existing tests pass
     c. new tests written, hit 80% coverage
     d. RTL works (visual + functional)
     e. copy audit clean (no "scary" language)
     f. accessibility (touch targets ≥44pt, contrast WCAG AA)
  6. if QA fails: send back to original author with specific findings
  7. iterate until all features 100% complete + all QAs passed
  8. final commits (path-restricted) + team disassemble
```

### Exit criteria (no team disassembly until all true)

- [ ] All Phase N tasks marked completed in TaskList
- [ ] `npx tsc --noEmit` exits 0 (frontend)
- [ ] `python -m pytest tests/ -v -m "not (live_unit or live_db or integration)"` passes (backend, free unit tests)
- [ ] Coverage report shows ≥80% on new code
- [ ] Each agent has performed at least one QA on another agent's work
- [ ] All QA findings either resolved or explicitly deferred with TaskCreate'd follow-up
- [ ] All copy audited for "scary" language
- [ ] RTL run-through complete (manual visual check, recorded in commit message)
- [ ] Accessibility check complete (touch targets, contrast, screen reader labels)
- [ ] Feature flag set per phase (`ENABLE_NEW_ONBOARDING` etc.)

---

## Section 8 — Success Metrics

Instrumented in Phase 1, measured per phase.

| Metric | Today (baseline) | Target after redesign |
|---|---|---|
| Onboarding completion rate | (measure first) | ≥75% |
| First-comparison conversion (signup → compare) | (measure first) | ≥85% |
| Loop 2 trigger rate (invitee compares within 3d) | low (no expiry) | ≥35% |
| Inviter share rate (% users who tap Share) | (measure first) | ≥15% |
| Time-to-first-value (signup → first compare) | (measure first) | ≤4 minutes |
| Bonus claim rate (% who use 2 invitee bonuses before 3d expiry) | n/a | ≥60% |
| App Store rating after 30d on new flow | current | +0.3 stars |

---

## Section 9 — Open Questions / TBD

| # | Question | Owner | Resolve before |
|---|---|---|---|
| 1 | Designer for hero illustration #1 (phone mockup) — internal or commission? | Ahmed | Phase 2 start |
| 2 | Geist font license — confirm SIL OFL allows commercial mobile redistribution | backend agent | Phase 1 start |
| 3 | `migrations/018` — exact `expires_at` semantics on existing `referral_redemptions` (data migration for in-flight credits?) | backend agent | Phase 4 start |
| 4 | Push notification testing on physical iOS + Android (Expo Go vs EAS dev build) | test-qa agent | Phase 4 mid |
| 5 | Tips carousel content review by Ahmed (5 tips, EN + AR) | Ahmed | Phase 5 |
| 6 | Cohort match card "improve match" tap behavior — what does it surface? Edit demographics? Re-take quiz? | frontend-flow agent | Phase 5 |
| 7 | Web landing pages (Phase 6) — wait for app to ship before designing? | Ahmed | After Phase 5 ships |

---

## Appendix — File touch list (rough)

**Frontend (new):**
- `src/screens/onboarding/` (17 files)
- `src/components/illustrations/` (5 files: PhoneMockup, CohortBarChart, ConcentricMotif, LoadingRings, RevealBurst)
- `src/components/onboarding/OnboardingFlow.tsx`
- `src/components/CounterTicker.tsx`
- `src/components/StageChecklist.tsx`
- `src/components/StreamingProductCard.tsx`
- `src/components/CohortBadge.tsx`
- `src/components/LoadingTipsCarousel.tsx`
- `src/icons/` (8 files: QaranIcon, ModeIcons, TabIcons, CategoryIcons, StageIcons, CohortIcons, RewardIcons, index)
- `src/theme/fonts.ts`
- `src/theme/motion.ts`

**Frontend (modified):**
- `src/theme/index.ts` (color tokens, typography tokens, radii.hero)
- `src/components/Button.tsx` (black CTA)
- `src/components/SkeletonLoader.tsx` (`variant="ghostCard"`)
- `src/components/ProgressBar.tsx` (`variableEasing` prop)
- `src/screens/HomeScreen.tsx` (camera-first card, 3-mode chips)
- `src/screens/ResultsScreen.tsx` (winner-celebration, post-reveal layout, "Where the runner-up wins")
- `src/screens/ProfileScreen.tsx` (cohort match card promoted)
- `src/screens/ReferralLandingScreen.tsx` (partial blur, two CTAs)
- `src/screens/InviteeQuizScreen.tsx` (personalized score reveal)
- `src/components/ShareBottomSheet.tsx` (live preview, reward block)
- `App.tsx` (route changes if needed)
- `src/i18n/en.json` + `src/i18n/ar.json` (~120 new keys)

**Backend (new):**
- `migrations/018_referral_bonus_expires_at.sql`
- `scripts/cron_expire_bonuses.py`

**Backend (modified):**
- `app/api/auth_routes.py` (POST /attribution)
- `app/services/referral_service.py` (expires_at logic, push trigger)
- `app/services/push_service.py` (gift-framing copy, expiry reminders)
- `app/services/usage_service.py` (account for expired bonuses)

**Tests (new):**
- `SmartCompareApp/__tests__/onboarding/*` (17 screen tests)
- `SmartCompareApp/__tests__/components/CounterTicker.test.tsx`
- `SmartCompareApp/__tests__/components/StageChecklist.test.tsx`
- `SmartCompareApp/__tests__/screens/ReferralLandingScreen.test.tsx`
- `tests/test_attribution_endpoint.py`
- `tests/test_referral_expiry.py`
- `tests/test_cron_expire_bonuses.py`

---

**End of design specification.** Approved 2026-05-06. Implementation begins via 4-Opus team per Section 7.
