/**
 * Lane A-L3 Task L3.7 — global Jest mock for @sentry/react-native.
 *
 * Production code (sentry.ts, wallTimeInstrumentation.ts, authService.ts)
 * imports @sentry/react-native as an ES module. The published ESM has
 * `export {...} from '@sentry/core'` which Jest's CommonJS transformer
 * trips over (`SyntaxError: Unexpected token 'export'`).
 *
 * This stub provides no-op implementations for the surface area touched
 * by app code. Tests that need to assert on Sentry calls override this
 * via jest.mock() at the file level (see wallTimeInstrumentation.test.ts).
 */
export const setTag = (_key: string, _value: string) => {};
export const setTags = (_tags: Record<string, string>) => {};
export const setContext = (_name: string, _ctx: any) => {};
export const setExtra = (_key: string, _value: any) => {};
export const setUser = (_user: any) => {};
export const captureMessage = (_msg: string, _opts?: any) => {};
export const captureException = (_err: any, _opts?: any) => {};
export const captureEvent = (_event: any) => {};
export const addBreadcrumb = (_crumb: any) => {};
export const addIntegration = (_integ: any) => {};
export const init = (_opts: any) => {};
export const getCurrentScope = () => ({
  setTag,
  setTags,
  setContext,
  setExtra,
  setUser,
  clear: () => {},
});
export const withScope = (cb: (scope: any) => void) => {
  cb(getCurrentScope());
};
export const startSpan = (_opts: any, cb: (span: any) => any) =>
  cb({ end: () => {} });
export const startInactiveSpan = (_opts: any) => ({ end: () => {} });
export const startSpanManual = (_opts: any, cb: (span: any) => any) =>
  cb({ end: () => {} });
export const getClient = () => null;
export const lastEventId = () => null;

export default {
  setTag,
  setTags,
  setContext,
  setExtra,
  setUser,
  captureMessage,
  captureException,
  captureEvent,
  addBreadcrumb,
  addIntegration,
  init,
  getCurrentScope,
  withScope,
  startSpan,
  startInactiveSpan,
  startSpanManual,
  getClient,
  lastEventId,
};
