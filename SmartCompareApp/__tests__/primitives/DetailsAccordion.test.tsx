/**
 * Primitive contract — DetailsAccordion.
 *
 * Contract (plan S0.3 + design doc § 3.1 ResultsScreen):
 *   - 3-section accordion shell with icon-circle + chevron rotate
 *   - Props: sections: { key, label, sub, icon, body }[]
 *   - Only ONE section open at a time (accordion behavior)
 *   - Chevron rotates 0deg → 180deg over 220ms ease (motion.accordionChevron)
 */
import React from 'react';
import { Text } from 'react-native';
import { render, fireEvent } from '@testing-library/react-native';
import { DetailsAccordion } from '../../src/components/primitives/DetailsAccordion';

// RNTL getByText only matches strings inside <Text> nodes — raw strings
// inside React Fragments don't register. Wrap each body in <Text>.
const sections = [
  { key: 'reviews', label: 'Reviews', sub: '4.6 · 1.2k', icon: 'star', body: <Text>Reviews body</Text> },
  { key: 'pros_cons', label: 'Pros & Cons', sub: '6 reasons', icon: 'list', body: <Text>PC body</Text> },
  { key: 'specs', label: 'Specs', sub: '12 fields', icon: 'chip', body: <Text>Specs body</Text> },
];

describe('DetailsAccordion primitive', () => {
  it('renders all three section headers', () => {
    const { getByText } = render(<DetailsAccordion sections={sections} />);
    expect(getByText('Reviews')).toBeTruthy();
    expect(getByText('Pros & Cons')).toBeTruthy();
    expect(getByText('Specs')).toBeTruthy();
  });

  it('opens a section on tap and shows body content', () => {
    const { getByText, queryByText } = render(<DetailsAccordion sections={sections} />);
    expect(queryByText('Reviews body')).toBeNull();
    fireEvent.press(getByText('Reviews'));
    expect(getByText('Reviews body')).toBeTruthy();
  });

  it('closes previously-open section when another opens (single-open invariant)', () => {
    const { getByText, queryByText } = render(<DetailsAccordion sections={sections} />);
    fireEvent.press(getByText('Reviews'));
    expect(getByText('Reviews body')).toBeTruthy();
    fireEvent.press(getByText('Specs'));
    // The single-open contract: opening Specs collapses Reviews.
    expect(queryByText('Reviews body')).toBeNull();
    expect(getByText('Specs body')).toBeTruthy();
  });

  it('exposes chevron rotation state per section via testID', () => {
    const { getByTestId } = render(<DetailsAccordion sections={sections} />);
    // Chevron testIDs follow `accordion-chevron-{key}` pattern; their
    // rotation prop is bound to the section's open state. We assert the
    // initial closed state — no chevron has rotation 180.
    for (const s of sections) {
      const chev = getByTestId(`accordion-chevron-${s.key}`);
      const rotated = chev.props?.style?.transform?.some?.(
        (t: any) => t.rotate === '180deg',
      );
      expect(rotated).toBeFalsy();
    }
  });
});
