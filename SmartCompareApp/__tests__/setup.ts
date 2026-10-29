/**
 * Jest test setup
 * Runs before all tests
 */

import '@testing-library/jest-native/extend-expect';

// React Native sets `__DEV__` globally; replicate in the Jest env so app
// code that branches on it (e.g. dev-only console.warn calls) doesn't
// throw ReferenceError under the node test runner.
(globalThis as any).__DEV__ = false;

// S69 U3 — the AI-processing consent gate defaults to "granted" in every
// suite, so a suite that dispatches a compare keeps its synchronous
// dispatch and never meets the sheet. The consent suite
// (__tests__/consent/aiProcessingConsent.s69.test.tsx) maps the module back
// to the real implementation.
jest.mock('../src/services/aiConsent', () => {
  const mockConsent: Record<string, any> = {
    __esModule: true,
    AI_CONSENT_VERSION: 2,
    AI_CONSENT_KEY_PREFIX: '@qaren_ai_consent_',
    aiConsentStorageKey: (userId: string) => `@qaren_ai_consent_${userId}`,
    readAiConsent: jest.fn(async () => null),
    hasCurrentAiConsent: jest.fn(async () => true),
    // S81-08 fix round 1 (RULINGS_FIX1_S81_08 F1-3): the request-path read
    // answers what the mocked hasCurrentAiConsent answers for that user (no
    // user: false), so requestContext carries no jest-only fallback.
    hasCurrentAiConsentForRequest: jest.fn(async (userId: string | null) =>
      userId ? mockConsent.hasCurrentAiConsent(userId) : false,
    ),
    recordAiConsent: jest.fn(async () => undefined),
    clearAiConsent: jest.fn(async () => undefined),
    ensureAiConsent: jest.fn(async () => true),
    useAiConsentGate: () => ({
      withAiConsent: (action: () => void) => action(),
      sheetProps: {
        visible: false,
        busy: false,
        onAgree: () => undefined,
        onNotNow: () => undefined,
        onOpenPrivacy: () => undefined,
        onDismiss: () => undefined,
      },
    }),
  };
  return mockConsent;
});

// Suppress console warnings during tests
const noop = () => {};
console.warn = noop as any;
console.error = noop as any;
