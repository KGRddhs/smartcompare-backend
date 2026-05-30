/**
 * deriveTone — Bundle E S1 pre-stage utility.
 *
 * Maps a product brand-string to a tone-string (hex) for visual tile
 * backgrounds. Used by 4 surfaces composing mini VS pairs:
 *   - HomeScreen SmartPickCard (PickTile tone)
 *   - HistoryScreen HeroStats marquee + HistoryRowV2 (ProductBlock tone)
 *   - ProfileScreen RecentDecisions (MiniVsCard tone)
 *   - PaywallScreen HeroVisual mini-pairs
 *
 * Mapping derived from `docs/claude-design-handoff/ui_kits/mobile/*.jsx`
 * inline `tone` literals (HomeScreen.jsx:469-480, HistoryScreen.jsx:31-72,
 * ProfileScreen.jsx:124-129, LoadingScreen.jsx:210-211,
 * ShareBottomSheet.jsx:45-59). Cross-referenced 5 JSX consumers; tones
 * agree across surfaces (iPhone always #E8E9ED, Galaxy always #1B1C1F,
 * etc.).
 *
 * Fallback (per team-lead Bundle E ruling 2026-05-26): unknown brand →
 * `#F8F8FA` neutral secondary. Don't throw, don't hash-derive — visual
 * stability beats coverage.
 *
 * Matching: case-insensitive substring on the brand-string. iPhone-Pro
 * still resolves to the iPhone tone. The keys are ordered most-specific
 * to least-specific (so "Galaxy S24 Ultra" matches "galaxy" not "samsung"
 * if both were present); BRAND_TONES is iterated in order via
 * Object.entries.
 *
 * Test snapshot: __tests__/utils/deriveTone.test.ts pins the full table
 * + fallback contract.
 */

/**
 * Canonical brand → tone lookup table. Lower-case keys; matched via
 * `String.includes(key)` against a lower-cased input. Order matters —
 * the first match wins so multi-word brands (e.g. "la roche") are
 * placed before single-word brands they might collide with.
 */
export const BRAND_TONES: Record<string, string> = {
  // Apple ecosystem — cool silver-gray
  iphone: '#E8E9ED',
  ipad: '#E8E9ED',
  airpods: '#E8E9ED',
  apple: '#E8E9ED',

  // Samsung Galaxy — premium charcoal-black
  'galaxy s': '#1B1C1F',
  galaxy: '#1B1C1F',
  samsung: '#1B1C1F',

  // Pixel — same charcoal family (Android premium)
  pixel: '#1B1C1F',

  // MAC cosmetics — black (premium luxury cosmetic)
  'mac studio': '#1B1C1F',
  mac: '#1B1C1F',

  // Centrum / multivitamin — warm pink
  centrum: '#FBE6E6',

  // Maybelline — warm pink-coral
  maybelline: '#FCD9D2',

  // One A Day — warm tan / wheat
  'one a day': '#FFEAD4',

  // CeraVe — cool light-blue (skincare clinical)
  cerave: '#E6EEF9',

  // La Roche-Posay — cream
  'la roche': '#FFF1DA',
  'la roche-posay': '#FFF1DA',

  // Vitabiotics / HealthAid supplements — same warm tan family as One A Day
  vitabiotics: '#FFEAD4',
  healthaid: '#FFEAD4',
};

/**
 * Neutral fallback. Per Bundle E ruling 2026-05-26 — unknown brands get
 * this. Don't throw, don't hash-derive.
 */
export const FALLBACK_TONE = '#F8F8FA';

/**
 * Resolve a brand-string to a tone hex. Case-insensitive substring match
 * against the canonical lookup, fallback to neutral secondary.
 *
 * @param brand — the product display name (e.g. "iPhone 15 Pro", "Galaxy S24")
 * @returns hex color string (always 7-char #RRGGBB)
 */
export function deriveTone(brand: string | null | undefined): string {
  if (!brand || typeof brand !== 'string') return FALLBACK_TONE;
  const needle = brand.toLowerCase();
  for (const [key, tone] of Object.entries(BRAND_TONES)) {
    if (needle.includes(key)) return tone;
  }
  return FALLBACK_TONE;
}
