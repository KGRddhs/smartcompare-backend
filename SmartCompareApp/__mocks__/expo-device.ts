// Test mock for expo-device.
// Real package is untransformed ESM; provides only the surface
// src/services/deviceFingerprint.ts reads (osBuildId / osInternalBuildId).
export const osBuildId = 'TEST-BUILD-ID';
export const osInternalBuildId = 'TEST-INTERNAL-BUILD-ID';
export const modelName = 'Test Device';
export const isDevice = false;

export default {
  osBuildId,
  osInternalBuildId,
  modelName,
  isDevice,
};
