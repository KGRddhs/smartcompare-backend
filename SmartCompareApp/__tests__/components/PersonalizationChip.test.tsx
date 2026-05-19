/**
 * Bundle C — PersonalizationChip (Plan B.8.3, spec § 7a + 7c).
 *
 * Compact single-line chip below the verdict. Up to 3 direction arrows
 * (the 3 strongest shifts vs category defaults). Arrows-only — NEVER
 * percentages, never coefficients, never cap math (rule #2, spec § 7a).
 *
 * Hidden when applied_shifts is empty or undefined (no priorities set
 * or no significant shifts).
 */
import React from 'react';
import { render } from '@testing-library/react-native';

import { PersonalizationChip } from '../../src/components/results/PersonalizationChip';

test('renders chip with 3 arrows when applied_shifts has 3+ entries', () => {
  const shifts = [
    { dim_display: 'performance', direction: 'up' as const },
    { dim_display: 'build', direction: 'up' as const },
    { dim_display: 'brand_recognition', direction: 'down' as const },
  ];
  const { getByText } = render(<PersonalizationChip appliedShifts={shifts} />);
  // Mock i18n returns the key; the chip_template wraps the joined arrows.
  expect(getByText(/Weighted/)).toBeTruthy();
});

test('caps to 3 arrows even when more shifts emitted', () => {
  const shifts = [
    { dim_display: 'performance', direction: 'up' as const },
    { dim_display: 'build', direction: 'up' as const },
    { dim_display: 'brand_recognition', direction: 'down' as const },
    { dim_display: 'design', direction: 'up' as const },
    { dim_display: 'durability', direction: 'down' as const },
  ];
  const tree = render(<PersonalizationChip appliedShifts={shifts} />).toJSON();
  const text = JSON.stringify(tree);
  // performance, build, brand recognition (underscores → spaces) appear
  expect(text).toContain('performance');
  expect(text).toContain('build');
  expect(text).toContain('brand recognition');
  // design and durability (4th + 5th) do NOT
  expect(text).not.toContain('design');
  expect(text).not.toContain('durability');
});

test('hidden when applied_shifts is empty', () => {
  const tree = render(<PersonalizationChip appliedShifts={[]} />).toJSON();
  expect(tree).toBeNull();
});

test('hidden when applied_shifts is undefined', () => {
  const tree = render(<PersonalizationChip appliedShifts={undefined} />).toJSON();
  expect(tree).toBeNull();
});

test('NO percentages or coefficient leaks in rendered text (spec § 7a + rule #2)', () => {
  const shifts = [
    { dim_display: 'performance', direction: 'up' as const },
  ];
  const tree = render(<PersonalizationChip appliedShifts={shifts} />).toJSON();
  const text = JSON.stringify(tree);
  expect(text).not.toMatch(/\d+%/);
  expect(text).not.toMatch(/coefficient|weight:\s*\d|cap of/i);
});

test('NO scary copy in rendered chip', () => {
  const shifts = [{ dim_display: 'performance', direction: 'up' as const }];
  const tree = render(<PersonalizationChip appliedShifts={shifts} />).toJSON();
  const text = JSON.stringify(tree);
  expect(text).not.toMatch(/\b(couldn't|try again|Failed to)\b/i);
  expect(text).not.toMatch(/(تعذر|فشل)/);
});

test('substitutes underscores in dim_display with spaces (display-friendly)', () => {
  const shifts = [{ dim_display: 'brand_recognition', direction: 'down' as const }];
  const tree = render(<PersonalizationChip appliedShifts={shifts} />).toJSON();
  const text = JSON.stringify(tree);
  // "brand recognition" appears (with a space), not "brand_recognition"
  expect(text).toContain('brand recognition');
  expect(text).not.toContain('brand_recognition');
});
