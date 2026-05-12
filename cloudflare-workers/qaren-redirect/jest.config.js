module.exports = {
  preset: 'ts-jest',
  testEnvironment: 'node',
  testMatch: ['**/__tests__/**/*.test.ts'],
  globals: {
    'ts-jest': {
      tsconfig: {
        target: 'ES2022',
        module: 'CommonJS',
        moduleResolution: 'Node',
        esModuleInterop: true,
      },
      isolatedModules: true,
    },
  },
};
