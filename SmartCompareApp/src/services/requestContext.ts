/**
 * S81-08 CLIENT-FIRST-OTA: the request-context headers the S81-05 server half
 * parses (RULINGS_S81_08 R-S08-1, R-S08-3, R-S08-4 as amended by R-S08B-1 /
 * R-S08B-5, R-S08-5, R-S08-6, R-S08-9; GATE_S81_08 GC-1..GC-6).
 *
 *   X-Device-Fingerprint   getDeviceFingerprint() (64 lower-case hex). On the
 *                          request path the read is bounded at
 *                          DEVICE_ID_HEADER_TIMEOUT_MS; past it, or on any
 *                          failure, the header is omitted.
 *   X-AI-Consent-Version   String(AI_CONSENT_VERSION), only when the SAVED
 *                          ACCOUNT holds a current consent record (R-S08-3:
 *                          per account, no device-level copy; a signed-out
 *                          device or a getSavedUser failure sends none).
 *   X-Compare-Request-Id   a lower-case uuid4 minted by newCompareRequestId()
 *                          at the compare call site (one per compare attempt)
 *                          and passed in; never derived from a path list.
 *   X-Client-Capabilities  CLIENT_CAPABILITIES joined with ','. The list ships
 *                          EMPTY, so no header is sent (R-S08-6: S81-11 adds
 *                          'price_asof' with the as-of rendering).
 *
 * X-Device-Fingerprint-Legacy is NOT built here: it rides register and the two
 * social sign-ins only (authService), never a metered request.
 *
 * The device and consent headers ride only the requests a call site marks with
 * withRequestContext() (R-S08-5: the REST and POST text compare, the link
 * compare and /usage/status; the request interceptor reads the marker, and no
 * route literal lives in this file); the camera upload and the SSE request
 * build the same headers with buildContextHeaders(). A header is never sent
 * empty, never overwrites a value the request already carries (any letter
 * case), and no header value, hash or id is ever logged. Every function here
 * resolves (or returns) normally: a failing builder only omits its header.
 */

import * as Crypto from 'expo-crypto';
import { getDeviceFingerprint } from './deviceFingerprint';

/** The capabilities this client renders (R-S08-6). Empty: no header is sent. */
export const CLIENT_CAPABILITIES: readonly string[] = [];

/** The request-config key a call site sets to put a request on the metered allowlist. */
export const REQUEST_CONTEXT_MARKER = 'qarenRequestContext';

/** Bound on the device-id read on the request path (R-S08-9); past it the header is omitted. */
export const DEVICE_ID_HEADER_TIMEOUT_MS = 1000;

const UUID_V4 = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;
const DEVICE_HASH = /^[a-f0-9]{64}$/;
const CONSENT_VERSION = /^[0-9]{1,3}$/;

export type ContextHeaders = Record<string, string>;

/** The marker object a call site spreads into its axios request config. */
export interface RequestContextConfig {
  qarenRequestContext: true;
  headers?: ContextHeaders;
}

/**
 * A fresh compare request id: Crypto.randomUUID() lower-cased (an iOS NSUUID is
 * upper case) when it is a canonical uuid4, else null (never a made-up id).
 */
export function newCompareRequestId(): string | null {
  try {
    const raw = Crypto.randomUUID();
    if (typeof raw !== 'string') return null;
    const id = raw.toLowerCase();
    return UUID_V4.test(id) ? id : null;
  } catch {
    return null;
  }
}

/**
 * The call-site marker (R-S08-1 / R-S08-5): spread into an axios request config
 * so the request interceptor adds the device and consent headers. A compare
 * request passes its id, which then rides in `headers`; with no id the config
 * gains no `headers` key at all.
 */
export function withRequestContext(compareRequestId?: string | null): RequestContextConfig {
  const marker: RequestContextConfig = { qarenRequestContext: true };
  if (typeof compareRequestId === 'string' && UUID_V4.test(compareRequestId)) {
    marker.headers = { 'X-Compare-Request-Id': compareRequestId };
  }
  return marker;
}

/** True for a request config a call site marked with withRequestContext(). */
export function isContextRequest(config: unknown): boolean {
  return (
    !!config &&
    typeof config === 'object' &&
    (config as Record<string, unknown>)[REQUEST_CONTEXT_MARKER] === true
  );
}

async function deviceHeaderValue(): Promise<string | null> {
  let timer: ReturnType<typeof setTimeout> | null = null;
  const bound = new Promise<null>((resolve) => {
    timer = setTimeout(() => resolve(null), DEVICE_ID_HEADER_TIMEOUT_MS);
  });
  try {
    const read = Promise.resolve()
      .then(() => getDeviceFingerprint())
      .then(
        (fp) => (typeof fp === 'string' && DEVICE_HASH.test(fp) ? fp : null),
        () => null,
      );
    return await Promise.race([read, bound]);
  } finally {
    if (timer) clearTimeout(timer);
  }
}

async function consentHeaderValue(): Promise<string | null> {
  try {
    // Lazy: aiConsent and authService import api.ts, which imports this module.
    const { getSavedUser } = require('./authService');
    const user = await getSavedUser();
    const userId = user && typeof user.id === 'string' && user.id ? user.id : null;
    const consent = require('./aiConsent');
    // The per-account memo (R-S08-3); a null id drops it and reads false. No
    // other read: a consent module without it omits the header
    // (RULINGS_FIX1_S81_08 F1-3; the jest global mock exports it).
    const current = (await consent.hasCurrentAiConsentForRequest(userId)) === true;
    if (!current || !userId) return null;
    const version = String(consent.AI_CONSENT_VERSION);
    return CONSENT_VERSION.test(version) ? version : null;
  } catch {
    return null;
  }
}

/**
 * The context headers of one request: the device id and the consent version
 * (read concurrently), the compare id when one is passed, and the capability
 * list when it is not empty. Never rejects; a failing builder only omits its
 * header.
 */
export async function buildContextHeaders(
  opts: { compareRequestId?: string | null } = {},
): Promise<ContextHeaders> {
  const headers: ContextHeaders = {};
  try {
    const [device, consentVersion] = await Promise.all([deviceHeaderValue(), consentHeaderValue()]);
    if (device) headers['X-Device-Fingerprint'] = device;
    if (consentVersion) headers['X-AI-Consent-Version'] = consentVersion;
  } catch {
    // Unreachable (both readers resolve); kept so this can never reject.
  }
  const id = opts && opts.compareRequestId;
  if (typeof id === 'string' && UUID_V4.test(id)) headers['X-Compare-Request-Id'] = id;
  if (CLIENT_CAPABILITIES.length > 0) {
    headers['X-Client-Capabilities'] = CLIENT_CAPABILITIES.join(',');
  }
  return headers;
}

function hasHeader(headers: Record<string, unknown>, name: string): boolean {
  const lower = name.toLowerCase();
  return Object.keys(headers).some((key) => {
    if (key.toLowerCase() !== lower) return false;
    const value = headers[key];
    return value !== undefined && value !== null && value !== '';
  });
}

/**
 * Adds every context header the request does not already carry (any letter
 * case; an empty value counts as absent) and never overwrites one. Works on a
 * plain headers object and on axios' AxiosHeaders. Never throws.
 */
export function mergeContextHeaders(
  config: { headers?: unknown } | null | undefined,
  context: ContextHeaders | null | undefined,
): void {
  try {
    if (!config || !context) return;
    const names = Object.keys(context);
    if (names.length === 0) return;
    if (!config.headers || typeof config.headers !== 'object') config.headers = {};
    const target = config.headers as Record<string, unknown>;
    for (const name of names) {
      if (!hasHeader(target, name)) target[name] = context[name];
    }
  } catch {
    // A header that cannot be added is omitted; the request still leaves.
  }
}
