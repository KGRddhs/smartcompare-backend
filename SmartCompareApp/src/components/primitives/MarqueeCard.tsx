/**
 * MarqueeCard — Bundle E S0.3 primitive.
 *
 * Horizontal-scroll container used on HistoryScreen HeroStats and
 * ProfileScreen RecentDecisions. Items are rendered via a renderItem
 * callback so callers can vary the per-card layout (mini VS pair vs.
 * stats tile etc.) while keeping the same scroll behavior.
 *
 * Contract: __tests__/primitives/MarqueeCard.test.tsx
 *   - renders every item via renderItem
 *   - underlying ScrollView is horizontal w/ showsHorizontalScrollIndicator=false
 *   - testID is forwarded to the ScrollView root
 *   - empty items array renders without crashing
 */
import React from 'react';
import { ScrollView, StyleSheet, View } from 'react-native';
import { spacing } from '../../theme';

interface Props<T> {
  items: T[];
  renderItem: (item: T, index: number) => React.ReactNode;
  testID?: string;
}

export function MarqueeCard<T>({ items, renderItem, testID }: Props<T>) {
  return (
    <ScrollView
      horizontal
      showsHorizontalScrollIndicator={false}
      contentContainerStyle={styles.content}
      testID={testID}
    >
      {items.map((item, index) => (
        <View key={(item as any).key ?? index} style={styles.item}>
          {renderItem(item, index)}
        </View>
      ))}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  content: {
    paddingHorizontal: spacing.base,
    gap: spacing.md,
  },
  item: {
    marginRight: spacing.md,
  },
});
