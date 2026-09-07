// Learn more https://docs.expo.io/guides/customizing-metro
const { getDefaultConfig } = require('expo/metro-config');

const { qarenCacheVersion } = require('./metro.cacheVersion');

/** @type {import('expo/metro-config').MetroConfig} */
const config = getDefaultConfig(__dirname);

// P-B1-CACHE: key Metro's machine-global transform cache on the transform
// inputs Metro ignores (babel.config.js + the lucide ESM barrel the B1 plugin
// parses). Without this, a box whose %TEMP%\metro-cache predates a babel.config
// change re-emits the pre-change bundle from cache and `eas update` ships it.
// See metro.cacheVersion.js for the full reasoning and the measurement.
// This is the ONLY deviation from the stock Expo default config.
config.cacheVersion = qarenCacheVersion(__dirname, config.cacheVersion);

module.exports = config;
