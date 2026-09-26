# W4-14 — Arabic on the results surface: dimension labels through the catalog, a `lang` on the compare call, and a dark Arabic-verdict directive

Findings `PO-CATEGORIES-I18N-04`, `-10`, `-11`, `-02` (P2), `-05`, `-12` (P3).
Worktree `sc-w4-specs` (READ-ONLY for this spec), base **`61585c58`** (= origin/main, confirmed
`git rev-parse HEAD` → `61585c581e9deb78213f030260a765080f2e1dff`). Every line anchor below is at that SHA,
re-located by symbol (the review's anchors are from `76ace90`; table in §13).
Every number below was MEASURED in this run by running the real code offline: backend through
pytest under the netguard plugin (`[netguard] blocked 0 network attempt(s)` on every run), client
through jest with the REAL `i18next` instance and the REAL `en.json`/`ar.json` at `lng='ar'`. Probe
sources and raw outputs are frozen in `.qa-s68/specs/W4_14_probes/` (§15).

**Flags.**
* Client half (Part A): **unflagged** — React Native has no per-call env; it is OTA-gated. Every EN
  render stays byte-identical (pinned), so the only visible change is Arabic text for Arabic users.
* Backend half (Part B): **`ENABLE_ARABIC_VERDICT_OUTPUT`**, default OFF, read PER CALL. The route
  field and the threading are inert plumbing; the only behaviour fork (the prompt directive) sits
  behind the flag.
* Part C (a catalog-parity fence test): no flag, no runtime code.
* Part D (Arabic category tokens, `-02`): **recommended to move to W4-8** (§14 Q1); if kept here it
  gets its own flag `ENABLE_ARABIC_CATEGORY_TOKENS`.

---

## 0. What an Arabic user reads today (the one-paragraph truth)

At `61585c58`, with `lng='ar'` and the real catalogs, **72 of 72** dimension rows DimensionBars renders
across the 9 categories show the backend's raw English label (`Longevity`, `Craftsmanship`,
`Performance`…); the "limited data" row, the point-math delta fallback in DimensionBars and in the
"Where the runner-up wins" card, and the personalization chip also print English dimension names.
The `results.dimension.*` family has **0 keys in either catalog**. No compare route accepts a locale,
the client sends none, and no verdict prompt carries an output-language instruction. The price-numeral
half of the row (`-10`) is **no longer true**: PR #175 (W3-11bcd, `f9a6f197`) put every price through
one formatter with the `latn` digit policy, and the History price the finding compared against was
dead code (§1b). `0 of 58` Arabic queries classify deterministically (re-derived from the frozen
360-query corpus, §1d).

---

## 1. The defect, measured

### 1a. Dimension labels (`-04`) — HOLDS

Backend vocabulary (`app/services/scoring_service.py`, probe `test_a_dimension_vocabulary`):

| measure | value |
|---|---|
| `CATEGORY_DIMENSIONS` (`:25`) categories / rows / distinct dim keys | 9 / 54 / **49** |
| distinct dim keys labelled in `_DIMENSION_LABELS` (`:3262`, 49 entries) | 49 |
| labels containing a non-ASCII character | **0** |
| the review's "52" = 49 + the 3 core labels `Price`/`Reviews`/`Value` | 52 — arithmetic HOLDS, but `value_score` → public key `value` IS the core key, so the **distinct public keys** (dim key minus `_score`, ∪ `price`/`reviews`/`value`) are **51** |
| public keys `build_dimensions_v2` (`:3669`) can actually EMIT (every dim scored, 9 categories) | **45** keys / 44 distinct labels (`review` and `reviews` both render `Reviews`) |
| public keys that can never reach the client at HEAD | 6: `cpw` (fashion's 6th dim, cut by the 5-contextual cap at `:3711`), and the 5 value proxies `serving_value`, `perf_value`, `results_value`, `multi_value`, `wear_value` (skipped by the `value_` test at `:3717`) |

Per category, `build_dimensions_v2` emits `price, reviews, value` + 5 contextual keys (full list in
`W4_14_probes/probe_out/dims_reach.json`). The dimension dict is
`{"key": public_key, "label": label, ...}` (`_dim_from_category_lookup` `:3324`, label `:3394`,
`public_key` `:3396`; the three core builders `_dim_price` `:3061`, `_dim_reviews` `:3093`,
`_dim_value` `:3135` hard-code `"Price"/"Reviews"/"Value"`).

Client, REAL i18next at `lng='ar'` (probe `w414.probe.test.tsx`):

| measure | value |
|---|---|
| `results.dimension.<key>` present, over the 45 reachable keys | **en 0 / ar 0** (family size 0 in both catalogs) |
| `t('results.dimension.longevity')` under ar | returns the key itself (`results.dimension.longevity`) |
| DimensionBars rows rendered (9 categories, expand row pressed) | **72**, of which **72** show the raw English backend label |
| `InsufficientRow` (`DimensionBars.tsx:227`) for `{key:'longevity', label:'Longevity', data_insufficient:true}` | `Longevity` (English) + the Arabic `results.dimensions.limited_data` caption |
| DimensionBars delta caption, `{key:'projection', label:'Projection', delta_text:'+18pt'}` → `safeDelta` fallback to `label` (`:286`) | the row renders `Projection` TWICE (label + fallback caption), both English |
| `RunnerUpWinsCard` `dimRowText` (`RunnerUpWinsCard.tsx:67-68`), `delta_text:'+18pt'` | `Projection` (English) |
| `PersonalizationChip` (`PersonalizationChip.tsx:46`), shift `{dim_display:'longevity'}` | `↑ longevity` (English; the backend sends `DIMENSION_DISPLAY_NAMES` `:1226`, 49 lowercase English entries, 0 non-ASCII, and NO key) |
| the `results.spec.*` precedent (`CategoryProfile.tsx:138`, `t(\`results.spec.${f.key}\`, {defaultValue: f.label})`) | 68 keys, full parity (unchanged since the review) |

Render sites of a dimension label on the results surface at HEAD (grep of `src/components/results`,
`src/components/hero`, `src/screens/ResultsScreen.tsx`): `DimensionBars.tsx:227`, `:286` (fallback),
`:313`; `RunnerUpWinsCard.tsx:68` (fallback); `PersonalizationChip.tsx:46` (different vocabulary,
see §4 A6). `ResultsScreen.tsx:601` `SCORE_LABELS` is declared and never read (dead).

### 1b. Price numerals (`-10`) — CHANGED by #175 (W3-11bcd, `f9a6f197`, merged `4eeb18aa`)

| claim at `76ace90` | at `61585c58` (measured) |
|---|---|
| `ResultsContent.tsx:143` builds `localizedCurrency(...) ${amount.toLocaleString()}` from the DEVICE locale | the closure `formatPrice` (`ResultsContent.tsx:134`) calls `formatAmountWithCurrency` = `formatPrice` (`src/utils/formatNumber.ts:96`) at `:145`: amount first, ISO minor unit, `APP_DIGIT_SYSTEM='latn'`. `formatPrice(12.345,'BHD',t_ar)` **=== `'12.345 د.ب'`**, `formatPrice(250,'SAR',t_ar)` **=== `'250.00 ر.س'`**, `formatPrice(19.9,'EUR',t_ar)` = `'19.90 EUR'` |
| `HistoryScreen.tsx:715` renders `${amount.toFixed(2)} ${glyph}` | that `formatPrice` was **DEAD at `76ace90`** (`git show 76ace90:…/HistoryScreen.tsx`: defined at `:709`, zero call sites) and #175 deleted it. History shows no per-comparison price at all. Its only money string is the hero `history.hero.savings` `~{{amount}} د.ب …` with `amount = savingsBhd.toFixed(0)` (`HistoryScreen.tsx:181-184`, a deliberate whole-dinar aggregate) |
| Results and History disagree on numeral system | digit class under ar: Results price `{ascii:true, arabicIndic:false}`; History savings, History count, Home savings count: all `{ascii:true, arabicIndic:false}`. **One digit system.** |
| `toLocaleString()` without a locale on a price | `grep toLocaleString src` → 2 sites, both with an explicit `'en-US'` (`LoadingRings.tsx:84`, `StatBlock.tsx:29`), neither a price |

So the row's second jest claim ("a price string under `lng='ar'` does not mix numeral systems between
Results and History") is **GREEN at HEAD**. This unit turns it into a PIN (§7 T13-T15) so the property
cannot regress; it adds no price code.

### 1c. Locale plumbing (`-11`) — HOLDS

Probe `test_b_route_and_service_contracts` / `test_c_prompts_have_no_output_language`:

| surface | measured at HEAD |
|---|---|
| `TextCompareRequest` fields (`app/api/text_routes.py:217`) | `include_pros_cons, include_reviews, include_specs, product_a, product_b, query, region, selected_category` — no locale |
| `TextCompareRequest(product_a='a', product_b='b', lang='ar')` | constructs fine; `model_dump()` has no `lang` (`model_config['extra']` is unset = pydantic default **ignore**) — an OTA that sends `lang` today is silently ignored, never a 422 |
| query params of `GET /api/v1/text/compare` (`:532`) and `GET /api/v1/text/compare/stream` (`:697`) | `nocache, product_a, product_b, pros_cons, q, region, reviews, selected_category, specs` — no locale (FastAPI ignores unknown query params) |
| `POST /api/v1/text/compare` (`:354`) | one body param (`body`) |
| `compare_from_text` (`structured_comparison_service.py:3484`), `compare_from_text_streaming` (`:4150`) | params end at `explicit_pair` — no locale |
| `generate_comparison` (`extraction_service.py:2313`), `build_verdict_prompt` (`:1961`) | no locale param |
| client (`src/services/api.ts`): REST `baseParams` (`:609`), SSE `URLSearchParams` (`:750-760`), `compareTextPair` body (`:887`) | `region`, `selected_category`, `nocache`, the query/pair — no language. `grep -n "language\|Accept-Language" api.ts` → only the demographics type (`:1059`, `:1068`) |
| output-language instruction in the 9 verdict prompts (`build_verdict_prompt`, every category) | **0** (`/in arabic|respond in|write in|output language/i`; one `answer in` hit per category is `"…wants the answer in seconds…"` from the pain-workflow block — a false positive, recorded in `verdict_match.json`) |
| the word "arabic" in any verdict prompt | 0 in all 9 |
| `_build_cohort_priors_block` (`:1811`) with `language:'Arabic'`, `ENABLE_COHORT_PERSONALIZATION=true` | emits `USER CONTEXT: Country=Bahrain, Language=Arabic` (`:1856`/`:1860`) — metadata, NOT an output instruction; flag false → empty block |
| verdict prose fields the model writes (`COMPARISON_SYSTEM` `:1004`) | `winner_reason`, `key_tradeoff`, `value_context.{product_0,product_1}`, `best_for.{…}`, `product_{0,1}_{pros,cons}`, `specs_comparison.*`, `personalized_insights[].insight` — all English |

### 1d. Arabic category tokens (`-02`) — HOLDS (re-derived from the frozen corpus)

Probe `test_d_arabic_category_tokens` + `test_g_corpus_arabic_rows`:

| measure | value |
|---|---|
| `_CATEGORY_SYNONYMS` (`extraction_service.py:1083`) keys / non-ASCII keys | 41 / **0** |
| W4-8's frozen 360-query corpus (`.qa-s68/specs/W4_8_probes/corpus_gcc_360.json`, sha256 `0852f556…d3ae91`, identical to W4-8's recorded hash) — Arabic-script rows | **58** (55 pure Arabic, 3 mixed; per truth: electronics 7, grocery 8, supplements 5, makeup 5, skincare 5, haircare 6, fragrances 8, fashion 9, other 5) |
| of those 58, `classify_category_from_text` (`:1167`) returns non-`other` | **0** — the review's `0 of 58` HOLDS exactly |
| this spec's own 18-query sample (2 per category + 2 mixed) | 1 of 18 non-`other`, and that one (`perfume عطر…`) hit the ENGLISH token `perfume` |
| `canonicalize_category` (`:1136`) of 5 Arabic category words (`عطور`, `عطر`, `إلكترونيات`, `مكملات`, `أزياء`) | all `other` |

A prototype (defined in the probe only, never app code; tokens in `W4_14_probes/proto_ar_tokens.json`,
75 tokens, a clitic-tolerant `(?:^|\s)(?:وال|بال|فال|كال|لل|ال|و|ب|ل|ف|ك)?TOKEN(?=$|\s|punct)` match,
consulted ONLY after the ASCII sweep returns nothing) over the same corpus: **34 correct / 21 other /
3 wrong** of 58 Arabic rows; **0 of 302** non-Arabic rows change. The 3 wrong rows are exactly the
ambiguity class W4-8 owns: `ساعة ابل سيريس 10 …` (a smartwatch) → `fashion` via `ساعة`;
`كريم اساس …` (foundation, bare-alef spelling) → `skincare` via `كريم`; `سيروم فيتامين سي …` → `supplements`
via `فيتامين` (the Arabic twin of `PO-CATEGORIES-I18N-06`). On the explicit_pair path a deterministic
hit OUTRANKS the user's chip (`_resolve_pair_category` `scs:440`, `name_cat` `:467`), so a wrong
Arabic token silently overrides a correct chip — the precise failure W4-8 exists to stop. Hence §14 Q1.

### 1e. `category_switched` (`-05`) — HOLDS (product call)

`grep -rn "category_switched\|categorySwitched" SmartCompareApp/src` → `types.ts:296` (the type),
`ResultsScreen.tsx:798` (the comment recording its deliberate deletion per the no-info-banners rule),
and the two catalog values (`en.json:890`, `ar.json:887`). **0 render sites.** Whether to show a
disclosure or make the chip authoritative is a product decision (§14 Q4); this unit does not touch it.

### 1f. Plurals (`-12`) — PARTLY CHANGED

| part | at HEAD |
|---|---|
| `ResultsAccordion.tsx:662-668` passes a formatted STRING as `count` to `results.reviews.ratingWithCount` | still true, but now **deliberate**: #175 ruling R10 (comment at `:665-666`: "a STRING count keeps the grouping separator (ratingWithCount has no plural family)"). Not a defect to reopen here (§12) |
| `referrals.bonus.expiresIn{Days,Hours,Minutes}` carry only `_one`/`_other` in BOTH catalogs | HOLDS. Real i18next, ar: `expiresInDays` renders ENGLISH for counts **0, 2, 3, 11** (Arabic for 1 and 100). Zero call sites in `src` (latent); the W3-11 fence allowlists all three (`__tests__/i18n/pluralFamilies.fence.w311.test.ts` `ALLOWLIST_INCOMPLETE`, comment "Owned by W3-11 14(b): delete or complete, then drop from here") |
| `referrals.share.maxReached` | no plural family; called once with `count: LIFETIME_CAP` (`ShareBottomSheet.tsx:335`, a constant) — not a live plural defect |

---

## 2. Red-claim status (the row's claims, verbatim)

| claim | status | measurement |
|---|---|---|
| "every rendered dimension label resolves through a `results.dimension.*` key present in BOTH catalogs (RED: the family does not exist)" | **HOLDS** | family size en 0 / ar 0; 45 reachable keys, 0 covered; 72/72 rendered rows raw English under ar |
| "a price string under `lng=ar` does not mix numeral systems between Results and History" (RED) | **CHANGED — now GREEN** (#175 `f9a6f197`) | Results `'12.345 د.ب'` ASCII; History savings/count ASCII; no Arabic-Indic anywhere; the History price the review cited was dead code at `76ace90` |
| "52 dimension labels render raw English" | **HOLDS, number refined** | 49 dim keys + 3 core = 52 rows of vocabulary; 51 distinct public keys; 45 reachable at HEAD; every reachable one renders English |
| "every verdict an Arabic user reads is English (no route accepts a locale, the client sends none, no prompt asks for Arabic)" | **HOLDS** | §1c: 0 locale fields/params on 3 routes, 0 in the service/prompt signatures, 0 in the client requests, 0 output-language directives in 9 verdict prompts |
| `-02` "0 of 58 Arabic/mixed-script queries classify" | **HOLDS** | 0/58 on the frozen corpus (sha matches W4-8) |
| `-05` category_switched rendered nowhere | **HOLDS** | 0 render sites |
| `-12` plural sites | **PARTLY CHANGED** | referral expiry English fallback HOLDS (0/2/3/11); the ratingWithCount string count is now a recorded #175 ruling |

---

## 3. What already exists — reuse it, do not reinvent it

* **Echo-guard catalog resolver** — `localizedCurrency(code, t)` (`src/utils/currencyDisplay.ts:17`):
  `const key = \`currency.${code}\`; const out = t(key, {defaultValue: code}); return out === key ? code : out;`.
  It is correct under all THREE t() shapes the suite uses: the real i18next (returns the catalog
  value), the per-file mock that returns `defaultValue ?? key`, and the GLOBAL mock
  `__mocks__/react-i18next.ts` whose `stableT` IGNORES `defaultValue` and returns the key. Six
  DimensionBars suites run on that global mock (`__tests__/components/DimensionBars.{test,delta_hero,
  hero_expand,insufficient,silent_omission,snapshot}.test.tsx`, `jest.mock('react-i18next')` count 0 in
  each, measured). A bare `t('results.dimension.'+key, {defaultValue: label})` would render the KEY
  there and break them; the echo guard is mandatory.
* **The `results.spec.*` precedent** — `CategoryProfile.tsx:138`, 68 keys, full EN/AR parity.
* **One formatter for prices/digits** — `formatNumber.ts` (`formatPrice` `:96`, `APP_DIGIT_SYSTEM`,
  `CURRENCY_FRACTION_DIGITS`); the W3-11 digit fence `__tests__/i18n/digitPolicy.w311.test.ts`.
* **The i18n fences** — `__tests__/i18n.test.ts` (EN/AR key-set equality), `__tests__/i18n/no-deleted-keys.test.ts`
  (equal key COUNT), `__tests__/i18n/no-missing-referenced-keys.test.ts` (static `t('…')` keys — template
  literals are excluded by design, so `t(\`results.dimension.${key}\`)` needs this unit's own fence),
  `__tests__/i18n/pluralFamilies.fence.w311.test.ts`, `__tests__/copy-policy.test.ts`
  (`src/i18n/.copy-policy.json` banned/scary vocab; the §4 A2 proposal was checked against it: **0 hits**
  in either language).
* **Real-catalog i18next harness** — `__tests__/i18n/digitPolicy.w311.test.ts` / `plurals.test.ts`
  (`i18next.createInstance()` + `init({lng:'ar', fallbackLng:'en', resources})`). For component renders
  under the real catalog, wrap it in a `jest.mock('react-i18next', …)` factory that `require`s i18next
  and both JSON files inside the factory (the working pattern is `W4_14_probes/jest/w414.probe.test.tsx`).
* **Cross-language fence precedent** — `tests/test_events_allowlist_superset.py:30` reads
  `SmartCompareApp/src` from a backend test (CI checks out the whole repo).
* **Flag idiom** — `_gpt_winner_lever_enabled()` (`extraction_service.py:2106`): read live via
  `os.environ.get(...).strip().lower() in ("1","true","yes","on")`, never memoised.
* **Verdict prompt capture harness** — `tests/test_verdict_prompt_unification.py:36-75`
  (`_capture_prod_system_msg`: `patch.object(extraction_service, "get_client")` + a fake router; the
  probe's `_capture` extends it to the user message and the call kwargs).
* **Body max-length idiom** — `tests/test_m13_25_compare_body_maxlength.py` (model-level + HTTP 422).
* **"Omit when unset" request idiom** — `api.ts:611-616` (`...(options?.selected_category && {...})`),
  used at all three send sites.

---

## 4. The design

### Part A — client (unflagged, OTA-gated)

**A1. `src/utils/dimensionLabel.ts` (new).**
```ts
type TranslateFn = (key: string, options?: Record<string, unknown>) => string;
export function localizedDimensionLabel(key: string | null | undefined, label: string, t: TranslateFn): string {
  if (!key) return label;
  const k = `results.dimension.${key}`;
  const out = t(k, { defaultValue: label });
  return out === k || typeof out !== 'string' || out.length === 0 ? label : out;
}
```
Exactly the `localizedCurrency` echo guard. An uncatalogued key (a future backend dim) falls back to the
backend label — today's behaviour.

**A2. Catalogs.** Add the 51 `results.dimension.<public_key>` keys to BOTH `en.json` and `ar.json`
(all 51, not only the 45 reachable: the 6 unreachable ones are one cap/ordering change away from the
screen, and Part C's fence keys on the full 51). **EN values echo the backend label byte-for-byte**
(so every EN render is unchanged); AR values below are a PROPOSAL (checked: 0 copy-policy hits; max 25
chars; reused the existing `results.spec.*` Arabic where the concept is identical — `dosage`, `finish`,
`form`, `scent`, `style`=`الطراز`; `longevity` deliberately `الثبات`, not the spec key's fragrance-only
`ثبات العطر`, because the dimension is shared by makeup and fragrances). **A native review is required
before the OTA** (§14 Q6); the red/green agent writes these values verbatim.

| key | EN (= backend label) | AR (proposal) | reachable at HEAD |
|---|---|---|---|
| `actives` | Active ingredients | المكونات الفعالة | yes |
| `availability` | Availability | التوفر | yes |
| `build` | Build | التصنيع | yes |
| `build_quality` | Build quality | جودة التصنيع | yes |
| `character` | Character | الطابع | yes |
| `cpw` | Cost per wear | التكلفة لكل استخدام | no (cap) |
| `craft` | Craftsmanship | الحرفية | yes |
| `dietary` | Dietary fit | الملاءمة الغذائية | yes |
| `dosage` | Dosage | الجرعة | yes |
| `durability` | Durability | المتانة | yes |
| `ecosystem` | Ecosystem | المنظومة | yes |
| `efficacy` | Efficacy | الفعالية | yes |
| `evidence` | Evidence | الأدلة | yes |
| `feature` | Features | المزايا | yes |
| `feature_match` | Feature match | مطابقة المزايا | yes |
| `finish` | Finish | اللمسة النهائية | yes |
| `fit` | Fit | المقاس | yes |
| `form` | Form | الشكل | yes |
| `formulation` | Formulation | التركيبة | yes |
| `function` | Function | الوظيفة | yes |
| `futureproof` | Future-proofing | مواكبة المستقبل | yes |
| `hair_match` | Hair match | ملاءمة الشعر | yes |
| `heritage` | Heritage | العراقة | yes |
| `ingredient` | Ingredients | المكونات | yes |
| `ingredient_safety` | Ingredient safety | أمان المكونات | yes |
| `longevity` | Longevity | الثبات | yes |
| `multi_value` | Multi-use value | قيمة الاستخدامات المتعددة | no (value proxy) |
| `nutrition` | Nutrition | القيمة الغذائية | yes |
| `perf_value` | Performance vs value | الأداء مقابل السعر | no (value proxy) |
| `performance` | Performance | الأداء | yes |
| `presentation` | Presentation | التقديم | yes |
| `price` | Price | السعر | yes |
| `projection` | Projection | الانتشار | yes |
| `reliability` | Reliability | الاعتمادية | yes |
| `results` | Results | النتائج | yes |
| `results_value` | Results vs value | النتائج مقابل السعر | no (value proxy) |
| `review` | Reviews | التقييمات | yes |
| `reviews` | Reviews | التقييمات | yes |
| `safety` | Safety | الأمان | yes |
| `scalp` | Scalp | فروة الرأس | yes |
| `scent` | Scent | الرائحة | yes |
| `sensory` | Sensory | الإحساس عند الاستخدام | yes |
| `serving_value` | Serving value | قيمة الحصة | no (value proxy) |
| `shade` | Shade range | درجات اللون | yes |
| `skin_compat` | Skin compatibility | ملاءمة البشرة | yes |
| `style` | Style | الطراز | yes |
| `taste` | Taste | الطعم | yes |
| `trust` | Trust | الموثوقية | yes |
| `value` | Value | القيمة | yes |
| `versatility` | Versatility | تعدد الاستخدامات | yes |
| `wear_value` | Wear value | قيمة الاستخدام | no (value proxy) |

The dimension family adds exactly 51 keys to each catalog (957 today, measured); A4 adds 12 more to each
(4 missing forms × 3 referral families) — 1020 each, or 1002 each if Q5 deletes the three families instead.
`no-deleted-keys` compares the two counts, not a constant; no absolute key count is pinned anywhere
(grep of `__tests__` for `toBe(9xx)`/`toHaveLength(9xx)` → none).

**A3. Route the four label sites through A1.**
* `DimensionBars.tsx:313` `DimensionRow` label → `localizedDimensionLabel(key, label, t)` (`t` is already
  in scope, `:244`).
* `DimensionBars.tsx:227` `InsufficientRow` → same (`t` in scope `:224`).
* `DimensionBars.tsx:286` `safeDelta(delta_text, label)` → `safeDelta(delta_text, <the localized label>)`
  — the point-math fallback prints the localized label; a qualitative `delta_text` still passes through
  untouched (it is backend English prose; §11).
* `RunnerUpWinsCard.tsx:67-68` `dimRowText(d)` → `dimRowText(d, t)` returning
  `safeDelta(d.delta_text, localizedDimensionLabel(d.key, d.label, t))` (`t` is in scope in the component).
Nothing else in either file moves: filters, winner paint, testIDs, the hero cap, the score hooks.

**A4. Referral expiry plurals (`-12` residue).** Complete the three families with the six Arabic CLDR
forms (`_zero,_one,_two,_few,_many,_other`) in `ar.json` and add the same six-form keys' EN twins
(`_zero/_two/_few/_many` echo `_other`, as `history.hero.count_*` does) so the EN/AR key-set equality
holds; then **drop the three entries from `ALLOWLIST_INCOMPLETE`** in
`__tests__/i18n/pluralFamilies.fence.w311.test.ts` (a tightening its own comment asks for). Alternative
the orchestrator may prefer: delete the three dead families from both catalogs (0 call sites) — §14 Q5.

**A5. `lang` on the three text compare requests (`src/services/api.ts`).** A one-line reader
`currentOutputLang(): 'ar' | undefined` = `(i18next.language || '').toLowerCase().startsWith('ar') ? 'ar' : undefined`,
importing the default `i18next` instance from the `i18next` package (the app's `src/i18n/index.ts`
initialises that same default instance; importing the package, not `../i18n`, avoids pulling
`expo-localization`/AsyncStorage init into `api.ts`'s importers). Send it with the omit-when-unset idiom:
`...(lang && { lang })` in `baseParams` (`:609`), `if (lang) params.set('lang', lang)` next to `:760`, and
`...(lang && { lang })` in the `compareTextPair` body (`:893-899`). **EN or unset → no `lang` key at all →
the request is byte-identical to HEAD** (pinned, §7 T21). The current backend (and every older one)
ignores it (§1c). `/url/compare`, `/image/identify` and `/text/quick` are out of scope (§14 Q3).

**A6. NOT in this unit:** `PersonalizationChip` (`:46`) prints `dim_display`, a separate 49-entry
lowercase English vocabulary (`DIMENSION_DISPLAY_NAMES`) with no key in the payload
(`applied_shifts: [{dim_display, direction}]`, `types.ts:431`). Localizing it needs an additive backend
field (e.g. `dim_key`) — §14 Q2.

### Part B — backend, `ENABLE_ARABIC_VERDICT_OUTPUT` (default OFF, read per call)

**B1. Reader + normaliser** in `extraction_service.py` next to `_gpt_winner_lever_enabled` (`:2106`):
* `arabic_verdict_output_enabled() -> bool` = `os.environ.get("ENABLE_ARABIC_VERDICT_OUTPUT", "").strip().lower() in ("1","true","yes","on")`, read on every call.
* `normalize_output_lang(raw) -> Optional[str]`: non-str/empty → `None`; `raw.strip().lower()`, primary
  subtag before `-`/`_`; returns `"ar"` or `"en"`, anything else → `None`. Pure.

**B2. Route field (inert).** `TextCompareRequest` gains `lang: Optional[str] = Field(default=None, max_length=8)`
(M13-25 bounding style — an over-long value is a 422 exactly like the other bounded fields; the phones
never send it). `text_compare_get` and `text_compare_stream` gain
`lang: Optional[str] = Query(None, max_length=8, description="UI language for generated prose (en|ar)")`.
Each handler computes `output_lang = normalize_output_lang(lang)` and passes
`**({"output_lang": output_lang} if output_lang else {})` to `compare_from_text` /
`compare_from_text_streaming` — **conditional kwargs, so a request without `lang` (every 561d2cba phone)
produces a service call byte-identical to HEAD**, and route tests whose fake services have fixed
signatures (`tests/test_category_selection.py:310` reads `call_args`) are unaffected.

**B3. Threading (inert).** `compare_from_text`, `_compare_from_text_impl`, `compare_from_text_streaming`
and `generate_comparison` each gain a trailing `output_lang: Optional[str] = None`. The three
`generate_comparison` call sites in `structured_comparison_service.py` (sync `:3922`, stream `:4687`, the
self-critique regen `:8763`) and the two `regen_args=dict(...)` builders (`:3940`, `:4713`) pass it with
the SAME conditional-kwargs form, so the no-lang path is kwarg-identical (fakes with fixed signatures:
`tests/test_self_critique_orchestration.py:98`, `tests/test_security_regression.py:1275` are
`*args, **kwargs` today, but the conditional form keeps any stricter fake safe). `url_extraction_service.py:628`
is NOT touched (default `None`).

**B4. The one behaviour fork.** In `generate_comparison`, immediately AFTER the `_gpt_winner_lever_enabled()`
block (`:2391-2392`) and BEFORE the user message is built:
```python
if output_lang == "ar" and arabic_verdict_output_enabled():
    system_msg += _ARABIC_OUTPUT_DIRECTIVE
    logger.info("[ARABIC_VERDICT_OUTPUT] directive appended category=%s", category)
```
`_ARABIC_OUTPUT_DIRECTIVE` (module constant, exact text):
```
\n\n## Output language\nThe reader of this verdict reads Arabic. Write EVERY human-readable string value in the JSON in Modern Standard Arabic: winner_reason, key_tradeoff, both value_context sentences, both best_for sentences, every item of product_0_pros, product_0_cons, product_1_pros and product_1_cons, every item of specs_comparison, and every personalized_insights[].insight.\nKeep EXACTLY as given, never translated or transliterated: every JSON key, the winner_declaration value (the product name), product and brand names, model numbers, units, currency codes, and personalized_insights[].focus_area.\nWrite every number with Western digits (0-9).\nEvery other rule above still applies unchanged.
```
Appending it LAST makes the flag-ON prompt `HEAD_prompt + DIRECTIVE` exactly (a suffix gate, §9.3) and
keeps the static per-category prefix intact for OpenAI prompt caching. "Western digits" matches the
client's signed `APP_DIGIT_SYSTEM='latn'`.

**Why OFF is byte-identical:** with the flag OFF the only new work is the `output_lang == "ar"`
comparison and (only when it is `"ar"`) one `os.environ.get`; `system_msg`, `user_msg`, the model, the
kwargs and the response handling are the HEAD values for every input (gate §9.3 over 18 cells × 3
`output_lang` values). With the flag ON and `output_lang` in `{None, "en"}` the same holds. The route
field and threading change no response byte.

**Must NOT touch (Part B):** `COMPARISON_SYSTEM`, `build_verdict_prompt`, `_build_preferences_prompt`,
`_build_cohort_priors_block` (its `Language=` metadata line stays metadata), the pain-workflow/exemplar
loaders, `_verdict_safe_product`, the specs/reviews/pros-cons extraction prompts and their caches (§11),
`response_builder` (factual verdict, `_compose_delta_text`), `strip_score_internals`, the critique and
trust-validation services, `url_extraction_service`, `image_routes`, `url_routes`.

### Part C — cross-language catalog fence (no flag, test-only)

`tests/test_dimension_label_catalog_parity_w414.py` reads `SmartCompareApp/src/i18n/{en,ar}.json` and
`scoring_service` so a NEW backend dimension cannot ship unlocalized and an EN catalog value cannot
silently shadow a renamed backend label (the EN echo makes the catalog, not the backend, the rendered
source for known keys — this fence is what keeps them equal).

### Part D — Arabic category tokens (`-02`) — CONDITIONAL on §14 Q1

Recommended: move to W4-8 (same classifier sweep `extraction_service.py:1186-1189`, same corpus gate,
same chip-override hazard, and W4-8's spec already forbids editing `_CATEGORY_SYNONYMS` because
`canonicalize_category` shares it). If Fable keeps it here: a separate `_CATEGORY_SYNONYMS_AR` map
consulted ONLY when the ASCII sweep returned nothing and `ENABLE_ARABIC_CATEGORY_TOKENS` is ON; clitic
tolerant match as the prototype; `canonicalize_category` untouched. The prototype's 3 wrong rows must be
fixed or excluded before it ships (`ساعة` needs a device veto, `كريم اساس` needs the bare-alef twin,
`سيروم` must outrank `فيتامين` — the Arabic twin of `-06`), and its equality gate is W4-8's
360-corpus record hash (`b76fcef9…` at HEAD — W4-8's recorded figure, not re-measured by this spec) with the flag OFF, plus "0 of 302 non-Arabic rows change"
with it ON.

---

## 5. Files

**Touch (Part A):** `SmartCompareApp/src/utils/dimensionLabel.ts` (new),
`SmartCompareApp/src/components/results/DimensionBars.tsx` (`:227`, `:286`, `:313` only),
`SmartCompareApp/src/components/results/RunnerUpWinsCard.tsx` (`dimRowText` + its one call),
`SmartCompareApp/src/i18n/en.json`, `SmartCompareApp/src/i18n/ar.json` (51 dimension keys; the referral
plural forms), `SmartCompareApp/src/services/api.ts` (three send sites + the reader),
`SmartCompareApp/__tests__/i18n/pluralFamilies.fence.w311.test.ts` (drop 3 allowlist entries only), the
new test files of §7.
**Touch (Part B):** `app/api/text_routes.py`, `app/services/structured_comparison_service.py`
(signatures + 3 call sites + 2 regen_args), `app/services/extraction_service.py` (reader, normaliser,
constant, `generate_comparison` signature + the 3-line block), the new test files.
**Must NOT touch:** everything listed under "Must NOT touch (Part B)"; `formatNumber.ts`,
`currencyDisplay.ts`, `ResultsContent.tsx`, `HistoryScreen.tsx`, `ResultsAccordion.tsx`,
`PersonalizationChip.tsx`, `CategoryProfile.tsx`, `_deltaText.ts`, `scoring_service.py` (no label or key
changes), `_CATEGORY_SYNONYMS`/`classify_category_from_text` (unless Q1 keeps Part D), every existing
snapshot file (no `jest -u`), `app.json`/`eas.json`/`package.json` (the OTA must stay native-compatible),
`requirements*.txt`, lockfiles, `tests/.pre_impl_failures.txt`.

---

## 6. Preserve (every test that pins the touched code — measured by grep)

Client (all green at HEAD — the 30-suite / 322-test preserve run below):
`__tests__/components/DimensionBars.{test,delta_hero,hero_expand,insufficient,silent_omission,snapshot}.test.tsx`
(global echo mock — the reason for the echo guard), `__tests__/DimensionBars.{bundle-c,deltaGuard,perCategory}.test.tsx`
(defaultValue mock; `perCategory` asserts English labels from `__tests__/fixtures/v2_response_*.json` — must stay
green because under that mock the helper returns the backend label), the snapshots
`__tests__/__snapshots__/DimensionBars.bundle-c.test.tsx.snap` and the components snapshot (44 snapshots
suite-wide, must pass unchanged), `__tests__/components/RunnerUpWinsCard.test.tsx`,
`__tests__/components/ResultsContent.runnerUp.test.tsx`, `__tests__/components/ResultsContent.render.test.tsx`
(pins `'329.000 BHD'`), `__tests__/HomeEditorialSections.smartPickPrice.w311.test.tsx`,
`__tests__/PersonalizationChip.test.tsx` + `__tests__/components/PersonalizationChip.test.tsx`,
every `__tests__/i18n/*` file, `__tests__/i18n.test.ts`, `__tests__/i18n.bundle_c.test.ts`,
`__tests__/copy-policy.test.ts`, `__tests__/rtl/textAlignLogical.contract.test.ts` (no new textAlign
ternary), `__tests__/api.streamComparison.{noBodyFallback,expoFetch}.test.ts`,
`__tests__/api.expiredTokenRetry.b2.test.ts` (uses `toMatchObject`/`objectContaining` on the params —
measured — so an added key would not break it, but T21 proves no key is added for EN).
Measured at HEAD: `npx jest <those 30 suites>` → **Test Suites: 30 passed, 30 total; Tests: 322 passed, 322 total**.

Backend: `tests/test_verdict_prompt_unification.py`, `tests/test_personalization.py`,
`tests/test_verdict_response_format.py`, `tests/test_review_prompt_quality.py`,
`tests/test_security_regression.py`, `tests/test_prescoring_showable_guard.py`,
`tests/test_self_critique_orchestration.py` (the six files that drive `generate_comparison` and read its
messages/kwargs, + the regen), `tests/test_m13_25_compare_body_maxlength.py`,
`tests/test_category_selection.py`, `tests/test_explicit_pair_category.py`,
`tests/test_m13_03_paid_work_gating.py`, `tests/test_events_allowlist_superset.py`. Measured symbol
reach (files under `tests/`): `TextCompareRequest` 2, `text_compare_get|text_compare_stream|text_compare(` 5,
`compare_from_text` 43, `generate_comparison` 28, `build_verdict_prompt` 12,
`_build_preferences_prompt|_build_cohort_priors_block` 6, `build_dimensions_v2|_DIMENSION_LABELS|_dim_from_category_lookup` 15,
`/text/compare` 34.

---

## 7. Red tests (RED = fails at `61585c58` for the stated reason; PIN = green at HEAD and must stay)

### Client (jest; run from `SmartCompareApp`)

`__tests__/i18n/dimensionLabels.w414.test.ts` — the 51 keys and EN labels are a literal table in the
test (Part C keeps it equal to the backend):
1. **RED `every public dimension key has results.dimension.<key> in en.json and ar.json`** — HEAD: 0 of 51.
2. **RED `the results.dimension family is exactly the 51 keys in both catalogs and no ar value contains an ASCII letter`** — non-vacuous (asserts size 51 first); HEAD: size 0.
3. **RED `en.json results.dimension.<key> equals the backend English label byte-for-byte`** (51 rows incl. `review`→`Reviews`, `value`→`Value`) — HEAD: missing.

`__tests__/utils/dimensionLabel.w414.test.ts`:
4. **RED `localizedDimensionLabel echo-guard semantics`** — (a) real ar instance → catalog value; (b) a
   t that echoes the key → the label; (c) a t that returns `defaultValue` → the label; (d) empty/undefined
   key → the label; (e) an uncatalogued key (`popularity`/`Popularity`) → the label. HEAD: module absent.

`__tests__/components/DimensionBars.arabicLabels.w414.test.tsx` (real i18next at `lng='ar'` via the
factory mock of §3; the 9-category row fixture is the probe's `dims_reach.json` `reach` table, inlined):
5. **RED `DimensionRow renders the Arabic label for all 72 rows (9 categories, expand pressed)`** — HEAD: 72/72 English.
6. **RED `InsufficientRow renders the Arabic label`** — HEAD: `Longevity`.
7. **RED `a point-math delta_text ('+18pt') on a non-hero row falls back to the Arabic label`** — HEAD: English label.
8. **PIN `under lng='en' (real catalog) every one of the 72 rows renders the backend label byte-identically`** — green at HEAD (the EN identity gate, §9.2).
9. **PIN `an uncatalogued key renders its backend label under lng='ar'`** (`{key:'popularity', label:'Popularity'}`) — green at HEAD.
10. **PIN `under the GLOBAL __mocks__/react-i18next (no per-file mock) a row still renders the backend label`** — separate file `__tests__/components/DimensionBars.globalMockLabel.w414.test.tsx`; green at HEAD; reddens if the helper loses its echo guard.

`__tests__/components/RunnerUpWinsCard.arabicLabels.w414.test.tsx`:
11. **RED `point-math delta falls back to the Arabic label under lng='ar'`** — HEAD: `Projection`.
12. **PIN `a qualitative delta_text passes through unchanged`** (`'Longer-lasting'`) — green.

`__tests__/i18n/priceDigits.crossScreen.w414.test.ts` (real i18next, ar):
13. **PIN `Results price, History hero savings, History count and Home savings count carry one digit class (ASCII, no U+0660-0669/U+06F0-06F9)`** — green at HEAD (the row's second claim, CHANGED by #175).
14. **PIN `formatPrice(12.345,'BHD',t_ar) === '12.345 د.ب' and formatPrice(250,'SAR',t_ar) === '250.00 ر.س'`** — green.
15. **PIN `every toLocaleString( call under src/ passes an explicit locale argument`** (source scan; 2 sites at HEAD, both `'en-US'`) — green.

`__tests__/i18n/referralExpiryPlurals.w414.test.ts` (real i18next, ar):
16. **RED `referrals.bonus.expiresIn{Days,Hours,Minutes} never fall back to English for counts 0,1,2,3,11,100`** — HEAD: `expiresInDays` English at 0/2/3/11 (measured); Hours/Minutes measured in the red phase and recorded.
17. **RED (existing fence, tightened)** `pluralFamilies.fence.w311 (ii)` with the 3 allowlist entries removed — red at HEAD (`ar referrals.bonus.expiresIn* missing _zero,_two,_few,_many`), green after A4.

`__tests__/api.outputLang.w414.test.ts` (axios instance + `expo/fetch` mocked as in
`api.streamComparison.noBodyFallback.test.ts` / `…expoFetch.test.ts`; set the default `i18next`
instance's language with `i18next.changeLanguage` after an `init({lng})` in `beforeEach`):
18. **RED `REST compare (GET /api/v1/text/compare) sends lang='ar' when the app language is ar`** — HEAD: absent.
19. **RED `SSE compare URL carries lang=ar`** (feature override ON) — HEAD: absent.
20. **RED `compareTextPair body carries lang: 'ar'`** — HEAD: absent.
21. **PIN `with language 'en', 'ar-…'-less or uninitialised, all three requests carry NO lang key (deep-equal to HEAD's params/body)`** — green at HEAD.

### Backend (pytest, under netguard)

`tests/test_dimension_label_catalog_parity_w414.py` (Part C):
22. **RED `every public dimension key (CATEGORY_DIMENSIONS minus _score, plus price/reviews/value) has results.dimension.<key> in en.json and ar.json`** — HEAD 0/51.
23. **RED `en.json results.dimension.<key> equals the backend label`** — label source: `_DIMENSION_LABELS` for the 49, and the `label` field `_dim_price`/`_dim_reviews`/`_dim_value` actually return (call them), not literals.
24. **PIN `build_dimensions_v2 over the 9 categories with every dim scored emits exactly the 45 recorded keys`** — green; if a future change makes `cpw`/a value proxy reachable the list moves deliberately.

`tests/test_arabic_verdict_output_w414.py` (Part B; capture harness = the probe's `_capture`,
`W4_14_probes/test_w414_probe.py::_capture`, which extends `test_verdict_prompt_unification.py:36`;
`monkeypatch.delenv` for `ENABLE_ARABIC_VERDICT_OUTPUT`, `ENABLE_GPT_WINNER`, `ENABLE_REVIEW_SOURCE_CONSULT`,
`ENABLE_YOUTUBE_SOURCE`, `ENABLE_SELF_CRITIQUE` unless a test sets them):
25. **RED `normalize_output_lang`** — `'ar'`,`'AR'`,`' ar-BH '`,`'ar_SA'` → `'ar'`; `'en'`,`'en-US'` → `'en'`; `'fr'`,`''`,`None`,`5` → `None`. HEAD: absent.
26. **RED `TextCompareRequest keeps lang and bounds it`** — `lang='ar'` round-trips in `model_dump()`; `'x'*9` → `ValidationError`; HTTP POST with `lang='x'*9` → 422 (the M13-25 harness). HEAD: dropped / no 422.
27. **RED `GET /text/compare and /text/compare/stream declare a lang query param`** (route `dependant.query_params`) — HEAD: absent (measured list in §1c).
28. **RED `each of the 3 handlers passes output_lang='ar' to the service for lang=ar, and passes NO output_lang kwarg when lang is absent or unrecognised`** (mocked service; assert on `call_args.kwargs`). HEAD: never passed.
29. **RED `compare_from_text and compare_from_text_streaming thread output_lang to generate_comparison`** (spy on `generate_comparison`, the sync and SSE paths) — HEAD: TypeError on the kwarg.
30. **RED `flag ON + output_lang='ar' → system_msg == HEAD system_msg + _ARABIC_OUTPUT_DIRECTIVE, user_msg and call kwargs unchanged`**, over the 18-cell matrix (§9.3) — HEAD: no directive.
31. **PIN `flag OFF → system+user messages and call kwargs identical for output_lang None / 'en' / 'ar'`** — equal to the recorded base digests (§9.3). Green at HEAD for `None` (the `'en'`/`'ar'` cases need the new param: they are RED-by-TypeError at HEAD and must equal the base capture after green).
32. **PIN `flag ON + output_lang None or 'en' → identical to base`**.
33. **RED `the self-critique regen keeps the directive`** (`ENABLE_SELF_CRITIQUE=true`, flag ON, `output_lang='ar'`, force one regen: the regen's system message also ends with the directive) — HEAD: no param.
34. **PIN `the cohort USER CONTEXT line is unchanged`** (`Language=Arabic` stays `USER CONTEXT: Country=Bahrain, Language=Arabic`, and the cohort block never contains the directive) — green.
35. **PIN `a request with no lang (the 561d2cba phone contract), flag ON` → service called WITHOUT an output_lang kwarg and the captured prompt equals base** — green at HEAD in effect (no param exists).

(Part D tests, only if §14 Q1 keeps it: W4-8's corpus-hash equality with the flag OFF; 0/302
non-Arabic rows change with it ON; one row per category classifies; the three prototype failures as
named REDs; a chip-precedence node proving a wrong Arabic token no longer overrides a correct chip.)

---

## 8. MUTATION CHECKS ARE REQUIRED (restore by byte copy + sha256, never `git checkout --`)

| # | mutation | must redden |
|---|---|---|
| M1 | `DimensionBars.tsx:313` back to `{label}` | 5 (and 7 stays red-adjacent) |
| M2 | helper without the echo guard (`return t(k, {defaultValue: label})`) | 10, 4(b), and the 6 global-mock DimensionBars suites |
| M3 | delete `results.dimension.longevity` from `ar.json` | 1, 2, 5, 6, 22 |
| M4 | change EN `results.dimension.build_quality` to `Build Quality` | 3, 8, 23 |
| M5 | skip A3 at `InsufficientRow` | 6 |
| M6 | skip A3 at the `safeDelta` fallbacks (both) | 7, 11 |
| M7 | send `lang` for `en` too | 21 |
| M8 | remove `lang` from the SSE URL only | 19 (18/20 stay green — proves per-site coverage) |
| M9 | delete `referrals.bonus.expiresInDays_two` from `ar.json` | 16, 17 |
| M10 | `arabic_verdict_output_enabled()` forced `True` | 31 |
| M11 | memoise the reader at import (module global) | 31 or 30 (whichever runs second under monkeypatch) |
| M12 | insert the directive BEFORE the scoring block instead of last | 30 (suffix equality) |
| M13 | drop the threading in `compare_from_text_streaming` only | 29 (SSE node) while the sync node stays green |
| M14 | pass `output_lang=None` unconditionally at the route | 28 ("NO output_lang kwarg") and 35 |
| M15 | `normalize_output_lang` without `.lower()` | 25 |
| M16 | drop `output_lang` from `regen_args` | 33 |
| M17 | delete one backend dim label key from `ar.json` only | 22 (the cross-language fence) |

---

## 9. Gates

1. **TDD red-first** — each RED above observed red at `61585c58` for the stated reason (paste the reason),
   then green.
2. **EN render identity (client equality gate).** Compared: the rendered text of every DimensionBars row
   (72 rows, 9 categories) under the real EN catalog, at HEAD vs after (test 8 carries it), AND the full
   jest snapshot set: `npx jest` must report **Snapshots: 44 passed, 44 total** with no `-u` and no
   snapshot file in the diff. Baseline measured at HEAD: `npx jest` → **Test Suites: 3 skipped, 320 passed,
   320 of 323 total; Tests: 15 skipped, 15 todo, 3150 passed, 3180 total; Snapshots: 44 passed, 44 total**.
   After: 320 + the new suites passed, 0 failed, snapshots 44/44. `npx tsc --noEmit --pretty false` exit 0
   at HEAD (measured) and after. The CI eslint command must stay at 0 errors and under the warning ceiling
   (#175 recorded 147 < 149).
3. **Prompt byte-identity (backend equality gate).** Harness: the probe's `_capture(category, prefs,
   scores, quality)` (`W4_14_probes/test_w414_probe.py`) — stubbed `get_client`, stubbed
   `model_router`, fixed products (Lattafa Yara / Fakhar, BHD prices), `scores_summary='A=70 B=60'`.
   Matrix: categories `{fragrances, electronics, other}` × prefs `{None, {"priorities":["longevity","price"],
   "budget":"mid","lifestyle":[],"brand_attitude":"best_of_both"}}` × `comparison_quality {normal, weak,
   weird}` = **18 cells**; each cell records `(sha256(system)[:16], sha256(user)[:16], len(system),
   sorted(call kwargs))`. **Base, measured at `61585c58`:** 18 distinct system digests; the file
   `W4_14_probes/probe_out/prompt_capture_base.json` sha256 `7fc3a311…aad9ae4`; e.g.
   `fragrances/noprefs/normal` = `0474e8b9ee1323fb / 89ea4eeb498992ac / 11187`, kwargs
   `[max_tokens, model, response_format, temperature]`; re-run identical (deterministic). **Head:** the
   same 18 cells with `output_lang ∈ {None, "en", "ar"}` × flag `{OFF, ON}` = 108 captures. Required: flag
   OFF → all 54 equal the base cell record-by-record; flag ON with `None`/`"en"` → 36 equal base; flag ON
   with `"ar"` → `user`, kwargs equal base and `system == base_system + _ARABIC_OUTPUT_DIRECTIVE`
   (compare the full strings, not only digests: rebuild the base string at head by capturing with the
   flag OFF in the same process, then assert the suffix). Run the base capture in a DETACHED scratch
   worktree of `61585c58` under the agent's scratchpad (`git worktree add --detach`), never by checkout;
   remove it after. The `_proof` / `scripts/verify_flag_byte_identity.py` harness is **not applicable**:
   it calls `extract_price_from_html` only and this unit touches no price code — say so in the PR.
4. **Comm sets.**
   * Backend: `grep -rlE "text_routes|extraction_service|TextCompareRequest|compare_from_text|generate_comparison|build_verdict_prompt|_build_cohort_priors_block|classify_category_from_text|_CATEGORY_SYNONYMS|canonicalize_category|/text/compare" tests --include=*.py | sort -u`
     → **148 files** at HEAD (list frozen in `W4_14_probes/comm_backend.txt`; 29 of them carry a
     live/integration marker and are deselected by `-m "not (live_unit or live_db or integration)"`). Run
     at base and head through the netguard (`-p qaren_netguard`, paste the `[netguard] blocked N` line);
     `comm -13 base_failed head_failed` must be empty. Known pre-existing network-reaching nodes in this
     set (session-66 close doc §5): `tests/test_winner_prose_reconciliation.py` (4 SSE tests via
     `moderate_output`), `tests/test_explicit_pair_integration_mocked.py`, `tests/test_timeout_partial_integration.py`
     — pass under the guard; add them to the accepted set only if they fail at BOTH base and head.
   * Client: `grep -rlE "DimensionBars|RunnerUpWinsCard|PersonalizationChip|_deltaText|safeDelta|i18n/en\.json|i18n/ar\.json|src/i18n'|streamComparison|compareTextPair|services/api'|ResultsContent|ResultsScreen" __tests__ --include=*.ts --include=*.tsx | sort -u`
     → **162 files** of 323 (frozen in `W4_14_probes/comm_client.txt`); then the FULL jest suite
     (memory rule: a client unit rebased onto a moved main runs the full suite before the PR).
5. **CI-order pin set** (run in this order in one process to catch env/flag leakage):
   backend `tests/test_verdict_prompt_unification.py tests/test_personalization.py tests/test_self_critique_orchestration.py tests/test_arabic_verdict_output_w414.py tests/test_verdict_response_format.py tests/test_m13_25_compare_body_maxlength.py tests/test_dimension_label_catalog_parity_w414.py tests/test_events_allowlist_superset.py`;
   client `__tests__/i18n __tests__/i18n.test.ts __tests__/copy-policy.test.ts __tests__/components/DimensionBars.snapshot.test.tsx __tests__/DimensionBars.bundle-c.test.tsx __tests__/components/DimensionBars.arabicLabels.w414.test.tsx __tests__/components/DimensionBars.globalMockLabel.w414.test.tsx __tests__/api.outputLang.w414.test.ts __tests__/api.streamComparison.noBodyFallback.test.ts`
   (the default `i18next` instance's language must be reset in `afterEach` of test 18-21 so it cannot
   leak into later suites in the same worker).
6. Ruff (`--select E9,F63,F7,F82`) + `py_compile` on the three backend modules; `git diff --stat` shows no
   whole-file (CRLF) rewrite. 7. Full pytest + full jest. 8. Fable review before commit. Agents never commit.

---

## 10. Activation

* **Client half:** rides the next `eas update --branch preview --clear-cache` from a main containing it
  (Ahmed's lever; the same OTA that first ships W3-11bcd/W3-14/W3-6/W3-15/W3-16, all main-only since
  `4eeb18aa`). Native-compatible: no `app.json`/`eas.json`/package change. The on-device Arabic walkthrough
  must check that every one of the 45 reachable Arabic labels fits `numberOfLines={1}` in the DimensionBars
  label row on the narrowest device (longest proposal 25 chars: `قيمة الاستخدامات المتعددة`, currently
  unreachable; the longest reachable is `الإحساس عند الاستخدام`, 21).
* **`lang` on the wire:** from that OTA, Arabic-UI phones send `lang=ar`; every deployed backend ignores it
  until Part B deploys, and Part B ignores it until the flag flips. English phones send nothing.
* **`ENABLE_ARABIC_VERDICT_OUTPUT` stays OFF until ALL of:** (1) OpenAI credits restored (the verdict call
  is dead at 429 anyway); (2) the English-only guards on verdict prose are audited for Arabic output —
  `text_sanitize.strip_score_internals` (`:76`), `trust_validation_service.validate_verdict` (`:46`),
  `verdict_critique_service.critique_verdict` (`:148`), `response_builder.reconcile_winner_prose`
  (`:202`), and the client's `SCORE_INTERNALS_RE`/`BANNED_PATTERN` (`_deltaText.ts`, `FactualVerdict.tsx:54-57`):
  each is an English regex that would pass an Arabic "N نقطة" leak vacuously (§14 Q7); (3) the verdict
  `max_tokens` budget (`token_limit_kwargs(verdict_model, 1000)`, `extraction_service.py` in the
  `guarded_llm_create` call) is measured against Arabic output length on a sample — Arabic prose can
  truncate the JSON; (4) the device walkthrough of an Arabic verdict (RTL + mixed Latin product names).
* **Canary lines:** `[ARABIC_VERDICT_OUTPUT] directive appended category=<c>` (count = Arabic compares
  that took the path); watch the verdict JSON-parse failure rate and the `[VERDICT` error lines for the
  same window; a spike means (3). Roll back by unsetting the flag (per-call read, no restart).

---

## 11. Honest limits

* **Most English prose on the Arabic results surface remains** after this unit, flag ON or OFF:
  the per-dimension `delta_text` (`_compose_delta_text` `scoring_service.py:3413`, ~31 English return
  templates; a qualitative delta is shown as-is, only the point-math form falls back to the label), the
  deterministic factual verdict `line1`/`line2` (`response_builder._format_line1` `:953`/`_format_line2`
  `:981`, English templates that embed the English dimension label), the spec VALUES, the review
  summary and per-product pros/cons from the reviews/specs extraction (cached per product under
  language-agnostic keys, so localizing them needs a cache-key change), and the personalization chip.
  Part B localizes only the per-comparison verdict call, which is uncached (no verdict cache exists —
  grep measured), so no cache split is needed for it.
* A verdict generated in Arabic is persisted in `full_response`; the same comparison reopened from
  History or a share link after switching to English shows Arabic prose. Acceptable for a dark flag;
  recorded.
* The Arabic label table is a proposal by a non-native author; §14 Q6.
* `lang` is sent only on the three text-compare calls; URL compare, the camera identify path and
  `/text/quick` are untouched (§14 Q3).
* Part D's prototype numbers (34/21/3) describe a probe-only token list; they are not the shipped design.
* No live OpenAI call was made; the directive's effect on output quality and length is unmeasured.

---

## 12. Spec disagreements with the review

1. **"52 dimension labels"** — 52 is 49 dim keys + 3 core labels, but `value` is shared, so there are
   **51** distinct public keys and only **45** can reach the screen at HEAD (the 5-contextual cap drops
   `cpw`; the value-proxy rule drops five). The catalog still covers all 51 (A2).
2. **The numeral claim (`-10`) is CHANGED, not RED:** #175 routed Results through `formatPrice` with the
   `latn` policy, and the History price the finding compared against was **dead code at `76ace90`**
   (defined `:709`, never called) — the "Results vs History" disagreement was never user-visible. This
   unit pins the property instead of fixing it.
3. **`-12` "passes a formatted string as count"** is now a recorded #175 ruling (R10), not a defect; only
   the referral-expiry English fallback remains, and it is latent (0 call sites).
4. **The finder's fix `t('results.dimension.'+key, { defaultValue: label })` is unsafe as written** under
   the global jest mock (returns the key, ignores `defaultValue`) — six DimensionBars suites would render
   `results.dimension.<key>`; the echo guard of `localizedCurrency` is required (A1, test 10, M2).
5. **Flag naming:** the finder proposed `ENABLE_ARABIC_OUTPUT` for all three layers; this spec flags only
   the prompt fork (`ENABLE_ARABIC_VERDICT_OUTPUT`) and leaves the client unflagged (OTA-gated, EN
   byte-identical) and the route field + threading inert — the standing rule flags result forks, and
   those are not forks.
6. **"no prompt asks for Arabic"** — true, but the cohort block DOES carry `Language=Arabic` as metadata
   (measured); it is not an output instruction and stays untouched.
7. **Anchors** drifted (§13); `ResultsScreen.tsx:411` no longer formats a price at all.

---

## 13. Anchors (review → symbol → line at `61585c58`)

| review anchor | symbol | line now |
|---|---|---|
| `DimensionBars.tsx:313` | `DimensionRow` label `<Text … numberOfLines={1}>{label}` | `:313` (unchanged); also `InsufficientRow` `:227` (fn `:223`), `safeDelta(delta_text, label)` `:286`, `DimensionRow` fn `:243` |
| (implied) runner-up card | `RunnerUpWinsCard.dimRowText` | `RunnerUpWinsCard.tsx:67-68` |
| `ResultsContent.tsx:143` | `formatPrice` closure → `formatAmountWithCurrency` | fn `:134`, call `:145` (`:143` is now the W3-11 comment) |
| `ResultsScreen.tsx:411` | price formatting | gone (0 `toLocaleString` in the file); dead `SCORE_LABELS` `:601` |
| `HistoryScreen.tsx:715` | `formatPrice` | deleted by #175 (was dead at `76ace90:709`); hero savings `:181-184` |
| `ResultsAccordion.tsx:664` | `ratingWithCount` call | `:662-668` |
| `ResultsScreen.tsx:774` (`-05`) | categorySwitched deletion note | `:798`; type `types.ts:296` |
| `extraction_service.py:1849` (`-11`) | `_build_cohort_priors_block` language line | fn `:1811`, `language =` `:1856`, context `:1860`; `generate_comparison` `:2313`, `system_msg = build_verdict_prompt(` `:2354`, winner-lever block `:2391-2392`; `COMPARISON_SYSTEM` `:1004`; `build_verdict_prompt` `:1961`; `_gpt_winner_lever_enabled` `:2106` |
| `extraction_service.py:1072` (`-02`) | `_CATEGORY_SYNONYMS` | `:1083`; `canonicalize_category` `:1136`; `classify_category_from_text` `:1167`, sweep `:1187` |
| `text_routes.py:62-88` | `TextCompareRequest` | `app/api/text_routes.py:217-253`; POST `:354-356`; GET `:532-544`; stream `:697-709`; service calls `:414`, `:606`, `:837` |
| `scoring_service.py:3381` | `public_key` | `:3396`; `_DIMENSION_LABELS` `:3262`; `build_dimensions_v2` `:3669`; `DIMENSION_DISPLAY_NAMES` `:1226`; `_compute_applied_shifts` `:624` |
| `scs@76ace90:369-379` | `_resolve_pair_category` | `:440`, `name_cat` `:467` |
| (new) SCS verdict sites | `generate_comparison(` | `:3922`, `:4687`, `:8763`; `regen_args=dict(` `:3940`, `:4713` |
| (new) client send sites | `streamComparison` / REST `baseParams` / SSE params / `compareTextPair` | `api.ts:576` / `:609` / `:750-760` / `:887` |

---

## 14. OPEN QUESTIONS FOR FABLE

1. **Part D (`-02`, Arabic category tokens): move to W4-8 or keep here?** Recommendation: W4-8. Same
   sweep (`:1186-1189`), same 360-corpus gate, same chip-override hazard (a wrong Arabic token outranks a
   correct chip on explicit_pair), and the prototype's 3 wrong rows are W4-8's ambiguity class. Keeping
   it here couples an OTA-gated client unit to a price-path-adjacent backend flag and makes two units edit
   one function concurrently.
2. **Personalization chip dimension names** — add an additive `dim_key` to each `applied_shifts` entry
   (backend, unflagged additive field; old phones ignore it) and localize via the same
   `results.dimension.*` family, in this unit or a follow-up? The review never filed it; measured English
   (`↑ longevity`).
3. **`lang` on `/url/compare`, `/image/identify`, `/text/quick`** — this unit covers only the three text
   compare calls the Home default path uses. Extend now (client sends, backend ignores until threaded) or
   a follow-up?
4. **`-05` category_switched** — product call for Ahmed: (a) a one-line disclosure (catalog key exists in
   both languages, 0 render sites), or (b) chip-authoritative precedence on explicit_pair
   (`ENABLE_CHIP_WINS_OVER_NAME_DETECT`, a W4-8-adjacent resolver change). Not implemented here.
5. **Referral expiry families** — complete the six Arabic forms (A4, keeps the keys for the future bonus
   UI) or delete the three dead families from both catalogs? Either empties the W3-11 allowlist.
6. **The 51 Arabic labels** need a native review (Ahmed or a reviewer) before the OTA; should the green
   agent ship the §4 proposal verbatim and flag it in the PR, or wait for the reviewed table?
7. **Arabic-aware guards before the flag can ever flip** — the English-only score-leak/critique/trust
   regexes (§10 (2)) are their own unit; confirm it is a hard precondition of `ENABLE_ARABIC_VERDICT_OUTPUT`
   and who owns it.
8. **`delta_text` and the factual verdict lines** (deterministic English templates) — a key+params
   contract so the client can localize them is the next Arabic unit; confirm it is out of W4-14.

---

## 15. Measurement provenance

* HEAD: `git -C sc-w4-specs rev-parse HEAD` → `61585c581e9deb78213f030260a765080f2e1dff`; `git status --short` clean
  (`.qa-s68/` is gitignored).
* Backend probe `W4_14_probes/test_w414_probe.py` (sha256 `db601e71…5b2f9686`), run from the worktree root:
  `PYTHONIOENCODING=utf-8 PYTHONPATH=<netguard dir>;<worktree> <venv python> -m pytest -p qaren_netguard -p tests.conftest -p no:cacheprovider -p no:randomly --timeout=120 -m "not (live_unit or live_db or integration)" --rootdir=<worktree> <probe> -q -s`
  → `4 passed` (tests a-d), then `-k test_e`, `-k test_f` (twice, identical), `-k test_g`, `-k test_h`
  each `1 passed`; every run printed `[netguard] blocked 0 network attempt(s)`. Outputs in
  `W4_14_probes/probe_out/` (`dims_summary.json`, `dims_reach.json` sha256 `a9594b19…d7e768`,
  `routes.json`, `prompts.json`, `verdict_match.json`, `category.json`, `corpus_arabic.json`,
  `prompt_capture_base.json`, `proto_ar.json`).
* Client probe `W4_14_probes/jest/w414.probe.test.tsx` with `jest.probe.config.js` (reuses the worktree's
  `jest.config.js`, collects only the scratch folder; nothing written into the worktree):
  `npx jest --config <probe config>` → `Tests: 6 passed, 6 total`; output `probe_out/jest_probe.json`.
* Preserve run: 30 suites / 322 tests passed. Full jest at HEAD: 320 passed + 3 skipped suites, 3150 passed
  tests, 44/44 snapshots (`W4_14_probes/jest_full_base.txt`). `npx tsc --noEmit --pretty false` exit 0.
  Toolchain behind `npx` verified (the junction trap): `node_modules/@babel/core`, `.bin/jest`, `.bin/tsc`
  present; `npx tsc --version` = `node node_modules/typescript/bin/tsc --version` = 5.9.3; jest 29.7.0 both ways.
* The Arabic label proposal `W4_14_probes/ar_proposal.json` (sha256 `79e95745…7cd734f`, 51 keys, equals the
  §4 A2 table); copy-policy check (banned + scary, EN labels and AR proposal) 0 hits; longest value 25
  chars (`multi_value`), longest reachable 21 (`sensory`).

---

# ADVERSARIAL SPEC REVIEW (2026-09-26, session 68)

**VERDICT: APPROVED_WITH_CORRECTIONS.** The core measurements reproduce byte-for-byte, and the
design works when prototyped against the real suites. Before a red phase starts, three things
must be fixed: PIN 15 is red at HEAD as written, A4's plural instructions would turn the
EN/AR interpolation fence red, and the mutation table has no kill for an emptied directive.

Reviewer base: `sc-w4-specs` at `61585c58` (clean). Backend runs used the pinned venv under
netguard. Client runs used the worktree's jest through a scratch config. Nothing was written
into the worktree except this section. Scratch: `scratchpad/w414_adv/`.

## R1. Re-measured claims that HOLD (reproduced, not re-read)

* **Backend probe re-run** (author's `test_w414_probe.py` copied to scratch, all 8 tests):
  `8 passed`, `[netguard] blocked 0 network attempt(s)`. All nine output JSONs are byte-identical
  to the author's `probe_out/` (sha256 prefixes match: `category 5e38e7d8`, `corpus_arabic 5acc1050`,
  `dims_reach a9594b19`, `dims_summary 76b66960`, `prompt_capture_base 7fc3a311`, `prompts ec024b17`,
  `proto_ar 79c825fb`, `routes 17815869`, `verdict_match 4feb11d7`). This confirms 9/54/49
  dimension rows, 51 public keys, 45 reachable, the 6 unreachable, 0/58 Arabic rows classified,
  34/21/3 and 0/302 for the prototype, the route and signature lists, and 0 output-language
  directives.
* **The capture base does not depend on the environment**: with every `ENABLE_*` var deleted,
  18/18 cells still equal the author's `prompt_capture_base.json`. It would therefore hold in
  CI, which has no `.env`. Sample: `0474e8b9ee1323fb / 89ea4eeb498992ac / 11187`.
* **Full jest at HEAD**: `Test Suites: 3 skipped, 320 passed, 320 of 323 total; Tests: 15 skipped,
  15 todo, 3150 passed, 3180 total; Snapshots: 44 passed, 44 total`. `npx tsc --noEmit` exits 0.
* **Client claims, reproduced** (author's jest probe output, plus my own probe): 72/72 rows in raw
  English under ar; `t('results.dimension.longevity')` returns the key itself; the
  `results.dimension.*` family has 0 keys in both catalogs (957 keys each); the four digit
  classes are ASCII; `formatPrice` gives `12.345 د.ب` / `250.00 ر.س`; `results.spec.*` has 68
  keys, identical in both catalogs; the proposal has 51 keys, a 25-character maximum, 0 ASCII
  letters and 0 copy-policy hits; the 5 claimed `results.spec.*` reuses are equal; `longevity`
  deliberately differs.
* **Green design prototyped** (scratch copies of `DimensionBars`/`RunnerUpWinsCard` with the A1
  echo-guarded helper at `:227/:286/:313` and `dimRowText`, mapped in through `moduleNameMapper`;
  catalogs = HEAD + the 51 keys):
  * The existing suites stay green: `24 passed, 259 tests, 4 snapshots passed`. This covers the
    9 DimensionBars suites, RunnerUpWinsCard, ResultsContent.* and ResultsScreen.*.
  * Real i18next, ar: 72/72 rows Arabic (0 ASCII labels). The insufficient row, the point-math
    fallback (label plus caption), the hero `value` point-math slot and the RunnerUp fallback
    all render Arabic. An uncatalogued `popularity` renders `Popularity`.
  * Real i18next, en: **72/72 rows equal the backend label byte-for-byte** (tests 8 and 9 are
    realisable).
* **Referral expiry**: `expiresInDays`, `expiresInHours` and `expiresInMinutes` all render
  ENGLISH under ar for counts 0, 2, 3 and 11. The spec left Hours/Minutes "to be measured in
  the red phase"; they are now measured.
* **A5 harness**: in jest the default `i18next` instance has `language` undefined before init;
  after `init({lng:'ar'})` it is `ar`; `changeLanguage('en')` gives `en`; `'ar-BH'` gives
  `ar-BH`. `isInitialized` is true. No suite mocks `i18next` (0 `jest.mock('i18next'`). A5 is
  implementable as written.
* **Other checks that hold**:
  * Fakes at `test_self_critique_orchestration.py:98` and `test_security_regression.py:1275` are
    `*args, **kwargs`.
  * `test_category_selection.py:310` reads `call_args`.
  * `test_behavior_integration.py:24/31` only asserts `"user_id" in sig.parameters`, so an
    additive param is safe.
  * Backend comm-set count: **148**, set-equal to `comm_backend.txt`. Client comm-set count:
    **162**.
  * Every anchor in §13 re-located, except R2.8.
  * The backend preserve files plus the six extra `generate_comparison` drivers (R4.3), run at
    HEAD: `502 passed, 4 deselected`. `[netguard] blocked 54 network attempt(s)` (the blocked
    calls go to `neutralized.supabase.invalid`/`api.openai.com`, and all tests pass anyway).
    The comm run must expect a non-zero blocked count; it cannot use 0 as its signal.

## R2. Refuted or drifted claims (with measurements)

1. **§7 test 15 / §1b "`toLocaleString` in src = 2 sites"**: REFUTED. `grep -rn toLocaleString src`
   finds **4** matches:
   * the two `'en-US'` call sites;
   * a comment `The toLocaleString()` at `src/utils/formatNumber.ts:59`;
   * the same text at `src/utils/__tests__/formatNumber.test.ts:65`.

   A source scan for `toLocaleString(` without an explicit locale would therefore be **red at
   HEAD** on both comment lines. As written, test 15 is not a PIN.
2. **A4 "EN twins `_zero/_two/_few/_many` echo `_other`, as `history.hero.count_*` does"**: REFUTED.
   * In EN, `history.hero.count_zero` and `_two` do NOT equal `_other` and carry no `{{count}}`.
     Only `_few`/`_many` echo `_other` (the same pattern holds for `time.daysAgo_*`).
   * `__tests__/i18n.test.ts:28-35` requires the `{{…}}` variable set to be identical per key
     in EN and AR.
   * So if the AR `_zero`/`_two` forms use natural Arabic without `{{count}}` (e.g. a dual form)
     while the EN twin echoes `_other` (which has `{{count}}`), the existing i18n fence goes RED.
3. **§6 client Preserve "30 suites / 322 tests"**: NOT REPRODUCIBLE from the listed files. `jest
   --listTests` over exactly the listed paths gives **28** suites. Run: `Test Suites: 28 passed;
   Tests: 269 passed; Snapshots: 6 passed`. (`__tests__/i18n/` holds 6 files.)
4. **§6 "`__tests__/DimensionBars.{bundle-c,deltaGuard,perCategory}` (defaultValue mock)"**: PARTLY
   REFUTED. `bundle-c` and `deltaGuard` use a KEY-ECHO per-file mock, `t: (key) => key`, which
   ignores `defaultValue`. Only `perCategory` is a defaultValue mock. So the §3 claim of "three
   t() shapes" is really four shapes; the echo guard handles the fourth the same way as the
   global mock.
5. **§8 M2 "must redden … the 6 global-mock DimensionBars suites"**: REFUTED by running M2 (the
   helper without the echo guard) against the real suites: `4 failed, 9 passed; 6 tests failed;
   3 snapshots failed`.
   * Red: `components/DimensionBars.test.tsx` (long label numberOfLines), `…insufficient` (row
     test), `…snapshot` (3 snapshots), and the per-file `DimensionBars.deltaGuard.test.tsx`
     (point-math label).
   * Stay GREEN: `…delta_hero`, `…hero_expand`, `…silent_omission` (they assert testIDs and keys
     only).

   M2 is still killed (tests 10 and 4b, plus these 4), but the kill list must be corrected.
6. **§0 "the 'limited data' row … print[s] English"**: the claim is only component-true.
   `data_insufficient` has **0 emitters in `app/`** (grep). `InsufficientRow` is unreachable from
   any backend at HEAD. It is not user-visible; test 6 is a latent-path pin.
7. **§4 A5 / §14 Q3 "the three text compare calls the Home default path uses"**: REFUTED.
   * `compareTextPair` has **0 call sites** in `src`.
   * The only live compare call is `streamComparison` (`HomeScreen.tsx:388`). It takes the REST
     `GET /text/compare` path by default (`ENABLE_EXPO_FETCH_SSE_DEFAULT = false`,
     `features.ts:52`) and uses SSE only when that flag is on.
   * `/url/compare` and `/text/quick` have **0 client callers**. The only other compare-producing
     call the client makes is `POST /api/v1/image/identify` (`api.ts:298`, which runs
     `compare_from_text` at `image_routes.py:390`).
8. **§1c/§13 stream service call `:837`**: drifted to **`text_routes.py:835`**
   (`_stream = service.compare_from_text_streaming(`).
9. **§9.4 "29 of them carry a live/integration marker and are deselected"**: REFUTED. Only **13**
   of the 148 files carry a `mark.live_unit|live_db|integration` / `pytestmark`. The other 16
   only contain the word (file names, comments). Their nodes are NOT deselected and will run.
10. **§9.2 "under the warning ceiling (#175 recorded 147 < 149)"**: no such ceiling exists. The
    CI step is `npx eslint "src/**/*.{ts,tsx}"` (`.github/workflows/ci.yml`) with no
    `--max-warnings`, and no test pins 149. Only the 0-errors part is a gate.
11. **§9.5 "i18next language must be reset afterEach so it cannot leak into later suites in the
    same worker"**: jest gives each test FILE its own module registry, so the default `i18next`
    instance cannot leak across suites. The reset is still needed, but only between tests inside
    `api.outputLang.w414.test.ts`.
12. **§10(2)/§14 Q7 FE guards `FactualVerdict.tsx:54-57`**: misdirected. Those lines guard the
    DETERMINISTIC `line1/line2`, not LLM prose. The FE guards that see the verdict prose Part B
    would localize are `ResultsContent.tsx:371` (`SCORE_INTERNALS_RE.test(verdictBody)`) and
    `RunnerUpWinsCard.tsx:90` (key_tradeoff).
13. **§6 backend "the six files that drive `generate_comparison`"**: the list is incomplete.
    `generate_comparison` is called directly in 10 test files. Missing from Preserve:
    * `test_comparison_quality_v2.py`
    * `test_diagnostics_flag_gated.py`
    * `test_extraction_pros_cons_diagnostic.py`
    * `test_guidance_insights.py`
    * `test_m18_openai_tpm_sizing.py` (reads the verdict call kwargs, including max_tokens)
    * `test_w49_extraction_catch_redaction.py`

    All are in the comm set and green at HEAD (R1).

Every other §1–§2 number re-measured equal (R1). The HOLDS/CHANGED rulings in §2 are correct.

## R3. Corrections (edits the spec needs before red)

* **C1 (test 15)**: scan code only. Strip `//` and `/* */` comments and exclude `src/**/__tests__/`,
  then assert that the 2 remaining sites carry a locale argument. Otherwise the test is red at
  HEAD (R2.1).
* **C2 (A4)**: for each new referral form, the AR and EN twins must carry the same `{{…}}`
  variables (`i18n.test.ts:28`). Either:
  * keep `{{count}}` in every AR form; or
  * model the EN `_zero/_two` on the `history.hero.count_zero/_two` / `time.daysAgo_zero/_two`
    pattern (no `{{count}}`), matching AR.

  Delete the false "echo `_other`" precedent. Add `__tests__/i18n.test.ts` to the red-phase
  checklist for A4.
* **C3 (mutation table)**: add **M18: `_ARABIC_OUTPUT_DIRECTIVE = ""`** (or truncated). Nothing
  in §7 reddens:
  * test 30 asserts `system == base + DIRECTIVE`, which is vacuous for `""`;
  * test 33 asserts `endswith(DIRECTIVE)`, which is also vacuous.

  Add a PIN on the constant: non-empty; names every prose field of `COMPARISON_SYSTEM`
  (`winner_reason`, `key_tradeoff`, `value_context`, `best_for`, pros/cons, `specs_comparison`,
  `personalized_insights`); contains the keep-list (JSON keys, `winner_declaration`,
  `focus_area`) and "Western digits". Test 30 must also assert `system != base`.
* **C4 (test 28)**: add `lang='AR'` and `lang=' ar-BH '`, each expecting `output_lang='ar'`. This
  kills a route that forwards the raw value. M14 does not cover that mutation, and
  `generate_comparison` compares `== "ar"`.
* **C5 (tests 18–21)**: add a node that flips the language between two calls on one imported
  `api` module (ar → en → ar). The second request must carry no `lang` and the third
  `lang='ar'`. This kills a reader memoised at module load. Name it **M19** in the table.
* **C6 (M2 row)**: replace the kill list with the measured one (R2.5).
* **C7 (§6)**: set the client Preserve number to what the listed files give (28/269/6), or name
  the two missing suites. Correct the mock-shape description (R2.4). Add the 6 backend drivers
  (R2.13) and `src/utils/__tests__/formatNumber.test.ts` and `src/utils/__tests__/currencyDisplay.test.ts`
  (price digit/currency pins under `src/`, outside the `__tests__` grep).
* **C8 (§9.4 comm sets)**:
  * Backend: the unit EDITS `structured_comparison_service.py`, but the regex does not name it.
    104 more test files import that module without matching any regex term (list in
    `scratchpad/w414_adv/scs_missing.txt`). Add `structured_comparison_service` to the regex, or
    state that gate 7 (full pytest, base vs head) is the net for them.
  * Client: the grep covers only `__tests__/`. `src/**/__tests__/` holds 10 suites, and
    `src/services/__tests__/sentry.test.ts` references `streamComparison`.
  * Fix the marker count (R2.9).
* **C9**: fix the anchor (R2.8), the eslint-ceiling sentence (R2.10), the afterEach rationale
  (R2.11), the §0/§1a "limited data row" framing (R2.6) and the A5/Q3 call inventory (R2.7).
* **C10 (§9.3 matrix)**: add cells with `demographics_profile` present (e.g.
  `{country:'Bahrain', language:'Arabic', cohort_match:{…}}` with `ENABLE_COHORT_PERSONALIZATION`
  on). This is the Arabic users' real path (the cohort block and the pain-workflow/decision-style
  blocks through `user_cohort`), and the 18 cells all use `demographics_profile=None`.

## R4. Missing items

1. **English REPLACEMENT paths, not just English guards.** An Arabic verdict (flag ON) is
   silently overwritten with English in unflagged code:
   * `_QUALITATIVE_WINNER_REASON` (`response_builder.py:1270`), used unconditionally at `:306`
     (winner-mismatch repair) and `:1687` (scrub-empties fallback);
   * `deterministic_verdict_fields` (`:152`, under `ENABLE_WINNER_PROSE_RECONCILE`);
   * `_deterministic_partial_verdict` (`structured_comparison_service.py:8416`, on the timeout
     partial path);
   * the `COMPARISON_GENERATION_ERROR` fallback.

   The spec's Q7 list only covers guards that let Arabic leaks through. These sites produce
   mixed-language verdicts, and they belong on the §10 precondition list.
2. **The English-only pending-price guard** `_PRICE_ADJECTIVE_RE` / `_leaks_price_adjective`
   (`response_builder.py:525-537`) drops price adjectives from pros/cons when a price is pending.
   Arabic ("أرخص", "سعر مناسب") passes it vacuously. This guard sits next to the price path and
   must join the §10(2) audit list.
3. **Arabic copy policy in the directive.** `src/i18n/.copy-policy.json` bans `الفائز`,
   `أفضل اختيار`/`الخيار الأفضل`/`أفضل خيار` and `نوصي بـ`, and the scary words `تقدير`,
   `مُقدَّر`, `فشل`, `تعذر`. The directive does not forbid them, and
   `tests/test_verdict_prompt_forbidden_words_audit.py` audits `build_verdict_prompt` only, not
   the directive suffix. Add them to the directive text (or a precondition) plus an audit node over
   `generate_comparison`'s flag-ON system message.
4. **The independent-winner lever**: the directive's field list omits `independent_winner_basis`
   (`extraction_service.py` `_build_independent_winner_block`). Its first sentence ("EVERY
   human-readable string value") makes the behaviour ambiguous when `ENABLE_GPT_WINNER` is also on.
5. **Camera path**: `/image/identify` (`image_routes.py:390`) is the only other live compare
   route the client calls. With the flag ON, Arabic camera users still get English verdicts.
   Q3 should be re-scoped to this route alone; `/url/compare` and `/text/quick` have no client
   callers (R2.7).
6. **Test 20** pins `compareTextPair`, which has 0 callers. Keep it for wire parity, but record
   it as dead-path coverage.

## R5. Design risks

* **"Unflagged" client half.** The client changes Arabic-visible text with no OFF switch. The
  spec's premise "RN has no per-call env" is only half true: `src/config/features.ts` already
  carries build-time client flags with a test override (`ENABLE_EXPO_FETCH_SSE`). The standing
  rule therefore allows a flag here; skipping one is a policy choice. EN renders ARE
  byte-identical (measured 72/72 and all suites green under the prototype), so the fork only
  reaches Arabic users. Fable must rule (Q-R1).
* **Catalog shadowing**: once the 51 EN keys exist, the catalog, not the backend, renders every
  known label. Part C test 23 is the only thing that keeps the two sources equal, so it must run
  in the backend CI job (it reads `SmartCompareApp/src/i18n/*.json`; the precedent is
  `test_events_allowlist_superset.py:30`).
* **Persisted Arabic verdicts** in `full_response` get re-served to English viewers through
  History and share links (§11 records this). No comparison-level cache was found (grep of
  `structured_comparison_service.py`/`text_routes.py`), so there is no cross-user cache
  contamination.
* **`numberOfLines={1}`** on the Arabic labels. The longest reachable label is 21 characters
  (`sensory`). This is device-walkthrough-only; no jest measures it.

## R6. Questions Fable must rule on (in addition to §14 Q1–Q8)

* **Q-R1**: Does the client half ship unflagged (EN byte-identical, measured), or behind a
  `features.ts` build flag default OFF?
* **Q-R2**: Do the English REPLACEMENT paths (R4.1) and the pending-price regex (R4.2) join the
  hard preconditions for `ENABLE_ARABIC_VERDICT_OUTPUT`, next to §10(2)?
* **Q-R3**: Does the directive carry the AR banned/scary vocabulary (R4.3), and should
  `independent_winner_basis` be translated or kept English (R4.4)?
* **Q-R4**: Q3 re-scoped: thread `lang` through `/image/identify` in this unit, or in a
  follow-up?
* **Q-R5**: A4 plural shape: which interpolation-parity option (C2)? (Linked to Q5: delete versus
  complete.)

Reviewer artefacts (scratch only): `scratchpad/w414_adv/`:
* `test_w414_probe_copy.py`, `test_w414_adv_probe.py`, `adv.probe.test.tsx`;
* `make_mut.py`, `jest.mut.config.js`, `DimensionBars.{guard,bare}.tsx`,
  `RunnerUpWinsCard.guard.tsx`, `{en,ar}_green.json`;
* `probe_out/*.json`, `jest_full_mine.txt`, `comm_backend_mine.txt`, `scs_missing.txt`.
