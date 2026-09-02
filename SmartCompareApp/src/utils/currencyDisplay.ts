/**
 * Localized currency display — M21 W4 rtl-i18n (MB-i18n-rtl-02).
 *
 * The design language localizes currency: Home/History hero copy ships
 * "د.ب" in Arabic, but the Results price lines interpolated the raw
 * Latin ISO code ("BHD 12.500") into Arabic copy — two languages in one
 * app. This helper resolves an ISO code through the `currency.*` catalog
 * family: EN keys map to the ISO code itself (EN rendering unchanged),
 * AR keys carry the Arabic glyphs the hero copy already uses.
 *
 * Uncatalogued codes fall back to the raw input — a foreign currency the
 * backend labels (EUR, TRY, ...) still renders honestly as its ISO code.
 */

type TranslateFn = (key: string, options?: Record<string, unknown>) => string;

export function localizedCurrency(code: string, t: TranslateFn): string {
  if (!code) return code;
  const key = `currency.${code}`;
  const out = t(key, { defaultValue: code });
  // A t() that echoes unknown keys (e.g. the jest mock, or an i18next
  // configured without defaultValue support) returns the key itself —
  // treat that as "not catalogued" and fall back to the raw code.
  return out === key ? code : out;
}

export default localizedCurrency;
