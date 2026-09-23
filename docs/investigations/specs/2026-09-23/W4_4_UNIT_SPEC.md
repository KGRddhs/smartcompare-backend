# W4-4 — a partial must not invent a score it never computed

Finding `PO-VERDICT-TRUTH-02`; it also lands the `metadata.partial_stage` counter that
`PO-RECORDED-MEASURED-10` / `-13` need in order to be measurable at all. Backend only
(the FE half is recorded, not built — see Honest limits 6). Flag
`ENABLE_HONEST_PARTIAL_SCORING`, **default OFF, read per call**. Worktree `sc-w4-4`,
branch `feature/s65-w4-4-honest-partial-scoring`, base `b63a8368` (= `origin/main`,
"Merge pull request #159"). Every line anchor below was verified at `b63a8368`; the
review's anchors are from `76ace90` and the drift is tabulated in § 9. Every number
below came from a probe that was RUN (`PYTHONIOENCODING=utf-8`, conftest-equivalent
env — `load_dotenv(override=True)` + `neutralize_credentials()` + `install_dotenv_guard()`
— zero network, no `LIVE`).

**One sentence on why it is flagged at all.** The review row says "none — a degraded
path only". That is wrong on the measurement: `scoring_v2` is a *client contract*
(`SmartCompareApp/src/types/types.ts:471`, read on five surfaces), the phones run the
PRE-OTA client `97b5f15`, and flag ON deletes three rendered sections from the partial
screen (§ 8.1). Fable's standing rule applies: flagged, default OFF.

---

## 1. The defect, measured

### 1.1 Where it is produced

`app/services/response_builder.py`, `_build_scoring_v2(product_data, scoring_result,
category, winner_index)` (`:1097`):

```
:1105    if len(product_data) < 2:
:1106        return {}
:1107    raw_a = scoring_result.get("scores", {}).get("product_0", {}).get("overall", 50)
:1108    raw_b = scoring_result.get("scores", {}).get("product_1", {}).get("overall", 50)
:1109    score_a = calibrate_score(raw_a)
:1110    score_b = calibrate_score(raw_b)
:1111-1141   the CALIBRATION-COLLAPSE guard (nudges the loser strictly below the winner)
:1147    dimensions = build_dimensions_v2(product_data, scoring_result, category)
:1168-1201   the scoring_v2 dict literal
:1174        "win_margin": abs(score_a - score_b),
:1224    return scoring_v2
```

The two `, 50)` defaults at `:1107-1108` are the whole defect. `MISSING_SCORE = 50`
(`scoring_service.py:297`) and `calibrate_score` (`scoring_service.py`, body
`base = 70 + (raw_score - 50) * 0.5`, clamped to `[_CALIBRATION_FLOOR 60,
_CALIBRATION_CEILING 95]`, `:2928-2929`) map `50 → 70`. Both products therefore
calibrate to **70**, the collapse guard at `:1132-1141` cannot leave a tie, so it
writes the loser down to **69**, and `:1174` asserts a **1**-point `win_margin`.
None of those three numbers was computed from data.

`build_comparison_response` ships the result unconditionally at `:1827`
(`"scoring_v2": _build_scoring_v2(product_data, scoring_result, category_used,
winner_index)`) — it is NOT gated by `ENABLE_BUNDLE_C_SCORING`, which gates
`scoring_service` only.

### 1.2 Who feeds it an empty `scoring_result`

`app/services/structured_comparison_service.py`, `_build_partial_response(*,
elapsed_seconds)` (`:3161`):

```
:3184    product_data    = self._partial_product_data or self._early_specs_buffer_list() or []
:3185    scoring_result  = self._partial_scoring_result or {}      <-- the review's scs:2956
:3186    comparison      = self._partial_comparison or {}
:3229    result = build_comparison_response(... scoring_result=scoring_result ...)
:3257        metadata={"partial": True, "category_used": ctx.get("category_used", "")},
```

Three call sites, all funnelling through that one method:

| site | path | gate |
|---|---|---|
| `:3355` | `compare_from_text`, Phase-1 hard cap (`asyncio.TimeoutError` on `STREAM_HARD_CAP_SECONDS`, prod **30.0**) | always |
| `:3996` | `compare_from_text_streaming`, `_emit_stream_deadline_partial` (post-Phase-1 tail) | `ENABLE_FULL_STREAM_DEADLINE` (default OFF) |
| `:4206` | `compare_from_text_streaming`, Phase-1 hard cap | always |

Stash order, measured by reading the assignments: `self._partial_scoring_result` is
written at `:3699`, `self._partial_comparison` at `:3748` — strictly after, with no
branch that skips the first. The streaming entry resets both to `None` at `:4049/:4051`
and **never** assigns them, so on the SSE path a partial always carries
`scoring_result == {}` and `comparison == {}`.

### 1.3 RED reproduction — the builder (probe `w44_probe.py`)

Two realistic products (Alpha BHD 250, 4.1★/12 reviews; Beta BHD 150, 4.6★/950 reviews),
`comparison={}`, `scoring_result={}`, `metadata={"partial": True}`, category
`electronics`:

```
A  type(scoring_v2)        = dict
A  scoring_v2.overall_score= {"product_a": 70, "product_b": 69, "winner_idx": 0}
A  scoring_v2.win_margin   = 1
A  scoring.scores          = {}
A  overview overall_score  = [None, None]
A  overview.winner.name    = 'Alpha Phone'
A  overview.winner.reason  = 'Alpha Phone is the stronger overall pick.'
A  winner_index (BC)       = 0
A  recommendation          = 'Alpha Phone is the stronger overall pick.'
A  factual_verdict         = {"line1": "Alpha Phone carries a 40% price premium for the upgrade.",
                              "line2": "Beta Phone pulls ahead on Value."}
A  metadata.partial        = True
A  metadata.partial_stage  = '<ABSENT>'
A  'scoring_v2' in res     = True
A2 direct _build_scoring_v2([A,B], {},                      'electronics', 0) -> 70/69, margin 1
A2 direct _build_scoring_v2([A],  {},                      'electronics', 0) -> {}
A3 direct _build_scoring_v2([A,B], {"scores":{"product_0":{"overall":62.0}}}, 'electronics', 0)
                                                                             -> 76/70, margin 6
A5 direct _build_scoring_v2([A,B], {"scores": {}},          'electronics', 0) -> 70/69, margin 1
A6 direct _build_scoring_v2([A,B], {},                      'electronics', 1) -> 69/70, margin 1
A4 CONTROL, real scores 62.0/48.0                                            -> 76/69, margin 7
calibrate_score(50) = 70   floor= 60   ceil= 95   MISSING_SCORE= 50
```

**A3 is a second, narrower fabrication the review does not name**: when only ONE
product's `overall` landed, the other silently becomes 70. The defect is "an absent
`overall`", not only "an empty `scoring_result`".

### 1.4 RED reproduction — the orchestrator twin (probe `w44_probe2.py`)

Real `get_comparison_service()` instance, stash set as `_compare_from_text_impl` sets
it, `_build_partial_response(elapsed_seconds=30.0)`:

```
usable_data = True
ORCH scoring_v2.overall_score = {"product_a": 70, "product_b": 69, "winner_idx": 0}
ORCH scoring_v2.win_margin    = 1
ORCH scoring.scores           = {}
ORCH overview overall_score   = [None, None]
ORCH overview.winner.reason   = 'Alpha Phone is the stronger overall pick.'
ORCH metadata.partial         = True
ORCH metadata.partial_stage   = '<ABSENT>'
ORCH winner_index             = 0
ORCH success                  = True
CTRL (real scores 62/48)      = 76/69, margin 7          <- untouched control
EARLY (early-specs buffer only, no post-gather stash) = 70/69, margin 1
```

### 1.5 The measured harm, precisely

The 70/69 pair is never *displayed* (the HeroRings score-rings panel was pruned in
Faithful-results Phase 2.1; `grep -rn "overall_score" SmartCompareApp/src` returns
exactly four hits — `ResultsScreen.tsx:773`, `:774`, and two type declarations). What
it does:

1. **It decides the crown.** `ResultsScreen.tsx:772-778`:
   ```
   :772  const scoringV2WinnerIndex: 0 | 1 =
   :773    (scoring_v2?.overall_score?.product_a ?? 0) >=
   :774    (scoring_v2?.overall_score?.product_b ?? 0) ? 0 : 1;
   :776  const presentationWinnerIndex: 0 | 1 = (
   :777    scoring_v2 ? scoringV2WinnerIndex : (winner_index === 1 ? 1 : 0)) as 0 | 1;
   ```
2. **It contradicts the honest bars on the same screen.** `build_dimensions_v2`
   (`scoring_service.py:3654`) builds the three core dims from `products_data`
   DIRECTLY, not from `scoring_result` — so on a no-scoring partial they are real.
   Measured (probe `w44_probe4.py`):
   ```
   price   79 85 winner=1 conf=high   delta='BHD 100 less'
   reviews 86 88 winner=None conf=high delta='0.5 stars higher'
   value   79 88 winner=1 conf=medium delta='Substantially stronger value on the other side'
   crowned index (FE) = 0
   ```
   **Every dimension that has a winner says product_1; the crown says product_0.**
3. **It is persisted and re-rendered.** `database_service._validate_renderable`
   (`:291`) returns **True** for this payload (measured), `text_routes.py:413`
   states "A best-available PARTIAL has `success:true` so it never reaches this
   branch", so the route falls through to `log_search(success=True)` (`:430`) and
   `save_comparison`/`persist_comparison` (`:455`/`:474`). The fabricated 70/69 lands
   in `comparisons.full_response` and is re-rendered by History for as long as the row
   lives.
4. **Its rate is unmeasurable.** `metadata.partial_stage` does not exist anywhere:
   `grep -rn "partial_stage" app/ tests/ SmartCompareApp/src` returns **zero** hits at
   `b63a8368`. Nothing distinguishes a partial from a full success in `search_logs`.

---

## 2. The design — one flag branch, one additive metadata key

### 2.1 The flag reader (copy the nearest in-file idiom)

`response_builder.py` already carries three per-call readers with one idiom:
`_gpt_winner_lever_enabled()` (`:108-113`), `_winner_prose_reconcile_enabled()`
(`:116`), `_eval_capture_debug_enabled()` (`:288-298`). Copy `:108-113` verbatim
(note: this file uses `os.environ.get(...)`, not `os.getenv(...)`, and the truthy
tuple is ordered `("1","true","yes","on")` — match the file, not `price_service`):

```python
def _honest_partial_scoring_enabled() -> bool:
    """W4-4 / PO-VERDICT-TRUTH-02 flag reader (default OFF). Read live so a
    Railway flip / monkeypatch takes effect without a restart."""
    return os.environ.get("ENABLE_HONEST_PARTIAL_SCORING", "").strip().lower() in (
        "1", "true", "yes", "on",
    )
```

`_factual_verdict_diag_enabled()` (`:29-35`) memoises into a module global — do NOT
copy that one; it is the anti-pattern this project's flag rule forbids.

### 2.2 The predicate (pure, no env read)

```python
def _scoring_overall_absent(scoring_result: Dict[str, Any]) -> bool:
    """True when the scorer never produced BOTH products' `overall`, i.e. when
    _build_scoring_v2's `, 50)` defaults at :1107-1108 would fabricate a score."""
    scores = (scoring_result or {}).get("scores")
    if not isinstance(scores, dict) or not scores:
        return True
    for key in ("product_0", "product_1"):
        entry = scores.get(key)
        if not isinstance(entry, dict) or entry.get("overall") is None:
            return True
    return False
```

### 2.3 The one branch in `_build_scoring_v2`

Inserted between `:1106` and `:1107` — **after** the `len(product_data) < 2` guard,
which must keep returning `{}` (§ 3):

```python
    if _honest_partial_scoring_enabled() and _scoring_overall_absent(scoring_result):
        return None
```

The signature's return annotation widens to `Optional[Dict[str, Any]]`. Nothing else in
the function changes: `:1107-1224` are untouched, so with the flag OFF the function's
bytes-executed path is identical to `b63a8368`.

### 2.4 The response assembly

`:1827` is **not edited**. `"scoring_v2": _build_scoring_v2(...)` simply carries `None`
instead of a dict, so the top-level key SET is unchanged.

**`null`, not absent — and this is measured, not aesthetic.**
`tests/test_timeout_partial_integration.py:242-250`
(`test_partial_response_full_structural_shape`) asserts `"scoring_v2" in resp`. Popping
the key would redden an existing pin that is *correct* (the FE is allowed to branch on
the value, not on the key). `json.dumps` of the payload with `scoring_v2=None` succeeds
(measured, 4,434 B) and `_validate_renderable` still returns True (measured). The FE's
`?.` / `!scoring_v2` reads treat `null` and `undefined` identically (§ 10.2), so
`null` satisfies the review row's "ABSENT or `null`" while breaking nothing.

### 2.5 `metadata.partial_stage` — UNFLAGGED, additive

In `_build_partial_response`, derive the stage from the stash state and thread it through
the existing `metadata=` kwarg at `:3257`:

```python
    def _partial_stage(self) -> str:
        """W4-4 — the last stage that landed before the cap fired. One string,
        derived from the same stash `_build_partial_response` reads."""
        if self._partial_comparison:
            return "verdict"
        if self._partial_scoring_result:
            return "scoring"
        if self._partial_product_data:
            return "phase1"
        if self._early_specs_buffer_list():
            return "identity"
        return "none"
```

```python
            metadata={
                "partial": True,
                "partial_stage": self._partial_stage(),
                "category_used": ctx.get("category_used", ""),
            },
```

**Why unflagged**: it is an additive `metadata` key on an already-degraded path, the
exact precedent CLAUDE.md records for `metadata.data_freshness_shaky`
("attached unflagged (additive key)"). Measured safety: the client reads exactly one
metadata key on this surface (`ResultsContent.tsx:161`,
`metadata?.partial === true`); `grep -rn "set(.*metadata.*keys()\|sorted(.*metadata.*keys()\|metadata.keys() ==" tests/`
returns **zero** hits, so no test pins the metadata key set; `_validate_renderable`
reads only `metadata.query`. Nothing can see the new key except a consumer that asks
for it — which is W4-13's job, not this unit's.

### 2.6 Files touched

* `app/services/response_builder.py` — one new reader, one new pure predicate, one
  two-line branch, one annotation.
* `app/services/structured_comparison_service.py` — one new method, three lines in the
  existing `metadata=` kwarg.
* `tests/test_partial_response_no_fabricated_scores.py` — new (the finding's own
  `test_first` filename, kept for traceability).

### 2.7 MUST-NOT-TOUCH list (named)

| surface | why |
|---|---|
| `_build_scoring_v2`'s `len(product_data) < 2 → {}` at `:1105-1106` | pinned by `tests/test_scoring_v2_confidence.py:104-113` (`assert isinstance(v2, dict)`). The new branch goes AFTER it. |
| `:1107-1141` (the `, 50)` defaults themselves + the CALIBRATION-COLLAPSE guard) and `calibrate_score` / `_CALIBRATION_FLOOR` / `_CALIBRATION_CEILING` | 167 nodes across 11 files pin this arithmetic (§ 4). Removing the defaults unflagged would fork every legacy fixture. |
| `build_dimensions_v2`, `_build_factual_verdict`, `_confidence_legs_and_details`, `_safe_detect_comparison_quality`, `_safe_compute_applied_shifts`, `_factual_verdict_diag_enabled` | they stay correct; the flag stops *emitting* their output on a no-scoring partial, it must not change *them*. |
| the legacy `"scoring"` block `:1818-1825` | the FE fallback is literally `!scoring_v2 && scoring` (`ResultsContent.tsx:528`); if `scoring` stopped being truthy the fallback would never fire. Measured truthy: `{"scores": {}, "dimension_winners": {}, "price_tiers": {}, "is_cross_tier": false, "scoring_method": "category_weighted", "category_weights": {}}`. |
| `reconcile_winner_prose` (`:1386`), `winner_index`, `overview.winner.*`, `recommendation`, the BC `comparison` alias, `overview.products[i].overall_score` | the crown is the FE half and NO backend-only change moves it (§ 9.3). Touching it here would be an unmeasured product change. |
| `metadata["partial"]` boolean, `_partial_has_usable_data` (`:3143`), the three call sites `:3355 / :3996 / :4206`, and both `STREAM_TIMEOUT` bodies (`:4016`, `:4232` — `success:false`, top-level `partial`, no `scoring_v2` at all) | out of scope. |
| `app/api/text_routes.py:892` (`if complete_response and not had_error and not complete_after_client_gone:`) and every `log_search` call | that is `PO-RECORDED-MEASURED-10`'s fix and belongs to **W4-13**; W4-4 only produces the counter it will read. |
| `SmartCompareApp/**` and `results.partial.note` (`en.json:768`) | FE half, OTA-gated. Recorded in § 8.6, not built. |
| `app/services/price_service.py`, `app/api/home_routes.py`, `database_service._validate_renderable` | not on this path (measured). |

### 2.8 Why this design beats the alternatives

* **vs. deleting the `, 50)` defaults unflagged** — 167 existing nodes across 11 files
  depend on the calibration arithmetic, and the phones run the pre-OTA client. Fable's
  standing rule settles it.
* **vs. returning `{}`** — explicitly refuted by the verifier: `{}` is truthy in JS, so
  `ResultsScreen.tsx:777` and `ResultsContent.tsx:528` would NOT fall back and the fix
  would be a silent no-op. Reproduced by reading both guards at HEAD and at `97b5f15`.
* **vs. keeping the block and nulling only its fields** (the finding's own "if a block
  must still ship for shape stability" alternative) — **measured strictly worse**:
  `(null ?? 0) >= (null ?? 0)` is `0 >= 0` → crowns product_0 unconditionally, so in the
  case where the GPT verdict names product_1 (`reconcile_winner_prose({'winner_index':1},
  {}, ...)` → **1**, and today's payload then gives `69/70` → FE crown **1**) the narrow
  variant would FLIP the crown to product_0. The null-block variant falls to
  `winner_index === 1 ? 1 : 0` → **1**, i.e. unchanged. Measured in `w44_probe4.py`:
  `HYPO winner_index = 1  scoring_v2.overall = {"product_a": 69, "product_b": 70,
  "winner_idx": 1}  FE crown = 1`.
* **vs. a per-call-site fix in the orchestrator** — `build_comparison_response` is the
  chokepoint all three partial sites already share; fixing it once is the CD-wave-diffs-03
  lesson (a rule applied at one door only lets the other door ship the same row).

---

## 3. Preserve

Run at `b63a8368`, `-m "not (live_unit or live_db or integration)" --timeout=180
-q -p no:cacheprovider`:

| set | command basis | result |
|---|---|---|
| the partial + calibration suites | `tests/test_timeout_partial_integration.py tests/test_compare_timeout_graceful.py tests/test_partial_specs_stash_on_price_timeout.py tests/test_calibration_collapse_v2.py` | **52 passed** |
| every file naming `_build_scoring_v2` (11 files) | `$(grep -rl "_build_scoring_v2" tests/ --include=test_*.py)` | **167 passed** |
| every file naming `scoring_v2` (30 files) | `$(grep -rl "scoring_v2" tests/ --include=test_*.py)` | **448 passed, 30 deselected** |
| that 30 + the three empty-`scoring_result` builders (`test_cache_hitrate_metadata.py`, `test_category_payload_completeness.py`, `test_review_paraphrase.py`) = 33 files | same | **489 passed, 30 deselected** (106.5 s) |

**Flag-ON blast measured, not guessed.** The same 33-file set was re-run with a
scratchpad-only pytest plugin (`-p w44_flagon_plugin`, `PYTHONPATH` pointed at the
scratchpad; **nothing in the worktree was modified**) that patches
`response_builder._build_scoring_v2` to exactly the § 2.2/§ 2.3 behaviour:
**489 passed, 30 deselected** (87.1 s) — **zero existing tests redden with the flag ON**.

Specific pins that must stay green in BOTH flag states, with the reason they are safe:

* `test_timeout_partial_integration.py:215-225` and `:383-399` subscript
  `resp["scoring_v2"]["factual_verdict"]`. Safe because both helpers default
  `scoring_result` to `_partial_scoring()` (`{"scores": {"product_0": {"overall": 64.0},
  "product_1": {"overall": 55.0}}, ...}`) — both `overall` keys present, so
  `_scoring_overall_absent` is False and the block still ships.
* `test_timeout_partial_integration.py:242-250` asserts `"scoring_v2" in resp` — the
  reason § 2.4 chooses `null` over absent.
* `test_scoring_v2_confidence.py:104-113` asserts `_build_scoring_v2([], {}, ...)` is a
  `dict` — the `len < 2` guard fires first, so it returns `{}` in both flag states.
* `tests/test_calibration_collapse_v2.py` (11 `_build_scoring_v2` calls, every one with
  real `overall` values) — untouched in both states.
* Flag OFF: the entire § 1.3 / § 1.4 table reproduces byte-for-byte — 70 / 69 /
  `win_margin` 1 / `winner_idx` 0 / `'scoring_v2' in res` True.

---

## 4. Red tests — `tests/test_partial_response_no_fabricated_scores.py`

Toggle with `monkeypatch.setenv` / `delenv` — the idiom `tests/test_gpt_winner_lever.py:65`
/`:196` already uses for the sibling `ENABLE_GPT_WINNER` reader in the same module.
Fixture: the two products of § 1.3.

| # | assertion | state today |
|---|---|---|
| 1 | **flag ON**, `build_comparison_response(..., scoring_result={}, metadata={"partial": True})` ⇒ `result.get("scoring_v2") is None` **and** `"scoring_v2" in result` | **RED** — a dict, `overall_score` 70/69 |
| 2 | **flag ON**, parametrized over `scoring_result ∈ ({}, {"scores": {}}, {"scores": {"product_0": {"overall": 62.0}}}, {"scores": {"product_1": {"overall": 62.0}}}, {"scores": {"product_0": {"overall": None}, "product_1": {"overall": 48.0}}})` ⇒ `_build_scoring_v2(...) is None` for every row | **RED** — 70/69, 70/69, 76/70, 70/76, 70/69 |
| 3 | **flag ON**, orchestrator twin: real `get_comparison_service()`, `_partial_product_data=[A,B]`, `_partial_scoring_result={}`, `_partial_comparison={}`, `_build_partial_response(elapsed_seconds=30.0)` ⇒ `resp.get("scoring_v2") is None`, `"scoring_v2" in resp`, `resp["metadata"]["partial"] is True`, `resp["success"] is True` | **RED** — 70/69, `win_margin` 1 |
| 4 | **flag ON**, early-buffer-only twin (`_partial_product_data=None`, `_early_specs_buffer=[{specs only}, {…}]`) ⇒ `resp.get("scoring_v2") is None` | **RED** — 70/69 (measured `EARLY` row) |
| 5 | **PIN**, flag OFF, parametrized over `("" unset, "false", "0", "no", "off")` ⇒ the exact § 1.3 values: `overall_score == {"product_a": 70, "product_b": 69, "winner_idx": 0}` and `win_margin == 1` | green |
| 6 | **PIN**, flag ON, real scores `{"product_0": {"overall": 62.0}, "product_1": {"overall": 48.0}}`, `winner_index=0` ⇒ `overall_score == {"product_a": 76, "product_b": 69, "winner_idx": 0}`, `win_margin == 7` — identical to flag OFF | green |
| 7 | **PIN**, flag ON, `_build_scoring_v2([A], {}, "electronics", 0) == {}` (NOT `None`) — pins the guard ORDERING at `:1105` | green |
| 8 | **PIN**, flag ON, the payload still carries the legacy fallback's premise: `result["scoring"]` is a dict with the six keys and is truthy, `result["winner_index"] == 0`, `result["overview"]["winner"]["product_index"] == 0`, `result["overview"]["products"][i]["overall_score"] is None` | green — the deliberate non-fix (§ 9.3) |
| 9 | **PIN**, flag ON, `json.dumps(result)` succeeds and `database_service._validate_renderable(result) is True` | green (measured 4,434 B / True) |
| 10 | **RED**, UNFLAGGED, `metadata.partial_stage` on the twin, parametrized over the four stash states ⇒ `"phase1"` (product_data only), `"scoring"` (+`_partial_scoring_result`), `"verdict"` (+`_partial_comparison`), `"identity"` (early buffer only) | **RED** — key ABSENT in all four (measured) |
| 11 | **PIN**, a NON-partial `build_comparison_response` (no `metadata=` kwarg) has no `partial_stage` key | green |
| 12 | **PIN**, the reader: unset ⇒ False; `"1"/"true"/"TRUE"/"yes"/"on"` ⇒ True; `"false"/"0"/""/"maybe"` ⇒ False; a `setenv` AFTER import flips the very next call (per-call read, never a module global) | green once written |
| 13 | **PIN**, flag ON, the top-level key SET of the partial response equals the flag-OFF key set exactly (`sorted(result)` compared across the two states) | green |

Parametrisation axes: flag string × `scoring_result` shape × stash state × `winner_index
∈ (0, 1)`.

---

## 5. Gates

1. **TDD red-first.** Write the file, run it alone
   (`python -m pytest tests/test_partial_response_no_fabricated_scores.py -q
   -p no:cacheprovider --timeout=120`), record `.qa-w4/W4-4-RED.txt` showing 1–4 and 10
   RED and 5–9, 11–13 green **before** any edit to `app/`.
2. **Comm gate — module-reference set for THIS unit.** The union, measured at
   `b63a8368`:
   ```
   grep -rlE "response_builder|structured_comparison_service|build_comparison_response|_build_scoring_v2|scoring_v2|_build_partial_response|partial_stage" tests/ --include=test_*.py
   grep -rl  "SmartCompareApp" tests/ --include=test_*.py
   ```
   sorted, de-duplicated, **plus this unit's own new file** = **203 files** (of 608
   `tests/test_*.py` in the tree). Component counts, all measured:
   `response_builder|structured_comparison_service` 189 · `build_comparison_response` 37 ·
   `_build_scoring_v2` 11 · `scoring_v2` 30 · `SmartCompareApp` scanners 10. The
   SmartCompareApp scanners are in the set deliberately — this unit changes a shape the
   client reads, and the standing rule (CLAUDE.md, "Five more gate rules") says a backend
   test that SCANS `SmartCompareApp/` belongs in the set whenever a client contract
   moves. Record the list to `.qa-w4/comm-set-W4-4.txt`. Base run BEFORE the edit (this
   worktree IS `b63a8368`), head run after green, `-m "not (live_unit or live_db or
   integration)" --timeout=120 -q -p no:cacheprovider` plus `--deselect` for every id in
   `tests/.pre_impl_failures.txt`; `comm -13 <(sort base) <(sort head)` must be empty.
3. **Byte-identity gate: N/A, with the reason.** `scripts/verify_flag_byte_identity.py`
   drives `extract_price_from_html` only, and this unit does not touch
   `app/services/price_service.py` (nor any module on the extraction spine) — measured:
   the changed surfaces are `response_builder._build_scoring_v2` and
   `structured_comparison_service._build_partial_response`, and
   `grep -rn "scoring_v2" app/ --include=*.py` shows **zero** consumers outside
   `response_builder.py` itself. The harness therefore has literally nothing to observe.
   Flag-OFF identity is carried instead by red tests 5/6/7/13, by the 489-node
   flag-simulated run recorded in § 3, and by the 33 existing files listed there.
4. **Ruff + py_compile**:
   `python -m ruff check --select E9,F63,F7,F82 --no-cache app/services/response_builder.py
   app/services/structured_comparison_service.py
   tests/test_partial_response_no_fabricated_scores.py`, then `python -m py_compile` on
   all three.
5. **Full free-tier suite before merge**, same marker/deselect shape as gate 2; failures
   only on ids already in `tests/.pre_impl_failures.txt` / the recorded comm base.
6. **Fable review before commit. Agents never commit.** The CLAUDE.md flag row is a
   merge-time item.

---

## 6. Mutation checks (REQUIRED — record each in `.qa-w4/W4-4-MUTATIONS.txt`, restore after each)

| mutation | tests that MUST redden |
|---|---|
| Delete the `return None` branch at `:1107` (revert § 2.3) | 1, 2, 3, 4 |
| Make `_scoring_overall_absent` return False unconditionally | 1, 2, 3, 4 |
| Weaken `_scoring_overall_absent` to `not scoring_result` only (drop the per-product `overall` check) | 2 (the `{"scores": {"product_0": {"overall": 62.0}}}` and `{"overall": None}` rows) |
| Move the new branch ABOVE the `len(product_data) < 2` guard | 7 |
| Make `_honest_partial_scoring_enabled()` return True unconditionally | 5 |
| Read the env into a module-level constant at import instead of per call | 12 |
| Return `{}` instead of `None` | 1, 2, 3, 4 (each asserts `is None`, and `{} is None` is False) |
| `del result["scoring_v2"]` instead of `None` | 1, 3, 13 (`"scoring_v2" in result`) — and `test_timeout_partial_integration.py:242-250` in the comm gate |
| Also null `overall_score`'s fields while KEEPING the block (the rejected narrow variant) | 1, 2, 3, 4 |
| Delete `partial_stage` from the `metadata=` kwarg at `:3257` | 10 |
| Hard-code `_partial_stage()` to `"phase1"` | 10 (the `scoring`/`verdict`/`identity` rows) |
| Add `partial_stage` to the auto-built metadata block instead of the partial kwarg | 11 |
| Touch `calibrate_score`'s `70 + (raw-50)*0.5` | 5, 6 — and `tests/test_calibration_collapse_v2.py` (11 nodes) in the comm gate |

Test 8 has no mutation target by construction (it pins a deliberate NON-change — that
the crown does not move). Say so in the report rather than inventing one.

---

## 7. Activation order

1. `ENABLE_HONEST_PARTIAL_SCORING` is **safe to flip on the CURRENT pre-OTA client**
   (`97b5f15`): measured in § 10, no crash, no crown change, no CTA change. That is the
   floor, not the goal.
2. Flip it only **after** the pending `eas update --branch preview` lands, because the
   FE half — widening `results.partial.note` (`en.json:768`, today
   `"Prices are still settling — tap to refresh in a moment."`) to say the *verdict* is
   provisional, not just the prices — is what makes the removed sections read as honesty
   rather than as an empty screen. Without it the user sees a partial with one verdict
   line, no bars, no pills and an extra blank spacer, and the copy still only talks about
   prices.
3. `metadata.partial_stage` ships with the deploy (unflagged) and is INERT until W4-13
   reads it in `log_search`. It has no canary of its own.
4. Canary line to watch after the flip: the existing
   `"[L2.7] compare_from_text hard-cap %.1fs hit"` WARNING (`:3356`) and
   `"[stream] hard cap %.1fs hit"` (`:4209`), now correlatable with
   `metadata.partial_stage`. PO-RECORDED-MEASURED-13 puts the organic cap-hit rate at
   **15.4 %** (n=1,513), so this path is not rare.
5. No coupling with any other flag was found. `ENABLE_FULL_STREAM_DEADLINE` (default OFF)
   only adds a fourth way to reach the SAME `_build_partial_response`;
   `ENABLE_BUNDLE_C_SCORING` gates `scoring_service`, never `:1827`.

---

## 8. Honest limits

1. **Flag ON removes three rendered sections from the partial screen.** Measured from
   the guards at HEAD and at `97b5f15`, with `scoring_v2` null:
   * `ResultsContent.tsx:423` (`scoring_v2 && scoring_v2.dimensions && length >= 3`) —
     the three-bar `DimensionBars` block disappears. Today it renders three honest,
     product-derived bars (§ 1.5).
   * `:480` (`scoring_v2?.confidence_legs`) — the confidence pill row disappears. Today
     it renders `{"price": "strong", "reviews": "strong", "specs": "weak"}` (measured).
   * `:403` → `RunnerUpWinsCard`: `dimensions` becomes `undefined`, `runnerUpWinningDims`
     returns `[]` (`RunnerUpWinsCard.tsx:53`), `keyTradeoff` is `''` (measured), so the
     card self-hides at `:96`.
   * `:362` — `FactualVerdict` is replaced by `<Text>{verdictBody}</Text>` =
     `overview.winner.reason` = `'Alpha Phone is the stronger overall pick.'` (measured).
   * `:385` — `PersonalizationChip` stops rendering; net-zero, it already hides itself
     with `applied_shifts: []` (measured).
   * `:528` — `!scoring_v2 && scoring` becomes true, so an **empty** `<View
     style={styles.section} testID="results-legacy-scoring-fallback" />` spacer is
     inserted. Byte-identical block at `97b5f15:508-518`.
   This is the unit's real cost and it is a product trade-off, not a bug. See § 11.1.
2. **The crown does not move.** No backend-only variant changes which product is
   crowned on a no-scoring partial: `scoring_v2` present ⇒ `70 >= 69` ⇒ 0;
   `scoring_v2` null/absent ⇒ `winner_index === 1 ? 1 : 0` ⇒ 0 (measured
   `winner_index = 0`). The user still sees a definitive winner chosen by input order.
   Closing that needs the FE half plus a product decision about what a partial should
   show instead — out of scope, recorded.
3. **Persisted rows are not migrated.** Every partial already written to
   `comparisons.full_response` keeps its 70/69 and will keep rendering it from History.
   No backfill in this unit.
4. **Both streaming `STREAM_TIMEOUT` bodies are untouched** (`:4016`, `:4232`): they are
   `success:false`, carry a TOP-LEVEL `partial: true` (not `metadata.partial`), and
   never call `build_comparison_response` — so they carry neither a fabricated
   `scoring_v2` nor a `partial_stage`. If W4-13 wants a stage on those, it is a second
   site.
5. **`metadata.partial_stage` is a producer only.** Nothing reads it after this unit;
   `search_logs` still records a partial as `success=True`
   (`text_routes.py:892`, `PO-RECORDED-MEASURED-10`). The cap-hit rate does not become
   measurable until W4-13 lands the consumer. Do not claim otherwise in the PR.
6. **`results.partial.note` is NOT widened here.** It is `en.json:768` + its `ar.json`
   twin, RN, OTA-gated. Recorded for the FE half. (The review cites `en.json:758` —
   drift +10, § 9.1.)
7. **The A3 half-score case (`{"scores": {"product_0": {"overall": 62.0}}}`) is covered
   by the predicate but its reachability through the orchestrator was NOT established**:
   `compute_scores` is called once and produces both products or neither. It is pinned
   because `build_comparison_response` is a public function and because the review's fix
   text asks for it; treat it as defence-in-depth, not a reproduced production case.
8. **Coverage of "does the flag break any existing test" is measured but bounded**: the
   489-node flag-simulated run covers the 33 files that name `scoring_v2` or build with
   an empty `scoring_result`. The 203-file comm gate at head-with-flag-OFF is what
   settles the rest, and CI runs flag OFF.

---

## 9. Spec disagreements with the review

### 9.1 Anchor drift, per anchor, resolved at `b63a8368`

| review anchor (`76ace90`) | at HEAD | note |
|---|---|---|
| `response_builder.py:1105-1146` | **`:1105-1146` — ZERO drift** | verified by `git show 76ace90:…` — `:1105` is `if len(product_data) < 2:`, `:1107/:1108` the `, 50)` defaults, `:1147` `dimensions = build_dimensions_v2(...)` on BOTH. `response_builder.py` has not moved in this region. |
| `verified.json` `response_builder.py:1107` | `:1107` | exact |
| `structured_comparison_service.py:2956` | **`:3185`** (`scoring_result = self._partial_scoring_result or {}`) | drift **+229**; `_build_partial_response` is now `:3161`, its `build_comparison_response` call `:3229`, its `metadata=` kwarg `:3257` |
| `ResultsScreen.tsx:746` / `:740-747` | **`:772-778`** at HEAD, **`:689-695`** at the phones' `97b5f15` | same code, three line bases |
| `ResultsContent.tsx:528` (`!scoring_v2 && scoring`) | `:528` at HEAD, `:512` at `97b5f15` | |
| `ResultsContent.tsx:243 / :402 / :459 / :550` (impact text) | not re-resolved individually; the four consumers were re-derived from the prop graph instead — `winnerIndex={presentationWinnerIndex}` is threaded once at `ResultsScreen.tsx:787` | |
| `text_routes.py:630` (PO-RECORDED-MEASURED-10) | **`:892`** | drift **+262**; W4-13's line, not ours |
| `structured_comparison_service.py:3440` (PO-RECORDED-MEASURED-13) | **`:3708`** (`comparison, usage = await generate_comparison(`) | drift **+268**; W4-13's line |
| `en.json:758` (`results.partial.note`) | **`:768`** | drift **+10** |

### 9.2 The review row's fix column — "none — a degraded path only" — is overridden

Flagged, default OFF, per Fable's standing rule, because the change IS visible to the
CURRENT client: § 8.1 lists four rendered blocks that change. The review's own synthesis
("the synthesis argues no fork") looked at the crown, which indeed does not fork — but
the crown is not the only thing `scoring_v2` drives.

### 9.3 "The fix only PARTLY closes it" (second vote) — confirmed, and stated as a limit

Reproduced independently: `{}` is truthy, `?? 0` makes `0 >= 0` crown product_0, and
omitting the block entirely falls back to `winner_index`, which is also 0. **No
backend-only variant changes the crown.** This spec does not pretend otherwise; test 8
pins the non-change so nobody later mistakes it for a regression.

### 9.4 The finding's "emit `overall_score: {product_a: None, product_b: None,
winner_idx: None}` for shape stability" is REJECTED, on measurement

It can FLIP a crown (§ 2.8, `HYPO` row), whereas null/absent cannot. Recorded rather
than silently dropped.

### 9.5 The review's `test_first` assertion is weaker than what this spec asks

It proposes `result['scoring_v2'].get('overall_score', {}).get('product_a') is None`
and `win_margin in (None, 0)` — both of which a truthy `{}` would satisfy, i.e. the
exact no-op the verifier warned about. The tests here assert
`result.get("scoring_v2") is None`.

### 9.6 Scope split with W4-13, stated so neither unit assumes the other

W4-4 **produces** `metadata.partial_stage`. W4-13 **consumes** it (its own red-test row
says "a partial increments `metadata.partial_stage`") and owns the `log_search`
`success=False` change at `text_routes.py:892`. W4-4 changes no logging.

### 9.7 Product decisions this spec does NOT make

* What a partial should SHOW instead of a crown (hide the winner? show both as
  provisional? a "still settling" verdict card?) — needs the FE half and Ahmed.
* Whether partials should be persisted to History at all
  (`_validate_renderable` says yes today; measured).
* Whether the removed dimension bars / confidence pills should be re-emitted from a
  separate, scorer-independent block so the partial screen keeps its honest content.
  That is § 11.1 and it is a design change, not a line.

---

## 10. Blast radius

### 10.1 Backend

* `_build_scoring_v2` has exactly **one** caller: `response_builder.py:1827`
  (`grep -n "_build_scoring_v2" app/`). It is also imported by 11 test files.
* `build_comparison_response` has exactly **three** callers, all in the orchestrator
  (`grep -rn "build_comparison_response(" app/ scripts/`):
  `structured_comparison_service.py:3229` (`_build_partial_response`), `:3825` (the sync
  full response), `:4598` (the streaming `complete`). Sites `:3825` and `:4598` always
  pass a real `scoring_result` from `compute_scores`, so the flag cannot reach them;
  only `:3229` can, and only when the cap fired before `:3699`.
* **Zero** non-builder consumers of `scoring_v2` in `app/`:
  `grep -rn "scoring_v2" app/ --include=*.py` outside `response_builder.py` returns only
  four comments (`home_routes.py:525/:854`, `scoring_service.py:1450/:1576/:3719`,
  `structured_comparison_service.py:971`) and no reads.
* `home_routes._extract_winner_loser_prices` (`:150`) — the `/home/savings` aggregate —
  reads `full_response["winner_index"]` and `products[i].price`, **never** `scoring_v2`
  (read in full). The SavingsBanner is therefore untouched by this unit, in both the
  flag-ON and the `ENABLE_HOME_SAVINGS_AGGREGATE` RPC paths.
* `database_service._validate_renderable` (`:291`) reads `overview.products` /
  `products` / `metadata.query` only — measured True with `scoring_v2: None`.
* `_build_partial_response`'s three call sites (`:3355`, `:3996`, `:4206`) all take the
  new `partial_stage` automatically; none of them is edited.

### 10.2 Client — read-only, at HEAD **and** at the phones' `97b5f15`

Every `scoring_v2` read in `SmartCompareApp/src`, with its behaviour under `null`,
`undefined` and a present-but-nulled `overall_score`:

| read | HEAD | `97b5f15` | `scoring_v2 = null` | `absent` | fields nulled |
|---|---|---|---|---|---|
| `const scoring_v2 = (result as any)?.scoring_v2` | `ResultsScreen.tsx:360` | `:324` | `null` | `undefined` | dict |
| `(scoring_v2?.overall_score?.product_a ?? 0) >= (… product_b ?? 0)` → `scoringV2WinnerIndex` | `:772-774` | `:689-691` | not consulted | not consulted | `0 >= 0` → **0** |
| `scoring_v2 ? scoringV2WinnerIndex : (winner_index === 1 ? 1 : 0)` | `:776-778` | `:694-695` | → `winner_index` (**0** measured) | same | **0** |
| `ctaVariant` margin | `:463` `scoring_v2?.win_margin ?? overview.winner.margin` | `:412` **`scoring?.win_margin`** — a key the wire never carries, so the phones are permanently `'default'` | HEAD: `0` → `'close'`, same as today's `1` → `'close'`; phones: unchanged | same | same |
| `scoring_v2 && scoring_v2.factual_verdict?.line1` | `:362` | `:346` | falls to `<Text>{verdictBody}</Text>` | same | block still renders |
| `scoring_v2 ? <PersonalizationChip …>` | `:385` | `:369` | not rendered (already self-hiding) | same | rendered |
| `dimensions={scoring_v2?.dimensions}` → `RunnerUpWinsCard` | `:403` | `:387` | `undefined` → `Array.isArray` guard (`RunnerUpWinsCard.tsx:53`, identical at `97b5f15:53`) → `[]` → card self-hides (`:96`) | same | card renders |
| `scoring_v2 && scoring_v2.dimensions && length >= 3` → `DimensionBars` | `:423` | `:407` | block not rendered (so `DimensionBars` is never called with `undefined`) | same | rendered |
| `scoring_v2.comparison_quality === 'weird'` | `:425` | `:409` | unreachable | same | reachable |
| `details={scoring_v2.confidence_details ?? {}}` | `:469` | `:453` | unreachable | same | reachable |
| `scoring_v2?.confidence_legs` → `ConfidencePills` | `:480` | `:464` | not rendered | same | rendered |
| `!scoring_v2 && scoring` → legacy spacer | `:528` | `:512` | **renders** an empty `<View>` | same | not rendered |
| `scoring_v2?: ScoringV2` | `types.ts:484` | same | type-only; every runtime read is `any`-cast or `?.` | same | `overall_score: OverallScore` would disagree with `null` fields |

**No crash on any path, in either shape, on either client build** — verified by reading
every guard rather than by inference. `DimensionBars` is the only consumer that would
throw on `undefined` (`DimensionBars.tsx:67` calls `dimensions.filter` unguarded) and it
is unreachable, because its render site is itself gated on `scoring_v2 &&
scoring_v2.dimensions`.

### 10.3 Wire / persistence

`json.dumps` of the flag-ON partial succeeds (4,434 B measured). The persisted
`full_response` gains `metadata.partial_stage` and loses `scoring_v2`'s value; History
re-renders it through the same `ResultsScreen`, so the § 10.2 table applies there too.
Rows written before the flip keep their fabricated 70/69 (§ 8.3).

---

## 11. Open rulings requested (Fable decides; the spec does not)

1. **The three lost sections (§ 8.1).** Options: (a) ship as specified — a no-scoring
   partial shows the verdict line, the accordion, the cohort badge and the feedback
   card, and nothing scorer-derived; (b) narrow the flag to null only `overall_score` +
   `win_margin` — **rejected here on measurement** (it can flip a crown, § 2.8); (c) a
   follow-up unit that re-emits the product-derived `dimensions` and `confidence_legs`
   from a block that does not pretend to be `scoring_v2`. The spec ships (a) and
   recommends logging (c) as its own row, because today's partial screen is internally
   contradictory (every dim winner says product_1, the crown says product_0 — § 1.5) and
   removing the bars removes the contradiction rather than adding a gap.
2. **`null` vs popping the key.** The spec picks `null`, on the measured strength of
   `test_timeout_partial_integration.py:242-250`. Confirm, so the implementer does not
   "tidy" it into a `pop`.
3. **`metadata.partial_stage` unflagged.** Precedent `metadata.data_freshness_shaky`;
   measured: no client read, no test pins the metadata key set. Confirm.
4. **Stage vocabulary** — `identity | phase1 | scoring | verdict | none`. If W4-13 wants
   different strings in `search_logs`, they should be agreed now, since the two units
   share the key.
5. **The FE half.** Widening `results.partial.note` (`en.json:768` + `ar.json`) so the
   caveat covers the verdict and not only prices is OTA-gated and is NOT built here.
   Confirm it becomes its own mobile-wave row rather than riding this PR.

---

# FABLE REVIEW RULINGS (binding, 2026-09-23) — W4-4 `ENABLE_HONEST_PARTIAL_SCORING` + `metadata.partial_stage`

Reviewer verdict SOUND_WITH_CHANGES (Opus 5.5 adversarial spec review, read-only, at `b63a8368`). The defect reproduces in both the builder and the orchestrator twin (70/69, margin 1, crown by input order); every anchor holds; the 97b5f15 client-impact table holds (no crash on null/absent, crown stays at index 0, the bars/pills/runner-up card/FactualVerdict/personalization chip AND the RevealBurst stop rendering). Everything below overrides the spec body where they conflict.

## R1 (BLOCKING → design) — ruling 1 is RE-RULED into a stage split under the same flag
The spec's premise "no backend-only variant changes the crown on a no-scoring partial" is FALSE on its own §1.4 ORCH fixture: `compute_scores` on the post-gather stash takes 0.30 ms (pure CPU, no provider call) and crowns Beta (56.8 vs 77.1), the product every dimension names, with the factual verdict "Beta Phone comes in 40% cheaper." The specced flag-ON output instead deletes that evidence and keeps an input-order crown with "Alpha Phone is the stronger overall pick." — net honesty goes DOWN. Therefore, with `ENABLE_HONEST_PARTIAL_SCORING` ON:
- **(i) post-gather stash present (`_partial_product_data` set, post fairness/currency guard) and scoring absent ⇒ COMPUTE** `scoring_result = compute_scores(stashed product data)` inside `_build_partial_response` and build normally (real `scoring_v2`, real crown, bars/pills/card kept). No LLM call, no network; the stage is `post_gather`.
- **(ii) early-buffer-only (identity stage, no product data) ⇒ `scoring_v2: null`** (never popped), as the spec proposes.
- **(iii) whenever `scoring_v2` is nulled, ALSO blank `overview.winner.reason`, `key_tradeoff` and the recommendation alias** — the finding's own fix text, silently dropped by §2.7's must-not-touch list, which is overturned to exactly that extent. Otherwise the phones' only verdict is an unqualified "<product_0> is the stronger overall pick." (`ResultsContent.tsx:346-361` at 97b5f15, `SCORE_INTERNALS_RE` does not match it).
- (c) re-emitting product-derived dims from a non-`scoring_v2` block is a recorded follow-up, not this unit.

## R2 — `null`, not absent: CONFIRMED, rationale corrected
`tests/test_timeout_partial_integration.py:242-250` does NOT protect null over pop (a simulated pop fired 8 times across 112 passing nodes; that test builds with real 64/55 scores and CI runs flag OFF). Null is right because both client generations treat null and undefined alike and the top-level key set stays stable. The new tests 1, 3 and 13 are the only pins — keep all three; fix the mutation-table row.

## R3 — `metadata.partial_stage` unflagged: AGREED
No client read at 97b5f15 or HEAD; the client never iterates `metadata`; the only backend iteration (`feedback_service.py:50`) copies all keys but one; `_validate_renderable` reads only `metadata.query`; the 203-file comm set is unaffected. Precedent `data_freshness_shaky`. It persists into `comparisons.full_response` (History and public share) — acceptable, stated.

## R4 — stage vocabulary (agree with W4-13 now)
Drop `none` (unreachable: every call site gates on `_partial_has_usable_data`). Values describe where the cap fired: `gather` (early buffer) / `post_gather` / `scoring` / `verdict`. The docstring says "the stage the partial CARRIED", not "the last stage that landed": on SSE the stream never stashes, so the tail-deadline partial at `:~3996` would report the early-buffer value after scoring and verdict ran — latent while phones use REST (`ENABLE_EXPO_FETCH_SSE_DEFAULT=false` at 97b5f15 and HEAD) and `ENABLE_FULL_STREAM_DEADLINE` is OFF; record a follow-up to stash on the streaming path.

## R5 — the FE half is its own OTA-gated mobile-wave row, ranked below R1(iii)
The copy must say the VERDICT is provisional, not only the prices.

## R6 — test-list corrections
Test 8 is rewritten for the stage split: post-gather ⇒ crown = the `compute_scores` winner (Beta on the fixture) with real `scoring_v2`; early-buffer ⇒ `winner_index` 0 with `scoring_v2: null` AND reason/key_tradeoff blank (mutation: skip the blanking ⇒ red). Tests 5, 6, 9, 11, 13 stay as labelled Preserve pins (they pass with the fix removed). Test 2's `{'scores':{'product_0':…}}` / `{'overall': None}` rows are labelled defence-in-depth for the public builder (unreachable through the orchestrator — settled). Comm set = 204 with the new file. §8.1 adds the RevealBurst.

## R7 — canary and old rows
The canary splits by `partial_stage` before claiming impact (the GPT verdict is the slow stage, so cap-during-verdict partials already carry real scores and the flag is inert for them). Rows persisted before the flip keep 70/69 forever; any backfill uses `metadata.partial == true AND scoring.scores == {}` as its predicate. Byte-identity: flag OFF byte-identical (the 203-file set shows identical failure sets in both states — the new file is the sole guard, so its mutations are load-bearing).

## R8 — merge order
After W4-1 (scs anchors after `:1214` shift +5; no textual conflict).
