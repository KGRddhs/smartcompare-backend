# W4-3 — score the price you are willing to show: a PRE-SCORING showable pass

Finding `PO-RECORDED-MEASURED-04` (review unit "U7"). Backend only, no client change.
Flag `ENABLE_PRESCORING_SHOWABLE_GUARD` (default OFF, read PER CALL). Worktree
`sc-w4-3`, branch `feature/s65-w4-3-prescoring-showable-guard`, base commit
`b63a8368` (= `origin/main`, "Merge pull request #159").

Every line anchor below was verified at `b63a8368` in THIS worktree. The review's
anchors are from `76ace90` and have drifted — per-anchor table in "Spec disagreements".
Every "today's behaviour" claim was produced by a probe run offline
(`PYTHONIOENCODING=utf-8`, `load_dotenv` + `neutralize_credentials` +
`install_dotenv_guard` exactly as `tests/conftest.py:16-29` does, zero network,
no `LIVE`). Probe scripts live in the agent scratchpad
(`w43_probe2.py` … `w43_probe5.py`), never in the worktree.

---

## 1. The defect, measured

### 1.1 The three passes, at HEAD, in execution order

| # | where | anchor at HEAD | what it does |
|---|---|---|---|
| 1 | orchestrator sync | `structured_comparison_service.py:3641` | `reconcile_pair_fairness(product_data, …)` — may re-select / pend |
| 2 | orchestrator sync | `:3658` | `apply_region_currency_guard(product_data, region)` — the #113 PRE-SCORING pass, flag `ENABLE_REGION_CURRENCY_GUARD` |
| 3 | orchestrator sync | `:3686` | `scoring_service.compute_scores(product_data, …)` — **reads `product["price"]["amount"]` raw** |
| 1′ | orchestrator stream | `:4275` | `reconcile_pair_fairness` |
| 2′ | orchestrator stream | `:4293` | `apply_region_currency_guard` |
| — | orchestrator stream | `:4340` | the SSE `prices` projection calls `is_price_showable(_name, _price, …, enforce_correctness=True)` **on a COPY of the payload only** (`prices_payload[key]`), deliberately NOT mutating `product_data` (comment at `:4322-4328`) |
| — | orchestrator stream | `:4356` | `yield ("prices", prices_payload)` |
| 3′ | orchestrator stream | `:4418` | `compute_scores(product_data, …)` — still the raw amount |
| 4 | response chokepoint | `response_builder.py:1522` | `if not is_price_showable(_name, _price, _cat, enforce_correctness=True):` → `make_pending_price(...)`, runs inside `build_comparison_response` — i.e. AFTER `compute_scores` and AFTER the LLM verdict |

`compute_scores` consumes the raw amount at `scoring_service.py:1646-1655`:

```
:1646        if price_data and isinstance(price_data, dict) and price_data.get("amount"):
:1649            scores["price_raw"] = float(price_data["amount"])
:1654        else:
:1655            scores["_price_missing"] = True
```

`_price_missing` then drives `_compute_value_score` (`:1178-1207`) and the
`_signal_missing_for` → `missing_data` / `dimension_winners` path (`:2220-2232`).

So the correctness gate — the one that decides what the user is ALLOWED to see —
has never been consulted before the winner is picked. `#113` fixed exactly this
shape for the currency half (`price_service.py:3088`, `apply_region_currency_guard`,
docstring `:3093-3120`: *"it runs AFTER compute_scores has already picked a winner
from the raw amount"*). The correctness half never got the same pass.

### 1.2 RED reproduction — both products behind a non-PDP url

Probe `w43_probe4.py`. Two electronics products with numerically scored specs, both
prices `local_bhd`, both `url = https://www.google.com/search?ibp=oshop&…`
(`_is_listing_url` → `True`, measured). Region `bahrain`, category `electronics`,
all flags at their shipped defaults (`ENABLE_EXACT_PRICE_GATE` unset ⇒
`exact_gate_enabled() == True`; `ENABLE_REGION_CURRENCY_GUARD`,
`ENABLE_BUNDLE_C_SCORING`, `ENABLE_MISSING_DIM_OMISSION` all unset).

```
is_price_showable(product_0) = False  guard_rejected='non_pdp_url'
is_price_showable(product_1) = False  guard_rejected='non_pdp_url'

-- HEAD today: compute_scores over the RAW product_data --
scores.product_0.breakdown = {"performance_score": 85.0, "value_score": 89.5,
  "build_quality_score": 50, "feature_score": 87.0, "ecosystem_score": 50,
  "futureproof_score": 90.0}
scores.product_0.missing_data = ["build_quality_score", "ecosystem_score"]
scores.product_1.breakdown.value_score = 40.5
dimension_winners.value_score = {"winner": "Sony Sony WH-1000XM5", "margin": 49.0}
winner_index = 0   win_margin = 24.6

-- the same product_data pended BEFORE compute_scores (what this unit does) --
scores.product_0.breakdown.value_score = 85.0
scores.product_0.missing_data = ["value_score", "build_quality_score", "ecosystem_score"]
scores.product_1.breakdown.value_score = 45.0
dimension_winners.value_score = {"winner": "N/A", "margin": null}
winner_index = 0   win_margin = 22.8
```

End to end through `build_comparison_response` (same probe), HEAD:

```
overview.winner.margin            = 24.6
scoring.scores.product_0.breakdown.value_score = 89.5
scoring.dimension_winners.value_score = {"winner": "Sony Sony WH-1000XM5", "margin": 49.0}
overview.products[0].price        = {"amount": null, "currency": "BHD",
                                     "unavailable": true, "reason": "pending_genuine"}
metadata.guard_rejected           = [{"product_index": 0, "reason": "non_pdp_url"},
                                     {"product_index": 1, "reason": "non_pdp_url"}]
```

**A 24.6-point win and a 49.0-point value-dimension margin, asserted on top of two
prices the same payload ships as `unavailable: true`.** That is the finding,
reproduced at HEAD.

### 1.3 The review's literal numbers — reproduced on the review's own shape

Probe `w43_probe5.py` case 4. The same pair but with specs that carry NO numerically
scored field (`_score_specs` → `None`, so `_spec_missing` is also set):

```
raw   : value_score p0=100.0  p1=30.0  win_margin=14.0
guard : value_score p0=50     p1=50    win_margin=0.0
missing_data (BOTH states) = ['performance_score','value_score','build_quality_score','ecosystem_score']
```

`100.0` from the raw price → `50` = `MISSING_SCORE` (`scoring_service.py:297`).
The review's "RED: 100.0 from the raw price" is exact. **But `MISSING_SCORE` is
reached only when the SPEC signal is missing too** — `_compute_value_score`
(`:1178-1207`) returns `MISSING_SCORE` only at `if spec_gone and price_gone`
(`:1202-1203`); with a real spec signal it returns `spec_score` (`:1207`), which is
why §1.2 shows `85.0`, not `50`. See "Spec disagreements" #2.

### 1.4 The verifier caveat, confirmed

`value_score` is in `missing_data` **at HEAD, before any fix**, in §1.3 (both
states) — driven by `_spec_missing`, not by the price. An assertion on
`missing_data` for the electronics shape pins NOTHING. The wave plan's
`tests_first` column already says so ("VERIFIER CAVEAT, LOAD-BEARING"); measurement
confirms it. There IS a shape where the `missing_data` assertion is genuinely RED —
**fragrance**, where the value dim is `wear_value_score` and the spec signal is
present (probe `w43_probe5.py` case 5):

```
FRAG raw  : wear_value_score=76.0  missing_data=['versatility_score','presentation_score']
            dimension_winners.wear_value_score={"winner":"Dior Dior Sauvage EDP 100ml","margin":22.0}
            win_margin=2.8
FRAG guard: wear_value_score=65.7  missing_data=['versatility_score','wear_value_score','presentation_score']
            dimension_winners.wear_value_score={"winner":"N/A","margin":null}
            win_margin=0.6
```

### 1.5 The winner actually flips — one-sided case

Probe `w43_probe2.py`, product_0 behind a google search link, product_1 on a real
PDP (`https://bolo.bh/products/bose-qc-ultra`, `is_price_showable → True`,
`guard_rejected None`), specs with no numeric field:

```
RAW  : winner_index=0  win_margin=14.8  v0=100.0 v1=30.0
       winner_evidence=["Sony WH-1000XM5 leads on the overall picture"]
PEND : winner_index=1  win_margin=8.2   v0=50    v1=75.0
       winner_evidence=["Bose QuietComfort Ultra has a confirmed Bahrain price
                         while the other relies on an indicative figure"]
```

The guard does not merely blank a number — it changes who wins, and the deterministic
evidence line becomes the honest one. "Expect winner flips; that is the point"
(wave plan, `order_reason`).

### 1.6 The measurement regression the naive fix causes

Probe `w43_probe4.py`, E2E 2 and E2E 3:

```
HEAD                      metadata.guard_rejected = [{0,"non_pdp_url"},{1,"non_pdp_url"}]
guard, no harvest code    metadata.guard_rejected = []
guard + product-level stash, still no harvest code
                          metadata.guard_rejected = []
```

The chokepoint's `if _price.get("unavailable") is True: continue` (`response_builder.py:1498`)
returns BEFORE the `guard_rejected` append at `:1533-1537`, so a pre-scoring pend
makes the canary read clean. `#113` hit exactly this and solved it with a
PRODUCT-level `_region_guard_rejected` stash harvested at `:1487-1493` **before**
the early-continue. W4-3 must copy that, or the flag's canary is blind — which is
the failure mode CLAUDE.md:362 already warns about for the region guard.

### 1.7 The reasons the guard can stash (measured, `w43_probe5.py` case 6)

| price shape | `is_price_showable` | stamped `guard_rejected` |
|---|---|---|
| google search url | False | `non_pdp_url` |
| `in_stock: False` on a PDP | False | `out_of_stock` |
| no url AND no title/name | False | `no_identity` |
| `"Dior Sauvage EDT"` vs title `"Dior Sauvage Parfum"` | False | `not_exact` |
| `"iPhone 15"` vs title `"iPhone 15 Pro"` | False | `not_exact` |
| `source_method: "estimated"` on a PDP | False | **`None`** — the method check (`:1811-1812`) returns before any stamp |
| `"Sony WH-1000XM5"` vs title `"Sony WH-1000XM4"` | **True** | None (the backstop accepts it — pre-existing, not this unit) |

So the stash value can legitimately be `None`. The harvest must fall back to a
named reason rather than dropping the row.

---

## 2. The design — one pure pass, flagged OFF, mirroring `#113` exactly

### 2.1 Flag reader — `app/services/price_service.py`, immediately after `region_currency_guard_enabled` (`:806-824`)

Copy that helper's idiom verbatim (per-call `os.getenv`, `""` default, truthy set):

```python
def prescoring_showable_guard_enabled() -> bool:
    """..."""
    return os.getenv("ENABLE_PRESCORING_SHOWABLE_GUARD", "").strip().lower() in (
        "true", "1", "yes", "on",
    )
```

Never read at import; never cached in a module constant.

### 2.2 The pass — `app/services/price_service.py`, immediately after `apply_region_currency_guard` (def `:3088`, body ends `:3145` `return changed`)

```python
def apply_prescoring_showable_guard(product_data: List[Dict[str, Any]]) -> bool:
    # ... docstring ...
    if not prescoring_showable_guard_enabled():
        return False
    changed = False
    for pd in product_data:
        _price = pd.get("price")
        if not isinstance(_price, dict):            # chokepoint's SIB-5 branch owns it
            continue
        if _price.get("unavailable") is True:       # keep size_mismatch / unit_mismatch
            continue
        _name = pd.get("full_name") or pd.get("name") or ""
        _cat = pd.get("category") or _infer_category_from_query(_name)
        if is_price_showable(_name, _price, _cat, enforce_correctness=True):
            continue
        pd["price"] = make_pending_price(
            currency=_price.get("currency") or "BHD",
            reason="pending_genuine", size=_price.get("size"),
        )
        pd["best_price"] = None
        if "retailer" in pd:
            pd["retailer"] = None
        pd["_prescoring_showable_rejected"] = _price.get("guard_rejected") or "not_showable"
        changed = True
    return changed
```

Every line of the loop is the chokepoint's own (`response_builder.py:1496-1542`)
with `make_pending_price`'s three kwargs identical, plus `#113`'s product-level
stash. `is_price_showable` is called on the REAL dict (as the chokepoint does), so
`guard_rejected` is stamped there and read back one line later; the dict is then
discarded with the replaced price, which is precisely why the stash exists.

**No `region` parameter, no category argument**: the category is derived exactly
as the chokepoint and the stream projection derive it
(`pd.get("category") or _infer_category_from_query(_name)` —
`response_builder.py:1462`, `structured_comparison_service.py:4340`). Do not
invent a third derivation.

### 2.3 Two call sites, in lockstep

* **sync**: `structured_comparison_service.py`, immediately after the
  `apply_region_currency_guard` try/except at `:3655-3661`, in its own
  `try/except Exception` with `logger.warning("pre-scoring showable guard skipped (sync): %s", _e)`
  — byte-for-byte the neighbouring idiom.
* **stream**: same, immediately after `:4290-4296`.

Order is load-bearing and must be stated in the code comment: AFTER
`reconcile_pair_fairness` (which can re-select a candidate with a different url)
and AFTER `apply_region_currency_guard` (an already-region-pended price then hits
this pass's `unavailable is True` early-continue and cannot double-pend), and
BEFORE the `specs`/`prices` yields and `compute_scores`.

Add `apply_prescoring_showable_guard` to the existing `from app.services.price_service import (…)`
block at `structured_comparison_service.py:1206-1226` (next to `apply_region_currency_guard`
at `:1219`).

### 2.4 The harvest — `app/services/response_builder.py`

Extend the import at `:1448-1452` with `prescoring_showable_guard_enabled`, read it
once next to `_region_guard_on` (`:1456`), and add a SECOND harvest block
immediately after the `#113` one (`:1487-1493`), before the `unavailable`
early-continue at `:1498`:

```python
if _prescoring_guard_on:
    _psr = pd_item.get("_prescoring_showable_rejected")
    if _psr:
        _entry = {"product_index": _pd_idx, "reason": _psr}
        if _entry not in _guard_rejected_diag:
            _guard_rejected_diag.append(_entry)
```

The `if _entry not in …` de-dup is `#113`'s (`:1491-1493`) and is required: a
direct `build_comparison_response` caller (share / history rebuild) can be handed
product_data that already carries the stash.

### 2.5 Byte-identical flag-OFF

`apply_prescoring_showable_guard` returns at its first line with the flag OFF; both
call sites then execute their HEAD bodies exactly. The harvest block is inside
`if _prescoring_guard_on:`. No existing line changes behaviour — only three
insertions (two calls, one harvest block) plus two new functions and two import
names.

### 2.6 What must NOT change — the must-NOT-touch list

`is_price_showable` (`price_service.py:1781`) and every guard inside it —
`_showable_source_methods` (`:1743`), `_is_listing_url` (`:8238`),
`backstop_identity_verdict`, the sample/decant guard (`:1842`), the low-fragrance
floor (`:1833`), `exact_gate_enabled` (`:4217`); `make_pending_price`;
`public_price_view` (`:9118`); `apply_region_currency_guard` (`:3088`) and
`region_currency_guard_enabled` (`:806`); `reconcile_pair_fairness`;
`scoring_service.py` in its entirety (`_compute_raw_scores` `:1637`,
`_compute_value_score` `:1178`, `_normalize_scores`, `compute_dimension_winners`
`:2429`, `MISSING_SCORE` `:297`, `build_scores_summary`); the chokepoint's own
`is_price_showable` call at `response_builder.py:1522` and its `_guard_rejected_diag`
appends at `:1510`/`:1535` (the backstop STAYS — direct `build_comparison_response`
callers at `structured_comparison_service.py:3229` (hard-cap partial), `:3825`
(sync) and `:4598` (stream complete) still need it); the SSE `prices` projection at
`:4331-4356`; `_showable_source_methods`'s membership (so W4-1's `converted_usd`
rows stay showable); the `price` dict's public key set; the `pending_genuine`
reason string; `scoring_v2` (`response_builder.py:1097/:1827`).

**No new `source_method`. No new price key. No new response key.** The only new
key anywhere is the PRODUCT-level `_prescoring_showable_rejected`, which
`public_price_view` never sees (it is not on the price) and which both product
projections drop because they build explicit key sets — the same argument `#113`
records at `price_service.py:3112-3117`.

### 2.7 Composition with W4-1 and W4-2 — "showable" after W4-1

Measured at HEAD (`w43_probe3.py` §3), `_showable_source_methods()` is the 16-member
set `{converted_usd, firecrawl, firecrawl_brand_domain, local_bhd,
magento_graphql_bhd, occ_rest_bhd, official_brand, page_scrape, page_scrape_jsonld,
page_scrape_rendered, rest_json_bhd, salla_api, scrapedo_rendered, shopify_json,
woo_store_api, zyte_render_bhd}`:

```
method=converted_usd       PDP url  -> showable=True   guard_rejected=None
method=local_bhd           PDP url  -> showable=True   guard_rejected=None
method=page_scrape_jsonld  PDP url  -> showable=True   guard_rejected=None
method=estimated           PDP url  -> showable=False  guard_rejected=None
method=gpt_organic_extract PDP url  -> showable=False  guard_rejected=None
method=converted_usd       GOOG url -> showable=False  guard_rejected='non_pdp_url'
method=local_bhd           GOOG url -> showable=False  guard_rejected='non_pdp_url'
```

I read `sc-w4-1`'s uncommitted diff (`git -C ../sc-w4-1 diff`, 338 insertions
across `price_service.py` + `structured_comparison_service.py`; read-only, never
written to). **W4-1 touches neither `is_price_showable` nor
`_showable_source_methods`.** What it does is relabel a shopping-rung
`local_bhd` row to `converted_usd` when the link carries no Bahrain host evidence
(`source_method = "converted_usd"` at its step-3 hunk). `converted_usd` is a
member of the showable set at HEAD and stays one.

**Therefore, precisely:** after W4-1, a shopping row that was `local_bhd` and
becomes `converted_usd` is *still showable* on the source-method axis, and this
guard will NOT blank it for the relabel. It is blanked only if it independently
fails a correctness guard — in the wave's own headline case, `non_pdp_url`,
because W4-1 leaves the google search link in `price["url"]` (W4-1 red test 12
pins that its relabel un-pends nothing). W4-3 must NOT add any source-method test
of its own; delegating the whole predicate to
`is_price_showable(..., enforce_correctness=True)` is what makes this
automatically true. Red test 6 pins it.

**W4-2** (`ENABLE_SHOPPING_DISCOVERY_URL_SPLIT`, no spec on disk in `sc-w4-2` at the
time of writing — the directory is empty and the worktree is clean) moves the
search link out of `price["url"]` into `discovery_url`, which makes those rows pass
`_is_listing_url`. When W4-2's flag is ON, this guard stops blanking them — correct
and intended: they are then genuinely showable. The two flags are INDEPENDENT (no
shared code path); the wave plan's hard order is W4-1 ≤ W4-2, and W4-3's own
activation constraint is only "after W4-1/W4-2 land, so the two guards move the
pend set once" (`order_reason`).

### 2.8 Why this design beats the alternatives

* **Put the helper in `structured_comparison_service.py` instead** (avoids touching
  `price_service.py` and so avoids the byte-identity gate). Rejected: the mirror
  (`apply_region_currency_guard`) lives in `price_service.py` and is imported by the
  orchestrator at `:1219`; splitting the pair across modules is exactly the drift
  `#113`'s docstring (`:3107-3110`, "Mirrors the chokepoint's condition exactly so
  the two cannot drift") was written to prevent. The gate is cheap and its
  discrimination is stated honestly in Gate 3.
* **Move the chokepoint check earlier and delete it from `response_builder`.**
  Rejected: three direct `build_comparison_response` callers (`:3229` partial,
  `:3825`, `:4598`) plus share/history rebuilds and tests bypass the orchestrator
  entirely. `#113` kept the chokepoint as the idempotent backstop for the same
  reason; an already-pended price hits its `unavailable` early-continue.
* **Blank `price_raw` inside `compute_scores` instead of pending the price.**
  Rejected: `compute_scores` has no access to the category/url/identity the
  predicate needs, it would duplicate the predicate in a third place, and it would
  leave the SSE `prices` event and the LLM verdict input still reading the raw
  amount.
* **Null only `amount` and keep the rest of the price dict.** Rejected: the shipped
  vocabulary for "not showable" is `make_pending_price`, and the FE renders
  `unavailable: true` (`ResultsContent.tsx:128` per `response_builder.py:1467`).
  A half-pended price is a new shape.
* **Stash the reason on the PRICE rather than the product.** Rejected for `#113`'s
  measured reason (`price_service.py:3112-3117`): `public_price_view` strips
  `_`-prefixed keys from a price only when `ENABLE_EXACT_PRICE_GATE` is ON, so a
  price-level key leaks into the public surface with that gate off.

---

## 3. Preserve — existing tests on the touched paths, run at HEAD

| file | why it pins this unit | result at HEAD |
|---|---|---|
| `tests/test_m18_region_guard_prescoring.py` | the mirror: both orchestrator call sites, the SSE `prices` event, the `compute_scores` hand-off, the `metadata.guard_rejected` harvest | **14 passed** |
| `tests/test_m13_region_currency_guard.py` | the chokepoint half of `#113` | **4 passed** |
| `tests/test_price_showable.py` | the predicate itself — must be untouched | **19 passed** |
| `tests/test_m13_04_full_stream_deadline.py` | the `_mock_to_verdict` harness this unit's streaming tests reuse | **2 passed** |
| `tests/test_exact_gate_flag_off_parity.py`, `tests/test_kpi_metric.py`, `tests/test_correctness_runtime_leaks.py`, `tests/test_fragrance_content_quality.py` | every test file that names `guard_rejected` / `non_pdp_url` | **117 passed** (as a group) |

`grep -rln "non_pdp_url" tests --include=test_*.py` → exactly one file
(`tests/test_fragrance_content_quality.py`). `grep -rln "guard_rejected"` → 11
files. No test anywhere references `ENABLE_PRESCORING_SHOWABLE_GUARD` or
`apply_prescoring_showable_guard` (grep over `*.py/*.md/*.ts/*.tsx`, zero hits
outside the review docs).

Additionally preserved, by construction and pinned below:

* Flag OFF ⇒ `overview.winner.margin 24.6`, `value_score 89.5/40.5`,
  `dimension_winners.value_score {"winner":"Sony Sony WH-1000XM5","margin":49.0}`,
  `metadata.guard_rejected [{0,"non_pdp_url"},{1,"non_pdp_url"}]` — the §1.2 numbers.
* A SHOWABLE price is untouched in BOTH flag states (measured: `guard changed=False`,
  `product dict unchanged=True`).
* An already-pending `size_mismatch` price keeps its own reason and size
  (measured: `{"amount":null,"currency":"BHD","unavailable":true,"reason":"size_mismatch","size":"50ml"}`,
  dict unchanged).
* A non-dict price is left to the chokepoint's SIB-5 branch (measured: unchanged `None`).
* **The SSE `prices` payload is byte-identical whether the guard pends in place
  first or the projection pends its copy** — measured by running the projection
  code from `:4331-4355` verbatim in both orders (`w43_probe5.py` case 1):
  `{"best_price": null, "brand": "Sony", "currency": "BHD", "name": "WH-1000XM5",
  "price": {"amount": null, "currency": "BHD", "reason": "pending_genuine",
  "unavailable": true}, "retailer": null}` — `IDENTICAL = True`. This is why the
  guard may safely run before the `prices` yield.

---

## 4. Red tests — `tests/test_prescoring_showable_guard.py`

Shape and harness copied from `tests/test_m18_region_guard_prescoring.py` (unit
half + `_mock_to_verdict` streaming half + `_collect_until`). Toggle with
`monkeypatch.setenv/delenv`. Leave `ENABLE_EXACT_PRICE_GATE` at its default (ON) —
the whole correctness backstop is gated on it (§8.4).

Fixtures: `_goog(q)` → `https://www.google.com/search?ibp=oshop&q=…`;
`_pdp()` → `https://bolo.bh/products/…`; electronics specs WITH numeric fields
(`{"battery_life":"30 hours","ram":"8 GB","storage":"256 GB","screen_size":"6.1 inch","weight":"250 g"}`
/ the `6 GB`/`128 GB` twin) for the value-dim cases, and the spec-poor variant
(`{"battery_life","weight","warranty"}`) for the `MISSING_SCORE` case.

1. **RED — the headline, sync semantics.** Both products behind a google search
   link; call `apply_prescoring_showable_guard(pd)` with the flag ON, then
   `compute_scores(pd)`. Assert
   `scores["product_0"]["breakdown"]["value_score"] == 85.0` (was `89.5`),
   `scores["product_1"]["breakdown"]["value_score"] == 45.0` (was `40.5`),
   `dimension_winners["value_score"]["winner"] == "N/A"` and its `margin is None`,
   `win_margin == 22.8`. Also assert the helper returned `True`.
   **RED today** (the helper does not exist; with the guard removed the values are
   `89.5 / 40.5`, winner `"Sony Sony WH-1000XM5"` margin `49.0`, `win_margin 24.6`).
2. **RED — the review's literal claim.** Same pair, spec-poor variant: after the
   guard, `value_score == 50` (`MISSING_SCORE`) for BOTH products and
   `win_margin == 0.0`. RED today: `100.0 / 30.0`, `win_margin 14.0`.
   Docstring must record that `missing_data` already contains `value_score` in
   BOTH states here and is therefore NOT asserted (the wave plan's verifier caveat).
3. **RED — the `missing_data` assertion that actually pins something (fragrance).**
   Category `fragrance`, both behind google links, specs
   `{"concentration":"EDP","size":"100ml","longevity":"8h"/"7h"}`. After the guard:
   `"wear_value_score" in scores["product_0"]["missing_data"]`,
   `breakdown["wear_value_score"] == 65.7`,
   `dimension_winners["wear_value_score"] == {"winner":"N/A","margin":None}`,
   `win_margin == 0.6`. RED today: `76.0`, NOT in `missing_data`, winner
   `"Dior Dior Sauvage EDP 100ml"` margin `22.0`, `win_margin 2.8`.
4. **RED — the winner flips.** One-sided (product_0 google link, product_1 real
   PDP), spec-poor variant. After the guard `winner_index == 1` and
   `winner_evidence == ["Bose QuietComfort Ultra has a confirmed Bahrain price
   while the other relies on an indicative figure"]`. RED today: `winner_index 0`,
   evidence `["Sony WH-1000XM5 leads on the overall picture"]`.
5. **RED — `metadata.guard_rejected` survives the pre-scoring pend.** Run the guard
   with the flag ON, then `build_comparison_response(...)`, and assert
   `metadata["guard_rejected"] == [{"product_index":0,"reason":"non_pdp_url"},
   {"product_index":1,"reason":"non_pdp_url"}]`. RED today in the strongest sense:
   with the guard applied but no harvest block the list is `[]` (measured, §1.6),
   and with no guard at all the chokepoint produces it. This is the test that makes
   the harvest load-bearing.
6. **RED — the guard delegates, it does not re-implement (the W4-1 composition
   pin).** Parametrized over `source_method in {converted_usd, local_bhd,
   page_scrape_jsonld, shopify_json, official_brand}` on a REAL PDP url with an
   exact title: flag ON ⇒ the guard returns `False` and the price dict is
   `==` its pre-call deepcopy. And the same five on a google search url ⇒ the guard
   pends every one with stash `non_pdp_url`. RED today (no helper). The
   `converted_usd`/PDP row is the specific W4-1 pin: a legitimately showable
   converted price is never blanked.
7. **RED — the reason vocabulary.** Parametrized, flag ON, one product per row;
   assert `pd["_prescoring_showable_rejected"]` equals:
   `non_pdp_url` (google url); `out_of_stock` (`in_stock: False` on a PDP);
   `no_identity` (no url, no title, no name); `not_exact` (query
   `"Dior Sauvage EDT"`, title `"Dior Sauvage Parfum"`, category `fragrance`);
   **`not_showable`** (`source_method: "estimated"` on a PDP — measured
   `guard_rejected is None`, so the helper's `or "not_showable"` fallback is what
   is asserted). RED today.
8. **RED — both orchestrator call sites, streaming.** Reuse
   `test_m18_region_guard_prescoring.py`'s `_mock_to_verdict` +
   `_showable_bhd_fetch` pattern, but patch `_fetch_product_data` to return a price
   whose `url` is a google search link (everything else identical to the mirror's
   fixture, so the ONLY thing that can pend it is this guard). Flag ON:
   `scoring.compute_scores.call_args[0][0][0]["price"]["amount"] is None`.
   Flag OFF: `== 10.0`. RED today on the ON half. Parametrize `(flag_on, expected)`
   exactly as the mirror's `test_streaming_compute_scores_receives_guarded_product_data`.
9. **PIN — the SSE `prices` event is unchanged in both flag states.** Same harness,
   collect until `prices`: `payload["product_0"]["price"]["amount"] is None` and
   `["unavailable"] is True` with the flag ON **and** with it OFF (the projection
   already pends it today). Green today in both; pins that moving the pend earlier
   does not alter the streamed payload (§3, `IDENTICAL = True`).
10. **PIN — flag OFF is a no-op.** Unset and `"false"`: the helper returns `False`,
    `pd == deepcopy(pd_before)` (no `_prescoring_showable_rejected` key added), and
    the §1.2 end-to-end numbers hold (`value_score 89.5`, `win_margin 24.6`,
    `overview.winner.margin 24.6`, `metadata.guard_rejected` the two `non_pdp_url`
    rows). Green today; the rollback pin the corpus harness cannot see.
11. **PIN — a showable price is untouched with the flag ON.** Real PDP, exact
    title, `in_stock: True`: helper returns `False`, dict `==` its deepcopy,
    `best_price` and `retailer` unchanged, no stash key. Green once the helper
    exists; this is the over-rejection guard.
12. **PIN — an already-pending price keeps its own reason.** `size_mismatch` with
    `size="50ml"`, flag ON: helper returns `False`, price unchanged
    (`reason == "size_mismatch"`, `size == "50ml"`). Mirrors
    `test_m13_region_currency_guard`'s contract.
13. **PIN — a non-dict price is skipped.** `pd["price"] = None`, flag ON: returns
    `False`, `pd["price"] is None`, no crash. Mirrors
    `test_flag_on_non_dict_price_untouched`.
14. **PIN — the chokepoint backstop still fires for a DIRECT caller.** Call
    `build_comparison_response` with raw google-linked product_data and no guard
    run at all (the share / history / hard-cap-partial shape), flag ON: prices are
    still pended and `metadata.guard_rejected` still carries the two `non_pdp_url`
    rows. Green today; reddens if the implementer "moves" the chokepoint instead of
    adding a pass.
15. **PIN — the harvest de-dups.** Product_data already carrying
    `_prescoring_showable_rejected` AND an already-pending price, passed twice
    through `build_comparison_response`, flag ON ⇒ exactly one entry per
    `product_index` in `metadata.guard_rejected`.
16. **PIN — the flag reader.** unset → `False`; `"true"/"1"/"yes"/"on"` → `True`;
    `"false"/"0"/"no"/"off"/""` → `False`; `"  TRUE  "` → `True`;
    `monkeypatch.setenv` AFTER import flips the next call (per-call read).

---

## 5. Gates

1. **TDD red-first.** Write the file, run it alone
   (`python -m pytest tests/test_prescoring_showable_guard.py -q -p no:cacheprovider --timeout=180`),
   record `.qa-w4/W4-3-RED.txt` showing 1-8 red and 9-16 green (9/10/12/13/14 green;
   11/15/16 will error on the missing symbol — record them as red-by-absence and say so)
   BEFORE any edit under `app/`.
2. **Comm gate — module-reference set for THIS unit's touched modules.**
   The union of
   `grep -rlE "price_service|structured_comparison_service|response_builder|is_price_showable" tests --include=test_*.py`
   = **321 files** (measured at HEAD; per-module: `price_service` 174,
   `structured_comparison_service` 152, `response_builder` 56, `is_price_showable` 31;
   613 test files exist in total). Record the set in `.qa-w4/comm-set-W4-3.txt`.
   Base run BEFORE the edit (this worktree IS `b63a8368`), head run after green WITH
   `tests/test_prescoring_showable_guard.py` appended. Same invocation shape both
   times: `-m "not (live_unit or live_db or integration)" --timeout=180 -q -p no:cacheprovider`
   plus `--deselect` for every id in `tests/.pre_impl_failures.txt` (**89 lines**),
   split across two or more nodes. `comm -13 <(sort comm-base) <(sort comm-head)`
   must be empty.
   **No client scanner is needed:** no client contract is touched (§10) — zero
   `guard_rejected` references anywhere in `SmartCompareApp/src` (measured), and no
   response key is added or removed.
3. **Byte-identity — REQUIRED, and honestly scoped.** This unit edits
   `app/services/price_service.py`, so the standing rule applies: base → head → base
   RE-RUN, comparing the `results` ARRAYS record-by-record (`verify_flag_byte_identity.py:276/:293`),
   **never the OVERALL SHA** (it hashes the `--flags` list, `GATE_RECIPE.md` Step 1).
   ```
   python scripts/verify_flag_byte_identity.py \
     --flags ENABLE_PRESCORING_SHOWABLE_GUARD \
     --proof-root C:/Users/SynAckITPC/Documents/AI/sc-w0-load/_proof \
     --out .qa-w4/gate_<base|head|base2>_W4-3.json > .qa-w4/gate_<…>.log 2>&1
   ```
   Re-verify the corpus manifest first
   (`sc-w0-load/.qa-w0/proof_html_manifest.sha` = `380902fba73c9169ed0becf77a45fe27b50c2caed511a364313f41270b497ba9`
   over the 593 frozen files; expected records `n=414 skipped_no_html=6
   distinct_queries=362 non_none=825 calls=1656`). The base and base2 runs come from
   a DETACHED checkout of `b63a8368` created under the agent's OWN scratchpad
   (`git worktree add --detach <scratch>/w43-base b63a8368`, removed with
   `git worktree remove` afterwards) — never `git checkout` in `sc-w4-3` or any
   other worktree. **Never run `_proof/sweep2.py`.**
   **Honest discrimination:** the harness calls `extract_price_from_html` ONLY
   (`:244/:268`); `extract_price_from_html` never calls `is_price_showable`,
   `apply_region_currency_guard` or `compute_scores`. So it CANNOT observe this
   change at all. Expect equality; report "expected equal, observed equal, harness
   blind to the pre-scoring pass". What it does prove is that the two new functions
   were inserted without moving anything on the extraction spine. The real
   flag-OFF proof is red test 10 + the 39 Preserve nodes in
   `test_m18_region_guard_prescoring.py` / `test_m13_region_currency_guard.py` /
   `test_price_showable.py` / `test_m13_04_full_stream_deadline.py`.
4. **Ruff + py_compile.**
   `python -m ruff check --select E9,F63,F7,F82 --no-cache app/services/price_service.py app/services/structured_comparison_service.py app/services/response_builder.py tests/test_prescoring_showable_guard.py`
   and `python -m py_compile` on all four.
5. **Full free-tier suite before merge**, same marker/deselect shape as gate 2;
   failing only on ids already in `tests/.pre_impl_failures.txt` / the recorded
   comm base.
6. **Fable review before commit. Agents never commit.** The CLAUDE.md flag row is a
   merge-time item (model it on the `ENABLE_REGION_CURRENCY_GUARD` row at
   `CLAUDE.md:354` and the Wave-2 activation coupling note at `:362`).

---

## 6. Mutation checks — REQUIRED

Record each in `.qa-w4/W4-3-MUTATIONS.txt`; snapshot the file bytes before each and
sha-verify the restore (never `git checkout` a file carrying agent work).

| mutation | tests that MUST redden |
|---|---|
| delete the sync call site (`scs` after `:3661`) only | 1, 2, 3, 4, 5, 7 (unit half) stay green; the sync-path assertions of 8 and the E2E halves of 4/5 redden — the asymmetry proves the site is load-bearing |
| delete the STREAM call site (`scs` after `:4296`) only | 8 (flag-ON half) reddens; 1-7 stay green |
| delete the harvest block in `response_builder` | 5 reddens (list is `[]`); 15 reddens |
| drop the `or "not_showable"` fallback in the stash | 7's `estimated` row reddens (stash becomes `None`, so no entry is harvested) |
| drop the `if _price.get("unavailable") is True: continue` early-continue | 12 reddens (`size_mismatch` → `pending_genuine`, `size` lost) |
| drop the `if not isinstance(_price, dict): continue` guard | 13 reddens (TypeError / coerced price) |
| pass `enforce_correctness=False` to `is_price_showable` | 1, 2, 3, 4, 5, 6(google half), 7, 8 redden (measured: the same google row is `True` with `enforce_correctness=False`) |
| replace the predicate with a `source_method in {"converted_usd"}` test | 6's `converted_usd`/PDP row reddens (a showable converted price would be blanked) — the W4-1 composition mutation |
| use `pd.get("category")` only, dropping `_infer_category_from_query` | 3 and 7's `not_exact` row redden (the fragrance derivation is lost) |
| make `prescoring_showable_guard_enabled()` return `True` unconditionally | 10 reddens; 14 stays green |
| read the env into a module constant at import | 16 reddens |
| stash on the PRICE (`_price["_prescoring_showable_rejected"]`) instead of the product | 5 reddens (the key dies with the replaced dict) |
| `de-dup` removed from the harvest (`_guard_rejected_diag.append` unconditional) | 15 reddens |
| run the guard BEFORE `apply_region_currency_guard` | no test reddens — **note this explicitly**: with the region flag OFF the order is unobservable; the ordering is pinned by the code comment and by `#113`'s own contract, not by a test. Say so in the report rather than inventing a test that does not discriminate. |
| test 9 has no mutation target | it is a no-change pin by construction; note it |

---

## 7. Honest limits — what this unit does NOT fix

1. **`scoring_v2` is already honest today and this unit does not change it.**
   Measured (`w43_probe3.py`): `scoring_v2.win_margin == 12` and the price/value
   dims read `{"score_a":75,"score_b":75,"delta_text":"Price data unavailable",
   "caption_key":"limited_data"}` in BOTH the HEAD and guarded runs, because
   `_build_scoring_v2` (`response_builder.py:1097`, called at `:1827`) runs AFTER
   the chokepoint has pended `product_data`. The defect lives in
   `overview.winner.margin`, `scoring.scores.*.breakdown`,
   `scoring.dimension_winners`, `winner_evidence` and the LLM verdict's input —
   not in `scoring_v2`.
2. **The LLM verdict text is not re-run.** The guard changes
   `build_scores_summary`'s output (measured: the `Dimension leaders: … value=`
   segment flips from `Sony Sony WH-1000XM5` to `Bose Bose QuietComfort Ultra`
   in the one-sided case), which is the GPT verdict's input. But a verdict already
   generated from a raw-price summary on a cached/partial path is not regenerated,
   and `comparison.winner.reason` is free GPT text this unit never inspects. The
   wave plan's phrasing "assert `overview.winner.reason` carries no price-derived
   margin" is not achievable as a deterministic assertion — see disagreement #5.
3. **`win_margin == 0.0` can produce a coin-flip winner.** In the spec-poor
   both-sided case (§1.3) the guard drives the margin to `0.0` and
   `winner_index` falls to the deterministic index-0 tie-break. That is the
   H6/`INSUFFICIENT_DATA` family's known hazard (`scs:3615`), unchanged by this
   unit, and it is the honest outcome: with both prices unshowable and no spec
   signal there IS no evidence for a winner. `PO-VERDICT-TRUTH-02` owns the
   fabricated-winner half.
4. **`ENABLE_EXACT_PRICE_GATE` OFF disarms most of the guard.** Measured: with the
   gate OFF, the same google-linked `local_bhd` row is `showable=True`,
   `guard_rejected=None` — the whole `enforce_correctness` block at
   `price_service.py:1855` is gated on it. With the gate OFF this unit still pends
   `estimated` / `gpt_organic_extract` / non-positive amounts (the pre-gate half of
   the predicate) but nothing url- or identity-based. Correct, not a gap: prod runs
   the gate ON (default `"true"`, `:4219`).
5. **Cached and pre-existing rows are not re-evaluated.** The pass runs per request
   over the assembled `product_data`; it writes nothing back to the price cache and
   does not migrate anything.
6. **The KPI will move.** `usable_exact_genuine` and the win-margin distribution
   both change the moment the flag flips; the review's "1,032 of 1,484 `local_bhd`
   rows" figure is the review's and was NOT re-measured here (the cache is not
   readable offline in this worktree).
7. **A list-typed `price["title"]` is coerced one step earlier** with the flag ON
   (inside the guard rather than at the `prices` projection / chokepoint), because
   `is_price_showable` mutates `price["title"]` at `:1819-1824`. No consumer between
   the two points reads `title` (the `specs` yield reads brand/name/specs/fact_check/
   image_url only — `scs:4300-4311`), so no observable difference; stated because it
   is a real mutation moving earlier.
8. **No live request was exercised.** Everything above is offline: the pure pass,
   the scorer, the response builder, and the `prices` projection copied verbatim.
   The streaming call sites are pinned by test 8 through the fully-mocked
   `_mock_to_verdict` harness, which is what `#113`'s own file does.

---

## 8. Spec disagreements with the review

1. **Anchor drift — every review anchor is stale.**

| review (`76ace90`) | at HEAD `b63a8368` | resolved by |
|---|---|---|
| `structured_comparison_service.py:3373-3418` (sync) | `:3641` fairness, `:3658` region guard, `:3686` `compute_scores` | symbol; `76ace90:3373` IS `reconcile_pair_fairness(` — the block moved +268 lines |
| `structured_comparison_service.py:3985-4128` (stream twin) | `:4275` fairness, `:4293` region guard, `:4340` projection, `:4356` `prices` yield, `:4418` `compute_scores` | symbol; `76ace90:3985` IS `reconcile_pair_fairness(` — +290 lines |
| `response_builder.py:1522` (tables row) | **`:1522`, unchanged** — verified byte-identical via `git show 76ace90:app/services/response_builder.py \| sed -n '1522p'` | coincidence, not luck; recorded so nobody "corrects" it |
| `price_service.py:2992` ("the code's own comment names this hazard") | `:3113` — `76ace90:2992` sits inside `apply_region_currency_guard`'s docstring (verified by `git show`); at HEAD that docstring spans `:3092-3121`, with the hazard sentence at `:3097-3105` and the `_region_guard_rejected` rationale at `:3112-3117`. At HEAD, `:2992` is an unrelated line in the fairness re-selection helper | symbol |

2. **"`value_score` is the MISSING sentinel" is true only when the SPEC signal is
   also missing.** `_compute_value_score` returns `MISSING_SCORE` only at
   `if spec_gone and price_gone` (`scoring_service.py:1202-1203`); with a real spec
   signal it returns `spec_score` (`:1207`). Measured: `89.5 → 85.0` with specs,
   `100.0 → 50` without. Red test 1 asserts the first, red test 2 the second. The
   review's headline number is reproduced; its characterisation is imprecise.
3. **"`missing_data` lists it BEFORE `compute_scores` runs (RED today)" is STALE
   for the review's own example.** Measured: on the electronics shape `value_score`
   is in `missing_data` at HEAD in BOTH states (`PO-RUBRIC-01`). The wave plan's
   own `tests_first` column flags this as a load-bearing verifier caveat; this spec
   confirms it by measurement and moves the `missing_data` assertion to the
   FRAGRANCE shape (red test 3), where it is genuinely red.
4. **`scores.product_0.breakdown.value_score` is not a response key.** The wire
   path is `response["scoring"]["scores"]["product_0"]["breakdown"]["value_score"]`
   (`response_builder.py:1818-1819`). `response["scores"]` does not exist
   (measured: `None`). Tests must use the `scoring` key or assert on
   `compute_scores`' return directly.
5. **"assert `overview.winner.reason` carries no price-derived margin" is not
   implementable as specified.** Measured: `overview.winner.reason` is
   `'Sony WH-1000XM5 is the stronger overall pick.'` in BOTH the HEAD and guarded
   runs — it is the deterministic fallback string, not a margin sentence, and on a
   real request it is free GPT text. The assertable, price-derived surfaces are
   `overview.winner.margin` (`24.6 → 22.8`; `17.0` in the one-sided case),
   `scoring.dimension_winners.value_score`, and `winner_evidence`. This spec
   asserts those. **Open ruling requested:** accept the substitution, or add a
   separate unit that makes the verdict prompt refuse price language when the price
   is pending.
6. **The review row does not mention the `metadata.guard_rejected` regression.**
   Measured (§1.6): the naive pre-scoring pend silently empties it. The harvest
   block (§2.4) and red test 5 are ADDITIONS to the review's design, taken directly
   from `#113`'s solution to the identical problem. Without them the canary for
   this flag reads clean while the flag is working — the exact failure CLAUDE.md:362
   documents for the region guard.
7. **"Keep `response_builder.py:1522` as an idempotent backstop" — agreed and
   pinned** (red test 14). Recorded because the review's `files` column lists
   `response_builder.py:1522` as a file to touch; this unit touches it only to ADD
   the harvest block, never to move or weaken the check.
8. **Product decisions I am NOT making.** (a) Whether a pended price should still
   contribute a `price_tier` to `is_cross_tier` (measured: `price_tiers` stays
   `{'…': 'mid', '…': 'mid'}` after the guard because the tier was computed from
   the pre-guard array — left exactly as `#113` leaves it). (b) Whether the
   deterministic tie-break should refuse to crown anyone at `win_margin == 0.0`
   (`PO-VERDICT-TRUTH-02`'s territory). (c) Whether `guard_rejected` reasons should
   reach the client at all (they do not today, and this unit keeps it that way).
   (d) The activation window relative to `ENABLE_REGION_CURRENCY_GUARD` — both are
   pre-scoring pends and both flip winners; my recommendation is W4-3 flips in its
   OWN window, AFTER `ENABLE_SHOPPING_CURRENCY_TRUTH` (W4-1) and
   `ENABLE_SHOPPING_DISCOVERY_URL_SPLIT` (W4-2) and BEFORE
   `ENABLE_REGION_CURRENCY_GUARD`, so the highest-blast-radius flag stays last as
   CLAUDE.md:354 requires — but the ordering is Ahmed's call.

---

## 9. Blast radius

### 9.1 Changed surface and its consumers

| new/changed symbol | consumers at HEAD |
|---|---|
| `price_service.prescoring_showable_guard_enabled` (new) | 2: `apply_prescoring_showable_guard`, `response_builder`'s harvest |
| `price_service.apply_prescoring_showable_guard` (new) | 2: `structured_comparison_service:~3663` (sync), `~4298` (stream) |
| product-level `_prescoring_showable_rejected` (new key) | 1: the `response_builder` harvest. `public_price_view` never sees it (product-level, not price-level); both product projections build explicit key sets |
| `product_data[i]["price"]` mutated in place, flag ON | `compute_scores` (`scs:3686`, `:4418`; also `scripts/shadow_experiments.py:761`, which does not call the orchestrator), the SSE `specs`/`prices`/`reviews`/`first_paint` yields, `build_comparison_response` (`scs:3229` hard-cap partial, `:3825` sync, `:4598` stream complete), `compute_confidence`, `self._partial_product_data` (`scs:3605` — the SAME list object, so the partial path sees the guarded data too) |
| `response_builder`'s `_guard_rejected_diag` | 1: `metadata.guard_rejected` |

`grep -rn "compute_scores(" app scripts` → 3 call sites (2 orchestrator + 1 script).
`grep -rn "build_comparison_response(" app scripts` → 3 call sites, all in
`structured_comparison_service.py`. Test-side reference counts are in Gate 2.

### 9.2 Client impact — the phones still run the PRE-OTA client

Read-only scan of `SmartCompareApp/src`:

* **`metadata.guard_rejected`: zero references anywhere in the client** (measured).
  The harvest is a canary/KPI surface only.
* **`missing_data`: zero references.** `ProductScores` (`src/types/types.ts:343-347`)
  declares only `overall`, `breakdown`, `weights_used` — adding `value_score` to
  `missing_data` is invisible to the current client.
* **`overview.winner.margin` IS read**: `ResultsScreen.tsx:463`
  `const margin = scoring_v2?.win_margin ?? result?.overview?.winner?.margin;`
  feeding the CTA variant at `:464-468` (`>= 15` → `strong`, `< 8` → `close`, else
  `default`). `scoring_v2.win_margin` takes precedence and was **unchanged (12) in
  both states** in every case measured; `overview.winner.margin` moves
  (`24.6 → 22.8`, `24.6 → 17.0`). A margin near 15 or 8 can therefore flip the CTA
  copy variant on the fallback branch. **No crash, no undefined, no shape change** —
  the field stays a number.
* **`breakdown.value_score` is typed non-optional `number`**
  (`types.ts:334-341` — `ScoreBreakdown`). In every flag-ON combination measured
  (defaults; `ENABLE_BUNDLE_C_SCORING=true`; `ENABLE_MISSING_DIM_OMISSION=true`;
  fragrance; electronics with and without spec signal) the value stayed a number
  (`85.0 / 45.0 / 65.7 / 50`). **No `null` is introduced**, so the type contract
  holds for the pre-OTA client.
* **`DimensionWinner` is `{winner: string; margin: number | null}`**
  (`types.ts:349-352` — `DimensionWinner`). The guard produces `{"winner":"N/A","margin":null}` — both
  already occur at HEAD (measured in the §1.2 HEAD run for
  `build_quality_score`/`ecosystem_score`), and `margin` is already declared
  nullable. Shape-safe.
* **`overview.products[i].price`** is `{"amount": null, "unavailable": true,
  "reason": "pending_genuine"}` — the identical shape the chokepoint already ships
  today for these rows (`ResultsContent.tsx` renders the calm pending line). **Byte-identical.**
* **SSE `prices` event: byte-identical**, measured (§3).

**Conclusion:** the only client-observable change is the VALUE of numbers the
client already reads (`overview.winner.margin`, `breakdown.*`, `dimension_winners.*`)
and, on the one-sided case, which product is named the winner. No key is added,
removed, retyped or nulled. The backend stays safe for the CURRENT client.

---

# FABLE REVIEW RULINGS (binding, 2026-09-23) — W4-3 `ENABLE_PRESCORING_SHOWABLE_GUARD`

Reviewer verdict SOUND_WITH_CHANGES (Opus 5.5 adversarial spec review, read-only, at `b63a8368`). The defect reproduces under default flags; the design mirrors #113 in placement and blanking; flag-OFF is byte-identical (full-response sha equal, Preserve suite 156 passed); the harvest is load-bearing (without it `metadata.guard_rejected` empties); W4-1 composition is safe. The DESIGN stands; the spec's client-impact section, mutation table and several tests are corrected below. Everything below overrides the spec body where they conflict.

## R1 (BLOCKING) — the SYNC twin must be pinned
Every spec test drives the helper directly or `compare_from_text_streaming` only; deleting the sync call site reddens nothing (measured). Add a sync-path orchestrator pin on an existing harness (`tests/test_compare_timeout_graceful.py` / `test_explicit_pair_integration_mocked.py` pattern): `compute_scores` side_effect records its product input and raises; assert the recorded input carries the pended price for a google-url row. Mutation: delete the sync call ⇒ this pin reds; delete the stream call ⇒ test 8 reds. The two twins stay in lockstep by construction (same helper, same placement: after the fairness/currency guard, before `compute_scores`).

## R2 (BLOCKING) — the client-impact section is rewritten against 97b5f15; the flag stays
`scoring_v2` CHANGES in every shape and every flag combination (both-google 82/68 → 79/66; one-sided 82/68 → 79/69; spec-poor one-sided 75/68 → 70/72 with the crown flipping), and `scoring_v2` is the ONLY results surface the phones' 97b5f15 bundle renders (rings, crown via `product_a >= product_b`, DimensionBars, confidence legs). `overview.winner.margin`, `breakdown`, `dimension_winners`, `missing_data` and `guard_rejected` have zero readers at 97b5f15; the CTA reads `scoring?.win_margin`, which the legacy block never carries, so it is always `default` and unaffected. Winners flip on legitimate traffic ⇒ a result fork ⇒ the flag stays, default OFF, per-call.

## R3 — the in-call de-dup is dead code; the double-count is real and is fixed under the flag
`_guard_rejected_diag` is created fresh per `build_comparison_response` call, so the specified de-dup cannot be falsified (test 15 stays green with it removed). Delete it. The real duplicate shape is a pre-scoring stash PLUS the chokepoint's own unconditional append (`response_builder.py:~1535`) for a price that is not pended on display — measured two `non_pdp_url` rows for one product. Under the flag the chokepoint append becomes idempotent on `(product_index, reason)`. Pin: stash + unpended price ⇒ exactly one entry per product; mutation: remove the idempotency guard ⇒ red. Direct callers of the builder other than the three orchestrator sites do not exist (the "share / history rebuild" caller cited by the spec is not real).

## R4 — the guard order IS observable; pin it
With `ENABLE_REGION_CURRENCY_GUARD=true`, region `saudi_arabia`, a BHD price behind a google url: showable → region gives currency BHD and stash `non_pdp_url`; region → showable gives SAR and `region_currency_mismatch`. Add the both-flags-ON test pinning showable-then-region (the load-bearing order); replace the mutation-table row that called it unobservable.

## R5 — category-derivation mutation needs a discriminating fixture
Test 3 (google url) is category-independent and the Dior EDT/Parfum row is `not_exact` under every category. Pin the derivation with a row that OMITS `pd['category']` and where the inferred category decides: `Apple iPhone 15` vs title `Apple iPhone 15 Pro` ⇒ `not_exact` with `electronics`, showable with `None`.

## R6 — the `or "not_showable"` fallback STAYS, as a documented new reason with a canary split
Scoring must agree with display, and the chokepoint pends every non-showable row (estimated / sample / low-floor rows return False before any stamp). So the pre-scoring guard pends them too, stamping `not_showable`. Document it as a NEW `metadata.guard_rejected` reason (the warmer's log at `scripts/cron_warm_price_cache.py:246` will see it), and the canary counts it separately from the url/identity reasons. The prod share of estimated rows is measured on the first canary day and recorded.

## R7 — blast-radius disclosures the spec omitted (all measured; all go in the spec and the PR body)
(a) A pended price has no `source_method`, so `_product_source_method` returns `estimated` and every pended product takes the -4 price-authority overall penalty (most of the overall drop). (b) `price_tiers` are recomputed AFTER the guard and a `None` price defaults to `mid`, which can MANUFACTURE `is_cross_tier` and cut the honest, showable product's value score (40.5 → 15.6) while crowning it value "winner" at the lower score. This is a `scoring_service` hazard shared with #113 and outside this unit's must-not-touch list: pin the CURRENT behaviour so it is visible, and open follow-up `PO-RECORDED-MEASURED-04b` (exclude a missing-price tier from `is_cross_tier`), sequenced BEFORE this flag flips. (c) A pended product's `breakdown.value_score` becomes its spec score, not the sentinel — a pended EXPENSIVE price raises it. (d) `overview.confidence` reports `price.method: estimated` for pended rows (persisted, not rendered on phones); the one-sided evidence line "relies on an indicative figure" is not honest for a card that shows no figure — reword under the flag or state it. (e) The verdict's raw-price channel is `best_price` and `scores_summary`, not `price` (already scrubbed at HEAD); the guard closes both when ON — pin `best_price is None` in the verdict payload under the flag; queue an UNFLAGGED one-line follow-up in `_verdict_safe_product` to null `best_price` whenever the price pends (flag-OFF still leaks it).

## R8 — test-list corrections
Test 1 also asserts `value_score` in `missing_data` for the numeric-spec electronics shape (it IS red there; only the spec-poor shape pins nothing). Tests 11/12/13 and test 6's PDP half are red only by ImportError — write them so a stub `return False` reddens at least one. Tests 9 and 14 are labelled regression pins. State the fixture amounts so test 1's numbers reproduce. Anchors: `_is_listing_url` `:8263`, `compute_dimension_winners` `:2430`; `ENABLE_MISSING_DIM_OMISSION` does not exist (the real flag is `ENABLE_MISSING_DIM_RENORM`, swept: no nulls); §10/§8.4 references are dropped; "size lost" in the drop-early-continue row is false (`make_pending_price` carries size).

## R9 — KPI and canary
`usable_exact_genuine` does NOT move from W4-3 alone (the displayed price is identical in both states). The canary reads `scoring_v2.overall_score` / `winner_idx` and the SSE `scores` event — what phones render — split by reason including `not_showable`.

## R10 — activation and merge order
Own window, after W4-1 and W4-2 (W4-2 un-pends google rows W4-3 would pend, so flipping W4-3 after W4-2 moves the pend set once — stated in the runbook); `ENABLE_REGION_CURRENCY_GUARD` last. The corpus byte-identity gate is blind to this unit (320-call trace never reaches `is_price_showable`) — run as a formality and say so. Merge after W4-1 (scs anchors after `:1214` shift +5).
