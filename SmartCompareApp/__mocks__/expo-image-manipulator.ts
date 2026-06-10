// Test mock for expo-image-manipulator.
// The real package ships untransformed ESM (`export { ... } from './...'`)
// which Jest's CJS runtime can't parse, so any test that transitively imports
// src/services/api.ts (JPEG transcoding) fails to load the suite. This shim
// gives the two surfaces api.ts uses — manipulateAsync + SaveFormat — as safe
// no-ops in node.
export const SaveFormat = {
  JPEG: 'jpeg',
  PNG: 'png',
  WEBP: 'webp',
} as const;

export const manipulateAsync = async (
  uri: string,
  _actions?: unknown,
  _options?: unknown
): Promise<{ uri: string; width: number; height: number }> => {
  return { uri, width: 0, height: 0 };
};

export default {
  SaveFormat,
  manipulateAsync,
};
