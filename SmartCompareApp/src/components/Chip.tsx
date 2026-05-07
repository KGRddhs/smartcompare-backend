import React from 'react';
import { TouchableOpacity, Text, StyleSheet } from 'react-native';
import { colors, spacing, radii, typography } from '../theme';

interface ChipProps {
  label: string;
  selected?: boolean;
  onPress?: () => void;
  disabled?: boolean;
}

export function Chip({ label, selected = false, onPress, disabled = false }: ChipProps) {
  return (
    <TouchableOpacity
      style={[styles.chip, selected && styles.chipSelected]}
      onPress={onPress}
      disabled={disabled}
      activeOpacity={0.7}
      accessibilityRole="button"
      accessibilityLabel={label}
      accessibilityState={{ selected, disabled }}
    >
      <Text style={[styles.text, selected && styles.textSelected]}>{label}</Text>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  chip: {
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.base,
    borderRadius: radii.chip,
    backgroundColor: colors.bg.secondary,
    borderWidth: 1,
    borderColor: colors.border.light,
    // Phase 5 a11y (WCAG 2.5.5 Target Size). Caption font 13pt + 8pt
    // vertical padding yields ~29pt visual height; minHeight 44 +
    // centered alignment guarantees the touch target hits the floor
    // without changing the chip's visual proportions much (extra
    // height shows as light surrounding bg — chips already pad).
    minHeight: 44,
    justifyContent: 'center',
    alignItems: 'center',
  },
  chipSelected: {
    backgroundColor: colors.accent,
    borderColor: colors.accent,
  },
  text: {
    ...typography.caption,
    fontWeight: '500',
    color: colors.text.primary,
  },
  textSelected: {
    color: '#FFFFFF',
    fontWeight: '600',
  },
});
