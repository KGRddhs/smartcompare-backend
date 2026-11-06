# S81-G8 FOLLOWUPS - group unit spec (B1b + S81-11b + S81-18b)

Spec writer: Opus 5.5 (claude-opus-5-5), 2026-11-06 19:36-20:40 AST. Worktree `C:/Users/SynAckITPC/Documents/AI/sc-s81-g8`, detached at the base `18cb9e04a36382fc417307500a092486f618d95e` (origin/main after #391); `git status --short` empty before and after every probe (only this gitignored `.qa-s80/` file is new). Branch for RED / GREEN: `feature/s81-g8-followups` (the RED round re-points the worktree to the then-main after PR #392 SF1 and the S81-22 PR; section 12.7 names the seams). Measurement notes, scripts and logs: `<scratchpad>/g8spec/` (scratchpad = `C:/Users/SYNACK~1/AppData/Local/Temp/claude/cde30765822f13ce/4478042e-6f11-47b0-addf-eb1422827e28/scratchpad`). Binding inputs read: `scripts/s81-common.txt` (LC-1..LC-9), `specs/S81_G8_BRIEF.md` (in full, twice), PLAN_STATUS cross-unit notes (the S85 / S81-11 / S81-20 follow-up lines, `PLAN_STATUS_S81_2026-10-24.md:138-141`), `specs/RULINGS_S81_11.md` R-S11-14, `specs/S81_20_BRIEF.md` R-S20-13 / R-S20-15, `specs/S81_20_UNIT_SPEC.md` L5 / L19, the worked group spec `specs/S81_G7_UNIT_SPEC.md`, PLAN_S80 section 0 (re-read before section 2). Personal-data rule: every value in this spec and in the RED files is synthetic (hosts `store-a.example.com` style, identities `Acme Nimbus Noir`); the store names in 18b.2.4 are public business names, no person. No production probe was made. Production flag state: the newest dated ledger line (2026-11-06 19:33, `ledger.md:293`) and the S85 close line (`ledger.md:277`: "every flag OFF") name none of the three flags set; `ENABLE_RESULT_AGGREGATES` and `ENABLE_STORE_LABEL` are new names, unset by construction; 045 (the kb_* tables) is written NOT applied, so `ENABLE_KB_FIRST_SERVE` serves nothing in production today.

## 0. The group

| Unit | What | Flag | Files (non-test) | RED file |
|---|---|---|---|---|
| B1b URL-TELEMETRY | B1's URL telemetry assessment reads the URL evidence: `assess_result` gains `url_mode: bool = False` (the price / rating facts and the per-side corroboration through S81-20's `_url_price` / `_url_rating` when True); `capture_result_status` passes `url_mode=True` only for `input_type == "url"` | none new: rides `ENABLE_RESULT_STATUS_METADATA` (existing, OFF) | `app/services/result_gate.py`, `app/services/sentry_service.py` | `tests/test_s81_b1b_url_telemetry.py` |
| S81-11b RESULT-AGGREGATES | the ADDITIVE `metadata.aggregates` (a 2-list in product order of `{compare_count, store_count, price_checked_at}`) stamped by the builder from the per-slot KB views the G4 H1 hook already holds (`self._kb_views`); `compare_count` null until S81-11c | NEW `ENABLE_RESULT_AGGREGATES` (default OFF, read per call as the first statement of the stamp) | `app/services/kb_serve.py`, `app/services/response_builder.py`, `app/services/structured_comparison_service.py` (three call-site kwargs) | `tests/test_s81_s11b_result_aggregates.py` |
| S81-18b STORE-LABEL | the ADDITIVE `price.store_label` on every price dict the builder emits (`products[i].price`, `overview.products[i].price`), from the NEW repo table `data/merchant_labels.json` keyed by `deny_hosts.normalize_host`, in the request's `output_lang` (ar / else en), the retailer string as the fallback | NEW `ENABLE_STORE_LABEL` (default OFF, read per call as the first statement of the price-dict pass) | NEW `app/services/store_labels.py`, NEW `data/merchant_labels.json`, `app/services/response_builder.py`, `app/services/structured_comparison_service.py` (three call-site kwargs + two ctx literals) | `tests/test_s81_s18b_store_label.py` |

Shared by all three: `CLAUDE.md` (one G8 block + the :341 pointer clause + two rows edited in place, section 12.5). One shared fixture: `tests/fixtures/s81_g8_flag_off_golden.json` (recorded at the RED base by the RED agent, the S18 golden recipe; read by the 11b and 18b OFF rows).

Files two units share, and the GREEN order:
- `app/services/response_builder.py`: S81-11b (one top import line, one signature kwarg `kb_views`, the stamp hunk after the S81-20 block :2327-2334) and S81-18b (one top import line, one signature kwarg `output_lang`, the pass hunk after the D08 block :2336-2346). Disjoint anchors; the two kwargs are adjacent lines after `product_categories` (:1483).
- `app/services/structured_comparison_service.py`: both units add one kwarg each at the SAME three builder call sites (:3881-3923 partial, :4796-4823 REST, :5719-5746 stream); S81-18b also adds the conditional `output_lang` entry to the two `_partial_build_ctx` literals (:4343-4351, :5212-5224).
- GREEN applies, in order: B1b (result_gate, then sentry_service), S81-11b (kb_serve, response_builder import + kwarg + stamp, scs `kb_views=` at the three sites), S81-18b (data table, store_labels leaf, response_builder import + kwarg + pass, scs `output_lang=` at the three sites + the two ctx entries), the golden is NOT re-recorded (it is the base), CLAUDE.md last.
- No migration, no `SmartCompareApp/` file, no `.github/`, no `.githooks/`, no requirements, no railway config, no route file (`url_routes.py`, `text_routes.py`, `image_routes.py` are read, never edited).

Line endings (measured with `file` and `git ls-files --eol`): every edited app file is index LF / working copy CRLF (`result_gate.py` ASCII CRLF, `kb_serve.py` ASCII CRLF, `sentry_service.py` / `response_builder.py` / `structured_comparison_service.py` / `CLAUDE.md` UTF-8 CRLF; `core.autocrlf=true`, no `.gitattributes`). The Edit tool keeps CRLF; a whole-file diff in `git diff --stat` is a defect. New files (`store_labels.py`, `merchant_labels.json`, the three RED files, the golden) are written pure ASCII + LF (the Arabic label values, when the owner supplies them, are `\uXXXX` escapes: the lexicon precedent `data/fragrance_lexicon.json` holds 0 bytes > 127 and 245 `\u` escapes).

---

## Unit B1b URL-TELEMETRY

### 1. Base state (measured at 18cb9e04)

| # | Site | Measured |
|---|---|---|
| 1.1 | `app/services/sentry_service.py:671-697` | `capture_result_status(result, input_type, *, vision_ms=None, compare_ms=None)`: flag FIRST (:679 `if not result_status_metadata_enabled(): return`); non-dict or `success is not True` returns (:681-682); `compare_ms` falls back to `metadata.elapsed_ms` (:683-685); `assessment = assess_result(result, product_categories=stamped_product_categories(result))` (:687) for EVERY input type; `telemetry_tags(result, input_type, assessment=...)` (:688-689); one `sentry_sdk.capture_message("comparison_result_status", level="info", tags=..., [extras=...])` (:690-696); any exception -> one WARNING `[RESULT_STATUS] telemetry skipped: <Type>` (:697). Imports from result_gate at :10-16. |
| 1.2 | the four callers | `text_routes.py:885` / `:1090` (`"text"`), `:1482` (`"text_stream"`), `image_routes.py:782` (`"camera"`), `url_routes.py:392` (`"url"`, `compare_ms` = the route wall). |
| 1.3 | `app/services/result_gate.py:504-550` | `assess_result(result, *, product_categories=None, vision_confidences=None)`; facts by `evidence_facts(body)` = `_facts(strict=True)` and `evidence_facts_literal(body)` = `_facts(strict=False)` (:529); `coverage == 0` -> reason `no_evidence` -> `partial_no_winner` (:531-533, `_STATUS_BY_REASON` :43-50); `identity_confidence(... facts_per_product=[_corroborated(body, 0), _corroborated(body, 1)])` (:534-536). |
| 1.4 | `result_gate.py:387-403` | `_facts`: price by `price_is_showable` (strict: numeric amount > 0 AND a named non-estimated `source_method`, :210-221) or `price_is_present_literal` (:224-233, numeric amount); ratings by `rating_is_real` (:236-239: a NUMERIC top-level `product.rating`, not derived) in both readings; specs strict `real_spec_rows(_specs_of(...))` (:347-353 falls back to the product's own `specs` when no `result["specs"]` block), literal `literal_spec_items(_prose(...))`; dims from `scoring_v2`. |
| 1.5 | `result_gate.py:489-493` | `_corroborated(result, i)` = `price_is_showable(price) or rating_is_real(product) or real_spec_rows_one_side(...) >= 1`. |
| 1.6 | `result_gate.py:706-741` | S81-20's URL readers: `_url_number` (int / float or an ASCII numeric string, `_URL_NUMBER_RE` :683), `_url_price(product)` (:722-729: not pended / estimated, amount > 0 by `_url_number`), `_url_rating(product)` (:732-741: `reviews.rating` in (0, 5], else a real top-level rating). Used by `url_gate_reason` (:744-765) and `result_gate_refusal(url_mode=True)` (:844-860). |
| 1.7 | `result_gate.py:584-621` | `telemetry_tags`: `price_showable_a/b` read `price_is_showable` directly on the raw products (:609-610), not from the assessment; every other status tag reads the passed assessment. |
| 1.8 | the URL envelope | `url_extraction_service.compare_from_urls` returns `{success, products, comparison, winner_index, recommendation, key_differences, category_used, source_urls}` (:1510-1519): NO `metadata` key; `url_routes.py:37-38` "the URL envelope carries no metadata and is never stamped, R0-1 / B4"; pinned by `tests/test_s80_b1.py:1161-1168` (P12) and `:812` (r18). Each product from `normalize_product_data` (:1225-1250): `price = {amount: raw price (a JSON-LD string or a number), currency, retailer, url, in_stock}` with NO `source_method`; `reviews = {rating, count}`; no top-level `rating`. **Answer to the brief's question: the URL envelope carries no `metadata.result_status` at all, so B1b changes nothing on the wire and nothing in a stored row; it changes only the URL message's Sentry tags.** |
| 1.9 | measured probe (`g8spec/probe_b1b.py`, the S81-20 fixture readers `url_real` of `tests/test_s81_s20_result_gate.py:222-266`) | base tags for input "url": bh pair (bheshop `"490.00"` / godukkan `"4099"`, rating `"5"` on one side) -> `result_status partial_no_winner`, `reasons no_evidence`, `data_coverage 0`, `data_coverage_literal 0`, `identity_confidence medium`, `price_showable_a false`; the URL reading: `_url_price` True / True, `_url_rating` False / True, `url_gate_reason` None (delivered). ae pair (lulu `"175.000"` / samawa `"271.0"`): the same base tags; URL reading price True / True, rating False / False. `url_v03` (numeric 10.5 / 12.25, no source_method): base coverage 0, literal 1. So every delivered real URL compare is tagged `partial_no_winner` today (R-S20-13, L19). |
| 1.10 | base pass state (bounded runner) | `[pyt] tag=g8spec-base-pins2 start=2026-11-06 19:47:33 end=2026-11-06 19:47:56 elapsed=23s bound=1200s status=OK rc=0` - `954 passed`; `[hermeticity] sentinel checked 954 test(s)`; `[netguard] blocked 24 attempt(s) from 9 node(s)` (neutralized `supabase.invalid` connects inside S81-20 rows; every node passed). Files: test_cohort_snapshots, test_s80_b1, test_s81_s20_result_gate, test_s81_s18_kb_first_serve, test_s81_g4_gate_rows, test_s81_kb_schema. Every other pin file of the group is green at this sha in the stored same-sha records (section 12.1): its base FAILED ids are the 22 known environmental ones, none in a B1b file. |
| 1.11 | purity pins | `tests/test_s80_b1.py:1133-1159` P10 / P11: result_gate.py pure ASCII; imports only `os, re, typing, __future__, app.services.text_sanitize`; the substrings `sentry_sdk, structured_comparison_service, response_builder, price_service, extraction_service, httpx, asyncio, socket, logging` must not appear ANYWHERE in the source (docstrings and comments included); no `async def`. |
| 1.12 | flag idiom | `result_status_metadata_enabled()` (:83-85) `os.getenv("ENABLE_RESULT_STATUS_METADATA","false").strip().lower() in _TRUTHY` (`("true","1","yes","on")`), read per call. Libraries (pinned venv `.venv-qaren`, Python 3.12.9): `sentry-sdk==2.68.1` (`requirements.txt:155`); nothing new imported. |

### 2. Contract

- Flag: `ENABLE_RESULT_STATUS_METADATA` (existing, default OFF, read per call FIRST in `capture_result_status`); no new name, no knob.
- `assess_result(result, *, product_categories=None, vision_confidences=None, url_mode: bool = False)`: the new keyword is additive with a False default, so every existing caller (`response_builder.py:2306`, `kb_ingest.py:275`, `gate_reason` :700, the S81-22 `compare_runs.build_run_row` at the rebase) is byte-identical. When `url_mode is True`: (a) `facts["price"]` = `_url_price(p0) and _url_price(p1)` and `facts["ratings"]` = `_url_rating(p0) and _url_rating(p1)`, in BOTH the strict and the literal reading (so `data_coverage == data_coverage_literal` on a URL body); `specs` and `dims` unchanged; (b) `_corroborated` for each side = `_url_price(product) or _url_rating(product) or real_spec_rows_one_side(...) >= 1`. Everything else (reasons order, placeholder / same-identity / category checks, `section_status`, the returned keys) is unchanged. `evidence_facts` / `evidence_facts_literal` / `evidence_coverage` keep their signatures and behaviour (the new path goes through a private `_facts(..., url_mode=...)`).
- `capture_result_status`: the ONE call becomes `assess_result(result, product_categories=stamped_product_categories(result), **({"url_mode": True} if input_type == "url" else {}))` (the house conditional-kwarg idiom: a text / camera / stream call is byte-identical, recorders included).
- Tags (no new key, no removed key; the grammar `^[a-z0-9_,]+$` unchanged): for input `url` only, `result_status`, `reasons`, `identity_confidence`, `winner_emitted`, `data_coverage`, `data_coverage_literal` follow the URL reading; `price_showable_a/b` stay the strict builder-chokepoint predicate (default of Q-B1b-1); `image_present_*`, `unknown_product_count`, `partial_stage`, the walls unchanged.
- Expected values (from 1.9): the real bh and ae pairs -> `result_status supported_result`, `reasons none`, `winner_emitted true`, `data_coverage 1`, `data_coverage_literal 1`, `identity_confidence high` (both brands non-empty, both sides corroborated by a URL price), `price_showable_a false`.
- Flag-OFF identity (the main invariant): OFF, `capture_result_status` returns before any read (zero messages on every exit); the builder stamp never passes `url_mode`, so every body, stored row, `search_logs` row and log line is byte-identical. With the flag ON, the text / text_stream / camera tags are byte-equal to base (PIN rows), and the URL envelope stays unstamped.
- Failure table:

| Input | Base | After |
|---|---|---|
| flag OFF, any exit | no message | no message |
| flag ON, URL pair with JSON-LD string prices both sides | `partial_no_winner`, coverage 0 | `supported_result`, coverage 1 |
| flag ON, URL pair, string ratings both sides, no price | `partial_no_winner` | `supported_result`, coverage 1 |
| flag ON, URL pair, no price / rating / spec | `partial_no_winner` | unchanged |
| flag ON, URL same identity | `needs_identification`, reasons `same_identity,no_evidence` | `needs_identification`, reasons `same_identity` (no_evidence drops when a URL price counts) |
| flag ON, text / stream / camera body | tags T | tags T (byte-equal) |
| `assess_result` raises inside the capture | one WARNING, no message | unchanged |

- Seams: `sentry_sdk.capture_message` (a recorder), `result_gate.assess_result` (a delegating recorder; the conditional kwarg keeps every non-URL call shape).

### 3. Change list

Byte copies first (`shutil.copyfile` of both files to the GREEN notes folder; sha256 recorded).
1. `app/services/result_gate.py`: `_facts(result, *, strict, url_mode=False)` (the two price / rating lines pick the URL readers when `url_mode`); `_corroborated(result, i, url_mode=False)`; `assess_result` gains the keyword, computes `facts` / `facts_literal` through `_facts(body, strict=..., url_mode=url_mode)` and passes `url_mode` to `_corroborated`; one module-docstring sentence ("B1b: assess_result(url_mode=True) reads the price / rating facts through the URL readers"). The docstring text must not contain any P11 banned substring (no `response_builder`, `price_service`, `logging`, `asyncio`, ...).
2. `app/services/sentry_service.py`: the one call at :687 with the conditional kwarg; one docstring sentence in `capture_result_status`.
3. New `tests/test_s81_b1b_url_telemetry.py` (section 5).

### 4. Existing pins

4.1 Deliberate changes: none. Measured: `tests/test_s80_b1.py:789-812` (r18) asserts for the URL exit only `result_status in STATUSES`, `price_showable_a == "false"` (kept by the strict tag, Q-B1b-1) and `"metadata" not in r.json()`; P12 (:1161-1168) asserts the URL body unstamped and one message with input_type url; no row pins the URL tag values `partial_no_winner` / coverage 0. The S81-20 URL rows (`tests/test_s81_s20_result_gate.py` `url_*` fixtures, the `result_gate_refusal(url_mode=True)` rows) read `url_gate_reason`, untouched.
4.2 Must stay green: `tests/test_s80_b1.py` (all rows incl. P10 / P11 purity, F1-1a..d "tags equal the stamp" on text / camera / stream: the stamp and the text tags share the url_mode=False path), `tests/test_s81_s20_result_gate.py`, `tests/test_s81_g3_gate_rows.py:398-420` (a delegating `assess_result` recorder: zero calls at the success exit), `tests/test_s81_s10_fragrance_gate.py` / `tests/test_s81_s10_gate_rows.py` / `tests/test_s81_s10b_links_gate.py` (capture recorders that accept `*a, **k`), `tests/test_s81_s18_kb_first_serve.py:1091` (a no-op capture), `tests/test_sentry_channels_u8d_unit.py` and `tests/test_sentry_channels_u8d.py` (the scrubber, untouched).

### 5. RED tests: `tests/test_s81_b1b_url_telemetry.py`

Hermetic: `import app.main` FIRST (the dotenv guard); `ENABLE_RESULT_STATUS_METADATA` set per row; a recorder on `sentry_sdk.capture_message` (the B1 `rec` shape: `(message, level, tags, extras)`); the JSON-LD readers COPIED from `tests/test_s81_s20_result_gate.py:222-266` (`_url_env`, `_up`, `_jsonld_offer`, the four real fixtures `tests/fixtures/bh_gcc/curl_bh_bheshop.html`, `curl_bh_godukkan.html`, `tests/fixtures/jsonld_first/ae_lulu_lowercase_jsonld_pricecurrency.html`, `ae_samawa_ae_og_no_currency_jsonld_aed.html`); synthetic identities `StoreA Item A` / `StoreB Item B`; the route row reuses `tests.test_paid_route_metering._stub_url_leaves` / `_post_compare` (the B1 r18 harness); netguard on; pure ASCII, LF. Every RED row calls the EXISTING `capture_result_status` (present at base), so it fails at base on an AssertionError only; R1 reads the signature with `inspect` (never an import or a TypeError).

| # | test | assertion | at base | satisfied by |
|---|---|---|---|---|
| R1 | `test_r1_assess_result_url_mode_keyword` | `"url_mode" in inspect.signature(assess_result).parameters` and its default is False | AssertionError | 3.1 |
| R2 | `test_r2_bh_jsonld_pair_tags` | flag ON, the bh fixture envelope through `capture_result_status(body, "url", compare_ms=1234)`: one message; tags `result_status == "supported_result"`, `reasons == "none"`, `winner_emitted == "true"`, `data_coverage == "1"`, `data_coverage_literal == "1"`, `identity_confidence == "high"`, `price_showable_a == "false"`, `input_type == "url"`, `compare_ms == "0"` | AssertionError (`partial_no_winner`) | 3.1 + 3.2 |
| R3 | `test_r3_ae_jsonld_pair_tags` | the same for the ae fixture pair | AssertionError | 3.1 + 3.2 |
| R4 | `test_r4_string_ratings_only` | a URL envelope with no prices and `reviews.rating` `"4.5"` / `"4"` -> `data_coverage == "1"`, `result_status == "supported_result"` | AssertionError | 3.1 (rating reader) |
| R5 | `test_r5_same_identity_keeps_needs_identification` | `url_same()`-shaped envelope (same brand / name, prices 10.0 / 12.0) -> `result_status == "needs_identification"`, `reasons == "same_identity"` (no_evidence gone) | AssertionError (`same_identity,no_evidence`) | 3.1 |
| R6 | `test_r6_url_route_tags_follow_the_url_reading` | flag ON, POST `/api/v1/url/compare` through the r18 harness (stub prices 1.0 numeric, no source_method): one message; `int(tags["data_coverage"]) >= 1` and the tags equal `telemetry_tags(body, "url", assessment=<the URL reading recomputed from the delivered body>, compare_ms=...)` minus `compare_ms` | AssertionError (coverage "0") | 3.2 |
| P1 | `test_p1_flag_off_no_message_any_input` | flag OFF in each spelling `None / "false" / " 0 " / "OFF"`, the bh / ae / text / camera bodies for inputs url / text / text_stream / camera -> zero messages, and a raising `assess_result` recorder is never called | green | base |
| P2 | `test_p2_text_camera_stream_tags_byte_equal` | flag ON: a text-shaped body where the readings DIFFER (the lane1 `tomford_vs_creed` body with each `price.source_method` removed and `rating_derived` True, so strict coverage drops while a URL reading would count) captured as `text`, `text_stream` and `camera` -> the tags dict equals `telemetry_tags(body, input, assessment=assess_result(body, product_categories=stamped_product_categories(body)))` exactly (byte-equal JSON with sort_keys) | green | base |
| P3 | `test_p3_assess_result_default_unchanged` | over the lane1 nine bodies, the S81-20 synthetic bodies (`v09`, `v07`, `v10`, `v10_one`, `cat`) and the four real URL envelopes: `assess_result(b, product_categories=...)` (no keyword) equals the base values stated inline (status, reasons, data_coverage, data_coverage_literal, identity_confidence) | green | base |
| P4 | `test_p4_url_gate_reading_unchanged` | `url_gate_reason` and `result_gate_refusal(body, url_mode=True)` with `ENABLE_RESULT_GATE` ON on the four real envelopes + `url_noev` / `url_same` / `url_v09`: None, None, ..., `no_evidence`, `same_identity`, `placeholder_identity` | green | base |
| P5 | `test_p5_url_body_never_stamped_and_strict_showable_tag` | flag ON, the route row: `"metadata" not in body`; `price_showable_a == "false"` and `price_showable_b == "false"` | green | base |
| P6 | `test_p6_result_gate_purity_restated` | result_gate.py ASCII; its import set within the P11 allowlist; no P11 banned substring | green | base |

Counts: RED 6, PIN 6.

### 6. Mutation table (byte copies, `.qa-mutation.lock`, `pyt.py -k`, bound 600 each)

| M | Mutation | Killed by |
|---|---|---|
| M1 | `capture_result_status` never passes `url_mode` | R2, R3, R4, R6 |
| M2 | `url_mode=True` for every input type | P2 |
| M3 | url_mode swaps the price reader only (ratings strict) | R4 |
| M4 | url_mode swaps the rating reader only (price strict) | R2, R3 |
| M5 | `_corroborated` not url-aware | R2 (`identity_confidence` medium) |
| M6 | url_mode applied to the strict reading only | R2 (`data_coverage_literal` 0) |
| M7 | the default flipped (`url_mode: bool = True`) | P3 |

### 7. Comm set
The group's (section 12.1); B1b's own reach is the result_gate / sentry_service importers (the whole route surface through app.main), already inside it.

### 8. CLAUDE.md row and owner steps
Row (inside the G8 block): `- B1b URL-TELEMETRY (no new flag; rides ENABLE_RESULT_STATUS_METADATA): result_gate.assess_result gains url_mode (default False, so every existing caller is byte-identical); sentry_service.capture_result_status passes url_mode=True only for input_type url, so B1's URL message reads the JSON-LD string price / rating evidence through S81-20's _url_price / _url_rating (a delivered real URL compare tags supported_result with data_coverage 1 instead of partial_no_winner); price_showable_a/b stay the strict chokepoint predicate; the URL envelope is still never stamped; text / text_stream / camera tags byte-identical. RED tests/test_s81_b1b_url_telemetry.py.`
In place: the B1 row (CLAUDE.md:475) clause "its telemetry reads a body without prices or `scoring_v2` (status mostly `partial_no_winner`)" becomes "its telemetry reads the URL evidence (S81-G8 B1b)"; the S81-20 block's `L19 B1's URL telemetry over-reports (B1b)` (CLAUDE.md:586) becomes `L19 B1's URL telemetry reads the URL evidence since S81-G8 B1b`; the S81-20 Canary sentence keeps the `[RESULT_GATE]` lines and the `result_gate:` rows and adds "and B1's URL message" (R-S20-15 wording updated in place).
Owner steps: none (rides B1's window; the B1 flip read can now include `input_type url`).

### 9. Stated limits
- L-B1b-1: the telemetry still differs from the URL gate in two ways: the assessment keeps the category checks (`unsupported_category` / `category_conflict`) the URL gate never applies (R-S20-1), and the dims fact (none on a URL body).
- L-B1b-2: `price_showable_a/b` stay strict on URL (a JSON-LD string price tags false although it counts in coverage) unless Q-B1b-1 rules otherwise.
- L-B1b-3: a rating count field stays as the reading defines it (`reviews.count` is not read).
- L-B1b-4: the S81-22 `compare_runs` row (a rebase-time file) computes its `result_status` through `assess_result` without `url_mode` unless Q-B1b-2 adds the same conditional kwarg there.

### 10. Out of scope
Stamping the URL envelope (R0-1 / B4 forbid it); any change to `url_gate_reason` or the B2 refusals; a new tag key.

### 11. Open questions
- Q-B1b-1: should `price_showable_a/b` follow the URL reading for input url? Default: NO (they mirror the builder chokepoint; flipping them is a deliberate change of `tests/test_s80_b1.py:810`).
- Q-B1b-2: if the S81-22 branch is on the then-main at the RED re-point, add `**({"url_mode": True} if input_type == "url" else {})` to its `_rg.assess_result` call in `app/services/compare_runs.py` (one hunk, rides `ENABLE_COMPARE_RUN_LEDGER`, a RED row in this file)? Default: YES when present, else a stated limit.

---

## Unit S81-11b RESULT-AGGREGATES

### 1. Base state (measured at 18cb9e04)

| # | Site | Measured |
|---|---|---|
| 1.1 | `structured_comparison_service.py:4523-4528` (REST, H0) / `:5240-5245` (stream) | under `kb_serve.kb_first_serve_enabled()` (read once per compare) ONE task `self._kb_cards_task = asyncio.ensure_future(kb_serve.fetch_cards(products, output_lang))`, `self._kb_hit_marks = ["miss","miss"]`, `self._kb_views = [None, None]`. Absent with the flag OFF (`getattr(self, "_kb_views", None)` is None). The service is per request (`get_comparison_service` :10132-10134 returns a new instance). |
| 1.2 | `scs.py:6097-6113` (H1, inside `_fetch_product_data`) | for `partial_slot in (0, 1)`: `_kb = kb_serve.classify(card, category, region, now=kb_serve._now(), accepts_asof=...)` then `self._kb_views[partial_slot] = _kb` (:6113). The view is the classify output: `{hit, pid, version, price, price_state, candidates, specs, specs_complete, image_url, reviews, rating, review_count}` (`kb_serve._miss` :202-205). The views are already read by `log_verdict_key(views=getattr(self, "_kb_views", None))` (:4662, :5539). |
| 1.3 | `kb_serve.py:237-334` (classify) | the eligible offers: region bahrain, `market == "BH"`, `observed_currency == "BHD"`, a positive finite amount, `in_stock is not False`, a readable `last_seen` not beyond `FUTURE_SKEW_SECONDS` (D16b), `kb_source_allowed(canonical_url)`; graded fresh (age <= `GENUINE_PRICE_DB_TTL` 7 d) / asof (capable client, <= the knob) / stale; the first non-empty grade group in (fresh, asof), sorted newest `last_seen` first, becomes `candidates` (each a `_price_dict`, :208-226: `retailer = offer.merchant_id` = the kb_merchants host, `as_of = _iso_z(last_seen)` "%Y-%m-%dT%H:%M:%SZ") and `price = candidates[0]`. A card dict -> `hit` full / partial; no card -> `_miss()` (`hit "miss"`, `candidates []`). |
| 1.4 | card offers shape (the real producer, `tests/test_s81_s18_kb_first_serve.py:241-276`) | `{variant_id, merchant_id (host), market, observed_currency, amount, canonical_url, last_seen, captured_at, first_seen, in_stock, list_vs_sale, evidence_rung, size_ml}`. |
| 1.5 | `response_builder.py:1457-1484` | `build_comparison_response(*, ..., product_categories=None)`: keyword-only, every kwarg defaulted; NO `kb_views`, NO language parameter. `result["metadata"]` built at :2082; the B1 stamp :2296-2326 is the precedent (flag FIRST, additive keys, `try` -> one WARNING, the body as with the flag OFF); the S81-20 block :2327-2334; D08 :2336-2346; `_strip_inference_markers(result)` :2354; `return result` :2356. |
| 1.6 | the three builder call sites | `_build_partial_response` :3881-3923 (ctx-based, `product_categories=ctx.get("product_categories")` :3922), `_compare_from_text_impl` :4796-4823 (`product_categories=product_categories` :4822), `compare_from_text_streaming` :5719-5746 (:5744, then `_single_margin` :5745). Each is followed by `attach_data_freshness_notice` and `self._stamp_unit_metadata(...)` (:3925-3926, :4825-4826, :5748-5749; the H7 `metadata.kb_hit` stamp lives there, :3991-3995). The only callers in app/ (grep). |
| 1.7 | flag idiom | `kb_serve.kb_first_serve_enabled` (:67-69) `os.getenv(NAME, "false").strip().lower() in _TRUTHY`, read per call; the builder reads its leaves by module attribute (`from app.services import jsonld_widen as _jsonld_widen` :25, `llm_pricing` :23). kb_serve's module top imports the standard library only (:37-47), so a top import in the builder adds no cycle. |
| 1.8 | KB pins | `tests/test_s81_kb_schema.py:369-418` P01 (no `kb_service` importer / no string constant containing `kb_service` together with `app.` or `/`, docstrings included) and P02 (no `kb_*` relation name as an exact string constant outside the allowlist): the helper adds neither. `tests/test_s81_s18_kb_first_serve.py:697-711` R9 pins the exact key set of `_price_dict` and of every candidate (untouched: the helper only reads them). |
| 1.9 | metadata-key snapshots (measured grep) | `tests/test_s80_b1.py:1071` (`BASE_MD_KEYS`, flag OFF bodies), `tests/test_partial_response_no_fabricated_scores.py:725` (on / off of another flag), `tests/test_s75_fanout_identity.py` FY5 / FY25 digests (flags cleared, payload-based), `tests/fixtures/s81_s18_flag_off_golden.json` (S18 P1, `ENABLE_KB_FIRST_SERVE` OFF), `tests/fixtures/s81_s10_flag_off_golden.json`, `s81_s10b_flag_off_golden.json`, `s81_d22c_flag_off_golden.json`: every one runs with the new flag unset, so an additive flag-ON key moves none. `tests/test_s71_u13_compare_auth_required.py` T23 is the OpenAPI snapshot: the compare routes return dicts, no response model gains a field. |
| 1.10 | base pass state | the 1.10 run of B1b covers test_s81_s18_kb_first_serve (all green) and test_s81_g4_gate_rows; FY / W4-13 / U13 / S10 files green in the same-sha records (12.1). |

### 2. Contract

- Flag `ENABLE_RESULT_AGGREGATES`: `kb_serve.result_aggregates_enabled()` (the house idiom, read per call), the FIRST statement of the stamp; no knob.
- Seam (the cheapest card-to-builder seam, Q-S11b-1): the builder gains `kb_views: Optional[List[Any]] = None`; the three call sites pass `kb_views=getattr(self, "_kb_views", None)` (the data the H1 hook already holds; None with the KB flag OFF). No DB read, no new query, no card re-read, no change to H0-H8.
- New pure helper `kb_serve.result_aggregates(views) -> List[Dict[str, Any]]` (flag-free, total, never raises): exactly two entries in product order, each `{"compare_count": None, "store_count": <None | int>, "price_checked_at": <None | str>}` in that key order:
  - a slot whose view is not a dict, or whose `hit` is not `"full"` / `"partial"` (no card: KB OFF, a miss, a classify failure) -> all three None;
  - else `store_count` = the number of DISTINCT non-empty `retailer` strings (`.strip().lower()`) over the view's `candidates` dicts (the live, servable offers: the same filter and grade classify applied), an int >= 0; `price_checked_at` = the NEWEST parseable `as_of` over those candidates as `"%Y-%m-%dT%H:%M:%SZ"` (via `_ts` / `_iso_z`), None when there is none;
  - `compare_count` is None in this unit (no per-product counter without a migration: S81-11c).
- The stamp (after the S81-20 block): `if _kb_serve.result_aggregates_enabled(): try: result["metadata"]["aggregates"] = _kb_serve.result_aggregates(kb_views) except Exception as exc: logger.warning("[RESULT_AGGREGATES] stamp skipped: %s", type(exc).__name__)`. Additive; the crown never moves; a failure leaves the body exactly as with the flag OFF.
- The later client contract (S81-11d, names only): a count renders only when `compare_count >= 20`, a store count only when `store_count >= 2`, `price_checked_at` as a date.
- Flag-OFF identity (the main invariant): no `aggregates` key on any REST / stream / partial / camera body, stored row (`comparisons.full_response`) or log line, with the FULL configuration (ENABLE_KB_FIRST_SERVE ON with a card present, B1 ON, ENABLE_RESULT_GATE ON, both W4-13 states); the new kwarg is unused OFF.
- Failure table:

| Input | After (flag ON) |
|---|---|
| KB OFF (views None) | `[{nulls}, {nulls}]` |
| card on slot 0 only | slot 0 counted, slot 1 nulls |
| card present, no eligible offer (price_state none / stale_refused) | `store_count 0`, `price_checked_at null` |
| 3 candidates on 2 hosts, last_seen d-1 / d-2 / d-4 | `store_count 2`, `price_checked_at` = d-1 |
| a candidate with an unreadable `as_of` | skipped for the time, still counted as a host |
| `result_aggregates` raises (cannot: total) / metadata not a dict | one WARNING, no key |
| flag OFF | no key, no read of `kb_views` |

- Seams: `kb_serve.result_aggregates_enabled`, `kb_serve.result_aggregates` (module attributes), the S18 harness seams (`_admin_client`, `_now`, `run_db`).

### 3. Change list

Byte copies first.
1. `app/services/kb_serve.py`: `result_aggregates_enabled()` beside the two readers (:67-75); `AGGREGATE_FIELDS = ("compare_count", "store_count", "price_checked_at")` and `result_aggregates(views)` after `served` (:337-341); one module-docstring bullet naming the flag and the helper.
2. `app/services/response_builder.py`: `from app.services import kb_serve as _kb_serve` beside the leaf imports (:22-25, with a one-line comment); the `kb_views` kwarg after `product_categories` (:1483) and one docstring sentence; the stamp hunk after :2334.
3. `app/services/structured_comparison_service.py`: `kb_views=getattr(self, "_kb_views", None),` at :3922 (partial), :4822 (REST), :5745 (stream), each after the `product_categories` / `_single_margin` line with a `# S81-11b` comment.
4. New `tests/test_s81_s11b_result_aggregates.py` and the shared golden `tests/fixtures/s81_g8_flag_off_golden.json` (recorded at the RED base; `python -m tests.test_s81_s11b_result_aggregates <out.json>` re-records only at a base sha).

### 4. Existing pins

4.1 Deliberate changes: none (every metadata-key snapshot of 1.9 runs with the flag unset; the builder signature pins `tests/test_s80_b1.py:140` and `tests/test_s81_s20_result_gate.py:1525` introspect names and pass only the ones they know).
4.2 Must stay green: `tests/test_s81_s18_kb_first_serve.py` (R9 key sets, P1 golden, P2 no `kb_hit` OFF), `tests/test_s81_g4_gate_rows.py`, `tests/test_s75_fanout_identity.py` (FY5 / FY25), `tests/test_w4_13_flag_off_ledger.py`, `tests/test_s71_u13_compare_auth_required.py` (T17 / T23), `tests/test_m18_factcheck_honest.py:247-259` (`= build_comparison_response(` count >= 3), `tests/test_cohort_summary_orchestrator.py:150-163` (the cohort kwarg strings at the three sites: the new line is added beside, not into, those lines), `tests/test_s81_s03_llm_ledger_v2.py:441-447` and `tests/test_s81_s20_result_gate.py:915-925` (delegating builder recorders `*a, **k`), `tests/test_s81_kb_schema.py` P01 / P02 / P06, `tests/test_s80_b1.py` (P1 / P2 builder and orchestrator digests OFF).

### 5. RED tests: `tests/test_s81_s11b_result_aggregates.py`

Hermetic: `import app.main` first; the S18 harness imported from `tests.test_s81_s18_kb_first_serve` (`_full_config`, `_install_kb`, `_CardClient`, `_card`, `_card_b`, `_offer`, `_pid`, `_compare`, `_complete`, `_classify`, `NOW`, `HOST_A`, `HOST_B`, `P0`, `P1`, `PDP_A`, `CLEARED_ENV`, `OFF_SPELLINGS`); a third synthetic host `store-c.example.com`; `ENABLE_RESULT_STATUS_METADATA` and `ENABLE_RESULT_GATE` ON in the OFF rows (full configuration); W4-13 both states via `ENABLE_SEARCH_LOG_TRUTH` unset / "true" where a route row runs; missing symbols read with `getattr` / `inspect` and asserted.

| # | test | assertion | at base | satisfied by |
|---|---|---|---|---|
| R1 | `test_r1_flag_reader_house_boolean` | `getattr(kb_serve, "result_aggregates_enabled")` callable; False for None / "" / "false" / "0" / "garbage" / " OFF "; True for " TRUE " / "1" / "yes" / "On" | AssertionError (absent) | 3.1 |
| R2 | `test_r2_helper_hosts_and_newest` | `result_aggregates([_classify(card3), None])` where card3 has offers on HOST_A (d-2), HOST_A (d-4, another variant), HOST_B (d-1) -> `[{"compare_count": None, "store_count": 2, "price_checked_at": _z(NOW - 1 d)}, {all None}]`; key order exact | AssertionError (absent) | 3.1 |
| R3 | `test_r3_helper_nulls_and_zero` | views None / [] / a `_miss()` view -> two all-null entries; a card with only out-of-stock offers (hit partial, no candidates) -> `store_count 0`, `price_checked_at None` | AssertionError | 3.1 |
| R4 | `test_r4_builder_stamps_under_the_flag` | `"kb_views" in inspect.signature(build_comparison_response).parameters` asserted; then a minimal builder call (the S20 `_builder_body` shape) with `kb_views=[view3, None]`, flag ON -> `metadata["aggregates"]` equals R2's list; OFF spellings -> no key | AssertionError (no kwarg) | 3.2 |
| R5 | `test_r5_orchestrator_rest_and_stream` | full config, KB ON, `_CardClient({pid0: card3, pid1: _card_b()})`, flag ON: the REST payload and the stream `complete` carry `metadata.aggregates` = `[{None, 2, d-1}, {None, 1, d-2}]` | AssertionError (no key) | 3.3 |
| R6 | `test_r6_partial_builder_carries_it` | a real service instance with `_partial_build_ctx` (the REST ctx keys), `_kb_views = [view3, None]`, flag ON: `svc._build_partial_response(elapsed_seconds=1.0)["metadata"]["aggregates"][0]["store_count"] == 2` | AssertionError | 3.3 |
| R7 | `test_r7_flag_read_first` | flag OFF: a `kb_views` object whose every access raises (a list subclass) is never touched by the builder (no exception, no WARNING); flag ON with that object -> one WARNING `[RESULT_AGGREGATES] stamp skipped: <Type>` and NO key (degrades to OFF) | AssertionError (TypeError on the unknown kwarg is avoided by the R4 signature assert first) | 3.1 + 3.2 |
| P1 | `test_p1_flag_off_golden_full_config` | OFF spellings x W4-13 {unset, "true"}: KB ON with both cards, B1 ON, the result gate ON; the REST / stream / camera payloads (S18 `_normalize`) equal `tests/fixtures/s81_g8_flag_off_golden.json` (recorded at the base with the same configuration; shared with 18b P1); no `aggregates` key | green (recorded at base) | base |
| P2 | `test_p2_kb_off_bodies_unchanged` | KB OFF, flag OFF: the S18 golden `tests/fixtures/s81_s18_flag_off_golden.json` scenarios unchanged (re-run of S18 P1's recipe) | green | base |
| P3 | `test_p3_classify_shapes_untouched` | `_classify(card3)` price / candidates key sets equal S18 R9's set (the helper reads, never writes) | green | base |

Counts: RED 7, PIN 3.

### 6. Mutation table

| M | Mutation | Killed by |
|---|---|---|
| M1 | the stamp drops the flag read (always stamps) | P1, R4 (OFF half) |
| M2 | `store_count` = len(candidates) (offers, not hosts) | R2 (3 vs 2) |
| M3 | `price_checked_at` = the OLDEST as_of | R2 |
| M4 | `price_checked_at` = `candidates[-1]` | R2 |
| M5 | a miss view counted as 0 instead of null | R3 |
| M6 | one call site does not pass `kb_views` (stream) | R5 |
| M7 | the partial site does not pass it | R6 |
| M8 | the flag read after `result_aggregates(kb_views)` | R7 |

### 7. Comm set: the group's (section 12.1).

### 8. CLAUDE.md row
`- ENABLE_RESULT_AGGREGATES (S81-11b, default OFF, read PER CALL by kb_serve.result_aggregates_enabled as the first statement of the builder stamp): the additive metadata.aggregates, a 2-list in product order of {compare_count, store_count, price_checked_at}, computed by the pure kb_serve.result_aggregates from the per-slot KB views the S81-18 H1 hook already holds (passed to build_comparison_response as kb_views at the three call sites; no DB read, no new query): store_count = the distinct merchant hosts among the card's live servable offers (classify's candidates), price_checked_at = their newest as_of (ISO-8601 Z), compare_count null until S81-11c; every field null without a card (ENABLE_KB_FIRST_SERVE OFF or a miss). OFF: no key on any body or stored row. Nothing renders until the client line S81-11d (count only when compare_count >= 20, stores only when >= 2). RED tests/test_s81_s11b_result_aggregates.py.`
Owner steps: flip only after 045 is applied, `ENABLE_KB_FIRST_SERVE` is live and the S81-11d client line ships; nothing to do at merge.

### 9. Stated limits
- L-S11b-1: compare_count is null until S81-11c (the S81-22 run ledger feeds a later counter).
- L-S11b-2: the aggregates reflect the KB card only: a live-fetched price contributes nothing; a slot whose KB price the chokepoint later pends still reports its card's stores.
- L-S11b-3: "live" is classify's servable grade group: when a fresh group exists, the as-of-only stores are not counted.
- L-S11b-4: nothing renders until the client line; the stream's intermediate frames carry no aggregates (the `complete` does).

### 10. Out of scope
A per-product compare counter (S81-11c, a migration or the S81-22 ledger); any kb_* read on the request path; the client rendering (S81-11d).

### 11. Open questions
- Q-S11b-1: the seam: the builder kwarg `kb_views` (the brief's builder stamp, the B1 precedent) vs writing the key in `_stamp_unit_metadata` beside H7 `kb_hit` (one hunk, no builder edit). Default: the builder kwarg (the brief's rule; the stamp stays in one place with S81-18b's pass).
- Q-S11b-2: a card present with zero servable offers: `store_count 0` (proposed, honest) or null? Default: 0.

---

## Unit S81-18b STORE-LABEL

### 1. Base state (measured at 18cb9e04)

| # | Site | Measured |
|---|---|---|
| 1.1 | migration 045 `kb_merchants` | no display-name column (the brief's measured column list); a column would make the unit FOCUS (S81-18c). |
| 1.2 | the price-dict emitters | KB: `kb_serve._price_dict` (:208-226, `retailer = merchant_id` = the host). Live: `price_service` (`"retailer": domain` :13891, :14092, :14364, :14743, :14858, :15697; literal hosts `"bolo.bh"` :16002, `"boutiqaat.com"` :16110, `"nasserpharmacy.com"` :16325; a NAME `"iHerb"` :16875; `retailer_name` :16987; `retailer` :10577; candidate copies :2211, :3109), `algolia_service.py:821/:928`, `magento_graphql_service.py:1184`, `noon_service.py:446` (`"noon.com"`), `occ_service.py:229`, `product_data_service.py:293/:344`. Every one reaches the response only through the orchestrator's `product_data[i]["price"]` and the builder. |
| 1.3 | the builder's price-dict surfaces (the ONE chokepoint) | `response_builder.py:1938` `overview.products[i].price = public_price_view(pd.get("price"))` and `:2250-2251` `products[i].price = public_price_view(pd["price"])` (the products alias). `public_price_view` (`price_service.py:9371-9387`) returns a NEW dict under `ENABLE_EXACT_PRICE_GATE` (default ON, in prod) and the SAME object with it OFF; a non-dict passes through. No other price dict is in the body (measured grep of the builder: the scoring / tradeoff readers read amounts only). |
| 1.4 | emitters that bypass the builder | the SSE `prices` frame (`scs.py:5414-5444`, `public_price_view` over a pending projection, before `complete`); the URL envelope (`url_extraction_service.normalize_product_data` :1236-1242, `retailer = retailer.get("name")`); stored bodies replayed by history / share (labelled only if stored under the flag). |
| 1.5 | the language | `build_comparison_response` has NO language parameter (grep: no `lang` in response_builder.py). The routes normalise `lang` with `extraction_service.normalize_output_lang` (:2324-2332 -> "ar" / "en" / None; `text_routes.py:753`, `:986`, `:1261`, forwarded only when set); the orchestrator receives `output_lang` (`_compare_from_text_impl` :4276, `compare_from_text_streaming` :4942) and already passes it to `kb_serve.fetch_cards` (:4526, :5243) and the verdict (`lang=output_lang` :4661, :5538). The camera route passes none (image_routes.py: no lang). `_partial_build_ctx` (:4343-4351 REST, :5212-5224 stream) carries no language. **Answer: the lang source is the orchestrator's `output_lang`, passed to the builder as a new kwarg; the partial builder reads it from ctx.** |
| 1.6 | `deny_hosts.normalize_host` (:119-134) | a str -> stripped, lower-cased, `:port` dropped, trailing dots dropped, ONE leading `www.` dropped; a non-str -> `""`; never raises. deny_hosts imports `os, re, typing, urllib.parse` only (:46-51). Not a registrable-domain reducer (`bh.asgharali.com` stays as is). |
| 1.7 | the house data-table loader (`category_gate.py:99-100`, `:127-134`, `:215-284`) | `_REPO_ROOT = Path(__file__).resolve().parents[2]`; a path reader; a stat-keyed cache `(path, mtime_ns, size)` under a `threading.Lock`; parse only on a changed key; a missing / invalid / wrongly shaped file -> the EMPTY value with ONE WARNING per file state (`[CATEGORY-GATE] lexicon unavailable type=<Type>`, the set capped at 64); a test seam `_reset_lexicon_cache()`. |
| 1.8 | readers of data/ (measured) | no backend test walks `data/` (no glob / iterdir / listdir over it); no client fence reads a data file other than `data/cohort_priors.json` / `data/trending_curated.json` (comments / specific paths); so a new `data/merchant_labels.json` joins no existing reader. |
| 1.9 | key-set pins on price dicts | `tests/test_s81_s18_kb_first_serve.py:697-711` R9 (`_price_dict`'s exact keys, every candidate): the label is added at the builder pass, never in `_price_dict`. `tests/test_l2_promotion_remaining_ttl.py:187`, `tests/test_adapter_prefetch_hook.py:513`, `tests/test_correctness_coverage_review_findings.py:1013` pin price_service outputs (untouched). Body snapshots: the 1.9 list of S81-11b (all flag-unset). |
| 1.10 | base pass state | as B1b 1.10 (S18 file green); the price_service / builder pins green in the same-sha records (12.1). |

### 2. Contract

- Flag `ENABLE_STORE_LABEL`: `store_labels.store_label_enabled()` (house idiom, per call), the FIRST statement of the pass; no env knob (the table path is a module attribute seam `LABELS_PATH`).
- New leaf `app/services/store_labels.py` (stdlib `json`, `logging`, `os`, `threading`, `pathlib`, `urllib.parse` + `deny_hosts.normalize_host`; ASCII, LF): `LABELS_PATH = <repo>/data/merchant_labels.json`; `load_labels() -> Dict[str, Dict[str, str]]` (the category_gate stat-keyed cache; invalid -> `{}` with ONE WARNING `[STORE_LABEL] table unavailable type=<Type>` per file state); `label_for(price, lang) -> Optional[str]`; `label_prices(result, lang) -> None`; `_reset_label_cache()` (test seam).
- The table `data/merchant_labels.json`: `{"version": 1, "labels": {"<host>": {"en": "<label>", "ar": "<label>"}, ...}}`; every key equals `normalize_host(key)`, matches `kb_service.KB_HOST_REGEX` (`kb_service.py:117`), is ASCII; every value a non-empty str with no `/`, no `:`, no `http`; the AR values carry no harakat (U+064E-U+0650, U+0652), no shadda (U+0651), no tanween (U+064B-U+064D) and no superscript alef (U+0670); the file is ASCII bytes (`\uXXXX` escapes); sorted keys. Validation failure of any row -> the whole table unavailable (fail safe: the host fallback).
- `label_for(price, lang)`: `host = normalize_host(price.get("retailer"))`; no row and `price["url"]` an http(s) str -> `normalize_host(urlsplit(url).hostname or "")` (a ValueError -> no row); a row -> `row["ar"]` when `lang == "ar"` else `row["en"]`; no row -> the `retailer` string as-is when it is a non-empty str (what the client renders today), else None.
- The pass (`response_builder`, after the D08 block, before `_strip_inference_markers`): `if _store_labels.store_label_enabled(): try: _store_labels.label_prices(result, output_lang) except Exception as exc: logger.warning("[STORE_LABEL] pass skipped: %s", type(exc).__name__)`. `label_prices` computes every label FIRST, then writes `products[i]["price"] = {**price, "store_label": label}` and the same for `overview.products[i]["price"]` (a NEW dict per slot: never mutates the price object, which under the exact gate OFF is the product_data / cache object); a non-dict price is skipped. Additive key on every price dict of the body; `retailer` unchanged.
- Builder kwarg `output_lang: Optional[str] = None`; the call sites pass `output_lang=output_lang` (REST, stream) and `output_lang=ctx.get("output_lang")` (partial); the two ctx literals gain `**({"output_lang": output_lang} if output_lang else {})` (no lang -> the ctx is byte-identical to base).
- Flag-OFF identity (the main invariant): no `store_label` key on any body, stored row, SSE frame or log line (full configuration: KB ON with cards, B1 ON, the result gate ON, both W4-13 states); OFF never stats or reads the table.
- Failure table:

| Input (flag ON) | `store_label` |
|---|---|
| KB price, retailer `store-a.example.com` with a row, lang None / "en" | the row's en |
| the same, lang "ar" | the row's ar |
| live price, retailer `bolo.bh`, row present | en / ar |
| retailer `www.Store-A.example.com:443` | the row of `store-a.example.com` |
| retailer a name (`iHerb`), url `https://iherb.com/...`, row for `iherb.com` | that row's label |
| no row (unknown host) | the retailer string |
| pending price (retailer None, url None) | None |
| table missing / invalid | the retailer string everywhere + one WARNING per file state |
| `label_prices` raises | no key anywhere, one WARNING |

- Seams: `store_labels.LABELS_PATH`, `store_labels._reset_label_cache`, `store_labels.store_label_enabled`.

### 2.4 The seed (proposed; the hosts the price pipeline serves for fragrance in Bahrain today)

Source (measured): the code registry `source_router.SOURCE_REGISTRY` (44 rows) BH-tier hosts serving fragrances or general BH retail, plus the catalog `data/bh_gcc_sources.json` rows with `tier "bahrain"`, `status "live"`, `fragrances` in categories (21 of 368), plus the literal price-service emitters. 33 hosts. EN labels PROPOSED from each store's public name as its host spells it (the orchestrator / owner confirm); the AR value is the EN label in every row (no Arabic store name was verified at spec time: no web probe), every row `[NATIVE READ]` for the owner to replace the AR value where the store itself publishes an Arabic name, without diacritics.

| host | en (proposed) | host | en (proposed) |
|---|---|---|---|
| nasserpharmacy.com | Nasser Pharmacy | bh.afnan.com | Afnan |
| boutiqaat.com | Boutiqaat | perfumistaaloud.com | Perfumista Al Oud |
| sephora.me | Sephora | goldencollections.net | Golden Collections |
| bh.asgharali.com | Asghar Ali | bh-en.smellsoreal.com | Smells So Real |
| en-bh.ajmal.com | Ajmal | fragrancebh.com | Fragrance BH |
| alhajisbahrain.com | Al Haji's | alibaksh.com | Ali Baksh |
| jalilaperfumes.com | Jalila Perfumes | theperfumesclub.com | The Perfumes Club |
| bahrain.ounass.com | Ounass | bh.arabianoud.com | Arabian Oud |
| noon.com | noon | ashrafsbahrain.com | Ashrafs |
| gcc.luluhypermarket.com | LuLu Hypermarket | bh.oudelite.com | Oud Elite |
| bn.boots.com | Boots | bdutyfree.com | Bahrain Duty Free |
| bolo.bh | Bolo | reefperfumes.com | Reef Perfumes |
| bh.jashanmal.com | Jashanmal | goldenscent.com | Golden Scent |
| klinq.com | Klinq | bh.azhaperfumes.com | Azha Perfumes |
| bahrain.naseem.com | Naseem | beautyandblends.com | Beauty and Blends |
| bh.mubkhar.com | Mubkhar | en-bh.rituals.com | Rituals |
| bh.taifalemarat.com | Taif Al Emarat | | |

### 3. Change list

Byte copies first.
1. New `data/merchant_labels.json` (2.4, ASCII, LF, sorted keys, `json.dumps(..., ensure_ascii=True, indent=1, sort_keys=True)` + newline).
2. New `app/services/store_labels.py` (2; module docstring names the flag, the table, the fallback; no constant named with a gitleaks keyword: `LABELS_PATH`, `_LABEL_CACHE`, `_LABEL_LOCK`, `_LABEL_WARNED`, `_DIACRITICS`).
3. `app/services/response_builder.py`: `from app.services import store_labels as _store_labels` beside the leaf imports; the `output_lang` kwarg after `kb_views`; one docstring sentence; the pass hunk after :2346.
4. `app/services/structured_comparison_service.py`: `output_lang=ctx.get("output_lang"),` (partial, after the S81-11b line), `output_lang=output_lang,` (REST, stream); the conditional ctx entry in the literals :4343-4351 and :5212-5224, each with a `# S81-18b` comment.
5. New `tests/test_s81_s18b_store_label.py` (reads the shared golden for its OFF row).

### 4. Existing pins

4.1 Deliberate changes: none (R9 untouched; every body snapshot runs flag-unset; `tests/test_compare_timeout_graceful.py:73-151` builds its own `_partial_build_ctx` dicts without a language: `ctx.get("output_lang")` is None there).
4.2 Must stay green: S81-11b 4.2 plus `tests/test_s81_s18_kb_first_serve.py` R9, `tests/test_compare_timeout_graceful.py`, `tests/test_cost_meter_s74.py` (its `_partial_build_ctx` fake :1353), `tests/test_price_public_view*` / every `public_price_view` reader (the function is not edited), `tests/test_w4_14_*` (the Arabic verdict lane; `output_lang` routing unchanged), `tests/test_s81_kb_schema.py` P01 (the leaf names no `kb_service` path string).

### 5. RED tests: `tests/test_s81_s18b_store_label.py`

Hermetic: `import app.main` first; a synthetic table written to `tmp_path` and installed through `store_labels.LABELS_PATH` + `_reset_label_cache()` (rows `store-a.example.com` -> en "Store A" / ar "<Arabic letters built with chr() from code points, no diacritics>", `store-b.example.com`, `iherb.com`); the S18 harness for the orchestrator rows (KB price on slot 0 from HOST_A; slot 1 a live price dict `{"amount": 9.5, "currency": "BHD", "retailer": "store-b.example.com", "url": "https://store-b.example.com/p", "source_method": "page_scrape"}` from a faked `_get_price`); missing symbols asserted with `importlib.util.find_spec` / `getattr` / `inspect`.

| # | test | assertion | at base | satisfied by |
|---|---|---|---|---|
| R1 | `test_r1_leaf_and_reader` | `find_spec("app.services.store_labels")` not None; `store_label_enabled` a house boolean (the R1 spellings of 11b) | AssertionError | 3.2 |
| R2 | `test_r2_table_shape` | `data/merchant_labels.json` exists; bytes all < 128; `version == 1`; every key `== normalize_host(key)` and matches `KB_HOST_REGEX`; every value has exactly `en` / `ar` non-empty str; no value contains `/`, `:` or `http`; no AR value contains a code point in U+064B-U+0652 or U+0670; keys sorted; the 2.4 host set is a subset of the keys | AssertionError (absent) | 3.1 |
| R3 | `test_r3_label_for_lookup_and_lang` | `label_for` over: a row host en / ar; `www.` + upper + `:443` normalised; the url-host second lookup (`iHerb` + iherb.com url); unknown host -> the retailer string; retailer None -> None; `lang` "ar" vs "en" vs None differ on the row host | AssertionError | 3.2 |
| R4 | `test_r4_builder_pass_both_surfaces` | `"output_lang" in signature` asserted; a builder call with two price dicts, flag ON, `output_lang="ar"`: `products[i].price.store_label` and `overview.products[i].price.store_label` carry the ar labels; every other price key byte-equal to the OFF build; the input product_data price objects carry no `store_label` (never mutated) with `ENABLE_EXACT_PRICE_GATE` "false" and "true" | AssertionError | 3.3 |
| R5 | `test_r5_orchestrator_kb_and_live` | full config, KB ON with card0 (HOST_A) and slot 1 live: REST payload and stream `complete`: slot 0 label of HOST_A, slot 1 label of store-b; with `output_lang="ar"` the ar labels; the camera scenario (no lang) the en labels | AssertionError | 3.3 + 3.4 |
| R6 | `test_r6_partial_builder_lang_from_ctx` | `_build_partial_response` with ctx carrying `output_lang "ar"` -> ar labels; without it -> en | AssertionError | 3.4 |
| R7 | `test_r7_fail_safe_table` | `LABELS_PATH` -> a missing file / invalid JSON / a row with a diacritic: every label is the retailer string and exactly ONE WARNING `[STORE_LABEL] table unavailable type=` per file state across two builds | AssertionError | 3.2 |
| R8 | `test_r8_flag_read_first` | flag OFF: a `LABELS_PATH` whose stat raises is never touched (no WARNING), no key; flag ON with `label_prices` patched to raise -> no key anywhere + one WARNING `[STORE_LABEL] pass skipped:` | AssertionError | 3.3 |
| P1 | `test_p1_flag_off_golden_full_config` | the 11b P1 recipe (OFF spellings x W4-13 states, KB ON with cards, B1 ON, the result gate ON), also with `output_lang "ar"` on the REST scenario: equal to the shared golden; no `store_label` in any payload | green (recorded at base) | base |
| P2 | `test_p2_classify_price_dict_untouched` | `_classify(_card(P0))["price"]` key set equals S18 R9's set | green | base |
| P3 | `test_p3_sse_prices_frame_unchanged` | flag OFF and ON-at-base: the stream's `prices` frame keys equal the base frame (the label is a `complete`-only key; documents L-S18b-2) | green | base |

Counts: RED 8, PIN 3.

### 6. Mutation table

| M | Mutation | Killed by |
|---|---|---|
| M1 | the pass drops the flag read | P1, R8 |
| M2 | the fallback is None instead of the retailer | R3, R7 |
| M3 | `lang` ignored (always en) | R3, R4, R5 |
| M4 | the key not normalised (raw retailer lookup) | R3 |
| M5 | only `products[i]` labelled (overview missed) | R4 |
| M6 | the price object mutated in place | R4 (exact gate OFF half) |
| M7 | the partial site passes no lang | R6 |
| M8 | the diacritic check dropped from the table validation | R7 |

### 7. Comm set: the group's (section 12.1).

### 8. CLAUDE.md row
`- ENABLE_STORE_LABEL (S81-18b, default OFF, read PER CALL by app/services/store_labels.store_label_enabled as the first statement of the builder's price-dict pass): every price dict the builder emits (products[i].price and overview.products[i].price; KB-served and live alike) gains the additive price.store_label = the display name of the price's retailer host from the repo table data/merchant_labels.json (keyed by deny_hosts.normalize_host, the price url's host as the second lookup; EN / AR by the request's output_lang, passed to build_comparison_response at the three call sites), falling back to the retailer string (today's rendering) when no row matches; the pass writes new dicts (never mutates a price object); a missing or invalid table labels nothing but the fallback (one WARNING per file state). OFF: no key anywhere, the table is never read. The SSE prices frame and the URL envelope carry no label. The client keeps rendering price.retailer until S81-11d reads store_label. RED tests/test_s81_s18b_store_label.py.`
Owner steps: the [NATIVE READ] of every AR label in `data/merchant_labels.json` (2.4) before the flip; flip with or after the S81-11d client line.

### 9. Stated limits
- L-S18b-1: the labels are a repo data table until a kb_merchants display-name column exists (S81-18c, FOCUS by migration); a table edit is a deploy.
- L-S18b-2: the SSE `prices` frame (before `complete`), the URL envelope and stored rows written before the flip carry no label.
- L-S18b-3: a host missing from the table renders the retailer string (today's behaviour); the seed covers 33 BH fragrance hosts only.
- L-S18b-4: every AR value equals its EN label until the owner's native read; camera compares (no lang) always get EN.

### 10. Out of scope
A kb_merchants column (S81-18c); the client reading `store_label` (S81-11d); labels on the URL envelope; the product-level `retailer` mirror.

### 11. Open questions
- Q-S18b-1: the lang seam (a builder kwarg + the conditional ctx entry) vs emitting both labels (`store_label` en + `store_label_ar`) with no orchestrator lang plumbing. Default: the kwarg (the brief's "in the request's language").
- Q-S18b-2: the url-host second lookup (default YES: a name-shaped retailer like `iHerb` still gets its row).
- Q-S18b-3: the 33-host seed and its EN labels (2.4): confirm, or widen to the GCC fragrance catalog hosts (95 live rows; KB serving is BH / BHD only today). Default: the 33.

---

## 12. The group

### 12.1 Combined comm set (the union rule, re-derived at 18cb9e04)
Derivation (`<scratchpad>/g8spec/comm.py`, read-only over the worktree): (a) module and symbol reference grep over `tests/**/test_*.py` for the five edited modules (result_gate, sentry_service, response_builder, kb_serve, structured_comparison_service) and the touched symbols (`assess_result`, `capture_result_status`, `telemetry_tags`, `comparison_result_status`, `build_comparison_response`, `_kb_views`, `kb_views`, `store_label`, `aggregates`, `merchant_labels`, `output_lang`, `_stamp_unit_metadata`, `_partial_build_ctx`, `public_price_view`, `fetch_cards`, `classify(`, the three flags, `ENABLE_KB_FIRST_SERVE`, `verify_flag_byte_identity`, `normalize_host`); (b) every importer of an edited module: the transitive import closure of the five modules inside app/ and scripts/ by AST (104 modules incl. `app.main`, `<scratchpad>/g8spec/closure.txt`) and every test naming a closure module (664), plus every `app.main` / `app.api` / `TestClient` user; (c) the source-scanning pins (the forced list: test_model_config, test_model_config_enforced, test_prompt_fence, test_u3c_store_false_pin, test_start_command*, test_migration_index_predicate_immutability, test_openai_key_log_hygiene_s69, test_sentry_channels_u8d_unit, test_sentry_channels_u8d, test_secret_scan_static, test_hermeticity_pins, test_s81_kb_schema) and every test combining a source read (`inspect.getsource`, `ast.parse`, `find_spec`, `__file__`, `read_text`, `read_bytes`) or a walker with an app / scripts / data / SmartCompareApp path; (d) the CLAUDE.md readers (test_ci_gates, test_behavior_dimension_translation, test_s81_s04_spend_breaker, test_s81_s08b_legacy_fingerprint, test_s81_s08b_gate_rows, test_s81_s23_bypass_retire and every test naming CLAUDE.md); (e) importers of the test-support helpers that reference edited modules (`_env_safety`, `conftest`, `_gen_w4_13_flag_off_ledger`); MINUS the four `.githooks` test files `tests/test_precommit_hook.py`, `test_precommit_hook_round2.py`, `test_precommit_hook_phase_b.py`, `test_precommit_hook_phase_b_round2.py` (no `.githooks` change). The new `store_labels.py` and `merchant_labels.json` have no reader at base (measured, 18b.1.8). SmartCompareApp-scanning backend tests join through (c).
Result: **700 files** (`<scratchpad>/g8spec/COMM_SET_G8.txt`; sorted LF list sha256 `d0e58a4e66b09036c29af1ddda82bd4ae834f324293258b7c596a5c5b3eb4707`), plus the three RED files at GREEN (HEAD-only, the units).

Base record (LC-6, stored by this spec): `<scratchpad>/harness/base_records/18cb9e04a36382fc417307500a092486f618d95e/d0e58a4e66b09036c29af1ddda82bd4ae834f324293258b7c596a5c5b3eb4707.{files,header.txt,txt,pyt.log}`:
- 699 members REUSED OUTRIGHT from the same-sha records `e701a8ba...` (726, the S81-22 set) and `4345a784...` (297, the SF1 set) (same sha, same bytes);
- 1 member RUN at 18cb9e04: `tests/test_cohort_snapshots.py` (inside `[pyt] tag=g8spec-base-pins2 ... elapsed=23s bound=1200s status=OK rc=0`, 954 passed);
- the base FAILED set = **22 node ids**, all known environmental: 2 test_auth_interceptor, 2 test_page_scraping, 2 test_personalization_bundle_c, 2 test_prompt_truth (tiktoken), d16 r10 / d17 r9 / s16 r27 x5 / s19 r15 (CRLF hygiene), s10 r06 (lexicon CRLF), d22c p1 x5 (the golden read under CRLF).
At the RED re-point (a new main sha) the record is re-derived by GC-9 per-file reuse: a member is reused only when its file is unchanged since 18cb9e04, its text names no module stem SF1 / S81-22 changed (feedback_routes, feedback_service, version_routes, referral_routes, referral_service, database_service, text_routes, image_routes, url_routes, compare_runs, cron_compare_judge), nor CLAUDE.md, nor app.main / TestClient when an app/api file changed, and it is no walker; the rest run at the new base in chunks of <= 25 files (bound 1200; one pytest at a time); the new comm set also gains every importer of the merged `app/services/compare_runs.py` (it imports result_gate). GREEN runs the set + 3 at HEAD; `comm -13` of the sorted FAILED sets must be EMPTY.

CI-order set (one call, bound 1200, flags unset, and again per row where a row sets them): the three RED files + test_s80_b1, test_s81_s20_result_gate, test_s81_s18_kb_first_serve, test_s81_g4_gate_rows, test_s81_g3_gate_rows, test_s81_s10_fragrance_gate, test_s81_s10_gate_rows, test_s81_s10b_links_gate, test_s75_fanout_identity, test_w4_13_flag_off_ledger, test_s71_u13_compare_auth_required, test_m18_factcheck_honest, test_cohort_summary_orchestrator, test_compare_timeout_graceful, test_cost_meter_s74, test_partial_response_no_fabricated_scores, test_s81_kb_schema, test_paid_route_metering, test_ci_gates, test_hermeticity_pins.

Client fences: the fourteen (brand/inAppMark.u4c, clientTruth/{medicalNote,privacyManifest,shareTruth}.s74, clipboardFallbackService, config/nativeBundle.w37, DimensionBars.perCategory, honestCounts.s69, landing.domain.s76, navigation/linking.w315, onboarding/step05Trust.s69, playInstallReferrerService(+.edges), ResultsScreen.timeout) + b3a/nativeStrings, BY PATH through the junction the orchestrator creates at GREEN (the app/ edits and CLAUDE.md change). Measured: no `SmartCompareApp/__tests__` file reads result_gate.py, sentry_service.py, response_builder.py, kb_serve.py, structured_comparison_service.py, CLAUDE.md (no `readFileSync` of it) or any new data file (the repo files the fences name: referral_service, extraction_service, attribution_service, usage_service, scoring_service, reengagement_service, push_service, database_service, analytics_service, sitemap_discovery_service, robots_eval, data/trending_curated.json, data/cohort_priors.json). Expected green, unchanged. FULL jest once in the final round (LC-7).

Corpus gate: `scripts/verify_flag_byte_identity.py --proof-root <_proof> --flags ENABLE_RESULT_AGGREGATES,ENABLE_STORE_LABEL,ENABLE_RESULT_STATUS_METADATA` at base and HEAD; it drives `price_service.extract_price_from_html` only, which none of the edits reach: OVERALL SHA256 expected EQUAL (not run at spec time; RED measures the base digest).

Other gates (cheapest first): ruff `--select E9,F63,F7,F82` and `py_compile` on the five edited Python files, the new leaf and the three RED files; `json.loads` on the table and the golden; bytes > 127 = 0 in every new file; `git diff --stat` shows no whole-file diff; the added-line sweep (no 64-hex literal in one piece; no constant named with access / auth / api / credential / creds / key / password / secret / token: `AGGREGATE_FIELDS`, `LABELS_PATH`, `_LABEL_CACHE`, `_LABEL_LOCK`, `_LABEL_WARNED`, `_DIACRITICS` are clean); the P11 banned substrings absent from result_gate.py; no string constant in app/ containing `kb_service` with `app.` or `/` (P01).

### 12.2 Combined footprint
app/: `app/services/result_gate.py`, `app/services/sentry_service.py`, `app/services/kb_serve.py`, `app/services/response_builder.py`, `app/services/structured_comparison_service.py`, NEW `app/services/store_labels.py`. data/: NEW `data/merchant_labels.json`. tests/: three new RED files, one new fixture `tests/fixtures/s81_g8_flag_off_golden.json`. CLAUDE.md. No E-row (no existing test edited). No migration, `.github/`, `.githooks/`, `SmartCompareApp/`, requirements, railway config or route file.

### 12.3 Shared-file plan
Section 0. response_builder.py: two import lines (adjacent), two signature kwargs (adjacent, 11b first), the 11b stamp after :2334 and the 18b pass after :2346 (disjoint). scs: at each of the three call sites one `kb_views=` line then one `output_lang=` line after the last existing kwarg; the two ctx entries are 18b-only. GREEN applies 11b's lines before 18b's so each unit's hunks stay reviewable; the RED files import the modules fresh and do not depend on each other.

### 12.4 PR plan
ONE PR `feature/s81-g8-followups` -> main, body <= 25,600 bytes measured with python: a summary; one short section per unit (B1b, S81-11b, S81-18b: what, flag, RED file, counts); the E-rows table (none expected); the comm result (700 + 3, the base record id `d0e58a4e...` or its re-derivation at the then-main, branch-only-new EMPTY); the corpus gate line (EQUAL); the fences and the full-jest figure; the stated limits by id (L-B1b-1..4, L-S11b-1..4, L-S18b-1..4); the owner steps names-only (B1b none; 11b after 045 + KB-first live + S81-11d; 18b the native read then with S81-11d); the `[NATIVE READ]` list = the 33 AR values of `data/merchant_labels.json`. Mutation tables and per-row evidence go to specs/ files in the state folder.

### 12.5 CLAUDE.md
ONE block after the NEWEST block at the final round (at base: after the S81-G7 owner-steps bullet, CLAUDE.md:594, before `## Tests` :596; at the final round after whichever of the SF1 / S81-22 blocks is newest, one blank line before its heading), heading `**SESSION 81 flags (S81-G8 FOLLOWUPS: B1b URL-TELEMETRY + S81-11b RESULT-AGGREGATES + S81-18b STORE-LABEL, 2026-11-06; TWO new flags default OFF read PER CALL, unset in production by construction; B1b rides ENABLE_RESULT_STATUS_METADATA; the seventh SAFE group under LC-9; spec .qa-s80/S81-G8_UNIT_SPEC.md, rulings specs/RULINGS_S81_G8.md):**` followed directly by the three rows of sections 8 and one owner-steps bullet; the :341 pointer clause gains, in merge order after the S81-G7 sentence (and after SF1 / S81-22 if merged first): `` `ENABLE_RESULT_AGGREGATES` (S81-G8 S81-11b, default OFF) and `ENABLE_STORE_LABEL` (S81-G8 S81-18b, default OFF): the rows of the **SESSION 81 flags (S81-G8 FOLLOWUPS, ...)** block. ``; the two in-place edits of B1b section 8 (CLAUDE.md:475 and the S81-20 block :584-586). Text constraints measured: no line containing both `scoring_method` and `enum` (test_behavior_dimension_translation.py:215-233), none of the five S23 forbidden phrases (test_s81_s23_bypass_retire.py:290-296), pure ASCII in the added text.

DEFECT_LEDGER ids (drafted, names only; the orchestrator files them): `B1b URL-TELEMETRY` (closes S81-20 L19 / R-S20-13), `S81-11b RESULT-AGGREGATES` (the backend half of the removed client counters, PLAN_S81:109), `S81-18b STORE-LABEL` (closes S81-11 L12 / R-S11-14 behind the flag).

### 12.6 SAFE check (FOCUS surfaces)
| Surface | Touched? | Evidence |
|---|---|---|
| auth / tokens / sessions | no | no auth_routes / dependency / token code; the routes are not edited |
| quota / billing / refunds | no | no usage_service, no refund or reserve call; the URL route's refund arms are read, not edited; B1b changes a Sentry message after delivery |
| legal or privacy text | no | no app/legal, landing or privacy-inventory file; the new values are public store names, counts and a timestamp (no personal data) |
| consent path | no | no aiConsent / router consent code |
| security middleware | no | sentry_service's scrubbers (`before_send`, the breadcrumb scrubber) untouched; only `capture_result_status`'s assessment call changes (enum tags) |
| migrations | no | none; 18b deliberately uses a repo table instead of a kb_merchants column (S81-18c) |
| Redis / Lua scripts | no | none |
| App-Review-visible client surface | no | no client file; the build-3 client ignores unknown keys (measured: no `Object.keys/entries` over a price or metadata object in `SmartCompareApp/src`, no reader of `store_label` / `aggregates`); every key is dark |
| secrets or key handling | no | no new credential name; nothing joins CREDENTIALS_UNSET |
Result: **no FOCUS surface; every unit stays in the group** (focus_surfaces_found empty).

### 12.7 Known rebases (the RED re-point)
- PR #392 SF1 (feedback_routes / feedback_service / version_routes / referral_* / database_service / CLAUDE.md / the r01 tuple / the s05 allowlist): no file of this group's app footprint; CLAUDE.md (the block order and the :341 clause), and the comm-set re-derivation (database_service is in the closure).
- The S81-22 branch (text_routes / image_routes / url_routes one line each beside the `capture_result_status` calls :885 / :1090 / :1482 / :782 / :392, compare_runs.py, the judge script, CLAUDE.md, the r01 tuple, the s05 allowlist, tests/test_migration_043_delete_user_cascade.py): no hunk of this group touches those lines; `compare_runs.build_run_row` calls `_rg.assess_result(body, product_categories=...)` (S81-22 spec 147): B1b's default keeps it byte-identical (Q-B1b-2 for the URL reading there); compare_runs.py and the judge script join the comm set as result_gate importers.

Not done in this spec: the RED files, the golden, the table, the corpus gate at base, the mutation runs, any production probe.
