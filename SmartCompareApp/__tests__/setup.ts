/**
 * Jest test setup
 * Runs before all tests
 */

import '@testing-library/jest-native/extend-expect';

// Suppress console warnings during tests
const noop = () => {};
console.warn = noop as any;
console.error = noop as any;
