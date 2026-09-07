/**
 * A9 — the force-update client, end to end minus React.
 *
 * THE DEAD WIRE
 * `GET /api/v1/app/version` has been served since Bundle D and called by
 * nobody, so `APP_FORCE_UPDATE` could not reach a device. These tests pin
 * BOTH halves of closing it: that the request is actually made against the
 * documented path with a deadline, and — far more important — that every
 * uncertain outcome fails OPEN. A false block is unrecoverable from the
 * device side.
 */

// `mock`-prefixed so jest's hoisting rules allow the factory to close
// over it. Drives what expo-application reports for this install.
let mockNativeVersion: string | null | undefined = '1.0.0';
jest.mock('expo-application', () => ({
  get nativeApplicationVersion() {
    return mockNativeVersion;
  },
  applicationId: 'com.qaren.test',
}));

import { Platform } from 'react-native';
import {
  checkForcedUpdate,
  decideForcedUpdate,
  getCurrentAppVersion,
  pickUpdateUrl,
  VERSION_CHECK_PATH,
  VERSION_CHECK_TIMEOUT_MS,
} from '../src/services/appVersionService';
import { API_BASE_URL } from '../src/services/api';

const mockFetch = jest.fn();
(global as any).fetch = mockFetch;

/** The exact body `version_routes.get_version_info()` returns. */
function serverBody(overrides: Record<string, unknown> = {}) {
  return {
    min_version: '1.0.0',
    latest_version: '1.0.0',
    force_update: false,
    update_url_ios: '',
    update_url_android: '',
    ...overrides,
  };
}

function jsonResponse(body: unknown, ok = true) {
  return { ok, status: ok ? 200 : 500, json: async () => body };
}

const originalPlatformOS = Platform.OS;

beforeEach(() => {
  mockFetch.mockReset();
  mockNativeVersion = '1.0.0';
  (Platform as any).OS = originalPlatformOS;
});

afterEach(() => {
  (Platform as any).OS = originalPlatformOS;
});

describe('decideForcedUpdate — the block/no-block truth table', () => {
  it('BLOCKS on force_update true AND current strictly below min_version', () => {
    const gate = decideForcedUpdate(
      serverBody({ force_update: true, min_version: '1.4.0', update_url_ios: 'https://apps.apple.com/app/id1' }),
      '1.3.9',
      'ios'
    );
    expect(gate).toEqual({
      minVersion: '1.4.0',
      currentVersion: '1.3.9',
      updateUrl: 'https://apps.apple.com/app/id1',
    });
  });

  it('does NOT block when force_update is off, even far below min_version', () => {
    expect(
      decideForcedUpdate(serverBody({ force_update: false, min_version: '9.0.0' }), '1.0.0', 'ios')
    ).toBeNull();
  });

  it('does NOT block when the version is at or above the minimum', () => {
    const body = serverBody({ force_update: true, min_version: '1.4.0' });
    expect(decideForcedUpdate(body, '1.4.0', 'ios')).toBeNull();
    expect(decideForcedUpdate(body, '1.4.1', 'ios')).toBeNull();
    expect(decideForcedUpdate(body, '2.0.0', 'ios')).toBeNull();
  });

  it('does NOT block on 1.10.0 vs a 1.9.0 minimum (numeric, not lexicographic)', () => {
    expect(
      decideForcedUpdate(serverBody({ force_update: true, min_version: '1.9.0' }), '1.10.0', 'ios')
    ).toBeNull();
    // ...and still blocks the genuinely older build.
    expect(
      decideForcedUpdate(serverBody({ force_update: true, min_version: '1.10.0' }), '1.9.0', 'ios')
    ).not.toBeNull();
  });

  it.each([
    ['string "true"', 'true'],
    ['number 1', 1],
    ['truthy object', {}],
    ['string "yes"', 'yes'],
  ])('does NOT block when force_update is %s rather than the boolean', (_label, value) => {
    expect(
      decideForcedUpdate(serverBody({ force_update: value, min_version: '9.0.0' }), '1.0.0', 'ios')
    ).toBeNull();
  });

  it.each([
    ['null payload', null],
    ['undefined payload', undefined],
    ['array payload', [{ force_update: true, min_version: '9.0.0' }]],
    ['string payload', '{"force_update":true}'],
    ['empty object', {}],
    ['missing min_version', { force_update: true }],
    ['blank min_version', { force_update: true, min_version: '   ' }],
    ['non-string min_version', { force_update: true, min_version: 9 }],
    ['unparseable min_version', { force_update: true, min_version: 'latest' }],
  ])('does NOT block on %s', (_label, payload) => {
    expect(decideForcedUpdate(payload, '1.0.0', 'ios')).toBeNull();
  });

  it.each([[null], [undefined], [''], ['   '], [42], [{}]])(
    'does NOT block when the installed version is %p',
    (current) => {
      expect(
        decideForcedUpdate(serverBody({ force_update: true, min_version: '9.9.9' }), current, 'ios')
      ).toBeNull();
    }
  );
});

describe('pickUpdateUrl', () => {
  const body = serverBody({
    update_url_ios: 'https://apps.apple.com/app/id1',
    update_url_android: 'https://play.google.com/store/apps/details?id=app.qaren',
  });

  it('picks per platform', () => {
    expect(pickUpdateUrl(body, 'ios')).toBe('https://apps.apple.com/app/id1');
    expect(pickUpdateUrl(body, 'android')).toBe(
      'https://play.google.com/store/apps/details?id=app.qaren'
    );
  });

  it('accepts the native store schemes', () => {
    expect(pickUpdateUrl({ update_url_ios: 'itms-apps://itunes.apple.com/app/id1' }, 'ios')).toBe(
      'itms-apps://itunes.apple.com/app/id1'
    );
    expect(pickUpdateUrl({ update_url_android: 'market://details?id=app.qaren' }, 'android')).toBe(
      'market://details?id=app.qaren'
    );
  });

  it.each([
    ['empty (the backend default)', ''],
    ['whitespace', '   '],
    ['missing', undefined],
    ['non-string', 12345],
    ['javascript: scheme', 'javascript:alert(1)'],
    ['file: scheme', 'file:///etc/passwd'],
    ['bare host', 'apps.apple.com/app/id1'],
  ])('returns null for a %s url', (_label, value) => {
    expect(pickUpdateUrl({ update_url_ios: value }, 'ios')).toBeNull();
  });

  it('a missing store url does not cancel the block itself', () => {
    const gate = decideForcedUpdate(
      serverBody({ force_update: true, min_version: '2.0.0' }),
      '1.0.0',
      'ios'
    );
    expect(gate).not.toBeNull();
    expect(gate?.updateUrl).toBeNull();
  });
});

describe('getCurrentAppVersion', () => {
  it('returns the native version when the runtime reports one', () => {
    mockNativeVersion = '1.4.2';
    expect(getCurrentAppVersion()).toBe('1.4.2');
  });

  it.each([[null], [undefined], [''], ['   ']])('returns null for %p (Expo Go / simulator)', (v) => {
    mockNativeVersion = v as string | null;
    expect(getCurrentAppVersion()).toBeNull();
  });
});

describe('checkForcedUpdate — the network path', () => {
  it('calls the documented endpoint with a deadline', async () => {
    mockFetch.mockResolvedValue(jsonResponse(serverBody()));

    await checkForcedUpdate();

    expect(mockFetch).toHaveBeenCalledTimes(1);
    expect(mockFetch.mock.calls[0][0]).toBe(`${API_BASE_URL}${VERSION_CHECK_PATH}`);
    expect(`${API_BASE_URL}${VERSION_CHECK_PATH}`).toContain('/api/v1/app/version');
    // fetchWithDeadline attaches an abort signal; without one a stalled
    // socket would keep this promise pending forever.
    expect(mockFetch.mock.calls[0][1].signal).toBeDefined();
    expect(VERSION_CHECK_TIMEOUT_MS).toBeLessThanOrEqual(15000);
  });

  it('returns the gate when the server affirmatively demands an update', async () => {
    mockNativeVersion = '1.2.0';
    mockFetch.mockResolvedValue(
      jsonResponse(
        serverBody({
          force_update: true,
          min_version: '1.5.0',
          update_url_ios: 'https://apps.apple.com/app/id1',
        })
      )
    );

    await expect(checkForcedUpdate()).resolves.toEqual({
      minVersion: '1.5.0',
      currentVersion: '1.2.0',
      updateUrl: 'https://apps.apple.com/app/id1',
    });
  });

  it('reads the ANDROID url on android', async () => {
    (Platform as any).OS = 'android';
    mockNativeVersion = '1.2.0';
    mockFetch.mockResolvedValue(
      jsonResponse(
        serverBody({
          force_update: true,
          min_version: '1.5.0',
          update_url_ios: 'https://apps.apple.com/app/id1',
          update_url_android: 'https://play.google.com/store/apps/details?id=app.qaren',
        })
      )
    );

    const gate = await checkForcedUpdate();
    expect(gate?.updateUrl).toBe('https://play.google.com/store/apps/details?id=app.qaren');
  });

  it('never asks the server at all when the runtime has no native version', async () => {
    mockNativeVersion = null; // Expo Go
    await expect(checkForcedUpdate()).resolves.toBeNull();
    expect(mockFetch).not.toHaveBeenCalled();
  });

  it('fails open when the request rejects (offline / TLS / DNS)', async () => {
    mockNativeVersion = '1.0.0';
    mockFetch.mockRejectedValue(new TypeError('Network request failed'));
    await expect(checkForcedUpdate()).resolves.toBeNull();
  });

  it('fails open on a non-2xx response', async () => {
    mockNativeVersion = '1.0.0';
    mockFetch.mockResolvedValue(
      jsonResponse(serverBody({ force_update: true, min_version: '9.9.9' }), false)
    );
    await expect(checkForcedUpdate()).resolves.toBeNull();
  });

  it('fails open when the body is not JSON', async () => {
    mockNativeVersion = '1.0.0';
    mockFetch.mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => {
        throw new SyntaxError('Unexpected token < in JSON');
      },
    });
    await expect(checkForcedUpdate()).resolves.toBeNull();
  });

  it('fails open when the deadline expires on a socket that never settles', async () => {
    jest.useFakeTimers();
    try {
      mockNativeVersion = '1.0.0';
      mockFetch.mockImplementation(() => new Promise<never>(() => {}));

      const pending = checkForcedUpdate();
      jest.advanceTimersByTime(VERSION_CHECK_TIMEOUT_MS);

      await expect(pending).resolves.toBeNull();
    } finally {
      jest.useRealTimers();
    }
  });

  it('never rejects — the caller wires it fire-and-forget', async () => {
    mockNativeVersion = '1.0.0';
    // A rejection here would surface as an unhandled rejection at the
    // App.tsx call site rather than a quiet no-gate.
    mockFetch.mockRejectedValue(new Error('boom'));
    await expect(checkForcedUpdate()).resolves.toBeNull();

    mockFetch.mockResolvedValue({ ok: true, status: 200 }); // no .json at all
    await expect(checkForcedUpdate()).resolves.toBeNull();

    mockFetch.mockResolvedValue(undefined);
    await expect(checkForcedUpdate()).resolves.toBeNull();
  });
});
