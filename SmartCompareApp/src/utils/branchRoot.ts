/**
 * branchRoot — leave the referral flow for a route the root navigator
 * ACTUALLY has mounted.
 *
 * App.tsx's root navigator mounts one of three route-name sets (unauth ->
 * `Auth`, needs-preferences -> `Onboarding`, authed -> `Main`), plus the two
 * hoisted referral screens. A `reset` to a name outside the mounted set is
 * dropped by the router (`null` = not handled) and, in a release build,
 * silently — so the target is resolved at press time from the navigator's
 * own `getState().routeNames`, never hard-coded and never read from a second
 * source of truth such as the stored auth token.
 */
import type { NavigationProp } from '@react-navigation/native';
import type { RootStackParamList } from '../types';

export type BranchRoot = 'Main' | 'Onboarding' | 'Auth';

type RootNav = NavigationProp<RootStackParamList>;

/** The root screen of whichever branch App.tsx's root navigator has mounted. */
export function resolveBranchRoot(routeNames: readonly string[]): BranchRoot {
  if (routeNames.includes('Main')) return 'Main';
  if (routeNames.includes('Onboarding')) return 'Onboarding';
  return 'Auth';
}

/** Leave the referral flow for the mounted branch's root. Never dispatches a route the navigator lacks. */
export function exitToBranchRoot(navigation: Pick<RootNav, 'getState' | 'reset'>): void {
  navigation.reset({
    index: 0,
    routes: [{ name: resolveBranchRoot(navigation.getState().routeNames) }],
  });
}

/** Back if there is anything beneath us (in-app entry); otherwise exit (cold-start deep link). */
export function backOrExit(
  navigation: Pick<RootNav, 'getState' | 'reset' | 'canGoBack' | 'goBack'>,
): void {
  if (navigation.canGoBack()) navigation.goBack();
  else exitToBranchRoot(navigation);
}
