# B1 adversarial spec review: RESULT-STATUS + TELEMETRY (Fable adversary, 2026-10-20 ~00:55 AST)

Spec under review: `.qa-s80/B1_UNIT_SPEC.md`, sha256 `05d48e2cef8c17ca472e6cad9696fa582ac2ba37eedc2b823aeb74dc00289bd6`
(re-hashed at the start of this review; 659 lines; 0 bytes > 127). Worktree `sc-s80-b1` at
`81df2b641454e0301cca51a3ba01bf8ef3d7e649`, `git status --short` empty before and after this review
(only this file and the spec under the gitignored `.qa-s80/`). Every file:line below was re-read at
the base sha in this run. Probes ran in a DETACHED scratch worktree under the reviewer's notes folder
(`<scratchpad>/b1-review/wt`, cut at 81df2b64, removed after the run) through the bounded runner:

```
[pyt] tag=b1rev-probe start=2026-10-20 00:03:05 end=2026-10-20 00:03:08 elapsed=3s bound=600s status=OK rc=0
[hermeticity] sentinel checked 1 test(s); [netguard] blocked 0 attempt(s) from 0 node(s)
```
Probe file `tests/test_zz_b1_review_probe.py` (scratch only, never in the worktree); output
`<scratchpad>/b1-review/probe_out.json`. No production, Railway, Supabase, Sentry or network access;
no .env read; the pinned venv only.

## Verdict: APPROVE_WITH_CHANGES (two blocking corrections, both inside the spec's own text; no design change)

The unit's shape (one stamp site in `build_comparison_response`, a pure predicate module, flag-OFF
byte identity pinned with full configuration, unflagged allowlist widening per R-A1(a)/R0-2) is
sound and the anchors hold by symbol. Two items would make GREEN red against pins the spec lists as
"must stay green", and three RED rows are unsatisfiable as written; they are corrections to the
spec text, not to the design. Nothing here touches the build-3 contract: every new key is additive,
flag-OFF is byte-identical, and the camera refusal envelope is untouched (B1 never refuses).

---------------------------------------------------------------------------------------------------

## 1. Refuted claims (each with the measured truth)

| # | spec claim | measured truth | where |
|---|---|---|---|
| RC1 | 2.7: the sampler "returns exactly the SDK's rules 3/4 when the flag is OFF (`parent_sampled` else 0.1), so the sampling decisions are identical OFF" | FALSE whenever `traces_sample_rate` != 0.1. On sentry-sdk 2.68.1 `_set_initial_sampling_decision` (tracing.py:1215-1232) uses the sampler's return and NEVER consults `client.options["traces_sample_rate"]` when a sampler is callable (only on a raise). The spec hardcodes `_TRACES_SAMPLE_RATE = 0.1` in the sampler. The two child-process harnesses force `kw["traces_sample_rate"] = 1.0` (`tests/test_sentry_channels_u8d.py:263-265`, `tests/test_retro_w1_1.py:376-378`) and assert transactions: `test_sentry_channels_u8d.py:951-956` ("every request that reached a route yielded a transaction") and the W1-1b transaction-scrub rows. With B1's sampler installed and the flag OFF those requests sample at 0.1 -> both files go red (and flaky). Both are listed in 4.2 as "must stay green". | tracing.py:1215-1232; the two test files |
| RC2 | 2.2 `real_spec_rows`: "neither value a str whose `norm()` is in `NA_VALUES`" and R6 "7/7 `"N/A"` vs `"N/A"` -> 0" | CONTRADICTORY as written: `norm("N/A")` = `"n a"` (the `/` becomes a space), which is NOT in `NA_VALUES = {"", "n/a", "na", "none", "unknown", "-"}`. A literal implementation (the probe) counted the six remaining Manama `"N/A"` rows as REAL (`specs_real_rows: 6` on the rebuilt row 12 after one field was replaced). R6 and R8 are unsatisfiable by the spec's own definitions; R14/R13 inflate. `response_builder` compares `value.strip().lower()` against `_SPEC_NA_TOKENS` (:590, :677-678). | probe `w412_row_12_rebuilt.specs_real_rows`; response_builder.py:590 |
| RC3 | R15 / R17: FY25 `rest_q_full` / `rest_pair_full` bodies have `data_coverage == 4` ("local_bhd 120 both, rating 4.5 both, 3 real specs, dims") | 3. The FY25 fakes return IDENTICAL specs (`_specs`, test_s75_fanout_identity.py:129-130), prices (:132-135) and ratings (:140-142) for both products, so every `scoring_v2` dimension ties (measured: price 85/85, reviews 88/88, value 88/88, feature 90/90, futureproof 90/90) and the dims fact is False under BOTH readings. Measured AUDITABLE coverage 3 on both scenarios. | probe `fy25_rest_q_full`, `fy25_rest_pair_full` |
| RC4 | R16: vision pair `Casio G-Shock watch` vs `Dior Sauvage eau de parfum` -> `product_categories == ["electronics","fragrances"]`, status `unsupported_category`; L2 "a watch beside a perfume" | `classify_category_from_text("Casio G-Shock watch")` returns `"other"`: `_CATEGORY_SYNONYMS` (extraction_service.py:1164-1215) has no watch/casio token (electronics = electronic, phone(s), smartphone(s), mobile(s), laptop(s), tablet(s), gadget(s)). The pair resolves to `["other","fragrances"]` -> coherent -> `supported_result`. R16 is unsatisfiable as written. Measured: `Samsung Galaxy S24 phone` -> electronics, `Apple MacBook laptop` -> electronics, `Dior Sauvage eau de parfum` -> fragrances. | probe `stubs` |
| RC5 | R13: w412 rows 15-19 through the builder -> `data_coverage >= 3` | The REBUILT row 15 has BOTH prices pended by the chokepoint (`amount None, unavailable True, source_method None` after `is_price_showable(..., enforce_correctness=True)`, response_builder.py:1700-1712; the minimised fixture's `local_bhd` price lacks the identity stamp the exact gate needs) and every rebuilt dimension ties (price 75/75 limited_data, reviews 87/87, value 75/75, function 70/70, build 30/30, review 88/88, reliability 77.2/77.2, feature_match 100/100). Price fact False, dims False, ratings True, specs <= 1 real row -> coverage <= 2. The tally's "full coverage" was over the STORED rows, not a rebuild. | probe `w412_row_15_rebuilt` |
| RC6 | R8: `metadata.product_categories == ["grocery","grocery"]` with `product_categories=[c, c]` where `c` = the row category | rows 12-14 carry `category_used == "other"` (`category == "other"`), so `[c, c]` is `["other","other"]`; the assertion contradicts the recipe. | fixture rows 12-14 |
| RC7 | 1.2 / 2.5: "A success:False body never reaches these points (camera: the unsuccessful branch returns :532-534 / the envelope :575-578 is excluded by comparison_unsuccessful)" | FALSE with `ENABLE_PAID_ROUTE_METERING` OFF: `unsuccessful_not_billed` is `comparison_unsuccessful and paid_route_metering_enabled()` (image_routes.py:465-467), so with metering OFF an unsuccessful result skips :503-534, is logged, SAVED (:555) and lifetime-bumped, and when the envelope flag is also OFF reaches `return result` at :580 with `success: False`, `action: "comparison"` (the test-env default; production has both ON). The emitter at :579 would then tag `result_status=failed` on a non-delivery. R18 covers metering ON only. | image_routes.py:457-467, :503-534, :575-580 |
| RC8 | 2.2 `same_identity` / 1.6: products read from `overview.products` first; `variant` compared | `overview.products[i].variant` is `_compose_variant_string(pd, category_used)` (response_builder.py:1915), a DISPLAY string composed from specs: the probe's rebuilt row 12 shows `["red","blue"]` after the colour field was set, while the raw `products[i].variant` is `[None, "250g"]`. The overview mirror also carries no `rating_derived` key (it nulls `rating` instead, :1920). Reading the mirror for identity axes compares colour captions, not sizes. | probe `ov_variant` vs `raw_variant`; response_builder.py:1896-1945 |
| RC9 | 1.1: `metadata.update(metadata)` at :2109-2112, `verdict_scrubbed` :2115-2116, margin :2119-2120, `result["winner_index"]` :2231 | :2125-2126, :2129-2130, :2134-2135, :2243 (the builder tail is 12-14 lines lower than cited; `tier_context` :2249, `_strip_inference_markers` :2260, `return result` :2262 are right). Symbol-resolvable; GREEN must anchor by symbol. | response_builder.py |
| RC10 | 3 step 3: `"product_categories": product_categories` added to "the two `_partial_build_ctx.update({...})` dicts (:4284-4288, :4923-4927)" | The REST site is an `.update({...})` at :4284-4288 and sits BEFORE the write-back (:4296); the STREAM site is a dict-literal ASSIGNMENT `self._partial_build_ctx = {...}` at :4921-4931 and sits AFTER the write-back (:4912). The capture must happen before :4284 on REST (or a second update after it) and before :4912 on the stream. | scs :4280-4300, :4905-4932 |

Claims checked and CONFIRMED (not refuted): `metadata.query` is written only in the builder; `_field_confidence` survives into `specs.products[i].specs` at the stamp site (probe `specs0_has_fc: true`) so the tier-3 exclusion is live (L3 holds); the chokepoint pends an `estimated` price before the stamp site (rebuilt row 12: `amount None, unavailable True`), so X19 is a real mutant and fact (a) "equals the chokepoint verdict by position" holds; rows 12-14 carry a non-empty `products[i].reviews.review_summary.consensus` (so `section_status.reviews == available` in R8 holds); R14 row 24 rebuilt: `dims_strict == 1` (reliability 65/90, not in either `missing_data`), ratings one-sided, prices pended -> coverage 1 once RC2 is fixed; `history_routes._extract_winner_index` present-with-None -> None (:38-39) and the four pinned shapes do not cover it (P7 is new); `test_u8d_pin_options_init_kwargs_kept` asserts a 3-tuple, not the kwarg key set, so `traces_sampler=` is additive there; T23 compares the `$ref` closure of the ten operations (`_referenced_components`, :948-997), `FeedbackRequest` is outside it; 027's CHECK is `('correct','wrong','unsure')` (migrations/027:46-61) and `mattered_most` has no CHECK; the comm-set rule sizes to 268 module-reference files + 25 SmartCompareApp scanners + the pins at base (`grep -rlE`, this run); `HistoryScreen.tsx:442/:473-481` tolerates `winner_index: null` (no highlight, both tiles from `runner_up_image_url`); contract_freeze finding 1 reads only `metadata.partial` and the six `overview.winner` keys; `sentry_sdk.capture_message(message, level=None, scope=None, **scope_kwargs)` accepts `tags=` (scope.py:1993-2000); `dedup_brand_name("GUESS","GUESS!") == "GUESS GUESS!"`, `("Guess","GUESS !") == "GUESS !"` (R3's second row passes through the brand + Jaccard arm, not identity equality).

---------------------------------------------------------------------------------------------------

## 2. Corrections (apply to the spec before RED)

C1 (BLOCKING, RC1) 2.7 sampler OFF branch: return `parent_sampled` when not None, else the LIVE
client option, never a module constant:
```python
client = sentry_sdk.get_client()
rate = client.options.get("traces_sample_rate") if client is not None else None
return rate if rate is not None else 0.1
```
(or keep one module constant `_TRACES_SAMPLE_RATE` and pass `traces_sample_rate=_TRACES_SAMPLE_RATE`
to `init`, PLUS read the client option in the sampler so a harness that forces 1.0 is honoured).
P5 gains a row: with `traces_sample_rate` forced to 1.0 on a recording init, the sampler returns 1.0
for a non-compare path with the flag OFF. Gate step 3 adds `tests/test_sentry_channels_u8d.py` and
`tests/test_retro_w1_1.py` as identity nodes run ALONE (child processes). X26/X28 keep their rows.

C2 (BLOCKING, RC2) 2.2: NA matching uses `value.strip().lower() in NA_VALUES` (the
`response_builder._SPEC_NA_TOKENS` idiom), not `norm(value)`; `norm` stays for identity text only.
R6 adds `"N/A"`, `" n/a "`, `"NA"`, `"-"`, `"None"` as explicit NA rows and one positive row
(`"n a"` is NOT NA). P10 keeps `_SPEC_NA_TOKENS <= NA_VALUES`. Mutant X10a: "NA check through `norm`"
(killed by the new R6 rows).

C3 (RC3) R15 and R17: `data_coverage == 3` and tag `"3"` on the FY25 full scenarios (price, ratings,
specs; dims tie). Keep a `== 4` case only on a fixture whose dims differ (lane1, if RC5's measurement
allows, or a synthetic scoring_result with price 85/75).

C4 (RC4) R16 and L2: use `Samsung Galaxy S24 phone` vs `Dior Sauvage eau de parfum` (measured
electronics / fragrances); add the measured negative: `Casio G-Shock watch` -> `other` ->
`["other","fragrances"]` coherent -> `supported_result` (this is also the honest statement of L2:
the per-product stubs recognise generic category words only, so most brand-only names are `other`
and the conflict is reachable only when BOTH names carry a category word).

C5 (RC5, RC6) R13: assert the MEASURED rebuilt values (`result_status == supported_result` needs
coverage >= 1 -- ratings True on rows 15-19 gives exactly that; `identity_confidence == "medium"`;
`data_coverage >= 1`), never `>= 3`; or feed the price dicts the identity the exact gate needs. R8:
`metadata.product_categories == ["other","other"]` (or pass `["grocery","grocery"]` explicitly and say
so). R9 (lane1): the lane1 price dicts carry `url, in_stock, retailer, source_method` and no identity
stamp (measured keys); whether `is_price_showable(enforce_correctness=True)` pends them on a re-feed is
NOT measured here -- RED measures `price: available` / `data_coverage` / `identity_confidence` on the
rebuilt lane1 bodies before asserting `>= 3` / `high`.

C6 (RC7) 2.5 camera call site: gate the emitter on `not comparison_unsuccessful` (equivalently
`result.get("success") is True`), not on code position. R18 gains the metering-OFF + envelope-OFF
variant (the `_Service` returning `success False`; zero entries; the :580 body unchanged). Same guard
on text (already by construction) and the stream (already `success is True`).

C7 (RC8) 2.2 `evidence_facts` / `same_identity` / `product_is_placeholder` / `rating_is_real`: read
brand, name, `variant`, `size_or_count`, `distinguishing_features`, `rating`, `rating_derived`,
`review_count`, `image_url` from the RAW `result["products"]` alias (the same `product_data` dicts,
post-chokepoint, post-scrub; present on every built body and every stored text/camera row) and fall
back to `overview.products` only when the alias is absent. Prices may stay on either (the chokepoint
mutates `product_data` in place, so both views agree). R11 adds a builder row where the two products
differ only in a spec-derived display variant (colour) and are still the same identity.

C8 (RC9, RC10) Re-anchor the builder tail by symbol (`result["tier_context"]` / `_strip_inference_markers`),
and state the stream ctx as the dict literal at scs:4921-4931 with the capture placed before :4912
(REST: capture before the `.update` at :4284, or a second `.update` after :4296).

C9 (mutants no RED row kills) Add: (a) a V09-shaped row that is BOTH placeholder AND no-evidence,
asserting `reasons == ["placeholder_identity", "same_identity", "no_evidence"]` exactly (kills
"emit only the first reason" and "wrong precedence" together); (b) a telemetry row on a non-supported
body asserting `winner_emitted == "false"` and `unknown_product_count == "2"`; (c) a direct
`assess_result({"success": False, ...})` -> `failed` row (`failed` is otherwise unreachable in B1,
since the builder always writes `success: True` at :1893 and every emitter site is success-only;
state that in L-new); (d) `product_categories` passed as a 3-list / None -> key omitted, coherence
True (2.12 row with no test); (e) X17 as a concrete row: lane1 grocery with product 1's `specs`
emptied -> `section_status.specs == "partial"`; (f) a `stamp_camera_stage_timings` row where
`vision_moderation_ms` is None -> key skipped, the other two written.

C10 (telemetry tags) `vision_ms` / `compare_ms` as raw integers are unbounded-cardinality Sentry TAGS.
Either bucket them (`compare_ms_bucket` = 5 s steps as a string enum, `vision_ms_bucket` = 1 s steps)
or carry the raw ints as `extras` (ints only; the PII rule is about strings). The client precedent
(`wall_time.<stage>_ms` tags) exists but is the same anti-pattern. Recommend bucketed tags + raw ints
in `extras` and extend R17's grammar check to extras. Owner's call (Q10).

C11 (1.10 / section 7) The three base runs cover 351 nodes; the two child-process Sentry files and
`tests/test_s71_u13_compare_auth_required.py` were NOT measured at spec time -- RED measures them
first, alone (they are the collision class C1 found).

---------------------------------------------------------------------------------------------------

## 3. Blocking issues

B1. RC1/C1: the sampler as written reddens `tests/test_sentry_channels_u8d.py` (:951-956 and every
transaction row) and `tests/test_retro_w1_1.py` (the W1-1b transaction rows) in CI, both listed in
4.2 as "stay green and unedited". Fix the OFF branch to the live option.

B2. RC2/C2: fact (c) is unsatisfiable by the spec's own `norm` + `NA_VALUES`; R6/R8 cannot go green
and `data_coverage` would over-count on every stored row (the MYEZ-003 class would read
`supported_result`). Fix the NA comparison.

Everything else is a correction to a RED expectation or a wording fix; none changes the flag, the
stamp site, the key set, or the flag-OFF identity invariant.

---------------------------------------------------------------------------------------------------

## 4. Contract risks (build 3, App Review, production)

CR1. `metadata.winner_index = None` on non-supported rows: after the flip and before the C1 OTA,
build-3 History shows no winner highlight and placeholder tiles on BOTH cards for stamped rows
(contract_freeze 5b :293, RULE 10; `HistoryScreen.tsx:442, :473-481` tolerate null; no crash). The
spec records it (L6). It is a build-3-visible change at the flip, not at merge; the flip is
post-approval by R-A2. Accepted, stated.

CR2. The sampler changes the SDK code path in BOTH flag states (sampler vs rate). With C1 the decision
distribution is identical OFF; without C1 it silently diverges from any `traces_sample_rate` that is
not 0.1. Under the flag the four compare paths go to 100 % transaction sampling: Sentry transaction
quota is the owner's reading (8.2 step 3 says so).

CR3. `overview.winner.supported` and the six new `metadata` keys are additive; build 3 reads only
`metadata.partial` and the six existing `overview.winner` keys (contract_freeze finding 1). Confirmed.

CR4. Camera route with metering OFF: an unsuccessful body is persisted and lifetime-bumped today
(image_routes.py:553-569; pre-existing, not B1's), so if the emitter ever fires there it would count a
non-delivery as a delivery in the status series (C6 closes it).

CR5. Billing (R-A3): B1 abstains nowhere, adds no `fire_and_forget` label and no `log_search` kwarg;
the W4-13 ledger (`labels` = the fire_and_forget sequence, test_w4_13_flag_off_ledger.py:17-18) is
unaffected. Confirmed by reading the emitter design (a direct synchronous call).

CR6. Telemetry tag cardinality (C10): raw ms values as tags.

CR7. `profile_routes.py:75/:97/:141` (recent decisions) still crown stamped non-supported rows (L13,
Q7): a Home surface the owner will see on build 3 after the flip. Recommend the same `result_status`
skip in this unit (one more reader, same unflagged rule, same P8-style pin) -- Q7 = yes.

---------------------------------------------------------------------------------------------------

## 5. Pin collisions not listed in section 4.1

PC1. `tests/test_sentry_channels_u8d.py` (child process; `traces_sample_rate` forced 1.0 at :263-265;
transactions asserted at :951-956 and the per-scenario transaction rows) -- RED under the spec's
sampler (RC1). Fixed by C1 (no re-record).
PC2. `tests/test_retro_w1_1.py` (child process at :376-378, the W1-1b transaction-scrub rows) -- same.
PC3. None of: T23 (closure excludes `FeedbackRequest`), the FY25 digests (unused kwarg OFF), the
W4-11 prompt digests (no prompt change), `test_retro_w2_1` URL pins (flag-OFF no-op before :219),
the W4-13 ledger fixture (no new label / kwarg), the copy-policy fences (no client file),
`test_u13e_url_detect_guard.py` (pins the two detect operation objects only),
`test_u3b_sharing_branch_removed.py:158` (one component description), `test_m13_29_feedback_uuid.py`
(constructs `FeedbackRequest` with existing fields only), `test_feedback.py::test_save_feedback_success`
(asserts named keys, not the exact record), the two allowlist superset files (set membership only).
PC4. `tests/test_stage_timings.py:163-164` asserts `stage_timings_ms` ABSENT with the memo off; B1
never creates the dict -- not a collision, but P3/R20 must reset `scs._DEBUG_STAGE_TIMINGS = None`
exactly as that file does (:20).

---------------------------------------------------------------------------------------------------

## 6. Answers / positions on the spec's open questions (for the orchestrator's rulings)

Q1 category conflict -> `unsupported_category` / `category_conflict`: agree (the pair is not one
supported category; B2's refusal copy can still say "check the products"). Q2 four levels: agree,
with C7 (raw alias). Q3 AUDITABLE reading: agree, with C2 (NA via strip/lower) and the measured row
24 = 1. Q4 four paths incl. the stream: agree. Q5 smart pick skip: yes (MYEZ-027). Q6 add
`identity_confidence` + `reasons`: yes. Q7 profile recent decisions: yes, this unit (CR7). Q8 name:
`comparison_result_status` fine. Q9: no second `is_price_showable` call (confirmed by the probe: the
chokepoint already pended the estimate; a second call would re-stamp `guard_rejected`).

## 7. Numbered questions for the orchestrator

1. C1: accept the live-option fallback in the sampler (`sentry_sdk.get_client().options["traces_sample_rate"]`), or install the sampler ONLY when the flag is ON at init (NOT per call, so a flip needs a redeploy)? The per-call sampler with the live-option fallback is the recommendation.
2. C2: `NA_VALUES` matched by `strip().lower()`; confirm `norm` stays for identity text only.
3. C3: R15/R17 at the measured 3; keep a 4-coverage case on a synthetic scoring_result?
4. C4: R16 pair = `Samsung Galaxy S24 phone` vs `Dior Sauvage eau de parfum`; keep the Casio negative?
5. C5: may RED feed the lane1/w412 price dicts the exact gate's identity stamp to reach `price: available`, or assert the rebuilt (pended) values as measured?
6. C6: gate the camera emitter on `not comparison_unsuccessful`; add the metering-OFF R18 variant?
7. C7: identity/rating axes from the raw `products` alias (fallback overview) -- confirm.
8. C9(c): is the `failed` status kept in the vocabulary with a direct `assess_result` row only (unreachable through any B1 exit)?
9. C10: bucketed ms tags + raw ints in extras, or raw tags as spec'd?
10. CR7/Q7: apply the `result_status` skip to `profile_routes` in this unit?
11. The 1.10 NOT-MEASURED set (both Sentry child-process files, T17/T23, the metering file): RED runs them ALONE at base first and records the lines (the collision C1 found lives there).

Not done in this review: no run of the FY25 gather-partial scenario (R15's open item stays RED's);
no lane1 rebuild through the builder (C5 lists it as RED's first measurement); no mutation run (no
GREEN bytes exist); the comm set was sized by grep (268 + 25 + the named pins), not computed with
`scripts/comm_set.py`; the Sentry transaction behaviour was read from the pinned SDK source, not
executed against a client. Scratch worktree removed after the probe; `git worktree list` verified.
