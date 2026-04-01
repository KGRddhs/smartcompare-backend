const translations: Record<string, Record<string, string>> = {
  en: {
    'home.freeCounter': '{{used}} of {{total}} free',
    'home.search.placeholder': 'Search products...',
    'home.search.recent': 'Recent',
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
