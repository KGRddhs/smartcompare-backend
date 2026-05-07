// Test mock for expo-font.
// In production, expo-font ships with the Expo SDK and exposes useFonts +
// loadAsync. Jest runs under node, so we stub the module: useFonts always
// returns [loaded=true, error=null], and loadAsync is a no-op promise.

export const useFonts = (_map: Record<string, unknown>): [boolean, Error | null] => [true, null];

export const loadAsync = async (_map: Record<string, unknown>): Promise<void> => {
  return;
};

export const isLoaded = (_name: string): boolean => true;
export const isLoading = (_name: string): boolean => false;
export default { useFonts, loadAsync, isLoaded, isLoading };
