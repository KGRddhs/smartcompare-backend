/**
 * AppleSignInButton — S69 U6 R1 (audit LL-10, ruling R-A).
 *
 * App Store Review guideline 4.8 + Apple's Human Interface Guidelines
 * require the Apple logo on a Sign in with Apple control, drawn by the
 * system. This wraps the SDK's native `AppleAuthenticationButton` — never a
 * hand-drawn look-alike — with the two things the native view lacks:
 *
 *   - no `disabled` prop: while ANY sign-in is in flight the press is
 *     swallowed here (`disabled`), and the screen's handler guards too;
 *   - no loading state: while the Apple sign-in itself runs, a same-size
 *     black placeholder with a spinner replaces the button.
 *
 * Styling rules from the SDK docs: never set backgroundColor / borderRadius
 * through `style` (use `buttonStyle` / `cornerRadius`), and always give it a
 * height and width or it renders nothing. The caller decides visibility
 * (`Platform.OS === 'ios'` + `isAppleSignInAvailable()`); on Android the
 * SDK's native view does not exist.
 */

import React from 'react';
import { View, ActivityIndicator, StyleSheet } from 'react-native';
import * as AppleAuthentication from 'expo-apple-authentication';
import { radii } from '../theme';

export const APPLE_BUTTON_HEIGHT = 48;

interface Props {
  /** 'continue' on Login ("Continue with Apple"), 'signUp' on Register. */
  variant: 'continue' | 'signUp';
  onPress: () => void;
  /** The Apple sign-in itself is running — show the placeholder spinner. */
  loading?: boolean;
  /** Another sign-in (or the form) is running — swallow presses, dim. */
  disabled?: boolean;
  testID?: string;
}

export function AppleSignInButton({ variant, onPress, loading, disabled, testID }: Props) {
  if (loading) {
    return (
      <View
        testID={testID ? `${testID}-loading` : undefined}
        style={[styles.button, styles.placeholder]}
        accessibilityRole="progressbar"
        accessibilityState={{ busy: true }}
      >
        <ActivityIndicator size="small" color="#FFFFFF" />
      </View>
    );
  }
  return (
    <AppleAuthentication.AppleAuthenticationButton
      testID={testID}
      buttonType={
        variant === 'signUp'
          ? AppleAuthentication.AppleAuthenticationButtonType.SIGN_UP
          : AppleAuthentication.AppleAuthenticationButtonType.CONTINUE
      }
      buttonStyle={AppleAuthentication.AppleAuthenticationButtonStyle.BLACK}
      cornerRadius={radii.button}
      style={[styles.button, disabled ? styles.dimmed : null]}
      accessibilityState={{ disabled: !!disabled }}
      onPress={() => {
        if (disabled) return;
        onPress();
      }}
    />
  );
}

const styles = StyleSheet.create({
  button: {
    width: '100%',
    height: APPLE_BUTTON_HEIGHT,
  },
  placeholder: {
    borderRadius: radii.button,
    backgroundColor: '#000000',
    alignItems: 'center',
    justifyContent: 'center',
  },
  dimmed: {
    opacity: 0.5,
  },
});
