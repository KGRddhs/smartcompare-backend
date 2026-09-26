# W4-6a — rubric truth: stop reporting measured data as missing

Findings `PO-RUBRIC-01`, `PO-RUBRIC-02`, `PO-RUBRIC-03` (P1) and `PO-RUBRIC-08` (P2).
Flags `ENABLE_VALUE_DIM_PARTIAL_SIGNAL` ("V") and `ENABLE_TIE_IS_NOT_MISSING` ("T"),
both default OFF, both read PER CALL. The `PO-RUBRIC-08` guard ("G") is proposed
UNFLAGGED (open question 1). Base **`61585c58`** (= origin/main, confirmed with
`git rev-parse HEAD` in `sc-w4-specs`). Every line anchor below is at that SHA
(the review's anchors are from `76ace90`; drift table at the end). Every number
below was MEASURED in this run by the real functions through pytest under the
`qaren_netguard` plugin (`[netguard] blocked 0 network attempt(s)` on every probe
run), no `LIVE`, no network. The ON-state numbers come from a PROTOTYPE of the
design in a detached scratch worktree of `61585c58` (removed afterwards); the
prototype diff is kept for reference at
`.qa-s68/specs/W4_6A_probes/prototype_scoring_service.diff` — it is evidence, not
code to copy (its `W46A_PROTO_*` env hooks are measurement switches).

Only ONE production file changes: `app/services/scoring_service.py`.
`response_builder.py`, `structured_comparison_service.py` and the client are
untouched; the downstream consumers follow the emitted `missing_data` list.

## 0. How to re-run every number in this spec

Probes: `.qa-s68/specs/W4_6A_probes/test_probe_w46a.py` (scenarios + the 144-row
grid + the 6 recorded `comparison_baseline_d2*` fixtures, 12 flag states),
`test_probe_w46a_v2dims.py` (what the phone renders), `test_probe_w46a_mut.py`
(the V-reads-emitted-list mutation), `test_probe_w46a_bounds.py` (T sparsity
boundaries), `analyze.py` (pure JSON). Run from the worktree root (conftest loaded
as a plugin so credentials are neutralised before any `app.*` import):

```
SPW=<scratchpad>; cd <worktree>
W46A_OUT=$SPW/out.json PYTHONIOENCODING=utf-8 PYTHONPATH="$SPW/netguard;<probe dir>" \
  <venv python> -m pytest -p qaren_netguard -p tests.conftest -p no:cacheprovider -p no:randomly \
  -c pyproject.toml --rootdir=. --timeout=120 <probe dir>/test_probe_w46a.py -q
```

At `61585c58` the two flags do not exist, so all 12 states of the probe must be
equal to their non-new-flag counterpart — measured: OFF == V == T == VT, and
R == RV == RT == RVT, on all 164 records (scenarios 14 + grid 144 + d2 6).
Canonical-JSON sha256 of the base records (probe shape): OFF
`d07801178e833bc7cd757f93d3a6d1c05f6164aa78034f72f26643474399b545`, R (renorm ON)
`e18fc89f05840040ffb05084960996a333dfd56adc38c875b1f852723f9609b0`, S (spec-field
norm ON) `e9d1aa15d9a1e92ea1f757249d7e86d2bdf10240acf82603e123bfcffb56d8f8`. The
prototype reproduced all three OFF/R/S record sets exactly (flag-OFF identity of
the design, measured).

Test products (the probe's builders; the red tests reuse them verbatim):
`ELEC_SPECS` = the 11-field electronics schema fully populated (`display 6.1 inch
OLED`, `processor A17 Pro`, `ram 8 GB`, `storage 256 GB`, `battery 4000 mAh`,
`rear_camera 48 MP`, `front_camera 12 MP`, `os iOS 18`, `connectivity 5G, Wi-Fi 7`,
`weight 171 g`, `water_resistance IP68`); `FULL_FC` = `{specs_verified: 11,
specs_likely: 0, specs_flagged: 0, specs_unverified: 0, price_verified: True,
review_sentiment_consistent: True}`; brands `Brand A`/`Brand B`, names
`Phone X`/`Phone Y`, `source_method local_bhd`, BHD prices.

## 1. The defect, measured

### 1a. PO-RUBRIC-01 — the dimension that decides the winner is stamped missing and resolves N/A

Mechanism at `61585c58`:

| step | anchor | what it does |
|---|---|---|
| value-dim missingness | `_signal_missing_for` `:318`, clause `:330-331` | `signal == "value"` ⇒ missing when `_spec_missing` **OR** `_price_missing` |
| value-dim number | module `_compute_value_score` `:1163`, `:1195-1207` | spec gone + price present ⇒ returns the REAL `price_score` (not the sentinel) |
| stamp | `_normalize_scores` loop `:2230-2241` (call at `:2240`) | sets `_{dim}_missing` from the OR rule |
| emitted list | `compute_scores` `:1428`, `:1434` | `missing_data` = every dim with `_{dim}_missing` |
| N/A | `compute_dimension_winners` `:2439`, `:2473-2474` | both-sided missing ⇒ `{"winner": "N/A", "margin": None}` |
| verdict prompt | `build_scores_summary` `:2838`, lead word `:2909`, leaders `:2913-2920` | prints the lead and the N/A leaders in one block |

Measured, pair **R01** (identical `ELEC_SPECS`, 4.5 stars / 900 reviews, `FULL_FC`
on both, prices 50.0 vs 52.0 BHD), all flags unset:

| field | product_0 | product_1 |
|---|---|---|
| `overall` | 72.0 | 58.0 |
| `win_margin` | 14.0 (winner_index 0) | |
| `value_score` breakdown | 100.0 | 30.0 |
| per-dim contribution to the margin (`(b0-b1)·w`) | `value_score` **14.0** (= 0.20 × 70), every other dim 0 | |
| `missing_data` | `performance_score, value_score, build_quality_score, ecosystem_score` | same |
| `dimension_winners` | `value=N/A, performance=N/A, build_quality=N/A, ecosystem=N/A, feature=tie, futureproof=tie` | |
| raw signals | `spec_raw 378.0`, `reliability_raw 1.0`, `popularity_raw 0.9847`, `price_raw 50.0` | `378.0`, `1.0`, `0.9847`, `52.0` |
| `count_missing_dim_cells` | 8 / 12 | |

`build_scores_summary` (the text handed to the gpt-4o verdict), verbatim:

```
Score winner: Brand A Phone X (clear lead)
Dimension leaders: performance=N/A, value=N/A, build quality=N/A, features=tie, ecosystem=N/A, future-proofing=tie
```

**R01b** (same but NO specs on either side): byte-identical numbers (`[72.0, 58.0]`,
14.0, same four stamps, same summary). `raw_spec [None, None]` — here the spec is
genuinely absent, so only the value half of the defect applies.

**HOLDS** — the review's `[72.0, 58.0]`, `14.0`, `100.0/30.0` reproduce to the digit.

### 1b. PO-RUBRIC-02 — the B0-A array tie-collapse turns equal measured signal into "missing"

Three collapse blocks in `_normalize_scores` (`:2072`): reliability `:2125-2132`,
popularity `:2133-2140`, spec `:2154-2161`. Each fires on `len(set(scores)) == 1
and scores[0] != MISSING_SCORE`, replaces both values with `MISSING_SCORE = 50`
(`:297`) and sets `_<sig>_missing` on every product. The comment (`:2115-2124`)
justifies it with "ZERO genuine non-MISSING ties observed" on a
24-query 2026-06 sample.

Measured, pair **R02** (as R01 but prices 50.0 / 50.0):

| field | value (both products) |
|---|---|
| raw | `spec_raw 378.0`, `reliability_raw 1.0`, `popularity_raw 0.9847` |
| breakdown | `performance 50`, `value 75.0`, `build_quality 50`, `feature 90.0`, `ecosystem 50`, `futureproof 90.0` |
| `missing_data` | `performance_score, value_score, build_quality_score, ecosystem_score` (**4/6**) |
| `overall` | 67.0 / 67.0 |
| `scoring_v2.dimensions` rows (`build_dimensions_v2`) | 5: `price, reviews, value, feature, futureproof` — performance/build_quality/ecosystem silently omitted |

A near tie collapses too: battery `4100 mAh` vs `4000 mAh` (spec_raw gap under the
8 % `_DEFAULT_DIM_GAP_TOLERANCE` ⇒ both 65.0) ⇒ the same 4 stamps. Saturated
popularity collapses: `review_count` 1500 vs 2500 ⇒ both `popularity_raw 1.0` ⇒
`ecosystem_score` stamped.

**HOLDS** (4/6 dims, all three collapsed dims at 50, reliability measured 1.0).

### 1c. PO-RUBRIC-03 — fashion/other have no numeric spec fields

`HIGHER_IS_BETTER_BY_CATEGORY` / `LOWER_IS_BETTER_BY_CATEGORY` `:262-284`:
`fashion` `:270`/`:282` and `other` `:271`/`:283` are `set()`, so `_score_specs`
(`:1777`) takes the presence credit `total_score += 1` (`:1819`/`:1822`) for every
populated field and returns exactly 1.0 above `CATEGORY_MIN_COVERAGE` (`:1219`).

Measured, pair **R03** (fashion, 10/10 fields each): `Maison A Oxford One` —
`material "Full-grain Italian calfskin leather"`, `craftsmanship "Hand-welted
Goodyear construction"`, `origin "Made in Italy"`, 4.6 stars / 220, fact_check
8 verified + 2 likely, 180.0 BHD — vs `Brand B Oxford Two` — `"PU synthetic
leather"`, `"Glued sole, machine-made"`, `"Made in China"`, 3.9 / 1500, 5 verified +
5 unverified, 25.0 BHD:

| field | Oxford One | Oxford Two |
|---|---|---|
| `spec_raw` | **1.0** | **1.0** |
| `craft_score` | 50 (stamped) | 50 (stamped) |
| `cpw_score` (value) | 30.0 (stamped) | 100.0 (stamped) |
| contribution of `cpw_score` | −7.0 and `dimension_winners.cpw_score = N/A` | |
| `overall` | 72.8 | 75.7 (winner, margin 2.9) |

**R03c** (other, 7/7 fields: anodised aluminium case 250 BHD vs ABS case 30 BHD):
`spec_raw 1.0 / 1.0`, `function_score 50/50` stamped, `value_score 30.0/100.0`
stamped with contribution −10.5 and `N/A`, overall `[69.8, 74.2]`.

**HOLDS** (`1.0 == 1.0`; the value leg of these categories is also an instance of 1a).
`ENABLE_SPEC_FIELD_NORM` does NOT close it: with it ON, R03/R03c are unchanged
(craft/function 50/50 stamped) — the second vote's statement, re-measured.

### 1d. PO-RUBRIC-08 — the runner-up card names a data void as the loser's strength

`_loser_strongest_dim` (`:2625`, loop `:2644`) picks the loser's highest breakdown
value and never consults `missing_data`, so the 50 sentinel competes. It is
reached from `compute_tradeoff_pairs` (`:2556`, fallback call `:2601`) at all three
orchestrator sites (`structured_comparison_service.py:3392`, `:4004`, `:4768`,
each passes `scores=`), and the first pair's `loser_wins` becomes user-facing copy
via `response_builder.deterministic_verdict_fields` (`:152`, string at `:198`):
the hard-cap partial fill (`_deterministic_partial_verdict`, `scs:8416`) and, under
`ENABLE_WINNER_PROSE_RECONCILE`, the reconcile path. W4-10 (#176) made this MORE
reachable: before it, brand-prefixed names never matched and the fallback returned
`[]`.

Measured, pair **R08d** (winner: 12 GB/512 GB/5000 mAh/200 MP phone, 4.8 / 5000,
fact_check `{specs_flagged: 10}`, 40.0 BHD; loser: 2 spec fields, 1.0 star, 1
review, NO fact_check, 60.0 BHD): loser breakdown
`build_quality 50 (sentinel, missing)`, `performance 45.0`, `value 40.5`,
`feature 35.0`, `futureproof 20.0`, `ecosystem 0`; winner `build_quality 0`.
`tradeoffs[0].loser_wins = {dimension: build_quality_score, margin: 50}` ⇒
`key_tradeoff = "Brand B Phone Y stays competitive on build quality."` With
`{specs_verified: 1, specs_flagged: 9}` (**R08e**) the margin is 40.0.
**HOLDS** — the verifier's 50.0 and 40.0 reproduce; the finder's exact 44.0 depends
on an unrecorded fact_check shape and was not reproduced.

### 1e. The corpus numbers

* **"53.7 % of dimension cells carry a missing stamp" — UNVERIFIABLE offline.** The
  review's 2,016-run grid is recorded only as 16 pattern NAMES
  (`journals/wf_4127a8d5-5b2.journal.jsonl`); the product constructions are not on
  disk. What IS measured here: a reconstruction of the same 16 pattern names × 9
  categories (144 rows, `_grid()` in the probe) at prod flags gives
  **388 / 864 product_0 cells = 44.9 %** (both products 693/1728 = 40.1 %), and
  16 / 144 rows have a > 1.0-point margin contributor that resolves N/A.
* **The only recorded real payloads on disk** — the 6
  `tests/fixtures/comparison_baseline_d2*.json` (iPhone 17 vs S25 Ultra ×2, Nike AF1
  vs Stan Smith, Tom Ford Tobacco Vanille vs Sauvage, Garnier vs Bioderma, Centrum vs
  One A Day), re-scored at `61585c58` from their `products` block: **16 / 72 cells
  stamped (22.2 %), and every one of the 16 sits on a MEASURED raw signal**
  (ecosystem/presentation/style/sensory = `popularity_raw 1.0/1.0`; Nike/Adidas
  craft = `spec_raw 1.0/1.0`; Garnier/Bioderma evidence = `reliability_raw
  0.47/0.47`; Nike/Adidas cpw = the 1a value rule, with a > 1-point N/A contributor).
  The payloads as recorded carried `missing_data: None` on 11 of 12 products — they
  predate the B0-A v2.1/v2.2 collapse; the stamps are HEAD's.
* The 27 recorded production bodies the rubric lane used are not on disk.

## 2. What already exists — reuse it, do not reinvent it

* **Flag idiom** — `_spec_field_norm_enabled()` `:450` / `_missing_dim_renorm_enabled()`
  `:471`: `os.environ.get(NAME, "").strip().lower() in ("1","true","yes","on")`,
  read per call, never at import. Copy verbatim for both new readers. Do NOT copy
  `_bundle_c_scoring_enabled` (`:413`, process-cached).
* **Missingness is flag-sourced, never value-sourced** — the S3 L3 v2 "gate finding B"
  rule is honoured at four sites (`_signal_missing_for`, `_dim_from_category_lookup`
  `:3324`/`_was_missing`, `compute_dimension_winners` `:2463-2464`,
  `count_missing_dim_cells` `:3757`/`_cell_missing`). They all read the emitted
  `missing_data` list, so changing WHAT is emitted is the whole unit for V — no
  consumer needs an edit.
* **The genuine-tie path already exists** — `_normalize_dimension` `:2306` returns
  `_DIM_NORM_TIE_DAMPENED = 65.0` (`:312`; 70 under `DISABLE_DIM_NORM_DAMPENING`)
  for a non-missing tie; `_normalize_direct` `:2387` returns the measured value ×100.
  T only stops the collapse from overwriting those values.
* **Sparsity vocabulary already in the file** — `_score_reliability` `:1957`
  (bucket total), `_score_popularity` `:1988` (`review_count` vs `source_ratings`),
  `_score_specs` schema/`CATEGORY_MIN_COVERAGE` (`:1219`), `NON_SCORING_SPEC_KEYS`
  `:22`. The T predicates are these, restated on `products_data` (which
  `_normalize_scores` already receives).
* **Coupled-reader precedent** — W4-2's reader is coupled to W4-1's flag. T is coupled
  to `ENABLE_MISSING_DIM_RENORM` the same way (design §3.2).
* **Golden precedent** — the four `tests/fixtures/*_flag_off_golden.json` and the
  auditable generator `tests/fixtures/_gen_behavioral_flag_off_golden.py`.

## 3. The design

### 3.1 `ENABLE_VALUE_DIM_PARTIAL_SIGNAL` (V) — the emitted list tells the truth about the value dim

Reader `_value_dim_partial_signal_enabled()` next to `_missing_dim_renorm_enabled`.

**Flag ON changes exactly one thing: the list `compute_scores` EMITS as
`missing_data`.** At `:1428`, build the legacy list exactly as today, keep it in a
local `legacy_missing[product_key]`, and when V is ON emit it minus every
value-signal dim (`_DIMENSION_SIGNAL_MAP[category][dim] == "value"`) whose product
does NOT have BOTH `_spec_missing` and `_price_missing` — i.e. the dim is reported
missing only when `_compute_value_score` actually returned the sentinel.

**Every read of missingness INSIDE `compute_scores` keeps the legacy semantics:**
* the renorm pre-pass (`:1353`) and `sentinel_only` (`:1388`) read the raw
  `_{dim}_missing` flags, which V does not touch (`_signal_missing_for` stays as is);
* the price-authority exemption (`:1475-1476`, `md = result_products[pk].get("missing_data")`)
  and the renorm parity tie-break (`:1501`) must read `legacy_missing`, not the emitted
  list.

Why: the review's literal fix (change `_signal_missing_for`'s OR to AND) was
prototyped and measured to move arithmetic —
* with `ENABLE_MISSING_DIM_RENORM` ON it flips **9 / 9** `nodata_vs_measured_good`
  grid rows to the NO-DATA product (`[75.0, 68.0]` vs R's `[55.0, 79.9]`): the void's
  price-only value (75.0) stops being one-sided and is compared against the measured
  product's spec-blended value (68.0);
* reading the emitted list at the authority exemption moves a no-data product on an
  `estimated` price from 55.0 to 51.0 (`nodata_estimated_vs_measured`, probe 3).

With the emitted-list-only design, measured over all 164 records: **OFF→V and R→RV
change 0 `overall`, 0 `win_margin`, 0 `winner_index`, 0 `breakdown` values**, and
T→VT, RT→RVT likewise 0. V is a pure truth-of-labelling flag.

Effect ON (measured):
* R01/R01b: `value_score` leaves both lists; `dimension_winners.value_score =
  "Brand A Phone X"`; summary line becomes
  `Dimension leaders: performance=N/A, value=Brand A Phone X, build quality=N/A, features=tie, ecosystem=N/A, future-proofing=tie`;
  overall stays `[72.0, 58.0]`, "clear lead" stays — and is now attributed.
* Grid: rows with a > 1.0-point N/A contributor 16 → **0**; p0 stamps 388 → 300
  (34.7 %). Under V the invariant "a dim N/A on both sides contributes exactly 0" holds
  BY CONSTRUCTION (every remaining both-sided-missing dim carries the 50 sentinel on
  both sides), so `build_scores_summary` needs no edit.
* 22 / 144 grid rows change `key_tradeoff` (value dims become eligible tradeoff
  entries); 0 badges change.
* Phone-visible: `build_dimensions_v2` (`:3669`) skips `value_score` and every key
  containing `value_` (`:3717`), but NOT `cpw_score` — so fashion gains a `cpw` row
  (R03: `cpw 30.0 / 100.0, winner 1`; the recorded Nike/Adidas pair too). 3 of 20
  probe payloads change rows; all fashion.

### 3.2 `ENABLE_TIE_IS_NOT_MISSING` (T) — a tie on real evidence stays a real tie

Reader `_tie_is_not_missing_enabled()`: returns False whenever
`_missing_dim_renorm_enabled()` is True (coupled, see below), else the env parse.

**Flag ON: each of the three collapse blocks fires only when the tied signal is
SPARSE on EVERY product** (else the tied values stand, no `_<sig>_missing` is set):
* reliability (`:2125`): sparse ⇔ `fact_check` not a dict, or
  `specs_verified + specs_likely + specs_flagged + specs_unverified < 3`;
* popularity (`:2133`): sparse ⇔ `int(review_count) > 0` is not true (None, 0,
  unparseable) — popularity then comes from `source_ratings` alone;
* spec (`:2154`): sparse ⇔ `specs` not a dict, or populated-schema-fields /
  schema-fields `< CATEGORY_MIN_COVERAGE[schema_key]` (same field selection as
  `_score_specs`: `CATEGORY_SPEC_SCHEMAS[schema_key]` minus `NON_SCORING_SPEC_KEYS`,
  a field counts when truthy and `!= "N/A"`).
Name the constant `_SPARSE_FACT_CHECK_BUCKETS = 3`. Helpers take the product dict
(`products_data[i]`), never the raw scores.

Boundary rows, measured on the prototype (identical R02-shaped pairs, one knob moved):

| knob (both products) | HEAD | T ON |
|---|---|---|
| fact_check `{specs_verified: 2}` | 4 dims stamped | `build_quality_score` stamped (sparse, collapse kept) |
| fact_check `{specs_verified: 3}` | 4 stamped | 0 stamped, build_quality 100/100 |
| `review_count None` + 2 source ratings | 4 stamped | `ecosystem_score` stamped (sparse) |
| `review_count 0` | 4 stamped | `ecosystem_score` stamped (sparse) |
| `review_count 1500` / `2500` (both `popularity_raw 1.0`) | 4 stamped | 0 stamped, ecosystem 100/100 |
| 5 of 11 spec fields (0.4545 < 0.5) | 4 stamped | `performance_score, value_score` stamped (sparse) |
| 6 of 11 spec fields (0.5455) | 4 stamped | 0 stamped, performance 65.0/65.0 |
| battery 4100 vs 4000 (near tie → both 65.0) | 4 stamped | 0 stamped |
| R02c: 2/11 fields, fact_check `{unverified: 1}`, `review_count None` | 4 stamped | 4 stamped (B0-A behaviour kept for sparse evidence) |

Effect ON (measured):
* R02: `missing_data None` on both; `build_quality 100`, `performance 65.0`,
  `ecosystem 98.5`, `feature 75.0`, `value 68.0`; overall `[78.7, 78.7]` (was 67.0);
  `scoring_v2.dimensions` 5 → 8 rows (+`performance 65.0/65.0`,
  `build_quality 100/100`, `ecosystem 98.5/98.5`); calibrated display 78 → 84.
* R01: overall `[80.2, 76.0]`, **margin 14.0 → 4.2** ("clear lead" → "narrow lead"):
  with the spec tie no longer erased the value dim is the designed 0.6·spec + 0.4·price
  blend (75.5 vs 54.5) instead of price alone (100 vs 30). Same winner.
* R03 (fashion): craft 65.0/65.0 not stamped; cpw 38.0/54.0 (cross-tier formula,
  `is_cross_tier` true for 180 vs 25 BHD); overall `[75.8, 74.0]` — **the winner flips
  from Oxford Two (25 BHD PU) to Oxford One (180 BHD leather)**, margin 1.8.
  R03c (other): `[72.4, 68.9]` — **flips from the ABS case to the aluminium case**.
* Grid (144 rows): p0 stamps 388 → 189 (21.9 %); `overall` changes on 66 rows,
  `win_margin` on 24, value badges on 17, `key_tradeoff` on 30; 0 winner flips among
  rows with a non-zero base margin. The 6 recorded d2 payloads: 16 → 0 stamps,
  no winner flip, fashion margin 10.6 → 6.0, overalls rise 0.0–14.3.
* T ALONE does NOT close 1a for a genuinely spec-less pair (R01b under T: `value_score`
  still stamped and N/A while carrying 14.0) — V is needed for that. VT closes both:
  grid N/A contributors 0, p0 stamps 153 / 864 (17.7 %).

**The RENORM coupling (binding part of the design, measured).** Without it, T with
`ENABLE_MISSING_DIM_RENORM` ON re-opens the #101 inversion the renorm flag exists to
close: R→RT flips **8 / 9** `unrated_vs_2star` grid rows back to the UNRATED product,
and six existing renorm pin nodes of `tests/test_scoring_missing_dim_renormalize.py` redden —
`test_no_rating_does_not_beat_two_star_rating` (measured 59.1 < void 62.4) and
`test_issue_headline_two_star_beats_void_with_estimated_price[measured_first|void_first]`
(55.1 < 58.4), plus `test_one_star_does_not_beat_no_rating`,
`test_effective_weights_sum_to_one`, `test_renorm_composes_with_bundle_c_both_states`.
Cause: un-collapsed equal specs leave `spec_secondary` one-sided-partial (the void's
feature = spec only 65.0, the measured product's = 0.6·65 + 0.4·40 = 55.0). With the
coupled reader the prototype keeps every renorm test green with T set, and RT ≡ R
record-for-record. Lifting the coupling belongs to W4-6b (the #101 call).

**Composition with `ENABLE_SPEC_FIELD_NORM` (S):** allowed. S→SVT: 0 winner flips,
61 margin changes, p0 stamps 475 → 153. The S-only pin
`tests/test_scoring_spec_field_normalization.py::test_identical_specs_still_collapse_to_tie`
asserts `_spec_missing is True` for identical specs and goes red if T is ALSO set —
it is an S-alone pin, stays untouched, CI never sets T; the S+T behaviour is pinned
by this unit's test 16.

### 3.3 The `PO-RUBRIC-08` guard (G) — proposed UNFLAGGED

In `_loser_strongest_dim` (`:2625`): skip a dim that is in the LOSER's `missing_data`
(read `scores[loser_key].get("missing_data") or []`) or absent from the winner's
breakdown; return None when nothing is left (the existing `if best_dim is None:
return None` then makes `compute_tradeoff_pairs` return `[]` and `key_tradeoff` "").
Measured: R08d/R08e `loser_wins` → `performance_score` margin 0 ⇒
`"Brand B Phone Y stays competitive on performance."`; 0 / 144 grid rows change;
0 results of the 71-file scoring symbol set change (1,892 passed, 2 failed = the
2 baselined `test_personalization_bundle_c` ids, 35 xfailed — identical to G unset).
Rule it satisfies to ship unflagged: the output changes ONLY when today's output names
a dimension the same payload declares missing (a self-contradiction); every loser dim
backed by a measured value is chosen exactly as today (the precedent class of W4-9/W4-10
and M13-10: a defect correction with no fork for legitimate traffic). It composes with
V/T automatically (it reads the emitted list). Fable decides (open question 1).

### 3.4 Logs (flag ON only — flag OFF emits nothing new)
* T: at most one INFO per `compute_scores` call when a collapse was SKIPPED:
  `[scoring] W4-6a tie kept: signals=<reliability,popularity,spec subset> category=<cat>`;
  and one when a collapse fired UNDER T because the evidence was sparse:
  `[scoring] W4-6a tie collapsed (sparse): signals=<...> category=<cat>`.
* V: at most one INFO per call when a value dim was un-stamped:
  `[scoring] W4-6a value dim partial: dim=<dim> products=<idx list> category=<cat>`.
* G: DEBUG only (unflagged; no INFO volume change).

### 3.5 Why flag OFF is byte-identical
Both readers are consulted only inside `if` branches that are skipped when OFF: the
three collapse conditions gain an `and (not _tie_is_not_missing_enabled() or all(...))`
term whose first operand short-circuits to True; the emitted list equals the legacy
list; the two internal reads of `legacy_missing` equal what `result_products[...]
["missing_data"]` held before (same list object contents). No new result key, no key
reorder (`result_products[product_key]` dict literal unchanged), no new log line OFF.
G is the only OFF-visible change and it touches only `tradeoffs` / `key_tradeoff`.

### 3.6 The phones (preview OTA group `561d2cba` from `ab9442ae`)
`git diff --stat ab9442ae 61585c58 -- SmartCompareApp/src` is EMPTY, so HEAD's client
== the phones'. No payload key is added or removed; only VALUES of existing keys move:
`scoring.scores.product_i.missing_data` (typed, never rendered — zero references in
`SmartCompareApp/src` outside `types.ts`), `scoring.dimension_winners` (typed at
`types.ts:253/:373`, not rendered), `overview.tradeoffs` (typed `types.ts:209`, not
rendered), `overview.winner.key_tradeoff` (rendered: `ResultsContent.tsx:171`,
`RunnerUpWinsCard.tsx` caption), `scoring_v2.dimensions` rows (rendered by
`DimensionBars.tsx`; `RunnerUpWinsCard.tsx:50-62` `runnerUpWinningDims` filters
`caption_key === 'limited_data'` and non-number scores — the 8-row shape T produces is
the shape every full-data electronics pair already ships, capped at 8 by
`build_dimensions_v2`), `scoring_v2` overall (T raises raw overall, e.g. R02 67.0 →
78.7, display 78 → 84), `metadata.missing_dim_cells` (the eval KPI; drops under both
flags). SSE and sync carry the same `scoring_result`. Compatible with the phones;
no OTA needed.

## 4. Files

**Touch:**
* `app/services/scoring_service.py` — two readers; `_SPARSE_FACT_CHECK_BUCKETS`; three
  sparsity helpers; three collapse conditions (`:2125`, `:2133`, `:2154`); the emitted
  list at `:1428` + `legacy_missing` reads at `:1475` and `:1501`; the G guard in
  `_loser_strongest_dim` (`:2644` loop).
* NEW `tests/test_scoring_rubric_truth.py` (the red tests, §6).
* NEW `tests/fixtures/rubric_truth_flag_off_digests.json` — captured at BASE (§8 gate E2).
* NEW `tests/fixtures/rubric_truth_flag_on_golden.json` +
  `tests/fixtures/_gen_rubric_truth_flag_on_golden.py` (generator; `build_golden()`
  imports `app.*` lazily inside the function; agents run it only through a pytest
  probe under the guard, never as a bare script — s68 rule).
* `CLAUDE.md` flag rows + `.claude/skills/qaren-scoring/SKILL.md` one line each — by the
  orchestrator at merge time (`tests/test_behavior_dimension_translation.py` greps the
  `scoring_method` enum line in both files; do not reflow that line).

**Must NOT touch:** `_signal_missing_for` (its OR rule is the INTERNAL legacy truth
the renorm path reads), `_compute_value_score` (both), `_normalize_price`,
`_normalize_dimension`, `_normalize_direct`, `_normalize_review`, `_score_specs`,
`_score_specs_fields`, `_apply_spec_field_normalization`, the renorm pre-pass/
`sentinel_only` logic (`:1347-1408`), `compute_dimension_winners`,
`build_scores_summary`, `build_dimensions_v2`, `_dim_from_category_lookup`,
`count_missing_dim_cells`, `compute_tradeoff_pairs` (only its helper changes),
`apply_value_badges`/`compute_value_badge`, `HIGHER/LOWER_IS_BETTER_BY_CATEGORY`,
`CATEGORY_*` tables, `MISSING_SCORE`; `response_builder.py`,
`structured_comparison_service.py`, `price_service.py`; the four existing
`*_flag_off_golden.json` (byte-unchanged, shas in §8); every existing test file;
`SmartCompareApp/`; migrations; `tests/.pre_impl_failures.txt`.

## 5. Preserve (every test file that pins the touched functions — grep at `61585c58`)

Run flag-unset, all green except baselined nodes:
* Goldens: `tests/test_scoring_missing_dim_renormalize.py`,
  `tests/test_scoring_spec_field_normalization.py`,
  `tests/test_value_badge_category_dims.py`, `tests/test_behavior_dimension_translation.py`.
* Collapse / missingness pins (`grep -rlE "_normalize_scores|B0-A|phantom|_reliability_missing|_popularity_missing|_spec_missing|MISSING_SCORE" tests`,
  scoring-relevant subset): `test_dim_phantom_tie_followup.py`,
  `test_missing_score_collision_v2.py`, `test_dim_silent_omission.py`,
  `test_dim_winner_one_sided_missing.py`, `test_missing_dim_coverage.py`,
  `test_normalization_denoise_v2.py`, `test_scoring_missing_propagates_none.py`,
  `test_scoring_edge_cases.py`, `test_bundle_c_feature_flag.py`,
  `test_scoring_calibration_bundle_c.py`, `test_scoring_dimensions_v2.py`,
  `test_category_keystone_scoring.py`, `test_dim_scoring_no_default_literals.py`,
  `test_calibrate_band.py`, `test_lane1_helpers_unit.py`, `test_scoring_service.py`.
* Tradeoffs / summary / winners: `test_tradeoffs_dedup_parity.py` (W4-10),
  `test_winner_prose_reconciliation.py`, `test_m13_04_full_stream_deadline.py`,
  `test_streaming.py`, `test_category_dimensions.py`, `test_fragrance_content_quality.py`.
* Missing-data consumers upstream: `test_prescoring_showable_guard.py` (W4-3; pins
  `missing_data` shapes), `test_personalization_bundle_c.py` (2 nodes baselined).

**Flag-ON sensitivity of the Preserve set (measured on the prototype, 71-file symbol
set):** with V set, 14 extra nodes redden (renorm golden fashion/fragrances/other,
spec golden fashion/other, `test_prescoring_showable_guard` ×3 —
`test_01_red_headline_both_google_numeric_specs`,
`test_03_red_fragrance_missing_data_pins_something`,
`test_r7b_pin_current_manufactured_cross_tier` — and `test_tradeoffs_dedup_parity`
×6; run: 16 failed / 1,878 passed / 35 xfailed incl. the 2 baselined); with T set
(coupled), 15 extra (goldens 5, `test_identical_specs_still_collapse_to_tie`,
`test_tradeoffs_dedup_parity` ×9; run: 17 failed / 1,877 passed / 35 xfailed). Uncoupled
T adds the 6 renorm acceptance pins of §3.2 (23 failed / 1,871 passed). These are FLAG-OFF pins that do not clear the new
env names; CI never sets them. **Do not edit them.** Consequence recorded for ops: a
developer `.env` carrying either flag reddens them locally.

## 6. Red tests — `tests/test_scoring_rubric_truth.py`

Autouse fixture: `monkeypatch.delenv` both new flags plus `ENABLE_MISSING_DIM_RENORM`,
`ENABLE_SPEC_FIELD_NORM`, `ENABLE_BUNDLE_C_SCORING`, `ENABLE_CATEGORY_VALUE_BADGE`,
`ENABLE_BEHAVIORAL_DIM_TRANSLATION`, `DISABLE_DIM_NORM_DAMPENING`,
`WINNER_DIM_GAP_TOLERANCE`, `WINNER_PRICE_AUTHORITY_POINTS`,
`WINNER_VALUE_WEIGHT_SCALE`, `ENABLE_WINNER_PROSE_RECONCILE`, and
`monkeypatch.setattr(scoring_service, "_BUNDLE_C_SCORING_FLAG", None)`. Always a FRESH
`ScoringService()` — never `get_scoring_service()` and never setattr on the singleton
(#186 class). Names via `text_sanitize.dedup_brand_name`, as `compute_scores` spells
them. Builders = the probe's (`§0`). RED = fails at `61585c58` for the stated reason;
PIN = green at `61585c58` and must stay green.

*Readers*
1. RED `test_readers_default_off_and_parse` — both readers: unset/`""`/`"false"`/`"0"`
   ⇒ False; `"true"`, `" TRUE "`, `"On"`, `"1"`, `"yes"` ⇒ True. RED: AttributeError.
2. RED `test_tie_reader_inert_under_missing_dim_renorm` — T=`true` + renorm `true` ⇒
   `_tie_is_not_missing_enabled()` False; renorm unset ⇒ True.

*PO-RUBRIC-01 (V)*
3. RED `test_decisive_dim_is_never_reported_missing[identical_spec|no_spec]` — V ON,
   R01 and R01b: `value_score` in neither `missing_data`; `dimension_winners["value_score"]["winner"] == "Brand A Phone X"`;
   for every dim with |(b0−b1)·w| > 1.0, the dim is in neither list and not N/A.
   RED: value in both lists, N/A, contribution 14.0.
4. RED `test_scores_summary_names_the_value_leader` — V ON, R01: the `Dimension leaders`
   line equals `Dimension leaders: performance=N/A, value=Brand A Phone X, build quality=N/A, features=tie, ecosystem=N/A, future-proofing=tie`
   and `Score winner: Brand A Phone X (clear lead)`. RED: `value=N/A`.
5. PIN `test_value_flag_off_identity_R01` — OFF: the four stamps, `value=N/A`, both
   summary lines verbatim as in §1a, overall `[72.0, 58.0]`, margin 14.0.
6. PIN `test_value_flag_is_arithmetic_neutral` — over the 14 scenarios + the 144-row
   grid + `nodata_estimated_vs_measured` (probe 3: product A = price only, 50.0 BHD
   `estimated`; B = `ELEC_SPECS`, 3.0 / 40, `{specs_verified: 5}`, 50.0): V ON vs OFF
   and (renorm ON + V) vs renorm ON — `overall`, `win_margin`, `winner_index`,
   `breakdown` equal. Anchor value: `nodata_estimated_vs_measured` overall
   `[55.0, 68.8]` in both. Green at HEAD (V inert); it is the mutation-killer for M4.
7. RED `test_value_missing_only_when_both_legs_gone` — V ON, electronics pair vs a
   measured partner: price-only product ⇒ `value_score` not in its list; spec-only
   (no price) ⇒ not in its list; neither ⇒ in its list. RED on the first two.
8. RED `test_no_na_dim_contributes_to_margin_grid` — V ON and VT ON over the 144 grid
   rows: 0 rows with a dim |contribution| > 1.0 resolving N/A. RED: 16 rows
   (`sparse_vs_sparse` ×9, `both_full`/`extreme_price_ratio`/`one_missing_price` in
   fashion and other, `supplements|both_no_price`).

*PO-RUBRIC-02 (T)*
9. RED `test_equal_strong_signal_is_not_reported_missing` — T ON, R02: `missing_data`
   None on both; `build_quality_score == 100`, `performance_score == 65.0`,
   `ecosystem_score == 98.5`, overall `[78.7, 78.7]`. RED: 4 stamps, 50s, 67.0.
10. RED `test_saturated_popularity_tie_is_not_missing` — T ON, the `products` of
    `tests/fixtures/comparison_baseline_d2_post_bucket_a__electronics.json`:
    `ecosystem_score` in neither list, 100/100. RED: stamped.
11. RED `test_near_tie_spec_is_not_missing` — T ON, battery 4100 vs 4000: 0 stamps,
    performance 65.0/65.0. RED: 4 stamps.
12. PIN `test_sparse_tie_still_collapses` — T ON, R02c: the same 4 stamps as HEAD, the
    same breakdown. Green at HEAD.
13. RED/PIN `test_sparsity_boundaries` — parametrized over the 8 boundary rows of §3.2
    with the T-ON expected column. The "kept" rows are RED at HEAD, the "sparse" rows
    PIN (equal to HEAD).
14. RED `test_tie_flag_restores_scoring_v2_rows` — T ON, R02: `build_dimensions_v2`
    keys `price, reviews, value, performance, build_quality, feature, ecosystem,
    futureproof` with `performance 65.0/65.0`, `build_quality 100/100`,
    `ecosystem 98.5/98.5`. RED: 5 rows.
15. PIN `test_tie_flag_inert_under_renorm` — renorm ON + T ON ≡ renorm ON: full
    `compute_scores` output equal over the 144 grid rows + 14 scenarios, and
    `electronics|unrated_vs_2star` keeps R's `[58.3, 58.3]`, winner 1. Green at HEAD;
    kills M8 (uncoupled: 8 flips, e.g. that row becomes `[70.9, 68.4]`, winner 0).
16. RED `test_tie_flag_composes_with_spec_field_norm` — S ON + T ON, identical specs
    (the fixture of `test_identical_specs_still_collapse_to_tie`): `_spec_missing` not
    set, spec 65/65, `performance_score` not in `missing_data`. RED: collapsed.

*PO-RUBRIC-03*
17. RED `test_fashion_other_spec_dim_not_reported_missing[fashion|other]` — T ON, R03
    and R03c: `craft_score` / `function_score` in neither list, 65.0 == 65.0, and (VT
    ON) `cpw_score` / `value_score` in neither list. RED: 50/50 stamped.
18. XFAIL(strict=True) `test_spec_dim_can_separate_two_fashion_products` — the review's
    red test (c), kept as a pin OF THE LIMIT: VT ON, R03 ⇒ assert
    `|craft_0 − craft_1| > 3.0`. Fails today (50 == 50) and under this unit (65.0 ==
    65.0); `strict=True` so the day a discriminator lands it XPASSes and forces the
    marker off. Reason string names open question 2.
19. RED `test_fashion_price_leg_restored` — V ON, R03: `dimension_winners["cpw_score"]["winner"] == "Brand B Oxford Two"`,
    `cpw_score` in neither list, and the `build_dimensions_v2` rows gain
    `["cpw", 30.0, 100.0, 1]`. RED: N/A, no row.

*PO-RUBRIC-08 (G)*
20. RED `test_loser_strongest_dim_never_names_a_missing_dim[R08d|R08e]` — every
    `loser_wins["dimension"]` is absent from the loser's `missing_data`; expected
    `performance_score`, margin 0; `deterministic_verdict_fields(...)["key_tradeoff"]
    == "Brand B Phone Y stays competitive on performance."`. RED: `build_quality_score`,
    margin 50 / 40.0.
21. RED `test_loser_strongest_dim_returns_none_when_only_voids_remain` — hand-built
    `scores` where every numeric loser dim is in its `missing_data` ⇒
    `_loser_strongest_dim` None, `compute_tradeoff_pairs(..., scores=)` `[]`,
    `key_tradeoff` "". RED: names the void.
22. RED `test_loser_strongest_dim_skips_dim_absent_from_winner` — hand-built: the
    loser's highest dim key is absent from the winner's breakdown ⇒ skipped.
23. PIN `test_loser_real_strength_unchanged` — OFF: R03's `tradeoffs` =
    `[{loser_wins: {dimension: durability_score, margin: 29.0, product: "Maison A Oxford One"}, winner_wins: {dimension: style_score, margin: 21.9, product: "Brand B Oxford Two"}}]`;
    R08c's `loser_wins` `performance_score` margin 0.
24. PIN `test_loser_genuine_fifty_is_still_eligible` — a loser whose best dim is a REAL
    50.0 not in `missing_data` (a 2.5-star rating ⇒ `_normalize_review` 50.0) is still
    chosen. Kills a value-equality implementation of G (M12).

*Identity + KPI*
25. PIN `test_flags_off_record_digests` — recompute the §8-E2 records OFF, renorm-ON and
    spec-norm-ON (both new flags unset) and compare each to
    `tests/fixtures/rubric_truth_flag_off_digests.json` key by key (print the first
    differing key).
26. RED `test_flag_on_golden` — V, T, VT over the two SENSITIVE golden builders
    (renorm golden `golden_fixture_products`, spec-field golden
    `golden_fixture_products`, 9 categories each) equal
    `tests/fixtures/rubric_truth_flag_on_golden.json`; and the value-badge and
    behavioral goldens stay green with V, T and VT set (measured: unchanged). RED: the
    file does not exist / flags inert.
27. RED `test_missing_cell_kpi_counts_only_true_gaps` — VT ON:
    `count_missing_dim_cells` R02 = 0/12 (HEAD 8/12), R02c = 6/12 (HEAD 8/12), R01b
    = 2/12 (HEAD 8/12).

## 7. MUTATION CHECKS ARE REQUIRED (record each count)

| # | mutation | must redden |
|---|---|---|
| M1 | V reader returns False | 3, 4, 7, 8, 17(VT half), 19, 26, 27 |
| M2 | V filter keeps a value dim when spec OR price missing (review's literal semantics on the emitted list) | 3, 7 |
| M3 | V filter drops the value dim even when BOTH legs are missing | 7 (neither-leg row) |
| M4 | the authority exemption `:1475` reads the emitted list | 6 (`nodata_estimated_vs_measured` 55.0 → 51.0, measured) |
| M5 | the parity tie-break `:1501` reads the emitted list | red agent constructs and records a killing renorm-parity pair; if none exists, record the unreachability measurement |
| M6 | V implemented in `_signal_missing_for` (AND) instead of the emitted list | 6 (renorm half: 9 `nodata_vs_measured_good` flips, `[75.0, 68.0]`) |
| M7 | T reader returns False | 9, 10, 11, 13 (kept rows), 14, 16, 17, 26, 27 |
| M8 | T reader ignores the renorm coupling | 2, 15 |
| M9 | T reader ignores the flag (always ON) | 25 (digests), 5, and the renorm/spec-field golden tests |
| M10a-c | each sparsity helper forced "not sparse" (per signal) | 12, 13 (that signal's sparse rows) |
| M10d-f | each sparsity helper forced "sparse" | 9/10/11/13 (that signal's kept rows) |
| M11 | G removed | 20, 21 |
| M11b | G checks the loser's `missing_data` but not winner-absent | 22 |
| M12 | G implemented as `val == MISSING_SCORE` skip | 24 |
| M13 | reliability threshold `< 3` → `<= 3` | 13 (fact_check 3 row) |

Mutations are applied to byte-snapshots (shutil.copyfile), restored and sha-compared —
never `git checkout --`.

## 8. Gates

1. **TDD red-first** — each RED above observed red for the stated reason, then green.
2. **Comm gate (module-reference set).** At `61585c58`:
   ```
   grep -rlE "scoring_service|ScoringService|compute_scores|build_scores_summary|compute_tradeoff_pairs|compute_dimension_winners|count_missing_dim_cells|_loser_strongest_dim|_signal_missing_for|missing_data|response_builder|structured_comparison_service|build_dimensions_v2" tests --include=*.py | sort
   ```
   = **241 files** (list: `.qa-s68/specs/W4_6A_comm_set.txt`) + the new test file. Base
   run at `61585c58` (guarded, `-m "not (live_unit or live_db or integration)"`,
   `--timeout=120`, `-p no:randomly`): **4 failed, 6,447 passed, 2 skipped, 29
   deselected, 35 xfailed in 387 s; `[netguard] blocked 554 network attempt(s)`**
   (pre-existing: openai / neutralised-supabase / footlocker / noon). The 4 failures
   (`.qa-s68/specs/W4_6A_comm_base_failed.txt`) are all in
   `tests/.pre_impl_failures.txt` (two `test_page_scraping.py`, two
   `test_personalization_bundle_c.py`). Head: `comm -13 base head` must be empty.
3. **Byte-identity / equality gate — what is compared, exactly:**
   * **E1** the four existing goldens are byte-unchanged at head:
     `behavioral 6b531fcb…dbbf`, `missing_dim_renorm 43573b52…0549`,
     `spec_field_norm 8fc0e3d5…d82c`, `value_badge b7fc3f15…e12b` (full sha256:
     `6b531fcbf1aef2d54c1d050533a7ad9f43d013e3197fed0993ed683dda72dbbf`,
     `43573b52d386ab26a82b9c01c03d60dc1b7331118fc62c1932de7c650da80549`,
     `8fc0e3d5c9d699b8bfd176fa09b77ff6bf8e151e5b143a3e38ac0c895ef4d82c`,
     `b7fc3f15f6f2e18829b4991b1cfcd8ee319a62bbf6a5333f43511e0a462ee12b`), and their four
     tests are green flag-unset.
   * **E2** `rubric_truth_flag_off_digests.json` is CAPTURED AT BASE, before any code
     change, in a detached scratch worktree of `61585c58` (via a pytest-run capture
     under the guard): for each of the 164 records (144 grid + 14 scenarios + 6 d2) ×
     3 states (all unset; renorm ON; spec-field-norm ON), sha256 of the canonical JSON
     (`sort_keys=True, ensure_ascii=True`) of
     `{compute_scores result, build_dimensions_v2 rows, count_missing_dim_cells, build_scores_summary text}`
     — `tradeoffs`/`key_tradeoff` EXCLUDED (G changes them unflagged, gate E5). Head
     must match every key; then re-run the capture at base AGAIN (base2) and require
     base2 == base (control). Scoring is pure CPU with no corpus input, so the control
     is expected to be trivially equal — it is still run and reported.
   * **E3** the flag-ON arm: `rubric_truth_flag_on_golden.json` is generated from the
     GREEN head for V, T, VT over the two sensitive builders; the diff of its
     OFF-equivalent (regenerate with flags unset) must equal the two existing goldens'
     content for those builders (proves the generator shape). Value-badge and
     behavioral goldens asserted unchanged under V/T/VT (test 26).
   * **E4** V arithmetic neutrality (test 6) and T-under-renorm identity (test 15).
   * **E5** G's delta: over the 144 grid rows and 14 scenarios, `tradeoffs` differ
     from base ONLY on R08d and R08e (measured on the prototype: 0/144 grid rows).
   * The `_proof` corpus harness (`scripts/verify_flag_byte_identity.py`) is BLIND to
     this unit — it runs `extract_price_from_html` only and `price_service` imports
     just the `PRICE_TIERS_BY_CATEGORY` constant from `scoring_service` (`:9633`),
     which is untouched. Not run; say so in the PR.
4. **CI-order pin set.** Run with `-p no:randomly` in both orders — the new file FIRST
   and LAST around: `test_scoring_service.py test_scoring_missing_dim_renormalize.py
   test_scoring_spec_field_normalization.py test_value_badge_category_dims.py
   test_behavior_dimension_translation.py test_tradeoffs_dedup_parity.py
   test_prescoring_showable_guard.py test_missing_dim_coverage.py
   test_missing_score_collision_v2.py test_dim_phantom_tie_followup.py
   test_dim_silent_omission.py test_bundle_c_feature_flag.py
   test_winner_prose_reconciliation.py test_m13_04_full_stream_deadline.py` — identical
   results both orders (catches env leaks of the two new names, the process-cached
   `_BUNDLE_C_SCORING_FLAG`, and singleton patching).
5. Ruff `E9,F63,F7,F82` + `py_compile` on `scoring_service.py` and the new test/generator.
6. `git diff --stat` shows no whole-file diff (CRLF working copy).
7. Fable review of the diff before commit. Agents never commit.

## 9. Activation

* **V first, alone.** Arithmetic-neutral (0 overall/margin/winner/badge changes over
  164 records). Canary: the `[scoring] W4-6a value dim partial` line count; the
  `metadata.missing_dim_cells` KPI drops (grid 44.9 % → 34.7 % p0); the verdict prompt's
  `Dimension leaders` no longer shows `value=N/A` beside a clear lead; fashion payloads
  gain a `cpw` row.
* **T second, own window, never with `ENABLE_MISSING_DIM_RENORM`** (the coupled reader
  makes it inert there anyway). It MOVES results: `overall` on 66/144 grid rows,
  `win_margin` on 24, badges on 17; winners flip on price-driven fashion/other pairs
  (R03, R03c); the 4 %-price-gap pair goes from a 14.0 "clear lead" to a 4.2 "narrow
  lead"; displayed scores rise (R02 display 78 → 84); `scoring_v2.dimensions` regains
  omitted rows. Canary lines: `tie kept` (expect the majority) vs `tie collapsed
  (sparse)`; watch `WINNER_INDEX_MISMATCH` (GPT vs deterministic) — the verdict now
  sees non-N/A leaders — and the eval axis averages post-deploy (smoke20,
  `--concurrency 1`, judged on axis averages). Re-baseline `missing_dim_cells` the day
  it flips.
* **W4-6b dependency:** W4-6a is a precondition for #101's evidence being readable, and
  W4-6b's grid must be re-run with T ON — T changes which sentinels exist, and
  uncoupled RT re-crowns the unrated product in 8/9 `unrated_vs_2star` rows. Lifting the
  coupling is W4-6b's decision.
* Needs a funded search/LLM path to be observed live; latent until then. No migration,
  no client release.

## 10. Honest limits

* **(c) is not closed.** Under VT two different fashion (or other) products tie
  honestly at 65.0/65.0 on craft/function — no longer "missing", still not separated.
  Separation needs a merit discriminator for non-numeric fields (a material /
  construction / origin tier table): a PRODUCT CALL, not a rubric bug (open question 2).
* T's sparsity thresholds (3 fact-check buckets; `review_count > 0`;
  `CATEGORY_MIN_COVERAGE`) are heuristics; the boundaries are pinned, not justified by
  production frequency (unknown — `search_logs` stores no `category_used`).
* One-sided missing dims still carry the 50 sentinel into the margin (e.g. R08d's
  loser `build_quality 50` vs winner's measured 0 contributes −7.5): that is the #101
  sentinel arithmetic, W4-6b.
* The `PO-rubric-07` price cliff is not addressed; T incidentally damps it only where
  specs tie (value becomes the designed blend instead of price alone).
* After G, the F4.2 fallback still writes "stays competitive on performance" for a loser
  that trails 45.0 vs 85.0 (R08d) — the copy claims competitiveness at margin 0 by design
  of F4.2. Recorded as follow-up `PO-RUBRIC-08b`, not built here.
* 53.7 % is not re-derivable; the reconstruction (44.9 %) and the 6 recorded payloads
  (22.2 %) are what is measured. No live compare was possible.

## 11. Spec disagreements with the review

1. **V's mechanism.** The review puts the AND rule in `_normalize_scores` (the internal
   `_{dim}_missing` flags). Measured hazard: with renorm ON it flips 9/9
   `nodata_vs_measured_good` rows to the no-data product, and it moves the authority
   exemption (55.0 → 51.0). Ruling proposed: V changes the EMITTED list only; internal
   reads stay legacy.
2. **T's composition.** The review's sparsity-gated collapse omits the renorm interaction;
   uncoupled it re-opens #101 (8/9 flips, six renorm pins red including the headline
   inversion 55.1 < 58.4). Proposed: reader coupled to renorm OFF.
3. **Red claim (c) as written cannot go green in this unit** — both flags leave
   `craft 65.0 == 65.0`; the review's own alternative (#100 field norm) was re-measured
   and does not close it either. Reframed: test 17 (not missing) + test 18 (xfail pin of
   the limit).
4. **"Regenerate the four `*_flag_off_golden.json` for the flag-ON arm"** — only two are
   flag-sensitive (renorm golden: fashion/fragrances/other; spec-field golden:
   fashion/other); value-badge and behavioral are unchanged under V+T (measured). The
   ON arm is ONE new golden over the two sensitive builders; the four OFF files stay
   byte-identical.
5. **The `build_scores_summary` "too close to separate" rewrite is unnecessary** — under V
   the N/A-contributor invariant holds by construction (0/144 rows); the summary is left
   untouched.
6. **The 14.0-point "clear lead" is partly an artifact of the collapse itself**: with the
   spec tie kept (T), the same pair's margin is 4.2 — the decisive dim was price-only
   value because the tie had been erased.
7. **`PO-RUBRIC-08` magnitude:** 50 and 40.0 reproduce; the finder's 44.0 does not (its
   fact_check shape is unrecorded). The review says "no flag needed" — this spec agrees
   but routes the call to Fable against the standing rule (open question 1).
8. **Anchors** (76ace90 → 61585c58; W4-10 #176 added 9 lines above the collapse region):
   `:262-286` → `:262-284`; `:328-334` → `:318-334` (value clause `:330-331`);
   `:1789-1826` → `_score_specs :1777-1835` (presence credit `:1819`/`:1822`);
   `:2113-2155` → collapse blocks `:2125-2161`; `:2222-2233` (verified.json `:2231`) →
   stamp loop `:2230-2241`, call `:2240`; verified.json `:2116` → `:2127`; `:274` →
   `:270`/`:282`; `:2635` → `:2644`; `compute_scores :1264`, emitted list `:1428`
   (unchanged by the drift); tradeoff call sites `scs:3392/:4004/:4768` (the verifier's
   `:2970/:3522/:4241` were at 76ace90).

## 12. OPEN QUESTIONS FOR FABLE

1. **G flagged or unflagged?** Recommendation: unflagged (changes output only where the
   payload contradicts itself; 0/144 grid rows and 0 symbol-set results move).
   Alternative: ride T, or a third dark flag.
2. **(c) scope:** accept the reframing (not-missing + xfail pin) and open W4-6c for a
   non-numeric merit discriminator (product call for Ahmed: is "Italian full-grain,
   hand-welted" > "PU, glued" a rule the product wants to assert?), or instead drop the
   spec dim's weight for fashion/other (redistribute) as the honest answer?
3. **T's coupling to `ENABLE_MISSING_DIM_RENORM`** — accept "T inert under renorm" (the
   recommendation), or require W4-6b to land first?
4. **T's thresholds** (`< 3` buckets, `review_count > 0`, `CATEGORY_MIN_COVERAGE`) —
   accept as measured boundaries?
5. **T moves winners and displayed scores** (fashion/other price-driven pairs flip to the
   pricier, better-evidenced product; display +6 on R02). Is "restoring the designed
   0.6/0.4 value blend" a correctness ruling you take, or does the flip need Ahmed's
   sign-off before activation?
6. **`PO-RUBRIC-08b`** — the F4.2 "stays competitive" copy for a loser that trails badly:
   follow-up unit, or fold a "loser must be within the tie margin" rule into G?
7. **The review's additive `partial_dims` key** (FE caption "price only") — not built (no
   reader on the phones); confirm it stays out.
8. **Split V and T into two PRs?** They are independent mechanisms with independent
   activation windows; one PR keeps the shared test file coherent. Recommendation: one
   PR, two flags.

---

Files in `.qa-s68/specs/` supporting this spec: `W4_6A_comm_set.txt` (241 files),
`W4_6A_comm_base_failed.txt` (4 baselined ids), `W4_6A_probes/` (the probes,
`analyze.py`, and `prototype_scoring_service.diff`).


# ADVERSARIAL SPEC REVIEW (2026-09-26, session 68)

**VERDICT: APPROVED_WITH_CORRECTIONS.** The measurements hold, but three parts of the design are wrong and must not be built as written: V's un-stamp rule, T on fashion/other, and G combined with V/T (C1–C3 below). Nothing in this section rewrites the author's text above. Where the two conflict, the corrections here are binding until Fable rules.

## How this review measured

- Base `61585c58` was confirmed with `git rev-parse HEAD` in `sc-w4-specs`.
- The review used two detached scratch worktrees under the scratchpad (`w46adv/base` and `w46adv/proto`). The author's prototype diff applied cleanly to proto (`git apply --check` passed; 70 insertions, 2 deletions). Both worktrees were removed afterwards with `git worktree remove --force`; `git worktree list | grep -c w46adv` = 0. Neither worktree held a node_modules junction, and no `.env` was copied.
- All probes ran through pytest with `-p qaren_netguard -p tests.conftest` on the pinned venv. Every probe run printed `[netguard] blocked 0 network attempt(s)`.
- The review's own probes are in the scratchpad `w46adv/probes/`: `test_adv_w46a.py`, `test_adv_w46a_mut.py`, `test_adv_w46a_alt.py`, and `an1.py` to `an5.py`. They cover 16 flag states over 181 records: 14 scenarios, 8 boundary pairs, 9 extra pairs, the 144-row grid and the 6 d2 payloads (the alternative-rule probe uses 173 records, without the boundary pairs). The review's added prototype switches are saved as `w46adv/adv_proto_scoring_service.diff`. They are measurement-only, all env-gated: `W46A_ADV_M6`, `W46A_ADV_VALT`, `W46A_ADV_TEXEMPT`, `W46A_ADV_GPRIME`.
- **Reproducibility.** The author's main probe re-run at base is byte-identical to the author's `probe_head.json` (sha256 `73c5712d…26dc`). The author's v2dims probe re-run on the prototype is byte-identical to `probe2_proto.json` (`ce3fa51d…9c7119`). All three probe-shape digests (OFF `d0780117…b545`, R `e18fc89f…09b0`, S `e9d1aa15…d8f8`) reproduce as the sha256 of `json.dumps({"scenarios","grid","d2"}[state], sort_keys=True)`.
- **Prototype flag-OFF identity.** With V and T unset, the prototype equals base record-for-record in OFF, R and S over all 181 records. At base, every new-flag state equals its counterpart (OFF==V==T==VT==G, R==RV==RT, S==SVT).

## Claims re-measured and CONFIRMED (to the digit)

- **1a / R01 and R01b.** Overall `[72.0, 58.0]`, margin 14.0, value 100.0/30.0, value contribution 14.0. The four stamps, all the dimension_winners values and both summary lines match verbatim. `count_missing_dim_cells` = 8/12.
- **1b / R02.** Breakdown matches exactly. 4 of 6 dims are stamped, overall 67.0/67.0, and `build_dimensions_v2` returns 5 rows. The near-tie pair (battery 4100 vs 4000) and the saturated-popularity pair (review_count 1500 vs 2500) also collapse with 4 stamps each.
- **1c / R03 and R03c.** All figures match: 72.8/75.7, margin 2.9, cpw −7.0; 69.8/74.2, value −10.5. S (`ENABLE_SPEC_FIELD_NORM`) leaves both pairs unchanged.
- **1d / R08d and R08e.** Breakdown matches, and `loser_wins build_quality` has margin 50 and 40.0 respectively. R08c returns performance with margin 0.
- **1e / grid.** 388/864 product_0 cells (44.9 %) and 693/1728 across both products (40.1 %). 16 rows have a >1-point N/A contributor, and they are exactly the 16 rows the spec lists.
- **1e / d2.** 16 of 72 cells are stamped. The raws match (skincare reliability 0.47/0.47, fashion spec 1.0/1.0, popularity 1.0/1.0). 11 of 12 recorded products carry `missing_data: None`.
- **Anchors.** Every `scoring_service.py` line anchor in §1, §2 and §11 was checked with `sed -n` and is correct at `61585c58`. `price_service.py:9633` is the only `scoring_service` import there. `git diff --stat 76ace90 61585c58 -- scoring_service.py` = +18/−3.
- **Phone anchors.** `types.ts:209/:253/:373` and `ResultsContent.tsx:171` are correct. `git diff --stat ab9442ae 61585c58 -- SmartCompareApp/src` is empty.
- **V on the prototype (ON = flag set):**
  - OFF→V, R→RV, T→VT and RT→RVT (coupled) each change 0 `overall`, 0 `win_margin`, 0 `winner_index`, 0 breakdowns and 0 badges.
  - Grid: rows with a >1-point N/A contributor drop 16→0; p0 stamps drop 388→300; 22 rows change `key_tradeoff`.
  - V changes the phone's `v2` rows on 3 of 20 probe payloads, all fashion; 12 of 144 grid rows, also all fashion.
  - The R01 summary line matches the spec.
- **T on the prototype:**
  - R02 matches the §3.2 values: `missing_data` None, 100 / 65.0 / 98.5 / 75.0 / 68.0, overall 78.7, 8 rows. Display moves 78→84 (`calibrate_score`).
  - R01 goes to `[80.2, 76.0]`, margin 4.2. R03 goes to `[75.8, 74.0]` with cpw 38.0/54.0; R03c to `[72.4, 68.9]`.
  - Grid: overall changes on 66 rows, margins on 24, badges on 17, `key_tradeoff` on 30, and there are 0 winner flips.
  - d2: stamps 16→0, fashion margin 10.6→6.0, overalls rise 0.0 to 14.3, no flips.
  - VT: p0 stamps 153 (17.7 %). SVT: margins change on 61 rows, p0 stamps 475→153, 0 flips.
- **Renorm coupling.** Uncoupled RT flips 8 of 9 `unrated_vs_2star` rows; `electronics|unrated_vs_2star` goes `[58.3, 58.3]` winner 1 → `[70.9, 68.4]` winner 0. Coupled RT is identical to R on every record.
- **Mutations.**
  - M6 (AND inside `_signal_missing_for`) under renorm flips 9/9 `nodata_vs_measured_good` rows, `[55.0, 79.9]` → `[75.0, 68.0]`.
  - M4 (exemption reads the emitted list) moves `nodata_estimated_vs_measured` from `[55.0, 68.8]` to `[51.0, 68.8]` with V ON and renorm OFF. Under renorm the value is 51.0 either way, so M4 is killed only by test 6's non-renorm half.
- **G.** At OFF, G changes tradeoffs only on R08d and R08e, to performance with margin 0 ("stays competitive on performance"). It changes 0 of 144 grid rows and 0 d2 payloads.
- **§5 flag-ON sensitivity (71-file symbol set, run on the prototype):**

  | state | failed | passed | xfailed |
  |---|---|---|---|
  | OFF | 2 | 1892 | 35 |
  | V | 16 | 1878 | 35 |
  | T coupled | 17 | 1877 | 35 |
  | T uncoupled | 23 | 1871 | 35 |
  | G | 2 | 1892 | 35 |

  The reddening node lists are exactly the spec's: 14 under V, 15 under T coupled, plus the 6 renorm acceptance pins when uncoupled.
- **Comm gate.** Regenerated with the spec's grep, the comm set is identical to `W4_6A_comm_set.txt` (241 files). The base run gave 4 failed / 6,444 passed / 5 skipped / 29 deselected / 35 xfailed in 385 s, with `[netguard] blocked 554 network attempt(s)`. All 4 failures are in `tests/.pre_impl_failures.txt`.
- **Goldens.** All four golden sha256 values match E1.

## REFUTED or drifted claims

**R1 — "sparse rows PIN (equal to HEAD)" is wrong (§6 test 13).**
- Every one of the 8 boundary rows differs from HEAD under T, because the other two signals in each row are dense and un-collapse. Measured `md0` under T:
  - `fc_total_2` and `rc_none_sources2`: 4 stamps at HEAD vs 1 under T.
  - `rc_zero`: 4 vs 1.
  - `cov_5_of_11`: 4 vs 2.
- So the whole parametrization is RED at HEAD. What distinguishes the sparse rows is only which single signal stays stamped.

**R2 — the "designed 0.6·spec + 0.4·price blend" is mislabelled (§3.2 R01 bullet, §9 activation, open question 5).**
- `VALUE_FORMULA_BY_PRIORITY["_default"]` is `{"spec": 0.70, "price": 0.30}` (`scoring_service.py:611`).
- The spec's own numbers are the 0.7/0.3 values: 75.5 = 0.7·65 + 0.3·100 and 54.5 = 0.7·65 + 0.3·30. R02's 68.0 = 0.7·65 + 0.3·75.
- The 0.6/0.4 split is `spec_secondary`, which §3.2's renorm paragraph uses correctly.

**R3 — the §7 M1 row is wrong: test 17's VT half cannot redden when V is off.**
- T alone already empties the list for R03 and R03c (measured `md0 None` / `md1 None` under T), so `cpw_score` / `value_score` are absent with V off.
- M1 is killed by tests 3, 4, 7, 8, 19, 26 and 27 (R02c 8≠6, R01b 4≠2). Drop 17 from M1's row.

**R4 — the §8 comm baseline depends on the worktree.**
- The spec's 6,447 passed / 2 skipped needs `SmartCompareApp/node_modules`, which sc-w4-specs has through its junction.
- In a node_modules-less worktree the same 241 files give 6,444 passed / 5 skipped. The totals are equal (6,449).
- The gate recipe must name the worktree, or accept a 3-node pass/skip shift.

**R5 — §3.1 "V is a pure truth-of-labelling flag" / "the emitted list tells the truth" is wrong.**
- V is arithmetic-neutral (confirmed), but the labels it emits are not true. See C1.

**Minor — `missing_data` has no reference at all in `SmartCompareApp/src`.**
- §3.6 says there are zero references "outside types.ts", which implies `types.ts` has one; it does not.

## CORRECTIONS (binding until Fable rules)

**C1 (P1) — V as specified crowns the no-data product on the value dimension. Replace the rule.**
- *What the spec's rule does.* It un-stamps a product's value dim unless both of its legs are missing. That makes a price-only value (for example the equal-price tie score 75.0) comparable against the other product's spec+price blend (68.0), and against a spec-only value on a product with no price.
- *Measured effect.* In 27 records the value-dim winner flips to the other product. In the grid (24 rows):

  | pattern | categories flipped |
  |---|---|
  | `nodata_vs_measured_good` | 9 of 9 |
  | `nodata_vs_measured_bad` | 9 of 9 |
  | `one_missing_price` | 5 |
  | `one_missing_all_specs` | 1 |

  The other 3 are `nodata_estimated_vs_measured`, `renorm_parity_partial` and `specless_vs_full_priced`.
- *Worked example.* On `electronics|nodata_vs_measured_good` the verdict prompt reads `Score winner: Brand B … (clear lead)` next to `value=Brand A electronics A`. Brand A is the product with no data. This is the #101 "no data beats measured data" inversion, moved into the GPT verdict input and the tradeoff pairs.
- *No price at all.* On `electronics|one_missing_price`, V crowns the product that has **no price** on "value" (62.9 vs 55.7).
- *Phone.* On `fashion|one_missing_price`, V adds a new phone row `cpw [75.0, 50, None]`. The 50 is a sentinel bar for a product with no price.
- *The replacement rule.* Un-stamp the value dim only when **every product has a price AND `_spec_missing` is equal across the pair** (a like-for-like formula on both sides). Otherwise emit today's list.
- *Measured on the prototype (`W46A_ADV_VALT`), grid:*

  | state | value-crown flips | arithmetic changes | p0 stamps | rows with >1-pt N/A contributor |
  |---|---|---|---|---|
  | V as specified | 24 | 0 | 300 | 0 |
  | V-alt (replacement rule) | 0 | 0 | 327 | 3 |
  | V-alt with T | 0 | 0 | 180 | 1 |

  - V-alt still closes R01, R01b, R03 (cpw goes to Brand B) and R03c.
  - The 3 rows V-alt leaves are `fashion|one_missing_price`, `other|one_missing_price` and `supplements|both_no_price`. Their contribution is sentinel or no-price arithmetic that no label can make honest (#101 / W4-6b).
- *Test changes.*
  - Test 7 flips: "price-only product vs a measured partner" and "spec-only (no price)" must both **stay stamped**; "both priced, both spec-less" gets un-stamped.
  - Test 8's expected set becomes exactly those 3 rows under V (1 row under VT).
  - Add a PIN: under V, no record crowns a product on its value dim when that product lacks a price or when its value is price-only against a blended partner. The kill for this is the spec's own rule (24 grid flips).
  - Add the spec's rule as mutation M14.

**C2 (P1) — T turns fashion/other presence-credit equality into a displayed "tie". This is less truthful than HEAD.**
- *Why it is not a measured tie.* For categories with empty HIGHER/LOWER sets, `spec_raw` is 1.0 for any product above coverage. §1c and §10 of this spec say so themselves. It measures only that fields are populated, not merit. Under T, R03 ships a phone row `craft [65.0, 65.0, None]` (Italian hand-welted calfskin vs glued PU as a craftsmanship tie). The d2 fashion payload gains `craft 65/65` and `style 100/100`.
- *Where the flips come from.* Every winner flip T produces in the probe set (R03, R03c) comes from this path. So does the d2 fashion margin move from 10.6 to 6.0.
- *The fix.* `_spec_sparse` returns True (the collapse is kept) whenever `HIGHER_IS_BETTER_BY_CATEGORY[cat]` and `LOWER_IS_BETTER_BY_CATEGORY[cat]` are both empty, until W4-6c ships a discriminator.
- *Measured on the prototype (`W46A_ADV_TEXEMPT`):*

  | measure | T as specified | T with the fix |
  |---|---|---|
  | grid `overall` changes | 66 | 54 |
  | grid margin changes | 24 | 11 |
  | grid badge changes | 17 | 6 |
  | record winner flips | 2 | 0 |
  | p0 stamps | 189 | 237 |
  | rows with >1-pt N/A contributor, with V | 0 | 0 |

  R02 and R01 keep every T value (78.7 / `[80.2, 76.0]`, 8 rows). R03 and R03c return to HEAD, and d2 fashion returns to margin 10.6.
- *Test changes.* Test 17's craft/function "not missing, 65 == 65" becomes a PIN that they stay stamped under T. Open question 5 mostly dissolves: the winner flips were the presence-credit artefact.

**C3 (P1) — G composed with V/T emits self-contradictory tradeoff pairs; §3.3's "composes with V/T automatically" is wrong.**
- *G under VT.* G changes tradeoffs on 9 grid rows (every `*|sparse_vs_sparse` row), not 0.
- *Same-dimension pairs.* In 18 records `loser_wins.dimension == winner_wins.dimension`. Example, `electronics|sparse_vs_sparse`: `winner_wins value margin 70.0` beside `loser_wins value margin 0`, producing "Brand B … stays competitive on value." At OFF with G the count is 0.
- *V without G makes PO-RUBRIC-08 more common.* The number of records where `loser_wins` names a dim in the loser's own `missing_data` goes from 2 at OFF to 11 under V or VT.
- *T alone also spreads the 08b copy.* "stays competitive on build quality" at margin 0 on the tied R01 pair.
- *Margin-0 "competitive" copy across the 181 records:* OFF 68, V 86, T 89, VT 104.
- *Required.* V/T must not ship without G. Test 20 must not pin "stays competitive on performance." as the target: the loser trails 45.0 vs 85.0, so that copy is a PO-RUBRIC-08b false claim.
- *The measured fork (G', `W46A_ADV_GPRIME`: G plus skip any dim the winner leads by more than 5):*
  - At OFF, G' changes 54 of 173 records and empties `key_tradeoff` on 115 of 173 (G alone: 81).
  - Under VT it removes all 18 same-dim pairs.
  - G' is a user-visible fork on unflagged traffic, so it cannot ride "unflagged".
- *Ruling needed.* Either fold G' in behind V/T (active only when either flag is ON; OFF keeps plain G), or give G' its own dark flag. Plain unflagged G alone swaps one false claim for another.

**C4 — Test 13.** Reclassify all 8 rows as RED at HEAD (R1). Each row asserts the exact T-ON `missing_data` from §3.2's table.

**C5 — Relabel 0.6/0.4 as 0.7/0.3** in §3.2, §9 and open question 5 (R2).

**C6 — Rewrite the M1 row** without test 17 (R3). Add mutations:
- M14: the spec's V rule instead of V-alt (kill: the new PIN in C1).
- M15: the fashion/other exemption removed from `_spec_sparse` (kill: the test 17 PIN in C2).
- M16: G without the G' clause when V/T are ON (kill: a new PIN asserting no pair has `loser_wins.dimension == winner_wins.dimension` under VT).
- M17: log lines emitted with the flags OFF (kill: a caplog PIN that the flags-OFF run emits no `W4-6a` line; §3.4 currently has no test).

**C7 — E2 needs a committed, auditable generator** (a `_gen_rubric_truth_flag_off_digests.py` twin of the flag-ON generator, lazy `app.*` import, run only through a pytest probe). Without it the 492 digests can only be regenerated from this spec's scratch probe. The E2 fixture also depends on `extraction_service.CATEGORY_SPEC_SCHEMAS` through `_grid()`; say so in the fixture header.

**C8 — Name the comm-gate worktree** (R4), and re-run base and head in the same one.

## MISSING ITEMS

- **Consumers the spec does not list:**
  - `app/services/trust_validation_service.validate_verdict` reads the same breakdowns with `== MISSING_SCORE` value-equality, and its result ships as `metadata.verdict_validation`, including `confidence_adjustment`. Under T, the collapsed 50s become 65/100/98.5 and start counting as `claims_softened` / `claims_flagged`, and `flagged > 2` sets `confidence_adjustment: "reduced"`. This is a payload fork the spec does not mention; not measured live (it needs a GPT verdict).
  - `app/api/home_routes.py:452-459` reads `scoring.dimension_winners`. It compares the dict value to a string, which is a pre-existing dead comparison, so V/T have no effect there. Record that in §3.6 so the next reader does not re-derive it.
- **Badges under the category-badge flag.** With `ENABLE_CATEGORY_VALUE_BADGE` ON, T changes badges on 54 of 144 grid rows (17 with it OFF). The §9 activation text must say so; that flag is also dark and could be flipped first.
- **The phone under V.** The fashion `cpw` row appears only when another fashion dim is both-sided missing, because the 8-row cap fills with craft/fit/style/durability/heritage first. Under VT the row is gone again (R03 and d2 fashion under VT have no `cpw`). §9's canary "fashion payloads gain a cpw row" is therefore V-alone-only.
- **Excluded vs missing under RV.** `excluded_dims` is computed from the legacy flags while `missing_data` is the V-filtered list, so under RV one payload can list a dim as excluded from `overall` and still crown it in `dimension_winners`. The count is the same 85 records under R and RV, so this is not new, but the spec should state the shape.
- **The 3 remaining N/A rows under V-alt** (`one_missing_price` in fashion and other, `supplements|both_no_price`) are W4-6b's (#101 sentinel arithmetic). Record them in §10.
- **G for a sentinel on the winner's side.** G does not cover a margin computed against the winner's sentinel: the loser has a real value and the winner has `missing_data` on that dim, giving a margin such as 80 − 50. The dimension named is real, so this is low severity; record it.

## DESIGN RISKS

- **V's labels feed GPT.** V's crowns reach the gpt-4o verdict prompt, so the model receives "value=<void>" and may write it into the verdict prose. C1 removes this.
- **Presence credit shown as measurement.** T, as specified, shows the product making merit claims (craft/function ties) that the data cannot support; this is the PO-RUBRIC-03 row's own subject. C2 removes it.
- **Unflagged G has two problems.** Its OFF output on R08d is still false (08b), and combined with V/T it creates same-dimension contradictions. See C3.
- **More "competitive at margin 0" copy.** The count rises under every flag state (68 → 104 of 181 records). The hard-cap partial path is unflagged and renders this string.
- **T needs a sign-off even after C2.** T still moves `overall` on 54 of 144 grid rows and badges on 6 (54 with the category-badge flag), and raises displayed scores (R02 78→84). The shipped scores move, so Ahmed needs to see the before/after before activation.

## QUESTIONS FABLE MUST RULE ON

1. Adopt V-alt (C1: every product priced and `_spec_missing` equal across the pair) in place of the spec's per-product rule?
2. Exempt fashion/other from T's spec un-collapse until W4-6c (C2)? This removes every T winner flip in the probe set.
3. G' (skip dims the winner leads by more than 5) behind V/T, or under its own flag? And what is test 20's target string: `""`, or a margin-0 copy you accept?
4. Should the 08b follow-up become part of this unit, since V/T triple its reach? (Answer together with question 3.)
5. With C2 applied, does T's remaining movement (54 overall rows, 6 badges; 54 badges with the category-badge flag; R02 display 78→84) need Ahmed's sign-off before activation?
6. Confirm `metadata.verdict_validation` may change under T, or require a `trust_validation_service` pin.
7. The author's open questions 3 (renorm coupling), 4 (thresholds, now with R1's corrected classification), 7 (no `partial_dims` key) and 8 (one PR) stand as asked; the measurements support the author's recommendations on all four.
