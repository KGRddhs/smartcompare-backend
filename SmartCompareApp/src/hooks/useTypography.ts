/**
 * useTypography — locale-aware typography presets.
 *
 * Phase 5 Task #56. Returns the same shape as `typography` from
 * src/theme, but under AR (RTL) applies design § 1's 1.7x line-height
 * multiplier to the body-text presets (body / bodyEmphasis / title /
 * caption / small). The headline-tight presets (hero, display, eyebrow)
 * have spec-defined compressed line-heights and stay invariant — those
 * deliberate hero typography choices look correct in both locales.
 *
 * Migration pattern in components:
 *
 *   // Before (still valid for non-text-density UI like icons):
 *   import { typography } from '../theme';
 *   <Text style={{...typography.body, color: ...}} />
 *
 *   // After (Arabic-readable):
 *   import { useTypography } from '../hooks/useTypography';
 *   const t = useTypography();
 *   <Text style={{...t.body, color: ...}} />
 *
 * Components that read from `typography` directly continue to work
 * (EN-only readability stays correct); incremental migration is fine.
 */

import { useLanguage } from './useLanguage';
import { typography } from '../theme';

const AR_MULTIPLIER = 1.7 / 1.5;

/** Adjust line-height by the AR multiplier; preserves all other props. */
function withArLineHeight<T extends { fontSize: number; lineHeight: number }>(
  preset: T
): T {
  return { ...preset, lineHeight: preset.lineHeight * AR_MULTIPLIER };
}

export function useTypography(): typeof typography {
  const { isRTL } = useLanguage();
  if (!isRTL) return typography;

  // hero / display / eyebrow keep their spec-tight line-heights.
  return {
    hero: typography.hero,
    display: typography.display,
    eyebrow: typography.eyebrow,
    title: withArLineHeight(typography.title),
    body: withArLineHeight(typography.body),
    bodyEmphasis: withArLineHeight(typography.bodyEmphasis),
    caption: withArLineHeight(typography.caption),
    small: withArLineHeight(typography.small),
  };
}
