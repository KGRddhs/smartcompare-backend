/**
 * S81-G6 CL2 CLIENT-SPEED -- the client timing constants and rules.
 *
 * A leaf: no imports. The Home floor reuses the A17 history rule
 * (ResultsScreen HISTORY_FLOOR_MS / HISTORY_FLOOR_SKIP_BELOW_MS): a response
 * that arrived within HOME_FLOOR_SKIP_BELOW_MS renders now, anything slower
 * is held to HOME_FLOOR_MS from the compare start. The winner reveal keeps
 * its 800 ms brand moment except on a measured fast hit (RULINGS_S81_G6
 * R-G6-4: the Home response under the skip band, carried to Results as the
 * route param fastHit: true).
 */

export const HOME_FLOOR_MS = 400;
export const HOME_FLOOR_SKIP_BELOW_MS = 300;
export const REVEAL_DELAY_MS = 800;

/**
 * Milliseconds the Home loader still waits before navigating to Results.
 * 0 for a response at or under the skip band (and for a negative or
 * non-finite elapsed value); else the rest of the 400 ms floor.
 */
export function homeFloorDelayMs(elapsedMs: number): number {
  if (!Number.isFinite(elapsedMs) || elapsedMs <= HOME_FLOOR_SKIP_BELOW_MS) {
    return 0;
  }
  return Math.max(0, HOME_FLOOR_MS - elapsedMs);
}

/** The winner-reveal delay: 0 on a measured fast hit, else 800 ms. */
export function revealDelayMs(fastHit: boolean): number {
  return fastHit ? 0 : REVEAL_DELAY_MS;
}
