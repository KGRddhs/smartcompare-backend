/**
 * App.tsx PIR wiring contract — Bundle B/C/D Task 2.11.
 *
 * This file asserts the imports + hand-off shape that App.tsx uses at
 * boot. Rendering the full App tree is expensive (NavigationContainer,
 * fonts, splash, auth init) and not what we want to test here — we want
 * to lock in the contract between the PIR service and the deferred-code
 * slot. Real end-to-end PIR validation lives in the EAS dev-build smoke.
 */
import {
  tryReadPlayInstallReferrer,
} from '../src/services/playInstallReferrerService';
import {
  setDeferredInviteCode,
  consumeDeferredInviteCode,
  __resetDeferredInviteCodeForTests,
} from '../src/services/deferredInviteCode';

jest.mock('../src/services/playInstallReferrerService', () => ({
  tryReadPlayInstallReferrer: jest.fn(),
}));

beforeEach(() => {
  jest.clearAllMocks();
  __resetDeferredInviteCodeForTests();
});

describe('PIR → deferredInviteCode wiring contract', () => {
  it('App init pattern: read PIR then setDeferredInviteCode iff non-null', async () => {
    // Simulate what App.tsx does on mount.
    (tryReadPlayInstallReferrer as jest.Mock).mockResolvedValue('QR-ATAUX9');
    const code = await tryReadPlayInstallReferrer();
    if (code) setDeferredInviteCode(code);

    expect(consumeDeferredInviteCode()).toBe('QR-ATAUX9');
  });

  it('App init pattern: no code → deferred slot stays empty', async () => {
    (tryReadPlayInstallReferrer as jest.Mock).mockResolvedValue(null);
    const code = await tryReadPlayInstallReferrer();
    if (code) setDeferredInviteCode(code);

    expect(consumeDeferredInviteCode()).toBeNull();
  });

  it('App init pattern: PIR throw is swallowed → slot stays empty', async () => {
    (tryReadPlayInstallReferrer as jest.Mock).mockRejectedValue(
      new Error('PLAY_SERVICE_UNAVAILABLE')
    );
    try {
      const code = await tryReadPlayInstallReferrer();
      if (code) setDeferredInviteCode(code);
    } catch {
      // App.tsx wraps in .catch(() => {}) — booting must not be blocked.
    }
    expect(consumeDeferredInviteCode()).toBeNull();
  });

  it('App.tsx source imports both functions (compile-time contract)', () => {
    const fs = require('fs');
    const path = require('path');
    const src = fs.readFileSync(
      path.resolve(__dirname, '../App.tsx'),
      'utf8'
    );
    expect(src).toMatch(/tryReadPlayInstallReferrer/);
    expect(src).toMatch(/setDeferredInviteCode/);
  });

  it('App.tsx wires the PIR call in a fire-and-forget shape (no await blocking init)', () => {
    const fs = require('fs');
    const path = require('path');
    const src = fs.readFileSync(
      path.resolve(__dirname, '../App.tsx'),
      'utf8'
    );
    // The pattern is `tryReadPlayInstallReferrer().then(...).catch(...)`
    // or `void tryReadPlayInstallReferrer().then(...)`; either way, no
    // top-level `await tryReadPlayInstallReferrer()` that would block
    // boot inside the synchronous part of init().
    expect(src).toMatch(/tryReadPlayInstallReferrer\s*\(\s*\)\s*\.then/);
  });
});
