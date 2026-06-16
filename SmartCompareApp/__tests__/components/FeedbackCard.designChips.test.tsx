/**
 * FeedbackCard — design-structure pass (2026-06-16).
 *
 * The card matches the design-system reference (ResultsScreen.jsx 384-404):
 * a "Was this helpful?" title + a single row of three pill chips
 * (Accurate / Detailed / Fast). NO thumbs up/down, NO free-text box.
 * Tapping a chip fires the existing feedback event with a positive-helpful
 * signal + the chosen quality in mattered_most, then shows the thanks state.
 */

import React from 'react';
import { render, fireEvent, waitFor } from '@testing-library/react-native';

jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

const submitFeedbackMock = jest.fn().mockResolvedValue({ success: true });
jest.mock('../../src/services/api', () => ({
  submitFeedback: (...args: any[]) => submitFeedbackMock(...args),
}));

import FeedbackCard from '../../src/components/FeedbackCard';

describe('FeedbackCard — reference chips', () => {
  beforeEach(() => {
    submitFeedbackMock.mockClear();
  });

  it('renders the title + the three quality chips (no thumbs, no text box)', () => {
    const { getByText, getByTestId, queryByText } = render(<FeedbackCard />);
    expect(getByText('results.feedback.title')).toBeTruthy();
    expect(getByTestId('feedback-chip-accurate')).toBeTruthy();
    expect(getByTestId('feedback-chip-detailed')).toBeTruthy();
    expect(getByTestId('feedback-chip-fast')).toBeTruthy();
    // No submit button surface from the old design.
    expect(queryByText('results.feedback.submit')).toBeNull();
  });

  it('fires the feedback event with useful:true + the chip in mattered_most', async () => {
    const onSubmitted = jest.fn();
    const { getByTestId } = render(
      <FeedbackCard comparisonId="cmp-1" onSubmitted={onSubmitted} />
    );
    fireEvent.press(getByTestId('feedback-chip-detailed'));
    await waitFor(() => expect(submitFeedbackMock).toHaveBeenCalledTimes(1));
    expect(submitFeedbackMock).toHaveBeenCalledWith({
      useful: true,
      comparison_id: 'cmp-1',
      mattered_most: ['detailed'],
    });
    expect(onSubmitted).toHaveBeenCalled();
  });

  it('shows the thanks state after a chip tap', async () => {
    const { getByTestId, getByText } = render(<FeedbackCard />);
    fireEvent.press(getByTestId('feedback-chip-fast'));
    await waitFor(() =>
      expect(getByText('results.feedback.thanks')).toBeTruthy()
    );
  });

  it('renders the thanks state immediately when parent marks submitted', () => {
    const { getByText, queryByTestId } = render(
      <FeedbackCard submitted />
    );
    expect(getByText('results.feedback.thanks')).toBeTruthy();
    expect(queryByTestId('feedback-chip-accurate')).toBeNull();
  });
});
