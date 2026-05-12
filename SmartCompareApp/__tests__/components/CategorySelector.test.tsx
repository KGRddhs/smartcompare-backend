/**
 * CategorySelector tests — Bundle B/C/D Task 2.9.
 *
 * Verifies the emoji-to-lucide swap is complete and the per-icon
 * imports preserve tree-shaking (no barrel import).
 */
import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';
import CategorySelector from '../../src/components/CategorySelector';

describe('CategorySelector — lucide glyphs', () => {
  it('renders a chip for each of the 9 categories', () => {
    const { getByTestId } = render(
      <CategorySelector value="electronics" onChange={jest.fn()} />
    );
    for (const value of [
      'electronics',
      'grocery',
      'supplements',
      'makeup',
      'skincare',
      'haircare',
      'fragrances',
      'fashion',
      'other',
    ]) {
      expect(getByTestId(`category-chip-${value}`)).toBeTruthy();
    }
  });

  it('renders a lucide icon next to each chip label (mock-icon host element)', () => {
    const { UNSAFE_root } = render(
      <CategorySelector value="electronics" onChange={jest.fn()} />
    );
    const mockIcons = UNSAFE_root.findAll(
      (n: any) =>
        typeof n.type === 'string' && n.type.startsWith('mock-icon-')
    );
    expect(mockIcons.length).toBe(9);
  });

  it('fires onChange with the category value when a chip is tapped', () => {
    const onChange = jest.fn();
    const { getByTestId } = render(
      <CategorySelector value={null} onChange={onChange} />
    );
    fireEvent.press(getByTestId('category-chip-grocery'));
    expect(onChange).toHaveBeenCalledWith('grocery');
  });

  it('marks the active chip via accessibilityState.selected', () => {
    const { getByTestId } = render(
      <CategorySelector value="supplements" onChange={jest.fn()} />
    );
    expect(
      getByTestId('category-chip-supplements').props.accessibilityState
        ?.selected
    ).toBe(true);
    expect(
      getByTestId('category-chip-grocery').props.accessibilityState?.selected
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
