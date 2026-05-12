/**
 * iOS-primary clipboard fallback for install-survival.
 *
 * Cloudflare Worker copies the canonical QR code to the user's
 * clipboard before redirecting to the App Store. On RegisterScreen
 * mount, the app reads the clipboard ONCE; if the contents look like a
 * QR-XXXXXX code, an explicit consent banner is shown before pre-fill.
 *
 * iOS 14+ shows a system clipboard-paste banner whenever an app reads
 * the clipboard — that is the intended privacy notice; do not try to
 * suppress it.
 *
 * Spec: docs/plans/2026-05-12-bundle-bcd-consolidated-design.md § 4.1
 *
 * Canonical QR alphabet (matches backend `_CODE_ALPHABET` in
 * `app/services/referral_service.py`):
 *   ABCDEFGHJKMNPQRSTUVWXYZ23456789 — no I, L, O, 0, 1.
 *
 * Same regex as backend `_QR_CODE_PATTERN` in
 * `app/services/attribution_service.py`.
 */
import * as Clipboard from 'expo-clipboard';

const QR_EXACT = /^QR-[A-HJ-NP-Z2-9]{6}$/;

export async function tryReadClipboardForInviteCode(): Promise<string | null> {
  try {
    const raw = (await Clipboard.getStringAsync()) ?? '';
    const trimmed = raw.trim();
    return QR_EXACT.test(trimmed) ? trimmed : null;
  } catch {
    return null;
  }
}
