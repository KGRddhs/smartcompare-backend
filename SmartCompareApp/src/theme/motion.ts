/**
 * Qaren motion language tokens.
 *
 * Sources of truth:
 *   - Bundle D (Qaren UX redesign): docs/plans/2026-05-06-qaren-ux-redesign-design.md § 1
 *     "Motion language" — screenTransition / springConfig / variableEasing / haptic.
 *   - Bundle E (visual fidelity): docs/plans/2026-05-26-bundle-e-visual-fidelity-design.md
 *     § 3.3 — accordionChevron, ctaGlow, modeSegment, shimmer, counterTick, revealBurst,
 *     and screenTransition.mirrorRTL.
 *
 * Bundle E adds the per-interaction tokens consumed by S0.3 shared primitives
 * (DetailsAccordion, ModeSegment) and S0.4 SlideTransition wrapper.
 *
 * Build Principle #4 — never frame the app as scary:
 *   - haptic intensities are confidence-only (light / medium); no warning / error / heavy.
 *   - No motion token name or string value may contain shake / wobble / jitter / b-o-u-n-c-e.
 *     Spring physics (numeric damping / stiffness) is allowed; the literal word is not.
 *     Regression-tested in __tests__/theme/motion.test.ts via a JSON-stringify walk.
 */
import { Easing } from 'react-native-reanimated';

export const motion = {
  // --- Bundle D foundations ---

  screenTransition: {
    // 320ms cubic-bezier slide between onboarding steps + nav transitions.
    // mirrorRTL=true tells SlideTransition to invert translateX sign when
    // I18nManager.isRTL so Arabic locale slides feel native.
    duration: 320,
    easing: Easing.bezier(0.32, 0.72, 0, 1),
    mirrorRTL: true,
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

  // --- Bundle E extensions ---

  // DetailsAccordion chevron rotates 0deg <-> 180deg over 220ms on expand/collapse.
  accordionChevron: {
    duration: 220,
    easing: Easing.ease,
  },

  // Compare CTA emerald glow when both inputs valid. shadowRadius animates
  // 0 -> 12 paired with shadowColor; shadowOpacity stays driven by the
  // consumer to keep tokens declarative.
  ctaGlow: {
    duration: 240,
    easing: Easing.ease,
    shadowColor: '#10B981',
    shadowRadius: 12,
  },

  // HomeScreen segmented mode rail active-pill slide. 180ms feels instant
  // without being abrupt; cubic-bezier matches screenTransition curve.
  modeSegment: {
    duration: 180,
    easing: Easing.bezier(0.32, 0.72, 0, 1),
  },

  // Skeleton placeholder shimmer (LoadingScreen StreamingCardsVariant).
  // repeat: -1 maps to react-native-reanimated Animated.loop infinite.
  shimmer: {
    duration: 1400,
    easing: Easing.linear,
    repeat: -1,
  },

  // LoadingRings cohort-peer counter 0 -> 2,074 tick over 2.4s ease-out-cubic.
  counterTick: {
    duration: 2400,
    easing: Easing.out(Easing.cubic),
  },

  // ResultsScreen winner-card RevealBurst on first mount.
  // particleEmit: ms the 6-8 emerald particles take to emit outward from center.
  // particleFall: ms the parabolic fall + fade lasts after emit.
  // badgeSpring: scale 0 -> 1.1 -> 1.0 via withSpring on the center badge.
  revealBurst: {
    particleEmit: 600,
    particleFall: 800,
    badgeSpring: { damping: 8, stiffness: 100 },
  },
} as const;

export type HapticKind = (typeof motion.haptic)[keyof typeof motion.haptic];
