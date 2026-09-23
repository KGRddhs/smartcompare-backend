# W3-11bcd — Arabic rendering pack, the remainder after W3-11a

## 1. Header

| field | value |
|---|---|
| unit | **W3-11bcd** (W3-11 minus (a); (a) = the textAlign revert, shipped in #141 `cc7c7ace` — this unit does NOT touch the five textAlign sites or `__tests__/rtl/textAlignLogical.contract.test.ts`) |
| findings | `MB-I18N-RTL-05`, `-06`, `-07`, `-08`, `-09`, `-14(c)(d)(f)` |
| base | `origin/main` = **`ed75dc70`** (worktree `sc-w3-ar`, measured 2026-09-11) |
| OTA class, per half | client copy/format/rendering (05, 06, 07, 08, 14c/d/f, the 7 literal sites of 09): **OTA-safe** (pure JS, no `app.json`, no native dep). The `eslint.config.js` fence half of 09 + every new/updated jest file: **ci-only** (never shipped). Overall: **mixed (OTA-safe + ci-only)**. No backend half, no flag, no migration. |
| toolchain measured | node v24.11.1 (ICU 77.1); `node node_modules/typescript/bin/tsc -v` = **5.9.3** (pin `~5.9.2`); jest 29.7.0 / ts-jest 29.4.9; i18next **26.1.0** (pin `^26.0.1`); react-i18next 17.0.7; intl-pluralrules 2.0.1; eslint **9.39.4**; eslint-plugin-i18next **6.1.4** (pin `^6.1.4`); react-native 0.81.5; expo 54.0.34 (pin `~54.0.33`) |

Reference specs followed for shape: `sc-w3-boot/.qa-w3/W3_12_UNIT_SPEC.md`, `sc-w1-limkey/.qa-w1b/W1_5_UNIT_SPEC.md`.

---

## 2. Scope correction — what is ALREADY on main at `ed75dc70`

Every plan row was re-located and re-measured at HEAD. Line anchors in the finding texts are from `76ace90`; the moves are listed.

### 2.1 Anchors that moved (all still red)

| finding anchor (76ace90) | at ed75dc70 | state |
|---|---|---|
| RTL-05 `HomeScreen.tsx:355` (SSE site) | **`:430-433`** (`onComplete`, `success:false` arm) | RED — measured, §3.1 |
| RTL-05 `HomeScreen.tsx:447` (URL site) | **`:540`** | RED — measured, §3.1 |
| RTL-05 "already-correct :396-398 branch" | the `onError` branch **`:450-483`** (`friendlyErrorKey` at `:482`, A11 `74d041cb`) | green, is the template |
| RTL-07 `HistoryScreen.tsx:715` | **`:767-776`** | see 2.3 — DEAD CODE |
| RTL-08 `formatDate.ts:28` | `:28-39` unchanged | RED |
| RTL-08 `ProfileEditorialSections.tsx:64` / `:143` | **`:63-78`** / **`:142`** | RED |
| RTL-09 `eslint.config.js:52` | `:52-58` unchanged (`mode: 'jsx-text-only'` at `:55`) | RED (fence absent) |
| RTL-09 `RegisterScreen.tsx:130/147/223` | `:137/:143` and `:159/:164` (google/apple) — **already `t(result.errorKey ?? 'auth.googleFailed')`** ; `:223` → **`:237`** | google/apple GREEN (2.2); `:237` RED |
| RTL-09 Results a11y labels | `ResultsContent.tsx:208` `accessibilityLabel="Back"`, `:224` `accessibilityLabel="Share"` | RED |
| RTL-14(d) "shimmer" | `LoadingScreenVariants.tsx:529-546` (`GhostField`), constant `:421 SHIMMER_TRANSLATE_PX = 60` | RED — measured, §3.6 |
| RTL-14(c) `DimensionBars.tsx:340/:373` | `:340` render, `:373` key literal | fence RED; runtime GREEN (2.4) |

### 2.2 Plan red tests DROPPED as already green (with evidence)

1. **RTL-09 "render RegisterScreen with a failing Google sign-in under `ar` and assert no ASCII letters" — ALREADY GREEN.** `git log -S"auth.googleFailed" -- SmartCompareApp/src/screens/RegisterScreen.tsx` → `8594826a fix(mobile): P-A8 - keep the [B4-DIAG] diagnostic out of the auth error banner`. At HEAD:
   ```
   137:        setError(t(result.errorKey ?? 'auth.googleFailed'));
   143:      setError(t('auth.googleFailed'));
   159:        setError(t(result.errorKey ?? 'auth.appleFailed'));
   164:      setError(t('auth.appleFailed'));
   ```
   Both keys exist in `en.json:899/904` and `ar.json:896/901`. Do not build this test. What remains at RegisterScreen is only `:237 setError(result.error || 'Registration failed');` (an email-path literal — a fence hit, see §3.5).

2. **RTL-14(c) "cheaper_of_two resolves wrongly" as a RUNTIME claim — never was a defect** (the verifier said so; re-measured): under `lng='ar'` on i18next 26.1.0, `t('results.valueMatch.cheaper_of_two')` = `"الأرخص بين الاثنين"` with no count, `count:2` and `count:5` alike (§10 probe 1). The only thing red is the *catalog fence* the finding asks for; that fence is kept (§5 test 6).

3. **RTL-06 "the plan said 32 vs 21 — re-measure"**: the per-STRING census is **exactly 32 Arabic-Indic vs 21 Western, 0 mixed** (896-value count in the finding is now 915 keys; the digit rows are unchanged). The task brief's "79 vs 338" is per-CHARACTER over the RAW FILE: 79 Arabic-Indic characters, and 338 ASCII digits of which **303 are inside KEY NAMES** (`demographics.age.18_24`, `onboarding.s9…`, …) — only **35** ASCII digits sit in VALUES outside `{{…}}` placeholders. Nothing to drop; the rule is defined in §4.2.

### 2.3 RTL-07: two of the finding's "six sites" are DEAD CODE

* `HistoryScreen.tsx:767-776` defines `const formatPrice = (product: any) …` (the `toFixed(2)` + two `'N/A'`) — **never called**: `grep -n "formatPrice" src/screens/HistoryScreen.tsx` → only `:767`; `grep -in "price" src/screens/HistoryScreen.tsx` outside `:767-776` → **no output**. History rows render no price at all.
* `ResultsScreen.tsx:440-448` defines `const formatPrice = (price?: …)` — **never called** (`grep -n formatPrice src/screens/ResultsScreen.tsx` → only `:440`). `tsconfig.json` is `strict` without `noUnusedLocals`, so tsc does not flag either.
* The LIVE price surfaces are: `ResultsContent.tsx:134-149` (called at `:303`) → `د.ب 12.345` symbol-first, digits from the DEVICE locale; `HomeEditorialSections.tsx:142` and `:187` (smart-pick prices) → `toFixed(0)` → `12 د.ب` for 12.345. The three remaining `toFixed(0)` sites (`HomeEditorialSections.tsx:293`, `HistoryScreen.tsx:184`, `ProfileEditorialSections.tsx:398`) are **whole-dinar savings aggregates** ("~N BHD shopped smarter"), not prices; this unit leaves them as-is and says so (Ahmed may overrule, §8).
* Consequence: `src/utils/__tests__/currencyDisplay.test.ts:62-74` source-greps `localizedCurrency(` in `screens/HistoryScreen.tsx` and `screens/ResultsScreen.tsx` — it is **pinning dead code**. Deleting the dead helpers requires updating that pin (§6, item P4).

### 2.4 Out of this unit by the brief (verify-and-drop, do not re-file)

* RTL-14(a) bidi isolation, (b) dead/empty keys (`onboarding.language.subtitle` is explicitly `allowedEmpty` in `__tests__/i18n.test.ts:13/21`), (e) polyfill probe — not in `(c)(d)(f)`.
* RTL-03 textAlign (W3-11a, #141).
* Every `home.errors.*` key used below already exists (`en.json:115-120`, `ar.json:112-117`, A11).

---

## 3. The defect — measured at `ed75dc70`

All probe files live in `.qa-w3b/probes/` (gitignored: `.gitignore:72 .qa-*/`). Run recipe (jest cannot resolve `node_modules` from outside the app dir, so pass `--modulePaths`):

```
cd SmartCompareApp
node node_modules/jest/bin/jest.js --ci --roots ../.qa-w3b/probes --modulePaths "$(pwd)/node_modules" --testMatch "**/*.probe.test.ts" --testMatch "**/*.probe.test.tsx"
```

### 3.1 RTL-05 — English backend prose reaches Arabic alerts (HomeScreen)

`src/screens/HomeScreen.tsx`:
```
429          const isTimeout = data.code === 'TIMEOUT' || data.code === 'STREAM_TIMEOUT';
430          Alert.alert(
431            t('common.error'),
432            isTimeout ? t('home.errors.timeout') : data.error || t('home.errors.comparison')
433          );
…
540        Alert.alert(t('common.error'), response.data.error || t('home.errors.comparison'));
```
The backend really emits that prose: `app/services/structured_comparison_service.py:3494-3499`
```
            return {
                "success": False,
                "error": "We don't compare this category",
                "code": "CONTENT_UNAVAILABLE",
                "layer": "query_prefilter",
            }
```
and `:3541-3545` the CODELESS identify failure `"error": "Could not identify two products to compare. Try: 'iPhone 15 vs Galaxy S24'"`. Codes that can arrive in a `success:false` envelope (grep over `text_routes.py`, `url_routes.py`, the service): `CONTENT_UNAVAILABLE`, `INSUFFICIENT_DATA`, `LLM_UNAVAILABLE`, `TIMEOUT`, `STREAM_TIMEOUT`, `USAGE_LIMIT`, plus codeless.

Probe `w311.home.probe.test.tsx` (the A11 harness verbatim, catalog switched to `ar.json`, `i18n.language='ar'`), measured output:
```
SSE CONTENT_UNAVAILABLE title="لحظة — جرّب الضغط مرّة ثانية." body="We don't compare this category" asciiLetters=true
SSE codeless identify-fail body="Could not identify two products to compare. Try: 'iPhone 15 vs Galaxy S24'" asciiLetters=true
URL CONTENT_UNAVAILABLE title="لحظة — جرّب الضغط مرّة ثانية." body="We don't compare this category" asciiLetters=true
```
"Could not" is on the CLAUDE.md:255 copy contract's forbidden list, shipped verbatim. Note the `onError` path already routes `CONTENT_UNAVAILABLE` to `handleContentUnavailable('text', layer)` at `:452-455` and everything else through `friendlyErrorKey` at `:482` — the two `success:false` arms simply never got the same treatment.

### 3.2 RTL-06 — no digit policy

Census (`scratchpad/b5/W3-11bcd/ar_census.py`, full output §10):
```
leaf keys ar/en: 915 915
chars: arabic-indic 79 | western (all) 35 | western outside {{}} 35
strings: arabic-indic 32 | western (outside {{}}) 21 | both 0
{{count}} keys: 35
percent glyphs: U+066A 4 | ASCII % 2
```
Same-screen contradictions in the catalog itself: `home.camera.slotIndicator = "{{index}} من ٢"` vs `home.camera.a11y.slot = "خانة الصورة {{count}} من 2"`; `paywall.features.unlimited = "٧٠ مقارنة شهرياً"` vs `paywall.features.comparisons = "70 مقارنة شهرياً"`; `onboarding.s13.factoid` (٧٣٪) vs `loading.tip.peer_prioritize` (73٪).

Runtime sites that follow the DEVICE locale, not the app locale: `ResultsAccordion.tsx:224 totalReviews.toLocaleString()`, `:664 count: ratingCount.toLocaleString()`, `ResultsContent.tsx:143 price.amount.toLocaleString()`, `ResultsScreen.tsx:443` (dead), `ProfileEditorialSections.tsx:74 new Date(iso).toLocaleDateString()` (no locale at all). `formatDate.ts:14` hard-codes `'ar-SA'`.

Probe `w311.units.probe.test.ts`, node ICU 77.1:
```
formatDate(ar) = "١١ سبتمبر"          formatDate(ar) has Arabic-Indic digits = true
formatTimeAgo(ar, 5 min) = "منذ 5 دقيقة"   … has Arabic-Indic digits = false
```
One helper, two digit systems. **No repo document states a convention**: grep of `CLAUDE.md`, `docs/**`, `src/i18n/.copy-policy.json` for arabic-indic / western / numeral / digit system finds only `docs/claude-design-handoff/project-README.md:96` ("Numerals stay numeric … Never spelled out" — digits vs words, not which digits). The only in-tree statement is the code comment `formatDate.ts:4-5`: *"Arabic note: ASCII digits are kept inside interpolations … to match the rest of the app's idiom (referrals.status, etc.)"*.

### 3.3 RTL-07 — BHD never gets its 3 decimals; symbol side flips

Probe output for 12.345 BHD / 12.5 SAR, `lng='ar'`, real catalogs:
```
History(ar) 12.345 BHD = "12.35 د.ب"      (dead code, §2.3)
Results(ar) 12.345 BHD = "د.ب 12.345"     (live: ResultsContent.tsx:143 shape)
Results(ar) 1234.5 BHD = "د.ب 1,234.5"
Home smart-pick(ar) 12.345 = "12 د.ب"     (live: HomeEditorialSections.tsx:142/:187 shape)
finding target = "12.345 د.ب"
Results(en) 329 BHD = "BHD 329"
```
The finding's exact target strings are **`'12.345 د.ب'`** and **`'12.50 ر.س'`** (MB-I18N-RTL-07 `test_first`, verifier CONFIRMED). Digit system: ASCII (the finding writes them so; consistent with §4.2). Symbol position: **amount first, then symbol** — the finding's own rule, and the position the hero copy already uses in both languages (`history.hero.savings = "~{{amount}} BHD shopped smarter"`, `paywall.plan.monthly_price = "2.9 د.ب"`). The verifier's correction is honoured: Results does NOT round today (`toLocaleString()` defaults to 3 max fraction digits); the Results defect is symbol side + device digits + no fixed minor-unit width (`329` vs `329.000`).

### 3.4 RTL-08 — relative time hard-coded, one Arabic plural form

`src/utils/formatDate.ts:28-39` (verbatim at HEAD): 8 hard-coded strings, no `t()`, `منذ ${n} دقيقة` for every count. Measured:
```
formatTimeAgo(ar, 1 min) = "منذ 1 دقيقة"  … (2 min) = "منذ 2 دقيقة" … (5 min) = "منذ 5 دقيقة" … (15 min) = "منذ 15 دقيقة"
formatTimeAgo(ar, 1 h)   = "منذ 1 ساعة"   … (2 h) = "منذ 2 ساعة"  … (11 h) = "منذ 11 ساعة"
formatTimeAgo(ar, 1 d)   = "منذ 1 يوم"    … (2 d) = "منذ 2 يوم"
```
`ProfileEditorialSections.tsx:63-78` `timeAgo()` has no language branch: `` `${hrs}h` `` (`:70`), `` `${days}d` `` (`:73`), `toLocaleDateString()` (`:74`) reach Arabic users via `:142`. Live consumers: `HistoryScreen.tsx:414-415 formatTimeAgo(dateString, i18n.language)` → `:503`; Profile `:142`.

The catalog template for six-form families exists and resolves (probe): `history.hero.count_{zero,one,two,few,many,other}` in both catalogs (`ar.json:913-918`, `en.json:916-921`) → `لا قرارات هذا الشهر | قرار واحد هذا الشهر | قراران هذا الشهر | 3 قرارات هذا الشهر | 11 قرارًا هذا الشهر | 100 قرار هذا الشهر`. A synthetic `time.minutesAgo_*` family resolved to **6 distinct strings** for 0/1/2/5/15/100 on the installed i18next (§10). `_zero` is honoured for EN count 0 even though `Intl.PluralRules('en').select(0)='other'` (measured: `ZERO-EN`).

### 3.5 RTL-09 — the literal-string fence sees nothing

Base, the exact CI command (`ci.yml:270 npx eslint "src/**/*.{ts,tsx}"`), run by path:
```
node node_modules/eslint/bin/eslint.js "src/**/*.{ts,tsx}" -f json -o ../.qa-w3b/probes/eslint.base.ci.json ; exit=0
FILES 148 | errors 0 | warnings 149 | i18next/no-literal-string messages 0
```
while these literals exist at HEAD: `ResultsContent.tsx:208 accessibilityLabel="Back"`, `:224 accessibilityLabel="Share"`, `RegisterScreen.tsx:237 result.error || 'Registration failed'`, `HistoryScreen.tsx:768/:772 'N/A'`, and — found by the candidate fence, not in the finding — `ForgotPasswordScreen.tsx:41 setError(t('auth.email') + ' is required')`.

Why the plugin cannot see them (installed 6.1.4, `lib/rules/no-literal-string.js:160-180`): under `jsx-text-only` a node is skipped unless its DIRECT parent is a `JSXElement`/`JSXFragment` — attributes, `Alert.alert(...)`, `setError(...)` and template strings are structurally invisible. Two widenings were measured:

| candidate | i18next messages | `no-restricted-syntax` | verdict |
|---|---|---|---|
| `mode:'jsx-only'` (probe `eslint.jsx-only.config.js`) | **562** (`testID=`, `viewBox=`, `provider=`, `keyboardType=` …) | — | unusable |
| `jsx-only` + attribute include-list + v1 descendant selectors (`eslint.targeted.config.js`) | 15 (11 are `{cond ? 'rtl' : 'ltr'}`-style JSX children) | 24, mostly false positives (`t('key')` args, `style:'cancel'`, `defaultValue:`) | rejected |
| **v2: keep `jsx-text-only`; add child-combinator `no-restricted-syntax` selectors** (`eslint.targeted2.config.js`) | 0 | **7 — all real** (list below) | **the design** |

v2 hits (`FILES 96 | errors 7 | warnings 113`):
```
/src/components/results/ResultsContent.tsx:208:30  user-visible JSX attribute carries an untranslated literal
/src/components/results/ResultsContent.tsx:224:30  (same)
/src/screens/ForgotPasswordScreen.tsx:41:34         a literal English string reaches setError()
/src/screens/HistoryScreen.tsx:768:83               'N/A' is user-visible English
/src/screens/HistoryScreen.tsx:772:87               'N/A' is user-visible English
/src/screens/RegisterScreen.tsx:237:34              a literal English string reaches setError()
/src/screens/onboarding/Step02Language.tsx:40:17    label="English"   <- language SELF-LABEL, allow (like '^EN$' / '^عر$' in wordsExclude)
```
`no-restricted-syntax` is not set by `eslint-config-expo/flat` (grep: no hits), so the block adds it without override.

### 3.6 RTL-14(c)(d)(f)

* **(c)** census: keys ending in a reserved plural suffix whose family is incomplete in `ar.json`: `results.valueMatch.cheaper_of` `['_two']` (the false family the finding names) **and** `referrals.bonus.expiresInDays/Hours/Minutes` `['_one','_other']`. The latter is a live-looking gap — measured on i18next 26.1.0 with `lng='ar'`: `count=3 → "Expires in 3 days"` (falls back to ENGLISH, not to `_other`) — but the family has **zero callers in `src/`** (grep `expiresIn` outside `src/i18n/` → nothing): dead keys, 14(b)'s territory. The fence allowlists them by name and says why.
* **(d)** probe `w311.shimmer.probe.test.tsx` (mutable `I18nManager` in `__mocks__/react-native.ts:87`, reanimated mock evaluates `useAnimatedStyle` once): `LTR translateX=[-60]`, `RTL translateX=[-60]`. The sweep starts at `-60` and travels to `+60` regardless of direction (`LoadingScreenVariants.tsx:529 useSharedValue(-SHIMMER_TRANSLATE_PX)`, `:534 withTiming(SHIMMER_TRANSLATE_PX …)`), i.e. left→right under a mirrored layout. The verifier's path correction stands: `src/screens/LoadingScreenVariants.tsx`, not `src/components/`.
* **(f)** `ar.json` mixes `٪` U+066A (4 values: `loading.tip.peer_prioritize`, `onboarding.s13.factoid`, `onboarding.s14.tip_1`, `results.tips.cohort_priority`) with ASCII `%` (2: `results.priceLess` — dead key, no callers; `paywall.plan.yearly_sub`).

---

## 4. The fix — MINIMAL design (client only, unflagged, backward-compatible with the backend on main)

Nothing here changes a request, a response contract, or a native surface. Every change is either pure formatting, catalog copy, or a lint rule.

### 4.1 New `src/utils/formatNumber.ts` — one place for digits and prices

```ts
export type DigitSystem = 'latn' | 'arab';
export const APP_DIGIT_SYSTEM: DigitSystem = 'latn';          // §4.2 — Ahmed's sign-off item
export const CURRENCY_FRACTION_DIGITS: Record<string, number> = { BHD: 3, KWD: 3, OMR: 3 }; // default 2
export function toAsciiDigits(s: string): string             // ٠-٩ (U+0660-0669) and ۰-۹ (U+06F0-06F9) → 0-9
export function applyDigitSystem(s: string): string          // identity for 'latn'; 0-9 → ٠-٩ for 'arab'
export function formatNumber(n: number, opts?: { minFraction?: number; maxFraction?: number; grouping?: boolean }): string
export function formatPrice(amount: number, currencyCode: string, t: TranslateFn): string
```
* `formatNumber` is **pure JS**: `toFixed(maxFraction)`, trim to `minFraction`, insert `,` every three integer digits, then `applyDigitSystem`. It deliberately does NOT call `Intl.NumberFormat(..., { numberingSystem })` — Hermes' Intl coverage on Android cannot be measured from this machine and the existing code already had to avoid it (`LoadingRings.tsx:84` / `StatBlock.tsx:29` pin `'en-US'`). Deterministic across engines, so the jest result IS the device result for this function.
* `formatPrice(amount, code, t)` = `` `${formatNumber(amount, { minFraction: d, maxFraction: d })} ${localizedCurrency(code, t)}` `` with `d = CURRENCY_FRACTION_DIGITS[code] ?? 2`. Amount first in BOTH languages; `localizedCurrency` (M21 W4) stays the symbol resolver exactly as it is. `formatPrice(12.345,'BHD',t)` under `ar` → `'12.345 د.ب'`; `(12.5,'SAR')` → `'12.50 ر.س'`; `(329,'BHD')` under `en` → `'329.000 BHD'`; `(1234.5,'BHD')` → `'1,234.500 BHD'`. Negative/NaN/null are the caller's problem (callers already guard `amount === null`).

### 4.2 The digit policy (RTL-06) — Western (ASCII) digits, marked for Ahmed

Rule: **one digit system across everything an Arabic user reads: ASCII `0-9`.** Enforced at three layers: (i) the catalog fence (§5 test 2a) — no `ar.json` value may contain `[٠-٩۰-۹]` while `APP_DIGIT_SYSTEM === 'latn'` (and the inverse rule if it is ever flipped: no ASCII digit outside `{{…}}`); (ii) every runtime number goes through `formatNumber` / `formatPrice`; (iii) `formatDate()` post-maps its output through `applyDigitSystem(toAsciiDigits(...))`, so whatever the engine's `toLocaleDateString('ar-SA')` produces, the digits obey the policy.

Why ASCII and not the per-string majority (32 > 21): the majority of what is RENDERED is already ASCII — all 35 `{{count}}` families, every `toFixed`/`toLocaleString` site, every price, and `formatTimeAgo`; `formatDate.ts:4-5` documents ASCII as "the rest of the app's idiom"; the RTL-07 finding writes its target as `12.345 د.ب`; the paywall price strings are ASCII (`2.9 د.ب`). Choosing Arabic-Indic would mean touching the 21 strings **and** every runtime site. **This is a product convention nobody has written down — Ahmed signs it off (§8).** The inverse costs one constant (`APP_DIGIT_SYSTEM = 'arab'`) plus rewriting the other 21 strings; the fence flips with the constant.

Catalog edit: rewrite the **32** Arabic-Indic values in `ar.json` to ASCII digits (list in §10 census output; includes `٢٬٠٧٤` → `2,074`, the `+١`/`+٥` reward lines keep their U+200E mark). No key changes, no EN changes, interpolation placeholders untouched (the `i18n.test.ts:28` placeholder-parity test stays green).

### 4.3 RTL-05 — HomeScreen renders code-keyed copy on the two `success:false` arms

`HomeScreen.tsx:429-433` becomes:
```ts
if (data.code === 'CONTENT_UNAVAILABLE') {
  handleContentUnavailable('text', data.layer ?? 'unknown');
} else {
  const isTimeout = data.code === 'TIMEOUT' || data.code === 'STREAM_TIMEOUT';
  Alert.alert(t('common.error'), isTimeout ? t('home.errors.timeout') : t(friendlyErrorKey(data.code)));
}
```
and `:540` the same shape with `'url'` and `response.data`. This mirrors the `onError` branch (`:452-455`, `:467-468`, `:482`) exactly; `friendlyErrorKey` (`services/errorCopy.ts`) is total, so a codeless identify failure lands on `home.errors.comparison` — which happens to be the right guidance ("try with brand or model"). `data.error` is no longer render input anywhere in HomeScreen. Additive type change: `layer?: string` on `ComparisonResult` (`src/types/types.ts:280`, next to the existing `code?: string`). No new catalog keys are needed for this finding — `CONTENT_UNAVAILABLE` already has `home.compare.unavailable_title/_body`, `INSUFFICIENT_DATA` has `home.errors.insufficientData`. (`LLM_UNAVAILABLE` collapses onto the generic nudge today; adding a dedicated key would touch A11's `errorCopy.a11.test.ts:196-201` enumeration — left as an observation, §8.)

### 4.4 RTL-07 — route the live price sites through `formatPrice`, delete the dead ones

* `ResultsContent.tsx:143` → `const base = formatPrice(price.amount, price.currency, t);` (the `converted_usd` suffix at `:147` unchanged). **EN Results changes from `BHD 329` to `329.000 BHD`** — a deliberate, PR-stated change; update the pin `__tests__/components/ResultsContent.render.test.tsx:349-350` to `'329.000 BHD'` / `'299.000 BHD'` (that test's echo-`t` makes `localizedCurrency` return the ISO code).
* `HomeEditorialSections.tsx:142` and `:187` → `formatPrice(pick.runner_up_price_bhd, 'BHD', t)` / `formatPrice(pick.winner_price_bhd, 'BHD', t)`; the trailing `{t('home.smart_pick.bhd')}` is removed at those two sites (the key stays — it may have other consumers; the referenced-key fence only checks the code→catalog direction).
* Delete `HistoryScreen.tsx:767-776` and `ResultsScreen.tsx:440-448` (dead), and the `localizedCurrency` import in each if it becomes unused (`ResultsScreen.tsx:74` — its only use was `:443`; `HistoryScreen.tsx:37` — its only uses were `:773/:775`). Update `src/utils/__tests__/currencyDisplay.test.ts:64-68` SITES: drop the two screens, add `utils/formatNumber.ts` (the resolver is now wired through it).
* Savings aggregates (`toFixed(0)` at `HomeEditorialSections.tsx:293`, `HistoryScreen.tsx:184`, `ProfileEditorialSections.tsx:398`) stay: whole-dinar stats, ASCII already, not prices.

### 4.5 RTL-08 — relative time through the catalog

* Catalog: add `time.justNow`, and the families `time.minutesAgo_*`, `time.hoursAgo_*`, `time.daysAgo_*` with **six forms in `ar.json` and six in `en.json`** (copy the `history.hero.count` template; EN `_zero/_two/_few/_many` may repeat `_other`'s text — they exist so one fence rule covers both catalogs). `_one` of `daysAgo` is "Yesterday" / "أمس" (matches Profile's existing behaviour at `:72`; History's `منذ 1 يوم` goes away). ASCII digits only (§4.2). Copy contract: none of the strings may contain `couldn't`/`try again`/`Failed to`/`تعذر`/`فشل`/`تقدير`/`مُقدَّر` (`copy-policy.test.ts` runs over every value).
* `formatDate.ts`: `formatTimeAgo(d, language, t)` — third parameter `t: TranslateFn` (additive; the `language` parameter stays because the ≥7-day fallback `formatDate(date, language)` needs it and `t` carries no language). Body: `<1 min → t('time.justNow')`, `<60 → t('time.minutesAgo', { count })`, `<24 h → t('time.hoursAgo', { count })`, `<7 d → t('time.daysAgo', { count })`, else `formatDate`. All eight hard-coded strings are deleted; the file contains **no Arabic script and no English relative-time literal** afterwards (pin P8). `formatDate()` keeps `toLocaleDateString(locale, { month:'short', day:'numeric' })` and post-maps digits (§4.2).
* `HistoryScreen.tsx:414-415` → `formatTimeAgo(dateString, (i18n.language as AppLanguage) ?? 'en', t)` — keep the names `formatTimeAgoLocalized` / `formatTimeAgo` (source pin `HistoryScreen.bundleE.s3.test.tsx:105-107`).
* `ProfileEditorialSections.tsx`: delete the local `timeAgo` (`:63-78`); the card component that renders `:142` takes `i18n` from its `useTranslation()` and calls `formatTimeAgo(item.created_at, i18n.language as AppLanguage, t)`. `profile.recent.justNow` / `profile.recent.yesterday` become unreferenced; they are NOT deleted here (key deletion is 14(b)'s scope) — say so in the PR.

### 4.6 RTL-09 — the seven fence hits + the fence itself

Site fixes (all OTA-safe):
* `ResultsContent.tsx:208` → `accessibilityLabel={t('results.a11y.back')}`; `:224` → `accessibilityLabel={t('results.a11y.share')}`. New keys `results.a11y.back` = "Back"/"رجوع", `results.a11y.share` = "Share"/"مشاركة" (both catalogs).
* `RegisterScreen.tsx:237` → `setError(result.error || t('auth.registerFailed'));` — new key `auth.registerFailed` = "Registration didn't complete" / "لم يكتمل إنشاء الحساب" (mirrors `auth.googleFailed`'s register; passes the copy contract). Honest note: `authService.register()` always populates `error` (`authService.ts:179/185`), so the literal was unreachable and the Arabic user keeps seeing `result.error` prose on the email path exactly as LoginScreen `:305` does today — that is the RTL-05 class on auth screens, out of this unit (§8).
* `ForgotPasswordScreen.tsx:41` → `setError(t('auth.emailRequired'))` — the key ALREADY EXISTS (`en.json:902`); no new copy.
* `HistoryScreen.tsx:768/:772` 'N/A' — gone with the dead helper (§4.4); no `common.notAvailable` key is added because no live consumer remains.
* `Step02Language.tsx:40 label="English"` — allowed by the fence (self-label), untouched.

Fence (`eslint.config.js`, ci-only), in the SAME block as the i18next rule (`files: ['src/screens/**', 'src/components/**']`), leaving `mode: 'jsx-text-only'` and `wordsExclude` exactly as they are:
```js
'no-restricted-syntax': ['error',
  { selector: "JSXAttribute[name.name=/^(accessibilityLabel|accessibilityHint|placeholder|title|label)$/] > Literal[value=/[A-Za-z]{2,}/]:not([value='English'])", message: '…use t(key)' },
  // setError(...) and Alert.alert(...): the literal itself, or the arm of a || / ?: / ?? / + / template right under the call
  { selector: "CallExpression[callee.name='setError'] > Literal[value=/[A-Za-z]{2,}/]", … },
  { selector: "CallExpression[callee.name='setError'] > LogicalExpression > Literal[value=/[A-Za-z]{2,}/]", … },
  { selector: "CallExpression[callee.name='setError'] > ConditionalExpression > Literal[value=/[A-Za-z]{2,}/]", … },
  { selector: "CallExpression[callee.name='setError'] > BinaryExpression > Literal[value=/[A-Za-z]{2,}/]", … },
  { selector: "CallExpression[callee.name='setError'] > TemplateLiteral > TemplateElement[value.raw=/[A-Za-z]{2,}/]", … },
  …the same five with "CallExpression[callee.object.name='Alert'][callee.property.name='alert']"…,
  { selector: "Literal[value='N/A']", message: "'N/A' is user-visible English" },
]
```
Exactly the selectors measured in `eslint.targeted2.config.js` plus the `:not([value='English'])` self-label allowance. Child combinators only: `t('key')` literals are children of the `t` call, `{ defaultValue: '…' }` / `{ text, style: 'cancel' }` are `Property` children of an `ObjectExpression` — none match (measured: 7 hits, 0 false positives). CI's `npx eslint "src/**/*.{ts,tsx}"` exits non-zero on errors, so the fence is blocking the moment it lands; it must land in the same PR as the seven site fixes or `frontend-tests` goes red. The finding's "bring `src/utils`/`src/hooks` under the rule" is NOT done: under `jsx-text-only` the plugin cannot see a non-JSX string, so un-exempting `src/utils` would be a no-op; pin P8 covers `formatDate.ts` instead.

### 4.7 RTL-14(c)(d)(f)

* **(c)** rename `results.valueMatch.cheaper_of_two` → `results.valueMatch.cheaperOfTwo` in both catalogs and at `DimensionBars.tsx:373`; update the two pins that spell the old key: `__tests__/components/DimensionBars.delta_hero.test.tsx:93` and `:104`, `__tests__/i18n.bundle_c.test.ts:25`. New fence `__tests__/i18n/pluralFamilies.fence.test.ts` (§5 test 6a).
* **(d)** `LoadingScreenVariants.tsx`: import `I18nManager` from `react-native` (`:28`); in `GhostField` (`:528`) read `const dir = I18nManager.isRTL ? -1 : 1;` at RENDER time (not module scope — the mock's mutable `I18nManager` and the frozen-StyleSheet rule both require it); `useSharedValue(-SHIMMER_TRANSLATE_PX * dir)`; `withTiming(SHIMMER_TRANSLATE_PX * dir, …)`. Nothing else in the file changes.
* **(f)** normalise the four `٪` values to ASCII `%` (consistent with §4.2; `results.priceLess` and `paywall.plan.yearly_sub` already use `%`). Fence in §5 test 6c.

### 4.8 Files to touch (complete list)

Source (OTA-safe): `src/utils/formatNumber.ts` (new), `src/utils/formatDate.ts`, `src/types/types.ts` (+`layer?`), `src/screens/HomeScreen.tsx`, `src/screens/HistoryScreen.tsx`, `src/screens/ResultsScreen.tsx`, `src/screens/RegisterScreen.tsx`, `src/screens/ForgotPasswordScreen.tsx`, `src/screens/LoadingScreenVariants.tsx`, `src/components/results/ResultsContent.tsx`, `src/components/results/ResultsAccordion.tsx` (`:224`, `:664` → `formatNumber`), `src/components/results/DimensionBars.tsx` (`:373`), `src/components/HomeEditorialSections.tsx`, `src/components/ProfileEditorialSections.tsx`, `src/i18n/en.json`, `src/i18n/ar.json`.
CI-only: `eslint.config.js`; new tests (§5); updated pins: `__tests__/components/ResultsContent.render.test.tsx:349-350`, `src/utils/__tests__/currencyDisplay.test.ts:64-68`, `__tests__/components/DimensionBars.delta_hero.test.tsx:93/:104`, `__tests__/i18n.bundle_c.test.ts:25`.
NOT touched: `package.json`, lockfiles, `app.json`, `babel.config.js`, `jest.config.js`, `__mocks__/*`, `src/services/errorCopy.ts`, `src/utils/currencyDisplay.ts`, `src/utils/rtl.ts`, the five textAlign sites, `__tests__/rtl/textAlignLogical.contract.test.ts`, `src/i18n/index.ts`, anything under `app/` (backend).

---

## 5. Red tests — exact files, assertions, measured reason RED, and the mutation that must redden each

All tests run with `node node_modules/jest/bin/jest.js --ci <path>` from `SmartCompareApp`. Real catalogs (`en.json`/`ar.json`) and a real `i18next.createInstance()` unless a component render needs the echo mock.

**1. RTL-05 — `__tests__/HomeScreen.arabicAlerts.w311.test.tsx`** (harness = `HomeScreen.errorCopy.a11.test.tsx` verbatim, react-i18next mocked to resolve through `ar.json`, `i18n.language = 'ar'`; `Alert.alert` spied).
   * (a) `handlers.onComplete({ success:false, code:'CONTENT_UNAVAILABLE', error:"We don't compare this category", layer:'query_prefilter' })` ⇒ the alert TITLE is `AR['home.compare.unavailable_title']` and the body `AR['home.compare.unavailable_body']`; `expect(body).not.toMatch(/[A-Za-z]/)`.
   * (b) `handlers.onComplete({ success:false, error:"Could not identify two products to compare. Try: 'iPhone 15 vs Galaxy S24'", parsed:{} })` ⇒ body `=== AR['home.errors.comparison']`, no ASCII letters, `not.toMatch(/Could not/)`.
   * (c) URL path: `mockApiPost.mockResolvedValueOnce({ data: <same CONTENT_UNAVAILABLE envelope> })` ⇒ same as (a) with `handleContentUnavailable`'s `trackEvent('compare_entry_content_block', { mode:'url', layer:'query_prefilter' })` observed.
   * (d) `success:false, code:'STREAM_TIMEOUT'` keeps `AR['home.errors.timeout']` (regression pin for the D2 branch).
   * RED today (measured §3.1): bodies are the English literals, `asciiLetters=true`, and no `compare_entry_content_block` event fires from `onComplete`. **Mutation:** restore `data.error ||` on either arm ⇒ (a)/(b) or (c) red.

**2. RTL-06 — `__tests__/i18n/digitPolicy.w311.test.ts`**
   * (a) catalog fence: for every `ar.json` value, `/[٠-٩۰-۹]/.test(v) === false` when `APP_DIGIT_SYSTEM === 'latn'` (and the mirror rule for `'arab'`: no `/[0-9]/` outside `{{…}}`). Prints the offending keys. RED today: 32 offenders (§3.2). **Mutation:** re-introduce one Arabic-Indic digit ⇒ red.
   * (b) `formatDate(new Date(Date.UTC(2026,8,11,12)), 'ar')` contains no `[٠-٩]` and DOES contain `11`; `formatTimeAgo(now - 5*60_000, 'ar', t)` and `formatDate(...,'ar')` report the same digit class (`/[0-9]/` both). RED today: `"١١ سبتمبر"` vs `"منذ 5 دقيقة"` (measured). **Mutation:** drop the `applyDigitSystem(toAsciiDigits(...))` post-map in `formatDate` ⇒ red on this node (ICU emits Arabic-Indic for `ar-SA`).
   * (c) `formatNumber(1234.5, { minFraction: 3, maxFraction: 3 }) === '1,234.500'`, `formatNumber(0.5, { maxFraction: 0 }) === '1'` (`toFixed` rounding, document it), `formatNumber(1234567) === '1,234,567'`. RED today: module missing. **Mutation:** remove grouping ⇒ red.

**3. RTL-07 — `src/utils/__tests__/formatNumber.test.ts` + a live-site render**
   * (a) with a real i18next instance on the real catalogs, `lng='ar'`: `formatPrice(12.345,'BHD',t) === '12.345 د.ب'`, `formatPrice(12.5,'SAR',t) === '12.50 ر.س'`, `formatPrice(8.75,'KWD',t) === '8.750 د.ك'`; `lng='en'`: `formatPrice(329,'BHD',t) === '329.000 BHD'`, `formatPrice(1234.5,'BHD',t) === '1,234.500 BHD'`, unknown code `formatPrice(9.99,'EUR',t) === '9.99 EUR'` (localizedCurrency fallback preserved). RED today: module missing. **Mutation:** hard-code 2 fraction digits ⇒ BHD/KWD cases red; swap symbol first ⇒ every case red.
   * (b) `__tests__/components/ResultsContent.render.test.tsx:347-351` updated: `getByText('329.000 BHD')` / `'299.000 BHD'`. RED today: renders `BHD 329` (measured, that test currently asserts the old string and passes). **Mutation:** revert `ResultsContent.tsx:143` ⇒ red.
   * (c) `HomeEditorialSections` smart-pick: render with `winner_price_bhd: 12.345` under the echo-`t` mock ⇒ `getByText('12.345 BHD')`; RED today: `12 BHD`. **Mutation:** restore `toFixed(0)` ⇒ red.

**4. RTL-08 — `src/utils/__tests__/formatDate.test.ts`** (real i18next instance, real catalogs)
   * (a) `lng='ar'`: `formatTimeAgo(now - 5*60_000, 'ar', t)` `not.toBe('منذ 5 دقيقة')` and equals `t('time.minutesAgo', { count: 5 })`; the strings for counts `[0,1,2,5,15,100]` of `time.minutesAgo` are **six distinct** values, none equal to the bare key; `count 1` and `count 2` contain no digit (grammatical singular/dual, the `history.hero.count` convention). Same distinctness for `time.hoursAgo` `[0,1,2,3,11,100]` and `time.daysAgo` `[0,1,2,3,11,100]`; `daysAgo count 1 === t('time.daysAgo_one')` is the "yesterday" string. RED today: `formatTimeAgo` has no `t` parameter and returns `منذ 5 دقيقة`; the keys do not exist. **Mutation:** collapse `_few`/`_many` onto `_other` ⇒ distinctness red.
   * (b) `lng='en'`: `formatTimeAgo(now - 3*3_600_000, 'en', t) === t('time.hoursAgo', { count: 3 })` and `=== '3h ago'` (EN wording preserved exactly). **Mutation:** wrong EN template ⇒ red.
   * (c) `__tests__/ProfileEditorialSections.timeAgo.w311.test.tsx`: render the recents row with `created_at = now - 3h` under an `ar`-resolving `t` mock and `i18n.language='ar'` ⇒ no rendered text matches `/\b\d+[hd]\b/` and the row contains `AR['time.hoursAgo_few']`'s digitless prefix; with `created_at = now - 20 days` ⇒ the date text has no `[٠-٩]`. RED today: `3h` (measured shape `${hrs}h`, `:70`). **Mutation:** restore the local `timeAgo` ⇒ red.

**5. RTL-09 — `__tests__/lint/i18nFence.w311.test.ts`** (runs the real `eslint.config.js` through ESLint's Node API — `const { ESLint } = require('eslint'); new ESLint({ cwd: <SmartCompareApp> })`, `lintText(fixture, { filePath: 'src/screens/__fence_fixture__.tsx' })`; if the API refuses to load the flat config under jest, `child_process.spawnSync` on `node_modules/eslint/bin/eslint.js --stdin --stdin-filename src/screens/x.tsx -f json` is the fallback — say which was used).
   * Fixtures, each must yield ≥1 `no-restricted-syntax` error: `<Pressable accessibilityLabel="Back" />`; `setError(result.error || 'Registration failed')`; `Alert.alert(t('x'), 'Something went wrong')`; `const s = 'N/A'`; `setError(t('auth.email') + ' is required')`.
   * Negative fixtures, each must yield 0 errors: `setError(t(result.errorKey ?? 'auth.googleFailed'))`; `Alert.alert(t('a', { defaultValue: 'Pick two photos' }), t('b'), [{ text: t('c'), style: 'cancel' }])`; `<Option label="English" />`; `<View testID="stat-card" />`.
   * RED today: the rule is absent ⇒ 0 errors on every positive fixture. **Mutation:** delete any one selector ⇒ its fixture red; widen `LETTERS` to `[A-Za-z]` (one letter) ⇒ nothing here reddens, so ALSO assert the negative fixtures (a `style:'cancel'`-class false positive reddens them).
   * (b) `__tests__/components/ResultsContent.a11y.w311.test.tsx`: render `ResultsContent` with the echo-`t` mock ⇒ `getByLabelText('results.a11y.back')` and `getByLabelText('results.a11y.share')` exist and `queryByLabelText('Back')`/`('Share')` are null. RED today: labels are the literals. **Mutation:** revert `:208` ⇒ red.
   * (c) the whole-tree assertion is CI's own `npx eslint "src/**/*.{ts,tsx}"` exit code (§7); not duplicated in jest.

**6. RTL-14(c)(d)(f)**
   * (a) `__tests__/i18n/pluralFamilies.fence.w311.test.ts`: for each catalog, group keys by reserved suffix (`_zero|_one|_two|_few|_many|_other`); assert (i) **no key whose last dotted segment ends in a reserved suffix is a lone member** (catches `results.valueMatch.cheaper_of_two`; the fixed name `cheaperOfTwo` ends in no suffix), (ii) every `ar.json` family has all six forms and every `en.json` family has at least `_one` + `_other`, with an explicit allowlist `['referrals.bonus.expiresInDays','referrals.bonus.expiresInHours','referrals.bonus.expiresInMinutes']` annotated "dead — zero callers in src/, i18next 26.1.0 falls back to ENGLISH for ar counts 0/2/3-10/11-99 (measured); 14(b)'s owner deletes or completes". RED today on (i). **Mutation:** re-add a key `foo.bar_two` alone ⇒ red; remove `time.minutesAgo_few` from `ar.json` ⇒ red.
   * (b) `__tests__/LoadingScreenVariants.shimmerRTL.w311.test.tsx` (harness = `w311.shimmer.probe.test.tsx`): with `RN.I18nManager.isRTL = false` the shimmer `translateX` of `loading-streaming-card-a-name-shimmer` is `-60`; with `isRTL = true` (set BEFORE render, reset after) it is `+60`. RED today: `-60` under both (measured). **Mutation:** read `isRTL` at module scope instead of in `GhostField` ⇒ the RTL case stays `-60` ⇒ red (this is also why the test proves the read is render-time).
   * (c) in `digitPolicy.w311.test.ts`: `ar.json` values contain either `٪` or `%` but never both across the catalog; with the policy `latn`, zero `٪`. RED today: 4 vs 2. **Mutation:** restore one `٪` ⇒ red.

Decoration check: every test above names the edit that reddens it; none passes at HEAD except the pins in §6.

---

## 6. Preserve — behaviours that must stay identical, with the proof

| id | behaviour | proof |
|---|---|---|
| P1 | The `onError` path's copy (INSUFFICIENT_DATA / codeless 502 / RATE_LIMITED / TIMEOUT; text and URL agree) | existing `__tests__/HomeScreen.errorCopy.a11.test.tsx` (7 tests) + `__tests__/errorCopy.a11.test.ts` — untouched, must stay green |
| P2 | `friendlyErrorKey` totality and 4-key map | `errorCopy.a11.test.ts:144/:208` — `errorCopy.ts` is not edited |
| P3 | `localizedCurrency` glyph table, EN ISO passthrough, unknown-code fallback, echo-`t` tolerance | `src/utils/__tests__/currencyDisplay.test.ts:34-58` untouched |
| P4 | `localizedCurrency` is the price symbol resolver at every live price site | same file `:62-74` — SITES list updated to `components/results/ResultsContent.tsx` + `utils/formatNumber.ts` (the two dead screens dropped, reason in the test comment) |
| P5 | Six-form Arabic plurals for `home.savings.count` / `history.hero.count`; polyfill import order | `__tests__/i18n/plurals.test.ts` untouched |
| P6 | EN/AR key-set equality, placeholder parity, `allowedEmpty`, the two deleted keys | `__tests__/i18n.test.ts`, `__tests__/i18n/no-deleted-keys.test.ts`, `__tests__/i18n/no-missing-referenced-keys.test.ts` (every new `t('…')` key added to BOTH catalogs; `t('time.minutesAgo', {count})` resolves through the fence's plural-aware `isPresent`) |
| P7 | Copy contract on all new strings | `__tests__/copy-policy.test.ts` (runs over every catalog value) |
| P8 | NEW pin: `src/utils/formatDate.ts` contains no Arabic-script character (`/[؀-ۿ]/`) and none of `'just now'|'m ago'|'h ago'|'d ago'` as literals | in `formatDate.test.ts` — the RTL-08 class cannot come back through the exempted `src/utils` |
| P9 | Shimmer DOM: all 8 `-pending` and `-shimmer` testIDs mount; badge not mounted before reveal | `__tests__/LoadingScreen.bundleE.test.tsx:125-140`, `LoadingScreenVariants.*.test.tsx` untouched |
| P10 | DimensionBars value captions for above/below/in-range | `DimensionBars.delta_hero.test.tsx` (only the two `cheaper_of_two` spellings change) + the other 8 DimensionBars suites |
| P11 | History source pins (`formatTimeAgoLocalized`, `formatTimeAgo`, `history.yesterday`) | `__tests__/HistoryScreen.bundleE.s3.test.tsx:64/:105-107` untouched |
| P12 | Register google/apple copy via `errorKey` (P-A8) | `__tests__/AuthScreens.socialDiagnostic.pa8.test.tsx` untouched |
| P13 | textAlign contract (W3-11a) | `__tests__/rtl/textAlignLogical.contract.test.ts` — NOT edited, must stay green |
| P14 | `LoadingRings.tsx:84` / `StatBlock.tsx:29` keep `toLocaleString('en-US')` (already policy-conformant) | not touched |

Baseline measured at `ed75dc70` for the suites named above (17 files): **17 passed / 221 tests / 0 failed** (§10).

---

## 7. Gates

1. **Red-first**: tests 1-6 fail for the measured reasons before any source edit; a test that is green before the fix is deleted, not kept.
2. **Unit test files**: `__tests__/HomeScreen.arabicAlerts.w311.test.tsx`, `__tests__/i18n/digitPolicy.w311.test.ts`, `src/utils/__tests__/formatNumber.test.ts`, `src/utils/__tests__/formatDate.test.ts`, `__tests__/ProfileEditorialSections.timeAgo.w311.test.tsx`, `__tests__/lint/i18nFence.w311.test.ts`, `__tests__/components/ResultsContent.a11y.w311.test.tsx`, `__tests__/i18n/pluralFamilies.fence.w311.test.ts`, `__tests__/LoadingScreenVariants.shimmerRTL.w311.test.tsx` (all matched by `testMatch: **/__tests__/**/*.test.ts(x)`).
3. **Neighbour suites** (derive with `grep -rlE "HomeScreen|HistoryScreen|ResultsScreen|RegisterScreen|ForgotPasswordScreen|AuthScreens|LoadingScreenVariants|LoadingScreen|ResultsContent|ResultsAccordion|DimensionBars|HomeEditorialSections|ProfileEditorialSections|ProfileScreen|formatDate|currencyDisplay|errorCopy|i18n|copy-policy|rtl/" __tests__ src/utils/__tests__` — ~90 files at HEAD). Minimum named set: the 17 measured in §10 plus every `HomeScreen.*`, `HistoryScreen.*`, `ResultsScreen.*`/`screens/ResultsScreen.*`, `ResultsContent.*`/`components/ResultsContent.*`, `ResultsAccordion.*`, `DimensionBars.*`/`components/DimensionBars.*`, `LoadingScreen*`, `ProfileScreen.*`, `ProfileEditorialSections.*`, `RegisterScreen.*`, `AuthScreens.*`, `Screens.bundleD.contract.test.ts`, `i18n*`, `rtl/*`. Snapshot suites (`DimensionBars.snapshot`, `DimensionBars.bundle-c`) must pass WITHOUT `-u`.
4. `node node_modules/typescript/bin/tsc --noEmit` — exit 0 (base: exit 0, 5.9.3).
5. `node node_modules/eslint/bin/eslint.js "src/**/*.{ts,tsx}"` — the CI command — **exit 0 with 0 errors** (base: 0 errors / 149 warnings; the new rule adds 7 errors until the sites are fixed; warnings may not grow: an unused `localizedCurrency` import left behind would add one).
6. Full jest suite once, in the green phase (baseline 2,729 passed / 0 failed / 278 suites at `ece0fbbe`; expect +9 suites).
7. Backend halves: **none** — no pytest, no ruff, no comm gate (nothing under `app/` or `tests/` is touched; state this in the PR).
8. Fable review before commit; agents never commit.

---

## 8. What this unit CANNOT do / Ahmed dependencies / device-only

* **Digit-policy sign-off (Ahmed).** Western digits is a measured majority-of-rendered-surface choice, not a documented product rule. If Ahmed wants Arabic-Indic, flip `APP_DIGIT_SYSTEM` and rewrite the 21 ASCII strings instead of the 32; the fence follows the constant. Same sign-off covers `%` vs `٪`.
* **On-device Arabic walkthrough (Ahmed, after the OTA).** Jest cannot verify: (1) what Hermes' `toLocaleDateString('ar-SA', {month:'short'})` returns for the MONTH NAME (the digit map is engine-independent, the month word is not — on a Hermes build without ICU data it may be Latin or numeric; check History rows older than 7 days in Arabic); (2) the shimmer direction as seen on a mirrored layout (the test proves the sign flips, not that it looks right); (3) VoiceOver/TalkBack reading "رجوع"/"مشاركة" on the Results header; (4) that `Alert` titles/bodies render fully RTL with the new copy; (5) the smart-pick `12.345 د.ب` line fitting its tile at 3 decimals in Cairo/system font.
* **The OTA itself** (`eas update --branch preview --clear-cache`) — every client change here is invisible on phones until Ahmed publishes; phones are on `97b5f15`.
* **No backend change** — an Arabic user still receives the English `error` string in the payload; it is simply never rendered. Localising `LLM_UNAVAILABLE` (and the auth screens' `result.error`-first pattern at `LoginScreen.tsx:305` / `RegisterScreen.tsx:237`, and `RegisterScreen.tsx:240 parseApiError(err).message`) is the same class and is deliberately NOT in this diff — file as follow-ups.
* **Dead catalog keys** (`referrals.bonus.expiresIn*` with the English fallback, `results.priceLess`, `profile.recent.justNow/yesterday` after this unit) belong to 14(b), not here.
* **Not measurable here**: Hermes `Intl` coverage (which is why `formatNumber` is pure JS). Also not measured: `eslint`'s Node API inside jest for test 5 — the implementer picks API vs `spawnSync` and records which.

---

## 9. PR-body facts (every sentence the PR must carry)

1. Base `ed75dc70`; W3-11 remainder after #141 (textAlign revert untouched). Client-only, unflagged, OTA-safe; the eslint fence and tests are ci-only; no backend file, no migration, no `package.json`/native change.
2. RTL-05: `HomeScreen.tsx:430-433` and `:540` rendered the backend's English `error` prose to Arabic users ("We don't compare this category", "Could not identify two products… Try: …"); both `success:false` arms now branch on `code` exactly like the `onError` path (`CONTENT_UNAVAILABLE` → the existing content-block alert, timeouts → `home.errors.timeout`, else `friendlyErrorKey`). `data.error` is no longer render input anywhere in HomeScreen. No new keys.
3. RTL-06: digit policy = ASCII everywhere an Arabic user reads a number (Ahmed sign-off requested in the PR). `ar.json`: 32 values rewritten from Arabic-Indic to ASCII digits, 4 `٪` → `%`; 0 key changes. Measured before: 32 Arabic-Indic vs 21 ASCII strings (79 vs 35 characters), 4 `٪` vs 2 `%`; after: 0 vs 53, 0 vs 6. New `formatNumber`/`formatPrice`/`toAsciiDigits`; 3 device-locale `toLocaleString()` sites (`ResultsAccordion.tsx:224/:664`, `ResultsContent.tsx:143`) and 1 bare `toLocaleDateString()` (`ProfileEditorialSections.tsx:74`) now follow the app policy; `formatDate()` output digits are policy-mapped.
4. RTL-07: prices render amount-then-symbol with the ISO minor unit (BHD/KWD/OMR 3, others 2) in BOTH languages: `12.345 د.ب`, `12.50 ر.س`, and — visible EN change — Results shows `329.000 BHD` where it showed `BHD 329`; smart-pick prices on Home stop truncating to whole dinars. Two never-called `formatPrice` helpers (`HistoryScreen.tsx:767-776`, `ResultsScreen.tsx:440-448`) deleted; the `currencyDisplay` source pin updated accordingly. Whole-dinar savings aggregates (3 sites) intentionally unchanged.
5. RTL-08: relative time goes through the catalog — `time.justNow` + `time.{minutes,hours,days}Ago` six-form families in both catalogs (36 + 1 keys); `formatTimeAgo(d, language, t)` gains a `t` parameter; the Profile-local `timeAgo` (English `3h`/`5d` to Arabic users) is deleted. Arabic counts 0/1/2/3-10/11-99/100+ now produce six distinct forms (was one). `profile.recent.justNow/yesterday` become unreferenced and are left for 14(b).
6. RTL-09: `i18next/no-literal-string` measured 0 messages at base while 7 user-visible literals shipped. Added `no-restricted-syntax` selectors (attributes `accessibilityLabel|accessibilityHint|placeholder|title|label`, `setError(...)`, `Alert.alert(...)`, `'N/A'`) to the screens+components block — measured 7 hits, 0 false positives, 562 with the plugin's `jsx-only` mode (rejected). Fixed: Results header a11y labels (`results.a11y.back/share`), `RegisterScreen.tsx:237` (`auth.registerFailed`), `ForgotPasswordScreen.tsx:41` (existing `auth.emailRequired`), the two `'N/A'` (dead code removed); `Step02Language.tsx:40 label="English"` allowed as a self-label. CI's existing `npx eslint` step blocks on the rule from this PR on. RegisterScreen `:130/:147` were already fixed by `8594826a`.
7. RTL-14: (c) `results.valueMatch.cheaper_of_two` → `cheaperOfTwo` + a plural-family fence (which also documents the dead `referrals.bonus.expiresIn*` families' English fallback, allowlisted); (d) shimmer sweep sign follows `I18nManager.isRTL` (read at render); (f) one percent glyph.
8. Tests: +9 suites; 4 existing pins updated (`ResultsContent.render:349-350`, `currencyDisplay.test:64-68`, `DimensionBars.delta_hero:93/104`, `i18n.bundle_c:25`) with the reason in each; A11, plurals, copy-policy, parity, referenced-key and textAlign suites untouched and green. `tsc` 0 errors; eslint 0 errors (warnings unchanged at 149).
9. Not verified in jest and owed to the device walkthrough: Hermes Arabic month names, shimmer look under RTL, screen-reader labels, tile fit at 3 decimals. Requires the pending `eas update` to reach phones.

---

## 10. Measurements run (command → observed output)

1. `git rev-parse HEAD` (worktree) → `ed75dc708b82c0b911c9de8a3e59d4418c6e278c`; `git status --short` → empty (before and after this spec; `.qa-w3b/` is ignored via `.gitignore:72 .qa-*/`).
2. `node -v` → `v24.11.1`; `node node_modules/typescript/bin/tsc -v` → `Version 5.9.3`; installed/pinned table in §1 (from `node_modules/<pkg>/package.json` vs `package.json`); `process.versions.icu` → `77.1`; `Intl.NumberFormat.supportedLocalesOf(['ar','ar-BH','ar-u-nu-latn'])` → all three.
3. Finding rows: `docs/investigations/2026-09-06-full-review-tables.md:222-225,410,414,541-542`; full text via `2026-09-06-full-review-verified.json` (`findings[]` by id, 442 entries); plan row `2026-09-06-full-review.md:139`; `2026-09-02-mobile-checkup-findings.md` grep for relative-time/jsx-text-only/toLocaleString/N/A/Arabic-Indic → no matches.
4. `node node_modules/jest/bin/jest.js --ci --roots ../.qa-w3b/probes --modulePaths "$(pwd)/node_modules" --testMatch "**/*.probe.test.ts" --testMatch "**/*.probe.test.tsx"` → 3 suites / 8 tests pass; outputs:
   ```
   formatTimeAgo(ar, 0 min)="الآن" 1="منذ 1 دقيقة" 2="منذ 2 دقيقة" 5="منذ 5 دقيقة" 15="منذ 15 دقيقة" 59="منذ 59 دقيقة"; 1h="منذ 1 ساعة" 2h="منذ 2 ساعة" 3h="منذ 3 ساعة" 11h="منذ 11 ساعة"; 1d="منذ 1 يوم" 2d="منذ 2 يوم" 5d="منذ 5 يوم"; en 5min="5m ago" 3h="3h ago"
   formatDate(ar)="١١ سبتمبر" formatDate(en)="Sep 11"; formatDate(ar) Arabic-Indic=true; formatTimeAgo(ar,5min) Arabic-Indic=false
   History(ar) 12.345 BHD="12.35 د.ب"; 12.5 SAR="12.50 ر.س"; Results(ar) 12.345 BHD="د.ب 12.345"; 1234.5 BHD="د.ب 1,234.5"; Home smart-pick(ar) 12.345="12 د.ب"; Results(en) 329 BHD="BHD 329"; History(en) 329 BHD="329.00 BHD"
   i18next 26.1.0; t(cheaper_of_two) ar no count/count:2/count:5 = "الأرخص بين الاثنين" ×3; synthetic six-form ar 0/1/2/5/15/100 → 6 distinct; ratingWithCount count:number 1234 → "4.5 · 1234 تقييم", count:string → "4.5 · 1,234 تقييم"; (1234).toLocaleString() → "1,234"
   HOME PROBE: SSE CONTENT_UNAVAILABLE title="لحظة — جرّب الضغط مرّة ثانية." body="We don't compare this category" asciiLetters=true; SSE codeless body="Could not identify two products to compare. Try: 'iPhone 15 vs Galaxy S24'" asciiLetters=true; URL CONTENT_UNAVAILABLE body="We don't compare this category" asciiLetters=true
   SHIMMER: LTR translateX=[-60]; RTL translateX=[-60]; EN count 0 => ZERO-EN | 1 => 1m ago(one) | 5 => 5m ago; AR 0/1/2/3/11/100 => ZERO-AR | ONE | TWO | FEW 3 | MANY 11 | OTHER 100; Intl.PluralRules native en select(0)=other
   ```
   (first attempt without `--modulePaths` failed with `Cannot find module 'react'/'i18next'/'@react-navigation/native'` — resolution walks up from `.qa-w3b/probes`, which has no `node_modules`.)
5. `… --testMatch "**/w311.i18next.probe.test.ts"` → `ar referrals.bonus.expiresInDays count=0 => Expires in 0 days | 1 => تنتهي خلال 1 يوم | 2 => Expires in 2 days | 3 => Expires in 3 days | 11 => Expires in 11 days | 100 => تنتهي خلال 100 أيام`; `history.hero.count` ar 0/1/2/3/11/100 → `لا قرارات هذا الشهر | قرار واحد هذا الشهر | قراران هذا الشهر | 3 قرارات هذا الشهر | 11 قرارًا هذا الشهر | 100 قرار هذا الشهر`; both catalogs carry all six `history.hero.count_*`; synthetic `time.minutesAgo` ar → `الآن | منذ دقيقة | منذ دقيقتين | منذ 5 دقائق | منذ 15 دقيقة | منذ 100 دقيقة`; en `1m ago | 5m ago`.
6. `PYTHONIOENCODING=utf-8 python scratchpad/b5/W3-11bcd/ar_census.py <SmartCompareApp>` → `leaf keys ar/en: 915 915 | chars: arabic-indic 79, western (all) 35, western outside {{}} 35, ext-arabic-indic 0 | strings: arabic-indic 32, western 21, both 0 | {{count}} keys 35 | percent U+066A 4, ASCII % 2 | bidi: referrals.share.reward.now/.later [U+200E] | empty: onboarding.language.subtitle (both) | incomplete suffix families (ar): referrals.bonus.expiresInDays/Hours/Minutes [_one,_other], results.valueMatch.cheaper_of [_two]; complete six-form families: 2`. Raw-file digits: `ascii 338 | arabic-indic 79` (338 − 35 = 303 inside key names). The 32 Arabic-Indic keys: `onboarding.priorities.subtitle, paywall.features.unlimited, demographics.subtitle, demographics.age.18_24/25_34/35_44/45_54/55_plus, referrals.share.reward.now/.later, referrals.share.toast.confirm, referrals.quiz.signupCtaSoft, onboarding.s3.subtitle, onboarding.s8.subtitle, onboarding.s9.budget_range/mid_range/premium_range/luxury_range/top_tier_range, onboarding.s12.title, onboarding.s13.factoid, onboarding.s14.stage_1/tip_1/tip_2, onboarding.s17.preview_body/tag_echoes_body, results.tips.cohort_priority/retailers/cohort_match, profile.password.new, register.benefits.daily, home.camera.slotIndicator`.
7. Docs grep for a digit convention (`CLAUDE.md`, `SmartCompareApp/CLAUDE.md`, `docs/*.md`, `.copy-policy.json`) → only `docs/claude-design-handoff/project-README.md:96` ("Numerals stay numeric … Never spelled out"); `CLAUDE.md:255` copy contract quoted in §3.1.
8. `git log --oneline 76ace90..HEAD -- <the touched screens/utils/config>` → 14 commits (`cc7c7ace` W3-11a … `e001c36a`); `git log -S"auth.googleFailed" -- SmartCompareApp/src/screens/RegisterScreen.tsx` → `8594826a`.
9. ESLint (installed plugin 6.1.4; `lib/helper/shouldSkip.js:3-11` include/exclude semantics read; `lib/options/defaults.js` read):
   * base CI command → `exit=0`, `FILES 148 | errors 0 | warnings 149 | i18next/no-literal-string messages 0` (`eslint.base.ci.json`; the earlier `eslint.base.json` from this worktree agrees).
   * `eslint.jsx-only.config.js` → `FILES 148 | errors 562 | warnings 149 | i18next messages 562`.
   * `eslint.targeted.config.js` (v1) → `errors 39 | i18next messages 15 | no-restricted-syntax 24` (false positives listed in §3.5).
   * `eslint.targeted2.config.js` (v2, the design) over `src/screens/**` + `src/components/**` → `FILES 96 | errors 7 | warnings 113`, the 7 hits in §3.5; wall 15 s.
   * `grep no-restricted-syntax node_modules/eslint-config-expo/flat/**` → none.
10. `node node_modules/typescript/bin/tsc --noEmit` → `exit=0` (5.6 s).
11. `node node_modules/jest/bin/jest.js --ci <17 neighbour suites>` → `Test Suites: 17 passed, 17 total | Tests: 221 passed, 221 total | Snapshots: 0 total` (`copy-policy`, `rtl/textAlignLogical.contract`, `i18n/no-deleted-keys`, `HistoryScreen.bundleE.s3`, `i18n.bundle_c`, `i18n.test`, `i18n/no-missing-referenced-keys`, `utils/__tests__/currencyDisplay`, `i18n/plurals`, `errorCopy.a11`, `LoadingScreenVariants.wave2`, `components/DimensionBars.delta_hero`, `LoadingScreen.bundleE`, `HomeScreen.errorCopy.a11`, `components/ResultsContent.render`, `RegisterScreen.deferredCode`, `ProfileEditorialSections.imageUrl`).
12. Reachability greps: `grep -n formatPrice src/screens/HistoryScreen.tsx` → `767` only; `grep -in price src/screens/HistoryScreen.tsx` outside 767-776 → none; `grep -n formatPrice src/screens/ResultsScreen.tsx` → `440` only; `grep -n localizedCurrency src/screens/ResultsScreen.tsx` → `74` (import), `443`; `grep -rn "expiresIn|results.priceLess|language.subtitle" src --include=*.ts --include=*.tsx` (excluding `src/i18n/`) → none; `grep -n "layer" src/types/types.ts` → none; `CLAUDE.md`/`ci.yml:264-274` → jest `--ci`, `eslint "src/**/*.{ts,tsx}"`, `tsc --noEmit` all in `frontend-tests`.
13. Files read in full or at the cited ranges: `formatDate.ts`, `rtl.ts`, `i18n/index.ts`, `errorCopy.ts`, `eslint.config.js`, `currencyDisplay.ts`, `useLanguage.ts`, `jest.config.js`, `tsconfig.json`, `__mocks__/react-i18next.ts`, `__mocks__/react-native-reanimated.ts`, `__tests__/setup.ts`, `HomeScreen.errorCopy.a11.test.tsx`, `errorCopy.a11.test.ts:194-210`, `plurals.test.ts`, `i18n.test.ts:12-27`, `no-missing-referenced-keys.test.ts:1-70`, `no-deleted-keys.test.ts`, `copy-policy.test.ts` + `.copy-policy.json`, `currencyDisplay.test.ts`, `ResultsContent.render.test.tsx:29-45,335-352`, `DimensionBars.delta_hero.test.tsx:85-106`, `LoadingScreen.bundleE.test.tsx:125-140`, and the source ranges quoted in §3.

---

## FABLE REVIEW RULINGS (binding, 2026-09-11)

Verdict: **APPROVED_WITH_RULINGS.** Every census number, every file:line anchor, the base-eslint
baseline, the toolchain table, the 17-suite neighbour baseline and all four jest probes were
re-measured independently and reproduce EXACTLY. Four claims are refuted and are corrected below;
eight more are tightened. The red phase executes §1–§10 **as amended by these rulings**, which win
wherever they disagree with the body above.

---

### R1 — The base moved. Rebase on `b63a8368`; every client measurement still stands.

`git rev-parse HEAD` in `sc-w3-ar` → **`b63a8368b7910a946020438a5447bbcd6b792805`** (= `origin/main`,
branch `feature/s65-w3-11b-arabic-pack`), NOT the `ed75dc70` §1/§10.1 record.
`git merge-base --is-ancestor ed75dc70 HEAD` → true; 10 commits between (PRs #155/#156/#157/#158/#159 —
W3-2 comparison_id echo, W1-5 limiter endpoint key, W1-6 shutdown drain, W4-5 showable-name identity,
a security-assert fix).

`git diff --stat ed75dc70..b63a8368` = 13 files, 3,770 insertions:
`Procfile`, `app/api/text_routes.py`, `app/main.py`, `app/middleware/rate_limiter.py`,
`app/services/{feedback_service,price_service}.py`, `app/utils/async_utils.py`, `railway.json`,
`tests/test_{comparison_id_echo,limiter_endpoint_key,showable_name_identity,shutdown_drain}.py`,
`tests/test_security_regression.py`.

**ZERO files under `SmartCompareApp/`.** Therefore every line anchor, census figure, probe output and
lint/tsc/jest baseline in §1–§10 remains valid verbatim at `b63a8368`. The red phase records the base
as `b63a8368` in the spec header and the PR body; §1 and §9.1 are corrected to that SHA.

---

### R2 — REFUTED: the SSE `onComplete` `success:false` arm is UNREACHABLE. RTL-05's only LIVE site is the URL path.

§3.1, §4.3 and §9.2 assert that `HomeScreen.tsx:430-433` renders backend English prose to Arabic
users on the SSE path. **It cannot.** Measured chain at `b63a8368`:

1. `src/services/api.ts:774-776` — `case 'complete': dispatchTerminal(parsed)`; `:781-785` —
   `case 'settle_complete':` … `dispatchTerminal(parsed)`. Those are the only two producers of
   `onComplete` on the streaming leg.
2. `src/services/api.ts:688-700` — `const dispatchTerminal = (parsed) => { … if (parsed && parsed.success === false) { … callbacks.onError?.(Object.assign(new Error('stream_incomplete'), { response: { status: 503, data: { code, error: parsed.error } } })); } else { callbacks.onComplete?.(parsed); } … }`.
   A `success:false` terminal payload is routed to **`onError`**, never to `onComplete`.
3. `src/services/api.ts:603-618` — the non-streaming fallback: `if (response.data.success) callbacks.onComplete?.(response.data); else callbacks.onError?.(…)`. Same routing.
4. Backend, streaming path: `app/services/structured_comparison_service.py:4069-4074` yields
   `("error", {"success": False, "error": "We don't compare this category", "code": "CONTENT_UNAVAILABLE", "layer": "query_prefilter"})` and `:4116-4121` yields `("error", {… "Could not identify two products to compare. Try: 'iPhone 15 vs Galaxy S24'" …})`.
   Both are **`error` events**, not `complete`. `api.ts:788-800` routes `case 'error'` to `onError`.
5. `HomeScreen.tsx:450-483` (`onError`) already handles exactly these: `CONTENT_UNAVAILABLE` →
   `handleContentUnavailable('text', layer)` at `:452-455`; everything else → `t(friendlyErrorKey(parsed.code))`
   at `:482`. **Green today.**

Consequence: `HomeScreen.tsx:418-434`'s whole `else if (!data.success)` branch — including the
`data.error ||` at `:433` — is **defensive code no shipped transport can reach**, the same class the
spec correctly identified for the two `formatPrice` helpers (§2.3). The writer's probe measured it
"red" only because `w311.home.probe.test.tsx` invokes `handlers.onComplete({success:false, …})`
DIRECTLY, bypassing `api.ts`. The `1,500 failures` impact figure quoted from the finding does **not**
attach to this arm.

`HomeScreen.tsx:540` IS live: `handleUrlCompare` calls `apiPost('/api/v1/url/compare', …)` directly
(`:518-529`) and renders `response.data.error` at `:540`; `/url/compare` runs the SYNC
`compare_from_text`, whose `:3493-3498` and `:3541-3545` returns carry those exact English literals.

**Binding:**
(a) §3.1 and §9.2 are corrected: the user-visible RTL-05 defect is the **URL path (`:540`) only**;
    the SSE `onComplete` arm is a defensive arm that would leak prose **if** `api.ts`'s routing ever
    changed. Do not claim Arabic users see the SSE bodies today.
(b) Keep the fix on BOTH arms (defence-in-depth, zero cost) and keep tests 1(a)(b)(d) — but each must
    carry a comment naming it a defensive-arm pin with the `api.ts:688-700` evidence, so no later
    reader mistakes it for a live-path regression test.
(c) **Add test 1(e), a reachability pin** (this is the test that actually protects the user):
    drive `streamComparison`'s SSE reader with a `complete` frame carrying
    `{success:false, code:'CONTENT_UNAVAILABLE', error:"We don't compare this category"}` and assert
    `onError` fired and `onComplete` did NOT. Red-phase note: this is GREEN at base — it is an
    explicitly-exempt forward guard under R8's carve-out, and its justification is that it is the
    invariant that makes (a)(b)(d) unreachable. Mutation: make `dispatchTerminal` call `onComplete`
    unconditionally ⇒ red.
(d) Test 1(c) (URL path via `mockApiPost.mockResolvedValueOnce`) is the **primary** RTL-05 red test.
    Promote it to first position in the file and say so in the PR.
(e) The additive `layer?: string` on `ComparisonResult` (§4.8) stays: `:540`'s `response.data.layer`
    is real (the sync envelope at `:3493-3498` carries it).

---

### R3 — REFUTED: ESLint's Node API CANNOT run under jest here. `spawnSync` is MANDATORY, not a choice.

§5 test 5 and §8 leave "ESLint Node API vs `spawnSync`" to the implementer. Measured
(`.qa-w3b/probes/w311.eslintapi.probe.test.ts`, `new ESLint({cwd: APP, overrideConfigFile: …}).lintText(...)`):

```
TypeError: A dynamic import callback was invoked without --experimental-vm-modules
  at dynamicImportConfig (node_modules/eslint/lib/config/config-loader.js:186:38)
  at loadConfigFile (…/config-loader.js:276:15)
  at ConfigLoader.calculateConfigArray (…/config-loader.js:589:23)
  at ESLint.lintText (node_modules/eslint/lib/eslint/eslint.js:1139:4)
Test Suites: 1 failed
```
eslint 9.39.4 loads a flat config through a dynamic `import()`; jest's CJS VM refuses it without
`NODE_OPTIONS=--experimental-vm-modules`, which neither `jest.config.js` nor CI
(`.github/workflows/ci.yml:263-264`, `cd SmartCompareApp && npx jest --ci`) sets — and this unit does
NOT touch `jest.config.js` (§4.8).

The `spawnSync` path works. Measured (`.qa-w3b/probes/w311.eslintspawn.probe.test.ts`,
`spawnSync(process.execPath, [node_modules/eslint/bin/eslint.js, '--config', <cfg>, '--stdin', '--stdin-filename', 'src/screens/__fence_fixture__.tsx', '-f', 'json'], {cwd: APP, input: code})`):

```
pos attr:               restricted=1 other=[react/jsx-no-undef@1] exit=1
pos setError ||:        restricted=1 other=[]                     exit=1
pos Alert:              restricted=1 other=[]                     exit=1
pos N/A:                restricted=1 other=[]                     exit=1
pos concat:             restricted=1 other=[]                     exit=1
neg t(??):              restricted=0 other=[]                     exit=0
neg defaultValue/cancel:restricted=0 other=[]                     exit=0
neg label English:      restricted=0 other=[react/jsx-no-undef@1] exit=1
neg testID:             restricted=0 other=[react/jsx-no-undef@1] exit=1
PASS (191.832 s)
```

**Binding:** test 5 uses `child_process.spawnSync` on `node_modules/eslint/bin/eslint.js` by PATH
(never `npx`), `cwd` = `SmartCompareApp`, `--stdin --stdin-filename src/screens/<fixture>.tsx -f json`,
and `--config` pointing at the repo's own `eslint.config.js` (so the test lints the SHIPPED rule, not
a copy). Do not attempt the Node API. §8's "the implementer picks and records which" is struck.

---

### R4 — REFUTED: test 5's negative fixtures must assert on `no-restricted-syntax` messages, not on "0 errors".

§5 test 5 says "Negative fixtures, each must yield 0 errors". Measured (R3 table): three of the four
negatives yield **1 `react/jsx-no-undef` error** and `exit=1`, because the fixtures reference
undeclared components (`<Option>`, `<View>`, `<Pressable>`). A "0 errors" assertion is red forever.

**Binding:** every assertion in test 5 filters `messages` to `ruleId === 'no-restricted-syntax'`.
Positives assert `>= 1`; negatives assert `=== 0`. Never assert on `errorCount` or the process exit
code. The N/A and `setError`/`Alert` fixtures (no JSX) are the only ones that happen to exit 0 —
do not rely on that.

---

### R5 — REFUTED: the fence as §4.6 writes it yields **6** errors, not 7.

§3.5's "7 hits" was measured with `.qa-w3b/probes/eslint.targeted2.config.js`, which does **not**
contain the `:not([value='English'])` allowance that §4.6 then adds. Re-measured with the spec's
exact §4.6 selector (`.qa-w3b/probes/eslint.fable.config.js`, CI command
`node node_modules/eslint/bin/eslint.js "src/**/*.{ts,tsx}"`):

```
FILES 148 errors 6 warnings 149 restricted-hits 6   exit=1
  src/components/results/ResultsContent.tsx:208:30   attr literal
  src/components/results/ResultsContent.tsx:224:30   attr literal
  src/screens/ForgotPasswordScreen.tsx:41:34         setError literal
  src/screens/HistoryScreen.tsx:768:83               N/A
  src/screens/HistoryScreen.tsx:772:87               N/A
  src/screens/RegisterScreen.tsx:237:34              setError literal
```
`Step02Language.tsx:40 label="English"` is correctly suppressed — esquery accepts
`Literal[value=/…/]:not([value='English'])` on the installed eslint 9.39.4. Base, same command:
`FILES 148 | errors 0 | warnings 149 | i18next/no-literal-string 0` (rule-id histogram:
`no-unused-vars 78, import/first 13, array-type 22, no-require-imports 13, import/no-duplicates 6,
import/no-named-as-default 6, exhaustive-deps 6, no-named-as-default-member 4, null 1`) — §3.5 and
§10.9 CONFIRMED.

**Binding:** §7 gate 5 reads "the new rule adds **6** errors until the sites are fixed"; §9.6 reads
"measured **6** hits with the self-label allowance (7 without it), 0 false positives". The six sites
are exactly the six the unit fixes, so gate 5's end state (0 errors / 149 warnings) is unchanged.

---

### R6 — REFUTED: `MiniVsCard` has no `useTranslation()` and no `i18n`. §4.5's Profile fix is not executable as written.

§4.5 says "the card component that renders `:142` takes `i18n` from its `useTranslation()`".
Measured `src/components/ProfileEditorialSections.tsx`:

```
 80: function MiniVsCard({
 81:   item,
 82:   onPress,
 83:   t,
 84: }: {
 85:   item: RecentDecisionItem;
 86:   onPress?: () => void;
 87:   t: (k: string) => string;
 88: }) {
…
142:         {item.winner_name} · {timeAgo(item.created_at, t)}
```
`useTranslation()` lives in the PARENT `RecentDecisionsRow` (`:153`, `const { t } = useTranslation();`
— `t` only, no `i18n`), which renders `<MiniVsCard … t={t} />` at `:222`. Two blockers: there is no
`i18n` anywhere in the file, and the `t` prop type `(k: string) => string` rejects
`t('time.hoursAgo', { count })`.

**Binding:** the fix (a) widens the `t` prop type to
`(k: string, o?: Record<string, unknown>) => string`, (b) destructures `const { t, i18n } = useTranslation();`
at `:153` and passes `language={(i18n.language as AppLanguage) ?? 'en'}` into `MiniVsCard` as a new
prop (do NOT add a second `useTranslation()` inside the card — the `t`-as-prop shape is what the
existing `ProfileEditorialSections.imageUrl` suite renders against), and (c) calls
`formatTimeAgo(item.created_at, language, t)` at `:142`. Measured: no test anywhere asserts
`timeAgo`'s output, and `profile.recent.justNow` / `profile.recent.yesterday` have no other consumer,
so nothing else moves.

---

### R7 — §4.2's enforcement claim is overstated, and "the fence flips with the constant" is FALSE.

Complete measured inventory at `b63a8368` (`grep -rn "toLocale\|toFixed" src`):

*8 `toLocale*` sites* — `LoadingRings.tsx:84` and `StatBlock.tsx:29` (both already pinned `'en-US'`,
P14 CONFIRMED), `ProfileEditorialSections.tsx:74`, `ResultsAccordion.tsx:224` and `:664`,
`ResultsContent.tsx:143`, `ResultsScreen.tsx:443` (dead), `formatDate.ts:15`.
*10 `toFixed` sites* — `HomeEditorialSections.tsx:142/:187/:293`, `ProfileEditorialSections.tsx:398`,
`ResultsAccordion.tsx:227/:663/:666`, `HistoryScreen.tsx:184/:773/:775` (the last two dead).

The unit routes 5 of them. **`ResultsAccordion.tsx:227/:663/:666` (rating `toFixed(1)`),
`HomeEditorialSections.tsx:293`, `HistoryScreen.tsx:184` and `ProfileEditorialSections.tsx:398`
(savings aggregates) stay unrouted**, and the 35 `{{count}}` families are interpolated by i18next,
not by `formatNumber`. Under `APP_DIGIT_SYSTEM = 'latn'` all of those already emit ASCII, so the
POLICY holds — but the mechanism does not.

**Binding:** §4.2 (ii) is rewritten to "every runtime number **on a price, review-count or date
surface** goes through `formatNumber`/`formatPrice`/`formatDate`; rating `toFixed(1)` and the three
whole-dinar savings aggregates emit ASCII directly and are conformant-by-construction under `latn`",
and §4.2's closing sentence "the fence flips with the constant" is struck and replaced with:
"**flipping `APP_DIGIT_SYSTEM` to `'arab'` is NOT a one-constant change** — it additionally requires
an i18next `interpolation.format` hook (or a `postProcess`) in `src/i18n/index.ts` for the 35
`{{count}}` families, plus routing the 6 unrouted `toFixed` sites; that is a separate unit." Carry the
same correction into the Ahmed sign-off item in §8 so the inverse is not costed as "one constant plus
21 strings".

---

### R8 — Decoration: two assertions are GREEN at base. Make them red or exempt them explicitly.

(a) **§5 test 6(a) rule (ii)** ("every `ar.json` family has all six forms") is **vacuously green
today**: measured suffix families in `ar.json` are exactly `history.hero.count` [6],
`home.savings.count` [6], `referrals.bonus.expiresIn{Days,Hours,Minutes}` [`_one`,`_other`] (all three
allowlisted) and `results.valueMatch.cheaper_of` [`_two`] (caught by rule (i)). Nothing is left for
(ii) to fail on. **Binding:** give rule (ii) an explicit REQUIRED-FAMILIES list
`['time.minutesAgo','time.hoursAgo','time.daysAgo','history.hero.count','home.savings.count']`, each
of which must carry all six forms in `ar.json` and at least `_one`+`_other` in `en.json`. The three
`time.*` families do not exist at base, so (ii) is then RED for the right reason. Mutation named in
§5 (remove `time.minutesAgo_few` from `ar.json`) then actually reddens it.

(b) **§5 test 2(a)** reads the fix's own `APP_DIGIT_SYSTEM` back and branches on it — a tautology the
implementer can satisfy by flipping the constant. **Binding:** the test asserts
`expect(APP_DIGIT_SYSTEM).toBe('latn')` as a standalone, comment-annotated policy pin (changing it is
then a deliberate edit that Ahmed's sign-off authorises), and asserts **unconditionally** that no
`ar.json` value matches `/[٠-٩۰-۹]/`. Drop the `if/else` mirror-rule branch.

(c) §7 gate 1 ("a test that is green before the fix is deleted, not kept") is amended: R2(c) and
R8(a)'s en-side `_one`+`_other` clause are **named, justified forward guards** and are exempt. No
other exemption is granted.

---

### R9 — Test 2(b) must not assert the literal `"11"`; CI runs a different node than this box.

Local: node **v24.11.1**, `process.versions.icu` **77.1**;
`new Date(Date.UTC(2026,8,11,12)).toLocaleDateString('ar-SA',{month:'short',day:'numeric'})` →
`"١١ سبتمبر"`, with `new Intl.DateTimeFormat('ar-SA').resolvedOptions()` = `{calendar:'gregory', numberingSystem:'arab'}`.
CI pins **node-version: '20'** (`.github/workflows/ci.yml:253-255`). The day number `11` is a product
of ICU resolving `ar-SA` to the **gregory** calendar; an ICU that resolved `islamic-umalqura` would
print a different day AND a different month word, and neither the spec nor this review can measure
node 20's ICU from here.

**Binding:** test 2(b) asserts only engine-independent facts —
(i) `toAsciiDigits('١١ سبتمبر') === '11 سبتمبر'` as a pure unit (this is the real subject);
(ii) `formatDate(<fixed date>, 'ar')` matches `/^\d/` and does NOT match `/[٠-٩۰-۹]/`;
(iii) `formatDate(…,'ar')` and `formatTimeAgo(…, 'ar', t)` report the same digit class.
Do NOT assert the literal `'11'`, the month word, or the full string. The Hermes month-name risk
already recorded in §8 is unchanged and stays device-only.

---

### R10 — `ResultsAccordion.tsx:664` must keep passing a STRING to `count`.

Measured on the installed i18next 26.1.0 against the real `ar.json`:
`t('results.reviews.ratingWithCount', {rating:'4.5', count: 1234})` → `"4.5 · 1234 تقييم"`;
with `count: '1,234'` → `"4.5 · 1,234 تقييم"`. `results.reviews.ratingWithCount` has **no**
`_zero/_one/_two/_few/_many/_other` family in either catalog (census), so `count` here is an
interpolation variable that i18next also treats as a plural trigger.

**Binding:** `formatNumber` returns `string`, and the `:664` edit is
`count: formatNumber(ratingCount)` — the value must stay a string. A red-phase agent that passes the
raw number "because formatNumber is for display" silently drops the grouping separator. Add an
assertion to test 3 (or the accordion suite) pinning the rendered `1,234`.

---

### R11 — Test 5 must not spawn nine ESLint processes.

Measured: the 9-fixture `spawnSync` probe took **191.8 s** (~20 s per spawn, config resolution
dominates). §7 gate 6 runs the full 278-suite estate once; a 3-minute single file is a real tax on
every CI run.

**Binding:** batch the fixtures — write all five positives into ONE temp fixture file and all four
negatives into a second (`os.tmpdir()`, or `--stdin` twice), assert per-LINE on the returned message
objects (`message.line`), and cap the file at **2** ESLint invocations. Record the measured wall time
in the PR body. If the batched run still exceeds ~60 s, say so and let the reviewer decide whether the
CI-level `eslint` exit code (§5 test 5(c)) is sufficient on its own.

---

### R12 — CONFIRMED, re-measured independently (no change required).

| claim | independent measurement |
|---|---|
| toolchain (§1) | node v24.11.1; `node node_modules/typescript/bin/tsc -v` → **Version 5.9.3** (pin `~5.9.2`); i18next **26.1.0** (`^26.0.1`); react-i18next 17.0.7 (`^17.0.1`); intl-pluralrules 2.0.1; eslint **9.39.4** (`^9.39.4`); eslint-plugin-i18next **6.1.4**; jest 29.7.0; react-native 0.81.5; expo 54.0.34 (`~54.0.33`) — all read from `node_modules/<pkg>/package.json` vs `package.json` |
| census (§3.2, §10.6) | **exact reproduction**: 915 leaf keys each, key sets equal; chars arabic-indic **79** / western **35** (35 outside `{{}}`) / ext-arabic-indic **0**; strings **32 / 21 / 0 both**; raw-file ascii digits **338**; `٪`×**4** (`loading.tip.peer_prioritize`, `onboarding.s13.factoid`, `onboarding.s14.tip_1`, `results.tips.cohort_priority`) vs `%`×**2** (`results.priceLess`, `paywall.plan.yearly_sub`); 35 `{{count}}` keys; the 32-key list matches §10.6 item-for-item; bidi U+200E only in `referrals.share.reward.now/.later`; only empty value `onboarding.language.subtitle` |
| anchors | HomeScreen `:429` isTimeout / `:430-433` Alert / `:540` Alert / `:336` `handleContentUnavailable` / `:70` `friendlyErrorKey` import; `formatDate.ts:14` `'ar-SA'`, `:28-39` the 8 literals; `ProfileEditorialSections.tsx:63-77` `timeAgo`, `:70` `` `${hrs}h` ``, `:73` `` `${days}d` ``, `:74` bare `toLocaleDateString()`, `:142` call; `HistoryScreen.tsx:414-415`; `ResultsContent.tsx:143/:208/:224`; `ResultsAccordion.tsx:224/:664`; `DimensionBars.tsx:340` render (no count) / `:373` key; `HomeEditorialSections.tsx:142/:187`; `RegisterScreen.tsx:137/:143/:159/:164` already `t(…)` and `:237 result.error \|\| 'Registration failed'`; `ForgotPasswordScreen.tsx:41 t('auth.email') + ' is required'`; `eslint.config.js:52-58` with `mode:'jsx-text-only'` at `:55`; `__mocks__/react-native.ts:87-91` mutable `I18nManager` |
| shimmer (§3.6d) | `LoadingScreenVariants.tsx:421 SHIMMER_TRANSLATE_PX = 60`, `:528 GhostField`, `:529 useSharedValue(-SHIMMER_TRANSLATE_PX)`, `:534 withTiming(SHIMMER_TRANSLATE_PX…)`, `:544-546 useAnimatedStyle`. Probe: `LTR translateX=[-60]; RTL translateX=[-60]`. It is the ONLY sweep of its kind (`grep -rn translateX src` → CohortBadge/SlideTransition entrance animations only). The verifier's `:447` anchor was `76ace90`-era and has drifted; §2.1's re-location is correct. |
| dead code (§2.3) | `grep -n formatPrice src/screens/HistoryScreen.tsx` → `767` only; `grep -in price` on that file → only `:767-775`; `grep -n formatPrice src/screens/ResultsScreen.tsx` → `440` only; `localizedCurrency` in ResultsScreen at `:74` (import) + `:443` only. The `currencyDisplay.test.ts` SITES pin sits at `:63-67`. |
| backend literals (§3.1) | `structured_comparison_service.py:3493-3498` and `:3541-3545` verbatim (sync path), `:4069-4074` and `:4116-4121` verbatim (streaming, as `error` events — see R2) |
| base lint / tsc / suites | eslint CI command: **148 files, 0 errors, 149 warnings, 0 i18next messages**, exit 0. `node node_modules/typescript/bin/tsc --noEmit` → **exit 0** (26.8 s). The 17 named neighbour suites → **17 passed / 221 tests / 0 failed**. |
| `toFixed` arithmetic behind §5 test 3 | `(12.345).toFixed(3)="12.345"`, `(12.5).toFixed(2)="12.50"`, `(8.75).toFixed(3)="8.750"`, `(329).toFixed(3)="329.000"`, `(1234.5).toFixed(3)="1234.500"`, `(0.5).toFixed(0)="1"`. Every §4.1/§5 target string is reachable by pure `toFixed` + grouping. (Recording the rounding trap the spec should name: `(1.005).toFixed(2)="1.00"`, `(2.675).toFixed(2)="2.67"` — binary rounding, not half-up. Say so in the `formatNumber` header comment.) |
| finding fidelity | RTL-07's `test_first` is verbatim `expect(formatPrice(12.345,'BHD',t,'ar')).toBe('12.345 د.ب')` and `('12.50 ر.س')` — §3.3 takes the strings from the finding, not from taste ✓. `currency.KWD` = `د.ك` (ar) / `KWD` (en), so `'8.750 د.ك'` resolves ✓. `auth.emailRequired` EXISTS in both catalogs ✓; `auth.registerFailed`, `results.a11y.back`, `results.a11y.share`, `time.*` are absent ✓. |
| pin completeness | No test file in the repo contains an Arabic-Indic digit, so rewriting the 32 values breaks no pin. `home.smart_pick.bhd` has exactly two consumers (`:142`, `:187`) and there is **no unused-key fence** (`no-deleted-keys.test.ts` pins only `results.whatsNext`/`results.save` + count parity), so leaving the key orphaned is safe. `winner_price_bhd`/`runner_up_price_bhd` render ONLY at those two sites; no existing test asserts their rendered text. No test asserts `timeAgo` output. `CounterTicker` is used once (`InviteeQuizScreen:196`, `suffix="%"`) and is not a price site. The four pin updates in §4.8 are therefore COMPLETE. |
| P1 is safe | Every test in `HomeScreen.errorCopy.a11.test.tsx` drives `onError` or the URL `catch`; none drives `onComplete` with `success:false`. The `:540` arm the unit changes is exercised only by the new test 1(c). |
| fence plumbing | `jest.config.js` `testMatch: ['**/__tests__/**/*.test.ts(x)']` covers `__tests__/lint/`, `__tests__/i18n/` and `src/utils/__tests__/` ✓. `no-restricted-syntax` is absent from `eslint-config-expo/flat` ✓. `.gitignore:72 .qa-*/` ✓ (git status empty before and after this review). |
| i18next runtime | `t('results.valueMatch.cheaper_of_two')` under `ar` resolves to `"الأرخص بين الاثنين"` for no-count / 2 / 5 ⇒ §2.2's "14(c) runtime was never red" CONFIRMED. Synthetic six-form `ar` family → 6 distinct strings. `ar referrals.bonus.expiresInDays` counts 0/2/3/11 fall back to the ENGLISH `"Expires in N days"` ⇒ the allowlist rationale CONFIRMED. `_zero` is honoured for EN count 0. Note for the implementer: both catalogs are **FLAT dotted-key maps** (915 top-level string keys, no nesting) resolved by i18next's default `keySeparator: '.'` deep-find; new keys are added as flat `"time.minutesAgo_few": "…"` entries, never as nested objects. |

---

### R13 — Scope decisions the spec makes against its findings: recorded and UPHELD.

Each of these departs from the finding's own `fix` text. All three are correct; the PR must name them
so a later reader does not read them as omissions.

1. **RTL-08's `common.notAvailable`** is not added, because the only two `'N/A'` sites are inside the
   dead `HistoryScreen` helper this unit deletes (measured: the only other `N/A` occurrences in
   `src/screens`+`src/components` are in COMMENTS at `ResultsAccordion.tsx:54` and
   `ResultsContent.tsx:137`, which `Literal[value='N/A']` cannot match). Upheld.
2. **RTL-08/-09's "bring `src/utils` and `src/hooks` under the i18next rule"** is declined: under
   `mode:'jsx-text-only'` the plugin skips any node whose direct parent is not a `JSXElement`/
   `JSXFragment`, so un-exempting a directory with no JSX is a literal no-op. Upheld — **on condition
   that pin P8 ships exactly as §6 specifies** (`formatDate.ts` contains no `/[؀-ۿ]/` and none of
   `'just now'|'m ago'|'h ago'|'d ago'`). P8 is the ONLY thing standing between this class and a
   silent return; do not weaken it.
3. **RTL-07's 4-parameter `formatPrice(amount, code, t, language)`** is implemented as 3 parameters
   (`language` dropped, digits taken from the module-level policy). Upheld — but say it in the PR, and
   note that R7's `'arab'` caveat is the reason the finding wanted the 4th parameter.

---

### R14 — Red-phase execution order (binding).

1. Rebase/verify on `b63a8368`; print `git rev-parse HEAD` and `git status --short` (must be empty).
2. Print `node node_modules/typescript/bin/tsc -v` once. Never `npx`.
3. Write the 9 test files of §7.2 **plus** R2(c)'s reachability pin, with R4/R8/R9/R10/R11 applied.
4. Run each new file by path; record the RED reason verbatim against the §5 row it belongs to. Test
   1(e) and rule (ii)'s en-side clause are the only permitted greens (R8(c)).
5. Do NOT edit any source file, any catalog, or `eslint.config.js` in the red phase.
6. Hand over with: the red transcript, the 6-hit fence measurement (R5), the measured wall time of
   test 5 (R11), and the four pin updates left UNAPPLIED for the green phase.

`ready_for_red = true` with these rulings appended. Every open question in §8 is now resolved except
the two that are genuinely Ahmed's (the `latn` digit-policy and `%`-glyph sign-off, and the on-device
Arabic walkthrough) — neither blocks the red phase, because the spec's choice is implementable and
reversible, and R7 now states honestly what reversing it costs.
