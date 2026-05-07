/**
 * ResultsScreen redesign tests — Phase 3 Task 30.
 *
 * Verifies the targeted post-reveal copy + structural changes per
 * design § 4b + § 4g audit by inspecting the source file. Behavior
 * tests (SSE, share, feedback) stay in their existing suites; the full
 * on-device render is checked at the Phase 3 QA gate (#33).
 *
 * We assert against the source string because rendering ResultsScreen
 * end-to-end in unit-test land would require reproducing the full
 * Reanimated entering-animation surface (FadeInDown, FadeIn,
 * useSharedValue) plus all dependent hooks — out of scope for this
 * task's targeted copy/structure verification.
 */

import * as fs from 'fs';
import * as path from 'path';

const RESULTS_PATH = path.resolve(
  __dirname,
  '../src/screens/ResultsScreen.tsx'
);

const SOURCE = fs.readFileSync(RESULTS_PATH, 'utf8');

describe('ResultsScreen redesign — Phase 3 Task 30 (source assertions)', () => {
  it('uses results.whyWePicked for the verdict section title', () => {
    expect(SOURCE).toMatch(/t\(['"]results\.whyWePicked['"]\)/);
  });

  it('drops the legacy results.verdict section title', () => {
    expect(SOURCE).not.toMatch(/t\(['"]results\.verdict['"]\)/);
  });

  it('uses results.runnerUpWins for the differences section title', () => {
    expect(SOURCE).toMatch(/t\(['"]results\.runnerUpWins['"]\)/);
  });

  it('drops the legacy results.keyDifferences section title', () => {
    expect(SOURCE).not.toMatch(/t\(['"]results\.keyDifferences['"]\)/);
  });

  it('renders the "What\'s next?" footer CTA', () => {
    expect(SOURCE).toMatch(/t\(['"]results\.whatsNext['"]\)/);
  });

  it('starts the specs section collapsed by default', () => {
    // useState(false) for specsExpanded → section collapsed on mount.
    expect(SOURCE).toMatch(/specsExpanded.*useState[<>(\s\w]*\(\s*false\s*\)/s);
  });

  it('renders the cohort badge slot below the verdict block', () => {
    expect(SOURCE).toMatch(/results-cohort-badge-slot/);
    expect(SOURCE).toMatch(/CohortBadge/);
  });

  it('imports CohortBadge from the new component', () => {
    expect(SOURCE).toMatch(
      /import\s*\{\s*CohortBadge\s*\}\s*from\s*['"]\.\.\/components\/CohortBadge['"]/
    );
  });

  it('exposes accessibilityState.expanded on the specs toggle', () => {
    expect(SOURCE).toMatch(/results-specs-toggle/);
    // The toggle node carries `accessibilityState={{ expanded: ... }}`.
    expect(SOURCE).toMatch(
      /accessibilityState=\{\{[^}]*expanded:\s*specsExpanded/
    );
  });
});

describe('ResultsScreen redesign — i18n catalog', () => {
  const en = fs.readFileSync(
    path.resolve(__dirname, '../src/i18n/en.json'),
    'utf8'
  );
  const ar = fs.readFileSync(
    path.resolve(__dirname, '../src/i18n/ar.json'),
    'utf8'
  );

  it('adds whyWePicked / runnerUpWins / whatsNext keys EN + AR', () => {
    for (const key of ['results.whyWePicked', 'results.runnerUpWins', 'results.whatsNext']) {
      expect(en).toContain(`"${key}"`);
      expect(ar).toContain(`"${key}"`);
    }
  });

  it('uses confident copy "Why we picked this" / "Where the runner-up wins" / "What\'s next?"', () => {
    expect(en).toContain('"Why we picked this"');
    expect(en).toContain('"Where the runner-up wins"');
    // Apostrophe escaped in JSON
    expect(en).toMatch(/"What\\?'s next\?"/);
  });
});
