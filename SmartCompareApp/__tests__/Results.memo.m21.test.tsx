/**
 * M21 mobile-jank — MB-perf-06: the ~1,650-line results tree re-renders on
 * every orchestrator state transition (usageStatus fetch, demographics
 * timer, share-sheet/toast state) because ResultsContent/ResultsAccordion
 * are plain function components fed freshly-created closures each render.
 *
 * Contract:
 *  1. ResultsContent and ResultsAccordion are React.memo components.
 *  2. ResultsScreen passes stable (useCallback) handlers — not inline
 *     arrows — for the five callback props, so the memo can actually hold.
 *
 * (2) is a source-grep pin, per the repo convention for screen-shaped
 * assertions (see HistoryScreen.imageUrl.test.tsx header).
 */

import * as fs from 'fs';
import * as path from 'path';

import { ResultsContent } from '../src/components/results/ResultsContent';
import { ResultsAccordion } from '../src/components/results/ResultsAccordion';

const REACT_MEMO_TYPE = Symbol.for('react.memo');

describe('MB-perf-06 — results tree memoization', () => {
  it('ResultsContent is wrapped in React.memo', () => {
    expect((ResultsContent as any).$$typeof).toBe(REACT_MEMO_TYPE);
  });

  it('ResultsAccordion is wrapped in React.memo', () => {
    expect((ResultsAccordion as any).$$typeof).toBe(REACT_MEMO_TYPE);
  });
});

describe('MB-perf-06 — ResultsScreen passes stable callbacks to ResultsContent', () => {
  const src = fs.readFileSync(
    path.resolve(__dirname, '../src/screens/ResultsScreen.tsx'),
    'utf8'
  );

  it.each([
    'onFeedbackSubmitted',
    'onPillPress',
    'onCloseSheet',
    'onBack',
    'onShare',
  ])('%s is passed as an identifier, not an inline arrow', (prop) => {
    // `onX={someIdentifier}` — an inline `onX={() => ...}` or
    // `onX={(leg) => ...}` recreates the closure every render and defeats
    // React.memo on the 1,650-line subtree.
    const inline = new RegExp(`${prop}=\\{\\s*\\(`);
    expect(src).not.toMatch(inline);
    const identifier = new RegExp(`${prop}=\\{[A-Za-z_$][\\w$]*\\}`);
    expect(src).toMatch(identifier);
  });

  it('ResultsScreen uses useCallback for the stable handlers', () => {
    expect(src).toMatch(/useCallback\(/);
  });
});
