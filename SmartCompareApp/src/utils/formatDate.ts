// Locale-aware date + relative-time formatting.
// Used by HistoryScreen and anywhere with user-visible timestamps.
//
// Arabic note: ASCII digits are kept inside interpolations (e.g. "منذ 2 يوم")
// to match the rest of the app's idiom (referrals.status, etc.).

export type AppLanguage = 'en' | 'ar';

export function formatDate(
  d: Date | string | number,
  language: AppLanguage,
): string {
  const date = d instanceof Date ? d : new Date(d);
  const locale = language === 'ar' ? 'ar-SA' : 'en-US';
  return date.toLocaleDateString(locale, { month: 'short', day: 'numeric' });
}

export function formatTimeAgo(
  d: Date | string | number,
  language: AppLanguage,
): string {
  const date = d instanceof Date ? d : new Date(d);
  const diffMs = Date.now() - date.getTime();
  const diffMin = Math.floor(diffMs / 60_000);
  const diffHr = Math.floor(diffMs / 3_600_000);
  const diffDay = Math.floor(diffMs / 86_400_000);

  if (language === 'ar') {
    if (diffMin < 1) return 'الآن';
    if (diffMin < 60) return `منذ ${diffMin} دقيقة`;
    if (diffHr < 24) return `منذ ${diffHr} ساعة`;
    if (diffDay < 7) return `منذ ${diffDay} يوم`;
    return formatDate(date, 'ar');
  }
  if (diffMin < 1) return 'just now';
  if (diffMin < 60) return `${diffMin}m ago`;
  if (diffHr < 24) return `${diffHr}h ago`;
  if (diffDay < 7) return `${diffDay}d ago`;
  return formatDate(date, 'en');
}
