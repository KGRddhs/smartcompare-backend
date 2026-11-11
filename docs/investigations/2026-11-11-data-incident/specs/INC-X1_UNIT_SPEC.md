# INC-X1 SIZE-FAIRNESS (server half, X1-S) - unit spec (measured, read-only round)

- Unit: INC-X1 server half (X1-S), incident root cause 4 (a found Bahrain price is blanked by the size-fairness rule), fix row X1 (IR:100). The client half X1-C is a SEPARATE client unit (brief R-X1-17..21) and is NOT specified here beyond the wire contract it reads.
- Flag ruling: DARK behind the NEW `ENABLE_SIZE_FAIR_OFFSIZE_LISTING` (default OFF, read per call, flag-OFF byte-identical and pinned on every path incl. the partial paths). Two parts ship unflagged by the brief's ruling (section 1 of INC_X1_BRIEF.md): (U1) the by-name pop of the product-level stash key in the builder on every call (a no-op when the key is absent; with the X1 flag OFF the key is never created); (U2) the D05 PRICE entry `other_size` for a size pend in `kb_ingest._status_one` plus the matching `kb_gaps` rule, a dormant production bug fix that runs only when `ENABLE_FIELD_STATUS_METADATA` or `ENABLE_KB_INGEST` is ON (both OFF on web, H2), pinned byte-identical while both are OFF.
- Worktree `C:/Users/SynAckITPC/Documents/AI/sc-inc-x1` (detached), branch GREEN creates: `fix/inc-x1-size-fairness`. Base sha `6b909e0a92067d6b3562eee325e4956c116441f7` (merge of #399 S81-04c). `git rev-parse HEAD` = the base sha; `git status --short` EMPTY at the start and after every probe of this round (the only file written in the worktree is this spec under the gitignored `.qa-s80/`).
- Evidence pointers (record copy, never a docs checkout): the filed brief `record/inc/INC_X1_BRIEF.md` (R-X1-1..21, E1-E7, P1-P11, Q1-Q6; it supersedes X1_BRIEF_DRAFT.md and X1_BRIEF_CORRECTIONS.md), the incident report `record/incident/INCIDENT_AND_DATA_PLAN_2026-11-11.md` (IR), `record/incident/T1_trace.md` (T1), `record/inc/PAGE_DESIGN_V2.md` (PD2), `record/inc/RULINGS_INC_R0.md` (R0-1..R0-10), `record/s81/PLAN_S81.md`, `record/s80/PLAN_S80.md` section 0 + `record/s80/contract_freeze.json` (re-read before section 2: the frozen price paths are only `price.amount`, `price.currency`, `price.source_method`, `price.unavailable`; additive only; never a bare 503).
- Measurement location: `<SP>/INC-X1/spec/` (base copies of the read modules via `git show HEAD:<path>`, `q4.py` (the key-iteration scan), `closure.py` + `comm_set.txt` (the comm set at base), `probe_re.py` + `probe_re.out` (the title-parser probe on the pinned CPython 3.12.9 `re`)). No pytest, jest, tsc or eslint was run (H5 c).
- Sister units and contracts: INC-X1 client half (X1-C, rides the X4 price card, INC-PAGE, PD2 table 6a keys `results.price.withSize` / `results.price.perMl` / `results.price.differentSizes`); INC-X10 LISTING-MATCH-GUARD (G-INC-1, the wrong-product title guard X1 does not replace, SL6); S81-17 D05 FIELD-STATUS (the closed 2.2 vocabulary this unit amends by ONE price state, `other_size`); S81-04c (merged at base; this unit keeps off the LLMUnavailableError log statements: no edit to extraction_service.py, image_routes.py or url_extraction_service.py). Known rebase points: CLAUDE.md (the block after the newest block and one sentence in the :341 pointer clause); `response_builder.py` if G-INC-1 (INC-X9 removes the cohort_summary attach at RB:2192-2213) merges first: disjoint hunks, union by hand.
- Personal-data rule: no personal value anywhere. Every host in tests is `*.example.com` (store-a / store-b / store-z); fixture product names are public perfume names; no real listing URL, no real store path, no account id; Arabic test strings are built at run time with `chr()` so every file stays pure ASCII.
- Short names: PS = app/services/price_service.py, RB = app/services/response_builder.py, KI = app/services/kb_ingest.py, SCS = app/services/structured_comparison_service.py, ES = app/services/extraction_service.py, SS = app/services/scoring_service.py, SR = app/services/source_router.py. Every file:line below was read at 6b909e0a in this round.

## 0. What the unit does

Today, when the pair is a fragrance pair and one side's selected price sits at a different bottle size than the pair's comparison basis (the flagship 100 ml unless the user typed a size), `reconcile_pair_sizes` (PS:2259) pends that side through `_mark_size_pending` (PS:2402-2417), which replaces the found price with `make_pending_price(..., reason="size_mismatch", size=<old price.size>)` (PS:2005-2018) and nulls `best_price` / `retailer`: the found Bahrain listing is thrown away and the phone shows the pending line. X1-S keeps that pending price byte-identical and, behind `ENABLE_SIZE_FAIR_OFFSIZE_LISTING`:

1. stashes a deep copy of the found price (plus the pair's target ml) on the PRODUCT dict under `_offsize_listing_src` at the pend (PS);
2. in `build_comparison_response`, right after the price chokepoint, pops that key from every product dict on EVERY call (unflagged U1) and, flag ON, writes the additive `price.offsize_listing` (amount in BHD, the listing's own title size, store, link, title, method and, only when the partner qualifies, a per-ml figure) when the stash passes the eligibility tests E1-E7; gives an on-basis partner `price.size_ml` and `price.per_ml` when its own listing qualifies; drops the false price-provenance sentence from `scoring_v2.winner_evidence` when the runner-up is a size pend; stamps `metadata.size_fair`; logs one `[SIZE_FAIR]` INFO line per size-pended side (RB);
3. (unflagged U2) labels a size pend's D05 PRICE entry `other_size` instead of `unknown / no_price`, and keeps the `kb_gaps` rows unchanged by treating `other_size` like `unknown` in `run_job` (KI).

No score, winner, verdict prompt, savings figure, SSE event before `complete`, or existing key changes; `price.amount` stays null; nothing says "cheaper". Neither live bundle (store 683f56c0, OTA f1e20c39) reads any new key, so this unit changes nothing on any phone by itself (SL1); the phone proof waits for X1-C (section 8b).

## 1. Base state (measured at 6b909e0a)

### 1.1 The pend (PS)

| what | where | measured fact |
|---|---|---|
| pending shape | PS:2005-2018 `make_pending_price(currency="BHD", reason="pending_genuine", size=None)` | returns `{"amount": None, "currency": currency or "BHD", "unavailable": True, "reason": reason}` plus `"size"` only when `size` is truthy. |
| the reconcile | PS:2259-2399 `reconcile_pair_sizes(product_data, user_query=None, candidates_by_name=None, treat_unsized_as_flagship=False)` | no-op unless both amounts are numbers > 0 (PS:2303-2309) and neither side is an estimate (PS:2318-2321); fair already when both effective sizes are equal and the user typed no size (PS:2338-2341); `target = target_pair_size_ml(...)` (PS:2343; a float: the query's smallest ml, else `_FRAGRANCE_FLAGSHIP_SIZE_ML = 100.0` PS:1439 when both names are designer fragrances or under `treat_unsized_as_flagship`, else None). Target None: legacy compare, `_mark_size_pending(p0, p1)` at PS:2353. Else `_resolve_to_target` (PS:2359-2381; a successful re-selection REPLACES `p["price"]`, so a side that fails keeps its ORIGINAL found price dict); outcome 2 pends one side (PS:2392 `_mark_size_pending(p1)`, PS:2395 `_mark_size_pending(p0)`), outcome 3 both (PS:2398). |
| the pend helper | PS:2402-2417 `_mark_size_pending(*products)` | per product: `price = p.get("price") if dict else {}`; `p["price"] = make_pending_price(currency=price.get("currency") or "BHD", reason="size_mismatch", size=price.get("size"))`; `best_price` / `retailer` set to None when present. The found price is dropped here. Callers: PS:2353, 2392, 2395, 2398 only; no test references the name. |
| the fragrance entry | PS:3301 `reconcile_pair_fairness`, PS:3346-3351 | `canon == "fragrances"` delegates to `reconcile_pair_sizes(..., treat_unsized_as_flagship=frag_reconcile_fix_enabled())`. |
| effective size | PS:2021-2045, PS:2048-2095 | precedence full_name / name, then `price.title`, then `price.size`, then specs volume / size / concentration; each scanned with `extract_sizes_ml` (PS:4087-4093) over `_SIZE_ML_RE = re.compile(r"(\d{1,4})\s*(?:-?\s*)ml\b", re.I)` (PS:4073); the MINIMUM token of the first field with any token wins; no token: 100.0 for a designer name or under the fix flag. |
| why a found price pends (C1) | inferred, T1:117 | Layton's name and pending dict carry no size and its specs were `{}`, so the found price's TITLE is the only field left: its smallest ml token is not 100 (LIKELY 125). The title is NOT persisted anywhere (T1:117 "title not persisted"); see Q1. |

### 1.2 Where the reconcile runs and where the body is built (SCS)

| what | where | measured fact |
|---|---|---|
| sync reconcile | SCS:4586-4592 | `reconcile_pair_fairness(product_data, query, category_used, candidates_by_name=self._price_candidates)` in try/except: `logger.warning("fairness reconciliation skipped (sync): %s", _e)`. `product_data` is the fresh gather result (SCS:4541) and is stashed as `self._partial_product_data` (SCS:4551) BEFORE the reconcile, so the sync partial sees the reconciled dicts (same objects). |
| stream reconcile | SCS:5339-5345 | the same call, `(stream)` warning text; `product_data` from `asyncio.wait_for(...)` (SCS:5243). |
| builders | SCS:4783 (sync), SCS:5676 (stream complete), SCS:3880 (`_build_partial_response`, def SCS:3798, list SCS:3821 `self._partial_product_data or self._early_specs_buffer_list() or []`; callers SCS:4210 sync timeout, SCS:5012 stream tail deadline, SCS:5270 stream hard cap) | every body carrying products is built by `build_comparison_response`; `_partial_product_data` is reset at SCS:4363 / SCS:5065 and set only at SCS:4551 (sync), so a stream partial never carries a reconciled dict. |
| after the builder | SCS:4822-4826 (pops `_stage_timings_ms`); SCS:4878-4881 and SCS:5797-5800 (`_kb_ingest_tail(result, product_data, ...)`) | the D05 tail reads the SAME product_data list after the builder, i.e. after the pop and the projection. |
| D05 tail | SCS:3938-3965 `_kb_ingest_tail` | reads `kb_ingest_enabled()` and `field_status_metadata_enabled()` FIRST and returns when both are OFF (SCS:3948-3951); else `kb_ingest.build_job(...)`; under `ENABLE_FIELD_STATUS_METADATA` `metadata["field_status"] = snap["field_status"]`. |
| SSE price event | SCS:5394-5435 | NEW payload dicts per product from named keys; a size pend (`unavailable is True`) passes through `public_price_view(_price)`, which returns the SAME object when the exact gate is OFF (PS:9371-9387). Hence the projection never mutates a price dict in place (rule I3, 2.4). |
| parked-price writers | miss path SCS:7039-7045 returns `self._parked_price[full_name]`; writers SCS:7804-7814 (`converted_fallback = dict(_conv_best)` of the best CONVERTED observed row, only under `exact_gate_enabled()`), SCS:7997-8003 (`converted_usd` Tier-1), SCS:8004-8018 (a GENUINE Tier-1 price on a listing url, under `_park_listing_url_tier1_enabled()` SCS:2846), SCS:8737-8747 `_maybe_park_supplement` (any price passing `is_price_showable(full_name, price_obj)`; callers SCS:8773, 8806, 8859, 9002) | Q6 answer in 11.2. |
| cache marks | SCS:7105-7107 (`cached["_cached"] = True` on an L1 hit), SCS:7871 (`best["_cached"] = False` on a fresh BH adapter hit; the INFO line SCS:7872-7877 `[PRICE] BH adapter direct hit for %s: %.3f %s via %s (%s, ...)`) | the stash keeps `_cached`, the pending dict does not. |

### 1.3 The builder (RB)

| what | where | measured fact |
|---|---|---|
| price chokepoint | RB:1646-1765 | per product: non-dict -> pending; the `_region_guard_rejected` / `_prescoring_showable_rejected` harvests; `if _price.get("unavailable") is True: continue` (RB:1715-1716: a size pend keeps its own reason); the region guard; `if not is_price_showable(_name, _price, _cat, enforce_correctness=True)` -> `pending_genuine` (RB:1739-1763), with `_name = pd.get("full_name") or pd.get("name") or ""` (RB:1660) and `_cat = pd.get("category") or _infer_category_from_query(_name)` (RB:1664). Wrapped in `try ... except Exception: logger.warning("price-pending normalization skipped", exc_info=True)` (RB:1764-1765). Lazy import of the PS names at RB:1648-1652. |
| next block | RB:1767 | the W4-7 single-confidence block copies every product key (`{**p, ...}` / `dict(p)`, RB:1779-1784): the pop must run before it. |
| overview price | RB:1951 `"price": public_price_view(pd.get("price"))` | the same object as `pd["price"]` when `ENABLE_EXACT_PRICE_GATE` is OFF; a shallow top-level copy without `guard_rejected` / `_` keys when ON (default ON, `exact_gate_enabled` PS:4370-4374). |
| scoring_v2 | RB:2079-2082 -> `_build_scoring_v2` (RB:1243); `winner_evidence` RB:1328-1331 (a NEW list `[str(e) for e in ...]`), key RB:1346 | `result["scoring_v2"]` may be None (the honest-partial branch, RB:2286-2290). |
| metadata | RB:2095-2144; the LLM-ledger stamps RB:2158-2179; the caller merge `if metadata: result["metadata"].update(metadata)` RB:2180-2181 | caller wins on a conflicting key. |
| legacy alias | RB:2227-2268 | ships the RAW product dicts; `pd["price"] = public_price_view(pd["price"])` (RB:2263-2264); `pd.pop("_shopping_listing_count", None)` (RB:2267: the unconditional-pop precedent). |
| cache flag | RB:49-81 `_compute_cache_observability` | `cache_hit` = ANY product price `_cached` truthy (response level); a pending dict carries no `_cached`. |
| evidence text | SS:988-1030 `build_winner_evidence`; SS:1007-1008; SS:964-968 `_has_real_price` | the entry is `f"{name} has a confirmed Bahrain price while the other relies on an indicative figure"` (name prefix SS:1029-1030), appended when the winner has a `_PRICE_TRUST_SET` method and the runner-up does not; a size pend has no source_method, so a size-pended runner-up always triggers it. Flag-free carriers of the text: tests/test_winner_evidence_scoring_v2.py:46, tests/test_prescoring_showable_guard.py:261, tests/fixtures/w412_corpus_min.json:11007. |

### 1.4 Readers between the reconcile and the builder (Q4, by `q4.py` over the base bodies)

| reader | where | iterates product keys? |
|---|---|---|
| `apply_prescoring_showable_guard` / `apply_region_currency_guard` | PS:3244-3298 / PS:3184-3241 | no (named keys) |
| `ScoringService.compute_scores` | SS:1357-1702 | no (`.items()` only over weights / breakdown) |
| `_display_product_names`, `verdict_comparison_quality` | SCS:1271-1281, SCS:1085-1107 | no |
| `kb_serve.log_verdict_key` | kb_serve.py:420-461 | no (brand / name / variant only) |
| `generate_comparison` -> `_verdict_safe_product` | ES:2552, ES:2482-2549, dump ES:2647-2654 | YES: `json.dumps(product)` of the product; but `_verdict_safe_product` strips every `_`-prefixed product key first (ES:2522-2526, a filtered copy preserving order), and a size-pended price is re-made by `make_pending_price(currency, reason, size)` (ES:2544-2548) from `price.size` only. With the stash present the copy-on-write branch runs where it may not have before, and its output equals the original minus the stash key: the prompt bytes are unchanged as long as X1 never fills `price.size` (pinned by P02). |
| `validate_verdict` | trust_validation_service.py:46-129 | no |
| `apply_value_badges` | SS:2671-2704 | no |
| `compute_confidence` (sync SCS:4757) | SS:2839-2858 (`{**p, "shopping_count": ...}` copies), SS:1150-1253 | copies keys; reads named keys only |
| SSE payloads | SCS:5379-5390, 5407-5435 and the later events | named keys only |

### 1.5 D05 (KI)

| what | where | measured fact |
|---|---|---|
| flag readers | KI:81-88 | `kb_ingest_enabled()`, `field_status_metadata_enabled()`: `os.getenv(NAME, "false").strip().lower() in _TRUTHY` (KI:57). |
| price entry | KI:193-207 | `_rg.price_is_showable(price)` -> fresh / stale; else `_item("unknown", None, "estimated" if estimated else "no_price")` + `as_of=None, rung=None` (KI:203-206). A size pend (amount None) lands in the else arm with `no_price`. |
| size entry | KI:209-217 | `_size_ml(price)` (KI:147-152 over `_ML_RE = ^\s*(\d{1,5})\s*ml\s*$` KI:73 on `price.size`) -> `known / listing`, else specs. UNCHANGED by this unit (R-X1-11, SL13). |
| host | KI:143-144 `_url_host(url)` = `deny_hosts.normalize_host(jsonld_widen._url_host(url))` | lower case, no port, no trailing dot, one leading `www.` dropped (deny_hosts.py:119-134; jsonld_widen.py:117-126). |
| the job | KI:270-299 `build_job` copies only `_PRICE_KEYS` (KI:264-267: amount, currency, url, source_method, estimated, _cached, size, image_url, in_stock, _cache_source), so `offsize_listing` never reaches a KB row. | |
| gap rule | KI:476-486 | per D05 field except identity: `if _dict(status.get(field)).get("state") != "unknown": continue` (KI:480), then one `kb_gaps` row (field, host hint, state open / needs_operator). |
| the frozen vocabulary pin | tests/test_s81_s17_kb_ingest.py:110-125 (`VOCAB_STATES["price"] = {"fresh", "stale", "unknown"}`, `VOCAB_REASONS["price"]`), `_check_vocab` :441-458 | applied to stub-pipeline bodies whose `reconcile_pair_fairness` is stubbed to a no-op (t17:545) and to `_product()` fixtures with `price.size "100ml"` and no pend (t17:240-256): no size pend ever reaches `_check_vocab`, so the file stays green and unedited (4.2). |

### 1.6 The helpers E1-E5 rely on

| helper | where | measured fact |
|---|---|---|
| `_GENUINE_BH_SOURCE_METHODS` | PS:17065-17087 | 15 genuine methods; none contains "converted" or "estimate". |
| `_is_genuine_bh_candidate(c)` | PS:17090-17124 | False on "converted" / "estimated" in `source_method` or `raw_data.source_method`; False unless one of them is genuine; False when `registry_tier(raw.retailer or c.retailer or raw.url) == "global"` (SR:764, no blocking I/O); a raising tier lookup counts as not global (PS:17122-17123). |
| `_is_listing_url(url)` | PS:8541-8551 | lazy `source_router.is_non_pdp_listing_url` (SR:1227); False for a missing url; False on a classifier exception. |
| `is_price_showable(name, price, category, enforce_correctness)` | PS:1877-2002 | amount number > 0; method in `_showable_source_methods()` (genuine + `converted_usd`, PS:1839-1840); WRITES `price["title"]` (PS:1917, 1920) and `price["guard_rejected"]` (PS:1953, 1965, 1976, 1982, 2000); the listing-url and identity backstops run only when `enforce_correctness and exact_gate_enabled()` (PS:1951). |
| `public_price_view` | PS:9371-9387 | identity when the exact gate is OFF; else a NEW dict without `guard_rejected` / `_` keys (top level only). |
| Woo title (Q5) | woocommerce_service.py:165-166, 270-279 | `title = html.unescape(prod["name"]).strip()`: the Store API product NAME; no variation attribute is appended; the candidate carries `title`, never `size`. |

### 1.7 Flag-reader idiom

The house reader (PS:4905-4923 `frag_reconcile_fix_enabled`, KI:81-88): `os.getenv("ENABLE_X", "false").strip().lower() in ("true", "1", "yes", "on")`, read per call, never cached at import. `ENABLE_SIZE_FAIR_OFFSIZE_LISTING`: `git grep` at base finds no `offsize`, `size_fair`, `SIZE_FAIR`, `per_ml` or `perMl` token in app/, SmartCompareApp/src, scripts/ or tests/ (one unrelated test name `test_tiny_size_per_ml_implausible_not_showable`, tests/test_price_showable.py:92). No new name contains access / auth / api / credential / creds / key / password / secret / token.

### 1.8 Libraries (pinned venv `.venv-qaren`, CPython 3.12.9)

Only the standard library: `re`, `copy`, `math`, `logging`, `os`. Probe `probe_re.out` (run with `-I`, no pytest): the strict parser `(?<![0-9.,])([0-9]{1,4})[ -]?ml\b` (re.IGNORECASE), values kept in 1..9999, gives 125 for "Layton EDP 125ml" / "Layton 125 ML" / "Layton 125-ml"; {} for "7.5ml" (the base `_SIZE_ML_RE` gives 5), "1,125ml" (base: 125), "0ml", "12345ml" (base: 2345), "100mlx", "100 mls", "100  ml" (two spaces; base: 100), an Arabic-only title and an Arabic-Indic-digit "ml" title (the base regex DOES match Arabic-Indic digits through `\d`); {50, 100} for "50ml / 100ml"; {100} for "100ml 100 ml"; 100 for "EDP100ml"; 90 for "Eau de Parfum 90ML Spray".

### 1.9 Guards the new code must not trip

| guard | where | what the code must do |
|---|---|---|
| D05 / KB import census | tests/test_s81_kb_schema.py:334-353 (P01 / P02: who imports `kb_service`, the table constants) | KI gains no import and no table constant; PS / RB import nothing from kb_* |
| scoring never reads the partner | tests/test_s81_s15_registry_robots.py:792-800 (`test_p6_scoring_never_reads_partner`, an AST import census of SS / RB / SCS) | RB adds no import of a registry / robots module; every new RB import is a function-local `from app.services.price_service import ...` (the RB:1648 style) |
| llm_pricing by module attribute | tests/test_s81_s03_llm_ledger_v2.py:2537-2560 (BL4 over RB, SCS, ...) | no from-import of `llm_pricing` |
| genuine-set parity | tests/test_eval_genuine_methods_parity.py, tests/test_genuine_predicate_parity.py:55 | `_GENUINE_BH_SOURCE_METHODS` and `_is_genuine_bh_candidate` are read, never edited |
| source-scanning pins | test_model_config*.py, test_prompt_fence.py, test_u3c_store_false_pin.py, test_start_command*.py, test_migration_index_predicate_immutability.py, test_openai_key_log_hygiene_s69.py, test_sentry_channels_u8d_unit.py | no LLM call, no prompt text, no migration, no Sentry channel, no key log |
| the D05 golden fixtures | tests/fixtures/s81_s22b_flag_off_golden.json (carries `field_status`, zero `size_mismatch`), s81_g8 / s81_s18 / s81_s17 / s81_d14 goldens (zero of either) | no golden body carries a size pend, so U2 moves no golden |
| gitleaks / added-line sweep (H7) | .githooks | no 64-hex constant; no long digit run (the per-ml literals 0.68 / 1.3346 are short); no keyword-named constant |
| black allowlist | .github/black-clean-paths.txt (63 lines) | none of PS / RB / KI / the new tests is listed |
| ES / image_routes / url_extraction_service | S81-04c (H1, R0-7) | not touched at all |

### 1.10 Line endings

`core.autocrlf=true`; PS, RB and KI are CRLF in the working copy and LF in the index (`file` at base). GREEN edits with the Edit tool (preserves CRLF); `git diff --stat` must show hunks only, never a whole-file diff. New test files are written LF, pure ASCII (bytes > 127 = 0), checked after every write.

### 1.11 Base pass state (DEFERRED TO RED: nothing was run in this round)

Every command uses the lane runner `<SP>/harness/pyt.py` and the pinned venv; tags start `inc-x1-`. The RED agent records each `[pyt]` line here before writing the RED files:

| # | set | command (exact) |
|---|---|---|
| B-1 | the files GREEN touches directly | `PYTHONIOENCODING=utf-8 C:/Users/SynAckITPC/Documents/AI/.venv-qaren/Scripts/python.exe <SP>/harness/pyt.py --bound 1200 --tag inc-x1-base-direct --log <SP>/INC-X1/red/base-direct.log --cwd C:/Users/SynAckITPC/Documents/AI/sc-inc-x1 -- tests/test_s81_s17_kb_ingest.py tests/test_s81_g3_gate_rows.py tests/test_response_builder_price_pending.py tests/test_pair_size_basis_fairness.py tests/test_pair_size_reselection.py tests/test_price_size_reconcile.py tests/test_fragrance_size_reconcile_fix.py tests/test_category_fairness.py tests/test_winner_evidence_scoring_v2.py tests/test_winner_evidence_prod_fixtures.py tests/test_prescoring_showable_guard.py tests/test_ws5_honesty.py tests/test_s81_kb_schema.py tests/test_s81_d22_nightly_learning.py -q` |
| B-2 | the identity digests | `... pyt.py --bound 1200 --tag inc-x1-base-ident --log <SP>/INC-X1/red/base-ident.log --cwd <W> -- tests/test_s75_fanout_identity.py tests/test_s81_s20_result_gate.py tests/test_s81_s22_compare_runs.py tests/test_streaming.py -q` |
| B-3 | the comm set (678 files, section 7) | 28 chunks of at most 25 files, `--bound 1200` each, tags `inc-x1-base-cNN`; or the LC-6 reuse of a stored record under `<SP>/harness/base_records/6b909e0a92067d6b3562eee325e4956c116441f7/<set-sha256>.txt` when one matches the set hash `3850de9e7dd19d8014f73991c18fd83d2fc356b998ab0ad8956507067c42ea35` |
| B-4 | the pre-commit hook files (own call, only if .githooks changes: it does not) | not run |
| B-5 | the fourteen client fences (footprint touches app/; no literal they read moves) | after the H5 jest probe, from `<W>/SmartCompareApp` through the orchestrator's junction: `timeout -k 15 600 node node_modules/jest/bin/jest.js --ci __tests__/brand/inAppMark.u4c.test.ts __tests__/clientTruth/medicalNote.s74.test.tsx __tests__/clientTruth/privacyManifest.s74.test.ts __tests__/clientTruth/shareTruth.s74.test.tsx __tests__/clipboardFallbackService.test.ts __tests__/config/nativeBundle.w37.test.ts __tests__/DimensionBars.perCategory.test.tsx __tests__/honestCounts.s69.test.tsx __tests__/landing.domain.s76.test.ts __tests__/navigation/linking.w315.test.ts __tests__/onboarding/step05Trust.s69.test.tsx __tests__/playInstallReferrerService.test.ts __tests__/playInstallReferrerService.edges.test.ts __tests__/ResultsScreen.timeout.test.tsx` (the RED agent confirms each file name with `git ls-files` first; the accepted base failures are the four nativeBundle.w37 drift nodes) |

Known environmental base noise to record identically at base and head: tests/test_prompt_truth.py::test_truth_on_prefix_static_and_cacheable and ::test_render_digests_match_base_except_the_fence (cold tiktoken cache); the 11 deselected nodes of tests/.pre_impl_failures.txt.

## 2. Contract

### 2.1 Flag and knobs

| name | reader | default | read where |
|---|---|---|---|
| `ENABLE_SIZE_FAIR_OFFSIZE_LISTING` | NEW `price_service.size_fair_offsize_listing_enabled() -> bool`: `return os.getenv("ENABLE_SIZE_FAIR_OFFSIZE_LISTING", "false").strip().lower() in ("true", "1", "yes", "on")` | OFF | (a) ONCE per `_mark_size_pending` call, the first statement of the new stash branch; (b) ONCE per `build_comparison_response` call, right after the unconditional pop (2.3), the value reused by the projection, the winner_evidence step and the metadata stamp of that build. Never at import. |

No knob, no new credential name (`tests/_env_safety.CREDENTIALS_UNSET` unchanged), no new external host (no processors.json row), no migration.

### 2.2 New PS symbols (all pure; no I/O beyond the existing in-memory `registry_tier`)

| symbol | signature | contract |
|---|---|---|
| `SIZE_FAIR_REASONS` | `frozenset` of str | exactly: no_stash, no_target, not_bhd, not_genuine, converted, global_tier, estimated, no_url, listing_url, not_showable, no_title, no_title_size, multi_size_title, size_equals_target, not_size_pend, error (16 codes, R-X1-12). |
| `_SIZE_FAIR_TITLE_ML_RE` | compiled | `re.compile(r"(?<![0-9.,])([0-9]{1,4})[ -]?ml\b", re.IGNORECASE)` (ASCII digits only, 1.8). |
| `parse_listing_title_ml(title)` | `(title: Any) -> Tuple[Optional[int], Optional[str]]` | not a str or blank -> `(None, "no_title")`; the set of int values from `findall` kept in 1..9999: empty -> `(None, "no_title_size")`; more than one distinct value -> `(None, "multi_size_title")`; exactly one -> `(value, None)`. Never reads `price.size`, `raw_data`, the name or specs (E5). |
| `size_fair_host(url)` | `(url: Any) -> str` | `normalize_host(jsonld_widen._url_host(url))` with a function-local `from app.services.deny_hosts import normalize_host`; "" for a non-str or an unparsable url. Equal by construction to KI's `_url_host` (1.5). |
| `size_fair_listing_eligibility(price, product_name, category, target_ml)` | `-> Tuple[bool, Optional[str], Optional[int]]` = (eligible, reason or None, title ml or None) | the checks below IN THIS ORDER, the first failure wins (the precedence row E12 pins it); `price` is never mutated (E13). |
| `size_fair_partner_size_ml(price, product_name, category, target_ml)` | `-> Optional[int]` | the partner test of R-X1-7 (a): None unless `price` is a dict whose `unavailable` is not True and which passes checks 2-10 below AND whose single title size equals `target_ml`; then that size. |
| `_mark_size_pending(*products, target_ml=None)` | keyword-only `target_ml: Optional[float]` | the four callers pass it: PS:2353 `target_ml=None`, PS:2392 / 2395 / 2398 `target_ml=target`. Flag OFF: byte-identical to base (one env read added). Flag ON, per product, BEFORE the pend: `try: stash = {"price": copy.deepcopy(price), "target_ml": (float(target_ml) if target_ml is not None else None)}` -> `p["_offsize_listing_src"] = stash`; `except Exception as exc: logger.warning("[SIZE_FAIR] stash skipped type=%s", type(exc).__name__)` and no stash; then the pend EXACTLY as PS:2409-2417 (the pending dict, best_price, retailer unchanged). `price` here is the same local as base (`{}` for a non-dict price). `copy` is imported function-locally or at module top (PS has no `import copy` at base: PS:5-49). |

Eligibility checks (E1-E7 of the brief, mapped to codes):

| # | check (on the stashed found price `fp`, side price `sp`, stash `st`) | code on failure |
|---|---|---|
| 0 | `st` is a dict whose `"price"` is a dict | no_stash |
| 1 | `st["target_ml"]` is not None (E6 part) | no_target |
| 2 | `fp["amount"]` is an int or float, not bool, finite, > 0, and `fp.get("currency") == "BHD"` (E1) | not_bhd |
| 3 | `fp.get("estimated") is not True` and "estimated" is in neither `source_method` nor `raw_data.source_method` (E2) | estimated |
| 4 | "converted" is in neither method (E2) | converted |
| 5 | one of the two methods is in `_GENUINE_BH_SOURCE_METHODS` (E2) | not_genuine |
| 6 | `_is_genuine_bh_candidate(fp)` is True (after 3-5 only the global-tier arm can fail) (E2) | global_tier |
| 7 | `fp.get("url")` is a non-blank str (E3) | no_url |
| 8 | `_is_listing_url(url)` is False, ALWAYS, whatever `exact_gate_enabled()` says (E3) | listing_url |
| 9 | `is_price_showable(product_name, copy.deepcopy(fp), category, enforce_correctness=True)` (E4) | not_showable |
| 10 | `parse_listing_title_ml(fp.get("title"))` gives one size (E5) | its code: no_title / no_title_size / multi_size_title |
| 11 | that size != `st["target_ml"]` compared as floats (E6) | size_equals_target |
| 12 | the side price at build time is a dict with `unavailable is True` and `reason == "size_mismatch"` (E7; checked by the RB step BEFORE 0 when a side carries a stash) | not_size_pend |

`product_name` and `category` are the chokepoint's own values for that product: `pd.get("full_name") or pd.get("name") or ""` (RB:1660) and `pd.get("category") or _infer_category_from_query(name)` (RB:1664), so E4 is literally the gate every shown price passes (the brief names `category_used`; see 11.1 Q-S1).

### 2.3 The builder step (RB)

Placement: a NEW block between the end of the chokepoint's try/except (RB:1764-1765) and the W4-7 block (RB:1767).

```
# INC-X1 (U1, unflagged): the size-fair stash never reaches any projection.
_sf_srcs = [pd.pop("_offsize_listing_src", None) if isinstance(pd, dict) else None
            for pd in product_data]
# INC-X1 (ENABLE_SIZE_FAIR_OFFSIZE_LISTING; read once per build, after the pop).
from app.services.price_service import size_fair_offsize_listing_enabled
_sf_on = size_fair_offsize_listing_enabled()
_sf_entries = None
if _sf_on:
    try:
        _sf_entries = _size_fair_step(product_data, _sf_srcs)
    except Exception as _sf_exc:  # noqa: BLE001 -- price handling never crashes the body
        logger.warning("[SIZE_FAIR] projection skipped: %s", type(_sf_exc).__name__)
        _sf_entries = None
```

`_size_fair_step(product_data, srcs) -> Optional[List[dict]]` (a new module-level RB function, the test seam of B08):

1. PLAN (may raise; nothing is written yet). For each index i in 0..1 with `product_data[i]` a dict: side price `sp`; it is a size-pended side when `sp` is a dict, `unavailable is True` and `reason == "size_mismatch"`. A side gets an entry when it is size-pended OR `srcs[i]` is not None. For each such side, inside its own try/except: not size-pended -> pended / not_size_pend; else `size_fair_listing_eligibility(...)` (2.2); a raise inside one side -> that side pended / error (the other side continues). An eligible side's object:
   `{"amount": round(float(fp["amount"]), 3), "currency": "BHD", "size_ml": <title ml>, "retailer": fp["retailer"] if a str else None, "url": fp["url"], "title": fp["title"], "source_method": <the genuine one of fp.source_method / raw_data.source_method, the top-level first>}` (a FRESH dict of exactly these seven keys; `per_ml` is added in step 2 or never).
2. PER-ML (R-X1-7). With target `T = srcs[i]["target_ml"]` of the eligible side: (a) the partner j is not a size-pended side and `size_fair_partner_size_ml(partner price, name_j, cat_j, T)` returns m: the eligible object gains `per_ml = round(amount / size_ml, 4)` and the partner's NEW price dict gains `size_ml = m` and `per_ml = round(round(float(partner amount), 3) / m, 4)`; (b) the partner is itself eligible (PD2 case D): each object gains its own `per_ml`; neither price gains `size_ml`; (c) else no `per_ml` anywhere and nothing on the partner.
3. COMMIT (cannot raise: plain dict construction and assignment). For each eligible side: `product_data[i]["price"] = {**sp, "offsize_listing": obj}` (a NEW dict; the pending dict object is never mutated, I3). For a qualifying partner: `product_data[j]["price"] = {**partner_price, "size_ml": m, "per_ml": v}` (a NEW dict; `_cached` and every other key ride along unchanged, so RB:2139 cache observability is unchanged).
4. Entries, in product order: `{"product_index": i, "outcome": "offsize_listing" | "pended", "reason": None | code, "listing_cached": (srcs[i]["price"].get("_cached") if it is a bool else None) when a stash exists, else None, "per_ml": bool("per_ml" in obj) for an eligible side, else False}`. One INFO line per entry (2.6). Returns the list, or None when it is empty.

After `result` exists, still under `_sf_on`, placed after the LLM-ledger stamps and BEFORE the caller merge (RB:2180), so a caller's `metadata={"size_fair": ...}` wins:

```
if _sf_on:
    if _sf_entries:
        result["metadata"]["size_fair"] = _sf_entries
    try:
        _size_fair_winner_evidence(result, product_data, winner_index)
    except Exception as _sf_exc:  # noqa: BLE001
        logger.warning("[SIZE_FAIR] winner_evidence skipped: %s", type(_sf_exc).__name__)
```

`_size_fair_winner_evidence(result, product_data, winner_index)` (R-X1-9): when `len(product_data) == 2`, `winner_index in (0, 1)`, the runner-up `product_data[1 - winner_index]["price"]` is a size-pended side (at this point the price dict may carry `offsize_listing`; the test is `unavailable is True and reason == "size_mismatch"`), and `result["scoring_v2"]` is a dict whose `winner_evidence` is a list: `result["scoring_v2"]["winner_evidence"] = [e for e in ev if not (isinstance(e, str) and e.endswith(_SIZE_FAIR_EVIDENCE_PHRASE))]` with the module constant `_SIZE_FAIR_EVIDENCE_PHRASE = "has a confirmed Bahrain price while the other relies on an indicative figure"` (a NEW list; `scoring_result` and `result["scoring"]` untouched; no fallback reason is added when the list empties, SL15).

### 2.4 KI (U2, unflagged; dormant while both D05 flags are OFF)

- `_status_one`, the non-showable arm (KI:203-207): when `price.get("unavailable") is True and price.get("reason") == "size_mismatch"`, the entry is `_item("other_size", <size_fair-equivalent host of price["offsize_listing"]["url"] when offsize_listing is a dict with a str url, via KI's own `_url_host`, else None> or None, "size_mismatch")` plus `as_of=None, rung=None`; every other price keeps today's `unknown / estimated|no_price`. The X1 flag is NOT read here (U2 must not wait for the X1 flip: a D05 flip first would otherwise print the false `results.honest.notListed` line, brief section 1).
- `run_job` (KI:480): `if _dict(status.get(field)).get("state") not in ("unknown", "other_size"): continue` (the gap rows stay exactly as at base, R-X1-11).
- The SIZE entry (KI:209-217), `build_job`, `_PRICE_KEYS` and every other line: unchanged.

Invariants (each pinned in section 5):

| id | invariant |
|---|---|
| I1 | Flag OFF: no product dict ever carries `_offsize_listing_src`; every body, SSE frame, saved row, log line and the verdict prompt is byte-identical to base (P01, S02). |
| I2 | Flag ON: before the builder nothing changes (the pending dict, best_price, retailer, the SSE events, compute_scores, the verdict user message: P02, P03, S01); after the builder no body carries `_offsize_listing_src` at any depth (P04, B02). |
| I3 | No price dict is mutated in place by X1; every write assigns a NEW dict (B05). |
| I4 | `price.amount`, `unavailable`, `reason`, `price.size`, `best_price`, `retailer`, `overview.winner`, `scoring.*`, `scoring_v2.dimensions`, `scoring_v2.factual_verdict`, `value_badge`, `overview.confidence` are identical ON and OFF (B21, P03). |
| I5 | U2 is independent of the X1 flag and changes nothing while `ENABLE_FIELD_STATUS_METADATA` and `ENABLE_KB_INGEST` are OFF (K08, P01 with both D05 flags unset). |

### 2.5 New keys (all additive; contract_freeze lists only amount / currency / source_method / unavailable under price)

| key | type | present when |
|---|---|---|
| `overview.products[i].price.offsize_listing` and the same object under `products[i].price` | object, exactly `amount` (float, 3 dp), `currency` ("BHD"), `size_ml` (int 1..9999, not bool), `retailer` (str or null), `url` (str), `title` (str), `source_method` (str in the genuine set), optional `per_ml` (float, 4 dp, BHD per ml) | flag ON, side i is a size pend and its stash passes E1-E7 |
| `overview.products[j].price.size_ml`, `.per_ml` (and the alias) | int; float 4 dp; together or not at all | flag ON, R-X1-7 (a) |
| `metadata.size_fair` | list of `{product_index: 0|1, outcome: "offsize_listing"|"pended", reason: null|code in SIZE_FAIR_REASONS, listing_cached: true|false|null, per_ml: bool}` | flag ON and at least one side is size-pended or carried a stash |
| `scoring_v2.winner_evidence` | unchanged type (list of str), one entry fewer | flag ON, the runner-up is a size pend and the list held the phrase |
| `metadata.field_status[i].price.state = "other_size"` (source host or null, reason "size_mismatch", as_of null, rung null) | the D05 shape | `ENABLE_FIELD_STATUS_METADATA` ON and side i is a size pend (any X1 state) |

No key is removed, renamed or retyped; no new error code; no HTTP status change; never a 503.

### 2.6 Log lines

| line | level | when |
|---|---|---|
| `[SIZE_FAIR] product_index=%d outcome=%s reason=%s listing_ml=%s target_ml=%s host=%s cached=%s` | INFO, once per entry | flag ON; `reason` the code or `none`; `listing_ml` the parsed title int when parsing ran, else `none`; `target_ml` `int(target)` or `none`; `host` `size_fair_host(stash url)` or `none`; `cached` `true` / `false` / `none`. Constants and ints plus one normalized host (the existing `[PRICE] ... via <domain>` practice, SCS:7872-7877); never a product name, query, title, URL path or amount. |
| `[SIZE_FAIR] stash skipped type=%s` | WARNING | flag ON, the deep copy raised in `_mark_size_pending` |
| `[SIZE_FAIR] projection skipped: %s` | WARNING | flag ON, `_size_fair_step` raised |
| `[SIZE_FAIR] winner_evidence skipped: %s` | WARNING | flag ON, the evidence step raised |

No ERROR line anywhere (ERROR only inside except arms by house rule; none here needs it). No Sentry event, no metric.

### 2.7 Failure table (flag ON)

| failure | effect |
|---|---|
| the deep copy in `_mark_size_pending` raises | that side has no stash (one WARNING); the pend is exactly today's; the builder reports pended / no_stash |
| the reconcile itself raises (SCS:4591 / 5344) | today's `fairness reconciliation skipped` WARNING; a stash already written for a side stays on the dict and is popped by the builder |
| a per-side eligibility call raises | that side pended / error (logged as an entry); the other side is evaluated |
| `_size_fair_step` raises in its plan phase | one WARNING; nothing was written; no `metadata.size_fair`; the body equals the flag-OFF body (the pop already ran) |
| the winner_evidence step raises | one WARNING; `winner_evidence` as built |
| the tier lookup raises | the retailer counts as not global (PS:17122-17123, SL9) |
| the flag reads ON at the pend and OFF at the build (mid-request flip) | the stash is popped, nothing projected (B06) |
| the flag reads OFF at the pend and ON at the build | pended / no_stash for each size pend (B10) |
| the stash survives because the request ends before any build (a refusal, INSUFFICIENT_DATA after the reconcile, a client gone) | the product dicts are per request (SCS:4541, 5243) and never shipped by another path; nothing reaches a body (no builder ran) |

### 2.8 Flag-OFF identity and the deploy-visible delta (the main invariant)

With every flag at its default (the X1 flag unset; `ENABLE_FIELD_STATUS_METADATA` and `ENABLE_KB_INGEST` OFF on web per H2): the stash branch is never entered, so `_offsize_listing_src` never exists and the unconditional pop removes nothing; the RB step, the evidence step and the metadata stamp never run; `_kb_ingest_tail` returns before `field_status` is ever computed, so U2's new arm and gap rule never run. What changes in production: one extra `os.getenv` per `_mark_size_pending` call (only when a pair is size-pended) and one per body build; nothing a user, a saved row, a log line, an SSE frame or the verdict prompt can show. The redeploy restarts the web process (the usual merge-window effect, R0-6).

### 2.9 Test seams (production values in brackets)

| seam | use |
|---|---|
| env `ENABLE_SIZE_FAIR_OFFSIZE_LISTING` via `monkeypatch.setenv` [unset] | both flag states; truthy / falsy matrices |
| env `ENABLE_FIELD_STATUS_METADATA`, `ENABLE_KB_INGEST` [unset] | the U2 rows and the full-configuration PIN rows |
| env `ENABLE_EXACT_PRICE_GATE` [unset = ON] | E08 both states; the projection shape under gate ON (copy) and OFF (identity) |
| env `ENABLE_FRAGRANCE_SIZE_RECONCILE_FIX` [a set variable name per T1:117; value never read] | the pipeline rows run it ON and OFF where the fixture's target depends on it |
| `price_service.size_fair_listing_eligibility`, `price_service.parse_listing_title_ml` (module attributes, looked up through the module at call time by RB) | call recorders (zero calls with the flag OFF) and the per-side raise (B07) |
| `response_builder._size_fair_step` (module attribute) | the whole-step raise (B08) |
| `source_router.registry_tier` | the global-tier and raising-lookup rows (E06) |
| the S17-style SCS stub harness (tests/test_s81_s17_kb_ingest.py `_install` / `_compare`, t17:480-600) with the REAL `reconcile_pair_fairness` (NOT stubbed), `svc._get_price` returning the fixture prices, `svc._price_candidates = {}`, `classify_category_llm` returning fragrances | the pipeline rows P01-P08 |
| the LLM dispatch seam under `generate_comparison` (the RED agent measures the exact attribute, e.g. the router or `guarded_llm_create` the ES verdict call reaches, and records the user message; no network) | P02 |

RB looks up the PS helpers through a function-local `from app.services import price_service as _ps_sf` and calls `_ps_sf.size_fair_listing_eligibility(...)` so a module-attribute recorder sees every call (the BL4 discipline).

## 3. Change list (the order GREEN applies it)

1. Byte copies (shutil.copyfile) of PS, RB, KI into `<SP>/INC-X1/green/` with sha256 recorded; the mutation lock `<W>/.qa-mutation.lock` for any later mutant work.
2. PS: `size_fair_offsize_listing_enabled()` beside `frag_reconcile_fix_enabled` (after PS:4923); `SIZE_FAIR_REASONS`, `_SIZE_FAIR_TITLE_ML_RE`, `parse_listing_title_ml`, `size_fair_host`, `size_fair_listing_eligibility`, `size_fair_partner_size_ml` after `_is_genuine_bh_candidate` (after PS:17124, so the genuine set and predicate are defined above them).
3. PS: `_mark_size_pending(*products, target_ml=None)` with the stash branch (PS:2402-2417), and the four call sites PS:2353 / 2392 / 2395 / 2398 pass `target_ml`.
4. RB: the pop + flag read + step call after RB:1765; `_size_fair_step`, `_size_fair_winner_evidence` and `_SIZE_FAIR_EVIDENCE_PHRASE` as module-level definitions near `_compute_cache_observability` (RB:49); the metadata / evidence block before RB:2180.
5. KI: the `other_size` arm in `_status_one` (KI:203-207) and the `run_job` gap rule (KI:480); the module docstring gains one sentence naming the amended state (KI:13-14).
6. Tests: the frozen RED files `tests/test_inc_x1_size_fair.py` and `tests/test_inc_x1_pipeline.py` (+ `tests/fixtures/inc_x1_flag_off_golden.json` written by the RED agent at base) are NOT edited; GREEN adds `tests/test_inc_x1_gate_rows.py` only if the gate rules gate rows.
7. CLAUDE.md: the block of section 8 after the newest block before `## Tests` (at base: after the S81-04c block, CLAUDE.md:637-640, before :641) and one sentence at the end of the :341 pointer clause.
8. No other file. In particular: no SCS, ES, SS, HR, SR, url_extraction_service.py, image_routes.py, text_routes.py, migration, processors.json, requirements or client file.

## 4. Existing pins

### 4.1 Pins that change deliberately

NONE is expected (measured, Q3): no test names `_mark_size_pending` (git grep tests/ at base: zero hits); every `size_mismatch` test (tests/test_category_fairness.py, test_correctness_concentration_size.py, test_exact_match_contract.py, test_frag_size_capture.py, test_fragrance_size_reconcile_fix.py, test_genuine_reach_cascade.py, test_m18_region_guard_prescoring.py, test_m6_c1_normalize_and_sitemap_match.py, test_pair_size_basis_fairness.py, test_pair_size_reselection.py, test_prescoring_showable_guard.py, test_price_size_reconcile.py, test_response_builder_price_pending.py, test_sitemap_discovery.py, test_ws5_honesty.py) runs with the X1 flag unset, where the pend is byte-identical; the D05 vocabulary pin (tests/test_s81_s17_kb_ingest.py:110-125) never sees a size pend (1.5); the winner_evidence carriers are flag-free. The D05 vocabulary AMENDMENT (one price state `other_size`, G3:283-291 / G3:351 "the 2.2 vocabulary only") is this unit's ruling R-X1-10 recorded in the spec and the CLAUDE.md block, not a test edit. If any 4.2 member goes red at GREEN, that is a finding for the gate (an E-row needs a ruling), never a weakening.

### 4.2 Pins that must stay green and unedited

The fifteen `size_mismatch` files above; tests/test_s81_s17_kb_ingest.py and tests/test_s81_g3_gate_rows.py (D05, the S4 / S5 exposure rows, the gap rows); tests/test_winner_evidence_scoring_v2.py, tests/test_winner_evidence_prod_fixtures.py, tests/test_w4_12_display_contract.py, tests/test_review_density_verdict.py, tests/test_m21_brand_dedup_and_verdict_copy.py (winner_evidence); tests/test_s75_fanout_identity.py (the FY25 nine digests), tests/test_s81_s20_result_gate.py, tests/test_s81_s22_compare_runs.py + tests/test_s81_s22_gate_rows.py (field_status in the run row), tests/test_s81_s18_kb_first_serve.py, tests/test_s81_s11b_result_aggregates.py, tests/test_s81_s18b_store_label.py, tests/test_s81_g8_gate_rows.py (builder goldens); tests/test_s81_kb_schema.py, tests/test_s81_s15_registry_robots.py, tests/test_s81_s03_llm_ledger_v2.py, tests/test_s81_d22_nightly_learning.py (`D05_FIELDS` literal, :1559), tests/test_eval_genuine_methods_parity.py, tests/test_genuine_predicate_parity.py (source scanners of PS / RB / KI); tests/test_streaming.py; the named source-scanning pins; the CLAUDE.md readers by the import graph (tests/test_ci_gates.py, test_behavior_dimension_translation.py, test_s81_s04_spend_breaker.py, test_s81_s08b_legacy_fingerprint.py, test_s81_s08b_gate_rows.py, test_s81_s23_bypass_retire.py).

## 5. RED tests (hermetic; no network, no live marker, no .env)

Files: `tests/test_inc_x1_size_fair.py` (unit level: PS helpers, the pend, the builder, KI) and `tests/test_inc_x1_pipeline.py` (the SCS stub pipeline), plus the golden `tests/fixtures/inc_x1_flag_off_golden.json` the RED agent records AT BASE (canonical JSON of the C1 / C2 / C3 sync bodies and stream event lists with the VOLATILE keys of t17:102-104 removed; literals, no digest constant named with a gitleaks keyword). Missing symbols are read with `getattr(module, name, None)` and asserted present, so every RED fails at base on an AssertionError only. Every PIN row and every flag-OFF row runs WITH the full configuration (`ENABLE_FIELD_STATUS_METADATA`, `ENABLE_KB_INGEST`, `ENABLE_EXACT_PRICE_GATE`, `ENABLE_FRAGRANCE_SIZE_RECONCILE_FIX` set to "true", the X1 flag "false" AND, in a second parametrization, unset) and with call recorders on `price_service.size_fair_listing_eligibility` and `price_service.parse_listing_title_ml` (installed with `raising=False`, asserted at zero calls), so a not-gated mutant is KILLED.

Fixtures (synthetic; hosts `store-a.example.com`, `store-b.example.com`, `store-z.example.com`):
- C1: products[0] "Creed Aventus EDP", price `{"amount": 133.46, "currency": "BHD", "source_method": "woo_store_api", "url": "https://store-b.example.com/product/aventus-100ml", "title": "Creed Aventus EDP 100ml", "retailer": "store-b.example.com", "estimated": False, "_cached": False}`; products[1] "Parfums de Marly Layton EDP", found price `{"amount": 85.0, "currency": "BHD", "source_method": "woo_store_api", "url": "https://store-a.example.com/product/layton-125ml", "title": "Parfums de Marly Layton EDP 125ml", "retailer": "store-a.example.com", "estimated": False, "_cached": False, "in_stock": True, "raw_data": {"source_method": "woo_store_api"}}`; both category "fragrances".
- C2: "Lancome La Vie Est Belle EDP" at 34.0 "... EDP 100ml" (store-b) vs "YSL Libre EDP" found at 39.0 "YSL Libre EDP 90ml" (store-a).
- C3 (negative control): "Armani Acqua di Gio Profumo" parked converted 40 ml fallback `{"amount": 30.5, "currency": "BHD", "source_method": "converted_usd", "url": "https://store-z.example.com/products/adg-profumo-40ml", "title": "Armani Acqua di Gio Profumo 40ml", "converted_usd": 81.0}` vs "Versace Eros EDP" 25.0 "Versace Eros EDP 100ml" (store-a).
- Calibration PIN K-CAL (green at base): `is_price_showable` is True on each fixture price with its own name and category "fragrances" under the exact gate ON, and `target_pair_size_ml` gives 100.0 for each pair (so the fixtures exercise outcome 2, not a guard). If K-CAL is red at base the RED agent adjusts the fixture, never the rule.

### 5.1 `tests/test_inc_x1_size_fair.py`

| # | test | assertion | at base | satisfied by |
|---|---|---|---|---|
| F01 | flag truthy matrix | `size_fair_offsize_listing_enabled()` True for "true", " TRUE ", "On", "1", "yes" | RED (symbol absent) | 2.1 |
| F02 | flag falsy matrix | False for unset, "", "false", "0", "off", "no", "garbage", " 2 " | RED | 2.1 |
| F03 | read per call | setenv true -> True, then setenv false -> False on the same import | RED | 2.1 |
| T01 | one token | `parse_listing_title_ml("Parfums de Marly Layton EDP 125ml") == (125, None)` | RED | 2.2 |
| T02 | spacing | "Layton 125 ML", "Layton 125-ml" -> 125; "EDP100ml" -> 100; "Eau de Parfum 90ML Spray" -> 90 | RED | 2.2 |
| T03 | decimal size | "7.5ml" -> (None, "no_title_size") | RED | 2.2 |
| T04 | two sizes | "50ml / 100ml" -> (None, "multi_size_title") | RED | 2.2 |
| T05 | repeated size | "100ml 100 ml" -> (100, None) | RED | 2.2 |
| T06 | Arabic-only | "125 " + chr(0x645) + chr(0x644) -> no_title_size | RED | 2.2 |
| T07 | Arabic-Indic digits | chr(0x661)+chr(0x662)+chr(0x665) + "ml" -> no_title_size | RED | 2.2 |
| T08 | boundaries | "1,125ml", "0ml", "12345ml", "100mlx", "100 mls", "100  ml" -> no_title_size | RED | 2.2 |
| T09 | not a title | None, "", "   ", 5, ["x"] -> (None, "no_title") | RED | 2.2 |
| H01 | host | `size_fair_host("https://www.Store-A.example.com:443/p/x?y=1") == "store-a.example.com"`; None / 5 / "not a url" -> "" | RED | 2.2 |
| E01 | eligible | C1 Layton stash, target 100.0 -> (True, None, 125) | RED | 2.2 |
| E02 | not_bhd | currency "USD"; amount 0; float("nan"); float("inf"); "85.0"; True -> not_bhd | RED | check 2 |
| E03 | estimated | `estimated: True` with a genuine method -> estimated | RED | check 3 |
| E04 | converted | method "converted_usd"; method "page_scrape_jsonld" with raw_data.source_method "converted_usd" -> converted | RED | check 4 |
| E05 | not_genuine | method "serper_shopping"; method None -> not_genuine | RED | check 5 |
| E06 | global tier | `registry_tier` patched to "global" for store-a -> global_tier; patched to raise -> eligible | RED | check 6, SL9 |
| E07 | no_url | url None / "" / "  " / 5 -> no_url | RED | check 7 |
| E08 | listing url | ".../collections/perfume" and ".../search?q=layton" -> listing_url, with ENABLE_EXACT_PRICE_GATE "true" AND "false" | RED | check 8 |
| E09 | not_showable | title "Parfums de Marly Layton EDP 125ml sample" (the sample rule) -> not_showable | RED | check 9 |
| E10 | title codes | title None -> no_title; "Parfums de Marly Layton EDP" -> no_title_size; "Parfums de Marly Layton EDP 75ml / 125ml" -> multi_size_title | RED | check 10 |
| E11 | target codes | target None -> no_target; title "... 100ml" with target 100.0 -> size_equals_target | RED | checks 1, 11 |
| E12 | precedence | a price that is USD AND converted AND url-less -> not_bhd (the first failing check) | RED | 2.2 order |
| E13 | purity | the input price deep-equals its snapshot after the call; the dict `is_price_showable` received is not the input object (recorder on `price_service.is_price_showable` capturing `id`) | RED | check 9 copy |
| E14 | partner helper | C1 Aventus price, target 100.0 -> 100; title "Creed Aventus EDP" -> None; "50ml / 100ml" -> None; converted -> None; listing url -> None; "90ml" -> None; a pending dict -> None | RED | 2.2 |
| S01 | stash ON | `reconcile_pair_sizes(C1)` with the flag ON: products[1]["price"] == `{"amount": None, "currency": "BHD", "unavailable": True, "reason": "size_mismatch"}` exactly; best_price / retailer None when present; `products[1]["_offsize_listing_src"] == {"price": <the found price>, "target_ml": 100.0}`; the stashed dict and its `raw_data` are NOT the found objects (identity); products[0] carries no stash | RED | 2.2 |
| S02 | stash OFF (PIN) | the same call, flag "false" and unset, full configuration: both product dicts equal the base literal; no `_offsize_listing_src`; recorders zero | PIN | I1 |
| S03 | target None | a pair whose sizes differ with no derivable target (two non-fragrance names, category not fragrances, via `reconcile_pair_sizes` directly) ON -> both stashes with `target_ml` None | RED | 2.2 |
| S04 | keyword | `_mark_size_pending(p, target_ml=100.0)` does not raise (a TypeError at base is caught and asserted False) | RED | 2.2 |
| S05 | stash failure | the found price holds an object whose `__deepcopy__` raises RuntimeError: no stash key, the pend identical to base, exactly one WARNING record `[SIZE_FAIR] stash skipped type=RuntimeError` | RED | 2.2 |
| S06 | positional (PIN) | `_mark_size_pending(p0, p1)` with the flag unset gives the base pending dicts | PIN | I1 |
| B01 | C1 projection | `build_comparison_response` (the argument set of tests/test_response_builder_price_pending.py's builder helper) on the reconciled C1 dicts, flag ON: `overview.products[1].price == {pending..., "offsize_listing": {"amount": 85.0, "currency": "BHD", "size_ml": 125, "retailer": "store-a.example.com", "url": ".../layton-125ml", "title": "Parfums de Marly Layton EDP 125ml", "source_method": "woo_store_api", "per_ml": 0.68}}`; `overview.products[0].price` = its base price plus `size_ml` 100 and `per_ml` 1.3346 | RED | 2.3 |
| B02 | alias + no stash | `products[i].price == overview.products[i].price` for both i; no `_offsize_listing_src` at any depth of the body (recursive walk) | RED | 2.3 |
| B03 | shape | the object's key set is exactly the eight; `amount` float rounded to 3; `size_ml` int not bool; `per_ml` float rounded to 4 | RED | 2.5 |
| B04 | fresh object | a stash price carrying `_cached`, `_cache_source`, `guard_rejected`, `raw_data`, `in_stock`, `confidence`: none of them in `offsize_listing` (exact gate ON and OFF) | RED | 2.3 step 1 |
| B05 | no in-place write | the pending dict object and the partner price object captured before the build carry no new key after it | RED | I3 |
| B06 | mid-request flip | a stash on products[1] with the flag OFF at the build: no `_offsize_listing_src` in the body; the body equals the same build without the stash (at base the alias ships the stash) | RED | U1 |
| B07 | per-side error | the eligibility recorder raises for side 1: entry `{product_index: 1, outcome: "pended", reason: "error", ...}`, no offsize on side 1 | RED | 2.3 step 1 |
| B08 | whole-step failure | `response_builder._size_fair_step` patched to raise RuntimeError: the build returns (asserted inside try/except, so a propagating raise is an assertion failure), one WARNING `[SIZE_FAIR] projection skipped: RuntimeError`, the body equals the flag-OFF body, no `metadata.size_fair` | RED | 2.3 |
| B09 | not a size pend | a stash beside a `pending_genuine` price: entry pended / not_size_pend; no offsize | RED | check 12 |
| B10 | no stash | a size pend without a stash, flag ON: entry pended / no_stash, `listing_cached` None | RED | check 0 |
| B11 | partner pended by the chokepoint | partner title "Creed Aventus EDP 100ml sample": partner pending_genuine; Layton's offsize without `per_ml`; no partner `size_ml` | RED | 2.3 step 2 |
| B12 | partner variants (brief P7) | partner title without a token / with two tokens / a converted partner / a listing-url partner (exact gate OFF so it stays shown): offsize present without `per_ml`; the partner has no `size_ml` / `per_ml` | RED | 2.3 step 2 (c) |
| B13 | case D | both sides size pends, both eligible: each object carries its own `per_ml`; neither price has `size_ml` | RED | 2.3 step 2 (b) |
| B14 | winner_evidence | flag ON, winner 0, runner-up 1 a size pend, `scoring_result["winner_evidence"] = ["Creed Aventus has a confirmed Bahrain price while the other relies on an indicative figure", "Creed Aventus draws stronger reviewer ratings"]`: `scoring_v2.winner_evidence == ["Creed Aventus draws stronger reviewer ratings"]`; the `scoring_result` list object is unchanged | RED | R-X1-9 |
| B15 | evidence kept (PIN) | flag OFF (full configuration): unchanged; flag ON with the WINNER as the size pend: unchanged | PIN | R-X1-9 |
| B16 | size_fair entries | C1 ON: `metadata.size_fair == [{"product_index": 1, "outcome": "offsize_listing", "reason": None, "listing_cached": False, "per_ml": True}]` | RED | 2.3 step 4 |
| B17 | absent (PIN) | ON with no size-pended side and no stash: no `metadata.size_fair` | PIN | 2.5 |
| B18 | caller wins (PIN) | `metadata={"size_fair": "caller"}` -> `"caller"` | PIN | RB:2180 |
| B19 | log line | caplog INFO: exactly `[SIZE_FAIR] product_index=1 outcome=offsize_listing reason=none listing_ml=125 target_ml=100 host=store-a.example.com cached=false`; no record contains "Layton", "Aventus", the query, "/product/" or "85" | RED | 2.6 |
| B20 | closed codes | over the E02-E11 / B07 / B09 / B10 cases: every `reason` in `metadata.size_fair` and every `reason=` token in the log is in `SIZE_FAIR_REASONS` (16) or none | RED | 2.2 |
| B21 | scores untouched (PIN) | C1 ON vs OFF: `scoring`, `overview.winner`, `scoring_v2.dimensions`, `scoring_v2.factual_verdict`, every `value_badge`, `overview.confidence`, `best_price`, `retailer`, `price.amount` / `unavailable` / `reason` equal | PIN | I4 |
| B22 | cached listing | a stash price with `_cached: True`: entry `listing_cached` True and `cached=true` in the line | RED | 2.3 step 4 |
| W01 | writer SCS:7814 | the converted_fallback dict shape (method converted_usd, `converted_usd` amount, a PDP url, title "... 40ml") as the stashed price: pended / converted | RED | check 4 |
| W02 | writer SCS:8003 | a `converted_usd` Tier-1 Serper dict (`retailer`, `url`, `title`): pended / converted | RED | check 4 |
| W03 | writer SCS:8018 | a GENUINE Tier-1 dict (method "local_bhd") on a shopping listing url ("https://store-a.example.com/search?q=layton"): pended / listing_url with ENABLE_EXACT_PRICE_GATE ON and OFF | RED | check 8 |
| W04 | writer SCS:8744 | a page-scrape dict (method "page_scrape_jsonld", PDP url ".../product/layton-125ml", title "... 125ml", `_cached` False): offsize_listing (eligible, SL14) | RED | 2.2 |
| K01 | other_size with host | `kb_ingest.field_status` on a C1 body whose products[1].price is the pend + offsize_listing: price entry == `{"state": "other_size", "source": "store-a.example.com", "reason": "size_mismatch", "as_of": None, "rung": None}` | RED | 2.4 |
| K02 | other_size without host | the pend alone (no offsize_listing): `{"state": "other_size", "source": None, "reason": "size_mismatch", "as_of": None, "rung": None}` | RED | 2.4 |
| K03 | other pends (PIN) | a `pending_genuine` pend -> `unknown / no_price`; an estimate -> `unknown / estimated` (base literals) | PIN | 2.4 |
| K04 | size entry (PIN) | for a size pend with `price.size` "125ml" -> `known / listing`; without size and specs `{}` -> `unknown / no_size` (equal to base) | PIN | R-X1-11 |
| K05 | gap rule | `run_job` on a snap whose product field_status has price state `other_size` (stub service-role client recording every `table().upsert()`): a `kb_gaps` row with field "price" is sent (at base KI:480 skips it) | RED | 2.4 |
| K06 | gap rows equal (PIN) | `build_job` + `run_job` end to end on the same C1 body: the sent `kb_gaps` rows equal the base literal | PIN | R-X1-11 |
| K07 | vocabulary | over K01-K04: price states in {fresh, stale, unknown, other_size}; `other_size` only with reason `size_mismatch`; every non-price field in S17's VOCAB_STATES | RED | R-X1-10 |
| K08 | X1-independent (PIN) | the field_status of K01's input is equal with the X1 flag ON and OFF | PIN | I5 |
| K-CAL | calibration (PIN) | 5 intro | PIN | fixtures |

### 5.2 `tests/test_inc_x1_pipeline.py` (S17-style stub harness, the REAL reconcile)

| # | test | assertion | at base | satisfied by |
|---|---|---|---|---|
| P01 | flag-OFF identity (PIN) | X1 "false" and unset, full configuration EXCEPT both D05 flags unset (so I5 is pinned on the production configuration), recorders: the C1 / C2 / C3 sync bodies and stream event lists equal `tests/fixtures/inc_x1_flag_off_golden.json` (recorded at base); recorders zero | PIN | I1 |
| P02 | verdict prompt | C1 and C2 with the real `generate_comparison` over the LLM dispatch stub: the recorded user message is byte-identical ON vs OFF | PIN | I2 |
| P03 | before the builder | C1 ON vs OFF: every SSE event before `complete` equal; `scoring`, `overview.winner`, `scoring_v2.dimensions`, `factual_verdict`, `value_badge`, `overview.confidence` equal | PIN | I2, I4 |
| P04 | no stash anywhere | ON: no `_offsize_listing_src` at any depth in the sync body, the stream complete, the sync partial after the reconcile (the verdict stub sleeps past `STREAM_HARD_CAP_SECONDS`), the stream tail-deadline partial and the stream hard-cap partial | PIN | U1 |
| P05 | C1 ON end to end | sync and stream complete: products[1] / overview.products[1] price as B01; `metadata.size_fair` one entry, outcome offsize_listing | RED | 2.3 |
| P07 | C3 negative control | ON: Armani stays the plain pend, no offsize; `metadata.size_fair[0] == {"product_index": 0, "outcome": "pended", "reason": "converted", "listing_cached": None, "per_ml": False}` (`listing_cached` None: the parked dict carries no `_cached`) | RED | 2.2 |
| P08 | D05 through the pipeline | `ENABLE_FIELD_STATUS_METADATA` ON, X1 OFF and ON: `metadata.field_status[1]["price"]["state"] == "other_size"` (source None with X1 OFF, "store-a.example.com" with X1 ON) | RED | 2.4 |

Counts: RED 60 (F 3, T 9, H 1, E 14, S 4, B 18, W 4, K 4, P 3); PIN 15 (S02, S06, B15, B17, B18, B21, K03, K04, K06, K08, K-CAL, P01, P02, P03, P04). The RED runner call: `PYTHONIOENCODING=utf-8 C:/Users/SynAckITPC/Documents/AI/.venv-qaren/Scripts/python.exe <SP>/harness/pyt.py --bound 600 --tag inc-x1-red --log <SP>/INC-X1/red/inc-x1-red.log --cwd C:/Users/SynAckITPC/Documents/AI/sc-inc-x1 -- tests/test_inc_x1_size_fair.py tests/test_inc_x1_pipeline.py -q` (DEFERRED TO RED; the RED gate expects 60 failed by AssertionError and 15 passed at base).

(The brief's P6 writer rows are W01-W04 above; P1-P11 of the brief map: P1 -> P01 + S02; P2 -> P02; P3 -> P03 + B21; P4 -> P04 + B02; P5 -> B01 + P05 + B16; P6 -> E02-E11 + W01-W04; P7 -> B12 + B13; P8 -> K01-K08 + P08; P9 -> B14 + B15; P10 -> B19 + B20; P11 is X1-C's own RED, not in this unit.)

## 6. Mutation table (on the GREEN bytes; each mutant on a byte copy, one exact-string edit matching once, the killing rows via pyt.py -k with `--bound 600`, restored and sha256-compared; KILLED = an assertion failure)

| M | mutant | killed by |
|---|---|---|
| M01 | the flag reader drops `.strip()` | F01 (" TRUE ") |
| M02 | the flag read cached in a module constant | F03 |
| M03 | the stash branch runs without the flag check | S02 |
| M04 | the stash stores the found dict itself (no deep copy) | S01 (identity) |
| M05 | the pop moved inside `if _sf_on:` | B06 |
| M06 | the projection writes `sp["offsize_listing"] = obj` in place | B05 |
| M07 | check 8 skipped when `exact_gate_enabled()` is False | E08 (gate "false"), W03 |
| M08 | check 4 reads only the top-level method | E04 (raw_data case) |
| M09 | `parse_listing_title_ml` uses the base `_SIZE_ML_RE` | T03 ("7.5ml" -> 5) |
| M10 | multi-size takes `min()` | T04 |
| M11 | check 11 removed | E11 (size_equals_target) |
| M12 | check 12 (E7) removed | B09 |
| M13 | `per_ml` added without the partner test | B12 |
| M14 | `per_ml` rounded to 2 | B01 (1.3346) |
| M15 | the evidence filter applied when the WINNER is the pend | B15 |
| M16 | the evidence filter mutates the scoring_result list | B14 |
| M17 | KI's other_size arm gated on the X1 flag | K08, P08 (X1 OFF) |
| M18 | the KI gap rule not widened | K05 |
| M19 | the `[SIZE_FAIR]` line prints `full_name` | B19 |
| M20 | `metadata.size_fair` stamped after the caller merge | B18 |
| M21 | check 9 runs on the input dict (no copy) | E13 |
| M22 | the RB step without its try/except | B08 |
| M23 | the object copies the whole stash price | B04, B03 |
| M24 | `listing_cached` taken from `metadata.cache_hit` | B22, B16 |
| M25 | check 6 lets a raising tier lookup refuse | E06 (raise -> eligible) |
| M26 | the chokepoint category replaced by `category_used` | NOT KILLED by design unless the RED adds a row where `pd.category` and the inferred category differ; reported as a candidate equivalent for the ruling Q-S1 |

## 7. Comm set and gates for GREEN (cheapest first; one pytest at a time; every run through pyt.py)

1. Byte hygiene: bytes > 127 = 0 in the new files; `git diff --stat` hunks only (no whole-file CRLF diff); `git diff` added-line sweep (no 8-digit run, no `@gmail`, no `+973`, no key shape, no keyword-named 64-hex).
2. Lint and syntax: `<venv python> -m ruff check --select E9,F63,F7,F82 --no-cache app/services/price_service.py app/services/response_builder.py app/services/kb_ingest.py tests/test_inc_x1_size_fair.py tests/test_inc_x1_pipeline.py`; `<venv python> -m py_compile` on the same files; `json.loads` of the golden fixture.
3. The RED files at HEAD: all 75 nodes pass (bound 600, tag `inc-x1-green-red`), with the flag unset in the runner environment (the rows set it themselves).
4. The mutation table (section 6), one mutant per runner call, bound 600, tags `inc-x1-mut-MNN`.
5. The CI-order set, one process, sorted (bound 1200, tag `inc-x1-ciorder`): tests/test_category_fairness.py, test_fragrance_size_reconcile_fix.py, test_inc_x1_pipeline.py, test_inc_x1_size_fair.py, test_pair_size_basis_fairness.py, test_pair_size_reselection.py, test_prescoring_showable_guard.py, test_price_size_reconcile.py, test_response_builder_price_pending.py, test_s81_g3_gate_rows.py, test_s81_s17_kb_ingest.py, test_s81_s20_result_gate.py, test_streaming.py, test_winner_evidence_prod_fixtures.py, test_winner_evidence_scoring_v2.py, test_ws5_honesty.py (the unit touches no /health and no lifespan path, so the P73 lifespan-first ordering is not required).
6. The comm set (zero-regression gate): base and head, chunks of at most 25 files, bound 1200, `comm -13` of the sorted FAILED node ids EMPTY; a branch-only failure is re-run against base once.

The comm set at base, derived by `closure.py` (in the notes folder) and stored as `comm_set.txt`: 678 test files of 767 `tests/test_*.py`, sha256 of the sorted LF list `3850de9e7dd19d8014f73991c18fd83d2fc356b998ab0ad8956507067c42ea35`. Rule applied:
- the app/ importer closure of the three edited modules to a fixpoint (69 modules, `app.main` among them, so EVERY `app.main` / `TestClient` user joins);
- every test referencing a closure module by import, module path or string path;
- every glob / rglob / os.walk / listdir / scandir walker over app/ (41 files at base, e.g. tests/test_model_config.py, test_s81_kb_schema.py, test_s81_s05_request_context.py, test_hermeticity_pins.py, test_s81_s15_registry_robots.py);
- the named source-scanning pins (test_model_config.py, test_model_config_enforced.py, test_prompt_fence.py, test_u3c_store_false_pin.py, test_start_command*.py, test_migration_index_predicate_immutability.py, test_openai_key_log_hygiene_s69.py, test_sentry_channels_u8d_unit.py);
- the CLAUDE.md readers by the import graph (test_ci_gates.py, test_behavior_dimension_translation.py, test_s81_s04_spend_breaker.py, test_s81_s08b_legacy_fingerprint.py, test_s81_s08b_gate_rows.py, test_s81_s23_bypass_retire.py), because CLAUDE.md changes;
- the two new RED files;
- MINUS the four tests/test_precommit_hook*.py files (.githooks is not edited).
The derivation is a grep-plus-import heuristic; GREEN re-derives the set at HEAD with the same rule and unions any file the re-derivation adds (an edited test-support helper adds its importers; none is edited here). No migration, processors.json, legal text, SmartCompareApp file or `.github` file changes, so those reader classes add nothing beyond the walkers already in the set. LC-6: a stored base record for (6b909e0a, this set hash) is reused when present; otherwise the base run is part of the RED round.
7. The fourteen backend-scanning client fences by path (B-5 command, after the H5 jest probe), because the footprint touches app/; none reads PS, RB, KI or the CLAUDE.md lines this unit adds (measured: their repo-root reads are docs/privacy-data-inventory.md, docs/brand, scripts/render_myez_icons.py, app/services/extraction_service.py, app/services/referral_service.py, app/services/robots_eval.py, app/services/sitemap_discovery_service.py, .github/workflows/ci.yml). No full jest suite (LC-7: a backend unit with no client file).
8. The adversary (the orchestrator classifies; measured footprint: PS / RB / KI + tests + CLAUDE.md, no FOCUS surface: no auth, quota, legal, consent, security middleware, migration, Redis / Lua, App-Review-visible client surface or secret; the response-contract change is additive and dark, read by no live bundle), so LC-1 SAFE with ONE adversary is the measured proposal.

## 8. CLAUDE.md block, anchor and owner steps

Anchor: after the newest block before `## Tests` (at base the S81-04c block, CLAUDE.md:637-640; if MON1 or G-INC-1 merges first, after theirs, one blank line before the heading), plus one sentence appended to the :341 pointer clause in merge order: "INC-X1 SIZE-FAIRNESS adds `ENABLE_SIZE_FAIR_OFFSIZE_LISTING` (dark): the rows of the **INC unit (INC-X1 SIZE-FAIRNESS, ...)** block."

Block text (GREEN may tighten wording, not content):

**INC unit (INC-X1 SIZE-FAIRNESS, server half, 2026-11-1x; ONE new flag, default OFF, read per call; SAFE (proposed), one adversary; spec `.qa-s80/INC-X1_UNIT_SPEC.md` of the unit worktree over the brief `INC_X1_BRIEF.md` (R-X1-1..21) in the incident lane's state folder):**
- `ENABLE_SIZE_FAIR_OFFSIZE_LISTING` (`app/services/price_service.py::size_fair_offsize_listing_enabled`, read once per `_mark_size_pending` call and once per `build_comparison_response`). **Effect ON:** a size-pended price (`reason size_mismatch`) keeps `amount` null, `unavailable` true and every score, winner, savings figure and SSE event as today; the found listing rides the additive `price.offsize_listing` {amount BHD 3 dp, currency, size_ml from the listing's own title (one strict ml token), retailer, url, title, source_method, per_ml (BHD per ml, 4 dp) only when the partner's own listing also states one size}, only for a genuine non-converted, non-estimated Bahrain product page that passes `is_price_showable` (E1-E7); an on-basis partner gains `price.size_ml` / `price.per_ml` under the same rule; `metadata.size_fair` (per size-pended side: product_index, outcome offsize_listing | pended, a closed reason code, listing_cached, per_ml); the false "has a confirmed Bahrain price while the other relies on an indicative figure" entry leaves `scoring_v2.winner_evidence` when the runner-up is a size pend; ONE INFO `[SIZE_FAIR] product_index=.. outcome=.. reason=.. listing_ml=.. target_ml=.. host=.. cached=..` per size-pended side. The stash `_offsize_listing_src` is popped by the builder on every call (unflagged, a no-op when absent). **Unflagged, dormant:** the D05 price entry of a size pend is `other_size` (source = the offsize host or null, reason size_mismatch) instead of `unknown / no_price`, and the kb_gaps rule treats `other_size` like `unknown`; it runs only with `ENABLE_FIELD_STATUS_METADATA` or `ENABLE_KB_INGEST` ON (the S81-17 vocabulary amended by this one state). **Flag OFF:** byte-identical on every body, partial, SSE frame, saved row, log and the verdict prompt (pinned by `tests/test_inc_x1_size_fair.py` + `tests/test_inc_x1_pipeline.py`). Neither live bundle reads the new keys: nothing changes on a phone until the X1-C client half ships with the result-page OTA. **Owner steps (names only):** approve the unflagged D05 entry's class; after the flip pause lifts, flip the flag on web in one canary window; the phone proof runs only after the X1-C OTA. **Merged is not proven.** **Rollback:** unset the variable (per call, immediate; rows saved while ON keep the key).

Owner steps (names only, in order; the brief's O1-O8):
1. (O1) N5 / N5b is RULED (2026-11-11); the relay records it as a ledger line (IR:93 still lists N5 open).
2. (O4) approve the class of the unflagged D05 price entry (dormant: both D05 flags OFF on web). Blocks the X1-S RED.
3. (O2, O3) hear that the winner stays as today (C1's winner partly came from the blanked price, T1:176); confirm the 100 ml basis and that the completeness score gives no point for an `offsize_listing` (default no). Nothing in X1 waits on them.
4. (O6) after the flip pause lifts (the OpenAI credential works, H2), flip `ENABLE_SIZE_FAIR_OFFSIZE_LISTING` on web in its own canary window; the relay sets it on the owner's yes. Rollback: unset it.
5. (O5, O7) approve the X4 price-card design and read every new Arabic string; approve and publish the OTA carrying X1-C; take it on the phone.
6. (O8) run 8b and send the screenshots with the row ids.

## 8b. PROOF ON THE PHONE (H6; from IR:100 as restated by the brief section 4)

Not provable by this unit alone: X1-S changes nothing on either bundle, so a screenshot before the X1-C OTA shows today's `results.price.pending` line with the flag ON or OFF and proves nothing; it must not be offered. The record's backing "products[1].price.amount not null" and IR:162 rule (c) can never pass under the ruled design (`amount` stays null, `reason` stays size_mismatch) and are replaced below.

When it CAN pass: X1-S merged and deployed; the flip pause lifted; the flag ON on web; X1-C merged with the result-page update and published in an approved OTA; the phone took it (close and reopen twice). No AI text is read anywhere in this proof.

Pairs (Arabic UI, golden set IR:140-145, typed as before): pair 1 Creed Aventus EDP vs Parfums de Marly Layton EDP (target: Layton); pair 2 Lancome La Vie Est Belle EDP vs YSL Libre EDP (target: Libre); pair 3 Armani Acqua di Gio Profumo vs Versace Eros EDP (NEGATIVE control); at least one of pair 4 Dior Sauvage EDP vs Chanel Bleu de Chanel EDP or pair 5 Maison Francis Kurkdjian Baccarat Rouge 540 EDP vs Lattafa Khamrah EDP the first time. Free tier 3 a day: day one pairs 1, 3 and 4 (or 5); day two pair 2 (unless the N6 choice says otherwise).

Must be visible on the Layton card (pair 2 the same for Libre): the amount and the LISTING's size through `results.price.withSize` (digits in the app's digit system); the caption `results.price.differentSizes`; `results.price.perMl` only when the row carries `per_ml`; no price bar, no value bar, no price pill, no "cheaper" / "less" / percent text; neither `results.price.pending` nor `results.honest.notListed`.

Backing in the saved row (`comparisons.full_response`; record the row id and its UTC `created_at`):

| # | key | must hold |
|---|---|---|
| S1 | `metadata.partial` | absent or false |
| S2 | `overview.products[1].price` | `amount` null, `unavailable` true, `reason` "size_mismatch" |
| S3 | `overview.products[1].price.offsize_listing` | present; `amount` = the screenshot's number; `currency` BHD; `size_ml` = the screenshot's size and not 100 |
| S4 | `offsize_listing.title` | exactly one ml token under the strict parse, equal to `size_ml` (this key is also the Q1 measurement) |
| S5 | `.url` / `.source_method` | a Bahrain store host (pair 1 expected the alibaksh.com host, T1:32), not a listing address, a genuine method (expected woo_store_api) |
| S6 | `products[1].price.offsize_listing` | equal to S3; `products[1]` has no `_offsize_listing_src` |
| S7 | `metadata.size_fair` | exactly one entry: product_index 1, outcome offsize_listing, reason null |
| S8 | `per_ml` | present only if `overview.products[0].price.title` holds exactly one ml token; then round(amount / size_ml, 4), and the partner's `size_ml` / `per_ml` present and consistent |
| S9 | `scoring_v2.winner_evidence` | no "has a confirmed Bahrain price while the other relies on an indicative figure" entry when Layton is the runner-up |

Backing in the deploy log for that request's minutes (read-only, the relay's usual read): L1 one `[SIZE_FAIR] product_index=1 outcome=offsize_listing ...` line whose host equals S5's and whose `listing_ml` equals S3's `size_ml`; L2 `[PRICE] BH adapter direct hit for ... via <host>` (SCS:7872-7877) for Layton with that host when `listing_cached` is false (legitimately absent when true: the 7-day price cache); L3 no `fairness reconciliation skipped`, no `[SIZE_FAIR] ... outcome=error`, no `[SIZE_FAIR] projection skipped` and no `[SIZE_FAIR] stash skipped` line.

Negative control (pair 3): the Armani card still shows `results.price.pending`; no `offsize_listing` for Armani; if Armani is size-pended, `metadata.size_fair` says pended / converted. Pair 4 or 5: card and row agree; a run with no size pend is reported "control, no size pend", not a pass. A pair whose title holds two tokens or none is reported "not provable on this pair". The result is "proven on pairs X, Y", never "fixed". A hermetic suite is not this proof (H6 d).

## 9. Stated limits

| # | limit |
|---|---|
| SL1 | X1-S changes nothing on either phone bundle; both ignore the new keys until X1-C ships. |
| SL2 | The winner, scores and Home savings stay as today, including a winner that came from the blanked price (C1, T1:176). |
| SL3 | A title stating its size in oz only, in Arabic only, with two ml sizes, with two spaces before "ml", or not at all (a Woo product name without the size, Q5) stays pended as today; the oz converter (PS:4099-4101) is not used. |
| SL4 | A title-less L2 database row (SCS:7109-7128) stays pended (no_title). |
| SL5 | Partial bodies change only by the pop; a stream partial never carries a reconciled dict and can still show two sticker prices at different sizes (R-X1-16). |
| SL6 | A wrong product whose title passes the shipped identity gate is shown with its size (the Versace "for Women" class, T1:59); that guard is INC-X10's. |
| SL7 | The KB never ingests the off-size offer (`_PRICE_KEYS`, KI:264-267). |
| SL8 | The completeness score does not count an off-size listing unless O3 rules otherwise. |
| SL9 | A raising tier lookup counts as not global (PS:17122-17123), as for every genuine price today. |
| SL10 | A hermetic test is not the production proof (H6). |
| SL11 | The converted-price label printed twice on the card is a separate cosmetic defect. |
| SL12 | Only a size-pended pair gains sizes and per-ml figures; two basis prices still show none (PD2 case A, conflict C3 open). |
| SL13 | The D05 SIZE entry is left as at base: a size pend whose found price had a `size` field keeps it on the pending dict and reads `known / listing`; without it the Specs body can print the size "Not listed" line once a D05 flag is ON (pre-existing, dormant). |
| SL14 | A genuine page-scrape price parked by the supplement stage (SCS:8744) is shown when it passes E1-E7 (eligibility by the listing's own properties). |
| SL15 | Removing the price-provenance entry can leave `winner_evidence` empty; no fallback reason ("leads on the overall picture", SS:1015-1024) is recomputed. |
| SL16 | E4 runs with the exact gate as configured: with `ENABLE_EXACT_PRICE_GATE` OFF the identity backstop does not run (PS:1951), so E4 is only the floor / sample / method part; E3 still refuses listing urls in both states. The production value of the exact gate is not in the ledger (default ON in code, PS:4370-4374). |
| SL17 | The `[SIZE_FAIR]` line carries one normalized store host (as the existing `[PRICE] ... via <domain>` line does); no name, title, path or amount. |
| SL18 | `listing_cached` reports the found price's own `_cached` mark; a parked price carries none (null). |

## 10. Out of scope

Per-ml comparison and design (b) (closed); the (a2) scoring change; the 100 ml basis; oz parsing; reconciling the partial paths; the X4 page, the X6 price-bar states, the X7 rows; per-ml on basis prices; the D05 size entry; the X10 identity guard; the non-fragrance `unit_mismatch` path (`_mark_unit_pending`, PS:3164-3180) and the URL compare path (both untouched: no reconcile call, no `make_pending_price` in url_extraction_service.py); Home / Profile savings; the CL3 feedback card; any edit to the LLMUnavailableError log statements (S81-04c); X1-C (its own spec, RED P11 and Arabic read); any flag flip, variable or production read by a build agent.

## 11. Open questions and the answers to the brief

### 11.1 Open questions for the orchestrator (only what measurement could not settle)

- Q-S1 (deviation by measurement): the brief's E4 names `category_used`; the chokepoint every shown price passes uses `pd.get("category") or _infer_category_from_query(name)` (RB:1664). The spec rules the chokepoint's value so E4 is literally the same gate (M26 is the equivalent-mutant candidate if the two never differ in a fixture). Confirm or rule `category_used`.
- Q-S2: the brief lists `no_stash` among the codes but not whether a side that carries a stash but is no longer a size pend gets an entry; the spec writes one (pended / not_size_pend) so the saved row explains every stash. Confirm.
- Q-S3: the strict parser follows the brief literally (one optional space OR hyphen); "100  ml" (two spaces) is refused (SL3). Widen to `\s{0,2}-?\s{0,2}` or keep?
- Q-S4: conflict C3 (sizes on every shown price) and C4 (PD2 citing `cache_hit: false` vs this spec's `listing_cached`) stay open from the brief; X1-S implements the brief (size-pended pairs only; `listing_cached`).
- Q-S5: Q1 cannot be measured read-only (below); the owner or relay may read the Layton and Libre product pages' titles on the two stores before the flip so a two-token title (a pair that cannot pass) is known in advance. A names-only read, no build agent.
- Q-S6: class (LC-1): measured SAFE (no FOCUS surface; dark additive contract read by no bundle). The orchestrator classifies at GREEN.

### 11.2 Answers to the brief's questions

- Q1 (the Layton / Libre titles): NOT MEASURABLE in a read-only round, and not by a replay either: no log line prints a price title (the direct-hit line SCS:7872-7877 prints the name, amount, host and method only) and the pended row keeps no title (T1:117 "title not persisted"). Inferred from the code: each title's SMALLEST ml token is not 100 (otherwise effective_pair_size_ml would give 100 and no pend; the names carry no token, the pending dicts carry no `size`, the specs were `{}`); whether it is ONE token (eligible) or several (multi_size_title) stays UNVERIFIED. Under the flag the first ON comparison measures it: `metadata.size_fair` gives the outcome and `offsize_listing.title` the title (8b S4).
- Q2 (readers of `field_status` outside app/): none counts the states. `git grep field_status` outside app/ and tests/: CLAUDE.md (docs) and migrations/048_compare_runs.sql (a jsonb column) only; no script, no eval runner, no admin page. Inside app/: KI and compare_runs.py:294-305 + :477 (stores the list as is, capped at 16,384 bytes). Client: fieldStatusView.ts:38, :52 and ResultsAccordion.tsx:147 test only `state === 'unknown'`; fieldStatusView.ts:58 turns an `unavailable` price with any other state into kind `none` (today's pending line). So `other_size` moves no metric and removes the false `results.honest.notListed` line.
- Q3 (pins that move): none (4.1). No test names `_mark_size_pending`; the S17 vocabulary pin (tests/test_s81_s17_kb_ingest.py:110-125) never receives a size pend (its pipeline stubs `reconcile_pair_fairness`, t17:545; its `_product` fixture has no pend, t17:240-256); the kb_gaps rule is not pinned on a size pend; the winner_evidence carriers are flag-free; the client `__tests__/s11` rows feed `unknown` / `stale` entries only.
- Q4 (key iteration between the reconcile and the builder): only `_verdict_safe_product` dumps the product (ES:2647-2654), after stripping every `_` key (ES:2522-2526): the stash never reaches the prompt and the bytes are unchanged (P02). `compute_confidence` copies keys but reads named ones (SS:2855, SS:1150-1253). Every other reader uses named keys (table 1.4). The W4-7 block and `_debug_capture_payload` run after the pop.
- Q5 (Woo titles): the title is the Store API product NAME, html-unescaped (woocommerce_service.py:165-166), never a variation attribute; the candidate carries no `size` (:270-279). A store that names the parent product without the size gives no_title_size (SL3). Which of the two BH stores name Layton with "125ml" is UNVERIFIED (Q1).
- Q6 (the parked-price writers): SCS:7814: `dict(select_best(converted rows))`, method `converted_usd`, carries the source's url / title -> converted (W01; the Armani 40 ml case). SCS:8003: a `converted_usd` Tier-1 Serper price -> converted (W02). SCS:8018: a GENUINE Tier-1 price whose url `_is_listing_url` flags (a shopping "local" / search url; gated by `_park_listing_url_tier1_enabled`, default ON, SCS:2846) -> listing_url with the exact gate ON or OFF (W03). SCS:8744 `_maybe_park_supplement`: whatever passed `is_price_showable(full_name, price_obj)` at the supplement stage (iHerb SCS:8773, pharmacy SCS:8806, page scrape SCS:8859, Tier-2 SCS:9002); a genuine page-scrape price on a Bahrain product page with a one-size title is eligible (W04, SL14), a converted one is refused by E2.

## Not done in this spec

No pytest, jest, tsc or eslint run (H5 c): the base pass state (1.11), the RED run, the comm-set base record and the fences are DEFERRED TO RED with their commands. No RED or GREEN file written; no mutation applied; no scratch worktree created; no git write anywhere; no .env read; no production read; Q1 and the production value of `ENABLE_EXACT_PRICE_GATE` are unmeasured; the LLM dispatch seam for P02 is named for the RED agent to measure; the X1-C client half is not specified; the comm set is a heuristic derivation GREEN re-derives at HEAD.
