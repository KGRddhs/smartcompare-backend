// W3-12 — MUST stay the FIRST import: its module body arms Sentry before any
// other module body runs, so a boot-time failure anywhere in App's import
// graph (notably the "running unpinned" certificate-pinning alarm raised from
// api.ts's module body) reaches an initialised Sentry instead of being
// dropped. Do not reorder, and do not let it reach services/api.
import './src/services/sentryBootstrap';

import { registerRootComponent } from 'expo';

import App from './App';

// registerRootComponent calls AppRegistry.registerComponent('main', () => App);
// It also ensures that whether you load the app in Expo Go or in a native build,
// the environment is set up appropriately
registerRootComponent(App);
