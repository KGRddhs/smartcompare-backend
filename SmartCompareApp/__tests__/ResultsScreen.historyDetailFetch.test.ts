/**
 * Bundle D Task 1.F.5 — History detail fetch contract.
 *
 * Backend R3 RCA (Migration 026, commit 52e7f01) backfilled 7 renderable
 * v1 comparisons to schema_version=2 — they now pass the history detail
 * gate. The remaining work on the frontend is to confirm the 404 path
 * is wired with an i18n-resolved, copy-policy-clean message for any row
 * that remains unrenderable.
 *
 * No new screen code is required — the existing `loadError === 'not_found'`
 * branch at ResultsScreen.tsx:529 already renders `t('results.emptyState.notFound')`.
 * This test pins the contract so any future regression (handler removed
 * or key renamed) lights up here.
 */

import * as fs from 'fs';
import * as path from 'path';

const RESULTS_PATH = path.resolve(__dirname, '../src/screens/ResultsScreen.tsx');
const SOURCE = fs.readFileSync(RESULTS_PATH, 'utf8');
// eslint-disable-next-line @typescript-eslint/no-var-requires
const EN = require('../src/i18n/en.json') as Record<string, string>;
// eslint-disable-next-line @typescript-eslint/no-var-requires
const AR = require('../src/i18n/ar.json') as Record<string, string>;

describe('ResultsScreen — history detail fetch + 404 copy (Bundle D 1.F.5)', () => {
  it('catches 404 from getComparison() and sets loadError to "not_found"', () => {
    expect(SOURCE).toMatch(/status\s*===\s*404[\s\S]{0,80}setLoadError\(\s*['"]not_found['"]/);
  });

  it('renders the not_found copy via t("results.emptyState.notFound")', () => {
    expect(SOURCE).toMatch(/loadError\s*===\s*['"]not_found['"][\s\S]{0,120}results\.emptyState\.notFound/);
  });

  it('not_found copy exists in EN and AR with no forbidden vocab', () => {
    expect(EN['results.emptyState.notFound']).toBeTruthy();
    expect(AR['results.emptyState.notFound']).toBeTruthy();
    // Forbidden EN vocab per Bundle D anchor.
    const forbiddenEn = /couldn['']t|try again|failed to/i;
    expect(EN['results.emptyState.notFound']).not.toMatch(forbiddenEn);
    // Forbidden AR vocab per Bundle D anchor.
    const forbiddenAr = /تعذر|فشل/;
    expect(AR['results.emptyState.notFound']).not.toMatch(forbiddenAr);
  });

  it('preserves the 1.2s min-display floor for the history → results path', () => {
    // Design § 3: cached responses still show LoadingRings for 1.2s.
    expect(SOURCE).toMatch(/minDisplayUntilRef/);
    expect(SOURCE).toMatch(/await\s+new\s+Promise\(\s*\(resolve\)\s*=>\s*setTimeout/);
  });
});
