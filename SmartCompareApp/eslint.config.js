// ESLint 9 flat config. Bundle A scope: enforce i18next/no-literal-string
// on user-visible JSX in src/screens + src/components so untranslated
// strings don't creep back in. Tests, theme/services/utils/types/config
// directories, generated types, native shims, and node_modules are ignored.

const expoConfig = require('eslint-config-expo/flat');
const i18next = require('eslint-plugin-i18next');

// Whitelist patterns merged with plugin defaults (digits, ALL-CAPS, html
// entities, emoji). Adds:
//   - punctuation/symbol/whitespace-only strings (·, ×, ✓, ←, —, ✦, etc.)
//     used as decorative glyphs between interpolations
//   - brand + copy-contract locked tokens (CLAUDE.md: "vs stays vs in
//     both locales"; "Qaren" / "قارن" = brand; "EN" / "عر" =
//     language self-labels in the in-app picker)
//
// String regex entries are treated by the plugin as case-sensitive
// non-unicode patterns wrapped with implicit anchors. RegExp instances
// pass through unchanged — required for unicode escapes (\p{...}/u).
const wordsExclude = [
  '[0-9!-/:-@[-`{-~]+',
  '[A-Z_-]+',
  /^[\p{P}\p{S}\p{Z}]+$/u,
  '^vs$',
  '^Qaren$',
  '^قارن$',
  '^عر$',
];

module.exports = [
  {
    ignores: [
      'node_modules/**',
      'android/**',
      'ios/**',
      '.expo/**',
      'dist/**',
      'build/**',
      'coverage/**',
      '**/*.d.ts',
      'babel.config.js',
      'jest.config.js',
      'metro.config.js',
      'eslint.config.js',
    ],
  },
  ...expoConfig,
  {
    files: ['src/screens/**/*.{ts,tsx}', 'src/components/**/*.{ts,tsx}'],
    plugins: { i18next: { rules: i18next.rules } },
    rules: {
      'i18next/no-literal-string': [
        'error',
        {
          mode: 'jsx-text-only',
          words: { exclude: wordsExclude },
        },
      ],
    },
  },
  {
    files: [
      '**/__tests__/**',
      '**/*.test.{ts,tsx}',
      '**/*.spec.{ts,tsx}',
      'src/i18n/**',
      'src/theme/**',
      'src/services/**',
      'src/utils/**',
      'src/types/**',
      'src/config/**',
      'src/hooks/**',
    ],
    rules: {
      'i18next/no-literal-string': 'off',
    },
  },
];
