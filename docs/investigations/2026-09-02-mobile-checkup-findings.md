# Mobile app checkup + price-cluster + issue-triage — findings for later work

**Date:** 2026-09-02 · **Main at capture:** `b6ce090` (M21 W1-W4 + #98/axios merged)
**Author:** Fable session (autonomous). Two workflows ran; both were cut off by the
6:50am Asia/Bahrain session limit mid-flight. This doc preserves what survived so the
next session resumes without re-deriving.

> ⚠️ **RECONCILIATION REQUIRED BEFORE ACTING ON ANY MOBILE FINDING.** The mobile audit
> ran against **`79a4594`** (my local HEAD at launch), which was **before** the parallel
> session's **M21 waves 2-4** merged. M21 W3 (`7fb0b0d`) **rewrote `HistoryScreen.tsx`
> (637 lines changed)** and added `HistoryScreen.mobileJank.m21.test.tsx` +
> `Results.memo.m21.test.tsx`; W4 (`9b34e95`) rewrote RTL across `ProfileScreen.tsx`,
> `LoginScreen.tsx`, `HistoryScreen.tsx`, `ResultsScreen.tsx` and more. **Every finding
> whose file M21 touched must be re-verified against current `b6ce090` first — the
> line numbers below are pre-M21 and several findings may already be closed.** The
> per-finding "M21 risk" tag says which.

M21-touched files (findings against these are suspect): `HistoryScreen.tsx` (W3+W4),
`ResultsScreen.tsx` (W2+W3+W4), `ResultsContent.tsx`/`ResultsAccordion.tsx`/`ProductImage.tsx`
(W3), `HomeScreen.tsx` (W2), `api.ts` (W2), `authService.ts` (W2+W3), `usage_service.py`
(W2), `ProfileScreen.tsx` (W4), `structured_comparison_service.py` (W2+W3).
M21-UNTOUCHED (findings likely still live): `App.tsx`, `features.ts`, `LoadingScreenVariants.tsx`,
`CounterTicker.tsx`, `RevealBurst.tsx`, `PhoneMockup.tsx`, `image_routes.py`, `url_routes.py`,
`version_routes.py`, `SplashScreen.tsx`.

---

## A. MOBILE CHECKUP — 17 adversarially-VERIFIED findings

Method: 7 Fable finders (startup, bundle-size, network-contract, render-perf,
flows-triggers, perceived-latency, safe-hygiene) → adversarial verify (default REFUTE) →
synth. **35 findings reached verify; 17 survived, 0 refuted, then the limit hit** (synth
never ran; `safe-hygiene` finder + ~18 verifiers killed). No device/emulator was available,
so startup-ms / frame-rate / on-device download numbers are NOT measured — items needing a
device are tagged. Bundle bytes ARE measured (`expo export`).

**Measured:** total JS bundle **8.2 MB / 3,826 modules** (`npx expo export --platform ios`).
Live prod compare latency observed **24.5-31.5s** cold (desktop network, not device).

### P1 — verified
1. **Camera compare `/image/identify` is unmetered for authenticated users — freemium-cap bypass.**
   `app/api/image_routes.py:63-110`. Only gate is `if anon_usage_gate_enabled() and not user:`
   (line 89, flag default OFF); no `consume_comparison_credit` / `record_lifetime_comparison`
   anywhere, while text compares consume atomically (`text_routes.py:193,355,506`). A signed-in
   free user past all daily/monthly/lifetime caps runs unlimited full Vision+OpenAI+Serper
   compares through the camera, no counter moves. History IS saved (metering-only, unlike URL).
   **M21 risk: LOW** — `image_routes.py` untouched by M21 (W2 touched `usage_service.py`, not this route). **Fix:** mirror the text-route consume/refund/record bracket before the Vision call; refund on 0-1 products identified.
2. **SSE progress is dead in the shipped client — fake checklist shows "all done" at 4.5s while backend runs ~31s.**
   `features.ts:52` `ENABLE_EXPO_FETCH_SSE_DEFAULT=false` → `api.ts:484-488` runs blind REST;
   `onStatus/onSpecs/onPrices` never fire. `LoadingScreenVariants.tsx:99` `STAGE_CYCLE_MS=900` ×5
   stages freezes all-done at ~4.5s regardless of real progress; caption is one static string.
   Single largest perceived-latency gap: real latency ~25-31s, communicated progress ends at 4.5s.
   **M21 risk: LOW** — `features.ts` + `LoadingScreenVariants.tsx` untouched. **Fix (a) short-term:** re-pace the synthetic checklist to the real ~30s envelope + escalate caption at ~8s. **(b):** flip `ENABLE_EXPO_FETCH_SSE` after the #118 cert-pinning device check AND after bounding the expo/fetch tail (no timeout on `api.ts:511-514`; post-Phase-1 tail unbounded unless `ENABLE_FULL_STREAM_DEADLINE` on).
3. **App boot blocks the splash on a network token refresh, 120s ceiling.**
   `App.tsx:185` awaits `initializeAuth()` before `setIsLoading(false)` (:203); `:245` gates the
   whole tree on `isLoading`. `initializeAuth` (`authService.ts:363-390`) awaits
   `refreshSession()` → `api.post('/auth/refresh')` on the shared axios instance (`timeout:120000`,
   `api.ts:22`, no per-call override). Cached-user fallback runs only AFTER the call settles, so
   blocking buys nothing on the failure path — the 401 interceptor already self-heals.
   **M21 risk: MEDIUM** — `App.tsx` untouched but `authService.ts` touched by W2/W3; re-check `refreshSession`/`initializeAuth` still shaped as described. **Fix:** boot optimistically from cached user+token, refresh in background; at minimum pass a ~5s per-call timeout to the boot refresh.
4. **Compare loader has no cancel + no slow-path watchdog in the 30s-120s gap; camera identify has no timeout at all.**
   `HomeScreen.tsx:863-872` full-screen overlay, no cancel/back; `abortRef.current?.()` fires only
   on unmount (`:187-201`), and tab-switch never unmounts Home. REST rides axios 120s. Camera path
   `api.ts:169-176` raw `fetch` with no `AbortSignal`/timeout. Instrumentation comment references an
   "88s wall-time gap". Escape hatch exists (tab bar stays tappable; axios 120s eventually errors →
   soft-timeout Alert), so verifier downgraded the "trapped indefinitely" wording but kept **P1**.
   **M21 risk: MEDIUM** — `HomeScreen.tsx`/`api.ts` touched by W2. **Fix:** cancel button wired to `abortRef` + ~35s client watchdog → existing soft-timeout Alert + `AbortController`+timeout on `identifyFromImages`. Abort plumbing already exists for text.

### P2 — verified
5. **1.5s minimum splash floor, stacked on native startup** (not overlapped — no
   `expo-splash-screen`/`preventAutoHideAsync` anywhere). `SplashScreen.tsx:33`
   `setTimeout(onFinish, 1500)`; render gate `App.tsx:245`. Deliberate brand moment, one-line
   tunable. **M21 risk: LOW** (untouched). **Fix:** shorten to ~800ms or skip when `fontsLoaded && !isLoading` at mount.
6. **`POST /url/compare`: no history save, no metering, and client `selected_category` silently dropped.**
   `url_routes.py:126-163` + `HomeScreen.tsx:415-426`. `URLCompareRequest` is `{url1,url2,region}`
   only (Pydantic `extra='ignore'` drops the category chip → no `category_switched` banner);
   no user dep, no `save_comparison`/metering → URL compares never appear in History + server-side
   freemium bypass; client `increment()` drifts the local counter. **M21 risk: LOW** (`url_routes.py` untouched). **Fix:** add `get_optional_user` + text-route usage bracket + fire-and-forget `save_comparison_and_track_cohort(input_type='url')`; add `selected_category` to the request model (or stop sending it).
7. **SSE terminal latch misses `settle_complete`** → flag-ON streaming can double-compare, and
   breaks outright when Bundle F removes the duplicate `complete` event. `api.ts:545-599` latches
   only on `complete`/`error`, not `settle_complete`; backend emits the pair at 7 sites.
   Latent today (REST default). **M21 risk: MEDIUM** (`api.ts` touched by W2). **Fix:** treat `settle_complete` as terminal + dedupe against `complete` while both coexist.
8. **Raw-fetch camera identify + social login have no timeout/abort** → camera flow can hang until
   the OS socket timeout. `api.ts:169-176`, `authService.ts:501,613`; `ResultsScreen.tsx:230-303`
   cleanup only sets a `cancelled` bool (can't abort). Hang duration **needs device**. **M21 risk: MEDIUM** (`authService.ts` W2/W3, `ResultsScreen.tsx` W2/W3/W4). **Fix:** `AbortController` + ~60-90s timeout → existing `timeout` retry state.
9. **Force-update contract is a dead wire — the app never calls `GET /app/version`.**
   `version_routes.py:19-22` serves it; zero client call sites (grep of all `.ts/.tsx` for
   `app/version`/`min_version`/`force_update` = 0). `APP_FORCE_UPDATE` kill-switch cannot reach any
   device. **M21 risk: LOW** (untouched). **Fix:** startup fire-and-forget `GET /app/version` vs `expo-application` native version → blocking update screen when `force_update && current < min_version`; gate behind remote-off default, test the comparator.
10. **RevealBurst winner celebration + PhoneMockup onboarding glow are dead animations** — shared
    values driven but never bound to render. `RevealBurst.tsx:104-121` drives `badgeScale`/
    `particleProgress` but has no `useAnimatedStyle`/`useAnimatedProps` (badge is a plain View, SVG
    particles are static). `PhoneMockup.tsx:222` reads `glowOpacity.value` once at render while
    `withRepeat(-1)` pulses it forever with zero output (a live no-op UI-thread driver in onboarding
    Step03). The signature emerald winner-reveal ships static. **M21 risk: LOW** (both files untouched). **Fix:** bind the values (`Animated.View` style + `createAnimatedComponent(Circle)`+`useAnimatedProps`).
11. **After a failed compare the text path shows the raw axios string** ("Request failed with status
    code 400") instead of the backend's friendly copy. `HomeScreen.tsx:388` uses `error.message`;
    URL path correctly uses `parsed.message` (`:453`). Live: the app's pair-shape request returns
    400 `INSUFFICIENT_DATA` with "choose different products." after 31.5s — the friendly sentence is
    on the wire and discarded (also violates the zero-scary-copy contract: "failed"). **M21 risk: MEDIUM** (`HomeScreen.tsx` W2). **Fix:** one line — `parsed.message || t('home.errors.comparison')`.
12. **History search submit blanks the whole screen to a spinner + focus-refetch stale closure
    clobbers filtered results.** `HistoryScreen.tsx:781` `onSubmitEditing` sets `loading=true` →
    `:742-750` early-returns the entire screen (incl. the search field) to a centered spinner;
    `:347-351` `useFocusEffect(useCallback(...,[]))` pins the first render's `loadHistory` (closure
    `searchQuery=''`), so every refocus fetches unfiltered and overwrites the search; a first-load
    network failure renders the "no comparisons yet" empty state. **M21 risk: HIGH — `HistoryScreen.tsx` was rewritten 637 lines in W3 + touched in W4. RE-VERIFY FIRST; likely partly addressed by the mobileJank pass.**

### P3 — verified (lower priority; several likely closed by M21)
13. **History rows mount invisible up to ~2s** — index-staggered `FadeInDown.delay(index*50)` inside
    a virtualized SectionList; deep "Older" rows blank on fast scroll. Verifier **downgraded P2→P3**
    (windowSize defaults keep most rows mounted once; worst case is a first-visit fast fling).
    `HistoryScreen.tsx:571`. **M21 risk: HIGH (W3 rewrite + mobileJank test) — probably already fixed.**
14. **Every keystroke in History search re-renders all visible rows** — inline `renderItem` closure
    (`HistoryScreen.tsx:521`), row not memoized, pierces the 4-layer SectionList pure guard; zero
    visual change (query applies on submit). **M21 risk: HIGH (W3 rewrite) — probably already fixed.**
15. **ResultsScreen fetches usage status into state nothing reads** — `ResultsScreen.tsx:164,175`
    dead `getUsageStatus().then(setUsageStatus)`; one dead round-trip + one full re-render of the
    unmemoized ResultsContent tree landing mid winner-reveal window. **M21 risk: HIGH (ResultsScreen touched W2/W3/W4 + a `Results.memo` test landed) — RE-VERIFY; may be closed.**
16. **CounterTicker flashes the final value then ticks from 0, ~60 setStates/s via `runOnJS`.**
    `CounterTicker.tsx:50,63-72`. Verifier **PARTIAL**: the flash is via the `useState` initializer
    (not the cited `setDisplay`), one live consumer (`InviteeQuizScreen`), and an `entering` wrapper
    likely masks the flash — real but edge-case. **M21 risk: LOW** (untouched). **Fix:** guard the reaction to commit only when the rounded value changes.
17. **History→Results floors every open at 1.2s even for warm cache hits** (`ResultsScreen.tsx:144`).
    The Home→Results floor was checked and is **healthy** (overlaps the fetch, doesn't stack).
    **M21 risk: MEDIUM** (ResultsScreen touched). **Fix:** apply the floor only when the fetch exceeds ~300ms, or drop to ~400ms on the history path.

### Adjacent observation (not a numbered finding, verifier-noted)
- `HomeScreen.tsx:843` (Home "Smart pick") and `ProfileScreen.tsx:413` navigate to `Results` with an
  unhandled **`from_history`** param that `ResultsScreen` never reads (route type only knows
  `result`/`comparison_id`/`vision_products`) → lands on the empty-state branch. **The
  flows-triggers finder flagged this as its own P1** but it was NOT reached by a verifier before the
  limit. **M21 risk: HIGH** — `ProfileScreen.tsx` was rewritten in W4; re-verify whether the param was fixed. If still live it is a real dead-tap on two entry points.

## B. MOBILE CHECKUP — reported but NOT adversarially verified (limit hit)

These come from the finders directly; treat as **leads, not confirmed** — the verify pass
never ran on them. Re-verify before acting.
- **P1 bundle — `lucide-react-native` barrel imports ship all ~1,682 icons = 1.27 MB minified /
  ~25% of the JS bundle, for 68 icons actually used.** 34 files `import { … } from 'lucide-react-native'`
  (`ResultsScreen.tsx:53`, `HistoryScreen.tsx:31`, `ProfileScreen.tsx:54`). **Highest-value size win
  if confirmed** (per-icon imports or a babel transform). M21 didn't address bundle size.
- **P1 network — expired access token silently downgrades a compare to anonymous** (history +
  personalization lost, usage unmetered). `get_optional_user` (`auth_routes.py:306-322`) returns
  `None` for an expired Bearer instead of 401; `api.ts:85-127` interceptor context. Verify whether
  the 401-refresh interceptor actually re-drives the compare.
- **P1 render — LoadingRings animate via 60Hz JS `setState` then freeze** (`LoadingRings.tsx:113`) —
  same dead-shared-value class as RevealBurst (#10). LoadingRings untouched by M21.
- **Startup leads:** 5 unused Cairo font weights (~470 KB) ship in every build; `init()` has
  unguarded awaits before its try/catch (a rejection strands the app on splash) + a redundant 2nd
  i18n import; first interactive paint fires 4 separate network calls incl. a telemetry-only health
  check and an unbatched analytics POST.
- **Flows leads:** Arabic logout confirmation shows account-DELETION copy ("cannot be undone") — the
  EN-only `.replace()` never matches the AR string (**W4 was the RTL sweep — likely fixed, verify**);
  compare handlers lack a re-entrancy guard (fast double-tap → two paid comparisons + leaked abort
  handle); Results has **no outbound purchase/source links at all** (`openRatingSource` is dead code,
  `price.url` never used); Login back arrow + "Email" social pill are no-ops; onboarding Step-17
  notifications answer is never persisted; camera capture failures are silent.
- `safe-hygiene` finder was **killed before returning** — the "safe to remove vs looks-dead-but-isn't"
  list does NOT exist yet. Re-run it before any deletion pass (this is the guardrail lane the user
  explicitly asked for; do NOT delete anything without it).

---

## C. PRICE/CACHE-TRUTH CLUSTER (#51-#57) — workflow died at the session limit, 0/13 agents done

Workflow `wf_3bf65bef-d68` (sequential implement → adversarial review → gates) never
completed a single agent. **One orphaned partial exists** and is preserved:

- Branch **`origin/wip/52-iherb-currency-partial`** (commit `712aeff`, parent `79a4594`).
  The `impl:#52` agent left a 158-line diff to `price_service.py` + a test file + 3 GA-card
  fixtures. It **compiles** (`py_compile` OK) but has **NO test run, NO strip-check, NO review,
  NO byte-identity gate** — it introduces `ENABLE_IHERB_PAGE_CURRENCY` (+ touches two existing
  flag reads: `ENABLE_VISIBLE_TEXT_CURRENCY`, `ENABLE_EXTENDED_FALLBACK_RATES`). **Treat as a
  starting point to audit, not as done.** `git diff main origin/wip/52-iherb-currency-partial`.
- **Resume:** `Workflow({scriptPath: '…/price-truth-cluster-wf_3bf65bef-d68.js', resumeFromRunId:
  'wf_3bf65bef-d68'})` — all 13 agents errored (session limit), so NONE are cached; the resume
  effectively re-runs from scratch. The #52 implementer should diff the wip branch for prior art.
- The seven issues are each self-contained with verified `file:line` in the workflow script and in
  the GitHub issue bodies. Order used: `#52 → #51 → #53 → #54 → #57 → #56 → #55` (provenance before
  cache-state; admin flush #55 last). **All still OPEN.**

## D. ISSUE TRIAGE (2026-09-02) — 6 closed, 32 REAL_OPEN, 1 blocked

Verified all 39 open issues against real code (`wp0x7p8rt`). **Closed 6:** #97 (Serper `web=0`
live), #92 (Firecrawl rawHtml), #62 (prefetch try/finally), #50 (currency relabel), #47 (frontend
CI blocking), #123 (stale — `_names_the_loser` deleted). **Now 33 open.** Grouped:

- **Price/cache truth (7):** #51 #52 #53 #54 #55 #56 #57 → cluster C above.
- **Scraper coverage (7):** #75 #76 #77 #78 #79(security: substring domain match) #93 #94.
- **Metering/spend (6):** #58 #61 #63 #64 #66 #67.
- **Perf/event-loop (6):** #70 #71 #72 #73 #74 #114 — partially eaten by M13/M18; re-scope each.
- **Data+errors (3):** #65 #68 #69.
- **Ops visibility (2):** #80 #81.
- **CI (1):** #89 — **NOT actually done.** CI is green only because the step deselects the 14 nodes
  in `tests/.pre_impl_failures.txt`; they still fail locally (camera_vision MagicMock fixture,
  `openai_service.py:109`). Reported "0 failed" off CI overstates the estate.
- **Blocked on Ahmed (1):** #96 — the Monday live-suite fails at import, empty `OPENAI_API_KEY`
  Actions secret (NOT scraper drift). Same OpenAI-credit blocker.

**Three quietly-worse-than-P2:** **#65** — `_update_behavior_profile` selects `category_used,
products` (columns the writer never emits, in no migration); fails silently behind a broad `except`,
so `users.behavior_profile` is **never written** — behavioural personalization is dead, not degraded.
**#52** — `fetch_iherb_price` compares currency to itself → **every iHerb price stamped genuine
`local_bhd`**. **#96** — mislabelled "scraper drift"; it's the empty-secret import abort.

## Next-session order (suggested)
1. **Reconcile mobile §A/§B against `b6ce090`** — kill the M21-HIGH-risk findings (#12/#13/#14/#15,
   ProfileScreen `from_history`, Arabic logout copy) first; keep the M21-LOW-risk live ones.
2. **Ship the M21-LOW-risk, high-value mobile fixes** (all clear of the parallel lane): SSE-checklist
   honesty (#2), the one-line friendly-error copy (#11), the lucide barrel bundle win (verify first),
   camera metering (#1 backend), url/compare metering+history (#6 backend). These are dark-shippable
   or client-side.
3. **Re-run the price cluster** (§C) once budget resets — it's the plan the user pinned.
4. **Re-run `safe-hygiene`** before any deletion, per the user's no-damage constraint.
