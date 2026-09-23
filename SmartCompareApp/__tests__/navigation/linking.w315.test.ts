/**
 * W3-15 — the linking config, measured through the REAL
 * `@react-navigation/core` `getStateFromPath` (installed core 7.17.4, reached
 * via `@react-navigation/native` 7.2.4).
 *
 * WHY THIS SUITE EXISTS
 * The backend emits four `qaren://` deep links in push payloads
 * (`app/services/push_service.py:80`, `scripts/cron_expire_bonuses.py:125`,
 * `app/services/reengagement_service.py:326/345/366`). At base `ed75dc70` the
 * client's linking config — a non-exported `const` inside `App()` at
 * `App.tsx:350-379` — registers only `c/:share_token`, `q/:share_token`,
 * `r/:code` and the `redeem?code=` rewrite, so all four backend URLs resolve
 * to `undefined`: a tap lands nowhere. W3-15 hoists that config verbatim into
 * `src/navigation/linking.ts` and adds the three missing targets.
 *
 * HOW IT MEASURES
 * The same two steps `@react-navigation/native`'s own
 * `useLinking.native.js:85-92` performs on a warm `Linking` URL:
 *   1. `extractPathFromURL(prefixes, url)`  — the package's real helper,
 *      reached by absolute path because the package's `exports` map exposes
 *      only "." and "./package.json" (so `@react-navigation/native/lib/...`
 *      is not importable by specifier).
 *   2. `linking.getStateFromPath(path, linking.config)` — the config's OWN
 *      override (the `redeem` rewrite), which delegates to the real
 *      `getStateFromPath`.
 * `jest.config.js` allow-lists `@react-navigation` and adds one narrow
 * `babel-jest` transform key for its `.js`, which is what lets the real
 * (ESM-only) package load under this runner at all.
 *
 * L1-L4 are the RED rows. L5-L9 are PINS that already describe today's
 * behaviour and must not move (they go green the moment the hoist lands).
 * L10 is a KNOWN-LIMIT pin: it records a documented limitation so that a
 * later change to it is visible, not a behaviour this unit endorses.
 */
import * as path from 'path';
import type { LinkingOptions } from '@react-navigation/native';

import { linking } from '../../src/navigation/linking';

// The package's "exports" map exposes only "." and "./package.json", so the
// real extractPathFromURL — what useLinking.native.js:85 calls — is only
// reachable by absolute path. Same technique the unit's probes used.
// eslint-disable-next-line @typescript-eslint/no-require-imports
const { extractPathFromURL } = require(path.resolve(
  __dirname,
  '../../node_modules/@react-navigation/native/lib/module/extractPathFromURL.js'
));

type AnyState = { routes: Record<string, any>[]; index?: number } | undefined;

/** url -> navigation state, through the real two-step pipeline. */
function resolve(url: string): AnyState {
  const cfg = linking as LinkingOptions<any>;
  const p = extractPathFromURL(cfg.prefixes, url);
  if (p === undefined) return undefined;
  return cfg.getStateFromPath!(p, cfg.config as any) as AnyState;
}

describe('W3-15 L1-L4 — backend push deep links name a route', () => {
  it('L1: qaren://profile/referrals -> Main > ProfileTab', () => {
    // push_service.py:80 (Loop-2 referrer push, LIVE today under
    // ENABLE_REFERRAL_SYSTEM=true) and cron_expire_bonuses.py:125.
    const state = resolve('qaren://profile/referrals');
    expect(state).toBeDefined();
    expect(state!.routes[0].name).toBe('Main');
    expect(state!.routes[0].state.routes[0].name).toBe('ProfileTab');
    expect(JSON.parse(JSON.stringify(state))).toEqual({
      routes: [{ name: 'Main', state: { routes: [{ name: 'ProfileTab', path: 'profile/referrals' }] } }],
    });
  });

  it('L2: qaren://comparison/:id?banner=insight -> Results with both params', () => {
    // reengagement_service.py:326 — deep_link_url f"qaren://comparison/{id}?banner=insight"
    const state = resolve('qaren://comparison/abc-123?banner=insight');
    expect(state).toBeDefined();
    expect(state!.routes[0].name).toBe('Results');
    expect(state!.routes[0].params).toEqual({ comparison_id: 'abc-123', banner: 'insight' });
  });

  it('L3: qaren://comparison/:id?banner=retrospective -> Results with both params', () => {
    // reengagement_service.py:366
    const state = resolve('qaren://comparison/abc-123?banner=retrospective');
    expect(state).toBeDefined();
    expect(state!.routes[0].name).toBe('Results');
    expect(state!.routes[0].params).toEqual({ comparison_id: 'abc-123', banner: 'retrospective' });
  });

  it('L4: qaren://cohort/divergence -> Main > HomeTab', () => {
    // reengagement_service.py:345 — no cohort screen exists and the payload
    // carries no id, so Home is the handled target.
    const state = resolve('qaren://cohort/divergence');
    expect(state).toBeDefined();
    expect(state!.routes[0].name).toBe('Main');
    expect(state!.routes[0].state.routes[0].name).toBe('HomeTab');
  });
});

describe('W3-15 L5 — PIN: unregistered paths stay unhandled', () => {
  // Already true at base; pinned so nobody "fixes" the four URLs above with a
  // catch-all '*' route, which would swallow every unknown link.
  it.each(['qaren://unknown/thing', 'qaren://'])('%s resolves to undefined', (url) => {
    expect(resolve(url)).toBeUndefined();
  });
});

describe('W3-15 L6-L9 — PINS: the live client-authored deep links are byte-identical', () => {
  // These four are the LIVE referral surfaces (app.json:54-70 intent filters).
  // They pass at base and must keep producing the exact same state after the
  // hoist — the shapes below are the ones measured at ed75dc70.
  it('L6: qaren://c/TOK1?ref=QR-1 -> ReferralLanding', () => {
    expect(JSON.parse(JSON.stringify(resolve('qaren://c/TOK1?ref=QR-1')))).toEqual({
      routes: [
        { name: 'ReferralLanding', params: { share_token: 'TOK1', ref: 'QR-1' }, path: 'c/TOK1?ref=QR-1' },
      ],
    });
  });

  it('L7: qaren://q/TOK2 -> InviteeQuiz', () => {
    expect(JSON.parse(JSON.stringify(resolve('qaren://q/TOK2')))).toEqual({
      routes: [{ name: 'InviteeQuiz', params: { share_token: 'TOK2' }, path: 'q/TOK2' }],
    });
  });

  it('L8: qaren://r/qr-abc -> Auth > Register with the code upper-cased', () => {
    expect(JSON.parse(JSON.stringify(resolve('qaren://r/qr-abc')))).toEqual({
      routes: [
        {
          name: 'Auth',
          state: { routes: [{ name: 'Register', params: { code: 'QR-ABC' }, path: 'r/qr-abc' }] },
        },
      ],
    });
  });

  // L9 pins the redeem -> r/ REWRITE and the rewrite's OWN `code.toUpperCase()`
  // (visible as `path: 'r/QR-XYZ'`). It does NOT pin the `parse.code`
  // upper-casing: the rewrite has already upper-cased the code before
  // getStateFromPath runs, so parse.code is idempotent here. Measured
  // mutations: drop the rewrite -> L9 red; drop the rewrite's toUpperCase ->
  // L9 red (path becomes 'r/qr-xyz'); drop parse.code's toUpperCase -> L8 red,
  // L9 stays GREEN by construction. L8 alone fences parse.code.
  it('L9: qaren://redeem?code=qr-xyz -> the r/ rewrite, upper-cased BY THE REWRITE (path r/QR-XYZ)', () => {
    expect(JSON.parse(JSON.stringify(resolve('qaren://redeem?code=qr-xyz')))).toEqual({
      routes: [
        {
          name: 'Auth',
          state: { routes: [{ name: 'Register', params: { code: 'QR-XYZ' }, path: 'r/QR-XYZ' }] },
        },
      ],
    });
  });

  it('L9b: https:// prefix resolves the same shapes (both prefixes preserved)', () => {
    expect(resolve('https://qaren.app/c/TOK1?ref=QR-1')).toBeDefined();
    const cfg = linking as LinkingOptions<any>;
    expect(cfg.prefixes).toEqual(['qaren://', 'https://qaren.app']);
  });
});

describe('W3-15 L10 — KNOWN-LIMIT PIN: a cold-start LINKING url for Results is a single-entry root stack', () => {
  // Documented limit, NOT a fix (PR body, device walkthrough). Push taps never
  // take this path — pushNavigation.ts dispatches NAVIGATE over the already
  // initialised `Main`. But registering the root `Results` path also means a
  // `qaren://comparison/X` opened through Linking on a COLD start (the app.json
  // `qaren` catch-all intent filter) becomes the container's INITIAL state:
  // one route, no `Main` beneath it, so ResultsScreen's back arrow
  // (`navigation.goBack()`) has nothing to go back to. No producer emits such a
  // Linking URL today. If a later change adds `initialRouteName: 'Main'` or
  // otherwise puts `Main` under Results, this pin goes red ON PURPOSE — update
  // it together with the PR-body limit, and re-check L6-L9 (the same knob
  // prepends `Main` to the live c/ q/ r/ shapes).
  it('resolves to [Results] only, and the real StackRouter rehydrates it as index 0 with nothing below', () => {
    const state = resolve('qaren://comparison/X');
    expect(JSON.parse(JSON.stringify(state))).toEqual({
      routes: [{ name: 'Results', params: { comparison_id: 'X' }, path: 'comparison/X' }],
    });

    // A two-name SUBSET of the authenticated root stack's route names (App.tsx
    // declares more screens; none affects this result), through the real
    // routers StackRouter (re-exported by @react-navigation/native).
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const { StackRouter } = require('@react-navigation/native');
    const routeNames = ['Main', 'Results'];
    const rehydrated = StackRouter({}).getRehydratedState(state, {
      routeNames,
      routeParamList: {},
      routeGetIdList: {},
    });
    expect(rehydrated.routes.map((r: { name: string }) => r.name)).toEqual(['Results']);
    expect(rehydrated.index).toBe(0);
  });
});
