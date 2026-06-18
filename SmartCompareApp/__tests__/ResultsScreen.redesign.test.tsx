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

// Bundle E S3 — Lane A2: presentation extracted to ResultsContent.tsx +
// ResultsAccordion.tsx. Task #24 2026-06-18: the runner-up surface moved into
// RunnerUpWinsCard.tsx. The redesign assertions read all four files.
const RESULTS_CONTENT_PATH = path.resolve(
  __dirname,
  '../src/components/results/ResultsContent.tsx'
);
const RESULTS_ACCORDION_PATH = path.resolve(
  __dirname,
  '../src/components/results/ResultsAccordion.tsx'
);
const RUNNER_UP_CARD_PATH = path.resolve(
  __dirname,
  '../src/components/results/RunnerUpWinsCard.tsx'
);
const SOURCE = [
  fs.readFileSync(RESULTS_PATH, 'utf8'),
  fs.existsSync(RESULTS_CONTENT_PATH)
    ? fs.readFileSync(RESULTS_CONTENT_PATH, 'utf8')
    : '',
  fs.existsSync(RESULTS_ACCORDION_PATH)
    ? fs.readFileSync(RESULTS_ACCORDION_PATH, 'utf8')
    : '',
  fs.existsSync(RUNNER_UP_CARD_PATH)
    ? fs.readFileSync(RUNNER_UP_CARD_PATH, 'utf8')
    : '',
].join('\n');

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

  // Phase 3 originally shipped a "What's next?" footer CTA — pruned in
  // Bundle E § Decision 6 because the NAVIGATE target was never wired
  // and the button threw in production. The Bundle E `no-deleted-keys`
  // test + `ResultsScreen.test.tsx` Task 0.2 block now own the
  // negative-assertion contract for this key.

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

  it('adds whyWePicked / runnerUpWins keys EN + AR', () => {
    // Bundle E § Decision 6 pruned results.whatsNext — see
    // __tests__/i18n/no-deleted-keys.test.ts for the negative-assertion
    // contract. The remaining Phase 3 keys must still be present.
    for (const key of ['results.whyWePicked', 'results.runnerUpWins']) {
      expect(en).toContain(`"${key}"`);
      expect(ar).toContain(`"${key}"`);
    }
  });

  it('uses factual copy per Bundle E § Decision 5 (replaced Phase 3 evaluative phrasing)', () => {
    // Bundle E Task 3.7 replaced "Why we picked this" → "Why this fits you"
    // because § Decision 5 banned "picked" as evaluative first-person endorsement.
    // The Phase 3 contract intent (a labeled section explaining the choice) is
    // preserved; only the user-visible string changed. See copy-policy.test.ts.
    expect(en).toContain('"Why this fits you"');
    expect(en).toContain('"Where the runner-up wins"');
  });
});
