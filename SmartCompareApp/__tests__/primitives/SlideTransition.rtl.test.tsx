/**
 * SlideTransition RTL snapshot — dedicated direction-mirror test.
 *
 * Complements __tests__/primitives/SlideTransition.test.tsx (which tests
 * the data-direction prop). This file pins the rendered tree as a snapshot
 * under BOTH locales so a visual diff during S2 walkthroughs catches any
 * regression in the translateX sign or wrapper attributes.
 *
 * RED until frontend lands src/components/SlideTransition.tsx (S0.4).
 *
 * Once S0.4 ships, the two snapshots committed alongside this file should
 * be byte-identical EXCEPT for `data-direction` ("ltr" vs "rtl") and the
 * sign on any initial translateX value the wrapper exposes.
 */
import React from 'react';
import { I18nManager, Text } from 'react-native';
import { render } from '@testing-library/react-native';
import { SlideTransition } from '../../src/components/SlideTransition';

describe('SlideTransition — RTL/LTR snapshot mirror', () => {
  afterEach(() => {
    (I18nManager as any).isRTL = false;
  });

  it('LTR snapshot — step=2 incoming, slides in from right', () => {
    (I18nManager as any).isRTL = false;
    const tree = render(
      <SlideTransition step={2} testID="slide-ltr">
        <Text>step content</Text>
      </SlideTransition>,
    ).toJSON();
    expect(tree).toMatchSnapshot();
  });

  it('RTL snapshot — step=2 incoming, slides in from left', () => {
    (I18nManager as any).isRTL = true;
    const tree = render(
      <SlideTransition step={2} testID="slide-rtl">
        <Text>step content</Text>
      </SlideTransition>,
    ).toJSON();
    expect(tree).toMatchSnapshot();
  });

  it('direction flip is observable via the rendered data-direction prop only', () => {
    // Belt-and-braces with the main test file: ensure the RTL flip is
    // captured at the visible-prop level, not just internal state. This
    // is the assertion Q-S2 will rely on during the Arabic-locale walk.
    (I18nManager as any).isRTL = false;
    const ltr = render(
      <SlideTransition step={2} testID="dir-probe">
        <Text>x</Text>
      </SlideTransition>,
    );
    expect(ltr.getByTestId('dir-probe').props['data-direction']).toBe('ltr');

    (I18nManager as any).isRTL = true;
    const rtl = render(
      <SlideTransition step={2} testID="dir-probe">
        <Text>x</Text>
      </SlideTransition>,
    );
    expect(rtl.getByTestId('dir-probe').props['data-direction']).toBe('rtl');
  });
});
