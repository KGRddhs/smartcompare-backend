/**
 * Tests for `parseComparisonShape` — extracted as a standalone util as part
 * of Bundle B. Spec ref: docs/superpowers/specs/2026-05-17-bundle-b-two-input-ux-design.md § 4.1.1.
 * Plan ref: docs/superpowers/plans/2026-05-17-bundle-b-two-input-ux.md § 3.6a.
 *
 * Coverage target: 100% (tiny pure functions).
 */

import {
  COMPARISON_PATTERN,
  looksLikeTwoProducts,
  splitComparisonShape,
} from '../parseComparisonShape';

describe('parseComparisonShape', () => {
  describe('looksLikeTwoProducts(s)', () => {
    it('detects EN " vs " separator', () => {
      expect(looksLikeTwoProducts('iPhone 15 vs Galaxy S24')).toBe(true);
    });

    it('detects EN " and " separator', () => {
      expect(looksLikeTwoProducts('iPhone 15 and Galaxy S24')).toBe(true);
    });

    it('detects EN " or " separator', () => {
      expect(looksLikeTwoProducts('iPhone 15 or Galaxy S24')).toBe(true);
    });

    it('detects EN " & " separator', () => {
      expect(looksLikeTwoProducts('iPhone 15 & Galaxy S24')).toBe(true);
    });

    it('detects EN "," separator', () => {
      expect(looksLikeTwoProducts('iPhone 15, Galaxy S24')).toBe(true);
    });

    it('detects AR " أو " separator', () => {
      expect(looksLikeTwoProducts('iPhone 15 أو Galaxy S24')).toBe(true);
    });

    it('detects AR " مقابل " separator', () => {
      expect(looksLikeTwoProducts('iPhone 15 مقابل Galaxy S24')).toBe(true);
    });

    it('returns false for a single product', () => {
      expect(looksLikeTwoProducts('iPhone 15')).toBe(false);
    });

    it('returns false when there is no separator at all', () => {
      expect(looksLikeTwoProducts('buy iPhone 15')).toBe(false);
    });

    it('returns false when " vs " is a substring inside another word (versus)', () => {
      // Plan § 3.6a — regex anchors on \s on BOTH sides of "vs", so
      // "versus" (letters on both sides) must NOT trigger split.
      expect(looksLikeTwoProducts('investments versus other')).toBe(false);
    });

    it('treats "vs" at the START with no left half as still matching the regex (split returns null later)', () => {
      // Spec pins the predicate (the regex matches " vs " surrounded by
      // whitespace), then `splitComparisonShape` rejects short halves.
      // The detector says yes; the splitter handles the length floor.
      expect(looksLikeTwoProducts('a vs Galaxy S24')).toBe(true);
    });

    it('treats "vs" at the END the same way (split rejects short right half)', () => {
      expect(looksLikeTwoProducts('iPhone 15 vs a')).toBe(true);
    });

    it('detects EN " VS " (uppercase) — case-insensitive', () => {
      expect(looksLikeTwoProducts('iPhone 15 VS Galaxy S24')).toBe(true);
    });

    it('detects EN " Vs " (mixed case) — case-insensitive', () => {
      expect(looksLikeTwoProducts('iPhone 15 Vs Galaxy S24')).toBe(true);
    });

    it('detects EN " AND " (uppercase)', () => {
      expect(looksLikeTwoProducts('iPhone 15 AND Galaxy S24')).toBe(true);
    });

    it('returns false on an empty string', () => {
      expect(looksLikeTwoProducts('')).toBe(false);
    });
  });

  describe('splitComparisonShape(s)', () => {
    it('splits on " vs " into trimmed halves', () => {
      expect(splitComparisonShape('iPhone 15 vs Galaxy S24')).toEqual([
        'iPhone 15',
        'Galaxy S24',
      ]);
    });

    it('trims surrounding whitespace from both halves', () => {
      expect(splitComparisonShape('  iPhone 15  vs  Galaxy S24  ')).toEqual([
        'iPhone 15',
        'Galaxy S24',
      ]);
    });

    it('returns null when the left half is shorter than 2 chars after trim', () => {
      expect(splitComparisonShape('a vs Galaxy S24')).toBeNull();
    });

    it('returns null when the right half is shorter than 2 chars after trim', () => {
      expect(splitComparisonShape('iPhone 15 vs a')).toBeNull();
    });

    it('returns null when there is no separator at all', () => {
      expect(splitComparisonShape('iPhone 15')).toBeNull();
    });

    it('splits at the FIRST separator occurrence — subsequent separators stay inside the right half', () => {
      // Pin from plan § 3.6a: "A vs B vs C" → ["A", "B vs C"]. If Frontend
      // changes this, the test fails and we revisit during cross-QA.
      expect(splitComparisonShape('Apple vs Banana vs Cherry')).toEqual([
        'Apple',
        'Banana vs Cherry',
      ]);
    });

    it('splits on AR " أو " separator', () => {
      expect(splitComparisonShape('iPhone 15 أو Galaxy S24')).toEqual([
        'iPhone 15',
        'Galaxy S24',
      ]);
    });

    it('splits on AR " مقابل " separator', () => {
      expect(splitComparisonShape('iPhone 15 مقابل Galaxy S24')).toEqual([
        'iPhone 15',
        'Galaxy S24',
      ]);
    });

    it('splits on "," separator', () => {
      expect(splitComparisonShape('iPhone 15, Galaxy S24')).toEqual([
        'iPhone 15',
        'Galaxy S24',
      ]);
    });

    it('splits on " & " separator', () => {
      expect(splitComparisonShape('iPhone 15 & Galaxy S24')).toEqual([
        'iPhone 15',
        'Galaxy S24',
      ]);
    });

    it('splits on " and " separator', () => {
      expect(splitComparisonShape('iPhone 15 and Galaxy S24')).toEqual([
        'iPhone 15',
        'Galaxy S24',
      ]);
    });

    it('splits on " or " separator', () => {
      expect(splitComparisonShape('iPhone 15 or Galaxy S24')).toEqual([
        'iPhone 15',
        'Galaxy S24',
      ]);
    });

    it('returns null on an empty string', () => {
      expect(splitComparisonShape('')).toBeNull();
    });
  });

  describe('COMPARISON_PATTERN exposed constant', () => {
    it('is a regex (consumers may compose it)', () => {
      expect(COMPARISON_PATTERN).toBeInstanceOf(RegExp);
    });
  });
});
