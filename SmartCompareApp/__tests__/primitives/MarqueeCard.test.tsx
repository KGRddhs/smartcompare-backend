/**
 * Primitive contract — MarqueeCard.
 *
 * Contract (plan S0.3 + design doc HistoryScreen + ProfileScreen):
 *   - Horizontal-scroll card container used in HistoryScreen HeroStats and
 *     ProfileScreen RecentDecisions
 *   - Renders an array of items as children with horizontal scroll
 *   - showsHorizontalScrollIndicator should be false (clean look)
 */
import React from 'react';
import { render } from '@testing-library/react-native';
import { Text } from 'react-native';
import { MarqueeCard } from '../../src/components/primitives/MarqueeCard';

describe('MarqueeCard primitive', () => {
  const items = [
    { key: 'a', a: 'Apple', b: 'Samsung', ago: '2d', category: 'Phones' },
    { key: 'b', a: 'iPhone 15', b: 'Pixel 8', ago: '5d', category: 'Phones' },
    { key: 'c', a: 'AirPods Pro', b: 'Galaxy Buds', ago: '1w', category: 'Audio' },
  ];

  it('renders all items as children', () => {
    const { getByText } = render(
      <MarqueeCard
        items={items}
        renderItem={(it) => <Text key={it.key}>{`${it.a} vs ${it.b}`}</Text>}
      />,
    );
    expect(getByText('Apple vs Samsung')).toBeTruthy();
    expect(getByText('iPhone 15 vs Pixel 8')).toBeTruthy();
    expect(getByText('AirPods Pro vs Galaxy Buds')).toBeTruthy();
  });

  it('underlying ScrollView is horizontal with indicator hidden', () => {
    const { getByTestId } = render(
      <MarqueeCard
        items={items}
        renderItem={(it) => <Text key={it.key}>{it.a}</Text>}
        testID="marquee"
      />,
    );
    const scroll = getByTestId('marquee');
    expect(scroll.props.horizontal).toBe(true);
    expect(scroll.props.showsHorizontalScrollIndicator).toBe(false);
  });

  it('renders nothing-but-still-mounts when items is empty', () => {
    const { queryByText } = render(
      <MarqueeCard
        items={[]}
        renderItem={(it: any) => <Text key={it.key}>{it.a}</Text>}
        testID="marquee"
      />,
    );
    expect(queryByText(/vs/)).toBeNull();
  });
});
