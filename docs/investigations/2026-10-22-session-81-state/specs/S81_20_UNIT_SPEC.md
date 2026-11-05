# S81-20 unit spec (measured): B2-RESULT-GATE-V2 (refuse unsupported verdicts as non-deliveries; FOCUS: the quota path)

Unit S81-20 of PLAN_S81 (Milestone M5, `:164`: "abstain only when the KB cards plus live evidence cannot
support a winner (placeholder_identity, same_identity, category_conflict, no_evidence); every exit per R-A3
(refund with consumed_keys, no lifetime bump, no history row); every abstain writes gaps; sized by B1's
measured abstain rate and the D17 pair hit rate before any flip"), the session-80 unit B2 RESULT-GATE
re-specified on the new brain. Binding inputs: the unit brief `specs/S81_20_BRIEF.md` (rulings
R-S20-1..R-S20-22, which settle every B2_SPEC_REVIEW item BL1 / BL2 / C1-C13 / Q-R1..Q-R7 and every B2 spec
question Q1-Q7), PLAN_S81 (Standing constraints, VERIFY-stage corrections, F1-F4, owner decisions 1-12),
PLAN_S80 section 0 (the contract freeze) and section 1 R-A3 / R-A4 / R-A5 / R-A6 (R-A5 as amended by
R-S20-4), the session-80 RULINGS_R0 (R0-1, R0-4, R0-5, R0-6) and RULINGS_BATCH1 (B3-R6(11), B4-R6), the
session-80 `B2_UNIT_SPEC.md` and `B2_SPEC_REVIEW.md` (the row intent R1-R70 / P1-P13 / M1-M23 is kept and
re-numbered here).

- **Unit:** S81-20 B2-RESULT-GATE-V2. **Class:** FOCUS by LC-1 (quota / billing / refunds on every paid
  route, the camera's anonymous credit, the error-envelope surface): Opus adversarial spec review, two
  adversaries at GREEN (correctness; quota-and-billing with the S81-10 lens's checks), a re-verifier for
  any fix round touching app/.
- **Flag:** `ENABLE_RESULT_GATE` (the R-A2 name; NEW, default OFF, read per call with the house idiom; no
  knob). Already NAMED (not read) in `CLAUDE.md:475` (the B1 row) and in the docstrings of
  `app/services/result_gate.py:14` and `app/services/response_builder.py` (the B1 comment); no code reads
  it at base (`grep -rn ENABLE_RESULT_GATE app tests scripts` -> result_gate.py, response_builder.py
  comments + CLAUDE.md only).
- **Worktree:** `C:/Users/SynAckITPC/Documents/AI/sc-s81-s20` (detached at the base sha; no
  SmartCompareApp/node_modules junction until GREEN). **Branch:** `feature/s81-s20-result-gate-v2`.
- **Base sha:** `6869a3e655805afd3adbba43f99578dd79585934` (origin/main after #388 S81-G5). `git rev-parse
  HEAD` == base; `git status --short` EMPTY at 08:05 AST 2026-11-05 and after every probe below; the only
  file this spec writes in the worktree is this one, under the gitignored `.qa-s80/`
  (`git check-ignore -v` -> `.gitignore:72:.qa-*/`).
- **Measurement location:** `<scratchpad>/s81-20/` (= `C:/Users/SYNACK~1/AppData/Local/Temp/claude/
  cde30765822f13ce/03431011-0c7e-4ecd-b0ce-08ff47f4af10/scratchpad/s81-20/`): base_r1..r4.log,
  comm_set.py, comm_set.txt (388 files, sha256 97218ca801416b02...), comm_set_summary.json,
  probe_jsonld.py, probe_g3.py, probe_g3b.py. The probes import only the pure `result_gate` (stdlib +
  `text_sanitize`, which imports `re` only) with `python -I -B` (no bytecode written, no dotenv load) or
  parse fixture HTML with stdlib json/re; no app.main import outside the bounded runner.
- **Evidence pointers:** PLAN_S81 `:164`; PLAN_S80 section 0 items 1-6 and section 1; the session-80
  `runs/research/contract_freeze.json` (finding 1, the read paths) and `runs/research/eval_regression.json`
  (T01 V04, T03 V09, T04 V10 "Hyper X MIC", T05 V07 GUESS / GUESS!, T10); the session-80 DEFECT_LEDGER rows
  MYEZ-001 / 002 / 003 / 004 / 007 / 011 / 012 / 027; the session-81 DEFECT_LEDGER row S81-20 (`:49`,
  PLANNED); PLAN_STATUS_S81 R-G3-6 (field_status is not a gate input), R-G4-2 (a KB-served price is
  `page_scrape` + `as_of`), R-G4-10 ("S81-20 consumes the G3 gap write and the G4 kb_hit marks only").
- **Sister units and contracts:** B1 RESULT-STATUS (#364, merged: the predicates, the builder stamp, the
  `comparison_result_status` message); B3 VISION-IDENTITY-V2 (#365: `confidence`, `_category`,
  `_distinguishing_features`, `_image_index`, `_is_product`, `public_vision_products`); B4 URL-MODE-V2
  (MERGED: `url_mode_v2` / `_compare_with_deadline`, the three coded URL refusals + its passthrough block);
  S81-09 DEVICE-QUOTA (#379: `consumed_keys` incl. `device_daily`, `_device_refund_keys`, the
  `_DEVICE_DEBIT` stash, the USAGE_LIMIT passthrough); S81-10 / S81-10b FRAGRANCE-ONLY-GATE / LINKS-GATE
  (#381 / #382: the pre-consume refusals, the refusal budget, CATEGORY_NOT_LIVE and its passthrough block,
  the camera pair gate); S81-G3 KB-INGEST (#384: `_kb_ingest_tail`, `kb_ingest.build_job` / `run_job`, D05
  `metadata.field_status`); S81-G4 KB-SERVE (#385: `metadata.kb_hit`); S81-11 (client, renders `reason`
  later: the per-reason copy incl. "those two links are the same product" is ITS brief, R-S20-3);
  S81-22 COMPARE-RUNS (later: makes refusals of KB full hits countable, R-S20-19). Known rebase hunks: none
  in flight on these files at this sha (S81-11 is a client unit).
- **Personal-data rule:** no real name, email, phone, Apple id, device id, address or account id in any
  file, test, fixture or log line; synthetic values built at run time (user ids like `s20-<node>`, device
  fingerprints as sha256 of a run-time string); the added-line sweep (@gmail, +973, 8-digit runs, key
  shapes) runs over the GREEN diff; no digest / hash constant named with a gitleaks keyword (access / auth /
  api / credential / creds / key / password / secret / token). This spec: pure ASCII, LF (checked after the
  write).

---------------------------------------------------------------------------------------------------

## 0. What the unit does (one paragraph)

Under the new dark flag `ENABLE_RESULT_GATE`, a comparison that the B1 assessment does not support (the gate
computes `result_gate.assess_result` ITSELF with the per-product categories; it never reads
`metadata.result_status`, `metadata.field_status` or `metadata.kb_hit`) is refused as a NON-DELIVERY through
envelopes build 3 already renders: the text POST / GET and URL compares answer HTTP 400 `code
INSUFFICIENT_DATA` (build 3: "Thin data on that pair") with an ADDITIVE `reason` in {placeholder_identity,
same_identity, category_conflict, no_evidence}; the stream's terminal pair is the existing INSUFFICIENT_DATA
shape plus `reason`; the camera refuses BEFORE the paid compare with the existing `action:'error'` body plus
`reason` in {placeholder_identity, low_confidence, same_identity, category_conflict} (always `action:'error'`,
never `need_second_product`, `comparison_failed`, a new code or a 503). The URL gate reads the URL envelope
with a JSON-LD-aware evidence reading (string prices and ratings count). Every refusal refunds the reserved
credit with the `consumed_keys` dict the consume returned (S81-09 shape, incl. the device-daily key) and the
anonymous camera credit with its keys, BEFORE any raise; never calls `record_lifetime_comparison`; writes no
history row; writes exactly ONE `search_logs` row `success=False`, `error_message="result_gate:<reason>"` in
both W4-13 states; logs ONE INFO line `[RESULT_GATE] refused input=<type> reason=<reason>` (constants
only). The builder stamps `metadata.product_categories` under this flag too, so `category_conflict` fires in
every flip order. "Every abstain writes gaps" is satisfied, without any KB write in this unit, by the G3
ingest tail that already ran inside the orchestrator before the route sees the body (measured in 1.7: the
no_evidence class with resolved identities is queued at identity `medium` / `high`; the identity classes
have nothing to queue). Flag OFF the unit is byte-identical on every response, SSE frame, stored row, log
row, refund call and KB write.

---------------------------------------------------------------------------------------------------

## 1. Base state (measured at 6869a3e6)

### 1.1 The delivery exits and where each gate goes (every line read at the base sha in this run)

| Exit | Where (base) | Measured fact | S81-20 seam |
|---|---|---|---|
| text POST | `app/api/text_routes.py:597` `text_compare`; S81-10 pre-consume gate `:618-622` (`_gate = await _category_gate.text_gate(...)` when `fragrance_only_gate_enabled()` and not admin); `usage_consumed = False` `:640`; consume `:641-643` (`consume_comparison_credit(..., **device_quota_kwargs())`); `usage_consumed = usage_check.get("consumed", False)` `:656` (the `consumed_keys` are DROPPED); compare `:663-677`; `_truth` `:681`, `_syn` `:682`; failure branch `:683-726` (W4-13 OFF row `:686-695`, refund `:703-707` WITHOUT keys, W4-13 ON row `:708-719`, `surfaced = _surface_comparison_failure(result)` `:724`, `return surfaced` `:726`); delivery `:728-799` (product_names `:729`, success row `:740-746`, W3-2 echo persist `:748-770`, composite save `:776-790`, `record_lifetime_comparison` `:793-796`, `capture_result_status(result, "text")` `:798`) | a `success:True` body is delivered and billed whatever B1 says | after `:726`, before the comment `:728` |
| text GET | `:804` `text_compare_get`; S81-10 gate `:849-851`; `usage_consumed = False` `:868`; consume `:869-871`; `:884` keeps `consumed` only; compare `:886-900`; `_truth` `:904`, `_syn` `:905`; failure branch (refund `:922-926` without keys; surface `:942`, return `:944`); delivery from `:946` (lifetime `:988-991`, B1 `:993`) | same shape as POST | after `:944`, before `:946` |
| stream | `:999` `text_compare_stream`; S81-10 gate `:1047-1049` raises BEFORE `StreamingResponse` (never reaches the generator); `usage_consumed = False` `:1067`, `:1083` keeps `consumed` only (closure-captured); `_truth` `:1110`, `_syn` `:1111`; `event_generator` `:1113` (locals `:1114-1124`); `_stream = service.compare_from_text_streaming(...)` `:1150-1164`; terminal capture `if event_type in ("complete", "settle_complete"):` `:1172`, latch `:1173-1177` (`complete_after_client_gone = client_gone` on the FIRST terminal); the W3-2 persist condition `:1199-1202` (`comparison_id_echo_enabled() and user_id and not client_gone and not had_error`); `complete_response = data` `:1221`; yield `:1270`; `finally:` `:1271`; chain: `if complete_response and not had_error and not complete_after_client_gone:` `:1275` (W4-13 T3 success:False row `:1276-1296`, success row `:1297-1314`, save `:1315-1347`, lifetime `:1349-1352`, B1 `:1357-1358`), `elif had_error:` `:1359` (keyless refund `:1372-1376`), `else:` `:1394` (keyless incomplete refund `:1403-1407`, T5 row `:1408-1423`) | a `success:False` terminal the client received takes the FIRST branch: no refund, a save attempt, `record_lifetime_comparison` (W4-13b): re-using the terminal shape alone would BILL every stream refusal | intercept at the top of `:1172`; persist condition `:1199-1202`; a new FIRST branch before `:1275` (which becomes `elif`) |
| camera | `app/api/image_routes.py` `identify_and_compare`; anon gate `:234-251` (`anon_consumed_keys = usage_check.get("consumed_keys")` `:251` when metering ON and consumed); `usage_user_id` `:292`, `usage_consumed = False` `:293`; `_refund_reserved_credit(label)` `:296-309` (keyless `refund_comparison_credit(usage_user_id)` `:309`, latched); `_refund_anon_credit(label)` `:313-330` (keyed `refund_anon_comparison_credit(device_fp, anon_consumed_keys)` `:328`, latched); S81-10 budget arm `:335-344`; authed consume `:346-361` (`:361` keeps `consumed` only); vision `:362-401`; parse-error exit `:403-416`; moderation `:426-470`; `products` `:476`, `vision_cost` `:477`; **size enrichment `:479-482`** (`p["name"] = f"{p['name']} {size_or_count}".strip()`, in place); `product_names` `:484`; zero products `:488-497`; one product: S81-10 single refusal `:505-512`, `need_second_product` `:515-524`; two+: `p1`/`p2` `:527-528`, `query` `:529`, S81-10 pair gate `:532-540`, `query_hash` `:541`, `_truth` `:544`, `_syn` `:545`, `try:` `:546` (V2 prefs read `:555-561` inside it), paid compare `:563-567`, post-resolve CATEGORY_NOT_LIVE arm `:572-575`, `comparison_unsuccessful` `:583`, delivery / failure envelope `:600-740` (lifetime `:717-720`, B1 `:736`) | no pre-compare identity, confidence or category check on the pair; the enrichment runs BEFORE the seam, so a placeholder identity with a size escapes `product_is_placeholder` (BL2, re-measured: the loop is at `:479-482`, the seam after `:545`) | snapshot before `:479`; block after `:545`, before `try:` `:546` |
| URL | `app/api/url_routes.py:76` `_reserve_comparison_credit(user) -> bool` (`return bool(usage_check.get("consumed", False))` `:108`, keys DROPPED); `_compare_urls_metered` `:230`; S81-10b budget `:263-264`; consent 503 `:268-273`; reserve `:274` (`usage_consumed = await _reserve_comparison_credit(user)`); `_url_row` `:279-289`; compare `:291-295` (`_compare_with_deadline` under `url_mode_v2`, else `compare_from_urls`); exception refund `:296-304` keyless; failure block `:306-339` (refund `:310-314` keyless, row `:315-319` under W4-13 only, B4 coded refusals `:327-331`, `_surface_comparison_failure` `:332-335`, the bare 400 `:336-339`); delivery `:341-363` (save + lifetime under metering, success row under `_truth`, `capture_result_status(result, "url", ...)` `:362`) | the envelope (`url_extraction_service.py:1499-1508`) has no `metadata`, no `scoring_v2`; the product dict (`normalize_product_data` `:1227-1253`) carries `price.amount = raw.get("price")` VERBATIM (`:1238`), `reviews.rating = raw.get("rating")` (`:1246`), `variant`, the canonical `category` overwritten by the pair category (`:1449`) | after `:339`, before `:341` |

The orchestrator callers of `build_comparison_response` pass `product_categories`: scs `:3882` (the
partial builder, `ctx.get("product_categories")`), `:4782` REST, `:5704` stream; the categories are
captured BEFORE the pair write-back at `:4450` REST / `:5161` stream (`[canonicalize_category(_p.get(
"category")) for _p in products]`). The H6 INSUFFICIENT_DATA early returns are `:4515-4522` (REST) and
`:5289` (stream); their `error` is the bytes `Comparison data was incomplete ` + U+2014 + ` choose different
products.` (measured with `cat -A`: `M-bM-^@M-^T`).

### 1.2 The B1 primitives the gate reuses (`app/services/result_gate.py`, 659 lines, unchanged since B1)

Imports `:18-24` (`__future__`, `os`, `re`, `typing`, `app.services.text_sanitize.dedup_brand_name`);
`REASONS` `:35-42`; `_STATUS_BY_REASON` `:43-50`; `_TRUTHY` `:78`; `result_status_metadata_enabled()`
`:83-85` (the idiom); `_num` `:104-106`; `_finite` `:112-115`; `is_placeholder_identity` `:128-133`;
`product_is_placeholder` `:136-141` (identity text via `dedup_brand_name` OR the name alone);
`_variant_axis` `:151-152` (`variant` or `size_or_count`); `_features_axis` `:155-159` (the key
`distinguishing_features`, NO underscore); `same_identity` `:171-183`; `identity_coherence` `:193-205`;
`price_is_showable` `:210-221`; `rating_is_real` `:236-239`; `real_spec_rows` `:258-272`;
`identity_confidence` `:470-486` (unresolved on a placeholder; low on same / incoherent / a low vision read;
medium on an empty brand, a medium vision read or a side without corroboration; else high);
`_corroborated` `:489-493`; `assess_result` `:504-548`; `stamped_product_categories` `:553-561` (the ONE
reader of `metadata.product_categories`). Bytes: 659 CRLF lines, 0 bytes > 127.

The B1 builder stamp: `app/services/response_builder.py:2304-2326` (`if result_status_metadata_enabled():`
`:2304`, `assess_result(result, product_categories=product_categories)` `:2306`, `product_categories`
stamped `:2309-2311` / `:2318-2319`, the except arm `:2325-2326` logging `[RESULT_STATUS] assess failed` by
type); the D08 rating post-pass `:2328-2338`; `_strip_inference_markers(result)` `:2346`; the import line
`:21` (`from app.services.result_gate import STATUS_SUPPORTED, assess_result,
result_status_metadata_enabled`).

### 1.3 Rule 1 is dead; the category input exists only at the builder

As measured by the session-80 spec (1.3) and re-checked by symbol here: every live path writes the pair
category onto both products before `detect_comparison_quality` sees them (REST write-back after `:4450`,
stream after `:5161`, URL `url_extraction_service.py:1449`), so the per-product categories survive only in
the `product_categories` list passed to the builder. B1's `identity_coherence` over that list is the revived
rule; this unit enforces it (decision D3 of the session-80 spec, kept). `detect_comparison_quality` is not
edited.

### 1.4 The stream bills a success:False terminal (W4-13b), re-measured

`finally` `:1275`: a received `success:False` terminal enters the first branch; under W4-13 flag 1 it writes
the T3 row (`:1276-1296`), then `if user_id:` (`:1315`, outside the success / failure split) schedules the
save and `record_lifetime_comparison` (`:1349-1352`), and no refund fires. The S81-10 stream refusal is
raised at `:1047-1049`, before `StreamingResponse` (`:1425`), so it never enters this chain (R-S20-21).

### 1.5 Refund primitives and the consumed_keys shape (R-S20-22)

- `usage_service.consume_comparison_credit` `:664` returns `consumed_keys` on every consumed result:
  the lifetime-free path `{"daily", "monthly"}` (`:707-716`), the standard path `{"daily", "monthly"}`
  (`:765-769`), and the S81-09 quota path (one Lua EVAL) `{"daily": account_key, "device_daily": key}`
  (`:431-440`; the request-scoped stash `_DEVICE_DEBIT.set(...)` at `:431`).
- `refund_comparison_credit(user_id, consumed_keys=None)` `:833-859`: `_device_refund_keys(user_id,
  consumed_keys)` `:456-477` first (explicit keys carrying `device_daily` win; else the stash when it names
  this user; latched by `debit.refunded`, so a second refund of the same debit returns `[]`); a quota-path
  debit is refunded by ONE EVAL in `_refund_device_debit` `:480`; otherwise `_refund_credit_sync(user_id,
  consumed_keys)` (keyed: exactly the debited windows; keyless: the floor-at-zero / previous-window
  fallback). MEASURED consequence: the existing keyless exits already refund a quota-path debit through the
  stash; the keyed form this unit passes is what makes the non-quota windows exact (M18 usage symmetry).
- `refund_anon_comparison_credit` `:133`; `record_lifetime_comparison` `:862`.
- No existing text / URL / camera-reserved refund passes keys (text `:705`, `:924`, `:1374`, `:1405`; URL
  `:299`, `:312`; camera `:309`); the camera anon refund does (`:328`). B4-R6: the existing exits keep their
  call shape; every NEW exit threads the keys.

### 1.6 The error envelope (`app/middleware/error_handler.py`, 350 lines)

`http_exception_handler` `:160`; `content = {success, error, code, request_id}` `:180-185`; three scoped
passthrough blocks, each behind a local one-line reader (the middleware imports no service): B4
`_url_mode_v2_keys_enabled()` `:50-57` + `_URL_V2_PASSTHROUGH_CODES` `:40`, block `:188-195` (`field` /
`reason` str for its three codes); S81-09 `_device_quota_keys_enabled()` `:65-72` + `_USAGE_LIMIT_SCOPES`
`:62`, block `:200-211` (429 USAGE_LIMIT `resets_at` / `scope`); S81-10 `_fragrance_gate_keys_enabled()`
`:75-81` + `_CANONICAL_CATEGORY_KEYS` `:44-47`, block `:217-231` (CATEGORY_NOT_LIVE); `headers = None` `:232`.
Every other detail key is dropped, so `reason` on INSUFFICIENT_DATA cannot reach the wire without a fourth
block. `text_routes._surface_comparison_failure` `:534-587`: CONTENT_UNAVAILABLE returned `:537-540`;
TIMEOUT / LLM_UNAVAILABLE 503 `:541-556`; the S81-10 arm FIRST among the 400s `:560-565`
(`_category_gate.http_detail(result)`); the coded 400 `:566-570` (`{"code", "error"}`); the W4-9 codeless
floor `:571-586`.

### 1.7 The G3 ingest tail per refusal class (R-S20-18, measured)

- `StructuredComparisonService._kb_ingest_tail` scs `:3889-3924`: reads `kb_ingest_enabled()` and
  `field_status_metadata_enabled()` FIRST (`:3907-3908`); both OFF -> return; else `snap =
  kb_ingest.build_job(result, product_data, product_categories=..., region=..., vision=..., captured_at=...)`
  (`:3911-3914`), stamps `metadata.field_status` under D05 (`:3918-3921`), and under ENABLE_KB_INGEST hands
  `kb_ingest.run_job(snap)` to ONE `asyncio.to_thread` inside ONE `_fire_and_forget(..., "kb_ingest")`
  (`:3922-3923`). Its ONLY call lines are `:4849-4852` (REST, after L3 moderation, before `return result`)
  and `:5798-5801` (stream, before the `settle_complete` yield). Between the category capture `:4450` and
  `:4849` the only returns are the H6 body `:4515` and the moderation body `:4840`, both `success:False`, so
  EVERY `success:True` REST / stream body (incl. a KB-first-served body) passes the tail BEFORE the route
  sees it. The hard-cap partials are built by `_build_partial_response` `:3759-3887` (callers `:4161` REST,
  `:4983` / `:5239` stream), which does NOT call the tail.
- `kb_ingest.build_job` `:270-302`: `identity_confidence` = `result_gate.assess_result(result,
  product_categories=product_categories)["identity_confidence"]` (no vision confidences), i.e. the SAME
  assessment the route gate makes on the same body with the same categories.
- `kb_ingest.run_job` `:383-510`: products, variants, offers, images, reviews only at identity `high`
  (`:427`); gap rows (one per D05 field whose state is `unknown`, `:476-487`, capped by `gap_max()` `:91`)
  at `high` or `medium` (`:412`); only for fragrance-category products (`_is_fragrance` `:160-161`,
  `:414`); insert-ignore + the compare-and-set demand bump (`:500-502`, `_bump_gaps` `:344`).
- Probe (`probe_g3.py` / `probe_g3b.py`, the real pure `assess_result` over the lane1 Tom Ford vs Creed
  body and its mutations, categories `[fragrances, fragrances]`):

| Refusal class (body) | assess reasons | identity_confidence | what G3 already wrote under ENABLE_KB_INGEST | gate adds |
|---|---|---|---|---|
| no_evidence, neither side corroborated (V10 shape: prices pended, ratings derived, specs `{}`, no dims) | [no_evidence], coverage 0 | **medium** | the gap rows of every `unknown` D05 field (fragrance products) | nothing |
| no_evidence, each side corroborated one-sidedly (p0 price only, p1 rating only) | [no_evidence], coverage 0 | **high** | the cards (product / variant / offer / image / review rows) AND the gaps | nothing |
| placeholder_identity (V09) | [placeholder_identity, same_identity] | unresolved | nothing | nothing (a gap needs an identity) |
| same_identity (V07 GUESS / GUESS!) | [same_identity] | low | nothing | nothing |
| category_conflict ([electronics, fragrances]) | [category_conflict] | low | nothing | nothing |
| supported (SUP, coverage 4) | [] | high | cards + gaps (delivered) | n/a |

  So the ruling's expectation holds for full bodies: S81-20 writes NO KB row and adds NO ingest call. Two
  MEASURED gaps in "every abstain writes gaps": (a) a hard-cap PARTIAL refused as no_evidence never passed
  the tail (`_build_partial_response` does not call it), so it queues no gap (open question Q1); (b) the
  camera refusals are pre-compare, so nothing ran (identity classes and low_confidence: nothing trustworthy
  to queue, L-CAM-GAPS); URL has no tail at all (`grep -n kb_ingest app/services/url_extraction_service.py`
  -> nothing; L-URL-GAPS).

### 1.8 The vision product shapes (R-S20-2, R-S20-4, R-S20-5)

- V2 normaliser `openai_service._normalize_vision_products_v2` `:341-397`: every KEPT candidate is
  `{"brand" (or "Unknown"), "name" (or "Unknown Product"), "size_or_count", "visible_price", "confidence"
  (one of the rank keys, else "low"), "_image_index", "_category" (canonicalize_category or None),
  "_product_type", "_distinguishing_features", "_is_product": True}` (`:385-395`). The V2 MARKER is
  `_is_product` (always `True` on a kept candidate, `:394`).
- V1 normaliser `:675-684`: `{"brand", "name", "size_or_count", "visible_price", "confidence":
  p.get("confidence", "medium")}`: no underscore key, so no marker. V1's prompt means "low" as "best guess" /
  "without packaging" (`:606`, `:614`).
- `public_vision_products` `:295-302` strips every underscore key; `VISION_V2_PUBLIC_KEYS` `:134`.
- The orchestrator's vision search identity (scs `:4347-4361`): `full = f"{brand} {vname}"` (the
  post-enrichment name), `"variant": vp.get("size_or_count")`, `category = classify_category_from_text(full)`;
  the V2 features never reach the compare (`_vision_identity_fields` `:1353`). So the size axis IS used by
  the compare (variant), the features axis is NOT (R-S20-4's precondition, re-measured).

### 1.9 URL evidence shapes (R-S20-1, measured)

`probe_jsonld.py` over the four real fixtures (stdlib json over the `application/ld+json` blocks; the first
Product node with offers): `tests/fixtures/bh_gcc/curl_bh_bheshop.html` price `'490.00'` (str), rating None;
`curl_bh_godukkan.html` price `'4099'` (str), rating `'5'` (str); `jsonld_first/
ae_lulu_lowercase_jsonld_pricecurrency.html` price `'175.000'` (str); `jsonld_first/
ae_samawa_ae_og_no_currency_jsonld_aed.html` price `'271.0'` (str). The R-S20-1 regex
`^\d{1,3}(?:,\d{3})*(?:\.\d+)?$|^\d+(?:\.\d+)?$` over stripped strings: `490.00`, `4099`, `175.000`,
`271.0`, `5`, `1,299.50`, ` 12 ` match; `abc`, `1e400` do not; `0` matches and is excluded by `> 0`.
`godukkan` is an iPhone page (electronics): under ENABLE_FRAGRANCE_ONLY_GATE ON the S81-10b links gate
refuses it BEFORE this gate, so the URL rows set that flag OFF explicitly and say so (R-S20-1 NOTE).

### 1.10 Base pass state (bounded runner, one process at a time, every unit flag unset)

```
r1  tests/test_text_routes_error_mapping.py tests/test_http_400_cap_cut_mapping.py
    tests/test_text_error_envelope_no_raw_exception.py tests/test_m13_37_freemium_atomic_consume.py
    tests/test_paid_route_metering.py tests/test_retro_w2_1.py tests/test_m13_26_image_error_envelope.py
    tests/test_image_identify_llm_unavailable_s69.py tests/test_error_middleware.py tests/test_429_contract.py
    tests/test_m18_usage_symmetry.py
    collected 226 items; 226 passed, 13 warnings in 10.46s
    [hermeticity] sentinel checked 226 test(s); [netguard] blocked 25 attempt(s) from 25 node(s)
    (the sentinel class neutralized.supabase.invalid:443, existing baseline behaviour)
    [pyt] tag=s20spec-base-r1 start=2026-11-05 08:15:29 end=2026-11-05 08:15:41 elapsed=13s bound=600s status=OK rc=0
r2  tests/test_s75_fanout_identity.py tests/test_w4_13_flag_off_ledger.py tests/test_w4_13_measurement_truth.py
    tests/test_s80_b1.py tests/test_s80_b3_vision_identity_v2.py tests/test_comparison_id_echo.py
    tests/test_streaming.py tests/test_s78_tier_fill_residual_guard.py tests/test_s78_all_timeout_cap_as_timeout.py
    collected 739 items; 739 passed, 12 warnings in 78.36s
    [hermeticity] sentinel checked 739 test(s); [netguard] blocked 44 attempt(s) from 18 node(s)
    [pyt] tag=s20spec-base-r2 start=2026-11-05 08:16:02 end=2026-11-05 08:17:25 elapsed=83s bound=600s status=OK rc=0
r3  tests/test_auth_error_log_hygiene.py tests/test_events_allowlist_superset.py
    tests/test_sentry_channels_u8d_unit.py tests/test_s71_u13_compare_auth_required.py tests/test_s71_u13_pins.py
    tests/test_global_anti_patterns.py tests/test_camera_vision.py tests/test_m18_preverdict_disconnect_refund.py
    tests/test_s80_url_mode_v2.py tests/test_ci_gates.py tests/test_behavior_dimension_translation.py
    collected 973 items / 1 deselected / 972 selected; 972 passed, 1 deselected, 11 warnings in 31.72s
    [hermeticity] sentinel checked 972 test(s); [netguard] blocked 0 attempt(s) from 0 node(s)
    [pyt] tag=s20spec-base-r3 start=2026-11-05 08:17:56 end=2026-11-05 08:18:31 elapsed=35s bound=600s status=OK rc=0
r4  tests/test_s81_s09_device_quota.py tests/test_s81_s10_fragrance_gate.py tests/test_s81_s10_gate_rows.py
    tests/test_s81_s10b_links_gate.py tests/test_s81_s17_kb_ingest.py tests/test_s81_s18_kb_first_serve.py
    tests/test_s81_g3_gate_rows.py tests/test_s81_g4_gate_rows.py tests/test_s81_s03_llm_ledger_v2.py
    tests/test_s81_s06_anthropic_router.py
    collected 1132 items; 1 failed, 1131 passed, 11 warnings in 58.34s
    FAILED tests/test_s81_s10_fragrance_gate.py::test_r06_production_lexicon_content
      (AssertionError: b"\r" in the bytes of data/fragrance_lexicon.json: the autocrlf working copy of this
      box, `git ls-files --eol` i/lf w/crlf; ENVIRONMENTAL, present in the stored base records
      0b19de5b/90b85603, 0b19de5b/c5734182, 744616e3/ba26af35, c6fb6533/3e2570e2, e1491c97/4b65c5db;
      recorded identically at base and head, never a regression)
    [hermeticity] sentinel checked 1132 test(s); [netguard] blocked 0 attempt(s) from 0 node(s)
    [pyt] tag=s20spec-base-r4 start=2026-11-05 08:19:06 end=2026-11-05 08:20:06 elapsed=60s bound=600s status=FAIL rc=1
```

Every file this unit touches or pins is green at base except the one environmental node above. NOT
MEASURED at spec time (RED's first job, alone): `tests/test_sentry_channels_u8d.py` (child process),
`tests/test_history_routes.py`, `tests/test_home_routes.py`, `tests/test_shutdown_drain.py`,
`tests/test_m13_04_full_stream_deadline.py`, `tests/test_s71_u13_compare_auth_required.py` T23 with the
OpenAPI snapshot under the flag exported (a GREEN-time check). The four runs above are per-file base
records at 6869a3e6 (41 files) the RED round reuses directly.

### 1.11 Line endings and bytes

`git ls-files --eol`: `i/lf w/crlf` for result_gate.py, response_builder.py, error_handler.py,
text_routes.py, image_routes.py, url_routes.py, CLAUDE.md. Measured bytes (python over the working copy):
result_gate.py 659 CRLF / 0 bytes > 127; text_routes.py 2061 CRLF / 267 non-ASCII; image_routes.py 791 /
21; url_routes.py 606 / 0; error_handler.py 350 / 3; response_builder.py 2348 / 668. The edits keep CRLF
(the Edit tool preserves line endings); `git diff --stat` must show content lines only; result_gate.py stays
0 bytes > 127 (B1 P11); new files LF and ASCII.

### 1.12 Libraries, readers and guards the new code must not trip

- Pinned venv `C:/Users/SynAckITPC/Documents/AI/.venv-qaren` (no new dependency; stdlib `re` only).
- Flag idiom (`result_gate.result_status_metadata_enabled` `:83-85`, `kb_ingest.kb_ingest_enabled` `:81-83`):
  `os.getenv("ENABLE_RESULT_GATE", "false").strip().lower() in ("true", "1", "yes", "on")`, per call.
- **B1 P11 purity pin** (`tests/test_s80_b1.py:1146-1157` `test_b1_p11_result_gate_is_pure`; also
  `tests/test_s81_kb_schema.py:1231` lists result_gate in `APP_OK` and `:2073-2084` reads
  `result_gate.product_is_placeholder` at call time, so the existing function stays untouched): result_gate.py stays pure ASCII, imports
  only {os, re, typing, __future__, app.services.text_sanitize}, no `async def`, and none of the SUBSTRINGS
  `sentry_sdk`, `structured_comparison_service`, `response_builder`, `price_service`, `extraction_service`,
  `httpx`, `asyncio`, `socket`, `logging` anywhere in the file (code, comments, docstrings). Therefore: the
  camera category stub (`classify_category_from_text`) is computed in image_routes; the INFO lines live in
  the routes; the em dash is `chr(0x2014)`; the new docstrings never name those modules.
- `tests/test_s75_fanout_identity.py:60-70` `UNIT_ENV` (the FY25 nine digests pop these names per scenario);
  `tests/test_w4_13_flag_off_ledger.py` (the fire_and_forget LABEL sequence + `log_search` kwargs at every
  existing exit with the W4-13 flags unset; chain: `tests/fixtures/_gen_w4_13_flag_off_ledger.py` ->
  `test_w4_13_measurement_truth._clean_flags` `:154-160` and `test_retro_w2_1._install` `:283`); flag OFF
  adds no label and no kwarg.
- `tests/test_s71_u13_compare_auth_required.py` `CLEAN_ENV` `:76-89` and its OpenAPI snapshot `:447-455`
  (T17 / T23): no route parameter or body field changes (`reason` is a response key only;
  `_reserve_comparison_credit` and the camera closure are not routes).
- `tests/test_text_routes_error_mapping.py`, `tests/test_http_400_cap_cut_mapping.py`,
  `tests/test_text_error_envelope_no_raw_exception.py`: the INSUFFICIENT_DATA 400 detail is exactly `{code,
  error}` and the envelope exactly `{success, error, code, request_id}` flag OFF.
- U8d log hygiene (`tests/test_sentry_channels_u8d_unit.py`, `tests/test_auth_error_log_hygiene.py` walk
  `app/`): templates carry constants / closed-set enums only; nothing at ERROR outside an except arm.
- `tests/test_global_anti_patterns.py:70` (the verdict-prompt vocabulary `couldn't` / `try again` /
  `failed to`): the camera sentence is neutral (R-S20-12).
- Production flag state for the design: the newest dated ledger line (session-81 `ledger.md`, 2026-11-05
  07:17: #388 merged, every S81 flag unset). ON in production: ENABLE_PAID_ROUTE_METERING,
  ENABLE_CAMERA_FAILURE_ENVELOPE, ENABLE_COMPARE_AUTH_REQUIRED (since 2026-10-03). OFF (designed for both
  states): ENABLE_RESULT_STATUS_METADATA, ENABLE_VISION_IDENTITY_V2, ENABLE_URL_MODE_V2,
  ENABLE_FRAGRANCE_ONLY_GATE, ENABLE_DEVICE_DAILY_QUOTA, ENABLE_KB_INGEST, ENABLE_FIELD_STATUS_METADATA,
  ENABLE_KB_FIRST_SERVE. UNKNOWN (both states): ENABLE_SEARCH_LOG_TRUTH / _SYNTHETIC_MARKER,
  ENABLE_COMPARISON_ID_ECHO, ENABLE_ANON_USAGE_GATE, ENABLE_STRICT_OPTIONAL_AUTH.

---------------------------------------------------------------------------------------------------

## 2. Contract

### 2.1 Flag and decisions

`ENABLE_RESULT_GATE`: new, default OFF, the 1.12 idiom; single service reader
`result_gate.result_gate_enabled()`; `error_handler.py` keeps a local one-line twin `_result_gate_keys_enabled()`
(the three precedents), pinned equal. No knob. The flag is read per call as: the FIRST statement of
`result_gate_refusal`; the single read `_rg_on = result_gate_enabled()` that opens the camera gate (taken
once, before the size enrichment, and the first operand of the camera block); the first operand of the
builder stamp, of the `_surface_comparison_failure` reason arm and of the handler block.

- **D1 (kept): the gate computes the assessment itself** from B1's pure predicates with the stamped
  categories, never reading `metadata.result_status`; the builder stamps `metadata.product_categories` under
  EITHER flag (2.3), so the flags are independent and, both ON, B2 refuses exactly the bodies B1 stamps
  non-supported (pinned by R26 and R24, R-S20-10 / C10).
- **D2 (kept, R-S20-14): the gate sits at the route exits**, never in the orchestrator (no scs edit).
- **D3 (kept): Rule 1 revived as `category_conflict`** on text / stream / camera; never on URL.
- **D4 (amended by R-S20-1, R-S20-3): the URL reading** applies the placeholder and same-identity rules and
  a JSON-LD-aware evidence reading (2.2); no category check.
- **D5 (kept, R-S20-7): the camera refuses only before the paid compare.**
- **D6 (R-S20-18, R-S20-19): no KB write, no ingest call, no read of `metadata.field_status` /
  `metadata.kb_hit`.** The gaps of the resolved-identity class are G3's (1.7).

### 2.2 `app/services/result_gate.py` additions (pure; appended after `:659`; P11-clean)

Constants (exact):
- `GATE_REASONS = ("placeholder_identity", "same_identity", "category_conflict", "no_evidence")`
- `CAMERA_GATE_REASONS = ("placeholder_identity", "low_confidence", "same_identity", "category_conflict")`
- `GATE_CODE = "INSUFFICIENT_DATA"`
- `GATE_REFUSAL_MESSAGE = "Comparison data was incomplete " + chr(0x2014) + " choose different products."`
  (byte-equal to the H6 sentence scs `:4517`, R-S20-12).
- `CAMERA_GATE_MESSAGE = "Photograph each product in its own photo so we can tell them apart."` (R-S20-12;
  build 3 renders `vision_failed` from its own i18n; the string is for logs and later clients).
- `GATE_LOG_PREFIX = "result_gate:"`
- `_GATE_REASON_BY_ASSESS = {"placeholder_identity": "placeholder_identity", "same_identity":
  "same_identity", "unsupported_category": "category_conflict", "category_conflict": "category_conflict",
  "no_evidence": "no_evidence"}` (`not_success` never maps).
- `_URL_NUMBER_RE = re.compile(r"^\d{1,3}(?:,\d{3})*(?:\.\d+)?$|^\d+(?:\.\d+)?$")` (R-S20-1).

Functions (each total: malformed input -> None or the conservative answer; never raises):
- `result_gate_enabled() -> bool`: the idiom over `ENABLE_RESULT_GATE`.
- `gate_reason(result, *, product_categories=None) -> Optional[str]`: no flag read. None unless `result` is a
  dict with `success is True`; else the first `assess_result(result, product_categories=...)["reasons"]`
  entry that maps through `_GATE_REASON_BY_ASSESS`, else None. Invariant (R8, the mapping-completeness pin):
  for every `success:True` body, `gate_reason(...) is None` iff the status is `supported_result`.
- `_url_number(value) -> Optional[float]`: an int / float that is not bool and `_finite`; or a str whose
  `.strip()` matches `_URL_NUMBER_RE`, converted with `float(s.replace(",", ""))`, returned only when
  `_finite`; else None.
- `_url_price(p) -> bool`: `p["price"]` is a dict, `unavailable is not True`, `estimated is not True`, and
  `_url_number(amount)` > 0.
- `_url_rating(p) -> bool`: `r = _url_number(p["reviews"]["rating"])` (when `reviews` is a dict) with
  `0 < r <= 5`, or `rating_is_real(p)` with the same range on `p["rating"]`.
- `url_gate_reason(result) -> Optional[str]`: no flag read. None unless a dict with `success is True` and a
  `products` list of >= 2 dicts; p0, p1 = the first two. In order: `product_is_placeholder(p0) or
  product_is_placeholder(p1)` -> `placeholder_identity`; `same_identity(p0, p1)` -> `same_identity`
  (R-S20-3); else coverage = `(_url_price(p0) and _url_price(p1))` + `(_url_rating(p0) and _url_rating(p1))`
  + `(real_spec_rows(p0.get("specs"), p1.get("specs")) >= 1)`; coverage 0 -> `no_evidence`; else None.
- `camera_gate_reason(p0, p1, *, categories=None, identities=None) -> Optional[str]`: no flag read; the pair
  the route would compare. `identities` is the pre-enrichment snapshot `[(brand, name), (brand, name)]`
  (R-S20-2); when it is a 2-sequence of 2-tuples side i's identity view is `{"brand": b_i, "name": n_i,
  "size_or_count": p_i.get("size_or_count")}`, else `{"brand", "name", "size_or_count"}` read from p_i. A
  non-dict side counts as a placeholder. In order: either view `product_is_placeholder` ->
  `placeholder_identity`; either side V2-shaped (`p_i.get("_is_product") is True`, R-S20-5) with
  `confidence` a str whose `.strip().casefold() == "low"` -> `low_confidence` (ANY low, either side);
  `same_identity(view0, view1)` -> `same_identity` (R-S20-4: the views carry no features key, so two equal
  normalised identities are the same identity whatever `_distinguishing_features` say; the size axis still
  vetoes, because the compare uses it as `variant`, 1.8); `identity_coherence(categories)` False ->
  `category_conflict`; else None.
- `gate_refusal_body(result, reason) -> Dict`: keys IN THIS ORDER `success` False, `error`
  GATE_REFUSAL_MESSAGE, `code` GATE_CODE, `elapsed_seconds` (metadata `elapsed_seconds` when `_finite` and
  >= 0 else 0.0), `total_cost` (same rule), `api_calls` (an int >= 0, not bool, else 0), `reason`. The prefix
  equals the H6 dict key order (scs `:4516-4521`); `reason` is last (additive).
- `result_gate_refusal(result, *, url_mode=False) -> Optional[Dict]`: FIRST statement `if not
  result_gate_enabled(): return None`; then None unless a dict with `success is True`; `reason =
  url_gate_reason(result)` when `url_mode` else `gate_reason(result,
  product_categories=stamped_product_categories(result))`, both called through the module globals (so a
  recorder patched on the module sees them), inside `try/except Exception` -> None (deliver as OFF; no log
  line here, P11); None -> None; else `gate_refusal_body(result, reason)`.
- `gate_log_message(reason) -> str`: `GATE_LOG_PREFIX + reason` when `reason in GATE_REASONS +
  CAMERA_GATE_REASONS` (tuple membership, an unhashable value cannot raise), else `GATE_LOG_PREFIX +
  "unknown"`.
- The module docstring line "nothing that reads a flag except ..." gains `result_gate_enabled` and
  `result_gate_refusal` (P11 substrings forbidden in the wording).

`camera_placeholder_sides` of the session-80 spec is NOT added (R-S20-6: no row uses it).

### 2.3 The builder stamp (`app/services/response_builder.py`; additive; after the B1 block `:2326`, before the D08 comment `:2328`)

```python
    # S81-20 (ENABLE_RESULT_GATE; default OFF, read per call -- the FIRST operand, so OFF
    # reads nothing more): the route-level gate re-assesses this body with the stamped
    # categories, so the per-product pair is on the body even with ENABLE_RESULT_STATUS_METADATA
    # OFF (no flip order leaves category_conflict inert). setdefault: under B1 the same
    # value is already there. Additive key only; the crown never moves here.
    if result_gate_enabled() and isinstance(product_categories, list) and len(product_categories) == 2:
        result["metadata"].setdefault(
            "product_categories", [c if isinstance(c, str) else None for c in product_categories])
```
Import at `:21`: `result_gate_enabled` joins the existing line. Nothing else in the builder changes.

### 2.4 Text POST and GET (`app/api/text_routes.py`)

- Import (after `:51`): `from app.services.result_gate import GATE_CODE, GATE_REASONS, gate_log_message,
  result_gate_enabled, result_gate_refusal`.
- Keys (R-S20-22): POST `usage_consumed_keys = None` after `:640`; `usage_consumed_keys =
  usage_check.get("consumed_keys")` after `:656` (the dict exactly as returned, never rebuilt). GET the same
  after `:868` / `:884`.
- One module helper after `_surface_comparison_failure` (`:587`):

```python
def _result_gate_exit(refusal, *, query, input_type, user_id, usage_consumed,
                      consumed_keys, duration_ms, syn, where):
    """S81-20 (ENABLE_RESULT_GATE): the abstain exit (R-A3). Refund FIRST with the
    consume's keys (the M13-37 lesson), then ONE failure row in both W4-13 states,
    then ONE INFO line, then the 400 through the shared mapping, which raises.
    Never a save, never a lifetime bump, never a KB write."""
    if usage_consumed and user_id:
        fire_and_forget(refund_comparison_credit(user_id, consumed_keys),
                        label=f"usage_refund.{where}.result_gate")
    fire_and_forget(
        log_search(query=query, input_type=input_type, user_id=user_id, success=False,
                   error_message=gate_log_message(refusal.get("reason")),
                   cost=_failure_log_cost(refusal), duration_ms=duration_ms, **syn),
        label=f"log_search.{where}.result_gate",
    )
    logger.info("[RESULT_GATE] refused input=%s reason=%s", input_type, refusal.get("reason"))
    _surface_comparison_failure(refusal)
```
- Call sites: POST after `:726` (`where="text.post"`, `query=body.query`), GET after `:944`
  (`where="text.get"`, `query=q`):

```python
    # S81-20: the flag is read inside, FIRST; None OFF or on a supported / failed body.
    _refusal = result_gate_refusal(result)
    if _refusal is not None:
        _result_gate_exit(_refusal, query=<body.query | q>, input_type="text",
                          user_id=user.get("id") if user else None,
                          usage_consumed=usage_consumed, consumed_keys=usage_consumed_keys,
                          duration_ms=duration_ms, syn=_syn, where="text.post")
```
  The helper always raises (400); the echo, save, lifetime and B1 lines below are unreachable for a refusal.
  An anonymous caller (no consume): no refund, one row (`user_id` None).

### 2.5 The stream (`text_compare_stream`; R-S20-21 re-derived on the 6869a3e6 chain)

- Keys: `usage_consumed_keys = None` after `:1067`, set after `:1083` (closure-captured).
- `event_generator` local `_s20_refusal = None` beside the locals `:1114-1124`.
- At the top of `if event_type in ("complete", "settle_complete"):` (`:1172`), BEFORE the latch `:1173`:

```python
                    # S81-20: the FIRST terminal decides; the duplicate terminal reuses it, so both
                    # frames carry the same refusal object.
                    if _s20_refusal is None and complete_response is None:
                        _s20_refusal = result_gate_refusal(data)
                    if _s20_refusal is not None:
                        data = _s20_refusal
```
- The W3-2 persist condition `:1199-1202` gains `and _s20_refusal is None` as its LAST operand (a refusal is
  never persisted and carries no `comparison_id`; OFF `_s20_refusal` is always None).
- The `finally` chain gains a FIRST branch; the existing `if` at `:1275` becomes `elif` (its text
  otherwise unchanged; every following line byte-identical):

```python
            if (_s20_refusal is not None and complete_response is _s20_refusal
                    and not had_error and not complete_after_client_gone):
                # S81-20 (R-A3): refund with the consume's keys, ONE failure row (both W4-13
                # states); no save, no lifetime, no B1 message.
                if usage_consumed and user_id:
                    fire_and_forget(refund_comparison_credit(user_id, usage_consumed_keys),
                                    label="usage_refund.text_stream.result_gate")
                fire_and_forget(log_search(query=q, input_type="text_stream", user_id=user_id,
                                           success=False,
                                           error_message=gate_log_message(_s20_refusal.get("reason")),
                                           cost=_failure_log_cost(_s20_refusal),
                                           duration_ms=duration_ms, **_syn),
                                label="log_search.text_stream.result_gate")
                logger.info("[RESULT_GATE] refused input=%s reason=%s", "text_stream",
                            _s20_refusal.get("reason"))
            elif complete_response and not had_error and not complete_after_client_gone:
                ...   # unchanged
```
  A client that left before the refusal terminal (`complete_after_client_gone` True) takes the existing
  `else` (keyless incomplete refund, which refunds a quota-path debit through the S81-09 stash; the T5 row):
  the base behaviour for a non-delivery (L21). `had_error` with a refusal takes the existing `elif had_error`.
  Wire shape of both terminal frames: `{"success": false, "error": GATE_REFUSAL_MESSAGE, "code":
  "INSUFFICIENT_DATA", "elapsed_seconds", "total_cost", "api_calls", "reason"}`.

### 2.6 The camera (`app/api/image_routes.py`; before ANY paid compare call)

- Imports: `from app.services.result_gate import CAMERA_GATE_MESSAGE, camera_gate_reason,
  gate_log_message, result_gate_enabled` (extending the `:25` line); `from app.services.extraction_service
  import canonicalize_category, classify_category_from_text` (P11 forbids them inside result_gate; the RED
  agent measures that image_routes importing extraction_service adds no import cycle at app.main import).
- `usage_consumed_keys = None` beside `:293`; `usage_consumed_keys = usage_check.get("consumed_keys")`
  after `:361`.
- `_refund_reserved_credit(label, consumed_keys=None)`: when `consumed_keys is None` the body is byte-equal
  to base (`refund_comparison_credit(usage_user_id)`); else `refund_comparison_credit(usage_user_id,
  consumed_keys)`. Same latch. Every existing call keeps its one-argument form.
- Module helper `_camera_gate_categories(p0, p1) -> list` (R-S20-17): per side, the V2 `_category` when it is
  a str in the nine canonical keys, else `classify_category_from_text(f"{brand} {name}".strip())` with the
  orchestrator's defaults `brand "Unknown"`, `name "Unknown Product"` over the POST-enrichment dict (the
  exact stub scs `:4351-4357` computes, so B1's camera stamp sees the same categories when V2 is OFF).
- The snapshot (R-S20-2), inserted after `vision_cost = ...` `:477`, before the enrichment loop `:479`:

```python
    # S81-20 (ENABLE_RESULT_GATE, ONE read per request, before the size enrichment below
    # rewrites the names in place): the vision identities the placeholder rule reads.
    _rg_on = result_gate_enabled()
    _rg_identities = ([(p.get("brand"), p.get("name")) if isinstance(p, dict) else (None, None)
                       for p in products[:2]] if _rg_on else None)
```
- The gate block, inserted after `_syn = ...` `:545`, before `try:` `:546` (after the S81-10 pair gate
  `:532-540`, so a CATEGORY_NOT_LIVE refusal wins and is counted on ITS budget; before the V2 preferences
  read and every paid call):

```python
    # S81-20 (R-A6, R-S20-6): the camera refusal is decided BEFORE the paid compare and is
    # always the action 'error' body (build 3: vision_failed); never comparison_failed.
    if _rg_on:
        _s20 = camera_gate_reason(p1, p2, categories=_camera_gate_categories(p1, p2),
                                  identities=_rg_identities)
        if _s20 is not None:
            _refund_reserved_credit("usage_refund.image.result_gate", consumed_keys=usage_consumed_keys)
            _refund_anon_credit("usage_refund.image.anon.result_gate")
            fire_and_forget(
                log_search(query=query, input_type="camera",
                           user_id=user.get("id") if user else None,
                           products_found=product_names, success=False,
                           error_message=gate_log_message(_s20),
                           cost=round(_log_cost_value(vision_cost) or 0.0, 6),
                           duration_ms=int((time.time() - start_time) * 1000), **_syn),
                label="log_search.camera.result_gate",
            )
            logger.info("[RESULT_GATE] refused input=%s reason=%s", "camera", _s20)
            return {"success": False, "action": "error", "error": CAMERA_GATE_MESSAGE,
                    "vision_cost": vision_cost, "reason": _s20}
```
  No `code` key (build 3's `isCameraEngineOutageResponse` keys on outage codes). Products beyond index 1 are
  not considered (base compares the first two). The zero-product and one-product exits are unchanged.

### 2.7 URL (`app/api/url_routes.py`)

- `_reserve_comparison_credit(user, keys_out=None)` (`:76`); before `return bool(...)` `:108`: `if
  isinstance(keys_out, dict) and isinstance(usage_check.get("consumed_keys"), dict):
  keys_out.update(usage_check["consumed_keys"])`. Call `:274`: `_s20_keys = {}` then `usage_consumed = await
  _reserve_comparison_credit(user, keys_out=_s20_keys)`. (No test patches this helper: `grep -rn
  _reserve_comparison_credit tests` -> no hit.)
- Import: `from app.services.result_gate import gate_log_message, result_gate_refusal`.
- After the failure block `:339`, before `:341`:

```python
    # S81-20 (ENABLE_RESULT_GATE; D4 as amended by R-S20-1 / R-S20-3): a non-delivery like
    # the failure exit above: refund with the consume's keys BEFORE the raise, one row in
    # both W4-13 states, one INFO line, the 400 INSUFFICIENT_DATA + reason.
    _refusal = result_gate_refusal(result, url_mode=True)
    if _refusal is not None:
        if usage_consumed and user_id:
            fire_and_forget(refund_comparison_credit(user_id, _s20_keys or None),
                            label="usage_refund.url.compare.result_gate")
        _url_row("log_search.url.result_gate", success=False,
                 error_message=gate_log_message(_refusal.get("reason")))
        logger.info("[RESULT_GATE] refused input=%s reason=%s", "url", _refusal.get("reason"))
        _surface_comparison_failure(_refusal)
```
  It runs after B4's coded refusals and the S81-10b CATEGORY_NOT_LIVE (both `success:False`, leaving through
  the failure block) on both `url_mode_v2` arms.

### 2.8 `_surface_comparison_failure` and the error envelope

- `text_routes._surface_comparison_failure` coded arm `:566-570` becomes (the S81-10 arm `:560-565` before
  it is untouched):

```python
    if code:
        detail = {"code": code, "error": error_msg}
        # S81-20 (flag read FIRST): an INSUFFICIENT_DATA gate refusal keeps its additive reason.
        if (result_gate_enabled() and code == GATE_CODE
                and result.get("reason") in GATE_REASONS):
            detail["reason"] = result["reason"]
        raise HTTPException(status_code=400, detail=detail)
```
- `error_handler.py`: `_RESULT_GATE_REASONS = ("placeholder_identity", "same_identity",
  "category_conflict", "no_evidence")` (pinned equal to `result_gate.GATE_REASONS`, R81);
  `_result_gate_keys_enabled()` the idiom over `ENABLE_RESULT_GATE` (pinned equal over the R1 table, R81);
  the FOURTH block after the S81-10 block `:231`, before `headers = None` `:232`:

```python
    # S81-20 (flag read FIRST, so OFF reads nothing more of the detail): an
    # INSUFFICIENT_DATA gate refusal keeps its additive `reason` (one of four).
    if (_result_gate_keys_enabled() and _is_structured_detail(detail)
            and detail.get("code") == "INSUFFICIENT_DATA"
            and detail.get("reason") in _RESULT_GATE_REASONS):
        content["reason"] = detail["reason"]
```
  Wire body of a text / URL refusal: `{"success": false, "error": "...", "code": "INSUFFICIENT_DATA",
  "request_id": "<uuid>", "reason": "<one of four>"}`, HTTP 400. Never a 503, never a new code.

### 2.9 New keys and types (all additive; contract freeze section 0 items 2-4 hold)

| Surface | Key | Type / values | When |
|---|---|---|---|
| text / URL 400 envelope | `reason` | str in GATE_REASONS | flag ON, gate refusal only |
| stream terminal frames | `reason` (+ the H6 keys) | str in GATE_REASONS | flag ON, gate refusal only |
| camera `action:'error'` body | `reason` | str in CAMERA_GATE_REASONS | flag ON, camera refusal only |
| delivered text / stream / camera body | `metadata.product_categories` | list of two (str or None) | flag ON (or B1 ON, as today) and the caller passed a 2-list |
| search_logs row | `error_message` | `result_gate:<reason>` | every refusal, both W4-13 states |

Build 3 (PLAN_S80 section 0; session-80 spec 1.7, re-checked by the session-80 review CR7): `parseApiError`
reads `code` / `error` / `detail` / `retry_after_seconds` only; INSUFFICIENT_DATA -> "Thin data on that
pair"; the camera routes by `action` (`error` -> vision_failed). No key removed, renamed or retyped.

### 2.10 Logging

One INFO line per refusal, `[RESULT_GATE] refused input=%s reason=%s` (input in {text, text_stream, camera,
url}; reason a closed-set constant): never a query, a name, a URL, an id or a kb_hit mark (R-S20-19).
Nothing at ERROR. No new line under OFF. The builder stamp logs nothing.

### 2.11 Test seams (production values in brackets)

`result_gate.gate_reason`, `url_gate_reason`, `camera_gate_reason` (module globals; recorders patch them);
`text_routes.get_comparison_service` [per-request service]; `image_routes.identify_products`,
`image_routes.StructuredComparisonService`, `image_routes.log_search`,
`image_routes.save_comparison_and_track_cohort`; `url_routes.compare_from_urls` /
`url_routes._compare_with_deadline`; the `tests.test_retro_w2_1.Ledger` recorders (consume, refund WITH
`consumed_keys`, lifetime, history, log rows, labels); the S81-09 FakeRedis / Lua recorder
(`tests/test_s81_s09_device_quota.py` `_install_redis` `:442`); `kb_ingest.build_job` / `kb_ingest.run_job`
recorders; `category_gate.record_refusal_async` recorder; the `fire_and_forget` label recorder; caplog.
Companions: [PROD ON] ENABLE_PAID_ROUTE_METERING, ENABLE_CAMERA_FAILURE_ENVELOPE, ENABLE_COMPARE_AUTH_REQUIRED
(with an `authed` override); [OFF in prod, set per row explicitly] ENABLE_RESULT_STATUS_METADATA,
ENABLE_VISION_IDENTITY_V2, ENABLE_URL_MODE_V2, ENABLE_FRAGRANCE_ONLY_GATE, ENABLE_DEVICE_DAILY_QUOTA,
ENABLE_KB_INGEST, ENABLE_FIELD_STATUS_METADATA, ENABLE_KB_FIRST_SERVE; [UNKNOWN, param both]
ENABLE_SEARCH_LOG_TRUTH, ENABLE_COMPARISON_ID_ECHO, ENABLE_ANON_USAGE_GATE.

### 2.12 Flag-OFF identity (the unit's main invariant)

With `ENABLE_RESULT_GATE` unset / blank / `false` / `0` / `off` / `no` / garbage, under the FULL companion
configuration (metering, envelope, auth required + authed, B1 ON, V2 ON, echo ON, URL_MODE_V2 ON, the device
quota ON, KB_INGEST + FIELD_STATUS ON, W4-13 flag 1 in both states): every response body and status, SSE
frame, `search_logs` kwarg set, fire_and_forget label sequence, refund call (arguments), save and lifetime
call, and every `kb_ingest` call is byte-identical to base; `gate_reason`, `url_gate_reason` and
`camera_gate_reason` are called ZERO times; the builder writes `metadata.product_categories` only under B1;
the error envelope never carries `reason`; the camera names are enriched exactly as base. Pinned by P1-P9
(5.1), the unedited 4.2 files (incl. the FY25 nine digests and the W4-13 flag-OFF ledger) and the comm set.

### 2.13 Failure table (flag ON)

| Situation | Behaviour |
|---|---|
| text / URL / stream body supported | delivered exactly as OFF, plus `metadata.product_categories` on text / stream / camera bodies |
| placeholder product (text / stream) | 400 / terminal INSUFFICIENT_DATA reason placeholder_identity; keyed refund; one row; no save; no lifetime |
| same identity | reason same_identity (URL included, R-S20-3) |
| per-product categories canonical, not other, different (or `category_used` not canonical) | reason category_conflict (not URL) |
| AUDITABLE coverage 0 (incl. a hard-cap partial with coverage 0) | reason no_evidence |
| a `success:False` result (H6, TIMEOUT, LLM_UNAVAILABLE, CONTENT_UNAVAILABLE, CATEGORY_NOT_LIVE, B4 codes, parser) | untouched (its own exit, before the gate) |
| `assess_result` / `url_gate_reason` raising (defensive) | `result_gate_refusal` returns None: delivered as OFF |
| camera: a placeholder on either side (pre-enrichment identity), any V2 low, same identity (features ignored, size veto kept), category conflict | `action:'error'` + reason; both refunds (reserved keyed, anon keyed); one row; no compare call |
| camera: a V1 product with confidence low | not refused on confidence (R-S20-5); the other rules apply |
| camera after the compare | as OFF (D5, L1) |
| URL: placeholder / same identity / URL coverage 0 | 400 INSUFFICIENT_DATA + reason; keyed refund; one row |
| stream: client gone before the refusal terminal | the existing incomplete arm (keyless refund, T5 row) |
| ENABLE_FRAGRANCE_ONLY_GATE ON | its pre-consume / post-resolve refusals run first and are counted on its budget; a result-gate refusal never calls `record_refusal_async` |
| mid-request flip | each read is per call: a refusal built ON and surfaced OFF loses `reason` on the wire (still INSUFFICIENT_DATA, still refunded by the S81-20 exit, which does not re-read); a body built OFF and gated ON lacks `product_categories` (category_conflict cannot fire for that request); the camera reads once (`_rg_on`) |

### 2.14 Delivered partials

R-A4: a partial (hard-cap) result may crown only if coverage >= 1: a partial with AUDITABLE coverage >= 1 and
a resolved, distinct, coherent pair is delivered and billed as today; a partial with coverage 0 or an
identity reason is refused like any other body (and queues no gap: 1.7, Q1).

---------------------------------------------------------------------------------------------------

## 3. Change list, in the order GREEN applies it

0. Byte copies (shutil.copyfile, sha256 recorded) of every file below into the GREEN notes folder; the
   mutation-lock rules apply.
1. `app/services/result_gate.py`: append the 2.2 constants and functions; the docstring line. ASCII,
   P11-clean.
2. `app/services/response_builder.py`: `result_gate_enabled` on the `:21` import; the 2.3 block.
3. `app/middleware/error_handler.py`: `_RESULT_GATE_REASONS`; `_result_gate_keys_enabled()`; the 2.8 block
   (fourth, after `:231`).
4. `app/api/text_routes.py`: the import; the coded arm of `_surface_comparison_failure`; the
   `_result_gate_exit` helper; POST keys + call; GET keys + call; stream keys, `_s20_refusal`, the terminal
   intercept, the persist operand, the `finally` first branch + `if` -> `elif`.
5. `app/api/image_routes.py`: the imports; `usage_consumed_keys`; `_refund_reserved_credit(label,
   consumed_keys=None)`; `_camera_gate_categories`; the snapshot; the 2.6 block.
6. `app/api/url_routes.py`: the import; `_reserve_comparison_credit(user, keys_out=None)`; the call; the
   2.7 block.
7. Tests: `tests/test_s81_s20_result_gate.py` (the RED file, frozen at the gate; GREEN adds nothing to it);
   the E-rows of 4.1 (one-name edits of env-clean lists).
8. `CLAUDE.md`: the section 8 block after the S81-G5 block (`:572-575`), before `## Tests` (`:576`), and the
   `:341` Feature Flags pointer clause gains one sentence (8.1). The DEFECT_LEDGER rows and the session ledger
   are the orchestrator's.
No other file. (`structured_comparison_service.py`, `kb_ingest.py`, `url_extraction_service.py`,
`openai_service.py`, `sentry_service.py`, `usage_service.py`, `category_gate.py`, every migration, every
client file, every requirements file: NOT edited.)

---------------------------------------------------------------------------------------------------

## 4. Existing pins

### 4.1 Pins that change deliberately (one row each; test-only one-name edits; no assertion changes)

| # | File:line | Edit | Reason |
|---|---|---|---|
| E1 | `tests/test_s75_fanout_identity.py:60-70` `UNIT_ENV` | add `"ENABLE_RESULT_GATE"` | the S81-20 stamp adds `metadata.product_categories` under the flag; a developer `.env` must not move the nine digests (the B1 E1 precedent) |
| E2 | `tests/test_retro_w2_1.py:173-179` `_clean_flags` | add `"ENABLE_RESULT_GATE"` | its URL / text stub bodies are thin (no price, rating or spec): with the flag exported they are refused no_evidence |
| E3 | `tests/test_s71_u13_compare_auth_required.py:76-89` `CLEAN_ENV` | add `"ENABLE_RESULT_GATE"` | the recorded flag-OFF responses include delivered compares |
| E4 | `tests/test_paid_route_metering.py:244` `_CLEAN_ENV` | add `"ENABLE_RESULT_GATE"` (unconditional: B4 merged) | stub bodies thin (`_stub_camera` B<i>/N<i> passes the camera gate, the URL / text stubs do not) |
| E5 | `tests/test_w4_13_measurement_truth.py:154-160` `_clean_flags` | add `"ENABLE_RESULT_GATE"` | guards this file AND the W4-13 flag-OFF ledger generator that imports it (C2 / PC1) |
| E6 | `tests/test_s80_b1.py:52-61` `CLEAR` | add `"ENABLE_RESULT_GATE"` | B1 drives V09-like bodies through the routes (PC9) |
| E7 | `tests/test_s80_b3_vision_identity_v2.py:79-92` `UNIT_ENV` | add `"ENABLE_RESULT_GATE"` | camera rows with identical or low pairs (PC9) |
| E8+ | candidates, decided by the 7.4 local-.env sweep: `tests/test_s81_s03_llm_ledger_v2.py:102` `UNIT_ENV`; `tests/test_s81_s06_anthropic_router.py` (its inline delenv loop `:338-341`); `tests/test_s81_s09_device_quota.py:97` `CLEAN_ENV`; `tests/test_s81_s10_fragrance_gate.py:500` `_CLEAR_ENV`; `tests/test_s81_s10_gate_rows.py` (its delenv lines `:252` / `:288`); `tests/test_s81_s10b_links_gate.py` (no list: a new delenv line in its autouse fixture); `tests/test_s81_s18_kb_first_serve.py:82` `CLEARED_ENV` | add `"ENABLE_RESULT_GATE"` only to each file that goes red with the flag exported | each drives text / camera / URL routes with stub bodies (route-driving counts measured by grep: s03 5, s06 9, s09 7, s10 4, s10_gate_rows 1, s10b 2, s18 5); no route file has gone red at base because no code reads the flag yet, so the sweep runs at GREEN; a red file without a list is named in the CLAUDE.md row instead |

GREEN proves each E-row file green with AND without the flag exported for that one runner call (the B4 F4-3
/ E6 precedent). Each edited test module's importers join the comm set (7.6).

### 4.2 Pins that must stay green and unedited (all green at base, 1.10)

`tests/test_text_routes_error_mapping.py`, `tests/test_http_400_cap_cut_mapping.py`,
`tests/test_text_error_envelope_no_raw_exception.py`, `tests/test_m13_37_freemium_atomic_consume.py`,
`tests/test_m18_usage_symmetry.py`, `tests/test_m13_26_image_error_envelope.py`,
`tests/test_image_identify_llm_unavailable_s69.py`, `tests/test_error_middleware.py`,
`tests/test_429_contract.py`, `tests/test_w4_13_flag_off_ledger.py`, `tests/test_comparison_id_echo.py`,
`tests/test_streaming.py`, `tests/test_s78_tier_fill_residual_guard.py`,
`tests/test_s78_all_timeout_cap_as_timeout.py`, `tests/test_auth_error_log_hygiene.py`,
`tests/test_events_allowlist_superset.py`, `tests/test_sentry_channels_u8d_unit.py`,
`tests/test_sentry_channels_u8d.py`, `tests/test_s71_u13_pins.py`, `tests/test_global_anti_patterns.py`,
`tests/test_camera_vision.py`, `tests/test_m18_preverdict_disconnect_refund.py`,
`tests/test_s80_url_mode_v2.py`, `tests/test_s81_s09_device_quota.py`, `tests/test_s81_s10_fragrance_gate.py`
(the r06 node environmental), `tests/test_s81_s10_gate_rows.py`, `tests/test_s81_s10b_links_gate.py`,
`tests/test_s81_s17_kb_ingest.py`, `tests/test_s81_s18_kb_first_serve.py`, `tests/test_s81_g3_gate_rows.py`,
`tests/test_s81_g4_gate_rows.py`, `tests/test_s81_s03_llm_ledger_v2.py`, `tests/test_s81_s06_anthropic_router.py`,
`tests/test_history_routes.py`, `tests/test_home_routes.py`, `tests/test_shutdown_drain.py`,
`tests/test_m13_04_full_stream_deadline.py`, the CLAUDE.md readers (`tests/test_ci_gates.py`,
`tests/test_behavior_dimension_translation.py`, `tests/test_s81_s04_spend_breaker.py`,
`tests/test_s81_s08b_legacy_fingerprint.py`, `tests/test_s81_s08b_gate_rows.py`,
`tests/test_s81_s23_bypass_retire.py`), and the E-row files apart from their one-name edit.

---------------------------------------------------------------------------------------------------

## 5. RED tests

### 5.1 `tests/test_s81_s20_result_gate.py` (new; pure ASCII, LF; hermetic)

Harness: an autouse fixture imports `app.main` FIRST (the dotenv guard), then `monkeypatch.setenv` /
`delenv`. Reuses (by import, never edited): `tests.test_s75_fanout_identity as fy` (`_Patcher`,
`_new_state`, `_install`, `_scenario`, `QUERY`) through the B1 `fy_text` pattern (`tests/test_s80_b1.py:270`),
`tests.test_retro_w2_1` (`Ledger` `:220`, `_install` `:283`, its camera stub pattern with an added compare-call
counter), `tests.test_s81_s09_device_quota._install_redis` (`:442`, the Lua recorder) and the lane1 fixtures,
`tests/fixtures/w412_corpus_min.json`, the four real URL fixtures (1.9) through the REAL
`url_extraction_service` extract + `normalize_product_data` (no network: the HTML is read from disk and the
fetch is stubbed), and the tester shapes of eval_regression T01 / T03 / T04 / T05. Missing symbols are read
with `getattr(rg, name, None)` + `assert callable(...)` (or `assert x is not None`) so every RED fails on an
AssertionError at base. Every ON route row sets the PROD companions explicitly (metering ON, envelope ON,
auth required ON with an `authed` override) unless the row says otherwise; every OFF PIN row sets the FULL
configuration of 2.12 plus the three decision recorders. ENABLE_FRAGRANCE_ONLY_GATE is OFF in every row that
uses a non-fragrance pair and says so; the rows that need it ON (R31, R60) use a fragrance pair.

Fixtures (built at run time): BODY_SUP = lane1 `tomford_vs_creed_response.json` (coverage 4, measured);
BODY_V09 = BODY_SUP with both products `brand ""`, `name "Unknown Product"` (+ overview mirror); BODY_V07 =
BODY_SUP with `GUESS` / `GUESS!` (brand GUESS both); BODY_V10 = BODY_SUP with both prices `{amount None,
unavailable True}`, `rating None`, `rating_derived True`, product and `specs.products[i]` specs `{}`,
`scoring_v2.dimensions []` (measured: `partial_no_winner`, [no_evidence], coverage 0, identity medium);
BODY_V10_ONE = the same with p0's price and p1's rating kept (identity high); BODY_CAT = BODY_SUP with
`metadata.product_categories ["electronics", "fragrances"]`; URL_V09 / URL_SAME / URL_NOEV / URL_V03 (the
synthetic numeric envelope) and URL_REAL_BH (bheshop + godukkan) / URL_REAL_AE (lulu + samawa) built from the
fixtures; VISION_V07 = V1 dicts GUESS / GUESS! `medium`; VISION_V04 = V2 dicts (`_is_product` True) Sefiki /
Violin `low` x2; VISION_LOW1 = (V2 high, V2 `"LOW "`); VISION_V1_LOW = V1 dicts, distinct, `low` x2 (no
marker); VISION_PH0 = (`Unknown` / `Unknown Product` medium) + (`Lattafa` / `Asad` high); VISION_PH1 = the
mirror; VISION_ENRICH = (`Unknown` / `Unknown Product`, `size_or_count "100ml"`, medium) + a real high side;
VISION_ENRICH_BRAND = (`Lattafa` / `Unknown Product`, `size_or_count "100 ml"`, medium) + a real high side;
VISION_CAT_V2 = V2 dicts `_category` electronics / fragrances; VISION_CAT_V1 = "Samsung" / "Galaxy S24
phone" + "Dior" / "Sauvage eau de parfum" (no `_category`); VISION_FEAT = V2 GUESS / GUESS! with
`_distinguishing_features` [polyurethane] / [cotton]; VISION_SIZES = two V1 dicts `Dior` / `Sauvage` with
`size_or_count` "60ml" / "100ml"; FY_V10 = the fy_text explicit pair ("Hyper X MIC", "Hyper X2 MIC") with the
T04 leaves (price None, rating None, specs `{}` and the all-dash dict, reviews `{}`); FY_V10_FRAG = the same
leaves on a fragrance explicit pair (the RED agent measures a pair whose resolved category is `fragrances`
through the stub, e.g. two Lattafa names, and records it); CONFLICT_PAIR = `tests/test_s80_b1.py:1230`.

| # | test | assertion | at base | satisfied by |
|---|---|---|---|---|
| R1 | `test_r01_flag_reader_table` (param unset, "", false, 0, off, no, garbage, " TRUE ", true, 1, yes, On) | `rg.result_gate_enabled()` equals the idiom | AssertionError (absent) | 2.2 |
| R2 | `test_r02_constants` | GATE_REASONS, CAMERA_GATE_REASONS, GATE_CODE, GATE_LOG_PREFIX exact; GATE_REFUSAL_MESSAGE == the H6 literal (built with chr(0x2014), and equal to the `error` string the real H6 exit returns through fy); CAMERA_GATE_MESSAGE exact | absent | 2.2 |
| R3 | `test_r03_gate_reason_lane1_supported` (9 files) | `gate_reason(body) is None` | absent | 2.2 |
| R4 | `test_r04_v09_placeholder` | BODY_V09 -> placeholder_identity | absent | 2.2 |
| R5 | `test_r05_same_identity` | BODY_V07 -> same_identity; GUESS Logo Tee vs GUESS Denim Shirt -> None | absent | 2.2 |
| R6 | `test_r06_category` | BODY_SUP + [electronics, fragrances] -> category_conflict; [other, fragrances] -> None; `category_used "toys"` -> category_conflict | absent | 2.2 (kills M24) |
| R7 | `test_r07_corpus` | w412 rows 12, 13, 14 (success True) -> no_evidence; rows 24, 26 (partials) -> None; row 6 -> placeholder_identity (the RED agent re-measures each at 6869a3e6 through the real assess_result and keeps a row only where the measured status matches) | absent | 2.2, 2.14 |
| R8 | `test_r08_mapping_completeness` (36 + the synthetic bodies) | `(gate_reason(b, product_categories=c) is None) == (assess_result(b, product_categories=c)["status"] == "supported_result")` | absent | 2.2 (C10) |
| R9 | `test_r09_totality` | success False / non-dict / products missing -> None (gate_reason, url_gate_reason, camera_gate_reason(non-dict sides) -> placeholder_identity) | absent | 2.2 |
| R10 | `test_r10_url_gate_synthetic` | URL_V09 -> placeholder_identity; URL_SAME -> same_identity; URL_NOEV -> no_evidence; URL_V03 (numeric prices, no specs) -> None | absent | 2.2 |
| R11 | `test_r11_url_string_reading` (R-S20-1) | URL_REAL_BH and URL_REAL_AE -> None; a str price "0", "abc", "1e400", "1" * 400, "-5", "nan", True -> not counted (one-sided pairs -> no_evidence); rating "5" counted, "6" and "0" not | absent | 2.2 (kills M16, M38) |
| R12 | `test_r12_url_one_sided` | price on p0 only, no rating, no spec -> no_evidence (S5); a placeholder on side 1 only -> placeholder_identity (S6) | absent | 2.2 (kills M17, M18) |
| R13 | `test_r13_camera_gate_table` | VISION_V07 -> same_identity; VISION_V04 -> low_confidence; VISION_LOW1 -> low_confidence (side 1, "LOW "); VISION_V1_LOW -> None; VISION_PH0 / VISION_PH1 -> placeholder_identity (S1); categories [electronics, fragrances] -> category_conflict; a distinct high pair with [other, other] -> None | absent | 2.2 (kills M11, M12, M25, M28, M29) |
| R14 | `test_r14_camera_snapshot` (R-S20-2) | the enriched dicts (`name "Unknown Product 100ml"`) with `identities` = the pre-enrichment pair -> placeholder_identity; VISION_ENRICH_BRAND -> placeholder_identity; without `identities` the enriched VISION_ENRICH reads not-placeholder (documents BL2) | absent | 2.2 (kills M13) |
| R15 | `test_r15_camera_features_ignored` (R-S20-4) | VISION_FEAT -> same_identity; VISION_SIZES -> None (the size veto stands) | absent | 2.2 (kills M33) |
| R16 | `test_r16_refusal_body_shape` | `list(gate_refusal_body(BODY_SUP, "no_evidence"))` == [success, error, code, elapsed_seconds, total_cost, api_calls, reason]; values from metadata; inf / nan / bool / negative -> 0 | absent | 2.2 |
| R17 | `test_r17_refusal_flag_first` (OFF / ON) | OFF: `result_gate_refusal(BODY_V09)` None and the recorders on `gate_reason` / `url_gate_reason` saw 0 calls; ON: one call; a body with reason placeholder_identity; `url_mode=True` routes to `url_gate_reason` | absent | 2.2 (kills M1) |
| R18 | `test_r18_log_message` | "no_evidence" -> "result_gate:no_evidence"; "low_confidence" -> "result_gate:low_confidence" (S4); "x", [] -> "result_gate:unknown" | absent | 2.2 |
| R20 | `test_r20_text_post_v09_refused` (W4-13 flag 1 param both) | service returns BODY_V09: 400; json code INSUFFICIENT_DATA, reason placeholder_identity, keys == {success, error, code, request_id, reason}; ledger refunds == [uid] with refund keys IDENTICAL (`is`-equal by value) to the consumed_keys the consume stub returned; history == []; lifetime == []; exactly one log row success False error "result_gate:placeholder_identity" cost == metadata.total_cost; the refund label precedes the log label | 200 delivered | 2.4, 2.8 (kills M2, M4, M5, M9, M10) |
| R21 | `test_r21_text_get_v07_refused` | GET BODY_V07: 400 reason same_identity; the R20 ledger shape | 200 | 2.4 |
| R22 | `test_r22_text_post_v10_no_evidence` | BODY_V10: 400 reason no_evidence; ledger shape | 200 | 2.4 |
| R23 | `test_r23_real_orchestrator_v10` (R-S20-9, mandatory) | fy_text with FY_V10, B2 ON, B1 OFF, FRAGRANCE gate OFF (an electronics pair): 400 reason no_evidence + the ledger shape | 200 | 2.2, 2.4 |
| R24 | `test_r24_real_orchestrator_v10_both_flags` | FY_V10 with B1 ON + B2 ON: 400 no_evidence AND a builder-output recorder shows the B1 stamp `partial_no_winner` on the same body (D1) | 200 | D1 |
| R25 | `test_r25_category_conflict_b2_alone` | B1 OFF, B2 ON, fy_text CONFLICT_PAIR: 400 reason category_conflict | 200 | 2.3 (kills M14) |
| R26 | `test_r26_category_conflict_both_flags` | B1 ON + B2 ON, CONFLICT_PAIR: 400 category_conflict | 200 | D1 |
| R27 | `test_r27_supported_real_orchestrator_stamp` | B2 ON, B1 OFF, the FY25 default pair: 200; `metadata.product_categories` == [electronics, electronics]; refunds []; history 1; lifetime 1 | stamp absent | 2.3 (kills M8) |
| R28 | `test_r28_anonymous_text_refusal` (R-S20-11: ENABLE_COMPARE_AUTH_REQUIRED OFF explicitly) | no user, BODY_V09: 400; refunds == []; one log row with user_id None | 200 | 2.4 |
| R29 | `test_r29_hard_cap_partials` | fy `_scenario` REST cap 0.5 slow, coverage 1 partial: 200 `metadata.partial` True; a coverage-0 partial (BODY_V10 marked partial) -> 400 no_evidence | the second half 200 | 2.14 |
| R30 | `test_r30_device_quota_keys` (R-S20-22) | ENABLE_DEVICE_DAILY_QUOTA ON with the S81-09 FakeRedis / Lua recorder and a valid synthetic fingerprint, BODY_V10 on POST: the refund passes `{"daily", "device_daily"}` exactly as consumed; ONE DEVICE_REFUND_SCRIPT EVAL over exactly those keys; no second refund; lifetime 0; history 0 | 200, no refund | 2.4 (kills M9) |
| R31 | `test_r31_fragrance_gate_budget_untouched` | ENABLE_FRAGRANCE_ONLY_GATE ON, FY_V10_FRAG via POST: 400 INSUFFICIENT_DATA reason no_evidence (not CATEGORY_NOT_LIVE); `category_gate.record_refusal_async` recorder 0 calls | 200 | 2.4 (kills M37) |
| R32 | `test_r32_text_info_line` (caplog) | exactly one INFO record with msg `[RESULT_GATE] refused input=%s reason=%s` and args ("text", "placeholder_identity"); no record carries the query text; nothing at ERROR | absent | 2.10 (kills M32) |
| R33 | `test_r33_g3_tail_no_evidence` (R-S20-18) | ENABLE_KB_INGEST ON + B2 ON, fy_text FY_V10_FRAG: 400 no_evidence; `kb_ingest.build_job` called exactly once and `kb_ingest.run_job` (recorder) scheduled exactly once with `snap["identity_confidence"] == "medium"` and at least one product `field_status` field in state `unknown`; no other kb_ingest call after the refusal | 200 | D6, 1.7 |
| R34 | `test_r34_g3_tail_identity_classes` (param category_conflict / same identity through fy) | the refusal; `run_job` scheduled once with identity in {low, unresolved} (so no gap row is built) | 200 | D6, 1.7 |
| R40 | `test_r40_stream_refusal_frames_and_accounting` (W4-13 both) | stub stream yields status, verdict, settle_complete(BODY_V09), complete(BODY_V09) (the SAME object): both terminal frames parse to the 2.5 shape with reason placeholder_identity; refunds == [uid] with the consumed keys; history == []; lifetime == []; exactly one log row "result_gate:placeholder_identity"; no `log_search.text_stream.terminal_failure` / `.success` label; one INFO line ("text_stream", ...) | billed (lifetime 1, no refund) | 2.5 (kills M3, M20, M21, M22, M23) |
| R41 | `test_r41_stream_refusal_not_persisted_under_echo` | ENABLE_COMPARISON_ID_ECHO ON: the persist recorder 0 calls; frames carry no `comparison_id` | persist called | 2.5 |
| R50 | `test_r50_camera_same_identity` | VISION_V07, metering + envelope ON, authed: compare calls 0; body == {success False, action "error", error CAMERA_GATE_MESSAGE, vision_cost 0.003, reason "same_identity"}; refunds == [uid] with the consumed keys; history []; lifetime []; one log row "result_gate:same_identity" cost 0.003 | compare called | 2.6 (kills M7, M27, M34) |
| R51 | `test_r51_camera_low_confidence` (param VISION_V04, VISION_LOW1) | reason low_confidence; compare 0; the log row message "result_gate:low_confidence" | compare called | 2.6 (kills M11, M29) |
| R52 | `test_r52_camera_two_placeholders` | both Unknown: action error reason placeholder_identity | compare called | 2.6 |
| R53 | `test_r53_camera_one_placeholder_is_error` (R-S20-6, param VISION_PH0 / VISION_PH1) | action "error" (never need_second_product) reason placeholder_identity; compare 0; one refund | compare called | 2.6 (kills M28, M36) |
| R54 | `test_r54_camera_enrichment_evasion` (R-S20-2, param VISION_ENRICH / VISION_ENRICH_BRAND) | through the real route (the enrichment runs): action error reason placeholder_identity; compare 0 | compare called | 2.6 (kills M13) |
| R55 | `test_r55_camera_category_conflict` (param VISION_CAT_V2 with V2 ON, VISION_CAT_V1) | action error reason category_conflict; compare 0 | compare called | 2.6 |
| R56 | `test_r56_camera_v2_features_same_identity` (R-S20-4; the session-80 P9 turned RED) | VISION_FEAT with V2 ON: action error reason same_identity; compare 0 | compare called | 2.6 (kills M33) |
| R57 | `test_r57_camera_anon_refund_keys` (R-S20-11: auth required OFF explicitly) | ENABLE_ANON_USAGE_GATE ON + metering ON + a synthetic fingerprint header, VISION_V07: anon refunds == [fp] with the anon consumed keys; compare 0 | compare called, no refund | 2.6 |
| R58 | `test_r58_camera_device_quota_keys` | ENABLE_DEVICE_DAILY_QUOTA ON + the Lua recorder, VISION_V07: the reserved refund passes the consumed `{"daily", "device_daily"}`; one refund EVAL | compare called | 2.6 (kills M34) |
| R59 | `test_r59_camera_info_line` (caplog) | one INFO ("camera", "same_identity"); no product name in any record args | absent | 2.10 |
| R60 | `test_r60_camera_fragrance_gate_order` | ENABLE_FRAGRANCE_ONLY_GATE ON, a fragrance VISION_V07-shaped pair (two Lattafa Asad dicts): the S81-10 pair gate passes, the S81-20 refusal fires (same_identity); `record_refusal_async` 0 calls | compare called | 2.6 (kills M37) |
| R70 | `test_r70_url_v09_refused` (W4-13 both; FRAGRANCE gate OFF) | 400 INSUFFICIENT_DATA reason placeholder_identity; refunds == [uid] with the consumed keys (via `keys_out`); history []; lifetime []; one row "result_gate:placeholder_identity" | 200, history, lifetime | 2.7 (kills M26, M35) |
| R71 | `test_r71_url_no_evidence` | URL_NOEV: 400 reason no_evidence | 200 | 2.7 |
| R72 | `test_r72_url_same_identity` (R-S20-3) | URL_SAME (two stores, one juice): 400 reason same_identity | 200 | 2.7 |
| R73 | `test_r73_url_info_line_and_v2_arm` (param url_mode_v2 OFF / ON) | one INFO ("url", ...) per refusal; the refusal fires on both arms | 200 | 2.7 |
| R80 | `test_r80_envelope_passthrough` | flag ON: HTTPException(400, {code INSUFFICIENT_DATA, error, reason "no_evidence"}) through `http_exception_handler` -> body.reason == "no_evidence"; reason "hacked" -> no key; code TIMEOUT (503) with reason -> no key; CATEGORY_NOT_LIVE with reason -> no `reason` key | no key | 2.8 (kills M6, M19) |
| R81 | `test_r81_reader_and_vocab_parity` | `error_handler._result_gate_keys_enabled()` == `rg.result_gate_enabled()` over the R1 table; `error_handler._RESULT_GATE_REASONS == rg.GATE_REASONS` | absent | 2.8 |
| R82 | `test_r82_surface_reason_on` | flag ON: `_surface_comparison_failure({"success": False, "code": "INSUFFICIENT_DATA", "error": "x", "reason": "no_evidence"})` raises detail == {code, error, reason}; reason "hacked" -> {code, error} | detail {code, error} | 2.8 (kills M5) |
| R90 | `test_r90_builder_stamp_b2_alone` | B2 ON, B1 OFF: `build_comparison_response(..., product_categories=["electronics", "fragrances"])` -> `metadata.product_categories` present; `metadata.result_status` absent | absent | 2.3 (kills M14) |

PIN rows (green at base; the FULL configuration of 2.12 and the recorders):

| # | test | assertion |
|---|---|---|
| P1 | `test_p01_off_text_post_v09_delivered` (W4-13 both) | B2 unset, FULL config: 200; body == the base body recorded as a literal at RED time (fields, never request-id substrings); refunds []; history / lifetime / labels as base; gate recorders 0 calls |
| P2 | `test_p02_off_text_get_v07_delivered` | the GET twin |
| P3 | `test_p03_off_stream_v09_billed_as_base` | base billing exactly (lifetime 1, no refund, the W4-13 labels per state); frames byte-equal to base literals |
| P4 | `test_p04_off_camera_v07_and_enrich_as_base` | compare called once; action comparison; camera recorder 0 calls; the enriched names reach the compare exactly as base (VISION_ENRICH -> name "Unknown Product 100ml") |
| P5 | `test_p05_off_url_v09_delivered` | 200, history + lifetime as base; the reserve's consume called once with the base arguments |
| P6 | `test_p06_h6_envelope_four_keys` (OFF and ON) | the H6 INSUFFICIENT_DATA failure: 400, envelope keys exactly {success, error, code, request_id} (ON: no reason on a non-gate failure) |
| P7 | `test_p07_off_handler_drops_reason` | flag OFF: a detail carrying reason "no_evidence" -> no reason key |
| P8 | `test_p08_off_builder_no_categories` (S7) | B1 OFF, B2 OFF: `build_comparison_response(..., product_categories=["electronics", "fragrances"])` -> no `metadata.product_categories` |
| P9 | `test_p09_off_surface_detail_two_keys` (S8) | flag OFF: the INSUFFICIENT_DATA dict carrying reason "no_evidence" raises a detail exactly {code, error} |
| P10 | `test_p10_on_supported_text_delivered` | B2 ON, BODY_SUP: 200, refunds [], history 1, lifetime 1, no result_gate row |
| P11 | `test_p11_on_url_priced_pairs_delivered` (param URL_REAL_BH, URL_REAL_AE, URL_V03; FRAGRANCE gate OFF) | 200 delivered, history 1, lifetime 1 |
| P12 | `test_p12_on_stream_supported_delivered` | base billing; frames carry no reason |
| P13 | `test_p13_on_lane1_all_delivered` (9 files via the text route) | 200 each |
| P14 | `test_p14_on_camera_v1_low_compares` (R-S20-5) | VISION_V1_LOW under ON: compare once, action comparison |
| P15 | `test_p15_on_camera_sizes_compare` | VISION_SIZES under ON: compare once |
| P16 | `test_p16_on_stream_client_gone_before_refusal` | ON, the client disconnects before the first terminal: the existing incomplete arm (keyless refund label `usage_refund.text_stream.incomplete`, the T5 row under W4-13 ON), history 0, no result_gate row |
| P17 | `test_p17_on_camera_single_product_exit_unchanged` | ON, one Unknown product: `need_second_product` as base, one refund |
| P18 | `test_p18_on_category_not_live_keeps_its_envelope` | ON + FRAGRANCE gate ON, the post-resolve CATEGORY_NOT_LIVE 400: its keys as base, no `reason` key, no result_gate row |

RED count: 50 test functions (R1-R18, R20-R34, R40-R41, R50-R60, R70-R73, R80-R82, R90); PIN 18
(P1-P18); parametrisations expand the node count (the RED agent reports nodes).

### 5.2 Satisfiability notes for the RED agent

- R22 / R23 / R29 / R33: assert each synthetic or fy body's base `assess_result` status FIRST in a helper
  row (the shapes in 1.7 were measured; FY_V10 was measured `partial_no_winner` by the session-80 review C3
  at 95cf6f86 and must be re-measured here); keep a row only where the measured status matches.
- R23-R27, R33, R34 reuse the B1 harness (`fy._install` via `text_routes.get_comparison_service`); the KB
  rows patch `kb_ingest.run_job` with a recorder (the tail hands it to `asyncio.to_thread` inside
  fire_and_forget: drain the scheduled tasks before asserting) and set ENABLE_KB_INGEST ON with
  ENABLE_FIELD_STATUS_METADATA OFF (the tail runs build_job under either).
- R30 / R58 reuse the S81-09 FakeRedis (EVAL emulation) and its fingerprint helper; the consume runs the
  real `consume_comparison_credit`; assert on the recorded EVAL key lists, not on counter values only.
- R40: the stub generator yields the SAME dict object for both terminals; parse frames by blank lines and
  the last `data:` line.
- R54: the enrichment must run, so drive the real route with the vision stub returning the un-enriched dicts.
- URL_REAL_*: build the products through the real extract + `normalize_product_data` over the HTML read from
  disk (no fetch); assert the measured string types of 1.9 first.
- P1-P5 record the base bodies / frames as literals at RED time; every P row sets the full configuration and
  asserts the recorders, so a not-gated mutant is killed (ruling B1).

---------------------------------------------------------------------------------------------------

## 6. Mutation table (each mutant on a byte copy, an exact-string edit that matches once, the killing rows via `pyt.py -k`, bound 600, restored and sha256-compared; KILLED = an assertion failure)

| # | Mutant | File | Killing rows |
|---|---|---|---|
| M1 | flag read after the assessment in `result_gate_refusal` | result_gate.py | R17, P1, P2 |
| M2 | text refund moved below `_surface_comparison_failure(refusal)` | text_routes.py | R20, R21, R22 |
| M3 | stream S81-20 branch condition forced False | text_routes.py | R40 |
| M4 | `_result_gate_exit` schedules `save_comparison_and_track_cohort` before raising | text_routes.py | R20 (history []) |
| M5 | the reason arm deleted in `_surface_comparison_failure` | text_routes.py | R20, R21, R82 |
| M6 | the handler block deleted | error_handler.py | R80, R20 |
| M7 | the camera block moved after the compare | image_routes.py | R50-R56 |
| M8 | `gate_reason` returns no_evidence when no reason maps | result_gate.py | R3, P10, P13, R27 |
| M9 | text refund without keys | text_routes.py | R20, R30 |
| M10 | the text log row removed | text_routes.py | R20 |
| M11 | any-low -> both-low | result_gate.py | R13, R51 |
| M12 | the `_is_product` marker check removed (V1 low gated) | result_gate.py | P14, R13 |
| M13 | the snapshot ignored (`identities` not passed / not used) | image_routes.py / result_gate.py | R14, R54 |
| M14 | the builder stamp gated on B1 only | response_builder.py | R25, R90 |
| M15 | URL uses the strict reading (`gate_reason`) | result_gate.py | P11, R10 |
| M16 | the string reading removed (numeric only) | result_gate.py | R11, P11 (real fixtures) |
| M17 | URL price fact `and` -> `or` | result_gate.py | R12 |
| M18 | URL placeholder tested on side 0 only | result_gate.py | R12 |
| M19 | the handler vocabulary check removed | error_handler.py | R80 ("hacked") |
| M20 | stream refusal applied to the first terminal only | text_routes.py | R40 |
| M21 | stream refund without keys | text_routes.py | R40 |
| M22 | the stream branch also calls `record_lifetime_comparison` | text_routes.py | R40 |
| M23 | the `elif` restored to `if` | text_routes.py | R40 |
| M24 | `_GATE_REASON_BY_ASSESS` drops `unsupported_category` | result_gate.py | R6 |
| M25 | strip / casefold removed from the low test | result_gate.py | R13 ("LOW ") |
| M26 | URL refund after the surface call | url_routes.py | R70 |
| M27 | the camera log row removed | image_routes.py | R50 |
| M28 | camera placeholder tested on side 0 only | result_gate.py | R13, R53 (PH1) |
| M29 | camera low tested on side 0 only | result_gate.py | R13, R51 (LOW1) |
| M30 | the builder stamp not gated (`result_gate_enabled() and` dropped) | response_builder.py | P8, the FY25 nine digests |
| M31 | the surface reason arm not gated | text_routes.py | P9 |
| M32 | the INFO line removed or given the query | text_routes.py | R32 |
| M33 | the features view re-added (`distinguishing_features` mapped from `_distinguishing_features`) | result_gate.py | R15, R56 |
| M34 | camera reserved refund without keys | image_routes.py | R50, R58 |
| M35 | URL `keys_out` not passed | url_routes.py | R70 |
| M36 | one placeholder answers `need_second_product` | image_routes.py | R53 |
| M37 | the refusal calls `category_gate.record_refusal_async` | text_routes.py / image_routes.py | R31, R60 |
| M38 | the rating range check dropped | result_gate.py | R11 ("6") |
| EQ1 | `result_gate_refusal` ignores `success` | result_gate.py | EQUIVALENT (RC8: gate_reason / url_gate_reason return None unless success is True, and a success:False result leaves through the failure branch first); recorded, not a survivor |

---------------------------------------------------------------------------------------------------

## 7. Comm set and gates for GREEN (cheapest first; every pytest through the bounded runner, one process at a time)

1. `py_compile` + `ruff check --select E9,F63,F7,F82 --no-cache` on the six app files and the test file;
   bytes > 127 = 0 on result_gate.py and the test file; `git diff --stat` content-only; the gitleaks keyword
   check on every new constant name.
2. The unit file alone, flag unset and with `ENABLE_RESULT_GATE=true` exported for that one call (bound 600).
3. The 4.1 / 4.2 files (the 1.10 runs plus the NOT MEASURED list), flag unset; then the E-row files with
   the flag exported (each green: the E-row proof).
4. **The local-.env hazard sweep (decides E8+):** the route-driving S81 suites of 4.1 E8+ and the
   SmartCompareApp-scanning / route chunks with the flag exported; every red file joins its clean list (a
   4.1 row the gate adds, never silently) or is named in the CLAUDE.md row.
5. CI-order set: the RED file + the E-row files + the 4.2 list, flag unset (bound 1200).
6. **Comm set = 388 files at base** (`<scratchpad>/s81-20/comm_set.txt`, sha256
   97218ca801416b02b4e5d4ab085a4e5a4410a60742327c51723332cf9cc58b18; built by `comm_set.py`): the module /
   symbol reference grep (346 files matching `result_gate|response_builder|text_routes|image_routes|
   url_routes|error_handler|build_comparison_response|_surface_comparison_failure|http_exception_handler|
   identify_and_compare|/text/compare|/image/identify|/url/compare|ENABLE_RESULT_STATUS_METADATA|
   ENABLE_RESULT_GATE|consume_comparison_credit|refund_comparison_credit|refund_anon_comparison_credit|
   record_lifetime_comparison|app\.main|TestClient|structured_comparison_service`; app.main / TestClient
   because the error handler is on every HTTP path) UNION the source-scanning pins (72: a scan call AND an
   `app` path segment, incl. test_model_config*, test_prompt_fence, test_u3c_store_false_pin,
   test_start_command*, test_migration_index_predicate_immutability, test_openai_key_log_hygiene_s69,
   test_sentry_channels_u8d_unit, test_auth_error_log_hygiene, test_events_allowlist_superset) UNION the
   SmartCompareApp-scanning backend tests (25; the client-visible contract gains `reason`) UNION the
   CLAUDE.md readers BY THE IMPORT GRAPH (44 test files naming CLAUDE.md / CLAUDE_MD or importing such a
   module, incl. the six named readers) UNION the importers of every edited test module E1-E8+ (12, closed
   transitively; by importer only: `tests/test_s78_tier_fill_residual_guard.py`,
   `tests/test_w4_13_flag_off_ledger.py` through `tests/fixtures/_gen_w4_13_flag_off_ledger.py`) MINUS the
   four `test_precommit_hook*.py` (0 in the set). 16 chunks of <= 25 files, bound 1200, base -> head,
   `comm -13` of the sorted FAILED node ids EMPTY; the environmental nodes (the r06 lexicon CRLF node, the
   cold-tiktoken pair) recorded identically at base and head.
   **Base-record reuse plan (LC-6 / GC-9; the RED round builds the 6869a3e6 record as its LAST step):** the
   41 files of 1.10 are fresh base records at 6869a3e6 (four [pyt] lines above). Of the remaining members,
   the stored records overlap the set as 0b19de5b/90b85603 379, 744616e3/ba26af35 368, e1491c97/4b65c5db
   185, 0b19de5b/c5734182 180, 00e4120d/9a85c0b0 37, ec747b49/c636b9d5 36 (measured with `grep -Fxf`); a
   member is reused only when its own file did not change since the record's sha, its text references none
   of the modules changed since that sha (the MOVING MAIN lines: since 0b19de5b the request path
   `structured_comparison_service`, `text_routes`, `image_routes`, `admin_routes`, `kb_ingest`, `kb_serve`,
   `kb_operator`, `kb_service`, `kb_seed_common`, `seed_kb_brands_wikidata`, `cron_learning`,
   `cron_few_shot_rotation`, SmartCompareApp files) nor CLAUDE.md, and it is not a glob walker; every other
   member runs at base in a detached junction-free scratch worktree, removed afterwards. Most members match
   `text_routes|image_routes|structured_comparison_service` by construction, so expect most of the 388 to
   run at base.
7. The fourteen backend-scanning client jest fences, by path from SmartCompareApp through the junction the
   orchestrator creates at GREEN (the unit touches app/ and CLAUDE.md).
8. The corpus gate `scripts/verify_flag_byte_identity.py` once at GREEN as a measurement (no extraction-spine
   file is edited, so the OVERALL SHA is expected equal at base and head).
9. The mutation table (lock, byte copies, sha256 restore).
10. The secret / personal-value sweep over the added lines; `git status --short` shows only the intended
    files.
The four `test_precommit_hook*.py` files are not run (no `.githooks` edit).

---------------------------------------------------------------------------------------------------

## 8. CLAUDE.md block and owner steps

### 8.1 The block (GREEN writes it after the S81-G5 block `:572-575`, before `## Tests` `:576`; wording may be tightened, content may not)

**SESSION 81 flag (S81-20 B2-RESULT-GATE-V2, 2026-11-05; default OFF, read PER CALL; a new name, so unset in
production by construction (Railway not read); FOCUS (the quota path); spec `.qa-s80/S81-20_UNIT_SPEC.md` of
the unit worktree with its review and rulings, the brief `specs/S81_20_BRIEF.md`):**
- `ENABLE_RESULT_GATE` (S81-20, `app/services/result_gate.py::result_gate_enabled` + the local one-liner
  `app/middleware/error_handler.py::_result_gate_keys_enabled` reading the same name; read per call as the
  FIRST statement of `result_gate_refusal`, as the one read `_rg_on` that opens the camera gate in
  `image_routes.identify_and_compare` (before the size enrichment), and as the first operand of the builder
  stamp, of `_surface_comparison_failure`'s reason arm and of the handler block). **Effect ON:** a comparison
  B1's assessment (`assess_result`, R-A4 / R-A5 / R0-5, computed by the gate itself; never
  `metadata.result_status`, `metadata.field_status` or `metadata.kb_hit`) does not support is NOT delivered:
  text POST / GET and URL compares answer HTTP 400 `code INSUFFICIENT_DATA` (build 3: "Thin data on that
  pair") with an additive `reason` in {placeholder_identity, same_identity, category_conflict, no_evidence};
  the stream's terminal pair is the existing INSUFFICIENT_DATA shape plus `reason`; the camera refuses
  BEFORE the paid compare with the existing `action:'error'` body (build 3: vision_failed) plus `reason` in
  {placeholder_identity (read on the vision identity before the size enrichment), low_confidence (ANY low
  on a V2-shaped product), same_identity (equal normalised identities, V2 features ignored, the size veto
  kept), category_conflict}; never `need_second_product`, `comparison_failed`, a new code or a 503. The URL
  reading counts JSON-LD string prices / ratings (`^\d{1,3}(?:,\d{3})*(?:\.\d+)?$|^\d+(?:\.\d+)?$`, > 0, a
  rating <= 5) and refuses two links to the same product as same_identity. Every refusal refunds the
  reserved credit with the consume's `consumed_keys` (the S81-09 shape incl. `device_daily`) and the
  anonymous camera credit with its keys BEFORE the raise, never calls `record_lifetime_comparison`, writes no
  history row, writes ONE `search_logs` row `success=False`, `error_message="result_gate:<reason>"` (both
  W4-13 states) and ONE INFO `[RESULT_GATE] refused input=<type> reason=<reason>`. The builder stamps
  `metadata.product_categories` under this flag too. No KB write: "every abstain writes gaps" is the G3
  ingest tail, which already ran inside the orchestrator (a no_evidence pair with resolved fragrance
  identities is queued at identity medium / high; placeholder / same / conflict pairs have nothing to
  queue). **Flag OFF:** byte-identical (pinned by `tests/test_s81_s20_result_gate.py` P1-P9 with the full
  configuration, the FY25 nine digests and the W4-13 flag-OFF ledger). **Flip preconditions (names only,
  never build preconditions):** App Store approval of build 3; B1's measured abstain rate
  (ENABLE_RESULT_STATUS_METADATA ON for one canary window and the `comparison_result_status` distribution
  read for text, text_stream, camera); the D17 pair hit rate from `kb_coverage_daily` (after 045 is applied
  and the kb-coverage service has run); the owner's names-only read of the stored camera rows'
  `metadata.identified_products[].confidence == "low"` share; the R-A2 order (after VISION_IDENTITY_V2 /
  IMAGE_PIPELINE_V2 / CATEGORY_TRUTH / CLAIMS_PROVENANCE / URL_MODE_V2 and after the S81-11 OTA so the client
  renders `reason`); the owner's explicit yes. **Canary:** the `[RESULT_GATE] refused` count per input and
  reason, the `result_gate:` rows, the 400 INSUFFICIENT_DATA rate on /text/compare and /url/compare, the
  camera `action:'error'` rate, refunds == refusals, no history row for a refused query (B1's message is not
  emitted for a refusal; B1's URL message over-reports and is not the URL canary: B1b). **Stated limits:**
  camera bodies thin after the compare are delivered; text / URL refusals come after the paid fan-out; the
  stream emits its intermediate events before the refusal terminal (build 3 never opens it); URL has no
  category check, does not catch a storefront-title name and refuses a same-product price check
  (L-URL-SAME; follow-up S81-20b) and queues no gap (L-URL-GAPS); a hard-cap partial refused no_evidence
  queues no gap; refusals of KB full hits are not countable until S81-22; a V1 low read is not refused;
  never set the flag in a local `.env` (route tests with thin stub bodies go red; the E-row clean lists).
  **Rollback:** unset the variable (per call, immediate).

The `:341` Feature Flags pointer clause gains: "`ENABLE_RESULT_GATE` (S81-20 B2-RESULT-GATE-V2, default OFF):
the row of the **SESSION 81 flag (S81-20 B2-RESULT-GATE-V2, ...)** block." The B1 row `:475` already names
B2 as the enforcer; it is not edited.

### 8.2 Owner steps (names only; a dated ledger line per step)

None to merge. After approval and the preconditions of 8.1: (1) ENABLE_RESULT_STATUS_METADATA ON on `web` for
one window; read the `comparison_result_status` distribution; (2) the D17 pair hit rate (after 045 and the
kb-coverage service); (3) the camera low-confidence share (names-only read of stored camera rows); (4) the
S81-11 OTA live; (5) flip `ENABLE_RESULT_GATE` on `web` with the owner's yes; watch the canary items;
rollback = unset.

### 8.3 The session-81 DEFECT_LEDGER row S81-20 (drafted; the orchestrator writes it; names only)

`| S81-20 | B2-RESULT-GATE-V2 (FOCUS: the quota path): refuse unsupported verdicts as non-deliveries at the
route exits (text / stream / URL 400 INSUFFICIENT_DATA + reason; camera action error + reason before the
compare), keyed refunds, one row, no lifetime, no history, no KB write (G3 tail queues the gaps); closes
MYEZ-001 (category-conflict half), MYEZ-002 (text / stream / URL / camera after R-S20-2), MYEZ-003 and
MYEZ-012 (text / stream / URL), MYEZ-004 (camera V1 and V2, R-S20-4), MYEZ-007 (refusal half), MYEZ-011,
MYEZ-027 | ENABLE_RESULT_GATE | tests/test_s81_s20_result_gate.py (tbd nodes) | feature/s81-s20-result-gate-v2 |
SPEC WRITTEN 2026-11-05 |`

---------------------------------------------------------------------------------------------------

## 9. Stated limits

- L1 (R-S20-7) Camera bodies thin AFTER the compare are delivered (PLAN_S80 section 0 item 2 binds camera
  refusals to pre-compare); under D05 + S81-11 they render honest unknowns.
- L2 URL: no category_conflict (categories overwritten at `url_extraction_service.py:1449`, no metadata);
  a name equal to the storefront title is not a placeholder here (B4's UNRESOLVED_PRODUCT under
  URL_MODE_V2).
- L-URL-SAME (R-S20-3) Two links to the same juice at two stores are refused as same_identity (the
  cross-retailer price check is not a compare); follow-up S81-20b "same-product price-check mode" for the
  owner; S81-11 carries the per-reason copy.
- L-URL-GAPS URL mode has no ingest tail: a URL refusal (or delivery) queues no gap.
- L-CAM-GAPS Camera refusals are pre-compare: no ingest, no gap (identity classes and low_confidence have
  no trustworthy identity to queue).
- L3 Stream: `scores` / `verdict` frames precede the refusal terminal; the terminal decides; build 3 never
  opens the stream.
- L4 (R-S20-14) Text and URL refusals happen after the paid fan-out; a pre-fan-out identity refusal on the
  text path = follow-up S81-20b; the orchestrator's post-build behaviour-profile update (scs `:4855-4860`)
  still runs for a refused compare.
- L5 (R-S20-15) B1's `comparison_result_status` message fires on deliveries only; refusals are counted by
  the `[RESULT_GATE]` lines and the `result_gate:` rows.
- L6 (R-S20-16, C12) The refusal row is written in both W4-13 states; on the URL and camera routes it is a
  NEW row while W4-13 flag 1 is OFF (their base pre-compare / failure exits write none then).
- L7 (B4-R6) The existing non-S81-20 exits keep their keyless refunds (a quota-path debit is still refunded
  there through the S81-09 stash, 1.5).
- L8 (R-S20-17) Camera category: the V2 `_category` when canonical, else the name stub; B1's camera stamp uses
  the stub only, so with V2 ON the B1 canary and the S81-20 camera decision can differ.
- L9 The gate inherits B1's predicate limits (the stub's generic category words; the tier-3 exclusion; the
  AUDITABLE reading); B1's merged camera stamp keeps the enrichment hole (its built names carry the size,
  R-S20-2).
- L10 `/text/quick` (admin-only) is not gated.
- L11 A mid-request flip can split one request (2.13 last row).
- L12 Never set the flag in a local `.env` (4.1, 7.4).
- L13 History keeps no trace of a refused compare (intended, MYEZ-027).
- L14 MYEZ-007 is closed in its refusal half only; the candidates route is a follow-up.
- L15 (R-S20-4) The distinguishing_features veto is dropped on the camera pre-compare while the compare
  searches brand + name only; when a later unit makes the compare use the features, the veto returns.
- L16 (R-S20-5) A V1 low read is not refused; a V2 rollback with the gate ON changes what is refused.
- L17 (1.7) G3 writes KB cards for a refused no_evidence pair at identity high (each side corroborated
  one-sidedly) and gaps at medium, for fragrance-category products only; a non-fragrance no_evidence pair
  queues nothing (the KB is fragrance-only, owner decision); a hard-cap partial refused no_evidence queues no
  gap (Q1).
- L18 (R-S20-19) Refusals of KB full hits are not countable from stored rows (a refusal stores no comparison
  row and the INFO line carries no kb_hit field) until S81-22 COMPARE-RUNS.
- L19 (R-S20-13) B1's URL telemetry over-reports `partial_no_winner`: the B1b follow-up, not this unit.
- L20 The camera log row's `query` is the base camera query string (brand / name of the identified pair),
  as the camera success row stores today; the INFO line carries none of it.
- L21 Stream: a client gone before the refusal terminal takes the base incomplete arm (keyless refund, the
  T5 row `client_gone_before_complete` / `stream_incomplete`, not `result_gate:`).

## 10. Out of scope

The orchestrator (no edit), `detect_comparison_quality` Rule 1, `kb_ingest.py` and any KB write or gap-only
call, `url_extraction_service.py` and the URL pre-gate / typed codes (B4), the category gate (S81-10 /
S81-10b), any client file and the S81-11 copy for `reason`, the vision prompt (B3), B1's emitter and its URL
calibration (B1b), `/text/quick`, the refund keys of the existing exits, a pre-fan-out text refusal and the
same-product price-check mode (S81-20b), any OpenAPI change (R0-6: none), any migration, any dependency.

## 11. Open questions for the orchestrator

- Q1 (R-S20-18, measured) A hard-cap PARTIAL refused as no_evidence never passed the G3 tail
  (`_build_partial_response` scs `:3759-3887`, callers `:4161` / `:4983` / `:5239`, does not call
  `_kb_ingest_tail`), so it queues no gap. Rule: accept as L17, or a gap-only call (which would edit the
  orchestrator or the route and write KB rows, both outside this unit as ruled)?
- Q2 (R-S20-2) The camera reads the flag ONCE (`_rg_on`, before the enrichment) and the block's first
  operand is that read, so the snapshot and the decision agree within a request. Confirm this satisfies "the
  FIRST statement of the camera block" (the alternative, a second read at the block, re-opens the BL2 hole
  for a request that flips between the two reads).
- Q3 (R-S20-5, measured) The V2 marker is `_is_product` (`openai_service.py:394`, always True on a kept V2
  candidate; V1 dicts `:678-684` carry no underscore key). Confirmed as the gate's V2 test.
- Q4 (R-S20-21, re-derived) The stream design is unchanged from the session-80 2.5 on the current chain:
  the S81-10 refusal never reaches the generator (`:1047-1049` raises before `StreamingResponse`); the W3-2
  persist condition is `:1199-1202`; the two keyless refund arms are `:1372-1376` and `:1403-1407`.
- Q5 (L17) G3 writes KB cards for a refused no_evidence pair whose identity is `high`: accept as a stated
  limit (cards describe the products, not the compare) or rule otherwise?
- Q6 (4.1 E8+) The E8+ list is a candidate list by inspection; the local-.env sweep at GREEN decides it (no
  file can go red at base: nothing reads the flag yet).
- Q7 (Q11 of the brief) Nothing in the measured footprint makes the unit more than FOCUS-by-quota: no
  legal / consent / migration / Lua / client change; the error_handler edit is a fourth scoped envelope
  passthrough of the three merged precedents' shape (FOCUS already).

Not done in this spec: no code, no test file, no CLAUDE.md edit, no scratch worktree; the RED file, the GREEN
change, the adversaries, the comm-set runs (beyond the 41-file base runs of 1.10), the E8+ sweep and the
mutation table are later phases. The NOT MEASURED files of 1.10 are RED's first job.
