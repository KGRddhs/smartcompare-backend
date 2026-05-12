/**
 * Smoke tests for root navigation registration.
 *
 * Asserts that the ScanCamera modal route + its underlying types are
 * wired into the root stack — see plan Task 1.8.
 */
import type { RootStackParamList } from '../src/types/types';

describe('Root stack types', () => {
  it('declares a ScanCamera entry in RootStackParamList', () => {
    // Compile-time guarantee — fails the TS build if the key is missing.
    const route: keyof RootStackParamList = 'ScanCamera';
    expect(route).toBe('ScanCamera');
  });
});
