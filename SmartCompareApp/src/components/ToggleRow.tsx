// SmartCompareApp/src/components/ToggleRow.tsx
//
// Row-tappable switch with haptic. Replaces inline switch rows on Profile so
// the entire row surface flips the toggle (Bundle A §6.1) — not just the
// thumb. Light haptic on every flip per motion.haptic.chip.

import React, { ReactNode } from 'react';
import { View, Text, Switch, TouchableOpacity, StyleSheet } from 'react-native';
import * as Haptics from 'expo-haptics';
import { colors, spacing, typography } from '../theme';

export interface ToggleRowProps {
  icon?: ReactNode;
  label: string;
  subtitle?: string;
  value: boolean;
  onValueChange: (v: boolean) => void;
  disabled?: boolean;
  accessibilityLabel?: string;
  testID?: string;
}

export default function ToggleRow({
  icon,
  label,
  subtitle,
  value,
  onValueChange,
  disabled,
  accessibilityLabel,
  testID,
}: ToggleRowProps) {
  const fire = (next: boolean) => {
    if (disabled) return;
    try { Haptics.selectionAsync(); } catch {}
    onValueChange(next);
  };

  return (
    <TouchableOpacity
      onPress={() => fire(!value)}
      activeOpacity={0.7}
      disabled={disabled}
      accessibilityRole="switch"
      accessibilityState={{ checked: value, disabled: !!disabled }}
      accessibilityLabel={accessibilityLabel ?? label}
      testID={testID}
    >
      <View style={[styles.row, disabled && styles.disabled]}>
        {icon ? <View style={styles.icon}>{icon}</View> : null}
        <View style={styles.text}>
          <Text style={styles.label}>{label}</Text>
          {subtitle ? <Text style={styles.subtitle}>{subtitle}</Text> : null}
        </View>
        <Switch
          value={value}
          onValueChange={fire}
          disabled={disabled}
          trackColor={{ false: colors.border.medium, true: colors.accent }}
          thumbColor="#FFFFFF"
        />
      </View>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.md,
    minHeight: 56,
  },
  disabled: {
    opacity: 0.5,
  },
  icon: {
    marginEnd: spacing.sm,
  },
  text: {
    flex: 1,
  },
  label: {
    ...typography.body,
    color: colors.text.primary,
  },
  subtitle: {
    ...typography.caption,
    color: colors.text.secondary,
    marginTop: 2,
  },
});
