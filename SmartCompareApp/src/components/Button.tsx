import React from 'react';
import {
  TouchableOpacity,
  Text,
  StyleSheet,
  ActivityIndicator,
  ViewStyle,
  TextStyle,
} from 'react-native';
import { colors, spacing, radii, typography } from '../theme';

/**
 * Button variants.
 *
 * - primary    — black bg + white text. The default CTA across the app.
 * - signature  — emerald bg + white text. Reserved for the ONE-TIME
 *                "Reveal my verdict" invitee CTA per design Section 4e.
 *                Do not reuse for generic CTAs; the emerald loses meaning.
 * - secondary  — white bg + black border + black text. Used for
 *                "Already have an account?" / "Skip" / similar.
 * - destructive — destructive border. Kept for delete-confirmation flows.
 */
type ButtonVariant = 'primary' | 'signature' | 'secondary' | 'destructive';

interface ButtonProps {
  title: string;
  onPress: () => void;
  variant?: ButtonVariant;
  disabled?: boolean;
  loading?: boolean;
  style?: ViewStyle;
  testID?: string;
  accessibilityLabel?: string;
}

export function Button({
  title,
  onPress,
  variant = 'primary',
  disabled = false,
  loading = false,
  style,
  testID,
  accessibilityLabel,
}: ButtonProps) {
  const buttonStyle = [
    styles.base,
    styles[variant],
    disabled && styles.disabled,
    style,
  ];

  const textStyle = [
    styles.text,
    variant === 'secondary' && styles.textSecondary,
    variant === 'destructive' && styles.textDestructive,
  ] as TextStyle[];

  return (
    <TouchableOpacity
      style={buttonStyle}
      onPress={onPress}
      disabled={disabled || loading}
      activeOpacity={0.7}
      testID={testID}
      accessibilityLabel={accessibilityLabel ?? title}
      accessibilityRole="button"
    >
      {loading ? (
        <ActivityIndicator
          size="small"
          color={variant === 'secondary' ? colors.text.primary : '#FFFFFF'}
        />
      ) : (
        <Text style={textStyle}>{title}</Text>
      )}
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  base: {
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.xl,
    borderRadius: radii.button,
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: 48,
  },
  primary: {
    backgroundColor: colors.cta.primary,
  },
  signature: {
    backgroundColor: colors.accent,
  },
  secondary: {
    backgroundColor: colors.bg.primary,
    borderWidth: 1,
    borderColor: colors.text.primary,
  },
  destructive: {
    backgroundColor: 'transparent',
    borderWidth: 1,
    borderColor: colors.destructive,
  },
  disabled: {
    opacity: 0.5,
  },
  text: {
    ...typography.body,
    fontWeight: '600',
    color: colors.cta.onPrimary,
  },
  textSecondary: {
    color: colors.text.primary,
  },
  textDestructive: {
    color: colors.destructive,
  },
});
