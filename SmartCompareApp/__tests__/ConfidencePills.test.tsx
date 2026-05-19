// Bundle C — ConfidencePills tests (Section C plan C.6.3 / C.6.4).
//
// Spec §5b + 5c: 3 small pills (Price · Reviews · Specs) replacing the legacy
// single-word banner. Tap → bottom sheet with countable facts.
//
// Price pill HIDDEN ENTIRELY (not muted) when the caller passes
// `hidePricePill=true` (caller computes via parseSourceMethod helper / spec §5c).
//
// Updated for B.7 component contract:
//   <ConfidencePills
//     confidence={{ price?: Level, reviews?: Level, specs?: Level }}
//     hidePricePill={boolean}
//     onPillPress={(leg) => void}
//     testID="confidence-pills"
//   />
// Default testID prefix: `confidence-pills-${leg}` per pill.

import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';
import { expectNoForbiddenStrings } from './_bundle_c_helpers';
import { ConfidencePills } from '../src/components/results/ConfidencePills';

jest.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));

describe('ConfidencePills (Bundle C §5)', () => {
  it('renders all 3 pills when hidePricePill is false', () => {
    const onPillPress = jest.fn();
    const { getByTestId } = render(
      <ConfidencePills
        confidence={{ price: 'strong', reviews: 'strong', specs: 'strong' }}
        hidePricePill={false}
        onPillPress={onPillPress}
      />,
    );
    expect(getByTestId('confidence-pills-price')).toBeTruthy();
    expect(getByTestId('confidence-pills-reviews')).toBeTruthy();
    expect(getByTestId('confidence-pills-specs')).toBeTruthy();
  });

  it('hides Price pill ENTIRELY when hidePricePill=true (§5c)', () => {
    const onPillPress = jest.fn();
    const { queryByTestId, toJSON } = render(
      <ConfidencePills
        confidence={{ price: 'strong', reviews: 'strong', specs: 'strong' }}
        hidePricePill={true}
        onPillPress={onPillPress}
      />,
    );
    // Spec §5c — pill ABSENT from render tree, not muted
    expect(queryByTestId('confidence-pills-price')).toBeNull();
    // Reviews + Specs still render
    expect(queryByTestId('confidence-pills-reviews')).toBeTruthy();
    expect(queryByTestId('confidence-pills-specs')).toBeTruthy();
    // NO "estimated" wording anywhere user-visible
    expectNoForbiddenStrings(toJSON());
  });

  it('omits a leg whose confidence is undefined', () => {
    const onPillPress = jest.fn();
    const { queryByTestId } = render(
      <ConfidencePills
        confidence={{ reviews: 'strong', specs: 'strong' }}
        hidePricePill={false}
        onPillPress={onPillPress}
      />,
    );
    expect(queryByTestId('confidence-pills-price')).toBeNull();
    expect(queryByTestId('confidence-pills-reviews')).toBeTruthy();
  });

  it('renders null when no legs present (§5b — caller decides fallback)', () => {
    const onPillPress = jest.fn();
    const { toJSON } = render(
      <ConfidencePills
        confidence={{}}
        hidePricePill={false}
        onPillPress={onPillPress}
      />,
    );
    expect(toJSON()).toBeNull();
  });

  it('fires onPillPress with the correct leg name when tapped', () => {
    const onPillPress = jest.fn();
    const { getByTestId } = render(
      <ConfidencePills
        confidence={{ price: 'strong', reviews: 'strong', specs: 'strong' }}
        hidePricePill={false}
        onPillPress={onPillPress}
      />,
    );
    fireEvent.press(getByTestId('confidence-pills-reviews'));
    expect(onPillPress).toHaveBeenCalledWith('reviews');
    fireEvent.press(getByTestId('confidence-pills-specs'));
    expect(onPillPress).toHaveBeenCalledWith('specs');
  });

  it('NO forbidden vocabulary anywhere in rendered tree', () => {
    const onPillPress = jest.fn();
    const tree = render(
      <ConfidencePills
        confidence={{ price: 'strong', reviews: 'acceptable', specs: 'weak' }}
        hidePricePill={false}
        onPillPress={onPillPress}
      />,
    ).toJSON();
    expectNoForbiddenStrings(tree);
  });

  it('snapshot — all 3 strong, no hide', () => {
    const onPillPress = jest.fn();
    const tree = render(
      <ConfidencePills
        confidence={{ price: 'strong', reviews: 'strong', specs: 'strong' }}
        hidePricePill={false}
        onPillPress={onPillPress}
      />,
    ).toJSON();
    expect(tree).toMatchSnapshot();
  });

  it('snapshot — Price pill hidden, mixed strengths', () => {
    const onPillPress = jest.fn();
    const tree = render(
      <ConfidencePills
        confidence={{ price: 'weak', reviews: 'strong', specs: 'acceptable' }}
        hidePricePill={true}
        onPillPress={onPillPress}
      />,
    ).toJSON();
    expect(tree).toMatchSnapshot();
  });
});
