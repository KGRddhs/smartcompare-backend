// Test mock for react-native-ssl-public-key-pinning.
// The real module reads NativeModules.SslPublicKeyPinning at import time,
// which is undefined under the node test runner — so any suite that
// transitively imports src/services/certificatePinning.ts (via api.ts ->
// authService.ts) crashes on load. This shim makes initializeSslPinning a
// safe async no-op (production already degrades gracefully when the native
// module is absent, e.g. Expo Go).
export const initializeSslPinning = async (
  _config?: Record<string, unknown>
): Promise<void> => {
  return;
};

export const isSslPinningAvailable = (): boolean => false;

export default {
  initializeSslPinning,
  isSslPinningAvailable,
};
