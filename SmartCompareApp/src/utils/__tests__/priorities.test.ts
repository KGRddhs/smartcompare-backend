import { toCanonicalPriorities, CANONICAL_PRIORITIES } from '../priorities';

describe('toCanonicalPriorities', () => {
  it('is identity for canonical keys', () => {
    expect(toCanonicalPriorities(['price', 'quality'])).toEqual(['price', 'quality']);
  });

  it('maps cohort-derived priorities to canonical display keys', () => {
    expect(
      toCanonicalPriorities(['best_price', 'quality_reliability', 'trusted_brand']),
    ).toEqual(['price', 'quality', 'brand_reputation']);
  });

  it('maps warranty_support + design_aesthetics to their nearest canonical', () => {
    expect(toCanonicalPriorities(['warranty_support', 'design_aesthetics'])).toEqual([
      'durability',
      'latest_features',
    ]);
  });

  it('de-duplicates collapsed mappings (best_price + value_for_money → price)', () => {
    expect(toCanonicalPriorities(['best_price', 'value_for_money'])).toEqual(['price']);
  });

  it('drops unknown keys', () => {
    expect(toCanonicalPriorities(['price', 'totally_unknown'])).toEqual(['price']);
  });

  it('caps at 3 by default, preserving order', () => {
    expect(
      toCanonicalPriorities(['price', 'quality', 'durability', 'eco_friendly']),
    ).toEqual(['price', 'quality', 'durability']);
  });

  it('returns [] for null / undefined / empty', () => {
    expect(toCanonicalPriorities(null)).toEqual([]);
    expect(toCanonicalPriorities(undefined)).toEqual([]);
    expect(toCanonicalPriorities([])).toEqual([]);
  });

  it('every canonical priority round-trips as identity', () => {
    for (const k of CANONICAL_PRIORITIES) {
      expect(toCanonicalPriorities([k])).toEqual([k]);
    }
  });
});
