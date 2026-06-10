// Test mock for expo-application.
// Real package is untransformed ESM; provides only the surface
// src/services/deviceFingerprint.ts reads (applicationId). Stable test value
// so device-fingerprint hashing is deterministic under the node runner.
export const applicationId = 'com.qaren.test';
export const nativeApplicationVersion = '1.0.0';
export const nativeBuildVersion = '1';

export default {
  applicationId,
  nativeApplicationVersion,
  nativeBuildVersion,
};
