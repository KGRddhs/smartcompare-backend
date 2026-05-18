/**
 * Bundle C — HeroRings sparse-data sanity (Plan B.6.1, spec § 2d).
 *
 * The hero card never apologizes for sparse data. No "Limited data" pill,
 * no "Low confidence" badge — the calibrated number stands clean.
 *
 * § 2e weird-mode hero suppression lives in ResultsScreen (B.6.3),
 * not here — HeroRings stays presentational.
 */
import React from 'react';
import { render } from '@testing-library/react-native';

import { HeroRings } from '../../src/components/results/HeroRings';

test('renders score cleanly with NO "Limited data" pill even when scores are low', () => {
  const { queryByText } = render(<HeroRings scoreA={61} scoreB={62} winnerIndex={1} />);
  expect(queryByText(/limited data/i)).toBeNull();
  expect(queryByText(/low confidence/i)).toBeNull();
});

test('renders score cleanly with NO apologetic copy at any low score', () => {
  const { queryByText } = render(<HeroRings scoreA={60} scoreB={60} winnerIndex={0} />);
  // Forbidden vocab guarded — no scary or apologetic copy on the hero.
  expect(queryByText(/couldn't|try again|failed|missing|unavailable/i)).toBeNull();
});

test('two rings render with their numerical scores visible', () => {
  const { getAllByText } = render(<HeroRings scoreA={88} scoreB={72} winnerIndex={0} />);
  // The number sits in each ring's center overlay.
  expect(getAllByText('88').length).toBeGreaterThan(0);
  expect(getAllByText('72').length).toBeGreaterThan(0);
});
