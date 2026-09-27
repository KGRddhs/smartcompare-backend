/**
 * W4-14 — a dimension label through the `results.dimension.*` catalog, with the
 * `localizedCurrency` echo guard: an uncatalogued key, or a t() that echoes the key
 * (the jest global mock), falls back to the backend label.
 */
type TranslateFn = (key: string, options?: Record<string, unknown>) => string;

export function localizedDimensionLabel(
  key: string | null | undefined,
  label: string,
  t: TranslateFn,
): string {
  if (!key) return label;
  const k = `results.dimension.${key}`;
  const out = t(k, { defaultValue: label });
  return out === k || typeof out !== 'string' || out.length === 0 ? label : out;
}
