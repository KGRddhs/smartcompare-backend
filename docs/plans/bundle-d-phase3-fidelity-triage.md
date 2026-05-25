# Bundle D — Phase 3 Fidelity Triage

**Filed:** 2026-05-25 (Frontend lane, post-device-walkthrough)
**Status:** No code in this commit — honest reassessment ahead of any fix.
**Branch:** `main` (Bundle D already merged @ `6ee3aa5`; further work lands as targeted fixes).

---

## Scope of this document

Ahmed ran the Phase 3 device-leg walkthrough on his iPhone via EAS preview
build + the post-merge OTA chain. Apple sign-in and email/password auth
landed GREEN after the device-leg fixes (`f6214c6` + `bb78b6b`), but the
walkthrough surfaced 6 concrete behavioral bugs and 7 visual-fidelity gaps
that this lane had previously marked ADDRESSED.

This triage:

1. Re-anchors each finding against the file/component that owns it.
2. Estimates effort in LOC + minutes.
3. Splits "ship-blocking for TestFlight internal testing" from "Bundle E
   followup" honestly.
4. Recommends a recovery sequence.

No code in this commit. After Ahmed picks the path, individual fixes land
one at a time, each its own PR-style hotfix on `main`.

---

## B-series — Concrete bugs (behavioral, observable)

| ID | Symptom | Owner file | Root-cause hypothesis | Est. LOC | Est. effort |
|----|---------|------------|------------------------|----------|-------------|
| B1 | Scan tab segmented header overlaps camera card content (only Scan mode; Link + Type render cleanly) | `SmartCompareApp/src/screens/HomeScreen.tsx` (Scan-mode `renderCenterArea` branch ~lines 380-450, `compareCard` style ~lines 700+) | Either an `absolute`-positioned camera child without an explicit `zIndex`, OR the Scan branch render returns content that escapes the segmented-control `flexDirection: 'column'` ordering. Most likely: `compareCard` has `overflow: 'hidden'` + the camera content is layered under the chip rail with no `zIndex` separation. | ~5 LOC (one `zIndex` + maybe a `position: 'relative'`) | 15 min |
| B2 | History rows render "Apple Apple iPhone 14", "Louis Vuitton Louis Vuitto…", "HealthAid HealthAid Vita…" — brand doubled | `SmartCompareApp/src/screens/HistoryScreen.tsx::formatTitle` (line ~169) + Backend `app/api/history_routes.py` HistoryItem serializer (line ~?, check `_extract_product_names`) | `product_names` from backend ALREADY contains the full brand-prefixed name (e.g. "Apple iPhone 14"); frontend reads `product_names[0]` and `[1]`. The doubled string would happen if backend now packs `{brand} {name}` AND frontend does the same join. Most likely: a recent backend serializer change added a brand prefix to names that already had brand baked in (some products store brand+model in `name`, others split). Need to inspect: do the failing rows have brand baked in product name? Fix: strip brand prefix in formatTitle if `name.toLowerCase().startsWith(brand.toLowerCase() + ' ')`. | ~6 LOC (defensive strip in formatTitle) | 20 min |
| B3 | ProfileScreen "What shapes your matches" shows snake_case enum keys + all 3 bars at 100% | `SmartCompareApp/src/components/ProfileEditorialSections.tsx::PrioritiesInline` (lines ~146-200) + Backend `app/api/profile_routes.py::profile_priorities_weighted` (`_normalize_weights_to_100`) | **Two bugs:** (a) Frontend renders `t(p.label_key, p.key)` where label_key is `priorities.<enum>` but no such i18n key exists (e.g. `priorities.ease_of_use`); i18next falls back to the raw key `ease_of_use`. (b) Backend `_normalize_weights_to_100` scales values so the MAX is 100, not so the SUM is 100. When all weights are equal (uniform fallback) every bar reads 100%. Spec § 4g says priorities are RELATIVE — should sum to 100%. | ~15 LOC: 8 i18n keys × 2 locales (16 strings) + 4-LOC backend normalize fix | 30 min |
| B4 | Google Sign-In still fails post-nonce-drop; exact error TBD from Ahmed | `SmartCompareApp/src/services/authService.ts::signInWithGoogle` (lines ~420-490) | Post-`bb78b6b` the FE sends `{ provider, id_token }` only. Three remaining failure modes: (a) `iosClientId` mismatch in Supabase Auth → Providers → Google (Supabase's audience-check uses Google's `aud` claim which is set from `iosClientId`); (b) Supabase Auth → Providers → Google project missing the iOS Bundle ID `com.qaren.app`; (c) `[GOOGLE-DIAG]` shows token shape != JWT 3-parts (token unwrap bug at `signInResult.data?.idToken`). **Diagnostic-first**: need Ahmed's `[GOOGLE-DIAG]` log line + Railway `SOCIAL_LOGIN_TRACE` line with `token_segs=N` to disambiguate. | 0 LOC code change until diagnostic data arrives | 15 min diag + ?-LOC fix |
| B5 | "This one's not loading" — v1 history row appears in list + errors on tap | `app/api/history_routes.py` GET /history handler | Migration 026 backfilled 7 of 8 v1 rows; 1 unrenderable Sony/Bose row stays v1 by design. The list endpoint SHOULD filter `schema_version=2` at the SQL layer (CLAUDE.md says "history list/get/count filter on schema_version=2 — v1 rows invisible"). Most likely: the filter exists but a specific code path (search? pagination?) bypasses it, OR the row IS v2 but its `full_response` is missing the renderable fields and crashes on tap. Need to: (a) query Supabase for the offending row's `schema_version`; (b) verify GET /history applies the filter unconditionally. | ~3 LOC (add `.eq('schema_version', 2)` if missing) | 20 min |
| B6 | Paywall never surfaces; user at 3/3 free counter with no upgrade prompt | `SmartCompareApp/src/screens/HomeScreen.tsx` (compare submit handlers) + `SmartCompareApp/src/screens/PaywallScreen.tsx` | PaywallScreen is registered as a `transparentModal` Stack.Screen (audit 2026-05-22), but the trigger logic was the silent no-op bug fixed in that audit. Recent HomeScreen handlers at lines 263/315/330/364/383/417 already call `navigation.navigate('Paywall')` on USAGE_LIMIT 429 — those work when the BACKEND rejects. But at 3/3 the FE may not even attempt the request (canCompare gate), so no 429 fires, so paywall never opens. Need an EXPLICIT path: when `canCompare=false` AND user taps Compare → `navigation.navigate('Paywall', { initialUsage })`. Also: add a "Get unlimited" entry in ProfileScreen Settings card. | ~8 LOC (one navigation.navigate call in HomeScreen submit guard + one Profile row) | 20 min |

**Total B-series effort:** ~50 LOC, ~2 hours of focused work + Ahmed-supplied diagnostic data for B4.

---

## D-series — Claude-Design fidelity gaps (visual, not behavioral)

This is the honest reassessment. Bundle D Frontend sign-off claimed "11
screens integrated + R10/R16 ADDRESSED". The token + spacing layer DID
land (`bundleD.ts`, color palette, type ramp, Geist font). The COMPOSITION
layer — hero illustrations, motion, layout-specific visual identity — did
NOT.

| ID | Gap | Claude-Design source | What shipped | What's missing | Bundle |
|----|-----|----------------------|--------------|----------------|--------|
| D1 | Hero illustrations — Onboarding | `docs/claude-design-handoff/ui_kits/mobile/Onboarding*.jsx` | None — Step01-17 render text + chips only | PhoneMockup (Step01), CohortBarChart (Step12), ConcentricMotif (Step03/05), LoadingRings (Step14), RevealBurst (Step15). Per CLAUDE.md these are "hand-coded SVG + Reanimated, ZERO Lottie" — they need to be authored as RN SVG components from scratch | Bundle E |
| D2 | Step 14 theatrical loading (3.2s min) | `OnboardingScreen.jsx` (Step14) | Step14Loading.tsx exists + the 3.2s `minDurationMs` floor is enforced, but the visual is a plain spinner | LoadingRings concentric-ring animation, cohort peer-count ticker animation, micro-copy rotation per design § 4f | Bundle E |
| D3 | RTL-mirrored slide transitions between onboarding steps | Design § 1 motion language | Orchestrator exposes `data-direction` attr on the slide wrapper, but no per-screen `Animated.View` consumes it. Steps render as instant swaps. | `motion.screenTransition` (320ms cubic-bezier, RTL-mirrored). Implementation: wrap StepContent in `Animated.View` + key on `step`, animate `translateX` from ±width to 0 on step change. | Bundle E |
| D4 | History row visual identity | `HistoryScreen.jsx` (Claude-Design) | Text-only rows with chevron + trash icon. Winner span highlight wired via commit `000dfe9` (`accentDark` color) but no per-product avatars or "vs" mini-tiles. | Per-row mini-VS card with two product placeholder tiles (gray + dark winner outline). Backend already returns `winner_index` (Backend 2.6.B.4); FE just needs the layout. | Bundle E |
| D5 | Profile "Tune my priorities" flow visual | Onboarding 5-file set rendered in edit mode | NewOnboardingHost edit-mode wiring is GREEN (commit `bb78b6b` + earlier); buttons + chips work; orchestrator clamps to steps 8-10. | The screens themselves are visually plain — the underlying Step08-10 lack the hero motifs from Claude-Design § 4d (priority-cards-as-tiles, dial visualizations) | Bundle E |
| D6 | Results "winner reveal" animation | `ResultsScreen.jsx` design § 4e | Static winner-card + Reanimated press-scale on shutter. RevealBurst animation NOT wired. | RevealBurst on first appearance of WinnerCard — emerald confetti emit + scale-bounce per design § 4e. Pre-Bundle-D this fired on `winner-card-anim` testID conditional; the post-redesign card doesn't have the animation hook. | Bundle E |
| D7 | Home editorial sections — visual richness | `HomeScreen.jsx` lines 438-651 (SmartPickCard, QuickCategories, SavingsBanner, TrendingNearYou) | All 4 sections wired to live Backend 2.5 endpoints + render text + simple chips (commit `33422b4`). Hide-gate discipline GREEN. | Visual richness: SmartPickCard VS-pair tile sizes + product avatar placeholders, SavingsBanner circular emerald accent decoration (line 583-591 in JSX), TrendingNearYou per-row "↗" trending arrow icon (text-fallback ships, but the proper TrendingUp icon needs to be from lucide). | Bundle E (LOW priority — sections functional) |

**Honest reassessment of R10 / R16 from sign-off doc:**

| Risk | Sign-off claim | Reality | Status |
|------|----------------|---------|--------|
| R10 (additive theme invariant) | "ADDRESSED — tokens live at `bundleD.ts`, legacy `theme/index.ts` unchanged" | TRUE for tokens. FALSE for composition — Claude-Design wasn't poured into screen layouts, only into the token namespace. | **R10 PARTIAL** — tokens live, composition deferred |
| R16 (Bundle B preservation framework) | "ADDRESSED — 84 PASS + 13 TODO across 2 contract files" | TRUE — contract grep-fence is GREEN. But contract verifies that Bundle B INVARIANTS (paste-split, dual-shape, paywall takeover, 8 analytics, 3-part celebration) survive — it does NOT verify Claude-Design visual fidelity. The framework was scoped correctly; the gap is in what was tested, not how. | **R16 ADDRESSED as-scoped** — visual fidelity was never in R16's scope |

The fair characterization: Bundle D shipped the **tokens + behavior contracts + content + backend integration**. Bundle D did NOT ship the **per-screen composition + motion + hero illustrations**. The sign-off doc conflated the two.

---

## Recovery proposal

### Path A — "Bundle D hotfixes" (B1-B6, ship today)

**Scope:** 6 fixes, ~50 LOC, ~2 hours work + Ahmed's B4 diagnostic data.

**Sequence:**

1. **B3 i18n keys + sum normalization** — quick win, unblocks Profile editorial
2. **B2 brand strip in History formatTitle** — defensive strip + investigation of which products have doubled brand
3. **B1 zIndex on Scan mode** — small CSS-ish fix
4. **B5 schema_version filter audit** — verify backend SQL filter applies on every code path (list + search)
5. **B6 paywall trigger** — explicit `navigate('Paywall')` in HomeScreen `canCompare=false` submit guard + ProfileScreen "Upgrade" entry
6. **B4 Google sign-in** — only after Ahmed posts `[GOOGLE-DIAG]` + Railway `SOCIAL_LOGIN_TRACE` lines

**Ship vehicle:** OTA (`eas update --branch preview`) — no native rebuild needed for B1/B2/B3/B6. B5 needs backend deploy (Railway). B4 may need Supabase dashboard change (no code).

**Verification:** tsc 0 + jest baseline (1263 PASS + 14 RED pre-existing) + Ahmed runs the 6-bug walkthrough.

### Path B — "Bundle E: Claude-Design Fidelity Pass" (D1-D7, multi-day)

**Scope:** Visual fidelity to Claude-Design handoff. Estimated 3-5 days for a 4-Opus team.

**Sub-tasks:**
- D1: Author 5 RN SVG hero illustrations + Reanimated animations (~1 day)
- D2: Step 14 LoadingRings + cohort ticker (~0.5 day)
- D3: Slide transitions infra (~0.5 day, 1 wrapper component + per-step keying)
- D4: HistoryRow mini-VS card layout (~0.5 day)
- D5: Step08-10 hero motifs in Tune flow (~1 day)
- D6: RevealBurst on Results winner card (~0.5 day)
- D7: HomeScreen editorial section visual polish (~0.5 day)

**Ship vehicle:** OTA at end. Each sub-task can ship independently if the foundation (animation lib, illustration components) lands first.

**Bundle E should also pick up:** the HomeScreen.redesign variant test re-mock work (4 pre-existing RED suites — see MEMORY.md "HomeScreen variant integration tests need re-mocking"). Total RED count post-Bundle-E should be 0.

### Path C — "Defer + ship as-is" (TestFlight internal only)

Ship the current state (`bb78b6b`) to TestFlight as the first internal tester invite. Collect feedback on the 6 B-series bugs from external eyes. Use feedback to prioritize between Bundle D hotfix vs. jumping straight to Bundle E.

---

## TestFlight ship-readiness verdict

**My honest assessment: Path A first, then TestFlight invite, then Path B.**

- **B1 (Scan tab z-index):** ship-blocking. First impression of the brand-defining feature is broken.
- **B2 (brand duplication):** ship-blocking. Looks like a content-quality bug to a tester ("they don't even know it's Apple iPhone, they wrote Apple twice").
- **B3 (snake_case + 100%):** ship-blocking. "What shapes your matches" is the trust moment — broken labels destroy it.
- **B4 (Google sign-in):** ship-acceptable. Apple + email work. Google failure is recoverable for users who have Apple ID or email.
- **B5 (v1 history row):** ship-acceptable. 1 row affecting 1 user. Backfill v2 manually via MCP as a workaround (Migration 026 leaves 1 unrenderable row intentionally).
- **B6 (paywall never shown):** ship-blocking for monetization, ship-acceptable for feedback gathering. Internal testers are not paying users; they should hit the 3/3 cap and the cap is a feedback signal even without the paywall surfacing.

**Path A fixes B1+B2+B3+B6 = ~50 minutes work + 1 OTA. B4 follows when Ahmed sends diagnostic. B5 can be a backend-only follow-up.**

After Path A lands + OTA activates, TestFlight ship is fair. Path B (visual fidelity) can run in parallel to TestFlight tester feedback.

---

## What needs Ahmed's input

1. **B4 Google sign-in:** post the `[GOOGLE-DIAG]` line from Xcode console after the next OTA + tap Google. Also send the Railway log for the corresponding `SOCIAL_LOGIN_TRACE provider=google token_segs=N` line.
2. **B2 brand duplication:** confirm whether the affected products are: (a) ALL products (suggests backend serializer change) or (b) only specific products like LV / HealthAid (suggests product-specific data shape variance).
3. **Recovery path choice:** A → B → TestFlight, or skip A and jump to B, or ship A + Path C immediately?
4. **B5:** post the `comparison_id` of the failing v1 row from history so the Backend lane can MCP-query its schema_version + decide between manual backfill vs. UI hide.

---

## Lessons for the sign-off discipline

The Bundle D Frontend sign-off doc claimed visual fidelity that wasn't
verified on device. The contract framework (R16) verifies behavioral
invariants, not pixel fidelity to Claude-Design. A future bundle that
claims Claude-Design integration MUST include device-walkthrough
screenshots as part of the sign-off package, NOT just `tsc 0 + contract
suite GREEN`.

Per MEMORY.md "feedback_docs_vs_railway_env_drift" + the audit-2026-05-22
discipline: same rule applies to design fidelity. Do not trust "shipped"
claims without device evidence. This triage doc is the device evidence
for what's actually live.

---

## Decision needed from Ahmed

> Path A (~50 min) + TestFlight invite, or jump straight to Path B (multi-day Bundle E)?

Awaiting input. No code lands until Ahmed picks.
