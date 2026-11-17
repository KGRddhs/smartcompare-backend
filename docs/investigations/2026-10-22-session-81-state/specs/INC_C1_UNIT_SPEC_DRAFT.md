# INC-C1 OTA-BATCH: unit spec DRAFT (S96 spec author, Opus 5.5, 2026-11-17)

Base: origin/main `5cd93c6aaa4e80e4b0ab36a43e6fa1f657d797c9` (fetched 2026-11-17, sc-s96-c1a, git plumbing only). `git diff --name-only 2e7a1229 origin/main -- SmartCompareApp` is EMPTY: no client byte has changed since INC-C1a (#412). A CLIENT unit for an over-the-air update to build 1.0.0: no app.json, package, lock or native change; none of S97's files (usage_service.py, url_extraction_service.py, url_routes.py, app.json) is touched. Cites: file:line at 5cd93c6a. ESTABLISHED = read in code or a quoted log line; LIKELY = best reading. Abbreviations: SCS = app/services/structured_comparison_service.py, RB = app/services/response_builder.py, TR = app/api/text_routes.py, IR = app/api/image_routes.py, UR = app/api/url_routes.py; client paths are under SmartCompareApp/src.

## 0. Summary and proposed split
- **INC-C1 core (M, client-only):** (1) "Hold on": the 35 s phone deadline cuts a 30 s-capped compare before its partial arrives; raise it, honest partial note (absorbs T7-10); (2) `price_asof` + "Last checked N days ago" (EN + AR plurals); (4) the honest camera message on the vision-failure answer with "Type the names"; T7-04 link wording per refusal code (INC-U1's flip note defers it here); T7-08 the converted label once.
- **Item 3 (R3 REC-4, the bottle size) DROPPED** (section 5). **INC-C1b (S, SAFE):** T7-09 and T7-11 (section 11). Out of scope: the INC-R1 picker.
- **No server dependency for any core item** (later units: section 8).

## 1. Item 1: why the phone showed "Hold on" over a real partial (diagnosis first, to the end)

### 1.1 What the phone showed, and the only client paths that draw it
The owner's dialog = an `Alert` with title `common.error` "Hold on — give it another tap." (en.json:379; ar.json:376 "لحظة — جرّب الضغط مرّة ثانية.") and body `home.errors.timeout` "Still gathering prices — give it another tap in a moment." (en.json:120; ar.json:117). ESTABLISHED (the Results-screen timeout state uses other words, `results.timeout.title/body`, en.json:864-865, and is not a dialog).

The text compare transport: `features.ENABLE_EXPO_FETCH_SSE` = `ENABLE_EXPO_FETCH_SSE_DEFAULT = false` (config/features.ts:52, :118-120; the override is test-only, :58-61), so `streamComparison` makes ONE REST call and never opens the stream (services/api.ts:787-794). The REST call: `api.get('/api/v1/text/compare', { params, signal, timeout: COMPARE_TIMEOUT_MS, ...withRequestContext })` (api.ts:742-752) with `COMPARE_TIMEOUT_MS = 35000` (api.ts:56). Both constants date from 2026-09-02 (1df95b02, 7c058424), before any published bundle. ESTABLISHED.

Every route to the dialog (ESTABLISHED, each arm read):
- api.ts:753-756: `success: true` (full OR the D1 partial) -> `onComplete` -> HomeScreen.tsx:479-485 `increment()` + `navigateToResultsWithFloor`. A success:true partial never reaches an Alert.
- api.ts:757-768: `success: false` -> `onError` (status 200, `{code, error}`); api.ts:770-773: a thrown axios error (not an abort) -> `onError`.
- HomeScreen.tsx:527 `parseApiError`; HomeScreen.tsx:543-545: `parsed.code === 'TIMEOUT'` -> `Alert.alert(t('common.error'), t('home.errors.timeout'))` = THE DIALOG.
- `parseApiErrorBase` gives TIMEOUT for a body code TIMEOUT / STREAM_TIMEOUT or a codeless 503 (api.ts:1164-1178), and for NO response with ECONNABORTED / ETIMEDOUT / ERR_NETWORK: the axios deadline or a dropped network (api.ts:1187-1194).
- The twin arm HomeScreen.tsx:504-508 (onComplete with success:false; `friendlyErrorTitleKey('TIMEOUT')` = `common.error`, errorCopy.ts:32-37) is unreachable on REST (api.ts:753-756) and on the stream (api.ts:847-860).

So the dialog means exactly one of: (a) the server answered success:false TIMEOUT (a 503, below), (b) a codeless 503, (c) no response within 35 s (ECONNABORTED), (d) the network dropped (ERR_NETWORK).

### 1.2 What the server did at 02:27 and the fields of the body it built
- The quoted log line (RELAY_RESUME_2026-11-16.md section 00, 02:20-02:45, production 5cd93c6a, 23:27-23:28Z): `[L2.7] compare_from_text hard-cap 30.0s ... returning best-available PARTIAL (success:true)`. It is the REST format string SCS:4335-4337 (the stream's tail partial logs `[stream] full-stream deadline`, SCS:5157), so the request was the REST GET. "30.0" is `STREAM_HARD_CAP_SECONDS` formatted `%.1f`; the code default is 25.0 (SCS:1786), so web carries 30 in its environment. ESTABLISHED by the quoted line.
- The cap: `asyncio.wait_for(self._compare_from_text_impl(...), timeout=STREAM_HARD_CAP_SECONDS)` (SCS:4298-4319), armed at `_t0 = time.time()` (SCS:4296), AFTER the route's own pre-work and the entry guards (the openai preflight SCS:4274, the spend breaker's Redis read SCS:4286-4288, the consent check SCS:4293). On timeout (SCS:4327): `elapsed = time.time() - _t0` (SCS:4328, measured after wait_for has cancelled the inner task and waited for it), `_late_image_drain_now()` (SCS:4329, synchronous, SCS:6114-6123), then `_partial_has_usable_data()` (SCS:3771) -> `_build_partial_response(elapsed_seconds=elapsed)` (SCS:3888-4018) -> `return partial` (SCS:4339). Not raised: success:false TIMEOUT exists only when there is NO usable data (SCS:4350-4393), and the log says PARTIAL, so arm (a) is excluded. ESTABLISHED.
- The partial body (`build_comparison_response`, the full-response shape, SCS:3970-4018): `success: true`; products and prices from `_partial_product_data or _early_specs_buffer_list()` (SCS:3911) through `public_price_view` (RB:1951); `metadata.partial: true` (SCS:3999); `metadata.partial_stage` gather / post_gather / scoring / verdict (SCS:4001, :3872-3886); `metadata.category_used` (SCS:4002); `metadata.elapsed_ms` / `elapsed_seconds` (RB:2098-2099); `metadata.timestamp` (RB:2110, naive); scores only if landed or under ENABLE_HONEST_PARTIAL_SCORING (SCS:3919-3926); a deterministic verdict when scores exist (SCS:3962-3968); the freshness notice (SCS:4016). The route returns it unchanged (TR:1061-1168): no refund, `log_search` with `duration_ms` = route entry (TR:1002) to compare return (TR:1061), the save fire-and-forget (TR:1151-1159; an awaited bounded insert under ENABLE_COMPARISON_ID_ECHO, TR:1136-1144). ESTABLISHED.
- The stream twin (unreachable on phones): `_emit_stream_deadline_partial` (SCS:5145-5163) yields the same partial; `dispatchTerminal` sends success:true to `onComplete` (api.ts:861-862). No client branch on either transport maps a success:true partial to "Hold on". ESTABLISHED.

### 1.3 The cause
The server answered 200 success:true; the phone shows "Hold on" for a 200 only when the body never reached it: (c) or (d). **LIKELY (c): the 35 s deadline expired before the capped body arrived.** The 30 s cap starts after the route's pre-work (auth, the gate's Redis budget read category_gate.py:643, preferences, `consume_comparison_credit` TR:1028, the spend breaker's Redis read with a 2.5 s fail-open bound); it fires late when the loop stalls (FINDINGS row 14, ESTABLISHED: "every 5 s cancel fired 0.6 to 1.7 s late", loop_lag_max_ms 2785; 03:21 logged a breaker Redis timeout, lag 2649 ms); wait_for waits for the cancelled work; then serialisation and the network. incident-2026-11-11/T1_trace.md section 1 measured the phone 2 to 3.5 s past the server's elapsed on UNcapped runs. The 02:27 run was the worst kind (a used-up first key, serper_shopping 14.4 s, race timeouts everywhere); E0's slowest returned compare was 30,438 ms (T7 section 2). Nothing in the record points to (d); the read below discriminates.
- Consequences (ESTABLISHED by the route code): the server kept the credit (no refund on success, TR:1071-1091 runs only on failure) and SAVED the result (TR:1151-1159), so the owner's History should hold a 02:27 "Chanel No 5 vs Dior Sauvage" row that the phone never drew.
- **Proof read (read-only, the orchestrator's, before GREEN; not done by this lane):** the `comparisons` row created 23:27-23:29Z for the owner's account: `full_response.metadata.partial` true, `metadata.elapsed_ms`, both prices present; and the matching `search_logs` row's `duration_ms`. duration_ms >= about 33,000 makes (c) ESTABLISHED (the tail after TR:1061 adds the rest); a value well under 32,000 points to (d), and the deadline fix below is then still right but not the whole answer.

### 1.4 Server dependency: NONE. The fix is client-only.

### 1.5 Contract
1. `COMPARE_TIMEOUT_MS` 35000 -> **50000** (api.ts:56). One constant: the REST compare api.ts:747, `compareTextPair` api.ts:1057, the link compare HomeScreen.tsx:629 and the History detail api.ts:515 move together (the V1 link path has no server deadline until INC-U1, T7-03, and was cut the same way); the m18 pin "at least 3 uses" holds. Comment: keep it at least 15 s above STREAM_HARD_CAP_SECONDS. The loader promises no duration (LoadingScreenVariants.a2Pacing.test.tsx:393-410) and cancel stays (HomeScreen.tsx:298).
2. A success:true body with `metadata.partial === true` renders the result (today's path, unchanged) and the note at ResultsContent.tsx:491-498 gets honest words (T7-10: today's text promises a tap that has no handler, and on REST nothing more arrives, T7-07): `results.partial.note` VALUE only (no new key): EN "Some details did not arrive in time, so a few may be missing." / AR "لم تصل بعض التفاصيل في الوقت المناسب، لذا قد ينقص بعضها." [NATIVE READ]. (The brief's "some details still loading" is not true on the REST path; open question Q3.)
3. "Hold on" stays exactly as today for a body with no usable result: the server's 503 TIMEOUT (SCS:4372-4393 -> TR:549-564), a codeless 503, a deadline at 50 s, a dropped network (HomeScreen.tsx:543-545 unchanged).

## 2. Item 2: `price_asof` and "Last checked N days ago"

### 2.1 What the server sends (read in app/services/kb_serve.py)
- `client_price_asof(request)` (kb_serve.py:128-140): reads the flag FIRST (`ENABLE_KB_FIRST_SERVE`, :70-72, :132-133), then `X-Client-Capabilities` (<= 512 chars, comma tokens, stripped, case-insensitive) for `price_asof`. Routes pass `kb_price_asof=True` from it: TR:817, TR:1058, TR:1341, TR:1699, IR:617; the orchestrator stores `self._kb_price_asof` (SCS:4426-4427, :5083-5084) and passes `accepts_asof` to `classify` (SCS:6264).
- `classify` (kb_serve.py:245-342): Bahrain BHD offers only (`market BH`, `observed_currency BHD`, in stock, an allowed source, a readable non-future `last_seen`, :271-281). Age <= `GENUINE_PRICE_DB_TTL` (env GENUINE_PRICE_CACHE_TTL_SECONDS, default 7 days, product_data_service.py:28-30) = "fresh"; age <= `max_asof_days()` (KB_FIRST_SERVE_MAX_ASOF_DAYS, default 30, clamped 8..90, kb_serve.py:102-103) AND `accepts_asof` = "asof"; else refused (:282-305).
- The served price (`_price_dict`, kb_serve.py:216-234): `amount`, `currency "BHD"`, `retailer` = the merchant host (kb_service.py:605 `KB_HOST_REGEX`), `url`, `source_method "page_scrape"`, `estimated false`, `title` ("brand name concentration NNml"), `size` "NNml" when known, `as_of` = last_seen as ISO-8601 Z (:229, `_iso_z` :196-197), `in_stock`; `_cached` / `_cache_source` are stripped by `public_price_view` when the exact gate is on (price_service.py:9426-9442). EVERY KB price carries `as_of`, fresh or asof.
- The only other date source: `metadata.field_status[i].price.as_of` under ENABLE_FIELD_STATUS_METADATA (kb_ingest.py:193-207): a live price (`_cached` False) gets `state fresh, as_of = captured_at` (now); a cached price gets `state stale, as_of None`. `price.as_of` has no other writer (git grep, compare_runs.py:360 only copies it).

### 2.2 What the client draws today (ESTABLISHED)
`priceProvenance` (services/fieldStatusView.ts:45-78): date = `price.as_of` else field_status `as_of` (:64); stored origin -> 'listed' (:69); live: age <= 7 d genuine (24 h converted) 'fresh', <= 30 d 'stale', else 'unknown' (the amount is replaced by `results.honest.notListed`, ResultsContent.tsx:411-418). `renderProvenanceLine` (ResultsContent.tsx:159-189): fresh "{{store}}, as of {{date}}", stale "{{store}}, last seen {{date}}", listed "Listed at {{store}} on {{date}}", staleNoDate "Price checked earlier" (en.json:706-712; ar.json:706-712). `CLIENT_CAPABILITIES = ['price_size']` (services/requestContext.ts:38), joined with ',' into the header (requestContext.ts:153).

### 2.3 Contract
1. `CLIENT_CAPABILITIES = ['price_size', 'price_asof']` -> header exactly `price_size,price_asof`.
2. For the LIVE kinds 'fresh' and 'stale' (both), the provenance line becomes the owner's wording; 'listed' (History), 'staleNoDate' and 'unknown' are byte-unchanged. `days` = whole CALENDAR days between the as-of date and today in the phone's local time zone (start-of-day difference, rounded), clamped at 0 (a future as_of, from server skew <= 300 s or a slow phone clock, reads "today"). The 30-day bound stays the elapsed-time rule of fieldStatusView.ts:70-77 (unchanged). New pure helper in fieldStatusView.ts: `calendarDaysAgo(dateIso, nowMs): number`.
   - days 0: `results.price.checkedToday` "{{store}}, last checked today" / AR "{{store}}، آخر تحقق اليوم"; no store: `results.price.checkedTodayNoStore` "Last checked today" / "آخر تحقق اليوم".
   - days 1: `results.price.checkedYesterday` "{{store}}, last checked yesterday" / "{{store}}، آخر تحقق أمس"; `...YesterdayNoStore` "Last checked yesterday" / "آخر تحقق أمس".
   - days >= 2: `results.price.checkedDaysAgo` with `count: days` (plural selection) and `days` (the display figure through the app digit policy, `formatNumber(days, { maxFraction: 0, grouping: false })`, as INC-C1a's size). The six suffixes in BOTH catalogs (the house shape, cf. home.errors.rateLimited_*):
     - EN `_zero` `_one` `_two` `_few` `_many` `_other`: all "{{store}}, last checked {{days}} days ago" (only `_other` is reached in EN).
     - AR [NATIVE READ]: `_two` "{{store}}، آخر تحقق قبل يومين"; `_few` (3-10) "{{store}}، آخر تحقق قبل {{days}} أيام"; `_many` (11-99) "{{store}}، آخر تحقق قبل {{days}} يومًا"; `_other` (100+, unreached) and `_zero` (unreached) "{{store}}، آخر تحقق قبل {{days}} يوم"; `_one` (unreached) "{{store}}، آخر تحقق قبل يوم واحد".
     - `results.price.checkedDaysAgoNoStore_*`: the same twelve strings without "{{store}}, " / "{{store}}، " (EN capital "Last checked {{days}} days ago"; AR "آخر تحقق قبل ...").
3. The old keys asOf / asOfNoStore / lastSeen / lastSeenNoStore stay in the catalogs, unused (no key-count drop; Q5). Same testIDs (`results-product-asof-<i>` / `-lastseen-<i>`) so the S81-11 structure pins keep their anchors.
4. One wording for fresh and stale removes today's only date-boundary hazard (the server's fresh window is an env knob, the client's is a constant 7): nothing on the card now depends on where the 7-day line falls.

### 2.4 Flag-mix walk (the line never shows a wrong date)
- ENABLE_KB_FIRST_SERVE unset (web today, the relay's 04:25 note): no `price.as_of`, the header is not read (kb_serve.py:132): byte-identical.
- KB_FIRST_SERVE on, any client: KB prices <= 7 d with `as_of` = last_seen: "noon.com, last checked N days ago", N 0..7. With this client (price_asof) also 7..30 d: N 8..30 (today "last seen <date>").
- KB_FIRST_SERVE_MAX_ASOF_DAYS > 30: a 31..90 d price the verdict used, while the client hides the amount (notListed): precondition SD-A2.
- GENUINE_PRICE_CACHE_TTL_SECONDS changed: the fresh/asof split moves, nothing visible (one wording).
- ENABLE_FIELD_STATUS_METADATA on: a live price gets as_of = capture time -> "last checked today"; a cached price (as_of None) keeps "Price checked earlier".
- ENABLE_PRICE_NOT_LOST on: `size_ml` from the KB title (INC-P2 `listing_size_ml`) -> INC-C1a's label; independent.
- History: 'listed' unchanged. Camera (IR:617) and stream (TR:1341): the same reads. A future INC-P4 `fallback: "last_seen"` price: the same wording.
- N follows the phone's clock and time zone (the clock today's windows use, ResultsContent.tsx:148); never a future date.

## 3. Item 4: the honest camera message

### 3.1 Today's server answer and client text (ESTABLISHED)
- The vision step: IR:385-388 (`camera_refuses_for_consent`, then `identify_products`). Any `LLMUnavailableError` (OpenAIEgressStoppedError is one, api_budget_service.py:735; ConsentUpdateRequiredError is one, llm_router.py:235) or a transient OpenAI failure -> refunds (IR:402-403) and `HTTPException(503, detail={"code": "LLM_UNAVAILABLE", "error": LLM_UNAVAILABLE_FRIENDLY_MESSAGE})` (IR:412-416; the handler lifts the code to the top, T7 section 4). Anything else: 500 "Image analysis failed. Please try again." (IR:417 -> SERVER_ERROR). Log: `[IMAGE] Vision call failed: OpenAIEgressStoppedError` (FINDINGS row 13).
- The client: `identifyFromImages` throws an axios-shaped error with `response.status 503, data = parsed body` (api.ts:406-411); ResultsScreen.tsx:399-402 `isCameraEngineOutage(err)` (failureClassification.ts:82-95: code LLM_UNAVAILABLE / INTERNAL_ERROR / SERVER_ERROR, or a non-503 5xx) -> loadError 'engine_unavailable' -> title "One moment — the comparison engine is resting", body "Comparisons are paused for a moment. Please come back shortly." (ResultsScreen.tsx:864, :879; en.json:121-122) and a Back button (:882). The body promises "shortly".
- Other camera failures that must NOT change: a 200 `comparison_failed` / `success:false` with an outage code AFTER a good identify (`isCameraEngineOutageResponse`, failureClassification.ts:104-109, ResultsScreen.tsx:307-315: the compare engine is down, so typing would not help); a bare 503 -> timeout (failureClassification.ts:92-93); USAGE_LIMIT -> Paywall (ResultsScreen.tsx:382-386).

### 3.2 The choice: key on the server's answer, not on the native version
Picked: the THROWN identify failure with HTTP 503 and code LLM_UNAVAILABLE (top-level `code` or `detail.code`). Why:
- That answer is emitted only when the vision call itself was refused or failed transiently (IR:412). In build 1.0.1, once vision is on Claude, a working camera never gets it, and a real outage does (the line is then still true: "not available right now").
- Keying on the native version would be WRONG inside 1.0.1 before the owner flips vision (CAM-1_BRANCH_PLAN: the build ships, then ENABLE_ANTHROPIC_VISION opens in its own window after the photo measurement): 1.0.1 would show the engine screen while the camera is still refused. requestContext.ts also sends no app version (ORCH-CAM-A).
- No time promise anywhere in the new copy.

### 3.3 Contract
1. failureClassification.ts: new `isCameraVisionUnavailable(err)`: `err.response.status === 503` AND code (data.code ?? data.detail.code) === 'LLM_UNAVAILABLE'. ResultsScreen's catch consults it BEFORE `isCameraEngineOutage` (ResultsScreen.tsx:399) -> new loadError `'photo_unavailable'`.
2. The state: title `results.photoUnavailable.title` "Photo compare is not available right now" / "المقارنة بالصور غير متاحة حاليًا" [NATIVE READ]; body `results.photoUnavailable.body` "You can type the two names instead." / "يمكنك كتابة اسمي العطرين بدلًا من ذلك." [NATIVE READ]; primary CTA `common.typeNames` "Type the names" / "اكتب الأسماء" [NATIVE READ] (testID `results-photo-type-names`); the existing Back affordance stays.
3. "Type the names": sets a one-shot intent in a new module `services/homeEntryIntent.ts` (`requestHomeMode('type')` / `consumeHomeMode()`, module state, no storage), then `navigation.popTo('Main')` (@react-navigation/native-stack 7.12, package.json:21; RootStackParamList `Main: undefined`, types.ts:608, so no nav type change). HomeScreen consumes it in a `useFocusEffect` (it already uses two, HomeScreen.tsx:198, :314) -> `setInputMode('type')` (HomeScreen.tsx:129). No typed text is carried over.
4. Every other camera answer renders byte-identical (P1 rows).

### 3.4 Flag-mix walk
- Today (ENABLE_ANTHROPIC_VISION off, OpenAI egress stopped): 503 LLM_UNAVAILABLE -> the message (true).
- Vision on Claude, consent 3, healthy: identify succeeds, the message never shows. Claude breaker open, spend lane exhausted, 429 / 5xx: the 503 -> the message (true; typing may fail too, then the text path's own engine copy).
- Consent below 3 (ConsentUpdateRequiredError): the 503 -> the message (L7). A decoded image over 5,000,000 bytes under Claude (T1 B7): the 503 -> the message (LIKELY never: 1024 px JPEGs).
- ENABLE_CAMERA_FAILURE_ENVELOPE on/off: post-identify failures only, unchanged states. CAM-2 refusing a client without the 1.0.1 token: must be the same 503 code (SD-C1).

## 4. T7-04 link-mode wording per refusal code, and T7-08

### 4.1 Today (ESTABLISHED)
- Link compare (HomeScreen.tsx:590-706): a `success:false` body (:643-660) or a thrown error (:662-704) with a code outside TIMEOUT / CONTENT_UNAVAILABLE / USAGE_LIMIT / CATEGORY_NOT_LIVE / the engine codes gets `home.errors.comparison` "Sharper match coming up — add the brand and the fragrance name." (errorCopy.ts:108-109; en.json:111) under "Hold on — give it another tap.": text-mode advice and a retry that fails the same way.
- Codes on main: V1 codeless 400 (UR:344-347 -> BAD_REQUEST, error_handler.py:25); V2 400 `{code, error, field, reason}` NOT_PRODUCT_PAGE / STORE_UNREADABLE / UNRESOLVED_PRODUCT (UR:145, :177-184, :335-339); TIMEOUT 503 (UR:203); LLM_UNAVAILABLE 503 (UR:275-277). S97's INC-U1 (dark ENABLE_URL_LINK_RESULT) adds STORE_UNREADABLE / UNRESOLVED_PRODUCT on V1 (code + error; INC-U1_FLIP_NOTE.md). The client maps by code only.

### 4.2 Contract (link path only; the text path is byte-unchanged)
- errorCopy.ts: new `linkErrorKey(code)`: STORE_UNREADABLE -> `home.errors.link.storeUnreadable`; NOT_PRODUCT_PAGE -> `home.errors.link.notProductPage`; UNRESOLVED_PRODUCT -> `home.errors.link.unresolved`; any other code for which `friendlyErrorKey(code)` returns `home.errors.comparison` (BAD_REQUEST, VALIDATION codes, null) -> `home.errors.link.generic`; everything else -> `friendlyErrorKey(code, reason)` (TIMEOUT, RATE_LIMITED, INSUFFICIENT_DATA, the engine codes keep today's copy).
- HomeScreen.tsx both link arms (:651-659 and :698-703): when the body key is a `home.errors.link.*` key, `Alert.alert(t('home.errors.link.title'), t(key), [{ text: t('common.cancel'), style: 'cancel' }, { text: t('common.typeNames'), onPress: () => setInputMode('type') }])`; otherwise today's call exactly.
- Strings (AR all [NATIVE READ]):
  - `home.errors.link.title`: "Let's try another way" / "لنجرّب طريقة أخرى"
  - `home.errors.link.storeUnreadable`: "This shop does not let us read its pages. Paste a link from another shop, or type the two names." / "هذا المتجر لا يسمح لنا بقراءة صفحاته. الصق رابطًا من متجر آخر، أو اكتب اسمي العطرين."
  - `home.errors.link.notProductPage`: "That link opens a shop page, not a product. Open the perfume's own page and copy its link." / "هذا الرابط يفتح صفحة متجر وليس صفحة منتج. افتح صفحة العطر نفسه وانسخ رابطها."
  - `home.errors.link.unresolved`: "We did not find a perfume on that page. Copy the link of the perfume's own page." / "لم نجد عطرًا في تلك الصفحة. انسخ رابط صفحة العطر نفسه."
  - `home.errors.link.generic`: "One of those links did not open for us. Paste a link from another shop, or type the two names." / "أحد الرابطين لم يُفتح لدينا. الصق رابطًا من متجر آخر، أو اكتب اسمي العطرين."
  - every string passes .copy-policy.json (no "couldn't", "try again", "Failed to"; no تعذر / فشل) and names no time.

### 4.3 T7-08 "(converted from USD)" once
ResultsContent.tsx:207 drops the inline suffix (`return base;` for every method); the caption (ResultsContent.tsx:445-455) stays the one label. INC-C1a's `withSize` then wraps the bare amount: "7.140 BHD · 100 ml" over the caption "(converted from USD)" (GATE_INC_C1A CC-2 / L-2 hand this to INC-C1). No other surface prints this formatPrice (CR-5 of INC-C1a).

## 5. Item 3: the bottle size beside the price (R3 REC-4): DROPPED
R3 (section 3 "What one over-the-air update would add"; ranked item 4) lists three client pieces: the `price_asof` token and the "Last checked" words (both item 2) and the bottle size, which INC-C1a #412 already draws from `price.size_ml` (ResultsContent.tsx:218-231; R3's "no reader of price.size" predates #412). A KB price carries `size "NNml"` and a title ending "NNml" but no `size_ml` (kb_serve.py:220-228); INC-P2's `listing_size_ml` reads the title then `size` (INC-P2 spec 2.5), so under ENABLE_PRICE_NOT_LOST it gets `size_ml`. Reading `price.size` on the client would bypass INC-P2's frozen `size_ml` contract (RULINGS_INC_P2 G) and draw sizes INC-P2 refused. Nothing remains (L9).

## 6. RED rows (jest; pure ASCII sources, Arabic built from code points; files under SmartCompareApp/__tests__/c1/)
Suggested files: `holdOn.c1.test.ts(x)`, `lastChecked.c1.test.tsx`, `cameraLink.c1.test.tsx`. Harness models: the INC-C1a suite (c1a/sizeLabel.c1a.test.tsx) for ResultsContent renders, HomeScreen.errorCopy.a11 / arabicAlerts.w311 for Home Alerts, screens/camera.engineUnavailable.s69 for the camera states, s81_08/requestHeaders for the header.
- H1 `COMPARE_TIMEOUT_MS === 50000`; the REST GET, the link POST and the History GET carry it.
- H2 THE 02:27 SHAPE: a mocked axios instance whose GET resolves at t = 36 s (fake timers) with a success:true body (`metadata.partial: true`, two shown BHD prices 77.940 noon.com and 47.000 fragrancebh.com) and which rejects with `ECONNABORTED` when `config.timeout` passes first. Assert `onComplete(body)` and no `onError`. At base: onError with parsed code TIMEOUT.
- H3 HomeScreen with that body: `navigate('Results', { result })`, no Alert. At base: `Alert.alert('common.error', 'home.errors.timeout')`.
- H4 ResultsContent partial body: both prices drawn; the note equals the new EN / AR strings; neither contains "tap" / "اضغط".
- H5 (pin) a 503 `{code TIMEOUT}` and an `ECONNABORTED` at 50 s still give `Alert(common.error, home.errors.timeout)`.
- D1 the header is exactly `price_size,price_asof`; `CLIENT_CAPABILITIES` deep-equals `['price_size', 'price_asof']`.
- D2 live price `retailer noon.com`, `as_of` at days 0, 1, 2, 3, 10, 11, 29 (local calendar): EN "noon.com, last checked today / yesterday / 2 days ago ..."; AR `_two` at 2, `_few` at 3 and 10, `_many` at 11 and 29 (code points), the figure through the digit policy.
- D3 boundary: as_of 23:50 local yesterday, now 00:10 -> "yesterday"; as_of 00:10 today, now 23:50 -> "today" (kills a floor(ms / day) mutant).
- D4 as_of 4 minutes in the future -> "today", never a negative figure.
- D5 (pin) > 30 days -> the notListed line; stored origin -> "Listed at noon.com on <date>"; staleNoDate -> "Price checked earlier"; all byte-identical.
- D6 no retailer -> the NoStore forms (EN capitalised).
- D7 field_status `as_of` only (no `price.as_of`) -> the same wording.
- C1 camera: thrown `{status 503, data {code LLM_UNAVAILABLE}}` (and the `detail.code` shape) -> testID of the new state, the EN / AR title and body, the CTA; pressing it calls `requestHomeMode('type')` and `popTo('Main')`; a focused HomeScreen then shows type mode (the type-mode input testID) and a second focus does not re-apply it.
- C2 (pin) thrown 500 `SERVER_ERROR`, thrown 502, 200 `comparison_failed` + LLM_UNAVAILABLE -> today's engine screen; bare 503 -> the timeout state; USAGE_LIMIT -> Paywall.
- C3 property: the new camera and link strings contain no digit and none of "update", "soon", "shortly", "next" (EN) / "تحديث", "قريب", "بعد قليل" (AR).
- L1 link: 400 STORE_UNREADABLE, NOT_PRODUCT_PAGE, UNRESOLVED_PRODUCT, BAD_REQUEST, on BOTH arms (a success:false 200 body and a thrown 400): `Alert(home.errors.link.title, <key>, [cancel, typeNames])`; pressing typeNames switches the input to type mode.
- L2 (pin) link TIMEOUT, USAGE_LIMIT, CATEGORY_NOT_LIVE, LLM_UNAVAILABLE, RATE_LIMITED (with retry_after_seconds) -> today's Alerts; the text path with BAD_REQUEST -> today's `home.errors.comparison`.
- X1 T7-08: a converted price shows "(converted from USD)" exactly once on the card (the caption); with `size_ml` 100: "7.140 BHD · 100 ml" plus the caption.
- P1 TODAY-BODY GOLDEN (recorded at base, byte-identical after, EN and AR): (a) a full non-partial body with two genuine undated BHD prices; (b) a stored History body with `as_of` (the listed line); (c) text-path Alerts for TIMEOUT, LLM_UNAVAILABLE, INSUFFICIENT_DATA + reason, RATE_LIMITED; (d) camera thrown 500 and 200 comparison_failed screens. Excluded by design and listed: converted prices (X1), partial bodies (H4), live dated prices (D2), the 503 LLM_UNAVAILABLE camera answer (C1), link refusals (L1).
- P2 en.json and ar.json key sets equal; every plural family complete in both; copy-policy clean (the existing fences run); every new AR string equals the spec bytes (read as UTF-8 by the RED agent, the INC-C1a CR-2 method).
- Mutants (each must be killed): M1 35000 kept; M2 the partial routed to onError; M3 the token list without `price_asof` or joined with "; "; M4 floor(elapsed / 24 h) day count; M5 no clamp (a "-1" figure); M6 the new wording applied to 'listed'; M7 the photo state keyed on ANY outage code (catches C2); M8 keyed on status 503 only (a bare 503 must stay timeout); M9 the link map applied on the text path; M10 the inline converted suffix kept; M11 the CTA without the intent (Home not in type mode); M12 an AR plural form swapped (few <-> many).

## 7. Stay-green, moved pins, the bundle rule
- Expected moved pins (quote each, never weaken): the INC-C1a exact header pins (about 18: requestHeaders / cameraHeaders / sseHeaders s81_08, api.cameraAuthRetry.u13c, c1a C1) -> `price_size,price_asof`; api.getComparison.comparisonId.m18.test.ts:79 `timeout: 35000` -> 50000 (the HomeScreen suites mock `COMPARE_TIMEOUT_MS: 35000` themselves and do not move); live "as of" / "last seen" cards and leaf counts in s11/copy.s11, s11/honestUnknowns.s11, s11e/arCopy.s11e; screens/camera.engineUnavailable.s69 (the thrown 503 LLM_UNAVAILABLE case); link-path BAD_REQUEST cases in HomeScreen.errorCopy.a11 / arabicAlerts.w311; frozen c1a C4 (converted label inside withSize: an E-row by ruling); tests/test_s81_12_legal_v3.py `BASE_I18N_KEY_COUNT` 1014 -> 1038 (24 new keys) and the name-set sha (CC-8 precedent).
- Gates: the new files and every suite above; ResultsContent / ResultsScreen / HomeScreen / errorCopy / failureClassification / api.networkMatrix suites; i18n parity and copy-policy fences; the FULL jest suite once (LC-7; the 4 accepted nativeBundle.w37 nodes); tsc --noEmit; eslint as CI; a --runInBand pair both orders with requestHeaders.s81_08. Backend: no app/ file; through pyt.py the tests/ fences that read the edited client files (test_s81_12_legal_v3.py, test_s81_12_gate_rows.py, test_legal_docs_u8*.py, test_dimension_label_catalog_parity_w414.py, test_comparison_id_echo.py, and any other `git grep -l SmartCompareApp/src tests/` hit on these files).
- Bundle rule: `git diff --name-only 2e7a1229 <M> -- SmartCompareApp`, minus `__tests__`, must be exactly: `src/services/api.ts`, `src/services/requestContext.ts`, `src/services/fieldStatusView.ts`, `src/services/errorCopy.ts`, `src/services/failureClassification.ts`, `src/services/homeEntryIntent.ts` (new), `src/components/results/ResultsContent.tsx`, `src/screens/ResultsScreen.tsx`, `src/screens/HomeScreen.tsx`, `src/i18n/en.json`, `src/i18n/ar.json` (11). No package, lock, app.json or SmartCompareApp/locales change.

## 8. Server dependencies (named, none part of this unit)
- SD-H1 (optional) The REST route keeps the credit and saves a result the phone never got (TR:1071-1159; HomeScreen.tsx:294-297 calls the refund a product call).
- SD-H2 Keep `STREAM_HARD_CAP_SECONDS` (web 30) at least 15 s under the client deadline; ENABLE_COMPARISON_ID_ECHO adds up to 5 s after the cap.
- SD-A1 ENABLE_KB_FIRST_SERVE is the owner's window; with this client it serves dated prices up to 30 days old, and the relay's 04:30 spot-check calls the stored data raw: clean first.
- SD-A2 Keep KB_FIRST_SERVE_MAX_ASOF_DAYS unset or <= 30.
- SD-C1 CAM-2 VISION-GATE must answer a client without the 1.0.1 token with the same 503 `{code: "LLM_UNAVAILABLE"}` at the vision step, or this predicate is widened in an update before CAM-2's flip.
- SD-L1 none (T7-04 needs no S97 change).

## 9. Stated limits
L1 cause (c) LIKELY until the proof read; a dropped network still shows "Hold on" (correctly). L2 a capped compare holds the loader up to about 40 s, a hung server 50 s (cancel stays). L3 the partial note cannot say which details are missing. L4 "Last checked" follows the phone's clock and zone. L5 item 2 changes nothing until ENABLE_KB_FIRST_SERVE (or ENABLE_FIELD_STATUS_METADATA) is on; the header goes out from the first launch. L6 the camera entry stays visible on 1.0.0; the message comes after the photos. L7 a consent-2 account on the camera also gets the photo message. L8 BAD_REQUEST links keep the generic link sentence until INC-U1 sends specific codes on V1. L9 no bottle size until INC-P2 is on. L10 the old asOf / lastSeen keys stay unused.

## 10. Open questions (the gate rules)
- Q1 The proof read of 1.3 (the orchestrator's, read-only): run it before GREEN; it decides whether the record says ESTABLISHED.
- Q2 The deadline: 50 s (this spec) or 45 s.
- Q3 The partial note: "did not arrive in time" (this spec, true on REST) or the brief's "still loading".
- Q4 "Last checked" on 'fresh' (<= 7 d) as well as 'stale' (this spec: both, one wording).
- Q5 Keep the unused old keys (this spec) or delete them (moves the legal_v3 pin down as well as up).
- Q6 Are INC-C1a's bytes already on the phones? If not, the published update also carries C1a's six files; the bundle list from 2e7a1229 names only C1's.
- Q7 The legal_v3 pin re-record at the gate (the CC-8 precedent).
- Q8 The CTA: `popTo('Main')` + a one-shot intent (this spec) or a typed `Main` param (types.ts:608, linking.ts:73-74 move).
- Q9 Class: SAFE by LC-1 proposed (INC-C1a precedent: client-only, no consent, auth, quota, legal or native change), one adversary, two lenses (correctness + every server answer and flag mix; words, RTL, P1). FOCUS if the gate weighs the global deadline and the widened price serve.

## 11. INC-C1b seed (S, SAFE)
T7-09: ProductImage.tsx:73-103, one retry after about 1.5 s on the first `onError`, then the placeholder, plus one host-only Sentry breadcrumb (sentry.ts:153-197 scrubbing). T7-11: getComparison (api.ts:512-526) keeps `comparison.created_at` as `saved_at`; a stored result shows "Saved on <date>" (formatAsOfDate) EN / AR [NATIVE READ]; no server change (history_routes.py:164).
