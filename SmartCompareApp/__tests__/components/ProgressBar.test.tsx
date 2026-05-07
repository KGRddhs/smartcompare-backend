/**
 * ProgressBar tests — Phase 2 Task 12.
 *
 * Adds the `variableEasing` variant per design spec Section 3 ("Variable
 * progress easing" mind-trick): 0→25% fast (0.6s), 25→60% slow, 60→90%
 * fast, 90→100% snap. Used on the Results loading screen to make the
 * 5-12s wait feel intentional even when the backend is faster.
 *
 * Per-segment timing is verified on-device at the Phase 2 QA gate.
 * These unit tests assert end-state width and the prop surface only.
 */

import React from 'react';
import { render } from '@testing-library/react-native';
import { ProgressBar } from '../../src/components/ProgressBar';

describe('ProgressBar', () => {
  it('renders with default linear easing when variableEasing is unset', () => {
    const { getByTestId } = render(
      <ProgressBar progress={0.5} testID="progress" />
    );
    expect(getByTestId('progress-track')).toBeTruthy();
    expect(getByTestId('progress-fill')).toBeTruthy();
  });

  it('accepts variableEasing prop without crashing', () => {
    const { getByTestId } = render(
      <ProgressBar progress={0.5} variableEasing testID="progress" />
    );
    expect(getByTestId('progress-fill')).toBeTruthy();
  });

  it('end-state width reflects clamped progress (0-1 → 0-100%)', () => {
    const { getByTestId } = render(
      <ProgressBar progress={0.42} variableEasing testID="progress" />
    );
    const fill = getByTestId('progress-fill');
    const styles = Array.isArray(fill.props.style) ? fill.props.style : [fill.props.style];
    const widthEntry = styles.find((s: any) => s && typeof s.width === 'string');
    expect(widthEntry?.width).toBe('42%');
  });

  it('clamps progress > 1 to 100%', () => {
    const { getByTestId } = render(
      <ProgressBar progress={1.5} variableEasing testID="progress" />
    );
    const fill = getByTestId('progress-fill');
    const styles = Array.isArray(fill.props.style) ? fill.props.style : [fill.props.style];
    const widthEntry = styles.find((s: any) => s && typeof s.width === 'string');
    expect(widthEntry?.width).toBe('100%');
  });

  it('clamps progress < 0 to 0%', () => {
    const { getByTestId } = render(
      <ProgressBar progress={-0.2} variableEasing testID="progress" />
    );
    const fill = getByTestId('progress-fill');
    const styles = Array.isArray(fill.props.style) ? fill.props.style : [fill.props.style];
    const widthEntry = styles.find((s: any) => s && typeof s.width === 'string');
    expect(widthEntry?.width).toBe('0%');
  });

  it('keeps the legacy single-arg shape (no testID, no variableEasing)', () => {
    // Backwards-compat with existing usages in OnboardingScreen,
    // ResultsScreen, InviteeQuizScreen.
    const { toJSON } = render(<ProgressBar progress={0.5} />);
    expect(toJSON()).toBeTruthy();
  });
});
