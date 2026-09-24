// Locale-aware date + relative-time formatting.
// Used by HistoryScreen, ProfileEditorialSections and anywhere with
// user-visible timestamps.
//
// W3-11 RTL-06/RTL-08: relative-time copy lives in the catalog
// (`time.justNow` + the `time.{minutes,hours,days}Ago` plural families, six
// Arabic forms each) — this file holds no user-visible copy. Digits follow
// the app digit policy (formatNumber.ts): whatever the engine's
// `toLocaleDateString('ar-SA')` emits, the digits are mapped to the policy.

import { applyDigitSystem, toAsciiDigits } from './formatNumber';

export type AppLanguage = 'en' | 'ar';

type TranslateFn = (key: string, options?: Record<string, unknown>) => string;

export function formatDate(
  d: Date | string | number,
  language: AppLanguage,
): string {
  const date = d instanceof Date ? d : new Date(d);
  const locale = language === 'ar' ? 'ar-SA' : 'en-US';
  return applyDigitSystem(
    toAsciiDigits(date.toLocaleDateString(locale, { month: 'short', day: 'numeric' })),
  );
}

export function formatTimeAgo(
  d: Date | string | number,
  language: AppLanguage,
  t: TranslateFn,
): string {
  const date = d instanceof Date ? d : new Date(d);
  const diffMs = Date.now() - date.getTime();
  const diffMin = Math.floor(diffMs / 60_000);
  const diffHr = Math.floor(diffMs / 3_600_000);
  const diffDay = Math.floor(diffMs / 86_400_000);

  if (diffMin < 1) return t('time.justNow');
  if (diffMin < 60) return t('time.minutesAgo', { count: diffMin });
  if (diffHr < 24) return t('time.hoursAgo', { count: diffHr });
  if (diffDay < 7) return t('time.daysAgo', { count: diffDay });
  return formatDate(date, language);
}
