/**
 * Certificate Pinning -- pins Let's Encrypt intermediate SPKI hashes.
 *
 * We pin the INTERMEDIATE certs (E7 active primary, E8 + E5 as backups),
 * NOT the leaf cert. Leaf certs rotate every 90 days; intermediates are
 * stable for years.
 *
 * Bundle D device-leg hotfix (2026-05-25): Railway moved the leaf to
 * Let's Encrypt E7. E7 is now the ACTIVE intermediate signing the
 * `*.up.railway.app` leaf. E8 cross-signed cert is still served in the
 * chain but is not the active issuer. Pinning E7 unblocks ALL backend
 * HTTPS calls on the EAS preview build (network-error reports cleared).
 *
 * To extract current hashes (run if Railway changes CA):
 *   echo | openssl s_client -servername web-production-58776.up.railway.app \
 *     -connect web-production-58776.up.railway.app:443 -showcerts 2>/dev/null | \
 *     csplit -z -f /tmp/cert_ - '/-----BEGIN CERTIFICATE-----/' '{*}'
 *   openssl x509 -in /tmp/cert_01 -noout -pubkey | \
 *     openssl pkey -pubin -outform DER | openssl dgst -sha256 -binary | base64
 *
 * E7 hash verified 2026-05-25 via the command above by dispatcher.
 */
import { initializeSslPinning } from 'react-native-ssl-public-key-pinning';
import * as Sentry from '@sentry/react-native';

// Let's Encrypt intermediate SPKI SHA256 hashes (base64)
const LE_E7_INTERMEDIATE = 'y7xVm0TVJNahMr2sZydE2jQH8SquXV9yLF9seROHHHU=';
const LE_E8_INTERMEDIATE = 'iFvwVyJSxnQdyaUvUERIf+8qk7gRze3612JMwoO3zdU=';
const LE_E5_INTERMEDIATE = 'NYbU7PBwV4y9J67c4guWTki8FJ+uudrXL0a4V4aRcrg=';
// 2026-07-06: Railway rotated to LE intermediate YE1 (E5/E7/E8 no longer in chain) -> app bricked with Network Error; added YE1 + ISRG Root X2 (stable root, survives future intermediate rotations)
const LE_YE1_INTERMEDIATE = 'brzvtCELCIZUo4sD/qPX0ccRtPsd3DY6RfmxpOU9oB4=';
const ISRG_ROOT_X2 = 'diGVwiVYbubAI3RW4hB9xU8e/CH2GnkuvVFZE8zmgzI=';
// M18 MB-security-04 (2026-09-02): RSA-chain backup. Every pin above sits on
// Let's Encrypt's ECDSA family (ISRG Root X2 + YE1/E7/E8/E5); the RSA
// issuance path (R10-R14 intermediates -> ISRG Root X1) shares NONE of those
// keys, so an LE/Railway rotation to an RSA leaf would brick every pinned
// build — a repeat of the documented 2026-07-06 outage. Pinning BOTH ISRG
// roots covers every current LE issuance path. Hash derived offline from the
// certifi CA bundle (SubjectPublicKeyInfo DER -> SHA-256 -> base64); the
// derivation method was validated by reproducing ISRG_ROOT_X2 above
// byte-for-byte from the same bundle. Cross-checkable any time via the
// openssl runbook in this file's header against
// https://letsencrypt.org/certs/isrgrootx1.pem
const ISRG_ROOT_X1 = 'C5+lpZ7tcVwmwQIMcRtPbsQtWLABXhQzejna0wHFr8M=';

let pinningInitialized = false;

export async function setupCertificatePinning(): Promise<void> {
  if (pinningInitialized) return;

  try {
    await initializeSslPinning({
      'web-production-58776.up.railway.app': {
        includeSubdomains: true,
        publicKeyHashes: [
          ISRG_ROOT_X2,        // Stable root: ISRG Root X2 (survives future LE intermediate rotations)
          ISRG_ROOT_X1,        // Stable root: ISRG Root X1 (RSA-chain backup — covers an LE R10-R14 issuance, M18 MB-security-04)
          LE_YE1_INTERMEDIATE, // Primary: Let's Encrypt YE1 (current active issuer, issued by ISRG Root YE)
          LE_E7_INTERMEDIATE,  // Backup: Let's Encrypt E7 (legacy — no longer in chain 2026-07-06)
          LE_E8_INTERMEDIATE,  // Backup: Let's Encrypt E8 (legacy / cross-signed)
          LE_E5_INTERMEDIATE,  // Backup: Let's Encrypt E5 (legacy — no longer in chain 2026-07-06)
        ],
      },
    });
    pinningInitialized = true;
    if (__DEV__) console.log('[SECURITY] Certificate pinning initialized');
  } catch (error) {
    // Graceful degradation -- app works but without pinning protection.
    // In DEV this is the expected Expo Go case (native module absent).
    if (__DEV__) {
      console.warn('[SECURITY] Certificate pinning unavailable:', error);
    } else {
      // M18 MB-security-07 — in a RELEASE build this same path used to
      // swallow a genuine native init failure (misbuilt binary, native-side
      // error), leaving every session silently unpinned: console.* is
      // babel-stripped in production, so Sentry is the only channel that
      // makes an unpinned fleet visible. Fail-open behavior is unchanged.
      try {
        Sentry.captureMessage(
          '[SECURITY] Certificate pinning init failed - session is running unpinned',
          { level: 'warning', extra: { message: String(error) } },
        );
      } catch {
        // Telemetry must never break app boot.
      }
    }
  }
}
