/**
 * Production `console.*` strip (M13-55).
 *
 * Functionally equivalent to babel-plugin-transform-remove-console, but
 * implemented inline so we do NOT add an npm dependency: the committed
 * package-lock.json can't be regenerated in the CI/build environment without
 * a network install, and desyncing package.json from the lock would break
 * `npm ci`. This local plugin needs no lockfile change.
 *
 * It removes standalone `console.*(...)` STATEMENTS from PRODUCTION bundles
 * only (NODE_ENV/BABEL_ENV === 'production'); dev keeps them, and jest never
 * loads this file (the test runner is ts-jest, not babel). Belt-and-braces
 * with the `if (__DEV__)` guards in authService.ts — a diagnostic that ever
 * slips past a guard still never ships a token head to logcat / the iOS
 * unified log in a release build. It only touches console calls that stand
 * alone as expression statements, so it can never change the value of an
 * expression that happens to embed a console call.
 */
function removeConsolePlugin() {
  return {
    name: 'qaren-remove-console-production',
    visitor: {
      ExpressionStatement(path) {
        const expr = path.node.expression;
        if (
          expr &&
          expr.type === 'CallExpression' &&
          expr.callee &&
          expr.callee.type === 'MemberExpression' &&
          expr.callee.object &&
          expr.callee.object.type === 'Identifier' &&
          expr.callee.object.name === 'console'
        ) {
          path.remove();
        }
      },
    },
  };
}

module.exports = function (api) {
  // Cache keyed on NODE_ENV so the production-only strip below is recomputed
  // when the env changes (a plain api.cache(true) freezes the first env seen).
  api.cache.using(() => process.env.NODE_ENV);

  const isProduction =
    process.env.NODE_ENV === 'production' ||
    process.env.BABEL_ENV === 'production';

  const plugins = [];
  if (isProduction) {
    plugins.push(removeConsolePlugin);
  }
  // react-native-reanimated/plugin MUST remain last.
  plugins.push('react-native-reanimated/plugin');

  return {
    presets: ['babel-preset-expo'],
    plugins,
  };
};
