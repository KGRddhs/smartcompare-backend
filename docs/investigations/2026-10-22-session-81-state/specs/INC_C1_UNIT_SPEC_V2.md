# INC-C1 OTA-BATCH: unit spec V2 (amend round, S98 spec writer, Opus 5.5, 2026-11-22)

Base: main `d2f49d8b9da1d34e10d20b4ca58421da70a4c0f7`. `git diff --stat 5cd93c6a d2f49d8b -- SmartCompareApp` is EMPTY (0 files; 0 since 2e7a1229): every client cite of the draft holds; server cites are re-measured. A CLIENT unit for an over-the-air update of build 1.0.0: no app.json, package, lock, locales or native change; it publishes nothing. SCS structured_comparison_service, RB response_builder, TR text_routes, IR image_routes, UR url_routes, UX url_extraction_service, EH error_handler, LR llm_router; client paths under SmartCompareApp/src.

## Changes from the draft (ruling or addendum -> where it landed)
- F1 -> 7.0: renders, existing exports and catalogs only; no new symbol imported, no new path mocked; popTo a jest.fn; type mode via `home-mode-type` after a focus event, not re-applied on a second; tsc 0 at base.
- F2 -> H1-H3 run the REAL services/api (a partial mock would spread jest.requireActual); only the axios instance is mocked. F3 -> D4. F4 -> 7.0. F5 -> C3 control, S1 bytes. F6 -> section 6. F7 -> 1.3. F8 -> 2.3, L11. F9 -> 4.2, row 22. F10 -> L7. F11 -> 8.3.
- F12 -> cites re-measured; the api.ts:55 and HomeScreen.tsx:288 comments move, LoadingScreenVariants.tsx:123 stays; requestContext.ts `if` :152, join :153 (the draft was right); UR:146.
- F13 -> 3.3: two buttons, primary Type the names (`results-photo-type-names`), secondary Back (`results-empty-back`), header back unchanged; read as the photo state only, the engine state stays byte-identical (C2, P1(d), Q11).
- Q1, Q6 open (relay). Q2 50 s. Q3 "did not arrive in time". Q4 one wording, fresh and stale. Q5 asOf / lastSeen kept unused. Q7 8.2. Q8 popTo('Main') + services/homeEntryIntent.ts. Q9 FOCUS, two adversaries (8.4). Q10 answered by code: CAM-2 (#423) refuses with the same 503 (3.1); SD-C1 closed.
- A-1, A-2, A-3 -> section 5, SERVER DEPENDENCY (SD-V1..V3). A-4, A-5 -> IN (4.1, 4.2).
- V2 corrections: (a) EN `_one` / `_two` day forms take a literal 1 / 2 (the draft's {{days}} breaks the frozen c1a P2 rule, equal {{vars}} per key); (b) the generic link sentence only for BAD_REQUEST and codeless (the draft's rule caught AUTH_REQUIRED and VALIDATION_ERROR too); (c) three header readers now, so never vision_anthropic (SD-C2); (d) SD-L2; (e) moved pins re-listed by grep (8.1).

## 0. Summary, class, switch, shipping
- IN: C1-1 deadline 35 -> 50 s plus an honest partial note (T7-10); C1-2 price_asof and "Last checked ..."; C1-4 the photo message on the 503 LLM_UNAVAILABLE at identify; T7-04 link words (A-4, A-5); T7-08 one converted label. OUT: C1-3 (dropped), T7-09 / T7-11 (INC-C1b), the INC-R1 picker, A-1..A-3.
- Class FOCUS: adversary 1 correctness (every server answer and flag mix), adversary 2 words and RTL.
- Switch: NONE. The publish gates a client unit; the app has no remote flag store (config/features.ts holds build-time defaults), so a client flag would need another publish to flip, the same act as a rollback. Each new line renders only on its trigger (metadata.partial, a valid as_of, the 503 identify answer, a link code, converted_usd; T7-08 shows on every converted price, a one-label display fix); the 50 s deadline only lets an answer the server already sends arrive; the token is read only under ENABLE_KB_FIRST_SERVE (SD-A1).
- Shipping: merged code reaches phones only through an over-the-air publish (runtime 1.0.0), the owner's, not part of this unit; rollback is his republish; Q6 decides whether INC-C1a's six files ride along.

## 1. C1-1: "Hold on" over a real partial
### 1.1 Client (unchanged)
Alert(common.error, home.errors.timeout) shows only for a parsed TIMEOUT (HomeScreen.tsx:543-545, link :683-685): a TIMEOUT code, a codeless 503 (api.ts:1164-1178) or no response (ECONNABORTED / ETIMEDOUT / ERR_NETWORK, :1187-1194). Phones never stream (config/features.ts:52): one REST GET under COMPARE_TIMEOUT_MS 35000 (api.ts:56, :742-752); success:true -> onComplete (:753-756).

### 1.2 Server contract at d2f49d8b
- compare_from_text SCS:4291-4457: guards :4334-4355 before the timer; NEW INC-P2 bind :4359 (no I/O); `_t0` :4360; `wait_for(..., STREAM_HARD_CAP_SECONDS)` :4361-4383 (default 25.0 SCS:1838; web 30 per the draft's quoted 02:27 line).
- Cap (:4391): usable data (:3823) -> `_build_partial_response` :3940-4070 -> the "[L2.7] ... PARTIAL (success:true)" WARNING :4398-4402 -> `return partial` :4403; full shape (:4022-4066), prices via public_price_view or the INC-P2 view (RB:2108), metadata.partial true (:4051), partial_stage (:4053), category_used (:4054), elapsed_ms (RB:2255).
- No usable data: TIMEOUT {success false, error SCS:1902, code TIMEOUT} (:4451-4457; :4428-4442 under ENABLE_ALL_TIMEOUT_CAP_AS_TIMEOUT) or INSUFFICIENT_DATA (:4443-4450).
- GET TR:966-1174: pre-work :1006-1048; call :1050-1065; on failure refund :1093-1097, then 503 for TIMEOUT / LLM_UNAVAILABLE (TR:553-568), else 400 (:578-592); persist :1141-1165 (echo flag awaited, 5.0 s bound TR:123). EH:220-245 sends {success false, error, code, request_id}.

### 1.3 Cause and the proof read (F7)
The server answered 200 success:true; the phone drew "Hold on" because no body arrived: (c) the 35 s deadline passed, LIKELY (the cap starts after the pre-work and fires late under loop lag; the cancel tail, the persist and the network follow), or (d) a dropped network. Proof (read-only, the relay's, before GREEN): the owner's `comparisons` row 23:27-23:29Z and its `search_logs.duration_ms`: >= 35,000 = ESTABLISHED, 31,000-35,000 LIKELY; the Railway HTTP duration discriminates best. No server dependency.

### 1.4 Contract
1. api.ts:56 `COMPARE_TIMEOUT_MS = 50000`: the REST GET (:747), compareTextPair (:1057), the History GET (:515), the link POST (HomeScreen.tsx:629). Comments: api.ts:55 -> "the server cap (STREAM_HARD_CAP_SECONDS, 30 s on web) plus at least 15 s"; HomeScreen.tsx:288 "35s" -> "50s". The m18 pin (>= 3 uses) holds; cancel stays (:298).
2. A partial renders as today; only the VALUE of `results.partial.note` changes (ResultsContent.tsx:491-498; en.json:867, ar.json:864; row 1): today's words promise a tap with no handler (T7-10).
3. "Hold on" stays for no usable result: 503 TIMEOUT, a codeless 503, no answer in 50 s, a dropped network.

### 1.5 Walk
Cap 30 s plus the tail and up to 5 s of echo persist: inside 50 s. All races cut: 503 TIMEOUT, "Hold on" (true). Result gate / INC-R1 ask: today's 400 copy. Camera: a partial in a 200 `action: comparison` (120 s identify deadline). Link: ENABLE_URL_LINK_RESULT on -> 25 s server deadline (UR:144, :309-313); off with V2 off -> none (UR:314-315), so up to 50 s (L2).

## 2. C1-2: price_asof and "Last checked ..."
### 2.1 Server contract at d2f49d8b (kb_serve, kb_ingest unchanged)
- client_price_asof (kb_serve.py:128-140): ENABLE_KB_FIRST_SERVE first, then the header (<= 512 chars, comma tokens, stripped, lower-cased); read at TR:821, :1063, :1347, :1706, IR:621; accepts_asof SCS:6350.
- classify (kb_serve.py:245-342): BH / BHD / in stock / allowed source; last_seen > 300 s ahead dropped (:276-277); fresh <= 7 d; asof <= max_asof_days() (30, clamp 8..90, :102-103) only with the token (:282-288). Every KB price has `as_of` = last_seen "YYYY-MM-DDTHH:MM:SSZ" (:216-234).
- public_price_view (price_service.py:9454-9470) keeps as_of; NEW: the INC-P2 wire view copies it for the shown side (:17974, :17983). field_status (kb_ingest.py:193-207): live `fresh, as_of captured_at`; cached `stale, as_of None`.
- NEW: three readers of X-Client-Capabilities, one parse: `price_asof` (kb_serve), `price_size` (price_service.py:17533-17546; tests/test_inc_p2_price_not_lost.py:1191-1192 pins "price_asof, price_size" -> True), `vision_anthropic` (LR:467-479).

### 2.2 Contract
1. requestContext.ts:38 -> `['price_size', 'price_asof']`; header (:152-153) exactly `price_size,price_asof`; docblock :17-19 updated; never `vision_anthropic` (SD-C2).
2. In priceProvenance (fieldStatusView.ts:45-78) / renderProvenanceLine (ResultsContent.tsx:159-189), kinds 'fresh' and 'stale' take the new wording (Q4); 'listed', 'staleNoDate', 'unknown', 'none' byte-unchanged; testIDs `results-product-asof-<i>` / `-lastseen-<i>` and styles as today. days = `calendarDaysAgo(prov.dateIso, nowMs)`, a new pure export of fieldStatusView.ts: (local start of day of nowMs minus that of the date) / 86,400,000, Math.round, clamped at 0; nowMs = ResultsContent.tsx:148's Date.now() (never `new Date()` inside). The 30-day bound stays elapsed time (:70-77).
   - 0: `results.price.checkedToday` / `...TodayNoStore`; 1: `...checkedYesterday` / `...YesterdayNoStore`; >= 2: `results.price.checkedDaysAgo` / `...DaysAgoNoStore` with `{ count: days, days: formatNumber(days, { maxFraction: 0, grouping: false }), store }`; the store form when prov.store is non-null.
   - Six suffixes per family in both catalogs, equal {{vars}} per key; EN reaches only `_other`; AR `_two` (2), `_few` (3-10), `_many` (11-99).
3. results.price.asOf / asOfNoStore / lastSeen / lastSeenNoStore stay, unused (Q5).

### 2.3 Walk (never a wrong date)
KB serve off: as_of only via field_status. KB on: N 0..7 for any client, 8..30 with the token. MAX_ASOF_DAYS > 30: the phone hides a 31-90 d amount the verdict may use (SD-A2). ENABLE_FIELD_STATUS_METADATA on: live "last checked today", cached "Price checked earlier" (L11). ENABLE_PRICE_NOT_LOST: the shown side's own as_of. History: the listed line. A date up to 300 s ahead: "today".

## 3. C1-4: the photo message
### 3.1 Server answer at d2f49d8b (after CAM-2 #423)
- Consent IR:385-386 (LR:240); NEW IR:387-390 `camera_vision_gate_refuses` (LR:482-501: vision role on, decided anthropic, and V2 off or no `vision_anthropic`; log :500) raises VisionCapabilityRequiredError (LR:281-286, an LLMUnavailableError).
- Except IR:394-421: refunds :406-407; any LLMUnavailableError (the two above, OpenAIEgressStoppedError api_budget_service.py:735, the Anthropic errors LR:245-279) or a transient OpenAI failure -> 503 detail {code LLM_UNAVAILABLE, error SCS:1907-1909} (IR:416-420); else 500 (IR:421).
- Wire (EH:229-245): HTTP 503 {success false, error, code "LLM_UNAVAILABLE", request_id}: top-level code, no field / reason / detail. identifyFromImages throws {response {status 503, data that body}} (api.ts:400-411); its watchdog {code TIMEOUT, response {status 503, data {code TIMEOUT}}} (:420-426).

### 3.2 Client today (unchanged)
isCameraEngineOutage (failureClassification.ts:79-95) -> 'engine_unavailable' (ResultsScreen.tsx:399-403): engine copy, ONE Back button (:881-898). The new message keys on the server answer, never the native version.

### 3.3 Contract
1. failureClassification.ts: new `isCameraVisionUnavailable(err)`: `err?.response?.status === 503` and `(data?.code ?? data?.detail?.code) === 'LLM_UNAVAILABLE'` (data = err?.response?.data); the camera catch (ResultsScreen.tsx:376-412) checks it after USAGE_LIMIT (:382-386), before isCameraEngineOutage (:399) -> `setLoadError('photo_unavailable')` (the union :164-176 gains it).
2. In the empty state (:804-902): container testID `results-photo-unavailable-state`; title `results.photoUnavailable.title`; body `results.photoUnavailable.body`; primary button (styles.emptyStateCta) testID `results-photo-type-names`, label `common.typeNames`; secondary button testID `results-empty-back`, label `common.back`, onPress goBack(); header back (:831) unchanged; every other loadError byte-identical.
3. Type the names: `requestHomeMode('type')`, then `navigation.popTo('Main')`. New services/homeEntryIntent.ts (module state, no storage): `requestHomeMode(mode: 'type'): void`, `consumeHomeMode(): 'type' | null` (once, then cleared). popTo, not goBack: the stack is Main, ScanCamera, Results (ScanCameraScreen.tsx:306-308); native-stack 7 (installed 7.15.0); `Main: undefined` (types/types.ts:608). HomeScreen: a focus effect (as :198 / :314) calls consumeHomeMode() and on 'type' setInputMode('type') (:129). Nothing carried over; a second focus does nothing.

### 3.4 Walk
OpenAI vision with egress stopped, Claude vision with V2 off, V2 on with this 1.0.0 client, a 1.0.1 client in a real outage: the 503, the message, true each time. Consent < 3: L7. 500, 502, 200 bodies (comparison_failed IR:840): unchanged (C2).

## 4. T7-04 link words (A-4, A-5) and T7-08
### 4.1 Server answers at d2f49d8b (after INC-U1 #417, INC-U1b #425)
- UR:524-577 (POST; GET :580): SSRF 400 (:559-560) = BAD_REQUEST (EH:24-35); V2-only NOT_PRODUCT_PAGE for url_too_long / same_url / a page class (UR:152-175, :562-567); consent 503 (:280-285); 429s (:104-107, :130-138).
- ENABLE_URL_LINK_RESULT on: the per-page path under 25 s (UR:305-313, UX:1808-1811); expiry -> 503 TIMEOUT (UR:206-209).
- Per link (UX:1204-1235): timeout, fetch errors, blocked, redirect cap, a challenge page, 401 / 403 / 429, other non-2xx, undecodable -> STORE_UNREADABLE; 404 / 410 -> UNRESOLVED_PRODUCT not_found (A-5); unreadable pages -> UNRESOLVED_PRODUCT (UX:1494-1516). Pair (UX:1833-1857, :2140-2158): all coded -> one code by precedence; any codeless -> "Could not extract both products".
- Exit (UR:327-361): refund first; a B4 code -> 400 {code, error, field, reason} (UR:178-186, :349-353); codeless -> BAD_REQUEST. Wire (EH:220-254): {success false, error, code, request_id}; field / reason only with ENABLE_URL_MODE_V2 on (:246-254), so with V2 off (the flip note's mix) the client maps by code. INC-U1b changed only History.

### 4.2 Contract (link path only; text path byte-unchanged)
- errorCopy.ts: new `linkErrorKey(code)`: STORE_UNREADABLE -> `home.errors.link.storeUnreadable`; NOT_PRODUCT_PAGE -> `...notProductPage`; UNRESOLVED_PRODUCT -> `...unresolved`; BAD_REQUEST or no code (null, undefined, '') -> `...generic`; else null.
- HomeScreen: the 200 success:false arm (:651-660, after CONTENT_UNAVAILABLE and the timeout check) and the catch's last arm (:686-704): if linkErrorKey(code) is non-null, `Alert.alert(t('home.errors.link.title'), t(key), [{ text: t('common.cancel'), style: 'cancel' }, { text: t('common.typeNames'), onPress: () => setInputMode('type') }])`; else today's call. CONTENT_UNAVAILABLE, USAGE_LIMIT and TIMEOUT keep their branches.
- Words: rows 21-25 (row 22 is F9); copy-policy clean; no time named.

### 4.3 T7-08
ResultsContent.tsx:207 goes (formatPrice returns `base` always); the caption (:445-455, `results-product-converted-<i>`) stays the one label; withSize wraps the bare amount (GATE_INC_C1A CC-2, L-2). Sources: price_service.py:10636 ff., links UX:2058-2062.

### 4.4 Walk
Flag off: BAD_REQUEST -> generic; a hung compare -> "Hold on" at 50 s. Flag on, V2 off: rows 22 / 24; mixed -> generic; 25 s -> "Hold on". V2 on: SD-L2. Result gate, fragrance gate, consent, 429s, AUTH_REQUIRED (TR:332-357): today's copy.

## 5. Addendum A-1..A-5
- A-1 Volume "100" vs "100 ml": SERVER DEPENDENCY SD-V1 (extraction lane). The client prints the raw value (ResultsAccordion.tsx:575-585); extract_specs copies the subtype `volume_ml` number (product_type_router.py:98-100) into `volume` without its unit (extraction_service.py:1651-1668, aliases :254-257) while other paths ship "100 ml"; RB:753-755 tidies it for the variant tag only. A client normaliser would guess the unit (schema "ml/oz", :222): not proposed (Q14).
- A-2 "107 reviews" vs 16,000: SERVER DEPENDENCY SD-V2 (verdict prompt lane). Pros are model text (SCS:4941-4948) written from the product JSON (extraction_service.py:2674-2681) with its own figure (total_reviews :985-986); the reviews section shows review_count (RB:2113; ResultsAccordion.tsx:431-436). Fix: one count in the payload, or none in pros.
- A-3 a con about our data: SERVER DEPENDENCY SD-V3 (verdict prompt lane). The default prompt demands cons; the dark ENABLE_VERDICT_PROMPT_TRUTH twin (prompt_personalities.py:83-86; extraction_service.py:1102-1117) forbids data-gap cons; the canary regex (:1153) filters nothing; with no wire marker a client filter would be text matching. Its flag state is not in the notes this spec may read.
- A-4 STORE_UNREADABLE: IN (4.2, row 22, the button). A-5 UNRESOLVED_PRODUCT not_found: IN (row 24 holds for every reason; the reason travels only with V2, L14).

## 6. OWNER READ: every new or changed user-facing string
EN literal; AR = quoted ASCII plus bracketed hex code points (U+ and leading zeros dropped; 20 space, 60C Arabic comma), decoded with String.fromCodePoint. INC_C1_V2_STRINGS.json beside this file is a machine copy; the table rules. Row 1 changes a value (the draft's words); row 22 is new (F9); EN rows 7-8, 13-14 take a literal (correction a); the rest are the draft's bytes.

| # | key | EN | AR (code points) | read |
|---|---|---|---|---|
| 1 | `results.partial.note` | Some details did not arrive in time, so a few may be missing. | [644 645 20 62A 635 644 20 628 639 636 20 627 644 62A 641 627 635 64A 644 20 641 64A 20 627 644 648 642 62A 20 627 644 645 646 627 633 628 60C 20 644 630 627 20 642 62F 20 64A 646 642 635 20 628 639 636 647 627 2E] | [NATIVE READ] |
| 2 | `results.price.checkedToday` | {{store}}, last checked today | "{{store}}" [60C 20 622 62E 631 20 62A 62D 642 642 20 627 644 64A 648 645] | [NATIVE READ] |
| 3 | `results.price.checkedTodayNoStore` | Last checked today | [622 62E 631 20 62A 62D 642 642 20 627 644 64A 648 645] | [NATIVE READ] |
| 4 | `results.price.checkedYesterday` | {{store}}, last checked yesterday | "{{store}}" [60C 20 622 62E 631 20 62A 62D 642 642 20 623 645 633] | [NATIVE READ] |
| 5 | `results.price.checkedYesterdayNoStore` | Last checked yesterday | [622 62E 631 20 62A 62D 642 642 20 623 645 633] | [NATIVE READ] |
| 6 | `results.price.checkedDaysAgo_zero` | {{store}}, last checked {{days}} days ago | "{{store}}" [60C 20 622 62E 631 20 62A 62D 642 642 20 642 628 644 20] "{{days}}" [20 64A 648 645] | [NATIVE READ] |
| 7 | `results.price.checkedDaysAgo_one` | {{store}}, last checked 1 day ago | "{{store}}" [60C 20 622 62E 631 20 62A 62D 642 642 20 642 628 644 20 64A 648 645 20 648 627 62D 62F] | [NATIVE READ] |
| 8 | `results.price.checkedDaysAgo_two` | {{store}}, last checked 2 days ago | "{{store}}" [60C 20 622 62E 631 20 62A 62D 642 642 20 642 628 644 20 64A 648 645 64A 646] | [NATIVE READ] |
| 9 | `results.price.checkedDaysAgo_few` | {{store}}, last checked {{days}} days ago | "{{store}}" [60C 20 622 62E 631 20 62A 62D 642 642 20 642 628 644 20] "{{days}}" [20 623 64A 627 645] | [NATIVE READ] |
| 10 | `results.price.checkedDaysAgo_many` | {{store}}, last checked {{days}} days ago | "{{store}}" [60C 20 622 62E 631 20 62A 62D 642 642 20 642 628 644 20] "{{days}}" [20 64A 648 645 64B 627] | [NATIVE READ] |
| 11 | `results.price.checkedDaysAgo_other` | {{store}}, last checked {{days}} days ago | "{{store}}" [60C 20 622 62E 631 20 62A 62D 642 642 20 642 628 644 20] "{{days}}" [20 64A 648 645] | [NATIVE READ] |
| 12 | `results.price.checkedDaysAgoNoStore_zero` | Last checked {{days}} days ago | [622 62E 631 20 62A 62D 642 642 20 642 628 644 20] "{{days}}" [20 64A 648 645] | [NATIVE READ] |
| 13 | `results.price.checkedDaysAgoNoStore_one` | Last checked 1 day ago | [622 62E 631 20 62A 62D 642 642 20 642 628 644 20 64A 648 645 20 648 627 62D 62F] | [NATIVE READ] |
| 14 | `results.price.checkedDaysAgoNoStore_two` | Last checked 2 days ago | [622 62E 631 20 62A 62D 642 642 20 642 628 644 20 64A 648 645 64A 646] | [NATIVE READ] |
| 15 | `results.price.checkedDaysAgoNoStore_few` | Last checked {{days}} days ago | [622 62E 631 20 62A 62D 642 642 20 642 628 644 20] "{{days}}" [20 623 64A 627 645] | [NATIVE READ] |
| 16 | `results.price.checkedDaysAgoNoStore_many` | Last checked {{days}} days ago | [622 62E 631 20 62A 62D 642 642 20 642 628 644 20] "{{days}}" [20 64A 648 645 64B 627] | [NATIVE READ] |
| 17 | `results.price.checkedDaysAgoNoStore_other` | Last checked {{days}} days ago | [622 62E 631 20 62A 62D 642 642 20 642 628 644 20] "{{days}}" [20 64A 648 645] | [NATIVE READ] |
| 18 | `results.photoUnavailable.title` | Photo compare is not available right now | [627 644 645 642 627 631 646 629 20 628 627 644 635 648 631 20 63A 64A 631 20 645 62A 627 62D 629 20 62D 627 644 64A 64B 627] | [NATIVE READ] |
| 19 | `results.photoUnavailable.body` | You can type the two names instead. | [64A 645 643 646 643 20 643 62A 627 628 629 20 627 633 645 64A 20 627 644 639 637 631 64A 646 20 628 62F 644 64B 627 20 645 646 20 630 644 643 2E] | [NATIVE READ] |
| 20 | `common.typeNames` | Type the names | [627 643 62A 628 20 627 644 623 633 645 627 621] | [NATIVE READ] |
| 21 | `home.errors.link.title` | Let's try another way | [644 646 62C 631 651 628 20 637 631 64A 642 629 20 623 62E 631 649] | [NATIVE READ] |
| 22 | `home.errors.link.storeUnreadable` | This shop's page did not open for us. You can type the two names instead. | [635 641 62D 629 20 647 630 627 20 627 644 645 62A 62C 631 20 644 645 20 62A 64F 641 62A 62D 20 644 62F 64A 646 627 2E 20 64A 645 643 646 643 20 643 62A 627 628 629 20 627 633 645 64A 20 627 644 639 637 631 64A 646 20 628 62F 644 64B 627 20 645 646 20 630 644 643 2E] | [NATIVE READ] |
| 23 | `home.errors.link.notProductPage` | That link opens a shop page, not a product. Open the perfume's own page and copy its link. | [647 630 627 20 627 644 631 627 628 637 20 64A 641 62A 62D 20 635 641 62D 629 20 645 62A 62C 631 20 648 644 64A 633 20 635 641 62D 629 20 645 646 62A 62C 2E 20 627 641 62A 62D 20 635 641 62D 629 20 627 644 639 637 631 20 646 641 633 647 20 648 627 646 633 62E 20 631 627 628 637 647 627 2E] | [NATIVE READ] |
| 24 | `home.errors.link.unresolved` | We did not find a perfume on that page. Copy the link of the perfume's own page. | [644 645 20 646 62C 62F 20 639 637 631 64B 627 20 641 64A 20 62A 644 643 20 627 644 635 641 62D 629 2E 20 627 646 633 62E 20 631 627 628 637 20 635 641 62D 629 20 627 644 639 637 631 20 646 641 633 647 2E] | [NATIVE READ] |
| 25 | `home.errors.link.generic` | One of those links did not open for us. Paste a link from another shop, or type the two names. | [623 62D 62F 20 627 644 631 627 628 637 64A 646 20 644 645 20 64A 64F 641 62A 62D 20 644 62F 64A 646 627 2E 20 627 644 635 642 20 631 627 628 637 64B 627 20 645 646 20 645 62A 62C 631 20 622 62E 631 60C 20 623 648 20 627 643 62A 628 20 627 633 645 64A 20 627 644 639 637 631 64A 646 2E] | [NATIVE READ] |

## 7. RED rows
### 7.0 Rules
- Files SmartCompareApp/__tests__/c1/: holdOn.c1.test.tsx, lastChecked.c1.test.tsx, cameraLink.c1.test.tsx, strings.c1.test.ts; ASCII sources, Arabic from section 6. F1 as above; new elements queried with queryBy* + expect, so each base failure is an assertion.
- F4: NOW = new Date(2025, 6, 15, 12, 0, 0).getTime(); asOf(n) = new Date(2025, 6, 15 - n, 12, 0, 0).toISOString(); Date.now spied to NOW (c1a); the 2025 NOW fails a helper that reads the device clock.
- Models: c1a/sizeLabel.c1a, api.networkMatrix.m18, HomeScreen.errorCopy.a11, screens/camera.engineUnavailable.s69, i18n/referralExpiryPlurals.w414.

### 7.1 holdOn.c1.test.tsx (real services/api, axios mocked, fake timers)
Harness: the m18 mocks (axios.create -> one instance; certificatePinning; authService with getSavedUser; expo-image-manipulator; expo/fetch; sentry) plus every a11 Home mock except services/api. get / post by url: '/api/v1/text/compare' -> DEADLINE(config, serverMs, response) = resolve at serverMs or reject Object.assign(new Error('timeout'), {code: 'ECONNABORTED'}) at config.timeout, first wins; '/api/v1/url/compare' -> resolve {data: PARTIAL}; else {data: {}}. PARTIAL = {success true, 'Chanel No 5' / 'Dior Sauvage' in products and overview.products, BHD 77.94 at noon.com and 47 at store-b.example.com, overview.winner, metadata {partial true, partial_stage 'post_gather'}}.
- H1: COMPARE_TIMEOUT_MS === 50000; streamComparison(pair).subscribe(cbs) -> get('/api/v1/text/compare', objectContaining({timeout: 50000})); getComparison('id') -> get(path, {timeout: 50000}); Home link submit (home-mode-link, shell onSubmit two https links) -> post('/api/v1/url/compare', anything, objectContaining({timeout: 50000})). Base: 35000.
- H2 (the 02:27 shape): DEADLINE(config, 36000, {data: PARTIAL}); subscribe({onComplete, onError}); advance 36,500 ms -> onComplete once with PARTIAL, no onError. Base: rejected at 35 s -> onError.
- H3: HomeScreen; press home-mode-type; act(shell onSubmit('Chanel No 5', 'Dior Sauvage')); advance 37,000 ms -> navigate('Results', {result: PARTIAL}), no Alert. Base: Alert(EN common.error, EN home.errors.timeout).
- H5 (pin): an axios 503 {success false, code TIMEOUT}, and a get that never settles (advance 60,000 ms): both Alert(EN common.error, EN home.errors.timeout), two arguments.

### 7.2 lastChecked.c1.test.tsx (ResultsContent, real i18next)
Harness: c1a's component mocks and makeProps; useTranslation -> {t: inst.t.bind(inst), i18n: {language: mockLang}}, inst = an i18next.createInstance() set up as in referralExpiryPlurals, changeLanguage(mockLang) per render. price(n, x) = {amount 58.11, currency 'BHD', retailer 'noon.com', source_method 'page_scrape', as_of asOf(n), ...x}; expected = the row with {{store}} noon.com and {{days}} the ASCII figure.
- D1: jest.isolateModules, deviceFingerprint -> null, getSavedUser -> null (c1a C1): CLIENT_CAPABILITIES deep-equals ['price_size', 'price_asof']; buildContextHeaders({}) X-Client-Capabilities === 'price_size,price_asof', no 'vision_anthropic'; mergeContextHeaders keeps it. Base: ['price_size'].
- D2: n = 0, 1, 2, 3, 10, 11, 29, EN and AR; text of results-product-asof-0 (n <= 7) or -lastseen-0 (n >= 8): EN rows 2, 4, then 11; AR rows 2, 4, 8 (n 2), 9 (n 3, 10), 10 (n 11, 29). Base: "as of" / "last seen".
- D3: as_of 2025-07-14 23:50, NOW 2025-07-15 00:10 -> row 4; as_of 2025-07-15 00:10, NOW 23:50 that day -> row 2. Base: the as-of line.
- D4 (F3): NOW 2025-07-15 23:58, as_of 2025-07-16 00:02 -> row 2, no '-' or digit. Base: the as-of line.
- D5 (pin, recorded at base): 31 d -> results-product-price-honest-0, no asof / lastseen id; resultOrigin 'stored' + asOf(2) -> results-product-listed-0 = listedOn; live field_status [{price: {state 'stale', as_of null}}, null] without price.as_of -> results-product-checked-0 = checkedEarlier.
- D6: no retailer, n = 0, 1, 3 -> rows 3, 5, then EN row 17 / AR row 15. Base: the NoStore as-of line.
- D7: no price.as_of, field_status [{price: {state 'fresh', as_of asOf(2)}}, null] -> EN row 11 (2), AR row 8. Base: the as-of line.
- H4: metadata.partial true, two shown BHD prices: price lines as today; results-content-partial-note = row 1 (EN, AR), no 'tap', no AR [627 636 63A 637]. Base: today's note.
- X1: price {7.14, BHD, converted_usd, noon.com}, no as_of: card texts hold results.convertedUSD exactly once, the price line is exactly "7.140 BHD", results-product-converted-0 present; with size_ml 100 the line is results.price.withSize of "7.140 BHD" and "100", label once; AR likewise. Base: the label twice.
- P1(a)(b) (pin, goldens at base): two genuine undated BHD prices, both cards, EN and AR; a stored body with as_of.

### 7.3 cameraLink.c1.test.tsx (ResultsScreen and HomeScreen, one module registry)
Harness: ONE services/api mock (default {post: mockApiPost}, healthCheck, streamComparison, trackEvent, trackEvents, submitFeedback, getComparison, identifyFromImages, COMPARE_TIMEOUT_MS, parseApiError = the a11 copy plus api.ts:1139-1144's reason read); the s69 camera and a11 Home mocks; usageService keyed on code USAGE_LIMIT; react-i18next = c1a's catalog t with mockLang. Focus: useFocusEffect (mocked @react-navigation/native) keeps a ref'd runner in a Set `mockFocus` (run on mount, dropped on unmount); fireFocus() = act(() => mockFocus.forEach((f) => f())). Camera navigation {goBack, navigate, setOptions, popTo} jest.fns, route vision_products ['file://a.jpg', 'file://b.jpg'], then advance 1,500 ms.
- C1: render HomeScreen first (scan mode); identifyFromImages rejects thrownIdentify(503, {success false, error 'x', code 'LLM_UNAVAILABLE', request_id 'r'}). Expect results-photo-unavailable-state; rows 18, 19 as title, body; results-photo-type-names labelled row 20; results-empty-back labelled common.back; no engine title / body, no results-timeout-state. Press results-photo-type-names: popTo once with 'Main', no goBack. fireFocus(): home-mode-type accessibilityState {selected: true}, home-mode-scan {selected: false}, mock-two-input-shell mode 'text'. Press home-mode-scan, fireFocus(): scan stays selected. Press results-empty-back: goBack. Again with {detail: {code 'LLM_UNAVAILABLE', error}}, and once in AR. Base: the engine state; the first expect fails.
- C2 (pin): thrown 500 SERVER_ERROR, bare 500, 502 {error}, resolved 200 {success false, action 'comparison_failed', code 'LLM_UNAVAILABLE'} -> the engine state, ONE button (common.back), none of the three new testIDs; thrown bare 503 {}, the watchdog shape, 503 {code 'FEATURE_DISABLED'} -> results-timeout-state; err.code 'USAGE_LIMIT' -> navigate('Paywall', {initialUsage: detail}).
- L1: link submit as H1. STORE_UNREADABLE, NOT_PRODUCT_PAGE, UNRESOLVED_PRODUCT, BAD_REQUEST on both arms (thrown axiosError(400, {success false, code, error 'prose', request_id}); 200 {data: {success false, code, error}}) and codeless on both (axiosError(400, '<html>x</html>'); {data: {success false, error}}): Alert.alert(EN link.title, EN <4.2 key>, [{text: EN common.cancel, style: 'cancel'}, {text: EN common.typeNames, onPress: expect.any(Function)}]); act(buttons[1].onPress()) -> home-mode-type selected; one AR pass. Base: Alert(common.error, home.errors.comparison), two arguments.
- L2 (pin, recorded at base): link TIMEOUT 503, USAGE_LIMIT 429 (Paywall), CATEGORY_NOT_LIVE 400, LLM_UNAVAILABLE 503, RATE_LIMITED 429 + retry_after_seconds 5, INSUFFICIENT_DATA 400 + reason same_identity, AUTH_REQUIRED 401, a codeless edge 502: today's Alert (two arguments) or navigation; text path onError axiosError(400, {code 'BAD_REQUEST'}) -> Alert(EN common.error, EN home.errors.comparison).
- P1(c)(d) (pin, goldens at base): text-path onError [title, body] for TIMEOUT 503, LLM_UNAVAILABLE 503, INSUFFICIENT_DATA + reason, RATE_LIMITED + retry_after_seconds; the camera 500 and 200 comparison_failed screens (texts and testIDs under results-empty-state).

### 7.4 strings.c1.test.ts (catalogs)
- S1: the 24 new keys and results.partial.note equal section 6 (EN in en.json, decoded AR in ar.json). Base: missing keys, today's note.
- C3 (F5): rows 18-25: control (non-empty string in both catalogs); no digit (ASCII, U+0660-0669, U+06F0-06F9); EN not /update|soon|shortly|next|minute|hour/i; AR none of [62A 62D 62F 64A 62B], [642 631 64A 628], [628 639 62F 20 642 644 64A 644]. Base: the control fails.
- P2 (pin, always green): equal key sets; six forms per AR family, at least _one and _other in EN; equal {{vars}} per key; no copy-policy hit.

### 7.5 Mutants (each killed)
M1 35000 kept (H1-H3). M2 partial to onError (H2, H3). M3 token missing or joined with "; " (D1). M4 floor, M4b round of elapsed / day (D3). M5 no clamp (D4). M6 new wording on 'listed' (D5). M7 photo state on any outage code (C2). M8 on any 503 (C2). M9 link map on the text path (L2). M10 inline suffix kept, M10b caption dropped (X1). M11 button without the intent (C1). M12 AR few / many swapped (D2). M13 sticky intent (C1). M14 goBack for popTo (C1). M15 AUTH_REQUIRED to generic (L2). M16 device clock (D2). M17 EN `_two` with {{days}} (P2).

## 8. Stay-green, moved pins, comm set, bundle
### 8.1 Expected moved pins (quote each, never weaken; any other failure is a finding)
- price_size -> price_size,price_asof: s81_08/requestHeaders (B9 :453-457, header objects), s81_08/cameraHeaders, s81_08/sseHeaders, api.cameraAuthRetry.u13c, c1a C1 (:321, :323, :327; :324 `.not.toMatch(/price_asof/)` yields to the exact value, stronger).
- api.getComparison.comparisonId.m18:79 35000 -> 50000 (Home suites mock the constant, stay).
- screens/camera.engineUnavailable.s69, both cases that throw 503 LLM_UNAVAILABLE: :160 (the R4 envelope) -> the photo state; :260-268 (the watchdog control's anchor) keeps an anchor that exists (the photo-state container, or ENGINE_TITLE via a thrown 500).
- HomeScreen.arabicAlerts.w311 (c2) :287-304 -> AR link.generic under AR link.title with the buttons (no-Latin / no "Could not" asserts stay); a11's URL cases stay.
- s11/honestUnknowns E3r :412-441 (plural forms, same testIDs; its t may become plural-aware) and P1 :566-568 (bare amount, label once).
- c1a C4 :415-434 and P1 converted golden rows :525, :527 (one label).
- Leaf counts 1014 -> 1038: s11/copy.s11:186-191, s11e/arCopy.s11e:132-140.
### 8.2 legal_v3 (Q7, CC-8)
tests/test_s81_12_legal_v3.py:239-242: prove that the 1038 keys minus the 24 new ones hash (sha256 of the sorted names, newline-joined) to the recorded BASE_I18N_NAMESET_SHA256, then record 1038 and the new hash with a comment naming INC-C1.
### 8.3 GREEN comm set
- Client: the FULL jest suite in ONE process (`npx jest --ci --runInBand`; only the 4 accepted nativeBundle.w37 nodes may fail); each c1 file paired --runInBand with s81_08/requestHeaders both orders; `tsc --noEmit` 0 errors; eslint on the changed files and CI's `eslint 'src/**/*.{ts,tsx}'` (0 errors, no new warning).
- Backend (no app/ change): every `.py` hit of `git grep -l SmartCompareApp -- tests/` at the GREEN head (30 at d2f49d8b) in one pyt.py run, waiting outside the runner. Readers of this unit's files among them: test_s81_12_legal_v3, test_s81_12_gate_rows, test_dimension_label_catalog_parity_w414, test_register_benefits_parity_s69, test_legal_docs_u8* (catalogs); test_events_allowlist_superset, test_s81_sf1_surfaces_be, test_inc_sec1_app_user_access, test_security_regression, test_migration_037_security_definer_grants (src scans); test_s81_sf1_gate_rows (HomeScreen.tsx); test_timeout_partial_integration; test_comparison_id_echo.
### 8.4 Adversaries (Q9)
A1 correctness: sections 1-4 against the GREEN head, every walk. A2 words and RTL: section 6 against both catalogs, the RTL render of each new line, the P1 goldens.
### 8.5 Bundle rule
`git diff --name-only 2e7a1229 <M> -- SmartCompareApp` minus `__tests__` = exactly src/services/{api.ts, requestContext.ts, fieldStatusView.ts, errorCopy.ts, failureClassification.ts, homeEntryIntent.ts (new)}, src/components/results/ResultsContent.tsx, src/screens/{ResultsScreen.tsx, HomeScreen.tsx}, src/i18n/{en.json, ar.json} (11 files).

## 9. Server dependencies (none built here)
SD-H1 (optional) the REST route keeps the credit and saves a result the phone never got (TR:1093-1097, :1141-1165). SD-H2 STREAM_HARD_CAP_SECONDS <= 30. SD-A1 ENABLE_KB_FIRST_SERVE is the owner's window (dated prices up to 30 days; clean data first). SD-A2 KB_FIRST_SERVE_MAX_ASOF_DAYS unset or <= 30. SD-C1 CLOSED by CAM-2 (IR:387-390, LR:281-286); new camera refusals keep this envelope. SD-C2 the 1.0.0 update never declares vision_anthropic (LR:462-479). SD-L2 ENABLE_URL_MODE_V2 stays off until a client words same_url / url_too_long (UR:152-175). SD-V1..V3: section 5.

## 10. Stated limits
L1 cause (c) LIKELY until the proof read; a dropped network still shows "Hold on". L2 a capped compare holds the loader about 40 s, a hung server 50 s; cancel stays. L3 the note cannot name the missing details. L4 "Last checked" follows the phone's clock and zone. L5 item 2 shows nothing new until ENABLE_KB_FIRST_SERVE or ENABLE_FIELD_STATUS_METADATA is on. L6 the camera entry stays; the message follows the photos. L7 (F10) a consent-below-3 account gets the message, yet typing is refused for it too (SCS:4353-4355). L8 refused shops read the generic sentence until ENABLE_URL_LINK_RESULT (or V2) sends their codes; so does a codeless client-side link failure. L9 no bottle size until INC-P2. L10 the old keys stay unused. L11 (F8) P1 assumes ENABLE_FIELD_STATUS_METADATA off on web; if on, live cards read "last checked today". L12 rows 22 / 25 name one shop / one link; with V2 off the phone cannot tell which failed. L13 SD-L2. L14 not_found reads row 24, silent that the page is gone. L15 Type the names keeps the shell's own type-mode text. L16 A-1..A-3 stay until their server work ships.

## 11. Open questions
Q1 (relay) the proof read. Q6 (relay) are INC-C1a's bytes on the phones. Q10 answered by code (relay to close). Q11 F13 read as the photo state only. Q12 the generic link sentence for BAD_REQUEST and codeless only. Q13 SD-L2: hold V2 off (this spec) or word same_url now. Q14 A-1: no client normaliser. Q15 (relay) is ENABLE_FIELD_STATUS_METADATA off on web.

## 12. INC-C1b seed (draft 11, unchanged)
T7-09 one picture-load retry (ProductImage.tsx:73-103) plus a host-only breadcrumb; T7-11 "Saved on <date>" on a History result; EN / AR [NATIVE READ]; no server change.
