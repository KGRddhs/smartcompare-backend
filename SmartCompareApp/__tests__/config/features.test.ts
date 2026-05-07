/**
 * Feature flag config tests — Phase 2 Task 24.
 *
 * Frontend feature flags. Stays code-side default-OFF (matches the
 * backend convention per CLAUDE.md "all default OFF in code; flip in
 * Railway during canary"). Flipping happens via a build-time const swap
 * (or remote config when that lands later).
 */

import { features } from '../../src/config/features';

describe('feature flags', () => {
  it('exposes ENABLE_NEW_ONBOARDING', () => {
    expect(features).toHaveProperty('ENABLE_NEW_ONBOARDING');
  });

  it('defaults ENABLE_NEW_ONBOARDING to false (canary-safe)', () => {
    expect(features.ENABLE_NEW_ONBOARDING).toBe(false);
  });
});
