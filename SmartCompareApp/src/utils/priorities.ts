// Priority-key normalization (device bug fix 2026-07-04).
//
// The FE PrioritiesPicker / Step08Priorities render + toggle only the 8
// CANONICAL priority keys. The backend, however, also accepts 6
// cohort-derived priority enums (see auth_routes VALID_PRIORITIES) which
// `cohort_service.seed_preferences` writes into `users.preferences.priorities`
// for users who completed the demographics modal.
//
// Left unmapped, a cohort-seeded priority sits INVISIBLE in the picker (no
// row matches it) yet still consumes the MAX_SELECTIONS=3 cap — so the user
// cannot select or change their priorities ("priorities can't be chosen").
// `toCanonicalPriorities` maps each cohort-derived value to its closest
// canonical display key so seeded priorities render as selected, editable
// rows.

export const CANONICAL_PRIORITIES = [
  'price',
  'quality',
  'brand_reputation',
  'durability',
  'latest_features',
  'ease_of_use',
  'eco_friendly',
  'health_safety',
] as const;

const CANONICAL_SET = new Set<string>(CANONICAL_PRIORITIES);

// Best-effort cohort-derived → canonical mapping. Four are exact in spirit
// (best_price→price, quality_reliability→quality, trusted_brand→
// brand_reputation, warranty_support→durability); value_for_money and
// design_aesthetics have no exact canonical, so map to the nearest
// (price / latest_features). The mapping only provides a sensible starting
// selection — the user can freely re-pick once the rows are visible.
const COHORT_TO_CANONICAL: Record<string, string> = {
  best_price: 'price',
  value_for_money: 'price',
  quality_reliability: 'quality',
  trusted_brand: 'brand_reputation',
  warranty_support: 'durability',
  design_aesthetics: 'latest_features',
};

/**
 * Normalize a stored priorities array to canonical display keys: map any
 * cohort-derived value to its canonical equivalent, drop unknown keys,
 * de-duplicate, and cap at `max` (default 3 — matches the backend
 * max_length and the picker MAX_SELECTIONS).
 *
 * Identity for an all-canonical input, so onboarding (which starts empty)
 * and any already-canonical selection are unaffected.
 */
export function toCanonicalPriorities(
  value: string[] | null | undefined,
  max = 3,
): string[] {
  if (!value) return [];
  const out: string[] = [];
  for (const raw of value) {
    const canon = CANONICAL_SET.has(raw) ? raw : COHORT_TO_CANONICAL[raw];
    if (canon && !out.includes(canon)) out.push(canon);
    if (out.length >= max) break;
  }
  return out;
}
