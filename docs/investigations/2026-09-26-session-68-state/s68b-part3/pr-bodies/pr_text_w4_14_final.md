## W4-14: Arabic on the results surface (dimension labels from the catalog, `lang` on the compare call, dark Arabic-verdict directive)

Findings PO-CATEGORIES-I18N-04 / -10 / -11 / -12 (-02 moved to W4-8c, #230; -05 is a DECISIONS item). Unit base `3985eaac`. Merge order: after W4-11 (both units edit the verdict prompt path).

### Defects
- **-04:** The results surface showed raw English dimension labels to Arabic users. With `lng='ar'` and the real catalogs, 72 of 72 DimensionBars rows printed the backend's English label, and the point-math `delta_text` fallbacks in DimensionBars and RunnerUpWinsCard printed it too. The `results.dimension.*` family had 0 keys in either catalog.
- **-11:** No compare route accepted a locale, the client sent none, and no verdict prompt carried an output-language instruction.
- **-12:** `referrals.bonus.expiresIn{Days,Hours,Minutes}` carried only `_one`/`_other`, so under `ar` they rendered English for counts 0, 2, 3 and 11. They have no call sites today (latent).
- **-10 (Results vs History numerals):** no longer a defect. #175 already fixed it. This PR pins it (PIN 13-15).

### Design
**Client (unflagged, OTA-gated; EN renders byte-identical)**
- New `src/utils/dimensionLabel.ts` `localizedDimensionLabel(key, label, t)`. It uses the `localizedCurrency` echo guard, so the global jest mock, key-echo mocks and uncatalogued keys fall back to the backend label.
- DimensionBars (row, InsufficientRow, the `safeDelta` fallback) and `RunnerUpWinsCard.dimRowText` now route through it.
- 51 `results.dimension.<public_key>` keys added to en.json and ar.json. The EN values echo the backend labels byte-for-byte. The AR values are the spec A2 table verbatim, **native review before the OTA** (table below).
- The six Arabic CLDR forms of the three referral-expiry families are completed. Per C2 and R2, `_zero`/`_two` carry no `{{count}}` in either language. R2 copy: minutes `_zero` EN "Expires in under a minute" / AR "تنتهي خلال أقل من دقيقة"; days `_zero` "Expires today" / "تنتهي اليوم"; hours `_zero` "Expires within the hour" / "تنتهي خلال أقل من ساعة". The three `ALLOWLIST_INCOMPLETE` entries are dropped from the W3-11 fence.
- `src/services/api.ts`: `currentOutputLang()` reads the DEFAULT `i18next` instance, once per request (R8). It returns `'ar'` only when the language lower-cased starts with `ar`. `lang` is sent with the omit-when-unset form on `streamComparison`'s REST params and SSE URL only (R1). EN or unset produces a request byte-identical to today.

**Backend (`ENABLE_ARABIC_VERDICT_OUTPUT`, default OFF, read per call)**
- `TextCompareRequest.lang`: `max_length=8`, over-long returns 422.
- `lang` query param on `GET /text/compare` and `/text/compare/stream`.
- `normalize_output_lang`: primary subtag `ar`/`en`, anything else becomes None.
- `output_lang` is threaded to `compare_from_text` / `compare_from_text_streaming` / `generate_comparison` and to both `regen_args` and the self-critique regen, always as CONDITIONAL kwargs. A request without `lang` makes kwarg-identical calls.
- The one fork: in `generate_comparison`, after the winner-lever block, `if output_lang == "ar" and arabic_verdict_output_enabled(): system_msg += _ARABIC_OUTPUT_DIRECTIVE`. It logs `[ARABIC_VERDICT_OUTPUT] directive appended category=<c>`. The directive is appended LAST, so the flag-ON prompt is exactly base + DIRECTIVE, and the static per-category prefix stays cacheable.
- The directive is the R3 text exactly (874 chars, sha16 `cef4fdeb0fd89ccb`). It names every prose field incl. `independent_winner_basis`, the keep-as-given list and Western digits, and forbids the 9 Arabic banned/scary copy-policy terms.

**Part C:** `tests/test_dimension_label_catalog_parity_w414.py` is a backend CI test that reads `SmartCompareApp/src/i18n/{en,ar}.json`. It keeps the EN catalog equal to the backend labels and makes a new backend dimension fail CI until it is catalogued.

### Flag row
`ENABLE_ARABIC_VERDICT_OUTPUT` (default OFF, `extraction_service.arabic_verdict_output_enabled`, read per call).
- **Effect ON:** Arabic-UI requests (`lang=ar`) get the Arabic-output directive on the verdict prompt, and the self-critique regen keeps it.
- **OFF:** byte-identical system message, user message and call kwargs (by VALUE) for `output_lang` None/en/ar over 24 cells, in both W4-11 states.
- **ON with None/en:** identical to OFF.
- **Knobs:** none.
- **Canary line:** `[ARABIC_VERDICT_OUTPUT] directive appended category=<c>`. In the same window, watch the verdict JSON-parse failure rate.
- **Activation preconditions, all required:**
  1. OpenAI credits.
  2. W4-14c: the Arabic-aware audit of the English-only guards (`strip_score_internals`, `validate_verdict`, `critique_verdict`, `reconcile_winner_prose`, FE `SCORE_INTERNALS_RE` at ResultsContent.tsx:371 and RunnerUpWinsCard.tsx:90) and of the English replacement paths (`_QUALITATIVE_WINNER_REASON`, `deterministic_verdict_fields`, `_deterministic_partial_verdict`, the `COMPARISON_GENERATION_ERROR` fallback), plus `_PRICE_ADJECTIVE_RE`.
  3. The Arabic `max_tokens` measurement. Test 30 now pins the token budget by value, so that change must update it deliberately.
  4. The on-device Arabic walkthrough.
- **Stated limit:** a verdict generated in Arabic is persisted and re-served to English viewers via History and share links.

**Client half:** unflagged and OTA-gated (`eas update --branch preview --clear-cache` is Ahmed's lever). The `numberOfLines={1}` fit is walkthrough-only; the longest reachable label is 21 chars (`sensory`).

### Gates (measured, final bytes)
- **Backend unit files, S1-S5** (unset / ARABIC / ARABIC+PROMPT_TRUTH / PROMPT_TRUTH / ARABIC+COHORT): 213 passed each, `[netguard] blocked 0`.
- **Netguard ratchet** over the unit files: OK, 0 new nodes, baseline 205.
- **Client unit suites** (9 files by path): 29 passed.
- **Full jest:** 328 passed / 3 skipped suites, 3176 tests, **Snapshots 44 passed, 44 total**, no `-u`.
- **Toolchain checks:** tsc 5.9.3 `--noEmit` exit 0. eslint 0 errors. ruff E9/F63/F7/F82 clean. py_compile clean.
- **Mutation matrix, all killed with sha-verified restores:** M1-M19, M14raw, M16regen, M20-M25, and the round-3 fixes N3/N4/N5/N16/N16on/N13/N13b/N13c.
- **R9 prompt byte-identity (24 cells x both W4-11 states):** every check 24/24. Drift vs `61585c58`: W4-11 off 18/18 equal; W4-11 on 0/18 system equal (W4-11's own prompt), user 18/18.
- **Backend CI-order set, S1 and S2:** 426 passed each, netguard 32/18 = base.
- **Client CI-order set:** 18 suites / 133 tests / 4 snapshots.
- **Comm gate:** HEAD, 261 files in 11 chunks, 11 deselects: 8516 passed, 0 failed.
- **Files:** exactly the ruled set; `git diff --stat` has no whole-file CRLF rewrite.

### Round-3 fixes (adversary r2, all minor, test-only)
1. **Test 36 pinned only the directive's vocabulary.** It now rebuilds the EXACT R3 text from the copy-policy file and asserts equality, `len == 874` and `sha16 == cef4fdeb0fd89ccb`. It is still file-derived, so a policy edit reddens backend CI. Kills N3 (keep-list inverted), N4 (bans turned into "prefer") and N5 (Arabic-Indic digits).
2. **The capture harness compared kwarg NAMES only.** It now records `{name: repr(value)}`, with a positive control that a token-limit kwarg is present. Tests 30/31/32 now cover values. Kills N16 (flag-OFF `max_tokens` fork: 48 nodes) and N16on (flag-ON fork: 24 nodes).
3. **The R2 copy correction was unpinned.** A new PIN in `referralExpiryPlurals.w414.test.ts` asserts the three `_zero` values in EN and AR and their Arabic rendering at count 0. Kills N13, N13b and N13c.

### Stated limits
- Most English prose stays on the Arabic results surface: `delta_text`, factual verdict `line1`/`line2`, spec values, review summary, pros/cons, and the personalization chip.
- `compareTextPair` (0 callers) sends no `lang` (R1; dead-path record in PIN 21).
- Test 21's "uninitialised i18next" case was dropped (R6).
- `/image/identify` gets no `lang`.
- The EN `_zero`/`_two` referral forms are parity twins that English never selects. They are now pinned by value, but EN rendering of them is not tested.
- `InsufficientRow` is backend-unreachable today (`data_insufficient` has 0 emitters); test 6 is a latent-path pin.
- The 51 Arabic labels are a non-native proposal.
- No live OpenAI call was made; the directive's effect on output quality and length is unmeasured.

### Follow-ups
- **W4-14b:** `PersonalizationChip` `dim_key`, and `lang` on `/image/identify`.
- **W4-14c:** the Arabic-aware guard and replacement-path audit, `_PRICE_ADJECTIVE_RE`, the Arabic `max_tokens` measurement.
- **W4-14d:** `delta_text` and the factual verdict lines as key+params.
- **W4-14e:** delete `compareTextPair`, or route it through the same reader once it has a caller.
- **W4-8c (#230):** Arabic category tokens behind `ENABLE_ARABIC_CATEGORY_TOKENS`.
- **DECISIONS for Ahmed:** `category_switched` disclosure vs chip-authoritative.

### CLAUDE.md corrections for the docs PR
- Add the `ENABLE_ARABIC_VERDICT_OUTPUT` row above.
- The mobile-gate rule `grep -rl SmartCompareApp tests/` gains `tests/test_dimension_label_catalog_parity_w414.py` (a backend CI test that reads the client catalogs).
- The client half is main-only until the next `eas update`.
- `tests/.pre_impl_failures.txt` carries 11 deselect rows (not 14).

### Arabic dimension labels (51 keys; **native review before the OTA**)
| key | EN (= backend) | AR |
|---|---|---|
| actives | Active ingredients | المكونات الفعالة |
| availability | Availability | التوفر |
| build | Build | التصنيع |
| build_quality | Build quality | جودة التصنيع |
| character | Character | الطابع |
| cpw | Cost per wear | التكلفة لكل استخدام |
| craft | Craftsmanship | الحرفية |
| dietary | Dietary fit | الملاءمة الغذائية |
| dosage | Dosage | الجرعة |
| durability | Durability | المتانة |
| ecosystem | Ecosystem | المنظومة |
| efficacy | Efficacy | الفعالية |
| evidence | Evidence | الأدلة |
| feature | Features | المزايا |
| feature_match | Feature match | مطابقة المزايا |
| finish | Finish | اللمسة النهائية |
| fit | Fit | المقاس |
| form | Form | الشكل |
| formulation | Formulation | التركيبة |
| function | Function | الوظيفة |
| futureproof | Future-proofing | مواكبة المستقبل |
| hair_match | Hair match | ملاءمة الشعر |
| heritage | Heritage | العراقة |
| ingredient | Ingredients | المكونات |
| ingredient_safety | Ingredient safety | أمان المكونات |
| longevity | Longevity | الثبات |
| multi_value | Multi-use value | قيمة الاستخدامات المتعددة |
| nutrition | Nutrition | القيمة الغذائية |
| perf_value | Performance vs value | الأداء مقابل السعر |
| performance | Performance | الأداء |
| presentation | Presentation | التقديم |
| price | Price | السعر |
| projection | Projection | الانتشار |
| reliability | Reliability | الاعتمادية |
| results | Results | النتائج |
| results_value | Results vs value | النتائج مقابل السعر |
| review | Reviews | التقييمات |
| reviews | Reviews | التقييمات |
| safety | Safety | الأمان |
| scalp | Scalp | فروة الرأس |
| scent | Scent | الرائحة |
| sensory | Sensory | الإحساس عند الاستخدام |
| serving_value | Serving value | قيمة الحصة |
| shade | Shade range | درجات اللون |
| skin_compat | Skin compatibility | ملاءمة البشرة |
| style | Style | الطراز |
| taste | Taste | الطعم |
| trust | Trust | الموثوقية |
| value | Value | القيمة |
| versatility | Versatility | تعدد الاستخدامات |
| wear_value | Wear value | قيمة الاستخدام |

🤖 Generated with [Claude Code](https://claude.com/claude-code)