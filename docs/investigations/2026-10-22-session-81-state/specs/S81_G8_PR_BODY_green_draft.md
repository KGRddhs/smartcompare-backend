# S81-G8 FOLLOWUPS: B1b URL-TELEMETRY + S81-11b RESULT-AGGREGATES + S81-18b STORE-LABEL

Base daf86d32d222a885c42dc537e83c25483527a83b (origin/main after #393). HEAD fe2ba6703d22e48842bf4af2d714d0716aa5f8bf (branch feature/s81-g8-followups, one commit through the hook). The seventh SAFE group under LC-9 (one adversary, GATE_S81_G8 GC-5). TWO new flags, both default OFF and read PER CALL as the first statement of the gated predicate; B1b adds none. Every flag is unset in production; nothing changes until the owner flips.

## B1b URL-TELEMETRY (no new flag; rides ENABLE_RESULT_STATUS_METADATA)
- Change: `result_gate.assess_result` gains the keyword-only `url_mode: bool = False`; under it the price / rating facts (strict AND literal) and the per-side corroboration read S81-20's `_url_price` / `_url_rating`. `sentry_service.capture_result_status` passes `url_mode=True` only for input_type url (a conditional kwarg: the text / text_stream / camera call shapes are unchanged). R-G8-3: `compare_runs.build_run_row` passes the same conditional kwarg (rides ENABLE_COMPARE_RUN_LEDGER; nothing else in that file).
- Effect: a delivered real URL compare tags `supported_result` with `data_coverage` 1 instead of `partial_no_winner` / 0. `price_showable_a/b` stay strict (R-G8-2). The URL envelope is still never stamped: no wire or stored-row change.
- RED rows: tests/test_s81_b1b_url_telemetry.py R1 (keyword), R2 / R3 (bh / ae JSON-LD pair tags), R4 (string ratings), R5 (same identity), R6 (URL route), R7 (compare_runs row); PIN P1-P6 (OFF on any input, non-URL tags byte-equal, the default unchanged, the URL gate unchanged, the URL body unstamped + strict showable, result_gate purity).

## S81-11b RESULT-AGGREGATES (ENABLE_RESULT_AGGREGATES)
- Change: `kb_serve.result_aggregates_enabled`, `AGGREGATE_FIELDS` and the pure, total `kb_serve.result_aggregates(views)`; the builder kwarg `kb_views` (R-G8-4) and the stamp after the S81-20 block; scs passes `kb_views=getattr(self, "_kb_views", None)` at the three builder call sites (partial, REST, stream).
- Effect ON: the additive `metadata.aggregates` = 2 entries `{compare_count: null, store_count, price_checked_at}`; store_count = the distinct retailer hosts over classify's servable candidates (0 for a card with none, R-G8-5), price_checked_at = their newest as_of (ISO Z); every field null without a card. A failure = one WARNING `[RESULT_AGGREGATES] stamp skipped: <Type>` and no key.
- RED rows: tests/test_s81_s11b_result_aggregates.py R1-R7; PIN P1 (the shared golden, full configuration), P2 (KB OFF = the S18 golden), P3 (classify shapes).
- Flip facts: only after ENABLE_KB_FIRST_SERVE is live and the S81-11d client line ships.

## S81-18b STORE-LABEL (ENABLE_STORE_LABEL)
- Change: NEW `data/merchant_labels.json` (version 1, 33 BH fragrance hosts, keys = `deny_hosts.normalize_host`, sorted, ASCII, LF, no URL; AR = EN until the native read, R-G8-8); NEW `app/services/store_labels.py` (`store_label_enabled`, `LABELS_PATH`, `load_labels` with the category_gate stat-keyed cache, `label_for`, `label_prices`, `_reset_label_cache`); the builder kwarg `output_lang` and the pass after the D08 block; scs passes `output_lang` at the three sites and both `_partial_build_ctx` literals gain the conditional `output_lang` entry (R-G8-6).
- Effect ON: every builder price dict (products[i].price, overview.products[i].price) gains `store_label` (the row of the retailer host, else of the url host (R-G8-7); AR for lang ar, else EN; no row -> the retailer string; neither -> null). A NEW price dict per slot; a price object is never mutated (GC-4 D2). A missing / invalid table = the fallback everywhere with ONE WARNING per file state. The SSE prices frame and the URL envelope carry no label.
- RED rows: tests/test_s81_s18b_store_label.py R1-R8; PIN P1 (the shared golden incl. REST lang ar), P2 (the classify price dict), P3 (the SSE prices frame).
- Flip facts: after the owner's [NATIVE READ] (below), with or after S81-11d.

## E-rows (deliberate pin changes)
| id | anchor | change |
|---|---|---|
| (none) | - | no existing test edited; no pin reddened |

## Counts and gates (the logs and the mutation table are separate files: specs/S81_G8_RED_REPORT.md section 6, S81-G8_GREEN_REPORT.md)
- 34 nodes (22 RED / 12 PIN): flags unset 34 passed; ENABLE_RESULT_STATUS_METADATA / ENABLE_RESULT_AGGREGATES / ENABLE_STORE_LABEL exported in the runner call only, 34 passed.
  - [pyt] tag=g8green-units-off elapsed=6s bound=600s status=OK rc=0 | 34 passed
  - [pyt] tag=g8green-units-on elapsed=6s bound=600s status=OK rc=0 | 34 passed
- Mutants (the RED round, byte copies): 24 / 24 KILLED, 0 survivors.
- CI-order set (spec 12.1): [pyt] tag=g8green-ciorder elapsed=88s bound=1200s status=FAIL rc=1 | 1 failed, 1716 passed (only the known CRLF environmental s10 r06; equal to the RED prototype figure).
- Comm set: the RED's 712 (sorted-list sha256 ea0d2f1b...) + the 3 RED files = 715 files in 29 chunks of <= 25 (bound 1200), compared with the STORED base record base_records/daf86d32.../ea0d2f1b....txt (REUSED, LC-6): the HEAD FAILED set is the same 24 environmental ids (GC-4 D7); `comm -13` EMPTY.
- Corpus gate (`scripts/verify_flag_byte_identity.py --flags ENABLE_RESULT_AGGREGATES,ENABLE_STORE_LABEL,ENABLE_RESULT_STATUS_METADATA`, every flag OFF): base 200474dfcecf2bcc625eb66b3c3fbe65a4a66f2d35b51037aaf5a6b13351dc3f = HEAD 200474dfcecf2bcc625eb66b3c3fbe65a4a66f2d35b51037aaf5a6b13351dc3f (EQUAL).
- tests/test_secret_scan_static.py alone: [pyt] tag=g8green-secretscan status=OK rc=0 | 31 passed.
- Client fences (the fourteen + b3a/nativeStrings by path through the junction; jest 29.7.0, node v24.11.1): 14 / 15 suites pass; the one red suite is config/nativeBundle.w37 with exactly the four known drift nodes (d5, k2, k4, k5); b3a green. The FULL jest runs once in the final round (LC-7).
- The four .githooks test files were NOT RUN (no .githooks change).
- ruff (E9,F63,F7,F82 and the default set) + py_compile clean on every edited / new Python file; json.loads on the table; bytes > 127 = 0 in every new file; `git diff --stat` shows hunks only (CRLF kept).

## Stated limits
- L-B1b-1: the telemetry still differs from the URL gate on the category checks (unsupported_category / category_conflict) and on the dims fact.
- L-B1b-2: price_showable_a/b stay strict on URL (a JSON-LD string price tags false although it counts in coverage), R-G8-2.
- L-B1b-3: the rating count field stays as the reading defines it (reviews.count is not read).
- L-B1b-4 / the R-G8-3 note: the S81-22 compare_runs row reads the URL evidence through the same conditional kwarg (one hunk, rides ENABLE_COMPARE_RUN_LEDGER); every other compare_runs line is untouched.
- L-S11b-1: compare_count is null until S81-11c.
- L-S11b-2: the aggregates reflect the KB card only (a live price contributes nothing; a KB price the chokepoint later pends still reports its card's stores).
- L-S11b-3: "live" is classify's servable grade group (as-of-only stores are not counted when a fresh group exists).
- L-S11b-4: nothing renders until the client line; the stream's intermediate frames carry no aggregates (the complete does).
- L-S18b-1: the labels are a repo data table until a kb_merchants display-name column exists (S81-18c); a table edit is a deploy.
- L-S18b-2: the SSE prices frame, the URL envelope and rows stored before the flip carry no label.
- L-S18b-3: a host missing from the table renders the retailer string; the seed covers 33 BH fragrance hosts only.
- L-S18b-4: every AR value equals its EN label until the owner's native read; camera compares (no lang) always get EN.
- L-S18b-5: with ENABLE_EXACT_PRICE_GATE OFF the builder's products[i] is the caller's product dict, so that dict carries the labelled price dict after the build, exactly as it carries the builder's public view today (production runs the gate ON); the price object itself is never mutated.

## Owner steps (names only; a dated ledger line per step)
- None to merge.
- B1b: none (rides B1's window; the B1 flip read can now include input_type url).
- ENABLE_RESULT_AGGREGATES: flip only after ENABLE_KB_FIRST_SERVE is live and the S81-11d client line ships (045 is LIVE since 2026-11-06).
- ENABLE_STORE_LABEL: the [NATIVE READ] of the 33 AR values below (replace a value only where the store itself publishes an Arabic name, without diacritics), then flip with or after S81-11d.

## [NATIVE READ] (data/merchant_labels.json; AR = EN until the owner's read)
- [NATIVE READ] alhajisbahrain.com: ar = "Al Haji's" (= en "Al Haji's")
- [NATIVE READ] alibaksh.com: ar = "Ali Baksh" (= en "Ali Baksh")
- [NATIVE READ] ashrafsbahrain.com: ar = "Ashrafs" (= en "Ashrafs")
- [NATIVE READ] bahrain.naseem.com: ar = "Naseem" (= en "Naseem")
- [NATIVE READ] bahrain.ounass.com: ar = "Ounass" (= en "Ounass")
- [NATIVE READ] bdutyfree.com: ar = "Bahrain Duty Free" (= en "Bahrain Duty Free")
- [NATIVE READ] beautyandblends.com: ar = "Beauty and Blends" (= en "Beauty and Blends")
- [NATIVE READ] bh-en.smellsoreal.com: ar = "Smells So Real" (= en "Smells So Real")
- [NATIVE READ] bh.afnan.com: ar = "Afnan" (= en "Afnan")
- [NATIVE READ] bh.arabianoud.com: ar = "Arabian Oud" (= en "Arabian Oud")
- [NATIVE READ] bh.asgharali.com: ar = "Asghar Ali" (= en "Asghar Ali")
- [NATIVE READ] bh.azhaperfumes.com: ar = "Azha Perfumes" (= en "Azha Perfumes")
- [NATIVE READ] bh.jashanmal.com: ar = "Jashanmal" (= en "Jashanmal")
- [NATIVE READ] bh.mubkhar.com: ar = "Mubkhar" (= en "Mubkhar")
- [NATIVE READ] bh.oudelite.com: ar = "Oud Elite" (= en "Oud Elite")
- [NATIVE READ] bh.taifalemarat.com: ar = "Taif Al Emarat" (= en "Taif Al Emarat")
- [NATIVE READ] bn.boots.com: ar = "Boots" (= en "Boots")
- [NATIVE READ] bolo.bh: ar = "Bolo" (= en "Bolo")
- [NATIVE READ] boutiqaat.com: ar = "Boutiqaat" (= en "Boutiqaat")
- [NATIVE READ] en-bh.ajmal.com: ar = "Ajmal" (= en "Ajmal")
- [NATIVE READ] en-bh.rituals.com: ar = "Rituals" (= en "Rituals")
- [NATIVE READ] fragrancebh.com: ar = "Fragrance BH" (= en "Fragrance BH")
- [NATIVE READ] gcc.luluhypermarket.com: ar = "LuLu Hypermarket" (= en "LuLu Hypermarket")
- [NATIVE READ] goldencollections.net: ar = "Golden Collections" (= en "Golden Collections")
- [NATIVE READ] goldenscent.com: ar = "Golden Scent" (= en "Golden Scent")
- [NATIVE READ] jalilaperfumes.com: ar = "Jalila Perfumes" (= en "Jalila Perfumes")
- [NATIVE READ] klinq.com: ar = "Klinq" (= en "Klinq")
- [NATIVE READ] nasserpharmacy.com: ar = "Nasser Pharmacy" (= en "Nasser Pharmacy")
- [NATIVE READ] noon.com: ar = "noon" (= en "noon")
- [NATIVE READ] perfumistaaloud.com: ar = "Perfumista Al Oud" (= en "Perfumista Al Oud")
- [NATIVE READ] reefperfumes.com: ar = "Reef Perfumes" (= en "Reef Perfumes")
- [NATIVE READ] sephora.me: ar = "Sephora" (= en "Sephora")
- [NATIVE READ] theperfumesclub.com: ar = "The Perfumes Club" (= en "The Perfumes Club")

🤖 Generated with [Claude Code](https://claude.com/claude-code)
