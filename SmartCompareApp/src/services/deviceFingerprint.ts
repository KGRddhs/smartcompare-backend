// SmartCompareApp/src/services/deviceFingerprint.ts
//
// SHA-256 hash that's stable across launches but resets on uninstall.
// Backend uses it to lock free-tier counters across re-signups on the
// same physical device. See Bundle A design §1.5.

import * as Application from 'expo-application';
import * as Device from 'expo-device';
import * as SecureStore from 'expo-secure-store';
import * as Crypto from 'expo-crypto';

const NONCE_KEY = 'device_fp_nonce';

let cached: string | null = null;
let inflight: Promise<string> | null = null;

export async function getDeviceFingerprint(): Promise<string> {
  if (cached) return cached;
  if (inflight) return inflight;

  inflight = (async () => {
    let nonce = await SecureStore.getItemAsync(NONCE_KEY);
    if (!nonce) {
      nonce = Crypto.randomUUID();
      await SecureStore.setItemAsync(NONCE_KEY, nonce);
    }
    const raw = [
      Application.applicationId ?? '',
      Device.osBuildId ?? Device.osInternalBuildId ?? '',
      nonce,
    ].join('|');
    const hash = await Crypto.digestStringAsync(
      Crypto.CryptoDigestAlgorithm.SHA256,
      raw,
    );
    cached = hash;
    inflight = null;
    return hash;
  })();

  return inflight;
}

export function _resetCacheForTests() {
  cached = null;
  inflight = null;
}
