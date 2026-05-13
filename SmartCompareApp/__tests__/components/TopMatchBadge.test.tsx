/**
 * TopMatchBadge — Bundle E Phase 3 Task 3.3 RED scaffold.
 *
 * Plan: docs/plans/2026-05-13-results-quality-overhaul.md
 * Design: docs/plans/2026-05-13-results-quality-overhaul-design.md § Decision 3
 * + § Decision 5 (legal-safe copy).
 *
 * One-word pill that sits above the higher-scoring hero ring:
 *   - EN: "Top match"      key: `results.topMatch`
 *   - AR: "الأنسب لك"      same key, translated
 *
 * Emerald background, white text. **No trophy icon**, **no "Best Pick"**,
 * **no "Winner"** — those are all banned per § Decision 5. Component
 * must read copy from i18n; hardcoded English would break Arabic + RTL
 * and would also evade the copy-policy lint rule.
 *
 * BLOCKED ON: Phase 3 implementation. Component path:
 * `src/components/results/TopMatchBadge.tsx` (to be created).
 */

import React from 'react';
import { render } from '@testing-library/react-native';

// Local mock keeps the test independent of the i18n catalog state.
jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, opts?: Record<string, unknown>) => {
      const defaults: Record<string, string> = {
        'results.topMatch': 'Top match',
      };
      return defaults[key] ?? (opts?.defaultValue as string) ?? key;
    },
  }),
}));

/* eslint-disable import/no-unresolved -- RED scaffold: Phase 3 Task 3.3 creates src/components/results/TopMatchBadge.tsx; remove this directive when the module lands. */
// @ts-expect-error Phase 3 Task 3.3 will create src/components/results/TopMatchBadge.tsx
import { TopMatchBadge } from '../../src/components/results/TopMatchBadge';
/* eslint-enable import/no-unresolved */

describe('TopMatchBadge — Bundle E Phase 3 § Decision 3 + 5', () => {
  it('renders the results.topMatch i18n key with no banned evaluative copy', () => {
    const { getByText, queryByText } = render(<TopMatchBadge testID="top-match" />);
    // The component must use the i18n key — our mock returns "Top match".
    expect(getByText('Top match')).toBeTruthy();
    // Banned vocabulary from § Decision 5. None of these may appear in
    // the rendered badge — not as the label, not as a hidden sibling.
    const banned = [
      'Best Pick',
      'Smart Pick',
      'Winner',
      'Best Choice',
      'Excellent',
      'Great',
      'We recommend',
      'Choose this',
    ];
    for (const word of banned) {
      expect(queryByText(new RegExp(word, 'i'))).toBeNull();
    }
  });
});

/**
 * RED→GREEN trajectory:
 *
 *  1. Pre-Phase-3: `src/components/results/TopMatchBadge.tsx` does not
 *     exist. Test fails at import.
 *  2. Phase 3 Task 3.3 lands the component reading `t('results.topMatch')`
 *     with a `defaultValue: 'Top match'` fallback. Assertion passes.
 *  3. The negative-assertion sweep enforces design § Decision 5 — any
 *     future regression that swaps the key copy for "Best Pick" or
 *     "Winner" trips the second branch.
 *
 * Companion: `__tests__/copy-policy.test.ts` owns the catalog-level
 * banned-word audit. This file owns the rendered-output guard so a
 * keyed-but-unused phrase in en.json can't slip into the UI.
 */
