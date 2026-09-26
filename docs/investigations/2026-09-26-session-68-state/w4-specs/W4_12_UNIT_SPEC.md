# W4-12 — display contract: one spelling, one margin, one verdict

Findings `PO-VERDICT-TRUTH-03`, `-04`, `-06`, `-07`, `-08`, `-09`, `-14` (all P2, all
`measured`/`verify:CONFIRMED` in `docs/investigations/2026-09-06-full-review-verified.json`).
Base **`61585c58`** (= `origin/main`, confirmed `git rev-parse HEAD` =
`61585c581e9deb78213f030260a765080f2e1dff`). Worktree for the red/green: a fresh
`feature/s68-w4-12-display-contract` from `61585c58`. Every line anchor below is at that SHA,
resolved by symbol (the review's anchors are from `76ace90`; table in §12). Every number below was
MEASURED in this run by the real function under pytest with the process-wide netguard
(`-p qaren_netguard -p tests.conftest`, no network, no `LIVE`, pinned venv `.venv-qaren`).

Two new flags, both default OFF, both read PER CALL:
`ENABLE_SINGLE_VERDICT_MARGIN` (the margin) and `ENABLE_SMART_PICK_VERDICT_CAPTION` (the Home
caption). Everything else in the unit ships UNFLAGGED, each with the precedent and the measured
reason it is not a result fork (§4). One finding half (`-06` tie scores) is deliberately NOT built
here: it cannot ship before the phones read `winner_idx` (§4.7, follow-up W4-12b).

---

## 0. Probe artefacts (all under `.qa-s68/specs/W4_12_probes/`, gitignored, never committed)

| file | what |
|---|---|
| `test_probe_w412.py` | measurement probe (SSE frames, reviews alias, tie, corpus rebuild, smart-pick/profile names, priority_match shapes, compute_scores spellings) → `$W412_OUT` |
| `test_probe_w412_proto.py` | PROTOTYPES defined in the probe only (SSE pre-verdict scrub via a patched `scs.reconcile_winner_prose`; caption sources; margin options; pre-nudge margin; corpus alias leaks) → `$W412_OUT2` |
| `w412_corpus_min.json` (sha256 `425bd8af1b5c3d839a5d6c035449eb3097386e1b69a2ff421c8bcbaf855699d0`) | de-identified copy of the review's own 27-row `comparisons` pull (no `user_id`/`id`/`share_token`/`query`), derived read-only from the review session's `scratchpad/po-rm/comparisons.json` (sha256 `c895f254ecdac625b982aec9fde0d19a7cb37564dfde35561807990a3182c7c0`, 27 rows, pulled 2026-09-06 01:35). **It is NOT under `docs/investigations/2026-09-06-full-review-state/`** — that folder carries only journals/reports; the corpus sat in the review session's scratchpad and was found there. |

Run (from the worktree root, conftest loaded as a plugin so credentials are neutralised before any
`app.*` import):

```
SPW=<scratchpad>; PD=<worktree>/.qa-s68/specs/W4_12_probes; cd <worktree>
W412_OUT=$SPW/w412_out.json W412_OUT2=$SPW/w412_out2.json PYTHONIOENCODING=utf-8 \
PYTHONPATH="$SPW/netguard;$PD" <venv python> -m pytest -p qaren_netguard -p tests.conftest \
  -p no:cacheprovider -p no:randomly -c pyproject.toml --rootdir=. --timeout=300 \
  -m "not (live_unit or live_db or integration)" $PD/test_probe_w412.py $PD/test_probe_w412_proto.py -q
```

Measured: `10 passed in 4.78s` + `[netguard] blocked 6 network attempt(s)` (probe);
`8 passed in 12.67s` + `[netguard] blocked 24 network attempt(s)` (proto). Every blocked attempt is
`socket.getaddrinfo b'api.openai.com'` — the streaming path's L3 `moderate_output`, which fails open
(the same pre-existing network reach the session-66 close doc §5 records for
`tests/test_winner_prose_reconciliation.py`). Any new streaming test in this unit MUST run under the
guard or patch `ContentSafetyService.moderate_output` (§6 conventions).

---

## 1. The defects, measured (REAL function outputs at `61585c58`)

### 1a. `-03` — the SSE `verdict` frame ships the raw verdict; `complete` ships the scrubbed one

`compare_from_text_streaming` (`structured_comparison_service.py:4150`) calls
`reconcile_winner_prose` (`:4781`), reads `win_margin` (`:4784`), builds the name
(`:4788`) and yields `("verdict", {...})` at **`:4793`** straight off the GPT `comparison` dict.
Nothing between the verdict build and the yield scrubs text; the score-internals scrub lives only in
`build_comparison_response` (SIB-4 block `response_builder.py:1632-1654`, winner text
`:1684-1693`, BC alias write-back `:2030-2042`), called at `:4835` AFTER the frame is on the wire
(`text_routes` `json.dumps` at yield).

Driven through the real generator with a GPT verdict that AGREES with scoring (index 0 both) and
leaks score internals in seven fields (probe `LEAKY`), frames captured as `json.dumps` at yield:

| field | `verdict` frame (wire) | `complete` frame | leak in verdict? |
|---|---|---|---|
| `winner.name` | `Apple iPhone 15 with a presentation score of 100` | `Apple iPhone 15` | **yes** |
| `winner.reason` | `Apple iPhone 15 scores 73.8 overall. It has the sharper camera.` | `It has the sharper camera.` | **yes** |
| `winner.key_tradeoff` | `Galaxy S24 trails by 12 points on value.` | `""` | **yes** |
| `recommendation` | = raw reason | `It has the sharper camera.` | **yes** |
| `value_context.product_0` | `Scores 81 on value.` | `""` | **yes** |
| `best_for.product_1` | `+5 pts battery fans` | `""` | **yes** |
| `personalized_insights[0].insight` | `Matches you: overall score higher.` | `""` | **yes** |
| `comparison.winner_declaration` (alias) | raw | `""` | **yes** |
| `comparison.specs_comparison.product_0_advantages` | `["10.7-point higher camera","Faster chip"]` | `["Faster chip"]` | yes |
| `winner.margin` / `winner.product_index` | 6 / 0 | 6 / 0 | — (equal) |

Verdict-vs-complete equality over the 10 shared fields: **2 of 10 equal** (margin, product_index);
leak count in the verdict frame 8, in the complete frame 0. With the GPT index DISagreeing
(`leaky_mismatch`, gpt 1 / scoring 0) the reconcile already repairs name/reason/key_tradeoff, and
4 fields still differ (`value_context`, `best_for`, `personalized_insights`, `comparison`).
With a CLEAN verdict all 10 are equal (so the defect is exactly the scrub, nothing else).

**Aliasing trap (load-bearing for the tests):** the verdict payload's `comparison` is the SAME
object `build_comparison_response` later mutates in place — measured
`live_verdict_comparison_is_complete_comparison: True`, and the collected in-memory verdict alias
reads the scrubbed `"It has the sharper camera."` after `complete`. A test that inspects the
collected Python object instead of a `json.dumps` snapshot taken AT YIELD passes vacuously on the
alias half. Every SSE test in this unit snapshots at yield.

### 1b. `-04` — the BC `products` alias re-ships the raw `review_summary`; `retailer_quotes` are never scrubbed

`build_comparison_response` scrubs `review_summary` only on the canonical projection
(`reviews.products[i].review_summary = scrub_review_summary(...)`, `response_builder.py:1843`;
`scrub_review_summary` returns a SHALLOW COPY, `text_sanitize.py:96`), then ships the raw
`product_data` as `result["products"]` (`:2025`), whose `reviews` dict is untouched. Measured with a
`review_summary.consensus = "Alpha scores 73.8 overall. Loved for its longevity."` and a highlight
`"Presentation score of 100."`:

| surface | consensus | highlights |
|---|---|---|
| `reviews.products[0].review_summary` | `Loved for its longevity.` | `[{"point": "Lasts all day."}]` |
| `products[0].reviews.review_summary` (BC alias, persisted, served by the unauthenticated `GET /share/{token}` — `share_routes.py:58/:70`) | **raw, leaks** | **both, incl. the leak** |

`canonical == alias` → **False**. The SSE `reviews` event already scrubs (`scs:4616`), so only the
alias disagrees.

`retailer_quotes` (`:1857`) ship unscrubbed on BOTH surfaces — measured a quote
`{"retailer": "amazon.com", "text": "I would give it a score of 100, …", "rating": 4.5}` ships
verbatim, `has_score_internals(text) == True`. **But** the key is `text`, not `quote` (the review's
fix reads `q.get('quote')`, which would filter nothing), and the producer
(`review_service.build_retailer_quotes_from_reviews`, `:256`) copies the REAL organic Serper
`snippet` of a cited source verbatim — third-party text, not model output, so it cannot carry OUR
internal score (§13 disagreement 1).

Recorded corpus (the 27 stored rows): **0 of 46** stored `review_summary` dicts would change under
the scrub, **0 of 6** stored `retailer_quotes` trip `has_score_internals`. The alias leak is a real
mechanism with zero recorded instances.

Also measured, NOT in scope: with `ENABLE_YOUTUBE_SOURCE` unset the alias still ships a cached
`reviews.youtube_review_signal` (`{"top_channel": "Chan", …}`) while the canonical projection ships
`None` (`_youtube_signal_for_response`, `:594`). Follow-up (§10).

### 1c. `-06` — exact tie: two margins, a fabricated 1-point score gap

`_build_scoring_v2` (`response_builder.py:1119`): `score_a/score_b = calibrate_score(raw)`
(`:1140-1141`); the argmax nudge (`:1160-1177`) forces `winner` strictly above `loser`;
`"win_margin": abs(score_a - score_b)` (`:1205`, POST-nudge). Measured, raw `57.3 / 57.3`:

| winner_index | overview overall | overview margin | scoring_v2 overall | scoring_v2 win_margin | phone presentation winner (`a >= b ? 0 : 1`) |
|---|---|---|---|---|---|
| 0 | 57.3 / 57.3 | **0.0** | 74 / **73** | **1** | 0 |
| 1 | 57.3 / 57.3 | **0.0** | **73** / 74 | **1** | 1 |

`calibrate_score(57.3) == 74` for both; the 73 is invented by the nudge. **The nudge is
load-bearing on the phones:** `ResultsScreen.tsx:765-771` (identical at `ab9442ae`) derives
`presentationWinnerIndex` ONLY from `product_a >= product_b`; without the nudge the `wi=1` row above
would be crowned product 0 while `overview.winner.product_index` says 1. So the score half of `-06`
cannot be fixed backend-only (§4.7).

### 1d. `-07` — doubled brand on `/home/smart-pick` and `/profile/recent-decisions`

`home_routes._select_smart_pick` (`:414`) ships
`"winner_name": f"{brand} {name}"` / `"runner_up_name": …` at **`:527`/`:528`**;
`profile_routes._extract_product_names` (`:85`) does the same at **`:102`/`:103`**. W4-10 (#176)
routed only `compute_scores`' `dimension_winners` labels through `dedup_brand_name`
(`scoring_service.py:1557-1565`); neither route was touched. Over the 27 recorded rows through the
REAL functions:

| surface | rows | doubled |
|---|---|---|
| `/home/smart-pick` (`_select_smart_pick(["camera"], [row])`) | 22 eligible (26 with ≥2 products; 4 lack a price and are ineligible) | **12** — winner AND runner-up doubled on the same 12 |
| `/profile/recent-decisions` (`_extract_product_names`) | 26 | **16** |
| stored `product_names` column | 26 | 4 (rows from 2026-03-13 … 2026-05-08; HEAD writer `database_service.py:450` writes bare `name`; History dedupes client-side, `HistoryScreen.tsx:92`) — out of scope |

Examples (winner tile text today → `dedup_brand_name`): `HealthAid HealthAid Vitamin D3 1000 IU`
→ `HealthAid Vitamin D3 1000 IU`; `Apple Apple iPhone 14` → `Apple iPhone 14`;
`Samsung Samsung Galaxy S25 Ultra 256GB` → `Samsung Galaxy S25 Ultra 256GB`;
`TOM FORD TOM FORD SOLEIL NEIGE 100ML` → `TOM FORD SOLEIL NEIGE 100ML`. Client render sites (phones =
EAS group `561d2cba` from `ab9442ae`; `git diff --stat ab9442ae 61585c58 -- SmartCompareApp` is
EMPTY, so the HEAD client source IS the phone bundle): `HomeEditorialSections.tsx:176`
(`{pick.winner_name}`, verbatim), `ProfileEditorialSections.tsx:131` (verbatim).
`deriveTone(pick.winner_name)` (`utils/deriveTone.ts:91`) is a case-insensitive SUBSTRING match, so
the tile tone is unchanged by the dedup.

Intra-payload second spelling (measured `compute_scores` on a brand-repeating pair):
`dimension_winners` label `TOM FORD OUD WOOD 100 ML` (deduped, W4-10) while `price_tiers` keys are
`TOM FORD TOM FORD OUD WOOD 100 ML` (raw, `scoring_service.py:1544`) — the two `price_tiers`
readers (`response_builder.py:1782`, `:1923`) use the same raw key, so `value_match` resolves
(`near`/`near` measured). Unrendered on phones (types only). Follow-up (§10), not this unit.

**`priority_match` is dead in production (the W4-10 follow-up), measured:** production writes
`dimension_winners[dim] = {"winner": name, "margin": m}` (`scoring_service.py:2473-2484`; all 22
recorded rows with dimension winners carry the dict shape), and `_select_smart_pick:456-464`
compares the DICT to a string (`winner_label == winner_name`). Through the real function with
`priorities=["camera_quality"]`: string-shaped value (what `tests/test_home_routes.py:302-341` and
`:375-429` pin) → `priority_match`; dict-shaped `{"winner": "Apple iPhone 15"}` → `recent_winner`;
0 of 22 recorded rows ever reach `priority_match`. Reviving it changes WHICH comparison the Home
card shows and its reason copy — a result fork, own unit (§10, W4-12c). This unit leaves `:456`
byte-for-byte untouched.

### 1e. `-08` — `verdict_short` is the winner's own name, or names the loser

`_select_smart_pick` sources `verdict_short` from `overview.winner.declaration` (`:500-503`) via
`_truncate_verdict_short` (`:317`). Over every stored row with ≥2 products (26): declaration
**same as the winner name 20**, **names the loser (and not the winner) 2** (rows 12/13, e.g. tile
`Manama Pickles Achbara Sauce` with caption `Manama Pickles Maabooch Kuwaiti Red 250g`), empty 3,
other 1 (a variant spelling of the winner). Through `_select_smart_pick` (22 eligible):
tautology 17, loser-named 2, None 3. Longest stored declaration 40 chars (the 140/160 budget never
bites). Producer already fixed for new writes (#99/#110 `reconcile_winner_prose` blanks the
declaration on a mismatch); nothing repairs the stored rows these read-paths serve.

Caption PROTOTYPE (flag ON design, §4.4) over the same 26 rows: source
`scoring_v2.factual_verdict.line1` **16**, `strip_score_internals(overview.winner.reason)` **1**,
none **9** (→ the existing `reason_key` i18n fallback); caption leaks score internals **0**, names
the loser **0**, over 140 chars **0** (lengths 31–63). Note the raw stored
`overview.winner.reason` leaks score internals in **17 of 26** rows — the reason fallback MUST go
through `strip_score_internals`. Every freshly built payload carries `factual_verdict.line1`
(23/23 rebuilt rows).

### 1f. `-09` — the verdict scrub is silent, and replaces most recorded verdicts

Rebuilding the 23 recorded rows that carry `overview.winner` through the HEAD builder: the stored
BC `comparison.winner_reason` trips `has_score_internals` on **17/23** and `strip_score_internals`
empties it on the same **17**; the shipped `overview.winner.reason` is the qualitative fallback
(`_QUALITATIVE_WINNER_REASON`, `:1270`) on **19/23** (17 scrub + 2 reconcile-mismatch rows 12/13) —
the review's 19/23 HOLDS. Telemetry: `metadata.verdict_scrubbed` present on **0/23**; `text_sanitize`
has no logger. The Results screen cannot show the reason anyway on any fresh payload
(`ResultsContent.tsx:364` renders `FactualVerdict` whenever `factual_verdict.line1` exists — 23/23);
it survives only in the share text (`ResultsScreen.tsx:354/:478`, `recommendation` =
`overview.winner.reason`).

### 1g. `-14` — two margins in every payload

`overview.winner.margin = scoring_result["win_margin"]` (`:1418` → `:1746`) is the RAW gap
(`scoring_service.py:1506`, `round(abs(o0-o1), 1)`); `scoring_v2.win_margin` is the CALIBRATED,
post-nudge gap (`:1205`; `calibrate = int(round(clamp(70 + (raw-50)*0.5, 60, 95)))`,
`scoring_service.py:2949`). Rebuilt recorded rows: **23/23 disagree** (e.g. 33.4 vs 16, 22.9 vs 12,
45.1 vs 22, 0.0 vs 1). Streaming: the `verdict` frame's `winner.margin` = raw 6 while
`complete.scoring_v2.win_margin` = 3 (same request, 78/72).

**What the phones do with it (measured in `SmartCompareApp/src` = the `ab9442ae` bundle):**
`ResultsScreen.tsx:448-459` — `const margin = scoring_v2?.win_margin ?? result?.overview?.winner?.margin;`
`>= 15 → 'strong'`, `< 8 → 'close'`, else `'default'`. `ctaVariant` is read at exactly three sites,
ALL analytics: `trackEvent('share', …cta_variant)` `:480`, `trackEvent('share_sheet_opened', …)`
`:483`, `trackEvent('share_completed', …)` `:495`. **It is not rendered.** The i18n keys
`referrals.cta.{strong,close,saved,default}` (`en.json:401-404`) have no reader in `src/`. Neither
margin is rendered as a number anywhere in `src/`. So the "strong CTA fires at 13 % where 41 % was
intended" is an ANALYTICS mis-bucketing on the phones, not visible copy. Counts on the 23 rows:
the rule applied to `scoring_v2.win_margin` (what phones read) = strong **3** / default 7 / close 13;
applied to `overview.winner.margin` (the raw scale the thresholds were written for) = strong **11** /
default 2 / close 10 (11/23 = 47.8 %; the review's "41 %" was 9/22 on an older count).
(The review's reachability note — phones at `97b5f15` read `scoring?.win_margin`, never on the wire
— is superseded: the M18 MB-contract-10 read shipped in the `561d2cba` OTA.)

Margin options measured on the same 23 rows (phone reads `scoring_v2 ?? overview`):

| option | phone `cta_variant` changes | no-`scoring_v2` fallback (legacy rows, W4-4 null) |
|---|---|---|
| C: `overview.winner.margin := scoring_v2.win_margin` | **0 / 23** | 11/2/10 → 3/7/13 |
| C': the same with the PRE-nudge calibrated gap M in both (this spec) | **1 / 23** — row 4 only, a legacy row whose stored `winner_index` contradicts its own overalls (unreachable at HEAD, §4.6); **0 / 22** otherwise (ties go 1 → 0, `close` either way) | as C |
| R: `scoring_v2.win_margin := raw` | 10 / 23 | unchanged |

Nudged rows (pre-nudge M ≠ post-nudge): 4, 12, 13, 14 (three exact ties + the legacy row).
The mobile follow-up's calibrated-scale thresholds (`>= 8` strong, `< 4` close) on M agree with the
raw-scale rule on **22/23** rows (11/3/9 vs 11/2/10).

---

## 2. Red claims of the row — status at `61585c58`

| # | claim | status | measurement |
|---|---|---|---|
| 1 | SSE `verdict` payload equals the `complete` payload after scrubbing (RED: raw dict on the wire) | **HOLDS** | leaky/agree: 2/10 shared fields equal, 8 leak fields in the verdict frame, 0 in complete; leaky/mismatch: 6/10 equal; clean: 10/10 |
| 2 | `overview.winner.margin == scoring_v2.win_margin` (RED on 23/23) | **HOLDS** | 23/23 rebuilt rows disagree; synthetic 83.0/49.6 → 33.4 vs 16; tie → 0.0 vs 1 |
| 3 | `/home/smart-pick` names deduped (RED on 16/26) | **HOLDS, number re-attributed** | smart-pick 12/22 eligible rows doubled (winner + runner-up); 16/26 is the `/profile/recent-decisions` surface. W4-10 #176 did not touch either route |
| 4 | `retailer_quotes` pass the score-internals scrub | **HOLDS as a fact, remedy DISPUTED** | synthetic `score of 100` quote ships verbatim on both surfaces; key is `text` not `quote`; content is verbatim third-party snippet; 0/6 recorded quotes trip the scrub (§13.1) |
| -06 | tie: margin 0.0 vs 1, fabricated 74/73 | **HOLDS** | §1c; score half blocked on the client (§4.7) |
| -08 | `verdict_short` = winner name (21/23), loser-named (2) | **HOLDS** | 20 same + 1 variant = 21, 2 loser, 3 empty over 26 rows |
| -09 | reason replaced 19/23, zero telemetry | **HOLDS** | 19/23 fallback (17 scrub + 2 reconcile), `verdict_scrubbed` 0/23 |

No finding was fixed by a later merge. W4-4 (#179→merged) added `honest_null` to `_build_scoring_v2`
(`:1136`) and the partial blanks (`:2043-2052`); W4-10 (#176) deduped `dimension_winners` only.

---

## 3. What already exists — reuse it, do not reinvent it

* **Scrub primitives** — `text_sanitize.strip_score_internals` (`:76`, drops a whole SENTENCE),
  `has_score_internals` (`:70`), `scrub_review_summary` (`:85`, returns a cleaned shallow copy),
  `dedup_brand_name` (`:24`, idempotent on already-correct names, token-boundary, "Applesauce" never
  deduped against "Apple"). Do not edit `text_sanitize.py`.
* **The builder's SIB-4 block** (`response_builder.py:1632-1654`) and winner-text composition
  (`:1684-1693`) + the WS-A alias write-back (`:2030-2036`) — the pre-verdict scrub is these, MOVED
  into one helper, not copied (§4.1).
* **The winner chokepoint** `reconcile_winner_prose` (`:202`) — idempotent, already called twice on
  the streaming path; the new helper is called right after it at `scs:4781`, the same way.
* **`_QUALITATIVE_WINNER_REASON`** (`:1270`) — the single fallback string; score-safe.
* **`_metadata_override`** (`scs:4816`) — the existing channel for streaming-only metadata into
  `build_comparison_response` (merged last, `:1957`).
* **Flag idiom** — `_honest_partial_scoring_enabled()` (`response_builder.py:116-121`):
  `os.environ.get(NAME, "").strip().lower() in ("1", "true", "yes", "on")`, read per call, never at
  import. Copy it verbatim for both new readers.
* **`_display_product_names`** (`scs:1234`) — the orchestrator already builds `product_names`
  through `dedup_brand_name`; the routes get the same helper.
* **Test harnesses** — the SSE harness `_collect_stream` in `tests/test_winner_prose_reconciliation.py:284-327`
  (patches `_fetch_product_data`, `parse_product_query`, `generate_comparison`,
  `get_scoring_service`); the smart-pick TestClient harness + `_comparison_row` in
  `tests/test_home_routes.py:27-137`; `_select_smart_pick` and `_extract_product_names` are pure
  functions and can be called directly.

---

## 4. The design

### 4.1 Pre-verdict scrub — UNFLAGGED (`-03`)

New helper in `response_builder.py`, placed beside `reconcile_winner_prose`:

```
def scrub_verdict_prose(comparison, product_names, winner_index) -> bool
```

Body = the SIB-4 block (`:1632-1654`, value_context / best_for / specs_comparison /
personalized_insights, in place) MOVED here, plus the winner-text write-back:
`comparison["winner_reason"] = strip(reason) or _QUALITATIVE_WINNER_REASON(name)`
(`name = product_names[winner_index] if product_names else ""`, the builder's exact `:1684`
expression), `key_tradeoff` / `winner_declaration` written back ONLY when the key is present (the
`:2031-2034` rule). Returns True iff the ORIGINAL `winner_reason` was a non-empty string and
`strip_score_internals` returned `""` (the `-09` signal; a reason already replaced by the reconcile
fallback is not counted). When it returns True it logs ONE line
`logger.warning("[VERDICT_SCRUB] winner_reason emptied by the score-internals scrub winner=%r dropped=%r", name, original[:200])`
(no query, no user id).

Call sites:
1. `build_comparison_response`, exactly where the SIB-4 block sits today (`:1632`): after the
   pros/cons scrub (`:1607-1616`), before the price-adjective drop (`:1655-1677`). The
   `_scrubbed_*` locals (`:1685-1693`) then read the already-scrubbed dict and are unchanged; the
   alias write-back (`:2030-2034`) stays (idempotent). If the helper returns True:
   `result["metadata"]["verdict_scrubbed"] = True` (key ABSENT otherwise, never `False`).
2. `compare_from_text_streaming`, immediately after `winner_index = reconcile_winner_prose(...)`
   (`:4781`) and BEFORE `_verdict_winner_name` (`:4788`) and the yield (`:4793`). If it returns
   True: `_metadata_override["verdict_scrubbed"] = True` (`:4816` block). The builder's own call on
   the same dict then returns False (already clean), so the WARNING fires exactly once per request
   on both paths.

Why unflagged: (a) the terminal `complete` payload is BYTE-IDENTICAL — prototype
(`test_probe_w412_proto.py::test_p03_proto`, the helper patched in after the real reconcile) over
leaky/clean × agree/mismatch: `complete`, `settle_complete` and every other frame
(`status/specs/prices/reviews/first_paint/scores`) identical to the unpatched run 4/4, the verdict
frame changes ONLY on leaky input, and verdict == complete on all 10 shared fields 4/4;
(b) no phone consumes the frame — `api.ts:809` dispatches `onVerdict`, but no screen registers it
(`grep onVerdict src/` = the type + the dispatch only) and phones do not stream at all
(`ENABLE_EXPO_FETCH_SSE_DEFAULT = false`, `features.ts:52`; `api.ts:672` → `runRestCompare`);
(c) precedent: #99/#110 made the SSE `verdict` index/name repair unflagged for the same "the frame
contradicts the terminal payload" reason. It only removes text the terminal payload already forbids.

### 4.2 Reviews alias — UNFLAGGED (`-04`, the `review_summary` half)

In the BC-alias loop (`response_builder.py:1994-2024`), for each `pd` whose `pd.get("reviews")` is a
dict AND whose `review_summary` is a dict: `pd["reviews"] = {**pd["reviews"], "review_summary": scrub_review_summary(pd["reviews"]["review_summary"])}`
— a NEW dict, never an in-place edit of the caller's reviews object (it may be a cache-owned
object). A `reviews` dict without `review_summary` is left as-is (no default injected — the default
dict at `:1843-1849` is the canonical projection's, not the alias's). Result: alias
`review_summary` == canonical `review_summary`. Recorded corpus: 0/46 would change; the synthetic
leak changes. Unflagged: the canonical projection and the SSE `reviews` event already ship this
exact text (WS-5 precedent); phones never render `review_summary` (Contract 2, `ResultsAccordion.tsx:339-341`).
`retailer_quotes`: NOT touched pending Fable ruling F2 (§14).

### 4.3 Display names — UNFLAGGED (`-07`)

`home_routes.py:527/528` and `profile_routes.py:102/103` become
`dedup_brand_name(winner.get("brand"), winner.get("name"))` (and loser). One import each
(`from app.services.text_sanitize import dedup_brand_name`). `home_routes.py:456` (the
`priority_match` comparison) is NOT touched. Measured effect: 12/22 smart-pick rows and 16/26
recent-decisions rows lose the doubled brand; every other row is byte-identical
(`dedup_brand_name` returns `f"{b} {n}"` when the name does not start with the brand — exactly
today's concat after `.strip()`). Note the stripping difference: today strips each half then
`.strip()`s the join; `dedup_brand_name` strips both halves — identical output for str inputs;
`None` brand/name → `""` in both. Unflagged: display spelling only, no winner/selection change;
precedent M21-W3 `7fb0b0d4` (display names) and W4-10 #176 (both unflagged, "live on deploy").
Cache: `home:smart_pick:{uid}` and `profile_recent:{uid}` are 5-minute Redis entries — the fix is
visible within 5 min of deploy.

### 4.4 `verdict_short` — loser guard UNFLAGGED, caption source FLAGGED (`-08`)

Add to `home_routes.py` two pure helpers and one reader:

* `_names_only_the_loser(text, winner, loser) -> bool`: normalise (casefold + collapse whitespace);
  True iff the text contains the loser's bare `name` or its `dedup_brand_name` display name AND
  contains NEITHER the winner's bare `name` NOR its display name. (Conservative: `iPhone 15` vs
  `iPhone 15 Pro` both ways keeps the caption — pinned.)
* `smart_pick_verdict_caption_enabled()` — reads `ENABLE_SMART_PICK_VERDICT_CAPTION`, the §3 idiom.
* **Unflagged (always):** after the candidate is chosen and truncated, if
  `_names_only_the_loser(verdict_short, winner, loser)` → `verdict_short = None` (the card then
  renders the `reason_key` copy, `HomeEditorialSections.tsx:194-203`). Measured: 2/26 rows.
  Precedent: #99's rule "shipping the losing product's name is indefensible, so it must not sit
  behind a flag".
* **Flag ON:** the candidate is `scoring_v2.factual_verdict.line1` (non-empty str) → else
  `strip_score_internals(overview.winner.reason)` (non-empty) → else `None`; then a tautology guard
  (normalised candidate == the winner's bare name or display name → `None`); then the loser guard;
  then `_truncate_verdict_short`. **Flag OFF:** today's candidate
  (`overview.winner.declaration`) and no tautology guard — byte-identical except the loser guard.
  Measured flag-ON over 26 rows: line1 16 / stripped reason 1 / None 9; 0 leaks, 0 loser, 0 > 140.
  Why flagged: it changes the Home card caption on essentially every row (20/26 today print the
  product name) — user-visible copy on a core surface, the #110 `ENABLE_WINNER_PROSE_RECONCILE`
  precedent (dark, canaried alone).

`/profile/recent-decisions` has no caption field — nothing to do there.

### 4.5 Scrub observability — UNFLAGGED (`-09` item 1)

Delivered by §4.1's return value + log + `metadata.verdict_scrubbed` (present only when True).
Additive metadata key, same category as `data_freshness_shaky` / `partial_stage`. Items (2) render
the reason on Results and (3) share-text fallback are client/product work → §10.

### 4.6 `ENABLE_SINGLE_VERDICT_MARGIN` (default OFF, read once per build, per call) (`-14` + the margin half of `-06`)

Reader `single_verdict_margin_enabled()` in `response_builder.py` (§3 idiom). Helper
`_calibrated_gap(scoring_result) -> int` = `abs(calibrate_score(raw_a) - calibrate_score(raw_b))`
with `raw_x = scoring_result.get("scores", {}).get(f"product_{x}", {}).get("overall", 50)` — the
exact extraction `_build_scoring_v2` uses (`:1138-1141`), taken BEFORE the nudge.

Flag ON, exact effect per site:
1. `_build_scoring_v2` gains a keyword `single_margin: bool = False` (direct callers and
   `tests/test_calibration_collapse_v2.py` keep today's behaviour); when True,
   `"win_margin": _calibrated_gap(scoring_result)` instead of `abs(score_a - score_b)`. The nudged
   `overall_score` values are UNCHANGED (the phones need them, §1c).
2. `build_comparison_response` reads the flag ONCE, passes it to `_build_scoring_v2`, and when
   `result["scoring_v2"]` is a non-empty dict sets `result["overview"]["winner"]["margin"] = result["scoring_v2"]["win_margin"]`.
   When `scoring_v2` is `{}` (fewer than 2 products) or `None` (W4-4 honest partial) the overview
   margin keeps today's raw value — there is no second margin to disagree with.
3. `compare_from_text_streaming` (`:4784`): `win_margin = _calibrated_gap(scoring_result)` when the
   flag is ON, else today's `scoring_result.get("win_margin", 0)`. The verdict frame is only emitted
   on the full 2-product path, so it equals `complete.overview.winner.margin` and
   `complete.scoring_v2.win_margin`.
4. NOT changed: the `scores` SSE event (`:4668-4674`) keeps the RAW `win_margin` beside the RAW
   `scores` it ships; `build_scores_summary`'s "clear/narrow lead" (`scoring_service.py:2907`) keeps
   the raw scale (verdict prompt input, not payload); `reconcile_winner_prose`'s log.

Flag OFF: every site executes today's code (the new branch is skipped; `_build_scoring_v2`'s default
keyword is False) — byte-identical.

Why pre-nudge: with a HEAD-produced `scoring_result` the winner is the raw argmax, calibration is
monotonic, so the nudge fires only when the calibrated scores COLLIDE — there M = 0 (honest "too
close") while the post-nudge value is the fabricated 1. Phone `cta_variant` is `close` for both, so
measured phone change = 0 on HEAD-reachable rows. The only row that moves (row 4) has a stored
`winner_index` contradicting its own overalls, which `compute_scores` cannot produce.

Why a FLAG although no phone renders it (the evidence the orchestrator asked for): (a) the value's
SCALE changes on the wire and in every persisted `comparisons.full_response` written after the
flip (raw float 33.4 → int 16) — the `comparisons` table then holds two scales in one field with no
marker; (b) third-party SSE/REST consumers (721 `text_stream` rows at the review) read it;
(c) the phones' `cta_variant` analytics on the no-`scoring_v2` fallback path moves 11/2/10 → 3/7/13
— the flip must coincide with the mobile threshold OTA (§10) so the analytics series breaks once,
not twice. The standing rule's test ("a user-visible result fork") is NOT met on the phones —
measured: zero render sites — so this is a contract/analytics flag, and it can flip as soon as the
mobile follow-up ships, with no product canary.

### 4.7 NOT built here: the tie SCORES (`-06` score half) → W4-12b

Deleting the nudge (the review's fix) or emitting equal calibrated scores on a tie requires the
phones to read `scoring_v2.overall_score.winner_idx` instead of comparing `product_a >= product_b`
(`ResultsScreen.tsx:765-771`). Until an OTA carrying that read is on the `preview` channel, a
backend-only change crowns product 0 where `overview.winner.product_index` says 1 (measured §1c,
`wi=1`). This unit pins today's nudged scores under BOTH margin-flag states (test F2/F4) so W4-12b
starts from a pinned baseline.

---

## 5. Files

**Touch:** `app/services/response_builder.py` (helper, two readers-worth of flag code, alias loop,
`_build_scoring_v2` keyword, metadata key); `app/services/structured_comparison_service.py` (two
lines at the verdict emit + one `_metadata_override` line + the flag-gated margin);
`app/api/home_routes.py` (`:527/:528`, the caption/guard helpers, one reader);
`app/api/profile_routes.py` (`:102/:103`); new `tests/test_w4_12_display_contract.py`; minimal
edits to existing tests ONLY where a pin asserts today's leak/doubling as desired behaviour (none
found by grep — `tests/test_home_routes.py` / `tests/test_profile_routes.py` use names that do not
repeat the brand; if one reddens, STOP and report rather than rewrite it).

**Must NOT touch:** `app/services/text_sanitize.py`; `scoring_service.py` (incl. `:1544`
`price_tiers` keys and `calibrate_score`); `home_routes.py:456-464` (`priority_match`);
`_truncate_verdict_short`'s budget; `reconcile_winner_prose`; `_QUALITATIVE_WINNER_REASON`; the
canonical `reviews.products[i]` projection (`:1822-1871`) incl. `retailer_quotes` and
`youtube_review_signal`; the `scores` SSE event; `database_service.py`; `share_routes.py`;
`history_routes.py`; anything under `SmartCompareApp/`; `backend/app/`.

---

## 6. Red tests — `tests/test_w4_12_display_contract.py`

Conventions: every SSE test uses a harness copied from `test_winner_prose_reconciliation.py:284-327`
that stores `json.loads(json.dumps(data, default=str))` AT YIELD (never the live object, §1a), runs
under the netguard (or patches `app.services.content_safety_service.ContentSafetyService.moderate_output`
— scs obtains the service via `get_content_safety_service()` at `:4280` and awaits `.moderate_output` at `:4914`, so the CLASS attribute is the patch point — to return not-flagged); flags via `monkeypatch.setenv`/`delenv`; `LEAKY` = the probe's comparison (§1a) with
GPT index == scoring index unless stated; scoring 78/72, `win_margin` 6.

**A — SSE verdict parity (unflagged)**
* A1 **RED** `test_sse_verdict_frame_carries_no_score_internals` — `has_score_internals` is False on
  verdict `winner.name/.reason/.key_tradeoff`, `recommendation`, every `value_context`/`best_for`
  value, every insight, alias `winner_reason/key_tradeoff/winner_declaration`, every
  `specs_comparison` list item. RED today: 8 fields leak.
* A2 **RED** `test_sse_verdict_frame_equals_complete_on_shared_fields` — the 10 fields of §1a
  (`comparison` alias compared whole). RED today: 8/10 differ.
* A3 **RED** `test_sse_verdict_frame_equals_complete_on_mismatch` — GPT 1 / scoring 0. RED today:
  `value_context`, `best_for`, `personalized_insights`, `comparison` differ.
* A4 **PIN** `test_sse_complete_payload_values_unchanged` — the leaky run's `complete` carries
  exactly today's measured values: winner `{name: "Apple iPhone 15", declaration: "", reason: "It has the sharper camera.", key_tradeoff: "", margin: 6, product_index: 0}`,
  `recommendation` = that reason, `comparison.value_context == {"product_0": "", "product_1": "Solid value for money."}`,
  `comparison.best_for == {"product_0": "camera lovers", "product_1": ""}`,
  `personalized_insights == [{"insight": ""}]`, advantages `["Faster chip"]` / `["More RAM"]`.
* A5 **PIN** `test_sse_clean_verdict_frame_unchanged` — clean verdict: the frame's
  `winner.reason/.key_tradeoff/.name`, `value_context`, `best_for` equal the INPUT strings.
* A6 **RED** `test_sse_scrub_sets_metadata_and_logs_once` — leaky run: `complete.metadata.verdict_scrubbed is True`,
  exactly ONE caplog WARNING containing `[VERDICT_SCRUB]`. RED today (no key, no log).

**B — reviews alias (unflagged)**
* B1 **RED** `test_products_alias_review_summary_is_scrubbed` — §1b input: alias consensus
  `"Loved for its longevity."`, highlights `[{"point": "Lasts all day."}]`, alias == canonical.
* B2 **PIN** `test_products_alias_reviews_input_dict_not_mutated` — keep a reference to the input
  `reviews` dict: after the build it still holds the raw consensus (copy, not in place).
* B3 **PIN** `test_products_alias_reviews_without_summary_untouched` — `reviews` without
  `review_summary` → alias has no `review_summary` key.
* B4 **PIN (pending F2)** `test_retailer_quotes_ship_verbatim_on_both_surfaces` — the §1b quote
  survives on canonical and alias, key `text`.

**C — names (unflagged)**
* C1 **RED** `test_smart_pick_names_are_deduped` (parametrized, corpus-shaped pairs inline:
  `("HealthAid","HealthAid Vitamin D3 1000 IU")`, `("Apple","Apple iPhone 14")`,
  `("Samsung","Samsung Galaxy S25 Ultra 256GB")`, `("TOM FORD","TOM FORD SOLEIL NEIGE 100ML")`,
  `("Manama Pickles","Manama Pickles Achbara Sauce")`) — `winner_name` and `runner_up_name` ==
  `dedup_brand_name`. RED today (doubled). Call both the pure function and the route (TestClient).
* C2 **RED** `test_recent_decisions_names_are_deduped` — same pairs through
  `_extract_product_names` and `GET /api/v1/profile/recent-decisions`.
* C3 **PIN** `test_names_unchanged_when_name_lacks_brand` — `("Apple","iPhone 15")` →
  `"Apple iPhone 15"`; `("Apple","Applesauce")` → `"Apple Applesauce"`; brand `None`/`""` → the
  name; name `None` → the brand.
* C4 **PIN** `test_priority_match_semantics_unchanged` — string-shaped dim winner → `priority_match`;
  dict-shaped → `recent_winner` (documents the dead branch; W4-12c owns it).

**D — verdict_short**
* D1 **RED** `test_verdict_short_never_names_only_the_loser` (flag unset AND set) — row-12 shape
  (winner `Achbara Sauce`, declaration = the loser's name) → `verdict_short is None`, `reason_key`
  `recent_winner`. RED today.
* D2 **PIN** `test_verdict_short_flag_off_keeps_declaration` — declaration == winner name → that
  name; the existing long-iPhone truncation pin (`tests/test_home_routes.py:499`) stays green.
* D3 **PIN** `test_loser_guard_keeps_captions_naming_both` — winner `iPhone 15 Pro` / loser
  `iPhone 15` and the reverse, declaration naming both → kept.
* D4 **RED** `test_caption_flag_on_prefers_factual_verdict_line1`.
* D5 **RED** `test_caption_flag_on_falls_back_to_scrubbed_reason` — no `factual_verdict`, reason
  `"X scores 73.8 overall. Lasts longer on skin."` → `"Lasts longer on skin."`.
* D6 **RED** `test_caption_flag_on_tautology_is_none` — no line1, empty reason, declaration ==
  winner name → `None`.
* D7 **PIN** `test_caption_flag_reader` — `TRUE`, ` true `, `on`, `1`, `yes` ON; unset, `false`,
  `0`, `` OFF.

**E — observability (unflagged, sync path)**
* E1 **RED** `test_scrubbed_reason_sets_metadata_flag_and_logs` — `comparison={"winner_index":0,"winner_reason":"Alpha scores 73.8 overall."}`
  → `metadata.verdict_scrubbed is True`, one `[VERDICT_SCRUB]` WARNING.
* E2 **PIN** `test_clean_reason_has_no_metadata_key_and_no_log` — key ABSENT (not False).
* E3 **PIN** `test_reconcile_dropped_reason_is_not_counted` — GPT 1 / scoring 0 → key absent.

**F — `ENABLE_SINGLE_VERDICT_MARGIN`**
* F1 **RED** (ON) `test_single_margin_overview_equals_scoring_v2` — raw 83.0/49.6 → both 16.
* F2 **RED** (ON) `test_single_margin_exact_tie_is_zero_everywhere` — 57.3/57.3, `wi` 0 and 1 →
  overview 0 and `scoring_v2.win_margin` 0; `overall_score` still 74/73 (wi 0) and 73/74 (wi 1).
  RED today (1).
* F3 **RED** (ON) `test_single_margin_sse_verdict_equals_complete` — 78/72: verdict margin ==
  complete overview margin == complete `scoring_v2.win_margin` == 3. RED today (6).
* F4 **PIN** (OFF) `test_margin_flag_off_is_today` — 33.4 & 16; tie 0.0 & 1 with 74/73; SSE verdict 6.
* F5 **PIN** (ON) `test_single_margin_leaves_partial_and_short_payloads_alone` — `len(product_data) < 2`
  → `scoring_v2 == {}`, overview margin raw; `ENABLE_HONEST_PARTIAL_SCORING=true` + partial +
  `scoring_result={}` → `scoring_v2 is None`, overview margin today's value.
* F6 **PIN** (ON) `test_scores_event_keeps_raw_win_margin` — the `scores` frame carries 6.
* F7 **PIN** `test_single_margin_reader` — same table as D7; plus `_build_scoring_v2` called
  directly without the keyword keeps the post-nudge value under the flag ON (the keyword, not the
  env, decides inside the helper).

---

## 7. Mutation checks — REQUIRED (delete the fix, confirm the named tests redden, record counts)

| mutation | must redden |
|---|---|
| drop the `scs` pre-verdict `scrub_verdict_prose` call | A1, A2, A3, A6 |
| helper skips the SIB-4 half | A2 (`value_context`/`best_for`/insights), A3 |
| helper skips the winner-text write-back | A1, A2 (name/reason/key_tradeoff/recommendation) |
| builder stops calling the helper (SIB-4 lost on sync) | existing SIB-4 pins in `tests/test_ws5_honesty.py` + E1 |
| helper returns True unconditionally / never | E2+E3 / E1+A6 |
| builder also logs when its own call returns False-after-prescrub (double log) | A6 (count == 1) |
| alias loop not applied | B1 |
| alias edited in place instead of copied | B2 |
| revert `home_routes:527` / `:528` | C1 winner / runner-up rows |
| revert `profile_routes:102/:103` | C2 |
| dedup applied at `home_routes:456` too | C4 |
| drop the loser guard | D1 |
| loser guard without the "and not the winner" clause | D3 |
| `smart_pick_verdict_caption_enabled()` forced True | D2 |
| caption sources swapped (reason before line1) | D4 |
| no `strip_score_internals` on the reason fallback | D5 |
| drop the tautology guard | D6 |
| `single_verdict_margin_enabled()` forced True | F4 |
| forced False | F1, F2, F3 |
| post-nudge gap instead of pre-nudge | F2 |
| `scs` verdict margin not routed | F3 |
| overview override applied when `scoring_v2` is `{}`/`None` | F5 |
| `scores` event margin routed | F6 |
| readers without `.strip().lower()` | D7, F7 |

---

## 8. Preserve (every test file that pins a touched function — green before and after)

`.qa-s68/specs/W4_12_preserve_set.txt` (70 files, sha256
`3d45004f24e08e410b268d9b7fa19f8db5cdacdd284d833752e271d885d9cba7`) = `grep -rlE
"build_comparison_response|_build_scoring_v2|compare_from_text_streaming|_select_smart_pick|home/smart-pick|_extract_product_names|profile/recent-decisions|_truncate_verdict_short" tests --include=*.py`.
Load-bearing among them: `test_response_builder_winner_card_consistency.py` (#99 pins),
`test_winner_prose_reconciliation.py` (#110 SSE pins — the verdict name/reason equality it asserts
on the mismatch path must stay green), `test_ws5_honesty.py` (SIB-4/A5 scrub),
`test_calibration_collapse_v2.py` (the nudge invariant — calls `_build_scoring_v2` directly, so the
new keyword MUST default False), `test_partial_response_no_fabricated_scores.py` (W4-4),
`test_streaming.py` (event order: `verdict` stays the 10th event), `test_home_routes.py`,
`test_profile_routes.py`, `test_endpoint_shapes_vs_jsx.py` (smart-pick/recent key sets — no new
key is added to either), `test_m21_brand_dedup_and_verdict_copy.py`, `test_tradeoffs_dedup_parity.py`.
Also every `text_sanitize` test (`grep -rl text_sanitize tests`) — unchanged module, must stay green.

---

## 9. Gates

1. **TDD red-first** — every RED in §6 observed red for the stated reason, then green.
2. **Comm gate.** Set = module grep ∪ function grep:
   `grep -rlE "response_builder|structured_comparison_service|home_routes|profile_routes" tests --include=*.py`
   (205 files) ∪ `grep -rlE "/api/v1/home|/api/v1/profile|/home/smart-pick|/profile/recent" tests --include=*.py`
   (adds `tests/_route_introspection.py`) ∪ the §8 preserve grep (adds
   `tests/test_m13_35_sse_disconnect_finally.py`, `tests/test_m18_preverdict_disconnect_refund.py`,
   `tests/fixtures/lane1/_helpers.py`) = **209 entries**
   (`.qa-s68/specs/W4_12_comm_set.txt`, sha256 `d00c7b7a7583de2bbd9d94ecefae83dce9ef4d0ffb448ec0a75891f4993aad85`),
   run over its `test_*.py` members plus the new file. Command = CI's selector
   (`-m "not (live_unit or live_db or integration)"`, the `tests/.pre_impl_failures.txt`
   `--deselect`s, `--ignore=tests/test_integration.py`) with `--timeout=120`, guarded, files in
   sorted order. **Base measured at `61585c58`:** 205-file module part
   `5432 passed, 2 skipped, 35 deselected, 35 xfailed, 17 warnings in 361.21s`,
   `[netguard] blocked 539 network attempt(s)` (curl_cffi noon/unbxd adapter fetches and the
   `api.openai.com` moderation reach — all fail-open); the two function-grep-only files
   `12 passed in 2.18s`, `[netguard] blocked 0 network attempt(s)`. **Zero base failures** — so at
   head ANY failed node in the set is a regression (after re-running it once against base to rule
   out a network flake, CLAUDE.md gotcha (g)).
   Head: `comm -13 base head` of the FAILED ids must be empty.
3. **Payload equality gate (flag-OFF identity; the `_proof` corpus harness is irrelevant — no price
   module moves).** Recorder `record_w412.py` (a pytest file under the agent's scratchpad, guarded,
   conftest as plugin) emits one record per input, `sha256(json.dumps(x, sort_keys=True, ensure_ascii=False, default=str))`
   after popping `metadata.{timestamp, elapsed_ms, elapsed_seconds, stage_timings_ms}`:
   (a) `build_comparison_response` over the 23 corpus rows rebuilt exactly as
   `test_probe_w412.py::test_p14_p09_corpus_rebuild` does (stored `products`, stored `comparison`,
   `scoring` + `winner_index` + `win_margin = overview.winner.margin`, `product_names` via
   `dedup_brand_name`); (b) the synthetic set: `LEAKY`/clean × agree/mismatch through the SSE
   harness (every frame recorded), tie `wi` 0/1, 83.0/49.6, the §1b reviews pair, `len==1`;
   (c) `_select_smart_pick(["camera"], [row])` and `_extract_product_names` over the 26 rows.
   Run at base in a DETACHED scratch worktree of `61585c58` under the agent's scratchpad
   (`git worktree add --detach`, removed after with `git worktree remove --force`, `git worktree list`
   shown), then at head with every flag unset, then base2 (base again). base == base2 record-by-record
   (determinism). head vs base with flags UNSET may differ ONLY at: the leaky SSE `verdict` frames
   (A); `metadata.verdict_scrubbed` on exactly the corpus rows whose stored reason the strip empties
   (17 of 23 at base — assert the list equals the probe's row list); the §1b alias record (B);
   `winner_name`/`runner_up_name` on the 12 smart-pick and 16 recent rows (C); `verdict_short` on
   rows 12 and 13 (D1). Any other differing record fails the gate. Then head with each flag ON
   alone: the margin fields (F) / the `verdict_short` of the rows in §1e (D4-D6) are the only
   additional differences.
4. **CI-order pin set** — head, one invocation, alphabetical:
   `tests/test_calibration_collapse_v2.py tests/test_endpoint_shapes_vs_jsx.py tests/test_home_routes.py tests/test_m21_brand_dedup_and_verdict_copy.py tests/test_partial_response_no_fabricated_scores.py tests/test_profile_routes.py tests/test_response_builder_winner_card_consistency.py tests/test_streaming.py tests/test_tradeoffs_dedup_parity.py tests/test_w4_12_display_contract.py tests/test_winner_prose_reconciliation.py tests/test_ws5_honesty.py`
   with every flag unset; again with `ENABLE_SINGLE_VERDICT_MARGIN=true`; again with
   `ENABLE_SMART_PICK_VERDICT_CAPTION=true`. In the flag-ON runs the ONLY expected reds are the OFF
   pins of the same flag (F4 resp. D2) — list them; nothing else may go red.
5. `ruff check --select E9,F63,F7,F82 --no-cache` + `py_compile` on the four edited modules;
   `git diff --stat` shows no whole-file diff (CRLF working copy, Edit tool only).
6. Fable review of the green before commit. Agents never commit.

---

## 10. Activation, canary lines, follow-ups

* **Deploy (unflagged parts, live immediately):** watch `[VERDICT_SCRUB]` WARNING volume (the first
  real measurement of the scrub rate on current prompts — publish it, it decides `-09`'s product
  call); the Home/Profile names correct within the 5-minute cache TTL; nothing else moves on the
  phones (the verdict frame is not consumed; the alias is not rendered).
* **`ENABLE_SMART_PICK_VERDICT_CAPTION`:** canary ALONE (Home copy). No precondition. Visible
  within 5 min (`home:smart_pick:{uid}` TTL). Check a Home card whose last comparison carries
  `factual_verdict` shows line1; a legacy row without it shows the `reason_key` copy.
* **`ENABLE_SINGLE_VERDICT_MARGIN`:** flip together with (or after) the mobile follow-up OTA that
  re-tunes the CTA thresholds to the calibrated scale — measured `>= 8` strong / `< 4` close agrees
  with the raw rule on 22/23 recorded rows. No phone-visible change either way (analytics only);
  the `cta_variant` property on `share*` events is the canary series.
* **CLAUDE.md at merge:** the two flag rows (effect ON, OFF identity, precondition, canary line) go into a SESSION 68 flags block; the unflagged changes go into its Active-runtime block under "what changed for callers with every flag OFF".
* **Follow-ups (each its own unit/issue):**
  - **W4-12b** tie scores honest (`-06` score half) — client reads `winner_idx`
    (`ResultsScreen.tsx:765-771`) in an OTA FIRST, then backend drops the nudge / ships `tie: true`
    behind its own flag.
  - **W4-12c** `priority_match` is dead (dict vs string, §1d) — repair against both spellings
    (raw concat for pre-#176 rows, deduped after) behind a flag; rewrite
    `tests/test_home_routes.py:302-341/:375-429` to the production shape.
  - **W4-12d** `price_tiers` keys still raw (`scoring_service.py:1544`) — dedup together with both
    readers (`response_builder.py:1782/:1923`); unrendered.
  - **W4-12e** stale `youtube_review_signal` on the BC alias with `ENABLE_YOUTUBE_SOURCE` OFF.
  - **Mobile lane:** CTA thresholds to the calibrated scale; `presentationWinnerIndex` from
    `winner_idx`; (product call) render `overview.winner.reason` beside `FactualVerdict`; share text
    fallback to `factual_verdict.line1` when `metadata.verdict_scrubbed`.
  - Stored rows are NOT rewritten (no migration): the 12/16 doubled names are fixed at read time
    by this unit; the 17 leaking stored `overview.winner.reason` values stay in `full_response`
    (served verbatim by `GET /share/{token}`) — a backfill is a separate decision.

---

## 11. Honest limits

1. The corpus is 27 rows from before 2026-06-22 (last write 2026-06-21, the review notes zero rows
   since 2026-08-01); the 17/23 scrub rate reflects older prompts. Today's rate is unknown until
   §4.5's log runs in production.
2. The `-04` alias leak and the `retailer_quotes` trip both have ZERO recorded instances (0/46,
   0/6); the fix is defence for a persisted, publicly shared body, not a measured user harm.
3. No web/third-party SSE consumer was observed; "no consumer" is proven for the phones only
   (`onVerdict` unregistered, SSE off).
4. `search_logs` product-name strings (`text_routes.py:461/:648/:958`) still use the raw concat —
   analytics only, not in scope.
5. The corpus rebuild feeds stored `scoring` into the HEAD builder; it measures the builder, not
   today's scoring engine (the scoring inputs are historical).

## 12. Anchors (review `76ace90` → `61585c58`, by symbol)

| review | symbol | HEAD |
|---|---|---|
| `rb:1136-1174` | `_build_scoring_v2` calibrate / nudge / `win_margin` | `:1140-1141` / `:1160-1177` / `:1205` (def `:1119`) |
| `rb:1387` | `overview.winner.margin` | read `:1418`, emit `:1746` |
| `rb:1635` | winner-text scrub | SIB-4 `:1632-1654`; `_scrubbed_*` `:1684-1693`; alias write-back `:2030-2042` |
| `rb:1801` | `retailer_quotes` projection | `:1857` (`review_summary` scrub `:1843`) |
| `scs:4266` | SSE `verdict` yield | `:4793` (reconcile `:4781`, margin `:4784`, name `:4788`); complete build `:4835` |
| `home_routes.py:503` | `verdict_short` | `:500-503` (unchanged), `_truncate_verdict_short` `:317` |
| `home_routes.py:527` | `winner_name` / `runner_up_name` | `:527` / `:528`; `priority_match` `:456-464` |
| `profile_routes.py` (drifted) | `_extract_product_names` | def `:85`, concat `:102/:103` |
| `text_sanitize.py:95` | `scrub_review_summary` shallow copy | `:96` |
| `ResultsScreen.tsx:431` | `ctaVariant` margin read | `:453` (block `:448-459`); presentation winner `:765-771` |
| `api.ts:684` | `case 'verdict'` | `:809` |
| `HomeEditorialSections.tsx:175` | winner tile | `:176`; caption `:194-203` |
| `ResultsAccordion.tsx:338-340` | review quotes unrendered | `:339-341` |
| `ResultsContent.tsx:362-377` | FactualVerdict XOR reason | `:364-379` |

## 13. Spec disagreements with the review

1. **`retailer_quotes` scrub (`-04`):** the review filters `q.get('quote')`; the key is `text`, and
   the text is a verbatim third-party organic snippet (`review_service.py:256-310`), not model output
   — a real review saying "a score of 100" is not OUR internal score, and dropping it is
   over-rejection. 0/6 recorded quotes trip. This spec does not scrub them (pin B4) — Fable F2.
2. **"Flag: none" for the margin (`-14`):** measured no phone render site, but the persisted scale
   and the analytics series change → default-OFF flag (§4.6).
3. **`-06` fix "delete the nudge + FE reads winner_idx, gate on `ENABLE_HONEST_TIE_SCORES`":** the
   backend half cannot be flipped until the OTA exists; building dark code now adds nothing —
   deferred to W4-12b; the margin half is folded into §4.6 (tie margin 0).
4. **`-14` CTA "fires at 13 % where 41 % was intended":** `ctaVariant` is analytics-only at
   `ab9442ae` (3 `trackEvent` sites, no render; `referrals.cta.*` unused). Numbers: 3/23 vs 11/23
   (47.8 %), not 41 %. The review's "phones read `scoring?.win_margin`" is superseded by the
   `561d2cba` OTA.
5. **`-07` "RED on 16/26" for smart-pick:** 16/26 is recent-decisions; smart-pick is 12/22
   eligible. `database_service.py:549` is not the `product_names` writer (`:450`, bare name; 4/26
   old rows doubled).
6. **`-08` read-time repair "drop the declaration when it does not contain the winner's name":**
   would also drop row 24's variant spelling and any caption naming neither product; this spec
   drops only captions that name the loser and not the winner.
7. **`-03` test_first:** inspecting the collected event object passes vacuously on the alias half
   (same dict mutated later); snapshot at yield.
8. **`-09` items (2)/(3):** client/product — follow-ups, not this unit.

## 14. OPEN QUESTIONS FOR FABLE

* **F1 — margin scale and flag.** Accept `ENABLE_SINGLE_VERDICT_MARGIN` (default OFF) with the
  PRE-nudge calibrated gap in overview + scoring_v2 + the SSE verdict (§4.6)? Alternatives measured:
  C (post-nudge, ties become a fabricated 1 in overview), R (raw into scoring_v2 — 10/23 phone
  analytics buckets move, breaks `app/models/scoring_v2.py:53 win_margin: int`). Or ship it
  unflagged, since no phone renders it?
* **F2 — `retailer_quotes`:** leave verbatim third-party snippets unscrubbed (this spec) or filter
  on `text` anyway?
* **F3 — scope split:** W4-12b (tie scores, client-first), W4-12c (`priority_match` revival,
  flagged), W4-12d (`price_tiers` keys), W4-12e (youtube alias) as separate units — agree?
* **F4 — unflagged set:** confirm the four unflagged changes (SSE pre-scrub, alias
  `review_summary`, display names, loser guard + `verdict_scrubbed`) under the precedents cited.
  The names change is visible copy on Home/Profile (12/22, 16/26 rows).
* **F5 — product calls for Ahmed:** stop paying gpt-4o for a sentence Results cannot show
  (`-09` item 2), and whether to backfill the 17 stored leaking reasons served by `/share/{token}`.
* **F6 — mobile follow-up ownership:** CTA threshold retune + `winner_idx` read belong to the
  mobile lane; the margin flag should flip with that OTA.


---

# ADVERSARIAL SPEC REVIEW (2026-09-26, session 68)

**VERDICT: APPROVED_WITH_CORRECTIONS.** The defects are real and the core design (move the SIB-4 and winner-text scrub into one helper, call it before the SSE `verdict` yield, dedup the two route spellings, loser-only guard, default-OFF margin and caption flags) holds up when prototyped. Seven claims are refuted or drifted. Three RED tests and one PIN as written do not kill the mutations the table assigns to them. The flag-ON gate expects zero collateral reds but gets 23. One RENDERED leak next to `-04` is missing. None of this changes the design's direction. All of it must be fixed in the spec before the red phase starts.

Base re-confirmed: `git rev-parse HEAD` = `61585c58…`; spec sha on entry `d4360e26…5a54`; `W4_12_comm_set.txt` `d00c7b7a…`, `W4_12_preserve_set.txt` `3d45004f…` and `w412_corpus_min.json` `425bd8af…` all re-hashed equal. Every number below comes from a run under the pinned venv with the process-wide netguard. Reviewer scratch (never committed) is in `<scratchpad>/w412rev/`: `plug/w412rev_proto.py` is a prototype plugin of the whole design, applied by source transform and wrappers, active only when `W412REV_PROTO=1`. The probe files are `probe/test_w412rev_{probe,praise,ws}.py` and the runners are `run_cfg.sh` and `run_comm.sh`.

## R0. Reproduction of the author's probes — CONFIRMED

`test_probe_w412.py` and `test_probe_w412_proto.py` ran together: `18 passed in 15.97s`, `[netguard] blocked 30 network attempt(s)` (6 + 24, all `socket.getaddrinfo b'api.openai.com'`). The following were reproduced exactly:

* **§1a:** 2/10 shared fields equal on the leaky input, 8 leaking fields in the verdict frame and 0 in complete, 6/10 on the mismatch, 10/10 on clean input. `live_verdict_comparison_is_complete_comparison: True`. Scores event 6, `scoring_v2` 3.
* **§1b:** alias raw vs canonical scrubbed. The quote key is `text` and the quote ships verbatim on both surfaces. The alias `youtube_review_signal` is stale.
* **§1c:** tie 57.3/57.3 → overview margin 0.0 vs 74/73 with `win_margin` 1, for both `wi` values. `calibrate_score(57.3) = 74`.
* **§1d:** smart-pick 22 eligible, 12 winner and 12 runner-up doubled. Recent-decisions 16. Stored `product_names` 4. `dimension_winners` values are dict-shaped on every row, and `priority_match` is reached on 0 rows.
* **§1e:** declaration relation 20/2/3/1. Through the route: 17 tautology, 2 loser, 3 None. Maximum declaration length 40.
* **§1f/-09:** 17 stored reasons emptied by the strip, 19/23 fallback, `verdict_scrubbed` present on 0/23, `factual_verdict.line1` present on 23/23. The prototype's True rows are exactly the stored-emptied rows `[3,5,7,8,9,10,11,15,16,17,20,21,22,23,24,25,26]`. 0 rows are partially stripped, so a full-empty-only signal loses nothing on this corpus.
* **§1g:** 23/23 disagree. The CTA rule on `scoring_v2` gives 3/7/13 and on the raw margin 11/2/10. Option C moves 0/23 rows, option R moves 10/23, C' moves 1/23 (row 4). Nudged rows are 4/12/13/14. The calibrated rule agrees with the raw rule on 22/23.
* **Prototype P03:** complete, settle_complete and every other frame are identical 4/4, and verdict == complete 10/10 in 4/4 cases.
* **P04 corpus:** 0/46 summaries and 0/6 quotes affected.

**Comm base (§9 gate 2) — CONFIRMED.** The 207 `test_*.py` members of the 209-entry set (recomputed by the three greps, `diff` empty) ran in one invocation under the CI selector (deselects from `tests/.pre_impl_failures.txt`, `--ignore=tests/test_integration.py`, `--timeout=120`): `5444 passed, 2 skipped, 35 deselected, 35 xfailed, 17 warnings in 349.58s`, `[netguard] blocked 539 network attempt(s)`, **0 failed**. That equals the author's 5432 + 12. The preserve grep, recomputed, is byte-equal to `W4_12_preserve_set.txt` (70 entries).

**Client anchors — CONFIRMED.**
* `git diff --stat ab9442ae 61585c58 -- SmartCompareApp` is empty.
* `ctaVariant` at `ResultsScreen.tsx:448-459` is read only at `:480/:483/:495` (trackEvent). `presentationWinnerIndex` is at `:765-771`.
* `onVerdict` exists only as the type at `api.ts:557` and the dispatch at `:809`. `ENABLE_EXPO_FETCH_SSE_DEFAULT = false` (`features.ts:52`).
* `referrals.cta.*` has no reader. `home.smart_pick.reason.recent_winner` exists in both `en.json` and `ar.json`, so the D1 fallback copy renders.
* `HomeEditorialSections.tsx:176/:194-203`, `ProfileEditorialSections.tsx:131`, `HistoryScreen.tsx:92` and `deriveTone.ts:91-95` (substring match) all hold.

**Backend anchors — CONFIRMED.** All §12 rows re-resolved by symbol at HEAD: rb `:1119/:1136/:1140-1141/:1160-1177/:1205/:1418/:1632-1654/:1684/:1746/:1843/:1857/:1994/:2009/:2025/:2030-2042`; scs `:1234/:4150/:4280/:4668-4674/:4781/:4784/:4788/:4793/:4816/:4835/:4914`; home_routes `:317/:456/:500-503/:527/:528`; profile_routes `:85/:102/:103`; text_sanitize `:24/:70/:76/:85/:96`. `validate_verdict` runs at scs `:4736`, before the pre-scrub, and the L3 moderation text at `:4900` reads `comparison` after the builder has already scrubbed it in place. The pre-scrub therefore moves no moderation or trust-validation input.

## R1. Refuted or drifted claims (with measurements)

1. **§9 gate 4: "in the flag-ON runs the ONLY expected reds are … F4 resp. D2" — REFUTED.** The full prototype was run over the CI-order set plus the preserve set plus `tests/test_prescoring_showable_guard.py` (71 files; base `1361 passed … 0 failed`, `[netguard] blocked 309`):
   * All flags unset (unflagged changes only): `1361 passed`, **0 failed**. This confirms §5's "no existing pin asserts the leak or doubling".
   * `ENABLE_SINGLE_VERDICT_MARGIN=true`: **22 failed** — `tests/test_partial_response_no_fabricated_scores.py::test_05a/05b/05c_pin_flag_off_*` ×6 each (18) and `::test_15_pin_non_partial_absent_overall_keeps_calibrated_block[None|true]` (2). Each asserts `scoring_v2.win_margin == 1` on the fabricated 70/69 block, and the pre-nudge gap of 50/50 is 0. The other 2 are `tests/test_prescoring_showable_guard.py::test_10b_pin_flag_off_end_to_end_numbers_hold[unset|false]`, which asserts the raw `overview.winner.margin == 24.6` at `:527`. **W4-3's file is not in the CI-order set at all.**
   * `ENABLE_SMART_PICK_VERDICT_CAPTION=true`: **1 failed** — `tests/test_home_routes.py::TestHomeSmartPick::test_extension_fields_present_when_data_available`. Its row has a declaration but no `factual_verdict` or reason, so the flag-ON candidate is None.

2. **§4.6 reason (c) and flag_decision: "the phones' `cta_variant` analytics on the no-`scoring_v2` fallback path moves 11/2/10 → 3/7/13 — the flip must coincide with the mobile threshold OTA" — REFUTED by the spec's own §4.6 item 2.** The phone reads `scoring_v2?.win_margin ?? overview.winner.margin`. It falls back to the overview margin only when `scoring_v2` is `null` (W4-4) or `{}` (len < 2), and exactly then the design keeps the overview margin RAW. Stored legacy rows are re-served verbatim and are never rebuilt. So under the flag the fallback series moves on **0** payloads; the 11/2/10 → 3/7/13 figure is option C applied to rows that do have `scoring_v2`. Measured phone-read change under C' is 0/22 HEAD-reachable rows. Only reasons (a) (persisted scale) and (b) (third-party consumers) survive, and the "flip with the OTA" coupling has no measured basis.

3. **Mutation row "drop the tautology guard → D6" does NOT kill; neither does the flag-set half of D1 for the loser guard.** D6's input is "no line1, empty reason, declaration == winner name". Under the flag the candidate never reads the declaration, so it is None before either guard runs. With the prototype and the caption flag ON, every variant pair and the row-12 shape return `verdict_short None` regardless of the guards. Both tests are vacuous for their guards.

4. **Mutation row "dedup applied at `home_routes:456` too → C4" survives** unless C4 carries a brand-repeating string-shaped case. For `("Apple","iPhone 15")`, `dedup_brand_name` equals today's concat, so the mutant is a no-op. Measured (`p07_priority`): string-shaped `TOM FORD`/`TOM FORD OUD WOOD` gives `recent_winner` at HEAD, and a :456 dedup would flip it to `priority_match`.

5. **§6: D7 and F7 are labelled PIN but are RED at HEAD.** `smart_pick_verdict_caption_enabled` and `single_verdict_margin_enabled` do not exist, so the tests fail with an AttributeError or ImportError. If the file imports `scrub_verdict_prose`, the readers or `_names_only_the_loser` at module level, the WHOLE file is a collection error at HEAD. Every PIN then reads red and every RED is red for the wrong reason.

6. **§4.1(a) "the terminal `complete` payload is BYTE-IDENTICAL" and gate 3's allowed-delta list — incomplete.** The design adds `metadata.verdict_scrubbed=True` to the leaky SSE `complete` AND `settle_complete` frames (via `_metadata_override`). Gate 3 lists only "the leaky SSE `verdict` frames" for the synthetic set, so a correct implementation fails the gate as written. Separately, "the verdict frame changes ONLY on leaky input" is false: `strip_score_internals` also normalises whitespace after sentence punctuation (measured: `"Sharper camera.  Faster chip."` → single space, `"A.\nB."` → `"A. B."`, leading and trailing trimmed, `None` → `""`). An ABSENT `winner_reason` also becomes the qualitative fallback. The verdict frame therefore also moves on clean-but-irregular input. That is the intended parity, but the claim and A5's "equal the INPUT strings" hold only for single-spaced, present strings.

7. **§1b/§4.2 "phones never render `review_summary` … the fix is defence for an unrendered alias" — INCOMPLETE; a rendered sibling leak exists.** `review_praise` IS rendered (`ResultsAccordion.tsx:364-368` reads `reviews.products[i].review_praise`, then `products[i].review_praise`). Both are built by `review_service.build_review_praise` from the RAW `review_summary` (rb `_safe_review_praise`, `:73-78`; canonical at `:1863`, alias at `:2009`). Measured, a positive highlight `"Presentation score of 100."` gives canonical AND alias praise `"Owners consistently highlight presentation score of 100 and lasts all day on skin."`. A positive consensus `"Alpha scores 73.8 overall. …"` gives praise `"Alpha scores 73.8 overall. Loved for its longevity"`. Built from `scrub_review_summary(...)` instead, the praise is clean (`"Owners say it lasts all day on skin."` / `"Loved for its longevity"` / `None`). Stored rows: 0/8 praise lines leak.

8. **Drift, §1e/§4.4 caption counts.** 16/1/9 is over all 26 rows. Through `_select_smart_pick` (22 eligible rows) the flag-ON caption is a string on 13 rows and None on 9, and it changes the Home card on **19/22** eligible rows relative to flag-OFF-with-guard (prototype). Gate 3's "the rows in §1e" should read "19 of 22 eligible rows".

9. **Drift, §4.1 call site 1.** "`result["metadata"]["verdict_scrubbed"] = True`" cannot be written at the SIB-4 site (`:1632`); `result` is created at `~:1726`. It must be a local, written after the `result` dict exists. Its precedence relative to `result["metadata"].update(metadata)` at `:1957` does not matter, since both write True.

## R2. Corrections (binding on the implementer unless Fable overrules)

* **K1 (gate 4).** Add `tests/test_prescoring_showable_guard.py` to the CI-order set, which makes 13 files in alphabetical order. The expected-red list becomes:
  * margin ON: F4 plus the 22 nodes of R1.1.
  * caption ON: D2 plus `test_home_routes.py::TestHomeSmartPick::test_extension_fields_present_when_data_available`.

  Any other red fails the gate. The spec forbids editing existing tests. Fable decides whether these pins get a `monkeypatch.delenv` of the new flag in this unit (see F-A).
* **K2 (§4.6).** Delete reason (c) and the "flip with the mobile OTA" coupling, or replace them with a measured basis. Keep (a) and (b). State the new intra-payload inconsistency the flag introduces: on nudged rows (4/23 corpus rows: three ties plus row 4) and on the W4-4 fabricated 70/69 block, `scoring_v2.win_margin` (pre-nudge) ≠ `|overall_score.product_a − product_b|`. F2 pins it; the prose must own it.
* **K3 (D tests).**
  * D6 must feed a `factual_verdict.line1` (and, separately, a stripped reason) whose normalised text equals the winner's bare or display name, and expect None.
  * D1's flag-set half must feed a line1 or reason that names only the loser.
  * D4 must carry BOTH a line1 and a clean reason, so that the "sources swapped" mutant is killed.
* **K4 (C4).** Add the brand-repeating string-shaped case (`TOM FORD`/`TOM FORD OUD WOOD`, label `TOM FORD OUD WOOD`) and expect `recent_winner`. This kills the :456 mutant.
* **K5 (§6 conventions).** Import every new symbol INSIDE the test body (or via `getattr` on the module), never at module level. Relabel D7 and F7 as RED (new API). Add to the red-phase report "every PIN observed green at HEAD, every RED observed red for its stated reason".
* **K6 (gate 3).** Add to the allowed unflagged deltas: `metadata.verdict_scrubbed` on the leaky SSE `complete` and `settle_complete` frames. Add to the caption-ON deltas: `verdict_short` on 19/22 eligible rows. A5's inputs must be single-spaced present strings. Add a PIN that a clean reason with a double space after a full stop yields verdict-frame reason == complete reason. Parity is the property, not identity to the input.
* **K7 (§4.2 placement).** The alias `review_summary` replacement must run AFTER `pd["review_praise"] = _safe_review_praise(pd)` (`:2009`). Otherwise alias `review_praise` diverges from canonical `reviews.products[i].review_praise` on leaky input, which is an unlisted delta. Add B5 (PIN): `reviews=None`, and a `review_summary` that is a string or None, pass through untouched, with no exception (the PYTHON-FASTAPI-J shape). Add B6 (PIN): alias `review_praise` == canonical `review_praise` on the §1b input.
* **K8 (F3).** Add an SSE tie case (57.3/57.3): verdict margin == complete overview == complete `scoring_v2.win_margin` == 0 under the flag. With 78/72 only, a post-nudge SSE computation is untested. Add the mutation row "SSE margin computed post-nudge → F3-tie".
* **K9 (mutation table additions).**
  * drop the `_metadata_override["verdict_scrubbed"]` line → A6
  * alias scrub placed before `:2009` → B6
  * alias rebuilt as `{"review_summary": …}` only (drops sibling keys) → B4/B6
  * scs helper called before `_verdict_winner_name` is fine; called AFTER it → A1 (`winner.name`)
* **K10 (loser guard, §4.4/D3).** Containment as specified keeps a caption that names ONLY the loser whenever the winner's name is a substring of the loser's. Measured under the prototype, winner `Galaxy S25`, loser `Galaxy S25 Ultra`, declaration `"Galaxy S25 Ultra"` → kept, flag OFF. Variant pairs of this shape are the app's common case. Mask the LONGER of the two normalised names first, then test the other:
  * loser is the superset: mask the loser → the winner is absent → drop
  * winner is the superset: mask the winner → the loser is absent → keep
  * both named: keep

  D3 must pin both directions. The present D3 text ("keeps the caption both ways") pins the defect.
* **K11.** E3 must use a score-leaking `winner_reason` on the mismatch (GPT 1 / scoring 0), so that "reconcile-replaced reason is not counted" is actually exercised.
* **K12 (single margin read).** scs reads the margin flag at `:4784` and the builder reads it again at `:4835`. A flip between the two breaks verdict == complete for that request. Read once in scs and route the value into the builder (e.g. a private builder kwarg), or record the race as accepted.

## R3. Missing items

1. **The rendered `review_praise` leak (R1.7).** It is the same class as `-04` but on a surface the phones DRAW, while `-04`'s own targets are unrendered. It needs a scope ruling (F-B).
2. **Flag-ON collateral in other units' pins (R1.1).** Neither the CI-order set nor the gate names them. W4-4's `test_05a/b/c/15` and W4-3's `test_10b` are PINs of THEIR flag-OFF state that implicitly pin THIS unit's margin semantics.
3. **Second user-visible doubled-brand site, not in `-07`'s surfaces.** `app/api/image_routes.py:376` `"Identified: {product['brand']} {product['name']}. "` (camera message) and `:350/:316` (logs and hash input). This is a follow-up at most; record it next to W4-12d.
4. **Caption reason fallback on pre-#99 stored rows.** A stored reason written for the GPT winner on a mismatch row can praise the loser by pronoun, and the loser guard checks names only. It is measured at 1/26 rows using the reason source (row 4); state it as a known residual of the caption flag.
5. **§8 preserve set is complete for the function grep.** A wider symbol grep (`reconcile_winner_prose|scrub_review_summary|dedup_brand_name|calibrate_score|win_margin|verdict_short|winner_name|retailer_quotes|review_summary`) adds 15 files outside the comm set. None of them imports a touched module (checked: scoring, review, retailer-quote and model files), so none is reachable. Recorded, no change.

## R4. Design risks

* **The standing rule vs the unflagged set.** The display-name dedup is visible Home/Profile copy (12/22 and 16/26 rows). The loser guard changes the visible Home caption on 2/26 rows, which then render the `reason_key` copy. Both rest on precedent (M21-W3 `7fb0b0d4`, W4-10 #176, #99), not on the letter of "every user-visible fork is flagged". The pre-scrub, the alias scrub and the metadata key are genuinely non-forking: 0 phone consumers are measured, and the complete payload changes only by the additive key.
* **Scale mixing in persisted rows** once the margin flag flips: raw floats before, calibrated ints after, no marker. The flag does not solve this; it only schedules it.
* **Telemetry signal quality.** `[VERDICT_SCRUB]` counts only full-empties (17/23 at the historical rate, so a WARNING on roughly 3 of 4 compares) and fires even when W4-4 then blanks the reason on an honest partial. The warning volume is noise-level for Sentry (WARNING is a breadcrumb only; the default LoggingIntegration event_level is ERROR), but the published scrub rate must exclude partials, or it overstates the GPT leak rate.
* **Idempotence dependency.** Double application (scs, then builder) is byte-safe only because `strip_score_internals` is idempotent after one pass (split on `(?<=[.!?])\s+`, join with a single space). A future change to that regex that is not idempotent would silently diverge verdict from complete. A1/A2 would catch it only for the fixtures used.

## R5. Questions Fable must rule on

* **F-A.** Under `ENABLE_SINGLE_VERDICT_MARGIN=true`, 22 existing pins of W4-4 and W4-3 go red. Either make them flag-aware in this unit (`monkeypatch.delenv("ENABLE_SINGLE_VERDICT_MARGIN")`, which is test-only and outside §5's "STOP" rule), or leave them red-under-ON and list them in gate 4 (K1)?
* **F-B.** The `review_praise` leak (R1.7). Should `build_review_praise` be fed `scrub_review_summary(...)` on both surfaces in THIS unit? That would be unflagged under the SIB-4/WS-5 precedent: the rendered copy changes only on leaky input, and 0/8 stored lines are affected. Or should it be split as W4-12f, with K7's ordering keeping this unit's alias scrub praise-neutral?
* **F-C.** With reason (c) refuted (R1.2), is `ENABLE_SINGLE_VERDICT_MARGIN` still worth a flag, or does it ship unflagged (spec F1)? The remaining arguments are the persisted-scale break and unseen third-party SSE/REST readers. Also rule on whether `scoring_v2.win_margin` may disagree with its own `overall_score` gap on nudged rows (K2), or whether the pre-nudge value belongs only in `overview.winner.margin` and the SSE frame.
* **F-D.** Loser guard semantics: longest-first masking (K10) vs the spec's containment, which pins the superset-variant false negative.
* **F-E.** Confirm the unflagged set under the standing rule (R4, first bullet): names dedup and loser guard by precedent.
* **F-F.** The spec's own F2–F7 stand as written. On F7: yes, commit the de-identified corpus as a fixture. Without it neither gate 3 nor K3/K4 is reproducible after scratchpads are cleaned.
