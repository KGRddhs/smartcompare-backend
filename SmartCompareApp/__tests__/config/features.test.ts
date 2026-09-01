/**
 * Feature flag config tests — Tasks 24 + 47.
 *
 * As of Task 47 (canary 10%), `features.ENABLE_NEW_ONBOARDING` is a
 * GETTER that reads `CANARY_NEW_ONBOARDING_PERCENT` and the stable id
 * set via `setFlagStableId()`. Default behavior (no id set) returns
 * false — canary-safe — even at non-zero percent.
 */

import {
  features,
  setFlagStableId,
  _resetFlagStableIdForTests,
  CANARY_NEW_ONBOARDING_PERCENT,
} from '../../src/config/features';

describe('feature flags', () => {
  beforeEach(() => {
    _resetFlagStableIdForTests();
  });

  it('exposes ENABLE_NEW_ONBOARDING', () => {
    expect(features).toHaveProperty('ENABLE_NEW_ONBOARDING');
  });

  it('returns false when no stable id is set (canary-safe default)', () => {
    expect(features.ENABLE_NEW_ONBOARDING).toBe(false);
  });

  it('CANARY_NEW_ONBOARDING_PERCENT is in [0, 100] range', () => {
    expect(CANARY_NEW_ONBOARDING_PERCENT).toBeGreaterThanOrEqual(0);
    expect(CANARY_NEW_ONBOARDING_PERCENT).toBeLessThanOrEqual(100);
  });

  it('returns deterministic boolean once a stable id is set', () => {
    setFlagStableId('user-stable-test-id');
    const first = features.ENABLE_NEW_ONBOARDING;
    // Read 10× — getter must be pure.
    for (let i = 0; i < 10; i++) {
      expect(features.ENABLE_NEW_ONBOARDING).toBe(first);
    }
  });
});

describe('#118 — ENABLE_EXPO_FETCH_SSE (SSE transport rollout knob)', () => {
  // require + optional-call so these cases are meaningfully RED (undefined
  // !== false) rather than import-broken at the pre-#118 base.
  const featuresModule = require('../../src/config/features');

  afterEach(() => {
    featuresModule._setExpoFetchSseForTests?.(null);
  });

  it('ENABLE_EXPO_FETCH_SSE defaults to false (Option B: single REST compare)', () => {
    expect((features as any).ENABLE_EXPO_FETCH_SSE).toBe(false);
  });

  it('ENABLE_EXPO_FETCH_SSE is a getter that re-reads its constant', () => {
    const desc = Object.getOwnPropertyDescriptor(features, 'ENABLE_EXPO_FETCH_SSE');
    expect(typeof desc?.get).toBe('function');
    // Getter is pure across repeated reads.
    const first = (features as any).ENABLE_EXPO_FETCH_SSE;
    for (let i = 0; i < 10; i++) {
      expect((features as any).ENABLE_EXPO_FETCH_SSE).toBe(first);
    }
    // Test override flips the read; clearing it restores the default.
    featuresModule._setExpoFetchSseForTests?.(true);
    expect((features as any).ENABLE_EXPO_FETCH_SSE).toBe(true);
    featuresModule._setExpoFetchSseForTests?.(null);
    expect((features as any).ENABLE_EXPO_FETCH_SSE).toBe(false);
  });
});
