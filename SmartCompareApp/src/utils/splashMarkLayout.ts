/**
 * splashMarkLayout — where the native launch screen draws the MYEZ mark, in
 * window points, so the JS splash can draw its mark on the same pixels (U4c,
 * decision D2: the mark does not move or fade at the hand-off).
 *
 * Spec: docs/investigations/2026-10-03-session-71-state/U4C_INAPP_MARK_SPEC.md
 * section 2d and R8.
 *
 * The iOS launch storyboard draws assets/splash-icon.png (a 1024 px square)
 * aspect-fit across the full window: scaled to D = min(width, height) and
 * centred. scripts/render_myez_icons.py made that file by scaling the
 * 2048 px master to SPLASH_MARK_PX and placing it at SPLASH_OFFSET_PX; the
 * mark PNG QarenLogo draws is the master's MARK_SQUARE_MASTER_PX square. The
 * constants equal the renderer's `mark_geometry` in
 * docs/brand/myez-icons.manifest.json (a test keeps them equal), so a change
 * to the launcher art changes the tests, not silently the hand-off.
 *
 * PHYSICAL and pure: the result depends only on the argument and imports
 * nothing from react-native. Under RTL React Native mirrors a physical
 * `left` while the launch screen is never mirrored; SplashScreen compensates
 * for that at render time, not here.
 */

/** Side of the master art, px. */
export const MASTER_PX = 2048;
/** Side of assets/splash-icon.png, px. */
export const SPLASH_CANVAS_PX = 1024;
/** Side the master is scaled to on the splash canvas, px. */
export const SPLASH_MARK_PX = 549;
/** Offset of the scaled master on the splash canvas, px (both axes). */
export const SPLASH_OFFSET_PX = 237;
/** The mark PNG's square in master pixels: [x0, y0, side]. */
export const MARK_SQUARE_MASTER_PX = [435, 399, 1242] as const;

export type SplashMarkLayout = { left: number; top: number; size: number };

export function splashMarkLayout(win: { width: number; height: number }): SplashMarkLayout {
  const { width, height } = win;
  const [x0, y0, side] = MARK_SQUARE_MASTER_PX;
  const d = Math.min(width, height);
  // Window points per splash-canvas pixel, and splash pixels per master pixel.
  const k = d / SPLASH_CANVAS_PX;
  const f = SPLASH_MARK_PX / MASTER_PX;
  return {
    left: (width - d) / 2 + k * (SPLASH_OFFSET_PX + x0 * f),
    top: (height - d) / 2 + k * (SPLASH_OFFSET_PX + y0 * f),
    size: k * side * f,
  };
}
