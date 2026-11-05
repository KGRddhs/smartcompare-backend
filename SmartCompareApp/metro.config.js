// Learn more https://docs.expo.io/guides/customizing-metro
const { getSentryExpoConfig } = require('@sentry/react-native/metro');

const { qarenCacheVersion } = require('./metro.cacheVersion');

/** @type {import('expo/metro-config').MetroConfig} */
// S81-G6 CL2: Sentry's Expo wrapper over the stock default config. With
// includeWebReplay false its resolver maps @sentry/replay and
// @sentry-internal/replay to an empty module (the web-only session replay
// code no native bundle runs); it also collapses Sentry-internal frames in
// the symbolicator and adds the debug-id serializer plugin.
const config = getSentryExpoConfig(__dirname, { includeWebReplay: false });

// P-B1-CACHE: key Metro's machine-global transform cache on the transform
// inputs Metro ignores (babel.config.js + the lucide ESM barrel the B1 plugin
// parses). Without this, a box whose %TEMP%\metro-cache predates a babel.config
// change re-emits the pre-change bundle from cache and `eas update` ships it.
// See metro.cacheVersion.js for the full reasoning and the measurement.
// The two deviations from the stock Expo default config are this cache key
// and the Sentry wrapper above.
config.cacheVersion = qarenCacheVersion(__dirname, config.cacheVersion);

module.exports = config;
