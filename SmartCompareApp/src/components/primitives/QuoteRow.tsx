/**
 * QuoteRow — Bundle E S0.3 primitive.
 *
 * Glass-blur testimonial card used as a trio on Step01Welcome. Source of
 * truth: docs/claude-design-handoff/ui_kits/mobile/OnboardingWelcomeScreen.jsx
 * QuoteRow function (lines 74–91): rounded 14px card on rgba-white-55%
 * background with a 1px hairline border, an emerald dot at the start, and
 * the quote text following.
 *
 * Added per design-doc patch 75e78f5 — Step01Welcome composes 3 of these
 * rather than a PhoneMockup hero (JSX-wins doctrine).
 *
 * Contract: __tests__/primitives/QuoteRow.test.tsx
 *   - testID="quote-row-dot" exposes the emerald dot
 *   - testID="quote-row-author" only rendered when author prop provided
 */
import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { colors, spacing } from '../../theme';

interface Props {
  quote: string;
  author?: string;
  testID?: string;
}

export function QuoteRow({ quote, author, testID }: Props) {
  return (
    <View style={styles.card} testID={testID}>
      <View style={styles.dot} testID="quote-row-dot" />
      <View style={styles.textCol}>
        <Text style={styles.quote}>{quote}</Text>
        {author ? (
          <Text style={styles.author} testID="quote-row-author">
            {author}
          </Text>
        ) : null}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    paddingVertical: 10,
    paddingHorizontal: 14,
    borderRadius: 14,
    backgroundColor: 'rgba(255,255,255,0.55)',
    borderWidth: 1,
    borderColor: colors.border.light,
  },
  dot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: colors.accent,
    flexShrink: 0,
  },
  textCol: {
    flex: 1,
    minWidth: 0,
  },
  quote: {
    fontSize: 13,
    fontWeight: '500',
    lineHeight: 13 * 1.4,
    color: colors.text.primary,
  },
  author: {
    fontSize: 11,
    fontWeight: '400',
    lineHeight: 11 * 1.4,
    color: colors.text.secondary,
    marginTop: spacing.xs,
  },
});
