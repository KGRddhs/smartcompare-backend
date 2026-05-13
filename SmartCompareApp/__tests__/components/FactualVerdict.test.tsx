/**
 * FactualVerdict — Bundle E Phase 3 Task 3.5 RED scaffold.
 *
 * Plan: docs/plans/2026-05-13-results-quality-overhaul.md
 * Design: docs/plans/2026-05-13-results-quality-overhaul-design.md § Decision 5
 * (legal-safe copy framing + `build_factual_verdict`).
 *
 * Replaces the old GPT-invented `overview.winner.reason` with a
 * deterministic factual line composed from the top 3 core dimensions
 * the top-match wins on (`delta_text` from each). Followed by a
 * conditional alternative line for the runner-up.
 *
 * The component is a passive render of backend-supplied text. It must
 * NEVER overlay its own evaluative copy and must REJECT any text that
 * contains banned vocabulary — that's a defense-in-depth check against
 * a bug in the backend builder.
 *
 * Banned word set is anchored on § Decision 5's table:
 *   `best`, `pick`, `excellent`, `great`, `recommend`, `winner`, `worst`,
 *   `better`, `worse`, `beats`, `smart`, `good`, `choose`
 *
 * BLOCKED ON: backend Task 1.5 (`build_factual_verdict` in
 * `response_builder.py`) + frontend Task 3.5 component. Component path:
 * `src/components/results/FactualVerdict.tsx` (to be created).
 */

import React from 'react';
import { render } from '@testing-library/react-native';

import { FactualVerdict } from '../../src/components/results/FactualVerdict';

describe('FactualVerdict — Bundle E Phase 3 § Decision 5', () => {
  it('renders the backend-supplied delta_text + conditional line verbatim', () => {
    const line1 = 'BHD 30 less, 0.2★ higher, 12g lighter';
    const line2 = 'If you want PBT keycaps, the Ducky fits.';
    const { getByText } = render(
      <FactualVerdict line1={line1} line2={line2} testID="verdict" />,
    );
    // Both lines render exactly as supplied — no client-side rewriting,
    // no decorative adjectives, no truncation.
    expect(getByText(line1)).toBeTruthy();
    expect(getByText(line2)).toBeTruthy();
  });

  it('throws (or renders a contract-violation node) if backend sends a banned word', () => {
    // Defense-in-depth: even though `build_factual_verdict` should never
    // emit evaluative copy, the frontend must fail loud if it does. This
    // catches a regression in the backend builder before it ships an
    // evaluative claim to users (legal exposure per § Decision 5).
    const bannedLines = [
      'This is the best pick overall.',
      'We recommend the Glorious.',
      'Excellent build quality on the winner.',
      'Choose this if you want value.',
      'Beats the runner-up on price.',
    ];
    for (const banned of bannedLines) {
      let threw = false;
      let violationNode: any = null;
      try {
        const { queryByTestId } = render(
          <FactualVerdict line1={banned} line2="" testID="verdict" />,
        );
        violationNode = queryByTestId('verdict-contract-violation');
      } catch {
        threw = true;
      }
      expect(threw || violationNode !== null).toBe(true);
    }
  });
});

/**
 * RED→GREEN trajectory:
 *
 *  1. Pre-Phase-3: component module does not exist. Both tests fail at
 *     import.
 *  2. Phase 3 Task 3.5 lands the component. Assertion (1) passes
 *     trivially (verbatim render). Assertion (2) passes once the
 *     banned-word guard is added to the component.
 *  3. The guard ALSO doubles as a contract-test fence between FE and BE:
 *     if backend Task 1.4 (`build_factual_verdict`) ever regresses and
 *     emits an evaluative claim, the FE test catches it before users see
 *     it — even if the backend pytest copy-policy test passes.
 */
