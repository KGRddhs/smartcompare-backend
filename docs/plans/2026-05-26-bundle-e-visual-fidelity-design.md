# Bundle E — Visual Fidelity Pass: Design Doc

**Status:** Approved by Ahmed in brainstorm session 2026-05-26.
**Owner:** Bundle E 4-Opus team (backend, frontend, test, qa).
**Ship vehicle:** One PR with staged device-walkthrough gates, OTA via `eas update --branch preview` once green on device.
**Reference source of truth:** `docs/claude-design-handoff/ui_kits/mobile/*.jsx` (15 files) + `docs/claude-design-handoff/screenshots/*.png` (Playwright-rendered references). Per Claude-Design handoff README, the JSX *is* the spec — read the HTML/CSS directly; screenshots are confirmation, not interpretation.

---

## 1. Goal

Take Qaren from **tokens-only fidelity** (Bundle D shipped color palette, type ramp, spacing) to **tokens + composition + motion + hero illustrations fidelity** so the device experience matches `docs/claude-design-handoff/ui_kits/mobile/*.jsx` side-by-side. ~150 testers are waiting on a TestFlight invite; Bundle E ships before the invite goes out.

## 2. Non-goals

- No new backend endpoints (the audit found all editorial endpoints — `/home/{savings,smart-pick,trending}`, `/profile/{recent-decisions,monthly-stats,priorities-weighted}` — already live).
- No new product features, no scoring/personalization changes, no auth flow redesign.
- No Lottie. Hero illustrations are SVG + Reanimated per CLAUDE.md.
- No "Arabic-as-default" reopen (dropped Session 44).
- No Apple App Store production submission gates (icon byte-identity + legal redraft remain separate). TestFlight internal is unblocked.

## 3. Scope

### 3.1 Per-screen composition gaps (15 reference screens)

| Ref `.jsx` | Current `.tsx` | Effort | Composition gaps (summary) |
|---|---|---|---|
| `HomeScreen.jsx` | `screens/HomeScreen.tsx` | L | HeaderCounter single-pill `2/3 free · +1`; SmartPickCard VS-pair PickTile + winner outline + center vs pill; QuickCategories 2×2 grid with circular icon glyph; SavingsBanner dark-inverse with concentric emerald arc + accent dot decoration; TrendingNearYou per-row category pill + center vs + count + trending arrow. |
| `ResultsScreen.jsx` | `screens/ResultsScreen.tsx` | L | TopMatchBadge eyebrow; hero ProductCard pair with absolute-centered vs pill + winner emerald outline + accentLight bg; DimensionBar two-color (secondary + emerald, 2px gap); ConfidencePill dot+label; cohort-line styled card; **DetailsAccordion** (3-section: Reviews / Pros&Cons / Specs, icon-circle + 220ms chevron rotate); feedback prompt 3-pill row; **RevealBurst** animation on winner card first mount. |
| `HistoryScreen.jsx` | `screens/HistoryScreen.tsx` | L | HeroStats marquee (horizontal scroll of MarqueeCard, mini VS pair + winner-check overlay); SearchField decorative pill; **HistoryRowV2** per-row mini-VS card (two ProductBlocks + centered vs pill + verdict line); DateGroupV2 eyebrow per "Today / Yesterday / This Week / Older"; row tap → detail (B5 unwrap fix already at `4aa9cff`). |
| `ProfileScreen.jsx` | `screens/ProfileScreen.tsx` | L | Lens header w/ Q logo + name + region + settings icon; **RecentDecisions** horizontal MiniVsCard marquee; **PrioritiesInline** card (B3 fix: human-readable labels, sum=100, "Tune my priorities" CTA); **MonthStrip** 3-tile (`27 / 240 BHD / +5`); **FlatSettings** eyebrow-grouped (Account / Privacy / Help / Danger). |
| `PaywallScreen.jsx` | `screens/PaywallScreen.tsx` | L | HeroVisual 3 staggered mini-vs pairs (center popped up w/ shadow); SocialProof avatar dots + "5,000+ GCC shoppers" + 4.8 rating pill; PlanCardLarge Yearly w/ "3 days free · Best value" eyebrow + Monthly radio; trial timeline dashed-border (Today / In 2 days / In 3 days); FeatureLine 4 rows w/ emerald-circle check; sticky CTA "Start My 3-Day Free Trial" + "No payment due now" trust line + Terms/Privacy/Restore links. |
| `ScanCameraScreen.jsx` | `screens/ScanCameraScreen.tsx` | L | Full-bleed black bg; faux camera viewfinder gradient + emerald scanline; **Reticle** 4-corner brackets (260×260); top bar: Close (X) circle + "1 of 2" glass-blur pill + Help circle; centered hint text; SlotThumb pair (filled+check + empty+plus); capture row gallery / 76px white shutter w/ inner inset / flash; sticky disabled "Snap one more to compare" until both slots filled. |
| `SplashScreen.jsx` | `screens/SplashScreen.tsx` | S | Logo + emerald accent pulse only (already close — minor polish). |
| `OnboardingWelcomeScreen.jsx` (s1) | `screens/onboarding/Step01Welcome.tsx` | M | **PhoneMockup hero SVG** centered; brand wordmark + emerald accent; "Compare anything" headline; sticky Continue CTA. |
| `OnboardingScreen.jsx` (s8 priorities) | `screens/onboarding/Step08Priorities.tsx` | M | Icon-in-circle OptionRow pattern; black-on-select active state; max 3 picks; optional warm wash bg toggle. |
| `OnboardingCohortScreen.jsx` (s12) | `screens/onboarding/Step12CohortProof.tsx` | M | **PeerLattice hero SVG** (8×12 dot grid, falloff opacity, emerald YOU-dot in center); "388 GCC shoppers helped train this" framing; 3 CohortBullet items. *(Patched 2026-05-26 per QA § 6 audit — JSX uses PeerLattice dot-grid, NOT CohortBarChart.)* |
| `OnboardingReadyScreen.jsx` (s15) | `screens/onboarding/Step15Reveal.tsx` | M | **MatchBadge primitive** (88px emerald-accentLight circle w/ "92%" inside + "✦" sparkle accent top-right) + "Strong match" eyebrow + StatBlock grid (Top priority / Budget / cohort count). Light scale-in on mount. *(Patched 2026-05-26 per QA § 6 audit — JSX uses 92% MatchBadge, NOT RevealBurst confetti. RevealBurst stays for ResultsScreen winner card only.)* |
| `OnboardingExtras.jsx` (s4, s5, s13, s17) | `screens/onboarding/Step04Country.tsx`, `Step05Trust.tsx`, `Step13Anticipation.tsx`, `Step17Notifications.tsx` | L | s4 IconRow region picker w/ flag glyph; s5 PrivacyRow w/ emerald-tint circle icon; s13 animated StageChecklist + factoid; s17 mock iOS push prompt anchor + Tag rows + "Maybe later" secondary. |
| `LoadingScreen.jsx` (s14 + comparison) | `screens/onboarding/Step14Loading.tsx` + comparison loading | L | **ConcentricVariant** (3 emerald rings expanding outward, staggered 700ms, counter 0→2,074 cohort peers); **StreamingCardsVariant** (two product-shape ghost cards, field-by-field reveal: photo → name → price → stars → top-match badge); shared StageChecklist + rotating TipCard; mode "comparison" rotates between variants, mode "onboarding" always concentric. |
| `AuthScreens.jsx` (SignIn + s16 Save Advisor) | `screens/LoginScreen.tsx`, `screens/onboarding/Step16Account.tsx` | M | SignIn: SocialRow at top + OrDivider + AuthField pair + Forgot password + sticky CTA; Save Advisor: emerald-tint check hero + headline + SocialRow + AuthField + Terms/Privacy fine print + **NO skip link**. **B4 Google sign-in fix folded in here.** |
| `EditProfileScreen.jsx`, `ShareBottomSheet.jsx`, `DemographicsBottomSheet.jsx` | `screens/EditProfileScreen.tsx`, share/demographics bottom sheets | M | Bottom-sheet primitives, edit-profile form fields, share preview card. |

Effort distribution: 7 L-tier + 6 M-tier + 1 S-tier + 1 multi-screen group. ~65% of work in L-tier screens.

### 3.2 Hero illustrations (4 SVG components — Reanimated, ZERO Lottie) + 1 primitive

Live under `SmartCompareApp/src/components/hero/`. Each owns its own Reanimated worklet — no shared global animation state. Hero count revised from 5 → 4 after QA § 6 audit dropped CohortBarChart (no JSX consumer). MatchBadge is a primitive (composed inline, lives under `src/components/primitives/`), not a hero.

| Component | Used in | Anatomy (from `.jsx` references) | Motion |
|---|---|---|---|
| **PhoneMockup** | *No JSX consumer in current spec.* Kept as available primitive for Step03ValueProp (no JSX ref exists for s3) per frontend lane's discretion. Otherwise deletable. | Stylized iOS-shape SVG outline w/ Qaren wordmark inside, emerald accent dot bottom-right. ~180×280px. | Subtle 0.95→1.0 scale-in on mount (320ms cubic-bezier); idle. |
| **ConcentricMotif** | LoadingScreen ConcentricVariant + Step05Trust (per JSX) | 3 emerald rings expanding outward from Q logo center, staggered 700ms, looping 2.1s. | `qarenRing` keyframe: `scale(0.8)` opacity `0.9` → `scale(2.5)` opacity `0`. |
| **PeerLattice** *(NEW per QA § 6 audit 2026-05-26)* | Step12CohortProof | 8×12 dot grid; YOU-dot in center emerald-accent w/ subtle glow ring; surrounding peers fall off in opacity radially. Optional micro-shimmer on the YOU-dot. | Stagger fade-in of dots from center outward over 600ms (cubic-bezier 0.32,0.72,0,1); YOU-dot scales 0→1.0 with subtle spring. |
| **LoadingRings** | Step14Loading (theatrical loader), also reused by LoadingScreen ConcentricVariant | Same 3-ring expanding motif + counter chip "N cohort peers refining your match" with 0→2,074 ease-out-cubic tick over 2.4s. | Counter `requestAnimationFrame` driven; ring keyframes via `Animated.loop(withTiming, -1)`. |
| **RevealBurst** | **ResultsScreen winner card first appearance ONLY** *(patched 2026-05-26 — Step15 dropped, JSX uses MatchBadge instead)* | 6–8 emerald confetti particles emit from center, parabolic fall, fade-out. Center holds an emerald-tint check or top-match badge that scale-bounces (0→1.1→1.0). | Particle: `withSequence(withTiming(x, 600ms), withTiming(y+50, 800ms))` + fade; Badge: `withSpring({ damping: 8, stiffness: 100 })`. Fires once on mount per `key=comparison_id` (resets on new comparison). |
| **MatchBadge** *(primitive, not hero)* | Step15Reveal | 88px circle w/ emerald-accentLight bg + emerald-accentDark `92%` text + "✦" sparkle accent top-right + "Strong match" eyebrow above. | Count-up tween on % (0→target over 1.2s, ease-out-cubic); circle 0.9→1.0 scale-in on mount; sparkle gentle pulse opacity 0.6→1.0→0.6 (2s loop). |

**Dropped:** `CohortBarChart` (Bundle D heritage, no JSX consumer in current spec). If `illustrations/CohortBarChart.tsx` already exists post-`git mv`, frontend should DELETE it from `hero/` (or move to `admin/` if Ahmed wants it for an internal dashboard later — out of scope for Bundle E).

### 3.3 Motion infrastructure

Lives in `SmartCompareApp/src/theme/motion.ts` (already exists for Bundle D); Bundle E extends with:

- `motion.screenTransition` — 320ms cubic-bezier(0.32, 0.72, 0, 1), RTL-mirrored (`translateX: ±width → 0`). Wrap each onboarding step in `<Animated.View>` keyed on `step`.
- `motion.accordionChevron` — 220ms ease for `transform: [{ rotate: '180deg' }]` on `<DetailsAccordion>` sections.
- `motion.ctaGlow` — 240ms ease for emerald `shadowColor` + `shadowRadius` on the Compare CTA when both inputs valid.
- `motion.modeSegment` — 180ms cubic-bezier(0.32, 0.72, 0, 1) for ModeSegment active-pill slide (HomeScreen segmented mode rail).
- `motion.shimmer` — 1.4s linear loop on skeleton placeholders (LoadingScreen StreamingCardsVariant).
- `motion.counterTick` — 2.4s ease-out-cubic for cohort peer counter (LoadingRings).
- `motion.revealBurst` — 1.2s total (particles 600ms emit + 800ms fall + 400ms fade; badge spring damping 8 stiffness 100).
- Haptic vocabulary stays at `{chip:light, stage:light, winner:medium}`. **NO error/warning/heavy.** Build Principle #4.

### 3.4 B3 fold-in (Profile priorities-weighted)

Two backend + frontend bugs:

- **Backend** `app/api/profile_routes.py::_normalize_weights_to_100` — current divides by max, must divide by sum. Spec § 4g: priorities are RELATIVE, three bars must SUM to 100 (largest-remainder method).
- **Frontend** `src/components/ProfileEditorialSections.tsx::PrioritiesInline` — i18n keys `priorities.<enum>` missing for `ease_of_use`, `durable`, `features`, `eco`, `brand`, etc. Render falls back to raw snake_case key. Need 8 i18n keys × 2 locales (16 strings) under `priorities.*` in `src/i18n/en.json` + `ar.json`.

Path A R2 already shipped the priorities sum=100 backend fix (`4aa9cff`). Frontend i18n keys + label rendering remain; verify on device once Bundle E ships.

### 3.5 B4 fold-in (Google Sign-In)

**Status entering Bundle E:** Apple ✓, email/password ✓, Google ✗ (Path A R1 dropped nonce per Bundle D Phase 3 fix `bb78b6b`, but failure persists).

**Diagnostic-first sequence:**

1. Ahmed captures `[GOOGLE-DIAG]` Xcode console line from EAS preview build (token length, parts count, head).
2. Backend lane queries Railway logs for the corresponding `[SOCIAL_LOGIN_TRACE] provider=google token_segs=N` line at the same timestamp. **Pre-flight: zero `SOCIAL_LOGIN_TRACE provider=google` log entries exist in the last 7 days** — the FE-side fetch never reached `/auth/social-login` in any prior attempt. This narrows the failure mode.

**Failure-mode triangulation matrix:**

| Xcode says | Railway says | Diagnosis | Fix |
|---|---|---|---|
| `token length: 0` OR `parts: 0` | nothing | Native SDK threw — `signInResult.data?.idToken` is null | Audit `app.json` → `expo-google-sign-in` plugin config for `iosClientId`; check Supabase dashboard → Authentication → Providers → Google → `iOS Client ID` field. |
| `token length: ~1000` `parts: 3` (valid JWT) | nothing | FE sent fetch but backend didn't receive | Network/cert-pin issue. Check `certificatePinning.ts` for Railway SPKI pin; also confirm `API_BASE_URL` resolves to web-production-58776 from device. |
| `parts: 3` | `token_segs=3` followed by Supabase rejection | aud claim mismatch | Confirm `iosClientId` in Supabase dashboard matches the one in `app.json`. Audit returns "invalid issuer" or "audience mismatch" error code from Supabase. |
| `parts: 3` | `token_segs=3` followed by Supabase "Nonces mismatch" | Path A nonce drop didn't take effect on phone | Confirm phone is on Path A R1 build (`bb78b6b` or later). Re-deploy `eas update --branch preview`. |

**Acceptance:** Google sign-in lands a user into Home tab. Tested on Ahmed's iPhone via EAS preview.

## 4. Approach — One PR with staged device-walkthrough gates

| Stage | What lands | Acceptance gate |
|---|---|---|
| **S0 — Foundation** | 5 hero SVG components + motion.ts extensions + shared primitives (TwoInputShell vs-pair, DetailsAccordion shell, IconRow / OptionRow, MarqueeCard, MiniVsCard, ProductBlock, ConfidencePill, DimensionBar) | tsc 0 + Jest baseline (1011+ existing PASS) + agent self-verification on iOS simulator; **no device walkthrough yet** (no user-visible screen changes). |
| **S1 — Tab surfaces** | Home + Results + History + Profile + Paywall + Scan + SignIn + Save Advisor wired against primitives. B4 Google fix lands here. B3 priorities-weighted i18n + sum=100 lands here. | Ahmed runs EAS preview on device; walks all 8 screens; signs off each with screenshot match against Claude-Design `.jsx` render. RED on any mismatch → rework cycle. |
| **S2 — Onboarding polish** | 18 onboarding step components (Step01–Step17) wired against hero SVGs + LoadingScreen variants A/B + theatrical Step 14. | Ahmed runs onboarding end-to-end on device fresh-install (or via dev-reset); walks all 17 steps + final loading; signs off transitions + RTL mirror works. |
| **S3 — Polish + ship** | EditProfile + ShareBottomSheet + DemographicsBottomSheet + Splash polish + any RED found in S1/S2 swept. Pre-deploy smoke (curl smoke pack from `tests/test_security_regression.py` + manual happy-path comparison). | `tsc 0` + Jest PASS + `expo-doctor` clean + Ahmed approves device walkthrough; OTA fires `eas update --branch preview`; sweep test pool. |

Each stage gates the next. NO advance until Ahmed's device-walkthrough sign-off — agent self-verification is necessary but not sufficient per Bundle D Phase 3 lesson (`feedback_agent_signoff_vs_device_walkthrough.md`).

## 5. Team protocol (Ahmed's rules, 2026-05-26)

1. **All Opus.** No Sonnet/Haiku in the 4-Opus team.
2. **Features 100% complete before disassembly.** A lane cannot signal "done" while any task in its scope is RED, untested, or unverified by another lane.
3. **Mandatory cross-QA.** Before disassembly each member QAs another's work. Pairings:
   - frontend QA's backend's B3 + B4 work
   - backend QA's frontend's primitive contracts
   - test QA's both frontend and backend
   - qa lane QA's everyone (final sign-off)
4. **Subpar / missed → send back.** No grade-inflated "good enough" sign-offs. RED feedback returns to the owning lane with a specific delta.
5. **Idle members write tests.** While waiting for QA return, idle members write red/green tests targeting 80% coverage of the new feature OR review another lane's pre-merge diffs.
6. **Path-restricted commits.** `git commit -m "msg" -- <paths>` (paths after `--`), NOT `git commit -- <paths> -m "msg"`. Discipline locked from `feedback_git_staging_in_team.md`.
7. **Worktree subagents have network sandbox limits** — pre-fetch data and embed in prompts. See `feedback_worktree_subagent_sandbox.md`.

## 6. Acceptance gates — per-screen checkpoints

Each L/M-tier screen ships with **2–4 visual checkpoints** the agent must declare hold post-merge, AND that Ahmed verifies on device. Below are the checkpoints, lifted from the `.jsx` references:

### HomeScreen (`HomeScreen.jsx`)
- [ ] HeaderCounter renders `2/3 free · +1` single pill, emerald-accentLight bg when `free=1`, plain bg otherwise. Tap → Paywall.
- [ ] SmartPickCard shows two product PickTile (gray + dark winner outline) with center absolute-positioned emerald "vs" pill, winner has emerald check overlay top-right.
- [ ] QuickCategories renders 2×2 grid, each tile has a 28px circular icon glyph (left-aligned) + label.
- [ ] SavingsBanner is dark-inverse (`#0A0A0B`) with concentric emerald arc decoration top-right and an accent dot.
- [ ] TrendingNearYou rows show category pill + center "vs" + product names + tail count "142 ↗" with trending arrow.

### ResultsScreen (`ResultsScreen.jsx`)
- [ ] TopMatchBadge eyebrow renders at top center with emerald star + "TOP MATCH" uppercase.
- [ ] Hero ProductCard pair side-by-side, winner has emerald 2px outline + accentLight bg, center vs pill absolute-positioned.
- [ ] DimensionBar shows two-color bar (secondary text-color left, emerald right, 2px gap in middle).
- [ ] DetailsAccordion has 3 sections (Reviews / Pros&Cons / Specs) with icon-circle + 220ms chevron rotate on expand.
- [ ] RevealBurst fires ONCE on winner card first mount (not on re-render). Particle animation + badge scale-bounce both complete in 1.2s.

### HistoryScreen (`HistoryScreen.jsx`)
- [ ] HeroStats marquee shows horizontal-scroll mini VS cards above the date-grouped list. Stat strip "27 decisions this month · 240 BHD shopped smarter" below.
- [ ] HistoryRowV2 per-row card: two ProductBlocks + centered emerald vs pill + verdict line below.
- [ ] Winner's ProductBlock has emerald 2px outline + accentLight bg + "TOP MATCH" eyebrow.
- [ ] Row tap → ResultsScreen with the same `comparison_id` (B5 unwrap fix verified end-to-end).

### ProfileScreen (`ProfileScreen.jsx`)
- [ ] Lens header: Q logo + name + region subtitle + settings icon button.
- [ ] RecentDecisions: horizontal marquee of 3 MiniVsCard items with "See all" link at right.
- [ ] PrioritiesInline (B3): 3 human-readable bars (Quality / Price / Durability) summing to 100%, "Tune my priorities" CTA below.
- [ ] MonthStrip: 3-tile (27 / 240 BHD / +5) — middle tile has emerald-dark color on the number.
- [ ] FlatSettings: eyebrow-grouped sections (ACCOUNT / PRIVACY & NOTIFICATIONS / HELP / DANGER ZONE), Delete account in destructive red.

### PaywallScreen (`PaywallScreen.jsx`)
- [ ] HeroVisual: 3 staggered mini-vs pairs, middle one popped up 6px with shadow.
- [ ] SocialProof: 5 avatar dots overlapping + "Trusted by 5,000+ GCC shoppers" + 4.8 rating pill.
- [ ] PlanCardLarge Yearly: "3 days free · Best value" emerald eyebrow ribbon, radio selected.
- [ ] Sticky CTA "Start My 3-Day Free Trial" + "No payment due now · Cancel anytime" trust line w/ emerald check icon + Terms/Privacy/Restore links.

### ScanCameraScreen (`ScanCameraScreen.jsx`)
- [ ] Full-bleed black bg with radial gradient camera-feed sim + thin emerald scanline at vertical center.
- [ ] Reticle: 4 corner brackets at 260×260px centered, each 28×28px with 3px white border, inner radius rounded.
- [ ] Top bar: Close X circle (left) + "1 of 2" glass-blur pill (center) + Help circle (right). All glass-blur (`rgba(255,255,255,0.15)` + `backdrop-filter: blur(12px)`).
- [ ] Capture row: gallery 48px circle (left) + 76px white shutter w/ inner 2px black inset (center) + flash 48px circle (right).
- [ ] SlotThumb pair below reticle: filled has product placeholder + emerald check overlay; empty has + icon.

### LoadingScreen (`LoadingScreen.jsx`)
- [ ] ConcentricVariant: 3 emerald rings expanding outward from QarenLogo center, staggered 700ms.
- [ ] Counter chip below logo: ticks 0 → 2,074 over 2.4s with ease-out-cubic, formatted with thousands separator.
- [ ] StageChecklist: 5-item list with pending → active (pulsing dot) → done (emerald check) transitions, ticks every 900ms.
- [ ] TipCard rotates between 4 factoids every 3.2s with crossfade.
- [ ] Comparison mode rotates between concentric and streaming on mount; onboarding mode always concentric.

### AuthScreens (`AuthScreens.jsx`)
- [ ] SignIn: SocialRow (Apple / Google / Email) at top + OrDivider + email + password AuthField + Forgot password right-aligned link + sticky black "Sign in" CTA.
- [ ] Save Advisor: emerald-tint check hero centered + "Save your advisor." headline + "So your match travels with you." subtitle + SocialRow + email AuthField + Terms/Privacy fine print + sticky black "Save my advisor" CTA. **NO skip link.**
- [ ] **B4 Google sign-in works** — taps "Continue with Google" on EAS preview, gets routed into Home tab.

### Onboarding screens (Step01–Step17)
- [ ] Each step renders the matching `.jsx` reference's composition + hero illustration.
- [ ] Slide transitions between steps: 320ms cubic-bezier, RTL-mirrored.
- [ ] Step 14 theatrical loading: 3.2s minimum display + ConcentricVariant + cohort peer counter.
- [ ] Step 15 reveal: RevealBurst on mount.
- [ ] Step 16 forced sign-in (no skip link).

## 7. Risks + mitigations

| Risk | Mitigation |
|---|---|
| Bundle D Phase 3 surfaced 13 bugs/gaps after "11 screens integrated" sign-off | Bundle E uses device-walkthrough gates per stage. Frontend cannot mark "done" without Ahmed's screenshot match. |
| Hero SVG illustrations land late and block screen composition | Foundation stage S0 ships heroes FIRST. Composition stage S1 cannot start until S0 green. |
| Reanimated worklets fight RTL mirror | Test agent writes `useReducedMotion()` + RTL-mirror snapshot tests at S0. |
| Google sign-in B4 still broken at S1 sign-off | If Xcode + Railway lines don't disambiguate, post the diagnostic data in this thread; Bundle E ships Apple + email only, B4 follows as targeted hotfix. Apple covers most iOS testers. |
| Path A R2 fixes (Scan chip, history detail unwrap) not yet on phone | Bundle E first OTA fires those fixes in addition to E itself. Verify both work in S3 device walkthrough. |
| Backend SOCIAL_LOGIN_TRACE log shows zero entries for past 7 days | Confirms FE never sent the request — fix is in `signInWithGoogle` BEFORE the fetch (likely `signInResult.data?.idToken` is null). Aligns with audit matrix row 1 in § 3.5. |

## 8. Out-of-scope follow-ups (NOT Bundle E)

- App icon ICN-0001 byte-identity fix (still needed for App Store production submission, not TestFlight internal).
- Legal-doc Qaren-jurisdiction redraft (15 decisions per `2026-05-16-tos-decisions-pending.md`).
- Bonus expiry push (Migration 018 + cron — gated by `ENABLE_BONUS_EXPIRY_PUSHES` env).
- Re-engagement push canary ramp.
- HomeScreen variant integration tests re-mock (pre-existing RED suites from Bundle B per MEMORY.md).
- v1.1 backlog from Bundle C (B.0 kwarg refactor, A.8.1 dim builder adapter, etc.).

## 9. Definition of done

- All 15 reference screens have agent-self-verified composition matches AND Ahmed-device-walkthrough screenshot matches.
- 5 hero SVG components live under `src/components/hero/` + Reanimated worklets, ZERO Lottie.
- B3 priorities-weighted bug fixed (sum=100 + i18n keys).
- B4 Google sign-in either works on EAS preview OR diagnostic posted + clear next-step (acceptable for ship-as-is if Apple + email work).
- `npx tsc --noEmit` exits 0.
- Jest baseline holds — 1011+ existing PASS, 0 new RED. New tests at 80%+ coverage per Ahmed's idle-member rule.
- `expo-doctor` clean.
- `pip-audit -r requirements.txt --strict` + `npm audit --audit-level=high` clean.
- Sentry watch through T+~120 min post-OTA, no new `TypeError` / `RangeError` / `ReferenceError` patterns.
- All four lanes have signed off another lane's work via cross-QA.
- Bundle E PR merged to `main`, `eas update --branch preview` fired, Ahmed confirms on device.

---

**Approval:** Ahmed, in this brainstorm thread, 2026-05-26.
**Next:** writing-plans skill to produce the executable per-lane task plan at `docs/plans/bundle-e-visual-fidelity.md`.
