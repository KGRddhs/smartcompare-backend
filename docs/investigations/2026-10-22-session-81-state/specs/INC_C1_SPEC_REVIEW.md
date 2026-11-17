# INC-C1 OTA-BATCH: spec review (S96 spec reviewer, Opus 5.5, 2026-11-17)

Base: origin/main `5cd93c6aaa4e80e4b0ab36a43e6fa1f657d797c9`, re-fetched in sc-s96-c1a (it has not moved). `git diff --name-only 2e7a1229 origin/main -- SmartCompareApp` is empty (0 lines). All reads were done through git plumbing. No checkout was edited, nothing was run, and no live system was touched.

**VERDICT: AMEND.** The diagnosis, the contracts and the flag walks hold. The RED design has one MAJOR defect (rows import symbols that do not exist at base) and several MINOR ones. Fix them in the spec before RED starts. Nothing here is NOT_READY.

## 1. The Hold-on cause (re-derived): CONFIRMED, as LIKELY (c)
I re-read each arm myself:
- The dialog is the Alert `common.error` + `home.errors.timeout` (en.json:379, :120). On the REST path, only `parsed.code === 'TIMEOUT'` reaches it (HomeScreen.tsx:543-545, after parseApiError at :527).
- The REST path is the one in use: `ENABLE_EXPO_FETCH_SSE_DEFAULT = false` (features.ts:52, getter :118-120). So there is ONE `api.get` with `timeout: COMPARE_TIMEOUT_MS` (api.ts:747; the constant is 35000 at :56).
- A body with success:true goes to onComplete (api.ts:753-756) and then to navigate (HomeScreen.tsx:479-485). No client branch turns a success:true body into the dialog.
- TIMEOUT comes only from one of these: a body code TIMEOUT / STREAM_TIMEOUT, a codeless 503 (api.ts:1164-1178), or no response with ECONNABORTED / ETIMEDOUT / ERR_NETWORK (api.ts:1187-1194).
- Server: the quoted line is the format string at SCS:4335-4337, printed just before `return partial` (SCS:4339). So compare_from_text returned success:true. The only TIMEOUT bodies are in the no-usable-data arm (SCS:4350-4393).
- I checked the post-compare exits myself; the draft does not cover them. Each would draw a DIFFERENT body sentence, so none matches the owner's screenshot:
  - The S81-20 result gate (TR:1112-1117 -> INSUFFICIENT_DATA 400, `home.errors.insufficientData*`).
  - The INC-R1 ask exit (TR:1066-1070 -> 400, `home.errors.comparison`).
  - A JSON parse failure (code null -> `home.errors.comparison`).
- Only "no 200 body reached the phone within 35 s" (c) or a network drop (d) remain.
- Why (c) is LIKELY: the 30 s cap is armed at SCS:4296, AFTER this route pre-work:
  - the auth dependency and the limiter;
  - text_gate (TR:1008);
  - get_user_preferences (TR:1013, a database read);
  - consume_comparison_credit (TR:1028);
  - the three entry guards (SCS:4274 / :4286-4288 / :4293).
- After the cap fires, wait_for waits for the cancelled task, then the tail runs (TR:1061-1168, including an awaited persist under ENABLE_COMPARISON_ID_ECHO, TR:1140), then serialisation and the network.
- `get_comparison_service()` builds a new instance per request (SCS:10244-10246), so no state leaks between requests.
- I agree that the deadline fix is client-only.

## 2. Checks 2 to 9
- **(2) Camera copy: holds.**
  - The thrown 503 `LLM_UNAVAILABLE` on /image/identify has exactly one emitter: IR:412-416. Its other exits are a 500 (IR:417) and 200 bodies (IR:836 `comparison_failed`).
  - No middleware emits the code (git grep over app/).
  - A healthy 1.0.1 camera never receives that answer, and the copy names no time. C3 enforces this as a property.
  - Keying on the server answer rather than the native version is the right pick: requestContext sends no app version.
- **(3) Files: holds.** The 11 files are all under SmartCompareApp/src:
  - There is no app.json, package, lock or SmartCompareApp/locales change. CAM-1 edits locales/*.json and app.json (lane-s97/cam/apply_cam1.py:23-24, :73), so there is no collision.
  - None of S97's backend files is touched (the real path is app/api/url_routes.py, not app/api/routes/).
  - `navigation.popTo` is a JS API of native-stack ^7.12 (package.json:21), so it needs no native change.
- **(4) EN and AR: partly holds.** See F6.
- **(5) P1: holds, apart from F8.**
  - Every new line is keyed on one of: `metadata.partial`, a valid date, a thrown 503 with LLM_UNAVAILABLE, a link-path code, or `source_method converted_usd`.
  - The only server reader of the new token is kb_serve.client_price_asof (kb_serve.py:128-140, flag first). The routes are TR:817, :1058, :1341, :1699 and IR:617.
- **(6) price_asof walk: no wrong date found.**
  - `as_of` is the offer's `last_seen` (kb_serve.py:229).
  - A changed amount is a NEW row, and a re-observation moves only last_seen (migrations/045_kb_core.sql:29-32; kb_service.py:153-156 `KB_OFFER_OBSERVATION_KEY` includes amount). So the date always belongs to the amount on screen.
  - A future last_seen beyond 300 s is dropped (kb_serve.py:276-277), and the client clamps the rest.
  - "N days ago" is computed from an absolute timestamp, so it stays true on replay or share.
  - The field_status `as_of` is stamped only for `_cached is False` (live) prices (kb_ingest.py:196-198). I found no whole-response cache that replays through `_kb_ingest_tail` (SCS:4020-4055).
  - Remaining risks: the phone clock (L4), and SD-A2 (MAX_ASOF_DAYS above 30 is hidden as notListed, which is honest).
- **(7) RED rows and mutants:** F1 (MAJOR), plus F2 to F5.
- **(8) Size: sane but heavy.** The unit has 11 files, 24 keys, about 19 rows plus P1/P2, 12 mutants and about 10 moved-pin suites. If the budget line bites, a clean seam is C1-core (items 1, 2 and T7-08) and C1-x (the camera state and T7-04, which share `common.typeNames` and HomeScreen). Both can still ride one OTA. This is not a finding.
- **(9) file:line: correct at 5cd93c6a**, apart from F12. I spot-checked about 70 cites across api.ts, HomeScreen, ResultsScreen, ResultsContent, fieldStatusView, errorCopy, failureClassification, requestContext, features, types, en/ar.json, SCS, TR, IR, UR, kb_serve, kb_ingest, RB, price_service, product_data_service, error_handler and category_gate.

## 3. Findings
- **F1 MAJOR (RED design).** Several rows reach new symbols directly:
  - C1 asserts `requestHomeMode('type')`, which needs an import or a `jest.mock` of the NEW `services/homeEntryIntent.ts`.
  - D3 and D4 suggest calling the new `calendarDaysAgo` directly.
  - The same risk applies to `isCameraVisionUnavailable` and `linkErrorKey`.

  At base these fail in four ways:
  - The cameraLink file cannot load ("Cannot find module"). Its pin rows (C2, L2) then FAIL at base, and C1 and L1 fail on resolution, not on assertions.
  - A direct call of a missing export gives a TypeError, not an assertion failure.
  - `tsc --noEmit` at base shows errors. The house gate requires 0 tsc errors at base (GATE_INC_C1A.md:5).

  Fix: every RED row observes only through surfaces that exist at base:
  - ResultsContent and ResultsScreen renders.
  - HomeScreen with a mocked navigation whose `popTo` is a jest.fn.
  - Type mode is asserted through the type-mode input testID after a focus event, and a second focus must not re-apply it.
  - No import of a new symbol, and no jest.mock of a new path.
- **F2 MINOR (RED design).** H3 must drive the REAL api.ts streamComparison (`jest.requireActual`), with only the axios instance mocked and the real `COMPARE_TIMEOUT_MS`. The house HomeScreen suites the draft names as models mock the api module with `COMPARE_TIMEOUT_MS: 35000` (HomeScreen.errorCopy.a11.test.tsx:102, arabicAlerts.w311:103). A suite built that way decides its own outcome and does not test the fix.
- **F3 MINOR (mutant kill).** D4 (as_of 4 minutes in the future) does not kill M5 (no clamp) unless the future as_of falls on the next local calendar day. On the same day the difference is already 0. Fix: pin now = 23:58 local and as_of = 00:02 the next day.
- **F4 MINOR (RED determinism).** The rows marked "local calendar" (D2, D3, D4) must build `as_of` from local Date parts (`new Date(y, m, d, h, mi).toISOString()`) or pin TZ in the test. Otherwise CI (UTC) and this box (UTC+3) give different day counts.
- **F5 MINOR (RED design).** C3 (no digit, no "soon" / "update") passes vacuously at base, because the keys do not exist. Add the positive control the house uses: the key exists with non-empty copy (LoadingScreenVariants.a2Pacing.test.tsx:402-407).
- **F6 MINOR (Arabic).**
  - The AR strings for `checkedToday`, `checkedTodayNoStore`, `checkedYesterday` and `checkedYesterdayNoStore` (section 2.3 item 2) carry no [NATIVE READ] mark.
  - The 12 `checkedDaysAgoNoStore_*` AR strings are given only as a rule ("the same twelve strings without ..."). P2 needs literal bytes.

  Fix: one table that lists every new AR string literally (24 keys, plus the new value of `results.partial.note`), each marked [NATIVE READ].
- **F7 MINOR (diagnosis, proof read).** The proof read's threshold is too generous. `duration_ms` covers only TR:1002 to TR:1061. It excludes the auth dependency and limiter before it, and the persist, serialisation and network after it. So a value of 33,000 or more does not make (c) ESTABLISHED. Only a value of 35,000 or more does, because the phone's deadline had necessarily passed by then.
  - 31,000 to 35,000 stays LIKELY.
  - Also read `metadata.elapsed_ms` of the saved row: its excess over 30,000 is the cancel tail.
  - The Railway HTTP log duration of that request is the best single discriminator (read-only, the orchestrator's).
- **F8 MINOR (P1 precondition).** P1(a) and the item 2 walk assume ENABLE_FIELD_STATUS_METADATA is off on web. The record says only LIKELY off: "not in the E0 flag lists" (investigation-2026-11-15/T7_client.md:48). If it is on, today's live cards change from "noon.com, as of Nov 17" to "noon.com, last checked today". That is true, but not byte-identical. Fix: state it as a P1 precondition and a stated limit, and have the orchestrator read the flag list.
- **F9 MINOR (words).** STORE_UNREADABLE is also emitted for transport errors, an SSRF hop, the redirect cap and non-2xx answers (url_extraction_service.py:1122-1152). So "This shop does not let us read its pages" overstates the cause for a timeout or a 5xx, and on a ToS-sensitive subject. It also reads singular when `field` is "both". It mirrors the server copy (url_extraction_service.py:103-105). Suggest neutral words such as "This shop's page did not open for us" (the copy-policy bans "couldn't"). This is a words call for the gate or the owner.
- **F10 MINOR (stated limit L7).** A consent-below-3 account on the camera gets "You can type the two names instead". The text compare refuses the same account at SCS:4293 (LLM_UNAVAILABLE -> the engine copy), so the sentence is false for that account. Say so in L7.
- **F11 MINOR (gates).** Name explicitly the backend fences that read the edited client files instead of relying on the catch-all:
  - tests/test_s81_sf1_gate_rows.py:107 (reads HomeScreen.tsx);
  - tests/test_s81_sf1_surfaces_be.py:1208-1215 (rglob over src/*.ts*, so the new homeEntryIntent.ts is scanned);
  - tests/test_timeout_partial_integration.py:66 (the copy-policy mirror).
- **F12 MINOR (cites).** UR:145 should be UR:144 (`_URL_V2_REFUSAL_CODES`). requestContext.ts:153 is the `if`, and the join is at :154. The stale "35 s" comments are api.ts:55 (in the bundle: update it with the constant), HomeScreen.tsx:288 (in the bundle) and LoadingScreenVariants.tsx:123 (not in the bundle: leave it). url_routes.py:140 is S97's file: leave it.
- **F13 MINOR (contract clarity).** The photo state says the existing Back affordance stays. Today the empty state has ONE button, whose onPress is goBack for the engine state (ResultsScreen.tsx:882). Say whether Back becomes a second button (with its testID), or whether the header back button is the back affordance.

## 4. Notes for the gate (not findings)
- Q2: 50 s is consistent with SD-H2 (the cap plus at least 15 s). 45 s leaves only about 10 s for the pre-work, the cancel tail and the persist, which is thin given the loop lag the record measured.
- Q4: one wording for fresh and stale is right. It removes the client's 7-day constant from anything visible.
- The relay's 03:21 phone-proof notes (RELAY_RESUME_2026-11-16.md:80) list more INC-C1 candidates that are not in the brief:
  - Volume shown without a unit;
  - the pros text quotes a review count that disagrees with the reviews section;
  - a con about our data.

  They are out of this spec's scope until the orchestrator sends them. Mentioned so they are not lost.
