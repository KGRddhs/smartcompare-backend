/**
 * deferredInviteCode tests — Bundle B/C/D Task 2.11.
 *
 * Verifies the once-per-launch slot semantics: set + consume returns
 * the value the first time and null on subsequent consumes.
 */
import {
  setDeferredInviteCode,
  consumeDeferredInviteCode,
  __resetDeferredInviteCodeForTests,
} from '../src/services/deferredInviteCode';

beforeEach(() => {
  __resetDeferredInviteCodeForTests();
});

describe('deferredInviteCode', () => {
  it('returns null when nothing has been set', () => {
    expect(consumeDeferredInviteCode()).toBeNull();
  });

  it('returns the stored code on first consume after set', () => {
    setDeferredInviteCode('QR-ATAUX9');
    expect(consumeDeferredInviteCode()).toBe('QR-ATAUX9');
  });

  it('returns null on the second consume (set is once-per-launch)', () => {
    setDeferredInviteCode('QR-ATAUX9');
    consumeDeferredInviteCode();
    expect(consumeDeferredInviteCode()).toBeNull();
  });

  it('overwrites a previously-set code if set fires twice', () => {
    setDeferredInviteCode('QR-AAAAAA');
    setDeferredInviteCode('QR-BBBBBB');
    expect(consumeDeferredInviteCode()).toBe('QR-BBBBBB');
  });
});
