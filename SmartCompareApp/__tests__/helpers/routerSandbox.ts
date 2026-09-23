/**
 * W3-4 router sandbox — lets a jest test run the INSTALLED React Navigation
 * StackRouter instead of a hand-written mock of it.
 *
 * NOT a test file (jest's `testMatch` only collects `*.test.ts(x)`).
 *
 * WHY THIS EXISTS. `@react-navigation/*` ship `"main": "./lib/module/index.js"`
 * (ESM), their `exports` map exposes only `.` (no `/src` subpath), and this
 * repo's `jest.config.js` `transformIgnorePatterns` does not allow-list
 * `@react-navigation` (ts-jest would not transform `.js` even if it did). So a
 * plain `require('@react-navigation/routers')` fails with
 * `SyntaxError: Cannot use import statement outside a module` — which is why
 * every existing suite `jest.mock`s `@react-navigation/native` with a factory
 * and no test in the repo exercises the real router. A test that only checks
 * `navigation.reset` was CALLED cannot tell a handled reset from one the
 * navigator silently dropped; this helper lowers the installed package to CJS
 * and evaluates it in-process so the test can ask the router itself.
 *
 * DEPENDENCY NOTE (for the next dependency audit): relies on the TRANSITIVE
 * `@babel/core` 7.29.0 (peer of `babel-jest`, a dep of the declared `jest`) and
 * `@babel/plugin-transform-modules-commonjs` 7.28.6 (dep of the declared
 * `babel-preset-expo`), both pinned in `package-lock.json` so CI's `npm ci`
 * installs them exactly as here — the same reliance `w312BootSandbox.ts` has.
 * `@react-navigation/routers` is a leaf (its only dependency is `nanoid`), so
 * the loader never has to lower `@react-navigation/core`.
 */
import * as fs from 'fs';
import * as path from 'path';

// eslint-disable-next-line @typescript-eslint/no-require-imports
const babel = require('@babel/core');
// NOTE: `require.resolve(...)` is NOT flagged by @typescript-eslint/no-require-imports
// (only a bare `require()` call is), so a disable directive here would itself
// be reported as an unused directive. Measured with this repo's eslint.config.js.
const COMMONJS_PLUGIN: string = require.resolve('@babel/plugin-transform-modules-commonjs');

export const APP_ROOT = path.resolve(__dirname, '../..');
export const APP_FILE = path.join(APP_ROOT, 'App.tsx');
export const ROUTERS_DIR = path.join(
  APP_ROOT,
  'node_modules',
  '@react-navigation',
  'routers',
  'lib',
  'module',
);

const cache = new Map<string, { exports: any }>();

/**
 * Lower one ESM file from `lib/module` to CommonJS with babel and evaluate it.
 * Relative specifiers (`./BaseRouter.js`) recurse through this loader; bare
 * specifiers (`nanoid/non-secure`) go to the real `require`.
 */
function loadEsm(file: string): any {
  const abs = path.resolve(file);
  const hit = cache.get(abs);
  if (hit) return hit.exports;
  const code = fs.readFileSync(abs, 'utf8');
  const out = babel.transformSync(code, {
    filename: abs,
    configFile: false,
    babelrc: false,
    plugins: [COMMONJS_PLUGIN],
  });
  const mod = { exports: {} as any };
  cache.set(abs, mod);
  const localRequire = (spec: string): any => {
    if (spec.startsWith('.')) return loadEsm(path.join(path.dirname(abs), spec));
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    return require(spec);
  };
  new Function('require', 'module', 'exports', '__filename', '__dirname', out.code)(
    localRequire,
    mod,
    mod.exports,
    abs,
    path.dirname(abs),
  );
  return mod.exports;
}

export interface InstalledRouters {
  /** `StackRouter(options)` factory from the installed `@react-navigation/routers`. */
  StackRouter: (options: Record<string, unknown>) => any;
  /** `CommonActions.reset` / `.goBack` / … from the same package. */
  CommonActions: { reset: (state: any) => any; goBack: () => any; [k: string]: any };
  /** The installed package version, so a report can name what was measured. */
  version: string;
}

/** Load the INSTALLED `@react-navigation/routers` (lowered to CJS in-process). */
export function loadInstalledRouters(): InstalledRouters {
  const { StackRouter, CommonActions } = loadEsm(path.join(ROUTERS_DIR, 'index.js'));
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const version: string = require(path.join(APP_ROOT, 'node_modules', '@react-navigation', 'routers', 'package.json')).version;
  return { StackRouter, CommonActions, version };
}

/** The `RouterConfigOptions` shape every router method takes. */
export function routerOptions(routeNames: readonly string[]) {
  return { routeNames: [...routeNames], routeParamList: {}, routeGetIdList: {} };
}

/**
 * The ONE-route stack a cold-start deep link produces: `getStateFromPath` on
 * App.tsx's linking config yields `{ routes: [{ name: 'ReferralLanding', params }] }`
 * (no `initialRouteName`), which the navigator rehydrates against the mounted
 * route names. Nothing is beneath the screen, so `goBack` has nowhere to go.
 */
export function coldStartState(
  router: any,
  screen: 'ReferralLanding' | 'InviteeQuiz',
  params: Record<string, unknown>,
  routeNames: readonly string[],
): any {
  return router.getRehydratedState({ routes: [{ name: screen, params }] }, routerOptions(routeNames));
}

/**
 * Ask the installed router whether it would HANDLE a `reset` with this payload
 * on this state. `null` is React Navigation's "not handled" — the container
 * then calls `onUnhandledAction`, which in a release build returns silently.
 */
export function resetOutcome(
  routers: InstalledRouters,
  router: any,
  state: any,
  payload: any,
  routeNames: readonly string[],
): any {
  return router.getStateForAction(state, routers.CommonActions.reset(payload), routerOptions(routeNames));
}

export type RootRouteNameSets = {
  unauth: string[];
  needsPreferences: string[];
  authed: string[];
};

/**
 * Static extraction of the route names App.tsx's root navigator mounts in each
 * branch of its three-way ternary, plus the hoisted (branch-independent) tail.
 * Same `<Stack.Screen … name=…>` regex as `App.distinctRouteNames.test.ts`.
 *
 * Fails LOUDLY on marker drift: an earlier probe keyed the branch split on the
 * first `)}` and silently leaked four authed-only names into the other two
 * sets. Every marker is asserted present and in order before slicing, and the
 * extracted sets are asserted against the shape App.tsx has today.
 */
export function rootRouteNameSets(): RootRouteNameSets {
  const src = fs.readFileSync(APP_FILE, 'utf8');
  const navStart = src.indexOf('<Stack.Navigator');
  const navEnd = src.indexOf('</Stack.Navigator>');
  if (navStart === -1) throw new Error('rootRouteNameSets: marker "<Stack.Navigator" not found in App.tsx');
  if (navEnd === -1) throw new Error('rootRouteNameSets: marker "</Stack.Navigator>" not found in App.tsx');
  const nav = src.slice(navStart, navEnd);

  const markers: [string, number][] = [
    ['{!isAuthenticated ? (', nav.indexOf('{!isAuthenticated ? (')],
    [') : needsPreferences ? (', nav.indexOf(') : needsPreferences ? (')],
  ];
  const iPrefs = markers[1][1];
  markers.push([') : ( (after needsPreferences)', iPrefs === -1 ? -1 : nav.indexOf(') : (', iPrefs)]);
  markers.push(['</> (last fragment closer)', nav.lastIndexOf('</>')]);

  for (const [label, idx] of markers) {
    if (idx === -1) throw new Error(`rootRouteNameSets: marker ${JSON.stringify(label)} not found inside <Stack.Navigator>`);
  }
  for (let i = 1; i < markers.length; i += 1) {
    if (!(markers[i][1] > markers[i - 1][1])) {
      throw new Error(
        `rootRouteNameSets: marker ${JSON.stringify(markers[i][0])} (index ${markers[i][1]}) does not follow ` +
          `${JSON.stringify(markers[i - 1][0])} (index ${markers[i - 1][1]})`,
      );
    }
  }
  const [iUnauth, , iAuthed, iClose] = markers.map(([, idx]) => idx);

  const names = (s: string): string[] => {
    const out: string[] = [];
    const re = /<Stack\.Screen[\s\S]{0,200}?name=["']([A-Za-z][A-Za-z0-9]*)["']/g;
    let m: RegExpExecArray | null;
    while ((m = re.exec(s)) !== null) out.push(m[1]);
    return out;
  };
  const hoisted = names(nav.slice(iClose));
  const sets: RootRouteNameSets = {
    unauth: [...names(nav.slice(iUnauth, iPrefs)), ...hoisted],
    needsPreferences: [...names(nav.slice(iPrefs, iAuthed)), ...hoisted],
    authed: [...names(nav.slice(iAuthed, iClose)), ...hoisted],
  };

  // Sanity: the shape App.tsx has today. A drift here means the extraction, not
  // the screens, needs attention — fail with the sets in the message.
  const expectUnauth = ['Auth', 'ReferralLanding', 'InviteeQuiz'];
  const expectPrefs = ['Onboarding', 'ReferralLanding', 'InviteeQuiz'];
  const same = (a: string[], b: string[]) => a.length === b.length && a.every((x, i) => x === b[i]);
  if (!same(sets.unauth, expectUnauth) || !same(sets.needsPreferences, expectPrefs) || !sets.authed.includes('Main')) {
    throw new Error(`rootRouteNameSets: App.tsx branch shape drifted; extracted ${JSON.stringify(sets)}`);
  }
  return sets;
}
