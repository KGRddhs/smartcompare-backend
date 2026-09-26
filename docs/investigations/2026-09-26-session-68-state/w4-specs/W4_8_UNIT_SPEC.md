# W4-8 — category truth: pharmacy "tablets" are not electronics, and the Arabic blocklist mirrors `9f6e498`

Findings `PO-CATEGORIES-I18N-01` (P1) and `PO-CATEGORIES-I18N-03` (P2 after the second vote), plus the
`PO-CATEGORIES-I18N-09` Arabic audit the row folds in ("audit rifle, silencer, tactical knife in the
same pass"). Two halves, shipped differently on purpose:

* **Half A — classifier (code, FLAGGED):** `ENABLE_CATEGORY_TOKEN_FIX`, default OFF, read PER CALL.
* **Half B — blocklist (DATA, UNFLAGGED):** `app/data/content_blocklist.json`, a change measured to
  STRICTLY NARROW the fail-closed L1/L2 block (0 newly blocked strings over 413 measured, §1e).

Base **`61585c58`** (`61585c581e9deb78213f030260a765080f2e1dff` = origin/main, confirmed with
`git rev-parse HEAD` in `sc-w4-specs`). The review's anchors are from `76ace90` and have drifted; every
anchor below is re-located BY SYMBOL at `61585c58` (table in §15). The touched code is byte-identical to
`76ace90` in the ranges that matter (measured: `_CATEGORY_SYNONYMS` → end of
`classify_category_from_text`, `_resolve_pair_category`, `is_supplement_query`,
`content_safety_service.py` and `content_blocklist.json` all diff-empty `76ace90..61585c58`), so no later
merge changed any red claim. **Every number in this spec was MEASURED in this run** through pytest under
the `qaren_netguard` plugin, `[netguard] blocked 0 network attempt(s)` on every probe run.

## 0. How to re-run every number

Probes (scratch, never committed) in `.qa-s68/specs/W4_8_probes/`:
`test_probe_w48.py` (classifier + resolver + price-branch expression over the corpus and the tablet sets,
the prototype classifier and its 5 mutations, the 4 prototype blocklists, the EN single-word audit, the
L2 title scan), `test_probe_w48_sources.py` (category-gated price sources + sync/stream write-back
capture, HEAD vs prototype), `probe_inputs.json` (every probe string + the 4 prototype blocklist
patches), `corpus_gcc_360.json` (the lane corpus, §1d), `golden_head_61585c58.json` (the HEAD records
the flag-OFF gate compares against). Run from the worktree root, conftest loaded as a plugin so
credentials are neutralised before any `app.*` import:

```
SPW=<scratchpad>; PD=<worktree>/.qa-s68/specs/W4_8_probes; cd <worktree>
W48_OUT=$SPW/w48_out.json W48_OUT2=$SPW/w48_out2.json PYTHONIOENCODING=utf-8 \
PYTHONPATH="$SPW/netguard;$PD" <venv python> -m pytest -p qaren_netguard -p tests.conftest \
  -p no:cacheprovider -p no:randomly -c pyproject.toml --rootdir=. --timeout=300 \
  -m "not (live_unit or live_db or integration)" $PD/test_probe_w48.py $PD/test_probe_w48_sources.py -q
```

**Record shape** (the flag-OFF equality gate hashes exactly this; reproduce it verbatim): per query
`q`, split on the first of `" vs ", " VS ", " or ", " OR ", " ضد ", " أو ", " او ", " مقابل "`;
each half → `sanitize_prompt_input(half, max_length=80)` → a product dict
`{"brand":"","name":s,"variant":None,"category":classify_category_from_text(s),"search_query":s,"_explicit":True}`
(exactly the explicit_pair branch, `structured_comparison_service.py:3716-3731`); the record is
`{"det": classify(" ".join(halves)), "halves": [...per-half categories...],
"chip": [used, switched, orig] from await _resolve_pair_category(products, <truth chip>, parser_path=False),
"chip_is_supp": [...], "nochip": [...same with selected_category=None...], "nochip_is_supp": [...]}`
where `*_is_supp[i] = (used == "supplements") or (used in ("other", None) and is_supplement_query(search_query_i))`
(the `_get_price` expression, `scs:6234-6237`) and `classify_category_llm` is monkeypatched to an async
stub returning `"other"` (no network; what A2b degrades to on failure). Key = `"C:<truth>:<idx:02d>"`.
Hash = sha256 of `json.dumps(records, ensure_ascii=False, sort_keys=True, separators=(",", ":"))` UTF-8.

## 1. The defect, measured

### 1a. The classifier (`extraction_service.classify_category_from_text`, `:1167`)

`is_supplement_query(text)` runs first (`:1182-1184`), then a longest-first `\b`-sweep over
`_CATEGORY_SYNONYMS` (`:1187-1189`), which maps `"tablet"` (`:1107`) and `"tablets"` (`:1108`) to
`"electronics"`. `is_supplement_query` counts `tablet(s)` only as a FORM token corroborating an
AMBIGUOUS nutrient (`price_service.py:643`, `:1319-1333`), so a pharmacy name with no nutrient token
falls through to the sweep.

| input (real function, `61585c58`) | measured |
|---|---|
| `classify_category_from_text('Panadol Extra 24 tablets vs Adol 500 tablets')` | **`electronics`** — red claim 1 **HOLDS** |
| `classify_category_from_text('Panadol Extra 24 tablets')` / `('Adol 500 tablets')` | `electronics` / `electronics` |
| `is_supplement_query(pair)` / `(half a)` | `False` / `False` |
| `classify_category_from_text('Samsung Galaxy Tab S10 tablet 256GB')` | `electronics` — the second node **HOLDS as a PIN** (green today, must stay) |
| `is_high_value_query('Samsung Galaxy Tab S10 tablet 256GB')` | `True` |
| `canonicalize_category('tablet')` / `('Tablets')` | `electronics` / `electronics` (shares `_CATEGORY_SYNONYMS`, `:1157-1158`) |

Tablet probe set (`probe_inputs.json`, authored for this spec — the lane corpus has only ONE `tablets`
row): **17 of 18 pharmacy-sense rows classify `electronics`** at HEAD (the 18th, `Vitamin C 1000mg
effervescent tablets vs Redoxon`, is `supplements` via `is_supplement_query`), including
`Finish Quantum dishwasher tablets vs Fairy Platinum tablets` and `Chlorine tablets for pool vs HTH
granules` (a third, household sense). **All 17 device-sense rows classify `electronics`** at HEAD.

### 1b. The pair resolver (`scs._resolve_pair_category`, `:440`; explicit/vision branch `:493-503`)

On `explicit_pair` / vision (`parser_path=False`) NAME detection outranks the chip (`:493-496`). For the
pharmacy pair (products built as §0):

| chip | measured `(category_used, category_switched, original_category)` |
|---|---|
| `supplements` | **`('electronics', True, 'supplements')`** — the correct chip is overridden |
| none | `('electronics', False, None)` — A2b never called |

All 17 electronics-classified pharmacy rows give exactly this with a Supplements chip.

### 1c. Worse than filed — the category gates the PRICE path (`scs:6234-6237` at `61585c58`; `:5671-5677` at `76ace90`)

End-to-end capture (the `tests/test_explicit_pair_category.py` harness: `_fetch_product_data` patched to
record `product_info["category"]` and raise), `compare_from_text(query=..., explicit_pair=(...), selected_category=chip)`:

| path | chip `supplements` | no chip |
|---|---|---|
| sync (`compare_from_text`) | **`['electronics','electronics']`** | `['electronics','electronics']` |
| stream (`compare_from_text_streaming`) | **`['electronics','electronics']`** | `['electronics','electronics']` |

`_fetch_product_data` canonicalises that value (`:5107`) and hands it to `_get_price` (`:5180`), which
publishes it as the per-task resolved price category (`set_resolved_price_category`, `:6001`) and
computes `is_supplement = (category == "supplements") or (category in ("other", None) and is_supplement_query(full_name))`
(`:6234-6237`). What each category selects, measured through the real selectors:

| category | `is_supplement` (both Panadol/Adol names) | `get_sitemap_sources_for_category` | `get_jsonapi_sources_for_category` | shopify / algolia sources |
|---|---|---|---|---|
| `electronics` (today) | `False` | `[]` | `[]` | 2 / 1 (electronics stores, wasted) |
| `supplements` | `True` → iHerb → pharmacy JSON-LD branch (`:6805`) | **`['bolo.bh']`** | **`['nasserpharmacy.com']`** | 0 / 0 |
| `other` | `False` (no supplement token in the names) | `[]` | `[]` | 0 / 0 |

So "electronics" kills the iHerb/pharmacy tier AND the two Bahrain pharmacy adapters (bolo, nasser)
for every such pair, and sends the pair to two Shopify + one Algolia electronics store instead — on top
of the electronics spec schema, dimensions and `CATEGORY_FAIRNESS` the finding named. **HOLDS.**

### 1d. The lane's 360-query GCC corpus — LOCATED, not in the review-state folder

It is NOT under `docs/investigations/2026-09-06-full-review-state/` (searched: `STATE_SUMMARY.md`,
`report-/critic-m22-product-output.md`, `partial-m22-product-output.json`, all four journals; the
journals only cite `scratchpad/lane/corpus.py, run_gate.py, run_resolve.py`). It IS on disk in the
2026-09-05 review session's volatile scratchpad:
`C:/Users/SynAckITPC/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/f110259b-2c46-4d36-b8fd-39f57a9eb840/scratchpad/lane/corpus.py`
(sha256 `157b94f6fe0ebaaa7cfffdd80fbddb4889fe9ea1d112402e23b54ecbc4e14eae`, 9 categories × 40 = 360,
`CORPUS = {category: [queries]}`), with `run_gate.py` and `gate_report.txt`; `run_resolve.py` is gone.
Because `%TEMP%` is volatile, this spec **freezes it** as `W4_8_probes/corpus_gcc_360.json`
(sha256 `0852f55687e05156c35b4104e55eeb6bf729a3bc8443ff43a4eebe08d5d3ae91`; rows
`{truth, idx, query}` in the source order; the ordered query list hashes to
`9352717a49b17506190ffb166befaec50c763251164369db1f44a779ea88c77e`). The red phase commits that file
verbatim as `tests/fixtures/category_corpus_gcc_360.json` (§9). If the file were ever lost, regenerate
it by `runpy.run_path(corpus.py)["CORPUS"]` → the same row list → re-check both hashes; there is no
other deterministic source.

Re-measured at `61585c58` over the corpus (reproduces the lane's `gate_report.txt` exactly):

| measure | lane (2026-09-06) | `61585c58` |
|---|---|---|
| L1-blocked | 3 | **3** (`Bosch exhaust silencer…` → `silencer`, `Tactical knife Gerber…` → `tactical knife`, `Shotgun shells 12 gauge…` → `shotgun shells`) |
| classifier correct / `other` / wrong | 74 / 279 / 7 | **74 / 279 / 7** |
| correct chip overridden | 7 | **7** |
| Arabic-script queries classified | 0 of 58 | **0 of 58** |
| rows containing `tablet`/`tablets` | — | **1** (`Ferrous sulfate 65mg tablets vs Ferrofol capsules` → `electronics`); the corpus's own Panadol row is `…24 tabs vs Adol 500 24 tabs` (`tabs`, no synonym hit) |

Corpus classification-record hash at HEAD (record shape §0): **`b76fcef9a855248d72d1b7b68c14b9bf77255b51f90edbe3bfdc197c3872ec1d`**.
Corpus L1-verdict hash at HEAD (`[allowed, reason, blocklist_match]` per key):
`3885d2701484167362f2241faa3b50b965b04c1771d149946764ae26d0238a07`.

### 1e. The blocklist (`content_blocklist.json`, loaded ONCE per `ContentSafetyService()` at `content_safety_service.py:54-72`)

One alternation per category, `(?:^|[\s\W])(term|…)(?=$|[\s\W])`, `IGNORECASE|UNICODE`, over the
lowercased raw query. It serves three layers: **L1** `check_query_intent` on the joined `"A vs B"` string
(`scs:3682` sync, `:4281` stream → terminal `CONTENT_UNAVAILABLE` "We don't compare this category"),
**L2** `is_text_safe` (22 call sites across `app/`, on price surfaces, e.g. `price_service.py:14894/15530/16200/16427`,
`scs:1904/2022/2116`) and `filter_shopping_items` (`price_service.py:10228`). Red claim 2:

| query | `61585c58` |
|---|---|
| `check_query_intent('عطر أفيون ايف سان لوران')` (bare hamza) | **`allowed=False, reason='illegal_drugs', match='أفيون'`** — red claim 2 **HOLDS** |
| `'بلاك أفيون ايف سان لوران ضد لانكوم لا في است بيل'` / `'أفيون ايف سان لوران ضد بلاك أفيون'` / `'بلاك أفيون'` | blocked, `أفيون` |
| `'عطر افيون …'` (no hamza) / `'عطر الأفيون …'` / `'بلاك اوبيوم ايف سان لوران'` | allowed (the second vote's reachability point HOLDS) |
| `'YSL Black Opium vs Lancome La Vie Est Belle'` | allowed |

The Arabic audit the row asks for (`بندقية` rifle, `كاتم صوت` silencer, `سكين قتالي` tactical knife),
plus the EN twins, measured at HEAD — every one of these is a **legitimate** shopping query that is
**BLOCKED today**: `Bosch exhaust silencer vs Walker silencer`, `Toyota Hilux silencer vs Land Cruiser
silencer`, `Honda generator silencer box` (`silencer`); `Tactical knife Gerber vs Victorinox Swiss knife`,
`Gerber tactical knife vs Leatherman Wave` (`tactical knife`); `كاتم صوت عادم السيارة بوش ضد ووكر`
(car exhaust), `كاتم صوت مولد هوندا` (generator) (`كاتم صوت`); `سكين قتالي جربر ضد فيكتورينوكس`
(`سكين قتالي`); `بندقية ماء للأطفال` (water gun), `بندقية نيرف ضد بندقية ماء` (Nerf), `بندقية هواء ضغط`
(air rifle) (`بندقية`). Structural asymmetry: `weapons.en` has NO bare `rifle` (only `assault rifle`,
`:15`), while `weapons.ar` has bare `بندقية` (`:23`) next to its `assault rifle` twin `بندقية هجومية` (`:28`).

**Found in the same pass, NOT in the row (§14 Q3):** the bare `مسدس` (handgun, `:22`) blocks five
ordinary Arabic product names at HEAD — `مسدس مساج ثيراجن ضد هايبرايس` (massage gun), `مسدس غراء حراري`
(hot-glue gun), `مسدس سيليكون` (caulk gun), `مسدس ماء` (water pistol), `مسدس حراري بوش` (heat gun) — while
the EN twin `Theragun massage gun vs Hypervolt` is allowed. `tests/test_content_safety_service.py:133-134,
:190-192, :652` pin `مسدس` as blocking.

L2 surface: over all 521 cached `_proof` pages (`_proof/html` 92 + `_proof/global/html` 429), the
`<title>`+`og:title` surface is `is_text_safe` on **521/521** at HEAD and under every prototype
blocklist below (0 differences) — the extraction corpus cannot see this half at all.

## 2. What already exists — reuse it, do not reinvent it

* **The ambiguous-token pattern** — `is_supplement_query` (`price_service.py:1295`) already splits its
  tokens into UNAMBIGUOUS and AMBIGUOUS-needing-corroboration (`:600-652`). The device corroborator below
  is that pattern applied to `tablet(s)`.
* **Whole-token matcher** — `price_service._contains_token` (`:1227`, lookaround boundary; a multi-word
  token matches as a phrase). Use it for the corroborator vocabulary.
* **Device vocabulary, already curated** — `HIGH_VALUE_DEVICE_TOKENS` (`:484`), `HIGH_VALUE_BRANDS`
  (`:489`), `_ELECTRONICS_BRAND_KEYWORDS` (`:1682`), `_ELECTRONICS_DEVICE_NOUNS` (`:1689`, minus its own
  `"tablet"`). Read them through the SAME function-local import `classify_category_from_text` already
  uses (`:1180-1182`, the circular-import guard) — never copy them.
* **Flag idiom** — `specs_no_fabrication_enabled()` (`extraction_service.py:535`, body `:584-586`):
  `os.getenv(NAME, "false").strip().lower() in ("true", "1", "yes", "on")`, read per call.
* **End-to-end capture harness** — `tests/test_explicit_pair_category.py:23-44` (sync) and `:127-157`
  (stream): patch `_fetch_product_data`, record `product_info["category"]`, raise.
* **Blocklist regression file + audit** — `tests/test_content_blocklist_opium_legitimate_products.py`
  (the five EN tests of `9f6e498`), `scripts/audit_blocklist_collisions.py` + its standing guard
  `tests/test_blocklist_collision_audit.py` (EN single-word entries vs 374 legitimate names; measured
  13 singles / 0 collisions at HEAD, 12 / 0 after the edit).
* **Fresh-service trick for data tests** — `ContentSafetyService.__init__` reads the MODULE GLOBAL
  `_BLOCKLIST_PATH` at call time (`:22`, `:60`), and `get_content_safety_service()` memoises `_service`
  (`:180-188`); the existing files reset it with `monkeypatch.setattr(css, "_service", None)`.

## 3. The design

### 3a. Half A — `ENABLE_CATEGORY_TOKEN_FIX` (default OFF, read per call)

Reader, in `extraction_service.py` next to `specs_no_fabrication_enabled`:
`category_token_fix_enabled() -> bool` = `os.getenv("ENABLE_CATEGORY_TOKEN_FIX", "false").strip().lower() in ("true", "1", "yes", "on")`.

**Effect ON — exactly one site, the sweep in `classify_category_from_text` (`:1187-1189`):** a hit on a
token in `_AMBIGUOUS_ELECTRONICS_TOKENS = frozenset({"tablet", "tablets"})` counts only when
`_tablet_device_corroborated(low)` is True; otherwise the sweep `continue`s to the next (shorter) token
and, if nothing else hits, returns `"other"`. Nothing else in the function moves: the
`is_supplement_query` precedence, the longest-first order, the `\b` regex, every other token.

`_tablet_device_corroborated(low: str) -> bool` (module-private, `low` is the already-lowercased text),
in this ORDER (each rung is pinned by a mutation, §6):
1. **hard device spec → True:** `_DEVICE_SPEC_RE` =
   `(?<![a-z0-9])\d+(?:\.\d+)?\s*(?:gb|tb)(?![a-z])` | `(?<![a-z0-9])(?:wi-?fi|cellular|lte|[45]g)(?![a-z0-9])`
   | `(?<![a-z0-9])\d+(?:\.\d+)?\s*(?:inch|inches|")` | `(?<![a-z0-9])(?:android|kids|graphics|drawing|pen|gaming|windows)\s+tablets?(?![a-z0-9])`;
2. **pharmacy veto → False:** `_PHARMA_SIGNAL_RE` = a dose `(?<![a-z0-9])\d+(?:[.,]\d+)?\s*(?:mg|mcg|iu)(?![a-z])`
   | a PLURAL count `(?<![a-z0-9.])\d+\s*(?:tablets|tabs)(?![a-z0-9])` (plural only — the singular form
   let `Fire HD 10 tablet`, `Pad 6 tablet`, `Surface Pro 11 tablet` veto themselves in the first
   prototype; measured, then narrowed);
3. **device vocabulary → True/False:** any `_contains_token(low, t)` for `t` in
   `_ELECTRONICS_BRAND_KEYWORDS | HIGH_VALUE_BRANDS | HIGH_VALUE_DEVICE_TOKENS | (_ELECTRONICS_DEVICE_NOUNS - {"tablet"})`.

Measured with this exact prototype (defined in the probe, never in app code):

| set | HEAD | prototype ON |
|---|---|---|
| 18 pharmacy-sense rows | 17 `electronics`, 1 `supplements` | **17 `other`**, 1 `supplements` |
| 17 device-sense rows (full string) | 17 `electronics` | **16 `electronics`**, bare `tablet` → `other` |
| device halves | — | `Amazon Fire HD 10 tablet` → `other` (its pair still `electronics` via `Lenovo`) |
| 360-query corpus | hash `b76fcef9…` | hash `5421996c770dfd0005c30446549b3fc412e3b5e042949d57e25d13b0ed37e390`; **exactly 1 of 360 records differs** — `C:supplements:05` `Ferrous sulfate 65mg tablets vs Ferrofol capsules`: det `electronics`→`other`, chip `('electronics', True, 'supplements')`→`('supplements', False, None)`, `chip_is_supp` `[False, False]`→`[True, True]` |
| pharmacy pair, resolver, chip `supplements` | `('electronics', True, 'supplements')` | **`('supplements', False, None)`** |
| pharmacy pair, resolver, no chip | `('electronics', False, None)`, A2b not called | `('other', False, None)` via A2b (stub) — **A2b is now called** |
| capture sync / stream, chip `supplements` | `electronics ×2` / `electronics ×2` | **`supplements ×2` / `supplements ×2`** |
| capture sync / stream, no chip | `electronics ×2` / `electronics ×2` | `other ×2` / `other ×2` (A2b stubbed) |

**Why OFF is byte-identical:** the new branch is `if token in _AMBIGUOUS_ELECTRONICS_TOKENS and category_token_fix_enabled() and not _tablet_device_corroborated(low): continue`
— with the flag OFF the only added work on a `tablet(s)` hit is one `os.getenv`; the return value is
the HEAD return value on every input (gate §9.1 proves it over the 360 corpus + 35 tablet rows + the
existing pins). The helper and the two regexes are module-level constants/functions that no OFF path
calls. `_CATEGORY_SYNONYMS` is NOT edited — `canonicalize_category` shares it (`:1157`) and
`tests/test_category_canonicalization.py:68` pins `("tablet", "electronics")` there; the LLM parser's
free-form `"Tablets"` category is a full-context judgment and must keep canonicalising to electronics.

**Every consumer, ON (all read the one function; none is edited):** `_resolve_pair_category`'s
`name_cat` (`scs:467`); the per-product stub on vision (`:3709`) and explicit_pair (`:3726`) and their
stream twins (`:4311`, `:4327`); the partial-build seed (`:3654`). The parser path (`q=`) is unaffected:
`det = llm_cat` there (`:476`), `name_cat` is computed and unused.

**Client (phones on OTA group `561d2cba` from `ab9442ae`; `SmartCompareApp/src` is diff-empty
`ab9442ae..61585c58`):** they send `product_a`/`product_b` + optional `selected_category` on REST
(`api.ts:611-616`) and SSE (`:760`). No request or response key changes. Values change: `metadata.
category_used` (`electronics` → `supplements`/`other`) and `category_switched` (`True` → `False` for a
pharmacy pair with a Supplements chip); the client types both (`types.ts:295-296`) and renders neither
(the banner was deleted, `PO-CATEGORIES-I18N-05`). The dimension set, spec table and price sources the
phone renders follow the category — that is the fix.

### 3b. Half B — the blocklist data edit (UNFLAGGED, strictly narrowing — measured)

Recommended edit = prototype **`A_strict`** (patch in `probe_inputs.json`, `protos.A_strict`):

| list | remove | add |
|---|---|---|
| `weapons.en` | `silencer`, `tactical knife` | `gun silencer`, `pistol silencer`, `rifle silencer`, `firearm silencer` |
| `weapons.ar` | `بندقية`, `كاتم صوت`, `سكين قتالي` | `كاتم صوت مسدس`, `كاتم صوت بندقية`, `كاتم صوت سلاح` |
| `illegal_drugs.ar` | `أفيون` | `صبغة أفيون`, `خشخاش أفيون`, `أفيون خام`, `وكر أفيون` |

`بندقية هجومية` (`assault rifle` twin), `مسدس`, `ذخيرة`, `switchblade`, `shotgun shells` and every other
entry stay. Bump `updated_at` only (the file's own note: `version` changes only on a shape change;
nothing reads either field). Keep the file's JSON shape, key order and 2-space indent; append each new
term at the end of its list (the prototype did exactly this).

Why each add mirrors `9f6e498`: the EN opium fix replaced a bare token with `opium tincture`,
`opium poppy`, `raw opium`, `opium den`; `A_strict` gives each its Arabic twin **built on the bare hamza
token** so every new entry is a string the bare `أفيون` already blocked (strict narrowing). The
natural-Arabic definite forms (`صبغة الأفيون`, `خشخاش الأفيون`, `وكر الأفيون`) were NOT blocked at HEAD
(`الأفيون` never matched the bare entry), so adding them WIDENS the block — variant `A` (§14 Q1).

Measured over **413 strings** (360 corpus + 27 legit probes + 26 intent probes), HEAD vs prototype:

| variant | newly BLOCKED (widening) | newly ALLOWED (narrowing) | EN single-word audit (singles / collisions) |
|---|---|---|---|
| **`A_strict` (recommended)** | **0** | 20 | 12 / 0 |
| `A` (natural `ال` forms for tincture/poppy/den) | 3: `صبغة الأفيون للبيع`, `زراعة خشخاش الأفيون`, `وكر الأفيون` | 21 (also `خشخاش أفيون`) | 12 / 0 |
| `A2_suppressor` (= `A` + bare `suppressor`) | 5: the 3 above + `APC surge suppressor 8 outlet vs Belkin surge protector` + `Boss NS-2 noise suppressor pedal` | 20 | 13 / 0 |
| `AB` (= `A` + `مسدس` → `مسدس ناري`, `مسدس جلوك`, `مسدس حقيقي`) | 3 (as `A`) | 27 (+ the 5 `مسدس` tools, − `شراء مسدس` now ALLOWED) | 12 / 0 |

`A_strict`'s 20 narrowed strings: the 3 bare-hamza Arabic YSL Opium queries + `بلاك أفيون`; the 3 EN
`silencer` + 2 EN `tactical knife` + 2 AR `كاتم صوت` + 1 `سكين قتالي` + 3 `بندقية` (water/Nerf/air)
legitimate queries; corpus rows `C:other:06` (Bosch silencer) and `C:other:37` (Gerber tactical knife)
— **and three intent strings that lose their block**, each a deliberate EN-parity consequence:
`شراء أفيون` ("buy opium"; EN `buy opium` is ALLOWED at HEAD, measured), `بندقية صيد` ("hunting rifle";
EN has no bare `rifle`), and `silencer suppressor` — **an existing pin
(`tests/test_blocklist_collision_audit.py:91`) that reddens; §14 Q2**. Still blocked under `A_strict`,
measured: `gun/pistol/rifle silencer` (match = the new phrase), `switchblade knife import`,
`كاتم صوت مسدس`, `كاتم صوت بندقية`, `بندقية هجومية`, `صبغة أفيون`, `خشخاش أفيون`, `أفيون خام للتصدير`,
`وكر أفيون`, `شراء مسدس`, `مسدس جلوك 19`, `ذخيرة مسدس`, all four EN opium phrases, and corpus
`C:other:38` (`shotgun shells`). L2: 0 of 521 `_proof` titles change (§1e).

**Client:** no change; the phones receive `CONTENT_UNAVAILABLE` on fewer queries.

## 4. Files

**Touch:** `app/services/extraction_service.py` (reader, `_AMBIGUOUS_ELECTRONICS_TOKENS`, the two
regexes, `_tablet_device_corroborated`, one guarded `continue` in the sweep; docstring of
`classify_category_from_text` gains one paragraph); `app/data/content_blocklist.json` (§3b);
`tests/test_category_token_fix.py` (new), `tests/test_content_blocklist_arabic_parity.py` (new),
`tests/fixtures/category_corpus_gcc_360.json` (new, = `W4_8_probes/corpus_gcc_360.json` byte-for-byte),
`tests/fixtures/category_corpus_gcc_360_head_records.json` (new, the `corpus_classification_records` +
`l1_verdicts_head` of `W4_8_probes/golden_head_61585c58.json`, re-derived from HEAD by the red agent and
checked against the two hashes of §1d); CLAUDE.md flag row at merge (orchestrator).

**Must NOT touch:** `_CATEGORY_SYNONYMS`, `canonicalize_category`, `classify_category_llm`,
`is_supplement_query` and every `price_service` constant it or the corroborator reads,
`_resolve_pair_category`, `structured_comparison_service.py` (no edit at all), `content_safety_service.py`
(the matcher), `scripts/audit_blocklist_collisions.py`, the `9f6e498` file
`tests/test_content_blocklist_opium_legitimate_products.py` (kept byte-unchanged; its Arabic twins live
in the new file), `tests/.pre_impl_failures.txt`, any client file.

## 5. Red tests

RED = fails at `61585c58` for the stated reason. PIN = green at `61585c58` and must stay. Flag set with
`monkeypatch.setenv`/`delenv` per test; `classify_category_llm` always monkeypatched on
`app.services.structured_comparison_service` (no network); `css._service` reset for every blocklist test.

### `tests/test_category_token_fix.py`

1. **RED `test_flag_reader_default_off_and_truthy_forms`** — unset, `""`, `"false"`, `"0"`, `"no"` → False;
   `"true"`, `"TRUE"`, `" true "`, `"1"`, `"yes"`, `"on"` → True. RED: `category_token_fix_enabled` does not exist.
2. **RED `test_pharmacy_tablets_not_electronics_flag_on`** — parametrized over the 17 pharmacy rows of
   `probe_inputs.json` `tablet_pharmacy[0:17]`: `== "other"`. RED today: all `electronics`.
3. **PIN `test_pharmacy_tablets_flag_off_identity`** — same 17 rows, flag unset AND `"false"`: `== "electronics"`.
4. **PIN `test_device_tablets_stay_electronics`** — the 16 device rows `tablet_device[0:16]` incl.
   `Samsung Galaxy Tab S10 tablet 256GB` (red-claim node 2): `== "electronics"` with the flag OFF and ON.
   Green today on both (flag absent); this is the node that rules out the naive drop (§6 M1).
5. **RED `test_bare_tablet_is_uncorroborated_flag_on`** — `"tablet"` → `"other"` ON (today `electronics`);
   `"tablet vs laptop"` → `"electronics"` ON (via `laptop`).
6. **PIN `test_supplement_precedence_unchanged`** — `Centrum Multivitamin tablets` and
   `Vitamin C 1000mg effervescent tablets vs Redoxon` → `supplements`, both flag states.
7. **PIN `test_canonicalize_tablet_untouched`** — `canonicalize_category("tablet")`, `("Tablets")` →
   `electronics`, both flag states.
8. **RED `test_resolver_honours_supplements_chip_flag_on`** — explicit products for the pharmacy pair
   (built as §0), `_resolve_pair_category(products, "supplements", parser_path=False)` →
   `("supplements", False, None)`. RED today: `("electronics", True, "supplements")`. Flag OFF → today's
   tuple (pin half, same test file, separate test `..._flag_off`).
9. **RED `test_resolver_no_chip_escalates_to_a2b_flag_on`** — A2b stub returns `"supplements"` and
   counts: → `("supplements", False, None)`, stub called once. RED today: `("electronics", False, None)`, 0 calls.
10. **RED `test_explicit_pair_writes_back_supplements_sync`** and **`..._stream`** — the capture harness
    with chip `supplements`: captured `["supplements", "supplements"]`. RED today: `["electronics", "electronics"]`
    on both paths (measured).
11. **PIN `test_supplement_category_selects_pharmacy_sources`** — `get_sitemap_sources_for_category("supplements")`
    contains `bolo.bh`, `get_jsonapi_sources_for_category("supplements")` contains `nasserpharmacy.com`,
    both empty for `"electronics"`; with 10, this proves the price-tier half end-to-end without a network
    `_get_price` run.
12. **PIN `test_flag_off_corpus_equality`** — load `tests/fixtures/category_corpus_gcc_360.json`, build the
    §0 records flag OFF, assert `== category_corpus_gcc_360_head_records.json["corpus_classification_records"]`
    AND the canonical hash `== b76fcef9a855248d72d1b7b68c14b9bf77255b51f90edbe3bfdc197c3872ec1d`.
13. **RED `test_flag_on_corpus_delta_is_exactly_one_row`** — flag ON: the records differ from the golden on
    exactly `{"C:supplements:05"}`, and that record equals the §3a ON record; the whole-corpus hash
    `== 5421996c770dfd0005c30446549b3fc412e3b5e042949d57e25d13b0ed37e390`. RED today (flag absent → 0 rows differ).
14. **RED `test_flag_read_per_call`** — one process: flag ON → pair `other`; `delenv` → `electronics`;
    ON again → `other` (catches an import-time read).

### `tests/test_content_blocklist_arabic_parity.py`

15. **RED `test_arabic_opium_brand_name_no_longer_blocks`** — `عطر أفيون ايف سان لوران`,
    `بلاك أفيون ايف سان لوران ضد لانكوم لا في است بيل`, `أفيون ايف سان لوران ضد بلاك أفيون`, `بلاك أفيون`
    → `allowed is True, reason is None`. RED today: `illegal_drugs` / `أفيون`. (Arabic twin of
    `test_ysl_black_opium_passes_l1_prefilter` + `test_bare_opium_in_brand_name_no_longer_blocks`.)
16. **RED `test_arabic_opium_tincture_blocked`** / **`_poppy_blocked`** / **`_compound_phrases_blocked`** —
    twins of the three EN intent tests, asserting `reason == "illegal_drugs"` AND `blocklist_match` equal
    to the new phrase: `صبغة أفيون` → `صبغة أفيون`; `خشخاش أفيون` → `خشخاش أفيون`; `أفيون خام للتصدير` →
    `أفيون خام`, `وكر أفيون` → `وكر أفيون`. RED today on the `blocklist_match` half (today's match is the
    bare `أفيون`); the `allowed is False` half is green today (strict narrowing).
17. **RED `test_weapons_false_positives_pass`** — the 11 legitimate EN/AR queries of §1e (`silencer` ×3,
    `tactical knife` ×2, `كاتم صوت` ×2, `سكين قتالي` ×1, `بندقية` ×3) + corpus rows `C:other:06`, `C:other:37`
    → allowed. RED today: all blocked.
18. **PIN + RED `test_weapons_intent_still_blocks`** — `gun silencer for sale`, `pistol silencer`,
    `rifle silencer`, `switchblade knife import`, `كاتم صوت مسدس`, `كاتم صوت بندقية`, `بندقية هجومية`,
    `شراء مسدس`, `مسدس جلوك 19`, `ذخيرة مسدس`, `Shotgun shells 12 gauge Winchester vs Remington` →
    `allowed is False, reason == "weapons"` (PIN, green today); the three `* silencer` rows additionally
    assert `blocklist_match` is the new phrase (RED today: `silencer`).
19. **RED `test_catalog_parity_no_bare_ar_twin_of_tightened_en`** — structural, over the LIVE file: for
    each `(en, ar)` in `{("opium", "أفيون"), ("rifle", "بندقية"), ("silencer", "كاتم صوت"),
    ("tactical knife", "سكين قتالي")}`, if `en` is not an entry of its category's `en` list then `ar` is
    not an entry of its `ar` list. RED today on `opium/أفيون` and `rifle/بندقية`.
20. **PIN `test_blocklist_edit_strictly_narrows`** — over the 360 corpus + the 53 probe strings, with the
    HEAD verdicts from `category_corpus_gcc_360_head_records.json["l1_verdicts_head"]`: no string allowed
    at HEAD is blocked now. Green today (identity); guards against a widening re-edit (e.g. variant `A`).
21. **RED `test_corpus_l1_delta_is_exactly_two_rows`** — over the corpus, the set of keys whose L1 verdict
    changed from HEAD is exactly `{"C:other:06", "C:other:37"}`.
22. **PIN** — existing `tests/test_blocklist_collision_audit.py` runs unchanged except the one row §14 Q2
    rules on; `test_audit_reports_zero_collisions` stays green (12 singles / 0 collisions, measured).

## 6. MUTATION CHECKS ARE REQUIRED

M1–M5 were MEASURED on the prototype over the 35 tablet rows + the corpus (`mutations` in the probe
output). M6–M8 and B1–B4 follow from measured tables (§1a `canonicalize_category`, §3b variant rows) and
are the red agent's to run and record against the real implementation.

| mutation | reddens (measured) |
|---|---|
| M1 naive drop (skip every `tablet(s)` hit — the finder's minimum fix) | test 4: 15 of 16 device rows → `other` (all but `tablet vs laptop`), incl. `Samsung Galaxy Tab S10 tablet 256GB` |
| M2 delete rung 1 (`_DEVICE_SPEC_RE`) | test 4: `kids tablet 7 inch vs Fire 7 Kids tablet`, `Wacom One drawing tablet vs Huion Kamvas 13` → `other` |
| M3 delete rung 3 (device vocabulary) | test 4: 8 rows → `other` (`Apple iPad Air M2…`, `Amazon Fire HD 10…`, `Xiaomi Pad 6…`, `Samsung Galaxy Tab A9 tablet`, `Samsung tablet vs Apple tablet`, `Microsoft Surface Pro 11…`, `Kindle Fire tablet…`, `Samsung Galaxy Tablet S9`) |
| M4 delete rung 2 (pharmacy veto) | test 2: `Apple cider vinegar 60 tablets vs Goli gummies` → `electronics` (via the `apple` brand) |
| M5 corroborator always True (= HEAD behaviour) | tests 2, 5, 8, 9, 10, 13: all 17 pharmacy rows `electronics`; corpus delta 0 rows |
| M6 force `category_token_fix_enabled()` to True | tests 3, 12 redden (the flag-OFF pins prove the gate is real) |
| M7 read the flag at import | test 14 reddens |
| M8 edit `_CATEGORY_SYNONYMS` instead (drop the two keys) | test 7 reddens (`canonicalize_category`), and test 4 as M1 |
| B1 restore bare `أفيون` | tests 15, 19 redden |
| B2 add `صبغة الأفيون` (variant `A`) | test 20 reddens (`صبغة الأفيون للبيع` newly blocked) |
| B3 drop `كاتم صوت مسدس` without replacement | test 18 reddens |
| B4 restore bare `silencer` | tests 17, 18 (match half) redden |

Record each with its count; a test that survives its own fix's removal is decoration.

## 7. Preserve (every test file that pins the touched functions or data — grep)

Classifier / resolver / canonicaliser: `tests/test_category_canonicalization.py` (`:68` `tablet→electronics`
canonicaliser row; `:102-117` classifier rows; `:121` Centrum tablets), `tests/test_explicit_pair_category.py`,
`tests/test_resolve_category.py`, `tests/test_supplement_detector_precision.py` (`:107` `Samsung Galaxy Tablet S9`),
`tests/test_error_paths.py` (`:97` galaxy tablet not a supplement), `tests/test_url_compare_category.py`,
`tests/test_fragrance_content_quality.py`, `tests/test_partial_specs_stash_on_price_timeout.py`,
`tests/test_paid_route_metering.py`, `tests/test_retro_w2_1.py`, `tests/test_text_error_envelope_no_raw_exception.py`,
`tests/test_flush_live_price_key.py`. Blocklist / matcher: `tests/test_content_safety_service.py` (`:133`,
`:190`, `:652` pin `مسدس` — untouched by `A_strict`), `tests/test_content_blocklist_opium_legitimate_products.py`,
`tests/test_blocklist_collision_audit.py` (`:91` — §14 Q2), `tests/test_two_input_shape.py`,
`tests/test_openai_breaker.py`, `tests/test_security_regression.py`, `tests/test_image_service_edges.py`,
`tests/test_m13_26_image_error_envelope.py`, `tests/test_model_config.py`, `tests/test_w49_extraction_catch_redaction.py`.

## 8. Comm set

`grep -rlE "extraction_service|content_safety_service|content_blocklist|classify_category_from_text|_resolve_pair_category|check_query_intent|is_text_safe|filter_shopping_items|audit_blocklist_collisions" tests --include=*.py`
= **95 files** (list saved as `.qa-s68/specs/W4_8_comm_set.txt`; `extraction_service` alone 87,
`content_safety_service` 13, `content_blocklist` 4), plus the two new unit files. Base run at `61585c58`
under the netguard with the 11 `tests/.pre_impl_failures.txt` ids deselected:
**3 failed, 2384 passed, 3 skipped, 17 deselected, 35 xfailed** (179 s; `[netguard] blocked 349 network
attempt(s)` — all from pre-existing nodes). The 3 failures (saved as `.qa-s68/specs/W4_8_comm_base_failed.txt`)
are `tests/test_security_hardening.py::TestSSRFProtection::test_valid_external_url_passes`,
`::test_valid_http_url_passes`, `::TestSecurityIntegration::test_ssrf_protection_integrated` — the guard
blocks their `getaddrinfo('example.com')`; accepted base failures. Gate: head run with the identical
command and deselect, `comm -13 base head` of the sorted FAILED ids EMPTY.

## 9. Gates

1. **Flag-OFF equality — the corpus gate, not the `_proof` SHA.** (a) Tests 12 and 3/4/6/7 (flag OFF
   records == the HEAD golden, hash `b76fcef9…`). (b) Independently, the red agent re-runs the probe in a
   DETACHED scratch worktree of `61585c58` (`git worktree add --detach <scratchpad>/w48base 61585c58`)
   and at head with `ENABLE_CATEGORY_TOKEN_FIX` unset, and compares the two `off_all_sha` values (corpus
   + 35 tablet rows, hash at base **`cac3460cd53020b681b87e41781c8ca11a6296f70925608690e2780104e8db3d`**)
   — then base AGAIN (base2) and requires base == head == base2, record by record over
   `off_corpus_records`, never only the hash. Remove the scratch worktree after (`git worktree remove --force`).
   **Why not `scripts/verify_flag_byte_identity.py`:** it calls `extract_price_from_html` only (`:258`,
   `:287`), whose body (`price_service.py:13744-14839`) calls neither the classifier nor the matcher
   (measured: no `is_text_safe`/`classify_category`/`content_safety` reference in that range), and 521/521
   `_proof` titles are unaffected by the data edit (§1e). It is blind by construction; do not run it as
   evidence for this unit, and say so in the PR.
2. **Half B has no flag, so its gate is the narrowing proof:** test 20 (0 widening over 413 strings) +
   test 21 (exactly 2 corpus rows) + the EN audit (12 / 0).
3. TDD red-first; every RED observed red for the stated reason, then green.
4. Comm gate §8. 5. Ruff `E9,F63,F7,F82` + `py_compile` on `extraction_service.py` and both test files;
   `python -c "import json; json.load(open('app/data/content_blocklist.json', encoding='utf-8'))"` and a
   `ContentSafetyService()` construction (the file is load-or-crash, `:54-58`). 6. `git diff --stat` shows
   no whole-file diff on the CRLF backend file. 7. Fable review before commit. Agents never commit.

## 10. CI-order pin set (run in alphabetical = CI order, after the unit files are written)

`tests/test_blocklist_collision_audit.py`, `tests/test_category_canonicalization.py`,
`tests/test_category_token_fix.py`, `tests/test_content_blocklist_arabic_parity.py`,
`tests/test_content_blocklist_opium_legitimate_products.py`, `tests/test_content_safety_service.py`,
`tests/test_error_paths.py`, `tests/test_explicit_pair_category.py`, `tests/test_flush_live_price_key.py`,
`tests/test_fragrance_content_quality.py`, `tests/test_openai_breaker.py`, `tests/test_paid_route_metering.py`,
`tests/test_partial_specs_stash_on_price_timeout.py`, `tests/test_resolve_category.py`, `tests/test_retro_w2_1.py`,
`tests/test_security_regression.py`, `tests/test_supplement_detector_precision.py`,
`tests/test_text_error_envelope_no_raw_exception.py`, `tests/test_two_input_shape.py`,
`tests/test_url_compare_category.py` — once with the flag unset, once with `ENABLE_CATEGORY_TOKEN_FIX=true`
(the second run must show only the RED-then-green rows moving; every Preserve file green in both).
New test files carry their own network guard (issue #184 class) — they must not reach A2b/OpenAI.

## 11. Activation

* **Half B ships live on deploy** (data, unflagged). Watch: the count of `log_content_blocked
  (query_prefilter)` audit rows and `CONTENT_UNAVAILABLE` responses should DROP (measured corpus rate
  3/360 → 1/360). No kill switch other than a revert — state it in the PR.
* **Half A (`ENABLE_CATEGORY_TOKEN_FIX`)**: own window, no ordering coupling with any price flag.
  Expected on flip: pharmacy pairs WITH a Supplements chip route to `supplements` (iHerb → pharmacy
  JSON-LD, bolo, nasser); pharmacy pairs WITHOUT a chip now reach the A2b classifier
  (`classify_category_llm`, gpt-4o-mini, `CLASSIFY_LLM_TIMEOUT` 4 s on the loop) where today they got a
  deterministic (wrong) `electronics` at $0 — **a new LLM call per chipless pharmacy compare**, and while
  OpenAI is 429 it degrades to `other` (not `supplements`). Canary: the distribution of
  `metadata.category_used` for queries containing `tablet`, the A2b call count
  (`classify_category_llm failed, defaulting to 'other'` WARNINGs), and the price `source_method` mix on
  those pairs. Suggested log line (no raw query — PO-CATEGORIES-I18N-14 item 6):
  `[CATEGORY_TOKEN_FIX] tablet token uncorroborated -> skip` at DEBUG.
* No migration, no OTA, no Railway variable other than the flag.

## 12. Honest limits

* ON, a chipless pharmacy pair becomes `other`, not `supplements` — the price-tier gain (§1c) lands only
  when the user taps the chip or A2b answers `supplements`. Mapping "uncorroborated tablets + pharmacy
  signal" straight to `supplements` is a product call (§14 Q4), not built.
* The device vocabulary is the repo's; a device half with no brand/spec/qualifier (`Amazon Fire HD 10
  tablet`, bare `tablet`) goes `other` ON (its pair usually recovers via the other half). A Supplements
  and an Electronics word in one query still resolve longest-token-first exactly as today.
* `Apple cider vinegar tablets` (no count, no dose) stays `electronics` ON (the `apple` brand
  corroborates); only the counted/dosed form is vetoed.
* `PO-CATEGORIES-I18N-02` (0 of 58 Arabic queries classify), `-06` (vitamin-C serums → supplements),
  `-07` (`food` → grocery) are the other 6 of the corpus's 7 wrong rows and are NOT this unit.
* Half B is a hand-curated data list: `الأفيون`, `افيون` and `بلاك اوبيوم` were already allowed and stay
  allowed; `A_strict` does not make the Arabic drug block "work" (the second vote's point), it removes
  its false positives. The camera path (`image_routes.py:390`) passes no `selected_category`, so on a
  vision pharmacy pair the chip branch cannot help (review gap (c)).
* The corpus is the review lane's authored set, not traffic (`search_logs` has 0 Arabic-script and 0
  `tablet` rows per the second votes); frequencies are not traffic frequencies.

## 13. Spec disagreements with the review

1. **Flag name:** the row says `ENABLE_CATEGORY_TOKEN_FIX`; the finder/report U3 said
   `ENABLE_AMBIGUOUS_CATEGORY_TOKENS`. This spec uses the row's name.
2. **"Blocklist edit strictly narrows"** holds only for `A_strict` (0 widening, measured). The finder's
   own proposal (`صبغة أفيون`-class with `ال`: `خشخاش الأفيون`, `وكر أفيون`…) is variant `A` and WIDENS
   (3 strings). Also: any edit that removes bare `silencer` reddens the existing
   `silencer suppressor` pin (`test_blocklist_collision_audit.py:91`), which the review did not mention.
3. **"All 3 blocked corpus queries are legitimate"** (lane): `Shotgun shells 12 gauge Winchester vs
   Remington` is ammunition and an explicit `weapons.en` entry (`:19`); this spec keeps it blocked (test 18).
4. **Anchors:** `extraction_service.py:1096-1097 → :1107-1108`; `classify_category_from_text :1156 → :1167`;
   `scs:5671-5677 → :6234-6237`; `scs:3216/:3770` (L1) `→ :3682/:4281`; `content_blocklist.json:53` unchanged.
5. **Minimum fix rejected (agrees with both votes), measured:** the naive token drop sends 15 of 16
   device rows to `other` (M1).
6. **The corpus does not contain the red-claim phrasing** (`…24 tabs…`, not `tablets`); the flag-ON
   corpus delta is 1 row, so the corpus is an identity gate, not the defect's measurement — the 35-row
   tablet set is.
7. **"worse than filed" is broader than the price branch:** the same category also drops the bolo/nasser
   pharmacy adapters and routes the pair to 2 Shopify + 1 Algolia electronics stores (§1c).

## 14. OPEN QUESTIONS FOR FABLE

1. **Blocklist variant:** `A_strict` (recommended: 0 widening, keeps the "unflagged because strictly
   narrowing" ruling true) vs `A` (natural Arabic `ال` forms, widens by 3 drug-only phrases, needs the
   row's unflagged justification restated).
2. **The `silencer suppressor` pin** (`tests/test_blocklist_collision_audit.py:91`) reddens under every
   variant that removes bare `silencer`. Options: (a) rewrite the row to `gun silencer suppressor`
   (recommended; still `weapons`); (b) add bare `suppressor` (measured: newly blocks `APC surge
   suppressor…` and `Boss NS-2 noise suppressor pedal` — rejected); (c) add the literal phrase
   `silencer suppressor` as an entry (games the pin). Editing an existing pin needs your ruling.
3. **`مسدس` (massage/glue/caulk/heat/water guns blocked today)** — in this unit or its own row
   (`PO-CATEGORIES-I18N-09b`)? Narrowing it (variant `AB`) frees 5 measured product queries but lets
   `شراء مسدس` through and reddens three pins in `tests/test_content_safety_service.py`.
4. **Product call:** should an uncorroborated `tablets` with a pharmacy signal map to `supplements` (so
   chipless pharmacy pairs reach bolo/nasser/iHerb without an A2b call) instead of `other`? Not built.
5. **Parity losses accepted?** `شراء أفيون` ("buy opium") and `بندقية صيد` ("hunting rifle") become allowed
   under `A_strict`, matching their EN twins (both allowed at HEAD). Confirm.
6. **Scope:** fold `PO-CATEGORIES-I18N-09`'s EN half (`silencer`, `tactical knife`) into this unit (as the
   row implies) — yes as specified — or split it out?

## 15. Anchors at `61585c58` (by symbol)

| symbol | review (`76ace90`) | `61585c58` |
|---|---|---|
| `_CATEGORY_SYNONYMS` / `"tablet"` / `"tablets"` | `:1072` / `:1096` / `:1097` | `extraction_service.py:1083` / `:1107` / `:1108` |
| `canonicalize_category` | `:1125` | `:1136` (synonym lookup `:1157-1158`) |
| `classify_category_from_text` / sweep | `:1156` / `:1175-1179` | `:1167` / `:1187-1189` (`is_supplement_query` import `:1182`) |
| `classify_category_llm` | `:1217`-ish | `:1217` (`_CLASSIFY_LLM_TIMEOUT` `:1214`) |
| `specs_no_fabrication_enabled` (flag idiom) | — | `:535` (body `:584-586`) |
| `_resolve_pair_category` / `name_cat` / explicit det | `scs:316-380` | `scs:440` / `:467` / `:493` |
| L1 gate sync / stream | `scs:3216` / `:3770` | `scs:3682` / `:4281` |
| per-product classify vision / explicit (sync) | `:3253-3262` | `:3709` / `:3726`; stream `:4311` / `:4327`; seed `:3654` |
| `_fetch_product_data` / canonicalise / price call | — | `:5088` / `:5107` / `:5180` |
| `_get_price` / `set_resolved_price_category` / `is_supplement =` | `:5671-5677` | `:5992` / `:6001` / `:6234-6237` |
| category-gated sitemap / jsonapi selectors | — | `:6388-6389` (`source_router.py:792` / `:747`) |
| supplement Tier-1 branch | — | `:6805` |
| `is_supplement_query` / `SUPPLEMENT_FORM_TOKENS` / `_contains_token` | `price_service.py:1181` | `price_service.py:1295` / `:643` / `:1227` |
| device vocabularies | — | `HIGH_VALUE_DEVICE_TOKENS :484`, `HIGH_VALUE_BRANDS :489`, `_ELECTRONICS_BRAND_KEYWORDS :1682`, `_ELECTRONICS_DEVICE_NOUNS :1689`, `is_electronics_query :1700` |
| blocklist: `silencer` / `tactical knife` / `shotgun shells` | `:13` / `:16` / — | `content_blocklist.json:13` / `:16` / `:19` |
| blocklist: `مسدس` / `بندقية` / `كاتم صوت` / `سكين قتالي` / `بندقية هجومية` | — | `:22` / `:23` / `:26` / `:27` / `:28` |
| blocklist: EN opium phrases / AR `أفيون` | `:42-45` / `:53` | `:42-45` / `:53` |
| matcher load / compile / `check_query_intent` / `is_text_safe` / `filter_shopping_items` / singleton | — | `content_safety_service.py:54` / `:69-72` / `:74` / `:91` / `:108` / `:183` |
| explicit-pair query join | — | `text_routes.py:252` (POST body), GET `:571`, stream GET `:738` |
| camera path (no chip) | `image_routes.py:229` | `image_routes.py:390` |


# ADVERSARIAL SPEC REVIEW (2026-09-26, session 68)

Reviewer: adversarial spec reviewer, base `61585c58` (`git rev-parse HEAD` in `sc-w4-specs` =
`61585c581e9deb78213f030260a765080f2e1dff`, `git status --short` empty). Spec sha256 on arrival
`4eaa4b468c7c31dfe16e9120eccfb3ba635370f150d49b1938add82b9e62f6ee` (matches the author's report). Every
measurement below ran through pytest with `-p qaren_netguard -p tests.conftest` on the pinned venv; each
run printed `[netguard] blocked 0 network attempt(s)`, except the comm base run, which printed `349`
(all from pre-existing nodes). Reviewer probes live in the reviewer's scratchpad (`adv48/test_adv48*.py`);
nothing under the worktree was written except this section.

## VERDICT: APPROVED_WITH_CORRECTIONS

The core red claims, the corpus numbers, every hash and the comm base reproduce exactly. The design of
Half A is sound for the pharmacy side. Five things must change before the red phase: the mutation
table (B3 survives its own removal, B4 is killed only by test 17, and 9 of 12 corroborator
alternatives are unpinned); the pharmacy false positive `Panadol Kids tablets`; the device-side
recall loss the curated set hides; the fixture and gate recipe gaps; and the Half-B intent losses,
which the spec undercounts. Fable must also rule on whether Half B may ship unflagged (Q-R1).

## 1. Claims re-measured: HOLDS (reproduced exactly)

* Red claim 1: `classify_category_from_text('Panadol Extra 24 tablets vs Adol 500 tablets')` =
  `electronics`; both halves `electronics`; `is_supplement_query` False on pair and half. HOLDS.
* Red claim 2 node: `Samsung Galaxy Tab S10 tablet 256GB` = `electronics`, `is_high_value_query` True;
  `canonicalize_category('tablet'/'Tablets')` = `electronics`. HOLDS.
* Arabic opium: bare-hamza query gives `allowed=False, illegal_drugs, match = the bare token`; the
  no-hamza, `al-` and transliterated forms are allowed. HOLDS.
* Tablet set at HEAD: 17 of 18 pharmacy rows `electronics` (TP:17 Redoxon `supplements`), 17 of 17
  device rows `electronics`. Resolver with a Supplements chip: 17 x `('electronics', True,
  'supplements')`. Prototype ON: 17 pharmacy rows `other` and 16 of 16 listed device rows
  `electronics`, bare `tablet` `other`. HOLDS on the author's set (see R4 for the wider set).
* Capture harness: HEAD sync/stream, chip or no chip, gives `electronics x2`. PROTO_ON with the chip gives
  `supplements x2`, and without the chip gives `other x2`. HOLDS.
* Test 9 premise: prototype ON, no chip, A2b stub returning `supplements` gives
  `['supplements', False, None]` with the stub called exactly once. HOLDS.
* Corpus: 360 rows (9 x 40); `runpy(corpus.py)["CORPUS"]` flattened == the frozen row order (True);
  source sha `157b94f6...` and frozen sha `0852f556...` match; ordered-query hash `9352717a...` reproduces
  (compact `sort_keys, separators=(",",":")` form). L1-blocked 3 (`C:other:06/37/38`); classifier
  74/279/7; chip-override 7; Arabic 0 of 58. HOLDS.
* Hashes: corpus records OFF `b76fcef9...`, ON `5421996c...`, exactly one differing record
  (`C:supplements:05`), all-records OFF `cac3460c...`; golden `corpus_classification_records` ==
  the probe's OFF records and hashes to `b76fcef9...`; corpus L1 hash `3885d270...`. HOLDS.
* Blocklist variants: `A_strict` widens 0, narrows 20 (the 20 keys listed in §3b); `A` widens 3
  (`BI:05/07/09`); `A2_suppressor` widens 5; `AB` narrows 27. EN audit: HEAD 13 singles / 0 collisions,
  `A_strict` 12 / 0. L2 over the 521 `_proof` titles: 0 unsafe and 0 differences under every variant. HOLDS.
* Comm set: the §8 grep gives 95 files, the same set as `W4_8_comm_set.txt`. Base run at `61585c58`
  with the 11 baseline ids deselected: `3 failed, 2384 passed, 3 skipped, 17 deselected, 35 xfailed`
  (182.7 s), `[netguard] blocked 349 network attempt(s)`. The 3 FAILED ids are exactly the ones in
  `W4_8_comm_base_failed.txt`. HOLDS.
* Mutations M1–M5 on the prototype: naive drop sends 15 device rows to `other`; the spec rung 2 rows
  (TD:07, TD:12); the vocabulary rung 8 rows; the veto 1 row (TP:14); always-corroborate all 17 pharmacy
  rows plus bare `tablet`. HOLDS.
* Anchors re-checked by symbol: `_CATEGORY_SYNONYMS` :1083 / `tablet` :1107 / `tablets` :1108;
  `canonicalize_category` :1136; `classify_category_from_text` :1167; `classify_category_llm` :1217;
  `specs_no_fabrication_enabled` :535 with getenv at :584; `_resolve_pair_category` :440, `name_cat`
  :467; L1 :3682/:4281; classify sites :3654/:3709/:3726/:4311/:4327; `set_resolved_price_category`
  :6001; `is_supplement =` :6234; selectors :6388-6389; price_service :484/:489/:643/:1227/:1236/
  :1295/:1682/:1689/:1700; source_router :747/:792; 22 `is_text_safe` call sites in `app/`;
  `filter_shopping_items` caller `price_service.py:10228`; text_routes :252/:571/:738; image_routes
  :390; the client diff `ab9442ae..61585c58 -- SmartCompareApp/src` is empty. Every diff-empty range
  holds against `76ace90` (the `extraction_service.py` hunks start at :1231, inside
  `classify_category_llm`, after the classifier). HOLDS.

## 2. Refuted or drifted claims (with measurement)

* **R1 — Mutation B3 is wrong.** It claims that dropping `كاتم صوت مسدس` without replacement reddens test 18.
  Measured under `A_strict` minus that entry, the query `كاتم صوت مسدس` stays `allowed=False, weapons`,
  with match = the bare `مسدس` (entry :22). Test 18 asserts only `allowed`/`reason` on the AR rows, so
  B3 SURVIVES. The entry is redundant for blocking: the bare `مسدس` still blocks, and the entry only
  changes `blocklist_match`. The load-bearing AR add is `كاتم صوت بندقية`. Dropping it (my `B3b`)
  makes that query `allowed=True`, which reddens test 18.
* **R2 — Mutation B4 is killed by test 17 only.** Under `A_strict` plus bare `silencer`, the matches
  for `gun silencer for sale`, `pistol silencer` and `rifle silencer` stay the NEW phrases, because the
  leftmost match position wins and each phrase starts before `silencer`. The "18 (match half)" part of
  the claim is refuted.
* **R3 — `firearm silencer` is a dead entry.** `firearm` is already `weapons.en` :8, earlier in the
  alternation. Under `A_strict` the query `firearm silencer` matches `firearm`, and removing the added
  entry changes nothing (measured). Drop it from the add list or state that it is inert.
* **R4 — "16/16 device rows stay electronics" does not generalise.** On 27 realistic device strings
  outside the author's list, the prototype sends 20 of 27 to `other`: Honor Pad 9, Nokia T21,
  Motorola Moto Tab G70, Amazon Fire 7, Amazon Fire HD 8 vs Fire HD 10, Wacom Intuos, Huion H610 Pro,
  XP-Pen Deco 01, reMarkable 2, Boox Note Air 3, Teclast P85, Blackview Tab 70, Surface Go 4, Honor Pad
  X9 vs Redmi Pad SE, Kobo Clara, Alcatel 1T, Doogee T10, Fire HD 10 Kids Pro, Wacom tablet vs Huion
  tablet, Chuwi HiPad X. HEAD gives `electronics` for all 27. The author's set was drawn from brands in
  the vocabulary. Consequence under ON: a chipless device compare from these brands now pays an A2b
  gpt-4o-mini call (4 s) where HEAD was a deterministic `electronics` at $0. While OpenAI is 429 it
  degrades to `other`, which means the wrong spec schema, dimensions and price sources.
* **R5 — A pharmacy false positive survives ON.** `Panadol Kids tablets` and `Adol Kids tablets vs
  Panadol Kids tablets` stay `electronics` under the prototype, because rung 1's `kids\s+tablets?`
  fires before the veto. Also still `electronics` ON: `Samsung washing machine cleaning tablets`,
  `LG washing machine tub clean tablets`, `Dyson descaling tablets` and `Nothing but Panadol tablets`
  (brand `nothing`). Across 25 extra pharmacy and household strings, 7 of 25 stay `electronics` ON.
* **R6 — 9 of 12 corroborator alternatives are unpinned.** I measured each alternative's deletion over
  every string tests 2–14 evaluate (the 35 rows, their halves, `tablet vs laptop` and Centrum).
  Deleting any one of these changes 0 outputs: rung-1 `gb|tb`, `wi-?fi|cellular|lte|[45]g`,
  `inch|inches|"`, the qualifiers `android`, `graphics`, `pen`, `gaming` and `windows`, and the rung-2
  dose alternative `mg|mcg|iu`. Only `kids` (Fire 7 Kids tablet), `drawing` (Wacom One) and the plural
  count (Apple cider vinegar 60 tablets) are killed. So §6's claim that the mutation table kills every
  load-bearing line is refuted.
* **R7 — The §1c source table is a test-environment measurement, not production.** With
  `ENABLE_BH_GCC_CATALOG_SOURCES=true` (ON in prod; measured on a private `source_router` instance,
  319 rows vs 44 literal), the selectors give: `electronics` 7 Shopify + 1 Algolia (the spec says
  2 / 1); `supplements` sitemap `['bolo.bh']`, jsonapi `['nasserpharmacy.com']`, 6 Shopify (skipped by
  the `not is_supplement` gate); `other` **13 Shopify** + 0 Algolia (the spec says 0 / 0). So a chipless
  pharmacy pair that goes `other` ON still fans out to 13 Shopify stores in prod, not 0.
* **R8 — "Only 1 corpus row contains tablets" should be 2.** `Iron 65 mg tablets vs Iron 18 mg
  gummies` also contains `tablets`. It is caught by `is_supplement_query` before the sweep, so the
  "1 row reaches the synonym" reading holds, but the stated count does not.
* **R9 — Variant AB breaks four `مسدس` pins, not three.** Measured under AB: :134 and :192 become
  allowed, :277 (`filter_shopping_items` keeps 2 items, the test wants 1) reddens, and :652 becomes
  `is_text_safe` True. The spec's §1e, §7 and Q3 cite :133/:190/:652. The call lines are :134 and :192,
  and :277 is missing.
* **R10 — The L1 golden hash is ambiguous.** `l1_verdicts_head` holds 413 entries (360 `C:` + 53
  `BL:`/`BI:`) and hashes to `8c8de712de00844c081901b4e1afc628ef5200bfd1ca7b89629bf5d2ea144627`.
  `3885d270...` is its 360-row `C:` subset only. §4 ("checked against the two hashes of §1d") would
  fail a red agent that hashes the whole key.
* **R11 — Wrong anchor in the §1c table.** `:6805` is the supplement Tier-1 shopping SKIP
  (`if is_supplement: search_results = {...}`), not an "iHerb → pharmacy JSON-LD branch". The iHerb
  stage is `:7613` (`if is_supplement:`) / `:7651` (Stage 1). One more point: the in-code comment at
  `:6379-6386` says the supplement branch does not consume the bolo/nasser prefetch. The escalation
  block at `:6965` has no `is_supplement` guard, and `_consume_adapter_prefetch()` at `:7190` sits
  inside it, ahead of the iHerb stage at `:7613`. So test 11 proves selector membership only. It does
  not prove the price tier end to end, as §5 test 11 claims.
* **R12 — Q5/§3b list only 3 intent strings that lose their block. The real count is larger.** I measured 22 natural
  intent phrasings. Under `A_strict`, 18 of them go from BLOCKED at HEAD to ALLOWED. Seven are EN weapons
  strings: `buy silencer`, `silencer for sale`, `silencer for rifle`, `9mm silencer`,
  `silencer for glock`, `tactical knife for self defense`, `buy tactical knife`. The other eleven
  are Arabic: `كاتم صوت للمسدس`, `كاتم صوت لمسدس`, `كاتم صوت للبندقية`, `كاتم صوت مسدسات`,
  `شراء كاتم صوت`, `بندقية قنص`, `شراء بندقية`, `سكين قتالي للبيع`, `بيع أفيون`, `أفيون للبيع`,
  `تهريب أفيون`. Still blocked: `sniper rifle silencer`, `handgun silencer`, `firearm silencer`.
  The EN rows are NOT parity. EN `buy silencer` and `silencer for sale` are blocked at HEAD, so
  `A_strict` loosens EN itself. The spec's "deliberate EN-parity consequence" framing covers only the
  opium and rifle rows.

## 3. Corrections (edits the spec needs)

1. §6 mutation table:
   * Replace B3 with "drop `كاتم صوت بندقية` → test 18 reddens (`كاتم صوت بندقية` allowed)". Alternatively,
     make test 18 assert `blocklist_match` on the AR rows too, so the `كاتم صوت مسدس` entry is pinned.
   * B4: "test 17 reddens". Remove "18 (match half)".
   * Add per-alternative rows for every rung-1/rung-2 alternative, and pin each with a test row that only
     that alternative corroborates. Examples: `Teclast P85 tablet 128GB`, `Teclast tablet wifi`,
     `Teclast 10 inch tablet`, `Windows tablet`, `Android tablet vs Teclast tablet`, `pen tablet`,
     `Apple cider vinegar 500mg tablets` (dose only). The other option is to delete the unpinned
     alternatives. The standing rule is: a line that survives its own removal is decoration.
2. Rung 1: remove `kids` from the qualifier list. It is the only qualifier that fires on a common GCC
   pharmacy product. Add `Panadol Kids tablets` and `Adol Kids tablets vs Panadol Kids tablets` to the
   test-2 parametrization (`other` ON) and a test-3 row (OFF `electronics`). Re-measure M2; TD:07 still
   corroborates through `7 inch` on its first half, which must then be pinned.
3. §3a / §12: replace "16/16 device rows stay electronics" with the measured recall on a brand-diverse
   set (proto 7 of 27 electronics; a veto-only variant, "tablets = device unless a dose/count
   signal", gives 27 of 27 devices but lets 6 of 18 + 18 of 25 pharmacy strings stay electronics). State the
   A2b-cost and OpenAI-429 consequence for chipless device pairs. Commit a DEVICE-side PIN of
   non-vocabulary brands in test 4 or test 5 so a future vocabulary edit is measured in both directions.
4. §3b add list: drop `firearm silencer` (inert, R3), or keep it with a note that it never matches.
5. §4 / tests 12/20: the fixture `category_corpus_gcc_360_head_records.json` must carry `l1_queries`
   (the 53 `BL:`/`BI:` query strings; `probe_inputs.json` is not committed), and the spec must state both
   L1 hashes: whole-map `8c8de712...` and the `C:` subset `3885d270...`.
6. §9 gate 6: also check `app/data/content_blocklist.json`. It is CRLF in the working copy and LF in the
   index (`git ls-files --eol`: `i/lf w/crlf`), and it stores raw UTF-8 Arabic. A `json.dump` rewrite
   (ensure_ascii default and LF) makes a whole-file diff. Edit it in place with the Edit tool; the
   diff must be the added or removed entry lines plus `updated_at`.
7. §0 recipe: `PYTHONPATH` must use Windows-form absolute paths (`C:/...`). With `PD=$PWD/...` in Git
   Bash the entries are `/c/...`, and Windows Python cannot import `test_probe_w48`
   (`ModuleNotFoundError`, measured).
8. §7 Preserve and §10 CI-order set: add every file that pins a touched function. The grep for
   `classify_category_from_text|_resolve_pair_category|check_query_intent|is_text_safe|
   filter_shopping_items|content_blocklist|ContentSafetyService|canonicalize_category|explicit_pair`
   gives 28 files. Missing from §7: `test_category_dimensions`, `test_category_payload_completeness`,
   `test_explicit_pair_integration_mocked` (8 explicit_pair pins), `test_latency_stack_i56`,
   `test_logger_no_query_leak`, `test_prescoring_showable_guard`, `test_rating_provenance`,
   `test_timeout_partial_integration`. Missing from §10 (though listed in §7): `test_image_service_edges`,
   `test_m13_26_image_error_envelope`, `test_w49_extraction_catch_redaction`.
9. §1c: correct the Shopify/Algolia counts to the prod-catalog numbers (R7), relabel `:6805` (R11), and
   downgrade test 11 to "selector membership". If membership is kept, assert `bolo.bh in` /
   `nasserpharmacy.com in` / `not in electronics` rather than `== []`. The empty lists depend on the
   import-time `ENABLE_BH_GCC_CATALOG_SOURCES` state of `SOURCE_REGISTRY` (`source_router.py:532`).
10. §3a client paragraph: the claim that values change "and the client renders neither" holds for
    `category_used` and `category_switched`. But the category VALUE is rendered elsewhere. The top-level
    response `category` feeds the Home smart-pick pill (`home_routes.py:497` → `HomeEditorialSections.tsx:101`,
    uppercased, so `ELECTRONICS` becomes `SUPPLEMENTS` or `OTHER`), and `HistoryScreen.tsx:496` reads
    `item.category`. These are value-only changes that 561d2cba renders; name them.
11. §2 claims "reuse, don't reinvent", yet rung 2 invents a dose regex that is `SUPPLEMENT_DOSE_RE`
    (`price_service.py:638`) minus `g`. Rung 1 runs first and catches `4g`/`5g`, so reusing the existing
    regex is safe. Either reuse it or say why not.
12. Q3 evidence: AB reddens 4 pins (:134, :192, :277, :652), not 3.

## 4. Missing items

* **The specs cache is not keyed on category.** `_get_specs` keys on `get_specs_cache_key(brand, name,
  variant)` (`extraction_service.py:2573`, `scs:5762`), with 7 d in L1 and 30 d in L2. Any pharmacy
  product compared before the flip keeps serving its ELECTRONICS-schema specs (and no
  `drug_context`) after the flip, for up to 30 days. The price key takes `category` only for the
  electronics bare-5G drop, so the price entries are shared too. So: (a) the §11 canary must use
  `nocache=true` or never-seen pairs, or it reads a "no change" that is only cache; (b) a flag
  rollback ON→OFF leaves supplements-schema specs cached under the same key. That is flag-OFF
  identity at the code level but not at the state level, and the spec must say so; (c) "the spec
  table the phone renders follows the category — that is the fix" is false for cached products.
* **No pin for the dose-only veto**, and none for any single-alternative device row (R6).
* **No pin for R5** (`Panadol Kids`).
* **No written policy for the natural intent phrasings (R12).** Test 18 fixes 11 blocked rows and
  test 20 guards only against widening. Nothing records that `buy silencer`, `silencer for sale`,
  `شراء كاتم صوت`, `أفيون للبيع` or `بيع أفيون` become allowed. Whatever Fable rules, commit those
  strings with their ruled verdicts.
* **L2 on shopping snippets is unmeasured.** The spec measured page titles only (`is_text_safe`). The
  narrowing also changes `filter_shopping_items` on Serper title+snippet text on the price path; no
  snippet corpus was run.
* **The flag-ON CI-order run lacks two things:** the capture tests and a device non-vocabulary row, so a
  vocabulary regression cannot appear in either run.

## 5. Design risks

* **Half B is shipped unflagged on a "strictly narrowing" argument, and that argument points the wrong
  way for a blocklist.** "0 newly blocked" proves no new false positives. It says nothing about the risk
  class of a safety list, which is newly ALLOWED content: measured 20 of 413 probe strings plus 18 of 22
  natural intent phrasings, several of them EN strings that are blocked today. The CLAUDE.md precedent
  for unflagged changes is "pure defect fixes, no behavioural fork for legitimate traffic". This change
  forks legitimate traffic (that is the goal) and also loosens intent. The only kill switch is a revert.
  A per-call flag is feasible: compile both lists and select per call in `check_query_intent`,
  `is_text_safe` and `filter_shopping_items`. That flag would sit on the L2 price surfaces as well.
* **Half A trades device recall for pharmacy precision** (R4 against the veto-only numbers). The spec
  presents this as a pure fix. It is a product choice between two error classes. Each one has a price
  and schema consequence and, ON, an A2b cost.
* **A2b on the cold path:** each chipless pharmacy compare, and (R4) each chipless out-of-vocabulary
  device compare, adds up to 4 s (`_CLASSIFY_LLM_TIMEOUT`, read at import) before `_fetch_product_data`,
  plus an OpenAI call behind the preflight breaker.
* **The specs and price caches mask the flip, and survive a rollback** (see §4).
* **Test 11's empty-list pins depend on import-time registry state** and can flake if another test
  loads the catalog.

## 6. Questions Fable must rule on (in addition to the spec's §14)

* **Q-R1.** Half B unflagged or flagged? Given R12 (EN `buy silencer` and `silencer for sale` are blocked
  today and allowed under `A_strict`) and the unmeasured L2 snippet surface, does "strictly narrowing" meet
  the unflagged bar? If it stays unflagged, rule on each R12 string. At minimum consider keeping
  `silencer for sale`, `buy silencer`, `شراء كاتم صوت`, `كاتم صوت للمسدس`, `أفيون للبيع` and `بيع أفيون`
  blocked through phrase entries (for example `buy silencer`, `silencer for sale`, `كاتم صوت لل`-forms,
  `للبيع` phrases).
* **Q-R2.** Device recall vs pharmacy precision: accept the prototype (7 of 27 out-of-vocabulary
  devices stay electronics; the rest go to A2b), curate a tablet-brand list into rung 3 (honor, nokia,
  motorola, amazon fire, wacom, huion, xp-pen, remarkable, boox, teclast, blackview, surface, kobo,
  alcatel, redmi, doogee, chuwi), or use a veto-only corroborator? Whichever is chosen, the choice
  must be measured on BOTH sets and pinned.
* **Q-R3.** Drop `kids` from rung 1 (R5)?
* **Q-R4.** The specs-cache consequence: accept a stale-schema window of up to 30 days for already-seen
  pharmacy products after the flip, or key the specs cache on the resolved category under the flag? The
  second is a cache-key change that needs its own identity proof.
