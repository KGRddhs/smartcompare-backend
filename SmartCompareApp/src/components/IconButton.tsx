import React from 'react';
import { TouchableOpacity, StyleSheet, ViewStyle } from 'react-native';
import { colors, spacing } from '../theme';
import { rtlFlip } from '../utils/rtl';

interface IconButtonProps {
  icon: React.ReactNode;
  onPress: () => void;
  directional?: boolean; // true = flip in RTL (arrows, chevrons)
  style?: ViewStyle;
}

export function IconButton({
  icon,
  onPress,
  directional = false,
  style,
}: IconButtonProps) {
  return (
    <TouchableOpacity
      style={[styles.button, directional && rtlFlip(), style]}
      onPress={onPress}
      activeOpacity={0.7}
    >
      {icon}
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  button: {
    padding: spacing.sm,
    borderRadius: 999,
  },
});
