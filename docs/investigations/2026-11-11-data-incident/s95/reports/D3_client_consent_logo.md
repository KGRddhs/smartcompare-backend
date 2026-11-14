# D3: the client - empty-data rendering, the logo over the page, the consent re-ask, the ship path

Read-only. Source: the plain export of main 731bcddf (scratchpad/src/731bcddf). All path:line refs are at 731bcddf.
`git diff --stat a74caba7 731bcddf -- SmartCompareApp/` touches only the consent / legal files (AiConsentSheet.tsx, aiConsent.ts, consent.ts, Step05Trust.tsx, i18n) - the result-page files are unchanged since T4. `git diff --stat 683f56c0 731bcddf` over SmartCompareApp/package.json, app.json, eas.json and assets/ is EMPTY: the store binary's native config equals main.
E = ESTABLISHED (read in code), L = LIKELY (inference).

## Summary (four findings)

1. **The MYEZ logo over the page is the RevealBurst badge (E).** ResultsContent mounts it in an absolute-fill slot over the dimension-bars section and never unmounts it (ResultsContent.tsx:536-549, style 872-880). Its badge is a 112 px light-emerald disc holding the 56 px MYEZ mark (RevealBurst.tsx:230-245, BADGE_R = 56 at :71). The badge springs to scale 1 and stays there: only the particles fade (RevealBurst.tsx:194-215). Fix: remove the slot. Size S, ships over the air.
2. **The consent re-ask: at 731bcddf the code DOES re-ask an account whose stored record is below 3 (E).** No server copy of the AI consent exists (E). So "never asked" is LIKELY a phone running the JS from before v3, not a logic bug. One owner phone test settles it before any code is written (section c).
3. **Empty-data rendering.** Most of what looked wrong is the client faithfully drawing server fields: delta captions, scores, review text, confidence legs. A few client rules make it worse: all-dash spec rows, a reviews header that adds up counts from unrated products, a price chip that is hidden instead of stated, no size on the price, and an unconditional TOP MATCH badge.
4. **Ship path.** Runtime 1.0.0 (appVersion policy), channel production. Every client fix in this report is JS-only, so it ships over the air. These need an App Store build: the native update-apply config, and the camera / photo permission strings that name OpenAI.

## (a) The result page, element by element

| Screen element | Rendered by | What it does with empty / odd data |
|---|---|---|
| "TOP MATCH" | TopMatchBadge, mounted unconditionally (ResultsContent.tsx:289; TopMatchBadge.tsx:24-27) | Always shown, even when one product has no picture, price, specs or reviews (E). |
| Grey placeholder picture | ProductImage (ResultsContent.tsx:337-344) | null, undefined or onError -> a tone tile (ProductImage.tsx header 6-21). Any URL string is drawn as given, so the Blake-poem page image is shown unchecked (E). The picture choice is server-side (image tier). |
| "29.320 BHD" with no size | formatPrice (ResultsContent.tsx:187-208); price line 376-386 | Prints the amount and currency only. ResultsContent has no size field at all (grep finds no size / size_ml / volume), so a 15 ml decant and a 100 ml bottle look alike (E). |
| "No confirmed price yet." | formatPrice: `price.unavailable` -> `results.price.pending` (ResultsContent.tsx:194; en.json:149) | Set by the server when no price passed its gate (pending_genuine / size_mismatch). `price == null` or `amount null` without the flag -> `results.priceNA` (:195). Under ENABLE_FIELD_STATUS_METADATA (OFF) the honest "not listed" line replaces it (:367-374) (E). |
| "The detailed write-up is unavailable this time. The scores and prices below are real." | ResultsContent.tsx:439-446 when `isDegradedComparison(result)` = `comparison.error` truthy (resultHonesty.ts:17-20); en.json:865 | Shown on every degraded 200. ENABLE_ANTHROPIC_VERDICT was OFF at 21:19 UTC on 2026-11-13, so a degraded verdict is expected (L). The second sentence still claims "prices below are real" beside "No confirmed price yet" and all-dash specs (E: the copy is fixed). |
| Bold "stronger with you leads on Versatility." + italic "Tyger stays in the conversation..." | FactualVerdict line1 / line2 (ResultsContent.tsx:463-468; FactualVerdict.tsx:63-67) | It wins the ternary before the `isDegraded` branch, so the server template verdict shows under the "unavailable" note. The client only blocks banned words and score internals (FactualVerdict.tsx:53-61) (E). The sentences are built on the server (response_builder.py, per T4 §4). |
| Chip "Weighted down value per wear, down presentation, up scent character" | PersonalizationChip (ResultsContent.tsx:489-494; PersonalizationChip.tsx) | Hidden only when `applied_shifts` is empty. It shows up to 3 server shifts with arrow glyphs and raw `dim_display` text (E). The shifts are the user's priorities, unrelated to whether any data exists. |
| One bar "Versatility", "More versatile" | DimensionBars, outer gate `dimensions.length >= 3` counts placeholder dims (ResultsContent.tsx:527); price and value dims dropped when any price is pending (:555-562); inner filter drops data_insufficient, null scores and caption_key limited_data (DimensionBars.tsx:82-87) | The bar count is whatever non-placeholder dims the server emitted (E). With 11 dash specs, a versatility score is still emitted, so the score source is not the shown specs (L, server). |
| A bar drawn for "N/A vs Moderate projection" | DimensionRow draws `Math.max(1, score)` split proportionally (DimensionBars.tsx:249-271 region; DimensionBar.tsx:49-51). The caption is server `delta_text`, shown verbatim via safeDelta | The client draws whenever both scores are non-null (E). The caption comes from scoring_service.py:3669-3677: `sillage` "N/A" is a truthy string, so it becomes "N/A vs Moderate projection" (E). The score is computed elsewhere and is not null (E for the client rule; server root cause). |
| "8h vs 8h" with unequal bars | the same; caption at scoring_service.py:3660-3668 | The caption is `max(ha,hb)h vs min(ha,hb)h`: NOT in left/right order, and a range "8-10 hours" collapses to one figure (E). The bars use the separate scores, so equal captions sit on unequal bars (E). Server fix. |
| "What we know: Reviews Low, Specs High", no price chip | ConfidencePills with `hidePricePill = anyEstimated(products) \|\| pricePending` (ResultsContent.tsx:591-596; ConfidencePills.tsx filter) | The price pill is REMOVED whenever either price is pending, so there is no price state at all (E). "Specs High" comes from the server leg: `best fact-check pct >= 40 or citations >= 8` across ANY product (scoring_service.py:1199-1213), not from spec values being present, so High can sit beside 11 dash rows (E rule; L for this case). |
| "Reviews - reviews across both" (no count) / "4.7 avg, 38,000 reviews across both" | ResultsAccordion sub (ResultsAccordion.tsx:170-196, 263-275; en.json:774-775) | `totalReviews` sums review_count over BOTH products, rated or not. `avgRating` uses only rated ones (E). "across both" is a fixed string, so a total from one product (or from an unrated one) still reads "across both" (E). With no counts the bare tail "reviews across both" is shown (E: Tyger case). |
| Tyger review text "No review data was available ..." | ReviewPraiseBlock: any non-empty `review_praise` string is shown as praise (ResultsAccordion.tsx:412-421, 438-452) | No guard against a model's no-evidence sentence (E). "Reviews are still coming in." (:457-461) is shown only when NO product has praise or rating > 0. Fix belongs on the server (null the praise when the model reports no evidence), with an optional client guard. |
| "Specs - 11 dimensions", all dashes | ResultsAccordion allSpecKeys (ResultsAccordion.tsx:206-222), cells (575-599), header count (292-296) | Pass 1 keeps keys with a real value. If none has one, pass 2 (the "structural" path) keeps every non-null scalar key, including "N/A" / "unknown" strings, and renders each as "—" on both sides (E). The header count is taken BEFORE the one-side-missing rows are dropped (`missing !== 1`, :597-598), so the count can exceed the rows shown (E: Sauvage "10 dimensions"). There is no empty-state line. The server must have sent 11 NA-like strings: a null value would have produced no row (L). |
| Pros & Cons absent | `hideProsCons={isDegraded}` (ResultsContent.tsx:646) | The row is removed on a degraded result (E). |

## (b) The MYEZ logo drawn over the result page

Every client place that draws the mark (grep of QarenLogo, LoadingRings, RevealBurst):

| Site | Can it sit on or above the results screen? |
|---|---|
| SplashScreen (SplashScreen.tsx:120): App.tsx:380-383 returns it early | No: it replaces the whole tree before navigation. |
| LoadingRings in ResultsScreen (ResultsScreen.tsx:775-797) | No: an early-return branch while `loadingResult`, never together with content. |
| LoadingRings in HomeScreen / LoadingScreenVariants | No: Home is below the Results stack screen. |
| Header marks: Home :1021, History :955, Profile :325, Register / Forgot / Step01 | No: in-flow, on other screens. |
| **RevealBurst in ResultsContent.tsx:536-549** | **Yes.** |

**Culprit (E for the code, L that it is exactly what the owner saw):**
- **Where and when it mounts.** `ResultsContent.tsx:536-549` mounts `<RevealBurst size={220}>` inside `styles.revealBurstSlot`. That style is `position: absolute`, top / left / right / bottom 0 (ResultsContent.tsx:872-880), so the slot fills the dimension-bars section. The condition is `!isWeird && winnerRevealed`, inside the `dimensions.length >= 3` gate. `winnerRevealed` becomes true after the reveal delay and stays true (ResultsScreen.tsx:207, 501-503).
- **Why it never goes away.** The badge is an Animated.View with the MYEZ mark (`QarenLogo size={BADGE_R}`, BADGE_R = 56, RevealBurst.tsx:71 and 230-245): a 112 px disc. Its scale springs 0 -> 1 and stays at 1 (RevealBurst.tsx:194-215). Only the particles fade (`PARTICLE_FADE_START`, RevealBurst.tsx:150-156). The file's own header says the burst "is never unmounted" (RevealBurst.tsx:23-24). The A10 fix (7c93df36) retired the frozen particles but not the badge. Commit e81199fa (S71 U4d, #283) then swapped the old Q glyph for the MYEZ mark, which made it read as the logo.
- **Why it is visible on top of the content.** The DimensionBars container has no background (DimensionBars.tsx:411-414), so the disc shows through the bars. The burst's fixed 220 px height is centred in a section that can be shorter (one bar, as on Tyger), so it spills over the verdict block above and the chips below (L: geometry). It has pointerEvents none, so nothing reacts to it and it simply scrolls with the page.
- **Fix (S, ships over the air).** Delete the slot in ResultsContent.tsx:536-549 and its style at :872-880, and drop the unused import at ResultsScreen.tsx:102. The alternative is to keep the particles and delete the badge (RevealBurst.tsx:230-245). The owner said the logo should not be shown, so removing the slot is the honest minimum.
- **Tests that pin it** (git grep at 731bcddf): `__tests__/brand/revealGlyph.u4d.test.tsx`, `__tests__/hero/RevealBurst*.test.tsx` plus the snapshot, `__tests__/components/hero/RevealBurst.test.tsx`, and about ten ResultsContent tests that query `results-v2-reveal-burst-slot`. Run the full jest suite at GREEN, because source-scanning fences read these files.

## (c) The consent re-ask

**What decides whether the sheet shows (E)**
- `ensureAiConsent` (aiConsent.ts:181-187) shows the sheet unless `hasCurrentAiConsent(userId)` holds, i.e. the stored `@qaren_ai_consent_<userId>` record has `version === AI_CONSENT_VERSION`, which is 3 at 731bcddf (aiConsent.ts:58, 93-97).
- A record with version 1 or 2 is not current, so the sheet IS shown. An Agree is persisted as version 3 only after `ask()` resolves true (aiConsent.ts:184-185, 143-153). Nothing auto-upgrades a consent: the legal constraint is met by the current code.
- Every Home dispatch path is wrapped in `withAiConsent`: text HomeScreen.tsx:421, link :585, scan CTA :825, camera permission :831, gallery :836, scan rows :893. The quick-pick path goes through handleTextCompare (:740). History and Profile open stored results by comparison_id and dispatch no compare.
- `grantedRef` (aiConsent.ts:218, 270, 297) remembers an Agree for the HomeScreen mount. Main unmounts on logout because App.tsx:400 renders Auth when not authenticated, so it cannot carry one account's Agree to another. Still, it is keyed by nothing: a latent defect worth keying by user id.
- **Header.** `X-AI-Consent-Version` is attached only when the saved account's record is current (requestContext.ts:114-131, 139-146; memo at aiConsent.ts:122-140, dropped by recordAiConsent).
- **Server.** The version comes only from that header, per request: app/utils/request_context.py:76, 125-129, 159-161, bound by app/middleware/request_context.py:31-39 when ENABLE_REQUEST_CONTEXT_HEADERS is on. llm_router.decide (llm_router.py:343-355) returns anthropic for consent >= 3 (MIN_CONSENT_VERSION = 3, :63), else openai while ENABLE_OPENAI_PRE_V3 is on, else refuse. The OpenAI stop then turns "openai" into no AI text.
- **No server-held AI consent.** ENABLE_CONSENT_PERSIST writes only the Terms fields (`terms_accepted_at`, `terms_version`, `age_attested_at`) on register / social-login (consent_service.py:1-24, 39-41; auth_service.py:388-396). No route returns an AI consent: a grep of app/ for ai_consent finds only the header plumbing. So the server cannot suppress or replace the sheet, and a "server-side reset of stored consents below 3" has nothing to reset.

**Why the old account was not asked (L)**
- The code at 731bcddf cannot produce "old record, no sheet, header below 3". The most likely state at 01:36 UTC is a phone running a bundle from before v3, where `AI_CONSENT_VERSION = 2`: the stored v2 record counts as current, no sheet appears, the header says 2, and the server takes the pre-v3 path.
- app.json:275-277 sets only `updates.url`. There is no `checkAutomatically` and no `fallbackToCacheTimeout`, so expo-updates uses its defaults: it checks at launch, downloads in the background and runs the new bundle at the NEXT cold launch (L: library default, not read in the pinned package).
- The new account six minutes later was on v3. Plausibly the app restarted in between. One mechanism: new-account onboarding calls `Updates.reloadAsync()` when the language changes the layout direction (useLanguage.ts:42-70; rtlBootstrap.ts:44-61), and that reload launches the newest downloaded bundle (L).
- Another possibility to rule out: a build on another channel (preview / development, eas.json) never receives production updates.

**Proof before code (owner phone, about 2 minutes).** Fully quit the app, open it, quit again, open again. Log out of the new account and log into the OLD account, then tap Compare.
- If the v3 sheet appears, there is no consent-logic bug, and every existing user gets it on their own second cold launch after the update.
- If it does not appear, capture which update is running (expo-updates `updateId`, e.g. from the Sentry event context) and reopen this question.
- The server cannot tell the two cases apart today: compare_runs records consent_version (compare_runs.py:173-177, 460), but only under ENABLE_COMPARE_RUN_LEDGER, which is not on the ON list.

**Smallest correct fixes, by which case holds**
- **Case A, the bundle was older (L, expected).** No change to the consent rule.
  - Optional client unit (S-M, ships over the air): on launch and on AppState 'active', call `Updates.checkForUpdateAsync()`, then `fetchUpdateAsync()`, then `reloadAsync()` at a safe moment (Home focused, no compare in flight). expo-updates is already in the binary (useLanguage.ts:66-67). This helps only phones that already run this update, so it speeds up the NEXT transition, not this one.
  - Native alternative (App Store build): `updates.fallbackToCacheTimeout` / `checkAutomatically` in app.json.
  - Owner / ops step now: users pick up v3 on their second cold launch. Nothing server-side may upgrade them.
- **Case B, the sheet really does not show on v3 JS (not supported by the code read).** Then the defect is outside aiConsent.ts. Look first at getSavedUser returning a different id shape for very old accounts (aiConsent.ts:167-174).
- **Either way (S, ships over the air):** key `grantedRef` by user id (aiConsent.ts:218, 270-297).

## (d) Ship path

- **Version.** app.json:5 `version` 1.0.0; :272-274 `runtimeVersion.policy appVersion` -> runtime "1.0.0"; :275-277 updates URL only. eas.json: production profile `channel: production`, `appVersionSource: remote`, autoIncrement.
- **What is native.** expo-updates ~29.0.20, expo ~54.0.37, RN 0.81.5 (package.json:25, 43, 49). Native config is identical between the store binary (683f56c0) and main (empty diff), so the binary matches what main declares.
- **Over the air to the 1.0.0 store app (JS and bundled JS-required assets only).** Every client fix above: removing RevealBurst; the consent `grantedRef` keying; an in-JS update check (the module is already native in the binary); the spec empty state; the reviews header math and wording; showing a price-pill state instead of hiding it; a size line on the price card once the server sends the size; and guards on review_praise.
- **App Store build (1.0.1).**
  - Any change to the `updates` native config (checkAutomatically, fallbackToCacheTimeout).
  - The camera and photo-library permission strings (app.json:220 and :228 say photos are "sent to OpenAI"). These must change when vision moves to Claude: they are Info.plist strings, so they need a new binary.
  - Any new native module, plugin or permission.
- **Publishing rule.** main says 1.0.0 now, so `eas update --channel production` from main targets runtime 1.0.0. Once main bumps app.json to 1.0.1, publish 1.0.0 updates only from a release/1.0.x checkout, because runtimeVersion follows that file.

## (e) Root causes and fixes

| id | cause | where | class | conf |
|---|---|---|---|---|
| RC-LOGO | RevealBurst badge (MYEZ mark, 112 px disc) stays at scale 1 for the life of the screen, in an absolute slot over the bars section | ResultsContent.tsx:536-549, 872-880; RevealBurst.tsx:194-245 | DISPLAY | ESTABLISHED |
| RC-CONSENT | No v3 sheet for old accounts: the 731bcddf client re-asks any record below 3, so the phone was most likely running the pre-v3 bundle (the default apply-on-next-cold-launch); the server has no AI consent of its own | aiConsent.ts:58, 93-97, 181-187; app.json:275-277; llm_router.py:343-355 | CONSENT | LIKELY |
| RC-SPECDASH | The structural fallback lists every NA-valued key as dash rows; the header count is taken before the one-side row drop | ResultsAccordion.tsx:206-222, 292-296, 575-599 | DISPLAY | ESTABLISHED |
| RC-REVHDR | The reviews header sums counts over both products (rated or not) and always says "across both" | ResultsAccordion.tsx:170-196, 263-275 | DISPLAY | ESTABLISHED |
| RC-PRAISE | Any non-empty review_praise is shown, including a "no review data" model sentence | ResultsAccordion.tsx:412-452 | DISPLAY | ESTABLISHED |
| RC-BARS | Bars come from scores while the caption comes from spec strings: "N/A" is truthy; longevity shows max-then-min, not A/B; ranges collapse | scoring_service.py:3660-3677; DimensionBars.tsx:82-87; DimensionBar.tsx:49-51 | DISPLAY | ESTABLISHED |
| RC-PRICEPILL | The price pill is hidden (not stated) when either price is pending; the specs leg comes from fact-check pct, not from spec values | ResultsContent.tsx:593; scoring_service.py:1199-1213 | DISPLAY | ESTABLISHED |
| RC-SIZE | The price card never shows a size | ResultsContent.tsx:187-208, 376-386 | DISPLAY | ESTABLISHED |
| RC-DEGRADED | The degraded note claims "prices below are real" beside no price; the factual verdict and TOP MATCH show on a degraded or unresolved pair | ResultsContent.tsx:289, 439-468 | DISPLAY | ESTABLISHED |

| fix | user sees | size | ships |
|---|---|---|---|
| F-LOGO: remove the RevealBurst slot and import; update the pinning tests | no logo over the result | S | over-the-air update |
| F-CONSENT-PROOF: owner cold-relaunches twice, then compares on the old account | the v3 sheet appears (or the bug is proven) | S | owner or ops step |
| F-CONSENT-KEY: key grantedRef by user id | none (latent) | S | over-the-air update |
| F-UPDATE-APPLY: in-JS check, fetch and reload on launch / foreground | future consent and fix updates reach phones on the first launch | M | over-the-air update |
| F-UPDATE-NATIVE: updates.fallbackToCacheTimeout / checkAutomatically | the same, enforced natively | S | App Store build |
| F-SPECEMPTY: when no key has a real value, show one "not listed by the stores we read" line, not dash rows; count the rows actually shown | an honest empty specs section | S | over-the-air update |
| F-REVHDR: sum counts over rated products only; say "across both" only when both are rated | a correct reviews header | S | over-the-air update |
| F-PRAISE: the server nulls a no-evidence praise (a client guard is optional) | no "no data" essay shown as a review | S | server deploy |
| F-BARS: null score when either side is NA; equal scores (or no bar) when values are equal; caption in A/B order; keep ranges | no bar for N/A; equal values give equal bars | M | server deploy |
| F-PRICEPILL: show "Price · Partial" (or Low) instead of hiding it; derive the specs leg from spec coverage | the chips match the page | S | over-the-air update + server deploy |
| F-SIZE: the server sends the size with the selected price; the client prints it beside the amount | "29.320 BHD · 100 ml" | M | server deploy + over-the-air update |
| F-DEGRADED: reword the degraded note (no "prices are real" claim); hide TOP MATCH when a product has no price and no data | no false reassurance | S | over-the-air update |
| F-PERMSTR: camera and photo strings name Anthropic when vision moves | correct OS prompts | S | App Store build |
