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
  },
  setupFilesAfterEnv: ['<rootDir>/__tests__/setup.ts'],
};
