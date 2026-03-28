import { useCallback } from 'react';
import { I18nManager } from 'react-native';
import { useTranslation } from 'react-i18next';
import { saveLanguage } from '../i18n';

export function useLanguage() {
  const { i18n } = useTranslation();
  const isRTL = i18n.language === 'ar';

  const switchLanguage = useCallback(async (lang: 'en' | 'ar') => {
    if (lang === i18n.language) return;

    await saveLanguage(lang);
    await i18n.changeLanguage(lang);

    const shouldBeRTL = lang === 'ar';
    if (I18nManager.isRTL !== shouldBeRTL) {
      I18nManager.allowRTL(true);
      I18nManager.forceRTL(shouldBeRTL);
      // App restart required for RTL to take effect
      try {
        const Updates = require('expo-updates');
        await Updates.reloadAsync();
      } catch {
        // In dev, Updates.reloadAsync may not work — user must restart manually
      }
    }
  }, [i18n]);

  return { language: i18n.language as 'en' | 'ar', isRTL, switchLanguage };
}
