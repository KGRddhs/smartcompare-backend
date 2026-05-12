/**
 * ImageSlotRow edge-case coverage.
 *
 * Extends the baseline 4 tests in ImageSlotRow.test.tsx with the boundary
 * cases test-bcd owns per docs/plans/2026-05-12-bundle-bcd-consolidated.md
 * Phase 1 Task 7: reverse-fill order, double-remove resilience, identical
 * uri rendering, mount immutability.
 *
 * Spec: docs/plans/2026-05-12-bundle-bcd-consolidated-design.md § 4.6
 */
import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';
import ImageSlotRow, { Slots } from '../../src/components/ImageSlotRow';

const FILLED_A = { uri: 'file://a.jpg' };
const FILLED_B = { uri: 'file://b.jpg' };

describe('ImageSlotRow — edges', () => {
  it('renders thumb in slot 1 only when slot 0 is empty (reverse fill)', () => {
    const slots: Slots = [null, FILLED_B];
    const { queryByTestId, getByText } = render(
      <ImageSlotRow slots={slots} onChange={() => {}} />
    );
    expect(queryByTestId('image-slot-0-thumb')).toBeNull();
    expect(queryByTestId('image-slot-1-thumb')).toBeTruthy();
    // Slot 0 still displays its "1" placeholder
    expect(getByText('1')).toBeTruthy();
  });

  it('renders 2 thumbs and 2 remove buttons when both filled', () => {
    const slots: Slots = [FILLED_A, FILLED_B];
    const { getByTestId } = render(
      <ImageSlotRow slots={slots} onChange={() => {}} />
    );
    expect(getByTestId('image-slot-0-thumb')).toBeTruthy();
    expect(getByTestId('image-slot-1-thumb')).toBeTruthy();
    expect(getByTestId('image-slot-0-remove')).toBeTruthy();
    expect(getByTestId('image-slot-1-remove')).toBeTruthy();
  });

  it('renders 2 independent thumbs when identical uri passed to both slots', () => {
    // Parent may reuse the same captured image — we render 2 independent
    // <Image> nodes rather than dedupe (a real-world camera flow can capture
    // the same product twice and the user should still see both slots).
    const same = { uri: 'file://identical.jpg' };
    const slots: Slots = [same, same];
    const { getByTestId } = render(
      <ImageSlotRow slots={slots} onChange={() => {}} />
    );
    expect(getByTestId('image-slot-0-thumb')).toBeTruthy();
    expect(getByTestId('image-slot-1-thumb')).toBeTruthy();
  });

  it('remove on slot 1 preserves slot 0', () => {
    const slots: Slots = [FILLED_A, FILLED_B];
    const onChange = jest.fn();
    const { getByTestId } = render(
      <ImageSlotRow slots={slots} onChange={onChange} />
    );
    fireEvent.press(getByTestId('image-slot-1-remove'));
    expect(onChange).toHaveBeenCalledWith([FILLED_A, null]);
  });

  it('rapid double-remove on slot 0 fires onChange twice without crashing', () => {
    // Component is stateless on its props — both presses produce the same
    // payload from the same render snapshot. Parent owns state consolidation.
    const slots: Slots = [FILLED_A, FILLED_B];
    const onChange = jest.fn();
    const { getByTestId } = render(
      <ImageSlotRow slots={slots} onChange={onChange} />
    );
    const btn = getByTestId('image-slot-0-remove');
    fireEvent.press(btn);
    fireEvent.press(btn);
    expect(onChange).toHaveBeenCalledTimes(2);
    expect(onChange).toHaveBeenNthCalledWith(1, [null, FILLED_B]);
    expect(onChange).toHaveBeenNthCalledWith(2, [null, FILLED_B]);
  });

  it('does not call onChange on mount', () => {
    const onChange = jest.fn();
    render(<ImageSlotRow slots={[null, null]} onChange={onChange} />);
    expect(onChange).not.toHaveBeenCalled();
  });

  it('does not mutate the slots prop when remove fires', () => {
    // Mutation here would silently break React reconciliation in the parent
    // (same reference → no re-render). The remove handler must return a new tuple.
    const slots: Slots = [FILLED_A, FILLED_B];
    const onChange = jest.fn();
    const { getByTestId } = render(
      <ImageSlotRow slots={slots} onChange={onChange} />
    );
    fireEvent.press(getByTestId('image-slot-0-remove'));
    expect(slots[0]).toEqual(FILLED_A);
    expect(slots[1]).toEqual(FILLED_B);
  });
});
