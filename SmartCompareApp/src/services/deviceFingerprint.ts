// SmartCompareApp/src/services/deviceFingerprint.ts
//
// SHA-256 hex of a per-install SecureStore UUID (`device_fp_nonce`, lower-cased):
// stable across launches and OS updates. The Keychain item usually survives an
// iOS reinstall; Android clears it on uninstall (S81-08, A7 finding 12).
// Backend uses it to lock free-tier counters across re-signups on the
// same physical device. See Bundle A design §1.5.
//
// S81-08 CLIENT-FIRST-OTA (RULINGS_S81_08 R-S08-4 / R-S08-7 / R-S08-9 and
// GATE_S81_08 GC-1): getDeviceFingerprint() keeps its string contract and
// resolves the NEW value (no osBuildId); getDeviceIdentity() exposes the same
// hash with its source. When SecureStore throws, the iOS IDFV or the Android
// ANDROID_ID is hashed the same way as a fallback that is never cached and
// never persisted (the next call reads SecureStore again); with no fallback
// value the call rejects with the ORIGINAL SecureStore error.
// legacyDeviceFingerprintHash() is the build-3 composition
// (applicationId|osBuildId|nonce) byte for byte, with its own cache; it rides
// X-Device-Fingerprint-Legacy at register and the two social sign-ins only,
// and only before LEGACY_FINGERPRINT_HEADER_UNTIL_MS (the S81-08b reader
// matches stored rows on it there). One SecureStore read of the nonce serves
// both hashes.

import { Platform } from 'react-native';
import * as Application from 'expo-application';
import * as Device from 'expo-device';
import * as SecureStore from 'expo-secure-store';
import * as Crypto from 'expo-crypto';

const NONCE_KEY = 'device_fp_nonce';

/**
 * 2027-04-01 00:00 Asia/Riyadh (UTC+3). From this instant no code path reads
 * the legacy composition, so X-Device-Fingerprint-Legacy stops by itself even
 * if no later OTA removes it (R-S08-4, spec Q2).
 */
export const LEGACY_FINGERPRINT_HEADER_UNTIL_MS = Date.UTC(2027, 2, 31, 21, 0, 0);

/** Where the device id came from (R-S08-7 / GC-1). */
export type DeviceIdSource = 'securestore' | 'idfv' | 'android_id';

export interface DeviceIdentity {
  hash: string;
  source: DeviceIdSource;
}

let nonceMemo: string | null = null;
let nonceInflight: Promise<string> | null = null;
let cached: DeviceIdentity | null = null;
let inflight: Promise<DeviceIdentity> | null = null;
let legacyCached: string | null = null;
let legacyInflight: Promise<string> | null = null;

function sha256Hex(raw: string): Promise<string> {
  return Crypto.digestStringAsync(Crypto.CryptoDigestAlgorithm.SHA256, raw);
}

/** The id as hashed for X-Device-Fingerprint: trimmed and lower-cased (an iOS NSUUID is upper case). */
function stableHash(id: string): Promise<string> {
  return sha256Hex(id.trim().toLowerCase());
}

function nonEmpty(v: unknown): v is string {
  return typeof v === 'string' && v.trim() !== '';
}

/**
 * The SecureStore nonce, generated with Crypto.randomUUID() and persisted on
 * the first launch exactly as build 3 does. Memoised per process, so the new
 * and the legacy hash share ONE read; a failure memoises nothing (W3-3 C5: a
 * transient SecureStore rejection must never be replayed for the rest of the
 * process, so the next call reads SecureStore again).
 */
function readNonce(): Promise<string> {
  if (nonceMemo !== null) return Promise.resolve(nonceMemo);
  if (!nonceInflight) {
    nonceInflight = (async () => {
      let nonce = await SecureStore.getItemAsync(NONCE_KEY);
      if (!nonce) {
        nonce = Crypto.randomUUID();
        await SecureStore.setItemAsync(NONCE_KEY, nonce);
      }
      nonceMemo = nonce;
      return nonce;
    })().finally(() => {
      nonceInflight = null;
    });
  }
  return nonceInflight;
}

/**
 * The fallback when SecureStore throws: the iOS IDFV or the Android ANDROID_ID
 * (expo-application, linked since build 1), hashed like the nonce. Never
 * cached, never persisted; null when the platform offers none or it fails.
 */
async function fallbackIdentity(): Promise<DeviceIdentity | null> {
  try {
    if (Platform.OS === 'ios') {
      if (typeof Application.getIosIdForVendorAsync !== 'function') return null;
      const idfv = await Application.getIosIdForVendorAsync();
      return nonEmpty(idfv) ? { hash: await stableHash(idfv), source: 'idfv' } : null;
    }
    if (Platform.OS === 'android') {
      if (typeof Application.getAndroidId !== 'function') return null;
      const androidId = Application.getAndroidId();
      return nonEmpty(androidId) ? { hash: await stableHash(androidId), source: 'android_id' } : null;
    }
  } catch {
    // A failing fallback counts as none: the caller rethrows the SecureStore error.
  }
  return null;
}

async function computeIdentity(): Promise<DeviceIdentity> {
  let nonce: string;
  try {
    nonce = await readNonce();
  } catch (secureStoreError) {
    const fallback = await fallbackIdentity();
    if (fallback) return fallback;
    throw secureStoreError;
  }
  return { hash: await stableHash(nonce), source: 'securestore' };
}

/**
 * The device id and its source (R-S08-7 / GC-1). Only a SecureStore-derived
 * id is cached; concurrent calls share one read; a rejection is not replayed.
 */
export async function getDeviceIdentity(): Promise<DeviceIdentity> {
  if (cached) return { ...cached };
  if (!inflight) {
    inflight = computeIdentity()
      .then((identity) => {
        if (identity.source === 'securestore') cached = identity;
        return identity;
      })
      .finally(() => {
        inflight = null;
      });
  }
  const identity = await inflight;
  return { ...identity };
}

/** The X-Device-Fingerprint value (64 lower-case hex): the device id hash. */
export async function getDeviceFingerprint(): Promise<string> {
  return (await getDeviceIdentity()).hash;
}

/**
 * The build-3 value, byte for byte: SHA-256 hex of
 * `applicationId|osBuildId (or osInternalBuildId)|nonce` with the nonce as
 * stored. Read only while legacyFingerprintHeaderActive(), at register and the
 * two social sign-ins. Its own cache; no fallback (the build-3 value exists
 * only on the SecureStore path), so it rejects when SecureStore or the digest
 * fails, and the rejection is not replayed.
 */
export async function legacyDeviceFingerprintHash(): Promise<string> {
  if (legacyCached) return legacyCached;
  if (!legacyInflight) {
    legacyInflight = (async () => {
      const nonce = await readNonce();
      const raw = [
        Application.applicationId ?? '',
        Device.osBuildId ?? Device.osInternalBuildId ?? '',
        nonce,
      ].join('|');
      const hash = await sha256Hex(raw);
      legacyCached = hash;
      return hash;
    })().finally(() => {
      legacyInflight = null;
    });
  }
  return legacyInflight;
}

/** True while X-Device-Fingerprint-Legacy may still be sent (strictly before the cutoff). */
export function legacyFingerprintHeaderActive(nowMs: number = Date.now()): boolean {
  return nowMs < LEGACY_FINGERPRINT_HEADER_UNTIL_MS;
}

export function _resetCacheForTests() {
  nonceMemo = null;
  nonceInflight = null;
  cached = null;
  inflight = null;
  legacyCached = null;
  legacyInflight = null;
}
