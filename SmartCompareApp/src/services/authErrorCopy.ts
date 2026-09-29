/**
 * Auth failure copy — S69 U6 R2 (audit RT-9).
 *
 * login() / register() used to hand the screen
 * `error.response?.data?.detail || error.message`. The backend's unified
 * envelope (app/middleware/error_handler.py) carries its text under `error`
 * and a machine `code`, never `detail`, so a wrong password rendered axios's
 * "Request failed with status code 401" — English, to every user. The copy
 * is now chosen from the status / `code` and travels as an i18n KEY; the
 * screen renders `t(key)` and nothing else.
 *
 * Mapping (never by matching English message text):
 *   - 429 RATE_LIMITED (slowapi)            -> common.errors.rateLimited
 *   - 429 ACCOUNT_LOCKED (login lockout)    -> common.errors.locked
 *   - any other 429                          -> common.errors.rateLimited
 *   - login 401 (AUTH_REQUIRED envelope)     -> auth.errors.invalidCredentials
 *     The route raises a plain-string 401 for a wrong password, an
 *     unconfirmed email AND an upstream blip, so the code is always
 *     AUTH_REQUIRED; a backend follow-up gives each its own code.
 *   - register TERMS_ACCEPTANCE_REQUIRED     -> auth.consent.required
 *   - register INVITE_CODE_NOT_FOUND (404)   -> auth.errors.inviteCodeNotFound
 *   - everything else (duplicate-email 400,
 *     5xx, transport, 200 without a user)    -> auth.loginFailed / auth.registerFailed
 */

import { settingsErrorKey } from './errorCopy';

export type AuthOperation = 'login' | 'register';

const FALLBACK_KEY: Record<AuthOperation, string> = {
  login: 'auth.loginFailed',
  register: 'auth.registerFailed',
};

/** The i18n key for a failed login / register, from the thrown (axios) error. */
export function authFailureKey(operation: AuthOperation, error: unknown): string {
  const response = (error as any)?.response;
  const status: unknown = response?.status;
  const data = response?.data;
  const code: string | null =
    (typeof data?.code === 'string' && data.code) ||
    (typeof data?.detail?.code === 'string' && data.detail.code) ||
    null;
  const fallback = FALLBACK_KEY[operation];

  if (code === 'RATE_LIMITED' || code === 'ACCOUNT_LOCKED') {
    return settingsErrorKey(code, fallback);
  }
  if (status === 429) return 'common.errors.rateLimited';
  if (operation === 'login' && status === 401) return 'auth.errors.invalidCredentials';
  if (operation === 'register') {
    if (code === 'TERMS_ACCEPTANCE_REQUIRED') return 'auth.consent.required';
    if (code === 'INVITE_CODE_NOT_FOUND') return 'auth.errors.inviteCodeNotFound';
  }
  return fallback;
}

/** The key a screen renders for a failed AuthResponse (never its raw text). */
export function authErrorKey(result: { errorKey?: string }, fallbackKey: string): string {
  return result.errorKey ?? fallbackKey;
}
