// Test mock for expo-crypto.
// Real package is ESM and isn't transformed by ts-jest under the current
// preset on Windows. Tests don't need real cryptographic randomness; a
// deterministic stub is fine for the canary-bucket use case (uniqueness
// is provided by the test itself when needed via per-test injection).
let _counter = 0;
export const randomUUID = (): string => {
  _counter += 1;
  // 8-4-4-4-12 hex layout; the per-call counter keeps it unique within
  // a test run while staying deterministic.
  const hex = _counter.toString(16).padStart(12, '0');
  return `00000000-0000-0000-0000-${hex}`;
};

export default { randomUUID };
