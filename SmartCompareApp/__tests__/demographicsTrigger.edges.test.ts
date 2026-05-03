/**
 * Edge cases for demographics trigger logic + state persistence.
 *
 * Covers race conditions, malformed stored state, and interaction
 * between submission and dismissal counts.
 */

import {
  shouldShowDemographicsPrompt,
  loadDemographicsState,
  recordDismissal,
  recordSubmission,
  _resetDemographicsState,
  COOLDOWN_DAYS,
  MAX_AUTO_ATTEMPTS,
} from '../src/services/demographicsTrigger';

const SecureStore = require('expo-secure-store');

const HOUR = 1000 * 60 * 60;
const DAY = HOUR * 24;

describe('shouldShowDemographicsPrompt — edge schedule cases', () => {
  it('shows when cooldown is exactly 7 days (boundary)', () => {
    const exactly7Days = new Date(Date.now() - COOLDOWN_DAYS * DAY);
    expect(
      shouldShowDemographicsPrompt({
        hasSubmitted: false,
        dismissedCount: 3,
        lastDismissedAt: exactly7Days,
        currentSessionIndex: 4,
      })
    ).toBe(true);
  });

  it('does NOT show when cooldown is 1ms short of 7 days (boundary)', () => {
    const justUnder7Days = new Date(Date.now() - COOLDOWN_DAYS * DAY + 1);
    expect(
      shouldShowDemographicsPrompt({
        hasSubmitted: false,
        dismissedCount: 3,
        lastDismissedAt: justUnder7Days,
        currentSessionIndex: 4,
      })
    ).toBe(false);
  });

  it('handles future-dated lastDismissedAt (clock skew) — does NOT show', () => {
    const future = new Date(Date.now() + 30 * DAY);
    expect(
      shouldShowDemographicsPrompt({
        hasSubmitted: false,
        dismissedCount: 3,
        lastDismissedAt: future,
        currentSessionIndex: 4,
      })
    ).toBe(false);
  });

  it('hasSubmitted overrides everything — even when dismissed counter is 0', () => {
    expect(
      shouldShowDemographicsPrompt({
        hasSubmitted: true,
        dismissedCount: 0,
        lastDismissedAt: null,
        currentSessionIndex: 100,
      })
    ).toBe(false);
  });

  it('dismissedCount = MAX even with old lastDismissedAt — never shows', () => {
    const yearAgo = new Date(Date.now() - 365 * DAY);
    expect(
      shouldShowDemographicsPrompt({
        hasSubmitted: false,
        dismissedCount: MAX_AUTO_ATTEMPTS,
        lastDismissedAt: yearAgo,
        currentSessionIndex: 50,
      })
    ).toBe(false);
  });

  it('dismissedCount > MAX (defensive) — never shows', () => {
    expect(
      shouldShowDemographicsPrompt({
        hasSubmitted: false,
        dismissedCount: MAX_AUTO_ATTEMPTS + 5,
        lastDismissedAt: new Date(),
        currentSessionIndex: 99,
      })
    ).toBe(false);
  });
});

describe('demographicsTrigger persistence — edge cases', () => {
  beforeEach(() => {
    SecureStore.__reset();
  });

  it('handles malformed JSON in storage — returns defaults', async () => {
    await SecureStore.setItemAsync(
      'qaren.demographicsPromptState.v1',
      'this is not valid json {'
    );
    const state = await loadDemographicsState();
    expect(state.hasSubmitted).toBe(false);
    expect(state.dismissedCount).toBe(0);
    expect(state.lastDismissedAt).toBeNull();
  });

  it('handles partial JSON missing fields — uses defaults for absent keys', async () => {
    await SecureStore.setItemAsync(
      'qaren.demographicsPromptState.v1',
      JSON.stringify({ hasSubmitted: true })
    );
    const state = await loadDemographicsState();
    expect(state.hasSubmitted).toBe(true);
    expect(state.dismissedCount).toBe(0);
    expect(state.lastDismissedAt).toBeNull();
  });

  it('round-trips lastDismissedAt as Date object (not ISO string)', async () => {
    await recordDismissal();
    const state = await loadDemographicsState();
    expect(state.lastDismissedAt).toBeInstanceOf(Date);
    if (state.lastDismissedAt) {
      const ageMs = Date.now() - state.lastDismissedAt.getTime();
      expect(ageMs).toBeLessThan(5000); // recorded "just now"
      expect(ageMs).toBeGreaterThanOrEqual(0);
    }
  });

  it('_resetDemographicsState clears all state', async () => {
    await recordDismissal();
    await recordSubmission();
    await _resetDemographicsState();
    const state = await loadDemographicsState();
    expect(state.hasSubmitted).toBe(false);
    expect(state.dismissedCount).toBe(0);
    expect(state.lastDismissedAt).toBeNull();
  });

  it('recordDismissal twice in immediate succession produces count=2', async () => {
    await recordDismissal();
    await recordDismissal();
    const state = await loadDemographicsState();
    expect(state.dismissedCount).toBe(2);
  });

  it('recordSubmission then recordDismissal does NOT clear hasSubmitted', async () => {
    await recordSubmission();
    await recordDismissal();
    const state = await loadDemographicsState();
    expect(state.hasSubmitted).toBe(true);
    expect(state.dismissedCount).toBe(1);
  });
});
