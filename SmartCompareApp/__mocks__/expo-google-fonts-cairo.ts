// Test mock for @expo-google-fonts/cairo. Real package is ESM and isn't
// transformed by ts-jest under the current preset on Windows. We don't
// need to load actual font files in node tests.
export const useFonts = (_map: Record<string, unknown>): [boolean, Error | null] => [true, null];
export const Cairo_400Regular = 'Cairo_400Regular';
export const Cairo_600SemiBold = 'Cairo_600SemiBold';
export const Cairo_700Bold = 'Cairo_700Bold';
