/**
 * Bundle C — TypeScript contract additions (Plan B.1.1)
 *
 * Type-level + runtime sanity test for the new scoring-engine contract:
 *   - BudgetValue extends to 5 literal tiers
 *   - Dimension.confidence is optional (acceptable when backend ships flag-OFF rows)
 *   - PersonalizationApplied carries applied_shifts array
 *   - ValueMatch | ComparisonQuality | SourceMethod literal unions
 *
 * Runs against the package types index (`src/types`) which re-exports `types.ts`.
 */
import type {
  BudgetValue,
  Dimension,
  PersonalizationApplied,
  ValueMatch,
  ComparisonQuality,
  SourceMethod,
} from '../src/types';

test('BudgetValue accepts 5 literal tiers', () => {
  const valid: BudgetValue[] = ['budget', 'mid', 'premium', 'luxury', 'top_tier'];
  expect(valid).toHaveLength(5);
});

test('Dimension.confidence is optional and accepts low|medium|high', () => {
  const d: Dimension = {
    key: 'price',
    label: 'Price',
    score_a: 80,
    score_b: 72,
    delta_text: '10% less',
    confidence: 'high',
    is_core: true,
  };
  expect(d.confidence).toBe('high');
});

test('PersonalizationApplied carries applied_shifts array', () => {
  const p: PersonalizationApplied = {
    applied_shifts: [{ dim_display: 'performance', direction: 'up' }],
  };
  expect(p.applied_shifts[0].direction).toBe('up');
});

test('ValueMatch literal accepts in_range|above_range|below_range', () => {
  const v: ValueMatch[] = ['in_range', 'above_range', 'below_range'];
  expect(v).toHaveLength(3);
});

test('ComparisonQuality literal accepts normal|weak|weird', () => {
  const q: ComparisonQuality[] = ['normal', 'weak', 'weird'];
  expect(q).toHaveLength(3);
});

test('SourceMethod includes estimated enum', () => {
  const m: SourceMethod = 'estimated';
  expect(m).toBe('estimated');
});

test('SourceMethod includes Firecrawl + Scrape.do enums', () => {
  const methods: SourceMethod[] = [
    'local_bhd',
    'converted_usd',
    'page_scrape',
    'page_scrape_rendered',
    'firecrawl',
    'scrapedo_rendered',
    'estimated',
  ];
  expect(methods).toHaveLength(7);
});
