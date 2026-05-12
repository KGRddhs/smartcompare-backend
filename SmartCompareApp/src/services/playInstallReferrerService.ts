/**
 * Android Play Install Referrer reader.
 *
 * On first launch after a Play Store install, the OS preserves the
 * referrer=QR-XXXXXX query parameter that the Cloudflare Worker added
 * to the Play Store URL. This service reads it once via the Play
 * Install Referrer API, parses the canonical QR code, and returns it.
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
import { Platform } from 'react-native';

const QR_BODY = '[A-HJ-NP-Z2-9]{6}';
const QR_BARE = new RegExp(`^QR-${QR_BODY}$`);
const QR_IN_QUERY = new RegExp(`(?:^|[?&])referrer=(QR-${QR_BODY})(?:&|$)`);

export async function tryReadPlayInstallReferrer(): Promise<string | null> {
  if (Platform.OS !== 'android') return null;

  let mod: any;
  try {
    mod = require('react-native-play-install-referrer');
  } catch {
    return null;
  }

  return new Promise((resolve) => {
    try {
      mod.PlayInstallReferrer.getInstallReferrerInfo((info: any, err: any) => {
        if (err || !info) return resolve(null);
        const raw: string = (info.installReferrer || '').trim();
        if (!raw) return resolve(null);

        const queryMatch = QR_IN_QUERY.exec(raw);
        if (queryMatch) return resolve(queryMatch[1]);

        if (QR_BARE.test(raw)) return resolve(raw);

        resolve(null);
      });
    } catch {
      resolve(null);
    }
  });
}
