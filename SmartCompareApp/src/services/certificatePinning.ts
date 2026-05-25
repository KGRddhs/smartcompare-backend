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

// Let's Encrypt intermediate SPKI SHA256 hashes (base64)
const LE_E7_INTERMEDIATE = 'y7xVm0TVJNahMr2sZydE2jQH8SquXV9yLF9seROHHHU=';
const LE_E8_INTERMEDIATE = 'iFvwVyJSxnQdyaUvUERIf+8qk7gRze3612JMwoO3zdU=';
const LE_E5_INTERMEDIATE = 'NYbU7PBwV4y9J67c4guWTki8FJ+uudrXL0a4V4aRcrg=';

let pinningInitialized = false;

export async function setupCertificatePinning(): Promise<void> {
  if (pinningInitialized) return;

  try {
    await initializeSslPinning({
      'web-production-58776.up.railway.app': {
        includeSubdomains: true,
        publicKeyHashes: [
          LE_E7_INTERMEDIATE,  // Primary: Let's Encrypt E7 (current active issuer)
          LE_E8_INTERMEDIATE,  // Backup: Let's Encrypt E8 (legacy / cross-signed)
          LE_E5_INTERMEDIATE,  // Backup: Let's Encrypt E5
        ],
      },
    });
    pinningInitialized = true;
    if (__DEV__) console.log('[SECURITY] Certificate pinning initialized');
  } catch (error) {
    // Graceful degradation -- app works but without pinning protection
    // This is expected in Expo Go where native modules aren't available
    if (__DEV__) console.warn('[SECURITY] Certificate pinning unavailable:', error);
  }
}
