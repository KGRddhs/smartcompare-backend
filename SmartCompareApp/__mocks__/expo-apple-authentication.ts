/**
 * Test mock for expo-apple-authentication (S69 U6 R1).
 *
 * The real package ships untransformed ESM with raw JSX
 * (build/index.js, build/AppleAuthenticationButton.js), so any suite that
 * renders LoginScreen / RegisterScreen — which now import the SDK's native
 * AppleAuthenticationButton — would fail to load without this shim.
 *
 * - AppleAuthenticationButton renders a host element of the same name and
 *   forwards every prop (testID, onPress, buttonType, buttonStyle,
 *   cornerRadius, style), so `fireEvent.press(getByTestId(...))` reaches
 *   the screen's handler exactly as the native view's onButtonPress would.
 * - The enums carry the REAL values (AppleAuthentication.types.d.ts):
 *   SIGN_IN=0, CONTINUE=1, SIGN_UP=2; WHITE=0, WHITE_OUTLINE=1, BLACK=2.
 * - isAvailableAsync resolves false and signInAsync rejects, mirroring an
 *   unsupported platform; suites that exercise the sign-in override these
 *   with their own jest.mock factory.
 */
import React from 'react';

export const AppleAuthenticationButtonType = { SIGN_IN: 0, CONTINUE: 1, SIGN_UP: 2 } as const;
export const AppleAuthenticationButtonStyle = { WHITE: 0, WHITE_OUTLINE: 1, BLACK: 2 } as const;
export const AppleAuthenticationScope = { FULL_NAME: 0, EMAIL: 1 } as const;

export function AppleAuthenticationButton(props: any) {
  return React.createElement('AppleAuthenticationButton', props);
}

export const isAvailableAsync = async (): Promise<boolean> => false;

export const signInAsync = async (): Promise<never> => {
  throw new Error('expo-apple-authentication is not available under jest');
};

export default {
  AppleAuthenticationButton,
  AppleAuthenticationButtonType,
  AppleAuthenticationButtonStyle,
  AppleAuthenticationScope,
  isAvailableAsync,
  signInAsync,
};
