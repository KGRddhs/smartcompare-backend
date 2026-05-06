/**
 * Custom icon library for Qaren.
 *
 * Phase 1 (this commit): infrastructure + brand mark.
 * Later phases add: ModeIcons, TabIcons, CategoryIcons, StageIcons,
 * CohortIcons, RewardIcons (28 total custom icons per design Section 5a).
 */
export { QaranIcon } from './QaranIcon';

/**
 * Mirror direction-bearing icons (arrows, share, chevrons) under RTL.
 *
 * Use:
 *   <ArrowIcon style={flipForRTL(I18nManager.isRTL).transform}/>
 *
 * Most icons are direction-agnostic (a magnifier, a heart, a phone) and
 * should NOT be flipped — the helper is opt-in per icon.
 */
export const flipForRTL = (
  isRTL: boolean
): { transform: Array<{ scaleX: number }> } =>
  isRTL ? { transform: [{ scaleX: -1 }] } : { transform: [] };
