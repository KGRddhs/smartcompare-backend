/**
 * Hero SVG snapshot — RevealBurst.
 *
 * Scope (per QA § 6 audit patch 7676875, 2026-05-26):
 *   ResultsScreen winner-card first appearance ONLY. NOT used by Step15Reveal
 *   anymore — Step15 uses the MatchBadge primitive (92% emerald circle).
 *
 * Contract (design doc § 3.2):
 *   - 6–8 emerald particles emit from center on parabolic fall
 *   - Center holds scale-bounce badge (0→1.1→1.0 with withSpring damping 8 stiffness 100)
 *   - `fireOnce` prop ensures it only animates on first mount per React `key`
 *   - Re-rendering with the SAME key → particles do NOT re-emit (load-bearing
 *     because ResultsScreen re-renders frequently as personalization /
 *     analytics fetches resolve; the celebration must not retrigger)
 */
import React from 'react';
import { render } from '@testing-library/react-native';
import { RevealBurst } from '../../src/components/hero/RevealBurst';

describe('RevealBurst hero', () => {
  it('renders default snapshot', () => {
    const tree = render(<RevealBurst />).toJSON();
    expect(tree).toMatchSnapshot();
  });

  it('renders with custom particle count', () => {
    const tree = render(<RevealBurst particleCount={8} />).toJSON();
    expect(tree).toMatchSnapshot();
  });

  /**
   * fireOnce invariant — the burst is the "winner reveal" moment. If
   * ResultsScreen re-renders for any other reason (analytics fetch
   * completing, paywall mounting), the burst MUST NOT re-fire. The
   * mechanism is a useRef gate keyed on the React `key` prop.
   *
   * Test strategy: count emitted particle nodes after first render, then
   * trigger a re-render via parent prop change WITHOUT changing the key.
   * Particle node count must not increase (still N, not 2N).
   */
  it('fireOnce: re-rendering with same key does not re-emit particles', () => {
    const { rerender, UNSAFE_root } = render(
      <RevealBurst fireOnce particleCount={6} />,
    );
    // Count emitted particle nodes via testID prefix on the first render.
    const initialParticles = UNSAFE_root.findAll(
      (n: any) => typeof n.props?.testID === 'string' &&
        n.props.testID.startsWith('reveal-burst-particle-'),
    );
    const initialCount = initialParticles.length;

    // Re-render without changing the React key.
    rerender(<RevealBurst fireOnce particleCount={6} />);
    const afterRerender = UNSAFE_root.findAll(
      (n: any) => typeof n.props?.testID === 'string' &&
        n.props.testID.startsWith('reveal-burst-particle-'),
    );

    expect(afterRerender.length).toBe(initialCount);
    // And the count must not have doubled.
    expect(afterRerender.length).toBeLessThanOrEqual(initialCount);
  });
});
