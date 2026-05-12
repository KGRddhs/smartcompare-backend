/**
 * Tests for iOS clipboard fallback reader.
 *
 * Canonical QR alphabet (matches backend `_CODE_ALPHABET` in
 * app/services/referral_service.py): `ABCDEFGHJKMNPQRSTUVWXYZ23456789`
 * (no I, L, O, 0, 1 — unambiguous). Same regex as
 * app/services/attribution_service.py `_QR_CODE_PATTERN`.
 */
jest.mock('expo-clipboard', () => ({
  getStringAsync: jest.fn(),
}));

import { tryReadClipboardForInviteCode } from '../src/services/clipboardFallbackService';

const Clipboard = jest.requireMock('expo-clipboard');

describe('clipboardFallbackService', () => {
  beforeEach(() => jest.clearAllMocks());

  it('returns the code when clipboard exactly matches QR-XXXXXX', async () => {
    Clipboard.getStringAsync.mockResolvedValue('QR-ATAUX9');
    expect(await tryReadClipboardForInviteCode()).toBe('QR-ATAUX9');
  });

  it('returns the code after trimming surrounding whitespace', async () => {
    Clipboard.getStringAsync.mockResolvedValue('  QR-ATAUX9\n');
    expect(await tryReadClipboardForInviteCode()).toBe('QR-ATAUX9');
  });

  it('returns null on arbitrary clipboard text', async () => {
    Clipboard.getStringAsync.mockResolvedValue('hello world');
    expect(await tryReadClipboardForInviteCode()).toBeNull();
  });

  it('returns null on empty clipboard', async () => {
    Clipboard.getStringAsync.mockResolvedValue('');
    expect(await tryReadClipboardForInviteCode()).toBeNull();
  });

  it('returns null when read throws', async () => {
    Clipboard.getStringAsync.mockRejectedValue(new Error('denied'));
    expect(await tryReadClipboardForInviteCode()).toBeNull();
  });

  it('rejects codes with ambiguous characters (I, L, O, 0, 1)', async () => {
    Clipboard.getStringAsync.mockResolvedValue('QR-ABO123');
    expect(await tryReadClipboardForInviteCode()).toBeNull();
  });

  it('rejects codes with wrong length', async () => {
    Clipboard.getStringAsync.mockResolvedValue('QR-ABCDE'); // 5 chars body
    expect(await tryReadClipboardForInviteCode()).toBeNull();
  });

  it('does NOT extract a code embedded in a longer string (safety — explicit-only)', async () => {
    Clipboard.getStringAsync.mockResolvedValue(
      'Hey check out qaren.app/r/QR-ATAUX9 it is cool'
    );
    expect(await tryReadClipboardForInviteCode()).toBeNull();
  });
});
