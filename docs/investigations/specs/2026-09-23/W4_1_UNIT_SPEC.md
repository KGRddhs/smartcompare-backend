# W4-1 — the shopping rung stamps the currency it parsed, and `local_bhd` needs a host

Findings `PO-PRICE-TRUTH-01`, `PO-PRICE-TRUTH-02`, `PO-RECORDED-MEASURED-02` (one
cluster). Flag `ENABLE_SHOPPING_CURRENCY_TRUTH`, default OFF, read PER CALL.
Worktree `sc-w4-1`, branch `feature/s65-w4-1-shopping-currency-truth`, from
`ed75dc70` (= origin/main). Every line anchor below is at that SHA (the review's
anchors are from `76ace90` and have drifted — resolved by symbol, table at the end).
Every number below was MEASURED by running the real function offline
(`PYTHONIOENCODING=utf-8`, no network, no `LIVE`).

## The defect, measured

`extract_price_from_shopping(product_name, shopping_items, currency, shopping_region=None, category=None)`
(`app/services/price_service.py:9656`). Per item the loop does, in order:

| step | line | what it does today |
|---|---|---|
| detect | `:9714` | `detected_cur = detect_currency(price_str)` — `detect_currency` (`:3584`) consults ONLY `CURRENCY_SYMBOLS` `{$,£,€,¥}` (`:665`) and the 11-code `CURRENCY_CODES` (`:666`). It never reads `GCC_CURRENCY_SYMBOLS` (`:692`, `BD/KD/SR/QR/DHS` + the Arabic glyphs), so every GCC display token and every ISO code outside the 11 returns `None`. |
| strict pend | `:9722-9725` | `if shopping_strict_currency_enabled() and shopping_strict_currency_pend(price_str, detected_cur, currency): continue` — M13-09, default OFF. |
| parse | `:9726` | `parse_price_string(price_str, detected_cur, display_text=True)` (`:3518` → `parse_money` `:3382`). With `currency=None`, `_money_minor_unit` (`:3327`) falls back to 2, so a 3-digit tail on a lone separator in display text is a GROUPING run: `22.500` → 22500. |
| label | `:9733-9737` | `item_converted = region_is_us_fallback or (detected_cur and detected_cur != currency)`; a converted amount goes through `_convert_to_bhd` (`:827`). |
| url | `:9804-9807`, `:9820` | `link` is used only to upgrade `retailer_score` for `OFFICIAL_BRAND_DOMAINS`; `"url": item.get("link") or build_retailer_url(...)` (`:9369` — a retailer SEARCH url, itself a listing url). |
| source_method | `:9824` | `"converted_usd" if item_converted else "local_bhd"` — the host contributes NOTHING. |

Run through the real function, target `'BHD'`, one title-matched item, a BH-evidenced
link (`bahrain.sharafdg.com/product/x`) unless stated, `round(amount, 2)` is the
function's own (`:9817`):

| case | defaults (all OFF) | `STRICT=true` | `EXTENDED=true` | `STRICT+EXTENDED` |
|---|---|---|---|---|
| A `22.500 BD` | **22500.0 BHD local_bhd** | 22500.0 local_bhd | 22500.0 local_bhd | 22500.0 local_bhd |
| B `8.750 KD` | **8750.0 BHD local_bhd** | PENDED (None) | 8750.0 local_bhd | PENDED |
| C `250 SR` | **250.0 BHD local_bhd** | PENDED | 250.0 local_bhd | PENDED |
| D `32,000 QR` | **32000.0 BHD local_bhd** | PENDED | 32000.0 local_bhd | PENDED |
| E `TRY 1.299,00` | **1299.0 BHD local_bhd** | 1299.0 local_bhd | 1299.0 local_bhd | PENDED |
| F `259.44`, link `google.com/search?ibp=oshop` | **259.44 BHD local_bhd** | same | same | same |
| G `259.44`, BH link | 259.44 local_bhd | same | same | same |
| H `1,399 د.إ` on BHD ask | 1399.0 BHD local_bhd | PENDED | 1399.0 local_bhd | PENDED |
| I `250 ر.س` on SAR ask | 250.0 SAR local_bhd | 250.0 local_bhd | same | same |
| J `SAR 250` on BHD ask | 25.07 BHD converted_usd | same | same | same |

Per-string intermediates at defaults: `detect_currency` is `None` for A–I;
`_shopping_foreign_currency_signal(s, 'BHD')` is `False` for A (residue `BD` →
`_normalize_currency_code` → **BHD = target**), `True` for B/C/D/H, `False` for E
(residue `TRY` unresolvable with the base 13-rate table, ASCII → not foreign),
`False` for F/G (no residue). All ten `FALLBACK_RATES_EXTENDED` codes
(`TRY/PLN/CAD/JOD/SEK/DKK/CHF/EGP/NOK/AUD`) behave as E: `1299.0 local_bhd` at
defaults, PENDED under `STRICT+EXTENDED`.

**So the review is partly stale, and the spec says exactly how:**
* **A and F have NO remedy in any existing flag** — they are this unit's reason to exist.
* **B/C/D are already de-fanged by `ENABLE_SHOPPING_STRICT_CURRENCY`** — it PENDS
  them (loses a convertible price). W4-1 upgrades pend → convert with the honest
  `converted_usd` label. "RED: 8750/250/32000" is true at the shipped defaults only.
* **E is already PENDED by `STRICT+EXTENDED`** (the documented precondition
  coupling, CLAUDE.md "Wave M13-W2 flags"). W4-1 adds the EXTENDED-independent
  pend (Fable: "a well-formed non-target ISO code is FOREIGN even when
  unconvertible") and, with EXTENDED ON, converts it instead of pending.
* I (the target-currency Arabic glyph) ships on every state and MUST keep shipping.

Display consequence at HEAD: `is_price_showable(..., enforce_correctness=True)`
(`:1781`) pends F as `guard_rejected='non_pdp_url'` (`:1865`, via `_is_listing_url`
`:8238` → `source_router.is_non_pdp_listing_url` `:1078`; measured `True` for the
google search link) and passes G. So the wrong `local_bhd` on a google-linked row
is invisible on the results surface TODAY, but not in `price_cache_ttl` (`:194`, 7d
genuine TTL), `_is_genuine_bh_candidate` (`:16226`, wins the fan-out race), or the
`usable_exact_genuine` KPI — and it becomes visible the moment W4-2 stops
pending the link. That is the review's hard order.

Exchange path: `_convert_to_bhd` (`:827`) multiplies by
`exchange_rate_service.effective_fallback_rates()` (`app/services/exchange_rate_service.py:69`
= `FALLBACK_RATES` `:19`, 13 codes; `|= FALLBACK_RATES_EXTENDED` `:43` only when
`ENABLE_EXTENDED_FALLBACK_RATES` is on). Measured rates `KWD 1.23`, `SAR 0.1003`,
`QAR 0.1033`, `BHD 1.0`, `AED 0.1024`, `TRY 0.0094` (extended). Arithmetic
confirmed: `8.75×1.23 = 10.7625`, `250×0.1003 = 25.075`, `32000×0.1033 = 3305.6`,
`1399×0.1024 = 143.2576`, `1299×0.0094 = 12.2106`. **After the function's
`round(amount, 2)` these are `10.76`, `25.07` (measured `round(25.075, 2) == 25.07`),
`3305.6`, `143.26`, `12.21`.** The review's `10.7625 / 25.075` are pre-rounding
values; the tests assert the rounded ones (the idiom `test_m13_shopping_strict_currency.py`
already uses: `143.26`, `526.02`, `30.09`).

Host facts measured through `source_router.registry_tier` (`:616`) and `_is_listing_url`:
`google.com/search?ibp=oshop` → tier `None`, listing `True`; `google.com/shopping/product/…`
→ `None`, listing `False`; `amazon.com`, `apple.com`, `bh.iherb.com` → `global`;
`bahrain.sharafdg.com`, `gcc.luluhypermarket.com`, `extra.com` (for `/en-sa/` too),
`sephora.me`, `bolo.bh` → `bahrain`; `noon.com` → `gcc` (two registry rows, first
match wins with `ENABLE_LONGEST_HOST_MATCH` OFF); `www.luluhypermarket.com`,
`bestbuy.com` → `None`. Registry `bahrain`-tier rows (24) declare `locale_paths`
on only 3 (`nasserpharmacy.com /bh-en`, `sephora.me /bh-en`, `boutiqaat.com /en-bh`)
— the registry alone cannot tell `extra.com/en-bh/` from `extra.com/en-sa/`.

## What already exists — reuse it, do not reinvent it

* **Flag idiom** — `shopping_strict_currency_enabled()` (`:9524-9541`): `os.getenv(...)
  .strip().lower() in ("true","1","yes","on")`, read per call, never at import. Copy it
  verbatim as `shopping_currency_truth_enabled()`.
* **ONE shared admission helper for BOTH doors** — `shopping_strict_currency_pend`
  (`:9613`) is called by the front door (`:9722`) AND by the M13-10 re-selection stash
  `structured_comparison_service._seed_shortcircuit_candidates` (`:8172`, strict
  mirror at `:8240-8242`, its own `source_method` stamp ~`:8268`). CD-wave-diffs-03
  paid for this pattern: a rule applied at the front door only lets the stash seed
  (and `reconcile_pair_fairness` ship) the exact row the front door rejected. **Every
  new rule in this unit lives in a shared helper both doors call under the same flag.**
* **Residue machinery** — `_RESIDUE_STRIP_RE` (`:9563`), `_GCC_SYMBOL_RESIDUE`
  (`:9572`, separator-stripped GCC glyph mirror), `_normalize_currency_code` (`:722`:
  effective-table ISO first, then `GCC_CURRENCY_SYMBOLS` — `"BD"→BHD`, `"KD"→KWD`,
  `"SR"→SAR`, `"QR"→QAR`, `"DHS"→AED`), `_CURRENCY_FOLD_STRIP` (`:719`). The
  resolver this unit adds is `_shopping_foreign_currency_signal`'s (`:9578`) first two
  steps with the answer KEPT instead of compared.
* **Known-currency vocabulary, flag-independent** — the KEYS of `FALLBACK_RATES` ∪
  `FALLBACK_RATES_EXTENDED` (`exchange_rate_service.py:19/:43`) ∪
  `_THREE_DECIMAL_CURRENCIES` (`:11322`) ∪ `_ZERO_DECIMAL_CURRENCIES` (`:3316`).
  Reading the extended dict's keys is not converting with it; it lets the unit say
  "TRY is a currency we know and cannot convert today" without EXTENDED being on.
* **Conversion + honest label** — the T2 rule at `:9733-9737`/`:9824` and the stash's
  copy: a resolved non-target currency converts via `_convert_to_bhd` and stamps
  `converted_usd`. `converted_usd` is showable (`_showable_source_methods` `:1743`),
  not genuine (`is_genuine_source_method` `:151`), 24 h TTL, not in the KPI numerator
  — the label `#51` (`ENABLE_CONVERTED_PROVENANCE_STAMP`) already reserves for
  "a real listing whose provenance is not a verified Bahrain shelf".
* **Host predicates** — `_is_listing_url` (`:8238`), `registry_tier` (`source_router.py:616`),
  `_registry_row_for_host(host, where=)` (`:562`), the wrong-GCC locale regex
  `_LOCALE_SEG_RE` (`:1123`, `/(en|ar)-(sa|ae|om|kw|qa)/`), the BH locale vocabulary
  the registry already documents on its `locale_paths`/`subdomain_patterns` fields
  (`:70-71`: `/bh-en, /en-bh, /ar-bh, /bahrain, /bh` and `bh., bahrain., en-bh.`),
  `extract_domain` (`price_service.py:3297`), and the standing rule "a `global`-tier
  host can never carry a genuine label" (`_is_genuine_bh_candidate` `:16226`,
  `_curl_scraper` downgrade).
* **Cache-write guard** — `should_cache_price` (`:9010`) already refuses a missing
  or listing `url` (`:9048`), so a google-linked row cannot enter the genuine TTL
  through it at HEAD. The 857 google-linked `local_bhd` rows the review counted
  predate that guard or entered through the L2 writer; this unit does not touch them
  (see Activation).

## The design — `ENABLE_SHOPPING_CURRENCY_TRUTH` (default OFF, read per call)

Flag OFF: `extract_price_from_shopping` and `_seed_shortcircuit_candidates` execute
their exact HEAD bodies — every new branch is `if shopping_currency_truth_enabled():`
and skipped. Flag ON changes exactly three things, all in shared helpers:

1. **Resolve the display token BEFORE the strict check and the parse**
   (`_shopping_display_currency(price_str) -> Optional[str]`): if `detect_currency`
   returned `None`, take the `_RESIDUE_STRIP_RE` residue of the folded string and
   resolve it with `_normalize_currency_code(residue)` then `_GCC_SYMBOL_RESIDUE.get(residue)`;
   a hit becomes `detected_cur`. Nothing else changes: the existing parse now receives
   the currency it was always meant to receive (`22.500` with `BHD` → minor unit 3 →
   22.5; `8.750` with `KWD` → 8.75), the existing `item_converted` rule labels it, the
   existing `_convert_to_bhd` converts it. A `detect_currency` hit (incl. the bogus
   `USD` for `R$`) is left alone — that stays STRICT's job.
2. **Pend a known, non-target ISO code the effective table cannot convert**
   (`_shopping_unconvertible_foreign_iso(price_str, target) -> bool`): after step 1
   failed, if the upper-cased residue is a member of the known-currency vocabulary
   above and `!= target` → skip the candidate (`continue`), log
   `[SHOPPING_CURRENCY_TRUTH] pend unconvertible <CODE> for <name>`. With
   `ENABLE_EXTENDED_FALLBACK_RATES` ON step 1 already resolved it, so it converts —
   the two flags compose in the direction CLAUDE.md already documents.
3. **`local_bhd` requires host evidence** (`_shopping_bh_host_evidence(link) -> bool`,
   consulted only when the row would otherwise be `local_bhd`): a row with no
   evidence is stamped `converted_usd` instead — amount, url, retailer and every
   other key unchanged — and logged
   `[SHOPPING_CURRENCY_TRUTH] relabel local_bhd->converted_usd host=<host> reason=<reason>`.
   Evidence, in this order (dry-run over 23 URL shapes, every row pinned by test 10):
   - no link, or `_is_listing_url(link)` → **no** (`google.com/search?ibp=oshop`, the
     `build_retailer_url` search fallback);
   - `registry_tier(link) == "global"` → **no** (`amazon.com`, `bh.iherb.com` —
     the iHerb tension is the `#52` open product call, recorded, not decided here);
   - host ends `.bh`, or a subdomain label ∈ `{bh, bahrain, en-bh, ar-bh}`, or the first
     path segment ∈ `{en-bh, ar-bh, bh-en, bh-ar, bahrain-en, bahrain-ar, bahrain, bh}`
     → **yes** (`bolo.bh`, `bahrain.sharafdg.com`, `gcc.luluhypermarket.com/en-bh/`,
     `extra.com/en-bh/`, `sephora.me/bh-en/`, `noon.com/bahrain-en/`, `talabat.com/bahrain/`);
   - a subdomain label or first path segment naming ANOTHER GCC/Arab country
     (`sa, ksa, ae, uae, kw, qa, om, saudi, kuwait, qatar, oman, egypt, jordan` and the
     `en-sa / uae-en / …` locale forms — a superset of `_LOCALE_SEG_RE`) → **no**
     (`extra.com/en-sa/`, `noon.com/uae-en/`, `uae.sharafdg.com`, `ksa.swissarabian.com`);
   - `_registry_row_for_host(host, where=tier == "bahrain")` is a row → **yes**
     (a BH-only store with no marker: `alosraonline.com`, `noon.com/p`);
   - else → **no** (`bestbuy.com`, `amazon.ae`, `www.sharafdg.com`,
     `google.com/shopping/product/…`).
   The vocabulary is bounded and lives in one module-level frozenset per class; an
   entry is added only with a measured URL.

**What the flag must NOT touch:** `detect_currency`, `parse_price_string`/`parse_money`,
`_normalize_currency_code`, `_convert_to_bhd`, `_GCC_SYMBOL_RESIDUE`,
`_shopping_foreign_currency_signal`, `shopping_strict_currency_pend`, `is_price_showable`,
`_showable_source_methods`, `_GENUINE_BH_SOURCE_METHODS` (and its `eval_runner.py:400`
mirror), `should_cache_price`, the candidate dict's key set, the sort, the `title` pop.
The unit adds helpers and edits two loop bodies; nothing on the `extract_price_from_html`
spine moves — which is what makes the byte-identity harness meaningful here (Gates).

**Composition with `ENABLE_SHOPPING_STRICT_CURRENCY` (deliberate, pinned, to be written
into the CLAUDE.md block):** step 1 runs first, so a RESOLVABLE foreign GCC glyph
(`1,399 د.إ` on a BHD ask) now has `detected_cur='AED'` and STRICT's clause (b)
("detected None + foreign signal") no longer fires — the row CONVERTS to
`143.26 converted_usd`, exactly as `AED 1,399` already does on both flag states
(`test_m13_09_iso_aed_never_ships_target_raw`). With TRUTH OFF, STRICT still pends it
(M13-09 contract unchanged). STRICT keeps everything TRUTH cannot resolve: the `R$`
letter-dollar collision, unknown glyphs, and — with TRUTH OFF — the unresolved-glyph pend.

## Preserve

* Flag OFF ⇒ every row of the measured table above, byte-for-byte: 22500 / 8750 / 250 /
  32000 / 1299 `local_bhd`, the google-link `local_bhd`, `SAR 250 → 25.07 converted_usd`.
* The 6 pins in `tests/test_m13_shopping_strict_currency.py`, the 5 in
  `tests/test_shopping_source_method_t2.py`, the shopping/stash pins in
  `tests/test_m21_currency_parity.py` (`TestSeedStrictParity`, `TestArabicIndicResidue`)
  and the 2 in `tests/test_m13_shortcircuit_stash_parse.py`. Note they use
  `link="https://noon.com/p"` (registry `bahrain` row → still `local_bhd` with TRUTH ON)
  and `link="https://www.amazon.com/dp/x"` (`global` → `converted_usd` with TRUTH ON) —
  all run flag-OFF today and stay green; the flag-ON label for those links is pinned
  by this unit, not left implicit.
* The target-currency glyph ships on EVERY flag combination (`250 ر.س` / `١٢٣ ر.س` on a
  SAR ask, `1,399 د.إ` on an AED ask): the M13-09 over-rejection fix must not regress.
* `ENABLE_EXACT_PRICE_GATE` interplay: none — the unit reads no gate state; the
  `title` pop at `:9888` is untouched.
* No new `source_method` string, no new dict key, no change to `search_product_prices`'
  `shopping_region` contract (`serper_service.py:910-944`: country code or `us_fallback`).

## Red tests (`tests/test_shopping_currency_truth.py`)

Isolate extraction with `ENABLE_EXACT_PRICE_GATE=false` as the M13-09 file does; one
title-matched item; `monkeypatch.setenv` per flag; a BH-evidenced link
(`https://bahrain.sharafdg.com/product/x`) unless the test is about the link.

1. **RED — GCC display tokens, flag ON**, parametrized, target `'BHD'`:
   `'22.500 BD' → (22.5, 'BHD', 'local_bhd')`; `'8.750 KD' → (10.76, 'BHD', 'converted_usd')`;
   `'250 SR' → (25.07, 'BHD', 'converted_usd')`; `'32,000 QR' → (3305.6, 'BHD', 'converted_usd')`.
   RED today: `22500 / 8750 / 250 / 32000`, all `local_bhd`.
2. **PIN — the same four, flag OFF** (STRICT and EXTENDED unset) at today's values.
   Green today; this is the rung's flag-OFF identity for the parse half.
3. **RED — known foreign ISO, unconvertible, flag ON, EXTENDED OFF** ⇒ `None`,
   parametrized over the ten `FALLBACK_RATES_EXTENDED` codes as `f"{code} 1,299.00"`
   plus the review's `'TRY 1.299,00'`. RED today: every one ships `1299.0 local_bhd`.
4. **RED — the same with EXTENDED ON** (STRICT OFF, and again with STRICT ON) ⇒
   `'TRY 1.299,00' → (12.21, 'BHD', 'converted_usd')`. RED today (STRICT OFF ships
   1299 `local_bhd`; STRICT+EXTENDED pends).
5. **RED — a google.com link is never `local_bhd`, flag ON**: `{'price':'259.44',
   'source':'Best Buy', 'link':'https://www.google.com/search?ibp=oshop&q=…'}` ⇒
   `source_method == 'converted_usd'`, amount `259.44`, `url` unchanged; and
   `'22.500 BD'` on the same link ⇒ `(22.5, 'converted_usd')` — amount fixed AND
   label honest. RED today: `local_bhd`.
6. **PIN — the target-currency Arabic glyph SHIPS on all four (TRUTH × STRICT)
   states**: `'250 ر.س'` and `'١٢٣ ر.س'` on a SAR ask ⇒ `(250.0 / 123.0, 'SAR', 'local_bhd')`;
   `'1,399 د.إ'` on an AED ask ⇒ `(1399.0, 'AED', 'local_bhd')`. Green today; must stay.
7. **RED-adjacent composition pin** — `'1,399 د.إ'` on a BHD ask: TRUTH OFF + STRICT ON
   ⇒ `None` (unchanged); TRUTH ON, STRICT OFF or ON ⇒ `(143.26, 'BHD', 'converted_usd')`.
   The ON half is RED today.
8. **PIN — STRICT's letter-dollar rule survives**: `'R$ 1.399'` with TRUTH ON + STRICT
   ON ⇒ `None`; TRUTH ON + STRICT OFF ⇒ today's `526.02` (the collision is STRICT's,
   not this unit's).
9. **RED — the stash back door agrees** (reuse the `_seed` harness of
   `test_m21_currency_parity.py`, `svc._shopping_items_cache[NAME] = [...]` then
   `_seed_shortcircuit_candidates(NAME, kind="tier1_shopping", currency="BHD",
   shopping_region="bahrain")`): with TRUTH ON, `'22.500 BD'` seeds `value == 22.5`;
   the google-link `'259.44'` seeds `source_method == 'converted_usd'`; `'TRY 1.299,00'`
   (EXTENDED OFF) seeds nothing. RED today on all three. Flag OFF ⇒ today's values (pin).
10. **RED — host-evidence table, flag ON**, `'BHD 12.500'` parametrized over the 23
    dry-run URLs with the expected label: `local_bhd` for `bolo.bh`, `bahrain.sharafdg.com`,
    `gcc.luluhypermarket.com/en-bh/`, `www.luluhypermarket.com/en-bh/`, `extra.com/en-bh/`,
    `sephora.me/bh-en/`, `noon.com/bahrain-en/`, `talabat.com/bahrain/`, `alosraonline.com`,
    `noon.com/p`; `converted_usd` for the google search link, `google.com/shopping/product/`,
    `noon.com/uae-en/`, `extra.com/en-sa/`, `uae.sharafdg.com`, `www.sharafdg.com`,
    `amazon.ae`, `amazon.com`, `bestbuy.com`, `bh.iherb.com`, `talabat.com/uae/`,
    `ksa.swissarabian.com`, and a MISSING link (today's `build_retailer_url` search url
    is a listing url). RED today on every `converted_usd` row.
11. **PIN — the same table, flag OFF**: every row `local_bhd` (today's stamp).
12. **PIN — `is_price_showable(..., enforce_correctness=True)` on the flag-ON google
    row still pends `non_pdp_url`** (the relabel does not un-pend anything; that is
    W4-2's job and the reason for the ordering).

## Gates

1. TDD red-first (each RED above observed red, then green).
2. Comm gate: referencers of `price_service|structured_comparison_service|source_router|exchange_rate_service`
   = **306 test files** (measured; the five-symbol set the task names —
   `extract_price_from_shopping` 30, `detect_currency` 3, `parse_price_string` 7,
   `_GCC_SYMBOL_RESIDUE` 0, `price_service` 174 — unions to **190**; the stash lives in
   `structured_comparison_service`, hence the wider set) plus this unit's file. 605 test
   files exist in total.
3. **Byte-identity gate, with its scope stated honestly.**
   `scripts/verify_flag_byte_identity.py --proof-root C:/Users/SynAckITPC/Documents/AI/sc-w0-load/_proof --flags ENABLE_SHOPPING_CURRENCY_TRUTH --out <base|head>.json`
   at base `ed75dc70` → HEAD → base RE-RUN; compare the `results` arrays record-by-record
   (`:276/:293`, 1,656 records), never only the OVERALL digest (`:360`). The harness calls
   `extract_price_from_html` ONLY (`:244/:268`) — it never enters
   `extract_price_from_shopping`. What it proves for this unit: that the shared helpers
   this rung uses (`detect_currency`, `parse_price_string`, `_normalize_currency_code`,
   `_convert_to_bhd`, `_GCC_SYMBOL_RESIDUE`) were not moved — i.e. the "must NOT touch"
   list held. What it does NOT prove: flag-OFF identity of the shopping rung. That
   rests on tests 2, 6, 8, 9(OFF), 11 here + the 30 existing `extract_price_from_shopping`
   files + the four pin files named under Preserve. Say this in the PR, as PR #136 did.
4. Ruff + `py_compile` on both edited modules. 5. Full suite. 6. Fable review before
   commit. Agents never commit.

## MUTATION CHECKS ARE REQUIRED

Remove step 1 (the resolver) ⇒ tests 1, 4, 7(ON), 9a redden. Remove step 2 (the
known-ISO pend) ⇒ test 3 (and 9c) redden. Remove step 3 (host evidence) ⇒ tests 5,
9b, 10 redden. Remove the stash mirror only ⇒ test 9 reddens while 1/5 stay green
(that asymmetry is the proof the mirror is load-bearing). Force
`shopping_currency_truth_enabled()` to `True` ⇒ tests 2, 9(OFF), 11 redden (the
flag-OFF pins prove the gate is real). Delete one vocabulary entry
(`en-sa`) ⇒ the `extra.com/en-sa/` row of test 10 reddens. Record each.

## Activation

* Own window. Order within the currency family: `ENABLE_EXTENDED_FALLBACK_RATES`
  (additive, measured 0 losses) with/before this flag → **`ENABLE_SHOPPING_CURRENCY_TRUTH`**
  → then `ENABLE_SHOPPING_STRICT_CURRENCY` in ITS own window (PO-PRICE-TRUTH-03; with
  TRUTH already ON its remaining effect is the `R$` collision and unknown glyphs, so its
  canary reads clean-er than the M13 notes predict — expected, not a regression).
* **Hard order with W4-2:** this unit merges WITH or BEFORE W4-2 and this flag flips
  BEFORE `ENABLE_SHOPPING_DISCOVERY_URL_SPLIT` — the review's 1,032-of-1,484 rows are
  hidden today only by the `non_pdp_url` pend (test 12).
* **The KPI is expected to DROP.** Re-take `--kpi usable_exact_genuine` after the flip;
  the genuine-BH share falls to the host-evidenced subset — that is the metric becoming
  true. Canary lines: `[SHOPPING_CURRENCY_TRUTH] relabel …` (count by `reason=`) and
  `… pend unconvertible <CODE>`; a stream of `reason=no_bh_evidence` on a host Ahmed
  knows is Bahraini is a registry row to add, not a bug.
* Pre-existing cache rows are NOT relabelled by this unit (no migration): the 7 d
  genuine TTL rolls them within a week of the flip; `DELETE /api/v1/text/cache?q=…`
  (`#55`, `ENABLE_FLUSH_LIVE_PRICE_KEY`) covers a specific key. Publish the
  re-measured share the day it flips.
* Needs a funded Serper key to be exercised live; latent until then, and armed on the
  first cold compare after a top-up — so it merges before any top-up.

## Honest limit

* `converted_usd` is the honest label the codebase HAS for "showable, provenance not a
  verified Bahrain shelf"; for a `22.500 BD` string on an unverifiable host it is a
  misnomer, and the client appends `results.convertedUSD` copy to it
  (`SmartCompareApp/src/components/results/ResultsContent.tsx:147`,
  `ResultsScreen.tsx:446`). A third showable-not-genuine label would touch
  `_showable_source_methods`, the `eval_runner` mirror and the client enum — out of
  scope; **product call for Ahmed**, and W4-2's option (a) (resolve the merchant PDP)
  makes the evidence available instead.
* Only ISO-shaped tokens in the known vocabulary pend; `"TL"`, `"zł"`, `"kr"` still ship
  as the target currency exactly as today (STRICT's non-ASCII catch-all covers the glyph
  ones when it is on).
* The host vocabulary is bounded; an off-registry Bahraini `.com` store with no locale
  marker loses `local_bhd` on the SHOPPING rung only (its page-scrape rungs still earn
  `page_scrape*`). The fix is a registry row.
* The 857 / 1,032 / 1,484 cache numbers are the review's; the cache cannot be read
  offline here and was not re-measured. `should_cache_price` refuses listing urls at
  HEAD (`:9048`), so how those rows got in is not settled by this unit.
* No live Serper item was available; the URL shapes come from the registry's own
  `sample_url`s and the review's recorded rows.

## Spec disagreements with the review

1. **Expected amounts:** the function returns `round(amount, 2)` (`:9817`), so the
   tests assert `10.76` and `25.07`, not `10.7625` and `25.075`; `22.5` and `3305.6`
   are unaffected.
2. **Staleness:** B/C/D already PEND under `ENABLE_SHOPPING_STRICT_CURRENCY` and E
   already pends under `STRICT+EXTENDED` (measured table). Only A and F are un-remedied.
   This unit's value on B–E is pend → convert (and the EXTENDED-independent pend for E).
3. **Composition:** with TRUTH ON a resolvable foreign GCC glyph converts instead of
   pending under STRICT (test 7) — a deliberate consistency ruling with the ISO path,
   to be written into the CLAUDE.md M13-W2 block when the flag table is updated.
4. **"flag OFF ⇒ goldens byte-identical":** the harness cannot see this rung; identity
   is carried by pins (Gate 3). Said plainly rather than claimed.
5. **Report U5's "backfill/expire those cache rows in the same change":** not in this
   unit (Activation).
6. **Anchors:** `detect_currency` `:3464 → :3584`; `_shopping_foreign_currency_signal`
   `:9457-9462 → :9578`; the loop `:9572-9591 → :9714-9737`; `source_method` `:9682 → :9824`;
   `url` `:9678 → :9820`; `_GCC_SYMBOL_RESIDUE` now at `:9572`; the chokepoint pend
   `:1744-1755 → :1865`.

---

# FABLE REVIEW of this spec (2026-09-11) — ACCEPTED as written; rulings on the open points

1. **Composition with STRICT is ruled as the spec says:** TRUTH resolves the display token FIRST, so a
   resolvable foreign GCC glyph on a BHD ask CONVERTS (`1,399 د.إ` → `143.26 converted_usd`) exactly as
   the ISO form `AED 1,399` already does; STRICT keeps the letter-dollar collision, unknown glyphs, and —
   with TRUTH OFF — the unresolved-glyph pend (M13-09 contract unchanged). Test 7 pins it. At merge the
   CLAUDE.md M13-W2 block gets one sentence saying so.
2. **Host evidence for `local_bhd` (design step 3) is ACCEPTED**, with ONE condition to MEASURE, not
   assume: the spec keeps `noon.com/p` as `local_bhd` under the flag via the registry last resort, but
   its own measurement says `registry_tier("noon.com")` is `gcc` (first row wins). The `local_bhd`
   outcome therefore depends on `_registry_row_for_host(host, where=tier=="bahrain")` finding a SECOND,
   `bahrain`-tier noon row. The red phase must print that lookup for `noon.com` and `alosraonline.com`:
   if a bahrain row exists, the table row stands and is pinned; if it does not, `noon.com/p` becomes
   `converted_usd` under the flag, the table row changes, and the four Preserve pin files (which use
   `noon.com/p` flag-OFF) are unaffected — say which happened. Never let a "yes" row rest on an unread
   registry.
3. **The rounding disagreement is accepted** — tests assert the function's own `round(amount, 2)`
   output (`10.76`, `25.07`); the review's pre-rounding numbers are not the contract.
4. **Staleness accepted and to be stated in the PR in the spec's words:** only A (`22.500 BD`) and F (the
   google link) have no remedy today; B–E are pend → convert relative to STRICT/EXTENDED.
5. **The `converted_usd` misnomer for a native-BHD string on an unverifiable host is a PRODUCT CALL for
   Ahmed**, recorded in the PR and the handoff doc: options are (a) accept the label (client appends
   "converted" copy), (b) a third showable-not-genuine label (touches `_showable_source_methods`, the
   `eval_runner` mirror and the client enum — its own unit), or (c) W4-2 option (a) resolving the
   merchant PDP so evidence exists. This unit ships (a) and says so.
6. **Byte-identity gate:** run it per gate 3 and state its scope honestly — it proves the shared helpers
   on the `extract_price_from_html` spine did not move; the shopping rung's flag-OFF identity rests on
   tests 2/6/8/9(OFF)/11 plus the 30 existing `extract_price_from_shopping` files. Base run in a
   DETACHED checkout of `ed75dc70` under the agent's scratchpad; never `git checkout` in any worktree.
7. **Ordering with W4-2 is binding:** W4-1 merges WITH or BEFORE W4-2 and its flag flips BEFORE
   `ENABLE_SHOPPING_DISCOVERY_URL_SPLIT`. Test 12 pins that the relabel un-pends nothing.
8. Mutation table as specified, plus: force `_shopping_bh_host_evidence` to return True ⇒ every
   `converted_usd` row of test 10 reddens (the "remove step 3" check in its strongest form).


---

# FABLE REWORK RULING (2026-09-11, after the adversary's DEFECTIVE verdict) — BINDING

The adversary reproduced one MAJOR and three minors against the green on disk (unit 101 passed, comm gate empty, byte-identity equal). The design stands; the rulings below change the step-3 predicate's SCOPE and ORDER, add pins, and fix the PR text. Do everything here, nothing else. Rework from the CURRENT on-disk files (never `git checkout`; byte-snapshot before every mutation, sha-verify every restore).

## R1 (MAJOR) — step 3 is a BAHRAIN-shelf rule; apply its host vocabulary ONLY when the ask currency is BHD

Measured: `'250 SR'`, ask SAR / region saudi_arabia, link `https://ksa.swissarabian.com/products/x` → `(250.0, 'SAR', 'converted_usd')` under the flag, while the same string on a Bahrain host stays `local_bhd`; at `structured_comparison_service.py:6662` a `converted_usd` Tier-1 price is PARKED, so every non-Bahrain region would lose its native shopping short-circuit. The spec never addressed non-BHD asks.

Ruling: split step 3 into a region-AGNOSTIC pair and the BHD-only vocabulary.
- Region-agnostic (every ask): `no_link` and `listing_url` relabel to `converted_usd` — a missing link (the `build_retailer_url` search fallback) or a google search/listing URL is not a shelf for ANY region.
- BHD asks only (`(ask_currency or "").upper() == "BHD"`): the rest of the vocabulary exactly as built — global tier, other-country markers, BH markers, bahrain-tier registry row, fallthrough `no_bh_evidence` (order per R2).
- Non-BHD asks past the agnostic pair: the label stands as today (return True, no reason appended). Host evidence for SAR/AED/KWD/QAR/OMR asks is follow-up `PO-PRICE-TRUTH-01b` (a region-aware predicate: `.sa/.ae/…` TLDs, the region's own country tokens, the registry's currency field); record it in the PR text, do not build it.

Implementation: add a keyword parameter `ask_currency: str` to `_shopping_bh_host_evidence`; both call sites pass the loop's `currency` (the stash mirror already has `currency` in scope — verify, do not assume). Keep the helper name; update its docstring with the split.

Pins (front door AND stash, each): (a) SAR ask, region saudi_arabia, `'250 SR'` on `https://ksa.swissarabian.com/products/x` → `(250.0, 'SAR', 'local_bhd')` with the flag ON (unchanged from HEAD); (b) SAR ask, the google search link → `converted_usd` with reason `listing_url`; (c) SAR ask, link None → `converted_usd` with reason `no_link`; (d) BHD ask on the same ksa host stays `converted_usd` (already pinned in test 10 — keep). MUTATIONS: drop the BHD scoping (apply the vocabulary to every ask) → (a) reds; drop the agnostic pair for non-BHD asks → (b)/(c) red.

## R2 (minor) — conflicting markers resolve toward NO evidence: evaluate the other-country rung BEFORE the BH-marker rung

Measured: `https://uae.sharafdg.com/en-bh/product/x` and `https://bahrain.sharafdg.com/en-sa/product/x` both earned `local_bhd`. A URL that names another country anywhere (subdomain label OR first path segment) is contradictory evidence, and a contradiction must not mint a genuine, 7-day-cached, KPI-counted label. Reorder: `other_country` first, then the BH markers, then the registry row. Pin both conflicting URLs → `converted_usd` reason `other_country`. Re-check that the 23-row table is unchanged by the reorder (no existing row carries both markers) and that the adversary's X3 (registry ahead of other-country) still reddens noon/uae-en, extra/en-sa, talabat/uae.

## R3 (minor, PR text + docstring, NO code change) — compound price strings are a stated limit

`'From 22.500 BD'` (residue `FromBD`) and `'22.500 BD (was 30 BD)'` (residue `BD(wasBD)`) defeat step 1 and still parse as 22,500 with the flag ON. The residue transform is deliberately the M13-09 one (`_shopping_foreign_currency_signal`), unchanged; tokenising it is follow-up `PO-PRICE-TRUTH-01c`. State it in the honest-limit list of the PR text and in `_shopping_display_currency`'s docstring, and add ONE pin that documents today's outcome for `'From 22.500 BD'` under the flag (a pin OF the limit, labelled as such, so the canary reader is not surprised) — assert the current value, do not "fix" it.

## R4 (minor) — `no_host` joins the advertised `reason=` vocabulary

`'https://'`, `'not a url'`, `'javascript:alert(1)'` all relabel via `no_host`. Add it to the PR text's canary vocabulary and the helper docstring; pin one of them (caplog, see R5.6).

## R5 — pins for the rungs the adversary showed unproven

Each row must redden EXACTLY when its rung is deleted; run the deletion as a mutation and record the count:
1. `.bh` TLD rung: an OFF-registry `.bh` host, e.g. `https://example-store.bh/p/x` → `local_bhd` (bolo.bh is carried by the registry rung, so it proves nothing for the TLD rung).
2. BH subdomain-label rung: an OFF-registry host, e.g. `https://bh.example-store.com/p/x` → `local_bhd` (bahrain.sharafdg.com is a registry row).
3. Listing-url rung: `https://bolo.bh/search?q=x` → `converted_usd` reason `listing_url` (a listing URL on a BH-evidenced registry host: only the listing rung can relabel it).
4. Global-tier rung: `bh.iherb.com` already pins it; note in the test docstring that `amazon.com` relabels via the fallthrough and is a table row, not a rung pin.
5. Decimal-set half of `_shopping_known_currency_codes`: `'IQD 1,299'` (three-decimal; in NO rate table — measured: base 13 codes, extended adds AUD/CAD/CHF/DKK/EGP/JOD/NOK/PLN/SEK/TRY; `IQD`/`LYD`/`TND` are three-decimal-only) → pend (None) with the flag ON, EXTENDED off AND on. MUTATION: drop the `_THREE_DECIMAL_CURRENCIES | _ZERO_DECIMAL_CURRENCIES` half → the IQD row reds.
6. Canary log lines: one caplog pin per line — the relabel line carries `reason=listing_url` for the google row and `reason=no_host` for `'not a url'`; the pend line carries `IQD` — so the vocabulary the PR advertises is asserted.
7. Step 2's `code != target` clause and the `isascii()` guard: leave both (defensive; the ask currency is always in the base table today) and say so in the docstring; no pin required.

## Gates for the rework (standing rules, unchanged)
Unit file green with the flag unset AND `ENABLE_SHOPPING_CURRENCY_TRUTH=true`; the four Preserve pin files 32 passed; the 30 `extract_price_from_shopping` files green; comm gate head re-run over `.qa-w4/comm-set-W4-1-all.txt` with the identical two-node deselect, `comm -13 base head` empty; byte-identity base → head → base2 re-run exactly as before (detached scratch worktree under YOUR scratchpad, `git worktree remove` after; the harness is blind to the rung — say so again); ruff `E9,F63,F7,F82` + py_compile. Report every mutation with its count. Update the PR text (flag row, honest limits incl. R3, canary vocabulary incl. `no_host`, the R1 scope sentence, and the `PO-PRICE-TRUTH-01b/01c` follow-ups).
