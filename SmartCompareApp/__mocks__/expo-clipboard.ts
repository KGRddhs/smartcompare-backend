/**
 * Global expo-clipboard mock for the jest test environment.
 *
 * Tests that need specific behavior (returning a code, throwing, etc.)
 * should still wire a per-test jest.mock(...) factory to override these
 * defaults. This file exists so unrelated tests that transitively pull
 * in `clipboardFallbackService` (which imports `* as Clipboard from
 * 'expo-clipboard'`) don't blow up on the ES-module syntax error from
 * the real package not being transformable.
 */
export const getStringAsync = jest.fn(async () => '');
export const setStringAsync = jest.fn(async () => true);
export const hasStringAsync = jest.fn(async () => false);
