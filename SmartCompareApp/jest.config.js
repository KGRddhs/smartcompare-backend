module.exports = {
  preset: 'ts-jest',
  testEnvironment: 'node',
  testMatch: ['**/__tests__/**/*.test.ts', '**/__tests__/**/*.test.tsx'],
  moduleFileExtensions: ['ts', 'tsx', 'js', 'jsx', 'json'],
  globals: {
    'ts-jest': {
      tsconfig: {
        jsx: 'react',
      },
      isolatedModules: true,
    },
  },
  transformIgnorePatterns: [
    'node_modules/(?!(@expo-google-fonts|expo-localization|@react-native-async-storage|react-native|@react-native|lucide-react-native|react-i18next|i18next|expo-haptics|expo-image|react-native-reanimated)/)',
  ],
  moduleNameMapper: {
    '^react-native$': '<rootDir>/__mocks__/react-native.ts',
    '^react-native-reanimated$': '<rootDir>/__mocks__/react-native-reanimated.ts',
    '^lucide-react-native$': '<rootDir>/__mocks__/lucide-react-native.ts',
    '^react-i18next$': '<rootDir>/__mocks__/react-i18next.ts',
    '^@react-native-async-storage/async-storage$': '<rootDir>/__mocks__/async-storage.ts',
    '^expo-secure-store$': '<rootDir>/__mocks__/expo-secure-store.ts',
    '^expo-screen-capture$': '<rootDir>/__mocks__/expo-screen-capture.ts',
    // expo-image-manipulator ships untransformed ESM; any suite that
    // transitively imports src/services/api.ts (JPEG transcoding) fails to
    // load without this shim. B.1 F3.6.
    '^expo-image-manipulator$': '<rootDir>/__mocks__/expo-image-manipulator.ts',
    // react-native-ssl-public-key-pinning reads a native module at import
    // time; no-op shim so suites importing certificatePinning.ts load. B.1 F3.6.
    '^react-native-ssl-public-key-pinning$':
      '<rootDir>/__mocks__/react-native-ssl-public-key-pinning.ts',
    '^expo-clipboard$': '<rootDir>/__mocks__/expo-clipboard.ts',
    '^expo-haptics$': '<rootDir>/__mocks__/expo-haptics.ts',
    '^expo-crypto$': '<rootDir>/__mocks__/expo-crypto.ts',
    // expo-application + expo-device ship untransformed ESM; shimmed so
    // suites importing deviceFingerprint.ts (via authService.ts) load. B.1 F3.6.
    '^expo-application$': '<rootDir>/__mocks__/expo-application.ts',
    '^expo-device$': '<rootDir>/__mocks__/expo-device.ts',
    // expo-notifications ships untransformed ESM (imports from 'expo'); shimmed
    // so suites importing Step17Notifications.tsx / OnboardingFlow.tsx load. B.1 F3.6.
    '^expo-notifications$': '<rootDir>/__mocks__/expo-notifications.ts',
    '^expo-font$': '<rootDir>/__mocks__/expo-font.ts',
    '^@expo-google-fonts/cairo$': '<rootDir>/__mocks__/expo-google-fonts-cairo.ts',
    '^react-native-svg$': '<rootDir>/__mocks__/react-native-svg.ts',
    // Lane A-L3 Task L3.7 — stub @sentry/react-native. Published ESM
    // re-exports from @sentry/core which Jest CJS can't parse; tests
    // get a quiet no-op shim. Tests asserting Sentry behavior override
    // via per-file `jest.mock('@sentry/react-native', ...)`.
    '^@sentry/react-native$': '<rootDir>/__mocks__/sentry-react-native.ts',
    '\\.(ttf|otf|woff2?|png|jpg)$': '<rootDir>/__mocks__/fileStub.ts',
  },
  setupFilesAfterEnv: ['<rootDir>/__tests__/setup.ts'],
};
