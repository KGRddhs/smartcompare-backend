---
name: qaren-design
description: Use this skill to generate well-branded interfaces and assets for Qaren — a mobile product-comparison app for GCC shoppers. Contains essential design guidelines, colors, type, fonts, assets, and UI kit components for prototyping mobile screens, marketing surfaces, and design explorations.
user-invocable: true
---

Read the `README.md` file within this skill, and explore the other available files. The system is laid out as:

- `README.md` — full context: product description, content fundamentals (voice/tone, banned vocabulary), visual foundations (colors, type, spacing, motion), iconography, and index of files.
- `tokens.json` — design tokens in the shape of `SmartCompareApp/src/theme/index.ts`. Consume directly if writing production code.
- `colors_and_type.css` — CSS custom properties (`--qaren-*`) and semantic type classes. Drop into any HTML artifact's `<head>`.
- `fonts/` — Geist TTFs (EN). Cairo (AR) loads from Google Fonts at runtime.
- `assets/` — Logo wordmark, app icon, reference screenshots.
- `preview/` — Per-concept specimen cards (colors, type, components, motion, voice, RTL).
- `ui_kits/mobile/` — React-in-HTML recreation of the mobile home surface, plus iOS device frame.

If creating visual artifacts (slides, mocks, throwaway prototypes, etc), copy assets out and create static HTML files for the user to view. Reach for the UI kit's `HomeScreen.jsx` as your reference for layout, spacing, and component idiom.

If working on production code, consume `tokens.json` directly and align with `AI/smartcompare/SmartCompareApp/src/theme/index.ts`. The GitHub mirror at <https://github.com/KGRddhs/smartcompare-backend> is public.

## Hard rules — never violate

1. **Primary CTA is black** (`#0A0A0B`). Emerald (`#10B981`) is a **signal color** for winner reveal, success ticks, active tab, toggle on-state, and the "vs" pill. Never use emerald as the default button color.
2. **No shake, wobble, jitter, or error bounce.** Haptics are light or medium only — never error/warning/heavy. Build Principle #4.
3. **No scary copy.** Forbidden in EN: "couldn't", "try again", "Failed to", "Error", "Oops", "Winner", "Best Pick", "We recommend", "Best for". Pattern errors as "Hold on — …" instead.
4. **RTL must work.** Use `marginInlineStart` / `marginInlineEnd` / `insetInlineStart`. Arabic uses Cairo with a 1.7/1.5 line-height multiplier and never `text-transform: uppercase`.
5. **Extend existing primitives.** The theme exports Button, Card, Chip, IconButton, TwoInputShell, ToggleRow, etc. Build with these; don't fork parallel ones.

## If invoked without other guidance

Ask the user what they want to build — a mobile screen, a marketing page, a slide deck, an icon, an animation? Ask 3–5 focused questions (target surface, dimensions, real vs. throwaway, options vs. one option) and then act as an expert designer who outputs HTML artifacts _or_ production-aligned `.tsx` components, depending on the need.
