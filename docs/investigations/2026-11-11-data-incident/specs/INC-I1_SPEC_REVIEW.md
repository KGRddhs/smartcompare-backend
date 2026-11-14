# INC-I1 PICTURE-MUST-MATCH: adversarial spec review (READ-ONLY round)

- Unit: INC-I1 PICTURE-MUST-MATCH, flag `ENABLE_IMAGE_RELEVANCE_GUARD`, knob `IMAGE_RELEVANCE_CANDIDATES`. Reviewer: the adversarial spec reviewer of the S95-FIX lane (Opus 5.5), 2026-11-14. Job: refute the spec.
- Spec: `.qa-s80/INC-I1_UNIT_SPEC.md`, sha256 `5539e84481bf3094b86d32554877f0a1063e597c89ecc5a153b5cda2e6c9d3c4` (re-hashed first: equal), 592 lines, 110,532 bytes. Read in full twice (start and before reporting), with the common brief, PLAN_S81 (Standing constraints, the VERIFY corrections, Fable rulings F1-F4), RULINGS_INC_R0, DEFECT_LEDGER_INCIDENT, the brief I1-1..I1-11 and the S95 reports D1 (F4), D2 (a, f), R2 (b), ADV (R-1, R-2, C-1).
- Base: `731bcddf531a7e123963246168ca19f262859337` = worktree HEAD; `git status --short` empty before and after (this file sits under `.qa-s80/`, ignored).
- READ-ONLY round (H5 c, R0-9): NO pytest, jest, tsc or eslint ran. Every file:line below was re-read at the base with `git -C <worktree> show 731bcddf:<path>` / `git grep`. Every run is DEFERRED TO RED (section 9).
- THE MODEL PROBE. To settle the spec's BY READING truth table, I wrote a stdlib-only re-implementation of spec section 2.2 (the word sets, `identity`, `check`, `first_https_raster`, exactly as the spec words them; `price_service._BRAND_ALIAS_GROUPS` and `_jsonld_image_urls` copied verbatim from ps:5177-5199 and ps:10995-11027; `category_gate`, `jsonld_widen`, `deny_hosts`, `robots_eval` and the two empty `__init__.py` exported from the base into `<SP>/INC-IH/scratch`, run with the venv's CPython 3.12.9 and `-I`). It is a model of the SPEC, not GREEN code: its results say what the spec's own rules decide. The probe scripts and outputs are kept in `<SP>/INC-IH/probes/` (hashes in section 10); the exported repo copies were deleted afterwards, file by file.
- Production flag state used (names only): the common brief H12 (c) (the relay's dated lines of 2026-11-14) plus the record-copy ledger lines 316 and 336 (2026-11-07): `ENABLE_DATA_GUARDS_V2` and `ENABLE_IMAGE_PIPELINE_V2` OFF on web, `ENABLE_FRAGRANCE_ONLY_GATE` believed OFF, `ENABLE_PAGE_SCRAPE` ON, `ENABLE_ANTHROPIC_TEXT` / `ENABLE_OPENAI_EGRESS_STOP` ON. The task text names the docs checkout's ledger; H4, H8 (c) and H12 (e) forbid touching sc-docs-70, so the record copy and H12 (c) were used, as the spec did.

---------------------------------------------------------------------------------------------------

## Verdict: BLOCK

Two blocking issues stop the RED, both resolvable by orchestrator rulings plus small spec edits (no new spec round is needed if the rulings carry the corrections):

- B-1: in the PRODUCTION flag mix (`ENABLE_DATA_GUARDS_V2` OFF) the guard ACCEPTS Fragrantica-sourced pictures (measured on the model, X5), and the new `"<name> perfume"` query steers Serper Images toward exactly those pages. House rule H12 (g), the PLAN_S81 standing constraint and the binding VERIFY "Images" correction all forbid it.
- B-2: the literal I1-3 default, frozen as A-R03 T20, removes every cascade picture of every non-fragrance text compare while the fragrance-only gate is OFF (every app compare has brand "").

What holds (measured): every base-state file:line I re-read (section 1); the truth table T1-T20 (0 mismatches on the model, T10 reversed included); the noon image's survival to the override (section 1, the noon row); the flag-OFF design and its call-shape pins; the comm set (710 files). Beyond the two blockers, the model accepts wrong-bottle pictures for the spec's own golden product and proof product with an empty brand (X1, X2), and the phone proof as written cannot see them (C-3).

---------------------------------------------------------------------------------------------------

## 1. Re-measured at the base (each holds unless section 2 refutes it)

| Area | Re-read at 731bcddf | Result |
|---|---|---|
| img (344 lines) | :33-48, :57-67 (http accepted; the deny runs only under DG, :65), :82, :85-129 (reads no title, source or link), :136-153, :156-217 (organic[:10], `- {link}: {snippet}`, router site image_tier3 at :189), :220-225, :232-239, :255-257, :259-262, :264-268, :274-281, :286-289 (one credit, :288), :290-314 (:295 `search_images(name, num_results=1)`, :306-311 images[0]), :317-333, :336-337, :338-344 (CancelledError arm, bare raise, no finally) | holds |
| callers | `get_product_image_url`: one caller scs:6261 (import scs:1591); `extract_image_via_gpt` also at scripts/meas_claude_gate.py:1685, :1687; `search_images` only at img:295 | holds |
| scs (9,979) | :86, :1432, :1591, :1596, :1601, :1374-1390, :1959-1971, :4422-4437 (`"_vision": True` at :4435 and :5137), :4438-4453, the only `_fetch_product_data` calls :4565-4566 / :5269-5270, :5953-5980 (`partial_slot` :5955; brand / name / category / is_vision :5966-5974), :6017-6034 (image 5.0 s :6033), :6128-6165 (unified search only when specs or reviews miss the cache), :6260-6273, :6301-6319 (race timeout or exception -> `_price_fallback_on_miss` -> None for the image, :6984+), :6396-6429 (V2 -> allowed_image_url; elif DG -> _is_valid_image_url; else any http(s)), :4610 / :5364 fairness, :7474-7499 (noon :7486), :7100 the size- and category-aware price key, :9357-9382 | holds |
| noon survival (Q4 precondition) | the consume appends the raw adapter dict (scs:7769-7771), `select_best` returns the candidate object itself (ps:8627+, `return eligible[0]`), the BH direct hit caches it whole and returns it (scs:7833-7885), `_get_price` returns it unchanged (scs:8296-8298), the price task (scs:6070, gathered at :6231-6232) writes it to `result["price"]` (scs:6319), `public_price_view` keeps `image_url` (ps:9439-9442) | a noon `image_url` reaches the override and the response |
| noon (541) | :73-93, :105, :123 (`_MAX_PDP_CONFIRMS = 2`), seams :139 / :152 / :158, :288-309, :327-333, :397-467 (the Product `image` is never read), :474-541 (never raises; showable and content safety after the confirm) | holds |
| ps | :51, :204-220 (7 d genuine TTL), :223-235 (L2 admits a genuine row for the same window), :594-601 (26 hosts, no noon / nooncdn), :3856-3868, :4370-4374, :5177-5199 (13 groups; comments :5171-5176 and :5186-5191), :6909-6959 (RS2), :9426-9442, :10995-11027 | holds (but see R-4) |
| jw | :56-61, :74, :79, :88, :129-142 (public host), :156-164, :170-193 (the deny at :189 is flag-free), :310-319 (D08 stamp under V2) | holds |
| cg | :40-44, :111-124, :140-141, :172-199 | holds |
| deny_hosts | :32-39 (the flag is read at each consumer site), :114-116, `is_denied_url` :168-195, `is_denied_source` :198-209 | holds |
| others | kb_serve.py:321-326 (https + validator + `kb_source_allowed`), ab:30-40 / :1236-1239 / :1248-1295, ss:1267-1309, rb:1951 / :1972 / :2232-2236 / :2264, product_data_service.py:340-359 (no image column), zyte_service.py:499 / :661, extraction_service.py:1183-1190 / :1236-1264 / :1326-1360 (bare names -> other), source_router.py:1026-1030 (noon serves electronics / fragrances / fashion / other), spec_spine_service.py:190-200 | holds |
| client | both live bundles send ONE REST GET /api/v1/text/compare with product_a / product_b (`ENABLE_EXPO_FETCH_SSE_DEFAULT = false`, features.ts:52 at 683f56c0 and f1e20c39; api.ts:703 at 683f56c0, :742 at 731bcddf); no read of `price.image_url` and no enumeration of price keys in SmartCompareApp/src at 683f56c0, f1e20c39 or 731bcddf (git grep: 0 hits); ProductImage.tsx:10-16, :59-62, :99-103; NSAppTransportSecurity 0 hits at both shas | holds |
| tests | x2a:32-36 and R2-7 :221-246 (walks ONLY the CancelledError handlers: a `finally` cannot trip it), P2-2 :262-272; test_image_service_longtail.py:29, :256; test_image_service.py:73, :153; test_image_knowledge_graph_tier.py:42, :48, :58-61; test_comparison_response_image_url.py:89-135, :321-324; test_s81_s18_kb_first_serve.py:404-406 (positional recorder) + the golden `"get_product_image_url": 2` (3 cases); test_legal_docs_u8.py:826-864 (T7b); test_s81_d03_deny_and_guards.py:587-611 (r1i), :1312-1325 (p8); test_s81_kb_schema.py:331-424 (P01 / P02 cover kb_service importers and kb_* literals only); tests/_hermeticity.py:85-93 (a module first imported during a test is not a leak); test_ci_gates.py:290-349, :765-790; test_noon_adapter.py (804 lines, no exact-dict or key-set pin) | holds |
| fixtures | the noon probe re-run independently: noon_pdp_iphone_bhd.html and noon_pdp_meta_quest_3s.html carry a Product `image` LIST of 10 `https://f.nooncdn.com/p/pzsku/.../*.jpg?width=1200` strings; sale_price/ae_noon_com_strikethrough.html has a Product with no image; platform/ae_noon_com.html has no Product node; eval_regression T01 shapes (b) and (c) | holds |
| comm set | comm_set.txt sha256 `5e2f0266...` equal, 710 lines; closure 84 with app/main.py; 783 test files at the base, 73 outside: none imports or names the closure; the directory walkers outside are the four excluded pre-commit files and test_be_harness.py (walks tmp_path only, :1263); every `.github` reader is inside except test_precommit_hook.py (excluded; its allowlist is a tmp repo's, :241) | holds |
| CLAUDE.md | 1,146 lines; image paragraph :312-313; Feature Flags line :341; S81-07c block :675-682; `## Tests` :684 | holds |
| lexicon | concentrations 14, forms 22, houses 75, notes 39 | holds |

### 1b. What the spec's rules decide (measured on the model)

| Row | Identity (brand / line / category) | Picture text ; host | Spec rules give | Precision-first wants |
|---|---|---|---|---|
| T1-T20, T10 reversed | the spec's table | the spec's table | the spec's expected value for all 21 (0 mismatches) | - |
| X1 | "" / "Bleu de Chanel EDP" / fragrances (a golden product, INC-R1 OFF) | "Chanel No 5 Eau de Parfum" | ACCEPTED | reject |
| X2 | "" / "stronger with you" (the proof product) | "Emporio Armani Because It's You Eau de Parfum" | ACCEPTED | reject |
| X3 | "" / "Dior Sauvage" | "Dior Homme Eau de Toilette" | ACCEPTED (L-I1-2) | reject |
| X4 | "" / "Aventus 100 ml" | "Creed Viking Eau de Parfum 100 ml" | ACCEPTED | reject |
| X5 | "" / "Tygar" | "Tygar Bvlgari cologne - a fragrance for men 2016", "Fragrantica" ; a fragrantica.com perfume page | ACCEPTED | reject |
| X6 | "Carolina Herrera" / "Good Girl" | "Good Girl Gone Bad Eau de Parfum" ; https://www.manor.ch/x | ACCEPTED ("ch" from the TLD) | reject |
| X7 | "Paris Hilton" / "Heiress" | "Lancome Heiress Eau de Parfum" | ACCEPTED (group {lancome, paris}) | reject |
| X8 | "Christian Louboutin" / "Loubirouge" | "Dior Loubirouge Eau de Parfum" | ACCEPTED (group {dior, christian}) | reject |
| X9 | "" / "Stronger With You" | "A perfume with vanilla notes" | name | name |
| X10 | "Maison Margiela" / "Replica Jazz Club" | "Maison Francis Kurkdjian Baccarat Rouge 540" | brand | brand |
| X11 | "" / "Aventus 100ml" | "Bleu de Chanel 100ml EDP" | name | name |
| X12 | "" / "Sauvage EDP" | "Sauvage" (a KG title of the real product) | fragrance_word (L-I1-1) | accept (Q-5) |

Mutants measured on the model (each changes NONE of the 21 truth-table rows): STOP_WORDS emptied (X9 flips to accepted), BRAND_NOISE emptied (X10 flips brand -> name), the SIZE_TOKEN exclusion removed (X11 flips to accepted).

Corrections measured on the model (each changes NONE of the 21 truth-table rows; the true titles of Bleu de Chanel EDP, stronger with you, Sauvage EDP, Aventus, Layton and "Aventus 100 ml" stay ACCEPTED with all of them on): every significant line token required when the brand is empty (rejects X1-X4); host tokens limited to the registrable label (rejects X6); alias groups expanded only when the brand's tokens are a subset of the group (rejects X7, X8); a number followed by a unit token dropped from the line (rejects X4); the deny list inside the guard (rejects X5, reason `denied`). first_https_raster on the model: the noon list, the http-then-https list, the ImageObject list and the contentUrl dict give a URL; svg, an IP host, a fimgs.net jpg, None, 42, {} and an `*.example.test` host give None. `allowed_image_url(N1, <noon PDP url>, OFFICIAL_BRAND_DOMAINS)` = None (the V2 branch refuses the noon CDN).

---------------------------------------------------------------------------------------------------

## 2. Refuted claims (measured truth, file:line)

- R-1 (2.11 "every mix the rollout can produce"). The walk omits the production mix `ENABLE_DATA_GUARDS_V2` OFF for the deny list. With DG OFF the cascade's only deny check (img:65, behind `data_guards_v2_enabled()`) does not run, so a fimgs.net image is base-valid, and the guard then ACCEPTS a Fragrantica item (X5: its page title always carries the line, the house and "perfume" / "cologne" / "fragrance"). The row "I1 ON, ENABLE_DATA_GUARDS_V2 ON" walks the NON-production mix. -> B-1.
- R-2 (5.3 row B-P05, "kills M24 / M25 at head"). False for M24: B-P05 runs with the flag "true", and M24 (the noon block without its flag check) behaves identically under it. Only B-P01 kills M24 (section 6 lists B-P01 alone). B-P05 kills M25 / M26.
- R-3 (1.8 "Both live bundles (683f56c0 store, f1e20c39 OTA) read image_url only on products (ResultsContent.tsx:339, imagePrefetch.ts:36, HistoryScreen.tsx:487-491, types.ts:103)"). Those are the f1e20c39 / 731bcddf lines. At 683f56c0 the reads are ResultsContent.tsx:285, HistoryScreen.tsx:489-493, types.ts:101, and src/services/imagePrefetch.ts does not exist there (`git cat-file -e`: absent; it arrived with CL2). The conclusion (no `price.image_url` read) holds at both shas.
- R-4 (1.6 / 2.2: the alias data reused "with the RS2 idiom" = I1-3's "brand alias folding the repository already has"). The repository's groups are documented as triggered "ONLY when the brand IS that house" (ps:5175-5176, :5190-5191), and the RS2 fence expands only the query's padding-brand tokens (ps:6935-6946). The leaf expands every group that touches ANY brand token, so a multi-word brand inherits a foreign house: X7 (Paris Hilton gains lancome), X8 (Christian Louboutin gains dior); by the same rule Tom Tailor gains ford / tf, Jean Patou gains gaultier / jpg, Marc-Antoine Barrois gains jacobs / mj.
- R-5 (2.2 check: "Host tokens serve the BRAND test only ... precision first"). The host tokens are every label of the hostname, the TLD included: `www.manor.ch` gives {manor, ch}, and "ch" is a member of the Carolina Herrera group (ps:5182). X6: any .ch-hosted picture passes the Carolina Herrera brand test.
- R-6 (L-I1-2 as the whole cost of an empty brand). L-I1-2 names only "Dior Sauvage <- Dior Homme EDT" (X3). With an empty brand the typed house is a LINE token (brand forms are empty, scs:4449-4452), so the spec's own golden product "Bleu de Chanel EDP" accepts a Chanel No 5 picture (X1; T8 protects only a KNOWN brand, which no app compare has in the first window) and the proof product "stronger with you" accepts "Because It's You" (X2; "you" is no stop word). The phone proof as written ("both photos", 8b check 2) passes on a wrong bottle.
- R-7 (2.2 SIZE_TOKEN as the size guard). `cg.normalize` splits "100 ml" into "100" and "ml" (cg:193-199); SIZE_TOKEN matches only the attached form, so "100" stays a line token: X4.
- R-8 (6 "Expected: 27 KILLED, no equivalent mutant", read as the complete killer map). Three plausible mutants change none of the 21 truth-table rows (measured): STOP_WORDS emptied, BRAND_NOISE emptied (T16's "parfums" is also a concentration word), the SIZE_TOKEN exclusion removed. By reading, also unkilled: (a) scs passing brand "" (B-R03 drives only brand ""; the q= path, the warmer and INC-R1 ON reach the image task with a brand); (b) `_first_image` without its https preference (no row has an http and an https key on one item); (c) the snake_case `knowledge_graph` key dropped under the guard; (d) the images-block `hosts=(link, domain)` ignored; (e) the "first related item's reason" branch of `accept_pick` (no row has a related item that fails).
- R-9 (2.8 F4 "byte-identical functions (A-P03, A-P04)"). The two PINs evaluate one input each and cannot show byte identity; the diff and the existing suites (tests/test_image_knowledge_graph_tier.py:40-143, tests/test_image_service*.py) carry F4.
- R-10 (header: "D1 F4 (merged here per ADV C-1)"). D1 F4 (D1 report line 95) also asks for the category word in the SHOPPING and UNIFIED queries; this unit changes only the image query, and section 10 does not list the rest. The defect ledger must not mark D1 F4 addressed by INC-I1.

---------------------------------------------------------------------------------------------------

## 3. Blocking issues

### B-1 The deny list is missing from the guard in the production flag mix

Binding: H12 (g) ("Never Fragrantica, Parfumo or Basenotes data in any form"), PLAN_S81 Standing constraints ("no Fragrantica/Parfumo"), the VERIFY "Images" correction ("deny fimgs.net, fragrantica, parfumo"; binding on every unit). With `ENABLE_DATA_GUARDS_V2` OFF on web the cascade has no deny check at all (img:65). Under the guard the relevance test PREFERS a Fragrantica item (X5), and the new " perfume" suffix (2.2 item 6) moves Serper Images toward exactly those pages (an inference: the result mix is not measurable in this round). Fable ruling F1 put the router / rating / ingest deny behind a flag; the image-policy precedents show a NEW image flag carries the deny itself (jw:189 inside `allowed_image_url` under V2; kb_serve.py:323-324 `kb_source_allowed` under KB_FIRST_SERVE).

Fix (one of, by ruling):
- (a) Under the guard a candidate is rejected when `deny_hosts.is_denied_url(url)`, or its `link` / `domain` host is denied, or `deny_hosts.is_denied_source(source)` (or its title) is true; a denied organic item never satisfies the Tier-3 precondition or the related-host test. Flag-free match functions only, never a host literal (D03 r1i, tests/test_s81_d03_deny_and_guards.py:587-611). A-R06's module-level import allowlist gains `app.services.deny_hosts` (or the leaf reaches it as `_jw.deny_hosts`). A closed reason word (`denied`) extends the I1-8 grammar and the A-R14 regex. New rows: the X5 shape, a fimgs.net `imageUrl` under a passing title, a Tier-3 pick on a fragrantica host; a mutant "deny removed" killed by them. Measured on the model: (a) changes none of T1-T20 and rejects X5.
- (b) `ENABLE_DATA_GUARDS_V2` ON on web becomes a recorded precondition of the INC-I1 flip, in its own window (D03 changes far more than pictures, so (a) is the smaller step).

### B-2 The literal I1-3 default blanks every non-fragrance picture

Every app compare has brand "" (scs:4449-4452); `ENABLE_FRAGRANCE_ONLY_GATE` is believed OFF (H12 c), so non-fragrance compares run, and noon and the cascade serve electronics / fashion / other (source_router.py:1026-1030). Under the literal rule a brand-empty product needs a fragrance word in its picture's text, so an iPhone or a handbag never gets a cascade picture again (T20 = fragrance_word, measured). The spec freezes that in A-R03 T20 while asking OQ-1. The RED must not freeze T20 before the ruling.

Recommended ruling: OQ-1 as the spec proposes. The fragrance word stays required for the canonical categories fragrances AND other: a bare "Tyger" with no chip on a below-3 account resolves to other (extraction_service.py:1326-1360, scs:477-541; the classifier fails locally under the egress stop) and must still refuse the poem. T20 -> None; one clause of `check`; add a row "" / "Tyger" / other / "The Tyger by William Blake" -> fragrance_word. Alternative: record `ENABLE_FRAGRANCE_ONLY_GATE` ON as a flip precondition.

---------------------------------------------------------------------------------------------------

## 4. Corrections (not blocking; each by a ruling or a spec edit before RED)

- C-1 (major) Precision fixes, each measured on the model (section 1b): (a) host tokens = the registrable label(s) only (drop the public-suffix labels and `www`), fixing X6; (b) an alias group is expanded only when the brand's kept tokens are a subset of it, fixing X7 / X8 and keeping T3, T5, T6, T10, T19; (c) a number immediately followed by a unit token (ml, oz, fl, g, gm) is not a line token, fixing X4; (d) Q-3 (every significant token when the brand is empty), fixing X1-X4. Each lands with its truth-table row so its mutant is killable.
- C-2 (major) Complete the mutation table: add X9 (kills STOP_WORDS emptied), X10 (kills BRAND_NOISE emptied: the reason flips brand -> name), X11 (kills the SIZE_TOKEN removal); extend B-R03 with a q=-shaped product with a brand (`{"brand": "Dior", "name": "Sauvage", "variant": "EDP", "category": "fragrances", "search_query": "Dior Sauvage EDP"}`: positional `("Dior Sauvage EDP",)`, relevance `{"brand": "Dior", "line": "Sauvage", "category": "fragrances", "slot": ...}`); one A-R12 variant whose KG item carries an http `imageUrl` and an https `image` (the https one is taken), one with the `knowledge_graph` key, one images-block item that passes by its `domain` only, one Tier-3 case with a related but failing organic item (its reason is logged). List them as M28-M33 with their killers.
- C-3 (major) PROOF ON THE PHONE (8b):
  - (a) Check 2 must read "each card shows the named product's own bottle (the owner reads it)", not "both photos" (X1 accepts a Chanel No 5 bottle for Bleu de Chanel). The backing records per product the `[IMG_RELEVANCE] tier=` value: with an empty brand a KG card titled with the line alone is rejected (X12), so a golden photo that came from the free tier now comes from the paid Tier 1 inside the 5 s race; also any `[L2.6] Phase 1 race timeout for image_url` line.
  - (b) Check 1's noon half needs a FRESH noon fetch. The 2026-11-13 noon price of "stronger with you" is genuine (page_scrape_jsonld): L1 keeps it 7 days (ps:204-220) and L2 admits a genuine row for the same window without any image column (ps:223-235; product_data_service.py:340-359), so, if that hit was cached (ADV claim 15: the write is gated by `should_cache_price`, scs:7874-7877), for the same pair and category the card shows the cascade picture or the placeholder until about 2026-11-20 21:19 UTC (BY READING). State the earliest date or add a second, never-compared noon-won pair; the relay reads the `[PRICE] BH adapter direct hit ... via noon.com` line before reading the noon half.
  - (c) Record the pair's resolved category and the account's consent version: the " perfume" suffix applies only to the category fragrances; with no chip and a below-3 account the classifier fails locally and the pair resolves to other (scs:477-541; extraction_service.py:1387-1420), so the query stays bare.
- C-4 (minor) B-P01 must use N1 (the image B-R01 proves the ON path copies). An image on a non-public host (an `*.example.test` name) is refused by allowed_image_url's public-host rule (jw:129-142; measured), which would leave B-P01 vacuous for M24 (ruling B1).
- C-5 (minor) Knob: the brief says "clamped 1..10"; the spec maps 0 and negatives to 5 (L-I1-17). For a spend knob an operator's 0 then buys five results instead of one; recommend clamping finite values below 1 to 1 (A-R02: "0" -> 1, "-3" -> 1), unless the ruling keeps the house idiom on purpose.
- C-6 (minor) Owner steps: the price-warmer runs the same cascade and noon adapter (scripts/cron_warm_price_cache.py:225); if `ENABLE_PRICE_CACHE_WARMER` is ever set true while the guard is unset there, its 7-day noon cache writes carry no `image_url` for web. The CLAUDE.md row should say the flag joins price-warmer in that window.
- C-7 (minor) Canary watch items in the PR body and the row: the `[BUDGET] serper_images daily budget exhausted` count (more products reach Tier 1, X12), the `[IMG_TIER] serper_images` ms and the image race timeouts, the `[IMG_RELEVANCE] reason=` mix.
- C-8 (minor) RED file A imports `app.services.price_service` at module top (it exists at base), so the leaf's function-local import is a sys.modules hit in every order; a `-k` mutant run of file A alone would otherwise import the 17,332-line module for the first time inside a timed row (A-R15 included).
- C-9 (minor) `organic_passes` / `accept_pick` walk organic[:20] while `extract_image_via_gpt` shows the model organic[:10] (img:173): a passing item at 11-20 buys an LLM call the model cannot use. Use 10 for the Tier-3 list (20 stays for Tier 1.5b), or state it.
- C-10 (minor) A Tier-3 pick equal to an organic `link` (the product PAGE, same host) passes `accept_pick` and is logged `accepted` while ProductImage shows the placeholder (onError). Reject a pick equal to an organic link, or require a raster path on Tier-3 picks only (the Tier-3 prompt already asks for .jpg / .jpeg / .png / .webp, img:151; RULE 7 "https raster"). KG and Serper candidates keep no raster test (thumbnail hosts carry no extension).
- C-11 (minor) Section 10 lists D1 F4's shopping / unified category word as out of scope (R-10).
- C-12 (minor) The citation and row-text fixes of R-2, R-3 and R-9.

---------------------------------------------------------------------------------------------------

## 5. Contract risks (for the classification, I1-10 / OQ-11)

- CR-1 `price.image_url` gains a value for a noon-won price under the flag, on overview.products[i].price and the legacy products[i].price (ps:9439-9442; rb:1951, :2264), the SSE prices event, the saved full_response, the admin-gated /text/prices endpoint and the L1 price cache. Additive and unread by both live bundles (0 reads at 683f56c0 and f1e20c39; no price-key enumeration). It is an existing member by schema, but no production response has carried it since S81-23 retired the Zyte seeds while V2 stays OFF: in traffic it is new.
- CR-2 PLAN_S80 section 0 point 4 / RULE 7 ("an absolute https raster URL or null"): under the flag the cascade still emits non-raster https URLs (L-I1-5; C-10 for Tier 3). http is closed for text compares (noon https-only, cascade https-only, KB https-only); the camera path is unchanged (L-I1-14).
- CR-3 Build-3-visible change: more placeholder tiles (B-2 for non-fragrance products; X12 for brand-empty KG cards when Tier 1 loses the 5 s race). Null is inside the contract; this is a visible regression risk on a live app, not a contract break.
- CR-4 Rollback is not byte-identical for up to 7 days: noon prices cached while ON keep `image_url` (L-I1-10). The owner-step (3) line should repeat it.
- CR-5 Hotlinking: the noon CDN pictures are shown by URL. Retailer image hotlinking is an open counsel item (PLAN_S81 owner actions item 4); no new class of behaviour (the cascade already hotlinks).
- CR-6 The binding VERIFY "Images" correction says the live path serves only the KB image or the retailer JSON-LD image; this unit keeps the Serper tiers live (OQ-10). The orchestrator records it as a ruled interim deviation, the end state unchanged.

---------------------------------------------------------------------------------------------------

## 6. Pin collisions

None beyond section 4.1 (NONE). Checked: the T23 OpenAPI fixture (no route or parameter change); the FY25 digests (tests/test_s75_fanout_identity.py: the flag is a new, unset name; the call shape is unchanged with it OFF); the w4_11 prompt digests and test_prompt_fence (the Tier-3 prompt, router site and organic list are unchanged); the test_retro_w2_1 URL pins (no URL route); the W4-13 ledger fixture (tests/test_w4_13_flag_off_ledger.py names no edited module; no search_logs change); the copy-policy fences (no client file); X2a R2-7 (walks only the CancelledError handlers, x2a:221-246); the S81-18 golden (positional recorder, :404-406); hermeticity (tests/_hermeticity.py:85-93); the black allowlist (test_ci_gates.py:290-349: the three new paths must exist and be black-clean); T7b and D03 r1i (no host literal). Two collisions the corrections would create, to pre-empt in the same ruling: A-R06's import allowlist (if `deny_hosts` is imported, B-1 a) and the A-R14 / I1-8 reason regex (if `denied` is added).

---------------------------------------------------------------------------------------------------

## 7. The session-79 defect classes, each checked

- Vacuous PIN rows: B-P01 needs N1 (C-4). A-R16, A-P02, B-P02, B-P03 run with the full configuration and recorders and kill M02, M05, M03, M04 (by reading). No config check precedes every observable action.
- Mutants no RED row can kill: R-8 (eight; three measured).
- Comm-set files missing: none (section 1); at head add the two RED files.
- Flag-OFF byte identity: pinned on the call shapes (A-R16, A-P01, B-P02, B-P01, B-R01's dict equality). No response golden, acceptable for this footprint.
- A response key removed, renamed or retyped: none (CR-1 is additive).
- A refusal through a shape build 3 cannot render: none (no refusal, code or status).
- Billing (R-A3): no abstain. The daily image credit and the lifetime count stay per call, but more calls reach Tier 1 (L-I1-4, X12): a cost item (C-7), not a user-billing item.
- Pin collisions: section 6.
- The camera failure envelope: camera products always carry `"_vision": True` (scs:4435, :5137) and get `{}` (B-P03); no interaction.
- Cache keys without a category or language axis: no new key; the noon picture rides the size- and category-aware price key (scs:7100).
- The error-handler mapping (a codeless 503 -> FEATURE_DISABLED): the unit raises nothing; an exception in a new helper surfaces as `Error fetching image_url: <Type>` (scs:6316) and None.
- A stated limit that is actually a defect: L-I1-3 (B-2); L-I1-2 understated (R-6); L-I1-17 (C-5).

---------------------------------------------------------------------------------------------------

## 8. Questions for the orchestrator (recommended answer first)

- Q-1 B-1: option (a) (the deny inside the guard, the reason word `denied`, A-R06 widened) or (b) (`ENABLE_DATA_GUARDS_V2` ON as a flip precondition)? Recommended (a).
- Q-2 B-2: rule OQ-1 before RED? Recommended yes: the fragrance word for fragrances and other only; T20 -> None.
- Q-3 Brand empty (every app compare until INC-R1): keep I1-3's "at least one significant line token" (X1-X4 accepted) or require EVERY significant line token when the brand is empty? Recommended every token (measured on the model: T1-T20 unchanged; X1-X4 rejected; the golden and proof products' true titles accepted). Alternative: split a typed house out of the line through the lexicon's 75 houses (phrase match).
- Q-4 C-1 (a)-(c): registrable-label host tokens, the subset rule for alias groups, the number-plus-unit drop, each with its row? Recommended yes.
- Q-5 OQ-3: may the knowledge graph's `type` text satisfy the FRAGRANCE-WORD test only (never the brand or line test)? Every brand-empty KG card titled with the line alone is rejected (X12), which moves golden photos to the paid tier inside the 5 s race. NOT MEASURED whether Serper's KG carries a perfume type (the T01 shape shows the field exists: type "Musical instrument"). Recommended yes, with a row "" / "Sauvage EDP" / KG {title "Sauvage", type "Perfume"} -> accepted and {title "The Tyger", type "Poem"} -> fragrance_word.
- Q-6 OQ-10 / CR-6: record the interim deviation from the binding VERIFY "Images" correction? Recommended yes.
- Q-7 C-5: knob values below 1 -> 1 (the brief) or -> 5 (the house idiom)? Recommended 1.
- Q-8 C-3 (b): the earliest proof date for check 1's noon half, or a second never-compared noon-won pair? Recommended both.
- Q-9 Classification: SAFE (I1-10) only with B-1 fixed, since the deny list is a licensing guard (D03) and an unfixed B-1 makes the flip a licensing-surface change? Recommended SAFE with B-1 (a).
- Q-10 C-10: reject a Tier-3 pick equal to an organic link, or require a raster path on Tier-3 picks? Recommended the raster path on Tier-3 picks.
- Q-11 STOP_WORDS: add the pronoun and audience words that never identify a line (you, your, my, me, it, its, his, her, him, men, man, women, woman, homme, femme, uomo, donna)? Moot if Q-3 is ruled "every token"; otherwise recommended.

---------------------------------------------------------------------------------------------------

## 9. DEFERRED TO RED (exact commands, from the spec; nothing ran in this round)

```
PYTHONIOENCODING=utf-8 C:/Users/SynAckITPC/Documents/AI/.venv-qaren/Scripts/python.exe C:/Users/SYNACK~1/AppData/Local/Temp/claude/cde30765822f13ce/fce5ef8e-45c1-47d7-9da1-42b27fb2581e/scratchpad/harness/gate.py --bound 600 --tag inc-i1-base-img --log C:/Users/SYNACK~1/AppData/Local/Temp/claude/cde30765822f13ce/fce5ef8e-45c1-47d7-9da1-42b27fb2581e/scratchpad/INC-I1/red/base_img.log --cwd C:/Users/SynAckITPC/Documents/AI/sc-inc-i1 -- tests/test_image_service.py tests/test_image_service_edges.py tests/test_image_service_longtail.py tests/test_image_knowledge_graph_tier.py tests/test_inc_x2a_image_tier_timing.py tests/test_inc_g1_gate_rows.py tests/test_comparison_response_image_url.py

PYTHONIOENCODING=utf-8 C:/Users/SynAckITPC/Documents/AI/.venv-qaren/Scripts/python.exe C:/Users/SYNACK~1/AppData/Local/Temp/claude/cde30765822f13ce/fce5ef8e-45c1-47d7-9da1-42b27fb2581e/scratchpad/harness/gate.py --bound 1200 --tag inc-i1-base-pins --log C:/Users/SYNACK~1/AppData/Local/Temp/claude/cde30765822f13ce/fce5ef8e-45c1-47d7-9da1-42b27fb2581e/scratchpad/INC-I1/red/base_pins.log --cwd C:/Users/SynAckITPC/Documents/AI/sc-inc-i1 -- tests/test_noon_adapter.py tests/test_s81_d08_jsonld_widen.py tests/test_s81_d03_deny_and_guards.py tests/test_s81_s07c_role_fix.py tests/test_s81_s06_anthropic_router.py tests/test_model_config_enforced.py tests/test_prompt_fence.py tests/test_s81_s18_kb_first_serve.py

PYTHONIOENCODING=utf-8 C:/Users/SynAckITPC/Documents/AI/.venv-qaren/Scripts/python.exe C:/Users/SYNACK~1/AppData/Local/Temp/claude/cde30765822f13ce/fce5ef8e-45c1-47d7-9da1-42b27fb2581e/scratchpad/harness/gate.py --bound 1200 --tag inc-i1-base-scan --log C:/Users/SYNACK~1/AppData/Local/Temp/claude/cde30765822f13ce/fce5ef8e-45c1-47d7-9da1-42b27fb2581e/scratchpad/INC-I1/red/base_scan.log --cwd C:/Users/SynAckITPC/Documents/AI/sc-inc-i1 -- tests/test_legal_docs_u8.py tests/test_ci_gates.py tests/test_s81_s22b_self_critique_retire.py tests/test_s81_s12d_openai_egress_stop.py tests/test_sentry_channels_u8d_unit.py tests/test_openai_key_log_hygiene_s69.py tests/test_serper_budget_gate.py

PYTHONIOENCODING=utf-8 C:/Users/SynAckITPC/Documents/AI/.venv-qaren/Scripts/python.exe C:/Users/SYNACK~1/AppData/Local/Temp/claude/cde30765822f13ce/fce5ef8e-45c1-47d7-9da1-42b27fb2581e/scratchpad/harness/gate.py --bound 600 --tag inc-i1-red-base --log C:/Users/SYNACK~1/AppData/Local/Temp/claude/cde30765822f13ce/fce5ef8e-45c1-47d7-9da1-42b27fb2581e/scratchpad/INC-I1/red/red_base.log --cwd C:/Users/SynAckITPC/Documents/AI/sc-inc-i1 -- tests/test_inc_i1_picture_must_match.py tests/test_inc_i1_noon_and_wiring.py
```

Also deferred: the comm-set base record (710 files, 29 chunks of at most 25, tags `inc-i1-comm-base-NN`), the CI-order set (`inc-i1-ciorder`), the fourteen client fences by path, the mutation run (M01-M27 plus the M28-M33 of C-2 and the deny / precision mutants of B-1 and C-1). If B-1 (a) and C-1 land, `tests/test_s81_d03_deny_and_guards.py` stays in the base-pins run (it already is) because the leaf then calls deny_hosts.

---------------------------------------------------------------------------------------------------

## 10. Not done in this review

- No pytest, jest, tsc or eslint (READ-ONLY round). The section 1b results come from a model of the spec, not from GREEN code; the RED rows decide.
- NOT MEASURED (no network): the Serper Images item fields `source` / `link` / `domain`; whether Serper's knowledge graph carries a perfume `type`; the share of Fragrantica pages in `"<name> perfume"` image results; Serper billing for `num` 5; the KG titles of the golden pairs.
- Probe files (kept, `<SP>/INC-IH/probes/`): see the sha256 lines appended below. The exported base copies (`app/__init__.py`, `app/services/__init__.py`, `category_gate.py` 8bfa2617..., `jsonld_widen.py` 28f6b9ce..., `deny_hosts.py` 9ac5f2ad..., `robots_eval.py` bb584acb...) were deleted after the probe, file by file (no recursive delete). To re-run: export those six files at 731bcddf into `<SP>/INC-IH/scratch/app/...`, copy `leaf_probe.py` into `scratch/app/services/`, then `python -I run_probe.py <scratch>` and `python -I run_variants.py <scratch>` from the scratch folder.

Probe sha256 (file name: digest):

```
69ce05897790d8ee45deac1f54b94e53a0cc08ea1e7b0c346c205505c98b99d5  leaf_probe.py
e41d00a00e7ffd22a8025553496c30bf91f0642cf919fe258a68dfbf0f5bfca1  run_probe.py
e6d82ed5610702e0771eb662cae24911dba724f5fa762927d34d8ab89437e04e  run_variants.py
37ba5eacc3434712faf1d7d8ae3687ddec321ddb3d55210c54d11d3c32d9f322  probe_out.txt
ebd3333cef4540807f411aee405efd1907fb093833b886688739137aefa6922a  variants_out.txt
02ef225bb12d97a358f8d43d0b3a172d7d430f60f3047b574f79df0b5a7e18ee  ld_probe.py
```
