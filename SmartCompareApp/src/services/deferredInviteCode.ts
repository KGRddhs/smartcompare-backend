/**
 * Module-scoped slot for the QR-XXXXXX invite code captured from the
 * Android Play Install Referrer on app mount.
 *
 * Why module-scope: the consumer is `RegisterScreen`, which is mounted
 * inside the navigation stack AFTER `App.tsx`'s root effect fires. A
 * React context would require RegisterScreen to be a descendant of the
 * provider at the exact moment the PIR resolves; the simpler module
 * variable survives mount/unmount/remount without coupling either
 * party to a provider hierarchy.
 *
 * The set is once-per-launch (PIR is only meaningful the first time
 * after install). `consume` clears so a re-mount of RegisterScreen
 * doesn't double-pre-fill.
 *
 * Spec: docs/plans/2026-05-12-bundle-bcd-consolidated-design.md § 4.1
 */
let _code: string | null = null;

export function setDeferredInviteCode(code: string): void {
  _code = code;
}

export function consumeDeferredInviteCode(): string | null {
  const c = _code;
  _code = null;
  return c;
}

/**
 * Test-only helper — production code never calls this. Allows test
 * files to ensure isolation across describe blocks.
 */
export function __resetDeferredInviteCodeForTests(): void {
  _code = null;
}
