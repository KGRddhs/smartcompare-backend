import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';
import ImageSlotRow from '../../src/components/ImageSlotRow';

describe('ImageSlotRow', () => {
  it('renders 2 empty slots with placeholder testIDs', () => {
    const onChange = jest.fn();
    const { getByTestId } = render(
      <ImageSlotRow slots={[null, null]} onChange={onChange} />
    );
    expect(getByTestId('image-slot-0')).toBeTruthy();
    expect(getByTestId('image-slot-1')).toBeTruthy();
  });

  it('renders thumbnail when slot filled', () => {
    const { getByTestId } = render(
      <ImageSlotRow
        slots={[{ uri: 'file://photo1.jpg' }, null]}
        onChange={jest.fn()}
      />
    );
    expect(getByTestId('image-slot-0-thumb')).toBeTruthy();
  });

  it('removes slot when × tapped', () => {
    const onChange = jest.fn();
    const { getByTestId } = render(
      <ImageSlotRow
        slots={[{ uri: 'file://photo1.jpg' }, null]}
        onChange={onChange}
      />
    );
    fireEvent.press(getByTestId('image-slot-0-remove'));
    expect(onChange).toHaveBeenCalledWith([null, null]);
  });

  it('does not show remove button on empty slot', () => {
    const { queryByTestId } = render(
      <ImageSlotRow slots={[null, null]} onChange={jest.fn()} />
    );
    expect(queryByTestId('image-slot-0-remove')).toBeNull();
    expect(queryByTestId('image-slot-1-remove')).toBeNull();
  });
});
