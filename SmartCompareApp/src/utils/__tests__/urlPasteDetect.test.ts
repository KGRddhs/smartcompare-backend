/**
 * Tests for `urlPasteDetect.looksLikeUrl` — cheap shape detector used by
 * TwoInputShell's paste-detection. Spec ref § 4.1.2.
 * Plan ref: docs/superpowers/plans/2026-05-17-bundle-b-two-input-ux-design.md § 3.6b.
 *
 * Coverage target: 100% (pure function).
 *
 * NOTE — OQ flagged during Phase 1 red-stub authoring:
 *   The spec's example regex is `^https?://[^\s]+$` (anchored, no trim).
 *   Plan § 3.6b `test_negative_leading_whitespace` expects `false` for
 *   `"   https://example.com"`. Current implementation calls `.trim()`
 *   before regex which would let leading whitespace through.
 *   This test pins the SPEC behavior — leading whitespace is rejected so
 *   pasting "  https://..." into Box A does NOT trigger an auto-mode-switch
 *   when the user typed (rather than pasted) the spaces. If Frontend agent
 *   wants `.trim()` semantics, OQ for cross-QA before changing the test.
 */

import { looksLikeUrl } from '../urlPasteDetect';

describe('urlPasteDetect.looksLikeUrl', () => {
  it('returns true for an https URL', () => {
    expect(looksLikeUrl('https://amazon.ae/dp/B0XYZ12345')).toBe(true);
  });

  it('returns true for an http URL', () => {
    expect(looksLikeUrl('http://example.com')).toBe(true);
  });

  it('returns true for a URL with query params', () => {
    expect(looksLikeUrl('https://noon.com/uae-en/p/123?ref=foo&utm=bar')).toBe(true);
  });

  it('returns true for a URL with a deep path', () => {
    expect(looksLikeUrl('https://example.com/path/to/page')).toBe(true);
  });

  it('returns true for a URL with an explicit port', () => {
    expect(looksLikeUrl('https://example.com:8443/path')).toBe(true);
  });

  it('returns true for http://localhost (frontend accepts; backend SSRF rejects)', () => {
    // Per spec § 3.0 + Frontend § 2.4 — client-side detector is intentionally
    // permissive; SSRF validation runs at the backend boundary.
    expect(looksLikeUrl('http://localhost:3000')).toBe(true);
  });

  it('returns false when there is no protocol prefix', () => {
    expect(looksLikeUrl('amazon.ae/dp/B0XYZ12345')).toBe(false);
  });

  it('returns false for ftp:// (only http/https accepted)', () => {
    expect(looksLikeUrl('ftp://example.com/file.txt')).toBe(false);
  });

  it('returns false for javascript: scheme (XSS guard belt-and-suspenders)', () => {
    expect(looksLikeUrl('javascript:alert(1)')).toBe(false);
  });

  it('returns false for data: URLs', () => {
    expect(looksLikeUrl('data:text/html,<script>alert(1)</script>')).toBe(false);
  });

  it('returns false when there is whitespace inside the URL body', () => {
    // Regex body is `[^\s]+` — internal whitespace is fatal.
    expect(looksLikeUrl('https://example .com')).toBe(false);
  });

  it('returns false on an empty string', () => {
    expect(looksLikeUrl('')).toBe(false);
  });

  it('returns false for a protocol with no host ("https://" alone)', () => {
    // `[^\s]+` requires at least 1 non-whitespace char after `://` — an
    // empty host is rejected.
    expect(looksLikeUrl('https://')).toBe(false);
  });

  it('returns false for leading whitespace before the URL (spec pin — pin)', () => {
    // Spec § 4.1.2 regex is `^https?://[^\s]+$` — anchored. Plan § 3.6b
    // matches. Flagged for cross-QA (current impl calls .trim()).
    expect(looksLikeUrl('   https://example.com')).toBe(false);
  });

  it('returns false for trailing whitespace after the URL (mirror of the leading-whitespace case)', () => {
    expect(looksLikeUrl('https://example.com   ')).toBe(false);
  });
});
