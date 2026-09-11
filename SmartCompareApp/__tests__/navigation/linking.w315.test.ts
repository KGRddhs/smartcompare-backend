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

  it('L9: qaren://redeem?code=qr-xyz -> the r/ rewrite, path rewritten too', () => {
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
