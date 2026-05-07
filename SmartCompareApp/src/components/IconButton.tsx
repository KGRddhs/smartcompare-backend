import React from 'react';
import { TouchableOpacity, StyleSheet, ViewStyle } from 'react-native';
import { colors, spacing } from '../theme';
import { rtlFlip } from '../utils/rtl';

interface IconButtonProps {
  icon: React.ReactNode;
  onPress: () => void;
  directional?: boolean; // true = flip in RTL (arrows, chevrons)
  style?: ViewStyle;
  /** Required for screen readers since the icon glyph carries no text. */
  accessibilityLabel: string;
}

export function IconButton({
  icon,
  onPress,
  directional = false,
  style,
  accessibilityLabel,
}: IconButtonProps) {
  return (
    <TouchableOpacity
      style={[styles.button, directional && rtlFlip(), style]}
      onPress={onPress}
      activeOpacity={0.7}
      accessibilityRole="button"
      accessibilityLabel={accessibilityLabel}
      hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
    >
      {icon}
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  button: {
    // Touch target ≥44pt per WCAG 2.5.5 — base padding+icon=24+8*2=40,
    // hitSlop top adds another 16pt extending the touchable area to 56pt.
    padding: spacing.sm,
    minWidth: 44,
    minHeight: 44,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 999,
  },
});
