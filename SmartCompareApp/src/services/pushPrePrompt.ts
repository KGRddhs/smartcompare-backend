/**
 * Push pre-prompt — S69 U6 R3 (audit RT-12, App Review guideline 4.5.4).
 *
 * The system notification prompt used to fire from tryRegisterPushToken()
 * on every authenticated launch and right after login, with nothing on
 * screen saying what the notifications are for. The OS is now asked only
 * after an in-app explanation, in exactly two places:
 *
 *   1. Onboarding Step 17 (new signed-in users) — its Allow / Maybe later
 *      both persist the answer below, so Results never asks again;
 *   2. the one-time PushPrePrompt sheet after a fresh compare result
 *      renders (ResultsScreen), for everyone who never answered Step 17.
 *
 * The answer is persisted in AsyncStorage under
 * `@qaren_push_preprompt_answered` (same `@qaren_…` key family as
 * pushTokenService / HomeScreen; services/consent.ts is a pure module with
 * no storage). A persisted answer — either one — means the pre-prompt is
 * never shown automatically again; Profile's notifications toggle is the
 * place a user changes their mind.
 *
 * expo-notifications is lazy-required (same pattern as pushTokenService) so
 * a build without the native module degrades to "never show, never ask".
 * Nothing here throws.
 */

import AsyncStorage from '@react-native-async-storage/async-storage';
import { tryRegisterPushToken } from './pushTokenService';

export const PUSH_PREPROMPT_ANSWERED_KEY = '@qaren_push_preprompt_answered';

export type PushPrePromptAnswer = 'allow' | 'not_now';

export interface PushPrePromptContext {
  /** Results was opened from History / Smart pick (a `comparison_id` param). */
  fromHistory?: boolean;
  /** The demographics sheet is showing (or about to) on this Results mount. */
  demographicsShown?: boolean;
}

function loadNotifications(): typeof import('expo-notifications') | null {
  try {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    return require('expo-notifications');
  } catch {
    return null;
  }
}

/**
 * True only when the OS has never been asked ('undetermined'), no answer is
 * persisted, and this is not a History / Smart-pick re-open or the mount
 * that shows the demographics sheet.
 */
export async function shouldShowPushPrePrompt(ctx: PushPrePromptContext = {}): Promise<boolean> {
  if (ctx.fromHistory || ctx.demographicsShown) return false;
  try {
    const answered = await AsyncStorage.getItem(PUSH_PREPROMPT_ANSWERED_KEY);
    if (answered != null) return false;
    const Notifications = loadNotifications();
    if (!Notifications) return false;
    const permission = await Notifications.getPermissionsAsync();
    return permission?.status === 'undetermined';
  } catch {
    return false;
  }
}

/** Persist the answer; a storage failure is swallowed (worst case: asked once more). */
export async function recordPushPrePromptAnswer(answer: PushPrePromptAnswer): Promise<void> {
  try {
    await AsyncStorage.setItem(PUSH_PREPROMPT_ANSWERED_KEY, answer);
  } catch {
    /* best-effort */
  }
}

/**
 * After an answer the OS has already been asked about: persist it, then
 * register the push token when the OS granted (fire-and-forget; never
 * throws). Step 17 calls this with the result of its own system prompt.
 */
export async function completePushPrePrompt(
  answer: PushPrePromptAnswer,
  granted: boolean,
): Promise<void> {
  await recordPushPrePromptAnswer(answer);
  if (granted) {
    tryRegisterPushToken().catch(() => {
      /* never surfaces */
    });
  }
}

/**
 * The pre-prompt's two actions. 'not_now' persists the answer and never
 * touches the OS; 'allow' persists it, shows the system prompt once and,
 * when granted, registers the push token. Resolves to whether permission
 * was granted.
 */
export async function answerPushPrePrompt(answer: PushPrePromptAnswer): Promise<boolean> {
  if (answer !== 'allow') {
    await completePushPrePrompt(answer, false);
    return false;
  }
  let granted = false;
  const Notifications = loadNotifications();
  if (Notifications) {
    try {
      const result = await Notifications.requestPermissionsAsync();
      granted = Boolean(result?.granted) || result?.status === 'granted';
    } catch {
      granted = false;
    }
  }
  await completePushPrePrompt(answer, granted);
  return granted;
}
