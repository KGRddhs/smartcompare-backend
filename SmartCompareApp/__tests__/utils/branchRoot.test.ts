/**
 * W3-4 — `src/utils/branchRoot.ts`, the pure half.
 *
 * `resolveBranchRoot(routeNames)` answers "which root has the navigator
 * actually mounted?" from the navigator's OWN `getState().routeNames`, and
 * `exitToBranchRoot(navigation)` dispatches a reset onto it. The point of this
 * suite is that the dispatched payload is then handed to the INSTALLED
 * `@react-navigation/routers` (via `__tests__/helpers/routerSandbox.ts`), so a
 * payload the real router would silently drop cannot pass here.
 *
 * Expected roots are LITERALS (FABLE REVIEW RULING 4) — never
 * `resolveBranchRoot(...)` read back into its own assertion.
 *
 * RED today because `src/utils/branchRoot` does not exist yet.
 */

import {
  coldStartState,
  loadInstalledRouters,
  resetOutcome,
  rootRouteNameSets,
} from '../helpers/routerSandbox';
import { resolveBranchRoot, exitToBranchRoot } from '../../src/utils/branchRoot';

const routers = loadInstalledRouters();
const stackRouter = routers.StackRouter({});
const SETS = rootRouteNameSets();

/** Would the installed router HANDLE this reset on this branch? `null` = no. */
function routerOutcome(payload: any, routeNames: readonly string[]): any {
  const state = coldStartState(
    stackRouter,
    'ReferralLanding',
    { share_token: 'abc123', ref: 'QR-ABCDEF' },
    routeNames,
  );
  return resetOutcome(routers, stackRouter, state, payload, routeNames);
}

// [label, routeNames, expected root LITERAL]
const BRANCHES: [string, readonly string[], string][] = [
  ['unauth', SETS.unauth, 'Auth'],
  ['needsPreferences', SETS.needsPreferences, 'Onboarding'],
  ['authed', SETS.authed, 'Main'],
];

describe('resolveBranchRoot', () => {
  it.each(BRANCHES)(
    '%s branch resolves to its own root',
    (_label, routeNames, expectedRoot) => {
      expect(resolveBranchRoot([...routeNames])).toBe(expectedRoot);
    },
  );

  it("UNREACHABLE FALLBACK (no App.tsx branch produces it): an empty set resolves to 'Auth'", () => {
    expect(resolveBranchRoot([])).toBe('Auth');
  });
});

describe('exitToBranchRoot', () => {
  it.each(BRANCHES)(
    '%s branch: dispatches { index: 0, routes: [{ name: <root> }] } the router accepts',
    (_label, routeNames, expectedRoot) => {
      // RULING 1 — every test-side navigation stub is `any`, never typed
      // structurally against `NavigationProp`.
      const reset = jest.fn();
      const navigation: any = {
        getState: () => ({ routeNames: [...routeNames] }),
        reset,
      };

      exitToBranchRoot(navigation);

      expect(reset).toHaveBeenCalledTimes(1);
      const payload = reset.mock.calls[0][0];

      // Screen contract: single route, index 0. NOTE the router itself does
      // NOT require `index` on a reset (`BaseRouter` checks membership only),
      // so this is asserted as the screen contract, not as a router demand.
      expect(payload.index).toBe(0);
      expect(payload.routes).toHaveLength(1);
      expect(payload.routes[0].name).toBe(expectedRoot);

      // The load-bearing line: the INSTALLED router handles it.
      expect(routerOutcome(payload, routeNames)).not.toBeNull();
    },
  );
});
