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

// B.1 F3.5 — screenshot detection. Tests that need to simulate a screenshot
// override this via jest.mock to capture the registered listener. The default
// no-op returns a removable subscription so production effect cleanup is safe.
export const addScreenshotListener = (
  _listener: () => void
): { remove: () => void } => {
  return { remove: () => {} };
};

export default {
  usePreventScreenCapture,
  preventScreenCaptureAsync,
  allowScreenCaptureAsync,
  addScreenshotListener,
};
