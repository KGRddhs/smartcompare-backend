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

// W3-15 — src/services/pushNavigation.ts lazy-requires this module for the
// notification-response listener + the cold-start replay. The names below are
// the real 0.32.17 surface it touches (NotificationsEmitter.js:11 for the
// action-identifier literal; :105-112 / :136-141 for the sync getLast/clear
// pair — both of which throw UnavailabilityError when the native fn is absent).
// Suites that need behaviour override with jest.doMock per test.
export const DEFAULT_ACTION_IDENTIFIER = 'expo.modules.notifications.actions.DEFAULT';
export const addNotificationResponseReceivedListener = (_listener: unknown) => ({
  remove: () => {},
});
export const getLastNotificationResponse = () => null;
export const clearLastNotificationResponse = () => {};

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
  DEFAULT_ACTION_IDENTIFIER,
  addNotificationResponseReceivedListener,
  getLastNotificationResponse,
  clearLastNotificationResponse,
  AndroidImportance,
};
