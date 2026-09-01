/**
 * Sentry crash reporting for the Qaren mobile app.
 *
 * Mirrors the backend scrubbing patterns in `app/services/sentry_service.py`
 * so JWTs, OpenAI / Firecrawl API keys, generic long-hex tokens, and
 * Bearer headers are redacted before events leave the device. Sensitive
 * request headers (authorization, x-admin-key, cookie) are also redacted
 * wholesale.
 *
 * Follow-ups (NOT in this commit):
 *   - Move the DSN out of source into an EAS env secret
 *     (`EXPO_PUBLIC_SENTRY_DSN`). The DSN is a write-only public key —
 *     safe to commit as a fallback, but cleaner in EAS.
 *   - Sourcemap upload via the expo plugin object form
 *     `["@sentry/react-native", { url, organization, project }]`. Needs
 *     `SENTRY_AUTH_TOKEN` in CI.
 */
import * as Sentry from '@sentry/react-native';

// Apply in declared order — earlier patterns win over later ones (the
// JWT pattern matches before the generic-long-hex pattern can swallow
// a JWT payload segment, for example).
// M4 (audit 2026-05-22): widened the generic hex pattern from {40,} to
// {32,} so 32-char lowercase Serper API keys get redacted. Also added
// SENSITIVE_KEY_FRAGMENTS-based scrubbing below for provider-specific
// tokens whose shape we don't pattern-match (Scrape.do, Upstash REST,
// future providers). Mirrors the backend sentry_service.py changes.
const SENSITIVE_PATTERNS: Array<[RegExp, string]> = [
  [/eyJ[A-Za-z0-9_-]{20,}\.eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]+/g, '[JWT_REDACTED]'],
  [/sk-proj-[A-Za-z0-9_-]+/g, '[OPENAI_KEY_REDACTED]'],
  [/fc-[a-f0-9]{20,}/g, '[FIRECRAWL_KEY_REDACTED]'],
  [/[a-f0-9]{32,}/g, '[TOKEN_REDACTED]'],
  [/Bearer\s+[A-Za-z0-9_.-]+/g, 'Bearer [REDACTED]'],
];

const SENSITIVE_HEADERS = new Set(['authorization', 'x-admin-key', 'cookie']);

// Dict key fragments (case-insensitive) — when a key matches, the whole
// value is replaced regardless of pattern match. Catches provider tokens
// whose format isn't explicitly listed above.
const SENSITIVE_KEY_FRAGMENTS = ['api_key', 'apikey', 'token', 'secret', 'password'];

function keyIsSensitive(key: string): boolean {
  const lower = key.toLowerCase();
  return SENSITIVE_KEY_FRAGMENTS.some((frag) => lower.includes(frag));
}

// Hard-coded write-only public DSN. Safe to commit; the EAS secret
// follow-up is cosmetic.
const FALLBACK_DSN =
  'https://ac5bd897c6c0580bf79f3002efac58a6@o4511371892097024.ingest.de.sentry.io/4511397433180240';

export function scrubString(s: string): string {
  let out = s;
  for (const [pattern, replacement] of SENSITIVE_PATTERNS) {
    out = out.replace(pattern, replacement);
  }
  return out;
}

function scrubDict(data: Record<string, unknown>): Record<string, unknown> {
  const scrubbed: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(data)) {
    // M4: key-name scrub takes priority — secret-shaped keys get redacted
    // regardless of value shape.
    if (keyIsSensitive(key) && value !== null && value !== undefined) {
      scrubbed[key] = '[REDACTED]';
    } else if (typeof value === 'string') {
      scrubbed[key] = scrubString(value);
    } else if (value !== null && typeof value === 'object' && !Array.isArray(value)) {
      scrubbed[key] = scrubDict(value as Record<string, unknown>);
    } else if (Array.isArray(value)) {
      scrubbed[key] = value.map((v) =>
        typeof v === 'string'
          ? scrubString(v)
          : v !== null && typeof v === 'object'
          ? scrubDict(v as Record<string, unknown>)
          : v,
      );
    } else {
      scrubbed[key] = value;
    }
  }
  return scrubbed;
}

export function scrubBeforeSend(event: any, _hint: any): any {
  if (!event) return event;

  // Scrub exception messages.
  if (event.exception && Array.isArray(event.exception.values)) {
    for (const exc of event.exception.values) {
      if (typeof exc?.value === 'string') {
        exc.value = scrubString(exc.value);
      }
    }
  }

  // Scrub breadcrumbs.
  if (event.breadcrumbs && Array.isArray(event.breadcrumbs.values)) {
    for (const crumb of event.breadcrumbs.values) {
      if (typeof crumb?.message === 'string') {
        crumb.message = scrubString(crumb.message);
      }
      if (crumb?.data && typeof crumb.data === 'object' && !Array.isArray(crumb.data)) {
        crumb.data = scrubDict(crumb.data as Record<string, unknown>);
      }
    }
  }

  // Redact sensitive request headers wholesale.
  if (event.request && event.request.headers && typeof event.request.headers === 'object') {
    const headers = event.request.headers as Record<string, unknown>;
    for (const key of Object.keys(headers)) {
      if (SENSITIVE_HEADERS.has(key.toLowerCase())) {
        headers[key] = '[REDACTED]';
      }
    }
  }

  return event;
}

/**
 * #118 — production-visible signal when the SSE streaming transport fails
 * and streamComparison degrades to the single REST compare. Before this,
 * the only trace was a __DEV__ console.log, so a silent transport
 * regression (the exact defect #118 fixed) was invisible in the dashboard.
 * Call shape mirrors the b4_diag breadcrumb in authService.ts.
 */
export function addSseFallbackBreadcrumb(err: unknown): void {
  try {
    const message = scrubString(
      String((err as { message?: unknown })?.message ?? err),
    );
    Sentry.addBreadcrumb({
      category: 'sse',
      level: 'warning',
      message: `SSE transport failed; fell back to REST compare: ${message}`,
    });
  } catch {
    // A breadcrumb must never break the compare path.
  }
}

let _initialized = false;

export function initSentry(dsn?: string): void {
  if (_initialized) return;
  const resolved =
    dsn ||
    (typeof process !== 'undefined' && process.env && process.env.EXPO_PUBLIC_SENTRY_DSN) ||
    FALLBACK_DSN;
  if (!resolved) return;
  try {
    Sentry.init({
      dsn: resolved,
      sendDefaultPii: false,
      tracesSampleRate: 0.1,
      beforeSend: scrubBeforeSend,
    });
    _initialized = true;
  } catch {
    // Never let Sentry init crash app boot. Native bridge missing in
    // Expo Go / test env is the most common cause; the SDK still
    // captures unhandled errors via JS global hooks.
  }
}
