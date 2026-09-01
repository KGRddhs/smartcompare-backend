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

export function useTranslation() {
  return {
    t: (key: string, params?: Record<string, any>) => {
      const dict = translations[currentLang] || translations['en'];
      let value = dict[key] || key;
      if (params) {
        for (const [k, v] of Object.entries(params)) {
          value = value.replace(new RegExp(`\\{\\{${k}\\}\\}`, 'g'), String(v));
        }
      }
      return value;
    },
    i18n: {
      language: currentLang,
      changeLanguage: jest.fn(async (lang: string) => {
        currentLang = lang;
      }),
    },
  };
}

export function initReactI18next() {}
initReactI18next.type = '3rdParty';
initReactI18next.init = jest.fn();
