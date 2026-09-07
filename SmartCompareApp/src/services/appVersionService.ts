/**
 * A9 — the client half of the force-update contract.
 *
 * THE DEAD WIRE THIS CLOSES
 * The backend has served `GET /api/v1/app/version` since Bundle D
 * (`app/api/version_routes.py`), reading `APP_MIN_VERSION` /
 * `APP_LATEST_VERSION` / `APP_FORCE_UPDATE` straight out of the
 * environment and returning them with ZERO comparison logic — enforcement
 * was always meant to be client-side. No client ever called it. So the
 * documented incident lever ("flip APP_FORCE_UPDATE and every stale
 * install is bounced") did nothing at all: during an incident the runbook
 * would be followed and silently no-op. This module is the missing
 * consumer.
 *
 * WHY NO NEW FEATURE FLAG
 * The change is entirely client-side (React Native has no per-call env
 * flag; repo precedent M13-W4 ships such changes unflagged), and the
 * remote gate already exists and is already OFF by default:
 * `APP_FORCE_UPDATE` defaults to "false" server-side, so this code path
 * decides "do not block" until an operator deliberately flips it.
 *
 * FAIL-OPEN IS THE WHOLE DESIGN
 * Blocking is the highest-blast-radius thing this app can do to itself, so
 * EVERY uncertain path resolves to "no gate":
 *   - `nativeApplicationVersion` null/blank (Expo Go, some simulators)
 *   - request timeout, offline, TLS/pinning failure, DNS
 *   - non-2xx response, non-JSON body, unexpected body shape
 *   - `force_update` anything other than the boolean `true`
 *   - a min_version or current version this build cannot parse
 * A gate is returned ONLY on an affirmative, fully-parsed
 * `force_update === true` AND `current < min_version`.
 *
 * SHIPPING NOTE
 * `expo-application` is already a linked dependency (in use at
 * `deviceFingerprint.ts`), so this needs no new native module: it reaches
 * devices via `eas update` alone, no store build.
 */
import { Platform } from 'react-native';
import * as Application from 'expo-application';
import { API_BASE_URL } from './api';
import { fetchWithDeadline } from './fetchWithDeadline';
import { isBelowMinVersion } from '../utils/versionCompare';

/** Path of the backend contract (`app/api/version_routes.py`). */
export const VERSION_CHECK_PATH = '/api/v1/app/version';

/**
 * Deadline for the version check.
 *
 * One tiny JSON GET. It runs beside boot and nothing waits on it, so the
 * only job of this number is to make sure the request cannot sit on a
 * stalled socket forever (RN's fetch has no default deadline at all — see
 * `fetchWithDeadline`). Short enough to be irrelevant, long enough not to
 * spuriously miss a real answer on a slow GCC mobile connection.
 */
export const VERSION_CHECK_TIMEOUT_MS = 8000;

/** Store-URL schemes we are willing to hand to `Linking.openURL`. */
const ALLOWED_UPDATE_URL_SCHEMES = ['https://', 'http://', 'itms-apps://', 'market://'];

/** What the blocking screen needs. Presence of this object === block. */
export type ForcedUpdateGate = {
  /** The `min_version` the server asked for (diagnostics + tests). */
  minVersion: string;
  /** The version this install actually reports. */
  currentVersion: string;
  /** Platform store URL, or null when the server did not supply a usable one. */
  updateUrl: string | null;
};

function readString(source: Record<string, unknown>, key: string): string | null {
  const value = source[key];
  return typeof value === 'string' && value.trim() !== '' ? value.trim() : null;
}

/**
 * Pick the store URL for `platform`, or null.
 *
 * The value comes from operator-set env vars, but it is still handed to
 * `Linking.openURL`, so an unknown scheme is refused rather than opened.
 * A missing URL is not a reason to skip the gate — the screen falls back
 * to telling the user to update from their own store.
 */
export function pickUpdateUrl(payload: Record<string, unknown>, platform: string): string | null {
  const raw = readString(payload, platform === 'ios' ? 'update_url_ios' : 'update_url_android');
  if (raw === null) return null;
  const lower = raw.toLowerCase();
  return ALLOWED_UPDATE_URL_SCHEMES.some((scheme) => lower.startsWith(scheme)) ? raw : null;
}

/**
 * The pure decision: does this response, against this installed version,
 * justify blocking the app?
 *
 * Separated from the fetch so the whole truth table is testable without a
 * network, a native module or a React tree.
 */
export function decideForcedUpdate(
  payload: unknown,
  currentVersion: unknown,
  platform: string
): ForcedUpdateGate | null {
  if (payload === null || typeof payload !== 'object' || Array.isArray(payload)) return null;
  const body = payload as Record<string, unknown>;

  // Strictly the boolean. A string "true", 1, or a truthy object is a
  // contract the backend does not emit, so it reads as "do not block".
  if (body.force_update !== true) return null;

  if (typeof currentVersion !== 'string' || currentVersion.trim() === '') return null;
  const minVersion = readString(body, 'min_version');
  if (minVersion === null) return null;

  if (!isBelowMinVersion(currentVersion, minVersion)) return null;

  return {
    minVersion,
    currentVersion: currentVersion.trim(),
    updateUrl: pickUpdateUrl(body, platform),
  };
}

/**
 * The installed native version, or null when the runtime cannot report one
 * (Expo Go returns null; some dev/simulator contexts return undefined).
 */
export function getCurrentAppVersion(): string | null {
  const version = Application.nativeApplicationVersion;
  return typeof version === 'string' && version.trim() !== '' ? version : null;
}

/**
 * Ask the backend whether this install must be blocked.
 *
 * Resolves with a gate ONLY on an affirmative answer, and with `null` on
 * every other outcome. It never rejects and never throws — callers wire it
 * fire-and-forget.
 */
export async function checkForcedUpdate(): Promise<ForcedUpdateGate | null> {
  try {
    const currentVersion = getCurrentAppVersion();
    if (currentVersion === null) return null;

    const response = await fetchWithDeadline(
      `${API_BASE_URL}${VERSION_CHECK_PATH}`,
      { method: 'GET', headers: { Accept: 'application/json' } },
      VERSION_CHECK_TIMEOUT_MS
    );
    if (!response || response.ok !== true) return null;

    const payload = await response.json();
    return decideForcedUpdate(payload, currentVersion, Platform.OS);
  } catch {
    // Offline, timeout, pinning failure, malformed JSON — none of these
    // are evidence that the app is out of date.
    return null;
  }
}
