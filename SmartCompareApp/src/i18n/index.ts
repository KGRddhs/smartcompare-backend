import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import * as Localization from 'expo-localization';
import AsyncStorage from '@react-native-async-storage/async-storage';
import en from './en.json';
import ar from './ar.json';

const LANGUAGE_KEY = '@qaren_language';

export async function getSavedLanguage(): Promise<string> {
  try {
    const saved = await AsyncStorage.getItem(LANGUAGE_KEY);
    if (saved) return saved;
  } catch {}
  // Default: detect from device, fallback to English
  const deviceLocale = Localization.getLocales()[0]?.languageCode ?? 'en';
  return deviceLocale === 'ar' ? 'ar' : 'en';
}

export async function saveLanguage(lang: string): Promise<void> {
  await AsyncStorage.setItem(LANGUAGE_KEY, lang);
}

i18n.use(initReactI18next).init({
  resources: {
    en: { translation: en },
    ar: { translation: ar },
  },
  lng: 'en', // overridden at app start by getSavedLanguage()
  fallbackLng: 'en',
  interpolation: {
    escapeValue: false,
  },
});

export default i18n;
