/**
 * Primitive contract — PrivacyRow.
 *
 * Source of truth: docs/claude-design-handoff/ui_kits/mobile/OnboardingExtras.jsx
 * PrivacyRow function (lines 154-170). 36px accentLight circle + accentDark
 * icon glyph + head/body pair.
 *
 * First consumer: Step05Trust (F-S2.W1). Future reuse: Profile/Settings
 * privacy surface in S3+.
 */
import React from 'react';
import { Text } from 'react-native';
import { render } from '@testing-library/react-native';
import { PrivacyRow } from '../../src/components/primitives/PrivacyRow';

describe('PrivacyRow primitive', () => {
  it('renders the head string', () => {
    const { getByText } = render(
      <PrivacyRow icon={<Text>✓</Text>} head="What we use" body="Some body copy." />,
    );
    expect(getByText('What we use')).toBeTruthy();
  });

  it('renders the body string', () => {
    const { getByText } = render(
      <PrivacyRow icon={<Text>✓</Text>} head="What we use" body="Some body copy." />,
    );
    expect(getByText('Some body copy.')).toBeTruthy();
  });

  it('renders the icon slot inside testID="privacy-row-icon"', () => {
    const { getByTestId } = render(
      <PrivacyRow icon={<Text testID="custom-icon">✓</Text>} head="H" body="B" />,
    );
    const wrapper = getByTestId('privacy-row-icon');
    expect(wrapper).toBeTruthy();
    // Caller's testID survives — confirms icon is rendered as a child
    expect(getByTestId('custom-icon')).toBeTruthy();
  });

  it('forwards testID to the row container', () => {
    const { getByTestId } = render(
      <PrivacyRow
        icon={<Text>✓</Text>}
        head="H"
        body="B"
        testID="privacy-row-1"
      />,
    );
    expect(getByTestId('privacy-row-1')).toBeTruthy();
  });

  it('circle is 36x36 per JSX spec', () => {
    const { getByTestId } = render(
      <PrivacyRow icon={<Text>✓</Text>} head="H" body="B" />,
    );
    const circle = getByTestId('privacy-row-icon');
    const styleArr = Array.isArray(circle.props.style)
      ? circle.props.style
      : [circle.props.style];
    const flattened = Object.assign({}, ...styleArr.filter(Boolean));
    expect(flattened.width).toBe(36);
    expect(flattened.height).toBe(36);
  });
});
