/**
 * Tests for Android Play Install Referrer reader.
 *
 * Canonical QR alphabet (matches backend `_CODE_ALPHABET` in
 * app/services/referral_service.py): `ABCDEFGHJKMNPQRSTUVWXYZ23456789`
 * (no I, L, O, 0, 1 — unambiguous). Same regex as
 * app/services/attribution_service.py `_QR_CODE_PATTERN`.
 */
jest.mock('react-native-play-install-referrer', () => ({
  PlayInstallReferrer: {
    getInstallReferrerInfo: jest.fn(),
  },
}));

// Force android in the platform mock used by tryReadPlayInstallReferrer.
jest.mock('react-native', () => ({
  ...jest.requireActual('../__mocks__/react-native'),
  Platform: { OS: 'android', select: (o: any) => o.android },
}));

import { tryReadPlayInstallReferrer } from '../src/services/playInstallReferrerService';

const { PlayInstallReferrer } = jest.requireMock(
  'react-native-play-install-referrer'
);

describe('playInstallReferrerService', () => {
  beforeEach(() => jest.clearAllMocks());

  it('returns the QR code when referrer query string contains a valid code', async () => {
    PlayInstallReferrer.getInstallReferrerInfo.mockImplementation((cb: any) =>
      cb(
        { installReferrer: 'referrer=QR-ATAUX9&utm_source=share' },
        null
      )
    );
    expect(await tryReadPlayInstallReferrer()).toBe('QR-ATAUX9');
  });

  it('returns the QR code from a bare referrer value (no other params)', async () => {
    PlayInstallReferrer.getInstallReferrerInfo.mockImplementation((cb: any) =>
      cb({ installReferrer: 'QR-ATAUX9' }, null)
    );
    expect(await tryReadPlayInstallReferrer()).toBe('QR-ATAUX9');
  });

  it('returns null when no QR pattern is found', async () => {
    PlayInstallReferrer.getInstallReferrerInfo.mockImplementation((cb: any) =>
      cb({ installReferrer: 'utm_source=organic' }, null)
    );
    expect(await tryReadPlayInstallReferrer()).toBeNull();
  });

  it('returns null when Play services error fires', async () => {
    PlayInstallReferrer.getInstallReferrerInfo.mockImplementation((cb: any) =>
      cb(null, new Error('PLAY_SERVICE_UNAVAILABLE'))
    );
    expect(await tryReadPlayInstallReferrer()).toBeNull();
  });

  it('rejects codes containing ambiguous characters (I, L, O, 0, 1)', async () => {
    PlayInstallReferrer.getInstallReferrerInfo.mockImplementation((cb: any) =>
      cb({ installReferrer: 'referrer=QR-ABO123' }, null)
    );
    // O and 0 and 1 are not in the canonical alphabet → reject.
    expect(await tryReadPlayInstallReferrer()).toBeNull();
  });

  it('rejects codes with wrong length', async () => {
    PlayInstallReferrer.getInstallReferrerInfo.mockImplementation((cb: any) =>
      cb({ installReferrer: 'referrer=QR-ABC' }, null)
    );
    expect(await tryReadPlayInstallReferrer()).toBeNull();
  });
});

describe('playInstallReferrerService — iOS no-op', () => {
  beforeAll(() => {
    jest.resetModules();
    jest.doMock('react-native', () => ({
      ...jest.requireActual('../__mocks__/react-native'),
      Platform: { OS: 'ios', select: (o: any) => o.ios },
    }));
  });

  afterAll(() => {
    jest.dontMock('react-native');
    jest.resetModules();
  });

  it('returns null without invoking native module on iOS', async () => {
    const mod = await import('../src/services/playInstallReferrerService');
    expect(await mod.tryReadPlayInstallReferrer()).toBeNull();
  });
});
