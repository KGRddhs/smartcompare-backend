/**
 * S69 U6 T4 — first launch on an Arabic device reloads once into RTL (RT-14).
 *
 * Spec R4 + review corrections 16-17 and open question H:
 *   - `src/i18n/rtlBootstrap.ts` exports `bootstrapRtl(lang)`. It does what
 *     App.tsx:195-199 did (allowRTL + forceRTL when the direction differs)
 *     and, when that CHANGES the direction and `@qaren_rtl_bootstrapped` is
 *     unset, writes the flag FIRST and then calls `Updates.reloadAsync()`
 *     exactly once — so a crash after the write can never loop.
 *   - expo-updates is lazy-required inside try/catch (it is mocked nowhere,
 *     and useLanguage.ts:21-26 uses the same pattern); the reload is gated on
 *     `Updates.isEnabled && !__DEV__`; nothing in it ever throws.
 *   - App.tsx's `init()` calls `bootstrapRtl(lang)` in place of the inline
 *     block, so the boot-block suites (App.bootGuard.b5,
 *     bootRegressionPins.w312) only need the one new parameter name.
 *
 * `__DEV__` is false under jest (__tests__/setup.ts:11), so the reload path
 * is live here; T4.6 flips it on explicitly.
 */

import * as fs from 'fs';
import * as path from 'path';
import AsyncStorage from '@react-native-async-storage/async-storage';

const mockUpdates = {
  isEnabled: true,
  reloadAsync: jest.fn(),
};
let mockUpdatesLoadThrows = false;
jest.mock('expo-updates', () => {
  if (mockUpdatesLoadThrows) throw new Error('native module missing');
  return mockUpdates;
});

// eslint-disable-next-line @typescript-eslint/no-require-imports
const RN = require('react-native');

const FLAG = '@qaren_rtl_bootstrapped';
const APP_TSX = path.resolve(__dirname, '../App.tsx');
const MODULE_TS = path.resolve(__dirname, '../src/i18n/rtlBootstrap.ts');

function bootstrapRtl(lang: string): Promise<unknown> {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  return require('../src/i18n/rtlBootstrap').bootstrapRtl(lang);
}

const order: string[] = [];

beforeEach(async () => {
  jest.clearAllMocks();
  order.length = 0;
  await AsyncStorage.clear();
  RN.I18nManager.isRTL = false;
  (globalThis as any).__DEV__ = false;
  mockUpdates.isEnabled = true;
  mockUpdates.reloadAsync.mockImplementation(async () => {
    order.push('reloadAsync');
  });
  (AsyncStorage.setItem as jest.Mock).mockImplementation(async (key: string, value: string) => {
    order.push(`setItem:${key}`);
    (AsyncStorage as any)._store[key] = value;
  });
});

afterAll(() => {
  RN.I18nManager.isRTL = false;
  (globalThis as any).__DEV__ = false;
});

describe('S69 U6 T4 \u2014 bootstrapRtl', () => {
  it('T4.1 first launch, Arabic device, LTR layout: forces RTL, writes the flag BEFORE reloadAsync, reloads exactly once', async () => {
    await bootstrapRtl('ar');

    expect(RN.I18nManager.allowRTL).toHaveBeenCalledWith(true);
    expect(RN.I18nManager.forceRTL).toHaveBeenCalledWith(true);
    expect(await AsyncStorage.getItem(FLAG)).not.toBeNull();
    expect(mockUpdates.reloadAsync).toHaveBeenCalledTimes(1);
    expect(order.indexOf(`setItem:${FLAG}`)).toBeGreaterThanOrEqual(0);
    expect(order.indexOf(`setItem:${FLAG}`)).toBeLessThan(order.indexOf('reloadAsync'));
  });

  it('T4.2 second launch (flag set, now RTL) does not reload', async () => {
    await bootstrapRtl('ar');
    expect(mockUpdates.reloadAsync).toHaveBeenCalledTimes(1);

    RN.I18nManager.isRTL = true; // what the reload produced
    mockUpdates.reloadAsync.mockClear();
    await bootstrapRtl('ar');
    expect(mockUpdates.reloadAsync).not.toHaveBeenCalled();
  });

  it('T4.3 flag already set but the layout is still LTR: forceRTL again, never a second reload (no crash loop)', async () => {
    await bootstrapRtl('ar');
    expect(mockUpdates.reloadAsync).toHaveBeenCalledTimes(1);

    RN.I18nManager.isRTL = false; // the reload did not take
    mockUpdates.reloadAsync.mockClear();
    (RN.I18nManager.forceRTL as jest.Mock).mockClear();
    await bootstrapRtl('ar');
    expect(RN.I18nManager.forceRTL).toHaveBeenCalledWith(true);
    expect(mockUpdates.reloadAsync).not.toHaveBeenCalled();
  });

  it('T4.4 an English device never reloads and never writes the flag', async () => {
    await bootstrapRtl('en');
    await bootstrapRtl('en');

    expect(mockUpdates.reloadAsync).not.toHaveBeenCalled();
    expect(await AsyncStorage.getItem(FLAG)).toBeNull();
    expect(RN.I18nManager.forceRTL).not.toHaveBeenCalledWith(true);
  });

  it('T4.5 Arabic device already reporting RTL (no direction change) does not reload', async () => {
    RN.I18nManager.isRTL = true;
    await bootstrapRtl('ar');
    expect(mockUpdates.reloadAsync).not.toHaveBeenCalled();
    expect(RN.I18nManager.forceRTL).not.toHaveBeenCalled();
  });

  it('T4.6 no reload in __DEV__ or when Updates.isEnabled is false (RTL is still forced)', async () => {
    (globalThis as any).__DEV__ = true;
    await bootstrapRtl('ar');
    expect(RN.I18nManager.forceRTL).toHaveBeenCalledWith(true);
    expect(mockUpdates.reloadAsync).not.toHaveBeenCalled();

    (globalThis as any).__DEV__ = false;
    await AsyncStorage.clear();
    (RN.I18nManager.forceRTL as jest.Mock).mockClear();
    mockUpdates.isEnabled = false;
    await bootstrapRtl('ar');
    expect(RN.I18nManager.forceRTL).toHaveBeenCalledWith(true);
    expect(mockUpdates.reloadAsync).not.toHaveBeenCalled();
  });

  it('T4.7 never throws: a rejecting reloadAsync and a failing flag write both resolve', async () => {
    mockUpdates.reloadAsync.mockRejectedValueOnce(new Error('reload refused'));
    await expect(bootstrapRtl('ar')).resolves.not.toThrow();
    expect(mockUpdates.reloadAsync).toHaveBeenCalledTimes(1);

    await AsyncStorage.clear();
    RN.I18nManager.isRTL = false;
    mockUpdates.reloadAsync.mockClear();
    (AsyncStorage.setItem as jest.Mock).mockRejectedValueOnce(new Error('disk full'));
    await expect(bootstrapRtl('ar')).resolves.not.toThrow();
    // With no persisted flag there is no crash-loop guard, so it must not reload.
    expect(mockUpdates.reloadAsync).not.toHaveBeenCalled();
  });

  // Runs LAST among the behavioural tests: it resets the module registry so
  // the expo-updates factory runs again (a cached mock would be reused
  // otherwise), and the tests after it only read source files.
  it('T4.8 never throws when expo-updates cannot be loaded, and still forces RTL', async () => {
    mockUpdatesLoadThrows = true;
    try {
      jest.resetModules();
      // eslint-disable-next-line @typescript-eslint/no-require-imports
      const RNi = require('react-native');
      RNi.I18nManager.isRTL = false;
      // eslint-disable-next-line @typescript-eslint/no-require-imports
      const mod = require('../src/i18n/rtlBootstrap');
      await expect(mod.bootstrapRtl('ar')).resolves.not.toThrow();
      expect(RNi.I18nManager.forceRTL).toHaveBeenCalledWith(true);
      expect(mockUpdates.reloadAsync).not.toHaveBeenCalled();
    } finally {
      mockUpdatesLoadThrows = false;
    }
  });

  it('T4.9 expo-updates is lazy-required (no top-level import) in rtlBootstrap.ts', () => {
    const src = fs.readFileSync(MODULE_TS, 'utf8');
    expect(src).not.toMatch(/^\s*import[^;]*['"]expo-updates['"]/m);
    expect(src).toMatch(/require\(\s*['"]expo-updates['"]\s*\)/);
  });
});

describe('S69 U6 T4 \u2014 App.tsx boot calls bootstrapRtl', () => {
  it('T4.10 init() calls bootstrapRtl(lang) and no longer forces RTL inline', () => {
    const src = fs.readFileSync(APP_TSX, 'utf8');
    const start = src.indexOf('async function init()');
    expect(start).toBeGreaterThan(-1);
    const block = src.slice(start, src.indexOf('initializeAuth', start));
    expect(block).toMatch(/bootstrapRtl\(\s*lang\s*\)/);
    expect(block).not.toMatch(/I18nManager\.forceRTL\(/);
    expect(src).toMatch(
      /import\s*\{[^}]*\bbootstrapRtl\b[^}]*\}\s*from\s*['"]\.\/src\/i18n\/rtlBootstrap['"]/,
    );
  });
});
