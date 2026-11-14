# INC-H1 NO-CONFIDENT-EMPTY - UNIT SPEC (server only; read-only spec round)

- Unit: INC-H1 NO-CONFIDENT-EMPTY. Closes: S95-FIX diagnosis 2026-11-14 D2 RC4 (11 "N/A" fields -> 11 dash rows), RC5 (N/A fields counted as fact-check citations -> Specs High), RC6 (the Versatility bar and the "leads on Versatility" line from the citation-reliability of N/A rows), RC7 (the model's no-data sentence shipped as review praise) and the caching part of F6; ADV R-4 (the three cases behind the dash rows are told apart by the new log line), R-5 and C-2 (the server owns the Specs chip: the D2 F4 cure, the D3 F-PRICEPILL specs half is not built), C-3 (the server half of the spec pair; the client empty line is INC-C1's, H1-3 / H1-10). The owner's comparison of 2026-11-13 21:19 UTC (eleven dash rows headed "11 dimensions", Specs High, the Versatility bar and headline, the no-data review sentence).
- Flag ruling (H1-2): ONE new DARK flag `ENABLE_HONEST_EMPTY` (git grep at the base: 0 hits for ENABLE_HONEST_EMPTY, honest_empty and has_review_data in the whole tree). Default OFF, read PER CALL with the house idiom `os.getenv(NAME, "false").strip().lower() in ("true", "1", "yes", "on")` as the FIRST statement of every new predicate; never cached at import. Flag OFF: byte-identical bodies, SSE frames, saved rows, cache writes, prompt bytes and logs, pinned with the full configuration AND the production set of record, with call recorders (section 5). No knob.
- Class (H1-9): FOCUS (the result screen of both live bundles once flipped: the Specs section, the confidence chips, the dimension set, the reviews block). Chain: spec -> adversarial spec review -> rulings -> RED (frozen) -> gate -> GREEN -> two adversaries (correctness; contract-and-live-bundles) -> fix rounds -> final round (comm set + source-scanning pins + client fences by path) -> PR.
- Worktree: C:/Users/SynAckITPC/Documents/AI/sc-inc-h1 (detached at the base; read-only in this round). Branch for later rounds (H3): fix/inc-h1-honest-empty (the prompt template's feature/s81-<slug> is replaced by this lane's name, common brief H3). RED files: tests/test_inc_h1_honest_empty.py (unit grain) and tests/test_inc_h1_body_pins.py (body grain, wiring, identity). Runner tags: inc-h1-*.
- Base sha (full): 731bcddf531a7e123963246168ca19f262859337 (merge of #404 S81-07c on top of #403 S81-12d and #402 S81-07). `git -C <W> status --short`: EMPTY before the first probe and after the last one of this round; the only new file is this spec under the gitignored .qa-s80/ (`git check-ignore -v` -> .gitignore:72 `.qa-*/`).
- Measurement location: <SP>/INC-H1/ (notes.txt; tools/blobcmp.py, tools/closure.py, tools/prompt_anchors.py; spec/closure.json, spec/comm_set.txt, spec/comm_chunks.txt, spec/RA_683f56c0.tsx, spec/eval_findings_1_9_19.txt). <SP> = C:/Users/SYNACK~1/AppData/Local/Temp/claude/cde30765822f13ce/fce5ef8e-45c1-47d7-9da1-42b27fb2581e/scratchpad. Source reading: the plain export <SP>/src/731bcddf, proved byte-equal to the base blobs after CRLF normalisation for every file cited (tools/blobcmp.py: extraction_service, structured_comparison_service, fact_check_service, scoring_service, response_builder, review_service, cache_service, result_gate, ResultsAccordion.tsx, ConfidencePills.tsx: SAME); tests, fixtures and the store bundle read with `git -C <W> show <sha>:<path>` / `git -C <W> grep` only; CLAUDE.md from <SP>/src/CLAUDE_md_731bcddf.txt (blob ff7fe1fe = the base blob).
- This round is READ-ONLY (common brief H5 c, R0-9): no pytest, jest, tsc or eslint ran; every run is listed with its exact gate.py command and marked DEFERRED TO RED.
- Evidence pointers: the unit brief <SP>/INC-H1/brief_rulings.txt (rulings H1-1..H1-10, questions Q1-Q6; read in full first and again before reporting); <SP>/s95/reports/D2_image_specs_reviews_chips.md sections b-f, D3_client_consent_logo.md section a, ADV_review.md R-4, R-5, C-2, C-3; <SP>/record/inc/RULINGS_INC_R0.md; <SP>/record/inc/DEFECT_LEDGER_INCIDENT.md; <SP>/record/s81/PLAN_S81.md (Standing constraints :13-19, VERIFY corrections :71-120, Fable rulings F1-F4 :123); <SP>/record/s80/PLAN_S80.md section 0 and contract_freeze.json (:36, :64, :435, :542); <SP>/record/s80/eval_regression.json findings 1 (harness), 9 (T04 the all-dash dict) and 19 (T14 reviews without a source); the house template <SP>/record/s79/{B3B_APPLE_REVOKE_UNIT_SPEC.md, S78_F8_UNIT_SPEC.md} and this lane's worked example <SP>/record/inc/INC-X6_UNIT_SPEC.md with RULINGS_INC_X6.md (X6-R1 signature-aware helpers, X6-R12 two configurations, X6-R22 the main lane's two statements on `_clean_specs`); the common brief <SP>/wf/inc-common.txt H0-H12.
- Sister units and contracts: INC-R1 (resolution) and INC-I1 (pictures) are specified in parallel in their own worktrees and are NOT assumed merged; INC-X6 HONEST-BARS (spec at 6b909e0a, not built) owns the bars, the fact-line templates and the one-side default-50 rows; INC-C1 owns the client empty states (the honest Specs line, the reviews header). Known rebases: INC-X6 edits RB `_build_scoring_v2` / `_build_factual_verdict` / `_top_dim_candidate` / `_runner_up_dim_candidate` / `_format_line2` and SCS :63 / the tradeoff and summary sites; H1 edits other hunks of RB `build_comparison_response` and other SCS hunks; INC-R1 may edit SCS Step 1 and the top of `_fetch_product_data`; INC-I1 the image override SCS:6396-6429 and image_service. Whichever merges second rebases and re-runs the comm set. Contracts consumed: result_gate.NA_VALUES (the token base, RG:63), the D08 count-checked prompt-twin derivation (ES:1031-1044), the frozen client contract (contract_freeze.json:36, :64), the S81-04c arms (ES:1742-1747, ES:1915-1920: H1 keeps its footprint off those statements). The main lane's two `_clean_specs` statements (RULINGS_INC_X6 X6-R22: the specs error string is stripped there; `_field_confidence` feeds the result gate's tier-3 detection) stay true trivially: H1 does not edit `_clean_specs`.
- Personal-data rule: the repo is public. No personal value in any file, test, fixture or log line; product names in tests are synthetic ("Brand A Line One"); no credential shape; digests written as base64 or built at run time; no constant whose name contains access / auth / api / credential / creds / key / password / secret / token. The em dash token is built at run time (chr(0x2014)) so every file stays pure ASCII.

Short names: ES = app/services/extraction_service.py, SCS = app/services/structured_comparison_service.py, FC = app/services/fact_check_service.py, SS = app/services/scoring_service.py, RB = app/services/response_builder.py, RV = app/services/review_service.py, RG = app/services/result_gate.py, PDS = app/services/product_data_service.py, HE = app/services/honest_empty.py (NEW). RA / RC / CP = SmartCompareApp/src/components/results/{ResultsAccordion, ResultsContent, ConfidencePills}.tsx. "OTA" = the over-the-air JS on main (the results files at 731bcddf equal f1e20c39: `git diff --stat f1e20c39 731bcddf -- SmartCompareApp/src/` touches only AiConsentSheet, the i18n catalogs, Step05Trust, aiConsent, consent); "store" = 683f56c0. Every file:line below was read at 731bcddf in this run (store lines read with `git show 683f56c0:`).

## 0. What the unit does

Today a comparison whose spec sheet came back empty ships as if it had data. Measured at 731bcddf:
- With ENABLE_SPECS_NO_FABRICATION OFF (production), `extract_specs` stamps "N/A" into every empty field of the 11-field fragrance schema (ES:213-227 schema, ES:1679-1707 loop, the stamp at ES:1706-1707); the sheet is cached 7 days (L1) and 30 days (L2) (SCS:6912-6922; SCS:1709; PDS:18). `specs.products[i].specs` and the `products[i]` alias ship the stamps (RB:2004, RB:2268) and `specs_comparison.rows` keeps "N/A" vs "N/A" rows (RB:762 skips only None and ""). Both live bundles fall back to the structural key set when no key has a real value and draw every key as a dash row headed "N dimensions" (RA:206-223, RA:293-296, RA:596-599 OTA; RA:165-182, RA:252-255, RA:552-553 store).
- `verify_spec_citations` scores every non-meta key, so 11 "N/A" fields become 11 "unverified" rows (FC:213-220; FC:565-568); with ENABLE_CONFIDENCE_FACTCHECK_WIRING OFF (production) the specs leg counts them as 11 citations, and 8 or more is "strong" = the High chip (SS:1110-1115, SS:1207; CP:54-58 maps strong to High). The fragrance versatility score is that citation reliability (SS:2177; SS:2096 (verified + 0.7 likely + 0.3 unverified) / total), emitted with a hard-coded "medium" confidence (SS:3585), and the factual verdict cites it ("<A> leads on Versatility.", RB:1097 via RB:920-950).
- The reviews prompt has no no-data field (ES:983-996); `build_review_praise` falls back to the consensus whenever the sentiment is not negative and the text is at least 12 characters (RV:631-645), so the model's "No review data was available in the provided search results ..." is the praise both bundles draw (RA:414-421 OTA, RA:371-379 store); the no-data dict is cached as a normal one (RV:792-809).

Behind `ENABLE_HONEST_EMPTY`, H1: (1) WIRE VIEWS: every empty spec value (None, an empty container, NaN, or a string whose strip().lower() is one of "", "n/a", "na", "none", "unknown", "-", "null", U+2014, or contains "or null") is OMITTED from `specs.products[i].specs`, from the `products[i].specs` alias, from `specs.specs_comparison.rows` and from the SSE `specs` frame, a field with a real value unchanged; for a product whose reviews answer is no-data (`has_review_data` false, or no highlights and a consensus carrying a guard phrase) no review text reaches the wire (praise null, consensus "", highlights and the four text lists []); (2) FACT-CHECK: `verify_spec_citations` and the #107 cached citation map skip empty values, so empty fields never count as citations (no Specs High and no reliability-proxy bar or "leads on Versatility" line from empty fields: a product with no real field has a reliability total of 0, which the scoring already treats as missing, SS:2087-2088); (3) REVIEWS: the reviews prompt gains `has_review_data` through a count-checked twin selected per call (the OFF prompt is the base constant, sha 46791e1b... = the D08 P7 pin), and `build_review_praise` never uses a no-data consensus as praise; (4) CACHE: an all-empty spec sheet and a no-data reviews dict are never written to L1 or L2 (the post-extract writes, the enriched re-cache and the L2-to-L1 promotions); (5) LOG: one INFO line per product, `[HONEST_EMPTY] product=<slot> specs_real=<n> specs_dropped=<n> reviews=<data|no_data> cached=<yes|no>`.

What H1 does NOT move (H1-1): the data stage that scoring, the refill cascade and the verdict prompt read (extract_specs and `_clean_specs` keep their stamps, so the smart-fallback / Tier-2 / Tier-3 triggers, `compute_scores`, the crown inputs other than the fact-check counts, and the verdict prompt's product JSON are byte-identical with the flag ON); the scoring_v2 captions and bars (the views are applied AFTER `scoring_v2` is built: INC-X6's domain); ENABLE_SPECS_NO_FABRICATION's and ENABLE_CONFIDENCE_FACTCHECK_WIRING's own behaviour; any client file; the S81-04c arms; the link-mode body (url_extraction_service, out of scope, section 10).

## 1. Base state MEASURED (731bcddf)

### 1.1 The specs path (Q1, Q5)

| Site | file:line | Measured |
|---|---|---|
| fragrance schema | ES:213-227 | 11 fields: scent_family, notes_top, notes_heart, notes_base, longevity, sillage, season, occasion, volume, concentration, heat_stability |
| extract_specs | ES:1584-1747 | route("specs") ES:1611; json.loads ES:1627; alias reconcile ES:1651-1668; `no_fab = specs_no_fabrication_enabled()` ES:1675; loop over meta keys + schema ES:1679; is_empty = None, "", "null", contains "or null" ES:1686-1691; no_fab: placeholder "n/a"/"na" + uncited dropped ES:1692-1705; OFF: `cleaned[key] = "N/A"` ES:1706-1707; `str(val)` ES:1712 (a literal "N/A" / "unknown" from the model passes through); `_source` siblings copied when truthy ES:1714-1721 (an empty field keeps its source OFF); S81-04c arm ES:1742-1747 |
| _get_specs | SCS:6831-6926 | L1 hit returns the cached dict + `_cached` True SCS:6837-6840; L2 hit: `_cache_set_async(cache_key, db_specs, SPECS_CACHE_TTL)` promotion SCS:6847, `_cached` True, `_cache_source` "db" SCS:6848-6850; spine SCS:6859; extract SCS:6867-6870; #107 map `specs["_spec_citation_confidence"] = verify_spec_citations(specs, raw_snippets)` SCS:6898-6910; WRITE when `specs and not specs.get("error") and not unified_search_timed_out(search_results)` SCS:6913-6922 (L1 + `save_specs` L2); `_search_snippets` + `_cached` False SCS:6924-6925. An all-"N/A" sheet passes every conjunct |
| Phase-1 assignment | SCS:6301-6319 | a race timeout or error gives `_price_fallback_on_miss(key, ...)` = None for specs and reviews (SCS:6984-6993 docstring) |
| fact-check on RAW specs | SCS:6431-6455 | `_search_snippets` popped; `_resolve_citation_confidence(raw_specs, snippets)` SCS:6440; shopping upgrade only for keys already in the map SCS:6449-6454; `result["_spec_confidence"]` SCS:6455. Runs BEFORE `_clean_specs` |
| _resolve_citation_confidence | SCS:440-460 | ENABLE_SPEC_CONFIDENCE_CACHE (SCS:368-384) ON and a non-empty cached `_spec_citation_confidence` map -> that map AS IS (SCS:456-459), else verify_spec_citations (SCS:460) |
| _clean_specs | SCS:3520-3572 | meta_keys brand / model / variant / category / _cached / error dropped (SCS:3524, the S81-04c GC-6 error strip); `_source` siblings lifted into `_field_confidence` (SCS:3529-3541, 3560-3561); empty value -> "N/A" (SCS:3551-3552); lists joined, dicts json-dumped (SCS:3553-3558); #107 carry (SCS:3568-3571). Called once on the main path (SCS:6457-6458) |
| refill triggers | SCS:6541-6547, SCS:800, SCS:921, SCS:3331-3333 | missing = value in (None, "", "N/A") / `not value or value in ("N/A", "")`: an omitted key and an "N/A" are both "missing"; a literal "unknown" / "n/a" / "-" is NOT missing |
| fill merges | SCS:6582-6589, 6617-6622, 6648-6653 | smart fallback skips a falsy or "N/A" value; tier 2 / 3 values merge when `existing in (None, "", "N/A")` |
| enriched re-cache | SCS:6656-6687 | only when a fill changed the dict (`_specs_enriched_by_fallback`) and not timed out (SCS:6669); writes the CLEANED dict when `_enriched and not _enriched.get("error")` (SCS:6674-6682, L1 + L2) |
| SSE specs frame | SCS:5403-5414 | products[i].specs = pd.get("specs") (post-clean), fact_check, image_url |
| RB specs projection | RB:1999-2017 | `specs.products[i].specs = pd.get("specs")` RB:2004; `specs_comparison.rows = _build_specs_rows(product_data)` RB:2015 |
| _build_specs_rows | RB:735-772 | one row per field both sides populate; skips `_`-keys; skips only `v in (None, "")` RB:762, so "N/A" vs "N/A" rows ship with winner None (`_spec_row_winner` RB:673-711 treats `_SPEC_NA_TOKENS` RB:635 as missing) |
| alias | RB:2227-2268 | the loop mutates pd (pros/cons, image_url, review_praise RB:2242, the scrubbed reviews copy RB:2247-2249, category_profile RB:2258, public_price_view RB:2264); `result["products"] = product_data` RB:2268 |
| literal order | RB:1927-2079 | `result = {` RB:1927; the specs block RB:1999 and the reviews block RB:2019 are evaluated BEFORE `"scoring_v2": _build_scoring_v2(...)` RB:2079 (dict-literal order) |
| captions read specs | SS:3592-3685 | projection `f"{sa} vs {sb} projection"` when both sillage values are truthy SS:3669-3677 ("N/A" is truthy: "N/A vs Moderate projection", RC9, INC-X6 / F8 domain); longevity hours caption SS:3660-3668 |

### 1.2 The fact-check, the chips and the reliability proxy (Q1, Q3, Q6)

| Site | file:line | Measured |
|---|---|---|
| verify_spec_citations | FC:204-263 | skips `_source` keys, `_`-keys and brand / model / variant / category (FC:213-215); no source or "training" -> "unverified" (FC:219-220); snippet branch: an "N/A" value with a snippet source grades "likely" (terms ["n/a"] unmatched, FC:250-255) - a citation even with the wiring ON |
| build_fact_check | FC:555-585 | specs_verified / likely / flagged / unverified counted from `_spec_confidence` (FC:565-568) |
| _product_fact_check_pcts | SS:1089-1115 | total = v + l + u + f; verified_pct = round(v / total * 100); citations = total with ENABLE_CONFIDENCE_FACTCHECK_WIRING OFF (SS:1115), v + l ON (SS:1113-1114) |
| compute_confidence specs leg | SS:1200-1213 | best over products; strong = best_pct >= 40 or best_citations >= 8 (SS:1207); acceptable = >= 20 or >= 4 (SS:1208) |
| pills | RB:1184-1240, RB:1318-1321; RC:584-596; CP:54-58 | `scoring_v2.confidence_legs` from compute_confidence(product_data); strong -> High, acceptable -> Medium, weak -> Low (CP unchanged between store and OTA: `git diff --stat 683f56c0 731bcddf -- .../ConfidencePills.tsx` empty) |
| reliability raw | SS:1831-1839 | `_score_reliability(fact_check)`; None -> `_reliability_missing` |
| _score_reliability | SS:2071-2106 | total == 0 -> None (SS:2087-2088); ENABLE_RELIABILITY_UNCHECKED_ABSENCE (effective only with ENABLE_MISSING_DIM_RENORM, SS:1062-1070) and v + l + f == 0 -> None (SS:2093-2094); score (v + 0.7 l + 0.3 u) / total (SS:2096), +0.1 price_verified (SS:2098-2099), +0.05 / -0.1 sentiment (SS:2101-2104) |
| fragrance signal map / weight | SS:2175-2179; SS:72 | versatility_score = reliability; default weight 0.15 |
| normalisation | SS:2553-2558; SS:2251-2268 | `_normalize_direct` -> MISSING_SCORE (50, SS:297) when None; a tie of non-MISSING reliability on both sides collapses to MISSING (W4-6a T gate SS:2248-2266) |
| one-side missing | SS:1440-1544; SS:3503-3589 | ENABLE_MISSING_DIM_RENORM excludes a one-sided-missing dim from every overall (SS:1442-1529) and adds `excluded_dims`; `_dim_from_category_lookup` drops a dim only when BOTH sides were missing (SS:3569-3571), else emits it with the breakdown values (50 on a missing side with ENABLE_BUNDLE_C_SCORING false), `confidence: "medium"` (SS:3585); build_dimensions_v2 stamps `winner` None on either was_missing (SS:3920-3927) and does not read `excluded_dims` |
| verdict line | RB:920-950, RB:1073-1131, RB:1134-1181 | `_top_dim_candidate` takes any non-core row with two numbers and a positive margin for the winner (RB:931-942) -> "{w} leads on {label}." (RB:1097); no candidate -> "{w} edges ahead on the overall picture." (RB:1175); line2 neutral fallback RB:1131 |

### 1.3 The reviews path (Q4)

| Site | file:line | Measured |
|---|---|---|
| REVIEWS_EXTRACTION_SYSTEM | ES:978-1028 | JSON shape ES:983-996 (average_rating, total_reviews, review_summary {overall_sentiment, consensus "2-3 sentence ...", highlights, review_volume, agreement_level}); RULES ES:998-1005; no no-data field. AST-evaluated in this round (tools/prompt_anchors.py): 3364 ASCII chars, sha256 46791e1b346c8be5780004d0245f40bc0947d4445f7950aae04224b2d64987e3 = the D08 P7 pin (tests/test_s81_d08_jsonld_widen.py:1147-1158) |
| D08 twin | ES:1031-1044 | REVIEWS_EXTRACTION_SYSTEM_NO_RATING = the base minus the two rating-ask lines, count-checked, RuntimeError at import if a line moved; sha256 ebe9f3f3... |
| extract_reviews | ES:1863-1920 | system picked per call: NO_RATING when `_jsonld_widen.jsonld_rating_enabled()` else the base (ES:1886-1889); route("reviews") ES:1890; S81-04c arm ES:1915-1920 |
| _normalize_review_response | ES:1923-1976 | defaults sentiment "mixed", consensus "", highlights [], volume "minimal", agreement "moderate" (ES:1929-1933); source_ratings [] (ES:1944); unknown model keys pass through; common_praises / common_complaints derived from highlights (ES:1965-1974) |
| get_reviews | RV:722-851 | L1 hit returns the cached dict (RV:749-752); L2 hit: `set_cached(cache_key, db_reviews, REVIEWS_CACHE_TTL)` promotion RV:759; extract RV:775; WRITE when `reviews and not reviews.get("error") and not unified_search_timed_out(search_results)` RV:792-809 (inline `set_cached` RV:794 when ENABLE_USAGE_PATH_OFFLOOP is OFF, `save_reviews` L2 RV:801-804, the durable pool write RV:805-808); consult and YouTube re-caches only when `extraction_persisted` (RV:825-829, RV:842-846). TTL 7 d (RV:45), L2 14 d (PDS:20) |
| retailer quotes | RV:280-348; SCS:6806-6815 | built from the highlights' cited snippets (no highlights -> []) |
| build_review_praise | RV:547-646 | type checks RV:562-566; positive highlights woven RV:597-629; consensus fallback when sentiment is not "negative", >= 12 chars, no banned vocab (RV:631-645) |
| RB praise and reviews | RB:84-96, RB:2019-2068, RB:2242-2249 | `_safe_review_praise(pd)` -> build_review_praise of a scrubbed copy; `reviews.products[i]` ships review_summary (scrubbed, RB:2039-2047), retailer_quotes (RB:2053), review_praise (RB:2059), youtube_review_signal (RB:2064); the alias pd gets review_praise (RB:2242) and the scrubbed reviews copy (RB:2247-2249) |
| SSE reviews frame | SCS:5466-5497 | review_summary (scrubbed), retailer_quotes, youtube signal per product |
| verdict prompt input | ES:2482-2500, ES:2674-2681 | `json.dumps(_verdict_safe_product(product))`: the product's specs (with stamps) and reviews (with the consensus) reach the verdict prompt; H1 leaves that input unchanged (section 0) |

### 1.4 Every cache write path for specs and reviews (Q5)

| # | Write | file:line | Today with an empty input |
|---|---|---|---|
| W1 | specs L2 -> L1 promotion | SCS:6847 | an all-"N/A" L2 entry is re-promoted to L1 for 7 d on every L1 miss |
| W2 | specs post-extract L1 + L2 | SCS:6913-6922 | an all-"N/A" sheet (or, under ENABLE_SPECS_NO_FABRICATION, a sheet with no field at all) is written |
| W3 | specs enriched re-cache L1 + L2 | SCS:6669-6682 | written only after a fill added a value; a fill of a token value ("unknown") makes it an all-empty sheet that is written |
| W4 | reviews L2 -> L1 promotion | RV:759 | a no-data L2 entry is re-promoted |
| W5 | reviews post-extract L1 (inline or pool) + L2 | RV:792-809 | a no-data dict is written |
| W6 / W7 | reviews consult / YouTube re-caches | RV:825-829, RV:842-846 | gated on `extraction_persisted` (set only by W5): they follow W5 |

No other writer under app/ (git grep `save_specs`, `save_reviews`, `_cache_set_async(.*specs`, `set_cached(cache_key, .*reviews`: only the sites above; the off-clock scripts are out of scope). The comparison-level cache (`get_comparison_cache` / `set_comparison_cache`) has no caller under app/ (INC-X6 Q-13, unchanged at this base).

### 1.5 What both live bundles render (Q2; code reading, not a device)

| Reader | OTA (731bcddf = f1e20c39) | store (683f56c0) | Measured |
|---|---|---|---|
| source of the table | RC:244-249, RC:266-270 | same logic | specsProducts = `result.specs.products`; specsComparison = `result.specs.specs_comparison.rows` |
| client NA set | RA:86-87 | RA:81-82 | HIDDEN brand / model / variant / category; NA {"n/a", "na", "null", "none", "unknown", ""} (no "-", no U+2014) |
| key set | RA:198-223 | RA:165-182 | pass 1 "rich" = keys with a real value on any product (filterSpecs RA:89-107 / :84-); pass 2 "structural" = every non-null scalar key, used ONLY when rich is empty |
| header | RA:288-297 | RA:248-256 | "<n> dimensions" (n = allSpecKeys.length, counted BEFORE the row filter) or the bare `results.accordion.specsDimensions` ("dimensions", en.json:779 OTA / :776 store) when no key |
| rows | RA:575-599 | RA:530-553 | a value null / object / client-NA -> the em dash; a row with exactly ONE dash is dropped (RA:596-598 / :552-553); 0 or 2 dashes kept |
| honest lines | RA:123-157, RA:551-552; RC:647-664 | absent | OTA only, and only when the body carries `metadata.section_status` / `field_status` (ENABLE_RESULT_STATUS_METADATA / ENABLE_FIELD_STATUS_METADATA, both OFF on web): `sectionNeedsHonestLine` = section_status.specs === "unavailable" |
| reviews body | RA:401-465 | RA:359-423 | per product praise = `reviews.products[i].review_praise` else the root `products[i].review_praise` (RA:413-421 / :371-379); a product with no praise and no rating > 0 is skipped (RA:440-442 / :398); no block -> "Reviews are still coming in." (RA:457-463 / :418); consensus, highlights and retailer_quotes are NOT rendered by either bundle (git grep of both trees: only types.ts:237 / :235 names `consensus`) |
| reviews header | RA:170-196, RA:267-276 | RA:129-155, RA:226-235 | sums review_count over both, avg over rated; "reviews across both" always (RC-REVHDR, INC-C1) |
| pills | RC:584-596; CP:54-58 | same | `scoring_v2.confidence_legs` |
| SSE frames | HomeScreen.tsx:470-471; api.ts:958-967 | HomeScreen.tsx:424-425; api.ts:879-888 | onSpecs / onPrices only call markTtfb; no screen renders the specs or reviews frame |

So, for a product pair whose specs carry no real value, today both bundles draw one dash row per stamped key and "11 dimensions"; with the wire view the dict is empty and both bundles draw the Specs row with the bare "dimensions" header and an expanded table holding only the two names (H1-10, the interim; INC-C1 owns the empty line). For a short dict (some real keys), the rich path is used today and with the flag: the same rows and the same count (the NA keys never entered the rich set), so the visible table is unchanged; the server `rows` lose their NA entries, which only fed `winnerByField` for rows the client already dropped (one-dash) or drew neutral (two dashes).

### 1.6 Every NA token set and NA test in the code (Q1)

| Site | file:line | Set or test |
|---|---|---|
| result gate | RG:63, RG:245-250 | NA_VALUES {"", "n/a", "na", "none", "unknown", "-"} on strip().lower(); `_is_na(None)` True |
| response builder | RB:635, RB:597-601, RB:687-688 | `_SPEC_NA_TOKENS` {"n/a", "na", "none", "unknown", "-", ""} (= NA_VALUES) |
| category profile | ES:1434, ES:1485-1494 | `_PROFILE_NA_VALUES` {"n/a", "na", "null", "none", "unknown", "", "-", U+2014} |
| extract / clean empty test | ES:1686-1691, SCS:3551 | None, "", "null", contains "or null" |
| no-fab placeholder | ES:1700-1702 | strip().lower() in ("n/a", "na") |
| spine | app/services/spec_spine_service.py:250-265 | ("n/a", "na", "null", "none") |
| coverage | SCS:644-647 | (None, "", "N/A", "n/a") or whitespace |
| refill tests | SCS:800, 841, 921, 955, 3332, 6546, 6583, 6586, 6619, 6650 | the exact "N/A" and "" (case-sensitive) |
| scoring | SS:536, SS:1921, SS:1979 | `not value or value == "N/A"` |
| shopping cross-check | FC:333 | `not value or value == "N/A"` |
| openai fills | app/services/openai_service.py:781-785, 858 | drop None and "N/A" |
| client | RA:87 (OTA) / RA:82 (store); ResultsScreen.tsx:745-747 | {"n/a", "na", "null", "none", "unknown", ""} |

"not specified" (the brief's example) appears nowhere under app/ (git grep, 0 hits). The H1 set is therefore the union the code already uses: NA_VALUES + "null" + U+2014 + the "or null" substring + None (section 2.2).

### 1.7 Production state and the flag mixes (Q3)

Production flag state of record (names only; the newest dated lines): the session-81 ledger line 316 (2026-11-07 06:24, the flag-value read of web: ON ENABLE_BH_GCC_CATALOG_SOURCES, ENABLE_APPLE_TOKEN_REVOCATION, ENABLE_BRIGHTDATA_BUDGET_GATE, ENABLE_BRIGHTDATA_FALLBACK, ENABLE_CAMERA_FAILURE_ENVELOPE, ENABLE_COHORT_PERSONALIZATION, ENABLE_COMPARE_AUTH_REQUIRED, ENABLE_CONSENT_PERSIST, ENABLE_FIRECRAWL, ENABLE_FRAGRANCE_SIZE_RECONCILE_FIX, ENABLE_HYBRID_MODEL_ROUTING, ENABLE_LOGOUT_UPSTREAM_REVOCATION, ENABLE_OFFLOOP_DNS_RESOLVE, ENABLE_PAGE_SCRAPE, ENABLE_PAID_ROUTE_METERING, ENABLE_PHASE2_RESIDUAL_GUARD, ENABLE_PRICE_PARSE_OFFLOAD, ENABLE_PRICE_PATH_REDIS_OFFLOOP, ENABLE_PRICE_TITLE_PERSIST, ENABLE_REFERRAL_SYSTEM, ENABLE_SCRAPEDO, ENABLE_SERPER_FAIL_FAST, ENABLE_UNIFIED_SEARCH_BOUND, ENABLE_VARIANT_DESCRIPTOR_AXES; STREAM_HARD_CAP_SECONDS set; false: ENABLE_BUNDLE_C_SCORING, ENABLE_GENUINE_PRICE_PRIORITY, ENABLE_REENGAGEMENT_PUSHES, ENABLE_SUPABASE_CLIENT_REUSE; every other name unset) plus the common brief H12(c) (2026-11-14: ON ENABLE_LLM_LEDGER_V2, ENABLE_LLM_SPEND_BREAKER, ENABLE_REQUEST_CONTEXT_HEADERS, ENABLE_OPENAI_EGRESS_STOP, ENABLE_OPENAI_PRE_V3, ENABLE_ANTHROPIC_TEXT, ENABLE_ANTHROPIC_VERDICT, ENABLE_LEGACY_FINGERPRINT_READER, ENABLE_CONSENT_PERSIST; OFF ENABLE_ANTHROPIC_MODERATION, ENABLE_ANTHROPIC_VISION, ENABLE_KB_INGEST, ENABLE_KB_FIRST_SERVE, ENABLE_FIELD_STATUS_METADATA, ENABLE_RESULT_STATUS_METADATA). The record copy of the ledger ends 2026-11-11 (its last lines 425-443); no later line names a flag of this unit. So in production: W = ENABLE_CONFIDENCE_FACTCHECK_WIRING, U = ENABLE_RELIABILITY_UNCHECKED_ABSENCE, R = ENABLE_MISSING_DIM_RENORM, N = ENABLE_SPECS_NO_FABRICATION, C = ENABLE_SPEC_CONFIDENCE_CACHE and T = ENABLE_TIE_IS_NOT_MISSING are all UNSET (OFF); this ESTABLISHES what D2 marked LIKELY (D2 b "most likely off", d, e).

Documented activation orders:
| Flag | Order | Source |
|---|---|---|
| C | first of W's chain | SS:1044-1047; CLAUDE.md:410 |
| W | HARD order: C, then ENABLE_FACTCHECK_SHOPPING_KEY right before ENABLE_FACTCHECK_CURRENCY_NORMALIZATION (#106), ENABLE_CITATION_RUBRIC_V2 (#108) canaried before W | SS:1044-1055 |
| R | after the W4-6b order-symmetric tie-break | CLAUDE.md:357, :830 |
| U | COUPLED: always False while R is OFF (code, SS:1066-1067); flips LAST: W4-6b -> R -> U | SS:1062-1070; CLAUDE.md:830 |
| N | LAST, only after the search layer is restored and D1's cascade closure | CLAUDE.md:346, :377 step (7) |
| T | COUPLED: always False while R is ON | SS:494-500; CLAUDE.md:822 |

Reachable mixes (the orders allow): W in {0, 1} with W = 1 implying C = 1; (R, U) in {(0, 0), (1, 0), (1, 1)} ((0, 1) is code-equal to (0, 0)); N in {0, 1}: 2 x 3 x 2 = 12 mixes, each with H OFF and ON. Section 2.5 walks them.

### 1.8 Libraries, the reader idiom, the names the touched code reads

- Pinned venv .venv-qaren (the CI pins; dist-info directories listed in this run): pytest 9.1.1, pytest_asyncio 1.4.0, pytest_timeout 2.4.0, pydantic 2.13.4 (= requirements.txt `pydantic==2.13.4`; `git diff 6b909e0a 731bcddf -- requirements.txt` is empty). H1 adds no dependency and no external host (no processors.json row).
- Idiom: ES:552-603 `specs_no_fabrication_enabled` (`os.getenv(NAME, "false").strip().lower() in (...)`); RG:81 `_TRUTHY`. The house module-import form: `from app.services import jsonld_widen as _jsonld_widen` (ES:33, RB:25): every H1 call site calls `_honest_empty.<fn>(...)` through the module attribute, so one monkeypatch of HE reaches every site (the recorders of section 5).
- Env names the touched functions read (the FULL CONFIGURATION of section 5, derived by the RED round from the import graph as INC-X6 did, at least): FC ENABLE_CITATION_RUBRIC_V2, ENABLE_FACTCHECK_CURRENCY_NORMALIZATION, ENABLE_FACTCHECK_HONEST_ABSENCE; RV ENABLE_REVIEW_SOURCE_CONSULT, ENABLE_YOUTUBE_SOURCE, ENABLE_USAGE_PATH_OFFLOOP, ENABLE_PRICE_PATH_REDIS_OFFLOOP, ENABLE_DATA_GUARDS_V2; ES ENABLE_JSONLD_RATING, ENABLE_SPECS_NO_FABRICATION and the router names (ENABLE_ANTHROPIC_TEXT, ENABLE_OPENAI_PRE_V3, ENABLE_OPENAI_EGRESS_STOP); SCS ENABLE_SPEC_CONFIDENCE_CACHE, ENABLE_SPEC_SPINE, ENABLE_FACTCHECK_SHOPPING_KEY, ENABLE_CONFIDENCE_SINGLE_COMPUTATION, ENABLE_ASYNC_REDIS_OFFLOAD, ENABLE_UNIFIED_SEARCH_BOUND, ENABLE_TIER_FILL_RESIDUAL_GUARD, ENABLE_PHASE2_RESIDUAL_GUARD, ENABLE_EARLY_SPECS_STASH; SS ENABLE_CONFIDENCE_FACTCHECK_WIRING, ENABLE_RELIABILITY_UNCHECKED_ABSENCE, ENABLE_MISSING_DIM_RENORM, ENABLE_TIE_IS_NOT_MISSING, ENABLE_VALUE_DIM_PARTIAL_SIGNAL, ENABLE_SPEC_FIELD_NORM, ENABLE_BUNDLE_C_SCORING (process-cached: reset like the digest generator); RB ENABLE_GPT_WINNER, ENABLE_HONEST_PARTIAL_SCORING, ENABLE_SINGLE_VERDICT_MARGIN, ENABLE_WINNER_PROSE_RECONCILE, ENABLE_YOUTUBE_SOURCE, ENABLE_RESULT_STATUS_METADATA, ENABLE_RESULT_GATE, ENABLE_RESULT_AGGREGATES, ENABLE_STORE_LABEL, ENABLE_LLM_LEDGER_V2 (DEBUG_STAGE_TIMINGS and EVAL_CAPTURE_DEBUG stay unset: process-cached / debug-only). Census of this round: FC 3, RV 2 direct + the imported readers, RB 7, ES 9, SCS 30 distinct literal names (grep of getenv / environ.get / _flag_on).

### 1.9 Guards the new code must not trip

- tests/test_s81_st1_usage_path_offloop.py:1996-2018 (`test_r25a_source_inventory`, AST of RV `get_reviews`): exactly one `run_redis_offloop(get_cached, ...)`, one non-durable pool read, exactly FOUR direct `set_cached` calls, every pool `set_cached` durable. H1 wraps the existing RV:759 call in a condition and adds a conjunct to RV:792; it adds and removes no `set_cached` call.
- tests/test_m18_offload_sweep_residual.py:530-538: no inline `if not has_budget(` in RV and `_has_budget_async(` at least 3 times: untouched.
- tests/test_s81_d08_jsonld_widen.py:1147-1158 (P7: the base constant's sha and that extract_reviews SENDS it with ENABLE_JSONLD_RATING OFF) and :836-850 (R18: the NO_RATING derivation): the base constants are not edited; the twins are new names.
- tests/test_prompt_fence.py:272-287 (the guard sentence in REVIEWS_EXTRACTION_SYSTEM and _NO_RATING) and :325-332 (extract_reviews wraps the digest region); tests/test_prompt_injection.py:113-117 (no `{brand}` / `{name}` placeholder): the twins keep the guard and add no placeholder.
- tests/test_s81_s04c_refusal_log_hygiene.py (the LLMUnavailableError arms by behaviour; P3 records `any_role_enabled()` reads only): H1 edits no line of ES:1742-1747 / ES:1915-1920; the H1 read in extract_reviews is not an any_role read.
- tests/test_s81_s08b_legacy_fingerprint.py:820-822: exactly ONE line starts with "**Feature Flags:**" in CLAUDE.md: the pointer sentence is added INSIDE that line, never as a new line.
- tests/test_s75_fanout_identity.py FY25 (nine flag-OFF compare digests, :278-286) and the golden fixtures that pin flag-OFF bodies (tests/fixtures/s81_g8_flag_off_golden.json, s81_s18_flag_off_golden.json, missing_dim_renorm_flag_off_golden.json, behavioral_flag_off_golden.json, rubric_truth_flag_*): green and unedited (flag OFF byte-identical).
- The hermeticity pins (no import-time env read): the flag is read per call; HE reads nothing at import.
- gitleaks names (H7): no new constant name with a scanner keyword (HONEST_NA_TOKENS, REVIEW_NO_DATA_PHRASES, REVIEWS_EXTRACTION_SYSTEM_HONEST, _H1_SHAPE_ANCHOR are clean).
- Pure ASCII in every added line (the em dash built with chr(0x2014); the tool layer decodes typed backslash-u escapes, so never type the escape).
- The house rule "new external host -> processors.json row": none.

### 1.10 Line endings and the base pass state

Line endings: core.autocrlf=true (measured), no .gitattributes: ES, SCS, FC, RV, RB and CLAUDE.md are LF in the index and CRLF in the working copy (the export carries CRLF: blobcmp crlf counts 2904 / 9979 / 608 / 1172 / 2387); the Edit tool keeps CRLF; a whole-file diff in `git diff --stat` is a defect. New files (HE, the two RED files): LF in the index, the house form of the lane's RED files.

Base pass state: NOT MEASURED in this read-only round. DEFERRED TO RED, with these exact commands (<P> = PYTHONIOENCODING=utf-8 C:/Users/SynAckITPC/Documents/AI/.venv-qaren/Scripts/python.exe, <G> = <SP>/harness/gate.py, <W> = C:/Users/SynAckITPC/Documents/AI/sc-inc-h1, <N> = <SP>/INC-H1/red):
1. Touched-function suites at base (two calls, at most 25 files each): `<P> <G> --bound 1200 --tag inc-h1-base-touch1 --log <N>/base-touch1.log --cwd <W> -- tests/test_fact_checking.py tests/test_decomposed_services.py tests/test_spec_confidence_cache.py tests/test_specs_no_fabrication_guard.py tests/test_lane1_helpers_unit.py tests/test_s80_b1.py tests/test_review_paraphrase.py tests/test_fragrance_content_quality.py tests/test_w4_12_display_contract.py tests/test_m13_33_review_fire_and_forget.py tests/test_s77_redis_offloop.py tests/test_s81_st1_usage_path_offloop.py tests/test_youtube_reviews_race.py tests/test_review_source_consult.py tests/test_s81_d08_jsonld_widen.py tests/test_m18_factcheck_honest.py tests/test_review_prompt_quality.py tests/test_extraction_prompt.py tests/test_smart_fallback.py tests/test_fact_check_service_v2.py tests/test_product_data_service.py tests/test_m18_offload_sweep_residual.py` and `<P> <G> --bound 1200 --tag inc-h1-base-touch2 --log <N>/base-touch2.log --cwd <W> -- tests/test_streaming.py tests/test_s75_fanout_identity.py tests/test_confidence_thresholds.py tests/test_scoring_v2_confidence.py tests/test_w4_7_reliability_unchecked_absence.py tests/test_w4_7_confidence_single_computation.py tests/test_w4_7_factcheck_shopping_key.py tests/test_dim_phantom_tie_followup.py tests/test_scoring_service.py tests/test_scoring_rubric_truth.py tests/test_specs_refill_no_fabrication.py tests/test_subtype_spec_reconciliation.py tests/test_s78_tier_fill_residual_guard.py tests/test_unified_search.py tests/test_fire_and_forget_wrap.py tests/test_cost_tracking.py tests/test_be_harness.py` (DEFERRED TO RED).
2. Prompt and source pins at base: `<P> <G> --bound 600 --tag inc-h1-base-prompt --log <N>/base-prompt.log --cwd <W> -- tests/test_prompt_fence.py tests/test_prompt_injection.py tests/test_prompt_truth.py tests/test_model_config.py tests/test_model_config_enforced.py tests/test_s81_s04c_refusal_log_hygiene.py tests/test_hermeticity_pins.py` (the two cold-tiktoken ERROR nodes of test_prompt_truth are known base noise; record them identically) (DEFERRED TO RED).
3. The comm-set base record (section 7, 743 files, 30 chunks, bound 1200 each, tags inc-h1-base-c01..c30): no record exists for 731bcddf under <SP>/harness/base_records/ (listed: 25 shas, not this one; 445f8de3 -> 731bcddf changed ES, SCS and CLAUDE.md among 28 files, so the cccfb855 record is not reusable per file for this set), so it is computed ONCE at RED and stored by LC-6 (DEFERRED TO RED).
4. The fourteen client fences by path at base (section 7 G9; they need the orchestrator's node_modules junction) (DEFERRED TO RED / GREEN).

## 2. Contract

Contract freeze re-read (record/s80/PLAN_S80.md section 0 items 1-6; contract_freeze.json :36 `specs.products[i].{name, specs{scalar values; _-prefixed, *_source, brand/model/variant/category keys hidden}}`, `reviews.products[i].{name, rating, review_count, rating_count, review_praise}` with the root fallback, `specs_comparison rows {field, winner 0|1|null}`; :64 "reviews.products / specs.products / specs.specs_comparison: all optional (sections fall back or show calm empty copy)"; :542 RULE 2 `scoring_v2.confidence_legs.<leg>` in strong / acceptable / weak): no path the bundles read is removed, renamed or retyped. H1 changes VALUES only: fewer entries in a free-form scalar map, a `review_praise` null (tolerated: RA:413-421 / :371-379 fall through), a consensus "" and empty lists (same types), a leg word inside the enum, one fewer dimension row while the three core rows stay (the RC raw-array gate `length >= 3` still passes). One additive key: `has_review_data` (bool) inside the `products[i].reviews` alias, when the model returned it. No new envelope, no new code, no 503 of any kind: H1 raises nothing.

### 2.1 Flag and knobs

| Name | Type | Default | Read | Production |
|---|---|---|---|---|
| ENABLE_HONEST_EMPTY | env flag | OFF (unset) | per call, the FIRST statement of every gated HE function (2.2); strip + lower; ON only for true / 1 / yes / on | unset on web (a new name) |

No knob. Constants (test seams; production values in brackets): `HONEST_NA_TOKENS` [{"", "n/a", "na", "none", "unknown", "-", "null", chr(0x2014)}], the substring rule `"or null"`, `SPEC_META_KEYS` [{"brand", "model", "variant", "category", "error"}], `REVIEW_NO_DATA_PHRASES` [("no review data", "provided search results", "no reliable reviewer consensus", "insufficient review")], `REVIEW_TEXT_LIST_KEYS` [("common_praises", "common_complaints", "retailer_quotes", "review_source_quotes")], `LOG_PREFIX` ["[HONEST_EMPTY]"].

### 2.2 The new leaf app/services/honest_empty.py (stdlib only: os, logging, math; imports no app module, so ES / SCS / FC / RV / RB import it with no cycle)

| Symbol | Signature | Contract |
|---|---|---|
| HONEST_EMPTY_FLAG | str | "ENABLE_HONEST_EMPTY" |
| honest_empty_enabled | () -> bool | the idiom; per call |
| spec_value_is_empty | (value) -> bool | PURE, total. None -> True; bool -> False; int -> False; float -> math.isnan(value); str s -> `s.strip().lower() in HONEST_NA_TOKENS or "or null" in s.lower()`; list / tuple -> every element empty (so [] -> True); dict -> `not value`; anything else -> False |
| spec_field_key | (key) -> bool | PURE: a str, not `_`-prefixed, not ending "_source", not in SPEC_META_KEYS |
| spec_real_field_count / spec_empty_field_count | (specs) -> int | PURE: field keys with a real / an empty value; a non-dict -> 0 |
| honest_spec_view | (specs) -> same type | PURE: a non-dict is returned as is; a dict -> a NEW dict in the same key order without (a) every field key whose value is empty and (b) the `<key>_source` sibling of such a key; every other key and value (the `_`-keys `_field_confidence`, `_spec_citation_confidence`, `_cached`, `_cache_source`, `_evidence_limited`, the meta keys) kept as the same objects; never mutates its input |
| consensus_states_no_data | (text) -> bool | PURE: a str whose `" ".join(text.lower().split())` contains one of REVIEW_NO_DATA_PHRASES |
| review_no_data | (reviews) -> bool | PURE: False for a non-dict; True when `reviews.get("has_review_data") is False`; else, with `summary = reviews.get("review_summary")` a dict, True when its `highlights` is not a non-empty list AND `consensus_states_no_data(summary.get("consensus"))`; else False (an error dict has no summary: False) |
| honest_review_view | (reviews) -> same type | PURE: a non-dict as is; a dict -> a NEW shallow copy whose `review_summary` (when a dict) is a NEW dict `{**summary, "consensus": "", "highlights": []}` and whose keys of REVIEW_TEXT_LIST_KEYS that are PRESENT are []; no key added; every other key kept (average_rating, total_reviews, has_review_data, source_ratings, verified_rating, youtube_review_signal, `_cached`) |
| wire_specs | (specs) | GATED: OFF -> `specs` itself (the same object); ON -> honest_spec_view(specs) |
| wire_reviews | (reviews) | GATED: OFF -> `reviews` itself; ON -> honest_review_view(reviews) when review_no_data(reviews), else `reviews` itself |
| wire_views | (product_data) -> None or list | GATED: OFF -> None; ON -> `[(honest_spec_view(pd.get("specs")), <the ON value of wire_reviews>(pd.get("reviews"))) ...]` for each dict pd (a non-dict pd -> (None, None)), one entry per product, in order; a missing key gives None and is never written back as a key (S19) |
| filter_citation_map | (cached_map, raw_specs) | GATED: OFF -> `cached_map` itself; ON -> `{k: v for k, v in cached_map.items() if not spec_value_is_empty(raw_specs.get(k))}` (a key with no value in the current dict is dropped) |
| skip_specs_cache | (specs) -> bool | GATED: OFF -> False (reads nothing else); ON -> `isinstance(specs, dict) and spec_real_field_count(specs) == 0` |
| skip_reviews_cache | (reviews) -> bool | GATED: OFF -> False; ON -> review_no_data(reviews) |
| praise_blocked | (reviews) -> bool | GATED: OFF -> False; ON -> review_no_data(reviews) |
| consensus_blocked | (text) -> bool | GATED: OFF -> False; ON -> consensus_states_no_data(text) |
| served_from_cache | (specs) -> bool | GATED: OFF -> False; ON -> `isinstance(specs, dict) and specs.get("_cached") is True` |
| log_product | (slot, result, served) -> None | GATED: OFF -> returns at once (no log, nothing read); ON -> ONE `logger.info("[HONEST_EMPTY] product=%d specs_real=%d specs_dropped=%d reviews=%s cached=%s", ...)` with product = slot when it is an int 0 / 1 else -1; specs_real / specs_dropped = spec_real_field_count / spec_empty_field_count of `result["specs"]`; reviews = "data" when `result["reviews"]` is a dict without "error" and not review_no_data, else "no_data"; cached = "yes" when `served`, else "no" |

Every function is total: any JSON-like input (None, a list, a bool, NaN, a str where a dict is expected, a short list) returns a value, never raises (the fuzz row R16). No try/except, no import-time env read, no module state.

### 2.3 The edited sites (each call goes through the module attribute `_honest_empty.<fn>`, imported as `from app.services import honest_empty as _honest_empty`, the ES:33 / RB:25 form)

| # | File:site | Change | Flag OFF |
|---|---|---|---|
| S1 | FC verify_spec_citations FC:204-263 | first statement `_h1 = _honest_empty.honest_empty_enabled()`; after the skip at FC:213-215: `if _h1 and _honest_empty.spec_value_is_empty(value): continue` | today's loop (one env read) |
| S2 | SCS `_resolve_citation_confidence` SCS:456-459 | the cached-map return becomes `return _honest_empty.filter_citation_map(cached_map, raw_specs)` | returns `cached_map` itself (`is`) |
| S3 | SCS SSE specs frame SCS:5408 | `"specs": _honest_empty.wire_specs(pd.get("specs")),` | the same object |
| S4 | SCS SSE reviews frame SCS:5466-5497 | the two `(pd.get("reviews") or {})` reads (SCS:5482, SCS:5489) read `_honest_empty.wire_reviews(pd.get("reviews"))` once per product | the same object |
| S5 | SCS `_fetch_product_data`, before `_clean_specs` SCS:6457 | `_h1_served = _honest_empty.served_from_cache(result.get("specs"))` | False, the dict not read |
| S6 | SCS enriched re-cache SCS:6675 | `if _enriched and not _enriched.get("error") and not _honest_empty.skip_specs_cache(_enriched):` | today's condition (W3) |
| S7 | SCS `_fetch_product_data`, before `return result` SCS:6829 | `_honest_empty.log_product(partial_slot, result, _h1_served)` | returns at once |
| S8 | SCS `_get_specs` L2 promotion SCS:6847 | `if not _honest_empty.skip_specs_cache(db_specs):` around the `_cache_set_async` call; the `_cached` / `_cache_source` stamps and the return unchanged (W1) | the call runs as today |
| S9 | SCS `_get_specs` write SCS:6913 | `and not _honest_empty.skip_specs_cache(specs)` as the LAST conjunct (W2) | today's conjuncts, then False |
| S10 | RV build_review_praise RV:566 | after the summary type check: `if _honest_empty.praise_blocked(reviews): return None` | today |
| S11 | RV consensus fallback RV:643-644 | `if len(consensus) >= 12 and not _has_banned_vocab(consensus) and not _honest_empty.consensus_blocked(consensus): return consensus` | today |
| S12 | RV get_reviews L2 promotion RV:759 | `if not _honest_empty.skip_reviews_cache(db_reviews):` around the existing `set_cached` call (no call added or removed: the 1.9 inventory of four direct calls holds) (W4) | today |
| S13 | RV get_reviews write RV:792 | `and not _honest_empty.skip_reviews_cache(reviews)` as the LAST conjunct; `extraction_persisted` stays False, so W6 / W7 are skipped by today's code (W5) | today |
| S14 | ES after ES:1044 | the derivation: `_H1_SHAPE_ANCHOR = '    "review_summary": {\n'`, `_H1_SHAPE_LINE = '    "has_review_data": true|false,\n'` inserted BEFORE it; `_H1_RULE_ANCHOR = '- DO NOT generate source_ratings -- retailer ratings are injected separately from real data\n'`, `_H1_RULE_LINE` (below) inserted BEFORE it; the helper `_h1_reviews_twin(prompt) -> str` inserts both lines and raises RuntimeError unless each anchor occurs exactly once (at import, the D08 contract); `REVIEWS_EXTRACTION_SYSTEM_HONEST = _h1_reviews_twin(REVIEWS_EXTRACTION_SYSTEM)` and `REVIEWS_EXTRACTION_SYSTEM_NO_RATING_HONEST = _h1_reviews_twin(REVIEWS_EXTRACTION_SYSTEM_NO_RATING)` | the base constants are not edited |
| S15 | ES extract_reviews, after ES:1889 | `if _honest_empty.honest_empty_enabled(): _reviews_system = (REVIEWS_EXTRACTION_SYSTEM_NO_RATING_HONEST if _reviews_system == REVIEWS_EXTRACTION_SYSTEM_NO_RATING else REVIEWS_EXTRACTION_SYSTEM_HONEST)` | the base / NO_RATING string as today (P7) |
| S16 | RB build_comparison_response, between RB:1925 and RB:1927 | `_h1_views = _honest_empty.wire_views(product_data)` | None |
| S17 | RB specs block RB:2004, RB:2015 | `"specs": pd.get("specs") if _h1_views is None else _h1_views[i][0]`; `"rows": _build_specs_rows(product_data if _h1_views is None else [{"specs": v[0]} for v in _h1_views])` | today |
| S18 | RB reviews block RB:2019-2068 | the comprehension iterates `product_data` when `_h1_views is None`, else `[{**p, "reviews": v[1]} for p, v in zip(product_data, _h1_views)]` (shallow copies, never a mutation), so review_summary, retailer_quotes, review_praise and the YouTube signal of the block read the view | today |
| S19 | RB the alias loop RB:2227-2267 | at the top of each iteration, when `_h1_views is not None`: rebind `pd["specs"]` to `_h1_views[i][0]` and `pd["reviews"]` to `_h1_views[i][1]`, each ONLY when that key is already present (no key is ever added), BEFORE `pd["review_praise"]` (RB:2242), so the alias, `category_profile` and the B1 stamp (RB:2315-2335) read the views | today |

`_H1_RULE_LINE` (ASCII, one line): `- has_review_data: true ONLY when the search results contain reviewer opinions or ratings for this exact product (the same brand, line and concentration); otherwise false, and then consensus is "" and highlights is [].` + "\n". Measured on the base constants by AST evaluation (tools/prompt_anchors.py): both anchors occur exactly once in REVIEWS_EXTRACTION_SYSTEM and in REVIEWS_EXTRACTION_SYSTEM_NO_RATING; "has_review_data" occurs 0 times; the guard sentence once; the twins are 3618 / 3533 chars with sha256 9bd925488019919bdc764948fbb42d56e3afca1ed09e183cce1bc57ebe1fb473 / 30fb98d183a67f3377748e94e4fd5bef13481329b694a85751b1838555a66a09 (the RED writes them base64).

Order inside RB: S16 runs before the literal; S17 / S18 are inside the literal BEFORE `"scoring_v2": _build_scoring_v2(...)` (RB:2079) but read only the views, never `pd["specs"]`; S19 rebinds after the literal. So `_build_scoring_v2` (captions, dims, factual verdict, confidence legs) reads exactly today's `product_data` (H1-1: the bars and templates are unchanged).

### 2.4 The wire table (flag ON; every other state: today's bytes)

| Path | Today (the incident shape) | Flag ON | Type |
|---|---|---|---|
| specs.products[i].specs | 11 keys "N/A" | {} (or only the real keys); `_`-keys kept | dict |
| products[i].specs (alias) | the same object | the same view | dict |
| specs.specs_comparison.rows | 11 rows "N/A" vs "N/A", winner None | rows only where both values are real | list |
| SSE `specs` frame products[i].specs | the stamped dict | the view | dict |
| products[i].fact_check / overview.confidence / scoring_v2.confidence_legs.specs | specs_unverified 11 / citations 11 / "strong" | 0 / 0 / "weak" | ints / enum |
| scoring_v2.dimensions | core 3 + versatility (40 vs 30, "More versatile", medium) | core 3 (both sides empty) | list, >= 3 rows |
| scoring_v2.factual_verdict.line1 | "<A> leads on Versatility." | "<A> edges ahead on the overall picture." (no price / rating candidate) | str |
| products[i].review_praise, reviews.products[i].review_praise (the no-data product) | the model's no-data sentence | null | str or null |
| reviews.products[i].review_summary (no-data) | consensus = the sentence, highlights as returned | consensus "", highlights []; overall_sentiment / review_volume / agreement_level kept | dict |
| reviews.products[i].retailer_quotes (no-data) | as built | [] | list |
| products[i].reviews (alias, no-data) | the dict | the view: + common_praises / common_complaints / retailer_quotes / review_source_quotes [] when present | dict |
| products[i].reviews.has_review_data | absent | the model's bool (additive) | bool |
| SSE `reviews` frame (no-data) | consensus, quotes | consensus "", highlights [], retailer_quotes [] | dict |
| a product with real values only, a data reviews dict | today | byte-identical (P3) | |

### 2.5 The flag-mix walk (Q3; values from the formulas of 1.2; the RED round pins each cell)

Fixtures (synthetic names; section 5): E = two fragrance products, each with the 11 schema fields "N/A" and no `_source` (the raw flag-OFF extract of an all-null reply), p0 `price_verified` True, p1 False, sentiment None, no ratings (the incident shape, 40 vs 30); E' = E with both `price_verified` False (a 30 / 30 tie); P = p0 with 4 real values cited by snippets that verify (scent_family, notes_top, concentration, longevity) + 7 "N/A", p1 as E's p1; F = real values only on both sides (p0 4 verified, p1 3 verified). W / U / R / N / C / T as in 1.7; ENABLE_BUNDLE_C_SCORING false (production).

| Fixture | Mix | H OFF (today) | H ON |
|---|---|---|---|
| E | W0, (R,U) not (1,1), N any | Specs leg strong (High: citations 11); reliability 0.4 / 0.3 -> versatility 40.0 vs 30.0, "More versatile", medium, winner 0; line1 "<A> leads on Versatility." | Specs weak (Low); reliability None / None -> no versatility row (both missing, SS:3569-3571); line1 "<A> edges ahead on the overall picture." |
| E | W0, R1 U1 | Specs strong; reliability None / None (all-unverified absence, SS:2093) -> no row | Specs weak; no row |
| E | W1 (C1), any R / U / N | Specs weak (citations v + l = 0); the reliability cells as the W0 rows | Specs weak; no row |
| E' | W0 R0 T1 (T is effective only with R OFF) | 30.0 / 30.0 on dense evidence (total 11 >= 3, not sparse, SS:508-516) -> the tie is KEPT (SS:2251-2258): a versatility row 30 vs 30 "Comparable" | no row (total 0) |
| E' | T0 (production) | the tie collapses to MISSING (SS:2259-2268): no row | no row |
| P | W0, (R,U) not (1,1) | Specs strong (11 citations); reliability p0 (4 + 7 x 0.3) / 11 = 0.5545 -> 55.5, p1 30.0 -> row 55.5 vs 30.0, winner 0, line1 "<A> leads on Versatility." | Specs strong (pct 4 / 4 = 100); p0 1.0 -> 100.0, p1 None -> the one-side row 100.0 vs 50 (MISSING_SCORE), winner None (was_missing), line1 still "<A> leads on Versatility." (L-ONESIDE, INC-X6) |
| P | W0, R1 U1 | p1 absence -> row 55.5 vs 50, winner None, excluded from the overall (renorm) | row 100.0 vs 50, winner None, excluded from the overall |
| P | W1 (C1) | Specs ACCEPTABLE (Medium: citations 4, pct 36) | Specs STRONG (High: pct 100 over the real fields) - the denominator effect, L-CHIP-THIN / O6 |
| F | every mix | today | equal to today (PIN P6) |
| E-fresh (the extract grain: a fake all-null model reply) | N0 | the sheet is 11 "N/A", WRITTEN (W2) | the same sheet returned, NOT written |
| E-fresh | N1 | the sheet has no field (+ `_evidence_limited`), WRITTEN (W2) | NOT written (skip_specs_cache: no real field) |

Reading the table: H turns every "from empty fields" cell into absence (the chip, the reliability, the row, the line) in every reachable mix, and changes nothing for real-only data. Two cells move a REAL-data outcome: P under W1 (Medium -> High, the verified share now counts real fields only) and P everywhere (the one-side row reads 100 vs the default 50 instead of 55.5 vs 30). Both are stated (L-CHIP-THIN, L-ONESIDE) and pinned. N does not change the fact-check grain (it acts at extract time); under N ON H still stops the empty-sheet write.

Interplays outside the brief's four (both OFF on web, pinned by R23, stated): ENABLE_RESULT_STATUS_METADATA reads the body after S19 (RB:2315-2335): the E body loses its dims fact (the 40 vs 30 row was discriminating) and the no-data product's reviews stop counting as present (`_reviews_present` reads a non-empty consensus, RG:432-438), so `section_status` and `data_coverage` fall; with ENABLE_RESULT_GATE also ON a thin pair can be refused with INSUFFICIENT_DATA instead of served (L-RG). On the OTA bundle `section_status.specs` / `.reviews` "unavailable" draws the D20 honest line (RA:551-552, RC:647-664).

### 2.6 The visible delta with the flag ON, per live bundle (code reading; not measured on a device)

| Element | Store 683f56c0 and OTA (main) |
|---|---|
| Specs section, no real value on either side | the bare "dimensions" header; the expanded table holds only the two names (no dash rows) - both bundles (RA:248-256 / RA:288-297); the OTA adds the D20 line only under ENABLE_RESULT_STATUS_METADATA (OFF) |
| Specs section, some real values | unchanged: the same rows and the same "<n> dimensions" (the rich path never used the NA keys) |
| Specs chip | Low instead of High when no product has a real field (W OFF, production) |
| Bars | no Versatility bar when both products have no real field; one side empty: the bar stays with 50 on the empty side (L-ONESIDE) |
| Verdict line1 | no "leads on Versatility" from empty fields; "edges ahead on the overall picture" instead (L-VERDICT-TEXT) |
| Reviews section | no praise for the no-data product; when neither product has praise or a rating > 0, "Reviews are still coming in." (RA:457-463 / :418); the header still sums counts and says "across both" (INC-C1) |
| Captions, pros / cons, prices, the crown display | unchanged (the crown can move only through the removed reliability gap: L-CROWN) |
| Home caption | unchanged in production (ENABLE_SMART_PICK_VERDICT_CAPTION unset; home_routes.py:362 defaults OFF) |

### 2.7 Failure table

| Input | Outcome (flag ON) |
|---|---|
| specs None / a list / a str / an int | the views return it as is; counts 0; S9 is never reached for a non-dict (extract_specs always returns a dict) |
| a value NaN | empty; 0, 0.0, False, "0", "No" -> real |
| a list of empty tokens / [] | empty; a list with one real element -> real (`_clean_specs` joins lists, so the wire rarely carries one) |
| a dict value {} | empty; a non-empty dict -> real (not judged) |
| "Not specified", "n.a.", "--" | REAL (not in the measured set; O2) |
| reviews None / a str / an error dict / no review_summary | review_no_data False; the view is not applied; praise by today's code (an error dict has no summary: praise None today) |
| has_review_data "false" (a str) or 0 | not `is False`: the phrase guard decides (L-HRD-STRING) |
| a cached #107 map with keys absent from the current dict | those keys dropped |
| a moved prompt anchor (a future edit of the base constant) | RuntimeError at import, the D08 contract (R12 sub-row) |
| an exception in HE | cannot happen by construction (total functions, R16); no new try / except and no new ERROR log |

### 2.8 Flag-OFF identity (the main invariant) and the deploy-visible delta

With ENABLE_HONEST_EMPTY unset, "false", "0", "off", "no" or padded garbage: every byte of every response body (sync, the stream `specs` / `reviews` / `scores` / `verdict` / `complete` frames, the hard-cap partial), every saved comparisons row, every L1 / L2 write (count, key, payload), the reviews system prompt (P7 sha), the verdict prompt, `products[i].fact_check`, `scoring_v2` and the log equal the base, for every category. The deploy with every flag at its default changes NO response byte, NO stored row, NO cache write, NO prompt byte and NO log line in production; the only change is the source and the CLAUDE.md text (section 8). With the flag ON, a product whose spec values are all real and whose reviews are data is byte-identical to OFF (P3). Pinned by P1 and P3-P6 (and the recorder row R24) with the FULL configuration (1.8, every listed name set, the knobs at valid non-defaults) AND the production set of record (1.7: the ON names of the ledger line 316 and H12(c) set true, ENABLE_BUNDLE_C_SCORING false, every other name unset), each with call recorders (X6-R12).

### 2.9 Test seams (production values in brackets)

`honest_empty.honest_empty_enabled` [the env read]; recorders on `honest_empty.spec_value_is_empty`, `review_no_data`, `honest_spec_view`, `honest_review_view`, `spec_real_field_count`, `consensus_states_no_data` [0 calls OFF, R24]; `HONEST_NA_TOKENS`, `REVIEW_NO_DATA_PHRASES`, `REVIEW_TEXT_LIST_KEYS` [2.1]; `extraction_service.REVIEWS_EXTRACTION_SYSTEM_HONEST` / `_NO_RATING_HONEST` [the twins]; `extraction_service.get_client` [a fake client capturing `messages`]; `structured_comparison_service._cache_set_async`, `product_data_service.save_specs` / `get_cached_specs` [recorders / fakes]; `review_service.set_cached`, `get_cached`, `save_reviews`, `run_redis_offloop_pool`, `product_data_service.get_cached_reviews` [recorders / fakes]; `honest_empty.logger` [caplog at INFO]; the `_install` leaves of tests/test_s75_fanout_identity.py:101-197 and `_install_real` of tests/test_s78_all_timeout_cap_as_timeout.py (eval_regression finding 1) for the orchestrator rows.

### 2.10 Logs and events

One INFO line per product per request under the flag only, from `_fetch_product_data` (S7): `[HONEST_EMPTY] product=<0|1|-1> specs_real=<int> specs_dropped=<int> reviews=<data|no_data> cached=<yes|no>` (constants and ints only: no product name, no value, no URL). `specs_dropped` = the field keys the wire view drops for that product; `cached=yes` = the product's spec sheet was served from L1 or L2 in this request (the `_cached` mark read BEFORE `_clean_specs` strips it, S5). The three cases of ADV R-4 read off the line: (i) the specs race timed out or errored: specs_real=0 specs_dropped=0 cached=no; (ii) an all-empty sheet from the cache: specs_real=0 specs_dropped>0 cached=yes; (iii) a fresh all-empty reply: specs_real=0 specs_dropped>0 cached=no. No Sentry event (INFO), no metadata key, no ERROR line. A product whose fetch the hard cap cancels writes no line (L-PARTIAL-LOG).

## 3. Change list (in the order GREEN applies it)

0. Byte copies (shutil.copyfile + sha256) of ES, SCS, FC, RV, RB and CLAUDE.md into <SP>/INC-H1/green/bytes/ before the first edit; sha-checked after any restore.
1. NEW app/services/honest_empty.py (2.1, 2.2): ASCII, LF in the index; HONEST_NA_TOKENS built with chr(0x2014); module docstring naming the unit, the flag, the read rule and the four surfaces.
2. FC: the import (after FC:8) and S1.
3. ES: the import (in the ES:29-37 block), S14 (after ES:1044), S15 (after ES:1889). No edit of ES:1584-1747 or of any LLMUnavailableError arm.
4. RV: the import (in the RV:15-40 block), S10, S11, S12, S13.
5. SCS: the import (beside SCS:1569-1576), S2, S3, S4, S5, S6, S7, S8, S9.
6. RB: the import (in the RB:19-29 block), S16, S17, S18, S19.
7. CLAUDE.md: the block of section 8 after the S81-07c block (CLAUDE.md:675-682) and before `## Tests` (CLAUDE.md:684), one blank line before its heading; the pointer sentence INSIDE the one `**Feature Flags:**` line (CLAUDE.md:341) right after the S81-07c sentence (or after the newest lane block / sentence in merge order at the final round).
8. New tests/test_inc_h1_honest_empty.py and tests/test_inc_h1_body_pins.py (the RED round; frozen at the gate).

No other file. No client file, no migration, no requirements file, no processors.json, no .github file, no `_clean_specs` / extract_specs / scoring_service / result_gate / url_extraction_service edit, no edit of any S81-04c log arm.

## 4. Existing pins (Q6)

### 4.1 Pins that change deliberately

None. No existing test sets ENABLE_HONEST_EMPTY (a new name, 0 hits); every edit is gated by a flag whose OFF path is today's code; the base reviews constants are not edited; no signature changes (no new parameter anywhere: H1 adds statements, not arguments). Any red existing node at GREEN is a defect, not an E-row. Optional E1 for the orchestrator (O4): add the two twins to the reviews guard loop of tests/test_prompt_fence.py:278-287 (the D08 E2 precedent); the spec's default is no E-row (the RED file asserts the guard sentence in the twins itself, R12).

### 4.2 Pins that must stay green and unedited

- Fact-check and confidence: tests/test_fact_checking.py, test_decomposed_services.py, test_fact_check_service_v2.py, test_m18_factcheck_honest.py, test_spec_confidence_cache.py (verify_spec_citations, `_resolve_citation_confidence`, the #107 carry, `_build_specs_rows`, save_specs), test_confidence_thresholds.py, test_scoring_v2_confidence.py, test_w4_7_reliability_unchecked_absence.py, test_w4_7_confidence_single_computation.py, test_w4_7_factcheck_shopping_key.py, test_dim_phantom_tie_followup.py, test_scoring_service.py, test_scoring_rubric_truth.py with its digest fixtures (tests/fixtures/rubric_truth_flag_*), tests/fixtures/missing_dim_renorm_flag_off_golden.json and behavioral_flag_off_golden.json readers.
- Specs: tests/test_specs_no_fabrication_guard.py (incl. :129 `test_flag_off_still_stamps_na_and_keeps_training_values` and :317-332 the `_build_specs_rows` row), test_specs_refill_no_fabrication.py, test_subtype_spec_reconciliation.py, test_extraction_prompt.py, test_smart_fallback.py, test_lane1_helpers_unit.py, test_s80_b1.py, test_s78_tier_fill_residual_guard.py, test_unified_search.py, test_product_data_service.py, test_fire_and_forget_wrap.py, test_be_harness.py.
- Reviews: tests/test_review_paraphrase.py, test_fragrance_content_quality.py, test_w4_12_display_contract.py (build_review_praise / `_safe_review_praise`), test_m13_33_review_fire_and_forget.py, test_s77_redis_offloop.py (the S6 promotion row :1172-1196), test_s81_st1_usage_path_offloop.py (incl. the :1996-2018 AST inventory), test_youtube_reviews_race.py, test_review_source_consult.py, test_review_prompt_quality.py, test_cost_tracking.py, test_m18_offload_sweep_residual.py (:530-538).
- Prompts: tests/test_s81_d08_jsonld_widen.py (P7 :1147-1158, R18 :836-850, R19), test_prompt_fence.py (:272-287, :325-332), test_prompt_injection.py (:113-117), test_prompt_truth.py with tests/w4_11_prompt_digest_recorder.py (they digest the specs / targeted / verdict prompts, never the reviews prompt: no digest moves), test_model_config.py, test_model_config_enforced.py (H1 adds no LLM dispatch site).
- Bodies and streams: tests/test_streaming.py, test_s75_fanout_identity.py (FY25), tests/fixtures/s81_g8_flag_off_golden.json and s81_s18_flag_off_golden.json readers (test_s81_g8_gate_rows / test_s81_s18_kb_first_serve and kin), test_s81_s04c_refusal_log_hygiene.py, test_inc_x8_phase2_cached_rating.py, test_inc_x9_cohort_line_retire.py, test_s81_s20_result_gate.py and every importer in the comm set.
- The source-scanning pins of every backend comm set (common brief): test_model_config.py, test_model_config_enforced.py, test_prompt_fence.py, test_u3c_store_false_pin.py, test_start_command*.py, test_migration_index_predicate_immutability.py, test_openai_key_log_hygiene_s69.py, test_sentry_channels_u8d_unit.py; and the readers of an edited file by path (59 files, closure.json set C; e.g. test_m21_brand_dedup_and_verdict_copy.py:118-165, test_genuine_price_clobber_guard.py:1190-1225, test_diagnostics_flag_gated.py:165).
- The CLAUDE.md readers by the import graph (109 files, closure.json set E; among them test_ci_gates.py, test_behavior_dimension_translation.py, test_s81_s04_spend_breaker.py, test_s81_s08b_legacy_fingerprint.py with :820-822 the one Feature Flags line, test_s81_s08b_gate_rows.py, test_s81_s23_bypass_retire.py).

## 5. RED tests (hermetic; no network, no LLM, no database)

Rules for both files (eval_regression finding 1; RULINGS_INC_X6 X6-R1, X6-R2, X6-R12): pure ASCII, LF; import app.main FIRST in an autouse fixture (the dotenv guard), then delenv ENABLE_HONEST_EMPTY and every walk flag (the UNIT_ENV pattern), then monkeypatch; the W4-3 `_no_network` teardown assertion; new symbols read through `_sym(module, name)` (`importlib.util.find_spec("app.services.honest_empty")` asserted not None, then getattr asserted callable), so a missing symbol at the base is an AssertionError, never an ImportError or AttributeError; every RED row asserts its base precondition FIRST (the OFF behaviour it changes), so the row fails at base on the ON assertion; base literals recorded at the base in the RED round and written as base64 sha256 of the canonical JSON (sort_keys, ensure_ascii) under names without scanner keywords (`_BASE_BODY_SHA_B64`); product names synthetic ("Brand A Line One", "Brand B Line Two"). FULL_CONFIG and PROD_SET as in 2.8; ENABLE_BUNDLE_C_SCORING's process cache reset like the digest generator (`scoring_service._BUNDLE_C_SCORING_FLAG`).

Fixtures: SPEC_E(name) = {"brand": "", "model": name, "variant": None, "category": "fragrances"} + the 11 ES:213-227 fields "N/A" (the raw flag-OFF extract of an all-null reply, ES:1679-1707); SPEC_E_CLEAN = the 11 fields "N/A" (the `_clean_specs` output); SPEC_T04 = {"connectivity": "-", "frequency_response": "N/A", "polar_pattern": None} (eval_regression finding 9, the V10 all-dash dict, electronics); SPEC_P0 = 4 real values with `<field>_source` "snippet_1".."snippet_4" + 7 "N/A", SNIPPETS_P0 = four snippet strings containing those values (each grades "verified" under the legacy rubric FC:250-255); SPEC_F0 / SPEC_F1 = real values only; D2F = the two products of tests/fixtures/comparison_baseline_d2_post_bucket_a__fragrances.json (a recorded pair: p0 scent_family / sillage / season / occasion "N/A", p1 notes_top / notes_heart / notes_base / season "N/A"); REV_NODATA = `_normalize_review_response` of {"average_rating": None, "total_reviews": None, "review_summary": {"overall_sentiment": "mixed", "consensus": "No review data was available in the provided search results for this product.", "highlights": [], "review_volume": "minimal", "agreement_level": "moderate"}}; REV_FALSE = a dict with has_review_data False and one positive cited highlight; REV_NEGONLY = one negative highlight + the no-data consensus; REV_DATA = two positive cited highlights and a real consensus.

File tests/test_inc_h1_honest_empty.py (unit grain):

| # | Test | Assertion | At base | Satisfied by |
|---|---|---|---|---|
| R1 | test_r1_flag_reader_per_call | "true", "1", "yes", "on", " TRUE ", "On" -> True; unset, "", "false", "0", "off", "no", "2", "tru", " " -> False; set then unset in one test flips the answer (no cache) | RED (module missing -> assert fails) | 2.1 |
| R2 | test_r2_empty_value_table | spec_value_is_empty: None, "", "  ", "N/A", " n/a ", "NA", "na", "None", "none", "Unknown", "-", " - ", "null", "NULL", chr(0x2014), "string or null", [], [None, "N/A"], {}, float("nan") -> True; "EDP", "8 hours", "8", 8, 0, 0.0, True, False, ["Bergamot"], {"a": 1}, "Not specified", "--", "n.a." -> False | RED | 2.2, O2 |
| R3 | test_r3_spec_view | honest_spec_view(SPEC_E) is a NEW dict == the four meta keys only; on SPEC_P0 drops the 7 "N/A" keys and no `_source` of a kept key, keeps the 4 real values (`is` the same objects) in order; a dict with `_field_confidence` / `_cached` keeps them; `x_source` of a dropped `x` is dropped; the input deep-equals its copy afterwards; None / a list / a str returned as is (`is`); SPEC_T04 -> {} | RED | 2.2 |
| R4 | test_r4_field_counts | spec_real_field_count / spec_empty_field_count: SPEC_E 0 / 11; SPEC_E_CLEAN 0 / 11; SPEC_T04 0 / 3; SPEC_P0 4 / 7; D2F p0 6 / 4 and p1 6 / 4; meta-only 0 / 0; `_`-keys and `_source` keys never counted; a non-dict 0 / 0 | RED | 2.2 |
| R5 | test_r5_review_no_data | True: has_review_data False (even with highlights); each phrase of REVIEW_NO_DATA_PHRASES in upper / mixed case and with doubled spaces when highlights is [] or missing; has_review_data True + no highlights + a phrase. False: a phrase with a non-empty highlights list; no phrase and no highlights; an error dict; None; a str; a consensus that is not a str | RED | 2.2 |
| R6 | test_r6_review_view | honest_review_view(REV_FALSE + the four lists): a NEW dict; review_summary a NEW dict with consensus "" and highlights [] and the other summary keys kept; the four lists [] ONLY when present (a dict without retailer_quotes gains no key); has_review_data, average_rating, source_ratings, youtube_review_signal, `_cached` kept (`is`); the input unchanged | RED | 2.2 |
| R7 | test_r7_verify_skips_empty | precondition OFF: verify_spec_citations(SPEC_E, []) == 11 x "unverified". ON: == {}; a literal "N/A" with source "snippet_1" (OFF "likely") is absent ON; "unknown" with a snippet source absent; SPEC_P0 + SNIPPETS_P0 -> exactly the 4 real keys, each "verified"; SPEC_T04 -> {} | RED | S1 |
| R8 | test_r8_cached_map_filtered | ENABLE_SPEC_CONFIDENCE_CACHE ON: precondition OFF: `_resolve_citation_confidence(SPEC_E + {"_spec_citation_confidence": 11 x "unverified"}, [])` `is` that map. ON: == {}; a mixed map {real: "verified", na_key: "unverified", absent_key: "likely"} -> {real: "verified"}; ENABLE_SPEC_CONFIDENCE_CACHE OFF + ON -> the verify path (== R7's ON value) | RED | S2 |
| R9 | test_r9_specs_leg | the chain verify_spec_citations -> `_spec_confidence` -> build_fact_check -> compute_confidence over the E pair: precondition OFF + W OFF: legs.specs "strong" and citation_count 11. ON: "weak" with W OFF and with W ON (+C ON); `products[i].fact_check` specs_* all 0 | RED | S1, 2.5 |
| R10 | test_r10_no_reliability_proxy | E pair, fragrances, the real ScoringService: precondition OFF: `_score_reliability` 0.4 / 0.3, a "versatility" dim 40.0 vs 30.0, line1 "Brand A Line One leads on Versatility.". ON: `_score_reliability` None / None; "versatility_score" in both products' missing_data; build_dimensions_v2 has no "versatility" key; `_build_factual_verdict` line1 contains no "Versatility" and == "<winner name> edges ahead on the overall picture." | RED | S1, 2.5 |
| R11 | test_r11_praise | precondition OFF: build_review_praise(REV_NODATA) == the consensus sentence. ON: REV_NODATA -> None; REV_FALSE -> None; REV_NEGONLY -> None (S11: the consensus fallback refuses a no-data sentence); REV_DATA -> == the OFF output computed in the same test | RED | S10, S11 |
| R12 | test_r12_prompt_twins | REVIEWS_EXTRACTION_SYSTEM_HONEST / _NO_RATING_HONEST exist (str); each == its base with exactly the two insertions of S14 (anchor counts 1 / 1 in the base, rebuilt in the test with the literal lines); each contains SEARCH_RESULTS_GUARD (the test_prompt_fence `_search_guard_sentence` rule) and "has_review_data" exactly once, and no "{brand}" / "{name}"; base sha256 == the P7 value; the twins' sha256 == the 2.3 values (base64 in the file); a fake get_client capturing messages: ON + ENABLE_JSONLD_RATING OFF -> the HONEST string sent, ON + ENABLE_JSONLD_RATING ON -> the NO_RATING_HONEST string; the derivation helper raises RuntimeError on a prompt without the anchor | RED | S14, S15 |
| R13 | test_r13_reviews_not_cached | get_reviews with fakes (extract_reviews, search_web, get_cached / get_cached_reviews, set_cached, save_reviews, run_redis_offloop_pool recorders), for ENABLE_USAGE_PATH_OFFLOOP OFF and ON: precondition OFF: REV_NODATA extraction -> one L1 write + one save_reviews. ON: REV_NODATA -> 0 L1 writes and 0 save_reviews for the key, no consult / YouTube re-cache, the returned dict == the extraction; an L2 hit returning REV_NODATA -> 0 promotion writes and the dict returned; REV_DATA -> 1 + 1 as today | RED | S12, S13 |
| R14 | test_r14_specs_not_cached | `_get_specs` with a fake extract_specs and recorders on `_cache_set_async` / save_specs / get_cached_specs: precondition OFF: SPEC_E -> 1 L1 write + 1 save_specs. ON: SPEC_E -> 0 + 0, the dict returned with `_search_snippets` / `_cached` False as today; one real field -> 1 + 1; an L2 hit returning SPEC_E -> 0 promotion writes, `_cached` True and `_cache_source` "db" kept; skip_specs_cache({"longevity": "unknown"}) True and skip_specs_cache(SPEC_P0) False ON, both False OFF | RED | S8, S9, S6 |
| R15 | test_r15_log_line | caplog INFO on `app.services.honest_empty`, `_fetch_product_data` with `_install_real`-style leaves (tests/test_s78_all_timeout_cap_as_timeout.py), partial_slot 0: ON + a fresh SPEC_E + REV_NODATA -> exactly one record "[HONEST_EMPTY] product=0 specs_real=0 specs_dropped=11 reviews=no_data cached=no"; the leaf returning SPEC_E with `_cached` True -> "cached=yes"; specs leaf timed out (None) -> "specs_real=0 specs_dropped=0"; REV_DATA -> "reviews=data"; the line contains neither product name; OFF -> no record | RED | S5, S7, 2.10 |
| R16 | test_r16_total | 300 seeded random JSON-like shapes (None, bools, NaN, inf, str, lists, nested dicts, short lists of products) into every HE function ON and OFF: no exception; views never add a key; counts are non-negative ints; wire_views length == the input length | RED (module missing) | 2.2, 2.7 |

File tests/test_inc_h1_body_pins.py (body grain, wiring, identity):

| # | Test | Assertion | At base | Satisfied by |
|---|---|---|---|---|
| R17 | test_r17_body_specs | build_comparison_response over the E pair (cleaned specs, fact_check from R9's chain, a hand-built scoring_result from the real ScoringService): precondition OFF: 11 "N/A" keys in specs.products[0].specs and 11 rows. ON: specs.products[i].specs and products[i].specs carry no field key with an empty value (`_`-keys allowed); specs_comparison.rows == []; `scoring_v2` deep-equals the OFF build's `scoring_v2` for the same inputs (captions, dims and lines untouched by the views) | RED | S16, S17, S19 |
| R18 | test_r18_body_reviews | product 0 REV_DATA, product 1 REV_NODATA: precondition OFF: products[1].review_praise == the sentence. ON: products[1].review_praise is None; reviews.products[1].review_praise is None; reviews.products[1].review_summary consensus "" and highlights []; reviews.products[1].retailer_quotes == []; products[1].reviews.review_summary.consensus == ""; product 0's review entries deep-equal the OFF body's | RED | S16, S18, S19, S10 |
| R19 | test_r19_d2f_real_values_kept | D2F: ON drops exactly p0 scent_family / sillage / season / occasion and p1 notes_top / notes_heart / notes_base / season from both specs projections; every real key and value unchanged (`==` the OFF body's value); rows == the OFF rows restricted to fields both sides fill (longevity, volume, concentration) with the same winners; the client's rich-key union and its count, computed with a pure re-implementation of RA:86-107 + RA:198-223, are equal OFF and ON (9) | RED | S17, 1.5 |
| R20 | test_r20_orchestrator_sync_and_stream | `_install` leaves (tests/test_s75_fanout_identity.py:101-197 pattern): `_get_specs` returns SPEC_E for both, `_get_reviews` returns REV_NODATA for product 1; sync and stream: precondition OFF: confidence_legs.specs "strong" and a "versatility" dim. ON: legs.specs "weak"; no "versatility" dim; line1 contains no "Versatility"; the SSE `specs` frame carries no empty field; the SSE `reviews` frame's product 1 consensus "" and retailer_quotes []; `complete` == the sync body's specs / reviews projections; exactly two [HONEST_EMPTY] records (product=0, product=1) | RED | S1-S9, S16-S19 |
| R21 | test_r21_wiring_ast | ast over the edited files: FC verify_spec_citations' first statement calls `_honest_empty.honest_empty_enabled`; SCS `_get_specs` W1 / W2 and the W3 site test `_honest_empty.skip_specs_cache`; RV get_reviews W4 / W5 test `_honest_empty.skip_reviews_cache` and still holds exactly four direct `set_cached` calls (1.9); the SSE frames call wire_specs / wire_reviews; RB build_comparison_response assigns `_h1_views` BEFORE the `result = {` assignment and the literal's `scoring_v2` value reads no `_h1_views`; the source segments of the LLMUnavailableError arms of extract_specs and extract_reviews equal the base bytes (sha in the file) | RED | S1-S19 |
| R22 | test_r22_flag_mix_walk | parametrized over the 12 reachable (W, R, U, N) mixes (W1 sets C1) + the E' / T1 case, for E and P with H ON: the H ON cells of 2.5 (legs.specs, reliability per product, the versatility row's presence / scores / winner, line1 contains or lacks "Versatility") AND `products[i].fact_check` counters equal to the real-field grades only (so every case, including the ones whose leg and row read the same OFF and ON such as E under W1 R1 U1, fails at base on the counters); each case asserts its H OFF cell first | RED | 2.5 |
| R23 | test_r23_result_status_interplay | H ON + ENABLE_RESULT_STATUS_METADATA ON over the E pair with REV_NODATA: `metadata.data_coverage` and `section_status.reviews` computed from the ON body vs the OFF body: the dims fact True OFF -> False ON; product 1 reviews present OFF (the consensus) -> absent ON | RED | 2.5 |
| P1 | test_p1_off_identity | ENABLE_HONEST_EMPTY unset / "false" / "0" / "off" / " garbage ", each under FULL_CONFIG and PROD_SET: verify_spec_citations(SPEC_E) == the base literal; `_resolve_citation_confidence` returns the cached map object (`is`); build_review_praise(REV_NODATA) == the sentence; the E-pair and D2F sync bodies, the stream frames (`specs`, `reviews`, `scores`, `verdict`, `complete`) and the hard-cap partial body == the base literals (sha); extract_reviews sends REVIEWS_EXTRACTION_SYSTEM / _NO_RATING (`is`); get_reviews / `_get_specs` write calls == the base; no [HONEST_EMPTY] record | PIN | 2.8 |
| R24 | test_r24_recorders_off | recorders on every pure HE function (2.9): FULL_CONFIG + OFF -> 0 calls across a sync compare, a stream compare, get_reviews, `_get_specs`, build_review_praise and verify_spec_citations; ON -> >= 1 at each site | RED (module missing at base) | 2.2 |
| P3 | test_p3_on_real_identity | H ON vs OFF over SPEC_F0 / SPEC_F1 + REV_DATA both: the sync body, the stream frames and the cache writes are equal (deep / call lists) | PIN | 2.8 |
| P4 | test_p4_prompt_off_bytes | H OFF, ENABLE_JSONLD_RATING OFF / ON: the sent system string `is` REVIEWS_EXTRACTION_SYSTEM / _NO_RATING; the base sha == P7 | PIN | S15 |
| P5 | test_p5_clean_specs_statements | `_clean_specs({"error": "x", "longevity": None, "longevity_source": "snippet_1"})` == {"longevity": "N/A", "_field_confidence": {"longevity": "snippet"}} in BOTH flag states (the X6-R22 statements: the error strip and the confidence lift; H1 does not touch `_clean_specs`) | PIN | 3 |
| P6 | test_p6_walk_real_only | the 12 mixes over F: H ON == H OFF (legs, reliability, dims, lines) | PIN | 2.5 |

Counts: RED rows R1-R24 = 24 (R1-R16 in the first file, R17-R24 in the second); PIN rows P1, P3, P4, P5, P6 = 5 (all green at base). Every PIN runs with FULL_CONFIG (and P1 also with PROD_SET) and at least one recorder or an identity (`is`) check, so a "not gated" mutant is killed (ruling B1); R24 adds the recorder proof that OFF computes nothing (the house B1 recorder rule). Runner (DEFERRED TO RED): `<P> <G> --bound 600 --tag inc-h1-red --log <SP>/INC-H1/red/red.log --cwd <W> -- tests/test_inc_h1_honest_empty.py tests/test_inc_h1_body_pins.py`. At the base the RED rows fail on AssertionError ONLY and the PIN rows (P1, P3-P6) pass; read the log for ImportError / AttributeError / TypeError / fixture errors: each is a RED-file defect.

## 6. Mutation table (GREEN or the adversary; each on a byte copy, one exact-string edit that matches once, the killing rows via the bounded runner with -k and bound 600, restore, sha256 compare; the mutation lock .qa-mutation.lock first)

| # | Mutant | Killed by |
|---|---|---|
| M1 | honest_empty_enabled returns True | P1, R24 |
| M2 | the reader drops .strip() | R1 (" TRUE ") |
| M3 | the reader drops .lower() | R1 ("On") |
| M4 | the reader cached at import | R1 (set / unset flip) |
| M5 | wire_specs builds the view before reading the flag | R24 (recorder on honest_spec_view) |
| M6 | "unknown" removed from HONEST_NA_TOKENS | R2, R7 |
| M7 | "-" removed | R2, R3 (SPEC_T04) |
| M8 | the "or null" substring rule removed | R2 |
| M9 | the em dash removed | R2 |
| M10 | spec_value_is_empty treats 0 / False as empty | R2 |
| M11 | NaN treated as real | R2 |
| M12 | honest_spec_view keeps the `_source` of a dropped key | R3 |
| M13 | honest_spec_view drops `_`-keys | R3, R17 (`_field_confidence`) |
| M14 | honest_spec_view mutates its input | R3 |
| M15 | spec_real_field_count counts meta keys | R4 |
| M16 | the S1 skip removed | R7, R9, R10 |
| M17 | the S1 skip not gated (applies OFF) | P1 |
| M18 | S2 returns the unfiltered map ON | R8 |
| M19 | S2 filters OFF | P1 (`is`) |
| M20 | review_no_data ignores has_review_data | R5, R11 |
| M21 | the phrase guard fires with non-empty highlights | R5 |
| M22 | the phrase guard is case-sensitive | R5 |
| M23 | "provided search results" removed from the phrases | R5 |
| M24 | honest_review_view keeps highlights | R6, R18 |
| M25 | honest_review_view adds absent list keys | R6 |
| M26 | S10 removed | R11 (REV_FALSE: its positive highlight would be woven) |
| M27 | S11 removed | R11 (REV_NEGONLY) |
| M28 | S10 not gated | P1 |
| M29 | S17 uses `pd.get("specs")` for the rows | R17 |
| M30 | S18 not applied (the reviews block reads pd) | R18 |
| M31 | S19 not applied (the alias keeps the stamps) | R17, R18 |
| M32 | S16 rebinds pd["specs"] before the literal (captions move) | R17 (`scoring_v2` equality) |
| M33 | S3 removed | R20 |
| M34 | S4 removed | R20 |
| M35 | S9 removed | R14 |
| M36 | S8 removed | R14 |
| M37 | S6 removed | R14 (the predicate row), R21 |
| M38 | S13 removed | R13 |
| M39 | S12 removed | R13 |
| M40 | skip_specs_cache not gated (skips OFF) | P1, R14 precondition |
| M41 | S15 ignores ENABLE_JSONLD_RATING (always the base twin) | R12 |
| M42 | an anchor inserted after instead of before | R12 |
| M43 | the log counts real fields as dropped | R15 |
| M44 | the log reads `_cached` after `_clean_specs` (always "no") | R15 (cached=yes case) |
| M45 | the log emitted OFF | R15, P1 |
| M46 | the log carries the product name | R15 |

46 mutants; each must be KILLED by an assertion failure (an import or collection error is not a kill). An equivalent survivor is reported for a ruling (expected candidate: M37 is reachable only when a fill writes a token value; R14's predicate row kills it at unit grain and R21 at the wiring grain).

## 7. Comm set and gates for GREEN (cheapest first; every run DEFERRED TO RED / GREEN, none ran in this round)

Comm set by the union rule, computed in this round by <SP>/INC-H1/tools/closure.py over `git cat-file --batch` at the base (output <SP>/INC-H1/spec/closure.json and comm_set.txt, sha256 of the sorted LF list 6d73dae4f2b062321c3100222a008eeb31787d998ffc612a865be4b6bedf4ef4; 30 chunks in comm_chunks.txt, the last of 18):
- the importer closure of the five edited modules to a fixpoint over app/ = 80 modules (app.main among them), then over scripts/ and tests/ helpers (gate-row files, importlib loads, path loads): 730 test files (set A);
- the tests naming a closure module as a dotted string: 101 (A2); naming an edited symbol (verify_spec_citations, `_resolve_citation_confidence`, `_clean_specs`, `_get_specs`, `_build_specs_rows`, build_review_praise, `_safe_review_praise`, get_reviews, extract_reviews, `_normalize_review_response`, REVIEWS_EXTRACTION_SYSTEM, build_comparison_response, `_fetch_product_data`, extract_specs, save_specs, save_reviews, `_strip_transient_spec_keys`, spec_confidence_cache_enabled): 119 (B); naming an edited file by path: 59 (C); the source readers (getsource / ast.parse / glob / rglob / listdir / scandir / walk, or `__file__` / read_text / open with an app path): 155 (D); the CLAUDE.md readers by the import graph: 109 (E); the named pins: 10 (F); the SmartCompareApp-scanning backend tests (the client-visible contract changes: the praise, the specs map, the rows): 29 (G);
- MINUS the four pre-commit hook files (test_precommit_hook.py, _round2, _phase_b, _phase_b_round2; H1 edits no .githooks);
- UNION = 741 by the script + 2 added by hand after reading the nine leftovers that name an edited module, importlib or TestClient: tests/test_s71_u13_harness_auth.py (loads scripts/eval_runner.py by a Path join; eval_runner imports price_service, in the closure) and tests/test_sephora_provider_test_classify.py (loads .qa-bias-rerun/_sephora_provider_test.py by os.path.join; it imports price_service and scrapedo_service) = 743 of the 783 test_*.py files (+ the two RED files at GREEN = 745). The other leftovers import nothing in the closure (test_observability builds its own app on error_handler, which is outside the closure; test_async_utils names SCS in a comment; bias_matrix_probe, etl_survey_to_priors, instagram_feasibility_test and run_validation_matrix import no app module). No edited test-support helper. No migration, manifest, legal or client file changes.

| # | Gate | Command (DEFERRED) | Pass rule |
|---|---|---|---|
| G1 | syntax + lint | `<P-python> -m py_compile app/services/honest_empty.py app/services/extraction_service.py app/services/structured_comparison_service.py app/services/fact_check_service.py app/services/review_service.py app/services/response_builder.py tests/test_inc_h1_honest_empty.py tests/test_inc_h1_body_pins.py`; `<P-python> -m ruff check --select E9,F63,F7,F82 --no-cache <same files>` | clean |
| G2 | hygiene | bytes > 127 in every ADDED line = 0; `git diff --stat` shows no whole-file diff (CRLF kept); the added-line sweep (no @gmail, +973, 8-digit runs, key shapes); no new constant name with a scanner keyword; the Feature Flags paragraph still ONE line | clean |
| G3 | RED + PIN | `<P> <G> --bound 600 --tag inc-h1-green-red --log <SP>/INC-H1/green/red.log --cwd <W> -- tests/test_inc_h1_honest_empty.py tests/test_inc_h1_body_pins.py` | all pass |
| G4 | touched suites | the two 1.10 command-1 calls at HEAD, tags inc-h1-green-touch1 / -touch2 | FAILED set equal to the base set |
| G5 | prompt and source pins | the 1.10 command 2 at HEAD + tests/test_s81_st1_usage_path_offloop.py tests/test_m18_offload_sweep_residual.py tests/test_genuine_price_clobber_guard.py tests/test_m21_brand_dedup_and_verdict_copy.py tests/test_diagnostics_flag_gated.py, tag inc-h1-green-pins, bound 1200 | equal to base (the two cold-tiktoken ERROR nodes identical) |
| G6 | CLAUDE.md readers (cheap first look) | `<P> <G> --bound 600 --tag inc-h1-green-claude --log ... -- tests/test_ci_gates.py tests/test_behavior_dimension_translation.py tests/test_s81_s04_spend_breaker.py tests/test_s81_s08b_legacy_fingerprint.py tests/test_s81_s08b_gate_rows.py tests/test_s81_s23_bypass_retire.py` | green |
| G7 | the comm set | 30 chunks from comm_chunks.txt (743 files; + the RED files in a 31st call), bound 1200 each, tags inc-h1-cNN; base record at <SP>/harness/base_records/731bcddf531a7e123963246168ca19f262859337/<set-sha>.txt, computed at RED (LC-6) | `comm -13` of the sorted FAILED node sets EMPTY; a branch-only failure re-run against base once |
| G8 | client fences by path | from <W>/SmartCompareApp through the orchestrator's junction, after `<P> <G> --wait-only`: `timeout -k 15 600 node node_modules/jest/bin/jest.js --ci __tests__/brand/inAppMark.u4c.test.ts __tests__/clientTruth/medicalNote.s74.test.tsx __tests__/clientTruth/privacyManifest.s74.test.ts __tests__/clientTruth/shareTruth.s74.test.tsx __tests__/clipboardFallbackService.test.ts __tests__/config/nativeBundle.w37.test.ts __tests__/DimensionBars.perCategory.test.tsx __tests__/honestCounts.s69.test.tsx __tests__/landing.domain.s76.test.ts __tests__/navigation/linking.w315.test.ts __tests__/onboarding/step05Trust.s69.test.tsx __tests__/playInstallReferrerService.test.ts __tests__/playInstallReferrerService.edges.test.ts __tests__/ResultsScreen.timeout.test.tsx` | equal to base (the 4 nativeBundle.w37 drift nodes are the accepted base failures). Measured: medicalNote.s74.test.tsx:219-226 reads ES's `_PHARMACY_TABLET_TOKENS` set, which H1 does not touch; no fence reads FC, RV, RB, SCS, HE or CLAUDE.md lines H1 edits; they run because the footprint touches app/ (the lane rule) |
| G9 | CI-order set | `pytest tests/ -m "not (live_unit or live_db or integration)" --ignore=tests/test_integration.py` with the .pre_impl_failures deselects, through the runner in the final round only if the orchestrator rules the comm set insufficient | CI is the arbiter |

The pre-commit hook files run in their own call only if .githooks changes (it does not). <P-python> = C:/Users/SynAckITPC/Documents/AI/.venv-qaren/Scripts/python.exe.

## 8. The CLAUDE.md block, its anchor, the owner steps

Anchor: a new paragraph after the S81-07c block (CLAUDE.md:675-682 at the base) and before `## Tests` (CLAUDE.md:684), one blank line before its heading; at the final round it goes after the newest lane block in merge order (INC-R1 / INC-I1 / INC-X6 if they merged first). Plus ONE pointer sentence INSIDE the single `**Feature Flags:**` line (CLAUDE.md:341), right after the sentence that ends "...the **SESSION 81 follow-up unit (S81-07c CLAUDE-ROLE-FIX, ...)** block." and before "`REAL_ACTION_MIN_SECONDS` (5)." (never a new line: tests/test_s81_s08b_legacy_fingerprint.py:820-822). ASCII text, CRLF in the working copy.

Pointer sentence: `ENABLE_HONEST_EMPTY` (INC-H1 NO-CONFIDENT-EMPTY, default OFF, read per call): the rows of the **INCIDENT LANE unit (INC-H1 NO-CONFIDENT-EMPTY, ...)** block.

Block:

```
**INCIDENT LANE unit (INC-H1 NO-CONFIDENT-EMPTY, 2026-11-14, the S95-FIX lane of the 2026-11-11 incident; ONE new flag `ENABLE_HONEST_EMPTY`, default OFF, read PER CALL; a new name, so unset in production by construction; FOCUS (the result screen of both live bundles once flipped): two adversaries; no migration, no client file; branch `fix/inc-h1-honest-empty`; spec .qa-s80/INC-H1_UNIT_SPEC.md; frozen RED files tests/test_inc_h1_honest_empty.py, tests/test_inc_h1_body_pins.py):**
- `ENABLE_HONEST_EMPTY` (`app/services/honest_empty.py::honest_empty_enabled`, read as the first statement of every gated helper of that stdlib leaf). **Effect ON:** (1) an empty spec value (None, an empty container, NaN, or a string whose strip().lower() is "", "n/a", "na", "none", "unknown", "-", "null" or the em dash, or that contains "or null") is omitted from `specs.products[i].specs`, the `products[i].specs` alias, `specs.specs_comparison.rows` and the SSE `specs` frame; a real value is unchanged; the views are applied AFTER `scoring_v2` is built, so captions, bars and verdict templates are unchanged; (2) `fact_check_service.verify_spec_citations` and the #107 cached citation map skip empty values, so empty fields never count as citations: a product with no real field has specs counters 0, the specs leg is not strong from empty fields, and its reliability is absent (no reliability-proxy Versatility row and no "leads on Versatility" line when both products are empty); (3) `extract_reviews` sends `REVIEWS_EXTRACTION_SYSTEM_HONEST` / `_NO_RATING_HONEST` (count-checked twins asking for `has_review_data`); a no-data answer (`has_review_data` false, or no highlights and a consensus containing "no review data", "provided search results", "no reliable reviewer consensus" or "insufficient review") ships no review text: `review_praise` null, consensus "", highlights and the four text lists []; `build_review_praise` never returns a no-data consensus; (4) an all-empty spec sheet and a no-data reviews dict are never written to L1 or L2 (the post-extract writes, the enriched re-cache, the L2-to-L1 promotions); (5) one INFO line per product `[HONEST_EMPTY] product=<slot> specs_real=<n> specs_dropped=<n> reviews=<data|no_data> cached=<yes|no>` (cached = served from L1 / L2). The data stage (extract_specs, `_clean_specs`, the refill cascade, `compute_scores`, the verdict prompt input) is unchanged. **Flag OFF:** byte-identical bodies, SSE frames, saved rows, cache writes, prompt bytes and logs (pinned with the full configuration and the production set of record). Stated limits: the spec's section 9 (L-ONESIDE, L-CHIP-THIN, L-UNCITED, L-DATASTAGE, L-CAPTION, L-OLDCACHE, L-OLDROWS, L-HEADER, L-VERDICT-TEXT, L-PROSE, L-HRD-STRING, L-PHRASE, L-CROWN, L-READS, L-URL, L-PARTIAL-LOG, L-RG, L-SSE).
- **Owner steps (names only; a dated ledger line per step):** none to merge. The flip of `ENABLE_HONEST_EMPTY` on `web`, in its own canary window, set by the relay on the owner's yes; run the phone proof (the spec's section 8b) BEFORE any flip of INC-R1's resolution flag (proof 1 needs the empty identity). Merged is not proven until the phone shows it.
```

Owner steps (names only): the flip of ENABLE_HONEST_EMPTY on the web service in its own window (the relay, on the owner's explicit yes); the phone proof of 8b with the relay reading the saved rows and the [HONEST_EMPTY] lines. Nothing else: no credential, no migration, no other variable, no OTA. Independent of INC-X6 and of INC-C1's OTA (the bare header is the accepted interim, H1-10).

## 8b. PROOF ON THE PHONE (common brief H6; brief H1-8)

After the merge the unit is "merged, NOT yet proven". The proof runs after the relay's flip and needs NO AI text beyond what the comparison already produces (a consent-3 account sends the reviews call to Claude with the honest twin; a consent-below-3 account gets no reviews text at all because the OpenAI egress stop refuses the call; both satisfy the checks).
1. Repeat "stronger with you" vs "Tyger" (INC-R1 OFF, so the empty identity of 2026-11-13 reproduces). Must be visible: the Specs row shows no table of dash rows (the bare "dimensions" header and only the two names when expanded); the Specs chip is not High; no "Versatility" bar; the bold verdict line does not say "leads on Versatility"; the Reviews section shows no "No review data was available ..." sentence (it shows "Reviews are still coming in." or a real star rating). If one product returns real spec fields this time, the Specs rows with real values appear (correct) and a one-side Versatility bar may remain (L-ONESIDE): record it, it is not a failure of this unit.
2. "Dior Sauvage EDP vs Chanel Bleu de Chanel EDP": the Specs rows with real values are still shown (the same rows a pre-flip run of the pair showed, when one exists in History; the rich key count unchanged).
Each screenshot records the row id, the UTC time and the bundle (store app or updated app); the store bundle draws the same Specs, chips and reviews by construction (1.5, code reading) unless a device still on the store JS is used: the report says which.

BACKING CHECK in each saved row (the relay reads the comparisons row): `products[*].specs` and `specs.products[*].specs` contain no value from the H1 token set (case-insensitive, after strip) and no "or null" text; `specs.specs_comparison.rows` hold only rows with two real values; for pair 1 `scoring_v2.confidence_legs.specs` is not "strong" and `scoring_v2.dimensions` has no "versatility" key when both products show `specs_real=0`; `scoring_v2.factual_verdict.line1` has no "Versatility"; the no-data product's `review_praise` is null and `reviews.products[i].review_summary.consensus` is ""; `products[i].fact_check.specs_unverified` is 0 for a product with no real field. In the Railway log of the request: two `[HONEST_EMPTY]` lines (product=0 and product=1) with `specs_real=0`, `specs_dropped=<n>`, `reviews=no_data` for pair 1, and `specs_real` matching the number of real keys of the saved row for pair 2; `cached=yes` means the sheet came from the pre-flip cache (still a pass: the wire views and the fact-check skip apply to cached sheets; L-OLDCACHE). `metadata.partial` true makes a row NOT evidence. The lines also answer ADV R-4 for the incident pair (2.10).

NOT provable on the phone: the flag-OFF byte identity (the pins are the evidence); the non-write of empty sheets to Redis and the DB (hermetic rows R13 / R14; a production hint: repeating pair 1 a few minutes later logs `cached=no` again when the first run found no pre-flip entry, because nothing was written); the prompt twin's wording effect (probabilistic; the phrase guard is the belt). Suites and gates are necessary and are never the proof.

## 9. Stated limits

| Id | Limit |
|---|---|
| L-ONESIDE | When ONE product has real cited fields and the other none, the versatility row stays, with MISSING_SCORE 50 on the empty side and the hard-coded "medium" (SS:3585), winner None but painted by the client's score heuristic, and line1 can still say "leads on Versatility" (2.5 rows P). The one-side default-50 row is INC-X6's (R-X6 rows; its honest bars drop versatility for fragrance pairs entirely). |
| L-CHIP-THIN | The specs leg's verified share now counts real fields only, so a few verified fields can read strong (P under W ON: Medium -> High; under W OFF, production, the chip was already strong from the 11-field count). A coverage floor for strong is not in this unit (O6). |
| L-UNCITED | With W OFF (production) eight or more REAL but uncited fields (training-data answers, "unverified") still read strong: the citation-truth wiring (#109) owns it. |
| L-DATASTAGE | The internal sheet keeps its "N/A" stamps (extract_specs, `_clean_specs`): scoring, the refill triggers and the verdict prompt input are unchanged; a literal "unknown" / "-" still earns presence credit in `_score_specs` (SS:1921) as today (O1). |
| L-CAPTION | The "N/A vs Moderate projection" caption (SS:3669-3677) and every other caption are unchanged (INC-X6 / D2 F8). |
| L-OLDCACHE | Sheets and reviews written before the flip keep being served until their TTL (L1 7 d; L2 specs 30 d, reviews 14 d); the views, the fact-check skip and the praise gate make the wire honest anyway; `cached=yes` marks them; an empty L2 entry is no longer promoted to L1, so it is read from L2 on each miss until it expires (O9). |
| L-OLDROWS | Saved rows written before the flip keep their dash rows and praise (History serves the stored body). |
| L-HEADER | Both bundles draw the bare "dimensions" header and an empty table for an all-empty pair, and the reviews header still says "across both", until INC-C1 (H1-10). |
| L-VERDICT-TEXT | The deterministic lines beyond the removed dim are INC-X6's: "edges ahead on the overall picture" still crowns a winner on an all-empty pair, and the TopMatch badge is unconditional on both bundles (PLAN_S80 section 0 item 1). |
| L-PROSE | The verdict prompt still receives the stamped specs and the reviews consensus (ES:2674-2681), so the AI prose may mention missing reviews or "N/A" fields after the Claude switch. |
| L-HRD-STRING | A `has_review_data` that is not a bool ("false", 0) is ignored; the phrase guard decides (O10). |
| L-PHRASE | The phrase guard is English, substring-based and needs empty highlights (or a consensus fallback for S11); a no-data answer in other words slips through unless `has_review_data` is false. |
| L-CROWN | The crown can change for a pair whose overall included a reliability gap built from empty fields (fragrance versatility weight 0.15, SS:72; the incident shape 40 vs 30 -> both MISSING removes 1.5 overall points from p0). No other scoring input moves. |
| L-READS | The flag is read at several sites per request; a flip inside one request can split them for that request only (the house per-call rule). |
| L-URL | The link-mode body (url_extraction_service.py:1248 `"specs": raw.get("specs", {})`) is untouched. |
| L-PARTIAL-LOG | A product whose fetch the hard cap cancels writes no [HONEST_EMPTY] line; its partial body still gets the views (RB is the chokepoint of all three bodies, SCS:3903 / 4807 / 5701). |
| L-RG | With ENABLE_RESULT_STATUS_METADATA / ENABLE_RESULT_GATE ON (both OFF on web), H1 lowers the dims and reviews facts of an empty pair; the gate may refuse such a pair with INSUFFICIENT_DATA instead of serving it (the more truthful outcome; to be read at that gate's flip). |
| L-SSE | The SSE `specs` / `reviews` frames are cleaned too, but no screen renders them (onSpecs / onPrices only mark TTFB). |

## 10. Out of scope

INC-C1 (the client empty states, the reviews header) and every client file; INC-X6 (bars, captions, the fact-line templates, the one-side default rows); INC-R1 (resolution); INC-I1 (pictures); the data-stage stamping in extract_specs / `_clean_specs` (O1); a coverage floor on the Specs chip (O6); the citation-truth chain W / C / #106 / #108; the link-mode body; the KB paths; the refill cascade and the Tier-2 wall (RC8); the reviews variant filter and the stitched praise (RC10); the caption faults (RC9); the verdict prompt input; every flag flip; the S81-04c log arms; the History screen.

## 11. Open questions for the orchestrator, and the answers to the brief questions

### 11.1 Open questions (each with the spec's default and the reason it beats the alternative)

- O1 (H1-3 "instead of being stamped"): the omission is applied on the WIRE (the projections, the rows, the SSE frame), and the stamping sites ES:1706-1707 / SCS:3551-3552 are NOT edited. Reason: measured in 1.1 / 1.6, the refill triggers treat an omitted key and "N/A" alike but not "unknown" / "n/a" / "-" (SCS:6546, 800, 921, 3332), `_score_specs` counts those tokens as presence (SS:1921), the captions read the sheet before the builder (SS:3669-3677) and the verdict prompt dumps it (ES:2674-2681); a data-stage omission would change the refill cascade (latency: the Tier-2 4 s wall), the spec score (the crown), the captions (INC-X6) and the verdict prompt input, none of which H1-1 puts in scope. The wire views meet H1-3's visible contract exactly. Alternative: also omit at ES:1706-1707 (refill-neutral for empties) - harmless but buys nothing visible and widens the pins.
- O2 (Q1, the token set): the union the code already uses (2.1); "not specified", "not available", "not listed", "n.a." and "--" are NOT added (0 hits under app/). Reason: the brief's rule is "the exact set the code already uses"; a wider phrase set would be a new judgement on real text.
- O3 (H1-7, `cached=<yes|no>`): "yes" = the sheet was served from L1 / L2 in this request. Reason: it splits ADV R-4's cases (ii) and (iii) on the owner's own pair, and "written" would always read "no" for an empty sheet under the flag (no information). Alternative: "written to cache by this request" (needs a mark plumbed out of `_get_specs`).
- O4 (Q4, the fence file): no E-row; R12 asserts the guard sentence and the absence of placeholders in both twins. Reason: no existing node goes red; an E-row edits a source-scanning pin of every comm set. Alternative: the D08 E2 precedent (add the twins to tests/test_prompt_fence.py:286's loop), cheap and keeps one list of consuming prompts.
- O5: HE is not added to .github/black-clean-paths.txt. Reason: keeps .github out of the footprint (no extra fence trigger, no test_ci_gates allowlist row). Alternative: the MON1 precedent (its two new leaves joined the allowlist, lines 64-65).
- O6 (C-2 / R-5 follow-on): no coverage floor on the specs leg. Reason: H1-4 rules the cure as the fact-check skip; compute_confidence is not in the change list. Alternative: strong only with >= 4 real fields (would also cover L-CHIP-THIN), a scoring change for a follow-up unit with its own walk.
- O7 (H1-5 "no review text"): the no-data view also empties common_praises, common_complaints, retailer_quotes and review_source_quotes when present. Reason: they are review text in the alias and the reviews projection (retailer_quotes are built from the model's cited highlights, RV:280-348); neither bundle renders them, so nothing visible changes. Alternative: blank only consensus / highlights / praise.
- O8 (S11): `build_review_praise` also refuses a no-data consensus in the fallback when highlights exist but none is positive (REV_NEGONLY). Reason: that is exactly when the consensus would be the praise; the brief's "the consensus is not used as praise".
- O9 (H1-6): no read-side miss for empty entries written before the flip (they are served, with the views, until their TTL). Reason: the brief rules the writes; a read-side miss re-runs an LLM call per request for those keys. Alternative: treat a cached all-empty sheet / no-data dict as a miss under the flag (faster recovery, more calls).
- O10: no coercion of a string `has_review_data`. Reason: the router's JSON replies carry booleans; the phrase guard is the belt.
- O11 (Q3): the walk adds the T (ENABLE_TIE_IS_NOT_MISSING) cell E' because H changes it (a kept 30 / 30 tie on dense all-unverified evidence disappears). Reason: T is coupled to R in the code (SS:494-500) and touches the same reliability array.
- O12 (flip order): H1's flip before INC-R1's (proof 1 needs the empty identity); independent of INC-X6 and INC-C1.

### 11.2 Answers to the brief questions (file:line at 731bcddf)

- Q1 THE NA TOKENS. Section 1.6 lists every set and test (RG:63 / RG:245-250, RB:635, ES:1434, ES:1686-1691, ES:1700-1702, SCS:3551, spec_spine_service.py:265, SCS:644-647, the refill tests, SS:536 / 1921 / 1979, FC:333, openai_service.py:781-785 / 858, the client RA:87 / RA:82). Stamping sites: ES:1706-1707 and SCS:3551-3552 (left as they are, O1). The H1 set: NA_VALUES + "null" + U+2014 + "or null" + None (2.1, 2.2); "not specified" is not used anywhere.
- Q2 WHAT BOTH BUNDLES RENDER. Section 1.5: an empty dict on both sides -> the bare "dimensions" header (en.json:779 / :776) and an expanded table with only the two names, no rows (RA:206-223 / :165-182 with rich and structural empty); a short dict -> the rich keys, "<n> dimensions" counted before the one-dash drop (RA:293-296, RA:596-598), the same OFF and ON because the NA keys never entered the rich set. The OTA adds the D20 honest line only under ENABLE_RESULT_STATUS_METADATA / ENABLE_FIELD_STATUS_METADATA (both OFF). Fewer or no rows is the interim; the honest empty line is INC-C1's.
- Q3 THE FLAG MIXES. Section 1.7 (the orders: C before W, the #106 / #108 chain; U coupled to R and LAST; N LAST; T coupled) and the walk 2.5 (12 reachable mixes, pinned by R22 / P6, plus the E' / T cell). In production every one of W, U, R, N, C, T is unset (ledger line 316 + H12(c)).
- Q4 THE PROMPT PINS. The reviews prompt is pinned by tests/test_s81_d08_jsonld_widen.py P7 (sha 46791e1b... + the string sent OFF) and R18 (the NO_RATING derivation), tests/test_prompt_fence.py:272-287 (the guard sentence) and :325-332 (the digest wrap), tests/test_prompt_injection.py:113-117; the W4-11 recorder and tests/test_prompt_truth.py digest no reviews prompt. The house way to keep the OFF prompt byte-identical is the D08 derivation (ES:1031-1044): new constants derived by count-checked edits at import, picked per call; the base constants are never edited, so the OFF prompt stays the P7 bytes and no digest moves (measured by AST evaluation, 1.3 / 2.3). The prompt change must sit behind the flag: yes, it does (S15).
- Q5 EVERY CACHE WRITE PATH. Section 1.4: W1 SCS:6847, W2 SCS:6913-6922, W3 SCS:6669-6682, W4 RV:759, W5 RV:792-809, W6 / W7 RV:825-829 / 842-846 (they follow W5). H1 gates W1-W5 (S8, S9, S6, S12, S13); W6 / W7 follow `extraction_persisted`. No other writer under app/.
- Q6 THE PINS. Section 4: no E-row (O4 optional); 4.2 lists the fact-check, confidence, scoring-dims, factual-verdict, response-contract, prompt, stream, golden-fixture, source-scanning and CLAUDE.md-reader pins that must stay green and unedited, with the two source inventories H1 must not trip (1.9: the four direct `set_cached` calls of get_reviews, the single Feature Flags line).

## Not done in this spec

- No pytest, jest, tsc or eslint ran (READ-ONLY round, H5 c): the base pass state (1.10), the comm-set base record, every RED / PIN verdict and every mutant are DEFERRED TO RED / GREEN with their commands.
- The base literals of P1 (bodies, frames, partial, write calls) and the H OFF cells of R22 are recorded by the RED round at the base, not here; the 2.5 values are computed from the formulas of 1.2 by hand and are to be confirmed by the RED round (a mismatch is a finding, never a re-record).
- Not measured: the production share of empty sheets and no-data reviews in L1 / L2 (no production read in this lane); any device rendering (1.5 and 2.6 are code reading); the Claude reply to the honest twin (probabilistic; the phrase guard is the belt); the Railway log of 2026-11-13 behind ADV R-4 (the [HONEST_EMPTY] line answers it after the flip).
- Nothing here is a production proof; once merged the unit is "merged, NOT yet proven" until the owner's phone shows section 8b.
