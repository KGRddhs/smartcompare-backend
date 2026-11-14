## INC-I1 PICTURE-MUST-MATCH: a dark guard so a result picture must name the product (ENABLE_IMAGE_RELEVANCE_GUARD)

Unit INC-I1 of the S95-FIX incident lane (SAFE, one adversary; spec `.qa-s80/INC-I1_UNIT_SPEC.md`, the batch rulings I1-R1..I1-R21, the RED gate GATE_INC_I1 GC-1..GC-14). Trigger: the owner's comparison of 2026-11-13 21:19 UTC, where the "Tyger" card showed a page of William Blake's poem as the product picture. Status: **merged, NOT yet proven** (once merged) until the owner's phone shows it. No production problem is called solved by this PR; the suites below are necessary gates, not the proof.

### What the flag does

`ENABLE_IMAGE_RELEVANCE_GUARD` (new, default OFF, read per call with the house idiom) and the knob `IMAGE_RELEVANCE_CANDIDATES` (5; a finite value is truncated and clamped to 1..10; unset, blank, garbage, inf and nan give 5).

ON, for TEXT compares only (camera products never get the guard):
- `structured_comparison_service._fetch_product_data` passes `relevance={brand, line, category, slot}` to `image_service.get_product_image_url` (through `image_relevance.relevance_kwargs`; flag OFF or a camera product = `{}` = the base call).
- Every cascade tier accepts a picture only when (1) no deny channel names a banned site (the image URL, the link or domain host, the source or title text, through the flag-free `deny_hosts.is_denied_url` / `is_denied_source`, so it holds with `ENABLE_DATA_GUARDS_V2` OFF as in production and ON; reason `denied`, checked first), (2) its URL is https (`scheme`), and (3) its text names the product: with a brand, a brand token (title or source text, or the registrable label of the link / domain host, alias-folded; a group joins only when the brand's tokens are its subset; plus the local {bvlgari, bulgari}) and at least one significant line token (`brand`, `name`); with an empty brand (every app compare while INC-R1 is OFF), EVERY significant line token and, for the categories fragrances and other, a fragrance word of the text or of a knowledge-graph `type` (`name`, `fragrance_word`). Host labels prove the brand only; a KG type supplies the fragrance word only.
- Tier 1 asks Serper Images for `<full name> perfume` (fragrances; else the full name) with `IMAGE_RELEVANCE_CANDIDATES` results and walks them in order (still ONE budget credit and ONE usage count per call); Tier 1.5b tests every knowledge-graph / organic / images item in the base precedence; Tier 3 (the LLM pick) runs only when one of `organic[:10]` passes, and its pick must be an https raster path on a passing result's host and never an organic page link; the piggyback is https-only.
- One INFO line per guarded call: `[IMG_RELEVANCE] product=<0|1|-> tier=<none|piggyback|search_payload|serper_images|llm_pick> outcome=<accepted|rejected|none> candidates=<n> reason=<none|scheme|brand|name|fragrance_word|denied>` (closed words and one int; the INC-X2a `[IMG_TIER]` lines are unchanged).
- The noon adapter copies the PDP's own Product JSON-LD image (its first member passing `jsonld_widen.allowed_image_url`) into its price dict as `image_url`; the post-Phase-1 price-page override then also requires https for text products (I1-R14). With `ENABLE_IMAGE_PIPELINE_V2` OFF (production) the noon picture replaces the cascade picture; with V2 ON, D08's allowlist refuses `f.nooncdn.com` (I1-R13, candidate follow-up INC-I1b).

OFF: byte-identical: no new keyword in the call, no new key in the noon dict, no new log line, no knob read (pinned by A-R16, A-P01, B-P01, B-P02, B-P06, with A-P02 and B-P03 pinning the flag-ON base-equal paths; the response and stored-row goldens of the comm set stay green).

Footprint (one commit): NEW `app/services/image_relevance.py` (a leaf: the stdlib, `category_gate`, `jsonld_widen`, `deny_hosts` at module level, `price_service` only inside functions; no logger, no I/O, no host literal); `app/services/image_service.py` (one import, four helpers, the keyword, the guard setup, four tier conditions, a `finally` for the one line; `extract_image_from_search`, `_is_valid_image_url`, `extract_image_via_gpt`, the Tier-3 prompt and the CancelledError arm untouched); `app/services/structured_comparison_service.py` (one import, one keyword expression in the image task, the I1-R14 condition in the override); `app/services/noon_service.py` (one import, one block before the return of `_confirm_pdp`); `CLAUDE.md` (the INC-I1 block before `## Tests`, the Feature Flags pointer clause, one sentence in the image paragraph); `.github/black-clean-paths.txt` (the leaf and the two RED files); the two frozen RED files. No client, migration, requirements, processors.json, price_service, jsonld_widen, category_gate or router edit.

### Defect ids -> RED node ids

| Defect (diagnosis id) | RED / PIN node ids (file A = tests/test_inc_i1_picture_must_match.py, B = tests/test_inc_i1_noon_and_wiring.py) | Behaviour under the flag |
|---|---|---|
| S95 D2 RC1: no relevance check on any tier, a bare-name Tier-1 query with num 1 (the Blake poem for "Tyger") | A: test_r03_relevance_truth_table (55 nodes), test_r04_image_query, test_r08_tyger_poem_rejected_at_tier1, test_r09_kg_poem_rejected_tier1_bottle_accepted, test_r10_walk_order_and_knob, test_r12_search_payload_each_item_tested, test_r13_tier3_precondition_and_pick, test_r20_kg_type_serves_the_fragrance_word_only, test_r21_tier3_pick_needs_a_raster_path_and_is_no_page, test_r22_tier3_reads_organic_first_ten, test_r23_tier3_related_but_failing_item_reason, test_r24_brand_from_source_link_or_domain, test_r25_kg_https_preference_and_snake_key | every tier tests the candidate's text; Tier 1 = `<name> perfume`, knob results, walked |
| S95 D2 RC2: the noon adapter drops the PDP's JSON-LD image | B: test_r01_noon_copies_the_first_https_raster, test_r02_noon_image_shapes (4), test_p05_noon_image_rejects (7); A: test_r05_first_https_raster | `price['image_url']` = the first https raster member |
| ADV R-1 (b): an http picture shows the grey tile on the iPhone (no ATS override) | A: test_r11_https_on_every_tier, test_r10 (the http walk item), test_r21 (raster pick); B: test_r04_override_requires_https_under_the_flag, test_p06_override_flag_off_keeps_the_base_branches (2) | https only on every tier and on the override (text products) |
| D1 F4 (merged here per ADV C-1; the image query only) | A: test_r04_image_query, test_r08 / test_r09 (the recorded query) | the word perfume for the fragrance category |
| H12 (g) / I1-R1: never a Fragrantica / Parfumo / Basenotes picture, with `ENABLE_DATA_GUARDS_V2` OFF (production) and ON | A: test_r17_denied_candidate_rejected_on_every_tier (9), test_r18_fragrantica_item_rejected_in_both_guard_states (2), test_r19_denied_organic_never_opens_tier3 (2), test_p03, test_p04; B: test_p05[denied_host] | reason `denied`, checked first, on every tier |
| The one log line (I1-8) and the 5 s cancellation | A: test_r14_one_line_closed_grammar, test_r15_cancel_under_the_flag | one closed-grammar `[IMG_RELEVANCE]` line per guarded call |
| The leaf contract | A: test_r01_flag_reader_table, test_r02_knob_table, test_r06_leaf_import_shape, test_r07_alias_reuse | house idiom; clamp 1..10; import shape; alias reuse |
| The scs wiring | B: test_r03_scs_passes_the_identity_under_the_flag | `relevance={brand, line, category, slot}` for text products |
| Flag-OFF byte identity (F1-F7) | A: test_r16_flag_off_with_relevance_is_the_base_call (4), test_p01_base_call_full_config, test_p02_flag_on_without_identity_is_the_base_call; B: test_p01_noon_flag_off_full_config (2), test_p02_scs_flag_off_exact_call (2), test_p03_scs_camera_product_never_gets_the_identity, test_p04_override_branches_for_a_noon_image | the base call, dict, lines and override |

Counts: 118 nodes in the two frozen RED files (RED 29 functions = 99 nodes, all failing at base on an AssertionError only; PIN 10 functions = 19 nodes, green at base). The RED round's mutation table on the thrown-away prototype: 66 mutants, 66 KILLED (GC-3; the adversary re-runs a sample on these bytes).

### Deliberate pin changes (spec 4.1)

| E-row | test | change |
|---|---|---|
| none | - | GC-4: no existing pin changes (the review's collision sweep and the head runs below confirm it) |

### Gates (every pytest through the lane wrapper `harness/gate.py`, one at a time)

```
[pyt] tag=inc-i1-green-on start=2026-11-14 22:25:59 end=2026-11-14 22:26:02 elapsed=3s bound=600s status=OK rc=0   (118 passed, 1 warning)
[pyt] tag=inc-i1-green-off start=2026-11-14 22:31:26 end=2026-11-14 22:31:29 elapsed=3s bound=600s status=OK rc=0   (118 passed, 1 warning)
[pyt] tag=inc-i1-head-img start=2026-11-14 22:32:22 end=2026-11-14 22:32:30 elapsed=8s bound=600s status=OK rc=0   (112 passed, 14 warnings)
[pyt] tag=inc-i1-head-pins start=2026-11-14 22:32:36 end=2026-11-14 22:33:02 elapsed=25s bound=1200s status=OK rc=0   (972 passed, 15 warnings)
[pyt] tag=inc-i1-head-scan start=2026-11-14 22:33:09 end=2026-11-14 22:33:34 elapsed=25s bound=1200s status=OK rc=0   (371 passed, 15 warnings)
[pyt] tag=inc-i1-head-pins2 start=2026-11-14 22:33:41 end=2026-11-14 22:35:04 elapsed=83s bound=1200s status=FAIL rc=1   (1 failed, 373 passed, 6 warnings)
[pyt] tag=inc-i1-ciorder start=2026-11-14 22:35:42 end=2026-11-14 22:35:59 elapsed=17s bound=1200s status=OK rc=0   (783 passed, 15 warnings)
[pyt] tag=inc-i1-ciorder-rev start=2026-11-14 22:37:52 end=2026-11-14 22:38:09 elapsed=17s bound=1200s status=OK rc=0   (783 passed, 15 warnings)
```

- The two RED files: 118 passed with `ENABLE_IMAGE_RELEVANCE_GUARD=true` and with `=false` exported (every row sets its own flags; netguard 0).
- The spec 1.10 sets at head equal the base pass state: img 112 passed, pins 972 passed, scan 371 passed (base 112 / 972 / 371, none failing). The remaining 4.2 identity pins (test_s81_s07_meas_harness, test_s75_fanout_identity, test_serper_record_usage, test_s78_serper_key_memo, test_hermeticity_pins): only `tests/test_s81_s07_meas_harness.py::test_r35_fixtures` fails, a base-record id (box noise: CR bytes of this CRLF checkout, GC-5 Q-6).
- The CI-order set (spec 7.3 + the two RED files, 14 files) in alphabetical and in reverse order: green both ways (the one netguard block is the known base node `test_comparison_response_image_url.py::TestOrchestratorWiring::test_organic_results_passed_to_image_service`, listed in `tests/.network_attempt_baseline.txt`).
- Comm set (zero-regression gate): 712 files = the RED round's 710 (union rule at 731bcddf, sha256 5e2f0266...) + the two RED files; re-derived at head with the same rules and the new leaf as a seed (closure 85 modules incl. app/main.py; derived set = base + the two RED files, nothing else). 30 chunks of at most 25, bound 1200. HEAD failure ids: 28; base record ids: 28; **branch-only NEW: NONE**; base ids not failing at head: none.

<details><summary>The comm chunk [pyt] lines</summary>

```
[pyt] tag=inc-i1-comm-head-01 start=2026-11-14 22:38:16 end=2026-11-14 22:38:47 elapsed=31s bound=1200s status=OK rc=0
[pyt] tag=inc-i1-comm-head-02 start=2026-11-14 22:40:13 end=2026-11-14 22:40:38 elapsed=25s bound=1200s status=FAIL rc=1
[pyt] tag=inc-i1-comm-head-03 start=2026-11-14 22:45:13 end=2026-11-14 22:45:38 elapsed=25s bound=1200s status=OK rc=0
[pyt] tag=inc-i1-comm-head-04 start=2026-11-14 22:45:45 end=2026-11-14 22:46:49 elapsed=64s bound=1200s status=OK rc=0
[pyt] tag=inc-i1-comm-head-05 start=2026-11-14 22:49:02 end=2026-11-14 22:49:17 elapsed=15s bound=1200s status=OK rc=0
[pyt] tag=inc-i1-comm-head-06 start=2026-11-14 22:49:24 end=2026-11-14 22:49:37 elapsed=13s bound=1200s status=OK rc=0
[pyt] tag=inc-i1-comm-head-07 start=2026-11-14 22:50:00 end=2026-11-14 22:50:20 elapsed=19s bound=1200s status=OK rc=0
[pyt] tag=inc-i1-comm-head-08 start=2026-11-14 22:50:27 end=2026-11-14 22:51:05 elapsed=39s bound=1200s status=OK rc=0
[pyt] tag=inc-i1-comm-head-09 start=2026-11-14 22:51:12 end=2026-11-14 22:52:09 elapsed=57s bound=1200s status=OK rc=0
[pyt] tag=inc-i1-comm-head-10 start=2026-11-14 22:52:16 end=2026-11-14 22:53:06 elapsed=50s bound=1200s status=OK rc=0
[pyt] tag=inc-i1-comm-head-11 start=2026-11-14 22:54:59 end=2026-11-14 22:55:26 elapsed=26s bound=1200s status=OK rc=0
[pyt] tag=inc-i1-comm-head-12 start=2026-11-14 22:55:33 end=2026-11-14 22:55:45 elapsed=12s bound=1200s status=OK rc=0
[pyt] tag=inc-i1-comm-head-13 start=2026-11-14 22:55:52 end=2026-11-14 22:56:11 elapsed=19s bound=1200s status=OK rc=0
[pyt] tag=inc-i1-comm-head-14 start=2026-11-14 22:56:18 end=2026-11-14 22:56:45 elapsed=27s bound=1200s status=FAIL rc=1
[pyt] tag=inc-i1-comm-head-15 start=2026-11-14 22:56:51 end=2026-11-14 22:57:28 elapsed=37s bound=1200s status=FAIL rc=1
[pyt] tag=inc-i1-comm-head-16 start=2026-11-14 22:57:35 end=2026-11-14 22:58:01 elapsed=26s bound=1200s status=FAIL rc=1
[pyt] tag=inc-i1-comm-head-17 start=2026-11-14 22:58:08 end=2026-11-14 22:58:21 elapsed=13s bound=1200s status=OK rc=0
[pyt] tag=inc-i1-comm-head-18 start=2026-11-14 23:06:48 end=2026-11-14 23:09:34 elapsed=166s bound=1200s status=OK rc=0
[pyt] tag=inc-i1-comm-head-19 start=2026-11-14 23:09:41 end=2026-11-14 23:11:04 elapsed=83s bound=1200s status=OK rc=0
[pyt] tag=inc-i1-comm-head-20 start=2026-11-14 23:11:11 end=2026-11-14 23:12:04 elapsed=54s bound=1200s status=FAIL rc=1
[pyt] tag=inc-i1-comm-head-21 start=2026-11-14 23:12:27 end=2026-11-14 23:14:36 elapsed=128s bound=1200s status=FAIL rc=1
[pyt] tag=inc-i1-comm-head-22 start=2026-11-14 23:14:42 end=2026-11-14 23:15:34 elapsed=51s bound=1200s status=FAIL rc=1
[pyt] tag=inc-i1-comm-head-23 start=2026-11-14 23:15:41 end=2026-11-14 23:16:18 elapsed=37s bound=1200s status=OK rc=0
[pyt] tag=inc-i1-comm-head-24 start=2026-11-14 23:16:25 end=2026-11-14 23:17:11 elapsed=46s bound=1200s status=OK rc=0
[pyt] tag=inc-i1-comm-head-25 start=2026-11-14 23:17:17 end=2026-11-14 23:17:59 elapsed=41s bound=1200s status=OK rc=0
[pyt] tag=inc-i1-comm-head-26 start=2026-11-14 23:18:05 end=2026-11-14 23:18:41 elapsed=35s bound=1200s status=OK rc=0
[pyt] tag=inc-i1-comm-head-27 start=2026-11-14 23:18:48 end=2026-11-14 23:19:15 elapsed=27s bound=1200s status=OK rc=0
[pyt] tag=inc-i1-comm-head-28 start=2026-11-14 23:19:21 end=2026-11-14 23:19:56 elapsed=34s bound=1200s status=OK rc=0
[pyt] tag=inc-i1-comm-head-29 start=2026-11-14 23:21:07 end=2026-11-14 23:21:13 elapsed=6s bound=1200s status=OK rc=0
[pyt] tag=inc-i1-comm-head-30 start=2026-11-14 23:21:20 end=2026-11-14 23:21:23 elapsed=3s bound=1200s status=OK rc=0
```
</details>

- Lint: `ruff check --select E9,F63,F7,F82` clean on the four app files and the two RED files (ruff 0.16.5); `py_compile` clean; black 26.5.1 `--check` clean on the leaf and the two RED files (both join `.github/black-clean-paths.txt`, I1-R17); pure ASCII added lines (the only high bytes in the diff are the existing characters of the two rewritten CLAUDE.md lines); CRLF kept in the edited files (no whole-file diff).
- Client fences (GC-10, the fourteen repository-reading suites by path, once, the last gate; jest 29.7.0 through the orchestrator's junction): `Test Suites: 1 failed, 13 passed, 14 total`; `Tests:       4 failed, 236 passed, 240 total`; `[jest] tag=inc-i1-fences start=2026-11-14 23:23:02 end=2026-11-14 23:23:10 rc=1`; the 4 failed nodes are the four accepted `config/nativeBundle.w37` drift nodes (d5, k2, k4, k5), as in the G-INC-1 and S81-12d records.
- Commit: 5cf13f622394f4f9133b46b026dc77376b0038b1 (the pre-commit hook ran: black, ruff, py_compile, gitleaks and the added-line sweep).

### Stated limits (spec section 9 as amended by the rulings; adversary minors join here by LC-4)

- L-I1-1 Precision first: a correct picture whose text lacks the brand (when known) or a line token, or, with an empty brand, any significant line token or a fragrance word, is rejected and the placeholder tile shows. A knowledge-graph card titled with the line alone fails the brand test when the brand is known (title only, I1-3) and the product falls to the paid Tier 1. The golden-pair effect is NOT measurable hermetically (no recorded Serper payload of the golden pairs in the repo); the phone proof measures it.
- L-I1-2 With an empty brand (every app compare while INC-R1 is OFF) every significant line token plus a fragrance word decides; a picture of another product whose title carries all the typed tokens and a fragrance word still passes (I1-R8 (1): the unit guarantees "never the poem", not "the right bottle").
- L-I1-3 (I1-R2) A non-fragrance product with an empty brand needs its line tokens only (no fragrance word); an empty or non-string category reads as other (fragrance word required, GC-5 Q-3).
- L-I1-4 More Serper Images spend: a rejected free knowledge-graph or organic picture now falls to the paid Tier 1 (one daily credit and one lifetime usage count per call, not per result); Tier 3 runs less often. The 5 s race is unchanged, so a new Tier-1 call can be cut by it.
- L-I1-5 No vision check, perceptual hash, size or HEAD recheck; the raster-extension test applies to Tier-3 picks only (I1-R10): a knowledge-graph or Serper thumbnail without an extension is still accepted, and an SVG there shows the placeholder through ProductImage onError.
- L-I1-6 No cross-script matching (an Arabic-titled picture of a Latin-typed line fails the line test, and the reverse); no stemming beyond the listed plurals (I1-R12).
- L-I1-9 / I1-R13 With `ENABLE_IMAGE_PIPELINE_V2` ON the noon picture (`f.nooncdn.com`) is refused by D08's host allowlist and the cascade picture stays (candidate follow-up INC-I1b before any V2 flip).
- L-I1-10 Cache residue: a noon price cached in L1 while the flag is ON carries `image_url` for its TTL (7 days for `page_scrape_jsonld`), so after a rollback the override can still show that picture until the entry expires; a noon price cached BEFORE the flip carries none until it expires or is refreshed; the L2 row never stores it.
- L-I1-12 Pair fairness may re-select the displayed price after the override ran: the noon picture can sit beside another store's price for the same identity.
- L-I1-13 The Tier-3 pick check is host-based: a correct image on a CDN host unrelated to a passing organic result's host is rejected.
- L-I1-14 The camera path gets no relevance guard and no https rule on its override (GC-5 Q-4). It is not fully unchanged: under the flag a camera compare priced by a fresh noon fetch (or by an L1 noon entry written while the flag was ON) would show the noon JSON-LD picture through the base override; no camera compare reaches that override while vision is off (adversary m1). The CLAUDE.md row's word 'unchanged' is carried to the next CLAUDE.md touch.
- L-I1-15 The `[IMG_RELEVANCE]` reason names only the LAST rejection; per-reason counts are not logged.
- L-I1-16 / I1-R15 Serper's billing for a 5-result images query is not measured hermetically (the code counts one call).
- L-I1-18 The stop, noise, concentration and placeholder word sets are closed lists in the leaf; a brand made only of excluded words counts as empty; a brand such as "D&G" folds to one-letter tokens and also counts as empty.
- I1-R6 The live path keeps the Serper tiers, narrowed by this guard: a ruled interim deviation from the PLAN_S81 VERIFY "Images" correction (the end state, KB or retailer JSON-LD images only, belongs to the KB track).
- D1 F4 is only partly addressed (the image query's category word); the shopping and unified queries' category word is out of scope (R-10).
- L-G1 `_related` (Tier-3 host relation) relates a dotless pick host (for example a bare top-level label) to every link under it; such a pick cannot load, so the client shows the placeholder (never a wrong picture). Not hardened mid-run to keep the gated bytes stable.
- L-G2 `_first_image` prefers the first https key of an item; an item whose https value is on a banned host is rejected whole (`denied`), even when another key of the same item holds a clean https image.
- L-G3 The GC-5 Q-4 camera exemption of the override https rule (D-G8) and the Q-3 empty-category reading (D-G7) carry no frozen row: the adversary may ask for gate rows (LC-4: a minor is a stated limit by default).
- L-G4 The deny on titles (D-G5) uses `is_denied_source`'s whole-token match of the four banned labels; a product title that merely names one of those sites as a word is rejected (precision first).

### Adversary (correctness, one lens; SAFE class): SOUND, 0 blocking, 0 major, 8 minors

Verified on HEAD 5cf13f62: 118 rows ON and OFF, 29 mutants re-run on the GREEN bytes (25 killed, including the deny-list set M38-M43 and the flag gates; the four survivors N1-N4 are the ruled GREEN behaviours that carry no frozen row, stated as L-G3 and below), the CI-order set both ways (783 passed), the source-scanning pins and CLAUDE.md readers (1,039 passed), three comm chunks re-run with no new id. The minors are stated limits here (LC-4): (m1) see L-I1-14; (m2) RESPONSE DELTA under the flag: the noon `image_url` rides `products[i].price` and `overview.products[i].price` through `public_price_view` (additive, read by neither live bundle); (m3) with `ENABLE_DATA_GUARDS_V2` OFF (production) an https page image on a banned host from another producer would still pass the post-Phase-1 override (only noon, which denies them, and a cached Zyte-seed image produce such images; out of I1-1 scope); the in-cascade piggyback check is unreachable from the orchestrator (it passes `page_scrape_image=None`); (m4) with DG ON, banned image URLs are dropped by the base validator before the guard, so those denials log `reason=none`, not `denied` (canary reason mix); (m5) under the guard an organic list with no passing result logs `[IMG_TIER] tier=llm_pick outcome=skipped` and `[IMG_RELEVANCE] tier=none ... reason=none` (canary item); (m6) N1-N4 (the camera exemption, the empty-category reading, deny-before-https, the knowledge-graph website / description deny channels) have no frozen row; (m7) tests/test_seed_zyte_guard.py reaches an edited module through scripts/ and sits outside the comm closure; measured green at HEAD (6 passed); (m8) the leaf calls the private `deny_hosts._registrable_label`: a rename of that helper would make the guard raise under the flag (a coupling to keep in mind on any deny_hosts edit).

### PROOF ON THE PHONE (H6, R0-1, I1-8 as amended by I1-R8; nothing here needs AI text)

Preconditions (read-only, the relay): the running web deployment's commit contains this merge; the dated flip line `ENABLE_IMAGE_RELEVANCE_GUARD` ON on web; the dated state of `ENABLE_IMAGE_PIPELINE_V2` (OFF expected) and of INC-R1's flag (OFF for check 1). Record for every pair: the pair's resolved category and the account's consent version.

1. "stronger with you" vs "Tyger" (typed as on 2026-11-13). Must be visible: the Tyger card NEVER shows the Blake poem (the hermetic guarantee is "never a picture whose text lacks the line token or a fragrance word"; a perfume picture titled with Tyger and a perfume word may still show). Backing: the two `[IMG_RELEVANCE]` lines of that compare (product=0 and product=1: Tyger `outcome=rejected` or `none`, never `accepted` with the poem) and the saved row's `products[i].image_url` (no poem host, no `http://`).
2. The noon picture: on a never-compared noon-won pair, or on the 2026-11-13 pair only after about 2026-11-20 21:19 UTC (the 7-day L1 / L2 price windows): the noon-won card shows the noon bottle photo. Backing: the `[PRICE] BH adapter direct hit for ... via noon.com` line in the same compare (a FRESH noon fetch) and the saved row's `image_url` an https URL on `f.nooncdn.com`.
3. Two golden pairs that had photos before: "Aventus" vs "Layton" and "Sauvage EDP" vs "Bleu de Chanel EDP". Must be visible: each card shows the NAMED product's own bottle, read by the owner (not just "a photo"). Backing: per product the `[IMG_RELEVANCE] ... outcome=accepted` line and its `tier=` value, and any `[L2.6] Phase 1 race timeout for image_url` line. A placeholder or a wrong bottle on a golden product is a FINDING for the relay (L-I1-1 / L-I1-2), not a pass.
4. On every saved row of these compares no cascade `image_url` starts with `http://`.

The unit stays "merged, NOT yet proven" until the relay files the dated phone result.

### Owner steps (names only; a dated ledger line per step; flips are the owner's, one window each on an explicit yes)

None to merge. (1) The relay sets `ENABLE_IMAGE_RELEVANCE_GUARD` ON on web on the owner's yes, in its own window; `IMAGE_RELEVANCE_CANDIDATES` stays unset (5). (2) If `ENABLE_PRICE_CACHE_WARMER` is ever set true on `price-warmer`, `ENABLE_IMAGE_RELEVANCE_GUARD` joins `price-warmer` in that window (I1-R19; until then the warmer's 7-day noon cache writes carry no `image_url`). (3) The PROOF ON THE PHONE above. (4) Rollback: set the flag false (or unset it); L1 noon prices cached while ON keep their picture up to 7 days (L-I1-10).

Canary watch (I1-R15), read by the relay in the flip window: the `[IMG_RELEVANCE]` reason mix (brand / name / fragrance_word / scheme / denied), the `[BUDGET] serper_images daily budget exhausted` count, the `[IMG_TIER] serper_images` ms and the image race timeouts, and the Serper dashboard counter delta of one comparison (the billing for `num` 5).

Once merged, the unit is "merged, NOT yet proven" until the relay files the owner's dated phone result; the hermetic rows above are necessary and are never presented as the proof (H6).

🤖 Generated with [Claude Code](https://claude.com/claude-code)
