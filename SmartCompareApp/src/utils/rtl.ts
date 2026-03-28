import { I18nManager } from 'react-native';

/**
 * Returns scaleX transform for icons that should flip in RTL.
 * Only use for directional icons: arrows, chevrons, send, share.
 * Do NOT use for: search, camera, star, heart, trash, settings, check.
 */
export function rtlFlip(): { transform: { scaleX: number }[] } {
  return { transform: [{ scaleX: I18nManager.isRTL ? -1 : 1 }] };
}

/** Returns 'rtl' or 'ltr' for writingDirection style prop. */
export function writingDirection(): 'rtl' | 'ltr' {
  return I18nManager.isRTL ? 'rtl' : 'ltr';
}
