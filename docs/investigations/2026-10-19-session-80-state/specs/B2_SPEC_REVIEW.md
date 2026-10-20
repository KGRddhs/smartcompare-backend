# B2 RESULT-GATE: adversarial spec review

Unit B2 (ENABLE_RESULT_GATE). Reviewer: adversarial spec reviewer (session 80). Spec reviewed:
`.qa-s80/B2_UNIT_SPEC.md`, sha256 46b6847c9cbcecffa776aaa15ebc972179468973c6e69377639c43503b5d84f1 (re-hashed
at 20:18 and again before this report; the scratchpad copy is byte-equal). Base 95cf6f864b4e70980ca191daa064c0118e223c13;
worktree HEAD == base, `git status --short` empty before and after (this file is under the gitignored `.qa-s80/`).
Every probe ran in a detached scratch worktree under the review notes folder (`<scratchpad>/b2_review/wt`, created
at the base sha, removed with `git worktree remove --force`, absent from `git worktree list` at 20:48). Notes,
probe sources and outputs: `<scratchpad>/b2_review/` (notes.md, probe_url_price_types.py/.out,
test_zz_b2_review_probe.py.txt, probe_out/*.json, probe_camera_pred.py/.out, probe1.log, missed_comm_base.log).
No .env read, no network, no production probe, no personal value. Pure ASCII, LF.

## Verdict

APPROVE_WITH_CHANGES, with two BLOCKING corrections that must land in the spec before RED (BL1 URL evidence reading
counts only numeric JSON-LD values and refuses real priced Bahrain PDP pairs; BL2 the camera placeholder rule is
evaded by the route's in-place size enrichment) and four MAJOR corrections (comm set misses two files incl. the
W4-13 flag-OFF ledger; the W4-13 clean list is a missing pin collision; the real-orchestrator V10 row must be
mandatory; nine surviving mutants have no killing row). The text/stream half is sound and measured: the V10 shape
is refused as no_evidence through the real orchestrator, and B1's stamp equals the route re-assessment there.

## Runs (bounded runner, one process at a time)

```
probe1  tests/test_zz_b2_review_probe.py (scratch worktree at 95cf6f86; measurement-only rows)
        6 passed, 10 warnings in 3.23s
        [hermeticity] sentinel checked 6 test(s)
        [netguard] blocked 0 attempt(s) from 0 node(s)
        [pyt] tag=b2rev-probe1 start=2026-10-20 20:35:22 end=2026-10-20 20:35:27 elapsed=5s bound=600s status=OK rc=0
missed  tests/test_w4_13_flag_off_ledger.py tests/test_s78_tier_fill_residual_guard.py (base bytes)
        56 passed, 11 warnings in 4.56s
        [hermeticity] sentinel checked 56 test(s)
        [netguard] blocked 0 attempt(s) from 0 node(s)
        [pyt] tag=b2rev-missed-comm start=2026-10-20 20:44:02 end=2026-10-20 20:44:08 elapsed=6s bound=600s status=OK rc=0
```
Two pure-python probes (no app import beyond result_gate + text_sanitize, `-I -B`): probe_url_price_types.py
(bs4 over every captured HTML fixture) and probe_camera_pred.py (the merged predicates on camera dicts).

## Re-measurement of the cited file:line (at 95cf6f86)

All matched except RC9 (one off-by-two). Checked: text_routes.py :523-570, :578-771, :774-955 (GET), :958-1382
(stream: :1021-1034, :1064, :1121-1170, :1148-1163, :1219, :1220-1372, :1224, :1225-1245, :1264, :1298-1301,
:1307, :1323, :1354), :445-479 (`_failure_log_cost`, `_failure_log_message`, `_partial_log_note`); image_routes.py
:192, :217-240, :282-334, :285-298, :302-318, :341-363, :365-473, :452-457, :466-473, :475-484, :497, :501-503,
:511-595, :597-647, :646; url_routes.py :59-88, :122-224, :144, :160-200, :202-223; error_handler.py :74-91,
:113-143; result_gate.py :35-50, :83-85, :136-141, :171-183, :193-205, :210-221, :236-239, :258-272, :504-548,
:553-561 (659 lines); response_builder.py :21, :1416-1450, :2255, :2264-2295, :2297, :2303; scs :193-194, :985,
:1006-1009, :1038, :3848, :4188-4250, :4302-4327, :4371-4377, :4628, :4800-4801, :4818-4819, :4945-4947,
:5025-5026, :5049-5050, :5064-5073, :5472, :5555-5556, :5564-5565; usage_service.py :129-135, :331-430, :472-505;
extraction_service.py :1307-1341; client api.ts :1038-1124, :646-730 (build 3 text compare = GET /text/compare REST),
errorCopy.ts :76, en.json :119, :853, :854, ResultsScreen.tsx :291-353, failureClassification.ts :104-109;
tests: test_s75_fanout_identity.py :60-64, test_retro_w2_1.py :172-176, test_s71_u13_compare_auth_required.py
:76-84, test_s80_b1.py :1146-1157, :270-285; CLAUDE.md :476-479. B4 seams re-read from the shared object store
(`git diff 81df2b64 96676f1f`, no B4 worktree touched).

## Refuted claims (measured truth, file:line)

RC1. D4 / 2.2 `url_gate_reason` ("page price on both sides ... counts") and 1.12 ("URL_V03, two page prices, no
specs -> None"). The base URL path copies JSON-LD `offers.price` and `aggregateRating.ratingValue` verbatim
(url_extraction_service.py:283, :317, :320, :289, :325 -> normalize_product_data :553-564 `"amount": raw.get("price")`,
`"rating": raw.get("rating")`); the numeric-price AI prompt (:365) runs only when the title or the price is missing
(:503); the JSON-LD path sets no `specs` (extract_generic_data :302-347; :560 `raw.get("specs", {})`). Measured over
the 27 captured retailer pages in tests/fixtures with a top-level Product node: price types str 12 / int 5 / float 5 /
None 5, so only 10 of 27 pass `_num(amount) and amount > 0`; rating str 4. Real pairs through base
extract_generic_data + normalize_product_data + the spec's D4 predicate (implemented verbatim from 2.2):
curl_bh_bheshop vs curl_bh_godukkan (two Bahrain registry sources, real prices) -> `no_evidence`;
ae_lulu vs ae_samawa -> `no_evidence`; noon BH pair delivered only through the numeric rating; boutiqaat pair only
through int ratings; fragrancex vs perfume.com (the same Dior Sauvage) -> `same_identity`. The spec's URL_V03 fixture
(numeric prices) does not represent the common real shape, so P11 would pin the wrong predicate green.

RC2. D2 ("B1's telemetry already assesses at the same five exits, so B1's production distribution sizes B2 one to
one") and the 8.1 canary ("vs B1's non-supported share (text/stream/camera)"). False for the camera:
`sentry_service.capture_result_status` (:671-698) assesses the POST-compare body (`assess_result` at :687 with no
`vision_confidences`), while B2's camera decision is PRE-compare on other predicates (any low vision confidence; the
V2 `_category`; no no_evidence). Neither the low-confidence share nor the V2-category conflicts appear in B1's
distribution, and B1's camera no_evidence share (3/16 corpus rows) is never refused by B2 (D5). True for text and
stream: probe A measured B1's stamp == the route re-assessment (V10, REST and stream).

RC3. 1.12 "confidence / vision categories are not stored -> NOT MEASURABLE offline". The minimised corpus omits
them, but every saved camera row stores `metadata.identified_products = public_vision_products(products)`
(image_routes.py:542 / :547, saved at :615-621), and public_vision_products strips only underscore keys
(openai_service.py:293-301), so the V1 `confidence` (normaliser :672) is in production rows. The any-low share is
measurable by an owner names-only read before the flip.

RC4. 7.6 "No test-support module ... is edited, so no importer union applies" and the 182-file comm set. E1 edits
`UNIT_ENV`, which `_scenario` pops and restores (test_s75_fanout_identity.py:200-202, :228-232); 
tests/test_s78_tier_fill_residual_guard.py imports `_scenario` (:43) and is NOT in comm_set.txt.
tests/test_w4_13_flag_off_ledger.py (the R-A3 W4-13 flag-OFF ledger: it drives every route through
tests/fixtures/_gen_w4_13_flag_off_ledger.py, which imports test_w4_13_measurement_truth's autouse fixtures (:69-70)
and wraps test_retro_w2_1._install (:162-167), an E2-edited module) is NOT in comm_set.txt although 4.2 lists it.
The reference grep misses it because the route strings live in the fixtures-dir generator. Both green at base
(56 passed, [pyt] above). Session-80 addendum: a missed importer that is green is still a MAJOR.

RC5. The camera placeholder rule (2.6, R42, R43): the gate seam (after :483) runs AFTER the in-place size
enrichment at image_routes.py:439-442 (`p["name"] = f"{p['name']} {size_or_count}"`). Measured with the merged
predicates: brand "Unknown" + name "Unknown Product" + size_or_count "100ml" -> name "Unknown Product 100ml" ->
`product_is_placeholder` False (True before the enrichment); the same for "60 Capsules" and for a known brand with
name "Unknown Product" + "100 ml". A vision read that sees a size and no name escapes `placeholder_identity` and,
when its confidence is not low, goes to the paid compare (and, D5, is delivered crowned).

RC6. MYEZ-004 (V07) closed by B2 under the planned activation order (V2 before RESULT_GATE, R-A2). With V2 ON,
VISION_FEAT (GUESS / GUESS! with features polyurethane / cotton) is pinned to COMPARE (P9). The features never reach
the compare: `_vision_identity_fields` documents "These keys never reach product_data or the wire" (scs:1346-1367)
and both products search the same `full = f"{brand} {vname}"` (scs:4239-4249). Measured: normalised identity_text
equal True; `same_identity` raw True; with the V2 view False. So two different shirts are compared on ONE search
identity and delivered crowned and billed (camera not gated after the compare, D5), while B1 stamps the built body
`needs_identification` (the built product dicts carry no `distinguishing_features`). B1 and B2 disagree on the same
request; MYEZ-004 is closed only with V2 OFF. The spec follows R-A5 literally, so this needs a ruling (Q-R3).

RC7. R8 "pins the equivalence" (D1: "when both are ON, B2 refuses exactly the bodies B1 stamps non-supported").
R8 compares `gate_reason` and `assess_result` on the SAME body; since `_GATE_REASON_BY_ASSESS` maps every reason a
success:True body can carry, R8 is a tautology that only kills a mapping-drop mutant. The builder-time stamp (before
`_strip_inference_markers`, response_builder.py:2273-2303) vs the route re-assessment is pinned by R24 (category)
only. The equivalence itself holds on text (probe A; B1 R16); the claim is true but R8 is not its pin.

RC8. M21 "killed by R9, P6": equivalent. `gate_reason` and `url_gate_reason` each return None unless
`success is True`, and on text/URL a success:False result leaves through the failure branch before the gate
(text_routes.py:655-698, url_routes.py:173-200); removing the success check of `result_gate_refusal` alone changes
no output.

RC9. 1.1 / 2.4 "GET consume `:832-847`", "GET the same at `:832`": `usage_consumed = False` is :834 (832-833 are
comments); the POST anchors :617 / :630 are exact. Trivial.

## Blocking issues

BL1 (URL over-refusal, RC1). `_url_price` / `_url_rating` must accept the JSON-LD string shape. Rule (stdlib `re`
only, P11-clean, inside result_gate): a price is an int/float (not bool), or a str whose strip matches
`^\d{1,3}(?:,\d{3})*(?:\.\d+)?$|^\d+(?:\.\d+)?$` (commas as thousands separators dropped), finite and > 0; a rating
is the same numeric reading with 0 < r <= 5; anything else is not evidence. RED/PIN rows from the real fixtures:
(curl_bh_bheshop, curl_bh_godukkan) and (ae_lulu, ae_samawa) through the URL route under ON -> 200 delivered (both
measured `no_evidence` with the spec's predicate); a str price "0", "abc", "1e400" -> not counted; a one-sided price
pair with no rating/spec -> no_evidence (kills the `and`->`or` survivor S5). Replace URL_V03 by an envelope built from
real fixtures (strings), keep the synthetic numeric one as a second param. State the cross-retailer same-product
refusal (RC1 fragrancex vs perfume.com) as a limit or rule on it (Q-R2).

BL2 (camera placeholder evasion, RC5). Decide placeholder (and `_ph0` / `_ph1` for the need_second_product branch)
on the vision identity BEFORE the size enrichment: snapshot `[(p.get("brand"), p.get("name")) for p in products]`
before :439 (a pure read; flag OFF output unchanged) and pass the pre-enrichment names to `camera_gate_reason` /
`camera_placeholder_sides` (or strip a trailing `size_or_count` from the name before the test). RED rows: ("Unknown",
"Unknown Product", size "100ml", confidence medium) + a real high pair side -> placeholder_identity, compare 0; the
same with a known brand -> placeholder_identity. Also say in L9 that B1's merged camera stamp has the same hole (its
built names carry the size).

## Corrections (binding unless ruled otherwise)

C1 (MAJOR, RC4). Comm set += tests/test_s78_tier_fill_residual_guard.py, tests/test_w4_13_flag_off_ledger.py
(184 files). Recompute with the importer union of the three edited modules: test_s75_fanout_identity ->
test_s78_all_timeout_cap_as_timeout, test_s78_tier_fill_residual_guard, test_s80_b1; test_retro_w2_1 ->
tests/fixtures/_gen_w4_13_flag_off_ledger.py (-> test_w4_13_flag_off_ledger), test_paid_route_metering, test_s80_b1,
test_s80_b3_vision_identity_v2, test_w4_13_measurement_truth (-> test_m18_preverdict_disconnect_refund);
test_s71_u13_compare_auth_required -> test_s71_u13_pins; plus every importer of any test module GREEN edits (E5-E7).

C2 (MAJOR, pin collision). 4.1 gains E5: tests/test_w4_13_measurement_truth.py `_clean_flags` (:154-160) +=
"ENABLE_RESULT_GATE". It guards that file AND the W4-13 flag-OFF ledger generator (imports it, _gen :69-70), whose
stubs carry no price/rating/spec (DELIVERED :254, PARTIAL :257, URL_OK :441; test_retro_w2_1 DELIVERED :323-327)
and would be refused as no_evidence with the flag in a developer env. Expected too (gate 4 confirms, list them up
front): E6 tests/test_s80_b1.py `CLEAR` (:243-246; B1 drives V09-like bodies through the routes) and E7
tests/test_s80_b3_vision_identity_v2.py `UNIT_ENV` (:170-173; camera rows with identical or low pairs).

C3 (MAJOR). The real-orchestrator V10 row is mandatory, not optional (5.2). Measured at base through the FY25 harness
with the V10 leaves (explicit pair "Hyper X MIC" / "Hyper X2 MIC"; price None; rating None; specs {} and the all-dash
dict; reviews {}): success True, winner_index 0, B1 stamp `partial_no_winner` coverage 0, the route re-assessment
identical, reasons ["no_evidence"], REST and stream; every dim score 75/75 with caption limited_data. So the route row
(POST via `fy_text` with those leaves) is RED-able (200 at base) and satisfiable (400 no_evidence + ledger shape),
and a B1 ON + B2 ON variant pins D1 (stamp non-supported <-> 400). This is the tester's MYEZ-003/MYEZ-007 shape.

C4 (MAJOR, mutants no listed row kills). Add a killing row per survivor or record it as equivalent:
S1 camera placeholder tested on side 0 only (no side-1-only placeholder row; add (real high, Unknown) );
S2 camera low tested on side 0 only (state the side in R41; add (high, low));
S3 drop `not _is_low(_other)` in the need_second_product precedence (add (placeholder, low other) -> action error);
S4 `gate_log_message` dropping CAMERA_GATE_REASONS (assert the camera row message "result_gate:low_confidence" in R41);
S5 URL fact `and` -> `or` (one-sided price row, BL1); S6 URL placeholder side 0 only (one-sided URL placeholder row);
S7 builder stamp not gated (drop `result_gate_enabled() and`): add M24, killed by the FY25 nine digests and by P8 --
P8 MUST call the builder with `product_categories=["electronics", "fragrances"]` (B1 OFF, B2 OFF), otherwise it is a
vacuous PIN (None never stamps); S8 `_surface_comparison_failure` reason arm not gated: wire-equivalent while the
handler is OFF -- add a direct OFF unit row (an INSUFFICIENT_DATA dict carrying reason "no_evidence" raises a detail
exactly {code, error}) or record it equivalent; S9 the INFO template: a caplog row asserting exactly one
`[RESULT_GATE] refused input=%s reason=%s` record at INFO per refusal with constant args and no query text (text, URL,
camera); M21 reclassified as equivalent (RC8).

C5. One placeholder on the camera: PLAN section 3 B2 and identity_winner F3 say placeholder -> `action:'error'`;
the spec's `need_second_product` renders `needMorePhotos` = "We spotted one product. Bring both items into the frame
for a side-by-side." (en.json:853), the copy R-A6 calls contradictory, to a user who already sent two photos. Default
to `action:'error'` (drop M11 and the `_is_low` precedence; R42 becomes an error row) unless Q-R5 keeps it; if kept,
S3's row is mandatory.

C6. Camera low_confidence sizing and semantics: 1.12 and 8.1 state that the share is measurable from stored camera
rows (RC3) and add the owner's names-only read (camera rows with any `identified_products[].confidence == low`) to
the activation precondition; note that V1 semantics differ (openai_service.py:595 "low (best guess)", :603 "Identify
products even WITHOUT packaging ... (confidence=low)"; normaliser :672 passes the raw value, default medium) from
V2's (:372-375, unknown -> low), so a V2 rollback with B2 ON changes what is refused (Q-R4).

C7. Satisfiability: R26 (anonymous text) and R46 (anonymous camera + fingerprint) cannot pass with
ENABLE_COMPARE_AUTH_REQUIRED ON (the U13 guard rejects an anonymous caller before the route body); state that these
two rows set the auth flag OFF explicitly, unlike every other ON row.

C8. B4 seam (2.7): E2 edits the exact tuple line B4 96676f1f edits (test_retro_w2_1.py:175, B4 appends
"ENABLE_URL_MODE_V2") and E3 appends at the same CLEAN_ENV anchor B4 appends to (test_s71_u13_compare_auth_required.py
after :83, now also B3's line) -> textual conflicts in either merge order; resolution: keep every name. The url_routes
adjacency analysis of 2.7 holds (B4 hunks at -85,6 / -136,6 / -155,7 / -187,6 leave >= 2 unchanged lines to B2's
regions).

C9. 8.1 sizing sentence: add "URL refusal rate unsized (URL compares are never persisted, R0-1; BL1)" and "camera
low_confidence and V2-category refusals not in B1's distribution (RC2)". The current "1 of 36 ... 0 of 26 real
deliveries" covers text and camera post-compare only.

C10. R8 is described as the mapping-completeness pin; D1 is pinned by R24 and C3's both-flags V10 row (RC7).

C11. CAMERA_GATE_MESSAGE "Could not confirm two different products. ..." collides with the house no-scary-copy
vocabulary (tests/test_global_anti_patterns.py:70 bans "couldn't"); build 3 never renders it (vision_failed copy), C1
might. Prefer a neutral sentence, e.g. "Photograph each product in its own photo so we can tell them apart." Minor.

C12. L6 also covers the camera: the B2 camera row is a new search_logs row in both W4-13 states (base pre-compare
exits 1-5 write none).

C13. DEFECT_LEDGER / PR-body mapping: MYEZ-003 and MYEZ-012 closed for text/stream/URL only (the measured production
no_evidence class, 3/16 camera rows, stays delivered and billed, L1/Q-R6); MYEZ-004 closed with V2 OFF only unless
Q-R3 rules (RC6); MYEZ-002 on camera only after BL2.

## Contract risks

CR1. URL over-refusal on build 3 (BL1): two real priced PDPs answered 400 INSUFFICIENT_DATA ("Thin data on that pair
-- swap in two products with brand and model").
CR2. URL same product at two retailers (a price check) refused as same_identity (measured fragrancex vs perfume.com
Dior Sauvage); the JSON-LD path carries no variant/size, so R-A5's size veto never applies on URL.
CR3. Camera any-low under V1 (V2 OFF or rolled back) refuses unpackaged-product photos the V1 prompt marks low; share
unsized; build-3 copy "Snap each product in its own photo" for a user who did.
CR4. Under V2, an identical-search pair with differing features is delivered crowned and billed (RC6).
CR5. need_second_product renders the contradictory needMorePhotos copy (C5).
CR6. Stream (dormant on build 3): scores/verdict frames precede the refusal terminal (L3, stated).
CR7. Additive-only check passed: `reason` on the 400 envelope (parseApiError api.ts:1049-1124 reads code/error/detail/
retry_after_seconds only), `reason` on camera bodies (ResultsScreen routes by action; no code key, so
isCameraEngineOutageResponse stays false), `metadata.product_categories` under B2 alone; no key removed, renamed or
retyped; no 503, no new code (error_handler.py:34 FEATURE_DISABLED path never reached).

## Pin collisions

PC1 W4-13 flag-OFF ledger (via test_w4_13_measurement_truth `_clean_flags`): missing from 4.1 (C2).
PC2 B4's test edits overlap E2/E3 (C8).
PC3 FY25 nine digests: E1 correct; FY25 also kills the not-gated builder stamp (S7/M24).
PC4 T23 OpenAPI: none (no route parameter or body field; `_reserve_comparison_credit` and the camera closure are not
routes) -- verified.
PC5 w4_11 prompt digests: none (no prompt edited).
PC6 test_retro_w2_1 URL pins: unchanged flag OFF; E2 is the local-env clean list.
PC7 copy-policy fences: no client copy; backend sentence C11.
PC8 B1 P11 purity (test_s80_b1.py:1146-1157): BL1's parser must be stdlib `re` inside result_gate; no price_service.
PC9 test_s80_b1 CLEAR / test_s80_b3 UNIT_ENV (local env, C2).

## Questions for the orchestrator

Q-R1. BL1: parse numeric strings inside result_gate (stdlib, recommended) or normalise the URL envelope in url_routes
before the gate?
Q-R2. URL same_identity: refuse per R-A5 (spec), or exempt pairs whose two URLs have different hosts (the cross-
retailer price check)?
Q-R3. Camera same identity under V2: amend R-A5 for the camera pre-compare so the distinguishing_features veto applies
only when the compare can use the features (today it cannot: search identity = brand + name, scs:4241), i.e. refuse
equal normalised identities regardless of features; or accept that V07 under V2 is delivered (MYEZ-004 then open
under V2)?
Q-R4. Camera low confidence: any-low (spec, eval T01) or both-low; and apply it only to V2-shaped products (the
`_is_product` marker) so V1's "low without packaging" is not a refusal? Size it from stored rows first (C6).
Q-R5. One placeholder: need_second_product (spec Q2) or action:'error' (PLAN B2, F3, R-A6)?
Q-R6. L1: PLAN section 0 item 2 binds camera refusals to pre-compare; confirm L1 and the C13 scoping of
MYEZ-003/MYEZ-012.
Q-R7. The relayed owner request "also update context files": this reviewer wrote only this review (sc-docs-70 is
read-only for agents). The DEFECT_LEDGER rows (MYEZ-001/002/003/004/007/011/012/027: B2 spec reviewed,
APPROVE_WITH_CHANGES with BL1/BL2) and the session ledger line are the orchestrator's to write.

Not done in this review: no implementation prototype (the local-.env sweep of gate 4 is not measured; C2's E6/E7
are from inspection of the stub shapes), no run of the spec's NOT MEASURED files (RED's G-3 job), no B4 worktree
read (B4 bytes read from the object store only).
