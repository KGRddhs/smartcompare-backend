# S81-20 B2-RESULT-GATE-V2 adversarial spec review (FOCUS: the quota path; lenses: correctness + quota-and-billing)

- Spec reviewed: `.qa-s80/S81-20_UNIT_SPEC.md` sha256 8435f266934df2275db25978cc60695db9bd940da903aa0e76a787c6176fdf09
  (re-hashed before and after the review; 0 bytes > 127, 0 CR). Base 6869a3e655805afd3adbba43f99578dd79585934 (HEAD == base).
- Worktree `git status --short`: EMPTY before and after (this file is under the gitignored `.qa-s80/`).
- Inputs read: s81-common.txt, the brief `specs/S81_20_BRIEF.md` (R-S20-1..22), the R-A rulings via the common brief, the
  spec in full twice.
- Notes folder: `<scratchpad>/s81-20-review/` (base_a.log, review_body.txt, write_review.py). No scratch worktree, no
  mutation, no app import outside the runner.

## Verdict: APPROVE_WITH_CHANGES

No blocking defect: every load-bearing seam, refund primitive, envelope path and build-3 render path the spec cites was
re-measured and holds. The changes below are RED-table gaps (mutants no row kills, one vacuous recorder seam, quota rows
missing on three of five routes) and stated-limit / contract-risk additions. Fold them into the rulings before RED.

## Run evidence

```
tests/test_text_routes_error_mapping.py tests/test_http_400_cap_cut_mapping.py tests/test_text_error_envelope_no_raw_exception.py
tests/test_m18_usage_symmetry.py tests/test_text_routes_sse_contract.py tests/test_logger_no_query_leak.py
tests/test_s81_s05_request_context.py
241 passed, 63 warnings in 19.67s
[hermeticity] sentinel checked 241 test(s)
[netguard] blocked 22 attempt(s) from 22 node(s)   (the neutralized.supabase.invalid sentinel, baseline)
[pyt] tag=s20rev-base-a start=2026-11-05 08:51:11 end=2026-11-05 08:51:32 elapsed=21s bound=600s status=OK rc=0
```
(test_text_routes_sse_contract, test_logger_no_query_leak and test_s81_s05_request_context are source scanners of
text_routes / image_routes NOT in the spec's 1.10 runs; green at base; all three are in the 388-file comm set.)

## Verified (measured at 6869a3e6; held)

- text POST seams: consume :641-656 (`consumed_keys` dropped at :656), failure refund :703-707 keyless, surface :724 /
  return :726, delivery :728-799 (lifetime :793-796, `capture_result_status` :798). GET :868 / :884 / :942-944 / :988-993.
- stream chain: terminal capture :1172, W3-2 persist condition :1199-1202, `complete_response = data` :1221, yield :1270,
  finally :1271, first branch :1275, `elif had_error` :1359 (keyless refund :1372-1376), `else` :1394 (keyless
  :1403-1407). The `if` -> `elif` plan keeps every existing line; the intercept-before-latch design is sound (the second
  terminal reuses the same object; the first branch requires `complete_response is _s20_refusal`).
- Build 3 never opens the stream: `ENABLE_EXPO_FETCH_SSE_DEFAULT = false` at 683f56c0 SmartCompareApp/src/config/features.ts
  (and on main :52). Build 3 maps INSUFFICIENT_DATA to `home.errors.insufficientData` ("Thin data on that pair"; 683f56c0
  errorCopy.ts friendlyErrorKey, en.json:119) and camera `action === 'error'` to `results.emptyState.visionFailed`
  (683f56c0 ResultsScreen.tsx:348 / :805). PLAN section 0 holds for all four surfaces.
- camera: anon gate :234-251 (keys kept :251), `_refund_reserved_credit` :296-309 keyless + latch, `_refund_anon_credit`
  :313-330 keyed, consume :346-361, the enrichment loop :479-482 BEFORE the seam, the S81-10 pair gate :532-540, `_syn`
  :545, `try:` :546. BL2 re-located correctly. No `response_model` on `/image/identify` (:201), so `reason` survives.
- V2 marker `_is_product` True on every kept V2 candidate (openai_service :384-395); the V1 normaliser :678-684 has no
  underscore key; the orchestrator's search identity is brand + name + `variant=size_or_count` (scs :4347-4361) and the
  features ride `_vision_identity_fields` (:1353-1373) without reaching it: R-S20-4's precondition holds.
- usage_service: the lifetime-free path returns `{daily, monthly}` captured before the bump (:703-716); the standard path
  `{daily, monthly}` (:765-769); the S81-09 path `{daily}` plus `device_daily` only when a device HMAC exists (:431-435) and
  the `_DEVICE_DEBIT` stash; `_device_refund_keys` (:456-477) lets explicit `device_daily` keys win, else the stash,
  latched; the keyed `_refund_credit_sync` credits exactly the debited windows. A refusal never calls
  `record_lifetime_comparison`, so a lifetime-free slot is not burned: R-A3 holds on all three consume shapes.
- error_handler: three scoped blocks :188-195 / :200-211 / :217-231, `headers = None` :232; INSUFFICIENT_DATA is in none of
  them, so a fourth block is required and its proposed shape matches the precedents.
- H6 bodies scs :4515-4522 / :5287-5295: the error string carries U+2014; keys success / error / code / elapsed_seconds /
  total_cost / api_calls (the 2.2 prefix order).
- D1 (both flags ON refuse exactly what B1 stamps non-supported): the B1 stamp runs before `_strip_inference_markers`, the
  route gate after; the strip removes only `*inference_source*` keys and the value "model_knowledge" (response_builder
  :1423-1454), neither of which a B1 predicate reads (the `_field_confidence` markers tier3_synthesis / training_data
  survive); the REST post-builder tail (scs :4784-4859: freshness notice, unit metadata, cohort flag, L3 moderation, the G3
  tail, the profile update) adds no evidence. D1 holds as measured.
- G3 tail: the only REST returns between the category capture and the tail are :4515 (H6) and :4840 (moderation), both
  success:False; stream success terminals pass the tail; partials do not (spec Q1 stands).
- No log_search / save_comparison / record_lifetime / refund / consume call in structured_comparison_service, kb_serve or
  kb_ingest (grep empty): the route exit is the only billing site.
- `_reserve_comparison_credit` is called once (url_routes :273) and patched by no test (grep empty).
- The URL structured extractor passes JSON-LD `offers.price` / `aggregateRating.ratingValue` verbatim (strings) into
  `normalize_product_data` (url_extraction_service :1236-1247): R-S20-1 is needed.
- The E-row clean lists exist at the cited lines (s75 :60, s71_u13 :76, paid_route_metering :244, w4_13_measurement_truth
  :154, s80_b1 :52, s80_b3 :79, s03 :102, s09 :97, s10 :500, s18 :82); the W4-13 ledger test imports `_clean_flags` from
  test_w4_13_measurement_truth (:43-44), so E5 covers it.
- The comm-set file exists (388 lines, sha256 97218ca8... as stated); the reference grep alone gives 345 top-level files;
  nine `app.api.*` importers outside the set (auth / profile route tests) build bare apps with no error handler and import
  no edited module: not members by the union rule.

## Refuted claims

- RC-1 (1.1 URL row, minor): the `_reserve_comparison_credit` call is url_routes :273, not :274; `_url_row` is :277-287
  (not :279-289); the compare `try` :289-293 (not :291-295); the exception arm :294-303; the failure block :305-339. The
  insertion point "after :339, before :341" is correct.
- RC-2 (2.11, the test seams): "`camera_gate_reason` (module globals; recorders patch them)" is false for the camera.
  Section 2.6 imports `camera_gate_reason` BY NAME into image_routes, so a recorder set on `result_gate.camera_gate_reason`
  never sees the route's call: P4's "camera recorder 0 calls" is vacuous as written. (gate_reason / url_gate_reason are fine:
  `result_gate_refusal` calls them through result_gate's own globals.)
- RC-3 (2.6: "after the S81-10 pair gate, so a CATEGORY_NOT_LIVE refusal wins and is counted on ITS budget"): true of the
  code as specified but UNPINNED: R60 uses a fragrance pair that PASSES the S81-10 gate, so swapping the two blocks leaves
  every listed row green (correction C1).

## Corrections (fold into the rulings before RED)

- C1 (a mutant no row kills; quota lens): add M39 "the S81-20 camera block moved BEFORE the S81-10 pair gate" and a killing
  row R61: ENABLE_FRAGRANCE_ONLY_GATE ON + B2 ON, a NON-fragrance same-identity pair (two `Samsung` / `Galaxy S24 phone`
  dicts): body == `camera_refusal_body` (CATEGORY_NOT_LIVE keys, no `reason`), `record_refusal_async` exactly 1 call,
  compare 0, one reserved refund with the S81-10 label `usage_refund.image.category_not_live`, NO `result_gate:` row, no
  `[RESULT_GATE]` line.
- C2 (R-S20-22 scope; quota lens): the real-consume Lua-recorder rows exist only for text POST (R30) and camera (R58). Add
  params (or rows) for GET, the STREAM and URL with ENABLE_DEVICE_DAILY_QUOTA ON and the S81-09 FakeRedis: exactly the
  consumed `{daily, device_daily}` reach ONE DEVICE_REFUND_SCRIPT EVAL, lifetime 0, history 0, one row. Add a
  no-fingerprint STREAM variant (consumed_keys `{daily}` only, so the refund resolves through the `_DEVICE_DEBIT` stash):
  the stream refund runs in the generator's `finally` through fire_and_forget, the one exit whose keyed refund depends on
  the request-scoped stash being visible in the StreamingResponse task; pin it rather than assume it.
- C3 (mutant survivors): "`not had_error` dropped from the stream first branch" survives every listed row (no row has an
  `error` event and a refusal terminal in one stream). Add a row (stub yields `error` then `complete(BODY_V09)`: the
  existing `elif had_error` arm runs, keyless label `usage_refund.text_stream`, no `result_gate:` row) or record it
  EQUIVALENT with the measured fact that no orchestrator terminal follows an `error` event. Record "`complete_response is
  _s20_refusal` dropped" as EQUIVALENT (data is always replaced by the refusal once `_s20_refusal` is set).
- C4 (the RC-2 fix): 2.11 names `image_routes.camera_gate_reason` as the camera seam and P4's recorder is installed there,
  OR image_routes calls it through the module (`from app.services import result_gate as _rg`; the S81-10 module-attribute
  precedent). The spec picks one.
- C5 (1.1 line drift): rewrite the URL row with the RC-1 lines.
- C6 (a stated limit missing; quota lens): under ENABLE_ANON_USAGE_GATE ON with ENABLE_PAID_ROUTE_METERING OFF,
  `_refund_anon_credit` is a no-op (`anon_credit_refundable` requires metering, image_routes :249-251 / :325), so a camera
  result-gate refusal burns the anonymous credit; with metering OFF the authed camera consume never runs. Production has
  metering ON, so this is a stated limit the base non-delivery exits share, but the CLAUDE.md row and section 9 must say
  "both refunds where metering is ON", not "every refusal refunds".
- C7 (INFO-line coverage): R-S20-10 S9 asks for the caplog row on text / URL / camera; R32 covers POST only. Make R32 param
  POST / GET so the GET call site of the helper is pinned.
- C8 (regex reading, minor): `_URL_NUMBER_RE` over a str matches Unicode decimal digits (`\d` without `re.ASCII`) and
  `float()` accepts them, so an Arabic-Indic digit price counts as evidence. Add `re.ASCII` (with an R11 case) or state it
  as intended; the ruling says "numeric reading", so the spec must decide explicitly.
- C9 (4.2 list): name test_s81_s05_request_context.py, test_logger_no_query_leak.py, test_text_routes_sse_contract.py and
  test_s81_s10b_links_gate.py's URL-file source row explicitly in 4.2 (source scanners of the edited files; in the comm set
  but not in the stay-green list).

## Blocking issues

None.

## Contract risks

- CR-1 (quota lens: an unmetered paid loop): every text / stream / URL refusal is decided AFTER the paid fan-out (L4) and is
  refunded with no counter of its own (2.13: never `record_refusal_async`). A free user who submits pairs that land in
  no_evidence / same_identity (obscure names, two spellings of one product) runs unlimited paid compares (verdict LLM +
  Serper legs per cold pair) bounded only by the 10/min limiter; with B2 OFF the same request is billed and capped at
  3/day. The base already refunds H6 / TIMEOUT failures (the same class), so this widens an existing hole rather than
  opening a new one, but under FOCUS it needs a stated limit with a canary item (refusals per user per day) or a ruled
  budget (question 1).
- CR-2 (false category_conflict from the name stub; camera with V2 OFF = production): `classify_category_from_text` maps
  generic tokens (`hair` -> haircare, `skin` -> skincare, `mobile` / `phone` -> electronics; extraction_service :1183-1233,
  longest token first). A fragrance pair where one name carries such a word and no fragrance word (a "... Hair Mist" vs an
  "... Eau de Parfum"; a perfume named "Skin") reads [haircare or skincare, fragrances] and is refused pre-compare as
  category_conflict. L9 names "the stub's generic category words" only as a B1 inheritance; the CLAUDE.md row should name
  the camera false-refusal case and the canary should split camera refusals by reason.
- CR-3 (copy fit): CAMERA_GATE_MESSAGE ("Photograph each product in its own photo...") is rendered by no build-3 surface
  (vision_failed is client i18n), but a later client rendering `error` for `category_conflict` / `low_confidence` would
  show the wrong instruction; S81-11 must key its copy on `reason`, never on `error` (a cross-unit note for its brief).
- CR-4 (wire, additive): delivered text / stream / camera bodies gain `metadata.product_categories` under B2 ON even with B1
  OFF, and stored history rows carry it. Additive and allowed by section 0; listed so S81-11 never treats it as B1's
  presence signal.

## Pin collisions (already listed or confirmed absent)

- FY25 nine digests (E1); test_retro_w2_1 URL / camera pins (E2); T23 OpenAPI (no route parameter change; E3 env list);
  W4-13 flag-OFF ledger (flag OFF adds no label; E5 via the imported `_clean_flags`); w4_11 prompt digests (no prompt edit:
  no collision); copy-policy fences (no client file: no collision); test_global_anti_patterns (the camera string is
  fence-clean).
- Source scanners confirmed green at base and untouched by the planned text: test_s81_s05_request_context P07 and
  test_s81_s10_fragrance_gate P07 (the `valid_device_fingerprint(request.headers.get("x-device-fingerprint"))` needle once
  per file, no `request_context` substring: the spec adds neither); test_logger_no_query_leak (the image_routes
  `query_hash` format kept); test_text_routes_sse_contract (the `_BUNDLE_E_EVENT_TYPES` breadcrumb kept);
  test_s81_s10b_links_gate (URL files must not name the fragrance flag nor import category_gate by name: the 2.7 edit does
  neither).

## Questions for the orchestrator

1. CR-1: do result-gate refusals stay uncounted (a stated limit + a canary on refusals per user per day), or join a refusal
   budget (S81-10's REFUSAL_DAILY_BUDGET, or a new knob, which this unit's brief forbids)?
2. C4: the camera seam: a by-name import with the recorder on image_routes, or a module-attribute call through result_gate
   (the S81-10 precedent)?
3. C3: accept the two stream-branch operands as EQUIVALENT on the measured "no terminal after an error event" fact, or
   require the extra row?
4. C8: an ASCII-only numeric reading for URL strings, or Unicode digits accepted as evidence?
5. CR-2: is a pre-compare camera refusal on a stub-derived category_conflict acceptable while V2 is OFF, or should the camera
   conflict rule fire only when both categories come from the V2 `_category` (stub conflicts left to B1 telemetry)?
6. Spec Q5 / L17: G3 writes KB cards for a REFUSED no_evidence pair at identity high (measured in 1.7); confirm it is
   intended before RED pins it in R33.
