/**
 * Custom icon library for Qaren.
 *
 * Phase 1: infrastructure. The brand mark is QarenLogo
 * (src/components/QarenLogo.tsx), not an icon.
 * Later phases add: ModeIcons, TabIcons, CategoryIcons, StageIcons,
 * CohortIcons, RewardIcons (28 total custom icons per design Section 5a).
 */
export {
  BackIcon,
  CloseIcon,
  SearchIcon,
  BellIcon,
  SettingsIcon,
  PlusIcon,
} from './UtilityIcons';
export { ScanIcon, LinkIcon, TypeIcon } from './ModeIcons';

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
