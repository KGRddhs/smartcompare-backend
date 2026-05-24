# Qaren Mobile UI Kit

High-fidelity recreations of the Qaren mobile app's surfaces, built as plain React-in-HTML so any designer can drop them into a prototype. Tokens come from `../../tokens.json`; visual primitives come from `../../colors_and_type.css`.

## What's here

| File | What it is |
|---|---|
| `index.html` | Interactive demo — boots all five screens with a screen switcher + Tweaks panel for Cal AI-inspired options. Open this for the full experience. |
| `home.html` / `onboarding.html` / `results.html` / `profile.html` / `history.html` | Standalone per-screen mounts — used by the Design System cards. Each is self-contained (no nested iframe) so card capture works. |
| `HomeScreen.jsx` | Home surface with the three crowding fixes wired in (see below). |
| `OnboardingScreen.jsx` | "What matters most when you buy?" priorities pick. Two row styles toggleable via Tweaks (`icon-circle` / `plain`). Optional warm wash. |
| `ResultsScreen.jsx` | The payoff — top-match badge, product pair (winner outlined emerald), dimension bars, confidence pills, feedback prompt. |
| `ProfileScreen.jsx` | Avatar + Style profile card + Account / Privacy / Notifications / Support grouped rows + Log out / Delete account. |
| `HistoryScreen.jsx` | Date-grouped list (Today / Yesterday / This Week / Older). Each row shows the product pair with a top-match emerald checkmark on the winner. |
| `tweaks-panel.jsx` | Tweaks shell (host protocol + form controls). |
| `ios-frame.jsx` | Standard iOS 26 device chrome. |

## Source mapping

| This file | Mirrors |
|---|---|
| `HomeScreen.jsx` | `AI/smartcompare/SmartCompareApp/src/screens/HomeScreen.tsx` |
| Mode chips | `src/components/CategorySelector.tsx` + ad-hoc `ModeChip` from HomeScreen |
| Numeral circles + "vs" pill | `src/components/TwoInputShell.tsx` |
| Inline icons | `src/icons/{ModeIcons,UtilityIcons,QaranIcon}.tsx` |

## The three crowding fixes (from HomeScreen review)

The original HomeScreen had three things competing for the same vertical band at the bottom of the screen. The reference rebuild collapses them as follows:

| # | Was | Now |
|---|---|---|
| 1 | A `BonusCountdownCard` ("1 free comparisons available · 1 anytime") **and** a `ComparisonCounter` pill ("2 of 3 free") rendered together. | **One** counter chip in the header — `2/3 free · +1` — taps through to Paywall. The bonus is appended only when non-zero. |
| 2 | Three mode chips (Scan / Link / Type) sat above the iOS tab bar and visually fought it. | Mode chips moved **inside** the compare card as a top segmented control (black-on-active iOS segmented vibe). The tab bar is the only chrome at the bottom edge. |
| 3 | Empty white card with no products picked felt dead. | The compare card always previews the comparison structure — two outlined numeral circles **①** **②** joined by a hairline + emerald "vs" pill. In scan mode the rows become tappable "snap product" buttons; in type/link mode they become two text inputs. |

## What stays untouched (invariants)

- **Primary CTA is black** (`cta.primary`). Emerald is reserved for the "ready" glow shadow on the CTA, the "vs" pill, the active tab, the toggle on-state, and the winner card.
- **No shake / wobble / jitter.** Transitions are spring-or-cubic-bezier; errors are silent state changes with calm captions.
- **Copy passes `.copy-policy.json`** — no "Winner", "Failed", "couldn't", "try again".
- **RTL-ready.** All margins use `marginInlineStart` / `marginInlineEnd`, `insetInlineStart`. Drop `<html dir="rtl">` and the layout mirrors cleanly.

## Known gaps

- **Scan mode is not interactive.** It's a high-fidelity static preview of the empty/snap state. The full camera flow lives in `ScanCameraScreen.tsx` in the native app.
- **Comparison-shape paste detection** (the "split this into two products" magic from `TwoInputShell`) is not wired up here — that's logic, not visual. Reference the native source for behaviour.
- **Edit Profile, Paywall, Camera, Onboarding splash + first step** aren't built yet. Ask when you want them.

## Extending

1. Add a new screen file (`ResultsScreen.jsx`, `ProfileScreen.jsx`, …) next to `HomeScreen.jsx`.
2. Read tokens via `window.qarenTokens` — the loader in `index.html` populates this from `tokens.json` before mounting.
3. Use only the primitives in the existing screen file. If a primitive doesn't exist, add it back to the native source first, then mirror.
4. Register the rendered HTML as a new asset card if it's worth previewing.
