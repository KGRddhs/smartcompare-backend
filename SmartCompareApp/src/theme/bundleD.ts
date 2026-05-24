/**
 * Bundle D — Claude-Design tokens (additive namespace, R10 invariant).
 *
 * Source of truth: `docs/claude-design-handoff/tokens.json` (Ahmed's
 * Claude-Design package, commit 0b87415). Values mirror the legacy
 * `src/theme/index.ts` shape exactly per SKILL.md "tokens.json is in
 * the shape of SmartCompareApp/src/theme/index.ts" — most values are
 * identical to legacy (Claude-Design deliberately matched our existing
 * design system). The additions are: `motion` (spring + easing +
 * haptic vocabulary), `policy` (machine-readable design rules),
 * `ctaReady` shadow, and `minTouchTarget`.
 *
 * R10 invariant per `memory/BUNDLE_D_FRONTEND_ANCHOR.md`:
 *   "Frontend extends theme, doesn't replace; tokens applied additively;
 *    cross-QA verifies no breaking theme change."
 *
 * Legacy `src/theme/index.ts` stays unchanged — existing surfaces keep
 * referencing the legacy namespace until each page is individually
 * migrated to the Bundle D redesign. The `bundleD*` namespace below is
 * what redesigned pages import from.
 *
 * Drop-in usage (per redesigned page):
 *   import { bundleDColors, bundleDTypography, bundleDMotion } from '../theme/bundleD';
 *
 * Why hardcoded values (vs. JSON import):
 *   tokens.json lives at `docs/claude-design-handoff/` — outside the
 *   SmartCompareApp/ bundle root, so a relative JSON import would
 *   either need a docs/ symlink (fragile) or a fragile relative path
 *   (`../../../docs/...`) that breaks if docs/ moves. Hardcoded values
 *   here keep production code self-contained; sync with tokens.json
 *   when Claude-Design ships a new bundle.
 */

export const bundleDColors = {
  bg: {
    primary: '#FFFFFF',
    secondary: '#F8F8FA',
    inverse: '#0A0A0B',
  },
  text: {
    primary: '#0A0A0B',
    secondary: '#6B7280',
    placeholder: '#9CA3AF',
    onInverse: '#FFFFFF',
  },
  cta: {
    primary: '#0A0A0B',
    onPrimary: '#FFFFFF',
  },
  accent: '#10B981',
  accentDark: '#059669',
  accentLight: '#ECFDF5',
  accentGlow: 'rgba(16,185,129,0.20)',
  // Restrained dark accent for premium / luxury / top_tier picker cards.
  // Editorial only — never used for state or CTA.
  editorialDark: '#1A1A1A',
  destructive: '#EF4444',
  warning: '#F59E0B',
  border: {
    light: '#E5E7EB',
    medium: '#D1D5DB',
  },
} as const;

export const bundleDSpacing = {
  xs: 4,
  sm: 8,
  md: 12,
  base: 16,
  lg: 20,
  xl: 24,
  '2xl': 32,
  '3xl': 48,
} as const;

export const bundleDRadii = {
  card: 16,
  button: 12,
  chip: 999,
  input: 12,
  hero: 24,
} as const;

export const bundleDTypography = {
  hero: {
    fontSize: 36,
    fontWeight: '700' as const,
    lineHeight: 36 * 1.2,
    letterSpacing: 36 * -0.02,
  },
  display: {
    fontSize: 28,
    fontWeight: '700' as const,
    lineHeight: 28 * 1.3,
    letterSpacing: 28 * -0.01,
  },
  title: {
    fontSize: 20,
    fontWeight: '600' as const,
    lineHeight: 20 * 1.5,
  },
  body: {
    fontSize: 16,
    fontWeight: '400' as const,
    lineHeight: 16 * 1.5,
  },
  bodyEmphasis: {
    fontSize: 16,
    fontWeight: '600' as const,
    lineHeight: 16 * 1.5,
  },
  caption: {
    fontSize: 13,
    fontWeight: '400' as const,
    lineHeight: 13 * 1.5,
  },
  eyebrow: {
    fontSize: 11,
    fontWeight: '600' as const,
    lineHeight: 11 * 1.4,
    letterSpacing: 11 * 0.10,
    textTransform: 'uppercase' as const,
    // AR locales MUST drop textTransform — Arabic letterforms break under uppercase.
  },
  small: {
    fontSize: 11,
    fontWeight: '400' as const,
    lineHeight: 11 * 1.5,
  },
} as const;

// Arabic line-height multiplier (1.7x vs 1.5x for English). Multiply
// the EN lineHeight by this value when rendering Arabic.
export const bundleDArabicLineHeightMultiplier = 1.7 / 1.5;

export const bundleDShadows = {
  card: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.08,
    shadowRadius: 3,
    elevation: 2,
  },
  // Emerald-glow shadow used ONLY on the Compare CTA when canCompare
  // transitions to true (both inputs filled). Per SKILL.md emerald-usage
  // rule #9: "CTA ready-glow shadow only (button stays black)".
  ctaReady: {
    shadowColor: '#10B981',
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.45,
    shadowRadius: 12,
    elevation: 0,
  },
} as const;

// Motion tokens — spring configs + easing curves + haptic vocabulary.
// New in Bundle D (legacy theme/index.ts has no motion section;
// `motion.ts` lives separately at `src/theme/motion.ts` for the current
// 17-step onboarding screen-transition timing).
export const bundleDMotion = {
  screenTransition: {
    durationMs: 320,
    easing: 'cubic-bezier(0.32, 0.72, 0, 1)',
  },
  springConfig: {
    chip: { damping: 14, stiffness: 200 },
    progress: { damping: 18, stiffness: 120 },
    tab: { damping: 12, stiffness: 180 },
  },
  variableEasing: {
    fast: 'cubic-bezier(0, 0.55, 0.45, 1)',
    slow: 'cubic-bezier(0.4, 0, 0.6, 1)',
    snap: 'cubic-bezier(0.55, 0, 0.1, 1)',
  },
  // Haptic vocabulary per Build Principle #4. chip + stage are LIGHT;
  // winner is MEDIUM. NEVER use heavy / error / warning intensities —
  // those frame the app as scary.
  haptic: {
    chip: 'light' as const,
    stage: 'light' as const,
    winner: 'medium' as const,
  },
} as const;

// Apple HIG / Material Design minimum interactive surface.
export const bundleDMinTouchTarget = 44;

// Machine-readable design-rule policy. Mirrors `.copy-policy.json` +
// Bundle B Build Principle #4 + the R10/R16 invariants. Consumed by
// jest contract tests (e.g. `__tests__/HomeScreen.bundleB.contract.test.tsx`)
// for source-grep checks against banned vocabulary.
export const bundleDPolicy = {
  primaryCtaColor: 'cta.primary (black). Emerald is signal, NOT primary.',
  emeraldUsage: [
    'vs-pill (text on accentLight bg)',
    'logo accent dot',
    'active category chip',
    'toggle on track',
    'active tab icon + label',
    'winner card border',
    'last-free counter pill',
    'CTA ready-glow shadow only (button stays black)',
    "signature button — invitee 'Reveal my verdict' ONLY",
  ],
  bannedMotion: ['shake', 'wobble', 'jitter', 'error bounce'],
  bannedCopyEN: [
    "couldn't",
    'try again',
    'Failed to',
    'Error',
    'Oops',
    'Winner',
    'Best Pick',
    'We recommend',
    'Best for',
  ],
  bannedCopyAR: ['تعذر', 'فشل', 'تقدير', 'مُقدَّر'],
  rtl: 'Every component must work mirrored. Use marginStart/marginEnd, never marginLeft/marginRight. flexDirection row flips automatically; positioned elements need explicit start/end.',
} as const;
