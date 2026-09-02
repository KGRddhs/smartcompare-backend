const translations: Record<string, Record<string, string>> = {
  en: {
    'home.freeCounter': '{{used}} of {{total}} free',
    'home.search.placeholder': 'Search products...',
    'home.search.recent': 'Recent',
    // Bundle C (spec § 7c) — personalization chip needs interpolation.
    'results.personalization.chip_template': 'Weighted {{arrows}} (based on your priorities)',
    'results.personalization.arrow_up': '↑ {{dim}}',
    'results.personalization.arrow_down': '↓ {{dim}}',
    // #105 — confidence-sheet composed lines (toConfidenceLines). Without
    // these the sheet tests would render literal key strings and the
    // no-backend-internals leak assertions would prove nothing.
    'results.confidence.sheet.price.sources': 'Checked across {{n}} retail sources.',
    'results.confidence.sheet.price.method_retailer': 'Price confirmed from retailer listings.',
    'results.confidence.sheet.price.method_converted': 'Price converted from an international retailer listing.',
    'results.confidence.sheet.price.freshness_live': 'Pricing checked just now.',
    'results.confidence.sheet.price.freshness_cached': 'Pricing from a recent check.',
    'results.confidence.sheet.reviews.count': '{{n}} reviews considered.',
    'results.confidence.sheet.reviews.source': 'Ratings sourced from {{source}}.',
    'results.confidence.sheet.reviews.verified': 'Review source cross-checked.',
    'results.confidence.sheet.specs.citations': 'Backed by {{n}} source citations.',
    'results.confidence.sheet.specs.verified': 'Key specs cross-checked against sources.',
  },
};

let currentLang = 'en';

// M21 mobile-jank — `t` and the returned object are STABLE singletons, like
// real react-i18next (whose `t` is referentially stable between renders and
// only swaps on language change). The old mock fabricated a new `t` closure
// per useTranslation() call, which made every `useCallback(..., [t])` in app
// code churn each render and falsely defeated React.memo in tests. `t` reads
// `currentLang` live, so changeLanguage behavior is unchanged.
const stableT = (key: string, params?: Record<string, any>) => {
  const dict = translations[currentLang] || translations['en'];
  let value = dict[key] || key;
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      value = value.replace(new RegExp(`\\{\\{${k}\\}\\}`, 'g'), String(v));
    }
  }
  return value;
};

const stableI18n = {
  get language() {
    return currentLang;
  },
  changeLanguage: jest.fn(async (lang: string) => {
    currentLang = lang;
  }),
};

const stableUseTranslationResult = {
  t: stableT,
  i18n: stableI18n,
};

export function useTranslation() {
  return stableUseTranslationResult;
}

export function initReactI18next() {}
initReactI18next.type = '3rdParty';
initReactI18next.init = jest.fn();
