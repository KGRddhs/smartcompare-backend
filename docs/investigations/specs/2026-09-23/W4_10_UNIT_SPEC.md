# W4-10 — `compute_scores` must spell the product the way the display side already spells it

Finding `CR-DELTA-CORRECTNESS-07` limb (a) — a LIVE M21-W3 regression. Backend only.
**Unflagged — regression fix.** Justification (one sentence): M21-W3 `7fb0b0d4` (merged
`eb331cb7`, PR #129, 2026-09-02) moved the *display* half of the product-name spelling onto
`dedup_brand_name` and left `compute_scores`' *internal* half on the raw `f"{brand} {name}"`,
breaking the invariant "the winner labels inside `dimension_winners` are drawn from the same
list `compute_tradeoff_pairs` is handed", so this unit restores an equality that held
byte-for-byte before that commit rather than introducing a new behaviour.

Worktree `C:/Users/SynAckITPC/Documents/AI/sc-w4-10`, branch
`feature/s65-w4-10-tradeoffs-dedup-parity`, base `b63a8368` (= `origin/main`).
Every line anchor below was verified at `b63a8368`. Every "today" claim below came out of a
probe run at that SHA with conftest-equivalent env (`load_dotenv(override=True)`,
`neutralize_credentials()`, `install_dotenv_guard()`, `PYTHONIOENCODING=utf-8`, zero network,
no `LIVE`); the probes live in the agent scratchpad, never in the worktree.

---

## 1. The defect, measured

### 1.1 The two halves, anchored at HEAD

`app/services/scoring_service.py`, inside `compute_scores` (`:1264`):

```
:1541    price_tiers_map = {}
:1544        name = f"{product.get('brand', '')} {product.get('name', '')}".strip()   # RAW
:1545        price_tiers_map[name] = tier
:1551        price_tiers_by_index[f"product_{i}"] = tier                              # index — safe
:1553    # Compute dimension winners
:1554    product_names = [
:1555        f"{p.get('brand', '')} {p.get('name', '')}".strip()                       # RAW  <-- the defect
:1556        for p in products_data
:1557    ]
:1559    dimension_winners = self.compute_dimension_winners(result_so_far, product_names, category)
:1566        "price_tiers": price_tiers_map,
:1569        "dimension_winners": dimension_winners,
:1577        "winner_evidence": winner_evidence,
```

`compute_dimension_winners` (`:2430`) stores the *string it was handed* as the winner label
(`:2467`, `:2469`, `:2473`, `:2475`: `winners[dim] = {"winner": product_names[0|1], ...}`).

The display side, same file and the orchestrator:

```
scoring_service.py:913-914   _product_name_for_evidence -> dedup_brand_name(brand, name)   # DEDUPED
                             (reached from build_winner_evidence :964, called at :1513)
structured_comparison_service.py:1149-1159  _display_product_names -> dedup_brand_name       # DEDUPED
```

`compute_tradeoff_pairs` (`:2547`) joins the two by **string equality**:

```
:2567    winner_name = product_names[winner_index]          # DEDUPED at every call site
:2568    loser_name  = product_names[1 - winner_index]
:2583    if info["winner"] == winner_name:  winner_dims.append(...)
:2585    elif info["winner"] == loser_name: loser_dims.append(...)   # info["winner"] is RAW
:2596    if not winner_dims or not loser_dims: return []
```

All three call sites pass the DEDUPED list:

| call site | `product_names` source | anchor |
|---|---|---|
| WS1 hard-cap partial (`_build_partial_response`) | `self._partial_product_names` (set at `:3700` from `_display_product_names`) | `scs:3187`, `scs:3199-3206` |
| sync compare | `_display_product_names(product_data)` | `scs:3692`, `scs:3790-3791` |
| SSE streaming compare | `_display_product_names(product_data)` | `scs:4424`, `scs:4532` |

### 1.2 Who introduced it — `git show`, not inference

`git log -S "_display_product_names" -- app/services/structured_comparison_service.py` and
`git log -S "def dedup_brand_name" -- app/services/text_sanitize.py` both return exactly ONE
commit: **`7fb0b0d4` "fix(currency,verdict,mobile,tests): M21 wave 3 …", 2026-09-02**
(merge `eb331cb7`, PR #129 `feature/m21-w3-quality`). Its whole `scoring_service.py` half is
5 insertions / 2 deletions:

```
@@ -907,8 +907,11 @@ def _product_name_for_evidence(p):
-    name = (f"{p.get('brand', '')} {p.get('name', '')}".strip()
-            or (p.get('name') or '').strip())
+    from app.services.text_sanitize import dedup_brand_name
+    name = dedup_brand_name(p.get('brand', ''), p.get('name', ''))
```

and its `structured_comparison_service.py` half replaced, at BOTH call sites, exactly the
expression `compute_scores:1554-1557` still carries:

```
-            product_names = [
-                f"{p.get('brand', '')} {p.get('name', '')}".strip()
-                for p in product_data
-            ]
+            product_names = _display_product_names(product_data)
```

`git blame -L 1541,1559` confirms `compute_scores` was untouched by that wave:
`:1554-1557` is `ee7789703` (2026-03-20), `:1544` is `a976fe0d8` (2026-03-20), `:1545-1551`
is `14b305c4d` (2026-09-01, M20 #102), `:1559` is `11e0c7064` (2026-03-26). **No line of the
defect site is younger than M21-W3.** Before `7fb0b0d4` both sides built the identical
f-string, so the equality at `:2583/:2585` held by construction. That is the contract this
unit restores.

### 1.3 RED reproduction — real output

Probe `w410_probe.py` (env as above). `compute_scores(products)` then
`compute_tradeoff_pairs(result["dimension_winners"], _display_product_names(products),
result["winner_index"], scores=result["scores"])` — i.e. exactly what `scs:3790` does.

```
CASE A_tomford
  raw  product_names (compute_scores internal) : ['TOM FORD TOM FORD OUD WOOD', 'TOM FORD TOM FORD TOBACCO VANILLE']
  disp product_names (_display_product_names)  : ['TOM FORD OUD WOOD', 'TOM FORD TOBACCO VANILLE']
  winner_index: 0  win_margin: 10.8
  price_tiers KEYS      : ['TOM FORD TOM FORD OUD WOOD', 'TOM FORD TOM FORD TOBACCO VANILLE']
  price_tiers_by_index  : {'product_0': 'premium', 'product_1': 'premium'}
  dimension_winners winner values: ['N/A', 'TOM FORD TOM FORD OUD WOOD']
  winner_evidence       : ['TOM FORD OUD WOOD leads on the overall picture']
  >> tradeoffs with DEDUPED names (prod path) len=0 []
  >> tradeoffs with RAW     names (control)   len=1 [{'winner_wins': {'dimension': 'presentation_score', 'product': 'TOM FORD TOM FORD OUD WOOD', 'margin': 14.1}, 'loser_wins': {'dimension': 'longevity_score', 'product': 'TOM FORD TOM FORD TOBACCO VANILLE', 'margin': 0}}]
  build_scores_summary tier lines: ['  TOM FORD OUD WOOD: stronger overall (price tier: unknown)', '  TOM FORD TOBACCO VANILLE: slightly behind overall (price tier: unknown)']

CASE B_xerjoff  (brand="Xerjoff", names "Xerjoff Naxos" / "Xerjoff Erba Pura")
  dimension_winners winner values: ['N/A', 'Xerjoff Xerjoff Naxos']
  winner_evidence       : ['Xerjoff Naxos draws stronger reviewer ratings']
  >> tradeoffs with DEDUPED names len=0 []      >> with RAW names len=1
  build_scores_summary tier lines: [... (price tier: unknown), ... (price tier: unknown), ...]

CASE C_control  (brand="Xerjoff", names "Naxos" / "Erba Pura" — no repeat)
  diverge: False
  dimension_winners winner values: ['N/A', 'Xerjoff Naxos']
  >> tradeoffs with DEDUPED names len=1   >> with RAW names len=1      # identical
  build_scores_summary tier lines: ['  Xerjoff Naxos: stronger overall (price tier: mid)', '  Xerjoff Erba Pura: slightly behind overall (price tier: premium)', ...]

CASE D_mixed   (only product 0 repeats: brand "Dior", name "Dior Sauvage")
  dimension_winners winner values: ['Dior Dior Sauvage', 'N/A']
  >> DEDUPED len=0   >> RAW len=1

CASE E_diorhomme (brand "Dior", names "Dior Homme Intense" / "Dior Sauvage Elixir")
  dimension_winners winner values: ['Dior Dior Homme Intense', 'N/A']
  >> DEDUPED len=0   >> RAW len=1
```

So: **`tradeoffs == []` on every brand-repeating pair, and identical on every
non-repeating pair.** The review's `[]` reproduces exactly.

### 1.4 The user-visible consequence, measured end to end

Probe `w410_probe2.py` runs the real
`response_builder.deterministic_verdict_fields(scoring_result, deduped_names, tradeoffs)`
(`:130`, `:170-176`) — the function `scs._deterministic_partial_verdict` (`:8133`, called
**unflagged** at `scs:3223`) and `reconcile_winner_prose` (`rb:1384`) both consume:

```
PAIR A_tomford(repeat)
  tradeoffs TODAY     len=0 -> key_tradeoff=''
  tradeoffs AFTER FIX len=1 -> key_tradeoff='TOM FORD TOBACCO VANILLE stays competitive on longevity.'
PAIR C_control(no repeat)
  tradeoffs TODAY     len=1 -> key_tradeoff='Xerjoff Erba Pura stays competitive on longevity.'
  tradeoffs AFTER FIX len=1 -> key_tradeoff='Xerjoff Erba Pura stays competitive on longevity.'   # unchanged
```

`key_tradeoff` is what the shipped client renders: `ResultsContent.tsx:169`
(`result.overview.winner.key_tradeoff`) → `RunnerUpWinsCard` `keyTradeoff` prop
(`ResultsContent.tsx:404`, `RunnerUpWinsCard.tsx:39-40/:88-95`). On the hard-cap partial path
a brand-repeating pair therefore ships an EMPTY runner-up caption today. That is the LIVE
half of the finding, and it is category-agnostic (fragrance houses repeat the brand
constantly; `Sony / "Sony WH-1000XM5"` shows the same divergence in case F).

### 1.5 Every place `compute_scores` spells a product key (complete)

| key in the result dict | spelling today | dedup'd today? | anchor |
|---|---|---|---|
| `scores` | `product_{i}` | n/a — index | `:1565` |
| `breakdown` keys (inside `scores`) | dimension names, never a product key | n/a | built in `_normalize_scores` `:2063` |
| `price_tiers` **keys** | RAW `f"{brand} {name}".strip()` | **NO** | `:1544-1546` |
| `price_tiers_by_index` keys | `product_{i}` | n/a — index | `:1551` |
| `dimension_winners[dim]["winner"]` **values** | RAW (via `product_names` `:1554-1557`) | **NO** | `:1554-1559`, `:2467-2476` |
| `winner_evidence` strings | `dedup_brand_name` | **YES** | `:913-914` → `:964` → `:1513` |
| `winner_index`, `win_margin`, `scoring_method`, `is_cross_tier`, `category`, `category_weights` | no product name | n/a | `:1562-1576` |

Two raw spellings, one deduped. **This unit fixes ONE of the two raw ones** —
`dimension_winners` — and deliberately leaves `price_tiers` alone; §3.3 gives the measured
reason and §9 asks for the ruling.

---

## 2. The design — one expression, unflagged

### 2.1 The change

`app/services/scoring_service.py`, replace `:1553-1557` (the comment stays, the list-comp
body changes) with:

```python
        # Compute dimension winners.
        # CR-DELTA-CORRECTNESS-07(a) — the SAME spelling the display side uses
        # (`structured_comparison_service._display_product_names`, which is what
        # every `compute_tradeoff_pairs` call site passes as `product_names`).
        # M21-W3 `7fb0b0d4` moved the display half onto `dedup_brand_name` and
        # left this half raw, so `info["winner"]` never matched
        # `product_names[winner_index]` for a brand-prefixed `name` and
        # `compute_tradeoff_pairs` returned [] (blank `key_tradeoff`).
        from app.services.text_sanitize import dedup_brand_name
        product_names = [
            dedup_brand_name(p.get('brand', ''), p.get('name', ''))
            for p in products_data
        ]
```

Function-local import, matching `_product_name_for_evidence:913` and
`_display_product_names:1155` in the same codebase (both import it inside the function;
`text_sanitize` is deliberately not a module-level import of `scoring_service`). **That is
the whole change: four lines of body plus the comment. No other line of any file.**

### 2.2 Flag

**Unflagged.** Justification and the evidence for it:

1. It is a regression fix, not a new behaviour: §1.2 shows byte-for-byte that before
   `7fb0b0d4` both sides built `f"{p.get('brand','')} {p.get('name','')}".strip()` and the
   equality at `:2583/:2585` held.
2. Every measured delta is strictly repairing and one-directional:
   `tradeoffs [] -> 1 pair`, `key_tradeoff "" -> real prose`. No measured case goes the
   other way (§4, §7).
3. On non-repeating inputs the change is a no-op: `dedup_brand_name(b, n) ==
   f"{b} {n}".strip()` for every str/str pair whose `name` does not start with `brand`
   (probe `w410_probe5.py`, rows `('Xerjoff','Naxos')`, `('Apple','Applesauce')`,
   `('','Naxos')`, `('Xerjoff','')`, `('','')`, `{}` — all `same=True`).
4. A flag would leave a LIVE regression live behind a dark default with no canary planned
   for it; the project's own precedent for this shape is `7fb0b0d4`'s own brand-dedup unit,
   shipped **unflagged, "presentation-only"** (its commit message says so).

If Fable overrules (§9 ruling 1), the flag is `ENABLE_TRADEOFF_DEDUP_PARITY`, default OFF,
read PER CALL, copying the nearest reader in the SAME file —
`_category_value_badge_enabled` (`scoring_service.py:432-437`):

```python
def _tradeoff_dedup_parity_enabled() -> bool:
    import os
    return os.environ.get("ENABLE_TRADEOFF_DEDUP_PARITY", "").strip().lower() in (
        "1", "true", "yes", "on",
    )
```

and `:1554` becomes a ternary whose OFF branch is the byte-identical HEAD expression.
Red tests 1-6 then take `flag_on`; pin 8 (rollback) becomes load-bearing.

### 2.3 MUST NOT TOUCH

Named list. Any diff hunk outside `scoring_service.py:1553-1557` is out of scope for W4-10:

1. **`scoring_service.py:1541-1551`** — the `price_tiers_map` key stays RAW. Measured
   reasons in §3.3.
2. **`scoring_service.py:1551`** `price_tiers_by_index` — already index-keyed; untouched.
3. **`scoring_service.py:913-914` / `:964` / `:1513`** (`winner_evidence`) — already
   deduped; the fix makes it AGREE with `dimension_winners`, it does not edit it.
4. **`compute_dimension_winners` (`:2430-2477`, assignments at `:2467`/`:2469`/`:2473`/`:2475`)** — it stores whatever it is handed; the
   defect is the argument, not the function. No signature change, no dedup inside it.
5. **`compute_tradeoff_pairs` (`:2547-2613`) and `_loser_strongest_dim` (`:2615-2647`)** —
   no fuzzy/normalised matching. String equality is the contract; fixing the producer is the
   fix. A `casefold()`/`in` match would silently pair the wrong product.
6. **`structured_comparison_service.py:1149-1159`** `_display_product_names` — the display
   half is correct; it is the reference spelling.
7. **`structured_comparison_service.py:3187-3189`** — the `_partial_product_names` fallback
   `[p.get("name", "") for p in product_data]` (a THIRD, bare-`name` spelling used only when
   the stash is None, i.e. a cancel during the Phase-1 gather). Real, out of scope, §8 limit 4.
8. **`response_builder.py:1726` and `:1865`** (`_compute_value_match`,
   `_compute_budget_mismatch`) — both look `price_tiers` up with the RAW
   `f"{brand} {name}".strip()`. They MATCH the raw key today and must keep matching; they
   only break if `price_tiers` is deduped, which this unit does not do.
9. **`app/api/home_routes.py:455-464`** (`_select_smart_pick` priority-match) — see §10.3:
   the branch is already dead for an unrelated reason and the unit must not "fix" it here.
10. **No new import at module scope**, no change to the `result = {...}` literal
    (`:1561-1578`), no reordering of keys.

### 2.4 Why this beats the alternatives

* *Normalise inside `compute_tradeoff_pairs`* — rejected: it papers over a producer bug at
  one of several consumers, leaves the shipped/persisted `dimension_winners` value wrong,
  and adds a fuzzy join where an exact one is correct.
* *Make `_display_product_names` raw again (revert the display half)* — rejected: it
  un-ships a deliberate M21-W3 user-facing fix ("TOM FORD TOM FORD OUD WOOD") that is live
  on phones through `winner_evidence`, `winner_declaration` and share text.
* *Have `compute_scores` return BOTH spellings and let callers pick* — rejected: a second
  key in the persisted `scoring` block for every comparison, for one join.
* *Also dedup `price_tiers` in the same hunk* — rejected for W4-10; §3.3 measures a live
  `value_badge` flip it would cause on the DEFAULT flag state.

---

## 3. What the change does NOT change — measured

### 3.1 Identical output on non-repeating input

`w410_probe5.py`, `raw = f"{p.get('brand','')} {p.get('name','')}".strip()` vs
`dedup_brand_name(p.get('brand',''), p.get('name',''))`:

```
input                                          | RAW today                | dedup_brand_name         | same
{'brand': 'Xerjoff', 'name': 'Naxos'}          | 'Xerjoff Naxos'          | 'Xerjoff Naxos'          | True
{'brand': 'Apple',   'name': 'Applesauce'}     | 'Apple Applesauce'       | 'Apple Applesauce'       | True
{'brand': '',        'name': 'Naxos'}          | 'Naxos'                  | 'Naxos'                  | True
{'brand': 'Xerjoff', 'name': ''}               | 'Xerjoff'                | 'Xerjoff'                | True
{'brand': '',        'name': ''}               | ''                       | ''                       | True
{}                                             | ''                       | ''                       | True
```

### 3.2 The deltas that DO exist beyond the brand-repeat (state them, do not hide them)

Same probe:

```
{'brand': None,      'name': 'Naxos'}          | 'None Naxos'             | 'Naxos'                  | False
{'brand': 'Xerjoff', 'name': None}             | 'Xerjoff None'           | 'Xerjoff'                | False
{'brand': 'Xerjoff', 'name': '  Naxos  '}      | 'Xerjoff   Naxos'        | 'Xerjoff Naxos'          | False
{'brand': '  Xerjoff  ', 'name': 'Naxos'}      | 'Xerjoff   Naxos'        | 'Xerjoff Naxos'          | False
{'brand': 'tom ford','name': 'TOM FORD OUD WOOD'} | 'tom ford TOM FORD OUD WOOD' | 'TOM FORD OUD WOOD' | False
{'brand': 'Xerjoff', 'name': 'Xerjoff  Naxos'} | 'Xerjoff Xerjoff  Naxos' | 'Xerjoff  Naxos'         | False
{'brand': 123,       'name': 'Naxos'}          | '123 Naxos'              | RAISE AttributeError     | False
{'brand': 'Xerjoff', 'name': ['Naxos']}        | "Xerjoff ['Naxos']"      | RAISE AttributeError     | False
```

Four of these (`None` halves, whitespace, case-mismatched brand) are repairs that make
`dimension_winners` agree with `winner_evidence`, which is the point.

**The two `RAISE` rows are the only risk, and they are PRE-EXISTING, not new.** Measured
directly (`w410_probe6.py` + the follow-up one-liner): `compute_scores` with
`brand=123` / `name=['Naxos']` on a NON-degenerate pair already raises today —

```
brand=123 non-degenerate -> RAISE AttributeError 'int' object has no attribute 'strip'
name=list non-degenerate -> RAISE AttributeError 'list' object has no attribute 'strip'
```

because `build_winner_evidence:964 -> _product_name_for_evidence:914` calls the same
`dedup_brand_name` forty lines EARLIER in the same function (it is skipped only when
`reasons == []`, i.e. a degenerate tie — probe row `brand=123 (both products)` -> `OK`
with `winner_evidence=[]`). So the fix adds **no new crash surface**, and I recommend NOT
adding a defensive `str()` coercion (it would be scope creep, and it would mask an
already-live shape bug that belongs in its own row).

### 3.3 Why `price_tiers` stays RAW in this unit — the measurement

Deduping `price_tiers_map[name]` at `:1544` is a DIFFERENT change with a live blast radius.
Measured, `w410_probe2.py` / `w410_probe4.py`:

1. **`response_builder.py:1726` `_compute_value_match` breaks.** It looks the tier up with
   the RAW key. With deduped keys, for the TOM FORD pair:
   ```
   p0 raw_key='TOM FORD TOM FORD OUD WOOD'  price_tiers.get(raw)='premium'  price_tiers.get(dedup)=''
      _compute_value_match(raw,'mid')   = near
      _compute_value_match(dedup,'mid') = unknown
   ```
2. **`response_builder.py:1865` `_compute_budget_mismatch` breaks the same way:**
   `budget_mismatch(raw tier='premium') = True` vs `budget_mismatch(dedup tier='') = False`.
3. **`apply_value_badges` (`:2514`) FLIPS a user-facing badge on the DEFAULT flag state.**
   Its flag-OFF branch reads `legacy_tiers.get(product.get("name", ""), "mid")` — the BARE
   `name`. For a brand-repeating product the deduped key IS the bare name, so a lookup that
   misses today would start hitting:
   ```
   RAW-keyed  (today)  flag OFF -> value_badge='great_value'
   DEDUP-keyed(after)  flag OFF -> value_badge='fair_price'
     (legacy branch reads legacy_tiers.get(product['name']) = 'TOM FORD OUD WOOD')
     compute_value_badge(80,'mid')='great_value'   compute_value_badge(80,'luxury')='fair_price'
   ```
   `ENABLE_CATEGORY_VALUE_BADGE` is **OFF in prod** (CLAUDE.md:390; the M22 report lists it
   under "DARK — armed, fires on the next flip"), so that is a live badge change with no
   flag behind it.
4. The one thing deduping `price_tiers` WOULD repair is `build_scores_summary:2861`
   (`scoring_result["price_tiers"].get(name, "unknown")` with the DEDUPED `name`), which
   today feeds the GPT verdict prompt `price tier: unknown` for every brand-repeating pair
   (measured, §1.3 cases A/B/D/E; case C reads `mid`/`premium` correctly).

That is a real second defect with a real fix, and it needs the two `response_builder`
readers moved in the same hunk plus a `value_badge` ruling. **Follow-up row
`CR-DELTA-CORRECTNESS-07a2`, its own flag.** §9 ruling 2.

---

## 4. Preserve — existing tests on the touched paths, run at HEAD

All run with `-m "not (live_unit or live_db or integration)" -q -p no:cacheprovider`.

| suites | result |
|---|---|
| `test_scoring_service.py`, `test_winner_prose_reconciliation.py`, `test_m21_brand_dedup_and_verdict_copy.py`, `test_home_routes.py` | **230 passed**, 11 warnings, 17.64s |
| `test_category_dimensions.py`, `test_value_badge_category_dims.py`, `test_streaming.py`, `test_decomposed_services.py`, `test_missing_dim_coverage.py`, `test_missing_score_collision_v2.py`, `test_trust_edge_cases.py`, `test_trust_validation.py`, `test_m13_04_full_stream_deadline.py`, `test_endpoint_shapes_vs_jsx.py`, `test_hotfix_pros_cons_legacy_alias.py`, `test_fragrance_content_quality.py`, `test_compare_timeout_graceful.py`, `test_scoring_value_math_v11.py` | **311 passed**, 13 warnings, 46.74s |

**541 passed across the 18 suites that name the touched surface. Every one must stay green.**

What specifically is pinned, and why the fix cannot move it:

* `tests/test_scoring_service.py:876-910` — `compute_dimension_winners` called DIRECTLY with
  `["A", "B"]`. The function is untouched.
* `tests/test_scoring_service.py:1021-1060` — `compute_tradeoff_pairs` called DIRECTLY with
  hand-built `dimension_winners` and `product_names = ["Product A", "Product B"]`. Untouched.
* `tests/test_value_badge_category_dims.py:163` — the ONLY existing assertion on a
  `price_tiers` key literal: `scoring_result["price_tiers"]["BrandLux ProLux"]`. Fixture
  brand `"BrandLux"`, name `"ProLux"` (`:72-90`) — no repeat, and `price_tiers` is not
  touched anyway.
* `tests/test_value_badge_category_dims.py:288-299` — the flag-OFF GOLDEN
  (`tests/fixtures/value_badge_flag_off_golden.json`, all 9 categories). Its `_pair()`
  fixture (`:46-69`) is `("HouseA","ItemA")` / `("HouseB","ItemB")` — no repeat. Green
  either way; named here because it is the tripwire if anyone widens the hunk to
  `price_tiers`.
* `tests/test_m21_brand_dedup_and_verdict_copy.py` — the only suite that references
  `dedup_brand_name` / `_display_product_names` at all; it pins the display half, which
  this unit does not edit.
* No test in `tests/` asserts a `dimension_winners` winner value produced by
  `compute_scores` from a brand-repeating pair (grep over the 15 files naming
  `dimension_winners`: every one either builds the dict by hand or uses `"A"`/`"B"`/
  `"Product A"` names). **That absence IS the regression's escape route**, and red test 4
  below closes it.

---

## 5. Red tests — `tests/test_tradeoffs_dedup_parity.py`

New file. No env toggling (unflagged); if §9 ruling 1 goes the other way, wrap 1-6 in a
`flag_on` fixture using `monkeypatch.setenv` exactly as
`tests/test_value_badge_category_dims.py:33-43` does.

Shared fixture — two module-level helpers, no network, no DB:

```python
def _pair(brand_a, name_a, brand_b, name_b, amt_a=78.0, amt_b=95.0,
          rat_a=4.8, rat_b=4.2, rc_a=400, rc_b=150, category="fragrance"): ...
REPEAT  = _pair("Xerjoff", "Xerjoff Naxos", "Xerjoff", "Xerjoff Erba Pura")
CONTROL = _pair("Xerjoff", "Naxos",         "Xerjoff", "Erba Pura")
```

(The CONTROL pair is the REPEAT pair with the brand prefix removed from both names — same
prices, ratings, specs — so the two differ in exactly the spelling.)

| # | test | exact assertion | today |
|---|---|---|---|
| 1 | `test_tradeoffs_non_empty_for_brand_repeating_pair` | `r = svc.compute_scores(REPEAT)`; `to = svc.compute_tradeoff_pairs(r["dimension_winners"], _display_product_names(REPEAT), r["winner_index"], scores=r["scores"])`; `assert to != []` and `len(to) == 1` | **RED** (`[]`) |
| 2 | `test_dimension_winners_keys_match_winner_evidence_spelling` (the review's own `test_first`, verbatim inputs `brand="TOM FORD"`, `name="TOM FORD OUD WOOD"`) | every non-sentinel `v["winner"]` in `r["dimension_winners"].values()` (excluding `"tie"`/`"N/A"`) is a prefix-match of some string in `r["winner_evidence"]`; concretely `assert {v["winner"] for v in ...} - {"tie","N/A"} == {"TOM FORD OUD WOOD"}` and `r["winner_evidence"][0].startswith("TOM FORD OUD WOOD")` | **RED** (`{'TOM FORD TOM FORD OUD WOOD'}`) |
| 3 | `test_dimension_winner_labels_are_drawn_from_display_names` | `set(v["winner"] for v in dw.values()) - {"tie","N/A"} <= set(_display_product_names(REPEAT))` — the INVARIANT `compute_tradeoff_pairs` joins on, stated directly | **RED** |
| 4 | `test_key_tradeoff_prose_is_non_empty_for_brand_repeating_pair` | with `to` from test 1, `deterministic_verdict_fields(r, _display_product_names(REPEAT), to)["key_tradeoff"] == "Xerjoff Erba Pura stays competitive on longevity."` | **RED** (`''`) |
| 5 | `test_parity_repeat_vs_control` — parametrised over `("winner_labels", "tradeoff_len", "key_tradeoff_shape")` | for each: the value computed from REPEAT equals the value computed from CONTROL after substituting the product names. Concretely `len(to_repeat) == len(to_control) == 1`, and `to_repeat[0]["loser_wins"]["dimension"] == to_control[0]["loser_wins"]["dimension"]` | **RED** (1 vs 0) |
| 6 | `test_mixed_pair_only_one_product_repeats` — `("Dior","Dior Sauvage")` vs `("Chanel","Bleu de Chanel")` | `len(to) == 1`; `{v["winner"] for v in dw.values()} - {"tie","N/A"} == {"Dior Sauvage"}` | **RED** (`{'Dior Dior Sauvage'}`, `len 0`) |
| 7 | **PIN** `test_control_pair_byte_identical` — parametrised over `("dimension_winners", "price_tiers", "winner_evidence", "scores", "win_margin", "winner_index", "category_weights")` | `svc.compute_scores(CONTROL)[key]` equals the literal captured at HEAD for that key (inline expected values, not a golden file) | green today, must stay green |
| 8 | **PIN** `test_price_tiers_keys_stay_raw` | `set(svc.compute_scores(REPEAT)["price_tiers"]) == {"Xerjoff Xerjoff Naxos", "Xerjoff Xerjoff Erba Pura"}` and `svc.compute_scores(REPEAT)["price_tiers_by_index"] == {"product_0": "mid", "product_1": "premium"}` | green today; **the scope fence for §2.3 item 1 / §3.3** |
| 9 | **PIN** `test_value_match_lookup_still_resolves` | for each product of REPEAT, `r["price_tiers"].get(f"{b} {n}".strip())` is a non-empty tier (the `response_builder:1726/:1865` read) — `'premium'`/`'premium'` for the TOM FORD pair, `'mid'`/`'premium'` for REPEAT | green today; reddens if anyone dedups `price_tiers` |
| 10 | **PIN** `test_degenerate_and_empty_identity_unchanged` — parametrised over `("", "")`, `("Xerjoff", "")`, `("", "Naxos")`, `("Apple", "Applesauce")` | the `dimension_winners` winner labels for a pair built from each shape equal the RAW `f"{b} {n}".strip()` spelling (§3.1) | green today, must stay green |
| 11 | **PIN** `test_non_str_identity_raises_as_it_does_today` | `pytest.raises(AttributeError)` on `svc.compute_scores(_pair(123, "Naxos", 123, "Erba"))` | green today (§3.2); pins that the unit adds no coercion and no new swallow |
| 12 | **PIN** `test_single_product_and_three_product_shapes_unchanged` | one-product input still raises `KeyError: 'price_tiers'` (measured today); a three-product input's `dimension_winners` is `{}` when `len(product_names) < 2` is false but `compute_dimension_winners` is fed 3 names — assert the HEAD value, whatever it is, is unchanged | green today |

Tests 1-6 are RED today, 7-12 are PINS. Import `_display_product_names` from
`app.services.structured_comparison_service` and `deterministic_verdict_fields` from
`app.services.response_builder` so the tests exercise the REAL production join, not a
re-implementation of it.

---

## 6. Gates

1. **TDD red-first.** Write `tests/test_tradeoffs_dedup_parity.py`, run it ALONE before the
   edit:
   `python -m pytest tests/test_tradeoffs_dedup_parity.py -q -p no:cacheprovider --timeout=120`
   Record `.qa-w4/W4-10-RED.txt` showing 1-6 RED and 7-12 GREEN. Then edit, re-run, record
   `.qa-w4/W4-10-GREEN.txt`.

2. **Comm gate — module-reference sweep.** The union grep for THIS unit's touched module
   (`app/services/scoring_service.py`) and the symbols it produces/consumes:
   ```
   grep -rlE "scoring_service|compute_scores|compute_dimension_winners|compute_tradeoff_pairs|dimension_winners|build_scores_summary|price_tiers" tests --include=test_*.py
   ```
   **Measured: 78 files** (the narrower `scoring_service`-only grep is 64). Record the set in
   `.qa-w4/comm-set-W4-10.txt`. Run the set at BASE **before** the edit (this worktree IS
   `b63a8368`), then at HEAD after green **with `tests/test_tradeoffs_dedup_parity.py`
   appended**. Same invocation shape as `sc-w0-load/.qa-w0/run_comm_head_w04.py`:
   `-m "not (live_unit or live_db or integration)" --timeout=120 -q -p no:cacheprovider`
   plus `--deselect` for every id in `tests/.pre_impl_failures.txt` (**89 lines**, measured),
   split in two halves. `comm -13 <(sort comm-base) <(sort comm-head)` must be empty.
   **No SmartCompareApp scanner run is required** — §10.4 measures zero client contract
   change (the changed value is typed but never read by any component), so no jest/tsc
   gate for this unit. State that in the PR body rather than silently skipping it.

3. **Byte-identity corpus gate: N/A.** `app/services/price_service.py` is NOT touched (the
   diff is confined to `app/services/scoring_service.py:1553-1557`), and the harness
   `scripts/verify_flag_byte_identity.py` exercises `extract_price_from_html` only — a
   function that never reaches `compute_scores`, `compute_dimension_winners` or
   `compute_tradeoff_pairs` (zero call edges). Running it would be a guaranteed-equal
   no-op with zero discrimination. The rollback proof for this unit is instead pins 7-12
   (which assert the HEAD values literally) plus the 541-test Preserve set.

4. **Ruff + py_compile:**
   ```
   python -m ruff check --select E9,F63,F7,F82 --no-cache app/services/scoring_service.py tests/test_tradeoffs_dedup_parity.py
   python -m py_compile app/services/scoring_service.py tests/test_tradeoffs_dedup_parity.py
   ```

5. **Full free-tier suite before merge**, same marker/deselect shape as gate 2; the only
   permitted failures are ids already in `tests/.pre_impl_failures.txt` or in the recorded
   comm base.

6. **Fable review before commit. Agents never commit.** The PR body must carry: the
   `7fb0b0d4` provenance (§1.2), the unflagged justification (§2.2), §8 in full, and the two
   follow-up rows from §9.

---

## 7. Mutation checks (REQUIRED) — record in `.qa-w4/W4-10-MUTATIONS.txt`, restore after each

| mutation | tests that MUST redden |
|---|---|
| Revert `:1554-1557` to the raw f-string comprehension | 1, 2, 3, 4, 5, 6 (run each individually) |
| Use `dedup_brand_name(p.get('name',''), p.get('brand',''))` (arguments swapped) | 2 (`'TOM FORD OUD WOOD TOM FORD'`-shaped label), 3, 6 |
| Also dedup `price_tiers_map` at `:1544` (the scope-creep mutation) | 8 and 9 |
| Apply the dedup at `:1559` only (pass a deduped list to `compute_dimension_winners` but keep `product_names` raw for anything below) | nothing — proves `product_names` has no other reader in `compute_scores`; record the no-op honestly rather than inventing a target |
| Normalise inside `compute_tradeoff_pairs` (`info["winner"].casefold() in winner_name.casefold()`) instead of fixing the producer | 2 and 3 stay red (the persisted label is still wrong) while 1/4/5 go green — the measurement that justifies §2.4 |
| Add a `str()`/`or ""` coercion around the brand/name arguments | 11 |
| Move the `text_sanitize` import to module scope in `scoring_service.py` | none of 1-12; caught by review, not by test — note it in the report |

---

## 8. Honest limits

1. **`price_tiers` keys stay wrong.** `build_scores_summary:2861` still tells the GPT verdict
   prompt `price tier: unknown` for every brand-repeating pair (measured §1.3: cases A/B/D/E
   `unknown`, case C `mid`/`premium`). Fixing it requires moving
   `response_builder.py:1726` and `:1865` in the same hunk and ruling on the measured
   `value_badge` flip (§3.3). Own row, own flag.
2. **`_partial_product_names`'s fallback is a third spelling.** `scs:3187-3189` falls back to
   bare `[p.get("name", "") for p in product_data]` when the stash is None (a cancel DURING
   the Phase-1 gather). On that narrow path `compute_tradeoff_pairs` is joined against bare
   names and returns `[]` for EVERY product whose brand is non-empty, repeat or not — before
   and after this unit. Not measured end-to-end here (it needs the cancel-timing harness the
   critic file flags as never executed); stated as a known residual.
3. **The SSE streaming path is not driven end to end by this unit.**
   `docs/.../critic-m22-code-review.md:7` says the streaming path was never executed by any
   review lane and names "the CR-DELTA-CORRECTNESS-07(a) tradeoffs collapse" specifically as
   reasoned on the sync path only. My probes are unit-level too. The streaming call site
   (`scs:4424`/`:4532`) is textually identical to the sync one (`scs:3692`/`:3790-3791`), and
   pin 7 plus the Preserve run of `test_streaming.py` (in the 311) are the coverage I have.
   The fix is producer-side, so it cannot be path-dependent — but I did not execute the SSE
   generator, and the PR body must say so.
4. **The fix does not guarantee a NON-EMPTY `tradeoffs` for every pair.** It restores
   parity, not content. Measured counter-example (probe `w410_probe.py` case F,
   `Sony "Sony WH-1000XM5"` vs `Bose "QuietComfort Ultra"`, electronics): `len == 0` with
   the deduped names AND `len == 0` with the raw names — the winner's dims all tie or fall
   under the 5-point filter (`:2576`), so `winner_dims` is empty and `:2596-2597` returns `[]`
   legitimately. Red tests 1/5/6 deliberately use fragrance fixtures that produce a pair on
   the control, so the assertion is about parity, not about a universal non-empty.
5. **No `key_tradeoff` change on the MAIN (non-hard-cap) path today.** There,
   `overview.winner.key_tradeoff` comes from the LLM verdict; the deterministic string only
   overwrites it when `ENABLE_WINNER_PROSE_RECONCILE` is ON, and that flag is **OFF in prod**
   (CLAUDE.md:367; M22 report lists it OFF). The LIVE user-visible half is therefore the
   hard-cap partial path (`scs:3223`, unflagged) — real, but narrower than "every compare".
   The fix is also a **precondition** for flipping `ENABLE_WINNER_PROSE_RECONCILE`: flipping
   it today would ship a blank `key_tradeoff` on every brand-repeating pair.
6. **Persisted history rows keep the old spelling.** `response_builder.py:1820` persists
   `dimension_winners` into `full_response`. Rows written before this merge carry the raw
   label; rows after carry the deduped one. No reader joins on it (§10.3), so the mixed
   corpus is inert — but it IS mixed, and any future analytics that groups by that value
   must handle both. This unit does not backfill.
7. **`compute_scores` still raises `AttributeError` on a non-str `brand`/`name`** (§3.2).
   Pre-existing at `:914`; pinned, not fixed, by test 11.

---

## 9. Spec disagreements with the review

1. **The second-vote says this needs a flag; I am specifying it unflagged, and I want the
   ruling in writing.** Verbatim from the verifier ledger
   (`docs/investigations/2026-09-06-full-review-verified.json`, `verdict_trail[1]`):
   *"Fix (a) as written would leave price_tiers_map raw, creating a new key mismatch; it
   also alters persisted output and needs a flag."* My position, with the measurements:
   * "leaves `price_tiers_map` raw" — **true, and deliberate** (§3.3). But no consumer joins
     `price_tiers` keys against `dimension_winners` values, so leaving it raw creates no NEW
     mismatch; it leaves an OLD, separate one (`build_scores_summary:2861`) exactly where it
     is. Deduping it in this hunk would break `response_builder:1726/:1865` and flip
     `value_badge` on the default flag state — measured.
   * "alters persisted output" — **true** (§8 limit 6), and inert: zero readers (§10.3).
   * "needs a flag" — I disagree on the grounds in §2.2 (regression fix, one-directional,
     no-op on non-repeating input, direct precedent in `7fb0b0d4` itself), and I have
     written §2.2's fallback so the flagged variant is a 6-line delta if Fable rules the
     other way. **RULING REQUESTED.**
2. **Split ruling: is `price_tiers` in or out of W4-10?** The wave-plan row says "Route
   `:1554` through `text_sanitize.dedup_brand_name`" — `:1554` only, which is what I
   specified. The brief's framing ("the fix makes ONE spelling flow everywhere") argues for
   both. I recommend **OUT**, as `CR-DELTA-CORRECTNESS-07a2` with its own flag, on the §3.3
   evidence. **RULING REQUESTED.**
3. **Anchor drift: none on the primary anchor, contrary to the brief's warning.**
   `scoring_service.py:1554-1557` at `76ace90` is *the same four lines* at `b63a8368`
   (verified with `git show 76ace90:app/services/scoring_service.py | sed -n '1548,1562p'`
   against `sed -n '1538,1562p'` at HEAD — both put `product_names = [` on 1554). The tables
   row's bare `scoring_service.py:1554` is likewise current. Anchors that DID need
   resolving by symbol, because the review does not give them:
   `compute_dimension_winners :2430`, `compute_tradeoff_pairs :2547` (join at `:2583/:2585`),
   `_product_name_for_evidence :907-915`, `build_winner_evidence :926`,
   `_display_product_names scs:1149`, the three call sites `scs:3199 / :3790 / :4532`,
   `deterministic_verdict_fields rb:130`, `apply_value_badges :2496`,
   `build_scores_summary :2861`, `home_routes._select_smart_pick :414`.
4. **The review's `eb331cb` is the MERGE; the change is `7fb0b0d4`.** Both are stated in
   §1.2 so the blame trail is reproducible either way. Not a contradiction — a precision.
5. **The impact field understates it in one direction and overstates in another.**
   `"None user-visible today … (a) becomes user-visible the moment anything renders
   dimension_winners"` is stale — the verify stage already corrected it (`tradeoffs`
   collapse), and I measured the rest of the chain to a rendered component:
   `key_tradeoff` → `ResultsContent.tsx:169` → `RunnerUpWinsCard`. But `dimension_winners`
   ITSELF is indeed rendered by nothing (§10.4), so the sentence is right about that key and
   wrong about the finding.
6. **Limbs (b)-(g) of `CR-DELTA-CORRECTNESS-07` are NOT in W4-10.** The wave plan scopes
   W4-10 to limb (a). (b) `consumed_keys` threading, (c) `_strip_inference_markers`,
   (d) `CATEGORY_MIN_COVERAGE`, (e) unconvertible `target` guard, (f) `1 - winner_index`,
   (g) `home_routes:163` — untouched, unmeasured here, and none of them shares a line with
   this hunk. Recorded so the reviewer does not expect them in the diff.
7. **Product decisions I am NOT making:** whether `key_tradeoff` should be non-empty at all
   on the hard-cap path; whether `build_scores_summary` should say `unknown` or omit the
   tier; whether `ENABLE_WINNER_PROSE_RECONCILE` / `ENABLE_CATEGORY_VALUE_BADGE` flip after
   this merge; whether the mixed persisted corpus needs a backfill; whether
   `dedup_brand_name` should coerce non-str inputs.

---

## 10. Blast radius

### 10.1 Callers of the changed surface

`compute_scores` — **2 production call sites**, both in
`app/services/structured_comparison_service.py`: `:3686` (sync `compare`) and `:4418`
(SSE streaming). `grep -rn "compute_scores" app/ scripts/ --include=*.py` returns those two
plus the definition; `scripts/` has none.

`dimension_winners` as a *value* — 5 production reads
(`grep -rn "dimension_winners" app/ scripts/ --include=*.py`, definition lines excluded):

| reader | what it does with the winner LABEL | affected? |
|---|---|---|
| `scs:3199-3206` (WS1 partial) → `compute_tradeoff_pairs` | string-equality join | **YES — this is the fix** |
| `scs:3790-3791` (sync) → `compute_tradeoff_pairs` | string-equality join | **YES — this is the fix** |
| `scs:4532` (SSE) → `compute_tradeoff_pairs` | string-equality join | **YES — this is the fix** |
| `scs:4433` — the SSE `scores` event payload | passes the dict through to the client verbatim | value spelling changes on the wire; no client reader (§10.4) |
| `response_builder.py:1820` — the persisted `scoring` block | stores it | spelling changes in new rows (§8 limit 6) |
| `scoring_service.py:2897` (`build_scores_summary`) | prints `f"{display}={winner}"` into the GPT verdict prompt | **YES, and it is a repair**: the prompt line goes from `Dimension leaders: presentation=TOM FORD TOM FORD OUD WOOD` to `…=TOM FORD OUD WOOD`, matching the `Score winner:` line two lines above it (`:2895`), which already uses the deduped name |
| `app/api/home_routes.py:455-464` | see §10.3 | **NO — branch already dead** |

`price_tiers` — **6 production reads**: 4 in `response_builder.py` (`:1726` `_compute_value_match`,
`:1865` `_compute_budget_mismatch`, `:1821` the persisted `scoring` block, `:1993` `tier_context`)
and 2 in `scoring_service.py` (`:2514` `apply_value_badges` legacy branch, `:2861`
`build_scores_summary`). **None affected by this unit**: the keys do not change. §3.3 measures
what would happen to the first three if they did.

### 10.2 Test-side reach

78 test files match the comm grep (gate 2); 15 name `dimension_winners`, 4 name
`compute_tradeoff_pairs`, 33 name `compute_scores`, 1 names `_display_product_names`. The
18 most-relevant suites were run at HEAD: **541 passed** (§4). None asserts a
`compute_scores`-produced winner label from a brand-repeating pair.

### 10.3 `home_routes._select_smart_pick` — no effect, and the reason matters

`app/api/home_routes.py:453-464`:

```
:455    dim_winners = scoring.get("dimension_winners") or {}
:456    winner_name = f"{winner.get('brand', '')} {winner.get('name', '')}".strip()   # RAW
:459    for dim_key, winner_label in dim_winners.items():
:460-462    if (winner_label == winner_name and user_top_priority in dim_key.lower()):
```

This is the one place in `app/` that compares a persisted `dimension_winners` entry against a
locally-rebuilt RAW name, so it LOOKS like collateral damage. It is not: `dim_winners.items()`
yields `(dim, {"winner": ..., "margin": ...})`, so `winner_label` is a **dict**, and
`dict == str` is always `False`. `priority_match` is therefore already unreachable at HEAD,
independent of spelling, and the branch always falls through to
`"home.smart_pick.reason.recent_winner"`. **This unit must NOT fix it** (§2.3 item 9): it is
a separate latent defect on the M20/M21 delta, it needs a product ruling about mixed old/new
persisted rows, and repairing the `.items()` bug in the same PR would silently activate a
user-facing i18n branch. Recorded as its own follow-up row.

### 10.4 Client impact — NONE, measured, and the phones still run the pre-OTA client

`SmartCompareApp` read only, never written. Full scan
(`grep -rn "dimension_winners|price_tiers|\.tradeoffs" SmartCompareApp --include=*.ts --include=*.tsx`,
`node_modules` excluded) returns **5 lines, all in `src/types/types.ts`**:
`:253` `dimension_winners: Record<string, DimensionWinner>`, `:254` `price_tiers:
Record<string, string>`, `:355` a comment, `:370-371` the optional mirrors. **Zero component
reads either key**, and `OverviewSection.tradeoffs` (`types.ts:209`) likewise has zero
component readers. So:

* `dimension_winners` winner labels: a TYPE-only field. Its `Record<string, …>` shape is
  unchanged (same keys — dimension names; only a VALUE string changes). No client match
  breaks.
* `price_tiers`: untouched by this unit anyway.
* `tradeoffs`: goes from `[]` to a 1-element array on brand-repeating pairs. `TradeoffPair`
  (`types.ts:194-197`) is already the shape the backend emits for non-repeating pairs today,
  so the current client parses it fine — it just does not render it.
* The ONE surface the current client DOES render is `overview.winner.key_tradeoff`
  (`ResultsContent.tsx:169` → `:404` → `RunnerUpWinsCard.tsx:39-40`). It is typed
  `key_tradeoff?: string` (`types.ts:406`) / `key_tradeoff: string` (`types.ts:170`) and
  `RunnerUpWinsCard:88-95` already handles empty/absent by self-hiding. Going from `""` to
  real prose makes a previously self-hidden card render its caption — **strictly the
  intended UX**, no new type, no new key, no removed key.
* `DimensionBars.tsx` (named in the brief) joins on `dimension.winner` — an **index**
  (`0 | 1`) from `scoring_v2.dimensions[]` (`DimensionBars.tsx:263-268`), not on any product
  name. Zero exposure.

**Conclusion: the backend change is safe for the CURRENT pre-OTA client. No `eas update` is
required by this unit, and none should be claimed in the PR.**

---

# FABLE REVIEW RULINGS (binding, 2026-09-23) — W4-10 tradeoffs / dimension_winners dedup parity

Reviewer verdict SOUND_WITH_CHANGES (Opus 5.5 adversarial spec review, read-only, at `b63a8368`). The RED reproduces under every flag state; provenance `7fb0b0d4` (PR #129 merge `eb331cb7`) confirmed; `home_routes` `priority_match` confirmed dead (dict vs str). Everything below overrides the spec body where they conflict.

## R1 — UNFLAGGED stands, with full disclosure
The strongest case for a flag is real and was under-disclosed: on EVERY brand-repeating compare (sync and SSE, not only the hard-cap path) the live gpt-4o verdict system prompt's `Dimension leaders:` line changes, and the same prompt feeds self-critique regen and `pain_workflow_context`; the LLM's `winner_reason` / `key_tradeoff` can shift and this is unmeasurable offline. It still loses: `7fb0b0d4` changed the same prompt's product-name lines unflagged and this change only makes the leaders line agree with the `Score winner:` line already in that prompt; no persisted-row reader joins on the label; no client component reads `dimension_winners` / `price_tiers` / `tradeoffs` at 97b5f15 or HEAD; the 78-file comm set is unchanged under the simulated fix. **The PR body lists the main-path prompt change as the unit's live effect, first.**

## R2 — `scripts/shadow_experiments.py:762-763` is IN SCOPE
The spec's "scripts/ has no caller" is false. Route the offline prompt's names through `_display_product_names` (or the identical dedup) so the shadow prompt spells each product one way and matches what production sends. Pin it. State in the PR body that shadow A/B baselines captured before the fix are not comparable for brand-repeating pairs.

## R3 — `price tier: unknown` is the SAME regression and is folded in; the `price_tiers` KEYS stay raw
`build_scores_summary:~2861` reads `scoring_result["price_tiers_by_index"][f"product_{i}"]` (the M20 #102 index mirror, present in every result) — one line, no key change, no `response_builder` move, no badge ruling. Pin: a brand-repeating pair's summary shows the tier, not `unknown`; the control pair unchanged. Follow-up 07a2 is CLOSED by this unit. The spec's reason for leaving the keys out (the TOM FORD `value_badge` flip) is false for its own example (fair_price both ways, measured); the keys stay out because nothing on the phones reads them and the fix does not need them — say that, not the badge story.

## R4 — crash surface: coerce, and correct the claim
`dedup_brand_name` on a non-str brand raises `AttributeError` inside `compute_scores` for direct callers (shadow scripts over DB rows); the orchestrator raises earlier regardless. Coerce with `str(x or "")` in the new expression at `:~1554`, correct §3.2 ("no new crash surface" is wrong for direct callers), and rewrite pin 11 to the degenerate pair (`brand=123` both products, identical names ⇒ empty `winner_evidence`) asserting OK — that pin then detects removal of the coercion (the spec's pin 11 could not: it raises at `:914/:966` before `:1554`).

## R5 — pin 12 rewritten
Drop the one-product half (`compute_scores([p])` returns early without `price_tiers` and never reaches `:1554` — measured). The three-product half uses brand-repeating names and asserts the CORRECT post-fix labels (deduped), since the correct fix changes them.

## R6 — mutation table corrections
The `casefold in` row is inverted as written (the raw label is the LONGER string): the expression that turns 1/4/5 green is `display in label`. Record the measured counts for the flipped expression. Pins 7 (all parametrisations except `dimension_winners`), 9 (duplicate of 8) and 10 are Preserve decoration — keep, label them; the Applesauce argument-swap row is the load-bearing one.

## R7 — `home_routes` `priority_match` is NOT repaired here; two follow-ups are recorded
(a) When it is repaired, compare against `dedup_brand_name(winner_name)` and remember pre-merge rows carry raw labels (mixed corpus, measured OLD True / NEW False). (b) `tests/test_home_routes.py:311` and `:400-428` pin a STR-valued `dimension_winners` production never writes — test debt, separate row.

## R8 — client anchors and merge order
Cite the 97b5f15 anchors in the PR body: no reader for `dimension_winners` / `price_tiers` / `tradeoffs` (only `types.ts`); `key_tradeoff` rendered via `ResultsContent.tsx:155 → :388 → RunnerUpWinsCard:88-95`, self-hiding when empty; the new prose does not match `SCORE_INTERNALS_RE`. Merge after W4-1 (scs anchors after `:1214` shift +5; no textual conflict).
