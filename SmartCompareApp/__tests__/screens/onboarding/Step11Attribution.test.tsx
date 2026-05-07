/**
 * Step11Attribution tests — Phase 2 Task 15.
 *
 * 6 stacked cards: Friend / Instagram / TikTok / App Store / Google /
 * Other. Market-research signal. Backend: POST /api/v1/auth/attribution
 * (Task 8). See design spec § 2 row 11.
 */

import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';
import { Step11Attribution } from '../../../src/screens/onboarding/Step11Attribution';

jest.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));

describe('Step11Attribution', () => {
  it('renders all 6 attribution sources matching the backend enum', () => {
    const { getByTestId } = render(<Step11Attribution onChange={jest.fn()} />);
    expect(getByTestId('attr-friend')).toBeTruthy();
    expect(getByTestId('attr-instagram')).toBeTruthy();
    expect(getByTestId('attr-tiktok')).toBeTruthy();
    expect(getByTestId('attr-app_store')).toBeTruthy();
    expect(getByTestId('attr-google')).toBeTruthy();
    expect(getByTestId('attr-other')).toBeTruthy();
  });

  it('fires onChange("instagram") on Instagram tap', () => {
    const onChange = jest.fn();
    const { getByTestId } = render(<Step11Attribution onChange={onChange} />);
    fireEvent.press(getByTestId('attr-instagram'));
    expect(onChange).toHaveBeenCalledWith('instagram');
  });

  it('fires onChange("app_store") with the snake_case value', () => {
    const onChange = jest.fn();
    const { getByTestId } = render(<Step11Attribution onChange={onChange} />);
    fireEvent.press(getByTestId('attr-app_store'));
    expect(onChange).toHaveBeenCalledWith('app_store');
  });

  it('marks selected with accessibilityState.selected=true', () => {
    const { getByTestId } = render(
      <Step11Attribution value="tiktok" onChange={jest.fn()} />
    );
    expect(getByTestId('attr-tiktok').props.accessibilityState?.selected).toBe(true);
    expect(getByTestId('attr-friend').props.accessibilityState?.selected).toBe(false);
  });
});
