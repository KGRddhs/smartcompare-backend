/**
 * First-launch RTL bootstrap — S69 U6 R4 (audit RT-14).
 *
 * `I18nManager.forceRTL()` only takes effect on the NEXT JS bundle load.
 * App.tsx's boot used to call it and carry on, so the very first session on
 * an Arabic device showed Arabic text in a left-to-right layout (the in-app
 * language switch, useLanguage.ts, has always reloaded; the boot path did
 * not).
 *
 * bootstrapRtl(lang) keeps the boot's allowRTL + forceRTL, and when that
 * CHANGES the layout direction it reloads the bundle once through
 * `Updates.reloadAsync()`:
 *   - the persisted `@qaren_rtl_bootstrapped` flag (the target direction,
 *     'rtl' / 'ltr') is written BEFORE the reload, and a flag already equal
 *     to the target means "reloaded for this direction once already" — so a
 *     reload that does not take (or a crash after the write) can never loop;
 *   - if the flag cannot be written there is no loop guard, so no reload;
 *   - no reload in __DEV__ or when `Updates.isEnabled` is false (Expo Go,
 *     dev clients) — RTL is still forced for the next launch;
 *   - expo-updates is lazy-required inside try/catch (same pattern as
 *     useLanguage.ts), so a build without the native module only skips the
 *     reload.
 * It never throws: boot must always reach the splash release.
 */

import { I18nManager } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';

export const RTL_BOOTSTRAPPED_KEY = '@qaren_rtl_bootstrapped';

type UpdatesModule = { isEnabled?: boolean; reloadAsync?: () => Promise<void> };

function loadUpdates(): UpdatesModule | null {
  try {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    return require('expo-updates') as UpdatesModule;
  } catch {
    return null;
  }
}

export async function bootstrapRtl(lang: string): Promise<void> {
  try {
    const shouldBeRTL = lang === 'ar';
    if (I18nManager.isRTL === shouldBeRTL) return;

    I18nManager.allowRTL(true);
    I18nManager.forceRTL(shouldBeRTL);

    if (__DEV__) return;
    const Updates = loadUpdates();
    if (!Updates?.isEnabled || typeof Updates.reloadAsync !== 'function') return;

    const target = shouldBeRTL ? 'rtl' : 'ltr';
    const previous = await AsyncStorage.getItem(RTL_BOOTSTRAPPED_KEY);
    if (previous === target) return; // already reloaded once for this direction

    // Flag FIRST: a reload that does not take, or a crash after this line,
    // cannot turn into a reload loop.
    await AsyncStorage.setItem(RTL_BOOTSTRAPPED_KEY, target);
    await Updates.reloadAsync();
  } catch {
    // Never block boot: worst case the layout flips on the next launch.
  }
}
