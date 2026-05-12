/**
 * clipboardFallbackService edge-case coverage.
 *
 * Complements clipboardFallbackService.test.ts (8 baseline tests covering
 * valid bare code, trim, arbitrary text, empty, throw, ambiguous chars,
 * wrong length, embedded-in-longer-string).
 *
 * Adds test-bcd's gate-coverage cases:
 *   - whitespace-only clipboard returns null
 *   - clipboard returns null (native bridge edge) returns null
 *   - mixed-case body returns null
 *   - case-mismatched prefix (qr-) returns null
 *   - clipboard with leading/trailing tabs only is treated as empty
 *
 * Spec: docs/plans/2026-05-12-bundle-bcd-consolidated-design.md § 4.1
 */
jest.mock('expo-clipboard', () => ({
  getStringAsync: jest.fn(),
}));

import { tryReadClipboardForInviteCode } from '../src/services/clipboardFallbackService';

const Clipboard = jest.requireMock('expo-clipboard');

beforeEach(() => jest.clearAllMocks());

describe('clipboardFallbackService — edges', () => {
  it('returns null for whitespace-only clipboard', async () => {
    Clipboard.getStringAsync.mockResolvedValue('   \t\n');
    expect(await tryReadClipboardForInviteCode()).toBeNull();
  });

  it('treats null clipboard read as empty (defensive)', async () => {
    // The bridge typing says string but native can return null at very-
    // early boot or after a pasteboard wipe — impl uses `?? ''` to coerce.
    Clipboard.getStringAsync.mockResolvedValue(null as any);
    expect(await tryReadClipboardForInviteCode()).toBeNull();
  });

  it('treats undefined clipboard read as empty (defensive)', async () => {
    Clipboard.getStringAsync.mockResolvedValue(undefined as any);
    expect(await tryReadClipboardForInviteCode()).toBeNull();
  });

  it('returns null for mixed-case body (QR-AtAuX9)', async () => {
    Clipboard.getStringAsync.mockResolvedValue('QR-AtAuX9');
    expect(await tryReadClipboardForInviteCode()).toBeNull();
  });

  it('returns null for lowercase prefix (qr-ATAUX9)', async () => {
    Clipboard.getStringAsync.mockResolvedValue('qr-ATAUX9');
    expect(await tryReadClipboardForInviteCode()).toBeNull();
  });

  it('returns null when whitespace-padded code does not match after trim', async () => {
    // After trim the code is still confusable-alphabet → reject.
    Clipboard.getStringAsync.mockResolvedValue('  QR-OOO000  ');
    expect(await tryReadClipboardForInviteCode()).toBeNull();
  });

  it('returns null when whitespace-padded code becomes wrong length after trim', async () => {
    Clipboard.getStringAsync.mockResolvedValue('  QR-ABCDE  '); // 5 body chars
    expect(await tryReadClipboardForInviteCode()).toBeNull();
  });

  it('accepts alphabet-compliant code with mixed leading whitespace types', async () => {
    Clipboard.getStringAsync.mockResolvedValue('\t \nQR-ATAUX9\r\n');
    expect(await tryReadClipboardForInviteCode()).toBe('QR-ATAUX9');
  });

  it('does NOT call clipboard.setStringAsync (read-only contract)', async () => {
    // Defensive: confirm the service is purely a reader. If a future
    // change accidentally writes back to the clipboard, this fails.
    Clipboard.setStringAsync = jest.fn();
    Clipboard.getStringAsync.mockResolvedValue('QR-ATAUX9');
    await tryReadClipboardForInviteCode();
    expect(Clipboard.setStringAsync).not.toHaveBeenCalled();
  });

  it('coerces null via `?? \'\'` BEFORE calling .trim (not via try/catch)', async () => {
    // Mutation guard: removing the `?? ''` coalesce makes `null.trim()` throw,
    // which would be silently swallowed by the surrounding try/catch and still
    // return null — semantically equivalent at the return level, but the code
    // path differs. We pin the impl to the explicit-coerce path by asserting
    // String.prototype.trim IS called exactly once with the empty string,
    // which only happens when the impl performs `null ?? ''` first.
    Clipboard.getStringAsync.mockResolvedValue(null as any);
    const trimSpy = jest.spyOn(String.prototype, 'trim');
    try {
      const result = await tryReadClipboardForInviteCode();
      expect(result).toBeNull();
      // The spy must have observed at least one call on an empty string —
      // proof the null was coerced rather than allowed to throw.
      const calledOnEmptyString = trimSpy.mock.contexts.some(
        (ctx) => ctx === '' || (typeof ctx === 'object' && ctx?.toString() === '')
      );
      expect(calledOnEmptyString).toBe(true);
    } finally {
      trimSpy.mockRestore();
    }
  });
});
