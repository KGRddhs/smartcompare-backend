/**
 * Global expo-haptics mock.
 *
 * Tests that need to assert specific haptic invocations can override via
 * `jest.mock('expo-haptics', () => ...)` in their own file. This stub
 * exists so unrelated tests don't blow up on the real package's ES
 * module syntax (which pulls expo-modules-core through the import
 * graph).
 */
export const impactAsync = jest.fn(() => Promise.resolve());
export const notificationAsync = jest.fn(() => Promise.resolve());
export const selectionAsync = jest.fn(() => Promise.resolve());

export const ImpactFeedbackStyle = {
  Light: 'Light',
  Medium: 'Medium',
  Heavy: 'Heavy',
  Rigid: 'Rigid',
  Soft: 'Soft',
} as const;

export const NotificationFeedbackType = {
  Success: 'Success',
  Warning: 'Warning',
  Error: 'Error',
} as const;
