/**
 * Qaren motion language tokens.
 *
 * See docs/plans/2026-05-06-qaren-ux-redesign-design.md Section 1
 * "Motion language" for the source-of-truth animation contract.
 *
 * - screenTransition: 320ms slide for onboarding step changes (mirrors RTL)
 * - springConfig: per-purpose spring (chip bounce, progress bar, tab icon)
 * - variableEasing: theatrical loading bar — fast/slow/snap segments
 * - haptic: chip select, stage tick, winner reveal — never used in error
 *   paths (the redesign never frames the app as "scary")
 */
import { Easing } from 'react-native-reanimated';

export const motion = {
  screenTransition: {
    duration: 320,
    easing: Easing.bezier(0.32, 0.72, 0, 1),
  },
  springConfig: {
    chip: { damping: 14, stiffness: 200 },
    progress: { damping: 18, stiffness: 120 },
    tab: { damping: 12, stiffness: 180 },
  },
  variableEasing: {
    fast: Easing.bezier(0, 0.55, 0.45, 1),
    slow: Easing.bezier(0.4, 0, 0.6, 1),
    snap: Easing.bezier(0.55, 0, 0.1, 1),
  },
  haptic: {
    chip: 'light' as const,
    stage: 'light' as const,
    winner: 'medium' as const,
  },
} as const;

export type HapticKind = (typeof motion.haptic)[keyof typeof motion.haptic];
