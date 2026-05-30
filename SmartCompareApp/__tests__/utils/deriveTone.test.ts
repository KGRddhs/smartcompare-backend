/**
 * deriveTone util — Q1 follow-up snapshot test (T-S1.4 / F-S1.0).
 *
 * Per Bundle E team-lead ruling 2026-05-26 (Q1 confirmation): snapshot
 * the BRAND_TONES lookup table + assert the canonical brand→tone mapping
 * from `docs/claude-design-handoff/ui_kits/mobile/*.jsx` inline `tone`
 * literals + the fallback contract for unknown brands.
 *
 * The util is consumed by 4 S1 surfaces (HomeScreen SmartPickCard,
 * HistoryScreen HistoryRowV2, ProfileScreen RecentDecisions,
 * PaywallScreen HeroVisual) — locking the lookup table here prevents
 * silent drift if a future commit reorders/renames keys.
 */
import { deriveTone, BRAND_TONES, FALLBACK_TONE } from '../../src/utils/deriveTone';

describe('deriveTone util', () => {
  describe('canonical brand → tone mapping (per JSX inline literals)', () => {
    // Locked from docs/claude-design-handoff/ui_kits/mobile/HistoryScreen.jsx:31-72
    // + HomeScreen.jsx:469-480 + ProfileScreen.jsx:124-129 + LoadingScreen.jsx:210-211.
    // Cross-referenced across 5 JSX files; tones agree across surfaces.
    const cases: Array<[string, string]> = [
      // Apple ecosystem — silver-gray
      ['iPhone 15', '#E8E9ED'],
      ['iPhone 15 Pro', '#E8E9ED'],
      ['Apple Watch', '#E8E9ED'],
      ['iPad', '#E8E9ED'],
      ['AirPods Pro', '#E8E9ED'],
      // Samsung Galaxy + Pixel + MAC cosmetics — charcoal-black
      ['Galaxy S24', '#1B1C1F'],
      ['Galaxy S24 Ultra', '#1B1C1F'],
      ['Samsung Galaxy', '#1B1C1F'],
      ['Pixel 8', '#1B1C1F'],
      ['MAC Studio Fix', '#1B1C1F'],
      ['MAC Lipstick', '#1B1C1F'],
      // Multivitamins / cosmetics — warm pink + tan
      ['Centrum Multi', '#FBE6E6'],
      ['Maybelline Fit Me', '#FCD9D2'],
      ['One A Day', '#FFEAD4'],
      // Skincare — cool light-blue + cream
      ['CeraVe Hydrating', '#E6EEF9'],
      ['La Roche Effaclar', '#FFF1DA'],
      ['La Roche-Posay Sun', '#FFF1DA'],
      // Supplements — same warm tan family
      ['Vitabiotics Wellman', '#FFEAD4'],
      ['HealthAid Multi', '#FFEAD4'],
    ];

    test.each(cases)('deriveTone("%s") returns "%s"', (brand, expected) => {
      expect(deriveTone(brand)).toBe(expected);
    });
  });

  describe('case-insensitive substring matching', () => {
    it('matches lower-case input against canonical lower-case keys', () => {
      expect(deriveTone('iphone 15')).toBe('#E8E9ED');
      expect(deriveTone('GALAXY S24')).toBe('#1B1C1F');
    });

    it('matches anywhere in the brand string (substring, not prefix-only)', () => {
      // "New iPhone 16 Pro" — "iphone" is in the middle of the lowercased
      // input, util should still find it.
      expect(deriveTone('New iPhone 16 Pro')).toBe('#E8E9ED');
    });
  });

  describe('fallback contract', () => {
    it('returns FALLBACK_TONE for unknown brand', () => {
      expect(deriveTone('Some Unknown Brand')).toBe(FALLBACK_TONE);
      expect(deriveTone('Asus ROG')).toBe(FALLBACK_TONE);
    });

    it('FALLBACK_TONE is the neutral secondary (#F8F8FA) per team-lead ruling', () => {
      // Locked from Bundle E 2026-05-26 Q1 ruling — don't throw, don't
      // hash-derive, visual stability beats coverage.
      expect(FALLBACK_TONE).toBe('#F8F8FA');
    });

    it('returns FALLBACK_TONE for empty string', () => {
      expect(deriveTone('')).toBe(FALLBACK_TONE);
    });

    it('returns FALLBACK_TONE for null without throwing', () => {
      expect(() => deriveTone(null)).not.toThrow();
      expect(deriveTone(null)).toBe(FALLBACK_TONE);
    });

    it('returns FALLBACK_TONE for undefined without throwing', () => {
      expect(() => deriveTone(undefined)).not.toThrow();
      expect(deriveTone(undefined)).toBe(FALLBACK_TONE);
    });

    it('returns FALLBACK_TONE for non-string input without throwing', () => {
      // Defensive — JS callers may pass numbers via dynamic untyped data.
      expect(() => deriveTone(123 as any)).not.toThrow();
      expect(deriveTone(123 as any)).toBe(FALLBACK_TONE);
    });
  });

  describe('BRAND_TONES table snapshot', () => {
    it('matches the locked snapshot — alarms on silent key drift', () => {
      // Sort keys for snapshot stability — Object.entries order should be
      // deterministic but explicit sort guards against engine differences.
      const sorted = Object.fromEntries(
        Object.entries(BRAND_TONES).sort(([a], [b]) => a.localeCompare(b)),
      );
      expect(sorted).toMatchSnapshot();
    });

    it('every value is a 7-char #RRGGBB hex', () => {
      for (const [key, value] of Object.entries(BRAND_TONES)) {
        expect(value).toMatch(/^#[0-9A-Fa-f]{6}$/);
        expect(key.toLowerCase()).toBe(key); // keys lower-case for matching
      }
    });
  });
});
