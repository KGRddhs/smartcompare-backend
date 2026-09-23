# W4-2 — the shopping rung must not put a search link in `price["url"]`

Finding `PO-RECORDED-MEASURED-03`. **Backend only** (the client is read-only here and
reads nothing that changes — measured, see Blast radius). Flag
`ENABLE_SHOPPING_DISCOVERY_URL_SPLIT`, **default OFF, read PER CALL**.
Worktree `C:/Users/SynAckITPC/Documents/AI/sc-w4-2`, branch
`feature/s65-w4-2-shopping-url-split`, base commit **`b63a8368`**
(= `origin/main`, "Merge pull request #159"). Every line anchor below is at
`b63a8368` and was read there; the review's anchors are from `76ace90` and have
drifted (per-anchor table in §8). Every behavioural claim below was produced by a
probe run offline (`PYTHONIOENCODING=utf-8`, conftest-equivalent env —
`load_dotenv(override=True)` + `neutralize_credentials()` + `install_dotenv_guard()`,
no `LIVE`, zero network); the real output is pasted.

The unit is designed **against the post-W4-1 code**: W4-1 is in flight and uncommitted
in `C:/Users/SynAckITPC/Documents/AI/sc-w4-1` (base `ed75dc70`, 338 insertions across
`price_service.py` + `structured_comparison_service.py`; read via
`git -C …/sc-w4-1 diff HEAD -- app/`). W4-1 was also **executed read-only** to measure
the composition (§1.6). **Hard order: W4-1 lands WITH or BEFORE this unit, and
`ENABLE_SHOPPING_CURRENCY_TRUTH` flips BEFORE `ENABLE_SHOPPING_DISCOVERY_URL_SPLIT`.**

---

## 1. The defect, measured

### 1.1 Who produces the url

`extract_price_from_shopping` (`app/services/price_service.py:9681`) builds every
Serper-Google-Shopping candidate at `:9841-9860`. The url line is **`:9845`**:

```
:9828        link = item.get("link", "")
:9841        candidates.append({
:9845            "url": item.get("link") or build_retailer_url(retailer, product_name),
:9849            "source_method": "converted_usd" if item_converted else "local_bhd",
:9912        if not exact_gate_enabled():
:9913            best.pop("title", None)
```

`build_retailer_url` (`:9394`) is, by its own docstring, *"Build a retailer **search**
URL"* — it formats one of the 46 `RETAILER_SEARCH_URLS` templates (`:380`). So the key
that the display backstop treats as "the PDP" is, on this rung, **either Serper's
Google-Shopping search link or a synthesized retailer search link**.

The **stash mirror** `StructuredComparisonService._seed_shortcircuit_candidates`
(`app/services/structured_comparison_service.py:8172`) stamps it **identically** at
**`:8276`**:

```
:8276                        "url": item.get("link") or build_retailer_url(retailer, full_name),
```

— so the rule must be applied in both doors (the CD-wave-diffs-03 lesson W4-1 restates).

A third, out-of-scope mirror of the same expression is `rating_service.py:198` and
`:239` (`rating_source.url`) — see §7 limit 5.

### 1.2 Who consumes it

| consumer | anchor | what it does with `price["url"]` |
|---|---|---|
| display backstop | `price_service.py:1867-1870` | `if url and _is_listing_url(url): price["guard_rejected"]="non_pdp_url"; return False` — **a MISSING url is not pended** (`:1871-1881` only pends when there is neither identity NOR url) |
| cache-write gate | `price_service.py:9072-9073` (`should_cache_price`) | `if not url or _is_listing_url(url): return False` |
| selector | `price_service.py:8353-8360` (`select_best`) | `require_url=True` (default) drops a url-less candidate; a listing url is dropped even with `require_url=False` |
| budget-house floor bypass | `price_service.py:4626-4628` | requires a present non-listing url |
| public projection | `price_service.py:9118` (`public_price_view`) | strips `guard_rejected` + `_`-prefixed keys **only when `exact_gate_enabled()`** |
| Tier-1 park vs short-circuit | `structured_comparison_service.py:6650-6654` | `_t1_url = price.get("url") or ""` → `_is_listing_url` decides **park** (cascade continues) vs **genuine short-circuit** (cascade stops, `_persist_genuine_price`, return) |
| parked-row url backfill | `structured_comparison_service.py:7661-7663` | `if converted_fallback.get("retailer") and not converted_fallback.get("url"): converted_fallback["url"] = build_retailer_url(...)` |
| KPI `usable_exact_genuine` | `scripts/eval_runner.py:532-540` | clause (d): a missing url is **not usable**; a listing url is not usable |
| L2 row | `product_data_service.py:345` | persists `url` (only reachable behind `should_cache_price`) |
| **the CURRENT client** | — | **nothing.** `grep -rn "price\.url\|price?\.url" SmartCompareApp/` = **0 hits**. The only `Linking.openURL` on a product surface is `rating_source.url` (`ResultsScreen.tsx:533-535`). |

Four response chokepoints call `is_price_showable(..., enforce_correctness=True)`:
`response_builder.py:1522`, `structured_comparison_service.py:4340` (SSE) and `:8601`
(regional), `api/text_routes.py:1163`, plus `extraction_service.py:2290` and
`zyte_service.py:672`.

### 1.3 RED reproduction (probe `w42_probe.py`, real output)

```
=== env ===
  ENABLE_EXACT_PRICE_GATE=None
  ENABLE_SHOPPING_DISCOVERY_URL_SPLIT=None
  ENABLE_PARK_LISTING_URL_TIER1=None
  exact_gate_enabled() = True

=== A: google-linked shopping item through the real function ===
  result keys: ['amount','concentration','confidence','currency','in_stock','retailer',
                'retailer_score','size','source_method','title','url']
  url          = https://www.google.com/search?ibp=oshop&q=Creed+Aventus&prds=catalogid:1234567890
  discovery_url= <ABSENT>
  source_method= local_bhd
  amount       = 259.44 BHD
  title        = Creed Aventus 100ml

=== D: the review's exact RED assertion, through the real pair ===
  is_price_showable(...enforce_correctness=True) = False
  guard_rejected = non_pdp_url
```

The finding's `test_first` assertion is therefore **RED at HEAD**, exactly as filed.

The rest of the chokepoint matrix (same probe):

```
=== C: is_price_showable(enforce_correctness=True) ===
  google search link     -> showable=False guard_rejected='non_pdp_url'
  noon search link       -> showable=False guard_rejected='non_pdp_url'
  real PDP               -> showable=True  guard_rejected=None
  url=None               -> showable=True  guard_rejected=None
  no url key             -> showable=True  guard_rejected=None

=== C2: same, source_method=converted_usd (the post-W4-1 label) ===
  google search link     -> showable=False guard_rejected='non_pdp_url'
  url absent             -> showable=True  guard_rejected=None

=== C3: url absent AND title absent (the no_identity backstop) ===
  -> False no_identity

=== E: should_cache_price ===
  google search link -> False      real PDP -> True
  url absent         -> False      url None -> False

=== I: select_best ===
  google  require_url=True -> False   require_url=False -> False
  absent  require_url=True -> False   require_url=False -> True
  pdp     require_url=True -> True    require_url=False -> True

=== J: TTL / genuineness ===
  local_bhd      ttl=604800 genuine=True
  converted_usd  ttl=86400  genuine=False
```

So: **removing the url un-pends the row and changes nothing about caching
(`False→False`) or selection (`False→False`)** — but it *does* silently change the
Tier-1 park decision, which the review never mentions (§1.5).

### 1.4 The no-link fallback is only PARTLY pended — the review understates it

`probe2` ran all 46 `RETAILER_SEARCH_URLS` templates through `_is_listing_url`:

```
=== every RETAILER_SEARCH_URLS template through _is_listing_url ===
  NOT-LISTING  adorama      https://www.adorama.com/l/?searchinfo=Creed+Aventus+100ml
  NOT-LISTING  aliexpress   https://www.aliexpress.com/wholesale?SearchText=Creed+Aventus+100ml
  NOT-LISTING  amazon       https://www.amazon.com/s?k=Creed+Aventus+100ml
  NOT-LISTING  amazon.ae    https://www.amazon.com/s?k=Creed+Aventus+100ml
  NOT-LISTING  amazon.sa    https://www.amazon.com/s?k=Creed+Aventus+100ml
  NOT-LISTING  apple        https://www.apple.com/shop/buy?fh=Creed+Aventus+100ml
  NOT-LISTING  ebay         https://www.ebay.com/sch/i.html?_nkw=Creed+Aventus+100ml
  NOT-LISTING  newegg       https://www.newegg.com/p/pl?d=Creed+Aventus+100ml
  NOT-LISTING  target       https://www.target.com/s?searchTerm=Creed+Aventus+100ml
  totals: n=46 listing=37 NOT-listing=9

=== the NOT-listing ones: is_price_showable(enforce_correctness=True) today ===
  adorama    showable=True guard=None cache=True
  aliexpress showable=True guard=None cache=True
  amazon     showable=True guard=None cache=True
  amazon.ae  showable=True guard=None cache=True
  amazon.sa  showable=True guard=None cache=True
  apple      showable=True guard=None cache=True
  ebay       showable=True guard=None cache=True
  newegg     showable=True guard=None cache=True
  target     showable=True guard=None cache=True
```

**9 of 46 synthesized search urls are SHOWN and CACHED as genuine `local_bhd`
for 7 days on a url we fabricated and never fetched.** That is the *opposite*
direction of the filed finding and strictly worse than a pend — and it is the reason
this unit's rule is "a search link never enters `url`", not "an
`_is_listing_url`-positive link never enters `url`". (See the §8 disagreement and the
ruling requested.)

### 1.5 The two composition hazards the review did not see — MEASURED

**(a) The Tier-1 park.** `ENABLE_PARK_LISTING_URL_TIER1` is **default ON**
(`structured_comparison_service.py:2406`, `not in ("false","0","no","off","")`). Its
branch (`:6648-6692`) uses `price["url"]` to choose between *parking* a genuine Tier-1
shopping price (cascade continues to the real-PDP adapters) and the *genuine
short-circuit* (`_cancel_prefetched_discovery()`, `_seed_shortcircuit_candidates`,
`_persist_genuine_price`, `return price`). `probe3`, evaluating the exact `:6652-6654`
expression:

```
=== Tier-1 park predicate (scs :6650-6654 expression) ===
  url=google                        _tier1_is_listing_url(today)=True  (url-or-discovery)=True
  url=PDP                           _tier1_is_listing_url(today)=False (url-or-discovery)=False
  url absent                        _tier1_is_listing_url(today)=False (url-or-discovery)=False
  url absent + discovery_url=google _tier1_is_listing_url(today)=False (url-or-discovery)=True
```

So a naive "just drop the url" **flips a parked google row into a genuine Tier-1
short-circuit**: the discovery prefetch is cancelled, the whole Tier-1.5 adapter
cascade (woo/shopify/algolia — the local Arabic houses) never runs, and
`_persist_genuine_price` is called. This unit must teach that predicate the discovery
url, under the same flag.

**(b) The parked-row url backfill** (`:7661-7663`). A parked shopping row whose `url`
was dropped hits `if converted_fallback.get("retailer") and not
converted_fallback.get("url")` and gets `build_retailer_url(retailer, full_name)`
stamped back on — re-minting the very search link the unit removed (and, for the 9
shapes above, minting it as *showable*). Measured: `build_retailer_url("Best Buy",
"Creed Aventus 100ml") = 'https://www.bestbuy.com/site/searchpage.jsp?st=…'` (non-None),
and `retailer` is always set on this rung (`item["source"]`).

### 1.6 Composition with W4-1 (measured against the in-flight tree)

`probe3` was run a second time with `sys.path` pointed at `sc-w4-1`
(`PYTHONDONTWRITEBYTECODE=1`; `git -C sc-w4-1 status --porcelain` unchanged before and
after — ` M app/services/price_service.py`, ` M
app/services/structured_comparison_service.py`, `?? tests/test_shopping_currency_truth.py`):

```
=== tree === C:/Users/SynAckITPC/Documents/AI/sc-w4-1
  has shopping_currency_truth_enabled: True

=== W4-1 composition: flag ON, google link ===
  source_method = converted_usd
  url           = https://www.google.com/search?ibp=oshop&q=Creed+Aventus&prds=catalogid:1234567890
  showable(enforce)= False
  same row with url REMOVED -> showable(enforce)= True genuine= False ttl= 86400 cacheable= False

=== W4-1 flag ON, NO link (build_retailer_url fallback) ===
  source_method = converted_usd
  url           = https://www.bestbuy.com/site/searchpage.jsp?st=Creed+Aventus+100ml

=== W4-1 flag ON, real BH PDP link (must stay local_bhd) ===
  source_method = local_bhd  url = https://bahrain.sharafdg.com/product/creed-aventus-100ml
  showable(enforce)= True

=== W4-1 flag OFF, google link (today's shipped default) ===
  source_method = local_bhd  url = https://www.google.com/search?ibp=oshop&q=…
  showable(enforce)= False
```

**The composition target is met exactly:** with W4-1 ON the google-linked row is
`converted_usd`; with W4-2 ON its url is gone; the pair is
**showable=True, genuine=False, ttl=86400 s, cacheable=False** — showable-not-genuine,
never genuine. W4-1 reads the *item's* `link` (`_shopping_bh_host_evidence(link,
ask_currency=currency, …)`), **not** `price["url"]`, so W4-2 dropping the url cannot
disarm W4-1's relabel — verified by reading the diff and by the run above.

Conversely, with W4-1 **OFF** and W4-2 ON, the same row is `local_bhd` (genuine,
7-day TTL, KPI-eligible-by-method) and would become *showable*. That is the review's
hard order, and it is why `ENABLE_SHOPPING_CURRENCY_TRUTH` flips first.

---

## 2. The design — `ENABLE_SHOPPING_DISCOVERY_URL_SPLIT` (default OFF, read per call)

Option **(b)** of the finding: *keep the search link out of `url`, in a diagnostic
`discovery_url`*. Option (a) (resolve the merchant PDP before selection) is **NOT**
implemented — its cost is stated in §7/§8.

### 2.1 The flag reader (`price_service.py`, next to `shopping_strict_currency_enabled` `:9549`)

Copy that helper's idiom verbatim (per-call `os.getenv`, empty default, truthy set):

```python
def shopping_discovery_url_split_enabled() -> bool:
    """True iff a SEARCH link is kept out of the shopping candidate's ``url``
    and carried in ``discovery_url`` instead (default OFF).

    W4-2 (PO-RECORDED-MEASURED-03). ... Read PER CALL from os.getenv so Railway
    can flip it without a restart; default OFF so flag-OFF is byte-identical.
    """
    return os.getenv("ENABLE_SHOPPING_DISCOVERY_URL_SPLIT", "").strip().lower() in (
        "true", "1", "yes", "on",
    )
```

### 2.2 The one shared splitter (`price_service.py`, immediately below the reader)

```python
def _shopping_split_discovery_url(
    link: Optional[str], retailer: str, product_name: str,
) -> Tuple[Optional[str], Optional[str]]:
    """(url, discovery_url) for a shopping candidate. Pure; the callers gate it."""
    if link:
        return (None, link) if _is_listing_url(link) else (link, None)
    return (None, build_retailer_url(retailer, product_name))
```

Three rungs, each with its measured justification:

| rung | input | flag ON | why |
|---|---|---|---|
| 1 | a Serper `link` that `_is_listing_url` flags | `url=None`, `discovery_url=link` | it is the exact url the backstop pends (`:1869`) |
| 2 | **no** `link` | `url=None`, `discovery_url=build_retailer_url(...)` | a `build_retailer_url` output is a SEARCH url by construction; 9 of 46 evade `_is_listing_url` and ship showable+cacheable today (§1.4) |
| 3 | a real PDP `link` | `url=link`, `discovery_url=None` | unchanged — measured `bahrain.sharafdg.com/product/…` stays `local_bhd`, showable |

`Tuple` and `Optional` are already imported (`price_service.py:20`).

### 2.3 The four edited call sites

**(i) `price_service.py:9841-9860` — the front-door candidate.** `link` is already in
scope (`:9828`).

```python
_url = item.get("link") or build_retailer_url(retailer, product_name)
_discovery: Optional[str] = None
if shopping_discovery_url_split_enabled():
    _url, _discovery = _shopping_split_discovery_url(link, retailer, product_name)
candidates.append({
    ...
    "url": _url,
    ...
    **({"discovery_url": _discovery} if _discovery else {}),
})
```

Flag OFF the expression is character-for-character today's, `_discovery` is `None`, and
`**{}` adds no key: **the candidate dict's key set is unchanged**.

**(ii) `structured_comparison_service.py:8270-8279` — the stash mirror.** The identical
two lines against `item.get("link")` and `full_name`, under the same flag, importing
`shopping_discovery_url_split_enabled` and `_shopping_split_discovery_url` from
`price_service` (extend the existing import block at `:1195-1240`).

**(iii) `structured_comparison_service.py:6650-6654` — the Tier-1 park predicate.** Add
ONE module-level helper in `structured_comparison_service.py` and use it at both
composition sites:

```python
def _discovery_url_of(price: Dict[str, Any]) -> str:
    """W4-2 — the split-off SEARCH url of a price, or "" (flag OFF -> always "")."""
    if not shopping_discovery_url_split_enabled():
        return ""
    return str(price.get("discovery_url") or "") if isinstance(price, dict) else ""
```

then

```python
_t1_url = price.get("url") or _discovery_url_of(price) or ""
```

Flag OFF ⇒ `_discovery_url_of` is `""` ⇒ the expression is today's.

**(iv) `structured_comparison_service.py:7661-7663` — the parked-row backfill.**

```python
if (converted_fallback.get("retailer")
        and not converted_fallback.get("url")
        and not _discovery_url_of(converted_fallback)):
    converted_fallback["url"] = build_retailer_url(...)
```

Flag OFF ⇒ the added conjunct is `not ""` = `True` ⇒ the condition is today's.

### 2.4 Must-NOT-touch (named)

* `is_price_showable` (`price_service.py:1781`) and **every** line of its correctness
  backstop, in particular `:1867-1870` (`non_pdp_url`) and `:1871-1881`
  (`no_identity`). The unit is entirely producer-side; the backstop keeps pending any
  *other* path that puts a listing url in `url`.
* `_is_listing_url` (`:8263`) and `source_router.is_non_pdp_listing_url` — the 9-shape
  blind spot (§1.4) is **not** widened here (own row, §8 limit 2).
* `build_retailer_url` (`:9394`), `_descriptor_search_url`, `has_retailer_url`, and
  `RETAILER_SEARCH_URLS` (`:380`) — including the measured `amazon.ae → amazon.com`
  substring collision (§7 limit 4).
* `should_cache_price` (`:9035`), its `not url` refusal (`:9072-9073`), `select_best`
  (`:8295`) and its `require_url=True` default, `_candidate_authority` (`:8276`),
  `_budget_house_trusted_price` (`:4626`), `public_price_view` (`:9118`).
* `_showable_source_methods` (`:1743`), `_GENUINE_BH_SOURCE_METHODS`,
  `is_genuine_source_method` (`:151`), `price_cache_ttl`, `_is_genuine_bh_candidate`
  (`:16251`). **No new `source_method` string. No change to the label.**
* `_park_listing_url_tier1_enabled()` (`scs:2390`) itself — its name, default (ON) and
  truthy set stay; only the url it is handed changes.
* `scs:7619-7620` and `:7699-7700` (Tier-2 GPT-organic and Tier-3 estimate backfills):
  those prices never carry `discovery_url`, so the guard would be dead code there.
* `rating_service.py:198/239`, `scripts/eval_runner.py:532-540`,
  `product_data_service.save_price`, every file under `SmartCompareApp/`,
  every migration, every doc.
* W4-1's surface: `shopping_currency_truth_enabled`, `_shopping_display_currency`,
  `_shopping_unconvertible_foreign_iso`, `_shopping_bh_host_evidence`,
  `_shopping_price_residue` and the two loop bodies it edits.

### 2.5 Why this beats the alternatives

* **vs. option (a) (resolve the merchant PDP first).** (a) is the real answer and stays
  the documented alternative. Its cost, measured from this codebase: it needs a live
  fetch per shopping candidate on the 15 s critical path (Serper's `link` is the only
  handle we have; there is no offline resolver), a new failure mode (unresolvable ⇒
  drop the candidate ⇒ *fewer* prices, the opposite of the finding's lever), and it
  cannot ship while the Serper account is unfunded — every measurement here would be
  un-runnable. (b) is one expression, no network, and reversible by a flag.
* **vs. "widen `_is_listing_url` so the google link is dropped by the consumer".** That
  keeps a search link in `url`, which is the thing the finding names; every consumer
  would still have to special-case it, and `should_cache_price` already refuses it.
* **vs. mutating `price["url"] = None` at the chokepoint.** The chokepoint must stay a
  pure predicate (W4-5's ruling 3 on the same file); a mutation there leaks into the
  cached row, the L2 write and the SSE payload.
* **vs. adding a third `source_method`.** That touches `_showable_source_methods`, the
  `eval_runner` mirror and the client enum (`types.ts:43-58`) — explicitly out of scope
  and already recorded as the W4-1 product call for Ahmed.

---

## 3. Preserve

Run at HEAD, flag unset (real counts):

| file | nodes | what it pins on the touched paths |
|---|---|---|
| `tests/test_url_quality.py` | **22 passed** | `result["url"] == <serper link>`; `"amazon.com" in result["url"]` for the no-link fallback; `result["url"] is None` for an unknown retailer — the flag-OFF identity of `:9845` |
| `tests/test_park_listing_url_tier1.py` | **16 passed** | the park flag's default-ON + truthy set, and `_is_listing_url` on the three google `ibp=oshop` shapes and three merchant PDPs |
| `tests/test_listing_url_search_family.py` | **15 passed** | the listing-url family classifier |
| `tests/test_shopping_source_method_t2.py` | **5 passed** | the T2 `converted_usd`/`local_bhd` label rule on this rung |
| `tests/test_price_showable.py` | **19 passed** | the chokepoint, incl. the sample/decant guard W4-5 just changed |
| `tests/test_correctness_runtime_leaks.py` | **27 passed** | `public_price_view` strips `guard_rejected` + `_`-keys |
| `tests/test_retailer_url_bahrain_l13.py` | **23 passed** | `build_retailer_url` templates + `has_retailer_url` parity |
| `tests/test_budget_fragrance_floor.py` | **37 passed** | `_budget_house_trusted_price`'s url requirement |

All eight together: **164 passed, 3 warnings in 6.82s** at HEAD.

Also preserved, and pinned by this unit rather than left implicit:

* Flag OFF ⇒ `extract_price_from_shopping` and `_seed_shortcircuit_candidates` return
  **the same dicts with the same key set** (no `discovery_url` key exists at all).
* A real merchant PDP link is untouched in **both** flag states (`local_bhd`, showable).
* `should_cache_price` is `False` for a google-linked row **and** for a
  discovery-only row (measured `False → False`): this unit cannot cache anything new.
* `select_best(require_url=True)` drops a discovery-only row exactly as it drops a
  google-linked one (`False → False`).
* The 30 test files that reference `extract_price_from_shopping` and the 3 that
  reference `_seed_shortcircuit_candidates` run flag-OFF and must stay green.

---

## 4. Red tests — `tests/test_shopping_price_not_self_pending.py`

(The finding's own `test_first` filename.) Toggle with `monkeypatch.setenv/delenv`;
leave `ENABLE_EXACT_PRICE_GATE` at its default (ON) unless a test says otherwise.
Fixtures: `Q = "Creed Aventus 100ml"`,
`GOOGLE = "https://www.google.com/search?ibp=oshop&q=Creed+Aventus&prds=catalogid:1234567890"`,
`PDP = "https://bahrain.sharafdg.com/product/creed-aventus-100ml"`, one title-matched
item `{"title": Q, "price": "259.44", "source": <retailer>, "link": …}`, `currency="BHD"`,
`shopping_region="bahrain"`, `category="fragrance"`.

1. **RED — the finding's exact assertion.** Flag ON, google-linked item:
   `price.get("url") is None`, `price["discovery_url"] == GOOGLE`, and
   `is_price_showable(Q, price, "fragrance", enforce_correctness=True) is True`.
   *RED today:* `url == GOOGLE`, no `discovery_url` key, showable `False`,
   `guard_rejected == "non_pdp_url"`.
2. **PIN — flag OFF (unset, and `"false"`).** Same item: `price["url"] == GOOGLE`,
   `"discovery_url" not in price`, showable `False` with
   `guard_rejected == "non_pdp_url"`. Green today; this is the rollback proof the
   corpus harness cannot see (§5 gate 3).
3. **RED — the synthesized fallback, parametrized** over `("Best Buy", listing-caught)`
   and `("Amazon", NOT-listing-caught)`, item with **no** `link`, flag ON:
   `price.get("url") is None` and `price["discovery_url"] == build_retailer_url(src, Q)`
   and showable is `True`. *RED today* for both: `url` is the search template
   (`bestbuy…` showable `False`; `amazon.com/s?k=…` showable `True` but `url` is a
   fabricated search link, so the `url is None` assertion reds).
4. **PIN — an unknown retailer with no link invents nothing.** Flag ON,
   `source="Totally Unknown Store XYZ"`: `price["url"] is None` **and**
   `"discovery_url" not in price` (measured `build_retailer_url(...) is None`). Green
   today for the `url` half; the key-absence half is the new pin.
5. **PIN — a real PDP is untouched in BOTH flag states.** `link=PDP` ⇒
   `price["url"] == PDP`, `"discovery_url" not in price`, showable `True`,
   `source_method == "local_bhd"`. Green today.
6. **PIN — showable-not-genuine, never genuine (the W4-1 composition target).**
   Construct `{"amount":259.44,"currency":"BHD","retailer":"Best Buy","in_stock":True,
   "source_method":"converted_usd","title":Q,"discovery_url":GOOGLE}` (no `url`):
   `is_price_showable(..., enforce_correctness=True) is True`,
   `is_genuine_source_method("converted_usd") is False`, `price_cache_ttl(...) == 86400`,
   `should_cache_price(Q, ..., "fragrance") is False`. Green today (pure predicates) —
   it pins the invariant the ordering exists to protect.
   **Plus a live half, skipped until W4-1 lands:**
   `pytest.mark.skipif(not hasattr(price_service, "shopping_currency_truth_enabled"))` —
   with BOTH flags ON a google-linked item yields
   `source_method == "converted_usd"` AND `url is None` AND showable `True`. Measured
   green against the in-flight `sc-w4-1` tree (§1.6); it will turn from *skipped* to
   *green* the moment W4-1 merges, and red if either half regresses.
7. **RED — the stash mirror agrees.** `svc._shopping_items_cache[Q] = [google item]`,
   then `svc._seed_shortcircuit_candidates(Q, kind="tier1_shopping", currency="BHD",
   shopping_region="bahrain")` (the harness `tests/test_m21_currency_parity.py` and
   `tests/test_m13_shortcircuit_stash_parse.py` already use). Flag ON: the single seeded
   candidate's `raw_data` has `url is None` and `raw_data["discovery_url"] == GOOGLE`.
   *RED today:* `raw_data["url"] == GOOGLE`. Flag-OFF half is a PIN at today's values.
8. **RED — the Tier-1 park survives the split.** `_discovery_url_of`:
   flag ON + `{"discovery_url": GOOGLE}` ⇒ `GOOGLE`; flag OFF ⇒ `""`; non-dict ⇒ `""`.
   And the park expression `price.get("url") or _discovery_url_of(price) or ""` fed to
   `_is_listing_url` ⇒ `True` for the discovery-only row (flag ON) and `False` (flag
   OFF). *RED today:* the helper does not exist. This is the test that stops a parked
   row silently becoming a genuine Tier-1 short-circuit (§1.5a).
9. **RED — the parked-row backfill is guarded.** The `:7661` condition, flag ON, on
   `{"retailer":"Best Buy","discovery_url":GOOGLE}` (no url) ⇒ the backfill does **not**
   fire (`url` stays absent); flag OFF ⇒ it fires (today). *RED today.*
10. **PIN — the flag reader.** unset ⇒ `False`; `"true"/"1"/"yes"/"on"` ⇒ `True`;
    `"false"/"0"/"no"/"off"/""` ⇒ `False`; `setenv` **after** import flips the next call
    (per-call read, no module constant).
11. **PIN — the wire projection, asserted not assumed.** `public_price_view` on a
    discovery-only price: gate ON ⇒ the returned dict **contains** `discovery_url` and
    not `guard_rejected`/`_cached`; gate OFF ⇒ the input dict is returned unchanged.
    Green today (measured) — it makes the §8 ruling-7 naming question explicit in a test.
12. **PIN — nothing new becomes selectable or cacheable.** For the discovery-only row:
    `select_best([row], Q, "fragrance") is None` (require_url default) and
    `should_cache_price(Q, row, "fragrance") is False`, in **both** flag states. Green
    today; it pins that the unit buys DISPLAY only (§8 limit 1).

---

## 5. Gates

1. **TDD red-first.** `python -m pytest tests/test_shopping_price_not_self_pending.py
   -q -p no:cacheprovider --timeout=180`, recorded to `.qa-w4/W4-2-RED.txt` showing
   1/3/7/8/9 red and 2/4/5/6/10/11/12 green **before** any edit. Then green, and green
   again with `ENABLE_SHOPPING_DISCOVERY_URL_SPLIT=true` exported.
2. **Comm gate — module-reference set for THIS unit's touched modules.** Touched
   modules: `app/services/price_service.py`, `app/services/structured_comparison_service.py`.

   ```
   grep -rlE 'price_service|structured_comparison_service|extract_price_from_shopping|is_price_showable|build_retailer_url|_seed_shortcircuit_candidates|_park_listing_url_tier1_enabled|should_cache_price|public_price_view|_is_listing_url' tests --include=test_*.py
   ```
   **= 288 files** (measured; `price_service` alone 174, `structured_comparison_service`
   152, their union 285; `extract_price_from_shopping` 30, `is_price_showable` 31,
   `should_cache_price` 28, `build_retailer_url` 4, `_seed_shortcircuit_candidates` 3,
   `_is_listing_url` 2, `public_price_view` 1, `_park_listing_url_tier1_enabled` 1).
   **608** test files exist in total. Record the set in `.qa-w4/comm-set-W4-2.txt`; run
   the base BEFORE the edit (this worktree IS `b63a8368`) and the head after green WITH
   the unit's own file appended (289), same shape as `sc-w4-1`'s:
   `-m "not (live_unit or live_db or integration)" --timeout=120 -q -p no:cacheprovider`
   plus `--deselect` for every id in `tests/.pre_impl_failures.txt` (**89 lines**), split
   in two halves. `comm -13 <(sort base) <(sort head)` must be empty.
   **No SmartCompareApp scanner is required:** the client contract is touched only in
   the sense that a key is added and `url` may be absent, and
   `grep -rn "price\.url\|price?\.url\|discovery_url" SmartCompareApp/` returns **0
   hits** (measured) — `ProductPrice.url` is already optional (`types.ts:64`). Record
   that grep's zero output as the client evidence instead.
3. **Byte-identity gate — REQUIRED** (`app/services/price_service.py` is touched).
   ```
   python scripts/verify_flag_byte_identity.py --flags ENABLE_SHOPPING_DISCOVERY_URL_SPLIT \
     --proof-root C:/Users/SynAckITPC/Documents/AI/sc-w0-load/_proof \
     --out .qa-w4/gate_<base|head|base2>_W4-2.json > .qa-w4/gate_<…>.log 2>&1
   ```
   base → head → **base re-run**, comparing the `results` **arrays** record-by-record
   (`scripts/verify_flag_byte_identity.py:276-295`), **never** the OVERALL digest (it
   hashes the `--flags` list). Re-verify the corpus manifest first
   (`sc-w0-load/.qa-w0/proof_html_manifest.sha` = `380902fb…`, recipe in
   `GATE_RECIPE.md`); **never run `_proof/sweep2.py`**; the base re-run comes from a
   DETACHED checkout of `b63a8368` created by the agent under **its own scratchpad**
   (`git worktree add --detach <scratch>/w42-base b63a8368`, removed with `git worktree
   remove` afterwards) — never `git checkout` in this or any other worktree.
   **Honest discrimination:** the harness calls `extract_price_from_html` only
   (`:244/:268`), and `extract_price_from_html` (`:13166`) never calls
   `extract_price_from_shopping` (measured: 0 occurrences in `:13000-14000`). The
   harness is therefore **blind to this rung** — expect equality, observe equality, and
   say so. What it proves: the shared spine (`_is_listing_url`, `build_retailer_url`,
   `is_price_showable`) did not move, i.e. the must-NOT-touch list held. The rung's
   flag-OFF identity rests on red tests 2/4/5/7(OFF)/8(OFF)/9(OFF) + the 8 Preserve
   files (164 nodes) + the 30 `extract_price_from_shopping` files.
4. **Ruff + py_compile** on both edited modules and the new test file:
   `python -m ruff check --select E9,F63,F7,F82 --no-cache app/services/price_service.py
   app/services/structured_comparison_service.py tests/test_shopping_price_not_self_pending.py`
   and `python -m py_compile` on all three.
5. **Full free-tier suite before merge**, same marker/deselect shape as gate 2; failing
   only on ids already in `tests/.pre_impl_failures.txt` / the recorded comm base.
6. **Fable review before commit. Agents never commit.** The CLAUDE.md flag row is a
   merge-time item, not the agent's.

---

## 6. Mutation checks (REQUIRED — record each in `.qa-w4/W4-2-MUTATIONS.txt`)

Byte-snapshot before each mutation; restore from the snapshot and sha256-verify;
**never `git checkout --`** a file carrying uncommitted unit work.

| mutation | tests that MUST redden |
|---|---|
| revert `:9845` to `item.get("link") or build_retailer_url(...)` | 1, 3 |
| drop rung 1 (a listing `link` stays in `url`) | 1 (3 stays green) |
| drop rung 2 (the synthesized fallback stays in `url`) | 3 (1 stays green) |
| drop rung 3 / make the helper always return `(None, link)` | 5 |
| stamp `discovery_url` unconditionally (even when `None`) | 4 |
| put the link in BOTH `url` and `discovery_url` | 1 (`url is None`) |
| force `shopping_discovery_url_split_enabled()` to `True` | 2, 5(OFF half), 7(OFF half), 8(OFF half), 9(OFF half) |
| read the env into a module constant at import | 10 |
| remove the **stash** mirror only | 7 reddens while 1 and 3 stay green (the asymmetry proves the mirror is load-bearing) |
| remove the discovery fallback from the park predicate (`:6652`) | 8 |
| remove the backfill guard (`:7661`) | 9 |
| make `_discovery_url_of` ignore the flag (always read the key) | 8(OFF half), 9(OFF half) |
| loosen `should_cache_price` to allow a url-less row | 12 |

Test 6's first half and test 11 have no mutation target inside this unit (they pin
predicates the unit does not own); say so in the report rather than inventing one.

---

## 7. Honest limits

1. **This unit buys DISPLAY, nothing else.** A discovery-only row is still dropped by
   `select_best(require_url=True)` (measured `False → False`), still refused by
   `should_cache_price` (measured `False → False`), still excluded from the
   `usable_exact_genuine` KPI (`eval_runner.py:532-540` clause (d) requires a present
   non-listing url), and still fails `_budget_house_trusted_price` (`:4626`). The
   finding's "single largest lever on the shown-price rate" is exactly that — a
   shown-price lever, not a genuine-share lever. **Expect `usable_exact_genuine` to be
   unchanged and the pend rate to fall; publish both.**
2. **`_is_listing_url`'s blind spot is NOT fixed.** 9 of 46 search templates are not
   classified as listing urls (§1.4 list). Rung 2 stops *synthesized* ones entering
   `url`, but a real Serper `link` of the same shape (an item whose link genuinely is
   `amazon.com/s?k=…`) passes rung 1 untouched and still ships in `url`. Widening
   `source_router.is_non_pdp_listing_url` changes what every consumer pends and is its
   own row — follow-up `PO-RECORDED-MEASURED-03b`.
3. **The cache numbers are the review's.** 1,032 of 1,484 `local_bhd` rows pended, 857
   google-linked — not re-measured (no offline DB access here). Pre-existing rows are
   not migrated by this unit; the 7 d genuine TTL rolls them, and
   `ENABLE_FLUSH_LIVE_PRICE_KEY` (`#55`) covers a specific key.
4. **`build_retailer_url("amazon.ae", …)` returns the amazon.COM template** (measured):
   the loop at `:9404-9406` does `if key in source_lower`, and `"amazon"` is inserted
   before `"amazon.ae"`. A wrong-country search url. Out of scope; record as a
   follow-up on `RETAILER_SEARCH_URLS`.
5. **The only url the current client opens is not this one.** `rating_service.py:198`
   and `:239` build `rating_source.url` with the identical
   `best.get("link") or build_retailer_url(...)` expression, and
   `ResultsScreen.tsx:533-535` does `Linking.openURL(source.url)` on it — i.e. a user
   tapping the rating source can still land on a Google search page
   (`docs/CONTEXT_SESSION_LOG.md:1706` describes this exact symptom). **Not touched by
   this unit** (different producer, different surface, and it would change what the
   shipped pre-OTA client opens). Follow-up row.
6. **`discovery_url` is on the wire with the exact gate ON.** Measured
   `public_price_view` (gate ON) keeps it: `['amount','discovery_url','url']`. That is
   not a new disclosure — the same link ships in `url` today — and no client code reads
   either key (0 grep hits). The `_`-prefixed alternative is the §8 ruling 7.
7. **Flag ON + `ENABLE_EXACT_PRICE_GATE=false`:** the backstop never ran, so there was
   nothing to un-pend; the split then only removes information (and `public_price_view`
   returns the dict unchanged, `discovery_url` included). Pinned (test 11), not "fixed".
   The prod state is gate ON.
8. **No live Serper item was available.** Every item shape here is synthesized from the
   review's recorded rows and the registry's own `sample_url`s; the arithmetic and the
   predicates are real, the traffic mix is not.

---

## 8. Spec disagreements with the review

1. **Anchor drift (review anchors are at `76ace90`).**

   | review / brief | symbol | `76ace90` | `ed75dc70` | **HEAD `b63a8368`** |
   |---|---|---|---|---|
   | `price_service.py:9678` | the shopping `"url":` stamp | `:9678` ✓ | `:9820` | **`:9845`** |
   | "`build_retailer_url` (`:260-275`)" | **wrong symbol** — `:260` at `76ace90` is the `RETAILER_SEARCH_URLS` **dict**, not the function | dict `:260`, fn `:9227` | — | dict **`:380`**, fn **`:9394`** |
   | brief: "the `non_pdp_url` backstop (`:1851` region at `ed75dc70`-era numbering)" | the pend line | `:1745` | **`:1865`** (not 1851) | **`:1869`** |
   | — | `is_price_showable` | `:1661` | — | **`:1781`** |
   | — | `_is_listing_url` | `:8096` | — | **`:8263`** |
   | — | `should_cache_price` | `:8868` | — | **`:9035`** |
   | — | `public_price_view` | `:8951` | — | **`:9118`** |
   | — | `extract_price_from_shopping` | `:9514` | `:9656` | **`:9681`** |
   | — | the stash mirror's `"url":` | — | `~:8251` | **`:8276`** |

2. **The review's core mechanism reproduces exactly** (`False`,
   `guard_rejected='non_pdp_url'`) and so does its "an absent URL is NOT pended"
   premise. Nothing in the filed row is refuted.
3. **The second vote's "AND the no-link `build_retailer_url` fallback" is only 80 %
   true.** It pends for **37 of 46** templates and does **not** pend for 9 — those ship
   *showable and cacheable* as genuine `local_bhd` on a fabricated url (§1.4). The
   review therefore understates the defect in one direction while stating it in the
   other. This spec widens the rule to "a search link never enters `url`" for that
   reason. **RULING REQUESTED:** keep rung 2 (recommended — it removes a fabrication),
   or scope W4-2 to rung 1 only and file rung 2 as `PO-RECORDED-MEASURED-03c`.
4. **The review's fix text does not mention the Tier-1 park, and the park is DEFAULT
   ON.** Implementing (b) without §2.3(iii) silently converts a parked row into a
   genuine Tier-1 short-circuit that cancels the discovery prefetch, skips the whole
   Tier-1.5 adapter cascade and calls `_persist_genuine_price`. Measured predicate table
   in §1.5a. This is a spec **addition**, not in the review, and it is the single
   riskiest thing about the unit.
5. **Nor the parked-row url backfill** (`scs:7661-7663`), which would re-stamp a search
   url onto the very row the split cleaned. Also an addition (§1.5b, §2.3(iv)).
6. **Product decision (a) vs (b) is NOT made here.** The unit implements (b), as the
   brief directs; (a) remains the documented real answer with its cost (§2.5). Ahmed's
   call.
7. **Field-name ruling requested: `discovery_url` vs `_discovery_url`.** The brief's red
   test names `discovery_url`, and this spec follows it. Measured consequence:
   `public_price_view` (gate ON) **keeps** `discovery_url` on the wire and **strips**
   `_discovery_url`; with the gate OFF neither is stripped. No client code reads either
   (0 hits). Recommendation: keep `discovery_url` (it matches the finding, the content
   is already on the wire today under `url`, and a `_`-key would be invisible to the
   canary reader) — but it is a wire-shape change and deserves an explicit yes.
8. **`converted_usd` is still a misnomer for a native-BHD string on an unverifiable
   host** — W4-1's recorded product call (its Fable ruling 5). W4-2 inherits it
   unchanged and makes it *visible* for the first time, since these rows now display.
   That is the intended consequence of the hard order, and the PR must say so.
9. **Not making:** whether the KPI definition should count a discovery-only showable
   row (it does not today, `eval_runner.py:532-540`); whether
   `ENABLE_PARK_LISTING_URL_TIER1` should stay ON once these rows are showable (with
   W4-2 ON a parked row that reaches tier-7 now *displays*, so the park is strictly
   better than the short-circuit — but flipping that default is a separate decision);
   whether `rating_source.url` should get the same split (§7 limit 5).

---

## 9. Blast radius

**Changed surface:** the shopping-rung candidate dict gains an optional
`discovery_url` key and may carry `url is None`, in `extract_price_from_shopping`
(`price_service.py:9845`) and `_seed_shortcircuit_candidates`
(`structured_comparison_service.py:8276`); two cascade predicates in
`structured_comparison_service.py` learn to read it. **Flag OFF: no key, no behaviour
change, byte-identical.**

**Backend consumers of `price["url"]` (measured greps, all of `app/`):**
`grep -rn 'price\.get("url")\|price\["url"\]\|c\.get("url")\|cand\.get("url")' app/`
= **14 hits in 2 files**:

* `price_service.py:1867` (`is_price_showable` backstop — the one that stops pending),
  `:4626` (`_budget_house_trusted_price`), `:8281` (`_candidate_authority`), `:8353`
  and `:8387` (`select_best`), `:9072` (`should_cache_price`).
* `structured_comparison_service.py:6652` (**Tier-1 park — edited**), `:7393` (iHerb
  `link`, unrelated), `:7529`, `:7561` (supplement/iHerb stamps, unrelated),
  `:7619-7620` (Tier-2 GPT backfill — untouched, unreachable for this rung),
  `:7661-7663` (**parked-row backfill — edited**), `:7699-7700` (Tier-3 estimate
  backfill — untouched).

Plus `scripts/eval_runner.py:532` (KPI) and `app/services/product_data_service.py:294/345`
(L2 row read/write, unreachable behind `should_cache_price`).

**Test-reference counts** (`tests/ --include=test_*.py`): `price_service` **174**,
`structured_comparison_service` **152** (union **285**), `extract_price_from_shopping`
**30**, `is_price_showable` **31**, `should_cache_price` **28**, `build_retailer_url`
**4**, `_seed_shortcircuit_candidates` **3**, `_is_listing_url` **2**,
`public_price_view` **1**, `_park_listing_url_tier1_enabled` **1**. Comm-gate union
**288** (+1 for the unit's own file). Total test files **608**.

**Client impact: NONE, measured.**
* `grep -rn "price\.url\|price?\.url\|discovery_url" SmartCompareApp/` → **0 hits.**
* `ProductPrice.url` is already `url?: string` (`SmartCompareApp/src/types/types.ts:64`),
  so an absent url is already a valid shape for the pre-OTA client; an unknown extra key
  is ignored by `JSON.parse` and never read.
* The only product-surface `Linking.openURL` is `rating_source.url`
  (`ResultsScreen.tsx:533-535`), produced by `rating_service.py:198/239` — **not touched**.
* Net effect on the phones running the pre-OTA client: rows that today render the
  "pricing lands soon" pend card will render a **price with a retailer name and no
  tappable link** — which is exactly what they already render for every genuine price,
  because the client has never rendered a price link. Nothing new is asked of the
  client, and the backend stays safe for it.

**Ops/canary.** `[PRICE] parked %s fallback used for %s` (`scs:7675-7679`) and the
`[PRICE] Selected: …` line (`:9899`) are the existing canary anchors; add one line in
the splitter's callers — `[SHOPPING_DISCOVERY_URL] split url->discovery_url host=<host>
reason=<listing_url|synthesized> for <name>` — and read it alongside W4-1's
`[SHOPPING_CURRENCY_TRUTH] relabel …`. A rise in shown prices with **no** rise in
`usable_exact_genuine` is the expected, correct signature.

---

# FABLE REVIEW RULINGS (binding, 2026-09-23) — W4-2 `ENABLE_SHOPPING_DISCOVERY_URL_SPLIT`

Reviewer verdict SOUND_WITH_CHANGES (Opus 5.5 adversarial spec review, read-only, at `b63a8368`; W4-1's uncommitted diff snapshotted sha256 688d227d…). The mechanism and the RED reproduction stand. Everything below overrides the spec body where they conflict. Base for the red phase: **merged W4-1** (rebase this worktree onto `origin/main` after W4-1 lands; the two units edit the same candidate-dict literal at `price_service.py:~9841-9860` and the same `structured_comparison_service.py` import block).

## R1 (BLOCKING → design) — couple the two flags in code
`shopping_discovery_url_split_enabled()` returns True **only when `shopping_currency_truth_enabled()` is also True** (one conjunct, both per-call reads). Measured: split ON with TRUTH OFF is the only harmful state (search-link rows displayed as genuine `local_bhd` with no caption through the Tier-1 short-circuit, the listing-park + tier-7 path, or the broader-search rung), and nothing in the design prevented it; a W4-1 rollback while W4-2 is on re-created it. Pin: split=true, TRUTH unset ⇒ every observable is byte-identical to HEAD (url stamped exactly as today, no `_discovery_url`, no log line).

## R2 — the tier-7 backfill guard is the load-bearing edit; the Tier-1 park edit is DROPPED
Measured end-to-end: with W4-1 on, zero split rows reach the `elif _tier1_is_listing_url` branch (compose table, BHD and SAR; e2e `tier1_seed=false`), so edit (iii) is unreachable in the only order R1 now permits. Without the backfill guard (iv) the unit is a no-op for the Best Buy shape and ships + caches (86 400 s, L2 row) a fabricated `amazon.com/s?k=` url for the Amazon shape. **Build (iv); do not build (iii).** If a later unit changes the park flag's reachability it re-opens (iii) then.

## R3 — tests 8 and 9 must drive the real `_get_price`
As specified they re-implement the call-site expressions in the test body and stay green with the edit deleted (measured). Rewrite both on the existing harness (`tests/test_converted_price_before_estimate_t1.py` / `tests/test_converted_tier1_parks_for_bh.py` pattern: `search_product_prices` mocked, network blocked), asserting the returned `url` / `_discovery_url`, the `_seed_shortcircuit_candidates(kind='tier1_shopping')` call and the `_cache_set_async` / `_save_price_to_db` writes. Delete the OFF halves of tests 8/9 (they pin a dict shape production never produces). `_discovery_url_of` reads the key unconditionally — no flag read inside the helper (the flag read there only adds a mid-request rollback race).

## R4 — the key is `_discovery_url` (private), not `discovery_url`
Measured: `public_price_view` strips `_discovery_url` under the gate and keeps `discovery_url`; no client (97b5f15 or HEAD) reads either; the spec's canary is a log line, not the wire; a public key is a new wire contract that also persists into comparison-history rows. With the gate off both names leak — that is the existing rollback shape, stated in the PR body.

## R5 — the client-impact section (§9) is WRONG and must be corrected; the flip has a product precondition
Under R1's order every row W4-2 un-pends is `converted_usd`, and the phones' 97b5f15 bundle (and HEAD) renders it as "BHD x (converted from USD)" / "(محول من الدولار)" with the 'Local listing' pill (`ResultsScreen.tsx:392-400` at 97b5f15; `ResultsContent.tsx:147`, `ResultsScreen.tsx:446` at HEAD). W4-2 is what makes W4-1's ruling-5 misnomer visible. **The `ENABLE_SHOPPING_DISCOVERY_URL_SPLIT` flip is gated on Ahmed's explicit product call with that rendering in front of him** (options a/b/c as recorded in W4-1). The unit ships; the flag stays dark until the call.

## R6 — the PR body must disclose, measured
(a) The un-cache cost: rows from the 9 non-listing-template retailers (amazon, amazon.ae, amazon.sa, target, newegg, adorama, apple, ebay, aliexpress) lose their 24 h converted / 7 d local cache, so each request re-runs Serper + the Tier-1.5 cascade while the key is unfunded or spend-gated; accepted (a fabricated url must not be cached) and stated, with the KPI note that `usable_exact_genuine` can drop with W4-1 off. (b) `amazon.ae` AND `amazon.sa` collide to `amazon.com` (substring insertion order in `RETAILER_SEARCH_URLS`) — a stated limit + follow-up `PO-RECORDED-MEASURED-03b`. (c) Real Serper links of the `google.com/shopping/product/<id>` shape are not caught by `_is_listing_url` — follow-up `03c`. (d) The broader-search rung (`extract_price_from_shopping(broader_name, …)` → `_persist_genuine_price` → return) and the race-miss `_parked_price` return at `scs:~5729` are consumers of the split row; list them. (e) The `[SHOPPING_DISCOVERY_URL]` line logs once for `best`, not per candidate. (f) Comparison-history rows carry `_discovery_url` only with the gate off. (g) `ENABLE_PARK_LISTING_URL_TIER1` is left unchanged (its elif is unreachable for shopping-rung output once W4-1 is on).

## R7 — test list corrections
Test 6's live half becomes UNCONDITIONAL (no `skipif`) once the worktree is rebased onto merged W4-1. Test 12 is parametrised explicitly on `ENABLE_EXACT_PRICE_GATE` ON only, and the spec's rollback section records the measured gate-off consequence (url-less row L1-cached with `_discovery_url` inside, L2 url NULL). Test 11 stays as a Preserve pin, labelled as such. Byte-identity gate 3's honest scope sentence is copied from W4-1 (the harness never enters the shopping rung).

## R8 — KPI and follow-ups
KPI clause (d) keeps requiring a PDP url; publish the pend-rate fall separately. `rating_source.url` is a separate follow-up (the only link the pre-OTA client opens). Merge order: W4-1 first.
