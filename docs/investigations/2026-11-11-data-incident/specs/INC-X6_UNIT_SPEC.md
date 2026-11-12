# INC-X6 HONEST-BARS - UNIT SPEC (server only; first unit of the INC-PAGE cluster)

- Unit: INC-X6 HONEST-BARS (incident root cause 7, fix row X6 of record/incident/INCIDENT_AND_DATA_PLAN_2026-11-11.md:105; part of INC-PAGE = X4 + X7 + X5 + X6, RULINGS_INC_R0.md R0-2 row 5).
- Flag ruling: ONE new DARK flag `ENABLE_HONEST_FRAGRANCE_BARS` (git grep at the base finds 0 hits for the name, for `honest_fragrance` and for `DIM_EVIDENCE_FIELDS` in app/, tests/, scripts/, CLAUDE.md). Default OFF, read PER CALL with the house idiom `os.getenv(NAME, "false").strip().lower() in ("true", "1", "yes", "on")` as the FIRST statement of its predicate; never cached at import. Flag OFF: byte-identical bodies, rows, SSE frames, prompt bytes, verdict key, Home caption and logs, pinned with the FULL configuration and call recorders (section 5). Flag ON changes what BOTH live bundles draw for a fragrance pair (section 2.6). Nothing ships unflagged.
- Class: FOCUS (the App-Review-visible result screen of both live bundles, once flipped). Chain: spec -> adversarial spec review -> rulings -> RED (frozen) -> gate -> GREEN -> two adversaries (correctness; contract-and-live-bundles) -> fix rounds -> final round (comm set + source-scanning pins + client fences by path) -> PR.
- Worktree: C:/Users/SynAckITPC/Documents/AI/sc-inc-x6 (detached at the base; read-only in this round). Branch GREEN creates: fix/inc-x6-honest-bars. RED files: tests/test_inc_x6_honest_bars.py, tests/test_inc_x6_body_pins.py. Runner tags: inc-x6-*.
- Base sha (full): 6b909e0a92067d6b3562eee325e4956c116441f7 (merge of #399, S81-04c). `git status --short` of the worktree: EMPTY before and after every probe of this round (the only new file is this spec under the gitignored .qa-s80/, `git check-ignore` -> .gitignore:72 `.qa-*/`).
- Measurement location: <SP>/INC-X6/spec (base file copies via `git show 6b909e0a:<path>`, the comm-set script output closure.json / comm_set.txt). <SP> = C:/Users/SYNACK~1/AppData/Local/Temp/claude/cde30765822f13ce/db84aee4-7211-4eaf-8fea-00a7c4310b9b/scratchpad.
- This round is READ-ONLY (header H5 c): no pytest, jest, tsc or eslint ran; every run is listed with its command and marked DEFERRED TO RED.
- Evidence pointers: the unit brief record/inc/INC_X6_BRIEF.md (rulings R-X6-1..R-X6-21, questions Q-1..Q-15); record/inc/PAGE_DESIGN_V2.md sections 2, 2.1-2.4; record/inc/PAGE_INVENTORY.md part (c); record/incident/T1_trace.md section 5 (the three incident rows C1/C2/C3); record/s80/PLAN_S80.md section 0 and R-A8 (line 29); record/s80/contract_freeze.json (lines 30, 48, 466, 472, 478, 545); record/inc/RULINGS_INC_R0.md; the common brief wf/inc-common.txt header H0-H7.
- Sister units and contracts: X5 (ENABLE_RESULT_TEXT_CODES) reads this unit's `state` (PD2 section 8), so X6 lands before X5; X7 and X5 edit response_builder near the fact-line templates (RB:1073-1181), X1 edits RB / price_service / SCS: whichever merges second rebases and re-runs the comm set (R-X6-21). S91 (S81-04c, merged in this base) edited only the LLMUnavailableError log arms of extraction_service.py, image_routes.py, url_extraction_service.py: X6 edits none of those files. Consumed contracts: result_gate.price_is_showable / rating_is_real / MODEL_KNOWLEDGE_MARKERS (S80 B1), the Dimension pydantic model (app/models/scoring_v2.py), the frozen client contract (contract_freeze.json).
- Personal-data rule: the repo is public. No personal value in any file, test, fixture or log line; product names in tests are synthetic (e.g. "Brand A Scent X"); no credential shape; digests written as base64 or built at run time; no constant whose name contains access / auth / api / credential / creds / key / password / secret / token.

Short names: SS = app/services/scoring_service.py, RB = app/services/response_builder.py, SCS = app/services/structured_comparison_service.py, RG = app/services/result_gate.py, HR = app/api/home_routes.py, ES = app/services/extraction_service.py, M = app/models/scoring_v2.py, DB / RU / RC = SmartCompareApp/src/components/results/{DimensionBars,RunnerUpWinsCard,ResultsContent}.tsx at the base (= the OTA f1e20c39; DB, RU and FactualVerdict.tsx byte-identical in the 683f56c0 store export per the brief's cmp). Every file:line below was read at 6b909e0a in this run.

## 0. What the unit does

Today a fragrance result can show score bars that are not what their label says, and default values can reach the bars and the verdict lines:
- Longevity is the `spec_secondary` signal (SS:2176) that falls back to the REVIEW score when specs are missing (SS:2339-2352); Projection is the `review` signal (SS:2177); Presentation is `popularity` (rating count), Character counts filled specs, Versatility is the fact-check share (SS:2175-2179). Incident row C2 showed longevity 92 vs 96 "Longer-lasting" and projection 92 vs 96 "Stronger projection" from the star ratings 4.6 / 4.8, and presentation 64.3 vs 100 from the counts 85 vs 6600 (T1_trace.md:174).
- A missing raw signal is MISSING_SCORE = 50 (SS:297); a one-side-missing category dim is still emitted with 50 on the missing side (`_dim_from_category_lookup`, SS:3503-3589; only both-missing is omitted, SS:3570-3571). Its server `winner` is None (SS:3226-3227), but both bundles then paint the bar winner from the scores (DB:263-269). Row C3: versatility 50 (default) vs 30, "More versatile", and `factual_verdict.line1` "... leads on Versatility." (T1_trace.md:175) because `_top_dim_candidate` (RB:920-950) and `_runner_up_dim_candidate` (RB:953-979) read any row with two numbers.
- The runner-up sentence `"{loser} stays competitive on {dim}."` (RB:238-244) comes from `compute_tradeoff_pairs` (SS:2722-2789), whose F4.2 sweep fallback `_loser_strongest_dim` (SS:2791-2837) can pick a default or a proxy dim; `overview.tradeoffs` ships the same list (RB:1995).
- The AI scores summary `build_scores_summary` (SS:3017-3104) prints "stronger / weaker / comparable" per breakdown dim with `breakdown.get(dim, 50)` (SS:3068, SS:3070-3072) and a "Dimension leaders" line (SS:3091-3099), the proxies included.

Behind `ENABLE_HONEST_FRAGRANCE_BARS`, for a fragrance pair only, X6: (1) makes `scoring_v2.dimensions` exactly five rows in a fixed order (price, reviews, longevity, projection, value), each "known" only from a real source for THAT dimension, the others "partial" or "unknown" in the existing placeholder shape plus additive keys (`state`, `basis`, `known_side`, `data_insufficient`); (2) stops the fact lines (and through line1 the Home smart-pick caption of new rows), the tradeoff list / runner-up sentence and the AI scores summary from using a row that is not known. It moves NOT the crown, the weights, `compute_scores`, the breakdown, `dimension_winners`, the legacy `scoring` block, personalization, any client file, or any S81-04c log arm. Non-fragrance and mixed pairs are byte-identical with the flag ON.

## 1. Base state MEASURED (6b909e0a)

### 1.1 The bars path (SS)

| Site | file:line | Measured |
|---|---|---|
| fragrance category dims | SS:50-53 | character, longevity, projection, versatility, wear_value, presentation (`*_score`) |
| fragrance signal map | SS:2175-2179 | character=spec, longevity=spec_secondary, projection=review, versatility=reliability, wear_value=value, presentation=popularity |
| spec_secondary fallback | SS:2339-2352 | spec missing -> the review score; both missing -> MISSING_SCORE |
| MISSING_SCORE | SS:297 | 50 |
| _NEUTRAL_DISPLAY_SCORE | SS:3168 | 75 |
| _dim_winner | SS:3192-3237 | None on a None score, on either was_missing flag, on confidence "low", on a margin < 3.0 (SS:3189); else 0 / 1 |
| _dim_price | SS:3240-3269 | placeholder when either amount <= 0 or None: 75/75, "Price data unavailable", low, caption_key limited_data; else calibrated, "<CUR> <diff> less", high. Reads price.amount only (no source_method / estimated / unavailable check) |
| _dim_reviews | SS:3272-3311 | non-numeric or rating_derived True = missing -> 75/75 "Limited review data" low limited_data; else calibrate(40 + r*10), "<d> stars higher" / "Same rating", high |
| _dim_value | SS:3314-3422 | "Limited value data" placeholder unless both prices > 0 and both ratings real; else value ratio, confidence "medium", is_cross_tier |
| _dim_from_category_lookup | SS:3503-3589 | scores from scores.product_i.breakdown[dim]; was_missing from missing_data (SS:3558-3567); both missing -> None (SS:3570-3571); ONE missing -> emitted with the default on the missing side |
| fragrance captions | SS:3660-3685 | longevity "{max}h vs {min}h" with int() when both hours parse (SS:3661-3667) else "Longer-lasting"; projection "{sa} vs {sb} projection" from the raw sillage texts (SS:3673-3676) else "Stronger projection"; "More distinctive" / "More versatile" / "Better presented" / "Better everyday value"; "Comparable" on a margin < 1.0 (SS:3614-3615) |
| hours reader | SS:3790-3818 | _LONGEVITY_PHRASE_HOURS ("long-lasting" 9.0, "strong" 8.0, "moderate" 5.0, ...); _extract_hours: int/float as is (a bool passes), the first number of a string, else the phrase map, else None |
| build_dimensions_v2 | SS:3848-3933 | core price, reviews, value (SS:3867-3871); canonical categories (SS:3877-3879); category dims only when cat_a == cat_b and category in CATEGORY_DIMENSIONS (SS:3880-3881), at most 5, value_ proxies skipped (SS:3896-3899 drops wear_value_score); None/None rows omitted (SS:3907-3910); winner stamped, was_missing popped (SS:3920-3932); dims[:8] |
| compute_dimension_winners | SS:2605-2652 | keyed by breakdown name (longevity_score ...); one side missing names the OTHER product, margin None |
| compute_tradeoff_pairs | SS:2722-2789 | entries {"dimension": <breakdown key>, "product": <name>, "margin": float}; margins <= 5 dropped; sweep fallback when scores is passed (SS:2766-2769) |
| _loser_strongest_dim | SS:2791-2837 | the loser's highest raw sub-score; guard only under ENABLE_VALUE_DIM_PARTIAL_SIGNAL or ENABLE_TIE_IS_NOT_MISSING (SS:2813) |
| build_scores_summary | SS:3017-3104 | category from the breakdown key SET (SS:3026-3031); rank line (SS:3058-3064); "    Per dimension: " over six dims with breakdown.get(dim, 50) (SS:3065-3083); "  Score winner" (SS:3085-3089); "  Dimension leaders" from dimension_winners (SS:3091-3099); cross-tier note (SS:3101-3102); no product data in the signature (SS:3017) |
| display names | SS:1339-1340 | longevity_score "longevity", projection_score "projection", wear_value_score "value per wear" |
| imports | SS:7-12 | stdlib + extraction_service (CATEGORY_SPEC_SCHEMAS, canonicalize_category); no result_gate import today |

canonicalize_category (ES:1236-1262): "other" for None / non-string / empty / unknown; pure.

### 1.2 The response builder (RB)

| Site | file:line | Measured |
|---|---|---|
| scoring imports | RB:11-18 | MISSING_SCORE, build_dimensions_v2, calibrate_score, compute_confidence, confidence_single_computation_enabled, count_missing_dim_cells |
| result_gate import | RB:21 | STATUS_SUPPORTED, assess_result, result_status_metadata_enabled, result_gate_enabled |
| flag idiom | RB:171-182 | _winner_prose_reconcile_enabled (strip, lower, in 1/true/yes/on) |
| deterministic verdict fields | RB:197-245 | key_tradeoff "{loser} stays competitive on {dim_label}." from tradeoffs[0].loser_wins (RB:238-244) |
| reconcile chokepoint | RB:248-353 | ENABLE_WINNER_PROSE_RECONCILE ON + a mismatch writes deterministic_verdict_fields (RB:341-345) |
| rating derive | RB:1612-1621 | ENABLE_JSONLD_RATING OFF: a None rating becomes derive_rating_from_scores(overall), rating_derived True, BEFORE scoring_v2 |
| price chokepoint | RB:1636-1765 | UNCONDITIONAL: a non-dict price, a currency-guard reject and every not is_price_showable price become make_pending_price (amount None, unavailable True; price_service.py:2005-2018); is_price_showable refuses a source_method outside the showable set, "estimated" included (price_service.py:1877-1910). An estimated price with an amount reaches _build_scoring_v2 only if this block raises (except arm RB:1764-1765) or when build_dimensions_v2 is called directly |
| _safe_price_amount / _safe_rating | RB:842-870 | any amount > 0 (no source check); rating None when derived, dict ratings read score / average |
| line1 candidates | RB:873-950 | _price_candidate, _rating_candidate, _top_dim_candidate (skips price/reviews/value, RB:933; any row with two numbers, RB:935-942) |
| line2 candidate | RB:953-979 | _runner_up_dim_candidate: any row incl. core; a 75/75 placeholder never fires (margin 0) |
| line formats | RB:1073-1131 | "{w} leads on {label}." (RB:1095-1097); "{r} pulls ahead on {label}." (RB:1110-1112); price fallback (RB:1113-1121); rating fallback (RB:1122-1129); neutral (RB:1131) |
| _build_factual_verdict | RB:1134-1181 | candidates by magnitude (RB:1162-1171); sparse fallback "{w} edges ahead on the overall picture." (RB:1175) |
| _build_scoring_v2 | RB:1243-1366 | build_dimensions_v2(product_data, scoring_result, category) (RB:1309); _build_factual_verdict(product_data, scoring_result, winner_index, dimensions) (RB:1312-1314) |
| the call | RB:2079-2082 | _build_scoring_v2(product_data, scoring_result, category_used, winner_index, ...) |
| specs block | RB:1999-2008 | specs.products[i].specs = pd.get("specs") (the _field_confidence map ships in the saved row) |
| tradeoffs out | RB:1995 | overview.tradeoffs = the caller's list |
| legacy scoring | RB:2070-2077 | scores, dimension_winners, ... (untouched) |

### 1.3 The orchestrator (SCS)

| Site | file:line | Measured |
|---|---|---|
| imports | SCS:63-66 | from app.services.scoring_service import get_scoring_service, MISSING_SCORE (+ NUMERIC_SPEC_FIELDS) |
| partial tradeoffs | SCS:3845-3857 | inside `if scoring_result:`; product_data = the stash (SCS:3821); category ctx.get("category_used", "") (SCS:3891) |
| partial deterministic verdict | SCS:3872-3878, SCS:9518-9555 | fill-only key_tradeoff from deterministic_verdict_fields (SCS:9543-9554) |
| sync summary | SCS:4652-4653 | scores_summary = scoring_service.build_scores_summary(scoring_result, product_names); category_used in scope (SCS:4672, SCS:4681) |
| sync key / prompt | SCS:4668-4685 | kb_serve.log_verdict_key(..., scores_summary=...); generate_comparison(..., scores_summary=..., category=category_used) |
| sync tradeoffs | SCS:4750-4754 | then build_comparison_response(..., tradeoffs=tradeoffs, category_used=category_used) (SCS:4783-4795) |
| stream summary | SCS:5503-5504 | same call; the SSE scores frame (SCS:5510-5516) carries scores + dimension_winners only |
| stream key / prompt | SCS:5525-5538 | as sync |
| stream tradeoffs | SCS:5598-5602 | then reconcile_winner_prose(..., tradeoffs) (SCS:5611-5613) and the complete build (SCS:5676) |

Tests drive SCS with a MagicMock scoring service (tests/test_streaming.py:128, tests/test_m13_04_full_stream_deadline.py:71-75, tests/test_winner_prose_reconciliation.py:309, tests/test_arabic_verdict_output_w414.py:497-498): a NEW method called on the service instance would return a MagicMock there. Hence the tradeoff filter is a MODULE function imported by name into SCS, never a service method. No test asserts the call args of build_scores_summary or compute_tradeoff_pairs, and none monkeypatches build_dimensions_v2, _build_factual_verdict, _build_scoring_v2, build_scores_summary or compute_tradeoff_pairs (git grep: 0 hits each).

### 1.4 Evidence facts and the confidence map (RG, producers)

| Site | file:line | Measured |
|---|---|---|
| _num | RG:107-109 | a number, never a bool |
| price_is_showable | RG:213-224 | dict, _num amount > 0, not unavailable / estimated, a non-empty source_method other than "estimated". NOTE: a NaN amount passes (_num(nan) True, nan <= 0 False): X6 adds math.isfinite |
| rating_is_real | RG:239-242 | _num rating and rating_derived is not True |
| MODEL_KNOWLEDGE_MARKERS | RG:69-73 | {"tier3_synthesis", "training_data"}; the comment: snippet, db, smart_fallback, tier2_fallback keep counting (R-A4, fix round F1-3) |
| _tier3_fields | RG:253-258 | an EMPTY set when the map is missing: NOT reused as the known test |
| dim_is_discriminating | RG:299-321 | numeric pair, caption / confidence not in {missing, limited_data, tier3}, margin >= 3; strict also refuses confidence low, a 50 on either side and a missing_data key |
| facts / _dims | RG:359-364, RG:390-411 | dims fact = any discriminating row of scoring_v2.dimensions |
| RG imports | RG:21-27 | stdlib + text_sanitize (which imports only re): SS may import RG with no cycle |
| producers of _field_confidence | SCS:3497-3538 (_clean_specs lifts `<field>_source`: snippet_N -> "snippet", "training" -> "training_data", else the raw value); SCS:6590-6597 "smart_fallback"; SCS:6625-6630 "tier2_fallback"; SCS:6656-6661 "tier3_synthesis"; kb_serve.py:313-317 "kb_cited" for every KB-served field | the extraction prompt asks a `<field>_source` for EVERY field (ES:660, ES:765) |
| sillage vocabulary | ES:219 (schema comment "soft, moderate, strong"), ES:467 (rule: "Intimate, Moderate, Heavy, Enormous"), ES:527-528 (example "Heavy"); kb_serve.LICENCE_FIELDS names longevity and sillage (kb_serve.py:55) |
| longevity alias | ES:255 | longevity_hrs -> longevity |
| recorded fragrance fixture | tests/fixtures/comparison_baseline_d2_post_bucket_a__fragrances.json | Tobacco Vanille: longevity "long-lasting" (marker snippet), sillage "N/A"; Sauvage: longevity "8-10 hours" (smart_fallback), sillage "4+ hours" (smart_fallback); ratings 4.4 / 4.6 real |

### 1.5 The live bundles (code reading at the base = OTA f1e20c39; DB, RU, FactualVerdict byte-identical in the 683f56c0 export per the brief)

| Reader | file:line | Measured |
|---|---|---|
| visible "Limited data" row | DB:68, DB:148-154, DB:224-233 | selects `data_insufficient === true` ALONE; draws the localized label + results.dimensions.limited_data; rendered AFTER the bars (DB:139-154), so on today's apps unknown rows sit at the bottom |
| renderable filter | DB:82-88 | drops data_insufficient, null scores and caption_key limited_data |
| zero guard | DB:95-111 | a renderable score <= 0 replaces all bars with an English breach line |
| legend | DB:128 | only with >= 1 renderable row |
| HERO_CAP | DB:116-117 | 4; more renderable rows -> "See full breakdown" |
| bar winner | DB:263-269 | `winner` 0/1 wins; null -> the score heuristic (ties -> the overall winner) |
| runner-up rows | RU:50-63 | caption_key limited_data skipped; runner score > winner score |
| runner-up hide | RU:100 | no row and no key_tradeoff prose -> no card |
| outer gate | RC:527 | scoring_v2.dimensions.length >= 3 (RAW list) |
| price pending filter | RC:212, RC:555-562 | any price.unavailable -> price and value rows removed |
| key_tradeoff caption | RC:239-241 | overview.winner.key_tradeoff when not degraded |

### 1.6 Home and History

HR:629-648: under ENABLE_SMART_PICK_VERDICT_CAPTION the caption is the saved row's factual_verdict.line1 (production value UNVERIFIED); else the winner declaration. `_select_smart_pick` (HR:538-620) reads the legacy scoring.dimension_winners and the price amounts, not scoring_v2.dimensions. History GET /{id} returns the STORED full_response (app/api/history_routes.py:138-168); no app module rebuilds a body (git grep: only RB / SCS / SS name the builders). No whole-body cache is in use: cache_service.get_comparison_cache / set_comparison_cache (cache_service.py:777-785) have no caller under app/ (git grep).

### 1.7 Libraries on the pinned venv (.venv-qaren, read from dist-info and the lock)

pydantic 2.13.4 / pydantic-core 2.46.4 (requirements.txt pins the same); the Dimension model sets no `extra`, so the default (ignore) applies (pydantic/config.py:63 `extra: ExtraValues | None`, _config.py:278 `extra=None`): the additive keys do not fail validation. pytest 9.1.1. No new dependency.

### 1.8 The flag-reader idiom and the flags the touched functions read

Idiom: RG:701-703 (`result_gate_enabled`, os.getenv(NAME, "false").strip().lower() in _TRUTHY, RG:81) and RB:171-182. Env names read at the base (grep of getenv / environ.get): SS reads DISABLE_DIM_NORM_DAMPENING, ENABLE_BEHAVIORAL_DIM_TRANSLATION, ENABLE_BUNDLE_C_SCORING (process-cached, SS:413-418), ENABLE_CATEGORY_VALUE_BADGE, ENABLE_CONFIDENCE_FACTCHECK_WIRING, ENABLE_CONFIDENCE_SINGLE_COMPUTATION, ENABLE_FACTCHECK_SHOPPING_KEY, ENABLE_MISSING_DIM_RENORM, ENABLE_RELIABILITY_UNCHECKED_ABSENCE, ENABLE_SPEC_FIELD_NORM, ENABLE_TIE_IS_NOT_MISSING, ENABLE_VALUE_DIM_PARTIAL_SIGNAL, WINNER_DIM_GAP_TOLERANCE, WINNER_PRICE_AUTHORITY_POINTS, WINNER_VALUE_WEIGHT_SCALE; RB reads DEBUG_STAGE_TIMINGS (process-cached), ENABLE_GPT_WINNER, ENABLE_HONEST_PARTIAL_SCORING, ENABLE_SINGLE_VERDICT_MARGIN, ENABLE_WINNER_PROSE_RECONCILE, ENABLE_YOUTUBE_SOURCE, EVAL_CAPTURE_DEBUG, and through other modules ENABLE_JSONLD_RATING, ENABLE_REGION_CURRENCY_GUARD, ENABLE_PRESCORING_SHOWABLE_GUARD, ENABLE_EXACT_PRICE_GATE, ENABLE_SHOWABLE_NAME_IDENTITY, ENABLE_STORE_LABEL, ENABLE_RESULT_AGGREGATES, ENABLE_LLM_LEDGER_V2, ENABLE_RESULT_STATUS_METADATA, ENABLE_RESULT_GATE; HR reads ENABLE_SMART_PICK_VERDICT_CAPTION, ENABLE_HOME_SAVINGS_AGGREGATE; the SCS summary sites feed kb_serve.log_verdict_key (ENABLE_VERDICT_CACHE_LOG) and generate_comparison (ENABLE_ARABIC_VERDICT_OUTPUT). This union is the FULL CONFIGURATION of section 5 (every name present in git grep, counts 9..259 hits each).

### 1.9 Guards the new code must not trip

- tests/test_scoring_calibration_bundle_c.py:133-166 scan SS source for `.get('rating') or <digit>`, `price or 0.<digit>`, `warranty or 1`: the new code writes none of them.
- The Dimension model (M:24-43): int scores, confidence in high / medium / low, delta_text free of the banned words of M:9-14 ("better", "best", ... ; "Longer-lasting", "Stronger projection", "Comparable", "<n>h vs <n>h" are clean). ScoringV2 (M:51-69): at most 8 rows, core keys exactly price / reviews / value with is_core True.
- The WS-B rule (SS:3656-3659): never a "+Npt" fragrance caption.
- The client zero guard (DB:95-111): no score 0 on a renderable row; every X6 score is an int in [40, 100] or 75.
- No import-time env read (the hermeticity pins, tests/test_hermeticity_pins.py:1122-1287): the flag is read per call.
- gitleaks names (H7): no new constant name with a scanner keyword (the row tuple is HONEST_FRAGRANCE_ROWS, not ..._KEYS).
- The S81-04c arms: X6 edits no line of extraction_service.py, image_routes.py or url_extraction_service.py.
- The prompt fences: no prompt builder is edited (extraction_service.py untouched); tests/test_prompt_fence.py:696 and tests/w4_11_prompt_digest_recorder.py:177 render with a fixed scores_summary, so their digests cannot move.
- Pure ASCII in every added line (the touched files already hold UTF-8 characters elsewhere; GREEN adds none).

### 1.10 Line endings and the base pass state

Line endings: core.autocrlf=true, no .gitattributes; `git ls-files --eol` = i/lf w/crlf for SS, RB, SCS and CLAUDE.md; the Edit tool keeps CRLF; a whole-file diff in `git diff --stat` is a defect. New test files: LF in the index (the house form of the S81 RED files).

Base pass state: NOT MEASURED in this read-only round. DEFERRED TO RED, with these exact commands (<SP> as in the header; <N> = <SP>/INC-X6/red):
1. Touched-file suites at base: `PYTHONIOENCODING=utf-8 C:/Users/SynAckITPC/Documents/AI/.venv-qaren/Scripts/python.exe <SP>/harness/pyt.py --bound 600 --tag inc-x6-base-touch --log <N>/base-touch.log --cwd C:/Users/SynAckITPC/Documents/AI/sc-inc-x6 -- tests/test_dimensions_builder.py tests/test_scoring_v2_models.py tests/test_category_dimensions.py tests/test_fragrance_content_quality.py tests/test_scoring_dimensions_v2.py tests/test_w4_12_display_contract.py tests/test_tradeoffs_dedup_parity.py tests/test_winner_prose_reconciliation.py tests/test_scoring_rubric_truth.py tests/test_scoring_service.py tests/test_arabic_verdict_output_w414.py tests/test_m13_04_full_stream_deadline.py tests/test_streaming.py` (DEFERRED TO RED).
2. Prompt pins at base: `... pyt.py --bound 600 --tag inc-x6-base-prompt --log <N>/base-prompt.log --cwd <W> -- tests/test_prompt_truth.py tests/test_prompt_fence.py tests/test_model_config.py tests/test_model_config_enforced.py` (the two cold-tiktoken ERROR nodes of test_prompt_truth are known base noise; record them identically) (DEFERRED TO RED).
3. The comm set base record (section 7, 681 files, 28 chunks of <= 25, bound 1200 each, tags inc-x6-base-cNN): no record exists for 6b909e0a under <SP>/harness/base_records/ (listed: 21 shas, none this one), so it is computed ONCE at RED and stored there by LC-6 (DEFERRED TO RED).
4. The fourteen client fences by path (section 7 G9) at base (DEFERRED TO RED / GREEN; they need the node_modules junction the orchestrator creates).

## 2. Contract

Contract freeze re-read (record/s80/PLAN_S80.md section 0 items 1-6; contract_freeze.json lines 30, 48, 466, 472, 478, 545): additive keys only; no key a bundle reads is removed, renamed or retyped; dimension keys stay inside the 51-key catalog (price, reviews, longevity, projection, value are in it, brief R-X6-8); no score 0 (RULE 5); no new error envelope, no 503 of any kind (this unit raises nothing new).

### 2.1 Flags and knobs

| Name | Type | Default | Read | Production |
|---|---|---|---|---|
| ENABLE_HONEST_FRAGRANCE_BARS | env flag | OFF (unset) | per call, first statement of `honest_fragrance_pair`; strip + lower; ON only for true / 1 / yes / on | unset on web (a new name, Railway not read) |

No knob. Constants (test seams, production values in brackets): `_HONEST_LONGEVITY_CAP_HOURS` [12.0], `_HONEST_LONGEVITY_MAX_HOURS` [72.0], `_HONEST_SILLAGE_LEVELS` [section 2.3], `_HONEST_LEVEL_SCORES` [1: 40, 2: 60, 3: 80, 4: 100].

### 2.2 New and changed symbols (all in SS unless named)

| Symbol | Signature | Contract |
|---|---|---|
| HONEST_FRAGRANCE_FLAG | str constant | "ENABLE_HONEST_FRAGRANCE_BARS" |
| honest_fragrance_bars_enabled | () -> bool | the idiom; per call |
| honest_fragrance_pair | (products_data, category) -> bool | FIRST statement: `if not honest_fragrance_bars_enabled(): return False` (reads no other state OFF). Then True exactly when products_data is a list/tuple of >= 2 dicts and `canonicalize_category(p0.category) == canonicalize_category(p1.category)` and `canonicalize_category(category) == "fragrances"` - the SAME test build_dimensions_v2 makes today for routing a pair to the fragrance dims (SS:3877-3881; see Q-1 / O2). Pure, total |
| HONEST_FRAGRANCE_ROWS | tuple | ("price", "reviews", "longevity", "projection", "value") |
| honest_fragrance_spec_rows | (products_data) -> dict | {"longevity": row, "projection": row}, the two spec rows of 2.3 (used by the bars, the tradeoff filter and the summary so the three cannot disagree) |
| build_honest_fragrance_dims | (products_data, scoring_result) -> list[dict] | the five rows of 2.3, in order; never reads the breakdown |
| honest_fragrance_tradeoffs | (tradeoffs, products_data, category, winner_index) -> list | not an honest pair -> returns `tradeoffs` ITSELF (the same object, untouched); else a NEW list of the pairs that pass 2.4 (b) |
| build_dimensions_v2 | (products_data, scoring_result, category, *, honest=None) | honest None -> `honest_fragrance_pair(products_data, category)`; True -> `return build_honest_fragrance_dims(...)`; False -> today's body byte-for-byte |
| ScoringService.build_scores_summary | (self, scoring_result, product_names, *, products_data=None, category=None) | today's early return first (SS:3019-3020); then the honest path only when products_data is not None and honest_fragrance_pair(products_data, category); else today's bytes |
| RB _build_scoring_v2 | unchanged signature | reads `honest = honest_fragrance_pair(product_data, category)` ONCE and passes `honest=honest` to build_dimensions_v2 and _build_factual_verdict |
| RB _build_factual_verdict | (..., dimensions=None, *, honest=False) | honest False -> today's body; True -> 2.4 (a) |
| RB _top_dim_candidate / _runner_up_dim_candidate | (dimensions, winner_index, *, known_only=False) | known_only False -> today's loop |
| RB _format_line2 | (..., winner_index, *, price_known=True, rating_known=True) | defaults = today |
| SCS import | SCS:63 | `from app.services.scoring_service import get_scoring_service, MISSING_SCORE, honest_fragrance_tradeoffs` |
| SCS tradeoff sites | SCS:3850, SCS:4750, SCS:5598 | right after each compute_tradeoff_pairs: `tradeoffs = honest_fragrance_tradeoffs(tradeoffs, product_data, <category>, scoring_result.get("winner_index", 0))`, <category> = category_used (sync, stream) / ctx.get("category_used", "") (partial) |
| SCS summary sites | SCS:4653, SCS:5504 | `build_scores_summary(scoring_result, product_names, products_data=product_data, category=category_used)` |

Every new function is pure and total: any JSON-like input (None, list, bool, NaN, a string where a dict is expected) yields "unknown", never an exception.

### 2.3 The five rows (honest pair, flag ON)

Per-side known tests (side i = products_data[i]; a side that is not a dict is not known):
- price: `price_is_showable(p.price)` (RG:213-224, imported from result_gate) AND `math.isfinite(float(p.price.amount))`.
- reviews: `rating_is_real(p)` (RG:239-242) AND `math.isfinite(p.rating)`.
- longevity: specs = p.specs is a dict; value v = specs.get("longevity") if it is "present" else specs.get("longevity_hours") (present = not None, not a bool, not a string whose strip().lower() is in RG NA_VALUES {"", "n/a", "na", "none", "unknown", "-"}); field f = the key that supplied v; CONFIDENCE RULE (R-X6-5 as refined, O1): `specs.get("_field_confidence")` is a dict AND it holds f with a str marker AND that marker is not in MODEL_KNOWLEDGE_MARKERS; HOURS: h = _extract_hours(v) (int/float that is not a bool, the first number of a string, else the phrase map), h finite and 0 < h <= _HONEST_LONGEVITY_MAX_HOURS. `digits` = v is a non-bool int/float, or a string containing a digit (re `\d`).
- projection: v = specs.get("sillage") (only that key; the projection alias of SS:3673 is not read: no extraction schema names it, ES:213-224); the same CONFIDENCE RULE on "sillage"; level = _HONEST_SILLAGE_LEVELS.get(" ".join(str(v).strip().lower().split())); every other word, a number, a phrase like "4+ hours" or "moderate to strong" -> not known.

_HONEST_SILLAGE_LEVELS (O9): level 1 {"intimate", "soft", "light", "weak", "close", "skin close", "skin-close"}; level 2 {"moderate", "medium", "average"}; level 3 {"strong", "heavy"}; level 4 {"enormous", "very strong", "very heavy", "huge", "beast mode"}.

Row state: known = both sides known; partial = exactly one side (known_side = its index, int); unknown = neither. value: known only when the price row AND the reviews row are known, else unknown (never partial).

Known rows:
| key | scores (int) | delta_text | confidence | other keys |
|---|---|---|---|---|
| price | `_dim_price(products_data)` unchanged | `_dim_price` unchanged ("<CUR> <d> less") | high | is_core True; basis "price" |
| reviews | `_dim_reviews(products_data)` unchanged | unchanged ("<d> stars higher" / "Same rating") | high | is_core True; basis "rating" |
| longevity | `int(round(40 + 60 * min(h, 12.0) / 12.0))` per side (8 h -> 80, 6 h -> 70, 9 h -> 85, 2 h -> 50) | ha == hb -> "Comparable"; both sides digits -> f"{_g(max)}h vs {_g(min)}h" with `_g(x) = f"{x:g}"` (so 7.5 prints 7.5, never int-truncated); else winner None -> "Comparable", else "Longer-lasting" | medium | label "Longevity", is_core False, basis "specs" |
| projection | _HONEST_LEVEL_SCORES[level] per side | same level -> "Comparable"; else "Stronger projection" (never the raw sillage texts) | medium | label "Projection", is_core False, basis "specs" |
| value | `_dim_value(products_data, is_cross_tier=...)` unchanged | unchanged | medium | is_core True, is_cross_tier as today; basis "price_rating" (O3) |

Every known row: `winner = _dim_winner(score_a, score_b, confidence)`, `state = "known"`; no caption_key, no data_insufficient, no known_side.

Partial and unknown rows (the placeholder shape both bundles already handle): `key`, `label` (Price / Reviews / Longevity / Projection / Value), `score_a = score_b = 75`, `delta_text` = "Price data unavailable" / "Limited review data" / "" / "" / "Limited value data", `confidence "low"`, `is_core` (True for price / reviews / value), `caption_key "limited_data"`, `winner None`, `state "partial" | "unknown"`, `basis` as for the known row, `known_side` (partial only), `data_insufficient True`.

Key order of each row (pinned): today's keys in today's order, then winner, state, basis, then (partial / unknown) known_side when partial, data_insufficient. Never emitted for an honest pair: character, versatility, presentation, wear_value, or any breakdown-derived row; `compute_scores`, the breakdown, `missing_data`, `dimension_winners` and the legacy `scoring` block are not read by these rows and not changed.

### 2.4 The readers of the rows (honest pair, flag ON; every other pair: today's code)

(a) Fact lines (`_build_factual_verdict(..., honest=True)`), with K = {row key: row} of the five rows:
- line1 price candidate only when K["price"].state == "known"; rating candidate only when K["reviews"].state == "known"; `_top_dim_candidate(..., known_only=True)` considers only rows with state "known" whose `winner` equals winner_index (O5); the review-density candidate is unchanged (it cites YouTube attention, not a bar, and needs ENABLE_YOUTUBE_SOURCE).
- line2: `_runner_up_dim_candidate(..., known_only=True)` considers only known rows whose `winner` equals 1 - winner_index; `_format_line2(..., price_known=K["price"] known, rating_known=K["reviews"] known)` skips the price fallback (RB:1113-1121) unless price_known and the rating fallback (RB:1122-1129) unless rating_known; the neutral fallback (RB:1131) and the sparse line1 fallback (RB:1175) are unchanged.
- So line1 / line2 never name a row that is not known (R-X6-11). The Home smart-pick caption of a NEW row copies line1 (HR:629-648) and needs no Home change.

(b) Tradeoffs (`honest_fragrance_tradeoffs`): map {"longevity_score": "longevity", "projection_score": "projection"}; a pair is kept only when BOTH its winner_wins.dimension and its loser_wins.dimension map to a spec row whose state is "known" AND the row's `winner` equals winner_index for the winner_wins entry and 1 - winner_index for the loser_wins entry (O4: the sentence never contradicts the bar); character, versatility, presentation, wear_value never qualify. No pair left -> []. Applied at the three SCS sites, so `overview.tradeoffs` (RB:1995), `deterministic_verdict_fields` (partial path SCS:9543, reconcile RB:343) and the stream reconcile (SCS:5611) all read the filtered list; with [] the deterministic key_tradeoff is "" (RB:238). compute_tradeoff_pairs and dimension_winners are unchanged.

(c) The AI scores summary (honest path of build_scores_summary): per product the rank line exactly as today (rank word and price tier, SS:3054-3064); then "    Per dimension: " + ", ".join(f"{display}: {word}") over the KNOWN spec rows in the order longevity, projection (display = DIMENSION_DISPLAY_NAMES of longevity_score / projection_score = "longevity" / "projection"), word = "stronger" when the row winner == i, "weaker" when == 1 - i, "comparable" when None (O8: the word comes from the honest row, not the breakdown); the line is OMITTED when no spec row is known; "  Score winner" as today; "  Dimension leaders: " + ", ".join(f"{display}={product_names[w] if w is not None else 'tie'}") over the known spec rows, omitted when none is known; the cross-tier note as today. Price, reviews and value rows are not added (today's summary carries no core-row line; adding one is a prompt change outside R-X6-13).

Exact honest summary, zero known rows (names A, B; A stronger overall; tiers t0, t1):
```
Product scores (deterministic, qualitative summary):
  A: stronger overall (price tier: t0)
  B: <rank word> (price tier: t1)
  Score winner: A (<clear lead | narrow lead>)
```
One known row (longevity, winner 0): after the A rank line `    Per dimension: longevity: stronger`, after the B rank line `    Per dimension: longevity: weaker`, and after the Score winner line `  Dimension leaders: longevity=A`. Two known rows: `longevity: stronger, projection: weaker` (etc.) and `longevity=A, projection=B`.

### 2.5 The wire table (per state; checked against M:24-43, contract_freeze.json:48 and every client reader of 1.5)

| State | Keys (type) | Client readers on both bundles |
|---|---|---|
| known price / reviews | key str, label str, score_a int, score_b int, delta_text str, confidence "high", is_core True, winner 0/1/None, state "known", basis str | a bar row (DB:82-88 keeps it), winner paints emerald (DB:263-269) |
| known value | as above + is_cross_tier bool, confidence "medium" | a bar row; is_cross_tier as today (DB:279) |
| known longevity / projection | as price, confidence "medium", is_core False | a bar row |
| partial | key, label, score_a 75, score_b 75, delta_text str, confidence "low", is_core bool, caption_key "limited_data", winner None, state "partial", basis str, known_side int 0/1, data_insufficient True | InsufficientRow (DB:68, DB:148-154); skipped by RU (RU:57); price/value removed when a price pends (RC:555-562) |
| unknown | as partial without known_side, state "unknown" | as partial |

Types never change for an existing key (score ints, confidence enum, winner 0/1/null). New keys: state (str), basis (str), known_side (int), and data_insufficient (bool) on fragrance rows; types.ts already declares data_insufficient and caption_key (SmartCompareApp/src/types/types.ts:411, :418); state / basis / known_side are ignored by both bundles.

### 2.6 The visible delta with the flag ON, per live bundle (code reading; not measured on a device)

The drawing files are byte-identical in the store app 683f56c0 and the OTA f1e20c39 (DB, RU, FactualVerdict.tsx; RC differs in line numbers only), so the two bundles show the same thing:

| Honest pair, flag ON | Store app 683f56c0 and OTA f1e20c39 |
|---|---|
| known row | a bar row as today; longevity caption "Nh vs Nh" (digits on both sides), "Longer-lasting" or "Comparable"; projection "Stronger projection" or "Comparable" |
| partial / unknown price or value while any price pends | removed by RC:555-562, as today |
| partial / unknown, any other row | the existing "Limited data" row (localized label + results.dimensions.limited_data), no bar, no winner; drawn BELOW the bars (DB:139-154), so the wire order is visible only once X4 ships |
| character, versatility, presentation | gone |
| no known row | five rows pass the RC:527 gate; no legend (DB:128); three to five "Limited data" rows |
| all five known | four bars + "See full breakdown" (HERO_CAP 4) |
| fact lines | never name a row that is not known (row C3 no longer reads "... leads on Versatility.") |
| runner-up card | only known rows the runner-up leads (RU:57 skips limited_data); key_tradeoff appears less often; the card hides when neither remains (RU:100) |
| Home caption (ENABLE_SMART_PICK_VERDICT_CAPTION ON) | new rows inherit the honest line1 |
| captions language | still English on both bundles (delta_text and the fact lines are English: X5 / R-A10) |
| non-fragrance or mixed pair | unchanged on both bundles |

### 2.7 Failure table

| Input | Outcome (flag ON, honest pair) |
|---|---|
| specs None / a list / a string | both spec rows unknown |
| _field_confidence missing, not a dict, no entry for the field, a non-str marker | that side not known |
| marker tier3_synthesis or training_data | that side not known |
| longevity "N/A" / "unknown" / "" / None / True | that side not known |
| hours NaN, inf, <= 0, > 72 | that side not known |
| sillage outside the level table | that side not known |
| price not a dict, amount None / NaN / <= 0, unavailable / estimated / source_method "estimated" or empty | that side not known |
| rating a bool / None / NaN / derived | that side not known |
| products_data shorter than 2 or not dicts | not an honest pair (today's path) |
| an exception anywhere in the new code | cannot happen by construction (total functions, pinned by a fuzz row); no new try/except and no new log |

### 2.8 Flag-OFF identity (the main invariant) and the deploy-visible delta

With ENABLE_HONEST_FRAGRANCE_BARS unset, "false", "0", "off", padded garbage: every byte of every response body (sync, streaming `scores` / `verdict` / `complete`, partial), every saved comparisons row, the verdict prompt (system and user text), the S81-18 verdict key, the Home caption, `overview.tradeoffs` (the SAME list object), `scoring_v2` and the legacy `scoring` block equal the base, for EVERY category; no log line is added. With the flag ON, a non-fragrance or mixed pair is byte-identical to OFF. The deploy with every flag at its default changes NO response byte, NO stored row, NO prompt byte, NO SSE frame and NO log line in production; the only change is the source and the CLAUDE.md text (section 8). Pinned by P1-P8 (section 5) with the FULL configuration of 1.8 and call recorders.

### 2.9 Test seams (production values in brackets)

`scoring_service.honest_fragrance_bars_enabled` [the env read], `scoring_service.canonicalize_category` [the ES function; a recorder proves OFF reads nothing], `scoring_service.build_honest_fragrance_dims` and `scoring_service.honest_fragrance_spec_rows` [recorders: 0 calls OFF], `_HONEST_LONGEVITY_CAP_HOURS` [12.0], `_HONEST_LONGEVITY_MAX_HOURS` [72.0], `_HONEST_SILLAGE_LEVELS`, `_HONEST_LEVEL_SCORES` [40/60/80/100], `structured_comparison_service.honest_fragrance_tradeoffs` [the SS function bound by name], `extraction_service.generate_comparison` as imported by SCS [recorder of `scores_summary`], `kb_serve.log_verdict_key` [recorder of `scores_summary`].

### 2.10 Logs and events

None. X6 adds no log line, no Sentry event and no metadata key (Q-15). No log arm of PR #399 is touched.

## 3. Change list (in the order GREEN applies it)

0. Byte copies (shutil.copyfile + sha256) of app/services/scoring_service.py, app/services/response_builder.py, app/services/structured_comparison_service.py and CLAUDE.md into <SP>/INC-X6/green/bytes/ before the first edit; sha-checked after any restore.
1. SS imports (after SS:12): `import math`; `from app.services.result_gate import MODEL_KNOWLEDGE_MARKERS, NA_VALUES, price_is_showable, rating_is_real` (RG imports only stdlib + text_sanitize: no cycle).
2. SS, a new block AFTER `_extract_hours` (after SS:3818) and BEFORE `build_dimensions_v2` (SS:3848): HONEST_FRAGRANCE_FLAG, honest_fragrance_bars_enabled, honest_fragrance_pair, HONEST_FRAGRANCE_ROWS, the four constants of 2.1, the per-side readers, honest_fragrance_spec_rows, build_honest_fragrance_dims, honest_fragrance_tradeoffs (sections 2.2-2.4). ASCII only; no `or <digit>` default on rating / price / warranty.
3. SS build_dimensions_v2 (SS:3848-3852): add `*, honest: Optional[bool] = None`; first statements: `if honest is None: honest = honest_fragrance_pair(products_data, category)`, `if honest: return build_honest_fragrance_dims(products_data, scoring_result)`. The rest of the body unchanged.
4. SS ScoringService.build_scores_summary (SS:3017): add `*, products_data=None, category=None`; after the early return (SS:3019-3020) branch to a private `_honest_scores_summary(scoring_result, product_names, products_data)` when `products_data is not None and honest_fragrance_pair(products_data, category)`; the rest unchanged.
5. RB _top_dim_candidate (RB:920) and _runner_up_dim_candidate (RB:953): add `*, known_only: bool = False`; when True, skip rows whose state is not "known" or whose winner is not the side's index (2.4 a).
6. RB _format_line2 (RB:1101): add `*, price_known: bool = True, rating_known: bool = True` guarding RB:1113-1121 and RB:1122-1129.
7. RB _build_factual_verdict (RB:1134): add `*, honest: bool = False`; when True, gate the price / rating candidates and pass known_only / price_known / rating_known (2.4 a); when False the body is today's.
8. RB _build_scoring_v2 (RB:1309-1314): `honest = honest_fragrance_pair(product_data, category)` (imported in the RB:11-18 block with build_dimensions_v2), then `build_dimensions_v2(product_data, scoring_result, category, honest=honest)` and `_build_factual_verdict(product_data, scoring_result, winner_index, dimensions, honest=honest)`.
9. SCS:63: add honest_fragrance_tradeoffs to the scoring_service import.
10. SCS:3850-3857 (partial), SCS:4750-4754 (sync), SCS:5598-5602 (stream): the filter line of 2.2 right after each call, inside the same block.
11. SCS:4653 and SCS:5504: pass `products_data=product_data, category=category_used`.
12. CLAUDE.md: the block of section 8 after the S81-04c block (CLAUDE.md:637-639) and before `## Tests` (CLAUDE.md:641) (or after the newest lane block in merge order at the final round).
13. New tests/test_inc_x6_honest_bars.py and tests/test_inc_x6_body_pins.py (RED round; frozen at the gate).

No other file. No client file, no migration, no requirements file, no extraction_service / image_routes / url_extraction_service / home_routes / result_gate / models edit.

## 4. Existing pins

### 4.1 Pins that change deliberately

None. No existing test sets ENABLE_HONEST_FRAGRANCE_BARS (a new name, 0 hits), every changed signature only gains keyword-only parameters whose defaults reproduce today, and the flag-OFF output is byte-identical. Any red existing node at GREEN is a defect, not an E-row. (If the orchestrator rules O2 the other way, no E-row follows either: the predicate only narrows ON behaviour.)

### 4.2 Pins that must stay green and unedited

- The digest fixture tests/fixtures/rubric_truth_flag_off_digests.json and its generator tests/fixtures/_gen_rubric_truth_flag_off_digests.py (record_payload calls build_dimensions_v2(p, result, cat) and build_scores_summary(result, names) positionally, its lines 279-290; 164 records x 3 states), read by tests/test_scoring_rubric_truth.py.
- The prompt render digests: tests/test_prompt_truth.py with tests/w4_11_prompt_digest_recorder.py:177 (fixed scores_summary) and tests/test_prompt_fence.py:696.
- The twelve files naming build_scores_summary (git grep at the base): the generator, test_arabic_verdict_output_w414, test_category_dimensions, test_fragrance_content_quality, test_m13_04_full_stream_deadline, test_prompt_truth, test_scoring_rubric_truth, test_scoring_service, test_streaming, test_tradeoffs_dedup_parity, test_w4_12_display_contract, test_winner_prose_reconciliation. A fragrance summary is embedded in test_fragrance_content_quality.py:36-49 (get_scoring_service().build_scores_summary(sr, ["A", "B"]), positional: the OFF path by construction); test_category_dimensions.py:255-264 is a supplements summary; test_scoring_service.py:558-572, test_prompt_truth.py:227 and test_tradeoffs_dedup_parity.py:367 / :565 / :611 / :623 call it positionally on non-fragrance or hand-built results; test_streaming, test_m13_04, test_w4_12_display_contract, test_winner_prose_reconciliation and test_arabic_verdict_output_w414 mock it with a fixed return_value. Every one stays green OFF and ON (no products_data is passed).
- The dims / model suites: tests/test_dimensions_builder.py, tests/test_scoring_v2_models.py, tests/test_scoring_dimensions_v2.py, tests/test_w4_12_display_contract.py, tests/test_tradeoffs_dedup_parity.py, tests/test_winner_prose_reconciliation.py, tests/test_scoring_calibration_bundle_c.py (the source regexes of 1.9).
- The source-scanning pins of the comm set (section 7): test_model_config.py, test_model_config_enforced.py, test_prompt_fence.py, test_u3c_store_false_pin.py, test_start_command.py, test_migration_index_predicate_immutability.py, test_openai_key_log_hygiene_s69.py, test_sentry_channels_u8d_unit.py, and the readers of SS / RB / SCS as source: test_scoring_calibration_bundle_c.py:138-160, test_m21_brand_dedup_and_verdict_copy.py:118-165, test_no_luxury_gate_in_tier3.py:28, test_s81_s15_registry_robots.py:762 (48 test files name an edited file by path; list in <SP>/INC-X6/spec/closure.json).
- The CLAUDE.md readers (38 test files contain "CLAUDE.md", closure.json; among them test_ci_gates.py and test_behavior_dimension_translation.py).

## 5. RED tests (hermetic; no network, no LLM, no database)

Rules for both files: import app.main FIRST in an autouse fixture (the dotenv guard), then monkeypatch; new symbols are read through a `_sym(module, name)` getattr helper and asserted callable, so a missing symbol at the base is an AssertionError, never an ImportError or AttributeError; product names synthetic; base literals recorded at the base in the RED round and written as base64 sha256 of the canonical JSON (sort_keys, ensure_ascii) under names without scanner keywords (e.g. `_BASE_BODY_SHA_B64`). FULL_CONFIG = every flag of 1.8 set "true" (the knobs WINNER_DIM_GAP_TOLERANCE / WINNER_PRICE_AUTHORITY_POINTS / WINNER_VALUE_WEIGHT_SCALE to valid non-default values, DEBUG_STAGE_TIMINGS and EVAL_CAPTURE_DEBUG unset because they are process-cached / debug-only) plus a synthetic credential NAME set to a run-time-built dummy; `scoring_service._BUNDLE_C_SCORING_FLAG` reset like the digest generator does. Shapes: C1 = two fragrance products, specs empty, both ratings derived, product 1 price pended; C2 = specs empty, real ratings 4.6 / 4.8, product 0 price pended; C3 = specs empty, ratings derived, product 0 price pended, a scoring_result whose breakdown carries versatility 50 (in product_0.missing_data) vs 30; D2F = the two products of tests/fixtures/comparison_baseline_d2_post_bucket_a__fragrances.json.

File tests/test_inc_x6_honest_bars.py (unit grain):

| # | Test | Assertion | At base | Satisfied by |
|---|---|---|---|---|
| R1 | test_r1_flag_reader_per_call | parametrized: "true", "1", "yes", "on", " TRUE ", "On" -> True; unset, "", "false", "0", "off", "no", "2", "tru", " " -> False; set and unset in one test flips the answer (no cache) | RED (symbol missing -> assert callable fails) | 2.1 |
| R2 | test_r2_predicate_reads_flag_first | flag OFF, FULL_CONFIG, a recorder on scoring_service.canonicalize_category: honest_fragrance_pair(D2F, "fragrances") is False and the recorder saw 0 calls; flag ON: True and >= 1 call | RED | 2.2 |
| R3 | test_r3_c1_five_rows_order | ON, C1: [d["key"] for d in build_dimensions_v2(C1, sr, "fragrances")] == ["price","reviews","longevity","projection","value"]; no character / versatility / presentation / wear_value | RED (base emits the core three in another order) | 2.3 |
| R4 | test_r4_c1_unknown_row_shape | ON, C1: longevity and projection rows == the exact dicts (75, 75, "", "low", False, "limited_data", None, "unknown", "specs", True) in the pinned key order; reviews unknown with "Limited review data" | RED | 2.3 |
| R5 | test_r5_c2_reviews_known | ON, C2: reviews row score 88 / 89, "0.2 stars higher", high, winner None, state known, basis rating, no data_insufficient; price partial known_side 1 (int, not bool); value unknown, no known_side | RED | 2.3 |
| R6 | test_r6_longevity_digits | ON: longevity "8 hours" vs "6-8 hours", both marker "snippet": known, 80 / 70, "8h vs 6h", winner 0, medium, is_core False; a 7.5 vs 8 pair prints "8h vs 7.5h" | RED | 2.3 |
| R7 | test_r7_longevity_phrase_d2f | ON, D2F: longevity known 85 / 80, "Longer-lasting", winner 0; projection unknown ("N/A" and "4+ hours") | RED | 2.3 |
| R8 | test_r8_no_map_no_entry_not_known | ON: numeric longevity on both sides with NO _field_confidence -> unknown; a map without a longevity entry -> unknown; a non-str marker -> unknown | RED | 2.3 O1 |
| R9 | test_r9_model_knowledge_partial | ON: side 0 marker "tier3_synthesis" (then "training_data"), side 1 "snippet" -> partial, known_side 1, winner None, 75 / 75, data_insufficient True | RED | 2.3 |
| R10 | test_r10_projection_levels_never_review | ON: "Heavy" vs "Intimate" -> 80 / 40 "Stronger projection" winner 0; "Moderate" vs " moderate " -> 60 / 60 "Comparable" winner None; "moderate to strong" -> unknown; ratings 5.0 vs 1.0 with no sillage -> projection unknown and longevity unknown (never the review score); no caption contains a raw sillage word | RED | 2.3 |
| R11 | test_r11_value_rule | ON: price known + reviews known -> value == _dim_value(...) plus state known, basis price_rating; price known + reviews unknown -> value unknown; price partial -> value unknown; value never carries known_side | RED | 2.3 |
| R12 | test_r12_price_uses_showable | ON, a direct call: both prices amount 40 / 55 with source_method "estimated" -> price unknown (today _dim_price computes); unavailable True on one side -> partial; NaN amount -> not known | RED | 2.3 |
| R13 | test_r13_no_default_reaches_a_bar | ON, C3: no row carries 50 from MISSING_SCORE; every row is known with source-derived ints or 75 / 75 limited_data; no versatility row | RED | 2.3 |
| R14 | test_r14_wire_types | ON over C1, C2, C3, D2F and six synthetic shapes: state in the three words; basis str; known_side present iff partial, type(int) and not bool; data_insufficient is True iff partial / unknown; winner None on partial / unknown; scores int in [40, 100] or 75 | RED | 2.5 |
| R15 | test_r15_fuzz_total | ON: 200 seeded shapes (None / list / str specs, bool / NaN / str ratings, odd price dicts, short lists) never raise and never yield a score <= 0 | RED (helper missing) | 2.7 |
| R16 | test_r16_fact_lines_c3 | ON, _build_scoring_v2(C3 ...): factual_verdict.line1 == "<A> edges ahead on the overall picture." and line2 == "<B> stays in the conversation as a close alternative."; neither contains "Versatility" | RED (base: "<A> leads on Versatility.") | 2.4 a |
| R17 | test_r17_fact_line_price_rating_gated | ON, direct _build_scoring_v2 with estimated prices on both sides and one derived rating: no "% cheaper" / "price premium" / "stars" / "lighter on the wallet" / "rates a touch higher" in line1 / line2 | RED | 2.4 a |
| R18 | test_r18_fact_lines_cite_known_rows | ON: winner 0 leads a known longevity row -> line1 "<A> leads on Longevity." when it is the largest candidate; the runner leads a known projection row -> line2 "<B> pulls ahead on Projection."; a known row with winner None is never cited | RED | 2.4 a, O5 |
| R19 | test_r19_tradeoffs_filter | ON: honest_fragrance_tradeoffs over C3's sweep list (loser_wins versatility_score) -> []; deterministic_verdict_fields(sr, names, []) key_tradeoff == ""; a longevity_score / projection_score pair with agreeing known rows kept; the same pair with the projection row won by the winner dropped | RED | 2.4 b, O4 |
| R20 | test_r20_summary_zero_one_two | ON: build_scores_summary(sr, names, products_data=..., category="fragrances") == the exact texts of 2.4 c for zero, one and two known rows (C1, a longevity-only pair, a longevity + projection pair) | RED | 2.4 c |
| R21 | test_r21_digest_fragrance_records | ON, the generator's 17 fragrance records (16 grid + 1 d2): v2 keys == HONEST_FRAGRANCE_ROWS order, every row has state; the summary computed WITH products_data contains none of "scent character", "versatility", "presentation", "value per wear" | RED | 2.3, 2.4 c |
| R22 | test_r22_recorders_on_off | recorders on build_honest_fragrance_dims and honest_fragrance_spec_rows: FULL_CONFIG + flag OFF -> 0 calls over the C1-C3 / D2F builds; ON -> >= 1 | RED | 2.2 |

File tests/test_inc_x6_body_pins.py (body grain, wiring, identity):

| # | Test | Assertion | At base | Satisfied by |
|---|---|---|---|---|
| P1 | test_p1_non_fragrance_on_equals_off | FULL_CONFIG; for an electronics, a makeup, an "other" pair and a mixed fragrance-vs-makeup pair: build_dimensions_v2, _build_scoring_v2 and build_scores_summary(..., products_data=..., category=...) ON == OFF (deep equal); no row carries state / basis / known_side / data_insufficient | PIN (green) | 2.8 |
| P2 | test_p2_digest_non_fragrance_on | ENABLE_HONEST_FRAGRANCE_BARS=true exported in-process for the generator's 147 non-fragrance records x 3 states: every digest equals tests/fixtures/rubric_truth_flag_off_digests.json | PIN | R-X6-19 (i) |
| P3 | test_p3_off_identity_full_config | flag unset, then "false", then " garbage ": FULL_CONFIG; for C1, C2, C3, D2F: build_dimensions_v2, _build_scoring_v2 (whole dict), build_scores_summary with AND without the new kwargs, and honest_fragrance_tradeoffs (when present; `is` the input) equal the base literals recorded in the RED round | PIN | 2.8 |
| P4 | test_p4_off_c3_fact_line_literal | flag OFF: C3 line1 == "<A> leads on Versatility." (the base behaviour, recorded) | PIN | 2.8 |
| P5 | test_p5_full_body_off_identity | flag OFF, FULL_CONFIG: build_comparison_response(...) over C1, C2, C3 (sync body) canonical sha == the base literal, after dropping only timestamp-like keys the builder stamps (named in the RED file, e.g. metadata elapsed fields fed as fixed inputs; never a substring compare); overview.tradeoffs is the input list | PIN | 2.8 |
| P6 | test_p6_scs_paths_off_identity | flag OFF, FULL_CONFIG: drive compare_from_text (sync) and compare_from_text_streaming with the real ScoringService and stubbed gather / generate_comparison (the harness pattern of tests/test_prescoring_showable_guard.py:783 and tests/test_streaming.py); recorders on generate_comparison (scores_summary kwarg) and kb_serve.log_verdict_key (scores_summary kwarg): the recorded summary, the sync body, the stream `scores` / `verdict` / `complete` frames and the hard-cap partial body equal the base literals | PIN | 2.8 |
| P7 | test_p7_model_guard | ON and OFF over every shape of both files: ScoringV2.model_validate({overall_score, win_margin, dimensions}) succeeds and Dimension.model_validate succeeds per row | PIN | 2.5, R-X6-18 |
| P8 | test_p8_home_caption_off | flag OFF, ENABLE_SMART_PICK_VERDICT_CAPTION ON: the HR caption over a saved C3 body built OFF equals the base literal | PIN | 2.8 |
| R23 | test_r23_scs_sync_on | flag ON, the P6 harness, fragrance C3-like pair: the recorded scores_summary has no "Per dimension" and no "Dimension leaders" line; body overview.tradeoffs == [] and overview.winner.key_tradeoff carries no non-known dim; scoring_v2.dimensions keys == HONEST_FRAGRANCE_ROWS | RED | 2.2, 2.4 |
| R24 | test_r24_scs_stream_and_partial_on | as R23 for the stream (`complete` and the `verdict` frame's tradeoff text) and the hard-cap partial body (deterministic key_tradeoff == "") | RED | 2.2, 2.4 |
| R25 | test_r25_scs_wiring_ast | ast over app/services/structured_comparison_service.py: each of the three compute_tradeoff_pairs assignments is followed, in the same block, by an assignment `tradeoffs = honest_fragrance_tradeoffs(tradeoffs, product_data, <category>, ...)`; both build_scores_summary calls pass products_data and category keywords; honest_fragrance_tradeoffs is imported from app.services.scoring_service | RED | 3 items 9-11 |
| R26 | test_r26_home_caption_on | flag ON + ENABLE_SMART_PICK_VERDICT_CAPTION ON: the HR caption over a saved C3 body built ON is the honest line1 (no "Versatility") | RED | 2.4 a |
| R27 | test_r27_rg_interplay | flag ON + ENABLE_RESULT_STATUS_METADATA ON: evidence_facts of the C2 body built ON has dims False (75 / 75 rows and the 88 / 89 reviews row are not discriminating); built OFF over the same C2 breakdown with the incident's 92 / 96 proxies, dims True (Q-8, stated in words) | RED | Q-8 |

Counts: RED rows R1-R27 = 27 (R1-R22 in the first file, R23-R27 in the second); PIN rows P1-P8 = 8. Every PIN row runs with FULL_CONFIG and at least one recorder or an identity (`is`) check, so a "not gated" mutant is killed (ruling B1). Runner (DEFERRED TO RED): `PYTHONIOENCODING=utf-8 C:/Users/SynAckITPC/Documents/AI/.venv-qaren/Scripts/python.exe <SP>/harness/pyt.py --bound 600 --tag inc-x6-red --log <SP>/INC-X6/red/red.log --cwd C:/Users/SynAckITPC/Documents/AI/sc-inc-x6 -- tests/test_inc_x6_honest_bars.py tests/test_inc_x6_body_pins.py`. At the base the RED rows must fail on AssertionError ONLY and the PIN rows must pass (read the log for ImportError / AttributeError / fixture errors: each is a RED-file defect).

## 6. Mutation table (GREEN or the adversary; each on a byte copy, one exact-string edit that matches once, the killing rows via pyt.py -k with bound 600, restore, sha256 compare; the mutation lock .qa-mutation.lock first)

| # | Mutant | Killed by |
|---|---|---|
| M1 | honest_fragrance_bars_enabled returns True | P3 (the OFF fragrance identity) |
| M2 | the reader drops .strip() | R1 (" TRUE ") |
| M3 | the reader drops .lower() | R1 ("On") |
| M4 | the reader is cached at import | R1 (set / unset flip) |
| M5 | honest_fragrance_pair checks the flag AFTER canonicalize_category | R2 |
| M6 | the predicate drops the "fragrances" test (any same-category pair) | P1 |
| M7 | the predicate drops cat_a == cat_b (mixed pairs honest) | P1 (mixed pair) |
| M8 | longevity falls back to the review score when specs are missing | R10, R4 |
| M9 | projection reads the review score | R10 |
| M10 | the confidence rule uses _tier3_fields (map optional) | R8 |
| M11 | the field-entry requirement dropped (map present suffices) | R8 |
| M12 | MODEL_KNOWLEDGE_MARKERS exclusion dropped | R9 |
| M13 | phrase hours print "9h vs 8h" | R7 |
| M14 | int() truncation of hours restored | R6 (7.5) |
| M15 | projection caption prints the raw sillage texts | R10 |
| M16 | a partial row takes _dim_winner on 75 / 75 or keeps a source score | R9, R14 |
| M17 | data_insufficient omitted | R4, R14 |
| M18 | known_side emitted as a bool or swapped | R5, R14 |
| M19 | value partial when only price is known | R11 |
| M20 | the price side test uses _safe_price_amount (no showable check) | R12 |
| M21 | the isfinite guard dropped | R12 (NaN), R15 |
| M22 | the character row still emitted | R3 |
| M23 | value before longevity (old order) | R3 |
| M24 | _top_dim_candidate ignores state | R16 |
| M25 | the winner-equals-side requirement dropped in the fact lines | R18 |
| M26 | the price candidate not gated on the price row | R17 |
| M27 | the line2 rating fallback not gated | R17 |
| M28 | the tradeoff filter keeps any dim | R19, R23 |
| M29 | the tradeoff filter ignores the row direction | R19 |
| M30 | honest_fragrance_tradeoffs returns list(tradeoffs) OFF | P3 (`is`) |
| M31 | the summary lists unknown dims ("comparable") | R20 |
| M32 | the summary keeps the old breakdown words for known rows | R20 (one known row, breakdown disagreeing) |
| M33 | the summary honest path runs whenever products_data is passed, flag ignored | P3 (summary with kwargs) |
| M34 | the stream tradeoff site not filtered | R24, R25 |
| M35 | the sync summary site does not pass products_data | R23, R25 |
| M36 | _build_scoring_v2 does not pass honest to _build_factual_verdict | R16 |
| M37 | the honest rows built for a non-fragrance pair carry state keys | P1 |

37 mutants; each must be KILLED by an assertion failure (an import or collection error is not a kill). An equivalent survivor is reported for a ruling.

## 7. Comm set and gates for GREEN (cheapest first; every run DEFERRED TO RED / GREEN, none ran in this round)

Comm set by the union rule (computed in this round by <SP>/INC-X6/tools/closure.py over `git show 6b909e0a:<path>`; output <SP>/INC-X6/spec/closure.json and comm_set.txt, sha256 of the sorted list 2f621457036deb4af9bfa76a57b53195718f87b5996c431378a4e75b554acec6):
- the importer closure of SS, RB and SCS to a fixpoint over app/ = 75 modules (app.main among them, so every test that imports app.main is in);
- the tests that reference a closure module: 673; the tests naming an edited symbol: 293; the tests naming an edited file by path: 48; the source-scanning readers (getsource / __file__ / ast.parse / glob / rglob / listdir / scandir / read_text with an app path): 106; the CLAUDE.md readers (CLAUDE.md changes): 38; the named pins (test_model_config, test_model_config_enforced, test_prompt_fence, test_u3c_store_false_pin, test_start_command, test_migration_index_predicate_immutability, test_openai_key_log_hygiene_s69, test_sentry_channels_u8d_unit, test_ci_gates, test_behavior_dimension_translation): all present;
- MINUS the four pre-commit hook files (test_precommit_hook.py, _round2, _phase_b, _phase_b_round2; X6 edits no .githooks);
- UNION = 681 of the 768 test_*.py files (+ the two new RED files at GREEN = 683). No edited test-support helper (none is edited). No migration / manifest / legal / client file changes, so no migration, manifest or SmartCompareApp-scanning reader joins beyond the above.

| # | Gate | Command (DEFERRED) | Pass rule |
|---|---|---|---|
| G1 | syntax + lint | `<venv python> -m py_compile app/services/scoring_service.py app/services/response_builder.py app/services/structured_comparison_service.py tests/test_inc_x6_honest_bars.py tests/test_inc_x6_body_pins.py`; `<venv python> -m ruff check --select E9,F63,F7,F82 --no-cache <same files>` | clean |
| G2 | hygiene | bytes > 127 in every ADDED line = 0; `git diff --stat` shows no whole-file diff (CRLF kept); the added-line sweep (no @gmail, +973, 8-digit runs, key shapes); no new constant name with a scanner keyword; no `or <digit>` rating / price / warranty default in SS | clean |
| G3 | RED + PIN | `... pyt.py --bound 600 --tag inc-x6-green-red --log <SP>/INC-X6/green/red.log --cwd <W> -- tests/test_inc_x6_honest_bars.py tests/test_inc_x6_body_pins.py` | all pass |
| G4 | touched suites | the 1.10 command 1 at HEAD, tag inc-x6-green-touch | FAILED set equal to the base set |
| G5 | prompt and source pins | the 1.10 command 2 at HEAD + tests/test_scoring_calibration_bundle_c.py tests/test_m21_brand_dedup_and_verdict_copy.py tests/test_no_luxury_gate_in_tier3.py tests/test_s81_s15_registry_robots.py tests/test_hermeticity_pins.py, tag inc-x6-green-pins | equal to base (the two cold-tiktoken ERROR nodes identical) |
| G6 | the digest fixture | `... -- tests/test_scoring_rubric_truth.py`, tag inc-x6-green-digest | green, fixture unedited |
| G7 | CLAUDE.md readers | `... -- tests/test_ci_gates.py tests/test_behavior_dimension_translation.py`, tag inc-x6-green-claude | green |
| G8 | the comm set | 28 chunks of <= 25 files from comm_set.txt (+ the RED files), bound 1200 each, tags inc-x6-cNN, base record from <SP>/harness/base_records/6b909e0a.../<set-sha>.txt (computed at RED, LC-6) | `comm -13` of the sorted FAILED node sets EMPTY; a branch-only failure re-run against base once |
| G9 | client fences by path | from <W>/SmartCompareApp through the orchestrator's junction, after the H5 jest probe: `timeout -k 15 600 node node_modules/jest/bin/jest.js --ci __tests__/brand/inAppMark.u4c.test.ts __tests__/clientTruth/medicalNote.s74.test.tsx __tests__/clientTruth/privacyManifest.s74.test.ts __tests__/clientTruth/shareTruth.s74.test.tsx __tests__/clipboardFallbackService.test.ts __tests__/config/nativeBundle.w37.test.ts __tests__/DimensionBars.perCategory.test.tsx __tests__/honestCounts.s69.test.tsx __tests__/landing.domain.s76.test.ts __tests__/navigation/linking.w315.test.ts __tests__/onboarding/step05Trust.s69.test.tsx __tests__/playInstallReferrerService.test.ts __tests__/playInstallReferrerService.edges.test.ts __tests__/ResultsScreen.timeout.test.tsx` | equal to base (the 4 nativeBundle.w37 drift nodes are the accepted base failures). Measured in this round: none of the fourteen reads SS, RB, SCS or CLAUDE.md (their repo-path reads are extraction_service.py, referral_service.py, robots_eval.py, sitemap_discovery_service.py, scripts/render_myez_icons.py, docs/ and .github/ files), so no fence literal moves; they run because the footprint touches app/ (the lane rule) |
| G10 | CI-order set | `pytest tests/ -m "not (live_unit or live_db or integration)" --ignore=tests/test_integration.py` with the .pre_impl_failures deselects (.github/workflows/ci.yml:115-126), through pyt.py in the final round only if the orchestrator rules the comm set insufficient | CI is the arbiter |

The pre-commit hook files run in their own call only if .githooks changes (it does not).

## 8. The CLAUDE.md block, its anchor, the owner steps

Anchor: a new paragraph after the S81-04c block (CLAUDE.md:637-639 at the base) and before `## Tests` (CLAUDE.md:641), the house position of the newest unit block; at the final round it goes after the newest lane block in merge order (e.g. MON1 / G-INC-1 if they merged first). ASCII text, CRLF in the working copy:

```
**INCIDENT LANE unit (INC-X6 HONEST-BARS, 2026-11-12; ONE new flag `ENABLE_HONEST_FRAGRANCE_BARS`, default OFF, read PER CALL; a new name, so unset in production by construction; FOCUS (the result screen of both live bundles once flipped): two adversaries; no migration, no client file; spec .qa-s80/INC-X6_UNIT_SPEC.md of the unit worktree):**
- `ENABLE_HONEST_FRAGRANCE_BARS` (`app/services/scoring_service.py::honest_fragrance_bars_enabled`, read as the first statement of `honest_fragrance_pair`; a pair is honest exactly when build_dimensions_v2 would route it to the fragrance dims). **Effect ON, fragrance pairs only:** `scoring_v2.dimensions` is exactly five rows in the order price, reviews, longevity, projection, value; a row is `state` "known" only from a real source for that dimension (price: `result_gate.price_is_showable` on both sides; reviews: `rating_is_real`; longevity: specs `longevity` / `longevity_hours` hours, projection: specs `sillage` on a four-level table, each only when the specs' `_field_confidence` holds that field with a marker outside MODEL_KNOWLEDGE_MARKERS; value: price and reviews known), else "partial" (`known_side`) or "unknown": the existing 75/75 `caption_key: "limited_data"` placeholder plus `data_insufficient: true`, so both live bundles draw their existing "Limited data" row; character, versatility, presentation and wear_value are not emitted; `factual_verdict` line1 / line2 cite only known rows; the tradeoff list (`overview.tradeoffs`, the deterministic key_tradeoff) keeps only pairs on known longevity / projection rows in the bar's direction; the verdict prompt's scores summary lists only known longevity / projection rows. The crown, `compute_scores`, the breakdown, `dimension_winners`, the legacy `scoring` block, personalization and every non-fragrance or mixed pair are unchanged. **Flag OFF:** byte-identical bodies, rows, SSE frames, prompt bytes and verdict key (pinned with the full configuration). Stated limits: the spec's section 9 (L-CROWN, L-NF1, L-HOME, L-HOME-AR, L-AI-PROSE, L-LEGACY, L-CONF, L-OLD, L-ORDER, L-TIE, L-SSE, L-RG50, L-READS).
- **Owner steps (names only; a dated ledger line per step):** none to merge. The flip of `ENABLE_HONEST_FRAGRANCE_BARS` on `web`, in its own canary window, set by the relay on the owner's yes, after the Claude switch works and the flip pause lifts; then the phone proof (the spec's section 8b). Merged is not proven until the phone shows it.
```

Owner steps (names only): the flip of ENABLE_HONEST_FRAGRANCE_BARS on the web service in its own window (relay, on the owner's yes; after the Claude switch, Q16, and after the H2 flip pause lifts); the phone proof of 8b with the relay reading the saved rows. Nothing else: no credential, no migration, no other variable, no OTA.

## 8b. PROOF ON THE PHONE (header H6; the brief section 4; IR:105)

After the merge the unit is "merged, NOT yet proven". The proof runs after the flip, needs NO AI text, and works best while specs are still empty. Free tier: three comparisons fit one day (IR:83).
1. Repeat "Lancome La Vie Est Belle EDP vs YSL Libre EDP" (row C2 shape) with specs still empty. Must be visible: NO "Longer-lasting" bar, NO "Stronger projection" bar, NO "Better presented" bar; the Longevity and Projection rows read "Limited data" (on the Arabic UI the existing results.dimensions.limited_data string), BELOW the bars on today's apps; positive control in the same screenshot: the Reviews bar with both real ratings (IR:155: 4.8 with 6,600 and 4.6 with 85). If either rating is derived on that run, Reviews also reads "Limited data", the control is missing, and the run is INCONCLUSIVE, not passed.
2. One golden pair never compared before: "Dior Sauvage EDP vs Chanel Bleu de Chanel EDP" (pair 4), or, if compared since, "Maison Francis Kurkdjian Baccarat Rouge 540 EDP vs Lattafa Khamrah EDP" (pair 5). Same checks: no bar from stars or counts; unknown rows read "Limited data"; any drawn bar is one of the five keys.
3. Optional (quota permitting): "Armani Acqua di Gio Profumo vs Versace Eros EDP" (row C3 shape): no "More versatile" bar, and the fact line does not say "leads on Versatility".
Each screenshot records the row id, the UTC time and the bundle (store app or updated app). The store bundle draws the same rows by construction (DB, RU, FactualVerdict byte-identical): CODE READING unless a device still on the store bundle is used; the report says which.

BACKING CHECK in each saved row: `scoring_v2.dimensions` keys exactly price, reviews, longevity, projection, value in that order; every row carries `state` (only a flag-ON build writes it: no body cache exists and History serves the stored body, Q-13); longevity and projection `state` "unknown", `caption_key` "limited_data", `data_insufficient` true, `winner` null, 75 / 75; character, versatility, presentation, wear_value ABSENT; reviews `state` "known" for proof 1 with both ratings real (`rating_derived` absent or false on both products); `factual_verdict.line1` / `.line2` name no row that is not known; `overview.winner.key_tradeoff` and `overview.tradeoffs` name no dim that is not known; `specs.products[i].specs` empty or without a usable `_field_confidence` entry for longevity / sillage (explains the unknown rows). `metadata.partial` true makes a row NOT evidence.

NOT provable in production: the crown is unchanged (a HERMETIC before / after on the saved row's inputs, stated in words, not the production proof, H6 c); the flag-OFF byte identity (the pins are the evidence; the phone cannot see bytes); the AI-summary change (no AI text until the Claude switch). Second check after the Claude switch (not a regression): a longevity or projection BAR drawn from real specs ("8h vs 6h" or "Stronger projection") is CORRECT when that row's specs carry the confidence entry with a non-model-knowledge marker. Suites and gates are necessary and are never the proof.

## 9. Stated limits

| Id | Limit |
|---|---|
| L-CROWN | The crown (winner_index, TopMatchBadge, the "edges ahead" reason and line1 fallback, the summary's rank word and "Score winner") still rests on the overall score that includes MISSING_SCORE 50s and the proxies (PI part c consequence 5; row C1 margin 1.4 from wear_value 75 vs a default 50). X6 does not move it (Q5). |
| L-NF1 | Non-fragrance and mixed pairs keep today's default-50 mechanics and proxy rows, flag ON or OFF (Q14). |
| L-HOME | Home captions of rows saved before the flip keep their old line1 while those rows stay on Home; the smart-pick choice still reads the legacy dimension_winners (HR:576-590). |
| L-HOME-AR | Captions and fact lines stay English on both live apps until X5 / R-A10. |
| L-AI-PROSE | After the Claude switch the AI's own prose (reason, its key_tradeoff, pros / cons) can still mention longevity or projection; X6 changes only the summary it is given. |
| L-LEGACY | The legacy `scoring` block (scores, breakdown, dimension_winners, RB:2070-2077) and the SSE `scores` frame (SCS:5510-5516) keep the proxy values; neither bundle renders dimension_winners, and no screen consumes the stream callbacks (PD2 section 1). |
| L-CONF | Real longevity / projection bars need the `_field_confidence` entry (O1); how many cached and KB specs carry it in production is UNVERIFIED; smart_fallback and tier2_fallback markers count as retrieved by the recorded R-A4 ruling (RG:70-72), although both are model fills over retrieved text (O10). |
| L-OLD | Rows saved before the flip keep their stored scoring_v2: History serves the stored body (history_routes.py:138-168), so an old row never shows the new rows. |
| L-ORDER | On today's apps the unknown rows are drawn below the known bars (DB:139-154): the fixed order is a wire property until X4 renders by key. |
| L-TIE | A known row with winner null (a margin under 3) is still painted by the client's score heuristic (DB:263-269) until X4. |
| L-RG50 | A known longevity of exactly 2 h scores 50 and reads non-discriminating under the strict result-gate reading (RG:315-316); harmless while ENABLE_RESULT_STATUS_METADATA / ENABLE_RESULT_GATE are OFF on web. |
| L-READS | The flag is read in several places per request (the SCS summary site, the tradeoff site, the RB build); a flip inside one request could split them for that request only (the house per-call rule accepts this). |
| L-URL | The link-compare body has no scoring_v2 (PD2 section 1 citing url_extraction_service.py:1500-1509; that cite was not re-read in this round): untouched. |

## 10. Out of scope

X5 (ENABLE_RESULT_TEXT_CODES, delta_msg, the Arabic by-value unit); X7 (ENABLE_DIFFERENCES_LIST, ENABLE_DETAILS_LINE_FILL); X4 (the client fixed page, results.bars.knownForOne) and every client file; the crown and the scoring weights (Q5); compute_scores, the breakdown, personalization, the cohort, the value badge; X1 / X2 / X8 / X9 / X10; every flag flip; the S81-04c log arms; the History screen.

## 11. Open questions for the orchestrator, and the answers to the brief questions

### 11.1 Open questions (each with the spec's default and the reason it beats the alternative)

- O1 (R-X6-5 refined, narrower): a spec value counts only when `_field_confidence` holds THAT field with a str marker outside MODEL_KNOWLEDGE_MARKERS; a map that lacks the field does not count. Reason: the extraction prompt demands a `<field>_source` for every field (ES:660, ES:765), so a missing entry is an anomaly, and a wrong "known" is worse than one more "Limited data" row. Alternative (the brief's literal wording: map present and field not marked) would count an unmarked field.
- O2 (R-X6-1): the honest predicate is today's routing test (cat_a == cat_b and canonical category == "fragrances", SS:3877-3881), not "all three canonicalize to fragrances" (the brief's parenthetical). Reason: a pair whose products both canonicalize to "other" with the pair category "fragrances" gets the fragrance proxy dims TODAY; the stricter test would leave those proxies on screen with the flag ON.
- O3: value rows carry basis "price_rating" (a fourth word beyond the brief's price / rating / specs). Reason: value is derived from both; neither bundle reads basis; X5 / X4 can key on it.
- O4 (R-X6-12 narrowed): a tradeoff pair is kept only when each entry's known row is won in the entry's direction. Reason: "{loser} stays competitive on longevity" next to a longevity bar won by the winner contradicts the screen; dimension_winners is built from the breakdown blend (spec 0.6 + review 0.4, SS:2352), not from the honest row.
- O5 (R-X6-11 narrowed): a known row is cited in line1 / line2 only when its winner is that side (a margin >= 3). Reason: the fact line and the bar's own winner agree; a 1-point lead is a tie by the house tie rule (SS:3189).
- O6: bar lengths: longevity `40 + 60 * min(h, 12) / 12` rounded; projection 40 / 60 / 80 / 100. Reason: ints in [40, 100], never 0 (DB:95-111), monotonic, and the tie margin 3 separates one hour at 12 h scale (5 points). Accepts L-RG50.
- O7: the fixed order is visible only on the wire on today's apps (L-ORDER); the spec does not try to reorder the client.
- O8: the summary word of a known row comes from the honest row winner, not the breakdown. Reason: the breakdown longevity is the spec / review blend; the AI must hear the same answer the bar shows.
- O9: the sillage table of 2.3 (19 words, exact match after strip / lower / whitespace collapse). Reason: the prompt rule names Intimate / Moderate / Heavy / Enormous (ES:467) and the schema comment soft / moderate / strong (ES:219); anything else (ranges, numbers) is not a level.
- O10: smart_fallback and tier2_fallback markers count (the recorded R-A4 F1-3 reading, RG:70-72). The owner may rule them model knowledge; the change would be one set.

### 11.2 Answers to the brief questions (file:line at 6b909e0a)

- Q-1 THE PREDICATE AND THE DATA. One pure predicate `honest_fragrance_pair(products_data, category)` in SS (2.2), flag first. RB:1309-1314: `_build_scoring_v2` reads it once from (product_data, category_used) (RB:2079-2080) and passes `honest=` to build_dimensions_v2 and _build_factual_verdict. The three tradeoff sites (SCS:3850, SCS:4750, SCS:5598) call `honest_fragrance_tradeoffs(tradeoffs, product_data, category, winner_index)` which reads the predicate itself; the partial path (SCS:9543) and the reconcile chokepoint (RB:343) consume the already-filtered list. The two summary sites (SCS:4653, SCS:5504) pass `products_data=product_data, category=category_used`; they run BEFORE the response builder, on the same product_data object (the pre-chokepoint prices do not matter: the summary reads only the spec rows). Fields present at each site: specs with `_field_confidence` (lifted at SCS:3497-3538 and the fill stages SCS:6590-6661; shipped in the body at RB:2004), price dicts (pended by the RB chokepoint only inside build_comparison_response, RB:1636-1765), `rating_derived` (set at RB:1612-1621, before scoring_v2). Every flag-OFF call is byte-identical because each new parameter is keyword-only with a default that runs today's code (2.2).
- Q-2 THE KNOWN TESTS. Section 2.3: price = price_is_showable + isfinite; reviews = rating_is_real + isfinite; longevity = present value of longevity / longevity_hours, the confidence entry rule, hours via _extract_hours (numeric first, SS:3811-3813; the phrase map SS:3790-3797 only without a digit), 0 < h <= 72; projection = sillage on the 4-level table of O9, every unmapped word not known. Vocabulary actually produced: the prompt rule Intimate / Moderate / Heavy / Enormous (ES:467), example "Heavy" (ES:527-528), schema comment soft / moderate / strong (ES:219); KB serve copies cited values as is (kb_serve.py:308-317, LICENCE_FIELDS kb_serve.py:55); the recorded fixture holds "N/A" and "4+ hours" (both not known). Bar lengths: O6 (never 0). An estimated price with an amount reaches the builder only through the chokepoint's except arm (RB:1764-1765) or a direct build_dimensions_v2 call; price_is_showable covers both.
- Q-3 THE CONFIDENCE MAP. Producers: _clean_specs from `<field>_source` (SCS:3503-3538: snippet / training_data / the raw marker), smart_fallback (SCS:6597), tier2_fallback (SCS:6630), tier3_synthesis (SCS:6661), kb_cited for every KB field (kb_serve.py:315). Cached specs are re-cached from the CLEANED dict (SCS:3539-3545 comment), so they carry the map when the extraction emitted markers. Therefore a real longevity / projection bar CAN appear after the Claude switch when the extraction cites a snippet for longevity / sillage (or a smart_fallback / tier2 fill lands); today (every LLM call 401) specs are empty and both rows are unknown. Production share UNVERIFIED (no production read in this lane; PD2 2.2 rule 5).
- Q-4 THE WIRE TABLE. Section 2.5, checked against M:24-43 (int scores, the confidence enum, banned words), M:51-69 (<= 8 rows, core keys exactly price / reviews / value), contract_freeze.json:48 (the client reads key, label, score_a, score_b, delta_text, confidence, data_insufficient, caption_key, winner, is_cross_tier, value_match_a/b), and the readers DB:68, :82-88, :128, :148-154, :263-269, RU:50-63, :100, RC:212, :527, :555-562, types.ts:411, :418.
- Q-5 THE RENDER TABLE PER GOLDEN PAIR (code reading of both bundles over the incident rows of T1_trace.md section 5: specs empty; C1 / C3 ratings derived; C2 ratings real 4.6 / 4.8; one price pended in each of C1, C2, C3 by the size reconcile, so RC:555-562 removes price and value in all three; pairs 4 and 5 have no incident row, so their row is the rule, not a measurement):

| Pair | Flag OFF today (both bundles) | Flag ON (both bundles) |
|---|---|---|
| 1 Aventus vs Layton (C1) | bars: none (core rows are hidden placeholders, no category row: all six missing on both sides); no legend; fact line1 from the remaining candidates (price / rating: none, so "<A> edges ahead on the overall picture.") | Reviews, Longevity, Projection as three "Limited data" rows; no bar, no legend; fact lines unchanged in kind (no known row to cite); runner-up card as today (no row) |
| 2 La Vie Est Belle vs Libre (C2) | bars: Reviews 88 / 89 "0.2 stars higher", Longevity 92 / 96 "Longer-lasting", Projection 92 / 96 "Stronger projection", Presentation 64.3 / 100 "Better presented" (proxies); runner-up card can list longevity / projection / presentation | Reviews bar 88 / 89 (the positive control); Longevity and Projection "Limited data"; no Presentation; fact lines cite no proxy; runner-up card: reviews only if the runner-up leads it, else hidden unless key_tradeoff prose exists |
| 3 Acqua di Gio Profumo vs Eros (C3) | bars: Versatility 50 / 30 "More versatile" (server winner null, client paints Armani from the default 50); line1 "<Armani> leads on Versatility." | Reviews, Longevity, Projection "Limited data"; no Versatility; line1 "<Armani> edges ahead on the overall picture."; line2 "<Versace> stays in the conversation as a close alternative." |
| 4 Sauvage vs Bleu de Chanel | by the rule: proxies when specs are empty | by the rule: five rows on the wire, every row without a real source "Limited data"; price / value removed if a price pends |
| 5 BR540 vs Khamrah | as 4 | as 4 |

- Q-6 THE TRADEOFF FILTER. Shared helper `honest_fragrance_tradeoffs` in SS, applied at SCS:3850, SCS:4750, SCS:5598 right after compute_tradeoff_pairs (2.4 b). R1-R3 shapes ON: C1 (all dims missing on both sides, no margins) -> [] ON and OFF; C2 (loser leads only proxies; any F4.2 pick is a proxy) -> [] ON, OFF the base list; C3 (the sweep fallback can pick versatility_score) -> [] ON. key_tradeoff ON = "" on the deterministic paths (partial, reconcile); on the normal production path today the comparison carries no key_tradeoff (the verdict 401 body, T1_trace.md:168), so overview.winner.key_tradeoff is "" ON and OFF there. E-rows of tests/test_tradeoffs_dedup_parity.py and tests/test_winner_prose_reconciliation.py: none (neither sets the new flag; both call compute_tradeoff_pairs / build_scores_summary positionally or through a MagicMock whose return_value the OFF helper returns as the same object).
- Q-7 THE SUMMARY BYTES. Exact ON texts in 2.4 c (zero / one / two known rows); OFF identical for every category (P3, P1, the digest fixture P2 / G6). Of the twelve files: only test_fragrance_content_quality.py:36-49 embeds a fragrance summary (positional call: OFF path); the rest are non-fragrance or mocked (section 4.2). Each stays green OFF.
- Q-8 THE RESULT-STATUS INTERPLAY. dim_is_discriminating (RG:299-321) is False for every partial / unknown row (caption_key limited_data, margin 0). Under ENABLE_RESULT_STATUS_METADATA and / or ENABLE_RESULT_GATE (both OFF on web) the "dims" fact (RG:410) of a fragrance body ON is True only through a known row with a margin >= 3 (strict: not low, no 50): C2 drops from dims True (the 92 / 96 proxies, margin 4, longevity not in missing_data) to dims False, so data_coverage falls by one; C2 keeps its ratings fact (both real), so it stays coverage >= 1; C1 and C3 are unchanged (no discriminating row in either state; C3's 50 is refused by the strict reading). A later flip of either flag inherits this (R27).
- Q-9 THE HOME CAPTION. HR:629-648 copies the saved line1 under ENABLE_SMART_PICK_VERDICT_CAPTION (its production value UNVERIFIED). C3 shape: OFF "<Armani> leads on Versatility." -> ON "<Armani> edges ahead on the overall picture." (R26 / P8). Rows saved before the flip keep their line1 (L-HOME).
- Q-10 FLAG-OFF IDENTITY WITH THE FULL CONFIGURATION. The list is 1.8 (the SS, RB, RG, HR names plus the module flags RB reaches and the two SCS prompt-side flags), including ENABLE_VALUE_DIM_PARTIAL_SIGNAL and ENABLE_TIE_IS_NOT_MISSING (SS:2813), ENABLE_WINNER_PROSE_RECONCILE (RB:171-182), ENABLE_HONEST_PARTIAL_SCORING, ENABLE_SMART_PICK_VERDICT_CAPTION and ENABLE_VERDICT_CACHE_LOG. Identity rows: P3 (function grain), P5 (the sync body), P6 (the sync body, the stream scores / verdict / complete frames, the hard-cap partial body, the recorded verdict-prompt summary and the log_verdict_key input), P8 (Home), P2 (the 147 non-fragrance digest records with the flag ON).
- Q-11 THE E-ROW TABLE. None (section 4.1). The files that read fragrance dims, captions, fact lines, tradeoffs or the summary (test_dimensions_builder, test_scoring_v2_models, test_category_dimensions, test_fragrance_content_quality, test_scoring_dimensions_v2, test_w4_12_display_contract and the Q-7 files) never set the new flag, so none moves; the source-scanning pins are in 4.2 / G5.
- Q-12 THE CLIENT FENCES BY PATH. X6 moves no literal any of the fourteen fences reads: their repo-path reads are app/services/extraction_service.py (medicalNote.s74), app/services/referral_service.py (shareTruth.s74), app/services/robots_eval.py and sitemap_discovery_service.py (landing.domain.s76), scripts/render_myez_icons.py, docs/ and .github/ files (git grep of readFileSync / path.join / path.resolve under SmartCompareApp/__tests__); DimensionBars.perCategory reads its own JSON fixtures. They still run at GREEN by path (G9) because the footprint touches app/.
- Q-13 NO STALE BODY. No whole-body cache serves a compare: get_comparison_cache / set_comparison_cache (cache_service.py:777-785) have no caller under app/; metadata.cache_hit is the price-cache signal (RB:49-80); the S81-18 verdict key is a log / seed (SCS:4668, SCS:4689); History returns the stored full_response (history_routes.py:138-168). So `state` on every dim of a saved row proves a flag-ON build.
- Q-14 THE CLAUDE.md BLOCK. Section 8 (text and anchor: after the S81-04c block CLAUDE.md:637-639, before `## Tests` CLAUDE.md:641).
- Q-15 THE LOGS. None proposed (2.10); no product name can reach a log because no log is added.

## Not done in this spec

- No pytest, jest, tsc or eslint ran (READ-ONLY round, H5 c): the base pass state (1.10), the comm-set base record, the RED / PIN verdicts and every mutant are DEFERRED TO RED / GREEN with their commands.
- The base literals of P3 / P4 / P5 / P6 / P8 are recorded by the RED round at the base, not here.
- Not measured: the production share of specs carrying a usable `_field_confidence` entry (L-CONF), the production value of ENABLE_SMART_PICK_VERDICT_CAPTION, any device rendering (section 2.6 is code reading), url_extraction_service.py:1500-1509 (a PD2 cite, not re-read).
- Nothing here is a production proof; once merged the unit is "merged, NOT yet proven" until the owner's phone shows section 8b.
