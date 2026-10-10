/**
 * S74 CLIENT-TRUTH (#295, DEVICE-PURGE) — the device copy of the user's
 * recent searches.
 *
 * HomeScreen reads and writes the list under this AsyncStorage key
 * (HomeScreen.tsx RECENT_SEARCHES_KEY; a jest node pins the two literals
 * equal). Account deletion removes it (EditProfileScreen, success path only)
 * so the next account on the device never sees the deleted account's
 * searches. Kept out of authService on purpose: the EditProfile suites mock
 * authService with a factory, so a new export there would be undefined in
 * them.
 */
import AsyncStorage from '@react-native-async-storage/async-storage';

export const RECENT_SEARCHES_KEY = '@qaren_recent_searches';

/** Removes the stored recent searches. Never throws. */
export async function clearRecentSearches(): Promise<void> {
  try {
    await AsyncStorage.removeItem(RECENT_SEARCHES_KEY);
  } catch {
    /* nothing to clean up */
  }
}
