/**
 * StreamingProductCard tests — Phase 3 Task 27.
 *
 * Wraps the existing product card and fills fields progressively as SSE
 * events arrive. See design § 3 — "Streaming data preview" mind-trick:
 * title fills first, then specs, then prices count up (BHD numbers tick
 * via CounterTicker), then star rating fades in.
 */

import React from 'react';
import { render } from '@testing-library/react-native';
import { StreamingProductCard } from '../../src/components/StreamingProductCard';

describe('StreamingProductCard', () => {
  it('renders the title slot once a name is supplied', () => {
    const { getByText } = render(
      <StreamingProductCard
        testID="card"
        stage="specs"
        product={{ name: 'iPhone 15 Pro' }}
      />
    );
    expect(getByText('iPhone 15 Pro')).toBeTruthy();
  });

  it('shows a title placeholder when stage is "init"', () => {
    const { getByTestId, queryByText } = render(
      <StreamingProductCard testID="card" stage="init" />
    );
    expect(getByTestId('card-title-skeleton')).toBeTruthy();
    expect(queryByText('iPhone 15 Pro')).toBeNull();
  });

  it('hides specs section before stage "specs"', () => {
    const { queryByTestId } = render(
      <StreamingProductCard
        testID="card"
        stage="init"
        product={{ name: 'iPhone 15' }}
      />
    );
    expect(queryByTestId('card-specs')).toBeNull();
  });

  it('renders specs once stage reaches "specs"', () => {
    const { getByTestId } = render(
      <StreamingProductCard
        testID="card"
        stage="specs"
        product={{ name: 'iPhone 15', specs: { storage: '256GB', battery: '3349 mAh' } }}
      />
    );
    expect(getByTestId('card-specs')).toBeTruthy();
  });

  it('renders the price slot once stage reaches "prices"', () => {
    const { getByTestId } = render(
      <StreamingProductCard
        testID="card"
        stage="prices"
        product={{ name: 'iPhone 15', price: { amount: 295, currency: 'BHD' } }}
      />
    );
    expect(getByTestId('card-price')).toBeTruthy();
  });

  it('hides the price slot before stage "prices"', () => {
    const { queryByTestId } = render(
      <StreamingProductCard
        testID="card"
        stage="specs"
        product={{ name: 'iPhone 15', price: { amount: 295, currency: 'BHD' } }}
      />
    );
    expect(queryByTestId('card-price')).toBeNull();
  });

  it('renders rating once stage reaches "reviews"', () => {
    const { getByTestId } = render(
      <StreamingProductCard
        testID="card"
        stage="reviews"
        product={{ name: 'iPhone 15', rating: 4.7 }}
      />
    );
    expect(getByTestId('card-rating')).toBeTruthy();
  });

  it('handles missing optional fields without crashing', () => {
    const { toJSON } = render(
      <StreamingProductCard testID="card" stage="prices" product={{ name: 'iPhone 15' }} />
    );
    expect(toJSON()).toBeTruthy();
  });

  it('renders all slots (title, specs, price, rating) at stage "verdict"', () => {
    const { getByTestId } = render(
      <StreamingProductCard
        testID="card"
        stage="verdict"
        product={{
          name: 'iPhone 15',
          specs: { storage: '256GB' },
          price: { amount: 295, currency: 'BHD' },
          rating: 4.7,
        }}
      />
    );
    expect(getByTestId('card-title')).toBeTruthy();
    expect(getByTestId('card-specs')).toBeTruthy();
    expect(getByTestId('card-price')).toBeTruthy();
    expect(getByTestId('card-rating')).toBeTruthy();
  });

  it('shows the converted-from-USD caption for a converted_usd price', () => {
    const { getByTestId } = render(
      <StreamingProductCard
        testID="card"
        stage="prices"
        product={{
          name: 'Sauvage',
          price: { amount: 45, currency: 'BHD', source_method: 'converted_usd' },
        }}
      />
    );
    expect(getByTestId('card-converted')).toBeTruthy();
  });

  it('hides the converted caption for a genuine local price', () => {
    const { queryByTestId } = render(
      <StreamingProductCard
        testID="card"
        stage="prices"
        product={{
          name: 'Sauvage',
          price: { amount: 45, currency: 'BHD', source_method: 'local_bhd' },
        }}
      />
    );
    expect(queryByTestId('card-converted')).toBeNull();
  });

  it('hides the converted caption before the price stage is reached', () => {
    const { queryByTestId } = render(
      <StreamingProductCard
        testID="card"
        stage="specs"
        product={{
          name: 'Sauvage',
          price: { amount: 45, currency: 'BHD', source_method: 'converted_usd' },
        }}
      />
    );
    expect(queryByTestId('card-converted')).toBeNull();
  });
});
