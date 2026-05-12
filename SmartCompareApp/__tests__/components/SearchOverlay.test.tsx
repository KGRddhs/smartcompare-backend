/**
 * SearchOverlay tests — Bundle B/C/D Task 2.8.
 *
 * Verifies the "Enter TWO products to compare" guidance banner shows
 * until the user types a comparison-shaped query (containing " vs ",
 * " & ", " and ", or a comma).
 */
import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';
import { SearchOverlay } from '../../src/components/SearchOverlay';

describe('SearchOverlay — need-TWO-products hint', () => {
  it('shows the hint on first render when query is empty', () => {
    const { getByTestId } = render(
      <SearchOverlay
        visible
        onClose={jest.fn()}
        onSubmit={jest.fn()}
        recentSearches={[]}
      />
    );
    expect(getByTestId('search-need-two-hint')).toBeTruthy();
  });

  it('keeps the hint visible while the user is still typing one product', () => {
    const { getByTestId, queryByTestId } = render(
      <SearchOverlay
        visible
        onClose={jest.fn()}
        onSubmit={jest.fn()}
        recentSearches={[]}
      />
    );
    fireEvent.changeText(getByTestId('search-overlay-input'), 'iPhone 15');
    expect(queryByTestId('search-need-two-hint')).toBeTruthy();
  });

  it('dismisses the hint when "X vs Y" pattern is typed', () => {
    const { getByTestId, queryByTestId } = render(
      <SearchOverlay
        visible
        onClose={jest.fn()}
        onSubmit={jest.fn()}
        recentSearches={[]}
      />
    );
    fireEvent.changeText(
      getByTestId('search-overlay-input'),
      'iPhone 15 vs Galaxy S24'
    );
    expect(queryByTestId('search-need-two-hint')).toBeNull();
  });

  it('dismisses the hint when comma-separated products are typed', () => {
    const { getByTestId, queryByTestId } = render(
      <SearchOverlay
        visible
        onClose={jest.fn()}
        onSubmit={jest.fn()}
        recentSearches={[]}
      />
    );
    fireEvent.changeText(
      getByTestId('search-overlay-input'),
      'AirPods Pro, Sony WF-1000XM5'
    );
    expect(queryByTestId('search-need-two-hint')).toBeNull();
  });

  it('dismisses the hint when " and " separator is typed', () => {
    const { getByTestId, queryByTestId } = render(
      <SearchOverlay
        visible
        onClose={jest.fn()}
        onSubmit={jest.fn()}
        recentSearches={[]}
      />
    );
    fireEvent.changeText(
      getByTestId('search-overlay-input'),
      'Tesla Model 3 and BMW i4'
    );
    expect(queryByTestId('search-need-two-hint')).toBeNull();
  });

  it('renders nothing when overlay is hidden', () => {
    const { queryByTestId } = render(
      <SearchOverlay
        visible={false}
        onClose={jest.fn()}
        onSubmit={jest.fn()}
        recentSearches={[]}
      />
    );
    expect(queryByTestId('search-need-two-hint')).toBeNull();
  });
});
