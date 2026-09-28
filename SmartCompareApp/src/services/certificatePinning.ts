/**
 * Certificate Pinning -- pins Let's Encrypt SPKI hashes for the backend host.
 *
 * We pin ROOTS and INTERMEDIATES, never the leaf (leaves rotate every ~90
 * days). A request passes when ANY certificate in the chain the DEVICE's trust
 * check builds (it ends at a root the phone trusts, which may differ from what
 * the server sends) matches ANY pin, so the set below is deliberately wide:
 * both ISRG root families plus every Gen-Y Let's Encrypt intermediate (the
 * 2024-generation E6/E9 and R10-R14 intermediates are covered only through
 * the ISRG Root X1/X2 pins).
 *
 * LIVE CHAIN, measured 2026-09-29 (openssl s_client -showcerts):
 *   leaf *.up.railway.app  <-  Let's Encrypt YE2  <-  ISRG Root YE  <-  ISRG Root X2
 * Before session 69 U5 only the ISRG Root X2 pin (or X1, on a device that ends
 * the chain there) matched (YE1, the pinned "primary", is no longer served).
 * Once a phone trusts ISRG Root YE directly, path building can stop at Root YE
 * and leave X2 out -- with the old pin set every backend call would then fail
 * with a network error on the App Store binary, a repeat of the 2026-07-06
 * outage. YE2 and Root YE (plus the rest of the Gen-Y family: YE1/YE3, YR1-3,
 * Root YR) are now pinned.
 *
 * History: 2026-05-25 Railway moved the leaf to E7; 2026-07-06 rotation to
 * YE1 bricked the preview build (E5/E7/E8 gone) -> YE1 + ISRG Root X2 added;
 * 2026-09-02 (M18 MB-security-04) ISRG Root X1 added as the RSA-chain backup.
 *
 * To re-derive the hashes (run whenever Railway or Let's Encrypt rotates):
 *   echo | openssl s_client -servername web-production-58776.up.railway.app \
 *     -connect web-production-58776.up.railway.app:443 -showcerts 2>/dev/null | \
 *     csplit -z -f /tmp/cert_ - '/-----BEGIN CERTIFICATE-----/' '{*}'
 *   # cert_00 is the s_client preamble and cert_01 is the LEAF (never pinned);
 *   # the intermediates and roots start at cert_02:
 *   for c in /tmp/cert_0[2-9]; do openssl x509 -in "$c" -noout -subject; \
 *     openssl x509 -in "$c" -noout -pubkey | openssl pkey -pubin -outform DER | \
 *     openssl dgst -sha256 -binary | base64; done
 * The Gen-Y PEMs are published at https://letsencrypt.org/certificates/
 * (certs/gen-y/int-ye1.pem ... root-yr.pem); every Gen-Y hash below was
 * derived from those PEMs; YE2, Root YE, X2 and X1 were also cross-checked
 * against the live chain (the other Gen-Y hashes are not in today's chain and
 * can only be checked against the published PEMs).
 *
 * A pin MISMATCH is reported to Sentry through addSslPinningErrorListener
 * (session 69 U5): before, a wrong pin set was invisible until users reported
 * "Network Error".
 */
import {
  addSslPinningErrorListener,
  initializeSslPinning,
} from 'react-native-ssl-public-key-pinning';
import * as Sentry from '@sentry/react-native';

// SPKI SHA-256 hashes (base64). Derived per the runbook in the header.
// --- ISRG roots (both families) -------------------------------------------
const ISRG_ROOT_X2 = 'diGVwiVYbubAI3RW4hB9xU8e/CH2GnkuvVFZE8zmgzI='; // ECDSA root, cross-signed by X1
const ISRG_ROOT_X1 = 'C5+lpZ7tcVwmwQIMcRtPbsQtWLABXhQzejna0wHFr8M='; // RSA root (M18 MB-security-04)
const ISRG_ROOT_YE = 'sCkq5UWXjg+7mKu9lMhhYF5bGLsy7VI/UNW3tccdR7w='; // Gen-Y ECDSA root, in the LIVE chain 2026-09-29
const ISRG_ROOT_YR = 'fk6IOKit1ild5647BH06ujSIq5XbCgqlbYl6ANhhi88='; // Gen-Y RSA root
// --- Let's Encrypt Gen-Y intermediates (2026 -> 2028) -----------------------
const LE_YE2_INTERMEDIATE = 's/tdAOmUzd8syaTuqfgGvFcn6DzA5Cmb+Vby1ST+U3Y='; // CURRENT issuer of the *.up.railway.app leaf (2026-09-29)
const LE_YE1_INTERMEDIATE = 'brzvtCELCIZUo4sD/qPX0ccRtPsd3DY6RfmxpOU9oB4='; // issuer 2026-07-06 .. before 2026-09-29
const LE_YE3_INTERMEDIATE = 'ppiiCCS+BOR6GjPE+kiHMb6SAR8jox6QDiyibJwqz84=';
const LE_YR1_INTERMEDIATE = 'LoMHBotttiDko50Gi13uXW71eIy7LAttI+rYT8wXF4w=';
const LE_YR2_INTERMEDIATE = 'nWN7PSep5XDQdge5zK24CnCRXHr3KvzhKEGxsdqCX9E=';
const LE_YR3_INTERMEDIATE = 'UaqofZhLVZrGnpKfiIoCLYMuCJ/026CkErUQG8pLx5k=';
// --- Legacy 2024-generation intermediates (kept: additive set) ---------------
const LE_E7_INTERMEDIATE = 'y7xVm0TVJNahMr2sZydE2jQH8SquXV9yLF9seROHHHU=';
const LE_E8_INTERMEDIATE = 'iFvwVyJSxnQdyaUvUERIf+8qk7gRze3612JMwoO3zdU=';
const LE_E5_INTERMEDIATE = 'NYbU7PBwV4y9J67c4guWTki8FJ+uudrXL0a4V4aRcrg=';

const BACKEND_HOST = 'web-production-58776.up.railway.app';

export const BACKEND_PUBLIC_KEY_HASHES: readonly string[] = [
  ISRG_ROOT_X2,
  ISRG_ROOT_X1,
  ISRG_ROOT_YE,
  ISRG_ROOT_YR,
  LE_YE2_INTERMEDIATE,
  LE_YE1_INTERMEDIATE,
  LE_YE3_INTERMEDIATE,
  LE_YR1_INTERMEDIATE,
  LE_YR2_INTERMEDIATE,
  LE_YR3_INTERMEDIATE,
  LE_E7_INTERMEDIATE,
  LE_E8_INTERMEDIATE,
  LE_E5_INTERMEDIATE,
];

let pinningInitialized = false;
// Session 69 U5: one Sentry event per session for a pin mismatch. During a real
// rotation outage every backend request on every device would otherwise emit
// an event, and Sentry's default dedupe only drops identical back-to-back
// events.
let pinMismatchReported = false;

export async function setupCertificatePinning(): Promise<void> {
  if (pinningInitialized) return;

  try {
    await initializeSslPinning({
      [BACKEND_HOST]: {
        includeSubdomains: true,
        publicKeyHashes: [...BACKEND_PUBLIC_KEY_HASHES],
      },
    });
    pinningInitialized = true;
    if (__DEV__) console.log('[SECURITY] Certificate pinning initialized');
    // Session 69 U5: a pin mismatch used to be silent (the request just failed
    // with "Network Error"). Report it so a rotation is visible in Sentry
    // before users report it. Registered only after a successful init; the
    // listener itself must never break boot.
    try {
      addSslPinningErrorListener((event) => {
        try {
          if (pinMismatchReported) return;
          pinMismatchReported = true;
          // iOS sends only { serverHostname }; Android adds OkHttp's message.
          Sentry.captureMessage('[SECURITY] Certificate pin mismatch - backend call rejected', {
            level: 'error',
            fingerprint: ['cert-pin-mismatch'],
            extra: { serverHostname: event?.serverHostname, message: String(event?.message ?? '') },
          });
        } catch {
          // Telemetry must never throw inside the native callback.
        }
      });
    } catch {
      // An older native module without the listener is not an init failure.
    }
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
