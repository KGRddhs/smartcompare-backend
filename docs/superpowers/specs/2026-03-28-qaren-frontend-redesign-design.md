# Qaren Frontend Redesign — Design Specification

**Date:** 2026-03-28
**Status:** Approved
**App Name:** Qaren (قارن) — formerly SmartCompare
**Tagline:** "Compare smarter" / "قارن بذكاء"

---

## Quick Visual Overview

### App Architecture at a Glance
```
┌─────────────────────────────────────────────────────────────────┐
│                        QAREN (قارن)                             │
│                   "Compare smarter"                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  FIRST LAUNCH FLOW:                                             │
│  ┌────────┐  ┌────────────┐  ┌──────────┐  ┌────────────────┐  │
│  │ Splash │→│ Onboarding  │→│  Sign Up  │→│  Home (Camera)  │  │
│  │  1.5s  │  │  6 steps   │  │  / Login  │  │                │  │
│  └────────┘  └────────────┘  └──────────┘  └────────────────┘  │
│                                                                 │
│  RETURNING USER:                                                │
│  ┌────────┐  ┌────────────────┐  ┌──────────┐  ┌───────────┐  │
│  │ Splash │→│  Home (Camera)  │→│ Compare  │→│  Results   │  │
│  └────────┘  └────────────────┘  └──────────┘  └───────────┘  │
│                                                                 │
│  BOTTOM NAVIGATION:                                             │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │   📷 Home        ◷ History        👤 Profile            │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                 │
│  PAYWALL (after 3 free comparisons):                            │
│  Compare 1: ✅ Full access, no interruption                     │
│  Compare 2: 💬 Subtle "2 of 3 free" pill                       │
│  Compare 3: ✅ Results shown → bottom sheet paywall             │
│  Compare 4+: 🔒 Hard paywall before results                    │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│  DESIGN: Light + Minimal  │  ACCENT: Emerald #10B981           │
│  FONTS: Inter (EN) + Cairo (AR)  │  RTL: Full Arabic support   │
└─────────────────────────────────────────────────────────────────┘
```

### Color Palette Visual
```
  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
  │ ████████ │ │ ████████ │ │ ████████ │ │ ████████ │ │ ████████ │
  │ #FFFFFF  │ │ #F8F8FA  │ │ #1A1A1E  │ │ #10B981  │ │ #ECFDF5  │
  │ bg.main  │ │ bg.card  │ │ text     │ │ accent   │ │ acc.lite │
  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘
  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
  │ ████████ │ │ ████████ │ │ ████████ │ │ ████████ │
  │ #6B7280  │ │ #EF4444  │ │ #F59E0B  │ │ #E5E7EB  │
  │ text.sec │ │ destroy  │ │ warning  │ │ border   │
  └──────────┘ └──────────┘ └──────────┘ └──────────┘
```

---

## 1. Design System

### Visual Direction
Editorial Magazine approach — Cal AI's proven structural patterns (clean white, camera-first, 3-tab nav) wrapped in a typography-driven, premium editorial identity. Think Apple.com product pages meets Cal AI. Content (product images, prices, comparisons) is the star — no decorative gradients or UI widget clutter.

### Color Palette
| Token | Value | Usage |
|-------|-------|-------|
| `bg.primary` | `#FFFFFF` | Main background |
| `bg.secondary` | `#F8F8FA` | Card backgrounds, sections |
| `text.primary` | `#1A1A1E` | Headings, body text |
| `text.secondary` | `#6B7280` | Descriptions, metadata |
| `text.placeholder` | `#9CA3AF` | Input placeholders |
| `accent` | `#10B981` | CTAs, winner badges, active states |
| `accent.light` | `#ECFDF5` | Winner card background highlight |
| `destructive` | `#EF4444` | Delete, errors, "worse" indicator |
| `warning` | `#F59E0B` | Similar/tie indicator |
| `border.light` | `#E5E7EB` | Card borders, dividers |
| `border.medium` | `#D1D5DB` | Input borders |

### Typography
| Level | Size | Weight | Font |
|-------|------|--------|------|
| Display | 28pt | Bold | Inter (EN) / Cairo (AR) |
| Title | 20pt | SemiBold | Inter / Cairo |
| Body | 16pt | Regular | Inter / Cairo |
| Caption | 13pt | Regular | Inter / Cairo |
| Small | 11pt | Regular | Inter / Cairo |

- Arabic line-height: 1.7x (English: 1.5x)
- Only Regular + SemiBold + Bold weights loaded (~300KB total)

### Spacing
Base unit: 4px. Scale: 4, 8, 12, 16, 20, 24, 32, 48.

### Border Radius
- Cards: 16px
- Buttons: 12px
- Chips: 999px (pill)
- Inputs: 12px

### Shadows
Minimal. Elevated cards only: `0 1px 3px rgba(0,0,0,0.08)`

### Icons
Lucide React Native — tree-shakeable, consistent line-weight, RTL-friendly.

---

## 2. Screen Architecture

### Navigation
Bottom tab bar with 3 tabs:
- **Home** (camera icon) — Camera-first with search overlay
- **History** (clock icon) — Past comparisons, searchable
- **Profile** (user icon) — Settings, preferences, language, account

### User Flows
```
First Launch:
  Splash → Onboarding (6 steps) → Sign Up/Login → Home (camera)

Returning User:
  Splash → Home (camera) → Compare → Results → (save/share)

Guest Flow (no account):
  Splash → Onboarding (6 steps) → Home → 3 free comparisons → Paywall
```

### Screen Inventory (10 screens)
| Screen | Purpose | Auth Required |
|--------|---------|---------------|
| SplashScreen | Brand moment + auth check (1-2s) | No |
| OnboardingScreen | 6-step personalization wizard | No |
| LoginScreen | Email + Google + Apple sign in | No |
| RegisterScreen | Account creation | No |
| ForgotPasswordScreen | Password reset | No |
| HomeScreen | Camera-first + search bar + category chips | No (tracks free uses) |
| ResultsScreen | Single-scroll comparison result | No |
| HistoryScreen | Past comparisons list | Yes |
| ProfileScreen | Settings, language, preferences, account | Yes |
| PaywallScreen | Subscription options after 3 free uses | No |

### Key Changes from Current App
- CameraScreen absorbed INTO HomeScreen (camera is the default home view)
- AccountScreen renamed to ProfileScreen
- PreferencesScreen becomes part of OnboardingScreen (same questions, new design)
- SplashScreen and PaywallScreen are new
- ResultsScreen: 3 tabs → single scroll

---

## 3. Screen Layouts (Visual Wireframes)

### SplashScreen
```
┌──────────────────────────────────┐
│                                  │
│                                  │
│                                  │
│                                  │
│            ┌───────┐             │
│            │ قارن  │             │  Logo fades in, holds 800ms
│            └───────┘             │
│                                  │
│         Compare smarter          │  Tagline fades in 200ms after
│                                  │
│                                  │
│                                  │
│                                  │
└──────────────────────────────────┘
  Then: logo scales to top-left,
  camera fades in underneath
```

### OnboardingScreen (6 steps)
Cal AI style — one question per screen, full height, big typography.

```
STEP 1 — LANGUAGE                    STEP 2 — REGION
┌──────────────────────────┐         ┌──────────────────────────┐
│ ←  ████░░░░░░░░    skip  │         │ ←  ████████░░░░          │
│                          │         │                          │
│ Choose your              │         │ Where are you            │
│ language                 │         │ shopping?                │
│                          │         │                          │
│ اختر لغتك               │         │ This helps us find       │
│                          │         │ local prices             │
│                          │         │                          │
│ ┌──────────────────────┐ │         │ ┌──────────────────────┐ │
│ │      English         │ │         │ │  🇧🇭  Bahrain         │ │
│ └──────────────────────┘ │         │ └──────────────────────┘ │
│                          │         │ ┌──────────────────────┐ │
│ ┌──────────────────────┐ │         │ │  🇸🇦  Saudi Arabia    │ │
│ │      العربية          │ │         │ └──────────────────────┘ │
│ └──────────────────────┘ │         │ ┌──────────────────────┐ │
│                          │         │ │  🇦🇪  UAE              │ │
│                          │         │ └──────────────────────┘ │
│                          │         │ ┌──────────────────────┐ │
│       [   Next   ]       │         │ │  🇰🇼  Kuwait          │ │
└──────────────────────────┘         │ └──────────────────────┘ │
                                     │  + Qatar, Oman           │
                                     │       [   Next   ]       │
                                     └──────────────────────────┘

STEP 3 — PRIORITIES                  STEP 4 — BUDGET
┌──────────────────────────┐         ┌──────────────────────────┐
│ ←  ████████████░░░       │         │ ←  ████████████████░░    │
│                          │         │                          │
│ What matters             │         │ How do you               │
│ most to you?             │         │ usually spend?           │
│                          │         │                          │
│ Pick 1 to 3 priorities   │         │ ┌──────────────────────┐ │
│                          │         │ │ ◉ Budget              │ │
│ ┌────────┐ ┌─────────┐  │         │ │   Best deals          │ │
│ │ Price  │ │ Quality │  │         │ └──────────────────────┘ │
│ └────────┘ └─────────┘  │         │ ┌──────────────────────┐ │
│ ┌────────────────┐      │         │ │ ○ Balanced            │ │
│ │ Brand Reputation│      │         │ │   Price & quality     │ │
│ └────────────────┘      │         │ └──────────────────────┘ │
│ ┌────────────┐ ┌──────┐ │         │ ┌──────────────────────┐ │
│ │ Durability │ │ Eco  │ │         │ │ ○ Premium             │ │
│ └────────────┘ └──────┘ │         │ │   The best, any price │ │
│ ┌────────────────┐      │         │ └──────────────────────┘ │
│ │ Latest Features│      │         │                          │
│ └────────────────┘      │         │                          │
│                          │         │                          │
│  Back       [   Next  ]  │         │  Back       [   Next  ]  │
└──────────────────────────┘         └──────────────────────────┘

STEP 5 — LIFESTYLE                   STEP 6 — BRAND ATTITUDE
┌──────────────────────────┐         ┌──────────────────────────┐
│ ←  ████████████████████░ │         │ ←  ████████████████████  │
│                          │         │                          │
│ What describes           │         │ Your approach            │
│ you?                     │         │ to brands?               │
│                          │         │                          │
│ Pick any that apply      │         │ ┌──────────────────────┐ │
│                          │         │ │ ○ Brand Loyal         │ │
│ ┌────────┐ ┌────────┐   │         │ │   Stick with trust    │ │
│ │ Gamer  │ │ Fitness│   │         │ └──────────────────────┘ │
│ └────────┘ └────────┘   │         │ ┌──────────────────────┐ │
│ ┌──────┐ ┌───────────┐  │         │ │ ○ Function First      │ │
│ │Vegan │ │Sens. Skin │  │         │ │   Whatever works best │ │
│ └──────┘ └───────────┘  │         │ └──────────────────────┘ │
│ ┌────────┐ ┌──────────┐ │         │ ┌──────────────────────┐ │
│ │Student │ │  Parent  │ │         │ │ ○ Best of Both        │ │
│ └────────┘ └──────────┘ │         │ │   Good brand + func.  │ │
│ ┌──────────┐ ┌────────┐ │         │ └──────────────────────┘ │
│ │Minimalist│ │  Tech  │ │         │                          │
│ └──────────┘ └────────┘ │         │                          │
│                          │         │                          │
│  Back       [   Next  ]  │         │  Back    [ Complete ✓ ]  │
└──────────────────────────┘         └──────────────────────────┘
```

### HomeScreen (Camera-First)
```
┌──────────────────────────────────┐
│ قارن                    EN | عر  │  Logo left, lang toggle right
│                                  │
│  ┌────────────────────────────┐  │
│  │  🔍 Search products...     │  │  Tap to open search overlay
│  └────────────────────────────┘  │
│                                  │
│ [Electronics] [Grocery] [Supp.]  │  Horizontal scroll chips
│                                  │
│ ┌──────────────────────────────┐ │
│ │                              │ │
│ │                              │ │
│ │    ┌──────────────────┐     │ │
│ │    │                  │     │ │
│ │    │  CAMERA PREVIEW  │     │ │  Live viewfinder (~80%)
│ │    │                  │     │ │
│ │    │    (product)     │     │ │
│ │    │                  │     │ │
│ │    └──────────────────┘     │ │
│ │                              │ │
│ │         ┌────────┐          │ │
│ │         │   ◉    │          │ │  Capture (emerald ring)
│ │         └────────┘          │ │
│ │                              │ │
│ │  [Scan Product]       [URL]  │ │  Mode chips
│ └──────────────────────────────┘ │
│                                  │
│  2 of 3 free                     │  Subtle pill (gray→emerald)
│                                  │
├──────────────────────────────────┤
│  📷 Home    ◷ History   👤 Profile│  Bottom tabs
└──────────────────────────────────┘

SEARCH OVERLAY (when search bar tapped):
┌──────────────────────────────────┐
│  ← 🔍 [iPhone 15 vs Galaxy S24] │  Auto-focus, keyboard up
│──────────────────────────────────│
│                                  │
│  Recent                          │
│  ┌──────────────────────────┐    │
│  │  iPhone 15 vs Galaxy S24 │    │
│  │  Dyson V15 vs Shark      │    │
│  └──────────────────────────┘    │
│                                  │
│  Trending in Bahrain             │
│  ┌──────────────────────────┐    │
│  │  Samsung S25 vs iPhone 16│    │
│  │  PS5 Pro vs Xbox Series X│    │
│  └──────────────────────────┘    │
│                                  │
│          [keyboard]              │
└──────────────────────────────────┘
```

### ResultsScreen (Single Scroll)
```
┌──────────────────────────────────┐
│  ←  iPhone 15 vs Galaxy S24  ⋯  │  Back + query + share
│──────────────────────────────────│
│                                  │
│  ┌─────────────┐ ┌─────────────┐│
│  │   [image]   │ │   [image]   ││
│  │  iPhone 15  │ │  Galaxy S24 ││
│  │   $799      │ │   $749      ││
│  │   ⭐ 4.5    │ │   ⭐ 4.6    ││  Product cards
│  │             │ │  ╔═════════╗││
│  │             │ │  ║BEST PICK║││  Emerald badge
│  │             │ │  ╚═════════╝││
│  └─────────────┘ └─────────────┘│
│                                  │
│  ── Verdict ─────────────────── │
│  Galaxy S24 edges ahead with     │
│  better camera and $50 less      │
│                                  │
│  ── Price ───────────────────── │
│  Galaxy S24    $749  ✓ 6% less   │  Emerald "less" badge
│  iPhone 15     $799              │
│  📍 Amazon.sa                    │
│                                  │
│  ── Key Differences ─────────── │
│  📷 Camera     Galaxy wins       │
│  🔋 Battery    Galaxy wins       │
│  🖥️ Display    Tie               │
│  ⚡ Speed      iPhone wins       │
│                                  │
│  ── Specs ──────────── [▼ all]  │
│  ┌──────────┬──────────┬───────┐│
│  │          │ iPhone   │Galaxy ││
│  ├──────────┼──────────┼───────┤│
│  │ Display  │ 6.1"     │ 6.2" ││
│  │ Chip     │ A16      │Snap 8 ││
│  │ RAM      │ 6GB      │ 8GB ✓││  Winner dot
│  │ Storage  │ 128GB    │128GB  ││
│  │ Camera   │ 48MP     │50MP ✓││
│  └──────────┴──────────┴───────┘│
│  [Show differences only]         │
│                                  │
│  ── Reviews ────────────────── │
│  ┌──────────────────────────┐   │
│  │ "Excellent camera..."    │   │
│  │  — TechRadar  ⭐⭐⭐⭐½    │   │
│  └──────────────────────────┘   │
│  ┌──────────────────────────┐   │
│  │ "Great value flagship"   │   │
│  │  — GSMArena   ⭐⭐⭐⭐⭐    │   │
│  └──────────────────────────┘   │
│                                  │
│  ── Scores ─────────────────── │
│  Camera  ████████░░  ██████████ │
│  Battery ███████░░░  █████████░ │
│  Display █████████░  █████████░ │
│  Value   ███████░░░  █████████░ │
│                                  │
│  ── Was this helpful? ──────── │
│  👍  👎                          │
│  [accurate] [detailed] [fast]    │
│                                  │
│  ┌────────────┐ ┌────────────┐  │
│  │   Share    │ │    Save    │  │
│  └────────────┘ └────────────┘  │
│                                  │
├──────────────────────────────────┤
│  📷 Home    ◷ History   👤 Profile│
└──────────────────────────────────┘
```

### HistoryScreen
```
┌──────────────────────────────────┐
│  History                         │
│                                  │
│  ┌────────────────────────────┐  │
│  │  🔍 Search comparisons...  │  │
│  └────────────────────────────┘  │
│                                  │
│  Today                           │
│  ┌──────────────────────────────┐│
│  │ iPhone 15 vs Galaxy S24      ││
│  │ Winner: Galaxy S24 · $749    ││  Tap to re-open results
│  │ 2 hours ago            [⋯]  ││  Menu: delete, re-compare
│  └──────────────────────────────┘│
│                                  │
│  Yesterday                       │
│  ┌──────────────────────────────┐│
│  │ Dyson V15 vs Shark NZ801    ││
│  │ Winner: Dyson V15 · 89 BHD  ││
│  │ Yesterday              [⋯]  ││
│  └──────────────────────────────┘│
│  ┌──────────────────────────────┐│
│  │ CeraVe vs La Roche-Posay    ││
│  │ Winner: CeraVe · 4.2 BHD    ││
│  │ Yesterday              [⋯]  ││
│  └──────────────────────────────┘│
│                                  │
├──────────────────────────────────┤
│  📷 Home    ◷ History   👤 Profile│
└──────────────────────────────────┘

EMPTY STATE:
┌──────────────────────────────────┐
│  History                         │
│                                  │
│                                  │
│           ┌────────┐             │
│           │  📷🔍  │             │
│           └────────┘             │
│                                  │
│     Your first comparison        │
│        is waiting                │
│                                  │
│    ┌──────────────────────┐      │
│    │  Start Comparing →   │      │  Emerald CTA
│    └──────────────────────┘      │
│                                  │
├──────────────────────────────────┤
│  📷 Home    ◷ History   👤 Profile│
└──────────────────────────────────┘
```

### ProfileScreen
```
┌──────────────────────────────────┐
│  Profile                         │
│                                  │
│  ┌──────────────────────────────┐│
│  │  👤  Ahmed Al-Rashid         ││
│  │      ahmed@email.com         ││
│  │      Edit Profile →          ││
│  └──────────────────────────────┘│
│                                  │
│  Settings                        │
│  ┌──────────────────────────────┐│
│  │  🌐  Language      [EN|عر]  ││  Toggle switch
│  │  ─────────────────────────  ││
│  │  📍  Region        Bahrain ▾││  Dropdown
│  │  ─────────────────────────  ││
│  │  🎯  Preferences    Edit → ││  Opens onboarding edit mode
│  │  ─────────────────────────  ││
│  │  🔔  Notifications     ●○  ││  Toggle
│  └──────────────────────────────┘│
│                                  │
│  Support                         │
│  ┌──────────────────────────────┐│
│  │  📜  Privacy Policy      →  ││
│  │  ─────────────────────────  ││
│  │  📋  Terms of Service    →  ││
│  │  ─────────────────────────  ││
│  │  💬  Contact Us          →  ││
│  └──────────────────────────────┘│
│                                  │
│  ┌──────────────────────────────┐│
│  │  🚪  Log Out                 ││
│  │  ─────────────────────────  ││
│  │  🗑️  Delete Account         ││  Red text
│  └──────────────────────────────┘│
│                                  │
├──────────────────────────────────┤
│  📷 Home    ◷ History   👤 Profile│
└──────────────────────────────────┘
```

### PaywallScreen (Bottom Sheet)
```
┌──────────────────────────────────┐
│                                  │
│  (blurred results behind)        │
│                                  │
│▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓│  Frosted glass overlay
│┌────────────────────────────────┐│
││         ─────                  ││  Drag handle
││                                ││
││  Unlock unlimited              ││
││  comparisons                   ││
││                                ││
││  ┌──────────┐ ┌──────────────┐││
││  │ Monthly  │ │ Yearly -40%  │││  Yearly highlighted
││  │  $4.99   │ │ $2.99/mo     │││  with emerald border
││  └──────────┘ └──────────────┘││
││                                ││
││  ✓ Unlimited comparisons       ││
││  ✓ Full price history          ││
││  ✓ Priority processing         ││
││  ✓ Ad-free experience          ││
││                                ││
││  ┌────────────────────────────┐││
││  │      Subscribe Now         │││  Emerald CTA
││  └────────────────────────────┘││
││                                ││
││  Restore purchase              ││  Text link
││                                ││
││  Join smart shoppers            ││
││  across the GCC                 ││
│└────────────────────────────────┘│
└──────────────────────────────────┘
```

### RTL Mirror Example (Arabic)
```
ENGLISH (LTR)                        ARABIC (RTL)
┌──────────────────────┐             ┌──────────────────────┐
│ قارن          EN|عر  │             │  EN|عر          قارن │
│                      │             │                      │
│ 🔍 Search products.. │             │ ..ابحث عن منتجات 🔍  │
│                      │             │                      │
│ [Elec] [Groc] [Supp] │             │ [مكمل] [بقال] [إلك]  │
│                      │             │                      │
│  ←  Back   Next →    │             │    → التالي   رجوع ← │
└──────────────────────┘             └──────────────────────┘
  Logo: LEFT                           Logo: RIGHT
  Back arrow: ←                        Back arrow: →
  Progress: LEFT to RIGHT              Progress: RIGHT to LEFT
  Text: LEFT aligned                   Text: RIGHT aligned
```

### Comparison Loading Sequence (Skeleton → Real)
```
PHASE 1: SKELETON (0-2s)             PHASE 2: SPECS ARRIVE (2-4s)
┌──────────────────────┐             ┌──────────────────────┐
│ ← Finding products.. │             │ ← Analyzing specs... │
│ ████████████░░░░░░░░ │             │ ████████████████░░░░ │
│                      │             │                      │
│ ┌────────┐ ┌────────┐│             │ ┌────────┐ ┌────────┐│
│ │ ░░░░░░ │ │ ░░░░░░ ││             │ │iPhone15│ │GalaxyS2││
│ │ ░░░░░░ │ │ ░░░░░░ ││             │ │  ░░░░  │ │  ░░░░  ││
│ │ ░░░░░░ │ │ ░░░░░░ ││             │ │  ⭐4.5  │ │  ⭐4.6  ││
│ └────────┘ └────────┘│             │ └────────┘ └────────┘│
│                      │             │                      │
│ ── ░░░░░░░ ──────── │             │ ── Verdict ──────── │
│ ░░░░░░░░░░░░░░░░░░░ │             │ ░░░░░░░░░░░░░░░░░░░ │
│ ░░░░░░░░░░░░░░░░░░░ │             │                      │
│                      │             │ ── Price ─────────── │
│ ── ░░░░░░░ ──────── │             │ ░░░░  $749           │
│ ░░░░ ░░░░ ░░░░ ░░░░ │             │ ░░░░  $799           │
└──────────────────────┘             └──────────────────────┘
 (shimmer animation)                  (real data fading in)

PHASE 3: COMPLETE (done)
┌──────────────────────┐
│ ← Here's your comp.. │
│ ████████████████████ │  Progress bar completes
│                      │
│  Full results with   │
│  staggered fade-in   │
│  from top to bottom  │
│                      │
│  Winner reveal:      │
│  emerald border      │
│  draws on + haptic   │
└──────────────────────┘
```

---

## 4. Micro-interactions & Transitions

### Splash → Home
Qaren logo (قارن) fades in centered, holds 800ms. Logo scales down + moves to top-left (becomes nav header). Camera view fades in underneath. Total ~1.5s.

### Comparison Loading Sequence
Progressive skeleton with smooth non-linear progress bar (emerald):
1. (0-2s) "Finding products..." — skeleton cards shimmer in
2. (2-4s) "Analyzing specs..." — skeleton spec rows with typewriter dots
3. (4-6s) "Checking prices..." — price placeholders pulse
4. (6-8s) "Reading reviews..." — review skeletons fade in
5. (8-10s) "Calculating scores..." — progress ring fills
6. (done) "Here's your comparison" — content replaces skeletons with staggered fade-in

SSE events drive real progress. Bar animation smoothed so it never jumps or stalls. Early data = satisfying acceleration. Slow data = bar crawls (never stops).

### Winner Reveal
Scroll-triggered animation when verdict section enters viewport:
- Winner card gets emerald border that draws on (like signature being written)
- "Best Pick" badge slides in from right (left in RTL)
- Single haptic tap: `Haptics.impactAsync(ImpactFeedbackStyle.Medium)`

### Screen Transitions
- Tab switches: Cross-fade 200ms (not slide)
- History items: Staggered list entrance — each card fades in 50ms after previous
- Onboarding steps: Horizontal slide with slight parallax (title faster than options)

### Skeleton Screens
Every screen has a skeleton state. Never blank white screens.

### Language Switch
Brief fade-to-white (200ms) → Qaren logo splash animation → app restarts with new direction. Masks the required `I18nManager.forceRTL()` restart.

### 3 Free Comparisons Counter
- Subtle gray pill on home: "2 of 3 free"
- After comparison 2: pill turns emerald
- After comparison 3: results show normally, then bottom sheet slides up with frosted glass blur

### Removed from Original Proposal (not worth complexity)
- ~~Custom pull-to-refresh logo rotation~~ → Standard with emerald color
- ~~Card-expand shared element transition~~ → Clean fade-in (more reliable cross-platform)

---

## 5. Performance Constraints

### Targets
| Metric | Target |
|--------|--------|
| App bundle | < 25MB |
| Cold start to camera | < 2s |
| Screen transitions | < 200ms |
| Comparison end-to-end | < 10s (SSE makes it feel instant) |
| Active memory | < 150MB |

### Bundle Size Decisions
| Decision | Savings |
|----------|---------|
| No Lottie — Reanimated for all animations | ~3MB |
| Lucide icons (tree-shakeable) not full vector-icons | ~2MB |
| Inter + Cairo — only 3 weights each | ~1.2MB saved |
| No Redux/Zustand — hooks + Context | ~50KB |
| expo-image replaces RN Image | Built-in cache, blurhash, 60% faster |

### Anti-Sluggishness Rules
1. FlatList everywhere for lists (virtualized rendering)
2. Image caching via `expo-image` with blurhash placeholders
3. `React.memo` + `useMemo` for expensive computations
4. No inline styles in render — all `StyleSheet.create`
5. Debounce search at 300ms
6. AbortController on every API call — cancel on unmount
7. Skeleton screens instead of spinners
8. Hermes engine (already enabled via Expo)

### Not Adding (YAGNI)
- No offline mode
- No product image caching
- No background sync
- No push notifications
- No third-party analytics SDK

---

## 6. RTL & Internationalization

### Stack
```
expo-localization          → detect device locale
i18next + react-i18next    → translation engine + hooks
AsyncStorage               → persist language choice
I18nManager                → RTL layout direction (built-in)
```

### File Structure
```
src/i18n/
  index.ts    → i18next config
  en.json     → English strings (~200 keys)
  ar.json     → Arabic strings (~200 keys)
```

### String Key Format
Flat dot-notation: `"onboarding.language.title"`, `"home.search.placeholder"`, `"results.bestPick"`, etc.

### RTL Layout Rules (project-wide ban)
| BANNED | USE INSTEAD |
|--------|-------------|
| `marginLeft` / `marginRight` | `marginStart` / `marginEnd` |
| `paddingLeft` / `paddingRight` | `paddingStart` / `paddingEnd` |
| `left` / `right` (position) | `start` / `end` |
| `textAlign: 'left'` | `textAlign: 'auto'` |
| `borderLeftWidth` | `borderStartWidth` |

### Icon Flipping
**Flip in RTL** (via `transform: [{ scaleX: I18nManager.isRTL ? -1 : 1 }]`): back arrow, forward arrow, chevrons, send icon, share icon.
**Do NOT flip**: search, camera, star, heart, trash, settings, checkmarks, plus/minus.

### Arabic Typography
- Cairo font for all Arabic text
- Line-height: 1.7x (vs 1.5x English)
- Numbers stay LTR in RTL context (prices, ratings, dates)
- Product names from API stay in original language
- Search input: `textAlign: 'auto'` — adapts to content language
- Arabic strings ~30% wider than English — test for text overflow

### Language Switch Flow
1. User taps toggle in Profile or Onboarding
2. Save choice to AsyncStorage
3. Update i18next locale
4. `I18nManager.forceRTL(isArabic)` + `I18nManager.allowRTL(true)`
5. Show Qaren splash (masks restart)
6. `expo-updates.reloadAsync()` restarts app

### RTL Testing Checklist
- [ ] Every screen verified in EN and AR
- [ ] Border radius correct on Android RTL
- [ ] No text overflow from longer Arabic strings
- [ ] Numbers, prices, ratings display correctly in RTL
- [ ] Camera viewfinder does NOT flip
- [ ] Only directional icons flip
- [ ] Mixed Arabic/English text renders correctly

---

## 7. Agent Team Architecture

### Team Composition
4 Opus agents with cross-QA:
- **Backend Agent** — i18n setup, theme system, API wiring, storage migration
- **Frontend Agent** — All 10 screens, design system components, animations
- **Test Agent** — Unit tests, RTL tests, i18n tests, navigation tests (80%+ coverage)
- **QA Agent** — Cross-review all work, RTL verification, performance audit, bug filing

### Phase 1: Foundation (Backend + Frontend parallel)

**Backend Agent:**
- i18n infrastructure: expo-localization, i18next, react-i18next
- Create `src/i18n/index.ts`, `en.json`, `ar.json` (~200 keys)
- Language persistence + `I18nManager` RTL toggling
- Rename storage keys: `@smartcompare_*` → `@qaren_*`
- Region selection in user preferences
- Shared theme file: `src/theme/index.ts` (all design tokens)

**Frontend Agent:**
- Install: expo-image, react-native-reanimated, lucide-react-native, expo-haptics
- Load Inter + Cairo fonts via expo-font
- Build design system components: Button, Card, Chip, SkeletonLoader, ProgressBar, IconButton

**Test Agent:**
- Write test shells for all 10 screens (red tests)
- RTL test utilities
- i18n test utilities

### Phase 2: Screens (all agents active)

**Frontend Agent builds screens in order:**
1. SplashScreen
2. OnboardingScreen (6-step)
3. LoginScreen + RegisterScreen + ForgotPasswordScreen
4. HomeScreen (camera-first)
5. ResultsScreen (single-scroll)
6. HistoryScreen
7. ProfileScreen
8. PaywallScreen (placeholder)

**Backend Agent:**
- SSE streaming integration with new skeleton states
- 3 free comparison counter (AsyncStorage + backend events)
- Navigation wiring (React Navigation, bottom tabs)
- All existing API endpoints connected to new screens

**Test Agent:**
- Green tests as each screen delivers
- RTL snapshot tests
- i18n coverage test (no hardcoded strings)
- Navigation flow tests

### Phase 3: Polish & QA

**Frontend Agent:** Loading sequence, winner reveal, staggered entrances, language switch animation.

**QA Agent:**
- Every screen in EN + AR
- RTL layout audit
- Performance: bundle size, cold start, scroll FPS
- Edge cases: empty history, offline, expired auth, paywall trigger
- No hardcoded strings, no stale `@smartcompare_*` references
- File bugs → assign to responsible agent

### Idle Rule
Any agent waiting for QA writes red-green tests targeting 80% coverage.

### Cross-QA Before Dissolve
- Backend reviews Frontend's API integration
- Frontend reviews Backend's i18n setup
- Test reviews QA's bug reports
- QA does final full-app walkthrough in both languages

### Done Criteria (ALL must pass)
- [ ] All 10 screens render in EN and AR without layout breaks
- [ ] RTL mirroring works on all directional elements
- [ ] Camera-first home screen works (permissions, capture, identify)
- [ ] SSE streaming with skeleton → reveal animation works
- [ ] 3 free comparison counter works (tracks, shows, triggers paywall)
- [ ] All navigation flows work (onboarding, auth, main, paywall)
- [ ] No hardcoded English strings
- [ ] Bundle size < 25MB
- [ ] 80%+ test coverage on new code
- [ ] Zero console errors/warnings in both languages
