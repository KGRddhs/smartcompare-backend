/* eslint-disable @typescript-eslint/no-require-imports */
/**
 * S81-G6 CL2 CLIENT-SPEED -- rows R27-R29, P8 (spec section 5, RULINGS_S81_G6
 * R-G6-6): metro.config.js = getSentryExpoConfig(__dirname,
 * { includeWebReplay: false }) composed with the P-B1 qarenCacheVersion.
 * Measured on the installed @sentry/react-native 7.2.0: the replay packages
 * resolve to {type: 'empty'} on every platform, every other module goes to
 * the original resolver, and the Sentry frame collapse is installed.
 *
 * Loading the real config sets ___SENTRY_METRO_DEV_SERVER___ in this worker
 * at HEAD; the variable is restored in afterAll.
 */

import * as fs from 'fs';
import * as path from 'path';

const APP_ROOT = path.resolve(__dirname, '../..');
const hadEnv = Object.prototype.hasOwnProperty.call(process.env, '___SENTRY_METRO_DEV_SERVER___');
const envBefore = process.env.___SENTRY_METRO_DEV_SERVER___;

const { qarenCacheVersion } = require('../../metro.cacheVersion');

let cached: any = null;
function loadConfig(): any {
  if (!cached) {
    cached = require('../../metro.config.js');
  }
  return cached;
}

/** Strip // and block comments (string-aware enough for this small file). */
function stripComments(src: string): string {
  return src.replace(/\/\*[\s\S]*?\*\//g, '').replace(/(^|[^:'"])\/\/.*$/gm, '$1');
}

afterAll(() => {
  if (hadEnv) process.env.___SENTRY_METRO_DEV_SERVER___ = envBefore;
  else delete process.env.___SENTRY_METRO_DEV_SERVER___;
});

describe('CL2 metro Sentry wrapper (C5)', () => {
  it('R27 static: the Sentry wrapper with includeWebReplay false, one cacheVersion line', () => {
    const raw = fs.readFileSync(path.join(APP_ROOT, 'metro.config.js'), 'utf8').replace(/\r\n/g, '\n');
    const src = stripComments(raw);
    expect(raw).toContain('P-B1-CACHE');
    expect(src).toContain("require('@sentry/react-native/metro')");
    expect(src).toMatch(
      /getSentryExpoConfig\(\s*__dirname\s*,\s*\{\s*includeWebReplay:\s*false\s*\}\s*\)/
    );
    expect(src).not.toMatch(/includeWebFeedback/);
    expect(src.split('config.cacheVersion = qarenCacheVersion(').length - 1).toBe(1);
  });

  it('R28 resolver: the replay packages resolve empty on ios and android; react passes through', () => {
    const config = loadConfig();
    const rr = config.resolver && config.resolver.resolveRequest;
    expect(typeof rr).toBe('function');
    const calls: string[] = [];
    const context = {
      resolveRequest: (_ctx: any, name: string, platform: string) => {
        calls.push(name + '@' + platform);
        return { type: 'sourceFile', filePath: '/synthetic/' + name };
      },
    };
    for (const platform of ['ios', 'android']) {
      expect(rr(context, '@sentry-internal/replay', platform)).toEqual({ type: 'empty' });
      expect(rr(context, '@sentry/replay', platform)).toEqual({ type: 'empty' });
    }
    expect(calls).toEqual([]);
    expect(rr(context, 'react', 'ios')).toEqual({ type: 'sourceFile', filePath: '/synthetic/react' });
    expect(calls).toEqual(['react@ios']);
  }, 120000);

  // Measured deviation from the spec row: the STOCK Expo customizeFrame
  // already collapses node_modules/@sentry/core/cjs/debug.js (collapse true
  // at base), so the behaviour alone cannot tell the wrapper apart. The row
  // therefore pins the frame result AND that the installed customizeFrame is
  // Sentry's withSentryFramesCollapsed wrapper (7.2.0 source names
  // collapseSentryInternalFrames), composed over the original.
  it('R29 the Sentry frame collapse is installed', async () => {
    const config = loadConfig();
    const cf = config.symbolicator && config.symbolicator.customizeFrame;
    expect(typeof cf).toBe('function');
    expect(String(cf)).toContain('collapseSentryInternalFrames');
    const out = await cf({ file: 'node_modules/@sentry/core/cjs/debug.js' });
    expect(out && out.collapse).toBe(true);
    const app = await cf({ file: 'src/screens/HomeScreen.tsx' });
    expect(app && app.collapse).toBe(false);
  }, 120000);

  it('P8 the P-B1 cache key is still composed (stock 1.0 base)', () => {
    const config = loadConfig();
    expect(config.cacheVersion).toBe(qarenCacheVersion(APP_ROOT, '1.0'));
  }, 120000);
});
