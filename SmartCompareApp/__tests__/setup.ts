/**
 * Jest test setup
 * Runs before all tests
 */

import '@testing-library/jest-native/extend-expect';

// React Native sets `__DEV__` globally; replicate in the Jest env so app
// code that branches on it (e.g. dev-only console.warn calls) doesn't
// throw ReferenceError under the node test runner.
(globalThis as any).__DEV__ = false;

// Suppress console warnings during tests
const noop = () => {};
console.warn = noop as any;
console.error = noop as any;
