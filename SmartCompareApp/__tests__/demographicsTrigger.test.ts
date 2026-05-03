/**
 * Tests for the demographics-prompt trigger logic.
 *
 * Schedule (per design doc Section 5.5):
 *   - Sessions 1, 2, 3: show on each session until dismissed
 *   - After 3 dismissals: 7-day cooldown
 *   - 4th attempt after 7 days
 *   - Dismissed on 4th: never auto-prompt again
 *
 * Anything submitted (even all "Prefer not to say") permanently disables
 * the prompt.
 */

import {
  shouldShowDemographicsPrompt,
  COOLDOWN_DAYS,
  MAX_AUTO_ATTEMPTS,
} from '../src/services/demographicsTrigger';

const HOUR = 1000 * 60 * 60;
const DAY = HOUR * 24;

describe('shouldShowDemographicsPrompt', () => {
  it('does NOT show when user has submitted', () => {
    expect(
      shouldShowDemographicsPrompt({
        hasSubmitted: true,
        dismissedCount: 0,
        lastDismissedAt: null,
        currentSessionIndex: 1,
      })
    ).toBe(false);
  });

  it('shows on session 1 when nothing has happened yet', () => {
    expect(
      shouldShowDemographicsPrompt({
        hasSubmitted: false,
        dismissedCount: 0,
        lastDismissedAt: null,
        currentSessionIndex: 1,
      })
    ).toBe(true);
  });

  it('shows on session 2 after one dismissal', () => {
    expect(
      shouldShowDemographicsPrompt({
        hasSubmitted: false,
        dismissedCount: 1,
        lastDismissedAt: new Date(Date.now() - HOUR),
        currentSessionIndex: 2,
      })
    ).toBe(true);
  });

  it('shows on session 3 after two dismissals', () => {
    expect(
      shouldShowDemographicsPrompt({
        hasSubmitted: false,
        dismissedCount: 2,
        lastDismissedAt: new Date(Date.now() - HOUR),
        currentSessionIndex: 3,
      })
    ).toBe(true);
  });

  it('does NOT show on the same session it was just dismissed in', () => {
    expect(
      shouldShowDemographicsPrompt({
        hasSubmitted: false,
        dismissedCount: 2,
        lastDismissedAt: new Date(Date.now() - HOUR),
        currentSessionIndex: 2,
      })
    ).toBe(false);
  });

  it('after 3 dismissals: does NOT show until 7-day cooldown elapses', () => {
    const dismissedRecently = new Date(Date.now() - 3 * DAY);
    expect(
      shouldShowDemographicsPrompt({
        hasSubmitted: false,
        dismissedCount: 3,
        lastDismissedAt: dismissedRecently,
        currentSessionIndex: 4,
      })
    ).toBe(false);
  });

  it('after 3 dismissals + 7+ days: shows attempt #4', () => {
    const dismissedLongAgo = new Date(
      Date.now() - (COOLDOWN_DAYS + 1) * DAY
    );
    expect(
      shouldShowDemographicsPrompt({
        hasSubmitted: false,
        dismissedCount: 3,
        lastDismissedAt: dismissedLongAgo,
        currentSessionIndex: 5,
      })
    ).toBe(true);
  });

  it('after 4 dismissals: NEVER shows again', () => {
    const dismissedLongAgo = new Date(Date.now() - 90 * DAY);
    expect(
      shouldShowDemographicsPrompt({
        hasSubmitted: false,
        dismissedCount: MAX_AUTO_ATTEMPTS,
        lastDismissedAt: dismissedLongAgo,
        currentSessionIndex: 99,
      })
    ).toBe(false);
  });

  it('handles missing lastDismissedAt gracefully when dismissedCount > 0', () => {
    expect(
      shouldShowDemographicsPrompt({
        hasSubmitted: false,
        dismissedCount: 3,
        lastDismissedAt: null,
        currentSessionIndex: 4,
      })
    ).toBe(false);
  });

  it('exposes cooldown constant of 7 days', () => {
    expect(COOLDOWN_DAYS).toBe(7);
  });

  it('exposes max attempts constant of 4', () => {
    expect(MAX_AUTO_ATTEMPTS).toBe(4);
  });
});

describe('demographics state persistence (SecureStore)', () => {
  // expo-secure-store is mocked at module level via jest.config.js
  // moduleNameMapper -> __mocks__/expo-secure-store.ts
  const SecureStore = require('expo-secure-store');
  const {
    loadDemographicsState,
    recordDismissal,
    recordSubmission,
  } = require('../src/services/demographicsTrigger');

  beforeEach(() => {
    SecureStore.__reset();
  });

  it('loadDemographicsState returns defaults when nothing stored', async () => {
    const state = await loadDemographicsState();
    expect(state.hasSubmitted).toBe(false);
    expect(state.dismissedCount).toBe(0);
    expect(state.lastDismissedAt).toBeNull();
  });

  it('recordDismissal increments count and sets timestamp', async () => {
    await recordDismissal();
    const state = await loadDemographicsState();
    expect(state.dismissedCount).toBe(1);
    expect(state.lastDismissedAt).toBeInstanceOf(Date);
  });

  it('recordSubmission sets hasSubmitted permanently', async () => {
    await recordSubmission();
    const state = await loadDemographicsState();
    expect(state.hasSubmitted).toBe(true);
  });

  it('multiple dismissals accumulate', async () => {
    await recordDismissal();
    await recordDismissal();
    await recordDismissal();
    const state = await loadDemographicsState();
    expect(state.dismissedCount).toBe(3);
  });

  it('recordSubmission preserves prior dismissed count', async () => {
    await recordDismissal();
    await recordDismissal();
    await recordSubmission();
    const state = await loadDemographicsState();
    expect(state.hasSubmitted).toBe(true);
    expect(state.dismissedCount).toBe(2);
  });
});
