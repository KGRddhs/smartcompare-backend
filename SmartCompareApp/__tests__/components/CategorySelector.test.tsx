/**
 * CategorySelector tests — Bundle B/C/D Task 2.9.
 *
 * Verifies the emoji-to-lucide swap is complete and the per-icon
 * imports preserve tree-shaking (no barrel import).
 */
import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';
import CategorySelector from '../../src/components/CategorySelector';

// S81-11 (E10, R-S11-15, C6): the fragrance-only launch row. Without
// `surfaces` the row is the one Fragrances chip; the six other categories are
// hidden everywhere and Skincare / Makeup render only as coming-soon chips
// (pinned by __tests__/s11/categoryRow.s11).
const ALL_NINE = [
  'electronics',
  'grocery',
  'supplements',
  'makeup',
  'skincare',
  'haircare',
  'fragrances',
  'fashion',
  'other',
];

describe('CategorySelector — lucide glyphs', () => {
  it('renders a chip for each of the 9 categories', () => {
    // S81-11: re-pinned to "exactly the Fragrances chip without surfaces".
    const { getByTestId, queryByTestId } = render(
      <CategorySelector value="fragrances" onChange={jest.fn()} />
    );
    expect(getByTestId('category-chip-fragrances')).toBeTruthy();
    for (const value of ALL_NINE.filter((v) => v !== 'fragrances')) {
      expect(queryByTestId(`category-chip-${value}`)).toBeNull();
    }
  });

  it('renders a lucide icon next to each chip label (mock-icon host element)', () => {
    // S81-11: one rendered chip -> one icon (was nine).
    const { UNSAFE_root } = render(
      <CategorySelector value="fragrances" onChange={jest.fn()} />
    );
    const mockIcons = UNSAFE_root.findAll(
      (n: any) =>
        typeof n.type === 'string' && n.type.startsWith('mock-icon-')
    );
    expect(mockIcons.length).toBe(1);
  });

  it('fires onChange with the category value when a chip is tapped', () => {
    const onChange = jest.fn();
    const { getByTestId } = render(
      <CategorySelector value={null} onChange={onChange} />
    );
    // S81-11: the pressed chip is the one live chip, fragrances.
    fireEvent.press(getByTestId('category-chip-fragrances'));
    expect(onChange).toHaveBeenCalledWith('fragrances');
  });

  it('marks the active chip via accessibilityState.selected', () => {
    // S81-11: fragrances selected = true; unselected = false.
    const selected = render(
      <CategorySelector value="fragrances" onChange={jest.fn()} />
    );
    expect(
      selected.getByTestId('category-chip-fragrances').props.accessibilityState
        ?.selected
    ).toBe(true);
    selected.unmount();
    const unselected = render(
      <CategorySelector value={null} onChange={jest.fn()} />
    );
    expect(
      unselected.getByTestId('category-chip-fragrances').props.accessibilityState
        ?.selected
    ).toBe(false);
  });

  it('source contains NO emoji codepoints (the swap is complete)', () => {
    const fs = require('fs');
    const path = require('path');
    const src = fs.readFileSync(
      path.resolve(__dirname, '../../src/components/CategorySelector.tsx'),
      'utf8'
    );
    // \u{1F...} or \u{2728} (sparkle) escapes should not exist in source.
    expect(src).not.toMatch(/\\u\{1F[0-9A-F]{3}\}/);
    expect(src).not.toMatch(/\\u2728/);
  });

  it('lucide imports are per-icon (not barrel) so tree-shaking works', () => {
    const fs = require('fs');
    const path = require('path');
    const src = fs.readFileSync(
      path.resolve(__dirname, '../../src/components/CategorySelector.tsx'),
      'utf8'
    );
    // Reject `import * as Lucide from 'lucide-react-native'` style.
    expect(src).not.toMatch(/import\s+\*\s+as\s+\w+\s+from\s+['"]lucide-react-native['"]/);
    // Confirm we DO use the named-import form.
    expect(src).toMatch(/import\s+\{\s*\w+/);
  });
});
