/**
 * OptionRow — Bundle E S0.3 primitive.
 *
 * Cal-AI-Lite option row used across multiple onboarding steps:
 *   - Step08Priorities (icon-circle style, multi-select max 3)
 *   - Step06Age / Step07Gender / Step09Budget / Step10BrandAttitude /
 *     Step11Attribution (icon-circle OR plain depending on category)
 *
 * style='icon-circle' renders a 36px circle to the left of the label.
 * style='plain' is the bare row (no circle). Active state inverts the
 * background to bg.inverse (black-on-select per Cal-AI pattern). selected
 * is also exposed via accessibilityState so screen readers + tests can
 * key off it.
 *
 * Contract: __tests__/primitives/OptionRow.test.tsx
 *   - testID forwarded to the Pressable root
 *   - testID="option-row-icon-circle" only when style='icon-circle'
 *   - icon circle is 36x36
 *   - onToggle called with option.key on press
 *   - accessibilityState.selected mirrors `active`
 */
import React from 'react';
import { View, Text, Pressable, StyleSheet } from 'react-native';
import { colors, spacing, radii } from '../../theme';

interface OptionData {
  key: string;
  label: string;
  icon?: string;
}

interface Props {
  option: OptionData;
  active: boolean;
  onToggle: (key: string) => void;
  style: 'icon-circle' | 'plain';
  testID?: string;
}

const CIRCLE_SIZE = 36;

export function OptionRow({ option, active, onToggle, style, testID }: Props) {
  const handlePress = () => onToggle(option.key);
  return (
    <Pressable
      onPress={handlePress}
      style={[styles.row, active ? styles.rowActive : styles.rowInactive]}
      testID={testID}
      accessibilityRole="button"
      accessibilityState={{ selected: active }}
      accessibilityLabel={option.label}
    >
      {style === 'icon-circle' ? (
        <View
          style={[styles.circle, active ? styles.circleActive : null]}
          testID="option-row-icon-circle"
        />
      ) : null}
      <Text style={[styles.label, active ? styles.labelActive : null]}>{option.label}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.base,
    borderRadius: radii.card,
    borderWidth: 1,
  },
  rowInactive: {
    backgroundColor: colors.bg.primary,
    borderColor: colors.border.light,
  },
  rowActive: {
    backgroundColor: colors.bg.inverse,
    borderColor: colors.bg.inverse,
  },
  circle: {
    width: CIRCLE_SIZE,
    height: CIRCLE_SIZE,
    borderRadius: CIRCLE_SIZE / 2,
    backgroundColor: colors.bg.secondary,
    borderWidth: 1,
    borderColor: colors.border.light,
    flexShrink: 0,
  },
  circleActive: {
    backgroundColor: colors.accentLight,
    borderColor: colors.accent,
  },
  label: {
    flex: 1,
    fontSize: 15,
    fontWeight: '500',
    lineHeight: 15 * 1.4,
    color: colors.text.primary,
  },
  labelActive: {
    color: colors.text.onInverse,
  },
});
