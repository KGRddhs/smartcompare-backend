# Bundle E S2 Prep — onboarding step composition deltas

**Owner:** frontend
**Status:** prep / scratch, NO commit to step code yet (waiting on S1 device walkthrough sign-off)
**Trigger:** team-lead message during S1 OTA window (update_id `019e6629-efd9-7d5d-b5a6-e83176380970`, 2026-05-26)

Per-Step deltas captured by reading each `Step*.tsx` against its matching JSX reference. Each entry calls out **what needs rework** in S2 composition. Effort estimates are rough; final scope locks at S2 KICKOFF.

---

## Step01Welcome — `OnboardingWelcomeScreen.jsx`

**Current:** logo badge + headline + subtitle + Continue + sign-in link.
**JSX (per F-S0.0 doc-fix `75e78f5`):** Warm-wash radial-gradient bg + QarenLogo 40px + headline + subtitle + **3 QuoteRow testimonial cards** + Continue + sign-in.

**Rework:**
- [ ] Add warm-wash radial-gradient background (orange + blue corner tints) — RN approximation via two overlapping `LinearGradient` views or absolutely-positioned tinted blurs since RN has no native CSS radial-gradient.
- [ ] Compose `<QuoteRow quote=... author=... />` trio from `src/components/primitives/QuoteRow.tsx` (shipped F-S0.3 at `b2fe300`). Three sample quotes: "Picked Galaxy — camera + battery edged out Apple here", "Picked La Roche — matched my sensitive-skin tag", "Picked Centrum — better nutrient profile" (lift verbatim from JSX:46-48).
- [ ] Swap the giant Q-logo-badge for the same `QarenLogo size={40}` used elsewhere (currently a 96px black square with QaranIcon — JSX has a much smaller, less-anchored brand mark).

**Effort:** **M** (warm-wash bg is the most fiddly part; trio + logo swap are tokens-only).

---

## Step03ValueProp — no JSX reference (your-own anatomy)

**Current:** PhoneMockup hero illustration + headline + subtitle + Continue.
**Spec:** PhoneMockup hero (already wired, refined for Bundle E at `e977de4`). No JSX reference exists per design doc § 3.1.

**Rework:** **S** (already complete; verify on device walkthrough only).

---

## Step04Country — `OnboardingExtras.jsx` s4 ("Where do you shop?")

**Current:** 6 GCC flag cards via `TouchableOpacity` + `selected` border state; conditional governorate dropdown when `country===BH`.
**JSX:** OnbHeader (back arrow + 28% progress bar) + OnbHeadline ("Where do you `shop`?" + sub) + 6 `IconRow` (icon-circle + label + sub) + sticky OnbCTA.

**Rework:**
- [ ] Replace bespoke country cards with `<OptionRow style="icon-circle" />` from `src/components/primitives/OptionRow.tsx`. icon=flag emoji, sub-line (e.g. "Capital, Muharraq, Northern, Southern" for BH).
- [ ] Headline must use `accentWord`-style emerald color on "shop" (per `OnbHeadline:62-81`).
- [ ] Progress bar at 28% (current Step04 doesn't show a per-step progress bar; OnboardingFlow wraps with a shared chrome).
- [ ] Subtitle: "Currency, retailers, and peer cohort all calibrate to your region."
- [ ] Conditional governorate dropdown still required for BH (cohort_priors.json depends on exact-case `Capital`/`Muharraq`/`Northern`/`Southern` — keep verbatim per B-XQA #2 reminder).

**Effort:** **M** (OptionRow swap straightforward; emerald-accentWord headline requires nested Text spans).

---

## Step05Trust — `OnboardingExtras.jsx` s5 ("Your data, your call.")

**Current:** title + subtitle + ConcentricMotif hero + 3 trust statements.
**JSX:** OnbHeader (36% progress) + OnbHeadline ("Your data, your `call`." + sub) + 3× `<PrivacyRow icon={...} head={...} body={...} />` + sticky "I'm in" OnbCTA.

**Rework:**
- [ ] Drop ConcentricMotif hero — JSX doesn't render it here (it's used on Step03 + Step13 + LoadingScreen ConcentricVariant per design doc § 3.2).
- [ ] Wire 3 PrivacyRows as primitives — each = 36px emerald-tint icon circle + head/body pair. The icons: check (use), search (anonymized), X (never share).
- [ ] CTA label: "I'm in" (not "Continue").

**Effort:** **M** — needs a new `PrivacyRow` primitive at `src/components/primitives/PrivacyRow.tsx` OR composed inline since no test scaffold exists for it yet.

---

## Step08Priorities — `OnboardingScreen.jsx` s8

**Current:** 8 chip-style buttons, max 3 selected, no icon glyph.
**JSX (assumed per design doc § 3.1):** Icon-in-circle OptionRow pattern, max 3, black-on-select active state, optional warm-wash bg toggle.

**Rework:**
- [ ] Swap chip layout → `<OptionRow style="icon-circle" />` primitive. icon = priority-specific glyph (sparkle for quality, $ for price, etc.).
- [ ] Keep MAX_SELECTIONS=3 and the silent-cap behavior (don't add user-facing error).
- [ ] B-XQA #2 reminder: `option.key` must use the exact 8 canonical strings (`price`, `quality`, `brand_reputation`, `durability`, `latest_features`, `ease_of_use`, `eco_friendly`, `health_safety`) for cohort_priors.json match.

**Effort:** **M** — primitive swap + per-priority icon mapping.

---

## Step12CohortProof — `OnboardingCohortScreen.jsx`

**Current:** PeerLattice hero + title + 3 staggered bullets (wired in F-S0.1c `333f117`).
**JSX:** PeerLattice + 3 `CohortBullet` (with emerald-tint check circle) + OnbCTA.

**Rework:**
- [ ] Swap inline `<Animated.Text>` bullets → `<CohortBullet icon="check" text=... />` primitive from `src/components/primitives/CohortBullet.tsx` (shipped F-S0.3). Stagger animation can wrap the CohortBullet via `<Animated.View>`.

**Effort:** **S** — primitive swap, ~10-line edit.

---

## Step13Anticipation — `OnboardingExtras.jsx` s13 (animated build-out)

**Current:** ConcentricMotif + title + Continue.
**JSX:** OnbHeader (88% progress) + OnbHeadline ("Building your `advisor`…" + sub) + 4-item StageChecklist (with done/active/pending state + pulse animation on active) + "Did you know — 73% of Capital shoppers your age prioritize Quality first." factoid + OnbCTA "Almost there…" (disabled until items complete).

**Rework:**
- [ ] Replace ConcentricMotif with StageChecklist composition. 4 items: "Locking your region", "Mapping your priorities", "Matching to N peers in {governorate}", "Calibrating your advisor". Each row has 22px circle (done = emerald solid + check, active = accentLight + 8px pulse dot, pending = white + border).
- [ ] Factoid line at bottom of card (centered, 13/400 secondary).
- [ ] CTA disabled until tick reaches items.length+1, label "Almost there…" pre-completion, "Continue" after.

**Effort:** **L** — StageChecklist is bespoke; either build inline OR create a new `StageChecklist` primitive (test lane scaffold may already exist — check `__tests__/components/StageChecklist.test.tsx`). The pulse animation can use existing motion tokens.

---

## Step14Loading — `LoadingScreen.jsx` (onboarding mode)

**Current:** LoadingRings hero + ProgressBar + CounterTicker.
**JSX:** ConcentricVariant (LoadingRings + StageChecklist + TipCard rotator) vs StreamingCardsVariant (two product-shape ghost cards w/ shimmer overlay). Mode `comparison` rotates between variants on mount; mode `onboarding` always concentric.

**Rework:**
- [ ] Wire to `LoadingScreenVariants.tsx` stub shipped at F-S0.5 — flesh out the StageChecklist + TipCard rotator inside ConcentricVariant.
- [ ] Step14 sets `mode="onboarding"` so it always renders concentric, never streaming.
- [ ] StageChecklist content: same 4-stage list as Step13 (region / priorities / peers / calibrate) OR a different "fetching" copy set — TBD pending JSX line-by-line read.
- [ ] 3.2s minimum display floor (already in stub).

**Effort:** **L** — biggest S2 task. StreamingCardsVariant is net-new + LoadingScreenVariants stub needs full impl.

---

## Step15Reveal — `OnboardingReadyScreen.jsx`

**Current:** RevealBurst illustration #5 + 4 stat cards in 2x2 grid + black CTA.
**JSX (per QA § 6 audit `7676875`):** **MatchBadge primitive** (88px emerald-accentLight circle w/ "92%" + ✦ sparkle + "Strong match" eyebrow) + "Your shopping advisor is ready." headline + sub + **4 StatBlock** in 2x2 grid (Top priority / Budget tier / Peers in Capital / GCC cohort) + "Compare your first product" CTA.

**Rework — CRITICAL:**
- [ ] **Drop the `import { RevealBurst }`** — Step15 no longer uses it per QA audit. RevealBurst is now ResultsScreen-only (wired at F-S1.8 `0fab1ed`).
- [ ] Compose `<MatchBadge percent={profile.matchQuality} eyebrow="Strong match" />` from `src/components/primitives/MatchBadge.tsx` (shipped F-S0.3 at `b2fe300`).
- [ ] Replace existing stat-card layout with 4× `<StatBlock label=... value=... />` from `src/components/primitives/StatBlock.tsx`. Layout: 2×2 grid via two flex rows w/ gap.
- [ ] CTA label: "Compare your first product".

**Effort:** **M** — both primitives (MatchBadge + StatBlock) already exist; mostly wiring.

---

## Step17Notifications — `OnboardingExtras.jsx` s17

**Current:** existing implementation (Bundle D Phase 2 polish).
**JSX:** OnbHeader (96% progress) + mock iOS push prompt card (QarenLogo + "Qaren · now" + sample notification text) + OnbHeadline ("One helpful nudge `per week`." + sub) + 3 `<Tag head body />` rows + "Allow notifications" black CTA + "Maybe later" secondary.

**Rework:**
- [ ] Verify mock iOS push prompt anchor renders (current may already have this).
- [ ] 3 `Tag` rows for "Decision insights" / "Cohort echoes" / "Smart shortcuts" — small new primitive OR inline.
- [ ] "Maybe later" secondary CTA must exist below the primary "Allow notifications" — both wire to onDone (with the appropriate notification permission flow).

**Effort:** **S** — design doc § 3.1 said "already close per Bundle D"; spot-check during S2 walkthrough.

---

## Summary by effort tier

- **L (Large):** Step13Anticipation, Step14Loading
- **M (Medium):** Step01Welcome, Step04Country, Step05Trust, Step08Priorities, Step15Reveal
- **S (Small):** Step03ValueProp (already done), Step12CohortProof (~10 LOC swap), Step17Notifications (spot-check)

**Estimated total S2 effort:** ~2-3 days of frontend chain-through, similar throughput to S1. The two L-tier (Step13 + Step14) eat the bulk; the M-tier are mostly primitive swaps using S0.3 components I already built.

## Open questions for S2 KICKOFF

1. **PrivacyRow primitive:** ship as a new shared primitive at `src/components/primitives/PrivacyRow.tsx`, OR inline only in Step05Trust? Lean toward primitive since it could be reused on Settings privacy screen.
2. **StageChecklist primitive:** does test lane have a scaffold (`__tests__/components/StageChecklist.test.tsx`) that locks the API? Check before building.
3. **Warm-wash background:** RN approximation strategy — `LinearGradient` from `expo-linear-gradient` OR positioned tinted views? `expo-linear-gradient` is already a dep; check if it supports radial (no — only linear). May need to use 2 overlapping linear gradients OR Skia for true radial.
4. **TipCard rotator (Step14):** existing `LoadingTipsCarousel.tsx` may be the right primitive — verify before building net-new.

## Dependencies on other lanes for S2

- **Backend:** none — S2 is purely composition + animation (no new endpoints required).
- **Test lane:** will likely scaffold per-Step integration tests for S2 (continuing T-S1.3b-h pattern). Heads-up sent.
- **QA:** Q-S2 gate (#16) covers LTR+RTL simulator traversal + Ahmed fresh-install walkthrough.

## What's NOT in scope for S2

- F-S1.4 HomeScreen HeaderCounter pill rebuild (Bundle D-era; was deferred to S3 polish if device walkthrough surfaces deltas)
- Per `bundle-e-visual-fidelity.md` § Frontend lane S3, the EditProfile + ShareBottomSheet + DemographicsBottomSheet + Splash refresh are S3, not S2.

— frontend, 2026-05-26
