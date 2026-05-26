# B-XQA: Frontend Primitive ↔ Backend Endpoint Contract Audit

**Bundle:** E — Visual Fidelity Pass
**Owner:** backend lane
**Task:** #7 (B-XQA QA frontend primitive contracts)
**Inputs reviewed:**
- `SmartCompareApp/src/components/primitives/{VsPair,DetailsAccordion,MarqueeCard,OptionRow,ProductBlock}.tsx`
- `SmartCompareApp/src/services/api.ts` (commit `f17799f` type migration — HomeTrendingItem / HomeSmartPickItem / RecentDecisionItem)
- `app/api/home_routes.py` + `app/api/profile_routes.py` actual response shapes
- JSX reference sites: HomeScreen.jsx:438-651, HistoryScreen.jsx:250-318, ProfileScreen.jsx:122-200, ResultsScreen.jsx, OnboardingScreen.jsx (Step08)

**Verdict at a glance:** all 5 primitives are **CLEAN with notes** — no contract violations against the new B4.3a/b shapes. Two notes worth flagging for S1 wire-up (caller-side concerns, not primitive bugs).

---

## VsPair (`SmartCompareApp/src/components/primitives/VsPair.tsx`)

**Status:** CLEAN
**Consumer surfaces:** `/home/smart-pick` (SmartPickCard winner/runner_up pair), `/profile/recent-decisions` (MarqueeCard items via MiniVsCard), `/history` HistoryRowV2 (item card)
**Props contract:** `{ left: ProductBlockData, right: ProductBlockData, winner: 'left' | 'right' | null, testID? }`
**ProductBlockData:** `{ name: string, sub?: string }`

**Findings:**
- Decouples cleanly from any endpoint type — accepts the minimal `{name, sub?}` shape that all three consumer endpoints can produce. The primitive is endpoint-agnostic by design, which is correct.
- Winner state is exposed via `accessibilityState.selected` on each ProductBlock — screen readers + tests get a clean signal.
- Center VS pill is `pointerEvents="none"` over an absolute overlay — doesn't block taps on either block. Good.

**S1 caller-side notes (not primitive issues):**
- When wiring from `HomeSmartPickItem`, callers must adapt: `{name: winner_name, sub: winner_sub ?? undefined}` and `{name: runner_up_name, sub: runner_up_sub ?? undefined}`. The `?? undefined` is important because the API type is `string | null` for the sub fields, but `ProductBlockData.sub` is `string | undefined`. TypeScript will flag the `null` → `undefined` mismatch at the call site — the primitive itself is fine, the adapter sits at the caller. Confirmed at `api.ts:710-712`.
- When wiring from `RecentDecisionItem`, the API ships only `winner_name` + `runner_up_name`. `sub` will always be `undefined` for that surface (no per-product sub on the recent-decisions response). That's correct behavior — the JSX HistoryRowV2 doesn't render a sub line either.
- For the `winner: 'left' | 'right' | null` derivation: backend ships `winner_name` (HomeSmartPickItem) or `winner_name`/`runner_up_name` distinctly. Map by string match OR put `winner` first and pass `'left'`. Either works; the primitive's `null` case is the tie path (untested in production right now since tie-break always assigns 0 or 1).

---

## ProductBlock (`SmartCompareApp/src/components/primitives/ProductBlock.tsx`)

**Status:** CLEAN
**Consumer surfaces:** sub-component of VsPair, used by every VsPair callsite above. Also directly used by PaywallScreen HeroVisual + Results hero card.
**Props contract:** `{ product: ProductBlockData, winner?: boolean, showTopMatch?: boolean, testID? }`

**Findings:**
- The exported `ProductBlockData` interface (line 22) is exactly `{name: string, sub?: string}` — minimal and surface-friendly.
- `showTopMatch` is a presentation toggle (eyebrow render only when true) decoupled from `winner` styling. Callers can opt out of the eyebrow even when winner=true (e.g. for HistoryRowV2 where the eyebrow lives at the row level not the block level). Good separation.
- `numberOfLines={2}` on name and `numberOfLines={1}` on sub guard against runaway content from the API. Defensive and correct.
- Winner state styling AND a11y both flow through `accessibilityState.selected={Boolean(winner)}` — tests can assert without reaching into computed styles.

**S1 caller-side notes (not primitive issues):**
- The optional `sub?: string` cleanly handles the `winner_sub: null` / absent-data path from B4.3b. No primitive change needed when adapting.

---

## MarqueeCard (`SmartCompareApp/src/components/primitives/MarqueeCard.tsx`)

**Status:** CLEAN
**Consumer surfaces:** HistoryScreen HeroStats marquee + ProfileScreen RecentDecisions
**Props contract:** `{ items: T[], renderItem: (item: T, index: number) => React.ReactNode, testID? }` — generic over T

**Findings:**
- Generic-over-T design intentionally lets callers vary the per-card layout (MiniVsCard, StatBlock, etc.) while keeping ONE scroll behavior. This is the right primitive shape.
- `key={(item as any).key ?? index}` line 34 — type-unsafe but practical. The cast assumes the item may or may not have a `.key` field. Better pattern would be a `getItemKey?: (item: T, index: number) => string` prop, but the `as any` is contained and reads ok. **Defer as v1.1 polish.**
- `showsHorizontalScrollIndicator={false}` matches JSX (scrollbar hidden, no scroll-snap).

**S1 caller-side notes (not primitive issues):**
- When feeding `RecentDecisionsResponse.recent` directly: each item already has `comparison_id` which works as the marquee key naturally. Callers should pass a `renderItem` that maps `RecentDecisionItem → MiniVsCard props` (which itself wraps VsPair). No primitive change.

---

## DetailsAccordion (`SmartCompareApp/src/components/primitives/DetailsAccordion.tsx`)

**Status:** CLEAN
**Consumer surfaces:** ResultsScreen bottom three sections (Reviews / Pros & Cons / Specs)
**Props contract:** `{ sections: AccordionSection[], testID? }`
**AccordionSection:** `{ key: string, label: string, sub?: string, icon: string, body: React.ReactNode }`

**Findings:**
- The `body: React.ReactNode` slot keeps the primitive composition-agnostic — caller decides whether to render reviews list, pros/cons pair, or specs table. Good.
- Single-open invariant enforced via `openKey` state (line 38, toggle line 40). Opening section B collapses A automatically. Matches the JSX contract per the .tsx docstring lines 13-15.
- `accessibilityState.expanded` on the Pressable (line 53) lets screen readers + tests detect open state. Chevron rotation `transform: [{ rotate }]` (line 62) gives visual feedback. Both signals available.
- The `icon: string` prop is currently a semantic placeholder (the .tsx renders a plain `iconCircle` View at line 56 — the string value isn't actually rendered as a glyph). **This is intentional for S0 — the iconCircle exists to hold the visual circle; per-section glyph variation can be wired later if needed.** Note for ResultsScreen wire-up: pass any non-empty `icon` string; it doesn't need to be a real icon name yet.

**S1 caller-side notes (not primitive issues):**
- This primitive doesn't bind to a `/home/*` or `/profile/*` endpoint — it's wired against scoring/comparison data structures (`fact_check.reviews`, `pros_cons`, `specs.products[i].specs`). No B4.3a/b shape concern here.

---

## OptionRow (`SmartCompareApp/src/components/primitives/OptionRow.tsx`)

**Status:** CLEAN
**Consumer surfaces:** Step06Age / Step07Gender / Step08Priorities / Step09Budget / Step10BrandAttitude / Step11Attribution onboarding writes → POST `/api/v1/auth/demographics` cohort enums
**Props contract:** `{ option: OptionData, active: boolean, onToggle: (key: string) => void, style: 'icon-circle' | 'plain', testID? }`
**OptionData (file-local, line 26):** `{ key: string, label: string, icon?: string }`

**Findings:**
- The `key: string` is what gets sent back via `onToggle(key)` — caller maps `key` → cohort enum value (`"25-34"`, `"Male"`, `"top_tier"` etc.) per `cohort_priors.json` exact-case keys. Primitive is correctly enum-agnostic.
- Active state inverts background (`bg.inverse` = black) per Cal-AI pattern. Matches JSX.
- `accessibilityState.selected={active}` exposes state to screen readers + tests.
- `icon?: string` is currently semantic-only (not rendered as a glyph — the iconCircle is a plain View). Same pattern as DetailsAccordion. Future polish if per-step glyph variation matters.

**S1 caller-side notes (not primitive issues):**
- Step08Priorities is multi-select max 3. The primitive doesn't enforce max — that's caller-side. Confirmed correct: `onToggle(key)` fires every press; caller maintains the set + ignores presses beyond 3 active. Cleanly factored.
- Cohort-write `key` strings must EXACTLY match `cohort_priors.json` keys (`"25-34"` not `"25_34"`, `"Male"` not `"male"`). Reminder for S1 wire-up — not a primitive concern.

---

## Summary

| Primitive       | Status | Endpoint surface                                | Caller-side note?              |
|-----------------|--------|--------------------------------------------------|--------------------------------|
| VsPair          | CLEAN  | `/home/smart-pick`, `/profile/recent-decisions` | `null` → `undefined` for sub fields |
| ProductBlock    | CLEAN  | sub-component of VsPair + Paywall + Results     | optional sub handles null cleanly |
| MarqueeCard     | CLEAN  | HeroStats marquee + RecentDecisions             | generic-over-T scrolls correctly |
| DetailsAccordion| CLEAN  | ResultsScreen (scoring data, not editorial)     | no B4.3a/b binding             |
| OptionRow       | CLEAN  | Onboarding cohort writes                        | caller enforces max-3 multi-select |

**Two adapter-pattern notes for S1 wire-up (NOT primitive bugs):**

1. **`HomeSmartPickItem.winner_sub` / `runner_up_sub`** are `string | null` per `api.ts:710-712`, but `ProductBlockData.sub` is `string | undefined` per `ProductBlock.tsx:22-25`. TypeScript will flag `null` at the VsPair call site. Adapter at caller: `sub: smartPick.winner_sub ?? undefined`. One-liner per slot.

2. **`OptionRow.option.key` ↔ `cohort_priors.json` keys** must match exactly (case-sensitive, hyphen-vs-underscore-sensitive). Reminder lives in the qaren-cohort skill — surfacing here because OptionRow is the input pipeline for those writes.

**No deltas to send back to frontend.** Primitives are tight against the shipped backend shapes. Ready for S1 composition.

---

## Cross-reference

- Backend endpoint shapes pinned in `tests/test_endpoint_shapes_vs_jsx.py:ENDPOINT_MANIFEST` (commit `2bcbb14`).
- `HomeTrendingItem` + `HomeSmartPickItem` types: `SmartCompareApp/src/services/api.ts:690-765` (frontend commit `f17799f`).
- JSX references: `docs/claude-design-handoff/ui_kits/mobile/HomeScreen.jsx:438-651` (SmartPickCard, TrendingNearYou); `HistoryScreen.jsx:250-318` (HistoryRowV2); `ProfileScreen.jsx:122-200` (RecentDecisions, PrioritiesInline); `ResultsScreen.jsx` (DetailsAccordion 3 sections); `OnboardingScreen.jsx` s8 (Priorities OptionRow).
