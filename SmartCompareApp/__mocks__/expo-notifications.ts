// Test mock for expo-notifications.
// The real package ships untransformed ESM (`import { isRunningInExpoGo } from
// 'expo'`) that Jest's CJS runtime can't parse, so any suite importing
// Step17Notifications.tsx / pushTokenService.ts (and thus OnboardingFlow.tsx)
// fails to load. This shim provides the surface the app touches as safe
// no-ops in node. Permission requests resolve "granted" so the happy path is
// exercised by default; tests that need a denial override via jest.mock.

const GRANTED = {
  status: 'granted' as const,
  granted: true,
  canAskAgain: true,
  expires: 'never' as const,
};

export const getPermissionsAsync = async () => GRANTED;
export const requestPermissionsAsync = async () => GRANTED;
export const getExpoPushTokenAsync = async () => ({ data: 'ExponentPushToken[test]' });
export const setNotificationChannelAsync = async () => null;
export const setNotificationHandler = (_handler: unknown) => {};

export const AndroidImportance = {
  DEFAULT: 3,
  HIGH: 4,
  MAX: 5,
  LOW: 2,
  MIN: 1,
} as const;

export default {
  getPermissionsAsync,
  requestPermissionsAsync,
  getExpoPushTokenAsync,
  setNotificationChannelAsync,
  setNotificationHandler,
  AndroidImportance,
};
