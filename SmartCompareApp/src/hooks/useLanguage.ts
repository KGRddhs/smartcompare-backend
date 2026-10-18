import { useCallback } from 'react';
import { I18nManager } from 'react-native';
import { useTranslation } from 'react-i18next';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { saveLanguage } from '../i18n';
import { RTL_BOOTSTRAPPED_KEY } from '../i18n/rtlBootstrap';

/** S79 B3-A C3: how long the pre-reload writes may hold the reload. */
const BEFORE_RELOAD_BOUND_MS = 1500;

export interface SwitchLanguageOptions {
  /**
   * Runs only on the reload path (the layout direction changes), after
   * forceRTL and before Updates.reloadAsync(). Bounded and fail-soft: a
   * rejecting or hung hook never prevents the reload.
   */
  beforeReload?: () => Promise<void> | void;
}

/** Resolve when `run` settles; never reject, never throw synchronously. */
function settleQuietly(run: () => Promise<unknown> | unknown): Promise<void> {
  try {
    return Promise.resolve(run()).then(
      () => undefined,
      () => undefined,
    );
  } catch {
    return Promise.resolve();
  }
}

export function useLanguage() {
  const { i18n } = useTranslation();
  const isRTL = i18n.language === 'ar';

  const switchLanguage = useCallback(async (lang: 'en' | 'ar', opts?: SwitchLanguageOptions) => {
    if (lang === i18n.language) return;

    await saveLanguage(lang);
    await i18n.changeLanguage(lang);

    const shouldBeRTL = lang === 'ar';
    if (I18nManager.isRTL !== shouldBeRTL) {
      I18nManager.allowRTL(true);
      I18nManager.forceRTL(shouldBeRTL);
      // S79 B3-A C3 + ruling A5: before the reload, (1) let the caller
      // persist what must survive it (onboarding writes its resume record)
      // and (2) record the direction we are reloading into, so the boot-time
      // bootstrapRtl never reloads a second time after the resume record was
      // consumed. Both run at once inside ONE 1500 ms bound; each is
      // swallowed on failure, so neither can hold or block the reload.
      let timer: ReturnType<typeof setTimeout> | undefined;
      const beforeReload = opts?.beforeReload;
      await Promise.race([
        Promise.all([
          beforeReload ? settleQuietly(beforeReload) : Promise.resolve(),
          settleQuietly(() => AsyncStorage.setItem(RTL_BOOTSTRAPPED_KEY, shouldBeRTL ? 'rtl' : 'ltr')),
        ]),
        new Promise<void>((resolve) => {
          timer = setTimeout(resolve, BEFORE_RELOAD_BOUND_MS);
        }),
      ]);
      if (timer !== undefined) clearTimeout(timer);
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
