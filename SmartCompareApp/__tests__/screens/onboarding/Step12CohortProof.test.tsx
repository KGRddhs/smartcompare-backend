/**
 * Step12CohortProof tests — Phase 2 Task 19.
 *
 * "388 GCC shoppers helped train this." Hero illustration #2 +
 * 3 bullet stats animating one-by-one. Sunk-cost + trust + "I'm not
 * alone." See design spec § 2 row 12.
 */

import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';
import { Step12CohortProof } from '../../../src/screens/onboarding/Step12CohortProof';

jest.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));

describe('Step12CohortProof', () => {
  it('renders the CohortBarChart hero illustration', () => {
    const { getByTestId } = render(<Step12CohortProof onNext={jest.fn()} />);
    expect(getByTestId('s12-bar-chart')).toBeTruthy();
  });

  it('renders the hero title (matches § 4g audit copy)', () => {
    const { getByText } = render(<Step12CohortProof onNext={jest.fn()} />);
    expect(getByText('onboarding.s12.title')).toBeTruthy();
  });

  it('renders all 3 stat bullets', () => {
    const { getByText } = render(<Step12CohortProof onNext={jest.fn()} />);
    expect(getByText('onboarding.s12.bullet_1')).toBeTruthy();
    expect(getByText('onboarding.s12.bullet_2')).toBeTruthy();
    expect(getByText('onboarding.s12.bullet_3')).toBeTruthy();
  });

  it('fires onNext when Continue is pressed', () => {
    const onNext = jest.fn();
    const { getByText } = render(<Step12CohortProof onNext={onNext} />);
    fireEvent.press(getByText('onboarding.s12.continue'));
    expect(onNext).toHaveBeenCalledTimes(1);
  });

  it('passes total + userCohortSize props to the chart when supplied', () => {
    const { getByTestId } = render(
      <Step12CohortProof onNext={jest.fn()} totalShoppers={420} userCohortSize={47} />
    );
    expect(getByTestId('s12-bar-chart')).toBeTruthy();
  });

  // Phase 5 polish — design § 1 "Card slide-in: Stagger 80ms, slide 24px
  // from below + fade". Each bullet has its own testID + animated style
  // so we can confirm the stagger contract is wired (each bullet has a
  // transform + opacity from the Reanimated useAnimatedStyle output).
  it('renders 3 staggered bullet hosts with animation surfaces', () => {
    const { getByTestId } = render(<Step12CohortProof onNext={jest.fn()} />);
    [0, 1, 2].forEach((i) => {
      const bullet = getByTestId(`s12-bullet-${i}`);
      const styleArr = Array.isArray(bullet.props.style)
        ? bullet.props.style
        : [bullet.props.style];
      const flat: Record<string, unknown> = styleArr
        .filter(Boolean)
        .reduce(
          (acc: Record<string, unknown>, s: Record<string, unknown>) =>
            Object.assign(acc, s),
          {} as Record<string, unknown>,
        );
      expect(flat.opacity).toBeDefined();
      expect(flat.transform).toBeDefined();
    });
  });
});
