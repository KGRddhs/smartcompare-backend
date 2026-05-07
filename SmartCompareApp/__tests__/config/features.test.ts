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
