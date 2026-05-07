/**
 * StageChecklist tests — Phase 2 Task 11.
 *
 * Vertical 5-row list with ✓ (done, emerald) / ⟳ (active spinner, emerald)
 * / ○ (pending, gray). Used on the Results loading screen and on onboarding
 * screen 14 (theatrical loading). Each transition pending→done OR
 * active→done fires haptic light per design spec Section 3.
 */

import React from 'react';
import { render } from '@testing-library/react-native';

const impactAsyncMock = jest.fn().mockResolvedValue(undefined);
jest.mock('expo-haptics', () => ({
  impactAsync: (style: string) => impactAsyncMock(style),
  ImpactFeedbackStyle: { Light: 'light', Medium: 'medium', Heavy: 'heavy' },
  __esModule: true,
}));

import { StageChecklist, Stage } from '../../src/components/StageChecklist';

const baseStages: Stage[] = [
  { id: 'init', label: 'Understanding your query', status: 'done' },
  { id: 'specs', label: 'Reading specs from 6 sources', status: 'active' },
  { id: 'prices', label: 'Cross-checking 12 retailers in Bahrain', status: 'pending' },
  { id: 'reviews', label: 'Analyzing 200+ reviews', status: 'pending' },
  { id: 'verdict', label: 'Locking in your winner', status: 'pending' },
];

beforeEach(() => {
  impactAsyncMock.mockClear();
});

describe('StageChecklist', () => {
  it('renders all 5 stages with their labels', () => {
    const { getByText } = render(<StageChecklist stages={baseStages} />);
    for (const s of baseStages) {
      expect(getByText(s.label)).toBeTruthy();
    }
  });

  it('exposes status via accessibilityLabel on each row icon', () => {
    const { getByTestId } = render(<StageChecklist stages={baseStages} />);
    expect(getByTestId('stage-init-icon').props.accessibilityLabel).toBe('done');
    expect(getByTestId('stage-specs-icon').props.accessibilityLabel).toBe('active');
    expect(getByTestId('stage-prices-icon').props.accessibilityLabel).toBe('pending');
    expect(getByTestId('stage-reviews-icon').props.accessibilityLabel).toBe('pending');
    expect(getByTestId('stage-verdict-icon').props.accessibilityLabel).toBe('pending');
  });

  it('renders the right glyph for each status', () => {
    const { getByTestId } = render(<StageChecklist stages={baseStages} />);
    expect(getByTestId('stage-init-glyph').props.children).toBe('\u2713'); // ✓
    expect(getByTestId('stage-specs-glyph').props.children).toBe('\u27F3'); // ⟳
    expect(getByTestId('stage-prices-glyph').props.children).toBe('\u25CB'); // ○
  });

  it('does NOT fire haptic for stages already done on initial mount', () => {
    render(<StageChecklist stages={baseStages} />);
    expect(impactAsyncMock).not.toHaveBeenCalled();
  });

  it('fires haptic light when a stage transitions pending → done', () => {
    const { rerender } = render(<StageChecklist stages={baseStages} />);
    impactAsyncMock.mockClear();
    const transitioned = baseStages.map((s) =>
      s.id === 'prices' ? { ...s, status: 'done' as const } : s
    );
    rerender(<StageChecklist stages={transitioned} />);
    expect(impactAsyncMock).toHaveBeenCalledTimes(1);
    expect(impactAsyncMock).toHaveBeenCalledWith('light');
  });

  it('fires haptic light when a stage transitions active → done', () => {
    const { rerender } = render(<StageChecklist stages={baseStages} />);
    impactAsyncMock.mockClear();
    const transitioned = baseStages.map((s) =>
      s.id === 'specs' ? { ...s, status: 'done' as const } : s
    );
    rerender(<StageChecklist stages={transitioned} />);
    expect(impactAsyncMock).toHaveBeenCalledTimes(1);
    expect(impactAsyncMock).toHaveBeenCalledWith('light');
  });

  it('does not re-fire haptic on a status that stays "done"', () => {
    const { rerender } = render(<StageChecklist stages={baseStages} />);
    impactAsyncMock.mockClear();
    rerender(<StageChecklist stages={baseStages} />);
    expect(impactAsyncMock).not.toHaveBeenCalled();
  });

  it('handles an empty stage list cleanly', () => {
    const { queryByText } = render(<StageChecklist stages={[]} />);
    expect(queryByText('Understanding your query')).toBeNull();
  });
});
