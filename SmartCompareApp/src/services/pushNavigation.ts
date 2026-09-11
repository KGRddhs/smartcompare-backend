/**
 * W3-15 — push notification taps, from the payload's `data.url` to a
 * navigation.
 *
 * WHAT WAS MISSING
 * At base the client registered ZERO notification-response listeners and never
 * called `setNotificationHandler`. React Navigation's own linking integration
 * only watches `Linking` (`useLinking.native.js:13-35`) and a notification
 * response is not a `Linking` URL, so a tap on any Qaren push opened the app
 * wherever it last was and `data.url` was never read. Separately, with no JS
 * handler installed a push that ARRIVES while the app is foregrounded times
 * out after 3 s and is never presented on either platform (Android
 * `SingleNotificationHandlerTask.java:32,116-123`; iOS
 * `SingleNotificationHandlerTask.swift:34-41,53-57`).
 *
 * WHY DISPATCH INSTEAD OF `linking.getInitialURL`
 * A cold-start URL fed through `getInitialURL` becomes the container's INITIAL
 * state, and for a root-level route that is a single-entry root stack with no
 * `Main` beneath it — ResultsScreen's back arrow would be unhandled. Adding
 * `initialRouteName: 'Main'` fixes Results but also prepends `Main` to the
 * live `c/`, `q/` and `r/` referral shapes. Dispatching `NAVIGATE` over the
 * already-initialised stack keeps both correct, and is exactly what
 * `useLinking.native.js:127-146` does for a warm `Linking` URL.
 *
 * `expo-notifications` is lazy-required, the same way `pushTokenService.ts:50-56`
 * does it: a missing native module must degrade to "no push navigation", never
 * to a boot crash.
 */
import { getActionFromState } from '@react-navigation/native';

import { linking, navigationRef } from '../navigation/linking';

type NotificationsModule = typeof import('expo-notifications');

/** The literal at `expo-notifications/build/NotificationsEmitter.js:11`. */
const DEFAULT_ACTION_IDENTIFIER_FALLBACK = 'expo.modules.notifications.actions.DEFAULT';

/** `undefined` = not tried yet, `null` = tried and unavailable. */
let notificationsModule: NotificationsModule | null | undefined;

function loadNotifications(): NotificationsModule | null {
  if (notificationsModule !== undefined) return notificationsModule;
  try {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    notificationsModule = require('expo-notifications') as NotificationsModule;
  } catch (err) {
    if (__DEV__) console.warn('[pushNav] expo-notifications module unavailable', err);
    notificationsModule = null;
  }
  return notificationsModule;
}

type ResolvedTap = {
  state: ReturnType<NonNullable<typeof linking.getStateFromPath>>;
  action: ReturnType<typeof getActionFromState>;
};

type PendingTap = ResolvedTap & { identifier?: string };

/** A tap that arrived before the container was ready, drained by onNavigationReady(). */
let pending: PendingTap | undefined;

/**
 * The last notification identifier we actually navigated for.
 *
 * The native emitters deliver ONE tap through BOTH channels: iOS
 * `EmitterModule.swift:40-46` sets `lastResponse` AND sends the JS event in the
 * same `didReceive`, and `NotificationsEmitter.kt:70-83` does the same. On a
 * cold start the listener installs during the splash, so the response is parked
 * here AND still sits in the native slot when `onNavigationReady()` reads it.
 * Without this slot that is two dispatches for one tap.
 */
let lastHandledIdentifier: string | undefined;

let listenerSubscription: { remove: () => void } | undefined;
let handlerInstalled = false;

/**
 * Strip a matching `linking.prefixes` entry off a push `data.url`.
 *
 * `@react-navigation/native`'s own `extractPathFromURL` is NOT importable —
 * the package's "exports" map exposes only "." and "./package.json" — so the
 * prefix match is done here. Scheme comparison is case-insensitive, as
 * `extractPathFromURL` is. Returns `undefined` for anything that does not
 * belong to this app, which is what makes a foreign-origin `data.url`
 * un-navigable.
 */
export function pathFromPushUrl(
  url: unknown,
  prefixes: readonly string[] = linking.prefixes
): string | undefined {
  if (typeof url !== 'string') return undefined;
  const lowered = url.toLowerCase();
  for (const prefix of prefixes) {
    if (lowered.startsWith(prefix.toLowerCase())) {
      return url.slice(prefix.length).replace(/^\/+/, '');
    }
  }
  return undefined;
}

/**
 * url -> { state, action }, through the SAME two functions
 * `useLinking.native.js:85-92` and `:127-146` use. `undefined` when the URL is
 * foreign or names no registered route.
 */
export function actionFromPushUrl(url: unknown): ResolvedTap | undefined {
  const path = pathFromPushUrl(url);
  if (path === undefined) return undefined;
  try {
    const state = linking.getStateFromPath!(path, linking.config as any);
    if (!state) return undefined;
    return { state, action: getActionFromState(state, linking.config as any) };
  } catch {
    return undefined;
  }
}

function dispatchTap(tap: PendingTap): void {
  lastHandledIdentifier = tap.identifier;
  if (tap.action !== undefined) {
    navigationRef.dispatch(tap.action);
  } else {
    // Mirrors useLinking.native.js:138-145. getActionFromState yields a
    // NAVIGATE for all of this unit's URLs, so this branch exists only so the
    // two code paths stay the same shape.
    navigationRef.resetRoot(tap.state as any);
  }
}

/**
 * One notification response -> at most one navigation. Never throws.
 *
 * Returns true when the tap was navigated (or parked for `onNavigationReady`),
 * false when a guard rejected it.
 */
export function handlePushResponse(response: unknown): boolean {
  if (!response || typeof response !== 'object') return false;
  const r = response as {
    actionIdentifier?: unknown;
    notification?: { request?: { identifier?: unknown; content?: { data?: unknown } } };
  };

  const request = r.notification?.request;
  const identifier = typeof request?.identifier === 'string' ? request.identifier : undefined;
  // Double-delivery dedupe — see lastHandledIdentifier above.
  if (identifier !== undefined && identifier === lastHandledIdentifier) return false;

  // A plain tap only. An action-button response carries that action's own
  // identifier (Notifications.types.d.ts:589) and must not navigate.
  const defaultAction =
    loadNotifications()?.DEFAULT_ACTION_IDENTIFIER ?? DEFAULT_ACTION_IDENTIFIER_FALLBACK;
  if (r.actionIdentifier !== defaultAction) return false;

  // NotificationContent.data is `{ [key: string]: unknown }`
  // (Notifications.types.d.ts:390-392), so this guard is required by tsc as
  // well as by safety.
  const data = request?.content?.data as Record<string, unknown> | undefined;
  if (typeof data?.url !== 'string') return false;

  const resolved = actionFromPushUrl(data.url);
  if (!resolved) return false;

  const tap: PendingTap = { ...resolved, identifier };
  if (navigationRef.isReady()) {
    dispatchTap(tap);
    return true;
  }
  // The container is not mounted yet (splash). Park it; onNavigationReady
  // drains it. Dropping it here is what loses a cold-start tap.
  pending = tap;
  return true;
}

/**
 * Arm the foreground handler and the response listener. Idempotent.
 * Returns an unsubscribe; returns a no-op when the native module is missing.
 */
export function installPushTapListeners(): () => void {
  const Notifications = loadNotifications();
  if (!Notifications) return () => {};

  try {
    if (!handlerInstalled) {
      Notifications.setNotificationHandler({
        // No `shouldShowAlert` — it is deprecated on 0.32.17 and makes
        // NotificationsHandler.js:65-66 warn.
        handleNotification: async () => ({
          shouldShowBanner: true,
          shouldShowList: true,
          shouldPlaySound: false,
          shouldSetBadge: false,
        }),
      });
      handlerInstalled = true;
    }
    if (!listenerSubscription) {
      // Concise body on purpose: the listener's declared return type is void,
      // but handlePushResponse's boolean is what the suite asserts when it
      // invokes the captured callback directly.
      listenerSubscription = Notifications.addNotificationResponseReceivedListener((response) =>
        handlePushResponse(response)
      );
    }
  } catch (err) {
    if (__DEV__) console.warn('[pushNav] could not install push tap listeners', err);
    return () => {};
  }

  return () => {
    try {
      listenerSubscription?.remove();
    } catch {
      /* a removed subscription must never break an effect cleanup */
    }
    // Resetting the slot is load-bearing: a React StrictMode cleanup ->
    // re-run of the effect would otherwise leave the app with NO listener.
    listenerSubscription = undefined;
  };
}

/**
 * `<NavigationContainer onReady={...}>`. Drains a parked tap, then replays the
 * cold-start response the OS stored before JS was running.
 */
export function onNavigationReady(): void {
  if (pending && navigationRef.isReady()) {
    const parked = pending;
    pending = undefined;
    dispatchTap(parked);
  }

  const Notifications = loadNotifications();
  if (!Notifications) return;

  let response: unknown;
  try {
    // Sync on 0.32.17 (the `…Async` variant is deprecated and just returns
    // this). Throws UnavailabilityError when the native fn is absent
    // (NotificationsEmitter.js:105-112).
    response = Notifications.getLastNotificationResponse();
  } catch (err) {
    if (__DEV__) console.warn('[pushNav] getLastNotificationResponse unavailable', err);
    return;
  }
  if (response == null) return;

  try {
    handlePushResponse(response);
  } finally {
    try {
      // Clear whether or not it was a duplicate, so a later container remount
      // cannot replay it. This throws the SAME UnavailabilityError
      // (NotificationsEmitter.js:136-141), hence its own try/catch.
      Notifications.clearLastNotificationResponse();
    } catch {
      /* nothing to do — the slot simply stays set on this platform */
    }
  }
}
