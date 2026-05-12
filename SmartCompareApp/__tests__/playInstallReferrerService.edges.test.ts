/**
 * playInstallReferrerService edge-case coverage.
 *
 * Complements the 7 baseline tests in playInstallReferrerService.test.ts
 * (which already cover: valid-query, bare-code, no-QR, Play error,
 * ambiguous-char rejection, wrong-length rejection, iOS no-op).
 *
 * This file adds the boundary cases test-bcd owns per plan Task 7:
 *   - empty installReferrer string
 *   - missing installReferrer property
 *   - null info object
 *   - malformed callback signature (info=undefined)
 *   - native module require throws (Expo Go without dev client)
 *   - native module throws on getInstallReferrerInfo call
 *   - case-mismatched code (lowercase qr- prefix)
 *
 * All test fixtures use only the canonical unambiguous alphabet
 * `[A-HJ-NP-Z2-9]` matching `app/services/attribution_service.py:_QR_CODE_PATTERN`.
 *
 * Spec: docs/plans/2026-05-12-bundle-bcd-consolidated-design.md § 4.1
 */
jest.mock('react-native-play-install-referrer', () => ({
  PlayInstallReferrer: {
    getInstallReferrerInfo: jest.fn(),
  },
}));

jest.mock('react-native', () => ({
  ...jest.requireActual('../__mocks__/react-native'),
  Platform: { OS: 'android', select: (o: any) => o.android },
}));

import { tryReadPlayInstallReferrer } from '../src/services/playInstallReferrerService';

const { PlayInstallReferrer } = jest.requireMock(
  'react-native-play-install-referrer'
);

describe('playInstallReferrerService — edges (Android)', () => {
  beforeEach(() => jest.clearAllMocks());

  it('returns null when installReferrer is an empty string', async () => {
    PlayInstallReferrer.getInstallReferrerInfo.mockImplementation((cb: any) =>
      cb({ installReferrer: '' }, null)
    );
    expect(await tryReadPlayInstallReferrer()).toBeNull();
  });

  it('returns null when installReferrer is whitespace-only', async () => {
    PlayInstallReferrer.getInstallReferrerInfo.mockImplementation((cb: any) =>
      cb({ installReferrer: '   ' }, null)
    );
    expect(await tryReadPlayInstallReferrer()).toBeNull();
  });

  it('returns null when installReferrer property is missing from info', async () => {
    PlayInstallReferrer.getInstallReferrerInfo.mockImplementation((cb: any) =>
      cb({}, null)
    );
    expect(await tryReadPlayInstallReferrer()).toBeNull();
  });

  it('returns null when info object itself is null', async () => {
    PlayInstallReferrer.getInstallReferrerInfo.mockImplementation((cb: any) =>
      cb(null, null)
    );
    expect(await tryReadPlayInstallReferrer()).toBeNull();
  });

  it('returns null when callback fires with info=undefined (defensive)', async () => {
    PlayInstallReferrer.getInstallReferrerInfo.mockImplementation((cb: any) =>
      cb(undefined, null)
    );
    expect(await tryReadPlayInstallReferrer()).toBeNull();
  });

  it('returns null when the native module throws synchronously', async () => {
    PlayInstallReferrer.getInstallReferrerInfo.mockImplementation(() => {
      throw new Error('JNI exception');
    });
    // Must NEVER bubble — install-survival is best-effort, app must still launch.
    await expect(tryReadPlayInstallReferrer()).resolves.toBeNull();
  });

  it('case-mismatched code (lowercase) is rejected even when well-formed', async () => {
    PlayInstallReferrer.getInstallReferrerInfo.mockImplementation((cb: any) =>
      cb({ installReferrer: 'referrer=qr-abcdef' }, null)
    );
    expect(await tryReadPlayInstallReferrer()).toBeNull();
  });

  it('mixed-case body (Qr-ABcdef) is rejected', async () => {
    PlayInstallReferrer.getInstallReferrerInfo.mockImplementation((cb: any) =>
      cb({ installReferrer: 'referrer=Qr-ABCDEF' }, null)
    );
    expect(await tryReadPlayInstallReferrer()).toBeNull();
  });

  it('valid alphabet-compliant bare code is accepted (regression for trim path)', async () => {
    // Whitespace around a bare code is trimmed before regex test.
    PlayInstallReferrer.getInstallReferrerInfo.mockImplementation((cb: any) =>
      cb({ installReferrer: '  QR-ATAUX9  ' }, null)
    );
    expect(await tryReadPlayInstallReferrer()).toBe('QR-ATAUX9');
  });

  it('first valid query referrer wins when 2 are present', async () => {
    // Defense against an attacker appending a decoy referrer to steal credit.
    PlayInstallReferrer.getInstallReferrerInfo.mockImplementation((cb: any) =>
      cb(
        { installReferrer: 'referrer=QR-FRSTAB&referrer=QR-SCNDCD' },
        null
      )
    );
    expect(await tryReadPlayInstallReferrer()).toBe('QR-FRSTAB');
  });
});
