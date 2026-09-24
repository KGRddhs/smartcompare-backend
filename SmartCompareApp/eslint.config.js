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

// W3-11 RTL-09 — under mode:'jsx-text-only' the i18next plugin skips any
// node whose DIRECT parent is not a JSXElement/JSXFragment, so user-visible
// literals in attributes, setError(...) and Alert.alert(...) were invisible
// (measured: 0 messages while accessibilityLabel="Back", 'N/A', ... shipped).
// These child-combinator selectors see exactly those shapes; `t('key')`
// arguments, `{ defaultValue }` and `{ style: 'cancel' }` are children of a
// `t` call / ObjectExpression and never match. `label="English"` is the
// language picker's self-label (like '^EN$' / '^عر$' above).
const LETTERS = '/[A-Za-z]{2,}/';
const USER_VISIBLE_ATTRS = 'accessibilityLabel|accessibilityHint|placeholder|title|label';
const SET_ERROR = "CallExpression[callee.name='setError']";
const ALERT = "CallExpression[callee.object.name='Alert'][callee.property.name='alert']";
const literalArms = (root) => [
  `${root} > Literal[value=${LETTERS}]`,
  `${root} > LogicalExpression > Literal[value=${LETTERS}]`,
  `${root} > ConditionalExpression > Literal[value=${LETTERS}]`,
  `${root} > TemplateLiteral > TemplateElement[value.raw=${LETTERS}]`,
  `${root} > BinaryExpression > Literal[value=${LETTERS}]`,
];
const restrictedLiteralSyntax = [
  {
    selector: `JSXAttribute[name.name=/^(${USER_VISIBLE_ATTRS})$/] > Literal[value=${LETTERS}]:not([value='English'])`,
    message: 'A user-visible JSX attribute carries an untranslated literal — use t(key).',
  },
  ...literalArms(SET_ERROR).map((selector) => ({
    selector,
    message: 'A literal English string reaches setError() — use t(key).',
  })),
  ...literalArms(ALERT).map((selector) => ({
    selector,
    message: 'A literal English string reaches Alert.alert() — use t(key).',
  })),
  { selector: "Literal[value='N/A']", message: "'N/A' is user-visible English — use t(key)." },
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
      'no-restricted-syntax': ['error', ...restrictedLiteralSyntax],
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
