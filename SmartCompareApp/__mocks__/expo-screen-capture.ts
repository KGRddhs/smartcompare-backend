// Test mock for expo-screen-capture.
// Real package is ESM and isn't transformed by ts-jest under the current
// preset on Windows. Tests don't need to actually prevent capture; the
// hook/function calls just need to be safe no-ops in node.
export const usePreventScreenCapture = (): void => {
  // no-op
};

export const preventScreenCaptureAsync = async (): Promise<void> => {
  return;
};

export const allowScreenCaptureAsync = async (): Promise<void> => {
  return;
};

export default {
  usePreventScreenCapture,
  preventScreenCaptureAsync,
  allowScreenCaptureAsync,
};
