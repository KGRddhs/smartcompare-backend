/**
 * W3-6 — the Supabase password-recovery deep link.
 *
 * GoTrue's post-verify redirect lands on `qaren://reset-password` with the
 * session in the URL FRAGMENT (`#access_token=…&refresh_token=…&type=recovery`;
 * the query form is accepted too, the shape is server behaviour). The
 * installed @react-navigation/core splits a path on `?` only and has no
 * fragment handling, and forwarding the tokens as a query would write the
 * access token into navigation state. So the linking override parses the
 * link here, parks ONLY the access token in this module-scoped slot, and
 * routes to the bare `reset-password` path.
 *
 * The slot mirrors `deferredInviteCode.ts`: `consume` clears on read. The
 * refresh token is discarded — the backend completion route needs only the
 * access token. Nothing in this module logs or reports the token.
 */

export type PendingRecovery = { accessToken: string };

const RECOVERY_LINK = /^\/?reset-password[#?](.*)$/;

let _pending: PendingRecovery | null = null;

/**
 * Pure. Returns `{ accessToken }` only for a `reset-password` link whose
 * parameters carry `type=recovery` and a non-empty `access_token`.
 */
export function parseRecoveryLink(path: string): PendingRecovery | null {
  const match = RECOVERY_LINK.exec(path);
  if (!match) {
    return null;
  }
  try {
    const params = new URLSearchParams(match[1]);
    if (params.get('type') !== 'recovery') {
      return null;
    }
    const accessToken = params.get('access_token');
    if (!accessToken) {
      return null;
    }
    return { accessToken };
  } catch {
    // A malformed %-escape makes decodeURIComponent throw; treat it as no link.
    return null;
  }
}

export function setPendingRecovery(recovery: PendingRecovery): void {
  _pending = { accessToken: recovery.accessToken };
}

export function consumePendingRecovery(): PendingRecovery | null {
  const pending = _pending;
  _pending = null;
  return pending;
}

/**
 * Test-only helper — production code never calls this.
 */
export function __resetPendingRecoveryForTests(): void {
  _pending = null;
}
